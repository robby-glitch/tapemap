"""raftaar.py -- RAFTAAR round-1 design (OPUS): the OI-speed READ, replayed causally over recorded days.

DESIGN ONLY. Reads tapemap/data/chain (and data/book for the optional futures leg, data/read for THE READ's word) and
writes nothing outside this folder. Stdlib only. Every threshold here is [I], fixed in DESIGN.md before the replay rows
were read; nothing is tuned to what price did afterwards. Rows, never rates.

    python -X utf8 raftaar.py 2026-10-08 2026-10-22 ...        -> replay/<day>.txt  (all three indices)
    python -X utf8 raftaar.py --check                          -> the self-check

The rule, in one breath (DESIGN.md §2-§3 has the table):
  window   read.writers' nine: ATM +/- m strikes (m <= 4, symmetric, both OIs present)
  zones    CE: ANDAR = strikes <= ATM, BAHAR = strikes > ATM (the cap) | PE: ANDAR >= ATM, BAHAR < ATM (the floor)
  flows    each zone's OI change over S (15 min; SENSEX 16) and each side's over F (5 min; SENSEX 8), % of the window OI
  size     every flow ranked against the same index, same day kind (NORMAL / EXPIRY), same day-part on the prior
           sessions (rank.py's PARTS and cut-offs: < p70 noise, p70 notable, p90 BADA); fewer than 5 such sessions ->
           today's own minutes so far; neither -> "?"
  side     9 structures from the two zones' signs (likh / roll up / roll down / bhaag / deewar ...)
  story    price over S x net pressure over S x the two structures -> one named story (DESIGN §2 table)
  picture  regime CHAL RAHA ^/v | ATKA ^/v | CHOP | PIN | KHAMOSH, a move's phase SHURU / TEZ / JAARI / THAK,
           held 3 min (SENSEX 6) before it changes; grade = an agreement COUNT n/N, never a %
"""
from __future__ import annotations

import bisect
import datetime
import gzip
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TAPEMAP = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(TAPEMAP, "data")
CACHE = os.path.join(HERE, "cache")          # pickled minute grids (derived, git-ignorable); never under tapemap/data
OUT = os.path.join(HERE, "replay")

IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
F_MIN = {"NIFTY": 5, "BANKNIFTY": 5, "SENSEX": 8}      # fast window: ~5 OI updates (SENSEX OI steps every ~2.7 min)
S_MIN = {"NIFTY": 15, "BANKNIFTY": 15, "SENSEX": 16}   # slow window: the story's window
HOLD = {"NIFTY": 3, "BANKNIFTY": 3, "SENSEX": 6}       # minutes a new picture must hold before it is stamped
NEAR = 4                                               # ATM +/- 4 (read.writers)
ROLE = 0.25                                            # a zone counts when it carries >= 25% of its side's gross flow
P_NOTE, P_BADA = 70, 90                                # rank.py's cut-offs
MIN_DAYS = 5                                           # rank.MIN_DAYS
REF_DAYS = 20                                          # the most recent prior sessions of the same kind
OWN_MIN = 30                                           # today's own minutes needed for the fallback reference
PARTS = ((555, 600), (600, 720), (720, 810), (810, 931))   # 09:15-10:00, 10:00-12:00, 12:00-13:30, 13:30-15:30
CHOP_TURNS, CHOP_RANGE, PIN_RANGE, LOOK = 2, 1.0, 1.0, 30   # chop: 2 turns of notable fast pressure in 30 min, range >= 1 step
PIN_TIGHT = 0.6                                        # PIN TIKA: 30-min range <= 0.6 step, spot within 0.5 step of the strike
RETRACE, ENDS_AFTER, STALE = 0.5, 10, 30               # a leg ends: half of it given back | 10 min of chop/pin | 30 min no new extreme
CHOP_WIN = 60                                          # chop is read over the last 60 min of swings
TWO_WAY = 120                                          # the last two legs, both given back, alternating, within 120 min
QUIET_MIN = 5                                          # "kuch khaas nahi" is stamped only when it lasts 5 min
EV_GAP, RESTART = 30, 20                              # a side event: at most once per side per 30 min; "phir likhne lage" after >= 20 min ruke
SHORT = {"NIFTY": "NIFTY", "BANKNIFTY": "BNF", "SENSEX": "SNX"}
FUT_OI_PCT = 0.10                                      # §1o's fut_oi vote: |fut OI change over 15 min| >= 0.10 %
EXPIRY_WD = {"NIFTY": 1, "SENSEX": 3}                  # weekly expiry weekday when the record has no expiry field
UP, DN = "▲", "▼"


# ---- data ---------------------------------------------------------------------------------------------------------

def mm(t):
    return int(t[:2]) * 60 + int(t[3:5])


def hm(m):
    return "%02d:%02d" % divmod(m, 60)


def days(idx):
    return sorted(f[len(f"chain_{idx}_"):].split(".")[0] for f in os.listdir(os.path.join(DATA, "chain"))
                  if f.startswith(f"chain_{idx}_"))


def _open(path):
    if os.path.exists(path):
        return open(path, encoding="utf-8")
    if os.path.exists(path + ".gz"):
        return gzip.open(path + ".gz", "rt", encoding="utf-8")
    return None


def grid(idx, day):
    """The minute grid with ABSOLUTE OI (the last chain row of each minute) -- /api/oihist's minutes + its `open`."""
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, f"{idx}_{day}.pkl")
    live = day == datetime.date.today().isoformat()
    if os.path.exists(cp) and not live:
        with open(cp, "rb") as f:
            return pickle.load(f)
    last, exp = {}, None
    with _open(os.path.join(DATA, "chain", f"chain_{idx}_{day}.jsonl")) as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("ts") and r.get("spot") is not None:
                last[r["ts"][:5]] = r
                exp = r.get("expiry") or exp
    ts = sorted(last)
    ks = sorted({s["k"] for t in ts for s in last[t]["strikes"]})
    G = {"t": [mm(t) for t in ts], "spot": [last[t]["spot"] for t in ts], "expiry": exp, "ks": ks,
         "step": min(b - a for a, b in zip(ks, ks[1:])),
         "ce": {k: [None] * len(ts) for k in ks}, "pe": {k: [None] * len(ts) for k in ks},
         "cchg": {k: [None] * len(ts) for k in ks}, "pchg": {k: [None] * len(ts) for k in ks}}
    for i, t in enumerate(ts):
        for s in last[t]["strikes"]:
            for side, chg in (("ce", "cchg"), ("pe", "pchg")):
                leg = s.get(side) or {}
                if isinstance(leg.get("oi"), (int, float)):
                    G[side][s["k"]][i] = leg["oi"]
                    G[chg][s["k"]][i] = leg.get("oi_chg") or 0
    if not live:
        with open(cp, "wb") as f:
            pickle.dump(G, f)
    return G


