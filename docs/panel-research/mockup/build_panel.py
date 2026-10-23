"""build_panel.py -- right panel v3, DESIGN V2 (../PANEL-DESIGN-V2.md: §A measures, §B face, §C pass bar), computed cell by
cell from recorded files. Round 1 (the draft) stays reachable as mockup-v1.html / NOTES-v1.md.

    python -B build_panel.py        -> frames.json, mockup.html, and the generated self-check at the end of NOTES.md

THE CLOCK. A frame at T uses market data stamped before T only. References are prior days only (all kinds pooled; the day
kind is a header chip, never a filter -- V2 §A1). Measures follow CRITIQUE-SONNET.md §3 as V2 adopts them; the scratch
scripts cs_*.py are the reference implementations (their loaders and formulas are reused here, with prior-days-only
references in place of their leave-one-day-out tests).

INPUTS (read only; no HTTP; nothing written outside this folder):
  flow, Upstox (UX)   ../scratch/pr_1m_<IDX>.json (1-min, ladder.Ladder over data/book)
  flow, GoCharting    data/tape/tape_NIFTY_<day>.jsonl; candles filled [I] from orderflow-desk/test/session-<day>.ofd.json
  option OI, spot     data/chain/chain_<IDX>_<day> [M] + data/chain_backfill (REST minutes) [I]
  futures OI          UX 1-min `oi` (book), else the GC bar `oi`
  header / SIRF BADE / PLAN   tools/frame_v2_replay.py + the dist-v2 bundle via test/shell.mjs (as round 1)
"""
import sys
sys.dont_write_bytecode = True
import bisect, functools, glob, gzip, html, json, os, random, statistics, subprocess, tempfile  # noqa: E401

HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
TM = os.path.normpath(os.path.join(HERE, '..', '..', '..')).replace('\\', '/')
DATA = TM + '/data/'
SCR = os.path.normpath(HERE + '/../scratch').replace('\\', '/') + '/'
OFD = 'C:/Users/kaam/Desktop/Go charting/orderflow-desk'
SHOT_DIR = OFD + '/docs/v2-shots/v24/'
SHOT_REL = '../../../../../Go%20charting/orderflow-desk/docs/v2-shots/v24/'
for _p in (TM + '/tools', TM):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import rank as RK            # noqa: E402  pure: pct_vals, day_kind, MIN_DAYS
import rank_build as RB      # noqa: E402  read-only helpers: _first_row, _surface_expiry

# ---- every hand-picked number, in one place (Sonnet §3 numbers unless marked "mine") ---------------------------------
IDXS, PEERS = ('NIFTY', 'BANKNIFTY', 'SENSEX'), ('BANKNIFTY', 'SENSEX')
LOT = {'NIFTY': 65, 'BANKNIFTY': 30, 'SENSEX': 20}
STEP = {'NIFTY': 50, 'BANKNIFTY': 100, 'SENSEX': 100}
MIN_DAYS = RK.MIN_DAYS                          # 5: under 5 prior days nothing ranks (house)
TINT_N = ((20, 80), (10, 85), (5, 90))          # §3 #8: tint at p80 with N >= 20 days, p85 with 10-19, p90 with 5-9
LOUD_ADD, LOUD_CAP = 10, 97                     # §3 #8: loud = tint + 10, capped at p97
W_TEMPO_FLOW, W_TEMPO_OI = 60, 90               # §3 #1: tempo weight w = min(1, minutes since open / 60 | 90)
TILT_MIN_LOTS = 60                              # cs_states: a tilt needs >= 60 lots in its window
LADDER = (5, 15, 45)                            # §3 #3: 5m, 15m, and the 45 min before the last 15
HOLD = 3                                        # §3 #9: a speed word must hold on 3 consecutive evaluations
BURST_BACK, BURST_FADE = 90, 30                 # §3 #4
PX_DEAD, DELTA_DEAD = 4.0, 0.10                 # §3 #4: px ulta dead-band (pts, share of the window's lots)
CHURN, TEZ_SN, DHEEMA_SN = 4.0, 2.0, 0.8        # §3 #5
TOKEN_SHARE = 0.25                              # §3 #6
SPREAD_FLOOR, PEER_MIN_N = 0.15, 10             # §3 #7 (% from open)
CONFIRM_TOL = 0.05                              # mine: a peer within 0.05% of its own extreme has "confirmed" (σ is cut)
BNF_THIN, BNF_LOUD = 15, 85                     # §3 #7: BANKNIFTY pace two-sided
FRESH = 15                                      # V2 §B6: a rasad chip is solid if fed within 15 min
ZZ_MIN, ZZ_SIG, READ_STALE = 50, 0.5, 5          # §D5: zigzag = max(50 pts, 0.5 × IV-priced 30-min σ); READ > 5 min old hands over
TEST_TOL = 0.1                                  # mine: the leg's extreme is "still being tested" within 0.1 × the zigzag threshold
STRENGTH = ((0, .10), (50, .14), (70, .30), (90, .80), (97, 1.0), (100, 1.0))   # §D1: faint < p70, darkening to p90, full p97+
TWO_SRC_CAP = 0.78                              # §D2 / house rule: one source beyond -> tinted, capped below full
LAST_BACK = 120                                 # §D6: a dead feed shows its last known value from up to 2 h back
OPEN_M, CLOSE_M = 555, 930
LK = 1e5
SEED = 20261020
FIXED = [('2026-10-09', '09:40'), ('2026-10-09', '10:30'), ('2026-10-09', '13:50'),
         ('2026-10-12', '10:00'), ('2026-10-12', '13:30'),
         ('2026-10-16', '09:40'), ('2026-10-16', '10:00'), ('2026-10-16', '10:25'), ('2026-10-16', '11:05'),
         ('2026-10-19', '09:55'), ('2026-10-19', '11:30'), ('2026-10-19', '14:30')]
DAYS = sorted({d for d, _ in FIXED})


def pick_random():
    """the round-1 draw, unchanged: a day of the four, a 5-min clock 09:20..15:25, not a fixed frame."""
    rnd, out = random.Random(SEED), []
    while len(out) < 3:
        d, m = rnd.choice(DAYS), rnd.randrange(9 * 60 + 20, 15 * 60 + 26, 5)
        if (d, hm(m)) not in FIXED and (d, hm(m)) not in out:
            out.append((d, hm(m)))
    return out


