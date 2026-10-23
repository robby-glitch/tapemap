"""STUDY 1: prior-day nodes (GoCharting ladders, prints.profile / prints.nodes): accept or reject at the first touch.
Definitions fixed in ORDERFLOW-STUDY.md before counting. GC 5-min bars for both the profile and the touch day."""
import of_lib, json, sys
from of_lib import *
import lib
SRC = sys.argv[1] if len(sys.argv) > 1 else 'gc'
def ux_bars(day):
    out = []
    for b in lib.ux('NIFTY', day):
        if b.get('c') is None or b.get('o') is None or not b.get('ladder'): continue
        b = dict(b); out.append(b)
    return out
def getbars(day):
    return gc_bars(day) if SRC == 'gc' else ux_bars(day)


ALLGC = ['2026-09-21','2026-09-22','2026-09-23','2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09']
TEST = ['2026-09-22','2026-09-23','2026-09-24','2026-09-25','2026-09-29','2026-10-01','2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09'] if SRC == 'gc' else ['2026-09-23','2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-10-01','2026-10-05','2026-10-06']
TOL = 5.0          # one 5-pt row
WIN = 6            # 30 minutes of 5-min bars

def zones(nd):
    """POC/VAH/VAL as points; HVN and LVN 5-pt bins merged into zones when adjacent."""
    out = [dict(kind='POC', lo=nd['poc'], hi=nd['poc']), dict(kind='VAH', lo=nd['vah'], hi=nd['vah']), dict(kind='VAL', lo=nd['val'], hi=nd['val'])]
    for kind in ('HVN', 'LVN'):
        ps = sorted(n['p'] for n in nd['nodes'] if n['kind'] == kind)
        cur = None
        for p in ps:
            if cur and p - cur['hi'] <= 5: cur['hi'] = p
            else:
                if cur: out.append(cur)
                cur = dict(kind=kind, lo=p, hi=p)
        if cur: out.append(cur)
    return out

def rank_in(xs, x):
    v = [y for y in xs if y is not None]
    return None if len(v) < 6 else sum(1 for y in v if y <= x)/len(v)

def classify(bars, vw, z):
    """first touch of zone z from outside, then ACCEPT / REJECT / NEITHER within WIN bars. returns dict or None"""
    lo, hi = z['lo']-TOL, z['hi']+TOL
    for j in range(1, len(bars)):
        b = bars[j]; prev = bars[j-1]
        inter = b['l'] <= hi and b['h'] >= lo
        if not inter: continue
        if prev['c'] > hi: appr = -1        # coming from above (moving down)
        elif prev['c'] < lo: appr = 1       # coming from below
        else: continue                       # opened inside: not a touch from outside
        far = hi if appr > 0 else lo        # far edge in the direction of travel
        near = lo if appr > 0 else hi
        sg = vw[j][1] if vw[j][1] else 0
        U = max(sg, 0.001*b['c']); turn = max(0.5*U, 10.0)
        closes = 0; first_acc = None; res = 'NEITHER'; t_res = None
        # the touch bar itself can already close beyond
        for k in range(j, min(len(bars), j+WIN+1)):
            c = bars[k]['c']
            beyond = (c > far) if appr > 0 else (c < far)
            closes = closes+1 if beyond else 0
            if closes >= 2: res = 'ACCEPT'; t_res = k-j; break
            # turn away from the near edge back toward the approach side, no close beyond so far
            away = (near - bars[k]['l']) if appr > 0 else (bars[k]['h'] - near)
            if k > j and away >= turn and closes == 0: res = 'REJECT'; t_res = k-j; break
        # delta at the touch bar: sign vs approach, ranked among the session's bars so far
        dl = b.get('delta') or 0
        ds = [abs(x.get('delta') or 0) for x in bars[:j]]
        rk = rank_in(ds, abs(dl))
        bucket = 'noise(<p80 / <6 bars)' if (rk is None or rk < 0.8) else ('big WITH the approach' if dl*appr > 0 else 'big AGAINST the approach')
        dwell = sum(1 for k in range(j+1, min(len(bars), j+WIN+1)) if lo <= bars[k]['c'] <= hi)
        return dict(kind=z['kind'], lo=z['lo'], hi=z['hi'], T=hm(b['sec']), appr=appr, res=res, t_res=t_res, bucket=bucket, dwell=dwell, j=j)
    return None

rows = []; elig = collections.defaultdict(lambda: [0, 0]); plc = collections.Counter(); pel = [0, 0]; pdwell = 0; pdt = collections.defaultdict(collections.Counter)
for day in TEST:
    pday = prior_day(day, ALLGC)
    pb_ = getbars(pday)
    nd = None
    if len(pb_) >= 68:
        pr_ = prints.profile(pb_)
        if pr_: nd = dict(poc=pr_['poc'], vah=pr_['vah'], val=pr_['val'], nodes=prints.nodes(pr_), hi=max(b['h'] for b in pb_), lo=min(b['l'] for b in pb_))
    bars = getbars(day)
    if not nd or len(bars) < 40: print('skip', day, 'prior', pday, 'nbars', len(bars)); continue
    for b in bars: b.setdefault('sec', b.get('sec'))
    vw = gc_vwap(bars)
    ct, dt = daytype(day)
    O = bars[0]['o']; prange = nd['hi'] - nd['lo']
    for z in zones(nd):
        r = classify(bars, vw, z)
        mid = (z['lo']+z['hi'])/2
        near_open = abs(mid - O) <= 0.75*prange
        if near_open:
            elig[z['kind']][0] += 1
            touched = any(b['l'] <= z['hi']+TOL and b['h'] >= z['lo']-TOL for b in bars)
            elig[z['kind']][1] += touched
        for sh in (-30.0, 30.0):
            zz = dict(kind=z['kind'], lo=z['lo']+sh, hi=z['hi']+sh)
            pr2 = classify(bars, vw, zz)
            midp = (zz['lo']+zz['hi'])/2
            if abs(midp - O) <= 0.75*prange:
                pel[0] += 1; pel[1] += any(b['l'] <= zz['hi']+TOL and b['h'] >= zz['lo']-TOL for b in bars)
            if pr2: plc[pr2['res']] += 1; pdwell += pr2['dwell']; pdt[dt][pr2['res']] += 1
        if r:
            r['day'] = day; r['daytype'] = dt; r['crosses'] = ct; r['pday'] = pday; rows.append(r)
