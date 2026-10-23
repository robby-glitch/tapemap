"""fold.py -- THE HOLD / EXIT ENGINE, rev 6, in shadow (docs/pro-tool/6-blueprint.md §4, 6-amendment.md §3).

PORTED, NOT REINVENTED: the replay that produced §4.9's numbers is scratchpad j6/reader_j6.py
(FOLD_NEEDS=p3, MODE=fill, TRAIL_ON_BREAK=0, NEVER_LOOSEN=1; EXP_TRAIL=EXP_PLAIN=1 on the expiry day),
itself t5/reader_t5.py + two flags, on h3/reader6.py. Its fills and 1-minute bars come from
ladder.Ladder(lot, tick=10.0, interval_s=60) over the book rows (h3/build.py); the same here. Where the
blueprint's text and the harness differ the text wins, and the place is marked "blueprint:".

INPUT, recorded rows only, in the shapes the recorders write:
    book   data/book/book_<IDX>_<day>.jsonl rows (arrival `t`, `ltt`, `ltp`, `ltq`, `vtt`, `b`, `a`)
    chain  data/chain/chain_<IDX>_<day>.jsonl rows (`ts` HH:MM:SS, `strikes[k, ce{ltp, oi, delta}, pe{...}]`)
    vpin   data/vpin_fast.jsonl rows (`at`, `buy`, `sell`, `inst`, `day`)
    tape   data/tape/tape_<IDX>_<day>.jsonl rows (GoCharting 5-min bars; used only to dispute a fight)
    prior  up to 5 prior sessions of the front-month series, oldest first, each {"bars": [{h, l, c, vol}],
           "fills": [{p, q}]} -- session_from_book() builds one from a day's book rows
Her trade: {k, ty: CE|PE, side: BUY|SELL, p0, entry_t: HH:MM:SS, trade_id?}. d = +1 when the trade wants
the future up (long CE, short PE), else -1; a sale is the same engine with d flipped (§4.10).

Pure: no I/O, no clock reads -- `now` is always given. Deterministic in the rows' key order (a book row by
its arrival t, a chain row by its own ts, chain first on a tie), so a restart recomputes the same events
(§10). It gates nothing; there is no order path. Every number is [M] or [I]; absence has three sentences;
no candle close anywhere; moneyness is against F* (the options' own forward), never the chain's spot.
"""
from __future__ import annotations

import bisect
import datetime
import math
import statistics as st

import ladder

# ---- thresholds. (h) = hand-picked on the design days 22-28 Sep (6-amendment.md §3).
BK_MULT, PRIOR_N = 3, 5              # (h) bucket = 3 x the median 1-min volume, pooled over <= 5 prior sessions
ONE_SIDED = 0.5                      # (h) sure imbalance for a one-sided bucket
STALL_WIN, STALL_IN, STALL_OUT = 5, 2, 2   # (h) TIRING: 5-bucket window, 2 stalled closes in, 2 out
CONFIRM = 2                          # (h) a condition-born chip change, and a new named wall, stand 2 closes
OI_Z, OI_NOISE_N, STOP_N = 3.0, 15, 15     # 3 (h); 15 = fronts.SLOPE_MARKS (sigma window; STOPPED)
OI_MIN_N, OI_MIN_PCT = 3, 0.03       # (h) blueprint T4: the event also needs n >= 3 updates and a 3 % drop
ACCEPT_BK = 1                        # (h) acceptance = one bucket of lots beyond G
HELD_N = 2                           # (h) the held breach: 2 more closes and 2 x the median bucket duration
VPIN_WIN, VPIN_LEAD = 10, 2          # (h)
FWD_MS = 15 * 60000                  # (h) F*'s basis window
HOLE_MS = 30000                      # (h) order flow silent >= 30 s in hours = CAN'T CHECK
CHAIN_STALE_MS = 180000              # (h) chain older than 180 s blinds the OI row
PREM_STALE_MS = 60000                # (h) premium at G / A needs a chain <= 60 s old
EXPIRY_PM = "13:30:00"               # (h) the expiry-afternoon row
NEAR_ATM = 19                        # (h) strikes ranked for a wall: the 19 nearest F*
LADDER_TICK = 10.0                   # (h) h3/build.py's ladder tick, the one §4.9's fills were built with
SESSION_OPEN, SESSION_CLOSE = "09:15:00", "15:30:00"
THRESHOLDS = dict(BK_MULT=BK_MULT, PRIOR_N=PRIOR_N, ONE_SIDED=ONE_SIDED, STALL_WIN=STALL_WIN, STALL_IN=STALL_IN,
                  STALL_OUT=STALL_OUT, CONFIRM=CONFIRM, OI_Z=OI_Z, OI_NOISE_N=OI_NOISE_N, STOP_N=STOP_N,
                  OI_MIN_N=OI_MIN_N, OI_MIN_PCT=OI_MIN_PCT, ACCEPT_BK=ACCEPT_BK, HELD_N=HELD_N, VPIN_WIN=VPIN_WIN,
                  VPIN_LEAD=VPIN_LEAD, FWD_MS=FWD_MS, HOLE_MS=HOLE_MS, CHAIN_STALE_MS=CHAIN_STALE_MS,
                  PREM_STALE_MS=PREM_STALE_MS, EXPIRY_PM=EXPIRY_PM, NEAR_ATM=NEAR_ATM, LADDER_TICK=LADDER_TICK)
REV = "6"
CC = "could not check"
WHO = {1: "buyers", -1: "sellers"}
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
sgn = lambda x: (x > 0) - (x < 0)   # noqa: E731


def ms(day, s):
    """'HH:MM[:SS]' on `day` (IST) -> epoch ms."""
    y, m, d = map(int, day.split("-"))
    h, mi, *x = map(int, s.split(":"))
    return int(datetime.datetime(y, m, d, h, mi, x[0] if x else 0, tzinfo=IST).timestamp() * 1000)


hms = ladder.hms_ist


def hm(t):
    return hms(t)[:5]


def _L(x):
    return f"{x / 1e5:.1f}L"


def session_from_book(rows, lot=65, idx="", day=""):
    """A session for `prior` from a day's book rows: the harness's h3/build.py. Pure; the caller reads the file."""
    lad = ladder.Ladder(lot=lot, tick=LADDER_TICK, interval_s=60, idx=idx, day=day)
    bars, fills = [], []
    for r in rows:
        c, f = lad.step(r)
        if c and c["h"] is not None:
            bars.append(c)
        fills += f
    return {"bars": bars, "fills": fills}


def _vp(fs, binw=5.0):
    m = {}
    for f in fs:
        k = round(f["p"] / binw) * binw
        m[k] = m.get(k, 0) + f["q"]
    return m


def _va(m, frac=0.7):
    ks = sorted(m)
    poc = max(ks, key=lambda k: m[k])
    tot = sum(m.values())
    lo = hi = ks.index(poc)
    acc = m[poc]
    while acc < tot * frac and (lo > 0 or hi < len(ks) - 1):
        up = m[ks[hi + 1]] if hi < len(ks) - 1 else -1
        dn = m[ks[lo - 1]] if lo > 0 else -1
        if up >= dn:
            hi += 1
            acc += m[ks[hi]]
        else:
            lo -= 1
            acc += m[ks[lo]]
    return poc, ks[hi], ks[lo]


class _OIWatch:
    """One strike-side's OI from a reference start: the peak since, and the noise-sized off-peak EVENT (§4.5)."""

    def __init__(s, key, start):
        s.key, s.start, s.pk, s.pk_i, s.j, s.event = key, start, None, None, None, None

    def sigma(s, u, i):
        seg = u[max(0, i - OI_NOISE_N):i + 1]
        d = [abs(b[1] - a[1]) for a, b in zip(seg, seg[1:])]
        return 1.4826 * st.median(d) if d else 0

    def update(s, oiu, lot):
        u = oiu.get(s.key)
        out = []
        if not u:
            return out
        if s.pk is None:
            i0 = max(0, bisect.bisect_right([x[0] for x in u], s.start) - 1)
            s.pk, s.pk_i, s.j = u[i0][1], i0, i0
        while s.j < len(u) - 1:
            s.j += 1
            ut, oi = u[s.j]
            if oi > s.pk:
                if s.event:
                    out.append(("WITHDRAWN", ut, s.event))
                    s.event = None
                s.pk, s.pk_i = oi, s.j
            elif s.event is None:
                n = s.j - s.pk_i
                sig = max(s.sigma(u, s.pk_i), lot)
                drop = s.pk - oi
                z = drop / (sig * math.sqrt(n))
                # blueprint T4: n >= 3 updates and >= 3 % of the peak, on top of 3 sigma sqrt n
                if z >= OI_Z and n >= OI_MIN_N and drop >= OI_MIN_PCT * s.pk:
                    s.event = dict(t=ut, key=s.key, pk=s.pk, pk_t=u[s.pk_i][0], oi=oi, z=z, sig=sig, n=n, pct=100 * drop / s.pk)
                    out.append(("EVENT", ut, s.event))
        return out

    def state(s):
        if s.pk is None:
            return None
        if s.event:
            return "off"
        return "stopped" if s.j - s.pk_i >= STOP_N else "building"

    def peak_t(s, oiu):
        return oiu[s.key][s.pk_i][0] if s.pk is not None else None


