from engine import *
import statistics
def tick_delta(d):
    """per-tick signed volume using prior-tick quote; returns list (sec, signed qty, qty, ltp)"""
    out=[];prev_v=None;pa=pb=None;pl=None
    for r in d.bk:
        v=r['vtt']
        if prev_v is None: prev_v=v; 
        dv=v-prev_v; prev_v=v
        a=r['a'][0][0] if r.get('a') else None; b=r['b'][0][0] if r.get('b') else None
        if dv>0:
            p=r['ltp']
            if pa is not None and p>=pa: s=1
            elif pb is not None and p<=pb: s=-1
            elif pl is not None: s=1 if p>pl else (-1 if p<pl else 0)
            else: s=0
            out.append((r['sec'],s*dv,dv,p))
            pl=p
        pa,pb=a,b
    return out
if __name__=='__main__':
    for day in ['2026-10-08','2026-10-06','2026-09-28']:
        d=Day('NIFTY',day)
        td=tick_delta(d)
        # 5-min sums aligned with ux bars
        xs=[];ys=[]
        for b in d.ux[1:-1]:
            s0=b['sec']; s1=s0+300
            mine=sum(x[1] for x in td if s0<=x[0]<s1); vol=sum(x[2] for x in td if s0<=x[0]<s1)
            xs.append(b['delta']);ys.append(mine)
        n=len(xs);mx=sum(xs)/n;my=sum(ys)/n
        cov=sum((a-mx)*(b-my) for a,b in zip(xs,ys));vx=sum((a-mx)**2 for a in xs);vy=sum((b-my)**2 for b in ys)
        print(day,'n',n,'corr %.3f'%(cov/math.sqrt(vx*vy)),'sign agree %.2f'%(sum(1 for a,b in zip(xs,ys) if a*b>0)/n),'tot ux %d mine %d'%(sum(xs),sum(ys)), 'vol ux %d mine %d'%(sum(b['vol'] for b in d.ux[1:-1]),sum(x[2] for x in td)))
