"""Rebuild the trending-OI minute grid from REST, for the part of a session
the chain poller never saw.

WHY THIS EXISTS. The chain is only ever recorded LIVE. Upstox's socket carries
no history, and `ChainPoller._warm_start` replays the tool's own file, which
holds only what was already captured. So a poller that starts at 12:18 -- a
restart, a dead token, a machine that was asleep -- has no morning at all,
while the chart beside it starts at 09:15, because BARS are re-fetched whole
from REST on every refresh. On 2026-08-07 the morning was lost to a token that
expired at 03:30, and the Trending OI table opened at 12:40 next to a chart
showing 200 bars from 09:15. The operator's question was the right one: it
should not matter when the tool is started.

WHAT IT DELIBERATELY DOES NOT DO. It fills `ChainState.minutes` and nothing
else. Synthesising whole snapshots and pushing them through `ChainState.update`
would also seed `flow`, `peak`, `walls` and `series` -- and REST candles carry
no IV, no greeks and no bid/ask, so every one of those would be derived from
inputs that do not exist. `oi_flow` reads `minutes` alone, so that is the whole
surface being restored; everything else stays honestly empty rather than
quietly wrong.

WHAT IS AND IS NOT RECOVERABLE, stated here rather than discovered later:

    recoverable      per-strike OI (and so oi_chg), LTP, volume, index spot
    NOT recoverable  IV, greeks, GEX, gamma flip, anything gamma-weighted

RECORDED DATA ALWAYS WINS. This only writes marks EARLIER than the first one
the poller recorded. What the socket actually saw is the truth; this is a
reconstruction, and a reconstruction never overwrites an observation.

`oi_chg` here means OI(t) minus OI at the day's first candle -- "since the
open", which is what the live path means by it too (HANDOFF: "oi_chg means
since 09:15, not since prior close"). Getting that baseline wrong would not
raise; it would quietly shift every row in the table.

Upstox only. Dhan's REST does not serve per-strike option OI history in this
shape, so on that broker the caller skips this rather than half-filling.
"""

import threading
import time

MARK = "%H:%M"
# The session's last candle is 15:29. Upstox keeps serving option candles to
# ~15:39 (post-close OI, no index spot), so a restart after the close used to
# gain ten minutes the live poller never records -- with spot None on the last
# one, which blinded fronts.read (2026-09-23). The warm start already skips
# closed-market snapshots; the backfill now keeps the same boundary.
SESSION_END = "15:30"

# Gap between REST calls. 17 strikes x 2 sides = 34 calls for a NIFTY window,
# so this is the difference between ~9s and ~2min. Upstox's historical limit is
# more generous than the chain endpoint's 1-per-3s, but the exact number is not
# documented anywhere citable -- this is a conservative guess, and a 429 backs
# off rather than hammering. Tune it against measurement, not against vibes.
GAP_S = 0.25
BACKOFF_S = 5.0
MAX_RETRY = 2


def _minute_leg(key, tok, fetch=None):
    """`({"HH:MM": oi}, baseline, {"HH:MM": close})` for one instrument today.

    OI AND PREMIUM COME OFF THE SAME CANDLE, in the one call that was already
    being made. The UI's OI x premium paint needs both axes -- OI alone tells
    you a wall grew, not whether the people who built it paid up or got paid --
    and on a late start the premium half was simply missing while the OI half
    was already being rebuilt. The operator: *"ye to kabhi start karu ye bhr
    lega apne ap haina"*. No extra request, no extra rate-limit budget.

    PREMIUM IS A LEVEL, OI IS A CHANGE, and that asymmetry is deliberate. The
    live path publishes `oi_chg` (cumulative since the open) because that is
    what the chain sends, so the rebuilt grid matches it. There is no such
    convention for premium, and a "premium change since the open" would bake in
    one window choice forever -- the caller differences the level over whatever
    window it is drawing.

    `baseline` is the day's FIRST candle's OI -- the "since the open" anchor.
    Returns `({}, None, {})` when the instrument served nothing, which is a
    real answer (a strike that never traded) rather than an error.
    """
    from datetime import datetime

    import upstox_adapter
    import upstox_rest

    fetch = fetch or upstox_rest.intraday
    arr = upstox_adapter.candles_to_arrays(fetch(key, tok))
    ts = arr.get("timestamp") or []
    oi = arr.get("open_interest") or []
    close = arr.get("close") or []
    if not ts or not oi:
        return {}, None, {}
    mark = [datetime.fromtimestamp(t).strftime(MARK) for t in ts]
    out = {m: float(v) for m, v in zip(mark, oi) if v is not None}
    px = {m: float(c) for m, c in zip(mark, close) if c is not None}
    return out, (float(oi[0]) if oi[0] is not None else None), px


