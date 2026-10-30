"""review_run.py -- round-3 review harness for the converged engine (docs/speed/final), run READ-ONLY on final/.

Imports final/ from its folder (run with `python -B` so no __pycache__ lands there); writes only under opus/review/.

    python -B -X utf8 review_run.py replay DAY...        stamps + every minute -> review/<IDX>_<day>.txt (fresh, same as replay.py)
    python -B -X utf8 review_run.py trunc DAY HH:MM...   truncate the day at each T, rerun, compare the picture at T with the full run
    python -B -X utf8 review_run.py refs                 which sessions each day's reference reads (look-ahead check)
    python -B -X utf8 review_run.py cost DAY             seconds per Engine.step
"""
import copy
import json
import os
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.normpath(os.path.join(HERE, "..", "final"))
sys.path.insert(0, FINAL)
import chainio      # noqa: E402
import refbuild     # noqa: E402
import raftaar as R  # noqa: E402

OUT = os.path.join(HERE, "review")


def inputs(day, upto=None):
    data = {}
    for idx in chainio.IDXS:
        grid, opens, kind = chainio.load_chain(idx, day)
        if not grid:
            continue
        fut = chainio.load_fut(idx, day)
        rw = chainio.load_read(idx, day)
        if upto:
            grid = {t: v for t, v in grid.items() if t <= upto}
            fut = {t: v for t, v in fut.items() if t <= upto}
            rw = [x for x in rw if x[0] <= upto]
        data[idx] = (grid, opens, kind, fut, rw)
    return data


def run(day, upto=None, keep_all=True):
    data = inputs(day, upto)
    eng = {idx: R.Engine(idx, day, R.Ref(refbuild.load(idx)), kind, opens, fut, read_words=rw)
           for idx, (grid, opens, kind, fut, rw) in data.items()}
    minutes = sorted({t for d in data.values() for t in d[0]})
    pics = {idx: {} for idx in eng}
    for t in minutes:
        for idx, e in eng.items():
            g = data[idx][0]
            if t not in g:
                continue
            peers = {o: R._peer_at(x.pic_hist, t) for o, x in eng.items() if o != idx}
            rw = R._read_word_at(e.read_words, t) if e.read_words else None
            out = e.step(t, g[t], peers=peers, read_word=rw)
            if keep_all:
                pics[idx][t] = json.loads(json.dumps({k: v for k, v in out.items() if k != "stamps"}, default=str))
    stamps = {idx: json.loads(json.dumps(e.stamps, default=str)) for idx, e in eng.items()}
    return eng, pics, stamps, data


def word(p):
    pic = (p or {}).get("picture") or {}
    w = pic.get("word") or "?"
    d = pic.get("dir")
    a = (" ▲" if d == 1 else " ▼" if d == -1 else "")
    g = pic.get("grade")
    sw = pic.get("swing")
    extra = f" ~swing{' ▲' if sw and sw['dir'] == 1 else ' ▼' if sw else ''}" if sw else ""
    return f"{w}{a}{extra} {pic.get('phase') or ''} {g['n']}/{g['N']} {g['word']}" if g else f"{w}{a}{extra} {pic.get('phase') or ''}"


def cmd_replay(days):
    os.makedirs(OUT, exist_ok=True)
    for day in days:
        eng, pics, stamps, data = run(day)
        for idx in eng:
            L = [f"== {idx} {day} (fresh run of final/raftaar.py) ref: {eng[idx].ref.source()}", ""]
            for s in stamps[idx]:
                L.append(f"{s['t']}  {s['spot'] or 0:>8.0f}s  {s['kind']:<8} {s['title']:<36} {s.get('grade') or '':<14} {s['why']}")
            L += ["", "-- every minute:"]
            for t, p in pics[idx].items():
                st = (p.get("picture") or {}).get("story") or (p.get("picture") or {}).get("why") or ""
                L.append(f"{t} {p.get('spot') or 0:>8.1f} | {word(p):<34} | {st}")
            with open(os.path.join(OUT, f"{idx}_{day}.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(L) + "\n")
            kinds = {}
            for s in stamps[idx]:
                kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
            print(day, idx, len(stamps[idx]), kinds)


def cmd_trunc(day, ts):
    _, full, fstamps, _ = run(day)
    bad = 0
    for T in ts:
        _, cut, cstamps, _ = run(day, upto=T)
        for idx in full:
            a, b = full[idx].get(T), cut[idx].get(T)
            same = a == b
            sa = [(s["t"], s["title"], s.get("grade")) for s in fstamps[idx] if s["t"] <= T]
            sb = [(s["t"], s["title"], s.get("grade")) for s in cstamps[idx]]
            print(f"{day} {T} {idx:<9} picture identical: {same}   stamps<=T identical: {sa == sb}  ({len(sa)} vs {len(sb)})")
            if not same:
                bad += 1
                for k in a:
                    if a.get(k) != b.get(k):
                        print("   differs:", k)
            if sa != sb:
                for x, y in zip(sa + [None] * 9, sb + [None] * 9):
                    if x != y:
                        print("   full:", x, "\n   cut: ", y)
                        break
    print("pictures differing:", bad)


def cmd_refs():
    for idx in chainio.IDXS:
        table = refbuild.load(idx)
        for day in ("2026-10-08", "2026-10-22", "2026-10-26", "2026-10-27"):
            kind = table.get(day, {}).get("kind") or chainio.load_chain(idx, day)[2]
            ref = R.Ref(table).for_day(day, kind)
            prior = sorted(d for d in table if d < day and table[d].get("kind") == kind)[-R.REF_DAYS:]
            print(idx, day, kind, "sessions", ref.n_sessions, "newest used", prior[-1] if prior else None,
                  "table has", len(table), "days, newest", max(table), "| today in table:", day in table)


def cmd_cost(day):
    data = inputs(day)
    for idx, (grid, opens, kind, fut, rw) in data.items():
        e = R.Engine(idx, day, R.Ref(refbuild.load(idx)), kind, opens, fut, read_words=rw)
        ts = sorted(grid)
        t0 = time.perf_counter()
        worst = 0.0
        for t in ts:
            a = time.perf_counter()
            e.step(t, grid[t], read_word=R._read_word_at(rw, t) if rw else None)
            worst = max(worst, time.perf_counter() - a)
        dt = time.perf_counter() - t0
        print(f"{idx} {day} {len(ts)} steps  {1000 * dt / len(ts):.1f} ms/step mean  {1000 * worst:.1f} ms worst  "
              f"grid kept {len(e.grid)} minutes, series {sum(len(v) for v in e.series.values())} points")


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "replay":
        cmd_replay(sys.argv[2:])
    elif c == "trunc":
        cmd_trunc(sys.argv[2], sys.argv[3:])
    elif c == "refs":
        cmd_refs()
    elif c == "cost":
        cmd_cost(sys.argv[2])
