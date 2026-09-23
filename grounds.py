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

W = 3               # 5-minute ladder bars in the window (15 min)
STRONG = 0.5        # |dCVD| rank vs today's own 15-min changes
ONE_SIDED = 0.8
FOR, AGAINST, FLAT, BLIND = "for", "against", "flat", "blind"


def _hh(t_ms) -> str:
    s = (int(t_ms) // 1000 + 19800) % 86400
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"


def _f(state, fact, tag="I"):
    return {"state": state, "fact": fact, "tag": tag}


def facts(bars, runs, fronts_rows) -> dict:
    """The evidence, measured once and shared by every call."""
    out = {}
    b = [x for x in (bars or []) if isinstance(x, dict) and x.get("cvd") is not None
         and None not in (x.get("c"), x.get("h"), x.get("l"), x.get("t"))]
    if len(b) < W + 1:
        out["cvd"] = out["flow"] = None
        out["cvd_why"] = out["flow_why"] = f"{len(b)} closed 5-min ladder bars; the window needs {W + 1}"
    else:
        a, z = b[-1 - W], b[-1]
        d = z["cvd"] - a["cvd"]
        hist = [abs(b[i]["cvd"] - b[i - W]["cvd"]) for i in range(W, len(b))]
        rank = sum(1 for h in hist if h <= abs(d)) / len(hist)

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
        out["cvd"] = {"d": d, "dpx": round(z["c"] - a["c"], 1), "rank": round(rank, 2), "since": since,
                      "div_top": div(hi, 1), "div_bottom": div(lo, -1), "tag": "I"}
        if a.get("oi") is not None and z.get("oi") is not None:
            doi, dpx = z["oi"] - a["oi"], z["c"] - a["c"]
            q = ("longs building" if dpx > 0 and doi > 0 else "shorts covering" if dpx > 0
                 else "shorts building" if doi > 0 else "longs exiting")
            out["fut_oi"] = f"futures OI {doi:+,.0f} with price {dpx:+,.1f} since {since}: {q}"
        t0 = b[-W]["t"]
        rb = sum(1 for r in (runs or []) if isinstance(r, dict) and (r.get("t") or 0) >= t0 and (r.get("side") or 0) > 0)
        rs = sum(1 for r in (runs or []) if isinstance(r, dict) and (r.get("t") or 0) >= t0 and (r.get("side") or 0) < 0)
        sk = [s for x in b[-W:] for s in (x.get("stacks") or []) if isinstance(s, dict)]
        out["flow"] = {"buy": rb + sum(1 for s in sk if s.get("side") == "buy"),
                       "sell": rs + sum(1 for s in sk if s.get("side") == "sell"),
                       "since": since, "tag": "I"}
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
    if kind == "range":
        if ce.get("state") == "BUILDING" and pe.get("state") == "BUILDING":
            return _f(FOR, f"both fronts writing: {_w(ce)}, {_w(pe)}{tail}", "M")
        gone = next((f for f in (ce, pe) if f.get("state") == "UNWINDING"), None)
        if gone:
            return _f(AGAINST, f"{_w(gone)} — one side is giving up{tail}", "M")
        return _f(FLAT, f"{_w(ce)}, {_w(pe)}{tail}", "M")
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

    def dom(a, b):
        return a >= 2 and a >= 2 * b
    if kind == "range":
        if dom(nb, ns) or dom(ns, nb):
            return _f(AGAINST, txt + " — one-sided")
        return _f(FOR, txt + (" — two-sided" if nb or ns else " — quiet"))
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


def ground(ctx, px, bars, runs, fronts_rows) -> dict:
    """Every engine call on the latest bar, each with its three families and a status."""
    F = facts(bars, runs, fronts_rows)
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
    print("grounds demo ok")
