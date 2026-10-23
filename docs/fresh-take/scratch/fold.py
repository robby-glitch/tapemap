"""Fold board: the four reasons Mary folds on (zone, order flow, OI, VPIN), judged continuously, never on a candle close."""
from plays import *


def fold_lights(recs, T, dirn, vp_entry=None, vp_now=None):
    """recs: per-minute raw records; dirn: +1 long-delta trade (buy CE/sell PE), -1 short-delta."""
    r = recs[T]
    # ZONE: last 3 one-minute z samples on the wrong side of VWAP (beyond 0.25 sigma)
    zs = []
    for k in range(3):
        rr = recs.get(T-60*k)
        if rr:
            zs.append(rr['z']*dirn)
    z_now = r['z']*dirn
    if len(zs) == 3 and all(x <= -0.25 for x in zs):
        zone = R
    elif z_now < 0.6:
        zone = A
    else:
        zone = G
    fl = r['fl15']
    flow = N if fl is None else (G if fl == dirn else (R if fl == -dirn else A))
    wr = r['wr']
    if wr is None:
        oi = N
    elif wr == dirn:
        oi = A if r.get('flip') else G
    elif wr == -dirn:
        oi = R
    else:
        oi = A
    if vp_entry is None or vp_now is None:
        vp = N
    else:
        dv = vp_now - vp_entry
        vp = R if (dv >= 0.06 and fl == -dirn) else (A if dv >= 0.03 else G)
    lights = dict(zone=zone, flow=flow, oi=oi, vpin=vp)
    reds = sum(1 for k in ('flow', 'oi', 'vpin') if lights[k] == R)
    ambers = sum(1 for k in lights if lights[k] == A)
    if zone == R or reds >= 2:
        verdict = 'FOLD'
    elif reds == 1 or ambers >= 2:
        verdict = 'WATCH'
    else:
        verdict = 'HOLD'
    return lights, verdict


if __name__ == '__main__':
    import sys
    idx, day, a, b, dirn, T_entry = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), sys.argv[6]
    d, rl, recs = replay(idx, day)
    pday = prev_full_day(idx, day)
    bucket = Day(idx, pday).v[-1][5]/300.0
    vs = vpin_series(d, bucket) if idx == 'NIFTY' else []
    def tt(x):
        h, m = x.split(':')
        return int(h)*3600+int(m)*60
    Te = tt(T_entry)
    vpe = vpin_at(vs, Te) if vs else None
    print('vpin at entry', vpe)
    for T in range(tt(a), tt(b)+1, 60):
        vpn = vpin_at(vs, T) if vs else None
        L, v = fold_lights(recs, T, dirn, vpe, vpn)
        r = recs[T]
        print(fmt(T), 'F %.0f z %+.2f fl15 %s wr %s vpin %s | zone %s flow %s oi %s vpin %s -> %s' % (r['F'], r['z'], r['fl15'], r['wr'], ('%.3f' % vpn) if vpn else '-', L['zone'], L['flow'], L['oi'], L['vpin'], v))
