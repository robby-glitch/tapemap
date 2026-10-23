"""daytype.py -- AAJ KA DIN: is today a TREND day or a PIN/CHOP day? Read live off the futures' own 5-min bars.

Mary, 2026-10-05: "its important for us to figure our if its pin/chop day or trend day". The answer band's
verdict changed 66 times that day, never named the 09:50-12:10 leg down, and said STAND ASIDE in its middle.
This names the DAY instead, slowly -- one type, held, with the evidence and the level that would change it.

    TREND ▼/▲  ENTER: >= RUN_IN closed bars in a row on one side of the session VWAP, the last close
               >= DIST_IN median bar ranges from it, and the last 30 min (W bars) moved >= NET_IN
               ranges that way, AND it has SIZE: the close is >= SIZE x IB away from the leg's swing (its
               extreme since it crossed VWAP) or from VWAP, IB = the smaller of today's initial balance
               (once built) and the prior sessions' median (`ib_ref`), else the range so far. (Added
               2026-10-05: the check day's close read TREND ▼ for a 17-pt drift. Plain today's IB delayed
               SENSEX 28 Sep's leg by 60 min on its 398-pt gap IB, hence the smaller of the two.)
               STAY while no close is more than TOL ranges back across VWAP and the
               leg (its start: the extreme since the last opposite trend, or the open -> its extreme
               since) has not been RETRACE given back.
    PIN/CHOP   >= X_PIN VWAP crosses in the last hour (X_WIN bars) -- X_PIN_BOX when expiry is <= 1
               day out and spot sits between the two biggest-OI strikes, PE below, CE above (the pin pull).
    TWO-SIDED  neither.
    EARLY      until the initial balance (09:15-10:15) is built and two closed bars agree.

The SHOWN type changes only when the new one shows on HOLD closed bars in a row AND the shown one has
lasted MIN_LIFE minutes -- unless a bar closes past the shown type's own `changes_if` level (a decisive
break), which switches it at once. One more decisive event ENDS a shown trend at once (added
2026-10-05, after the check day's 12:10-13:40 short-covering V read TREND ▼ until 13:45): the trap layer
(trap.py, via story._trap_rows) stamps FAILED at a KEY level and the side it traps IS the trend's side
(sellers phanse in TREND ▼, buyers in TREND ▲). Applied at the close of the 5-min bar the stamp falls in,
"since" the stamp's minute; the type becomes the bar's raw PIN/CHOP, else TWO-SIDED; and the same trend
may not start again until a close goes past that trend's extreme or back across VWAP (the V it starts has
to finish before a new leg counts). A second ender -- futures OI falling against the trend for 2 bars -- was tried and dropped:
it added switches on the tuning days (SENSEX and BANKNIFTY 2026-10-01, +2 each). Thresholds tuned 2026-10-05 on the recorded sessions 2026-09-22 ..
2026-10-01 only; 2026-10-05 is the check (test_daytype.py). One off-by-one was fixed after reading the check
day -- a trend's leg started AFTER the bar where the opposite trend ended, not on it -- and changed nothing on
the tuning days. A change is a new REV with its date.

Every number in a chip is [M] (bars, OI, the chain); the type is [I]. Pure: no I/O, no clock -- the caller
hands in the closed bars (ux_log's), the chain's minute grid and open OI (the poller's, or
sides_log.load_session's), the sides slots, the other indices' bars and `now`, so a restart rebuilds the
same day (the anytime-start rule). DISPLAY ONLY: it gates nothing and logs nothing.
"""
from __future__ import annotations

import bisect
import statistics

import board
import fronts
import grounds
import sides
import story

