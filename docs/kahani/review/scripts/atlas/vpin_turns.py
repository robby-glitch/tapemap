"""VPIN during the move (her ask, 31 Oct: "check if vpin is helping us in some way during the move"). The LIVE fast line
(data/vpin_fast.jsonl, NIFTY-FUT:fast -- what her panel showed, no backfill) read the way fold.py reads it: the last
10 buckets, one-sided at imb >= 0.5, WITH / AGAINST the trade at a lead of 2 (stateless here: fold's hold-the-chip
hysteresis is left out), plus the gauge's pct (>= 0.90 = the toxic level). Checked at three points: the band signal,
the first stall (band_turns.py's signals), and the VWAP crossing of the real NIFTY band turns (atlas §9 B).
SENSEX reads NIFTY's VPIN by §1q; BANKNIFTY's is a proxy, shown apart. §1k terms: counts only, never a rate."""
import collections
import contextlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import band_turns as bt                      # its traced band signals (T) and cached frames; its prints swallowed
sys.path.insert(0, bt.ROOT)
from fold import ONE_SIDED, VPIN_LEAD, VPIN_WIN  # noqa: E402  the live chip's own numbers

STALE_S = 15 * 60                                # last bucket older than this = a hole in the live log, no read

VP = collections.defaultdict(list)
for x in open(os.path.join(bt.ROOT, "data", "vpin_fast.jsonl"), encoding="utf-8"):
    r = json.loads(x)
    if r.get("inst") == "NIFTY-FUT:fast":
        h, m, s = map(int, r["at"].split(":"))
        VP[r["day"]].append((h * 3600 + m * 60 + s, r["buy"], r["sell"], r.get("pct")))
SRC = os.environ.get("VPIN_SRC", "live")          # live (her panel's log) | tick | quote (rebuilt from the 1 s book, vpin_lab.py)
if SRC != "live":
    VP = {day: [(t, bu, se, None) for t, bu, se in B] for day, B in
          json.load(open(os.path.join(os.path.dirname(bt.A), f"buckets_{SRC}.json"), encoding="utf-8")).items()}
    print(f"(VPIN source: buckets rebuilt from the 1-second book, {SRC} rule)")
for v in VP.values():
    v.sort()


def vread(day, t_s, s):
    """(chip, pct) from the buckets complete by t_s seconds, for a trade in direction s; None when the log can't say."""
    b = [r for r in VP.get(day, ()) if r[0] <= t_s][-VPIN_WIN:]
    if len(b) < VPIN_WIN or t_s - b[-1][0] > STALE_S:
        return None
    one = [1 if bu > se else -1 for _, bu, se, _ in b if bu + se and abs(bu - se) / (bu + se) >= ONE_SIDED]
    net = s * sum(one)
    return ("WITH" if net >= VPIN_LEAD else "AGAINST" if net <= -VPIN_LEAD else "QUIET"), b[-1][3]


CHIPS = ("WITH", "QUIET", "AGAINST", "no read")


def tally(title, rows, key, outs):
    print(title)
    for c in CHIPS:
        X = [r for r in rows if key(r) == c]
        if X:
            print(f"  VPIN {c:<8} n {len(X):>3}: " + " · ".join(f"{lbl} {sum(map(f, X))}" for lbl, f in outs))


chip = lambda v: v[0] if v else "no read"
hot = lambda v: "no read" if not v or v[1] is None else "WITH" if v[1] >= 0.90 else "QUIET"   # pct >= 0.90 shown as WITH

for x in bt.T:
    s = 1 if x["side"] == "BUY" else -1
    x["v_sig"] = vread(x["day"], bt.m2i(x["t"]) * 60, s)                  # the bar closed at x["t"]
    st = x["stall"]
    x["v_st"] = vread(x["day"], (bt.m2i(st["t"]) + 1) * 60, s) if st else None

print("== 1. at the band signal: VPIN chip in the trade's direction -> which came first in the next 60 min ==")
first = (("+1σ first", lambda r: r["first"] == "+1σ"), ("−1σ first", lambda r: r["first"] == "−1σ"),
         ("neither", lambda r: r["first"] == "neither"))
