"""hold2.py -- HOLD v2: the push trail, the profit lock and FADE -> RIDE at VWAP (research-findings §1m).

THE BINDING TEXT is docs/setup-review/HOLD-V2-PREREG.md (sha256 fca358a2...d9a6). Every number is that file's, fixed
before any outcome existed; none is to be tuned. Pure: no I/O, no clock. Causal: a read at a moment uses only bars closed
by then. A second exit scored BESIDE each setup's own (v1) on the same entries, and shown beside her hold window's word:
it never changes an entry, a v1 exit or the window's HOLD / FOLD. DESCRIPTIVE ONLY: no hit rate anywhere.

    PUSH    a closed 5-min futures bar whose SIZE (|delta| / the same 15-min slot's median |delta| on prior days) is at
            or above the reference's p90, not thin (volume at or under the slot's p10), with R = sign(delta) x
            (close - open) / the slot's median range >= 0.25. The extension's flowState PUSH (orderflow-desk
            src/engine/v2.js, v2.5), ported line for line in `state`; its table is rank_build.flow_ref's. Origin = the
            bar's OPEN; U = max(sigma at the bar, 0.1% of the origin), sigma being market.js vwapSeries over the same
            5-min bars -- the extension's push-fail unit, so the v2 line sits where her chart's PUSH line fails.
    LINE    starts at the setup's initial stop. Each PUSH of the trade's direction closing after entry, whose origin lies
            between the line and price, moves it to origin + 0.25U (DOWN; mirrored UP), only toward price. Once MFE
            >= 2R (initial risk) the line is never worse than the entry. Touched intrabar on 1-min bars, never a close.
    GAVE UP the trend-side front (DOWN: CE, UP: PE; fronts.read, §1d) UNWINDING at a 3-min close AND (AMENDMENT 1,
            §1m) price at that close on its writers' LOSING side of the price at the front's peak minute -- CE: the chain
            spot above the spot then; PE: below -- by more than 0.25U (AMENDMENT 2: the stack's break distance, U the
            line's own). Exit at that close. Unwinding with price still in the writers' favour is the winners taking
            profit: stamped "munafa booking"; inside the 0.25U buffer it is "munafa / chop"; neither is an exit, and an
            unread spot is never a verdict.
            STALLED is stamped, never an exit.
    15:20   marked at the 15:20 price.
    FADE    the first 1-min bar touching its own VWAP (§1i's target) is decided at that bar's 3-min close: RIDE's OI and
            FLOW (ride.oi_read / flow_read) in the FADE's own direction both ok -> no exit, the line restarts at
            VWAP + 0.5 sigma (DOWN) / - 0.5 sigma (UP), never worse than it was; otherwise the v1 exit at VWAP.

TIMES are IST minutes of the day (`hm` -> "HH:MM"); exits are named by the 1-min bar's END, as ride.py's are.
"""
from __future__ import annotations

import heapq
import math

import confluence
import fronts
import ride

REV = "hold2-1 (HOLD-V2-PREREG fca358a2)"
BIG, RES_MIN = 90, 0.25          # PUSH: SIZE >= p90 (v2.js V2.BIG) and R >= 0.25 (V2.RES_MIN)
TRAIL_U, U_MIN = 0.25, 0.001     # the line -> origin -/+ 0.25U; U = max(sigma, 0.1% of price)
LOCK_R, CONV_SIG = 2.0, 0.5      # breakeven once MFE >= 2R; FADE -> RIDE restarts at VWAP -/+ 0.5 sigma
OPEN_M, MARK = 9 * 60 + 15, ride.MARK
NO_REF = "push ? ref nahi"
hm = confluence.hm


def _sgn(x):
    return (x > 0) - (x < 0)


# ---- the push (the same definition live and in scoring) --------------------------------------------------------------

