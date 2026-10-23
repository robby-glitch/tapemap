import json,gzip,glob,datetime,csv,math
D="C:/Users/kaam/Desktop/operator mode/tapemap/data/"
DAYS=['2026-09-22','2026-09-23','2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-05','2026-10-06','2026-10-07','2026-10-08']
IDXS=['NIFTY','BANKNIFTY','SENSEX']
STEP={'NIFTY':50,'BANKNIFTY':100,'SENSEX':100}
def op(p): return gzip.open(p,'rt') if p.endswith('.gz') else open(p)
def hms(s): h,m,x=s.split(':'); return int(h)*3600+int(m)*60+int(x)
def ist(ms): return datetime.datetime.fromtimestamp(ms/1000,datetime.timezone.utc)+datetime.timedelta(hours=5,minutes=30)
def sec_of(ms):
    d=ist(ms); return d.hour*3600+d.minute*60+d.second
def fmt(sec): return '%02d:%02d'%(sec//3600,(sec%3600)//60)
def chain(idx,day):
    f=glob.glob(D+'chain/chain_%s_%s.jsonl*'%(idx,day))
    return [json.loads(l) for l in op(f[0])] if f else []
def ux(idx,day):
    f=glob.glob(D+'tape/ux_%s_%s.jsonl*'%(idx,day))
    out=[]
    if f:
        for l in op(f[0]):
            r=json.loads(l); r['sec']=sec_of(r['t']); out.append(r)
    return out
def book(idx,day):
    f=glob.glob(D+'book/book_%s_%s.jsonl*'%(idx,day))
    out=[]
    if f:
        for l in op(f[0]):
            r=json.loads(l); r['sec']=sec_of(r['t']); out.append(r)
    return out
