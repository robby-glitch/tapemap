"""raftaar.py -- RAFTAAR: the OI-speed STATE read, as a causal replay over the chain record. stdlib only, read-only.

The question: from the speed of OI writing and covering on the nine strikes nearest spot, read ACROSS strikes, is a
MOVE happening (which way, writers with it or against it, starting / pressing / tiring), is price CHOPPING, is it
PINNED, is one side LOADING, are both sides UNWINDING, or did nothing clear the noise bar? One graded picture, and a
stamped line only when the graded story changes. Every threshold is [I] unless marked a §1d number.

MEASURES, per minute t (the minute grid = the last ~10 s snapshot of each minute, the grid /api/oihist serves):
  nine        the NEAR = 9 strikes nearest spot at t (§1d), atm = the nearest one
  zones       CE near = strikes <= atm (the call writers at / under water if price rises), CE wall = strikes > atm;
              PE near = strikes >= atm, PE wall = strikes < atm.  Mirror images.
  d_k,s(w)    OI change of strike k, side s over w minutes (strikes not recorded at t-w are skipped and counted)
  zone net    sum of d over the zone's strikes; zone votes = strikes with |d| >= §1d's stall rate x w x their own OI,
              split up / down (agreement across strikes)
  adds / cuts the side's gross writing / covering over w on the nine
  floors      the day's own distribution at that time: per side, the running medians of |zone net15| (both zones
              pooled), adds15 and cuts15 over the marks so far, >= MIN_HIST marks  [I]
  bar         a flow clears the bar at BAR x its own median; BADA at BADA x  [I]
  P           "a move" = THR_PCT 0.18 % of the day's first spot (effort.py / oi-lab detector's yardstick)  [I]
  m(w), r(w)  spot change and spot range over w; a LEG = a mark with |m15| >= P, carrying its direction

SIDE PATTERNS over 15 min (the side that LOSES if the move continues, then the side that wins):
  losing side   near <= -T and wall >= 0.5 |near|  -> ROLL (cap rolled up / floor rolled down: still short, wall moved)
                near <= -T otherwise               -> RETREAT (covering at / under water, no new wall: fuel)
                near >= +T                         -> ABSORB (writing into the move at / under spot: wall or trap)
                wall >= +T                         -> WALL BUILD (a wall ahead)
                wall <= -T                         -> WALL LIFT (the wall ahead is leaving)
                else                               -> QUIET
  winning side  adds15 >= TA                       -> PRESS (chasing with the move)
                near <= -T                         -> BOOK (the winners leaving)
                else                               -> QUIET
  with15 = losing-side cuts + winning-side adds;  against15 = losing-side adds.

WORDS (priority order):
  CHAL RAHA ▲/▼  a LEG now with a side pattern behind it.  Qualifier ULTA (against >= with), SAATH (with >= 2 against),
                 MILA-JULA.  Phase from with5: SHURU (first HOLD marks), TEZ (with5 >= 1.5 x with5 five marks ago, at a
                 new 15-min extreme), THAK RAHA (3 marks of with5 <= 0.5 x the move's peak with5, or m5 against the move
                 with against5 >= with5), else BARABAR.  Only TEZ / THAK RAHA re-stamp.
  CHOP           legs BOTH ways inside CHOP_WIN = 30 min, and no leg with OI behind it now (a leg with both sides QUIET
                 right after the opposite leg is a chop leg, not a move).
  PIN            |m15| < P, both sides' adds15 >= TA.  "PIN k" when the biggest combined add is within a step of spot,
                 else "PIN · dono deewar CE k1 / PE k2" (a range being fenced).  'balanced' = CE / PE OI at k within 25 %.
  UNWIND         |m15| < P, both sides' net15 <= -T: dono nikal rahe.
  LOAD           |m15| < P, one side's net15 >= T, the other's < T: <side> likh rahe at its biggest-add strike.
  KHAMOSH        nothing cleared the bar.
  BINA OI        a LEG with both sides QUIET and no opposite leg in 30 min: price moving, writers absent (shown as
                 CHAL RAHA ▲/▼ BINA OI, graded by price alone).
  SOCH RAHA      cannot read yet (history / a hole), with the reason.

GRADE = a count of checks, never a %:  size >= BAR (the bar) · size >= BADA · held >= 3 marks · held >= 9 marks ·
  strikes agree (>= 2/3 of the voting strikes in the story's zones go its way) · peers agree (both other indices showed
  the same word and direction within the last 3 marks).  5-6 PAKKA · 3-4 THEEK · 1-2 HALKA.

STAMP: the story key (word, direction, side patterns, qualifier, TEZ / THAK RAHA) must hold HOLD = 3 marks; stamped
at its first mark.  FRONT STAMPS (her 09:27 "ruka" / 10:21 "phir likhne lage"): §1d's own BUILDING / STALLED /
UNWINDING on the top-2 strikes per side by OI, a change held HOLD marks; UNWINDING while the same side's next strike
outward is BUILDING reads SHIFT -> k2.

    python raftaar.py NIFTY 2026-10-08                   stamped lines + census (+ peers from the other two indices)
    python raftaar.py NIFTY 2026-10-08 --all 09:40 10:20  every minute in a window
    python raftaar.py --check                            the synthetic self-check
"""
import os
import sys

