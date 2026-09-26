import sys, os
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "expr"))
import expr as X
th, hold = X.th, X.hold
mm = hold.mm
for key in [("NIFTY","2026-09-22"),("SENSEX","2026-09-24"),("NIFTY","2026-09-24"),("SENSEX","2026-09-22")]:
    D = th._day(*key); M = D["minutes"]
    best = []
    for i in range(5, len(M), 3):
        a, b = M[i-3].get("ix"), M[i].get("ix")
        S, _ = X.straddle(D, i)
        if a and b and S:
            best.append((round(abs(b[0]-a[0]) / S, 2), M[i]["t"], round(abs(b[0]-a[0]),1), S))
    best.sort(reverse=True)
    lateS = [(M[i]["t"], X.straddle(D, i)[0]) for i in (mm("14:30")-mm("09:15"), mm("15:00")-mm("09:15"), mm("15:20")-mm("09:15"))]
    print(key, "largest 3-min move / S:", best[:3], "S late:", lateS)
