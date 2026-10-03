import json, gzip, os, sys
import analyze7 as A, analyze8 as B
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import analyze10 as G
D = r"C:\Users\kaam\Desktop\operator mode\tapemap\data\chain"
_c = {}
def chain(day):
    if day not in _c:
        p = os.path.join(D, f"chain_NIFTY_{day}.jsonl")
        op = open if os.path.exists(p) else gzip.open
        p = p if os.path.exists(p) else p + ".gz"
        with op(p, "rt", encoding="utf-8") as f:
            _c[day] = [json.loads(l) for l in f if l.strip()]
    return _c[day]
for r in A.R:
    oty = "pe" if r["ty"] == "CE" else "ce"
    te = A.ms_of(r["day"], r["entry"]); t1 = A.ms_of(r["day"], "15:00:00")
    path = []
    for c in chain(r["day"]):
        t = A.ms_of(r["day"], c["ts"])
        if te <= t <= t1:
            x = next((x for x in c["strikes"] if x["k"] == r["k"]), None)
            if x and x[oty].get("ltp"): path.append((t, x[oty]["ltp"]))
    if not path: continue
    p0 = path[0][1]
    c = A.candidates(r); e6 = c["rev6"]; e = G.ivg(r)
    ex = e if (e and (e6 is None or e["t"] < e6["t"])) else e6
    if ex is e6 or (e6 and e6["t"] - e["t"] < 120000): continue
    p6, t6 = B.exit_pct(r, e6, path, p0, -1); p, t = B.exit_pct(r, ex, path, p0, -1)
    print(f"   {r['name']:28} short {r['k']}{oty.upper()} @ {p0}: rev6 {p6:+d} {t6} -> (iv-g) {p:+d} {t} | 15:00 {A.pct(r, path[-1][1], p0, -1):+d}")
