"""compare.py -- Fable's raftaar.py and Opus's raftaar.py on the same index, day and minutes, side by side (round 2).
Read-only on both (Fable's folder is imported, never written). stdlib.

    python -X utf8 compare.py NIFTY 2026-10-22 11:40 12:00
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FABLE = os.path.join(HERE, "..", "fable")
sys.path.insert(0, HERE)
import raftaar as O                                    # noqa: E402
sys.path.insert(0, FABLE)
import importlib.util                                  # noqa: E402
spec = importlib.util.spec_from_file_location("fraftaar", os.path.join(FABLE, "raftaar.py"))
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

_cache = {}


def fable_rows(idx, day):
    if (idx, day) not in _cache:
        rows = {}
        for i in O.IDXS:
            g = F.load(i, day)
            if g:
                rows[i] = F.read_day(g)[0]
        for i in rows:
            F.peers(rows[i], [rows[o] for o in rows if o != i])
        _cache[(idx, day)] = rows
    return _cache[(idx, day)][idx]


def opus_rows(idx, day):
    first = {i: O.run(i, day) for i in O.IDXS if day in O.days(i)}
    dirs = {i: O.dirs_of(r) for i, r in first.items()}
    return O.run(idx, day, dirs)


def fword(r):
    if r["word"] != "CHAL RAHA":
        extra = f" {r.get('side', '')} {r.get('k', '') or ''}".rstrip() if r["word"] in ("LOAD", "PIN") else ""
        return (r["word"] + extra)[:34]
    a = "▲" if r["dirn"] > 0 else "▼"
    return f"CHAL {a} {r['qual']} {r['phase']} {r['lose'][:2]}:{r['lose_pat']} {r['win'][:2]}:{r['win_pat']}"[:44]


def main(idx, day, a, b):
    fr = {r["t"]: r for r in fable_rows(idx, day)}
    ores = opus_rows(idx, day)
    print(f"{idx} {day}  minute | spot | FABLE (word · grade) | OPUS (held picture · n/N · minute story)")
    for o in ores["rows"]:
        t = O.hm(o["t"])
        if not (a <= t <= b):
            continue
        f = fr.get(t)
        fs = "—"
        if f:
            fs = fword(f) + (f" {F.GRADE_WORD(f['grade'])} {f['grade']}/{len(f['checks'])}" if f.get("grade") is not None else "")
        n, N = O.count(o["ch"])
        print(f"{t} {o['spot']:8.1f} | {fs:<58} | {O.headline(o['pic']):<22} {n}/{N:<3} {o['st']['name'][:40]}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
