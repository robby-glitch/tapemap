"""raftaar.py -- RAFTAAR, the OI-speed picture. THE converged engine (Fable + Opus, round 3, 27 Oct 2026).

Pure, stdlib, causal, no I/O. Drop-in for the TapeMap server next to fronts.py: one Engine per index, step(t, row...) per
minute off the /api/oihist grid, or read(grid, ...) over a whole day. Every threshold is [I] unless marked §1d / rank.py.

INPUT per minute (the /api/oihist grid): {"HH:MM": {"spot": float, "k": {strike: [ce_chg, pe_chg]}}} where chg = OI minus
the 09:15 open; `opens` = {strike: [ce_open, pe_open]} (the grid's `open`) so absolute OI = open + chg. Optional: the
prior-session reference (refbuild.py), the fut book per minute {"HH:MM": {"oi", "c"}} (SENSEX: NIFTY's, §1q), the other two
indices' current pictures, THE READ's word, the day kind (NORMAL / EXPIRY), the day's real open.

MEASURES (S = 15 min, F = 5; SENSEX 16 / 8 -- its ATM OI steps ~1.7x slower [M]):
  nine, atm      the 9 strikes nearest spot (§1d); spot outside the recorded strikes or < 7 of the nine at t-S -> "?"
  zones          CE near = strikes <= atm, CE wall = > atm; PE near = >= atm, PE wall = < atm
  zone net       sum of OI change over the zone, in % of the side's nine OI (W_s); votes = strikes with |d| >= §1d's stall
                 rate x window x their own OI, up / down
  adds, cuts, Z  side gross writing / covering (%); Z = netPE - netCE over S in % of (W_CE + W_PE): > 0 pushes up
  D, D5          spot change over S / F (pts); P = 0.18 % of the day's first spot (effort.py's yardstick) [I]
  fast           side gross over F (%), and the F before it ("pehle")

SIZE (the noise bar): rank.py's cut-offs against the prior sessions of the same index, day kind and day part (PARTS):
  < p70 noise, >= p70 NOTABLE, >= p90 BADA; < MIN_DAYS sessions -> today's own minutes (>= OWN_MIN) -> else "?" PAIMANA NAHI.
  ABSOLUTE CLAUSE: a flow >= 2x the index's all-session median, or >= 1.5x today's own median (>= OWN_MIN minutes), is
  NOTABLE whatever the part says -- the expiry open included. Speed change (TEZ / DHEEMA) uses the last hour's own medians.

SIDE STRUCTURE over S (a side is RUKE unless max(|near|, |wall|) is NOTABLE; a zone counts at >= 25 % of the side's gross):
  near+ wall+ LIKH RAHE · near+ wall0 ATM LIKH (absorbing / pressing) · near0 wall+ DEEWAR MOTI (wall build) ·
  near- wall+ ROLL (cap upar / floor neeche shift, still short) · near+ wall- DEEWAR PRICE PE · near- wall- BHAAG RAHE ·
  near- wall0 ITM COVER (retreat) · near0 wall- DEEWAR HAT RAHI (wall lift) · RUKE.  PHANSE: covered strikes written in
  the last 60 min (their peak inside the hour and >= half the cover built since then).

MINUTE STORY (first match): L = the side the move hurts, W = the side it pays; D = +-1 if |D| NOTABLE and >= P/2
  1 D, Z=-D, price still moving     L LIKHAI INTO MOVE · PHANS RAHE   (ULTA)
  2 D, Z=-D, price stalled           L LIKHAI INTO MOVE · ROK RAHE     (ULTA)
  3 D, L covering, W writing         L BHAAG + W LIKHAI               (SAATH, dono engine)
  4 D, L covering                    L BHAAG RAHE                      (SAATH)
  5 D, L rolled away                 L CAP/FLOOR SHIFT                 (MILA-JULA)
  6 D, W writing                     W SAATH LIKH                      (SAATH)
  7 D, both RUKE                     BINA OI                           (price akela)
  8 D, else                          OI SAATH                          (MILA-JULA)
  9 no D, Z notable                  ATKA <lead side> · zor hai, price nahi
 10 no D, both adding within 1:2, gross notable, range30 <= 1 step      PIN BAN RAHA @k
 11 no D, range30 <= 0.6 step, spot within 1/2 step of the most two-sided strike (OI ratio >= 0.6)   PIN TIKA @k
 12 no D, both sides net cutting notable                                 UNWIND · dono nikal rahe
 13 else                             KUCH KHAAS NAHI
 PIN BAARI-BAARI @k: an ATKA of one side then of the other within 45 min at one strike (+-1 step), both net adding, range45 < 2P.

HELD PICTURE: a LEG starts when a D-story holds HOLD marks with OI behind it (Z = D notable) or D BADA; inside CHOP it
needs both. Phases SHURU (5 min) · TEZ (with-flow over F >= 1.5x the F before, new extreme <= 3 min) · JAARI · RUKA (no new
extreme >= 5 min, OI not against) · THAK (fading fuel AND a price stall >= 5 min). It ENDS (KHATAM, with the reason) on half
the leg given back (min 1 step), an OI-backed opposite leg held, 20 min without a new extreme, 10 min at KAMZOR, 10 min of
CHOP / PIN story. WAPSI = a leg against the day's drift (|spot - open| >= 3P) that has retraced < half of it: a pullback.
CHOP is the big word when NOTABLE legs went both ways inside 30 min; a leg inside it is shown small, capped THEEK, ends it
only on a new 60-min extreme with OI behind it. ATKA / PIN / UNWIND / BINA OI / KHAMOSH / ? hold HOLD marks.

GRADE n/N over the checks that could be read: size (history) · size (today's own) · BADA · 5 min tika · 15 min tika ·
2+ strikes (and >= 2/3 of the zone's voters) · price (leg: still moving; ATKA: stopped; CHOP/PIN: range in band) · fut leg
(|dOI15| >= 0.10 %: direction with the leg; quiet for PIN) · each other index (same word + direction within 3 min) · chop ke
bahar.  n/N >= 0.6 MAZBOOT · >= 0.4 THEEK · else KAMZOR.  Caps: KAMZOR unless the picture's OWN flow is NOTABLE; THEEK
inside CHOP, for WAPSI, and when the nine's OI is PATLA (< 100 L).

STAMPS: a picture at the first minute it reaches THEEK (KAMZOR lives on the face, never a line) · inside a stamped leg: TEZ,
the first THAK, WAPSI <-> CHAL, KHATAM with the reason · KHAMOSH / BINA OI once, after a stamped picture, after 5 min · ? always
(3 min) · side events (ROLL; BADA cover into price; PHIR LIKHNE LAGE after 20 min ruke; roll toota), once per side per 30 min ·
the != READ line only on a MAZBOOT picture that is not a WAPSI and not inside CHOP, with numbers.
"""
from __future__ import annotations

NEAR = 9
S_MIN = {"NIFTY": 15, "BANKNIFTY": 15, "SENSEX": 16}
F_MIN = {"NIFTY": 5, "BANKNIFTY": 5, "SENSEX": 8}
HOLD = 3                              # [I] her 3-min bar, every index (SENSEX's cadence is 1.7x, not 2.7x)
PARTS = ((555, 600), (600, 720), (720, 810), (810, 931))   # rank.py: 09:15-10:00, 10:00-12:00, 12:00-13:30, 13:30-15:30
P_NOTE, P_BADA, MIN_DAYS, REF_DAYS, OWN_MIN = 70, 90, 5, 20, 30   # rank.py's cut-offs and minimums
ABS_X, OWN_X = 2.0, 1.5               # [I] the absolute clause: 2x the all-session median, or 1.5x today's own
THR_PCT = 0.0018                      # effort.py / oi-lab: "a move" yardstick; D needs >= P/2 as well as its rank
ZONE_SHARE = 0.25                     # [I] a zone counts when it carries >= 25 % of the side's gross
ROLL_FRAC = 0.5                       # [I] a roll re-adds >= half of what the near zone cut
STALL_RATE = 0.05 / 15                # §1d stall rate per minute of the strike's own OI (vote threshold)
PIN_RATIO, PIN_RANGE, PIN_TIGHT, PIN_STOCK = 0.5, 1.0, 0.6, 0.6   # [I] both within 1:2; range30 <= 1 step; TIKA 0.6 step, OI ratio 0.6
TURN_WIN, TURN_RANGE = 45, 2.0        # [I] baari-baari: 45 min, range < 2 P
CHOP_WIN, CHOP_OUT = 30, 60           # [I] CHOP enters on legs both ways inside 30 min, lapses after 60 without one (hysteresis);
                                      #     a swing leaves it only on a break of the 60-min range by >= P with OI behind it
