"""judge.py -- every ≠ READ line in replay/, with spot over the next 15 / 30 min along the line's own direction (points, never a
rate), plus the best / worst excursion in 30 min. The evening review of the one line this screen must never print on noise.

    python judge.py            -> replay/NEQ.txt and stdout
"""
import glob
import os
import re

import chainio
import raftaar as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "replay")
LINE = re.compile(r"^(\d\d:\d\d)\s+(\d+)s\s+≠ READ\s+(\S+ \S+)\s+(.*)$")


def judge():
    rows = ["≠ READ lines after the fix round · points along the line's direction (+ = went its way) · best / worst in 30 min", ""]
    for p in sorted(glob.glob(os.path.join(OUT, "*_2026-*.txt"))):
        name = os.path.basename(p)[:-4]
        idx, day = name.split("_", 1)
        grid = None
        for line in open(p, encoding="utf-8"):
            mt = LINE.match(line.strip())
            if not mt:
                continue
            t, spot, grade, why = mt.group(1), float(mt.group(2)), mt.group(3), mt.group(4)
            d = 1 if "RAFTAAR: CHAL RAHA ▲" in why else -1 if "RAFTAAR: CHAL RAHA ▼" in why else 0
            if grid is None:
                grid = chainio.load_chain(idx, day)[0]
            m = R.mins(t)
            s0 = grid[t]["spot"] if t in grid else spot

            def at(k):
                tt = R.hm(m + k)
                return grid[tt]["spot"] if tt in grid else None
            p15, p30 = at(15), at(30)
            path = [grid[R.hm(m + k)]["spot"] for k in range(1, 31) if R.hm(m + k) in grid]
            best = max((x - s0) * d for x in path) if path and d else None
            worst = min((x - s0) * d for x in path) if path and d else None
            f = lambda x: "—" if x is None else f"{(x - s0) * d:+.0f}"   # noqa: E731
            rows.append(f"{day} {idx:<9} {t}  {spot:>8.0f}s  {grade:<14} +15 {f(p15):>5}  +30 {f(p30):>5}  best {('—' if best is None else f'{best:+.0f}'):>5} / worst {('—' if worst is None else f'{worst:+.0f}'):>5}  | {why[:110]}")
    text = "\n".join(rows) + "\n"
    with open(os.path.join(OUT, "NEQ.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    judge()
