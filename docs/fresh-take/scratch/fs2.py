"""FS2 - FLOW STATE rules made concrete, run on GC NIFTY (17 days), then outcomes vs comparators. Descriptive. SEEN.
Definitions are fixed in fs_lib.state() BEFORE the first outcome table was printed. Added/flagged choices are listed in the study file."""
import numpy as np
import of_lib
from fs_lib import *

days = gc_days(); ref = Ref(days)
PB = {}
def pb(day):
    if day not in PB: PB[day] = of_lib.path(day)
    return PB[day]

def run(res_min=RES_MIN, quiet=False):
    rows = label_all(ref, res_min=res_min)
    return rows
rows = run()
n = len(rows)
cnt = collections.Counter(r['st'] for r in rows)
print('=== 17 days, %d bars. State counts (priority PUSH > CLIMAX_a > CLIMAX_b > PATLA > NOISE > NONE):' % n)
for k in ('PUSH', 'CLIMAX_a', 'CLIMAX_b', 'PATLA', 'NOISE', 'NONE'): print('  %-9s %4d' % (k, cnt[k]))
multi = collections.Counter(tuple(r['hit']) for r in rows if len(r['hit']) > 1)
print('  bars satisfying 2+ rules before priority:', sum(multi.values()), dict(multi))
nores = sum(1 for r in rows if r['res'] is None); print('  bars with no price result (missing o/c or range base):', nores)
res = np.array([r['res'] for r in rows if r['res'] is not None])
print('  price result R (signed, in slot-typical ranges): p10 %.2f p25 %.2f p50 %.2f p75 %.2f p90 %.2f; share R<0.25: %d of %d; R<0 (price against the delta): %d' % (*np.quantile(res, [.1, .25, .5, .75, .9]), (res < .25).sum(), len(res), (res < 0).sum()))
big = [r for r in rows if r['res'] is not None and abs(r['d']) >= ref.TH[r['day']]['d']['p90']]
print('  bars with |delta|>=p90 (LODO) and a price result: %d; R<0.25 in %d; R<0 in %d; R>=0.25 in %d' % (len(big), sum(r['res'] < .25 for r in big), sum(r['res'] < 0 for r in big), sum(r['res'] >= .25 for r in big)))
for rm in (0.0, 0.5):
    c2 = collections.Counter(r['st'] for r in run(rm))
    print('  sensitivity res_min=%.2f: PUSH %d CLIMAX_a %d CLIMAX_b %d PATLA %d NOISE %d NONE %d' % (rm, c2['PUSH'], c2['CLIMAX_a'], c2['CLIMAX_b'], c2['PATLA'], c2['NOISE'], c2['NONE']))
c3 = collections.Counter(r['st'] for r in label_all(ref, need_sign=False))
print('  without the sign-agreement requirement on slope/acc: PUSH %d (vs %d)' % (c3['PUSH'], cnt['PUSH']))

print('\nper-day state counts')
print('  day        wd   bars PUSH CL_a CL_b PATLA NOISE NONE')
for dd in days:
    c = collections.Counter(r['st'] for r in rows if r['day'] == dd)
    print('  %s %s %5d %4d %4d %4d %5d %5d %4d' % (dd, wd(dd), sum(c.values()), c['PUSH'], c['CLIMAX_a'], c['CLIMAX_b'], c['PATLA'], c['NOISE'], c['NONE']))

# ------------------------------------------------------------------ the hand-picked moments of spec section 4 under the concrete rules
print('\nspec illustrative moments under the concrete rules (SEEN; LODO thresholds; GC rows)')
want = (('2026-10-09', '10:15'), ('2026-10-09', '11:20'), ('2026-10-09', '12:00'), ('2026-10-09', '12:30'), ('2026-10-12', '09:50'), ('2026-10-12', '10:15'), ('2026-10-12', '10:30'))
for dd, tt in want:
    r = next((x for x in rows if x['day'] == dd and hm(x['s']) == tt), None)
    if not r: print(' ', dd, tt, 'no bar'); continue
    P = ref.P[dd]
    print('  %s %s state %-8s hit %s | d %+5.0f (p%s) rv %s (p%s) vacc %s slope %s acc %s R %s' % (dd, tt, r['st'], r['hit'], r['d'], rank(P, 'd', r['d']), None if r['rv'] is None else round(r['rv'], 1), rank(P, 'rv', r['rv']),
          None if r['vacc'] is None else round(r['vacc'], 1), None if r['slope'] is None else round(r['slope'], 1), None if r['acc'] is None else round(r['acc'], 1), None if r['res'] is None else round(r['res'], 2)))
