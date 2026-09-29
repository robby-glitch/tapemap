"""tools/reader_replay.py -- replay the SHADOW leg engine (reader.py) over recorded days, read-only, as-of.

    python tools/reader_replay.py                       # every day with a book file, all three indices
    python tools/reader_replay.py 2026-09-29 NIFTY      # one day, one index
    python tools/reader_replay.py --out docs/reader/replays

Inputs, all read-only (nothing under data/ is written):
  data/book/book_<IDX>_<day>.jsonl[.gz]      the Upstox book: the canonical minute when no candle exists, and the side
  docs/reader/data-<day>/fut_*_1m.json        exchange 1-minute candles, when pulled (29 Sep only so far): the canonical
                                              minute for the front contract; another month's file gives its OI only
  data/tape/tape_NIFTY_<day>.jsonl            GoCharting bars (NIFTY only), made available AS OF their arrival, read
                                              from data/frame/frame_<day>.jsonl minutes (a bar posted at 16:08 is not live)
  data/upstox_<idx>.json                      the instrument master: lot, tick (paise -> rupees), the front expiry
Prior sessions for the ruler: the up-to-5 book days before the day. Output per index-day: <IDX>_<day>.txt (the day
story + counts + the integrity audit) and <IDX>_<day>.json (legs and events, for the cross-index layer).
No outcome is scored anywhere: no hit rate, no "next leg".
"""
import glob
import json
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import daylog  # noqa: E402
import reader  # noqa: E402
import upstox_instruments as ui  # noqa: E402

DATA = os.path.join(ROOT, "data")
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
_TS = re.compile(r'"ts":\s*"(\d\d):(\d\d)')


def rows(path):
    try:
        f = daylog.open_text(path)
    except OSError:
        return []
    out = []
    with f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict):
                out.append(r)
    return out


def book_days(idx):
    names = glob.glob(os.path.join(DATA, "book", f"book_{idx}_*.jsonl*"))
    return sorted({re.search(r"(\d{4}-\d\d-\d\d)", os.path.basename(n)).group(1) for n in names})


def day_ms(day, hhmm="09:15"):
    return int(datetime.fromisoformat(f"{day}T{hhmm}:00+05:30").timestamp() * 1000)


def master(idx, day):
    """(front key, lot, rupee tick, expiry) from the cached instrument dump, as of the day's open."""
    path = os.path.join(DATA, f"upstox_{idx.lower()}.json")
    with open(path, encoding="utf-8") as f:
        rws = json.load(f)["rows"]
    futs = ui._futs(rws, day_ms(day))
    if not futs:
        return None, None, None, None
    f0 = futs[0]
    return f0["instrument_key"], int(f0["lot_size"]), reader.rupee_tick(float(f0["tick_size"])), ui._ymd(f0["expiry"])


def candles(day, front_key, lot):
    """(front candles, other-month {minute: OI lots}) from docs/reader/data-<day>/ when pulled."""
    front, other = None, {}
    for p in glob.glob(os.path.join(ROOT, "docs", "reader", f"data-{day}", "fut_*_1m.json")):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        cm = reader.candle_minutes(d["candles"], lot)
        if d.get("key") == front_key:
            front = cm
        else:
            other.update({c["t"]: c["oi"] for c in cm if c["oi"] is not None})
    return front, other


def gc_bars(day):
    """GoCharting bars with `arrived` = the end of the first frame-log minute at or after the bar's close."""
    bars = rows(os.path.join(DATA, "tape", f"tape_NIFTY_{day}.jsonl"))
    if not bars:
        return [], "no GoCharting tape file"
    mins = []
    try:
        with daylog.open_text(os.path.join(DATA, "frame", f"frame_{day}.jsonl")) as f:
            for line in f:
                m = _TS.search(line[:400])
                if m:
                    mins.append(day_ms(day, f"{m.group(1)}:{m.group(2)}"))
    except OSError:
        return [], "no frame log: GoCharting arrival times unknown"
    mins.sort()
    import bisect
    out, seen = [], set()
    for b in bars:
        if b.get("t") in seen or b.get("t") is None:
            continue
        seen.add(b["t"])
        close = b["t"] + reader.GC_BAR_MS
        k = bisect.bisect_left(mins, reader.minute_of(close))
        b = dict(b)
        b["arrived"] = (mins[k] + 60000) if k < len(mins) else 10 ** 15
        out.append(b)
    return out, None


def day_minutes(idx, day, lot, tick, front_key=None, with_candles=True):
    bm = reader.book_minutes(rows(os.path.join(DATA, "book", f"book_{idx}_{day}.jsonl")), lot, tick)
    front, other = candles(day, front_key, lot) if with_candles and front_key else (None, {})
    return reader.canonical(bm, front), other, front is not None


