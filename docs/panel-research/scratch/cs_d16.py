import json, gzip, os
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/data/'
def mint(ms): return (int(ms) // 60000 + 330) % 1440
rows = {}
for line in open(D + 'tape/tape_NIFTY_2026-10-16.jsonl', encoding='utf-8'):
    try: r = json.loads(line)
    except ValueError: continue
    if isinstance(r.get('t'), (int, float)) and isinstance(r.get('buy'), (int, float)): rows[mint(r['t'])] = r
print('16 Oct GC 5-min bars: start buy sell tilt close oi fromTicks?')
for m in sorted(rows):
    if m > 11 * 60 + 10: break
    r = rows[m]; b, s = r['buy'], r['sell']
    print('%02d:%02d b%4d s%4d t%+4.0f%% c%s oi%s ft%s' % (m // 60, m % 60, b, s, 100 * (b - s) / max(b + s, 1), r.get('c') or r.get('close'), r.get('oi'), r.get('fromTicks')))
print(list(rows[min(rows)].keys()))
