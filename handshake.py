"""handshake.py -- RAFTAAR's HANDSHAKE, Phase 1 (NOTEPAD A132; docs/speed/BUILD-PLAN.md, BUILD-PLAN-FABLE.md §0 / §3):
who PUSHES the future, does the attacked wall ANSWER, who opened the OI behind price, and what the futures leg did.
ONE copy (the §1d lesson): palat.py imports the flow / push / answer / who-opened code back from here.

Fable's validated definitions (docs/speed/handshake/fable/export_v2.py, CRITIQUE.md M1-M7), every threshold [I]:
  flow      the 1-min fut delta in lots: the near-month Dext candles (the contract is the book record's own `ik`; per
            minute the row with the largest total_volume, M1/M2), else the Upstox 1-second book by the quote rule (a trade
            at / above the ask a buy, at / below the bid a sell, else by tick, M5). Each minute carries its source D / B.
  push      a 2-min delta >= 2x the median |2-min delta| of the 30 min before (>= 10 of them) and >= MIN_PUSH lots,
            >= 4 min after the last push its way.
  answer    the attacked strike = the biggest ABSOLUTE OI in the push's band (CE spot-half-step .. +2 steps for a buy,
            PE -2 steps .. +half-step for a sell, M3), its bar max(3L, 4 % of that OI). A129 (her "has to be real time"):
            the ANSWER is the FIRST chain minute within 4 min whose OI change from the push minute crosses the bar --
            TOOT (cut), PHANS (added, price through 0.3 step), TIKI (added, held) -- else NAHI at the 4-min minute.
            G1 (30 Oct): where the strike says nothing, its band (+/- 2 strikes, 2x the bar) may answer, tagged "band".
            palat reads it at the fixed 4-min minute (first=False): its A131 replay, unchanged.
  who       who opened OI added at a strike: the premium move minus delta x the spot move; < -2 ticks WRITERS, > +2
            KHAREEDAR, else "?" (M4). A floor / cap behind price is one only when WRITERS opened it.
  behind    at the answer: the other side's biggest add (>= 3L) within 2 steps behind price since the push, and who.
  fut leg   the futures OI from before the push (end of m-2) to the answer: FRESH (rose >= FUT_LOTS), COVER (fell
            >= FUT_LOTS), FLAT. FRESH = new positions, whichever way the push went (palat's fut check, A129 / A131's words;
            export_v2 multiplied by the push's sign, which reads a sell push's long-unwind as FRESH: not kept).
  effort    effort.py's lots per point over the 5 min to the answer vs the day's median of 5-min blocks (effort.lam_at:
            one definition, Fable's).
SENSEX reads NIFTY's flow and its own chain and futures OI (§1q, sensex_flow.on). OI off the absolute `oi`, never
`oi_chg` (A125). Causal: `read(inp, upto)` uses chain minutes and flow minutes < upto only (a minute m is complete at
m + 1). DISPLAY ONLY: no gate, no order path, no rate. Pure except `load_flow` / `load`.
"""
from __future__ import annotations

import statistics

import effort as _effort

