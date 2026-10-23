import json, math
from engine import *
from ref1 import pct
TN=13*3600+45*60
PRIOR=[x for x in DAYS if x!='2026-10-07']
def med(a): a=sorted(a); n=len(a); return a[n//2] if n%2 else (a[n//2-1]+a[n//2])/2
def tick_at(v,T):
    c=[x for x in v if x[0]<=T]; return c[-1] if c else v[0]
def prior_metrics(idx,day):
    d=Day(idx,day); t=tick_at(d.v,TN); F=t[1]; iv=d.atm_iv(d.snap(TN))
    p30=tick_at(d.v,TN-1800)[1]; p60=tick_at(d.v,TN-3600)[1]
    pr30=iv*F*math.sqrt(30/94500); pr60=iv*F*math.sqrt(60/94500)
    P=[x[1] for x in d.v if 9*3600+18*60<=x[0]<=TN]
    o18=tick_at(d.v,9*3600+18*60)
    oi_now=t[4]; oi18=o18[4]; oi60=tick_at(d.v,TN-3600)[4]; oi30=tick_at(d.v,TN-1800)[4]
    return dict(mv30=abs(F-p30)/pr30,mv60=abs(F-p60)/pr60,day=(max(P)-min(P))/(iv*F/math.sqrt(252)),iv=iv,
        doi_day=(oi_now-oi18)/oi_now*100,doi60=(oi_now-oi60)/oi_now*100,doi30=(oi_now-oi30)/oi_now*100,
        dpx_day=F-o18[1],dpx60=F-p60,dpx30=F-p30)
ref={idx:{x:prior_metrics(idx,x) for x in PRIOR} for idx in IDXS}
for idx in IDXS:
    rows=json.load(open('rows_%s.json'%idx)); d=Day(idx,'2026-10-09'); bk=[x for x in d.bk if x['sec']<=TN]
    F=bk[-1]['ltp']; iv=d.atm_iv(d.snap(TN)); iv0=d.atm_iv(d.snap(10*3600+12*60))
    def px_at(T):
        c=[x for x in bk if x['sec']<=T]
        if c: return c[-1]['ltp']
        b=[r for r in rows if r['T']*60+180<=T]; return b[-1]['c']
    p30=px_at(TN-1800); p60=px_at(TN-3600)
    bars=[r for r in rows if r['T']>=9*60+18 and r['T']+3<=13*60+45]
    H=max(max(r['h'] for r in bars),max(x['ltp'] for x in bk)); L=min(min(r['l'] for r in bars),min(x['ltp'] for x in bk))
    # futures OI from contract bars (REST) and book ticks
    def oi_at(T):
        c=[x for x in bk if x['sec']<=T]
        if c: return c[-1]['oi']
        b=[r for r in rows if r['T']*60+180<=T]; return b[-1]['oi']
    o18=rows[[r['T'] for r in rows].index(9*60+18)]
    oi_now=oi_at(TN); oi18=o18['oi']; oi60=oi_at(TN-3600); oi30=oi_at(TN-1800)
    prevclose_oi=Day(idx,'2026-10-08').v[-1][4]
    t=dict(mv30=abs(F-p30)/(iv*F*math.sqrt(30/94500)),mv60=abs(F-p60)/(iv*F*math.sqrt(60/94500)),day=(H-L)/(iv*F/math.sqrt(252)),iv=iv,
        doi_day=(oi_now-oi18)/oi_now*100,doi60=(oi_now-oi60)/oi_now*100,doi30=(oi_now-oi30)/oi_now*100,dpx_day=F-o18['o'],dpx60=F-p60,dpx30=F-p30)
    print('=====',idx,'F %.1f IV %.3f (10:11 %.3f)  fut OI now %.0f vs 09:18 %.0f vs prev close %.0f (%+.2f%%)'%(F,iv,iv0,oi_now,oi18,prevclose_oi,(oi_now-prevclose_oi)/prevclose_oi*100))
    for k,lab,fm in [('iv','ATM IV','%.3f'),('mv30','moved30 / priced30','%.2f'),('mv60','moved60 / priced60','%.2f'),('day','range so far / IV-priced 1-day σ','%.2f'),('doi_day','fut OI change 09:18→now (%)','%+.2f'),('doi60','fut OI change last 60m (%)','%+.2f'),('doi30','fut OI change last 30m (%)','%+.2f'),('dpx60','price change last 60m (pts)','%+.0f'),('dpx30','price change last 30m (pts)','%+.0f')]:
        arr=[v[k] for v in ref[idx].values()]
        print('  %-36s today '%lab+fm%t[k]+' | prior median '+fm%med(arr)+' [%s .. %s] pctile %.0f'%(fm%min(arr),fm%max(arr),pct(arr,t[k])))
