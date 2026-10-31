"""legs.py -- THE LEG: pause or reversal, read causally, minute by minute (docs/kahani/review/NOISE-DECODER-BRAINSTORM.md,
rounds 1-2 as amended by the "Merged decision" of 30 Oct; her words: "noise is also give a message").

`read(d, chain=None, marks=None) -> {"rows", "day", "pauses", "missing"}` over a jarvis.build frame `d`. Pure: no I/O,
no clock, nothing written. Causal: row i reads minutes <= i only. The one object is the LEG (origin -> extreme, >= 40 pts
and >= 2U at its start);
its direction is the lean and changes only at PALAT (half the leg given back, floored at 1U). A leg is a TREND after
10:00 at >= 80 pts with 1.5 sigma, a TOOT or Jarvis's own fuel; before 10:00 only at >= 100 pts with a TOOT; else
OPENING / ROTATION (no lean on the open); every row with a leg before 10:00 reads OPENING, its lean shown and never
announced (Jarvis v3). Inside a pause the word is HOLD (no risk item; "clean" with k1 loading),
WATCH (>= 2 risk items) or PALAT? (>= 3, or 0.35 of the leg back, or speed FAST against), PALAT? shown only once
confirmed at a 3-min close or after 6 min, latched while true, on screen >= 6 min, never carried stale. Writers +/-7 and
Sides are shown at a pause tagged "(lagging)": with the leg at 17 of 19 reversals on the record. RISK is never a word.
Every threshold is a named constant with an [I] comment. A missing input makes its item absent and is named in the
row's `missing` (rule 6: "could not check" is its own sentence, never a silent zero). Counts, never a rate. DISPLAY
ONLY: no order path, no gate.

Inputs beyond the frame (both optional):
  chain  {"HH:MM": {"spot": float, "ce": {strike: {"ltp": float, "delta": float}}, "pe": {...}}}  per chain minute,
         strikes near ATM (int / float / str keys all fine): the ATM trend-side premium vs delta read (R2.3)
  marks  her ofd_marks2 rows for the day as recorded: [{"id", "t" (epoch ms, the 5-min bar's start), "kind", "name",
         "winner" (+1 / -1), "p", "prov", ...}]; first row per id wins; known at bar close + MARK_LAG (R2.1)
"""
from __future__ import annotations

# ---- every threshold [I], the reason beside it (counts from the 10-day record, CONT vs REV after 10:00) ----------------
START_M = 555          # 09:15, her 3-min bars count from here
OPEN_M = 600           # 10:00: the open is its own regime (65 of 119 events before it, reversals clustered there)
LEG_MIN = 40           # [I] a leg: 40 pts origin -> extreme (~0.2 %; under it is tick noise) ...
LEG_MIN_U = 2.0        # [I] ... and at least 2U at the day's first leg (U = max(sigma, 0.1 % of price), the stack's unit):
                       #     before 10:00 sigma is 10-15 pts, so a 40-pt swing is noise (30 Oct flipped the lean 7x in 38 min).
                       #     The start only: a 2U floor on a PALAT's own leg would pin a wrong lean on a wide day
