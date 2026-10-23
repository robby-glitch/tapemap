from rules import *
import sys
idx,day=sys.argv[1],sys.argv[2]
d=Day(idx,day)
prev=None
for T in range(9*3600+20*60,15*3600+1,15*60):
    r=read(d,T)
    if r['state']=='WAIT': print(fmt(T),'WAIT'); continue
    print(fmt(T),'%-10s F %.0f z %+.1f up%.2f dn%.2f cr %s | CE30 %+.1fL PE30 %+.1fL wr %s | delta %+.0f fl %s | moved %s'%(r['state'],r['F'],r['z'],r['up_share'],r['dn_share'],r['cross'],r['ce30']/1e5,r['pe30']/1e5,r['wr'],r['delta'],r['fl'],('%.2f'%r['moved']) if 'moved' in r else '-'))
