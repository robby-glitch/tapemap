"""moment.py -- the engine's JSON picture for one index at one minute (what GET /api/raftaar?idx= would return), off the record.

    python moment.py NIFTY 2026-10-26 09:58
"""
import json
import sys

import chainio
import refbuild
import raftaar as R


def picture(idx, day, at):
    grid, opens, kind = chainio.load_chain(idx, day)
    eng = R.Engine(idx, day, R.Ref(refbuild.load(idx)), kind, opens, chainio.load_fut(idx, day), read_words=chainio.load_read(idx, day))
    out = None
    for t in sorted(grid):
        if t > at:
            break
        out = eng.step(t, grid[t], read_word=R._read_word_at(eng.read_words, t) if eng.read_words else None)
    return out


if __name__ == "__main__":
    print(json.dumps(picture(sys.argv[1], sys.argv[2], sys.argv[3]), ensure_ascii=False, indent=1, default=str))
