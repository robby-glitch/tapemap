"""Upstox's shapes -> the two shapes TapeMap already consumes. Pure, no network.

WHY A TRANSLATION AND NOT A REWRITE. The engine does not know what a broker is.
It knows two shapes:

  1. **chart arrays** -- `{timestamp, open, high, low, close, volume,
     open_interest}`, parallel lists, oldest first. `live._intraday` returns
     them and `live._bars` consumes them.
  2. **the chain payload** -- `{last_price, oc: {strike: {ce, pe}}}`, which
     `chain_live.normalize` turns into the snapshot contract that
     `chain_metrics`, `engine`, GEX, the walls and ZONE READ all read.

Hit those two and nothing downstream changes. So this module deliberately
rebuilds Dhan's payload shape rather than a cleaner one of its own: that lets
`chain_live.normalize` be reused verbatim, which keeps the strike window, the
ATM pick and the sort in ONE tested place instead of two that can drift.

Everything here is a pure function of its arguments. The socket, the token and
the instrument dump live elsewhere, so the mapping can be tested without a
network, a token, or market hours.

FIELD MAP, measured 2026-08-05 against the live v3 feed:

    TapeMap wants   <- Upstox
    ltp             <- ltpc.ltp
    oi              <- oi
    iv              <- iv          (already a FRACTION: 0.1154 for ~11.5% vol)
    vol             <- vtt
    bid / ask       <- firstDepth.bidP / .askP   (or marketLevel[0] in full)
    gamma / delta   <- optionGreeks.gamma / .delta
    avg             <- atp         ** full mode only **
    oi_chg          <- NOTHING. See below.

WHY `full` AND NOT `option_greeks`. `option_greeks` omits `atp`, which is the
chain's `avg`. `full` is a superset -- it adds atp, 5-level depth, tbq/tsq --
and its subscription cap (2000 keys) is far above the ~40 this tool needs.

**`oi_chg` HAS NO SOURCE AND IS NOT INVENTED HERE.** Dhan ships `previous_oi`
(the PRIOR SESSION'S CLOSING open interest) and `chain_live._side` derives the
change from it. Upstox's feed carries current `oi` only. So `prev_oi` is a
REQUIRED argument: pass the prior close per (strike, side) and `oi_chg` means
exactly what it always meant. Pass nothing for a strike and this module emits
`previous_oi = None`, which `_side` reads as a change of 0 -- honestly "not
known", never a guess. What must NOT happen is silently baselining against the
session's first snapshot: that would make `oi_chg` mean "since we connected",
a different quantity wearing the same name, and every writer-score and wall
reading built on it would be wrong in a way nothing downstream could detect.
"""

from datetime import datetime

# Upstox candles are [ts, o, h, l, c, volume, open_interest], NEWEST FIRST.
CANDLE_FIELDS = ("timestamp", "open", "high", "low", "close", "volume",
                 "open_interest")


