"""tools/day_test.py -- the day test, every evening: what THE READ said, what every engine voice said, what the
signals did, and what spot did afterwards. Row counts only, never a rate (CLAUDE.md rule 4); the pass bar is hers.

    python tools/day_test.py                 today (after the close)
    python tools/day_test.py 2026-10-08      any recorded day

Writes docs/review/daytest/DAYTEST-<day>.md and prints it. Read-only on data/. The first one was done by hand on
2026-10-08 (docs/review/DAY-TEST-2026-10-08.md); this is it as a habit, so twenty sessions decide, not one.
"""
import datetime
import glob
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
os.chdir(HERE)

import read_replay  # noqa: E402

IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
LAST = 15 * 60 + 15                                  # nothing scored across the 15:15 cash-auction freeze


def spot_by_minute(idx, day):
    m = {}
    for r in read_replay._rows(os.path.join("data", "chain", f"chain_{idx}_{day}.jsonl")):
        if r.get("spot") and r.get("ts"):
            m[int(r["ts"][:2]) * 60 + int(r["ts"][3:5])] = r["spot"]
    return m


def fwd(m, t, h):
    if t + h > LAST:
        return None
    a = next((m[s] for d in range(4) for s in (t - d, t + d) if s in m), None)
    b = next((m[s] for d in range(4) for s in (t + h - d, t + h + d) if s in m), None)
    return None if a is None or b is None else b - a


def read_section(day):
    out = ["## THE READ (read.py)", "", "| Index | Open → close | Changes | The day, word by word (spot move inside each) |",
           "|---|---|---|---|"]
    with_, against = defaultdict(int), defaultdict(int)
    for idx in IDXS:
        try:
            X, tl, c, lv = read_replay.replay(day, idx)
        except Exception as e:                       # one bad index must not hide the others
            out.append(f"| {idx} | could not check — {type(e).__name__}: {e} | | |")
            continue
        if not c.get("ok"):
            out.append(f"| {idx} | {c.get('why')} | | |")
            continue
        segs = " · ".join(f"{g['from']} **{g['word']}** {g['move']:+d}" for g in c["day"])
        out.append(f"| {idx} | {X['spot'][0]:,.0f} → {X['spot'][-1]:,.0f} ({X['spot'][-1] - X['spot'][0]:+,.0f}) | {c['changes']} | {segs} |")
        for g in c["day"]:
            if g["dir"] and g["move"]:                 # a segment with no move is neither
                (with_ if g["move"] * g["dir"] > 0 else against)[g["word"].split()[0]] += 1
    out += ["", "Directional words, segments where spot moved their way vs against: "
            + ", ".join(f"{w} {with_[w]} with / {against[w]} against" for w in ("TREND", "LEAN")), ""]
    return out


def voices_section(day):
    p = glob.glob(os.path.join("data", "calls", f"calls_{day}.jsonl*"))
    if not p:
        return ["## ENGINE VOICES", "", "could not check — no calls log for the day", ""]
    spots = {i: spot_by_minute(i, day) for i in IDXS}
    st = defaultdict(lambda: [0, 0, 0, 0])            # rows@30, with@30, rows@60, with@60
    for r in read_replay._rows(p[0][:-3] if p[0].endswith(".gz") else p[0]):
        t = int(r["t"][:2]) * 60 + int(r["t"][3:5])
        for c in r.get("calls") or []:
            d, k = c.get("dir"), c.get("kind")
            if d not in ("up", "down") or k == "range":
                continue
            imp = (1 if d == "up" else -1) * (-1 if k == "exhaust" else 1)
            word = c["text"].split(" —")[0].split(" of ")[0].split(" a test")[0][:24]
            for n, h in ((0, 30), (2, 60)):
                f = fwd(spots.get(r["idx"]) or {}, t, h)
                if f is not None:
                    st[(c["source"], word)][n] += 1
                    st[(c["source"], word)][n + 1] += f * imp > 0
    out = ["## ENGINE VOICES (calls log; an exhaust call implies the other way)", "",
           "| Source | Word | With spot @30m | With spot @60m |", "|---|---|---|---|"]
    for (src, w), v in sorted(st.items(), key=lambda x: -x[1][0]):
        if v[0] >= 5:
            out.append(f"| {src} | {w} | {v[1]} of {v[0]} | {v[3]} of {v[2]} |")
    return out + [""]


def signals_section(day):
    rows = []
    with open(os.path.join("data", "trigger_log.jsonl"), encoding="utf-8") as fh:
        for x in fh:
            if f'"{day}"' in x:
                rows.append(json.loads(x))
    fires = [r for r in rows if r.get("kind") != "arm" and "px" in r and r.get("day") == day]
    out = ["## SIGNALS (zone machine) and the fade gate", "",
           f"Fires {len(fires)} · arms {sum(1 for r in rows if r.get('kind') == 'arm')}", "",
           "| Time | Index | Side | Px (fut) | Gate | Spot @30m their way |", "|---|---|---|---|---|---|"]
    for r in fires:
        g = r.get("gate") or {}
        f = fwd(spot_by_minute(r["index"], day), int(r["t"][:2]) * 60 + int(r["t"][3:5]), 30)
        gate = "LEGAL" if g.get("legal") else "VETO" if g.get("veto") else "refused"
        mv = "—" if f is None else f"{f * (1 if r['side'] == 'BUY' else -1):+.0f}"
        out.append(f"| {r['t']} | {r['index']} | {r['side']} | {r['px']:,.1f} | {gate} — {(g.get('why') or '')[:40]} | {mv} |")
    return out + [""]


def main(argv):
    day = next((a for a in argv if a[:2] == "20"), datetime.date.today().isoformat())
    lines = [f"# DAY TEST — {day}", "", "Row counts only, never a rate (CLAUDE.md rule 4). Rows overlap (re-logged calls); "
             "the pass bar is the operator's, stated before reading. Spot = the chain's index print.", ""]
    lines += read_section(day) + voices_section(day) + signals_section(day)
    os.makedirs(os.path.join("docs", "review", "daytest"), exist_ok=True)
    path = os.path.join("docs", "review", "daytest", f"DAYTEST-{day}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("\nwrote", path)


if __name__ == "__main__":
    main(sys.argv[1:])
