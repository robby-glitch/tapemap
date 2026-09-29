"""reader.py -- THE LEG ENGINE of the order-flow reader (R-a, R-b, R-c on the front contract). SHADOW ONLY.

WHAT IT IS (docs/reader/7-final-design.md §3.2 items 1-4, as ruled by docs/reader/6-judgement.md):
  * ONE CANONICAL MINUTE. Price, volume and OI come from the exchange's 1-minute candle when one is given,
    otherwise from the Upstox book (`src` says which). Delta always comes from the book, per frame, with
    ladder.attribute at the index's RUPEE tick (not the paise tick; audit 2-data-audit.md §3f).
    One volume universe per ratio: delta share uses book (vtt) volume, never candle volume.
  * THE RULER IS FROZEN AT THE OPEN: delta = K x fold's prior-session unit (median 1-minute high-low pooled
    over up to 5 prior sessions, fold.PRIOR_B). It never re-sizes intraday. With no prior session the ruler
    is set from the day's own first 15 minutes and says it is not causal before then (fold's own fallback).
  * LEGS: directional change confirmed on 1-MINUTE CLOSES (a restart rebuilds the same cut); extremes are
    minute highs/lows. The pivot minute belongs to the leg it ends.
  * AUCTION: TREND / RANGE / BREAKOUT. Legs confirm on closes; a range breakout and a broken trend are read
    live on the minute's high/low (her invalidations never wait for a close).
  * EFFORT vs RESULT per leg, per tape: points per 1,000 lots of net delta, ranked only against TODAY's
    completed legs, with n; mute (says "warming") until 3 legs exist on that tape.
    UX delta is attributed by minute. GoCharting (GC) delta only on legs holding >= 2 whole GC bars.
    Blocks and spread prints are excluded BY PRINT, never by bar.
  * WHO per leg (delta x OI x price) on the front contract: new longs / short covering / new shorts /
    long liquidation / rotation, plus ABSORBED. OI goes through the batched-OI screen and is read with a
    one-update tolerance at each end. Inside its roll window the contract is labelled "expiring" and
    every OI-down class carries "or roll". No word here is "bullish" or "bearish".

WHAT IT IS NOT: no curve / next-month read (that waits for next-month capture), no absorbed levels,
divergence, extremes, FLOW word or face. No hit rate, ever.

Pure: rows in, dicts and sentences out. No I/O, no clock. Every number carries [M] or [I]; delta is [I].
"""
from __future__ import annotations

import math
import statistics as st
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import fold
import ladder

# ---- THE THRESHOLD SHEET (h): every hand-picked number of this engine, in one place, for her signature.
SHEET: List[Tuple[str, float, str]] = [
    ("K", 3.0, "ruler = K x fold's prior-session median 1-min range, frozen at the open (judge §3.1)"),
    ("PRIOR_N", 5, "prior sessions pooled for the unit (fold.PRIOR_N)"),
    ("SELF_N", 15, "no prior session on disk: the ruler comes from the day's first 15 minutes (fold's fallback)"),
    ("THIN_UNIT", 0.5, "fold's 1-min unit gives way to the 5-min range / sqrt 5 only when below half of it (a thin book)"),
    ("SPREAD_X", 2.0, "the ruler is never under 2 x the median bid-ask spread (thin-book prints bounce across it)"),
    ("MIN_PRINTS", 30, "a tape names a side or an efficiency only on >= 30 traded frames in the leg (fewer is a sample)"),
    ("SHARE", 0.10, "a tape names the aggressor when |net delta| / its own volume >= this"),
    ("THIN", 0.05, "opposite-signed tapes both at or above this = SPLIT (no aggressor)"),
    ("UX_COVER", 0.90, "UX delta for a leg needs book minutes carrying >= 90% of the leg's volume"),
    ("OI_Z", 3.0, "OI moved when the whole one-update-tolerance range is beyond OI_Z x sigma x sqrt(updates) (fold.OI_Z)"),
    ("OI_SIGMA_N", 15, "OI updates needed before sigma is today's own (before that: the prior session's, else warming)"),
    ("PUB_SHARE", 0.5, "one publication step carrying >= half a leg's OI change: not read as positioning"),
    ("BLOCK_X", 100, "a print >= 100 x today's lots per trade (sum lots / sum trades) ..."),
    ("BLOCK_BAR", 0.25, "... and >= 25% of its 5-minute bar"),
    ("SPREAD_WIT", 0.5, "spread witness: >= half the print missing from the exchange candle, or mirrored in the other month's OI"),
    ("SPREAD_MIN", 2, "... the OI mirror within 2 minutes"),
    ("WARM_N", 3, "ranks mute until 3 completed legs have a defined efficiency on that tape"),
    ("LOW", 1 / 3, "low / easy efficiency = bottom / top third of today's legs ..."),
    ("PAIR", 0.5, "... or low = at most half the last same-way leg's efficiency"),
    ("ABSORB_MAX_R", 2.0, "'heavy effort, little progress' needs a low rank AND a leg under 2 rulers: a big move is not 'little'"),
    ("PAID_R", 3.0, "a leg of >= 3 rulers is never 'heavy effort, little progress'; a low rank there reads 'heavy effort, move paid'"),
    ("EDGE", 0.5, "RANGE: a trend-side pivot must extend by EDGE x delta; a pivot within it widens the band"),
    ("BREAK", 1.0, "BREAKOUT: a trade beyond the band by BREAK x delta"),
    ("GC_SHORT", 0.97, "a GC bar under 97% of the book's volume ..."),
    ("GC_SHORT_LOTS", 10, "... and short by more than 10 lots is a short bar (audit §3d)"),
    ("GC_MIN_BARS", 2, "GC effort only on legs holding >= 2 whole GC bars (judge §3.1)"),
    ("ROLL_SESSIONS", 5, "the expiring contract's roll window, in sessions to its instrument-master expiry"),
]
TH: Dict[str, float] = {k: v for k, v, _ in SHEET}
PRINT_KEEP = 25            # frames of >= 25 lots are kept as block/burst candidates (storage, not a read rule)
SESSION = (fold.SESSION_OPEN, fold.SESSION_CLOSE)     # the existing constants; the 15:40 change was dropped
GC_BAR_MS = 300000
REV = "shadow-1"


# ---- small helpers ----------------------------------------------------------------------------------------
def hm(ms: int) -> str:
    return ladder.hms_ist(ms)[:5]