from survey import CHAIN, grid, mins, nine

NEAR = 9
THR_PCT = 0.0018                 # [I] house yardstick for "a move"
HOLD = 3                         # [I] her 3-min bar
MIN_HIST = 10                    # [I] marks of 15-min history before the floors are read (first word ~09:41)
FLOOR_WIN = 60                   # [I] the floors are medians over the last 60 marks: the day's distribution AT THAT TIME
PIN_WIN = 45                     # [I] a pin is judged on both sides over 45 min (the writers take turns)
PIN_RNG = 2.0                    # [I] and the 45-min spot range must stay under 2 P
BAR, BADA = 1.5, 3.0             # [I] a flow clears the bar at 1.5 x its own running median; BADA at 3 x
CHOP_WIN = 30                    # [I] legs both ways inside 30 min = chop
SAATH_X, TEZ_X, THAK_X = 2.0, 1.5, 0.5   # [I]
ROLL_FRAC = 0.5                  # [I] the wall re-adds >= half of what the near zone cut -> ROLL
PIN_BAL = 0.25                   # [I]
PEER_LAG = 3                     # [I] a peer's same word within the last 3 marks counts
STALL_RATE = 0.05 / 15           # §1d: STALL_FRAC / SLOPE_MARKS per minute of the strike's own size
L = 1e5


def lakh(x):
    """Signed OI in lakh; under a lakh in thousands (BANKNIFTY's non-expiry weeks), never a '-0.0L'."""
    if abs(x) < 500:
        return "0"
    s = "+" if x > 0 else "-"
    a = abs(x)
    return f"{s}{a / 1e3:.0f}k" if a < 1e5 else f"{s}{a / 1e5:.1f}L"


GRADE_WORD = lambda n: "PAKKA" if n >= 5 else "THEEK" if n >= 3 else "HALKA"   # noqa: E731


def step_of(ks):
    ks = sorted(ks)
    return min((b - a for a, b in zip(ks, ks[1:]) if b > a), default=50)


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def _share(a, b):
    return a / (a + b) if a + b else None


