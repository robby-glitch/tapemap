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
SQ_MIN_SH = 0.03        # a squeeze needs real writers trapped, measured against
                        # the chain's heaviest book so it scales across indices.
                        # The score is a ratio, so a near-empty book over a
                        # near-empty total still reads high: 2026-07-28 10:15
                        # printed 0.65-0.88 on "0.0M writer OI trapped" (share
                        # ~0, now killed) while the genuine 12:18 call was 2.0M
                        # against a 44M book (share 0.045, still passes).
SQ_MIN_PREM = 5.0       # ... and they must be defending something worth
                        # holding. A 20% unwind of a Rs 2 option near expiry is
                        # margin housekeeping, not fear (13:53: 24,100 CE -20%
                        # at Rs 2.10; 15:20: 12.7M "covered" at Rs 1.75).
SQ_SQUARE_AT = "15:05"  # after this, OI decay is mechanical across the whole
                        # chain and no unwind supports a directional claim
SQ_NET_MIN = 0.35       # at least this share of the unwind must have left the
                        # SIDE, not just moved strike, before it counts as
                        # capitulation — below it the writers merely rolled
SQ_SIDE_TOL = 60        # a CE book only caps price at/above spot and a PE book
                        # only supports it at/below; this much slack keeps a
                        # wall price has JUST crossed in scope. Deeper ITM books
                        # are losers closing out, not a wall failing.
WALL_ROLE_M = 1.15      # one side must lead the other by this much to own a
                        # strike; going through CONTESTED is the hysteresis
WALL_MIN_SH = 0.25      # ... and the strike must carry this share of the
                        # chain's heaviest book before its role is news
HEAVY_SH = 0.50         # strikes at/above this share define the "book zone":
                        # price outside it is where gex_total lies to you
SKEW_OFF = 300          # skew measured ATM-300 PE vs ATM+300 CE
IV_MAX = 2.0            # >200% vol is a solver blow-up, not a reading
IV_MIN_TV = 2.0         # ... and so is any fit on less time value than this.
                        # Near expiry an option trades at intrinsic and the
                        # solver has nothing left to fit: 2026-07-28 14:52
                        # printed atm_pe 1.3313 (133% vol) off ~Rs 0.5 of time
                        # value, and that fed the UI's skew direction vote.


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


def _iv_at(strikes, k, side, spot):
    """IV only where it was fitted on real time value.

    An option trading at (or through) intrinsic leaves the solver nothing to
    fit, so it returns garbage — and that garbage propagates: the UI's
    direction bias reads `skew`, so a diverged solve becomes a vote on which
    side to trade. Returning None makes downstream drop the term instead."""
    for s in strikes:
        if s["k"] != k:
            continue
        iv, ltp = s[side]["iv"], s[side]["ltp"]
        if iv is None or ltp is None or not 0 < iv <= IV_MAX:
            return None
        intrinsic = (max(0.0, spot - k) if side == "ce"
                     else max(0.0, k - spot))
        return iv if ltp - intrinsic >= IV_MIN_TV else None
    return None


