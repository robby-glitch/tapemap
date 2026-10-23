from lib import *
import csv,math
rows=list(csv.DictReader(open("C:/Users/kaam/Downloads/NIFTY OCT FUT (20261008153900000 _ 20261006091500000).csv",encoding='utf-8-sig')))
def g(r,k):
    for kk in r:
        if kk.startswith(k): return float(r[kk])
for day,iso in [('Oct 06','2026-10-06'),('Oct 08','2026-10-08')]:
    bk=book('NIFTY',iso)
    cv=pv=pv2=0;prev=None;series=[]
    for r in bk:
        v=r['vtt']
        if prev is None: prev=v
        dv=v-prev
        if dv>0: pv+=r['ltp']*dv;pv2+=r['ltp']**2*dv;cv+=dv
        prev=v
        if cv: 
            m=pv/cv; series.append((r['sec'],m,math.sqrt(max(pv2/cv-m*m,0))))
    cs=[r for r in rows if r['Date'].split(' ')[1]+' '+r['Date'].split(' ')[2]==day]
    for r in cs[::20]:
        t=r['Date'].split(' ')[4]; s=hms(t)+180
        b=[x for x in series if x[0]<=s][-1]
        print(day,t,'csv sigma1 %.2f  tick sigma %.2f | csv vwap %.1f tick %.1f'%(g(r,'SDVWAP1+')-g(r,'VWAP'),b[2],g(r,'VWAP'),b[1]))
