from engine import *
for idx in IDXS:
    for day in DAYS:
        d=Day(idx,day)
        if not d.ch: continue
        r=d.ch[-1]
        # top strikes by CE oi, PE oi at close and at 09:17 and 12:00
        out=[]
        for T,lab in [(9*3600+20*60,'0920'),(12*3600,'1200'),(15*3600,'1500')]:
            s=d.snap(T)
            mx=max(s['ce'],key=lambda k:s['ce'][k]['oi']); mp=max(s['pe'],key=lambda k:s['pe'][k]['oi'])
            mt=max(s['ce'],key=lambda k:s['ce'][k]['oi']+s['pe'][k]['oi'])
            out.append('%s spot %.0f CEwall %d PEwall %d tot %d'%(lab,s['spot'],mx,mp,mt))
        print(idx,day[5:],' | '.join(out))
