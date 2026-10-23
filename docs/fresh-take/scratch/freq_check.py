import sys, statistics, collections
sys.path.append('C:/Users/kaam/Desktop/operator mode/tapemap')
import prints
from frames_lib import *
def med(a):
    a=sorted(a); n=len(a)
    return a[n//2] if n%2 else (a[n//2-1]+a[n//2])/2
res={}
for idx in IDXS:
    bp=[];stk=[];unf=[];bars_n=[]
    for day in DAYS:
        if day=='2026-10-07': continue
        bars=[b for b in ux(idx,day) if b.get('ladder')]
        allc=[];n=0;e1=0;s=0;u=0
        for b in bars:
            if b['sec']+300>15*3600+1: continue
            cells=[(L['p'],L['b'],L['s']) for L in b['ladder']]
            for p,bb,ss in cells: allc.append(bb+ss)
            if n<6: n+=1
            else:
                m=med(allc); vol=b['vol'] or 1
                best=None
                for p,bb,ss in cells:
                    tot=bb+ss; size=max(bb,ss)
                    if tot and size>=50*m and size>=0.25*vol and size/tot>=0.8: best=1
                if best: e1+=1
                n+=1
            f=prints.bar_flags(b,BIN[idx])
            if f:
                if f['stacks']: s+=1
                if f['unfinished_high'] or f['unfinished_low']: u+=1
        bp.append(e1);stk.append(s);unf.append(u);bars_n.append(len(bars))
    print(idx,'index-days',len(bp),'| E1 BADA PRINT events per day: median',statistics.median(bp),'max',max(bp),'total',sum(bp),'| bars with a STACK: %d of %d'%(sum(stk),sum(bars_n)),'| bars with unfinished auction: %d of %d'%(sum(unf),sum(bars_n)))
