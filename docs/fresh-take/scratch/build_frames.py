"""Assemble the mockup frames. Every number is computed from data with sec <= T (causal)."""
import json, datetime, math
from fold import *

OUT = 'C:/Users/kaam/Desktop/operator mode/tapemap/docs/fresh-take/scratch/frames.json'
SESS = {}


def tt(x):
    h, m = x.split(':')
    return int(h)*3600+int(m)*60


def sess(idx, day):
    k = (idx, day)
    if k not in SESS:
        d, rl, recs = replay(idx, day)
        pday = prev_full_day(idx, day)
        prof = profile(idx, pday)
        vs = []
        if idx == 'NIFTY' and pday:
            bucket = Day(idx, pday).v[-1][5]/300.0
            vs = vpin_series(d, bucket)
        SESS[k] = (d, rl, recs, pday, prof, vs)
    return SESS[k]


def lab(v):
    return v


def ribbon(recs, T):
    segs = []
    for t in sorted(recs):
        if t > T:
            break
        k = recs[t]['shown']
        if segs and segs[-1][2] == k[0] and segs[-1][3] == k[1]:
            segs[-1][1] = t+60
        else:
            segs.append([t, t+60, k[0], k[1]])
    return segs


def build_index(idx, day, T):
    d, rl, recs, pday, prof, vs = sess(idx, day)
    if T not in recs:
        return None
    r = dict(recs[T])
    reg, dr, pin = r['shown']
    held = (T - r['since'])//60 + 1
    rr = dict(r)
    rr['regime'], rr['dir'] = reg, dr
    rr['idx'] = idx
    rr['pin'] = pin
    sn = d.snap(T)
    basis = r['basis']
    atm = sn['atm']
    ce = sn['ce'][atm]
    pe = sn['pe'][atm]
    spr = d.spread(sn)
    start = d.v[0][0]
    early = (T - start) < 1800
    partial = r['partial']
    F = r['F']
    iv_ = r['iv']
    pr_ = iv_*F*math.sqrt(30/94500) if iv_ else None
    d5_ = d.delta_sum(T, 300)[0]
    drv = ((F - r['open'])/pr_) if pr_ else None
    drive = dict(pts=F - r['open'], ratio=drv, d5=d5_, open=r['open'])
    if reg == 'UNCLEAR' and early and drv is not None and abs(drv) >= 1.0 and d5_*(F - r['open']) > 0:
        reg = 'DRIVE'
        dr = 1 if F > r['open'] else -1
        rr['regime'], rr['dir'] = reg, dr
        plays_ = []
        for nm, dirn, kind, side in EXPR:
            if dirn == dr:
                lg = dict(place=G, oi=N, flow=G, price=(G if kind == 'buy' else A), clock=G)
                plays_.append(dict(name=nm, dir=dirn, kind=kind, side=side, lights=lg, status='HALF', why=''))
            else:
                plays_.append(dict(name=nm, dir=dirn, kind=kind, side=side, lights=dict(place=N, oi=N, flow=N, price=N, clock=G), status='NO', why='drive ulta'))
    else:
        plays_ = all_plays(rr, T)
    # EARLY / PARTIAL cap: nothing above HALF, and say why
    for p in plays_:
        if p['status'] == 'OK' and (early or partial):
            p['status'] = 'HALF'
    # walls
    wce, wpe = walls(d, T, sn)
    levels = []
    F = r['F']
    levels.append(dict(p=r['vwap'], tag='FUT', nm='VWAP', kind='vwap'))
    if r['ready']:
        for k in (1, 2):
            levels.append(dict(p=r['vwap']+k*r['sigma'], tag='FUT', nm='VWAP +%dσ' % k, kind='band'))
            levels.append(dict(p=r['vwap']-k*r['sigma'], tag='FUT', nm='VWAP -%dσ' % k, kind='band'))
    levels.append(dict(p=r['hi'], tag='FUT', nm='Day high', kind='day'))
    levels.append(dict(p=r['lo'], tag='FUT', nm='Day low', kind='day'))
    levels.append(dict(p=r['open'], tag='FUT', nm='Open (09:17 print)' if not partial else 'Feed start', kind='day'))
    if prof:
        levels.append(dict(p=prof['poc'], tag='FUT', nm='Kal POC', kind='prev'))
        levels.append(dict(p=prof['vah'], tag='FUT', nm='Kal VAH', kind='prev'))
        levels.append(dict(p=prof['val'], tag='FUT', nm='Kal VAL', kind='prev'))
        levels.append(dict(p=prof['close'], tag='FUT', nm='Kal close', kind='prev'))
        for h in prof['hvn']:
            levels.append(dict(p=h, tag='FUT', nm='Kal HVN', kind='prev'))
        for h in prof['lvn']:
            levels.append(dict(p=h, tag='FUT', nm='Kal LVN', kind='prev'))
    for k, oi, chg in wce:
        levels.append(dict(p=k+basis, tag='STRIKE', nm='CE wall %d' % k, kind='wall', strike=k, oi=oi, chg=chg, side='ce'))
    for k, oi, chg in wpe:
        levels.append(dict(p=k+basis, tag='STRIKE', nm='PE wall %d' % k, kind='wall', strike=k, oi=oi, chg=chg, side='pe'))
    if pin:
        levels.append(dict(p=pin+basis, tag='STRIKE', nm='Pin %d' % pin, kind='pin', strike=pin))
    out = dict(
        idx=idx, lot=LOT[idx], step=STEP[idx], reg=reg, dir=dr, pin=pin, since=fmt(r['since']), held=held,
        raw=r['regime'], rawdir=r['dir'], phase=r['phase'], flip=r['flip'], early=early, partial=partial, ready=r['ready'],
        F=F, spot=r['spot'], basis=basis, vwap=r['vwap'], sig=r['sigma'], z=r['z'], hi=r['hi'], lo=r['lo'], open=r['open'], atm=atm,
        drive=drive, up_share=r['up_share'], dn_share=r['dn_share'], cross=r['cross'], nwin=r['nwin'],
        wr=r['wr'], ce30=r['ce30'], pe30=r['pe30'], span=r['span']/60.0,
        fl15=r['fl15'], d15=r['d15'], v15=r['v15'], d30=r['d30'], v30=r['v30'], dp15=r['dp15'],
        foi=({'pd': r['foi'][0], 'od': r['foi'][1], 'dp': r['foi'][2], 'doi': r['foi'][3]} if r['foi'] else None),
        used=r['used'], disp=r['disp'], ruler=r['ruler'], moved30=r.get('moved30'), priced30=r.get('priced30'), iv=r['iv'],
        vpin=vpin_at(vs, T) if vs else None,
        cost=dict(ce=ce['ltp'], pe=pe['ltp'], spr=spr, strad=ce['ltp']+pe['ltp']),
        expiry=sn_expiry(d, T), walls=dict(ce=wce, pe=wpe), levels=levels, plays=plays_,
        ribbon=ribbon(recs, T), prev=(dict(day=pday, **{k: v for k, v in prof.items() if k not in ('day',)}) if prof else None),
        stop=r.get('stop'),
    )
    return out


