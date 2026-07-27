"""BREAKGO research — both-books continuation signal (Phase 2).
Spec: docs/superpowers/specs/2026-07-28-continuation-signal-design.md

Generates continuation signals (trade WITH the break of a strong level, only
when the ATM option books agree) and validates them through the measure.py
harness with a 35/19 walk-forward. This is research: nothing here ships into
the engine/UI unless the validation split is +EV after costs.

  python continuation.py --walkforward
  python continuation.py --live <payload.json>     # inspect one day's signals
"""
import json
import statistics
import sys
from pathlib import Path

from measure import causal_R, score_day, wilson, DEFAULTS

ROOT = Path(__file__).parent
SESSION_AGE = 30          # bars a session extreme must stand before it's a pool


def _confirmed(bar, direction, mode):
    """Both-books agreement at the trigger bar. UP: call writers covering
    (ce oi_slope < 0) while put writers add (pe oi_slope > 0); DOWN mirrored."""
    ce = (bar.get("ce") or {}).get("oi_slope") or 0
    pe = (bar.get("pe") or {}).get("oi_slope") or 0
    up = (ce < 0, pe > 0) if direction > 0 else (pe < 0, ce > 0)
    if mode == "both":
        return all(up)
    if mode == "either":
        return any(up)
    return True                                       # 'none' control


def generate(bars, pdh, pdl, Rs, prior_R, margin, confirm):
    """One pass over session_json-style bars -> [{t, kind, dir}].

    Pools: PDH/PDL (static) + session extremes ≥SESSION_AGE bars old. One
    trigger per pool per direction per day. A gap-open beyond PDH/PDL counts
    as a break on the first bar (it IS the first close beyond the level)."""
    sigs = []
    hi = lo = None
    hi_i = lo_i = 0
    used = set()

    def fire(i, b, dr, pool):
        if pool in used:
            return
        used.add(pool)
        if _confirmed(b, dr, confirm):
            sigs.append({"t": b["t"], "kind": "BREAKGO", "dir": dr})

    for i, b in enumerate(bars):
        f = b["fut"]
        R = Rs[i] or prior_R
        if R:
            m = margin * R
            if pdh and f["c"] > pdh + m:
                fire(i, b, 1, "pdh")
            if pdl and f["c"] < pdl - m:
                fire(i, b, -1, "pdl")
            if hi is not None and i - hi_i >= SESSION_AGE and f["c"] > hi + m:
                fire(i, b, 1, "sess_hi")
            if lo is not None and i - lo_i >= SESSION_AGE and f["c"] < lo - m:
                fire(i, b, -1, "sess_lo")
        if hi is None or f["h"] > hi:
            hi, hi_i = f["h"], i
        if lo is None or f["l"] < lo:
            lo, lo_i = f["l"], i
    return sigs


def _norm(bars):
    return [{"t": b["t"], "h": b["fut"]["h"], "l": b["fut"]["l"],
             "c": b["fut"]["c"]} for b in bars]


def _tally(recs, n_days):
    scored = [r for r in recs
              if r["outcome"] not in ("collapsed", "skipped_warmup")]
    w = sum(1 for r in scored if r["outcome"] == "win")
    l = sum(1 for r in scored if r["outcome"] == "loss")
    lo, hi = wilson(w, w + l)
    return {"n": len(scored), "per_wk": round(len(scored) / max(n_days, 1) * 5, 1),
            "win": w, "loss": l,
            "hit": round(w / (w + l), 2) if w + l else None,
            "ci": (round(lo, 2), round(hi, 2)),
            "exp_R": round(statistics.mean([r["exp_R"] for r in scored]), 3)
                     if scored else 0.0,
            "pts": round(statistics.mean([r["pts"] for r in scored]), 2)
                   if scored else 0.0}


