"""optflow -- the Option Battlefield: a live board of option-strike order flow + OI. http://127.0.0.1:8790/

Strikes down the side, the day across. Per strike and 5 minutes: did call writers / put writers add or leave (OI from
TapeMap's Upstox chain), and who did it (the Dext footprint's buyers vs sellers, fed by dext_bridge.mjs), the biggest
single-price hit, the index spot line, and NIFTY futures delta (SENSEX too: §1q, she trades SENSEX on NIFTY's flow).
On top: CAP / FLOOR / LEAN. Why it exists and how to read it: docs/optflow/README.md.

Every page load reads tapemap/data fresh and writes nothing.
    python -I optflow.py                    serve the board (start-v2.bat starts it)
    python -I optflow.py --check [DAY]      build both indices once for DAY (default today) and assert they hold data
"""
import csv, glob, json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:        # python -I drops the script dir: ladder / structures live beside this file
    sys.path.insert(0, HERE)
D = os.path.normpath(os.path.join(HERE, "..", "data"))
IST, PORT = 19800, 8790
LADDER_TTL_S = 20              # the ladder page polls every 30 s; two pages share one build
MIN_PRINT = {"NIFTY": 5e5, "SENSEX": 0.2e5}     # a "big hit" floor in qty: SENSEX ATM options trade ~1/65 of NIFTY's (3 Nov)
LABEL_PRINT = {"NIFTY": 10, "SENSEX": 0.5}       # lakh: hits this big carry their size on the map
_SCRIP = {}


def scrip():
    if not _SCRIP:          # ponytail: whole scrip master read once per process; restart after a new contract month
        for f in ("scrip_archive.csv", "scrip_master.csv"):   # A226: the archive keeps expired contracts; today's master wins
            if not os.path.exists(os.path.join(D, f)):        # ponytail: keyed by id alone; an id the exchange reuses maps
                continue                                      # to its newest contract, and the old day's file is dropped by
            for r in csv.reader(open(os.path.join(D, f), encoding="utf-8", errors="ignore")):   # the expiry check
                if len(r) > 14 and r[1] == "D" and (r[0], r[6]) in (("NSE", "NIFTY"), ("BSE", "SENSEX")):
                    _SCRIP[f"{r[0]}-{r[2]}"] = r        # keyed as Dext's files are named: NSE-54062, BSE-1134410
    return _SCRIP