# 13 and 16 Oct are short days: features vs the 17-day pooled thresholds
ext = gc_all()
for dd, tts in (('2026-10-13', ('09:15', '09:45')), ('2026-10-16', ('09:15', '09:35', '10:10', '10:15'))):
    bv, br = bases(days, set()); F = feats(ext[dd], bv, br)
    th = {k: dict(p50=q(ref.POOL[k], .5), p70=q(ref.POOL[k], .7), p90=q(ref.POOL[k], .9)) for k in KEYS}
    for r in F:
        if hm(r['s']) in tts:
            st, sg, hit = state(r, th)
            print('  %s %s state %-8s hit %s | d %+5.0f rv %s vacc %s slope %s acc %s R %s' % (dd, hm(r['s']), st, hit, r['d'], None if r['rv'] is None else round(r['rv'], 1), None if r['vacc'] is None else round(r['vacc'], 1), None if r['slope'] is None else round(r['slope'], 1), None if r['acc'] is None else round(r['acc'], 1), None if r['res'] is None else round(r['res'], 2)))

# ------------------------------------------------------------------ outcomes
def hi60(r, days_bars):
    """is the bar at a 60-min extreme in the effort direction (high >= max of prior 12 bars' highs if buying; low <= min if selling)"""
    F = days_bars[r['day']]; i = r['i']
    if i < 12 or r['_w'] == 0: return None
    prev = F[i - 12:i]
    if r['_w'] > 0: return r['h'] >= max(x['h'] for x in prev)
    return r['l'] <= min(x['l'] for x in prev)

def direction(r):
    if r['st'] == 'CLIMAX_b' or r['_cls'] == 'CLB':
        return 0 if not r['ret15'] else (1 if r['ret15'] > 0 else -1)
    return r['sg']

def lab(r, w, shift=0, horizon=3600):
    p = pb(r['day'])
    if not p or w == 0: return None
    o = of_lib.outcome(p, r['s'] + 300 + shift * 300, w, 0.5, horizon)
    return o

def fwdU(r, w, shift=0, minutes=30):
    p = pb(r['day'])
    if not p or w == 0: return None
    T = r['s'] + 300 + shift * 300
    ends = [b['e'] for b in p]; i = bisect.bisect_right(ends, T) - 1; j = bisect.bisect_right(ends, T + minutes * 60) - 1
    if i < 0 or j <= i or p[j]['e'] < T + minutes * 60 - 180: return None
    return w * (p[j]['c'] - p[i]['c']) / of_lib.unit(p[i]['c'], p[i]['sig'])

TESTDAYS = [d for d in days if d >= '2026-09-22']
th_of = lambda r: ref.TH[r['day']]
for r in rows:
    r['_w'] = r['sg']
    r['_cls'] = ''
dayF = ref.F
def groups(rows):
    G = collections.defaultdict(list)
    for r in rows:
        if r['day'] not in TESTDAYS or r['res'] is None: continue
        th = th_of(r)
        bigd = abs(r['d']) >= th['d']['p90']
        volspike = (r['rv'] is not None and r['rv'] >= th['rv']['p90']) or (r['vacc'] is not None and r['vacc'] >= th['vacc']['p90'])
        G['ALL'].append(r)
        if r['st'] == 'PUSH': G['PUSH'].append(r)
        if r['st'] == 'CLIMAX_a': G['CLIMAX_a'].append(r)
        if r['st'] == 'CLIMAX_b': G['CLIMAX_b'].append(r)
        if r['st'] == 'PATLA': G['PATLA'].append(r)
        if bigd and r['res'] >= RES_MIN and r['st'] not in ('PUSH',): G['BIG_other'].append(r)         # big delta, price moved, but no slope/acc/volume confirmation
        if volspike and abs(r['d']) > th['d']['p70'] and r['st'] not in ('CLIMAX_b',): G['VOL_other'].append(r)
        if r['rv'] is not None and r['rv'] < th['rv']['p70'] and r['st'] != 'PATLA': G['LOWVOL_other'].append(r)
    return G
G = groups(rows)
def w_for(grp, r):
    if grp in ('CLIMAX_b', 'VOL_other'): return 0 if not r['ret15'] else (1 if r['ret15'] > 0 else -1)
    return r['sg']
