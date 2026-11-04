"""Loaders for the 3 Nov option-flow x OI study. Read-only on data/. Every function is causal by construction: a
minute-keyed dict is read up to a minute by the caller. Minutes are IST minute-of-day (09:15 = 555).
Run from tapemap/:  python -I docs/optflow/fable/load.py  (prints a health summary)."""
import csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
D = os.path.join(ROOT, "data")
IST = 19800
DAY = "2026-11-03"
CUR = {"day": DAY}        # set CUR["day"] to study another day (study.py --day YYYY-MM-DD)
EXPIRY = {"NIFTY": "2026-11-03", "SENSEX": "2026-11-05"}
STEP = {"NIFTY": 50, "SENSEX": 100}
LOT = {"NIFTY": 75, "SENSEX": 20}


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def m_of(s):
    h, mi = s[:5].split(":")
    return int(h) * 60 + int(mi)


def scrip():
    """{'NSE-54062': (idx, expiry, strike, 'CE'|'PE')} for NIFTY / SENSEX options."""
    out = {}
    for fn in ("scrip_archive.csv", "scrip_master.csv"):     # A226: the archive keeps expired contracts; the master wins
        if not os.path.exists(os.path.join(D, fn)):
            continue
        with open(os.path.join(D, fn), encoding="utf-8", errors="ignore") as f:
            for r in csv.reader(f):
                if len(r) > 14 and r[1] == "D" and (r[0], r[6]) in (("NSE", "NIFTY"), ("BSE", "SENSEX")) and r[14] in ("CE", "PE"):
                    out[f"{r[0]}-{r[2]}"] = (r[6], r[12], int(float(r[13])), r[14])
    return out


