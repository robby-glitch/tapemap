import json,gzip,glob,os,datetime
D="C:/Users/kaam/Desktop/operator mode/tapemap/data/"
def op(p):
    return gzip.open(p,'rt') if p.endswith('.gz') else open(p)
def ist(ms): return (datetime.datetime.utcfromtimestamp(ms/1000)+datetime.timedelta(hours=5,minutes=30)).strftime('%m-%d %H:%M:%S')
days=['2026-09-22','2026-09-23','2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-05','2026-10-06','2026-10-07','2026-10-08']
for idx in ['NIFTY','BANKNIFTY','SENSEX']:
    for d in days:
        out=[idx,d]
        for kind in ['chain','ux']:
            fs=glob.glob(D+('chain/chain_%s_%s.jsonl*'%(idx,d) if kind=='chain' else 'tape/ux_%s_%s.jsonl*'%(idx,d)))
            if not fs: out.append(kind+':none'); continue
            n=0;first=last=None
            for l in op(fs[0]):
                n+=1
                try: r=json.loads(l)
                except: continue
                x=r.get('ts') if kind=='chain' else ist(r['t'])[6:]
                if first is None:first=x
                last=x
            out.append('%s n=%d %s-%s'%(kind,n,first,last))
        print(' | '.join(out))