def _spot_series(index, tok, fetch=None):
    """`{"HH:MM": ltp}` for the INDEX -- not the future.

    Frame discipline (HANDOFF section 6b): the chain's `spot` is the index, and
    the future trades 30-90 points away from it. Substituting one for the other
    would put a plausible, wrong number under every break column.
    """
    from datetime import datetime

    import upstox_adapter
    import upstox_instruments
    import upstox_rest

    fetch = fetch or upstox_rest.intraday
    arr = upstox_adapter.candles_to_arrays(
        fetch(upstox_instruments.index_key(index), tok))
    ts = arr.get("timestamp") or []
    close = arr.get("close") or []
    return {datetime.fromtimestamp(t).strftime(MARK): float(c)
            for t, c in zip(ts, close) if c is not None}


def _retry(key, tok, fetch, gap_s, say, index):
    for attempt in range(MAX_RETRY + 1):
        try:
            return _minute_leg(key, tok, fetch)
        except Exception as e:                        # noqa: BLE001
            if attempt >= MAX_RETRY:
                say(f"chain backfill {index}: {key} gave up ({e})")
                return {}, None, {}
            time.sleep(BACKOFF_S if "429" in str(e) else gap_s)
    return {}, None, {}



def _legs(index, strikes, tok, gap_s, fetch, keys_of, say):
    """`({strike: {"ce": (oi_by_min, base, px_by_min), "pe": ...}}, missing)`.

    The per-strike REST walk, lifted out of `minute_grid` so the ledger seed
    (`chainside.ChainSide`) can reuse it. `minute_grid` reduces these legs to
    OI CHANGE and throws the premium away; the basis ledger needs the premium,
    which is why it reads the legs directly rather than the minute grid.
    """
    per_strike, missing = {}, 0
    for k in strikes:
        try:
            kk = keys_of(float(k))
        except Exception as e:                        # noqa: BLE001
            missing += 1
            say(f"chain backfill {index}: strike {k} has no keys ({e})")
            continue
        pair = {}
        for side in ("ce", "pe"):
            key = (kk or {}).get(side.upper())
            if not key:
                pair[side] = ({}, None, {})
                continue
            pair[side] = _retry(key, tok, fetch, gap_s, say, index)
            time.sleep(gap_s)
        per_strike[float(k)] = pair
    return per_strike, missing


def leg_grid(index, strikes, tok, gap_s=GAP_S, fetch=None, keys_of=None,
             log=None):
    """Raw `(t, oi, price)` legs for the basis ledger -- `Ledger.feed`'s three
    inputs, all three in this module's own "recoverable" list.

    A SEPARATE REST WALK from `minute_grid`'s on purpose. Sharing one would
    couple the ledger seed to the minute grid's lifetime, and the two run for
    different reasons at different moments; the cost is ~9s on a daemon thread,
    once per index per day, and it is paced by the same `gap_s` and `_retry`.
    """
    import upstox_instruments
    keys_of = keys_of or (lambda k: upstox_instruments.option_keys(k, index))
    per_strike, _missing = _legs(index, strikes, tok, gap_s, fetch, keys_of,
                                 log or (lambda *_a: None))
    return per_strike