json.dump(rows, open('study1_rows_%s.json' % SRC, 'w'))

out = []; P = out.append
P('STUDY 1 [%s] rows: %d first-touches from outside, on %d test days (SEEN, 5-min).' % (SRC, len(rows), len({r["day"] for r in rows})))
P('')
P('=== node kind x outcome within 30 min (ACCEPT = 2 consecutive 5-min closes beyond the FAR edge; REJECT = turn >= max(0.5 sigma, 10 pts) away from the NEAR edge, no close beyond; else NEITHER) ===')
for k in ['POC', 'VAH', 'VAL', 'HVN', 'LVN']:
    s = [r for r in rows if r['kind'] == k]
    c = collections.Counter(r['res'] for r in s)
    ta = sorted(r['t_res'] for r in s if r['res'] == 'ACCEPT')
    P('  %-4s touches %2d | ACCEPT %2d | REJECT %2d | NEITHER %2d | accept bar-lag (0 = touch bar, 1 = +5 min..): %s | dwell bars in zone, summed over touches: %d' % (k, len(s), c['ACCEPT'], c['REJECT'], c['NEITHER'], ta, sum(r['dwell'] for r in s)))
P('')
P('=== by approach direction (from below = up-approach) ===')
for k in ['POC', 'VAH', 'VAL', 'HVN', 'LVN']:
    for a, nm in ((1, 'from below'), (-1, 'from above')):
        s = [r for r in rows if r['kind'] == k and r['appr'] == a]
        if s:
            c = collections.Counter(r['res'] for r in s)
            P('  %-4s %-10s n=%2d | ACCEPT %2d | REJECT %2d | NEITHER %2d' % (k, nm, len(s), c['ACCEPT'], c['REJECT'], c['NEITHER']))
P('')
P('=== SPLIT 1: ranked delta at the touch bar (rank among the session bars so far; big = >= p80) ===')
for b in ['big WITH the approach', 'big AGAINST the approach', 'noise(<p80 / <6 bars)']:
    for grp, kinds in (('all kinds', ['POC', 'VAH', 'VAL', 'HVN', 'LVN']),):
        s = [r for r in rows if r['bucket'] == b]
        c = collections.Counter(r['res'] for r in s)
        P('  %-26s n=%2d | ACCEPT %2d | REJECT %2d | NEITHER %2d' % (b, len(s), c['ACCEPT'], c['REJECT'], c['NEITHER']))
P('')
P('=== SPLIT 2: day type (full-day VWAP crosses: trend <=4 / mid 5-8 / chop >=9; only 7 Oct is chop on the test days) ===')
for dt in ['trend(<=4)', 'mid(5-8)', 'chop(>=9)']:
    s = [r for r in rows if r['daytype'] == dt]
    c = collections.Counter(r['res'] for r in s)
    P('  %-11s days %s | n=%2d | ACCEPT %2d | REJECT %2d | NEITHER %2d' % (dt, sorted({r['day'][5:] for r in s}), len(s), c['ACCEPT'], c['REJECT'], c['NEITHER']))
P('')
P('=== MAGNET check: nodes within 0.75 x prior-day range of the 09:15 open: touched during the day / eligible ===')
for k in ['POC', 'VAH', 'VAL', 'HVN', 'LVN']:
    P('  %-4s touched %2d of %2d eligible' % (k, elig[k][1], elig[k][0]))
P('')
P('=== PLACEBO (added after the first run; same zones shifted -30 and +30 pts, same rules): first-touches %d | ACCEPT %d | REJECT %d | NEITHER %d | dwell bars %d | touched %d of %d eligible ===' % (sum(plc.values()), plc['ACCEPT'], plc['REJECT'], plc['NEITHER'], pdwell, pel[1], pel[0]))
P('  placebo by day type: ' + '; '.join('%s: ACCEPT %d / REJECT %d / NEITHER %d' % (k, v['ACCEPT'], v['REJECT'], v['NEITHER']) for k, v in sorted(pdt.items())))
P('')
P('=== every row ===')
for r in sorted(rows, key=lambda r: (r['day'], r['T'])):
    P('  %s %s %-3s %.0f-%.0f %s | %-7s lag %s | %s | dwell %d | %s' % (r['day'][5:], r['T'], r['kind'], r['lo'], r['hi'], 'up-approach' if r['appr'] > 0 else 'dn-approach', r['res'], r['t_res'], r['bucket'], r['dwell'], r['daytype']))
open('study1_out_%s.txt' % SRC, 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:60]))
