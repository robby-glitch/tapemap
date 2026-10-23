"""STUDY 3: the extension's marks. Descriptive counts only. Definitions fixed in ORDERFLOW-STUDY.md before running."""
import of_lib, json
from of_lib import *

MDAYS = ['2026-09-22','2026-09-23','2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-09-30','2026-10-01',
         '2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09','2026-10-12','2026-10-13','2026-10-16']
ALLGC = ['2026-09-21','2026-09-22','2026-09-23','2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-09-30','2026-10-01',
         '2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09','2026-10-12','2026-10-13','2026-10-16']
FULLGC = ['2026-09-21','2026-09-22','2026-09-23','2026-09-24','2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-05','2026-10-06','2026-10-07','2026-10-08']
NOPRIOR = {'2026-09-28', '2026-09-30'}     # 28 Sep: prior 25 Sep GC partial; 30 Sep: contract roll

def era(day): return 'A pre-0.4.0 (to 1 Oct)' if day < '2026-10-05' else 'B 0.4.0 (5 Oct on)'

def winner(m):
    k = m['kind']
    if k == 'trap': return -m['side']          # log stores the TRAPPED side
    if k == 'climax': return 0
    return m['side']

def loc_class(day, p, pb_bar, nodes):
    z = (p - pb_bar['vwap'])/pb_bar['sig'] if pb_bar['sig'] > 0 else None
    near = None
    if nodes:
        cands = [('POC', nodes['poc']), ('VAH', nodes['vah']), ('VAL', nodes['val']), ('PDH', nodes['hi']), ('PDL', nodes['lo']), ('PDC', nodes['close'])]
        cands += [(n['kind'], n['p']) for n in nodes['nodes']]
        hit = [(abs(p-v), nm) for nm, v in cands if abs(p-v) <= 10]
        if hit: near = min(hit)[1]
    if near: return 'node/level'
    if z is not None and abs(z) >= 1.5: return 'sigma ring'
    if z is not None and abs(z) <= 0.25: return 'at VWAP'
    return 'nowhere'

rows = []
for day in MDAYS:
    pb = path(day)
    if not pb: continue
    ms, n_raw = marks(day)
    ct, dt = daytype(day)
    pday = prior_day(day, ALLGC)
    nodes = None if (day in NOPRIOR or day in ('2026-10-12', '2026-10-13', '2026-10-16')) else (prior_nodes(pday) if pday else None)
    dhi = max(b['h'] for b in pb); dlo = min(b['l'] for b in pb)
    for m in ms:
        w = winner(m)
        T_r = m['sec'] + 300
        ends = [b['e'] for b in pb]; i = bisect.bisect_right(ends, T_r) - 1
        if i < 0: continue
        b0 = pb[i]
        r = dict(day=day, era=era(day), kind=m['kind'], side=m['side'], w=w, p=m['p'], size=m['size'], T=hm(m['sec']), n=m['n'], daytype=dt, crosses=ct)
        r['loc'] = loc_class(day, m['p'], b0, nodes) if (nodes or True) else None
        r['node_known'] = nodes is not None
        zc = (b0['c']-b0['vwap'])/b0['sig'] if b0['sig'] > 0 else 0
        r['ctx'] = 'flat' if (w == 0 or abs(zc) < 0.25) else ('with-trend' if (w > 0) == (zc > 0) else 'counter-trend')
        # local extreme (30 min lookback, causal): winner buyers -> mark price vs lowest low; sellers -> highest high
        look = [b for b in pb[:i+1] if b['e'] > T_r - 1800]
        if w != 0 and look:
            ext = min(b['l'] for b in look) if w > 0 else max(b['h'] for b in look)
            r['gap_local'] = abs(m['p'] - ext)
            r['gap_day'] = abs(m['p'] - (dlo if w > 0 else dhi))       # hindsight
        else:
            r['gap_local'] = r['gap_day'] = None
        if w != 0:
            o = outcome(pb, T_r, w)
            r['out'] = o[0] if o else None; r['mins'] = o[3] if o else None
        else:
            o = outcome(pb, T_r, 1)    # climax: up-first / down-first only
            r['out'] = ({'WITH': 'UP-first', 'AGAINST': 'DOWN-first'}.get(o[0], o[0])) if o else None; r['mins'] = o[3] if o else None
        rows.append(r)
