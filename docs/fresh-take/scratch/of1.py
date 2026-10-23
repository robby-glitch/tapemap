import json, datetime, statistics
from lib import *
from ref1 import pct
def hm(ms): d=datetime.datetime.fromtimestamp(ms/1000,datetime.timezone.utc)+datetime.timedelta(hours=5,minutes=30); return d.hour*60+d.minute
def load(day):
    f=D+'tape/tape_NIFTY_%s.jsonl'%day
    rows=[json.loads(l) for l in open(f)]
    for r in rows: r['m']=hm(r['t'])
    return rows
END=13*60+30   # last bar START included (ends 13:35)
def med(a):
    a=sorted(a); n=len(a); return a[n//2] if n%2 else (a[n//2-1]+a[n//2])/2
def metrics(day):
    rows=[r for r in load(day) if r['m']<=END]
    vol=sum(r['vol'] for r in rows); cvd=sum(r['delta'] for r in rows)
    last60=[r for r in rows if r['m']>=END-55]; last30=[r for r in rows if r['m']>=END-25]
    first=rows[0]
    # E1 big prints
    cells_all=[];ev=[];top=[]
    for i,r in enumerate(rows):
        lad=r.get('ladder') or []
        for L in lad: cells_all.append((L['b'] or 0)+(L['s'] or 0))
        m=med(cells_all) if cells_all else 0
        for L in lad:
            b,s=(L['b'] or 0),(L['s'] or 0); tot=b+s; size=max(b,s)
            if tot and m and i>=6 and size>=50*m and size>=0.25*r['vol'] and size/tot>=0.8:
                ev.append((r['m'],L['p'],'buy' if b>s else 'sell',size,round(size/m)))
        if lad:
            mx=max(lad,key=lambda L:max(L['b'] or 0,L['s'] or 0)); top.append((max(mx['b'] or 0,mx['s'] or 0),r['m'],mx['p'],'buy' if (mx['b'] or 0)>(mx['s'] or 0) else 'sell',r['vol']))
    return dict(vol=vol,cvd=cvd,share=cvd/vol if vol else 0,cvd60=sum(r['delta'] for r in last60),cvd30=sum(r['delta'] for r in last30),
        vol60=sum(r['vol'] for r in last60),vol30=sum(r['vol'] for r in last30),first_delta_share=first['delta']/first['vol'] if first['vol'] else 0,
        n_e1=len(ev),ev=ev,top=sorted(top,reverse=True)[:3],nbars=len(rows),
        maxcell_bar=max(t[0]/ r_vol if (r_vol:=t[4]) else 0 for t in top) if top else 0)
today=metrics('2026-10-09')
priors={d:metrics(d) for d in DAYS if d!='2026-10-07'}
print('today bars',today['nbars'],'(11:15 bar missing)')
for k,lab in [('vol','GC volume lots 09:15-13:35'),('cvd','CVD lots'),('share','delta share'),('cvd60','CVD last 60m'),('cvd30','CVD last 30m'),('vol60','vol last 60m'),('vol30','vol last 30m'),('first_delta_share','first bar delta share'),('n_e1','E1 big prints by now')]:
    arr=[v[k] for v in priors.values()]
    print('%-28s today %9.3f | prior median %9.3f range [%.3f .. %.3f] pctile %.0f'%(lab,today[k],med(arr),min(arr),max(arr),pct(arr,today[k])))
print('today big prints (E1 rule on GC ladder):',today['ev'])
print('today top single-price cells (side lots, minute, price, side, bar vol):',[(round(a),b//60*100+b%60,c,d,e) for a,b,c,d,e in today['top']])
print('prior E1 counts by day:',{d[5:]:v['n_e1'] for d,v in priors.items()})
print('prior biggest single cell per day (lots, bar vol):',{d[5:]:(round(v['top'][0][0]),v['top'][0][4]) for d,v in priors.items() if v['top']})
