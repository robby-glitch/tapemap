"""export.py -- the HANDSHAKE mockup's data: per minute, NIFTY spot, the RAFTAAR picture (engine, lockstep), every strike's
OI written today, the three order-flow sources (Dext 1-min, GoCharting 5-min, Upstox 5-min, all in lots), and the
handshake events (Mary 27 Oct: "flow pushes there -> OI must answer here; walls breaking, floors forming"). Causal: a PUSH
is known at its minute, its ANSWER only ANSWER minutes later. Read-only on data/. Rows, not rates.

    python export.py        -> data.js + RAFTAAR-handshake.html (self-contained)
"""
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "final"), os.path.join(HERE, "..", "live"), os.path.join(HERE, "..", "coil")]
import coil_scan as C          # noqa: E402  (chain minutes)
from export import lockstep    # noqa: E402  (the engine, all three indices in step: ../live/export.py)

DATA = os.path.join(HERE, "..", "..", "..", "data")
LOT = 65
DAYS = [("2026-10-26", "trend ▲ · the 09:52 wall break"), ("2026-10-22", "chop · the 12:21 fake"),
        ("2026-10-23", "trend ▼ then +204"), ("2026-10-27", "Oct expiry")]
NORM, PUSH_X, MIN_PUSH = 30, 2.0, 150      # [I] a 2-min fut delta >= 2x the median |2-min delta| of the last 30 min, and >= 150 lots
ANSWER, QUIET = 4, 4                       # [I] the answer is read 4 min after the push; one push per side per 4 min
CUT_L, CUT_FRAC = 3.0, 0.04                # [I] a strike "answered" when its OI moved >= max(3L, 4 % of its own build)
PRINT_X = 10                               # [I] a 2-min delta >= 10x normal is a block print (a roll / cross), shown apart from pushes


def dext(day):
    """{minute: lots or None} -- None when Dext printed a bar with no volume (its 27 Oct afternoon): missing, never 0"""
    p = os.path.join(DATA, "dext", f"dext_NSE-48704_{day}.jsonl")
    out = {}
    for line in open(p, encoding="utf-8") if os.path.exists(p) else ():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        m = int(r["time"][11:13]) * 60 + int(r["time"][14:16])
        out[m] = None if not r.get("total_volume") else round(r["delta"] / LOT)
    return out


