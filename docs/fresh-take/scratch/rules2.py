# Regime (slow) + Phase (fast) + Flip-watch. Causal: uses only data <= T. Constants in C are the only knobs.
from engine import *
import math

C = dict(WIN_LOC=1800, WIN_OI=1800, WIN_PH=900, BANDS_AT=9*3600+45*60, SIDE=0.80, CROSS_N=2, CROSS_WIN=2700,
         SCHMITT=0.25, WEAK=0.4, MAT_OI=0.005, MAT_FLOW=0.03, MIN_SPAN=600, STOP_FRAC=0.25, STOP_MIN_PEAK=0.003,
         PIN_USED=0.6, DISP=0.6, PIN_NEAR=0.5, PIN_AFTER=10*3600+15*60)
OPEN_DATA = 9*3600+20*60


def minutes(d):
    if hasattr(d, '_m'):
        return d._m
    out = []
    for T in range(9*3600+16*60, 15*3600+31*60, 60):
        t = d.tick(T)
        if t:
            out.append((T, t[1], t[2], t[3], t[4]))
    d._m = out
    return out


def day_range(idx, day):
    d = Day(idx, day)
    if not d.v or d.v[0][0] > 9*3600+30*60:
        return None
    P = [x[1] for x in d.v if x[0] <= 15*3600]
    return max(P) - min(P)


_ruler_cache = {}


def ruler_for(idx, day):
    """mean H-L of up to 3 previous COMPLETE sessions (fut). None if no history."""
    if idx not in _ruler_cache:
        _ruler_cache[idx] = {dd: day_range(idx, dd) for dd in DAYS}
    prev = [_ruler_cache[idx][dd] for dd in DAYS if dd < day and _ruler_cache[idx][dd]]
    prev = prev[-3:]
    return sum(prev)/len(prev) if prev else None


def sgn(x, thr=0):
    return 1 if x > thr else (-1 if x < -thr else 0)


def crossings(zs):
    cr = 0
    st = 0
    for z in zs:
        if z > C['SCHMITT']:
            if st == -1:
                cr += 1
            st = 1
        elif z < -C['SCHMITT']:
            if st == 1:
                cr += 1
            st = -1
    return cr


def side_oi(sn):
    a = sn['atm']
    return (sum(v['oi'] for k, v in sn['ce'].items() if k >= a), sum(v['oi'] for k, v in sn['pe'].items() if k <= a))


def writers(d, T, W, sn):
    ce, pe, span = d.oi_flow(T, W)
    bce, bpe = side_oi(sn)
    if span < C['MIN_SPAN'] and W >= C['WIN_OI']:
        return None, ce, pe, span
    mce = ce > C['MAT_OI']*bce
    mpe = pe > C['MAT_OI']*bpe
    if mce and (not mpe or pe <= C['WEAK']*ce):
        v = -1
    elif mpe and (not mce or ce <= C['WEAK']*pe):
        v = 1
    elif mce and mpe:
        v = 0
    else:
        v = 'dry'
    return v, ce, pe, span


def peak10(d, T, side):
    """largest 10-min OTM flow on side ('ce'/'pe') seen so far today (grid 5 min), as fraction of side OI"""
    best = 0.0
    t = max(d.ts0 + 600, OPEN_DATA)
    while t <= T:
        ce, pe, sp = d.oi_flow(t, 600)
        sn = d.snap(t)
        bce, bpe = side_oi(sn)
        x = (ce/bce) if side == 'ce' else (pe/bpe)
        best = max(best, x)
        t += 300
    return best


