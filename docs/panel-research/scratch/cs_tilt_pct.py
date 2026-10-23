import json
exec(open('cs_states.py', encoding='utf-8').read().split('BAND = ')[0])
def pc(xs, p): xs = sorted(xs); k = (len(xs) - 1) * p / 100; f = int(k); c = min(f + 1, len(xs) - 1); return xs[f] + (xs[c] - xs[f]) * (k - f)
for W in (5, 15, 30, 60):
    v = []
    for d in FULL:
        for E in range(10 * 60 + 20, CLOSE, 5):
            t = tl(d, E, W) if E - W >= OPEN + 1 else None
            if t is not None: v.append(abs(t))
    print('|tilt| over %2dm  n=%d  p50 %.2f  p70 %.2f  p80 %.2f  p90 %.2f  p95 %.2f' % (W, len(v), pc(v, 50), pc(v, 70), pc(v, 80), pc(v, 90), pc(v, 95)))
