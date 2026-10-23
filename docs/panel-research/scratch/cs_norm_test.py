"""Critique test: which 'normal' keeps expiry / high-volume days from going blind or lighting up everything?
NIFTY, Upstox 1-min rebuilds (pr_1m_NIFTY.json), 12 full days. Leave-one-day-out (descriptive only; live use = prior days only).
Definitions of x = 5-min lots / normal:
  A  slot median over OTHER days, all kinds pooled
  AK slot median over OTHER days of the SAME kind (draft rule 2) -> blind when < 5 days
  C  slot median over other days  x  today's day-level scale (cum vol so far / median cum vol so far), shrunk early
  B  today's own trailing normal: median of the 5-min windows over the previous 60 min (no reference days at all)
"""
import json, statistics as st, math, sys
SCR = 'C:/Users/kaam/Desktop/operator mode/tapemap/docs/panel-research/scratch/'
OPEN, CLOSE = 555, 930
FULL = ['2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30',
        '2026-10-01', '2026-10-05', '2026-10-06', '2026-10-08', '2026-10-19']
EXP = {'2026-09-22', '2026-09-29', '2026-10-06', '2026-10-19'}
raw = json.load(open(SCR + 'pr_1m_NIFTY.json', encoding='utf-8'))
def mint(ms): return (int(ms) // 60000 + 330) % 1440
D = {}
for d in FULL:
    B = {}
    for b in raw[d]['1m']:
        m = mint(b['t'])
        if OPEN <= m < CLOSE and not b['partial']:
            B[m] = b
    D[d] = B
# minute arrays, 0.0 where a minute printed no trade but exists? A missing minute (no bar) = no trade = 0 lots only inside the session
def arr(d, key):
    B = D[d]
    return {m: (B[m][key] if m in B else 0.0) for m in range(OPEN + 1, CLOSE)}
V = {d: arr(d, 'vol') for d in FULL}
Bu = {d: arr(d, 'buy') for d in FULL}
Se = {d: arr(d, 'sell') for d in FULL}
dayvol = {d: sum(V[d].values()) for d in FULL}
print('day volume (lots):', {d[5:]: int(v) for d, v in dayvol.items()})
print('expiry mean %.0f  normal mean %.0f' % (st.mean(dayvol[d] for d in EXP), st.mean(dayvol[d] for d in FULL if d not in EXP)))

def w5(arrd, E): return sum(arrd[m] for m in range(E - 5, E))
def cum(arrd, E): return sum(arrd[m] for m in range(OPEN + 1, E))
Es = list(range(OPEN + 36, CLOSE - 4, 1))   # 09:51 .. 15:26 window ends (so every method has >=36 min of day)

def med(xs):
    xs = list(xs); return st.median(xs) if xs else None

def x_A(d, E, kind=False):
    ref = [o for o in FULL if o != d and (not kind or ((o in EXP) == (d in EXP)))]
    if kind and len(ref) < 5: return None
    m = med(w5(V[o], E) for o in ref)
    return w5(V[d], E) / m if m else None

def x_C(d, E):
    ref = [o for o in FULL if o != d]
    m = med(w5(V[o], E) for o in ref)
    cm = med(cum(V[o], E) for o in ref)
    if not m or not cm: return None
    raw_scale = cum(V[d], E) / cm
    w = min(1.0, (E - OPEN) / 60.0)
    scale = raw_scale ** w
    return w5(V[d], E) / (m * scale)

def x_B(d, E):
    # today's own trailing normal: median of non-overlapping 5-min windows in the previous 60 min
    if E - 65 < OPEN + 1: return None
    wins = [w5(V[d], E - 5 - 5 * k) for k in range(12)]
    m = med(wins)
    return w5(V[d], E) / m if m else None

def spearman(a, b):
    def rk(x):
        s = sorted(range(len(x)), key=lambda i: x[i]); r = [0] * len(x)
        for i, j in enumerate(s): r[j] = i
        return r
    ra, rb = rk(a), rk(b); n = len(a)
    ma, mb = st.mean(ra), st.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den

def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p / 100; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)

res = {}
for name, fn in (('A  all-days slot median', lambda d, E: x_A(d, E)),
                 ('AK same-kind slot median (draft)', lambda d, E: x_A(d, E, True)),
                 ('C  slot median x day scale', x_C),
                 ('B  own trailing 60m', x_B)):
    X = {d: {E: fn(d, E) for E in Es} for d in FULL}
    pool = [v for d in FULL for v in X[d].values() if v is not None]
    cov = {d: sum(1 for v in X[d].values() if v is not None) / len(Es) for d in FULL}
    p90 = pct(pool, 90); p70 = pct(pool, 70)
    share = {}
    for d in FULL:
        vals = [v for v in X[d].values() if v is not None]
        share[d] = (sum(1 for v in vals if v >= p90) / len(vals)) if vals else None
    ds = [d for d in FULL if share[d] is not None]
    rho = spearman([share[d] for d in ds], [dayvol[d] for d in ds]) if len(ds) > 4 else None
    ex_sh = [share[d] for d in ds if d in EXP]; no_sh = [share[d] for d in ds if d not in EXP]
    # by 30-min slot: share >= p90 pooled
    slot_sh = []
    for s in range(0, 12):
        lo, hi = OPEN + 30 * s, OPEN + 30 * s + 30
        v = [x for d in FULL for E, x in X[d].items() if x is not None and lo < E <= hi]
        slot_sh.append(sum(1 for x in v if x >= p90) / len(v) if v else None)
    print('\n== %s' % name)
    print('  coverage (share of windows with a usable normal): expiry days %.0f%%  normal days %.0f%%' % (
        100 * st.mean(cov[d] for d in FULL if d in EXP), 100 * st.mean(cov[d] for d in FULL if d not in EXP)))
    print('  pooled p70=%.2f p90=%.2f' % (p70, p90))
    print('  per-day share >= pooled p90: ' + ' '.join('%s:%s' % (d[5:], ('%.0f%%' % (100 * share[d])) if share[d] is not None else '--') for d in FULL))
    print('  spearman(day share>=p90, day volume) = %s' % ('%.2f' % rho if rho is not None else 'n/a'))
    if ex_sh and no_sh: print('  mean share>=p90: expiry %.1f%%  normal %.1f%%' % (100 * st.mean(ex_sh), 100 * st.mean(no_sh)))
    print('  share>=p90 by 30-min slot: ' + ' '.join('%s' % (('%.0f' % (100 * x)) if x is not None else '--') for x in slot_sh))
    res[name] = X

# 19 Oct walk-through with C and B
d = '2026-10-19'
print('\n19 Oct: 5-min total lots, price, and x under each definition')
print('time  vol5  buy5 sell5  close   xA    xC    xB')
for E in range(13 * 60 + 0, 14 * 60 + 36, 5):
    if E not in Es: continue
    c = D[d].get(E - 1, {}).get('c')
    print('%02d:%02d %5d %5d %5d %8s %5.2f %5.2f %5s' % (E // 60, E % 60, w5(V[d], E), w5(Bu[d], E), w5(Se[d], E), c,
          x_A(d, E) or 0, x_C(d, E) or 0, ('%.2f' % x_B(d, E)) if x_B(d, E) else '--'))