def _num(x):
    """float(x) or None -- never raises, never returns NaN as a real number."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None                 # NaN != NaN


def _core(feed):
    """The one payload inside a `Feed`, whichever mode produced it.

    `full` yields fullFeed.marketFF, `option_greeks` yields
    firstLevelWithGreeks; both carry ltpc / optionGreeks / oi / iv / vtt under
    the same names, so callers do not need to know which mode was subscribed.
    An index arrives as fullFeed.indexFF and has no greeks at all.
    """
    if not isinstance(feed, dict):
        return None
    if feed.get("firstLevelWithGreeks"):
        return feed["firstLevelWithGreeks"]
    full = feed.get("fullFeed") or {}
    return full.get("marketFF") or full.get("indexFF") or None


def ltp_of(feed):
    """Last traded price out of any feed shape -- index, future or option."""
    core = _core(feed)
    if not core:
        return None
    return _num((core.get("ltpc") or {}).get("ltp"))


def _depth(core):
    """(bid, ask) from firstDepth (option_greeks) or marketLevel (full)."""
    q = core.get("firstDepth")
    if not q:
        levels = (core.get("marketLevel") or {}).get("bidAskQuote") or []
        q = levels[0] if levels else {}
    return _num(q.get("bidP")), _num(q.get("askP"))


def side_payload(feed, prev_oi=None):
    """One Upstox option `Feed` -> the per-side dict Dhan's chain payload uses.

    Keys are Dhan's, not ours, because `chain_live._side` reads them.
    `prev_oi` is the PRIOR SESSION'S closing open interest, or None when it is
    not known -- see the module docstring on why it is never faked.
    """
    core = _core(feed)
    if not core:
        return None
    greeks = core.get("optionGreeks") or {}
    bid, ask = _depth(core)
    return {
        "last_price": _num((core.get("ltpc") or {}).get("ltp")) or 0.0,
        "oi": _num(core.get("oi")) or 0.0,
        "previous_oi": _num(prev_oi),
        "implied_volatility": _num(core.get("iv")),
        "volume": _num(core.get("vtt")) or 0.0,
        "top_bid_price": bid,
        "top_ask_price": ask,
        "average_price": _num(core.get("atp")),
        "greeks": {"gamma": _num(greeks.get("gamma")),
                   "delta": _num(greeks.get("delta"))},
    }


def chain_payload(feeds, meta, spot, prev_oi=None):
    """Latest feed-by-instrument-key -> the payload `chain_live.normalize` eats.

    `feeds`   {instrument_key: decoded Feed}
    `meta`    {instrument_key: (strike, "ce"|"pe")} -- who each key is
    `spot`    index last price, the frame every strike is measured against
    `prev_oi` {(strike, "ce"|"pe"): prior close OI}, optional

    A strike is emitted only when BOTH legs have arrived. A half-filled strike
    is dropped rather than half-reported, because `chain_live.normalize`
    already discards any row missing a side and a partial row would otherwise
    look like a real one carrying a zeroed leg -- which reads downstream as a
    wall that is not there.
    """
    if not spot:
        raise ValueError("chain_payload needs a spot; the index feed had none")
    prev_oi = prev_oi or {}
    oc = {}
    for key, feed in (feeds or {}).items():
        who = meta.get(key)
        if not who:
            continue
        strike, side = who
        if side not in ("ce", "pe"):
            continue
        built = side_payload(feed, prev_oi.get((strike, side)))
        if built is None:
            continue
        oc.setdefault(f"{float(strike):.6f}", {})[side] = built
    both = {k: v for k, v in oc.items() if "ce" in v and "pe" in v}
    return {"last_price": float(spot), "oc": both}


def candles_to_arrays(candles):
    """Upstox intraday candles -> Dhan's parallel chart arrays.

    Two differences that would corrupt the tape if missed, so both are handled
    here rather than assumed:

      * Upstox returns candles **NEWEST FIRST**; every consumer of the chart
        arrays walks them oldest-first. Feeding them reversed would run VWAP
        and the sigma bands backwards through the session.
      * Upstox timestamps are ISO strings carrying a real IST offset
        ('2026-08-05T09:53:00+05:30'); Dhan's are epoch seconds. The epoch is
        what `dhan_fetch._series` and `_one_session` expect, and having a true
        instant here is strictly better than Dhan's date-less "HH:MM" -- it is
        the problem `ui-v2/src/proto/protoTime.ts` exists to work around.

    Rows that cannot be parsed are dropped, not zero-filled: a zero row is a
    price of 0.0 and would print as a candle collapsing to the axis.
    """
    rows = []
    for c in candles or []:
        if not isinstance(c, (list, tuple)) or len(c) < 6:
            continue
        try:
            ts = datetime.fromisoformat(str(c[0]))
        except ValueError:
            continue
        vals = [_num(x) for x in c[1:5]]
        if any(v is None for v in vals):
            continue
        rows.append((ts.timestamp(), *vals, _num(c[5]) or 0.0,
                     _num(c[6]) if len(c) > 6 else 0.0))
    rows.sort(key=lambda r: r[0])                # oldest first, always
    out = {k: [] for k in CANDLE_FIELDS}
    for r in rows:
        for name, v in zip(CANDLE_FIELDS, r):
            out[name].append(int(v) if name == "timestamp" else v)
    return out