def audit(eng):
    """The misdescription audit: each confirmed leg's words re-derived from its own numbers. A count, never a rate."""
    bad = []
    legs = eng.legs
    table = {(1, 1): "new_longs", (-1, 1): "new_shorts", (1, -1): "short_covering", (-1, -1): "long_liquidation"}
    for k, L in enumerate(legs):
        idx0 = next(i for i, m in enumerate(eng.m) if m["t"] == L["t0"])
        idx1 = next(i for i, m in enumerate(eng.m) if m["t"] == L["t1"])
        mins = eng.m[:idx1 + 1] if L.get("from_open") else eng.m[idx0 + 1:idx1 + 1]
        if L.get("zero"):
            continue
        ext = max(m["h"] for m in mins) if L["dir"] > 0 else min(m["l"] for m in mins)
        if abs(ext - L["px1"]) > 1e-6:
            bad.append((L["id"], f"extreme {L['px1']} is not the leg's {'high' if L['dir'] > 0 else 'low'} {ext}"))
        if k and not L.get("from_open") and abs(L["px0"] - legs[k - 1]["px1"]) > 1e-6:
            bad.append((L["id"], "start is not the previous leg's end"))
        if L["confirmed_at"] < L["t1"] + 60000:
            bad.append((L["id"], "confirmed before its extreme minute closed"))
        w, oi = L["who"], L["oi"]
        mv = oi.get("moved") if oi.get("state") == "ok" else None
        want = "oi_cant" if mv is None else "rotation" if mv == 0 else table[(L["dir"], mv)]
        if w["class"] != want:
            bad.append((L["id"], f"WHO {w['class']} but its signs say {want}"))
        if mv and not (oi["lo"] >= oi["floor"] or oi["hi"] <= -oi["floor"]):
            bad.append((L["id"], "OI 'moved' inside its tolerance range"))
        lams = [L[t] for t in ("ux", "gc") if L[t].get("lam") is not None]
        size = abs(L["pts"]) / eng.delta
        against = w["aggressor"] and w["aggressor"] == -L["dir"]
        low = bool(lams) and all(x.get("low") for x in lams)
        if w["absorbed"] and not (against or (w["aggressor"] and low and size < reader.TH["ABSORB_MAX_R"])):
            bad.append((L["id"], "ABSORBED without its conditions"))
        if w["absorbed"] and not against and size >= reader.TH["PAID_R"]:
            bad.append((L["id"], f"a {size:.1f}-ruler leg called 'heavy effort, little progress'"))
        for t in ("ux", "gc"):
            r = L[t].get("rank")
            if r and r[1] - 1 < reader.TH["WARM_N"]:
                bad.append((L["id"], f"{t} ranked with n {r[1] - 1} before warm-up"))
        ux = L["ux"]
        if ux.get("state") == "ok":
            d = sum(m["buy"] - m["sell"] for m in mins if m["bk"])
            d -= sum(e["side"] * e["lots"] for e in L["excluded"] if e["tape"] == "UX")
            if abs(d - ux["d"]) > 1.0:
                bad.append((L["id"], f"UX delta {ux['d']} does not recompute ({d:.1f})"))
    return bad


def stamp(idx, day):
    """The contract the book itself names (stamped on book rows from 2026-09-29), or (None, None)."""
    try:
        with daylog.open_text(os.path.join(DATA, "book", f"book_{idx}_{day}.jsonl")) as f:
            for k, line in enumerate(f):
                r = json.loads(line)
                if r.get("expiry"):
                    return r.get("ik"), r["expiry"]
                if k > 50:
                    break
    except (OSError, ValueError):
        pass
    return None, None