TREND_PTS = 80         # [I] after 10:00 a trend leg is >= 80 pts (~2U on a quiet day) ...
TREND_Z = 1.5          # [I] ... that reached 1.5 sigma of the session VWAP (23/35 vs 6/19), or had a TOOT, or was fuelled
OPEN_PTS = 100         # [I] before 10:00 only >= 100 pts (10/35 vs 2/30) with a TOOT counts; sigma means nothing yet
PAUSE_U = 0.25         # [I] a pause: 0.25U back from the extreme (the stack's break distance, HOLD v2 / marks TOOTA)
PAUSE_MIN = 6          # [I] or no new extreme for 6 min (two of her 3-min bars)
NEW_U = 0.25           # [I] a real new extreme: 0.25U past the pause's extreme (a 3-pt new low is not "running")
REV_FRAC = 0.5         # [I] PALAT: half the leg given back ...
REV_U = 1.0            # [I] ... floored at 1U (U = max(sigma, 0.1 % of price), the stack's unit)
SHALLOW = 0.20         # [I] shallow pullback: < 0.20 of the leg after SHALLOW_MIN (21/31 vs 5/17 one bar in)
SHALLOW_MIN = 3        # [I] one 3-min bar into the pause before "shallow" means anything
DEEP = 0.35            # [I] PALAT?: 0.35 of the leg given back (0/31 vs 6/17 one bar in)
K_MIN = 9              # [I] the strike-OI window: 9 min (three 3-min bars)
K1_L = 2.0             # [I] k1 loading / emptying: 2L in 9 min (the handshake's CUT_L floor); loading 14/34 vs 2/19
BAND_L = 4.0           # [I] k1..k3 emptying: 4L in 9 min (7/10 vs 6/23 one bar in, 27 Oct out)
D3_AGAINST = 150       # [I] 3-min delta against >= 150 lots (the push floor MIN_PUSH)
FAST = 2.0             # [I] speed FAST: |3-min delta| >= 2x its own median so far (jarvis.FAST)
SPEED_WARM = 10        # [I] the median needs 10 bars
PREM_RS = 0.5          # [I] ATM premium vs delta: 0.5 Rs (10 ticks) beyond what delta explains; holding 10/27 vs 2/16
COIL = 0.5             # [I] coiling: the pause's range <= 0.5x the 9 min before the extreme (21/35 vs 7/19)
Z_INSIDE = 1.0         # [I] back inside 1 sigma after a >= TREND_Z leg: the band is the trend's home
MARK_BAR = 5           # her footprint bars are 5 min
MARK_LAG = 1           # [I] a mark is known at bar close + 1 min (ofd_marks2 has no first-seen stamp; R2.1)
MARK_NEAR_U = 1.0      # [I] a mark counts within 1U of the leg's extreme
MARK_LATE_MIN = 10     # [I] a mark first appended after a row whose bar is >= 10 min later was revised late
MARK_FRESH_MIN = 15    # [I] a mark is a risk item for 15 min after it became known (three of her bars); then a note "old":
                       #     on 29 Oct one mark near the 10:30 extreme kept PALAT? on for 3 hours of a 0.05-0.12 pullback
PREM_FRESH = 15        # [I] the premium read is anchored at the leg's extreme for 15 min (R2.3's +0 / +3 reads unchanged),
                       #     then at the minute 15 min ago: theta / IV crush over a long pause is not "bleeding"
Z_RETRACE_MIN = SHALLOW  # [I] inside 1 sigma counts only when price came back >= 0.20 of the leg, not when VWAP walked up
WATCH_N = 2            # [I] WATCH at >= 2 risk items (12/19 reversals, 9/35 continuations)
PALAT_N = 3            # [I] PALAT? at >= 3 risk items (0/31 vs 6/17 one bar in)
CONFIRM_MIN = 6        # [I] PALAT? confirmed after 6 min of its condition, or at a 3-min close
MIN_SHOW = 6           # [I] a confirmed PALAT? stays on screen 6 min (flicker halved on 8 of 9 days)
HOLD_MIN = 3           # [I] WATCH -> HOLD waits one 3-min bar (no flicker); HOLD -> WATCH / PALAT? shows at once
PUSH_WIN = 10          # [I] a push with the leg in the last 10 min (23/35 vs 9/19)
WF_L, WF_STOP = 10.0, -2.0   # jarvis's +/-7 leg bars, for the (lagging) note and the fuelled read
FUT_WIN, FUT_LOTS, FUT_PTS = 30, 500, 15   # [I] the slow fut-OI quadrant: 500 lots and 15 pts over 30 min
HORIZON = 45           # [I] the after-the-fact outcome window (the forward log), minutes
MARK_AGAINST = ("absorption", "exhaustion", "trap", "climax", "E6", "E7", "E3", "E1")
REV = "legs-1 (merged decision 30 Oct)"
UP, DN = "▲", "▼"


