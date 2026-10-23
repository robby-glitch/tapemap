"""tools/mark_grade.py -- A46: the nightly grading of the extension's marks. DESCRIPTION ONLY.

    python tools/mark_grade.py [--day YYYY-MM-DD] [--idx NIFTY] [--data DIR] [--out DIR]
        -> <out>/marks_<day>.json     one row per mark + its groups        (default out: data/grade/, day: today IST)
        -> <out>/marks_summary.json   every graded day's rows, grouped again, split by the extension's build

Per mark -- the FINAL state of each id in data/tape/ofd_marks2_<IDX>_<day>.jsonl (the last row of an id wins):
  ref       the minute the mark is known: its 5-min bar's close (t + 5 min); a trap is known at bar B's close (t + 10),
            drawn back on bar A (MARKS-EXPLAINED §2). spot0 = the chain recorder's spot at the end of the minute before.
  mfe/mae   over the next 15 / 30 / 60 minutes, in SPOT points [M] (the chain recorder's last spot of each minute),
            signed to the side the mark favours (`winner`): mfe >= 0 the best excursion, mae <= 0 the worst. An unsided
            mark (winner 0, a climax) has none. A horizon past the day's last spot minute is null, never a zero.
  held      the extension's own TIKA / TOOTA (its rule, MARKS-EXPLAINED §5) and, when TOOTA, `broke_after` = minutes
            from ref to the close that broke it (status_t is the breaking 5-min bar's start, v2.js:200).
Groups (each value: n, tika, toota, toota within 15 / 30 / 60, median mfe / mae per horizon):
  kind · rank band (the mark's rank: p90+, p70-89, <p70, none; rank.py's tags) · tier (solid / ghost / count / print)
  · ring (its sigma ring / band, or none) · pd (within 10 fut pts of the prior session's futures high / low / close,
  Upstox 5-min bars closed by 15:15 -- A2's cut; 10 pts = the extension's own "near the session low" distance)
  · part (rank.PARTS' day-parts of the ref minute).
COUNTS AND MEDIANS ONLY: no hit rate, no win rate, no expectancy (CLAUDE.md rule 4), and never on a live screen.
Promoting or demoting a mark needs a pass bar stated by the operator BEFORE these numbers are read.
"""
import argparse
import datetime
import gzip
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # tapemap/
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import rank as R                                                            # noqa: E402

DATA = os.path.join(HERE, "data")
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
HORIZONS = (15, 30, 60)
KNOWN_AFTER = {"trap": 10}             # minutes from the bar's start to the mark being known; 5 for every other kind
PD_NEAR = 10                           # fut points
PD_CUT = 15 * 3600 + 15 * 60           # A2: the prior session's levels from bars closed by 15:15
PART_NAMES = [f"{R.hm(a)}-{R.hm(b)}" for a, b in R.PARTS]


