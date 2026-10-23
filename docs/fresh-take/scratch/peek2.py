import json,gzip,glob
D="C:/Users/kaam/Desktop/operator mode/tapemap/data/"
def op(p): return gzip.open(p,'rt') if p.endswith('.gz') else open(p)
days=['2026-09-22','2026-09-23','2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-05','2026-10-06','2026-10-07','2026-10-08']
import datetime
for idx in ['NIFTY','BANKNIFTY','SENSEX']:
    for d in days:
        f=glob.glob(D+'chain/chain_%s_%s.jsonl*'%(idx,d))[0]
        first=None;last=None;exps=set();ks=set();n=0;spots=[]
        for l in op(f):
            r=json.loads(l); n+=1
            if first is None: first=r
            last=r; exps.add(r.get('expiry')); ks.add((r['strikes'][0]['k'],r['strikes'][-1]['k'])); spots.append(r['spot'])
        a=[s for s in first['strikes'] if s['k']==first['atm']][0]
        wd=datetime.date.fromisoformat(d).strftime('%a')
        print(idx,d,wd,'exp',sorted(map(str,exps)),'nk',len(ks),'o %.0f h %.0f l %.0f c %.0f'%(spots[0],max(spots),min(spots),spots[-1]),'ATMstrad %.0f'%(a['ce']['ltp']+a['pe']['ltp']))
