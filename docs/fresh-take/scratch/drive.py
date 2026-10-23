from rules2 import *
import math
rows=[]
for idx in IDXS:
    for day in DAYS:
        d=Day(idx,day)
        if not d.v or d.v[0][0]>9*3600+30*60: continue
        o=d.v[0][1]
        for hm in (9*3600+22*60, 9*3600+27*60, 9*3600+32*60):
            t=d.tick(hm); sn=d.snap(hm)
            iv=d.atm_iv(sn)
            pr=iv*t[1]*math.sqrt(30/94500)
            d5=d.delta_sum(hm,300)[0]
            rows.append((idx,day[5:],hm,(t[1]-o),(t[1]-o)/pr,d5))
import collections
for hm in (9*3600+22*60, 9*3600+27*60, 9*3600+32*60):
    rr=[r for r in rows if r[2]==hm]
    big=[r for r in rr if abs(r[4])>=1.0]
    print(fmt(hm),'n',len(rr),'|drive|>=1.0x priced30 :',len(big),' >=0.7:',len([r for r in rr if abs(r[4])>=0.7]))
    for r in big: print('   ',r[0],r[1],'%+.0f pt %.2fx delta5 %+.0f'%(r[3],r[4],r[5]))
