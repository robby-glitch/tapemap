"""effort.py -- EFFORT PER POINT (Kyle lambda) at a fresh extreme, for the DECODE block's EFFORT line (gap A44).

The only order-flow read that survived Fable's two holdouts (oi-lab/flow/AUDIT.md §3.1, rows 51-52 / 261-262):
  lots per point over the last 5 min >= 2x the day median at a fresh HIGH -> reversal   (75 % vs 60 % base, n 87)
  lots per point over the last 5 min <= 0.5x the day median at a fresh LOW -> continuation (77 % vs 54 % base, n 119)
The MIRRORS FAILED (row 263: >= 2x at a low, noise; row 260: <= 0.5x at a high, noise / inverted in-sample only), so
they read "read nahi", never a direction. NIFTY futures, 19 days (22 Sep - 22 Oct 2026): a HYPOTHESIS, tag [I].

THE DEFINITION IS FABLE'S, PORTED LINE FOR LINE (oi-lab/flow/proto/audit.py reads_extreme "lambda level", load_day's
fresh-extreme test; flowlab.load_book / flow_minutes; oi-lab/proto/detector.py leg_states / running_extreme) -- the
same data, window, median and "fresh extreme" test, no variant:
  minute m       IST minute of the book row's t (the 1-second futures book record, data/book/book_<IDX>_<day>)
  vol            the volume since the previous row (vtt - previous vtt, > 0 only) / the lot, in LOTS, on the row's minute;
                 rows without an ltp or a bid / ask level are skipped (flowlab.load_book)
  h / l          the minute's highest / lowest ltp
  lots/pt (lam)  sum vol over minutes m-4..m / (max h - min l over them)
  day median     median of the same over the 5-minute blocks ending 09:25, 09:30, ... strictly before m-5, those with a
                 range; needs >= 6 of them (so the first read is 09:56)
  fresh extreme  on the chain recorder's spot (the last spot of each minute): the causal zigzag at 0.18 % of the first
                 spot (detector.THR_PCT) -- spot within 0.25 strike step of the leg's extreme set <= 5 min ago, on a
                 confirmed leg -- else within 0.25 step of the 30-min running high / low set <= 5 min ago
Causal: read() uses minutes <= `upto` only. NIFTY and BANKNIFTY only (A25: SENSEX futures are too thin); BANKNIFTY
was never in Fable's test, and its line says so. DISPLAY ONLY: no gate, no sign of the 7-sign call, no hit rate. Pure.
"""
from __future__ import annotations

import statistics

STEP = {"NIFTY": 50, "BANKNIFTY": 100}     # oilab.STEP; an index not here is not read (SENSEX: A25)
THR_PCT, FRESH, TOL_STEPS, N = 0.0018, 5, 0.25, 30   # detector.py
OPEN_M = 9 * 60 + 15                       # oilab.OPEN_MIN
HI, LO, MIN_HIST = 2.0, 0.5, 6             # audit.py's lambda level
RECENT = 30                                # display: an extreme older than Fable's 30-min verdict horizon is not shown
FIRST = "09:56"                            # the first minute with 6 blocks before m-5 (565..590 < m-5)
PASS_BAR = ("Fable AUDIT.md §1: lift >= +8 pts over the matched base in all four halves (CHRONO + ALT tune and "
            "holdout), n >= 20 and z >= 1.5 in both holdouts -- passed on NIFTY, 19 days; ~2-3 false survivors are "
            "expected from 291 trials, so a hypothesis judged forward, never an edge")
WORDS = {("H", "hi"): "mehenga (palat?)", ("L", "lo"): "sasta (aur girega?)",
         ("H", "lo"): "sasta · read nahi", ("L", "hi"): "mehenga · read nahi"}   # the mirrors failed


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def minutes(rows, lot):
    """{minute: {"vol": lots, "h", "l"}} from the book record's rows (flowlab.load_book + flow_minutes' vol / h / l)."""
    kept = sorted((r for r in rows or () if isinstance(r, dict) and isinstance(r.get("t"), (int, float))
                   and r.get("ltp") is not None and r.get("b") and r.get("a")), key=lambda r: r["t"])
    out, prev = {}, None
    for r in kept:
        m = int(r["t"] / 1000 + 19800) % 86400 // 60
        p = r["ltp"]
        f = out.get(m)
        if f is None:
            f = out[m] = {"vol": 0.0, "h": p, "l": p}
        else:
            f["h"], f["l"] = max(f["h"], p), min(f["l"], p)
        if prev is not None:
            v = (r.get("vtt") or 0) - (prev.get("vtt") or 0)
            if v > 0:
                f["vol"] += v / lot
        prev = r
    return out


def leg_states(spot, thr):
    """detector.leg_states: {m: (dirn, ext_m, ext_p, last_pivot_p)}, the causal zigzag as known at each minute."""
    ms = sorted(spot)
    out, piv, dirn = {}, [], 0
    hi_m = lo_m = ms[0]
    hi_p = lo_p = spot[ms[0]]
    for m in ms:
        p = spot[m]
        if dirn == 0:
            if p > hi_p:
                hi_m, hi_p = m, p
            if p < lo_p:
                lo_m, lo_p = m, p
            if hi_p - lo_p >= thr:
                dirn = 1 if hi_m > lo_m else -1
                piv.append(lo_p if dirn == 1 else hi_p)
        elif dirn == 1:
            if p > hi_p:
                hi_m, hi_p = m, p
            elif p <= hi_p - thr:
                piv.append(hi_p)
                dirn, lo_m, lo_p = -1, m, p
        else:
            if p < lo_p:
                lo_m, lo_p = m, p
            elif p >= lo_p + thr:
                piv.append(lo_p)
                dirn, hi_m, hi_p = 1, m, p
        last = piv[-1] if piv else None
        out[m] = (1, hi_m, hi_p, last) if dirn == 1 else (-1, lo_m, lo_p, last) if dirn == -1 else (0, None, None, None)
    return out


