"""grounds.py -- every call the engine makes, held against the tape's own evidence.

THE PROBLEM (the operator, 2026-09-23): the engine calls MOVE SPENT, CAUTION,
GO, "FADE a test of X", "BREAK of X" off price and OI bars alone. It never sees
who is aggressing or whether the order flow agrees, so a call can read "SPENT --
don't chase" while buyers are still lifting every offer. Her rule: any call
this tool makes, anywhere, has to be grounded in facts.

WHAT A TRADER WOULD CHECK before trusting each kind of call, and so what this
file checks. Three independent families, each read from a source the engine
never touches:

  OI    the near-ATM fronts (fronts.py, her rule): is the side that PAYS for
        the move covering, or writing more in its way? [M]
  CVD   cumulative delta off the Upstox ladder (ux, every index): did the
        aggressors push WITH the price, and did a new high/low come WITHOUT a
        new CVD extreme (divergence -- the move not being paid for)? Prints and
        volume are measured; the buy/sell side of each print is [I].
  FLOW  big same-side fill runs and stacked imbalances off the same ladder:
        who hit size, which way, in the same window. [I] (side attribution).

A call is one of three kinds, and each family answers "for", "against",
"flat" or "blind" for that kind:

  move     "this continues in direction d"   (MOVE RUNNING, GO, NO FADE,
           BREAK of X, RIDE the hedge flow, a BULL/BEAR breadth)
  exhaust  "the move in d is done"            (MOVE SPENT/STALLING, TRAP
           UNWINDING, DON'T CHASE, FADE a test of X, FADE the band tag)
  range    "no side has an edge"              (WAIT, STAND ASIDE, CAUTION,
           FIGHT AT)

STATUS, never a score: CONTRADICTED if any readable family says the opposite;
BACKED if two or more say "for" and none against; THIN otherwise; PATA NAHI if
every family is blind. The facts behind each answer are printed with it. This
changes nothing the engine computes or logs -- it is how the face is allowed to
show a call.

THE [I] LAYER, declared, not tuned: the window is 3 closed 5-minute ladder bars
(15 min); "strong" CVD is a 15-min change at or above the median of today's own
15-min changes (STRONG); "one-sided" is the top fifth (ONE_SIDED); a flow side
"dominates" with at least 2 prints and twice the other side's. KILL CONDITION:
after ~30 sessions of forward calls, if CONTRADICTED calls do not resolve
against their own claim more often than BACKED ones, this grounding is noise
and is deleted rather than tuned. Pure, stdlib only, no I/O, no clock.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

W = 3               # 5-minute ladder bars in the window (15 min)
STRONG = 0.5        # |dCVD| rank vs today's own 15-min changes
ONE_SIDED = 0.8
MIN_PRIOR = 3       # earlier W-bar changes a rank needs; fewer is "could not check" (2026-09-28 audit, bug 1)
ROLL_DAYS = 7       # the near future's OI is blind this many calendar days up to its expiry (pro-tool P1-02)
THIN_FLOW = ("SENSEX",)   # futures too thin for a flow read: SENSEX prints a median 7-10 lots a 5-min bar [M] (P1-02)
FOR, AGAINST, FLAT, BLIND = "for", "against", "flat", "blind"


def roll_why(day, fut_expiry) -> str | None:
    """The sentence that blinds the near future's OI read in its expiry week, or None.
    The roll drains the expiring contract (NIFTY Sep: 17.0M -> 10.4M over 22-28 Sep [M])
    while it still trades, so a quadrant read on it names the roll, not positioning."""
    try:
        d, e = date.fromisoformat(str(day)), date.fromisoformat(str(fut_expiry))
    except (TypeError, ValueError):
        return None
    if not 0 <= (e - d).days < ROLL_DAYS:
        return None
    nxt = e.replace(day=1) + timedelta(days=32)          # the next contract is the next month's
    return f"the {e:%b} future is rolling into {nxt:%b}"


def _hh(t_ms) -> str:
    s = (int(t_ms) // 1000 + 19800) % 86400
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"


def _f(state, fact, tag="I"):
    return {"state": state, "fact": fact, "tag": tag}


def _rank(v, s):
    """|v| (the change ending at s[-1]) against today's EARLIER W-bar changes of series s, 0..1,
    or None when fewer than MIN_PRIOR exist. The current change is not its own history: counted
    in, the day's first read ranked 1.0 by construction and its second at least 0.5 = STRONG,
    so every CVD read "pressing" 09:35-09:44 (2026-09-28, the false 09:35 FOLD)."""
    h = [abs(s[i] - s[i - W]) for i in range(W, len(s) - 1) if s[i] is not None and s[i - W] is not None]
    return sum(1 for x in h if x <= abs(v)) / len(h) if len(h) >= MIN_PRIOR else None


def _unsized(n):
    return f"{n} earlier 15-min change{'' if n == 1 else 's'} today; sizing this one needs {MIN_PRIOR}"


def facts(bars, runs, fronts_rows, runs_why=None, roll=None, idx=None) -> dict:
    """The evidence, measured once and shared by every call. `runs_why` is the
    run detector's own reason (runs.Runs.why); anything but "checked, none"
    means it could not look, so zero runs is not zero. `roll` (roll_why's
    sentence) blinds the futures-OI quadrant; `idx` in THIN_FLOW blinds the
    flow read with the bar's own lot count as the reason (P1-02)."""
    out = {}
    b = [x for x in (bars or []) if isinstance(x, dict) and x.get("cvd") is not None
         and None not in (x.get("c"), x.get("h"), x.get("l"), x.get("t"))]
    if len(b) < W + 1:
        out["cvd"] = out["flow"] = None
        out["cvd_why"] = out["flow_why"] = f"{len(b)} closed 5-min ladder bars; the window needs {W + 1}"
    else:
        a, z = b[-1 - W], b[-1]
        d = z["cvd"] - a["cvd"]
        rank = _rank(d, [x["cvd"] for x in b])

        def div(i_ext, better):
            """A new extreme inside the window whose CVD did not beat its own earlier best."""
            if i_ext < len(b) - W or i_ext == 0:
                return None
            j = max(range(i_ext), key=lambda i: b[i]["cvd"] * better)
            if (b[i_ext]["cvd"] - b[j]["cvd"]) * better >= 0:
                return None
            word, px = ("high", b[i_ext]["h"]) if better > 0 else ("low", b[i_ext]["l"])
            return (f"new {word} {px:,.0f} at {_hh(b[i_ext]['t'])} with CVD {b[i_ext]['cvd']:+,.0f}, "
                    f"{'under' if better > 0 else 'above'} its {_hh(b[j]['t'])} "
                    f"{'peak' if better > 0 else 'trough'} {b[j]['cvd']:+,.0f}")
        hi = max(range(len(b)), key=lambda i: b[i]["h"])
        lo = min(range(len(b)), key=lambda i: b[i]["l"])
        since = _hh(b[-W]["t"])
        out["cvd"] = {"d": d, "dpx": round(z["c"] - a["c"], 1), "since": since,
                      "rank": None if rank is None else round(rank, 2),
                      "rank_why": _unsized(len(b) - W - 1) if rank is None else None,
                      "div_top": div(hi, 1), "div_bottom": div(lo, -1), "tag": "I"}
        if roll:
            out["fut_oi"] = f"futures OI: could not check — {roll}"
        elif a.get("oi") is not None and z.get("oi") is not None:
            doi, dpx = z["oi"] - a["oi"], z["c"] - a["c"]
            # a quadrant is named only when both legs are a real move for today, never off noise
            ro, rp = _rank(doi, [x.get("oi") for x in b]), _rank(dpx, [x["c"] for x in b])
            big = None not in (ro, rp) and ro >= STRONG and rp >= STRONG
            q = ("could not check — " + _unsized(len(b) - W - 1) if None in (ro, rp) else
                 "too small against today's own 15-min changes to read" if not big else
                 "longs building" if dpx > 0 and doi > 0 else "shorts covering" if dpx > 0
                 else "shorts building" if doi > 0 else "longs exiting")
            out["fut_oi"] = f"futures OI {doi:+,.0f} with price {dpx:+,.1f} since {since}: {q}"
        t0 = b[-W]["t"]
        rb = sum(1 for r in (runs or []) if isinstance(r, dict) and (r.get("t") or 0) >= t0 and (r.get("side") or 0) > 0)
        rs = sum(1 for r in (runs or []) if isinstance(r, dict) and (r.get("t") or 0) >= t0 and (r.get("side") or 0) < 0)
        sk = [s for x in b[-W:] for s in (x.get("stacks") or []) if isinstance(s, dict)]
        out["flow"] = {"buy": rb + sum(1 for s in sk if s.get("side") == "buy"),
                       "sell": rs + sum(1 for s in sk if s.get("side") == "sell"),
                       "since": since, "tag": "I",
                       "runs_why": runs_why if runs_why not in (None, "checked, none") else None}
    if idx in THIN_FLOW:
        # a thin future's prints are too few to read as flow; the count is the reason, never "quiet"
        lots = b[-1].get("vol") if b else None
        out["flow"] = None
        out["flow_why"] = (f"{idx} future, {lots:g} lots this bucket" if isinstance(lots, (int, float))
                           else f"{idx} future: no closed ladder bar yet")
    ce = next((f for f in (fronts_rows or []) if f.get("side") == "CE"), None)
    pe = next((f for f in (fronts_rows or []) if f.get("side") == "PE"), None)
    out["oi"] = {"ce": ce, "pe": pe} if (ce or pe) else None
    out["oi_why"] = None if out["oi"] else "near-ATM fronts not read"
    return out


