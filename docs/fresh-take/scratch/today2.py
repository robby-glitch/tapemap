import json, bisect
from engine import *
from ref1 import pct
ref=json.load(open('ref_price.json'))
T=13*3600+45*60
def today(idx):
    rows=json.load(open('rows_%s.json'%idx))
    bars=[r for r in rows if r['T']>=9*60+18 and r["T"]+3<=13*60+45]
    bk=book(idx,'2026-10-09')
    tk=[x for x in bk if x['sec']<=T]
    last=tk[-1]
    H=max(max(r['h'] for r in bars),max(x['ltp'] for x in tk)); L=min(min(r['l'] for r in bars),min(x['ltp'] for x in tk))
    o18=bars[0]['o']
    def window(a):
        hs=[r['h'] for r in bars if r['T']*60>=a]+[x['ltp'] for x in tk if x['sec']>=a]
        ls=[r['l'] for r in bars if r['T']*60>=a]+[x['ltp'] for x in tk if x['sec']>=a]
        return max(hs)-min(ls)
    vt=lambda s:(next((x for x in reversed(tk) if x['sec']<=s),tk[0]))['vtt']
    zs=[((r['c']-r['vwap'])/(r['u1']-r['vwap'])) for r in bars if r['T']>=9*60+48 and r['u1']>r['vwap']]
    cr=0;st=0
    for z in zs:
        if z>0.25:
            if st==-1: cr+=1
            st=1
        elif z<-0.25:
            if st==1: cr+=1
            st=-1
    lb=bars[-1]; z_now=(last['ltp']-lb['vwap'])/(lb['u1']-lb['vwap'])
    first_close=[r for r in bars if r['T']==9*60+45][0]['c']
    return dict(rng=H-L,net=last['ltp']-o18,absnet=abs(last['ltp']-o18),z=z_now,rng60=window(T-3600),rng30=window(T-1800),
        up=sum(1 for z in zs if z>0)/len(zs),cross=cr,beyond1=sum(1 for z in zs if abs(z)>1)/len(zs),
        vcum=last['vtt'],v60=last['vtt']-vt(T-3600),v30=last['vtt']-vt(T-1800),first30=abs(first_close-o18),px=last['ltp'],H=H,L=L,o18=o18,tick_t=fmt(last['sec']))
res={}
for idx in IDXS:
    t=today(idx); res[idx]=t
    print('=====',idx,'last tick',t['tick_t'],'px %.1f'%t['px'],'H %.1f L(09:18+) %.1f open18 %.1f'%(t['H'],t['L'],t['o18']))
    vals=ref[idx]
    for k,lab,fmtv in [('rng','range since 09:18 (pts)','%.0f'),('absnet','|move from 09:18 print| (pts)','%.0f'),('net','signed move','%+.0f'),('z','z vs VWAP now','%+.2f'),('first30','|first 30-min move| (pts)','%.0f'),('rng60','last-60-min range (pts)','%.0f'),('rng30','last-30-min range (pts)','%.0f'),('up','share of closes above VWAP since 09:48','%.2f'),('cross','VWAP crossings since 09:48','%d'),('beyond1','share beyond ±1σ since 09:48','%.2f'),('vcum','cum volume (units)','%.0f'),('v60','last-60-min volume','%.0f'),('v30','last-30-min volume','%.0f')]:
        arr=[v[k] for v in vals.values()]
        x=t[k]
        lo,hi=min(arr),max(arr); med=sorted(arr)[len(arr)//2]
        print('  %-40s today '%lab+fmtv%x+'  | prior median '+fmtv%med+'  range ['+fmtv%lo+' .. '+fmtv%hi+']  pctile %.0f'%pct(arr,x))
json.dump(res,open('today_price.json','w'))
