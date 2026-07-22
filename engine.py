"""
Tape-reading replay engine for FUT + CE + PE 1-minute data.

Reads three synchronized CSVs (futures, call, put) each carrying:
OHLC, VWAP, +/-1/2/3 sigma VWAP bands, standard pivots (P, R1-R3, S1-S3), OI, Volume.

Philosophy: NO absolute thresholds. Every raw value is ranked against the
session's own expanding distribution (percentile-so-far), so the same engine
reads NIFTY, BANKNIFTY or a stock without retuning. Only *relative* cutoffs
(percentile ranks) define events.

Event grammar:
  CAMPAIGN    one book's OI building hard while its premium falls -> writers pressing
  BUYER-BUILD one book's OI building while its premium firms -> protection being bought
  TRAP        option stretched beyond 2-sigma inside immature bands w/ two-sided writing
  DIVERGENCE  FUT new extreme not confirmed by the option that should profit from it
  PRESS       both option books rotating the same direction ahead of price
  SPRING      dip/rally being disbelieved: winners cashing out + losers adding at extreme
  ARMED       spring + level confluence + band compression
  IGNITION    synchronized volume detonation across all three books
  CLIMAX      3-sigma overshoot + losing-side OI cliff + volume extreme -> marks the turn
  ABSORPTION  extreme volume, no price result
  FLIP-TEST   broken pivot retested from the other side and holding
  CARRY       end-of-day residual OI verdict -> next-day bias
"""

import csv
import math
import re
import sys
from bisect import bisect_right, insort
from collections import defaultdict

from gamma import implied_vol

# ---------------------------------------------------------------- data loading

COLS = ["O", "H", "L", "C", "VWAP", "U1", "D1", "U2", "D2", "U3", "D3",
        "P", "R1", "S1", "R2", "S2", "R3", "S3", "OI", "V"]


def load(path):
    """Parse a Zerodha CSV export -> {day: [bar dicts]} keeping full sessions only."""
    days = defaultdict(list)
    with open(path, newline="", encoding="utf-8-sig") as f:
        rdr = csv.reader(f)
        next(rdr)
        for row in rdr:
            m = re.match(r"\w+ (\w+ \d+) \d+ (\d\d:\d\d):", row[0])
            if not m:
                continue
            day, t = m.group(1), m.group(2)
            bar = {"T": t}
            for i, c in enumerate(COLS):
                bar[c] = float(row[i + 1])
            days[day].append(bar)
    return {d: bars for d, bars in days.items() if len(bars) > 100}


# ------------------------------------------------------------- expanding ranks

class Rank:
    """Percentile-so-far of a stream: rank(x) in [0,1] vs values seen earlier."""

    def __init__(self):
        self.sorted = []

    def rank(self, x):
        n = len(self.sorted)
        r = bisect_right(self.sorted, x) / n if n else 0.5
        insort(self.sorted, x)
        return r

    @property
    def n(self):
        return len(self.sorted)


# ---------------------------------------------------------------- one session

MATURITY = 20      # minutes before VWAP bands carry statistical weight
SLOPE_W = 10       # OI slope window (minutes)
WARMUP = 15        # bars before volume/range ranks are trusted


class Book:
    """Per-instrument session state: ranks, slopes, swing extremes."""

    def __init__(self, name):
        self.name = name
        self.vol = Rank()
        self.rng = Rank()
        self.oi_slope = Rank()   # ranks |OI slope|
        self.bw = Rank()
        self.bars = []
        self.max_c = -1e18
        self.min_c = 1e18

    def update(self, bar):
        self.bars.append(bar)
        i = len(self.bars) - 1
        f = {}
        f["vol_r"] = self.vol.rank(bar["V"])
        f["rng_r"] = self.rng.rank(bar["H"] - bar["L"])
        span = bar["U1"] - bar["VWAP"]
        f["z"] = (bar["C"] - bar["VWAP"]) / span if span > 1e-9 else 0.0
        f["bw"] = bar["U2"] - bar["D2"]
        f["bw_r"] = self.bw.rank(f["bw"])
        if i >= SLOPE_W:
            slope = bar["OI"] - self.bars[i - SLOPE_W]["OI"]
            prem = bar["C"] - self.bars[i - SLOPE_W]["C"]
        else:
            slope, prem = 0.0, 0.0
        f["oi_slope"] = slope
        f["oi_slope_r"] = self.oi_slope.rank(abs(slope))
        f["prem_d"] = prem
        self.max_c = max(self.max_c, bar["C"])
        self.min_c = min(self.min_c, bar["C"])
        bar["f"] = f
        return f


