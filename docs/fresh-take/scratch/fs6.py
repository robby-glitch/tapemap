"""FS6 - sign-shuffle null for the state counts; SENSEX with empty bars kept and at 15 minutes. Descriptive. SEEN."""
import numpy as np
from fs_lib import *
from fs_lib import _rows
SHUF = '--shuffle' in sys.argv
days = gc_days(); ref = Ref(days)
real = collections.Counter(r['st'] for r in label_all(ref))
rng = random.Random(11)
res = collections.defaultdict(list)
for k in range(100 if SHUF else 0):
    sh = {dd: [dict(b, d=abs(b['d']) * rng.choice((-1, 1))) for b in bars] for dd, bars in days.items()}
    c = collections.Counter(r['st'] for r in label_all(Ref(sh)))
    for s_ in ('PUSH', 'CLIMAX_a', 'CLIMAX_b', 'PATLA', 'NOISE', 'NONE'): res[s_].append(c[s_])
print('=== sign-shuffle null (each bar keeps |delta|, volume, price; delta sign random; thresholds rebuilt; 100 shuffles)')
for s_ in (('PUSH', 'CLIMAX_a', 'CLIMAX_b', 'PATLA', 'NOISE', 'NONE') if SHUF else ()):
    print('  %-9s real %3d   shuffled mean %6.1f  (5-95%%: %3d - %3d)' % (s_, real[s_], np.mean(res[s_]), *np.quantile(res[s_], [.05, .95])))

print('\n=== SENSEX')
raw = {}
for p in sorted(glob.glob(D + 'tape/ux_SENSEX_2026-*.jsonl')):
    day = p[-16:-6]; rs = [r for r in _rows(p) if 33300 <= sec(r['t']) <= 54900]
    raw[day] = rs
print('  rows per day (09:15-15:15) / of which vol==0:', {d[5:]: (len(v), sum(1 for r in v if not r.get('vol'))) for d, v in raw.items() if len(v) > 60})
days0 = ux_days('SENSEX', minbars=70, keep0=True)
r0 = Ref(days0); P = r0.POOL
vols = np.array([b['v'] for v in days0.values() for b in v])
print('  empty bars kept: %d days, %d bars, volume median %.0f lots, zero-volume bars %d' % (len(days0), len(vols), np.median(vols), (vols == 0).sum()))
for k, lab in (('d', '|5-min delta|'), ('dv', '|delta/vol|'), ('slope', '|slope| lots/min'), ('acc', '|acc| lots/min'), ('rv', 'RVOL'), ('vacc', 'vol accel')):
    print('   %-16s median %7.2f p70 %7.2f p90 %7.2f' % (lab, q(P[k], .5), q(P[k], .7), q(P[k], .9)))
c = collections.Counter(r['st'] for r in label_all(r0)); print('  states 5-min:', dict(c))
# 15-min aggregation
def agg15(bars):
    out = []; cur = {}
    for b in bars:
        k = b['s'] // 900
        a = cur.setdefault(k, dict(t=b['t'], s=k * 900, v=0, d=0, o=b['o'], h=b['h'], l=b['l'], c=b['c'], ft=None, n=0))
        a['v'] += b['v']; a['d'] += b['d']; a['n'] += 1
        if b['h'] is not None: a['h'] = b['h'] if a['h'] is None else max(a['h'], b['h'])
        if b['l'] is not None: a['l'] = b['l'] if a['l'] is None else min(a['l'], b['l'])
        a['c'] = b['c'] if b['c'] is not None else a['c']
    return [cur[k] for k in sorted(cur)]
# SENSEX 15-min: the pipeline's slot arithmetic is 5-min; here just report the pooled distribution
d15 = {dd: agg15(b) for dd, b in days0.items()}
v15 = np.array([b['v'] for x in d15.values() for b in x]); a15 = np.array([abs(b['d']) for x in d15.values() for b in x]); dv15 = a15 / np.maximum(v15, 1)
print('  15-min bars: %d, volume median %.0f lots (p10 %.0f), <=10 lots in %d' % (len(v15), np.median(v15), np.quantile(v15, .1), (v15 <= 10).sum()))
print('   |delta| median %.1f p70 %.1f p90 %.1f ; |d/v| median %.2f p70 %.2f p90 %.2f ; |d/v| exactly 1.0 in %d bars' % (np.median(a15), np.quantile(a15, .7), np.quantile(a15, .9), np.median(dv15), np.quantile(dv15, .7), np.quantile(dv15, .9), (dv15 >= .999).sum()))
for idx in ('NIFTY', 'BANKNIFTY'):
    dd_ = ux_days(idx, minbars=70)
    x15 = {k: agg15(v) for k, v in dd_.items()}
    a_ = np.array([abs(b['d']) for x in x15.values() for b in x]); v_ = np.array([b['v'] for x in x15.values() for b in x])
    print('  (%s Upstox 15-min for scale: |delta| median %.0f p70 %.0f p90 %.0f ; volume median %.0f lots)' % (idx, np.median(a_), np.quantile(a_, .7), np.quantile(a_, .9), np.median(v_)))