def zones(g, at, t, w):
    """Per side: near / wall nets, votes, gross, adds, cuts over w minutes on the nine at t; None if t-w is missing."""
    b = at.get(mins(t) - w)
    if b is None:
        return None
    now, was = g[t], g[b]
    spot = now["spot"]
    nk = nine(list(now["k"]), spot)
    atm = min(nk, key=lambda k: (abs(k - spot), k))
    out = {"m": spot - was["spot"], "miss": 0, "nk": nk, "atm": atm}
    for i, s in enumerate(("CE", "PE")):
        z = {"near": 0.0, "wall": 0.0, "near_up": 0, "near_dn": 0, "wall_up": 0, "wall_dn": 0, "adds": 0.0, "cuts": 0.0, "per": {}}
        for k in nk:
            if k not in was["k"]:
                out["miss"] += 1
                continue
            d = now["k"][k][i] - was["k"][k][i]
            z["per"][k] = d
            zone = "near" if ((k <= atm) if s == "CE" else (k >= atm)) else "wall"
            z[zone] += d
            if abs(d) >= STALL_RATE * w * max(now["oi"][k][i], 1.0):
                z[zone + ("_up" if d > 0 else "_dn")] += 1
            if d > 0:
                z["adds"] += d
            else:
                z["cuts"] -= d
        out[s] = z
    return out


def rng(g, at, t, w):
    xs = [g[at[m]]["spot"] for m in range(mins(t) - w, mins(t) + 1) if m in at]
    return (max(xs), min(xs)) if xs else (None, None)


def losing(z, T):
    """The losing side's pattern and its strike agreement (share of its voting strikes going the pattern's way)."""
    near, wall = z["near"], z["wall"]
    if near <= -T:
        agree = _share(z["near_dn"], z["near_up"])
        if wall >= ROLL_FRAC * -near:
            return "ROLL", min(x for x in (agree, _share(z["wall_up"], z["wall_dn"])) if x is not None) if agree is not None else None
        return "RETREAT", agree
    if near >= T:
        return "ABSORB", _share(z["near_up"], z["near_dn"])
    if wall >= T:
        return "WALL BUILD", _share(z["wall_up"], z["wall_dn"])
    if wall <= -T:
        return "WALL LIFT", _share(z["wall_dn"], z["wall_up"])
    return "QUIET", None


def winning(z, T, TA):
    if z["adds"] >= TA:
        return "PRESS", _share(z["near_up"] + z["wall_up"], z["near_dn"] + z["wall_dn"])
    if z["near"] <= -T:
        return "BOOK", _share(z["near_dn"], z["near_up"])
    return "QUIET", None


def biggest(z, sign=1):
    per = z["per"]
    return max(per, key=lambda k: sign * per[k]) if per else None


