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
    the FULL book   <- marketLevel.bidAskQuote[] + tbq / tsq, via
                       `depth_ladder` -- full mode only, and deliberately NOT
                       in the chain payload: `chain_live._side` builds its
                       result key by key, so a `depth` field added to the
                       payload would be dropped there in silence. A ladder
                       consumer reads `depth_ladder(feed)` off
                       `upstox_feed.snapshot()` directly, which is also the
                       only way to reach the FUTURE's book -- its key is
                       subscribed but `upstox_chain.poll` reads only the
                       index's ltp from that frame.
    gamma / delta   <- optionGreeks.gamma / .delta
    avg             <- atp         ** full mode only **
    oi_chg          <- NOTHING. See below.

WHY `full` AND NOT `option_greeks`. `option_greeks` omits `atp`, which is the
chain's `avg`. `full` is a superset -- it adds atp, tbq/tsq and the depth
book -- and its subscription cap (2000 keys) is far above the ~40 this tool
needs.

HOW DEEP, AND WHY THE NUMBER LOOKS DIFFERENT DEPENDING ON WHO IS COUNTING.
`full` sends FIVE `Quote` structs, and each one carries a bid AND an ask -- so
it is five levels a side, TEN PRICE LEVELS in total. Upstox's docs count the
structs and say "5 market level quotes"; Kite's packet counts the prices and
says "10 depth entries". Same book, two conventions, and NSE market-by-price
is five deep per side either way. Measured 2026-08-20 on NIFTY AUG FUT: five
entries, ten prices, nothing truncated. `full_d30` (Upstox Plus, 50 keys) is
the only mode that goes deeper -- thirty structs, sixty prices.