NORM, PUSH_X, ANSWER, QUIET = 30, 2.0, 4, 4                    # export_v2.py
MIN_PUSH = {"NIFTY": 150, "BANKNIFTY": 45}  # BANKNIFTY [I]: 150 x its median 1-min fut volume vs NIFTY's (0.15-0.40, 22/23/26 Oct)
CUT_L, CUT_FRAC, THROUGH = 3.0, 0.04, 0.3
BAND_K, BAND_X = 2, 2.0                     # G1: the answer's band, attacked strike +/- 2 steps, at 2x its bar [I]
TICK = 0.05                                 # WHO OPENED: premium vs delta beyond 2 ticks
BEHIND = 2                                  # steps behind price for the floor / cap
# the fut leg's bar in lots: NIFTY 500 (export_v2); BANKNIFTY / SENSEX [I] scaled to the 5-min |fut OI change| (26 Oct: NIFTY
# median 154 / p90 649, BANKNIFTY 64 / 327, SENSEX 2 / 15 -- SENSEX futures are thin, A25)
FUT_LOTS = {"NIFTY": 500, "BANKNIFTY": 200, "SENSEX": 10}
AFTER = (15, 30)                            # the forward log's points after the push
GAP_S = 60                                  # a book gap longer than this is a hole (28 Oct: the laptop slept 374 s, A142)
FIRST_M, LAST_M = 555, 930                  # the chain grid, 09:15-15:30
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")     # SENSEX: NIFTY's flow, its own OI (§1q)
# The indices whose answers are SAID (the stream, the voice). The bar max(3L, 4 %) is NIFTY's (Fable validated NIFTY only):
# 27 Oct the attacked walls' median OI was NIFTY 250L, BANKNIFTY 22L, SENSEX 6L, the biggest |change| in 4 min 48L / 2.7L /
# 1.2L, so a BANKNIFTY or SENSEX push can never cross 3L and every one would read NAHI ("pullback lagta hai" on every SENSEX
# trade). They are LOGGED (at the close) for the evening review to set their bar; never said until then.
SPEAK = ("NIFTY",)
SAID = ("TOOT", "PHANS", "TIKI")            # the answers that go to the stream; a NAHI never does
WIN = 10                                    # the voice: a push against her in the last 10 min
ARROW = {1: "▲", -1: "▼"}
REV = "handshake-2 (A143)"                  # handshake-2: an answer is stamped only when the next chain minute confirms it


def mod(ms):
    """Epoch ms -> IST minute of the day."""
    return int(ms / 1000 + 19800) % 86400 // 60


def holes(rows):
    """[(t0 ms, t1 ms)]: the 1-second book's gaps longer than GAP_S (a laptop sleep, a feed drop). Measured 21-28 Oct: zero
    to one a day of ~70 s, and 28 Oct's 374 s sleep (A142)."""
    ts = sorted(r["t"] for r in rows or () if isinstance(r, dict) and isinstance(r.get("t"), (int, float)))
    return [(a, b) for a, b in zip(ts, ts[1:]) if b - a > GAP_S * 1000]


def hole_minutes(hs):
    """Every minute a hole touches, both ends included: a minute that lost part of its seconds is not a whole minute."""
    return {m for a, b in hs for m in range(mod(a), mod(b) + 1)}


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def _sg(s):
    """A signed number with the real minus sign (decode._num's), as every chip on the faces."""
    return s.replace("-", "−")


def _l(x):
    return _sg(f"{x:+.1f}L")


# ---- the flow (Fable's export_v2: Dext near month, else the book by the quote rule) ---------------------------------

def dext_flow(rows, lot):
    """{minute: delta lots} from one contract's Dext candles: per minute the row with the largest total_volume (rows are
    re-written as the bar fills, M1); a minute with no volume is absent (27 Oct pm: blank, not quiet)."""
    best = {}
    for r in rows or ():
        try:
            m = int(r["time"][11:13]) * 60 + int(r["time"][14:16])
        except (KeyError, TypeError, ValueError):
            continue
        if m not in best or (r.get("total_volume") or 0) >= (best[m].get("total_volume") or 0):
            best[m] = r
    return {m: round(r["delta"] / lot) for m, r in best.items()
            if r.get("total_volume") and isinstance(r.get("delta"), (int, float))}


