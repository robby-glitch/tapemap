"""tools/read_replay.py -- THE READ (read.py) replayed over recorded days, through the same loader the live route uses.

    python tools/read_replay.py                      every recorded day, all three indices, the day-so-far line
    python tools/read_replay.py 2026-10-08 -v        one day, every mark and every event

Read-only. Yesterday's levels come from the prior session's recorded spot (10-s polls), so they are [M] but can miss
the exact print by a few points; live, /api/read takes PDH / PDL / PDC from the daily candles. A row count, never a
rate: what the READ said, when, and what spot did inside each word.
"""
import glob
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.chdir(HERE)

import read  # noqa: E402
import v2feed  # noqa: E402

DATA = os.path.join(HERE, "data")


def _rows(path):
    for p in (path, path + ".gz"):
        if os.path.exists(p):
            op = gzip.open if p.endswith(".gz") else open
            with op(p, "rt", encoding="utf-8") as f:
                return [json.loads(x) for x in f if x.strip()]
    return []


def days():
    out = set()
    for p in glob.glob(os.path.join(DATA, "chain", "chain_NIFTY_2026-*.jsonl*")):
        out.add(os.path.basename(p)[12:22])
    return sorted(out)


def prior_levels(idx, day):
    """PDH / PDL / PDC from the prior recorded session's spot polls."""
    for d in reversed([d for d in days() if d < day]):
        spots = [r["spot"] for r in _rows(os.path.join(DATA, "chain", f"chain_{idx}_{d}.jsonl")) if r.get("spot")]
        if spots:
            return {"PDH": max(spots), "PDL": min(spots), "PDC": spots[-1], "from": d}
    return None


def replay(day, idx):
    D = v2feed.Day(day, DATA)
    D.refresh()
    X = read.from_v2(D.idx[idx], v2feed.LOTS.get(idx))
    bars5 = _rows(os.path.join(DATA, "tape", f"ux_{idx}_{day}.jsonl"))
    lv = prior_levels(idx, day)
    tl = read.timeline(X, bars5, lv)
    return X, tl, read.card(X, tl, lv), lv


def main(argv):
    verbose = "-v" in argv
    want = [a for a in argv if a[:2] == "20"]
    for day in want or days():
        for idx in v2feed.IDXS:
            try:
                X, tl, c, lv = replay(day, idx)
            except Exception as e:                       # one bad day must not hide the rest
                print(day, idx, "could not check --", type(e).__name__, e)
                continue
            if not c.get("ok"):
                print(day, idx, c.get("why"))
                continue
            first, last = X["spot"][0], X["spot"][-1]
            segs = " | ".join(f"{g['from']}-{g['to']} {g['word']} {g['move']:+d}" for g in c["day"])
            print(f"{day} {idx:9s} {first:>9,.0f} -> {last:>9,.0f} ({last - first:+6.0f})  changes {c['changes']:2d}  {segs}")
            if verbose:
                for r in tl["rows"]:
                    w = r["writers"]
                    print(f"   {r['t']} {r['word']:8s}{read.ARROW[r['dir']]:2s} spot {r['spot']:>9,.1f} flip {read.num(r['flip']):>7s}"
                          f"  W {w.get('cls')} A {w.get('A')}  P {r['price'].get('word')}  F {r['flow'].get('vote')}"
                          f" cvd {r['flow'].get('cvd')}  {'; '.join(r['warn'])}")
                for e in tl["events"]:
                    print(f"   EVENT {e['t']} {e['kind']:5s} {e['text']}")


if __name__ == "__main__":
    main(sys.argv[1:])
