"""tools/fold_replay.py -- replay the rev 6 engine (fold.py) on the recorded design trades and print
6-blueprint.md §4.9's table beside what fold.py exits at. Read-only on data/; writes nothing.

    python tools/fold_replay.py            # the 8 design trades + the sold mirrors S1-S8 + the re-entry read R-A2
    python tools/fold_replay.py H2 A1      # a subset
    python tools/fold_replay.py --resume   # also: a mid-day restart on each day yields the same events (P2-02's test, on disk)

The bucket for a day pools the prior sessions on disk the way the harness did (h3/build.py through
fold.session_from_book), oldest first, up to 5. 22 Sep has none on disk: its bucket is the day's own first
15 minutes, not causal before 09:30, and no VPIN rows exist for it.
"""
import bisect
import gzip
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import fold  # noqa: E402

D = os.path.join(ROOT, "data")
PRIORS = {"2026-09-22": [], "2026-09-23": ["2026-09-22"], "2026-09-24": ["2026-09-22", "2026-09-23"],
          "2026-09-25": ["2026-09-22", "2026-09-23", "2026-09-24"],
          "2026-09-28": ["2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25"]}
EXPIRY = {"2026-09-22": "2026-09-22"}          # the weekly that expired on a design day
# name, day, k, ty, side, p0, entry, blueprint-6 exit (pct, hh:mm[:ss], rule) -- §4.9 and t5/j6
DESIGN = [
    ("A1", "2026-09-22", 23450, "PE", "BUY", 47.75, "09:39:44", (199, "14:12:45", "expiry")),
    ("A2", "2026-09-22", 23350, "CE", "BUY", 43.65, "12:01:43", (-42, "13:51:16", "accept")),
    ("A3", "2026-09-23", 23450, "PE", "BUY", 122.3, "10:40:47", (-12, "12:04:57", "accept")),
    ("A4", "2026-09-25", 23150, "PE", "BUY", 111.6, "09:31:38", (7, "10:09:29", "held")),
    ("A5", "2026-09-25", 23150, "CE", "BUY", 96.5, "09:39:28", (-10, "09:47:03", "accept")),
    ("A6", "2026-09-28", 22950, "CE", "BUY", 84.05, "09:31:31", (-17, "10:16:12", "accept")),
    ("H1", "2026-09-24", 23250, "PE", "BUY", 102.65, "09:30:00", (98, "14:39:36", "held")),
    ("H2", "2026-09-28", 23000, "PE", "BUY", 120.4, "09:30:27", (None, "15:00", "none (+71)")),
    ("R-A2", "2026-09-22", 23350, "CE", "BUY", 68.35, "14:15:02", (None, "15:00", "none (-43)")),
]
# sold mirrors: the other side at the same second; p0 = that leg's LTP on the first chain snapshot at/after entry
MIRROR = {"A1": (84, "14:12:45", "expiry"), "A2": (-40, "13:51:16", "accept"), "A3": None, "A4": None, "A5": None,
          "A6": None, "H1": None, "H2": None}
_cache = {}