class State:
    """One marked trade on one day: the market read and her position, fed rows in key order."""

    def __init__(self, trade, inputs):
        self.trade, self.day = trade, inputs["day"]
        self.idx, self.lot = inputs.get("idx", "NIFTY"), int(inputs.get("lot") or 65)
        if trade is None:                                             # the market alone (flat): nothing ever seeds
            self.k = self.ty = self.p0 = self.trade_id = self.exit_t = None
            self.own = self.d = 1
            self.dty, self.aty, self.entry_t = "PE", "CE", 1 << 62
        else:
            self.k, self.ty = int(trade["k"]), str(trade["ty"]).lower()
            buy = str(trade.get("side", "BUY")).upper() == "BUY"
            self.own = 1 if buy else -1                               # +1 long option, -1 short
            self.d = 1 if (self.ty == "ce") == buy else -1           # the way the trade wants the future
            self.dty, self.aty = ("CE", "PE") if self.d < 0 else ("PE", "CE")
            self.p0 = float(trade["p0"])
            e = trade["entry_t"]
            self.entry_t = ms(self.day, e) if isinstance(e, str) else int(e)
            x = trade.get("exit_t")
            self.exit_t = None if x is None else (ms(self.day, x) if isinstance(x, str) else int(x))
            self.trade_id = trade.get("trade_id") or f"{self.day}:{self.k}{self.ty.upper()}:{'B' if buy else 'S'}:{hms(self.entry_t)}"
        self.exit_view = None
        self.expiry_day = inputs.get("expiry") == self.day
        self.zone_text = inputs.get("zone")
        self.flat_watch = {}
        # ---- units (§4.2)
        prior = list(inputs.get("prior") or [])[-PRIOR_N:]
        pbars = [b for p in prior for b in p.get("bars") or [] if b.get("h") is not None]
        self.prior_n = len(prior)
        if pbars:
            self.PRIOR_B = st.median([b["h"] - b["l"] for b in pbars])
            self.BK = BK_MULT * st.median([b["vol"] for b in pbars])
            self.bk_src = f"{len(prior)} prior session(s)"
        else:
            self.PRIOR_B = self.BK = None                             # the day's own first 15 minutes, once seen
            self.bk_src = "no prior session on disk: the day's own first 15 minutes (not causal before 09:30)"
        self.PRIOR = []
        if prior:
            pb = [b for b in prior[-1].get("bars") or [] if b.get("h") is not None]
            pf = prior[-1].get("fills") or []
            if pb:
                self.PRIOR = [("prior high", max(b["h"] for b in pb)), ("prior low", min(b["l"] for b in pb)),
                              ("prior close", pb[-1]["c"])]
            if pf:
                poc, vah, val = _va(_vp(pf))
                self.PRIOR += [("prior POC", poc), ("prior VAH", vah), ("prior VAL", val)]
        self.lad = ladder.Ladder(lot=self.lot, tick=LADDER_TICK, interval_s=60, idx=self.idx, day=self.day)
        # ---- the market
        self.bars, self.ft, self.fp, self.flo, self.fhi, self.pre = [], [], [], [], [], []
        self.bk, self.cur, self.runs, self.marks = [], None, [], []
        self.basis, self.oiu, self.rc, self.rc_t, self.F, self.bas = [], {}, None, None, None, None
        self.basis_ix, self.bas_ix = [], None      # DISPLAY ONLY: future minus the index (her one basis, 2026-10-05)
        self.named, self.cand, self.wall_px = {"CE": None, "PE": None, "A": None}, {"CE": None, "PE": None, "A": None}, {}
        self.sess_lo = self.sess_hi = self.last_p = self.open_p = None
        self.volp, self.vp, self.gc = {}, [], []
        self.last_key = self.last_book_t = None
        self.holes, self.chain_since_book = [], 0
        # ---- her position (the harness's Fold)
        self.seeded = False
        self.G = self.G_src = self.G_t = None
        self.G_steps = []                   # output only: the give-up's staircase, one row per step (Trade tab)
        self.G_hit = False
        self.W = self.Ww = self.Aw = None
        self.entry_px = self.best_px = None
        self.etally, self.etally_t0, self.eacc = 0.0, None, None
        self.acc_n, self.held = 0, None
        self.epoch, self.acc, self.tally, self.tally_t0, self.oi_ev = 0, None, 0.0, None, None
        self.folded, self.folds = None, []
        self.newest_win = self.latest = self.failed = self.pend = None
        self.stall_n = self.prog_n = 0
        self.tiring, self.stall_t0 = False, None
        self.nfixed = 0
        self.shown = dict(ZONE=None, FLOW=None, OI=None, VPIN=None)
        self.why = dict(ZONE=None, FLOW=None, OI=None, VPIN=None)
        self.since = dict(ZONE=None, FLOW=None, OI=None, VPIN=None)
        self.pc, self.off_shown, self.vraw, self.tally_n = {}, False, None, 0
        self.zone_ids, self.zone_broken, self.zone_seen = set(), set(), 0
        self.first, self.prem_hist = {}, []
        self.prem_peak = self.prem_peak_t = None
        self.headline = self.clause = None
        self.events, self.seq, self._new = [], 0, 0

    # ---- units at a time
    def B_at(self, t):
        done = [b["h"] - b["l"] for b in self.bars if b["t"] + 60000 <= t]
        if len(done) >= 5:
            return st.median(done)
        return self.PRIOR_B

    def m_at(self):
        mv = [abs(x["dp"]) for x in self.bk]
        return st.median(mv) if len(mv) >= 5 else self.PRIOR_B / 2

    def med_bk_dur(self):
        ds = [x["t1"] - x["t0"] for x in self.bk]
        return st.median(ds) if len(ds) >= 5 else BK_MULT * 60000

    def cur_oi(self, key):
        u = self.oiu.get(key)
        return u[-1][1] if u else 0

    def in_hours(self, t):
        return SESSION_OPEN <= hms(t) <= SESSION_CLOSE

    def _emit(self, t, kind, text, **kw):
        """One event, placed once at (t, px) for the chart; px defaults to the last future print."""
        self.seq += 1
        kw.setdefault("px", self.last_p)
        e = dict(seq=self.seq, t=t, ts=hms(t), kind=kind, text=text, epoch=self.epoch,
                 after_exit=bool(self.exit_t is not None and t > self.exit_t), **kw)
        e["row"] = self._snap(t)
        self.events.append(e)
        return e

    # ---- feed
    def feed(self, book=(), chain=(), vpin=(), tape=()):
        for r in vpin or ():
            if r.get("day") == self.day and r.get("inst") == f"{self.idx}-FUT:fast" and not r.get("backfilled"):
                t1 = ms(self.day, r["at"])
                self.vp.append(dict(t0=self.vp[-1]["t1"] if self.vp else ms(self.day, SESSION_OPEN), t1=t1,
                                    buy=float(r["buy"]), sell=float(r["sell"])))
        self.gc.extend(tape or ())
        rows = [(r["t"], 1, r) for r in book or ()] + [(ms(self.day, r["ts"]), 0, r) for r in chain or ()]
        rows.sort(key=lambda x: (x[0], x[1]))
        for key, kind, r in rows:
            if self.exit_t is not None and self.exit_view is None and key > self.exit_t:
                self.exit_view = self._view_core(self.exit_t)         # frozen at her exit; the engine logs on
            if kind:
                self._book(r, key)
            else:
                self._chain(r, key)
            self.last_key = key
        return self

    def _book(self, r, t):
        if self.last_book_t is not None and t - self.last_book_t >= HOLE_MS and self.in_hours(t):
            self._hole(self.last_book_t, t)
        self.last_book_t, self.chain_since_book = t, 0
        closed, fills = self.lad.step(r)
        if closed and closed["h"] is not None:
            self._bar(closed)
        for f in fills:
            self._fill(f)

    def _hole(self, t0, t1):
        why = f"order-flow feed silent {(t1 - t0) // 1000} s" if self.chain_since_book else "TapeMap was down, no rows recorded"
        self.holes.append((t0, t1, why))
        # §4.6: no tally and no OI event spans a hole
        self.tally, self.tally_t0, self.etally, self.etally_t0, self.acc_n = 0.0, None, 0.0, None, 0
        if self.Ww is not None:
            self.oi_ev = None
            self.Ww = _OIWatch(self.Ww.key, t1)
        if self.seeded:
            self._emit(t1, "hole", f"{CC} {hm(t0)}–{hm(t1)}: {why}", t0=t0, t1=t1)

    def _bar(self, bar):
        self.bars.append(bar)
        if self.BK is None and len(self.bars) >= 15:
            fb = self.bars[:15]
            self.PRIOR_B = st.median([b["h"] - b["l"] for b in fb])
            self.BK = BK_MULT * st.median([b["vol"] for b in fb])
            pre, self.pre = self.pre, []
            for f, t in pre:                       # the harness bucketed these with this BK (flagged, not causal)
                self._bucketed(f, t)
        T = bar["t"] + 60000
        v = sum(r["b"] + r["s"] + r["u"] for r in bar["ladder"])
        vw = sum(r["p"] * (r["b"] + r["s"] + r["u"]) for r in bar["ladder"]) / v if v else bar["c"]
        B = self.B_at(T)
        if B is None:
            return
        th = 2 * B
        for r in self.runs:
            if "fixed_t" not in r or r["fixed_t"] > T or r["disp"] or r["src"] != "book":
                continue
            if r["trap"] is None and r["side"] * (r["vw"] - vw) >= th:
                r["trap"], r["trap_t"] = "trapped", T
                self._mark(T, "trapped", r["vw"], r["side"], "book", r["lots"], f"{r['lots']:.0f} lots of {WHO[r['side']]} trapped at {r['vw']:.0f}")
            elif r["trap"] == "trapped" and r["trap_t"] < T and (bar["h"] >= r["vw"] if r["side"] > 0 else bar["l"] <= r["vw"]):
                r["trap"] = "released"
                self._mark(T, "released", r["vw"], r["side"], "book", r["lots"], f"{WHO[r['side']]} at {r['vw']:.0f} released")

    def _mark(self, t, kind, px, side, by, lots, text, **kw):
        """A chart mark, placed once: kept for the day (the flat read) and, after her mark, an event too."""
        m = dict(kind=kind, t=t, ts=hms(t), px=round(px, 1), side=side, by=by, lots=None if lots is None else round(lots), text=text, **kw)
        self.marks.append(m)
        if self.seeded:
            self._emit(t, kind, text, px=m["px"], side=side, by=by, lots=m["lots"], **kw)

    def _fill(self, f):
        t, p = f["ltt"], f["p"]
        if self.ft and t < self.ft[-1]:
            t = self.ft[-1]
        self.last_p = p
        if self.open_p is None:
            self.open_p = p
        self.sess_lo = p if self.sess_lo is None else min(self.sess_lo, p)
        self.sess_hi = p if self.sess_hi is None else max(self.sess_hi, p)
        self.ft.append(t)
        self.fp.append(p)
        self.flo.append(min(self.flo[-1], p) if self.flo else p)
        self.fhi.append(max(self.fhi[-1], p) if self.fhi else p)
        k = round(p / 5) * 5
        self.volp[k] = self.volp.get(k, 0) + f["q"] / self.lot
        if self.BK is None:
            self.pre.append((f, t))
            return
        self._bucketed(f, t)

    def _bucketed(self, f, t):
        p, q, closed = f["p"], f["q"] / self.lot, []
        while q > 1e-9:
            c = self.cur
            if c is None:
                c = self.cur = dict(t0=t, b=0, s=0, gh=0, u=0, v=0, pv=0, p0=p, p1=p, hi=p, lo=p)
            take = min(q, self.BK - c["v"])
            if f["hidden"]:
                c["gh"] += take
            elif f["side"] == 0:
                c["u"] += take
            elif f["side"] > 0:
                c["b"] += take
            else:
                c["s"] += take
            c["v"] += take
            c["pv"] += p * take
            c["p1"] = p
            c["hi"], c["lo"] = max(c["hi"], p), min(c["lo"], p)
            q -= take
            if c["v"] >= self.BK - 1e-9:
                closed.append(self._close_bucket(c, t))
                self.cur = None
        fixed = [r for r in self.runs if "fixed_t" in r]
        if t >= self.entry_t:
            if not self.seeded:
                self._seed(t)
                self.nfixed = len(fixed)
            for r in fixed[self.nfixed:]:
                self._on_run(r, t)
            self.nfixed = len(fixed)
            for x in closed:
                self._on_bucket(x, t)
            self._on_fill(f, t)
            self._refresh(t, close=bool(closed), biz=closed[-1]["vw"] if closed else None)
            for x in closed:
                self._emit(t, "bucket", f"bucket closed {hms(x['t0'])}–{hms(x['t1'])} at {x['vw']:.1f}", vw=x["vw"])
        else:
            self.nfixed = len(fixed)

    def ext_before(self, t, d):
        i = bisect.bisect_left(self.ft, t) - 1
        return None if i < 0 else (self.flo[i] if d < 0 else self.fhi[i])

    # ---- buckets, fights (R0 / R1)
    def _vpin_net(self, t0, t1, now):
        b = s = 0.0
        for r in self.vp:
            if r["t1"] > now or r["t1"] < t0 or r["t0"] > t1:
                continue
            dur = max(1, r["t1"] - r["t0"])
            ov = max(0, min(t1, r["t1"]) - max(t0, r["t0"]))
            if ov == 0 and not (t0 <= r["t1"] <= t1):
                continue
            fr = (ov / dur) or 1.0
            b += fr * r["buy"] / self.lot
            s += fr * r["sell"] / self.lot
        return b, s

    def _gc_net(self, t0, t1, pmin, pmax, now):
        b = s = 0.0
        for r in self.gc:
            if r["t"] + 300000 <= t0 or r["t"] > t1 or r["t"] + 300000 > now:
                continue
            for x in r.get("ladder") or []:
                if pmin - 1 <= x["p"] <= pmax + 1:
                    b += x["b"]
                    s += x["s"]
        return b, s

    def _disputes(self, side, t0, t1, pmin, pmax, now):
        out = []
        for name, (b, s) in (("VPIN tape", self._vpin_net(t0, t1, now)), ("GoCharting", self._gc_net(t0, t1, pmin, pmax, now))):
            if b + s and sgn(b - s) == -side and abs(b - s) / (b + s) >= ONE_SIDED:
                out.append(f"{name} {b:.0f} v {s:.0f}")
        return out

    def _fix_run(self, r, t):
        m = self.m_at()
        wv = r["side"] * (r["p1"] - r["p0"])
        r["res"] = "INITIATIVE" if wv >= m else "ABSORBED" if wv <= 0 else "PRESSING"
        r["fixed_t"], r["m"] = t, m
        r["disp"] = self._disputes(r["side"], r["t0"], r["t1"], r["pmin"], r["pmax"], t) if r["src"] == "book" else []
        dp = r["p1"] - r["p0"]
        if r["src"] == "price":
            r["winner"], r["how"] = r["side"], "by price [I]"
        elif r["disp"]:
            r["winner"] = sgn(dp) if abs(dp) >= m else None
            r["how"] = "disputed; " + ("by price [I]" if r["winner"] else "no result")
        else:
            r["winner"], r["how"] = (r["side"] if r["res"] != "ABSORBED" else -r["side"]), "book [I]"
        if r["winner"] is None:
            kind, side, by, text = "disputed", r["side"], "book", f"a disputed fight at {r['vw']:.0f} {hm(r['t1'])}: {'; '.join(r['disp'])}"
        elif r["src"] == "price":
            kind, side, by, text = "won", r["winner"], "price", f"{WHO[r['winner']]} won at {r['vw']:.0f} {hm(r['t1'])} by price"
        elif r["res"] == "ABSORBED":
            kind, side, by, text = "absorbed", r["side"], "book", f"{r['lots']:.0f} lots of {WHO[r['side']]} absorbed at {r['vw']:.0f} {hm(r['t1'])}"
        else:
            kind, side, by = "won", r["winner"], ("price" if r["disp"] else "book")
            text = f"{WHO[r['winner']]} won at {r['vw']:.0f} {hm(r['t1'])}, {r['lots']:.0f} lots {r['res'].lower()}"
        self._mark(t, kind, r["vw"], side, by, r["lots"], text, t0=r["t0"], t1=r["t1"], disputed=bool(r["disp"]))

    def _close_bucket(self, c, t):
        b, s, gh, u, v = c["b"], c["s"], c["gh"], c["u"], c["v"]
        G = gh + u
        dp = c["p1"] - c["p0"]
        if b + s and abs(b - s) / (b + s) >= ONE_SIDED and abs(b - s) > G:
            side, src = sgn(b - s), "book"
        elif (abs(b - s) + G) / v < ONE_SIDED:
            side, src = 0, "two-sided"
        elif abs(dp) >= 2 * self.B_at(t):
            side, src = sgn(dp), "price"
        else:
            side, src = 0, "unproven"
        x = dict(t0=c["t0"], t1=t, b=b, s=s, g=G, side=side, src=src, dp=dp, p0=c["p0"], p1=c["p1"], hi=c["hi"], lo=c["lo"], vw=c["pv"] / v, v=v)
        self.bk.append(x)
        prev = self.bk[-2] if len(self.bk) > 1 else None
        open_run = self.runs[-1] if self.runs and "fixed_t" not in self.runs[-1] else None
        if open_run and not (side and prev and prev["side"] == side and open_run["t1"] == prev["t1"] and open_run["src"] == src):
            self._fix_run(open_run, t)
            open_run = None
        if side:
            lots, opp = (max(b, s), min(b, s)) if src == "book" else (v, 0)
            if open_run:
                r = open_run
                r["lots"] += lots
                r["opp"] += opp
                r["g"] += G
                r["pv"] += x["vw"] * v
                r["v"] += v
                r["p1"], r["t1"], r["n"] = x["p1"], t, r["n"] + 1
                r["pmin"], r["pmax"] = min(r["pmin"], x["lo"]), max(r["pmax"], x["hi"])
                r["vw"] = r["pv"] / r["v"]
            else:
                self.runs.append(dict(side=side, src=src, t0=x["t0"], t1=t, lots=lots, opp=opp, g=G, pv=x["vw"] * v, v=v,
                                      vw=x["vw"], p0=x["p0"], p1=x["p1"], n=1, pmin=x["lo"], pmax=x["hi"], trap=None))
        return x

    # ---- levels (R2), the one wall ranking (§4.4)
    def levels(self, t):
        """(px, priority, name, side, k, ty): the name is her sentence for it -- points, lots, hh:mm, no symbols."""
        lv = [(p, 5, "yesterday's " + n.split()[1], 0, None, None) for n, p in self.PRIOR]
        if self.open_p is not None:
            lv.append((self.open_p, 6, "the open", 0, None, None))
        if self.sess_hi is not None:
            lv += [(self.sess_hi, 6, "the day high", 0, None, None), (self.sess_lo, 6, "the day low", 0, None, None)]
        if self.volp:
            lv.append((max(self.volp, key=lambda k: self.volp[k]), 7, "today's value", 0, None, None))
        for r in self.runs:
            if "fixed_t" not in r or r["fixed_t"] > t:
                continue
            when = hm(r["t1"])
            if r["trap"] == "trapped":
                lv.append((r["vw"], 1, f"{r['lots']:.0f} lots of {WHO[r['side']]} trapped at {when}", -r["side"], None, None))
            elif r["winner"] and r["res"] == "ABSORBED" and not r["disp"]:
                lv.append((r["vw"], 2, f"{r['lots']:.0f} lots of {WHO[-r['side']]} held at {when}", -r["side"], None, None))
            elif r["winner"] is None:
                lv.append((r["vw"], 3, f"a disputed fight at {when}", 0, None, None))
            elif r["winner"]:
                lv.append((r["vw"], 3, f"{WHO[r['winner']]} won {r['lots']:.0f} lots at {when}", r["winner"], None, None))
        for ty, sd in (("CE", -1), ("PE", 1)):
            k = self.named[ty]
            if k:
                lv.append((self.wall_px[ty], 4, f"{k} {ty} writers {_L(self.cur_oi((k, ty)))}", sd, k, ty))
        return lv

    def _px(self, k):
        """Where strike k is DRAWN and PRINTED on her futures chart: K + her basis (future minus the index), the forward's
        until the index basis exists. Output only; the engine's own wall_px / G stay on the forward basis."""
        b = self.bas_ix if self.bas_ix is not None else self.bas
        return None if k is None or b is None else round(k + b)

    def _lvpx(self, x):
        """A levels() tuple's printed price: a named wall at its drawn price, any other level at its own futures price."""
        return self._px(x[4]) if x[1] == 4 and x[4] is not None and self._px(x[4]) is not None else round(x[0])

    def _rank(self, ty, sd, F, w, beyond=None):
        """blueprint §4.4: current OI (not day-high), near-ATM, beyond F* by w; the nearer of the top two."""
        near = sorted((x["k"] for x in self.rc["strikes"]), key=lambda k: abs(k - F))[:NEAR_ATM]
        el = [k for k in near if sd * (k - F) > w and (beyond is None or beyond(k))]
        top = sorted(el, key=lambda k: -self.cur_oi((k, ty)))[:2]
        return min(top, key=lambda k: abs(k - F)) if top else None

    def _name(self, key, c, sd, F, w):
        """A new choice must stand CONFIRM bucket closes, or F* must be w through the old wall."""
        cur, nb = self.named[key], len(self.bk)
        if c == cur:
            self.cand[key] = None
            return False
        if self.cand[key] is None or self.cand[key][0] != c:
            self.cand[key] = (c, nb)
        if cur is None or sd * (cur - F) <= -w or nb - self.cand[key][1] >= CONFIRM:
            self.named[key], self.cand[key] = c, None
            return True
        return False

    def _chain(self, r, t):
        self.chain_since_book += 1
        if self.last_p is None:
            return
        f = self.last_p
        fw = [x["k"] + x["ce"]["ltp"] - x["pe"]["ltp"] for x in r["strikes"]
              if abs(x["ce"].get("delta") or 0) > 0.3 and abs(x["pe"].get("delta") or 0) > 0.3 and x["ce"]["ltp"] and x["pe"]["ltp"]]
        if fw:
            self.basis.append((t, f - st.median(fw)))
        self.basis = [x for x in self.basis if x[0] >= t - FWD_MS]
        # Her basis (2026-10-05): future minus the INDEX, the row's own spot paired with the same future, a 15-min median like
        # the forward's (a raw fut - spot swung 8-12 pts a minute, CHECK M1). It places and labels; it decides nothing --
        # G, the walls' ZONE reads and every premium stay on the forward basis above (the signed rule's).
        if r.get("spot"):
            self.basis_ix.append((t, f - r["spot"]))
        self.basis_ix = [x for x in self.basis_ix if x[0] >= t - FWD_MS]
        self.bas_ix = st.median([x[1] for x in self.basis_ix]) if self.basis_ix else None
        if not self.basis:
            return
        self.bas = st.median([x[1] for x in self.basis])
        self.F, self.rc, self.rc_t = f - self.bas, r, t
        for x in r["strikes"]:
            for ty in ("ce", "pe"):
                oi = x[ty].get("oi") or 0
                if oi <= 0:
                    continue
                u = self.oiu.setdefault((x["k"], ty.upper()), [])
                if not u or u[-1][1] != oi:
                    u.append((t, oi))
        if t >= self.entry_t:
            pn = self.prem_now()
            if pn is not None:
                self.prem_hist.append((t, pn))
                if self.prem_peak is None or self.own * (pn - self.prem_peak) > 0:
                    self.prem_peak, self.prem_peak_t = pn, t
        B = self.B_at(t)
        if B is None:
            return
        w = B / 2
        for ty, sd in (("CE", 1), ("PE", -1)):
            c = self._rank(ty, sd, self.F, w)
            if c is not None and self._name(ty, c, sd, self.F, w):
                self.wall_px[ty] = round(c + self.bas)
                self.marks.append(dict(kind="wall", t=t, ts=hms(t), px=self.wall_px[ty], side=-sd, by="oi", lots=None, k=c, ty=ty,
                                       text=f"{c} {ty} writers {_L(self.cur_oi((c, ty)))} named at {self.wall_px[ty]}"))
            k = self.named[ty]
            if k is not None:                                         # the flat read's watch on each named wall, from 09:15
                self.flat_watch.setdefault((k, ty), _OIWatch((k, ty), ms(self.day, SESSION_OPEN))).update(self.oiu, self.lot)
        if t >= self.entry_t:
            if not self.seeded:
                self._seed(t)
                self.nfixed = len([r for r in self.runs if "fixed_t" in r])
            self._on_chain(t)

    # ---- the give-up (§4.3)
    def _set_G(self, run, t):
        B, d = self.B_at(t), self.d
        th, w = 2 * B, B / 2
        g0 = run["vw"] - d * th
        mine = [x for x in self.levels(t) if x[3] == d and -w <= -d * (x[0] - g0) <= th]
        far = max(mine, key=lambda x: -d * x[0]) if mine else None
        g = round(g0 if far is None else -d * max(-d * g0, -d * (far[0] - d * w)))
        if self.G is not None and -d * (g - self.G) > 0:                 # blueprint T7: G never loosens, touched or not
            self._emit(t, "refused_loosen", f"give-up stays {self.G}: it never loosens (the new win would put it at {g})", refused=g)
            return False
        if g == self.G:
            return False
        src = f"{WHO[run['winner']]} won at {run['vw']:.0f} {hm(run['t1'])}" + (f", past {far[2]} ({far[0]:.0f})" if far else "")
        self.G, self.G_src, self.G_t = g, src, t
        return True

    def _fallback_G(self, t):
        sd, w = -self.d, self.B_at(t) / 2
        F, bas = self.F, self.bas
        ks = sorted([x["k"] for x in self.rc["strikes"] if sd * (x["k"] - F) > w], key=lambda k: sd * (k - F))[:2]
        if not ks:
            return False
        k0 = max(ks, key=lambda k: self.cur_oi((k, self.dty)))
        self.G, self.G_t = round(k0 + bas + sd * w), t
        self.G_src = f"{k0} {self.dty} writers {_L(self.cur_oi((k0, self.dty)))}, no win of yours yet"
        self.W = k0
        return True

    def _pick_W(self, t):
        if self.rc is None or self.G is None:
            return
        sd = -self.d
        F, bas = self.F, self.bas
        Gk = self.G - bas
        ks = sorted(x["k"] for x in self.rc["strikes"])
        cand = [k for k in ks if sd * (k - F) > 0 and sd * (k - Gk) <= 0]
        if not cand:
            beyond = [k for k in ks if sd * (k - Gk) > 0]
            cand = [min(beyond, key=lambda k: sd * (k - Gk))] if beyond else []
        if not cand:
            return
        if self.W not in cand:
            self.W = max(cand, key=lambda k: self.cur_oi((k, self.dty)))
        self.Ww = _OIWatch((self.W, self.dty), t)
        self.Ww.update(self.oiu, self.lot)

    def _seed(self, t):
        self.seeded = True
        d, p = self.d, self.last_p
        w = self.B_at(t) / 2
        self.entry_px = self.best_px = p
        fx = [r for r in self.runs if "fixed_t" in r and r["fixed_t"] <= t and r["winner"]]
        nw = fx[-1] if fx else None
        self.newest_win, self.latest = nw, ("WIN" if nw else None)
        if nw and nw["winner"] == d:
            self._set_G(nw, t)
            if self.G is not None and -d * (p - self.G) > -w:
                self.G = None
        if self.G is None and self.rc is not None:
            self._fallback_G(t)
        self._pick_W(t)
        self._emit(t, "seed", (f"MARK {'long' if self.own > 0 else 'short'} {self.k} {self.ty.upper()} @ {self.p0}; fut {p}; "
                               + (f"give-up {self.G} ({self.G_src})" if self.G is not None else "no give-up yet")))

    def _new_epoch(self, t, why):
        self.epoch += 1
        if self.acc:
            self._emit(t, "withdrawn", f"flow give-up withdrawn: {why}")
        if self.oi_ev:
            self._emit(t, "oi_withdrawn", f"OI event withdrawn: {why}")
        self.acc, self.tally, self.tally_t0, self.oi_ev = None, 0.0, None, None
        self.acc_n, self.held, self.tally_n = 0, None, 0
        self._pick_W(t)

    def _on_run(self, r, t):
        if r["winner"] is None:
            return
        self.newest_win, self.latest = r, "WIN"
        if r["winner"] != self.d:
            return
        self.failed = None
        if self.acc is None:
            self.tally, self.tally_t0 = 0.0, None
        self.acc_n = 0                                                  # blueprint §4.5: the held breach needs no win by her side
        if self.G is None:
            if self._set_G(r, t):
                if -self.d * (self.last_p - self.G) > -self.B_at(t) / 2:
                    self.G = None
                    return
                self._pick_W(t)
                self._emit(t, "seed", f"give-up {self.G} ({self.G_src})")
        elif self._set_G(r, t):
            self._emit(t, "reset", f"give-up {'above' if self.d < 0 else 'below'} {self.G} ({self.G_src})")
            self._new_epoch(t, "your side won again and set a new give-up")

    def _trailed(self):
        return self.G is not None and self.entry_px is not None and self.d * (self.G - self.entry_px) > 0

    def _expiry_pm(self, t):
        return self.expiry_day and hms(t) >= EXPIRY_PM

    def _on_fill(self, f, t):
        if self.G is None:
            return
        d, p = self.d, f["p"]
        w = self.B_at(t) / 2
        q = f["q"] / self.lot
        if self._trailed() and self.eacc is None:
            E_ = self.entry_px - d * w
            xe = -d * (p - E_)
            if xe >= 0:
                if self.etally_t0 is None:
                    self.etally_t0, self.etally = t, 0.0
                self.etally += q
                if self.etally >= ACCEPT_BK * self.BK and t - self.etally_t0 >= self.med_bk_dur():
                    self.eacc = dict(t=t, px=E_)
                    self.first.setdefault("backstop", (t, self.prem_now()))
                    self._emit(t, "backstop", f"{self.etally:.0f} lots accepted back through your entry {E_:.0f}")
                    self._check_fold(t)
            elif xe <= -w:
                self.etally_t0, self.etally = None, 0.0
        x = -d * (p - self.G)
        if x >= 0:
            if not self.G_hit:
                self.G_hit = True
                self._emit(t, "touch", f"give-up {self.G} touched ({p})")
            if self.tally_t0 is None:
                self.tally_t0, self.tally = t, 0.0
                self.tally_n += 1
                if self.tally_n == 1:            # one row per epoch; restarts are counted on it, never a row each
                    self._emit(t, "tally", f"tally at {self.G} from {p}")
            self.tally += q
            if self.acc is None and self.tally >= ACCEPT_BK * self.BK and t - self.tally_t0 >= self.med_bk_dur():
                self.acc = dict(t=t, G=self.G, lots=self.tally, secs=(t - self.tally_t0) / 1000, t0=self.tally_t0, epoch=self.epoch)
                self.acc_n, self.held = 0, None
                self.first.setdefault("plain_accept", (t, self.prem_now()))
                self._emit(t, "accepted", f"{self.tally:.0f} lots accepted beyond {self.G} over {(t - self.tally_t0) / 1000:.0f} s")
                self._check_fold(t)
        elif x <= -w and self.tally_t0 is not None:
            if self.acc is not None and self.folded != self.epoch:
                self._emit(t, "withdrawn", f"flow give-up withdrawn: trading back {p} inside {self.G} by w")
                self.acc, self.acc_n, self.held = None, 0, None
            if self.acc is None:
                self.tally_t0, self.tally = None, 0.0

    def _on_chain(self, t):
        if self.G is None and self.rc is not None and self._fallback_G(t):     # §4.6: the first wall read sets it
            self._pick_W(t)
            self._emit(t, "seed", f"give-up {self.G} ({self.G_src})")
        d, w = self.d, self.B_at(t) / 2
        a = self._rank(self.aty, d, self.F, w, beyond=lambda k: d * (k + self.bas - self.entry_px) > w)
        if self._name("A", a, d, self.F, w):
            self.Aw = _OIWatch((a, self.aty), t) if a is not None else None
        if self.Aw:
            self.Aw.update(self.oiu, self.lot)
        if self.Ww is None:
            if self.G is not None:
                self._pick_W(t)
            self._refresh(t, close=False)
            return
        for kind, ut, e in self.Ww.update(self.oiu, self.lot):
            if kind == "EVENT":
                self.oi_ev = e
                self._emit(ut, "oi_event", f"{self.W} {self.dty} writers left {hm(ut)}: {_L(e['pk'])} -> {_L(e['oi'])} "
                           f"(-{e['pct']:.1f} %, z {e['z']:.1f}, {e['n']} updates, sigma {_L(e['sig'])}/update)",
                           z=round(e["z"], 2), n=e["n"], pct=round(e["pct"], 2), sigma=e["sig"], peak=e["pk"], oi=e["oi"])
                self._check_fold(ut)
            else:
                self.oi_ev = None
                self._emit(ut, "oi_withdrawn", f"OI event withdrawn: {self.W} {self.dty} rebuilt above {_L(e['pk'])}")
        self._refresh(t, close=False)

    def oi_blind(self, t):
        return self.rc_t is None or t - self.rc_t > CHAIN_STALE_MS

    def _check_fold(self, t):
        fl, oi = self.acc is not None, self.oi_ev is not None and not self.oi_blind(t)
        hl = self.held is not None and self.acc is not None
        if fl and oi:
            self.first.setdefault("flow_oi", (t, self.prem_now()))
        if hl:
            self.first.setdefault("held", (t, self.prem_now()))
        if self._trailed():
            why = ("flow_oi" if fl and oi else "held" if hl else "expiry" if fl and self._expiry_pm(t) else
                   "backstop" if self.eacc else None)
        else:
            why = "accept" if fl else "backstop" if self.eacc else None
        if why is None or self.folded == self.epoch:
            return
        self.folded = self.epoch
        G, W = self.G, self.W
        text = {"accept": f"FOLD · {G} accepted",
                "flow_oi": f"FOLD · {W} {self.dty} writers gave up {hm(self.oi_ev['t']) if self.oi_ev else '?'}, {G} accepted",
                "held": f"FOLD · {G} accepted and held {HELD_N} buckets",
                "backstop": f"FOLD · back through your entry {self.eacc['px']:.0f}" if self.eacc else "FOLD",
                "expiry": f"FOLD · expiry afternoon: {G} accepted"}[why]
        sid = f"{self.trade_id}:{self.epoch}"
        self.folds.append(dict(t=t, why=why, text=text, sound_id=sid, epoch=self.epoch, prem=self.prem_now()))
        self._emit(t, "fold", f"{text} · {hm(t)}", why=why, sound_id=sid, px=self.last_p,
                   bucket_px=round(self.bk[-1]["vw"], 1) if self.bk else None, bucket_t=self.bk[-1]["t1"] if self.bk else None)

    def _on_bucket(self, x, t):
        d, w, bk = self.d, self.B_at(t) / 2, self.bk
        i = len(bk) - 1
        if self.acc is not None:
            self.acc_n += 1
            if self.held is None and self.acc_n >= HELD_N and t - self.acc["t"] >= HELD_N * self.med_bk_dur():
                self.held = dict(t=t)
                self._emit(t, "held", f"acceptance beyond {self.G} stood {HELD_N} bucket closes")
                self._check_fold(t)
        else:
            self.acc_n, self.held = 0, None
        if i >= STALL_WIN:
            t_win = bk[i - STALL_WIN + 1]["t0"]
            ref = self.ext_before(t_win, d)
            ins = [y["lo"] if d < 0 else y["hi"] for y in bk[i - STALL_WIN + 1:i + 1]]
            ext = min(ins) if d < 0 else max(ins)
            prog = ref is not None and d * (ext - ref) >= w
            won = any(r["winner"] == d and r["t1"] >= t_win for r in self.runs if "fixed_t" in r)
            if not prog and not won:
                self.stall_n, self.prog_n = self.stall_n + 1, 0
                self.stall_t0 = self.stall_t0 or x["t0"]
                if self.stall_n >= STALL_IN and not self.tiring:
                    self.tiring = True
            else:
                self.prog_n, self.stall_n = self.prog_n + 1, 0
                if self.tiring and self.prog_n >= STALL_OUT:
                    self.tiring = False
                if not self.tiring:
                    self.stall_t0 = None
        newx = x["lo"] if d < 0 else x["hi"]
        pend = self.pend
        if pend is None:
            old = self.ext_before(x["t0"], d)
            if old is not None and d * (newx - old) > 0 and x["t0"] > self.entry_t:
                self.pend = pend = dict(old=old, new=newx, i=i, mine=x["side"] == d)
        elif d * (newx - pend["new"]) > 0:
            pend.update(new=newx, i=i)
            pend["mine"] |= x["side"] == d
        if pend:
            if not pend["mine"] and d * (pend["new"] - pend["old"]) >= w and -d * (x["p1"] - pend["old"]) >= w and i <= pend["i"] + 1:
                self.failed, self.latest, self.pend = (x["t1"], pend["new"], pend["old"]), "FAILED", None
                self._emit(x["t1"], "failed", f"failed {'low' if d < 0 else 'high'} at {pend['new']:.0f} {hm(x['t1'])}, back to {x['p1']:.0f}",
                           px=round(pend["new"], 1), side=d, by="price", lots=None)
            elif i > pend["i"] + 1:
                if self.failed and d * (pend["new"] - self.failed[1]) > 0:
                    self.failed = None
                self.pend = None
        if self.entry_px is not None:
            ext = x["lo"] if d < 0 else x["hi"]
            if d * ext > d * self.best_px:
                self.best_px = ext
            # blueprint T2: expiry afternoon, trailed -- G steps to the best future since entry less theta, tighten only
            if self._expiry_pm(t) and self._trailed():
                g = round(self.best_px - d * 2 * self.B_at(t))
                if -d * (g - self.G) < 0:
                    self.G, self.G_t = g, t
                    self.G_src = f"expiry afternoon: a swing from the best {self.best_px:.0f}"
                    self._emit(t, "expiry_trail", f"give-up tightened to {self.G} ({self.G_src})")
                    self._new_epoch(t, "give-up tightened")

    # ---- words, chips (§4.7, §4.8)
    def prem_now(self):
        if self.rc is None:
            return None
        x = next((x for x in self.rc["strikes"] if x["k"] == self.k), None)
        return x[self.ty]["ltp"] if x else None

    def _tape_word(self, t):
        d = self.d
        if self.latest == "FAILED" and self.failed:
            return "FAILED", f"failed {'low' if d < 0 else 'high'} {hm(self.failed[0])}"
        nw = self.newest_win
        if nw and nw["winner"] != d:
            return "PULLBACK", ("pullback inside your give-up: time still yours" if self.own < 0 else f"pullback since {hm(nw['t1'])}")
        if self.tiring and self.stall_t0:
            return "TIRING", ("stalled: time is working for you" if self.own < 0 else f"tiring {max(0, (t - self.stall_t0) // 60000)} min")
        if nw:
            return "BEHIND", ("behind you: the move away from your strike" if self.own < 0 else f"{WHO[d]} won {hm(nw['t1'])} at {nw['vw']:.0f}")
        return None, None

    def _raw_chips(self, t, biz, close):
        d, w, out = self.d, self.B_at(t) / 2, {}
        # ZONE: event-born (blueprint §4.8) -- re-read only when a level is born, broken by w, or taken by a fixed fight
        if close:
            strong = [x for x in self.levels(t) if x[1] in (1, 2, 4, 5)]
            ids = {(x[2], round(x[0], 1)) for x in strong}
            ev = ids - self.zone_ids
            for x in strong:
                key = (x[2], round(x[0], 1))
                if key not in self.zone_broken and x[3] and (biz - x[0]) * x[3] <= -w:
                    self.zone_broken.add(key)
                    ev.add(key)
            fixed = [r for r in self.runs if "fixed_t" in r]
            for r in fixed[self.zone_seen:]:
                if any(abs(r["vw"] - x[0]) <= w for x in strong):
                    ev.add(("fight", round(r["vw"], 1)))
            self.zone_seen, self.zone_ids = len(fixed), ids
            if ev or self.shown["ZONE"] is None:
                # "at" a level: within w, on the side against her, and not one business already broke
                at = next((x for x in sorted(strong, key=lambda x: abs(x[0] - biz))
                           if abs(biz - x[0]) <= w and x[3] == -d and (x[2], round(x[0], 1)) not in self.zone_broken), None)
                beh = sorted([x for x in strong if -d * (x[0] - biz) > -w], key=lambda x: -d * (x[0] - biz))
                if not strong:
                    out["ZONE"] = ("CAN'T CHECK", f"{CC}: no levels yet")
                elif at:
                    out["ZONE"] = ("AGAINST", f"at {self._lvpx(at)}: {at[2]}")
                elif beh and beh[0][3] == d:
                    out["ZONE"] = ("WITH", f"behind you: {self._lvpx(beh[0])} ({beh[0][2]})")
                else:
                    out["ZONE"] = ("QUIET", f"no level born or broken since {hm(t)}")
        # FLOW: the newest fixed fight within 10 buckets, plus the tape word; event-born, no gate
        word, wtxt = self._tape_word(t)
        fixed = [r for r in self.runs if "fixed_t" in r and r["fixed_t"] <= t]
        last = fixed[-1] if fixed else None
        recent = [x for x in self.bk if x["t1"] <= t][-VPIN_WIN:]
        fresh = last is not None and recent and last["t1"] >= recent[0]["t0"]
        if self.acc is not None:
            fc, parts = "AGAINST", [f"accepted past {self.G} {hm(self.acc['t'])}"]
        elif word == "FAILED":
            fc, parts = "AGAINST", []
        elif fresh and last["winner"] is None:
            fc, parts = "CAN'T CHECK", [f"{CC}: newest fight disputed {hm(last['t1'])}"]
        elif fresh and last["winner"] == -d:
            fc, parts = "AGAINST", [f"{WHO[-d]} won {hm(last['t1'])} at {last['vw']:.0f}"]
        elif fresh and last["winner"] == d:
            fc, parts = "WITH", [f"{WHO[d]} won {hm(last['t1'])} at {last['vw']:.0f}"]
        else:
            fc, parts = "QUIET", [f"no fight in the last {len(recent)} buckets"]
        if wtxt and not (word == "BEHIND" and fresh and self.own > 0):
            parts.append(wtxt)
        out["FLOW"] = (fc, " · ".join(parts))
        # OI: W's watch (§4.8); a stale chain blinds the row (§4.6)
        if self.oi_blind(t):
            age = None if self.rc_t is None else (t - self.rc_t) // 1000
            out["OI"] = ("CAN'T CHECK", f"{CC}: chain from 09:17" if age is None else f"{CC}: chain {age // 60} min old")
        elif self.Ww is None or self.Ww.state() is None:
            out["OI"] = ("CAN'T CHECK", f"{CC}: no wall behind you read yet")
        else:
            a, oi = self.Ww.state(), self.cur_oi(self.Ww.key)
            if a == "off":
                e = self.oi_ev or self.Ww.event
                out["OI"] = ("AGAINST", f"{self.W} {self.dty} writers left {hm(e['t'])} (-{e['pct']:.1f} %): {_L(e['pk'])} to {_L(e['oi'])} [M]")
            elif a == "building":
                out["OI"] = ("WITH", f"{self.W} {self.dty} {_L(oi)}, writers adding (high {_L(self.Ww.pk)} {hm(self.Ww.peak_t(self.oiu))}) [M]")
            else:
                out["OI"] = ("QUIET", f"{self.W} {self.dty} {_L(oi)}, writers stopped adding (quiet) [M]")
        # VPIN: 10 buckets, in at lead >= 2, out only after 2 closes past zero (the raw state keeps its lead)
        vb = [r for r in self.vp if r["t1"] <= t][-VPIN_WIN:]
        one = [sgn(r["buy"] - r["sell"]) for r in vb if (r["buy"] + r["sell"]) and abs(r["buy"] - r["sell"]) / (r["buy"] + r["sell"]) >= ONE_SIDED]
        nw_, na = sum(1 for x in one if x == d), sum(1 for x in one if x == -d)
        net = nw_ - na
        if len(vb) < VPIN_WIN:
            v = ("CAN'T CHECK", f"{CC}: {len(vb)} of {VPIN_WIN} VPIN buckets")
        elif net >= VPIN_LEAD or (self.vraw == "WITH" and net > 0):
            v = ("WITH", f"{nw_} of {len(vb)} buckets one-sided, your way")
        elif net <= -VPIN_LEAD or (self.vraw == "AGAINST" and net < 0):
            v = ("AGAINST", f"{na} of {len(vb)} buckets one-sided, against you")
        else:
            v = ("QUIET", f"{len(one)} of {len(vb)} buckets one-sided, no lead")
        self.vraw = v[0]
        out["VPIN"] = v
        return out

    def _refresh(self, t, close, biz=None):
        raw = self._raw_chips(t, biz if biz is not None else self.last_p, close)
        for c, (v, why) in raw.items():
            off_now = c == "OI" and v in ("AGAINST", "CAN'T CHECK")
            immediate = c in ("FLOW", "ZONE") or (c == "OI" and off_now != self.off_shown) or self.shown[c] is None
            if v == self.shown[c]:
                self.why[c] = why
                self.pc.pop(c, None)
                continue
            if not immediate:
                if not close:
                    continue
                n = self.pc.get(c, (v, 0))
                n = (v, n[1] + 1) if n[0] == v else (v, 1)
                self.pc[c] = n
                if n[1] < CONFIRM:
                    continue
            old = self.shown[c]
            self.shown[c], self.why[c], self.since[c] = v, why, t
            self.pc.pop(c, None)
            if c == "OI":
                self.off_shown = off_now
            if old is not None:
                self._emit(t, "chip", f"{c} {old} -> {v}: {why}", chip=c, old=old, new=v)
        h, cl = self._headline(t)
        if (h, cl) != (self.headline, self.clause):
            was = self.headline
            self.headline, self.clause = h, cl
            if was is not None and not h.startswith("FOLD"):
                kind = "cant_check" if h.startswith("CAN'T CHECK") else "past_give_up" if h.startswith("PAST") else "clause"
                self._emit(t, kind, f"{h} · {cl}" if cl else h)

    def _live_words(self, t):
        """The four-reads clause (§4.7): against you first, then behind you; never a count."""
        name = dict(ZONE="zone", FLOW="flow", OI="OI", VPIN="VPIN")
        against = [name[c] + (f" since {hm(self.since[c])}" if self.since[c] and self.since[c] > self.entry_t else "")
                   for c in ("ZONE", "FLOW", "OI", "VPIN") if self.shown[c] == "AGAINST"]
        behind = [name[c] for c in ("ZONE", "FLOW", "OI", "VPIN") if self.shown[c] == "WITH"]
        parts = []
        if against:
            parts.append("against you: " + ", ".join(against))
        if behind:
            parts.append("behind you: " + ", ".join(behind))
        return " · ".join(parts) if parts else "nothing behind you now, nothing against you"

    def _headline(self, t, live=False):
        if self.folds and not live:
            f = self.folds[-1]
            return f"{f['text']} · {hm(f['t'])}", None
        if self.last_book_t is not None and t - self.last_book_t >= HOLE_MS and self.in_hours(t):
            return f"CAN'T CHECK since {hm(self.last_book_t)}", f"order-flow feed silent {(t - self.last_book_t) // 1000} s"
        if self.G is None:
            return "CAN'T CHECK", "no give-up yet: no fight her way, " + ("chain from 09:17" if self.rc is None else "no wall read")
        if self.acc is not None and self._trailed():
            return "PAST GIVE-UP", self._pgu_count()
        return "HOLD", self._live_words(t)

    def _pgu_count(self):
        return (f"{self.acc['G']} accepted {hm(self.acc['t'])} · {self.acc_n} of {HELD_N} buckets · "
                f"{self.W} {self.dty} writers {'leaving' if self.oi_ev else 'holding'}")

    def _line2(self, t):
        if self.G is None:
            return "a give-up is set at the first fight her way or the first wall read"
        if self.folds:
            h, cl = self._headline(t, live=True)
            return "still marked · now: " + (f"{h} · {cl}" if cl else h)
        d, G, W = self.d, self.G, self.W
        wr = f"{W} {self.dty} writers" if W else "the wall behind you"
        if not self._trailed():
            s = f"out if {G} is accepted"
        elif self.acc is not None:
            s = self._pgu_count()
        elif self._expiry_pm(t):
            s = f"expiry: your give-up follows your best · out if {G} is accepted"
        elif self.oi_ev is not None:
            s = f"{wr} left {hm(self.oi_ev['t'])} (-{self.oi_ev['pct']:.1f} %): acceptance past {G} now takes you out"
        else:
            s = f"out if {G} is accepted and held {HELD_N} buckets, or accepted while {wr} leave · never back through {self.entry_px - d * self.B_at(t) / 2:.0f}"
        if self.oi_blind(t) and self._trailed():
            s += " · OI blind: held breach and backstop still watch"
        return s

    # ---- premium (§4.7)
    def _prem_at(self, px, t):
        if self.rc is None or self.F is None:
            return None, f"{CC}: chain from 09:17"
        age = t - self.rc_t
        if age > PREM_STALE_MS:
            return None, f"{CC}: chain {age // 1000} s old"
        kp = self.k + self.F + self.bas - px              # px is a futures-chart price (G, A): back to the forward first
        xs = sorted(((x["k"], x[self.ty]["ltp"]) for x in self.rc["strikes"] if x[self.ty].get("ltp")), key=lambda z: z[0])
        i = bisect.bisect_left([z[0] for z in xs], kp)
        if i == 0 or i >= len(xs):
            return None, f"{CC}: {kp:.0f} is beyond the chain"
        (k0, p0), (k1, p1) = xs[i - 1], xs[i]
        return round(p0 + (p1 - p0) * (kp - k0) / (k1 - k0), 1), "[I]"

    def _prem(self, t):
        pn = self.prem_now()
        age = None if self.rc_t is None else (t - self.rc_t) // 1000
        pct = lambda p: None if p is None else round(100 * self.own * (p - self.p0) / self.p0)   # noqa: E731
        atG, atG_why = self._prem_at(self.G, t) if self.G is not None else (None, f"{CC}: no give-up yet")
        ak = self.named["A"]
        ax = ak + self.bas if (ak is not None and self.bas is not None) else None
        atA, atA_why = self._prem_at(ax, t) if ax is not None else (None, f"{CC}: no wall ahead read")
        intr = None if self.F is None else round(max(0.0, (self.F - self.k) if self.ty == "ce" else (self.k - self.F)), 1)
        return dict(now=pn, pct=pct(pn), peak=self.prem_peak, peak_pct=pct(self.prem_peak),
                    peak_t=hm(self.prem_peak_t) if self.prem_peak_t else None,
                    given_back=(round(self.own * (self.prem_peak - pn), 1) if None not in (pn, self.prem_peak) else None),
                    at_G=atG, at_G_why=atG_why, at_A=atA, at_A_why=atA_why, chain_age_s=age,
                    intrinsic=intr, time=(round(pn - intr, 1) if None not in (pn, intr) else None),
                    expiry_day=self.expiry_day, tag=dict(M=["now", "peak", "given_back"], I=["at_G", "at_A", "intrinsic", "time"]))

    # ---- the state at a time
    def _snap(self, t):
        B = self.B_at(t)
        h, cl = self._headline(t)
        d = self.d
        Wd = None
        if self.W is not None:
            w_ = self.Ww
            pk = w_.pk if w_ is not None else None
            Wd = dict(k=self.W, side=self.dty, oi=self.cur_oi((self.W, self.dty)), peak=pk,
                      peak_t=hm(w_.peak_t(self.oiu)) if pk is not None else None, state=w_.state() if w_ else None,
                      px=self._px(self.W))                                         # at K + her basis, as A.px is
        Ad = None
        ak = self.named["A"]
        if ak is not None:
            a_ = self.Aw
            Ad = dict(k=ak, side=self.aty, px=self._px(ak), pts=round(d * (self._px(ak) - self.last_p)),
                      oi=self.cur_oi((ak, self.aty)), peak=a_.pk if a_ else None,
                      peak_t=hm(a_.peak_t(self.oiu)) if a_ and a_.pk is not None else None,
                      state=a_.state() if a_ else None)                                # W's vocabulary: building / stopped / off
        bm = min(15, max(1, round((t - self.basis[0][0]) / 60000))) if self.basis else None
        # The staircase, output only: a step is recorded when a snapshot sees G at a new price (every change of G
        # happens at an event, and every event is snapped), so a G set and withdrawn inside one step never shows.
        if self.G is not None and (not self.G_steps or self.G_steps[-1]["px"] != self.G):
            self.G_steps.append(dict(t=hm(self.G_t) if self.G_t else None, px=self.G, why=self.G_src))
        return dict(t=t, ts=hms(t), headline=h, clause=cl, line2=self._line2(t),
                    chips=dict(Z=self.shown["ZONE"], F=self.shown["FLOW"], O=self.shown["OI"], V=self.shown["VPIN"]),
                    sentences=dict(Z=self.why["ZONE"], F=self.why["FLOW"], O=self.why["OI"], V=self.why["VPIN"]),
                    mode=("trailed" if self._trailed() else "at entry") if self.G is not None else None,
                    expiry_pm=self._expiry_pm(t), d=d, E=self.entry_px, fut=self.last_p, F=None if self.F is None else round(self.F, 1),
                    G=dict(px=self.G, why=self.G_src, set_t=hm(self.G_t) if self.G_t else None, locked=True, touched=self.G_hit),
                    W=Wd, A=Ad, epoch=self.epoch, G_steps=[dict(x) for x in self.G_steps],
                    units=dict(bucket=self.BK, B=B, theta=None if B is None else 2 * B, w=None if B is None else B / 2,
                               med_bucket_s=self.med_bk_dur() / 1000, pooled_sessions=self.prior_n, bucket_src=self.bk_src,
                               basis_minutes=bm, basis=None if self.bas is None else round(self.bas, 1),
                               basis_of="future minus the options' own forward (K + CE - PE, both |delta| > 0.3), median over 15 min; "
                                        "the engine's own: G, the zone reads and the premiums",
                               basis_ix=None if self.bas_ix is None else round(self.bas_ix, 1),
                               basis_ix_of="future minus the index, median over 15 min: where a strike is drawn (K + basis_ix) "
                                           "and how a futures price is printed as spot (fut - basis_ix)"),
                    prem=self._prem(t),
                    acc=None if self.acc is None else dict(t=hms(self.acc["t"]), G=self.acc["G"], lots=round(self.acc["lots"]), n=self.acc_n),
                    tally=dict(t0=hms(self.tally_t0) if self.tally_t0 else None, lots=round(self.tally), restarts=max(0, self.tally_n - 1),
                               backstop_t0=hms(self.etally_t0) if self.etally_t0 else None),
                    oi_event=None if self.oi_ev is None else dict(t=hms(self.oi_ev["t"]), z=round(self.oi_ev["z"], 2), n=self.oi_ev["n"],
                                                                  pct=round(self.oi_ev["pct"], 2), peak=self.oi_ev["pk"], k=self.W, side=self.dty),
                    alt={k: (dict(t=hms(v[0]), prem=v[1]) if v else None) for k, v in
                         ((k, self.first.get(k)) for k in ("plain_accept", "flow_oi", "held", "backstop"))},
                    sound_id=self.folds[-1]["sound_id"] if self.folds else None,
                    tag=dict(M=["G", "W", "A", "fut", "prem.now"], I=["F", "chips", "prem.at_G", "prem.at_A"]))

    def _view_core(self, t):
        s = self._snap(t)
        s["rows"] = {c.lower(): dict(chip=self.shown[C], sentence=self.why[C] or f"{CC}: not read yet") for c, C in
                     (("zone", "ZONE"), ("flow", "FLOW"), ("oi", "OI"), ("vpin", "VPIN"))}
        if self.zone_text:
            s["rows"]["zone"]["machine"] = self.zone_text
        s["holes"] = [dict(t0=hms(a), t1=hms(b), why=w) for a, b, w in self.holes]
        s["trade_id"], s["rev"], s["frozen"] = self.trade_id, REV, False
        return s

    def view(self, now=None):
        t = now if now is not None else (self.last_key or self.entry_t)
        if t < self.entry_t or not self.seeded:
            return dict(headline=None, why="before the mark" if t < self.entry_t else "no rows since the mark yet",
                        t=t, ts=hms(t), d=self.d, trade_id=self.trade_id, rev=REV, events=[], new_events=[])
        if self.exit_t is not None and t >= self.exit_t:
            if self.exit_view is None:
                self.exit_view = self._view_core(self.exit_t)
            s = dict(self.exit_view, frozen=True, exit_t=hms(self.exit_t))   # the premium and P&L at her exit, never later
        else:
            s = self._view_core(t)
        s["events"], s["new_events"] = self.events, self.events[self._new:]
        self._new = len(self.events)
        return s

    # ---- flat (§6): no trade, the market alone
    def flat_view(self, t):
        out = dict(date=self.day, asof=hms(t), next_fight=None, at=None, gave_up=None, reentry=None,
                   marks=[m for m in self.marks if m["t"] <= t],
                   basis=None if self.bas is None else round(self.bas, 1), basis_ix=None,
                   frame="flat: a row's chip names the side it favours -- BUYERS, SELLERS, QUIET, CAN'T CHECK",
                   rows={}, day=None, tag=dict(M=["next_fight.px", "what", "day"], I=["confirm", "F"]))
        B = self.B_at(t)
        if B is None or self.F is None or self.last_p is None:
            why = f"{CC}: chain from 09:17" if self.F is None else f"{CC}: no bars yet"
            out["why"] = why
            out["rows"] = {c: dict(chip="CAN'T CHECK", sentence=why) for c in ("zone", "flow", "oi", "vpin")}
            out["day"] = why
            return out
        w, F = B / 2, self.F
        out["F"], out["basis_ix"] = round(F, 1), None if self.bas_ix is None else round(self.bas_ix, 1)
        # Every level here is a futures-chart price, so it is sorted against the FUTURE (2026-10-05: it was sorted
        # against F, the forward ~94 below, and called 22,565 "upar" with the future at 22,640). Walls at her drawn price.
        P = self.last_p
        strong = [((self._lvpx(x),) + x[1:]) for x in self.levels(t) if x[1] in (1, 2, 4, 5)]

        rank = {4: 0, 1: 1, 2: 2, 5: 3}                                # walls, trapped, held, yesterday's; two facts at most

        def group(ref):
            near = sorted((x for x in strong if abs(x[0] - ref[0]) <= w), key=lambda x: rank.get(x[1], 4))
            return " · ".join(x[2] for x in near[:2])

        def confirm(ref, up):
            walls = [x for x in strong if abs(x[0] - ref[0]) <= w and x[1] == 4 and x[5] == ("CE" if up else "PE")]
            oi = f" and {walls[0][4]} {walls[0][5]} off its peak" if walls else " and no absorption there"
            px = ref[0]
            flow = f"lifts at {px:.0f}–{px + w:.0f} followed by price" if up else f"hits at {px - w:.0f}–{px:.0f} followed by price"
            return f"{flow}{oi} · VPIN turning {'buyers' if up else 'sellers'}' way: {'calls' if up else 'puts'}"

        at = next((x for x in sorted(strong, key=lambda x: abs(x[0] - P)) if abs(x[0] - P) <= w), None)
        above = sorted((x for x in strong if x[0] > P + w), key=lambda x: x[0])
        below = sorted((x for x in strong if x[0] < P - w), key=lambda x: -x[0])
        if at:
            out["at"] = dict(px=round(at[0]), what=group(at))
        if strong:
            out["next_fight"] = dict(
                above=dict(px=round(above[0][0]), what=group(above[0]), confirm=confirm(above[0], True)) if above else dict(px=None, what=f"{CC}: no level above yet", confirm=None),
                below=dict(px=round(below[0][0]), what=group(below[0]), confirm=confirm(below[0], False)) if below else dict(px=None, what=f"{CC}: no level below yet", confirm=None))
        # the frozen, silent GAVE UP event: a fight won at a named wall while that wall is off its peak (both halves)
        recent = [x for x in self.bk if x["t1"] <= t][-VPIN_WIN:]
        t_win = recent[0]["t0"] if recent else t
        for ty, winner, who in (("CE", 1, "SELLERS"), ("PE", -1, "BUYERS")):
            k = self.named[ty]
            wt = self.flat_watch.get((k, ty)) if k is not None else None
            if not wt or wt.state() != "off":
                continue
            px = self.wall_px[ty]
            f = next((r for r in reversed(self.runs) if "fixed_t" in r and r["fixed_t"] <= t and r["winner"] == winner
                      and r["t1"] >= t_win and r["pmin"] - w <= px <= r["pmax"] + w), None)
            if f:
                te = max(f["fixed_t"], wt.event["t"])
                out["gave_up"] = dict(text=f"{who} GAVE UP AT {px:.0f} · {hm(te)}", t=hms(te), px=px, k=k, side=ty,
                                      oi=f"{_L(wt.event['pk'])} to {_L(self.cur_oi((k, ty)))} (-{wt.event['pct']:.1f} %) [M]",
                                      unproven=f"unproven · wrong if price is back through {px:.0f} within 20 min · counts, never rates")
        fold_ = self.trade_fold if hasattr(self, "trade_fold") else None
        if fold_:
            out["reentry"] = self._reentry(fold_, t, w)
        # the rows, for buyers (up)
        fixed = [r for r in self.runs if "fixed_t" in r and r["fixed_t"] <= t]
        last = fixed[-1] if fixed else None
        fresh = last is not None and recent and last["t1"] >= recent[0]["t0"]
        SIDE = {1: "BUYERS", -1: "SELLERS"}
        if not strong:
            zone = ("CAN'T CHECK", f"{CC}: no levels yet")
        elif at:
            zone = (SIDE.get(at[3], "QUIET"), f"at {at[0]:.0f} ({group(at)})")
        else:
            zone = ("QUIET", f"between {below[0][0]:.0f} and {above[0][0]:.0f}" if above and below else "no level on one side yet")
        if fresh and last["winner"] is None:
            flow = ("CAN'T CHECK", f"{CC}: newest fight disputed {hm(last['t1'])}")
        elif fresh:
            flow = (SIDE[last["winner"]], f"{WHO[last['winner']]} won {hm(last['t1'])} at {last['vw']:.0f}")
        else:
            flow = ("QUIET", f"no fight in the last {len(recent)} buckets")
        parts, votes = [], []
        for ty, sd in (("CE", 1), ("PE", -1)):
            k = self.named[ty]
            wt = self.flat_watch.get((k, ty)) if k is not None else None
            if not wt or wt.pk is None:
                continue
            st_ = wt.state()
            oi = self.cur_oi((k, ty))
            if st_ == "off":
                parts.append(f"{k} {ty} {_L(oi)} off since {hm(wt.event['t'])} (-{wt.event['pct']:.1f} %)")
                votes.append(-sd)          # CE writers leaving helps the buyers; PE writers leaving, the sellers
            elif st_ == "building":
                parts.append(f"{k} {ty} {_L(oi)} adding, high {_L(wt.pk)} {hm(wt.peak_t(self.oiu))}")
                votes.append(sd)           # CE adding sits in the buyers' way
            else:
                parts.append(f"{k} {ty} {_L(oi)} stopped adding")
        if self.oi_blind(t):
            oi_row = ("CAN'T CHECK", f"{CC}: chain {(t - self.rc_t) // 60000} min old")
        elif not parts:
            oi_row = ("CAN'T CHECK", f"{CC}: no wall named yet")
        else:
            v = sum(votes)
            oi_row = ("BUYERS" if v < 0 else "SELLERS" if v > 0 else "QUIET", " · ".join(parts) + " [M]")
        vb = [r for r in self.vp if r["t1"] <= t][-VPIN_WIN:]
        one = [sgn(r["buy"] - r["sell"]) for r in vb if (r["buy"] + r["sell"]) and abs(r["buy"] - r["sell"]) / (r["buy"] + r["sell"]) >= ONE_SIDED]
        net = sum(one)
        if len(vb) < VPIN_WIN:
            vp = ("CAN'T CHECK", f"{CC}: {len(vb)} of {VPIN_WIN} VPIN buckets")
        elif net >= VPIN_LEAD:
            vp = ("BUYERS", f"{sum(1 for x in one if x > 0)} of {len(vb)} buckets one-sided, buyers' way")
        elif net <= -VPIN_LEAD:
            vp = ("SELLERS", f"{sum(1 for x in one if x < 0)} of {len(vb)} buckets one-sided, sellers' way")
        else:
            vp = ("QUIET", f"{len(one)} of {len(vb)} buckets one-sided, no lead")
        out["rows"] = {c: dict(chip=v[0], sentence=v[1]) for c, v in (("zone", zone), ("flow", flow), ("oi", oi_row), ("vpin", vp))}
        if self.zone_text:
            out["rows"]["zone"]["machine"] = self.zone_text
        # THE DAY (R6), one sentence: whose day, value, boxed or trending
        nb = sum(1 for r in fixed if r["winner"] == 1)
        ns = sum(1 for r in fixed if r["winner"] == -1)
        whose = f"{'buyers' if nb > ns else 'sellers'}' day ({max(nb, ns)} fights to {min(nb, ns)}) [M]" if nb != ns else f"nobody's day yet ({nb} fights each) [M]"
        biz = recent[-1]["vw"] if recent else self.last_p
        if self.volp:
            poc, vah, val = _va(_vp([dict(p=k, q=q) for k, q in self.volp.items()]))
            where = ("trending above value" if biz > vah + w else "trending below value" if biz < val - w else "boxed in value")
            out["day"] = f"{whose} · value {poc:.0f} ({val:.0f}–{vah:.0f}) [I] · {where}"
        else:
            out["day"] = f"{whose} · {CC}: no business yet"
        return out

    def _reentry(self, fd, t, w):
        """§6: after a FOLD, the first fight won by her side fixed after a print w back inside G. Unproven, silent."""
        d, G = fd["d"], fd["G"]
        i0 = bisect.bisect_right(self.ft, fd["t"])
        back = next((self.ft[i] for i in range(i0, len(self.ft)) if self.ft[i] <= t and d * (self.fp[i] - G) >= w), None)
        if back is None:
            return dict(text=f"no re-entry read: not back inside {G} by w since the FOLD {hm(fd['t'])}", unproven=True)
        r = next((r for r in self.runs if "fixed_t" in r and back < r["fixed_t"] <= t and r["winner"] == d), None)
        if r is None:
            return dict(text=f"no re-entry read: back inside {G} {hm(back)}, no fight won {WHO[d]}' way since", unproven=True)
        x = next((x for x in self.rc["strikes"] if x["k"] == fd["k"]), None) if self.rc else None
        pn = x[str(fd["ty"]).lower()]["ltp"] if x else None
        return dict(text=f"stop run failed at {G}: {WHO[r['winner']]} won at {r['vw']:.0f}, {hm(r['fixed_t'])} · "
                         f"{str(fd['ty']).upper()} {pn} v your exit {fd.get('exit_prem')} · unproven: 0 of 3 in replay",
                    t=hms(r["fixed_t"]), px=round(r["vw"]), prem=pn, exit_prem=fd.get("exit_prem"), unproven=True,
                    falsifier=f"G {G} accepted again within 20 min")


