"""Claim C checks: (a) window-geometry bias in the writers read, (b) writing-vs-buying via IV change at the strike."""
from seq import *
import collections

def sym_writers(d, T, W=1800, k=4):
    sn = d.snap(T); r0 = d.snap(max(T-W, d.ts0))
    a = sn['atm']; st = STEP[d.idx]
    ks = sorted(sn['ce'])
    below = [x for x in ks if x <= a]; above = [x for x in ks if x >= a]
    ke = min(k, len(below)-1, len(above)-1)
    ce = sum(sn['ce'][x]['oi'] - r0['ce'].get(x, sn['ce'][x])['oi'] for x in ks if a <= x <= a+ke*st)
    pe = sum(sn['pe'][x]['oi'] - r0['pe'].get(x, sn['pe'][x])['oi'] for x in ks if a-ke*st <= x <= a)
    bce = sum(sn['ce'][x]['oi'] for x in ks if a <= x <= a+ke*st); bpe = sum(sn['pe'][x]['oi'] for x in ks if a-ke*st <= x <= a)
    mce = ce > C['MAT_OI']*bce; mpe = pe > C['MAT_OI']*bpe
    if mce and (not mpe or pe <= C['WEAK']*ce): v = -1
    elif mpe and (not mce or ce <= C['WEAK']*pe): v = 1
    elif mce and mpe: v = 0
    else: v = 'dry'
    return v, len(below), len(above), ke

def iv_split(d, T, W=1800, k=3):
    """near-ATM strikes: weight of positive OI change that came with IV falling (writing) vs rising (buying)"""
    sn = d.snap(T); r0 = d.snap(max(T-W, d.ts0)); a = sn['atm']; st = STEP[d.idx]
    out = {}
    for side in ('ce', 'pe'):
        w = b = 0.0
        for x in sn[side]:
            if abs(x-a) > k*st or x not in r0[side]: continue
            o1, o0 = sn[side][x], r0[side][x]
            if o1.get('iv') is None or o0.get('iv') is None: continue
            doi = o1['oi'] - o0['oi']
            if doi <= 0: continue
            if o1['iv'] < o0['iv']: w += doi
            else: b += doi
        out[side] = (w, b)
    return out

diff = tot = asym_geo = 0
dn_diff = dn_tot = 0
per = []
cewrite_windows = ce_buy_major = 0
pewrite_windows = pe_buy_major = 0
for idx in IDXS:
    for day in DAYS:
        if day == '2026-10-07': continue
        d, rl, recs = replay(idx, day)
        if not recs: continue
        n = m = 0
        for T in range(9*3600+50*60, 15*3600+1, 300):
            if T not in recs: continue
            r = recs[T]
            v2, nb, na, ke = sym_writers(d, T)
            tot += 1; n += 1
            if na >= 2*nb or nb >= 2*na: asym_geo += 1
            if v2 != r['wr']:
                diff += 1; m += 1
            if r['wr'] == -1:
                s = iv_split(d, T)['ce']
                if s[0]+s[1] > 0:
                    cewrite_windows += 1
                    if s[1] > s[0]: ce_buy_major += 1
            if r['wr'] == 1:
                s = iv_split(d, T)['pe']
                if s[0]+s[1] > 0:
                    pewrite_windows += 1
                    if s[1] > s[0]: pe_buy_major += 1
            if r['shown'][0] == 'TREND':
                dn_tot += 1
                if v2 != r['wr']: dn_diff += 1
        per.append((idx, day[5:], n, m))
print('5-min samples', tot, '| window geometry lopsided (>=2:1 strikes above vs below ATM):', asym_geo, '(%.0f%%)' % (100*asym_geo/tot))
print('writers verdict changes when window is made symmetric (+-4 strikes or less):', diff, '(%.0f%%)' % (100*diff/tot))
print('...among minutes shown TREND:', dn_diff, 'of', dn_tot)
print('CE-only windows where near-ATM OI build came mostly with IV RISING (buying):', ce_buy_major, 'of', cewrite_windows)
print('PE-only windows where near-ATM OI build came mostly with IV RISING (buying):', pe_buy_major, 'of', pewrite_windows)
# 8 Oct NIFTY detail
d, rl, recs = replay('NIFTY', '2026-10-08')
for hm in ('10:00', '12:00', '14:00'):
    h, m = hm.split(':'); T = int(h)*3600+int(m)*60
    print(hm, 'wr full', recs[T]['wr'], 'sym', sym_writers(d, T), 'iv split', {k: (round(v[0]/1e5), round(v[1]/1e5)) for k, v in iv_split(d, T).items()})
