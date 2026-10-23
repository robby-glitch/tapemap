from rules2 import *
import itertools
D_={}
for idx in IDXS:
    for day in DAYS:
        D_[(idx,day)]=Day(idx,day)
tot=0;allsame=0;pair={'N-S':0,'N-B':0,'B-S':0};nclear=0;lockn=0
rows=[]
for day in DAYS:
    if day=='2026-10-07': continue
    for T in [10*3600+30*60,12*3600,13*3600+30*60]:
        r={}
        for idx in IDXS:
            d=D_[(idx,day)]
            r[idx]=read(d,T,ruler_for(idx,day))
        locs=[r[i]['loc'] for i in IDXS]
        tot+=1
        if locs[0]==locs[1]==locs[2]: allsame+=1
        if locs[0]==locs[2]: pair['N-S']+=1
        if locs[0]==locs[1]: pair['N-B']+=1
        if locs[1]==locs[2]: pair['B-S']+=1
        rows.append((day[5:],fmt(T),[(r[i]['regime'],{1:'U',-1:'D',0:''}[r[i]['dir']]) for i in IDXS]))
print('samples',tot,'all3 same loc',allsame,pair)
for x in rows: print(x)
