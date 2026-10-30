"""timeline.py -- a 5-min strip of one (index, day): spot, its 5-min change, per-side gross add / cut over the nine (lakh),
the top-2 fronts per side by OI with their own 5-min change, so the composition of a move can be READ, not guessed.

    python timeline.py NIFTY 2026-10-26 [09:30 12:00]
"""
import os
import sys

from survey import CHAIN, grid, mins, nine
from explore import speeds, step_of

L = 1e5


def fronts_at(now, nk):
    out = {}
    for i, s in enumerate(("CE", "PE")):
        top = sorted(nk, key=lambda k: -now["oi"][k][i])[:2]
        out[s] = top
    return out


def main():
    idx, day = sys.argv[1], sys.argv[2]
    lo, hi = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else ("09:25", "15:30")
    p = os.path.join(CHAIN, f"chain_{idx}_{day}.jsonl")
    if not os.path.exists(p):
        p += ".gz"
    g = grid(p)
    sp = speeds(g)
    step = step_of(list(next(iter(g.values()))["k"]))
    at = {mins(t): t for t in g}
    print(f"== {idx} {day} step {step} ==  (add/cut = gross over the nine, 5 min, lakh; fronts = top-2 by OI with their 5-min chg)")
    print(f"{'t':<6}{'spot':>9}{'d5':>7}{'CE add':>8}{'CE cut':>8}{'PE add':>8}{'PE cut':>8}  CE fronts (chg5)              PE fronts (chg5)")
    for r in sp:
        t = r["t"]
        if t < lo or t > hi or mins(t) % 5:
            continue
        now = g[t]
        b = at.get(mins(t) - 5)
        was = g[b] if b else None
        fr = fronts_at(now, r["nine"])

        def cell(s, i):
            parts = []
            for k in fr[s]:
                d = (now["k"][k][i] - was["k"][k][i]) / L if was and k in was["k"] else float("nan")
                parts.append(f"{k:.0f}{d:+.1f}")
            return " ".join(parts)
        print(f"{t:<6}{r['spot']:>9.0f}{r['dspot']:>+7.0f}{r['add']['CE'] / L:>8.1f}{-r['cut']['CE'] / L:>8.1f}{r['add']['PE'] / L:>8.1f}{-r['cut']['PE'] / L:>8.1f}  "
              f"{cell('CE', 0):<30}{cell('PE', 1)}")


if __name__ == "__main__":
    main()
