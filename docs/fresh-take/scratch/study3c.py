"""STUDY 3c: drift-expected counts, day extremes caught, and the days the marks failed. Descriptive."""
import json, collections
import of_lib
from of_lib import *
from study3 import MDAYS, winner, era, rows as R, base as BASE

out = []; P = out.append
# ---- drift-expected WITH counts: what a mark with NO information would show given the era's baseline drift
P('=== DRIFT CHECK: observed WITH-first vs the WITH count expected if the mark carried no information (baseline UP/DOWN-first of the same era, same winner mix) ===')
P('  baseline A: UP-first %d DOWN-first %d | baseline B: UP-first %d DOWN-first %d' % (BASE[era('2026-09-22')]['UP-first'], BASE[era('2026-09-22')]['DOWN-first'], BASE[era('2026-10-05')]['UP-first'], BASE[era('2026-10-05')]['DOWN-first']))
for e in sorted({r['era'] for r in R}):
    b = BASE[e]; pu = b['UP-first']/(b['UP-first']+b['DOWN-first'])
    for k in ['trap', 'absorption', 'exhaustion', 'initiative', 'vacuum']:
        s = [r for r in R if r['era'] == e and r['kind'] == k and r['out'] in ('WITH', 'AGAINST')]
        if not s: continue
        exp = sum(pu if r['w'] > 0 else 1-pu for r in s)
        nb = sum(1 for r in s if r['w'] > 0)
        P('  %s %-11s decided n=%3d (buyer-winner %3d, seller-winner %3d) | observed WITH %3d | expected-from-drift WITH %5.1f' % (e[:1], k, len(s), nb, len(s)-nb, sum(1 for r in s if r['out'] == 'WITH'), exp))
P('')
# ---- day extremes caught
P('=== DAY EXTREMES CAUGHT: a trap / absorption / exhaustion mark whose winner is opposite the extreme, within 10 pts of it, dated 5 min before to 20 min after the extreme bar (hindsight: the extremes are the final ones) ===')
tot = caught = 0; marks_total = 0
for day in MDAYS:
    pb = path(day)
    if not pb: continue
    hi = max(pb, key=lambda b: b['h']); lo = min(pb, key=lambda b: b['l'])
    g = gc_bars(day); cov_end = (g[-1]['sec']+300) if g else 0
    ms, _ = marks(day)
    sel = [m for m in ms if m['kind'] in ('trap', 'absorption', 'exhaustion')]
    line = []
    for nm, ex, w, t_ex in (('low', lo['l'], +1, lo['s']), ('high', hi['h'], -1, hi['s'])):
        covered = t_ex + 1200 <= cov_end
        hit = [m for m in sel if winner(m) == w and abs(m['p']-ex) <= 10 and t_ex-300 <= m['sec'] <= t_ex+1200]
        line.append('%s %.0f@%s %s%s' % (nm, ex, hm(t_ex), ('CAUGHT by ' + ','.join(sorted({m['kind'] for m in hit}))) if hit else ('not marked' if covered else 'outside mark coverage'), ''))
        if covered:
            tot += 1; caught += bool(hit)
    marks_total += len(sel)
    P('  %s: %s | %s | trap/absorption/exhaustion marks that day: %d' % (day[5:], line[0], line[1], len(sel)))
P('  TOTAL covered day extremes %d | caught %d | trap+absorption+exhaustion marks on those days %d' % (tot, caught, marks_total))
P('')
P('=== THE DAYS THE MARKS FAILED: 12 Oct (down-trend) buyer-winner marks and what price did ===')
for r in sorted([r for r in R if r['day'] == '2026-10-12' and r['w'] == 1 and r['kind'] in ('absorption', 'trap')], key=lambda r: r['T']):
    P('  %s %-10s winner buyers p %.1f size %d | 0.5U: %s | ctx %s' % (r['T'], r['kind'], r['p'], r['size'], r['out'], r['ctx']))
P('')
P('=== counter-trend vs with-trend initiative (the only kind where the split looked different) ===')
for ctx in ['with-trend', 'counter-trend']:
    s = [r for r in R if r['kind'] == 'initiative' and r['ctx'] == ctx]
    c = collections.Counter(r['out'] for r in s)
    P('  initiative %-13s n=%3d | WITH %d / AGAINST %d / other %d' % (ctx, len(s), c['WITH'], c['AGAINST'], len(s)-c['WITH']-c['AGAINST']))
open('study3c_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))

# ---- era split and a 20-pt tolerance for the day-extreme catch
res = {}
for tol in (10, 20):
    for e in ('A', 'B'):
        tot = caught = nm = 0
        for day in MDAYS:
            if (day < '2026-10-05') != (e == 'A'): continue
            pb = path(day)
            if not pb: continue
            hi = max(pb, key=lambda b: b['h']); lo = min(pb, key=lambda b: b['l'])
            g = gc_bars(day); cov_end = (g[-1]['sec']+300) if g else 0
            ms, _ = marks(day)
            sel = [m for m in ms if m['kind'] in ('trap', 'absorption', 'exhaustion')]
            nm += len(sel)
            for ex, w, t_ex in ((lo['l'], +1, lo['s']), (hi['h'], -1, hi['s'])):
                if t_ex + 1200 > cov_end: continue
                tot += 1; caught += any(winner(m) == w and abs(m['p']-ex) <= tol and t_ex-300 <= m['sec'] <= t_ex+1200 for m in sel)
        res[(tol, e)] = (tot, caught, nm)
        print('era %s tolerance %d pts: covered day extremes %d | caught %d | trap+absorption+exhaustion marks on those days %d' % (e, tol, tot, caught, nm))
