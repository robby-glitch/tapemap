"""Scratch, read-only: NIFTY index 1-min candles for today (Upstox REST GET, the same call the
server's trend box makes), saved to this folder; then the median 1-min high-low over the 15
finished minutes ending at each check minute. Writes nothing in the repo."""
import json, os, statistics, sys
REPO = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, REPO); os.chdir(REPO)
import upstox_rest, upstox_feed, trendbox
HERE = os.path.dirname(os.path.abspath(__file__))
raw = upstox_rest.intraday("NSE_INDEX|Nifty 50", upstox_feed.read_token())
rows = [r for r in trendbox.candles(raw) if r[0] == "2026-09-25"]
json.dump(rows, open(os.path.join(HERE, "nifty_1m_2026-09-25.json"), "w"), indent=0)
ix = {r[1]: r for r in rows}
print(len(rows), rows[0][:2], rows[-1][:2])
for t in ("12:00", "12:02", "12:30", "12:32"):
    print("check close", t, ix.get(t))
def mm(t): h, m = t.split(":"); return int(h) * 60 + int(m)
def hm(n): return f"{n // 60:02d}:{n % 60:02d}"
for chk in ("09:35", "09:43", "12:00", "12:04", "14:12"):
    win = [hm(n) for n in range(mm(chk) - 14, mm(chk) + 1)]
    rg = [round(ix[t][3] - ix[t][4], 2) for t in win if t in ix]
    print(chk, "n", len(rg), "median", statistics.median(rg) if rg else None, "min", min(rg), "max", max(rg), rg)
