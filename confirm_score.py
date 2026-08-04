"""Score the TWO-LEG band-rotation confirm on cached option premium days.

THE TRIAL THAT WAS BLOCKED ALL DAY. rotation_score.py could only score the
INDEX expression (`detect_index`), where `confirm` is UNKNOWN by construction.
data/backtest/opt_<ISO>.json (73 NIFTY days, Apr-Jul 17, per-bar CE/PE
o/h/l/c/v/oi at a fixed near-ATM strike, monthly leg) is exactly the pair
history `band_rotation.detect` was written for. The operator's actual claim
is ON TRIAL HERE: premium at its own band extreme, reversing, WITH the other
leg rotating off its opposite extreme and OI confirming -- does CONFIRMED
separate winners from losers?

METHOD (house rules; deviations stated):
  * Legs built per day: 1-min CE/PE bars -> vwap_bands -> resample(3) --
    the premium's OWN session VWAP bands, the validated order.
  * CE and PE aligned on a shared axis of 3-min clock labels (union); a
    minute one leg did not print is None for that leg, never interpolated.
  * index_series = the SAME day's banded FUT bars (squeeze_score.load) so
    the compression/trap read is the index's, per the spec.
  * Scored on the PREMIUM of the triggered leg: entry at trigger-bar close,
    forward +15m/+30m signed by side, MFE/MAE over 30m. Points of premium.
  * CONTROL: unconditional +30m drift over every post-09:25 bar of the same
    legs -- for premium this is NEGATIVE (theta); a buy signal must beat a
    falling tape, which futures scoring never had to.
  * First-of-run per (leg, side), post-09:25 primary; medians beside means;
    monthly legs only -- weekly behaviour is NOT tested here.

    python confirm_score.py
"""

import glob
import json
import os
import statistics as st

import band_rotation as br
import contract_bars as cb
from squeeze_score import INTERVAL, load as load_fut

BAND_KEYS = ("vwap", "u1", "d1", "u2", "d2", "u3", "d3")
HORIZON_BARS = {"+15m": 5, "+30m": 10}
MFE_BARS = 30 // INTERVAL
ANCHOR_MIN = br.ANCHOR_MINUTE


def _minute(t):
    try:
        hh, mm = t.split(":")
        return int(hh) * 60 + int(mm)
    except (AttributeError, ValueError):
        return None


def _leg_on_axis(bars3, axis):
    """One resampled banded leg -> {bars, vwap} aligned to the shared axis."""
    by_t = {b["t"]: b for b in bars3 if b}
    bars, vwap = [], []
    for t in axis:
        b = by_t.get(t)
        if b is None:
            bars.append(None)
            vwap.append(None)
        else:
            bars.append({k: b.get(k) for k in ("t", "o", "h", "l", "c", "v", "oi")})
            vwap.append({k: b.get(k) for k in BAND_KEYS})
    return {"bars": bars, "vwap": vwap, "oi": [], "bar_days": []}


def collect():
    fut_days = load_fut("NIFTY")
    rows = []
    controls = {k: [] for k in HORIZON_BARS}
    n_days = 0
    for p in sorted(glob.glob("data/backtest/opt_*.json")):
        day = os.path.basename(p)[4:14]
        try:
            d = json.load(open(p))
            legs3 = {}
            for name in ("ce", "pe"):
                legs3[name.upper()] = cb.resample(cb.vwap_bands(d[name]), INTERVAL)
        except Exception:
            continue
        if not legs3.get("CE") or not legs3.get("PE"):
            continue
        axis = sorted({b["t"] for leg in legs3.values() for b in leg if b},
                      key=_minute)
        legs = {n: _leg_on_axis(b3, axis) for n, b3 in legs3.items()}
        fut = fut_days.get(day)
        recs = br.detect(legs, index_series=fut["bars"] if fut else None)
        n_days += 1
        px = {n: [b["c"] if b else None for b in legs[n]["bars"]] for n in legs}
        hi = {n: [b["h"] if b else None for b in legs[n]["bars"]] for n in legs}
        lo = {n: [b["l"] if b else None for b in legs[n]["bars"]] for n in legs}
        prev = {}
        for i, r in enumerate(recs):
            if r is None:
                continue
            leg, side = r["leg"], r["side"]
            dsign = 1 if side == "BUY" else -1
            c = px[leg]
            if c[i] is None:
                continue
            key = (leg, side)
            first = prev.get(key) != i - 1
            prev[key] = i
            t = axis[i]
            row = {"day": day, "t": t, "leg": leg, "side": side,
                   "band": r["band"], "confirm": r["confirm"], "trap": r["trap"],
                   "px": c[i], "first": first,
                   "anchored": (_minute(t) or 0) >= ANCHOR_MIN}
            for name, h in HORIZON_BARS.items():
                j = i + h
                row[name] = (None if j >= len(c) or c[j] is None
                             else dsign * (c[j] - c[i]))
            hs = [v for v in hi[leg][i + 1:i + 1 + MFE_BARS] if v is not None]
            ls = [v for v in lo[leg][i + 1:i + 1 + MFE_BARS] if v is not None]
            if hs and ls:
                row["mfe"] = dsign * ((max(hs) if dsign > 0 else min(ls)) - c[i])
                row["mae"] = dsign * ((min(ls) if dsign > 0 else max(hs)) - c[i])
            else:
                row["mfe"] = row["mae"] = None
            rows.append(row)
        for n in legs:
            c = px[n]
            for i, t in enumerate(axis):
                if (_minute(t) or 0) < ANCHOR_MIN or c[i] is None:
                    continue
                for name, h in HORIZON_BARS.items():
                    j = i + h
                    if j < len(c) and c[j] is not None:
                        controls[name].append(c[j] - c[i])
    return rows, controls, n_days


