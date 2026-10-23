"""Cadence and artefacts of the two OI sources and the book feed (read-only; run with python -B).
book: frame gap, futures-OI update gap and jump size, OI at the open.
chain: row gap, option OI update gap at ATM+/-2, jump share, zero/None OI at the open."""
import sys, json, glob, gzip, statistics as st
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


def q(xs, ps=(10, 50, 90)):
    v = sorted(xs)
    return [round(v[int(p / 100 * (len(v) - 1))], 3) for p in ps] if v else None


def sec_ist(ms):
    return int(ms // 1000 + 19800) % 86400


for idx in ('NIFTY', 'BANKNIFTY', 'SENSEX'):
    fg, og, oj, ojpct, first_oi, nchg = [], [], [], [], [], []
    for day in FULL:
        f = glob.glob(D + f'book/book_{idx}_{day}.jsonl*')
        if not f:
            continue
        R = [r for r in rows(f[0]) if isinstance(r.get('t'), (int, float))]
        R = [r for r in R if 33300 <= sec_ist(r['t']) < 55800]
        ts = [r['t'] for r in R]
        fg += [(b - a) / 1000 for a, b in zip(ts, ts[1:])]
        last, lt, n = None, None, 0
        for r in R:
            oi = r.get('oi')
            if oi is None:
                continue
            if last is not None and oi != last:
                if lt is not None:
                    og.append((r['t'] - lt) / 1000)
                oj.append(abs(oi - last))
                ojpct.append(abs(oi - last) / last * 100)
                lt = r['t']
                n += 1
            last = oi
        nchg.append(n)
        first_oi.append((day, sec_ist(R[0]['t']), R[0].get('oi')))
    print(f'BOOK {idx}: frame gap s p10/50/90 {q(fg)}; fut-OI change gap s p10/50/90 {q(og)}; '
          f'changes/day median {st.median(nchg)}; jump contracts p10/50/90 {q(oj)}; jump % of OI p50/90/99 {q(ojpct, (50, 90, 99))}')
    print('   first row (sec, oi):', first_oi[:3], '...')

# chain: OI update cadence per option leg at ATM+/-2
for idx in ('NIFTY', 'BANKNIFTY', 'SENSEX'):
    rg, ug, share_same, blank_open, jump_top = [], [], [], [], []
    for day in FULL:
        f = glob.glob(D + f'chain/chain_{idx}_{day}.jsonl*')
        if not f:
            continue
        R = [r for r in rows(f[0]) if r.get('strikes') and 'sec' in r]
        secs = [r['sec'] for r in R]
        rg += [b - a for a, b in zip(secs, secs[1:])]
        atm0 = R[len(R) // 2]['atm']
        ks = sorted(s['k'] for s in R[0]['strikes'])
        step = ks[1] - ks[0]
        # blank / zero OI in the first 5 minutes of the file
        early = [r for r in R if r['sec'] < R[0]['sec'] + 300]
        nb = sum(1 for r in early for s in r['strikes'] for leg in ('ce', 'pe')
                 if (s.get(leg) or {}).get('oi') in (None, 0))
        nt = sum(1 for r in early for s in r['strikes'] for leg in ('ce', 'pe'))
        blank_open.append((day, nb, nt))
        for r in R:
            pass
        # per leg near the day's mid ATM: update gaps and how many rows repeat the same OI
        for k in (atm0 + step * n for n in range(-2, 3)):
            for leg in ('ce', 'pe'):
                last, lt, same, tot = None, None, 0, 0
                ch = []
                for r in R:
                    s = next((x for x in r['strikes'] if x['k'] == k), None)
                    oi = (s or {}).get(leg, {}).get('oi') if s else None
                    if oi is None:
                        continue
                    if last is not None:
                        tot += 1
                        if oi == last:
                            same += 1
                        else:
                            if lt is not None:
                                ug.append(r['sec'] - lt)
                            lt = r['sec']
                            ch.append((r['sec'], oi - last))
                    last = oi
                if tot:
                    share_same.append(same / tot)
                # jumpiness: within each 30-min window, the share of |net change| carried by its biggest update
                for w0 in range(33300, 55800, 1800):
                    xs = [d for s_, d in ch if w0 <= s_ < w0 + 1800]
                    net = abs(sum(xs))
                    if xs and net > 0:
                        jump_top.append(max(abs(x) for x in xs) / sum(abs(x) for x in xs))
    print(f'CHAIN {idx}: row gap s p10/50/90 {q(rg)}; ATM+/-2 OI update gap s p10/50/90 {q(ug)}; '
          f'share of rows with OI unchanged p10/50/90 {q(share_same)}; biggest single update / total |updates| per 30 min p10/50/90 {q(jump_top)}')
    print('   blank-or-zero OI legs in the first 5 min of the file (day, n, of):', blank_open)