def read_day(g):
    """[row per minute], causal. Each row: t, spot, word, the story's parts, numbers and grade checks."""
    ts = sorted(g)
    at = {mins(t): t for t in ts}
    P = THR_PCT * g[ts[0]]["spot"]
    step = step_of(list(g[ts[0]]["k"]))
    hist = {s: {"net": [], "add": [], "cut": [], "net5": [], "add5": []} for s in ("CE", "PE")}
    rows, move, legs = [], None, []          # legs: (minute, dirn) of every |m15| >= P mark, for CHOP
    loads = []                               # (minute, side, k) of LOAD marks: writers taking turns at one strike = PIN
    for t in ts:
        if t < "09:20":
            continue
        spot = g[t]["spot"]
        z5, z15 = zones(g, at, t, 5), zones(g, at, t, 15)
        if z5 is None or z15 is None:
            rows.append({"t": t, "word": "SOCH RAHA", "why": "5/15-min lookback missing", "spot": spot})
            continue
        for s in ("CE", "PE"):
            hist[s]["net"] += [abs(z15[s]["near"]), abs(z15[s]["wall"])]
            hist[s]["add"].append(z15[s]["adds"])
            hist[s]["cut"].append(z15[s]["cuts"])
            hist[s]["net5"] += [abs(z5[s]["near"]), abs(z5[s]["wall"])]
            hist[s]["add5"].append(z5[s]["adds"])
        if len(hist["CE"]["add"]) < MIN_HIST:
            rows.append({"t": t, "word": "SOCH RAHA", "why": f"{len(hist['CE']['add'])}/{MIN_HIST} marks of 15-min history", "spot": spot})
            continue
        f = {s: {q: max(median(hist[s][q][-(FLOOR_WIN * (2 if q.startswith("net") else 1)):]), 1.0) for q in hist[s]} for s in hist}
        T5 = {s: BAR * f[s]["net5"] for s in f}
        TA5 = {s: BAR * f[s]["add5"] for s in f}
        z30 = zones(g, at, t, PIN_WIN)
        T = {s: BAR * f[s]["net"] for s in f}
        TA = {s: BAR * f[s]["add"] for s in f}
        m15, m5 = z15["m"], z5["m"]
        hi15, lo15 = rng(g, at, t, 15)
        hi30, lo30 = rng(g, at, t, 30)
        r45 = rng(g, at, t, PIN_WIN)
        b30 = at.get(mins(t) - 30)
        m30 = spot - g[b30]["spot"] if b30 else None
        row = {"t": t, "spot": spot, "m5": m5, "m15": m15, "m30": m30, "r15": hi15 - lo15,
               "r30": (hi30 - lo30) if hi30 is not None else None, "P": P, "floor": f, "T": T, "TA": TA, "miss": z15["miss"],
               "z5": z5, "z15": z15, "atm": z15["atm"], "step": step, "checks": {}}
        legs = [(m, d) for m, d in legs if mins(t) - m <= CHOP_WIN]
        if abs(m15) >= P:
            legs.append((mins(t), 1 if m15 > 0 else -1))
        both_ways = {d for _, d in legs} == {1, -1}
        if abs(m15) >= P:
            d = 1 if m15 > 0 else -1
            lose, win = ("CE", "PE") if d > 0 else ("PE", "CE")
            lp, la = losing(z15[lose], T[lose])
            wp, wa = winning(z15[win], T[win], TA[win])
            fast = False
            if lp == "QUIET" and wp == "QUIET":                 # a sharp turn: the 15-min window still carries the old flow
                lp, la = losing(z5[lose], T5[lose])
                wp, wa = winning(z5[win], T5[win], TA5[win])
                fast = lp != "QUIET" or wp != "QUIET"
            with15, against15 = z15[lose]["cuts"] + z15[win]["adds"], z15[lose]["adds"]
            with5, against5 = z5[lose]["cuts"] + z5[win]["adds"], z5[lose]["adds"]
            w_, a_ = (with5, against5) if fast else (with15, against15)
            if lp == "QUIET" and wp == "QUIET":
                qual = "BINA OI"
            elif a_ >= w_:
                qual = "ULTA"
            elif w_ >= SAATH_X * a_:
                qual = "SAATH"
            else:
                qual = "MILA-JULA"
            if qual == "BINA OI" and both_ways:
                move = None
                row.update(word="CHOP", size=row["r30"] / P if row["r30"] else None, agree=None, why="leg bina OI, dono taraf")
                rows.append(row)
                continue
            if move is None or move["dirn"] != d:
                move = {"dirn": d, "peak": with5, "since": t, "n": 0, "w5": [], "thak": 0}
            move["n"] += 1
            new_ext = (d > 0 and spot >= hi15) or (d < 0 and spot <= lo15)
            prev = move["w5"][-5] if len(move["w5"]) >= 5 else None
            if move["n"] <= HOLD:
                phase = "SHURU"
            elif prev is not None and with5 >= TEZ_X * max(prev, f[win]["add"] / 3) and new_ext:
                phase = "TEZ"
            else:
                phase = "BARABAR"
            tired = with5 <= THAK_X * move["peak"] or (m5 * d < 0 and against5 >= with5)
            move["thak"] = move["thak"] + 1 if tired else 0
            if move["n"] > HOLD and move["thak"] >= HOLD:
                phase = "THAK RAHA"
            move["w5"].append(with5)
            move["peak"] = max(move["peak"], with5)
            zl, zw = (z5[lose], z5[win]) if fast else (z15[lose], z15[win])
            fn, fa = ("net5", "add5") if fast else ("net", "add")
            lose_size = max(abs(zl["near"]), abs(zl["wall"])) / f[lose][fn]
            win_size = (zw["adds"] / f[win][fa] if wp == "PRESS" else abs(zw["near"]) / f[win][fn] if wp == "BOOK" else 0)
            agree = [x for x in (la, wa) if x is not None]
            row.update(word="CHAL RAHA", dirn=d, qual=qual, phase=phase, lose=lose, win=win, lose_pat=lp, win_pat=wp,
                       with15=with15, against15=against15, with5=with5, against5=against5, since=move["since"],
                       lose_k=biggest(zl, -1 if lp in ("ROLL", "RETREAT") else 1),
                       wall_k=biggest(zl, 1) if lp == "ROLL" else None,
                       win_k=biggest(zw, 1 if wp == "PRESS" else -1), fast=fast,
                       size=(abs(m15) / P) if qual == "BINA OI" else max(lose_size, win_size),
                       agree=min(agree) if agree else None)
        else:
            move = None
            ce, pe = z15["CE"], z15["PE"]
            net = {s: z15[s]["near"] + z15[s]["wall"] for s in ("CE", "PE")}
            if both_ways:
                row.update(word="CHOP", size=row["r30"] / P if row["r30"] else None, agree=None, why="dono taraf legs")
            elif (z30 is not None and r45[0] is not None and r45[0] - r45[1] < PIN_RNG * P
                  and all(z30[s]["near"] + z30[s]["wall"] >= 3 * T[s] for s in ("CE", "PE"))):
                c30, p30 = z30["CE"], z30["PE"]
                k = max(z30["nk"], key=lambda k: max(c30["per"].get(k, 0), 0) + max(p30["per"].get(k, 0), 0))
                coi, poi = g[t]["oi"][k]
                ag = [x for x in (_share(c30["near_up"] + c30["wall_up"], c30["near_dn"] + c30["wall_dn"]),
                                  _share(p30["near_up"] + p30["wall_up"], p30["near_dn"] + p30["wall_dn"])) if x is not None]
                row.update(word="PIN", k=k, kc=biggest(c30, 1), kp=biggest(p30, 1), at_spot=abs(k - spot) <= step, z30=z30, r45=r45[0] - r45[1],
                           balanced=abs(coi - poi) <= PIN_BAL * max(coi, poi, 1),
                           size=min((c30["near"] + c30["wall"]) / (3 * f["CE"]["net"]), (p30["near"] + p30["wall"]) / (3 * f["PE"]["net"])),
                           agree=min(ag) if ag else None)
            elif net["CE"] <= -T["CE"] and net["PE"] <= -T["PE"]:
                row.update(word="UNWIND", size=min(-net["CE"] / f["CE"]["net"], -net["PE"] / f["PE"]["net"]),
                           agree=_share(ce["near_dn"] + ce["wall_dn"] + pe["near_dn"] + pe["wall_dn"],
                                        ce["near_up"] + ce["wall_up"] + pe["near_up"] + pe["wall_up"]))
            else:
                side = None
                for s, o in (("CE", "PE"), ("PE", "CE")):
                    if net[s] >= BADA * f[s]["net"] and net[o] < T[o]:
                        side = s
                if side:
                    z = z15[side]
                    k = biggest(z, 1)
                    loads = [x for x in loads if mins(t) - x[0] <= PIN_WIN]
                    other = [x for x in loads if x[1] != side and abs(x[2] - k) <= step]
                    if (other and r45[0] is not None and r45[0] - r45[1] < PIN_RNG * P and z30 is not None
                            and all(z30[s]["near"] + z30[s]["wall"] > 0 for s in ("CE", "PE"))):   # both still net adding over 45
                        coi, poi = g[t]["oi"][k]
                        row.update(word="PIN", k=k, kc=k if side == "CE" else other[-1][2], kp=k if side == "PE" else other[-1][2],
                                   at_spot=abs(k - spot) <= step, z30=z30, r45=r45[0] - r45[1], turns=True,
                                   balanced=abs(coi - poi) <= PIN_BAL * max(coi, poi, 1), size=net[side] / f[side]["net"],
                                   agree=_share(z["near_up"] + z["wall_up"], z["near_dn"] + z["wall_dn"]))
                    else:
                        row.update(word="LOAD", side=side, k=k, size=net[side] / f[side]["net"],
                                   agree=_share(z["near_up"] + z["wall_up"], z["near_dn"] + z["wall_dn"]))
                    loads.append((mins(t), side, k))
                else:
                    row.update(word="KHAMOSH", size=None, agree=None)
        rows.append(row)
    _grade(rows)
    return rows, P, step


