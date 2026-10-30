"""export.py -- runs the converged engine (../final/raftaar.py) minute by minute over real days and writes data.js for the
visual mockup (live.html): the engine's picture per minute + the strike grid around spot, in lakh. Read-only on data/.

    python export.py            -> data.js (NIFTY: 26 Oct trend up, 21 Oct trend down, 22 Oct chop, 6 Oct pin, 27 Oct expiry)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "final"))
import chainio  # noqa: E402
import raftaar as R  # noqa: E402
import refbuild  # noqa: E402

DAYS = [("NIFTY", "2026-10-26", "trend ▲"), ("NIFTY", "2026-10-21", "trend ▼"), ("NIFTY", "2026-10-22", "chop · stop-loss din"),
        ("NIFTY", "2026-10-06", "expiry grind / pin"), ("NIFTY", "2026-10-27", "Oct expiry")]


def L(x):
    """'+267.3L' / '−46.3L' / '0' / a number -> lakh as a float, None when absent."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return round(x / 1e5, 1)
    s = str(x).replace("−", "-").replace("L", "").replace("+", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def side(s):
    s = s or {}
    return {"x": s.get("structure"), "sp": s.get("speed"), "v": L(s.get("speed_now_L_min"))}


def lockstep(d):
    """All three indices stepped together, each seeing the others' picture as it stood (replay.run_day's loop), so the
    grades and stamps here are the official replay's. -> ({idx: [(t, out)]}, {idx: engine}, {idx: grid})"""
    engines, grids = {}, {}
    for idx in chainio.IDXS:
        grid, opens, kind = chainio.load_chain(idx, d)
        if grid:
            engines[idx] = R.Engine(idx, d, R.Ref(refbuild.load(idx)), kind, opens, chainio.load_fut(idx, d), read_words=chainio.load_read(idx, d))
            grids[idx] = grid
    outs = {idx: [] for idx in engines}
    for t in sorted({t for g in grids.values() for t in g}):
        for idx, eng in engines.items():
            if t in grids[idx]:
                peers = {o: R._peer_at(e.pic_hist, t) for o, e in engines.items() if o != idx}
                rw = R._read_word_at(eng.read_words, t) if eng.read_words else None
                outs[idx].append((t, eng.step(t, grids[idx][t], peers=peers, read_word=rw)))
    return outs, engines, grids


def day(idx, d, label):
    outs, engines, grids = lockstep(d)
    grid, eng, kind = grids[idx], engines[idx], engines[idx].kind
    ts = sorted(grid)
    spots = [grid[t]["spot"] for t in ts if grid[t].get("spot")]
    ks = sorted({float(k) for t in ts for k in grid[t]["k"]})
    step = min(b - a for a, b in zip(ks, ks[1:]) if b > a)
    keep = [k for k in ks if min(spots) - 4 * step <= k <= max(spots) + 4 * step]
    rows = []
    for t, out in outs[idx]:
        p, nb = out.get("picture") or {}, out.get("numbers") or {}
        g = p.get("grade") or {}
        cell = grid[t]["k"]
        rows.append({"t": t, "s": out.get("spot"), "w": p.get("word"), "d": p.get("dir"), "ph": p.get("phase"), "since": p.get("since"),
                     "g": [g.get("n"), g.get("N")], "gw": g.get("word"), "st": p.get("story"), "q": p.get("qual"),
                     "pk": p.get("k"), "chop": p.get("in_chop"),
                     "ce": side((out.get("sides") or {}).get("CE")), "pe": side((out.get("sides") or {}).get("PE")),
                     "m15": round(nb["m15"], 1) if isinstance(nb.get("m15"), (int, float)) else None, "cx": out.get("contradiction"),
                     # flat [ce, pe, ce, pe, ...] in lakh, aligned with "strikes" (live.html unpacks it)
                     "oi": [L((cell.get(str(int(k))) or cell.get(str(k)) or [None, None])[j]) for k in keep for j in (0, 1)]})
    stamps = [{"t": s["t"], "s": s.get("spot"), "kind": s.get("kind"), "title": s.get("title"), "why": s.get("why"), "g": s.get("grade")}
              for s in eng.stamps]                       # the engine's own full list, as replay.py prints it
    return {"idx": idx, "day": d, "label": label, "kind": kind, "step": step, "strikes": [int(k) for k in keep], "rows": rows, "stamps": stamps}


if __name__ == "__main__":
    data = [day(*x) for x in DAYS]
    js = "window.RAFTAAR = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    with open(os.path.join(HERE, "data.js"), "w", encoding="utf-8") as f:
        f.write(js)
    # one self-contained page (the data inside), so it opens anywhere, a preview pane included
    page = open(os.path.join(HERE, "live.html"), encoding="utf-8").read().replace('<script src="data.js"></script>', "<script>" + js + "</script>")
    with open(os.path.join(HERE, "RAFTAAR-live.html"), "w", encoding="utf-8") as f:
        f.write(page)
    for x in data:
        print(x["idx"], x["day"], len(x["rows"]), "min", len(x["stamps"]), "stamps", len(x["strikes"]), "strikes")
