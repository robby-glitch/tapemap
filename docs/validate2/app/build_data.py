"""build_data.py -- reduce TapeMap's recorded 2026-10-06 files to one compact data.json for the VALIDATE replay.

Reads (never writes) tapemap/data/chain/chain_{IDX}_{DAY}.jsonl, tapemap/data/book/book_{IDX}_{DAY}.jsonl and
tapemap/data/vpin_fast.jsonl. Emits app/data.json (< 5 MB). Every number in data.json is [M] from the recorder;
the app's reads on top of it are prototype logic.

  python build_data.py            # default day 2026-10-06
  python build_data.py 2026-10-05
"""
import json, os, sys, statistics, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "..", "data"))
DAY = sys.argv[1] if len(sys.argv) > 1 else "2026-10-06"
IDXS = ["NIFTY", "BANKNIFTY", "SENSEX"]
IST_OFFSET = 19800            # +05:30
EACH_SIDE = 8                 # ATM +/- 8 strikes kept
SLOW_EVERY = 6                # delta and day-avg kept every 6th chain row (~1 min): moneyness and pain read slowly
BAR_S = 1                     # book bars, seconds
# option expiry per index for DAY (NSE: NIFTY Tue; BSE: SENSEX Thu; BANKNIFTY monthly) -- the chain file carries it
LOTS = {"NIFTY": 65, "BANKNIFTY": 30, "SENSEX": 20}


def sec_of(ts):                      # "HH:MM:SS" -> seconds of day
    h, m, s = ts.split(":"); return int(h) * 3600 + int(m) * 60 + int(s)


def rows(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try: yield json.loads(line)
                except json.JSONDecodeError: pass     # a torn last line while the recorder wrote


def chain(idx):
    path = os.path.join(DATA, "chain", f"chain_{idx}_{DAY}.jsonl")
    rs = list(rows(path))
    if not rs: raise SystemExit(f"no chain rows: {path}")
    step = rs[0]["strikes"][1]["k"] - rs[0]["strikes"][0]["k"]
    # the union of strikes seen inside ATM +/- EACH_SIDE over the day
    ks = sorted({s["k"] for r in rs for s in r["strikes"] if abs(s["k"] - r["atm"]) <= EACH_SIDE * step})
    pos = {k: i for i, k in enumerate(ks)}
    out = {"step": step, "expiry": rs[0].get("expiry"), "lot": LOTS.get(idx), "ks": ks, "slowEvery": SLOW_EVERY,
           "t": [], "spot": [], "atm": [],
           "ce": {"oi": [], "ltp": [], "d": [], "avg": []}, "pe": {"oi": [], "ltp": [], "d": [], "avg": []}}
    for ri, r in enumerate(rs):
        slow = ri % SLOW_EVERY == 0
        out["t"].append(r["sec"] if "sec" in r else sec_of(r["ts"]))
        out["spot"].append(round(r["spot"], 1)); out["atm"].append(r["atm"])
        for leg in ("ce", "pe"):
            oi = [None] * len(ks); ltp = [None] * len(ks); d = [None] * len(ks); avg = [None] * len(ks)
            for s in r["strikes"]:
                i = pos.get(s["k"])
                if i is None: continue
                g = s[leg]
                oi[i] = round(g["oi"] / 1000)                       # OI in thousands (309.1L = 30910)
                ltp[i] = round(g["ltp"] * 20)                       # price in 0.05 ticks
                d[i] = round((g.get("delta") or 0) * 100)           # delta x100
                avg[i] = round(g.get("avg") or 0)                   # day avg traded price, whole rupees
            out[leg]["oi"].append(oi); out[leg]["ltp"].append(ltp)
            if slow: out[leg]["d"].append(d); out[leg]["avg"].append(avg)
    return out, rs[0]["ts"], rs[-1]["ts"], len(rs)


def book(idx):
    """1-s bars off the futures ticks: [sec, ltp x10, volume, buy volume]; plus futures OI per minute.
    Side: a trade at/above the prior best ask = buy, at/below the prior best bid = sell, else the tick rule."""
    path = os.path.join(DATA, "book", f"book_{idx}_{DAY}.jsonl")
    bars, oi_min = [], []
    prev = None; last_side = 1; cur = None; expiry = None
    for r in rows(path):
        expiry = expiry or r.get("expiry")
        sec = int(r["t"] // 1000 + IST_OFFSET) % 86400
        ltp = r["ltp"]
        if prev is None:
            vol = 0; side = 1
        else:
            vol = max(0, r["vtt"] - prev["vtt"])
            ask = prev["a"][0][0] if prev.get("a") else None
            bid = prev["b"][0][0] if prev.get("b") else None
            if ask is not None and ltp >= ask: side = 1
            elif bid is not None and ltp <= bid: side = -1
            elif ltp > prev["ltp"]: side = 1
            elif ltp < prev["ltp"]: side = -1
            else: side = last_side
        last_side = side
        b = sec - sec % BAR_S
        if cur is None or cur[0] != b:
            if cur: bars.append(cur)
            cur = [b, round(ltp * 10), 0, 0]
        cur[1] = round(ltp * 10); cur[2] += vol
        if side > 0: cur[3] += vol
        m = sec - sec % 60
        if not oi_min or oi_min[-1][0] != m: oi_min.append([m, r["oi"]])
        else: oi_min[-1][1] = r["oi"]
        prev = r
    if cur: bars.append(cur)
    return {"bars": bars, "futoi": oi_min, "futExpiry": expiry}, len(bars)


def vpin():
    path = os.path.join(DATA, "vpin_fast.jsonl")
    out = []
    if not os.path.exists(path): return out
    for r in rows(path):
        if r.get("day") != DAY: continue
        v = r["buy"] + r["sell"]
        out.append([sec_of(r["at"]), r["bucket"], round((r["buy"] - r["sell"]) / v, 4) if v else 0,
                    r.get("vpin"), r.get("pct")])
    return out


def main():
    doc = {"day": DAY, "built": datetime.datetime.now().isoformat(timespec="seconds"),
           "source": "tapemap/data chain + book + vpin_fast, recorder rows [M]", "idx": {}, "vpin": vpin()}
    for idx in IDXS:
        ch, t0, t1, n = chain(idx)
        bk, nb = book(idx)
        ch.update(bk)
        doc["idx"][idx] = ch
        print(f"{idx:10s} chain {n} rows {t0}..{t1} strikes {ch['ks'][0]}..{ch['ks'][-1]} step {ch['step']} | bars {nb} | futoi {len(bk['futoi'])}")
    out = os.path.join(HERE, "data.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    mb = os.path.getsize(out) / 1e6
    print(f"vpin buckets {len(doc['vpin'])} | wrote {out} {mb:.2f} MB")
    assert mb < 5, "data.json must stay under 5 MB"
    # one self-check against the day's known facts (ground truth from the 14:55 read)
    if DAY == "2026-10-06":
        n = doc["idx"]["NIFTY"]; i = min(range(len(n["t"])), key=lambda i: abs(n["t"][i] - (14 * 3600 + 55 * 60)))
        k = n["ks"].index(22700)
        assert 22700 <= n["spot"][i] <= 22712, n["spot"][i]
        assert 30500 <= n["ce"]["oi"][i][k] <= 31500 and 40000 <= n["pe"]["oi"][i][k] <= 41500, "22700 pin OI"
        print("self-check 14:55 NIFTY ok: spot", n["spot"][i], "22700 CE/PE OI(k)", n["ce"]["oi"][i][k], n["pe"]["oi"][i][k])


if __name__ == "__main__":
    main()
