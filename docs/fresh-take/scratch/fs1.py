"""FS1 - statistical critique of the metrics (GC NIFTY, 17 days). Descriptive. SEEN."""
import numpy as np
from scipy.stats import spearmanr
from fs_lib import *
from fs_lib import _val

days = gc_days(); ref = Ref(days)
R = [dict(r, day=dd) for dd, F in ref.ALLF.items() for r in F]          # in-sample features as in roc.py
print('=== bars', len(R), 'days', len(days))

# ---- 1. serial structure of the bar delta (why slope / acceleration / flip are mostly one bar)
print('\n[1] serial correlation of the 5-min delta, within days (adjacent bars only)')
for lag in (1, 2, 3):
    a, b, a2, b2, same, n = [], [], [], [], 0, 0
    for dd in days:
        F = ref.ALLF[dd]
        for i in range(lag, len(F)):
            if F[i]['s'] - F[i - lag]['s'] == 300 * lag:
                a.append(F[i]['d']); b.append(F[i - lag]['d'])
                a2.append(F[i]['d'] / math.sqrt(F[i]['v'])); b2.append(F[i - lag]['d'] / math.sqrt(F[i - lag]['v']))
                n += 1; same += (F[i]['d'] > 0) == (F[i - lag]['d'] > 0)
    print('  lag %d: pairs %d  pearson(d) %.3f  pearson(d/sqrt v) %.3f  same-sign %d of %d' % (lag, n, np.corrcoef(a, b)[0, 1], np.corrcoef(a2, b2)[0, 1], same, n))
# pairs whose two deltas are both small are the usual 'flips'
fl = [r for r in R if r['flip'] is not None]
print('  flips (sign change vs previous bar): %d of %d bars with a previous bar' % (len(fl), sum(1 for r in R if r['i'] > 0)))
absd = np.array([abs(r['d']) for r in R])
p30 = np.quantile(absd, .3)
sm = sum(1 for r in R if r['flip'] is not None and abs(r['d']) <= p30)
print('  of the flips, current |delta| below the 30th pct (%.0f lots): %d' % (p30, sm))

# ---- 2. scaling: delta vs volume
print('\n[2] how |delta| scales with volume (is delta/volume the right scale-free measure?)')
v = np.array([r['v'] for r in R], float); ad = np.array([abs(r['d']) for r in R], float)
ok = ad > 0
beta = np.polyfit(np.log(v[ok]), np.log(ad[ok]), 1)[0]
print('  log|d| on log v slope beta = %.2f (0.5 = pure sampling noise; 1.0 = delta share is constant)' % beta)
print('  spearman(|d|, v) %.2f   spearman(|d|/v, v) %.2f   spearman(|d|/sqrt v, v) %.2f' % (spearmanr(ad, v)[0], spearmanr(ad / v, v)[0], spearmanr(ad / np.sqrt(v), v)[0]))
t = np.quantile(v, [1 / 3, 2 / 3])
print('  volume terciles cut at %.0f / %.0f lots; |delta/vol| p50 / p90 by tercile:' % tuple(t))
for nm, m in (('low', v <= t[0]), ('mid', (v > t[0]) & (v <= t[1])), ('high', v > t[1])):
    x = ad[m] / v[m]; print('    %-4s n %d  median %.2f  p90 %.2f   |d| median %.0f p90 %.0f' % (nm, m.sum(), np.median(x), np.quantile(x, .9), np.median(ad[m]), np.quantile(ad[m], .9)))
p90dv = np.quantile(ad / v, .9)
lo = (ad / v >= p90dv)
print('  bars with |d/v| >= pooled p90 (%.2f): %d; of them in the lowest volume tercile %d, mid %d, top %d' % (p90dv, lo.sum(), (lo & (v <= t[0])).sum(), (lo & (v > t[0]) & (v <= t[1])).sum(), (lo & (v > t[1])).sum()))
z = ad / np.sqrt(v); p90z = np.quantile(z, .9); lz = z >= p90z
print('  same for |d|/sqrt(v) >= its p90 (%.2f): %d; terciles low %d, mid %d, top %d' % (p90z, lz.sum(), (lz & (v <= t[0])).sum(), (lz & (v > t[0]) & (v <= t[1])).sum(), (lz & (v > t[1])).sum()))

# ---- 3. double counting
print('\n[3] overlap between delta, flip, slope, acceleration (pooled p90 of |.|, in-sample)')
P = ref.POOL
def hi(r, k, p=.9): return r[k] is not None and _val(k, r[k]) >= q(P[k], p)
D90 = [r for r in R if hi(r, 'd')]
print('  bars |delta| >= p90: %d' % len(D90))
for k in ('slope', 'acc', 'flip', 'dv'):
    have = [r for r in D90 if r[k] is not None]
    print('    of those with a %s defined (%d): %s >= p90 in %d' % (k, len(have), k, sum(hi(r, k) for r in have)))
