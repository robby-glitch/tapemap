import json
from engine import *
TN=13*3600+45*60
def hmsec(s): h,m=s.split(':')[:2]; return int(h)*3600+int(m)*60
for idx in IDXS:
    st=STEP[idx]; d=Day(idx,'2026-10-09')
    bf=[json.loads(l) for l in open(D+'chain_backfill/backfill_%s_2026-10-09.jsonl'%idx)]
    print('=====',idx,'day build path (symmetric ±4 strikes around ATM at that time; lakh; vs prior close)')
    def row_bf(r):
        a=int(round(r['spot']/st)*st); ks=sorted(int(k) for k in r['k']); 
        ce=sum(r['k'][str(k)][0] for k in ks if a<=k<=a+4*st and str(k) in r['k']); pe=sum(r['k'][str(k)][1] for k in ks if a-4*st<=k<=a and str(k) in r['k'])
        return r['spot'],ce,pe
    marks=['09:30','10:00','10:10']
    for hm in marks:
        T=hmsec(hm); cand=[r for r in bf if hmsec(r['t'])<=T]
        if cand:
            sp,ce,pe=row_bf(cand[-1]); print('  %s (REST-rebuilt [I]) spot %.0f CE %+7.1fL PE %+7.1fL'%(hm,sp,ce/1e5,pe/1e5))
    for hm in ['10:30','11:00','11:30','12:00','12:30','13:00','13:30','13:45']:
        T=hmsec(hm); sn=d.snap(T); a=sn['atm']; ks=sorted(sn['ce']); below=[x for x in ks if x<=a]; above=[x for x in ks if x>=a]; ke=min(4,len(below)-1,len(above)-1)
        ce=sum(sn['ce'][x]['oi_chg'] or 0 for x in ks if a<=x<=a+ke*st); pe=sum(sn['pe'][x]['oi_chg'] or 0 for x in ks if a-ke*st<=x<=a)
        print('  %s (chain [M]) spot %.0f CE %+7.1fL PE %+7.1fL'%(hm,sn['spot'],ce/1e5,pe/1e5))
    sn=d.snap(TN); a=sn['atm']; r0=d.snap(10*3600+12*60)
    ivs=lambda s:[ (s['ce'][a]['iv'],s['pe'][a]['iv']) ]
    atm_iv_now=d.atm_iv(sn); atm_iv0=d.atm_iv(r0)
    print('  ATM IV 10:11 %.3f -> now %.3f'%(atm_iv0,atm_iv_now))
    print('  strike table at %s (spot %.1f ATM %d): strike | CE day-build L | CE OI L | CE dIV vs ATM since 10:11 | PE day-build L | PE OI L | PE dIV vs ATM'%(d.ch[-1]['ts'],sn['spot'],a))
    for k in range(a-4*st,a+4*st+1,st):
        if k not in sn['ce']: continue
        c,p=sn['ce'][k],sn['pe'][k]; c0,p0=r0['ce'].get(k),r0['pe'].get(k)
        dc=(c['iv']-c0['iv'])-(atm_iv_now-atm_iv0) if c0 and c['iv'] and c0['iv'] else float('nan')
        dp=(p['iv']-p0['iv'])-(atm_iv_now-atm_iv0) if p0 and p['iv'] and p0['iv'] else float('nan')
        print('   %d | %+7.1f | %6.1f | %+.3f | %+7.1f | %6.1f | %+.3f'%(k,(c['oi_chg'] or 0)/1e5,c['oi']/1e5,dc,(p['oi_chg'] or 0)/1e5,p['oi']/1e5,dp))
    # biggest OI walls in window
    mc=max(sn['ce'],key=lambda k:sn['ce'][k]['oi']); mp=max(sn['pe'],key=lambda k:sn['pe'][k]['oi'])
    print('  largest CE OI wall %d (%.0fL, build %+.0fL) | largest PE OI wall %d (%.0fL, build %+.0fL)'%(mc,sn['ce'][mc]['oi']/1e5,(sn['ce'][mc]['oi_chg'] or 0)/1e5,mp,sn['pe'][mp]['oi']/1e5,(sn['pe'][mp]['oi_chg'] or 0)/1e5))
