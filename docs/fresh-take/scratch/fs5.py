"""FS5 - extras added AFTER seeing the fs2 table (flagged in the study): episodes (clustering), flip as its own row, next-bar failure, clock buckets, roll/expiry days. Descriptive. SEEN."""
import numpy as np
import of_lib
from fs_lib import *

days = gc_days(); ref = Ref(days); rows = label_all(ref)
TEST = [d for d in days if d >= '2026-09-22']
PB = {}
def pb(day):
    if day not in PB: PB[day] = of_lib.path(day)
    return PB[day]
def lab(day, s, w, shift=0):
    p = pb(day)
    return of_lib.outcome(p, s + 300 + shift * 300, w, 0.5, 3600) if p and w else None
def line(nm, c):
    n = sum(c.values())
    return '  %-46s n %3d  WITH %3d  AGAINST %3d  TIE %2d  NONE/END %3d' % (nm, n, c['WITH'], c['AGAINST'], c['TIE'], c['NONE'] + c['END'])

# ---- 1. episodes: PUSH / CLIMAX bars within 30 minutes of each other on a day are one episode
print('=== 1. clustering: bars -> episodes (bars of the same kind <= 30 min apart merge)')
for st in ('PUSH', 'CLIMAX_a', 'CLIMAX_b', 'PATLA'):
    eps = 0; n = 0; byday = collections.Counter()
    for dd in days:
        ss = sorted(r['s'] for r in rows if r['day'] == dd and r['st'] == st); n += len(ss)
        last = None
        for s in ss:
            if last is None or s - last > 1800: eps += 1; byday[dd] += 1
            last = s
    print('  %-9s bars %3d -> episodes %3d on %2d days (most on one day: %s)' % (st, n, eps, len(byday), byday.most_common(1)))

# ---- 2. flip as its own row (the headline metric of the ask; it appears in NO state rule)
print('\n=== 2. flip swing as its own row (LODO p90 of |swing|; direction = sign of the new bar delta; WITH = the new direction continues)')
flip = [r for r in rows if r['flip'] is not None and abs(r['flip']) >= ref.TH[r['day']]['flip']['p90'] and r['day'] in TEST]
c, cs = collections.Counter(), collections.Counter()
for r in flip:
    o = lab(r['day'], r['s'], r['sg']);
    if o: c[o[0]] += 1
    for sh in (-12, -6, 6, 12):
        o = lab(r['day'], r['s'], r['sg'], sh)
        if o: cs[o[0]] += 1
print(line('flip >= p90 (all)', c)); print(line('  same bars, direction kept, shifted +-30/60 min', cs))
fl2 = [r for r in flip if r['res'] is not None and r['res'] >= RES_MIN]
c = collections.Counter()
for r in fl2:
    o = lab(r['day'], r['s'], r['sg']);
    if o: c[o[0]] += 1
print(line('flip >= p90 and price moved with it (R>=0.25)', c))
fl3 = [r for r in flip if r['res'] is not None and r['res'] < RES_MIN]
c = collections.Counter()
for r in fl3:
    o = lab(r['day'], r['s'], r['sg']);
    if o: c[o[0]] += 1
print(line('flip >= p90 and price did not follow (R<0.25)', c))
print('  flip>=p90 bars: %d (of which in a PUSH/CLIMAX_a state %d)' % (len(flip), sum(1 for r in flip if r['st'] in ('PUSH', 'CLIMAX_a'))))

# ---- 3. next-bar failure (effort bar then the NEXT bar gives back / continues)
print('\n=== 3. effort bar (|d|>=p90 and RVOL>=p70, own price result ignored) split by the NEXT bar: continues (same-direction close-to-close) vs fails; outcome counted from the next bar close (+10 min)')
def nxt(r, F):
    j = r['i'] + 1
    return F[j] if j < len(F) and F[j]['s'] == r['s'] + 300 else None
def sel(allbars):
    out = []
    for r in allbars:
        if r['day'] not in TEST: continue
        F = ref.F[r['day']]; n1 = nxt(r, F)
        if n1 is None or n1['c'] is None or r['c'] is None or r['sg'] == 0: continue
        out.append((r, r['sg'] * (n1['c'] - r['c'])))
    return out