def sn_expiry(d, T):
    i = bisect.bisect_right(d.chs, T)-1
    return d.ch[i].get('expiry')


def trade_block(idx, day, expr, Te, T):
    """hypothetical position: expr like 'SELL CE'. entry thesis lights from the entry minute, fold lights now."""
    d, rl, recs, pday, prof, vs = sess(idx, day)
    kind, side = expr.split()
    dirn = +1 if (expr in ('BUY CE', 'SELL PE')) else -1
    sn_e = d.snap(Te)
    sn_n = d.snap(T)
    k = sn_e['atm']
    ent = sn_e[side.lower()][k]['ltp']
    now = sn_n[side.lower()][k]['ltp']
    pts = (now-ent) if kind == 'BUY' else (ent-now)
    vpe = vpin_at(vs, Te) if vs else None
    vpn = vpin_at(vs, T) if vs else None
    rE = dict(recs[Te])
    rE['regime'], rE['dir'] = rE['shown'][0], rE['shown'][1]
    pe_rows = {p['name']: p for p in all_plays(rE, Te)}
    # persistence for FOLD: three consecutive minutes
    seq = []
    for t in range(T-120, T+1, 60):
        vp_t = vpin_at(vs, t) if vs else None
        L, v = fold_lights(recs, t, dirn, vpe, vp_t)
        seq.append((L, v))
    L, v = seq[-1]
    if v == 'FOLD' and not all(x[1] == 'FOLD' for x in seq):
        v = 'WATCH'
    F_e = recs[Te]['F']
    return dict(expr=expr, kind=kind, side=side, strike=k, entry_t=fmt(Te), entry_F=F_e, entry_z=recs[Te]['z'], entry_vwap=recs[Te]['vwap'],
                entry_prem=ent, now_prem=now, pts=pts, rupees=pts*LOT[idx], mins=(T-Te)//60, dirn=dirn,
                thesis=pe_rows[expr]['lights'], thesis_note=None, fold=L, verdict=v, vpin_e=vpe, vpin_n=vpn,
                entry_status=pe_rows[expr]['status'], entry_reg=rE['regime'], entry_dir=rE['dir'], entry_wr=rE['wr'], entry_fl=rE['fl15'])


