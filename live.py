"""LIVE mode: fetch today's bars-so-far from Dhan, compute the indicator
stack (session VWAP + sigma bands, prior-day pivots), run the SAME engine as
replay (architecture invariant 2: causal engine == live engine) and hand the
UI payload to server.py.

Instrument-agnostic: build_payload(cfg) takes an instrument config from
instruments.py (NIFTY / BANKNIFTY / SENSEX). All volatile ids (futures
security-id, expiry, prior day) come from cfg via resolve_dynamic.

Standalone check:  python live.py         (resolves NIFTY, prints bars/state)
Serving:           python server.py live  (refreshes every REFRESH_S)
"""

import json
import math
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import band_rotation
import contract_bars
import instruments
import structure
from dhan_fetch import _intraday_body, _one_session
from engine import Session, session_json

IST = timezone(timedelta(hours=5, minutes=30))
REFRESH_S = 15
INTRADAY_URL = "https://api.dhan.co/v2/charts/intraday"
STICK_F = Path(__file__).parent / "data" / "stick_state.json"

_ids_cache = {}                         # (sym, expiry, strike) -> {"CE": id, "PE": id}
_piv_cache = {}                         # (sym, prev_day) -> pivots dict


def _load_stick():
    """Sticky-ATM state survives a mid-day restart (same day only — a strike
    carried over from Friday would poison Monday's hysteresis)."""
    try:
        d = json.loads(STICK_F.read_text(encoding="utf-8"))
        if d.get("day") == datetime.now(IST).strftime("%Y-%m-%d"):
            return d.get("sticks", {})
    except Exception:
        pass
    return {}


def _save_stick():
    try:
        STICK_F.parent.mkdir(parents=True, exist_ok=True)
        STICK_F.write_text(json.dumps(
            {"day": datetime.now(IST).strftime("%Y-%m-%d"), "sticks": _stick}),
            encoding="utf-8")
    except OSError:
        pass                            # persistence is best-effort


_stick = _load_stick()                  # per-index sticky-ATM state: sym -> {...}


def _token():
    """The Dhan access token -- and only when Dhan is the broker.

    On the Upstox path this value is never transmitted: `_intraday` routes to
    `_upstox_bars`, which reads `.upstox_token` itself. Opening `.dhan_token`
    regardless was a live dependency on a file the Upstox path has no use for
    -- delete or rename it and the whole tape dies with FileNotFoundError
    naming a broker it is not running on.

    Returns "" rather than None so callers keep passing a string:
    `resolve_dynamic` takes `tok` for signature parity and does not use it
    (the scrip master is a public CSV), which is why server.py already calls
    it with "".
    """
    if _upstox():
        return ""
    return open(".dhan_token").read().strip()


def _pick_strike(F, cfg):
    """Sticky ATM on the cfg['step'] grid, keyed per index. Migrate only after
    price holds clearly nearer another strike (>0.6 grid steps away from the
    current one) for 5 consecutive refreshes — kills midpoint whipsaw on pin
    days while the hysteresis stays relative to the instrument's strike spacing."""
    sym, step = cfg["under_sym"], cfg["step"]
    st = _stick.setdefault(sym, {"strike": None, "drift": 0})
    cand = round(F / step) * step
    if st["strike"] is None:
        st["strike"], st["drift"] = cand, 0
        _save_stick()
        return cand
    if cand != st["strike"] and abs(F - st["strike"]) > 0.6 * step:
        st["drift"] += 1
    else:
        st["drift"] = 0
    if st["drift"] >= 5:
        st["strike"], st["drift"] = cand, 0
    _save_stick()
    return st["strike"]


# one gate for ALL Dhan intraday calls: the per-index builder threads
# (server.refresh_one) otherwise burst simultaneously every cycle and trip
# Dhan's rate limit (2026-07-28 open: 107x HTTP 429, tape stale ~4 min)
_gate_lock = threading.Lock()
_gate_t = [0.0]


def _throttle(min_gap=0.35):
    with _gate_lock:
        wait = _gate_t[0] + min_gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _gate_t[0] = time.monotonic()


def _upstox():
    """True when the live tape is running on Upstox rather than Dhan.

    Read through `chain_live` so there is ONE definition of which broker is
    selected -- two would eventually disagree, and the chain and the tape
    disagreeing about their source is a very quiet way to be wrong. Imported
    locally to keep the module graph acyclic.
    """
    from chain_live import _broker
    return _broker() == "upstox"


def _broker_name():
    """What to CALL the source in a sentence a human reads.

    Every "X served nothing" message names a broker, and naming the wrong one
    sends the reader to the wrong dashboard to find out why. Derived from the
    same switch rather than written out at each site."""
    return "Upstox" if _upstox() else "Dhan"


def _upstox_bars(sec_id, instrument, day, name=None):
    """One session of 1-min bars from Upstox, in Dhan's chart-array shape.

    `sec_id` is an UPSTOX INSTRUMENT KEY here, because `_atm_ids` returns keys
    on this path. The future is the exception: its id arrives from
    `cfg['fut_id']`, which `instruments.resolve_dynamic` filled from Dhan's
    scrip master and which means nothing to Upstox. There is exactly one
    near-month future per index, so it is RESOLVED from the Upstox dump.

    That resolution needs the index name, and `seg` cannot supply it --
    NIFTY and BANKNIFTY are both NSE_FNO. Rather than defaulting to NIFTY and
    silently charting the wrong index, `name` is required for the future.
    """
    import upstox_adapter
    import upstox_feed
    import upstox_instruments
    import upstox_rest

    if instrument == "FUTIDX":
        if not name:
            raise RuntimeError(
                "upstox bars: the future needs its index name — seg alone "
                "cannot tell NIFTY from BANKNIFTY, and guessing would chart "
                "the wrong index without saying so.")
        key = upstox_instruments.fut_key(name)
    else:
        key = sec_id
    tok = upstox_feed.read_token()
    today = datetime.now(IST).strftime("%Y-%m-%d")
    candles = (upstox_rest.intraday(key, tok) if day == today
               else upstox_rest.historical(key, tok, day))
    return upstox_adapter.candles_to_arrays(candles)


