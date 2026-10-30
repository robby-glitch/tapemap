"""chart_data.py -- the data behind chart_mockup.html: for each of the four real moments, the 5-min bars (from the chain spot),
the RAFTAAR ribbon per bar (big word + grade), the stamps in the window, the cap / floor deewar lines (the biggest CE wall and PE
wall strikes by OI, now and 30 min earlier, so a roll shows), the fut basis as a 3-min median (fold.BIX_MS's rule), and the
picture JSON at the moment. Writes chart_data.js next to the mockup. Read-only on the record.

    python chart_data.py
"""
import json
import os

import chainio
import refbuild
import raftaar as R

HERE = os.path.dirname(os.path.abspath(__file__))
MOMENTS = [("move", "NIFTY", "2026-10-26", "09:58"), ("chop", "NIFTY", "2026-10-22", "10:01"),
           ("pin", "NIFTY", "2026-10-06", "11:39"), ("quiet", "NIFTY", "2026-09-23", "12:30")]
BARS = 54          # 4.5 hours of 5-min bars at most


def walls(grid, opens, t):
    """(cap, floor): the CE wall strike and the PE wall strike with the biggest OI among the nine at t (spot-tagged)."""
    row = grid.get(t)
    if not row:
        return None, None
    nk, atm, why = R.nine_at(row, opens)
    if why:
        return None, None
    best = {"CE": None, "PE": None}
    for k in nk:
        c = R._cell(row, k)
        if not c:
            continue
        for i, s in enumerate(("CE", "PE")):
            wall = (k > atm) if s == "CE" else (k < atm)
            if not wall:
                continue
            oi = R._oi(opens, k, i, c[i])
            if best[s] is None or oi > best[s][1]:
                best[s] = (k, oi)
    return (best["CE"][0] if best["CE"] else None), (best["PE"][0] if best["PE"] else None)


def moment(idx, day, at):
    grid, opens, kind = chainio.load_chain(idx, day)
    fut = chainio.load_fut(idx, day)
    eng = R.Engine(idx, day, R.Ref(refbuild.load(idx)), kind, opens, fut, read_words=chainio.load_read(idx, day))
    per_min = {}
    last = None
    for t in sorted(grid):
        if t > at:
            break
        last = eng.step(t, grid[t], read_word=R._read_word_at(eng.read_words, t) if eng.read_words else None)
        pic = last["picture"]
        per_min[t] = (pic["word"], pic.get("dir"), (pic.get("grade") or {}).get("word"), (pic.get("swing") or {}).get("dir"))
    # 5-min bars from the spot, closing at :04, :09, ...
    ts = [t for t in sorted(grid) if t <= at]
    bars = []
    cur = None
    for t in ts:
        m = R.mins(t)
        b0 = m - (m - 555) % 5
        s = grid[t]["spot"]
        if cur is None or cur["m0"] != b0:
            if cur:
                bars.append(cur)
            cur = {"m0": b0, "t": R.hm(b0), "o": s, "h": s, "l": s, "c": s, "word": None}
        cur["h"], cur["l"], cur["c"] = max(cur["h"], s), min(cur["l"], s), s
        w = per_min.get(t)
        if w:
            cur["word"], cur["dir"], cur["grade"], cur["swing"] = w
    if cur:
        bars.append(cur)
    bars = bars[-BARS:]
    t0 = bars[0]["t"]
    stamps = [x for x in eng.stamps if x["t"] >= t0 and x["kind"] in ("picture", "phase", "end", "neq", "event", "q")]
    cap, floor = walls(grid, opens, at)
    cap30, floor30 = walls(grid, opens, R.hm(R.mins(at) - 30))
    # the 3-min median basis (fold.BIX_MS's rule): fut close minus chain spot, the median of the last 3 minutes
    bs = []
    for k in range(3):
        tt = R.hm(R.mins(at) - k)
        if tt in fut and tt in grid:
            bs.append(fut[tt]["c"] - grid[tt]["spot"])
    basis = R.median(bs) if bs else None
    return {"idx": idx, "day": day, "at": at, "kind": kind, "bars": bars, "stamps": stamps, "cap": cap, "floor": floor,
            "cap30": cap30, "floor30": floor30, "basis": None if basis is None else round(basis, 1), "picture": last["picture"],
            "numbers": last.get("numbers"), "sides": last.get("sides"), "contradiction": last.get("contradiction"),
            "ref": last.get("ref"), "day_drift": last.get("day_drift"), "fut": fut.get(at, {}).get("c")}


def main():
    out = {key: moment(idx, day, at) for key, idx, day, at in MOMENTS}
    js = "window.RAFTAAR_MOMENTS = " + json.dumps(out, ensure_ascii=False, default=str) + ";"
    with open(os.path.join(HERE, "chart_data.js"), "w", encoding="utf-8") as f:
        f.write(js + "\n")
    # the mockup carries the same data inline, between its markers, so it opens anywhere as one file
    import re
    hp = os.path.join(HERE, "chart_mockup.html")
    html = open(hp, encoding="utf-8").read()
    html = re.sub(r'(<script id="raftaar-data">)(.*?)(</script>)', lambda m: m.group(1) + "\n" + js + "\n" + m.group(3), html, flags=re.S)
    open(hp, "w", encoding="utf-8").write(html)
    for k, v in out.items():
        print(k, v["idx"], v["day"], v["at"], v["picture"]["word"], v["picture"].get("dir"), (v["picture"].get("grade") or {}).get("word"),
              "cap", v["cap"], "floor", v["floor"], "cap30", v["cap30"], "floor30", v["floor30"], "basis", v["basis"], "stamps", len(v["stamps"]))


if __name__ == "__main__":
    main()