def replay(idx, day, out_dir=None):
    key, lot, tick, expiry = master(idx, day)
    if not lot:
        return None
    ik, exp_stamp = stamp(idx, day)
    if exp_stamp:
        key, expiry, exp_src = ik or key, exp_stamp, "stamped on the book rows"
    else:
        exp_src = "from the current instrument dump (book rows not stamped before 29 Sep): unverified for a past day"
    mins, other, has_candles = day_minutes(idx, day, lot, tick, key)
    if not mins:
        return None
    prior = [d for d in book_days(idx) if d < day][-int(reader.TH["PRIOR_N"]):]
    prior_mins = []
    for d in prior:
        k2, l2, t2, _ = master(idx, d)
        pm, _, _ = day_minutes(idx, d, l2 or lot, t2 or tick, with_candles=False)
        prior_mins.append(pm)
    unit = reader.prior_unit(prior_mins) if prior_mins else None
    spread = reader.prior_spread(prior_mins) if prior_mins else None
    psig = reader.oi_sigma(prior_mins[-1]) if prior_mins else None
    gc, gc_why = gc_bars(day) if idx == "NIFTY" else ([], "no GoCharting for this index")
    eng = reader.run(mins, idx=idx, day=day, lot=lot, unit=unit, expiry=expiry, gc=gc, gc_expected=(idx == "NIFTY"),
                     other_oi=other, prior_sigma=psig, contract=key, spread=spread)
    lines = reader.story(eng)
    bad = audit(eng)
    au = [e for e in eng.events if e["kind"] == "auction"]
    states = [e for e in au if not e["en"].split(":")[1].strip().startswith("edge widened")]
    who = {}
    for L in eng.legs:
        who[L["who"]["class"]] = who.get(L["who"]["class"], 0) + 1
    cant = {t: sum(1 for L in eng.legs if L[t].get("state") == "cant") for t in ("ux", "gc")}
    excl = [e for L in eng.legs for e in L["excluded"]]
    pubs = sum(1 for _, _, p in eng.oi_upd if p)
    late = [b for b in gc if b["arrived"] > day_ms(day, "15:30")]
    head = [
        f"sources: {'exchange 1-min candles (price, volume, OI) + ' if has_candles else ''}Upstox book "
        f"({'side only' if has_candles else 'price, volume, OI and side'}; tick {tick} rupee) · "
        f"prior sessions for the ruler: {', '.join(prior) or 'none on disk'} · lot {lot}",
        f"GoCharting: {gc_why or f'{len(gc)} bars; {len(late)} arrived after 15:30 (not live, not read)'}",
        f"session read {reader.SESSION[0][:5]}–{reader.SESSION[1][:5]} (existing constants; 15:30–15:40 not read)",
        f"front contract {key} · expiry {expiry} {exp_src}",
        f"first minute read {reader.hm(mins[0]['t'])}" + ("" if reader.hm(mins[0]['t']) == "09:15" else
                                                         " (nothing earlier is recorded; the live hook will backfill from "
                                                         "REST candles, this replay does not)"),
    ]
    tail = [
        "",
        "COUNTS (n, never a rate)",
        f"  minutes read {len(eng.m)} · confirmed legs {len(eng.legs)} · auction state changes {len(states)} "
        f"(bar ≤ 12) · range-edge widenings {len(au) - len(states)}",
        f"  WHO classes: " + ", ".join(f"{k} {v}" for k, v in sorted(who.items())),
        f"  legs with UX CAN'T CHECK {cant['ux']} · GC CAN'T CHECK {cant['gc']} · "
        f"GC leg shorter than 2 bars {sum(1 for L in eng.legs if L['gc'].get('state') == 'short_leg')}",
        f"  prints excluded {len(excl)} ({', '.join(sorted({e['kind'] for e in excl})) or 'none'}) · "
        f"OI publication steps {pubs} of {len(eng.oi_upd)} updates",
        f"  integrity audit: {len(bad)} violation(s) (bar = 0)",
    ] + [f"    {i}: {w}" for i, w in bad]
    text = "\n".join(lines[:1] + head + lines[1:] + tail) + "\n"
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{idx}_{day}.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        keep = ("id", "idx", "day", "contract", "expiring", "t0", "t1", "dir", "px0", "px1", "pts", "mins", "vol", "ami", "zero",
                "ux", "gc", "oi", "who", "excluded", "holes", "from_open", "confirmed_at", "en", "chip", "x")
        with open(os.path.join(out_dir, f"{idx}_{day}.json"), "w", encoding="utf-8") as f:
            json.dump({"idx": idx, "day": day, "rev": reader.REV, "ruler": round(eng.delta, 1), "unit": round(eng.unit, 2),
                       "ruler_note": eng.ruler_note,
                       "thresholds": reader.TH, "legs": [{k: L[k] for k in keep} for L in eng.legs],
                       "forming": eng.forming(), "events": eng.events}, f, ensure_ascii=False, indent=1, default=str)
    return {"idx": idx, "day": day, "legs": len(eng.legs), "states": len(states), "bad": len(bad), "text": text,
            "who": who, "excluded": len(excl), "pubs": pubs, "cant": cant}


def main(argv):
    out = os.path.join(ROOT, "docs", "reader", "replays")
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        argv = [a for a in argv if a not in ("--out", out)]
    days = [a for a in argv if re.match(r"\d{4}-\d\d-\d\d$", a)]
    idxs = [a for a in argv if a in IDXS] or list(IDXS)
    res = []
    for idx in idxs:
        for day in days or book_days(idx):
            r = replay(idx, day, out)
            if r:
                res.append(r)
                print(f"{idx:9} {day}  legs {r['legs']:3}  auction changes {r['states']:2}  excluded {r['excluded']}  "
                      f"OI pub steps {r['pubs']:3}  CAN'T CHECK ux/gc {r['cant']['ux']}/{r['cant']['gc']}  "
                      f"integrity violations {r['bad']}")
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
