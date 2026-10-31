"""tools/jarvis_measure.py -- does the word hold? The plan's bar for the ACTION word (Jarvis v3, Task 1), on the record.

    python tools/jarvis_measure.py 2026-10-21 2026-10-29 2026-10-30
    python tools/jarvis_measure.py --all                 # every NIFTY day of jarvis.days()
    python tools/jarvis_measure.py --all --json out.json # the rows as JSON too

Per day: jarvis.build(day, "NIFTY", None, fill=True) and jarvis.calls(d) (the call as it stood at every minute), then
  word changes (raw state)   changes of the leg's raw word with its lean arrow (before Task 1 the call's word IS it)
  ACTION changes             changes of the call's word
  PALAT? episodes            minutes the call's word turned PALAT? (a run of PALAT? minutes is one episode)
  true flips                 the leg's lean flips (PALAT) at or after 10:00
  opening lean flips (<10:00) flips before 10:00 that the word announced (a word other than OPENING / NO LEG at the flip
                             minute), and in brackets every geometric flip before 10:00, announced or not
  NOT_READ                   the frame's GAPS §3 rows with no reader (health.not_read)
Counts, never a rate. Read-only: nothing is written under data/ (only --json's own path).
"""
import argparse
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

COLS = ("day", "minutes", "raw_changes", "action_changes", "palatq_episodes", "true_flips", "open_announced",
        "open_flips", "not_read")
HEAD = ("day", "minutes", "word changes (raw state)", "ACTION changes", "PALAT? episodes", "true flips",
        "opening lean flips (<10:00)", "NOT_READ")


def changes(xs):
    return sum(1 for a, b in zip(xs, xs[1:]) if a != b)


def measure(day):
    import jarvis
    d = jarvis.build(day, "NIFTY", None, fill=True)
    if not d.get("ok", True):
        return {"day": day, "why": d.get("why") or "no frame"}
    cs = jarvis.calls(d)
    words = [c["word"] for c in cs]
    raw = [(c["state"] + (f" {jarvis.ARR[c['lean']]}" if c.get("lean") else "")) if c.get("state") else c["word"]
           for c in cs]
    flips = ((d.get("legs") or {}).get("day") or {}).get("flips") or [0] * len(cs)
    early = [i for i, c in enumerate(cs) if c["at"] < "10:00"]
    open_flips = flips[early[-1]] if early else 0
    announced = sum(1 for i in early if flips[i] > (flips[i - 1] if i else 0)
                    and not words[i].startswith(("OPENING", "NO LEG")))
    return {"day": day, "minutes": len(cs), "raw_changes": changes(raw), "action_changes": changes(words),
            "palatq_episodes": sum(1 for a, b in zip([""] + words, words) if b.startswith("PALAT?") and not a.startswith("PALAT?")),
            "true_flips": (flips[-1] if flips else 0) - open_flips, "open_announced": announced, "open_flips": open_flips,
            "not_read": len(d["health"].get("not_read") or ())}


def table(rows):
    out = [" | ".join(HEAD), " | ".join("---" for _ in HEAD)]
    ok = [r for r in rows if "why" not in r]
    for r in rows:
        if "why" in r:
            out.append(f"{r['day']} | could not check — {r['why']}")
            continue
        out.append(" | ".join([r["day"], str(r["minutes"]), str(r["raw_changes"]), str(r["action_changes"]),
                               str(r["palatq_episodes"]), str(r["true_flips"]), f"{r['open_announced']} ({r['open_flips']})",
                               str(r["not_read"])]))
    tot = {k: sum(r[k] for r in ok) for k in COLS[1:]}
    out.append(" | ".join([f"TOTAL {len(ok)} days", str(tot["minutes"]), str(tot["raw_changes"]), str(tot["action_changes"]),
                           str(tot["palatq_episodes"]), str(tot["true_flips"]), f"{tot['open_announced']} ({tot['open_flips']})",
                           "-"]))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("days", nargs="*")
    ap.add_argument("--all", action="store_true", help="every NIFTY day of jarvis.days()")
    ap.add_argument("--json", help="also write the rows to this path")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.json) if a.json else None
    os.chdir(ROOT)                                    # the record's paths are relative to the repo
    import jarvis
    days = jarvis.days()["NIFTY"] if a.all else a.days
    if not days:
        ap.error("name the days, or --all")
    rows = [measure(day) for day in days]
    print(table(rows))
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