def _intraday(tok, sec_id, instrument, day, oi=True, seg="NSE_FNO", name=None):
    """v1's intraday fetch: ONE session, consumed whole.

    The body comes from `dhan_fetch._intraday_body` so there is exactly one
    place in the codebase that decides a date range. `to_day=day` is passed
    EXPLICITLY to keep this path bit-for-bit what it has always sent, because
    both callers consume the response without slicing it:

      * `build_payload` charts the CURRENT session, where toDate == day is the
        value in production today.
      * `_pivots` reads the PRIOR session's H/L/C. Older sessions do serve
        fromDate == toDate (measured 2026-07-31: 07-29 -> 07-29 = 375 bars),
        while day + 1 would return 750 bars across two days and quietly
        compute yesterday's pivots off a two-day high and low.

    The measured date behaviour, including the newest session returning zero
    bars for toDate == day, is recorded in `_intraday_body`'s docstring. What
    makes it safe to ignore here is that neither caller PERSISTS these bars;
    anything that does must go through `dhan_fetch._one_session` first.
    """
    if _upstox():
        return _upstox_bars(sec_id, instrument, day, name)
    _throttle()
    body = json.dumps(_intraday_body(sec_id, instrument, day, oi, seg,
                                     to_day=day)).encode()
    req = urllib.request.Request(INTRADAY_URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "access-token": tok})
    return json.loads(
        instruments.fetch_bytes(req, 20, f"intraday {sec_id}").decode())


def _atm_ids(strike, cfg):
    """CE/PE security ids for the strike nearest `strike` at cfg['expiry'].

    Matched on UNDERLYING_SYMBOL / INSTRUMENT / OPTION_TYPE / STRIKE_PRICE —
    uniform across NSE and BSE (SENSEX option trading symbols are the generic
    'BSXOPT', so a trading-symbol prefix match would fail).

    Resolved ONCE per (index, expiry, strike) from the daily scrip-master
    cache and remembered — the ids only change when the sticky strike migrates
    or expiry rolls. Re-downloading the 37 MB master per refresh cycle is what
    froze the tape on 2026-07-27. Both legs must resolve within one strike
    step; anything farther means a stale/truncated master and must fail loudly
    rather than chart the wrong contract.

    On the Upstox path the ids are instrument KEYS, resolved from Upstox's own
    dump. Dhan security ids mean nothing to Upstox, so they are not translated
    -- they are replaced."""
    if _upstox():
        import upstox_instruments
        return upstox_instruments.option_keys(strike, cfg["under_sym"])
    key = (cfg["under_sym"], cfg["expiry"], strike)
    ids = _ids_cache.get(key)
    if ids:
        return ids
    sym, exp = cfg["under_sym"], cfg["expiry"]
    best = {}                                    # option_type -> (dist, sec_id)
    for r in instruments._load_scrip():
        if (r.get("UNDERLYING_SYMBOL") == sym
                and r.get("INSTRUMENT") == "OPTIDX"
                and (r.get("SM_EXPIRY_DATE") or "")[:10] == exp
                and r.get("OPTION_TYPE") in ("CE", "PE")):
            try:
                dist = abs(float(r.get("STRIKE_PRICE") or 0) - strike)
            except ValueError:
                continue
            ot = r["OPTION_TYPE"]
            if ot not in best or dist < best[ot][0]:
                best[ot] = (dist, r["SECURITY_ID"])
    if set(best) != {"CE", "PE"} or max(d for d, _s in best.values()) > cfg["step"]:
        got = {ot: round(d) for ot, (d, _s) in best.items()}
        raise RuntimeError(f"{sym} {exp}: ATM legs unresolved near {strike:.0f} "
                           f"(nearest {got}) — scrip master stale or truncated?")
    ids = {ot: sid for ot, (_d, sid) in best.items()}
    _ids_cache[key] = ids
    return ids


def _pivots(tok, cfg):
    """Standard pivots off the prior session's FUT H/L/C — fetched once per
    (index, prior day); yesterday's bars cannot change intraday."""
    key = (cfg["under_sym"], cfg["prev_day"])
    if key in _piv_cache:
        return _piv_cache[key]
    d = _intraday(tok, cfg["fut_id"], "FUTIDX", cfg["prev_day"], oi=False,
                  seg=cfg["fut_seg"], name=cfg["under_sym"])
    piv = _floor_pivots(max(d["high"]), min(d["low"]), d["close"][-1])
    _piv_cache[key] = piv
    return piv


def _floor_pivots(H, L, C):
    """Standard floor pivots from one session's H/L/C. ONE derivation for the
    FUT and the option legs — this repo already grew two R3 conventions once
    (live.py vs the vendor CSV export; see structure.prior_day_hlc), so the
    formula lives in exactly one place. R3 = H + 2(P-L) is this repo's."""
    P = (H + L + C) / 3.0
    return {"P": P, "R1": 2 * P - L, "S1": 2 * P - H,
            "R2": P + (H - L), "S2": P - (H - L),
            "R3": H + 2 * (P - L), "S3": L - 2 * (H - P)}


_opt_exp_cache = {}                       # (sym, today) -> "YYYY-MM-DD"


def _nearest_opt_expiry(under_sym, today):
    """Nearest unexpired OPTION expiry for `under_sym`, from the scrip master.

    The operator trades the CURRENT expiry only — and until 2026-08-01 the
    tape resolved its CE/PE legs at cfg['expiry'], which resolve_dynamic sets
    from the FUTURES contract, i.e. the MONTHLY. The chain analytics were
    already on the nearest expiry (chain_live.resolve_expiry), so the tape's
    option legs and the chain's books sat on different expiries — the exact
    mismatch the 2026-07-25 desk-grade review flagged as 'possibly open'.
    This resolves it: nearest OPTIDX expiry >= today, local scrip-master scan,
    no API call. On expiry day the current expiry stays current until close
    (>=, not >)."""
    key = (under_sym, today)
    if key in _opt_exp_cache:
        return _opt_exp_cache[key]
    exps = {(r.get("SM_EXPIRY_DATE") or "")[:10]
            for r in instruments._load_scrip()
            if r.get("UNDERLYING_SYMBOL") == under_sym
            and r.get("INSTRUMENT") == "OPTIDX"}
    cands = sorted(e for e in exps if e >= today)
    if not cands:
        raise RuntimeError(f"no unexpired option expiry for {under_sym} "
                           f"in the scrip master")
    _opt_exp_cache[key] = cands[0]
    return cands[0]