def key(r):
    w = r["word"]
    if w == "CHAL RAHA":
        # the STORY is direction + with / against the writers + a speed change; the side patterns are its explanation
        # and may flicker PRESS <-> QUIET minute to minute without the story changing
        return (w, r["dirn"], r["qual"] if r["qual"] in ("ULTA", "BINA OI") else "WITH", r["phase"] if r["phase"] in ("TEZ", "THAK RAHA") else "")
    if w == "PIN":
        return (w, r["k"])
    if w == "LOAD":
        return (w, r["side"])
    return (w,)


def _grade(rows):
    """Persistence (marks the key has held) and the check count. Peers are added later by `peers`."""
    run, n = None, 0
    for r in rows:
        if r["word"] == "SOCH RAHA":
            run, n = None, 0
            continue
        k = key(r)
        n = n + 1 if k == run else 1
        run = k
        r["held"] = n
        if r["word"] == "KHAMOSH":
            r["grade"] = None
            continue
        c = r["checks"]
        c["bar"] = (r.get("size") or 0) >= BAR
        c["bada"] = (r.get("size") or 0) >= BADA
        c["held3"] = n >= HOLD
        c["held9"] = n >= 3 * HOLD
        if r.get("agree") is not None:
            c["strikes"] = r["agree"] >= 2 / 3
        r["grade"] = sum(1 for v in c.values() if v)