def _w(f):
    return f"{f['side']} {float(f['k']):.0f} {str(f['state']).lower()}" if f else "?"


def _cvd(kind, d, F):
    c = F.get("cvd")
    if c is None:
        return _f(BLIND, F.get("cvd_why"))
    if c["rank"] is None:
        return _f(BLIND, c.get("rank_why"))
    sgn = (c["d"] > 0) - (c["d"] < 0)
    strong = c["rank"] >= STRONG
    txt = (f"CVD {c['d']:+,.0f} since {c['since']} with price {c['dpx']:+,.1f} "
           f"(rank {c['rank']:.2f} of today's 15-min moves)")
    div = c["div_top"] if d == 1 else c["div_bottom"] if d == -1 else None
    if kind == "range":
        if c["rank"] >= ONE_SIDED:
            return _f(AGAINST, txt + " — one side is pressing")
        return _f(FOR, txt + " — nobody pressing") if not strong else _f(FLAT, txt)
    if kind == "move":
        if div:
            return _f(AGAINST, "divergence: " + div)
        return _f(FOR if sgn == d else AGAINST, txt) if strong and sgn else _f(FLAT, txt)
    # exhaust: the d-move is claimed done
    if div:
        return _f(FOR, "divergence: " + div)
    if strong and sgn == d:
        return _f(AGAINST, txt + " — aggressors still pushing")
    return _f(FOR, txt) if strong and sgn == -d else _f(FLAT, txt)