def iv_surface(strikes, atm, spot):
    """ATM IVs + fixed-offset skew (PE fear below vs CE fear above)."""
    ce, pe = _iv_at(strikes, atm, "ce", spot), _iv_at(strikes, atm, "pe", spot)
    otm_pe = _iv_at(strikes, atm - SKEW_OFF, "pe", spot)
    otm_ce = _iv_at(strikes, atm + SKEW_OFF, "ce", spot)
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
        # Trending-OI: the LAST snapshot of each minute, per strike. oi_chg is
        # Dhan's cumulative day change, so a bucket's value is simply its
        # closing value — which means one minute-grid serves any interval
        # (5/15/30/60) without re-reading anything.
        # 375 minutes x ~50 strikes x 2 legs is a few hundred KB per index.
        self.minutes = {}       # "HH:MM" -> {"spot": float, "k": {strike: (ce_chg, pe_chg)}}
        self.role = {}          # k -> "CEILING"/"FLOOR"/"CONTESTED"
        self.walls = {}         # "up"/"dn" -> last wall strike
        self.wall_log = []      # structural changes, newest last
        self.peak = {}          # (k, "ce"/"pe") -> session-high OI. "% off
                                # peak" is the cheapest read of a wall losing
                                # its defenders, and it is what made the
                                # 2026-07-28 roll-vs-rout calls possible.

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
                key = (s["k"], side)
                self.peak[key] = pk = max(self.peak.get(key, 0.0),
                                          s[side]["oi"])
                row[side + "_pk"] = pk
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
        iv = iv_surface(strikes, atm, spot)
        sq = self._squeeze(strikes, w_by_k, spot, snap.get("ts") or "00:00:00")

        self.minutes[(snap.get("ts") or "00:00:00")[:5]] = {
            "spot": spot,
            "k": {s["k"]: ((s["ce"].get("oi_chg") or 0.0),
                           (s["pe"].get("oi_chg") or 0.0)) for s in strikes},
        }

        wall_ev = self._wall_events(strikes, prof, spot, snap.get("ts") or "")

        # gex_total alone is a trap: it falls both when dampening genuinely
        # dies AND when price has simply walked away from the strikes holding
        # the gamma — and those mean opposite things. On 2026-07-28 it read
        # 120k at the 15:01 low (outside the zone, snap-back coming) and
        # 1.56M twenty minutes later back at 24,000. Ship the context with it.
        ks = sorted(s["k"] for s in strikes)
        step = min((b - a) for a, b in zip(ks, ks[1:])) if len(ks) > 1 else 50.0
        tot_oi = {s["k"]: (s["ce"]["oi"] or 0) + (s["pe"]["oi"] or 0)
                  for s in strikes}
        heaviest = max(tot_oi.values()) if tot_oi else 0.0
        heavy = [k for k, v in tot_oi.items() if heaviest and v >= HEAVY_SH * heaviest]
        gt = prof["gex_total"]
        in_zone = bool(heavy) and min(heavy) - step <= spot <= max(heavy) + step
        # The comment above says gex_total alone is a trap, and this function
        # already knows when spot has walked out of the book -- but the regime
        # label used to be stamped off gt's sign regardless. On 2026-08-04 that
        # printed "POSITIVE" (gt +179k, carried by the wings) while the
        # near-money book the hedgers actually trade against was NEGATIVE
        # (gex_spot -42k) and the tape sprang a bull trap at 10:13 and a bear
        # trap at 11:00. A trader reading "positive gamma, fade the move" at
        # the money was reading the wings. Out of the zone the total says
        # nothing about here, so say that instead of guessing.
        metrics = {
            "gex_spot": sum(v for k, v in per_gex.items()
                            if v is not None and abs(k - spot) <= step),
            "book_zone": [min(heavy), max(heavy)] if heavy else None,
            "in_book_zone": in_zone,
            "mp_dist": round(mp - spot, 1) if mp is not None else None,
            "wall_events": wall_ev,
            "wall_log": self.wall_log[-12:],
            "pcr_oi": round(pcr_oi, 2) if pcr_oi is not None else None,
            "pcr_vol": round(pcr_vol, 2) if pcr_vol is not None else None,
            "max_pain": mp,
            "gex_total": gt,
            "gex_regime": None if gt is None else
                          ("POSITIVE" if gt >= 0 else "NEGATIVE")
                          if in_zone else "OUT-OF-ZONE",
            "flip_px": prof["flip_px"],
            # Why there is no flip level, when there is none. "We looked and
            # the book never changes sign" and "we could not look" are
            # different sentences and must not both render as a blank.
            "flip_status": prof["flip_status"],
            "wall_up": prof["wall_up"],
            "wall_dn": prof["wall_dn"],
            "iv": iv,
            "squeeze": sq,
            "per_strike": [
                {"k": r["k"], "ce_w": r["ce_w"], "pe_w": r["pe_w"],
                 "ce_pk": r["ce_pk"], "pe_pk": r["pe_pk"],
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

    def oi_flow(self, interval=15, strikes=None):
        """Trending-OI table — one row per `interval`-minute bucket.

        Column semantics were reverse-engineered from a reference tool and
        checked against our own 2026-07-28 capture (six buckets matched within
        1-2%, the residual being sampling instant). The key thing the labels
        get right and the eye gets wrong: "Chng. in Call OI" really is Dhan's
        cumulative day CHANGE per strike, not the outstanding OI. Summing
        outstanding OI instead gives ~1.8x the numbers and the wrong PCR.

            call/put  = sum of per-strike oi_chg over the selected strikes
            diff      = put - call
            pcr       = put / call
            strength  = diff / max(call, put)      (signed)
            chg_dir   = diff(t) - diff(t-1)
            chg_dir_pct = chg_dir / |diff(t-1)|
            sentiment = BULLISH when diff > 0

        `strikes` is an iterable of strike prices; None means every strike in
        the snapshot.
        """
        if not self.minutes or interval <= 0:
            return []
        ks = set(strikes) if strikes else None

        # Each row is the chain AS AT that clock mark — a sampled series, not
        # an average over the interval that follows. Getting this wrong shifts
        # every row by one bucket, which is exactly how the first attempt
        # disagreed with the reference tool.
        mins = sorted(self.minutes)
        tmin = lambda t: int(t[:2]) * 60 + int(t[3:5])
        first, last_m = tmin(mins[0]), tmin(mins[-1])
        marks = [m for m in range(((first + interval - 1) // interval) * interval,
                                  last_m + 1, interval)]

        rows, prev_diff, day_hi, day_lo, prev_mark = [], None, None, None, first - 1
        for mk_min in marks:
            bk = "%02d:%02d" % (mk_min // 60, mk_min % 60)
            window = [m for m in mins if prev_mark < tmin(m) <= mk_min]
            if not window:
                continue
            rec = self.minutes[window[-1]]       # the state as at this mark
            spots = [self.minutes[m]["spot"] for m in window
                     if self.minutes[m]["spot"] is not None]
            call = put = 0.0
            for k, (c, p) in rec["k"].items():
                if ks is None or k in ks:
                    call += c
                    put += p
            diff = put - call
            scale = max(abs(call), abs(put)) or 1.0
            chg = None if prev_diff is None else diff - prev_diff
            chg_pct = (chg / abs(prev_diff)) if (chg is not None and prev_diff) else None

            brk, brk_px = None, None
            if spots:
                hi, lo = max(spots), min(spots)
                # a break is a NEW extreme made inside this bucket, so compare
                # against the extremes of everything before it
                if day_hi is None or hi > day_hi:
                    if day_hi is not None:
                        brk, brk_px = "DHB", round(hi, 2)
                    day_hi = hi
                if day_lo is None or lo < day_lo:
                    if day_lo is not None:
                        brk, brk_px = "DLB", round(lo, 2)
                    day_lo = lo

            rows.append({
                "time": bk,
                "ltp": round(rec["spot"], 2) if rec["spot"] is not None else None,
                "call": round(call),
                "put": round(put),
                "diff": round(diff),
                "strength": round(diff / scale, 4),
                "pcr": round(put / call, 2) if call else None,
                "chg_dir": None if chg is None else round(chg),
                "chg_dir_pct": None if chg_pct is None else round(chg_pct, 4),
                "sentiment": "BULLISH" if diff > 0 else "BEARISH" if diff < 0 else "NEUTRAL",
                "brk": brk,
                "brk_px": brk_px,
            })
            prev_diff, prev_mark = diff, mk_min
        return rows

    def _wall_events(self, strikes, prof, spot, ts):
        """Structural changes in the book — the day's real headlines.

        On 2026-07-28 the 24,000 strike flipped ceiling->floor in the morning
        and floor->ceiling in the afternoon. Both were the decisive move of
        their half of the session, both were plainly visible in the chain, and
        neither produced a single line of narrative because the engine watches
        books at one ATM strike while the analyser only ever showed numbers.
        """
        out = []
        tot = {s["k"]: (s["ce"]["oi"] or 0) + (s["pe"]["oi"] or 0)
               for s in strikes}
        heaviest = max(tot.values()) if tot else 0.0
        for s in strikes:
            k = s["k"]
            if not heaviest or tot[k] < WALL_MIN_SH * heaviest:
                continue
            ce, pe = s["ce"]["oi"] or 0, s["pe"]["oi"] or 0
            role = ("CEILING" if ce > pe * WALL_ROLE_M else
                    "FLOOR" if pe > ce * WALL_ROLE_M else "CONTESTED")
            was = self.role.get(k)
            self.role[k] = role
            if was and was != role and "CONTESTED" not in (was, role):
                out.append({
                    "ts": ts, "kind": "ROLE-FLIP", "k": k,
                    "side": "UP" if role == "FLOOR" else "DN",
                    "msg": (f"{k:.0f} flipped {was.lower()}→{role.lower()}: "
                            f"CE {ce/1e6:.1f}M vs PE {pe/1e6:.1f}M — the level "
                            f"that {'capped' if was == 'CEILING' else 'held'} "
                            f"price now {'holds' if role == 'FLOOR' else 'caps'} it")})
        for tag, key, word in (("up", "wall_up", "ceiling"),
                               ("dn", "wall_dn", "floor")):
            now, was = prof.get(key), self.walls.get(tag)
            self.walls[tag] = now
            if was and now and now != was:
                moved = "up" if now > was else "down"
                out.append({
                    "ts": ts, "kind": "WALL-MIGRATION", "k": now,
                    "side": "UP" if moved == "up" else "DN",
                    "msg": (f"{word} moved {was:.0f} → {now:.0f} ({moved}) — "
                            f"writers relocated their defence, spot {spot:.0f}")})
        self.wall_log = (self.wall_log + out)[-40:]
        return out

    def _squeeze(self, strikes, w_by_k, spot, ts="00:00:00"):
        """Chain-wide squeeze: writer-dominant books now underwater, and how
        fast they are unwinding. UP squeeze = CE writers trapped (fuel above),
        DOWN = PE writers trapped."""
        best = {"score": 0.0, "side": None, "rows": [],
                "unwound_net": 0, "rebuilt": 0,
                "verdict": "no writer book under pressure"}
        heaviest = max((max(s["ce"]["oi"] or 0, s["pe"]["oi"] or 0)
                        for s in strikes), default=0.0)
        for side, dirn in (("ce", "UP"), ("pe", "DOWN")):
            total_w_oi, uw_rows = 0.0, []
            net_flow = 0.0        # + = OI genuinely left this side of the band
            for s in strikes:
                if abs(s["k"] - spot) > SQ_BAND:      # near-the-money only
                    continue
                # Only books that can actually act as a wall (see SQ_SIDE_TOL)
                if side == "ce" and s["k"] < spot - SQ_SIDE_TOL:
                    continue
                if side == "pe" and s["k"] > spot + SQ_SIDE_TOL:
                    continue
                # Net EVERY in-scope book, underwater or not: writers rolling
                # to the next strike show up here as an offsetting build, which
                # is what separates a roll from a rout. On 2026-07-28 the
                # morning CE "squeeze" was a roll (24,000 drained while 24,050
                # built to its day high) and the afternoon PE one was real
                # (every put strike shed at once) — same shape, opposite truth.
                fl = self.flow[(s["k"], side)]
                oi_then, _lt = fl.window()
                if oi_then is not None:
                    net_flow += oi_then - s[side]["oi"]
                w = w_by_k[s["k"]][side + "_w"]
                if w < W_SAT:
                    continue
                uw_oi = min(s[side]["oi"], max(0.0, fl.w_flow - fl.b_flow))
                total_w_oi += uw_oi
                bpx = fl.build_px()
                ltp = s[side]["ltp"]
                if ltp is not None and ltp < SQ_MIN_PREM:
                    continue          # near-worthless: decay, not defence
                itm = spot > s["k"] if side == "ce" else spot < s["k"]
                under = itm or (bpx is not None and ltp > UW_PREM * bpx)
                if not under or uw_oi <= 0:
                    continue
                _ot, ltp_then = fl.window()
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
            if uw_oi_sum < SQ_MIN_SH * heaviest:
                continue              # hollow: the ratio would flatter nothing
            gross = sum(r["unwind_5m"] for r in uw_rows)
            # A roll is not a squeeze: credit only the OI that left the whole
            # side, so writers stepping to the next strike score ~0.
            net = max(0.0, min(gross, net_flow))
            rebuilt = gross - net
            if gross > 0 and net < SQ_NET_MIN * gross:
                continue          # rolled to the next strike, not capitulating
            frac = _clamp01(uw_oi_sum / total_w_oi)
            u5 = _clamp01(net / max(uw_oi_sum, 1.0) / SQ_UNWIND_SAT)
            pv = _clamp01(max(r["prem_vel"] for r in uw_rows) / SQ_PREMV_SAT)
            score = round(frac * (0.35 + 0.65 * u5) * (0.35 + 0.65 * pv), 2)
            if score > best["score"]:
                uw_rows.sort(key=lambda r: -r["uw_oi"])
                ks = [r["k"] for r in uw_rows]
                span = (f"{min(ks):.0f}" if min(ks) == max(ks)
                        else f"{min(ks):.0f}–{max(ks):.0f}")
                best = {
                    "score": score, "side": dirn, "rows": uw_rows[:6],
                    "unwound_net": round(net), "rebuilt": round(rebuilt),
                    "verdict": (f"{side.upper()} writers {span} underwater: "
                                f"{uw_oi_sum/1e6:.1f}M writer OI trapped, "
                                f"{net/1e3:.0f}k NET unwound in 5m"
                                + (f" ({rebuilt/1e3:.0f}k rolled to nearby "
                                   f"strikes)" if rebuilt >= 1e3 else "")
                                + " — squeeze fuel "
                                f"{'ABOVE' if dirn == 'UP' else 'BELOW'}")}
        if best["side"] and ts >= SQ_SQUARE_AT:
            # everyone is closing, everywhere: the unwind stops meaning anything
            best = dict(best, score=0.0, side=None,
                        verdict="expiry squaring window — chain-wide OI decay, "
                                "no directional read from unwind")
        return best


def thin_series(series, keep_full=120, step=6):
    """Recent points at full resolution, older ones sampled every `step`."""
    if len(series) <= keep_full:
        return series
    old, recent = series[:-keep_full], series[-keep_full:]
    return old[::step] + recent