_opt_piv_cache = {}     # (sym, expiry, strike, side, prev_day) -> leg dict|None


def _opt_pivots(tok, cfg, strike, ids):
    """Floor pivots off each option leg's OWN prior session — the operator
    reads pivots on option charts too ("pivots also are good support and
    resistance on index as well as on option charts").

    Per (contract, prev_day), cached: yesterday's premium cannot change
    intraday, so each leg costs ONE Dhan fetch per strike per day — and a
    sticky-strike hop naturally refetches for the new contract, because the
    strike is in the key.

    A leg with no usable prior session (a strike that did not trade yesterday,
    or the first session after its expiry rolled) gets None PLUS the reason —
    an invented pivot is a fabricated level, and "no prior session" must never
    be rendered as "no pivots exist". Failures never break the tape: the
    caller attaches whatever this returns.
    """
    out = {"strike": strike, "prev_day": cfg["prev_day"],
           "expiry": cfg["expiry"], "ce": None, "pe": None,
           "why": {"ce": None, "pe": None}}
    for side in ("CE", "PE"):
        key = (cfg["under_sym"], cfg["expiry"], strike, side, cfg["prev_day"])
        if key in _opt_piv_cache:
            leg, why = _opt_piv_cache[key]
        else:
            try:
                time.sleep(0.22)             # same pacing as build_payload's fetches
                d = _intraday(tok, ids[side], "OPTIDX", cfg["prev_day"],
                              oi=False, seg=cfg["fut_seg"])
                if d.get("close"):
                    H, L, C = max(d["high"]), min(d["low"]), d["close"][-1]
                    leg = dict(_floor_pivots(H, L, C), H=H, L=L, C=C)
                    why = None
                else:
                    leg, why = None, (f"no prior session for this contract on "
                                      f"{cfg['prev_day']} — strike may be newly "
                                      f"listed or its expiry rolled")
            except Exception as e:           # isolation: pivots must never kill the tape
                leg, why = None, f"prior-day fetch failed: {type(e).__name__}: {e}"
            _opt_piv_cache[key] = (leg, why)
        out[side.lower()] = leg
        out["why"][side.lower()] = why
    return out


def _bars(d, piv):
    """Dhan arrays -> engine bar dicts with session VWAP + sigma bands
    (VWAP = cum(TP*V)/cumV, TP=(H+L+C)/3; bands = VWAP ± n*sqrt(Var_w)).

    The band recurrence used to be inlined here. It was extracted verbatim to
    `contract_bars.vwap_sigma` so the option-premium tape and this FUT path
    share ONE derivation -- two would drift, and then v1 and v2 would disagree
    about the same band on the same data (contract-tape spec, section 2).
    The numbers this function returns are unchanged.
    """
    n = len(d.get("close", []))
    oi = d.get("open_interest") or [0.0] * n
    bands = contract_bars.vwap_sigma(
        (d["high"][i], d["low"][i], d["close"][i], d["volume"][i])
        for i in range(n))
    bars = []
    for i in range(n):
        ts = datetime.fromtimestamp(d["timestamp"][i], IST)
        b = bands[i]
        bar = {"T": ts.strftime("%H:%M"), "O": d["open"][i], "H": d["high"][i],
               "L": d["low"][i], "C": d["close"][i],
               "VWAP": b["vwap"],
               "U1": b["u1"], "D1": b["d1"],
               "U2": b["u2"], "D2": b["d2"],
               "U3": b["u3"], "D3": b["d3"],
               "OI": oi[i], "V": d["volume"][i]}
        bar.update(piv)
        bars.append(bar)
    return bars


# ---- /api/contract: option-premium tape (Phase 5) --------------------------
#
# The glue lives here rather than in a module of its own because every Dhan
# intraday concern it needs is already in this file: the token, the shared
# 5-req/s gate (_throttle), and the strike -> CE/PE security-id resolver
# (_atm_ids). The pure computation it drives lives in contract_bars.py and
# contract_pair.py, which do no I/O at all.

CONTRACT_DEADLINE_S = 25        # wall-clock cap on ONE intraday chart call.
                                # urllib's timeout= only bounds individual
                                # socket reads, so a trickling response can
                                # hang a request thread forever (2026-07-27
                                # outage). chain_live._with_deadline bounds
                                # the whole call; a healthy 375-bar fetch
                                # returns in well under a second.
CONTRACT_MAX_DAYS = 10          # days x legs is one request each; bounded so a
                                # stray ?days=900 cannot walk into the rate cap

AXIS_RULE = (
    "bars/vwap/oi/bar_days on EVERY leg are indexed by the shared `axis`: "
    "axis[i] is the (session, bar label) pair that slot i means, so "
    "legs.CE.bars[i] and legs.PE.bars[i] are the same minute of the same "
    "session, or null. A leg with no bar at a slot gets an explicit null in "
    "bars, vwap and oi -- never a value carried forward from a neighbouring "
    "bar, which would invent a print that never happened. The axis is the "
    "UNION of the legs' slots sorted by session then clock, so a minute only "
    "one leg traded is still a slot and the hole is visible rather than "
    "closed up. Slots match on the exact label: with interval > 1 each leg's "
    "buckets are anchored on ITS OWN first bar, so two legs whose sessions "
    "start at different minutes can produce disjoint labels -- that shows up "
    "as nulls on both sides, which is the honest reading, not an alignment. "
    "`axis_collisions` on a leg counts slots that leg filled more than once "
    "(a repeated minute in the feed); the first bar wins and the rest are "
    "dropped, because a shared slot cannot hold two bars.")

INDEX_SERIES_RULE = (
    "`index_series` is the INDEX (futures) tape for the same sessions, in the "
    "same shape as a leg (bars / vwap / oi / bar_days, 1:1 with each other) "
    "and banded by the SAME `contract_bars.vwap_sigma` recurrence the v1 FUT "
    "chart uses, so it is the band the operator already reads on screen. It "
    "exists because the compression half of the setup is judged on the index "
    "and not on option premium -- *'squeeze on index entry on option chart'* "
    "-- while the TRIGGER stays on the option leg's own bands. It is "
    "deliberately NOT re-indexed onto `axis`: the axis is the union of the "
    "two OPTION legs' minutes, and a minute neither option printed is still a "
    "minute the index's band existed, so aligning it would punch holes in the "
    "very history the compression rank is taken against. The detector joins "
    "it by (session, bar label) instead. It is null when it could not be "
    "fetched, and `index_series_why` then says why; every `trap` reads "
    "UNKNOWN in that case and NEVER falls back to premium.")