print('    RVOL >= p70 in %d of %d; vacc >= p90 in %d of %d defined' % (sum(hi(r, 'rv', .7) for r in D90), len(D90), sum(hi(r, 'vacc') for r in D90 if r['vacc'] is not None), sum(1 for r in D90 if r['vacc'] is not None)))
for k in ('slope', 'acc', 'flip'):
    have = [r for r in R if r[k] is not None]
    print('  among all bars where %s is defined (%d): %s >= p90 in %d, of which |delta| >= p90 in %d' % (k, len(have), k, sum(hi(r, k) for r in have), sum(hi(r, k) and hi(r, 'd') for r in have)))
M = [r for r in R if None not in (r['flip'], r['slope'], r['acc'])]
cols = ['d', 'dv', 'flip', 'slope', 'acc', 'rv', 'vacc']
X = np.array([[_val(k, r[k]) for k in cols] for r in M], float)
rho = spearmanr(X).statistic
print('  spearman on the %d bars where all are defined (|.| for signed ones):' % len(M))
print('        ' + ' '.join('%6s' % c for c in cols))
for i, c in enumerate(cols): print('  %-6s' % c + ' '.join('%6.2f' % rho[i, j] for j in range(len(cols))))
# swing identity
sw = [(abs(r['flip']), abs(r['d'])) for r in fl]
print('  flip swing = |d_now| + |d_prev| exactly (sign change); corr(|flip|, |d_now|) = %.2f' % np.corrcoef(*zip(*sw))[0, 1])
# slope includes the bar itself
print('  slope = (d_i + d_i-1 + d_i-2)/15: the current bar is 1 of 3 terms; corr(slope, d) = %.2f; acc = slope - slope0: corr(acc, slope) = %.2f, corr(acc, slope0) = %.2f' % (
    np.corrcoef([r['slope'] for r in M], [r['d'] for r in M])[0, 1], np.corrcoef([r['acc'] for r in M], [r['slope'] for r in M])[0, 1], np.corrcoef([r['acc'] for r in M], [r['slope0'] for r in M])[0, 1]))

# ---- 4. sign-shuffle null: how much of slope / acc / flip tail is directional persistence?
print('\n[4] sign-shuffle null (keep every bar |delta| and time slot, give each bar a random sign; 300 shuffles) - p90 of |slope|, |acc|, |flip| real vs shuffled')
rng = random.Random(7)
def tails(sign_map):
    s_, a_, f_ = [], [], []
    for dd in days:
        bars = days[dd]
        sh = [dict(b, d=abs(b['d']) * sign_map(dd, i, b)) for i, b in enumerate(bars)]
        bv, br = bases(days, {dd})
        for r in feats(sh, bv, br):
            if r['slope'] is not None: s_.append(abs(r['slope']))
            if r['acc'] is not None: a_.append(abs(r['acc']))
            if r['flip'] is not None: f_.append(abs(r['flip']))
    return np.quantile(s_, .9), np.quantile(a_, .9), np.quantile(f_, .9), len(f_)
real = tails(lambda dd, i, b: 1 if b['d'] >= 0 else -1)
ss, aa, ff, nf = [], [], [], []
for k in range(300):
    t_ = tails(lambda dd, i, b: rng.choice((-1, 1)))
    ss.append(t_[0]); aa.append(t_[1]); ff.append(t_[2]); nf.append(t_[3])
print('  p90 |slope| real %.1f   shuffled mean %.1f (5-95%%: %.1f-%.1f)' % (real[0], np.mean(ss), *np.quantile(ss, [.05, .95])))
print('  p90 |acc|   real %.1f   shuffled mean %.1f (5-95%%: %.1f-%.1f)' % (real[1], np.mean(aa), *np.quantile(aa, [.05, .95])))
print('  p90 |flip|  real %.1f   shuffled mean %.1f (5-95%%: %.1f-%.1f); flips per sample real %d shuffled mean %.0f' % (real[2], np.mean(ff), *np.quantile(ff, [.05, .95]), real[3], np.mean(nf)))

# ---- 5. clock: where do the 'extreme' ranks live?
print('\n[5] share of bars flagged by pooled thresholds, by time of day (pooled ranks are not slot-normalised except RVOL)')
slots = [(33300, 35100, '09:15-09:44'), (35100, 37800, '09:45-10:29'), (37800, 41400, '10:30-11:29'), (41400, 46800, '11:30-12:59'), (46800, 50400, '13:00-13:59'), (50400, 55000, '14:00-15:15')]
def share(k, p, sl=None):
    out = []
    for a, b, nm in slots:
        rs = [r for r in R if a <= r['s'] < b and r[k] is not None]
        out.append((nm, len(rs), sum(hi(r, k, p) for r in rs)))
    return out
print('  slot          bars | ' + ' | '.join('%s' % k for k in ('|d|>=p90', 'slope>=p90', 'acc>=p90', 'flip>=p90', 'dv>=p90', 'rv>=p70', 'rv>=p90')))
cols5 = (('d', .9), ('slope', .9), ('acc', .9), ('flip', .9), ('dv', .9), ('rv', .7), ('rv', .9))
tabs = [share(k, p) for k, p in cols5]
for si, (a, b, nm) in enumerate(slots):
    n_bars = sum(1 for r in R if a <= r['s'] < b)
    print('  %-12s %5d | ' % (nm, n_bars) + ' | '.join('%3d/%-4d' % (t[si][2], t[si][1]) for t in tabs))