def m2i(s):
    return int(s[:2]) * 60 + int(s[3:5])


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def _fmt(x):
    """1,23,456 (en-IN), as the rest of the screen writes levels."""
    n = int(x + 0.5) if x >= 0 else -int(-x + 0.5)
    s = str(abs(n))
    if len(s) > 3:
        h, s = s[:-3], s[-3:]
        while len(h) > 2:
            h, s = h[:-2], h[-2:] + "," + s
        s = h + "," + s
    return ("-" if n < 0 else "") + s


def _sg(x, nd=0):
    return ("+" if x >= 0 else "−") + (f"{abs(x):.{nd}f}" if nd else _fmt(abs(x)))


def _med(xs):
    s = sorted(xs)
    return s[len(s) // 2] if s else None


def _sides_fuel(s):
    if not s or s.get("fuel_side") not in ("ce", "pe"):
        return None
    dr = 1 if s["fuel_side"] == "ce" else -1
    if s.get("word") in ("REAL", "BACKED"):
        return dr
    if s.get("word") == "SQUEEZE" and (s.get("p") if dr > 0 else s.get("c")) == "FLAT":
        return dr
    return None


def _jarvis_words(d):
    """Jarvis's own call word per minute (the rule of jarvis.call: the writers and one more read agree), from the frame's
    reads / timeline / sides -> ["UP" | "DOWN" | None]; None for the whole day when the frame has no reads."""
    r, tl = d.get("reads") or {}, d.get("timeline") or []
    W, SP, SY = r.get("writers"), r.get("speed"), r.get("sync")
    if not W or not SP or len(tl) < len(d["mins"]):
        return None
    out, slot = [], None
    sides = sorted((s for s in d.get("sides") or () if s.get("t")), key=lambda s: s["t"])
    for i, t in enumerate(d["mins"]):
        while sides and sides[0]["t"] <= t:
            slot = sides.pop(0)
        w, sp, sy, fu, fst = W[i], SP[i], (SY[i] if SY else None), tl[i].get("fuel"), tl[i].get("fuel_state")
        s_dir = _sides_fuel(slot) or 0
        w_dirs = {w["dir"] if w.get("state") in ("UP", "DOWN", "BACK") else 0, w.get("push") or 0}
        ok = []
        for dr in (1, -1):
            first = s_dir == dr or dr in w_dirs
            more = (fst == "LIVE" and fu and fu.get("dir") == (UP if dr > 0 else DN)) or \
                   (sp.get("word") == "FAST" and sp.get("dir") == dr) or (bool(sy) and sy.get("dir") == dr)
            if first and more:
                ok.append(dr)
        out.append(("UP" if ok[0] > 0 else "DOWN") if len(ok) == 1 else None)
    return out


def _marks(marks):
    """ofd_marks2 rows -> [{known_m, bar_m, kind, name, winner, p, late}], first row per id (R2.1)."""
    out, seen, maxt = [], set(), 0
    for r in marks or ():
        t = r.get("t")
        if r.get("id") in seen or not isinstance(t, (int, float)):
            continue
        seen.add(r.get("id"))
        bar_m = ((int(t // 1000) + 19800) % 86400) // 60          # IST minute of the day
        out.append({"known_m": bar_m + MARK_BAR + MARK_LAG, "bar_m": bar_m, "kind": r.get("kind"), "name": r.get("name"),
                    "winner": r.get("winner"), "p": r.get("p"), "prov": bool(r.get("prov")),
                    "late": t < maxt - MARK_LATE_MIN * 60 * 1000})
        maxt = max(maxt, t)
    return out


def wall_behind_broke(pushes, lean, m):
    """The latest push AGAINST the lean whose answer BROKE (TOOT) or TRAPPED (PHANS) the wall behind, pushed in the last
    PUSH_WIN min and known by minute m (the minute after its read, as jarvis.build's final_ans) -> the push or None. One
    rule for the leg's risk item and Jarvis's ACTION word (jarvis.action_words): the chip and the word never disagree."""
    got = [p for p in pushes or () if not p.get("artifact") and p.get("dir") == -lean
           and p.get("ans") in ("TOOT", "PHANS") and p.get("am") and m - PUSH_WIN < m2i(p["t"]) <= m and m2i(p["am"]) < m]
    return got[-1] if got else None


def _lad(d, t, side, k):
    L = (d.get("ladder") or {}).get(t)
    if not L:
        return None
    for key, v in L.get(side, {}).items():
        try:
            if float(key) == float(k):
                return v
        except (TypeError, ValueError):
            continue
    return None


def _chain_leg(chain, t, side, k):
    row = (chain or {}).get(t)
    if not row:
        return None, None
    for key, v in (row.get(side) or {}).items():
        try:
            if float(key) == float(k):
                return v, row.get("spot")
        except (TypeError, ValueError):
            continue
    return None, row.get("spot")


def read(d: dict, chain: dict | None = None, marks: list | None = None) -> dict:
    """The LEG rows for one frame -> {"rows": [per minute], "day": {"flips", "fut_oi"}, "pauses": [...], "missing": [...]}."""
    mins = d["mins"]
    N = len(mins)
    M = [m2i(t) for t in mins]
    ix = {m: i for i, m in enumerate(M)}
    fut, fhi, flo = d["fut"], d.get("fhi") or d["fut"], d.get("flo") or d["fut"]
    spot, vw, sd, oi = d.get("spot") or fut, d["vwap"], d["sd"], d.get("oi") or [None] * N
    flow = d.get("flow") or d.get("delta") or [None] * N
    step = d.get("step") or 50
    pushes = [p for p in d.get("pushes") or () if not p.get("artifact")]
    wf_ce, wf_pe = d.get("wf_ce") or [None] * N, d.get("wf_pe") or [None] * N
    sides = sorted((s for s in d.get("sides") or () if s.get("t")), key=lambda s: s["t"])
    jw = _jarvis_words(d)
    mk = _marks(marks)
    missing_all = []
    if chain is None:
        missing_all.append("could not check: ATM premium vs delta (no chain extra passed)")
    if marks is None:
        missing_all.append("could not check: her footprint marks (none passed)")
    if jw is None:
        missing_all.append("could not check: fuelled (the frame has no reads / timeline)")

    def at(m):
        return ix.get(m)

    def s3(i):
        xs = [flow[j] for j in (at(M[i] - 2), at(M[i] - 1), i) if j is not None]
        return None if len(xs) < 3 or any(x is None for x in xs) else sum(xs)

    def U_at(i):
        return max(sd[i] or 0.0, 0.001 * fut[i])

    # ---- state ----------------------------------------------------------------------------------------------------------
    d_, org, orgi, ext, exti = 0, fut[0], 0, fut[0], 0
    zx_max, toot_t, fuel_t = 0.0, None, None
    pause_ext, pause_i = None, None
    last_word, word_since = None, -99
    raw_run, latched, shown_since = 0, False, None
    flips, hist = 0, []
    rows, pauses, fut_oi, flips_pm = [], [], [], []
    slot_i, slot = 0, None

    for i in range(N):
        t, m, U = mins[i], M[i], U_at(i)
        row = {"t": t, "lean": 0, "leg": None, "word": "NO LEG", "line": "", "alive": [], "risk": [], "notes": [],
               "missing": []}
        # the speed median (for FAST against), the Sides slot
        x3 = s3(i)
        sp_x = None if x3 is None or len(hist) < SPEED_WARM or not _med(hist) else abs(x3) / _med(hist)
        if x3 is not None:
            hist.append(abs(x3))
        while slot_i < len(sides) and sides[slot_i]["t"] <= t:
            slot = sides[slot_i]
            slot_i += 1
        # the slow fut-OI quadrant (DAY line)
        j30 = at(m - FUT_WIN)
        q = None
        if j30 is not None and oi[i] is not None and oi[j30] is not None:
            dp, doi = fut[i] - fut[j30], oi[i] - oi[j30]
            if abs(doi) >= FUT_LOTS and abs(dp) >= FUT_PTS:
                q = {"word": ("fresh longs" if doi > 0 else "short covering") if dp > 0 else ("fresh shorts" if doi > 0 else "long unwinding"),
                     "lots": round(doi), "pts": round(dp)}
        fut_oi.append(q)

        # ---- the leg ------------------------------------------------------------------------------------------------------
        if d_ == 0:
            lo_i, hi_i = min(range(i + 1), key=lambda j: flo[j]), max(range(i + 1), key=lambda j: fhi[j])
            floor = max(LEG_MIN, LEG_MIN_U * U)
            if fhi[i] - flo[lo_i] >= floor:
                d_, orgi, org, ext, exti = 1, lo_i, flo[lo_i], fhi[i], i
                zx_max, toot_t, fuel_t = 0.0, None, None
            elif fhi[hi_i] - flo[i] >= floor:
                d_, orgi, org, ext, exti = -1, hi_i, fhi[hi_i], flo[i], i
                zx_max, toot_t, fuel_t = 0.0, None, None
        if d_ == 0:
            row["line"] = f"NO LEG · no {floor:.0f}-pt swing yet"
            row["missing"] = list(missing_all)
            rows.append(row)
            flips_pm.append(flips)
            continue
        arrow, other = (UP, DN) if d_ > 0 else (DN, UP)
        px_ext = fhi[i] if d_ > 0 else flo[i]
        if d_ * (px_ext - ext) > 0:
            ext, exti = px_ext, i
        if sd[i]:
            zx_max = max(zx_max, d_ * (ext - vw[i]) / sd[i])
        if jw and jw[i] == ("UP" if d_ > 0 else "DOWN") and fuel_t is None:
            fuel_t = t
        if toot_t is None:
            for p in pushes:
                if p.get("dir") == d_ and p.get("ans") == "TOOT" and p.get("am") and M[orgi] <= m2i(p["t"]) <= m and m2i(p["am"]) <= m:
                    toot_t = p["t"]
                    break
        A = d_ * (ext - org)
        r = d_ * (ext - fut[i])
        rf = r / A if A else 0.0
        leg = {"dir": d_, "origin": org, "origin_t": mins[orgi], "extreme": ext, "extreme_t": mins[exti], "pts": round(A),
               "sigma_max": round(zx_max, 2), "toot": toot_t, "fuelled": fuel_t, "retrace": round(rf, 2),
               "since": m - M[exti], "quality": None, "k1": None}

        # PALAT: the leg gives back half (floored at 1U) -> the lean flips here and only here
        if A >= LEG_MIN and r >= max(REV_FRAC * A, REV_U * U):
            flips += 1
            leg["quality"] = "PALAT"
            row.update(lean=-d_, leg=leg, word="PALAT",
                       line=f"PALAT {other} · leg {arrow} {A:.0f} pts gave back {r:.0f} ({rf:.2f}) · new leg {other} from {_fmt(ext)}f")
            row["missing"] = list(missing_all)
            rows.append(row)
            flips_pm.append(flips)
            d_, org, orgi = -d_, ext, exti
            ext, exti = (flo[i] if d_ < 0 else fhi[i]), i
            zx_max, toot_t, fuel_t, pause_ext, pause_i = 0.0, None, None, None, None
            raw_run, latched, shown_since, last_word = 0, False, None, None
            continue
        flips_pm.append(flips)

        early = m < OPEN_M
        trend = (A >= OPEN_PTS and toot_t is not None) if early else \
                (A >= TREND_PTS and (zx_max >= TREND_Z or toot_t is not None or fuel_t is not None))
        quality = "TREND" if trend else ("OPENING" if early else "ROTATION")
        leg["quality"] = quality
        s = spot[i] if spot[i] is not None else fut[i]
        k1 = (s // step + 1) * step if d_ > 0 else (s // step) * step
        leg["k1"] = k1
        row.update(lean=d_, leg=leg)
        why_leg = f"{A:.0f} pts · {zx_max:.1f}σ" + (f" · TOOT {toot_t}" if toot_t else " · no TOOT") + (f" · fuelled {fuel_t}" if fuel_t else "")
        row["missing"] = list(missing_all)

        if not trend:
            row["word"] = quality
            row["line"] = (f"OPENING {arrow} {why_leg} · no lean until {OPEN_PTS} pts + TOOT" if early else
                           f"ROTATION {arrow} {why_leg} · not a trend leg")
            raw_run, latched, shown_since = 0, False, None
            rows.append(row)
            continue

        # a pause begins at 0.25U back or 6 min without a new extreme; it ends only at a real new extreme (0.25U past)
        if pause_ext is None and (r >= PAUSE_U * U or m - M[exti] >= PAUSE_MIN):
            pause_ext, pause_i = ext, i
        if pause_ext is not None and d_ * (ext - pause_ext) >= NEW_U * U:
            pause_ext, pause_i = None, None
        if pause_ext is None:
            row["word"] = "TREND"
            row["line"] = f"TREND {arrow} running · {why_leg} · {_fmt(org)}f → {_fmt(ext)}f"
            raw_run, latched, shown_since, last_word = 0, False, None, None
            rows.append(row)
            continue

        # ---- the items at a pause ------------------------------------------------------------------------------------------
        alive, risk, notes, miss = [], [], [], []
        side, SIDE = ("ce", "CE") if d_ > 0 else ("pe", "PE")
        # k1 / band ahead, 9-min OI change
        t9 = mins[at(m - K_MIN)] if at(m - K_MIN) is not None else None
        if t9 is None or not (d.get("ladder") or {}).get(t) or not (d.get("ladder") or {}).get(t9):
            miss.append(f"could not check: k1 OI (ladder missing at {t if not (d.get('ladder') or {}).get(t) else hm(m - K_MIN)})")
        else:
            ks = [k1 + j * step * d_ for j in range(3)]
            ch = []
            for k in ks:
                a, b = _lad(d, t, side, k), _lad(d, t9, side, k)
                ch.append(None if a is None or b is None else a - b)
            if ch[0] is None:
                miss.append(f"could not check: k1 OI ({_fmt(k1)}s {SIDE} not on the ladder)")
            else:
                band = None if any(c is None for c in ch) else sum(ch)
                if ch[0] >= K1_L:
                    alive.append({"k": "k1_loading", "text": f"{_fmt(k1)}s {SIDE} loading {_sg(ch[0], 1)}L / {K_MIN} min"})
                if ch[0] <= -K1_L or (band is not None and band <= -BAND_L):
                    risk.append({"k": "band_emptying", "text": f"{SIDE} band ahead {_fmt(ks[0])}–{_fmt(ks[-1])}s emptying "
                                                                f"{_sg(band if band is not None else ch[0], 1)}L / {K_MIN} min"})
        # shallow / coiling
        since = m - M[exti]
        if since >= SHALLOW_MIN and rf < SHALLOW:
            alive.append({"k": "shallow", "text": f"shallow {rf:.2f} of the leg after {since} min"})
        j9 = at(M[exti] - K_MIN)
        if j9 is not None and i > exti:
            before = max(fhi[j9:exti + 1]) - min(flo[j9:exti + 1])
            pr = max(fhi[exti:i + 1]) - min(flo[exti:i + 1])
            if before and pr <= COIL * before:
                alive.append({"k": "coiling", "text": f"coiling {pr:.0f} pts vs {before:.0f} the 9 min before"})
        # ATM trend-side premium vs delta, anchored at the leg's extreme while the pause is young, then PREM_FRESH min back
        if chain is not None:
            j0 = exti if m - M[exti] <= PREM_FRESH else next(j for j in range(exti, i + 1) if M[j] >= m - PREM_FRESH)
            atm = round((spot[j0] if spot[j0] is not None else fut[j0]) / step) * step
            a, sa = _chain_leg(chain, mins[j0], side, atm)
            b, sb = _chain_leg(chain, t, side, atm)
            if not a or not b or any(not isinstance(a.get(x), (int, float)) for x in ("ltp", "delta")) or not isinstance(b.get("ltp"), (int, float)):
                miss.append(f"could not check: ATM premium ({_fmt(atm)}s {SIDE} not in the chain at {mins[j0]} or {t})")
            else:
                s0 = sa if sa is not None else spot[j0]
                s1 = sb if sb is not None else spot[i]
                x = (b["ltp"] - a["ltp"]) - a["delta"] * (s1 - s0)
                if x > PREM_RS:
                    alive.append({"k": "premium_holding", "text": f"ATM {_fmt(atm)}s {SIDE} bid {_sg(x, 1)} vs delta since {mins[j0]}"})
                elif x < -PREM_RS:
                    risk.append({"k": "premium_bleeding", "text": f"ATM {_fmt(atm)}s {SIDE} bleeding {_sg(x, 1)} vs delta since {mins[j0]}"})
        # pushes
        p10 = [p for p in pushes if m - PUSH_WIN < m2i(p["t"]) <= m and p.get("am") and m2i(p["am"]) <= m]
        if any(p["dir"] == d_ for p in p10):
            alive.append({"k": "push_with", "text": f"push with the leg {[p['t'] for p in p10 if p['dir'] == d_][-1]}"})
        wb = wall_behind_broke(pushes, d_, m)
        if wb:
            risk.append({"k": "wall_behind_broke", "text": f"push against {wb['ans']} the wall behind {wb['t']}"})
        # flow: 3-min delta against, FAST against
        d3 = None if x3 is None else d_ * x3
        if d3 is None:
            miss.append("could not check: 3-min delta (flow missing in the last 3 min)")
        else:
            if d3 <= -D3_AGAINST:
                risk.append({"k": "delta_against", "text": f"3-min delta against {_sg(d3)} lots"})
            if sp_x is not None and sp_x >= FAST and d3 < 0:
                risk.append({"k": "fast_against", "text": f"speed FAST against ×{sp_x:.1f}"})
        fast_against = any(x["k"] == "fast_against" for x in risk)
        # location
        z = d_ * (fut[i] - vw[i]) / sd[i] if sd[i] else None
        if z is not None and abs(z) < Z_INSIDE and zx_max >= TREND_Z and rf >= Z_RETRACE_MIN:
            risk.append({"k": "inside_1sigma", "text": f"back inside 1σ ({z:+.1f}) after a {zx_max:.1f}σ leg, {rf:.2f} of it given back"})
        # her mark against, near the extreme, known by now: a risk item while fresh, a note once old
        if marks is not None:
            near = [x for x in mk if x["known_m"] <= m and M[exti] - MARK_BAR <= x["bar_m"] <= m and isinstance(x["p"], (int, float))
                    and abs(x["p"] - ext) <= MARK_NEAR_U * U and x["winner"] == -d_ and x["kind"] in MARK_AGAINST]
            if near:
                x = near[-1]
                age = m - x["known_m"]
                text = f"her mark {x['name'] or x['kind']} {_fmt(x['p'])} (bar {hm(x['bar_m'])}" + (", appended late" if x["late"] else "") + ")"
                if age <= MARK_FRESH_MIN:
                    risk.append({"k": "mark_against", "text": text})
                else:
                    notes.append({"k": "mark_old", "text": text + f" old, {age} min"})
        # the lagging reads, shown never weighed
        if wf_ce[i] is not None and wf_pe[i] is not None:
            w3 = d_ * (wf_pe[i] - wf_ce[i])
            if abs(w3) >= WF_L:
                notes.append({"k": "writers7", "text": f"writers ±7 {'with' if w3 > 0 else 'against'} {_sg(w3, 0)}L / 3 min (lagging)"})
        sf = _sides_fuel(slot)
        if slot and sf:
            notes.append({"k": "sides", "text": f"Sides {slot['t']} {slot.get('word')} {'with' if sf == d_ else 'against'} (lagging)"})
        notes.append({"k": "retrace", "text": f"retrace {rf:.2f} of the leg · {since} min since {mins[exti]} {_fmt(ext)}f"})

        # ---- the word: HOLD / WATCH / PALAT?, with the confirmation, latch and minimum display -----------------------------
        raw = fast_against or rf >= DEEP or len(risk) >= PALAT_N
        raw_run = raw_run + 1 if raw else 0
        latched = raw and (latched or raw_run >= CONFIRM_MIN or (m - START_M) % 3 == 2)
        if latched and shown_since is None:
            shown_since = m
        if not latched and shown_since is not None and m - shown_since < MIN_SHOW:
            latched = True
        if not latched:
            shown_since = None
        if latched:
            word = "PALAT?"
        elif len(risk) >= WATCH_N:
            word = "WATCH"
        else:
            word = "HOLD"
        if word == "HOLD" and last_word == "WATCH" and m - word_since < HOLD_MIN:
            word = last_word                                  # a relaxation waits one bar; an escalation never does
        if word != last_word:
            last_word, word_since = word, m
        clean = word == "HOLD" and not risk and any(x["k"] == "k1_loading" for x in alive)
        head = {"HOLD": f"PAUSE {arrow} · hold" + (" · clean" if clean else ""), "WATCH": f"PAUSE {arrow} · watch · {len(risk)} risk",
                "PALAT?": f"PALAT? {arrow} leg at risk" + (f" · retrace {rf:.2f} of the leg" if rf >= DEEP else "")}[word]
        row.update(word=word, alive=alive, risk=risk, notes=notes, missing=list(missing_all) + miss,
                   line=" · ".join([head] + [x["text"] for x in risk] + [x["text"] for x in alive]))
        rows.append(row)
        if pause_i == i:
            pauses.append({"t": t, "i": i, "leg": dict(leg), "word": word, "alive": [x["text"] for x in alive],
                           "risk": [x["text"] for x in risk], "missing": list(miss), "at3": None, "after": None})
        for ev in pauses:
            if ev["at3"] is None and m - M[ev["i"]] == 3 and rows[ev["i"]]["lean"] == d_:
                ev["at3"] = {"t": t, "word": word, "alive": [x["text"] for x in alive], "risk": [x["text"] for x in risk]}

    # ---- the outcome of each pause, strictly after the fact (the forward log; never read by a row) -----------------------
    for ev in pauses:
        i0, d0 = ev["i"], ev["leg"]["dir"]
        ext0 = ev["leg"]["extreme"]
        out = {"outcome": None, "t": None, "min": None, "why": "window open: the frame ends before 45 min"}
        hole = None
        for j in range(i0 + 1, N):
            if M[j] - M[j - 1] > 2 and hole is None:
                hole = f"{mins[j - 1]}–{mins[j]}"
            if M[j] - M[i0] > HORIZON:
                out = {"outcome": "UNRESOLVED", "t": mins[j], "min": M[j] - M[i0], "why": "no new extreme and no PALAT in 45 min"
                       + (f" (a hole {hole} inside the window: could not check it whole)" if hole else "")}
                break
            if rows[j]["word"] == "PALAT" and rows[j]["leg"] and rows[j]["leg"]["dir"] == d0:
                out = {"outcome": "REV", "t": mins[j], "min": M[j] - M[i0], "why": "the leg gave back half"}
                break
            if d0 * ((fhi[j] if d0 > 0 else flo[j]) - ext0) >= NEW_U * U_at(j):
                out = {"outcome": "CONT", "t": mins[j], "min": M[j] - M[i0], "why": "a new extreme 0.25U past the pause's"}
                break
        ev["after"] = out
    # the open is not announced (Jarvis v3): before 10:00 a row with a leg reads OPENING, its lean still set. After the
    # outcomes above, which read the state words (a PALAT before 10:00 is still the REV it was)
    for r in rows:
        if r["leg"] and m2i(r["t"]) < OPEN_M and r["word"] != "OPENING":
            r["line"] = f"OPENING {UP if r['lean'] > 0 else DN} · " + r["line"]
            r["word"] = "OPENING"
    return {"rows": rows, "day": {"flips": flips_pm, "fut_oi": fut_oi}, "pauses": pauses, "missing": missing_all, "rev": REV}