REV = "daytype-1 (2026-10-05)"
OPEN, CLOSE, IB_END = 9 * 60 + 15, 15 * 60 + 30, 10 * 60 + 15
W, X_WIN = 6, 12                 # 30 min for the net move, 60 min for the VWAP crosses
RUN_IN, DIST_IN, NET_IN = 3, 0.75, 0.5
TOL, RETRACE = 0.25, 0.5         # a poke back across VWAP under TOL ranges is not a cross; half the leg given back ends it
X_PIN, X_PIN_BOX = 3, 2
HOLD, MIN_LIFE = 2, 15
SIZE = 0.5                       # a trend's move, in initial balances (tuned on 2026-09-22 .. 2026-10-01)
BASIS_MIN = 15                   # her basis: future minus the index, median of the pairs closing in the last 15 min
ARROW = {1: "▲", -1: "▼", 0: ""}
NAME = {"TREND": "TREND", "PIN": "PIN/CHOP", "TWO": "TWO-SIDED", "EARLY": "EARLY"}
SHORT = {"NIFTY": "NIFTY", "SENSEX": "SENSEX", "BANKNIFTY": "BN"}
KEY = ("PDC", "PDH", "PDL", "OPEN", "ROUND")     # the trap levels whose FAILED ends a trend
WHO = {1: "buyers phanse", -1: "sellers phanse"}


def _m(t_ms):
    return board.mm(grounds._hh(t_ms))


def _bars(raw, now=None):
    """Closed session bars, oldest first, each with its cumulative VWAP (ladder volume at price; typical price
    x vol for a bar that carries no ladder). A bar starting at m is closed once the clock reads m + 5."""
    out, pv, v = [], 0.0, 0.0
    for b in sorted((b for b in raw or () if isinstance(b, dict) and isinstance(b.get("t"), (int, float))
                     and b.get("c") is not None), key=lambda b: b["t"]):
        m = _m(b["t"])
        if not OPEN <= m < CLOSE or (now is not None and m + 5 > now):
            continue
        lad = b.get("ladder") or ()
        for r in lad:
            q = (r.get("b") or 0) + (r.get("s") or 0) + (r.get("u") or 0)
            pv, v = pv + r["p"] * q, v + q
        if not lad:
            q = b.get("vol") or 0
            pv, v = pv + (b["h"] + b["l"] + b["c"]) / 3 * q, v + q
        out.append({"m": m, "t": board.hm(m), "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"],
                    "oi": b.get("oi"), "vw": pv / v if v else b["c"]})
    return out


def _side(b):
    return 1 if b["c"] >= b["vw"] else -1


def _crosses(B, j0, i):
    s = [_side(x) for x in B[max(0, j0):i + 1]]
    return sum(1 for a, c in zip(s, s[1:]) if a != c)


def _atr(B, i):
    return statistics.median(x["h"] - x["l"] for x in B[:i + 1]) or 1.0


def ib_of(B, i=None):
    """The initial balance (09:15-10:15 range) of `_bars` output, or None until its last bar has closed (bar i)."""
    ib = [x for x in B[:None if i is None else i + 1] if x["m"] < IB_END]
    if not ib or ib[-1]["m"] + 5 < IB_END:
        return None
    return max(x["h"] for x in ib) - min(x["l"] for x in ib)


