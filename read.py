"""read.py -- THE READ: one HELD market read per index, the way a desk reads it. OI first.

Mary, 2026-10-08 after the close: "the day where almost no put writing and almost whole day is call writing its
a trend day ... it lacks intelligence ... make this tool a 10 on 10." The day test
(docs/review/DAY-TEST-2026-10-08.md) found the answer on the screen at 09:45 (GO down, trend box PUTS) and lost by
10:00: nine voices re-decided every 3 minutes and nothing held a thesis. A blind read cut at 09:45 -- one bias, one
flip line, targets, "wrong if" -- held all day and was right. This module is that structure, computed. It never
re-decides from scratch: a read stands until its own line breaks.

THREE FAMILIES, each a vote in {-1, 0, +1}, or None when it could not be read
  WRITERS [M] -> [I]  the nine strikes ATM +/- 4 on the strike grid (read-1.1, decode-loop D1: the recorder's window
                      was fixed at the opening ATM, so on a trend day "the nine nearest" became lopsided -- 8 Oct's
                      22,150-22,950 window with spot at 22,232). A missing strike narrows the window to ATM +/- m on BOTH
                      sides and the read says so; m < 2 is "could not check". aaj likha = OI now - OI at yesterday's close
                      (oi - oi_chg on the strike's first recorded row). A = (CE - PE) / (|CE| + |PE|).
                        CALL LIKH RAHE  A >= A_IN and CE adding                -> -1
                        PUT LIKH RAHE   A <= -A_IN and PE adding               -> +1
                        DONO LIKH RAHE  both adding, |A| < A_IN                -> 0 (the range candidate)
                        DONO CHHOD RAHE both falling                           -> 0
                        QUIET           |CE| + |PE| < ACT_MIN x the nine's close OI
  PRICE   [I]         daytype.py's raw bar read (VWAP-side run with size), the same raw on HOLD closed 5-min bars in
                      a row: TREND d -> d, PIN / TWO-SIDED -> 0.
  FLOW    [M]         the future's CVD since the open (v2feed's 1-s bars, quote rule): d when |CVD| >= FLOW_IN x volume.
                      On a late start, GoCharting's closed bars from the open fill the minutes before the first tick
                      (tape_log, the extension's own delta) -- chip says "HH:MM tak GC"; never a price, never re-sided.

THE WORD, at each closed 5-min mark from FORM_AT (09:45: the first 30 minutes are read, never named)
  TREND d   WRITERS = d, and PRICE = d or FLOW = d, and no family = -d
  LEAN d    WRITERS = 0, PRICE = d, FLOW = d                    (price and flow agree; the OI is not behind it yet)
  RANGE     DONO LIKH RAHE and PRICE = 0                        (sellers own both sides)
  WAIT      anything else
HELD -- the thesis memory. A TREND / LEAN d stands until, at a closed mark:
  (1) spot closes past FLIP by TOL x step,
  (2) the writers vote -d; or, for a TREND only, they give the asymmetry back: A < A_OUT (d < 0) / A > -A_OUT
      (d > 0). (A LEAN formed without the writers, so it has nothing to give back -- fixed 2026-10-08 ~19:40 after
      the first replay showed every LEAN breaking one mark after it formed: a logic error, no threshold changed.)
  (3) PRICE turns -d.
  LEAN d becomes TREND d when the writers join; a TREND is never downgraded while it holds. RANGE stands until a
  mark closes past a box wall by TOL x step, or a TREND / LEAN forms. A broken read is re-read at the same mark.
LEVELS (spot; fut = spot + basis, the median of the last 15 one-minute future-minus-spot pairs)
  FLIP  d < 0: the CE strike above spot (within EDGE steps) with the most aaj likha -- where today's call writers
        stand. It trails toward price, never away. d > 0: the mirror on PE below spot.
  T1/T2 the walls in the trade's way: d < 0, PE strikes below spot with total OI >= WALL_R x the biggest PE OI below
        spot, nearest first (mirror for d > 0). RANGE: the box is the biggest CE OI above and PE OI below (EDGE steps).
WARNINGS (amber, never a break): the FLIP strike's writers have given back GIVE of their peak aaj likha; in the last
  30 minutes the other side wrote more than the read's side.
EVENTS: QUIT -- a strike-side within QUIT_NEAR steps of spot whose aaj likha peaked at >= QUIT_BIG x the day's
  biggest single-strike add has fallen to <= QUIT_LEFT of its peak ("22,500 PE likhne wale bhage"). Once per
  strike-side per day. (QUIT_NEAR added 2026-10-08 ~20:00, before any forward row: on SENSEX's expiry afternoon CE
  writers 700+ pts above spot covered -- profit-taking, not a wall giving way. A wall is the line in the fire.)
The basis skips minutes after FREEZE (15:15): the spot indices freeze for the cash auction while the future trades.

READ-2 (docs/read/READ-2-PREREG.md, sha256 182aa67d...fb6ae, research-findings §1l; registered 2026-10-21 ~13:15 before
any replay of it; 21 Oct motivated it and is in-sample, never evidence). Two more votes at every closed mark:
  FUEL     [M]  rank.foi's 40 minutes on the Upstox 5-min bars: |futures OI change %| ranked by rank.by_part against the
                rank_ref's foi40 tables for the day's kind (rank.fuel_ref; the card's own ABHI rank). >= FUEL_P -> the sign
                of the 40-min futures price change (OI down + price down: long liquidation; OI up + price down: fresh
                shorts; covering / fresh longs the mirror); below -> 0; no reference or no OI on both ends -> None.
  LEG FLOW [M]  the leg from the session's spot extreme opposite to d (d < 0: the high) made before the mark, on 5-min
                bars of FLOW's own 1-s bars (GoCharting only before the first tick): S = the d-side bars' share of
                |delta|, M = their mean |delta| / the other side's (no other-side bar: M passes). d when >= LEG_N bars,
                S >= LEG_S and M >= LEG_M; else 0; a shorter leg, or one that began before the flow did, is None.
                d = the held TREND / LEAN's direction, else FLOW's vote.
  THE WORD      read-1.1's word and every HELD rule above run unchanged: the row's `word_r1`. A held LEAN d reads
                TREND d · flow+fuel (`src` "flow+fuel") from a mark where WRITERS = 0, PRICE = d, FLOW = d, the leg's
                latched FUEL = d and LEG FLOW = d; it drops back to LEAN (not a break, the read stands) only once LEG
                FLOW has failed to vote d at LEG_MISS marks in a row ("could not check" counts). It breaks as the LEAN it
                is; when the writers join it is read-1.1's TREND (`src` "writers").
  AMENDMENT 1   (research-findings §1l, 2026-10-21 ~14:10, before the forward check; persistence, no threshold moved.
                The literal "down when FUEL stops" flickered on 21 Oct NIFTY, in-sample: FUEL is a rolling 40-min burst.)
                FUEL is the TRIGGER, latched (_latch, the row's `fuel_leg`): a FUEL = d vote at any mark after the leg's
                extreme and from the read's own mark counts for the rest of that leg -- the biggest rank, and when. A
                new leg (a new session extreme against d) or a break / re-read resets it. FUEL fading never downgrades.
  JAGAH    [I]  display only, never a vote, never a probability: the room in the read's direction (the nearest of T1,
                the day's extreme, PDL / PDH and the round 100, more than step / 4 away; points and the session VWAP
                sigma), the obstacle behind (the nearest of FLIP, VWAP and -- on the card only, live -- the extension's
                last-push origin), the leg's latched fuel ("fuel ▼ long chhod rahe p97 @10:25"), the 40-min rank now
                ("abhi pNN") and LEG FLOW. RANGE: the two box walls; WAIT: "saaf nahi".

Thresholds fixed 2026-10-08 ~19:00 IST BEFORE any replay of this rule. The A measure itself was LOOKED AT on the
recorded sessions 2026-09-22 .. 2026-10-08 while choosing A_IN, so those days are in-sample (disclosed).
2026-10-09 onward is the forward check (data/read/read_<day>.jsonl). A change is a new REV with its date; never tune
a number here against what price did afterwards.

DISPLAY ONLY: gates nothing. The engine, the zone machine, the fade gate, signals and trigger_log are untouched.
Pure: stdlib + daytype, rank and frame_v2 (pure; imported where used, they import this). No I/O, no clock -- the caller hands in the day (v2feed's arrays), the 5-min bars,
yesterday's levels and `now`, so the same files give the same read whenever they are read (anytime-start).
"""
from __future__ import annotations