EFF = [r for r in rows if abs(r['d']) >= ref.TH[r['day']]['d']['p90'] and r['rv'] is not None and r['rv'] >= ref.TH[r['day']]['rv']['p70']]
for nm, pool in (('EFFORT bars', EFF), ('ALL bars', rows)):
    S = sel(pool)
    for part, f in (('next bar continues', lambda x: x > 0), ('next bar fails', lambda x: x <= 0)):
        c = collections.Counter()
        for r, x in S:
            if f(x):
                p = pb(r['day']);
                if not p: continue
                o = of_lib.outcome(p, r['s'] + 600, r['sg'], 0.5, 3600)
                if o: c[o[0]] += 1
        print(line('%s, %s' % (nm, part), c))

# ---- 4. clock buckets and roll / expiry days
print('\n=== 4. where the active states sit on the clock (17 days, counts of bars)')
buckets = [(33300, 35100, '09:15-09:44'), (35100, 37800, '09:45-10:29'), (37800, 46800, '10:30-12:59'), (46800, 50400, '13:00-13:59'), (50400, 54000, '14:00-14:59'), (54000, 55000, '15:00-15:15')]
print('  bucket        bars  PUSH CL_a CL_b PATLA')
for a, b, nm in buckets:
    rs = [r for r in rows if a <= r['s'] < b]; c = collections.Counter(r['st'] for r in rs)
    print('  %-12s %5d %5d %4d %4d %5d' % (nm, len(rs), c['PUSH'], c['CLIMAX_a'], c['CLIMAX_b'], c['PATLA']))
print('\n=== roll / expiry days (Upstox book: Sep contract to 29 Sep, Oct contract from 30 Sep; Sep-contract OI at close, from ux files)')
oi = {}
for dd in sorted(days):
    try:
        rs = [json.loads(l) for l in open(D + 'tape/ux_NIFTY_%s.jsonl' % dd, encoding='utf-8') if l.strip()]
        oi[dd] = rs[-1].get('oi')
    except OSError: oi[dd] = None
tag = {'2026-09-22': 'Tue weekly expiry', '2026-09-25': 'roll week (OI falling)', '2026-09-28': 'roll week (OI falling)', '2026-09-29': 'Tue: Sep futures expiry + weekly', '2026-09-30': 'first day on Oct futures', '2026-10-06': 'Tue weekly expiry', '2026-10-13': 'Tue weekly expiry (13 Oct short)'}
print('  day        wd  Ux close OI   bars  PUSH CL_a CL_b PATLA  |d|>=p90 bars  note')
for dd in sorted(days):
    rs = [r for r in rows if r['day'] == dd]; c = collections.Counter(r['st'] for r in rs)
    nb = sum(1 for r in rs if abs(r['d']) >= ref.TH[dd]['d']['p90'])
    print('  %s %s %12s %5d %5d %4d %4d %5d  %6d         %s' % (dd, wd(dd), '' if oi.get(dd) is None else '%.1fM' % (oi[dd] / 1e6), len(rs), c['PUSH'], c['CLIMAX_a'], c['CLIMAX_b'], c['PATLA'], nb, tag.get(dd, '')))
exp = ('2026-09-22', '2026-09-29', '2026-10-06'); roll = ('2026-09-25', '2026-09-28', '2026-09-29')
def agg(ds):
    rs = [r for r in rows if r['day'] in ds]; c = collections.Counter(r['st'] for r in rs)
    return len(rs), c['PUSH'] + c['CLIMAX_a'] + c['CLIMAX_b'] + c['PATLA'], sum(1 for r in rs if abs(r['d']) >= ref.TH[r['day']]['d']['p90'])
oth = [d for d in days if d not in exp and d not in roll]
print('  Tue expiry days (3): bars %d, active-state bars %d, |d|>=p90 bars %d ; roll-week days (3): bars %d, active %d, |d|>=p90 %d ; all other days (%d): bars %d, active %d, |d|>=p90 %d' % (*agg(exp), *agg(roll), len(oth), *agg(oth)))
print('  29 Sep after 14:55 (expiring Sep contract):', [(hm(r['s']), r['st'], round(r['d'])) for r in rows if r['day'] == '2026-09-29' and r['s'] >= 53700])
