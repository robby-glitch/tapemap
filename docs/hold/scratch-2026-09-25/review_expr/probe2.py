import sys, os, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "expr"))
import expr as X
th = X.th
from collections import Counter
DAYS = [(i, d) for d in ("2026-09-22", "2026-09-23", "2026-09-24") for i in ("NIFTY", "SENSEX", "BANKNIFTY")]
c = Counter(); byday = {}
for key in DAYS:
    D = th._day(*key); FR = X.oihist_fr(*key)
    for d in (1, -1):
        for i in range(len(D["minutes"])):
            e = X.expression(D, i, d, FR)
            f = e.get("facts") or {}
            r = f.get("room", (None,))[0]
            if r is None: continue
            ln, nz = e.get("line"), e.get("noise")
            inside = (ln is not None and nz is not None and ln <= nz)
            c[(r, "line<=noise" if inside else "line>noise" if nz is not None else "noise n/a")] += 1
            if key == ("NIFTY", "2026-09-23"):
                byday[(d, r, inside)] = byday.get((d, r, inside), 0) + 1
print(sorted(c.items()))
print("NIFTY 09-23", sorted(byday.items()))