# candidate normalisations: tail uniformity
def tail_by_slot(vals, p=.9):
    thr = np.quantile(vals, p); out = []
    for a, b, nm in slots:
        ix = [i for i, r in enumerate(R) if a <= r['s'] < b]
        out.append((sum(vals[i] >= thr for i in ix), len(ix)))
    return out
cand = {}
cand['|d| raw'] = np.array([abs(r['d']) for r in R], float)
cand['|d|/v'] = np.array([abs(r['d']) / r['v'] for r in R])
cand['|d|/sqrt(v)'] = np.array([abs(r['d']) / math.sqrt(r['v']) for r in R])
# slot-median |d| from the other days
sm_ = collections.defaultdict(list)
for dd in days:
    for r in ref.ALLF[dd]: sm_[(dd, r['s'] // 900)].append(abs(r['d']))
oth = collections.defaultdict(list)
for (dd, sl), vs in sm_.items(): oth[sl].append((dd, vs))
def lodo_med(dd, sl): return med([x for d2, vs in oth[sl] if d2 != dd for x in vs])
cand['|d|/slot-median|d| (LODO)'] = np.array([abs(r['d']) / lodo_med(r['day'], r['s'] // 900) for r in R])
print('\n  tail uniformity: share of the top-10%% bars per slot under each scaling (expected 10%% in every slot; first slot = %d%% of bars)' % round(100 * 6 * len(days) / len(R)))
for nm, vals in cand.items():
    tb = tail_by_slot(vals)
    print('   %-28s ' % nm + ' '.join('%s %2d%%' % (slots[i][2][:5], round(100 * a / b)) for i, (a, b) in enumerate(tb)))

# ---- 6. day-level: RVOL against a median of other days
print('\n[6] day level: what share of each day\'s bars is RVOL >= p70 / delta >= p90 (a neutral reference gives 30% / 10%)')
print('  day        wd  bars  day vol  RVOL>=p70  |d|>=p90  |dv|>=p90  note')
for dd in days:
    F = ref.ALLF[dd]; tot = sum(r['v'] for r in F)
    a = sum(hi(r, 'rv', .7) for r in F); b = sum(hi(r, 'd') for r in F); c = sum(hi(r, 'dv') for r in F)
    note = {'2026-09-22': 'Tue weekly expiry', '2026-09-29': 'Tue expiry of Sep fut (roll)', '2026-09-30': 'first day on Oct fut', '2026-10-06': 'Tue weekly expiry', '2026-10-13': 'Tue weekly expiry'}.get(dd, '')
    print('  %s %s %4d %8.0f  %3d%%       %3d%%      %3d%%   %s' % (dd, wd(dd), len(F), tot, round(100 * a / len(F)), round(100 * b / len(F)), round(100 * c / len(F)), note))
dv_ = [sum(r['v'] for r in ref.ALLF[dd]) / len(ref.ALLF[dd]) for dd in days]
sh_ = [sum(hi(r, 'rv', .7) for r in ref.ALLF[dd]) / len(ref.ALLF[dd]) for dd in days]
print('  spearman(day mean bar volume, share RVOL>=p70) = %.2f over %d days; day volume range %.0f - %.0f lots per bar-mean' % (spearmanr(dv_, sh_)[0], len(days), min(dv_), max(dv_)))
# alternative adaptive normaliser: bar volume / median of the previous 12 bars of the same day
alt = []
for dd in days:
    F = ref.ALLF[dd]
    for i, r in enumerate(F):
        if i >= 12: alt.append((dd, r['v'] / med([x['v'] for x in F[i - 12:i]])))
altv = np.array([a for _, a in alt]); thr = np.quantile(altv, .7)
byd = collections.defaultdict(lambda: [0, 0])
for dd, a in alt: byd[dd][0] += a >= thr; byd[dd][1] += 1
sh2 = [byd[dd][0] / byd[dd][1] for dd in days]
print('  adaptive RVOL12 (bar volume / median of previous 12 bars, same day) >= its p70: per-day share min %d%% max %d%% (slot-median RVOL: min %d%% max %d%%)' % (
    round(100 * min(sh2)), round(100 * max(sh2)), round(100 * min(sh_)), round(100 * max(sh_))))

# ---- 7. GC row provenance
print('\n[7] GC rows by provenance (fromTicks flag) - same distribution?')
for flag in (True, False):
    rs = [r for r in R if bool(r['ft']) == flag]
    if rs:
        print('  fromTicks=%s: n %d  median |delta| %.0f  median |d/v| %.2f  median vol %.0f' % (flag, len(rs), np.median([abs(r['d']) for r in rs]), np.median([abs(r['dv']) for r in rs]), np.median([r['v'] for r in rs])))
