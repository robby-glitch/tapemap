"""dream_facts.py -- READ-ONLY extraction of one NIFTY session for the DREAM TOOL mockup (docs/dream-tool/BRIEF.md).

Usage:  python dream_facts.py YYYY-MM-DD          -> writes facts_<day>.json beside this file (nothing under data/ is written)

What it pulls, all from the recorders' files, each series keyed so the brain (dream_build.py) can cut it CAUSALLY at any
replayed minute: nothing here is a decision, and nothing is invented.
  bars5     GoCharting 5-min footprint bars (o h l c buy sell delta vol) + the Upstox bar's fut OI at the close, the chain's
            spot at the close, the bar's basis, prints.bar_flags (stacked imbalances, unfinished auction, POC), the largest
            single-price print, 5-pt volume bins (for the developing profile)
  ones      the exchange's 1-min futures candles (data/backtest/fut_<day>.json): the forming bar, 1-min OI
  flow1     1-min buy / sell lots from the Upstox book (confluence.book_flow, ladder-sided [I])
  spot      the chain's spot per minute (NIFTY, BANKNIFTY, SENSEX)
  writers   per minute, per index: aaj likha CE / PE lots on the nine strikes ATM +/- 4 (read.py's window), the PE lead %,
            the top-OI strike per side (floor / ceiling), max pain, and fronts.read's top-2 fronts per side with state
  bars3     3-min futures bars with HER chart's bands (ZONE-3M, contract_bars on 3-min bars) and the zone machine's arms,
            re-arms, entries and stops on them (band_rotation.run_states, both sides)
  vpin      vpin_fast rows (per 20k-unit bucket, with the session percentile)
  effort    effort.py's lambda (lots per point) reads at fresh extremes (Fable's survivor definition)
  xi        xindex.py's 3-min cross-index read (sync, extremes, lead, walls, per-index word)
  legs      reader.py's confirmed 1-min legs and auction events, with the time each was KNOWN (`at`)
  marks     the extension's chart marks (ofd_marks2: ROKA / THAKAN / PHANSE / ZOR / KHALI; v1 marks on older days)
  events    the decoder's E1..E7 (BADA PRINT, PEHAL, DABAAV, DHER, KHULA, THAKAAN, CVD ulta)
  onesided  §1o's day type at every 5-min close (onesided.meter, causal `upto`)
  levels    PDH / PDL / PDC / PWH / PWL / PMH / PML / PMC in spot (chain spot <= 15:15) and futures (exchange candles),
            OPEN, prior-day POC / VAH / VAL / HVN / LVN (futures, the prior tape day's ladders), round numbers
"""
import bisect
import json
import os
import statistics
import sys
from datetime import date, timedelta

TAPE = r"C:\Users\kaam\Desktop\operator mode\tapemap"
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(TAPE)
sys.path.insert(0, TAPE)
import band_rotation      # noqa: E402
import book_log           # noqa: E402
import confluence         # noqa: E402
import confluence_log     # noqa: E402
import contract_bars      # noqa: E402
import effort             # noqa: E402
import fronts             # noqa: E402
import onesided           # noqa: E402
import prints             # noqa: E402
import v2feed             # noqa: E402

DAY = sys.argv[1]
IDX, PEERS = "NIFTY", ("BANKNIFTY", "SENSEX")
LOT = v2feed.LOTS
STEP = {"NIFTY": 50, "BANKNIFTY": 100, "SENSEX": 100}
ROW = 5.0                                  # the footprint row (server.py:1412's default rowSize)
OPEN_M, CLOSE_M, FREEZE_M = 9 * 60 + 15, 15 * 60 + 30, 15 * 60 + 15
CACHE = os.path.join(HERE, "levels_cache.json")


