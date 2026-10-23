"""STUDY 2: CVD / delta on trend days: pullbacks that held vs broke, and divergence at new extremes. Descriptive counts only.
Definitions fixed in ORDERFLOW-STUDY.md before counting."""
import of_lib, json, sys
from of_lib import *
import lib

# (instrument, day, trend direction, source) -- direction by close vs open and VWAP side; 28 Sep and 6 Oct were ADDED by me for n
SETS = [('NIFTY','2026-09-28',-1,'gc','added'), ('NIFTY','2026-10-06',+1,'gc','added'), ('NIFTY','2026-10-08',-1,'gc','given'),
        ('NIFTY','2026-10-09',+1,'gc','given'), ('NIFTY','2026-10-12',-1,'gc','given'), ('NIFTY','2026-10-13',+1,'gc','given'),
        ('NIFTY','2026-10-16',+1,'gc','given'),
        ('BANKNIFTY','2026-09-28',-1,'ux','added'), ('BANKNIFTY','2026-10-06',+1,'ux','added'), ('BANKNIFTY','2026-10-08',-1,'ux','given'),
        ('BANKNIFTY','2026-10-09',+1,'ux','given'), ('BANKNIFTY','2026-10-12',-1,'ux','given')]

def load(idx, day, src):
    if src == 'gc': return gc_bars(day)
    out = []
    for b in lib.ux(idx, day):
        if b.get('c') is None or b.get('o') is None: continue
        out.append(dict(b))
    return out

def run(idx, day, d, src):
    bars = load(idx, day, src)
    if len(bars) < 8: return None
    vw = gc_vwap(bars)
    cvd = []; c = 0.0
    for b in bars: c += b.get('delta') or 0; cvd.append(c)
    # gap flags: a bar missing between i-1 and i
    gap = [False] + [bars[i]['sec'] - bars[i-1]['sec'] > 300 for i in range(1, len(bars))]
    ext = bars[0]['h'] if d > 0 else bars[0]['l']; ext_i = 0
    depth = 0.0; low_i = 0; pbs = []; prev_ext = None; active = False
    def thr(i): return max(0.75*vw[i][1], 15.0)
    def far(b): return b['l'] if d > 0 else b['h']
    skip_to = 0
    for i in range(1, len(bars)):
        if i <= skip_to: continue
        b = bars[i]
        new_ext = (b['h'] > ext) if d > 0 else (b['l'] < ext)
        if new_ext:
            if depth >= thr(i):
                pbs.append(dict(start=ext_i, low=low_i, end=i, depth=depth, res='HELD'))
                prev_ext = far(bars[low_i])
            ext = b['h'] if d > 0 else b['l']; ext_i = i; depth = 0.0; low_i = i
            continue
        cd = (ext - b['l']) if d > 0 else (b['h'] - ext)
        if cd > depth: depth = cd; low_i = i
        sg = vw[i][1]; v = vw[i][0]
        beyond = lambda k: ((bars[k]['c'] < vw[k][0] - 0.25*vw[k][1]) if d > 0 else (bars[k]['c'] > vw[k][0] + 0.25*vw[k][1]))
        vwap_break = i >= 1 and beyond(i) and beyond(i-1) and depth >= thr(i)*0.5
        struct_break = prev_ext is not None and ((b['c'] < prev_ext - 5) if d > 0 else (b['c'] > prev_ext + 5)) and depth >= thr(i)
        if vwap_break or struct_break:
            pbs.append(dict(start=ext_i, low=low_i, end=i, depth=depth, res='BROKE', why='VWAP' if vwap_break else 'prev swing'))
            # re-arm only after a close back on the trend side of VWAP (one chop episode = one BROKE)
            j = i
            while j < len(bars) and not ((bars[j]['c'] > vw[j][0]) if d > 0 else (bars[j]['c'] < vw[j][0])): j += 1
            if j >= len(bars): ext = None; break
            ext = bars[j]['h'] if d > 0 else bars[j]['l']; ext_i = j; depth = 0.0; low_i = j; prev_ext = None
            skip_to = j
    if ext is not None and depth >= thr(len(bars)-1): pbs.append(dict(start=ext_i, low=low_i, end=len(bars)-1, depth=depth, res='OPEN'))
    # CVD features
    for p in pbs:
        s, l = p['start'], p['low']
        pre = cvd[max(0, s-12):s+1]
        p['gap'] = any(gap[k] for k in range(max(1, s-12), min(len(bars), p['end']+1)))
        p['cvd_dir'] = d*(cvd[l] - cvd[s])                     # <0: CVD moved AGAINST the trend during the pullback
        # new CVD extreme against the trend vs the prior 60 min (up trend: lower low in CVD)
        p['cvd_newlow'] = (cvd[l] < min(pre)) if d > 0 else (cvd[l] > max(pre))
        p['t0'] = hm(bars[s]['sec']); p['t1'] = hm(bars[l]['sec'])
        p['volsum'] = sum(b.get('vol') or 0 for b in bars[s:l+1])
    # extremes and divergence
    exs = []
    best = None
    for i, b in enumerate(bars):
        px = b['h'] if d > 0 else b['l']
        if best is None or ((px > best) if d > 0 else (px < best)):
            best = px
            prior = cvd[max(0, i-12):i]
            confirmed = True if not prior else ((cvd[i] >= max(prior)) if d > 0 else (cvd[i] <= min(prior)))
            exs.append(dict(i=i, t=hm(b['sec']), confirmed=confirmed, gap=gap[i] or any(gap[max(1, i-12):i+1])))
    for k, e in enumerate(exs):
        # further extreme within the next 12 bars?
        t_i = e['i']; px = bars[t_i]['h'] if d > 0 else bars[t_i]['l']
        e['cont'] = any(((bars[j]['h'] > px) if d > 0 else (bars[j]['l'] < px)) for j in range(t_i+1, min(len(bars), t_i+13)))
        e['last'] = (k == len(exs)-1)
    return dict(idx=idx, day=day, d=d, n=len(bars), first=hm(bars[0]['sec']), last=hm(bars[-1]['sec']), gaps=sum(gap), pbs=pbs, exs=exs)

