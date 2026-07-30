"""Option-premium bars and their own session VWAP + sigma bands.

Tape Chart Phase 5, task 2 (spec `2026-07-29-contract-tape-design.md` section
2, "Where the data comes from"). Pure computation, stdlib only, NO I/O --
the same isolation as `chain_metrics.py` / `structure.py`, and never imported
by `engine.py`. Fetching is the caller's job; this module receives an
already-fetched `dhan_fetch.rest_intraday` response.

    payload -> to_bars -> vwap_bands -> resample
               (reshape)  (1-minute)   (samples, never recomputes)

INPUT. One `rest_intraday` response is parallel arrays, verified against the
live API on 2026-07-30 (NIFTY security 65852, 375 entries each)::

    {"open": [...], "high": [...], "low": [...], "close": [...],
     "volume": [...], "timestamp": [...], "open_interest": [...]}

`timestamp` is TRUE epoch seconds (UTC), not an IST-shifted epoch. Checked on
paper against a real cached session: `data/backtest/fut_2026-07-17.json` opens
at 1784259900, which is 2026-07-17 03:45:00Z; 03:45 + 05:30 = 09:15 IST, the
NSE open, and the 375th value lands on 15:29. So the conversion is
`datetime.fromtimestamp(ts, IST)` with `IST` a FIXED +05:30 offset -- the same
call the rest of the codebase makes (`live.py:178`, `dhan_fetch.py:172`,
`backtest.py:39`). Being tz-aware it never consults the host clock, so the
labels are identical on a machine set to any timezone.

WHY THE VWAP MATH LIVES HERE. `live.py::_bars` grew the session VWAP + sigma
recurrence inline, welded to the FUT bar shape (uppercase keys, pivots merged
in, one loop doing reshape and bands at once). It could not be called as-is,
so it was EXTRACTED to `vwap_sigma()` below and `live._bars` now calls it.
There is exactly one derivation of a band in the live path. The spec's reason
is explicit: two derivations drift, and then v1 and v2 disagree about the same
band on the same data. `test_contract_bars.py` locks the two together.

The recurrence is reused VERBATIM, including its quirk -- the variance
accumulator uses the VWAP as it stood at bar `i` rather than re-centring the
whole history, so it is an incremental estimate and not the textbook
volume-weighted variance. That is what v1 has always drawn and what the
operator has always read; "fixing" it here would move every band in v1.

HONESTY RULES this module implements:

  * Ragged arrays are a defect in the feed. Truncate to the shortest and
    RECORD the drop on the returned `BarSeries.dropped` / `.lengths`. Never
    zip-pad, never silently.
  * A non-finite value makes that bar `None`, not 0. A `None` bar keeps its
    position (so indices stay addressable) and contributes NOTHING to the
    cumulative VWAP -- it is a bar we could not read, not a bar of zeros.
    An absent `open_interest` array is a missing INPUT rather than a bad
    value: the price bar survives with `oi: None`, because 0 would be a lie.
  * Never invent a bar. Empty or unusable input returns empty, never throws.
  * Causal: the bands at bar `i` are a function of bars 0..`i` only, so
    replay is truncation rather than recomputation (invariant 2).
  * Interval invariance: VWAP is computed on the 1-minute series and then
    SAMPLED. `resample` copies the bands off the last 1-minute bar in each
    bucket and never recomputes them, so changing interval cannot move a band
    by a paisa (spec section 2, invariant 6).
"""

import math
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

BAR_KEYS = ("t", "o", "h", "l", "c", "v", "oi")
BAND_KEYS = ("vwap", "u1", "d1", "u2", "d2", "u3", "d3")

# Arrays without which a bar cannot exist. `open_interest` is optional.
_REQUIRED = ("open", "high", "low", "close", "volume", "timestamp")
_OPTIONAL = ("open_interest",)


class BarSeries(list):
    """A list of bars that also carries what the reshape had to throw away.

    It IS a list -- callers index, slice and compare it as one -- but it
    answers `dropped` (rows lost to ragged arrays) and `lengths` (the raw
    per-array lengths the feed actually sent). The receipt travels with the
    data through `vwap_bands` and `resample` so a caller three steps down the
    pipeline can still say how much of the session it never saw.
    """

    def __init__(self, rows=(), dropped=0, lengths=None):
        super().__init__(rows)
        self.dropped = dropped
        self.lengths = dict(lengths or {})


def _carry(rows, src):
    """Propagate the drop receipt from `src` onto a new BarSeries."""
    return BarSeries(rows, getattr(src, "dropped", 0),
                     getattr(src, "lengths", None))


def _num(x):
    """A finite float, or None. Bools are not numbers here."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    f = float(x)
    return f if math.isfinite(f) else None


def _hhmm(ts):
    """Epoch seconds -> IST "HH:MM", or None if it is not a real instant."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, IST).strftime("%H:%M")
    except (OverflowError, OSError, ValueError):
        return None


