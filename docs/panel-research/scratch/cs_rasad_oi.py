"""19 Oct leg (down since 13:15): when did OI last feed it? Feeders in the leg's direction = CE build > 0 (call writing) or PE build < 0 (put unwinding),
ATM+-2 fixed at E, 15-min, tempo-free rank vs prior days (pooled, window ends E-15..E+15 step 5). Also futures OI 15-min change and its rank (|dOI| vs prior days, same ends, UX 1-min oi)."""
import json, statistics as st
src = open('cs_oi_norm.py', encoding='utf-8').read().split("Es = list(range(OPEN + 45")[0]
exec(src)
today = '2026-10-19'
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
def val(d, E, leg):
    M = Ms[d]; a = M.get(E - 1)
    if not a: return None
    atm = round(a[0] / STEP) * STEP
    return build(M, E, 15, leg, atm)
tempo = {}
def tmp(d, E):
    if (d, E) not in tempo:
        cg = {o: cumgross(Ms[o], E) for o in days if Ms[o].get(E - 1)}
        cg = {o: v for o, v in cg.items() if v}
        oth = [cg[o] for o in cg if o != d]
        tempo[(d, E)] = (cg[d] / st.median(oth)) if d in cg and len(oth) >= 8 else None
    return tempo[(d, E)]
def rank(E, leg, sign):
    t = tmp(today, E); v = val(today, E, leg)
    if t is None or v is None or v * sign <= 0: return None
    x = abs(v) / t
    ref = []
    for e in range(E - 15, E + 16, 5):
        for d in days:
            if d == today: continue
            vv, tt = val(d, e, leg), tmp(d, e)
            if vv is not None and tt and vv * sign > 0: ref.append(abs(vv) / tt)
    return 100 * sum(1 for r in ref if r <= x) / len(ref) if len(ref) > 20 else None
print('E      CE build  rank(+)   PE build  rank(-)')
last = {'CE': None, 'PE': None}
for E in range(13 * 60 + 30, 14 * 60 + 31, 5):
    c, p = val(today, E, 0), val(today, E, 1)
    rc, rp = rank(E, 0, +1), rank(E, 1, -1)
    print('%02d:%02d %8.1f %8s %9.1f %8s' % (E // 60, E % 60, c or 0, ('p%.0f' % rc) if rc is not None else '--', p or 0, ('p%.0f' % rp) if rp is not None else '--'))
    if rc is not None and rc >= 80: last['CE'] = E
    if rp is not None and rp >= 80: last['PE'] = E
f = lambda E: ('%02d:%02d' % (E // 60, E % 60)) if E else 'never'
print('last time >= p80 in leg direction: call writing %s, put unwinding %s' % (f(last['CE']), f(last['PE'])))
# futures OI: UX 1-min oi, 15-min change; rank of |change| vs prior days at the same ends (pool all kinds, no tempo)
raw = json.load(open('C:/Users/kaam/Desktop/operator mode/tapemap/docs/panel-research/scratch/pr_1m_NIFTY.json', encoding='utf-8'))
def mint2(ms): return (int(ms) // 60000 + 330) % 1440
FULL = ['2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30', '2026-10-01', '2026-10-05', '2026-10-06', '2026-10-08', '2026-10-19']
OIm = {d: {mint2(b['t']): b.get('oi') for b in raw[d]['1m']} for d in FULL}
def doi(d, E):
    a, b = OIm[d].get(E - 1), OIm[d].get(E - 16)
    return None if a is None or b is None else a - b
print('\nfut OI 15m change (units), today and rank of |change| vs prior days at the same end (pool E-15..E+15):')
lastf = None
for E in range(13 * 60 + 30, 14 * 60 + 31, 5):
    v = doi(today, E)
    if v is None: continue
    ref = [abs(doi(d, e)) for e in range(E - 15, E + 16, 5) for d in FULL if d != today and doi(d, e) is not None]
    r = 100 * sum(1 for x in ref if x <= abs(v)) / len(ref)
    print('%02d:%02d %8d  rank p%.0f  price-direction word: %s' % (E // 60, E % 60, v, r, 'naye short (OI up, px down)' if v > 0 else 'covering/long nikal (OI down)'))
    if r >= 80 and v > 0: lastf = E
print('last fut-OI feed (>= p80, OI up with price down):', f(lastf))