LEG_RETRACE, LEG_STALE, LEG_WEAK, LEG_FLAT = 0.5, 20, 10, 10   # [I] end rules
RESUME_WIN = 30                       # [I] S1 "phir chal pada": a stale / weak leg may resume within 30 min with < half retraced
NEQ_LAST = "15:00"                    # [I] no contradiction line after 15:00
EDGE_MIN = 3                          # [I] S4: fewer than 3 of the nine on one side of spot = "kinare pe", THEEK cap, no ≠
COUNTER_FRAC = 0.5                    # [I] a counter-leg counts toward CHOP when it is >= half the previous leg (22 Oct dips 56 %; 8 Oct bounces 14-31 %)
NEQ_YOUNG, NEQ_MOVE, NEQ_M5 = 15, 1.5, 0.5   # [I] a ≠ line: leg <= 15 min old or its breakout minute, |m15| >= 1.5 P with D BADA, m5 >= 0.5 step
WAPSI_DRIFT, WAPSI_MAX = 3.0, 0.5     # [I] drift >= 3 P; a pullback that takes > half the drift is a leg
TEZ_X, THAK_X, STALL_MIN, PHASE_MIN = 1.5, 0.5, 5, 5   # [I]
PHANSE_WIN, PHANSE_FRAC = 60, 0.5     # [I]
EV_GAP, RESTART_MIN = 30, 20          # [I] side events: once per side per 30 min; "phir likhne lage" after >= 20 min ruke
QUIET_MIN, Q_MIN, PEER_LAG = 10, 3, 3  # [I] a quiet line after 10 held minutes, once an hour; ? after 3
PATLA_L = 100e5                       # [I] nine's OI under 100 L: thin, grade capped THEEK (BANKNIFTY normal weeks, SENSEX off-expiry)
FUT_OI_PCT = 0.10                     # §1o's fut_oi vote
MAZBOOT, THEEK, KAMZOR = "MAZBOOT", "THEEK", "KAMZOR"
UP, DN = "▲", "▼"
L = 1e5

METRICS = ("zone", "adds", "cuts", "Z", "D", "fast")


# ---- small helpers -------------------------------------------------------------------------------------------------------

def mins(t):
    return int(t[:2]) * 60 + int(t[3:5])


def hm(m):
    return "%02d:%02d" % divmod(m, 60)


def part_of(t):
    m = mins(t)
    for i, (a, b) in enumerate(PARTS):
        if a <= m < b:
            return i
    return 3


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return None if not n else xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def lakh(x):
    if x is None:
        return "—"
    if abs(x) < 500:
        return "0"
    s = "+" if x > 0 else "−"
    a = abs(x)
    return f"{s}{a / 1e5:.2f}L" if a < 1e5 else f"{s}{a / 1e5:.1f}L"


def _num(k):
    try:
        return float(k)
    except (TypeError, ValueError):
        return None


def _pair(v):
    if not isinstance(v, (list, tuple)) or len(v) < 2:
        return None
    try:
        return float(v[0]), float(v[1])
    except (TypeError, ValueError):
        return None


# ---- the reference (built by refbuild.py; read here) --------------------------------------------------------------------

class Ref:
    """The prior-session size reference for one index: {day: {"kind", "parts": {part: {metric: [p50, p70, p90]}}}}.

    level(metric, x, ...) -> "BADA" / "NOTABLE" / "NOISE" / None (no reference). Causal: for_day(day) uses sessions < day.
    """

    def __init__(self, table=None):
        self.table = table or {}
        self.day = None
        self.kind = None
        self.cut = {}          # part -> metric -> (p70, p90) across the last REF_DAYS prior sessions of the kind
        self.all_med = {}      # metric -> median of every prior session's p50 (any kind, any part)
        self.n_sessions = 0

    def for_day(self, day, kind):
        self.day, self.kind = day, kind
        prior = sorted(d for d in self.table if d < day)
        same = [d for d in prior if self.table[d].get("kind") == kind][-REF_DAYS:]
        self.n_sessions = len(same)
        self.cut = {}
        if len(same) >= MIN_DAYS:
            for p in range(4):
                self.cut[p] = {}
                for m in METRICS:
                    v70 = [self.table[d]["parts"].get(str(p), {}).get(m, [None, None, None])[1] for d in same]
                    v90 = [self.table[d]["parts"].get(str(p), {}).get(m, [None, None, None])[2] for d in same]
                    v70 = [x for x in v70 if x is not None]
                    v90 = [x for x in v90 if x is not None]
                    if len(v70) >= MIN_DAYS:
                        self.cut[p][m] = (median(v70), median(v90))
        self.all_med = {}
        for m in METRICS:
            v = [self.table[d]["parts"].get(str(p), {}).get(m, [None])[0] for d in prior for p in range(4)]
            v = [x for x in v if x is not None]
            self.all_med[m] = median(v) if v else None
        return self

    def level(self, metric, x, part, own):
        """own = today's own samples so far for this metric (list). None when nothing can size it."""
        if x is None:
            return None
        cut = self.cut.get(part, {}).get(metric)
        lvl, src = None, None
        if cut:
            p70, p90 = cut
            lvl, src = ("BADA" if x >= p90 else "NOTABLE" if x >= p70 else "NOISE"), "history"
        elif own is not None and len(own) >= OWN_MIN:
            p70, p90 = pct(own, P_NOTE), pct(own, P_BADA)
            lvl, src = ("BADA" if x >= p90 else "NOTABLE" if x >= p70 else "NOISE"), "aaj"
        if lvl is None:
            return None
        # the absolute clause: a big flow is never "kuch khaas nahi"
        if lvl == "NOISE" and metric != "D":
            am = self.all_med.get(metric)
            if am and x >= ABS_X * am:
                lvl = "NOTABLE"
            elif own is not None and len(own) >= OWN_MIN and median(own) and x >= OWN_X * median(own):
                lvl = "NOTABLE"
        return lvl

    def source(self):
        return f"{self.n_sessions} pichhle {self.kind.lower()} din" if self.cut else "aaj ke minute"


# ---- measures -------------------------------------------------------------------------------------------------------------

def nine_at(row, opens):
    """(strikes, atm, why) for one grid row; why is set when the read is a '?'."""
    spot = row.get("spot")
    ks = [k for k in (_num(s) for s in (row.get("k") or {})) if k is not None]
    if spot is None or len(ks) < NEAR:
        return None, None, "PADH NAHI SAKE · chain window chhoti"
    if spot < min(ks) or spot > max(ks):
        return None, None, "PADH NAHI SAKE · spot chain window ke bahar"
    nk = sorted(ks, key=lambda k: (abs(k - spot), k))[:NEAR]
    atm = min(nk, key=lambda k: (abs(k - spot), k))
    if min(nk) >= spot or max(nk) <= spot:
        return None, None, "PADH NAHI SAKE · spot window ke kinare"
    return sorted(nk), atm, None


def _cell(row, k):
    kk = row.get("k") or {}
    for key in (k, int(k) if float(k).is_integer() else k, str(int(k)) if float(k).is_integer() else str(k)):
        if key in kk:
            return _pair(kk[key])
    return None


def _oi(opens, k, i, chg):
    o = None
    if opens:
        for key in (k, int(k) if float(k).is_integer() else k, str(int(k)) if float(k).is_integer() else str(k)):
            if key in opens:
                pr = _pair(opens[key])
                o = pr[i] if pr else None
                break
    return (o or 0.0) + chg


def measures(grid, t, w, opens):
    """Both sides' zone flows over w minutes, in % of the side's nine OI at t. None when t-w is not in the grid."""
    b = hm(mins(t) - w)
    now, was = grid.get(t), grid.get(b)
    if not now or not was:
        return None
    nk, atm, why = nine_at(now, opens)
    if why:
        return {"why": why}
    spot = now["spot"]
    out = {"t": t, "spot": spot, "atm": atm, "nk": nk, "m": spot - was["spot"], "W": {}, "miss": 0,
           "edge": min(sum(1 for k in nk if k < spot), sum(1 for k in nk if k > spot)) < EDGE_MIN}
    for i, s in enumerate(("CE", "PE")):
        z = {"near": 0.0, "wall": 0.0, "near_up": 0, "near_dn": 0, "wall_up": 0, "wall_dn": 0, "adds": 0.0, "cuts": 0.0,
             "per": {}, "oi": {}}
        W = 0.0
        for k in nk:
            c0, c1 = _cell(now, k), _cell(was, k)
            if c0 is None or c1 is None:
                out["miss"] += 1
                continue
            oi = _oi(opens, k, i, c0[i])
            W += max(oi, 0.0)
            d = c0[i] - c1[i]
            z["per"][k] = d
            z["oi"][k] = oi
            zone = "near" if ((k <= atm) if s == "CE" else (k >= atm)) else "wall"
            z[zone] += d
            if abs(d) >= STALL_RATE * w * max(oi, 1.0):
                z[zone + ("_up" if d > 0 else "_dn")] += 1
            if d > 0:
                z["adds"] += d
            else:
                z["cuts"] -= d
        z["W"] = W
        out["W"][s] = W
        out[s] = z
    if out["miss"] > 2 * (NEAR - 7):
        return {"why": "PADH NAHI SAKE · nine mein se strikes record mein nahi"}
    Wt = max(out["W"]["CE"] + out["W"]["PE"], 1.0)
    for s in ("CE", "PE"):
        z, W = out[s], max(out["W"][s], 1.0)
        z["near_pct"], z["wall_pct"] = 100 * z["near"] / W, 100 * z["wall"] / W
        z["adds_pct"], z["cuts_pct"] = 100 * z["adds"] / W, 100 * z["cuts"] / W
        z["gross_pct"] = z["adds_pct"] + z["cuts_pct"]
        z["net"] = z["near"] + z["wall"]
    out["Z"] = 100 * ((out["PE"]["net"]) - (out["CE"]["net"])) / Wt
    out["Wt"] = Wt
    return out


def spot_range(grid, t, w):
    xs = [grid[hm(m)]["spot"] for m in range(mins(t) - w, mins(t) + 1) if hm(m) in grid and grid[hm(m)].get("spot") is not None]
    return (max(xs), min(xs)) if xs else (None, None)


# ---- the structure of one side ---------------------------------------------------------------------------------------------

