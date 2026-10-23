"""FS4 - thresholds for all three indices on Upstox bars; NIFTY GoCharting vs Upstox agreement. Descriptive. SEEN."""
import numpy as np
from scipy.stats import spearmanr
from fs_lib import *

def table(nm, ref, unit=''):
    P = ref.POOL; n = sum(len(v) for v in ref.days.values())
    vols = [b['v'] for v in ref.days.values() for b in v]
    print('%s: %d days, %d bars; bar volume median %.0f lots (p10 %.0f, p90 %.0f)%s' % (nm, len(ref.days), n, np.median(vols), *np.quantile(vols, [.1, .9]), unit))
    for k, lab in (('d', '|5-min delta| lots'), ('dv', '|delta/vol|'), ('flip', '|flip swing| lots'), ('slope', '|CVD slope| lots/min'), ('acc', '|slope change| lots/min'), ('rv', 'RVOL'), ('vacc', 'vol acceleration')):
        print('   %-26s median %8.2f  p70 %8.2f  p90 %8.2f  (n %d)' % (lab, q(P[k], .5), q(P[k], .7), q(P[k], .9), len(P[k])))
    return vols

U = {}
for idx in ('NIFTY', 'BANKNIFTY', 'SENSEX'):
    days = ux_days(idx); U[idx] = Ref(days)
    print()
    vols = table('Upstox %s' % idx, U[idx])
    v = np.array(vols); ad = np.array([abs(b['d']) for d in days.values() for b in d]); ok = ad > 0
    beta = np.polyfit(np.log(v[ok]), np.log(ad[ok]), 1)[0]
    dv = ad / v
    print('   thin bars: volume <= 5 lots %d, <= 10 lots %d, <= 20 lots %d of %d; |d/v| exactly 1.0 in %d bars; exactly 0 in %d' % ((v <= 5).sum(), (v <= 10).sum(), (v <= 20).sum(), len(v), (dv >= 0.999).sum(), (dv == 0).sum()))
    print('   log|d| on log v slope beta = %.2f ; spearman(|d/v|, v) = %.2f' % (beta, spearmanr(dv, v)[0]))
    lag1 = []
    for dd, bars in days.items():
        for i in range(1, len(bars)):
            if bars[i]['s'] - bars[i - 1]['s'] == 300: lag1.append((bars[i]['d'], bars[i - 1]['d']))
    a, b = zip(*lag1); print('   lag-1 pearson of 5-min delta %.3f (pairs %d)' % (np.corrcoef(a, b)[0, 1], len(lag1)))
    rows = label_all(U[idx]); c = collections.Counter(r['st'] for r in rows)
    print('   states (LODO, concrete rules): PUSH %d CLIMAX_a %d CLIMAX_b %d PATLA %d NOISE %d NONE %d of %d' % (c['PUSH'], c['CLIMAX_a'], c['CLIMAX_b'], c['PATLA'], c['NOISE'], c['NONE'], len(rows)))
    # day-level share of RVOL>=p70
    sh = []
    for dd in days:
        F = U[idx].ALLF[dd]; sh.append(sum(1 for r in F if r['rv'] is not None and r['rv'] >= q(U[idx].POOL['rv'], .7)) / len(F))
    print('   per-day share RVOL>=p70: min %d%% max %d%%  (neutral 30%%)' % (round(100 * min(sh)), round(100 * max(sh))))

# ---------------------------------------------------------------- GC vs Upstox on NIFTY
print('\n=== NIFTY: GoCharting vs Upstox, same bars, same price source (GC OHLC), thresholds from each source\'s own history on the SAME reference days ===')
gc = gc_days(); ux = ux_days('NIFTY')
common = sorted(set(gc) & set(ux))
print('days in both:', len(common), common)
GCb, UXb = {}, {}
for dd in common:
    gm = {b['t']: b for b in gc[dd]}; um = {b['t']: b for b in ux[dd]}
    ts = sorted(set(gm) & set(um))
    GCb[dd] = [dict(gm[t]) for t in ts]
    UXb[dd] = [dict(um[t], o=gm[t]['o'], h=gm[t]['h'], l=gm[t]['l'], c=gm[t]['c']) for t in ts]
nb = sum(len(v) for v in GCb.values()); print('matched bars:', nb)
Rg, Ru = Ref(GCb), Ref(UXb)
g = [dict(r, day=dd) for dd in common for r in Rg.F[dd]]
u = [dict(r, day=dd) for dd in common for r in Ru.F[dd]]
dg = np.array([r['d'] for r in g]); du = np.array([r['d'] for r in u]); vg = np.array([r['v'] for r in g]); vu = np.array([r['v'] for r in u])
print('bar delta: pearson %.2f, sign agree %d of %d (zero-delta bars excluded %d); volume: pearson %.3f, median ratio ux/gc %.3f' % (
    np.corrcoef(dg, du)[0, 1], ((dg * du) > 0).sum(), ((dg * du) != 0).sum(), ((dg * du) == 0).sum(), np.corrcoef(vg, vu)[0, 1], np.median(vu / vg)))