json.dump(rows, open('study3_rows.json', 'w'))

# ---------- baseline: every 5-min bar close 09:30-14:30 on the same days, both directions
base = collections.defaultdict(collections.Counter)
for day in MDAYS:
    pb = path(day)
    if not pb: continue
    for T in range(9*3600+30*60, 14*3600+30*60+1, 300):
        o = outcome(pb, T, 1)
        if o: base[era(day)][{'WITH': 'UP-first', 'AGAINST': 'DOWN-first'}.get(o[0], o[0])] += 1
        # note: w=+1 UP-first; a w=-1 reading is the mirror (DOWN-first = with)

def tab(sel, title, key='out'):
    c = collections.Counter(r[key] for r in sel)
    n = len(sel)
    return '%s: n=%d | WITH-first %d | AGAINST-first %d | TIE %d | NONE %d | END %d' % (title, n, c['WITH'], c['AGAINST'], c['TIE'], c['NONE'], c['END'])

out = []
P = out.append
P('RAW ROWS: after collapse %d marks on %d days (NIFTY, SEEN / FORWARD-LOGGED)' % (len(rows), len({r["day"] for r in rows})))
P('')
P('BASELINE (every 5-min bar close 09:30-14:30 on the same days, +0.5U vs -0.5U, 60 min):')
for e, c in base.items(): P('  %s: UP-first %d | DOWN-first %d | TIE %d | NONE %d | END %d | total %d' % (e, c['UP-first'], c['DOWN-first'], c['TIE'], c['NONE'], c['END'], sum(c.values())))
P('')
sided = [r for r in rows if r['w'] != 0]
for e in sorted({r['era'] for r in rows}):
    P('=== ERA %s ===' % e)
    sel = [r for r in rows if r['era'] == e]
    c = collections.Counter(r['kind'] for r in sel); P('mark counts by kind: %s' % dict(c))
    for k in ['trap', 'absorption', 'exhaustion', 'initiative', 'vacuum']:
        s = [r for r in sel if r['kind'] == k]
        if s: P(tab(s, '  %-11s' % k))
        # trap sign check: if the winner convention were the other way round
        if k == 'trap' and s:
            c2 = collections.Counter(r['out'] for r in s)
            P('     (same trap rows read the OTHER way, winner = logged side: WITH %d | AGAINST %d)' % (c2['AGAINST'], c2['WITH']))
    s = [r for r in sel if r['kind'] == 'climax']
    if s:
        c3 = collections.Counter(r['out'] for r in s); P('  climax      : n=%d | UP-first %d | DOWN-first %d | TIE %d | NONE %d | END %d' % (len(s), c3['UP-first'], c3['DOWN-first'], c3['TIE'], c3['NONE'], c3['END']))
P('')
P('=== BY KIND x CONTEXT (both eras; WITH-first / AGAINST-first / TIE / NONE+END) ===')
for k in ['trap', 'absorption', 'exhaustion', 'initiative', 'vacuum']:
    for ctx in ['with-trend', 'counter-trend', 'flat']:
        s = [r for r in rows if r['kind'] == k and r['ctx'] == ctx]
        if s:
            c = collections.Counter(r['out'] for r in s)
            P('  %-11s %-13s n=%3d | %3d / %3d / %2d / %2d' % (k, ctx, len(s), c['WITH'], c['AGAINST'], c['TIE'], c['NONE']+c['END']))