def book_flow(rows, lot):
    """({minute: delta lots}, {minute: volume lots}) from the 1-second book: a trade at / above the ask is a buy, at / below
    the bid a sell, else by tick (M5). J1 (A142): a trade across a hole (holes) is not counted and every minute a hole
    touches is dropped -- the laptop's 6-minute sleep on 28 Oct came back as one +3,534-lot 'push' at 13:01 -- so no push
    is born in a minute the book could not see."""
    rows = sorted((r for r in rows or () if isinstance(r, dict) and isinstance(r.get("t"), (int, float))
                   and r.get("ltp") is not None and r.get("b") and r.get("a")), key=lambda r: r["t"])
    d, v, prev = {}, {}, None
    for r in rows:
        m = mod(r["t"])
        d.setdefault(m, 0.0)
        v.setdefault(m, 0.0)
        if prev is not None and r["t"] - prev["t"] <= GAP_S * 1000:
            q = (r.get("vtt") or 0) - (prev.get("vtt") or 0)
            if q > 0:
                bid, ask, p = prev["b"][0][0], prev["a"][0][0], r["ltp"]
                s = 1 if p >= ask else -1 if p <= bid else (p > prev["ltp"]) - (p < prev["ltp"])
                d[m] += s * q / lot
                v[m] += q / lot
        prev = r
    blind = hole_minutes(holes(rows))
    return {m: round(x) for m, x in d.items() if m not in blind}, {m: x for m, x in v.items() if m not in blind}


def flow(dx, bd, bv):
    """({minute: lots}, {minute: "D" | "B"}): Dext where it has the minute, else the book where it traded."""
    F = dict(dx)
    src = {m: "D" for m in dx}
    for m, x in bd.items():
        if m not in F and bv.get(m, 0) > 0:
            F[m], src[m] = x, "B"
    return F, src


def pushes(F, ms, min_push):
    """Every PUSH over the chain minutes `ms` (export_v2.py): causal, each needs only the flow up to its minute."""
    def d2(m):
        a, b = F.get(m - 1), F.get(m)
        return None if a is None or b is None else a + b
    out, last = [], {1: -99, -1: -99}
    for m in ms:
        x = d2(m)
        hist = [abs(y) for y in (d2(j) for j in range(m - NORM, m)) if y is not None]
        if x is None or len(hist) < 10:
            continue
        norm, s = statistics.median(hist), 1 if x > 0 else -1
        if abs(x) < max(min_push, PUSH_X * norm) or m - last[s] < QUIET:
            continue
        last[s] = m
        out.append({"m": m, "dir": s, "lots": x, "norm": round(norm)})
    return out


# ---- the chain grid -----------------------------------------------------------------------------------------------

def chain_minutes(rows):
    """{minute: the LAST chain snapshot of that minute} (coil_scan.minutes), 09:15-15:30, with a spot."""
    out = {}
    for r in rows or ():
        ts = r.get("ts") if isinstance(r, dict) else None
        if isinstance(ts, str) and r.get("spot") and "09:15" <= ts[:5] <= "15:30":
            out[int(ts[:2]) * 60 + int(ts[3:5])] = r
    return out


def with_backfill(R, grid):
    """J1b: the chain minutes `R` plus the REST backfill's (chain_backfill.read_grid: {"HH:MM": {spot, k: {strike: (ce_chg,
    pe_chg)}, px: {strike: (ce_ltp, pe_ltp)}}}) for the minutes the recorder never saw -- a late start's morning, a laptop
    sleep's hole -- as if it had been there. Absolute OI = the day's base seen live (oi - oi_chg, one per strike and side)
    + the change; a strike never seen live has no base, so no OI (could not check, never a zero). No delta, so WHO OPENED
    stays "?". An observed minute is never touched. Tagged src "backfill"."""
    base = {}
    for r in R.values():
        for s in (r or {}).get("strikes") or ():
            for side in ("ce", "pe"):
                leg = s.get(side) or {}
                if isinstance(leg.get("oi"), (int, float)) and isinstance(leg.get("oi_chg"), (int, float)):
                    base.setdefault((s.get("k"), side), leg["oi"] - leg["oi_chg"])
    out = dict(R)
    for t, rec in (grid or {}).items():
        m = int(t[:2]) * 60 + int(t[3:5])
        if m in out or not FIRST_M <= m <= LAST_M or not rec.get("spot"):
            continue
        strikes = []
        for k, chg in (rec.get("k") or {}).items():
            px = (rec.get("px") or {}).get(k) or (None, None)
            legs = {}
            for i, side in enumerate(("ce", "pe")):
                b = base.get((k, side))
                legs[side] = {"oi": None if b is None or chg[i] is None else b + chg[i], "ltp": px[i]}
            strikes.append({"k": k, **legs})
        out[m] = {"ts": t + ":00", "spot": rec["spot"], "strikes": strikes, "src": "backfill"}
    return out


