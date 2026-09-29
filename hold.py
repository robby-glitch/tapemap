"""hold.py -- THE HOLD / FOLD WINDOW and THE SIDE READ, exactly as registered.

THE SPEC is docs/hold/PREREG-merged.md rev 4 (sha256 e7f50391...a7744709d0,
anchored in context/research-findings.md §1e), signed by the operator
2026-09-25 01:42, AMENDED by docs/hold/PREREG-rev5.md (sha256 06a54cee...5189),
signed on her delegation 2026-09-25 19:40: OPTION B is the rule (§A.2) -- the
line breaks on a 3-minute index close past one frozen median 1-minute candle,
printed as a level; option A is NOT in force. Also rev 5's §A.0 (the grid,
closes read between, missing / late / backfilled closes, the latch, the heal),
§B (the display after a FOLD), §C (the PAYERS precedence), §D (the copy) and
§F / §G (clause 7's fields, `prereg`). Everything rev 5 does not name stands in
rev 4, word for word. Nothing here is a result: every verdict carries DRAFT
until §7 passes, and a rule changed here is a new registration, never a fix.

PORTED, NOT REINVENTED. The §3 order is Opus's literal probe of the
registration (docs/hold/opus/scratch/xreview/prereg_probe.js, rev2 mode, its
table probe_rev3.txt); the line is docs/hold/fable/hold.js as ported into
docs/hold/opus/verdict.js, with rev 5 B's break as the disclosure run wrote it
(scratchpad rev5/probeB.py `lineB`, the clamp as probeBc.py `lineBc`); the side
read is docs/hold/fable/scratch/side_report.js. test_hold.py replays the
registration's own stated examples on the frozen facts those prototypes were
probed with, re-pinned to rev 5 §E.1's option B column.

INPUT, one record per session minute 09:15..15:29, in the shape
docs/hold/opus/scratch/build_facts.py writes and server._hold_facts builds
from the same pure functions:
    {t, spot, blind?, CE, PE, folds, cvd, cvd_why, flow, flow_why, tr, tr_why, ix}
CE / PE are the NEARER of each side's §1d top 2 (board.nearer) by the running
session-peak OI; `folds` the fold events within 15 min of t, each with `still`
(board.still_folded); cvd / flow grounds' facts on ladder bars closed by t;
tr trendbox's 5m / 15m / 1h words; ix the index's own 1-min candle [c, h, l].
`late` (rev 5 §A.0.4) says which candles were first read after their own
minute -- the server keeps it in day state, so a restart re-reads what was read.

Pure: no I/O, no clock. It gates nothing -- not setup.gate, not the zone
machine, not trigger_log -- and there is no order path.
"""
from __future__ import annotations

import re
import statistics

import board
import fronts
import trendbox

PERSIST = 3          # §6: an against-state holds 3 finished minutes
QUIET = 15           # §6: the buyer's clock, in readable minutes; rev 5 §A.2: B's window (= fronts.SLOPE_MARKS)
FOLD_LIVE = 15       # §6: a fold is live within 15 min of its stamp AND still folded
ENTRY_SHOWN = 3      # §3 / S6: the entry check heads the window at least this long
BAR = 3              # rev 5 §A.0.1: the 09:15 grid of 3-min bars (band_rotation.SCORED_INTERVAL; her chart's candle)
HEAL = 15            # rev 5 §F.1: clause 7a's heal window, clock minutes (N5's reversal window, FOLD_LIVE)
LATE_BREAK = "15:14"  # rev 5 §F.1: a break whose bar closes after this has fewer than five closes left -> short
PREREG = "rev5-B"    # rev 5 §G: the option the rows are written under
CC, NONE, NOT_SHOWN = board.CC, board.NONE, board.NOT_SHOWN
WHO = " (writers: [I])"     # the OI change is measured; that writers made it is inferred -- OI up
                            # can be new buyers (2026-09-28 trader audit, bug 4)
DRAFT = ("DRAFT — pre-registered 2026-09-25 (docs/hold/PREREG-merged.md rev 4, amended by PREREG-rev5.md "
         "option B, signed 19:40), untested; §7's forward rows decide it, not this screen")
SESSION = [f"{m // 60:02d}:{m % 60:02d}" for m in range(9 * 60 + 15, 15 * 60 + 30)]
UNW, BLD = "UNWINDING", "BUILDING"
ROWS = ("5m", "15m", "1h")
RULE_NAME = {3: "the line", 4: "positioning flipped", 5: "the reason is gone", 6: "two families"}
LINE_OUT = ("src", "room", "px", "broken_at", "blind", "bar_close", "bar", "read_at", "backfill", "B", "B_at",
            "B_why", "level", "clamped", "clamp", "print", "note", "to_level", "next_close")

mm, hm = board.mm, board.hm
T0 = mm("09:15")


def read_minute(ts):
    """The last FINISHED minute before a fill (§2): a 13:41:38 fill reads 13:40."""
    return hm(max(mm(ts) - 1, mm("09:15")))


def thesis(side, role):
    """§1's table. d = the direction the thesis needs (a writer's: the danger absent)."""
    d = 1 if (side == "CE") == (role == "long") else -1
    return {"d": d, "buyer": role == "long", "Q": "CE" if d > 0 else "PE", "R": "PE" if d > 0 else "CE"}


def _strip(why):
    return (why or "").replace(CC, "") or None


def _k(k):
    return f"{float(k):,.0f}"


def _pts(x):
    """B as printed: 4.9, 5.25, 30.23 -- to the 0.05 it was measured to, no trailing zeros."""
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _w(side):
    """§D's {Pw} / {Hw}: the writers of `side`, capitalised; _lc lowers them mid-sentence."""
    return "Put writers" if side == "PE" else "Call writers"


def _lc(s):
    return s[0].lower() + s[1:] if s and s.startswith(("Put writers", "Call writers")) else s


def _cap(side):
    """§D's {cap}: the floor below (PE writers) or the ceiling above (CE writers)."""
    return "floor below" if side == "PE" else "ceiling above"


def _sw(f):
    return f.get("words") or f["state"].lower()