def hm(m): return '%02d:%02d' % (m // 60, m % 60)
def mof(s): h, m = s.split(':')[:2]; return int(h) * 60 + int(m)       # noqa: E702
def mint(ms): return (int(ms) // 60000 + 330) % 1440
def med(xs): return statistics.median(list(xs))
def sgn(x): return (x > 0) - (x < 0)
def fmtL(x): return '?' if x is None else '0L' if abs(x) < 0.05 else (('%+.0fL' if abs(x) >= 9.5 else '%+.1fL') % x).replace('-', '−')
def fmtk(k): return '{:,}'.format(int(round(k)))
def pxs(p): return '?' if p is None else '{:,.0f}'.format(p)
def tint_p(n): return next((p for m, p in TINT_N if n >= m), None)
def loud_p(n): t = tint_p(n); return None if t is None else min(LOUD_CAP, t + LOUD_ADD)    # noqa: E702


def strength(p):
    """§D1: a continuous 0.10..1.0 from a rank: faint below p70, darkening through p90, full at p97+ (no knife edge)."""
    if p is None:
        return STRENGTH[0][1]
    for (p0, s0), (p1, s1) in zip(STRENGTH, STRENGTH[1:]):
        if p <= p1:
            return s0 + (s1 - s0) * (p - p0) / (p1 - p0)
    return 1.0


def level(p, n):
    """0 quiet / 1 tinted / 2 loud for a rank p against a reference of n days (§3 #8)."""
    t = tint_p(n)
    if p is None or t is None:
        return None
    return 2 if p >= loud_p(n) else 1 if p >= t else 0


def jl(path):
    for p in (path, path + '.gz'):
        if os.path.exists(p):
            op = gzip.open if p.endswith('.gz') else open
            out = []
            with op(p, 'rt', encoding='utf-8') as f:
                for line in f:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
            return out
    return []


# ---- loaders --------------------------------------------------------------------------------------------------------
@functools.lru_cache(None)
def ux(idx):
    raw = json.load(open(SCR + 'pr_1m_%s.json' % idx))
    return {d: {mint(b['t']): b for b in v['1m'] if OPEN_M <= mint(b['t']) < CLOSE_M} for d, v in raw.items()}


@functools.lru_cache(None)
def gc():
    """{day: {bar start: bar}} NIFTY GC 5-min bars; o/h/l/c filled [I] from the orderflow-desk session file where the tape
    has none (bars logged across a server gap), each such bar flagged `filled`."""
    out = {}
    for p in glob.glob(DATA + 'tape/tape_NIFTY_2026-*.jsonl'):
        d = os.path.basename(p)[11:21]
        B = {}
        for r in jl(p):
            if isinstance(r.get('t'), (int, float)) and isinstance(r.get('buy'), (int, float)) and isinstance(r.get('sell'), (int, float)):
                B[mint(r['t'])] = dict(r)
        sp = OFD + '/test/session-%s.ofd.json' % d
        if os.path.exists(sp):
            for s in json.load(open(sp, encoding='utf-8'))['bars']:
                b = B.get(mint(s['t']))
                if b is not None and (b.get('c') is None or b.get('o') is None):
                    b.update(o=s.get('o'), h=s.get('h'), l=s.get('l'), c=s.get('c'), filled=bool(s.get('filled')))
        out[d] = B
    return out


@functools.lru_cache(None)
def kinds(idx):
    pats = [DATA + 'chain/chain_%s_2026-*' % idx, DATA + 'tape/ux_%s_2026-*' % idx] + ([DATA + 'tape/tape_NIFTY_2026-*'] if idx == 'NIFTY' else [])
    days = sorted({os.path.basename(p).split('_')[-1][:10] for pat in pats for p in glob.glob(pat)})
    out, last = {}, None
    for d in days:
        bk = RB._first_row(DATA + 'book/book_%s_%s.jsonl' % (idx, d)) or {}
        u = RB._first_row(DATA + 'tape/ux_%s_%s.jsonl' % (idx, d)) or {}
        ik, fx = bk.get('ik') or u.get('ik'), bk.get('expiry') or u.get('expiry')
        ex = (RB._first_row(DATA + 'chain/chain_%s_%s.jsonl' % (idx, d)) or {}).get('expiry') or RB._surface_expiry(DATA.rstrip('/'), idx, d)
        out[d] = RK.day_kind(d, ex, fx, ik, last)
        last = ik or last
    return out


@functools.lru_cache(None)
def oi(idx, day):
    """{minute: (spot, {strike: (ce, pe)}, tag)}: OI change since the open as the minute ended; recorded [M] beats REST [I]."""
    out = {}
    for r in jl(DATA + 'chain_backfill/backfill_%s_%s.jsonl' % (idx, day)):
        if r.get('spot') is not None and r.get('k'):
            out[mof(r['t'])] = (r['spot'], {int(float(k)): (v[0], v[1]) for k, v in r['k'].items()}, 'I')
    for r in jl(DATA + 'chain/chain_%s_%s.jsonl' % (idx, day)):
        sec = r.get('sec')
        if sec is None or not r.get('strikes') or r.get('spot') is None or not OPEN_M <= sec // 60 < CLOSE_M:
            continue
        out[sec // 60] = (r['spot'], {s['k']: ((s.get('ce') or {}).get('oi_chg'), (s.get('pe') or {}).get('oi_chg')) for s in r['strikes']}, 'M')
    return out


@functools.lru_cache(None)
def rec_minutes(idx, day):
    return sorted(m for m, v in oi(idx, day).items() if v[2] == 'M')


def live_at(idx, day, m, E):
    """V2 §A10: a REST-backfilled minute existed live at E only if the poller recorded a row after it, by E."""
    if oi(idx, day).get(m, (0, 0, 'M'))[2] == 'M':
        return True
    R = rec_minutes(idx, day)
    i = bisect.bisect_right(R, m)
    return i < len(R) and R[i] < E


def gc_live(day, st, E):
    """a GC snapshot bar (fromTicks false: replayed after a gap) existed at E only if a ticked bar followed it by E."""
    B = gc().get(day) or {}
    b = B.get(st)
    if b is None or b.get('fromTicks'):
        return not (b and b.get('filled'))
    return any(r > st and r + 5 <= E and B[r].get('fromTicks') for r in B)


def src_days(src, idx):
    return sorted(ux(idx)) if src == 'UX' else sorted(gc()) if src == 'GC' else sorted(
        {os.path.basename(p).split('_')[-1][:10] for p in glob.glob(DATA + 'chain/chain_%s_2026-*' % idx)})


def prior(src, idx, day):
    return [d for d in src_days(src, idx) if d < day]


# ---- flow windows (prefix sums; one source per call) ------------------------------------------------------------------
@functools.lru_cache(None)
def grid(src, idx, day):
    if src == 'UX':
        B, step = ux(idx).get(day) or {}, 1
        ms = list(range(OPEN_M, CLOSE_M))
        basic = [m in B and not B[m]['partial'] and (m - 1) in B for m in ms]       # the minute after a hole carries the hole
        cut = [m in B and (m + 1) not in B and m + 1 < CLOSE_M for m in ms]         # the minute cut short before a hole
        vals = [(B[m]['buy'], B[m]['sell'], B[m]['vol']) if m in B else (0, 0, 0) for m in ms]
    else:
        B, step = (gc().get(day) or {}) if idx == 'NIFTY' else {}, 5
        ms = list(range(OPEN_M, CLOSE_M, 5))
        basic = [m in B for m in ms]
        cut = [False] * len(ms)
        vals = [(B[m]['buy'], B[m]['sell'], B[m].get('vol') or B[m]['buy'] + B[m]['sell']) if m in B else (0, 0, 0) for m in ms]
    bad, pb, ps, pv = [0], [0.0], [0.0], [0.0]
    for ok, c, (b, s, v) in zip(basic, cut, vals):
        bad.append(bad[-1] + (0 if ok and not c else 1))
        pb.append(pb[-1] + b), ps.append(ps[-1] + s), pv.append(pv[-1] + v)
    return dict(step=step, basic=basic, cut=cut, bad=bad, b=pb, s=ps, v=pv, has=bool(B))


@functools.lru_cache(None)
def fwin(src, idx, day, a, b, asof=None):
    """(buy, sell, vol) lots in [a, b), or None unless every minute is whole (UX) / every 5-min bar is there (GC). For
    today the minute ending at T has no successor yet: that is not a hole (asof)."""
    g = grid(src, idx, day)
    st = g['step']
    if not g['has'] or a < OPEN_M or b > CLOSE_M or a >= b or a % st or b % st:
        return None
    i, j = (a - OPEN_M) // st, (b - OPEN_M) // st
    bad = g['bad'][j] - g['bad'][i]
    if bad and not (bad == 1 and asof is not None and b == asof and g['basic'][j - 1] and g['cut'][j - 1]):
        return None
    return g['b'][j] - g['b'][i], g['s'][j] - g['s'][i], g['v'][j] - g['v'][i]


def first_min(src): return 558 if src == 'UX' else OPEN_M       # UX's first whole minute is 09:18 (the record starts 09:17)


def cum(src, idx, day, E, asof=None):
    """lots from the open to E. UX: exact across a recorder hole, because the first minute after a hole carries the hole's
    volume (vtt differences) -- so it needs only a record that starts by 09:17 and a minute ending at E. GC: every bar."""
    a = first_min(src)
    if E <= a:
        return 0.0
    if src == 'UX':
        B = ux(idx).get(day) or {}
        if not B or min(B) > 557 or (E - 1) not in B:
            return None
        g = grid(src, idx, day)
        return g['v'][E - OPEN_M] - g['v'][a - OPEN_M]
    w = fwin(src, idx, day, a, E, asof)
    return None if w is None else w[2]


def gap_why(src, idx, day, a, b):
    g = grid(src, idx, day)
    if not g['has']:
        return '%s nahi' % src, 'no %s record on %s' % (src, day)
    B = ux(idx).get(day) if src == 'UX' else gc().get(day)
    if min(B) > a:
        return '%s %s se' % (src, hm(min(B))), 'the %s record begins %s; the window starts %s' % (src, hm(min(B)), hm(a))
    return '%s khali' % src, '%s has holes in %s-%s' % (src, hm(a), hm(b))


# ---- §3 #1: normal = slot reference × today's tempo ----------------------------------------------------------------------
def tempo_flow(src, idx, day, E, ref, need, asof=None):
    """today's cumulative lots open..T-15 ÷ the median of the reference days' same cumulative."""
    c = cum(src, idx, day, E - 15, asof)
    col = [v for o in ref if (v := cum(src, idx, o, E - 15)) is not None]
    if c is None or len(col) < need:
        return None
    if E - 15 <= first_min(src):
        return 1.0
    m = med(col)
    return c / m if m > 0 else None


@functools.lru_cache(None)
def xflow(src, idx, day, E, W, ref, need, asof=None):
    """x = lots[E-W, E) ÷ (median of the same window on the reference days × tempo^w). ref is a tuple of days."""
    v = fwin(src, idx, day, E - W, E, asof)
    if v is None:
        return None
    col = [w[2] for o in ref if (w := fwin(src, idx, o, E - W, E))]
    if len(col) < need:
        return None
    t = tempo_flow(src, idx, day, E, ref, need, asof)
    m = med(col) if col else 0
    if t is None or m <= 0 or t <= 0:
        return None
    return v[2] / (m * t ** min(1.0, (E - OPEN_M) / W_TEMPO_FLOW))


@functools.lru_cache(None)
def pace_pool(src, idx, day, W):
    """the same x for every prior day (its own normal from the OTHER prior days) at every 5-min window end."""
    P = prior(src, idx, day)
    pool, used = [], set()
    for d in P:
        others = tuple(o for o in P if o != d)
        for e in range(OPEN_M + 35, CLOSE_M + 1, 5):
            x = xflow(src, idx, d, e, W, others, MIN_DAYS - 1)
            if x is not None:
                pool.append(x)
                used.add(d)
    return tuple(sorted(pool)), len(used)


def pace(src, idx, day, E, W):
    """-> dict(x, p, n, lvl, lots, norm) or dict(why) ; today's tempo also returned"""
    P = tuple(prior(src, idx, day))
    x = xflow(src, idx, day, E, W, P, MIN_DAYS, E)
    if x is None:
        if fwin(src, idx, day, E - W, E, E) is None:
            s, why = gap_why(src, idx, day, E - W, E)
        elif cum(src, idx, day, E - 15, E) is None:
            B = (ux(idx) if src == 'UX' else gc()).get(day) or {}
            s = 'tempo nahi'
            why = 'today\'s tempo needs the %s cumulative from the open to T-15: %s' % (
                src, 'the record starts %s' % hm(min(B)) if B and min(B) > first_min(src) else 'bars are missing on the way')
        else:
            s, why = 'ref kam', 'fewer than %d prior %s days with this window and the cumulative to T-15' % (MIN_DAYS, src)
        return dict(ok=False, short=s, why=why, src=src, W=W, E=hm(E))
    pool, n = pace_pool(src, idx, day, W)
    p = RK.pct_vals(pool, x) if pool else None
    v = fwin(src, idx, day, E - W, E, E)
    return dict(ok=p is not None, x=x, p=p, n=n, lvl=level(p, n), src=src, W=W, E=hm(E), buy=v[0], sell=v[1], lots=v[2],
                tempo=tempo_flow(src, idx, day, E, P, MIN_DAYS, E), why=None if p is not None else 'no pool')


# ---- §3 #3: tilt ------------------------------------------------------------------------------------------------------------
def tilt(src, idx, day, a, b, asof=None):
    w = fwin(src, idx, day, a, b, asof)
    if w is None or w[0] + w[1] < TILT_MIN_LOTS:
        return None
    return (w[0] - w[1]) / (w[0] + w[1])


@functools.lru_cache(None)
def tilt_pool(src, idx, day, W):
    P = prior(src, idx, day)
    pool, used = [], set()
    for d in P:
        for e in range(OPEN_M + W + 5, CLOSE_M + 1, 5):
            t = tilt(src, idx, d, e - W, e)
            if t is not None:
                pool.append(abs(t))
                used.add(d)
    return tuple(sorted(pool)), len(used)


def band(src, idx, day, W):
    """|tilt| at the N-based tint percentile for that width and source: (band, loud band, n)."""
    Wb = 5 if W <= 10 else 15 if W <= 30 else 45
    pool, n = tilt_pool(src, idx, day, Wb)
    t = tint_p(n)
    if t is None or not pool:
        return None, None, n
    q = lambda p: pool[min(len(pool) - 1, int(p / 100 * len(pool)))]  # noqa: E731
    return q(t), q(loud_p(n)), n


def tilt2(day, a, b, E):
    """the two-source tilt of [a, b) for NIFTY: per source value, rank, strength, gate level; combined sign / length /
    strength. state: 'agree' (both present, same sign), 'ulte' (both present, opposite), 'GC' / 'UX' (one), None."""
    per = {}
    for src in ('GC', 'UX'):
        aa, bb = (a - a % 5, b - b % 5) if src == 'GC' else (a, b)
        t = tilt(src, 'NIFTY', day, aa, bb, E if bb == E else None)
        if t is None:
            continue
        bd, ld, n = band(src, 'NIFTY', day, bb - aa)
        Wb = 5 if bb - aa <= 10 else 15 if bb - aa <= 30 else 45
        pool, _ = tilt_pool(src, 'NIFTY', day, Wb)
        p = RK.pct_vals(pool, abs(t)) if pool else None
        lv = None if bd is None else 2 if abs(t) >= ld else 1 if abs(t) >= bd else 0
        w = fwin(src, 'NIFTY', day, aa, bb, E if bb == E else None)
        per[src] = dict(t=t, p=p, s=strength(p), lvl=lv, band=bd, n=n, buy=w[0], sell=w[1])
    if not per:
        return dict(state=None, per=per)
    if len(per) == 1:
        s_, r = next(iter(per.items()))
        return dict(state=s_, per=per, t=r['t'], lvl=r['lvl'], s=r['s'])
    g, u = per['GC'], per['UX']
    if sgn(g['t']) != sgn(u['t']) and g['t'] and u['t']:
        return dict(state='ulte', per=per, t=(abs(g['t']) + abs(u['t'])) / 2 * sgn(g['t']), lvl=None, s=None)
    weak = g if abs(g['t']) <= abs(u['t']) else u
    if g['lvl'] is None or u['lvl'] is None:
        lv = None
    else:          # rank.two_source (Mary's 19 Oct amendment): one source beyond and the other not -> tinted, capped below loud
        lv = min(g['lvl'], u['lvl']) if min(g['lvl'], u['lvl']) >= 1 else (1 if max(g['lvl'], u['lvl']) >= 1 else 0)
    hi, lo = max(g['s'], u['s']), min(g['s'], u['s'])
    return dict(state='agree', per=per, t=weak['t'], lvl=lv, s=min(hi, max(lo, TWO_SRC_CAP)),
                capped=lv == 1 and min(g['lvl'], u['lvl']) == 0)


def fed(tl, d):
    """'✓' the combined tilt is tinted in direction d (house two-source rule); 'ulte' a source is beyond its band the other
    way; else 'shaant'."""
    per = tl.get('per') or {}
    if not per:
        return None
    if any((r['lvl'] or 0) >= 1 and sgn(r['t']) == -d for r in per.values()):
        return 'ulte'
    if tl.get('state') != 'ulte' and (tl.get('lvl') or 0) >= 1 and sgn(tl['t']) == d:
        return '✓'
    return 'shaant'


# ---- OI (§3 #1, #5, #6) ---------------------------------------------------------------------------------------------------
def atm_at(idx, day, E):
    a = oi(idx, day).get(E - 1)
    return None if not a else round(a[0] / STEP[idx]) * STEP[idx]


@functools.lru_cache(None)
def build(idx, day, E, W, leg, atm, j=None):
    """signed OI change (L) over [E-W, E) at the strikes ATM-2..ATM+2 fixed at `atm` (or the one strike ATM+j)."""
    M = oi(idx, day)
    a, b = M.get(E - 1), M.get(E - 1 - W)
    if not a or not b or atm is None:
        return None
    ks = [atm + j * STEP[idx]] if j is not None else [atm + i * STEP[idx] for i in range(-2, 3)]
    t = 0.0
    for k in ks:
        x, y = a[1].get(k), b[1].get(k)
        if not x or not y or x[leg] is None or y[leg] is None:
            return None
        t += x[leg] - y[leg]
    return t / LK


@functools.lru_cache(None)
def cumgross(idx, day, E):
    """gross two-side ATM±2 activity open..E in 15-min steps, strikes fixed at ATM(E) (cs_oi_norm / cs_strike_rank)."""
    atm = atm_at(idx, day, E)
    if atm is None:
        return None
    t = 0.0
    for e in range(OPEN_M + 16, E + 1, 15):
        for leg in (0, 1):
            v = build(idx, day, e, 15, leg, atm)
            if v is not None:
                t += abs(v)
    return t


@functools.lru_cache(None)
def tempo_oi(idx, day, E, ref, need):
    if E - 15 < OPEN_M + 16:
        return 1.0
    c = cumgross(idx, day, E - 15)
    col = [v for o in ref if (v := cumgross(idx, o, E - 15))]
    if not c or len(col) < need:
        return None
    return c / med(col)


def oi_metric(name, idx, day, E):
    """ce15 / pe15: ATM±2 build; ce@j / pe@j: one strike; gce / gpe: the hour's gross (four quarters), strikes fixed at T."""
    leg = 0 if name.startswith(('ce', 'gce')) else 1
    atm = atm_at(idx, day, E)
    if name.startswith('g'):
        q = [build(idx, day, E - 15 * i, 15, leg, atm) for i in range(4)]
        return None if any(v is None for v in q) else sum(abs(v) for v in q)
    if '@' in name:
        return build(idx, day, E, 15, leg, atm, int(name.split('@')[1]))
    return build(idx, day, E, 15, leg, atm)


@functools.lru_cache(None)
def oi_pool(name, idx, day, E):
    """|value| ÷ tempo^w on every prior day at window ends E-15..E+15 (5-min steps), its tempo from the OTHER prior days."""
    P = prior('OI', idx, day)
    vals, used = [], set()
    for d in P:
        others = tuple(o for o in P if o != d)
        for e in range(E - 15, E + 16, 5):
            if not OPEN_M + 16 <= e <= CLOSE_M:
                continue
            v = oi_metric(name, idx, d, e)
            t = tempo_oi(idx, d, e, others, MIN_DAYS - 1)
            if v is not None and t:
                vals.append(abs(v) / t ** min(1.0, (e - OPEN_M) / W_TEMPO_OI))
                used.add(d)
    return tuple(sorted(vals)), len(used)


@functools.lru_cache(None)
def raw_pool(name, idx, day, E):
    """|value| in lakh on prior days at ends E-15..E+15: the quarter noise floor is its median (no tempo)."""
    return tuple(sorted(abs(v) for d in prior('OI', idx, day) for e in range(E - 15, E + 16, 5)
                        if OPEN_M + 16 <= e <= CLOSE_M and (v := oi_metric(name, idx, d, e)) is not None))


def oi_rank(name, idx, day, E):
    v = oi_metric(name, idx, day, E)
    if v is None:
        return dict(ok=False, v=None)
    t = tempo_oi(idx, day, E, tuple(prior('OI', idx, day)), MIN_DAYS)
    if not t:
        return dict(ok=False, v=v, why='OI tempo: fewer than %d prior chain days' % MIN_DAYS)
    pool, n = oi_pool(name, idx, day, E)
    x = abs(v) / t ** min(1.0, (E - OPEN_M) / W_TEMPO_OI)
    p = RK.pct_vals(pool, x) if pool else None
    return dict(ok=p is not None, v=v, x=x, p=p, n=n, lvl=level(p, n), tempo=t)


def oi_why(idx, day, E, W=15):
    M = oi(idx, day)
    if not M:
        return 'OI nahi', 'no chain row and no REST backfill for %s on %s' % (idx, day)
    for m in (E - 1, E - 1 - W):
        if m not in M:
            return 'OI khali', 'no OI minute at %s (chain gap, no backfill)' % hm(m)
    ks = sorted(M[E - 1][1])
    return 'strike bahar', 'ATM %s ±2 is outside the recorded strikes (%s..%s)' % (fmtk(atm_at(idx, day, E)), fmtk(ks[0]), fmtk(ks[-1]))


def oi_word(idx, day, E):
    """§3 #5 (V2 words): first match wins. -> (word or None, quarters oldest->newest, info) for both legs."""
    out = {}
    atm = atm_at(idx, day, E)
    for leg, nm in ((0, 'CALL'), (1, 'PUT')):
        qa = [build(idx, day, E - 15 * i, 15, leg, atm) for i in range(4)]       # newest first
        q = qa[:next((i for i, v in enumerate(qa) if v is None), 4)]          # stop at the first missing quarter
        n = len(q)
        r15 = oi_rank('ce15' if leg == 0 else 'pe15', idx, day, E)
        rg = oi_rank('gce' if leg == 0 else 'gpe', idx, day, E) if n == 4 else dict(ok=False)
        floor_pool = raw_pool('ce15' if leg == 0 else 'pe15', idx, day, E)
        tint = max(r15.get('lvl') or 0, rg.get('lvl') or 0)
        word = None
        if n >= 3:
            G, N, S = sum(abs(v) for v in q), sum(q), abs(q[0]) / max(sum(abs(v) for v in q), 1e-9)
            floor = med(floor_pool) if floor_pool else 0       # the slot's typical |quarter| (tempo-free)
            gt = (rg.get('lvl') or 0) >= 1 or (r15.get('lvl') or 0) >= 1
            if G >= CHURN * abs(N) and gt:
                word = 'churn'
            elif q[0] < 0 and abs(q[0]) >= floor and N < 0:
                word = 'nikal rahe'
            elif S * n >= TEZ_SN and q[0] > 0 and N > 0:
                word = 'badh raha'
            elif S * n <= DHEEMA_SN and gt:
                word = 'dheema'
        qp = []                                           # each quarter's own tempo-free rank at its own end
        for i, v in enumerate(q):
            e = E - 15 * i
            t = tempo_oi(idx, day, e, tuple(prior('OI', idx, day)), MIN_DAYS)
            pool, _ = oi_pool('ce15' if leg == 0 else 'pe15', idx, day, e)
            qp.append(RK.pct_vals(pool, abs(v) / t ** min(1.0, (e - OPEN_M) / W_TEMPO_OI)) if pool and t else None)
        out[nm] = dict(q=list(reversed(q)), qp=list(reversed(qp)), word=word, r15=r15, rg=rg, tint=tint, n=n,
                       floor=med(floor_pool) if floor_pool else None)
    return out


# ---- spot and peers (§3 #7) --------------------------------------------------------------------------------------------------
def spot_at(idx, day, E):
    M = oi(idx, day)
    for m in range(E - 1, E - 4, -1):
        if m in M:
            return M[m][0], m
    return None, None


def din(idx, day, E):
    """% from the open of the index spot; the open is the first spot minute, by 09:20 (cs_spread)."""
    M = oi(idx, day)
    if not M or min(M) > 9 * 60 + 20:
        return None
    s, _ = spot_at(idx, day, E)
    return None if s is None else 100 * (s / M[min(M)][0] - 1)


def spread_rank(idx, day, E):
    sp = None if din(idx, day, E) is None or din('NIFTY', day, E) is None else din(idx, day, E) - din('NIFTY', day, E)
    if sp is None:
        return dict(ok=False, v=None)
    ref = [din(idx, d, E) - din('NIFTY', d, E) for d in prior('OI', idx, day) if din(idx, d, E) is not None and din('NIFTY', d, E) is not None]
    if len(ref) < PEER_MIN_N:
        return dict(ok=False, v=sp, why='only %d prior days with both spots at %s (needs %d)' % (len(ref), hm(E), PEER_MIN_N))
    p = RK.pct_vals([abs(x) for x in ref], abs(sp))
    lv = level(p, len(ref))
    if abs(sp) < SPREAD_FLOOR:
        lv = 0
    return dict(ok=True, v=sp, p=p, n=len(ref), lvl=lv)


def ext15(idx, day, E):
    M = oi(idx, day)
    pts = sorted((m, v[0]) for m, v in M.items() if m < E)
    if not pts or pts[0][0] > 9 * 60 + 20:
        return None
    H, Lo = max(p for _, p in pts), min(p for _, p in pts)
    tH, tL = min(m for m, p in pts if p == H), min(m for m, p in pts if p == Lo)
    last = [p for m, p in pts if m >= E - 15]
    return dict(H=H, L=Lo, tH=hm(tH), tL=hm(tL), newH=tH >= E - 15, newL=tL >= E - 15,
                h15=max(last) if last else None, l15=min(last) if last else None)


def confirm(idx, day, E):
    """✓ / ✗ only after a test (NIFTY set a session extreme in the last 15 min); None when nothing was tested."""
    nx, pe = ext15('NIFTY', day, E), ext15(idx, day, E)
    if nx is None or not (nx['newH'] or nx['newL']):
        return None, dict(nifty=nx)
    if pe is None or pe['h15'] is None:
        return '?', dict(nifty=nx, peer=pe)
    tol = CONFIRM_TOL / 100
    failH = nx['newH'] and pe['h15'] < pe['H'] * (1 - tol)
    failL = nx['newL'] and pe['l15'] > pe['L'] * (1 + tol)
    word = ('high' if failH else 'low') + ' ✗' if failH or failL else ('high' if nx['newH'] else 'low') + ' ✓'
    return word, dict(nifty=nx, peer=pe)


# ---- the leg (§3 #2) -----------------------------------------------------------------------------------------------------------
def legs(bars, thr):
    """board.js legs(), ported: a zigzag on closes with a `thr`-point reversal; the last leg is open."""
    if not bars:
        return []
    out = []
    d = sgn(bars[0]['c'] - bars[0]['o']) or -1
    i0, ext, extI, frm = 0, bars[0]['c'], 0, bars[0]['o']
    pv = lambda i, dd: bars[i]['h'] if dd > 0 else bars[i]['l']   # noqa: E731
    for i in range(1, len(bars)):
        b = bars[i]
        if (b['c'] >= ext) if d > 0 else (b['c'] <= ext):
            ext, extI = b['c'], i
        if ((ext - b['c']) if d > 0 else (b['c'] - ext)) >= thr:
            out.append(dict(i0=i0, i1=extI, dir=d, frm=frm, to=pv(extI, d)))
            frm = pv(extI, d)
            d, i0, ext, extI = -d, extI, b['c'], i
    out.append(dict(i0=i0, i1=len(bars) - 1, dir=d, frm=frm, to=pv(extI, d), open=True))
    return out


def fut_px(day, E):
    """NIFTY futures price as of E: the UX minute ending at E, else the GC bar ending at E (filled [I] where needed)."""
    b = (ux('NIFTY').get(day) or {}).get(E - 1)
    if b and b.get('c') is not None:
        return b['c']
    g = (gc().get(day) or {}).get(E - 5) if E % 5 == 0 else None
    return g.get('c') if g else None


@functools.lru_cache(None)
def chain_iv(idx, day):
    """{minute: (spot, ATM IV)} from the recorded chain rows (REST backfill carries no IV)."""
    out = {}
    for r in jl(DATA + 'chain/chain_%s_%s.jsonl' % (idx, day)):
        if r.get('sec') is None or not r.get('strikes') or r.get('atm') is None:
            continue
        s_ = next((x for x in r['strikes'] if x['k'] == r['atm']), None)
        iv = [v for v in ((s_ or {}).get('ce', {}).get('iv'), (s_ or {}).get('pe', {}).get('iv')) if v]
        if iv:
            out[r['sec'] // 60] = (r['spot'], sum(iv) / len(iv))
    return out


def zz_thr(day, E):
    """§D5: max(50 pts, 0.5 × today's IV-priced 30-min σ = spot × ATM IV × sqrt(30 / (252 × 375))), from the last IV at or
    before T (a dead chain keeps its last IV, said in the hover)."""
    M = chain_iv('NIFTY', day)
    ms = [m for m in M if m < E]
    if not ms:
        return ZZ_MIN, None
    spot, iv = M[max(ms)]
    sig = spot * iv * (30 / (252 * 375)) ** 0.5
    return max(ZZ_MIN, ZZ_SIG * sig), dict(iv=iv, sigma30=sig, at=hm(max(ms)))


def leg_of(day, E, read):
    """§D5: the main leg and the current pullback, the way a trader says it.
    READ fresh and RIDE: the main leg runs from the READ's since-time to the extreme in its direction since then.
    Otherwise the zigzag (board.js legs on 5-min closes, threshold zz_thr): if the open leg is a reversal smaller than the
    leg before it, that earlier leg is the main leg and the open one is the pullback; else the open leg is the main leg.
    The pullback runs from the last bar that still tested the extreme (within TEST_TOL × threshold) to now."""
    bars = [dict(b, s=st) for st, b in sorted((gc().get(day) or {}).items())
            if st + 5 <= E and None not in (b.get('o'), b.get('h'), b.get('l'), b.get('c'))]
    if not bars:
        return None
    thr, ivi = zz_thr(day, E)
    fresh = read.get('t') and mof(read['t']) >= E - READ_STALE
    if fresh and read.get('khel') == 'RIDE' and read.get('dir') and read.get('since'):
        st, d, how = mof(read['since']), read['dir'], 'READ'
        frm = fut_px(day, st)
        mb = [b for b in bars if b['s'] >= st]
    else:
        L = legs(bars, thr)
        cur = L[-1]
        main = cur
        if len(L) >= 2:
            prev = L[-2]
            now = bars[-1]['c']
            if abs(now - cur['frm']) < abs(prev['to'] - prev['frm']):
                main = prev
        d, how = main['dir'], 'zigzag'
        near = [b for b in bars[:main['i0'] + 1] if b['s'] >= bars[main['i0']]['s'] - 15]
        sb = min(near, key=lambda b: b['l']) if d > 0 else max(near, key=lambda b: b['h'])
        st, frm = sb['s'], (sb['l'] if d > 0 else sb['h'])
        mb = [b for b in bars if b['s'] >= st]
    if not mb or frm is None:
        return None
    ext_bar = max(mb, key=lambda b: b['h']) if d > 0 else min(mb, key=lambda b: b['l'])
    ext = ext_bar['h'] if d > 0 else ext_bar['l']
    tol = TEST_TOL * thr
    last_test = max((b for b in mb if b['s'] >= ext_bar['s'] and ((b['h'] >= ext - tol) if d > 0 else (b['l'] <= ext + tol))), key=lambda b: b['s'])
    pb_from = last_test['s'] + 5 if last_test['s'] + 5 < E else last_test['s']
    return dict(start=st, dir=d, frm=frm, ext=ext, ext_t=ext_bar['s'], end=last_test['s'], pb_from=pb_from, how=how, thr=thr, iv=ivi,
                filled=any(not gc_live(day, b['s'], E) for b in mb))


def leg_block(day, E, read):
    lg = leg_of(day, E, read)
    if not lg:
        return dict(ok=False, why='no leg yet (no READ leg and no zigzag leg in the GC bars)')
    d, st = lg['dir'], lg['start']
    now = fut_px(day, E)
    move = lg['ext'] - lg['frm']
    pb = None if now is None else now - lg['ext']
    out = dict(ok=True, dir=d, start=hm(st), end=hm(lg['end']), how=lg['how'], age=E - st, move=move, frm=lg['frm'], ext=lg['ext'],
               now=now, pb=pb, wapas=None if pb is None or not move else 100 * abs(pb) / abs(move), pb_from=hm(lg['pb_from']),
               thr=lg['thr'], iv=lg['iv'], filled=lg.get('filled'))
    # where the main leg's points came from: its biggest 15-minute stretch, start .. the extreme
    a0, end = st - st % 5, max(lg['ext_t'] + 5, st + 15)
    best = None
    for a in range(a0, max(a0, min(end, E) - 15) + 1, 5):
        b = min(a + 15, E)
        pa = lg['frm'] if a == a0 else fut_px(day, a)
        pb_ = fut_px(day, b)
        if pa is None or pb_ is None:
            continue
        if best is None or d * (pb_ - pa) > d * best[2]:
            best = (a, b, pb_ - pa)
    if best:
        a, b, mv = best
        tl = tilt2(day, a, b, E)
        out['stretch'] = dict(a=hm(a), b=hm(b), pts=mv, tilt=tl, fed=fed(tl, d))
    # the pullback: who is pressing it (both sources), since the last test of the extreme
    if lg['pb_from'] < E and pb is not None and abs(pb) >= TEST_TOL * lg['thr']:
        tl2 = tilt2(day, min(lg['pb_from'], E - 5), E, E)
        out['pullback'] = dict(tilt=tl2, fed=fed(tl2, -d), pace=pace(flow_src(day, E) or 'GC', 'NIFTY', day, E - E % 5, min(15, max(5, (E - lg['pb_from']) // 5 * 5))) if flow_src(day, E) else {})
    out['rasad'] = rasad(day, E, st, d)
    return out


def rasad(day, E, st, d):
    """the last time each feeder fed the leg in its direction: flow (15-min tilt beyond band, both sources when both
    exist), OI (side build tinted, tempo-free), fut OI (|ΔOI15| tinted with OI up and price in the leg's way), BANKNIFTY (a
    new leg extreme of its own spot). None = never fed (checked); '?' = could not check."""
    res = {}
    seen, last = False, None
    for e in range(st + 5, E + 1):
        if e % 5 and not grid('UX', 'NIFTY', day)['has']:
            continue
        tl = tilt2(day, e - 15, e, E)
        if not tl['per']:
            continue
        seen = True
        if fed(tl, d) == '✓':
            last = e
    res['flow'] = last if last else ('?' if not seen or not tilt2(day, E - 15, E, E)['per'] else None)
    seen, last = False, None
    for e in range(st + 5 - (st + 5) % 5, E + 1, 5):
        for leg in (0, 1):                                # down leg: call writing (+) or put unwinding (−); up leg the mirror
            r = oi_rank('ce15' if leg == 0 else 'pe15', 'NIFTY', day, e)
            if r.get('v') is None:
                continue
            seen = True
            want = (1 if d < 0 else -1) if leg == 0 else (-1 if d < 0 else 1)
            if r.get('ok') and (r['lvl'] or 0) >= 1 and sgn(r['v']) == want:
                last = e
    res['oi'] = last if last else ('?' if not seen or oi_metric('ce15', 'NIFTY', day, E) is None else None)
    seen, last = False, None
    for e in range(st + 5 - (st + 5) % 5, E + 1, 5):
        r = fut_rank(day, e)
        if r.get('v') is None:
            continue
        seen = True
        pa, pb = fut_px(day, e - 15), fut_px(day, e)
        if r.get('ok') and (r['lvl'] or 0) >= 1 and pa is not None and pb is not None and sgn(pb - pa) == d:
            last = e
    res['fut'] = last if last else ('?' if not seen or fut_rank(day, E).get('v') is None and last_known(lambda e: fut_rank(day, e) if fut_rank(day, e).get('v') is not None else None, E)[0] != E else None)
    res['bnf'] = bnf_leg(day, E, st, d)
    return res


def bnf_leg(day, E, st, d):
    """§D7: at NIFTY's spot extreme of the main leg, did BANKNIFTY's spot (within 15 min either side) reach its own leg extreme
    (within CONFIRM_TOL %)? ✓ confirms / ✗ refuses / '?' when either spot is missing."""
    N = sorted((m, v[0]) for m, v in oi('NIFTY', day).items() if st <= m < E)
    B = sorted((m, v[0]) for m, v in oi('BANKNIFTY', day).items() if st <= m < E)
    if len(N) < 3 or len(B) < 3:
        return '?'
    tx, _ = (max if d > 0 else min)(N, key=lambda mp: mp[1])
    ext = (max if d > 0 else min)(p for _, p in B)
    near_pts = [p for m, p in B if tx - 15 <= m <= tx + 15]
    if not near_pts:
        return '?'
    near = (max if d > 0 else min)(near_pts)
    tol = ext * CONFIRM_TOL / 100
    ok = (near >= ext - tol) if d > 0 else (near <= ext + tol)
    return dict(word='✓' if ok else '✗', nifty_t=hm(tx), near=near, ext=ext, tol=tol)


# ---- futures OI (V2 §A4: with a dead-band) ---------------------------------------------------------------------------------
def fut_oi(src, day, E):
    if src == 'UX':
        a, b = (ux('NIFTY').get(day) or {}).get(E - 1), (ux('NIFTY').get(day) or {}).get(E - 16)
    else:
        a, b = ((gc().get(day) or {}).get(E - 5), (gc().get(day) or {}).get(E - 20)) if E % 5 == 0 else (None, None)
    if not a or not b or a.get('oi') is None or b.get('oi') is None:
        return None
    return (a['oi'] - b['oi']) / LK


@functools.lru_cache(None)
def fut_pool(src, day, E):
    vals, used = [], set()
    for d in prior(src, 'NIFTY', day):
        for e in range(E - 15, E + 16, 5):
            v = fut_oi(src, d, e)
            if v is not None:
                vals.append(abs(v))
                used.add(d)
    return tuple(sorted(vals)), len(used)


def fut_rank(day, E):
    for src in ('UX', 'GC'):
        v = fut_oi(src, day, E)
        if v is not None:
            pool, n = fut_pool(src, day, E)
            p = RK.pct_vals(pool, abs(v)) if pool else None
            return dict(ok=p is not None, v=v, p=p, n=n, lvl=level(p, n), src=src)
    return dict(ok=False, v=None)


def last_known(fn, E, step=1):
    """§D6: the latest clock E' <= E (up to LAST_BACK min back) where fn(E') has a value -> (E', value) or (None, None)."""
    for e in range(E, E - LAST_BACK - 1, -step):
        v = fn(e)
        if v is not None and (not isinstance(v, dict) or v.get('v') is not None or v.get('x') is not None):
            return e, v
    return None, None


# ---- the face: cells ---------------------------------------------------------------------------------------------------------
def C(kind, **kw):
    """one face element: kind = txt | pace | tilt | oiq | chip | tok ; everything else is data for the renderer / hover."""
    return dict(kind=kind, **kw)


def qcell(short, why):
    return C('txt', t='? ' + short, cls='qm', h=why)


def side_cls(d): return 'up' if d > 0 else 'dn' if d < 0 else 'nt'
def ptxt(r): return '' if not r or r.get('p') is None else 'p%.0f of %d days' % (r['p'], r['n'])


def tilt_cell(tl, W=None, after=None):
    """§D2: a diverging bar from a centre line; sellers left red, buyers right green, length = share - 50%; strength by rank;
    hatched (each source on its own side) when GC and UX disagree in sign; a small GC / UX when only one exists."""
    if after:
        return C('txt', t='%s se' % after, cls='q', h='this window starts before the open; it exists from %s' % after)
    if not tl or tl.get('state') is None:
        return qcell('tilt', 'neither GC nor UX has this window whole')
    per = tl['per']
    h = ' · '.join('%s %s %.0f%% (b %d / s %d)%s' % (s_, 'buyers' if r['t'] > 0 else 'sellers', 50 + 50 * abs(r['t']), r['buy'], r['sell'],
                                                         '' if r['p'] is None else ', p%.0f of %d days' % (r['p'], r['n'])) for s_, r in per.items())
    if tl['state'] == 'ulte':
        g, u = per['GC'], per['UX']
        return C('tilt', mode='ulte', left=50 * abs(g['t'] if g['t'] < 0 else u['t']), right=50 * abs(g['t'] if g['t'] > 0 else u['t']),
                 tag='', h='GC and UX disagree in sign: ' + h)
    return C('tilt', mode='one', side=sgn(tl['t']), ex=50 * abs(tl['t']), s=tl['s'], tag=tl['state'] if tl['state'] in ('GC', 'UX') else '',
             h=h + (' · one source inside its band: capped below full (rank.two_source)' if tl.get('capped') else ''))


def ladder_word(vals, levels, kind):
    """`tez ho raha` (rising 5m > 15m > 45m, 5m tinted) / `thak raha` (falling, 45m tinted); for tilt the three must
    share a sign and the magnitudes are compared."""
    if any(v is None for v in vals):
        return None
    if kind == 'tilt':
        if len({sgn(v) for v in vals}) != 1 or not vals[0]:
            return None
        vals = [abs(v) for v in vals]
    if vals[0] > vals[1] > vals[2] and (levels[0] or 0) >= 1:
        return 'tez ho raha'
    if vals[0] < vals[1] < vals[2] and (levels[2] or 0) >= 1:
        return 'thak raha'
    return None


def flow_block(day, E, src):
    """KAUN DABA RAHA: PACE + TILT ladders and the burst line, one flow source for pace (two for tilt)."""
    stride = 1 if src == 'UX' else 5
    blk = dict(title='KAUN DABA RAHA', src=src, rows=[], trace={})
    if src is None:
        blk['rows'] = [[qcell('flow nahi', 'neither UX nor GC has the window ending %s' % hm(E))]]
        blk['state'] = '?'
        return blk

    def at(e):
        pc = [pace(src, 'NIFTY', day, e, 5), pace(src, 'NIFTY', day, e, 15), pace(src, 'NIFTY', day, e - 15, 45)]
        tl = [tilt2(day, e - 5, e, E), tilt2(day, e - 15, e, E), tilt2(day, e - 60, e - 15, E)]
        return pc, tl
    pc, tl = at(E)
    words = {'pace': [], 'tilt': []}
    for k in range(HOLD):
        p_, t_ = (pc, tl) if k == 0 else at(E - k * stride)
        words['pace'].append(ladder_word([r.get('x') for r in p_], [r.get('lvl') for r in p_], 'pace'))
        words['tilt'].append(ladder_word([r.get('t') for r in t_], [r.get('lvl') for r in t_], 'tilt'))
    wp = words['pace'][0] if len(set(words['pace'])) == 1 else None
    wt = words['tilt'][0] if len(set(words['tilt'])) == 1 else None
    tempo = next((r['tempo'] for r in pc if r.get('tempo')), None)
    blk['tempo'] = tempo
    cells = []
    for i, r in enumerate(pc):
        if not r.get('x') and i == 2 and E - 60 < first_min(src):
            cells.append(C('txt', t='%s se' % hm(first_min(src) + 60), cls='q', h='the 45 min before the last 15 exist from %s' % hm(first_min(src) + 60)))
        elif not r.get('x'):
            cells.append(qcell(r.get('short', '?'), r.get('why', '')))
        else:
            cells.append(C('pace', x=r['x'], lvl=r['lvl'] or 0, s=strength(r['p']), h='%.2f× normal · %s · %d lots (b %d / s %d)' % (r['x'], ptxt(r), r['lots'], r['buy'], r['sell'])))
    if len({c.get('t') for c in cells}) == 1 and cells[0].get('cls') == 'qm':          # one reason, said once
        cells = [dict(cells[0], span=3)]
    blk['rows'].append([C('txt', t='pace', cls='lab')] + cells + [C('txt', t=wp or '', cls='word')])
    blk['rows'].append([C('txt', t='tilt', cls='lab')] + [tilt_cell(t, after=hm(OPEN_M + 60) if i == 2 and E - 60 < OPEN_M else None) for i, t in enumerate(tl)]
                       + [C('txt', t=wt or '', cls='word')])
    # the burst (§3 #4): the latest 5-min window in the last 90 min with pace at the tint threshold
    burst = None
    for e in range(E - E % 5, E - BURST_BACK, -5):
        r = pace(src, 'NIFTY', day, e, 5)
        if r.get('lvl') and r['lvl'] >= 1:
            burst = (e, r)
            break
    if burst:
        e, r = burst
        pa, pb = fut_px(day, e - 5), fut_px(day, e)
        dpx = None if pa is None or pb is None else pb - pa
        delta = r['buy'] - r['sell']
        ulta = dpx is not None and abs(dpx) >= PX_DEAD and abs(delta) >= DELTA_DEAD * r['lots'] and sgn(dpx) != sgn(delta)
        old = E - e > BURST_FADE
        t5 = tilt2(day, e - 5, e, E)
        blk['rows'].append([C('txt', t='burst %s' % hm(e), cls='lab' + (' old' if old else '')),
                            C('pace', x=r['x'], lvl=0 if old else r['lvl'], s=0.12 if old else strength(r['p']), h='burst %.2f× · %s' % (r['x'], ptxt(r))),
                            dict(tilt_cell(t5), s=0.12) if old else tilt_cell(t5),
                            C('txt', t=('%s%.0f' % ('▲' if dpx > 0 else '▼', abs(dpx))) if dpx else '·', cls=('q' if old or not dpx else side_cls(sgn(dpx))) + ' px',
                              h='futures %+.1f pts over the window' % dpx if dpx is not None else 'no price'),
                            C('txt', t='px ulta' if ulta else 'px ✓', cls='word' if ulta and not old else 'ink' if not old else 'q')])
        blk['trace']['burst'] = dict(t=hm(e), x=r['x'], p=r['p'], n=r['n'], buy=r['buy'], sell=r['sell'], dpx=dpx, ulta=ulta, old=old)
    else:
        blk['rows'].append([C('txt', t='burst', cls='lab'), C('txt', t='shaant ✓', cls='ok', h='no 5-min window at the tint threshold in the last 90 min')])
    blk['trace'].update(pace=pc, tilt=tl, words=words)
    lit = any((r.get('lvl') or 0) >= 1 for r in pc) or any((t.get('lvl') or 0) >= 1 for t in tl) or wp or wt or (burst and not (E - burst[0] > BURST_FADE))
    blk['state'] = 'lit' if lit else '?' if all(not r.get('x') for r in pc) else 'quiet'
    blk['n'] = min([r['n'] for r in pc if r.get('n')] + [t['per'][s]['n'] for t in tl for s in (t.get('per') or {})] or [99])
    return blk


def oi_block(day, E):
    blk = dict(title='KAUN LIKH RAHA', rows=[], trace={})
    atm = atm_at('NIFTY', day, E)
    W = oi_word('NIFTY', day, E) if atm else {}
    ws = {}
    for k in range(HOLD):                                   # §3 #9: an OI word holds on 3 evaluations, 5-min stride
        e = E - 5 * k
        ws[k] = oi_word('NIFTY', day, e) if atm_at('NIFTY', day, e) else {}
    qmax = max([abs(v) for nm in W for v in W[nm]['q']] + [30.0])
    lit = False
    for nm in ('CALL', 'PUT'):
        if nm not in W or W[nm]['r15'].get('v') is None:
            leg = 0 if nm == 'CALL' else 1
            e0, v0 = last_known(lambda e: oi_metric('ce15' if leg == 0 else 'pe15', 'NIFTY', day, e) if atm_at('NIFTY', day, e) else None, E - 1)
            if v0 is not None:
                blk['rows'].append([C('txt', t=nm, cls='lab'), C('txt', t='%s · %s tak' % (fmtL(v0), hm(e0)), cls='dead', span=3,
                                                                  h='the OI feed died: last known 15-min ATM±2 %s change up to %s; not live' % (nm, hm(e0)))])
            else:
                s_, why = oi_why('NIFTY', day, E)
                blk['rows'].append([C('txt', t=nm, cls='lab'), qcell(s_, why)])
            continue
        r = W[nm]
        r15 = r['r15']
        leg = 0 if nm == 'CALL' else 1
        d = (-1 if leg == 0 else 1) * sgn(r15['v'])
        word = r['word'] if all(ws[k].get(nm, {}).get('word') == r['word'] for k in range(HOLD)) and r['tint'] >= 1 else None
        lv = r15.get('lvl') or 0
        lit = lit or lv >= 1 or bool(word)
        qs = r['q']
        blk['rows'].append([C('txt', t=nm, cls='lab'),
                            C('txt', t=fmtL(r15['v']), cls='num ' + side_cls(d), sty='opacity:%.2f' % max(0.45, strength(r15.get('p'))),
                              h='15-min ATM±2 %s change %s · %s' % (nm, fmtL(r15['v']), ptxt(r15) or r15.get('why', ''))),
                            C('oiq', q=qs, qp=r['qp'], leg=leg, on=r['tint'] >= 1, scale=max([abs(v) for v in qs] + [2 * (r['floor'] or 0), 1.0]),
                              h='quarters oldest→newest: %s · hour gross %s%s' % (' '.join(fmtL(v) for v in qs), fmtL(sum(abs(v) for v in qs)),
                                                                              ' · ' + ptxt(r['rg']) if r['rg'].get('p') is not None else '')),
                            C('txt', t=word or '', cls='word')])
        blk['trace'][nm] = dict(v=r15['v'], p=r15.get('p'), n=r15.get('n'), lvl=lv, q=qs, word=word, raw_word=r['word'],
                                gross_p=r['rg'].get('p'), tempo=r15.get('tempo'), held=[ws[k].get(nm, {}).get('word') for k in range(HOLD)])
    # deewar tokens (§3 #6)
    toks = tokens('NIFTY', day, E) if atm else []
    blk['trace']['tokens'] = toks
    spot, _ = spot_at('NIFTY', day, E)
    shown = [t for t in toks if t['kind'] == 'deewar'][:2] + [t for t in toks if t['kind'] == 'nikal'][:1]
    for t in shown[:3]:
        lit = True
        near = min(t['ks'], key=lambda k: abs(k - spot)) if spot else t['ks'][0]
        dist = None if spot is None else near - spot
        rng = fmtk(t['ks'][0]) + ('–%s' % str(int(t['ks'][-1]))[-3:] if len(t['ks']) > 1 else '')
        blk['rows'].append([C('txt', t=t['kind'], cls='lab'),
                            C('tok', t='%s %s' % ('CALL' if t['leg'] == 0 else 'PUT', rng), d=t['d'], lvl=t['lvl'],
                              h='%s · change %s · %s · %.0f%% of the side\'s gross' % (rng, fmtL(t['v']), 'p%.0f' % t['p'], 100 * t['share'])),
                            C('txt', t=fmtL(t['v']), cls='num ' + side_cls(t['d'])),
                            C('txt', t='' if dist is None else '%d %s' % (abs(dist), 'upar' if dist > 0 else 'neeche'), cls='ink')])
    if any(t.get('pin') for t in toks):
        blk['rows'].append([C('txt', t='pin', cls='lab'), C('txt', t='pin %s' % fmtk(next(t['pin'] for t in toks if t.get('pin'))), cls='word')])
    # futures OI with a dead-band
    fr = fut_rank(day, E)
    blk['trace']['fut'] = fr
    if fr.get('v') is None:
        e0, r0 = last_known(lambda e: fut_rank(day, e) if fut_rank(day, e).get('v') is not None else None, E - 1)
        blk['trace']['fut_last'] = dict(at=e0 and hm(e0), r=r0)
        if r0:
            pa, pb = fut_px(day, e0 - 15), fut_px(day, e0)
            w = {(1, 1): 'naye long', (1, -1): 'naye short', (-1, 1): 'covering', (-1, -1): 'long nikal'}.get((sgn(r0['v']), sgn(pb - pa))) if pa and pb and (r0.get('lvl') or 0) >= 1 else ''
            blk['rows'].append([C('txt', t='fut OI', cls='lab'), C('txt', t='%s · %s tak%s' % (fmtL(r0['v']), hm(e0), ' · ' + w if w else ''), cls='dead', span=2,
                                  h='the feed died: last known 15-min futures OI change up to %s (%s, %s); not live' % (hm(e0), r0['src'], ptxt(r0)))])
        else:
            blk['rows'].append([C('txt', t='fut OI', cls='lab'), qcell('OI nahi', 'no futures OI at both ends of the 15 min (UX minute or a GC bar with oi)')])
    elif not fr.get('ok'):
        blk['rows'].append([C('txt', t='fut OI', cls='lab'), qcell('ref kam', 'fewer than %d prior days of futures OI here' % MIN_DAYS)])
    else:
        pa, pb = fut_px(day, E - 15), fut_px(day, E)
        dp = None if pa is None or pb is None else pb - pa
        if (fr['lvl'] or 0) >= 1 and dp:
            w = {(1, 1): 'naye long', (1, -1): 'naye short', (-1, 1): 'covering', (-1, -1): 'long nikal'}[(sgn(fr['v']), sgn(dp))]
            d = sgn(dp)
            lit = True
            blk['rows'].append([C('txt', t='fut OI', cls='lab'), C('txt', t=fmtL(fr['v']), cls='num nt', h='%s · %s' % (ptxt(fr), fr['src'])),
                                C('txt', t=w, cls=side_cls(d) + ' wd' + (' loud' if fr['lvl'] == 2 else ''), h='price %+.0f pts in the 15 min' % dp)])
        else:
            blk['rows'].append([C('txt', t='fut OI', cls='lab'), C('txt', t=fmtL(fr['v']), cls='num q', h='%s · %s' % (ptxt(fr), fr['src'])),
                                C('txt', t='shaant ✓', cls='ok')])
    blk['tempo'] = next((W[nm]['r15'].get('tempo') for nm in W if W[nm]['r15'].get('tempo')), None)
    tags = {oi('NIFTY', day).get(m, (0, 0, ''))[2] for m in range(E - 61, E)}
    blk['rest'] = 'I' in tags
    blk['late'] = any(not live_at('NIFTY', day, m, E) for m in range(E - 61, E) if m in oi('NIFTY', day))
    blk['state'] = 'lit' if lit else '?' if not atm or all(r[1].get('cls') == 'qm' for r in blk['rows'][:2]) else 'quiet'
    ns = [W[nm]['r15'].get('n') for nm in W if W[nm]['r15'].get('n')]
    blk['n'] = min(ns) if ns else 99
    return blk


def tokens(idx, day, E):
    """strikes that pass a tempo-free rank at the tint threshold AND carry >= 25% of the side's gross ATM±2 change; adjacent
    same-side same-sign strikes merge; deewar = adds, nikal = unwinds; `pin` on expiry when CE and PE pass at one strike."""
    atm = atm_at(idx, day, E)
    out, passed = [], {}
    for leg in (0, 1):
        ch = {j: build(idx, day, E, 15, leg, atm, j) for j in range(-2, 3)}
        gross = sum(abs(v) for v in ch.values() if v is not None)
        for j, v in ch.items():
            if v is None or not gross:
                continue
            r = oi_rank('%s@%d' % ('ce' if leg == 0 else 'pe', j), idx, day, E)
            if r.get('ok') and (r['lvl'] or 0) >= 1 and abs(v) >= TOKEN_SHARE * gross:
                passed[(leg, j)] = dict(v=v, p=r['p'], lvl=r['lvl'], share=abs(v) / gross)
    for leg in (0, 1):
        js = sorted(j for (l, j) in passed if l == leg)
        groups = []
        for j in js:
            if groups and groups[-1][-1] == j - 1 and sgn(passed[(leg, j)]['v']) == sgn(passed[(leg, groups[-1][-1])]['v']):
                groups[-1].append(j)
            else:
                groups.append([j])
        for g in groups:
            v = sum(passed[(leg, j)]['v'] for j in g)
            out.append(dict(leg=leg, ks=[atm + j * STEP[idx] for j in g], v=v, kind='deewar' if v > 0 else 'nikal',
                            d=(-1 if leg == 0 else 1) * sgn(v), p=max(passed[(leg, j)]['p'] for j in g),
                            lvl=max(passed[(leg, j)]['lvl'] for j in g), share=sum(passed[(leg, j)]['share'] for j in g)))
    if kinds(idx).get(day) == 'EXPIRY':
        for j in range(-2, 3):
            if (0, j) in passed and (1, j) in passed:
                out.append(dict(kind='pin', pin=atm + j * STEP[idx], leg=None, ks=[atm + j * STEP[idx]], v=0, d=0, p=0, lvl=0, share=0))
    out.sort(key=lambda t: -abs(t['v']))
    return out


def peer_block(day, E):
    blk = dict(title='DOOSRE INDEX', rows=[], trace={})
    lit, ns = False, []
    for idx in PEERS:
        dn = din(idx, day, E)
        sr = spread_rank(idx, day, E)
        cf, ct = confirm(idx, day, E)
        blk['trace'][idx] = dict(din=dn, spread=sr, confirm=cf, ext=ct)
        if sr.get('n'):
            ns.append(sr['n'])
        dcell = (C('txt', t='%s%.1f%%' % ('▲' if dn > 0 else '▼' if dn < 0 else '', abs(dn)), cls='num ' + side_cls(sgn(dn)), h='%s spot %% from the open' % idx)
                 if dn is not None else qcell('spot', 'the %s spot does not start by 09:20, or has no minute at %s' % (idx, hm(E))))
        if not sr.get('ok'):
            scell = qcell('ref kam' if sr.get('v') is not None else 'spot', sr.get('why', 'no spread'))
        elif idx == 'SENSEX' and (sr['lvl'] or 0) == 0:
            scell = C('txt', t='= NIFTY', cls='ok', h='spread %+.2f%% · %s: inside noise' % (sr['v'], ptxt(sr)))
        else:
            lv = sr['lvl'] or 0
            lit = lit or lv >= 1
            scell = C('txt', t=('NIFTY se %+.2f%%' % sr['v']).replace('-', '−'), cls=('spr l%d' % lv) if lv else 'spr q',
                      h='spread to NIFTY (%% from open) %+.2f%% · %s%s' % (sr['v'], ptxt(sr), ' · under the 0.15% floor' if abs(sr['v']) < SPREAD_FLOOR else ''))
        ccell = C('txt', t='', cls='')
        if cf == '?':
            ccell = qcell('confirm', 'NIFTY made a new extreme but the peer has no session to compare')
        elif cf:
            ccell = C('txt', t=cf, cls='warn' if '✗' in cf else 'ink', h='NIFTY set a session %s in the last 15 min' % cf.split()[0])
            lit = True
        blk['rows'].append([C('txt', t=idx, cls='lab'), dcell, scell, ccell])
        if idx == 'BANKNIFTY':
            pr = pace('UX', 'BANKNIFTY', day, E, 5)
            blk['trace']['BNF pace'] = pr
            if not pr.get('x'):
                e0, p0 = last_known(lambda e: (lambda r: r if r.get('x') else None)(pace('UX', 'BANKNIFTY', day, e, 5)), E - 1)
                pc = (C('txt', t='%.1f× · %s tak' % (p0['x'], hm(e0)), cls='dead', h='the UX feed died: last known BANKNIFTY 5-min pace up to %s; not live' % hm(e0))
                      if p0 else qcell(pr.get('short', '?'), pr.get('why', '')))
            else:
                thin = pr['p'] is not None and pr['p'] <= BNF_THIN
                loud = pr['p'] is not None and pr['p'] >= BNF_LOUD
                lit = lit or loud
                pc = C('pace', x=pr['x'], lvl=1 if loud else 0, thin=thin, h='BANKNIFTY 5-min pace %.2f× · %s%s' % (pr['x'], ptxt(pr), ' · thin' if thin else ''))
            st = []
            for leg, nm in ((0, 'call'), (1, 'put')):
                r = oi_rank('ce15' if leg == 0 else 'pe15', 'BANKNIFTY', day, E)
                blk['trace']['BNF ' + nm] = r
                if r.get('ok') and (r['lvl'] or 0) >= 1:
                    st.append((r['p'], leg, r['v']))
            r0 = blk['trace']['BNF call']
            if r0.get('v') is None:
                s, why = oi_why('BANKNIFTY', day, E)
                oc = qcell(s, why)
            elif not st:
                oc = C('txt', t='OI shaant ✓', cls='ok')
            else:
                p, leg, v = max(st)
                lit = True
                oc = C('txt', t=('call' if leg == 0 else 'put') + (' likh' if v > 0 else ' nikal'), cls=side_cls((-1 if leg == 0 else 1) * sgn(v)),
                       h='ATM±2 15-min %s %s · p%.0f' % ('CE' if leg == 0 else 'PE', fmtL(v), p))
            blk['rows'].append([C('txt', t='', cls='lab'), C('txt', t='pace', cls='sub'), pc, oc])
    late = any(not live_at(i, day, m, E) for i in IDXS for m in range(E - 16, E) if m in oi(i, day))
    blk['late'] = late
    blk['state'] = 'lit' if lit else '?' if all(r[1].get('cls') == 'qm' for r in blk['rows'][::2]) else 'quiet'
    blk['n'] = min(ns) if ns else 99
    return blk


def leg_face(day, E, read):
    L = leg_block(day, E, read)
    blk = dict(title='LEG', rows=[], trace=L)
    if not L.get('ok'):
        blk.update(state='?', rows=[[qcell('leg nahi', L.get('why', ''))]])
        return blk
    d = L['dir']
    blk['head'] = dict(dir=d, start=L['start'], end=L['end'], how=L['how'], age=L['age'], move=L['move'],
                       h='%s leg: %s %s → extreme %s (last tested %s) · zigzag threshold %.0f pts%s' % (
                           L['how'], L['start'], pxs(L['frm']), pxs(L['ext']), L['end'], L['thr'],
                           ' (ATM IV %.1f%% at %s → 30-min σ %.0f)' % (100 * L['iv']['iv'], L['iv']['at'], L['iv']['sigma30']) if L.get('iv') else ''))
    s_ = L.get('stretch')
    if s_:
        blk['rows'].append([C('txt', t='%s–%s' % (s_['a'], s_['b']), cls='lab'),
                            C('txt', t=('%s%.0f' % ('▲' if s_['pts'] > 0 else '▼', abs(s_['pts']))) if round(s_['pts']) else '0', cls='num ' + side_cls(sgn(s_['pts']))),
                            tilt_cell(s_['tilt']), fed_cell(s_['fed'])])
    pbk = L.get('pullback')
    if L['pb'] is None:
        blk['rows'].append([C('txt', t='abhi', cls='lab'), qcell('price', 'no futures price at T')])
    elif not pbk:
        blk['rows'].append([C('txt', t='abhi', cls='lab'), C('txt', t='extreme par', cls='ink b', h='price is still testing the leg extreme')])
    else:
        pr = pbk.get('pace') or {}
        blk['rows'].append([C('txt', t='abhi %s%.0f' % ('▲' if L['pb'] > 0 else '▼', abs(L['pb'])), cls='lab b ' + side_cls(sgn(L['pb'])),
                              h='now %s vs the extreme %s' % (pxs(L['now']), pxs(L['ext']))),
                            C('txt', t='pura wapas %s se' % L['pb_from'] if L['wapas'] >= 100 else '%.0f%% wapas %s se' % (L['wapas'], L['pb_from']), cls='ink b' if L['wapas'] >= 100 else 'ink',
                              h='%.0f%% of the main leg given back' % L['wapas']),
                            tilt_cell(pbk['tilt']),
                            C('pace', x=pr['x'], lvl=pr.get('lvl') or 0, s=strength(pr.get('p')), h='pace over the pullback %.2f×' % pr['x']) if pr.get('x') else C('txt', t='')])
    R = L['rasad']
    chips = []
    for k, lab in (('flow', 'flow'), ('oi', 'OI'), ('fut', 'fut')):
        v = R[k]
        if v == '?':
            chips.append(C('chip', lab=lab, t='?', look='amb', h='%s: could not check over the main leg' % lab))
        elif v is None:
            chips.append(C('chip', lab=lab, t='—', look='never', h='%s never fed the main leg (checked)' % lab))
        else:
            chips.append(C('chip', lab=lab, t=hm(v), look='solid' if E - v <= FRESH else 'stale', h='%s last fed the main leg at %s' % (lab, hm(v))))
    b = R.get('bnf')
    if b in (None, '?'):
        chips.append(C('chip', lab='BNF', t='?', look='amb', h='BANKNIFTY could not be compared at NIFTY\'s leg extreme'))
    else:
        chips.append(C('chip', lab='BNF', t=b['word'], look='refuse' if b['word'] == '✗' else 'confirm',
                       h='at NIFTY\'s leg extreme (%s) BANKNIFTY %s its own (%s vs its extreme %s, tolerance %.0f)' % (
                           b['nifty_t'], 'confirmed' if b['word'] == '✓' else 'did not confirm', pxs(b['near']), pxs(b['ext']), b['tol'])))
    blk['rows'].append([C('txt', t='rasad', cls='lab')] + chips)
    fresh = any(c.get('look') == 'solid' for c in chips)
    blk['state'] = 'lit' if fresh or (s_ and s_['fed'] == '✓' and E - mof(s_['b']) <= FRESH) or (pbk and pbk['fed'] == '✓') else 'quiet'
    blk['late'] = L.get('filled')
    return blk


def fed_cell(f):
    if f is None:
        return C('txt', t='?', cls='qm', h='no flow source for this stretch')
    return C('txt', t={'✓': '✓ saath', 'shaant': 'shaant ✓', 'ulte': 'ulte'}[f], cls={'✓': 'ink b', 'shaant': 'ok', 'ulte': 'warn'}[f])


# ---- header, SIRF BADE, PLAN, ? (from the v2.4 bundle, as round 1) -------------------------------------------------------------
NODE = r"""
import fs from 'node:fs';
const { run } = await import('file:///' + process.env.OFD.replace(/ /g, '%20') + '/test/shell.mjs');
const frames = JSON.parse(fs.readFileSync(process.env.F, 'utf8')), out = [];
for (const f of frames) {
  const all = JSON.parse(fs.readFileSync(process.env.OFD + `/test/session-${f.day}.ofd.json`, 'utf8')).bars.sort((a, b) => a.t - b.t);
  const T = +f.at.slice(0, 2) * 60 + +f.at.slice(3), bars = all.filter((b) => { const d = new Date(b.t + 19800000); return d.getUTCHours() * 60 + d.getUTCMinutes() + 5 <= T; });
  if (!bars.length) { out.push({ day: f.day, at: f.at, none: 'no GC bar closed by ' + f.at }); continue; }
  const a = run(bars.length, { bars }); a.win._reply = { ...f.after, ok: true, day: f.day }; a.deliver(); a.tick(); a.tick();
  const v = a.model().v2 || {};
  const ms = v.bade || (v.marks || []).filter((m) => m.tier === 'solid' || m.tier === 'ghost' || (m.tier === 'print' && !m.live));
  out.push({ day: f.day, at: f.at, price: v.price ?? null, basis: v.basis || null, src: v.src || null, refOk: !!(v.ref && v.ref.ok),
    bade: ms.map((m) => ({ t: m.t, fam: m.fam, chip: m.chip, name: m.name, p: m.p, status: m.status, winner: m.winner, tier: m.tier, kind: m.kind, hover: m.hover })),
    baaki: v.baaki || 0, plan: v.plan || null, planWhy: v.planWhy || null, inTrade: !!v.inTrade });
}
fs.writeFileSync(process.env.O, JSON.stringify(out));
"""


def recorded_frame(day, at):
    best = None
    for r in jl(DATA + 'frame/frame_%s.jsonl' % day):
        if r.get('ts') and r['ts'] <= at:
            best = r
    return best or {'ok': True, 'idx': 'NIFTY', 'day': day}


def v24(frames):
    cwd = os.getcwd()
    import frame_v2_replay as R      # chdirs into tapemap/
    parts, rows = {}, []
    try:
        for day in sorted({d for d, _ in frames}):
            ts = sorted(t for d, t in frames if d == day)
            got = R.replay('NIFTY', day, ts)
            for t in ts:
                parts[(day, t)] = got[t]
                rows.append(dict(day=day, at=t, after=dict(recorded_frame(day, t), **{k: v for k, v in got[t].items() if k not in ('day', 'at')})))
    finally:
        os.chdir(cwd)
    tmp = tempfile.mkdtemp(prefix='panelv3-')
    fi, fo, js = os.path.join(tmp, 'in.json'), os.path.join(tmp, 'out.json'), os.path.join(tmp, 'run.mjs')
    with open(fi, 'w', encoding='utf-8') as f:
        json.dump(rows, f, default=str)
    with open(js, 'w', encoding='utf-8') as f:
        f.write(NODE)
    subprocess.run(['node', js], check=True, env=dict(os.environ, F=fi, O=fo, OFD=OFD), cwd=OFD, stdout=subprocess.DEVNULL)
    with open(fo, encoding='utf-8') as f:
        model = {(m['day'], m['at']): m for m in json.load(f)}
    for p in (fi, fo, js):
        os.remove(p)
    os.rmdir(tmp)
    return {k: (parts[k], model.get(k) or {}) for k in parts}


def header(day, E, part, m, legb):
    rd = part.get('read') or {}
    b = m.get('basis') or {}
    p = m.get('price')
    khel, d = rd.get('khel') or '?', rd.get('dir') or 0
    stale = bool(rd.get('t') and mof(rd['t']) < E - READ_STALE)
    word = (khel if khel != '?' else '? ' + (rd.get('word') or 'READ nahi')) + (' ' + ('▲' if d > 0 else '▼') if khel == 'RIDE' and d else '') + \
        (' %s se' % rd['since'] if rd.get('since') else '')
    h = legb.get('head') or {}
    age = h.get('age') if h.get('how') == 'READ' else None
    dn = din('NIFTY', day, E)
    return dict(word=word, dir=d, read=rd.get('word') or '?', clock=hm(E), exp=kinds('NIFTY').get(day) == 'EXPIRY',
                fut=pxs(p), spot=('≈%ss' % pxs(round((p - b['v']) / 10) * 10)) if p is not None and b.get('ok') else '? spot',
                age=('%dh%02d' % (age // 60, age % 60)) if age else '', stale='READ %s ka' % rd['t'] if stale else '',
                din=dn, basis=b.get('v') if b.get('ok') else None, late_note=E >= 14 * 60 + 45)


def sirf(m, read):
    """V2 §A9: KHEL-relevant first (RIDE: marks favouring its side), then newest; one row per bar and kind; <= 3 rows."""
    bs = m.get('bade') or []
    d = read.get('dir') if read.get('khel') == 'RIDE' else 0
    seen, rows = {}, []
    for x in sorted(bs, key=lambda x: (0 if d and x.get('winner') == d else 1, -x['t'])):
        k = (x['t'], x.get('fam'), round(x.get('p') or 0))
        if k in seen:
            seen[k]['n'] += 1
            continue
        seen[k] = dict(x, n=1)
        rows.append(seen[k])
    return rows[:3], max(0, len(rows) - 3), m.get('baaki') or 0


def plan_rows(m, basis):
    pl, p = m.get('plan'), m.get('price')
    s = lambda x: '≈%ss' % pxs(round((x - basis) / 10) * 10) if x is not None and basis is not None else '?s'   # noqa: E731
    if m.get('inTrade'):
        return 'trade mein', [[C('txt', t='FOLD board (v2.4, unchanged)', cls='ink')]]
    if not pl:
        why = m.get('planWhy') or 'plan nahi aaya'
        import re
        g = re.search(r'futures ticks missing for (\d+) of (\d+)', why)
        return '', [[qcell('plan: fut ticks %s/%s nahi' % g.groups() if g else 'plan nahi', why)]]
    if pl.get('word') == 'RANGE':
        rows = []
        for z in (pl.get('zones') or [])[:2]:
            rows.append([C('txt', t=('BUY ▲' if z['side'] == 'buy' else 'SELL ▼') + ' FADE', cls='up' if z['side'] == 'buy' else 'dn'),
                         C('txt', t='%s–%sf' % (pxs(z['lo']), pxs(z['hi'])), cls='ink'),
                         C('txt', t='%s–%s' % (s(z['lo'])[:-1], s(z['hi'])[1:]) if basis is not None else '?s', cls='m')])
        t1 = (pl.get('t1') or {}).get('fut')
        rows.append([C('txt', t='T1 VWAP', cls='ink'), C('txt', t='%sf' % pxs(t1), cls='ink'), C('txt', t=s(t1), cls='m')])
        return 'RANGE', rows
    d = pl.get('d') or 0
    st = (pl.get('state') or '?').replace('_', ' ')
    if not d or not pl.get('zone'):
        return pl.get('word') or '', [[C('txt', t='%s · koi zone nahi' % st, cls='ink')]]
    z, k, t1 = pl.get('zone') or {}, pl.get('kill') or {}, pl.get('t1') or {}
    rows = [[C('txt', t='%s %s' % ('BUY ▲' if d > 0 else 'SELL ▼', st), cls='up' if d > 0 else 'dn'),
             C('txt', t='%s–%sf' % (pxs(z.get('lo')), pxs(z.get('hi'))), cls='ink'),
             C('txt', t='%s–%s' % (s(z.get('lo'))[:-1], s(z.get('hi'))[1:]) if basis is not None else '?s', cls='m')],
            [C('txt', t='KILL %s' % k.get('name', ''), cls='ink'), C('txt', t='%sf' % pxs(k.get('fut')), cls='ink'), C('txt', t=s(k.get('fut')), cls='m')],
            [C('txt', t='T1 %s' % t1.get('name', ''), cls='ink'), C('txt', t='%sf' % pxs(t1.get('fut')), cls='ink'), C('txt', t=s(t1.get('fut')), cls='m')]]
    return (pl.get('word') or '') + (' · 15:00 ke baad naya nahi' if pl.get('late') else ''), rows


def qline(blocks, hd, m):
    cant, read_, hidden = [], [], []
    for b in blocks:
        for r in b.get('rows', []):
            for c in r:
                if c.get('cls') == 'qm' or (c.get('kind') == 'chip' and c.get('look') == 'amb'):
                    cant.append(('rasad %s ?' % c['lab'] if c.get('kind') == 'chip' else '%s %s' % (
                        {'KAUN DABA RAHA': 'flow', 'KAUN LIKH RAHA': 'OI', 'DOOSRE INDEX': 'peers', 'LEG': 'leg', 'PLAN': 'plan'}.get(b['title'], b['title']),
                        (c.get('t') or '')[2:]), c.get('h', '')))
    if hd.get('stale'):
        cant.insert(0, ('READ %s se ruka' % hd['stale'][5:10], 'READ frozen at %s: TapeMap had no feed after it' % hd['stale'][5:10]))
    if hd.get('spot') == '? spot':
        cant.append(('spot ? basis', 'the futures-spot basis is implausible; levels are futures only'))
    if not m.get('refOk'):
        cant.append(('marks ref nahi', 'rank ref nahi: marks not ranked'))
    if m.get('baaki'):
        hidden.append(('%d chhote marks' % m['baaki'], '%d chhote marks' % m['baaki']))
    cant = list(dict.fromkeys(cant))
    groups = (('could not check', cant, 'qm'), ('checked, nothing', read_, 'ink'), ('not shown', hidden, 'q'))
    title = ' | '.join('%s: %s' % (n, ' · '.join(x[1] for x in xs)) for n, xs, _ in groups if xs)
    first = next((g for g in groups if g[1]), None)
    if not first:
        return dict(title='?', rows=[[C('txt', t='shaant ✓ · sab check hua', cls='ok')]], state='quiet')
    more = len(cant) + len(read_) + len(hidden) - 1
    return dict(title='?', rows=[[C('txt', t='%s%s' % (first[1][0][0], ' · +%d …' % more if more else ''), cls=first[2], h=title)]],
                lists={n: [x[1] for x in xs] for n, xs, _ in groups})


# ---- one frame -------------------------------------------------------------------------------------------------------------------
def flow_src(day, E):
    """one pace source (judgement call; V2 does not say): UX when it has today's cumulative and all three ladder windows, else
    GC when it does, else whichever has the cumulative, else whichever has the 5 min. Tilt shows both sources where they exist."""
    al = lambda s: E - E % 5 if s == 'GC' else E   # noqa: E731
    for src in ('UX', 'GC'):
        e = al(src)
        if cum(src, 'NIFTY', day, e, E) is not None and all(fwin(src, 'NIFTY', day, a, b, E if b == E else None) for a, b in ((e - 5, e), (e - 15, e), (e - 60, e - 15))):
            return src
    for src in ('UX', 'GC'):
        if cum(src, 'NIFTY', day, al(src), E) is not None:
            return src
    for src in ('UX', 'GC'):
        if fwin(src, 'NIFTY', day, E - 5 - (E % 5 if src == 'GC' else 0), E - (E % 5 if src == 'GC' else 0), E):
            return src
    return None


def build_frame(day, at, part, m, rnd):
    E = mof(at)
    read = part.get('read') or {}
    lg = leg_face(day, E, read)
    src = flow_src(day, E)
    fl = flow_block(day, E, src)
    ob = oi_block(day, E)
    pb = peer_block(day, E)
    hd = header(day, E, part, m, lg)
    sb, more, baaki = sirf(m, read)
    pw, prow = plan_rows(m, hd['basis'])
    late_flow = src == 'GC' and any(not gc_live(day, st, E) for st in range(E - 60 - E % 5, E, 5) if st in (gc().get(day) or {}))
    fl['late'] = late_flow
    q = qline([lg, fl, ob, pb], hd, m)
    ns = [b.get('n') for b in (fl, ob, pb) if b.get('n') and b['n'] < 99]
    hd['ref'] = 'ref %dd' % min(ns) if ns else 'ref ?'
    shot = '%s_%s_after.png' % (day, at.replace(':', ''))
    return dict(id='%s_%s' % (day, at.replace(':', '')), day=day, T=at, random=rnd, kind=kinds('NIFTY').get(day), header=hd,
                leg=lg, flow=fl, oi=ob, peers=pb, sirf=dict(rows=sb, more=more, baaki=baaki), plan=dict(word=pw, rows=prow), q=q,
                shot=SHOT_REL + shot if os.path.exists(SHOT_DIR + shot) else None)


# ---- text (for the notes and the report; the face is the html) -----------------------------------------------------------------
def ctext(c):
    k = c.get('kind')
    if k == 'pace':
        return '%.1f×(s%.1f)' % (c['x'], c.get('s', 0))
    if k == 'tilt':
        if c['mode'] == 'ulte':
            return '[ulte bech %.0f | kharid %.0f]' % (50 + c['left'], 50 + c['right'])
        return '[%s %.0f%% s%.1f%s]' % ('kharid' if c['side'] > 0 else 'bech', 50 + c['ex'], c['s'], (' ' + c['tag']) if c.get('tag') else '')
    if k == 'oiq':
        return '[%s]' % ' '.join('%s(p%s)' % (fmtL(v), '?' if p is None else '%.0f' % p) for v, p in zip(c['q'], c['qp']))
    if k == 'chip':
        return '%s %s%s' % (c['lab'], c['t'], {'solid': '', 'stale': ' (grey)', 'never': '', 'amb': '', 'confirm': '', 'refuse': ' (red)'}[c['look']])
    if k == 'tok':
        return c['t'] + ('*' if c['lvl'] == 2 else '')
    return c.get('t') or ''


def text(f):
    h = f['header']
    out = ['NIFTY  %s%s%s%s   %s' % (h['word'], ' · ' + h['age'] if h['age'] else '', '  EXP' if h['exp'] else '', '  [' + h['stale'] + ']' if h['stale'] else '', h['clock']),
           '  %sf | %s   %s din   %s' % (h['fut'], h['spot'], ('%+.1f%%' % h['din']) if h['din'] is not None else '?', h['ref'])]
    lg = f['leg']
    if lg.get('head'):
        hh = lg['head']
        out.append('LEG %s %s–%s %+.0f   (%s)' % ('▲' if hh['dir'] > 0 else '▼', hh['start'], hh['end'], hh['move'], hh['how']))
    else:
        out.append('LEG')
    for r in lg['rows']:
        out.append('  ' + '  '.join(ctext(c) for c in r if ctext(c)))
    for key in ('flow', 'oi', 'peers'):
        b = f[key]
        sub = []
        if b.get('tempo'):
            sub.append('aaj %.1f×' % b['tempo'])
        if key == 'flow' and b.get('src') == 'GC':
            sub.append('GC')
        if b.get('late'):
            sub.append('bad mein aaya')
        out.append('%s%s' % (b['title'], ('   (' + ' · '.join(sub) + ')') if sub else ''))
        if key == 'flow' and b.get('src'):
            out.append('        5m      15m     pichle45')
        for r in b['rows']:
            out.append('  ' + '  '.join(ctext(c) for c in r if ctext(c)))
    out.append('SIRF BADE   (P phase · R roka · T thakan · Z zor · B bada · ✕ toota)%s' % ('  +%d aur' % f['sirf']['more'] if f['sirf']['more'] else ''))
    for x in f['sirf']['rows']:
        out.append('  %s %s %s%s%s' % (hm(mint(x['t'])), x.get('fam') or '·', x.get('chip') or x.get('name'), ' ×%d' % x['n'] if x['n'] > 1 else '', ' ✕' if x['status'] == 'TOOTA' else ''))
    if not f['sirf']['rows']:
        out.append('  koi bada mark nahi')
    out.append('PLAN  %s' % f['plan']['word'])
    for r in f['plan']['rows']:
        out.append('  ' + '  '.join(ctext(c) for c in r if ctext(c)))
    out.append('? ' + ctext(f['q']['rows'][0][0]))
    return '\n'.join(out)


# ---- the page ------------------------------------------------------------------------------------------------------------------------
CSS = """
*{box-sizing:border-box}html,body{margin:0;background:#fff;color:#1c2026;font:14px/1.4 'Segoe UI',system-ui,sans-serif}
.top{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid #e3e7ec;padding:8px 16px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.top b{margin-right:6px}.top a{font:12px Consolas,monospace;color:#1c2026;text-decoration:none;border:1px solid #d5dbe2;border-radius:4px;padding:2px 6px}
.top a.r{border-style:dashed}.top a:hover{background:#f1f4f7}.top .note{color:#5c6675;font-size:12px;margin-left:8px}
.fr{padding:14px 16px 6px}.fr h2{font:600 14px 'Segoe UI';margin:0 0 6px}.fr h2 span{color:#5c6675;font-weight:400;font-size:12px;margin-left:8px}
.stage{display:flex;width:1700px;height:820px;border:1px solid #d5dbe2}
.ch{width:1340px;height:820px;overflow:hidden;background:#fff}.ch img{display:block}
.noshot{width:1340px;height:820px;background:#eef0f3;color:#8a94a0;display:flex;align-items:center;justify-content:center;font:600 18px 'Segoe UI'}
.pn{width:360px;height:820px;overflow:hidden;border-left:1px solid #d5dbe2;padding:7px 9px;background:#fff;font:12px/1 Consolas,'Cascadia Mono',monospace;font-variant-numeric:tabular-nums}
.hd .l1{display:flex;align-items:center;gap:6px;white-space:nowrap}
.ix{font-weight:700;font-size:15px}.kh{font-weight:700;font-size:15px;padding:2px 6px;border-radius:3px;background:#eef0f3}
.kh.up{background:#dff3ec;color:#0b6b52}.kh.dn{background:#fbe4e1;color:#a8321f}
.age{font-size:12px;color:#3f4854}.exp{font:700 12px Consolas;border:1.5px solid #3f4854;border-radius:3px;padding:1px 4px}
.clk{margin-left:auto;font-weight:700;font-size:14px}.stale{color:#9a6a00;background:#fff4d6;font-size:12px;padding:1px 4px;border-radius:3px}
.hd .l2{display:flex;gap:10px;align-items:center;margin-top:6px;white-space:nowrap;font-size:13px}.ref{margin-left:auto;color:#5c6675;font-size:12px}
.bk{margin-top:8px;border-top:1px solid #e3e7ec;padding-top:4px}
.bh{display:flex;justify-content:space-between;align-items:center;height:18px;white-space:nowrap}
.bh .t{font:700 12px 'Segoe UI';letter-spacing:.04em;color:#3f4854}.bh .sb{font-size:12px;color:#5c6675}
.bh .legt{display:flex;gap:6px;align-items:center}.lg{font-size:12px;color:#5c6675;white-space:nowrap;margin:1px 0 2px;letter-spacing:-.02em}
.late{color:#8a94a0;font-style:italic}
.rw{display:grid;align-items:center;height:23px;white-space:nowrap;column-gap:5px}
.rw>span{overflow:hidden;font-size:12px}
.gleg{grid-template-columns:76px 34px 70px 1fr}.gpb{grid-template-columns:60px 124px 64px 1fr}.grs{grid-template-columns:38px repeat(4,auto);column-gap:4px;justify-content:start}
.gfl{grid-template-columns:32px 82px 82px 82px 1fr}.gfh{grid-template-columns:32px 82px 82px 82px 1fr;height:15px;color:#8a94a0}
.gbu{grid-template-columns:76px 82px 70px 38px 1fr}
.goi{grid-template-columns:52px 42px 60px 1fr;height:37px}.gtok{grid-template-columns:52px 112px 42px 1fr}.gfu{grid-template-columns:52px 42px 1fr}
.gpe{grid-template-columns:76px 52px 1fr auto}.gsb{grid-template-columns:40px 16px 1fr 12px}.gpl{grid-template-columns:92px 108px 1fr}
.g1{grid-template-columns:1fr}
.lab{color:#3f4854;letter-spacing:-.02em}.lab.old,.sub{color:#8a94a0}
.num{text-align:right}.q{color:#aab2bc}.ok{color:#1c2026}.ink{color:#1c2026}.b{font-weight:700}.m{color:#5c6675}
.qm{color:#9a6a00;background:#fff4d6;border-radius:3px;padding:2px 4px;justify-self:start}
.nil{color:#8a94a0}
.up{color:#0b7a5c}.dn{color:#b73a26}.nt{color:#3f4854}
.loud{font-weight:700;border-radius:3px;padding:2px 3px}.loud.up{background:#d8f1e8}.loud.dn{background:#fadcd7}.loud.nt{background:#e6e9ee}
.word{font-weight:700;color:#1c2026}.warn{font-weight:700;color:#1c2026}.wd{font-weight:700}.px{font-weight:700}
.pace{justify-self:start;padding:2px 5px;border-radius:3px;color:#8a94a0}.pace.l1{background:#e1e6ee;color:#1c2026}.pace.l2{background:#4a5568;color:#fff;font-weight:700}
.pace.thin{color:#aab2bc;font-style:italic}
.tilt{display:flex;align-items:center;gap:3px}.dv{position:relative;width:62px;height:12px;background:#f3f5f7;border-radius:2px}
.dv b{position:absolute;left:31px;top:-2px;bottom:-2px;border-left:1.5px solid #6b7480}
.dv i{position:absolute;top:1px;bottom:1px}.dv i.l{right:31px;border-radius:2px 0 0 2px}.dv i.r{left:32px;border-radius:0 2px 2px 0}
.dv i.hl{right:31px;background:repeating-linear-gradient(135deg,#9aa3ae 0 3px,#eef0f3 3px 6px)}.dv i.hr{left:32px;background:repeating-linear-gradient(135deg,#9aa3ae 0 3px,#eef0f3 3px 6px)}
.pc{display:flex;align-items:center;gap:3px}.pt{position:relative;width:40px;height:10px;background:#f3f5f7;border-radius:2px}
.pt i{position:absolute;left:0;top:0;bottom:0;border-radius:2px}.pv{font-size:12px}.pc.thin .pv{font-style:italic}
.qc{display:inline-block;position:relative;width:9px;height:31px}.qc b{position:absolute;left:0;width:9px;border-radius:1px}
.oiq{display:flex;gap:3px;position:relative;height:31px;align-items:stretch;background:#f4f6f8;border-radius:3px;padding:0 3px}.oiq .mid{position:absolute;left:2px;right:2px;top:15px;border-top:1px solid #b8bfc8}
.dead{color:#9a6a00;font-style:italic}
.chip.confirm{background:#fff;color:#1c2026;border:1.5px solid #1c2026}.chip.refuse{background:#fff;color:#b73a26;border:1.5px solid #b73a26;font-weight:700}
.tr i{position:absolute;top:0;bottom:0;border-radius:2px}.tr b{position:absolute;left:50%;top:0;bottom:0;border-left:1px dashed #9aa3ae}
.tr i.up{background:#7cc7ae}.tr i.dn{background:#ea9d8e}.tr i.up.loud{background:#0b7a5c}.tr i.dn.loud{background:#b73a26}.tr i.q{background:#c9ced6}
.tr i.hatch{background:repeating-linear-gradient(135deg,#b8bfc8 0 3px,#eef0f3 3px 6px)}
.ttag{font-size:12px;color:#5c6675}
.oiq{display:flex;align-items:center;gap:3px;height:26px}.oiq i{display:inline-block;width:12px;position:relative}
.chip{border-radius:10px;padding:2px 5px;font-size:12px;justify-self:start;border:1px solid transparent}
.chip.solid{background:#1c2026;color:#fff}.chip.stale{background:#eef0f3;color:#6b7480}.chip.never{color:#6b7480;border:1px dashed #b8bfc8}
.chip.amb{background:#fff4d6;color:#9a6a00}.chip .x{font-weight:700;color:#1c2026;margin-left:3px}.chip.solid .x{color:#fff}
.tok{padding:2px 4px;border-radius:3px}.tok.l1.up{color:#0b7a5c;background:#e6f5ef}.tok.l1.dn{color:#b73a26;background:#fcebe8}
.tok.l2.up{color:#fff;background:#0b7a5c;font-weight:700}.tok.l2.dn{color:#fff;background:#b73a26;font-weight:700}
.tm{color:#5c6675}.L{font-weight:700;text-align:center;border:1.5px solid currentColor;border-radius:3px;font-size:12px;line-height:14px}
.toota{color:#aab2bc;text-decoration:line-through}.x{color:#aab2bc}
.amb{color:#9a6a00}.spr{justify-self:start;padding:2px 5px;border-radius:3px}.spr.l1{background:#e1e6ee;color:#1c2026}.spr.l2{background:#4a5568;color:#fff;font-weight:700}
.goi{height:27px}
.ovf{background:#b73a26;color:#fff;font:700 12px 'Segoe UI';padding:2px 6px;display:none}
"""

JS = """
const only = new URLSearchParams(location.search).get('only');
if (only) { document.querySelectorAll('.fr').forEach((f) => { if (f.id !== only) f.remove(); }); document.querySelector('.top').remove(); }
document.querySelectorAll('.pn').forEach((p) => { if (p.scrollHeight > p.clientHeight + 1) { const o = p.closest('.fr').querySelector('.ovf'); o.style.display = 'inline-block'; o.textContent = 'PANEL OVERFLOWS ' + (p.scrollHeight - p.clientHeight) + 'px'; } });
"""


def e(s): return html.escape(str(s), quote=True)


def oi_svg(q, qp, leg, scale):
    """§D4: four real columns, oldest -> newest, 9 px wide, up to 14 px up (adding) or down (cutting) from a midline, on one
    scale per side; each column's colour is the side it favours, its strength the quarter's own rank."""
    out = []
    pad = 4 - len(q)
    for i in range(4):
        if i < pad:
            out.append('<i class="qc"><b style="top:15px;height:1px;background:#d5dbe2"></b></i>')
            continue
        v, p = q[i - pad], qp[i - pad]
        h = max(1, round(14 * min(1.0, abs(v) / scale)))
        d = (-1 if leg == 0 else 1) * sgn(v)
        rgb = '11,122,92' if d > 0 else '183,58,38'
        top = 15 - h if v > 0 else 16
        out.append('<i class="qc" title="%s · p%s"><b style="top:%dpx;height:%dpx;background:rgba(%s,%.2f)"></b></i>' % (
            fmtL(v), '?' if p is None else '%.0f' % p, top, h, rgb, max(0.18, strength(p))))
    return '<span class="oiq">%s<span class="mid"></span></span>' % ''.join(out)


def cell_html(c):
    k, h = c.get('kind'), e(c.get('h', ''))
    sp = ' style="grid-column:span %d"' % c['span'] if c.get('span', 1) > 1 else ''
    if k == 'pace':
        w = round(40 * min(3.0, c['x']) / 3)
        s_ = c.get('s', 0.15)
        return '<span class="pc%s" title="%s"><span class="pt"><i style="width:%dpx;background:rgba(74,85,104,%.2f)"></i></span><span class="pv" style="color:rgba(28,32,38,%.2f)">%.1f×</span></span>' % (
            ' thin' if c.get('thin') else '', h, w, max(0.12, s_), max(0.45, min(1.0, 0.35 + s_)), c['x'])
    if k == 'tilt':
        tag = '<span class="ttag">%s</span>' % e(c['tag']) if c.get('tag') else ''
        px = lambda ex: round(30 * min(30.0, ex) / 30)   # noqa: E731  half-track 30 px = 30 points beyond 50%
        if c['mode'] == 'ulte':
            bars = '<i class="hl" style="width:%dpx"></i><i class="hr" style="width:%dpx"></i>' % (max(1, px(c['left'])), max(1, px(c['right'])))
        else:
            rgb = '11,122,92' if c['side'] > 0 else '183,58,38'
            bars = '<i class="%s" style="width:%dpx;background:rgba(%s,%.2f)"></i>' % ('r' if c['side'] > 0 else 'l', max(1, px(c['ex'])), rgb, max(0.15, c['s']))
        return '<span class="tilt" title="%s"><span class="dv">%s<b></b></span>%s</span>' % (h, bars, tag)
    if k == 'oiq':
        return '<span title="%s">%s</span>' % (h, oi_svg(c['q'], c['qp'], c['leg'], c['scale']))
    if k == 'chip':
        return '<span class="chip %s" title="%s">%s %s</span>' % (c['look'], h, e(c['lab']), e(c['t']))
    if k == 'tok':
        return '<span class="tok l%d %s" title="%s">%s</span>' % (c['lvl'], side_cls(c['d']), h, e(c['t']))
    sty = (' style="%s%s"' % (c['sty'], ';grid-column:span %d' % c['span'] if c.get('span', 1) > 1 else '')) if c.get('sty') else sp
    return '<span class="%s" title="%s"%s>%s</span>' % (e(c.get('cls', '')), h, sty, e(c.get('t', '')))


def rows_html(rows, g):
    return ''.join('<div class="rw %s">%s</div>' % ('g1' if len(r) == 1 else g, ''.join(cell_html(c) for c in r)) for r in rows)


def panel_html(f):
    h = f['header']
    kc = 'up' if h['dir'] > 0 else 'dn' if h['dir'] < 0 else ''
    dn = h['din']
    out = ['<div class="hd"><div class="l1"><span class="ix">NIFTY</span><span class="kh %s" title="READ %s">%s</span>%s%s%s<span class="clk">%s</span></div>'
           % (kc, e(h['read']), e(h['word']), '<span class="age">%s</span>' % e(h['age']) if h['age'] else '', '<span class="exp">EXP</span>' if h['exp'] else '',
              '<span class="stale">%s</span>' % e(h['stale']) if h['stale'] else '', e(h['clock'])),
           '<div class="l2"><span>%sf | %s</span><span class="%s">%s</span><span class="ref" title="the smallest reference behind a tinted cell">%s</span></div></div>'
           % (e(h['fut']), e(h['spot']), side_cls(sgn(dn or 0)), e(('%s%.1f%% din' % ('▲' if dn > 0 else '▼' if dn < 0 else '', abs(dn))) if dn is not None else '? din'), e(h['ref']))]
    lg = f['leg']
    if lg.get('head'):
        hh = lg['head']
        mv = '%s%.0f' % ('+' if hh['move'] > 0 else '−', abs(hh['move']))
        body = ''
        for r in lg['rows']:
            lab = r[0].get('t', '')
            body += rows_html([r], 'grs' if lab == 'rasad' else 'gpb' if lab.startswith('abhi') else 'gleg')
        out.append('<div class="bk"><div class="bh" title="%s"><span class="t">LEG <span class="%s">%s %s–%s %s</span></span><span class="sb">%s%s</span></div>%s</div>'
                   % (e(hh['h']), side_cls(hh['dir']), '▲' if hh['dir'] > 0 else '▼', e(hh['start']), e(hh['end']), e(mv),
                      'zigzag' if hh['how'] == 'zigzag' else 'READ', ' · <span class="late">bad mein aaya</span>' if lg.get('late') else '', body))
    else:
        out.append('<div class="bk"><div class="bh"><span class="t">LEG</span></div>%s</div>' % rows_html(lg['rows'], 'g1'))
    fl = f['flow']
    sub = []
    if fl.get('src') == 'GC':
        sub.append('GC')
    if fl.get('late'):
        sub.append('<span class="late">bad mein aaya</span>')
    if fl.get('tempo'):
        sub.append('aaj %.1f×' % fl['tempo'])
    fh = '<div class="rw gfh"><span></span><span>5m</span><span>15m</span><span>pichle 45m</span><span></span></div>' if fl.get('src') else ''
    out.append('<div class="bk"><div class="bh"><span class="t">KAUN DABA RAHA</span><span class="sb">%s</span></div>%s%s%s</div>'
               % (' · '.join(sub), fh, rows_html(fl['rows'][:2], 'gfl'), rows_html(fl['rows'][2:], 'gbu')))
    ob = f['oi']
    sub = (['<span class="late">bad mein aaya</span>'] if ob.get('late') else ['REST'] if ob.get('rest') else []) + \
        (['aaj %.1f×' % ob['tempo']] if ob.get('tempo') else [])
    rows = ''
    for r in ob['rows']:
        lab = r[0].get('t')
        g = 'gtok' if lab in ('deewar', 'nikal') else 'gfu' if lab == 'fut OI' else 'goi'
        rows += rows_html([r], g)
    out.append('<div class="bk"><div class="bh"><span class="t" title="15-min builds, ATM±2 fixed at T">KAUN LIKH RAHA</span><span class="sb">%s</span></div>%s</div>' % (' · '.join(sub), rows))
    pb = f['peers']
    out.append('<div class="bk"><div class="bh"><span class="t" title="din %%: from the open (spot) · NIFTY se: the spread to NIFTY">DOOSRE INDEX</span><span class="sb">%s</span></div>%s</div>'
               % ('<span class="late">bad mein aaya</span>' if pb.get('late') else '', rows_html(pb['rows'], 'gpe')))
    sb = f['sirf']
    srows = []
    for x in sb['rows']:
        w = x.get('winner') or 0
        srows.append([C('txt', t=hm(mint(x['t'])), cls='tm'), C('txt', t=x.get('fam') or '·', cls='L ' + side_cls(w)),
                      C('txt', t=(x.get('chip') or x.get('name')) + (' ×%d' % x['n'] if x['n'] > 1 else ''), cls='toota' if x['status'] == 'TOOTA' else side_cls(w), h=' · '.join(x.get('hover') or [])),
                      C('txt', t='✕' if x['status'] == 'TOOTA' else '', cls='x')])
    if not srows:
        srows = [[C('txt', t='koi bada mark nahi', cls='ok')]]
    out.append('<div class="bk"><div class="bh"><span class="t">SIRF BADE</span><span class="sb">%s</span></div><div class="lg">P phase · R roka · T thakan · Z zor · B bada · ✕ toota</div>%s</div>'
               % ('+%d aur · baaki %d' % (sb['more'], sb['baaki']) if sb['more'] else 'baaki %d chhote' % sb['baaki'], rows_html(srows, 'gsb')))
    pl = f['plan']
    out.append('<div class="bk"><div class="bh"><span class="t">PLAN</span><span class="sb">%s · fut | spot</span></div>%s</div>' % (e(pl['word']), rows_html(pl['rows'], 'gpl')))
    out.append('<div class="bk"><div class="bh"><span class="t">?</span></div>%s</div>' % rows_html(f['q']['rows'], 'g1'))
    return '<div class="pn">%s</div>' % ''.join(out)


def write_html(frames, note):
    picks = ''.join('<a href="#%s"%s>%s Oct %s</a>' % (f['id'], ' class="r"' if f['random'] else '', f['day'][8:], f['T']) for f in frames)
    body = []
    for f in frames:
        ch = ('<div class="ch"><img src="%s" width="1700" height="820" alt="chart %s %s"></div>' % (f['shot'], f['day'], f['T'])) if f['shot'] else '<div class="noshot">no chart shot</div>'
        body.append('<section class="fr" id="%s"><h2>%s · as of %s<span>%s day%s</span> <span class="ovf"></span></h2><div class="stage">%s%s</div></section>'
                    % (f['id'], f['day'], f['T'], f['kind'], ' · random frame' if f['random'] else '', ch, panel_html(f)))
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Panel v3 mockup</title>'
            '<style>%s</style></head><body><div class="top"><b>Panel v3 · design v2</b>%s<span class="note">%s · round 1: <a href="mockup-v1.html">mockup-v1.html</a></span></div>%s<script>%s</script></body></html>'
            % (CSS, picks, e(note), ''.join(body), JS))
    with open(HERE + '/mockup.html', 'w', encoding='utf-8') as fh:
        fh.write(page)


# ---- firing table and self-check ---------------------------------------------------------------------------------------------------
def firing(frames):
    out = {}
    for key, nm in (('leg', 'LEG'), ('flow', 'KAUN DABA RAHA'), ('oi', 'KAUN LIKH RAHA'), ('peers', 'DOOSRE INDEX')):
        for f in frames:
            k = 'EXPIRY' if f['kind'] == 'EXPIRY' else 'NORMAL'
            st = f[key].get('state', '?')
            out.setdefault(nm, {}).setdefault(k, {'lit': 0, 'quiet': 0, '?': 0})[st] += 1
    return out


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k != 'trace'}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def selfcheck_md(frames, which):
    out = ['## Self-check: the inputs behind every new cell (generated)\n',
           'x = lots ÷ (median of the same window on prior days × tempo^w). Ranks are against the same x on prior days; '
           '"tint" is the N-based cut (p80 / p85 / p90), "loud" +10. Text form of the pictures: `[bech 71%]` = a red tilt bar at 71%, '
           '`*` = loud, `[+60 +91 +23 +54]` = the four OI blocks oldest→newest.\n']
    for f in (x for x in frames if x['id'] in which):
        out.append('### %s %s (%s day)\n' % (f['day'], f['T'], f['kind']))
        out.append('```\n%s\n```\n' % text(f))
        L = f['leg']['trace']
        if L.get('ok'):
            out.append('- **LEG**: %s main leg (%s, threshold %.0f pts%s) from %s at %s to the extreme %s, last tested %s = %+.1f; now %s, pullback %s (%s%% back) since %s' % (
                'down' if L['dir'] < 0 else 'up', L['how'], L['thr'], ', ATM IV %.3f at %s' % (L['iv']['iv'], L['iv']['at']) if L.get('iv') else '',
                pxs(L['frm']), L['start'], pxs(L['ext']), L['end'], L['move'], pxs(L['now']), '?' if L['pb'] is None else '%+.1f' % L['pb'],
                '?' if L['wapas'] is None else '%.0f' % L['wapas'], L['pb_from']))
            if L.get('pullback'):
                out.append('  - pullback tilt: %s → %s' % ('; '.join('%s b%d s%d (%+.2f, p%s)' % (src, r['buy'], r['sell'], r['t'], '?' if r['p'] is None else '%.0f' % r['p'])
                                                             for src, r in (L['pullback']['tilt'].get('per') or {}).items()), L['pullback']['fed']))
            for k in ('stretch',):
                s = L.get(k)
                if s:
                    out.append('  - %s %s→: %+.1f pts; tilt %s → %s' % (k, s['a'], s['pts'] or 0, '; '.join('%s b%d s%d (%+.2f, band %s)' % (src, r['buy'], r['sell'], r['t'], 'n/a' if r['band'] is None else '%.2f' % r['band'])
                                                                                             for src, r in (s['tilt'].get('per') or {}).items()), s['fed']))
            out.append('  - rasad (main leg): %s' % ', '.join('%s %s' % (k, hm(v) if isinstance(v, int) else ('never' if v is None else v if isinstance(v, str) else json.dumps(v, default=str))) for k, v in L['rasad'].items()))
        fl = f['flow']['trace']
        for r, lab in zip(fl.get('pace', []), ('5m', '15m', 'pichle45')):
            out.append('- **pace %s** (%s): %s' % (lab, r.get('src'), ('lots %d (b %d / s %d) → x %.2f, p%.0f of %d days, tempo %.2f, level %s' % (r['lots'], r['buy'], r['sell'], r['x'], r['p'], r['n'], r['tempo'] or 0, r['lvl'])) if r.get('x') else r.get('why')))
        for t, lab in zip(fl.get('tilt', []), ('5m', '15m', 'pichle45')):
            out.append('- **tilt %s**: %s → %s' % (lab, '; '.join('%s b%d s%d %+.2f (band %s)' % (s, r['buy'], r['sell'], r['t'], 'n/a' if r['band'] is None else '%.2f' % r['band']) for s, r in (t.get('per') or {}).items()) or 'none', t.get('state')))
        if fl.get('words'):
            out.append('- **ladder words at T, T−1, T−2 evaluations**: pace %s · tilt %s' % (fl['words']['pace'], fl['words']['tilt']))
        if fl.get('burst'):
            out.append('- **burst**: `%s`' % json.dumps(fl['burst'], default=str))
        ot = f['oi']['trace']
        for nm in ('CALL', 'PUT'):
            if nm in ot:
                r = ot[nm]
                out.append('- **%s**: 15m %s (p%s of %s days, tempo %s), quarters oldest→newest %s, hour-gross p%s, word at T−10/T−5/T %s → %s' % (
                    nm, fmtL(r['v']), 'n/a' if r['p'] is None else '%.0f' % r['p'], r['n'], 'n/a' if not r['tempo'] else '%.2f' % r['tempo'],
                    ' '.join('%+.1f' % v for v in r['q']), 'n/a' if r['gross_p'] is None else '%.0f' % r['gross_p'], list(reversed(r['held'])), r['word']))
        for t in ot.get('tokens', []):
            out.append('- **token** %s %s: %s, p%.0f, %.0f%% of the side gross → %s' % ('CALL' if t['leg'] == 0 else 'PUT' if t['leg'] == 1 else '', '/'.join(fmtk(k) for k in t['ks']), fmtL(t['v']), t['p'], 100 * t['share'], t['kind']))
        fr = ot.get('fut') or {}
        out.append('- **fut OI**: %s' % ('%s 15m %+.2fL, p%s of %s days' % (fr.get('src'), fr['v'], 'n/a' if fr.get('p') is None else '%.0f' % fr['p'], fr.get('n')) if fr.get('v') is not None else 'none'))
        for idx in PEERS:
            t = f['peers']['trace'][idx]
            sr = t['spread']
            out.append('- **%s**: din %s, spread %s%s, confirm %s' % (idx, 'n/a' if t['din'] is None else '%+.2f%%' % t['din'], 'n/a' if sr.get('v') is None else '%+.2f%%' % sr['v'],
                                                                  ' p%.0f of %d days' % (sr['p'], sr['n']) if sr.get('p') is not None else ' (%s)' % sr.get('why', ''), t['confirm']))
        out.append('')
    return '\n'.join(out)


def main():
    rnd = pick_random()
    frames_in = sorted(FIXED + rnd)
    print('frames:', frames_in, '\nrandom (seed %d):' % SEED, rnd, flush=True)
    V = v24(frames_in)
    frames = [build_frame(d, t, *V[(d, t)], (d, t) in rnd) for d, t in frames_in]
    for f in frames:
        f['text'] = text(f)
        print('\n' + f['text'], flush=True)
    fire = firing(frames)
    print('\nfiring:', json.dumps(fire))
    doc = dict(built_from='build_panel.py (design v2)', seed=SEED, random=rnd, firing=fire, frames=frames)
    with open(HERE + '/frames.json', 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1, default=str)
    write_html([strip(f) for f in frames], '%d frames · 3 random (seed %d, dashed): %s · hover any cell for numbers'
               % (len(frames), SEED, ', '.join('%s %s' % x for x in rnd)))
    notes, mark = HERE + '/NOTES.md', '<!-- SELF-CHECK: generated by build_panel.py; everything below this line is rewritten on every run -->'
    if os.path.exists(notes):
        with open(notes, encoding='utf-8') as fh:
            top = fh.read().split(mark)[0]
        body = top + mark + '\n\n' + selfcheck_md(frames, ('2026-10-16_1000', '2026-10-16_1105', '2026-10-19_1430'))
        with open(notes, 'w', encoding='utf-8') as fh:
            fh.write(body)


if __name__ == '__main__':
    main()
