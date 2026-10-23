"""faded.py -- FADE-D, the deceleration fade at an extreme (research-findings §1n).

THE BINDING TEXT is docs/setup-review/FADE-D-PREREG.md (sha256 3fd5e84e...f237, anchored in §1n). Every number is that
file's, round numbers fixed before any outcome existed; none is to be tuned. Mary, 21 Oct: "even though the market is
going up the strength declined ... cvd and delta as well in that zone started decline right at high". Her §1b zone rule
"front-runs the OI peak using build-rate deceleration", which §1i's FADE never encoded. A top is a SELL; a bottom is
the mirror BUY. Pure: no I/O, no clock. Causal: a reading at a close uses only bars closed and chain rows recorded by
then. DESCRIPTIVE ONLY: no hit rate anywhere. Where the text is not literal, tools/faded_score.py's READINGS say how.

    BARS     the closed 5-min futures bars of confluence_log.push_bars (hold2.source_bars): NIFTY GoCharting's, Upstox's
             only where GoCharting lacks the slot; BANKNIFTY / SENSEX Upstox's. {s (sec of day, open), o h l c, vol,
             delta, src}, oldest first.
    1 LOCATION  a 5-min bar that made a new session high (low) -- topping every earlier bar of a session whose record
             begins at 09:15; the 09:15 bar never -- or the bar holding the 3-min close of a zone-machine SELL (BUY) arm
             or entry (trigger_log). Same-side location bars, each closing within 30 min of the one before, are one
             EPISODE: one row, at most one entry. Its window runs from the first location's close to the last's + 30.
    2a FLOW  a new-high bar closing within the 30 min before the close has delta <= 25% of the largest positive-delta
             bar of its up-leg (from the bar holding the session low before it -- the open if none -- through itself).
    2b FLOW  at the close, the bar's delta < 0 and CVD (the running sum of the bars' delta) below its peak over the
             current up-leg (from the session low before the session-high bar, through the close).
    3 OI     the PE lead = 100 x (PE - CE) / (|PE| + |CE|) of today's writing (aaj likha) over read.writers' nine strikes,
             read at each 5-min close: >= 10 points under its session peak, AND the peak within the last 15 min OR a
             >= 10-point fall over the last 15 min. A bottom reads the CE lead (the negative).
    4 ENTRY  the first close of the episode's window with 1, 2a, 2b and 3 all true there, at or before 15:00.
             AMENDMENT 1 (§1n, before forward data): the VWAP side is NOT a condition -- HOLD v2 has no VWAP target,
             so "room to the target" had no job. It is a STAMP: every close's `px` and the entry's `vwap` (the close
             vs the session VWAP, market.js vwapSeries over the same bars).
    5 STOP   the session high + 0.25U (low - 0.25U), U = max(sigma, 0.1% of that extreme), sigma = hold2.sigma_at (the
             5-min vwapSeries sigma, HOLD v2's own unit); risk at least 0.5 sigma.
    6 EXIT   HOLD v2's exit section only (hold2.exit_v2, §1m as amended): the line from the stop (push trail, lock),
             gave up (Amendments 1-2) and 15:20. NO VWAP convert-or-exit decision: §1m's FADE -> RIDE clause belongs to
             §1i FADE entries, which FADE-D's are not (a reading, 2026-10-21). For reference, §1i's VWAP-target exit
             (confluence.outcome) -- "n/a" for an entry stamped across VWAP. The scorer's only: never on a row.

TIMES: IST minutes of the day. A bar is named by its OPENING minute ("bar": "09:35"), a reading and an entry by the
bar's CLOSE ("close" / "t": "09:40"). An episode's "t" is its first location bar's close.
"""
from __future__ import annotations

import bisect

import band_rotation
import confluence
import fronts
import hold2
import read

REV = "faded-1a (FADE-D-PREREG 3fd5e84e + §1n Amendment 1)"
RATIO = 0.25                      # 2a: a new extreme on <= 25% of the leg's biggest same-direction bar
LEAD_PTS, LEAD_MIN = 10.0, 15     # 3: 10 points off the session peak; the peak within 15 min, or a 10-point fall in 15
WINDOW = 30                       # 4: every condition within 30 min of the location bar
CUTOFF = 15 * 60                  # 4: no entry after 15:00
STOP_U, MIN_RISK = 0.25, 0.5      # 5: the extreme + 0.25U; risk at least 0.5 sigma
OPEN_M, BAR = 9 * 60 + 15, 5
hm = confluence.hm
_m = band_rotation._minute
CC = "could not check — "


def close(b):
    return b["s"] // 60 + BAR


