"""vpin.py -- order-flow toxicity on the future's tape, SHADOW only.

WHAT IT ANSWERS. Not "who is winning" -- delta/CVD already says that -- but
"how badly are the books being adversely selected": is the volume arriving
two-sided (makers earning spread, comfortable) or one-sided (makers bleeding,
about to widen or pull)? Easley/Lopez de Prado/O'Hara's VPIN, computed in
VOLUME time: fixed-size volume buckets, |buy - sell| / V per bucket, mean of
the last N buckets. Direction-blind by construction -- the absolute value
throws the sign away -- so this is an expansion-risk gauge, never an entry.

METHOD, from what the feed actually gives. Frames arrive at snapshot cadence,
not per trade, so per-trade Lee-Ready is unavailable. Volume between frames is
`vtt` delta; its sign is the TICK RULE on ltp across the same pair of frames:
up -> buy, down -> sell, flat -> carry the last known sign. A frame that
aggregates several trades gets one sign for all of them -- that is the known
ceiling of snapshot-cadence classification, and it is the same compromise
every bar-data VPIN (BVC) makes, just at 0.5s frames instead of 1m bars.
Volume with NO sign yet (session start, before the first price change) is
split half/half: contributes volume, contributes zero imbalance, which is the
honest neutral rather than an invented direction.

`vtt` going BACKWARDS is a feed reset, not negative trading. The baseline
re-arms and that gap contributes nothing -- same refusal to invent volume that
`sweep.py` applies to its deltas.

READ THE PERCENTILE, NOT THE NUMBER. Raw VPIN is not comparable across days
or instruments (the Andersen-Bondarenko critique is exactly that the raw
value's alarm level is parameter- and regime-relative), so readings report
percentile-so-far against THIS session, the same `Rank` discipline `fuse.py`
and `engine.Rank` apply everywhere else. A cross-day reference was tried and
rejected the same evening it was built (2026-08-25) -- expiry character and
the vol regime reshape the distribution daily, so yesterday's buckets
mislead today's rank; see `Gauge.seed` for the full account. The percentile
is therefore mute until MIN_HIST buckets every morning, and that muteness is
honest.

THE [I] LAYER. V = 60_000 is ADV/50 with ADV the MEDIAN of the last 30 cached
sessions (data/backtest/fut_*.json through 2026-08-24: median 2,936,408
units), measured 2026-08-25. The first cut was 100_000, taken from the single
session 2026-07-17 -- which the same sweep then showed to be one of the
heaviest days in the cache, so on a normal day the 10th bucket (the first
trusted percentile, MIN_HIST) arrived at lunch and on a quiet one near the
close. At 60_000 the median day completes ~49 buckets -- the 1/50 the design
intends -- and the 10th lands around 09:56. N = 50 is the literature default.
Both untested forward, hence [I] and SHADOW:
nothing reads this gauge downstream -- no fuse, no regime, no desk. The
forward log (server.py writes data/vpin_log.jsonl, one row per completed
bucket) is the only path to promotion, and the kill condition is stated up
front: over 30 sessions, pct >= 0.90 must precede a range expansion at better
than base rate, or this module dies. No backtest -- VPIN's known
regime-dependence is exactly why only the forward tape counts.

Pure computation, stdlib only, no I/O -- the detector isolation `sweep.py` /
`fuse.py` established. The caller owns fetching and logging.
"""

from __future__ import annotations

from bisect import bisect_right, insort
from collections import deque
from typing import Dict, List, Optional

# --- the [I] layer ---------------------------------------------------------
BUCKET_V = 60_000    # units per bucket: median-of-30-sessions ADV/50 (docstring)
WINDOW = 50          # buckets a VPIN reading averages over (literature default)
MIN_HIST = 10        # percentiles on fewer completed buckets are not trusted


class Rank:
    """Percentile-so-far of a stream. Mirrors `fuse.Rank` / `engine.Rank`;
    copied, not imported, for the same reason fuse states: this group replays
    without the engine."""

    def __init__(self):
        self._seen: List[float] = []

    def rank(self, x: float) -> float:
        r = (bisect_right(self._seen, x) / len(self._seen)) if self._seen else 0.5
        insort(self._seen, x)
        return r

    def __len__(self):
        return len(self._seen)


