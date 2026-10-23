"""Critique test 3: flow structure on NIFTY Upstox 1-min, 12 full days (descriptive; LOO references).
 (1) how much of per-side 'x normal' is just total pace?  (2) tilt-window persistence (which EK-TARFA window)  (3) speed-ratio persistence total vs side
 (4) bursts vs price result  (5) the 19 Oct 14:30 numbers for the revised panel."""
import json, statistics as st, math
SCR = 'C:/Users/kaam/Desktop/operator mode/tapemap/docs/panel-research/scratch/'
OPEN, CLOSE = 555, 930
FULL = ['2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30',
        '2026-10-01', '2026-10-05', '2026-10-06', '2026-10-08', '2026-10-19']
raw = json.load(open(SCR + 'pr_1m_NIFTY.json', encoding='utf-8'))
def mint(ms): return (int(ms) // 60000 + 330) % 1440
V, Bu, Se, C = {}, {}, {}, {}
for d in FULL:
    B = {mint(b['t']): b for b in raw[d]['1m'] if OPEN <= mint(b['t']) < CLOSE and not b['partial']}
    V[d] = {m: (B[m]['vol'] if m in B else 0.0) for m in range(OPEN + 1, CLOSE)}
    Bu[d] = {m: (B[m]['buy'] if m in B else 0.0) for m in range(OPEN + 1, CLOSE)}
    Se[d] = {m: (B[m]['sell'] if m in B else 0.0) for m in range(OPEN + 1, CLOSE)}
    last = None; C[d] = {}
    for m in range(OPEN + 1, CLOSE):
        if m in B and B[m].get('c') is not None: last = B[m]['c']
        C[d][m] = last
def w(a, E, W): return sum(a[m] for m in range(E - W, E))
def pearson(a, b):
    ma, mb = st.mean(a), st.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b)); den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den
Es = list(range(OPEN + 36, CLOSE - 4, 5))
def med(xs): xs = list(xs); return st.median(xs)
# (1) per-side x with the day-scale normal; corr of logs
lb, ls, lt = [], [], []
for d in FULL:
    ref = [o for o in FULL if o != d]
    for E in Es:
        cm = med(sum(V[o][m] for m in range(OPEN + 1, E)) for o in ref)
        sc = (sum(V[d][m] for m in range(OPEN + 1, E)) / cm) ** min(1.0, (E - OPEN) / 60.0)
        mb, ms, mt = (med(w(A[o], E, 5) for o in ref) * sc for A in (Bu, Se, V))
        xb, xs, xt = w(Bu[d], E, 5) / mb, w(Se[d], E, 5) / ms, w(V[d], E, 5) / mt
        if min(xb, xs, xt) > 0: lb.append(math.log(xb)); ls.append(math.log(xs)); lt.append(math.log(xt))
r_bs = pearson(lb, ls)
def partial_given(a, b, c):   # residual correlation of a,b after removing c (log total)
    def res(y, x):
        mx, my = st.mean(x), st.mean(y); beta = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / sum((xi - mx) ** 2 for xi in x)
        return [yi - my - beta * (xi - mx) for xi, yi in zip(x, y)]
    return pearson(res(a, c), res(b, c))
print('(1) n=%d 5-min windows. corr(log x_buy, log x_sell) = %.2f ; corr(log x_buy, log x_total) = %.2f ; corr(log x_sell, log x_total) = %.2f ; corr(buy,sell | total) = %.2f' % (
    len(lb), r_bs, pearson(lb, lt), pearson(ls, lt), partial_given(lb, ls, lt)))
print('    share of var(log x_buy) explained by log x_total: %.0f%%   (sell: %.0f%%)' % (100 * pearson(lb, lt) ** 2, 100 * pearson(ls, lt) ** 2))

# (2) tilt-window persistence: does tilt over the last W min keep its side over the NEXT non-overlapping W min?
print('(2) tilt persistence, sign of (b-s) kept over the next non-overlapping window; also |tilt|>=0.15 only')
for W in (3, 5, 10, 15, 30):
    same = tot = same2 = tot2 = 0
    for d in FULL:
        for E in range(OPEN + 2 * W + 1, CLOSE - W, W):
            b0, s0 = w(Bu[d], E, W), w(Se[d], E, W); b1, s1 = w(Bu[d], E + W, W), w(Se[d], E + W, W)
            if b0 + s0 < 20 or b1 + s1 < 20: continue
            t0, t1 = (b0 - s0) / (b0 + s0), (b1 - s1) / (b1 + s1)
            if t0 == 0 or t1 == 0: continue
            tot += 1; same += (t0 > 0) == (t1 > 0)
            if abs(t0) >= 0.15: tot2 += 1; same2 += (t0 > 0) == (t1 > 0)
    print('    W=%2dm: sign kept %.0f%% (n=%d) | when |tilt|>=0.15: %.0f%% (n=%d)' % (W, 100 * same / tot, tot, 100 * same2 / max(tot2, 1), tot2))

