# Causal feature engine. Everything at time T uses only data with sec <= T.
from lib import *
import bisect, math

class Day:
    def __init__(s, idx, day):
        s.idx, s.day = idx, day
        s.ch = chain(idx, day)
        for r in s.ch: r['s'] = hms(r['ts'])
        s.chs = [r['s'] for r in s.ch]
        s.bk = book(idx, day)
        s.bks = [r['sec'] for r in s.bk]
        s.ux = ux(idx, day)
        # per-snapshot dicts K -> (ce_oi, pe_oi)
        for r in s.ch:
            r['ce'] = {x['k']: x['ce'] for x in r['strikes']}
            r['pe'] = {x['k']: x['pe'] for x in r['strikes']}
        # tick vwap / sigma / oi
        cv = pv = pv2 = 0.0; prev = None
        s.v = []   # (sec, ltp, vwap, sigma, oi, vtt)
        for r in s.bk:
            if prev is None: prev = r['vtt']
            dv = r['vtt'] - prev
            if dv > 0:
                pv += r['ltp']*dv; pv2 += r['ltp']**2*dv; cv += dv
            prev = r['vtt']
            if cv > 0:
                m = pv/cv
                s.v.append((r['sec'], r['ltp'], m, math.sqrt(max(pv2/cv - m*m, 0)), r['oi'], r['vtt']))
        s.vs = [x[0] for x in s.v]
        s.ts0 = s.ch[0]['s'] if s.ch else None

    def snap(s, T):
        i = bisect.bisect_right(s.chs, T) - 1
        return s.ch[i] if i >= 0 else None
    def tick(s, T):
        i = bisect.bisect_right(s.vs, T) - 1
        return s.v[i] if i >= 0 else None

    def straddle(s, r):
        a = r['atm']
        c, p = r['ce'].get(a), r['pe'].get(a)
        if not c or not p or c.get('ltp') is None or p.get('ltp') is None: return None
        return c['ltp'] + p['ltp']

    def atm_iv(s, r):
        a = r['atm']; c, p = r['ce'].get(a), r['pe'].get(a)
        if not c or not p or c.get('iv') is None or p.get('iv') is None:
            return None
        return (c['iv'] + p['iv'])/2

    def spread(s, r):
        a = r['atm']; out = []
        for side in ('ce', 'pe'):
            o = r[side].get(a)
            if o and o.get('bid') and o.get('ask') and o['ask'] > 0:
                mid = (o['bid'] + o['ask'])/2
                out.append((o['ask'] - o['bid'])/mid*100)
        return sum(out)/len(out) if out else None

    def oi_flow(s, T, W):
        """OTM-side OI change over last W seconds: CE strikes >= ATM(T), PE strikes <= ATM(T)."""
        r1 = s.snap(T)
        if not r1: return None
        r0 = s.snap(max(T - W, s.ts0))
        a = r1['atm']
        ce = sum(r1['ce'][k]['oi'] - r0['ce'].get(k, r1['ce'][k])['oi'] for k in r1['ce'] if k >= a)
        pe = sum(r1['pe'][k]['oi'] - r0['pe'].get(k, r1['pe'][k])['oi'] for k in r1['pe'] if k <= a)
        return ce, pe, r1['s'] - r0['s']

    def delta_sum(s, T, W):
        """sum of ux-bar delta for bars fully closed (start+300 <= T) in last W seconds"""
        tot = 0.0; vol = 0.0; n = 0
        for b in s.ux:
            end = b['sec'] + 300
            if end <= T and end > T - W:
                tot += b['delta']; vol += b['vol']; n += 1
        return tot, vol, n