def _raw(B, i, prev, box, raws, block=None, ib_ref=None):
    """(type, dir, leg) of bar i alone, given the previous bar's and the raws before it -- the entry/stay rules in
    the docstring. `leg` is a trend's (start, extreme); `block` {dir: extreme} bars a trend a FAIL ended from
    starting again until a close goes past that extreme or back across VWAP."""
    b, side, atr = B[i], _side(B[i]), _atr(B, i)
    if prev[0] == "TREND":
        d, (st, ex) = prev[1], prev[2]
        ex = min(ex, b["l"]) if d < 0 else max(ex, b["h"])
        back = (b["c"] - ex) * -d / (abs(st - ex) or 1.0)
        if (b["c"] - b["vw"]) * d > -TOL * atr and back < RETRACE:
            return ("TREND", d, (st, ex))
    run = 1
    while run <= i and _side(B[i - run]) == side:
        run += 1
    net = b["c"] - B[max(0, i - W)]["c"]
    swing = B[max(0, i - run):i + 1]
    swing = max(x["h"] for x in swing) if side < 0 else min(x["l"] for x in swing)
    ib = [x for x in (ib_of(B, i), ib_ref) if x]        # the smaller: a gap-open IB must not hide a real leg
    ib = min(ib) if ib else max(x["h"] for x in B[:i + 1]) - min(x["l"] for x in B[:i + 1])
    big = max(abs(b["c"] - swing), abs(b["c"] - b["vw"])) >= SIZE * ib
    for d in list(block or ()):
        if (b["c"] - block[d]) * d > 0 or side != d:      # past the extreme, or back across VWAP: a fresh leg may start
            del block[d]
    if block and side in block:
        run = 0
    if run >= RUN_IN and abs(b["c"] - b["vw"]) >= DIST_IN * atr and net * side >= NET_IN * atr and big:
        k = max((j for j, r in enumerate(raws) if r == ("TREND", -side)), default=0)   # its last bar holds the swing
        st = max(x["h"] for x in B[k:i + 1]) if side < 0 else min(x["l"] for x in B[k:i + 1])
        seg = B[i - run + 1:i + 1]
        return ("TREND", side, (st, min(x["l"] for x in seg) if side < 0 else max(x["h"] for x in seg)))
    if _crosses(B, i - X_WIN + 1, i) >= (X_PIN_BOX if box else X_PIN):
        return ("PIN", 0, None)
    return ("TWO", 0, None)


def _levels(lab, B, i):
    """changes_if for the shown type at bar i, futures scale: {up/down: (price, why, flips)}. `flips` = a
    close past it changes the type at once (a trend's own extension does not)."""
    t, d, s = lab["type"], lab["dir"], lab["since"]
    hi, lo = max(x["h"] for x in B[:i + 1]), min(x["l"] for x in B[:i + 1])
    if t == "TREND":
        vw = (B[i]["vw"], f"VWAP ke {'neeche' if d > 0 else 'upar'} close = trend khatam", True)
        ext = (hi if d > 0 else lo, f"naya {'high' if d > 0 else 'low'} = trend jari", False)
        return {"up": ext, "down": vw} if d > 0 else {"up": vw, "down": ext}
    if t == "PIN":
        seg = B[s:i + 1]
        return {"up": (max(x["h"] for x in seg), "box ke upar close = pin toota", True),
                "down": (min(x["l"] for x in seg), "box ke neeche close = pin toota", True)}
    if t == "TWO":
        seg = B[max(0, i - X_WIN + 1):i + 1]
        return {"up": (max(x["h"] for x in seg), "ghante ke high ke upar close", True),
                "down": (min(x["l"] for x in seg), "ghante ke low ke neeche close", True)}
    return {"up": (hi, "IB ka high ab tak", True), "down": (lo, "IB ka low ab tak", True)}