def _leg(r, k, side):
    for s in (r or {}).get("strikes") or ():
        if s.get("k") == k:
            return s.get(side) or {}
    return {}


def _ks(r):
    return sorted(s["k"] for s in (r or {}).get("strikes") or () if isinstance(s.get("k"), (int, float)))


def _step(ks):
    return min((b - a for a, b in zip(ks, ks[1:]) if b > a), default=None)


def _last(ms, upto):
    """The last chain minute <= upto, or None."""
    return next((m for m in reversed(ms) if m <= upto), None)


def answer(R, ms, p, upto, first=True, k=None):
    """The answer to push p at the attacked strike (or at `k`: her defending wall, the voice), known by `upto` (a chain
    minute j is known when j <= upto - 1), else None (pending).
    first=True (A129): the FIRST chain minute j in (m, m4] whose OI change from m crosses the bar; NAHI at m4.
    first=False (palat, A131): read at m4 only.
    -> {"ans": TOOT | PHANS | TIKI | NAHI | None (could not check), "k", "chg" (L), "bar" (L), "am" (the minute read)}
    plus "held" (the confirming minute) and, for a band answer (G1), "via": "band", "band" (its strikes), "wk" (the
    band's strike that moved most: who opened it is read there); "chg" and "bar" are then the band's."""
    m, d = p["m"], p["dir"]
    m4 = next((j for j in ms if j >= m + ANSWER), None)
    r0 = R.get(m)
    ks = _ks(r0)
    step = _step(ks)
    if r0 is None or step is None:
        return None if m4 is None or m4 > upto - 1 else {"ans": None, "k": None, "chg": None, "bar": None, "am": m4}
    s0, side = r0["spot"], "ce" if d > 0 else "pe"
    att = k
    if att is None:
        band = [x for x in ks if (s0 - step / 2 <= x <= s0 + 2 * step if d > 0 else s0 - 2 * step <= x <= s0 + step / 2)]
        att = max(band, key=lambda x: _leg(r0, x, side).get("oi") or 0) if band else None
    o0 = _leg(r0, att, side).get("oi")
    if att is None or o0 is None:
        return None if m4 is None or m4 > upto - 1 else {"ans": None, "k": att, "chg": None, "bar": None, "am": m4}
    bar = max(CUT_L, CUT_FRAC * o0 / 1e5)
    look = [j for j in ms if m < j <= (m4 if m4 is not None else m + ANSWER) and j <= upto - 1] if first else []
    # THE BAND (G1, 30 Oct, docs/kahani/review/DECODE-GAPS-2026-10-30.md): the push's own answer, read at the attacked
    # strike AND its BAND_K strikes either side. 29 Oct: of 24 pushes the strike called NAHI, the band crossed the bar in
    # the same 4 min in 14 and twice it in 8 (13:53: the strike -1.3L, the band -14.2L). The strike is read first every
    # minute; the band speaks only where the strike says nothing, at BAND_X x the strike's bar, with the same hold. Only
    # the push's own answer (first=True, no `k`): palat's fixed 4-min read and the voice's wall read keep the one strike.
    band_ks = [x for x in ks if abs(x - att) <= BAND_K * step + 1e-9] if first and k is None else []
    bbar = BAND_X * bar

    def chg_at(j):
        o = _leg(R[j], att, side).get("oi")
        return None if o is None else (o - o0) / 1e5

    def band_at(j):
        """(the band's OI change from m in L, its strike that moved most), or None when any of its legs is unread."""
        tot, big = 0.0, (0.0, att)
        for x in band_ks:
            a, b = _leg(r0, x, side).get("oi"), _leg(R[j], x, side).get("oi")
            if a is None or b is None:
                return None
            tot += (b - a) / 1e5
            big = max(big, ((b - a) / 1e5, x), key=lambda c: abs(c[0]))
        return tot, big[1]

    def word(j, chg, bar=bar):
        through = d * (R[j]["spot"] - s0) >= THROUGH * step
        return "TOOT" if chg <= -bar else "PHANS" if chg >= bar and through else "TIKI" if chg >= bar else "NAHI"

    def by_band(j, b, held=None):
        out = {"ans": word(j, b[0], bbar), "k": att, "chg": round(b[0], 1), "bar": round(bbar, 1), "am": j,
               "via": "band", "band": band_ks, "wk": b[1]}
        return out if held is None else dict(out, held=held)

    wapas = False
    for j in look + ([] if m4 is None or m4 > upto - 1 or (look and look[-1] == m4) else [m4]):
        chg = chg_at(j)
        if chg is None:
            continue
        b = band_at(j) if band_ks else None
        if j == m4:                                          # the 4-min minute is final: no confirmation needed
            out = {"ans": word(j, chg), "k": att, "chg": round(chg, 1), "bar": round(bar, 1), "am": j}
            if out["ans"] == "NAHI" and b is not None and abs(b[0]) >= bbar:
                return by_band(j, b)
            if wapas and out["ans"] == "NAHI":
                out["wapas"] = True
            return out
        if abs(chg) >= bar:                                  # handshake-2 (A143): the next chain minute must confirm it
            j2 = next((x for x in ms if x > j), None)        # (j < m4, so j2 <= m4)
            if j2 is None or j2 > upto - 1:
                return None                                  # crossed, not yet confirmable: pending
            c2 = chg_at(j2)
            if c2 is not None and abs(c2) >= bar and (c2 > 0) == (chg > 0):
                return {"ans": word(j, chg), "k": att, "chg": round(chg, 1), "bar": round(bar, 1), "am": j, "held": j2}
            wapas = True                                     # it came back: read on to m4
        elif b is not None and abs(b[0]) >= bbar:            # the band, with the same hold
            j2 = next((x for x in ms if x > j), None)
            if j2 is None or j2 > upto - 1:
                return None
            b2 = band_at(j2)
            if b2 is not None and abs(b2[0]) >= bbar and (b2[0] > 0) == (b[0] > 0):
                return by_band(j, b, held=j2)
            wapas = True
    if m4 is not None and m4 <= upto - 1:                       # the strike had no OI at m4: could not check (M7)
        return {"ans": None, "k": att, "chg": None, "bar": None, "am": m4}
    return None