def median(vals):
    s = sorted(vals)
    return s[len(s) // 2] if s else 0.0


class GammaLayer:
    """MM-perspective layer (architecture invariant 3: strictly separate).

    Reads the same per-bar features the base engine computes, maintains
    writer/buyer scores per book, classifies the dealer-hedging regime
    (PINNED / AMPLIFIED-UP / AMPLIFIED-DOWN / NEUTRAL) and emits only
    GAMMA-PIN, SQUEEZE-RISK and SQUEEZE-RELEASE events. It never touches
    base states, signals or their wording.
    """

    # bell width 0.35% of strike ≈ one intraday band; the only geometry
    # parameter, expressed relative to the strike (no absolute points)
    WIDTH = 0.0035

    def __init__(self, sess, strike, t_days):
        self.s = sess
        self.k = strike
        self.t = max(t_days, 0.25) if t_days else 1.0
        self.w = {"CE": 0.0, "PE": 0.0}          # writer score in [-1, 1]
        self.oi0 = None                          # session-open OI/premium refs
        self.px0 = None
        self.build_peak = {"CE": 0.0, "PE": 0.0}
        self.peak_oi = {"CE": 0.0, "PE": 0.0}
        self.oi_rank = {"CE": Rank(), "PE": Rank()}
        self.pv_rank = {"CE": Rank(), "PE": Rank()}   # |premium velocity|
        self.unwind = {"CE": 0, "PE": 0}         # accelerating-unwind minutes
        self.last_slope = {"CE": 0.0, "PE": 0.0}
        self.regime = "NEUTRAL"
        self.regime_since = 0
        self.iv = {"CE": None, "PE": None}   # solved every 5m, forward-held
        self.ivr = {"CE": Rank(), "PE": Rank()}   # IV percentile-so-far
        self.iv_r = {"CE": None, "PE": None}      # latest IV rank per book
        self.track = {}

    def update(self, i, fb, cb, pb, ff, cf, pf, mature):
        if self.k is None:
            return
        F = fb["C"]
        dist = (F - self.k) / (self.WIDTH * self.k)
        near = abs(dist) < 1.2   # within ~1.2 bell widths of the strike
        proxy = math.exp(-0.5 * dist * dist) / math.sqrt(self.t)

        if self.oi0 is None:
            self.oi0 = {"CE": cb["OI"], "PE": pb["OI"]}
            self.px0 = {"CE": cb["C"], "PE": pb["C"]}

        feats = {}
        self.peak_oi["CE"] = max(self.peak_oi["CE"], cb["OI"])
        self.peak_oi["PE"] = max(self.peak_oi["PE"], pb["OI"])
        for nm, ob, of in (("CE", cb, cf), ("PE", pb, pf)):
            # book weight = fraction of the session's own peak book (a wall
            # that unwound 20% is still a wall; level-rank decays wrongly)
            oir = ob["OI"] / self.peak_oi[nm] if self.peak_oi[nm] > 0 else 0.0
            pvr = self.pv_rank[nm].rank(abs(of["prem_d"]))
            # writer score = session-cumulative positioning (same read that
            # validated in the GEX-lite study): net new OI since open,
            # classified by premium direction since open. Magnitude relative
            # to the session's own largest build (self-scaling).
            doi = ob["OI"] - self.oi0[nm]
            self.build_peak[nm] = max(self.build_peak[nm], doi)
            dpx = ob["C"] - self.px0[nm]
            # 2% premium-move floor (relative) before calling a direction
            direction = 1.0 if dpx < -0.02 * self.px0[nm] else \
                (-1.0 if dpx > 0.02 * self.px0[nm] else 0.0)
            mag = max(doi, 0.0) / self.build_peak[nm] if self.build_peak[nm] > 0 else 0.0
            self.w[nm] = direction * min(1.0, mag)
            sl = of["oi_slope"]
            if sl < 0 and abs(sl) > abs(self.last_slope[nm]):
                self.unwind[nm] += 1
            elif sl >= 0:
                self.unwind[nm] = 0
            self.last_slope[nm] = sl
            feats[nm] = (oir, pvr)

        wc, wp = self.w["CE"], self.w["PE"]
        # release = violent unwind + violent premium move on one book
        ce_rel = cf["oi_slope"] < 0 and cf["oi_slope_r"] >= 0.9 \
            and cf["prem_d"] > 0 and feats["CE"][1] >= 0.9
        pe_rel = pf["oi_slope"] < 0 and pf["oi_slope_r"] >= 0.9 \
            and pf["prem_d"] > 0 and feats["PE"][1] >= 0.9

        # directional wall weights: a put writer wall supports the downside
        # (FLOOR), a call writer wall caps the upside (CEILING); both = PINNED.
        # A one-sided wall never dampens moves away from it.
        pin_dn = max(wp, 0.0) * feats["PE"][0]
        pin_up = max(wc, 0.0) * feats["CE"][0]

        regime = "NEUTRAL"
        # AMPLIFIED requires the NET book buyer-built (dealers net short
        # gamma). Backtest (55 days, 219 band tags): with the old rule the
        # fade still won 58% inside "AMPLIFIED" — the label over-fired; the
        # clean amplification measure is net writer score < 0.
        netw = wc + wp
        if (ce_rel or (wc < -0.3 and ff["z"] > 0.5)) and netw < 0:
            regime = "AMPLIFIED-UP"
        elif (pe_rel or (wp < -0.3 and ff["z"] < -0.5)) and netw < 0:
            regime = "AMPLIFIED-DOWN"
        elif near and min(pin_dn, pin_up) > 0.35:
            regime = "PINNED"
        elif near and pin_dn > 0.5:
            regime = "FLOOR"
        elif near and pin_up > 0.5:
            regime = "CEILING"

        if regime != self.regime:
            self.regime_since = i
        if i % 5 == 0:                      # causal: solve now, hold forward
            T = self.t / 365.0
            for nm, ob, kd in (("CE", cb, "C"), ("PE", pb, "P")):
                iv = implied_vol(ob["C"], F, self.k, T, kd)
                if iv is not None:
                    self.iv[nm] = round(iv, 4)
        for nm in ("CE", "PE"):             # rank the held IV vs the day
            if self.iv[nm] is not None:
                self.iv_r[nm] = self.ivr[nm].rank(self.iv[nm])
        self.track[fb["T"]] = {"regime": regime,
                               "w_ce": round(wc, 2), "w_pe": round(wp, 2),
                               "proxy": round(proxy, 3),
                               "iv_ce": self.iv["CE"], "iv_pe": self.iv["PE"]}

        if not mature:
            self.regime = regime
            return

        if regime in ("PINNED", "FLOOR", "CEILING") and regime != self.regime:
            what = {"PINNED": "two-sided walls — hedging dampens both ways, "
                              "expect mean reversion to strike",
                    "FLOOR": "put wall below — dips into the strike get "
                             "absorbed; upside is NOT capped",
                    "CEILING": "call wall above — rallies into the strike get "
                               "sold; downside is NOT supported"}[regime]
            self.s.emit(i, "GAMMA-PIN",
                        f"{regime} at {self.k:.0f}: writer scores CE {wc:+.2f} / "
                        f"PE {wp:+.2f}, books {cb['OI']/1e6:.1f}M/"
                        f"{pb['OI']/1e6:.1f}M, FUT {abs(F-self.k):.0f} pts away — "
                        f"{what}", every=20)

        for nm, ob, of, pain, dirn in (
                ("CE", cb, cf, F > self.k, "upside"),
                ("PE", pb, pf, F < self.k, "downside")):
            if (self.w[nm] > 0.25 and feats[nm][0] > 0.7 and pain
                    and self.unwind[nm] >= 2):
                self.s.emit(i, "SQUEEZE-RISK",
                            f"{nm} writer book ({ob['OI']/1e6:.1f}M, score "
                            f"{self.w[nm]:+.2f}) pressed on its pain side, unwind "
                            f"accelerating {self.unwind[nm]} min "
                            f"({of['oi_slope']/1000:.0f}k/{SLOPE_W}m) → {dirn} "
                            f"squeeze risk building", every=12)

        for rel, nm, of, dirn in ((ce_rel, "CE", cf, "UPWARD"),
                                  (pe_rel, "PE", pf, "DOWNWARD")):
            if rel:
                self.s.note_detonation(i, +1 if dirn == "UPWARD" else -1, F)
                mech = ("trapped writers force-covering" if self.w[nm] > 0.15
                        else "dealer short-gamma hedge chase"
                        if self.w[nm] < -0.15 else "positioning capitulation")
                self.s.emit(i, "SQUEEZE-RELEASE",
                            f"{dirn}: {nm} OI {of['oi_slope']/1000:.0f}k/{SLOPE_W}m "
                            f"(rank {of['oi_slope_r']:.2f}) with premium velocity "
                            f"rank {feats[nm][1]:.2f} — {mech}, hedging amplifies "
                            f"the move", every=10)

        self.regime = regime


class Session:
    """Replays one day across the three books and emits the event stream."""

    def __init__(self, day, fut, ce, pe, quiet=False, strike=None, t_days=None):
        self.day = day
        self.strike = strike
        self.gamma = GammaLayer(self, strike, t_days)
        self.fut_bars, self.ce_bars, self.pe_bars = fut, ce, pe
        self.ce_by_t = {b["T"]: b for b in ce}
        self.pe_by_t = {b["T"]: b for b in pe}
        self.books = {"FUT": Book("FUT"), "CE": Book("CE"), "PE": Book("PE")}
        self.events = []
        self.state = "OPENING"
        self.cooldown = {}
        self.quiet = quiet
        self.fut_hi_at = None      # CE close when FUT last made a session high
        self.fut_lo_at = None      # PE close when FUT last made a session low
        self.fut_hi = -1e18
        self.fut_lo = 1e18
        self.broken = {}           # level name -> (price, minute idx, dir)
        self.armed_until = -1
        self.armed_dir = 0
        self.med_rng = []
        self.state_since = 0
        self.snaps = []                # per-bar micro-snapshots for delta radar
        self.rng30_rank = Rank()       # 30m range, ranked vs the day's own
        self.ctx_track = {}
        self.setup = None              # momentum-card lifecycle (spring/armed)
        self.setup_track = {}          # per-bar setup snapshot for the UI
        self.trap_ev = {"UP": {}, "DN": {}}    # trap tell -> minute last seen
        self.trap_ref = {"UP": None, "DN": None}  # extreme bar refs per side
        self.trap_live = {"UP": -999, "DN": -999}  # last minute SETTING held
        self.band_armed = {"lo": True, "hi": True}  # re-arm inside ±1σ
        self.band_last = None          # (i, kind, side, px) for the playbook
        self.oi_peak = {"CE": (0.0, -1), "PE": (0.0, -1)}  # (oi, minute) session peak
        self.peaklag_done = {"DN": -999, "UP": -999}  # extreme idx already fired
        self.ep = None                 # current detonation leg {i,dir,start,ext}
        self.marks = []                # event-born levels (kind, px, t, note)
        self.flipped = {}              # pivot -> (lvl, dir, t) after FLIP-TEST
        self.level_hits = defaultdict(list)   # pivot -> touch minutes (fights)
        self.trap_last = None          # (i, side, px) of last TRAP-SPRUNG

    # ------------------------------------------------------------- utilities

    def emit(self, i, kind, msg, every=10, data=None):
        """Record an event with a per-kind cooldown (minutes). `data` is an
        optional structured payload for the UI (additive; prose unchanged).
        Noisy narrative kinds that recur with the same message template
        collapse into the prior line as a ×N counter (within a 20m window)
        instead of spamming near-duplicate rows — killing the morning
        'two-sided writing, fade risk' TRAP/DIVERGENCE clusters."""
        if not hasattr(self, "_ev_rep"):
            self._ev_rep = {}                 # (kind, template) -> [idx, i, n]
        merge = kind in ("TRAP", "DIVERGENCE")
        tmpl = None
        if merge:
            tmpl = (kind, "".join("#" if c.isdigit() else c for c in msg))
            prev = self._ev_rep.get(tmpl)
            if prev and i - prev[1] < 20:     # same signal recurring -> bump ×N
                idx, _, n = prev[0], prev[1], prev[2] + 1
                t0, k0, m0, d0 = self.events[idx]
                self.events[idx] = (t0, k0, m0.split("  ×")[0] + f"  ×{n}", d0)
                self._ev_rep[tmpl] = [idx, i, n]
                self.cooldown[kind] = i
                return
        last = self.cooldown.get(kind, -999)
        if i - last < every:
            return
        self.cooldown[kind] = i
        t = self.fut_bars[i]["T"]
        self.events.append((t, kind, msg, data))
        if merge:
            self._ev_rep[tmpl] = [len(self.events) - 1, i, 1]
        if not self.quiet:
            print(f"  {t} [{kind}] {msg}")

    def _cross_ev(self, i, nm, lvl, dirn):
        """A pivot cross. First two crossings of a level in a 30m window emit
        BREAK; beyond that the level is being chopped, not broken, so further
        crosses collapse into a single CHOP note (breaks there are noise — the
        FIGHT episode + STAND-ASIDE verdict govern that regime instead)."""
        recent = [j for j in self.level_hits[nm] if i - j <= 30]
        if len(recent) > 2:
            self.emit(i, "CHOP",
                      f"{nm} {lvl:.0f} chopping — {len(recent)} crossings in "
                      f"{i - recent[0]}m, breaks unreliable here", every=15)
        else:
            self.emit(i, "BREAK", f"FUT closes {dirn} {nm} {lvl:.0f}", every=3)

    def set_state(self, i, new, why):
        if new != self.state:
            self.state = new
            self.state_since = i
            t = self.fut_bars[i]["T"]
            self.events.append((t, "STATE", f"{new} — {why}", None))
            if not self.quiet:
                print(f"  {t} >> STATE {new} — {why}")

    def note_detonation(self, i, sgn, px):
        """Track the current expansion leg for the episode brain. Consecutive
        detonation minutes in one direction extend the same leg. The leg's
        start anchors at the recent swing (releases fire AT the extreme, so
        anchoring at the detonation bar would measure a zero-length leg)."""
        if self.ep and self.ep["dir"] == sgn and i - self.ep["i"] <= 10:
            self.ep["i"] = i
            return
        look = self.books["FUT"].bars[-15:]
        start = (max(b["C"] for b in look) if sgn < 0
                 else min(b["C"] for b in look))
        self.ep = {"i": i, "dir": sgn, "start": start, "ext": px}

    def _set_setup(self, i, fb, dirn, kind, lvl_name, lvl_px, ref, intensity):
        """(Re)arm the momentum-card lifecycle; the newest spring supersedes.
        `ref` is the hard invalidation boundary (session extreme at spring
        time; for ARMED the pivot level tightens it)."""
        if kind == "ARMED":
            ref = min(ref, lvl_px) if dirn > 0 else max(ref, lvl_px)
        self.setup = {"i": i, "t": fb["T"], "dir": dirn, "kind": kind,
                      "status": "ARMED" if kind == "ARMED" else "LOADING",
                      "level_name": lvl_name, "level_px": round(lvl_px, 1),
                      "ref": round(ref, 1), "intensity": round(intensity, 2)}

    def nearest_level(self, price):
        b = self.fut_bars[0]
        levels = {"P": b["P"], "R1": b["R1"], "R2": b["R2"], "R3": b["R3"],
                  "S1": b["S1"], "S2": b["S2"], "S3": b["S3"]}
        name = min(levels, key=lambda k: abs(levels[k] - price))
        return name, levels[name]

    # ----------------------------------------------------------------- replay

    def run(self):
        if not self.quiet:
            b = self.fut_bars[0]
            print(f"\n=== {self.day} | pivots P {b['P']:.0f} R1 {b['R1']:.0f} "
                  f"R2 {b['R2']:.0f} S1 {b['S1']:.0f} S2 {b['S2']:.0f} ===")
        for i, fb in enumerate(self.fut_bars):
            t = fb["T"]
            cb, pb = self.ce_by_t.get(t), self.pe_by_t.get(t)
            if cb is None or pb is None:
                continue
            ff = self.books["FUT"].update(fb)
            cf = self.books["CE"].update(cb)
            pf = self.books["PE"].update(pb)
            self.med_rng.append(fb["H"] - fb["L"])
            self.minute(i, fb, cb, pb, ff, cf, pf)
        self.carry_verdict()
        return self.events

    # ------------------------------------------------------------ per minute

    def minute(self, i, fb, cb, pb, ff, cf, pf):
        mature = i >= MATURITY
        ranks_ok = i >= WARMUP

        # --- TRAP: option stretched >2-sigma inside immature bands,
        #     both books' OI building (two-sided writing sells the spike)
        if not mature and i >= 5:
            for nm, ob, of in (("CE", cb, cf), ("PE", pb, pf)):
                stretched = ob["H"] > ob["U2"] or ob["L"] < ob["D2"]
                both_building = cf["oi_slope"] > 0 and pf["oi_slope"] > 0
                if stretched and both_building:
                    self.emit(i, "TRAP",
                              f"{nm} stretched beyond 2σ in immature bands while BOTH books "
                              f"add OI (CE +{cf['oi_slope']/1000:.0f}k, PE +{pf['oi_slope']/1000:.0f}k"
                              f"/{SLOPE_W}m) — two-sided writing, fade risk", every=8,
                              data={"side": "TWO-SIDED"})

        # --- CAMPAIGN / BUYER-BUILD: strong one-book OI trend, disambiguated
        #     by what that premium does during the build
        if ranks_ok:
            for nm, of, bias_w, bias_b in (("PE", pf, "BULLISH", "BEARISH"),
                                           ("CE", cf, "BEARISH", "BULLISH")):
                if of["oi_slope_r"] > 0.9 and of["oi_slope"] > 0:
                    if of["prem_d"] < 0:
                        self.emit(i, "CAMPAIGN",
                                  f"{nm} writers pressing: OI +{of['oi_slope']/1000:.0f}k/{SLOPE_W}m "
                                  f"(rank {of['oi_slope_r']:.2f}) into falling premium → {bias_w}",
                                  every=15)
                    elif of["prem_d"] > 0:
                        self.emit(i, "BUYER-BUILD",
                                  f"{nm} buyers building: OI +{of['oi_slope']/1000:.0f}k/{SLOPE_W}m "
                                  f"while premium firms → {bias_b}", every=15)

        # --- DIVERGENCE: FUT new extreme, confirming option can't better its own best
        if mature:
            tol = 2 * median(self.med_rng[-60:])
            if fb["C"] > self.fut_hi:
                self.fut_hi = fb["C"]
                self.trap_ref["UP"] = {"i": i, "px": fb["L"], "ext": fb["C"]}
                ce_gap = self.books["CE"].max_c - cb["C"]
                if self.fut_hi_at is not None and ce_gap > tol * (cb["C"] / max(fb["C"], 1e-9)) * 8:
                    self.trap_ev["UP"]["divergence"] = i
                    self.emit(i, "DIVERGENCE",
                              f"FUT new session high {fb['C']:.0f} but CE {cb['C']:.1f} is "
                              f"{ce_gap:.1f} under its own peak — upside not being paid for",
                              every=12, data={"side": "BULL"})
                self.fut_hi_at = cb["C"]
            if fb["C"] < self.fut_lo:
                self.fut_lo = fb["C"]
                self.trap_ref["DN"] = {"i": i, "px": fb["H"], "ext": fb["C"]}
                pe_gap = self.books["PE"].max_c - pb["C"]
                if self.fut_lo_at is not None and pe_gap > tol * (pb["C"] / max(fb["C"], 1e-9)) * 8:
                    self.trap_ev["DN"]["divergence"] = i
                    self.emit(i, "DIVERGENCE",
                              f"FUT new session low {fb['C']:.0f} but PE {pb['C']:.1f} is "
                              f"{pe_gap:.1f} under its own peak — downside not being paid for",
                              every=12, data={"side": "BEAR"})
                self.fut_lo_at = pb["C"]

        # --- TRAP lifecycle (mature session): independent tells corroborating
        #     at an extreme -> TRAP-SETTING; price closing back through the
        #     bar that made the extreme -> TRAP-SPRUNG (the failed break).
        #     Evidence comes only from signals the base engine already fires;
        #     printed base lines are untouched (new kinds are additive).
        if mature:
            if ff["z"] > 0.5 and cf["oi_slope"] > 0 and cf["prem_d"] < 0 \
                    and cf["oi_slope_r"] > 0.6:
                self.trap_ev["UP"]["writers"] = i      # calls sold into the high
            if ff["z"] < -0.5 and pf["oi_slope"] > 0 and pf["prem_d"] < 0 \
                    and pf["oi_slope_r"] > 0.6:
                self.trap_ev["DN"]["writers"] = i      # puts sold into the low
            tol3t = 3 * median(self.med_rng[-60:])
            for side, word, who in (("UP", "BULL", "longs"),
                                    ("DN", "BEAR", "shorts")):
                ref = self.trap_ref[side]
                if not ref:
                    continue
                # tells must corroborate within 25m (distinct kinds, not
                # repeats of one signal on cooldown)
                votes = sorted(k for k, j in self.trap_ev[side].items()
                               if i - j <= 25)
                if len(votes) >= 2 and abs(fb["C"] - ref["ext"]) <= tol3t:
                    self.trap_live[side] = i
                    self.emit(i, "TRAP-SETTING",
                              f"{word} TRAP SETTING near {ref['ext']:.0f} — "
                              f"{len(votes)} independent tells ({', '.join(votes)}) "
                              f"— the extreme is not being confirmed by the books",
                              every=10, data={"side": word, "votes": votes,
                                              "ref_px": round(ref["ext"], 1)})
                crossed = fb["C"] < ref["px"] if side == "UP" else fb["C"] > ref["px"]
                if i - self.trap_live[side] <= 25 and i > ref["i"] and crossed:
                    self.trap_last = (i, word, ref["px"])
                    self.marks.append(("TRAP", ref["px"], fb["T"],
                                       f"{word} trap sprung {fb['T']}"))
                    self.emit(i, "TRAP-SPRUNG",
                              f"{word} TRAP SPRUNG — FUT closes back "
                              f"{'below' if side == 'UP' else 'above'} {ref['px']:.0f} "
                              f"(the bar that made the extreme); late {who} trapped",
                              every=15, data={"side": word,
                                              "ref_px": round(ref["px"], 1)})
                    self.trap_ev[side] = {}
                    self.trap_live[side] = -999

        # --- OI-PEAK-LAG: the losing side's conviction peaking AFTER the
        #     extreme (Jul 20 ground truth: CE book peaked 26.5M nine minutes
        #     after the 24121 low; its forced unwind fueled the +78pt squeeze).
        #     Maximum positioning arriving after the move stopped = reversal
        #     fuel; the first unwind downturn is the causal trigger.
        for _nm, _ob in (("CE", cb), ("PE", pb)):
            if _ob["OI"] > self.oi_peak[_nm][0]:
                self.oi_peak[_nm] = (_ob["OI"], i)
        if mature:
            for side, nm2, of2, ext_word, dirn in (
                    ("DN", "CE", cf, "low", "UPWARD"),
                    ("UP", "PE", pf, "high", "DOWNWARD")):
                ref = self.trap_ref[side]
                pk, pj = self.oi_peak[nm2]
                bbars = self.books[nm2].bars
                # trigger = first SUSTAINED unwind after the late peak (two
                # consecutive negative slopes) — a rank gate here fires too
                # late; the violent unwind IS the squeeze, not the warning
                turning = (of2["oi_slope"] < 0 and len(bbars) >= 2
                           and bbars[-2]["f"]["oi_slope"] < 0)
                if (ref and self.peaklag_done[side] != ref["i"]
                        and 3 <= i - ref["i"] <= 45
                        and pj > ref["i"]
                        and turning):
                    self.peaklag_done[side] = ref["i"]
                    self.trap_ev[side]["peak-lag"] = i
                    self.emit(i, "OI-PEAK-LAG",
                              f"{nm2} book peaked {pk/1e6:.1f}M {pj - ref['i']}m AFTER "
                              f"the {ref['ext']:.0f} {ext_word} and is now unwinding "
                              f"({of2['oi_slope']/1000:.0f}k/{SLOPE_W}m) — maximum "
                              f"conviction arrived after the move stopped; this book "
                              f"is reversal fuel → {dirn}", every=10,
                              data={"side": side, "book": nm2,
                                    "peak_m": round(pk / 1e6, 1),
                                    "lag": pj - ref["i"],
                                    "ref_px": round(ref["ext"], 1)})

        # --- PRESS: both books rotating one direction ahead of price
        if ranks_ok:
            ce_r, pe_r = cf["oi_slope_r"], pf["oi_slope_r"]
            if (ce_r > 0.6 and cf["oi_slope"] > 0 and cf["prem_d"] < 0
                    and pe_r > 0.6 and pf["oi_slope"] < 0 and pf["prem_d"] > 0):
                self.emit(i, "PRESS",
                          f"BEARISH rotation: CE writers add (+{cf['oi_slope']/1000:.0f}k) while "
                          f"PE shorts evacuate ({pf['oi_slope']/1000:.0f}k) — books lean down "
                          f"before price", every=12)
            if (pe_r > 0.6 and pf["oi_slope"] > 0 and pf["prem_d"] < 0
                    and ce_r > 0.6 and cf["oi_slope"] < 0 and cf["prem_d"] > 0):
                self.emit(i, "PRESS",
                          f"BULLISH rotation: PE writers add (+{pf['oi_slope']/1000:.0f}k) while "
                          f"CE shorts evacuate ({cf['oi_slope']/1000:.0f}k) — books lean up "
                          f"before price", every=12)

        # --- SPRING / ARMED: the extreme is being disbelieved.
        #     Location-gated by the defended strike: a bullish spring only exists
        #     while price still holds the strike and the put book that defends it
        #     remains intact (and mirror for bearish). Without that, the same OI
        #     signature is an evacuation (PRESS), not disbelief.
        if ranks_ok and mature:
            lvl_name, lvl = self.nearest_level(fb["C"])
            tol3 = 3 * median(self.med_rng[-60:])
            near_lvl = abs(fb["C"] - lvl) < tol3
            compressing = ff["bw_r"] < 0.45
            pe_peak = max(b["OI"] for b in self.books["PE"].bars)
            ce_peak = max(b["OI"] for b in self.books["CE"].bars)
            bull_loc = self.strike is None or (
                fb["C"] >= self.strike - tol3 and pb["OI"] > 0.6 * pe_peak)
            bear_loc = self.strike is None or (
                fb["C"] <= self.strike + tol3 and cb["OI"] > 0.6 * ce_peak)
            # bullish: FUT pressed below VWAP, PE (winning side) dumping OI, CE adding
            if (bull_loc and ff["z"] < -0.6 and pf["oi_slope"] < 0
                    and pf["oi_slope_r"] > 0.75 and cf["oi_slope"] > 0):
                self.trap_ev["DN"]["spring"] = i   # dip disbelieved = bear-trap tell
                msg = (f"dip disbelieved: PE OI {pf['oi_slope']/1000:.0f}k/{SLOPE_W}m "
                       f"(rank {pf['oi_slope_r']:.2f}) while FUT z={ff['z']:.1f}; CE writers "
                       f"adding +{cf['oi_slope']/1000:.0f}k at the low")
                ref_lo = min(self.fut_lo, fb["L"])
                if near_lvl:
                    self.armed_until, self.armed_dir = i + 45, +1
                    self._set_setup(i, fb, +1, "ARMED", lvl_name, lvl, ref_lo,
                                    pf["oi_slope_r"])
                    self.emit(i, "ARMED", f"BULLISH SPRING at {lvl_name} {lvl:.0f} — {msg}"
                              + ("; bands compressing" if compressing else ""), every=15,
                              data={"side": "UP", "level_name": lvl_name,
                                    "level_px": round(lvl, 1)})
                else:
                    self._set_setup(i, fb, +1, "SPRING", "dip low", ref_lo, ref_lo,
                                    pf["oi_slope_r"])
                    self.emit(i, "SPRING", "bullish — " + msg, every=15,
                              data={"side": "UP", "level_name": "dip low",
                                    "level_px": round(ref_lo, 1)})
            # bearish mirror
            if (bear_loc and ff["z"] > 0.6 and cf["oi_slope"] < 0
                    and cf["oi_slope_r"] > 0.75 and pf["oi_slope"] > 0):
                self.trap_ev["UP"]["spring"] = i   # rally disbelieved = bull-trap tell
                msg = (f"rally disbelieved: CE OI {cf['oi_slope']/1000:.0f}k/{SLOPE_W}m "
                       f"(rank {cf['oi_slope_r']:.2f}) while FUT z={ff['z']:.1f}; PE writers "
                       f"adding +{pf['oi_slope']/1000:.0f}k at the high")
                ref_hi = max(self.fut_hi, fb["H"])
                if near_lvl:
                    self.armed_until, self.armed_dir = i + 45, -1
                    self._set_setup(i, fb, -1, "ARMED", lvl_name, lvl, ref_hi,
                                    cf["oi_slope_r"])
                    self.emit(i, "ARMED", f"BEARISH SPRING at {lvl_name} {lvl:.0f} — {msg}"
                              + ("; bands compressing" if compressing else ""), every=15,
                              data={"side": "DN", "level_name": lvl_name,
                                    "level_px": round(lvl, 1)})
                else:
                    self._set_setup(i, fb, -1, "SPRING", "swing high", ref_hi, ref_hi,
                                    cf["oi_slope_r"])
                    self.emit(i, "SPRING", "bearish — " + msg, every=15,
                              data={"side": "DN", "level_name": "swing high",
                                    "level_px": round(ref_hi, 1)})

        # --- IGNITION: synchronized detonation across the three books
        if ranks_ok:
            if ff["vol_r"] > 0.97 and cf["vol_r"] > 0.97 and pf["vol_r"] > 0.97 \
                    and ff["rng_r"] > 0.9:
                direction = "UP" if fb["C"] > fb["O"] else "DOWN"
                self.note_detonation(i, +1 if direction == "UP" else -1, fb["C"])
                armed_note = ""
                if i <= self.armed_until and (
                        (direction == "UP") == (self.armed_dir > 0)):
                    armed_note = " — FIRES A LIVE SPRING"
                su = self.setup
                if (su and su["status"] in ("LOADING", "ARMED")
                        and i <= su["i"] + 45
                        and (direction == "UP") == (su["dir"] > 0)):
                    su["status"], su["fired"] = "FIRED", fb["T"]
                self.emit(i, "IGNITION",
                          f"{direction}: all three books detonate (vol ranks FUT {ff['vol_r']:.2f} "
                          f"CE {cf['vol_r']:.2f} PE {pf['vol_r']:.2f}), FUT range rank "
                          f"{ff['rng_r']:.2f}{armed_note}", every=5)

        # --- CLIMAX: 3-sigma overshoot + losing-side OI cliff + volume extreme
        if ranks_ok and mature:
            for nm, ob, of, marks in (("CE", cb, cf, "TOP"), ("PE", pb, pf, "LOW")):
                overshoot = ob["H"] > ob["U3"]
                cliff = of["oi_slope"] < 0 and of["oi_slope_r"] > 0.9
                if overshoot and cliff and of["vol_r"] > 0.9:
                    self.emit(i, "CLIMAX",
                              f"{nm} beyond 3σ with OI cliff ({of['oi_slope']/1000:.0f}k/"
                              f"{SLOPE_W}m, rank {of['oi_slope_r']:.2f}) on extreme volume — "
                              f"covering climax, likely {marks} marker", every=10)

        # --- ABSORPTION: extreme effort, no result
        if ranks_ok and ff["vol_r"] > 0.95 and ff["rng_r"] < 0.55:
            side = "sellers" if fb["C"] < fb["O"] else "buyers"
            self.trap_ev["UP" if side == "buyers" else "DN"]["absorption"] = i
            tolm = 2 * median(self.med_rng[-60:])
            if not any(k == "ABS" and abs(p - fb["C"]) <= tolm
                       for k, p, *_ in self.marks[-4:]):
                self.marks.append(("ABS", fb["C"], fb["T"],
                                   f"{side} absorbed {fb['T']}"))
            self.emit(i, "ABSORPTION",
                      f"FUT vol rank {ff['vol_r']:.2f} but range rank {ff['rng_r']:.2f} — "
                      f"{side} hitting a wall near {fb['C']:.0f}", every=15)

        # --- pivot breaks and FLIP-TESTs
        if mature:
            b0 = self.fut_bars[0]
            tol = median(self.med_rng[-60:])
            for nm in ("R1", "R2", "R3", "S1", "S2", "P"):
                lvl = b0[nm]
                prev_c = self.fut_bars[i - 1]["C"] if i else fb["O"]
                if prev_c < lvl <= fb["C"] and nm not in self.broken:
                    self.broken[nm] = (lvl, i, +1)
                    self.level_hits[nm].append(i)
                    self._cross_ev(i, nm, lvl, "above")
                elif prev_c > lvl >= fb["C"] and nm not in self.broken:
                    self.broken[nm] = (lvl, i, -1)
                    self.level_hits[nm].append(i)
                    self._cross_ev(i, nm, lvl, "below")
            for nm, (lvl, j, d) in list(self.broken.items()):
                if i - j in range(3, 46) and abs(fb["L" if d > 0 else "H"] - lvl) < tol:
                    ok = fb["C"] > lvl if d > 0 else fb["C"] < lvl
                    if ok:
                        self.flipped[nm] = (lvl, d, fb["T"])
                        self.level_hits[nm].append(i)
                        self.emit(i, "FLIP-TEST",
                                  f"{nm} {lvl:.0f} retested from {'above' if d > 0 else 'below'} "
                                  f"and holding — level flipped", every=12)
                        del self.broken[nm]

        # --- gamma layer (separate; emits only GAMMA-*/SQUEEZE-* events).
        # Runs from bar 0 so session-open OI/premium references are the true
        # open (events remain gated on maturity inside the layer).
        self.gamma.update(i, fb, cb, pb, ff, cf, pf, mature)

        # --- BAND-REVERSAL / BAND-BREAK: the operator's core setup, validated
        #     on 54 unseen days / 219 tags: naked ±2σ fade 55-58% WR as a ~1R
        #     scalp; edge concentrates near expiry + pumped sold-side IV;
        #     DIES in negative gamma (fade 25%, continuation 75%) → veto.
        #     Re-arms only after price closes back inside ±1σ.
        if mature:
            if abs(ff["z"]) < 1:
                self.band_armed["lo"] = self.band_armed["hi"] = True
            netw = self.gamma.w["CE"] + self.gamma.w["PE"]
            for sgn, key, tag, deep in (
                    (+1, "lo", fb["L"] <= fb["D2"], fb["L"] <= fb["D3"]),
                    (-1, "hi", fb["H"] >= fb["U2"], fb["H"] >= fb["U3"])):
                if not (self.band_armed[key] and tag):
                    continue
                self.band_armed[key] = False
                sold = "PE" if sgn > 0 else "CE"
                ivr = self.gamma.iv_r[sold]
                word = "-2σ" if sgn > 0 else "+2σ"
                px = fb["L"] if sgn > 0 else fb["H"]
                side = "UP" if sgn > 0 else "DN"
                t_d = self.gamma.t
                tnote = (" · EXPIRY WINDOW — edge strongest" if t_d <= 1.5 else
                         " · far from expiry — edge historically flat, size down"
                         if t_d >= 4 else "")
                if netw < -0.3:
                    self.band_last = (i, "BAND-BREAK", side, px, None)
                    self.emit(i, "BAND-BREAK",
                              f"{word} tag at {px:.0f} in NEGATIVE gamma (net writer "
                              f"{netw:+.2f}) — do NOT fade; dealer hedging chases, "
                              f"continuation favored", every=8,
                              data={"side": side, "px": round(px, 1),
                                    "netw": round(netw, 2)})
                else:
                    # confidence tier from the three validated edge
                    # concentrators (expression backtest): near-expiry is
                    # dominant, then pumped sold-side IV, then deep 3σ.
                    score = (2 if t_d <= 1.5 else -2 if t_d >= 4 else 0)
                    score += 1 if (ivr is not None and ivr >= 0.7) else 0
                    score += 1 if deep else 0
                    tier = "HIGH" if score >= 3 else "MED" if score >= 1 else "LOW"
                    self.band_last = (i, "BAND-REVERSAL", side, px, tier)
                    conv = "DEEP 3σ, high conviction" if deep else "standard"
                    ivtxt = (f"; sell-side IV p{int(ivr*100)}"
                             if ivr is not None else "")
                    self.emit(i, "BAND-REVERSAL",
                              f"[{tier}] {word} tag at {px:.0f} — fade armed ({conv}), "
                              f"net writer {netw:+.2f} dampens{ivtxt} → scalp ~1R "
                              f"{'up' if sgn > 0 else 'down'}; seller expression: "
                              f"sell {sold}{tnote}", every=8,
                              data={"side": side, "px": round(px, 1),
                                    "deep": deep, "netw": round(netw, 2),
                                    "iv_rank": round(ivr, 2) if ivr is not None
                                    else None, "sold": sold, "tier": tier})

        # --- state machine
        if i >= MATURITY:
            look = 60
            recent = self.books["FUT"].bars[-look:]
            above = sum(1 for b in recent if b["C"] > b["VWAP"]) / len(recent)
            outside_core = sum(1 for b in recent[-20:]
                               if abs(b["f"]["z"]) > 1) / min(20, len(recent))
            if i <= self.armed_until:
                self.set_state(i, "ARMED",
                               f"spring live ({'bullish' if self.armed_dir > 0 else 'bearish'})")
            elif above > 0.8 and outside_core > 0.5:
                self.set_state(i, "TREND-UP",
                               f"{above:.0%} of last hour above VWAP, riding upper bands")
            elif above < 0.2 and outside_core > 0.5:
                self.set_state(i, "TREND-DOWN",
                               f"{1-above:.0%} of last hour below VWAP, riding lower bands")
            elif ff["bw_r"] < 0.3:
                self.set_state(i, "COILING", f"bandwidth rank {ff['bw_r']:.2f} — energy storing")
            else:
                self.set_state(i, "BALANCE", "two-sided around VWAP — scalp edges only")

        # --- momentum setup lifecycle. SPRING-FAIL is the only new printed
        #     line; base state machine (armed_until) is deliberately untouched
        #     so existing STATE transitions cannot shift.
        su = self.setup
        if su and su["status"] in ("LOADING", "ARMED"):
            if i > su["i"] + 45:
                su["status"] = "EXPIRED"
            elif su["dir"] > 0 and fb["C"] < su["ref"]:
                su["status"], su["died"] = "INVALIDATED", fb["T"]
                self.emit(i, "SPRING-FAIL",
                          f"bullish spring {su['t']} invalidated — FUT closed below "
                          f"{su['ref']:.0f}, the low it sprang from", every=5,
                          data={"side": "UP"})
            elif su["dir"] < 0 and fb["C"] > su["ref"]:
                su["status"], su["died"] = "INVALIDATED", fb["T"]
                self.emit(i, "SPRING-FAIL",
                          f"bearish spring {su['t']} invalidated — FUT closed above "
                          f"{su['ref']:.0f}, the high it sprang from", every=5,
                          data={"side": "DN"})
        if su:
            self.setup_track[fb["T"]] = {
                "status": su["status"], "dir": "UP" if su["dir"] > 0 else "DOWN",
                "t0": su["t"], "kind": su["kind"],
                "level_name": su["level_name"], "level_px": su["level_px"],
                "ref": su["ref"], "intensity": su["intensity"],
                "comp": round(1 - ff["bw_r"], 2),
                **({"died": su["died"]} if "died" in su else {}),
                **({"fired": su["fired"]} if "fired" in su else {}),
            }

        # --- context block (per-bar JSON only; prints nothing, alters nothing)
        self.context(i, fb, cb, pb, ff, cf, pf)

    def context(self, i, fb, cb, pb, ff, cf, pf):
        """Regime banner data: time-quantified window stats, breadth votes,
        tradeability verdict, and the delta radar (what's shifting while
        price stands still). Additive JSON; no events, no state changes."""
        g = self.gamma.track.get(fb["T"], {})
        self.snaps.append({
            "w_ce": g.get("w_ce", 0.0), "w_pe": g.get("w_pe", 0.0),
            "bw_r": ff["bw_r"], "z": ff["z"],
            "s_ce": 1 if cf["oi_slope"] > 0 else -1,
            "s_pe": 1 if pf["oi_slope"] > 0 else -1,
        })
        w = min(30, i + 1)
        fbars = self.books["FUT"].bars[-w:]
        rng30 = max(b["H"] for b in fbars) - min(b["L"] for b in fbars)
        rng_r = self.rng30_rank.rank(rng30)
        vol30 = sum(b["f"]["vol_r"] for b in fbars) / w
        inside1 = sum(1 for b in fbars if abs(b["f"]["z"]) <= 1) / w
        age = i - self.state_since
        regime = g.get("regime", "NEUTRAL")
        r_age = i - getattr(self.gamma, "regime_since", 0)

        # breadth: cross-book direction votes (z, CE prem, PE prem inverted,
        # MM regime lean) — agreement, not magnitude
        lean = {"FLOOR": 1, "AMPLIFIED-UP": 1,
                "CEILING": -1, "AMPLIFIED-DOWN": -1}.get(regime, 0)
        votes = ((1 if ff["z"] > 0.15 else -1 if ff["z"] < -0.15 else 0)
                 + (1 if cf["prem_d"] > 0 else -1 if cf["prem_d"] < 0 else 0)
                 + (-1 if pf["prem_d"] > 0 else 1 if pf["prem_d"] < 0 else 0)
                 + lean)
        breadth = ("STRONG BULL" if votes >= 3 else "LEAN BULL" if votes >= 1
                   else "STRONG BEAR" if votes <= -3
                   else "LEAN BEAR" if votes <= -1 else "MIXED")

        # --- episode brain: the story of the current leg, not just this bar
        med = median(self.med_rng[-60:]) or 1.0
        C = fb["C"]
        if self.ep:
            self.ep["ext"] = (min(self.ep["ext"], C) if self.ep["dir"] < 0
                              else max(self.ep["ext"], C))
        episode = ""
        if self.ep and i - self.ep["i"] <= 40:
            leg = abs(self.ep["start"] - self.ep["ext"])
            if leg >= 3 * med:      # a real leg, sized vs the day's own bars
                retr = abs(C - self.ep["ext"]) / leg
                prev = self.ep.get("phase")
                # sticky phase boundaries — hysteresis kills minute flapping;
                # SPENT is terminal for a leg (only a fresh detonation resets)
                if prev == "SPENT" or retr > 0.55:
                    phase = "SPENT"
                elif retr < (0.2 if prev == "STALLING" else 0.3):
                    phase = "RUNNING"
                else:
                    phase = "STALLING"
                self.ep["phase"] = phase
                word = "DOWN" if self.ep["dir"] < 0 else "UP"
                path = f"{self.ep['start']:.0f}→{self.ep['ext']:.0f}"
                if phase == "SPENT":
                    episode = (f"MOVE SPENT — {word} leg {path} was "
                               f"{'bought back' if self.ep['dir'] < 0 else 'sold back'} "
                               f"({min(retr, 1.5):.0%} retraced) — don't chase it")
                elif phase == "RUNNING":
                    episode = f"MOVE RUNNING — {word} leg {path} live, pullbacks shallow"
                else:
                    episode = f"MOVE STALLING — {word} leg {path}, half given back"
        if not episode and self.trap_last and i - self.trap_last[0] <= 20:
            episode = (f"TRAP UNWINDING — {self.trap_last[1]} extreme faded, "
                       f"ref {self.trap_last[2]:.0f}")
        if not episode:
            for nm, hits in self.level_hits.items():
                h = [j for j in hits if i - j <= 35]
                if len(h) >= 3:
                    episode = (f"FIGHT AT {nm} {self.fut_bars[0][nm]:.0f} — "
                               f"{len(h)} crossings in {i - h[0]}m")
                    break

        # --- event-born structure: today's map, not yesterday's math
        cands = [("session low", self.fut_lo), ("session high", self.fut_hi)]
        for _k, px, _t, note in self.marks[-6:]:
            cands.append((note, px))
        for nm, (lvl, dd, _t) in self.flipped.items():
            cands.append((f"{nm} flipped {'support' if dd > 0 else 'resistance'}", lvl))
        if self.gamma.k:
            if self.gamma.w["CE"] > 0.5 and self.gamma.k > C - med:
                cands.append((f"CE wall {cb['OI']/1e6:.0f}M", self.gamma.k))
            if self.gamma.w["PE"] > 0.5 and self.gamma.k < C + med:
                cands.append((f"PE wall {pb['OI']/1e6:.0f}M", self.gamma.k))
        below = [(n, p) for n, p in cands if p < C - med]
        above = [(n, p) for n, p in cands if p > C + med]
        floor = max(below, key=lambda x: x[1]) if below else None
        cap = min(above, key=lambda x: x[1]) if above else None
        loc = ""
        if floor and cap:
            pos = (C - floor[1]) / max(cap[1] - floor[1], 1e-9)
            where = ("at the lower edge" if pos < 0.3 else
                     "at the upper edge" if pos > 0.7 else
                     "mid-box — worst location, no defined risk")
            loc = (f"box {floor[1]:.0f} ({floor[0]}) – {cap[1]:.0f} ({cap[0]}) · "
                   f"{where}")

        # tradeability verdict — the "should I even be trading" answer.
        # A trend label alone is NOT a green light: if the 30m range has
        # compressed into the bottom third of the day, or dealers have the
        # tape PINNED, the "trend" is really a coil — gate GO off both so the
        # banner can't read GO while price is dead (the 21-Jul p0-range case).
        compressed = rng_r < 0.30
        trend = self.state in ("TREND-UP", "TREND-DOWN")
        if (trend or regime.startswith("AMPLIFIED")) \
                and not compressed and regime != "PINNED":
            verdict, vwhy = "GO", "one-sided tape / dealer hedging amplifies"
        elif self.state == "ARMED":
            verdict, vwhy = "READY", "spring loaded — trigger defined"
        elif self.state == "COILING":
            verdict, vwhy = "WAIT", "energy storing — prepare, don't chase"
        elif regime == "PINNED" or (self.state == "BALANCE" and rng_r < 0.35):
            verdict, vwhy = "STAND ASIDE", "pin/chop — edges only, no chasing"
        elif trend and compressed:
            verdict, vwhy = ("WAIT",
                             f"trend stalled — range p{int(rng_r*100)}, "
                             f"compression not continuation")
        else:
            verdict, vwhy = "CAUTION", "no edge defined right now"
        if episode.startswith("MOVE SPENT"):
            verdict, vwhy = "SPENT", "leg released and given back — don't chase"

        # --- playbook: if-then triggers from the map + regime
        plays = []
        if self.band_last and i - self.band_last[0] <= 20:
            _bi, bk, bs, bpx, btier = self.band_last
            if bk == "BAND-REVERSAL":
                plays.append(f"[{btier}] FADE the {bpx:.0f} band tag — scalp ~1R "
                             f"{'up' if bs == 'UP' else 'down'}; seller: sell "
                             f"{'PE' if bs == 'UP' else 'CE'}")
            else:
                plays.append(f"NO FADE at {bpx:.0f} — negative gamma; "
                             f"continuation only")
        if episode.startswith("MOVE SPENT"):
            plays.append("DON'T CHASE — the leg paid out; wait for a box edge")
        if regime.startswith("AMPLIFIED"):
            dd_ = "dips" if regime.endswith("UP") else "bounces"
            plays.append(f"RIDE the hedge flow — {dd_} toward VWAP are entries, not exits")
        if cap:
            inv = " · invalid if CE SQUEEZE-RISK lights" if "wall" in cap[0] else ""
            plays.append(f"FADE a test of {cap[1]:.0f} ({cap[0]}){inv}")
        if floor:
            plays.append(f"BREAK of {floor[1]:.0f} ({floor[0]}) needs vol rank >0.9 — "
                         f"invalid on instant reclaim")
        plays = plays[:3]

        # delta radar: what actually changed in the last 15 minutes
        flips = []
        if i >= 15:
            p = self.snaps[i - 15]
            n = self.snaps[i]
            if abs(n["w_pe"] - p["w_pe"]) >= 0.15:
                flips.append(f"PE writer score {p['w_pe']:+.2f}→{n['w_pe']:+.2f}")
            if abs(n["w_ce"] - p["w_ce"]) >= 0.15:
                flips.append(f"CE writer score {p['w_ce']:+.2f}→{n['w_ce']:+.2f}")
            if n["s_ce"] != p["s_ce"]:
                flips.append(f"CE OI flow flipped {'build' if n['s_ce']>0 else 'unwind'}")
            if n["s_pe"] != p["s_pe"]:
                flips.append(f"PE OI flow flipped {'build' if n['s_pe']>0 else 'unwind'}")
            if abs(n["bw_r"] - p["bw_r"]) >= 0.2:
                flips.append(f"bands {'compressing' if n['bw_r']<p['bw_r'] else 'expanding'} "
                             f"({int(p['bw_r']*100)}→{int(n['bw_r']*100)} pctile)")
            if (p["z"] < 0) != (n["z"] < 0) and abs(n["z"] - p["z"]) > 0.3:
                flips.append(f"VWAP side flip z {p['z']:+.1f}→{n['z']:+.1f}")

        line = (f"{self.state} {age}m · 30m range {rng30:.0f} pts "
                f"(p{int(rng_r*100)}) · vol {int(vol30*100)}% of day · "
                f"{int(inside1*100)}% inside ±1σ · MM {regime} {r_age}m")

        self.ctx_track[fb["T"]] = {
            "verdict": verdict, "vwhy": vwhy, "breadth": breadth,
            "line": line, "flips": flips[:4], "age": age,
            "rng30": round(rng30, 1), "rng_r": round(rng_r, 2),
            "vol30": round(vol30, 2), "inside1": round(inside1, 2),
            "z": round(ff["z"], 2), "bw_r": round(ff["bw_r"], 2),
            "iv_ce": round(self.gamma.iv["CE"], 4) if self.gamma.iv["CE"] else None,
            "iv_pe": round(self.gamma.iv["PE"], 4) if self.gamma.iv["PE"] else None,
            "ivr_ce": round(self.gamma.iv_r["CE"], 2)
            if self.gamma.iv_r["CE"] is not None else None,
            "ivr_pe": round(self.gamma.iv_r["PE"], 2)
            if self.gamma.iv_r["PE"] is not None else None,
            "pin": ({"k": self.gamma.k, "dist": round(C - self.gamma.k),
                     "regime": regime} if self.gamma.k else None),
            "t_exp": round(self.gamma.t, 2),
            "episode": episode, "loc": loc, "plays": plays,
            "floor": [floor[0], round(floor[1], 1)] if floor else None,
            "cap": [cap[0], round(cap[1], 1)] if cap else None,
        }

    # -------------------------------------------------------------- end of day

    def carry_verdict(self):
        out = []
        for nm in ("CE", "PE"):
            bars = self.books[nm].bars
            start, end = bars[0]["OI"], bars[-1]["OI"]
            peak = max(b["OI"] for b in bars)
            build, kept = peak - start, end - start
            ratio = kept / build if build > 0 else 0.0
            out.append((nm, start, peak, end, ratio))
        ce, pe = out
        # On expiry day the tracked weekly CE/PE SETTLE at 15:30 — their OI
        # does not carry to the next session, so an overnight directional
        # "carry" read from option-OI retention is meaningless. Report the
        # settlement + where it closed vs the strike instead.
        if self.gamma.t <= 0.5:
            close = self.fut_bars[-1]["C"]
            pin = self.gamma.k
            rel = (" — pinned to the strike" if pin and abs(close - pin) <= 30
                   else f" — closed {close - pin:+.0f} vs strike" if pin else "")
            msg = (f"EXPIRY SETTLEMENT — {self.strike:.0f} CE/PE expire at "
                   f"close{rel}; no option OI carries overnight. Book resets "
                   f"next session on a fresh weekly.")
            self.events.append(("15:29", "CARRY", msg, None))
            if not self.quiet:
                print(f"  15:29 [CARRY] {msg}")
            return
        diff = pe[4] - ce[4]      # which book kept its build overnight
        bias = "NEUTRAL"
        if diff > 0.35:
            bias = "BULLISH carry"
        elif diff < -0.35:
            bias = "BEARISH carry"
        msg = (f"CE kept {ce[4]:.0%} of its intraday build "
               f"({ce[1]/1e6:.1f}M→peak {ce[2]/1e6:.1f}M→close {ce[3]/1e6:.1f}M) | "
               f"PE kept {pe[4]:.0%} ({pe[1]/1e6:.1f}M→{pe[2]/1e6:.1f}M→{pe[3]/1e6:.1f}M) "
               f"→ {bias} into next session")
        self.events.append(("15:29", "CARRY", msg, None))
        if not self.quiet:
            print(f"  15:29 [CARRY] {msg}")


# ------------------------------------------------------------- JSON export

def session_json(sess):
    """Compact per-minute timeline of a finished Session for the UI."""
    b0 = sess.fut_bars[0]
    out = {
        "day": sess.day,
        "pivots": {k: b0[k] for k in ("P", "R1", "R2", "R3", "S1", "S2", "S3")},
        "strike": sess.strike,
        "bars": [],
        "events": [dict(t=t, kind=k, msg=m, **({"data": d} if d else {}))
                   for t, k, m, d in sess.events],
    }
    for name in ("FUT", "CE", "PE"):
        pass
    fut_by_t = {b["T"]: b for b in sess.books["FUT"].bars}
    ce_by_t = {b["T"]: b for b in sess.books["CE"].bars}
    pe_by_t = {b["T"]: b for b in sess.books["PE"].bars}
    for t, fb in fut_by_t.items():
        cb, pb = ce_by_t.get(t), pe_by_t.get(t)
        if cb is None or pb is None:
            continue
        row = {"t": t}
        for key, bar in (("fut", fb), ("ce", cb), ("pe", pb)):
            f = bar.get("f", {})
            row[key] = {
                "o": bar["O"], "h": bar["H"], "l": bar["L"], "c": bar["C"],
                "vwap": round(bar["VWAP"], 2),
                "u1": round(bar["U1"], 2), "d1": round(bar["D1"], 2),
                "u2": round(bar["U2"], 2), "d2": round(bar["D2"], 2),
                "u3": round(bar["U3"], 2), "d3": round(bar["D3"], 2),
                "oi": bar["OI"], "v": bar["V"],
                "z": round(f.get("z", 0), 2),
                "vol_r": round(f.get("vol_r", 0), 2),
                "oi_slope": round(f.get("oi_slope", 0)),
                "oi_r": round(f.get("oi_slope_r", 0), 2),
                "prem_d": round(f.get("prem_d", 0), 2),
                "bw_r": round(f.get("bw_r", 0), 2),
            }
        g = sess.gamma.track.get(t)
        if g:
            row["gamma"] = g
        c = sess.ctx_track.get(t)
        if c:
            row["ctx"] = c
        su = sess.setup_track.get(t)
        if su:
            row["setup"] = su
        out["bars"].append(row)
    return out


# ---------------------------------------------------------------------- main

def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "data"
    strike = float(sys.argv[2]) if len(sys.argv) > 2 else None
    fut = load(f"{base}/FUT_3day.csv")
    ce = load(f"{base}/CE_3day.csv")
    pe = load(f"{base}/PE_3day.csv")
    expiry_dom = 21   # instrument metadata: weekly expiry day-of-month (Jul 21)
    for day in sorted(fut, key=lambda d: (d.split()[0], int(d.split()[1]))):
        if day in ce and day in pe:
            t_days = max(expiry_dom - int(day.split()[1]), 0) + 0.25
            Session(day, fut[day], ce[day], pe[day], strike=strike,
                    t_days=t_days).run()


if __name__ == "__main__":
    main()
