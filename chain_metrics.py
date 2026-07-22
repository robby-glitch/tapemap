"""Full option-chain analytics: writer scores, dealer GEX, max pain, PCR,
IV surface and a chain-based squeeze score.

TapeMap chain layer (architecture boundary: pure computation, stdlib only,
no I/O -- mirrors gamma.py). Consumed by chain_live.py / server.py; never
imported by engine.py (invariant: the gamma/chain layer never modifies base
signal logic).

Snapshot contract (produced by chain_live.normalize / the mock fixture):
    {"ts": "HH:MM:SS", "sec": int_seconds_of_day, "spot": float, "atm": int,
     "strikes": [{"k": int,
                  "ce": {"ltp","oi","oi_chg","iv","vol","bid","ask","avg",
                         "gamma","delta"},        # iv as FRACTION (0.14)
                  "pe": {...}}, ...]}             # gamma/delta/avg may be None

ChainState is stateful-but-pure: deterministic given the snapshot sequence.
Writer-score convention matches engine.GammaLayer / the UI's OI-episode
classifier:
    dOI>0, prem down -> writers add       dOI>0, prem up   -> buyers add
    dOI<0, prem up   -> writers cover     dOI<0, prem down -> longs bail
w in [-1,1]: +1 = writer-built book (dealers LONG gamma there),
             -1 = buyer-built (dealers SHORT gamma). Same dealer-sign
convention gamma.gex_profile consumes.
"""

from collections import deque

from gamma import gamma as bs_gamma, gex_profile

PREM_TICK = 0.05        # ignore premium moves below one tick when classifying
CLASSIFY_S = 60         # classify OI flow on 1-minute buckets (5s deltas are
                        # noise: spot wiggle swamps theta/IV drift intraminute)
W_SAT = 0.25            # net flow = 25% of current OI saturates |w| to 1
SEED_FRAC = 0.5         # trust day-level oi_chg at half weight on cold start
UW_PREM = 1.30          # premium 30% above writers' avg build px = underwater
VEL_WIN = 300           # seconds of history for unwind / premium velocity
SQ_UNWIND_SAT = 0.25    # 25% of underwater OI unwound in 5m saturates
SQ_PREMV_SAT = 0.10     # +10% premium in 5m saturates
SQ_BAND = 300           # squeeze only scans strikes within +/-300 pts of spot
                        # (near-the-money writers are the actionable fuel; deep
                        # ITM writers far from price are noise on the pain map)
SKEW_OFF = 300          # skew measured ATM-300 PE vs ATM+300 CE


def _clamp1(x):
    return max(-1.0, min(1.0, x))


def _clamp01(x):
    return max(0.0, min(1.0, x))


def max_pain(strikes):
    """Strike minimizing total intrinsic payout to option holders."""
    best_k, best_pay = None, None
    for cand in strikes:
        K = cand["k"]
        pay = 0.0
        for s in strikes:
            pay += s["ce"]["oi"] * max(K - s["k"], 0.0)
            pay += s["pe"]["oi"] * max(s["k"] - K, 0.0)
        if best_pay is None or pay < best_pay:
            best_k, best_pay = K, pay
    return best_k


def pcr(strikes):
    """(PCR by OI, PCR by volume). None when the denominator is empty."""
    ce_oi = sum(s["ce"]["oi"] for s in strikes)
    pe_oi = sum(s["pe"]["oi"] for s in strikes)
    ce_v = sum(s["ce"]["vol"] for s in strikes)
    pe_v = sum(s["pe"]["vol"] for s in strikes)
    return (pe_oi / ce_oi if ce_oi else None,
            pe_v / ce_v if ce_v else None)


def _iv_at(strikes, k, side):
    for s in strikes:
        if s["k"] == k:
            return s[side]["iv"]
    return None


def iv_surface(strikes, atm):
    """ATM IVs + fixed-offset skew (PE fear below vs CE fear above)."""
    ce, pe = _iv_at(strikes, atm, "ce"), _iv_at(strikes, atm, "pe")
    otm_pe = _iv_at(strikes, atm - SKEW_OFF, "pe")
    otm_ce = _iv_at(strikes, atm + SKEW_OFF, "ce")
    skew = (otm_pe - otm_ce) if (otm_pe is not None and otm_ce is not None) \
        else None
    return {"atm_ce": ce, "atm_pe": pe, "skew": skew}