def who_opened(r0, r1, k, side):
    """Who opened the OI added at k between chain rows r0 and r1 (export_v2.who, Fable CRITIQUE M4): the premium move
    minus what delta explains; < -2 ticks WRITERS (selling into it), > +2 ticks KHAREEDAR (buyers paying up), else "?".
    None when a premium or the delta is missing."""
    a, b = _leg(r0, k, side), _leg(r1, k, side)
    if not all(isinstance(x, (int, float)) for x in (a.get("ltp"), b.get("ltp"), a.get("delta"))):
        return None
    x = (b["ltp"] - a["ltp"]) - a["delta"] * (r1["spot"] - r0["spot"])
    return "WRITERS" if x < -2 * TICK else "KHAREEDAR" if x > 2 * TICK else "?"


def behind(R, m, am, d):
    """The other side's biggest add (>= CUT_L) within BEHIND steps behind price at the answer minute am, since the push
    minute m, and who opened it -> {"k", "side", "add" (L), "who"} or None (checked: nothing that size)."""
    r0, r1 = R.get(m), R.get(am)
    ks = _ks(r1)
    step = _step(ks)
    if r0 is None or r1 is None or step is None:
        return None
    s1, other = r1["spot"], "pe" if d > 0 else "ce"
    adds = []
    for k in ks:
        if (s1 - BEHIND * step <= k <= s1) if d > 0 else (s1 <= k <= s1 + BEHIND * step):
            o0, o1 = _leg(r0, k, other).get("oi"), _leg(r1, k, other).get("oi")
            if o0 is not None and o1 is not None:
                adds.append((k, (o1 - o0) / 1e5))
    if not adds:
        return None
    k, add = max(adds, key=lambda a: a[1])
    if add < CUT_L:
        return None
    return {"k": k, "side": other.upper(), "add": round(add, 1), "who": who_opened(r0, r1, k, other)}


