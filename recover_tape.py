"""Rebuild a missing session tape from Kite historical candles.

WHY THIS EXISTS
    `trigger_log.score` fills a forward-logged row's outcome from the session
    tape in `data/backtest/`. Five sessions never got captured: 2026-08-10 and
    2026-08-13 predate `eod_capture.py`, and the Dhan Data API that
    `backfill.py` used lapsed 2026-08-05, so nothing in the repo could
    recreate them. Those rows have carried `unscored: no cached <IDX> session`
    ever since (DEFERRED §0d item 1, which names this exact route and blesses
    it: filling the outcome of a row logged FORWARD is allowed; searching a
    NEW hypothesis out of the cache is what §5's stop rule forbids).

WHAT IT IS NOT
    Not a backfill tool and not a data source. It converts candles the
    operator's own authenticated Kite session already returned into the ONE
    file shape `contract_bars.to_bars` reads, and refuses anything it cannot
    stand behind. `backfill.py` was deleted in the ponytail cleanup; this is
    30 lines and does one thing.

WHAT IT REFUSES
    * a day that already has a tape -- a live capture is the better record and
      is never overwritten
    * fewer than 60 bars -- `squeeze_score.load` silently drops such a file,
      so writing one would leave the row unscored with a WORSE reason
    * a candle list whose day does not match the requested day

The `_meta` block records that these bars came from Kite historical rather
than the live tape, so a reader can always tell a reconstruction from a
capture -- the same distinction `eod_capture` writes for its own files.
"""

import json
import os
import sys
from datetime import datetime

BT = "data/backtest"


def path_for(index, day):
    """NIFTY sits flat in data/backtest/, other indices in a subdirectory --
    `squeeze_score._paths`' layout, which the basename must match exactly."""
    return (f"{BT}/fut_{day}.json" if index == "NIFTY"
            else f"{BT}/{index}/fut_{day}.json")


def to_payload(candles, index, day, expiry=None, token=None):
    """Kite `historical_data` rows -> the arrays `contract_bars.to_bars` reads.

    A Kite row is [timestamp, open, high, low, close, volume, oi]; the stamp
    is ISO with the +05:30 offset, and `to_bars` sorts on a NUMERIC instant,
    so it is converted to epoch seconds here rather than carried as a string.
    """
    out = {"timestamp": [], "open": [], "high": [], "low": [], "close": [],
           "volume": [], "open_interest": []}
    for row in candles:
        ts = row[0]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts).timestamp()
        elif isinstance(ts, datetime):
            ts = ts.timestamp()
        if datetime.fromtimestamp(ts).strftime("%Y-%m-%d") != day:
            continue                  # a stray bar from a neighbouring day
        out["timestamp"].append(float(ts))
        for i, k in enumerate(("open", "high", "low", "close", "volume"), 1):
            out[k].append(float(row[i]))
        out["open_interest"].append(float(row[6]) if len(row) > 6 else 0.0)
    out["_meta"] = {"index": index, "expiry": expiry, "fut_id": token,
                    "bars": len(out["timestamp"]),
                    "source": "kite historical (recover_tape.py)",
                    "recovered_at": datetime.now().isoformat()}
    return out


def write(index, day, candles, expiry=None, token=None):
    """-> (path, bars) on success; raises with the reason on refusal."""
    dst = path_for(index, day)
    if os.path.exists(dst):
        raise SystemExit(f"refused: {dst} already exists — a live capture is "
                         f"the better record and is never overwritten")
    payload = to_payload(candles, index, day, expiry, token)
    n = len(payload["timestamp"])
    if n < 60:
        raise SystemExit(f"refused: {n} bars for {index} {day} — under 60, "
                         f"squeeze_score.load drops such a file silently, so "
                         f"writing it would replace one unscored reason with "
                         f"a worse one")
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return dst, n


if __name__ == "__main__":
    # recover_tape.py <INDEX> <YYYY-MM-DD> <candles.json> [expiry] [token]
    idx, day, src = sys.argv[1], sys.argv[2], sys.argv[3]
    exp = sys.argv[4] if len(sys.argv) > 4 else None
    tok = sys.argv[5] if len(sys.argv) > 5 else None
    rows = json.load(open(src, encoding="utf-8"))
    rows = rows.get("candles", rows) if isinstance(rows, dict) else rows
    p, n = write(idx, day, rows, exp, tok)
    print(f"wrote {p} — {n} bars")
