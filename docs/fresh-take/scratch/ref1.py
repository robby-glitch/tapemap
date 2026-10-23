"""Percentile of today's price/volume numbers vs the same clock time in prior full sessions (11 days: 22 Sep-8 Oct excl. 7 Oct)."""
import json, bisect, statistics
from engine import *
PRIOR=[d for d in DAYS if d!='2026-10-07']
T_NOW=13*3600+45*60
def pct(vals,x):
    return 100.0*sum(1 for v in vals if v<=x)/len(vals)
def ref_day(idx,day,T=T_NOW):
    d=Day(idx,day)
    t=d.tick(T); p18=(d.tick(9*3600+18*60) or d.v[0])[1]
    m=[x for x in d.v if 9*3600+18*60<=x[0]<=T]
    P=[x[1] for x in m]
    m60=[x[1] for x in d.v if T-3600<=x[0]<=T]; m30=[x[1] for x in d.v if T-1800<=x[0]<=T]
    # vwap side share and beyond +1 sigma since 09:48 on 1-min samples
    zs=[]
    for s in range(9*3600+48*60,T+1,60):
        k=d.tick(s)
        if k and k[3]>0: zs.append((k[1]-k[2])/k[3])
    cr=0;st=0
    for z in zs:
        if z>0.25:
            if st==-1: cr+=1
            st=1
        elif z<-0.25:
            if st==1: cr+=1
            st=-1
    v_cum=t[5]; v60=t[5]-d.tick(T-3600)[5]; v30=t[5]-d.tick(T-1800)[5]
    return dict(rng=max(P)-min(P),net=t[1]-p18,absnet=abs(t[1]-p18),z=(t[1]-t[2])/t[3],rng60=max(m60)-min(m60),rng30=max(m30)-min(m30),
        up=sum(1 for z in zs if z>0)/len(zs),cross=cr,beyond1=sum(1 for z in zs if abs(z)>1)/len(zs),vcum=v_cum,v60=v60,v30=v30,
        first30=abs((d.tick(9*3600+47*60) or d.v[0])[1]-p18),px=t[1])
out={}
for idx in IDXS:
    out[idx]={day:ref_day(idx,day) for day in PRIOR}
json.dump(out,open('ref_price.json','w'))
print('ok')