# ---- public API
def start(trade, inputs):
    """A State over the day's rows so far (inputs as the module docstring), not yet read."""
    st_ = State(trade, inputs)
    st_.feed(inputs.get("book"), inputs.get("chain"), inputs.get("vpin"), inputs.get("tape"))
    return st_


def step(state, new_inputs, now=None):
    """Feed new rows (book / chain / vpin / tape, in key order) and return the state at `now`
    (default: the newest key). The server's incremental use."""
    state.feed(new_inputs.get("book"), new_inputs.get("chain"), new_inputs.get("vpin"), new_inputs.get("tape"))
    return state.view(now if now is not None else new_inputs.get("now"))


def _cut(inputs, upto):
    day = inputs["day"]
    if isinstance(upto, str):
        upto = ms(day, upto)
    if upto is not None:
        inputs = dict(inputs, book=[r for r in inputs.get("book") or () if r["t"] <= upto],
                      chain=[r for r in inputs.get("chain") or () if ms(day, r["ts"]) <= upto],
                      vpin=[r for r in inputs.get("vpin") or () if r.get("day") != day or ms(day, r["at"]) <= upto])
    return inputs, upto


def read(trade, inputs, upto=None, exit_t=None):
    """The state at a time: {headline, clause, line2, rows:{zone, flow, oi, vpin}, G, A, prem, events, ...}.
    `upto` (ms or 'HH:MM:SS') cuts the rows by key; the rest of `inputs` is as start(). With an exit
    (`exit_t` here or trade["exit_t"]) the view is frozen at the exit -- premium and P&L at her exit -- while
    the events go on to the close, flagged after_exit."""
    if exit_t is not None:
        trade = dict(trade, exit_t=exit_t)
    inputs, upto = _cut(inputs, upto)
    return start(trade, inputs).view(upto)