def _and(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _beyond(px, x, d):
    """The break's strict test (rev 4 §2, rev 5 §A.0.6): below for a long CE / short PE, above otherwise."""
    return px > x if d < 0 else px < x


# ---------------------------------------------------------------- the 3-minute grid (rev 5 §A.0.1)
def is_close(t):
    """t is the last minute of its 3-min bar on the 09:15 grid: the 12:00 bar closes on the 12:02 candle."""
    return (mm(t) - T0) % BAR == BAR - 1


def bar_end(t):
    n = mm(t)
    return hm(n + BAR - 1 - (n - T0) % BAR)


def bar_name(end):
    return f"{hm(mm(end) - BAR + 1)}–{end}"


def _landed(late, t):
    """The minute t's candle was first read: its own, or when it landed late (rev 5 §A.0.4). A close first
    read from a backfill is read at its own bar."""
    r = (late or {}).get(t)
    return (r.get("read_at") or t) if r else t


def noise(minutes, i, late=None):
    """rev 5 §A.2's B = VALIDATE rev 2 §1.3's noise -- ONE measure: the median high − low of the index's own
    1-min candles over the QUIET finished minutes ending at minute i, all present. A candle that landed after
    i was not present at i. -> (pts | None, how many of QUIET were present)."""
    t = minutes[i]["t"]
    xs = [m["ix"][1] - m["ix"][2] for m in minutes[max(i - QUIET + 1, 0):i + 1]
          if m.get("ix") and _landed(late, m["t"]) <= t]
    return (round(statistics.median(xs), 2) if len(xs) == QUIET else None), len(xs)


# ---------------------------------------------------------------- the three families
def flow(rec, d):
    """ORDER FLOW [I], board.aggression's strict rule: with / against only when CVD
    is strong AND the prints dominate the same way. -> (state, fact, why)."""
    c, f = rec.get("cvd"), rec.get("flow")
    dirn, _word, fact, why = board.aggression({
        "cvd": c and {"d": c["d"], "rank": c["rank"], "since": c["since"], "rank_why": c.get("rank_why")},
        "flow": f and {"buy": f["b"], "sell": f["s"], "runs_why": f.get("rw")},
        "cvd_why": _strip(rec.get("cvd_why"))})
    if dirn:
        return ("with" if dirn == d else "against"), fact, None
    if fact is None or why == "prints could not be read" or (why or "").startswith("too thin"):
        return "blind", fact, why if (why or "").startswith(CC) else CC + why
    return "flat", fact, why


def trend(rec, th):
    """TREND [I], trendbox's 5m / 15m / 1h. -> (state, rows text)."""
    tr = rec.get("tr")
    if not tr:
        return "blind", CC + (_strip(rec.get("tr_why")) or "no index candle yet")
    w = [tr.get(k) for k in ROWS]
    txt = " · ".join(f"{k} {x or 'forming'}" for k, x in zip(ROWS, w))
    mine, other = ("UP", "DOWN") if th["d"] > 0 else ("DOWN", "UP")
    n_m, n_o = w.count(mine), w.count(other)
    if th["buyer"]:
        st = "for" if n_m >= 2 and n_o == 0 else "against" if n_o >= 2 else "flat"
    else:           # a writer: against when >= 2 read the danger direction; with her when none does and none forms
        forming = any(x not in ("UP", "DOWN", "RANGE") for x in w)
        st = "against" if n_o >= 2 else "for" if n_o == 0 and not forming else "flat"
    return st, txt


def side_of(rec):
    """§10.1: CALLS / PUTS / no side off the same vote, or None = could not check. -> (side, why)."""
    tr = rec.get("tr")
    if not tr:
        return None, CC + (_strip(rec.get("tr_why")) or "no index candle yet")
    w = [tr.get(k) for k in ROWS]
    if any(x not in ("UP", "DOWN", "RANGE") for x in w):
        return None, CC + "a middle row is still forming"
    up, dn = w.count("UP"), w.count("DOWN")
    txt = " · ".join(f"{k} {x}" for k, x in zip(ROWS, w))
    if up >= 2 and dn == 0:
        return "CALLS", txt
    if dn >= 2 and up == 0:
        return "PUTS", txt
    return "no side", txt + " — no side"


# ---------------------------------------------------------------- THE LINE [M]
def pivots(m1, day, asof=None):
    """Confirmed 5-min swing highs / lows of TODAY (trendbox PIV = 2, 09:15-aligned
    closed bars, strict), `confirm` = the last minute of the second bar after the
    pivot. Ported from build_facts.pivots; cut to `asof` so a forming bar is never read."""
    rows = [r for r in trendbox.candles(m1) if r[0] == day and (asof is None or r[1] <= asof)]
    bars, P = trendbox.agg(rows, 5), trendbox.PIV
    out = []
    for i in range(P, len(bars) - P):
        hi = all(bars[i][4] > bars[x][4] for x in range(i - P, i)) and all(bars[i][4] > bars[x][4] for x in range(i + 1, i + 1 + P))
        lo = all(bars[i][5] < bars[x][5] for x in range(i - P, i)) and all(bars[i][5] < bars[x][5] for x in range(i + 1, i + 1 + P))
        conf = hm(trendbox.slot_end(bars[i + P][1], 5))
        if hi:
            out.append({"kind": "H", "price": bars[i][4], "bar": bars[i][1], "confirm": conf})
        if lo:
            out.append({"kind": "L", "price": bars[i][5], "bar": bars[i][1], "confirm": conf})
    return out


def line(minutes, pivs, d, e, late=None, frozen=None):
    """THE LINE from entry index `e`: rev 4 §2's L (its source, its one-way trail on confirmed 5-min
    pivots, its room from the 1-min close every minute) with rev 5 OPTION B's break (§A.2):

      broken = the close of a 3-min bar (§A.0.1) beyond the break level, L − B below a long CE / short PE,
      L + B above a long PE / short CE, strict. B = noise() at the minute L was set (the entry read) or
      last trailed, all 15 candles present, FROZEN with L. On a trail the level is the NEARER to price of
      the old level and the new L ∓ B (never away, S-d), `clamped` when the old one is kept. Fewer than
      15 candles: buffer 0 until B can be read, then frozen (the named fallback; its first read is the one
      move away, S-i).

    Closes (§A.0.3 / §A.0.4): the first bar read is the first whose last minute is after the entry read.
    The line's state changes only when a close is read and stands until the next one. A close is read at
    its own minute, or -- its candle late -- at the minute it landed (`late[t].read_at`), never before,
    judged against the level in force at its bar (a late reading changes when it is read, not what it
    is). A due close that has not landed blinds the line until some close is read. A mid-bar minute with
    no candle is not blind: its room could not be checked. `frozen`: this trade's B reads from day state.

    -> ({i: row}, [B reads]) -- or (None, []) when the entry minute has no candle, or one that landed
    after it: the line cannot be set (rev 4 S4)."""
    bear, late = d < 0, late or {}
    kind, word = ("H", "high") if bear else ("L", "low")
    sg, dirw = (1, "above") if bear else (-1, "below")
    at = {m["t"]: i for i, m in enumerate(minutes)}
    m0 = minutes[e]
    et = m0["t"]
    if not m0.get("ix") or _landed(late, et) != et:
        return None, []

    def far(p, c):
        return p > c if bear else p < c

    def cand(i):                            # minute i's own candle, if it had landed by i
        m = minutes[i]
        return m["ix"] if m.get("ix") and _landed(late, m["t"]) <= m["t"] else None
    px0, t0 = m0["ix"][0], mm(et)
    mine = [p for p in pivs if p["kind"] == kind]
    known = sorted((p for p in mine if mm(p["confirm"]) <= t0 and far(p["price"], px0)),
                   key=lambda p: mm(p["bar"]), reverse=True)
    used = set()
    if known:
        L, src = known[0]["price"], f"5m swing {word} {known[0]['bar']}"
        used.add(known[0]["bar"])
    else:
        seen = [m["ix"] for m in minutes[:e + 1] if m.get("ix")]
        L = max(x[1] for x in seen) if bear else min(x[2] for x in seen)
        src = f"session {word} so far, no 5m swing {'above' if bear else 'below'} you yet"
    frz = {(round(f["L"], 2), f["L_at"]): f for f in frozen or [] if f.get("B") is not None}
    reads = []

    def take_b(i, L, L_at):
        """B for the line (L, set or trailed at L_at) as read at minute i -- frozen if day state holds it."""
        B, n = noise(minutes, i, late)
        f = frz.get((round(L, 2), L_at))
        if f is not None:
            B = f["B"] if f["B_at"] <= minutes[i]["t"] else None
            return B, f["B_at"] if B is not None else None, n
        return B, minutes[i]["t"] if B is not None else None, n

    def ev():
        return {"L": round(L, 2), "L_at": L_at, "B": B, "B_at": B_at, "level": round(lvl, 2), "clamped": clamped}
    L_at = et
    B, B_at, n15 = take_b(e, L, L_at)
    lvl, clamped, clamp = (None if B is None else L + sg * B), False, None
    if B is not None:
        reads.append(ev())
    when = {}                               # minute index -> the bar closes read at it
    for ib in range(e + 1, len(minutes)):
        tb = minutes[ib]["t"]
        if is_close(tb) and minutes[ib].get("ix"):
            j = at.get(_landed(late, tb))
            if j is not None:
                when.setdefault(max(j, ib), []).append(ib)
    out, held, broken, prev, carried, pend, last = {}, {}, None, px0, False, None, None
    for i in range(e, len(minutes)):
        t = minutes[i]["t"]
        c = m0["ix"] if i == e else cand(i)
        if i > e and c:
            moved = False
            for p in sorted((p for p in mine if p["bar"] not in used and t0 <= mm(p["confirm"]) < mm(t)),
                            key=lambda p: mm(p["confirm"])):
                used.add(p["bar"])
                if (p["price"] < L if bear else p["price"] > L) and far(p["price"], prev):
                    L, src, moved = p["price"], f"5m swing {word} {p['bar']}", True
            if moved:                       # B read again at the trail; the level never moves away (S-d)
                L_at = t
                Bn, Bn_at, n15 = take_b(i, L, L_at)
                new, clamped, clamp = (None if Bn is None else L + sg * Bn), False, None
                if new is None or lvl is None:
                    lvl, B, B_at = new, Bn, Bn_at
                else:
                    near = min(lvl, new) if bear else max(lvl, new)
                    if near != new:
                        clamped, clamp = True, {"t": t, "away": round(abs(new - near), 1)}
                    lvl, B, B_at = near, Bn, Bn_at
                if B is not None:
                    reads.append(ev())
            elif lvl is None:               # the fallback's first read of B: the one move away (S-i)
                B, B_at, n15 = take_b(i, L, L_at)
                if B is not None:
                    lvl = L + sg * B
                    reads.append(ev())
            prev = c[0]
        level = L if lvl is None else lvl
        held[i] = (L, src, level, B, B_at, clamped, clamp)
        if i > e and is_close(t) and i not in when.get(i, ()):
            pend = pend or t                # a due close that has not landed: blind until a close is read
        got = []
        for ib in when.get(i, ()):
            Lb, srcb, lvb, Bb, Bb_at, clb, cpb = held[ib]
            pxb, tb = minutes[ib]["ix"][0], minutes[ib]["t"]
            r = late.get(tb) or {}
            got.append({"bar": bar_name(tb), "end": tb, "px": pxb, "L": Lb, "src": srcb, "level": round(lvb, 2),
                        "B": Bb, "B_at": Bb_at, "clamped": clb, "clamp": cpb, "broke": _beyond(pxb, lvb, d),
                        "by": round(abs(pxb - Lb), 1), "by_level": round(abs(pxb - lvb), 1),
                        "read_at": None if r.get("backfill") else t, "backfill": r.get("backfill")})
        if got:
            pend, carried = None, any(g["broke"] for g in got)
            last = next((g for g in got if g["broke"]), got[-1])
            if carried and broken is None:
                broken = t
        note = None
        if pend:
            pass
        elif not c:
            note = CC + f"no candle for {t}"
        elif i > e and not got and not carried and _beyond(c[0], L, d):
            thr, be = round(abs(c[0] - L), 1), bar_end(t)
            note = (f"through your line by {thr} pts [M] — {round(abs(c[0] - level), 1)} pts to go to the break "
                    f"level {level:,.1f}; the 3-min bar closes at {be}" if level != L and not _beyond(c[0], level, d)
                    else f"through your line by {thr} pts [M] — the 3-min bar closes at {be}")
        nc = bar_end(t) if not is_close(t) else hm(mm(t) + BAR)
        out[i] = {"L": L, "src": src, "room": round(L - c[0] if bear else c[0] - L) if c else None,
                  "px": last["px"] if got else (c[0] if c else None), "c": c[0] if c else None,
                  "beyond": carried if i > e else False, "broken_at": broken,
                  "blind": CC + f"the {bar_name(pend)} bar's close has not landed" if pend else None,
                  "pending": bar_name(pend) if pend else None,
                  "bar_close": bool(got), "bar": last["bar"] if got else None,
                  "read_at": last["read_at"] if got else None, "backfill": bool(got and last["backfill"]),
                  "close": last, "B": B, "B_at": B_at, "level": round(level, 2), "clamped": clamped, "clamp": clamp,
                  "B_why": None if B is not None else CC + f"{n15} of {QUIET} candles",
                  "print": (f"line {L:,.1f} · breaks {dirw} {level:,.1f} — kept; the {clamp['t']} trail would have "
                            f"moved it {clamp['away']} pts away" if clamped else
                            f"line {L:,.1f} · breaks on a 3-min close {dirw} {level:,.1f} — one median candle, "
                            f"{_pts(B)} pts [M], read {B_at}" if B is not None else
                            f"line {L:,.1f} · breaks on a 3-min close {dirw} {L:,.1f} — buffer 0 until one median "
                            f"candle can be read (could not check — {n15} of {QUIET} candles)"),
                  "note": note, "to_level": round(abs(c[0] - level)) if c else None,
                  "next_close": nc if nc <= SESSION[-1] else None}
    return out, reads


# ---------------------------------------------------------------- one minute's OI facts
def _front(rec, side):
    """The nearer front on `side`, carrying its side (the frozen fixtures' rows do not)."""
    f = rec.get(side)
    return f and {"side": side, **f}


def _last_fold(rec, side, now):
    live = [f for f in rec.get("folds") or []
            if f["side"] == side and f.get("still") and 0 <= mm(now) - mm(f["t"]) <= FOLD_LIVE]
    return live[-1] if live else None


def _raw(rec, th):
    """PAYERS / HOLDERS [M] for this thesis at one minute, before persistence."""
    c = rec.get("cvd")
    o = {"t": rec["t"], "oi_blind": rec.get("blind"), "dpx": c.get("dpx") if c else None}
    if o["oi_blind"]:
        return o
    q, r = _front(rec, th["Q"]), _front(rec, th["R"])
    both = bool(q and r and q["state"] == UNW and r["state"] == UNW)
    o.update(q=q, r=r, both=both,
             q_pays=bool(not both and q and q["state"] == UNW),
             q_fold=None if both else _last_fold(rec, th["Q"], rec["t"]),
             q_build=bool(q and q["state"] == BLD and q.get("built")),
             r_hold=bool(r and r["state"] == BLD and r.get("built")),
             r_unw=bool(not both and r and r["state"] == UNW),
             r_fold=None if both else _last_fold(rec, th["R"], rec["t"]))
    return o


def _held(rs, i, key):
    """Held PERSIST finished minutes, OI readable in each (§2)."""
    return i - PERSIST + 1 >= 0 and all(not rs[j]["oi_blind"] and rs[j].get(key)
                                        for j in range(i - PERSIST + 1, i + 1))


def _run(rs, i, key):
    n = 0
    while i - n >= 0 and not rs[i - n]["oi_blind"] and rs[i - n].get(key):
        n += 1
    return n


def _fw(f):
    return f"{f['side']} {_k(f['k'])} {f.get('words') or f['state'].lower()}"


def _oi_why(rec):
    """§D item 13's {why}: for fronts forming, "fronts forming, n of 15 marks (OI reads from about HH:MM [I])"."""
    why = _strip(rec.get("blind")) or ""
    got = re.search(r"(\d+) so far", why) if "fronts forming" in why else None
    if got:
        n = int(got.group(1))
        return (f"fronts forming, {n} of {fronts.SLOPE_MARKS} marks "
                f"(OI reads from about {hm(mm(rec['t']) + fronts.SLOPE_MARKS - n)} [I])")
    return why


# ---------------------------------------------------------------- THE WINDOW (§3, §4)
def read(trade, minutes, pivs, upto=None, prem=None, idx=None, late=None, frozen=None):
    """Every finished minute of one trade from its entry read to `upto` (HH:MM,
    default the last record). `trade`: {side CE|PE, role long|short, t0
    HH:MM[:SS], p0, qty, k?}. `prem`: {"c": [...], "o": [...], "src"} aligned to
    `minutes`, or None. `late` / `frozen`: see line(); the close-time import passes
    neither, so it reads every close at its own bar (rev 5 §A.0.4).
    -> {ok, rows, entry, fold, th, b_reads}; rows[-1] is what shows now."""
    th = thesis(trade["side"], trade["role"])
    d, buyer, Q, R = th["d"], th["buyer"], th["Q"], th["R"]
    idx = idx or trade.get("idx") or "the index"
    at = {m["t"]: i for i, m in enumerate(minutes)}
    et = read_minute(trade["t0"])
    if et not in at:
        return {"ok": False, "why": CC + f"no record of {et}, the minute finished before your fill", "th": th}
    e = at[et]
    to = len(minutes) - 1 if upto is None else at.get(upto)
    if to is None or to < e:
        return {"ok": False, "why": CC + f"{upto} is not a finished minute at or after your entry read {et}", "th": th}
    LN, b_reads = line(minutes, pivs, d, e, late, frozen)
    rs = [_raw(m, th) for m in minutes[:to + 1]]
    p0, qty = trade.get("p0"), trade.get("qty") or 0
    sg = 1 if buyer else -1
    contract = f"{idx} {float(trade.get('k') or 0):g} {trade['side']}"
    # after her exit the premium and P&L are the exit minute's (the last finished minute before it, as the
    # entry reads), never the latest print: a 10:20 exit must not show 15:29's premium
    xi = at.get(read_minute(str(trade["exit_t"]))) if trade.get("exit_t") else None
    rows, latch, heal, readable, paid_at, run, etext, said = [], None, None, [], {}, None, None, None
    for i in range(e, to + 1):
        m, x = minutes[i], rs[i]
        ln = LN.get(i) if LN else None
        t = m["t"]
        line_blind = CC + f"no {idx} candle for {et}; the line can't be set" if LN is None else ln["blind"]
        oi_blind = x["oi_blind"]
        oi_why = _oi_why(m) if oi_blind else None
        fl_state, fl_fact, fl_why = flow(m, d)
        tr_state, tr_txt = trend(m, th)
        # PAYERS / HOLDERS with persistence, and the writer's own-side clause (§4)
        qA = not oi_blind and _held(rs, i, "q_build")
        rA_raw = not oi_blind and _held(rs, i, "r_unw")
        dpx = x["dpx"]
        squeeze = None if dpx is None else ((dpx > 0) - (dpx < 0)) == -d
        rA = rA_raw if buyer else bool(rA_raw and squeeze)
        rF = None if oi_blind else x.get("r_fold")
        rF_against = bool(rF) and (buyer or bool(squeeze))
        fAg, fWith, tAg = fl_state == "against", fl_state == "with", tr_state == "against"
        if not oi_blind:
            readable.append(i)
            paid_at[i] = bool(x["q_pays"] or x["q_fold"]) or fWith
        last_paid = next((minutes[j]["t"] for j in reversed(readable) if paid_at[j]), None)
        quiet_n = sum(1 for j in readable if not last_paid or mm(minutes[j]["t"]) > mm(last_paid))
        quiet = buyer and len(readable) >= QUIET and not any(paid_at[j] for j in readable[-QUIET:])
        P = _payers(x, oi_blind, qA, rs, i, Q, buyer)
        H = _holders(x, oi_blind, rA, rF, squeeze, dpx, buyer, R, rs, i)
        F = {"state": fl_state, "fact": fl_fact, "why": fl_why, "tag": "I"}
        T = {"state": tr_state, "rows": tr_txt, "tag": "I"}
        fam = [f for f in (_lc(P["fact"]) if qA else None, f"flow against you: {fl_fact} [I]" if fAg else None,
                           f"trend against you: {tr_txt} [I]" if tAg else None) if f]
        # §3 in order, the latch removed (the unlatched state, §7)
        rule, why = None, None
        if line_blind:
            u = "PATA NAHI"
        elif ln["beyond"]:
            u, rule, why = "FOLD", 3, _why3(idx, ln["close"], d)
        elif qA and rA:
            u, rule, why = "FOLD", 4, f"positioning flipped: {_lc(P['fact'])}; and {_lc(H['fact'])}"
        elif quiet:
            u, rule = "FOLD", 5
            why = (f"the reason is gone: nothing has paid in the last {QUIET} readable minutes "
                   f"(paid last {last_paid or 'never since entry'})")
        elif len(fam) >= 2:
            u, rule = "FOLD", 6
            why = "two families against you: " + "; ".join(fam[:-1]) + "; and " + fam[-1]
        else:
            w = [f for f in (_lc(P["fact"]) if buyer and qA else None, _lc(H["fact"]) if rA else None,
                             _lc(H["fold"]) if rF_against else None,
                             f"flow against you: {fl_fact} [I]" if fAg else None,
                             f"trend against you: {tr_txt} [I]" if tAg else None) if f]
            u, why = ("WATCH", "; ".join(w)) if w else ("HOLD", None)
        fors = [f for f in (P.get("short") if P["state"] == "for" else None,      # §D item 8's short forms
                            H.get("short") if H["state"] == "for" else None,
                            "winners cashing in" if H.get("fold_for") else None,
                            "flow with you" if fWith else None,
                            "the trend rows with you" if tr_state == "for" else None) if f]
        pr = _prem(prem, i if xi is None else min(i, xi), p0, qty, sg)   # never an input to the verdict (§1): noise tag, P&L, footer
        room = (ln or {}).get("room")
        room_txt = (f"Line could not check — no candle for {t}" if room is None else
                    f"Line {room} pts away [M]" if room >= 0 else f"Line {-room} pts past it [M]")
        tag = None
        if latch:
            word = "FOLD"
            if latch["rule"] == 3:          # A.0.6: the first later bar close not beyond the L that broke
                cl = ln["close"] if ln and ln["bar_close"] else None
                if cl and cl["end"] > latch["bar"][-5:]:
                    heal = (heal or t) if not _beyond(cl["px"], latch["L"], d) else None
                but = f" — but {RULE_NAME[rule]} reads FOLD now" if u == "FOLD" and rule in (4, 5, 6) else ""
                healed = (f" · the break has healed since {heal} (a 3-min close back on your side of "
                          f"{latch['L']:,.1f}) — a re-entry is a new trade{but}") if heal else ""
            else:
                heal = (heal or t) if u in ("HOLD", "WATCH") else None
                healed = f" · the break has healed since {heal} — a re-entry is a new trade" if heal else ""
            sentence = f"FOLD since {latch['t']} — {latch['why']}" + healed
        elif u == "PATA NAHI":
            word = u
            sentence = (f"PATA NAHI — no {idx} candle for {et}; the line can't be set." if LN is None else
                        f"PATA NAHI — the {ln['pending']} bar's close has not landed; the line can't say whether it "
                        f"broke. Last word: " + (f"{said[0]} since {said[1]}." if said else "none yet since entry."))
        else:
            word = u
            if u == "FOLD":
                latch = _latch(t, i, rule, why, ln)
                late_read = rule == 3 and latch["read_at"] and latch["read_at"] != latch["bar"][-5:]
                sentence = f"FOLD {t} — {why}" if late_read else f"FOLD — {why}"
            elif u == "WATCH":
                sentence = f"WATCH — {why}"
            elif oi_blind:
                tag = "OI blind"
                sentence = _oi_hold(oi_why, fl_state, fl_why, tr_state, tr_txt)
            elif not fors:
                tag = "nothing paying"
                sentence = (f"HOLD · nothing paying ({quiet_n} min)" if buyer else
                            "HOLD — nothing against you; time is paying the writer")
            elif pr.get("adverse"):
                tag = "noise"
                sentence = (("Your premium is red" if buyer else "The premium you sold is up")
                            + f"; the reason has not changed: {'; '.join(fors[:2])}. {room_txt}.")
            else:
                sentence = f"HOLD — the reason stands: {'; '.join(fors[:2])}. {room_txt}."
            if oi_blind and u in ("WATCH", "FOLD"):
                sentence += f" (OI blind — could not check: {oi_why})"
        if run is None or run[0] != word:
            run = (word, t)
        if word != "PATA NAHI":
            said = run
        n_for = sum(1 for r in (P, H, F, T) if r["state"] == "for")
        n_against = sum(1 for r in (P, H, F, T) if r["state"] == "against")
        hint = (_hint(ln, line_blind, idx, d, th, qA, rA, fAg, tAg, oi_why, F, T, dpx, rs, i, quiet_n)
                if word == "WATCH" else None)
        if i == e:                          # §3's entry check, from this reading with the latch removed
            paying = ("nothing paying yet" if tag == "nothing paying" else sentence if tag == "OI blind"
                      else "; ".join(fors[:2]))
            etext = (f"You entered into a broken setup — the reason was already gone (read {et}): {why}." if u == "FOLD"
                     else f"You entered into WATCH — {why}; it becomes FOLD if any one of: {' · '.join(hint)}."
                     if u == "WATCH" else
                     f"You entered into HOLD — line {ln['L']:,.1f}, {ln['room']:,} pts of room; {paying}." if u == "HOLD"
                     else f"You entered into PATA NAHI — no {idx} candle for {et}; the line can't be set.")
        fams_blind = [n for n, b in (("the line", line_blind), ("OI", oi_blind), ("flow", fl_state == "blind"),
                                     ("trend", tr_state == "blind")) if b]
        blind = [b for b in (line_blind, ln and (ln["note"] or "").startswith(CC) and ln["note"], oi_blind,
                             F["why"] if fl_state == "blind" else None, tr_txt if tr_state == "blind" else None) if b]
        rows.append({
            "t": t, "verdict": word, "tag": tag, "sentence": sentence,
            "since": latch["t"] if latch else run[1],
            "fold_rule": latch["rule"] if latch else None, "unlatched": u, "healed_since": heal,
            "line": ({"L": round(ln["L"], 2), **{k: ln[k] for k in LINE_OUT}, "tag": "M"} if ln else
                     {"blind": line_blind, "tag": "M"}),
            "payers": P, "holders": H, "flow": F, "trend": T, "both_leaving": bool(x.get("both")),
            "count": f"{n_for} for · {n_against} against — a count, not odds", "n_for": n_for, "n_against": n_against,
            "clock": ({"paid_last": last_paid, "quiet": min(quiet_n, QUIET), "readable": len(readable), "of": QUIET,
                       "text": f"paid last {last_paid or '—'} · quiet {min(quiet_n, QUIET)} of {QUIET}"}
                      if buyer else {"text": NOT_SHOWN + "a writer has no quiet clock; time pays her"}),
            "watch": "FOLD if any one of: " + " · ".join(hint) if hint else None, "watch_items": hint,
            "against": (why if word == "WATCH" else None if word == "FOLD" else     # §D item 11, the collapsed line
                        "nothing against you" + "".join(f" · {n} could not check" for n in fams_blind)),
            "after_fold": _after(latch, ln, d, contract, heal) if latch else None,
            "prem": pr, "blind": blind,
        })
    head = rows[0]
    start = mm("09:15") + (mm(et) - mm("09:15")) // 5 * 5
    fold = {k: v for k, v in latch.items() if k != "i"} if latch else None
    return {"ok": True, "th": th, "rows": rows, "fold": fold,
            "entry": {"t": et, "verdict": head["unlatched"], "text": etext,
                      "head_until": hm(max(start + 5, mm(et) + ENTRY_SHOWN)),
                      "fold_rule": head["fold_rule"] if head["unlatched"] == "FOLD" else None},
            "b_reads": [b for b in b_reads if b["B_at"] <= minutes[to]["t"]]}


def _why3(idx, cl, d):
    """§D.2 rule 3 under B: the bar, its close, how far past L and past the level in force; a late close
    says when it was read, a backfilled one says so (§A.0.4)."""
    how = (f" (read from backfill after a restart at {cl['backfill']})" if cl["backfill"] else
           f" (read late, at {cl['read_at']})" if cl["read_at"] != cl["end"] else "")
    s = (f"the line is broken: {idx}'s {cl['bar']} bar closed {cl['px']:,.1f}{how}, {cl['by']} pts "
         f"{'below' if d > 0 else 'above'} your line {cl['L']:,.1f} ({cl['src']}) [M]")
    if cl["B"] is None:                     # the fallback's break: buffer 0, B: null (rev 5 §A.2)
        return s
    return s + (f" — {cl['by_level']} past the break level {cl['level']:,.1f} " + (
        f"(kept — the {cl['clamp']['t']} trail would have moved it {cl['clamp']['away']} pts away) [M]" if cl["clamped"]
        else f"(one candle, {_pts(cl['B'])} pts, read {cl['B_at']}) [M]"))


def _latch(t, i, rule, why, ln):
    """rev 5 §A.0.5: set once, never changed. Rule 3 keeps the close that broke; rules 4-6 the line as it stood."""
    if rule == 3:
        cl = ln["close"]
        return {"t": t, "i": i, "rule": 3, "why": why, "bar": cl["bar"], "L": round(cl["L"], 2), "src": cl["src"],
                "px": cl["px"], "by": cl["by"], "read_at": cl["read_at"], "backfill": bool(cl["backfill"]),
                "B": cl["B"], "B_at": cl["B_at"], "level": cl["level"], "by_level": cl["by_level"],
                "clamped": cl["clamped"]}
    return {"t": t, "i": i, "rule": rule, "why": why, "bar": None, "L": round(ln["L"], 2), "src": ln["src"],
            "px": None, "by": None, "read_at": None, "backfill": False, "B": None, "B_at": None, "level": None,
            "by_level": None, "clamped": False}


def _after(latch, ln, d, contract, heal):
    """rev 5 §B: once FOLD is latched the STOP shows the line from the latch; the trailed line is detail."""
    c = (ln or {}).get("c")
    if latch["rule"] == 3:
        text = f"broke {latch['t']} by {latch['by']} pts [M]" + (
            f" ({latch['by_level']} past the break level {latch['level']:,.1f})" if latch["B"] is not None else "")
        if c is not None:
            n = round(abs(c - latch["L"]))
            if heal:
                text = f"broke {latch['t']} · the index is back {n} pts {'above' if d > 0 else 'below'} it"
            elif _beyond(c, latch["L"], d):
                text += f" · past it by {n} pts"
        col = f"FOLD · {contract} · line {latch['L']:,.1f} broke {latch['t']} by {latch['by']} pts · since {latch['t']}"
    else:
        text = f"held at the FOLD {latch['t']}"
        col = f"FOLD · {contract} · line {latch['L']:,.1f} held at the FOLD {latch['t']} · since {latch['t']}"
    moved = ln is not None and round(ln["L"], 2) != latch["L"]
    return {"L": latch["L"], "src": latch["src"], "text": text, "collapsed": col,
            "detail": (f"the line has since moved to {ln['L']:,.1f} ({ln['src']}) — detail; a re-entry is a new "
                       f"trade with its own line") if moved else None}


def heal7a(rows, d):
    """rev 5 §F.1, clause 7a's unit and heal, off a trade's rows (hold.read's or the logged ones): its FIRST
    line break (line.broken_at), whatever rule folded first, and whether a later 3-min close came back not
    beyond the L that broke (the break's strict test: a close exactly on L is a heal) within HEAL clock
    minutes of the break bar's last minute -- the closes at +3 … +15. A bar whose close was not read is no
    heal and does not extend the window. A break after 15:14 is `short`: shown apart, never counted.
    -> None | {t, bar, L, healed_at, short}."""
    first = next((r for r in rows if (r.get("line") or {}).get("broken_at") == r["t"]
                  and (r.get("line") or {}).get("bar")), None)
    if first is None:
        return None
    ln = first["line"]
    end = ln["bar"][-5:]
    back = next((r["t"] for r in rows if (r.get("line") or {}).get("bar_close")
                 and mm(end) < mm(r["line"]["bar"][-5:]) <= mm(end) + HEAL
                 and not _beyond(r["line"]["px"], ln["L"], d)), None)
    return {"t": first["t"], "bar": ln["bar"], "L": ln["L"], "healed_at": back, "short": end > LATE_BREAK}


def _payers(x, oi_blind, qA, rs, i, Q, buyer=True):
    """The PAYERS row, in rev 5 §C's precedence: both leaving flat; payers against AGAINST (a live fold as a
    clause); UNWINDING for; a live fold for; adding not yet held flat, n of 3; else flat. Copy: §D items 6, 6′, 10."""
    q = x.get("q")
    if oi_blind or not q:
        return {"state": "blind", "fact": CC + (_strip(oi_blind) or f"no {Q} front read"), "k": None, "tag": "M"}
    k, Pw = q["k"], _w(Q)
    gain = f"fuel for your {'put' if Q == 'PE' else 'call'}" if buyer else "in your favour"   # a buyer's {opt} is Q's
    if x["both"]:
        return {"state": "flat", "k": k, "tag": "M",
                "fact": f"both sides' writers leaving — OI cannot say which way ({_fw(q)})"}
    f = x["q_fold"]
    if qA:      # before the fold: the WATCH / FOLD sentences quote this fact as the reason (REVIEW P0-4)
        return {"state": "against", "k": k, "tag": "M", **({"fold_t": f["t"]} if f else {}),
                "fact": f"{Pw} at {_k(k)} adding in your way (held {PERSIST} min) — {_sw(q)} [M]{WHO}"
                        + (f"; the {Q} {_k(f['k'])} fold of {f['t']} is still with you" if f else "")}
    if x["q_pays"]:
        pk, ch = q.get("peak"), q.get("chg")
        how = (f"OI {(pk - ch) / max(abs(pk), 1):.0%} off its peak, giving back since "
               f"{q.get('unwind_at') or q.get('peak_at')}" if pk is not None and ch is not None else _sw(q))
        return {"state": "for", "k": k, "tag": "M", "short": f"{_lc(Pw)} covering",
                "fact": f"{Pw} at {_k(k)} are covering — {how} [M]{WHO} — {gain}"}
    if f:
        return {"state": "for", "k": k, "fold_t": f["t"], "tag": "M", "short": f"{_lc(Pw)} folded {f['t']}",
                "fact": f"{Pw} at {_k(f['k'])} folded {f['t']} — {f['off']:.0%} off their {f['high_at']} high [M]{WHO} — {gain}"}
    if x["q_build"]:
        return {"state": "flat", "k": k, "tag": "M",
                "fact": f"{_fw(q)} — adding, {_run(rs, i, 'q_build')} of {PERSIST} min before it counts"}
    return {"state": "flat", "k": k, "tag": "M", "fact": _fw(q)}


def _holders(x, oi_blind, rA, rF, squeeze, dpx, buyer, R, rs, i):
    """The HOLDERS row (a writer's YOUR SIDE, with rev 4 §4's own-side clause). Copy: §D items 7, 7′, 7″."""
    r = x.get("r")
    Hw, cap = _w(R), _cap(R)
    out = {"label": "HOLDERS" if buyer else "YOUR SIDE", "tag": "M", "fold": None, "fold_for": False}
    own = None
    if not buyer:
        own = (CC + "no ladder window yet" if dpx is None else
               "spot moving against you — a squeeze" if squeeze else         # by her direction, not the strike:
               "winners cashing in — spot moving your way")                  # rev 5 copy amendment 1
    if rF:
        out["fold"] = (f"{Hw} at {_k(rF['k'])} folded {rF['t']} — the {cap} you stepped [M]{WHO}" if buyer else
                       f"{Hw} at {_k(rF['k'])} (your side) folded {rF['t']} [M]{WHO} — {own}")
        out["fold_t"], out["fold_for"] = rF["t"], squeeze is False and not buyer
    if oi_blind or not r:
        return {**out, "state": "blind", "fact": CC + (_strip(oi_blind) or f"no {R} front read"), "k": None}
    out["k"] = r["k"]
    left = f", {_run(rs, i, 'r_unw')} of {PERSIST} min before it counts"
    if x["both"]:
        return {**out, "state": "flat", "fact": f"both sides' writers leaving — OI cannot say which way ({_fw(r)})"}
    if x["r_hold"]:
        return {**out, "state": "for", "short": f"the {'floor' if R == 'PE' else 'ceiling'} holds",
                "fact": f"{Hw} at {_k(r['k'])} {_sw(r)} [M]{WHO} — the {cap} you holds"}
    if not x["r_unw"]:
        return {**out, "state": "flat", "fact": _fw(r)}
    if buyer:
        return {**out, "state": "against" if rA else "flat",
                "fact": f"{Hw} at {_k(r['k'])} {_sw(r)} [M]{WHO} — the {cap} you is leaving" + ("" if rA else left)}
    mine = f"{Hw} at {_k(r['k'])} (your side) {_sw(r)} [M]{WHO} — {own}"
    if dpx is None:
        return {**out, "state": "blind", "fact": mine}
    if squeeze:
        return {**out, "state": "against" if rA else "flat", "fact": mine + ("" if rA else left)}
    return {**out, "state": "for", "short": "winners cashing in", "fact": mine}


def _prem(prem, i, p0, qty, sg):
    if not prem:
        return {"why": CC + "no premium record for this contract"}
    c = (prem.get("c") or [])[i] if i < len(prem.get("c") or []) else None
    if c is None:
        return {"why": CC + "no print for this contract in this minute", "tag": prem.get("src", "I")}
    o = (prem.get("o") or [])[i] if i < len(prem.get("o") or []) else None
    out = {"c": c, "tag": prem.get("src", "I")}
    if p0:
        out.update(pnl=round((c - p0) * qty * sg, 2), pct=round((c / p0 - 1) * 100, 1),
                   adverse=sg * (c - p0) < 0 or (o is not None and sg * (c - o) < 0))
    return out


def _oi_hold(why, fl_state, fl_why, tr_state, tr_txt):
    """§D item 13, HOLD · OI BLIND: what could not check, and what reads and decides."""
    reads = ["the line"] + [n for n, s in (("flow", fl_state), ("trend", tr_state)) if s != "blind"]
    blind = [f"{n} could not check — {_strip(w)}" for n, s, w in (("flow", fl_state, fl_why), ("trend", tr_state, tr_txt))
             if s == "blind"]
    return (f"could not check OI: {why}; {_and(reads)} decide{'s' if len(reads) == 1 else ''}"
            + "".join(f"; {b}" for b in blind))


def _line_item(ln, idx, d):
    """§D.1 (a), option B's item (§A.2); a clamped level says it was kept (S-h); the fallback says buffer 0."""
    dirw, nc = ("below" if d > 0 else "above"), ln["next_close"]
    away = (f"{ln['to_level']} pts away" if ln["to_level"] is not None else
            f"the distance could not check — {_strip(ln['note'])}")
    tail = f"; next close {nc}" if nc else ""
    if ln["B"] is None:
        return (f"{idx} closes a 3-min bar {dirw} {ln['L']:,.1f} (buffer 0 until one median candle can be read — "
                f"{_strip(ln['B_why'])}) — {away} [M]{tail}")
    if ln["clamped"]:
        return (f"{idx} closes a 3-min bar {dirw} {ln['level']:,.1f} (kept — the {ln['clamp']['t']} trail would "
                f"have moved it {ln['clamp']['away']} pts away) — {away}{tail}")
    return (f"{idx} closes a 3-min bar {dirw} {ln['level']:,.1f} (your line {'less' if d > 0 else 'plus'} one "
            f"candle, {_pts(ln['B'])} pts [M]) — {away}{tail}")


def _hint(ln, line_blind, idx, d, th, qA, rA, fAg, tAg, oi_why, F, T, dpx, rs, i, quiet_n):
    """§D.1: EVERY condition that alone would turn this WATCH into FOLD from the unlatched state, in the
    registered example's order -- the line, positioning, two families, the quiet clock. The row joins
    them under "FOLD if any one of:"."""
    buyer, Q, R = th["buyer"], th["Q"], th["R"]
    pw, hw, pos = _lc(_w(Q)), _lc(_w(R)), "below" if R == "PE" else "above"
    items = [f"the line could not check — {_strip(line_blind)}" if line_blind else _line_item(ln, idx, d)]   # (a)
    leave = (f"the {hw} {pos} leave for {PERSIST} min" if buyer else
             f"the {hw} {pos} (your side) leave for {PERSIST} min under a squeeze")
    if oi_why:                              # (b) rule 4, by state
        items.append(f"positioning could not check — {oi_why}")
    elif not buyer and dpx is None:
        items.append("positioning flip could not check — no ladder window yet")
    elif qA:
        items.append(f"{leave} — {_run(rs, i, 'r_unw')} of {PERSIST}")
    elif rA:
        items.append(f"{pw} add in your way for {PERSIST} min — {_run(rs, i, 'q_build')} of {PERSIST}")
    else:
        items.append(f"{leave} and {pw} add in your way for {PERSIST} min")
    fams = [(f"{pw} adding in your way for {PERSIST} min", f"{pw} adding in your way", qA, oi_why),
            ("flow (CVD strong and prints dominant)", "flow", fAg, _strip(F["why"]) if F["state"] == "blind" else None),
            ("the trend rows (2 of 5m / 15m / 1h)", "the trend rows", tAg,
             _strip(T["rows"]) if T["state"] == "blind" else None)]
    rest = [f"{short} (could not check now — {b})" if b else name for name, short, v, b in fams if not v]
    items.append(("one more family turns against you: " + " or ".join(rest)) if any(v for _, _, v, _ in fams)
                 else "two families turn against you, of: " + ", ".join(rest))     # (d) rule 6
    if buyer:                               # (c) rule 5
        items.append(f"nothing pays for {QUIET} readable min — quiet {min(quiet_n, QUIET)} of {QUIET}")
    return items


# ---------------------------------------------------------------- THE SIDE READ (§10)
def oi_half(rec):
    """board.oi_read on the two nearer fronts: printed, never counted (N4)."""
    if rec.get("blind") or not rec.get("CE") or not rec.get("PE"):
        return ["NOT READ", CC + (_strip(rec.get("blind")) or "fronts not read")]
    return list(board.oi_read([_front(rec, "CE"), _front(rec, "PE")], rec.get("spot") or rec["CE"]["k"]))


def side_facts(rec, s):
    """§10.2: payers, holders and aggression for / against the named side, counted."""
    if s not in ("CALLS", "PUTS"):
        return []
    d = 1 if s == "CALLS" else -1
    P, Hs = ("CE", "PE") if d > 0 else ("PE", "CE")
    out = []
    if rec.get("blind") or not rec.get(P) or not rec.get(Hs):
        why = CC + (_strip(rec.get("blind")) or "fronts not read")
        out += [{"k": "payers", "state": "blind", "fact": why, "tag": "M"},
                {"k": "holders", "state": "blind", "fact": why, "tag": "M"}]
    else:
        p, h, pf = _front(rec, P), _front(rec, Hs), _last_fold(rec, P, rec["t"])
        out.append({"k": "payers", "tag": "M", **(
            {"state": "for", "fact": _fw(p) + (f" · {P} {_k(pf['k'])} folded {pf['t']}" if pf else "")}
            if p["state"] == UNW or pf else
            {"state": "against", "fact": f"{_fw(p)} — writers adding in its way"} if p["state"] == BLD else
            {"state": "flat", "fact": _fw(p)})})
        out.append({"k": "holders", "tag": "M", **(
            {"state": "for", "fact": _fw(h)} if h["state"] == BLD else
            {"state": "against", "fact": f"{_fw(h)} — the {'floor' if Hs == 'PE' else 'ceiling'} is leaving"}
            if h["state"] == UNW else {"state": "flat", "fact": _fw(h)})})
    st, fact, why = flow(rec, d)
    out.append({"k": "aggression", "tag": "I", "state": {"with": "for"}.get(st, st),
                "fact": fact if st in ("with", "against") else (why or fact)})
    return out


def sides(minutes, upto=None):
    """§10 at every minute 09:15..upto (an index): [{t, side, why, since, stamp}] --
    `stamp` on the first minute a side is named after no side or the other side."""
    out, last, since, named = [], None, None, None
    for m in minutes[:None if upto is None else upto + 1]:
        s, why = side_of(m)
        key = s or "could not check"
        if key != last:
            since, last = m["t"], key
        stamp = s in ("CALLS", "PUTS") and s != named
        if s in ("CALLS", "PUTS") or s == "no side":
            named = s
        out.append({"t": m["t"], "side": key, "why": why, "since": since, "stamp": stamp})
    return out


def side_line(rec, sd, expiry):
    """The side read at one minute, printed: word, since, the counted facts, the OI half, expiry."""
    facts = side_facts(rec, sd["side"])
    n = {s: sum(1 for f in facts if f["state"] == s) for s in ("for", "against", "blind")}
    oi = oi_half(rec)
    head = (f"{sd['side']} side since {sd['since']} · {n['for']} for · {n['against']} against · "
            f"{n['blind']} could not check · OI: {oi[0]}" if sd["side"] in ("CALLS", "PUTS") else
            f"no side since {sd['since']} — {sd['why']}" if sd["side"] == "no side" else sd["why"])
    return {"side": sd["side"], "since": sd["since"], "stamp": sd["stamp"], "text": head, "rows": sd["why"],
            "facts": facts, "oi_half": oi, "expiry": expiry, "note": "a count, never odds", "tag": "I"}


def agrees(side, role, s):
    """§10.4: your side vs the read."""
    if s not in ("CALLS", "PUTS"):
        return "no side — the rows do not agree" if s == "no side" else "could not check"
    return "agrees" if (s == ("CALLS" if side == "CE" else "PUTS")) == (role == "long") else "against"


def expiry_line(idx, day, expiry, src):
    """§10.3, from the day's own record only (never the live instrument dump)."""
    if not expiry:
        return {"text": CC + "expiry not in the day's record", "tag": "M"}
    if expiry == day:
        return {"text": (f"0DTE today for {idx}: the ATM strike's theta is at its fastest and its gamma at its "
                         "largest — a side is not a hold; the window's clock and line decide when to leave."),
                "zero_dte": True, "src": src, "tag": "M"}
    from datetime import date
    n = (date.fromisoformat(expiry) - date.fromisoformat(day)).days
    return {"text": f"expiry {expiry}, {n} days", "zero_dte": False, "src": src, "tag": "M"}
