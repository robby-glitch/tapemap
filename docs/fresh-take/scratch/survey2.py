from engine import *
import sys
rows=[]
for idx in IDXS:
    for day in DAYS:
        d=Day(idx,day)
        if not d.v: continue
        r0=d.ch[0]; st0=d.straddle(r0)
        # 1-min grid from 09:20 to 15:00
        z=[];F=[]
        for T in range(9*3600+20*60,15*3600+1,60):
            t=d.tick(T)
            if not t: continue
            F.append(t[1]); z.append((t[1]-t[2], t[3]))
        if len(F)<50: 
            print(idx,day,'partial n',len(F)); 
        op_=r0['spot']; basis=d.v[0][1]-r0['spot']
        H=max(F);L=min(F);C=F[-1];O=F[0]
        # side share of VWAP
        up=sum(1 for a,b in z if a>0)/len(z)
        # crossings with dead zone 0.25 sigma
        cr=0;state=0
        for a,b in z:
            zz=a/b if b>1e-9 else 0
            if zz>0.25:
                if state==-1: cr+=1
                state=1
            elif zz<-0.25:
                if state==1: cr+=1
                state=-1
        zfin=z[-1][0]/z[-1][1] if z[-1][1] else 0
        eff=abs(C-O)/(H-L) if H>L else 0
        # OI flow: whole day OTM CE and PE change from 09:17 to 15:00 and by thirds
        def fl(t0,t1):
            r=d.oi_flow(t1,t1-t0)
            return r
        a=fl(9*3600+17*60,10*3600+17*60); b=fl(10*3600+17*60,12*3600+17*60); c=fl(12*3600+17*60,15*3600)
        def f(x): return '%+.1f/%+.1f'%(x[0]/1e5,x[1]/1e5) if x else '-'
        print('%-9s %s H-L %5.0f (%.2f strad) net %+5.0f eff %.2f vwapUp %.2f cross %d zEnd %+.1f | dOI CE/PE(L) 1h %s 2h %s pm %s'%(idx,day[5:],H-L,(H-L)/st0,C-O,eff,up,cr,zfin,f(a),f(b),f(c)))