def fut_minutes(oi):
    """{minute: the last futures OI of that minute} from [(t ms, oi)] in time order."""
    return {mod(t): v for t, v in oi or () if v}


def fut_leg(oim, m0, m1, lot, bar):
    """The futures OI from the end of minute m0 to the end of m1 (oim = fut_minutes) -> {"lots", "leg": FRESH | COVER |
    FLAT} or None (no reading within 3 min of either end)."""
    ms = sorted(oim)
    a, b = _last(ms, m0), _last(ms, m1)
    if a is None or b is None or a < m0 - 3 or b < m1 - 3:
        return None
    o0, o1 = oim[a], oim[b]
    lots = round((o1 - o0) / lot)
    return {"lots": lots, "leg": "FRESH" if lots >= bar else "COVER" if lots <= -bar else "FLAT"}


def effort(fm, m):
    """effort.py's lots per point over m-4..m and its ratio to the day's median of 5-min blocks -> {"lam", "x"} or None
    (no range; x None before 6 blocks)."""
    lam, med, _ = _effort.lam_at(fm or {}, m)
    if lam is None:
        return None
    return {"lam": round(lam), "x": None if not med else round(lam / med, 1)}


# ---- one push, read to `upto` -----------------------------------------------------------------------------------------

def _spot_at_or_after(R, ms, m, upto):
    j = next((j for j in ms if j >= m), None)
    return None if j is None or j > upto - 1 else R[j]["spot"]


def read(inp, upto):
    """Every push of the day before minute `upto`, each with what is known by then -> rows (the forward log's shape).
    `final`: its +30 is known, or the chain has stopped (upto > 15:30 + 1)."""
    R, idx = inp["R"], inp["idx"]
    ms = [m for m in inp["ms"] if m < upto]
    F = {m: x for m, x in inp["F"].items() if m < upto}
    P = pushes(F, ms, inp["min_push"])
    inp["pushes"] = P
    out = []
    for p in P:
        m, d = p["m"], p["dir"]
        a = answer(R, ms, p, upto)
        r0 = R.get(m) or {}
        row = {"t": hm(m), "idx": idx, "dir": d, "lots": p["lots"], "norm": p["norm"],
               "src": "".join(sorted({inp["src"].get(j) or "?" for j in (m - 1, m)})), "flow_of": inp["flow_of"],
               "k": None, "side": "CE" if d > 0 else "PE", "oi_L": None, "ans": "?" if a is None else a["ans"],
               "am": None, "held": None, "wapas": False, "after": None, "chg": None, "bar": None, "who": None, "behind": None, "floor_cap": None,
               "fut": None, "effort": None, "via": None}
        if a is not None:
            row.update(k=a["k"], chg=a["chg"], bar=a["bar"], am=hm(a["am"]), after=a["am"] - m,
                       held=hm(a["held"]) if a.get("held") is not None else None, wapas=bool(a.get("wapas")), via=a.get("via"))
            o0 = _leg(r0, a["k"], "ce" if d > 0 else "pe").get("oi")
            row["oi_L"] = None if o0 is None else round(o0 / 1e5, 1)
            if a["ans"] in ("PHANS", "TIKI"):                  # a band answer: who opened it, at its strike that moved most
                row["who"] = who_opened(r0, R.get(a["am"]), a.get("wk", a["k"]), "ce" if d > 0 else "pe")
            if a["ans"] is not None:
                row["behind"] = behind(R, m, a["am"], d)
                if (row["behind"] or {}).get("who") == "WRITERS":
                    row["floor_cap"] = row["behind"]["k"]           # writers only: a buyer-opened add is protection
                row["fut"] = fut_leg(inp["oim"], m - 2, a["am"], inp["lot"], FUT_LOTS.get(idx, FUT_LOTS["NIFTY"]))
                row["effort"] = effort(inp.get("fm"), a["am"])
        s0 = (R.get(m) or {}).get("spot")
        for w in AFTER:
            s1 = _spot_at_or_after(R, inp["ms"], m + w, upto)
            row[f"p{w}"] = None if s0 is None or s1 is None else round(d * (s1 - s0))
        row["final"] = a is not None and (row["p30"] is not None or upto > LAST_M + 1)
        if a is None and upto > LAST_M + 1:                        # the chain stopped before its 4 min: could not check
            row.update(ans=None, final=True, why="could not check — the chain stopped before its 4 min")
        row["key"] = f"{idx}|FLOW|{row['t']}|{ARROW[d]}"
        out.append(row)
    return out


