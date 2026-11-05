"""option_map_export.py -- today's NIFTY option record -> the JSON snapshot embedded in option-map.html. Read-only on
tapemap/data (streams the chain and the Dext files line by line), writes one JSON next to this file, never calls a server.

    python -I option_map_export.py [DAY]          -> option_map_<DAY>.json, then build_page() embeds it into option-map.html
"""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OPTFLOW = os.path.normpath(os.path.join(HERE, "..", "..", "optflow"))
sys.path.insert(0, OPTFLOW)
from optflow import D, IST, scrip       # the Battlefield's own data dir and scrip lookup (NSE-<id> -> scrip row)

T0, T1, STEP, LOT, IDX = 555, 930, 50, 65, "NIFTY"     # lot 65: v2feed.LOTS, as optladder uses


def main(day):
    N = T1 - T0 + 1
    spot, ch = [None] * N, {}
    expiry = None
    with open(os.path.join(D, "chain", f"chain_{IDX}_{day}.jsonl"), encoding="utf-8") as f:     # streamed, one row at a time
        for l in f:
            try:
                r = json.loads(l)
            except ValueError:
                continue
            i = r["sec"] // 60 - T0
            if not 0 <= i < N:
                continue
            spot[i] = r.get("spot") or spot[i]
            expiry = r.get("expiry") or expiry
            for s in r.get("strikes") or []:
                for sd in ("ce", "pe"):
                    q = s.get(sd) or {}
                    if q.get("oi") is not None:
                        ch.setdefault((s["k"], sd), {})[i] = (q["oi"], q.get("delta"), q.get("ltp"), q.get("avg"))
    live = [x for x in spot if x]
    lo, hi = min(live) - 5 * STEP, max(live) + 5 * STEP
    ks = sorted({k for k, _ in ch if lo <= k <= hi})
    last = max(i for i, x in enumerate(spot) if x is not None)

    def ffill(xs):
        out, v = [], None
        for x in xs:
            v = x if x is not None else v
            out.append(v)
        return out

    S = {}
    for k in ks:
        for sd in ("ce", "pe"):
            c = ch.get((k, sd), {})
            S[f"{k}{sd[0].upper()}"] = {"oi": ffill([None if i not in c else round(c[i][0] / 1e5, 2) for i in range(last + 1)]),
                                        "g": ffill([None if i not in c or c[i][1] is None else round(abs(c[i][1]), 3) for i in range(last + 1)]),
                                        "px": ffill([None if i not in c else c[i][2] for i in range(last + 1)]),
                                        "avg": ffill([None if i not in c else c[i][3] for i in range(last + 1)]),
                                        "d": [None] * (last + 1), "v": [None] * (last + 1)}
    fut_delta = [0] * (last + 1)
    prints, have = [], set()
    for p in glob.glob(os.path.join(D, "dext", f"dext_NSE-*_{day}.jsonl")):
        r = scrip().get(os.path.basename(p).split("_")[1])
        if not r or r[6] != IDX:
            continue
        fut = r[14] == "XX"
        if not fut and (r[12] != expiry or r[14] not in ("CE", "PE")):
            continue
        key = None if fut else f"{int(float(r[13]))}{r[14][0]}"
        if key and key not in S:
            continue
        rows = {}
        with open(p, encoding="utf-8") as f:
            for l in f:
                try:
                    c = json.loads(l)
                except ValueError:
                    continue
                i = (c["t"] + IST) % 86400 // 60 - T0
                if 0 <= i <= last:
                    rows[i] = c                     # last copy of a minute wins (dext_log's rule)
        for i, c in rows.items():
            if fut:
                fut_delta[i] = round(c.get("delta") or 0)
                continue
            have.add(key)
            S[key]["d"][i] = round((c.get("delta") or 0) / 1e5, 3)
            S[key]["v"][i] = round((c.get("total_volume") or 0) / 1e5, 2)
            big = max(c.get("levels") or [], key=lambda x: max(x["buy_volume"], x["sell_volume"]), default=None)
            if not big:
                continue
            q, side = (big["buy_volume"], "B") if big["buy_volume"] >= big["sell_volume"] else (big["sell_volume"], "S")
            g = S[key]["g"][i]
            dlots = round(q * g / LOT) if g else None
            if dlots and dlots >= 1000:            # kept from half the BADA floor; the page applies 2,000 (§1s-A, proposed)
                prints.append([i, key, side, round(q / 1e5, 2), big["price"], dlots])
        rows.clear()
    fut, futoi = [None] * (last + 1), [None] * (last + 1)
    try:
        with open(os.path.join(D, "tape", f"fut1m_{IDX}_{day}.json"), encoding="utf-8") as f:
            for t, v in json.load(f).items():
                i = int(t[:2]) * 60 + int(t[3:5]) - T0
                if 0 <= i <= last:
                    fut[i], futoi[i] = v[3], round(v[5] / LOT)
    except (OSError, ValueError):
        pass
    jv, prev = [], None
    try:
        with open(os.path.join(D, "jarvis", f"call_{day}.jsonl"), encoding="utf-8") as f:
            for l in f:
                try:
                    r = json.loads(l)
                except ValueError:
                    continue
                if r.get("idx") != IDX or "t" not in r:
                    continue
                w = r.get("word")
                if w != prev:
                    jv.append([int(r["t"][:2]) * 60 + int(r["t"][3:5]) - T0, w])
                    prev = w
    except OSError:
        pass
    for k in [k for k in S if k not in have]:       # no Dext file for that strike: flow stays null ("flow nahi"), never zero
        S[k]["noflow"] = 1
    sp = ffill(spot[:last + 1])
    first = next(i for i, x in enumerate(sp) if x is not None)
    sp[:first] = [sp[first]] * first                # the chain's first print stands in for 09:15 (said in the page's foot)
    out = {"day": day, "idx": IDX, "expiry": expiry, "t0": T0, "n": last + 1, "step": STEP, "lot": LOT, "ks": ks,
           "spot": sp, "spot_from": first, "fut": ffill(fut), "futoi": ffill(futoi), "futd": fut_delta, "s": S,
           "prints": sorted(prints), "jarvis": jv,
           "src": "data/chain/chain_NIFTY_<day>.jsonl (OI, greek delta, ltp) · data/dext/dext_NSE-*_<day>.jsonl (footprint) · "
                  "data/tape/fut1m_NIFTY_<day>.json · data/jarvis/call_<day>.jsonl"}
    path = os.path.join(HERE, f"option_map_{day}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    ds = sorted(abs(S[k]["oi"][i] - S[k]["oi"][i - 3]) for k in S for i in range(3, last + 1)
                if S[k]["oi"][i] is not None and S[k]["oi"][i - 3] is not None)
    print(f"{day}: {len(ks)} strikes {ks[0]}-{ks[-1]}, {last + 1} min, flow on {len(have)}/{len(S)}, prints>=1000 dlots {len(prints)}, "
          f">=2000 {sum(1 for p in prints if p[5] >= 2000)}; |dOI 3m| L p90 {ds[int(len(ds) * .9)]} p95 {ds[int(len(ds) * .95)]} "
          f"p99 {ds[int(len(ds) * .99)]} max {ds[-1]}; {os.path.getsize(path) // 1024} KB")


def build_page():
    """Embed the newest snapshot into option-map.html between the DATA markers."""
    snap = sorted(glob.glob(os.path.join(HERE, "option_map_*.json")))[-1]
    page = os.path.join(HERE, "option-map.html")
    html = open(page, encoding="utf-8").read()
    a, b = html.index("/*DATA*/"), html.index("/*END*/")
    html = html[:a] + "/*DATA*/const DATA = " + open(snap, encoding="utf-8").read() + ";" + html[b:]
    open(page, "w", encoding="utf-8").write(html)
    print("embedded", os.path.basename(snap), "into option-map.html")


if __name__ == "__main__":
    if "--page" in sys.argv:
        build_page()
    else:
        main(next((a for a in sys.argv[1:] if a[:2] == "20"), "2026-11-05"))
