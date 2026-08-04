"""Head-to-head: the operator's REAL two-candle d3 rule vs the one-candle rule.

WHY THIS EXISTS. `research-findings.md` §1's numbers (72% hit, +21.0 median,
-20.7 adverse swing) were measured on `band_rotation._trigger` -- ONE bar
pierces d3 and closes back above it. Asked directly on 2026-08-05, the operator
described something else: a bar TOUCHES d3, and entry comes when a LATER bar
closes above THAT bar's high. §1 is therefore VOID, not disproven, and this
file is what replaces it.

The rule under test is pre-registered in §5c, written before this ran. Its
predictions, so they can be checked rather than remembered:

  1. the new rule fires LESS often than the old one on the same sessions
  2. its mean MAE is SMALLER in magnitude than -20.7 (entry is later, higher)
  3. therefore the 20-pt stop is no longer sized to the swing, and is loose
  4. hit rate at +30m is materially above the ~50% / +0.3pt control

  FALSIFIER: +30m hit rate at or below ~55%, or a median at or below the
  control, or the result collapsing once the single best trade is dropped.

METHOD -- deliberately the same as rotation_score.py so the two are comparable:
  * 3-minute bars via squeeze_score.load (vwap_bands THEN resample: 0.972 vs
    Kite, reversed 0.948).
  * Entry is the CLOSE of the triggering bar, for both rules.
  * Forward move signed by side; horizons past the last bar are dropped, never
    zero-filled.
  * CONTROL: the same horizons over every post-09:25 bar, no signal involved.
  * Median beside every mean, and the whole table re-run with the single best
    trade removed (§5 lesson 2 -- one ADANIGREEN winner once carried an entire
    positive mean).

The 20-point stop lives HERE and not in band_rotation: the detector detects,
the scorer prices. Per HANDOFF §8 the width itself is a risk decision the
operator owns and is deliberately NOT grid-searched.

    python run_score.py
"""

import statistics as st

import band_rotation as br
from squeeze_score import INTERVAL, load

INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
HORIZON_BARS = {"+6m": 2, "+15m": 5, "+30m": 10}
MFE_BARS = 30 // INTERVAL
ANCHOR_MIN = br.ANCHOR_MINUTE
STOP_PTS = 20.0                 # the operator's own stop, not searched


def _minute(t):
    try:
        hh, mm = t.split(":")
        return int(hh) * 60 + int(mm)
    except (AttributeError, ValueError):
        return None


def _stop_exit(bars, i, stop, horizon):
    """(points, stopped) for a long held `horizon` bars with a hard stop.

    The stop is checked on every bar's LOW before the horizon close, so a trade
    that would have recovered still records the loss it actually took."""
    last = min(i + horizon, len(bars) - 1)
    entry = bars[i]["c"]
    for j in range(i + 1, last + 1):
        if bars[j]["l"] <= stop:
            return stop - entry, True
    return bars[last]["c"] - entry, False


def _old(bars, d3_only):
    """The one-candle rule, filtered as rotation_score reports it: post-09:25
    and first-of-run.

    `d3_only` matters more than it looks. §1's headline (72%, +21.0) was the
    **d3 BUY** population, n=18 -- d2 was separately found to be noise (180
    NIFTY signals, a coin flip) and selling was rejected on five datasets. So
    the everything-pooled column answers "what do the pills on the chart
    actually mark", and the d3-BUY column is the only fair comparator for the
    new rule. Both are printed; conflating them was a real error in the first
    draft of this file."""
    recs = br.detect_index(bars)
    out, prev_i, prev_side = [], None, None
    for i, r in enumerate(recs):
        if r is None:
            continue
        first = not (prev_i == i - 1 and prev_side == r["side"])
        prev_i, prev_side = i, r["side"]
        if not first or (_minute(r["t"]) or 0) < ANCHOR_MIN:
            continue
        if d3_only and not (r["band"] == "d3" and r["side"] == "BUY"):
            continue
        out.append({"i": i, "side": r["side"], "level": None})
    return out


def _rows_old_all(bars):
    return _old(bars, d3_only=False)


def _rows_old_d3(bars):
    return _old(bars, d3_only=True)


def _rows_new(bars):
    """The operator's rule. Arming, the reference walk, the window and the
    re-fire lock are all inside the detector, so nothing is filtered here --
    what it emits IS the trade list."""
    recs = br.detect_index_run(bars, stop_pts=STOP_PTS)
    return [{"i": r["i"], "side": r["side"], "level": r["level"]}
            for r in recs if r is not None]


