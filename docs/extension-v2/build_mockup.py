"""build_mockup.py -- the extension-v2 mockup, computed. Every mark, line, chip and panel row comes out of a rule below,
applied to recorded data at or before the frame's time T. Nothing is placed by hand; what cannot be computed is "?".

    python -B build_mockup.py          -> frames.json, mockup.html (and a short stdout trace)

Reads only. One GET (cached in cache/): /api/contract?idx=NIFTY&days=10&strike=23000&side=CE (index_series).
Reuses: fresh-take/scratch/fs_lib.py (loaders, features, R, quantile), tapemap/read.py via tools/read_replay.py (THE
READ), tapemap/prints.py (profile), and the extension's own engine (board.js / decoder.js, through before.mjs) for the
"before" count.
"""
import sys
sys.dont_write_bytecode = True
import bisect, collections, datetime, glob, gzip, html, json, math, os, statistics, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
TM = os.path.normpath(os.path.join(HERE, '..', '..')).replace('\\', '/')            # tapemap/
DATA = TM + '/data/'
SCR = TM + '/docs/fresh-take/scratch'
for p in (SCR, TM, TM + '/tools'):
    if p not in sys.path: sys.path.insert(0, p)
import fs_lib as FS          # noqa: E402  (the study's own loaders and features: flow states match the study's inputs)
import of_lib                # noqa: E402
import prints                # noqa: E402
import read                  # noqa: E402
import read_replay           # noqa: E402

LOT, STEP, ROW = 65, 50, 5
FRAMES = [('F1', '2026-10-16', '09:40', 'around the day low'),
          ('F2', '2026-10-16', '10:25', 'just after the high (23,155 at 10:18)'),
          ('F3', '2026-10-12', '10:30', 'down day; buyer marks at 22,500-22,525 later failed')]
WINDOW_MIN = 150                         # last 2.5 h of closed 5-min bars
PLACE_SIG = 0.25                         # "at a place" = within 0.25 sigma
BIG_P, NOTABLE_P = 90, 70
BASIS_OK = (20, 120)                     # plausible fut-minus-spot band (other recorded days 6-13 Oct: medians 53-89)
UX_GAPS = {'2026-10-12': [('11:20', '12:58')], '2026-10-16': [('09:48', '11:12'), ('11:17', '15:30')]}
ERA_B_FROM = '2026-10-05'


