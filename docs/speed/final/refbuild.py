"""refbuild.py -- the prior-session size reference, from data/chain, per index: ref/<IDX>.json.
{day: {"kind": NORMAL|EXPIRY, "parts": {"0".."3": {metric: [p50, p70, p90]}}}} over that session's minutes (one sample per
minute per side where a side applies). The engine picks the last 20 prior sessions of the same kind per day (causal).
Metrics (raftaar.METRICS): zone |near/wall net15| %, adds15 %, cuts15 %, |Z15| %, |D15| pts, fast gross %. Read-only on data.

    python refbuild.py            # all three indices, all recorded days
"""
import json
import os

import chainio
import raftaar as R

OUT = os.path.join(chainio.HERE, "ref")


def session_samples(idx, grid, opens):
    S, F = R.S_MIN.get(idx, 15), R.F_MIN.get(idx, 5)
    parts = {str(p): {m: [] for m in R.METRICS} for p in range(4)}
    for t in sorted(grid):
        mS, mF = R.measures(grid, t, S, opens), R.measures(grid, t, F, opens)
        if not mS or not mF or mS.get("why") or mF.get("why"):
            continue
        p = parts[str(R.part_of(t))]
        for s in ("CE", "PE"):
            p["zone"] += [abs(mS[s]["near_pct"]), abs(mS[s]["wall_pct"])]
            p["adds"].append(mS[s]["adds_pct"])
            p["cuts"].append(mS[s]["cuts_pct"])
            p["fast"].append(mF[s]["gross_pct"])
        p["Z"].append(abs(mS["Z"]))
        p["D"].append(abs(mS["m"]))
    out = {}
    for p, ms in parts.items():
        out[p] = {}
        for m, xs in ms.items():
            if len(xs) >= 10:
                out[p][m] = [R.pct(xs, 50), R.pct(xs, 70), R.pct(xs, 90)]
    return out


def build(idx):
    table = {}
    for day in chainio.days(idx):
        grid, opens, kind = chainio.load_chain(idx, day)
        if not grid or len(grid) < 60:
            continue
        table[day] = {"kind": kind, "parts": session_samples(idx, grid, opens)}
        print(idx, day, kind, {p: len(v) for p, v in table[day]["parts"].items()})
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{idx}.json"), "w", encoding="utf-8") as f:
        json.dump(table, f)
    return table


def load(idx):
    p = os.path.join(OUT, f"{idx}.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    for idx in chainio.IDXS:
        build(idx)
