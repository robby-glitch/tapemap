"""Score one hypothesis: does a VWAP-band squeeze breakout behave differently
when open interest is RISING into the move versus FALLING?

THE HYPOTHESIS, in the operator's terms
    A squeeze that breaks with OI expanding is position being ADDED -- the move
    has legs. A squeeze that breaks with OI flat or falling is covering: the
    buying is forced and finite, so the extreme comes early and the move fades.

WHAT A FIRST PASS FOUND (55 NIFTY sessions, 2026-07-31)
    OI rising  n=21  to close +43.1 (median +17.9)
    OI falling n= 5  to close -117.5
    control (same momentum rule at EVERY bar)      n=5093  +2.1
    control (OI split at every bar, no squeeze)    spread only +11.5 pts
    So OI direction ALONE is worthless (hit 52% vs 50%); the interaction with
    the squeeze is what separates. Robust in sign across all 12 grid cells --
    but n=5, one -415.9 outlier carried much of the mean, and only 3 of 5
    closed negative. That is why this file exists: to re-run it on more data
    without re-deriving the method, and to make the weakness visible rather
    than quotable.

READING RULES BUILT INTO THE OUTPUT
    - Median is printed beside every mean. Both arms were outlier-skewed.
    - Per-index is printed BEFORE pooled. NIFTY, BANKNIFTY and SENSEX trade the
      same market on the same days, so their squeezes co-occur; pooling
      inflates n without adding proportional information. An effect that only
      survives pooling is a warning, not a result.
    - The 12-cell sensitivity grid is always printed. A finding that holds at
      one threshold and nowhere else is a mined threshold.
    - Monthly-expiry sessions are reported separately. 2026-07-30 carried a
      -338k overnight OI step on NIFTY that is settlement mechanics, not
      positioning, and it contaminates exactly this measure.
    - Contract composition is printed per index, because data/backtest mixes a
      live front-month capture (to 2026-07-17) with a backfilled AUGUST
      contract (from 2026-07-20). See backfill.py's header.

  python squeeze_score.py
"""

import glob
import json
import os
import statistics as st
from datetime import date, timedelta

import contract_bars as cb
import instruments as I

BT = "data/backtest"
W = 30            # trailing window, in bars, that "narrow" is judged against
ANCHOR = 5        # no verdict before ~09:27 -- too little session to rank
SUPPRESS = 10     # bars before the same squeeze may fire again
MINTAIL = 20      # bars that must remain, or the outcome measures are noise
INTERVAL = 3      # minutes per bar; the operator reads 3-min charts


def _paths(idx):
    """NIFTY sits flat in data/backtest/; other indices in a subdirectory.
    See backfill.py's LAYOUT note for why the basename must stay `fut_<ISO>`."""
    if idx == "NIFTY":
        return sorted(glob.glob(f"{BT}/fut_*.json"))
    return sorted(glob.glob(f"{BT}/{idx}/fut_*.json"))


def _is_expiry(day, meta):
    """Prefer the stamp the backfill wrote; fall back to computing it, because
    the pre-existing live capture has no _meta at all."""
    if meta and "is_monthly_expiry" in meta:
        return bool(meta["is_monthly_expiry"])
    d = date.fromisoformat(day)
    return d.weekday() == 3 and (d + timedelta(days=7)).month != d.month


def load(idx):
    """-> {day: {"bars": banded 3-min bars, "expiry": bool, "fut_id": str|None}}

    Band order matters: vwap_bands THEN resample. Validated against the
    operator's own Kite export (data/FUT_3day.csv, Jul 15-17): this order
    reproduces their u3-d3 at a median ratio of 0.972, the reverse order 0.948
    with a much worse tail."""
    out = {}
    for p in _paths(idx):
        day = os.path.basename(p)[4:14]
        try:
            payload = json.load(open(p))
            bars = cb.resample(cb.vwap_bands(cb.to_bars(payload)), INTERVAL)
        except Exception:
            continue
        if len(bars) < 60:
            continue
        meta = payload.get("_meta") or {}
        out[day] = {"bars": bars, "expiry": _is_expiry(day, meta),
                    "fut_id": meta.get("fut_id")}
    return out