def hm(s): return '%02d:%02d' % (s // 3600, s % 3600 // 60)
def sec_hm(t): h, m = t.split(':')[:2]; return int(h) * 3600 + int(m) * 60
def sec_ms(ms): return int(ms / 1000 + 19800) % 86400
def pct(pop, x):                          # share of the population strictly below x, 0-100 (floored: p90 means >= 90%)
    return None if x is None or not pop else int(100 * bisect.bisect_left(pop, x) / len(pop))
def fmt(p): return '{:,.0f}'.format(p) if p is not None else '?'


def rows_jsonl(p):
    op = gzip.open if p.endswith('.gz') else open
    with op(p, 'rt', encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


# ---------------------------------------------------------------------------------------------- index_series (3-min fut)
def index_series():
    os.makedirs(HERE + '/cache', exist_ok=True)
    c = HERE + '/cache/contract_NIFTY_10d.json'
    if not os.path.exists(c):
        url = 'http://127.0.0.1:8765/api/contract?idx=NIFTY&days=10&strike=23000&side=CE'
        with urllib.request.urlopen(url, timeout=120) as r, open(c, 'wb') as f: f.write(r.read())
    s = json.load(open(c, encoding='utf-8'))['index_series']
    out = collections.defaultdict(list)
    for b, v, day in zip(s['bars'], s['vwap'], s['bar_days']):
        st = sec_hm(b['t'])
        out[day].append(dict(s=st, e=st + 180, o=b['o'], h=b['h'], l=b['l'], c=b['c'], v=b['v'] / LOT, oi=b['oi'],
                             vwap=v['vwap'], sig=v['u1'] - v['vwap']))
    return out


IX = index_series()


def ix_closed(day, T):
    return [b for b in IX[day] if b['e'] <= T]


def band_at(day, t):
    """VWAP and sigma of the last 3-min bar closed at or before t (the band she reads)."""
    bs = ix_closed(day, t)
    return (bs[-1]['vwap'], bs[-1]['sig']) if bs else (None, None)


def prev_day(day):
    ds = sorted(d for d in IX if d < day)
    return ds[-1] if ds else None


# ---------------------------------------------------------------------------------------------- GoCharting bars
GC_ALL = FS.gc_all()                       # fs_lib: every GC day, o/c filled from the REST path where null (of_lib)
GC_RAW = {}                                # the raw rows (ladders), by day and bar start sec


def gc_raw(day):
    if day not in GC_RAW:
        d = {}
        for r in rows_jsonl(DATA + 'tape/tape_NIFTY_%s.jsonl' % day): d[r['t']] = r
        filled = {b['t']: b for b in of_lib.gc_bars(day)}
        out = []
        for t in sorted(d):
            r = dict(d[t]); f = filled.get(t)
            r['s'] = sec_ms(t)
            r['filled'] = bool(f and f.get('filled'))
            if f: r['o'], r['c'] = f['o'], f['c']
            out.append(r)
        GC_RAW[day] = out
    return GC_RAW[day]


def gc_closed(day, T):
    return [b for b in gc_raw(day) if b['s'] + 300 <= T and b.get('o') is not None and b.get('c') is not None]


def check_index_vs_gc(day, T):
    """index_series against GC for the same minutes: 15-min windows, high / low / close and volume."""
    gc = {b['s']: b for b in gc_closed(day, T)}
    worst_px, worst_v, n, rows = 0.0, 0.0, 0, []
    for w0 in range(33300, T - 899, 900):
        i3 = [b for b in IX[day] if w0 <= b['s'] < w0 + 900 and b['e'] <= T]
        g5 = [gc[w0 + k] for k in (0, 300, 600) if w0 + k in gc]
        if len(i3) < 5 or len(g5) < 3: continue
        n += 1
        worst_px = max(worst_px, abs(max(b['h'] for b in i3) - max(b['h'] for b in g5)), abs(min(b['l'] for b in i3) - min(b['l'] for b in g5)))
        vi, vg = sum(b['v'] for b in i3), sum(b['vol'] for b in g5)
        worst_v = max(worst_v, abs(vi - vg) / vg if vg else 0)
        rows.append(dict(w=hm(w0), ix_hl=[max(b['h'] for b in i3), min(b['l'] for b in i3)], gc_hl=[max(b['h'] for b in g5), min(b['l'] for b in g5)],
                         ix_vol=round(vi), gc_vol=vg))
    ok = n > 0 and worst_px <= 5 and worst_v <= 0.02
    return dict(windows=n, max_px_diff=round(worst_px, 1), max_vol_diff=round(100 * worst_v, 1), agree=ok, rows=rows)


# ---------------------------------------------------------------------------------------------- FLOW STATE (study §6)
class FlowRef:
    """FLOW-STATE-STUDY §6 states on one source, reference = recorded days BEFORE the target day (no look-ahead).
    For both target days this equals the study's leave-one-day-out set (12 Oct is the last >= 40-bar GC day).
    SIZE = |delta| / the same-15-min-slot median |delta| of the reference days; RVOL = bar volume / median of today's
    previous 12 bars (fs1.py's adaptive RVOL12: undefined before the 13th bar); R from fs_lib.feats; thin = volume <=
    p10 of the slot on the reference days."""

    def __init__(self, days, target_bars):
        self.days = days
        self.sm, self.vp10 = self._slot(days, set())
        bv, br = FS.bases(days, set())
        self.F = FS.feats(target_bars, bv, br)
        size, share, rv12 = [], [], []
        for r in days:                                    # each reference day ranked with a base that excludes it
            sm_r, _ = self._slot(days, {r})
            bv2, br2 = FS.bases(days, {r})
            for i, b in enumerate(FS.feats(days[r], bv2, br2)):
                m = sm_r.get(b['s'] // 900)
                if m: size.append(abs(b['d']) / m)
                if b['v']: share.append(abs(b['d']) / b['v'])
                x = self._rv12(days[r], i)
                if x is not None: rv12.append(x)
        self.P = {'size': sorted(size), 'share': sorted(share), 'rv12': sorted(rv12)}
        self.TH = {k: {p: FS.q(v, p / 100) for p in (70, 90)} for k, v in self.P.items()}
        self.n_days = len(days)

    @staticmethod
    def _slot(days, skip):
        a, v = collections.defaultdict(list), collections.defaultdict(list)
        for d, bars in days.items():
            if d in skip: continue
            for b in bars:
                a[b['s'] // 900].append(abs(b['d'])); v[b['s'] // 900].append(b['v'])
        return {k: FS.med(x) for k, x in a.items()}, {k: FS.q(sorted(x), 0.10) for k, x in v.items()}

    @staticmethod
    def _rv12(bars, i):
        if i < 12: return None
        m = FS.med([x['v'] for x in bars[i - 12:i]])
        return bars[i]['v'] / m if m else None

    def state(self, i):
        b = self.F[i]
        m = self.sm.get(b['s'] // 900)
        size = abs(b['d']) / m if m else None
        share = abs(b['d']) / b['v'] if b['v'] else None
        rv = self._rv12(self.F, i)
        R = b['res']
        thin = b['v'] <= self.vp10.get(b['s'] // 900, -1)
        th = self.TH
        out = dict(size=None if size is None else round(size, 2), size_p=pct(self.P['size'], size),
                   share=None if share is None else round(share, 2), rv12=None if rv is None else round(rv, 2),
                   rv12_p=pct(self.P['rv12'], rv), R=None if R is None else round(R, 2), thin=thin,
                   d=b['d'], v=b['v'], dir=(1 if b['d'] > 0 else -1 if b['d'] < 0 else 0))
        st, why = None, []
        if size is not None and size >= th['size'][90] and not thin:
            if R is None: st, why = '?', ['R ? (no open/close)']
            else: st = 'PUSH' if R >= FS.RES_MIN else 'CLIMAX'
        if st is None and rv is not None and size is not None and rv >= th['rv12'][90] and size <= th['size'][70]:
            st = 'ROKA'
        if st is None:
            if rv is None:
                st, why = 'no read', ['RVOL12 ? (fewer than 12 bars today)']
            elif size is not None and size <= th['size'][70] and share <= th['share'][70] and rv <= th['rv12'][70]:
                st = 'noise'
            else:
                st = 'no read'
        out.update(state=st, why=why)
        return out


def flow_states(day, T, src):
    if src == 'GC':
        ref = {d: b for d, b in FS.gc_days().items() if d < day}
        tb = [b for b in GC_ALL.get(day, []) if b['s'] + 300 <= T]
    else:
        ref = {d: b for d, b in FS.ux_days('NIFTY').items() if d < day}
        tb = [b for b in FS._clean(FS._rows(DATA + 'tape/ux_NIFTY_%s.jsonl' % day)) if b['s'] + 300 <= T]
    if not tb: return {}, None
    fr = FlowRef(ref, tb)
    return {b['s']: fr.state(i) for i, b in enumerate(fr.F)}, fr




def vwap_check(day, T):
    """index_series VWAP / sigma at T against the same recurrence-free hlc3 VWAP rebuilt from the GC 5-min bars."""
    gb = [dict(b, vol=b['vol']) for b in gc_closed(day, T)]
    if not gb: return None
    gv, gs = of_lib.gc_vwap(gb)[-1]
    iv, isg = band_at(day, T)
    return dict(ix_vwap=round(iv, 1), gc_vwap=round(gv, 1), ix_sig=round(isg, 1), gc_sig=round(gs, 1),
                d_vwap=round(iv - gv, 1), d_vwap_sig=round((iv - gv) / isg, 2) if isg else None,
                sig_ratio=round(gs / isg, 2) if isg else None,
                agree=bool(isg and abs(iv - gv) <= 0.25 * isg and 0.8 <= gs / isg <= 1.25))


# ---------------------------------------------------------------------------------------------- THE READ (read.py)
def gc_pre(day, first_tick):
    """server._read_gc_pre: GC bars that closed before the first futures tick -> (sec, vol, buy) in contracts."""
    out = []
    for r in gc_raw(day):
        if r['s'] + 300 <= first_tick and isinstance(r.get('vol'), (int, float)) and isinstance(r.get('buy'), (int, float)):
            out.append((r['s'] + 299, round(r['vol'] * LOT), round(r['buy'] * LOT)))
    return sorted(set(out))


def read_at(day, T):
    """THE READ at T, replayed the way tools/read_replay.py does (v2feed + ux 5-min bars), with server._read_gc_pre's
    late-start flow. A chain-recorder gap before T is filled [I]: OI from chain_backfill (REST minutes, OI = the last
    recorded OI + the REST oi_chg difference), flow and price from the GC 5-min bars (o/c from the 3-min futures)."""
    import v2feed
    Dy = v2feed.Day(day, DATA.rstrip('/')); Dy.refresh(); s = Dy.idx['NIFTY']
    first = s.bars[0][0] if s.bars else 86400
    X = read.from_v2(s, LOT, gc_pre(day, first))
    X = {k: (list(v) if isinstance(v, list) else v) for k, v in X.items()}
    bars5 = rows_jsonl(DATA + 'tape/ux_NIFTY_%s.jsonl' % day)
    patch = []
    t = X['t']
    gap = next(((t[i], t[i + 1]) for i in range(len(t) - 1) if t[i + 1] - t[i] > 120 and t[i] < T), None)
    bfp = DATA + 'chain_backfill/backfill_NIFTY_%s.jsonl' % day
    if gap and os.path.exists(bfp):
        g0, g1 = gap
        ia = max(i for i in range(len(t)) if t[i] <= g0)
        bf = {sec_hm(r['t']): r for r in rows_jsonl(bfp) if r.get('backfilled') and r.get('spot') is not None}
        ma = (g0 // 60) * 60
        if ma in bf:
            anc = bf[ma]['k']
            ins = []
            for m in sorted(bf):
                if not (g0 < m and m + 60 <= g1 and m + 60 <= T): continue      # a minute is known once it has closed
                row = {'t': m, 'spot': round(bf[m]['spot'], 1)}
                for li, leg in enumerate(('ce', 'pe')):
                    oi = []
                    for j, k in enumerate(X['ks']):
                        key = str(int(k)); a = X[leg + '_oi'][ia][j]
                        c1, c0 = (bf[m]['k'].get(key) or [None, None])[li], (anc.get(key) or [None, None])[li]
                        oi.append(None if a is None or c1 is None or c0 is None else a + round((c1 - c0) / 1000))
                    row[leg + '_oi'] = oi
                    px = []
                    for j, k in enumerate(X['ks']):
                        v = (bf[m].get('px') or {}).get(str(int(k)))
                        px.append(None if not v or v[li] is None else round(v[li] * 20))
                    row[leg + '_ltp'] = px
                ins.append(row)
            at = ia + 1
            for key in ('t', 'spot', 'ce_oi', 'pe_oi', 'ce_ltp', 'pe_ltp'):
                X[key] = X[key][:at] + [r[key] for r in ins] + X[key][at:]
            if ins: patch.append('chain %s-%s: %d REST minutes [I]' % (hm(g0), hm(min(g1, T)), len(ins)))
    # futures ticks: fill a tick gap before T with the GC bars inside it (vol / buy in contracts, close as the price)
    X['ticks'] = list(X['bars'])                     # the real futures ticks only (3-min delta for READ-V2 §E)
    secs = [b[0] for b in X['bars']]
    tg = next(((secs[i], secs[i + 1]) for i in range(len(secs) - 1) if secs[i + 1] - secs[i] > 120 and secs[i] < T), None)
    if tg:
        add = [[r['s'] + 299, round(r['c'] * 10), round(r['vol'] * LOT), round(r['buy'] * LOT)] for r in gc_raw(day)
               if r['s'] >= tg[0] and r['s'] + 300 <= min(tg[1], T) and r.get('c') is not None]
        if add:
            X['bars'] = sorted(X['bars'] + add, key=lambda b: b[0])
            patch.append('futures ticks %s-%s: %d GC 5-min bars as flow [I]' % (hm(tg[0]), hm(min(tg[1], T)), len(add)))
    # 5-min price bars: the ux file's gap filled with the GC bars (filled o/c are [I])
    ux_last = max([sec_ms(b['t']) for b in bars5 if sec_ms(b['t']) + 300 <= T] or [0])
    extra = [dict(t=r['t'], o=r['o'], h=r['h'], l=r['l'], c=r['c'], vol=r['vol'], ladder=r.get('ladder'))
             for r in gc_raw(day) if ux_last and r['s'] > ux_last and r['s'] + 300 <= T and r.get('c') is not None]
    if extra:                                        # only after the ux feed stopped: the minutes live had are not touched
        bars5 = bars5 + extra
        patch.append('5-min price bars %s-%s: %d GC bars after ux stopped [I]' % (hm(ux_last + 300), hm(T), len(extra)))
    tl = read.timeline(X, bars5, None, now=T)
    return X, tl, patch


KHEL = {'TREND': 'RIDE', 'LEAN': 'RIDE', 'RANGE': 'FADE', 'WAIT': 'BAITHO'}
ARW = {1: '▲', -1: '▼', 0: ''}


# ---------------------------------------------------------------------------------------------- chain: fresh writing
def chain_series_raw(day):
    p = DATA + 'chain/chain_NIFTY_%s.jsonl' % day
    if not os.path.exists(p): p += '.gz'
    if not os.path.exists(p): return []
    out = []
    for r in rows_jsonl(p):
        if 'strikes' not in r or 'atm' not in r: continue
        sec = int(r['sec']) if 'sec' in r else sec_hm(r['ts'])
        out.append((sec, r['atm'], {s['k']: ((s.get('ce') or {}).get('oi'), (s.get('pe') or {}).get('oi')) for s in r['strikes']}))
    return out


def d30_ref(day, ndays=10):
    """Reference for 'fresh writing': 30-min OI change at ATM +/-2 strikes, CE and PE, every 5 min 09:45-15:15, pooled,
    over the last `ndays` recorded chain days before `day` (thousands of contracts)."""
    ds = sorted({os.path.basename(p)[12:22] for p in glob.glob(DATA + 'chain/chain_NIFTY_2026-*.jsonl*')})
    ds = [d for d in ds if d < day][-ndays:]
    pop = []
    for d in ds:
        rows = chain_series_raw(d)
        if not rows: continue
        ts = [r[0] for r in rows]
        for s in range(35100, 54901, 300):
            i, j = bisect.bisect_right(ts, s) - 1, bisect.bisect_right(ts, s - 1800) - 1
            if i < 0 or j < 0 or s - ts[i] > 120 or s - 1800 - ts[j] > 120: continue
            atm = rows[i][1]
            for k in (atm + STEP * n for n in range(-2, 3)):
                a, b = rows[i][2].get(k), rows[j][2].get(k)
                if not a or not b: continue
                for li in (0, 1):
                    if a[li] is not None and b[li] is not None: pop.append((a[li] - b[li]) / 1000)
    return sorted(pop), ds


def fresh_writing(X, t, ref):
    """Strikes at ATM +/-2 whose 30-min OI add (CE or PE) ranks >= p90 of the reference. [I]: OI up = writing (D2 open)."""
    if t - 1800 < 33300: return None, '30-min window opens 09:45'
    ts = X['t']
    i, j = bisect.bisect_right(ts, t) - 1, bisect.bisect_right(ts, t - 1800) - 1
    if i < 0 or j < 0 or t - ts[i] > 120 or t - 1800 - ts[j] > 120: return None, 'chain row missing near %s' % hm(t)
    atm = round(X['spot'][i] / STEP) * STEP
    out = []
    for jj, k in enumerate(X['ks']):
        if abs(k - atm) > 2 * STEP: continue
        for leg in ('ce', 'pe'):
            a, b = X[leg + '_oi'][i][jj], X[leg + '_oi'][j][jj]
            if a is None or b is None: continue
            p = pct(ref, a - b)
            if a - b > 0 and p >= BIG_P: out.append(dict(k=k, side=leg.upper(), add=a - b, rank=p))
    return out, None


# ---------------------------------------------------------------------------------------------- basis
def basis_at(day, X, T):
    """fut minus spot: median over the 3-min futures bars closed in the last 15 min, against the chain spot at each
    bar's last minute (read.basis's window; the 3-min close stands in for the 1-min futures pairs)."""
    vals = []
    for b in ix_closed(day, T):
        if b['e'] <= T - 900: continue
        i = bisect.bisect_right(X['t'], b['e'] - 1) - 1
        if i >= 0 and b['e'] - 1 - X['t'][i] <= 90: vals.append(b['c'] - X['spot'][i])
    if not vals: return None, None, 'no spot row in the last 15 min'
    v = round(statistics.median(vals), 1)
    if not BASIS_OK[0] <= v <= BASIS_OK[1]: return None, v, 'basis %+.0f implausible (other days +53..+89)' % v
    return v, v, None


# ---------------------------------------------------------------------------------------------- marks
def era_b_pop(day):
    """Era-B board marks (5 Oct on, days before `day`), deduped by (bar, kind, side, price); decoder E1 prints."""
    pop = collections.defaultdict(list)
    for p in sorted(glob.glob(DATA + 'tape/ofd_marks_NIFTY_2026-*.jsonl')):
        d = p[-16:-6]
        if not ERA_B_FROM <= d < day: continue
        seen = set()
        for r in rows_jsonl(p):
            key = (r['t'], r['kind'], r['side'], round(r['p']))
            if key in seen: continue
            seen.add(key); pop[r['kind']].append(r['size'])
    for p in sorted(glob.glob(DATA + 'decoder/decoder_2026-*.jsonl')):
        d = p[-16:-6]
        if not ERA_B_FROM <= d < day: continue
        seen = set()
        for r in rows_jsonl(p):
            if r.get('row') == 'event' and r['kind'] == 'E1' and r['id'] not in seen:
                seen.add(r['id']); pop['E1'].append(r['event']['lots'])
    return {k: sorted(v) for k, v in pop.items()}


def day_marks(day):
    seen, out = set(), []
    for r in rows_jsonl(DATA + 'tape/ofd_marks_NIFTY_%s.jsonl' % day):
        key = (r['t'], r['kind'], r['side'], round(r['p']))
        if key in seen: continue
        seen.add(key); out.append(r)
    return out


def winner(kind, side):
    return -side if kind == 'trap' else side          # the log's trap side is the TRAPPED side (ORDERFLOW-STUDY 3.2)


def chip_name(kind, w, lots=None, p=None):
    if kind == 'trap': return 'BECHNE WALE PHANSE ▲' if w > 0 else 'KHARIDNE WALE PHANSE ▼'
    if kind == 'absorption': return 'KHAREEDAR NE ROKA ▲' if w > 0 else 'BECHNE WALE NE ROKA ▼'
    if kind == 'E1': return ('BADA KHARIDAR' if w > 0 else 'BADA BECHNE WALA') + ' %s @%s' % (fmt(lots), fmt(p))
    nm = {'exhaustion': 'THAKAAN', 'initiative': 'PEHAL', 'vacuum': 'KHALI', 'climax': 'CLIMAX'}.get(kind, kind)
    return nm + (' ' + ARW[w] if w else '')


def status_at(day, p, w, t_close, T):
    """TIKA while no 3-min futures close is beyond the mark's price against its winner by more than one 5-pt row
    (board.js's own 'broken' test); TOOTA from the first such close."""
    for b in IX[day]:
        if b['e'] <= t_close or b['e'] > T: continue
        if (w > 0 and b['c'] < p - ROW) or (w < 0 and b['c'] > p + ROW):
            return 'TOOTA', hm(b['e'])
    return 'TIKA', None


# ---------------------------------------------------------------------------------------------- levels at a time
def prior_hlc(day):
    pd = prev_day(day)
    bs = IX.get(pd) or []
    if not bs: return None
    return dict(day=pd, h=max(b['h'] for b in bs), l=min(b['l'] for b in bs), c=bs[-1]['c'])


def value_at(day, t):
    pr = prints.profile([b for b in gc_raw(day) if b['s'] + 300 <= t])
    return None if not pr else dict(poc=pr['poc'], vah=pr['vah'], val=pr['val'])


def levels_at(day, t, X, ref30, prior):
    """Every 'place' the rules allow, at time t, in futures: VWAP and +/-1/2/3 sigma, yesterday's H/L/C, today's
    developing POC/VAH/VAL, and a strike with fresh writing (spot strike + the measured basis)."""
    vw, sg = band_at(day, t)
    L, notes = [], []
    if vw is not None:
        for k, nm in ((0, 'VWAP'), (1, '+1σ'), (-1, '−1σ'), (2, '+2σ'), (-2, '−2σ'), (3, '+3σ'), (-3, '−3σ')):
            L.append(dict(name=nm, p=vw + k * sg, kind='band'))
    if prior:
        for nm, key in (('KAL HIGH', 'h'), ('KAL LOW', 'l'), ('KAL CLOSE', 'c')): L.append(dict(name=nm, p=prior[key], kind='prior'))
    va = value_at(day, t)
    if va:
        for nm, key in (('POC aaj', 'poc'), ('VAH aaj', 'vah'), ('VAL aaj', 'val')): L.append(dict(name=nm, p=va[key], kind='value'))
    bs, braw, bwhy = basis_at(day, X, t)
    fw, fwhy = fresh_writing(X, t, ref30)
    if fw is None: notes.append('likhna strike ? (%s)' % fwhy)
    elif fw and bs is None: notes.append('likhna strike ? (%s)' % bwhy)
    elif fw:
        for f in fw:
            L.append(dict(name='%s %s likha' % (fmt(f['k']), f['side']), p=f['k'] + bs, spot=f['k'], kind='strike', add=f['add'], rank=f['rank']))
    return L, sg, notes, bs


# ---------------------------------------------------------------------------------------------- the trade (READ-V2 §E)
def word_at(tl, t):
    w = None
    for r in tl['rows']:
        if sec_hm(r['t']) <= t: w = r
    return w


def tick_delta(X, s, e):
    """Lots bought minus sold in [s, e) from the futures 1-s bars (v2feed quote rule). None when no tick."""
    tk = X['ticks']
    secs = [b[0] for b in tk]
    i, j = bisect.bisect_left(secs, s), bisect.bisect_left(secs, e)
    if i == j: return None
    vol = sum(b[2] for b in tk[i:j]); buy = sum(b[3] for b in tk[i:j])
    return round((2 * buy - vol) / LOT)


def run_entry_rule(day, X, tl, T, patched):
    """READ-V2 §E on closed 3-min futures bars from 09:45: TREND/LEAN d -> trigger, then stop / T1 / T2. Returns the
    trade open at T (or None) and every row the rule wrote. A bar whose delta cannot be read is '?', never a trigger."""
    rowsE, pos, armed = [], None, True
    for b in IX[day]:
        if b['s'] < 35100 or b['e'] > T: continue
        w = word_at(tl, b['e'])
        d = w['dir'] if w and w['word'] in ('TREND', 'LEAN') else 0
        vw, sg = b['vwap'], b['sig']
        if pos:
            pd = pos['d']
            if (pd < 0 and b['c'] > vw) or (pd > 0 and b['c'] < vw):
                rowsE.append(dict(t=hm(b['e']), what='STOP', px=b['c'], why='3m close %s VWAP %s' % ('>' if pd < 0 else '<', fmt(vw))))
                pos, armed = None, False
                continue
            if not pos.get('t1') and ((pd < 0 and b['l'] <= vw - 2 * sg) or (pd > 0 and b['h'] >= vw + 2 * sg)):
                pos['t1'] = hm(b['e']); rowsE.append(dict(t=hm(b['e']), what='T1', px=vw + pd * 2 * sg))
            t2 = pos['t2_fut']
            if t2 is not None and ((pd < 0 and b['l'] <= t2) or (pd > 0 and b['h'] >= t2)):
                rowsE.append(dict(t=hm(b['e']), what='T2', px=t2)); pos, armed = None, False
            continue
        if not armed:
            if d and ((d < 0 and b['l'] <= vw - 1.5 * sg) or (d > 0 and b['h'] >= vw + 1.5 * sg)): armed = True
            continue
        if not d: continue
        dl = tick_delta(X, b['s'], b['e'])
        hit = (d < 0 and b['h'] >= vw - sg and b['c'] < vw - sg) or (d > 0 and b['l'] <= vw + sg and b['c'] > vw + sg)
        if hit and dl is None:
            rowsE.append(dict(t=hm(b['e']), what='?', why='zone touched, 3m delta ? (no futures ticks)'))
            continue
        if hit and dl * d > 0:
            wall = (w.get('targets') or [{}])[0].get('k')
            bs, _, _ = basis_at(day, X, b['e'])
            wall_f = wall + bs if wall is not None and bs is not None else None
            t3, t1 = vw + d * 3 * sg, vw + d * 2 * sg
            beyond_t1 = wall_f is not None and (wall_f < t1 if d < 0 else wall_f > t1)   # a T2 nearer than T1 is no T2
            t2 = (max(t3, wall_f) if d < 0 else min(t3, wall_f)) if beyond_t1 else t3
            pos = dict(d=d, word=w['word'], t=hm(b['e']), sec=b['e'], px=b['c'], delta=dl, vwap=vw, sig=sg,
                       t2_fut=t2, t2_why='−3σ' if t2 == t3 else 'PE wall %s' % fmt(wall), t1=None)
            rowsE.append(dict(t=hm(b['e']), what='ENTRY', px=b['c'], why='%s %s: high %s >= −1σ %s, close < −1σ, 3m delta %+d' % (
                w['word'], ARW[d], fmt(b['h']), fmt(vw - sg), dl) if d < 0 else '%s %s: low %s <= +1σ %s, close > +1σ, 3m delta %+d' % (
                w['word'], ARW[d], fmt(b['l']), fmt(vw + sg), dl)))
    return pos, rowsE


def vpin_at(day, t):
    rows = [r for r in rows_jsonl(DATA + 'vpin_fast.jsonl') if r.get('day') == day and r.get('inst') == 'NIFTY-FUT:fast']
    rows = [r for r in rows if sec_hm(r['at']) <= t]
    if not rows: return None
    last = rows[-3:]
    net = sum(r['buy'] - r['sell'] for r in last)
    return dict(vpin=rows[-1]['vpin'], pct=rows[-1].get('pct'), side=1 if net > 0 else -1 if net < 0 else 0, at=rows[-1]['at'][:5])


def fold_board(day, pos, T, gc_states):
    d = pos['d']
    vT, sT = band_at(day, T)
    cT = ix_closed(day, T)[-1]['c']
    z0, z1 = (pos['px'] - pos['vwap']) / pos['sig'], (cT - vT) / sT
    rows = []
    zone_bad = (d < 0 and z1 > -0.5) or (d > 0 and z1 < 0.5)
    rows.append(dict(k='ZONE', a='%+.1fσ' % z0, b='%+.1fσ' % z1, bad=zone_bad, why='0.5σ of VWAP ke andar' if zone_bad else 'lane mein'))
    gb = [b for b in gc_raw(day) if b['s'] + 300 <= T]
    sums = [(gb[i]['s'] + 300, sum(x['delta'] for x in gb[i - 2:i + 1])) for i in range(2, len(gb))]
    def d15(t):
        xs = [v for e, v in sums if e <= t]
        return xs[-1] if xs else None
    f0, f1 = d15(pos['sec']), d15(T)
    rk = pct(sorted(abs(v) for _, v in sums), abs(f1)) if f1 is not None else None
    flow_bad = f1 is not None and f1 * d < 0 and rk is not None and rk >= 80
    rows.append(dict(k='FLOW', a='%+d' % f0 if f0 is not None else '?', b='%+d' % f1 if f1 is not None else '?', rank=rk, bad=flow_bad,
                     why='15m delta, aaj ke 15m windows mein p%s' % rk))
    ib = ix_closed(day, T)
    e_bar = [b for b in ib if b['e'] <= pos['sec']][-1]
    doi, dpx = ib[-1]['oi'] - e_bar['oi'], ib[-1]['c'] - e_bar['c']
    quad = ('naye long' if dpx > 0 else 'naye short') if doi > 0 else ('covering' if dpx > 0 else 'long exit')
    rows.append(dict(k='OI', a='%.1fL' % (e_bar['oi'] / 1e5), b='%.1fL %s' % (ib[-1]['oi'] / 1e5, quad), bad=False, rank=None,
                     why='OI rank bana nahi: against nahi gina'))
    v0, v1 = vpin_at(day, pos['sec']), vpin_at(day, T)
    vbad = bool(v1 and v1['pct'] is not None and v1['pct'] >= 0.70 and v1['side'] * d < 0)
    rows.append(dict(k='VPIN', a='%.2f' % v0['vpin'] if v0 else '?', b=('%.2f · p%d %s' % (v1['vpin'], round(100 * v1['pct']), ARW[v1['side']])) if v1 and v1['pct'] is not None else ('%.2f' % v1['vpin'] if v1 else '?'),
                     bad=vbad, why='p70+ aur ulta side' if vbad else ''))
    n = sum(1 for r in rows if r['bad'])
    return rows, ('FOLD' if n >= 2 else 'WATCH' if n == 1 else 'HOLD'), n


# ---------------------------------------------------------------------------------------------- before (today's rules)
def before_count(day, T, win_start, prior):
    bars = []
    for r in gc_raw(day):
        if r['s'] + 300 > T or r.get('o') is None or r.get('c') is None: continue
        bars.append(dict(t=r['t'], o=r['o'], h=r['h'], l=r['l'], c=r['c'], vol=r['vol'], buy=r['buy'], sell=r['sell'], delta=r['delta'],
                         oi=r.get('oi'), ladder=r['ladder'], fromTicks=r.get('fromTicks'), ivMs=300000, date=day))
    inp = json.dumps(dict(bars=bars, prior=prior or {}, winStart=win_start, T=hm(T)))
    out = subprocess.run(['node', HERE + '/before.mjs'], input=inp, capture_output=True, text=True, encoding='utf-8', timeout=300)
    if out.returncode: raise RuntimeError(out.stderr[-2000:])
    return json.loads(out.stdout)


# ---------------------------------------------------------------------------------------------- one frame
def in_gap(day, s):
    return any(sec_hm(a) <= s < sec_hm(b) for a, b in UX_GAPS.get(day, []))


def build_frame(fid, day, t, why):
    T = sec_hm(t)
    win = max(33300, T - WINDOW_MIN * 60)
    prior = prior_hlc(day)
    cov = []                                            # the "?" line: what could not be seen, and why
    # --- checks: index_series against GC; VWAP/sigma source
    chk = check_index_vs_gc(day, T)
    vchk = vwap_check(day, T)
    band_src = 'index_series (3m fut)' if (vchk and vchk['agree']) else 'GC 5m (index_series disagreed)'
    if vchk and not vchk['agree']:
        cov.append('VWAP/σ GC se (3m fut se mel nahi)')
    # --- READ
    X, tl, patch = read_at(day, T)
    rr = tl['rows'][-1] if tl['rows'] else None
    if patch: cov.append('READ %s: chain REST, flow/price GC [I]' % patch[0].split(': ')[0].split(' ')[-1])
    ref30, ref30_days = d30_ref(day)
    bs, braw, bwhy = basis_at(day, X, T)
    if bs is None: cov.append('basis ? (%+.0f, normal +53..+89) · spot ?' % braw if braw is not None else 'basis ? · spot ?')
    # --- flow states, both sources
    gcs, gcref = flow_states(day, T, 'GC')
    uxs, uxref = flow_states(day, T, 'UX')
    def src_tag(s):
        if s not in uxs or in_gap(day, s): return 'GC only'
        return 'GC+UX ✓' if uxs[s]['state'] == gcs[s]['state'] and uxs[s]['dir'] == gcs[s]['dir'] else 'GC only'
    # --- bars for the chart
    bars = []
    for r in gc_raw(day):
        if r['s'] < win or r['s'] + 300 > T: continue
        g = gcs.get(r['s'], {}); u = uxs.get(r['s'])
        cells = [[q['p'], int(q['b']), int(q['s'])] for q in prints.rebin(r['ladder'], ROW, 0)]
        tint = g.get('state') if g.get('state') in ('CLIMAX', 'ROKA') else None
        bars.append(dict(t=hm(r['s']), s=r['s'], o=r['o'], h=r['h'], l=r['l'], c=r['c'], filled=r['filled'], vol=r['vol'], delta=r['delta'],
                         cells=cells, gc=g, ux=(u or {}).get('state') if u and not in_gap(day, r['s']) else None, tint=tint,
                         tint_src=src_tag(r['s']) if tint else None))
    # --- marks: the extension's live-logged marks + the decoder's prints, each through the three rules
    pop = era_b_pop(day)
    day_ms0 = int(datetime.datetime.fromisoformat(day + 'T00:00:00+05:30').timestamp() * 1000)
    bef = before_count(day, T, day_ms0 + win * 1000, prior)
    node_keys = {(m['time'], m['kind'], round(m['p'])) for m in bef['marks']}
    cands = []
    for r in day_marks(day):
        s = sec_ms(r['t'])
        if s < win or s + 300 > T: continue
        seen_by_T = (hm(s), r['kind'], round(r['p'])) in node_keys
        if r['kind'] == 'exhaustion' and not seen_by_T: continue     # an exhaustion needs later bars: only if the engine at T sees it
        cands.append(dict(src='ofd log', kind=r['kind'], s=s, t=hm(s), p=r['p'], size=r['size'], w=winner(r['kind'], r['side']), logged_side=r['side'], engine_at_T=seen_by_T))
    for e in bef['decoder_events']:
        s = sec_hm(e['time'])
        if s < win or s + 300 > T: continue
        if e['kind'] == 'E1':
            cands.append(dict(src='decoder (node, bars <= T)', kind='E1', s=s, t=e['time'], p=e['p'], size=e['lots'], w=e['side']))
        else:
            cands.append(dict(src='decoder (node, bars <= T)', kind=e['kind'], s=s, t=e['time'], p=e['p'], size=e.get('lots'), w=e['side'], unranked=True))
    trend_day = rr and rr['word'] == 'TREND'
    for c in cands:
        c['t_close'] = c['s'] + 300
        kp = pop.get(c['kind'])
        c['rank'] = None if c.get('unranked') or c['size'] is None or not kp else pct(kp, c['size'])
        c['rank_n'] = len(kp) if kp else 0
        L, sg, lnotes, _ = levels_at(day, c['t_close'], X, ref30, prior)
        near = sorted(((abs(x['p'] - c['p']), x) for x in L), key=lambda z: z[0])
        c['sigma'] = round(sg, 1) if sg else None
        c['place'] = None
        if near and sg and near[0][0] <= PLACE_SIG * sg:
            c['place'] = dict(name=near[0][1]['name'], p=round(near[0][1]['p'], 1), dist=round(near[0][0], 1), tol=round(PLACE_SIG * sg, 1))
        c['nearest'] = dict(name=near[0][1]['name'], p=round(near[0][1]['p'], 1), dist=round(near[0][0], 1), tol=round(PLACE_SIG * sg, 1)) if near and sg else None
        c['place_notes'] = lnotes
        g = gcs.get(c['s'], {})
        c['flow'] = dict(gc=g.get('state'), gc_dir=g.get('dir'), size_p=g.get('size_p'), R=g.get('R'), ux=(uxs.get(c['s']) or {}).get('state'), tag=src_tag(c['s']))
        c['status'], c['broke_at'] = status_at(day, c['p'], c['w'], c['t_close'], T) if c['w'] else (None, None)
        drawable = c['kind'] in ('trap', 'absorption', 'E1')
        big = c['rank'] is not None and c['rank'] >= BIG_P
        flow_ok = c['flow']['gc'] in ('PUSH', 'CLIMAX', 'ROKA')
        c['rules'] = dict(kind_drawable=drawable, big=big, at_place=c['place'] is not None, flow_agrees=flow_ok)
        c['drawn'] = drawable and big and c['place'] is not None and flow_ok
        wn = []
        if not drawable: wn.append({'vacuum': 'vacuum: never drawn', 'exhaustion': 'exhaustion: no chip (never on trend days)', 'climax': 'climax mark: dropped (bar tint instead)'}.get(c['kind'], '%s: not a drawn kind' % c['kind']))
        if drawable and not big: wn.append('rank p%s < p90 (N=%d)' % (c['rank'], c['rank_n']) if c['rank'] is not None else 'rank ? (no era-B population)')
        if drawable and c['place'] is None: wn.append('no place within 0.25σ (nearest %s %s pts, tol %s)' % (c['nearest']['name'], c['nearest']['dist'], c['nearest']['tol']) if c['nearest'] else 'place ?')
        if drawable and not flow_ok: wn.append('bar flow %s' % (c['flow']['gc'] or '?'))
        c['why_not'] = wn
        c['chip'] = chip_name(c['kind'], c['w'], c['size'], c['p']) + (' · p%s' % c['rank'] if c['rank'] is not None else '') + (' · ' + c['status'] if c['status'] else '') + (' · GC only' if c['flow']['tag'] == 'GC only' else '')
    drawn = sorted([c for c in cands if c['drawn']], key=lambda c: (c['place'] is None, -(c['size'] or 0)))
    for i, c in enumerate(drawn): c['chip_shown'] = i < 6
    # --- READ -> KHEL / SIZE / PREMIUM
    word = rr['word'] if rr else None
    d = rr['dir'] if rr else 0
    khel = KHEL.get(word)
    khel_txt = (khel + (' ' + ARW[d] if d else '')) if khel else '?'
    if word == 'BAN RAHA': cov.append('KHEL ? · 09:45 se pehle word nahi')
    size_txt = 'ADHA' if khel in ('RIDE', 'FADE') else '—'
    vw, sg = band_at(day, T)
    ib = ix_closed(day, T)
    F_now = ib[-1]['c']
    b30 = [b for b in ib if b['e'] <= T - 1800]
    ch = [r for r in chain_series_full(day) if r[0] <= T]
    iv = ch[-1][1] if ch else None
    iv_age = T - ch[-1][0] if ch else None
    prem = None
    if b30 and iv:
        priced = iv * F_now * math.sqrt(30 / 94500)
        prem = dict(moved=round(abs(F_now - b30[-1]['c']), 1), priced=round(priced, 1), ratio=round(abs(F_now - b30[-1]['c']) / priced, 2), iv=round(iv, 4), iv_at=hm(ch[-1][0]))
        prem['call'] = 'KHARIDO' if prem['ratio'] >= 0.8 else 'BECHO' if prem['ratio'] <= 0.5 else 'koi call nahi'
        if iv_age and iv_age > 600: cov.append('PREM ka IV %s ka [I]' % hm(ch[-1][0]))
    elif not b30: cov.append('PREM ? · 30 min pure nahi')
    prem_txt = ('PREM %.2f %s' % (prem['ratio'], prem['call'])) if prem else 'PREM ?'
    # --- DIN
    w8 = rr['writers'] if rr else {}
    A = w8.get('A')
    absent = '?' if A is None else ('PE gayab' if A >= 0.40 else 'CE gayab' if A <= -0.40 else 'dono likh rahe')
    crosses = of_lib.crosses([dict(s=b['s'], c=b['c'], vwap=b['vwap'], sig=b['sig']) for b in ib])
    oi0, oi1, p0, p1 = ib[0]['oi'], ib[-1]['oi'], ib[0]['o'], ib[-1]['c']
    fuel = ('naye long' if p1 > p0 else 'naye short') if oi1 > oi0 else ('covering' if p1 > p0 else 'long exit')
    din = dict(A=A, absent=absent, cls=w8.get('cls'), ce=w8.get('ce'), pe=w8.get('pe'), crosses=crosses,
               fuel=fuel, oi_pct=round(100 * (oi1 - oi0) / oi0, 2), px=round(p1 - p0))
    # --- ABHI
    last_s = max(gcs) if gcs else None
    g = gcs.get(last_s, {})
    ux_last = uxs.get(last_s) if last_s is not None and not in_gap(day, last_s) else None
    if ux_last is None: agree = 'GC only'
    elif ux_last['state'] == g.get('state') and ux_last['dir'] == g.get('dir'): agree = 'GC+UX ✓'
    else: agree = 'sources disagree'
    abhi = dict(t=hm(last_s) if last_s else None, gc=g.get('state'), dir=g.get('dir'), size_p=g.get('size_p'), R=g.get('R'), rv12=g.get('rv12'),
                ux=ux_last['state'] if ux_last else None, ux_dir=ux_last['dir'] if ux_last else None, agree=agree)
    # --- SIRF BADE: ranked >= notable, newest first; the rest counted
    never = {'vacuum', 'climax'} | ({'exhaustion'} if KHEL.get(rr['word'] if rr else None) == 'RIDE' else set())
    ranked = [c for c in cands if c['rank'] is not None and c['rank'] >= NOTABLE_P and c['kind'] not in never]
    ranked.sort(key=lambda c: (-c['s'], -(c['size'] or 0)))
    sirf = []
    for c in ranked:
        row = dict(t=c['t'], ev=chip_name(c['kind'], c['w'], c['size'], c['p']), rank=c['rank'], status=c['status'], drawn=c['drawn'], tag=c['flow']['tag'], n=1)
        same = next((x for x in sirf if x['t'] == row['t'] and x['ev'] == row['ev']), None)
        if same: same['n'] += 1; same['drawn'] = same['drawn'] or row['drawn']
        else: sirf.append(row)
    baaki = len(cands) - len(ranked)
    # --- the trade (only if READ-V2 §E fired before T)
    pos, erows = run_entry_rule(day, X, tl, T, patch)
    fold = None
    if pos:
        frows, verdict, nbad = fold_board(day, pos, T, gcs)
        fold = dict(rows=frows, verdict=verdict, against=nbad, entry=pos)
    # --- lines
    Lt, sgT, lnT, _ = levels_at(day, T, X, ref30, prior)
    price = bars[-1]['c'] if bars else F_now
    lines = []
    def spot_of(pf): return None if bs is None or pf is None else round(pf - bs)
    def add_line(kind, pf, chip, rule, spot=None, pri=9):
        lines.append(dict(kind=kind, p=round(pf, 1) if pf is not None else None, spot=spot if spot is not None else spot_of(pf), chip=chip, rule=rule, pri=pri))
    if pos:
        dd = pos['d']
        add_line('kill', vw, 'KILL · 3m close %s VWAP' % ('upar' if dd < 0 else 'neeche'), 'trade: stop = 3-min close beyond VWAP (value at T)', pri=0)
        add_line('target', vw + dd * 2 * sg, 'T1 · −2σ' if dd < 0 else 'T1 · +2σ', 'trade: T1 = 2σ (value at T)', pri=1)
        add_line('entry', pos['px'], 'ENTRY · %s %s %s' % ('SELL' if dd < 0 else 'BUY', pos['word'], ARW[dd]), 'trade: entry at the trigger bar close %s' % pos['t'], pri=2)
    if word in ('TREND', 'LEAN') and rr.get('flip') is not None:
        k = rr['flip']
        if bs is not None: add_line('flip', k + bs, 'FLIP · %s %s likhne wale' % ('CE' if d < 0 else 'PE', fmt(k)), 'READ FLIP strike (spot) + basis', spot=k, pri=3)
        else: cov.append('FLIP %ss · fut ? (basis)' % fmt(k))
    if word == 'RANGE' and rr.get('box'):
        for key, side in (('top', 'CE'), ('bottom', 'PE')):
            bx = (rr['box'] or {}).get(key)
            if not bx: continue
            if bs is not None: add_line('box', bx['k'] + bs, 'BOX %s · %s %s wall' % (key.upper(), side, fmt(bx['k'])), 'READ RANGE box = biggest %s OI (spot) + basis' % side, spot=bx['k'], pri=3)
            else: cov.append('BOX %s %ss · fut ? (basis)' % (key, fmt(bx['k'])))
    real = [x for x in Lt if x['kind'] in ('prior', 'value', 'strike')]
    for above in (True, False):
        side = [x for x in real if (x['p'] > price if above else x['p'] <= price)]
        if side:
            x = min(side, key=lambda x: abs(x['p'] - price))
            nm = {'KAL HIGH': 'KAL KA HIGH', 'KAL LOW': 'KAL KA LOW', 'KAL CLOSE': 'KAL KA CLOSE'}.get(x['name'], x['name'])
            add_line(x['kind'], x['p'], nm, 'nearest real level %s price' % ('above' if above else 'below'), spot=x.get('spot'), pri=4)
    lines.sort(key=lambda x: x['pri'])
    kept = []
    for x in lines:
        if x['p'] is None or any(abs(x['p'] - y['p']) <= ROW for y in kept): continue
        kept.append(x)
    cap = 5 if pos else 2
    for i, x in enumerate(kept): x['drawn'] = i < cap
    # --- zone shading by KHEL
    zones = []
    since_s = sec_hm(rr['since']) if rr and rr.get('since') else None
    for b in bars:
        if since_s is None or b['s'] + 300 < since_s: continue          # the lane is shaded from the bar the READ formed in
        bb = [x for x in ib if x['e'] <= b['s'] + 300]
        if not bb: continue
        v, s_ = bb[-1]['vwap'], bb[-1]['sig']
        if khel == 'RIDE' and d: zones.append(dict(t=b['t'], bands=[sorted([v + d * s_, v + d * 2 * s_])]))
        elif khel == 'FADE': zones.append(dict(t=b['t'], bands=[[v + 2 * s_, v + 3 * s_], [v - 3 * s_, v - 2 * s_]]))
    # --- prior-day HVN / LVN as edge ticks
    pd = prev_day(day)
    praw = [r for r in rows_jsonl(DATA + 'tape/tape_NIFTY_%s.jsonl' % pd)] if os.path.exists(DATA + 'tape/tape_NIFTY_%s.jsonl' % pd) else []
    ticks, tick_note = [], None
    if praw:
        byt = {}
        for r in praw: byt[r['t']] = r
        last = hm(sec_ms(max(byt)) + 300)
        ticks = prints.nodes(prints.profile(list(byt.values())))
        tick_note = '%s footprint %s tak (adhoora)' % (datetime.date.fromisoformat(pd).strftime('%d %b'), last) if sec_ms(max(byt)) + 300 < 55800 - 600 else None
        if tick_note: cov.append('HVN/LVN: ' + tick_note)
    else:
        cov.append('%s ka footprint nahi · HVN/LVN ?' % datetime.date.fromisoformat(pd).strftime('%d %b'))
    # --- PLAN (flat)
    plan = []
    def fs(pf): return '%sf|%ss' % (fmt(pf), fmt(spot_of(pf)) if bs is not None else '?')
    if not pos:
        if word == 'BAN RAHA' or word is None:
            plan.append('09:45 se pehle zone nahi · §E')
            plan.append(writers_hint(X, T) or '—')
        elif word in ('TREND', 'LEAN'):
            if d < 0:
                plan.append('SELL%s · 3m high ≥ −1σ %s' % (' chhota' if word == 'LEAN' else '', fs(vw - sg)))
            else:
                plan.append('BUY%s · 3m low ≤ +1σ %s' % (' chhota' if word == 'LEAN' else '', fs(vw + sg)))
            plan.append('close %s, Δ%s · KILL VWAP %s' % ('neeche' if d < 0 else 'upar', '−' if d < 0 else '+', fs(vw)))
            plan.append('T1 %s %s' % ('−2σ' if d < 0 else '+2σ', fs(vw + d * 2 * sg)))
        elif word == 'RANGE':
            plan.append('SELL u2→u3 %s–%s · → VWAP' % (fmt(vw + 2 * sg), fs(vw + 3 * sg)))
            plan.append('BUY d2→d3 %s–%s · → VWAP' % (fmt(vw - 3 * sg), fs(vw - 2 * sg)))
        else:
            plan.append('READ WAIT · zone nahi'); plan.append('—')
    # --- coverage of the order-flow sources
    if day in UX_GAPS:
        for a, b in UX_GAPS[day]:
            if sec_hm(a) < T: cov.insert(0, 'UX %s %s · GC only' % (a + '–' + b if sec_hm(b) < T else a, 'band' if sec_hm(b) < T else 'se band'))
    if any(b['filled'] for b in bars): cov.append('GC o/c %d bars 3m fut se [I]' % sum(1 for b in bars if b['filled']))
    pn = collections.OrderedDict()                     # the place test could not see a strike for these marks
    for c in cands:
        if c['kind'] not in ('trap', 'absorption', 'E1') or not c['rank'] or c['rank'] < BIG_P: continue
        for n in c['place_notes']:
            key = '09:45 se pehle' if '09:45' in n else 'basis' if 'basis' in n else n
            pn.setdefault(key, []).append(c['t'])
    for k, ts in pn.items(): cov.append('likhna strike ? (%s) · %s marks' % (k, ','.join(sorted(set(ts)))))
    # --- counts
    after = dict(glyphs=len(drawn), lines=sum(1 for x in kept if x['drawn']), chips=sum(1 for c in drawn if c['chip_shown']) + sum(1 for x in kept if x['drawn']),
                 tints=sum(1 for b in bars if b['tint']), objects=len(drawn) + sum(1 for x in kept if x['drawn']))
    # --- price range for the chart
    lo = min(b['l'] for b in bars); hi = max(b['h'] for b in bars)
    for x in kept:
        if x['drawn'] and lo - 60 <= x['p'] <= hi + 60: lo, hi = min(lo, x['p']), max(hi, x['p'])
    head = dict(idx='NIFTY', khel=khel_txt, size=size_txt, prem=prem_txt, fut=round(F_now, 1), spot=spot_of(F_now), T=t, day=day,
                word=word, dir=d, since=rr.get('since') if rr else None)
    return dict(id=fid, day=day, T=t, why=why, window=dict(start=hm(win), end=t, bars=len(bars)),
                checks=dict(index_vs_gc=chk, vwap=vchk, band_source=band_src, basis=dict(used=bs, measured=braw, why=bwhy),
                            flow_ref=dict(gc_days=gcref.n_days if gcref else 0, ux_days=uxref.n_days if uxref else 0,
                                          gc_th=gcref.TH if gcref else None, ux_th=uxref.TH if uxref else None),
                            fresh_ref=dict(days=ref30_days, n=len(ref30), p90=round(FS.q(ref30, .9), 1) if ref30 else None)),
                read=dict(row=rr, events=tl['events'], patched=patch),
                chart=dict(bars=bars, lo=lo, hi=hi, zones=zones, khel=khel, khel_dir=d, edge_ticks=ticks, edge_note=tick_note,
                           vwap=round(vw, 1), sig=round(sg, 1)),
                marks=cands, lines=kept,
                panel=dict(head=head, din=din, abhi=abhi, sirf=sirf, baaki=baaki, plan=plan, fold=fold, entry_rows=erows, prem=prem,
                           cov=[c for i, c in enumerate(cov) if c not in cov[:i]]),
                counts=dict(before=bef['drawn'], after=after),
                before=dict(glyphs=bef['glyphs'], lines=bef['lines'], marks_engine_at_T=bef['marks']))


def chain_series_full(day):
    """(sec, ATM IV) from the recorded chain rows: (CE iv + PE iv) / 2 at the ATM strike."""
    out = []
    p = DATA + 'chain/chain_NIFTY_%s.jsonl' % day
    for r in rows_jsonl(p):
        a = r.get('atm')
        s = next((x for x in r.get('strikes') or [] if x['k'] == a), None)
        if not s: continue
        ci, pi = (s.get('ce') or {}).get('iv'), (s.get('pe') or {}).get('iv')
        if ci and pi: out.append((int(r['sec']) if 'sec' in r else sec_hm(r['ts']), (ci + pi) / 2))
    return out


def writers_hint(X, T):
    """READ-V2 §F before 09:45: one side's nine-strike aaj likha made no new high for 15 min while the other did."""
    i = bisect.bisect_right(X['t'], T) - 1
    if i < 0: return None
    peak, last_new = {'ce': None, 'pe': None}, {'ce': None, 'pe': None}
    for j in range(i + 1):
        w = read.writers(X, j)
        for s in ('ce', 'pe'):
            v = w.get(s)
            if v is None: continue
            if peak[s] is None or v > peak[s]: peak[s], last_new[s] = v, X['t'][j]
    if None in last_new.values(): return None
    stop = {s: T - last_new[s] >= 900 for s in ('ce', 'pe')}
    if stop['pe'] and not stop['ce']: return 'jhukav ▼: PE ruka %s, CE likh rahe' % hm(last_new['pe'])
    if stop['ce'] and not stop['pe']: return 'jhukav ▲: CE ruka %s, PE likh rahe' % hm(last_new['ce'])
    return None


def main():
    frames = []
    for fid, day, t, why in FRAMES:
        f = build_frame(fid, day, t, why)
        frames.append(f)
        h = f['panel']['head']
        print(fid, day, t, '| KHEL', h['khel'], h['size'], h['prem'], '| READ', h['word'], '| basis', f['checks']['basis'],
              '| before', f['counts']['before'], '-> after', f['counts']['after'])
        for c in f['marks']:
            print('   %s %-10s p%-5s %-8s rank %-4s place %-30s flow %-8s drawn %s %s' % (c['t'], c['kind'], fmt(c['p']), c['w'], c['rank'],
                  (c['place'] or {}).get('name'), c['flow']['gc'], c['drawn'], '; '.join(c['why_not'])))
        for x in f['lines']: print('   LINE', x['kind'], x['p'], x['spot'], x['chip'], x['drawn'])
        print('   PANEL', json.dumps({k: f['panel'][k] for k in ('din', 'abhi', 'sirf', 'baaki', 'plan', 'cov')}, ensure_ascii=False)[:1500])
        if f['panel']['fold']: print('   FOLD', json.dumps(f['panel']['fold'], ensure_ascii=False)[:800])
        print('   ENTRY ROWS', f['panel']['entry_rows'])
    for f in frames: f['panel']['text'] = panel_text(f)
    json.dump(dict(built=datetime.datetime.now().isoformat(timespec='seconds'), rules=RULES_TEXT, frames=frames),
              open(HERE + '/frames.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    selfcheck(frames)
    write_html(frames)
    return frames


def selfcheck(frames):
    """The rules hold on what was built: every drawn mark passed all three, nothing after T, budgets kept."""
    for f in frames:
        T = sec_hm(f['T'])
        assert all(b['s'] + 300 <= T for b in f['chart']['bars']), 'a bar after T'
        for c in f['marks']:
            assert c['t_close'] <= T, 'a mark after T'
            if c['drawn']:
                assert c['rank'] >= BIG_P and c['place'] and c['place']['dist'] <= c['place']['tol'] and c['flow']['gc'] in ('PUSH', 'CLIMAX', 'ROKA'), c
        drawn = [x for x in f['lines'] if x['drawn']]
        assert len(drawn) <= (5 if f['panel']['fold'] else 2), 'line budget'
        assert sum(1 for c in f['marks'] if c.get('chip_shown')) <= 6, 'chip budget'
        assert not f['panel']['fold'] or any(r['what'] == 'ENTRY' for r in f['panel']['entry_rows']), 'a trade with no rule entry'
    print('selfcheck ok')


# ---------------------------------------------------------------------------------------------- the panel, as text cells
def panel_text(f):
    """Every panel cell as the screen prints it (<= 6 words, Hinglish, numbers). The HTML only lays these out."""
    P, h = f['panel'], f['panel']['head']
    sp = lambda pf: '%sf|%ss' % (fmt(pf), fmt(pf - f['checks']['basis']['used']) if f['checks']['basis']['used'] is not None else '?')
    out = dict(head=dict(idx='NIFTY', khel=h['khel'], size=h['size'], prem=h['prem'],
                         px='%sf | %ss' % (fmt(h['fut']), fmt(h['spot']) if h['spot'] is not None else '?'), T=h['T'],
                         day=datetime.date.fromisoformat(h['day']).strftime('%d %b'),
                         word='READ %s%s%s%s' % (h['word'] or '?', ' ' + ARW[h['dir']] if h['dir'] else '', ' · %s se' % h['since'] if h['since'] else '',
                                                 ' [I]' if f['read']['patched'] else '')))
    d = P['din']
    out['din'] = ['A %+.2f · %s' % (d['A'], d['absent']) if d['A'] is not None else 'A ? · writers ?',
                  'VWAP cross %d · FUEL %s' % (d['crosses'], d['fuel']),
                  'fut OI %+.2f%% · px %+d' % (d['oi_pct'], d['px'])]
    a = P['abhi']
    if a['agree'] == 'sources disagree':
        out['abhi'] = ['FLOW ? · sources disagree', 'GC %s%s / UX %s%s' % (a['gc'], ARW[a['dir'] or 0], a['ux'], ARW[a['ux_dir'] or 0])]
    else:
        st = a['gc'] + (' ' + ARW[a['dir']] if a['gc'] in ('PUSH', 'CLIMAX') else '')
        out['abhi'] = ['FLOW %s · p%s · %s' % (st, a['size_p'], a['agree']), '%s bar · R %s · RVOL %s' % (a['t'], a['R'] if a['R'] is not None else '?', a['rv12'] if a['rv12'] is not None else '?')]
    out['sirf'] = [dict(t=r['t'], ev=r['ev'] + (' ×%d' % r['n'] if r['n'] > 1 else ''), rank='p%d' % r['rank'], status=r['status'] or '—',
                        chart=r['drawn'], tag=r['tag']) for r in P['sirf'][:4]]
    more = len(P['sirf']) - 4
    out['baaki'] = ('+%d bade upar · ' % more if more > 0 else '') + 'baaki %d chhote · noise' % P['baaki']
    if P['fold']:
        fo = P['fold']; e = fo['entry']
        out['trade'] = dict(title='%s %s %s · %s @%s' % ('SELL' if e['d'] < 0 else 'BUY', e['word'], ARW[e['d']], e['t'], sp(e['px'])),
                            rows=[dict(k=r['k'], a=r['a'], b=r['b'], bad=r['bad'], note=('ULTA' if r['bad'] else ('rank ?' if r['k'] == 'OI' else 'theek'))) for r in fo['rows']],
                            verdict=fo['verdict'], why='%d ulta' % fo['against'],
                            kill='KILL 3m close %s VWAP %s' % ('>' if e['d'] < 0 else '<', sp(f['chart']['vwap'])))
    else:
        out['plan'] = P['plan']
    out['cov'] = P['cov']
    b, af = f['counts']['before'], f['counts']['after']
    out['count'] = 'Aaj ka extension %d (%d glyph · %d line) → naya %d (%d glyph · %d line) · +%d tint' % (
        b['objects'], b['glyphs'], b['lines'], af['objects'], af['glyphs'], af['lines'], af['tints'])
    return out


def write_html(frames):
    slim = []
    for f in frames:
        slim.append(dict(id=f['id'], day=f['day'], T=f['T'], why=f['why'], chart=f['chart'], panel=f['panel']['text'],
                         marks=[dict(t=c['t'], kind=c['kind'], p=c['p'], w=c['w'], rank=c['rank'], status=c['status'], chip=c['chip'],
                                     chip_shown=c.get('chip_shown', False), drawn=c['drawn'], size=c['size'], why=c['why_not'],
                                     place=c['place'], nearest=c['nearest'], flow=c['flow'], rank_n=c['rank_n'], src=c['src']) for c in f['marks']],
                         lines=f['lines'], checks=dict(basis=f['checks']['basis'], band=f['checks']['band_source'], vwap=f['checks']['vwap'],
                                                       ix=dict((k, v) for k, v in f['checks']['index_vs_gc'].items() if k != 'rows')),
                         before=f['before']['glyphs'], before_lines=f['before']['lines'], counts=f['counts'], read_patch=f['read']['patched']))
    blob = json.dumps(dict(frames=slim, rules=RULES_TEXT), ensure_ascii=False, default=str).replace('</', '<\\/')
    open(HERE + '/mockup.html', 'w', encoding='utf-8').write(TEMPLATE.replace('/*DATA*/', blob))


TEMPLATE = open(HERE + '/template.html', encoding='utf-8').read() if os.path.exists(HERE + '/template.html') else ''


RULES_TEXT = {
    'mark': 'drawn only if (1) BIG: size rank >= p90 against era-B marks of the same kind (5 Oct on, days before the frame); '
            '(2) AT A PLACE: within 0.25 sigma of VWAP / +-1,2,3 sigma, yesterday H/L/C, today developing POC/VAH/VAL, or a '
            'fresh-writing strike in fut; (3) FLOW AGREES: the GC flow state of its bar is PUSH, CLIMAX or ROKA.',
    'lines': 'at most 2 flat, 5 in a trade: trade kill/target/entry > FLIP or RANGE box > nearest real level each side.',
    'flow_state': 'FLOW-STATE-STUDY §6: PUSH SIZE>=p90 & R>=0.25; CLIMAX SIZE>=p90 & R<0.25; ROKA RVOL12>=p90 & SIZE<=p70; '
                  'noise all <=p70; else no read. Thin bars cannot be PUSH/CLIMAX.',
    'status': 'TIKA until a 3-min futures close beyond the mark price (against its winner) by more than one 5-pt row; then TOOTA.',
}


if __name__ == '__main__':
    main()
