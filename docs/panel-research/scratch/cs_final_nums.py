import json, statistics as st
exec(open('cs_flow_test.py', encoding='utf-8').read().split('# (1) per-side')[0])
def pc(xs, p): xs = sorted(xs); k = (len(xs) - 1) * p / 100; f = int(k); c = min(f + 1, len(xs) - 1); return xs[f] + (xs[c] - xs[f]) * (k - f)
def xC(d, E, W):
    ref = [o for o in FULL if o != d]
    cm = med(sum(V[o][m] for m in range(OPEN + 1, E)) for o in ref)
    tempo = sum(V[d][m] for m in range(OPEN + 1, E)) / cm
    sc = tempo ** min(1.0, (E - OPEN) / 60.0)
    return w(V[d], E, W) / (med(w(V[o], E, W) for o in ref) * sc), tempo
d = '2026-10-19'; E = 14 * 60 + 30
for W in (5, 15, 60):
    x, t = xC(d, E, W); print('19 Oct 14:30 total pace %2dm x_C = %.2f  (tempo %.2f)' % (W, x, t))
# p-values of the 5-min x_C pool (all days, 5-min stride), and rank of key windows
pool = []
for dd in FULL:
    for EE in range(OPEN + 36, CLOSE - 4, 5): pool.append(xC(dd, EE, 5)[0])
print('5-min x_C pool n=%d p70 %.2f p80 %.2f p85 %.2f p90 %.2f p95 %.2f' % (len(pool), pc(pool, 70), pc(pool, 80), pc(pool, 85), pc(pool, 90), pc(pool, 95)))
for hm_, EE in (('13:25', 13 * 60 + 25), ('14:25', 14 * 60 + 25), ('14:30', 14 * 60 + 30)):
    x = xC(d, EE, 5)[0]; r = 100 * sum(1 for v in pool if v <= x) / len(pool)
    print('  %s x_C %.2f  rank p%.0f' % (hm_, x, r))
# 15m pool for rank of 14:30 15m
pool15 = [xC(dd, EE, 15)[0] for dd in FULL for EE in range(OPEN + 60, CLOSE - 14, 5)]
x15 = xC(d, E, 15)[0]; print('15m x_C %.2f rank p%.0f (pool n=%d)' % (x15, 100 * sum(1 for v in pool15 if v <= x15) / len(pool15), len(pool15)))
# day tempo percentile at 14:30 vs other days' cumulative
cums = {dd: sum(V[dd][m] for m in range(OPEN + 1, E)) for dd in FULL}
print('cum vol to 14:30: 19 Oct %d, others median %d, rank among 12 days: %d' % (cums[d], med(v for k, v in cums.items() if k != d), 1 + sum(1 for k, v in cums.items() if v < cums[d])))
x45, t45 = xC(d, 14 * 60 + 15, 45)
print('pehle45 (13:30-14:15) total pace x_C = %.2f (tempo at 14:15 %.2f); lots %d' % (x45, t45, w(V[d], 14 * 60 + 15, 45)))
print('UX per-side lots/min last 5m: buy %.0f sell %.0f' % (w(Bu[d], E, 5) / 5, w(Se[d], E, 5) / 5))