def rows(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        out = []
        for line in f:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out


def _p(path):
    """The file, or its gzipped copy (daylog.py gzips week-old days), or None."""
    return path if os.path.exists(path) else path + ".gz" if os.path.exists(path + ".gz") else None


def have_day(day, idx="NIFTY"):
    return all(_p(os.path.join(D, d, f"{f}_{idx}_{day}.jsonl")) for d, f in (("book", "book"), ("chain", "chain"))) \
        and all(have_day(p, idx) for p in PRIORS.get(day, []))


def day_files(day, idx="NIFTY"):
    if day not in _cache:
        tp = _p(os.path.join(D, "tape", f"tape_{idx}_{day}.jsonl"))
        _cache[day] = dict(book=rows(_p(os.path.join(D, "book", f"book_{idx}_{day}.jsonl"))),
                           chain=rows(_p(os.path.join(D, "chain", f"chain_{idx}_{day}.jsonl"))),
                           tape=rows(tp) if tp else [])
    return _cache[day]


def prior_sessions(day):
    out = []
    for p in PRIORS.get(day, [])[-fold.PRIOR_N:]:
        key = ("prior", p)
        if key not in _cache:
            _cache[key] = fold.session_from_book(day_files(p)["book"], lot=65, idx="NIFTY", day=p)
        out.append(_cache[key])
    return out


def inputs_for(day):
    f = day_files(day)
    if "vpin" not in _cache:
        _cache["vpin"] = rows(os.path.join(D, "vpin_fast.jsonl"))
    return dict(day=day, idx="NIFTY", lot=65, book=f["book"], chain=f["chain"], tape=f["tape"], vpin=_cache["vpin"],
                prior=prior_sessions(day), expiry=EXPIRY.get(day))


def prem_path(chain, day, k, ty, t0, t1):
    out = []
    for c in chain:
        t = fold.ms(day, c["ts"])
        if t0 <= t <= t1:
            x = next((x for x in c["strikes"] if x["k"] == k), None)
            if x and x[ty].get("ltp"):
                out.append((t, x[ty]["ltp"]))
    return out


ZONE_FORM = {"WITH": "behind you: ", "AGAINST": "at ", "QUIET": "no level born or broken since ", "CAN'T CHECK": "could not check"}


def zone_agrees(chip, sentence):
    return chip is None or (sentence or "").startswith(ZONE_FORM[chip])


def zone_sentence(v, e):
    return e["row"]["sentences"]["Z"]


def run(name, day, k, ty, side, p0, entry, expect, end="15:00:00"):
    inp = inputs_for(day)
    trade = dict(k=k, ty=ty, side=side, p0=p0, entry_t=entry, trade_id=name)
    t0 = time.time()
    v = fold.read(trade, inp, upto=end)
    dt = time.time() - t0
    own = 1 if side == "BUY" else -1
    pct = lambda p: None if p is None else round(100 * own * (p - p0) / p0)   # noqa: E731
    path = prem_path(inp["chain"], day, k, ty.lower(), fold.ms(day, entry), fold.ms(day, end))
    best = max(path, key=lambda x: own * x[1]) if path else (None, None)
    folds = [e for e in v["events"] if e["kind"] == "fold"]
    f = folds[0] if folds else None
    endp = path[-1][1] if path else None
    if f:
        i = bisect.bisect_right([x[0] for x in path], f["t"]) - 1
        fp = path[i][1] if i >= 0 else None
        got = (pct(fp), f["ts"], f["why"])
        peak = max((x[1] for x in path if x[0] <= f["t"]), key=lambda p: own * p, default=None)
    else:
        got = (pct(endp), end[:5], "none")
        peak = best[1]
    ok = ((got[2] == "none") if expect[0] is None else (got[0] == expect[0] and got[1][:5] == expect[1][:5])) if expect else None
    holes = "; ".join(f"{h['t0'][:5]}-{h['t1'][:5]} {h['why']}" for h in v["holes"])
    zbad = [e["ts"] for e in v["events"] if e["kind"] == "bucket" and not zone_agrees(e["row"]["chips"]["Z"], zone_sentence(v, e))]
    if zbad:
        print(f"   ZONE sentence disagrees with its chip on {len(zbad)} rows, first {zbad[0]}")
    print(f"{name:5} {day} {'long' if own > 0 else 'short'} {k}{ty} @ {p0} {entry} | best {pct(best[1])}% {fold.hms(best[0]) if best[0] else '-'} "
          f"| 15:00 {pct(endp)}% | EXIT {got} | blueprint {expect} | {'MATCH' if ok else 'DIFFERS' if ok is False else 'n/a'} "
          f"| peak->exit {pct(peak)}->{got[0]} | G {v['G']['px']} W {v['W'] and v['W']['k']} | {len(v['events'])} events, {dt:.1f}s"
          + (f" | holes: {holes}" if holes else ""))
    return v, got


def resume_check(name, day, k, ty, side, p0, entry, restart="12:30:00", end="15:00:00"):
    """A live run to `end` in 1-minute batches, against a restart at `restart` that recomputes from the rows:
    the same events, word for word (the P2-02 test on disk)."""
    inp = inputs_for(day)
    trade = dict(k=k, ty=ty, side=side, p0=p0, entry_t=entry, trade_id=name)
    live = fold.State(trade, dict(inp, book=[], chain=[]))
    live.feed(vpin=inp["vpin"], tape=inp["tape"])
    keys = sorted([(r["t"], 1, r) for r in inp["book"]] + [(fold.ms(day, r["ts"]), 0, r) for r in inp["chain"]], key=lambda x: (x[0], x[1]))
    T_end = fold.ms(day, end)
    i, step = 0, 60000
    t = keys[0][0] if keys else T_end
    while t <= T_end and i < len(keys):
        b, c = [], []
        while i < len(keys) and keys[i][0] < t + step and keys[i][0] <= T_end:
            (b if keys[i][1] else c).append(keys[i][2])
            i += 1
        fold.step(live, dict(book=b, chain=c), now=min(t + step, T_end))
        t += step
    again = fold.read(trade, inp, upto=end)
    a, b = live.events, again["events"]
    diff = [(x["seq"], x["ts"], x["kind"], x["text"]) for x, y in zip(a, b)
            if (x["ts"], x["kind"], x["text"], x["row"]["headline"], x["row"]["line2"]) != (y["ts"], y["kind"], y["text"], y["row"]["headline"], y["row"]["line2"])]
    print(f"   resume {name}: live {len(a)} events v recompute {len(b)}; diverged {len(diff) + abs(len(a) - len(b))}"
          + (f" first: {diff[0]}" if diff else ""))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    want = set(args) or {t[0] for t in DESIGN}
    for name, day, k, ty, side, p0, entry, expect in DESIGN:
        if name not in want:
            continue
        run(name, day, k, ty, side, p0, entry, expect)
        if name in MIRROR and not name.startswith("R"):
            oty = "CE" if ty == "PE" else "PE"
            inp = inputs_for(day)
            te = fold.ms(day, entry)
            snap = next(c for c in inp["chain"] if fold.ms(day, c["ts"]) >= te)
            mp0 = next(x for x in snap["strikes"] if x["k"] == k)[oty.lower()]["ltp"]
            run("S-" + name, day, k, oty, "SELL", mp0, entry, MIRROR.get(name))
        if "--resume" in sys.argv:
            resume_check(name, day, k, ty, side, p0, entry)
