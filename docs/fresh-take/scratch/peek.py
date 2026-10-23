import json
D="C:/Users/kaam/Desktop/operator mode/tapemap/data/"
for idx in ['NIFTY','BANKNIFTY','SENSEX']:
    f=open(D+'chain/chain_%s_2026-10-08.jsonl'%idx)
    rows=[json.loads(l) for l in f]
    r=rows[0]
    print(idx,[k for k in r.keys()],len(r['strikes']),'spot',r['spot'],'atm',r['atm'],'k range',r['strikes'][0]['k'],r['strikes'][-1]['k'])
    # ATM row
    a=[s for s in r['strikes'] if s['k']==r['atm']][0]
    print(' ATM',a['ce']['ltp'],a['pe']['ltp'],'iv',a['ce']['iv'],a['pe']['iv'],'bid/ask ce',a['ce']['bid'],a['ce']['ask'])
    print(' last ts',rows[-1]['ts'],'spot',rows[-1]['spot'])
    # missing keys in any row
    keys=set()
    for x in rows[:50]: keys|=set(x.keys())
    print(' keys',keys)