tally("all band signals (n %d)" % len(bt.T), bt.T, lambda r: chip(r["v_sig"]), first)
tally("  without BANKNIFTY", [r for r in bt.T if r["idx"] != "BANKNIFTY"], lambda r: chip(r["v_sig"]), first)
tally("  pct >= 0.90 at the signal (WITH = hot)", bt.T, lambda r: hot(r["v_sig"]), first)

print("\n== 2. at the first stall (her exit point): VPIN chip -> did the move go on? ==")
S = [x for x in bt.T if x["stall"]]
on = (("went on ≥ +0.5σ", lambda r: r["stall"]["went_on"] >= 0.5 * r["sd"]),
      ("came back to entry", lambda r: r["stall"]["then_back_to_E"]))
tally("all stalls (n %d)" % len(S), S, lambda r: chip(r["v_st"]), on)
tally("  without BANKNIFTY", [r for r in S if r["idx"] != "BANKNIFTY"], lambda r: chip(r["v_st"]), on)
tally("  pct >= 0.90 at the stall (WITH = hot)", S, lambda r: hot(r["v_st"]), on)
for lbl, f in (("delta AGAINST at the stall", lambda r: r["stall"]["delta_with"] is False),
               ("delta WITH at the stall", lambda r: r["stall"]["delta_with"] is True)):
    tally(f"  {lbl}, split by VPIN", [r for r in S if f(r)], lambda r: chip(r["v_st"]), on)

print("\n== 3. real NIFTY band turns (atlas §9 B): VPIN at the turn and at the VWAP crossing -> band to band? ==")
legs = collections.defaultdict(list)
for L in json.load(open(os.path.join(os.path.dirname(bt.A), "atlas_legs.json"), encoding="utf-8")):
    legs[L["day"]].append(L)
turns = []
for day, Ls in sorted(legs.items()):
    d = bt.frame("NIFTY", day)
    Ls.sort(key=lambda L: L["birth"])
    for a, b in zip(Ls, Ls[1:]):
        if b["dir"] == a["dir"] or a["extreme_t"] not in d["mins"] or b["extreme_t"] not in d["mins"]:
            continue
        i, j = d["mins"].index(a["extreme_t"]), d["mins"].index(b["extreme_t"])
        if not d["sd"][i] or not d["sd"][j] or a["extreme_t"] < "09:45" or b["pts"] < 40:
            continue
        if (a["extreme"] - d["vwap"][i]) / d["sd"][i] * a["dir"] < 2:
            continue
        zb = (b["extreme"] - d["vwap"][j]) / d["sd"][j] * b["dir"]
        k = next((k for k in range(i + 1, j + 1) if (d["fut"][k] - d["vwap"][k]) * b["dir"] >= 0), None)
        turns.append({"day": day, "t": a["extreme_t"], "pts": b["pts"], "zb": zb, "b2b": zb >= 2,
                      "vwap_t": d["mins"][k] if k is not None else None,
                      "v_turn": vread(day, (bt.m2i(a["extreme_t"]) + 1) * 60, b["dir"]),
                      "v_vwap": vread(day, (bt.m2i(d["mins"][k]) + 1) * 60, b["dir"]) if k is not None else None})
print(f"turns {len(turns)} · band to band {sum(t['b2b'] for t in turns)}")
b2b = (("band to band", lambda r: r["b2b"]), ("stopped short of the far band", lambda r: not r["b2b"]))
tally("  VPIN at the turn (in the turn's direction)", turns, lambda r: chip(r["v_turn"]), b2b)
X = [t for t in turns if t["vwap_t"]]
tally("  VPIN at the VWAP crossing (FADE -> RIDE point, n %d)" % len(X), X, lambda r: chip(r["v_vwap"]), b2b)
tally("  pct >= 0.90 at the VWAP crossing (WITH = hot)", X, lambda r: hot(r["v_vwap"]), b2b)
fmt = lambda v: "no read" if not v else f"{v[0]} {'' if v[1] is None else f'{v[1]:.0%}'}"
for t in turns:
    print(f"  {t['day']} turn {t['t']} -> {t['pts']:>3} pts, ended {t['zb']:+.1f}σ{' BAND TO BAND' if t['b2b'] else ''}"
          f" | VPIN at turn {fmt(t['v_turn'])} · at VWAP {t['vwap_t'] or '-'} {fmt(t['v_vwap'])}")
