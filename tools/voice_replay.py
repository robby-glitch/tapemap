"""tools/voice_replay.py -- THE ONE VOICE (voice.py, NOTEPAD A52) and its TRADE MAP (trademap.py) replayed over real trade
paths, minute by minute, through the live code (voice_path.run, the module GET /api/voice_path uses). Read-only on data/;
writes only <out.json>.   python -I -X utf8 tools/voice_replay.py <out.json>   (prints each trade's state changes and receipt)"""
import json
import os
import sys

OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath("voice_replay.json")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from voice_path import run  # noqa: E402

TRADES = [
    # her 21 Oct mark, verbatim from data/day_state/day_2026-10-21.json
    dict(name="21oct", day="2026-10-21", lot=65, tr={"id": "NIFTY-23000PE-long-100730", "idx": "NIFTY", "k": 23000.0, "side": "PE",
         "role": "long", "t0": "10:07:30", "p0": 174.85, "exit_t": "13:05:04", "thesis": {"inval": 23052}}, end="13:20:00"),
    # 22 Oct: NOT marked (hold_trades = [], NOTEPAD A22); rebuilt from docs/live/DAY-2026-10-22.md §4f: 13:00 in, 13:25 out
    dict(name="22oct", day="2026-10-22", lot=20, tr={"id": "SENSEX-73400CE-long-130000", "idx": "SENSEX", "k": 73400.0, "side": "CE",
         "role": "long", "t0": "13:00:00", "p0": None, "exit_t": "13:25:00"}, end="13:40:00"),
    # her 30 Sep mark, verbatim from data/day_state/day_2026-09-30.json; run past her 11:16 exit to the 12:46 wall touch
    dict(name="30sep", day="2026-09-30", lot=65, tr={"id": "NIFTY-22750CE-long-101012", "idx": "NIFTY", "k": 22750.0, "side": "CE",
         "role": "long", "t0": "10:10:12", "p0": 164.7, "exit_t": "11:16:50"}, end="12:50:00"),
]


if __name__ == "__main__":
    res = {}
    for c in TRADES:
        path = run(c)
        seq, last = [], None
        for p in path:
            vc = p["voice"]
            if not vc.get("ok"):
                continue
            if vc["state"] != last:
                aft = " [after her exit]" if p["t"] > c["tr"]["exit_t"][:5] else ""
                seq.append(f"{p['t']} {vc['state']}" + (f" ({vc['reason']})" if vc.get("reason") else "") + aft)
                last = vc["state"]
        print(c["name"], c["tr"]["id"], "p0", c["tr"]["p0"])
        print("  " + "\n  → ".join(seq))
        print("  receipt:", (c.get("receipt") or {}).get("text"))
        res[c["name"]] = dict(trade=c["tr"], receipt=c.get("receipt"), seq=seq,
                              path=[{k: p[k] for k in ("t", "voice", "headline", "clause", "chips", "W", "hold2_text", "map")} for p in path],
                              dec_src=c.get("dec_src"),
                              frames={p["t"]: {"view": p["view"], "words": p["words"]} for p in path})
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, default=str)