ROTATION_RULE = (
    "`rotation` is the band-rotation detector's answer for this request, one "
    "slot per `axis` index and the SAME length as every leg's arrays: null "
    "where nothing fired, else a record "
    "{i, side, leg, band, trigger, also, confirm, confirm_why, trap, "
    "trap_why, trap_dwell}. "
    "`i` is the axis index the record sits at, so rotation[i], axis[i], "
    "legs.CE.bars[i] and legs.PE.bars[i] are all the same minute of the same "
    "session. The ENGINE decides: a consumer renders these strings and these "
    "verdicts and must never re-derive a tag, a reversal or a confirmation "
    "from the bars it was handed -- two implementations of the operator's "
    "setup would disagree the first time one of them was changed. At most one "
    "record exists per bar even when both legs trigger (band_rotation "
    "interpretation 6), which is why this is a sibling of `legs` and not a "
    "field inside them; when the other leg qualified on that same bar it is "
    "named in `also` rather than dropped, so a consumer can see that both "
    "sides were at their extremes on one minute. `confirm` is three-valued "
    "(CONFIRMED / UNCONFIRMED / UNKNOWN) and `trap` likewise (CLEAR / SUSPECT "
    "/ UNKNOWN); UNKNOWN means unreadable, never 'fine', and must not be "
    "rendered as either verdict. `trap` is measured on `index_series` -- the "
    "INDEX band's width in points, ranked against a trailing window -- and is "
    "UNKNOWN whenever that series is missing. `trap_dwell` is how many "
    "consecutive INDEX bars the band had held a width that tight, or null "
    "where the trap read never got that far.")

FORMING_WHY = (
    "forming is null in this build. The incomplete candle is aggregated from "
    "the ChainPoller's ~10.5s ticks (contract-tape spec section 2, 'The "
    "forming candle'); wiring that up is a later task and cannot be verified "
    "until the market is open. It is never synthesised from the last "
    "completed bar -- a closed candle held open would look live and be a lie.")


def _sessions_back(day, n):
    """The `n` trading sessions ending on or before `day`, OLDEST FIRST.

    Weekends are skipped (instruments._prev_trading_day's rule). Exchange
    holidays are NOT modelled, so a holiday inside the window is requested,
    comes back empty, and is reported as a gap -- which is the honest outcome
    and strictly better than silently sliding the window to hide it.
    """
    d = datetime.strptime(day, "%Y-%m-%d")
    while d.weekday() >= 5:                      # a Sat/Sun request means the
        d -= timedelta(days=1)                   # session that actually traded
    out = [d.strftime("%Y-%m-%d")]
    while len(out) < n:
        out.append(instruments._prev_trading_day(out[-1]))
    return list(reversed(out))


def _leg_series(fetch, sessions, interval):
    """One leg across `sessions`: reshape -> per-session VWAP -> resample.

    `fetch(day)` returns one `dhan_fetch.rest_intraday` payload, or raises.
    Each response is first cut down to the session it was asked for (see
    `_one_session` -- Dhan can and does return the following day too), then
    banded on ITS OWN 09:15 anchor and only then concatenated, so yesterday's
    volume can never bleed into today's VWAP (spec section 2: "anchored at
    09:15 and reset every session").

    `bars`, `vwap`, `oi` and `bar_days` are aligned 1:1 by index. `bar_days`
    exists because bar timestamps are "HH:MM" -- with more than one session in
    the array that is ambiguous, and dating the bars is the only way a caller
    can line a bar up against `gaps`.

    A session Dhan serves no bars for is listed in `gaps` and NEVER
    interpolated; `gap_reasons` says whether it came back empty or the call
    itself failed, because those are different facts about the world.
    """
    bars, vwap, oi, bar_days = [], [], [], []
    gaps, reasons, lengths, served_by = [], {}, {}, {}
    dropped = 0
    for sess in sessions:
        try:
            raw = fetch(sess)
        except Exception as e:                   # noqa: BLE001 - recorded, not swallowed
            gaps.append(sess)
            reasons[sess] = f"fetch failed: {type(e).__name__}: {e}"
            continue
        mine, served, lost = _one_session(raw, sess)
        if served:
            served_by[sess] = served
        one = contract_bars.to_bars(mine)
        dropped += one.dropped + lost
        if one.lengths:
            lengths[sess] = one.lengths
        rows = contract_bars.resample(contract_bars.vwap_bands(one), interval)
        if not rows:
            reasons[sess] = (
                f"{_broker_name()} served no usable bars for this session (it "
                f"returned {served or 'nothing at all'} by date). The expired-option "
                "feed is rolling-ATM, so a strike far from spot that day may "
                "genuinely have no history -- see context/mental-map.md "
                "caveat 2.")
            gaps.append(sess)
            continue
        for b in rows:
            bars.append({k: b.get(k) for k in contract_bars.BAR_KEYS})
            vwap.append({k: b.get(k) for k in contract_bars.BAND_KEYS})
            oi.append(b.get("oi"))
            bar_days.append(sess)
    return {"bars": bars, "vwap": vwap, "oi": oi, "bar_days": bar_days,
            "gaps": gaps, "gap_reasons": reasons,
            "dropped": dropped, "lengths": lengths,
            "served_by_request": served_by,      # what Dhan sent per request
            "forming": None, "forming_why": FORMING_WHY}


def _slot(day, bar):
    """The (session, bar label) a bar occupies. The join key for the axis."""
    return (day, bar.get("t") if isinstance(bar, dict) else None)