def peers(rows, others):
    """The peer check: both other indices showed the same word (+ direction) within the last PEER_LAG marks."""
    tabs = [{r["t"]: (r["word"], r.get("dirn"), r.get("side")) for r in o} for o in others]
    for r in rows:
        if r["word"] in ("KHAMOSH", "SOCH RAHA"):
            continue
        me, m = (r["word"], r.get("dirn"), r.get("side")), mins(r["t"])
        same = 0
        for tb in tabs:
            if any(tb.get(f"{(m - j) // 60:02d}:{(m - j) % 60:02d}") == me for j in range(PEER_LAG + 1)):
                same += 1
        r["checks"]["peers"] = same == len(others) and len(others) > 0
        r["peers"] = same
        r["grade"] = sum(1 for v in r["checks"].values() if v)


def stamped(rows):
    """The lines she would have seen: a new story key held HOLD marks, stamped at its first mark."""
    out, cur, run, n = [], None, None, 0
    for i, r in enumerate(rows):
        k = key(r) if r["word"] != "SOCH RAHA" else ("SOCH RAHA",)
        n = n + 1 if k == run else 1
        run = k
        if n == HOLD and k != cur:
            out.append(rows[i - HOLD + 1])
            cur = k
    return out


def front_stamps(g):
    """§1d's own BUILDING / STALLED / UNWINDING on the top-2 strikes per side by OI (fronts.read's rule: a 15-mark
    slope against 5 % of the front's own peak change; UNWINDING at 15 % off the peak with a falling slope), a change
    held HOLD marks, stamped at its first mark. 'phir BUILDING' = building again after a stall or unwind (her 10:21
    question). UNWINDING while the same side's next strike outward is BUILDING reads SHIFT -> k2 (the wall rolled)."""
    ts = sorted(g)
    series, run, out = {}, {}, []

    def state(k, s):
        v = series.get((k, s)) or []
        if len(v) <= 15:
            return None
        chg, pk = v[-1], max(v)
        slope = chg - v[-16]
        scale = max(abs(pk), 1.0)
        if pk - chg >= 0.15 * scale and slope < 0:
            return "UNWINDING"
        if abs(slope) <= 0.05 * scale:
            return "STALLED"
        return "BUILDING" if slope > 0 else "UNWINDING"

    for t in ts:
        now = g[t]
        nk = nine(list(now["k"]), now["spot"])
        step = step_of(nk)
        for k in now["k"]:
            for i, s in enumerate(("CE", "PE")):
                series.setdefault((k, s), []).append(now["k"][k][i])
        for i, s in enumerate(("CE", "PE")):
            for k in sorted(nk, key=lambda k: -now["oi"][k][i])[:2]:
                st_ = state(k, s)
                if st_ is None:
                    continue
                st = run.setdefault((k, s), [None, 0, None])
                st[1] = st[1] + 1 if st_ == st[0] else 1
                st[0] = st_
                if st[1] == HOLD and st_ != st[2]:
                    if st[2] is None:                       # entering the top-2 is not a change
                        st[2] = st_
                        continue
                    word = "phir BUILDING" if st_ == "BUILDING" else st_
                    if st_ == "UNWINDING" and state(k + (step if s == "CE" else -step), s) == "BUILDING":
                        word = f"SHIFT -> {k + (step if s == 'CE' else -step):.0f}"
                    v = series[(k, s)]
                    out.append({"t": ts[ts.index(t) - HOLD + 1], "k": k, "side": s, "flow": st_, "word": word,
                                "d15": v[-1] - v[-16], "spot": now["spot"], "prev": st[2]})
                    st[2] = st_
    return out


