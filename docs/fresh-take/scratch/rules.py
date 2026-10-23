# First-principles state rules. All constants listed here are the ONLY knobs. Causal: uses data <= T.
from engine import *
import math

C = dict(WIN_LOC=1800, WIN_OI=1800, WIN_STOP=600, BANDS_AT=9*3600+45*60, SIDE=0.80, CROSS_N=2, CROSS_WIN=2700,
         SCHMITT=0.25, WEAK=0.25, MAT_OI=0.005, MAT_FLOW=0.03, MIN_SPAN=600)
OPEN_DATA = 9*3600+20*60

def minutes(d):
    """1-min series of (sec, F, vwap, sigma) from ticks"""
    if hasattr(d, '_m'): return d._m
    out = []
    for T in range(9*3600+16*60, 15*3600+31*60, 60):
        t = d.tick(T)
        if t: out.append((T, t[1], t[2], t[3], t[4]))
    d._m = out
    return out

def crossings(zs):
    cr = 0; st = 0
    for z in zs:
        if z > C['SCHMITT']:
            if st == -1: cr += 1
            st = 1
        elif z < -C['SCHMITT']:
            if st == 1: cr += 1
            st = -1
    return cr

def sgn(x, thr=0): return 1 if x > thr else (-1 if x < -thr else 0)

def read(d, T, ruler=None):
    t = d.tick(T); sn = d.snap(T)
    out = dict(T=T)
    if not t or not sn or T < OPEN_DATA:
        out['state'] = 'WAIT'; return out
    M = [m for m in minutes(d) if m[0] <= T]
    F, vw, sg = t[1], t[2], t[3]
    ready = T >= C['BANDS_AT']
    z = (F - vw)/sg if sg > 0 else 0.0
    out.update(F=F, vwap=vw, sigma=sg, z=z, ready=ready, spot=sn['spot'], basis=F - sn['spot'])
    # ---- 1 location
    win = [m for m in M if m[0] > T - C['WIN_LOC']]
    side_hist = [sgn(m[1]-m[2]) for m in win]
    up = sum(1 for s_ in side_hist if s_ > 0)/max(len(side_hist), 1)
    dn = sum(1 for s_ in side_hist if s_ < 0)/max(len(side_hist), 1)
    loc = 1 if up >= C['SIDE'] else (-1 if dn >= C['SIDE'] else 0)
    if len(win) < 10: loc_ok = False
    else: loc_ok = True
    out.update(loc=loc if loc_ok else None, up_share=up, dn_share=dn)
    zs = [((m[1]-m[2])/m[3] if m[3] > 0 else 0) for m in M if m[0] > T - C['CROSS_WIN']]
    cr = crossings(zs) if ready else None
    out['cross'] = cr
    # ---- 2 writers
    f = d.oi_flow(T, C['WIN_OI'])
    ce, pe, span = f
    base_ce = sum(v['oi'] for k, v in sn['ce'].items() if k >= sn['atm'])
    base_pe = sum(v['oi'] for k, v in sn['pe'].items() if k <= sn['atm'])
    out.update(ce30=ce, pe30=pe, span=span)
    if span < C['MIN_SPAN']:
        wr = None
    else:
        mce = ce > C['MAT_OI']*base_ce; mpe = pe > C['MAT_OI']*base_pe
        if mce and (not mpe or pe <= C['WEAK']*ce): wr = -1          # only call writing -> bearish
        elif mpe and (not mce or ce <= C['WEAK']*pe): wr = 1         # only put writing -> bullish
        elif mce and mpe: wr = 0                                     # both sides
        else: wr = 'dry'
    out['wr'] = wr
    # ---- 3 flow
    ds, vs, nb = d.delta_sum(T, C['WIN_LOC'])
    out.update(delta=ds, dvol=vs)
    fl = None if nb < 2 else sgn(ds/vs if vs else 0, C['MAT_FLOW'])
    out['fl'] = fl
    # ---- 4 fut OI vs price
    m0 = [m for m in M if m[0] <= T - C['WIN_LOC']]
    if m0:
        dp = F - m0[-1][1]; doi = t[4] - m0[-1][4]
        out['foi'] = (sgn(dp, 0), sgn(doi, 0), dp, doi)
    else: out['foi'] = None
    # ---- 5 range used
    day = [m[1] for m in M]
    out['range'] = max(day) - min(day)
    out['ruler'] = ruler
    out['used'] = out['range']/ruler if ruler else None
    # ---- 6 gauge moved vs priced (30m)
    iv = d.atm_iv(sn)
    if iv and m0:
        pr = iv*F*math.sqrt(30/94500)
        out['moved'] = abs(F - m0[-1][1])/pr
        out['priced30'] = pr
    # ---- state
    st = 'UNCLEAR'; why = []
    if loc not in (None,) and wr is not None and fl is not None:
        for dr, nm in ((1, 'UP'), (-1, 'DOWN')):
            if loc == dr and wr == dr and fl == dr:
                st = 'TREND ' + nm
        if st == 'UNCLEAR':
            for dr, nm in ((1, 'UP'), (-1, 'DOWN')):
                agree = (wr == dr) + (fl == dr)
                opp = (wr == -dr) + (fl == -dr)
                if loc == dr and agree == 1 and opp == 0: st = 'LEAN ' + nm
        if st == 'UNCLEAR' and ready and cr is not None and cr >= C['CROSS_N'] and abs(z) < 1.25:
            st = 'CHOP'
    out['state'] = st
    return out
