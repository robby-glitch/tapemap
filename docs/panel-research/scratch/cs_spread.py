import json, gzip, glob, os, statistics as st
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/data/'
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
def spots(idx, day):
    out = {}
    for r in jl(D + 'chain_backfill/backfill_%s_%s.jsonl' % (idx, day)):
        if r.get('spot') is not None: out[mof(r['t'])] = r['spot']
    for r in jl(D + 'chain/chain_%s_%s.jsonl' % (idx, day)):
        sec = r.get('sec')
        if sec is not None and r.get('spot') is not None and 555 <= sec // 60 < 930: out[sec // 60] = r['spot']
    return out
days = sorted({os.path.basename(p).split('_')[-1][:10] for p in glob.glob(D + 'chain/chain_BANKNIFTY_2026-*')} & {os.path.basename(p).split('_')[-1][:10] for p in glob.glob(D + 'chain/chain_NIFTY_2026-*')} & {os.path.basename(p).split('_')[-1][:10] for p in glob.glob(D + 'chain/chain_SENSEX_2026-*')})
P = {}
for d in days:
    P[d] = {i: spots(i, d) for i in ('NIFTY', 'BANKNIFTY', 'SENSEX')}
def at(S, m):
    c = [x for x in S if x <= m]
    return S[max(c)] if c else None
def opn(S):
    c = [x for x in S if x <= 560]
    return S[min(c)] if c else None
def pct_from_open(d, i, m):
    S = P[d][i]
    o, n = opn(S), at(S, m)
    return None if o is None or n is None else 100 * (n / o - 1)
def sp(d, m, i='BANKNIFTY', j='NIFTY'):
    a, b = pct_from_open(d, i, m), pct_from_open(d, j, m)
    return None if a is None or b is None else a - b
for lab, d, m in (('19 Oct 14:30', '2026-10-19', 870), ('16 Oct 11:05', '2026-10-16', 665), ('16 Oct 10:00', '2026-10-16', 600)):
    for i in ('BANKNIFTY', 'SENSEX'):
        cur = sp(d, m, i)
        ref = [sp(o, m, i) for o in days if o < d]
        ref = [x for x in ref if x is not None]
        n = len(ref)
        if cur is None or n < 5: print(lab, i, 'n/a'); continue
        rank = 100 * sum(1 for x in ref if abs(x) <= abs(cur)) / n
        print('%s  %-9s spread vs NIFTY (pct from open) = %+.2f%%  | prior-day |spread| at the same clock: n=%d median %.2f%% p90 %.2f%% -> |today| ranks p%.0f; NIFTY %+.2f%% | %s %+.2f%%' % (
            lab, i, cur, n, st.median(abs(x) for x in ref), sorted(abs(x) for x in ref)[int(0.9 * (n - 1))], rank, pct_from_open(d, 'NIFTY', m), i, pct_from_open(d, i, m)))
print('days', len(days))
# how redundant is SENSEX vs NIFTY: median |spread| at 14:30 across days
for i in ('BANKNIFTY', 'SENSEX'):
    xs = [abs(sp(d, 870, i)) for d in days if sp(d, 870, i) is not None]
    print(i, 'median |%from-open spread vs NIFTY| at 14:30 across', len(xs), 'days: %.2f%%  p90 %.2f%%' % (st.median(xs), sorted(xs)[int(0.9 * (len(xs) - 1))]))