def _shared_axis(legs):
    """Union of every leg's slots, in session order then clock order.

    `_leg_series` guarantees each leg's arrays are 1:1 WITHIN that leg, which
    says nothing about two legs lining up with each other: a leg is built from
    its own requests, and a session either leg is missing (or a minute one of
    them never traded) shifts everything after it by one index. The operator's
    setup is a JOINT read -- buy the leg at -2 sigma WHILE the other side comes
    down from +2/+3 -- so a consumer indexing both legs by `i` must be indexing
    the same minute. Reproduced before this existed: CE 5 bars all on 07-30,
    PE 10 bars spanning 07-29 and 07-30, and index 0 compared 07-30 09:15
    against 07-29 09:15.
    """
    seen, slots = set(), []
    for leg in legs.values():
        for key in map(_slot, leg["bar_days"], leg["bars"]):
            if key not in seen:
                seen.add(key)
                slots.append(key)
    return sorted(slots, key=lambda k: (k[0] or "", k[1] or ""))


def _align_to_axis(leg, axis):
    """Re-index one leg's arrays onto `axis`, in place. See AXIS_RULE.

    A slot the leg has no bar for becomes an explicit `None` in `bars`, `vwap`
    and `oi`. Nothing is carried forward from the previous bar: a null says
    "this leg did not print here", and a repeated close would say "it traded
    here at this price", which is a different and untrue claim.
    """
    idx, collisions = {}, 0
    for i, key in enumerate(map(_slot, leg["bar_days"], leg["bars"])):
        if key in idx:
            collisions += 1
            continue
        idx[key] = i
    bars, vwap, oi = [], [], []
    for key in axis:
        j = idx.get(key)
        bars.append(leg["bars"][j] if j is not None else None)
        vwap.append(leg["vwap"][j] if j is not None else None)
        oi.append(leg["oi"][j] if j is not None else None)
    leg["bars"], leg["vwap"], leg["oi"] = bars, vwap, oi
    leg["bar_days"] = [d for d, _t in axis]
    leg["axis_collisions"] = collisions
    return leg


