# -*- coding: utf-8 -*-
"""EXECUTE THE EDGE parity (spec §6): execute.py against the record, every NIFTY session with candles. Read-only.

    python -X utf8 docs/setup-review/check_execute_parity.py                    # PASS / FAIL
    python -X utf8 docs/setup-review/check_execute_parity.py --show 2026-11-13  # her replay: the screen at every signal
"""
import functools
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import execute as X  # noqa: E402
import look_cause_effect as L  # noqa: E402
import look_edge_walk as W  # noqa: E402
import ruler  # noqa: E402


@functools.lru_cache(maxsize=None)
def candles(day):
    ex = [b for b in ruler.ones_of(day) if b.get("c") is not None]
    cf = os.path.join(HERE, "candles", f"fut_NIFTY_{day}.json")
    if len(ex) < 300 and os.path.exists(cf):
        ex = json.load(open(cf, encoding="utf-8"))["bars"]
    return tuple(ex) if len(ex) >= 300 and sum(1 for b in ex if b.get("v")) >= 300 else None


def dext():
    out = {}
    for p in sorted(glob.glob(os.path.join(L.SCRATCH, "frame_NIFTY_*.json"))):
        f = L.load(p)
        if f and f["exch"] and f["dext"] >= 0.9:
            out[f["day"]] = {t: v for t, v in zip(f["mins"], f["delta"]) if v is not None}
        del f
    return out


def state(day, delta=None, upto=None):
    pday = X.prev_weekday(day)
    prev = candles(pday)
    return X.day_state(day, list(candles(day)), delta or {}, list(prev) if prev else None, X.contract_changed(day, pday), upto=upto)


def frame(day):
    ones = list(candles(day))
    bl = ruler.bands(ones, 3)
    d = {"day": day, "mins": [b["t"] for b in ones], "fhi": [b["h"] for b in ones], "flo": [b["l"] for b in ones],
         "fut": [b["c"] for b in ones], "blist": bl, "bars": {b["t"]: b for b in bl}}
    d["ix"] = {t: i for i, t in enumerate(d["mins"])}
    return d


def show(day):
    dl = dext().get(day)
    full = state(day, dl)
    for s in full["signals"]:
        ex = state(day, dl, upto=X.HM(X.M(s["t"]) + 2))
        print(f"\n{ex['state']} at {ex['upto']}\n" + "\n".join(ex["ticket"] or [ex["line"]]))
    print(f"\n{full['line']}")


def main(argv):
    if "--show" in argv:
        show(argv[argv.index("--show") + 1])
        return 0
    days = sorted({json.loads(l).get("day") for l in open(os.path.join(ROOT, "data", "trigger_log.jsonl"), encoding="utf-8")
                   if '"NIFTY"' in l} - {None})
    days = [d for d in days if candles(d)]
    DL, bad, A, B60, BF = dext(), 0, [], [], []
    for day in days:
        ex, d = state(day), frame(day)
        mine = [(s["t"], s["side"], s["px"], s["ext"]) for s in ex["signals"]]
        ref = [(e["t"], e["side"], e["px"], e["ext"]) for e in L.replay(d) if L.M(e["t"]) + 2 < L.LAST]
        if mine != ref:
            bad += 1
            print(f"TRIGGERS differ {day}")
        a, w = [round(x["pts"], 6) for x in ex["plan_a"]["trades"]], [round(x["pts"], 6) for x in W.walk(d, "FLIP")]
        if a != w:
            bad += 1
            print(f"PLAN A differs {day}")
        A += a
        B60 += ex["plan_b"]["trades"]
        if day in DL:
            BF += state(day, DL[day])["plan_b"]["trades"]
        for s in ex["signals"]:                                     # no look-ahead: read at its own close = read at day end
            cut = state(day, upto=X.HM(X.M(s["t"]) + 2))
            c = next((y for y in cut["signals"] if (y["t"], y["side"]) == (s["t"], s["side"])), None)
            if not c or any(c[k] != s[k] for k in ("px", "ext", "z", "vw", "chk", "b")):
                bad += 1
                print(f"LOOK-AHEAD {day} {s['t']} {s['side']}")
    late = [d for d in days if d >= L.FOUND_FROM]
    logged = {x for x in L.logged(set(late)) if L.M(x[1]) + 2 < L.LAST}
    ours = {(d, s["t"], s["side"]) for d in late for s in state(d)["signals"]}
    P = lambda xs: sum(x["pts"] for x in xs)                         # noqa: E731
    print(f"{len(days)} sessions · trigger log from {L.FOUND_FROM}: logged {len(logged)}, matched {len(logged & ours)}, "
          f"ours not logged {len(ours - logged)}")
    print(f"PLAN A: {len(A)} trades {sum(A):+.0f} (expected 257, +1,028)")
    print(f"PLAN B, every day without Dext: {len(B60)} trades {P(B60):+.0f} (expected 119, +1,650)")
    print(f"PLAN B, the order-flow days with Dext: {len(BF)} trades {P(BF):+.0f} (expected 24, +1,260)")
    ok = (bad == 0 and logged <= ours and len(A) == 257 and abs(sum(A) - 1028) < 1 and len(B60) == 119
          and abs(P(B60) - 1650) < 1 and len(BF) == 24 and abs(P(BF) - 1260) < 1)
    print("PASS" if ok else f"FAIL ({bad} differences)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
