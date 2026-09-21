"""One day's gate numbers (spec 2026-09-20-upstox-tape §D) from the two record
files, printed as a table. It prints NUMBERS; the bar is the operator's (§K).

    python tools/gate_report.py NIFTY 2026-09-22 [LOT [TICK]]

If the ux file is missing but the book file exists, the ux bars are rebuilt
from the book first (ux_log.rebuild), so this runs from files alone.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import book_log  # noqa: E402
import ux_gate as gate  # noqa: E402   (amended at Task 9: gate.py is the seller's gate)
import tape_log  # noqa: E402
import ux_log  # noqa: E402

FIELDS = ("bars_joined", "bars_ofd_only", "bars_ux_only", "poc_rows_median", "poc_within_1",
          "delta_sign_agree", "vol_ratio_median", "va_overlap", "hvn_jaccard", "lvn_jaccard",
          "exact_frac", "hidden_frac", "unknown_frac")


def _fmt(v):
    if v is None:
        return "—"
    return f"{v:.3f}" if isinstance(v, float) else str(v)


def main(idx: str, day: str, lot=None, tick=None) -> int:
    ofd = tape_log.read_bars(day, idx)
    ux = ux_log.read_bars(day, idx)
    have_book = os.path.exists(book_log.day_path(day, idx))
    if not ux and have_book:
        ux_log.rebuild(day, idx, lot, tick)
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