def recover_map(day):
    """The scrip master is re-downloaded every morning and drops expired contracts (4 Nov 09:17: no 03 NOV rows left).
    Recover file -> (strike, side) for a recorded day by matching each Dext file's 3-min delta at her closes against the
    strike's `dl` in days.json (exported while the mapping still existed). Exact equality on >= 20 closes, one strike only.
    Cached in scrip_recovered.json."""
    cache = os.path.join(HERE, "scrip_recovered.json")
    try:
        got = json.load(open(cache, encoding="utf-8"))
    except (OSError, ValueError):
        got = {}
    if day in got:
        return {k: tuple(v) for k, v in got[day].items()}
    days = json.load(open(os.path.join(HERE, "days.json"), encoding="utf-8"))
    x = days[day]["NIFTY"]
    C = [i for i, m in enumerate(x["mins"]) if (m - 555) % 3 == 2]
    out = {}
    for fn in os.listdir(os.path.join(D, "dext")):
        if not fn.startswith("dext_NSE-") or fn.startswith("dext_ohlc") or not fn.endswith(f"_{day}.jsonl"):
            continue
        rows = {}
        with open(os.path.join(D, "dext", fn), encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    r = json.loads(l)
                    rows[(r["t"] + IST) % 86400 // 60] = r
        ser = {}
        for i in C:
            m = x["mins"][i]
            ms = [mm for mm in (m - 2, m - 1, m) if mm in rows]
            if len(ms) == 3:
                ser[i] = sum(rows[mm]["delta"] for mm in ms)
        best = None
        for q, k in enumerate(x["strikes"]):
            hits = sum(1 for i, v in ser.items() if x["dl"][i] and x["dl"][i][q] is not None and abs(x["dl"][i][q] - v) < 1)
            if hits >= 20 and (best is None or hits > best[1]):
                best = (tuple(k), hits)
        if best:
            out[fn[len("dext_"):-len(f"_{day}.jsonl")]] = best[0]
    got[day] = {k: list(v) for k, v in out.items()}
    json.dump(got, open(cache, "w", encoding="utf-8"))
    return out


def dext(day=None):
    day = day or CUR["day"]
    """{idx: {(strike, 'CE'|'PE'): {minute: candle}}} for the day's expiry contracts. Last copy of a minute wins."""
    sc = scrip()
    rec = None
    if not any(v[0] == "NIFTY" and v[1] == EXPIRY["NIFTY"] for v in sc.values()):
        try:
            rec = recover_map(day)
        except (OSError, ValueError, KeyError):
            rec = None
    out = {"NIFTY": {}, "SENSEX": {}}
    for fn in os.listdir(os.path.join(D, "dext")):
        if not fn.startswith("dext_") or fn.startswith("dext_ohlc") or not fn.endswith(f"_{day}.jsonl"):
            continue
        key = fn[len("dext_"):-len(f"_{day}.jsonl")]
        c = sc.get(key)
        if (not c or c[1] != EXPIRY[c[0]]) and key.startswith("NSE-") and rec is not None:
            c = ("NIFTY", EXPIRY["NIFTY"], rec[key][0], rec[key][1]) if key in rec else None
        if not c or c[1] != EXPIRY[c[0]]:
            continue
        rows = {}
        with open(os.path.join(D, "dext", fn), encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    r = json.loads(l)
                    rows[(r["t"] + IST) % 86400 // 60] = r
        out[c[0]][(c[2], c[3])] = rows
    return out


def chain(idx, day=None):
    day = day or CUR["day"]
    """{minute: snapshot} — the LAST snapshot inside each minute (the one a trader had at the minute's close)."""
    out = {}
    with open(os.path.join(D, "chain", f"chain_{idx}_{day}.jsonl"), encoding="utf-8") as f:
        for l in f:
            if l.strip():
                try:
                    r = json.loads(l)
                except ValueError:
                    continue
                out[r["sec"] // 60] = r
    return out


def oi_table(ch):
    """{minute: {(strike, side): oi}} plus {minute: spot}."""
    oi, spot = {}, {}
    for m, r in ch.items():
        spot[m] = r["spot"]
        oi[m] = {(s["k"], side.upper()): s[side]["oi"] for s in r["strikes"] for side in ("ce", "pe") if s.get(side)}
    return oi, spot


def fut(idx, day=None):
    """{minute: [o, h, l, c, vol, oi]} from the 1-min futures tape (fut1m). When a day has no fut1m (28, 29 Oct): the
    1-min OHLC from Dext's futures footprint (dext_ohlc_NSE-61471, NIFTY only) and the OI from the GoCharting 5-min
    tape (tape_NIFTY_<day>.jsonl, last known at or before the minute). FUT_SRC[day] says which."""
    day = day or CUR["day"]
    p = os.path.join(D, "tape", f"fut1m_{idx}_{day}.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            raw = json.load(f)
        FUT_SRC[day] = "fut1m"
        return {m_of(k): v for k, v in raw.items()}
    if idx != "NIFTY":
        raise FileNotFoundError(p)
    # OI and (where 1-min rows exist) OHLC from Dext's futures OHLC file; price from the 1-min footprint (h, l; the
    # close is the 1-min OHLC close when that row exists, else the minute's mid (h + l) / 2, said in FUT_SRC)
    ohlc, oi_any = {}, {}
    for l in open(os.path.join(D, "dext", f"dext_ohlc_NSE-61471_{day}.jsonl"), encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            m = (r["t"] + IST) % 86400 // 60
            if r.get("oi") is not None:
                oi_any[m] = r["oi"]
            ohlc[m] = r
    out, last, mids = {}, None, 0
    for l in open(os.path.join(D, "dext", f"dext_NSE-61471_{day}.jsonl"), encoding="utf-8"):
        if not l.strip():
            continue
        r = json.loads(l)
        m = (r["t"] + IST) % 86400 // 60
        if m in oi_any:
            last = oi_any[m]
        o = ohlc.get(m)
        if o and (ohlc.get(m - 1) is not None or ohlc.get(m + 1) is not None):   # a 1-min row (its neighbours exist)
            out[m] = [o["o"], o["h"], o["l"], o["c"], o.get("v", r["total_volume"]), last]
        else:
            out[m] = [None, r["high"], r["low"], (r["high"] + r["low"]) / 2, r["total_volume"], last]
            mids += 1
    FUT_SRC[day] = f"dext 1-min footprint (close = mid of h/l on {mids} min) + Dext OHLC OI"
    return out


FUT_SRC = {}


def vix(day=None):
    day = day or CUR["day"]
    if not os.path.exists(os.path.join(D, {"vix": "vix", "jarvis": "jarvis", "messages": "messages"}["vix"], ("vix_" if "vix" == "vix" else "call_" if "vix" == "jarvis" else "msg_") + f"{day}.jsonl")):
        return {}
    out = {}
    with open(os.path.join(D, "vix", f"vix_{day}.jsonl"), encoding="utf-8") as f:
        for l in f:
            if l.strip():
                r = json.loads(l)
                out[m_of(r["ts"])] = r["vix"]
    return out


def jarvis(day=None):
    day = day or CUR["day"]
    if not os.path.exists(os.path.join(D, {"vix": "vix", "jarvis": "jarvis", "messages": "messages"}["jarvis"], ("vix_" if "jarvis" == "vix" else "call_" if "jarvis" == "jarvis" else "msg_") + f"{day}.jsonl")):
        return []
    """[{t, idx, word, state, lean, count, fut, spot, leg, wrong_line, missing, blind}] in file order."""
    out = []
    with open(os.path.join(D, "jarvis", f"call_{day}.jsonl"), encoding="utf-8") as f:
        for l in f:
            if l.strip():
                out.append(json.loads(l))
    return out


def messages(day=None):
    day = day or CUR["day"]
    if not os.path.exists(os.path.join(D, {"vix": "vix", "jarvis": "jarvis", "messages": "messages"}["messages"], ("vix_" if "messages" == "vix" else "call_" if "messages" == "jarvis" else "msg_") + f"{day}.jsonl")):
        return []
    out = []
    with open(os.path.join(D, "messages", f"msg_{day}.jsonl"), encoding="utf-8") as f:
        for l in f:
            if l.strip():
                out.append(json.loads(l))
    return out


if __name__ == "__main__":
    dx = dext()
    for idx in ("NIFTY", "SENSEX"):
        ks = sorted(dx[idx])
        print(idx, len(ks), "contracts", ks[0], "...", ks[-1], "bars/contract",
              sorted({len(v) for v in dx[idx].values()}))
        ch = chain(idx)
        ms = sorted(ch)
        print("  chain", len(ms), "minutes", hm(ms[0]), "->", hm(ms[-1]), "gaps",
              [hm(a) for a, b in zip(ms, ms[1:]) if b - a > 1][:10])
        ft = fut(idx)
        fm = sorted(ft)
        print("  fut", len(fm), hm(fm[0]), "->", hm(fm[-1]))
    print("vix", len(vix()), "jarvis rows", len(jarvis()), "msgs", len(messages()))
