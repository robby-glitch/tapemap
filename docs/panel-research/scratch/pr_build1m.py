"""Build 1-min and 5-min bars (o,h,l,c,vol,buy,sell,delta in lots) from Upstox book ticks via the repo's own Ladder (same side rule as the live ux bars).
Read-only on tapemap; cache -> fs_1m_<IDX>.json. Run with python -B."""
import sys, json, glob, gzip, math
sys.dont_write_bytecode = True
sys.path.insert(0, 'C:/Users/kaam/Desktop/operator mode/tapemap')
from ladder import Ladder
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/data/'
TICK = {'NIFTY': 10.0, 'BANKNIFTY': 20.0, 'SENSEX': 5.0}   # the live ux bars' own 'dump' tick (22 Sep used an inferred tick)
def op(p): return gzip.open(p, 'rt') if p.endswith('.gz') else open(p, encoding='utf-8')
def rows(idx, day):
    f = glob.glob(D + 'book/book_%s_%s.jsonl*' % (idx, day))
    out = []
    if f:
        for l in op(f[0]):
            try: out.append(json.loads(l))
            except Exception: pass
    return out
for idx in ('NIFTY', 'BANKNIFTY', 'SENSEX'):
    res = {}
    for p in sorted(glob.glob(D + 'book/book_%s_2026-*.jsonl*' % idx)):
        day = p.split('_')[-1][:10]
        R = rows(idx, day)
        if not R: continue
        g = 0
        for r in R:
            q = r.get('ltq')
            if q: g = math.gcd(g, int(q))
        out = []
        for iv, key in ((60, '1m'), (300, '5m')):
            L = Ladder(lot=g or None, tick=(None if day == '2026-09-22' else TICK[idx]), interval_s=iv, idx=idx, day=day)
            bars = []
            for r in R:
                b, _ = L.step(r)
                if b: bars.append(b)
            b = L.close_open()
            if b: bars.append(b)
            res.setdefault(day, {})[key] = [dict(t=x['t'], o=x['o'], h=x['h'], l=x['l'], c=x['c'], vol=x['vol'], buy=x['buy'], sell=x['sell'], unk=x['unknown'], delta=x['delta'], oi=x['oi'], partial=x['partial']) for x in bars]
        res[day]['lot'] = g
        print(idx, day, 'lot', g, 'rows', len(R), '1m', len(res[day]['1m']), '5m', len(res[day]['5m']), flush=True)
    json.dump(res, open('pr_1m_%s.json' % idx, 'w'))
