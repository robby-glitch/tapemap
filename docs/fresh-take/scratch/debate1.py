"""Debate round 1 checks. Descriptive only: no P&L, no outcomes. Uses replay() recs (causal)."""
from seq import *
import collections

def asym_shown(recs, n_fast=2, n_slow=10):
    """veto fast, permit slow: switching INTO a directional state (TREND/LEAN/TURN) needs n_fast minutes;
    switching into anything else (CHOP/PIN/UNCLEAR) or flipping direction needs n_slow."""
    shown = None; cand = None; cnt = 0; out = {}
    for T in sorted(recs):
        r = recs[T]; key = (r['regime'], r['dir'], r.get('pin'))
        if shown is None:
            shown = key
        elif key != shown:
            cnt = cnt + 1 if key == cand else 1
            cand = key
            need = n_fast if (key[0] in ('TREND', 'LEAN') and shown[0] in ('UNCLEAR', 'CHOP', 'PIN')) else n_slow
            if cnt >= need:
                shown = key; cand = None; cnt = 0
        else:
            cand = None; cnt = 0
        out[T] = shown
    return out

def touches(recs, level):
    """first minute of each episode where z crosses beyond +-level (from inside)"""
    ev = []; inside = True; side = 0
    for T in sorted(recs):
        r = recs[T]
        if not r['ready']: continue
        z = r['z']
        if inside and abs(z) >= level:
            ev.append((T, 1 if z > 0 else -1)); inside = False
        elif not inside and abs(z) < level - 0.25:
            inside = True
    return ev

tot = collections.Counter(); rows = []
sw_a = []; sw_s = []
for idx in IDXS:
    for day in DAYS:
        if day == '2026-10-07': continue
        d, rl, recs = replay(idx, day)
        if not recs: continue
        A = asym_shown(recs)
        sw_s.append(sum(1 for a, b in zip(sorted(recs), sorted(recs)[1:]) if recs[a]['shown'] != recs[b]['shown']))
        ks = sorted(recs)
        sw_a.append(sum(1 for a, b in zip(ks, ks[1:]) if A[a] != A[b]))
        for T, sd in touches(recs, float(__import__("sys").argv[1]) if len(__import__("sys").argv)>1 else 2.0):
            r = recs[T]
            # a touch at -2 sigma (sd=-1) is a BUY-the-band event; veto if state says trend/lean DOWN (or turn is not veto)
            def veto(k):
                return k[0] in ('TREND', 'LEAN') and k[1] == sd
            tot['touches'] += 1
            tot['veto_raw'] += veto((r['regime'], r['dir'], None))
            tot['veto_shown'] += veto(r['shown'])
            tot['veto_asym'] += veto(A[T])
            tot['unclear_shown'] += (r['shown'][0] == 'UNCLEAR')
            if idx == 'NIFTY' and day == '2026-10-08':
                rows.append((fmt(T), 'z%+.1f' % r['z'], 'raw', r['regime'], r['dir'], 'shown', r['shown'][:2], 'asym', A[T][:2]))
print('touches of +-2 sigma episodes over 33 index-days:', dict(tot))
print('switches/day shown(10) median', sorted(sw_s)[len(sw_s)//2], ' asym median', sorted(sw_a)[len(sw_a)//2])
print('NIFTY 8 Oct +-2sigma episodes:')
for r in rows: print('  ', r)
# lateness on 8 Oct: first minute each variant says TREND/LEAN down
d, rl, recs = replay('NIFTY', '2026-10-08'); A = asym_shown(recs)
def first(f):
    for T in sorted(recs):
        if f(T): return fmt(T)
print('8 Oct first raw LEAN/TREND dn', first(lambda T: recs[T]['regime'] in ('LEAN', 'TREND') and recs[T]['dir'] == -1),
      '| shown(10)', first(lambda T: recs[T]['shown'][0] in ('LEAN', 'TREND') and recs[T]['shown'][1] == -1),
      '| asym', first(lambda T: A[T][0] in ('LEAN', 'TREND') and A[T][1] == -1))
# first minute z <= -1 and <= -2
print('8 Oct first z<=-1', first(lambda T: recs[T]['ready'] and recs[T]['z'] <= -1), 'first z<=-2', first(lambda T: recs[T]['ready'] and recs[T]['z'] <= -2))
