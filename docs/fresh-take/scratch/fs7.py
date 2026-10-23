"""FS7 - threshold uncertainty (day-block bootstrap), RVOL slot-median reliability, delta-range coupling. GC NIFTY, 17 days. Descriptive. SEEN."""
import numpy as np
from scipy.stats import spearmanr
from fs_lib import *
days = gc_days(); ref = Ref(days); ALL = ref.ALLF; dl = list(days)
rng = np.random.default_rng(5)
print('=== day-block bootstrap (1,000 resamples of the 17 days) 5-95%% interval of the pooled thresholds')
vals = {k: {dd: np.array([_val(k, r[k]) for r in ALL[dd] if r[k] is not None]) for dd in dl} for k in KEYS} if False else None
from fs_lib import _val
vals = {k: {dd: np.array([_val(k, r[k]) for r in ALL[dd] if r[k] is not None], float) for dd in dl} for k in KEYS}
for k, nm in (('d', '|delta|'), ('dv', '|d/v|'), ('flip', '|flip|'), ('slope', '|slope|'), ('acc', '|acc|'), ('rv', 'RVOL'), ('vacc', 'vacc')):
    out = {p: [] for p in (.5, .7, .9)}
    for b in range(1000):
        pick = rng.integers(0, len(dl), len(dl)); a = np.concatenate([vals[k][dl[i]] for i in pick])
        for p in out: out[p].append(np.quantile(a, p))
    full = np.concatenate([vals[k][dd] for dd in dl])
    print('  %-8s median %7.2f [%7.2f - %7.2f]  p70 %7.2f [%7.2f - %7.2f]  p90 %7.2f [%7.2f - %7.2f]' % (nm, np.quantile(full, .5), *np.quantile(out[.5], [.05, .95]), np.quantile(full, .7), *np.quantile(out[.7], [.05, .95]), np.quantile(full, .9), *np.quantile(out[.9], [.05, .95])))

print('\n=== RVOL reference: slot median of the other days - how stable?  (25 slots of 15 min; bootstrap over reference days, 300 resamples)')
slotv = collections.defaultdict(lambda: collections.defaultdict(list))
for dd in dl:
    for b in days[dd]: slotv[b['s'] // 900][dd].append(b['v'])
rel = []
for sl, dd_ in slotv.items():
    dd_l = list(dd_)
    full = med([x for d in dd_l for x in dd_[d]])
    bs = []
    for b in range(300):
        pick = rng.integers(0, len(dd_l), len(dd_l)); bs.append(med([x for i in pick for x in dd_[dd_l[i]]]))
    rel.append((np.quantile(bs, .95) - np.quantile(bs, .05)) / 2 / full)
print('  slots %d; half-width of the 90%% interval of the slot median, relative to the median: median %.2f, max %.2f' % (len(rel), np.median(rel), max(rel)))
# leaving a day out: spread of the same-slot median across the 17 leave-one-out versions
sp = []
for sl, dd_ in slotv.items():
    dd_l = list(dd_); meds = [med([x for d in dd_l if d != o for x in dd_[d]]) for o in dd_l]
    sp.append((max(meds) - min(meds)) / med(meds))
print('  leave-one-day-out range of the slot median / its median: median %.2f, max %.2f' % (np.median(sp), max(sp)))

print('\n=== delta-price coupling (what "result" has to be scaled by)')
R = [r for dd in dl for r in ref.F[dd] if r['res'] is not None]
sd = np.array([r['d'] for r in R]); mv = np.array([(r['c'] - r['o']) for r in R])
print('  spearman(delta, bar move c-o) = %.2f over %d bars; spearman(|delta/vol|, |move|/slot-range) = %.2f' % (spearmanr(sd, mv)[0], len(R), spearmanr([abs(r['dv']) for r in R], [abs(r['res']) for r in R])[0]))
for nm, lo_, hi_ in (('|d/v| < p30', 0, np.quantile([abs(r['dv']) for r in R], .3)), ('|d/v| p30-p70', np.quantile([abs(r['dv']) for r in R], .3), np.quantile([abs(r['dv']) for r in R], .7)), ('|d/v| > p70', np.quantile([abs(r['dv']) for r in R], .7), 9)):
    sub = [r['res'] for r in R if lo_ <= abs(r['dv']) < hi_]
    print('  %-14s n %3d  price result R (signed with delta): p25 %+.2f median %+.2f p75 %+.2f ; R<0 in %d' % (nm, len(sub), *np.quantile(sub, [.25, .5, .75]), sum(x < 0 for x in sub)))
dmed_d = [med([abs(r['dv']) for r in ALL[dd]]) for dd in dl]; dmed_rg = [med([b['h'] - b['l'] for b in days[dd]]) for dd in dl]; dmed_v = [med([b['v'] for b in days[dd]]) for dd in dl]; dmed_ad = [med([abs(b['d']) for b in days[dd]]) for dd in dl]
print('  across the 17 days: spearman(day median |d|, day median volume) %.2f ; (day median |d/v|, day median bar range) %.2f ; (day median |d|, day median range) %.2f' % (spearmanr(dmed_ad, dmed_v)[0], spearmanr(dmed_d, dmed_rg)[0], spearmanr(dmed_ad, dmed_rg)[0]))
print('  day median bar range (pts): min %.0f max %.0f ; day median |delta|: min %.0f max %.0f ; day median bar volume: min %.0f max %.0f' % (min(dmed_rg), max(dmed_rg), min(dmed_ad), max(dmed_ad), min(dmed_v), max(dmed_v)))
