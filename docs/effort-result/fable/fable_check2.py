"""Fable, check 2: (1) does the SIGN of the 10-bucket window carry the stall split, or the bucket count since the signal?
(2) the 77 touches with outcomes anchored on the touch PRICE (two yardsticks). Read-only; in-sample; counts only."""
import collections
import contextlib
import io
import json
import os
import statistics
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
with contextlib.redirect_stdout(io.StringIO()):
    import fable_check as F                     # re-runs the loads (a minute); reuses its S, BQ, TR, FRM, bt
OUT = open(os.path.join(HERE, "fable_check2_out.txt"), "w", encoding="utf-8")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    OUT.write(s + "\n")


S, BQ, TR, FRM, bt = F.S, F.BQ, F.TR, F.FRM, F.bt
P("== 1. the band stalls: sign vs bucket count ==")
for x in S:
    t_s = (x["st"]["m"] + 1) * 60
    sig_s = bt.m2i(x["t"]) * 60
    B = BQ.get(x["day"], [])
    x["nb"] = sum(1 for b in B if sig_s <= b[1] <= t_s)                       # buckets closed signal -> stall
    w = [b for b in B if b[1] <= t_s][-10:]
    x["pre"] = sum(1 for b in w if b[1] < sig_s)                              # of the 10, closed before the signal
    x["after"] = x["st"]["m"] - bt.m2i(x["t"])
    x["best_sd"] = x["st"]["best"] / x["sd"]
    # sign of the SINCE-SIGNAL buckets only (no pre-signal bucket in the read), lead >= 2 on however many there are
    one = [1 if b[4] > b[5] else -1 for b in w if b[1] >= sig_s and abs(b[4] - b[5]) / (b[4] + b[5]) >= 0.5]
    net = x["s"] * sum(one)
    x["chip_since"] = "WITH" if net >= 2 else "AGAINST" if net <= -2 else "QUIET"
P("chip (quote) -> minutes signal->stall, best at the stall in sigma, pre-signal buckets inside the 10-bucket window:")
for chip in ("WITH", "QUIET", "AGAINST"):
    X = [x for x in S if x["chip_quote"] == chip]
    P(f"  {chip:<8} n {len(X):>3} · signal->stall median {statistics.median(x['after'] for x in X):.0f} min"
      f" · best median {statistics.median(x['best_sd'] for x in X):.2f} sigma"
      f" · pre-signal buckets in the window: median {statistics.median(x['pre'] for x in X):.0f}, none {sum(x['pre'] == 0 for x in X)}, >= 5 {sum(x['pre'] >= 5 for x in X)}")
P("\nsign-blind proxy: buckets closed since the signal (tape speed only, no sign):")
for lbl, lo, hi in (("< 5", 0, 5), ("5-9", 5, 10), (">= 10", 10, 999)):
    X = [x for x in S if lo <= x["nb"] < hi]
    P(f"  {lbl:<6} n {len(X):>3} · went on {sum(x['st']['went_on'] for x in X):>2}"
      f" · chips: " + " ".join(f"{c} {sum(x['chip_quote'] == c for x in X)}" for c in ("WITH", "QUIET", "AGAINST", "no read")))
P("\nwithin the fast-tape stalls (>= 10 buckets since the signal), by chip:")
for chip in ("WITH", "QUIET", "AGAINST"):
    X = [x for x in S if x["nb"] >= 10 and x["chip_quote"] == chip]
    P(f"  {chip:<8} n {len(X):>3} · went on {sum(x['st']['went_on'] for x in X)}")
P("within the slow-tape stalls (< 10 buckets since the signal), by chip:")
for chip in ("WITH", "QUIET", "AGAINST"):
    X = [x for x in S if x["nb"] < 10 and x["chip_quote"] == chip]
    P(f"  {chip:<8} n {len(X):>3} · went on {sum(x['st']['went_on'] for x in X)}")
P("\nthe chip read on SINCE-SIGNAL buckets only (pre-signal buckets dropped; lead >= 2):")
for chip in ("WITH", "QUIET", "AGAINST"):
    X = [x for x in S if x["chip_since"] == chip]
    P(f"  {chip:<8} n {len(X):>3} · went on {sum(x['st']['went_on'] for x in X)} · unique episodes {len({(x['day'], x['st']['m'] // 5) for x in X})}")
P("\nWITH stalls (quote), one line each:")
for x in sorted((x for x in S if x["chip_quote"] == "WITH"), key=lambda x: (x["day"], x["st"]["t"])):
    P(f"  {x['day']} {x['idx']:<9} {x['side']} sig {x['t']} stall {x['st']['t']} (+{x['after']} min, best {x['best_sd']:.2f}σ,"
      f" {x['nb']} buckets since signal, pre {x['pre']}) went on {x['st']['went_on']} · {x['grp'][:22]}")

P("\n== 2. the 77 touches, outcomes anchored on the touch PRICE ==")
touches = json.load(open(os.path.join(tempfile.gettempdir(), "jarvis_atlas", "touches.json"), encoding="utf-8"))
ITEMS = [k for k in touches[0] if k[0].isdigit()]


def outcome(r, back_sd, fwd_sd):
    d = FRM[r["day"]]
    j = d["mins"].index(r["t"])
    s = 1 if r["side"] == "top" else -1
    sd, px = d["sd"][j], d["fut"][j]
    for k in range(j + 1, min(len(d["mins"]), j + 61)):
        if d["fhi"][k] is None or d["flo"][k] is None:
            continue
        if s * ((d["fhi"][k] if s > 0 else d["flo"][k]) - px) >= fwd_sd * sd:
            return "BREAK"
        if s * (px - (d["flo"][k] if s > 0 else d["fhi"][k])) >= back_sd * sd:
            return "TURN"
    return "WALK"


for lbl, back, fwd in (("TURN = 1σ back from the touch price first / BREAK = 1σ further first", 1.0, 1.0),
                       ("vpin_lab's FIRST definition: BREAK = 0.5σ further first / TURN = 1σ back", 1.0, 0.5)):
    P(f"\n{lbl}:")
    W = {r["t"] + r["day"]: outcome(r, back, fwd) for r in touches}
    P("  all 77: " + " · ".join(f"{w} {sum(1 for v in W.values() if v == w)}" for w in ("TURN", "BREAK", "WALK")))
    for grp, X in (("before 10:15", [r for r in touches if r["t"] < "10:15"]), ("after 10:15", [r for r in touches if r["t"] >= "10:15"])):
        P(f"  {grp}: n {len(X)}: " + " · ".join(f"{w} {sum(1 for r in X if W[r['t'] + r['day']] == w)}" for w in ("TURN", "BREAK", "WALK")))
    for k in ITEMS:
        parts = []
        for v in ("yes", "no"):
            X = [r for r in touches if r.get(k) == v]
            if X:
                parts.append(f"{v} {len(X)}: turn {sum(W[r['t'] + r['day']] == 'TURN' for r in X)} / break {sum(W[r['t'] + r['day']] == 'BREAK' for r in X)} / walk {sum(W[r['t'] + r['day']] == 'WALK' for r in X)}")
        P(f"  {k[:58]:<58} " + " · ".join(parts))
OUT.close()