class Gauge:
    """One instrument's VPIN, fed frame pairs, emitting completed buckets.

    `on_frame` returns the completed-bucket event(s) -- usually [], sometimes
    one, more only if a single delta spans several buckets. Nothing is
    returned that the caller should not log, and `state()` never invents a
    reading it does not have (no completed bucket -> vpin is None, not 0).
    """

    def __init__(self, bucket_v: int = BUCKET_V, window: int = WINDOW):
        self.bucket_v = bucket_v
        self.window = window
        self._ltp: Optional[float] = None
        self._vtt: Optional[float] = None
        self._sign = 0                 # +1 buy, -1 sell, 0 unknown yet
        self._buy = 0.0                # current bucket's halves
        self._sell = 0.0
        self._imb: deque = deque(maxlen=window)   # |buy-sell|/V per bucket
        self._rank = Rank()
        self.buckets = 0               # completed, lifetime
        self.resets = 0                # vtt went backwards
        self.last: Optional[Dict] = None          # last completed event

    # -- feeding ------------------------------------------------------------

    def on_frame(self, ltp: Optional[float], vtt: Optional[float],
                 stamp: str = "") -> List[Dict]:
        if ltp is not None and self._ltp is not None:
            if ltp > self._ltp:
                self._sign = 1
            elif ltp < self._ltp:
                self._sign = -1
        if ltp is not None:
            self._ltp = ltp
        if vtt is None:
            return []
        if self._vtt is None or vtt < self._vtt:   # first frame, or feed reset
            if self._vtt is not None:
                self.resets += 1
            self._vtt = vtt
            return []
        dv, self._vtt = vtt - self._vtt, vtt
        if dv <= 0:
            return []
        out: List[Dict] = []
        while dv > 0:
            room = self.bucket_v - (self._buy + self._sell)
            take = min(dv, room)
            if self._sign > 0:
                self._buy += take
            elif self._sign < 0:
                self._sell += take
            else:                       # no sign yet: honest neutral
                self._buy += take / 2.0
                self._sell += take / 2.0
            dv -= take
            if self._buy + self._sell >= self.bucket_v:
                out.append(self._close(stamp))
        return out

    def _close(self, stamp: str) -> Dict:
        imb = abs(self._buy - self._sell) / self.bucket_v
        self._imb.append(imb)
        self.buckets += 1
        vpin = sum(self._imb) / len(self._imb)
        pct = self._rank.rank(vpin)
        ev = {"at": stamp, "bucket": self.buckets,
              "buy": round(self._buy, 1), "sell": round(self._sell, 1),
              "imb": round(imb, 4), "vpin": round(vpin, 4),
              "pct": round(pct, 3) if len(self._rank) >= MIN_HIST else None,
              "tag": "[I]", "shadow": True}
        self._buy = self._sell = 0.0
        self.last = ev
        return ev

    # -- seeding ------------------------------------------------------------

    def seed(self, rows: List[Dict], today: str) -> Dict:
        """Replay TODAY's completed-bucket rows from the forward log, at
        startup, so a mid-session restart resumes the gauge -- imb window,
        bucket count, rank -- instead of going blind for MIN_HIST buckets
        (2026-08-25 12:36 restart: blind until 13:2x, which sat the gauge
        out for the first half of the 14:39 burst's build-up).

        PRIOR sessions are DELIBERATELY IGNORED. A cross-day rank reference
        was built on the evening of 2026-08-25 and rejected by the operator
        the same day, correctly: expiry character and the vol regime change
        the imbalance distribution day to day (that day WAS an expiry, with
        one-second imb-1.0 buckets -- as a reference it would mark every
        normal morning "quiet" forever). That is the Andersen-Bondarenko
        critique this module's own header cites; it applies to us too. The
        percentile stays percentile-of-THIS-session, mute until MIN_HIST
        buckets, and the mute morning is the honest price until a
        regime-matched reference earns its way in forward.

        Pure: the caller reads the log file and passes rows in file order.
        """
        for r in rows:
            if r.get("day") == today and isinstance(r.get("imb"), (int, float)):
                self._imb.append(r["imb"])
                self.buckets += 1
                vpin = sum(self._imb) / len(self._imb)
                pct = self._rank.rank(vpin)
                self.last = {"at": r.get("at", ""), "bucket": self.buckets,
                             "buy": r.get("buy"), "sell": r.get("sell"),
                             "imb": round(r["imb"], 4), "vpin": round(vpin, 4),
                             "pct": (round(pct, 3)
                                     if len(self._rank) >= MIN_HIST else None),
                             "tag": "[I]", "shadow": True}
        return {"today_buckets": self.buckets}

    # -- reading ------------------------------------------------------------

    def state(self) -> Dict:
        fill = (self._buy + self._sell) / self.bucket_v
        return {"vpin": (self.last or {}).get("vpin"),
                "pct": (self.last or {}).get("pct"),
                "buckets": self.buckets, "fill": round(fill, 3),
                "resets": self.resets, "bucket_v": self.bucket_v,
                "window": self.window, "tag": "[I]", "shadow": True}