def minute_grid(index, strikes, tok, gap_s=GAP_S, fetch=None, keys_of=None,
                log=None):
    """`{"HH:MM": {"spot": float|None, "k": {strike: (ce_chg, pe_chg)}}}`.

    Shaped exactly like `ChainState.minutes` so it merges in without a
    translation step -- a translation step is somewhere for two shapes to
    drift apart.
    """
    import upstox_instruments
    keys_of = keys_of or (lambda k: upstox_instruments.option_keys(k, index))
    say = log or (lambda *_a: None)

    spots = _spot_series(index, tok, fetch)
    per_strike, missing = _legs(index, strikes, tok, gap_s, fetch, keys_of, say)

    marks = sorted({m for p in per_strike.values()
                    for side in p.values() for m in side[0]})
    grid, partial = {}, 0
    for m in marks:
        # A mark is published only if EVERY tracked strike has both sides at
        # it. Two reasons, and the first one is a bug this code already had:
        # a missing side written as 0.0 reads as "flat", which is a different
        # claim from "not observed" -- measured against the socket's own
        # recording, that alone accounted for the largest disagreements.
        # Second, `oi_flow` SUMS the row, so a mark missing one strike yields
        # a total that is not comparable to the marks around it; the table
        # would show a dip that never happened.
        row, pxrow = {}, {}
        for k, p in per_strike.items():
            ce_hist, ce_base, ce_px = p["ce"]
            pe_hist, pe_base, pe_px = p["pe"]
            ce, pe = ce_hist.get(m), pe_hist.get(m)
            if None in (ce, pe, ce_base, pe_base):
                row = None
                break
            row[int(k)] = (ce - ce_base, pe - pe_base)
            # PREMIUM DOES NOT GATE THE MARK. The completeness rule above
            # exists because `oi_flow` SUMS the OI row, so one missing strike
            # makes the total incomparable. Premium is never summed across
            # strikes -- it is read per strike -- so a leg with no close is
            # published as None (not observed) rather than costing every other
            # strike its mark. A None here is a gap, and a gap is a fact.
            pxrow[int(k)] = (ce_px.get(m), pe_px.get(m))
        if row:
            # `src` travels WITH the mark, not alongside it in a second
            # structure that could drift: `oi_flow` reads the mark it sampled
            # and republishes this, so a row on screen can say it was rebuilt
            # from candles rather than seen by the socket. The live writer
            # (`ChainState.update`) sets no `src`, so absent means observed.
            grid[m] = {"spot": spots.get(m), "k": row, "px": pxrow,
                       "src": "backfill"}
        else:
            partial += 1
    if partial:
        say(f"chain backfill {index}: {partial} mark(s) skipped as incomplete "
            f"(a strike had no candle there; a partial sum is not a sum)")
    if missing:
        say(f"chain backfill {index}: {missing} strike(s) unresolved")
    return grid


def backfill_minutes(state, index, strikes, tok, before=None, log=None,
                     gap_s=GAP_S, fetch=None, keys_of=None):
    """Fill `state.minutes` for marks the poller never recorded; returns how
    many were added.

    `before` is the earliest mark the poller DID record -- nothing at or after
    it is touched. None means the grid is empty and everything is fair game.
    An observation is never overwritten by a reconstruction.
    """
    say = log or (lambda *_a: None)
    grid = minute_grid(index, strikes, tok, gap_s=gap_s, fetch=fetch,
                       keys_of=keys_of, log=say)
    added = 0
    for m, rec in grid.items():
        if before is not None and m >= before:
            continue
        if m >= SESSION_END:     # a tool that ran from 09:15 never holds these
            continue
        if m in state.minutes:                        # never clobber the socket
            continue
        state.minutes[m] = rec
        added += 1
    say(f"chain backfill {index}: added {added} of {len(grid)} REST mark(s) "
        f"before {before or 'the first recorded one'} ({len(strikes)} strikes)")
    return added


def start_backfill(state, index, strikes, tok, before=None, log=None, **kw):
    """Run `backfill_minutes` on a daemon thread.

    Off the poll loop on purpose: 34 REST calls is ~9 seconds, and stalling the
    round-robin that long would age every OTHER index's chain while this one
    catches up on history.

    Writing from a second thread is safe here for one specific reason: this
    only ever adds marks EARLIER than the first recorded one, and the poller
    only ever writes `now`. The two never contend for the same key.
    """
    t = threading.Thread(
        target=backfill_minutes, args=(state, index, strikes, tok),
        kwargs={"before": before, "log": log, **kw},
        daemon=True, name=f"backfill-{index}")
    t.start()
    return t
