"""When did flow last feed the 19 Oct leg? last window end (minute stride) at which the 15-min tilt was beyond a band IN THE LEG'S DIRECTION (sellers),
for UX (1-min) and GC (5-min bars), bands 0.30 / 0.36 / 0.40. Also fut OI change over the leg."""
import json
exec(open('cs_flow_test.py', encoding='utf-8').read().split('# (1) per-side')[0])
d = '2026-10-19'
Bg = {}
for line in open('C:/Users/kaam/Desktop/operator mode/tapemap/data/tape/tape_NIFTY_2026-10-19.jsonl', encoding='utf-8'):
    try: r = json.loads(line)
    except ValueError: continue
    if isinstance(r.get('t'), (int, float)) and isinstance(r.get('buy'), (int, float)): Bg[mint(r['t'])] = r
for band in (0.30, 0.36, 0.40):
    last_ux = last_gc = None
    for E in range(13 * 60 + 15, 14 * 60 + 31):
        b, s = w(Bu[d], E, 15), w(Se[d], E, 15)
        if b + s >= 60 and (b - s) / (b + s) <= -band: last_ux = E
        if E % 5 == 0:
            bb = sum(Bg[m]['buy'] for m in range(E - 15, E, 5) if m in Bg); ss = sum(Bg[m]['sell'] for m in range(E - 15, E, 5) if m in Bg)
            if bb + ss >= 60 and (bb - ss) / (bb + ss) <= -band: last_gc = E
    f = lambda E: ('%02d:%02d' % (E // 60, E % 60)) if E else 'none'
    print('band %.2f: last 15m-sellers window end  UX %s  GC %s' % (band, f(last_ux), f(last_gc)))