def to_bars(payload):
    """One `rest_intraday` response -> `BarSeries` of bars sorted by time.

    Each bar is ``{"t": "HH:MM", "o", "h", "l", "c", "v", "oi"}`` in IST, or
    `None` where the feed sent something that is not a finite number. `oi` is
    `None` when the response carried no `open_interest` array at all.
    """
    payload = payload or {}
    lengths = {k: len(payload[k])
               for k in _REQUIRED + _OPTIONAL
               if isinstance(payload.get(k), (list, tuple))}
    longest = max(lengths.values()) if lengths else 0
    n = min(lengths.values()) if all(k in lengths for k in _REQUIRED) else 0
    out = BarSeries(dropped=longest - n, lengths=lengths)
    if n == 0:
        return out

    has_oi = "open_interest" in lengths
    raw_ts = payload["timestamp"]
    # Stable sort by instant; a bar whose timestamp is not a real instant
    # cannot be placed in the session, so it sinks to the end and is voided.
    order = sorted(range(n),
                   key=lambda i: (_num(raw_ts[i]) is None,
                                  _num(raw_ts[i]) or 0.0, i))
    for i in order:
        vals = [_num(payload[k][i]) for k in ("open", "high", "low", "close",
                                              "volume")]
        oi = _num(payload["open_interest"][i]) if has_oi else None
        t = _hhmm(_num(raw_ts[i]))
        if t is None or any(v is None for v in vals) or (has_oi and oi is None):
            out.append(None)
            continue
        o, h, l, c, v = vals
        out.append({"t": t, "o": o, "h": h, "l": l, "c": c, "v": v, "oi": oi})
    return out


class _Vwap:
    """The session VWAP + sigma recurrence, extracted from `live.py::_bars`.

    Cumulative and causal: `push` folds in one bar and returns the bands as
    they stand after it, so bar `i` has seen bars 0..`i` and nothing else.
    VWAP = cum(TP*V)/cumV with TP = (H+L+C)/3; bands = VWAP +/- n*sqrt(Var_w).
    With no volume yet there is no volume-weighted price, so VWAP falls back
    to the close and sigma is 0 -- live.py's rule, kept verbatim.
    """

    def __init__(self):
        self.cv = self.ctpv = self.cvar = 0.0

    def push(self, h, l, c, v):
        tp = (h + l + c) / 3.0
        self.cv += v
        self.ctpv += tp * v
        vwap = self.ctpv / self.cv if self.cv > 0 else c
        self.cvar += v * (tp - vwap) ** 2
        sd = math.sqrt(self.cvar / self.cv) if self.cv > 0 else 0.0
        return {"vwap": vwap,
                "u1": vwap + sd, "d1": vwap - sd,
                "u2": vwap + 2 * sd, "d2": vwap - 2 * sd,
                "u3": vwap + 3 * sd, "d3": vwap - 3 * sd}


def vwap_sigma(rows):
    """`(H, L, C, V)` tuples -> one band dict per row, cumulative and causal.

    The single implementation of a sigma band in the live path: `live._bars`
    and `vwap_bands` below both come through here.
    """
    st = _Vwap()
    return [st.push(h, l, c, v) for h, l, c, v in rows]


def vwap_bands(bars):
    """Bars -> the same bars with `vwap,u1,d1,u2,d2,u3,d3` appended.

    Session VWAP anchored at the first bar. The input is not mutated; a
    `None` bar yields a `None` entry and contributes nothing to the running
    sums, so a minute the feed could not deliver does not bend the band.
    """
    st = _Vwap()
    out = []
    for b in bars:
        if b is None:
            out.append(None)
            continue
        band = dict(b)
        band.update(st.push(b["h"], b["l"], b["c"], b["v"]))
        out.append(band)
    return _carry(out, bars)


def _minute_of_day(t):
    try:
        hh, mm = t.split(":")
        return int(hh) * 60 + int(mm)
    except (AttributeError, ValueError):
        return None


def _fold(group):
    """One bucket of 1-minute bars -> one aggregated bar."""
    first, last = group[0], group[-1]
    bar = {"t": first["t"], "o": first["o"],
           "h": max(b["h"] for b in group),
           "l": min(b["l"] for b in group),
           "c": last["c"],
           "v": sum(b["v"] for b in group),
           "oi": last["oi"]}                 # OI is a level, not a flow
    for k in BAND_KEYS:                      # SAMPLED off the last 1-min bar
        if k in last:
            bar[k] = last[k]
    return bar


def resample(bars, minutes):
    """Aggregate a 1-minute series to `minutes` (2 / 3 / 5 / 15).

    Buckets are anchored on the first bar's clock time, the same anchor the
    session VWAP uses, so a minute the feed never sent leaves a hole rather
    than shifting every later boundary. Each bucket is labelled by its opening
    minute. Band values are COPIED from the bucket's last 1-minute bar and are
    never recomputed -- that is what makes the interval invariance structural
    rather than a coincidence. Buckets with no real bar are not invented.
    """
    if isinstance(minutes, bool) or not isinstance(minutes, int):
        raise TypeError(f"interval must be a whole number of minutes, "
                        f"got {minutes!r}")
    if minutes < 1:
        raise ValueError(f"interval must be at least 1 minute, got {minutes}")

    out = []
    base = key = None
    group = []
    for b in bars:
        if b is None:
            continue
        m = _minute_of_day(b["t"])
        if m is None:
            continue
        if base is None:
            base = m
        k = (m - base) // minutes
        if key is None or k == key:
            group.append(b)
        else:
            out.append(_fold(group))
            group = [b]
        key = k
    if group:
        out.append(_fold(group))
    return _carry(out, bars)