def minute_of(ms: int) -> int:
    return int(ms) // 60000 * 60000


def in_session(ms: int) -> bool:
    return SESSION[0] <= ladder.hms_ist(ms) < SESSION[1]


def sgn(x: float) -> int:
    return (x > 0) - (x < 0)


def fmt(x: Optional[float], nd: int = 0, sign: bool = True) -> str:
    if x is None:
        return "?"
    s = f"{x:+,.{nd}f}" if sign else f"{x:,.{nd}f}"
    return s.replace("-", "−")


def robust_sigma(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    m = st.median(xs)
    return 1.4826 * st.median([abs(x - m) for x in xs])


def rupee_tick(dump_tick: Optional[float]) -> Optional[float]:
    """The instrument dump carries tick_size in PAISE (NIFTY 10.0 = 0.10 rupees; audit §3f)."""
    return dump_tick / 100.0 if dump_tick else None


def roll_window(day: str, expiry: Optional[str]) -> Tuple[bool, Optional[int]]:
    """(inside the roll window?, sessions left incl. today). Weekdays; holidays are not modelled in this repo."""
    if not expiry:
        return False, None
    d, e = date.fromisoformat(day), date.fromisoformat(expiry)
    if e < d:
        return False, None
    n, x = 0, d
    while x <= e:
        n += x.weekday() < 5
        x += timedelta(days=1)
    return n <= TH["ROLL_SESSIONS"], n


# ---- the canonical minute ---------------------------------------------------------------------------------
class BookMinutes:
    """Upstox book rows -> 1-minute records, INCREMENTALLY (the live hook tails the day file; a replay feeds it all):
    ltp OHLC [M], vtt volume [M], buy/sell by ladder.attribute at the rupee tick [I], last OI [M], the traded-frame
    count, the mean spread, and the big frames (block / burst candidates). Volumes and OI in lots."""

    def __init__(self, lot: int, tick: Optional[float]):
        self.lot, self.tick = lot, tick or 0.05
        self.out: Dict[int, dict] = {}
        self.prev = None

    def feed(self, r: dict) -> None:
        if r.get("t") is None:
            return
        lot = self.lot
        res = ladder.attribute(self.prev, r, self.tick) if self.prev is not None else None
        self.prev = r
        traded = res is not None and res["kind"] in ("exact", "recon", "unknown")
        t = r.get("ltt") if traded and r.get("ltt") else r["t"]
        m = minute_of(t)
        x = self.out.get(m)
        if x is None:
            x = self.out[m] = {"t": m, "o": None, "h": None, "l": None, "c": None, "bvol": 0.0, "buy": 0.0,
                               "sell": 0.0, "unk": 0.0, "oi": None, "prints": [], "nx": 0, "lx": 0.0, "nf": 0,
                               "spr": None, "_s": 0.0, "_n": 0}
        if r.get("oi") is not None:
            x["oi"] = r["oi"] / lot
        if r.get("b") and r.get("a") and r["a"][0][0] is not None and r["b"][0][0] is not None:
            x["_s"] += r["a"][0][0] - r["b"][0][0]
            x["_n"] += 1
            x["spr"] = x["_s"] / x["_n"]
        if not traded:
            return
        ltp = r.get("ltp")
        if ltp is not None:
            x["o"] = ltp if x["o"] is None else x["o"]
            x["h"] = ltp if x["h"] is None else max(x["h"], ltp)
            x["l"] = ltp if x["l"] is None else min(x["l"], ltp)
            x["c"] = ltp
        V = res["V"] / lot
        x["bvol"] += V
        x["nf"] += 1
        net = 0.0
        for f in res["fills"]:
            q = f["q"] / lot
            if f["side"] > 0:
                x["buy"] += q
            elif f["side"] < 0:
                x["sell"] += q
            else:
                x["unk"] += q
            net += f["side"] * q
        exact = res["kind"] == "exact"
        if exact:
            x["nx"] += 1
            x["lx"] += V
        if V >= PRINT_KEEP:
            x["prints"].append({"t": r["t"], "lots": V, "side": sgn(net), "p": ltp, "exact": exact})

    def minutes(self) -> List[dict]:
        return [self.out[k] for k in sorted(self.out)]


def book_minutes(rows, lot: int, tick: Optional[float]) -> List[dict]:
    """The whole-day form of BookMinutes."""
    bm = BookMinutes(lot, tick)
    for r in rows:
        bm.feed(r)
    return bm.minutes()


def candle_minutes(candles, lot: int) -> List[dict]:
    """Exchange 1-minute candles [ts, o, h, l, c, vol_units, oi_units] -> records in lots. ts: epoch ms or ISO."""
    out = []
    for c in candles:
        ts = c[0]
        t = int(ts) if isinstance(ts, (int, float)) else int(datetime.fromisoformat(ts).timestamp() * 1000)
        out.append({"t": minute_of(t), "o": c[1], "h": c[2], "l": c[3], "c": c[4],
                    "vol": c[5] / lot, "oi": (c[6] / lot) if c[6] is not None else None})
    return out


def canonical(book_mins: List[dict], candles: Optional[List[dict]] = None) -> List[dict]:
    """One record per session minute: price/volume/OI from the candle if present, else from the book; the
    side ONLY from the book (`bk` False = no book that minute: UX cannot be read there)."""
    cm = {c["t"]: c for c in candles or []}
    bm = {b["t"]: b for b in book_mins}
    out, last = [], None
    for t in sorted(set(cm) | set(bm)):
        if not in_session(t):
            continue
        c, b = cm.get(t), bm.get(t)
        px = c if c is not None else b
        notrade = px.get("o") is None
        if notrade:                       # the book was alive but nothing traded: a flat minute at the last price
            if last is None:
                continue
            px = {"o": last, "h": last, "l": last, "c": last}
        last = px["c"]
        out.append({"t": t, "o": px["o"], "h": px["h"], "l": px["l"], "c": px["c"], "notrade": notrade,
                    "vol": c["vol"] if c is not None else b["bvol"],
                    "oi": c["oi"] if c is not None else b["oi"],
                    "src": "candle" if c is not None else "book",
                    "cvol": c["vol"] if c is not None else None,
                    "bk": b is not None, "bvol": b["bvol"] if b else None,
                    "buy": b["buy"] if b else None, "sell": b["sell"] if b else None,
                    "prints": b["prints"] if b else [], "nx": b["nx"] if b else 0, "lx": b["lx"] if b else 0.0,
                    "nf": b["nf"] if b else 0, "spr": b["spr"] if b else None})
    return out


def prior_unit(prior_minute_lists: List[List[dict]]) -> Tuple[Optional[float], str]:
    """(unit, how). fold's PRIOR_B -- the median 1-minute high-low of traded minutes pooled over the prior
    sessions -- unless a thin book makes it understate by more than half: then the median 5-minute range / sqrt(5).
    A thin book can only shrink a 1-minute range (a minute of one print has none), never widen it; SENSEX futures
    print one price or none in 35-47% of minutes (22-29 Sep), which put fold's unit at 0-2 pts on a 73,000 index."""
    lists = prior_minute_lists[-int(TH["PRIOR_N"]):]
    r1 = [m["h"] - m["l"] for ms in lists for m in ms if m.get("h") is not None and not m.get("notrade")]
    r5 = []
    for ms in lists:
        bins: Dict[int, List[float]] = {}
        for m in ms:
            if m.get("h") is None:
                continue
            b = bins.setdefault(m["t"] // GC_BAR_MS, [m["h"], m["l"]])
            b[0], b[1] = max(b[0], m["h"]), min(b[1], m["l"])
        r5 += [h - l for h, l in bins.values()]
    u1 = st.median(r1) if r1 else 0.0
    u5 = st.median(r5) / math.sqrt(5) if r5 else 0.0
    if not u1 and not u5:
        return None, "no prior minutes"
    if u1 >= TH["THIN_UNIT"] * u5:
        return u1, "median 1-min range (fold's unit)"
    return u5, (f"median 5-min range / sqrt 5 = {u5:.2f}: the 1-min range {u1:.2f} is thin "
                f"({sum(1 for x in r1 if not x)} of {len(r1)} traded minutes printed one price)")


def prior_spread(prior_minute_lists: List[List[dict]]) -> Optional[float]:
    """The median minute-mean bid-ask spread of the prior sessions (book only), in points."""
    ss = [m["spr"] for ms in prior_minute_lists[-int(TH["PRIOR_N"]):] for m in ms if m.get("spr") is not None]
    return st.median(ss) if ss else None


def oi_sigma(minutes: List[dict]) -> Optional[float]:
    """Robust sigma of one session's batch-screened OI updates (lots): the next session's warm-up sigma."""
    return robust_sigma([d for _, d, pub in screen_oi(minutes) if not pub]) if minutes else None


def screen_oi(minutes: List[dict]) -> List[Tuple[int, float, bool]]:
    """THE BATCHED-OI SCREEN: (minute index, OI change, publication?) per OI update. An update whose |change|
    exceeds the volume traded since the previous update is a publication step, not that minute's trading."""
    out, last, since = [], None, 0.0
    for i, m in enumerate(minutes):
        if m.get("oi") is None:
            continue
        if last is None:
            last, since = m["oi"], 0.0
            continue
        since += m.get("vol") or 0.0
        d = m["oi"] - last
        if d:
            out.append((i, d, abs(d) > since))
            last, since = m["oi"], 0.0
    return out


# ---- the engine ------------------------------------------------------------------------------------------
class Engine:
    """Minutes in, one at a time (`step`). `run(minutes)` over any prefix equals the incremental state: every
    read is a function of data stamped at or before its as-of, and confirmed legs are frozen at confirmation."""

    def __init__(self, idx: str, day: str, lot: int, unit: Optional[float], expiry: Optional[str] = None,
                 gc: Optional[List[dict]] = None, gc_expected: bool = False, other_oi: Optional[Dict[int, float]] = None,
                 prior_sigma: Optional[float] = None, contract: str = "front", spread: Optional[float] = None):
        self.idx, self.day, self.lot, self.contract = idx, day, lot, contract
        unit, how = unit if isinstance(unit, tuple) else (unit, "median 1-min range (fold's unit)")
        self.unit, self.spread = unit, spread
        self.delta, self.ruler_note = self._ruler(unit, how, "prior", "frozen at the open")
        self.expiry = expiry
        self.expiring, self.sessions_left = roll_window(day, expiry)
        self.gc = sorted(gc or [], key=lambda b: b["t"])
        self.gc_expected = gc_expected or bool(gc)
        self.other_oi = dict(other_oi or {})
        self.prior_sigma = prior_sigma
        self.m: List[dict] = []
        self.buf: List[dict] = []
        self.legs: List[dict] = []
        self.events: List[dict] = []
        # cut state
        self.dir = 0
        self.p0 = self.i0 = None          # start pivot (price, minute index); i0 = -1 for the open
        self.ext = self.ext_i = None
        self.min_asof = 0                 # a ruler set late (no prior session) stamps the buffered legs at its own time
        self.hi = self.hi_i = self.lo = self.lo_i = None
        # auction state
        self.au = {"state": None, "d": 0, "ext": None, "ctr": None, "band": None, "lastH": None, "lastL": None}
        # OI screen state
        self.oi_last = None
        self.oi_since = 0.0
        self.oi_upd: List[Tuple[int, float, bool]] = []

    def _ruler(self, unit, how, whose, when):
        if not unit:
            return None, None
        d = TH["K"] * unit
        note = f"ruler {d:.1f} pts = {TH['K']:g} x {whose} unit {unit:.2f} [M] ({how})"
        if self.spread and TH["SPREAD_X"] * self.spread > d:
            d = TH["SPREAD_X"] * self.spread
            note = (f"ruler {d:.1f} pts = {TH['SPREAD_X']:g} x the median bid-ask spread {self.spread:.1f} [M], above "
                    f"{TH['K']:g} x {whose} unit {unit:.2f} ({how}): the thin book's prints bounce across its spread")
        return d, note + ", " + when

    def add_gc(self, bar: dict, arrived: int) -> None:
        """A GoCharting bar seen for the first time at `arrived` (ms): read only by legs confirmed at or after it."""
        if any(b["t"] == bar.get("t") for b in self.gc) or bar.get("t") is None:
            return
        self.gc.append({**bar, "arrived": arrived})
        self.gc.sort(key=lambda b: b["t"])
        self.gc_expected = True

    # ---- feeding ----
    def step(self, m: dict) -> List[dict]:
        n0 = len(self.events)
        if not in_session(m["t"]) or (self.m and m["t"] <= self.m[-1]["t"]) or m.get("c") is None:
            return []
        if self.delta is None:
            self.buf.append(m)
            if len(self.buf) < TH["SELF_N"]:
                return []
            self.unit, how = prior_unit([self.buf])
            if self.spread is None:
                self.spread = prior_spread([self.buf])
            self.delta, self.ruler_note = self._ruler(self.unit, how, f"today's first {int(TH['SELF_N'])} minutes'",
                                                      f"no prior session: not causal before {hm(m['t'] + 60000)}")
            if not self.delta:
                self.buf = self.buf[1:]      # still no range at all: keep waiting, one minute later
                return []
            self.min_asof = m["t"] + 60000
            self._event(self.min_asof, "ruler", self.ruler_note, "Ruler set · " + fmt(self.delta, 1, False) + " pts")
            buf, self.buf = self.buf, []
            for x in buf:
                self._one(x)
            return self.events[n0:]
        self._one(m)
        return self.events[n0:]

    def _one(self, m: dict) -> None:
        self.m.append(m)
        i = len(self.m) - 1
        asof = self.asof()
        self._oi(i, m)
        self._cut(i, m, asof)
        self._live(i, m, asof)

    def asof(self) -> int:
        return max((self.m[-1]["t"] + 60000) if self.m else 0, self.min_asof)

    def _event(self, t: int, kind: str, en: str, chip: str, **kw) -> dict:
        e = {"idx": self.idx, "t": t, "kind": kind, "en": en, "chip": chip, **kw}
        self.events.append(e)
        return e

    # ---- OI screen ----
    def _oi(self, i: int, m: dict) -> None:
        if m.get("oi") is None:
            return
        if self.oi_last is None:
            self.oi_last, self.oi_since = m["oi"], 0.0
            return
        self.oi_since += m.get("vol") or 0.0
        d = m["oi"] - self.oi_last
        if d:
            self.oi_upd.append((i, d, abs(d) > self.oi_since))
            self.oi_last, self.oi_since = m["oi"], 0.0

    def sigma(self) -> Tuple[Optional[float], str]:
        ok = [d for _, d, pub in self.oi_upd if not pub]
        if len(ok) >= TH["OI_SIGMA_N"]:
            return robust_sigma(ok), f"today's {len(ok)} screened OI updates"
        if self.prior_sigma:
            return self.prior_sigma, "the prior session's (today has too few OI updates yet)"
        return None, f"warming: {len(ok)} of {int(TH['OI_SIGMA_N'])} OI updates"

    # ---- the cut (1-minute closes) ----
    def _cut(self, i: int, m: dict, asof: int) -> None:
        dl = self.delta
        if self.dir == 0:
            if self.p0 is None:
                self.p0, self.i0 = m["o"], -1
                self.hi, self.hi_i, self.lo, self.lo_i = m["h"], i, m["l"], i
            else:
                if m["h"] > self.hi:
                    self.hi, self.hi_i = m["h"], i
                if m["l"] < self.lo:
                    self.lo, self.lo_i = m["l"], i
            # the order of high, low and close inside one minute is unknown except that the close is last:
            # a reversal is confirmed only by the close of a LATER minute than the extreme it reverses
            down = i > self.hi_i and m["c"] <= self.hi - dl
            up = i > self.lo_i and m["c"] >= self.lo + dl
            if down and up:                       # a range wider than 2 deltas in the opening: the later extreme wins
                down = self.hi_i >= self.lo_i
                up = not down
            if down:
                if self.hi - self.p0 >= dl:
                    self._confirm(1, self.p0, self.i0, self.hi, self.hi_i, asof)
                self._start(-1, self.hi, self.hi_i, i, m)
            elif up:
                if self.p0 - self.lo >= dl:
                    self._confirm(-1, self.p0, self.i0, self.lo, self.lo_i, asof)
                self._start(1, self.lo, self.lo_i, i, m)
            return
        if self.dir > 0:
            if m["h"] > self.ext:
                self.ext, self.ext_i = m["h"], i
            if i > self.ext_i and m["c"] <= self.ext - dl:
                p0, i0, ext, ext_i = self.p0, self.i0, self.ext, self.ext_i
                self._confirm(1, p0, i0, ext, ext_i, asof)
                self._start(-1, ext, ext_i, i, m)
        else:
            if m["l"] < self.ext:
                self.ext, self.ext_i = m["l"], i
            if i > self.ext_i and m["c"] >= self.ext + dl:
                p0, i0, ext, ext_i = self.p0, self.i0, self.ext, self.ext_i
                self._confirm(-1, p0, i0, ext, ext_i, asof)
                self._start(1, ext, ext_i, i, m)

    def _start(self, d: int, p0: float, i0: int, i: int, m: dict) -> None:
        """A new leg from pivot (p0, i0). Its running extreme uses only minutes strictly after i0 (the order of
        high and low inside the pivot minute is unknown); if i0 is this minute, the close stands in."""
        self.dir, self.p0, self.i0 = d, p0, i0
        after = self.m[i0 + 1:i + 1]
        if after:
            k = (min if d < 0 else max)(range(len(after)), key=lambda j: after[j]["l"] if d < 0 else after[j]["h"])
            self.ext, self.ext_i = (after[k]["l"] if d < 0 else after[k]["h"]), i0 + 1 + k
        else:
            self.ext, self.ext_i = m["c"], i

    # ---- a leg is confirmed: measure it as of now, freeze it ----
    def _confirm(self, d: int, p0: float, i0: int, p1: float, i1: int, asof: int) -> None:
        leg = self.measure(d, p0, i0, p1, i1, asof)
        leg.update(id=f"{self.idx}:{self.day}:L{len(self.legs) + 1:02d}", n=len(self.legs) + 1,
                   state="confirmed", confirmed_at=asof)
        self._rank(leg)
        self._who(leg)
        self._text(leg)
        leg["x"] = cross(leg)
        self.legs.append(leg)
        self._event(asof, "leg", leg["en"], leg["chip"], leg=leg["id"])
        self._pivot(leg, asof)

    # ---- measurement (shared by confirmed and forming legs) ----
    def measure(self, d: int, p0: float, i0: int, p1: float, i1: int, asof: int) -> dict:
        mins = self.m[i0 + 1:i1 + 1]
        t0 = self.m[i0]["t"] if i0 >= 0 else self.m[0]["t"]
        t1 = self.m[i1]["t"]
        pts = p1 - p0
        vol = sum(x["vol"] or 0 for x in mins)
        holes = []
        prev_t = t0 if i0 >= 0 else None
        for x in mins:
            if prev_t is not None and x["t"] - prev_t > 60000:
                holes.append((hm(prev_t + 60000), hm(x["t"] - 60000)))
            prev_t = x["t"]
        excl: List[dict] = []
        if not mins:                      # a reversal of >= delta inside the pivot minute: no minute of its own
            why = "the whole leg sits inside one minute shared with the previous leg"
            ux = {"state": "cant", "why": why}
            gc = {"state": "cant", "why": why} if self.gc_expected else {"state": "none", "why": "no GoCharting for this index"}
            oi = {"state": "cant", "why": why}
        else:
            ux = self._ux(mins, asof, excl)
            gc = self._gc(i0, i1, asof, excl)
            oi = self._oi_leg(i0, i1)
        return {"idx": self.idx, "day": self.day, "contract": self.contract,
                "expiring": self.expiring, "t0": t0, "t1": t1, "dir": d, "px0": p0, "px1": p1,
                "pts": round(pts, 2), "mins": len(mins), "vol": round(vol, 1),
                "ami": round(abs(pts) / vol * 1000, 1) if vol else None, "src": sorted({x["src"] for x in mins}),
                "holes": holes, "ux": ux, "gc": gc, "oi": oi, "excluded": excl, "zero": not mins, "from_open": i0 < 0}

    def _med_ux(self) -> Optional[float]:
        n = sum(x["nx"] for x in self.m)
        return sum(x["lx"] for x in self.m) / n if n else None

    def _bin_bvol(self, t: int) -> float:
        b = t // GC_BAR_MS * GC_BAR_MS
        return sum(x["bvol"] or 0 for x in self.m if b <= x["t"] < b + GC_BAR_MS)

    def _spread(self, t_from: int, t_to: int, lots: float) -> Tuple[Optional[bool], str]:
        """A print's spread/roll witnesses: missing from the exchange candle, or mirrored in the other month's
        OI within SPREAD_MIN minutes. (None, why) when neither witness is available."""
        need = TH["SPREAD_WIT"] * lots
        ms = [x for x in self.m if t_from <= x["t"] <= t_to]
        seen = []
        if ms and all(x["cvol"] is not None and x["bvol"] is not None for x in ms):
            gap = sum(x["bvol"] - x["cvol"] for x in ms)
            if gap >= need:
                return True, f"{fmt(gap, 0, False)} lots of it are not in the exchange candle [M]"
            seen.append("in the exchange candle")
        if self.other_oi:
            a, b = t_from - 60000, t_to + int(TH["SPREAD_MIN"]) * 60000
            if b + 60000 <= self.asof():
                ka = max((t for t in self.other_oi if t <= a), default=None)
                kb = max((t for t in self.other_oi if t <= b), default=None)
                sig = self._other_sigma()
                if ka is not None and kb is not None and sig is not None:
                    step = self.other_oi[kb] - self.other_oi[ka]
                    n = max(1, sum(1 for t in self.other_oi if ka < t <= kb))
                    if abs(step) >= max(need, TH["OI_Z"] * sig * math.sqrt(n)):
                        return True, f"the other month's OI stepped {fmt(step)} lots [M] with it"
                    seen.append("no mirror in the other month's OI")
        if not seen:
            return None, "spread witness CAN'T CHECK: no exchange candle and no other-month OI"
        return False, "; ".join(seen)

    def _other_sigma(self) -> Optional[float]:
        """Robust sigma of the other month's minute OI changes as of now: a mirror must beat that month's own
        churn (on a roll day its OI moves hundreds of lots a minute)."""
        ks = sorted(t for t in self.other_oi if t + 60000 <= self.asof())
        ch = [self.other_oi[b] - self.other_oi[a] for a, b in zip(ks, ks[1:]) if self.other_oi[b] != self.other_oi[a]]
        return robust_sigma(ch) if len(ch) >= TH["OI_SIGMA_N"] else None

    def _ux(self, mins: List[dict], asof: int, excl: List[dict]) -> dict:
        tot = sum(x["vol"] or 0 for x in mins)
        have = [x for x in mins if x["bk"]]
        cover = (sum(x["vol"] or 0 for x in have) / tot) if tot else 0.0
        if not have or cover < TH["UX_COVER"]:
            gaps = [hm(x["t"]) for x in mins if not x["bk"]]
            why = "no Upstox book for " + (f"{gaps[0]}–{gaps[-1]}" if gaps else "this leg")
            return {"state": "cant", "why": why}
        d = sum(x["buy"] - x["sell"] for x in have)
        bvol = sum(x["bvol"] for x in have)
        nf = sum(x.get("nf") or 0 for x in have)
        if nf < TH["MIN_PRINTS"]:
            return {"state": "thin", "d": round(d, 1), "vol": round(bvol, 1), "prints": nf,
                    "why": f"too thin to name a side: {nf} traded frames in the leg (< {int(TH['MIN_PRINTS'])})"}
        med = self._med_ux()
        if med:
            for x in have:
                for p in x["prints"]:
                    if p["lots"] < TH["BLOCK_X"] * med or p["lots"] < TH["BLOCK_BAR"] * self._bin_bvol(x["t"]):
                        continue
                    sp, why = self._spread(x["t"], x["t"], p["lots"])
                    if sp:
                        kind = "spread print"
                    elif p["exact"]:
                        kind = "block"
                    else:
                        continue                 # a burst (V != ltq): not one print, stays in delta
                    d -= p["side"] * p["lots"]
                    excl.append({"tape": "UX", "t": p["t"], "kind": kind, "lots": round(p["lots"]), "p": p["p"],
                                 "side": p["side"], "why": why})
        miss = [hm(x["t"]) for x in mins if not x["bk"]]
        share = d / bvol if bvol else 0.0
        return {"state": "ok", "d": round(d, 1), "vol": round(bvol, 1), "share": round(share, 3), "prints": nf,
                "partial": (f"{miss[0]}–{miss[-1]} not recorded" if miss else None)}

    def _gc(self, i0: int, i1: int, asof: int, excl: List[dict]) -> dict:
        if not self.gc_expected:
            return {"state": "none", "why": "no GoCharting for this index"}
        lo = self.m[i0 + 1]["t"] if i0 + 1 < len(self.m) else None
        hi = self.m[i1]["t"] + 60000
        if lo is None:
            return {"state": "short_leg", "why": "leg shorter than two GoCharting bars"}
        first = -(-lo // GC_BAR_MS) * GC_BAR_MS
        slots = list(range(first, hi - GC_BAR_MS + 1, GC_BAR_MS))
        if len(slots) < TH["GC_MIN_BARS"]:
            return {"state": "short_leg", "why": "leg shorter than two GoCharting bars"}
        have = {b["t"]: b for b in self.gc if b.get("arrived", 0) <= asof}
        miss = [hm(s) for s in slots if s not in have]
        if miss:
            return {"state": "cant", "why": f"GoCharting bar {miss[0]} not received as of {hm(asof)}"}
        bars = [have[s] for s in slots]
        for b in bars:
            bv = self._bin_bvol(b["t"])
            if bv and b["vol"] < TH["GC_SHORT"] * bv and bv - b["vol"] > TH["GC_SHORT_LOTS"]:
                return {"state": "cant", "why": f"GoCharting bar {hm(b['t'])} short ({fmt(b['vol'], 0, False)} of "
                                                f"{fmt(bv, 0, False)} lots)"}
        lots = trades = 0.0
        for b in have.values():
            for z in b.get("ladder") or []:
                n = (z.get("bt") or 0) + (z.get("st") or 0)
                if n:
                    lots += z["b"] + z["s"]
                    trades += n
        med = lots / trades if trades else None
        d = sum(b["delta"] for b in bars)
        vol = sum(b["vol"] for b in bars)
        for b in bars:
            for z in b.get("ladder") or []:
                n = (z.get("bt") or 0) + (z.get("st") or 0)
                v = z["b"] + z["s"]
                if not (n and med) or v / n < TH["BLOCK_X"] * med or v < TH["BLOCK_BAR"] * b["vol"]:
                    continue
                sp, why = self._spread(b["t"], b["t"] + GC_BAR_MS - 60000, v)
                d -= z["b"] - z["s"]
                excl.append({"tape": "GC", "t": b["t"], "kind": "spread print" if sp else "block",
                             "lots": round(v), "p": z["p"], "side": sgn(z["b"] - z["s"]), "why": why})
        return {"state": "ok", "d": round(d, 1), "vol": round(vol, 1), "share": round(d / vol, 3) if vol else 0.0,
                "bars": len(bars)}

    def _oi_leg(self, i0: int, i1: int) -> dict:
        """The leg's OI change with a ONE-UPDATE TOLERANCE at each end, against 3 sigma sqrt(updates)."""
        s0 = max(i0, 0)
        oi, last = [], None
        for x in self.m:                  # forward-filled: a minute with no OI print keeps the last one
            last = x.get("oi") if x.get("oi") is not None else last
            oi.append(last)
        if oi[s0] is None or oi[i1] is None:
            return {"state": "cant", "why": "no OI at the leg's ends"}
        upd = [(j, dv, pub) for j, dv, pub in self.oi_upd if s0 < j <= len(self.m) - 1]

        def after(j):             # the OI value after the first update following minute j
            nx = next((u for u in self.oi_upd if u[0] > j), None)
            return oi[nx[0]] if nx is not None else None

        starts = [oi[s0]] + ([after(s0)] if after(s0) is not None else [])
        ends = [oi[i1]] + ([after(i1)] if after(i1) is not None else [])
        rng = [e - s for s in starts for e in ends]
        nominal = oi[i1] - oi[s0]
        n = max(1, sum(1 for j, _, _ in upd if j <= i1))
        sig, sig_src = self.sigma()
        out = {"d": round(nominal), "lo": round(min(rng)), "hi": round(max(rng)), "updates": n}
        if sig is None:
            return {**out, "state": "cant", "why": f"OI noise floor {sig_src}"}
        floor = TH["OI_Z"] * sig * math.sqrt(n)
        moved = 1 if min(rng) >= floor else -1 if max(rng) <= -floor else 0
        out.update(floor=round(floor), sigma_src=sig_src)
        pubs = [(j, dv) for j, dv, pub in upd if pub and j <= i1]
        if moved and pubs:
            j, dv = max(pubs, key=lambda u: abs(u[1]))
            if abs(dv) >= TH["PUB_SHARE"] * abs(nominal):
                return {**out, "state": "pub", "why": f"one OI publication step at {hm(self.m[j]['t'])} "
                                                      f"({fmt(dv)} lots, larger than the volume since the last update): "
                                                      "not read as positioning"}
        return {**out, "state": "ok", "moved": moved}

    # ---- efficiency and rank (today only) ----
    def _lam(self, leg: dict, tape: str) -> Optional[float]:
        x = leg[tape]
        if x.get("state") != "ok" or abs(x["share"]) < TH["SHARE"] or sgn(x["d"]) != leg["dir"] or not x["d"]:
            return None
        return abs(leg["pts"]) / abs(x["d"]) * 1000

    def _rank(self, leg: dict) -> None:
        for tape in ("ux", "gc"):
            x = leg[tape]
            lam = self._lam(leg, tape)
            if lam is None:
                continue
            prior = [p[tape]["lam"] for p in self.legs if p[tape].get("lam") is not None]
            same = [p[tape]["lam"] for p in self.legs if p[tape].get("lam") is not None and p["dir"] == leg["dir"]]
            x["lam"] = round(lam, 1)
            if len(prior) >= TH["WARM_N"]:
                k, n = 1 + sum(1 for p in prior if p < lam), len(prior) + 1
                x["rank"] = [k, n]
                low = k / n <= TH["LOW"]
                x["easy"] = k / n > 1 - TH["LOW"]
            else:
                x["rank"] = None
                x["warming"] = f"{len(prior)} of {int(TH['WARM_N'])}"
                low = False
                x["easy"] = False
            if same:
                x["vs_last_same"] = same[-1]
                low = low or lam <= TH["PAIR"] * same[-1]
            x["low"] = low

    # ---- WHO ----
    def _who(self, leg: dict) -> None:
        d = leg["dir"]
        tapes = {t: leg[t] for t in ("ux", "gc") if leg[t].get("state") == "ok"}
        sh = {t: x["share"] for t, x in tapes.items()}
        split = any(a >= TH["THIN"] and b <= -TH["THIN"] for a in sh.values() for b in sh.values())
        named = {t: sgn(s) for t, s in sh.items() if abs(s) >= TH["SHARE"]}
        agg = 0 if split or not named else next(iter(named.values()))
        if len(tapes) == 2:
            agree = "SPLIT" if split else "AGREE" if len(named) == 2 else "DIFFER" if named else "BOTH THIN"
        elif len(tapes) == 1:
            agree = "ONE"
        else:
            agree = "NONE"
        oi = leg["oi"]
        moved = oi.get("moved") if oi.get("state") == "ok" else None
        lams = [leg[t] for t in tapes if leg[t].get("lam") is not None]
        low = bool(lams) and all(x.get("low") for x in lams)
        size = abs(leg["pts"]) / self.delta if self.delta else 0.0          # the leg in rulers
        against = bool(agg) and agg == -d                                    # sign, not size: stays ABSORBED at any size
        absorbed = against or (bool(agg) and low and size < TH["ABSORB_MAX_R"])
        paid = bool(agg) and agg == d and low and size >= TH["PAID_R"]
        if moved is None:
            cls = "oi_cant"
        elif moved > 0:
            cls = "new_longs" if d > 0 else "new_shorts"
        elif moved < 0:
            cls = "short_covering" if d > 0 else "long_liquidation"
        else:
            cls = "rotation"
        anythin = any(leg[t].get("state") == "thin" for t in ("ux", "gc"))
        leg["who"] = {"class": cls, "aggressor": agg, "tapes": agree, "absorbed": absorbed, "paid": paid,
                      "rulers": round(size, 1),
                      "thin": not split and not named and (bool(tapes) or anythin), "split": split,
                      "roll": self.expiring and moved is not None and moved < 0, "expiring": self.expiring}

    # ---- sentences ----
    WORDS = {"new_longs": ("new longs", "Naye long"), "new_shorts": ("new shorts", "Naye short"),
             "short_covering": ("short covering", "Short cover"), "long_liquidation": ("long liquidation", "Long nikal rahe"),
             "rotation": ("rotation, OI flat", "Sirf ghumaav · OI flat"), "oi_cant": ("OI can't check", "OI check nahi")}

    def _text(self, leg: dict) -> None:
        d, w = leg["dir"], leg["who"]
        arrow, word = ("▲", "Upar") if d > 0 else ("▼", "Neeche")
        span = f"{hm(leg['t0'])}→{hm(leg['t1'])}"
        parts = [f"{arrow} {span} · {fmt(leg['pts'], 1)} pts [M] · {leg['mins']} min"]
        chip = [f"{word} {fmt(leg['pts'], 0)}"]
        for t, name in (("ux", "UX"), ("gc", "GC")):
            x = leg[t]
            if x.get("state") == "ok":
                s = f"{name} Δ{fmt(x['d'])} [I] ({fmt(100 * x['share'], 0)}%)"
                if x.get("lam") is not None:
                    s += f", {x['lam']:.0f} pts/1k [I] · {rank_words(x)}"
                if x.get("partial"):
                    s += f" ({x['partial']})"
                parts.append(s)
            elif x.get("state") == "thin":
                parts.append(f"{name} Δ{fmt(x['d'])} [I]: {x['why']}")
            elif x.get("state") != "none":
                parts.append(f"{name} CAN'T CHECK: {x.get('why')}")
        if w["tapes"] in ("AGREE", "DIFFER", "SPLIT", "BOTH THIN"):
            parts.append(f"tapes {w['tapes']}")
        oi = leg["oi"]
        if oi.get("state") == "ok":
            parts.append(f"OI {fmt(oi['d'])} lots [M] ({'moved' if oi['moved'] else 'within noise'} "
                         f"±{oi['floor']:,}, tol {fmt(oi['lo'])}..{fmt(oi['hi'])})")
        else:
            parts.append(f"OI {fmt(oi.get('d'))} lots [M]: {oi.get('why')}")
        en_w, hi_w = self.WORDS[w["class"]]
        if w["class"] == "oi_cant":
            en_w = {1: "buyers pressing", -1: "sellers pressing"}.get(w["aggressor"], "no named aggressor")
            hi_w = {1: "Kharid dabav", -1: "Bikri dabav"}.get(w["aggressor"], "Koi pakka taraf nahi")
        if w["roll"]:
            en_w += " (expiring: or roll)"
            hi_w += " (ya roll)"
        if w["absorbed"]:
            en_w += ", ABSORBED" + (" (price moved against the aggressor)" if w["aggressor"] == -d else
                                    " (heavy effort, little progress)")
            hi_w += " · " + ("kharid dabi" if w["aggressor"] > 0 else "bikri dabi")
        if w.get("paid"):
            en_w += " · heavy effort, move paid"
            hi_w += " · zor laga, move mila"
        if w["split"]:
            en_w += " (tapes split: no aggressor named)"
            hi_w += " · tape ulte"
        elif w["thin"] and w["class"] not in ("oi_cant",):
            en_w += " (delta thin: price × OI only)"
            hi_w += " · Δ patla"
        w["en"], w["chip"] = en_w, hi_w
        parts.append("WHO: " + en_w + (" [I]" if w["class"] != "oi_cant" else ""))
        for e in leg["excluded"]:
            parts.append(f"{e['tape']} {e['kind']} {e['lots']:,} lots @{e['p']} excluded ({e['why']})")
        if leg["holes"]:
            parts.append("price hole " + ", ".join(f"{a}–{b}" for a, b in leg["holes"]))
        ux = leg["ux"]
        if ux.get("state") == "ok":
            chip.append(f"Δ{fmt(ux['d'] / 1000, 1)}k UX")
        if oi.get("state") in ("ok", "pub"):
            chip.append(f"OI {fmt(oi['d'] / 1000, 1)}k")
        chip.append(hi_w)
        if self.expiring:
            chip.append("expiring")
        leg["en"] = " · ".join(parts)
        leg["chip"] = " · ".join(chip)

    # ---- the auction: pivots on confirmation, invalidations live on price ----
    def _pivot(self, leg: dict, asof: int) -> None:
        A, dl = self.au, self.delta
        piv, side = leg["px1"], ("H" if leg["dir"] > 0 else "L")
        A["last" + side] = piv
        if A["state"] is None:
            A.update(state="TREND", d=leg["dir"], ext=piv, ctr=None)
            self._au_event(asof, "TREND " + ("UP" if leg["dir"] > 0 else "DOWN"), "first confirmed leg")
            return
        if A["state"] == "TREND":
            tside = "H" if A["d"] > 0 else "L"
            if side == tside:
                ext = A["ext"]
                if ext is None or (piv >= ext + TH["EDGE"] * dl if A["d"] > 0 else piv <= ext - TH["EDGE"] * dl):
                    A["ext"] = piv
                else:
                    other = A["ctr"] if A["ctr"] is not None else piv
                    A.update(state="RANGE", band=[min(ext, other), max(ext, other)])
                    self._au_event(asof, f"RANGE {A['band'][0]:.1f}–{A['band'][1]:.1f}",
                                   f"the {'high' if side == 'H' else 'low'} {piv:.1f} did not extend past {ext:.1f} by δ/2")
            else:
                A["ctr"] = piv
            return
        lo, hi = A["band"]
        if lo - TH["EDGE"] * dl <= piv < lo or hi < piv <= hi + TH["EDGE"] * dl:
            A["band"] = [min(lo, piv), max(hi, piv)]
            self._au_event(asof, f"RANGE {A['band'][0]:.1f}–{A['band'][1]:.1f}", f"edge widened to {piv:.1f} (within δ/2)")
        elif piv < lo or piv > hi:
            self._event(asof, "poke", f"pivot {piv:.1f} outside the range {lo:.1f}–{hi:.1f}, not past it by δ",
                        f"Range ke bahar jhanka {piv:.0f}")

    def _live(self, i: int, m: dict, asof: int) -> None:
        A, dl = self.au, self.delta
        if A["state"] == "RANGE":
            lo, hi = A["band"]
            if m["h"] >= hi + TH["BREAK"] * dl:
                A.update(state="TREND", d=1, ext=None, ctr=A["lastL"])
                self._au_event(asof, "BREAKOUT UP", f"traded {m['h']:.1f}, past {hi:.1f} + δ", chip=f"Range toota ▲ {hi + dl:.0f}")
            elif m["l"] <= lo - TH["BREAK"] * dl:
                A.update(state="TREND", d=-1, ext=None, ctr=A["lastH"])
                self._au_event(asof, "BREAKOUT DOWN", f"traded {m['l']:.1f}, past {lo:.1f} − δ", chip=f"Range toota ▼ {lo - dl:.0f}")
        elif A["state"] == "TREND" and A["ctr"] is not None:
            if A["d"] > 0 and m["l"] < A["ctr"]:
                c, e = A["ctr"], A["ext"]
                A.update(d=-1, ext=None, ctr=e)
                self._au_event(asof, "TREND DOWN", f"traded {m['l']:.1f}, below the last higher low {c:.1f}",
                               chip=f"Trend toota ↓ {c:.0f}")
            elif A["d"] < 0 and m["h"] > A["ctr"]:
                c, e = A["ctr"], A["ext"]
                A.update(d=1, ext=None, ctr=e)
                self._au_event(asof, "TREND UP", f"traded {m['h']:.1f}, above the last lower high {c:.1f}",
                               chip=f"Trend toota ↑ {c:.0f}")

    def _au_event(self, asof: int, state: str, why: str, chip: Optional[str] = None) -> None:
        hi = {"TREND UP": "Upar chal raha", "TREND DOWN": "Neeche chal raha"}.get(state)
        if chip is None:
            chip = hi or ("Range " + state.split(" ", 1)[1] if state.startswith("RANGE") else state)
        self._event(asof, "auction", f"{state}: {why}", chip, state=state)

    # ---- views ----
    def forming(self) -> Optional[dict]:
        """The leg since the last pivot, measured now. Never frozen, never ranked into the record."""
        if not self.m or self.dir == 0 or self.delta is None:
            return None
        leg = self.measure(self.dir, self.p0, self.i0, self.ext, self.ext_i, self.asof())
        leg.update(id=f"{self.idx}:{self.day}:forming", state="forming", now=self.m[-1]["c"],
                   back=round(abs(self.m[-1]["c"] - self.ext), 1))
        self._rank(leg)
        self._who(leg)
        self._text(leg)
        leg["x"] = cross(leg)
        leg["en"] = "forming " + leg["en"] + f" · now {self.m[-1]['c']:.1f}, {leg['back']:.1f} back of δ {self.delta:.1f}"
        return leg

    def auction_state(self) -> dict:
        return dict(self.au)


def rank_words(x: dict) -> str:
    """The rank with its direction said: 1 = the least points per lot of today's legs."""
    r = x.get("rank")
    if not r:
        return f"rank warming {x.get('warming')}"
    k, n = r
    if k == 1:
        return f"least progress per lot, 1 of {n}"
    if k == n:
        return f"most progress per lot, {n} of {n}"
    return f"progress per lot {k} of {n} (1 = least)"


def cross(leg: dict) -> dict:
    """The flat row a cross-index layer aligns on, without recomputing anything."""
    g = lambda t, k: leg[t].get(k) if leg[t].get("state") in ("ok", "thin") else None   # noqa: E731
    return {"idx": leg["idx"], "t0": leg["t0"], "t1": leg["t1"], "dir": leg["dir"], "px0": leg["px0"],
            "px1": leg["px1"], "pts": leg["pts"], "d_ux": g("ux", "d"), "d_gc": g("gc", "d"),
            "doi": leg["oi"].get("d"), "oi_state": leg["oi"].get("state"), "who": leg["who"]["class"],
            "absorbed": leg["who"]["absorbed"], "paid": leg["who"].get("paid"), "rulers": leg["who"].get("rulers"),
            "thin": leg["who"]["thin"], "expiring": leg["expiring"],
            "rank_ux": leg["ux"].get("rank"), "rank_gc": leg["gc"].get("rank"), "state": leg.get("state")}


def run(minutes: List[dict], **kw) -> Engine:
    """The pure form: an engine fed `minutes` in order. `run(minutes[:k])` IS the live state after k minutes."""
    eng = Engine(**kw)
    for m in minutes:
        eng.step(m)
    return eng


def story(eng: Engine) -> List[str]:
    """The day story: the ruler, the contract, every event in order (legs and auction), the forming leg."""
    out = [f"{eng.idx} {eng.day} · reader {REV} · SHADOW (unsigned thresholds)"]
    out.append(eng.ruler_note or "ruler not set yet")
    if eng.expiry:
        out.append(f"front contract expiry {eng.expiry} [M, instrument master] · {eng.sessions_left} session(s) left"
                   + (" · EXPIRING: inside its roll window; OI-down classes read 'or roll'" if eng.expiring else ""))
    for e in eng.events:
        out.append(f"{hm(e['t'])}  {e['en']}")
        out.append(f"        {e['chip']}")
    f = eng.forming()
    if f:
        out.append(f"{hm(eng.asof())}  {f['en']}")
        out.append(f"        {f['chip']}")
    return out
