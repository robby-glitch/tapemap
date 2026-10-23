"""tools/rank_build.py -- frame.rank_ref: what NORMAL looks like, from recorded days STRICTLY BEFORE a day.

    python tools/rank_build.py --idx NIFTY --before 2026-10-20 [--data DIR] [--out DIR]
        -> <out>/rank_ref_NIFTY_2026-10-20.json   (default out: data/rank/, default before: today IST)

Spec docs/superpowers/specs/2026-10-19-extension-v2-design.md §7; the wire is the V2-PLAN "Frame contract"
(orderflow-desk/docs/V2-PLAN.md). The page ranks x against a table as the largest k with q[k] <= x (rank() below),
so both sides agree. build() is also what the server calls (in a daemon thread) when today's file is missing.

Every table is {"q": [101 numbers, q[k] = sorted[floor(k * (n - 1) / 100)]], "n": n} -- or None with the reason in
`why` (key = the table's dotted path). Inputs, all [M] recorder rows, every one from a day < before:
  data/tape/tape_<IDX>_<day>.jsonl   GoCharting's closed 5-min bars (dedupe by t, last row wins; ladder in lots)
  data/tape/ofd_marks_<IDX>_<day>    the extension's marks (era B: day >= 2026-10-05)
  data/decoder/decoder_<day>.jsonl   E1 big prints (era B)
  data/chain/chain_<IDX>_<day>       the chain recorder (writers30: the last 10 chain days)
  data/tape/ux_<IDX>_<day>           the Upstox 5-min bars (the `read` section; all three indices)
  data/book/book_<IDX>_<day>         its first row only: the future's key and expiry (the day kind)
The JS it must agree with: orderflow-desk src/engine/board.js walls() binning and legs(), market.js vwapSeries().
`slot_range` (additive, A45 2026-10-23) is no q-table: {"HHMM": median 5-min bar high - low in points} per slot, from
GoCharting's bars (`slot_range_src` "gc"), or Upstox's for an index GoCharting never recorded ("ux").
`read` (additive, decode-loop Phase 1) is TapeMap's: the metric definitions are rank.py's, the extension never reads it
and the server strips it from what it sends the page. Every table above it is unchanged by it.
DESCRIPTIVE ONLY: a distribution, never a hit rate.
"""
import argparse
import bisect
import collections
import datetime
import gzip
import hashlib
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # tapemap/
DATA = os.path.join(HERE, "data")
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
V = 1                                        # the extension's tables; `read` (additive, its own `v`) is TapeMap's
CHECKPOINTS = tuple(range(585, 916, 30))     # 09:45 .. 15:15, IST minutes
WALL_FROM, OPEN_M, CLOSE_M = 560, 555, 930   # 09:20 (board.js walls), 09:15, 15:30
COVER = 0.8                                  # a day counts at a checkpoint with >= 80% of the expected 5-min bars
CROSS_FROM = 570                             # a cross counts once its bar closes after 09:30
ERA_B = "2026-10-05"
LEG_THR = 25                                 # fuel: board.js legs() at 25 points
FLOW_MIN_BARS, FLOW_LO, FLOW_HI, RES_MIN = 40, 33300, 54900, 0.25
CHAIN_DAYS, W30_FROM, W30_TO = 10, 35100, 54900