def _replay_days():
    """Yield (day, session_json_bars, pdh, pdl, prior_R) across backtest days,
    chaining causal R day over day exactly as measure.run_backtest does."""
    import glob
    import os
    import backtest as bt
    from engine import Session, session_json
    days = sorted(os.path.basename(p)[4:14]
                  for p in glob.glob(str(ROOT / "data/backtest/fut_*.json")))
    opt = {os.path.basename(p)[4:14]
           for p in glob.glob(str(ROOT / "data/backtest/opt_*.json"))}
    days = [d for d in days if d in opt]
    prior_R = None
    for i in range(1, len(days)):
        day, prev = days[i], days[i - 1]
        try:
            fut, ce, pe, strike, _h, _n = bt.load_day(day, prev)
            s = Session(day, fut, ce, pe, quiet=True, strike=strike,
                        t_days=bt._t_days(day))
            s.run()
            js = session_json(s)
            pf = bt._fut_raw(prev)
            pdh, pdl = max(x["H"] for x in pf), min(x["L"] for x in pf)
        except Exception as ex:
            print(f"  {day}: ERROR {ex}")
            continue
        yield day, js["bars"], pdh, pdl, prior_R
        Rs = causal_R(_norm(js["bars"]))
        prior_R = next((r for r in reversed(Rs) if r), prior_R)


def walkforward(tune_n=35):
    data = list(_replay_days())
    tune, val = data[:tune_n], data[tune_n:]
    print(f"walk-forward: {len(tune)} tune days ({data[0][0]}..{tune[-1][0]}), "
          f"{len(val)} validation days ({val[0][0]}..{data[-1][0]})")

    def run(split, margin, confirm):
        recs = []
        for day, bars, pdh, pdl, prior_R in split:
            nb = _norm(bars)
            Rs = causal_R(nb)
            sigs = generate(bars, pdh, pdl, Rs, prior_R, margin, confirm)
            recs += score_day(nb, sigs, prior_R=prior_R)
        return _tally(recs, len(split))

    print(f"\nTUNE grid (min 10 scored):  exits {DEFAULTS['stop_R']}R/"
          f"{DEFAULTS['target_R']}R, cost {DEFAULTS['cost_pts']}pt, "
          f"breakeven hit 35%")
    best = None
    for margin in (0.10, 0.20, 0.30):
        for confirm in ("both", "either", "none"):
            t = run(tune, margin, confirm)
            mark = ""
            if t["n"] >= 10 and (best is None or t["exp_R"] > best[2]["exp_R"]):
                best, mark = (margin, confirm, t), " <-- best so far"
            print(f"  m={margin:.2f} conf={confirm:<7} n={t['n']:>3} "
                  f"({t['per_wk']}/wk) hit {t['hit']} ci {t['ci']} "
                  f"expR {t['exp_R']:+.3f} pts {t['pts']:+.2f}{mark}")
    if not best:
        print("no tune cell reached 10 signals — design infeasible as specified")
        return
    margin, confirm, t = best
    v = run(val, margin, confirm)
    ctrl = run(val, margin, "none")
    print(f"\nFROZEN: margin={margin} confirm={confirm} "
          f"(tune expR {t['exp_R']:+.3f}, n={t['n']})")
    print(f"VALIDATION: n={v['n']} ({v['per_wk']}/wk) hit {v['hit']} "
          f"ci {v['ci']} expR {v['exp_R']:+.3f} pts {v['pts']:+.2f}")
    print(f"CONTROL (none, same margin): n={ctrl['n']} hit {ctrl['hit']} "
          f"expR {ctrl['exp_R']:+.3f} pts {ctrl['pts']:+.2f}")
    verdict = "PASS" if v["exp_R"] > 0 else "FAIL"
    print(f"\nGATE: {verdict} — validation expectancy "
          f"{v['exp_R']:+.3f}R after costs"
          + (f"; confirmation lift vs control {v['exp_R']-ctrl['exp_R']:+.3f}R"
             if ctrl["n"] else ""))


def live(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    day = d["days"][0]
    bars = day["bars"]
    piv = day.get("pivots") or {}
    pdh = 2 * piv["P"] - piv["S1"] if piv else None    # standard-pivot algebra
    pdl = 2 * piv["P"] - piv["R1"] if piv else None
    nb = _norm(bars)
    Rs = causal_R(nb)
    for margin in (0.10, 0.20, 0.30):
        for confirm in ("both", "either", "none"):
            sigs = generate(bars, pdh, pdl, Rs, None, margin, confirm)
            print(f"m={margin} conf={confirm}: "
                  + (", ".join(f"{s['t']} {'UP' if s['dir']>0 else 'DN'}"
                               for s in sigs) or "-"))


if __name__ == "__main__":
    if "--walkforward" in sys.argv:
        walkforward()
    elif "--live" in sys.argv:
        live(sys.argv[sys.argv.index("--live") + 1])
    else:
        print(__doc__)
