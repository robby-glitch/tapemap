# tapemap/tools/seed_tape_from_ofd.py
"""One-off: a recorded orderflow-desk export -> the ladder record, so a past
day can be drawn without the extension. Every row it writes -- bars AND marks
-- is tagged src:"seed" so a scorer can never mistake them for what the socket
wrote.

    python tools/seed_tape_from_ofd.py "C:\\Users\\kaam\\Desktop\\Go charting\\NIFTY-I_5m_2026-09-18.ofd.json" [NIFTY]

TWO REFUSALS, BOTH NON-ZERO EXITS (final review, 2026-09-19):

  * the day's bar file already exists. The tool REWRITES that file to add the
    seed tag, so running it over a day the extension really recorded would
    re-tag live rows as seed -- a measurement relabelled as a reconstruction.
    Delete the file yourself if that is genuinely what you want.
  * the export's session is not a 5m one. The POST gate is `interval == 5`
    (server.py) and every consumer of this record assumes 5-minute bars; a 1m
    export seeded here would read as a 5m day and nothing downstream would say
    otherwise.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tape_log  # noqa: E402


def _retag(path: str, rows: list) -> None:
    """Rewrite one record file with src:"seed" on every row. Only ever called
    for a file this run created."""
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            r["src"] = "seed"
            f.write(json.dumps(r) + "\n")


def main(path: str, idx: str = "NIFTY") -> None:
    j = json.load(open(path, encoding="utf-8"))
    session = str(j.get("session", ""))
    parts = session.split("|")
    interval = parts[1] if len(parts) > 2 else ""
    if interval != "5m":
        raise SystemExit(f"that export's session is '{session}' — the record is 5-minute bars only "
                         f"(the POST gate is interval == 5); refusing to seed a '{interval or '?'}' export")
    bars = sorted((b for b in j["bars"] if isinstance(b.get("ladder"), list) and b["ladder"]), key=lambda b: b["t"])
    if not bars:
        raise SystemExit("no bars with a ladder in that file")
    day = parts[-1] or bars[0].get("date")
    p = tape_log.day_path(day, idx)
    if os.path.exists(p):
        raise SystemExit(f"{p} already exists — this tool rewrites the whole file to tag it src:\"seed\", "
                         f"which would re-tag rows the extension really recorded; delete it first if you mean to")
    doc = {"session": session, "closed": bars, "events": j.get("events") or [], "forming": None,
           "rowSize": 5, "rowAnchor": 0, "lot": 65}
    n = tape_log.append(doc, day, idx)
    # the seed tag, added after the fact so tape_log's row shape stays one shape
    _retag(p, tape_log.read_bars(day, idx))
    if n["marks"]:
        _retag(tape_log.marks_path(day, idx), tape_log.read_marks(day, idx))
    print(f"seeded {n['bars']} bars and {n['marks']} marks for {idx} {day} -> {p}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "NIFTY")
