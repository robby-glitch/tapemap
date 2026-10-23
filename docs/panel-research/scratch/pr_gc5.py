"""GoCharting 5-min buy / sell rate (lots/min) by 30-min slot vs Upstox's on the same days (descriptive). python -B pr_gc5.py"""
import json, glob, os
import numpy as np
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/data/tape/'
def bars(p):
    by = {}
    for l in open(p, encoding='utf-8'):
        try: r = json.loads(l)
        except ValueError: continue
        if isinstance(r.get('t'), (int, float)): by[int(r['t'])] = r
    return by
out = {}
days = []
for p in sorted(glob.glob(D + 'tape_NIFTY_2026-*.jsonl')):
    d = os.path.basename(p)[11:21]
    g = bars(p)
    if len(g) < 60: continue
    days.append(d)
    u = bars(D + f'ux_NIFTY_{d}.jsonl') if os.path.exists(D + f'ux_NIFTY_{d}.jsonl') else {}
    for t, b in g.items():
        s = (t // 1000 + 19800) % 86400
        if not 33600 <= s < 55800 or b.get('buy') is None: continue
        sl = (s // 60 - 555) // 30
        out.setdefault(('gc', 'buy', sl), []).append(b['buy'] / 5); out.setdefault(('gc', 'sell', sl), []).append(b['sell'] / 5)
        x = u.get(t)
        if x and x.get('buy') is not None:
            out.setdefault(('ux', 'buy', sl), []).append(x['buy'] / 5); out.setdefault(('ux', 'sell', sl), []).append(x['sell'] / 5)
print('GC days with >= 60 bars:', len(days), days)
print('slot   GC buy p10/50/90 | UX buy (same days) | GC sell | UX sell   (lots/min, 5-min bars)')
for sl in range(13):
    f = lambda k: [round(float(np.percentile(out.get(k, [np.nan]), q)), 1) for q in (10, 50, 90)]
    print(f'{(555 + 30 * sl) // 60:02d}:{(555 + 30 * sl) % 60:02d}  {f(("gc","buy",sl))} | {f(("ux","buy",sl))} | {f(("gc","sell",sl))} | {f(("ux","sell",sl))}')
