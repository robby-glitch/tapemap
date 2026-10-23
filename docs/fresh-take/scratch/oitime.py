from engine import *
d=Day('NIFTY','2026-10-08')
for T in [9*3600+17*60+15, 9*3600+20*60, 9*3600+25*60,9*3600+30*60,9*3600+45*60,10*3600,10*3600+30*60,11*3600,12*3600,13*3600,14*3600,15*3600]:
    s=d.snap(T)
    a=s['atm']
    ce=sum(v['oi'] for k,v in s['ce'].items() if k>=a); pe=sum(v['oi'] for k,v in s['pe'].items() if k<=a)
    ceo=sum(v['oi_chg'] for k,v in s['ce'].items() if k>=a); peo=sum(v['oi_chg'] for k,v in s['pe'].items() if k<=a)
    print(s['ts'],'spot',s['spot'],'atm',a,'OTM CE oi %.1fM (chg vs yday %.2fM)  OTM PE oi %.1fM (chg %.2fM)'%(ce/1e6,ceo/1e6,pe/1e6,peo/1e6), 'k450', s['ce'][22450]['oi'] if 22450 in s['ce'] else '')
