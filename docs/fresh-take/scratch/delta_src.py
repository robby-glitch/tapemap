import json, datetime, statistics, math
from lib import *
from ref1 import pct
def hm(ms): d=datetime.datetime.fromtimestamp(ms/1000,datetime.timezone.utc)+datetime.timedelta(hours=5,minutes=30); return d.hour*3600+d.minute*60
S0=10*3600+15*60; S1=13*3600+35*60
def gc(day): return {hm(json.loads(l)['t']):json.loads(l) for l in open(D+'tape/tape_NIFTY_%s.jsonl'%day)}
res=[];corrs=[];agree=[]
days=[d for d in DAYS if d!='2026-10-07']+['2026-10-09']
for day in days:
    G=gc(day); U={b['sec']:b for b in ux('NIFTY',day)}
    keys=[s for s in sorted(G) if S0<=s and s+300<=S1 and s in U]
    g=[G[s]['delta'] for s in keys]; u=[U[s]['delta'] for s in keys]
    vg=sum(G[s]['vol'] for s in keys); vu=sum(U[s]['vol'] for s in keys)
    n=len(keys)
    mg=sum(g)/n; mu=sum(u)/n
    cov=sum((a-mg)*(b-mu) for a,b in zip(g,u)); den=math.sqrt(sum((a-mg)**2 for a in g)*sum((b-mu)**2 for b in u))
    c=cov/den if den else float('nan')
    ag=sum(1 for a,b in zip(g,u) if a*b>0)/n
    res.append((day,n,sum(g),sum(u),sum(u)-sum(g),vg,vu,c,ag))
print('day | bars | GC delta | Upstox delta | Upstox-GC | GC vol | Ux vol | corr | sign agree')
for r in res: print(r[0][5:],r[1],round(r[2]),round(r[3]),round(r[4]),round(r[5]),round(r[6]),'%.2f'%r[7],'%.2f'%r[8])
pri=res[:-1]
diffs=[r[4] for r in pri]; print('prior: Upstox-GC per day median %.0f lots, range [%.0f .. %.0f]; per-bar corr median %.2f; sign agreement median %.2f'%(statistics.median(diffs),min(diffs),max(diffs),statistics.median(r[7] for r in pri),statistics.median(r[8] for r in pri)))
print('today diff %.0f lots -> pctile %.0f of prior diffs'%(res[-1][4],pct(diffs,res[-1][4])))
