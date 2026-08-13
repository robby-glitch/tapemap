"""Capture the running session's 1-minute tape into data/backtest/.

WHY THIS EXISTS. `trigger_log` writes signals FORWARD, the instant the tape
shows them, but the bars those rows are scored against only ever arrived one
way: `backfill.py` -> `dhan_fetch`. The Dhan data API lapsed 2026-08-05, so no
August session was ever materialised, and a live session is reachable only
until the server rolls at midnight. On 2026-08-13 five SENSEX entries went
permanently unscoreable for exactly that reason -- the tape evaporated while
the rows sat in the log. This closes that hole without a broker.

IT WRITES THE RAW SHAPE, NOT DERIVED BARS. `squeeze_score.load` re-derives
every session with `to_bars -> vwap_bands -> resample`, so what goes on disk
must be a `rest_intraday` response: seven parallel arrays plus `_meta`, one
entry per MINUTE. Writing the 3-minute banded bars the API serves would band
them a second time on load and silently produce a different tape than the one
§5c was measured on. That is why this reads `interval=1` and keeps only
o/h/l/c/v/oi, discarding every derived field.

    python eod_capture.py                     # all three, after the close
    python eod_capture.py NIFTY SENSEX
    python eod_capture.py --force NIFTY       # overwrite an existing file

Run it after 15:30 and before midnight. Re-running is safe: an existing file is
never clobbered without `--force`, because a broker-fetched session is the
better record and must win over a capture.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime

from contract_bars import IST

HOST = "http://127.0.0.1:8765"
BT = "data/backtest"

# `squeeze_score.load` drops any session with fewer than 60 bars, and does it
# with a bare `continue`. A file it silently refuses looks EXACTLY like a file
# that was never written, so a short session is reported here as a reason
# instead -- "captured nothing" and "captured a stub that will never load" are
# opposite facts.
MIN_BARS = 60

# (array name on disk, key in the payload's `fut` block). `open_interest` is
# _OPTIONAL to `to_bars`, but the live tape always carries it and a session
# missing OI scores differently, so it is required here.
FIELDS = (("open", "o"), ("high", "h"), ("low", "l"),
          ("close", "c"), ("volume", "v"), ("open_interest", "oi"))


def path_for(idx, day, root=BT):
    """Where one session lives. NIFTY sits flat, others in a subdirectory --
    `squeeze_score._paths`' layout, which `backfill.py`'s LAYOUT note pins."""
    return (os.path.join(root, f"fut_{day}.json") if idx == "NIFTY"
            else os.path.join(root, idx, f"fut_{day}.json"))


def _fetch(idx, host=HOST):
    with urllib.request.urlopen(
            f"{host}/api/data?idx={idx}&interval=1", timeout=60) as r:
        return json.load(r)


def _iso_day(payload):
    """The session's ISO date, from the payload's own build stamp.

    NOT `date.today()`: this runs near midnight by design, and a capture that
    started at 23:59 and finished at 00:00 would file the session under the
    wrong day. `built_at` is stamped by the server that owns the bars.
    """
    ts = payload.get("built_at")
    if not isinstance(ts, (int, float)):
        return None
    return datetime.fromtimestamp(ts, IST).strftime("%Y-%m-%d")


def build(payload, idx):
    """`(rest_intraday-shaped dict, iso_day, None)` or `(None, day, why)`.

    Split out from `capture` so a test can hand it a payload without a server,
    and so the refusal reasons are testable on their own.
    """
    day = _iso_day(payload)
    if day is None:
        return None, None, ("the payload carries no readable `built_at`, so "
                            "the session's own date is unknown -- refusing to "
                            "guess it from the wall clock")

    days = [d for d in (payload.get("days") or []) if d.get("bars")]
    if not days:
        return None, day, (f"the {idx} payload holds no day with bars -- the "
                           f"server has rolled past the session, or never "
                           f"built one; nothing was captured")
    src = days[-1]

    cols = {name: [] for name, _ in FIELDS}
    stamps = []
    dropped = 0
    for b in src["bars"]:
        fut = b.get("fut") or {}
        vals = [fut.get(key) for _, key in FIELDS]
        t = b.get("t")
        try:
            ts = datetime.strptime(f"{day} {t}", "%Y-%m-%d %H:%M").replace(
                tzinfo=IST).timestamp()
        except (TypeError, ValueError):
            ts = None
        # A bar missing any field is DROPPED whole rather than written with a
        # gap: the arrays are positional, so a None in one of them would pair
        # the wrong minute's price with the next minute's volume.
        if ts is None or any(not isinstance(v, (int, float)) for v in vals):
            dropped += 1
            continue
        for (name, _), v in zip(FIELDS, vals):
            cols[name].append(float(v))
        stamps.append(ts)

    n = len(stamps)
    if n < MIN_BARS:
        return None, day, (f"only {n} usable {idx} bars for {day} "
                           f"({dropped} dropped) -- under the {MIN_BARS} that "
                           f"`squeeze_score.load` requires, so this file would "
                           f"be silently ignored on load; refusing to write it")

    out = dict(cols)
    out["timestamp"] = stamps
    out["_meta"] = {
        "index": idx,
        "expiry": payload.get("expiry"),
        "bars": n,
        "dropped": dropped,
        "served": {day: n},
        # Provenance, so a reader can never mistake a captured session for a
        # broker-fetched one. `_is_expiry` deliberately gets no
        # `is_monthly_expiry` key here: its own fallback computes that, and a
        # wrong stamp would be worse than no stamp.
        "source": "eod_capture from live tape",
        "captured_at": datetime.fromtimestamp(time.time(), IST).isoformat(),
    }
    return out, day, None


def capture(idx, host=HOST, fetch=None, force=False, root=BT):
    """`(path, bars, None)` on success, `(None, 0, why)` otherwise."""
    fetch = fetch or (lambda i: _fetch(i, host))
    try:
        payload = fetch(idx)
    except Exception as e:                     # noqa: BLE001 -- reported
        return None, 0, (f"could not read the live tape for {idx} "
                         f"({type(e).__name__}: {e}) -- is the server up?")

    out, day, why = build(payload, idx)
    if out is None:
        return None, 0, why

    path = path_for(idx, day, root)
    # A broker-fetched session is the better record: it is the contract's own
    # history rather than one process's view of it. Never overwrite silently.
    if os.path.exists(path) and not force:
        return None, 0, (f"{path} already exists -- leaving it alone; a fetched "
                         f"session outranks a capture. Pass --force to replace")

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f)
    # Atomic swap: a reader that globs this directory mid-write must never see
    # a half-written session, because `load` would drop it and report the day
    # as missing rather than as broken.
    os.replace(tmp, path)
    return path, out["_meta"]["bars"], None


def main(argv):
    force = "--force" in argv
    idxs = [a for a in argv[1:] if not a.startswith("-")] or [
        "NIFTY", "BANKNIFTY", "SENSEX"]
    bad = 0
    for idx in idxs:
        path, n, why = capture(idx, force=force)
        if why:
            bad += 1
            print(f"{idx:10} NOT CAPTURED -- {why}")
        else:
            print(f"{idx:10} {n} bars -> {path}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
