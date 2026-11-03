"""vix_log.py -- India VIX for Jarvis's HOW MUCH line (T2, docs/kahani/review/ALGO-AI-TAKE-2026-10-31.md).

data/vix/vix_<day>.jsonl, one row per CLOSED 1-minute candle of NSE_INDEX|India VIX: {"ts": "HH:MM", "vix": its close},
written once. The read is Upstox's intraday candles (upstox_rest.intraday, the tape's own endpoint; the token through
upstox_feed.read_token, never logged), once a minute in market hours. Those candles carry the whole session, so a server
started at 11:07 writes 09:15-11:05 from them too: a row written after the minute that followed its close carries
"src": "backfill" (the anytime-start rule: back, and tagged). The forming candle is never written, nor one before 09:15.
A bad read is counted and named in health() (/api/health coverage.vix) and the loop goes on: one bad minute never kills
the thread. Display only; gates nothing.
"""
from __future__ import annotations

import datetime
import json
import os
import threading
import time

import tailread

DIR = os.path.join("data", "vix")
KEY = "NSE_INDEX|India VIX"
OPEN, LAST = "09:16", "15:41"   # [I] reads while HH:MM is in [OPEN, LAST]: 09:15's candle closes at 09:16; F&O trades to 15:40
READ_AT = 20                    # [I] seconds past each minute: the candle that just closed has settled at Upstox
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
_LOCK = threading.Lock()
_SEEN = {}                      # path -> the ts already in its file (read once: a restart writes nothing twice)
STATE = {"last_ok": None, "last_row": None, "written": 0, "backfill": 0, "failed": 0, "why": "no read yet this process"}


def path_for(day):
    return os.path.join(DIR, f"vix_{day}.jsonl")


def rows(day):
    """The day's rows, each {"ts": "HH:MM", "vix": > 0, ...}, sorted by ts; a bad line is skipped; no file -> []."""
    return sorted((r for r in tailread.rows(path_for(day)) if isinstance(r.get("ts"), str) and len(r["ts"]) == 5
                   and isinstance(r.get("vix"), (int, float)) and r["vix"] > 0), key=lambda r: r["ts"])


def write(day, candles, now):
    """Append each closed candle of `day` (Upstox's [ts, o, h, l, c, ...]) not yet in the file -> the rows written."""
    n, path, out = now.hour * 60 + now.minute, path_for(day), []
    with _LOCK:
        if path not in _SEEN:
            _SEEN[path] = {r["ts"] for r in rows(day)}
        seen = _SEEN[path]
        for c in candles or ():
            if not (isinstance(c, (list, tuple)) and len(c) > 4 and str(c[0])[:10] == day):
                continue                           # just after midnight the endpoint still serves the last session
            ts, v = str(c[0])[11:16], c[4]
            m = int(ts[:2]) * 60 + int(ts[3:]) if len(ts) == 5 and ts[2] == ":" else None
            if m is None or ts < "09:15" or m >= n or ts in seen or not isinstance(v, (int, float)) or v <= 0:
                continue
            out.append(dict({"ts": ts, "vix": round(float(v), 2)}, **({"src": "backfill"} if n - m >= 2 else {})))
        out.sort(key=lambda r: r["ts"])
        if out:
            os.makedirs(DIR, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write("".join(json.dumps(r) + "\n" for r in out))
            seen.update(r["ts"] for r in out)
    return out


def _fetch():
    import upstox_feed
    import upstox_rest
    return upstox_rest.intraday(KEY, upstox_feed.read_token())


def tick(now=None, fetch=None):
    """One read: today's candles -> the file, health() updated -> rows written. Never raises: the thread's contract."""
    now = now or datetime.datetime.now(IST)
    hm = now.strftime("%H:%M")
    if now.weekday() >= 5 or not (OPEN <= hm <= LAST):
        if STATE["last_ok"] is None:
            STATE["why"] = f"no read: outside market hours ({hm})"
        return []
    try:
        out = write(now.strftime("%Y-%m-%d"), (fetch or _fetch)(), now)
    except Exception as e:                         # noqa: BLE001 -- one bad minute never kills the recorder
        STATE["failed"] += 1
        STATE["why"] = f"read failed at {hm}: {type(e).__name__}: {e}"[:200]
        return []
    STATE["written"] += len(out)
    STATE["backfill"] += sum(1 for r in out if r.get("src"))
    if out:
        STATE["last_row"] = f"{now:%Y-%m-%d} {out[-1]['ts']}"
    STATE["last_ok"] = now.isoformat(timespec="seconds")
    STATE["why"] = None if (STATE["last_row"] or "")[:10] == f"{now:%Y-%m-%d}" else f"no VIX candle today by {hm}"
    return out


def health():
    """/api/health coverage.vix: the last good read (IST), the newest row, rows written / backfilled and failed reads this
    process, and why when it is not reading."""
    return dict(STATE, key=KEY)


def run(stop=None):
    """The recorder thread: tick() READ_AT seconds past every minute, for ever (stop: a threading.Event, for a test)."""
    while not (stop and stop.is_set()):
        time.sleep((READ_AT - time.time()) % 60 or 60)
        tick()