def build_contract(idx, strike=None, side="BOTH", interval=3, days=1,
                   day=None, chain_rows=None, atm=None, fetch=None,
                   index_fetch=None):
    """The `/api/contract` payload: option-premium bars + their own VWAP.

    `strike` None means "let contract_pair.pick_pair choose", which needs a
    chain snapshot: pass `chain_rows` (the `strikes` list off an /api/chain
    payload) to reuse one the poller already paid for, or leave it None and
    one is fetched. Pass `atm` alongside it (the same payload's top-level
    `atm` -- see `chain_live.normalize` / `ChainPoller._publish`) so
    `pick_pair` ranks candidates against the real ATM instead of falling
    back to its own same-strike proxy; when `chain_rows` is left `None` and
    fetched here, the freshly-fetched snapshot's own `atm` is used unless
    the caller already supplied one. `pick_pair` returns a `(pair, why)`
    TUPLE and the pair's CE and PE sit at DIFFERENT strikes -- that is the
    setup, not a bug.

    `fetch(sec_id, day) -> rest_intraday payload` is injectable so the
    assembly can be tested without a token or a network. `index_fetch(day) ->
    rest_intraday payload` is the same hook for the INDEX (futures) series and
    takes ONE argument, because the futures security id is resolved in here
    and an injecting caller has no business having to know it. Injecting
    `fetch` WITHOUT `index_fetch` suppresses the index request altogether:
    taking over the option I/O and then being handed a silent network call for
    the index would defeat the point of injecting at all. `index_series` is
    then null with `index_series_why` saying so, and every `trap` is UNKNOWN.

    Shape note: with `side=BOTH` the two legs are two different strikes, so
    there is no single top-level series and `bars`/`vwap`/`oi` are `null`; the
    arrays live under `legs.CE` / `legs.PE`. With one side requested the
    top-level arrays are filled in as spec section 2 describes.

    JOIN RULE: the response carries ONE `axis` -- a list of `[session, bar
    label]` pairs -- and every leg's `bars`/`vwap`/`oi`/`bar_days` is indexed
    by it, so `legs.CE.bars[i]` and `legs.PE.bars[i]` are the same minute of
    the same session or `null`. Legs are NOT independently indexed and a
    missing bar is never filled in from its neighbour. `axis_rule` states this
    in the payload; the full wording, including what happens when the legs'
    resample anchors differ, is `AXIS_RULE`.

    `rotation` rides on that same axis as a SIBLING of `legs`: the
    band-rotation detector's record for slot `i`, or null where nothing fired.
    It is computed here, in the engine, so a UI renders it and never re-derives
    it -- see `ROTATION_RULE`. Its compression read comes off `index_series`,
    the futures tape for the same sessions, which is NOT axis-aligned; see
    `INDEX_SERIES_RULE`.

    `day` defaults to today and is the newest session charted. Passing an
    older `day` backfills history, but note the asymmetry: the BARS are
    historical while the chain snapshot the pair is picked from is fetched
    LIVE, so with `day` != today the pair describes the market now and the
    bars describe the market then. The operator's setup picks the pair at
    ~09:20 of the session being traded, so only `day` == today is a faithful
    reproduction of it; a backfilled pair is a convenience, not the setup.

    Not implemented here, deliberately: `spot` (needs the FUT series per
    session -- another request per session, and no consumer yet) and
    `narration` (its own task). `forming` is always null; see FORMING_WHY.
    """
    import chain_live
    import dhan_fetch
    from contract_pair import pick_pair

    side = (side or "BOTH").upper()
    if side not in ("CE", "PE", "BOTH"):
        raise ValueError(f"side must be CE, PE or BOTH, got {side!r}")
    interval = max(1, min(60, int(interval)))
    days = max(1, min(CONTRACT_MAX_DAYS, int(days)))
    cfg = instruments.get(idx)                   # KeyError on an unknown index
    day = day or datetime.now(IST).strftime("%Y-%m-%d")
    sessions = _sessions_back(day, days)

    on_upstox = _upstox()

    # The OPTION expiry, not the futures one build_payload resolves. On Dhan
    # `_atm_ids` matches OPTIDX rows on cfg['expiry']; on Upstox the leg keys
    # come out of the dump's own nearest-live expiry. Either way this is the
    # number that decides which contract's history we are about to chart, and
    # it MUST be the one the leg resolver will use -- which is why the Upstox
    # side reads it through `option_expiry`, the same `_near_opts` that
    # `option_keys` goes through, rather than computing a second answer.
    expiry_why = None
    if on_upstox:
        import upstox_feed
        import upstox_instruments

        tok = upstox_feed.read_token()           # raises with the fix in the message
        dhan = None
        expiry = upstox_instruments.option_expiry(cfg["under_sym"])
        if any(s != datetime.now(IST).strftime("%Y-%m-%d") for s in sessions):
            expiry_why = (
                f"these bars are the {expiry} contract. Upstox's instrument "
                f"dump carries LIVE instruments only -- an expired weekly is "
                f"absent, not merely unresolvable -- so a backfilled session "
                f"is charted on the CURRENT front contract, which is not the "
                f"one that was front on that day. Real bars, different "
                f"instrument; today is the only faithful reproduction.")
    else:
        tok = chain_live.read_token()
        st = chain_live.token_status(tok)
        if not st["ok"]:
            raise RuntimeError(st["msg"])
        dhan = chain_live._client(tok)
        expiry = chain_live._with_deadline(
            lambda: chain_live.resolve_expiry(dhan, day, cfg["under_id"],
                                              cfg["under_seg"]),
            chain_live.CHAIN_DEADLINE_S, f"{idx} expiry_list")
    cfg["expiry"] = expiry

    pair, why = None, None
    if chain_rows is None and strike is None:
        if on_upstox:
            # Deliberately not a fetch. On Upstox the chain arrives over the
            # websocket ChainPoller owns; opening a SECOND socket here would
            # double the subscription for one chart request, and server.py
            # already hands this route the snapshot the poller paid for.
            why = ("no chain snapshot to pick a pair from: on Upstox the chain "
                   "comes over the poller's websocket and this route will not "
                   "open a second one. Pass `chain_rows` (server.py does) or "
                   "name a strike.")
        else:
            try:
                resp = chain_live._with_deadline(
                    lambda: dhan.option_chain(cfg["under_id"], cfg["under_seg"],
                                              expiry),
                    chain_live.CHAIN_DEADLINE_S, f"{idx} option_chain")
                snap = chain_live.normalize(
                    chain_live._inner(resp), datetime.now(IST),
                    cfg.get("window", chain_live.WINDOW_PTS))
                chain_rows = snap["strikes"]
                if atm is None:
                    atm = snap.get("atm")
            except Exception as e:               # noqa: BLE001 - reported below
                why = f"no chain snapshot to pick a pair from: {type(e).__name__}: {e}"
    if chain_rows:
        pair, why = pick_pair(chain_rows, idx, atm=atm)
    elif why is None:
        why = ("pair not computed: an explicit strike was requested and no "
               "chain snapshot was supplied, so no chain request was spent")

    sides = ("CE", "PE") if side == "BOTH" else (side,)
    if strike is not None:
        strike = float(strike)
        want = [(s, strike) for s in sides]
    else:
        if pair is None:
            raise RuntimeError(f"no strike requested and no pair could be "
                               f"picked: {why}")
        want = [(s, pair[s.lower()]["strike"]) for s in sides]

    def _real_fetch(sec_id, sess):
        if on_upstox:
            # `sec_id` is an Upstox instrument KEY here (`_atm_ids` returns
            # keys on this path). upstox_rest carries its own throttle, and
            # `_upstox_bars` picks intraday vs historical off the session.
            return _upstox_bars(sec_id, "OPTIDX", sess)
        _throttle()                              # the shared 5-req/s gate
        return chain_live._with_deadline(
            lambda: dhan_fetch.rest_intraday(tok, sec_id, "OPTIDX", sess,
                                             oi=True, seg=cfg["fut_seg"]),
            CONTRACT_DEADLINE_S, f"{idx} intraday {sec_id} {sess}")

    injected = fetch is not None
    fetch = fetch or _real_fetch
    legs, gaps, reasons = {}, [], {}
    for s, k in want:
        # _atm_ids raises if neither leg resolves within one strike step, so a
        # truncated scrip master fails loudly instead of charting a neighbour.
        sec_id = _atm_ids(k, cfg)[s]
        leg = _leg_series(lambda sess, _i=sec_id: fetch(_i, sess),
                          sessions, interval)
        leg["side"], leg["strike"], leg["security_id"] = s, k, sec_id
        legs[s] = leg
        for g in leg["gaps"]:
            if g not in gaps:
                gaps.append(g)
            reasons[f"{s} {g}"] = leg["gap_reasons"][g]

    # The INDEX tape the compression read is taken from. Fetched here rather
    # than derived from anything already in hand: the option legs cannot
    # answer it (that was the 2026-07-31 correction) and no other caller has
    # the futures series for a BACKFILLED session.
    #
    # `resolve_dynamic` writes fut_id AND expiry into the cfg it is handed, so
    # it gets its OWN copy: `cfg["expiry"]` above is the OPTION expiry that
    # decides which contracts `_atm_ids` resolved, and letting the futures
    # expiry overwrite it would silently chart a different strike's history.
    # It resolves against `day`, not today, so a backfilled session gets the
    # future that was actually current then (NIFTY 2026-07-30 -> 58072; the
    # `FUT_ID = "61093"` constant in dhan_fetch.py is a stale July id and must
    # never be used here).
    index_series, index_why = None, None
    if index_fetch is None and injected:
        index_why = ("no index series was requested: `fetch` was injected but "
                     "`index_fetch` was not, so this build made no index "
                     "call. Compression reads UNKNOWN on every bar.")
    else:
        fut_id, ifetch = None, index_fetch
        if ifetch is None:                       # only then is an id needed
            try:
                if on_upstox:
                    # There is exactly one near-month future per index in the
                    # dump, so it resolves without a scrip master and without
                    # `day` -- and a Dhan security id would mean nothing here.
                    fut_id = upstox_instruments.fut_key(cfg["under_sym"])
                else:
                    fut_id = instruments.resolve_dynamic(
                        instruments.get(idx), tok, day)["fut_id"]
            except Exception as e:               # noqa: BLE001 - reported below
                index_why = (f"no index series: the futures security id for "
                             f"{idx} on {day} did not resolve "
                             f"({type(e).__name__}: {e}). Compression reads "
                             f"UNKNOWN on every bar.")
            if fut_id is not None and on_upstox:
                def ifetch(sess, _n=cfg["under_sym"]):
                    # `_upstox_bars` re-resolves the future from the same dump;
                    # the name is what it cannot infer (NIFTY and BANKNIFTY are
                    # both NSE_FNO), and guessing would chart the wrong index.
                    return _upstox_bars(None, "FUTIDX", sess, name=_n)
            elif fut_id is not None:
                def ifetch(sess, _i=fut_id):
                    _throttle()                  # the same 5-req/s gate
                    return chain_live._with_deadline(
                        lambda: dhan_fetch.rest_intraday(
                            tok, _i, "FUTIDX", sess, oi=True,
                            seg=cfg["fut_seg"]),
                        CONTRACT_DEADLINE_S, f"{idx} intraday FUT {_i} {sess}")
        if ifetch is not None:
            index_series = _leg_series(ifetch, sessions, interval)
            index_series["security_id"] = fut_id
            index_series["instrument"] = "FUTIDX"
            if not index_series["bars"]:
                said = "; ".join(index_series["gap_reasons"].values())
                index_why = (f"the index series (FUT {fut_id}) came back "
                             f"empty for {', '.join(sessions)}: "
                             f"{said or 'no reason recorded'}")

    # ONE axis for the request. Built AFTER every leg so it is the union of
    # what the legs really hold, then both legs are re-indexed onto it -- the
    # legs are 1:1 with each other only from here on. `index_series` is
    # deliberately NOT aligned onto it; see INDEX_SERIES_RULE.
    axis = _shared_axis(legs)
    for leg in legs.values():
        _align_to_axis(leg, axis)

    out = {"ok": True, "index": idx, "expiry": expiry, "interval": interval,
           # Additive, and disclosed rather than inferred: which source served
           # these bars, and -- on Upstox backfills -- why the contract they
           # belong to is not the one that was front on that session.
           "broker": "upstox" if on_upstox else "dhan", "expiry_why": expiry_why,
           "days": days, "sessions": sessions, "side": side, "strike": strike,
           "pair": pair, "pair_why": why, "legs": legs,
           "axis": [[d, t] for d, t in axis], "axis_rule": AXIS_RULE,
           # A SIBLING of `legs`, on the same shared axis. Computed here, in
           # the engine, so the browser never re-derives the operator's setup;
           # see ROTATION_RULE. Additive: nothing above changes shape.
           "rotation": band_rotation.detect(legs, axis,
                                            index_series=index_series),
           "rotation_rule": ROTATION_RULE,
           "index_series": index_series, "index_series_why": index_why,
           "index_series_rule": INDEX_SERIES_RULE,
           "bars": None, "vwap": None, "oi": None, "bar_days": None,
           "gaps": sorted(gaps), "gap_reasons": reasons,
           "forming": None, "forming_why": FORMING_WHY,
           "built_at": time.time(), "live_error": None}
    if len(legs) == 1:
        only = next(iter(legs.values()))
        out.update({k: only[k] for k in
                    ("strike", "side", "bars", "vwap", "oi", "bar_days")})
    return out