def _bar(b):
    return hm(b["s"] // 60)


def _top(side):
    return side == "SELL"


# ---- the session's extremes and legs --------------------------------------------------------------------------------

def opened(bars5):
    """Why a new session extreme cannot be read (the record does not begin with the 09:15 bar), or None."""
    if not bars5:
        return CC + "no closed 5-min bar yet"
    return None if bars5[0]["s"] == OPEN_M * 60 else CC + f"the 5-min bars begin {_bar(bars5[0])}, not 09:15"


def extremes(bars5):
    """[(new high, new low)] per bar: its high tops (low undercuts) every earlier bar's. The first bar never."""
    out, hi, lo = [], None, None
    for b in bars5:
        h, l = b.get("h"), b.get("l")
        out.append((hi is not None and h is not None and h > hi, lo is not None and l is not None and l < lo))
        hi = h if hi is None or (h is not None and h > hi) else hi
        lo = l if lo is None or (l is not None and l < lo) else lo
    return out


def _arg(bars5, k0, k1, side, own=False):
    """The index of the latest bar in [k0, k1) holding the extreme: for a top the lowest low (the leg's start), or with
    own=True the highest high (the session high); a bottom mirrored. k0 when none can be read."""
    key = ("h" if _top(side) else "l") if own else ("l" if _top(side) else "h")
    lowest = (key == "l")
    best, bv = k0, None
    for k in range(k0, k1):
        x = bars5[k].get(key)
        if x is not None and (bv is None or (x <= bv if lowest else x >= bv)):
            best, bv = k, x
    return best


def ratio(bars5, n, side):
    """2a's reading for bar n: its delta / the largest same-direction delta of its leg (from the bar holding the session
    low before it -- high, for a bottom -- through itself). A leg without one has no effort to fade: ok, ratio None."""
    top = _top(side)
    k0 = _arg(bars5, 0, n, side) if n else 0
    w = [(b["delta"], b) for b in bars5[k0:n + 1] if (b["delta"] > 0 if top else b["delta"] < 0)]
    big = (max(w, key=lambda x: x[0]) if top else min(w, key=lambda x: x[0])) if w else None
    r = None if big is None else bars5[n]["delta"] / big[0]
    return {"bar": _bar(bars5[n]), "close": hm(close(bars5[n])), "delta": bars5[n]["delta"],
            "big": None if big is None else big[0], "big_bar": None if big is None else _bar(big[1]),
            "leg_from": _bar(bars5[k0]), "ratio": None if r is None else round(r, 3), "ok": True if r is None else r <= RATIO}


def cvd_turn(bars5, j, side):
    """2b at bar j's close: its delta against the move and CVD off its peak over the current leg (from the session low
    before the session-high bar as of j -- mirrored for a bottom -- through j)."""
    top = _top(side)
    H = _arg(bars5, 0, j + 1, side, own=True)
    k0 = _arg(bars5, 0, H, side) if H else 0
    cvd, run = [], 0
    for b in bars5[:j + 1]:
        run += b["delta"]
        cvd.append(run)
    pk = (max if top else min)(range(k0, j + 1), key=lambda k: (cvd[k], k) if top else (cvd[k], -k))
    d = bars5[j]["delta"]
    ok = (d < 0 and cvd[j] < cvd[pk]) if top else (d > 0 and cvd[j] > cvd[pk])
    return {"delta": d, "cvd": cvd[j], "peak": cvd[pk], "peak_close": hm(close(bars5[pk])), "leg_from": _bar(bars5[k0]),
            "dd": abs(cvd[pk] - cvd[j]), "ok": ok}


# ---- 3. the lead ------------------------------------------------------------------------------------------------------

def leads(X, closes):
    """{close minute: {"pe": the PE lead or None, "why"}} -- read.writers' nine strikes (ATM +/- 4 on the grid, narrowed
    at a window edge) on the last chain row before the close's second; a row more than fronts.STALE_MIN old, or a window
    read.writers cannot read, is "could not check". `X` = read.from_v2(...)'s dict."""
    out = {}
    for c in closes:
        sec = c * 60
        i = bisect.bisect_left(X.get("t") or [], sec) - 1
        if i < 0:
            out[c] = {"pe": None, "why": CC + f"no chain row before {hm(c)}"}
            continue
        if sec - X["t"][i] > fronts.STALE_MIN * 60:
            out[c] = {"pe": None, "why": CC + f"the last chain row is {read.hm(X['t'][i])}"}
            continue
        w = read.writers(X, i)
        if w.get("ce") is None:
            out[c] = {"pe": None, "why": w.get("why")}
            continue
        tot = abs(w["ce"]) + abs(w["pe"])
        out[c] = ({"pe": 100.0 * (w["pe"] - w["ce"]) / tot, "why": None} if tot
                  else {"pe": None, "why": CC + "no strike has written today yet"})
    return out


def lead_read(lead, c, side):
    """3 at close c on `lead` (leads()): SELL the PE lead, BUY the CE lead (its negative). The session peak is the highest
    of the 5-min reads so far (the latest on a tie); 15 min ago is the read at c - 15."""
    sg = 1 if _top(side) else -1
    val = lambda k: None if (lead.get(k) or {}).get("pe") is None else sg * lead[k]["pe"]     # noqa: E731
    now = val(c)
    out = {"side": "PE" if sg > 0 else "CE", "now": None, "peak": None, "peak_t": None, "ago15": None, "chg15": None,
           "off": None, "ok": None, "why": None}
    if now is None:
        out["why"] = (lead.get(c) or {}).get("why") or CC + f"no lead read at {hm(c)}"
        return out
    seen = [(val(k), k) for k in sorted(lead) if k <= c and val(k) is not None]
    pv, pk = max(seen)
    ago = val(c - LEAD_MIN)
    chg = None if ago is None else now - ago
    r1 = lambda v: None if v is None else round(v, 1)                                          # noqa: E731
    out.update(now=r1(now), peak=r1(pv), peak_t=hm(pk), ago15=r1(ago), chg15=r1(chg), off=r1(pv - now),
               ok=pv - now >= LEAD_PTS and (c - pk <= LEAD_MIN or (chg is not None and -chg >= LEAD_PTS)))
    return out


# ---- 1. location and the episodes -------------------------------------------------------------------------------------

def locations(bars5, zone, side):
    """One side's location bars: [{"j", "bar", "close", "why"}], "why" naming each reason ("high" / "low", "zone arm
    HH:MM", "zone entry HH:MM"). `zone` = trigger_log's zone rows ({"t" (3-min label), "side", "kind": "arm" | None})."""
    top = _top(side)
    out = {}
    if opened(bars5) is None:
        for j, (nh, nl) in enumerate(extremes(bars5)):
            if nh if top else nl:
                out.setdefault(j, []).append("high" if top else "low")
    slot = {b["s"] // 60: j for j, b in enumerate(bars5)}
    for z in zone or ():
        k = _m(z.get("t"))
        if z.get("side") != side or k is None:
            continue
        j = slot.get(OPEN_M + (k + 3 - 1 - OPEN_M) // BAR * BAR)       # the bar holding the 3-min close's last minute
        if j is not None:
            out.setdefault(j, []).append(f"zone {'arm' if z.get('kind') == 'arm' else 'entry'} {z['t']}")
    return [{"j": j, "bar": _bar(bars5[j]), "close": close(bars5[j]), "why": w} for j, w in sorted(out.items())]


def episodes(bars5, zone):
    """Every location episode of the session, both sides, oldest first: {"side", "t" (first close), "end", "locs"}."""
    out = []
    for side in ("SELL", "BUY"):
        cur = None
        for L in locations(bars5, zone, side):
            if cur and L["close"] - cur["locs"][-1]["close"] <= WINDOW:
                cur["locs"].append(L)
            else:
                cur = {"side": side, "locs": [L]}
                out.append(cur)
    for e in out:
        e["t"], e["end"] = hm(e["locs"][0]["close"]), e["locs"][-1]["close"] + WINDOW
    return sorted(out, key=lambda e: (e["locs"][0]["close"], e["side"]))


# ---- 4. the entry, 5. the stop ------------------------------------------------------------------------------------------

def vwaps(bars5):
    """market.js vwapSeries' VWAP at each bar (hold2.sigmas' recurrence): hlc3, volume-weighted from the first bar."""
    pv = v = 0.0
    out = []
    for b in bars5:
        h, lo, c = b.get("h"), b.get("l"), b.get("c")
        tp = (h + lo + c) / 3 if None not in (h, lo, c) else (h + lo) / 2 if h is not None and lo is not None else c
        w = (b.get("vol") or 0) if tp is not None else 0
        if w:
            pv, v = pv + tp * w, v + w
        out.append(pv / v if v else None)
    return out


def stamp(side, b, vw):
    """Amendment 1's stamp: the close against the session VWAP -- "far" = above for a SELL / below for a BUY (where §4
    once required it), "across" = the other side. Never a condition."""
    if vw is None:
        return {"c": b["c"], "vwap": None, "side": None}
    far = b["c"] > vw if _top(side) else b["c"] < vw
    return {"c": b["c"], "vwap": round(vw, 2), "side": "far" if far else "across", "pts": round(b["c"] - vw, 2)}


def trade(side, bars5, j):
    """The entry at bar j's close: E, the session extreme through j, sigma, U and the stop (§5)."""
    top = _top(side)
    c, E = close(bars5[j]), bars5[j]["c"]
    xs = [b.get("h" if top else "l") for b in bars5[:j + 1] if b.get("h" if top else "l") is not None]
    x = max(xs) if top else min(xs)
    sg = hold2.sigma_at(bars5, c) or 0.0
    U = max(sg, hold2.U_MIN * x)
    stop = max(x + STOP_U * U, E + MIN_RISK * sg) if top else min(x - STOP_U * U, E - MIN_RISK * sg)
    return {"t": hm(c), "bar": _bar(bars5[j]), "d": -1 if top else 1, "E": E, "extreme": x, "sigma": round(sg, 2),
            "U": round(U, 2), "stop": round(stop, 2)}


def evaluate(ep, bars5, lead):
    """The readings at every 5-min close of the episode's window and its entry (or None)."""
    side = ep["side"]
    top = _top(side)
    ext, vw, why0 = extremes(bars5), vwaps(bars5), opened(bars5)
    first = ep["locs"][0]["close"]
    rows, entry = [], None
    for j, b in enumerate(bars5):
        c = close(b)
        if not first <= c <= ep["end"]:
            continue
        loc = [L for L in ep["locs"] if L["close"] <= c][-1]
        if why0:
            a = {"ok": None, "why": why0, "bars": []}
        else:
            rs = [ratio(bars5, n, side) for n in range(1, j + 1)
                  if (ext[n][0] if top else ext[n][1]) and close(bars5[n]) >= c - WINDOW]
            a = {"ok": any(r["ok"] for r in rs), "bars": rs,
                 "why": None if rs else f"no new session {'high' if top else 'low'} in the 30 min to {hm(c)}"}
        px = {"c": b["c"], "vwap": None if vw[j] is None else round(vw[j], 2),
              "ok": None if vw[j] is None else (b["c"] > vw[j] if top else b["c"] < vw[j])}
        ev = {"close": hm(c), "bar": _bar(b), "loc": {"bar": loc["bar"], "why": loc["why"]}, "a": a,
              "b": cvd_turn(bars5, j, side), "oi": lead_read(lead or {}, c, side), "px": px, "late": c > CUTOFF}
        rows.append(ev)
        if entry is None and not ev["late"] and all(ev[k]["ok"] is True for k in ("a", "b", "oi")):
            entry = dict(trade(side, bars5, j), vwap=stamp(side, b, vw[j]))     # Amendment 1: a stamp, never a gate
    return {"bars": rows, "entry": entry}


def row(ep, bars5, lead):
    """The forward log's row (and the scorer's): everything known by the window's last close. NO OUTCOME."""
    ev = evaluate(ep, bars5, lead)
    return {"setup": "FADE-D", "side": ep["side"], "t": ep["t"], "end": hm(ep["end"]),
            "locs": [{"bar": L["bar"], "close": hm(L["close"]), "why": L["why"]} for L in ep["locs"]],
            "bars": ev["bars"], "entry": ev["entry"], "rev": REV}


# ---- 6. the exits (the scorer's only) -------------------------------------------------------------------------------------

def exits(entry, sess, chain, pushes_, bars5, trail_why=None):
    """HOLD v2 (its exit section only: no VWAP decision) and the reference VWAP-target exit of one entry. `sess` =
    confluence_log.session() (its 3-min "bars" and 1-min "ones", the live session VWAP on each), `chain` =
    confluence.chain_grid (gave up's fronts), `pushes_` = hold2.pushes(bars5, refs) or None (`trail_why`)."""
    d, start = entry["d"], _m(entry["t"])
    side = "BUY" if d > 0 else "SELL"
    if (entry.get("vwap") or {}).get("side") == "across":                   # its "target" lies behind the entry
        ref = {"how": "n/a (entry across VWAP)", "exit": None, "exit_t": None, "R": None}
    else:
        ref = confluence.outcome(side, {"E": entry["E"], "stop": entry["stop"]}, start, sess["ones"])
        if ref:
            ref = dict(ref, exit_t=hm(_m(ref["exit_t"]) + 1))              # its bar's END, as v2 names exits
    ones = [{"s": _m(b["t"]) * 60, "h": b["h"], "l": b["l"], "c": b["c"]} for b in sess["ones"] if _m(b.get("t")) is not None]
    by3 = {confluence.close_of(f["t"]): f for f in map(confluence.flat, sess["bars"])
           if confluence.close_of(f.get("t")) is not None}
    b3 = [{"e": k * 60, "c": f["c"]} for k, f in sorted(by3.items())]
    v2 = hold2.exit_v2(d, {"E": entry["E"], "line0": entry["stop"]}, start, ones, pushes_,
                       hold2.closes(d, start, b3, chain, bars5), target=False, trail_why=trail_why)
    return {"v2": v2, "vwap_ref": ref}
