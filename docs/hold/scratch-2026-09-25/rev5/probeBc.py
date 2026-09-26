"""Scratch: option B with the S-d clamp -- on a trail the break level is the NEARER to price of the
old level and the new L -/+ B (rev 4's 'never away'). Reports every trail where the clamp binds and
whether any first FOLD changes versus unclamped B (frozen 33 + today's two)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Users\kaam\Desktop\operator mode\tapemap"); sys.path.insert(0, HERE)
os.chdir(r"C:\Users\kaam\Desktop\operator mode\tapemap")
import hold, probe3, probeB, test_hold as th
mm, CC = hold.mm, hold.CC
BINDS = []
def lineBc(minutes, pivs, d, e):
    bear = d < 0
    kind, word = ("H", "high") if bear else ("L", "low")
    m0 = minutes[e]
    if not m0.get("ix"): return None
    far = (lambda p, c: p > c) if bear else (lambda p, c: p < c)
    px0, t0 = m0["ix"][0], mm(m0["t"])
    mine = [p for p in pivs if p["kind"] == kind]
    known = sorted((p for p in mine if mm(p["confirm"]) <= t0 and far(p["price"], px0)), key=lambda p: mm(p["bar"]), reverse=True)
    used = set()
    if known:
        L, src = known[0]["price"], "swing"; used.add(known[0]["bar"])
    else:
        seen = [m["ix"] for m in minutes[:e + 1] if m.get("ix")]
        L = max(x[1] for x in seen) if bear else min(x[2] for x in seen); src = "session"
    B = probeB.noise(minutes, e)
    lvl = None if B is None else (L + B if bear else L - B)
    out, broken, prev, carried = {}, None, px0, False
    for i in range(e, len(minutes)):
        m = minutes[i]
        if not m.get("ix"):
            out[i] = {"L": L, "src": src, "broken_at": broken, "blind": CC + "x"}; continue
        c, beyond = m["ix"][0], False
        if i > e:
            for p in sorted((p for p in mine if p["bar"] not in used and t0 <= mm(p["confirm"]) < mm(m["t"])), key=lambda p: mm(p["confirm"])):
                used.add(p["bar"])
                if (p["price"] < L if bear else p["price"] > L) and far(p["price"], prev):
                    L = p["price"]; Bn = probeB.noise(minutes, i)
                    new = None if Bn is None else (L + Bn if bear else L - Bn)
                    if new is None: lvl, B = None, None
                    elif lvl is None: lvl, B = new, Bn
                    else:
                        near = min(lvl, new) if bear else max(lvl, new)
                        if near != new: BINDS.append((m["t"], L, Bn, lvl, new))
                        lvl, B = near, Bn
            if lvl is None:
                B = probeB.noise(minutes, i)
                if B is not None: lvl = L + B if bear else L - B
            if probe3.bar_close(m["t"]):
                x = lvl if lvl is not None else L
                carried = c > x if bear else c < x
                if carried and broken is None: broken = m["t"]
            beyond = carried
        out[i] = {"L": L, "src": src, "room": round(L - c if bear else c - L), "px": c, "beyond": beyond, "broken_at": broken}
        prev = c
    return out
diff = 0
if __name__ == "__main__":
  pass
for tr in (th._trades() if __name__ == "__main__" else []):
    rB, _ = probeB.run(tr, probeB.lineB)
    if rB is None: continue
    n0 = len(BINDS); rC, _ = probeB.run(tr, lineBc)
    a, b = rB["fold"], rC["fold"]
    if (a and (a["t"], a["rule"])) != (b and (b["t"], b["rule"])):
        diff += 1; print("DIFF", tr["id"][:40], a and (a["t"], a["rule"]), b and (b["t"], b["rule"]))
    if len(BINDS) > n0: print("clamp binds in", tr["id"][:40], BINDS[n0:])
if __name__ == "__main__": print("frozen first-FOLD differences:", diff, "| clamp binds:", len(BINDS))
