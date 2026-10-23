import json, statistics as st
src = open('cs_oi_norm.py', encoding='utf-8').read().split("Es = list(range(OPEN + 45")[0]
exec(src)
E0 = 14 * 60 + 30
def quarters(M, E, leg, atm):
    return [build(M, E - 15 * i, 15, leg, atm) for i in range(4)]
rows = {}
for d in days:
    M = oi(d)
    a = M.get(E0 - 1)
    if not a: continue
    atm = round(a[0] / STEP) * STEP
    for leg, nm in ((0, 'CE'), (1, 'PE')):
        q = quarters(M, E0, leg, atm)
        if any(v is None for v in q): continue
        rows[(d, nm)] = q
def cumgross(M, E):
    # gross two-side activity so far, 15-min steps at fixed ATM(E)
    a = M.get(E - 1); atm = round(a[0] / STEP) * STEP; t = 0.0
    for e in range(OPEN + 15 + 1, E + 1, 15):
        for leg in (0, 1):
            v = build(M, e, 15, leg, atm)
            if v is not None: t += abs(v)
    return t
cg = {}
Ms = {}
for d in {k[0] for k in rows}:
    Ms[d] = oi(d)
    cg[d] = cumgross(Ms[d], E0)
today = '2026-10-19'
for nm in ('CE', 'PE'):
    g = {d: sum(abs(v) for v in rows[(d, nm)]) for (d, n) in rows if n == nm}
    prior = [d for d in g if d != today]
    gt = g[today]
    raw_rank = 100 * sum(1 for d in prior if g[d] <= gt) / len(prior)
    tempo = cg[today] / st.median(cg[d] for d in prior)
    scaled = {d: g[d] / (cg[d] / st.median(cg[o] for o in prior)) for d in prior}  # remove each day's own tempo to compare level-free
    gt_adj = gt / tempo
    adj_rank = 100 * sum(1 for d in prior if scaled[d] <= gt_adj) / len(prior)
    q = rows[(today, nm)]
    print('%s hour gross %.0fL (quarters newest->oldest %s) | raw rank among %d prior days at 14:30: p%.0f | day tempo %.2f -> tempo-free rank p%.0f' % (
        nm, gt, ['%.0f' % v for v in q], len(prior), raw_rank, tempo, adj_rank))
    print('   S = |q0|/gross = %.2f ; same sign all four: %s' % (abs(q[0]) / gt, all(v > 0 for v in q) or all(v < 0 for v in q)))
