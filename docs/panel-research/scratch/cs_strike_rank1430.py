"""19 Oct 14:30: tempo-free rank of each ATM+-2 strike's 15-min OI change against prior days (all kinds pooled, window ends 14:15..14:45 step 5
to widen the pool). x = |change| / day-tempo, tempo = cumulative gross |15-min ATM+-2 build| so far / median of other days at the same clock.
Reads cs_oi_norm.py's loaders. Descriptive."""
import statistics as st
src = open('cs_oi_norm.py', encoding='utf-8').read().split("Es = list(range(OPEN + 45")[0]
exec(src)
E0 = 14 * 60 + 30; ENDS = list(range(14 * 60 + 15, 14 * 60 + 46, 5)); today = '2026-10-19'
Ms = {d: oi(d) for d in days}
def cumgross(M, E):
    a = M.get(E - 1)
    if not a: return None
    atm = round(a[0] / STEP) * STEP; t = 0.0
    for e in range(OPEN + 16, E + 1, 15):
        for leg in (0, 1):
            v = build(M, e, 15, leg, atm)
            if v is not None: t += abs(v)
    return t
def strike_chg(M, E, leg, j):
    a = M.get(E - 1)
    if not a: return None
    b = M.get(E - 16)
    if not b: return None
    atm = round(a[0] / STEP) * STEP; k = atm + j * STEP
    x, y = a[1].get(k), b[1].get(k)
    if not x or not y or x[leg] is None or y[leg] is None: return None
    return (x[leg] - y[leg]) / LK
pool = {}
for E in ENDS:
    cg = {d: cumgross(Ms[d], E) for d in days if Ms[d].get(E - 1)}
    cg = {d: v for d, v in cg.items() if v}
    for d in cg:
        others = [cg[o] for o in cg if o != d]
        if len(others) < 8: continue
        tempo = cg[d] / st.median(others)
        for leg in (0, 1):
            for j in range(-2, 3):
                v = strike_chg(Ms[d], E, leg, j)
                if v is not None: pool.setdefault((leg, j), []).append((d, E, abs(v) / tempo, v))
print('tempo-free rank of 19 Oct 14:30 strike changes (pool: prior days x window ends 14:15-14:45)')
for leg, nm in ((0, 'CE'), (1, 'PE')):
    for j in range(-2, 3):
        t = [x for x in pool[(leg, j)] if x[0] == today and x[1] == E0]
        if not t: continue
        _, _, xt, v = t[0]
        ref = [x[2] for x in pool[(leg, j)] if x[0] != today]
        r = 100 * sum(1 for x in ref if x <= xt) / len(ref)
        a = Ms[today].get(E0 - 1); atm = round(a[0] / STEP) * STEP
        print('  %s %d (ATM%+d)  change %+6.1fL  rank p%.0f  (n=%d, %d days)' % (nm, atm + j * STEP, j, v, r, len(ref), len({x[0] for x in pool[(leg, j)]}) - 1))