STRUCT = {
    (1, 1): ("LIKH RAHE", "likh rahe · deewar sab taraf"),
    (1, 0): ("ATM LIKH", "price pe likh rahe"),
    (0, 1): ("DEEWAR MOTI", "aage deewar moti ho rahi"),
    (-1, 1): ("ROLL", "roll · abhi bhi short"),
    (1, -1): ("DEEWAR PRICE PE", "deewar price pe kheench li"),
    (-1, -1): ("BHAAG RAHE", "poora bhaag rahe · fuel"),
    (-1, 0): ("ITM COVER", "price pe phanse buy back · fuel"),
    (0, -1): ("DEEWAR HAT RAHI", "aage deewar hat rahi"),
    (0, 0): ("RUKE", "ruke"),
}
COVERING = {"BHAAG RAHE", "ITM COVER", "ROLL"}
WRITING = {"LIKH RAHE", "ATM LIKH", "DEEWAR MOTI"}


def structure(z, notable):
    """(code, chip, strikes) for one side's zones over S. `notable` = whether max(|near|,|wall|) cleared the bar."""
    if not notable:
        return "RUKE", "ruke", []
    gross = abs(z["near"]) + abs(z["wall"])
    sn = 0 if abs(z["near"]) < ZONE_SHARE * gross else (1 if z["near"] > 0 else -1)
    sw = 0 if abs(z["wall"]) < ZONE_SHARE * gross else (1 if z["wall"] > 0 else -1)
    if sn == -1 and sw == 1 and z["wall"] < ROLL_FRAC * -z["near"]:
        sw = 0                                                     # the re-add is too small to be a roll
    code, chip = STRUCT[(sn, sw)]
    per = z["per"]
    cuts = sorted((k for k in per if per[k] < 0), key=lambda k: per[k])[:2]
    adds = sorted((k for k in per if per[k] > 0), key=lambda k: -per[k])[:2]
    strikes = [(k, per[k]) for k in cuts] + [(k, per[k]) for k in adds]
    return code, chip, strikes


def phanse(series, t, cover_strikes, side_i):
    """The covered strikes whose OI peaked inside the last PHANSE_WIN min and built >= half the cover since: [(k, built, peak_t)]."""
    out = []
    m0 = mins(t) - PHANSE_WIN
    for k, d in cover_strikes:
        v = series.get((k, side_i)) or []
        win = [(mm_, x) for mm_, x in v if m0 <= mm_ <= mins(t)]
        if len(win) < 2:
            continue
        pk_m, pk = max(win, key=lambda p: p[1])
        base = win[0][1]
        if pk_m > m0 and pk - base >= PHANSE_FRAC * -d and pk - base > 0:
            out.append((k, pk - base, hm(pk_m)))
    return out


# ---- the engine -------------------------------------------------------------------------------------------------------------

