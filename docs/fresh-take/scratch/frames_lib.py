"""Helpers for building mockup frames: profile, walls, vpin, plays. All causal at time T."""
from seq import *
import bisect

LOT = {'NIFTY': 65, 'BANKNIFTY': 30, 'SENSEX': 20}
BIN = {'NIFTY': 5, 'BANKNIFTY': 10, 'SENSEX': 10}
EXPIRY_DOW = {'NIFTY': 1, 'SENSEX': 3}   # weekday numbers (Mon=0): Tue, Thu (from the chain 'expiry' field)


def prev_full_day(idx, day):
    best = None
    for dd in DAYS:
        if dd >= day:
            break
        if day_range(idx, dd):
            best = dd
    return best


def profile(idx, pday):
    """prior-day volume profile from the footprint ladders (lots). Returns dict or None."""
    if not pday:
        return None
    bars = [b for b in ux(idx, pday) if b.get('h') is not None]
    if not bars or bars[0]['sec'] > 9*3600+30*60:
        return None
    step = BIN[idx]
    vol = {}
    for b in bars:
        for L in b.get('ladder', []):
            k = round(L['p']/step)*step
            vol[k] = vol.get(k, 0) + L['b'] + L['s'] + L.get('u', 0)
    if not vol:
        return None
    ks = sorted(vol)
    tot = sum(vol.values())
    poc = max(vol, key=lambda k: vol[k])
    # value area 70% expanding from POC
    lo = hi = poc
    acc = vol[poc]
    allk = list(range(ks[0], ks[-1]+step, step))
    while acc < 0.7*tot:
        up = vol.get(hi+step, 0)
        dn = vol.get(lo-step, 0)
        if up == 0 and dn == 0 and (hi+step > ks[-1] and lo-step < ks[0]):
            break
        if up >= dn and hi+step <= ks[-1]:
            hi += step
            acc += up
        elif lo-step >= ks[0]:
            lo -= step
            acc += dn
        else:
            hi += step
            acc += up
    # smoothed for HVN/LVN
    sm = {}
    for k in allk:
        sm[k] = sum(vol.get(k+j*step, 0) for j in range(-2, 3))/5.0
    pk = []
    for k in allk[2:-2]:
        if sm[k] >= sm[k-step] and sm[k] >= sm[k+step] and sm[k] >= 0.55*sm[poc] and abs(k-poc) >= 6*step:
            pk.append(k)
    # keep separated peaks
    hv = []
    for k in sorted(pk, key=lambda x: -sm[x]):
        if all(abs(k-h) >= 8*step for h in hv):
            hv.append(k)
    lv = []
    pts = sorted(hv+[poc])
    for a, b in zip(pts, pts[1:]):
        seg = [k for k in allk if a < k < b]
        if seg:
            m = min(seg, key=lambda k: sm[k])
            if sm[m] <= 0.5*min(sm[a], sm[b]):
                lv.append(m)
    day_o = bars[0]['o']
    H = max(b['h'] for b in bars)
    L = min(b['l'] for b in bars)
    C = bars[-1]['c']
    return dict(day=pday, poc=poc, vah=hi, val=lo, hvn=sorted(hv), lvn=sorted(lv), hi=H, lo=L, close=C, vol=tot)


def walls(d, T, sn, W=1800):
    """two biggest CE OI strikes above spot and PE OI strikes below spot (spot-based strikes), with 30m change"""
    r0 = d.snap(max(T-W, d.ts0))
    sp = sn['spot']
    ce = [(k, v['oi'], v['oi']-(r0['ce'].get(k) or v)['oi']) for k, v in sn['ce'].items() if k >= sp]
    pe = [(k, v['oi'], v['oi']-(r0['pe'].get(k) or v)['oi']) for k, v in sn['pe'].items() if k <= sp]
    ce.sort(key=lambda x: -x[1])
    pe.sort(key=lambda x: -x[1])
    return ce[:2], pe[:2]


def tick_delta(d):
    out = []
    prev_v = None
    pa = pb = pl = None
    for r in d.bk:
        v = r['vtt']
        if prev_v is None:
            prev_v = v
        dv = v - prev_v
        prev_v = v
        a = r['a'][0][0] if r.get('a') else None
        b = r['b'][0][0] if r.get('b') else None
        if dv > 0:
            p = r['ltp']
            if pa is not None and p >= pa:
                s = 1
            elif pb is not None and p <= pb:
                s = -1
            elif pl is not None:
                s = 1 if p > pl else (-1 if p < pl else 0)
            else:
                s = 0
            out.append((r['sec'], s*dv, dv))
            pl = p
        pa, pb = a, b
    return out


def vpin_series(d, bucket):
    """volume-bucket VPIN, n=50 buckets. returns list of (sec_at_bucket_close, vpin)"""
    td = tick_delta(d)
    res = []
    buys = sells = fill = 0.0
    imb = []
    for sec, sd, dv in td:
        q = dv
        sign = sd/dv if dv else 0
        while q > 0:
            take = min(q, bucket-fill)
            if sign > 0:
                buys += take
            elif sign < 0:
                sells += take
            else:
                buys += take/2
                sells += take/2
            fill += take
            q -= take
            if fill >= bucket-1e-9:
                imb.append(abs(buys-sells))
                if len(imb) >= 50:
                    res.append((sec, sum(imb[-50:])/(50*bucket)))
                buys = sells = fill = 0.0
    return res


def vpin_at(vs, T):
    secs = [x[0] for x in vs]
    i = bisect.bisect_right(secs, T)-1
    return vs[i][1] if i >= 0 else None
