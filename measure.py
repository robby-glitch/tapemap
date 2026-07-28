"""Canonical signal-measurement harness (spec: docs/superpowers/specs/
2026-07-28-measurement-harness-design.md).

Every signal evaluation — nightly live scoring, multi-day replays, acceptance
gates for new engines — goes through score_day(): intrabar first-touch fills,
per-kind cooldown de-clustering, cost-adjusted, asymmetric exits, causal R,
Wilson CIs. The naive audits this replaces scored close-only, cluster-inflated,
cost-free — and their conclusions moved with the ruler.

  python measure.py --backtest            # replay data/backtest days -> stats
  python measure.py --live payload.json [day-key]
"""
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
STATS_F = ROOT / "data" / "signal_stats.json"

DEFAULTS = dict(stop_R=0.7, target_R=1.3, window=45, cost_pts=1.5,
                warmup=45, eod="15:25")


def direction(kind, msg, data=None):
    """Canonical event-kind -> trade direction map (+1 long / -1 short / 0 n/a)."""
    m = (msg or "").upper()
    d = data or {}
    if kind == "BAND-REVERSAL":
        s = str(d.get("side") or "")
        if s:
            return -1 if ("UP" in s or "+2" in s) else 1
        return -1 if "+2" in (msg or "") else (1 if "-2" in (msg or "") else 0)
    if kind in ("TRAP-SPRUNG", "TRAP-SETTING"):
        s = d.get("side", "")
        if s:
            return -1 if s == "BULL" else 1 if s == "BEAR" else 0
        return -1 if "BULL TRAP" in m else (1 if "BEAR TRAP" in m else 0)
    if kind in ("PRESS", "CAMPAIGN", "BUYER-BUILD"):
        return 1 if "BULLISH" in m else (-1 if "BEARISH" in m else 0)
    if kind == "OI-PEAK-LAG":
        return 1 if "UPWARD" in m else (-1 if "DOWNWARD" in m else 0)
    if kind == "SQUEEZE-RISK":
        return 1 if "UPSIDE" in m else (-1 if "DOWNSIDE" in m else 0)
    if kind == "DIVERGENCE":
        return -1 if "HIGH" in m else (1 if "LOW" in m else 0)
    if kind == "IGNITION":
        return 1 if m.startswith("UP") or "UP:" in m else -1
    if kind in ("ARMED", "SPRING"):
        return 1 if d.get("side") == "UP" else -1 if d.get("side") == "DN" else 0
    return 0


def causal_R(bars, warmup=45):
    """R_i = median of trailing 15-bar rolling ranges over bars <= i, or None
    inside the warm-up. Strictly causal: no future bar can influence R_i."""
    out = []
    ranges = []
    for i in range(len(bars)):
        lo15 = min(b["l"] for b in bars[max(0, i - 14):i + 1])
        hi15 = max(b["h"] for b in bars[max(0, i - 14):i + 1])
        ranges.append(hi15 - lo15)
        if i >= warmup:
            med = statistics.median(ranges[14:i + 1] or [0])
            out.append(med or None)
        else:
            out.append(None)
    return out


