"""FS3 - do extension marks that coincide with CLIMAX / PUSH bars behave differently from the other marks? Descriptive. SEEN / FORWARD-LOGGED.
Conventions copied from ORDERFLOW-STUDY: winner = logged side except trap = -side; climax kind has no side; outcome = 0.5U first within 60 min from the bar close."""
import numpy as np
import of_lib
from fs_lib import *

days = gc_days(); ref = Ref(days); ext = gc_all()
POOLTH = {k: dict(p50=q(ref.POOL[k], .5), p70=q(ref.POOL[k], .7), p90=q(ref.POOL[k], .9)) for k in KEYS}
def bar_feats(day):
    """features + state per GC bar of `day`: LODO thresholds if the day is one of the 17, else pooled 17-day thresholds."""
    if day in ref.F:
        return {r['s']: dict(r, st=state(r, ref.TH[day])[0], hit=state(r, ref.TH[day])[2]) for r in ref.F[day]}
    bv, br = bases(days, set())
    return {r['s']: dict(r, st=state(r, POOLTH)[0], hit=state(r, POOLTH)[2]) for r in feats(ext.get(day, []), bv, br)}

ERA = lambda d: 'A' if d <= '2026-10-01' else 'B'
mdays = sorted(p[-16:-6] for p in glob.glob(D + 'tape/ofd_marks_NIFTY_2026-*.jsonl'))
mdays = [d for d in mdays if d >= '2026-09-22']                      # 21 Sep has no price path
rows = []
cover = collections.Counter()
for dd in mdays:
    ms, nraw = of_lib.marks(dd)
    BF = bar_feats(dd)
    pbk = of_lib.path(dd)
    for m in ms:
        s = m['sec']
        f = BF.get(s)
        w = None if m['kind'] == 'climax' else (-m['side'] if m['kind'] == 'trap' else m['side'])
        o = of_lib.outcome(pbk, s + 300, w, 0.5, 3600) if (w and pbk) else None
        rows.append(dict(day=dd, era=ERA(dd), kind=m['kind'], side=m['side'], w=w, s=s, size=m['size'], f=f, st=(f['st'] if f else 'NA'), hit=(f['hit'] if f else []),
                         out=(o[0] if o else None), sg=(f['sg'] if f and 'sg' in f else (1 if f and f['d'] > 0 else -1 if f and f['d'] < 0 else 0))))
        cover[(ERA(dd), 'bar' if f else 'no GC bar')] += 1
print('marks on %d days (%s..%s): %d collapsed marks' % (len(mdays), mdays[0], mdays[-1], len(rows)))
for e in 'AB':
    print('  era %s: marks %d, with a GC bar (state available) %d, without %d' % (e, sum(1 for r in rows if r['era'] == e), cover[(e, 'bar')], cover[(e, 'no GC bar')]))
print('  kind counts era A:', dict(collections.Counter(r['kind'] for r in rows if r['era'] == 'A')))
print('  kind counts era B:', dict(collections.Counter(r['kind'] for r in rows if r['era'] == 'B')))
print('  (ORDERFLOW-STUDY era A: trap 103 absorption 200 exhaustion 66 initiative 90 vacuum 37 climax 25 ; era B: 34 / 64 / 28 / 56 / 22 / 17 - the 21 Sep rows are excluded here)')

# how often is a mark bar in each state vs all GC bars
print('\nstate of the bar a mark sits on, vs the state of all bars on the same days (GC-covered)')
for e in 'AB':
    mk = [r for r in rows if r['era'] == e and r['f']]
    base = [b for dd in mdays if ERA(dd) == e for b in bar_feats(dd).values()]
    cm = collections.Counter(r['st'] for r in mk); cb = collections.Counter(b['st'] for b in base)
    print('  era %s marks on a GC bar %d | PUSH %d CLIMAX_a %d CLIMAX_b %d PATLA %d NOISE %d NONE %d   || all bars %d | PUSH %d CLIMAX_a %d CLIMAX_b %d PATLA %d NOISE %d NONE %d' % (
        e, len(mk), cm['PUSH'], cm['CLIMAX_a'], cm['CLIMAX_b'], cm['PATLA'], cm['NOISE'], cm['NONE'], len(base), cb['PUSH'], cb['CLIMAX_a'], cb['CLIMAX_b'], cb['PATLA'], cb['NOISE'], cb['NONE']))

def cells(sel):
    c = collections.Counter(r['out'] for r in sel if r['out'] is not None)
    n = sum(c.values())
    return n, c