def timeline(B, boxes=None, fails=None, ib_ref=None):
    """Bar by bar: the raw (type, dir) and the SHOWN label, with its hysteresis. -> (raws, labels), where labels
    is every label shown, oldest first: {type, dir, since (bar index its evidence began), named (bar index it
    was first shown on; visible at that bar's close)} and, for a trend ENDED, `end` (the chip) and `since_t`.
    `fails`: {bar index: [(trapped side, chip, 'HH:MM')]}, the KEY-level FAILED stamps."""
    boxes, fails = boxes or [False] * len(B), fails or {}
    raws, labels, lev, prev, block = [], [], None, ("", 0, None), {}
    for i in range(len(B)):
        prev = _raw(B, i, prev, boxes[i], raws, block, ib_ref)
        r = prev[:2]
        raws.append(r)
        tol = TOL * _atr(B, i)
        cur = labels[-1] if labels else None
        new = False
        if cur is None:
            labels.append({"type": "EARLY", "dir": 0, "since": 0, "named": i})
            cur = labels[-1]
        if cur["type"] == "TREND":
            d = cur["dir"]
            f = next((x for x in fails.get(i, ()) if x[0] == d), None)
            if f:
                seg = B[cur["since"]:i + 1]
                block[d] = min(x["l"] for x in seg) if d < 0 else max(x["h"] for x in seg)
                t = r[0] if r[0] == "PIN" else "TWO"
                labels.append({"type": t, "dir": 0, "named": i, "end": f[1], "since": i, "since_t": f[2]})
                prev, raws[-1] = (t, 0, None), (t, 0)
                lev = _levels(labels[-1], B, i)
                continue
        if cur["type"] == "EARLY":
            new = B[i]["m"] + 5 >= IB_END and i >= 1 and raws[-2] == r
        elif r != (cur["type"], cur["dir"]):
            held = len(raws) >= HOLD and all(x == r for x in raws[-HOLD:])
            old = B[i]["m"] - B[cur["named"]]["m"] >= MIN_LIFE
            brk = lev is not None and any(f and ((k == "up" and B[i]["c"] > p + tol) or (k == "down" and B[i]["c"] < p - tol))
                                          for k, (p, _, f) in lev.items())
            new = brk or (held and old)
        if new:
            labels.append({"type": r[0], "dir": r[1], "since": _since(B, i, r, cur), "named": i})
        lev = _levels(labels[-1], B, i)
    return raws, labels


def _since(B, i, r, cur):
    """Where the new type's evidence began: a trend at the start of its VWAP-side run, a pin at the first cross
    of its hour, anything after a trend at the bar after that trend's extreme; never before the shown one's."""
    if r[0] == "TREND":
        j = i
        while j > 0 and _side(B[j - 1]) == r[1]:
            j -= 1
    elif cur["type"] == "TREND":
        seg = range(cur["since"], i + 1)
        j = (max(seg, key=lambda k: B[k]["h"]) if cur["dir"] > 0 else min(seg, key=lambda k: B[k]["l"])) + 1
        if r[0] == "PIN":
            j = max(j, _first_cross(B, i))
    elif r[0] == "PIN":
        j = _first_cross(B, i)
    else:
        j = i
    return min(i, max(j, 0 if cur["type"] == "EARLY" else cur["since"] + 1))


def _first_cross(B, i):
    for j in range(max(1, i - X_WIN + 1), i + 1):
        if _side(B[j]) != _side(B[j - 1]):
            return j
    return i


def _fails(trap_events, day, B):
    """{bar index: [(trapped side, chip, 'HH:MM')]} -- each KEY-level FAILED stamp at the bar it falls in."""
    out = {}
    for r in story._trap_rows({"events": trap_events}, day):
        if r["state"] != "FAILED" or r["level"] not in KEY or r["dir"] not in WHO or r.get("px") is None:
            continue
        t = grounds._hh(r["t_ms"])
        j = next((k for k, b in enumerate(B) if b["m"] <= board.mm(t) < b["m"] + 5), None)
        if j is not None:
            out.setdefault(j, []).append((r["dir"], f"FAIL · {r['level']} {_f(r['px'])} spot · {WHO[r['dir']]} {t}", t))
    return out


def _label_word(lab):
    return NAME[lab["type"]] + (" " + ARROW[lab["dir"]] if lab["dir"] else "")


def _grid_at(minutes, keys, m):
    """The chain's minute record at or before minute m (the last snapshot of a minute wins), within 5 min."""
    j = bisect.bisect_right(keys, board.hm(m)) - 1
    if j < 0 or board.mm(keys[j]) < m - 5:
        return None
    return minutes[keys[j]]