def wilson(w, n, z=1.96):
    """95% Wilson interval for a binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    p = w / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, mid - half), min(1.0, mid + half))


def norm_bars_payload(day):
    """/api/data day -> normalized bars [{t,h,l,c}]."""
    return [{"t": b["t"], "h": b["fut"]["h"], "l": b["fut"]["l"],
             "c": b["fut"]["c"]} for b in day["bars"]]


def norm_bars_fut(fut):
    """backtest.load_day fut bars -> normalized bars."""
    return [{"t": b["T"], "h": b["H"], "l": b["L"], "c": b["C"]} for b in fut]


def score_day(bars, signals, *, stop_R=None, target_R=None, window=None,
              cost_pts=None, warmup=None, prior_R=None, portfolio=False,
              eod=None):
    """Score [{t, kind, dir}] against normalized bars.

    Returns TradeRecords {kind, t, dir, outcome, pts, R, exp_R}; the outcomes
    'collapsed' and 'skipped_warmup' are bookkeeping rows (pts 0, not traded)."""
    p = {**DEFAULTS}
    for k, v in dict(stop_R=stop_R, target_R=target_R, window=window,
                     cost_pts=cost_pts, warmup=warmup, eod=eod).items():
        if v is not None:
            p[k] = v
    t2i = {b["t"]: i for i, b in enumerate(bars)}
    Rs = causal_R(bars, p["warmup"])
    sigs = sorted((s for s in signals if s.get("dir") and s["t"] in t2i),
                  key=lambda s: t2i[s["t"]])
    open_tr = {}                      # key (kind, or 'PORT') -> trade dict
    records = []

    def close(tr, px, outcome):
        pts = tr["dir"] * (px - tr["entry"]) - p["cost_pts"]
        records.append({"kind": tr["kind"], "t": tr["t"], "dir": tr["dir"],
                        "outcome": outcome, "pts": round(pts, 2),
                        "R": round(tr["R"], 2),
                        "exp_R": round(pts / tr["R"], 3)})

    si = 0
    for i, b in enumerate(bars):
        # 1) resolve open trades on this bar (entry bar itself excluded)
        for key in list(open_tr):
            tr = open_tr[key]
            if i <= tr["i"]:
                continue
            hit_t = (b["h"] >= tr["target"]) if tr["dir"] > 0 else \
                    (b["l"] <= tr["target"])
            hit_s = (b["l"] <= tr["stop"]) if tr["dir"] > 0 else \
                    (b["h"] >= tr["stop"])
            if hit_s:                                  # both-in-bar -> loss
                close(tr, tr["stop"], "loss")
            elif hit_t:
                close(tr, tr["target"], "win")
            elif i - tr["i"] >= p["window"]:
                close(tr, b["c"], "timeout")
            elif b["t"] >= p["eod"]:
                close(tr, b["c"], "eod")
            else:
                continue
            del open_tr[key]
        # 2) admit signals on this bar
        while si < len(sigs) and t2i[sigs[si]["t"]] == i:
            s = sigs[si]
            si += 1
            if b["t"] >= p["eod"]:
                continue                               # no fresh entries at EOD
            R = Rs[i] if Rs[i] else prior_R
            if not R:
                records.append({"kind": s["kind"], "t": s["t"], "dir": s["dir"],
                                "outcome": "skipped_warmup", "pts": 0.0,
                                "R": 0.0, "exp_R": 0.0})
                continue
            key = "PORT" if portfolio else s["kind"]
            cur = open_tr.get(key)
            if cur:
                if cur["dir"] == s["dir"]:
                    records.append({"kind": s["kind"], "t": s["t"],
                                    "dir": s["dir"], "outcome": "collapsed",
                                    "pts": 0.0, "R": 0.0, "exp_R": 0.0})
                    continue
                close(open_tr.pop(key), b["c"], "reversal")
            entry = b["c"]
            open_tr[key] = {"kind": s["kind"], "t": s["t"], "dir": s["dir"],
                            "i": i, "entry": entry, "R": R,
                            "stop": entry - s["dir"] * p["stop_R"] * R,
                            "target": entry + s["dir"] * p["target_R"] * R}
    for key in list(open_tr):                          # ran off end of data
        close(open_tr.pop(key), bars[-1]["c"], "eod")
    return records


def report(records, label="", breakeven=None):
    """Per-kind stats with Wilson CIs. Returns dict; prints a table.

    `breakeven` is the hit rate that zeroes expectancy BEFORE costs for the
    exit geometry: stop_R/(stop_R+target_R) — 0.35 for the 0.7/1.3 defaults.
    A kind is only +/- when its CI clears that line; otherwise '?'."""
    if breakeven is None:
        breakeven = DEFAULTS["stop_R"] / (DEFAULTS["stop_R"]
                                          + DEFAULTS["target_R"])
    by = defaultdict(list)
    for r in records:
        by[r["kind"]].append(r)
    out = {}
    print(f"\n{label}  ({len(records)} records)")
    print(f"{'KIND':<15}{'n':>4}{'coll':>5}{'win':>4}{'loss':>5}{'oth':>4}"
          f"{'hit%':>6}{'CI95':>12}{'expR':>7}{'pts':>7}  flag")
    for kind, rs in sorted(by.items(), key=lambda x: -len(x[1])):
        scored = [r for r in rs
                  if r["outcome"] not in ("collapsed", "skipped_warmup")]
        coll = sum(1 for r in rs if r["outcome"] == "collapsed")
        w = sum(1 for r in scored if r["outcome"] == "win")
        l = sum(1 for r in scored if r["outcome"] == "loss")
        oth = len(scored) - w - l
        lo, hi = wilson(w, w + l)
        exp_R = statistics.mean([r["exp_R"] for r in scored]) if scored else 0.0
        pts = statistics.mean([r["pts"] for r in scored]) if scored else 0.0
        flag = ("?" if (lo <= breakeven <= hi or w + l < 30)
                else ("+" if exp_R > 0 else "-"))
        out[kind] = {"n": len(scored), "collapsed": coll, "win": w, "loss": l,
                     "other": oth,
                     "hit": round(w / (w + l), 3) if w + l else None,
                     "ci": [round(lo, 3), round(hi, 3)],
                     "exp_R": round(exp_R, 3), "exp_pts": round(pts, 2),
                     "flag": flag}
        hits = f"{w/(w+l)*100:.0f}" if w + l else "n/a"
        print(f"{kind:<15}{len(scored):>4}{coll:>5}{w:>4}{l:>5}{oth:>4}"
              f"{hits:>6}{f'{lo*100:.0f}-{hi*100:.0f}':>12}{exp_R:>7.2f}"
              f"{pts:>7.2f}  {flag}")
    return out


def _signals_from_events(events):
    return [{"t": e["t"], "kind": e["kind"],
             "dir": direction(e["kind"], e.get("msg"), e.get("data"))}
            for e in events]


def _save_stats(day_key, day_stats, params):
    stats = {"params": params, "days": {}, "rolling": {}}
    if STATS_F.exists():
        try:
            stats = json.loads(STATS_F.read_text(encoding="utf-8"))
        except ValueError:
            pass
    stats["params"] = params
    stats.setdefault("days", {})[day_key] = day_stats
    roll = defaultdict(lambda: {"win": 0, "loss": 0, "n": 0})
    for d in stats["days"].values():
        for kind, s in d.items():
            roll[kind]["win"] += s["win"]
            roll[kind]["loss"] += s["loss"]
            roll[kind]["n"] += s["n"]
    for kind, s in roll.items():
        dec = s["win"] + s["loss"]
        lo, hi = wilson(s["win"], dec)
        s["hit"] = round(s["win"] / dec, 3) if dec else None
        s["ci"] = [round(lo, 3), round(hi, 3)]
    stats["rolling"] = dict(roll)
    STATS_F.write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(f"stats -> {STATS_F}")


def run_backtest():
    import glob
    import os
    import backtest as bt
    from engine import Session, session_json
    days = sorted(os.path.basename(p)[4:14]
                  for p in glob.glob(str(ROOT / "data/backtest/fut_*.json")))
    opt = {os.path.basename(p)[4:14]
           for p in glob.glob(str(ROOT / "data/backtest/opt_*.json"))}
    days = [d for d in days if d in opt]
    allrecs = []
    prior_R = None
    for i in range(1, len(days)):
        day, prev = days[i], days[i - 1]
        try:
            fut, ce, pe, strike, _hops, _n = bt.load_day(day, prev)
            s = Session(day, fut, ce, pe, quiet=True, strike=strike,
                        t_days=bt._t_days(day))
            s.run()
            js = session_json(s)
        except Exception as ex:
            print(f"  {day}: ERROR {ex}")
            continue
        bars = norm_bars_fut(fut)
        recs = score_day(bars, _signals_from_events(js["events"]),
                         prior_R=prior_R)
        Rs = causal_R(bars)
        prior_R = next((r for r in reversed(Rs) if r), prior_R)
        for r in recs:
            r["day"] = day
        allrecs += recs
    stats = report(allrecs, f"BACKTEST {len(days) - 1} days, stop "
                            f"{DEFAULTS['stop_R']}R / target "
                            f"{DEFAULTS['target_R']}R, cost "
                            f"{DEFAULTS['cost_pts']}pt, de-clustered, intrabar")
    _save_stats("backtest_baseline", stats, DEFAULTS)


def run_live(path, day_key=None):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    day = d["days"][0]
    bars = norm_bars_payload(day)
    recs = score_day(bars, _signals_from_events(day["events"]))
    stats = report(recs, f"LIVE {day.get('day', path)}")
    if day_key:
        _save_stats(day_key, stats, DEFAULTS)


if __name__ == "__main__":
    if "--backtest" in sys.argv:
        run_backtest()
    elif "--live" in sys.argv:
        i = sys.argv.index("--live")
        run_live(sys.argv[i + 1],
                 sys.argv[i + 2] if len(sys.argv) > i + 2 else None)
    else:
        print(__doc__)