# --- basis plausibility -------------------------------------------------
# The operator's own read of the instrument (2026-08-05): NIFTY futures trade
# ABOVE the index, roughly 20-150 points, and a discount is unusual. That
# asymmetry is the guard: the upside is left generous (carry is largest early
# in a monthly contract) and the downside tight, because a futures price BELOW
# the index is not a market state we see -- it means one of the two numbers is
# stale.
#
# Why this matters more than it looks: everything DRAWN on the chart is
# futures-frame, and every chain-derived level (walls, PIN, STK, max pain, GEX
# flip) arrives in INDEX terms and is moved onto the tape by adding `basis`. A
# wrong basis does not degrade the chart -- it MISPLACES every one of those
# lines. That is exactly what cost a full day on 2026-08-04 (HANDOFF 6b), and
# the post-close print that exposed it was -52.90.
BASIS_MAX_PCT = 0.010      # +1.0% of spot -- ~+246 at NIFTY 24600
BASIS_MIN_PCT = -0.0015    # -0.15%        -- ~-37; catches the -52.90 print


def _basis(fut_last, spot):
    """(basis, why) -- the futures/index carry, or None with a reason.

    Returning 0.0 on failure, which this used to do, is not a safe default: it
    is the positive claim "futures and index are at the same price", and the UI
    draws chain levels on it. No plausible basis, no number.
    """
    try:
        s = float(spot)
        f = float(fut_last)
    except (TypeError, ValueError):
        return None, "the futures last price or the chain spot was unreadable"
    if not (math.isfinite(s) and math.isfinite(f)) or s <= 0:
        return None, "the chain gave no usable spot to measure the futures against"
    b = f - s
    lo, hi = s * BASIS_MIN_PCT, s * BASIS_MAX_PCT
    if not lo <= b <= hi:
        return None, (f"futures {f:.2f} against index {s:.2f} is a basis of "
                      f"{b:+.2f} ({b / s:+.2%}), outside the plausible "
                      f"{lo:+.0f}..{hi:+.0f} for this instrument -- one of the "
                      f"two prices is stale, so no chain level is placed")
    return b, ""