def _oi(kind, d, F):
    o = F.get("oi")
    if not o:
        return _f(BLIND, F.get("oi_why"), "M")
    ce, pe = o.get("ce") or {}, o.get("pe") or {}
    tail = f" · {F['fut_oi']}" if F.get("fut_oi") else ""
    both_gone = ce.get("state") == "UNWINDING" and pe.get("state") == "UNWINDING"
    if kind == "range":
        if ce.get("state") == "BUILDING" and pe.get("state") == "BUILDING":
            return _f(FOR, f"both fronts writing: {_w(ce)}, {_w(pe)}{tail}", "M")
        if both_gone:
            return _f(AGAINST, f"both fronts unwinding: {_w(ce)}, {_w(pe)} — the writers holding the range are leaving{tail}", "M")
        gone = next((f for f in (ce, pe) if f.get("state") == "UNWINDING"), None)
        if gone:
            return _f(AGAINST, f"{_w(gone)} — one side is giving up{tail}", "M")
        return _f(FLAT, f"{_w(ce)}, {_w(pe)}{tail}", "M")
    if both_gone:   # straddle writers leaving both sides says nothing about WHICH way
        return _f(FLAT, f"both fronts unwinding: {_w(ce)}, {_w(pe)} — writers leaving both sides, no direction{tail}", "M")
    # fuel = the writers who PAY if price goes d (CE for up, PE for down); base = the other side
    fuel, base = (ce, pe) if d > 0 else (pe, ce)
    fs, bs = fuel.get("state"), base.get("state")
    if kind == "move":
        if fs == "UNWINDING":
            return _f(FOR, f"{_w(fuel)}: writers covering into the move{tail}", "M")
        if fs == "BUILDING" and bs != "BUILDING":
            return _f(AGAINST, f"{_w(fuel)}: writers still adding in its way{tail}", "M")
        if bs == "BUILDING" and fs != "BUILDING":
            return _f(FOR, f"{_w(base)}: writers holding the other side{tail}", "M")
        return _f(FLAT, f"{_w(fuel)}, {_w(base)}{tail}", "M")
    if fs == "UNWINDING":
        return _f(AGAINST, f"{_w(fuel)}: covering is still paying the move{tail}", "M")
    if fs in ("BUILDING", "STALLED"):
        how = "writing again" if fs == "BUILDING" else "stopped covering"
        return _f(FOR, f"{_w(fuel)}: {how} — the move's fuel is off{tail}", "M")
    return _f(FLAT, f"{_w(fuel)}{tail}", "M")


