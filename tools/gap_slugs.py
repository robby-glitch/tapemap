"""gap_slugs.py -- READ-ONLY: list the ux bars a feed gap turned into a one-sided slug (25 Oct review, A67).

Before the fix, ladder.attribute booked a dropped socket's whole gap as ONE print on one side. This lists every
such pair in the book files -- the rule the fix uses: the feed clock `cts` jumped > ladder.GAP_MS with volume --
and the ux bar it landed in, so a reader of those days knows which bars to distrust. It never rewrites a file.

    python tools/gap_slugs.py              # every day on disk
    python tools/gap_slugs.py 2026-10-16   # one day (several may be given)
"""
import glob
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ladder  # noqa: E402


def _rows(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError:
                    continue                      # a torn line is skipped, never fatal


def _ux(day, idx):
    for p in (f"data/tape/ux_{idx}_{day}.jsonl", f"data/tape/ux_{idx}_{day}.jsonl.gz"):
        if os.path.exists(p):
            return {b["t"]: b for b in _rows(p) if b.get("t") is not None}
    return {}


def main(days):
    print("| day | idx | bar | gap | units | ux delta | ux vol |")
    print("|---|---|---|---|---|---|---|")
    for path in sorted(glob.glob("data/book/book_*_*.jsonl*")):
        _, idx, day = os.path.basename(path).split(".")[0].split("_")
        if days and day not in days:
            continue
        ux, prev = None, None
        for r in _rows(path):
            if prev and r.get("cts") and prev.get("cts") and r.get("vtt") and prev.get("vtt"):
                dv = r["vtt"] - prev["vtt"]
                if dv > 0 and r["cts"] - prev["cts"] > ladder.GAP_MS:
                    ux = _ux(day, idx) if ux is None else ux
                    t = ladder.bin_of(r.get("ltt") or r["t"])    # where the old code booked it
                    b = ux.get(t, {})
                    print(f"| {day} | {idx} | {ladder.hms_ist(t)[:5]} | {(r['cts'] - prev['cts']) // 1000}s "
                          f"| {dv} | {b.get('delta', '—')} | {b.get('vol', '—')} |")
            prev = r


if __name__ == "__main__":
    main(set(sys.argv[1:]))
