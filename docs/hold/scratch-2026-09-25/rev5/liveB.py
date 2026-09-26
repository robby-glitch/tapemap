"""Scratch, read-only: today's two live trades under rev 4 / option A / option B. The line comes
from today's REST index candles (hold.line, probe3.line3, probeB.lineB); rules 4-6 are rebuilt
from the live per-minute rows (rows_*.json, GET 16:14). qA (payers adding held 3 min) is read off
the PARTNER trade's HOLDERS row (the same nearer front: the CE trade's payers are the PE trade's
holders and vice versa), because rev 4's row precedence can print a live fold over it."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Users\kaam\Desktop\operator mode\tapemap")
sys.path.insert(0, HERE)
import hold      # noqa: E402  (the as-built rev 4 copy)
import probe3    # noqa: E402
import probeB    # noqa: E402

DAY = "2026-09-25"
rows = json.load(open(os.path.join(HERE, "nifty_1m_2026-09-25.json")))
raw = [[f"{d}T{t}:00+05:30", o, h, l, c, 0, 0] for d, t, o, h, l, c in reversed(rows)]
ix = {r[1]: [r[5], r[3], r[4]] for r in rows}
mins = [{"t": t, "ix": ix.get(t)} for t in hold.SESSION]
at = {m["t"]: i for i, m in enumerate(mins)}
pv = hold.pivots(raw, DAY, asof=hold.SESSION[-1])
R = {k: {r["t"]: r for r in json.load(open(os.path.join(HERE, f"rows_{k}.json"), encoding="utf-8"))["rows"]}
     for k in ("NIFTY-23100CE-long-120121", "NIFTY-23200PE-long-120528")}
TR = {"NIFTY-23100CE-long-120121": ("12:00", 1, "NIFTY-23200PE-long-120528", 113.55),
      "NIFTY-23200PE-long-120528": ("12:04", -1, "NIFTY-23100CE-long-120121", 155.40)}


def first_fold(tid, fn):
    t0, d, partner, p0 = TR[tid]
    e = at[t0]
    LN = fn(mins, pv, d, e)
    me, pa = R[tid], R[partner]

    def qA(t):
        r = me.get(t)
        if r and r["payers"]["state"] == "against":
            return True
        ts = [hold.hm(hold.mm(t) - k) for k in range(3)]
        if all(pa.get(x) and pa[x]["holders"]["state"] == "for" for x in ts):
            return True
        return False
    for i in range(e, len(mins)):
        t = mins[i]["t"]
        r, ln = me.get(t), LN[i]
        if r is None:
            continue
        if ln.get("beyond"):
            return t, 3, ln
        q, rA = qA(t), r["holders"]["state"] == "against"
        if q and rA:
            return t, 4, ln
        if r["clock"].get("quiet") == 15:
            return t, 5, ln
        if sum([q, r["flow"]["state"] == "against", r["trend"]["state"] == "against"]) >= 2:
            return t, 6, ln
    return None, None, None


for tid in TR:
    for name, fn in (("rev4", probe3.ORIG), ("A", probe3.line3), ("B", probeB.lineB)):
        t, rule, ln = first_fold(tid, fn)
        extra = ""
        if rule == 3:
            extra = f"L {ln['L']} close {ln['px']} by {round(abs(ln['px'] - ln['L']), 1)}"
            if "B" in ln:
                extra += f" B {ln['B']} @{ln['B_at']} level {ln['level']}"
        p = (R[tid].get(t) or {}).get("prem", {}).get("c") if t else None
        print(tid[:14], name, t, rule, extra, "prem", p, "pts", round(p - TR[tid][3], 2) if p else None)
    LN = probeB.lineB(mins, pv, TR[tid][1], at[TR[tid][0]])
    print("   B values along the trade:", sorted({(v.get("L"), v.get("B"), v.get("B_at"), v.get("level")) for v in LN.values() if v.get("L")}, key=lambda x: str(x[2])))
    # when (if ever) would the B line itself have broken, whatever folded first
    brk = next((mins[i]["t"] for i in sorted(LN) if LN[i].get("beyond")), None)
    print("   B line first break (any rule aside):", brk)