def _flow(kind, d, F):
    f = F.get("flow")
    if f is None:
        return _f(BLIND, F.get("flow_why"))
    nb, ns = f["buy"], f["sell"]
    txt = f"since {f['since']}: {nb} buy / {ns} sell prints of size (fill runs + stacked imbalances)"
    if f.get("runs_why"):   # "we could not check" is never "we checked and found nothing"
        if not (nb or ns):
            return _f(BLIND, f"since {f['since']}: no stacked imbalance; fill runs could not be read — {f['runs_why']}")
        txt += f"; fill runs could not be read — {f['runs_why']}"

    def dom(a, b):
        return a >= 2 and a >= 2 * b
    if kind == "range":
        if dom(nb, ns) or dom(ns, nb):
            return _f(AGAINST, txt + " — one-sided")
        return _f(FOR, txt + (" — two-sided" if nb and ns else " — thin" if nb or ns else " — quiet"))
    nd, no = (nb, ns) if d > 0 else (ns, nb)
    if kind == "move":
        return _f(FOR, txt) if dom(nd, no) else _f(AGAINST, txt) if dom(no, nd) else _f(FLAT, txt)
    return _f(FOR, txt) if dom(no, nd) else _f(AGAINST, txt) if dom(nd, no) else _f(FLAT, txt)


_EP = re.compile(r"^MOVE (RUNNING|STALLING|SPENT) — (UP|DOWN)")
_TRAP = re.compile(r"^TRAP UNWINDING — (BULL|BEAR)")
_NUM = re.compile(r"\b(?:of|at|the) (-?\d[\d,]*(?:\.\d+)?)")


def _toward(text, px):
    """+1 / -1: which way price must travel to reach the level the call names."""
    m = _NUM.search(text)
    if not m or px is None:
        return None
    x = float(m.group(1).replace(",", ""))
    return 1 if x > px else -1 if x < px else None


def calls_of(ctx: dict, px) -> list:
    """(source, text, kind, d) for every call on the engine's bar. The engine's
    sentences are fixed templates (engine.Session.context), read by prefix the
    way fronts.py reads NO FADE; a play no rule knows is kept as PATA NAHI."""
    ctx = ctx or {}
    out = []
    ep = ctx.get("episode") or ""
    m, t = _EP.match(ep), _TRAP.match(ep)
    ep_dir = (1 if m.group(2) == "UP" else -1) if m else None
    if m:
        out.append(("episode", ep, "move" if m.group(1) == "RUNNING" else "exhaust", ep_dir))
    elif t:
        out.append(("episode", ep, "exhaust", 1 if t.group(1) == "BULL" else -1))
    elif ep.startswith("FIGHT AT"):
        out.append(("episode", ep, "range", None))
    v = ctx.get("verdict")
    vt = f"{v} — {ctx.get('vwhy') or ''}"
    if v == "GO":
        reg, line = (ctx.get("pin") or {}).get("regime") or "", ctx.get("line") or ""
        d = (ep_dir if m and m.group(1) == "RUNNING" else
             1 if reg.endswith("UP") or line.startswith("TREND-UP") else
             -1 if reg.endswith("DOWN") or line.startswith("TREND-DOWN") else None)
        out.append(("verdict", vt, "move", d))
    elif v == "READY":
        out.append(("verdict", vt, "move", None))
    elif v == "SPENT":
        out.append(("verdict", vt, "exhaust", ep_dir))
    elif v in ("WAIT", "STAND ASIDE", "CAUTION"):
        out.append(("verdict", vt, "range", None))
    b = ctx.get("breadth") or ""
    if "BULL" in b or "BEAR" in b:
        out.append(("breadth", b, "move", 1 if "BULL" in b else -1))
    for p in ctx.get("plays") or []:
        if not isinstance(p, str):
            continue
        if "FADE the" in p and "band tag" in p:
            kind, d = "exhaust", (-1 if "scalp ~1R up" in p else 1)
        elif p.startswith("NO FADE"):
            kind, d = "move", _toward(p, px)
        elif p.startswith("DON'T CHASE"):
            kind, d = "exhaust", ep_dir
        elif p.startswith("RIDE"):
            kind, d = "move", (1 if "dips" in p else -1)
        elif p.startswith("FADE a test of"):
            kind, d = "exhaust", _toward(p, px)
        elif p.startswith("BREAK of"):
            kind, d = "move", _toward(p, px)
        else:
            kind, d = None, None
        out.append(("play", p, kind, d))
    return out