def _walls(rec, opens):
    """((pe_k, pe_oi), (ce_k, ce_oi), step) -- the biggest-OI strike each side on this minute's grid."""
    ce, pe = {}, {}
    for k, v in ((rec or {}).get("k") or {}).items():
        n = fronts._num(k)
        if n is None:
            continue
        c, p = fronts._pair(v)
        if (n, "ce") in opens:
            ce[n] = opens[(n, "ce")] + c
        if (n, "pe") in opens:
            pe[n] = opens[(n, "pe")] + p
    if not ce or not pe:
        return None
    ks = sorted(set(ce) | set(pe))
    step = min((b - a for a, b in zip(ks, ks[1:]) if b > a), default=None)
    return max(pe.items(), key=lambda x: x[1]), max(ce.items(), key=lambda x: x[1]), step


def _box(rec, opens, dte):
    """The pin pull: expiry <= 1 day out, spot between the PE wall below and the CE wall above, <= 4 steps apart."""
    if dte is None or dte > 1 or rec is None or rec.get("spot") is None:
        return False
    w = _walls(rec, opens)
    if not w or not w[2]:
        return False
    (pk, _), (ck, _), step = w
    return pk < ck and pk <= float(rec["spot"]) <= ck and ck - pk <= 4 * step


def _f(x):
    return f"{x:,.0f}"


def _oi_chip(B, s, i, roll, named_contract):
    """Futures OI against price since the type began, and over the last 30 min (the phase inside it)."""
    if roll:
        return {"chip": board.CC + f"fut OI: {roll}", "tag": "M"}
    if not named_contract:
        return {"chip": board.CC + "fut OI: bar mein contract ka naam nahi, roll check nahi ho sakta", "tag": "M"}

    def who(j):
        a = B[j - 1] if j > 0 else B[0]
        if a.get("oi") is None or B[i].get("oi") is None:
            return None
        doi, dp = B[i]["oi"] - a["oi"], B[i]["c"] - a["c"]
        w = ("naye long" if doi > 0 else "short covering") if dp > 0 else ("naye short" if doi > 0 else "long nikal rahe")
        return f"{board.L(doi)} · bhav {dp:+.0f} → {w}"
    seg, last = who(s), who(max(0, i - W + 1))
    if seg is None:
        return {"chip": board.CC + "fut OI: bar mein OI nahi", "tag": "M"}
    return {"chip": f"fut OI {seg} ({B[s]['t']} se)" + (f" · 30 min: {last}" if i - s >= W else ""), "tag": "M"}


def _writers_chip(rows, since_t, asof_t, d):
    """The option writers (sides.py slots) since the type began: the last POWER slot -- for a trend, the last one
    pushing WITH it (REAL / SQUEEZE / BACKED its way)."""
    if rows is None:
        return {"chip": board.CC + "writers: aaj ka sides read nahi mila", "tag": "M"}
    win = [r for r in rows if r.get("t") and since_t < r["t"] <= asof_t and r.get("kind", "slot") == "slot"]
    pw = [r for r in win if r.get("power") and r.get("dir")
          and (not d or (r["dir"] == d and r.get("word") in ("REAL", "SQUEEZE", "BACKED")))]
    if not pw:
        return {"chip": board.NONE + f"writers: {len(win)} slot ({since_t} se), koi POWER "
                                     + (f"{ARROW[d]} ki taraf " if d else "") + "nahi", "tag": "M"}
    r, bits = pw[-1], []
    for s, side in (("p", "pe"), ("c", "ce")):
        if r.get(f"{s}_power") and (side, r.get(f"{s}_state")) in sides.ACTION:
            bits.append(f"{sides.ACTION[(side, r[f'{s}_state'])].lower()} ×{r.get(f'{s}_ratio')} · "
                        f"{r.get(f'{s}_same9')}/9")
    return {"chip": f"{' + '.join(bits) or r.get('word')} ({r['t']}{', subah · gawah' if r.get('morning') else ''})"
                    f" · POWER slot {len(pw)}", "tag": "M"}


