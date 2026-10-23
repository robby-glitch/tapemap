"""Entry check per expression: PLACE / OI / FLOW / PRICE / CLOCK lights -> status. Rules of thumb, not predictions."""
from frames_lib import *

G, A, R, N = 'g', 'a', 'r', 'n'   # green, amber, red, none(unknown)
EXPR = [('BUY CE', +1, 'buy', 'ce'), ('SELL PE', +1, 'sell', 'pe'), ('BUY PE', -1, 'buy', 'pe'), ('SELL CE', -1, 'sell', 'ce')]
CUTOFF = 15*3600


def lights_for(r, dirn, kind, T):
    """returns dict of lights for expression direction dirn (+1 bullish, -1 bearish) and kind buy/sell"""
    reg, dr = r['regime'], r['dir']
    z = r['z']
    wr, fl = r['wr'], r['fl15']
    L = {}
    notes = {}
    # allowed?
    if reg in ('TREND', 'LEAN'):
        allowed = (dr == dirn)
    elif reg == 'TURN':
        allowed = (-dr == dirn)
    elif reg == 'CHOP':
        allowed = True
    elif reg == 'PIN':
        allowed = (kind == 'sell')          # theta only pays the seller; buying a pin is paying decay
    else:
        allowed = False
    # PLACE
    if reg in ('TREND', 'LEAN') and allowed:
        zz = z*dirn                      # >0 = extended in trade direction
        sg = max(r['sigma'], 1e-9)
        ext = (r['F']-r['lo'])/sg if dirn < 0 else (r['hi']-r['F'])/sg   # bounce off the extreme, in sigma
        if -0.3 <= zz <= 0.8:
            L['place'] = G
            notes['place'] = 'retest VWAP'
        elif ext >= 0.4 and zz >= 0.4:
            L['place'] = G
            notes['place'] = 'bounce %.1fs' % ext
        elif ext <= 0.1 and r['fl15'] == dirn and (r.get('moved30') or 0) >= 1.0:
            L['place'] = G
            notes['place'] = 'break'
        else:
            L['place'] = A
            notes['place'] = 'extended'
    elif reg == 'TURN' and allowed:
        L['place'] = A if z*dirn < 0 else G     # counter-trend: needs VWAP reclaim
        notes['place'] = 'VWAP reclaim chahiye'
    elif reg == 'CHOP':
        # fade: bullish at lower band, bearish at upper band
        L['place'] = G if z*dirn <= -1.0 else A
        notes['place'] = 'z %+.1f' % z
    elif reg == 'PIN' and allowed:
        L['place'] = G if abs(r['spot'] - r['pin']) <= 0.5*STEP[r['idx']] else A
        notes['place'] = 'pin ke paas'
    else:
        L['place'] = N
    # OI
    if wr is None:
        L['oi'] = N
    elif reg in ('TREND', 'LEAN'):
        L['oi'] = G if wr == dirn else (R if wr == -dirn else A)
    elif reg == 'TURN':
        L['oi'] = G if wr == dirn else (R if wr == -dirn else A)
    elif reg == 'PIN':
        L['oi'] = G if wr in (0, 'dry') else A      # one-sided writing = the pin may be breaking
    else:
        L['oi'] = R if wr == -dirn else G
    # FLOW
    if reg == 'PIN':
        L['flow'] = N
    elif fl is None:
        L['flow'] = N
    else:
        L['flow'] = G if fl == dirn else (R if fl == -dirn else A)
    # PRICE (buy vs sell edge)
    mv = r.get('moved30')
    if mv is None:
        L['price'] = N
    elif kind == 'buy':
        L['price'] = G if mv >= 0.8 else (A if mv >= 0.4 else R)
    else:
        L['price'] = G if mv <= 0.6 else (A if mv <= 1.1 else R)
    # CLOCK
    left = CUTOFF - T
    L['clock'] = G if left >= 2700 else (A if left >= 900 else R)
    return allowed, L


def status(r, allowed, L, T):
    reg = r['regime']
    if not allowed or L['place'] == N:
        return 'NO', ('pin me buy nahi' if reg == 'PIN' else 'side nahi')
    if L['clock'] == R:
        return 'NO', 'time khatam'
    if L['oi'] == R:
        return 'NO', 'writers ulte'
    miss = []
    if L['place'] != G:
        miss.append('place')
    if L['flow'] != G and reg != 'PIN':
        miss.append('flow')
    if L['oi'] == A or L['oi'] == N:
        miss.append('oi')
    if miss:
        return 'WAIT', '/'.join(miss)
    cap = reg in ('LEAN', 'TURN', 'PIN') or not r['ready']
    return ('HALF' if cap else 'OK'), ''


def all_plays(r, T):
    rows = []
    for nm, dirn, kind, side in EXPR:
        allowed, L = lights_for(r, dirn, kind, T)
        st, why = status(r, allowed, L, T)
        rows.append(dict(name=nm, dir=dirn, kind=kind, side=side, lights=L, status=st, why=why))
    return rows


if __name__ == '__main__':
    import sys
    idx, day, a, b = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    d, rl, recs = replay(idx, day)
    h, m = a.split(':')
    T0 = int(h)*3600+int(m)*60
    h, m = b.split(':')
    T1 = int(h)*3600+int(m)*60
    for T in range(T0, T1+1, 60):
        r = dict(recs[T])
        r['regime'], r['dir'] = r['shown'][0], r['shown'][1]
        rows = all_plays(r, T)
        print(fmt(T), r['shown'][:2], 'F %.0f z %+.2f' % (r['F'], r['z']), ' | '.join('%s %s %s' % (x['name'], x['status'], x['why']) for x in rows if x['status'] != 'NO'))
