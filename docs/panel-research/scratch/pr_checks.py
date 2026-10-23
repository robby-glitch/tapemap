"""The small checks quoted in INTERNAL.md, in one place (read-only). python -B pr_checks.py > pr_checks_out.txt
1 GC vs Upstox per side on matched NIFTY 5-min bars · 2 OI publication steps · 3 chain rows with ATM+/-2 / +/-4 off the
window · 4 Upstox arrival latency (19 Oct) · 5 senses option sweeps vs chain volume (19 Oct, NIFTY)."""
import json, glob, gzip, os, collections, sys
import numpy as np
sys.dont_write_bytecode = True
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/data/'
FULL = ['2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30',
        '2026-10-01', '2026-10-05', '2026-10-06', '2026-10-08', '2026-10-19']


def rows(p):
    op = gzip.open if p.endswith('.gz') else open
    out = []
    with op(p, 'rt', encoding='utf-8') as f:
        for l in f:
            try:
                out.append(json.loads(l))
            except ValueError:
                pass
    return out


def bars(p):
    return {int(r['t']): r for r in rows(p) if isinstance(r.get('t'), (int, float))} if os.path.exists(p) else {}


# 1
G, U = [], []
for d in FULL:
    g, u = bars(D + f'tape/tape_NIFTY_{d}.jsonl'), bars(D + f'tape/ux_NIFTY_{d}.jsonl')
    for t in sorted(set(g) & set(u)):
        a, b = g[t], u[t]
        if (t // 1000 + 19800) % 86400 < 33600 or None in (a.get('buy'), a.get('sell'), b.get('buy'), b.get('sell')):
            continue
        G.append((a['buy'], a['sell'])); U.append((b['buy'], b['sell']))
G, U = np.array(G, float), np.array(U, float)
print('1 matched bars', len(G))
for k, n in ((0, 'buy'), (1, 'sell')):
    lr = np.abs(np.log((U[:, k] + 1) / (G[:, k] + 1)))
    print(f'  {n}: Pearson {np.corrcoef(G[:, k], U[:, k])[0, 1]:.2f}, median UX/GC {np.median(U[:, k] / np.maximum(G[:, k], 1)):.2f}, '
          f'|log ratio| p50 {np.percentile(lr, 50):.2f} p90 {np.percentile(lr, 90):.2f}')
sg, su = np.sign(G[:, 0] - G[:, 1]), np.sign(U[:, 0] - U[:, 1])
nz = (sg != 0) & (su != 0)
gs, us = G[:, 0] / G.sum(1), U[:, 0] / U.sum(1)
print(f'  delta sign agrees {int((sg == su)[nz].sum())} of {int(nz.sum())}; buy share Pearson {np.corrcoef(gs, us)[0, 1]:.2f}, '
      f'median GC {np.median(gs):.3f} UX {np.median(us):.3f}')

# 2
for src, pre in (('GC', 'tape'), ('UX', 'ux')):
    n = st = 0
    for d in FULL:
        B = [b for _, b in sorted(bars(D + f'tape/{pre}_NIFTY_{d}.jsonl').items()) if b.get('oi')]
        for a, b in zip(B, B[1:]):
            if b['t'] - a['t'] == 300000:
                n += 1
                st += abs(b['oi'] - a['oi']) > (b.get('vol') or 0) * 65
    print(f'2 {src}: |dOI| > bar volume in {st} of {n} NIFTY 5-min bars')

# 3
for idx in ('NIFTY', 'BANKNIFTY', 'SENSEX'):
    n = b2 = b4 = days = 0
    for p in sorted(glob.glob(D + f'chain/chain_{idx}_*.jsonl*')):
        R = [r for r in rows(p) if r.get('strikes')]
        if len(R) < 1900:
            continue
        days += 1
        for r in R:
            ks = [s['k'] for s in r['strikes']]
            step = ks[1] - ks[0]
            atm = round(r['spot'] / step) * step
            n += 1
            b2 += atm - 2 * step < ks[0] or atm + 2 * step > ks[-1]
            b4 += atm - 4 * step < ks[0] or atm + 4 * step > ks[-1]
    print(f'3 {idx}: {days} full chain days, {n} rows: ATM+/-2 off the window {b2 / n:.1%}, ATM+/-4 off {b4 / n:.1%}')

# 4
for idx in ('NIFTY', 'BANKNIFTY', 'SENSEX'):
    R = rows(D + f'book/book_{idx}_2026-10-19.jsonl')
    lag = np.array([(r['t'] - r['ltt']) / 1000 for r in R if r.get('ltt') and r.get('t')])
    cts = np.array([(r['t'] - r['cts']) / 1000 for r in R if r.get('cts') and r.get('t')])
    print(f'4 {idx} 19 Oct: since last trade p50 {np.median(lag):.2f}s p90 {np.percentile(lag, 90):.1f}s; '
          f'arrival - feed ts p50 {np.median(cts):.2f}s p90 {np.percentile(cts, 90):.2f}s')

# 5
tr = collections.Counter()
with open(D + 'senses/senses_2026-10-19.jsonl', encoding='utf-8') as f:
    for l in f:
        if '"sweep"' not in l or '"NIFTY-' not in l or 'FUT' in l:
            continue
        try:
            r = json.loads(l)
        except ValueError:
            continue
        tr[r['inst']] += r.get('traded') or 0
ch = [r for r in rows(D + 'chain/chain_NIFTY_2026-10-19.jsonl') if r.get('strikes')]
v0 = {(s['k'], g): s[g]['vol'] for s in ch[0]['strikes'] for g in ('ce', 'pe') if s.get(g)}
v1 = {(s['k'], g): s[g]['vol'] for s in ch[-1]['strikes'] for g in ('ce', 'pe') if s.get(g)}
for inst, v in tr.most_common(6):
    k, g = int(inst.split('-')[1][:-2]), inst[-2:].lower()
    dv = (v1.get((k, g)) or 0) - (v0.get((k, g)) or 0)
    print(f'5 {inst}: swept traded / chain day volume = {v / dv:.2f}' if dv else f'5 {inst}: no chain volume')
