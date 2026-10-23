"""Order-flow study helpers (SEEN data only). GC = GoCharting 5-min bars (tape_NIFTY), path = REST 3-min futures bars
(5-16 Oct, /api/contract) or tick-built 3-min bars (22 Sep-1 Oct)."""
import json, glob, math, datetime, bisect, collections, sys
sys.path.append('C:/Users/kaam/Desktop/operator mode/tapemap')
from lib import D, DAYS, fmt
import prints

def ist_sec(ms):
    d = datetime.datetime.fromtimestamp(ms/1000, datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    return d.hour*3600 + d.minute*60 + d.second

def hm(sec): return '%02d:%02d' % (sec//3600, (sec % 3600)//60)

# ---------------- GoCharting bars
def gc_bars(day, fill=True):
    f = D+'tape/tape_NIFTY_%s.jsonl' % day
    try: rows = [json.loads(l) for l in open(f, encoding='utf-8')]
    except OSError: return []
    byt = {}
    for r in rows: byt[r['t']] = r          # last row for a t wins
    pb = None
    out = []
    for t in sorted(byt):
        r = dict(byt[t]); r['sec'] = ist_sec(t); r['filled'] = False
        if r.get('h') is None or r.get('l') is None: continue
        if r.get('c') is None or r.get('o') is None:
            if not fill: continue
            if pb is None: pb = path(day)
            if not pb: continue
            ends = [b['e'] for b in pb]
            i = bisect.bisect_right(ends, r['sec']+300) - 1
            j = next((k for k, b in enumerate(pb) if b['s'] <= r['sec'] < b['e']), None)
            if i < 0 or j is None: continue
            r['c'] = pb[i]['c'] if r.get('c') is None else r['c']
            r['o'] = pb[j]['o'] if r.get('o') is None else r['o']
            r['filled'] = True
        out.append(r)
    return out

def gc_vwap(bars):
    pv = v = pv2 = 0.0; out = []
    for b in bars:
        tp = (b['h']+b['l']+b['c'])/3; w = b.get('vol') or 0
        if w: pv += tp*w; v += w; pv2 += tp*tp*w
        vw = pv/v if v else None
        sg = math.sqrt(max(0, pv2/v - vw*vw)) if v else 0
        out.append((vw, sg))
    return out

# ---------------- price path (3-min bars) with VWAP / sigma
_rest = None
def _load_rest():
    global _rest
    if _rest is None:
        d = json.load(open('C:/Users/kaam/Desktop/operator mode/tapemap/docs/fresh-take/scratch/contract10_NIFTY.json'))
        s = d['index_series']; _rest = collections.defaultdict(list)
        for b, v, day in zip(s['bars'], s['vwap'], s['bar_days']):
            h, m = b['t'].split(':'); st = int(h)*3600+int(m)*60
            _rest[day].append(dict(s=st, e=st+180, o=b['o'], h=b['h'], l=b['l'], c=b['c'], vwap=v['vwap'], sig=v['u1']-v['vwap'], oi=b['oi'], v=b['v']))
    return _rest

def tick_path(day):
    from engine import Day
    d = Day('NIFTY', day)
    if not d.v: return []
    out = {}
    for x in d.v:
        if x[0] > 15*3600+30*60: break
        k = (x[0]-(9*3600+15*60))//180
        b = out.get(k)
        if b is None:
            out[k] = b = dict(s=9*3600+15*60+k*180, e=9*3600+15*60+k*180+180, o=x[1], h=x[1], l=x[1], c=x[1], vwap=x[2], sig=x[3], oi=x[4])
        b['h'] = max(b['h'], x[1]); b['l'] = min(b['l'], x[1]); b['c'] = x[1]; b['vwap'] = x[2]; b['sig'] = x[3]; b['oi'] = x[4]
    return [out[k] for k in sorted(out)]

def path(day):
    r = _load_rest()
    if day in r and len(r[day]) > 100: return r[day]
    if day >= '2026-09-22': return tick_path(day)
    return []

def crosses(pb):
    cr = 0; st = 0
    for b in pb:
        if b['s'] < 9*3600+30*60 or b['sig'] <= 0: continue
        z = (b['c']-b['vwap'])/b['sig']
        if z > 0.25:
            if st == -1: cr += 1
            st = 1
        elif z < -0.25:
            if st == 1: cr += 1
            st = -1
    return cr

def daytype(day):
    pb = path(day)
    if not pb: return None, None
    c = crosses(pb)
    return c, ('trend(<=4)' if c <= 4 else 'chop(>=9)' if c >= 9 else 'mid(5-8)')

# ---------------- outcome: 0.5 unit with / against within 60 min
def unit(p0, sig): return max(sig, 0.001*p0)

def outcome(pb, T_r, w, thresh=0.5, horizon=3600):
    """P0 = close of the last 3-min bar ending <= T_r. Returns (label, p0, U, minutes_to_first) ; label in WITH/AGAINST/TIE/NONE/END"""
    ends = [b['e'] for b in pb]
    i = bisect.bisect_right(ends, T_r) - 1
    if i < 0: return None
    b0 = pb[i]; p0 = b0['c']; U = unit(p0, b0['sig'])
    up, dn = p0 + w*thresh*U, p0 - w*thresh*U
    t_end = b0['e'] + horizon
    last_e = b0['e']
    for b in pb[i+1:]:
        if b['s'] >= t_end: break
        last_e = b['e']
        hit_w = (b['h'] >= up) if w > 0 else (b['l'] <= up)
        hit_a = (b['l'] <= dn) if w > 0 else (b['h'] >= dn)
        if hit_w and hit_a: return ('TIE', p0, U, (b['e']-b0['e'])//60)
        if hit_w: return ('WITH', p0, U, (b['e']-b0['e'])//60)
        if hit_a: return ('AGAINST', p0, U, (b['e']-b0['e'])//60)
    return ('NONE' if last_e >= t_end - 180 else 'END', p0, U, None)

def local_extreme_gap(pb, T_r, w, lookback=1800):
    """points from the winner-opposite local extreme of the last `lookback` seconds: buyers win (w>0) -> distance of last close from the low"""
    ends = [b['e'] for b in pb]; i = bisect.bisect_right(ends, T_r) - 1
    if i < 0: return None
    win = [b for b in pb[:i+1] if b['e'] > T_r - lookback]
    return win

# ---------------- marks
def marks(day):
    f = D+'tape/ofd_marks_NIFTY_%s.jsonl' % day
    try: rows = [json.loads(l) for l in open(f, encoding='utf-8')]
    except OSError: return [], 0
    n_raw = len(rows)
    # collapse: same bar, kind, side, price within 10 pts -> keep the largest
    rows.sort(key=lambda r: (r['t'], r['kind'], r['side'], r['p']))
    out = []
    for r in rows:
        dup = next((q for q in out if q['t'] == r['t'] and q['kind'] == r['kind'] and q['side'] == r['side'] and abs(q['p']-r['p']) <= 10), None)
        if dup:
            if r['size'] > dup['size']: dup.update(p=r['p'], size=r['size'])
            dup['n'] += 1
        else:
            q = dict(r); q['n'] = 1; q['sec'] = ist_sec(r['t']); out.append(q)
    return out, n_raw

def decoder_events(day):
    f = D+'decoder/decoder_%s.jsonl' % day
    try: rows = [json.loads(l) for l in open(f, encoding='utf-8')]
    except OSError: return []
    ev = {}
    for r in rows:
        if r.get('row') == 'event': ev[r['event']['id']] = r['event']
    return list(ev.values())

# ---------------- prior-day levels from GC ladders
def prior_day(day, days):
    prev = [d for d in days if d < day]
    return prev[-1] if prev else None

def prior_nodes(pday):
    bars = gc_bars(pday)
    if len(bars) < 68: return None
    pr = prints.profile(bars)
    if not pr: return None
    nd = prints.nodes(pr)
    return dict(poc=pr['poc'], vah=pr['vah'], val=pr['val'], nodes=nd, hi=max(b['h'] for b in bars), lo=min(b['l'] for b in bars), close=bars[-1]['c'], nbars=len(bars))