def line(r):
    """One stamped line, as the screen would print it (numbers in lakh, levels tagged s = spot)."""
    if r["word"] == "SOCH RAHA":
        return f"{r['t']}  SOCH RAHA · {r['why']}"
    g = f"{GRADE_WORD(r['grade'])} {r['grade']}/{len(r['checks'])}" if r.get("grade") is not None else "—"
    if "peers" in r:
        g += f" (peers {r['peers']}/2)"
    head = f"{r['t']}  {r['spot']:>8.0f}s  "
    w = r["word"]
    if w == "CHAL RAHA":
        arrow = "▲" if r["dirn"] > 0 else "▼"
        lose = f"{r['lose']} {r['lose_pat']}"
        if r["lose_pat"] == "ROLL" and r.get("wall_k"):
            lose += f" {r['lose_k']:.0f}->{r['wall_k']:.0f}"
        elif r.get("lose_k") and r["lose_pat"] != "QUIET":
            lose += f" {r['lose_k']:.0f}"
        win = f"{r['win']} {r['win_pat']}" + (f" {r['win_k']:.0f}" if r.get("win_k") and r["win_pat"] != "QUIET" else "")
        if r.get("fast"):
            lose += " (abhi)"
        return (head + f"CHAL RAHA {arrow} {r['qual']:<9} {r['phase']:<9} {lose:<26} {win:<16} "
                f"with15 {lakh(r['with15']):>7} against15 {lakh(r['against15']):>7}  m15 {r['m15']:+4.0f}  {g}")
    if w == "PIN":
        where = f"PIN {r['k']:.0f}" if r["at_spot"] else f"PIN · dono deewar CE {r['kc']:.0f} / PE {r['kp']:.0f}"
        c, p = r["z30"]["CE"], r["z30"]["PE"]
        where += " · baari-baari" if r.get("turns") else ""
        return head + f"{where}{' balanced' if r['balanced'] else ''}  net45 CE {lakh(c['near'] + c['wall'])} PE {lakh(p['near'] + p['wall'])}  r45 {r['r45']:.0f}  {g}"
    if w == "LOAD":
        z = r["z15"][r["side"]]
        return head + f"LOAD {r['side']} likh rahe {r['k']:.0f}  net15 {lakh(z['near'] + z['wall'])}  m15 {r['m15']:+4.0f}  {g}"
    if w == "UNWIND":
        c, p = r["z15"]["CE"], r["z15"]["PE"]
        return head + f"UNWIND {'band ka unwind' if r['t'] >= '15:00' else 'dono nikal rahe'}  CE {lakh(c['near'] + c['wall'])} PE {lakh(p['near'] + p['wall'])}  {g}"
    if w == "CHOP":
        return head + f"CHOP · {r['why']}  r30 {r['r30']:.0f} net30 {r['m30']:+.0f}  {g}"
    return head + "KHAMOSH · kuch khaas nahi"


