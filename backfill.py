"""Backfill data/backtest/ with 1-minute FUT bars + OI from Dhan.

WHY THIS EXISTS
    data/backtest/ was accumulated by a live day-by-day capture that stopped on
    2026-07-17, and nothing in the repo could recreate or extend it -- so a
    scoring run was permanently stuck at whatever the capture happened to hold.
    This script extends it, but only as far back as Dhan actually serves, which
    is far less than it looks.

THE HARD LIMIT (measured 2026-07-31 -- do not re-litigate)
    Dhan serves NOTHING before 2026-06-01, for any index. Two causes compound:
      1. instruments.resolve_dynamic reads the CURRENT scrip master, whose
         earliest FUTIDX expiry is 2026-07-30. Expired contracts are dropped
         from it, so a June-2026 future's security id cannot be resolved at all
         -- and resolve_dynamic does not fail, it silently hands back the
         current contract for ANY historical date.
      2. The contracts that ARE listed have no data before they listed.
    Probed on all three indices: 2026-05-20 -> 0 bars, 2026-05-26 -> 0 bars,
    2026-06-01 -> NIFTY 375, BANKNIFTY 374, SENSEX 161.
    A 0-bar day before 2026-06-01 is the limit, not a bug. It is logged with
    that reason rather than retried.

WHICH CONTRACT THIS CHARTS -- read this before pooling with the old cache
    Because only listed contracts resolve, June/July 2026 are fetched from the
    AUGUST future. In June that was the FAR month, whose OI is far thinner than
    the front month's. The pre-existing cache (2026-04-29 -> 07-17) was
    captured live and so used whichever contract was FRONT at the time. They
    are not the same instrument. Every file written here records its own
    fut_id/expiry under "_meta" so the difference stays visible. Never compare
    the two on an OI LEVEL. Relative OI change is scale-free -- which is what
    the scorer uses -- but the noise floor still differs, and a file with no
    "_meta" is an old front-month capture.

LAYOUT (chosen to avoid silently corrupting eight existing readers)
    NIFTY     -> data/backtest/fut_<ISO>.json
    other idx -> data/backtest/<INDEX>/fut_<ISO>.json
    backtest.py, band_backtest.py, continuation.py, contrarian.py,
    cross_breakout.py, cross_confluence.py, expression_backtest.py and
    measure.py all glob "data/backtest/fut_*.json" and slice the date with
    basename(p)[4:14]. An index PREFIX would make that slice return
    "NIFTY_2026" -- a wrong date, not a crash. A subdirectory leaves the
    basename untouched, so those readers keep working on NIFTY alone, which is
    what they were written for.

Usage:
  python backfill.py NIFTY 2026-06-01 2026-07-31
  python backfill.py --all 2026-06-01 2026-07-31
  python backfill.py --all 2026-06-01 2026-07-31 --dry-run
"""

import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import chain_live
import dhan_fetch as DF
import instruments as I

ROOT = Path(__file__).parent
BT = ROOT / "data" / "backtest"
LOG = BT / "backfill_log.json"
IST = timezone(timedelta(hours=5, minutes=30))

# Dhan's historical endpoint rate-limits harder than live._throttle's 5/s gate
# -- a 0.35s spacing produced HTTP 429 during the probe. These are measured,
# not guessed: 1.5s base spacing, exponential backoff, and a cap so a sustained
# 429 stops the run instead of hammering.
GAP_S = 1.5
MAX_RETRY = 4
EARLIEST = "2026-06-01"          # see THE HARD LIMIT above


def _sessions(start, end):
    """Weekdays from start to end inclusive. Exchange holidays are NOT modelled
    -- they are indistinguishable from an outage at this layer, so they surface
    as a 0-bar day and get logged with what Dhan actually said."""
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    out = []
    while d0 <= d1:
        if d0.weekday() < 5:
            out.append(d0.isoformat())
        d0 += timedelta(days=1)
    return out


def _is_monthly_expiry(day):
    """Last Thursday of the month -- the NSE monthly F&O expiry.

    This is stamped on every file because expiry contaminates exactly the
    measure the scorer depends on: 2026-07-30 (a last Thursday) carried a
    -338k overnight OI step on NIFTY that is settlement mechanics, not
    positioning. The scorer must be able to exclude these days."""
    d = date.fromisoformat(day)
    if d.weekday() != 3:
        return False
    return (d + timedelta(days=7)).month != d.month


def _path(idx, day):
    """NIFTY flat, everything else in its own subdirectory -- see LAYOUT."""
    if idx == "NIFTY":
        return BT / f"fut_{day}.json"
    return BT / idx / f"fut_{day}.json"