def said(ans, who):
    """The answer in her words. G4 (30 Oct): OI ADDED at the wall is a defence only when WRITERS opened it. Opened by
    buyers (premium up more than delta explains) it is buyers betting the wall breaks: fuel FOR the push, the opposite
    word. 27-29 Oct: 5 of 11 TIKIs were buyers'. "?" says it could not tell."""
    if ans == "TIKI":
        return {"WRITERS": "deewar tiki", "KHAREEDAR": "kharidar ghuse (deewar nahi)"}.get(who or "", "deewar tiki? (kaun ?)")
    return {"TOOT": "deewar toot rahi", "PHANS": "writers phanse"}.get(ans, ans or "?")


def message(row):
    """The stream line for an ANSWERED push (TOOT / PHANS / TIKI), else None. Kind FLOW: telegram_out.wants never sends
    it (screen only), and `quiet` says so twice. Spot strikes say s; no %.
    "◆ PUSH ▲ 09:52 +458 lots · CE 22,500s deewar toot rahi −31.0L (2 min) · floor 22,550s writers +15.2L · fut cover −763 lots" """
    import messages
    if row.get("ans") not in SAID or row.get("idx") not in SPEAK:
        return None
    d, of = row["dir"], ("NIFTY " if row.get("flow_of") not in (None, row["idx"]) else "")
    lots = _sg(f"{row['lots']:+,}")
    word = f"◆ {of}PUSH {ARROW[d]} {row['t']} {lots} lots"
    k = f"{row['side']} {row['k']:,.0f}s" + (" ±2" if row.get("via") == "band" else "")    # G1: the band answered
    ans = f"{k} {said(row['ans'], row.get('who'))} {_l(row['chg'])}" + (", price paar" if row["ans"] == "PHANS" else "")
    who = "" if row["ans"] == "TIKI" else \
        {"WRITERS": " · writers ne likha", "KHAREEDAR": " · kharidar ne liya"}.get(row.get("who") or "", "")
    ans += f" ({row['after']} min{who})"                           # who opened the add (PHANS; TIKI's word says it)
    fc, b = "floor" if d > 0 else "cap", row.get("behind")
    if b is None:
        back = f"{fc} nahi"
    elif b["who"] == "WRITERS":
        back = f"{fc} {b['k']:,.0f}s writers {_l(b['add'])}"
    else:                                                       # a buyer-opened add is protection, not a floor (M4)
        back = f"peeche {b['side']} {b['k']:,.0f}s {_l(b['add'])} " + (f"kharidar · {fc} nahi" if b["who"] == "KHAREEDAR"
                                                                         else "kaun ?")
    f = row.get("fut")
    fut = "fut ?" if f is None else f"fut {f['leg'].lower()} " + _sg(f"{f['lots']:+,}") + " lots"
    e = row.get("effort") or {}
    parts = [ans, back, fut] + ([f"effort {e['x']:g}×"] if (e.get("x") or 0) >= _effort.HI else [])
    m = messages._msg(row["am"], row["idx"], "FLOW", d, word, None, " · ".join(parts),
                      f"handshake: push {row['t']} ({row['src']}) · answer read {row['am']}", quiet=True)
    m["key"] = row["key"]
    return m


# ---- the voice: her defending wall (the fold engine's W) against the latest push at her ------------------------------

