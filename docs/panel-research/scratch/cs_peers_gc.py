import json, gzip, glob, os, statistics as st
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/data/'
def mint(ms): return (int(ms) // 60000 + 330) % 1440
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
# GC 5-min bars 19 Oct
B = {}
for r in jl(D + 'tape/tape_NIFTY_2026-10-19.jsonl'):
    if isinstance(r.get('t'), (int, float)) and isinstance(r.get('buy'), (int, float)):
        B[mint(r['t'])] = r
print('GC bars', len(B), 'first', min(B)//60, min(B)%60, 'last', max(B)//60, max(B)%60)
def gcw(s, e):
    b = sum(B[m]['buy'] for m in range(s, e, 5) if m in B); se = sum(B[m]['sell'] for m in range(s, e, 5) if m in B); n = sum(1 for m in range(s, e, 5) if m in B)
    return b, se, n
E = 14 * 60 + 30
for lab, s in (('5m', E - 5), ('15m', E - 15), ('30m', E - 30), ('60m', E - 60), ('since 13:15', 13 * 60 + 15), ('13:15-13:30', 13 * 60 + 15)):
    e = E if lab != '13:15-13:30' else 13 * 60 + 30
    b, se, n = gcw(s, e)
    print('GC %-12s buy %6d sell %6d bars %2d tilt %+.0f%%' % (lab, b, se, n, 100 * (b - se) / max(b + se, 1)))
# peers: spot path from chain + backfill
def mof(s): h, m = s.split(':')[:2]; return int(h) * 60 + int(m)
def spots(idx, day):
    out = {}
    for r in jl(D + 'chain_backfill/backfill_%s_%s.jsonl' % (idx, day)):
        if r.get('spot') is not None: out[mof(r['t'])] = r['spot']
    for r in jl(D + 'chain/chain_%s_%s.jsonl' % (idx, day)):
        sec = r.get('sec')
        if sec is not None and r.get('spot') is not None and 555 <= sec // 60 < 930: out[sec // 60] = r['spot']
    return out
for idx in ('NIFTY', 'BANKNIFTY', 'SENSEX'):
    S = spots(idx, '2026-10-19')
    ms = sorted(S)
    op = S[min(m for m in ms if m <= 560)] if any(m <= 560 for m in ms) else None
    now = S[max(m for m in ms if m <= E)]
    hi_t = max((m for m in ms if m <= E), key=lambda m: S[m]); lo_t = min((m for m in ms if m <= E), key=lambda m: S[m])
    s1315 = S[max(m for m in ms if m <= 13 * 60 + 15)]; s1430 = now
    s60 = S[max(m for m in ms if m <= E - 60)]; s15 = S[max(m for m in ms if m <= E - 15)]
    print('%-9s open %.1f now %.1f (%+.2f%%)  day hi %.1f @%02d:%02d lo %.1f @%02d:%02d | 13:15 %.1f (%+.2f%% since)  15m %+.2f%%  60m %+.2f%%' % (
        idx, op, now, 100 * (now / op - 1), S[hi_t], hi_t // 60, hi_t % 60, S[lo_t], lo_t // 60, lo_t % 60, s1315, 100 * (now / s1315 - 1), 100 * (now / s15 - 1), 100 * (now / s60 - 1)))
