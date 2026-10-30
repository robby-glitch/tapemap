"""tools/pause_log.py -- THE LEG's forward log (NOISE-DECODER-BRAINSTORM.md, merged decision #8, 30 Oct).

Every pause the leg read saw today, with its word and items at the pause minute and one 3-min bar later, and what
happened in the 45 minutes after (computed only after the fact, kept apart from the causal fields) -> one row per pause
in data/jarvis/pause_<day>.jsonl. The round-2 composite (clean HOLD 14/35 vs 0/19; >= 3 items at +3 0/31 vs 6/17) was
built after reading the tables; these rows are how it earns trust or is dropped -- against her pass bar, read in the
evening review, never as a rate on screen. Forward days only (from 2 Nov): the 10 design days stay their own population.

Run by eod_capture.bat after the close; re-runnable any time after the close (it rewrites the day's file):
    python tools/pause_log.py [YYYY-MM-DD]
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import jarvis  # noqa: E402

DIR = os.path.join("data", "jarvis")
IDXS = ("NIFTY",)        # SENSEX waits for G13 (its frame has no flow); BANKNIFTY's chain is too small (G14)


def run(day, idxs=IDXS, out_dir=DIR):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"pause_{day}.jsonl")
    rows = []
    for idx in idxs:
        d = jarvis.build(day, idx, None)
        if not d.get("ok", True) or "legs" not in d:
            rows.append({"day": day, "idx": idx, "why": d.get("why") or "no frame"})
            continue
        L = d["legs"]
        if L.get("error"):
            rows.append({"day": day, "idx": idx, "why": "the leg read failed: " + L["error"]})
            continue
        for p in L.get("pauses") or ():
            rows.append(dict(p, day=day, idx=idx, rev=L.get("rev")))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    os.replace(tmp, path)
    return path, len(rows)


if __name__ == "__main__":
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    p, n = run(day)
    print(f"pause log: {n} row(s) -> {p}")
