"""explore.py -- what the nine-strike OI speed looks like, per index and day, BEFORE any state is defined. stdlib only.

Per minute t (from 09:25), on the nine strikes nearest spot at t, over the W minutes to t (strikes absent at t-W skipped):
  add_s   gross writing on side s (sum of positive per-strike changes)       cut_s  gross covering
  net_s   add - cut                                                            lean   net_PE - net_CE  (+ = up pressure)
  size_s  the nine's total OI on side s at t                                   dspot  spot(t) - spot(t-W)
Prints quantiles of |lean| as % of (size_CE + size_PE), of add/cut per side as % of its size, of |dspot| in strike steps,
and the agreement between sign(lean) and sign(dspot) when both are "big" (above their own session median).

    python explore.py NIFTY 2026-10-08 2026-10-22 ...
"""
import os
import sys

from survey import CHAIN, grid, mins, nine

W = 5


def step_of(ks):
    ks = sorted(ks)
    return min((b - a for a, b in zip(ks, ks[1:]) if b > a), default=50)


def speeds(g, w=W):
    """[{t, spot, dspot, add, cut, net, size, lean, missing}] per minute with a full w-min lookback."""
    ts = sorted(g)
    at = {mins(t): t for t in ts}
    out = []
    for t in ts:
        m = mins(t)
        b = at.get(m - w)
        if b is None or t < "09:25":
            continue
        now, was = g[t], g[b]
        nk = nine(list(now["k"]), now["spot"])
        add = {"CE": 0.0, "PE": 0.0}
        cut = {"CE": 0.0, "PE": 0.0}
        size = {"CE": 0.0, "PE": 0.0}
        miss = 0
        for k in nk:
            size["CE"] += now["oi"][k][0]
            size["PE"] += now["oi"][k][1]
            if k not in was["k"]:
                miss += 1
                continue
            for i, s in enumerate(("CE", "PE")):
                d = now["k"][k][i] - was["k"][k][i]
                if d > 0:
                    add[s] += d
                else:
                    cut[s] -= d
        net = {s: add[s] - cut[s] for s in add}
        out.append({"t": t, "spot": now["spot"], "dspot": now["spot"] - was["spot"], "add": add, "cut": cut, "net": net,
                    "size": size, "lean": net["PE"] - net["CE"], "missing": miss, "nine": nk})
    return out


def q(xs, p):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    i = min(len(xs) - 1, int(p * (len(xs) - 1) + 0.5))
    return xs[i]


def explore(idx, day):
    p = os.path.join(CHAIN, f"chain_{idx}_{day}.jsonl")
    if not os.path.exists(p):
        p += ".gz"
    g = grid(p)
    if not g:
        print(idx, day, "unreadable")
        return
    step = step_of(list(next(iter(g.values()))["k"]))
    sp = speeds(g)
    tot = [r["size"]["CE"] + r["size"]["PE"] for r in sp]
    lean_pct = [100 * abs(r["lean"]) / max(T, 1) for r, T in zip(sp, tot)]
    add_ce = [100 * r["add"]["CE"] / max(r["size"]["CE"], 1) for r in sp]
    add_pe = [100 * r["add"]["PE"] / max(r["size"]["PE"], 1) for r in sp]
    cut_ce = [100 * r["cut"]["CE"] / max(r["size"]["CE"], 1) for r in sp]
    cut_pe = [100 * r["cut"]["PE"] / max(r["size"]["PE"], 1) for r in sp]
    dsp = [abs(r["dspot"]) / step for r in sp]
    print(f"\n== {idx} {day}  step {step}  minutes {len(sp)}  size9 median {q(tot, .5) / 1e5:.1f}L  missing>0 in {sum(1 for r in sp if r['missing'])} min")
    print(f"  |lean| % of size9      p25 {q(lean_pct, .25):.3f}  p50 {q(lean_pct, .5):.3f}  p75 {q(lean_pct, .75):.3f}  p90 {q(lean_pct, .9):.3f}  max {max(lean_pct):.3f}")
    print(f"  add CE % / add PE %    p50 {q(add_ce, .5):.3f} / {q(add_pe, .5):.3f}   p90 {q(add_ce, .9):.3f} / {q(add_pe, .9):.3f}")
    print(f"  cut CE % / cut PE %    p50 {q(cut_ce, .5):.3f} / {q(cut_pe, .5):.3f}   p90 {q(cut_ce, .9):.3f} / {q(cut_pe, .9):.3f}")
    print(f"  |dspot| steps / {W}m    p50 {q(dsp, .5):.2f}  p75 {q(dsp, .75):.2f}  p90 {q(dsp, .9):.2f}  max {max(dsp):.2f}")
    # agreement: sign(lean) vs sign(dspot) where both above their own session medians
    ml, md = q([abs(r["lean"]) for r in sp], .5), q([abs(r["dspot"]) for r in sp], .5)
    big = [r for r in sp if abs(r["lean"]) > ml and abs(r["dspot"]) > md]
    agree = sum(1 for r in big if (r["lean"] > 0) == (r["dspot"] > 0))
    print(f"  big lean & big dspot: {len(big)} min, lean sign == price sign in {agree}  ({len(big) - agree} against)")
    # the same, lagged: lean over t-5..t vs price over t..t+5 (does flow lead price?)
    by = {r["t"]: r for r in sp}
    lead = ag2 = 0
    for r in sp:
        m = mins(r["t"])
        nxt = by.get(f"{(m + W) // 60:02d}:{(m + W) % 60:02d}")
        if nxt and abs(r["lean"]) > ml and abs(nxt["dspot"]) > md:
            lead += 1
            ag2 += (r["lean"] > 0) == (nxt["dspot"] > 0)
    print(f"  lean(t) vs price(t..t+{W}): {lead} min, same sign {ag2}  ({lead - ag2} against)")
    # composition census: both adding / one adding one cutting / both cutting (above the side's median add/cut)
    fl = {s: q([r["add"][s] - r["cut"][s] for r in sp], .5) for s in ("CE", "PE")}
    ma = {s: q([abs(r["net"][s]) for r in sp], .5) for s in ("CE", "PE")}
    comp = {"both add": 0, "PE add CE cut": 0, "CE add PE cut": 0, "both cut": 0, "quiet": 0}
    for r in sp:
        ce, pe = r["net"]["CE"], r["net"]["PE"]
        bce, bpe = abs(ce) > ma["CE"], abs(pe) > ma["PE"]
        if not (bce or bpe):
            comp["quiet"] += 1
        elif ce > 0 and pe > 0:
            comp["both add"] += 1
        elif ce < 0 and pe < 0:
            comp["both cut"] += 1
        elif pe > 0 and ce <= 0 or (pe > 0 and not bce):
            comp["PE add CE cut"] += 1
        else:
            comp["CE add PE cut"] += 1
    print("  composition (vs side medians):", ", ".join(f"{k} {v}" for k, v in comp.items()), f"(fl med CE {fl['CE'] / 1e5:+.2f}L PE {fl['PE'] / 1e5:+.2f}L)")
    return sp, step


if __name__ == "__main__":
    idx = sys.argv[1]
    for day in sys.argv[2:]:
        explore(idx, day)
