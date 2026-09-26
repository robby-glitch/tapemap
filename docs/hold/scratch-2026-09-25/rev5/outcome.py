"""Scratch, descriptive only (seen AFTER the rev 2 rules were written): for each saved check and
today's two entries, which came first on the index -- the plan's rung (PLAN §2.4 touch: 1-min low /
high reaches the level) or the window's line break (rev 4: 1-min close; rev 5: 3-min close) -- within
30 finished minutes. Line = hold.line on today's REST candles (the as-built rev 4 copy + the rev 5
variant from probe3)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Users\kaam\Desktop\operator mode\tapemap"); sys.path.insert(0, HERE)
import hold, probe3
rows = json.load(open(os.path.join(HERE, "nifty_1m_2026-09-25.json")))
raw = [[f"{d}T{t}:00+05:30", o, h, l, c, 0, 0] for d, t, o, h, l, c in reversed(rows)]
DAY = "2026-09-25"
ix = {r[1]: [r[5], r[3], r[4]] for r in rows}
mins = [{"t": t, "ix": ix.get(t)} for t in hold.SESSION]
at = {m["t"]: i for i, m in enumerate(mins)}
cases = [("09:35 check 23200PE", "09:35", -1, 23100.0), ("09:43 check 23200PE", "09:43", -1, 23000.0),
         ("12:00 entry 23100CE", "12:00", 1, 23100.0), ("12:04 entry 23200PE", "12:04", -1, None),
         ("14:12 check 23100PE", "14:12", -1, 23100.0)]
for name, t, d, rung in cases:
    e = at[t]
    pv = hold.pivots(raw, DAY, asof=hold.SESSION[-1])
    out = {}
    for tag, fn in (("rev4 1m", probe3.ORIG), ("rev5 3m", probe3.line3)):
        ln = fn(mins, pv, d, e)
        L0 = ln[e]["L"]
        brk = next((mins[i]["t"] for i in range(e + 1, min(e + 31, len(mins))) if ln.get(i, {}).get("beyond")), None)
        out[tag] = (L0, brk)
    touch = None
    if rung is not None:
        for i in range(e + 1, min(e + 31, len(mins))):
            x = mins[i]["ix"]
            if x and ((x[2] <= rung) if d < 0 else (x[1] >= rung)):
                touch = mins[i]["t"]; break
    print(f"{name}: close {ix[t][0]} L {out['rev4 1m'][0]} | rung {rung} first touch {touch} | "
          f"break rev4 {out['rev4 1m'][1]} rev5 {out['rev5 3m'][1]} (within 30 min)")