def _stat(rows, key):
    v = [r[key] for r in rows if r[key] is not None]
    if not v:
        return None
    return {"n": len(v), "mean": st.mean(v), "med": st.median(v),
            "hit": sum(1 for x in v if x > 0) / len(v)}


def _line(label, rows):
    s15, s30 = _stat(rows, "+15m"), _stat(rows, "+30m")
    if not s30:
        if rows:
            print(f"  {label:<30} n={len(rows)} (no full horizon)")
        return
    mfe, mae = _stat(rows, "mfe"), _stat(rows, "mae")
    m1 = f"{mfe['mean']:+6.1f}" if mfe else "   n/a"
    m2 = f"{mae['mean']:+6.1f}" if mae else "   n/a"
    print(f"  {label:<30}"
          f"{s15['mean']:+7.1f} {s15['med']:+6.1f} {s15['hit'] * 100:4.0f}%   "
          f"{s30['mean']:+7.1f} {s30['med']:+6.1f} {s30['hit'] * 100:4.0f}% "
          f"n={s30['n']:<4} {m1} {m2}")


def main():
    rows, controls, n_days = collect()
    primary = [r for r in rows if r["anchored"] and r["first"]]
    print(f"NIFTY monthly-leg premium pairs -- {n_days} days, "
          f"{len(rows)} raw fires, {len(primary)} first-of-run post-09:25")
    print(f"  {'segment':<30}{'+15m avg':>7} {'med':>6} {'hit':>5}   "
          f"{'+30m avg':>7} {'med':>6} {'hit':>5} {'n':<6}{'MFE':>6} {'MAE':>6}")
    print("  " + "-" * 100)
    _line("ALL PRIMARY", primary)
    print()
    for conf in ("CONFIRMED", "UNCONFIRMED", "UNKNOWN"):
        _line(f"confirm={conf}", [r for r in primary if r["confirm"] == conf])
    print()
    buys = [r for r in primary if r["side"] == "BUY"]
    _line("BUY (all)", buys)
    for conf in ("CONFIRMED", "UNCONFIRMED"):
        _line(f"  BUY {conf}", [r for r in buys if r["confirm"] == conf])
    for band in ("d3", "d2"):
        _line(f"  BUY {band}", [r for r in buys if r["band"] == band])
    _line(f"  BUY d3+CONFIRMED",
          [r for r in buys if r["band"] == "d3" and r["confirm"] == "CONFIRMED"])
    sells = [r for r in primary if r["side"] == "SELL"]
    _line("SELL u3 (all)", sells)
    for conf in ("CONFIRMED", "UNCONFIRMED"):
        _line(f"  SELL {conf}", [r for r in sells if r["confirm"] == conf])
    print()
    for trap in ("CLEAR", "SUSPECT", "UNKNOWN"):
        _line(f"trap={trap}", [r for r in primary if r["trap"] == trap])
    c15, c30 = controls["+15m"], controls["+30m"]
    print(f"\n  CONTROL every post-09:25 premium bar (theta included): "
          f"+15m {st.mean(c15):+.1f} (med {st.median(c15):+.1f}), "
          f"+30m {st.mean(c30):+.1f} (med {st.median(c30):+.1f}), "
          f"{sum(1 for x in c30 if x > 0) / len(c30):.0%} up, n={len(c30)}")
    print("\nPremium points, monthly legs, fixed near-ATM strike, no costs, "
          "no stop. The confirm's job is separation:\nCONFIRMED must beat "
          "UNCONFIRMED, or the pair logic adds nothing. First measurement, "
          "not a verdict.")


if __name__ == "__main__":
    main()
