"""rank.py -- RANK, "kitna bada?": a measurement against recorded history at the same clock (decode-loop spec §4).

The metric definitions live here ONCE: tools/rank_build.py builds the reference from them (days strictly before the
session, into the `read` section of data/rank/rank_ref_<IDX>_<day>.json -- the same file the extension v2 reads), and
the server ranks today's numbers with them. Pure: stdlib + read (pure). No I/O, no clock.

WHAT IS RANKED (Phase 1, every number the READ card shows that measures the market; never a price, a level or a time)
  day-level, at the READ row's 5-minute mark, against every reference day's value at that same mark (exact clock):
    ce / pe     the writers' aaj likha on the nine (read.writers)            chain    [M]
    A           |A|, the writers' one-sidedness                              chain    [M]
    cvd         CVD since 09:15 (sum of the 5-min bars' delta)               ux / gc  [M]
    vol         volume since 09:15                                           ux / gc  [M]
    x           VWAP crosses since 09:30 (bar closes, hlc3 VWAP)             ux       [M]
  pooled within the spec's day-parts (09:15-10:00, 10:00-12:00, 12:00-13:30, 13:30-15:15):
    size        |bar delta| / the same-15-min-slot median |delta| of the other days (FLOW-STATE SIZE)   [M]
    share       |bar delta| / bar volume                                                                [M]
    bvol        bar volume (the thin gate: <= p10 is "thin", never BADA)                                [M]
    cvd40       the last 8 bars' delta summed (40 minutes)                                              [M]
    foi40       futures OI change over the last 8 bars, % of OI (FUEL: naye long / short, covering ...) [M]
    ce30 / pe30 the nine's 30-minute OI change                                                          [M]
  SENSEX's bar metrics are 15-minute bars with a 30-lot floor (FLOW-STATE §5: its 5-minute bars are not rankable).

THE LABEL (label()): pct = the size's percentile (mid-rank on ties, so "0 crosses" shared by half the days is not
BAHUT KAM), pct_sign = the signed value's percentile (shown, gates nothing), n = reference DAYS. Tags: <= p10 BAHUT KAM,
< p70 noise, p70-89 notable, >= p90 BADA, above every reference value RECORD. prov while n < 30. A bucket (day kind)
under MIN_DAYS days does not rank. Thin bar -> never BADA. Delta two-source rule (NIFTY, GoCharting + Upstox; amended
2026-10-19): both present and both >= p70 with the same sign -> ranked; both present and not agreeing -> "sources
disagree", capped at notable; one source absent -> the other's own rank, uncapped, tagged "GC only" / "1 src".
DESCRIPTIVE ONLY: a distribution, never a hit rate; nothing here gates the READ, the zone machine or any signal.
"""
from __future__ import annotations

import bisect
import math

import read

PARTS = ((33300, 36000), (36000, 43200), (43200, 48600), (48600, 54900))   # 09:15-10:00, 10:00-12:00, 12:00-13:30, 13:30-15:15
OPEN_S, CLOSE_S, CROSS_FROM = 33300, 55800, 34200                           # 09:15, 15:30, crosses count after 09:30
MARK = 300
MIN_DAYS, PROV_N = 5, 30
BAR_MIN = {"SENSEX": 15}                                                    # minutes per ranked bar; 5 elsewhere
LOT_FLOOR = {"SENSEX": 30}                                                  # lots: a lighter bar is not ranked
WIN = 8                                                                     # 8 x 5 min = the 40-minute window
TAGS = ("BAHUT KAM", "noise", "notable", "BADA", "RECORD")
CC = "could not check -- "


def part_of(sec):
    for n, (a, b) in enumerate(PARTS):
        if a <= sec < b:
            return n
    return None


def hm(sec):
    return read.hm(sec)


# ---- the day's bars -----------------------------------------------------------------------------------------------