def bars5(path):
    """[[minute, delta lots]] from a 5-min ladder file (GoCharting tape_ / Upstox ux_)"""
    out = []
    for line in open(path, encoding="utf-8") if os.path.exists(path) else ():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        m = int((r["t"] / 1000 + 19800) % 86400 // 60)
        if 555 <= m <= 930 and r.get("delta") is not None:
            out.append([m, round(r["delta"])])
    return out


def oi_at(r, k, side):
    return C.leg_of(r, k, side).get("oi_chg")


def day_data(day, label):
    R = C.minutes(day)
    ms = sorted(m for m in R if 555 <= m <= 930)
    sp = {m: R[m]["spot"] for m in ms}
    ks = sorted({s["k"] for s in R[ms[-1]]["strikes"]})
    step = min(b - a for a, b in zip(ks, ks[1:]))
    lo, hi = min(sp.values()) - 3 * step, max(sp.values()) + 3 * step
    keep = [k for k in ks if lo <= k <= hi]
    D = dext(day)
    outs, _, _ = lockstep(day)
    pic = {}
    for t, o in outs["NIFTY"]:
        p = o.get("picture") or {}
        g = p.get("grade") or {}
        pic[int(t[:2]) * 60 + int(t[3:])] = [p.get("word"), p.get("dir"), g.get("n"), g.get("N"), p.get("story")]

    def d2(m):
        a, b = D.get(m - 1), D.get(m)
        return None if a is None or b is None else a + b

    events, last = [], {1: -99, -1: -99}
    for m in ms:
        x = d2(m)
        hist = [abs(d2(j)) for j in range(m - NORM, m) if d2(j) is not None]
        if x is None or len(hist) < 10:
            continue
        norm = st.median(hist)
        sgn = 1 if x > 0 else -1
        if abs(x) < max(MIN_PUSH, PUSH_X * norm) or m - last[sgn] < QUIET:
            continue
        last[sgn] = m
        r0, s0 = R[m], sp[m]
        side = "ce" if sgn > 0 else "pe"
        band = [k for k in keep if (s0 - step / 2 <= k <= s0 + 2 * step if sgn > 0 else s0 - 2 * step <= k <= s0 + step / 2)]
        att = max(band, key=lambda k: oi_at(r0, k, side) or 0) if band else None
        ev = {"m": m, "dir": sgn, "lots": x, "norm": round(norm), "spot": s0, "k": att, "side": side.upper(),
              "print": abs(x) >= PRINT_X * norm}         # a block (26 Oct 12:41: 8,590 lots, price still): a BADA PRINT, not a push
        m4 = next((j for j in ms if j >= m + ANSWER), None)
        if att is not None and m4 is not None:
            o0, o4 = oi_at(r0, att, side), oi_at(R[m4], att, side)
            moved = sgn * (sp[m4] - s0)
            if None not in (o0, o4):
                chg = (o4 - o0) / 1e5
                bar = max(CUT_L, CUT_FRAC * max(o0, 0) / 1e5)
                through = moved >= 0.3 * step
                ev["chg"] = round(chg, 1)
                ev["ans"] = ("TOOT" if chg <= -bar else "PHANS" if chg >= bar and through else "TIKI" if chg >= bar else "NAHI")
                # behind price: the other side writing under (buy push) / over (sell push) the price at the answer
                s4, other = sp[m4], ("pe" if sgn > 0 else "ce")
                zone = [k for k in keep if (s4 - 2 * step <= k <= s4 if sgn > 0 else s4 <= k <= s4 + 2 * step)]
                adds = [(k, ((oi_at(R[m4], k, other) or 0) - (oi_at(r0, k, other) or 0)) / 1e5) for k in zone]
                best = max(adds, key=lambda a: a[1]) if adds else None
                if best and best[1] >= CUT_L:
                    ev["behind"] = [best[0], round(best[1], 1)]
                ev["am"] = m4
                ev["moved"] = round(moved)
        events.append(ev)

    rows = []
    for m in ms:
        r = R[m]
        rows.append({"m": m, "s": round(sp[m], 1), "d": D.get(m), "p": pic.get(m),
                     "oi": [None if oi_at(r, k, sd) is None else round(oi_at(r, k, sd) / 1e5, 1) for k in keep for sd in ("ce", "pe")]})
    return {"day": day, "label": label, "step": step, "strikes": keep, "rows": rows, "events": events,
            "G": bars5(os.path.join(DATA, "tape", f"tape_NIFTY_{day}.jsonl")), "U": bars5(os.path.join(DATA, "tape", f"ux_NIFTY_{day}.jsonl"))}


if __name__ == "__main__":
    data = [day_data(d, l) for d, l in DAYS]
    js = "window.HS = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    open(os.path.join(HERE, "data.js"), "w", encoding="utf-8").write(js)
    tpl = os.path.join(HERE, "handshake.html")
    if os.path.exists(tpl):
        page = open(tpl, encoding="utf-8").read().replace('<script src="data.js"></script>', "<script>" + js + "</script>")
        open(os.path.join(HERE, "RAFTAAR-handshake.html"), "w", encoding="utf-8").write(page)
    for x in data:
        ans = {}
        for e in x["events"]:
            ans[e.get("ans", "?")] = ans.get(e.get("ans", "?"), 0) + 1
        print(x["day"], len(x["rows"]), "min ·", len(x["events"]), "pushes", ans, "· G", len(x["G"]), "U", len(x["U"]))
        for e in x["events"][:40]:
            print("   ", C.hm(e["m"]), "▲" if e["dir"] > 0 else "▼", e["lots"], "(norm", e["norm"], ")", e["side"], e["k"], e.get("ans"), e.get("chg"), "behind", e.get("behind"), "moved", e.get("moved"))
