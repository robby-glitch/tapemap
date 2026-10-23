import json, statistics
from lib import *
from ref1 import pct
def med(a):
    a=sorted(a); n=len(a); return a[n//2] if n%2 else (a[n//2-1]+a[n//2])/2
S0=10*3600+15*60; S1=13*3600+35*60   # bars with start>=10:15 and end<=13:35
def metrics(idx,day):
    bars=[b for b in ux(idx,day) if b.get('ladder') and S0<=b['sec'] and b['sec']+300<=S1]
    cells=[];ev=[];top=[]
    for i,b in enumerate(bars):
        for L in b['ladder']: cells.append(L['b']+L['s']+L.get('u',0))
        m=med(cells)
        for L in b['ladder']:
            bb,ss=L['b'],L['s']; tot=bb+ss; size=max(bb,ss)
            if tot and m and i>=6 and size>=50*m and size>=0.25*b['vol'] and size/tot>=0.8: ev.append((fmt(b['sec']),L['p'],'buy' if bb>ss else 'sell',size))
        mx=max(b['ladder'],key=lambda L:max(L['b'],L['s'])); top.append((max(mx['b'],mx['s']),fmt(b['sec']),mx['p'],'buy' if mx['b']>mx['s'] else 'sell',b['vol']))
    vol=sum(b['vol'] for b in bars); cvd=sum(b['delta'] for b in bars)
    l60=[b for b in bars if b['sec']>=S1-3600]; l30=[b for b in bars if b['sec']>=S1-1800]
    return dict(n=len(bars),vol=vol,cvd=cvd,share=cvd/vol if vol else 0,cvd60=sum(b['delta'] for b in l60),cvd30=sum(b['delta'] for b in l30),
        vol60=sum(b['vol'] for b in l60),vol30=sum(b['vol'] for b in l30),e1=len(ev),ev=ev,top=sorted(top,reverse=True)[:3],
        maxcell=max((t[0] for t in top),default=0))
for idx in IDXS:
    t=metrics(idx,'2026-10-09'); pr={d:metrics(idx,d) for d in DAYS if d!='2026-10-07'}
    print('=====',idx,'today bars',t['n'],'(10:15-13:35 ux)')
    for k,lab in [('vol','volume lots'),('cvd','CVD lots'),('share','delta share'),('cvd60','CVD last 60m'),('cvd30','CVD last 30m'),('vol60','vol last 60m'),('vol30','vol last 30m'),('e1','E1 big prints'),('maxcell','largest single-price cell (lots)')]:
        arr=[v[k] for v in pr.values()]
        print('  %-30s today %9.3f | prior median %9.3f [%.3f .. %.3f] pctile %.0f'%(lab,t[k],med(arr),min(arr),max(arr),pct(arr,t[k])))
    print('  today E1:',t['ev'],' top cells:',[(round(a),b,c,d,e) for a,b,c,d,e in t['top']])
