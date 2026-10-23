import json, math, statistics, sys
from engine import *
from ref1 import pct
TNOW=13*3600+45*60
K=4
def sym_build(sn,k=K,field='oi_chg'):
    a=sn['atm']; st=STEP[sn['idx']] if 'idx' in sn else None
    return None
def build_at(d,T,k=K):
    sn=d.snap(T); a=sn['atm']; st=STEP[d.idx]; ks=sorted(sn['ce'])
    below=[x for x in ks if x<=a]; above=[x for x in ks if x>=a]; ke=min(k,len(below)-1,len(above)-1)
    ce=sum(sn['ce'][x]['oi_chg'] or 0 for x in ks if a<=x<=a+ke*st); pe=sum(sn['pe'][x]['oi_chg'] or 0 for x in ks if a-ke*st<=x<=a)
    return ce,pe,ke,len(below),len(above)
def flow_at(d,T,W,k=K):
    sn=d.snap(T); r0=d.snap(max(T-W,d.ts0)); a=sn['atm']; st=STEP[d.idx]; ks=sorted(sn['ce'])
    below=[x for x in ks if x<=a]; above=[x for x in ks if x>=a]; ke=min(k,len(below)-1,len(above)-1)
    ce=sum(sn['ce'][x]['oi']-(r0['ce'].get(x) or sn['ce'][x])['oi'] for x in ks if a<=x<=a+ke*st)
    pe=sum(sn['pe'][x]['oi']-(r0['pe'].get(x) or sn['pe'][x])['oi'] for x in ks if a-ke*st<=x<=a)
    return ce,pe
def Aof(ce,pe): return (ce-pe)/(abs(ce)+abs(pe)) if (abs(ce)+abs(pe)) else 0
def metrics(d,T):
    ce,pe,ke,nb,na=build_at(d,T); f30=flow_at(d,T,1800); f60=flow_at(d,T,3600)
    sn=d.snap(T); a=sn['atm']
    base_ce=sum(v['oi'] for k,v in sn['ce'].items() if abs(k-a)<=K*STEP[d.idx]); base_pe=sum(v['oi'] for k,v in sn['pe'].items() if abs(k-a)<=K*STEP[d.idx])
    iv=d.atm_iv(sn); st=d.straddle(sn)
    return dict(ce=ce,pe=pe,A=Aof(ce,pe),tot=abs(ce)+abs(pe),totrel=(abs(ce)+abs(pe))/(base_ce+base_pe),ce30=f30[0],pe30=f30[1],A30=Aof(*f30),ce60=f60[0],pe60=f60[1],A60=Aof(*f60),
        iv=iv,strad=st,ke=ke,nb=nb,na=na,atm=a,spot=sn['spot'])
def med(a): a=sorted(a); n=len(a); return a[n//2] if n%2 else (a[n//2-1]+a[n//2])/2
PRIOR=[x for x in DAYS if x!='2026-10-07']
out={}
for idx in IDXS:
    dt=Day(idx,'2026-10-09')
    # today's chain: ts0 = 10:11; backfill not merged into Day: path of day build uses chain only from 10:11
    t=metrics(dt,TNOW); pr={x:metrics(Day(idx,x),TNOW) for x in PRIOR}
    out[idx]=dict(today=t,prior=pr)
    print('=====',idx,'chain until',dt.ch[-1]['ts'],'spot %.1f atm %d window strikes below/above ATM %d/%d (k used %d)'%(t['spot'],t['atm'],t['nb'],t['na'],t['ke']))
    for k,lab,u in [('ce','day build CE (±4 sym, lakh)',1e5),('pe','day build PE (lakh)',1e5),('A','A=(CE-PE)/(|CE|+|PE|)',1),('totrel','|CE|+|PE| build / base OI',1),('ce30','CE flow 30m (lakh)',1e5),('pe30','PE flow 30m (lakh)',1e5),('A30','A30',1),('ce60','CE flow 60m',1e5),('pe60','PE flow 60m',1e5),('A60','A60',1),('iv','ATM IV',1),('strad','ATM straddle',1)]:
        arr=[v[k] for v in pr.values() if v[k] is not None]
        print('  %-30s today %9.3f | prior median %9.3f [%.3f .. %.3f] pctile %.0f'%(lab,t[k]/u,med(arr)/u,min(arr)/u,max(arr)/u,pct(arr,t[k])))
json.dump({i:{'today':out[i]['today']} for i in out},open('oi_today.json','w'))