import bisect
import math
import statistics

import daytype

REV = "read-2 (2026-10-21)"       # READ-2: FUEL + LEG FLOW show a held LEAN as TREND · flow+fuel; JAGAH. read-1.1
                                  # (2026-10-19, D1: the nine are ATM +/- 4 on the grid) is every row's word_r1
FUEL_P, LEG_N, LEG_S, LEG_M = 80, 6, 0.70, 2.0      # READ-2-PREREG: p80 over 40 min; >= 6 bars, S >= 0.70, M >= 2.0
LEG_MISS = 3                                        # Amendment 1: 3 marks (15 min) without LEG FLOW = d -> LEAN
FUEL_KIND = {(-1, -1): "long liquidation", (1, -1): "fresh shorts", (-1, 1): "covering", (1, 1): "fresh longs"}
OPEN_S, CLOSE_S, FORM_AT, LATE_S = 33300, 55800, 35100, 54000   # 09:15, 15:30, 09:45, 15:00
MARK = 300                                   # a closed 5-minute mark
NINE = 9
A_IN, A_OUT, ACT_MIN, FLOW_IN = 0.40, 0.15, 0.03, 0.05
HOLD, TOL, EDGE, WALL_R = 2, 0.2, 4, 0.6
GIVE, QUIT_BIG, QUIT_LEFT, QUIT_NEAR = 0.25, 0.25, 0.5, 2
FREEZE = 54900                               # 15:15, the cash-auction freeze of the spot indices
ARROW = {1: "▲", -1: "▼", 0: ""}
CLS_WORD = {"CALL": "CALL LIKH RAHE", "PUT": "PUT LIKH RAHE", "BOTH_WRITE": "DONO LIKH RAHE",
            "BOTH_COVER": "DONO CHHOD RAHE", "QUIET": "SHANT", "MIXED": "MILA-JULA", "BLIND": "PADH NAHI SAKE"}
CC = "could not check -- "