def running_extreme(spot, m, n=N):
    H = L = mH = mL = None
    for mm in range(m - n + 1, m + 1):
        p = spot.get(mm)
        if p is None:
            continue
        if H is None or p > H:
            H, mH = p, mm
        if L is None or p < L:
            L, mL = p, mm
    return H, mH, L, mL


def extremes(spot, step):
    """{minute: "H" | "L" | None}: audit.load_day's fresh-extreme test on the chain spot per minute."""
    if not spot:
        return {}
    ms = sorted(spot)
    thr = THR_PCT * spot[ms[0]]
    legs, tol, ext = leg_states(spot, thr), TOL_STEPS * step, {}
    for m in ms:
        dirn, em, ep, lastp = legs[m]
        S, k = spot[m], None
        if dirn == 1 and S >= ep - tol and m - em <= FRESH and lastp is not None and ep - lastp >= thr:
            k = "H"
        elif dirn == -1 and S <= ep + tol and m - em <= FRESH and lastp is not None and lastp - ep >= thr:
            k = "L"
        else:
            H, mH, L, mL = running_extreme(spot, m)
            if H is not None and S >= H - tol and m - mH <= FRESH:
                k = "H"
            elif L is not None and S <= L + tol and m - mL <= FRESH:
                k = "L"
        ext[m] = k
    return ext


def _stats(fm, m0, m1):
    """audit.leg_stats' volume and range over minutes m0+1..m1."""
    vol, hi, lo = 0.0, -1e9, 1e9
    for mm in range(m0 + 1, m1 + 1):
        f = fm.get(mm)
        if f:
            vol += f["vol"]
            hi, lo = max(hi, f["h"]), min(lo, f["l"])
    return vol, (hi - lo) if hi > lo else 0.0


def lam_at(fm, m):
    """(lots per point over m-4..m or None, the day median or None, blocks behind the median)."""
    v5, r5 = _stats(fm, m - 5, m)
    hist = []
    for mm in range(OPEN_M + 10, m - 5, 5):
        vv, rr = _stats(fm, mm - 5, mm)
        if rr > 0:
            hist.append(vv / rr)
    return (v5 / r5) if r5 > 0 else None, statistics.median(hist) if len(hist) >= MIN_HIST else None, len(hist)


def events(fm, spot, step):
    """Fable's lambda-level events, every minute: [(m, "H"|"L", "HI"|"LO")] -- HI = >= 2x the day median, LO = <= 0.5x
    (both ends and both mirrors; the test compares them with his harness's cached events)."""
    ext, out = extremes(spot, step), []
    for m in sorted(fm):
        k = ext.get(m)
        if not k:
            continue
        lam, med, _ = lam_at(fm, m)
        if lam and med is not None:
            if lam >= HI * med:
                out.append((m, k, "HI"))
            if lam <= LO * med:
                out.append((m, k, "LO"))
    return out


def blank(why, word="?"):
    return {"at": None, "t": None, "lpp": None, "x": None, "med": None, "word": word, "tag": "I", "why": why,
            "bar": PASS_BAR}


def _fired(f, m, k):
    """True when minute m's lambda is a SURVIVOR read: >= 2x at a fresh high, <= 0.5x at a fresh low."""
    lam, med, _ = lam_at(f, m)
    return bool(lam) and med is not None and (lam >= HI * med if k == "H" else lam <= LO * med)


def read(idx, fm, spot, upto):
    """decode.effort at the last closed minute `upto` (the DECODE close's bar is upto-4..upto): the latest fresh-extreme
    minute of that bar where a survivor fired, else the latest fresh-extreme minute within RECENT minutes, else the
    last 5 minutes with at = None. {at: "HIGH"|"LOW"|None, t, lpp, x, med, word, tag "I", why (None when read), bar}."""
    if idx not in STEP:
        return blank(f"not read — {idx} futures are too thin for a flow read (A25)", word="patla")
    sp = {m: p for m, p in (spot or {}).items() if m <= upto}
    f = {m: v for m, v in (fm or {}).items() if m <= upto}
    if not sp:
        return blank("could not check — no chain spot yet")
    if not f:
        return blank("could not check — no futures book row yet")
    ext = extremes(sp, STEP[idx])
    recent = [m for m in sorted(f, reverse=True) if m > upto - RECENT and ext.get(m)]
    hit = next((m for m in recent if m > upto - 5 and _fired(f, m, ext[m])), recent[0] if recent else None)
    m = upto if hit is None else hit
    lam, med, n = lam_at(f, m)
    out = blank(None)
    out.update(at=None if hit is None else {"H": "HIGH", "L": "LOW"}[ext[hit]], t=hm(m),
               lpp=None if lam is None else round(lam, 1), med=None if med is None else round(med, 1))
    if med is None:
        return dict(out, why=f"could not check — the day median needs {MIN_HIST} five-minute blocks (has {n}); "
                             f"from {FIRST}")
    if not lam:
        return dict(out, why="could not check — no price range or no volume in the last 5 minutes")
    x = lam / med
    out["x"] = round(x, 2)
    band = "hi" if x >= HI else "lo" if x <= LO else None
    if hit is None:
        out["word"] = "taaza high/low nahi"
    else:
        out["word"] = WORDS.get((ext[hit], band), "normal")
    return out