# --- the morning nobody watched -------------------------------------------

BACKFILL_SRC = "bars_1m_bvc"


def from_bars(bars, bucket_v: int = BUCKET_V,
              window: int = WINDOW) -> List[Dict]:
    """Buckets RECONSTRUCTED from 1-minute future bars. [I], and backfilled.

    WHY. The live gauge only knows what the socket saw, so a server started at
    11:00 has no morning -- the operator's own objection, verbatim: *"i open my
    laptop at 11 to pta chle morning ki koi info nhi h phir to reliable he nhi
    hoga"*. Bars are servable from REST for the whole session, so the morning's
    volume IS recoverable even though the frames are gone.

    METHOD -- BVC (bulk volume classification), the coarser cousin of what
    `Gauge.on_frame` does live. A bar's whole volume is signed by its
    close-to-close direction, which is the SAME tick rule, just applied to a
    60-second aggregate instead of a 0.5s frame. That is the ceiling and it is
    real: one 1-minute bar that was bought hard then sold hard nets one sign
    for all of it, where the live path would have split it across ~120 frames.
    A backfilled reading is therefore SMOOTHER and generally LOWER than the
    live gauge would have read on the same tape. Never compare the two as if
    they were the same measurement, and never pool their percentiles.

    The FIRST bar has no previous close, so its volume is split half/half --
    the same honest neutral the live path applies to volume with no sign yet,
    chosen over inventing a direction from the bar's own body.

    NOT A FORWARD RECORD. Every row is tagged `backfill: True` and the caller
    writes them to a SEPARATE file. `data/vpin_log.jsonl` is the promotion
    evidence for a shadow module on a 30-session kill clock; a reconstruction
    written into it would be indistinguishable from an observation the moment
    it landed, and the clock would be counting rows the socket never saw.

    `bars` is `(stamp, close, volume)` OLDEST FIRST -- the order
    `upstox_adapter.candles_to_arrays` already guarantees. Pure: no I/O, no
    clock, no token.
    """
    g = Gauge(bucket_v, window)
    out: List[Dict] = []
    cum = 0.0
    primed = False
    for stamp, close, vol in bars:
        if close is None or vol is None:
            continue          # a dropped bar is a gap, never a zero-volume bar
        if not primed:
            # Prime the baseline at zero so the FIRST bar's volume counts.
            # Feeding cumulative volume straight in would make bar 1 the
            # baseline frame and silently discard 09:15 -- the heaviest
            # minute of most sessions.
            g.on_frame(float(close), 0.0, stamp)
            primed = True
        cum += max(0.0, float(vol))
        for ev in g.on_frame(float(close), cum, stamp):
            out.append(dict(ev, backfill=True, src=BACKFILL_SRC))
    return out
