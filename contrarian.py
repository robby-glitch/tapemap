"""Phase 3 research — the three PRE-REGISTERED contrarian tests, through the
measure.py harness (spec follow-ups, 2026-07-28-measurement-harness-design.md):

  1. BUYER-BUILD inverted   (original: 16% hit, CI 7-33, the only clear cell)
  2. Gamma-agreement inverted: ARMED/SPRING scored separately when they FIGHT
     vs AGREE with the MM-regime lean (naive scorer said FIGHT 61% > AGREE 33%)
  3. CARRY inverted: next-day open->close traded OPPOSITE the EOD carry verdict
     (naive scorer said CARRY correct only 11/30)

Pre-registered means: these three, nothing else, no grids. Anything further
found here is hypothesis-generation, not evidence.

  python contrarian.py --run
"""
import statistics
import sys

from measure import causal_R, report, score_day, wilson

COST_PTS = 1.5


def _lean(regime):
    return {"FLOOR": 1, "AMPLIFIED-UP": 1,
            "CEILING": -1, "AMPLIFIED-DOWN": -1}.get(regime, 0)


def _carry_bias(msg):
    m = (msg or "").upper()
    return 1 if "BULLISH" in m else (-1 if "BEARISH" in m else 0)


def _dir_side(data):
    s = (data or {}).get("side")
    return 1 if s == "UP" else -1 if s == "DN" else 0


def _days():
    import glob
    import os
    import backtest as bt
    from engine import Session, session_json
    names = sorted(os.path.basename(p)[4:14]
                   for p in glob.glob("data/backtest/fut_*.json"))
    opt = {os.path.basename(p)[4:14]
           for p in glob.glob("data/backtest/opt_*.json")}
    names = [d for d in names if d in opt]
    out = []
    prior_R = None
    for i in range(1, len(names)):
        day, prev = names[i], names[i - 1]
        try:
            fut, ce, pe, strike, _h, _n = bt.load_day(day, prev)
            s = Session(day, fut, ce, pe, quiet=True, strike=strike,
                        t_days=bt._t_days(day))
            s.run()
            js = session_json(s)
        except Exception as ex:
            print(f"  {day}: ERROR {ex}")
            continue
        nb = [{"t": b["T"], "h": b["H"], "l": b["L"], "c": b["C"]} for b in fut]
        out.append((day, js, nb, prior_R,
                    (fut[0]["O"], fut[-1]["C"])))
        Rs = causal_R(nb)
        prior_R = next((r for r in reversed(Rs) if r), prior_R)
    return out


def run():
    data = _days()
    recs = []
    for day, js, nb, prior_R, _oc in data:
        bar_by_t = {b["t"]: b for b in js["bars"]}
        sigs = []
        for e in js["events"]:
            if e["kind"] == "BUYER-BUILD":
                m = (e["msg"] or "").upper()
                d0 = 1 if "BULLISH" in m else (-1 if "BEARISH" in m else 0)
                if d0:
                    sigs.append({"t": e["t"], "kind": "BB-INVERTED",
                                 "dir": -d0})
            elif e["kind"] in ("ARMED", "SPRING"):
                dr = _dir_side(e.get("data"))
                if not dr:
                    continue
                gam = ((bar_by_t.get(e["t"]) or {}).get("gamma")
                       or {}).get("regime")
                lean = _lean(gam)
                if lean == 0:
                    kind = "DIR-NEUTRAL"
                elif lean == dr:
                    kind = "DIR-AGREE"
                else:
                    kind = "DIR-FIGHT"
                sigs.append({"t": e["t"], "kind": kind, "dir": dr})
        recs += score_day(nb, sigs, prior_R=prior_R)
    report(recs, "PHASE 3 — inversions, 54 days, harness defaults")

    # CARRY inverted: next-day open->close, traded OPPOSITE the verdict
    w = n = 0
    pnl = []
    for i in range(len(data) - 1):
        _d, js, _nb, _pR, _oc = data[i]
        carry = next((e for e in js["events"] if e["kind"] == "CARRY"), None)
        bias = _carry_bias(carry and carry["msg"])
        if not bias:
            continue
        nxt_open, nxt_close = data[i + 1][4]
        moved = nxt_close - nxt_open
        inv_pts = -bias * moved - COST_PTS
        pnl.append(inv_pts)
        n += 1
        w += inv_pts > 0
    if n:
        lo, hi = wilson(w, n)
        print(f"\nCARRY-INVERTED (next-day open->close, cost {COST_PTS}pt): "
              f"n={n} profitable {w} ({w/n*100:.0f}%, "
              f"CI {lo*100:.0f}-{hi*100:.0f})"
              f"  avg {statistics.mean(pnl):+.1f} pts"
              f"  median {statistics.median(pnl):+.1f} pts")
    else:
        print("\nCARRY-INVERTED: no samples")


if __name__ == "__main__":
    if "--run" in sys.argv:
        run()
    else:
        print(__doc__)
