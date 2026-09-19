# tapemap/tools/seed_tape_from_ofd.py
"""One-off: a recorded orderflow-desk export -> the ladder record, so a past
day can be drawn without the extension. Rows are tagged src:"seed" so a
scorer can never mistake them for what the socket wrote.

    python tools/seed_tape_from_ofd.py "C:\\Users\\kaam\\Desktop\\Go charting\\NIFTY-I_5m_2026-09-18.ofd.json" [NIFTY]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tape_log  # noqa: E402


def main(path: str, idx: str = "NIFTY") -> None:
    j = json.load(open(path, encoding="utf-8"))
    bars = sorted((b for b in j["bars"] if isinstance(b.get("ladder"), list) and b["ladder"]), key=lambda b: b["t"])
    if not bars:
        raise SystemExit("no bars with a ladder in that file")
    day = str(j.get("session", "")).split("|")[-1] or bars[0].get("date")
    doc = {"session": j.get("session"), "closed": bars, "events": j.get("events") or [], "forming": None,
           "rowSize": 5, "rowAnchor": 0, "lot": 65}
    n = tape_log.append(doc, day, idx)
    # the seed tag, added after the fact so tape_log's row shape stays one shape
    p = tape_log.day_path(day, idx)
    rows = tape_log.read_bars(day, idx)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            r["src"] = "seed"
            f.write(json.dumps(r) + "\n")
    print(f"seeded {n['bars']} bars and {n['marks']} marks for {idx} {day} -> {p}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "NIFTY")