def bars_of(rows, minutes=5):
    """A source's 5-min bar rows (ux_log / tape_log: t ms, o h l c, vol, delta, oi, partial) -> the session's bars,
    deduped by t (last row wins), oldest first, each {s, e, o, h, l, c, vol, delta, oi, partial, fill}. minutes=15
    sums three 5-min bars on the 09:15 grid (a 15-min bar with a missing 5-min piece is `partial`)."""
    by = {}
    for r in rows or ():
        t = r.get("t") if isinstance(r, dict) else None
        if isinstance(t, (int, float)) and not isinstance(t, bool):
            by[int(t)] = r
    out = []
    for t in sorted(by):
        r = by[t]
        s = int(t // 1000 + 19800) % 86400
        if not OPEN_S <= s < CLOSE_S:
            continue
        out.append({"s": s, "e": s + MARK, "o": r.get("o"), "h": r.get("h"), "l": r.get("l"), "c": r.get("c"),
                    "vol": r.get("vol"), "delta": r.get("delta"), "oi": r.get("oi"), "partial": bool(r.get("partial")),
                    "fill": r.get("o") is None or r.get("c") is None})
    if minutes == 5:
        return out
    w, agg = minutes * 60, {}
    for b in out:
        k = OPEN_S + (b["s"] - OPEN_S) // w * w
        agg.setdefault(k, []).append(b)
    res = []
    for k in sorted(agg):
        g = agg[k]
        vals = lambda f: [x[f] for x in g if isinstance(x.get(f), (int, float))]   # noqa: E731
        hs, ls = vals("h"), vals("l")
        res.append({"s": k, "e": k + w, "o": g[0]["o"], "c": g[-1]["c"], "h": max(hs) if hs else None,
                    "l": min(ls) if ls else None, "vol": sum(vals("vol")), "delta": sum(vals("delta")),
                    "oi": g[-1]["oi"], "partial": len(g) < w // MARK or any(x["partial"] for x in g),
                    "fill": any(x["fill"] for x in g)})
    return res


def cross_closes(bars):
    """The close (sec) of every bar whose close is on the other side of the session's hlc3 VWAP from the last nonzero
    side, counted once the bar closes after 09:30. tools/rank_build.cross_closes, on `s` (seconds) instead of `m`."""
    pv = v = 0.0
    last, out = 0, []
    for b in bars:
        h, lo, c = b.get("h"), b.get("l"), b.get("c")
        tp = (h + lo + c) / 3 if None not in (h, lo, c) else (h + lo) / 2 if h is not None and lo is not None else c
        w = (b.get("vol") or 0) if tp is not None else 0
        if w:
            pv += tp * w
            v += w
        vw = pv / v if v else None
        if c is None or vw is None:
            continue
        sg = (c > vw) - (c < vw)
        if not sg:
            continue
        if last and sg != last and b["e"] > CROSS_FROM:
            out.append(b["e"])
        last = sg
    return out


def _whole(b):
    """A bar a running total may include: present, with delta and volume, and not partial -- except the 09:15 bar, which
    is partial on every recorded day (the recorder starts ~09:17), so every day's total is "from the first tick" alike."""
    return (b is not None and isinstance(b.get("delta"), (int, float)) and isinstance(b.get("vol"), (int, float))
            and (not b.get("partial") or b["s"] == OPEN_S))


def flow_marks(bars):
    """{mark sec: {"cvd", "vol", "x"}} at every 5-min mark the bars reach, each only while every 5-min bar from 09:15
    to that mark is present and whole (_whole; a hole makes the running total wrong, so it is None from there on:
    never a guess)."""
    out = {}
    if not bars:
        return out
    by = {b["s"]: b for b in bars}
    crosses = cross_closes(bars)
    cvd = vol = 0
    whole = True
    for m in range(OPEN_S + MARK, min(CLOSE_S, max(by) + MARK) + 1, MARK):
        b = by.get(m - MARK)
        if whole and not _whole(b):
            whole = False
        if whole:
            cvd += b["delta"]
            vol += b["vol"]
        out[m] = ({"cvd": cvd, "vol": vol, "x": sum(1 for e in crosses if e <= m)} if whole
                  else {"cvd": None, "vol": None, "x": None})
    return out


def window(bars, i, n=WIN):
    """(sum of delta, first bar, last bar) over bars[i-n+1 .. i] when they are n contiguous whole bars, else None."""
    if i < n - 1:
        return None
    g = bars[i - n + 1:i + 1]
    if any(g[k + 1]["s"] - g[k]["s"] != MARK for k in range(n - 1)) or not all(_whole(b) for b in g):
        return None
    return sum(b["delta"] for b in g), g[0], g[-1]


def foi(bars, i, n=WIN):
    """(futures OI change % over the window, change in contracts, price change) from the bar before the window's first
    to its last, or None. The bar before is the window's opening OI."""
    if i < n:
        return None
    a, b = bars[i - n], bars[i]
    if b["s"] - a["s"] != n * MARK or not all(isinstance(x.get("oi"), (int, float)) and x["oi"] > 0 for x in (a, b)):
        return None
    if a.get("c") is None or b.get("c") is None:
        return None
    return (b["oi"] - a["oi"]) / a["oi"] * 100, b["oi"] - a["oi"], b["c"] - a["c"]


def fuel_word(d_oi, d_px):
    """The FUEL label (spec §10b O3): who the move's OI says is acting."""
    if d_oi > 0:
        return "naye long" if d_px > 0 else "naye short" if d_px < 0 else "OI badha"
    if d_oi < 0:
        return "covering" if d_px > 0 else "long chhod rahe" if d_px < 0 else "OI ghata"
    return "OI flat"


def chain_marks(X):
    """{mark sec: {"ce", "pe", "A", "ce30", "pe30"}} -- read.writers at the chain row at or before each 5-min mark
    (and 30 minutes earlier), the READ's own definition. A row older than 2 minutes at the mark is None."""
    out = {}
    ts = X.get("t") or []
    for m in range(OPEN_S + MARK, CLOSE_S + 1, MARK):
        i = read._at(X, m)
        if i is None or m - ts[i] > 120:
            continue
        j = read._at(X, m - 1800)
        w = read.writers(X, i, j if j is not None and m - 1800 - ts[j] <= 120 and m - 1800 >= OPEN_S else None)
        if w.get("vote") is None and w.get("cls") == "BLIND":
            continue
        out[m] = {"ce": w.get("ce"), "pe": w.get("pe"), "A": None if w.get("A") is None else abs(w["A"]),
                  "ce30": w.get("ce30"), "pe30": w.get("pe30")}
    return out


# ---- reference tables ---------------------------------------------------------------------------------------------

def quant(xs):
    """101 quantiles of the values (tools/rank_build.quant's table)."""
    v = sorted(x for x in xs if x is not None)
    n = len(v)
    if not n:
        return None
    return {"q": [round(v[k * (n - 1) // 100], 4) for k in range(101)], "n": n}


def bar_samples(days5, daysb):
    """Per day, the pooled samples of one source: {day: {metric: [(part, x)]}}. size / share / bvol on the ranked bars
    (`daysb`: 15-min for SENSEX), SIZE against the same-slot median |delta| of the OTHER days (leave-one-day-out,
    FLOW-STATE §6); cvd40 / foi40 on the 5-min bars (`days5`). Each value {day: bars_of(...)}."""
    def slot_meds(skip):
        a = {}
        for d, bs in daysb.items():
            if d == skip:
                continue
            for b in bs:
                if isinstance(b.get("delta"), (int, float)) and not b.get("partial"):
                    a.setdefault(b["s"] // 900, []).append(abs(b["delta"]))
        return {k: sorted(x)[len(x) // 2] for k, x in a.items() if x}
    out = {}
    for d in sorted(set(days5) | set(daysb)):
        smp = {k: [] for k in ("size", "share", "bvol", "cvd40", "foi40")}
        sm = slot_meds(d)
        for b in daysb.get(d) or ():
            p = part_of(b["s"])
            if p is None or b.get("partial") or not isinstance(b.get("delta"), (int, float)) or not b.get("vol"):
                continue
            med = sm.get(b["s"] // 900)
            if med:
                smp["size"].append((p, abs(b["delta"]) / med))
            smp["share"].append((p, abs(b["delta"]) / b["vol"]))
            smp["bvol"].append((p, b["vol"]))
        bs = days5.get(d) or []
        for i, b in enumerate(bs):
            p = part_of(b["e"] - 1)
            if p is None:
                continue
            w = window(bs, i)
            if w is not None:
                smp["cvd40"].append((p, w[0]))
            f = foi(bs, i)
            if f is not None:
                smp["foi40"].append((p, round(f[0], 4)))
        out[d] = smp
    return out


def slot_medians(days):
    """{slot: median |delta|} over every day given (the live SIZE's denominator: all reference days)."""
    a = {}
    for bs in days.values():
        for b in bs:
            if isinstance(b.get("delta"), (int, float)) and not b.get("partial"):
                a.setdefault(b["s"] // 900, []).append(abs(b["delta"]))
    return {str(k): sorted(x)[len(x) // 2] for k, x in sorted(a.items()) if x}


def pool(samples, keep):
    """{metric: [table per day-part]} from bar_samples' days in `keep`; each table carries `nd`, its days."""
    out = {}
    for metric in ("size", "share", "bvol", "cvd40", "foi40", "ce30", "pe30"):
        per = []
        for p in range(len(PARTS)):
            xs, nd = [], 0
            for d in keep:
                v = [x for (pp, x) in (samples.get(d) or {}).get(metric, ()) if pp == p]
                if v:
                    xs += v
                    nd += 1
            t = quant(xs)
            if t:
                t["nd"] = nd
            per.append(t)
        if any(per):
            out[metric] = per
    return out


# ---- ranking ------------------------------------------------------------------------------------------------------

def pct_tab(tab, x):
    """Mid-rank percentile of x in a 101-quantile table (ties take the middle of their run)."""
    if not tab or x is None:
        return None
    q = tab["q"]
    lo, hi = bisect.bisect_left(q, x), bisect.bisect_right(q, x)
    return round(max(0.0, min(100.0, (lo + hi - 1) / 2)), 1) if hi > lo else round(min(100.0, max(0.0, lo - 0.5)), 1)


def pct_vals(vals, x):
    """Mid-rank percentile of x among raw reference values."""
    v = [y for y in vals if y is not None]
    if not v or x is None:
        return None
    below, eq = sum(1 for y in v if y < x), sum(1 for y in v if y == x)
    return round(100.0 * (below + 0.5 * eq) / len(v), 1)


def tag_of(pct, record=False, low=False):
    if pct is None:
        return "?"
    if record:
        return "RECORD"
    if pct <= 10 or low:
        return "BAHUT KAM"
    return "noise" if pct < 70 else "notable" if pct < 90 else "BADA"


def label(raw, pct, n, *, pct_sign=None, record=False, low=False, thin=False, single=None, unit=None, src=None,
          why=None):
    """The rank object. `single`: the one source's name when the reading has only one -- tagged, NOT capped (2026-10-19
    amendment: an absent source is not a disagreeing one; a missing value is never a contrary value, CLAUDE.md rule 6)."""
    if pct is None:
        return {"raw": raw, "unit": unit, "pct": None, "pct_sign": None, "n": n, "tag": "?", "prov": None,
                "src": src, "why": why or CC + "no reference for this number"}
    tag = tag_of(pct, record, low)
    capped = None
    if thin and tag in ("BADA", "RECORD"):
        tag, capped = "notable", "thin"
    return {"raw": raw, "unit": unit, "pct": pct, "pct_sign": pct_sign, "n": n, "tag": tag, "prov": n < PROV_N,
            "thin": thin or None, "single": single, "capped": capped, "src": src, "why": why}


def by_mark(ref_marks, kinds, kind, metric, mark, x, *, signed=True, unit=None, src=None, single=None):
    """Rank x against every reference day of `kind` at the same 5-min mark. ref_marks = {"days": [...], metric:
    {mark: [values aligned with days]}}."""
    if not ref_marks or x is None:
        return label(x, None, 0, unit=unit, src=src, why=None if ref_marks else CC + f"no {src} reference")
    vals_all = (ref_marks.get(metric) or {}).get(str(mark))
    if vals_all is None:
        return label(x, None, 0, unit=unit, src=src, why=CC + f"no {src} reference day reached {hm(mark)}")
    vals = [v for d, v in zip(ref_marks["days"], vals_all) if kinds.get(d) == kind and v is not None]
    if len(vals) < MIN_DAYS:
        return label(x, None, len(vals), unit=unit, src=src,
                     why=CC + f"only {len(vals)} {kind} day(s) at {hm(mark)} in the {src} reference (needs {MIN_DAYS})")
    mag = [abs(v) for v in vals]
    pct = pct_vals(mag, abs(x))
    return label(x, pct, len(vals), pct_sign=pct_vals(vals, x) if signed else None,
                 record=abs(x) > max(mag), low=abs(x) < min(mag), unit=unit, src=src, single=single)


def by_part(pools, metric, sec, x, *, signed=True, magnitude=None, unit=None, src=None, single=None, thin=False):
    """Rank x against the pooled day-part table. Signed tables (cvd40, foi40, ce30, pe30) rank |x| by the CDF
    difference F(|x|) - F(-|x|) and keep pct_sign = F(x); magnitude tables (size, share, bvol) rank x itself."""
    p = part_of(sec)
    tabs = (pools or {}).get(metric)
    tab = tabs[p] if tabs and p is not None and p < len(tabs) else None
    if not tab or x is None:
        return label(x, None, 0, unit=unit, src=src,
                     why=None if tab else CC + f"no {src} {metric} reference for this part of the day")
    nd = tab.get("nd") or 0
    if nd < MIN_DAYS:
        return label(x, None, nd, unit=unit, src=src, why=CC + f"only {nd} {src} day(s) in this part of the day")
    q = tab["q"]
    v = magnitude if magnitude is not None else x
    if signed:
        hi, lo = pct_tab(tab, abs(v)), pct_tab(tab, -abs(v))
        pct = round(max(0.0, min(100.0, hi - lo)), 1)
        rec = abs(v) > max(abs(q[0]), abs(q[-1]))
        low = abs(v) < min(abs(y) for y in q)
        return label(x, pct, nd, pct_sign=pct_tab(tab, v), record=rec, low=low, unit=unit, src=src, single=single,
                     thin=thin)
    return label(x, pct_tab(tab, v), nd, record=v > q[-1], low=v < q[0], unit=unit, src=src, single=single,
                 thin=thin)


def two_source(gc, ux, gc_raw, ux_raw):
    """The delta rule (spec §4, amended 2026-10-19 under Mary's standing rule): both sources present and both >= p70
    with the same sign -> the pair's rank; both present but NOT agreeing (sign differs, or one >= p70 and the other not)
    -> "sources disagree", capped at notable; ONE source present (the other not ticking, a feed gap, no GC for the
    index) -> that source's own rank, uncapped, tagged "GC only" / "1 src". An absent source is not a disagreeing one:
    9 Oct's record opening (GC +6,244, Upstox not yet up) reads RECORD · GC only. -> the combined label."""
    have = [(n, L, r) for n, L, r in (("GC", gc, gc_raw), ("UX", ux, ux_raw)) if L and L.get("pct") is not None]
    if not have:
        return dict(ux or gc or label(None, None, 0), src="GC+UX")
    if len(have) == 1:
        n, L, _r = have[0]
        return dict(L, single=n, src=f"{n} only")
    (_, g, gr), (_, u, ur) = have
    agree = (gr or 0) * (ur or 0) > 0
    both = g["pct"] >= 70 and u["pct"] >= 70
    weak = g if g["pct"] <= u["pct"] else u                        # the weaker of the two speaks for the pair
    if both and agree:
        return dict(weak, src="GC+UX ✓", gc=g, ux=u)
    if g["pct"] >= 70 or u["pct"] >= 70:                          # both present, not agreeing: capped at notable
        out = dict(g if g["pct"] >= u["pct"] else u, src="sources disagree", gc=g, ux=u,
                   why="GC and Upstox are both here and do not both say it")
        if out["tag"] in ("BADA", "RECORD"):
            out.update(tag="notable", capped="sources disagree")
        return out
    return dict(weak, src="GC+UX", gc=g, ux=u)


def day_kind(day, expiry, fut_expiry, ik=None, last_ik=None):
    """NORMAL / EXPIRY (that index's option expiry is today) / ROLL (the future expires today, or today is the first
    day on a new contract). A ROLL day is also an expiry day for a monthly-only index; ROLL wins."""
    if fut_expiry and str(fut_expiry)[:10] == day or (ik and last_ik and ik != last_ik):
        return "ROLL"
    if expiry and str(expiry)[:10] == day:
        return "EXPIRY"
    return "NORMAL"


# ---- the live read's ranks ----------------------------------------------------------------------------------------

def _last_closed(bars, mark):
    """Index of the bar that closed most recently at or before `mark` -- only if it is the grid's latest (a bar that is
    missing at the mark is "?", never an older bar standing in for it)."""
    i = bisect.bisect_right([b["e"] for b in bars], mark) - 1
    if i < 0:
        return None
    return i if mark - bars[i]["e"] < bars[i]["e"] - bars[i]["s"] else None


def _gap_why(bs, mark, src):
    """Why a running total from 09:15 is missing at `mark`: the first bar, or the first hole."""
    bs = [b for b in bs if b["e"] <= mark]
    if not bs:
        return CC + f"no {src} bar closed by {hm(mark)}"
    if bs[0]["s"] > OPEN_S:
        return CC + f"{src} bars begin {hm(bs[0]['s'])} (nothing recorded from 09:15)"
    by = {b["s"]: b for b in bs}
    for m in range(OPEN_S, mark, MARK):
        if not _whole(by.get(m)):
            return CC + f"{src} {hm(m)} bar " + ("missing" if by.get(m) is None else "incomplete")
    return CC + f"no {src} reference day reached {hm(mark)}"


def _row_at(rows, t):
    return next((r for r in rows or () if r.get("t") == t), None)


def _pre_end(f):
    """The mark (sec) up to which the READ's FLOW was filled from GoCharting ("HH:MM tak GC"), or -1."""
    g = f.get("gc")
    return int(g[:2]) * 3600 + int(g[3:5]) * 60 if isinstance(g, str) and len(g) >= 5 else -1


def card_ranks(ref, idx, day, X, card, rows, ux_rows, gc_rows=None, ik=None):
    """Every ranked number behind one READ card (read.card), at the card's 5-min mark. ref = rank_ref (its `read`
    section); rows = the READ timeline's rows (the 10:00 row carries the opening flow); ux_rows / gc_rows = the day's
    Upstox / GoCharting 5-min bar rows (only bars closed by the mark are used). The READ's own FLOW numbers (ticks)
    are ranked against the Upstox history -- the same feed -- and GoCharting is the second source (NIFTY).
    -> {"kind", "mark", <name>: label, ...}; a number with no reference carries tag "?" and the reason."""
    R = (ref or {}).get("read") or {}
    mark = int(card["t"][:2]) * 3600 + int(card["t"][3:5]) * 60
    kind = day_kind(day, X.get("expiry"), X.get("fut_expiry"), ik, R.get("last_ik"))
    kinds = R.get("kinds") or {}
    out = {"kind": kind, "mark": card["t"], "ref": (ref or {}).get("id"), "before": (ref or {}).get("before"),
           "why": None if R else CC + "no rank reference with a read section (tools/rank_build.py)", "tag": "M"}
    marks, pools = R.get("marks") or {}, ((R.get("pool") or {}).get(kind) or {})
    # chain: the writers at the mark -- the very numbers the LIKHNA / 30 MIN chips print
    w = card.get("w") or {}
    ch = marks.get("chain")
    for k in ("ce", "pe"):
        out[k] = by_mark(ch, kinds, kind, k, mark, w.get(k), unit="k", src="chain")
    out["A"] = by_mark(ch, kinds, kind, "A", mark, None if w.get("A") is None else abs(w["A"]), signed=False,
                       src="chain")
    for k in ("ce30", "pe30"):
        out[k] = by_part(pools.get("chain") or {}, k, mark - 1, w.get(k), unit="k", src="chain")
    # the READ's FLOW chip (ticks since the first tick, GC-filled before it on a late start) vs Upstox's history
    f = card.get("f") or {}
    um = marks.get("ux")
    r10 = _row_at(rows, hm(min(mark, 36000))) or {}
    f10 = r10.get("flow") or {}
    ff = X.get("flow_from")

    def read_side(fl, at, metric, signed=True):
        """The READ's own tick flow at `at`, ranked against Upstox's history -- only when it runs from the 09:15 bar
        (a late start's ticks, or GoCharting bars filling the morning, are not the same number as the history's)."""
        if fl.get(metric) is None:
            return label(None, None, 0, src="UX", why=fl.get("why") or CC + f"no futures tick by {hm(at)}")
        if _pre_end(fl) >= 0:
            return label(fl[metric], None, 0, src="UX",
                         why=CC + f"to {fl['gc']} the READ's flow is GoCharting's bars (a late start), not Upstox ticks")
        if ff is None or ff >= OPEN_S + MARK:
            return label(fl[metric], None, 0, src="UX", why=CC + f"ticks begin {hm(ff)} (nothing from 09:15)")
        return by_mark(um, kinds, kind, metric, at, fl[metric], signed=signed, unit="lots", src="UX")
    read_cvd = read_side(f, mark, "cvd")
    read_vol = read_side(f, mark, "vol", signed=False)
    read_open = read_side(f10, min(mark, 36000), "cvd")
    # the bars: Upstox (all three) and GoCharting (NIFTY)
    bm = BAR_MIN.get(idx, 5)
    srcs = {"ux": bars_of(ux_rows, 5)}
    if gc_rows is not None:
        srcs["gc"] = bars_of(gc_rows, 5)
    per = {}
    for name, bs in srcs.items():
        bs = [b for b in bs if b["e"] <= mark]
        S = name.upper()
        fms = flow_marks(bs)
        rm, pl = marks.get(name), (pools.get(name) or {})
        L = {}
        if name == "gc":
            for key, at, metric in (("cvd", mark, "cvd"), ("open", min(mark, 36000), "cvd"), ("vol", mark, "vol")):
                v = (fms.get(at) or {}).get(metric)
                L[key] = (by_mark(rm, kinds, kind, metric, at, v, signed=metric == "cvd", unit="lots", src="GC")
                          if v is not None else label(None, None, 0, src="GC", why=_gap_why(bs, at, "GC")))
        else:
            fm = fms.get(mark) or {}
            L["x"] = (by_mark(rm, kinds, kind, "x", mark, fm.get("x"), signed=False, src="UX")
                      if fm.get("x") is not None else label(None, None, 0, src="UX", why=_gap_why(bs, mark, "UX")))
        rb = bs if bm == 5 else _agg(bs, bm)
        i = _last_closed(rb, mark)
        b = rb[i] if i is not None else None
        if b is None or b.get("partial") or not isinstance(b.get("delta"), (int, float)) or not b.get("vol"):
            why = (CC + f"no whole {bm}-min {S} bar closed by {card['t']}" if b is None or b.get("partial")
                   else CC + f"the {hm(b['s'])} {S} bar carries no delta")
            L["bar"] = label(None, None, 0, src=S, why=why)
            L["bvol"] = label(None, None, 0, src=S, why=why)
        else:
            bv = dict(by_part(pl, "bvol", b["s"], b["vol"], signed=False, unit="lots", src=S), t=hm(b["s"]))
            if b["vol"] < LOT_FLOOR.get(idx, 0):
                L["bar"] = label(b["delta"], None, 0, src=S,
                                 why=f"not shown -- {b['vol']:.0f} lots in {bm} min, under the {LOT_FLOOR[idx]}-lot floor")
            else:
                thin = bv.get("pct") is not None and bv["pct"] <= 10
                med = ((R.get("slot") or {}).get(kind) or {}).get(name, {}).get(str(b["s"] // 900))
                size = abs(b["delta"]) / med if med else None
                L["bar"] = dict(by_part(pl, "size", b["s"], b["delta"], signed=False, magnitude=size, src=S, thin=thin),
                                raw=b["delta"], unit="lots", t=hm(b["s"]), min=bm,
                                size=None if size is None else round(size, 2), share=round(abs(b["delta"]) / b["vol"], 2))
            L["bvol"] = bv
        j = _last_closed(bs, mark)
        wv = window(bs, j) if j is not None else None
        L["cvd40"] = (by_part(pl, "cvd40", mark - 1, wv[0], unit="lots", src=S) if wv
                      else label(None, None, 0, src=S, why=CC + f"the last 40 minutes are not 8 whole {S} bars"))
        if name == "ux":
            fo = foi(bs, j) if j is not None else None
            if fo is None:
                L["foi40"] = label(None, None, 0, src="UX", why=CC + "futures OI not on both ends of the 40 minutes")
            else:
                fl = by_part(pl, "foi40", mark - 1, round(fo[0], 3), unit="%", src="UX")
                word = fuel_word(fo[1], fo[2]) if (fl.get("pct") or 0) >= 70 else "OI flat"
                L["foi40"] = dict(fl, lots=round(fo[1] / (X.get("lot") or 1)), px=round(fo[2], 1), word=word)
        per[name] = L
    ux, gc = per["ux"], per.get("gc")
    if gc is not None:                     # NIFTY: the two-source rule on every delta; the READ's own CVD is the UX side
        for k, u, fl in (("cvd", read_cvd, f), ("open", read_open, f10)):
            # a READ flow filled from GoCharting bars is GoCharting again, not an independent second source
            u = None if _pre_end(fl) >= 0 else u
            out[k] = two_source(gc[k], u, gc[k].get("raw"), (u or {}).get("raw"))
        for k in ("bar", "cvd40"):
            out[k] = two_source(gc[k], ux[k], gc[k].get("raw"), ux[k].get("raw"))
    else:                                  # BANKNIFTY / SENSEX: Upstox alone (spec §4, D5) -- tagged, not capped
        for k, L in (("cvd", read_cvd), ("open", read_open), ("bar", ux["bar"]), ("cvd40", ux["cvd40"])):
            out[k] = dict(L, single="UX", src="UX only")
    for k in ("x", "bvol", "foi40"):
        out[k] = ux[k]
    # volume is no delta (no two-source rule): the READ's own, else GoCharting's on a late start
    out["vol"] = read_vol if read_vol.get("pct") is not None or gc is None else (
        gc["vol"] if gc["vol"].get("pct") is not None else read_vol)
    out["open_t"] = "09:15–" + hm(min(mark, 36000))
    out["scale"] = scale(X, card)
    out["likhna"] = likhna_word(w, out["ce"], out["pe"])
    return out


def fuel_ref(ref, day, X, ux_rows):
    """READ-2 FUEL's reference (read.fuel): the `read` section's Upstox pool for the day's kind -- the very tables
    card_ranks ranks foi40 on -- or None when the reference has no `read` section."""
    R = (ref or {}).get("read") or {}
    if not R:
        return None
    ik = next((b.get("ik") for b in reversed(ux_rows or []) if isinstance(b, dict) and b.get("ik")), None)
    kind = day_kind(day, X.get("expiry"), X.get("fut_expiry"), ik, R.get("last_ik"))
    return ((R.get("pool") or {}).get(kind) or {}).get("ux")


def likhna_word(w, ce, pe):
    """The LIKHNA chip's word, gated by RANK (spec §4: positioning words only when the ranked move is >= p70). The
    READ's class (read.CLS_WORD) stays the READ's vote; only the word on screen waits for the size. -> (word, gated)."""
    cls = w.get("cls")
    big = lambda L: (L or {}).get("pct") is not None and L["pct"] >= 70     # noqa: E731
    if cls in ("CALL", "PUT"):
        side = ce if cls == "CALL" else pe
        if big(side):
            return {"word": read.CLS_WORD[cls], "gated": False}
        return {"word": ("CALL" if cls == "CALL" else "PUT") + " ki taraf · likhna " + (
            "?" if (side or {}).get("pct") is None else "noise"), "gated": True}
    if cls in ("BOTH_WRITE", "BOTH_COVER"):
        if big(ce) and big(pe):
            return {"word": read.CLS_WORD[cls], "gated": False}
        return {"word": "OI flat · noise" if cls == "BOTH_COVER" else "dono taraf · noise", "gated": True}
    return {"word": read.CLS_WORD.get(cls, cls), "gated": False}


def _agg(bs, minutes):
    """5-min bars (bars_of's) -> `minutes` bars on the 09:15 grid, the same aggregation bars_of does from rows."""
    rows = [dict(t=(b["s"] - 19800) * 1000, **{k: b[k] for k in ("o", "h", "l", "c", "vol", "delta", "oi", "partial")})
            for b in bs]
    return bars_of(rows, minutes)


def scale(X, card):
    """Scale units that need no history [I]: the day's range / the IV-priced day sigma (spot x ATM IV / sqrt(365)),
    and the last 30 minutes' spot move / the 30 minutes' priced share of it (sigma_day x sqrt(30 / 375))."""
    out = {"tag": "I"}
    ts = X.get("t") or []
    if not ts:
        return dict(out, why=CC + "no chain row")
    mark = int(card["t"][:2]) * 3600 + int(card["t"][3:5]) * 60
    i = read._at(X, mark)
    civ, piv, sl = X.get("ce_iv"), X.get("pe_iv"), X.get("slow") or 1
    if i is None or not civ:
        return dict(out, why=CC + "no IV on the chain rows")
    js, m = read._sym(X, i)
    a = min(i // sl, len(civ) - 1)
    ivs = [L[a][js[len(js) // 2]] for L in (civ, piv) if m >= 0 and L[a][js[len(js) // 2]] is not None]
    if not ivs:
        return dict(out, why=CC + "the ATM strike carries no IV")
    spot = X["spot"][i]
    sd = spot * (sum(ivs) / len(ivs) / 10000) / math.sqrt(365)
    hl = (card.get("hl") or {}).get("spot")
    out.update(iv=round(sum(ivs) / len(ivs) / 100, 2), sigma_d=round(sd, 1))
    if hl:
        out["range_sd"] = round((hl["hi"] - hl["lo"]) / sd, 2) if sd else None
    j = read._at(X, mark - 1800)
    if j is not None and mark - 1800 >= OPEN_S and sd:
        out["moved30"] = round(abs(spot - X["spot"][j]) / (sd * math.sqrt(30 / 375)), 2)
    return out