def flat(inputs, upto=None, idx="NIFTY"):
    """§6, FLAT: {next_fight:{above, below:{px, what, confirm}}, at, rows, day, gave_up, reentry, asof}.
    A `fold` in inputs ({G, d, k, ty, t, exit_prem}: the last FOLD today) yields the re-entry read, unproven."""
    inputs, upto = _cut(dict(inputs, idx=idx), upto)
    st_ = start(None, inputs)
    if inputs.get("fold"):
        fd = dict(inputs["fold"])
        fd["t"] = ms(inputs["day"], fd["t"]) if isinstance(fd["t"], str) else int(fd["t"])
        st_.trade_fold = fd
    return st_.flat_view(upto if upto is not None else (st_.last_key or ms(inputs["day"], SESSION_OPEN)))


def ifin(inputs, k, ty, side, upto=None):
    """§5, IF YOU WERE IN: the in-trade view for a trade marked now (the last recorded row at or before `upto`)
    at the chain's live premium for (k, ty). No GO / NO: line 2, G, A and the premium there are the answer."""
    inputs, upto = _cut(inputs, upto)
    day = inputs["day"]
    b = max(inputs.get("book") or (), key=lambda r: r["t"], default=None)
    c = max(inputs.get("chain") or (), key=lambda r: ms(day, r["ts"]), default=None)
    if b is None and c is None:
        return dict(headline=None, why=f"{CC}: no rows by {hms(upto) if upto else 'now'}", ifin=True)
    # the mark is the last recorded row: a book row seeds on its fill (its own ltt), a chain row on its ts
    t = b["t"] if b is not None and (c is None or b["t"] >= ms(day, c["ts"])) else ms(day, c["ts"])
    mark = min(t, b.get("ltt") or t) if (b is not None and t == b["t"]) else t
    snap = max((r for r in inputs.get("chain") or () if ms(day, r["ts"]) <= t), key=lambda r: ms(day, r["ts"]), default=None)
    x = next((x for x in (snap or {}).get("strikes") or [] if x["k"] == int(k)), None)
    p0 = x[str(ty).lower()]["ltp"] if x else None
    if not p0:
        return dict(headline=None, why=f"{CC}: no chain price for {k} {str(ty).upper()} by {hms(t)}", ifin=True, t=t, ts=hms(t))
    trade = dict(k=int(k), ty=str(ty).upper(), side=str(side).upper(), p0=p0, entry_t=mark,
                 trade_id=f"ifin:{day}:{k}{str(ty).upper()}:{str(side).upper()[0]}:{hms(t)}")
    v = start(trade, inputs).view(t)
    v.update(ifin=True, trade=trade, p0=p0, entry_t=hms(mark))
    return v