def fut(idx, day):
    """{minute: (ltp, oi)} from the futures book record, or None. SENSEX reads NIFTY's (§1q, its own is too thin)."""
    src = "NIFTY" if idx == "SENSEX" else idx
    cp = os.path.join(CACHE, f"fut_{src}_{day}.pkl")
    if os.path.exists(cp) and day != datetime.date.today().isoformat():
        with open(cp, "rb") as f:
            return pickle.load(f)
    f = _open(os.path.join(DATA, "book", f"book_{src}_{day}.jsonl"))
    if f is None:
        return None
    out = {}
    with f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("ltp") and r.get("oi") and r.get("t"):
                m = int((r["t"] / 1000 + 19800) % 86400 // 60)
                if 555 <= m <= 930:
                    out[m] = (r["ltp"], r["oi"])
    with open(cp, "wb") as fh:
        pickle.dump(out, fh)
    return out


def kind(idx, day, expiry):
    """rank.day_kind's NORMAL / EXPIRY (ROLL folded into EXPIRY: the monthly is both for BANKNIFTY)."""
    if expiry:
        return "EXPIRY" if str(expiry)[:10] == day else "NORMAL"
    d = datetime.date.fromisoformat(day)
    if idx == "BANKNIFTY":       # monthly: the last Tuesday
        return "EXPIRY" if d.weekday() == 1 and (d + datetime.timedelta(days=7)).month != d.month else "NORMAL"
    return "EXPIRY" if d.weekday() == EXPIRY_WD[idx] else "NORMAL"


def part(m):
    for n, (a, b) in enumerate(PARTS):
        if a <= m < b:
            return n
    return None


# ---- features (causal: minute i reads rows <= i) ------------------------------------------------------------------

def _back(G, pos, i, W):
    """Row index at minute t_i - W (an exact minute, else the nearest earlier one within 2 min), or None."""
    for b in range(3):
        j = pos.get(G["t"][i] - W - b)
        if j is not None:
            return j
    return None


def features(idx, day):
    G = grid(idx, day)
    t, sp, step = G["t"], G["spot"], G["step"]
    pos = {m: i for i, m in enumerate(t)}
    F, S = F_MIN[idx], S_MIN[idx]
    rows = []
    for i in range(len(t)):
        atm = round(sp[i] / step) * step
        m = NEAR
        while m >= 2:
            K = [atm + d * step for d in range(-m, m + 1)]
            if all(k in G["ce"] and G["ce"][k][i] is not None and G["pe"][k][i] is not None for k in K):
                break
            m -= 1
        r = {"t": t[i], "spot": sp[i], "atm": atm, "m": m, "step": step}
        if m < 2:
            r["blind"] = f"spot {sp[i]:.0f} at the chain window's edge (ATM ±{max(m, 0)})"
            rows.append(r)
            continue
        oi = sum(G["ce"][k][i] + G["pe"][k][i] for k in K)
        r.update(K=K, oi=oi)
        js, jf, jp = _back(G, pos, i, S), _back(G, pos, i, F), _back(G, pos, i, 2 * F)

        def d(side, k, j):
            a, b = G[side][k][i], (G[side][k][j] if j is not None else None)
            return None if a is None or b is None else a - b
        if js is not None:
            per = {(s, k): d(s, k, js) for s in ("ce", "pe") for k in K}
            per = {sk: v for sk, v in per.items() if v is not None}      # a strike without both ends drops out
            if all(sum(1 for (s_, _k) in per if s_ == s) >= 5 for s in ("ce", "pe")):
                zin = lambda s: [k for k in K if (k <= atm if s == "ce" else k >= atm)]      # noqa: E731
                zout = lambda s: [k for k in K if (k > atm if s == "ce" else k < atm)]       # noqa: E731
                for s in ("ce", "pe"):
                    r[s + "_in"] = 100 * sum(per[(s, k)] for k in zin(s) if (s, k) in per) / oi
                    r[s + "_out"] = 100 * sum(per[(s, k)] for k in zout(s) if (s, k) in per) / oi
                    r[s + "_k"] = {k: per[(s, k)] for k in K if (s, k) in per}   # raw OI change per strike, for the line
                r["z_s"] = (r["pe_in"] + r["pe_out"]) - (r["ce_in"] + r["ce_out"])
                r["d_s"] = (sp[i] - sp[js]) / step
        if jf is not None:
            fc = [d("ce", k, jf) for k in K]
            fp = [d("pe", k, jf) for k in K]
            if None not in fc + fp:
                r["ce_f"], r["pe_f"] = 100 * sum(fc) / oi, 100 * sum(fp) / oi
                r["z_f"] = r["pe_f"] - r["ce_f"]
                r["d_f"] = (sp[i] - sp[jf]) / step
                if jp is not None:
                    pc = [None if G["ce"][k][jf] is None or G["ce"][k][jp] is None else G["ce"][k][jf] - G["ce"][k][jp] for k in K]
                    pp = [None if G["pe"][k][jf] is None or G["pe"][k][jp] is None else G["pe"][k][jf] - G["pe"][k][jp] for k in K]
                    if None not in pc + pp:
                        r["ce_fp"], r["pe_fp"] = 100 * sum(pc) / oi, 100 * sum(pp) / oi
                        r["z_fp"] = r["pe_fp"] - r["ce_fp"]
        lo = [sp[j] for j in range(i + 1) if t[i] - t[j] <= LOOK]
        r["rng30"] = (max(lo) - min(lo)) / step
        r["d30"] = (sp[i] - lo[0]) / step
        # the most two-sided strike near spot (the pin candidate): max of min(CE OI, PE OI) within 1 step
        cands = [k for k in K if abs(k - sp[i]) <= step]
        pk = max(cands, key=lambda k: min(G["ce"][k][i], G["pe"][k][i])) if cands else None
        if pk is not None:
            c, p = G["ce"][pk][i], G["pe"][pk][i]
            r["pin"] = {"k": pk, "ce": c, "pe": p, "bal": min(c, p) / max(c, p) if max(c, p) else 0,
                        "top": min(c, p) >= max(min(G["ce"][k][i], G["pe"][k][i]) for k in K)}
        rows.append(r)
    return {"idx": idx, "day": day, "step": step, "rows": rows, "kind": kind(idx, day, G["expiry"]), "G": G}


METRICS = {   # name -> the magnitude a row contributes to its reference pool
    "side": lambda r: [abs(r["ce_in"]) + abs(r["ce_out"]), abs(r["pe_in"]) + abs(r["pe_out"])] if "z_s" in r else [],
    "z_s": lambda r: [abs(r["z_s"])] if "z_s" in r else [],
    "z_f": lambda r: [abs(r["z_f"])] if "z_f" in r else [],
    "side_f": lambda r: [abs(r["ce_f"]), abs(r["pe_f"])] if "z_f" in r else [],
    "d_s": lambda r: [abs(r["d_s"])] if "d_s" in r else [],
    "d_f": lambda r: [abs(r["d_f"])] if "d_f" in r else [],
    "gross": lambda r: [sum(abs(r[k]) for k in ("ce_in", "ce_out", "pe_in", "pe_out"))] if "z_s" in r else [],
}

_FEAT = {}


def feat(idx, day):
    if (idx, day) not in _FEAT:
        _FEAT[(idx, day)] = features(idx, day)
    return _FEAT[(idx, day)]


class Ref:
    """The size reference: prior sessions of the same index and kind, by day-part; else today's own minutes so far."""

    def __init__(self, idx, day, knd):
        prior = [d for d in days(idx) if d < day]
        same = [d for d in prior if feat(idx, d)["kind"] == knd][-REF_DAYS:]
        self.src = f"{len(same)} pichhle {knd.lower()} din" if len(same) >= MIN_DAYS else None
        self.pool = {}
        if self.src:
            for d in same:
                for r in feat(idx, d)["rows"]:
                    p = part(r["t"])
                    for name, f in METRICS.items():
                        self.pool.setdefault((name, p), []).extend(f(r))
            for v in self.pool.values():
                v.sort()
        self.own = {}                       # today's own minutes so far (the fallback), filled as the replay walks

    def add_own(self, r):
        for name, f in METRICS.items():
            for x in f(r):
                bisect.insort(self.own.setdefault(name, []), x)

    def tag(self, name, x, m):
        """0 noise / 1 notable / 2 BADA / None could not check -- and the reference's own name."""
        if x is None:
            return None
        v = self.pool.get((name, part(m))) if self.src else None
        if not v or len(v) < 30:
            v = self.own.get(name)
            if not v or len(v) < OWN_MIN:
                return None
        lo, hi = bisect.bisect_left(v, abs(x)), bisect.bisect_right(v, abs(x))
        pct = 100.0 * (lo + hi) / 2 / len(v)
        return 2 if pct >= P_BADA else 1 if pct >= P_NOTE else 0

    def name(self, m):
        return self.src if self.src and len(self.pool.get(("z_s", part(m))) or ()) >= 30 else "aaj ke minute"


# ---- the side structure (DESIGN §2a) --------------------------------------------------------------------------------

SIDE = {  # (andar sign, bahar sign) -> (code, words CE, words PE, push up for CE, push up for PE)
    (1, 1): ("LIKH", "CALL likh rahe", "PUT likh rahe", -2, 2),
    (1, 0): ("ANDAR_LIKH", "CALL ATM/ITM likh rahe", "PUT ATM/ITM likh rahe", -2, 2),
    (0, 1): ("DEEWAR_MOTI", "upar deewar moti", "neeche deewar moti", -1, 1),
    (-1, 1): ("ROLL_BAHAR", "CALL roll UP", "PUT roll DOWN", 1, -1),
    (1, -1): ("ROLL_ANDAR", "CALL roll DOWN", "PUT roll UP", -2, 2),
    (-1, -1): ("BHAAG", "CALL bhaag rahe", "PUT bhaag rahe", 2, -2),
    (-1, 0): ("ANDAR_BHAAG", "CALL ITM cover", "PUT ITM cover", 2, -2),
    (0, -1): ("DEEWAR_PATLI", "upar deewar hat rahi", "neeche deewar hat rahi", 1, -1),
    (0, 0): ("RUKE", "CALL ruke", "PUT ruke", 0, 0),
}
WRITING = {"LIKH", "ANDAR_LIKH", "ROLL_ANDAR", "DEEWAR_MOTI"}
COVERING = {"BHAAG", "ANDAR_BHAAG"}


def side_of(r, s, ref):
    """{code, words, push(up), size tag} for side s ('ce'/'pe') over the slow window."""
    a, b = r[s + "_in"], r[s + "_out"]
    g = abs(a) + abs(b)
    tg = ref.tag("side", g, r["t"])
    if not tg:
        key = (0, 0)
    else:
        sg = lambda x: 0 if abs(x) < ROLE * g else (1 if x > 0 else -1)      # noqa: E731
        key = (sg(a), sg(b))
    code, wce, wpe, uce, upe = SIDE[key]
    return {"code": code, "words": wce if s == "ce" else wpe, "push": uce if s == "ce" else upe, "tag": tg,
            "in": a, "out": b, "net": a + b}


def speed_word(now, prev, tg):
    """Speed change of one side over the fast window: TEZ / BARABAR / DHEEMA / PALTA / SHURU / RUK."""
    if now is None or prev is None:
        return "?"
    a, b = abs(now), abs(prev)
    if not tg:
        return "RUK" if b > 2 * a and b > 0 else "—"
    if b < 0.25 * a:
        return "SHURU"
    if now * prev < 0:
        return "PALTA"
    return "TEZ" if a >= 1.5 * b else "DHEEMA" if a * 1.5 <= b else "BARABAR"


# ---- one minute's raw story (DESIGN §2b) -----------------------------------------------------------------------------

def L(x):
    """OI in lakh, the Board's unit."""
    a = abs(x) / 1e5
    return ("+" if x > 0 else "−" if x < 0 else "") + (f"{a:.0f}" if a >= 10 else f"{a:.1f}") + "L"


def lead_strikes(r, s, sign, n=2):
    """The strikes carrying side s's flow of this sign, biggest first: '22700CE −31L 22650CE −12L'."""
    ks = sorted((k for k, v in r[s + "_k"].items() if v * sign > 0), key=lambda k: -abs(r[s + "_k"][k]))[:n]
    return " ".join(f"{k:.0f}{s.upper()} {L(r[s + '_k'][k])}" for k in ks)


def n_strikes(r, s, sign, zone_total):
    """How many strikes carry >= 10% of the zone flow with its sign (agreement across strikes, not one print)."""
    if not zone_total:
        return 0
    return sum(1 for v in r[s + "_k"].values() if v * sign > 0 and abs(v) >= 0.1 * abs(zone_total) * r["oi"] / 100)


def side_line(r, sd, s):
    """'CE: 22700 −31L 22650 −12L | +22800 +9L' -- the side's biggest cover and biggest add, by strike."""
    out, add = lead_strikes(r, s, -1, 2), lead_strikes(r, s, 1, 2)
    parts = [p for p in (out, add) if p]
    return f"{sd['words']} [{' · '.join(parts) or 'flat'}]"


def story(r, ref, hist):
    """The raw (unheld) story at this minute. regime: CHAL / CHOP / ATKA / PIN / KHAMOSH / ? ; d: +1 / -1 / 0."""
    t = r["t"]
    if "blind" in r:
        return {"regime": "?", "d": 0, "name": "PADH NAHI SAKE", "line": r["blind"], "size": None}
    if "z_s" not in r or "z_f" not in r:
        return {"regime": "?", "d": 0, "name": "PADH RAHE", "line": f"{S_MIN[ref.idx]} min ka record chahiye", "size": None}
    ts, tz, tf = ref.tag("d_s", r["d_s"], t), ref.tag("z_s", r["z_s"], t), ref.tag("z_f", r["z_f"], t)
    tg = ref.tag("gross", sum(abs(r[k]) for k in ("ce_in", "ce_out", "pe_in", "pe_out")), t)
    if ts is None or tz is None:
        return {"regime": "?", "d": 0, "name": "PAIMANA NAHI", "line": "no size reference yet", "size": None}
    D = (1 if r["d_s"] > 0 else -1) if ts else 0
    Z = (1 if r["z_s"] > 0 else -1) if tz else 0
    ce, pe = side_of(r, "ce", ref), side_of(r, "pe", ref)
    S = S_MIN[ref.idx]
    base = {"ce": ce, "pe": pe, "D": D, "Z": Z, "ts": ts, "tz": tz, "tg": tg, "tf": tf,
            "pts": f"spot {r['d_s'] * r['step']:+.0f} pts/{S}m · net {L(r['z_s'] * r['oi'] / 100)}",
            "sides": f"{side_line(r, ce, 'ce')} | {side_line(r, pe, 'pe')}"}
    seq = [h for h in hist if t - h[0] <= LOOK and h[1]]           # notable fast-pressure minutes, last 30 min
    turns = sum(1 for a, b in zip(seq, seq[1:]) if a[2] != b[2])

    if D:
        a = UP if D > 0 else DN
        lose, win = (ce, pe) if D > 0 else (pe, ce)                # the side the move hurts / the side it pays
        ln, wn = ("CALL", "PUT") if D > 0 else ("PUT", "CALL")
        if Z == -D:
            stuck = not ref.tag("d_f", r["d_f"], t)
            return dict(base, regime="CHAL", d=D, kind="ULTA", size=tz,
                        name=f"{ln} LIKHAI INTO {'RALLY' if D > 0 else 'FALL'} · {'ROK RAHE' if stuck else 'PHANS RAHE'}",
                        line=f"{ln} writers adding while price {'stalls' if stuck else 'runs through them'}")
        if lose["code"] in COVERING and win["code"] in WRITING:
            k, sz, name, why = "BOTH", max(lose["tag"], win["tag"]), f"{ln} BHAAG + {wn} LIKHAI {a}", f"{ln} chhod rahe aur {wn} likh rahe — dono engine"
        elif lose["code"] in COVERING:
            k, sz, name, why = "COVER", lose["tag"], f"{ln} BHAAG RAHE {a}", f"{ln} writers chhod rahe — fuel"
        elif lose["code"] == "ROLL_BAHAR":
            k, sz, name, why = "ROLL", lose["tag"], f"{ln} {'CAP UPAR' if D > 0 else 'FLOOR NEECHE'} SHIFT {a}", f"{ln} roll kar rahe, abhi bhi short"
        elif win["code"] in WRITING:
            k, sz, name, why = "WIN", win["tag"], f"{wn} {'FLOOR' if D > 0 else 'CAP'} SAATH {a}", f"{wn} writers price ke saath"
        elif Z == 0:
            k, sz, name, why = "KHAALI", 0, f"KHAALI CHAAL {a}", "price chal raha, OI chup — writer peeche nahi"
        else:
            k, sz, name, why = "NET", tz, f"OI SAATH {a}", "zor saath, structure mila-jula"
        return dict(base, regime="CHAL", d=D, kind=k, name=name, line=why, size=sz)

    if turns >= CHOP_TURNS and r["rng30"] >= CHOP_RANGE and abs(r["d30"]) <= 0.5 * r["rng30"]:
        return dict(base, regime="CHOP", d=0, kind="CHOP", name="CHOP · BAARI BAARI", size=tf,
                    line=f"zor {turns} baar palta · range {r['rng30'] * r['step']:.0f} pts/30m · net {r['d30'] * r['step']:+.0f}")
    if Z:
        a = UP if Z > 0 else DN
        lead = pe if (Z > 0) == (pe["push"] * Z > ce["push"] * Z) else ce
        return dict(base, regime="ATKA", d=Z, kind="ATKA", name=f"ATKA {a} · ZOR HAI, PRICE NAHI", size=tz,
                    line=f"{lead['words']} · price ruka")
    p = r.get("pin")
    if p and tg and ce["net"] > 0 and pe["net"] > 0 and min(ce["net"], pe["net"]) >= 0.33 * max(ce["net"], pe["net"]) \
            and r["rng30"] <= PIN_RANGE:
        return dict(base, regime="PIN", d=0, kind="PIN_BAN", name=f"PIN BAN RAHA @ {p['k']:.0f}s", size=tg,
                    line=f"dono likh rahe · CE {L(ce['net'] * r['oi'] / 100)} PE {L(pe['net'] * r['oi'] / 100)} /{S}m")
    if p and r["rng30"] <= PIN_TIGHT and abs(r["spot"] - p["k"]) <= 0.5 * r["step"] and p["bal"] >= 0.6 and p["top"]:
        return dict(base, regime="PIN", d=0, kind="PIN_TIKA", name=f"PIN TIKA @ {p['k']:.0f}s", size=None,
                    line=f"{p['k']:.0f}: CE {L(p['ce'])} · PE {L(p['pe'])} baithe · range {r['rng30'] * r['step']:.0f} pts/30m")
    return dict(base, regime="KHAMOSH", d=0, kind="Q", name="KUCH KHAAS NAHI", size=0,
                line="koi flow noise se upar nahi")


# ---- the held picture: a LEG with its phase, else the held raw regime (DESIGN §2c) -------------------------------

def leg_phase(st, leg, r, ref):
    """SHURU / TEZ / JAARI / RUKA / THAK inside a held leg, from this minute's raw story."""
    d, t = leg["d"], r["t"]
    if t - leg["t0"] < 5:
        return "SHURU"
    fresh = t - leg["ext_t"] <= 3                                           # a new extreme in the last 3 min
    if (st["regime"] == "CHAL" and st["d"] == d and st.get("kind") == "ULTA") or \
            (st["regime"] == "ATKA" and st["d"] == -d) or \
            (st["regime"] == "CHAL" and st["d"] == d and st.get("kind") == "KHAALI" and fresh):
        return "THAK"
    if st["regime"] == "CHAL" and st["d"] == d:
        zf, zp = r.get("z_f"), r.get("z_fp")
        if st["tf"] and zf * d > 0 and zp is not None and abs(zf) >= 1.5 * abs(zp) and fresh:
            return "TEZ"
        return "JAARI"
    return "RUKA"


def grade(kind_, st, r, ref, held, futr, peers):
    """[(check, True / False / None)]: None = could not check, never a miss. The count n/N is the grade."""
    ch = []
    if kind_ not in ("PIN_TIKA",) and st.get("size") is not None:
        ch += [("size ≥ notable", st["size"] >= 1), ("size BADA", st["size"] >= 2)]
    ch += [("5 min tika", held >= 5), ("15 min tika", held >= 15)]
    reg, D = st["regime"], st["d"]
    if reg in ("CHAL", "ATKA") and "z_s" in r:
        s = ("pe" if D > 0 else "ce") if reg == "CHAL" and st.get("kind") != "ULTA" else ("ce" if D > 0 else "pe")
        if st.get("kind") in ("COVER", "BOTH", "ROLL"):
            s = "ce" if D > 0 else "pe"                                     # the covering side is the evidence
        sd = st["pe"] if s == "pe" else st["ce"]
        zone = sd["in"] if abs(sd["in"]) >= abs(sd["out"]) else sd["out"]
        ch.append(("2+ strikes", bool(zone) and n_strikes(r, s, 1 if zone > 0 else -1, zone) >= 2))
        if reg == "CHAL":
            ch.append(("price abhi bhi chal raha", bool(ref.tag("d_f", r["d_f"], r["t"])) and r["d_f"] * D > 0))
        else:
            ch.append(("price sach mein ruka", not ref.tag("d_f", r["d_f"], r["t"])))
        ch.append(("fut leg saath", None if futr is None else futr == D))
    elif reg in ("PIN", "CHOP"):
        ch.append(("price band mein", r.get("rng30", 99) <= (PIN_RANGE if reg == "PIN" else 3)))
        ch.append(("fut leg chup", None if futr is None else futr == 0))
    for name, pd in peers:
        if reg in ("CHAL", "ATKA"):
            ch.append((f"{SHORT[name]} saath", None if pd is None else pd == D))
        elif reg in ("PIN", "CHOP"):
            ch.append((f"{SHORT[name]} bhi bina disha", None if pd is None else pd == 0))
    return ch


def count(ch):
    """(n, N) over the checks that could be read. THE SIZE GATE: when the story's own OI flow did not clear notable,
    n is capped at 3 (KAMZOR) whatever else agrees -- persistence and peers grade a flow, they never replace one."""
    seen = [ok for _, ok in ch if ok is not None]
    n = sum(1 for ok in seen if ok)
    gate = dict(ch).get("size ≥ notable")
    return (min(n, 3) if gate is False else n), len(seen)


def word(n, N):
    """The grade's word from the count: never a %, never a probability."""
    if not N:
        return "?"
    return "MAZBOOT" if n >= 6 else "THEEK" if n >= 4 else "KAMZOR"


def fut_vote(futm, m):
    """§1o's fut_oi vote over 15 min: |fut OI change| >= 0.10 % -> the sign of the fut price move, else 0; None absent."""
    if not futm or m not in futm or (m - 15) not in futm:
        return None
    (p1, o1), (p0, o0) = futm[m], futm[m - 15]
    if abs(o1 - o0) / o0 * 100 < FUT_OI_PCT:
        return 0
    return (p1 > p0) - (p1 < p0)


def flat_key(st, qualifies):
    """The non-leg picture a raw story asks for: (regime, d)."""
    reg, D = st["regime"], st["d"]
    if reg == "CHAL":                  # a move that may become a leg has no flat picture of its own (None)
        return None if qualifies else ("ATKA", st["Z"]) if st.get("kind") == "ULTA" else ("KHAALI", D)
    return (reg, D)


def flips_since(swings, t0):
    s = [x for x in swings if x[0] >= t0]
    return sum(1 for a, b in zip(s, s[1:]) if a[1] != b[1])


def chop_now(swings, spots, t, step):
    """CHOP from the SEQUENCE: >= 2 direction changes among the swings of the last CHOP_WIN min, a range of >= 2 steps,
    and a net move of no more than half that range (price went both ways and got nowhere)."""
    s = [x for x in swings if t - x[0] <= CHOP_WIN]
    flips = sum(1 for a, b in zip(s, s[1:]) if a[1] != b[1])
    w = [p for (m, p) in spots if t - m <= CHOP_WIN]
    rng = max(w) - min(w)
    return flips >= 2 and rng >= 2 * step and abs(w[-1] - w[0]) <= 0.5 * rng, flips, rng, w[-1] - w[0]


def run(idx, day, peers=None):
    """Causal replay of one index-day: the held picture each minute and the stamped lines."""
    fe = feat(idx, day)
    ref = Ref(idx, day, fe["kind"])
    ref.idx = idx
    futm = fut(idx, day)
    H, step = HOLD[idx], fe["step"]
    hist, out, stamps, swings, spots = [], [], [], [], []
    raw_key, raw_n, q_key, q_n = None, 0, None, 0
    leg, flat, since, last_chop, done = None, ("?", 0, ""), None, None, []
    ph, ph_cand, ph_n = "", "", 0
    side_mem = {s: {"ruke": None, "ev": -99} for s in ("ce", "pe")}
    rows = fe["rows"]
    for i, r in enumerate(rows):
        t = r["t"]
        spots.append((t, r["spot"]))
        st = story(r, ref, hist)
        if "z_f" in r:
            hist.append((t, bool(ref.tag("z_f", r["z_f"], t)), 1 if r["z_f"] > 0 else -1))
        ch_on, flips, rng60, net60 = chop_now(swings, spots, t, step)
        # a leg needs a BADA price move, or a notable one WITH the OI behind it; inside a chop, both (a breakout)
        q = st["regime"] == "CHAL" and st.get("kind") != "ULTA" and (
            (st["ts"] == 2 and st["Z"] == st["d"]) if ch_on else (st["ts"] == 2 or st["Z"] == st["d"]))
        qk = ("Q", st["d"]) if q else None
        q_n = q_n + 1 if qk == q_key and qk else (1 if qk else 0)
        q_key = qk
        key = flat_key(st, q)
        raw_n = raw_n + 1 if key == raw_key else 1
        raw_key = key
        if st["regime"] == "CHAL" and raw_n == H:                         # a swing: any held price move
            swings.append((t, st["d"]))
        # -- the leg: ends on half given back / an OI-backed opposite move / the chop / staleness
        if leg:
            if (r["spot"] - leg["ext"]) * leg["d"] > 0:
                leg["ext"], leg["ext_t"] = r["spot"], t
            size = abs(leg["ext"] - leg["px0"])
            back = (leg["ext"] - r["spot"]) * leg["d"]
            ended = None
            if back >= max(RETRACE * size, step):
                ended = f"price ne {back:.0f} pts wapas diye (leg {size:.0f} pts)"
            elif q_key == ("Q", -leg["d"]) and q_n >= H:
                ended = "ulta move shuru"
            elif flips_since(swings, leg["t0"]) >= 2:
                ended = f"chop: leg ke baad {flips_since(swings, leg['t0'])} palte, range {rng60:.0f} pts/60m"
            elif t - leg["ext_t"] >= STALE and st.get("Z") != leg["d"]:
                ended = f"{STALE} min se naya {'high' if leg['d'] > 0 else 'low'} nahi, zor saath nahi"
            if ended:
                stamps.append({"t": t, "kind": "END", "txt": f"MOVE {UP if leg['d'] > 0 else DN} KHATAM", "why": ended,
                               "st": st, "r": r, "leg": dict(leg)})
                done.append((leg["t0"], t, leg["d"], "back" if ended.startswith("price ne") or ended.startswith("ulta") else "x"))
                leg, flat = None, (key or ("KHAMOSH", 0)) + ("",)   # the picture the market is in now, no gap
                since = t
        if not leg and q_key and q_n >= H:
            j0 = max(0, i - q_n + 1)
            seg = [x["spot"] for x in rows[j0:i + 1]]
            prior = [x for x in done if t - x[1] <= TWO_WAY][-2:]
            two = len(prior) == 2 and prior[0][2] != prior[1][2] and prior[1][2] != st["d"] and \
                all(x[3] == "back" for x in prior)               # two legs in a row given back, alternating: chop day
            leg = {"d": st["d"], "t0": t - q_n + 1, "px0": rows[max(0, j0 - S_MIN[idx])]["spot"],
                   "ext": max(seg) if st["d"] > 0 else min(seg), "ext_t": t, "two": two}
            ph, ph_cand, ph_n, since = "SHURU", "SHURU", 0, leg["t0"]
            stamps.append({"t": leg["t0"], "at": t, "kind": "LEG", "st": st, "r": r, "leg": dict(leg)})
        # -- the picture: the leg with its phase, else CHOP from the sequence, else the held raw picture
        if leg:
            p = leg_phase(st, leg, r, ref)
            ph_n = ph_n + 1 if p == ph_cand else 1
            ph_cand = p
            if p != ph and ph_n >= H:
                old, ph = ph, p
                if p == "TEZ" or (p == "THAK" and not leg.get("thak")):
                    leg["thak"] = p == "THAK"
                    stamps.append({"t": t - ph_n + 1, "at": t, "kind": "PHASE", "ph": p, "old": old, "st": st, "r": r,
                                   "leg": dict(leg)})
            pic = ("CHAL", leg["d"], ph)
        else:
            want = ("CHOP", 0, "") if ch_on else (key + ("",)) if key and raw_n >= H else None
            if want and want != flat:                           # "?" too: could-not-check is never shown as quiet
                flat = want
                since = t - (raw_n if not ch_on else 1) + 1
                stamps.append({"t": since, "at": t, "kind": "FLAT", "st": st, "r": r,
                               "chop": (flips, rng60, net60) if ch_on else None})
            pic = flat
        # -- side events: covering into price / writing again after a stop / a wall rolled
        if "z_s" in r and st["regime"] != "?":
            for s, sd in (("ce", st["ce"]), ("pe", st["pe"])):
                m_ = side_mem[s]
                if sd["code"] == "RUKE":
                    m_["ruke"] = m_["ruke"] or t
                    continue
                ev, hurt = None, (1 if s == "ce" else -1)
                zone = sd["in"] if abs(sd["in"]) >= abs(sd["out"]) else sd["out"]
                if not (zone and n_strikes(r, s, 1 if zone > 0 else -1, zone) >= 2):
                    m_["ruke"] = None
                    continue
                if sd["code"] in COVERING and sd["tag"] == 2 and r["d_s"] * hurt > 0 and st["ts"] \
                        and not (leg and st.get("kind") in ("COVER", "BOTH")):
                    ev = f"{'CALL' if s == 'ce' else 'PUT'} BHAAG RAHE (price unke against)"
                elif sd["code"] in ("LIKH", "ANDAR_LIKH", "ROLL_ANDAR") and sd["tag"] == 2 and m_["ruke"] \
                        and t - m_["ruke"] >= RESTART:
                    ev = f"{'CALL' if s == 'ce' else 'PUT'} PHIR LIKHNE LAGE ({t - m_['ruke']} min ruk ke)"
                elif sd["code"] == "ROLL_BAHAR" and sd["tag"]:
                    ev = f"{'CALL CAP UPAR' if s == 'ce' else 'PUT FLOOR NEECHE'} SHIFT (roll, abhi bhi short)"
                m_["ruke"] = None
                if ev and t - m_["ev"] >= EV_GAP:
                    m_["ev"] = t
                    stamps.append({"t": t, "at": t, "kind": "SIDE", "txt": ev, "side": s, "sd": sd, "st": st, "r": r})
        held = t - since + 1 if since is not None else 0
        pr = [(n, (peers or {}).get(n, {}).get(t)) for n in IDXS if n != idx] if peers is not None else []
        fv = fut_vote(futm, t)
        ch = []
        if pic[0] == "CHAL":
            if st["regime"] == "CHAL" and st["d"] == pic[1] and st.get("kind") not in ("ULTA", "KHAALI"):
                oi_size = st["size"]
            else:
                oi_size = (st.get("tz") or 0) if st.get("Z") == pic[1] else 0 if st.get("tz") is not None else None
            ch = grade(st.get("kind"), dict(st, regime="CHAL", d=pic[1], size=oi_size), r, ref, held, fv, pr)
            ch.append(("chop ke bahar", not leg["two"] and (last_chop is None or leg["t0"] - last_chop > CHOP_WIN)))
        elif pic[0] in ("CHOP", "PIN", "ATKA") and "z_s" in r and (ch_on and pic[0] == "CHOP" or key == pic[:2]):
            ch = grade(st.get("kind"), dict(st, regime=pic[0], d=pic[1]), r, ref, held, fv, pr)
        if pic[0] == "CHOP":
            last_chop = t
        spd = None
        if "ce_fp" in r:                                    # each side's speed now vs the 5 min before (L/min)
            per = F_MIN[idx] * 100 * 1e5
            spd = [(s_.upper(), r[s_ + "_f"] * r["oi"] / per, speed_word(r[s_ + "_f"], r[s_ + "_fp"],
                    ref.tag("side_f", r[s_ + "_f"], t))) for s_ in ("ce", "pe")]
        out.append({"t": t, "spot": r["spot"], "st": st, "pic": pic, "held": held, "ch": ch, "fut": fv, "ref": ref.name(t),
                    "spd": spd,
                    "r": r, "leg": leg["t0"] if leg else None,
                    "chop": (flips, rng60, net60) if pic[0] == "CHOP" and ch_on else None})
        if "z_s" in r:
            ref.add_own(r)
    return {"idx": idx, "day": day, "kind": fe["kind"], "rows": out, "stamps": keep(stamps, out), "all": len(stamps),
            "step": step, "fut": futm is not None}


def keep(stamps, out):
    """The printed lines. A held picture (a leg, ATKA, CHOP, PIN) is stamped at the FIRST minute its grade reaches
    THEEK (n >= 4) -- at its birth if it is born strong, later if the OI joins later, never if it stays KAMZOR (it is
    shown live, small). KHAMOSH / KHAALI / ? are stamped once, only after a printed picture. Inside a printed leg: TEZ
    (grade >= 4) and the first THAK; its END. Side events as filtered in the walk."""
    kept, printed, last, i = [], {}, None, 0
    while i < len(out):
        o = out[i]
        key = (o["pic"][0], o["pic"][1], o.get("leg"))
        j = i
        while j + 1 < len(out) and (out[j + 1]["pic"][0], out[j + 1]["pic"][1], out[j + 1].get("leg")) == key:
            j += 1
        reg = o["pic"][0]
        if reg in ("CHAL", "ATKA", "CHOP", "PIN"):
            hit = next((x for x in out[i:j + 1] if count(x["ch"])[0] >= 4 and
                        (reg != "CHAL" or (x["st"]["regime"] == "CHAL" and x["st"]["d"] == x["pic"][1]))), None)
            if hit:
                kept.append({"t": hit["t"], "at": hit["t"], "kind": "PIC", "from": o.get("leg") or o["t"],
                             "st": hit["st"], "r": hit["r"], "pic": hit["pic"], "chop": hit.get("chop")})
                last = reg
                if reg == "CHAL":
                    printed[o.get("leg")] = hit["t"]
        elif last is not None and (last not in ("KHAMOSH", "?", "KHAALI") or (reg == "?" and last != "?"))                 and out[j]["t"] - o["t"] + 1 >= QUIET_MIN:            # "could not check" is never folded into quiet
            kept.append({"t": o["t"], "at": o["t"], "kind": "PIC", "from": o["t"], "st": o["st"], "r": o["r"],
                         "pic": o["pic"]})
            last = reg
        i = j + 1
    for s_ in stamps:
        if s_["kind"] == "PHASE" and s_["leg"]["t0"] in printed and s_["t"] > printed[s_["leg"]["t0"]]:
            o = next(x for x in out if x["t"] == s_["at"])
            if s_["ph"] == "THAK" or count(o["ch"])[0] >= 4:
                kept.append(dict(s_, pic=o["pic"]))
        elif s_["kind"] == "END" and s_["leg"]["t0"] in printed:
            printed.pop(s_["leg"]["t0"])                    # one END per printed leg
            kept.append(s_)
        elif s_["kind"] == "SIDE":
            kept.append(s_)
    kept.sort(key=lambda x: (x["t"], 0 if x["kind"] == "END" else 1))
    return kept


def dirs_of(res):
    """{minute: the held picture's direction} for the peer check: d for CHAL / ATKA, 0 for CHOP / PIN / KHAMOSH."""
    return {o["t"]: (None if o["pic"][0] == "?" else o["pic"][1] if o["pic"][0] in ("CHAL", "ATKA", "KHAALI") else 0)
            for o in res["rows"]}


# ---- the other voices (DESIGN §6) -----------------------------------------------------------------------------------

def read_words(day):
    """THE READ's word per index per 5-min mark, from its forward log (data/read), or None."""
    p = os.path.join(DATA, "read", f"read_{day}.jsonl")
    if not os.path.exists(p):
        return None
    out = {}
    for line in open(p, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") == "mark" and r.get("word"):
            out.setdefault(r["idx"], {})[mm(r["t"])] = (r["word"], r.get("dir") or 0)
    return out


def read_at(rw, idx, m):
    if not rw or idx not in rw:
        return None
    ks = [k for k in rw[idx] if k <= m]
    return rw[idx][max(ks)] if ks else None


def fronts_at(idx, day, m):
    """§1d's fronts on the grid cut at minute m, through tapemap/fronts.py itself (pure, imported read-only)."""
    if TAPEMAP not in sys.path:
        sys.path.insert(0, TAPEMAP)
    import fronts
    G = grid(idx, day)
    mins, peak = {}, {}
    for i, t in enumerate(G["t"]):
        if t > m:
            break
        mins[hm(t)] = {"spot": G["spot"][i], "k": {k: (G["cchg"][k][i] or 0, G["pchg"][k][i] or 0)
                                                   for k in G["ks"] if G["cchg"][k][i] is not None}}
        for k in G["ks"]:
            for s in ("ce", "pe"):
                x = G[s][k][i]
                if x is not None:
                    peak[(k, s)] = max(peak.get((k, s), 0), x)
    return fronts.read(mins, peak)


def trapped(idx, day, m, r, side, n=2):
    """PHANSE: the strikes this side is covering NOW were written in the last 60 min (their OI peaked inside the hour
    and was built up to that peak from below) -- the writers who wrote into the move are the ones buying back. [M] on
    the grid, the word [I]. '' when no covered strike was built inside the hour."""
    G = grid(idx, day)
    pos = {t: i for i, t in enumerate(G["t"])}
    i = pos.get(m)
    if i is None or not r.get(side + "_k"):
        return ""
    out = []
    for k in sorted((k for k, v in r[side + "_k"].items() if v < 0), key=lambda k: r[side + "_k"][k])[:n]:
        js = [j for j in range(i + 1) if m - G["t"][j] <= 60 and G[side][k][j] is not None]
        if not js:
            continue
        jp = max(js, key=lambda j: G[side][k][j])
        built = G[side][k][jp] - G[side][k][js[0]]
        if built > 0 and built >= 0.5 * -r[side + "_k"][k] and jp != js[0]:
            out.append(f"{k:.0f}{side.upper()} {L(built)} {hm(G['t'][jp])} tak likha")
    return ("PHANSE: " + " · ".join(out)) if out else ""


def fronts_txt(fr):
    ab = {"BUILDING": "B", "STALLED": "S", "UNWINDING": "U"}
    return " ".join(f"{f['side']}{f['k']:.0f}:{ab[f['state']]}" for f in fr) or "?"


WORD = {"CHAL": "CHAL RAHA", "KHAALI": "KHAALI CHAAL", "ATKA": "ATKA", "CHOP": "CHOP", "PIN": "PIN", "KHAMOSH": "KHAMOSH", "?": "?"}
STRIP = {"CHAL": None, "KHAALI": "k", "ATKA": "a", "CHOP": "~", "PIN": "P", "KHAMOSH": "·", "?": "?"}


def headline(pic):
    reg, d, ph = pic
    a = UP if d > 0 else DN if d < 0 else ""
    return (WORD[reg] + (" " + a if a else "") + (" · " + ph if ph else "")).strip()


def strip(res):
    """One character per 5 minutes of the held picture: ▲ ▼ leg (lower-case a = ATKA), ~ chop, P pin, · quiet."""
    s = ""
    for o in res["rows"]:
        if o["t"] % 5 == 0:
            reg, d, ph = o["pic"]
            s += (UP if d > 0 else DN) if reg == "CHAL" else STRIP[reg]
    return s


def contra(rw, idx, m, pic, st, ch):
    """One line when RAFTAAR and THE READ disagree -- only when RAFTAAR's own grade is MAZBOOT (never on noise), and
    never for a chop-day swing against a RANGE read (both are true at their own scale). None when they agree."""
    rd = read_at(rw, idx, m)
    n, N = count(ch)
    if not rd or rd[0] not in ("TREND", "LEAN", "RANGE") or n < 6:
        return None
    w, rdir = rd
    mine = pic[1] if pic[0] in ("CHAL", "ATKA") else 0
    swing = dict(ch).get("chop ke bahar") is False
    a = lambda d: UP if d > 0 else DN if d < 0 else ""             # noqa: E731
    dis = (w == "RANGE" and pic[0] == "CHAL" and not swing) or (w != "RANGE" and rdir and pic[0] == "CHAL" and mine != rdir) or \
          (w != "RANGE" and rdir and pic[0] in ("CHOP", "PIN"))
    if not dis:
        return None
    return f"≠ READ {w}{a(rdir)} · RAFTAAR {headline(pic)} {n}/{N}: {st.get('pts', '')}"


def fmt_day(day, results):
    rw = read_words(day)
    L_ = [f"RAFTAAR replay (OPUS round 1) — {day} — causal, minute by minute. A line is stamped only when the held picture",
          f"changes. Grade = agreement count n/N at the stamp → 10 min later (never a %). [I] throughout; OI lakh; levels spot.",
          f"THE READ log for the day: {'yes' if rw else 'none (READ forward log starts 9 Oct)'}", ""]
    for res in results:
        rows = res["rows"]
        if not rows:
            continue
        idx = res["idx"]
        sp = [o["spot"] for o in rows]
        byt = {o["t"]: o for o in rows}
        L_.append(f"== {idx} · {res['kind']} · spot {sp[0]:.0f} → {sp[-1]:.0f} (H {max(sp):.0f} L {min(sp):.0f}) · "
                  f"fut leg {'NIFTY fut' if idx == 'SENSEX' and res['fut'] else 'yes' if res['fut'] else 'not recorded'} · "
                  f"size ref: {rows[-1]['ref']}")
        L_.append(f"   strip (5 min, 09:15→): {strip(res)}")
        for s in sorted(res["stamps"], key=lambda x: (x["t"], x.get("at", x["t"]))):
            at = s.get("at", s["t"])
            o = byt[at]
            o10 = byt.get(at + 10) or o
            n, N = count(o["ch"])
            n2, N2 = count(o10["ch"]) if o10["pic"][:2] == o["pic"][:2] else (None, None)
            g = (f"{n}/{N}" + (f"→{n2}/{N2}" if N2 else "") + f" {word(n2 if N2 else n, N2 or N)}") if N else ""
            st = s["st"]
            if s["kind"] == "PIC":
                o = byt[s["at"]]
                head = headline(o["pic"])
                name = st["name"]
                if o["pic"][0] == "CHOP" and s.get("chop"):
                    fl, rg, nt = s["chop"]
                    name = f"CHOP · 60 min mein {fl} palte · range {rg:.0f} · net {nt:+.0f} pts"
                if s["from"] != s["t"]:
                    name += f"  (picture {hm(s['from'])} se)"
                if o["pic"][0] == "CHAL" and dict(o["ch"]).get("chop ke bahar") is False:
                    name += "  [CHOP ke andar: swing]"
                if st.get("kind") in ("COVER", "BOTH") and st["regime"] == "CHAL" and o["pic"][0] == "CHAL":
                    tr = trapped(idx, day, s["at"], s["r"], "ce" if st["d"] > 0 else "pe")
                    if tr:
                        name += f"  {tr}"
            elif s["kind"] == "PHASE":
                head, name = headline(("CHAL", s["leg"]["d"], s["ph"])), st["name"]
            elif s["kind"] == "END":
                head, name, g = s["txt"], s["why"], ""
            elif s["kind"] == "SIDE":
                head, name, g = "· " + s["txt"], side_line(s["r"], s["sd"], s["side"]), ""
            elif o["pic"][0] == "CHOP" and s.get("chop"):
                fl, rg, nt = s["chop"]
                head, name = headline(o["pic"]), f"CHOP · 60 min mein {fl} palte · range {rg:.0f} · net {nt:+.0f} pts"
            else:
                head, name = headline(o["pic"]), st["name"]
            L_.append(f"  {hm(s['t'])}  {s['r']['spot']:9.1f}s  {head:<24} {g:<17} {name}")
            if s["kind"] in ("PIC", "PHASE"):
                sp_ = o.get("spd")
                rt = " · raftaar " + " ".join(f"{a} {b:+.1f}L/m {c}" for a, b, c in sp_) if sp_ else ""
                L_.append(f"  {'':>19} {st.get('line', '')} · {st.get('pts', '')}{rt}")
                if st.get("sides"):
                    L_.append(f"  {'':>19} {st['sides']}")
            if s["kind"] in ("END", "PIC"):
                try:
                    L_.append(f"  {'':>19} §1d fronts: {fronts_txt(fronts_at(idx, day, at))}")
                except Exception as e:                          # fronts' failure is its own '?', never the replay's
                    L_.append(f"  {'':>19} §1d fronts: ? ({type(e).__name__})")
            c = None
            if s["kind"] == "PIC":
                c = contra(rw, idx, s["t"], o["pic"], st, o["ch"])
                if not c and o10 is not o and o10["pic"][:2] == o["pic"][:2]:
                    c = contra(rw, idx, o10["t"], o10["pic"], o10["st"], o10["ch"])
                    c = c and f"{hm(o10['t'])} {c}"
            if c:
                L_.append(f"  {'':>19} {c}")
        L_.append("")
    return "\n".join(L_)


def replay(day):
    first = {i: run(i, day) for i in IDXS if day in days(i)}
    dirs = {i: dirs_of(r) for i, r in first.items()}
    final = [run(i, day, dirs) for i in first]
    os.makedirs(OUT, exist_ok=True)
    txt = fmt_day(day, final)
    with open(os.path.join(OUT, f"{day}.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    return final, txt


def check():
    """The smallest thing that fails if the logic breaks."""
    assert SIDE[(-1, 1)][1] == "CALL roll UP" and SIDE[(-1, 1)][2] == "PUT roll DOWN"
    assert speed_word(3.0, 1.0, 1) == "TEZ" and speed_word(1.0, 3.0, 1) == "DHEEMA" and speed_word(-2, 2, 1) == "PALTA"
    assert word(6, 8) == "MAZBOOT" and word(4, 8) == "THEEK" and word(2, 8) == "KAMZOR"
    assert count([("a", True), ("b", None), ("c", False)]) == (1, 2)          # a missing check is not a miss
    assert kind("BANKNIFTY", "2026-09-29", None) == "EXPIRY" and kind("NIFTY", "2026-09-24", None) == "NORMAL"
    assert kind("NIFTY", "2026-09-22", None) == "EXPIRY"
    leg = {"d": -1, "t0": 600, "ext": 100.0, "ext_t": 610}
    r = {"t": 612, "z_f": -2.0, "z_fp": -1.0}
    assert leg_phase({"regime": "ATKA", "d": 1}, leg, r, None) == "THAK"           # pressure against a stalled fall
    assert leg_phase({"regime": "KHAMOSH", "d": 0}, leg, r, None) == "RUKA"        # a pause is not a turn
    print("check ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        check()
    else:
        for d in sys.argv[1:]:
            _, txt = replay(d)
            print(txt)