def ground(ctx, px, bars, runs, fronts_rows, runs_why=None, roll=None, idx=None) -> dict:
    """Every engine call on the latest bar, each with its three families and a status."""
    F = facts(bars, runs, fronts_rows, runs_why, roll=roll, idx=idx)
    rows = []
    for src, text, kind, d in calls_of(ctx, px):
        if kind is None or (kind != "range" and d is None):
            why = "no grounding rule for this play" if kind is None else "the call names no direction"
            fam = {k: _f(BLIND, why) for k in ("oi", "cvd", "flow")}
        else:
            fam = {"oi": _oi(kind, d, F), "cvd": _cvd(kind, d, F), "flow": _flow(kind, d, F)}
        st = [f["state"] for f in fam.values()]
        status = ("CONTRADICTED" if AGAINST in st else "BACKED" if st.count(FOR) >= 2
                  else "PATA NAHI" if all(s == BLIND for s in st) else "THIN")
        rows.append({"source": src, "text": text, "kind": kind,
                     "dir": {1: "up", -1: "down"}.get(d), "status": status, **fam})
    return {"calls": rows, "facts": {k: F.get(k) for k in ("cvd", "flow", "fut_oi")},
            "tag": "I", "note": "status, never a score: BACKED = two or more families agree and none "
                                "contradict; CONTRADICTED = the tape says the opposite of the call"}


if __name__ == "__main__":
    ms = lambda h, m: ((h * 60 + m) * 60 - 19800) * 1000   # IST HH:MM -> epoch ms on day 0
    # price makes a new high at 11:50 while CVD is below its 11:35 peak: a top divergence
    bars = [{"t": ms(11, 30 + 5 * i), "h": h, "l": h - 10, "c": h - 2, "cvd": c, "oi": 100 + i, "stacks": []}
            for i, (h, c) in enumerate([(100, 0), (110, 900), (108, 700), (112, 400), (115, 300)])]
    runs = [{"t": ms(11, 48), "side": -1}, {"t": ms(11, 49), "side": -1}]
    fr = [{"side": "CE", "k": 23400.0, "state": "BUILDING"}, {"side": "PE", "k": 23300.0, "state": "STALLED"}]
    ctx = {"episode": "MOVE RUNNING — UP leg 23380→23471 live, pullbacks shallow", "verdict": "CAUTION",
           "vwhy": "no edge defined right now", "breadth": "STRONG BULL",
           "plays": ["FADE a test of 120 (session high)", "WHATEVER new play"]}
    g = {c["text"][:12]: c for c in ground(ctx, 113.0, bars, runs, fr)["calls"]}
    run = g["MOVE RUNNING"]
    assert run["status"] == "CONTRADICTED" and run["cvd"]["state"] == AGAINST and "divergence" in run["cvd"]["fact"]
    assert run["oi"]["state"] == AGAINST and run["flow"]["state"] == AGAINST   # CE writing in the way, sellers hitting
    assert g["FADE a test "]["status"] == "BACKED"                                  # the exhaustion call is what the tape backs
    assert g["WHATEVER new"]["status"] == "PATA NAHI"                               # an unknown play is never passed as grounded
    assert ground({}, None, [], [], [])["calls"] == []
    # the close, 2026-09-23: both ATM fronts unwinding, a quiet last 15 min after a day of big swings
    day = [{"t": ms(10, 5 * i), "h": c + 5, "l": c - 5, "c": c, "cvd": c, "oi": oi, "stacks": []}
           for i, (c, oi) in enumerate([(100, 0), (150, 5000)] * 3 + [(151, 5010), (152, 5020), (153, 5030)])]
    both = [{"side": "CE", "k": 23400.0, "state": "UNWINDING"}, {"side": "PE", "k": 23400.0, "state": "UNWINDING"}]
    ctx = {"verdict": "STAND ASIDE", "vwhy": "pin/chop", "breadth": "STRONG BULL", "plays": ["BREAK of 140 (x)"]}
    G = ground(ctx, 153.0, day, [{"t": ms(10, 42), "side": -1}], both)
    v, up, dn = G["calls"]
    assert up["oi"]["state"] == dn["oi"]["state"] == FLAT     # covering on BOTH sides backs neither direction
    assert v["oi"]["state"] == AGAINST and "both fronts" in v["oi"]["fact"]
    assert v["flow"]["fact"].endswith("— thin")                # one print is not "two-sided"
    assert "too small" in G["facts"]["fut_oi"]                 # +30 OI on +3 points is not "longs building"
    blind = ground(ctx, 153.0, day, [], both, runs_why="fewer than 50 fills in the last 20 minutes")["calls"][0]
    assert blind["flow"]["state"] == BLIND                     # a detector that could not rank is not "quiet"
    print("grounds demo ok")