class _SideFlow:
    """Cumulative classified OI flow for one (strike, side) book."""

    __slots__ = ("w_flow", "b_flow", "bpx_num", "bpx_den", "hist", "seeded",
                 "pend_doi", "bkt_sec", "bkt_ltp")

    def __init__(self):
        self.w_flow = 0.0       # writer-built OI (cumulative, signed by cover)
        self.b_flow = 0.0       # buyer-built OI
        self.bpx_num = 0.0      # writer build-price VWAP accumulator
        self.bpx_den = 0.0
        self.hist = deque()     # (sec, oi, ltp) for velocity windows
        self.seeded = False
        self.pend_doi = 0.0     # OI delta accumulated in the open minute
        self.bkt_sec = None     # bucket start time / start premium
        self.bkt_ltp = None

    def seed(self, row):
        """Cold start: trust Dhan's day-level oi_change at half weight."""
        self.seeded = True
        chg, ltp, avg = row["oi_chg"], row["ltp"], row.get("avg")
        if not chg or chg <= 0 or not ltp:
            return
        writer = avg is not None and avg > 0 and ltp <= avg
        if writer:
            self.w_flow += SEED_FRAC * chg
            self.bpx_num += SEED_FRAC * chg * (avg or ltp)
            self.bpx_den += SEED_FRAC * chg
        else:
            self.b_flow += SEED_FRAC * chg

    def update(self, sec, prev_row, row):
        if self.bkt_sec is None:
            self.bkt_sec, self.bkt_ltp = sec, prev_row["ltp"]
        self.pend_doi += row["oi"] - prev_row["oi"]
        if sec - self.bkt_sec >= CLASSIFY_S:
            d_oi = self.pend_doi
            d_p = row["ltp"] - self.bkt_ltp
            if d_oi and abs(d_p) >= PREM_TICK:
                if d_oi > 0:
                    if d_p < 0:                 # writers add
                        self.w_flow += d_oi
                        self.bpx_num += d_oi * row["ltp"]
                        self.bpx_den += d_oi
                    else:                       # buyers add
                        self.b_flow += d_oi
                else:
                    if d_p > 0:                 # writers cover (buy back)
                        self.w_flow += d_oi
                    else:                       # longs bail
                        self.b_flow += d_oi
            self.pend_doi = 0.0
            self.bkt_sec, self.bkt_ltp = sec, row["ltp"]
        self.hist.append((sec, row["oi"], row["ltp"]))
        while self.hist and sec - self.hist[0][0] > VEL_WIN:
            self.hist.popleft()

    def w(self, oi_now):
        net = self.w_flow - self.b_flow
        return _clamp1(net / max(W_SAT * oi_now, 1.0)) if oi_now else 0.0

    def build_px(self):
        return self.bpx_num / self.bpx_den if self.bpx_den > 0 else None

    def window(self):
        """(oi_then, ltp_then) at the far edge of the velocity window."""
        return (self.hist[0][1], self.hist[0][2]) if self.hist else (None, None)