def _peers_chip(idx, B, peers):
    """Each index's last close against its OWN session VWAP. Her rule: NIFTY + SENSEX are counted, BN a witness."""
    t, out = B[-1]["m"], []
    for k in ("NIFTY", "SENSEX", "BANKNIFTY"):
        P = B if k == idx else _bars((peers or {}).get(k), t + 5)
        out.append(f"{SHORT[k]} {ARROW[_side(P[-1])] if P else '?'}" + (" gawah" if k == "BANKNIFTY" else ""))
    return {"chip": " · ".join(out) + " (VWAP ke hisaab)", "tag": "M"}


def read(idx, day, bars, now=None, minutes=None, opens=None, dte=None, sides_rows=None, peers=None, trap_events=None,
         ib_ref=None):
    """The day type at the last closed bar. `bars`: the index's ux bars (ux_log rows); `now`: clock minutes (None =
    every bar is closed); `minutes`/`opens`: the chain grid + open OI; `dte`: days to the option expiry;
    `sides_rows`: today's sides slots for idx (None = could not read); `peers`: {idx: ux bars};
    `trap_events`: the trap layer's state rows for idx today (None = could not read); `ib_ref`: the prior sessions'
    median initial balance, the SIZE floor's yardstick until today's is built (None: the range so far)."""
    B = _bars(bars, now)
    base = {"ok": False, "idx": idx, "day": day, "rev": REV, "tag": "I"}
    if not B:
        early = bars or (now is not None and now < OPEN + 5)
        return {**base, "why": board.NONE + "abhi koi 5-min bar band nahi hua (pehla 09:20 pe)" if early
                else board.CC + "aaj ka futures tape (ux) nahi mila"}
    minutes, opens = minutes or {}, opens or {}
    keys = sorted(k for k, v in minutes.items() if isinstance(v, dict) and v.get("spot") is not None)
    recs = [_grid_at(minutes, keys, b["m"] + 4) if keys else None for b in B]
    raw_last = bars[-1] if bars else {}
    roll = grounds.roll_why(day, raw_last.get("expiry"))
    fails = _fails(trap_events, day, B) if trap_events is not None else {}
    raws, labels = timeline(B, [_box(r, opens, dte) for r in recs], fails, ib_ref)
    i, lab = len(B) - 1, labels[-1]
    s = lab["since"]
    # her basis: future minus the index, 15-min median of the pairs (bar close, spot at its last minute)
    pairs = [B[j]["c"] - float(recs[j]["spot"]) for j in range(i + 1)
             if recs[j] and B[j]["m"] + 5 > B[i]["m"] + 5 - BASIS_MIN]
    basis = round(statistics.median(pairs), 1) if pairs else None
    lev = _levels(lab, B, i)
    chg = {k: {"fut": round(p, 1), "spot": None if basis is None else round(p - basis, 1),
               "text": f"{_f(p)} fut · " + (f"{_f(p - basis)} spot" if basis is not None else "spot ? (basis nahi)"),
               "why": why, "flips": f} for k, (p, why, f) in lev.items()}
    seg = B[s:i + 1]
    if lab["type"] == "TREND":
        n = sum(1 for x in seg if _side(x) == lab["dir"])
        vw_chip = f"{n}/{len(seg)} bar VWAP ke {'upar' if lab['dir'] > 0 else 'neeche'} ({B[s]['t']} se)"
    elif lab["type"] == "PIN":
        vw_chip = (f"VWAP cross {_crosses(B, i - X_WIN + 1, i)} / {min(X_WIN, i + 1)} bar (1 ghanta) · "
                   f"{B[s]['t']} se {_crosses(B, s, i)}")
    else:
        vw_chip = (f"VWAP se {B[i]['c'] - B[i]['vw']:+.0f} pts · cross {_crosses(B, i - X_WIN + 1, i)} "
                   f"/ {min(X_WIN, i + 1)} bar")
    ib = [x for x in B if x["m"] < IB_END]
    ih, il = max(x["h"] for x in ib), min(x["l"] for x in ib)
    if B[i]["m"] + 5 < IB_END:
        ib_chip = f"IB ban raha hai: {_f(il)}–{_f(ih)} ({ih - il:.0f}) abhi tak"
    else:
        hi, lo, r = max(x["h"] for x in B), min(x["l"] for x in B), (ih - il) or 1.0
        ext = [f"{w} {e / r:.1f}× IB" for w, e in (("upar", hi - ih), ("neeche", il - lo)) if e > 0]
        ib_chip = f"IB {_f(il)}–{_f(ih)} ({ih - il:.0f}) · " + (" · ".join(ext) if ext else "IB ke andar")
    w = _walls(recs[i], opens) if recs[i] else None
    if w is None:
        wall_chip = {"chip": board.CC + "walls: chain ka grid nahi mila", "tag": "M"}
    else:
        (pk, po), (ck, co), _ = w
        dd = "?" if dte is None else ("aaj expiry" if dte == 0 else "expiry kal" if dte == 1 else f"expiry {dte} din")
        wall_chip = {"chip": f"{dd} · {pk:.0f} PE {po / 1e5:.0f}L / {ck:.0f} CE {co / 1e5:.0f}L"
                             + (" · spot inke beech = pin khinchav" if _box(recs[i], opens, dte) else ""), "tag": "M"}
    since_t, asof_t = lab.get("since_t") or B[s]["t"], board.hm(B[i]["m"] + 5)
    last_fail = [x for j in sorted(fails) for x in fails[j]]
    trap_chip = ({"chip": board.CC + "trap: is din ka trap read nahi mila (trap-1 2026-10-04 se chalta hai)", "tag": "I"}
                 if trap_events is None else {"chip": last_fail[-1][1], "tag": "I"} if last_fail
                 else {"chip": board.NONE + "trap: aaj abhi tak koi key-level FAIL nahi", "tag": "I"})
    ev = [{"chip": vw_chip, "tag": "M"}, {"chip": ib_chip, "tag": "M"},
          _oi_chip(B, s, i, roll, raw_last.get("expiry")), _writers_chip(sides_rows, since_t, asof_t, lab["dir"]),
          _peers_chip(idx, B, peers), wall_chip]
    if lab.get("end"):
        ev.insert(0, {"chip": f"trend khatam: {lab['end']}", "tag": "I"})
    else:
        ev.append(trap_chip)
    segs = []
    for k, L in enumerate(labels):
        a = L["since"] if k else 0
        b = labels[k + 1]["since"] - 1 if k + 1 < len(labels) else i
        if b < a:
            continue
        p0 = B[a - 1]["c"] if a > 0 else B[0]["o"]
        segs.append({"from": (L.get("since_t") if k else None) or B[a]["t"], "to": board.hm(B[b]["m"] + 5),
                     "type": _label_word(L),
                     "net": round(B[b]["c"] - p0), "named": board.hm(B[L["named"]]["m"] + 5)})
    why = None
    if lab["type"] == "EARLY":
        why = ((f"IB 10:15 tak ban raha hai — {len(B)} bar hue" if B[i]["m"] + 5 < IB_END
                else "IB ban gaya; read abhi 2 bar se tika nahi")
               + f" · abhi ka jhukav {_label_word({'type': raws[-1][0], 'dir': raws[-1][1]})} [I]")
    return {**base, "ok": True, "type": NAME[lab["type"]], "dir": lab["dir"], "word": _label_word(lab),
            "since": since_t, "named": board.hm(B[lab["named"]]["m"] + 5), "asof": asof_t, "why": why,
            "evidence": ev, "day_so_far": segs, "changes_if": chg, "basis": basis,
            "basis_why": None if basis is not None else board.CC + "basis: chain ka spot is waqt ka nahi",
            "switches": len(labels) - 1, "raw": _label_word({"type": raws[-1][0], "dir": raws[-1][1]}),
            "labels": [{"word": _label_word(L), "since": L.get("since_t") or B[L["since"]]["t"],
                        "named": board.hm(B[L["named"]]["m"] + 5), "end": L.get("end")} for L in labels]}
