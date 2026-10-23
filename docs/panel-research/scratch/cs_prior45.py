import json
exec(open('cs_flow_test.py', encoding='utf-8').read().split('# (1) per-side')[0])
d = '2026-10-19'; E = 14 * 60 + 30
for lab, a, b in (('prior45 13:30-14:15', E - 60, E - 15), ('last15 14:15-14:30', E - 15, E), ('last5', E - 5, E)):
    bb, ss = w(Bu[d], b, b - a), w(Se[d], b, b - a)
    print('UX %-22s buy %5d sell %5d tilt %+.0f%%' % (lab, bb, ss, 100 * (bb - ss) / (bb + ss)))
import gzip, os
def mint2(ms): return (int(ms) // 60000 + 330) % 1440
Bg = {}
for line in open('C:/Users/kaam/Desktop/operator mode/tapemap/data/tape/tape_NIFTY_2026-10-19.jsonl', encoding='utf-8'):
    try: r = json.loads(line)
    except ValueError: continue
    if isinstance(r.get('t'), (int, float)) and isinstance(r.get('buy'), (int, float)): Bg[mint2(r['t'])] = r
for lab, a, b in (('prior45 13:30-14:15', E - 60, E - 15), ('last15', E - 15, E)):
    bb = sum(Bg[m]['buy'] for m in range(a, b, 5)); ss = sum(Bg[m]['sell'] for m in range(a, b, 5))
    print('GC %-22s buy %5d sell %5d tilt %+.0f%%' % (lab, bb, ss, 100 * (bb - ss) / (bb + ss)))
# leg: 13:15-13:30 share
bb = sum(Bu[d][m] for m in range(13 * 60 + 15, 13 * 60 + 30)); ss = sum(Se[d][m] for m in range(13 * 60 + 15, 13 * 60 + 30))
print('UX 13:15-13:30 buy %d sell %d sellers share %.0f%%' % (bb, ss, 100 * ss / (bb + ss)))
bb = sum(Bg[m]['buy'] for m in range(13 * 60 + 15, 13 * 60 + 30, 5)); ss = sum(Bg[m]['sell'] for m in range(13 * 60 + 15, 13 * 60 + 30, 5))
print('GC 13:15-13:30 buy %d sell %d sellers share %.0f%%' % (bb, ss, 100 * ss / (bb + ss)))
print('price fut: 13:14 close %s, 13:29 close %s, 14:29 close %s' % (C[d][13 * 60 + 14], C[d][13 * 60 + 29], C[d][14 * 60 + 29]))