class ChainState:
    """Rolls per-strike flow state across snapshots and derives all metrics."""

    def __init__(self):
        self.flow = {}          # (k, "ce"/"pe") -> _SideFlow
        self.series = []        # one point per update

    def _flow(self, k, side):
        fl = self.flow.get((k, side))
        if fl is None:
            fl = self.flow[(k, side)] = _SideFlow()
        return fl

    def update(self, snap, T, prev=None):
        """Consume one snapshot; returns the derived metrics dict.

        prev: the previous snapshot (None on the first call). T: years to
        expiry at this snapshot (caller computes; floor it > 0).
        """
        strikes = snap["strikes"]
        sec, spot, atm = snap["sec"], snap["spot"], snap["atm"]
        prev_by_k = {s["k"]: s for s in prev["strikes"]} if prev else {}

        rows = []
        for s in strikes:
            row = {"k": s["k"]}
            for side in ("ce", "pe"):
                fl = self._flow(s["k"], side)
                if not fl.seeded:
                    fl.seed(s[side])
                p = prev_by_k.get(s["k"])
                if p:
                    fl.update(sec, p[side], s[side])
                else:
                    fl.hist.append((sec, s[side]["oi"], s[side]["ltp"]))
                row[side + "_w"] = round(fl.w(s[side]["oi"]), 2)
            rows.append(row)
        w_by_k = {r["k"]: r for r in rows}

        # dealer-signed GEX: same math as gamma.gex_profile, exposed per
        # strike for the UI's diverging bars (profile call gives flip/walls)
        gex_in, per_gex = [], {}
        for s in strikes:
            r = w_by_k[s["k"]]
            ivs = [v for v in (s["ce"]["iv"], s["pe"]["iv"]) if v]
            if ivs:
                g = bs_gamma(spot, s["k"], sum(ivs) / len(ivs), T)
                per_gex[s["k"]] = g * (s["ce"]["oi"] * r["ce_w"]
                                       + s["pe"]["oi"] * r["pe_w"])
            gex_in.append({"k": s["k"], "ce_oi": s["ce"]["oi"],
                           "pe_oi": s["pe"]["oi"], "ce_iv": s["ce"]["iv"],
                           "pe_iv": s["pe"]["iv"], "ce_w": r["ce_w"],
                           "pe_w": r["pe_w"]})
        prof = gex_profile(gex_in, spot, T)

        pcr_oi, pcr_vol = pcr(strikes)
        mp = max_pain(strikes)
        iv = iv_surface(strikes, atm)
        sq = self._squeeze(strikes, w_by_k, spot)

        gt = prof["gex_total"]
        metrics = {
            "pcr_oi": round(pcr_oi, 2) if pcr_oi is not None else None,
            "pcr_vol": round(pcr_vol, 2) if pcr_vol is not None else None,
            "max_pain": mp,
            "gex_total": gt,
            "gex_regime": None if gt is None else
                          ("POSITIVE" if gt >= 0 else "NEGATIVE"),
            "flip_px": prof["flip_px"],
            "wall_up": prof["wall_up"],
            "wall_dn": prof["wall_dn"],
            "iv": iv,
            "squeeze": sq,
            "per_strike": [
                {"k": r["k"], "ce_w": r["ce_w"], "pe_w": r["pe_w"],
                 "gex": per_gex.get(r["k"])} for r in rows],
        }
        self.series.append({
            "ts": snap["ts"], "sec": sec, "spot": round(spot, 1),
            "pcr": metrics["pcr_oi"], "gex": gt, "flip": prof["flip_px"],
            "mp": mp, "sq": sq["score"],
            "ce_oi": sum(s["ce"]["oi"] for s in strikes),
            "pe_oi": sum(s["pe"]["oi"] for s in strikes),
            "iv_ce": iv.get("atm_ce"), "iv_pe": iv.get("atm_pe"),
            "greg": metrics["gex_regime"]})
        return metrics

    def _squeeze(self, strikes, w_by_k, spot):
        """Chain-wide squeeze: writer-dominant books now underwater, and how
        fast they are unwinding. UP squeeze = CE writers trapped (fuel above),
        DOWN = PE writers trapped."""
        best = {"score": 0.0, "side": None, "rows": [],
                "verdict": "no writer book under pressure"}
        for side, dirn in (("ce", "UP"), ("pe", "DOWN")):
            total_w_oi, uw_rows = 0.0, []
            for s in strikes:
                if abs(s["k"] - spot) > SQ_BAND:      # near-the-money only
                    continue
                w = w_by_k[s["k"]][side + "_w"]
                if w < W_SAT:
                    continue
                fl = self.flow[(s["k"], side)]
                uw_oi = min(s[side]["oi"], max(0.0, fl.w_flow - fl.b_flow))
                total_w_oi += uw_oi
                bpx = fl.build_px()
                ltp = s[side]["ltp"]
                itm = spot > s["k"] if side == "ce" else spot < s["k"]
                under = itm or (bpx is not None and ltp > UW_PREM * bpx)
                if not under or uw_oi <= 0:
                    continue
                oi_then, ltp_then = fl.window()
                unwound = max(0.0, (oi_then - s[side]["oi"])) \
                    if oi_then is not None else 0.0
                pv = (ltp / ltp_then - 1.0) \
                    if (ltp_then and ltp_then > 0) else 0.0
                uw_rows.append({"k": s["k"], "side": side.upper(),
                                "uw_oi": round(uw_oi),
                                "unwind_5m": round(unwound),
                                "prem_vel": round(pv, 3)})
            if not uw_rows or total_w_oi <= 0:
                continue
            uw_oi_sum = sum(r["uw_oi"] for r in uw_rows)
            frac = _clamp01(uw_oi_sum / total_w_oi)
            u5 = _clamp01(sum(r["unwind_5m"] for r in uw_rows)
                          / max(uw_oi_sum, 1.0) / SQ_UNWIND_SAT)
            pv = _clamp01(max(r["prem_vel"] for r in uw_rows) / SQ_PREMV_SAT)
            score = round(frac * (0.35 + 0.65 * u5) * (0.35 + 0.65 * pv), 2)
            if score > best["score"]:
                uw_rows.sort(key=lambda r: -r["uw_oi"])
                ks = [r["k"] for r in uw_rows]
                tot_m = uw_oi_sum / 1e6
                un_m = sum(r["unwind_5m"] for r in uw_rows) / 1e3
                best = {
                    "score": score, "side": dirn, "rows": uw_rows[:6],
                    "verdict": (f"{side.upper()} writers {min(ks)}–{max(ks)} "
                                f"underwater: {tot_m:.1f}M writer OI trapped, "
                                f"{un_m:.0f}k unwound in 5m — squeeze fuel "
                                f"{'ABOVE' if dirn == 'UP' else 'BELOW'}")}
        return best


def thin_series(series, keep_full=120, step=6):
    """Recent points at full resolution, older ones sampled every `step`."""
    if len(series) <= keep_full:
        return series
    old, recent = series[:-keep_full], series[-keep_full:]
    return old[::step] + recent