def _rows(path):
    for p in (path, path + ".gz"):
        if os.path.exists(p):
            op = gzip.open if p.endswith(".gz") else open
            with op(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(r, dict):
                        yield r
            return


def _sec(ms):
    return int(ms // 1000 + 19800) % 86400


def marks(data, idx, day):
    last = {}
    for r in _rows(os.path.join(data, "tape", f"ofd_marks2_{idx}_{day}.jsonl")):
        if r.get("id") and isinstance(r.get("t"), (int, float)):
            last[r["id"]] = r
    return sorted(last.values(), key=lambda r: (r["t"], r["id"]))


def spot_minutes(data, idx, day):
    out = {}
    for r in _rows(os.path.join(data, "chain", f"chain_{idx}_{day}.jsonl")):
        if isinstance(r.get("sec"), (int, float)) and isinstance(r.get("spot"), (int, float)):
            out[int(r["sec"]) // 60] = r["spot"]
    return out


def prior_levels(data, idx, day):
    """{"PDH", "PDL", "PDC"} of the prior recorded session (Upstox futures 5-min bars closed by 15:15), or None."""
    tape = os.path.join(data, "tape")
    try:
        prev = sorted(n[len(f"ux_{idx}_"):][:10] for n in os.listdir(tape) if n.startswith(f"ux_{idx}_")
                      and n[len(f"ux_{idx}_"):][:10] < day)
    except OSError:
        prev = []
    if not prev:
        return None
    bs = [b for b in R.bars_of(list(_rows(os.path.join(tape, f"ux_{idx}_{prev[-1]}.jsonl"))), 5)
          if b["e"] <= PD_CUT and None not in (b["h"], b["l"], b["c"])]
    if not bs:
        return None
    return {"PDH": max(b["h"] for b in bs), "PDL": min(b["l"] for b in bs), "PDC": bs[-1]["c"], "day": prev[-1]}


def band(rank):
    if not isinstance(rank, (int, float)):
        return "none"
    return "p90+" if rank >= 90 else "p70-89" if rank >= 70 else "<p70"


def part(minute):
    p = R.part_of(minute * 60)
    return PART_NAMES[p] if p is not None else ("15:15-15:30" if minute * 60 >= R.PARTS[-1][1] else "before 09:15")


def grade(m, spot, pd):
    """One mark's row."""
    s = _sec(m["t"])
    ref = s // 60 + KNOWN_AFTER.get(m.get("kind"), 5)
    m0 = next((x for x in (ref - 1, ref - 2, ref - 3) if x in spot), None)
    d = m.get("winner") if m.get("winner") in (1, -1) else 0
    last = max(spot) if spot else None
    row = {"id": m["id"], "kind": m.get("kind"), "name": m.get("name"), "build": m.get("build"), "t": R.hm(s),
           "ref": R.hm(ref * 60), "d": d, "p_fut": m.get("p"), "rank": m.get("rank"), "band": band(m.get("rank")),
           "tier": m.get("tier") or "none", "ring": m.get("ring") or "none", "part": part(ref),
           "status": m.get("status"), "broke_after": None, "spot0": None if m0 is None else spot[m0]}
    if m.get("status") == "TOOTA" and isinstance(m.get("status_t"), (int, float)):
        row["broke_after"] = _sec(m["status_t"]) // 60 + 5 - ref
    p = m.get("p")
    if pd is None or not isinstance(p, (int, float)):
        row["pd"] = "?"
    else:
        near = sorted((abs(p - pd[k]), k) for k in ("PDH", "PDL", "PDC"))[0]
        row["pd"] = near[1] if near[0] <= PD_NEAR else "—"
    for h in HORIZONS:
        mfe = mae = None
        if d and m0 is not None and last is not None and m0 + h <= last:
            mv = [d * (spot[x] - spot[m0]) for x in range(m0 + 1, m0 + h + 1) if x in spot]
            if mv:
                mfe, mae = round(max(0.0, max(mv)), 1), round(min(0.0, min(mv)), 1)
        row[f"mfe{h}"], row[f"mae{h}"] = mfe, mae
    return row


def groups(rows):
    """{dim: {value: {n, tika, toota, toota15/30/60, med_mfe15, med_mae15, ...}}} -- counts and medians only."""
    med = lambda xs: None if not xs else round(statistics.median(xs), 1)   # noqa: E731
    out = {}
    for dim in ("kind", "band", "tier", "ring", "pd", "part"):
        by = {}
        for r in rows:
            by.setdefault(str(r.get(dim)), []).append(r)
        out[dim] = {}
        for v, rs in sorted(by.items()):
            g = {"n": len(rs), "tika": sum(r["status"] == "TIKA" for r in rs), "toota": sum(r["status"] == "TOOTA" for r in rs)}
            for h in HORIZONS:
                g[f"toota{h}"] = sum(r["broke_after"] is not None and r["broke_after"] <= h for r in rs)
                g[f"med_mfe{h}"] = med([r[f"mfe{h}"] for r in rs if r[f"mfe{h}"] is not None])
                g[f"med_mae{h}"] = med([r[f"mae{h}"] for r in rs if r[f"mae{h}"] is not None])
            out[dim][v] = g
    return out


def build(idx, day, data=DATA):
    ms, spot, pd = marks(data, idx, day), spot_minutes(data, idx, day), prior_levels(data, idx, day)
    rows = [grade(m, spot, pd) for m in ms]
    why = None if ms else f"no ofd_marks2 mark for {idx} on {day}"
    if ms and not spot:
        why = f"could not check — no chain spot for {idx} on {day}: no excursion is measured"
    return {"day": day, "idx": idx, "tag": "M", "why": why, "n": len(rows),
            "src": "excursions in SPOT points: the chain recorder's last spot of each minute (data/chain)",
            "ref_rule": "known at the bar's close (t + 5 min), a trap at bar B's close (t + 10)",
            "pd": pd, "rows": rows, "groups": groups(rows), "note": "counts and medians only; no hit rate (rule 4)",
            "graded_at": datetime.datetime.now(IST).isoformat(timespec="seconds")}


def _write(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)
    return path


def summary(out_dir):
    """Every marks_<day>.json in out_dir, regrouped per (index, extension build): builds differ in their rules, so
    their rows are never pooled (CLAUDE.md rule 5)."""
    per, days = {}, []
    for n in sorted(os.listdir(out_dir)):
        if n.startswith("marks_") and n.endswith(".json") and n != "marks_summary.json":
            with open(os.path.join(out_dir, n), encoding="utf-8") as f:
                g = json.load(f)
            days.append(f"{g['idx']} {g['day']}")
            for r in g["rows"]:
                per.setdefault(f"{g['idx']} · {r.get('build')}", []).append(r)
    return {"days": days, "tag": "M", "note": "counts and medians only; no hit rate (rule 4); split by index and build",
            "by_build": {k: {"n": len(rs), "groups": groups(rs)} for k, rs in sorted(per.items())}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--day", default=datetime.datetime.now(IST).strftime("%Y-%m-%d"))
    ap.add_argument("--idx", default="NIFTY")
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    out = a.out or os.path.join(a.data, "grade")
    g = build(a.idx, a.day, a.data)
    if not g["n"]:                                  # no marks (a holiday, the extension closed): nothing is written
        print("not written --", g["why"])
        return 0
    print(_write(g, os.path.join(out, f"marks_{a.day}.json")), g["n"], "marks", g["why"] or "")
    print(_write(summary(out), os.path.join(out, "marks_summary.json")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