def build_payload(cfg, spot=None):
    """Fetch today, run the engine, return the /api/data JSON bytes for `cfg`.

    `spot` is the chain poller's live INDEX price. The futures tape trades at
    a carry premium to it (59 points on 2026-08-04, more than a strike step),
    and that premium must not reach the option maths: the legs are weekly, the
    future is monthly. We take one scalar `basis` from the latest bar rather
    than a per-bar spot series because only the current spot is available,
    and intraday carry is near-constant while the tape moves in points.
    Passing nothing, or passing a spot that makes the carry implausible, now
    publishes `basis: null` plus a `basis_why` sentence rather than the 0.0 it
    used to invent -- see `_basis` for why 0.0 was never a safe default.
    """
    tok = _token()
    today = datetime.now(IST).strftime("%Y-%m-%d")
    day_lbl = datetime.now(IST).strftime("%b %d")
    seg = cfg["fut_seg"]
    fut_raw = _intraday(tok, cfg["fut_id"], "FUTIDX", today, seg=seg,
                        name=cfg["under_sym"])
    if not fut_raw.get("close"):
        return json.dumps({"index": cfg["under_sym"], "strike": None, "days": [],
                           "built_at": time.time(),
                           "live_error": "no bars yet for " + today}).encode()
    # Basis first: the strike is picked in the OPTION's frame too, or the
    # engine's "ATM" sits a whole 50-point step above the real one.
    basis, basis_why = _basis(fut_raw["close"][-1], spot)
    # A strike still has to be picked -- the legs cannot be fetched without one
    # -- and with no trustworthy carry the best available estimate is zero. That
    # is a FETCH decision, not a published fact: `basis` still goes out as null
    # with `basis_why`, so nothing chain-derived is drawn on the tape.
    strike = float(_pick_strike(fut_raw["close"][-1] - (basis or 0.0), cfg))
    # The option side of the tape lives on the NEAREST expiry — the one the
    # operator actually trades — not on cfg['expiry'], which is the FUTURES
    # (monthly) contract's. See _nearest_opt_expiry for the history.
    ocfg = dict(cfg, expiry=_nearest_opt_expiry(cfg["under_sym"], today))
    ids = _atm_ids(strike, ocfg)
    time.sleep(0.22)
    ce_raw = _intraday(tok, ids["CE"], "OPTIDX", today, seg=seg)
    time.sleep(0.22)
    pe_raw = _intraday(tok, ids["PE"], "OPTIDX", today, seg=seg)
    piv = _pivots(tok, cfg)

    fut, ce, pe = (_bars(x, piv) for x in (fut_raw, ce_raw, pe_raw))
    # align on common minutes (options can miss the odd bar)
    keep = ({b["T"] for b in ce} & {b["T"] for b in pe} & {b["T"] for b in fut})
    fut = [b for b in fut if b["T"] in keep]
    ce = [b for b in ce if b["T"] in keep]
    pe = [b for b in pe if b["T"] in keep]

    # t_days prices the legs we actually chart — the nearest expiry's — so the
    # greeks and gamma.t now describe the operator's own contract. Note the
    # engine's expiry-day branch (gamma.t <= 0.5) therefore fires on WEEKLY
    # expiry days now, which is correct for what is being traded.
    exp = datetime.strptime(ocfg["expiry"] + " 15:30",
                            "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    # The REAL time to expiry, unfloored. GammaLayer owns the numerical floor
    # (engine.GAMMA_T_FLOOR) and reports when it binds; flooring here as well
    # meant the freeze happened twice and was invisible at both sites, which
    # is what D7 was. Clamped at zero only so a post-expiry clock cannot go
    # negative.
    t_days = max((exp - datetime.now(IST)).total_seconds() / 86400.0, 0.0)
    s = Session(day_lbl + " LIVE", fut, ce, pe, quiet=True,
                strike=strike, t_days=t_days, basis=basis or 0.0)
    s.run()
    js = session_json(s)
    # mid-session: the end-of-day CARRY verdict is meaningless until the
    # close — suppress it so the feed never shows a 15:29 event at 10:30
    if js["bars"] and js["bars"][-1]["t"] < "15:25":
        js["events"] = [e for e in js["events"] if e["kind"] != "CARRY"]
    # Phase 3.5 SMC/ICT layer, additive: each structure carries the index of
    # the bar that completed it, so the UI clips by `born` instead of the
    # backend re-deriving structure per scrub position. v1 ignores the key.
    # The pivots block goes in too: it is the prior session's H/L/C in reduced
    # form, and structure.py inverts PDH/PDL/PDC back out of it (refusing, and
    # emitting nothing, if the numbers do not check out as floor pivots).
    js["structures"] = structure.compute(js["bars"], pivots=js.get("pivots"))
    # The operator's own band-rotation setup, run on THIS INDEX's bars — the
    # same trigger /api/contract applies to the option legs, which is why the
    # code is shared rather than copied. Additive and 1:1 with `bars`, null
    # where nothing fired; v1 (ui/app.js) ignores the key. `confirm` is UNKNOWN
    # on every record by construction — see band_rotation.detect_index.
    js["rotation"] = band_rotation.detect_index(js["bars"])
    js["rotation_rule"] = band_rotation.INDEX_ROTATION_RULE
    # Floor pivots of each tracked option leg's OWN prior session, additive
    # (v1 ignores the key). Same formula as the FUT pivots (_floor_pivots),
    # applied to the contract's own H/L/C; a leg with no prior session says
    # why instead of inventing levels. The whole block is fail-soft.
    js["opt_pivots"] = _opt_pivots(tok, ocfg, strike, ids)
    # Which expiry the ce/pe legs (and their pivots, and t_days) belong to —
    # disclosed so the UI can name the contract rather than implying it.
    js["opt_expiry"] = ocfg["expiry"]
    # Disclosed, not hidden: every chain-derived level (walls, pin, max pain,
    # gamma flip) is quoted in the INDEX frame while these bars are FUTURES.
    # Publishing the measured basis is what lets the UI put both on one axis
    # instead of drawing option levels ~59 points from where they belong.
    # `spot` rides along so the screen can name the number it converted from;
    # both are null when the chain was unavailable -- never guessed.
    return json.dumps({"index": cfg["under_sym"], "strike": strike, "live": True,
                       "expiry": cfg["expiry"], "built_at": time.time(),
                       "basis": round(basis, 2) if basis is not None else None,
                       # Additive: a consumer that does not know the key ignores
                       # it. Empty string when basis is fine -- "we checked and
                       # it is good" and "we could not check" stay different
                       # sentences.
                       "basis_why": basis_why,
                       "spot": float(spot) if spot else None,
                       "days": [js]}).encode()


if __name__ == "__main__":
    from instruments import get, resolve_dynamic
    today0 = datetime.now(IST).strftime("%Y-%m-%d")
    cfg0 = resolve_dynamic(get("NIFTY"), _token(), today0)
    p = build_payload(cfg0)
    d = json.loads(p)
    if d.get("live_error"):
        print("live:", d["live_error"])
    else:
        day = d["days"][0]
        bars = day["bars"]
        last = bars[-1]
        print(f"LIVE {d['index']} {day['day']} strike {d['strike']:.0f}: "
              f"{len(bars)} bars, last {last['t']} FUT {last['fut']['c']:.1f}")
        ctx = last.get("ctx", {})
        print("verdict:", ctx.get("verdict"), "|", ctx.get("line"))
        print("events:", len(day["events"]))