class Engine:
    """One index. step(t) per minute, in order. picture() is the JSON for the face; stamps accumulate."""

    def __init__(self, idx, day, ref=None, kind="NORMAL", opens=None, fut=None, day_open=None, read_words=None):
        self.idx, self.day, self.kind = idx, day, kind
        self.S, self.F = S_MIN.get(idx, 15), F_MIN.get(idx, 5)
        self.ref = (ref or Ref()).for_day(day, kind)
        self.opens = opens or {}
        self.fut = fut or {}
        self.read_words = read_words or []         # [(t, word, dir)]
        self.grid = {}
        self.series = {}                           # (k, i) -> [(minute, chg)]
        self.own = {m: [] for m in METRICS}        # today's own samples
        self.fast_hist = {"CE": [], "PE": []}      # (minute, fast gross %) for the hour's pace
        self.day_open = day_open
        self.P = None
        self.step_ = None
        self.rows = []                             # minute stories
        self.pic = None                            # the held picture
        self.legs_seen = []                        # (minute, dir) of NOTABLE D minutes (pullbacks excluded), for CHOP
        self.chop_on = False
        self.atkas = []                            # (minute, side, k)
        self.stamps = []
        self.last_stamped = None                   # the last stamped picture key
        self.quiet_since = None
        self.q_since = None
        self.ev_last = {}                          # side -> minute of the last side event
        self.ruke_since = {"CE": None, "PE": None}
        self.last = None                           # the last picture dict (for peers)
        self.pic_hist = []                         # (minute, word, dir) for peers' lag
        self.roll_mark = {}                        # side -> minute of the last ROLL event (roll toota)
        self.pending_end = None                    # a KHATAM held 2 min: a picture that follows absorbs it

    # -- grid in
    def push(self, t, row):
        self.grid[t] = row
        if self.P is None and row.get("spot") is not None:
            self.P = THR_PCT * row["spot"]
            if self.day_open is None:
                self.day_open = row["spot"]
        if row.get("spot") is not None:
            self.day_hi = max(getattr(self, "day_hi", row["spot"]), row["spot"])
            self.day_lo = min(getattr(self, "day_lo", row["spot"]), row["spot"])
        kk = row.get("k") or {}
        for s, v in kk.items():
            k = _num(s)
            pr = _pair(v)
            if k is None or pr is None:
                continue
            for i in (0, 1):
                self.series.setdefault((k, i), []).append((mins(t), pr[i]))
        if self.step_ is None and len(kk) >= 2:
            ks = sorted(k for k in (_num(s) for s in kk) if k is not None)
            self.step_ = min((b - a for a, b in zip(ks, ks[1:]) if b > a), default=50)

    # -- size
    def lvl(self, metric, x, part):
        return self.ref.level(metric, x, part, self.own[metric])

    def notable(self, lvl):
        return lvl in ("NOTABLE", "BADA")

    # -- one minute
    def step(self, t, row=None, peers=None, read_word=None):
        if row is not None:
            self.push(t, row)
        part = part_of(t)
        mS, mF = measures(self.grid, t, self.S, self.opens), measures(self.grid, t, self.F, self.opens)
        if mS is None or mF is None:
            return self._q(t, "PADH RAHE · pehle %d min ka record chahiye" % self.S, peers)
        if mS.get("why") or mF.get("why"):
            return self._q(t, mS.get("why") or mF.get("why"), peers)
        # samples (today's own) -- before sizing this minute, so the first OWN_MIN minutes are a reference, not a verdict
        for s in ("CE", "PE"):
            self.own["zone"] += [abs(mS[s]["near_pct"]), abs(mS[s]["wall_pct"])]
            self.own["adds"].append(mS[s]["adds_pct"])
            self.own["cuts"].append(mS[s]["cuts_pct"])
            self.own["fast"].append(mF[s]["gross_pct"])
            self.fast_hist[s].append((mins(t), mF[s]["gross_pct"]))
        self.own["Z"].append(abs(mS["Z"]))
        self.own["D"].append(abs(mS["m"]))
        if not self.ref.cut and len(self.own["adds"]) < 2 * OWN_MIN:
            return self._q(t, "PAIMANA NAHI · %d/%d minute" % (len(self.own["adds"]) // 2, OWN_MIN), peers)
        spot, step = mS["spot"], self.step_ or 50
        # levels
        lv = {}
        for s in ("CE", "PE"):
            lv[s] = {"zone": self.lvl("zone", max(abs(mS[s]["near_pct"]), abs(mS[s]["wall_pct"])), part),
                     "adds": self.lvl("adds", mS[s]["adds_pct"], part), "cuts": self.lvl("cuts", mS[s]["cuts_pct"], part),
                     "fast": self.lvl("fast", mF[s]["gross_pct"], part)}
        lvZ, lvD = self.lvl("Z", abs(mS["Z"]), part), self.lvl("D", abs(mS["m"]), part)
        D = (1 if mS["m"] > 0 else -1) if (self.notable(lvD) and abs(mS["m"]) >= self.P / 2) else 0
        Z = (1 if mS["Z"] > 0 else -1) if self.notable(lvZ) else 0
        # structures
        st = {}
        for i, s in enumerate(("CE", "PE")):
            code, chip, strikes = structure(mS[s], self.notable(lv[s]["zone"]))
            ph = phanse(self.series, t, [(k, d) for k, d in strikes if d < 0], i) if code in COVERING else []
            st[s] = {"code": code, "chip": chip, "strikes": strikes, "phanse": ph, "near": mS[s]["near"], "wall": mS[s]["wall"],
                     "adds": mS[s]["adds"], "cuts": mS[s]["cuts"], "votes": (mS[s]["near_up"], mS[s]["near_dn"], mS[s]["wall_up"], mS[s]["wall_dn"])}
            if code == "RUKE":
                if self.ruke_since[s] is None:
                    self.ruke_since[s] = mins(t)
            else:
                st[s]["ruke_for"] = (mins(t) - self.ruke_since[s]) if self.ruke_since[s] is not None else 0
                self.ruke_since[s] = None
        # speed change per side (the hour's own pace)
        speed = {}
        for s in ("CE", "PE"):
            now_ = mF[s]["gross_pct"]
            prev = [x for mm_, x in self.fast_hist[s] if mm_ == mins(t) - self.F]
            prev = prev[0] if prev else None
            hour = [x for mm_, x in self.fast_hist[s] if mins(t) - 60 <= mm_ <= mins(t)]
            floor = median(hour) or 0.0
            w = "—"
            if prev is not None:
                if now_ < 0.5 * floor and prev >= floor:
                    w = "RUK"
                elif prev < 0.5 * floor and now_ >= floor:
                    w = "SHURU"
                elif now_ >= TEZ_X * max(prev, 1e-9):
                    w = "TEZ"
                elif now_ * TEZ_X <= prev:
                    w = "DHEEMA"
                else:
                    w = "BARABAR"
            speed[s] = {"word": w, "now_pct": now_, "pehle_pct": prev, "now_L": (mF[s]["adds"] + mF[s]["cuts"]) / max(self.F, 1),
                        "sign": 1 if mF[s]["net"] > 0 else -1 if mF[s]["net"] < 0 else 0}
        # the minute story
        story = self._story(t, mS, mF, D, Z, lvD, lvZ, lv, st, spot, step)
        story.update(t=t, spot=spot, D=D, Z=Z, m=mS["m"], m5=mF["m"], Zpct=mS["Z"], ZL=(mS["PE"]["net"] - mS["CE"]["net"]), lvD=lvD, lvZ=lvZ,
                     lv=lv, st=st, speed=speed, Wt=mS["Wt"], patla=mS["Wt"] < PATLA_L, edge=mS["edge"], part=part,
                     aaj_ref=not bool(self.ref.cut))
        if D:
            drift_ = spot - (self.day_open or spot)
            dh, dl = getattr(self, "day_hi", spot), getattr(self, "day_lo", spot)
            with_drift = D * (1 if drift_ >= 0 else -1) >= 0
            back_ = (dh - spot) if D < 0 else (spot - dl)                           # the counter-move from the day's extreme
            ref_ = self.last_leg if getattr(self, "last_leg", None) else ((dh - self.day_open) if drift_ >= 0 else (self.day_open - dl))
            if with_drift or back_ >= COUNTER_FRAC * max(ref_ or 0.0, 1.0):
                self.legs_seen.append((mins(t), D))                 # a counter-leg of comparable size is a chop leg; a small pullback is not
        self.legs_seen = [(m_, d) for m_, d in self.legs_seen if mins(t) - m_ <= CHOP_OUT]
        self.rows.append(story)
        # the held picture
        self._flush_end(t)
        out = self._hold(t, story, mS, spot, step, peers or {}, read_word)
        big = out.get("picture") or {}
        self.last = {"word": big.get("word"), "dir": big.get("dir")}
        self.pic_hist.append((mins(t), big.get("word"), big.get("dir")))
        return out

    # -- minute story (the combination table)
    def _story(self, t, mS, mF, D, Z, lvD, lvZ, lv, st, spot, step):
        ce, pe = st["CE"], st["PE"]
        hi30, lo30 = spot_range(self.grid, t, 30)
        r30 = (hi30 - lo30) if hi30 is not None else None
        if D:
            Ls, Ws = ("CE", "PE") if D > 0 else ("PE", "CE")
            Lc, Wc = st[Ls]["code"], st[Ws]["code"]
            with_ = mS[Ls]["cuts"] + mS[Ws]["adds"]
            against = mS[Ls]["adds"]
            qual = "ULTA" if against >= with_ and against > 0 else "SAATH" if with_ >= 2 * against else "MILA-JULA"
            moving = (mF["m"] * D) > 0.25 * step
            if Z == -D and Lc in WRITING:
                code = "PHANS RAHE" if moving else "ROK RAHE"
                return {"code": code, "name": f"{Ls} LIKHAI INTO {'RALLY' if D > 0 else 'FALL'} · {code}", "qual": "ULTA",
                        "lead": Ls, "flow": abs(mS[Ls]["near_pct"]), "lvl": lv[Ls]["zone"], "L": Ls, "W": Ws, "with": with_, "against": against,
                        "read": "writers " + ("getting trapped" if moving else "absorbing the move")}
            if Lc in COVERING and Wc in WRITING:
                return {"code": "DONO ENGINE", "name": f"{Ls} BHAAG + {Ws} LIKHAI", "qual": "SAATH", "lead": Ls,
                        "flow": max(mS[Ls]["cuts_pct"], mS[Ws]["adds_pct"]), "lvl": max(lv[Ls]["cuts"], lv[Ws]["adds"], key=_rank),
                        "L": Ls, "W": Ws, "with": with_, "against": against, "read": "losers covering, winners chasing"}
            if Lc in ("BHAAG RAHE", "ITM COVER"):
                return {"code": "BHAAG", "name": f"{Ls} BHAAG RAHE", "qual": "SAATH", "lead": Ls, "flow": mS[Ls]["cuts_pct"],
                        "lvl": lv[Ls]["cuts"], "L": Ls, "W": Ws, "with": with_, "against": against, "read": "short covering: fuel"}
            if Lc == "ROLL":
                return {"code": "ROLL", "name": f"{Ls} {'CAP UPAR' if D > 0 else 'FLOOR NEECHE'} SHIFT", "qual": "MILA-JULA", "lead": Ls,
                        "flow": abs(mS[Ls]["near_pct"]), "lvl": lv[Ls]["zone"], "L": Ls, "W": Ws, "with": with_, "against": against,
                        "read": "the wall moved, still short"}
            if Wc in WRITING:
                return {"code": "SAATH LIKH", "name": f"{Ws} {'FLOOR' if D > 0 else 'CAP'} SAATH", "qual": qual, "lead": Ws,
                        "flow": mS[Ws]["adds_pct"], "lvl": lv[Ws]["adds"], "L": Ls, "W": Ws, "with": with_, "against": against,
                        "read": "the wall follows price"}
            if Lc == "RUKE" and Wc == "RUKE" and Z == 0:
                return {"code": "BINA OI", "name": f"BINA OI {UP if D > 0 else DN}", "qual": "BINA OI", "lead": None, "flow": 0.0,
                        "lvl": "NOISE", "L": Ls, "W": Ws, "with": with_, "against": against, "read": "price akela, writer peeche nahi"}
            return {"code": "OI SAATH", "name": f"OI SAATH {UP if D > 0 else DN}", "qual": qual, "lead": Ls if Lc != "RUKE" else Ws,
                    "flow": abs(mS["Z"]), "lvl": lvZ, "L": Ls, "W": Ws, "with": with_, "against": against, "read": "net with the move, structure mila-jula"}
        # no move
        if Z:
            lead = "PE" if Z > 0 else "CE"
            return {"code": "ATKA", "name": f"ATKA {UP if Z > 0 else DN} · {lead} likh rahe, price nahi" if st[lead]["code"] != "RUKE"
                    else f"ATKA {UP if Z > 0 else DN} · zor hai, price nahi", "qual": None, "lead": lead, "dir": 1 if Z > 0 else -1,
                    "flow": abs(mS["Z"]), "lvl": lvZ, "k": _biggest(mS[lead], 1), "read": "effort without result"}
        ca, pa = mS["CE"]["adds"], mS["PE"]["adds"]
        both_note = self.notable(lv["CE"]["adds"]) and self.notable(lv["PE"]["adds"])
        if both_note and min(ca, pa) >= PIN_RATIO * max(ca, pa) and r30 is not None and r30 <= PIN_RANGE * step:
            k = max(mS["nk"], key=lambda k: max(mS["CE"]["per"].get(k, 0), 0) + max(mS["PE"]["per"].get(k, 0), 0))
            return {"code": "PIN BAN RAHA", "name": f"PIN BAN RAHA @ {k:.0f}s", "qual": None, "lead": None, "k": k,
                    "flow": min(mS["CE"]["adds_pct"], mS["PE"]["adds_pct"]), "lvl": min(lv["CE"]["adds"], lv["PE"]["adds"], key=_rank),
                    "read": "dono likh rahe, barabar"}
        if r30 is not None and r30 <= PIN_TIGHT * step:
            best = None
            for k in mS["nk"]:
                c, p = mS["CE"]["oi"].get(k, 0), mS["PE"]["oi"].get(k, 0)
                if c > 0 and p > 0 and min(c, p) / max(c, p) >= PIN_STOCK:
                    if best is None or min(c, p) > best[1]:
                        best = (k, min(c, p))
            if best and abs(spot - best[0]) <= 0.5 * step:
                return {"code": "PIN TIKA", "name": f"PIN TIKA @ {best[0]:.0f}s", "qual": None, "lead": None, "k": best[0],
                        "flow": None, "lvl": "STOCK", "read": "dono barabar baithe",
                        "oi_k": (mS["CE"]["oi"].get(best[0], 0), mS["PE"]["oi"].get(best[0], 0))}
        if (mS["CE"]["net"] < 0 and mS["PE"]["net"] < 0 and self.notable(lv["CE"]["cuts"]) and self.notable(lv["PE"]["cuts"])):
            return {"code": "UNWIND", "name": "UNWIND · dono nikal rahe", "qual": None, "lead": None,
                    "flow": min(mS["CE"]["cuts_pct"], mS["PE"]["cuts_pct"]), "lvl": min(lv["CE"]["cuts"], lv["PE"]["cuts"], key=_rank),
                    "read": "both sides covering"}
        return {"code": "KHAMOSH", "name": "KUCH KHAAS NAHI", "qual": None, "lead": None, "flow": 0.0, "lvl": "NOISE", "read": "nothing above noise"}

    # -- the held picture
    def _hold(self, t, s, mS, spot, step, peers, read_word):
        m = mins(t)
        pic = self.pic
        hi60, lo60 = spot_range(self.grid, t, CHOP_OUT)
        recent = {d for m_, d in self.legs_seen if m - m_ <= CHOP_WIN}
        both_ways = (recent == {1, -1}) or (self.chop_on and {d for _, d in self.legs_seen} == {1, -1})
        self.chop_on = both_ways
        drift = spot - (self.day_open or spot)
        self.day_hi = max(getattr(self, "day_hi", spot), spot)
        self.day_lo = min(getattr(self, "day_lo", spot), spot)
        day_move = (self.day_hi - self.day_open) if drift >= 0 else (self.day_open - self.day_lo)   # the day's run so far
        day_dir = 1 if drift >= 0 else -1
        # 1. a running leg: update or end
        if pic and pic["word"] in ("CHAL RAHA", "WAPSI"):
            d = pic["dir"]
            new_ext = (spot > pic["ext"]) if d > 0 else (spot < pic["ext"])
            if new_ext:
                pic["ext"], pic["ext_t"] = spot, m
            with5 = mS[pic["L"]]["cuts"] + mS[pic["W"]]["adds"] if False else None   # with-flow over F is read from the F measures below
            mF = measures(self.grid, t, self.F, self.opens)
            wf = (mF[pic["L"]]["cuts"] + mF[pic["W"]]["adds"]) if mF and not mF.get("why") else 0.0
            af = mF[pic["L"]]["adds"] if mF and not mF.get("why") else 0.0
            pic["peak_with"] = max(pic.get("peak_with", 0.0), wf)
            pic["wf"], pic["af"] = wf, af
            pic["w5"].append((m, wf))
            prev = [x for mm_, x in pic["w5"] if mm_ == m - self.F]
            stalled = (m - pic["ext_t"]) >= STALL_MIN
            against_now = s["D"] == -d or (s.get("qual") == "ULTA")
            fading = wf <= THAK_X * pic["peak_with"] or af >= wf
            retrace = (pic["ext"] - spot) * d
            leg_size = (pic["ext"] - pic["start"]) * d
            reason = None
            if retrace >= max(LEG_RETRACE * leg_size, step):
                reason = f"price ne {retrace:.0f} pts wapas diye (leg {leg_size:.0f} pts)"
            elif s["D"] == -d and s["code"] not in ("BINA OI",) and self._held_opposite(d):
                reason = "ulta move shuru, OI uske saath"
            elif m - pic["ext_t"] >= LEG_STALE + RESUME_WIN:
                reason = f"{LEG_STALE + RESUME_WIN} min se naya {'high' if d > 0 else 'low'} nahi"
            elif pic.get("weak_for", 0) >= LEG_WEAK + RESUME_WIN:
                reason = f"{LEG_WEAK + RESUME_WIN} min KAMZOR"
            elif pic.get("flat_for", 0) >= LEG_FLAT:
                reason = f"{LEG_FLAT} min CHOP / PIN ki kahani"
            if reason:
                self.last_leg = max(leg_size, 0.0)                     # the size the next counter-leg is measured against
                if pic.get("stamped") and not pic.get("in_chop") and pic.get("was_mazboot"):
                    self.pending_end = {"t": t, "spot": spot, "title": f"MOVE {UP if d > 0 else DN} KHATAM", "why": reason, "due": m + 2}
                self.pic = None
                pic = None
            else:
                # phase
                paused = (m - pic["ext_t"]) >= LEG_STALE or pic.get("weak_for", 0) >= LEG_WEAK
                resumed = paused and s["D"] == d and s["Z"] == d and s["code"] not in ("BINA OI", "PHANS RAHE", "ROK RAHE")
                if resumed:
                    pic["ext_t"], pic["weak_for"] = m, 0          # S1: phir chal pada -- the same leg goes on
                    pic["resumed"] = pic.get("resumed", 0) + 1
                    pic["resume_pending"] = True
                if m - pic["since"] < PHASE_MIN:
                    phase = "SHURU"
                elif resumed:
                    phase = "PHIR CHAL PADA"
                elif prev and wf >= TEZ_X * max(prev[0], 1e-9) and (m - pic["ext_t"]) <= 3 and s["D"] == d:
                    phase = "TEZ"                                 # accelerating only on a minute that is itself a move
                elif stalled and fading:
                    phase = "THAK"
                elif stalled and not against_now:
                    phase = "RUKA"
                else:
                    phase = "JAARI"
                pic["phase"] = phase
                pic["story"] = s
                pic["flat_for"] = pic.get("flat_for", 0) + 1 if s["code"] in ("PIN BAN RAHA", "PIN TIKA", "KHAMOSH") and s["D"] == 0 else 0
                # WAPSI -> CHAL once the pullback has taken half the day's run for HOLD marks; never back
                if pic["word"] == "WAPSI":
                    back = (self.day_hi - spot) if d < 0 else (spot - self.day_lo)
                    big_now = back >= WAPSI_MAX * max(day_move, 1.0)
                    pic["big_for"] = pic.get("big_for", 0) + 1 if big_now else 0
                    if pic["big_for"] >= HOLD:
                        pic["word"] = "CHAL RAHA"
                        if pic.get("stamped") and pic.get("grade", {}).get("word") in (THEEK, MAZBOOT):
                            self._stamp(t, spot, "CHAL RAHA", f"CHAL RAHA {UP if d > 0 else DN}", f"wapsi badi ho gayi ({back:.0f} of the day's {day_move:.0f} pts): ab ek leg", pic, kind="phase")
                moving_now = (s["D"] == d and s["Z"] == d and s["code"] not in ("BINA OI", "PHANS RAHE", "ROK RAHE") and t < NEQ_LAST)
                broke = (pic.get("in_chop") and moving_now and pic.get("born_hi") is not None
                         and leg_size >= max(WAPSI_DRIFT * self.P, 1.5 * pic.get("born_range", 1e9))
                         and ((spot > pic["born_hi"]) if d > 0 else (spot < pic["born_lo"])))
                pic["moving_now"] = moving_now
                pic["broke_now"] = bool(pic.get("in_chop") and broke)
                if pic.get("in_chop") and broke:
                    pic["in_chop"] = False                    # chop se bahar: the swing is now the leg
                    pic["stamped"] = True
                    pic["broke_ever"] = True
                    self.legs_seen, self.chop_on = [], False
                    both_ways = False
                    self._stamp(t, spot, "CHAL RAHA", f"CHAL RAHA {UP if d > 0 else DN} · chop se bahar", f"{s['name']} · 60-min range toota · spot {s['m']:+.0f}/{self.S}m", pic, kind="picture")
                elif pic.get("in_chop") and not both_ways and moving_now:
                    pic["in_chop"] = False                    # the chop lapsed under it and this minute moves with OI: now a leg
                    pic["stamped"] = False
                    pic["ex_swing"] = True
                self._grade(pic, s, mS, peers, step, hi60, lo60)
                pic["weak_for"] = pic.get("weak_for", 0) + 1 if pic["grade"]["word"] == KAMZOR else 0
                self._stamp_leg(t, spot, pic, phase, read_word)
                return self._out(t, s, pic, read_word, chop=both_ways and pic.get("in_chop"))
        # 2. CHOP as the big word (legs both ways inside CHOP_WIN); a leg born inside it is a swing until the chop lapses
        chop_now = both_ways
        # 3. a new leg?
        if s["D"] and s["code"] not in ("BINA OI", "PHANS RAHE", "ROK RAHE") and s["Z"] != -s["D"]:
            backed = s["Z"] == s["D"] or s["code"] in ("DONO ENGINE", "BHAAG", "ROLL", "SAATH LIKH")
            strong = s["lvD"] == "BADA"
            ok = backed if chop_now else (backed or strong)
            if ok:
                cand = self._cand("LEG", (s["D"],))
                if cand >= HOLD:
                    d = s["D"]
                    start_row = self.rows[-HOLD]
                    pic = {"word": "CHAL RAHA", "dir": d, "since": m - HOLD + 1, "start": start_row["spot"], "ext": spot, "ext_t": m,
                           "born_range": (hi60 - lo60) if hi60 is not None else 1e9, "born_hi": hi60, "born_lo": lo60,
                           "L": s["L"], "W": s["W"], "w5": [], "peak_with": 0.0, "phase": "SHURU", "story": s, "in_chop": chop_now,
                           "stamped": False, "flat_for": 0, "weak_for": 0}
                    back0 = (self.day_hi - spot) if d < 0 else (spot - self.day_lo)
                    if day_move >= WAPSI_DRIFT * self.P and d * day_dir < 0 and back0 < WAPSI_MAX * day_move:
                        pic["word"] = "WAPSI"
                    xs = [self.grid[hm(mm_)]["spot"] for mm_ in range(m - HOLD + 1 - self.S, m - HOLD + 2) if hm(mm_) in self.grid]
                    if xs:
                        pic["start"] = min(xs) if d > 0 else max(xs)      # the leg's origin, not its birth minute
                    self.pic = pic
                    self._grade(pic, s, mS, peers, step, hi60, lo60)
                    self._stamp_leg(t, spot, pic, "SHURU", read_word)
                    return self._out(t, s, pic, read_word, chop=chop_now)
        # 4. flat pictures -- a PIN beats CHOP (both sides writing within 1:2 at one strike is the more specific read)
        code = s["code"]
        if code == "ATKA":
            self.atkas.append((m, s["lead"], s.get("k")))
            self.atkas = [x for x in self.atkas if m - x[0] <= TURN_WIN]
            other = [x for x in self.atkas if x[1] != s["lead"] and x[2] is not None and s.get("k") is not None and abs(x[2] - s["k"]) <= step]
            hi45, lo45 = spot_range(self.grid, t, TURN_WIN)
            m45 = measures(self.grid, t, TURN_WIN, self.opens)
            if (other and hi45 is not None and hi45 - lo45 < TURN_RANGE * self.P and m45 and not m45.get("why")
                    and m45["CE"]["net"] > 0 and m45["PE"]["net"] > 0
                    and min(m45["CE"]["adds"], m45["PE"]["adds"]) >= PIN_RATIO * max(m45["CE"]["adds"], m45["PE"]["adds"])):
                s = dict(s, code="PIN BAARI-BAARI", name=f"PIN BAARI-BAARI @ {s['k']:.0f}s", read="dono baari-baari likh rahe", dir=None, lead=None,
                         ev45=(m45["CE"]["adds"], m45["PE"]["adds"], hi45 - lo45))
                code = "PIN BAARI-BAARI"
                self.rows[-1] = s
        if s["code"] in ("PIN BAN RAHA", "PIN TIKA", "PIN BAARI-BAARI") and self._cand("FLAT", (s["code"], s.get("k"))) >= HOLD:
            key = (s["code"], s.get("k"))
            pic = self._flat(pic, "PIN", key, m, s, s)
            self._grade(pic, s, mS, peers, step, hi60, lo60)
            self._stamp_flat(t, spot, pic, read_word)
            return self._out(t, s, pic, read_word)
        if chop_now:
            key = ("CHOP",)
            if self._cand("CHOP", key) >= HOLD or (pic and pic["word"] == "CHOP"):
                pic = self._flat(pic, "CHOP", None, m, s, {"name": "CHOP · dono taraf legs", "read": "upar-neeche, kuch nahi ban raha"})
                pic["k"] = None
                self._grade(pic, s, mS, peers, step, hi60, lo60)
                self._stamp_flat(t, spot, pic, read_word)
                return self._out(t, s, pic, read_word)
        if code == "UNWIND" and any(x["word"] == "UNWIND" and m - mins(x["t"]) < 30 for x in self.stamps):
            code = "KHAMOSH"
        if code in ("ATKA", "PIN BAN RAHA", "PIN TIKA", "PIN BAARI-BAARI", "UNWIND"):
            key = (code, s.get("lead") or s.get("k"))
            held = self._cand("FLAT", key)
            if held >= HOLD or (pic and pic.get("key") == key):
                pic = self._flat(pic, "PIN" if code.startswith("PIN") else code, key, m, s, s)
                pic["dir"] = s.get("dir")
                self._grade(pic, s, mS, peers, step, hi60, lo60)
                self._stamp_flat(t, spot, pic, read_word)
                return self._out(t, s, pic, read_word)
        # 5. BINA OI (price moving, writers absent) or KHAMOSH
        word = "BINA OI" if (s["D"] and s["code"] == "BINA OI") else "KHAMOSH"
        key = (word, s["D"] if word == "BINA OI" else None)
        if self._cand("QUIET", key) >= HOLD or (pic and pic.get("key") == key):
            pic = self._flat(pic, word, key, m, s, s)
            pic["dir"] = s["D"] if word == "BINA OI" else None
            pic["grade"] = None
            recent_end = any(x["kind"] == "end" and m - mins(x["t"]) < 10 for x in self.stamps[-3:])
            recent_quiet = any(x["kind"] == "quiet" and m - mins(x["t"]) < 60 for x in self.stamps[-8:])
            recent_end = recent_end or recent_quiet
            if (self.last_stamped not in (None, "KHAMOSH", "BINA OI") and m - pic["since"] + 1 >= QUIET_MIN
                    and not pic.get("stamped") and not recent_end):
                pic["stamped"] = True
                self._stamp(t, spot, word, "KHAMOSH · kuch khaas nahi" if word == "KHAMOSH" else s["name"],
                            "koi flow noise se upar nahi" if word == "KHAMOSH" else "price akela, writer peeche nahi", pic, kind="quiet")
            return self._out(t, s, pic, read_word)
        # nothing held yet: keep the old picture (a flat one) or show the minute story small
        if pic and pic["word"] not in ("CHAL RAHA", "WAPSI"):
            return self._out(t, s, pic, read_word)
        self.pic = None
        return self._out(t, s, None, read_word)

    def _flat(self, pic, word, key, m, s, name):
        if pic and pic["word"] == word and pic.get("key") == key:
            pic["story"] = s
            return pic
        pic = {"word": word, "key": key, "since": m - HOLD + 1, "story": s, "name": name.get("name"), "read": name.get("read"),
               "stamped": False, "k": s.get("k"), "lead": s.get("lead")}
        self.pic = pic
        return pic

    def _cand(self, kind, key):
        """How many of the last marks carried this candidate (the story rows, newest last)."""
        n = 0
        for r in reversed(self.rows):
            rk = self._row_key(r, kind)
            if rk == key:
                n += 1
            else:
                break
        return n

    @staticmethod
    def _row_key(r, kind):
        if kind == "LEG":
            return (r["D"],) if r["D"] and r["code"] != "BINA OI" else None
        if kind == "CHOP":
            return ("CHOP",)        # handled by both_ways; any row counts while both_ways holds
        if kind == "FLAT":
            return (r["code"], r.get("lead") or r.get("k")) if r["code"] in ("ATKA", "PIN BAN RAHA", "PIN TIKA", "PIN BAARI-BAARI", "UNWIND") else None
        if kind == "QUIET":
            if r["D"] and r["code"] == "BINA OI":
                return ("BINA OI", r["D"])
            if not r["D"] and r["code"] == "KHAMOSH":
                return ("KHAMOSH", None)
        return None

    def _held_opposite(self, d):
        rows = self.rows[-HOLD:]
        return len(rows) == HOLD and all(r["D"] == -d and r["Z"] == -d for r in rows)

    # -- grade
    def _grade(self, pic, s, mS, peers, step, hi60, lo60):
        c = {}
        m = mins(s["t"])
        own_ok = s.get("lvl") in ("NOTABLE", "BADA", "STOCK")
        c["size"] = own_ok
        c["bada"] = s.get("lvl") == "BADA"
        # today's own as a second size check
        metric = "Z" if pic["word"] in ("ATKA",) else "zone" if pic["word"] in ("CHAL RAHA", "WAPSI") else "adds"
        own = self.own.get(metric) or []
        if len(own) >= OWN_MIN and s.get("flow") is not None:
            c["aaj"] = s["flow"] >= pct(own, P_NOTE)
        held = m - pic["since"] + 1
        c["tika5"] = held >= 5
        c["tika15"] = held >= 15
        if pic["word"] in ("CHAL RAHA", "WAPSI", "ATKA"):
            lead = s.get("lead") or pic.get("L")
            if lead:
                v = s["st"][lead]["votes"]
                up, dn = v[0] + v[2], v[1] + v[3]
                way = dn if s["st"][lead]["code"] in COVERING else up
                c["strikes"] = way >= 2 and way >= 2 / 3 * max(up + dn, 1)
        if pic["word"] in ("CHAL RAHA", "WAPSI"):
            c["price"] = s["m5"] * pic["dir"] > 0
        elif pic["word"] == "ATKA":
            c["price"] = abs(s["m5"]) < 0.25 * step
        elif pic["word"] in ("CHOP", "PIN"):
            if hi60 is not None:
                c["price"] = (hi60 - lo60) <= (2 * self.P if pic["word"] == "PIN" else 6 * self.P)
        f = self._fut(s["t"])
        if f is not None:
            if pic["word"] in ("CHAL RAHA", "WAPSI", "ATKA"):
                c["fut"] = f == (pic.get("dir") or s.get("dir"))
            elif pic["word"] in ("PIN",):
                c["fut"] = f == 0
        for o, p in (peers or {}).items():
            if p is None:
                continue
            c["peer_" + o] = p.get("word") == pic["word"] and p.get("dir") == pic.get("dir")
        if pic["word"] in ("CHAL RAHA", "WAPSI"):
            c["chop_bahar"] = not pic.get("in_chop")
        n, N = sum(1 for v in c.values() if v), len(c)
        word = MAZBOOT if N and n / N >= 0.6 else THEEK if N and n / N >= 0.4 else KAMZOR
        if not own_ok:
            word = KAMZOR
        if word == MAZBOOT and (pic.get("in_chop") or pic["word"] == "WAPSI" or s.get("patla") or s.get("aaj_ref") or s.get("edge")):
            word = THEEK
        pic["grade"] = {"n": n, "N": N, "word": word, "checks": c}

    def _fut(self, t):
        """+1 / -1 / 0 from the fut book: |dOI15| >= 0.10 % -> the sign of the fut price move; 0 quiet; None absent."""
        a, b = self.fut.get(t), self.fut.get(hm(mins(t) - 15))
        if not a or not b or not a.get("oi") or not b.get("oi") or a.get("c") is None or b.get("c") is None:
            return None
        doi = 100 * (a["oi"] - b["oi"]) / b["oi"]
        if abs(doi) < FUT_OI_PCT:
            return 0
        dp = a["c"] - b["c"]
        return 1 if dp > 0 else -1 if dp < 0 else 0

    # -- stamps
    def _flush_end(self, t, absorbed_by=None):
        pe = self.pending_end
        if not pe:
            return
        if absorbed_by:
            self.pending_end = None
            return
        if mins(t) >= pe["due"]:
            self.pending_end = None
            self.stamps.append({"t": pe["t"], "spot": pe["spot"], "kind": "end", "word": "KHATAM", "title": pe["title"], "why": pe["why"],
                                "grade": None, "extra": {}})

    def _stamp(self, t, spot, word, title, why, pic, kind="picture", extra=None):
        if kind == "picture" and self.pending_end:
            why = f"{why} · (pichhla move {self.pending_end['t']} par khatam)"
            self.pending_end = None
        g = pic.get("grade") if pic else None
        self.stamps.append({"t": t, "spot": spot, "kind": kind, "word": word, "title": title, "why": why,
                            "grade": f"{g['n']}/{g['N']} {g['word']}" if g else None, "extra": extra or {}})
        if kind in ("picture", "quiet"):
            self.last_stamped = word

    def _stamp_leg(self, t, spot, pic, phase, read_word):
        g = pic["grade"]
        d = pic["dir"]
        s = pic["story"]
        arrow = UP if d > 0 else DN
        if pic.get("in_chop"):
            return                                                  # the face shows the swing small; CHOP already said "swings"
        if not pic.get("stamped") and g["word"] in (THEEK, MAZBOOT):
            pic["stamped"] = True
            pic["stamp_t"] = t
            title = f"{pic['word']} {arrow} · {phase}" + (" · chop se bahar" if pic.get("ex_swing") else "")
            why = f"{s['name']} · spot {s['m']:+.0f} pts/{self.S}m · with {lakh(s.get('with'))} against {lakh(s.get('against'))}"
            ex = {"in_chop": pic.get("in_chop"), "phanse": s["st"][pic["L"]]["phanse"]}
            self._stamp(t, spot, pic["word"], title, why, pic, kind="picture", extra=ex)
            pic["phases_stamped"] = {phase}
            self._neq(t, spot, pic, read_word)
            return
        if pic.get("stamped"):
            ps = pic.setdefault("phases_stamped", set())
            age = mins(t) - pic["since"]
            if phase == "TEZ" and "TEZ" not in ps and g["word"] in (THEEK, MAZBOOT):
                ps.add("TEZ")
                if pic.get("stamp_t") and mins(t) - mins(pic["stamp_t"]) >= 5:      # M1: a stamp is never edited; a TEZ is a new line or nothing
                    self._stamp(t, spot, pic["word"], f"{pic['word']} {arrow} · TEZ", f"{s['name']} · spot {s['m']:+.0f} pts · with {lakh(s.get('with'))}", pic, kind="phase")
            if phase == "PHIR CHAL PADA" and pic.get("resume_pending") and g["word"] in (THEEK, MAZBOOT):
                pic["resume_pending"] = False
                self._stamp(t, spot, pic["word"], f"{pic['word']} {arrow} · PHIR CHAL PADA", f"{s['name']} · spot {s['m']:+.0f} pts/{self.S}m · with {lakh(s.get('with'))} against {lakh(s.get('against'))}", pic, kind="phase")
            if g["word"] == MAZBOOT:
                pic["was_mazboot"] = True
            if False and phase == "THAK" and "THAK" not in ps and age >= 10 and pic.get("was_mazboot"):   # THAK lives on the face
                ps.add("THAK")
                self._stamp(t, spot, pic["word"], f"{pic['word']} {arrow} · THAK RAHA", f"fuel fading, price ruka · with5 {lakh(pic.get('wf'))} against5 {lakh(pic.get('af'))} · peak with5 {lakh(pic.get('peak_with'))}", pic, kind="phase")
            self._neq(t, spot, pic, read_word)

    def _stamp_flat(self, t, spot, pic, read_word):
        g = pic.get("grade")
        if pic["word"] == "CHOP" and any(x["word"] == "CHOP" and mins(t) - mins(x["t"]) < 60 for x in self.stamps[-10:]):
            pic["stamped"] = True
            return
        if pic["word"] == "ATKA" and g and g["word"] != MAZBOOT:
            return                                                  # stamp cut 5: ATKA only at MAZBOOT
        if not pic.get("stamped") and g and g["word"] in (THEEK, MAZBOOT):
            pic["stamped"] = True
            s = pic["story"]
            why = s.get("read") or ""
            if pic["word"] == "ATKA":
                lead = s["lead"]
                why = f"{lead} {s['st'][lead]['chip']} · net {lakh(s['ZL'])} · spot {s['m']:+.0f} pts/{self.S}m"
            elif pic["word"] == "PIN":
                if s["code"] == "PIN BAARI-BAARI" and s.get("ev45"):
                    why = f"{s.get('read')} · 45m adds CE {lakh(s['ev45'][0])} PE {lakh(s['ev45'][1])} · range45 {s['ev45'][2]:.0f}"
                elif s["code"] == "PIN TIKA" and s.get("oi_k"):
                    why = f"{s.get('read')} · OI at {s['k']:.0f}: CE {lakh(s['oi_k'][0])} PE {lakh(s['oi_k'][1])} · range30 tight"
                else:
                    why = f"{s.get('read')} · 15m adds CE {lakh(s['st']['CE']['adds'])} PE {lakh(s['st']['PE']['adds'])}"
            elif pic["word"] == "CHOP":
                hi, lo = spot_range(self.grid, t, 30)
                why = f"legs dono taraf 30 min mein · range30 {hi - lo:.0f}"
            elif pic["word"] == "UNWIND":
                why = f"CE {lakh(s['st']['CE']['near'] + s['st']['CE']['wall'])} PE {lakh(s['st']['PE']['near'] + s['st']['PE']['wall'])}" + (" · band ka unwind" if t >= "15:00" else "")
            self._stamp(t, spot, pic["word"], f"{pic['word']}{(' ' + (UP if pic.get('dir') == 1 else DN)) if pic.get('dir') else ''}" + (f" @ {pic['k']:.0f}s" if pic.get("k") else ""), why, pic)
            self._neq(t, spot, pic, read_word)

    def _neq(self, t, spot, pic, read_word):
        """The contradiction line: only MAZBOOT, not WAPSI, not inside CHOP, and THE READ's word disagrees."""
        if not read_word or pic.get("neq_done"):
            return
        if any(x["kind"] == "neq" and mins(t) - mins(x["t"]) < 30 for x in self.stamps[-6:]):
            return
        g = pic.get("grade")
        if not g or g["word"] != MAZBOOT or pic["word"] == "WAPSI" or pic.get("in_chop"):
            return
        s0 = pic["story"]
        if t >= NEQ_LAST or s0.get("aaj_ref") or s0.get("edge") or self.kind == "EXPIRY":
            return                                                  # no contradiction on the index's own expiry day: pin / unwind mechanics, thin reference
        if pic["word"] != "CHAL RAHA":
            return                                                  # a flat picture never contradicts THE READ (26 Oct 11:13 CHOP vs TREND was noise)
        d = pic["dir"]
        if not pic.get("moving_now", s0["D"] == d and s0["Z"] == d):
            return                                                  # M3: a contradiction needs THIS minute moving with OI
        age = mins(t) - pic["since"]
        young = age <= NEQ_YOUNG or pic.get("broke_now")
        big = abs(s0["m"]) >= NEQ_MOVE * self.P and s0.get("lvD") == "BADA"
        still = s0["m5"] * d >= NEQ_M5 * (self.step_ or 50)
        lapsed = pic.get("ex_swing") and not pic.get("broke_now") and not pic.get("broke_ever")
        if not (young and big and still) or lapsed:
            return
        rw, rd = read_word
        if rw not in ("RANGE", "TREND", "LEAN"):
            return
        dis = False
        if pic["word"] == "CHAL RAHA":
            dis = (rw in ("RANGE", "WAIT", "BAN RAHA")) or (rw in ("TREND", "LEAN") and rd and rd != pic["dir"])
        elif pic["word"] in ("PIN", "CHOP", "ATKA"):
            dis = rw in ("TREND",)
        if dis:
            pic["neq_done"] = True
            s = pic["story"]
            line = f"READ: {rw}{(' ' + (UP if rd == 1 else DN)) if rd else ''} · RAFTAAR: {pic['word']}{(' ' + (UP if pic.get('dir') == 1 else DN)) if pic.get('dir') else ''} {g['n']}/{g['N']} — {s['name']} · spot {s['m']:+.0f}/{self.S}m · net {lakh(s['ZL'])}"
            pic["neq"] = line
            self._stamp(t, spot, "≠ READ", "≠ READ", line, pic, kind="neq")

    # -- could not check
    def _q(self, t, why, peers):
        row = self.grid.get(t) or {}
        spot = row.get("spot")
        if self.q_since is None:
            self.q_since = mins(t)
        elif mins(t) - self.q_since + 1 == Q_MIN and not why.startswith("PADH RAHE"):
            self._stamp(t, spot, "?", "?", why, None, kind="q")
        pic = {"word": "?", "dir": None, "phase": None, "since": None, "grade": None, "story": None, "qual": None, "read": None,
               "held": False, "in_chop": False, "k": None, "pending": None, "swing": None, "why": why}
        self.last = {"word": "?", "dir": None}
        self.pic_hist.append((mins(t), "?", None))
        return {"idx": self.idx, "t": t, "spot": spot, "picture": pic, "numbers": None, "sides": None, "contradiction": None,
                "stamps": self.stamps[-12:], "ref": self.ref.source(),
                "day_drift": None if spot is None or self.day_open is None else round(spot - self.day_open, 1)}

    def _out(self, t, s, pic, read_word, chop=False):
        self.q_since = None
        g = pic.get("grade") if pic else None
        word = pic["word"] if pic else "KHAMOSH"
        pending = None if pic else (None if s["code"] == "KHAMOSH" else s["name"])
        swing = None
        if chop and pic and pic["word"] in ("CHAL RAHA", "WAPSI"):
            swing = {"dir": pic["dir"], "phase": pic.get("phase"), "story": s["name"], "grade": g, "since": hm(pic["since"])}
            word, g = "CHOP", None
        big = {"word": word, "dir": None if swing else ((pic or {}).get("dir") if pic else None), "pending": pending,
               "swing": swing, "why": None,
               "phase": (pic or {}).get("phase"), "since": hm((pic or {}).get("since")) if pic and pic.get("since") is not None else None,
               "grade": {"n": g["n"], "N": g["N"], "word": g["word"], "checks": g["checks"]} if g else None,
               "story": s["name"], "qual": s.get("qual"), "read": s.get("read"), "held": bool(pic),
               "in_chop": (pic or {}).get("in_chop", False), "k": (pic or {}).get("k")}
        sides = {}
        for side in ("CE", "PE"):
            st, sp = s["st"][side], s["speed"][side]
            sides[side] = {"structure": st["code"], "chip": st["chip"],
                           "strikes": [{"k": k, "d": d, "L": lakh(d)} for k, d in st["strikes"]],
                           "near_L": lakh(st["near"]), "wall_L": lakh(st["wall"]), "adds_L": lakh(st["adds"]), "cuts_L": lakh(-st["cuts"]),
                           "votes": st["votes"], "phanse": [{"k": k, "built_L": lakh(b), "till": tt} for k, b, tt in st["phanse"]],
                           "speed": sp["word"], "speed_now_L_min": lakh(sp["now_L"] * (1 if sp["sign"] >= 0 else -1)),
                           "level": s["lv"][side]}
        self._side_events(t, s)
        return {"idx": self.idx, "t": t, "spot": s["spot"], "picture": big, "numbers": {"m15": round(s["m"], 1), "m5": round(s["m5"], 1),
                "net_L": lakh(s["ZL"]), "Z_pct": round(s["Zpct"], 3), "D_level": s["lvD"], "Z_level": s["lvZ"], "patla": s["patla"],
                "edge": s["edge"], "aaj_ref": s["aaj_ref"], "nine_oi_L": lakh(s["Wt"]), "P": round(self.P, 1)},
                "sides": sides, "contradiction": (pic or {}).get("neq"), "stamps": self.stamps[-12:], "ref": self.ref.source(),
                "day_drift": round(s["spot"] - (self.day_open or s["spot"]), 1)}

    def _side_events(self, t, s):
        """ROLL · BADA cover into price · PHIR LIKHNE LAGE · roll toota, once per side per EV_GAP, 2+ strikes."""
        m = mins(t)
        for side in ("CE", "PE"):
            st = s["st"][side]
            code = st["code"]
            v = st["votes"]
            leg_live = bool(self.pic and self.pic.get("word") in ("CHAL RAHA", "WAPSI"))
            if leg_live and code != "RUKE" and not (code in WRITING and st.get("ruke_for", 0) >= RESTART_MIN):
                continue
            if m - self.ev_last.get(side, -999) < EV_GAP:
                # roll toota: a ROLL event followed within 3 min by the same side covering everywhere with a new extreme
                if code in ("BHAAG RAHE", "ITM COVER") and self.roll_mark.get(side) and m - self.roll_mark[side] <= 3 and s["D"]:
                    rm = self.roll_mark[side]
                    self.roll_mark[side] = None
                    self._stamp(t, s["spot"], "ROLL TOOTA", f"{side} ROLL TOOTA", f"roll {hm(rm)} ka toota, ab {st['chip']} · {', '.join(f'{k:.0f} {lakh(d)}' for k, d in st['strikes'][:2])}", None, kind="event")
                continue
            if code == "ROLL" and (v[1] + v[3]) >= 2 and self.notable(s["lv"][side]["zone"]):
                k2 = max((k for k, d in st["strikes"] if d > 0), default=None)
                last_roll = getattr(self, "roll_last", {}).get(side)
                if last_roll and m - last_roll[0] < 60 and last_roll[1] == k2:
                    continue
                self.roll_last = getattr(self, "roll_last", {})
                self.roll_last[side] = (m, k2)
                self.ev_last[side] = m
                self.roll_mark[side] = m
                self._stamp(t, s["spot"], "ROLL", f"{side} {'CAP UPAR' if side == 'CE' else 'FLOOR NEECHE'} SHIFT",
                            f"roll, abhi bhi short · {', '.join(f'{k:.0f} {lakh(d)}' for k, d in st['strikes'])}", None, kind="event")
            elif False and code in ("BHAAG RAHE", "ITM COVER") and s["lv"][side]["cuts"] == "BADA" and (v[1] + v[3]) >= 2 and not s["D"] \
                    and not (self.pic and self.pic.get("L") == side):
                self.ev_last[side] = m
                self._stamp(t, s["spot"], "BHAAG", f"{side} BHAAG RAHE · price unke against",
                            f"{', '.join(f'{k:.0f} {lakh(d)}' for k, d in st['strikes'] if d < 0)}" + (f" · PHANSE {st['phanse'][0][0]:.0f} {lakh(st['phanse'][0][1])} {st['phanse'][0][2]} tak" if st["phanse"] else ""), None, kind="event")
            elif code in WRITING and s["lv"][side]["adds"] == "BADA" and (v[0] + v[2]) >= 2 and st.get("ruke_for", 0) >= RESTART_MIN:
                self.ev_last[side] = m
                self._stamp(t, s["spot"], "PHIR LIKHNE LAGE", f"{side} PHIR LIKHNE LAGE ({st['ruke_for']} min ruk ke)",
                            f"{', '.join(f'{k:.0f} {lakh(d)}' for k, d in st['strikes'] if d > 0)}", None, kind="event")


def _rank(lvl):
    return {"BADA": 3, "NOTABLE": 2, "STOCK": 2, "NOISE": 1, None: 0}.get(lvl, 0)


def _biggest(z, sign=1):
    per = z["per"]
    return max(per, key=lambda k: sign * per[k]) if per else None


def read(idx, day, grid, ref=None, kind="NORMAL", opens=None, fut=None, read_words=None, peers_hist=None):
    """Whole-day convenience: run every minute in order; returns (last picture, engine)."""
    eng = Engine(idx, day, ref, kind, opens, fut)
    out = None
    for t in sorted(grid):
        rw = _read_word_at(read_words, t) if read_words else None
        peers = {o: _peer_at(h, t) for o, h in (peers_hist or {}).items()}
        out = eng.step(t, grid[t], peers=peers, read_word=rw)
    return out, eng


def _read_word_at(words, t):
    last = None
    for tt, w, d in words:
        if tt <= t:
            last = (w, d)
        else:
            break
    return last


def _peer_at(hist, t):
    m = mins(t)
    for mm_, w, d in reversed(hist):
        if m - PEER_LAG <= mm_ <= m:
            return {"word": w, "dir": d}
        if mm_ < m - PEER_LAG:
            break
    return None


# ---- self-check ----------------------------------------------------------------------------------------------------------

def check():
    """Flat 40 min, then +6 pts/min with the ITM calls covering and puts adding: KHAMOSH / PIN first, then CHAL RAHA ▲ with
    a leg object, SAATH, THEEK or better, and at most one picture stamp for the leg."""
    ks = [22500 + 50 * i for i in range(17)]
    grid, opens = {}, {str(k): [1e6, 1e6] for k in ks}
    for m in range(0, 70):
        t = hm(9 * 60 + 16 + m)
        spot = 22850 + max(0, m - 40) * 6
        k = {}
        for s in ks:
            ce = (-(m - 40) * 4e4 if m > 40 and s <= 22850 else 0) + m * 300 * (1 + (s % 7))
            pe = ((m - 40) * 4e4 if m > 40 and s <= 22900 else 0) + m * 300 * (1 + (s % 5))
            k[str(s)] = [ce, pe]
        grid[t] = {"spot": spot, "k": k}
    # a synthetic reference: every session identical, mid-size flows
    table = {f"2026-09-{d:02d}": {"kind": "NORMAL", "parts": {str(p): {"zone": [0.3, 0.6, 1.2], "adds": [0.5, 1.0, 2.0], "cuts": [0.3, 0.6, 1.2],
                                                                        "Z": [0.3, 0.6, 1.2], "D": [10, 25, 45], "fast": [0.3, 0.6, 1.2]} for p in range(4)}}
             for d in range(1, 9)}
    out, eng = read("NIFTY", "2026-10-01", grid, Ref(table), "NORMAL", opens)
    assert out["picture"]["word"] == "CHAL RAHA" and out["picture"]["dir"] == 1, out["picture"]
    assert out["picture"]["qual"] == "SAATH", out["picture"]["qual"]
    assert out["sides"]["CE"]["structure"] in COVERING and out["sides"]["PE"]["structure"] in WRITING, (out["sides"]["CE"]["structure"], out["sides"]["PE"]["structure"])
    assert out["picture"]["grade"]["word"] in (THEEK, MAZBOOT), out["picture"]["grade"]
    legs = [s for s in eng.stamps if s["kind"] == "picture" and s["word"] == "CHAL RAHA"]
    assert len(legs) == 1, [s["title"] for s in eng.stamps]
    early = [r["code"] for r in eng.rows if r["t"] < "09:55"]
    assert early and all(c in ("KHAMOSH", "PIN BAN RAHA", "PIN TIKA", "ATKA") for c in early), set(early)
    print("check ok:", out["picture"]["word"], out["picture"]["dir"], out["picture"]["grade"], "| stamps:", [s["title"] for s in eng.stamps])


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        check()
    else:
        print(__doc__)
