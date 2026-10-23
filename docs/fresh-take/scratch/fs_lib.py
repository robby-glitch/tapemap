"""FLOW-STATE-STUDY library. SEEN data only, descriptive. Run scripts with python -B (no bytecode written outside fresh-take).
Features replicate roc.py (the script behind the spec's thresholds) and add: price result R, slot-range reference, leave-one-day-out (LODO) thresholds
(for each target day the reference days' features are themselves built with a base that excludes BOTH the target and themselves)."""
import sys, json, glob, math, bisect, statistics, collections, datetime, random
sys.dont_write_bytecode = True
HERE = 'C:/Users/kaam/Desktop/operator mode/tapemap/docs/fresh-take/scratch'
if HERE not in sys.path: sys.path.insert(0, HERE)
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/data/'
def sec(t): return int(t / 1000 + 19800) % 86400
def hm(s): return '%02d:%02d' % (s // 3600, s % 3600 // 60)
def wd(day): return datetime.date.fromisoformat(day).strftime('%a')
def _rows(p):
    d = {}
    for x in open(p, encoding='utf-8'):
        if x.strip():
            r = json.loads(x); d[r['t']] = r
    return [d[k] for k in sorted(d)]

# ---------------------------------------------------------------- bar loaders (a bar = dict t,s,v,d,o,h,l,c,ft)
def _clean(bars, keep0=False):
    return [dict(t=b['t'], s=sec(b['t']), v=b['vol'], d=b['delta'], o=b.get('o'), h=b.get('h'), l=b.get('l'), c=b.get('c'), ft=b.get('fromTicks')) for b in bars if 33300 <= sec(b['t']) <= 54900 and (b.get('vol') or (keep0 and b.get('vol') is not None))]

def gc_days(minbars=40):
    import of_lib
    out = {}
    for p in sorted(glob.glob(D + 'tape/tape_NIFTY_2026-*.jsonl')):
        day = p[-16:-6]
        bs = _clean(of_lib.gc_bars(day))
        if len(bs) >= minbars: out[day] = bs
    return out

def gc_all():           # incl. the two short days (13, 16 Oct) for the marks study
    return gc_days(minbars=1)

def ux_days(idx, minbars=70, keep0=False):
    out = {}
    for p in sorted(glob.glob(D + 'tape/ux_%s_2026-*.jsonl' % idx)):
        day = p[-16:-6]
        bs = _clean(_rows(p), keep0)
        if len(bs) >= minbars: out[day] = bs
    return out

# ---------------------------------------------------------------- features
def med(a): return statistics.median(a)
def bases(days, skip):
    bv, br = collections.defaultdict(list), collections.defaultdict(list)
    for o, bars in days.items():
        if o in skip: continue
        for b in bars:
            bv[b['s'] // 900].append(b['v'])
            if b['h'] is not None and b['l'] is not None: br[b['s'] // 900].append(b['h'] - b['l'])
    return {k: med(v) for k, v in bv.items()}, {k: med(v) for k, v in br.items()}

def feats(bars, bv, br):
    out = []
    for i, b in enumerate(bars):
        s = b['s']; d = b['d']; v = b['v']
        mv = bv.get(s // 900); rv = v / mv if mv else None
        prev = bars[i - 1] if i and bars[i - 1]['s'] == s - 300 else None
        flip = (d - prev['d']) if prev and (d > 0) != (prev['d'] > 0) and d and prev['d'] else None
        w3 = [x for x in bars[max(0, i - 2):i + 1] if s - x['s'] <= 600]
        slope = sum(x['d'] for x in w3) / 15 if len(w3) == 3 else None
        w6 = [x for x in bars[max(0, i - 5):i - 2] if s - x['s'] <= 1500]
        slope0 = sum(x['d'] for x in w6) / 15 if len(w6) == 3 else None
        acc = slope - slope0 if slope is not None and slope0 is not None else None
        v3 = [x['v'] for x in bars[max(0, i - 3):i] if s - x['s'] <= 900]
        vacc = v / statistics.mean(v3) if len(v3) == 3 and statistics.mean(v3) else None
        rg = br.get(s // 900)
        res = None
        if b['o'] is not None and b['c'] is not None and rg:
            res = (1 if d > 0 else -1 if d < 0 else 0) * (b['c'] - b['o']) / rg      # signed: + = price moved with the delta
        p3 = bars[i - 3] if i >= 3 and bars[i - 3]['s'] == s - 900 else None
        ret15 = (b['c'] - p3['c']) if p3 and b['c'] is not None and p3['c'] is not None else None
        out.append(dict(b, rv=rv, flip=flip, slope=slope, slope0=slope0, acc=acc, vacc=vacc, dv=(d / v if v else 0.0), res=res, ret15=ret15, i=i))
    return out

KEYS = ('d', 'dv', 'flip', 'slope', 'acc', 'rv', 'vacc')
SIGNED = ('rv', 'vacc')
def _val(k, x): return x if k in SIGNED else abs(x)
def pops(featmap, days):
    P = {k: [] for k in KEYS}
    for dd in days:
        for r in featmap[dd]:
            for k in KEYS:
                if r[k] is not None: P[k].append(_val(k, r[k]))
    return {k: sorted(v) for k, v in P.items()}
q = lambda a, p: a[int(p * (len(a) - 1))]      # roc.py's quantile
def rank(P, k, x): return round(100 * bisect.bisect_left(P[k], _val(k, x)) / len(P[k])) if x is not None else None

class Ref:
    """Per-day LODO features + thresholds for one source."""
    def __init__(self, days):
        self.days = days; self.F = {}; self.TH = {}; self.P = {}
        for dday in days:
            bv, br = bases(days, {dday})
            self.F[dday] = feats(days[dday], bv, br)              # target day's own features (LODO base)
            refs = {}
            for r in days:
                if r == dday: continue
                bv2, br2 = bases(days, {dday, r}); refs[r] = feats(days[r], bv2, br2)
            P = pops(refs, list(refs))
            self.P[dday] = P
            self.TH[dday] = {k: dict(p50=q(P[k], .5), p70=q(P[k], .7), p90=q(P[k], .9)) for k in KEYS}
        # in-sample pooled (roc.py style) for reproduction of the spec table
        self.ALLF = {}
        for dd in days:
            bv, br = bases(days, {dd}); self.ALLF[dd] = feats(days[dd], bv, br)
        self.POOL = pops(self.ALLF, list(self.ALLF))

# ---------------------------------------------------------------- the FLOW STATE rules (spec §4, made concrete; every choice flagged in the study)
RES_MIN = 0.25       # "price moves with it" / "no result" cut in slot-typical bar ranges (choice fixed before counting; 0.0 and 0.5 reported as sensitivity)
def state(r, th, res_min=RES_MIN, need_sign=True):
    """returns (state, direction, all rules hit). PUSH > CLIMAX_a > CLIMAX_b > PATLA > NOISE > NONE (in-between)."""
    g = lambda k, p: th[k][p]
    d = r['d']; sg = 1 if d > 0 else -1 if d < 0 else 0
    big_d = abs(d) >= g('d', 'p90')
    sl, ac = r['slope'], r['acc']
    ok_sl = sl is not None and abs(sl) >= g('slope', 'p90') and (not need_sign or sl * sg > 0)
    ok_ac = ac is not None and abs(ac) >= g('acc', 'p90') and (not need_sign or ac * sg > 0)
    rv, va, res = r['rv'], r['vacc'], r['res']
    hit = []
    if res is not None and big_d and (ok_sl or ok_ac) and rv is not None and rv >= g('rv', 'p70') and res >= res_min: hit.append('PUSH')
    if res is not None and big_d and res < res_min: hit.append('CLIMAX_a')
    if abs(d) <= g('d', 'p70') and ((rv is not None and rv >= g('rv', 'p90')) or (va is not None and va >= g('vacc', 'p90'))): hit.append('CLIMAX_b')
    if abs(r['dv']) >= g('dv', 'p90') and rv is not None and rv < g('rv', 'p70'): hit.append('PATLA')
    if hit: return hit[0], sg, hit
    low = abs(d) <= g('d', 'p70') and abs(r['dv']) <= g('dv', 'p70') and (rv is None or rv <= g('rv', 'p70')) and (va is None or va <= g('vacc', 'p70')) \
        and (sl is None or abs(sl) <= g('slope', 'p70')) and (ac is None or abs(ac) <= g('acc', 'p70'))
    return ('NOISE' if low else 'NONE'), sg, hit

def label_all(ref, **kw):
    rows = []
    for dday, F in ref.F.items():
        th = ref.TH[dday]
        for r in F:
            st, sg, hit = state(r, th, **kw); rows.append(dict(r, day=dday, st=st, sg=sg, hit=hit))
    return rows

if __name__ == '__main__':
    days = gc_days(); ref = Ref(days)
    n = sum(len(v) for v in days.values())
    print(len(days), 'days', sorted(days)[0], sorted(days)[-1], n, 'bars')
    for k in KEYS:
        P = ref.POOL[k]; print('%-6s pooled(in-sample, roc.py) med %.2f p70 %.2f p90 %.2f n %d' % (k, q(P, .5), q(P, .7), q(P, .9), len(P)))