def breakouts(bars, sq_rank, expand):
    """Bars where a squeeze just broke.

    squeeze  -- (u3-d3) ranks in the bottom `sq_rank` of the trailing W
                readings. Absolute points, never divided by VWAP: on option
                premium that denominator decays through the day and manufactures
                a trend that is not there. A rank is scale-free anyway.
    breakout -- width >= `expand` x the trailing minimum AND still rising, with
                a squeeze true within the last 5 bars.
    """
    n = len(bars)
    w = [(b["u3"] - b["d3"]) if b.get("u3") is not None else None for b in bars]
    out, last = [], -99
    for i in range(ANCHOR, n):
        if w[i] is None:
            continue
        tw = [x for x in w[max(0, i - W):i] if x is not None]
        if len(tw) < 10:
            continue
        was_squeezed = False
        for j in range(max(ANCHOR, i - 5), i):
            if w[j] is None:
                continue
            tj = [x for x in w[max(0, j - W):j] if x is not None]
            if len(tj) >= 10 and sum(1 for x in tj if x < w[j]) / len(tj) <= sq_rank:
                was_squeezed = True
                break
        if was_squeezed and w[i] >= expand * min(tw) and w[i] > w[i - 1] \
                and i - last >= SUPPRESS:
            out.append(i)
            last = i
    return out


def outcome(bars, i, d):
    """Forward measures from bar `i`, signed by direction `d`."""
    n = len(bars)
    c = [x["c"] for x in bars]

    def fwd(k):
        return (c[i + k] - c[i]) * d if i + k < n else None

    tail = range(i, n)
    ex = max(tail, key=lambda j: (c[j] - c[i]) * d)
    mfe = (c[ex] - c[i]) * d
    mae = min((c[j] - c[i]) * d for j in tail)
    to_close = (c[n - 1] - c[i]) * d
    return {"f15": fwd(5), "f30": fwd(10), "f60": fwd(20), "tc": to_close,
            "mfe": mfe, "mae": mae,
            # How early the move topped, as a fraction of the session left.
            # Small = the extreme came right after the break, which is the
            # covering signature.
            "frac": (ex - i) / (n - 1 - i) if n - 1 - i > 0 else None,
            "gb": (mfe - to_close) / mfe if mfe > 1e-9 else None}


def collect(sessions, sq_rank, expand, oi_win, skip_expiry=False):
    up, dn, ctrl = [], [], []
    for day, s in sessions.items():
        if skip_expiry and s["expiry"]:
            continue
        bars = s["bars"]
        n = len(bars)
        c = [x["c"] for x in bars]
        oi = [x.get("oi") for x in bars]
        for i in breakouts(bars, sq_rank, expand):
            if i < oi_win + 1 or n - 1 - i < MINTAIL:
                continue
            d = 1 if c[i] > c[i - 3] else (-1 if c[i] < c[i - 3] else 0)
            if not d or oi[i] is None or oi[i - oi_win] is None or not oi[i - oi_win]:
                continue
            r = outcome(bars, i, d)
            r.update(day=day, t=bars[i]["t"],
                     dOI=(oi[i] - oi[i - oi_win]) / oi[i - oi_win])
            (up if r["dOI"] > 0 else dn).append(r)
        for i in range(ANCHOR + 6, n - MINTAIL):
            d = 1 if c[i] > c[i - 3] else (-1 if c[i] < c[i - 3] else 0)
            if d:
                ctrl.append(outcome(bars, i, d))
    return up, dn, ctrl


def _fmt(name, rows):
    if not rows:
        print(f"  {name:<10} n=0")
        return

    def col(k):
        return [r[k] for r in rows if r.get(k) is not None]

    def mm(k):
        v = col(k)
        return f"{st.mean(v):+7.1f}/{st.median(v):+7.1f}" if v else "       -"

    def hit(k):
        v = col(k)
        return f"{100 * sum(1 for x in v if x > 0) / len(v):3.0f}%" if v else "  - "

    fr, gb = col("frac"), col("gb")
    tail = (f"t-ext {st.median(fr):.2f} | gb {100 * st.median(gb):4.0f}%"
            if fr and gb else "t-ext - | gb -")
    print(f"  {name:<10} n={len(rows):<4} "
          f"+30m {mm('f30')} {hit('f30')} | "
          f"close {mm('tc')} {hit('tc')} | "
          f"MFE {st.mean(col('mfe')):5.1f} MAE {st.mean(col('mae')):6.1f} | "
          f"{tail}")


