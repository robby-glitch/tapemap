from frames_lib import *
import statistics, collections
# 1) tick cadence and trade aggregation
for day in ['2026-10-08','2026-09-30']:
    d=Day('NIFTY',day)
    gaps=[b['sec']-a['sec'] for a,b in zip(d.bk,d.bk[1:])]
    ms=[(b['t']-a['t']) for a,b in zip(d.bk,d.bk[1:])]
    ms.sort()
    prev=None; multi=0; n=0; sumdv=0; sumltq=0
    for r in d.bk:
        if prev is not None:
            dv=r['vtt']-prev
            if dv>0:
                n+=1; sumdv+=dv; sumltq+=r['ltq']
                if dv>r['ltq']: multi+=1
        prev=r['vtt']
    print(day,'ticks',len(d.bk),'median gap ms',ms[len(ms)//2],'p90',ms[int(len(ms)*.9)],'| frames with volume',n,'frames where dvtt>ltq (several trades in one frame): %.0f%%'%(100*multi/n),'| sum dvtt/sum ltq %.2f'%(sumdv/sumltq))
# 2) ux ladder biggest cells around the two misses (lots; units = lots*65)
def bigcells(day,hm0,hm1):
    d=Day('NIFTY',day); out=[]
    for b in d.ux:
        if hm0<=b['sec']<hm1:
            allc=[L['b']+L['s']+L.get('u',0) for L in b['ladder']]
            for L in b['ladder']:
                side=max(L['b'],L['s'])
                out.append((side,fmt(b['sec']),L['p'],'buy' if L['b']>L['s'] else 'sell',L['b'],L['s'],b['vol']))
    out.sort(reverse=True)
    return out[:3]
for day,hm0,hm1 in [('2026-09-30',12*3600+35*60,13*3600+5*60),('2026-09-29',9*3600+55*60,10*3600+20*60)]:
    print(day,'top ux ladder cells (side lots, bar start, price, side, b, s, bar vol lots; x65 = units):')
    for x in bigcells(day,hm0,hm1): print('   ',x,'units',x[0]*65)
# 3) session median cell for those days (all bars) in lots, to see multiple
for day in ['2026-09-30','2026-09-29']:
    d=Day('NIFTY',day); cells=[L['b']+L['s']+L.get('u',0) for b in d.ux for L in b['ladder']]
    print(day,'median ux cell lots',statistics.median(cells),'max',max(cells),'n cells',len(cells))