def show(nm, sel):
    n, c = cells(sel)
    return '  %-52s n %3d  WITH %3d  AGAINST %3d  TIE %2d  NONE/END %3d' % (nm, n, c['WITH'], c['AGAINST'], c['TIE'], c['NONE'] + c['END'])
REV = ('trap', 'absorption', 'exhaustion')
CLX = ('CLIMAX_a', 'CLIMAX_b')
print('\n=== reversal-type marks (trap, absorption, exhaustion): on a CLIMAX bar vs not ===')
for e in ('A', 'B', 'AB'):
    base = [r for r in rows if r['kind'] in REV and r['f'] and (e == 'AB' or r['era'] == e)]
    print(' era', e)
    print(show('on CLIMAX_a/b bar', [r for r in base if r['st'] in CLX]))
    print(show('  of which CLIMAX_a', [r for r in base if r['st'] == 'CLIMAX_a']))
    print(show('  of which CLIMAX_b', [r for r in base if r['st'] == 'CLIMAX_b']))
    print(show('on a PUSH bar', [r for r in base if r['st'] == 'PUSH']))
    print(show('on a PATLA bar', [r for r in base if r['st'] == 'PATLA']))
    print(show('on a NOISE / NONE bar', [r for r in base if r['st'] in ('NOISE', 'NONE')]))
print('\n=== each reversal kind, era A and B, on CLIMAX vs not (counts only; n small) ===')
for k in REV:
    for e in 'AB':
        base = [r for r in rows if r['kind'] == k and r['f'] and r['era'] == e]
        print(show('%s era %s on CLIMAX_a/b' % (k, e), [r for r in base if r['st'] in CLX]))
        print(show('%s era %s not on CLIMAX' % (k, e), [r for r in base if r['st'] not in CLX]))
print('\n=== initiative / vacuum marks on a PUSH bar vs not ===')
for k in ('initiative', 'vacuum'):
    for e in 'AB':
        base = [r for r in rows if r['kind'] == k and r['f'] and r['era'] == e]
        print(show('%s era %s on PUSH' % (k, e), [r for r in base if r['st'] == 'PUSH']))
        print(show('%s era %s not on PUSH' % (k, e), [r for r in base if r['st'] != 'PUSH']))

# coherence: does a reversal mark on a CLIMAX_a bar name the side AGAINST the spent delta?
print('\ncoherence on CLIMAX_a bars: reversal-type mark winner vs the bar delta (spent side = sign of delta; a reversal mark should be won by the opposite side)')
for e in 'AB':
    sel = [r for r in rows if r['kind'] in REV and r['f'] and r['era'] == e and r['st'] == 'CLIMAX_a' and r['w']]
    opp = sum(1 for r in sel if r['w'] == -r['sg']); same = sum(1 for r in sel if r['w'] == r['sg'])
    print('  era %s: %d marks; winner opposite the spent delta %d, same side %d' % (e, len(sel), opp, same))

# level-hold (0.25U in 60 min) - the way Mary uses marks - for the CLIMAX-coincident reversal marks
def hold(r, thr=0.25):
    p = of_lib.path(r['day'])
    if not p or not r['w']: return None
    T = r['s'] + 300; ends = [b['e'] for b in p]; i = bisect.bisect_right(ends, T) - 1
    if i < 0: return None
    U = of_lib.unit(p[i]['c'], p[i]['sig']); mk = r['f']['c']
    # level = the mark price is not carried here; use the bar extreme against the winner: buyers win -> bar low must hold
    lvl = r['f']['l'] if r['w'] > 0 else r['f']['h']
    for b in p[i + 1:]:
        if b['s'] >= T + 3600: break
        if r['w'] > 0 and b['l'] <= lvl - thr * U: return 'BROKE'
        if r['w'] < 0 and b['h'] >= lvl + thr * U: return 'BROKE'
    return 'HELD'
print('\nlevel hold of the bar extreme the winner needs (0.25U beyond it within 60 min = BROKE) - reversal-type marks, eras pooled')
for nm, sel in (('on CLIMAX_a/b', [r for r in rows if r['kind'] in REV and r['f'] and r['st'] in CLX]), ('not on CLIMAX', [r for r in rows if r['kind'] in REV and r['f'] and r['st'] not in CLX])):
    c = collections.Counter(hold(r) for r in sel); print('  %-16s n %3d HELD %3d BROKE %3d' % (nm, len(sel), c['HELD'], c['BROKE']))