# (3) speed ratio persistence: rel5/30 for total vs buy vs sell: same side of 1.0 five minutes later
def relp(A):
    same = tot = 0
    for d in FULL:
        for E in range(OPEN + 36, CLOSE - 5, 1):
            r0 = (w(A[d], E, 5) / 5) / max(w(A[d], E, 30) / 30, 1e-9); r1 = (w(A[d], E + 5, 5) / 5) / max(w(A[d], E + 5, 30) / 30, 1e-9)
            if w(A[d], E, 30) < 30 or w(A[d], E + 5, 30) < 30: continue
            tot += 1; same += (r0 > 1) == (r1 > 1)
    return 100 * same / tot, tot
print('(3) 5m/30m ratio: same side of 1.0 five minutes later:  total %.0f%% (n=%d) | buy %.0f%% | sell %.0f%%' % (relp(V) + relp(Bu)[:1] + relp(Se)[:1])[:1 + 1 + 1 + 1] if False else '')
tv, n = relp(V); bv, _ = relp(Bu); sv, _ = relp(Se)
print('(3) 5m/30m ratio, same side of 1.0 five minutes later: total %.0f%% (n=%d) | buy %.0f%% | sell %.0f%%' % (tv, n, bv, sv))

# (4) bursts vs price: C-normalised total >= pooled p90 5-min windows (non-overlapping ends)
X = []
for d in FULL:
    ref = [o for o in FULL if o != d]
    for E in Es:
        cm = med(sum(V[o][m] for m in range(OPEN + 1, E)) for o in ref)
        sc = (sum(V[d][m] for m in range(OPEN + 1, E)) / cm) ** min(1.0, (E - OPEN) / 60.0)
        x = w(V[d], E, 5) / (med(w(V[o], E, 5) for o in ref) * sc)
        X.append((x, d, E))
xs = sorted(v[0] for v in X); p90 = xs[int(0.9 * (len(xs) - 1))]
bursts = [v for v in X if v[0] >= p90]
agree = against = flat = 0
for x, d, E in bursts:
    dl = w(Bu[d], E, 5) - w(Se[d], E, 5)
    c1, c0 = C[d][E - 1], C[d][E - 6]
    if c1 is None or c0 is None or abs(c1 - c0) < 4 or abs(dl) < 0.1 * w(V[d], E, 5): flat += 1; continue
    if (dl > 0) == (c1 > c0): agree += 1
    else: against += 1
print('(4) bursts (x>=p90=%.2f): n=%d. delta and price move the SAME way %d, OPPOSITE ways (effort without result) %d, one of them under the dead-band %d' % (p90, len(bursts), agree, against, flat))

# (5) 19 Oct 14:30 numbers
d = '2026-10-19'; E = 14 * 60 + 30
def tilt(W): b, s = w(Bu[d], E, W), w(Se[d], E, W); return b, s, (b - s) / (b + s)
print('(5) 19 Oct 14:30 (UX):')
for W in (5, 15, 30, 60, 75):
    b, s, t = tilt(W); print('    %2dm buy %5d sell %5d tilt %+.0f%%  rate %.0f/min' % (W, b, s, 100 * t, (b + s) / W))
b, s = w(Bu[d], E, 75), w(Se[d], E, 75)
print('    since 13:15 (leg): buy %d sell %d delta %+d  px %s -> %s' % (b, s, b - s, C[d][13 * 60 + 14], C[d][E - 1]))
print('    day so far (09:16-14:30): vol %d  buy %d sell %d  | median same-clock vol of other days %d' % (
    sum(V[d][m] for m in range(OPEN + 1, E)), sum(Bu[d][m] for m in range(OPEN + 1, E)), sum(Se[d][m] for m in range(OPEN + 1, E)),
    med(sum(V[o][m] for m in range(OPEN + 1, E)) for o in FULL if o != d)))
# last 1-min bars 14:15..14:30
print('    1-min 14:19..14:29: ' + ' '.join('%02d:%02d b%d s%d c%s' % (m // 60, m % 60, Bu[d][m], Se[d][m], C[d][m]) for m in range(14 * 60 + 19, 14 * 60 + 30)))
raw_b = {mint(b['t']): b for b in raw[d]['1m']}
print('    fut OI at 13:14 %s, 14:14 %s, 14:29 %s' % (raw_b.get(13 * 60 + 14, {}).get('oi'), raw_b.get(14 * 60 + 14, {}).get('oi'), raw_b.get(14 * 60 + 29, {}).get('oi')))