**`oi_chg` HAS NO SOURCE IN THE SOCKET AND IS NOT INVENTED HERE.** Dhan ships
`previous_oi` (the PRIOR SESSION'S CLOSING open interest) and `chain_live._side`
derives the change from it. Upstox's *feed* carries current `oi` only. So
`prev_oi` is an argument: pass a baseline per (strike, side) and `oi_chg` is
real. Pass nothing and this module emits `previous_oi = None`, which `_side`
reads as a change of 0 -- honestly "not known", never a guess. What must NOT
happen is baselining against whatever OI happened to arrive when the process
started: that makes `oi_chg` mean "since we connected", a different quantity
wearing the same name, and every writer score and wall built on it would be
wrong with nothing downstream able to notice.

**Where the baseline comes from: the intraday candles.** Measured 2026-08-05,
NIFTY 24700 CE 11-Aug -- the option candle series carries open interest on
160 of 160 bars, back to the 09:15 bar. So `session_open_oi` reads the
baseline out of the same response the tape already needs; no extra per-strike
fetch, and no separate cache to go stale.

That baseline is TODAY'S OPEN, not the prior close, and the two are not the
same number. The 09:15 bar carries the pre-open auction (measured volume
3,810,885 against ~240,000 on a normal bar), so its OI already includes
positions built before the continuous session. Consequences, both deliberate:

  * `oi_chg` here means "since today's open" and will NOT match the "OI Chg"
    column on a broker's option chain, which is measured from the prior close.
  * It is the better number for this tool anyway -- the writer score is asking
    what was positioned TODAY, not what was carried overnight.

Anyone who needs the broker-matching figure must fetch the previous session's
closing OI per strike; that is a real extra call per strike per day and is
deliberately not done here.

Do not assume OI only rises. Measured the same day, the 24700 PE reached
4,050,410 and was back at 3,283,735 by 11:54 -- real unwinding, mid-session.
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


def _levels(core):
    """The bid/ask ladder as the socket sent it, best level first.

    `option_greeks` carries one level as `firstDepth`; `full` carries five
    (a side) as `marketLevel.bidAskQuote`. Index 0 is the top of book in both,
    an
    assumption `_depth` has always rested on, written down now that it has a
    second caller.
    """
    if not isinstance(core, dict):
        return []
    q = core.get("firstDepth")
    if q:
        return [q]
    return (core.get("marketLevel") or {}).get("bidAskQuote") or []


def _depth(core):
    """(bid, ask) at the top of book, whichever mode produced the feed."""
    levels = _levels(core)
    q = levels[0] if levels else {}
    return _num(q.get("bidP")), _num(q.get("askP"))


def depth_ladder(feed):
    """One `full` Feed -> the whole order book it was already carrying.

    WHY THIS EXISTS. `full` mode ships five levels a side -- ten price levels,
    as five Quote structs each holding one bid and one ask -- plus the
    session's total buy and sell quantity. `upstox_proto` decodes all of it,
    and until now `_depth` kept the top level and dropped the rest. The
    microstructure
    reads this tool wants -- one aggressive order taking out several levels at
    once, a level refilling after it is consumed, one side's book being pulled
    before a move -- are differences between consecutive snapshots of exactly
    those levels. The data was already arriving; only the discard was in the
    way. Nothing new is subscribed and no extra request is made.

        {"bid": [{"price": .., "qty": ..}, ...],   # best first
         "ask": [ ... ],                           # best first
         "bid_qty": total DISPLAYED bid quantity,
         "ask_qty": total DISPLAYED ask quantity,
         "tbq":     exchange-wide total buy qty,  or None,
         "tsq":     exchange-wide total sell qty, or None}

    EMPTY LEVELS ARE DROPPED, NOT ZEROED. A thin book pads its unused levels
    with zeros. Counting those keeps `bid_qty` honest but makes the ladder a
    lie -- a zero-priced level reads downstream as size resting at 0, which is
    a price the instrument can never trade at. A level is kept only when its
    price is a real non-zero number, so `len(bid)` counts real levels and a
    book genuinely thinning out shows up as that count falling.

    `tbq`/`tsq` exist in `full` ONLY, and come back None under
    `option_greeks` -- never 0, because "not subscribed" and "nobody is
    bidding" must not render the same. The rule `oi_chg` already follows.

    Returns None when the feed carries no book at all, which is what an index
    feed looks like, so a caller can tell "no depth here" from "an empty
    book". Do not read None as a flat market.

    Pure: a function of one decoded frame. No socket, no token, no clock --
    the feed's staleness is `upstox_feed.age()`'s job, and a ladder built from
    a frozen frame looks exactly like a calm one.
    """
    core = _core(feed)
    if not core:
        return None
    levels = _levels(core)
    if not levels:
        return None
    bid, ask = [], []
    for q in levels:
        if not isinstance(q, dict):
            continue
        bp, ap = _num(q.get("bidP")), _num(q.get("askP"))
        if bp:
            bid.append({"price": bp, "qty": _num(q.get("bidQ")) or 0.0})
        if ap:
            ask.append({"price": ap, "qty": _num(q.get("askQ")) or 0.0})
    return {"bid": bid, "ask": ask,
            "bid_qty": sum(l["qty"] for l in bid),
            "ask_qty": sum(l["qty"] for l in ask),
            "tbq": _num(core.get("tbq")), "tsq": _num(core.get("tsq"))}


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


def session_open_oi(candles):
    """Open interest on the session's FIRST bar -- the `oi_chg` baseline.

    Read from the candles the tape already fetches, so a baseline costs no
    extra request. Returns None when the series carries no usable OI, which
    keeps `oi_chg` at "not known" instead of turning a missing baseline into
    a change equal to the whole book.

    This is TODAY'S OPEN, and it is not the prior close -- the 09:15 bar
    includes the pre-open auction. See the module docstring; the difference is
    deliberate and has to stay visible wherever the number is shown.
    """
    arrays = candles_to_arrays(candles)
    ois = arrays["open_interest"]
    return ois[0] if ois and ois[0] else None