print('median per-day (ux - gc) delta: %.0f lots; per-day delta correlation on 5-min bars, min/median/max over days: ' % np.median([sum(r['d'] for r in Ru.F[dd]) - sum(r['d'] for r in Rg.F[dd]) for dd in common]), end='')
cs = [np.corrcoef([r['d'] for r in Rg.F[dd]], [r['d'] for r in Ru.F[dd]])[0, 1] for dd in common]; print('%.2f / %.2f / %.2f' % (min(cs), np.median(cs), max(cs)))
for flag in (True, False):
    ix = [i for i, r in enumerate(g) if bool(r['ft']) == flag]
    print('  GC rows with fromTicks=%s: %d bars, delta sign agreement with Upstox %d of %d, pearson %.2f' % (flag, len(ix), sum(1 for i in ix if dg[i] * du[i] > 0), sum(1 for i in ix if dg[i] * du[i] != 0), np.corrcoef(dg[ix], du[ix])[0, 1]))
print('\nsingle-metric flags (GC rank vs Upstox rank, each against its own LODO threshold):')
print('   metric        both   GC only   Ux only   neither')
for k, p, nm in (('d', 'p90', '|delta|>=p90'), ('d', 'p70', '|delta|>=p70'), ('dv', 'p90', '|d/v|>=p90'), ('slope', 'p90', 'slope>=p90'), ('acc', 'p90', 'acc>=p90'), ('rv', 'p70', 'RVOL>=p70'), ('rv', 'p90', 'RVOL>=p90'), ('vacc', 'p90', 'vacc>=p90')):
    c = collections.Counter()
    from fs_lib import _val
    for a, b in zip(g, u):
        if a[k] is None or b[k] is None: continue
        fa = _val(k, a[k]) >= Rg.TH[a['day']][k][p]; fb = _val(k, b[k]) >= Ru.TH[b['day']][k][p]
        c[(fa, fb)] += 1
    print('   %-13s %4d %8d %9d %9d' % (nm, c[(True, True)], c[(True, False)], c[(False, True)], c[(False, False)]))
# spec's own rule: delta counts only if both >= p70 with the same sign
nA = sum(1 for a, b in zip(g, u) if abs(a['d']) >= Rg.TH[a['day']]['d']['p90'])
nB = sum(1 for a, b in zip(g, u) if abs(a['d']) >= Rg.TH[a['day']]['d']['p90'] and abs(b['d']) >= Ru.TH[b['day']]['d']['p70'] and a['d'] * b['d'] > 0)
nC = sum(1 for a, b in zip(g, u) if abs(b['d']) >= Ru.TH[b['day']]['d']['p90'])
nD = sum(1 for a, b in zip(g, u) if abs(b['d']) >= Ru.TH[b['day']]['d']['p90'] and abs(a['d']) >= Rg.TH[a['day']]['d']['p70'] and a['d'] * b['d'] > 0)
print('spec rule (both >= p70, same sign): GC |d|>=p90 bars %d, of which Upstox >= p70 same sign %d; Upstox |d|>=p90 bars %d, of which GC >= p70 same sign %d' % (nA, nB, nC, nD))

def st4(r, th):
    s = state(r, th)[0]
    return 'CLIMAX' if s.startswith('CLIMAX') else s
SG = [st4(a, Rg.TH[a['day']]) for a in g]; SU = [st4(b, Ru.TH[b['day']]) for b in u]
labs = ['PUSH', 'CLIMAX', 'PATLA', 'NOISE', 'NONE']
M = collections.Counter(zip(SG, SU))
print('\nstate confusion, rows = GC, columns = Upstox (matched bars %d)' % len(g))
print('  %-8s' % '' + ' '.join('%7s' % l for l in labs) + '   GC total')
for a in labs: print('  %-8s' % a + ' '.join('%7d' % M[(a, b)] for b in labs) + '   %d' % sum(M[(a, b)] for b in labs))
print('  Upstox total ' + ' '.join('%d' % sum(M[(a, b)] for a in labs) for b in labs))
print('  same state in %d of %d bars; same state excluding bars where both say NONE or NOISE: %d of %d' % (sum(M[(a, a)] for a in labs), len(g), sum(M[(a, a)] for a in ('PUSH', 'CLIMAX', 'PATLA')), sum(v for (a, b), v in M.items() if a in ('PUSH', 'CLIMAX', 'PATLA') or b in ('PUSH', 'CLIMAX', 'PATLA'))))
# direction agreement for PUSH
pp = [(a, b) for a, b, sa, sb in zip(g, u, SG, SU) if sa == 'PUSH' and sb == 'PUSH']
print('  both PUSH %d; same direction in %d' % (len(pp), sum(1 for a, b in pp if a['d'] * b['d'] > 0)))
# agreement when the flagged-state is any of the four 'active' states
act = lambda s: s in ('PUSH', 'CLIMAX', 'PATLA')
print('  bars where GC is in an active state (PUSH/CLIMAX/PATLA): %d; Upstox in the same state %d, in another active state %d, NOISE/NONE %d' % (
    sum(act(s) for s in SG), sum(1 for a, b in zip(SG, SU) if act(a) and a == b), sum(1 for a, b in zip(SG, SU) if act(a) and act(b) and a != b), sum(1 for a, b in zip(SG, SU) if act(a) and not act(b))))
# threshold comparison on matched days
print('\nthreshold comparison on the same %d reference days (in-sample pooled): GC vs Upstox' % len(common))
for k, lab in (('d', '|delta|'), ('dv', '|d/v|'), ('slope', '|slope|'), ('acc', '|acc|'), ('rv', 'RVOL')):
    print('   %-9s GC median %7.2f p70 %7.2f p90 %7.2f | Ux median %7.2f p70 %7.2f p90 %7.2f' % (lab, q(Rg.POOL[k], .5), q(Rg.POOL[k], .7), q(Rg.POOL[k], .9), q(Ru.POOL[k], .5), q(Ru.POOL[k], .7), q(Ru.POOL[k], .9)))