def quant(xs):
    v = sorted(x for x in xs if x is not None)
    n = len(v)
    if not n:
        return None
    return {"q": [round(v[k * (n - 1) // 100], 4) for k in range(101)], "n": n}


def rank(tab, x):
    """The page's rule: the largest k with q[k] <= x; 0 below the reference's minimum; None when either is missing."""
    if not tab or x is None:
        return None
    return max(0, bisect.bisect_right(tab["q"], x) - 1)


def _rows(path):
    for p in (path, path + ".gz"):
        if os.path.exists(p):
            op = gzip.open if p.endswith(".gz") else open
            out = []
            with op(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except ValueError:            # a torn line
                        continue
                    if isinstance(r, dict):
                        out.append(r)
            return out
    return []


def _days(data, sub, prefix, before):
    rx = re.compile(re.escape(prefix) + r"(\d{4}-\d{2}-\d{2})\.jsonl(\.gz)?$")
    try:
        names = os.listdir(os.path.join(data, sub))
    except OSError:
        return []
    return sorted({m.group(1) for m in map(rx.match, names) if m and m.group(1) < before})


def gc_bars(data, idx, day):
    """GoCharting's 5-min bars of one day, deduped by t (last row wins), 09:15 <= start < 15:30, oldest first;
    each with s (IST sec of day) and m (IST minute of the bar's start)."""
    by = {}
    for r in _rows(os.path.join(data, "tape", f"tape_{idx}_{day}.jsonl")):
        t = r.get("t")
        if isinstance(t, (int, float)) and not isinstance(t, bool):
            by[int(t)] = r
    out = []
    for t in sorted(by):
        s = int(t / 1000 + 19800) % 86400
        if OPEN_M <= s // 60 < CLOSE_M:
            out.append(dict(by[t], s=s, m=s // 60))
    return out


def _covered(bars, C, has):
    exp = (C - WALL_FROM) // 5
    n = sum(1 for b in bars if b["m"] >= WALL_FROM and b["m"] + 5 <= C and has(b))
    return exp > 0 and n >= COVER * exp


def bin5(p):
    """board.js walls()' bin: Math.round(p / 5) * 5 -- half up, never Python's banker's round() (22,502.5 -> 22,505)."""
    return math.floor(p / 5 + 0.5) * 5


def wall_values(bars, C):
    """board.js walls()' candidate bins at checkpoint C -> their |net delta| (lots). Bars from 09:20 that closed by C;
    bin = Math.round(p / 5) * 5; v = b + s, d = b - s, n = distinct bars; candidates n >= 2 and v >= the median bin v
    (sorted[len >> 1], 0 -> 1); fewer than 4 bins -> none (walls()' own guard)."""
    bins = {}
    for b in bars:
        if b["m"] < WALL_FROM or b["m"] + 5 > C:
            continue
        for r in b.get("ladder") or ():
            if not isinstance(r, dict) or not isinstance(r.get("p"), (int, float)):
                continue
            k = bin5(r["p"])
            q = bins.setdefault(k, [0, 0, set()])
            q[0] += (r.get("b") or 0) + (r.get("s") or 0)
            q[1] += (r.get("b") or 0) - (r.get("s") or 0)
            q[2].add(b["t"])
    if len(bins) < 4:
        return []
    vs = sorted(q[0] for q in bins.values())
    vmed = vs[len(vs) // 2] or 1
    return [abs(q[1]) for q in bins.values() if len(q[2]) >= 2 and q[0] >= vmed]


def cross_closes(bars):
    """market.js vwapSeries' hlc3 VWAP from the day's first bar; the close minute of every bar whose close side of
    VWAP differs from the last nonzero side, counted once the bar closes after 09:30."""
    pv = v = 0.0
    last, out = 0, []
    for b in bars:
        h, l, c = b.get("h"), b.get("l"), b.get("c")
        tp = (h + l + c) / 3 if None not in (h, l, c) else (h + l) / 2 if h is not None and l is not None else c
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
        if last and sg != last and b["m"] + 5 > CROSS_FROM:
            out.append(b["m"] + 5)
        last = sg
    return out


def legs(bars, thr):
    """board.js legs(), verbatim: zigzag on closes, legs end at the extreme bar's high / low."""
    if not bars:
        return []
    sgn = lambda x: (x > 0) - (x < 0)   # noqa: E731
    if len(bars) < 2:
        return [{"i0": 0, "i1": 0, "dir": sgn(bars[0]["c"] - bars[0]["o"]) or -1, "from": bars[0]["o"],
                 "to": bars[0]["c"], "open": True}]
    pv = lambda i, d: bars[i]["h"] if d > 0 else bars[i]["l"]   # noqa: E731
    out = []
    d, i0, ext, ext_i, frm = sgn(bars[0]["c"] - bars[0]["o"]) or -1, 0, bars[0]["c"], 0, bars[0]["o"]
    for i in range(1, len(bars)):
        c = bars[i]["c"]
        if (c >= ext) if d > 0 else (c <= ext):
            ext, ext_i = c, i
        if (ext - c if d > 0 else c - ext) >= thr:
            out.append({"i0": i0, "i1": ext_i, "dir": d, "from": frm, "to": pv(ext_i, d), "open": False})
            frm, d, i0, ext, ext_i = pv(ext_i, d), -d, ext_i, c, i
    out.append({"i0": i0, "i1": len(bars) - 1, "dir": d, "from": frm, "to": pv(ext_i, d), "open": True})
    return out


def fuel_values(bars):
    """|futures OI change| in percent over every 25-pt leg (bars with o/h/l/c all present: JS null arithmetic is
    not a price)."""
    bs = [b for b in bars if None not in (b.get("o"), b.get("h"), b.get("l"), b.get("c"))]
    out = []
    for L in legs(bs, LEG_THR):
        o0, o1 = bs[L["i0"]].get("oi"), bs[L["i1"]].get("oi")
        if isinstance(o0, (int, float)) and isinstance(o1, (int, float)) and o0 > 0:
            out.append(abs(o1 - o0) / o0 * 100)
    return out


def flow_ref(gc):
    """build_mockup.FlowRef's reference (FLOW-STATE-STUDY §6), stored as tables: days with >= 40 bars, bars
    09:15..15:15 with volume, slot = start sec // 900. SIZE is ranked leave-one-day-out (each reference day's bars
    against slot medians that exclude it), as FlowRef does."""
    days = {}
    for d, bars in gc.items():
        bs = [b for b in bars if FLOW_LO <= b["s"] <= FLOW_HI and b.get("vol") and isinstance(b.get("delta"), (int, float))
              and b.get("h") is not None and b.get("l") is not None]
        if len(bs) >= FLOW_MIN_BARS:
            days[d] = bs

    def slots(skip):
        a, v, r = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
        for d, bs in days.items():
            if d == skip:
                continue
            for b in bs:
                k = b["s"] // 900
                a[k].append(abs(b["delta"]))
                v[k].append(b["vol"])
                r[k].append(b["h"] - b["l"])
        return a, v, r

    a, v, r = slots(None)
    size, share, rv12 = [], [], []
    for d, bs in days.items():
        sm = {k: statistics.median(x) for k, x in slots(d)[0].items()}
        for i, b in enumerate(bs):
            m = sm.get(b["s"] // 900)
            if m:
                size.append(abs(b["delta"]) / m)
            share.append(abs(b["delta"]) / b["vol"])
            if i >= 12:
                m12 = statistics.median(x["vol"] for x in bs[i - 12:i])
                if m12:
                    rv12.append(b["vol"] / m12)
    rd = lambda x: round(x, 2)   # noqa: E731
    return {"slot_absd": {str(k): rd(statistics.median(x)) for k, x in sorted(a.items())},
            "slot_range": {str(k): rd(statistics.median(x)) for k, x in sorted(r.items())},
            "slot_vp10": {str(k): rd(sorted(x)[int(0.10 * (len(x) - 1))]) for k, x in sorted(v.items())},
            "size": quant(size), "share": quant(share), "rv12": quant(rv12), "res_min": RES_MIN,
            "days": sorted(days)}


def slot_range(days):
    """A45: {"HHMM": the median (high - low) of that 5-min slot's bars} over the reference days `days` ({day: bars with
    s = the bar's start sec}), skipping partial bars and bars without both prices. Every day here is < `before`, so the
    day the file serves is always left out (as the slot medians are). For the extension's bars judged before its own
    NR (the median range of today's last 20 bars) has 5 bars."""
    r = collections.defaultdict(list)
    for bs in days.values():
        for b in bs:
            h, lo = b.get("h"), b.get("l")
            if not b.get("partial") and isinstance(h, (int, float)) and isinstance(lo, (int, float)):
                r[f"{b['s'] // 3600:02d}{b['s'] // 60 % 60:02d}"].append(h - lo)
    return {k: round(statistics.median(x), 2) for k, x in sorted(r.items())}


def chain_rows(data, idx, day):
    """(sec, atm, {k: (ce oi, pe oi)}) per recorded chain row, oldest first."""
    out = []
    for r in _rows(os.path.join(data, "chain", f"chain_{idx}_{day}.jsonl")):
        if "strikes" not in r or "atm" not in r:
            continue
        if "sec" in r:
            sec = int(r["sec"])
        else:
            try:
                h, m, s = (str(r.get("ts")) + ":0:0").split(":")[:3]
                sec = int(h) * 3600 + int(m) * 60 + int(s)
            except ValueError:
                continue
        out.append((sec, r["atm"], {s["k"]: ((s.get("ce") or {}).get("oi"), (s.get("pe") or {}).get("oi"))
                                     for s in r["strikes"] if isinstance(s, dict) and "k" in s}))
    return out


def writers30(data, idx, before):
    """build_mockup.d30_ref: the 30-min OI change (thousands, signed) at ATM +/- 2, CE and PE, every 5 min
    09:45..15:15, pooled over the last 10 chain days before `before`. A checkpoint whose row, or the row 30 min
    earlier, is more than 2 min stale is skipped."""
    ds = _days(data, "chain", f"chain_{idx}_", before)[-CHAIN_DAYS:]
    pop, used = [], []
    for d in ds:
        rows = chain_rows(data, idx, d)
        if len(rows) < 2:
            continue
        used.append(d)
        ks = sorted(rows[0][2])
        step = ks[1] - ks[0] if len(ks) > 1 else 50
        ts = [x[0] for x in rows]
        for s in range(W30_FROM, W30_TO + 1, 300):
            i, j = bisect.bisect_right(ts, s) - 1, bisect.bisect_right(ts, s - 1800) - 1
            if i < 0 or j < 0 or s - ts[i] > 120 or s - 1800 - ts[j] > 120:
                continue
            atm = rows[i][1]
            for k in (atm + step * n for n in range(-2, 3)):
                a, b = rows[i][2].get(k), rows[j][2].get(k)
                if not a or not b:
                    continue
                for li in (0, 1):
                    if a[li] is not None and b[li] is not None:
                        pop.append((a[li] - b[li]) / 1000)
    tab = quant(pop)
    if tab:
        tab["days"] = used
    return tab, ds


BOARD_KINDS = ("trap", "absorption", "exhaustion", "initiative", "vacuum", "climax")
DEC_KINDS = ("E1", "E2", "E3")


def marks_ref(data, idx, before):
    """The board's mark sizes (ofd_marks: trap, absorption and -- v2.1, for the restored and SAB MARKS kinds -- exhaustion,
    initiative, vacuum, climax; deduped by bar, kind, side, round(p)) and the decoder's lots (E1 prints, E2 PEHAL, E3 DABAAV;
    deduped by id), era B days before `before`. Size-less decoder kinds (E4-E7) are ranked on their bar's SIZE instead."""
    pop, days = collections.defaultdict(list), collections.defaultdict(list)
    for d in _days(data, "tape", f"ofd_marks_{idx}_", before):
        if d < ERA_B:
            continue
        seen = set()
        for r in _rows(os.path.join(data, "tape", f"ofd_marks_{idx}_{d}.jsonl")):
            if r.get("kind") not in BOARD_KINDS or not isinstance(r.get("p"), (int, float)):
                continue
            key = (r.get("t"), r["kind"], r.get("side"), round(r["p"]))
            if key in seen or not isinstance(r.get("size"), (int, float)):
                continue
            seen.add(key)
            pop[r["kind"]].append(r["size"])
            if d not in days[r["kind"]]:
                days[r["kind"]].append(d)
    for d in _days(data, "decoder", "decoder_", before):
        if d < ERA_B:
            continue
        seen = set()
        for r in _rows(os.path.join(data, "decoder", f"decoder_{d}.jsonl")):
            if r.get("row") != "event" or r.get("kind") not in DEC_KINDS or r.get("idx", idx) != idx or r.get("id") in seen:
                continue
            lots = (r.get("event") or {}).get("lots")
            if not isinstance(lots, (int, float)):
                continue
            seen.add(r.get("id"))
            pop[r["kind"]].append(lots)
            if d not in days[r["kind"]]:
                days[r["kind"]].append(d)
    for d in _days(data, "tape", f"tape_{idx}_", before):             # A9: exhaustion's own strength, its own pool
        if d >= ERA_B:
            f = exhaustion_fades(gc_bars(data, idx, d))
            pop["exhaustion_fade"] += f
            if f:
                days["exhaustion_fade"].append(d)
    out = {}
    for k in BOARD_KINDS + DEC_KINDS + ("exhaustion_fade",):
        out[k] = quant(pop[k])
        if out[k]:
            out[k]["days"] = days[k]
    return out


def exhaustion_fades(bars):
    """A9 (MARKS-EXPLAINED §12.3): `marks.exhaustion` ranks eff, the with-leg delta of the very bar that exhausted, so
    the purest exhaustion (eff ~ 0) ranks p0 and is never drawn solid. Its own strength is the FADE of effort at the new
    extreme, 1 - eff / the leg's peak eff (0.4 .. 1; 1 = a new extreme on no with-leg delta at all). board.js
    exhaustion(), run at every bar close on the bars so far the way the page does (legs re-cut on each bar), each event
    once at the bar it first appears. The page ranks `fade` against this table once it sends it; until then the
    table is additive and nothing reads it."""
    bs = [b for b in bars if None not in (b.get("h"), b.get("l"), b.get("c"), b.get("o"), b.get("delta"))]
    seen, out = set(), []
    for n in range(3, len(bs) + 1):
        cut = bs[:n]
        rng = sorted(b["h"] - b["l"] for b in cut)
        for L in legs(cut, max(rng[len(rng) >> 1] * 0.6, 6)):
            peak, ext = 0, None
            for i in range(L["i0"], L["i1"] + 1):
                b = cut[i]
                eff, px = max(0, L["dir"] * b["delta"]), b["h"] if L["dir"] > 0 else b["l"]
                new = ext is None or (px > ext if L["dir"] > 0 else px < ext)
                if new and i > L["i0"] and peak >= 100 and eff <= peak * 0.6:     # board.js peakMin: 5-min bars
                    if (b["t"], -L["dir"], px) not in seen:
                        seen.add((b["t"], -L["dir"], px))
                        out.append(round(1 - eff / peak, 4))
                    break
                if new:
                    ext = px
                peak = max(peak, eff)
    return out


def _first_row(path):
    """The first parseable row of a day file (plain or .gz), read lazily -- a book file is large."""
    for p in (path, path + ".gz"):
        if os.path.exists(p):
            op = gzip.open if p.endswith(".gz") else open
            with op(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(r, dict):
                        return r
    return None


def _surface_expiry(data, idx, day):
    """The option expiry the recorder resolved that day, from data/surface/surface_<day>.jsonl (stamped from 24 Aug) --
    the fallback for chain rows recorded before the chain carried `expiry` (before ~23 Sep). Read, never computed from a
    weekday (upstox_instruments: both indices' weekdays have moved before)."""
    path = os.path.join(data, "surface", f"surface_{day}.jsonl")
    for p in (path, path + ".gz"):
        if os.path.exists(p):
            op = gzip.open if p.endswith(".gz") else open
            with op(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(r, dict) and r.get("idx") == idx and r.get("expiry"):
                        return r["expiry"]
    return None


def _chain_x(data, idx, day):
    """THE READ's arrays for a recorded chain day (v2feed.IdxState fed the chain rows only, exactly as live -- the REST
    backfill prepended when its file exists), or None."""
    import read
    import v2feed
    s = v2feed.IdxState(idx, day, data)
    try:
        rows = s.chain.rows()
    except v2feed.Reset:
        return None
    for r in rows:
        s._chain_row(r)
    return read.from_v2(s, v2feed.LOTS.get(idx)) if s.t else None


def read_ref(data, idx, before):
    """The `read` section: THE READ's numbers' references for one index from days < before (rank.py's definitions).
    marks.<src>.<metric>.<mark sec> = one value per reference day (aligned with marks.<src>.days); pool.<kind>.<src>
    .<metric> = one table per day-part; slot.<kind>.<src> = the same-15-min-slot median |delta| (the live SIZE)."""
    if HERE not in sys.path:                      # run as a script, tools/ is sys.path[0]; rank.py lives in tapemap/
        sys.path.insert(0, HERE)
    import rank as R
    bm = R.BAR_MIN.get(idx, 5)
    why, kinds, meta = {}, {}, {}
    days5, daysb = {}, {}
    for src, prefix in (("ux", f"ux_{idx}_"), ("gc", f"tape_{idx}_")):
        ds = _days(data, "tape", prefix, before)
        d5 = {d: R.bars_of(_rows(os.path.join(data, "tape", f"{prefix}{d}.jsonl")), 5) for d in ds}
        d5 = {d: b for d, b in d5.items() if b}
        if d5:
            days5[src] = d5
            daysb[src] = d5 if bm == 5 else {d: R._agg(bs, bm) for d, bs in d5.items()}
        else:
            why[f"read.{src}"] = f"no {src.upper()} bar day before {before}"
    chain = {}
    for d in _days(data, "chain", f"chain_{idx}_", before):
        X = _chain_x(data, idx, d)
        if X is not None:
            chain[d] = (X, R.chain_marks(X))
    if not chain:
        why["read.chain"] = f"no chain day before {before}"
    alldays = sorted(set(chain) | {d for v in days5.values() for d in v})
    last_ik = None
    for d in alldays:                                       # the day kind: option expiry (chain), future (book / ux)
        bk = _first_row(os.path.join(data, "book", f"book_{idx}_{d}.jsonl")) or {}
        ux = (_rows(os.path.join(data, "tape", f"ux_{idx}_{d}.jsonl")) or [{}])[0] if d in days5.get("ux", {}) else {}
        ik, fx = bk.get("ik") or ux.get("ik"), bk.get("expiry") or ux.get("expiry")
        ex = ((chain[d][0].get("expiry") if d in chain else None)
              or (_first_row(os.path.join(data, "chain", f"chain_{idx}_{d}.jsonl")) or {}).get("expiry")
              or _surface_expiry(data, idx, d))
        kinds[d] = R.day_kind(d, ex, fx, ik, last_ik)
        last_ik = ik or last_ik
    marks = {}
    for src, d5 in days5.items():
        ds = sorted(d5)
        fm = {d: R.flow_marks(d5[d]) for d in ds}
        allm = sorted({m for v in fm.values() for m in v})
        marks[src] = {"days": ds, **{k: {str(m): [((fm[d].get(m) or {}).get(k)) for d in ds] for m in allm}
                                     for k in (("cvd", "vol", "x") if src == "ux" else ("cvd", "vol"))}}
    if chain:
        ds = sorted(chain)
        allm = sorted({m for _, cm in chain.values() for m in cm})
        marks["chain"] = {"days": ds, **{k: {str(m): [((chain[d][1].get(m) or {}).get(k)) for d in ds] for m in allm}
                                         for k in ("ce", "pe", "A")}}
    samples = {src: R.bar_samples(days5[src], daysb[src]) for src in days5}
    samples["chain"] = {d: {k: [(R.part_of(m - 1), v[k]) for m, v in cm.items()
                                if v.get(k) is not None and R.part_of(m - 1) is not None] for k in ("ce30", "pe30")}
                        for d, (_, cm) in chain.items()}
    pools, slots = {}, {}
    for kind in ("NORMAL", "EXPIRY", "ROLL"):
        keep = [d for d in alldays if kinds.get(d) == kind]
        pools[kind] = {src: R.pool(smp, keep) for src, smp in samples.items()}
        slots[kind] = {src: R.slot_medians({d: bs for d, bs in daysb[src].items() if d in keep}) for src in daysb}
    return {"v": 1, "parts": [list(p) for p in R.PARTS], "bar_min": bm, "kinds": kinds, "last_ik": last_ik,
            "marks": marks, "pool": pools, "slot": slots, "why": why}


def build(idx, before, data_dir=None):
    """The reference as of `before` (YYYY-MM-DD) for one index -> dict. Reads only days < before."""
    data = data_dir or DATA
    why = {}
    gdays = _days(data, "tape", f"tape_{idx}_", before)
    gc = {d: gc_bars(data, idx, d) for d in gdays}
    gc = {d: b for d, b in gc.items() if b}
    wall, crosses = {}, {}
    for C in CHECKPOINTS:
        ws, cs, nw, nc = [], [], 0, 0
        for bars in gc.values():
            if _covered(bars, C, lambda b: isinstance(b.get("ladder"), list) and b["ladder"]):
                ws += wall_values(bars, C)
                nw += 1
            if _covered(bars, C, lambda b: b.get("c") is not None):
                cs.append(sum(1 for e in cross_closes(bars) if e <= C))
                nc += 1
        wall[str(C)], crosses[str(C)] = quant(ws), quant(cs)
        if wall[str(C)]:
            wall[str(C)]["n_days"] = nw
        else:
            why[f"wall_bin.{C}"] = f"no reference day with >= {COVER:.0%} of its 5-min ladders 09:20-{C // 60:02d}:{C % 60:02d}"
        if crosses[str(C)]:
            crosses[str(C)]["n_days"] = nc
        else:
            why[f"crosses.{C}"] = f"no reference day with >= {COVER:.0%} of its 5-min closes 09:20-{C // 60:02d}:{C % 60:02d}"
    of = []
    for bars in gc.values():
        six = [b for b in bars if OPEN_M <= b["m"] <= OPEN_M + 25]
        if len(six) == 6 and all(isinstance(b.get("delta"), (int, float)) for b in six):
            of.append(abs(sum(b["delta"] for b in six)))
    fuel = [x for bars in gc.values() for x in fuel_values(bars)]
    flow = flow_ref(gc)
    w30, w30_days = writers30(data, idx, before)
    marks = marks_ref(data, idx, before)
    sr_src, sr_days = "gc", gc                   # A45: the extension's own bars (GoCharting); Upstox where it has none
    if not gc:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import rank as R
        sr_src = "ux"
        sr_days = {d: R.bars_of(_rows(os.path.join(data, "tape", f"ux_{idx}_{d}.jsonl")), 5)
                   for d in _days(data, "tape", f"ux_{idx}_", before)}
    body = {"v": V, "idx": idx, "before": before, "days": sorted(gc), "wall_bin": wall, "crosses": crosses,
            "open_flow": quant(of), "fuel": quant(fuel), "flow": flow, "marks": marks, "writers30": w30,
            "slot_range": slot_range(sr_days), "slot_range_src": sr_src, "read": read_ref(data, idx, before)}
    if not body["slot_range"]:
        why["slot_range"] = f"no {sr_src} 5-min bar with a high and a low before {before}"
    for k, tab in (("open_flow", body["open_flow"]), ("fuel", body["fuel"]), ("writers30", w30),
                   ("flow.size", flow["size"]), ("flow.share", flow["share"]), ("flow.rv12", flow["rv12"])):
        if not tab:
            why[k] = {"open_flow": "no reference day with all six 09:15-09:40 bars",
                      "fuel": "no 25-pt leg with futures OI at both ends",
                      "writers30": f"no usable chain checkpoint on {', '.join(w30_days) or 'any chain day'}"}.get(
                k, f"fewer than {FLOW_MIN_BARS} usable GoCharting bars on every reference day")
    for k in BOARD_KINDS + DEC_KINDS + ("exhaustion_fade",):
        if not marks[k]:
            why[f"marks.{k}"] = f"no era-B ({ERA_B} on) {k} before {before}"
    if not gc:
        why["days"] = f"no GoCharting tape day before {before}"
    body["why"] = why
    sha = hashlib.sha1(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:8]
    return dict(body, id=f"rank-{idx}-{before}-{sha}",
                built_at=datetime.datetime.now(IST).isoformat(timespec="seconds"))


def path_for(out_dir, idx, before):
    return os.path.join(out_dir, f"rank_ref_{idx}_{before}.json")


def write(ref, out_dir):
    """Atomic: a reader never sees half a file."""
    os.makedirs(out_dir, exist_ok=True)
    p = path_for(out_dir, ref["idx"], ref["before"])
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ref, f, separators=(",", ":"))
    os.replace(tmp, p)
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--idx", default="NIFTY")
    ap.add_argument("--before", default=datetime.datetime.now(IST).strftime("%Y-%m-%d"))
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    ref = build(a.idx, a.before, a.data)
    p = write(ref, a.out or os.path.join(a.data, "rank"))
    print(p, ref["id"], "days", len(ref["days"]), "why", json.dumps(ref["why"], ensure_ascii=False))


if __name__ == "__main__":
    main()
