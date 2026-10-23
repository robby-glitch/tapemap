from rules2 import *
import sys
N_HOLD=10
def run(idx,day,step=10):
    d=Day(idx,day); rl=ruler_for(idx,day)
    shown=None;cand=None;cnt=0;rows=[]
    for T in range(9*3600+20*60,15*3600+1,60):
        if T<d.ts0+120: continue
        r=read(d,T,rl)
        if r['regime']=='WAIT': continue
        key=(r['regime'],r['dir'],r.get('pin'))
        if shown is None: shown=key
        elif key!=shown:
            if key==cand: cnt+=1
            else: cand=key;cnt=1
            if cnt>=N_HOLD: shown=key;cand=None;cnt=0
        else: cand=None;cnt=0
        if (T-9*3600-20*60)%(step*60)==0: rows.append((T,shown,r))
    return rows
if __name__=='__main__':
    idx,day=sys.argv[1],sys.argv[2]
    for T,k,r in run(idx,day,int(sys.argv[3]) if len(sys.argv)>3 else 10):
        print(fmt(T),'%-8s %-3s F %.0f z %+.1f upSh %.2f cr %s used %s disp %s | CE30 %+.0fL PE30 %+.0fL wr %s | fl15 %s moved %s | raw %s %s'%(k[0]+('/pin%d'%k[2] if k[2] else ''),{1:'UP',-1:'DN',0:''}[k[1]],r['F'],r['z'],r['up_share'],r['cross'],('%.2f'%r['used']) if r.get('used') else '-',('%+.2f'%r['disp']) if r.get('disp') is not None else '-',r['ce30']/1e5,r['pe30']/1e5,r['wr'],r['fl15'],('%.2f'%r['moved30']) if 'moved30' in r else '-',r['regime'],r['dir']))