def sigmas(bars):
    """market.js vwapSeries' sigma at each bar: hlc3 (h/l mid, else c, for a bar without a candle), volume-weighted from
    the session's first bar; 0 before any volume."""
    pv = v = pv2 = 0.0
    out = []
    for b in bars:
        h, lo, c = b.get("h"), b.get("l"), b.get("c")
        tp = (h + lo + c) / 3 if None not in (h, lo, c) else (h + lo) / 2 if h is not None and lo is not None else c
        w = (b.get("vol") or 0) if tp is not None else 0
        if w:
            pv, v, pv2 = pv + tp * w, v + w, pv2 + tp * tp * w
        vw = pv / v if v else None
        out.append(math.sqrt(max(0.0, pv2 / v - vw * vw)) if v and vw is not None else 0.0)
    return out


def state(b, F):
    """v2.js flowState's SIZE gate for one bar against its own source's flow table F (rank_build.flow_ref): "PUSH",
    "CLIMAX", "?" (SIZE says big, R cannot be read) or None (neither -- the extension's ROKA / noise / no read)."""
    slot = str(b["s"] // 900)
    d, v = b.get("delta") or 0, b.get("vol") or 0
    m, rg, p10 = ((F.get(k) or {}).get(slot) for k in ("slot_absd", "slot_range", "slot_vp10"))
    size = abs(d) / m if m else None
    R = _sgn(d) * (b["c"] - b["o"]) / rg if b.get("o") is not None and b.get("c") is not None and rg else None
    thin = p10 is not None and v <= p10
    q = (F.get("size") or {}).get("q")
    th = q[BIG] if isinstance(q, list) and len(q) > BIG else None
    res = F.get("res_min") if F.get("res_min") is not None else RES_MIN
    st = None
    if size is not None and th is not None and size >= th and not thin:
        st = "?" if R is None else "PUSH" if R >= res else "CLIMAX"
    return {"state": st, "dir": _sgn(d), "size": size, "R": R, "thin": thin}


def pushes(bars5, refs):
    """Every PUSH bar of the session, oldest first. `bars5` = the closed 5-min bars in time order, each {s (sec of day
    of its open), o, h, l, c, vol, delta, src}; `refs` = {src: flow table}. A bar whose source has no table is never a
    push. -> [{"s", "t" (open "HH:MM"), "close" (IST minute it closed), "d", "origin", "c", "U", "size", "R", "src"}]"""
    out = []
    for b, sg in zip(bars5, sigmas(bars5)):
        F = (refs or {}).get(b.get("src"))
        f = state(b, F) if F else None
        if not f or f["state"] != "PUSH" or not f["dir"] or b.get("o") is None:
            continue
        out.append({"s": b["s"], "t": hm(b["s"] // 60), "close": b["s"] // 60 + 5, "d": f["dir"], "origin": b["o"],
                    "c": b["c"], "U": max(sg, U_MIN * b["o"]), "size": round(f["size"], 3), "R": round(f["R"], 3),
                    "src": b.get("src")})
    return out


def source_bars(gc, ux):
    """NIFTY's push bars (§ The push, Source): GoCharting's 5-min bar where it has one with a candle, delta and volume,
    the Upstox bar of the same slot only where GoCharting lacks one; each tagged with its source, so it is ranked only
    against that source's own history. `gc` / `ux` are rank.bars_of rows ({s, o, h, l, c, vol, delta}), None = absent."""
    def whole(b):
        return (b.get("o") is not None and b.get("c") is not None
                and isinstance(b.get("delta"), (int, float)) and isinstance(b.get("vol"), (int, float)))
    by = {b["s"]: dict(b, src="ux") for b in ux or () if whole(b)}
    by.update({b["s"]: dict(b, src="gc") for b in gc or () if whole(b)})
    return [by[s] for s in sorted(by)]


# ---- the v2 exit -------------------------------------------------------------------------------------------------------

def _why(src, mv=None, conv=None):
    if src == "push":
        dn = mv["d"] < 0
        return f"PUSH {'▼' if dn else '▲'} {mv['t']} origin {mv['origin']:,.0f}f {'+' if dn else '-'} 0.25U"
    if src == "lock":
        return "lock: breakeven after +2R"
    if src == "conv":
        return f"FADE → RIDE {conv['t']}: VWAP {'+' if conv['d'] < 0 else '-'} 0.5σ"
    return "initial"


def losing(d, spot, peak_spot, U):
    """Which side of their peak minute's price the trend-side writers are on. AMENDMENT 1: CE (a DOWN position) lose when
    spot is above it, PE (UP) when below; AMENDMENT 2: only beyond it by 0.25U (TRAIL_U, the stack's break distance;
    U = max(sigma, 0.1% of price), the line's own). -> "lose" (beyond the buffer: gave up), "chop" (the losing side but
    within 0.25U), "munafa" (level, or still in their favour), or None when a spot or U is unread (never a verdict)."""
    if spot is None or peak_spot is None or U is None:
        return None
    x = (spot - peak_spot) if d < 0 else (peak_spot - spot)            # > 0: the writers' losing side
    return "lose" if x > TRAIL_U * U else "chop" if x > 0 else "munafa"


def close_read(d, chain, k, c, sigma=None):
    """One 3-min close's read for the v2 exit: the trend-side front at the close's last minute (fronts.read on the grid cut
    there, §1d), its peak minute (fronts.read's peak_at, on that cut), the chain spot at the close's last minute and at
    the peak minute, U = max(sigma, 0.1% of the spot) -- `sigma` the 5-min vwapSeries sigma at the close (sigma_at), the
    line's own; none closed yet is 0, as in pushes -- and which side the writers are on (losing). `c` is the close's
    futures price (the gave-up exit price)."""
    at = hm(k - 1)
    cut = fronts.cut(chain[0], at)
    stale = fronts.stale(cut, at)
    f = None if stale else fronts.side_front(fronts.read(cut, confluence._upto(chain[1], at)), "CE" if d < 0 else "PE")
    now = confluence._upto(cut, at) if cut else None
    spot = (now or {}).get("spot")
    peak_spot = (cut.get(f["peak_at"]) or {}).get("spot") if f and f.get("peak_at") else None
    U = None if spot is None else max(sigma or 0.0, U_MIN * spot)
    return {"c": c, "trend_state": f["state"] if f else None, "k": f["k"] if f else None,
            "peak_at": f.get("peak_at") if f else None, "spot": spot, "peak_spot": peak_spot,
            "U": None if U is None else round(U, 2), "price": losing(d, spot, peak_spot, U) if f else None,
            "why": stale or (None if f else f"no {'CE' if d < 0 else 'PE'} front read at {at}")}


def sigma_at(bars5, k):
    """The 5-min vwapSeries sigma (sigmas(), the line's U) of the last 5-min bar CLOSED by minute k, or None."""
    sg = [s for b, s in zip(bars5 or (), sigmas(bars5 or ())) if b["s"] // 60 + 5 <= k]
    return sg[-1] if sg else None


def closes(d, start, b3, chain, bars5=None):
    """{close minute: close_read(...)} for every 3-min close after `start` up to 15:20; b3 = [{"e" (sec), "c"}], bars5 =
    the push source bars (their sigma makes U). Each close reads only the chain minutes and 5-min bars closed by then."""
    return {b["e"] // 60: close_read(d, chain, b["e"] // 60, b["c"], sigma_at(bars5, b["e"] // 60))
            for b in b3 or () if start < b["e"] // 60 <= MARK}


def exit_v2(d, tr, start, ones, pushes_, closes, target=False, convert=None, end=None, trail_why=None):
    """The v2 exit for a position in direction d, the first of THE LINE (intrabar on 1-min bars), SOMEBODY GAVE UP (the
    trend front UNWINDING at a 3-min close with price on its writers' losing side of their peak minute's price, Amendment
    1: exit at that close) and 15:20.

    tr        {"E", "line0"}: the entry price and the initial line (FADE's stop, RIDE's line0, her window's
              invalidation). R is on |line0 - E| throughout.
    start     the entry close (IST minute); the trade's 1-min bars are those labelled >= start.
    ones      1-min futures bars {s, h, l, c} (+ "vwap" when `target`), oldest first.
    pushes_   pushes(...) rows, or None when the push trail is inactive (`trail_why` says why).
    closes    {IST minute: {"c", "trend_state", "k", "peak_at", "spot", "peak_spot"}} at each 3-min close (closes()).
    target    FADE: the first 1-min bar touching its own VWAP is decided at that bar's 3-min close, by convert(close) ->
              fade_convert(...), called then and only then (causal): not ok -> the v1 exit at that VWAP; ok -> held, the
              line restarted. Until the close the position is held with the line live; a line touch in between is the
              exit only if it converts. A bar touching the line and VWAP is the line first (v1's rule); a touch whose
              close falls after 15:20 cannot be checked: the v1 exit stands.
    end       live: the first minute not yet closed; nothing fired by then -> how "open", the line as it stands.
    -> {"exit", "how" (line_init / line_push / line_lock / line_conv / gave_up / mark / vwap / open), "exit_t", "R",
        "line0", "line", "line_src", "line_why", "moves", "n_moves", "lock_t", "converted", "stalled", "munafa"
        (unwinding with price still in the writers' favour: stamped, never an exit), "unwind_cnc" (unwinding, price side
        unread), "mfe", "mae", "trail"} or None when no bar was ever read."""
    E, line = tr["E"], tr["line0"]
    risk = abs(line - E) or None
    src, why = "init", _why("init")
    moves, stalled, munafa, unread, conv, pend = [], [], [], [], None, None
    mfe = mae = lock_t = last = ex = None
    ev = [(k, 1, n, None) for n, k in enumerate(sorted(closes or {})) if k > start]
    ev += [(p["close"], 2, n, p) for n, p in enumerate(pushes_ or ()) if p["close"] > start and p["d"] == d]
    heapq.heapify(ev)
    toward = (lambda a, b: a < b) if d < 0 else (lambda a, b: a > b)        # a is nearer price than b

    def decide(k):
        """FADE -> RIDE at the touch bar's close k: an exit tuple, or None (converted: the line restarts)."""
        nonlocal line, src, why, conv, pend
        v = convert(k) if convert else None
        conv = dict(v or {}, touch_t=pend["touch_t"], d=d, ok=bool(v and v.get("ok")))
        if not conv["ok"]:
            return pend["vw"], "vwap", pend["touch_t"]            # the v1 exit at VWAP stands
        hit, pend = pend.get("hit"), None
        if hit:
            return hit
        if toward(conv["line"], line):                            # never worse than the line it had
            line, src, why = conv["line"], "conv", _why("conv", conv=conv)
        return None

    def fire(upto):
        nonlocal line, src, why
        while ev and ev[0][0] <= upto:
            k, kind, _n, x = heapq.heappop(ev)
            if kind == 0:
                got = decide(k)
                if got:
                    return got
            elif kind == 1:
                c = closes[k]
                if c.get("trend_state") == fronts.UNWINDING:
                    side = losing(d, c.get("spot"), c.get("peak_spot"), c.get("U"))
                    if side == "lose":
                        return c["c"], "gave_up", hm(k)
                    if side is None:
                        unread.append(hm(k))                       # the price side could not be read: never a verdict
                    else:                                          # the winners taking profit (A1) / chop (A2)
                        munafa.append({"t": hm(k), "k": c.get("k"), "spot": c.get("spot"), "peak_spot": c.get("peak_spot"),
                                       "peak_at": c.get("peak_at"), "U": c.get("U"), "read": side})
                elif c.get("trend_state") == fronts.STALLED:
                    stalled.append(hm(k))
            else:
                px = last["c"] if last else x["c"]
                new = x["origin"] + TRAIL_U * x["U"] if d < 0 else x["origin"] - TRAIL_U * x["U"]
                if toward(px, x["origin"]) and toward(x["origin"], line) and toward(new, line):
                    moves.append({"t": x["t"], "at": hm(k), "origin": x["origin"], "U": round(x["U"], 2),
                                  "from": round(line, 2), "to": round(new, 2), "src": x["src"]})
                    line, src = new, "push"
                    why = _why("push", dict(x, d=d))
        return None

    for b in ones or ():
        m = b["s"] // 60
        if m < start:
            continue
        if m >= MARK or (end is not None and m >= end):
            break
        ex = fire(m)
        if ex:
            break
        last = b
        fav, adv = ((E - b["l"]), (b["h"] - E)) if d < 0 else ((b["h"] - E), (E - b["l"]))
        mfe, mae = max(fav, mfe if mfe is not None else fav), max(adv, mae if mae is not None else adv)
        if (b["h"] >= line) if d < 0 else (b["l"] <= line):
            ex = (line, "line_" + src, hm(m + 1))
            if pend:                                               # held for the decision: it decides which exit
                pend["hit"] = ex
                ex = fire(pend["k"]) if end is None or pend["k"] <= end else (None, "open", None)
            break
        vw = b.get("vwap")
        if target and conv is None and pend is None and vw is not None and ((b["l"] <= vw) if d < 0 else (b["h"] >= vw)):
            pend = {"k": OPEN_M + ((m - OPEN_M) // 3 + 1) * 3, "vw": vw, "touch_t": hm(m + 1)}   # the touch bar's close
            heapq.heappush(ev, (pend["k"], 0, -1, None))
        if risk and lock_t is None and mfe >= LOCK_R * risk:
            lock_t = hm(m + 1)
            if toward(E, line):
                line, src, why = E, "lock", _why("lock")
        ex = fire(m + 1)
        if ex:
            break
    if ex is None and end is not None and end < MARK:
        ex = fire(end) or (None, "open", None)
    if ex is None and pend:                                        # its close falls after 15:20: never checked
        conv = {"ok": False, "touch_t": pend["touch_t"], "d": d, "why": "the touch's 3-min close is after 15:20"}
        ex = (pend["vw"], "vwap", pend["touch_t"])
    if ex is None:
        if last is None:
            return None
        ex = (last["c"], "mark", hm(last["s"] // 60 + 1))
    R = None if ex[0] is None or not risk else round(((E - ex[0]) if d < 0 else (ex[0] - E)) / risk, 4)
    return {"exit": None if ex[0] is None else round(ex[0], 4), "how": ex[1], "exit_t": ex[2], "R": R,
            "line0": tr["line0"], "line": round(line, 2), "line_src": src, "line_why": why, "moves": moves,
            "n_moves": len(moves), "lock_t": lock_t, "converted": conv, "stalled": stalled, "munafa": munafa,
            "unwind_cnc": unread,
            "mfe": None if mfe is None else round(mfe, 2), "mae": None if mae is None else round(mae, 2),
            "trail": trail_why if pushes_ is None else None}


def fade_convert(d, close, vwap, sigma, chain, book, gc=None):
    """FADE -> RIDE at VWAP: at the VWAP-touch bar's 3-min close (IST minute), RIDE's OI ✓ and FLOW ✓ (§1j, ride.oi_read /
    flow_read) in the FADE's own direction. "If both hold" is both True: a "could not check" is not a hold. The restart
    line is VWAP + 0.5 sigma (DOWN) / - 0.5 sigma (UP) from the 3-min bar closing there. `chain` = confluence.chain_grid,
    `book` = confluence.book_flow, `gc` = NIFTY's GoCharting bars."""
    oi = ride.oi_read(d, chain[0], chain[1], hm(close - 1))
    fl = ride.flow_read(d, book, close, gc)
    line = None if vwap is None or not sigma else vwap + CONV_SIG * sigma if d < 0 else vwap - CONV_SIG * sigma
    return {"ok": oi["ok"] is True and fl["ok"] is True and line is not None, "t": hm(close), "oi": oi, "flow": fl,
            "vwap": vwap, "sigma": sigma, "line": None if line is None else round(line, 2)}


# ---- her hold window (display only) --------------------------------------------------------------------------------

def bars3(ones):
    """1-min bars -> their 3-min closes on the 09:15 grid, [{"e" (sec), "c"}]: the last 1-min close inside each."""
    out = {}
    for b in ones or ():
        k = OPEN_M + ((b["s"] // 60 - OPEN_M) // 3 + 1) * 3
        out[k] = b["c"]
    return [{"e": k * 60, "c": c} for k, c in sorted(out.items())]


def front_now(d, chain, now_m, sigma=None):
    """The trend-side front as the window shows it at minute `now_m` (read at its last closed minute, the same read as a
    close): {"side", "k", "state", "price" (losing()), "U", "why"}; `sigma` = sigma_at(bars5, now_m)."""
    r = close_read(d, chain, now_m, None, sigma)
    return {"side": "CE" if d < 0 else "PE", "k": r["k"], "state": r["trend_state"], "price": r["price"], "U": r["U"],
            "why": r["why"]}


def front_words(d, f):
    """The front in the window's words. UNWINDING says whose profit it is (Amendment 1): "CE 23000 munafa booking
    (unwinding, price still neeche)" while the writers are winning, "... munafa / chop (within 0.25U)" inside the buffer
    (Amendment 2), "... gave up (unwinding, price upar)" beyond it."""
    side = f.get("side") or ("CE" if d < 0 else "PE")
    if not f.get("state"):
        return f"{side} front ?"
    if f["state"] != fronts.UNWINDING:
        return f"{side} front {f['state']}"
    k = "" if f.get("k") is None else f" {f['k']:.0f}"
    favour, against = ("neeche", "upar") if d < 0 else ("upar", "neeche")
    p = f.get("price")
    if p is None:
        return f"{side}{k} UNWINDING (price side ?)"
    if p == "lose":
        return f"{side}{k} gave up (unwinding, price {against})"
    if p == "chop":
        return f"{side}{k} munafa / chop (within 0.25U)"
    return f"{side}{k} munafa booking (unwinding, price still {favour})"


def short_why(src, moves=None):
    """The line's reason in one chip: "PUSH ▼ 12:20" / "lock BE" / "FADE→RIDE" / "initial"."""
    if src == "push" and moves:
        return f"PUSH {'▼' if moves[-1]['to'] > moves[-1]['origin'] else '▲'} {moves[-1]['t']}"
    return {"lock": "lock BE", "conv": "FADE→RIDE"}.get(src, "initial")


def window_line(d, E, line0, start, ones, pushes_, closes, end, fut, basis, front, trail_why=None, entry_t=None):
    """The hold window's HOLD v2 block for her open trade. Her trade is no setup entry, so the line starts at the
    window's own invalidation (`line0`, a futures price) and the push trail and the lock run from her entry (`start`
    minute, `E`). Two reads of exit_v2: the LINE alone (it keeps trailing while she holds, until touched) and the whole
    rule, whose SOMEBODY GAVE UP is stamped beside it ("v2 out hh:mm gave up"). `basis` = future minus the index (the
    window's basis_ix: spot = fut - basis); `front` = front_now(...). Display only: it never changes the word."""
    out = {"rev": REV, "d": d, "E": E, "line0": line0, "tag": "I", "ok": False, "text": None,
           "note": (f"her trade · line from the window's inval {line0:,.0f}f · push trail + lock from her entry "
                    f"{entry_t or hm(start)} @ {E:,.0f}f · display only")}
    tside = "CE" if d < 0 else "PE"
    out.update(front=front, front_why=(front or {}).get("why"))
    fr = front_words(d, front or {})
    tr = {"E": E, "line0": line0}
    q = exit_v2(d, tr, start, ones, pushes_, {k: dict(c, trend_state=None) for k, c in (closes or {}).items()},
                end=end, trail_why=trail_why)
    r = exit_v2(d, tr, start, ones, pushes_, closes, end=end, trail_why=trail_why)
    if q is None:
        out["why"] = "could not check — no 1-min futures bar since her entry yet"
        return out
    line = q["line"]
    sp = None if basis is None else round(line - basis, 1)
    pts = None if fut is None else round((line - fut) if d < 0 else (fut - line))
    gave = r["exit_t"] if r and r["how"] == "gave_up" else None
    out.update(ok=True, line_fut=line, line_spot=sp, line_src=q["line_src"], why=q["line_why"],
               why_short=short_why(q["line_src"], q["moves"]), pts=pts, moves=q["moves"], lock_t=q["lock_t"],
               how=q["how"], touched_t=q["exit_t"] if q["how"].startswith("line_") else None, gave_up_t=gave,
               munafa=r["munafa"] if r else [], trail=q["trail"], mfe=q["mfe"],
               # the whole rule's exit as it stands (how "open" until one fires): the hold shadow lines pair with it
               v2_exit=None if r is None else {"how": r["how"], "t": r["exit_t"], "px": r["exit"], "R": r["R"]})
    at = f"{'?' if sp is None else f'{sp:,.0f}'}s|{line:,.0f}f"
    touched = out["touched_t"]
    parts = ["HOLD v2", f"line {at}" + (f" touched {touched}" if touched else "") + f" ({out['why_short']})"]
    if q["how"] == "open":
        parts.append(f"{'?' if pts is None else pts} pts")
    elif q["how"] == "mark":
        parts[1] = f"15:20 · line was {at} ({out['why_short']})"
    parts.append(fr)
    if gave or touched:
        parts.append(f"v2 out {gave} ({tside} gave up)" if gave and (not touched or gave <= touched)
                     else f"v2 out {touched} (line)")
    if trail_why and pushes_ is None:
        parts.append(trail_why)
    out["text"] = " · ".join(parts)
    return out


def live(tr, view, now_m, bars1, chain_rows, bars5, refs, trail_why, cache):
    """window_line from the live server's memory, for her marked trade `tr` (server._hold_trade's record) and the fold
    engine's view of it: d and E are the engine's, the line starts at her thesis invalidation, else the engine's give-up G
    (the window's own `inval`, validate_live's rule). `bars1` = the engine's 1-min futures bars (ladder rows, t in ms),
    `chain_rows` = its chain rows, `bars5` = confluence_log.push_bars(...), `refs` = push_refs' tables. `cache` carries
    the 3-min closes' reads across calls: a close is read once, a minute after it (its last bar and chain minute are in by
    then), and never again. Reads `view`, never writes it: the window's word is untouched."""
    d, E = view.get("d"), view.get("E")
    th = tr.get("thesis") or {}
    line0 = th.get("inval") if th.get("inval") is not None else (view.get("G") or {}).get("px")
    if d not in (1, -1) or E is None or line0 is None:
        return {"ok": False, "tag": "I", "text": None, "why": "could not check — " + (
            "the window has no invalidation yet" if line0 is None else "the engine has no entry future yet")}
    h, mi = (int(x) for x in str(tr["t0"]).split(":")[:2])
    start = h * 60 + mi + 1                                   # the first whole minute after her entry
    ones = [{"s": (int(b["t"]) // 1000 + 19800) % 86400, "h": b["h"], "l": b["l"], "c": b["c"]}
            for b in bars1 or () if b.get("h") is not None and b.get("t") is not None]
    chain = confluence.chain_grid(chain_rows)
    for b in bars3(ones):
        k = b["e"] // 60
        if start < k < min(now_m, MARK + 1) and k not in cache:
            cache[k] = close_read(d, chain, k, b["c"], sigma_at(bars5, k))
    P = pushes(bars5, refs) if refs else None
    return window_line(d, E, line0, start, ones, P, cache, now_m, view.get("fut"),
                       (view.get("units") or {}).get("basis_ix"), front_now(d, chain, now_m, sigma_at(bars5, now_m)), trail_why,
                       str(tr["t0"])[:5])