def hm(sec):
    return None if sec is None else "%02d:%02d" % (sec // 3600, sec % 3600 // 60)


def _sign(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def lakh(th):
    """OI kept in thousands (v2feed) -> the app's unit, lakh contracts: 4260 -> '+42.6L'."""
    if th is None:
        return "—"
    a = abs(th) / 100
    return ("+" if th > 0 else "−" if th < 0 else "") + (f"{a:.0f}" if a >= 100 else f"{a:.1f}") + "L"


def num(x):
    return "—" if x is None else f"{x:,.0f}"


# ---- the day's arrays -------------------------------------------------------------------------------------------

def from_v2(s, lot=None, pre=()):
    """v2feed.IdxState -> the dict this module reads (references, no copy: call under v2feed's lock).
    `pre`: GoCharting's closed bars before the first future tick, for FLOW only (Flow's docstring).
    ce_iv / pe_iv (IV x 10^4 on every `slow`-th chain row), hl (each second's tick high / low) and the two expiries feed
    the display-only annotations (writing_vs_buying, day_hl, the basis's options check); the READ never reads them."""
    return {"step": s.step, "t": s.t, "spot": s.spot, "ks": s.ks, "ce_oi": s.ce["oi"], "pe_oi": s.pe["oi"],
            "ce_ltp": s.ce["ltp"], "pe_ltp": s.pe["ltp"], "base_ce": s.base["ce"], "base_pe": s.base["pe"],
            "bars": s.bars, "lot": lot or 1, "bf": s.bf, "flow_from": s.bars[0][0] if s.bars else None, "pre": pre,
            "ce_iv": s.ce.get("iv"), "pe_iv": s.pe.get("iv"), "slow": getattr(s, "slow_every", 6),
            "hl": getattr(s, "hl", None), "expiry": s.expiry, "fut_expiry": s.fut_expiry}


def _at(D, sec):
    i = bisect.bisect_right(D["t"], sec) - 1
    return i if i >= 0 else None


def _sym(D, i):
    """(the strike indices ATM - m .. ATM + m, m) with m <= 4 the widest half-width whose every strike carries both
    OIs at row i; ATM = spot rounded to the step. m = -1: the ATM strike itself is missing (spot off the window)."""
    spot, ks, step = D["spot"][i], D["ks"], D["step"] or 1
    pos = {k: j for j, k in enumerate(ks)}
    atm = math.floor(spot / step + 0.5) * step

    def ok(n):
        j = pos.get(atm + n * step)
        return j is not None and D["ce_oi"][i][j] is not None and D["pe_oi"][i][j] is not None
    m = -1
    while m < NINE // 2 and ok(m + 1) and ok(-(m + 1)):
        m += 1
    return [pos[atm + n * step] for n in range(-m, m + 1)] if m >= 0 else [], m


def _nine(D, i):
    return _sym(D, i)[0]


def _add(D, side, i, j):
    oi, b = D[side + "_oi"][i][j], D["base_" + side].get(D["ks"][j])
    return None if oi is None or b is None else oi - b


def writers(D, i, i30=None):
    """The WRITERS family at chain row i (and the 30-minute change since row i30), on ATM +/- 4 (narrowed, symmetric,
    at a window edge: `edge` says so)."""
    js, m = _sym(D, i)
    if m < 2:
        return {"cls": "BLIND", "vote": None, "edge": m,
                "why": CC + f"spot {num(D['spot'][i])} is at the chain window's edge (ATM ±{max(m, 0)} only)"}
    adds = {(j, s): _add(D, s, i, j) for j in js for s in ("ce", "pe")}
    if all(v is None for v in adds.values()):
        return {"cls": "BLIND", "vote": None, "why": CC + "no strike with yesterday's close OI yet"}
    ce = sum(v for (j, s), v in adds.items() if s == "ce" and v is not None)
    pe = sum(v for (j, s), v in adds.items() if s == "pe" and v is not None)
    base = sum(D["base_" + s].get(D["ks"][j]) or 0 for j in js for s in ("ce", "pe"))
    tot = abs(ce) + abs(pe)
    act = tot / base if base else None
    A = (ce - pe) / tot if tot else 0.0
    if act is None or act < ACT_MIN:
        cls = "QUIET"
    elif A >= A_IN and ce > 0:
        cls = "CALL"
    elif A <= -A_IN and pe > 0:
        cls = "PUT"
    elif ce > 0 and pe > 0:
        cls = "BOTH_WRITE"
    elif ce < 0 and pe < 0:
        cls = "BOTH_COVER"
    else:
        cls = "MIXED"
    out = {"cls": cls, "vote": -1 if cls == "CALL" else 1 if cls == "PUT" else 0, "A": round(A, 2),
           "ce": ce, "pe": pe, "act": None if act is None else round(act, 3),
           "ks": [D["ks"][j] for j in js], "tag": "M", "edge": m if m < NINE // 2 else None}
    if i30 is not None and i30 < i:
        d = lambda s: sum((D[s + "_oi"][i][j] - D[s + "_oi"][i30][j]) for j in js
                          if D[s + "_oi"][i][j] is not None and D[s + "_oi"][i30][j] is not None)
        out["ce30"], out["pe30"] = d("ce"), d("pe")
    return out


class Flow:
    """Prefix sums over the future's 1-s bars [sec, px x 10, vol, buy vol]: CVD = buys - sells.
    `pre` [(sec, vol, buy vol)]: GoCharting's bars that closed before the first tick (a late start), at each bar's
    last second -- volume only, never a price, so basis() still reads the live ticks alone."""

    def __init__(self, bars, pre=()):
        self.sec, self.px, self.vol, self.buy = [], [], [0], [0]
        self.pre_end = None
        for sec, vol, buy in pre or ():
            self.sec.append(sec)
            self.px.append(None)
            self.vol.append(self.vol[-1] + vol)
            self.buy.append(self.buy[-1] + buy)
            self.pre_end = sec
        for b in bars or ():
            self.sec.append(b[0])
            self.px.append(b[1] / 10)
            self.vol.append(self.vol[-1] + b[2])
            self.buy.append(self.buy[-1] + b[3])

    def upto(self, sec):
        n = bisect.bisect_left(self.sec, sec)          # bars strictly before `sec` (the mark's own second excluded)
        return self.vol[n], 2 * self.buy[n] - self.vol[n]

    def px_at(self, sec):
        n = bisect.bisect_right(self.sec, sec) - 1
        return self.px[n] if n >= 0 else None


def flow(F, sec, lot):
    vol, cvd = F.upto(sec)
    if not vol:
        return {"vote": None, "why": CC + "no futures tick yet (they begin when the server does)"}
    r = cvd / vol
    gc = hm(min(F.pre_end + 1, sec)) if F.pre_end is not None and F.sec[0] < sec else None   # GC bars counted, to when
    return {"vote": _sign(r) if abs(r) >= FLOW_IN else 0, "cvd": round(cvd / lot), "vol": round(vol / lot),
            "buy": round((vol + cvd) / 2 / lot), "sell": round((vol - cvd) / 2 / lot), "r": round(r, 3), "gc": gc,
            "tag": "M"}


def _price(B, raws, closes, sec):
    """PRICE at a mark: daytype's raw on the last HOLD closed bars."""
    n = bisect.bisect_right(closes, sec // 60)
    if n == 0:
        return {"vote": None, "why": CC + "no closed 5-min futures bar yet"}
    last = raws[max(0, n - HOLD):n]
    t, d = last[-1]
    held = len(last) == HOLD and all(x == last[-1] for x in last)
    word = {"TREND": "TREND " + ARROW[d], "PIN": "PIN/CHOP", "TWO": "DONO TARAF"}.get(t, t)
    return {"vote": d if (held and t == "TREND") else 0, "raw": t, "dir": d, "word": word, "held": held, "tag": "I"}


def basis(D, F, i, sec):
    """future minus spot: the median of the last 15 one-minute pairs (None when the futures ticks are missing)."""
    out = []
    sec = min(sec, FREEZE)
    for m in range(sec - 14 * 60, sec + 1, 60):
        j, px = _at(D, m), F.px_at(m)
        if j is not None and px is not None and m - D["t"][j] <= 60:
            out.append(px - D["spot"][j])
    return round(statistics.median(out), 1) if out else None


# ---- READ-2: FUEL, LEG FLOW, JAGAH (docs/read/READ-2-PREREG.md) -----------------------------------------------------

def fuel(UB, sec, ref, lot=1):
    """FUEL [M] at a mark: rank.foi's 40 minutes on the Upstox 5-min bars (rank.bars_of rows) closed by `sec`, the
    |OI %| ranked by rank.by_part against `ref` (rank.fuel_ref: the rank_ref's Upstox pool for the day's kind)."""
    import rank                                   # rank imports this module: here, not at the top
    bs = [b for b in UB if b["e"] <= sec]
    j = rank._last_closed(bs, sec) if bs else None
    fo = rank.foi(bs, j) if j is not None else None
    if fo is None:
        return {"vote": None, "why": CC + "futures OI not on both ends of the last 40 minutes"}
    L = rank.by_part(ref, "foi40", sec - 1, round(fo[0], 3), unit="%", src="UX")
    out = {"rank": L.get("pct"), "n": L.get("n"), "oi_pct": round(fo[0], 3), "lots": round(fo[1] / (lot or 1)),
           "px": round(fo[2], 1), "kind": None, "word": None, "tag": "M"}
    if L.get("pct") is None:
        return dict(out, vote=None, why=L.get("why") or CC + "no FUEL reference")
    if L["pct"] < FUEL_P:
        return dict(out, vote=0, why=None)
    k = (_sign(fo[1]), _sign(fo[2]))
    return dict(out, vote=k[1], kind=FUEL_KIND.get(k), word=rank.fuel_word(fo[1], fo[2]) if k in FUEL_KIND else None,
                why=None)


def legflow(F, sec, d, ext):
    """LEG FLOW [M] for direction d at a mark: FLOW's 1-s bars (Flow) summed into the 5-min bars from the one holding
    the session's spot extreme opposite to d (`ext[d]`, sec of day; d < 0: the high) to the last closed by `sec`. A bar
    with no volume read in it (a feed gap) is not a bar of the leg."""
    if not d:
        return {"vote": None, "why": "not read -- no TREND / LEAN held and FLOW votes no side"}
    x = ext.get(d)
    if x is None:
        return {"vote": None, "dir": d, "why": CC + "no spot row in the session before the mark"}
    b0 = OPEN_S + (x - OPEN_S) // MARK * MARK
    if not F.sec:
        return {"vote": None, "dir": d, "from": hm(b0), "why": CC + "no futures tick yet (they begin when the server does)"}
    if OPEN_S + (F.sec[0] - OPEN_S) // MARK * MARK > b0:
        return {"vote": None, "dir": d, "from": hm(b0),
                "why": CC + f"the leg began {hm(b0)}; the flow begins {hm(F.sec[0])}"}
    w, a, n = [], [], 0
    for b in range(b0, sec - MARK + 1, MARK):
        v0, c0 = F.upto(b)
        v1, c1 = F.upto(b + MARK)
        if v1 == v0:
            continue
        n += 1
        x = (c1 - c0) * d                          # > 0: a bar on the leg's side
        if x > 0:
            w.append(x)
        elif x < 0:
            a.append(-x)
    base = {"dir": d, "from": hm(b0), "n": n, "with": len(w), "against": len(a), "S": None, "M": None, "tag": "M"}
    if n < LEG_N:
        return dict(base, vote=None, why=CC + f"the leg from {hm(b0)} has {n} bar(s); it needs {LEG_N}")
    sw, sa = sum(w), sum(a)
    S = sw / (sw + sa) if sw + sa else None
    M = (sw / len(w)) / (sa / len(a)) if w and a else None
    ok = S is not None and S >= LEG_S and (M >= LEG_M if M is not None else bool(w))
    return dict(base, vote=d if ok else 0, S=None if S is None else round(S, 2), M=None if M is None else round(M, 2),
                why=None)


def _lvl(name, x, spot, bs, sg):
    pts = abs(x - spot)
    return {"name": name, "spot": round(x, 1), "fut": None if bs is None else round(x + bs, 1), "pts": round(pts),
            "sig": round(pts / sg, 1) if sg else None}


def _latch(fuels, d, x, since):
    """Amendment 1: the leg's FUEL, latched. `fuels` = [(mark sec, fuel())] so far; the leg's marks are those after
    its extreme `x` (sec) and from the read's own mark `since` (sec). -> {vote: d, kind, word, rank (the biggest), t
    (its mark, the first on a tie)}; vote 0 when the leg was read and gave no FUEL = d; None when no mark of it could."""
    best, read_ = None, False
    for m, f in reversed(fuels):
        if x is None or m <= x or m < since:
            break
        read_ = read_ or f.get("vote") is not None
        if d and f.get("vote") == d and (best is None or f["rank"] >= best[1]["rank"]):
            best = (m, f)
    if best is None:
        return {"vote": 0 if read_ and d else None, "kind": None, "word": None, "rank": None, "t": None}
    m, f = best
    return {"vote": d, "kind": f.get("kind"), "word": f.get("word"), "rank": f["rank"], "t": hm(m)}


def _jtext(d, room, obs, j, obs_why="?"):
    a, b = ARROW[d], ARROW[-d]
    out = [f"{a} jagah {room['pts']} pts" + (f" ({room['sig']}σ)" if room["sig"] is not None else "")
           + f" to {room['name']}" if room else f"{a} jagah ?",
           f"{b} rukawat {obs['pts']} pts to {obs['name']}" if obs else f"{b} rukawat {obs_why}"]
    fl, fz, lz = j["fuel_leg"], j["fuel"], j["legflow"]
    out.append("fuel ?" if fl.get("vote") is None else "fuel nahi" if not fl["vote"]
               else f"fuel {ARROW[fl['vote']]} {fl.get('word') or ''} p{fl['rank']:.0f} @{fl['t']}".replace("  ", " "))
    v = fz.get("vote")
    out.append("abhi ?" if v is None else f"abhi {ARROW[v] + ' ' if v else ''}p{fz['rank']:.0f}")
    s = lz.get("S")
    out.append("flow ?" if lz.get("vote") is None or s is None
               else f"flow {a} {round(s * 100)}%" + ("" if lz["vote"] == d else " kam"))
    return " · ".join(out)


def jagah(word, d, spot, step, bs, tg, bx, flip, lo_hi, levels, vw, sg, fu, lf, fl=None):
    """JAGAH [I] at a mark (display only): where the market is placed, in spot points and the session VWAP sigma
    (`sg`, futures; `vw` the futures VWAP, placed in spot by the row's basis `bs`). `lo_hi` = (day low, day high) of
    the spot rows before the mark; `fl` the leg's latched fuel (_latch). Never a vote, never a probability."""
    fz = {"vote": fu.get("vote"), "kind": fu.get("kind"), "rank": fu.get("rank"), "word": fu.get("word")}
    lz = {k: lf.get(k) for k in ("vote", "S", "M", "n")}
    out = {"text": None, "room": None, "obstacle": None, "fuel": fz, "legflow": lz,
           "fuel_leg": fl or {"vote": None, "kind": None, "word": None, "rank": None, "t": None},
           "sigma": None if sg is None else round(sg, 1), "tag": "I"}
    if word == "BAN RAHA":
        return dict(out, text="09:45 tak padh rahe")
    if word == "RANGE":
        walls = [(nm, k, (bx or {}).get(key)) for nm, k, key in (("TOP", 1, "top"), ("BOTTOM", -1, "bottom"))]
        return dict(out, text=" · ".join(f"{ARROW[k]} {round(abs(b['k'] - spot))} pts to {nm} {b['k']:,.0f}"
                                         for nm, k, b in walls if b) or "box ?")
    if word not in ("TREND", "LEAN") or not d:
        return dict(out, text="saaf nahi")
    near = step / 4 + 1e-9
    room = [(f"{tg[0]['k']:,.0f} {tg[0]['side']} wall", tg[0]["k"])] if tg else []
    ext = lo_hi[0] if d < 0 else lo_hi[1]
    if ext is not None:
        room.append((f"din ka {'low' if d < 0 else 'high'} {ext:,.0f}", ext))
    for k in ("PDL", "PDH"):
        if levels and levels.get(k) is not None:
            room.append((f"{k} {levels[k]:,.0f}", levels[k]))
    r100 = (math.floor((spot - near) / 100) if d < 0 else math.ceil((spot + near) / 100)) * 100
    room.append((f"{r100:,.0f} round", r100))
    room = [(n, x) for n, x in room if (x - spot) * d > near]
    behind = [(f"FLIP {flip:,.0f}", flip)] if flip is not None else []
    if vw is not None and bs is not None:
        behind.append((f"VWAP {vw - bs:,.0f}", vw - bs))
    behind = [(n, x) for n, x in behind if (x - spot) * d < 0]
    pick = lambda L: min(L, key=lambda nx: abs(nx[1] - spot)) if L else None       # noqa: E731 -- first listed on a tie
    rm, ob = pick(room), pick(behind)
    out["room"] = _lvl(rm[0], rm[1], spot, bs, sg) if rm else None
    out["obstacle"] = _lvl(ob[0], ob[1], spot, bs, sg) if ob else None
    out["why_obstacle"] = None if ob else ("?" if flip is None and vw is None else "nahi")
    out["text"] = _jtext(d, out["room"], out["obstacle"], out, out["why_obstacle"])
    return out


def _with_push(j, d, spot, bs, push):
    """The card's JAGAH with the extension's last-push origin (futures) as a candidate obstacle behind price."""
    p = (push or {}).get("down" if d < 0 else "up")
    if not p or bs is None:
        return j
    x = p["px"] - bs
    if (x - spot) * d >= 0:
        return j
    c = _lvl(f"push {x:,.0f}" + (" (fail)" if p.get("failed") else ""), x, spot, bs, j.get("sigma"))
    if j["obstacle"] is not None and j["obstacle"]["pts"] <= c["pts"]:
        return j
    return dict(j, obstacle=c, why_obstacle=None, text=_jtext(d, j["room"], c, j))


# ---- display-only annotations (decode-loop D2, D6): nothing in timeline() reads these ------------------------------

WB_MIN = 25                                  # 0.25 vol pt (IV x 10^4): inside it, writing and buying cannot be told apart


def writing_vs_buying(D, i, i30):
    """D2 [I]: was the OI that rose in the last 30 minutes SOLD or BOUGHT? OI up does not say. Per strike of the nine,
    its IV change minus the ATM-wide IV change (the mean of the ATM CE and PE), weighted by the OI it added, per side.
    A writer hitting bids pushes that strike's IV down against the rest -> "bech ke likha"; a buyer lifting offers
    pushes it up -> "khareed ke"; inside +/- WB_MIN it is "?", never a guess. Display only: no READ vote reads it."""
    out = {"ce": None, "pe": None, "tag": "I"}
    civ, piv, sl = D.get("ce_iv"), D.get("pe_iv"), D.get("slow") or 1
    if i30 is None or i is None or not civ or not piv:
        return dict(out, why=CC + "no IV on the chain rows, or no row 30 minutes back")
    a, b = i // sl, i30 // sl
    if a >= len(civ) or b >= len(civ) or a == b:
        return dict(out, why=CC + "no IV sample 30 minutes apart")
    js, m = _sym(D, i)
    if m < 0:
        return dict(out, why=CC + "spot is off the chain window")

    def div(L, j):
        x, y = L[a][j] if j < len(L[a]) else None, L[b][j] if j < len(L[b]) else None
        return None if x is None or y is None else x - y
    mid = js[len(js) // 2]
    base = [v for v in (div(civ, mid), div(piv, mid)) if v is not None]
    if not base:
        return dict(out, why=CC + "the ATM strike carries no IV")
    atm = sum(base) / len(base)
    for side, L in (("ce", civ), ("pe", piv)):
        num = wsum = 0
        for j in js:
            o1, o0, dv = D[side + "_oi"][i][j], D[side + "_oi"][i30][j], div(L, j)
            if o1 is None or o0 is None or dv is None or o1 <= o0:
                continue
            num += (o1 - o0) * (dv - atm)
            wsum += o1 - o0
        if not wsum:
            out[side] = {"word": "naya OI nahi", "res": None, "add": 0}           # checked: nothing was added
            continue
        res = num / wsum
        out[side] = {"res": round(res / 100, 2), "add": wsum,
                     "word": "bech ke likha" if res <= -WB_MIN else "khareed ke" if res >= WB_MIN else "?"}
    return dict(out, atm_move=round(atm / 100, 2), why=None)


def day_hl(D, now=None):
    """D6: the day's high and low -- fut from every tick (v2feed's per-second tick extremes), spot from every chain row
    (the index is polled ~10 s; the REST-rebuilt morning is minute closes [I] and says so) -- each with its time, as
    of `now` (None = the recorded day). Never a minute grid's."""
    out = {"spot": None, "fut": None, "tag": "M"}
    n = len(D["t"]) if now is None else bisect.bisect_right(D["t"], now)
    sp = [(D["spot"][j], D["t"][j]) for j in range(n) if OPEN_S <= D["t"][j] <= CLOSE_S]
    if sp:
        hi, lo = max(sp, key=lambda x: (x[0], -x[1])), min(sp, key=lambda x: (x[0], x[1]))
        bf = D.get("bf") or 0
        out["spot"] = {"hi": hi[0], "hi_t": hm(hi[1]), "lo": lo[0], "lo_t": hm(lo[1]),
                       "src": "chain rows ~10 s" + (f"; first {bf} rows REST minutes [I]" if bf else "")}
    hl = D.get("hl") or []
    k = len(hl) if now is None else bisect.bisect_right(hl, [now, float("inf"), float("inf")])
    fx = [h for h in hl[:k] if OPEN_S <= h[0] <= CLOSE_S]
    if fx:
        hi, lo = max(fx, key=lambda h: (h[1], -h[0])), min(fx, key=lambda h: (h[2], h[0]))
        out["fut"] = {"hi": hi[1] / 10, "hi_t": hm(hi[0]), "lo": lo[2] / 10, "lo_t": hm(lo[0]), "from": hm(fx[0][0]),
                      "src": "every tick" + (f" from {hm(fx[0][0])} (before it: no ticks, this process was not up)"
                                             if fx[0][0] > OPEN_S + 60 else "")}
    else:
        out["fut_why"] = CC + "no futures tick yet (they begin when the server does)"
    return out


# ---- levels -------------------------------------------------------------------------------------------------------

def _window(D, i, sign):
    """Strike indices strictly on one side of spot (sign -1 below, +1 above), within EDGE steps, nearest first."""
    spot, ks, step = D["spot"][i], D["ks"], D["step"] or 1
    js = [j for j in range(len(ks)) if (ks[j] - spot) * sign > 0 and abs(ks[j] - spot) <= EDGE * step + step / 2]
    return sorted(js, key=lambda j: abs(ks[j] - spot))


def flip_level(D, i, d):
    """d < 0: the CE strike above spot with the most aaj likha; d > 0: the PE strike below with the most."""
    side, sign = ("ce", 1) if d < 0 else ("pe", -1)
    js = _window(D, i, sign)
    best = max(((_add(D, side, i, j) or 0, -n, j) for n, j in enumerate(js)), default=None)
    if best is None:
        return None, CC + "no strike on that side in the chain window"
    if best[0] <= 0:
        return D["ks"][js[0]], "no " + side.upper() + " writing on that side -- the nearest strike"
    return D["ks"][best[2]], f"{side.upper()} {D['ks'][best[2]]:.0f} aaj likha {lakh(best[0])}"


def targets(D, i, d):
    """The walls in the trade's way: d < 0 -> PE OI below spot, d > 0 -> CE OI above, nearest first."""
    side, sign = ("pe", -1) if d < 0 else ("ce", 1)
    spot, ks, step = D["spot"][i], D["ks"], D["step"] or 1
    js = [j for j in range(len(ks)) if (ks[j] - spot) * sign > step / 4 and D[side + "_oi"][i][j] is not None]
    if not js:
        return []
    mx = max(D[side + "_oi"][i][j] for j in js)
    walls = sorted((j for j in js if mx and D[side + "_oi"][i][j] >= WALL_R * mx), key=lambda j: abs(ks[j] - spot))
    return [{"k": ks[j], "oi": D[side + "_oi"][i][j], "side": side.upper()} for j in walls[:2]]


def box(D, i):
    """RANGE: the biggest CE OI above spot and the biggest PE OI below, within EDGE steps."""
    def big(side, sign):
        js = [j for j in _window(D, i, sign) if D[side + "_oi"][i][j] is not None]
        if not js:
            return None
        j = max(js, key=lambda j: D[side + "_oi"][i][j])
        return {"k": D["ks"][j], "oi": D[side + "_oi"][i][j]}
    return {"top": big("ce", 1), "bottom": big("pe", -1)}


# ---- the day ------------------------------------------------------------------------------------------------------

def _word(w, p, f):
    """(word, dir, agree) from the three votes, before any holding."""
    wv, pv, fv = w.get("vote"), p.get("vote"), f.get("vote")
    vs = [v for v in (wv, pv, fv) if v is not None]
    for d in (-1, 1):
        if wv == d and (pv == d or fv == d) and -d not in vs:
            return "TREND", d, sum(1 for v in vs if v == d)
        if wv == 0 and pv == d and fv == d:
            return "LEAN", d, 2
    if w.get("cls") == "BOTH_WRITE" and pv == 0:
        return "RANGE", 0, None
    return "WAIT", 0, None


def timeline(D, bars5, levels=None, now=None, fuel_ref=None):
    """Every closed 5-minute mark of the day, oldest first, plus the events. `now` (sec of day) caps the marks;
    None = the whole recorded day. `levels` (PDH / PDL) and `fuel_ref` (rank.fuel_ref) feed READ-2's JAGAH and FUEL
    only; without `fuel_ref` FUEL could not check and every word is read-1.1's. -> {"rows": [...], "events": [...]}"""
    if not D.get("t"):
        return {"rows": [], "events": [], "why": CC + "no chain row recorded yet today"}
    import frame_v2                               # frame_v2 and rank import this module: here, not at the top
    import rank
    F = Flow(D.get("bars"), D.get("pre"))
    B = daytype._bars(bars5 or ())
    raws, _labels = daytype.timeline(B) if B else ([], [])
    closes = [b["m"] + 5 for b in B]
    step, lot = D["step"] or 1, D.get("lot") or 1
    last_sec = min(now if now is not None else CLOSE_S, CLOSE_S, D["t"][-1] + MARK)
    UB = rank.bars_of(bars5, 5)                   # FUEL's bars (Upstox, with OI)
    b3 = frame_v2.bars3(D.get("bars"), lot, now)  # JAGAH's VWAP / sigma: her chart's, from the ticks
    b3e = [b["e"] for b in b3]
    T, SP = D["t"], D["spot"]
    k, hi, lo = 0, None, None                     # the session's spot extremes before the mark: (spot, sec)
    fuels = []                                    # (mark sec, FUEL) at every mark so far: the latch's memory
    rows, events = [], []
    held = None                                   # {"word", "dir", "since", "flip", "agree", "box"} (+ READ-2's "ff")
    peaks, quit_done = {}, set()
    for sec in range(OPEN_S + MARK, last_sec + 1, MARK):
        while k < len(T) and T[k] < sec:
            if T[k] >= OPEN_S:
                hi = (SP[k], T[k]) if hi is None or SP[k] > hi[0] else hi
                lo = (SP[k], T[k]) if lo is None or SP[k] < lo[0] else lo
            k += 1
        ext = {-1: hi[1] if hi else None, 1: lo[1] if lo else None}
        i = _at(D, sec)
        if i is None:
            continue
        i30 = _at(D, sec - 1800)
        w = writers(D, i, i30)
        p = _price(B, raws, closes, sec)
        f = flow(F, sec, lot)
        spot = D["spot"][i]
        t = hm(sec)
        _quits(D, i, t, peaks, quit_done, events)
        fu = fuel(UB, sec, fuel_ref, lot)
        fuels.append((sec, fu))
        bs = basis(D, F, i, sec)
        if sec < FORM_AT:
            dd = f.get("vote") or 0
            lf, fleg = legflow(F, sec, dd, ext), _latch(fuels, dd, ext.get(dd), OPEN_S)
            rows.append(dict(_row(t, "BAN RAHA", 0, None, None, spot, w, p, f, None, [], None, [], bs),
                             word_r1="BAN RAHA", src=None, fuel=fu, fuel_leg=fleg, legflow=lf,
                             jagah=jagah("BAN RAHA", 0, spot, step, bs, [], None, None, (None, None), levels, None, None,
                                         fu, lf, fleg)))
            continue
        word, d, agree = _word(w, p, f)
        broke = None
        if held and held["word"] in ("TREND", "LEAN"):
            hd = held["dir"]
            cand, _why = flip_level(D, i, hd)
            if cand is not None and held["flip"] is not None:
                held["flip"] = min(held["flip"], cand) if hd < 0 else max(held["flip"], cand)
            elif cand is not None:
                held["flip"] = cand
            A = w.get("A")
            if held["flip"] is not None and (spot - held["flip"]) * hd < -TOL * step:
                broke = f"spot {num(spot)} ne FLIP {num(held['flip'])} tod diya"
            elif w.get("vote") == -hd:
                broke = f"writers ulta likh rahe (A {A:+.2f})"
            elif (held["word"] == "TREND" and A is not None and w.get("cls") not in ("BLIND", "QUIET")
                  and A * -hd < A_OUT):            # a LEAN never had the writers, so it has nothing to give back
                broke = f"writers ne saath chhoda (A {A:+.2f})"
            elif p.get("vote") == -hd:
                broke = "price ulta " + (p.get("word") or "")
            if not broke:
                if held["word"] == "LEAN" and word == "TREND" and d == hd:
                    name = _name(held)                 # "LEAN ▼", or READ-2's "TREND ▼ · flow+fuel"
                    held.update(word="TREND", agree=agree)
                    events.append({"t": t, "kind": "UP", "dir": hd, "tag": "I",
                                   "text": f"{name} → TREND {ARROW[hd]} · OI saath aaya", "en": "the writers joined"})
                elif word in ("TREND", "LEAN") and d == hd:
                    held["agree"] = agree
        elif held and held["word"] == "RANGE":
            bx = held["box"] or {}
            top, bot = (bx.get("top") or {}).get("k"), (bx.get("bottom") or {}).get("k")
            if top is not None and spot > top + TOL * step:
                broke = f"spot {num(spot)} box ke upar ({num(top)})"
            elif bot is not None and spot < bot - TOL * step:
                broke = f"spot {num(spot)} box ke neeche ({num(bot)})"
            elif word in ("TREND", "LEAN"):
                broke = f"{word} {ARROW[d]} bana"
        if broke:
            events.append({"t": t, "kind": "BREAK", "dir": -held["dir"], "tag": "I",
                           "text": f"{_name(held)} khatam · {broke}", "en": "the read broke"})
            held = None
        if held is None or held["word"] == "WAIT":
            was = held
            if word in ("TREND", "LEAN"):
                fl, _ = flip_level(D, i, d)
                held = {"word": word, "dir": d, "since": t, "flip": fl, "agree": agree, "box": None}
            elif word == "RANGE":
                held = {"word": "RANGE", "dir": 0, "since": t, "flip": None, "agree": None, "box": box(D, i)}
            elif was is None:
                held = {"word": "WAIT", "dir": 0, "since": t, "flip": None, "agree": None, "box": None}
            if held is not was and held["word"] != "WAIT":
                events.append({"t": t, "kind": "FORM", "dir": held["dir"], "tag": "I",
                               "text": f"{_name(held)} bana" + (f" · FLIP {num(held['flip'])}" if held["flip"] else ""),
                               "en": "the read formed"})
        hd = held["dir"]
        tg = targets(D, i, hd) if held["word"] in ("TREND", "LEAN") else []
        # READ-2 (+ Amendment 1): the flow+fuel overlay on the held word. Nothing above reads it; the held machine is
        # read-1.1's. FUEL is latched for the leg (a new leg, or this read's re-forming, resets it); only LEG FLOW
        # missing d at LEG_MISS marks in a row takes the flow+fuel TREND back to LEAN.
        dd = hd or f.get("vote") or 0
        lf = legflow(F, sec, dd, ext)
        fleg = _latch(fuels, dd, ext.get(dd), int(held["since"][:2]) * 3600 + int(held["since"][3:5]) * 60)
        word2, src = held["word"], ("writers" if held["word"] == "TREND" else None)
        was = held.get("ff", False)
        if held["word"] != "LEAN":
            held["ff"] = False
        elif was:
            if lf.get("vote") == hd:
                held["miss"], held["missq"] = 0, False
            else:                                        # 0 or "could not check": both are a miss
                held["miss"] = held.get("miss", 0) + 1
                held["missq"] = held.get("missq", False) or lf.get("vote") is None
            held["ff"] = held["miss"] < LEG_MISS
        else:
            held["ff"] = (word, d) == ("LEAN", hd) and fleg.get("vote") == hd and lf.get("vote") == hd
            held["miss"], held["missq"] = 0, False
        if held["ff"]:
            word2, src = "TREND", "flow+fuel"
        if held["ff"] != was and held["word"] == "LEAN":
            a = ARROW[hd]
            events.append({"t": t, "kind": "UP", "dir": hd, "tag": "I", "src": "flow+fuel",
                           "text": f"LEAN {a} → TREND {a} · flow+fuel · fuel {fleg.get('word')} p{fleg['rank']:.0f} "
                                   f"@{fleg['t']} · flow {round(lf['S'] * 100)}%",
                           "en": "the leg's fuel and its flow joined the lean"} if held["ff"] else
                          {"t": t, "kind": "DOWN", "dir": hd, "tag": "I", "src": "flow+fuel",
                           "text": f"TREND {a} · flow+fuel → LEAN {a} · flow {LEG_MISS} mark se saath nahi"
                                   + (" (? bhi)" if held["missq"] else "") + " · read khada hai",
                           "en": f"the leg's flow missed {LEG_MISS} marks in a row; the read stands"})
        nb = bisect.bisect_right(b3e, sec)
        vw, sg = ((b3[nb - 1]["vwap"], b3[nb - 1]["sig"]) if nb and frame_v2._holes(b3[:nb], sec) is None
                  else (None, None))
        jg = jagah(word2, hd, spot, step, bs, tg, held["box"], held["flip"], (lo and lo[0], hi and hi[0]), levels,
                   vw, sg, fu, lf, fleg)
        rows.append(dict(_row(t, word2, hd, held["since"], held["agree"], spot, w, p, f, held["flip"], tg,
                              held["box"], _warnings(D, i, held, w, peaks), bs),
                         word_r1=held["word"], src=src, fuel=fu, fuel_leg=fleg, legflow=lf, jagah=jg))
    return {"rows": rows, "events": events}


def _quits(D, i, t, peaks, done, events):
    """QUIT: a big build among the nine given back (peaks are kept over every strike the chain carried)."""
    big = 0
    for j in range(len(D["ks"])):
        for s in ("ce", "pe"):
            a = _add(D, s, i, j)
            if a is not None:
                key = (D["ks"][j], s)
                peaks[key] = max(peaks.get(key, 0), a)
                big = max(big, peaks[key])
    if big <= 0:
        return
    near = QUIT_NEAR * (D["step"] or 1) + 1e-9
    for j in _nine(D, i):
        if abs(D["ks"][j] - D["spot"][i]) > near:
            continue
        for s in ("ce", "pe"):
            key = (D["ks"][j], s)
            a, pk = _add(D, s, i, j), peaks.get(key, 0)
            if key in done or a is None or pk <= 0:
                continue
            if pk >= QUIT_BIG * big and a <= QUIT_LEFT * pk:
                done.add(key)
                wall = "floor" if s == "pe" else "ceiling"
                itm = round((D["spot"][i] - key[0]) * (1 if s == "ce" else -1))    # N4, display: > 0 = already through it
                paar = f" · paar +{itm:,}" if itm > 0 else ""
                events.append({"t": t, "kind": "QUIT", "k": key[0], "side": s.upper(), "dir": 1 if s == "ce" else -1,
                               "text": f"{key[0]:,.0f} {s.upper()} likhne wale bhage · {lakh(pk)} → {lakh(a)}{paar}",
                               "en": f"{key[0]:,.0f} {s.upper()} {wall} gone{paar}", "tag": "M"})


def _name(h):
    if h.get("ff") or h.get("src") == "flow+fuel":     # READ-2: never shown as a plain writers' TREND
        return f"TREND {ARROW[h['dir']]} · flow+fuel"
    return h["word"] + ((" " + ARROW[h["dir"]]) if h["dir"] else "")


def _warnings(D, i, held, w, peaks):
    out = []
    d = held["dir"]
    if held["word"] in ("TREND", "LEAN") and held["flip"] is not None:
        side = "ce" if d < 0 else "pe"
        if held["flip"] in D["ks"]:
            j = D["ks"].index(held["flip"])
            a, pk = _add(D, side, i, j), peaks.get((held["flip"], side), 0)
            if a is not None and pk > 0 and a <= (1 - GIVE) * pk:
                out.append(f"FLIP {held['flip']:,.0f} {side.upper()} writers chhod rahe ({lakh(pk)} → {lakh(a)})")
        mine, other = ("ce30", "pe30") if d < 0 else ("pe30", "ce30")
        if w.get(other) is not None and w[other] > 0 and w[other] > max(w.get(mine) or 0, 0):
            out.append(f"pichle 30m {other[:2].upper()} likha {lakh(w[other])} > {mine[:2].upper()} {lakh(w.get(mine))}")
    return out


def _row(t, word, d, since, agree, spot, w, p, f, flip, tg, bx, warn, bs=None):
    return {"t": t, "word": word, "dir": d, "since": since, "agree": agree, "spot": spot, "basis": bs,
            "flip": flip, "targets": tg, "box": bx, "warn": warn,
            "writers": {k: w.get(k) for k in ("cls", "vote", "A", "ce", "pe", "ce30", "pe30", "act", "why", "edge")},
            "price": {k: p.get(k) for k in ("vote", "word", "raw", "dir", "why")},
            "flow": {k: f.get(k) for k in ("vote", "cvd", "buy", "sell", "vol", "gc", "why")}}


# ---- the face -----------------------------------------------------------------------------------------------------

def _leg(D, i, side, k):
    if k is None or k not in D["ks"]:
        return None
    v = D[side + "_ltp"][i][D["ks"].index(k)]
    return {"side": side.upper(), "k": k, "ltp": None if v is None else round(v / 20, 2)}


def card(D, tl, levels=None, now=None, push=None):
    """The face for one index: the last closed mark's held read, the live spot against its lines, the trade, the
    facts as chips, and the day so far. `now` (sec of day) None = the recorded day's end. `push` (live only: the
    extension's last-push origins, server._push_for) is one more obstacle candidate for JAGAH -- the card's alone, so
    the rows stay what a replay gives."""
    rows = tl.get("rows") or []
    if not rows:
        return {"ok": False, "why": tl.get("why") or CC + "no closed 5-minute mark yet"}
    r = rows[-1]
    i = len(D["t"]) - 1 if now is None else (_at(D, now) or 0)
    spot, step = D["spot"][i], D["step"] or 1
    bs = r.get("basis")

    def fut(x):
        return None if x is None or bs is None else round(x + bs)

    d, word = r["dir"], r["word"]
    out = {"ok": True, "rev": REV, "t": r["t"], "word": word, "dir": d, "arrow": ARROW[d], "since": r["since"],
           "agree": r["agree"], "spot": spot, "spot_at": hm(D["t"][i]), "basis": bs, "warn": r["warn"], "beyond": False}
    j = r.get("jagah")
    if j and word in ("TREND", "LEAN") and push:
        j = _with_push(j, d, r["spot"], bs, push)
    out.update(word_r1=r.get("word_r1"), src=r.get("src"), fuel=r.get("fuel"), fuel_leg=r.get("fuel_leg"),
               legflow=r.get("legflow"), jagah=j)
    lines = []
    if word in ("TREND", "LEAN") and r["flip"] is not None:
        gap = (r["flip"] - spot) * -d                 # > 0 while the read is safe
        lines.append({"k": "FLIP", "spot": r["flip"], "fut": fut(r["flip"]), "gap": round(gap),
                      "note": "5m close " + ("upar" if d < 0 else "neeche") + " = read galat"})
        for n, tg in enumerate(r["targets"]):
            lines.append({"k": f"T{n + 1}", "spot": tg["k"], "fut": fut(tg["k"]),
                          "gap": round(abs(tg["k"] - spot)), "note": f"{tg['side']} OI {lakh(tg['oi'])}"})
        out["beyond"] = gap < -TOL * step               # live spot past the flip: the 5-min close decides
    elif word == "RANGE" and r["box"]:
        for k, key, side in (("TOP", "top", "CE"), ("BOTTOM", "bottom", "PE")):
            b = r["box"].get(key)
            if b:
                lines.append({"k": k, "spot": b["k"], "fut": fut(b["k"]), "gap": round(abs(b["k"] - spot)),
                              "note": f"{side} OI {lakh(b['oi'])}"})
    for k in ("PDH", "PDL", "PDC"):
        if levels and levels.get(k) is not None:
            lines.append({"k": k, "spot": round(levels[k], 1), "fut": fut(levels[k]), "gap": round(abs(levels[k] - spot)),
                          "note": "kal ka " + {"PDH": "high", "PDL": "low", "PDC": "close"}[k]})
    out["lines"] = lines
    w, p, f = r["writers"], r["price"], r["flow"]
    chips = []
    if w.get("cls") == "BLIND":
        chips.append({"k": "LIKHNA", "v": w.get("why"), "dir": 0, "tag": "M"})
    else:
        chips.append({"k": "LIKHNA", "v": f"{CLS_WORD[w['cls']]} · CE {lakh(w['ce'])} · PE {lakh(w['pe'])}",
                      "dir": w["vote"] or 0, "tag": "M"})
        if w.get("ce30") is not None:
            chips.append({"k": "30 MIN", "v": f"CE {lakh(w['ce30'])} · PE {lakh(w['pe30'])}",
                          "dir": _sign((w["pe30"] or 0) - (w["ce30"] or 0)), "tag": "M"})
    chips.append({"k": "PRICE", "v": p.get("word") or p.get("why"), "dir": p.get("vote") or 0, "tag": "I"})
    if f.get("vote") is None:
        chips.append({"k": "FLOW", "v": f.get("why"), "dir": 0, "tag": "M"})
    else:
        chips.append({"k": "FLOW", "v": f"CVD {f['cvd']:+,} lots · bech {f['sell']:,} / kharid {f['buy']:,}"
                      + (f" · {f['gc']} tak GC" if f.get("gc") else ""), "dir": f["vote"], "tag": "M"})
    if levels and levels.get("PDL") is not None and levels.get("PDH") is not None:
        below, above = spot < levels["PDL"], spot > levels["PDH"]
        chips.append({"k": "JAGAH", "v": "kal ke low ke neeche" if below else "kal ke high ke upar" if above
                      else "kal ki range ke andar", "dir": -1 if below else 1 if above else 0, "tag": "M"})
    out["chips"] = chips
    out["votes"] = {"writers": w.get("vote"), "price": p.get("vote"), "flow": f.get("vote")}
    out["w"], out["f"] = w, f                    # the numbers behind the chips, for RANK (rank.py) and the face
    ms = int(r["t"][:2]) * 3600 + int(r["t"][3:5]) * 60
    out["wb"] = writing_vs_buying(D, _at(D, ms), _at(D, ms - 1800))
    out["hl"] = day_hl(D, now)
    trade = []                                   # her way: with the trend buy ATM / ITM, or sell where the writers stand
    if word in ("TREND", "LEAN"):
        ks = D["ks"]
        if d < 0:
            buy_k = min((k for k in ks if k >= spot), default=None)
            trade = [dict(_leg(D, i, "pe", buy_k) or {}, act="BUY", why="ATM/ITM, trend ke saath"),
                     dict(_leg(D, i, "ce", r["flip"]) or {}, act="SELL", why="FLIP pe, call writers ke saath")]
        else:
            buy_k = max((k for k in ks if k <= spot), default=None)
            trade = [dict(_leg(D, i, "ce", buy_k) or {}, act="BUY", why="ATM/ITM, trend ke saath"),
                     dict(_leg(D, i, "pe", r["flip"]) or {}, act="SELL", why="FLIP pe, put writers ke saath")]
        out["against"] = ("CE kharidna / PE bechna" if d < 0 else "PE kharidna / CE bechna") + " = read ke khilaaf"
    elif word == "RANGE" and r["box"]:
        tb, bb = r["box"].get("top"), r["box"].get("bottom")
        trade = [dict(_leg(D, i, "ce", tb and tb["k"]) or {}, act="SELL", why="box top, CE wall"),
                 dict(_leg(D, i, "pe", bb and bb["k"]) or {}, act="SELL", why="box bottom, PE wall")]
    out["trade"] = [x for x in trade if x.get("k") is not None]
    out["late"] = (now if now is not None else D["t"][-1]) >= LATE_S
    segs = []                                    # the day so far: each held word, its span, the spot move inside it
    for x in rows:
        if x["word"] == "BAN RAHA":
            continue
        name = _name(x)
        if segs and segs[-1]["word"] == name and segs[-1]["since"] == x["since"]:
            segs[-1].update(to=x["t"], spot1=x["spot"])
        else:
            segs.append({"word": name, "dir": x["dir"], "since": x["since"], "from": x["t"], "to": x["t"],
                         "spot0": x["spot"], "spot1": x["spot"]})
    for s in segs:
        s["move"] = round(s["spot1"] - s["spot0"])
    out["day"] = segs
    out["changes"] = max(0, len(segs) - 1)
    return out