res = [r for r in (run(i, dd, d, s) + (None,) if False else run(i, dd, d, s) for (i, dd, d, s, tag) in SETS) if r]
out = []; P = out.append
P('STUDY 2: coverage (bars used; gaps = missing 5-min bars inside the span)')
for r in res: P('  %-9s %s dir %+d %s..%s bars %d gaps %d | qualified pullbacks %d | new-extreme bars %d' % (r['idx'], r['day'][5:], r['d'], r['first'], r['last'], r['n'], r['gaps'], len(r['pbs']), len(r['exs'])))
P('')
for idx in ['NIFTY', 'BANKNIFTY']:
    pb = [(r, p) for r in res if r['idx'] == idx for p in r['pbs'] if not p['gap'] and p['res'] != 'OPEN']
    P('=== %s: qualified pullbacks (depth >= max(0.75 sigma, 15 pts)), no data gap inside: n=%d ===' % (idx, len(pb)))
    for res_ in ['HELD', 'BROKE']:
        s = [p for r, p in pb if p['res'] == res_]
        P('  %-5s n=%2d | CVD moved AGAINST the trend during the pullback %d | CVD moved WITH the trend %d | CVD made a new 60-min extreme against the trend %d | CVD held inside its prior 60-min range %d' % (
            res_, len(s), sum(1 for p in s if p['cvd_dir'] < 0), sum(1 for p in s if p['cvd_dir'] >= 0), sum(1 for p in s if p['cvd_newlow']), sum(1 for p in s if not p['cvd_newlow'])))
    P('  rows:')
    for r, p in pb: P('    %s %s..%s depth %.0f %s | cvd_dir %+.0f newCVDext %s%s' % (r['day'][5:], p['t0'], p['t1'], p['depth'], p['res'] + ('(' + p.get('why', '') + ')' if p['res'] == 'BROKE' else ''), p['cvd_dir'], p['cvd_newlow'], ''))
    P('')
    P('=== %s: new trend-extreme bars: CVD confirmed vs diverged x further extreme within 60 min ===' % idx)
    ex = [(r, e) for r in res if r['idx'] == idx for e in r['exs'] if not e['gap'] and not e['last'] and e['i'] >= 12] if False else [(r, e) for r in res if r['idx'] == idx for e in r['exs'] if not e['gap']]
    # exclude the final extreme of each day (nothing can follow it by definition) from the 'continued' split, and bars within 60 min of the end of data
    ex2 = []
    for r, e in ex:
        if e['last']: continue
        ex2.append((r, e))
    for conf in (True, False):
        s = [e for r, e in ex2 if e['confirmed'] == conf]
        P('  CVD %-9s n=%3d | price made a further extreme within 60 min %3d | did not %3d' % ('confirmed' if conf else 'DIVERGED', len(s), sum(1 for e in s if e['cont']), sum(1 for e in s if not e['cont'])))
    P('  the DAY-FINAL extreme of each day (within the bars we have): ')
    for r in [r for r in res if r['idx'] == idx]:
        last = r['exs'][-1]
        P('    %s final extreme %s | CVD %s | within data %s..%s (gap near: %s)' % (r['day'][5:], last['t'], 'confirmed' if last['confirmed'] else 'DIVERGED', r['first'], r['last'], last['gap']))
    P('')
open('study2_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
json.dump([dict(idx=r['idx'], day=r['day'], pbs=r['pbs'], exs=r['exs']) for r in res], open('study2_rows.json', 'w'))
print('\n'.join(out))