def _load_log():
    if LOG.exists():
        try:
            return json.loads(LOG.read_text())
        except ValueError:
            return {}
    return {}


def _fetch(tok, cfg, day):
    """One session, with 429 backoff. Returns (payload, served, note).

    Every response goes through dhan_fetch._one_session, which dates bars from
    their OWN timestamps. This is not optional: `toDate` is exclusive for the
    newest session but inclusive for older ones, so a response for "day" can
    contain two sessions, and banding two trading days onto one 09:15 VWAP
    anchor silently poisons every derived number downstream."""
    delay = GAP_S
    for attempt in range(MAX_RETRY):
        try:
            raw = DF.rest_intraday(tok, cfg["fut_id"], "FUTIDX", day,
                                   oi=True, seg=cfg["fut_seg"])
            payload, served, lost = DF._one_session(raw, day)
            return payload, served, (f"dropped {lost} row(s)" if lost else None)
        except Exception as e:
            if "429" in str(e) and attempt < MAX_RETRY - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return None, None, f"{type(e).__name__}: {str(e)[:120]}"
    return None, None, "gave up after repeated 429"


def backfill(idx, start, end, dry_run=False):
    tok = chain_live.read_token()
    st = chain_live.token_status(tok)
    if not st.get("ok"):
        raise SystemExit(f"no usable token: {st.get('msg')}")

    cfg = I.resolve_dynamic(dict(I.get(idx)), tok, end)
    print(f"\n=== {idx}  fut_id={cfg['fut_id']} expiry={cfg['expiry']} "
          f"seg={cfg['fut_seg']} ===")
    if start < EARLIEST:
        print(f"    NOTE: Dhan serves nothing before {EARLIEST}; days before "
              f"that are logged as out-of-range, not retried.")

    log = _load_log()
    wrote = skipped = empty = failed = 0
    for day in _sessions(start, end):
        key = f"{idx} {day}"
        path = _path(idx, day)
        if path.exists():
            skipped += 1               # resume-safe: an interrupted run is free
            continue
        if day < EARLIEST:
            log[key] = {"ok": False, "reason": f"before {EARLIEST}: Dhan holds "
                        f"no listed contract covering this date"}
            empty += 1
            continue
        if dry_run:
            print(f"    would fetch {day}")
            continue

        payload, served, note = _fetch(tok, cfg, day)
        time.sleep(GAP_S)
        n = len((payload or {}).get("close") or [])
        if not n:
            # A holiday and an outage look identical here. Record what Dhan
            # actually said rather than inventing a cause -- an absence must be
            # legible as one.
            log[key] = {"ok": False, "reason": note or "Dhan served no bars "
                        "for this session (holiday or outage -- "
                        "indistinguishable at this layer)"}
            empty += 1
            print(f"    {day}  no bars  ({log[key]['reason'][:60]})")
            continue

        oi = payload.get("open_interest") or []
        payload["_meta"] = {
            "index": idx, "fut_id": cfg["fut_id"], "expiry": cfg["expiry"],
            "seg": cfg["fut_seg"], "is_monthly_expiry": _is_monthly_expiry(day),
            "fetched_at": datetime.now(IST).isoformat(timespec="seconds"),
            "bars": n, "served": served,
            # Flagged, not refused: a flat OI series is real data that the
            # scorer must be able to see and exclude on its own terms.
            "oi_constant": bool(oi) and len(set(oi)) == 1,
            "oi_missing": not oi,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
        log[key] = {"ok": True, "bars": n,
                    "is_monthly_expiry": _is_monthly_expiry(day)}
        wrote += 1
        flag = " [EXPIRY]" if _is_monthly_expiry(day) else ""
        warn = " [OI FLAT]" if payload["_meta"]["oi_constant"] else ""
        print(f"    {day}  {n} bars{flag}{warn}")

    if not dry_run:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text(json.dumps(log, indent=1, sort_keys=True))
    print(f"    -> wrote {wrote}, already had {skipped}, "
          f"no-data {empty}, failed {failed}")
    return wrote


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 1
    dry = "--dry-run" in argv
    argv = [a for a in argv if a != "--dry-run"]
    target, start, end = argv[1], argv[2], argv[3]
    idxs = I.ENABLED if target == "--all" else [target]
    for idx in idxs:
        if idx not in I.ENABLED:
            print(f"unknown index {idx!r}; known: {I.ENABLED}")
            return 1
    for idx in idxs:
        backfill(idx, start, end, dry_run=dry)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