def read(d, T, ruler=None):
    t = d.tick(T)
    sn = d.snap(T)
    o = dict(T=T)
    if not t or not sn or T < OPEN_DATA:
        o['regime'] = 'WAIT'
        o['phase'] = ''
        o['dir'] = 0
        return o
    M = [m for m in minutes(d) if m[0] <= T]
    F, vw, sg = t[1], t[2], t[3]
    start = d.v[0][0]
    partial = start > 9*3600+30*60
    ready = (T - start) >= 1800
    el = max(T - (9*3600+15*60), 60)/60.0
    scale = math.sqrt(min(el, 375)/375.0)
    z = (F - vw)/sg if sg > 0 else 0.0
    o.update(F=F, vwap=vw, sigma=sg, z=z, ready=ready, spot=sn['spot'], basis=F - sn['spot'], atm=sn['atm'])
    win = [m for m in M if m[0] > T - C['WIN_LOC']]
    sh = [sgn(m[1]-m[2]) for m in win]
    up = sum(1 for s_ in sh if s_ > 0)/max(len(sh), 1)
    dn = sum(1 for s_ in sh if s_ < 0)/max(len(sh), 1)
    loc = None if len(win) < 10 else (1 if up >= C['SIDE'] else (-1 if dn >= C['SIDE'] else 0))
    o.update(loc=loc, up_share=up, dn_share=dn, nwin=len(win))
    zs = [((m[1]-m[2])/m[3] if m[3] > 0 else 0) for m in M if m[0] > T - C['CROSS_WIN']]
    cr = crossings(zs) if ready else None
    o['cross'] = cr
    wr, ce, pe, span = writers(d, T, C['WIN_OI'], sn)
    o.update(wr=wr, ce30=ce, pe30=pe, span=span)
    if not hasattr(d, '_pmax'):
        pm = []; pn = []; a = -1e18; b = 1e18
        for x in d.v:
            a = max(a, x[1]); b = min(b, x[1]); pm.append(a); pn.append(b)
        d._pmax, d._pmin = pm, pn
    ii = bisect.bisect_right(d.vs, T) - 1
    o['hi'] = d._pmax[ii]
    o['lo'] = d._pmin[ii]
    o['range'] = o['hi'] - o['lo']
    if not ruler:
        iv_ = d.atm_iv(sn)
        ruler = 1.6*iv_*F/math.sqrt(252) if iv_ else None
    o['ruler'] = ruler
    o['partial'] = partial
    o['used'] = (o['range']/(ruler*scale)) if (ruler and not partial) else None
    o['open'] = d.v[0][1]
    o['disp'] = ((F - d.v[0][1])/(ruler*scale)) if (ruler and not partial) else None
    d15, v15, n15 = d.delta_sum(T, C['WIN_PH'])
    d30, v30, n30 = d.delta_sum(T, C['WIN_LOC'])
    o.update(d15=d15, v15=v15, d30=d30, v30=v30)
    fl15 = sgn(d15/v15, C['MAT_FLOW']) if n15 >= 2 and v15 else None
    o['fl15'] = fl15
    m15 = [m for m in M if m[0] <= T - C['WIN_PH']]
    dp15 = F - m15[-1][1] if m15 else None
    o['dp15'] = dp15
    m30 = [m for m in M if m[0] <= T - C['WIN_LOC']]
    if m30:
        o['foi'] = (sgn(F - m30[-1][1]), sgn(t[4] - m30[-1][4]), F - m30[-1][1], t[4] - m30[-1][4])
    else:
        o['foi'] = None
    iv = d.atm_iv(sn)
    o['iv'] = iv
    if iv and m30:
        pr = iv*F*math.sqrt(30/94500)
        o['priced30'] = pr
        o['moved30'] = abs(F - m30[-1][1])/pr
    # ---- regime
    reg = 'UNCLEAR'
    dr_ = 0
    if loc is not None and wr is not None:
        if loc in (1, -1):
            if wr == loc and o['disp'] is not None and o['disp']*loc >= C['DISP']:
                reg = 'TREND'
                dr_ = loc
            elif wr == loc:
                reg = 'LEAN'
                dr_ = loc
            elif wr in (0, 'dry'):
                reg = 'LEAN'
                dr_ = loc
            else:
                reg = 'TURN'
                dr_ = loc
        else:
            if ready and cr is not None and cr >= C['CROSS_N']:
                reg = 'CHOP'
    o['pin'] = None
    if reg in ('CHOP', 'UNCLEAR') and T >= C['PIN_AFTER'] and o['used'] is not None:
        step = STEP[d.idx]
        near = [k for k in sn['ce'] if abs(k - sn['spot']) <= 2*step and k in sn['pe']]
        if near:
            kstar = max(near, key=lambda k: min(sn['ce'][k]['oi'], sn['pe'][k]['oi']))
            o['kstar'] = kstar
            if o['used'] < C['PIN_USED'] and abs(sn['spot'] - kstar) <= C['PIN_NEAR']*step and (loc == 0 or (cr is not None and cr >= 1)):
                reg = 'PIN'
                o['pin'] = kstar
    o['regime'] = reg
    o['dir'] = dr_
    ph = ''
    if reg in ('TREND', 'LEAN') and fl15 is not None and dp15 is not None:
        with_ = (fl15 == dr_)
        against = (fl15 == -dr_)
        movedwith = sgn(dp15*dr_, 0.15*sg if sg else 0)
        if against and movedwith <= 0:
            ph = 'PULLBACK'
        elif with_ and movedwith >= 0:
            ph = 'PUSH'
        else:
            ph = 'PAUSE'
    o['flip'] = False
    if reg in ('TREND', 'LEAN') and T - d.ts0 >= 3600:
        side = 'ce' if dr_ == -1 else 'pe'
        bce, bpe = side_oi(sn)
        base = bce if side == 'ce' else bpe
        def fs(t_, W):
            f = d.oi_flow(t_, W)
            return f[0] if side == 'ce' else f[1]
        now20 = fs(T, 1200)
        prev40 = fs(T - 1200, 2400)
        o['stop'] = (round(now20/base*100, 2), round(prev40/base*100, 2))
        if prev40 >= C['MAT_OI']*base and now20 <= C['STOP_FRAC']*(prev40/2):
            o['flip'] = True
    o['phase'] = ph
    return o
