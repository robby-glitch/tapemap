"""ONE-OFF REPAIR (her ask, 29 Oct ~00:45): 28 Oct's NIFTY chain hole 12:55-12:59 (the laptop slept 12:54-13:00 with no
restart, so the start-only backfill never ran for it) rebuilt from Upstox's PAST-DAY 1-minute candles (the historical
endpoint; the live backfill uses the today-only one) through chain_backfill's own minute_grid, and appended to
data/chain_backfill/backfill_NIFTY_2026-10-28.jsonl through its own write_grid -- tagged backfill, ONLY the minutes no
recorder and no earlier backfill holds, never clobbering. The token is read by upstox_feed.read_token() and never printed."""
import json
import os
import sys

ROOT = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import chain_backfill  # noqa: E402
import upstox_feed  # noqa: E402
import upstox_rest  # noqa: E402

DAY, IDX = "2026-10-28", "NIFTY"
seen = set()
with open(os.path.join("data", "chain", f"chain_{IDX}_{DAY}.jsonl"), encoding="utf-8") as f:
    snaps = [json.loads(line) for line in f if line.strip()]
for s in snaps:
    seen.add(s["ts"][:5])
strikes = sorted({int(r["k"]) for r in snaps[-1]["strikes"]})
disk = chain_backfill.read_grid(DAY, IDX)
want = [m for m in ("12:55", "12:56", "12:57", "12:58", "12:59") if m not in seen and m not in disk]
print("strikes", strikes[0], "..", strikes[-1], f"({len(strikes)}) | missing minutes to fill:", want)
if want:
    tok = upstox_feed.read_token()
    grid = chain_backfill.minute_grid(IDX, strikes, tok, fetch=lambda key, t: upstox_rest.historical(key, t, DAY),
                                      log=print)
    got = {m: grid[m] for m in want if m in grid}
    chain_backfill.write_grid(DAY, IDX, got, have=disk)
    print("filled:", sorted(got), "| not in Upstox history:", [m for m in want if m not in got])
    for m in sorted(got):
        print(" ", m, "spot", got[m]["spot"], "22700 (ce_chg, pe_chg)", got[m]["k"].get(22700))