P('')
P('=== BY KIND x LOCATION (days with a prior-day profile only; node/level = POC/VAH/VAL/HVN/LVN/PDH/PDL/PDC within 10 pts) ===')
for k in ['trap', 'absorption', 'exhaustion', 'initiative', 'vacuum']:
    for loc in ['node/level', 'sigma ring', 'at VWAP', 'nowhere']:
        s = [r for r in rows if r['kind'] == k and r['loc'] == loc and r['node_known']]
        if s:
            c = collections.Counter(r['out'] for r in s)
            P('  %-11s %-11s n=%3d | %3d / %3d / %2d / %2d' % (k, loc, len(s), c['WITH'], c['AGAINST'], c['TIE'], c['NONE']+c['END']))
P('')
P('=== BY KIND x DAY TYPE (full-day VWAP crosses after 09:30: trend <=4, mid 5-8, chop >=9) ===')
for k in ['trap', 'absorption', 'exhaustion', 'initiative', 'vacuum']:
    for dt in ['trend(<=4)', 'mid(5-8)', 'chop(>=9)']:
        s = [r for r in rows if r['kind'] == k and r['daytype'] == dt]
        if s:
            c = collections.Counter(r['out'] for r in s)
            P('  %-11s %-11s n=%3d | %3d / %3d / %2d / %2d' % (k, dt, len(s), c['WITH'], c['AGAINST'], c['TIE'], c['NONE']+c['END']))
P('')
P('=== NEAR AN EXTREME (winner-opposite extreme; local = last 30 min, causal; day = final day extreme, hindsight) ===')
for k in ['trap', 'absorption', 'exhaustion', 'initiative', 'vacuum']:
    s = [r for r in rows if r['kind'] == k and r['gap_local'] is not None]
    if s:
        P('  %-11s n=%3d | within 10 pts of local extreme %d | within 10 pts of the DAY extreme %d | within 20 pts of day extreme %d' % (
            k, len(s), sum(1 for r in s if r['gap_local'] <= 10), sum(1 for r in s if r['gap_day'] <= 10), sum(1 for r in s if r['gap_day'] <= 20)))
P('')
P('=== SEQUENCE: absorption followed by a trap at the same price within 10 pts in the next bar (winner of both = same side) ===')
seq = []
for day in MDAYS:
    ms = [r for r in rows if r['day'] == day]
    for a in [r for r in ms if r['kind'] == 'absorption']:
        for t in [r for r in ms if r['kind'] == 'trap' and abs(r['p']-a['p']) <= 10]:
            ta = int(a['T'][:2])*60+int(a['T'][3:]); tt = int(t['T'][:2])*60+int(t['T'][3:])
            if 0 < tt-ta <= 10 and (-t['side']) == a['side']:
                seq.append((day, a['T'], a['side'], a['p'], t['T'], a['out'], t['out'], a['era']))
c = collections.Counter(s[6] for s in seq)
P('  pairs: %d | outcome of the trap bar: WITH %d / AGAINST %d / TIE %d / NONE+END %d' % (len(seq), c['WITH'], c['AGAINST'], c['TIE'], c['NONE']+c['END']))
for s in seq: P('    ' + str(s))
P('')
P('=== 16 OCT SEQUENCE (as logged; winner = trap side flipped) ===')
for r in sorted([r for r in rows if r['day'] == '2026-10-16'], key=lambda r: r['T']):
    P('  %s %-10s logged side %+d winner %+d p %.1f size %d | %s in %s min | ctx %s loc %s | gap local %s day %s' % (r['T'], r['kind'], r['side'], r['w'], r['p'], r['size'], r['out'], r['mins'], r['ctx'], r['loc'], None if r['gap_local'] is None else round(r['gap_local']), None if r['gap_day'] is None else round(r['gap_day'])))
P('')
P('=== PER DAY: all sided marks WITH / AGAINST / TIE / NONE+END ===')
for day in MDAYS:
    s = [r for r in sided if r['day'] == day]
    if s:
        c = collections.Counter(r['out'] for r in s)
        P('  %s %-10s %-11s n=%3d | %3d / %3d / %2d / %2d' % (day[5:], s[0]['daytype'], 'A' if day < '2026-10-05' else 'B', len(s), c['WITH'], c['AGAINST'], c['TIE'], c['NONE']+c['END']))
open('study3_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