def _first_back(state, t0, t1, level, d, w):
    """The first print in (t0, t1] that is w back inside `level` her way, as hh:mm:ss, or None."""
    if level is None:
        return None
    i0, i1 = bisect.bisect_right(state.ft, t0), bisect.bisect_right(state.ft, t1)
    return next((hms(state.ft[i]) for i in range(i0, i1) if d * (state.fp[i] - level) >= w), None)


def outcome(state, e, horizon_ms=20 * 60000):
    """6-amendment §4: the verdict on a falsifiable read, once 20 minutes of rows are in; None before then
    and for reads that are not falsifiable (CAN'T CHECK is counted, never judged)."""
    t = e["t"]
    if state.last_key is None or state.last_key < t + horizon_ms:
        return None
    d, row, kind, why = state.d, e.get("row") or {}, e["kind"], e.get("why")
    w = (row.get("units") or {}).get("w") or 0
    if kind == "fold":
        lvl = row.get("E") if why == "backstop" else (row.get("G") or {}).get("px")
        back = _first_back(state, t, t + horizon_ms, lvl, d, w)
        v = [f"back inside {lvl} by w at {back}" if back else f"never back inside {lvl} by w in 20 min"]
        oe = row.get("oi_event")
        if why == "flow_oi" and oe:
            u = state.oiu.get((oe["k"], oe["side"])) or []
            rb = next((hms(x[0]) for x in u if t <= x[0] <= t + horizon_ms and x[1] > oe["peak"]), None)
            v.append(f"W rebuilt above {_L(oe['peak'])} at {rb}" if rb else "W not rebuilt in 20 min")
        if why == "expiry":
            i = bisect.bisect_right([x[0] for x in state.prem_hist], t + horizon_ms) - 1
            p20, fp = (state.prem_hist[i][1] if i >= 0 else None), (row.get("prem") or {}).get("now")
            if None not in (p20, fp) and state.own * (p20 - fp) > 0:
                v.append(f"premium at +20 min {p20} better than the FOLD's {fp}")
        noise = any(x.startswith(("back inside", "W rebuilt", "premium at +20")) for x in v)
        return dict(read=f"fold:{why}", verdict="noise" if noise else "real", why="; ".join(v))
    if kind == "past_give_up":
        later = next((x for x in state.events if x["t"] > t and x["kind"] in ("fold", "withdrawn")), None)
        if later is None:
            return dict(read="past_give_up", verdict="real", why="stood to the horizon without a withdrawal")
        return dict(read="past_give_up", verdict="noise" if later["kind"] == "withdrawn" else "real", why=f"ended {later['kind']} {later['ts']}")
    if kind == "clause" and "against you" in (e.get("text") or ""):
        follow = next((x for x in state.events if t < x["t"] <= t + horizon_ms and x["kind"] in ("fold", "past_give_up")), None)
        return dict(read="against_you", verdict="real" if follow else "counted",
                    why=f"followed by {follow['kind']} {follow['ts']}" if follow else "no FOLD or PAST GIVE-UP within 20 min")
    return None