def rows(p):
    """{minute of day: candle}, last copy wins (dext_log's rule)."""
    out = {}
    try:
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                out[(r["t"] + IST) % 86400 // 60] = r
    except (OSError, ValueError):
        pass
    return out


def load_chain(day, idx="NIFTY"):
    """{minute of day: the chain's last snapshot in that minute}."""
    chain = {}
    try:
        for l in open(os.path.join(D, "chain", f"chain_{idx}_{day}.jsonl"), encoding="utf-8"):
            try:
                r = json.loads(l)
                chain[r["sec"] // 60] = r
            except ValueError:
                pass
    except OSError:
        pass
    return chain


def build_map(day, idx="NIFTY"):
    """Per strike and 5-min block: call/put OI at block end, option order-flow delta, the biggest single-price hit;
    the index spot per minute; NIFTY futures delta per block. All chain strikes within 3 strikes of the day's range."""
    chain = load_chain(day, idx)
    if not chain:
        return None
    t0 = 9 * 60 + 15
    mins = list(range(t0, min(15 * 60 + 30, max(chain) + 1)))
    spot, last = [], None
    for m in mins:
        last = (chain.get(m) or {}).get("spot") or last
        spot.append(last)
    live = [s for s in spot if s]
    if not live:
        return None
    exp = chain[max(chain)].get("expiry")
    allk = sorted({s["k"] for s in chain[max(chain)].get("strikes") or []})
    step = min((b - a for a, b in zip(allk, allk[1:])), default=50)
    ks = [k for k in allk if min(live) - 3 * step <= k <= max(live) + 3 * step]
    nb = (len(mins) + 4) // 5
    oi = {sd: {k: [None] * nb for k in ks} for sd in ("ce", "pe")}
    cur = {sd: {} for sd in ("ce", "pe")}
    for i, m in enumerate(mins):
        for s in (chain.get(m) or {}).get("strikes") or []:
            for sd in ("ce", "pe"):
                v = (s.get(sd) or {}).get("oi")
                if v is not None:
                    cur[sd][s["k"]] = v
        for sd in ("ce", "pe"):
            for k in ks:
                if k in cur[sd]:
                    oi[sd][k][i // 5] = round(cur[sd][k] / 1e5, 3)
    flow = {sd: {k: [None] * nb for k in ks} for sd in ("ce", "pe")}
    best, fut = {}, [0] * nb
    for p in glob.glob(os.path.join(D, "dext", f"dext_NSE-*_{day}.jsonl")) + glob.glob(os.path.join(D, "dext", f"dext_BSE-*_{day}.jsonl")):
        r = scrip().get(os.path.basename(p).split("_")[1])
        if not r or not (r[6] == idx or (r[6] == "NIFTY" and r[14] == "XX")):
            continue
        for m, c in rows(p).items():
            b = (m - t0) // 5
            if not 0 <= b < nb:
                continue
            if r[14] == "XX":
                fut[b] += round(c.get("delta") or 0)
                continue
            k, sd = int(float(r[13])), r[14].lower()
            if r[12] != exp or k not in ks:
                continue
            flow[sd][k][b] = round((flow[sd][k][b] or 0) + (c.get("delta") or 0) / 1e5, 3)
            for lv in c.get("levels") or []:
                for side, q in (("B", lv.get("buy_volume") or 0), ("S", lv.get("sell_volume") or 0)):
                    key = (sd, k, b)
                    if q > best.get(key, (0,))[0]:
                        best[key] = (q, m - t0, lv["price"], side)
    prints = [[i, k, sd, side, round(q / 1e5, 2), px] for (sd, k, b), (q, i, px, side) in best.items() if q >= MIN_PRINT[idx]]
    p90 = lambda xs: sorted(xs)[int(len(xs) * 0.9)] if xs else None     # the day's own size of a big 5-min move
    oi_moves = [abs(v[b] - v[b - 1]) for side in oi.values() for v in side.values()
                for b in range(1, nb) if v[b] is not None and v[b - 1] is not None]
    flows = [abs(x) for side in flow.values() for v in side.values() for x in v if x is not None]
    return {"day": day, "t0": t0, "spot": spot, "strikes": ks, "oi": oi, "flow": flow, "prints": prints, "fut": fut,
            "expiry": exp, "idx": idx, "minPrint": MIN_PRINT[idx] / 1e5, "labelPrint": LABEL_PRINT[idx],
            "oiScale": max(0.01, p90(oi_moves) or 25), "flowScale": max(0.01, p90(flows) or 10)}


def map_page(day, idx="NIFTY"):
    data = build_map(day, idx if idx in MIN_PRINT else "NIFTY")
    if data is None:
        return ("<title>Option Battlefield</title><p style='font:16px system-ui;padding:24px'>No chain for today yet."
                " This page checks again in 30 s.</p><script>setTimeout(()=>location.reload(),30000)</script>")
    html = open(os.path.join(HERE, "map.html"), encoding="utf-8").read()
    return html.replace("/*DATA*/", "const DATA = " + json.dumps(data, separators=(",", ":")) + ";")


_LADDER = {}      # (day, idx, upto) -> (built at, DATA): the ladder is rebuilt at most every LADDER_TTL_S per key


def ladder_json(day, idx, upto=None):
    """The ladder's DATA for the day (ladder.build), cached LADDER_TTL_S; an index with no Dext bridge says so."""
    import optladder as ladder
    key = (day, idx, upto)
    hit = _LADDER.get(key)
    if hit and time.time() - hit[0] < LADDER_TTL_S:
        return hit[1]
    try:
        d = ladder.build(day, idx, upto) if idx in ladder.IDX else {"ok": False, "idx": idx, "why": f"no Dext bridge for {idx}: dekh nahi paaye"}
    except Exception as e:          # the page must say why, never go blank
        d = {"ok": False, "idx": idx, "why": f"ladder failed: {e!r}"}
    _LADDER[key] = (time.time(), d)
    return d


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path, _, query = self.path.partition("?")
        q = parse_qs(query)
        idx = (q.get("idx") or ["NIFTY"])[0].upper()
        day = (q.get("day") or [time.strftime("%Y-%m-%d")])[0]
        if path == "/ladder":                       # the dashboard page (optflow/ladder.html, LIVE: it fetches /ladder.json)
            body, ctype = open(os.path.join(HERE, "ladder.html"), encoding="utf-8").read().encode("utf-8"), "text/html; charset=utf-8"
        elif path == "/ladder.json":
            upto = q.get("upto", [None])[0]
            body = json.dumps(ladder_json(day, idx, int(upto) if upto and upto.isdigit() else None), separators=(",", ":")).encode("utf-8")
            ctype = "application/json"
        elif path in ("/", "/index.html"):
            body, ctype = map_page(day, idx).encode("utf-8"), "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except ConnectionError:         # the browser reloaded mid-send; nothing to do
            pass

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if "--check" in sys.argv:
        day = next((a for a in sys.argv[1:] if a[:2] == "20"), time.strftime("%Y-%m-%d"))
        for idx in MIN_PRINT:
            d = build_map(day, idx)
            assert d and d["strikes"] and d["spot"], f"{idx}: no chain for {day}"
            known = sum(1 for sd in d["flow"].values() for v in sd.values() for x in v if x is not None)
            assert known, f"{idx}: no Dext order flow for {day} - is dext_bridge.mjs running?"
            print(f"{idx} {day}: strikes {d['strikes'][0]}-{d['strikes'][-1]}, {len(d['spot'])} minutes, "
                  f"{known} flow blocks, {len(d['prints'])} big hits")
    else:
        print(f"Option Battlefield: http://127.0.0.1:{PORT}/  (SENSEX: /?idx=SENSEX) · the ladder: /ladder?idx=NIFTY  Ctrl+C to stop")
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