def table(grp, shift=None, horizon=3600):
    c = collections.Counter(); fw = []
    for r in G[grp]:
        w = w_for(grp, r)
        if w == 0: continue
        shifts = [shift] if shift is not None else [0]
        for sh in shifts:
            o = lab(r, w, sh, horizon)
            if o is None: continue
            c[o[0]] += 1
            f = fwdU(r, w, sh)
            if f is not None: fw.append(f)
    return c, fw
def line(nm, c, fw):
    tot = sum(c.values())
    f = (' | fwd30 median %+.2fU, IQR %+.2f..%+.2f, positive %d of %d' % (np.median(fw), *np.quantile(fw, [.25, .75]), sum(x > 0 for x in fw), len(fw))) if fw else ''
    return '  %-34s n %3d  WITH %3d  AGAINST %3d  TIE %2d  NONE/END %3d%s' % (nm, tot, c['WITH'], c['AGAINST'], c['TIE'], c['NONE'] + c['END'], f)

print('\n=== OUTCOMES (0.5U first within 60 min, U = max(VWAP sigma, 0.1%% of price); direction w = sign of the effort; WITH = price goes w; days %s..%s) ===' % (TESTDAYS[0], TESTDAYS[-1]))
print('PUSH hypothesis: WITH (continuation).  CLIMAX hypothesis: AGAINST (a turn against the spent / absorbed side).')
for grp in ('PUSH', 'CLIMAX_a', 'CLIMAX_b', 'PATLA'):
    c, fw = table(grp); print(line(grp + ' (state)', c, fw))
    # shifted-time placebo: same bars, same w, +-30 and +-60 min
    cs, fs = collections.Counter(), []
    for sh in (-12, -6, 6, 12):
        c1 = collections.Counter();
        for r in G[grp]:
            w = w_for(grp, r)
            if w == 0: continue
            o = lab(r, w, sh)
            if o is None: continue
            c1[o[0]] += 1
            f = fwdU(r, w, sh)
            if f is not None: fs.append(f)
        cs.update(c1)
    print(line(grp + ' shifted +-30/60 min', cs, fs))
for grp in ('BIG_other', 'VOL_other', 'LOWVOL_other', 'ALL'):
    c, fw = table(grp); print(line(grp + ' (comparator)', c, fw))
print('  (BIG_other = |delta|>=p90, price result >= 0.25, not PUSH. VOL_other = volume spike with |delta|>p70, not CLIMAX_b. LOWVOL_other = RVOL<p70, not PATLA. ALL = every bar with a price result; direction = sign(delta), or prior-15-min price move for the CLIMAX_b and VOL_other rows.)')

# at-extreme split
print('\nat a 60-min extreme in the effort direction (high >= prior 12 bars highs when w>0 / low <= prior 12 lows when w<0)')
for grp in ('PUSH', 'CLIMAX_a', 'CLIMAX_b', 'BIG_other', 'ALL'):
    for flag in (True, False):
        c = collections.Counter(); fw = []
        for r in G[grp]:
            w = w_for(grp, r)
            if w == 0: continue
            r['_w'] = w
            e = hi60(r, ref.F)
            if e is None or e != flag: continue
            o = lab(r, w);
            if o is None: continue
            c[o[0]] += 1
            f = fwdU(r, w)
            if f is not None: fw.append(f)
        print(line('%s %s' % (grp, 'AT extreme' if flag else 'not at extreme'), c, fw))

# sensitivity: R threshold
print('\nsensitivity to the price-result cut (res_min) - PUSH and CLIMAX_a only')
for rm in (0.0, 0.5):
    rws = run(rm);
    for r in rws: r['_w'] = r['sg']; r['_cls'] = ''
    for grp in ('PUSH', 'CLIMAX_a'):
        c = collections.Counter()
        for r in rws:
            if r['st'] != grp or r['day'] not in TESTDAYS or r['res'] is None: continue
            o = lab(r, r['sg']);
            if o: c[o[0]] += 1
        print('  res_min %.2f %-9s n %3d WITH %3d AGAINST %3d TIE %2d NONE/END %3d' % (rm, grp, sum(c.values()), c['WITH'], c['AGAINST'], c['TIE'], c['NONE'] + c['END']))

# list of CLIMAX_a bars for eyeballing (trader read)
print('\nCLIMAX_a and PUSH bars on test days (day time delta R rv  -> outcome w=sign(d))')
for grp in ('PUSH', 'CLIMAX_a'):
    print(' ', grp)
    for r in G[grp]:
        o = lab(r, r['sg'])
        print('    %s %s d %+5.0f R %+.2f rv %.1f %s' % (r['day'][5:], hm(r['s']), r['d'], r['res'], r['rv'] or 0, o[0] if o else None))