def prestate(day):
    out = {}
    for idx in IDXS:
        pday = prev_full_day(idx, day)
        prof = profile(idx, pday)
        d = Day(idx, pday)
        sn = d.snap(15*3600+29*60)
        wce, wpe = walls(d, 15*3600+29*60, sn)
        # today's expiry from today's chain
        dd = Day(idx, day)
        exp = dd.ch[0].get('expiry') if dd.ch else None
        out[idx] = dict(idx=idx, prev=dict(day=pday, **{k: v for k, v in prof.items() if k != 'day'}), spot_close=sn['spot'],
                        walls=dict(ce=wce, pe=wpe), expiry=exp, lot=LOT[idx], step=STEP[idx])
    return out


FR = [
    ('PRE', '2026-10-08', None, 'Pre-open'),
    ('A', '2026-10-08', '09:20', 'Open: kam data'),
    ('B', '2026-10-08', '09:50', 'Banta hua'),
    ('C', '2026-10-08', '11:32', 'Entry check: OK'),
    ('D', '2026-10-08', '12:10', 'Trade mein: hold?'),
    ('E', '2026-10-05', '10:30', 'Saaf nahi'),
    ('F', '2026-09-29', '10:50', 'Palat? (TURN)'),
    ('G', '2026-09-30', '13:46', 'Trade mein: FOLD'),
    ('H', '2026-09-25', '12:35', 'Pin / chop'),
    ('I', '2026-10-07', '13:30', 'Der se start'),
    ('J', '2026-09-24', '09:22', 'Early drive'),
]
TRADES = {'D': ('NIFTY', 'SELL CE', '11:32'), 'G': ('NIFTY', 'BUY CE', '13:11')}

if __name__ == '__main__':
    frames = []
    for fid, day, hm, label in FR:
        f = dict(id=fid, day=day, label=label, dow=datetime.date.fromisoformat(day).strftime('%a'))
        if hm is None:
            f['pre'] = prestate(day)
            f['time'] = '08:55'
        else:
            T = tt(hm)
            f['time'] = hm
            f['idxs'] = {}
            for idx in IDXS:
                x = build_index(idx, day, T)
                if x:
                    f['idxs'][idx] = x
            if fid in TRADES:
                idx, expr, ent = TRADES[fid]
                f['trade'] = dict(idx=idx, **trade_block(idx, day, expr, tt(ent), T))
        frames.append(f)
    json.dump(frames, open(OUT, 'w'), default=lambda o: None)
    print('frames', len(frames), 'bytes', len(open(OUT).read()))
    for f in frames:
        if 'idxs' in f:
            print(f['id'], f['day'][5:], f['time'], ' | '.join('%s %s%s %s' % (i, x['reg'], {1: '↑', -1: '↓', 0: ''}[x['dir']], ','.join('%s:%s' % (p['name'], p['status']) for p in x['plays'] if p['status'] != 'NO')) for i, x in f['idxs'].items()))
        if 'trade' in f:
            t = f['trade']
            print('   trade', t['expr'], t['strike'], 'entry', t['entry_t'], '@', t['entry_prem'], 'now', t['now_prem'], 'pts %.1f' % t['pts'], t['fold'], t['verdict'])
