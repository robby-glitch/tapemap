import json, statistics
def load(idx):
    d=json.load(open('contract_%s.json'%idx)); s=d['index_series']
    rows=[]
    for b,v,o in zip(s['bars'],s['vwap'],s['oi']):
        h,m=b['t'].split(':'); rows.append(dict(t=b['t'],T=int(h)*60+int(m),o=b['o'],h=b['h'],l=b['l'],c=b['c'],v=b['v'],oi=o,**v))
    return rows,d
for idx in ['NIFTY','BANKNIFTY','SENSEX']:
    rows,d=load(idx)
    print('=====',idx,'bars',len(rows),rows[0]['t'],'->',rows[-1]['t'],'expiry',d.get('expiry'),'interval',d.get('interval'))
    hi=max(rows,key=lambda r:r['h']); lo=min(rows,key=lambda r:r['l'])
    print('open %.1f | day high %.1f at %s | day low %.1f at %s | last close %.1f (%s)'%(rows[0]['o'],hi['h'],hi['t'],lo['l'],lo['t'],rows[-1]['c'],rows[-1]['t']))
    r=rows[-1]; sg=r['u1']-r['vwap']
    print('VWAP %.1f sigma %.1f z %+.2f | u1 %.1f u2 %.1f d1 %.1f d2 %.1f'%(r['vwap'],sg,(r['c']-r['vwap'])/sg,r['u1'],r['u2'],r['d1'],r['d2']))
    # hourly path
    for hm in ['09:18','09:30','09:45','10:00','10:30','11:00','11:30','12:00','12:30','13:00','13:30']:
        h,m=hm.split(':'); T=int(h)*60+int(m)
        b=[x for x in rows if x['T']<=T][-1]
        s=b['u1']-b['vwap']
        print('  %s close %.1f vwap %.1f z %+.2f oi %.0f vol %.0f'%(b['t'],b['c'],b['vwap'],(b['c']-b['vwap'])/s if s>0 else 0,b['oi'],b['v']))
    # side share & crossings
    zs=[((x['c']-x['vwap'])/(x['u1']-x['vwap']) if x['u1']>x['vwap']+1e-9 else 0) for x in rows if x['T']>=9*60+45]
    up=sum(1 for z in zs if z>0)/len(zs)
    cr=0;st=0
    for z in zs:
        if z>0.25:
            if st==-1: cr+=1
            st=1
        elif z<-0.25:
            if st==1: cr+=1
            st=-1
    print('since 09:45: share of 3-min closes above VWAP %.0f%% ; crossings(0.25σ dead zone) %d ; max z %+.2f min z %+.2f ; closes beyond +1σ %d beyond -1σ %d of %d'%(100*up,cr,max(zs),min(zs),sum(1 for z in zs if z>1),sum(1 for z in zs if z<-1),len(zs)))
    tv=sum(x['v'] for x in rows); print('total volume so far (REST candles) %.0f units'%tv)
    json.dump(rows,open('rows_%s.json'%idx,'w'))