def defend(inp, d, k, now_m):
    """The latest push AGAINST her trade (direction -d) in the WIN min to now_m whose answer AT her defending wall k is
    known, with the futures leg -> {"p", "a", "fut", "of"} or None. `inp` must have been `read` (its pushes)."""
    if not inp or k is None or d not in (1, -1) or inp.get("idx") not in SPEAK:
        return None
    for p in reversed(inp.get("pushes") or ()):
        if p["dir"] != -d or p["m"] < now_m - WIN:
            continue
        a = answer(inp["R"], [m for m in inp["ms"] if m < now_m], p, now_m, k=k)
        if a is None:
            continue
        if a["ans"] in ("PHANS", "TIKI"):                  # G4: an add at her wall is protection only if writers opened it
            a = dict(a, who=who_opened(inp["R"].get(p["m"]), inp["R"].get(a["am"]), k, "ce" if p["dir"] > 0 else "pe"))
        fut = None if a["ans"] is None else fut_leg(inp["oim"], p["m"] - 2, a["am"], inp["lot"],
                                                    FUT_LOTS.get(inp["idx"], FUT_LOTS["NIFTY"]))
        return {"p": p, "a": a, "fut": fut, "of": "NIFTY " if inp.get("flow_of") not in (None, inp["idx"]) else ""}
    return None


# ---- I/O: the record files, the same live and in a replay (anytime-start) -------------------------------------------

def book_rows(day, idx):
    """The day's 1-second book rows (book_log.read_rows' rows), followed incrementally by tailread (A175: a full re-read
    every pass cost 10-40 s by the afternoon)."""
    import book_log
    import tailread
    return [r for r in tailread.rows(book_log.day_path(day, idx)) if isinstance(r.get("t"), (int, float))]


def load_flow(day, idx):
    """(flow index, its lot, its book rows, F, src): Dext of the book's own contract, else the book (SENSEX: NIFTY's, §1q)."""
    import dext_log
    import sensex_flow
    import tape_log
    import v2feed
    fi = "NIFTY" if sensex_flow.on(idx) else idx
    flot = v2feed.LOTS.get(fi) or 1
    brows = book_rows(day, fi)
    ik = next((r.get("ik") for r in brows if r.get("ik")), None)
    dx = {}
    if isinstance(ik, str) and ik.startswith("NSE_FO|"):                  # dext_parity's rule: the book's own contract
        dx = dext_flow(tape_log._read(dext_log.candles_path(f"NSE-{ik.split('|')[1]}", day)), flot)
    F, src = flow(dx, *book_flow(brows, flot))
    return fi, flot, brows, F, src


def load(day, idx):
    """Everything `read` needs for (day, idx) from the record: the chain grid, the flow, the futures OI (the index's own
    book), the effort minutes (the flow index's book)."""
    import confluence_log
    import tailread
    import v2feed
    fi, flot, brows, F, src = load_flow(day, idx)
    import chain_backfill
    R = with_backfill(chain_minutes(tailread.rows(confluence_log._chain_path(idx, day))),
                      chain_backfill.read_grid(day, idx))         # J1b: a hole's minutes from REST, as if we had been there
    own = brows if fi == idx else book_rows(day, idx)
    hs = holes(own)
    blind = hole_minutes(hs)                              # J1: the futures OI drops the minutes its book could not see
    oim = {m: x for m, x in fut_minutes(sorted((r["t"], r["oi"]) for r in own if isinstance(r.get("t"), (int, float))
                                               and isinstance(r.get("oi"), (int, float)) and r["oi"] > 0)).items()
           if m not in blind}
    return {"idx": idx, "R": R, "ms": sorted(m for m in R if FIRST_M <= m <= LAST_M), "F": F, "src": src,
            "oim": oim, "holes": hs,
            "lot": v2feed.LOTS.get(idx) or 1, "fm": _effort.minutes(brows, flot), "flow_of": fi,
            "min_push": MIN_PUSH.get(fi, MIN_PUSH["NIFTY"]), "pushes": []}
