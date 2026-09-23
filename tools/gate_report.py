"""One day's gate numbers (spec 2026-09-20-upstox-tape §D) from the two record
files, printed as a table. It prints NUMBERS; the bar is the operator's (§K).

    python tools/gate_report.py NIFTY 2026-09-22 [LOT [TICK]]

If the ux file is missing but the book file exists, the ux bars are rebuilt
from the book first (ux_log.rebuild), so this runs from files alone. Against
a past day it always rebuilds: the session's final bin is only ever closed
here, and write-once makes the call idempotent.

Run it AFTER CLOSE. Against today it leaves the open bin alone and says so.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import book_log  # noqa: E402
import daylog  # noqa: E402
import ux_gate as gate  # noqa: E402   (amended at Task 9: gate.py is the seller's gate)
import tape_log  # noqa: E402
import ux_log  # noqa: E402
import upstox_instruments  # noqa: E402

FIELDS = ("bars_joined", "bars_ofd_only", "bars_ux_only", "poc_rows_median", "poc_within_1",
          "delta_sign_agree", "vol_ratio_median", "va_overlap", "hvn_jaccard", "lvn_jaccard",
          "exact_frac", "hidden_frac", "unknown_frac", "unpriced_frac")


def _fmt(v):
    if v is None:
        return "—"
    return f"{v:.3f}" if isinstance(v, float) else str(v)


def _resolve_lot(idx: str, lot, tick, ofd):
    """Lot/tick the way the server resolves them (spec §B/§J.12): the dump
    first, GoCharting's own lot for this record second, gcd last -- so a
    report run without LOT/TICK on the command line writes at the SAME unit
    the live server wrote at, not at gcd. `lot`/`tick` pass through unchanged
    when given; the caller passed them from argv."""
    if lot is not None:
        return lot, tick, "given"
    try:
        d_lot, d_tick = upstox_instruments.lot_tick(idx)
    except Exception:                          # no dump is not a reason to stop
        d_lot, d_tick = None, None
    if tick is None:
        tick = d_tick
    if d_lot:
        return d_lot, tick, "dump"
    if ofd and ofd[0].get("lot"):
        return ofd[0].get("lot"), tick, "ofd"
    return None, tick, "gcd"


def main(idx: str, day: str, lot=None, tick=None) -> int:
    today = day == time.strftime("%Y-%m-%d")
    ofd = tape_log.read_bars(day, idx)
    lot, tick, lot_src = _resolve_lot(idx, lot, tick, ofd)
    print(f"lot {lot if lot is not None else '—'} ({lot_src})")
    ux = ux_log.read_bars(day, idx)
    have_book = daylog.exists(book_log.day_path(day, idx))     # plain or week-old .gz
    if have_book and (not today or not ux):
        ux_log.rebuild(day, idx, lot, tick, lot_src=lot_src, close_last=not today)
        ux = ux_log.read_bars(day, idx)
    missing = []
    if not ofd:
        missing.append(f"no GoCharting record for {idx} on {day}")
    if not ux:
        missing.append(f"no ux record for {idx} on {day} — the book file holds no frame that closes a bar"
                       if have_book else
                       f"no ux record for {idx} on {day} — and no book file to rebuild one from")
    for m in missing:
        print(m)
    if today:
        print("the last bin is still open — its frames are not in a closed bar yet; "
              "run again after close for the full day")
    if missing:
        return 2
    row = float(ofd[0].get("rowSize") or 5)
    anchor = float(ofd[0].get("rowAnchor") or 0)
    s = gate.session(ofd, ux, row, anchor)
    print(f"{idx} {day} — GoCharting vs ux on rowSize {row:g} (shape metrics; the bar is yours, §K)")
    for k in FIELDS:
        why = s.get(k + "_why") or ""
        print(f"{k:<20} {_fmt(s.get(k)):>8}  {why}  [M]".rstrip())
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    lot = int(sys.argv[3]) if len(sys.argv) > 3 else None
    tick = float(sys.argv[4]) if len(sys.argv) > 4 else None
    sys.exit(main(sys.argv[1].upper(), sys.argv[2], lot, tick))