def load(idx, day):
    p = os.path.join(CHAIN, f"chain_{idx}_{day}.jsonl")
    if not os.path.exists(p):
        p += ".gz"
    return grid(p) if os.path.exists(p) else None


def replay(idx, day, show_all=False, with_peers=True, out=print, fronts=12):
    g = load(idx, day)
    if not g:
        out(f"== RAFTAAR {idx} {day}: no record ==")
        return None
    rows, P, step = read_day(g)
    if with_peers:
        others = []
        for o in ("NIFTY", "BANKNIFTY", "SENSEX"):
            if o != idx:
                og = load(o, day)
                if og:
                    others.append(read_day(og)[0])
        peers(rows, others)
    out(f"== RAFTAAR {idx} {day}  P = {P:.0f} pts  step {step}  (floors = the day's own running medians per side) ==")
    lo, hi = show_all if isinstance(show_all, tuple) else ("00:00", "24:00")
    for r in (rows if show_all else stamped(rows)):
        if lo <= r["t"] <= hi:
            out(line(r))
    census = {}
    for r in rows:
        w = r["word"] if r["word"] != "CHAL RAHA" else f"CHAL RAHA {'▲' if r['dirn'] > 0 else '▼'} {r['qual']}"
        census[w] = census.get(w, 0) + 1
    out("-- minutes: " + ", ".join(f"{k} {v}" for k, v in sorted(census.items(), key=lambda kv: -kv[1])))
    out(f"-- stamped lines: {len(stamped(rows))}")
    fs = front_stamps(g)
    out(f"-- front stamps (§1d states, top-2 per side): {len(fs)}")
    for e in fs[:fronts]:
        out(f"   {e['t']}  {e['side']} {e['k']:.0f}  {e['word']:<14} d15 {lakh(e['d15']):>7} @ {e['spot']:.0f}s  (was {e['prev']})")
    return rows


def check():
    """Synthetic: price flat, then +6/min while the ITM calls cover and puts add -> KHAMOSH, then CHAL RAHA ▲ SAATH."""
    g = {}
    ks = [22500 + 50 * i for i in range(17)]
    for m in range(0, 60):
        t = f"{(9 * 60 + 16 + m) // 60:02d}:{(9 * 60 + 16 + m) % 60:02d}"
        spot = 22850 + max(0, m - 40) * 6
        k, oi = {}, {}
        for s in ks:
            ce = 1e6 + (-(m - 40) * 4e4 if m > 40 and s <= 22850 else 0) + m * 500 * (1 + (s % 7))
            pe = 1e6 + ((m - 40) * 4e4 if m > 40 and s <= 22900 else 0) + m * 500 * (1 + (s % 5))
            k[s] = (ce - 1e6, pe - 1e6)
            oi[s] = (ce, pe)
        g[t] = {"spot": spot, "atm": 22850, "k": k, "oi": oi}
    rows, P, step = read_day(g)
    last = rows[-1]
    assert last["word"] == "CHAL RAHA" and last["dirn"] == 1, last["word"]
    assert last["lose_pat"] in ("RETREAT", "ROLL") and last["win_pat"] == "PRESS", (last["lose_pat"], last["win_pat"])
    assert last["qual"] == "SAATH", last["qual"]
    flat = [r for r in rows if r["word"] != "SOCH RAHA" and r["t"] < "09:55"]
    assert flat and all(r["word"] in ("KHAMOSH", "PIN") for r in flat), {r["word"] for r in flat}
    assert stamped(rows), "nothing stamped"
    print("check ok:", line(last))


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        a = sys.argv
        win = (a[a.index("--all") + 1], a[a.index("--all") + 2]) if "--all" in a and len(a) > a.index("--all") + 2 else ("--all" in a)
        replay(a[1], a[2], show_all=win)
