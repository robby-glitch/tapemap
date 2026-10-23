"""Critique test 2: OI speed. (a) does the draft's ratio (b15/15)/(b60/60) blow up, and why; (b) does a gross-based bounded form behave;
(c) what does ATM+-2 hide at 19 Oct 14:30. NIFTY chain (M) + REST backfill (I), all recorded days. Descriptive only."""
import json, gzip, glob, os, statistics as st, math, sys
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/data/'
OPEN, CLOSE, STEP, LK = 555, 930, 50, 1e5
def jl(path):
    for p in (path, path + '.gz'):
        if os.path.exists(p):
            op = gzip.open if p.endswith('.gz') else open
            out = []
            with op(p, 'rt', encoding='utf-8') as f:
                for line in f:
                    try: out.append(json.loads(line))
                    except ValueError: pass
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
days = sorted({os.path.basename(p).split('_')[-1][:10] for p in glob.glob(D + 'chain/chain_NIFTY_2026-*')})
def build(M, E, W, leg, js=range(-2, 3), atm=None):
    a, b = M.get(E - 1), M.get(E - 1 - W)
    if not a or not b: return None
    if atm is None: atm = round(a[0] / STEP) * STEP
    t = 0.0
    for j in js:
        k = atm + j * STEP
        x, y = a[1].get(k), b[1].get(k)
        if not x or not y or x[leg] is None or y[leg] is None: return None
        t += x[leg] - y[leg]
    return t / LK

rows = []   # (day, E, leg, q0,q1,q2,q3)
for d in days:
    M = oi(d)
    if len(M) < 200: continue
    for E in range(OPEN + 62, CLOSE - 1, 5):
        for leg in (0, 1):
            a0 = M.get(E - 1)
            if not a0: continue
            atm0 = round(a0[0] / STEP) * STEP
            q = [build(M, E - 15 * i, 15, leg, atm=atm0) for i in range(4)]
            if any(v is None for v in q): continue
            rows.append((d, E, leg, *q))
print('days with chain', len(days), ' (day,E,leg) rows with 4 whole quarters:', len(rows))
allq = sorted(abs(r[3]) for r in rows)
def pc(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p / 100; f = int(k); c = min(f + 1, len(xs) - 1); return xs[f] + (xs[c] - xs[f]) * (k - f)
p70, p90, p50 = pc(allq, 70), pc(allq, 90), pc(allq, 50)
print('|15m build| pooled (all slots, ATM+-2 side sum, L): p50 %.1f p70 %.1f p90 %.1f' % (p50, p70, p90))
loud = [r for r in rows if abs(r[3]) >= p70]
print('rows with |q0| >= p70:', len(loud))
# draft ratio
def ratio_net(r):
    q0 = r[3]; b60 = r[3] + r[4] + r[5] + r[6]
    return (q0 / 15) / (b60 / 60) if abs(b60) > 1e-9 else float('inf')
rn = [ratio_net(r) for r in loud]
big = sum(1 for x in rn if abs(x) > 10); neg = sum(1 for x in rn if x < 0)
print('DRAFT ratio (b15/15)/(b60/60), among loud rows: |ratio|>10 in %d (%.0f%%), negative in %d (%.0f%%), |ratio|>=1.5 in %d (%.0f%%)' % (
    big, 100 * big / len(rn), neg, 100 * neg / len(rn), sum(1 for x in rn if abs(x) >= 1.5), 100 * sum(1 for x in rn if abs(x) >= 1.5) / len(rn)))
print('  ratio percentiles on |ratio|: p50 %.1f p90 %.1f p99 %.1f max %.0f' % tuple([pc([abs(x) for x in rn if x != float('inf')], p) for p in (50, 90, 99)] + [max(abs(x) for x in rn if x != float('inf'))]))
# why: base netting. share of loud rows where prior 45 min net is opposite sign to q0 and |prior net| >= half |q0|
opp = [r for r in loud if (r[4] + r[5] + r[6]) * r[3] < 0]
opp_big = [r for r in opp if abs(r[4] + r[5] + r[6]) >= 0.5 * abs(r[3])]
print('loud rows where the prior 45 min netted the OPPOSITE way: %d (%.0f%%); of those, prior net >= half of q0: %d' % (len(opp), 100 * len(opp) / len(loud), len(opp_big)))
# base explosion because net60 ~ 0 while gross60 is not
sm = [r for r in loud if abs(r[3] + r[4] + r[5] + r[6]) < 0.25 * abs(r[3])]
print('loud rows where |net60| < 25%% of |q0| (ratio > 4x by netting): %d (%.0f%%); of these median gross60 / |q0| = %.2f' % (
    len(sm), 100 * len(sm) / len(loud), st.median(sum(abs(v) for v in r[3:7]) / abs(r[3]) for r in sm) if sm else 0))
# bounded share form
def share(r): g = sum(abs(v) for v in r[3:7]); return abs(r[3]) / g if g > 0 else None
sh = [share(r) for r in loud if share(r) is not None]
print('BOUNDED share |q0| / sum|q0..q3| among loud rows: p10 %.2f p25 %.2f p50 %.2f p75 %.2f p90 %.2f   (0.25 = steady)' % tuple(pc(sh, p) for p in (10, 25, 50, 75, 90)))
tez = sum(1 for x in sh if x >= 0.5); dh = sum(1 for x in sh if x <= 0.2)
print('  front-loaded (>=0.50): %d (%.0f%%)   tiring (<=0.20): %d (%.0f%%)' % (tez, 100 * tez / len(sh), dh, 100 * dh / len(sh)))
# persistence: does the bounded share keep its class 5 min later?  (same leg, same day, E+5)
idx = {(r[0], r[1], r[2]): r for r in rows}
for lag in (5, 15):
    same = tot = same2 = 0
    for r in loud:
        n = idx.get((r[0], r[1] + lag, r[2]))
        if not n or abs(n[3]) < p70: continue
        a, b = share(r), share(n)
        if a is None or b is None: continue
        tot += 1; same += ((a >= 0.5) == (b >= 0.5)); same2 += ((abs(ratio_net(r)) >= 1.5) == (abs(ratio_net(n)) >= 1.5))
    print('  lag %2d: loud at T and still loud at T+lag: %d; bounded class(>=0.5) kept %.0f%% | draft class(|ratio|>=1.5) kept %.0f%%' % (lag, tot, 100 * same / tot if tot else 0, 100 * same2 / tot if tot else 0))

# 19 Oct 14:30 strike map and 16 Oct 11:05
for d, E in (('2026-10-19', 14 * 60 + 30), ('2026-10-16', 11 * 60 + 5)):
    M = oi(d); a, b = M.get(E - 1), M.get(E - 16)
    atm = round(a[0] / STEP) * STEP
    print('\n%s %02d:%02d spot %.1f ATM %d  15-min OI change per strike (L): strike CE PE' % (d, E // 60, E % 60, a[0], atm))
    for j in range(-3, 4):
        k = atm + j * STEP
        x, y = a[1].get(k), b[1].get(k)
        if x and y and None not in (x[0], y[0], x[1], y[1]):
            print('  %d (%+d)  CE %+7.1f  PE %+7.1f' % (k, j, (x[0] - y[0]) / LK, (x[1] - y[1]) / LK))
    for leg, nm in ((0, 'CE'), (1, 'PE')):
        q = [build(M, E - 15 * i, 15, leg, atm=atm) for i in range(4)]
        print('  %s quarters (newest first, ATM+-2 sum, L): %s' % (nm, ['%.1f' % v if v is not None else None for v in q]))
