"""OI normal: 15-min ATM+-2 side build (CE and PE pooled, |build|), 36 NIFTY chain days. Expiry day = first chain row's expiry == day.
Compare: A pooled all kinds raw | AK same kind | C pooled x day-scale (cum gross |15-min build| so far vs median of other days at the same clock). LOO. Descriptive."""
import json, gzip, glob, os, statistics as st, math
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/data/'
OPEN, CLOSE, STEP, LK = 555, 930, 50, 1e5
def jl(path, first=False):
    for p in (path, path + '.gz'):
        if os.path.exists(p):
            op = gzip.open if p.endswith('.gz') else open
            out = []
            with op(p, 'rt', encoding='utf-8') as f:
                for line in f:
                    try: out.append(json.loads(line))
                    except ValueError: pass
                    if first and out: return out
            return out
    return []
def mof(s): h, m = s.split(':')[:2]; return int(h) * 60 + int(m)
def oi(day):
    out = {}
    for r in jl(D + 'chain_backfill/backfill_NIFTY_%s.jsonl' % day):
        if r.get('spot') is not None and r.get('k'):
            out[mof(r['t'])] = (r['spot'], {int(float(k)): (v[0], v[1]) for k, v in r['k'].items()})
    for r in jl(D + 'chain/chain_NIFTY_%s.jsonl' % day):
        sec = r.get('sec')
        if sec is None or not r.get('strikes') or r.get('spot') is None or not OPEN <= sec // 60 < CLOSE: continue
        out[sec // 60] = (r['spot'], {s['k']: ((s.get('ce') or {}).get('oi_chg'), (s.get('pe') or {}).get('oi_chg')) for s in r['strikes']})
    return out
def build(M, E, W, leg, atm):
    a, b = M.get(E - 1), M.get(E - 1 - W)
    if not a or not b: return None
    t = 0.0
    for j in range(-2, 3):
        k = atm + j * STEP; x, y = a[1].get(k), b[1].get(k)
        if not x or not y or x[leg] is None or y[leg] is None: return None
        t += x[leg] - y[leg]
    return t / LK
days = sorted({os.path.basename(p).split('_')[-1][:10] for p in glob.glob(D + 'chain/chain_NIFTY_2026-*')})
EXP = set()
for d in days:
    r = jl(D + 'chain/chain_NIFTY_%s.jsonl' % d, first=True)
    if r and str(r[0].get('expiry', ''))[:10] == d: EXP.add(d)
print('chain days', len(days), 'expiry days (chain expiry == day):', sorted(x[5:] for x in EXP))
Es = list(range(OPEN + 45, CLOSE - 1, 15))
B = {}   # B[d][E] = (|ce|,|pe|) at fixed ATM(E) strikes
for d in days:
    M = oi(d)
    if len(M) < 200: continue
    B[d] = {}
    for E in Es:
        a = M.get(E - 1)
        if not a: continue
        atm = round(a[0] / STEP) * STEP
        ce, pe = build(M, E, 15, 0, atm), build(M, E, 15, 1, atm)
        if ce is None or pe is None: continue
        B[d][E] = abs(ce) + abs(pe)      # gross two-side activity
days = [d for d in days if d in B and len(B[d]) >= 15]
print('usable days', len(days), 'expiry among them', len([d for d in days if d in EXP]))
def cumg(d, E): return sum(v for e, v in B[d].items() if e <= E)
def med(xs): xs = list(xs); return st.median(xs) if xs else None
def pc(xs, p): xs = sorted(xs); k = (len(xs) - 1) * p / 100; f = int(k); c = min(f + 1, len(xs) - 1); return xs[f] + (xs[c] - xs[f]) * (k - f)
def spearman(a, b):
    def rk(x):
        s = sorted(range(len(x)), key=lambda i: x[i]); r = [0] * len(x)
        for i, j in enumerate(s): r[j] = i
        return r
    ra, rb = rk(a), rk(b); ma, mb = st.mean(ra), st.mean(rb)
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
def xval(d, E, mode):
    if E not in B[d]: return None
    ref = [o for o in days if o != d and E in B[o] and (mode != 'AK' or ((o in EXP) == (d in EXP)))]
    if mode == 'AK' and len(ref) < 5: return None
    if len(ref) < 5: return None
    m = med(B[o][E] for o in ref)
    if not m: return None
    if mode == 'C':
        cm = med(cumg(o, E) for o in ref)
        if not cm: return None
        m *= (cumg(d, E) / cm) ** min(1.0, (E - OPEN) / 90.0)
    return B[d][E] / m
tot_act = {d: sum(B[d].values()) for d in days}
print('mean gross OI activity per day (L): expiry %.0f  normal %.0f' % (st.mean(tot_act[d] for d in days if d in EXP), st.mean(tot_act[d] for d in days if d not in EXP)))
for mode, nm in (('A', 'A  pooled all kinds, raw'), ('AK', 'AK same-kind (draft)'), ('C', 'C  pooled x day-scale')):
    X = {d: {E: xval(d, E, mode) for E in Es} for d in days}
    pool = [v for d in days for v in X[d].values() if v is not None]
    p90 = pc(pool, 90)
    sh = {}
    for d in days:
        v = [x for x in X[d].values() if x is not None]
        sh[d] = sum(1 for x in v if x >= p90) / len(v) if len(v) >= 5 else None
    ds = [d for d in days if sh[d] is not None]
    cov_e = [len([x for x in X[d].values() if x is not None]) / len(Es) for d in days if d in EXP]
    cov_n = [len([x for x in X[d].values() if x is not None]) / len(Es) for d in days if d not in EXP]
    ex = [sh[d] for d in ds if d in EXP]; no = [sh[d] for d in ds if d not in EXP]
    print('%-26s coverage expiry %.0f%% normal %.0f%% | share>=p90: expiry %s normal %.1f%% | spearman(day share, day activity)=%.2f  (n=%d days, %d expiry)' % (
        nm, 100 * st.mean(cov_e) if cov_e else 0, 100 * st.mean(cov_n), ('%.1f%%' % (100 * st.mean(ex))) if ex else '--', 100 * st.mean(no),
        spearman([sh[d] for d in ds], [tot_act[d] for d in ds]), len(ds), len(ex)))