def report(label, sessions, sq=0.30, expand=1.20, oi_win=5, skip_expiry=False):
    up, dn, ctrl = collect(sessions, sq, expand, oi_win, skip_expiry)
    print(f"\n--- {label}  ({len(sessions)} sessions) "
          f"mean/median shown for every figure ---")
    _fmt("OI UP", up)
    _fmt("OI DOWN", dn)
    _fmt("control", ctrl)
    if up and dn:
        sp = st.mean([r["tc"] for r in up]) - st.mean([r["tc"] for r in dn])
        print(f"  spread (UP - DOWN, to close): {sp:+.1f} pts")
    return up, dn, ctrl


def main():
    all_sessions = {}
    print("=== what is on disk ===")
    for idx in I.ENABLED:
        s = load(idx)
        all_sessions[idx] = s
        if not s:
            print(f"  {idx:<10} no sessions")
            continue
        days = sorted(s)
        ids = sorted({v["fut_id"] or "live-capture (no _meta)" for v in s.values()})
        nexp = sum(1 for v in s.values() if v["expiry"])
        print(f"  {idx:<10} {len(s):3d} sessions  {days[0]} -> {days[-1]}  "
              f"expiry days {nexp}")
        print(f"  {'':<10} contracts: {', '.join(str(i) for i in ids)}")

    print("\n\n=== PER INDEX (read these first) ===")
    for idx in I.ENABLED:
        if all_sessions[idx]:
            report(idx, all_sessions[idx])

    pooled = {}
    for idx in I.ENABLED:
        for day, s in all_sessions[idx].items():
            pooled[f"{idx} {day}"] = s
    if not pooled:
        return

    print("\n\n=== POOLED (inflated n -- the indices co-move; see header) ===")
    report("pooled", pooled)
    print("\n=== POOLED, monthly-expiry sessions EXCLUDED ===")
    report("no-expiry", pooled, skip_expiry=True)

    print("\n\n=== SENSITIVITY GRID (pooled) ===")
    print(f"  {'params':<26}{'nUP':>5}{'nDN':>6} | {'UP close':>10} "
          f"{'DN close':>10} | {'spread':>8}")
    for sq in (0.30, 0.40, 0.50):
        for ex in (1.20, 1.12):
            for ow in (5, 10):
                u, d, _ = collect(pooled, sq, ex, ow)
                mu = st.mean([r["tc"] for r in u]) if u else float("nan")
                md = st.mean([r["tc"] for r in d]) if d else float("nan")
                print(f"  rank<={sq:.2f} exp>={ex:.2f} oi{ow:<2}"
                      f"{len(u):>10}{len(d):>6} | {mu:+10.1f} {md:+10.1f} "
                      f"| {mu - md:+8.1f}")

    print("\n=== CONTROL: OI split at EVERY bar (no squeeze condition) ===")
    au, ad = [], []
    for s in pooled.values():
        bars, n = s["bars"], len(s["bars"])
        c = [x["c"] for x in bars]
        oi = [x.get("oi") for x in bars]
        for i in range(ANCHOR + 6, n - MINTAIL):
            dd = 1 if c[i] > c[i - 3] else (-1 if c[i] < c[i - 3] else 0)
            if not dd or oi[i] is None or oi[i - 5] is None:
                continue
            (au if oi[i] - oi[i - 5] > 0 else ad).append(outcome(bars, i, dd))
    _fmt("OI UP", au)
    _fmt("OI DOWN", ad)
    if au and ad:
        base = st.mean([r["tc"] for r in au]) - st.mean([r["tc"] for r in ad])
        print(f"  spread everywhere: {base:+.1f} pts  <- the number the "
              f"squeeze spread must beat to mean anything")


if __name__ == "__main__":
    main()