def sec_of(ms):
    return int(ms // 1000 + 19800) % 86400


def hm(m):
    return f"{int(m) // 60:02d}:{int(m) % 60:02d}"


def mins(s):
    return int(s[:2]) * 60 + int(s[3:5])


def rows_of(path):
    return list(confluence_log._rows(path))


# ---- the chain: spot, writers, fronts ---------------------------------------------------------------------------------
def chain(idx, day):
    return [r for r in rows_of(confluence_log._chain_path(idx, day))
            if r.get("spot") is not None and isinstance(r.get("ts"), str) and "09:15:00" <= r["ts"] <= "15:30:00"]


def per_minute_spot(rows):
    out = {}
    for r in rows:
        out[mins(r["ts"])] = r["spot"]
    return out


def writers_series(rows, idx):
    """Per minute (the minute's last snapshot): the nine strikes' aaj likha per side, lead %, floor / ceiling, max pain."""
    base, out, step, lot = {}, {}, STEP[idx], LOT[idx]
    for r in rows:
        m = mins(r["ts"])
        ks = sorted(s["k"] for s in r["strikes"] if s.get("k") is not None)
        if not ks:
            continue
        by = {s["k"]: s for s in r["strikes"]}
        for k, s in by.items():
            for side in ("ce", "pe"):
                leg = s.get(side) or {}
                if leg.get("oi") is not None and (k, side) not in base:
                    base[(k, side)] = leg["oi"] - (leg.get("oi_chg") or 0)
        atm = min(ks, key=lambda k: abs(k - r["spot"]))
        i = ks.index(atm)
        nine = ks[max(0, i - 4): i + 5]
        ce = pe = 0.0
        for k in nine:
            s = by[k]
            if (s.get("ce") or {}).get("oi") is not None and (k, "ce") in base:
                ce += s["ce"]["oi"] - base[(k, "ce")]
            if (s.get("pe") or {}).get("oi") is not None and (k, "pe") in base:
                pe += s["pe"]["oi"] - base[(k, "pe")]
        tot = abs(ce) + abs(pe)
        # floor / ceiling: the heaviest absolute OI per side among ATM +/- 8 (the recorder's window)
        fl = max(ks, key=lambda k: (by[k].get("pe") or {}).get("oi") or 0)
        ce_w = max(ks, key=lambda k: (by[k].get("ce") or {}).get("oi") or 0)
        # max pain over the recorded strikes
        best, bp = None, None
        for k in ks:
            pain = sum(max(0, k - j) * ((by[j].get("pe") or {}).get("oi") or 0) + max(0, j - k) * ((by[j].get("ce") or {}).get("oi") or 0)
                       for j in ks)
            if bp is None or pain < bp:
                best, bp = k, pain
        out[m] = {"ce": round(ce / lot), "pe": round(pe / lot), "lead": round(100.0 * (pe - ce) / tot, 1) if tot else None,
                  "atm": atm, "nine": [nine[0], nine[-1]], "floor": fl, "floor_oi": round(((by[fl].get("pe") or {}).get("oi") or 0) / lot),
                  "ceil": ce_w, "ceil_oi": round(((by[ce_w].get("ce") or {}).get("oi") or 0) / lot), "maxpain": best}
    return out


def fronts_series(rows, every=1):
    """fronts.read at every `every`-th minute on the grid cut there (causal), with the session-peak OI as at that minute."""
    minutes, peaks = confluence.chain_grid(rows)
    ts = sorted(minutes)
    out, cut = {}, {}
    for j, t in enumerate(ts):
        cut[t] = minutes[t]
        if j % every and j != len(ts) - 1:
            continue
        fr = fronts.read(cut, peaks.get(t))
        out[mins(t)] = [{"k": f["k"], "side": f["side"], "state": f["state"], "chg": round(f["chg"]), "peak": round(f["peak"]),
                         "peak_at": f["peak_at"], "slope": round(f["slope"]), "oi": f["oi"]} for f in fr]
    return out


# ---- bars -----------------------------------------------------------------------------------------------------------------
def fut1(day):
    p = os.path.join("data", "backtest", f"fut_{day}.json")
    if not os.path.exists(p):
        return []
    d = json.load(open(p, encoding="utf-8"))
    out = []
    for i, ts in enumerate(d["timestamp"]):
        m = int(ts + 19800) % 86400 // 60
        if OPEN_M <= m < CLOSE_M:
            out.append({"m": m, "o": d["open"][i], "h": d["high"][i], "l": d["low"][i], "c": d["close"][i],
                        "v": d["volume"][i], "oi": d["open_interest"][i]})
    return out


def tape5(day, ones):
    raw = rows_of(os.path.join("data", "tape", f"tape_{IDX}_{day}.jsonl"))
    by = {}
    for b in raw:
        m = sec_of(b["t"]) // 60
        if OPEN_M <= m < CLOSE_M:
            by[m - (m - OPEN_M) % 5] = b          # the last copy of a re-written bar wins
    o1 = {x["m"]: x for x in ones}
    # a slot GoCharting never sent is filled from the Upstox bar (its own ladder and delta), tagged src "ux"
    uxb = {}
    for b in rows_of(os.path.join("data", "tape", f"ux_{IDX}_{day}.jsonl")):
        m = sec_of(b["t"]) // 60
        if OPEN_M <= m < CLOSE_M:
            uxb[m - (m - OPEN_M) % 5] = b
    for m, b in uxb.items():
        if m not in by and b.get("h") is not None:
            by[m] = dict(b, src="ux")
    out = []
    for m in sorted(by):
        b = by[m]
        win = [o1[k] for k in range(m, m + 5) if k in o1]
        o = b.get("o") if b.get("o") is not None else (win[0]["o"] if win else None)
        c = b.get("c") if b.get("c") is not None else (win[-1]["c"] if win else None)
        lad = b.get("ladder") or []
        f = prints.bar_flags(b, ROW) or {}
        big = max(lad, key=lambda r: max(r.get("b") or 0, r.get("s") or 0), default=None)
        bins = {}
        for r in lad:
            k = prints._jsround(float(r["p"]) / 5) * 5
            bins[k] = bins.get(k, 0) + (r.get("b") or 0) + (r.get("s") or 0)
        out.append({"m": m, "t": hm(m), "o": o, "h": b["h"], "l": b["l"], "c": c, "buy": b.get("buy"), "sell": b.get("sell"),
                    "delta": b.get("delta"), "vol": b.get("vol"), "src": b.get("src") or "gc", "oc_fill": b.get("o") is None,
                    "stacks": [{"p": s.get("high") if s.get("side") == "buy" else s.get("low"), "side": 1 if s.get("side") == "buy" else -1,
                                "n": s.get("run"), "lo": s.get("low"), "hi": s.get("high")} for s in (f.get("stacks") or []) if isinstance(s, dict)],
                    "unf_hi": f.get("unfinished_high"), "unf_lo": f.get("unfinished_low"), "poc": f.get("poc"),
                    "big": {"p": big["p"], "lots": int(max(big.get("b") or 0, big.get("s") or 0)),
                            "side": 1 if (big.get("b") or 0) >= (big.get("s") or 0) else -1} if big else None,
                    "bins": sorted(bins.items())})
    return out


def ux5(idx, day):
    out = []
    for b in rows_of(os.path.join("data", "tape", f"ux_{idx}_{day}.jsonl")):
        m = sec_of(b["t"]) // 60
        if OPEN_M <= m < CLOSE_M:
            out.append({"m": m, "t": hm(m), "o": b.get("o"), "h": b.get("h"), "l": b.get("l"), "c": b.get("c"),
                        "delta": b.get("delta"), "vol": b.get("vol"), "oi": b.get("oi")})
    by = {}
    for b in out:
        by[b["m"]] = b
    return [by[m] for m in sorted(by)]


def zone(day):
    band_rotation.ZONE3_FROM = day
    sess = (confluence_log.session(IDX, day) or {}).get("bars") or []
    z = contract_bars.with_bands(sess, contract_bars.bands_on(sess))
    bars3 = [{"t": b["t"], "o": b.get("o"), "h": b.get("h"), "l": b.get("l"), "c": b.get("c"), "v": b.get("v"), "oi": b.get("oi"),
              **{k: round(b[k], 2) for k in ("vwap", "u1", "u2", "u3", "d1", "d2", "d3") if b.get(k) is not None}} for b in z]
    eps = []
    for side, band in (("BUY", "d2"), ("SELL", "u2")):
        st = band_rotation.run_states(z, stop_pts=band_rotation.OPERATOR_STOP_PTS, side=side, band=band, span=confluence.INTERVAL)
        cur = None
        for s in st:
            a, e = s.get("arm"), s.get("entry")
            if a:
                if not a.get("rearm") or cur is None or cur["first_t"] != a["first_t"]:
                    cur = {"side": side, "band": band, "first_t": a["first_t"], "arms": [], "entry": None, "until": s["t"]}
                    eps.append(cur)
                cur["arms"].append({"t": s["t"], "level": round(s["level"], 2), "stop": round(s["stop"], 2),
                                    "extreme": a.get("extreme"), "rearm": bool(a.get("rearm"))})
            if cur is not None and cur["entry"] is None:
                if s["state"] == "ARMED":
                    cur["until"] = s["t"]                    # the machine's own expiry: candles_left runs to 0
                elif not e:
                    cur = None
            if e and cur is not None and cur["entry"] is None:
                cur["entry"] = {"t": e["t"], "E": confluence.flat(z[e["i"]]).get("c"), "stop": round(e["stop"], 2),
                                "level": round(s["level"], 2), "trigger": e.get("trigger")}
                cur = None
    eps.sort(key=lambda x: x["first_t"])
    return bars3, eps


# ---- the book: 1-min flow and effort ----------------------------------------------------------------------------------------
def book(day, spot_min):
    rows = list(book_log.read_rows(day, IDX))
    tick = None
    for r in rows_of(os.path.join("data", "tape", f"ux_{IDX}_{day}.jsonl")):
        if r.get("tick"):
            tick = r["tick"]
            break
    flow, seen, bad = confluence.book_flow(rows, tick)
    lot = LOT[IDX]
    flow1 = {m: [round(v[0] / lot), round(v[1] / lot)] for m, v in flow.items() if OPEN_M <= m < CLOSE_M}
    fm = effort.minutes(rows, lot)
    sp = {m: spot_min[m] for m in spot_min}
    ev = effort.events(fm, sp, STEP[IDX])
    lam = {}
    for c in range(OPEN_M + 5, CLOSE_M + 1, 5):
        l, med, n = effort.lam_at(fm, c - 1)
        if l is not None:
            lam[c] = {"lpp": round(l, 1), "med": None if med is None else round(med, 1), "n": n}
    ltp = {}                                                   # the futures LTP per second (the book's own rows)
    for r in rows:
        if r.get("ltp") is not None and isinstance(r.get("t"), (int, float)):
            ltp[int(r["t"] / 1000 + 19800) % 86400] = r["ltp"]
    return flow1, sorted(bad), [{"m": m, "ext": k, "band": band} for m, k, band in ev], lam, ltp


# ---- the rest of the record --------------------------------------------------------------------------------------------------
def vpin(day):
    return [{"m": mins(r["at"]), "s": r["at"], "vpin": r["vpin"], "pct": r.get("pct")}
            for r in rows_of(os.path.join("data", "vpin_fast.jsonl")) if r.get("day") == day and r.get("inst") == "NIFTY-FUT:fast"]


def xindex(day):
    out = []
    for r in rows_of(os.path.join("data", "xindex", f"xindex_{day}.jsonl")):
        o = r.get("out") or {}
        if not o.get("idx"):
            continue
        row = {"t": r["t"], "at": sec_of(r["at"]) if r.get("at") else None, "sync": {k: (o.get("sync") or {}).get(k) for k in ("state", "key", "chip", "dots")},
               "ext": None, "lead": (o.get("lead") or {}).get("chip"), "walls": {}, "idx": {}}
        ex = o.get("extremes") or {}
        for kind in ("high", "low"):
            e = ex.get(kind)
            if e:
                row["ext"] = {"type": kind, "verdict": e.get("verdict"), "chip": e.get("chip"),
                              "per": {i: {"status": v.get("status"), "px": v.get("px"), "t": v.get("t")} for i, v in (e.get("per") or {}).items()}}
        for i, w in ((o.get("walls") or {}).get("per") or {}).items():
            w = w or {}
            row["walls"][i] = {"vote": w.get("vote"), "why": w.get("why"), "ce": w.get("ce"), "pe": w.get("pe")}
        for i, v in o["idx"].items():
            v = v or {}
            row["idx"][i] = {"D": v.get("D"), "word": v.get("word"), "chip": v.get("chip"), "n_for": v.get("n_for"),
                             "n_against": v.get("n_against"), "zone_in": v.get("zone_in")}
        out.append(row)
    return out


def reader(idx, day):
    legs, auction, seen = [], [], set()
    for r in rows_of(os.path.join("data", "reader", f"reader_{idx}_{day}.jsonl")):
        e = r.get("event") or {}
        at = sec_of(r["at"]) if r.get("at") else None
        if e.get("kind") == "leg" and r.get("leg"):
            L = r["leg"]
            if L.get("id") in seen:
                continue
            seen.add(L.get("id"))
            legs.append({"id": L.get("id"), "at": at, "t0": sec_of(L["t0"]) // 60, "t1": sec_of(L["t1"]) // 60, "dir": L.get("dir"),
                         "px0": L.get("px0"), "px1": L.get("px1"), "pts": L.get("pts"), "mins": L.get("mins"),
                         "who": (L.get("who") or {}).get("class"), "who_chip": (L.get("who") or {}).get("chip"),
                         "absorbed": (L.get("who") or {}).get("absorbed"), "ux_d": (L.get("ux") or {}).get("d"),
                         "oi_d": (L.get("oi") or {}).get("d"), "chip": e.get("chip")})
        elif e.get("kind") == "auction":
            auction.append({"at": at, "t": sec_of(e["t"]) // 60 if e.get("t") else None, "state": e.get("state"), "chip": e.get("chip")})
    return legs, auction


def marks(day):
    p2 = os.path.join("data", "tape", f"ofd_marks2_{IDX}_{day}.jsonl")
    out = {}
    if os.path.exists(p2):
        for r in rows_of(p2):
            if r.get("kind") in ("E1", "E2", "E3", "E4", "E5", "E6", "E7"):
                continue
            k = r.get("id") or f"{r['kind']}@{r['t']}@{r['p']}"
            m = sec_of(r["t"]) // 60
            o = out.setdefault(k, {"m": m, "t": hm(m), "kind": r["kind"], "name": r.get("name"), "p": r["p"], "lots": r.get("lots") or 0,
                                   "side": r.get("winner"), "broke_m": None, "break_px": None, "src": "ext2"})
            if r.get("status") == "TOOTA" and r.get("status_t"):
                bm = sec_of(r["status_t"]) // 60
                if o["broke_m"] is None or bm < o["broke_m"]:
                    o["broke_m"], o["break_px"] = bm, r.get("break_px")
        return sorted(out.values(), key=lambda x: (x["m"], x["kind"]))
    NAME = {"absorption": "ROKA", "exhaustion": "THAKAN", "trap": "PHANSE", "initiative": "ZOR", "vacuum": "KHALI", "climax": "CLIMAX"}
    rows = rows_of(os.path.join("data", "tape", f"ofd_marks_{IDX}_{day}.jsonl"))
    for r in rows:
        m = sec_of(r["t"]) // 60
        k = f"{r['kind']}@{r['t']}@{r['p']}"
        out[k] = {"m": m, "t": hm(m), "kind": r["kind"], "name": f"{'▲' if r.get('side', 0) > 0 else '▼'} {NAME.get(r['kind'], r['kind'])}",
                  "p": r["p"], "lots": r.get("size") or 0, "side": r.get("side"), "broke_m": None, "break_px": None, "src": "ext1"}
    return sorted(out.values(), key=lambda x: (x["m"], x["kind"]))


def decoder_events(day):
    out = []
    for r in rows_of(os.path.join("data", "decoder", f"decoder_{day}.jsonl")):
        if r.get("row") != "event" or r.get("idx") != IDX:
            continue
        e = r["event"]
        out.append({"kind": e.get("kind"), "name": e.get("name"), "m": sec_of(e["t"]) // 60, "at": int(r["at"] + 19800) % 86400 if r.get("at") else None,
                    "p": e.get("p"), "side": e.get("side"), "lots": e.get("lots"), "chip": e.get("chip"), "at_kind": (e.get("at") or {}).get("name")})
    return out


# ---- levels ---------------------------------------------------------------------------------------------------------------------
def day_levels(day):
    """{h, l, c15, open} in spot from the chain (<= 15:15, the CAS rule) and {fh, fl, fc, fo} from the exchange's candles."""
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    if day in cache:
        return cache[day]
    rows = chain(IDX, day)
    sp = [(r["ts"], r["spot"]) for r in rows if r["ts"] <= "15:15:00"]
    o1 = fut1(day)
    rec = {"h": max(v for _, v in sp) if sp else None, "l": min(v for _, v in sp) if sp else None, "c15": sp[-1][1] if sp else None,
           "open": sp[0][1] if sp else None, "n": len(sp),
           "fh": max(x["h"] for x in o1) if o1 else None, "fl": min(x["l"] for x in o1) if o1 else None,
           "fc": o1[-1]["c"] if o1 else None, "fo": o1[0]["o"] if o1 else None}
    cache[day] = rec
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), indent=0)
    return rec


def recorded_days():
    out = set()
    for f in os.listdir(os.path.join("data", "chain")):
        if f.startswith(f"chain_{IDX}_"):
            out.add(f[len(f"chain_{IDX}_"):][:10])
    return sorted(out)


def levels(day, prev_tape_day):
    days = [d for d in recorded_days() if d < day]
    d0 = date.fromisoformat(day)
    out, why = [], []
    if not days:
        return out, ["no recorded session before this day"]
    pd_ = days[-1]
    L = day_levels(pd_)
    for kind, key, fr in (("PDH", "h", "s"), ("PDL", "l", "s"), ("PDC", "c15", "s"), ("PDH", "fh", "f"), ("PDL", "fl", "f"), ("PDC", "fc", "f")):
        if L.get(key) is not None:
            out.append({"kind": kind, "px": L[key], "fr": fr, "src": pd_, "tag": "M"})
    if (d0 - date.fromisoformat(pd_)).days > 4:
        why.append(f"prior session is {pd_}: the record has a hole before {day}")
    # the prior ISO week
    mon = d0 - timedelta(days=d0.weekday())
    wk = [d for d in days if mon - timedelta(days=7) <= date.fromisoformat(d) < mon]
    if wk:
        Ls = [day_levels(d) for d in wk]
        hs, ls = [x["h"] for x in Ls if x.get("h")], [x["l"] for x in Ls if x.get("l")]
        fhs, fls = [x["fh"] for x in Ls if x.get("fh")], [x["fl"] for x in Ls if x.get("fl")]
        if hs:
            out += [{"kind": "PWH", "px": max(hs), "fr": "s", "src": f"{wk[0]}..{wk[-1]} ({len(wk)}d)", "tag": "M"},
                    {"kind": "PWL", "px": min(ls), "fr": "s", "src": f"{wk[0]}..{wk[-1]} ({len(wk)}d)", "tag": "M"}]
        if fhs:
            out += [{"kind": "PWH", "px": max(fhs), "fr": "f", "src": f"{wk[0]}..{wk[-1]}", "tag": "M"},
                    {"kind": "PWL", "px": min(fls), "fr": "f", "src": f"{wk[0]}..{wk[-1]}", "tag": "M"}]
        if len(wk) < 5:
            why.append(f"prior week has {len(wk)} recorded sessions")
    else:
        why.append("no recorded session in the prior week")
    # the prior calendar month (recorded sessions only; levels.py has no monthly fetch -- the gap is named in DESIGN.md)
    pm_last = d0.replace(day=1) - timedelta(days=1)
    pm_first = pm_last.replace(day=1)
    mo = [d for d in days if pm_first <= date.fromisoformat(d) <= pm_last]
    if mo:
        Ls = [day_levels(d) for d in mo]
        hs, ls = [x["h"] for x in Ls if x.get("h")], [x["l"] for x in Ls if x.get("l")]
        if hs:
            out += [{"kind": "PMH", "px": max(hs), "fr": "s", "src": f"{pm_first:%b} ({len(mo)}d recorded)", "tag": "M"},
                    {"kind": "PML", "px": min(ls), "fr": "s", "src": f"{pm_first:%b} ({len(mo)}d recorded)", "tag": "M"},
                    {"kind": "PMC", "px": Ls[-1]["c15"], "fr": "s", "src": mo[-1], "tag": "M"}]
        why.append(f"prior month = {len(mo)} recorded sessions of ~22: PMH/PML may miss unrecorded days")
    else:
        why.append("no recorded session in the prior month")
    # the prior tape day's profile (futures)
    if prev_tape_day:
        raw = rows_of(os.path.join("data", "tape", f"tape_{IDX}_{prev_tape_day}.jsonl"))
        by = {}
        for b in raw:
            m = sec_of(b["t"]) // 60
            if OPEN_M <= m < CLOSE_M:
                by[m - (m - OPEN_M) % 5] = b
        prof = prints.profile(list(by.values()))
        if prof:
            out += [{"kind": "pPOC", "px": prof["poc"], "fr": "f", "src": prev_tape_day, "tag": "M"},
                    {"kind": "pVAH", "px": prof["vah"], "fr": "f", "src": prev_tape_day, "tag": "M"},
                    {"kind": "pVAL", "px": prof["val"], "fr": "f", "src": prev_tape_day, "tag": "M"}]
            for n in prints.nodes(prof):
                out.append({"kind": "p" + n["kind"], "px": n["p"], "fr": "f", "src": prev_tape_day, "tag": "M", "vol": n["vol"]})
    return out, why


# ---- main ---------------------------------------------------------------------------------------------------------------------
def main():
    ones = fut1(DAY)
    bars5 = tape5(DAY, ones)
    ux = {IDX: ux5(IDX, DAY)}
    for p in PEERS:
        ux[p] = ux5(p, DAY)
    rows = {IDX: chain(IDX, DAY)}
    for p in PEERS:
        rows[p] = chain(p, DAY)
    spot = {i: per_minute_spot(rows[i]) for i in rows}
    wr = {i: writers_series(rows[i], i) for i in rows}
    fr = {IDX: fronts_series(rows[IDX], 1)}
    for p in PEERS:
        fr[p] = fronts_series(rows[p], 5)
    # the bar's fut OI (Upstox bar), spot and basis at the close
    uxb = {b["m"]: b for b in ux[IDX]}
    o1 = {x["m"]: x for x in ones}
    for b in bars5:
        u = uxb.get(b["m"])
        last1 = o1.get(b["m"] + 4)
        b["oi"] = (last1["oi"] if last1 else None) or (u["oi"] if u else None)
        b["ux_delta"] = u["delta"] if u else None
        sm = max((m for m in spot[IDX] if m <= b["m"] + 4), default=None)
        b["spot"] = spot[IDX].get(sm)
        b["basis"] = round(b["c"] - b["spot"], 1) if b.get("c") is not None and b.get("spot") is not None else None
    bars3, eps = zone(DAY)
    flow1, holes, eff_ev, lam, ltp_sec = book(DAY, spot[IDX])
    # the raw basis per chain snapshot: fut LTP at (or just before) the snapshot's second minus its spot -- fold.BIX_MS's
    # 3-min median runs over these samples in dream_build
    secs = sorted(ltp_sec)
    bsnap = []
    for r in rows[IDX]:
        i = bisect.bisect_right(secs, r["sec"]) - 1
        if i >= 0 and r["sec"] - secs[i] <= 5:
            bsnap.append([r["sec"], round(ltp_sec[secs[i]] - r["spot"], 2)])
    legs, auction = reader(IDX, DAY)
    peer_legs = {p: reader(p, DAY)[0] for p in PEERS}
    # §1o at every close: l5 / l15 from the nine's lead %
    def lead_at(m):
        k = max((x for x in wr[IDX] if x <= m), default=None)
        return (wr[IDX][k]["lead"] if k is not None and m - k <= fronts.STALE_MIN else None)
    closes = [b["m"] + 5 for b in bars5]
    l5 = {c: {"pe": lead_at(c)} for c in closes}
    l15 = {c: ({"chg": lead_at(c) - lead_at(c - 15)} if lead_at(c) is not None and lead_at(c - 15) is not None else None) for c in closes}
    ob = [{"s": b["m"] * 60, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "vol": b["vol"], "delta": b["delta"], "oi": b["oi"]} for b in bars5]
    pb = [[{"s": b["m"] * 60, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "vol": b["vol"], "delta": b["delta"], "oi": b["oi"]} for b in ux[p]] for p in PEERS]
    ones_ = []
    for c in closes:
        try:
            r = onesided.meter(ob, l5, l15, pb, upto=c * 60)
        except Exception as e:                       # a day that cannot be read says so
            r = {"type": None, "why": str(e)}
        ones_.append({"c": c, "type": r.get("type"), "why": r.get("why"), "up": r.get("up"), "down": r.get("down"),
                      "flips": r.get("flips"), "crosses": r.get("crosses"), "strip": r.get("strip")})
    days_tape = sorted(f[len(f"tape_{IDX}_"):][:10] for f in os.listdir(os.path.join("data", "tape")) if f.startswith(f"tape_{IDX}_"))
    prev_tape = max((d for d in days_tape if d < DAY), default=None)
    lv, lv_why = levels(DAY, prev_tape)
    exp = None
    try:
        exp = (confluence_log.session(IDX, DAY) or {}).get("expiry")
    except Exception:
        pass
    out = {"day": DAY, "idx": IDX, "lot": LOT, "expiry": exp, "roll": DAY in ("2026-10-21", "2026-10-22", "2026-10-23", "2026-10-26"),
           "bars5": bars5, "ones": ones, "flow1": flow1, "flow_holes": holes, "spot": spot, "writers": wr, "fronts": fr,
           "peers5": {p: ux[p] for p in PEERS}, "basis_snap": bsnap, "bars3": bars3, "zone": eps, "vpin": vpin(DAY), "effort": {"events": eff_ev, "lam": lam},
           "xi": xindex(DAY), "legs": legs, "auction": auction, "peer_legs": peer_legs, "marks": marks(DAY), "events": decoder_events(DAY),
           "onesided": ones_, "levels": lv, "levels_why": lv_why, "prev_tape": prev_tape}
    p = os.path.join(HERE, f"facts_{DAY}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"), default=str)
    print("wrote", p, os.path.getsize(p) // 1024, "KB:", len(bars5), "bars5,", len(ones), "1-min,", len(bars3), "bars3,",
          len(eps), "zone episodes,", len(out["vpin"]), "vpin,", len(legs), "legs,", len(out["marks"]), "marks,", len(out["events"]), "events,",
          len(lv), "levels;", "why:", lv_why)


if __name__ == "__main__":
    main()
