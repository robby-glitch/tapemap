"""STUDY 3b: (a) post-hoc level-hold test for marks, (b) baselines for extreme-proximity, (c) decoder events 5-13 Oct."""
import of_lib, json
from of_lib import *
from study3 import MDAYS, winner, era   # re-runs study3 once (cheap)

def hold_test(pb, T_r, w, p, horizon=3600, tol=0.25):
    ends = [b['e'] for b in pb]; i = bisect.bisect_right(ends, T_r) - 1
    if i < 0: return None
    b0 = pb[i]; U = unit(b0['c'], b0['sig']); lim = p - w*tol*U     # buyers: broke if low <= p - 0.25U ; sellers: high >= p + 0.25U
    best = 0.0; seen = 0
    for b in pb[i+1:]:
        if b['s'] >= b0['e'] + horizon: break
        seen += 1
        if (w > 0 and b['l'] <= lim) or (w < 0 and b['h'] >= lim): return ('BROKE', best/U)
        best = max(best, (b['h']-b0['c']) if w > 0 else (b0['c']-b['l']))
    return ('HELD' if seen >= 15 else 'END', best/U)

out = []; P = out.append
rows = []
for day in MDAYS:
    pb = path(day)
    if not pb: continue
    ms, _ = marks(day)
    for m in ms:
        w = winner(m)
        if w == 0: continue
        h = hold_test(pb, m['sec']+300, w, m['p'])
        if h: rows.append(dict(day=day, era=era(day), kind=m['kind'], w=w, hold=h[0], mfe=h[1]))
P('=== (a) POST-HOC (added after the first table mis-scored the 16 Oct 09:40 trap): LEVEL HOLD within 60 min: BROKE = price trades 0.25U beyond the mark price against the winner; HELD = it does not (>=45 min seen); MFE>=1U = best excursion with the winner >= 1.0 unit ===')
for e in sorted({r['era'] for r in rows}):
    for k in ['trap', 'absorption', 'exhaustion', 'initiative', 'vacuum']:
        s = [r for r in rows if r['era'] == e and r['kind'] == k]
        if s:
            c = collections.Counter(r['hold'] for r in s)
            P('  %s %-11s n=%3d | HELD %3d | BROKE %3d | END %2d | MFE>=1U in %d of %d' % (e[:1], k, len(s), c['HELD'], c['BROKE'], c['END'], sum(1 for r in s if r['mfe'] >= 1.0), len(s)))
# baseline for the hold test: every 5-min bar close, winner buyers at that bar's low / sellers at that bar's high
bh = collections.Counter()
for day in MDAYS:
    pb = path(day); g = gc_bars(day)
    if not pb or not g: continue
    for b in g:
        T = b['sec']+300
        if not (9*3600+30*60 <= T <= 14*3600+30*60): continue
        for w, p in ((1, b['l']), (-1, b['h'])):
            h = hold_test(pb, T, w, p)
            if h: bh[(w, h[0])] += 1
P('  BASELINE (every 5-min bar, winner = buyers at the bar low / sellers at the bar high; same days): buyers-at-low HELD %d BROKE %d END %d | sellers-at-high HELD %d BROKE %d END %d' % (bh[(1,'HELD')], bh[(1,'BROKE')], bh[(1,'END')], bh[(-1,'HELD')], bh[(-1,'BROKE')], bh[(-1,'END')]))
# proximity baselines
tot = near_loc = near_day = 0; ndays = 0
for day in MDAYS:
    pb = path(day); g = gc_bars(day)
    if not pb or not g: continue
    dhi = max(b['h'] for b in pb); dlo = min(b['l'] for b in pb)
    for b in g:
        T = b['sec']+300
        if not (9*3600+30*60 <= T <= 14*3600+30*60): continue
        ends = [x['e'] for x in pb]; i = bisect.bisect_right(ends, T)-1
        look = [x for x in pb[:i+1] if x['e'] > T-1800]
        if not look: continue
        for w, p, ex_l, ex_d in ((1, b['l'], min(x['l'] for x in look), dlo), (-1, b['h'], max(x['h'] for x in look), dhi)):
            tot += 1; near_loc += abs(p-ex_l) <= 10; near_day += abs(p-ex_d) <= 10
P('  PROXIMITY BASELINE (every 5-min bar 09:30-14:30, both ends: bar low vs 30-min low, bar high vs 30-min high): %d readings | within 10 pts of the 30-min extreme %d | within 10 pts of the DAY extreme %d' % (tot, near_loc, near_day))

# ---------------- (c) decoder events
P('')
P('=== (c) DECODER EVENTS (5-13 Oct, FORWARD-LOGGED, 0.4.0): counts, and 0.5U WITH/AGAINST in the hypothesised direction ===')
P('  winner map (fixed before counting): E1 BADA PRINT = printer side; E2 PEHAL = side; E3 DABAAV absorbed = -side, positioning = +side; E4 DHER = side; E5 KHULA = side (the unfinished high/low gets revisited); E6 THAKAAN = -side (the side that ran out loses); E7 CVD ulta = side (warns against the other)')
evs = []
for day in ['2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09','2026-10-12','2026-10-13']:
    pb = path(day)
    if not pb: continue
    allrows = [json.loads(l) for l in open(D+'decoder/decoder_%s.jsonl' % day, encoding='utf-8')]
    state = {}
    for r in allrows:
        if r.get('row') == 'state': state[r['id']] = r.get('state')
    for e in decoder_events(day):
        k = e['kind']; s = e['side']
        if k == 'E1': w = s
        elif k == 'E2': w = s
        elif k == 'E3': w = -s if e.get('split') == 'absorbed' else (s if e.get('split') == 'positioning' else 0)
        elif k == 'E4': w = s
        elif k == 'E5': w = s
        elif k == 'E6': w = -s
        elif k == 'E7': w = s
        else: w = 0
        T_r = ist_sec(e['t']) + 300
        o = outcome(pb, T_r, w) if w else None
        h = hold_test(pb, T_r, w, e['p']) if w else None
        atk = (e.get('at') or {}).get('kind')
        evs.append(dict(day=day, kind=k, name=e['name'], side=s, w=w, T=hm(ist_sec(e['t'])), p=e['p'], lots=e.get('lots'), at=atk, split=e.get('split'), state=state.get(e['id'], e.get('state')), out=o[0] if o else None, hold=h[0] if h else None, daytype=daytype(day)[1]))
json.dump(evs, open('decoder_rows.json', 'w'))
for k in ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7']:
    s = [r for r in evs if r['kind'] == k]
    if not s: continue
    c = collections.Counter(r['out'] for r in s if r['w']); hh = collections.Counter(r['hold'] for r in s if r['w'])
    P('  %s %-9s n=%3d (unsided %d) | WITH %d / AGAINST %d / TIE %d / NONE+END %d | level HELD %d / BROKE %d / END %d | at: %s' % (k, s[0]['name'], len(s), sum(1 for r in s if not r['w']), c['WITH'], c['AGAINST'], c['TIE'], c['NONE']+c['END'], hh['HELD'], hh['BROKE'], hh['END'], dict(collections.Counter(r['at'] for r in s))))
P('')
P('  E1 BADA PRINT rows (all):')
for r in sorted([r for r in evs if r['kind'] == 'E1'], key=lambda r: (r['day'], r['T'])):
    P('    %s %s %s %5s lots @%.1f at=%s state=%s | 0.5U %s | hold %s | %s' % (r['day'][5:], r['T'], 'BUYER ' if r['side'] > 0 else 'SELLER', r['lots'], r['p'], r['at'], r['state'], r['out'], r['hold'], r['daytype']))
open('study3b_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
