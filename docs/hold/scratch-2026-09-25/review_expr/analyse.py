import json, os, statistics as st
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "per_minute.json")))
allm = [m for s in R.values() for m in s]
print("minutes", len(allm), Counter(m["w"] for m in allm))

# 1. flips: word changes between consecutive finished minutes, per index-day-direction
flips, runs = 0, []
for k, s in R.items():
    cur, n = None, 0
    for m in s:
        if m["w"] != cur:
            if cur is not None:
                flips += 1; runs.append(n)
            cur, n = m["w"], 1
        else:
            n += 1
    runs.append(n)
print("flips total", flips, "per index-day-dir", round(flips / len(R), 1), "median run (min)", st.median(runs),
      "runs of 1 min", sum(1 for r in runs if r == 1), "of", len(runs))
# flips among spoken words only (BUY<->SELL<->EITHER)
bs = 0
for s in R.values():
    for a, b in zip(s, s[1:]):
        if {a["w"], b["w"]} <= {"BUY", "SELL", "EITHER"} and a["w"] != b["w"]:
            bs += 1
print("minute-to-minute changes among BUY/SELL/EITHER", bs)
bs2 = sum(1 for s in R.values() for a, b in zip(s, s[1:]) if {a["w"], b["w"]} == {"BUY", "SELL"})
print("direct BUY<->SELL flips", bs2)

# 2. margins and words by refusal
c = Counter()
for m in allm:
    if m["w"] in ("BUY", "SELL", "EITHER"):
        nb, ns = m["nb"], m["ns"]
        if m["w"] == "BUY":
            kind = "by refusal (SELL refused)" if m["rs"] else "on the count"
            c[("BUY", kind, "tie/0-0" if nb == ns else f"margin {nb-ns}")] += 1
        elif m["w"] == "SELL":
            kind = "by refusal (BUY refused)" if m["rb"] else "on the count"
            c[("SELL", kind, "tie" if nb == ns else f"margin {ns-nb}")] += 1
        else:
            c[("EITHER", f"{nb}-{ns}")] += 1
for k in sorted(c):
    print(k, c[k])
# BUY by refusal: which refusal
cr = Counter()
for m in allm:
    if m["w"] == "BUY" and m["rs"]:
        cr[tuple(sorted(set(m["rs_codes"])))] += 1
print("BUY-by-refusal codes", cr.most_common(8))

# 3. fact co-occurrence (both directions, where the line could be set)
F = [m["f"] for m in allm if m["f"]]
def co(a, av, b, bv):
    n_a = sum(1 for f in F if f.get(a) == av)
    n_b = sum(1 for f in F if f.get(b) == bv)
    n_ab = sum(1 for f in F if f.get(a) == av and f.get(b) == bv)
    exp = n_a * n_b / len(F)
    return n_a, n_b, n_ab, round(exp)
for pair in [("speed", "buy", "room", "buy"), ("regime", "sell", "premium", "sell"), ("regime", "buy", "premium", "buy"),
             ("speed", "buy", "premium", "buy"), ("speed", "buy", "regime", "buy"), ("room", "sell", "regime", "sell"),
             ("shield", "sell", "room", "sell"), ("shield", "sell", "premium", "sell")]:
    print("co", pair, "n_a n_b n_ab expected_if_indep", co(*pair))

# 4. PREMIUM FOR BUY on a move against d over the same 15 min
pb = [(k, m) for k, s in R.items() for m in s if m["f"].get("premium") == "buy" and m["mv15"] is not None]
against = sum(1 for k, m in pb if (m["mv15"] < 0) == (int(k.split()[-1]) > 0) and m["mv15"] != 0)
print("PREMIUM FOR BUY minutes", len(pb), "of which the index's 15-min move was AGAINST d", against)

# 5. sell strike in straddles at SELL words, and its premium
rs, prm, otm = [], [], []
for m in allm:
    if m["w"] == "SELL" and m["otm"] is not None and m["S"]:
        rs.append(m["otm"] / m["S"]); otm.append(m["otm"])
        if m["spx"] is not None:
            prm.append(m["spx"])
q = lambda v: [round(x, 2) for x in st.quantiles(v, n=4)]
print("SELL words with S", len(rs), "otm/S quartiles", q(rs), "beyond 1 straddle", sum(r > 1 for r in rs),
      "beyond 0.5", sum(r > 0.5 for r in rs))
print("SELL otm pts quartiles", q(otm), "sell premium quartiles", q(prm))
# per index
for idx in ("NIFTY", "SENSEX", "BANKNIFTY"):
    v = [m["otm"] / m["S"] for k, s in R.items() if k.startswith(idx) for m in s
         if m["w"] == "SELL" and m["otm"] is not None and m["S"]]
    p = [m["spx"] for k, s in R.items() if k.startswith(idx) for m in s if m["w"] == "SELL" and m["spx"] is not None]
    bp = [m["bpx"] for k, s in R.items() if k.startswith(idx) for m in s if m["w"] == "SELL" and m["bpx"] is not None]
    if v:
        print(idx, "SELL n", len(v), "otm/S median", round(st.median(v), 2), ">1:", sum(x > 1 for x in v),
              "sell prem median", round(st.median(p), 1), "ATM buy-leg prem median", round(st.median(bp), 1))

# 6. % elasticity of the two legs over +30 at the 30-min grid (09:45..15:15), unconditioned on the word
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "expr"))
import expr as X  # noqa
th = X.th
grid = [f"{h:02d}:{m:02d}" for h in range(9, 16) for m in (15, 45)]
grid = [g for g in grid if "09:45" <= g <= "15:15"]
dom, n, gs = 0, 0, []
rat = []
for k, s in R.items():
    idx, day, d = k.split()
    D = th._day(idx, day)
    by_t = {m["t"]: m for m in s}
    for g in grid:
        m = by_t.get(g)
        if not m or m["sk"] is None or m["bpx"] is None or m["spx"] is None:
            continue
        i = m["i"]
        j = min(i + 30, len(D["minutes"]) - 1)
        b30 = X.prem(D, m["bk"], "CE" if int(d) > 0 else "PE", j)
        s30 = X.prem(D, m["sk"], m["sside"], j)
        if b30 is None or s30 is None or not m["bpx"] or not m["spx"]:
            continue
        lp = (b30 - m["bpx"]) / m["bpx"]
        sp = (m["spx"] - s30) / m["spx"]
        n += 1
        dom += abs(sp) > abs(lp)
        if lp:
            rat.append(abs(sp) / abs(lp) if lp else None)
print("grid units priced", n, "units where |short %| > |long %| (the short leg sets G's size)", dom,
      "median |short%|/|long%|", round(st.median([r for r in rat if r is not None]), 2))
