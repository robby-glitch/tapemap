from lib import *
import csv
rows=list(csv.DictReader(open("C:/Users/kaam/Downloads/NIFTY OCT FUT (20261008153900000 _ 20261006091500000).csv",encoding='utf-8-sig')))
print(len(rows)); 
cols=list(rows[0].keys()); print(cols[:5],cols[11:13])
def parse(r):
    d=r['Date']  # Tue Oct 06 2026 09:15:00 GMT+0530
    p=d.split(' ')
    return p[1]+' '+p[2], p[4]
csvbyday={}
for r in rows:
    day,t=parse(r)
    csvbyday.setdefault(day,[]).append((t,float(r['Close']),float(r['VWAP ‌VWAP‌ (y,y,y)']),float(r['SDVWAP1+ ‌VWAP‌ (y,y,y)']),float(r['OI'])))
print({k:len(v) for k,v in csvbyday.items()})
for day,iso in [('Oct 06','2026-10-06'),('Oct 08','2026-10-08')]:
    bk=book('NIFTY',iso)
    # tick vwap
    cv=0;pv=0;prev=None;series=[]
    for r in bk:
        v=r['vtt']
        if prev is None: prev=v; 
        dv=v-prev
        if dv>0:
            pv+=r['ltp']*dv; cv+=dv
        prev=v
        series.append((r['sec'],pv/cv if cv else None,r['ltp']))
    print(day,'first tick',fmt(bk[0]['sec']),bk[0]['sec']%60,'vtt',bk[0]['vtt'])
    cs=csvbyday[day]
    for t,c,vw,sd1,oi in cs[::20]:
        s=hms(t)+180  # bar end
        # last tick before s
        best=[x for x in series if x[0]<=s]
        if best: print(day,t,'csv vwap %.2f sd1+ %.2f close %.1f | tick vwap %.2f ltp %.1f diff %.2f'%(vw,sd1,c,best[-1][1],best[-1][2],best[-1][1]-vw))