def collect(idx, rows_of):
    days = load(idx)
    trades, controls, sessions = [], {k: [] for k in HORIZON_BARS}, 0
    for day, D in sorted(days.items()):
        bars = D["bars"]
        if not bars:
            continue
        sessions += 1
        close = [b["c"] for b in bars]
        high = [b["h"] for b in bars]
        low = [b["l"] for b in bars]
        for sig in rows_of(bars):
            i = sig["i"]
            d = 1 if sig["side"] == "BUY" else -1
            row = {"day": day, "i": i, "side": sig["side"], "px": close[i],
                   "expiry": D["expiry"]}
            for name, h in HORIZON_BARS.items():
                j = i + h
                row[name] = None if j >= len(close) else d * (close[j] - close[i])
            w = slice(i + 1, min(i + 1 + MFE_BARS, len(close)))
            hs, ls = high[w], low[w]
            if hs:
                row["mfe"] = d * ((max(hs) if d > 0 else min(ls)) - close[i])
                row["mae"] = d * ((min(ls) if d > 0 else max(hs)) - close[i])
            else:
                row["mfe"] = row["mae"] = None
            # The stop only makes sense on the long side, and it is anchored to
            # the band the setup fired at. The old rule's records do not carry
            # that level, so it is priced off the bar's own d3 instead.
            lvl = sig["level"]
            if lvl is None:
                lvl = bars[i].get("d3")
            if d > 0 and isinstance(lvl, (int, float)):
                pts, stopped = _stop_exit(bars, i, lvl - STOP_PTS,
                                          HORIZON_BARS["+30m"])
                row["stop_pts"], row["stopped"] = pts, stopped
            else:
                row["stop_pts"], row["stopped"] = None, None
            trades.append(row)
        for i, b in enumerate(bars):
            if (_minute(b["t"]) or 0) < ANCHOR_MIN:
                continue
            for name, h in HORIZON_BARS.items():
                j = i + h
                if j < len(close):
                    controls[name].append(close[j] - close[i])
    return trades, controls, sessions


def _stat(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    hit = sum(1 for v in vals if v > 0) / len(vals)
    return {"n": len(vals), "hit": hit, "med": st.median(vals),
            "mean": st.fmean(vals)}


def _line(label, s):
    if s is None:
        print(f"  {label:<22} --  no trades")
        return
    print(f"  {label:<22} n={s['n']:<4} hit={s['hit']:5.1%} "
          f"med={s['med']:+8.2f} mean={s['mean']:+8.2f}")


def _report(name, trades, sessions):
    per = f" = {len(trades) / sessions:.2f}/session" if sessions else ""
    print(f"\n{name}  ({len(trades)} trades over {sessions} sessions{per})")
    for h in HORIZON_BARS:
        _line(h, _stat([t[h] for t in trades]))
    _line("MFE (30m)", _stat([t["mfe"] for t in trades]))
    _line("MAE (30m)", _stat([t["mae"] for t in trades]))
    stopped = [t for t in trades if t["stopped"] is not None]
    if stopped:
        n_out = sum(1 for t in stopped if t["stopped"])
        _line(f"with {STOP_PTS:.0f}pt stop", _stat([t["stop_pts"] for t in stopped]))
        print(f"  {'stopped out':<22} {n_out}/{len(stopped)} "
              f"({n_out / len(stopped):.1%})")
    # §5 lesson 2: what survives without the single best trade?
    key = "+30m"
    vals = [t[key] for t in trades if t[key] is not None]
    if len(vals) > 1:
        vals.remove(max(vals))
        _line("+30m less best trade", _stat(vals))


def main():
    for idx in INDICES:
        print("=" * 66)
        print(idx)
        try:
            old_t, ctrl, sessions = collect(idx, _rows_old_all)
            old3_t, _, _ = collect(idx, _rows_old_d3)
            new_t, _, _ = collect(idx, _rows_new)
        except Exception as exc:                       # noqa: BLE001
            print(f"  could not load: {exc}")
            continue
        if not sessions:
            print("  no cached sessions")
            continue
        _report("OLD  one-candle, ALL bands+sides (what the pills mark)",
                old_t, sessions)
        _report("OLD  one-candle, d3 BUY only (§1's population, VOID)",
                old3_t, sessions)
        _report("NEW  two-candle, d3 BUY (the operator's rule, §5c)",
                new_t, sessions)
        print("\n  CONTROL  every post-09:25 bar, no signal")
        for h in HORIZON_BARS:
            _line(h, _stat(ctrl[h]))


if __name__ == "__main__":
    main()
