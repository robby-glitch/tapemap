"""How often would the proposed tilt states fire?  NIFTY UX 1-min, 12 full days, evaluated every 5 min from 10:15.
T15 = tilt of last 15 min, T45 = tilt of the 45 min before that (non-overlapping), dead-band 0.15, min 60 lots in a window.
 pressing : |T15|>=.15, same sign as T45 or T45 inside band, and |T5|>=|T15|  (5m at least as one-sided)
 tiring   : T15 and T45 same side beyond band, |T5| <= 0.5*|T15|
 handover : T15 and T45 opposite beyond band
 Also: persistence of the T15 side over the next non-overlapping 15 min for each state; events per day (episodes = consecutive firing evals merged)."""
import json, statistics as st
SCR = 'C:/Users/kaam/Desktop/operator mode/tapemap/docs/panel-research/scratch/'
OPEN, CLOSE = 555, 930
FULL = ['2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30', '2026-10-01', '2026-10-05', '2026-10-06', '2026-10-08', '2026-10-19']
raw = json.load(open(SCR + 'pr_1m_NIFTY.json', encoding='utf-8'))
def mint(ms): return (int(ms) // 60000 + 330) % 1440
Bu, Se = {}, {}
for d in FULL:
    B = {mint(b['t']): b for b in raw[d]['1m'] if OPEN <= mint(b['t']) < CLOSE and not b['partial']}
    Bu[d] = {m: (B[m]['buy'] if m in B else 0.0) for m in range(OPEN + 1, CLOSE)}
    Se[d] = {m: (B[m]['sell'] if m in B else 0.0) for m in range(OPEN + 1, CLOSE)}
def w(a, E, W): return sum(a[m] for m in range(E - W, E))
def tl(d, E, W):
    b, s = w(Bu[d], E, W), w(Se[d], E, W)
    return None if b + s < 60 else (b - s) / (b + s)
BAND = 0.15
stat = {'pressing': [], 'tiring': [], 'handover': []}
epi = {k: 0 for k in stat}
nev = 0
for d in FULL:
    last = {k: -99 for k in stat}
    for E in range(10 * 60 + 20, CLOSE - 15, 5):
        t5, t15, t45 = tl(d, E, 5), tl(d, E, 15), tl(d, E - 15, 45)
        if None in (t5, t15, t45): continue
        nev += 1
        fired = {}
        if abs(t15) >= BAND and abs(t5) >= abs(t15) and (t45 * t15 > 0 or abs(t45) < BAND): fired['pressing'] = 1
        if abs(t15) >= BAND and abs(t45) >= BAND and t15 * t45 > 0 and abs(t5) <= 0.5 * abs(t15): fired['tiring'] = 1
        if abs(t15) >= BAND and abs(t45) >= BAND and t15 * t45 < 0: fired['handover'] = 1
        nxt = tl(d, E + 15, 15)
        for k in fired:
            if E - last[k] > 15: epi[k] += 1
            last[k] = E
            if nxt is not None and abs(nxt) >= 1e-9: stat[k].append((t15 > 0) == (nxt > 0))
print('evaluations', nev, 'over', len(FULL), 'days (every 5 min, 10:20-15:15)')
for k in stat:
    v = stat[k]
    print('%-9s fires %4d evals (%.0f%%), %.1f episodes/day | T15 side kept over next 15 min: %.0f%% (n=%d)' % (k, len(v), 100 * len(v) / nev, epi[k] / len(FULL), 100 * sum(v) / max(len(v), 1), len(v)))
