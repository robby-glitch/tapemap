"""Score the operator's band-rotation setup against data/backtest/.

THE GAP THIS CLOSES (HANDOFF SS7.1): `band_rotation.py` encodes the operator's
own edge and has NEVER been scored. Everything else in the tool that got this
treatment either died (squeeze+OI fade) or measured worse than a control (the
engine event stream). This file gives the one detector that matters the same
trial, using the same method those verdicts came from.

WHAT IS SCORED. `detect_index` -- the single-series entry point -- over the
cached futures sessions, on the 3-minute bars the operator actually reads
(squeeze_score.INTERVAL), banded by the validated pipeline (vwap_bands THEN
resample, 0.972 vs Kite). This scores the INDEX expression of the setup only:
`confirm` is UNKNOWN on every record by construction, so the two-leg rotation
confirm is NOT on trial here -- it cannot be until option-leg history is cached.

METHOD, stated so the numbers can be argued with (signal_review.py's rules):
  * Entry is the CLOSE of the trigger bar -- the reversal close IS the signal,
    so that bar's move is already spent. Deliberately pessimistic.
  * Forward move at +6/+15/+30 minutes (2/5/10 bars), SIGNED by the side:
    positive means price went the way the record pointed.
  * MFE/MAE over the following 30 minutes, signed the same way. MAE is where
    an unholdable winner shows.
  * Horizons past the session's last bar are excluded, never zero-filled.
  * CONTROL: the same horizons over EVERY post-anchor bar, no signal involved.
    On a trending day a random entry "wins" too; the spread is the finding.
  * Median beside every mean (both squeeze arms were outlier-skewed).
  * Per-index BEFORE pooled: the three indices trade the same market on the
    same days, so pooling inflates n without adding information.

SEGMENTS THE OPERATOR'S OPEN DECISIONS FORCE (HANDOFF SS8 -- score both arms,
decide nothing silently):
  * 09:25 gate: the spec anchors the COMPRESSION read at 09:25 but the trigger
    itself has no clock. Before ~09:25 sigma is near 0 and the bands hug VWAP,
    so a pierce-and-reclaim is nearly free to fire. Scored separately.
  * Re-fire: consecutive-bar fires of the same side are one episode to a
    human. FIRST-OF-RUN collapses them (a measurement choice, not a trading
    rule); ALL-FIRES is printed beside it.
  * Compression as context vs co-condition: records split by trap state.
  * Provenance: files without _meta are pre-June captures whose contract
    identity cannot be re-verified (Dhan serves nothing before 2026-06-01).
    Split, per backfill.py's warning.

    python rotation_score.py
"""

import statistics as st

import band_rotation as br
from squeeze_score import INTERVAL, load

INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
HORIZON_BARS = {"+6m": 2, "+15m": 5, "+30m": 10}
MFE_BARS = 30 // INTERVAL
ANCHOR_MIN = br.ANCHOR_MINUTE          # 09:25, the spec's own clock


def _minute(t):
    try:
        hh, mm = t.split(":")
        return int(hh) * 60 + int(mm)
    except (AttributeError, ValueError):
        return None


def collect(idx):
    """-> (rows, controls, meta) for one index.

    rows: one dict per detect_index record across every cached session.
    controls: signed-long forward moves per horizon over every post-anchor bar.
    """
    days = load(idx)
    rows = []
    controls = {k: [] for k in HORIZON_BARS}
    n_files = len(days)
    n_expiry = sum(1 for d in days.values() if d["expiry"])
    for day, D in sorted(days.items()):
        bars = D["bars"]
        close = [b["c"] for b in bars]
        high = [b["h"] for b in bars]
        low = [b["l"] for b in bars]
        recs = br.detect_index(bars)
        prev_i, prev_side = None, None
        for i, r in enumerate(recs):
            if r is None:
                continue
            d = 1 if r["side"] == "BUY" else -1
            row = {"day": day, "t": r["t"], "i": i, "side": r["side"],
                   "band": r["band"], "trap": r["trap"], "dir": d,
                   "px": close[i], "expiry": D["expiry"],
                   "meta": D["fut_id"] is not None,
                   "anchored": (_minute(r["t"]) or 0) >= ANCHOR_MIN,
                   # first bar of a consecutive same-side run
                   "first": not (prev_i == i - 1 and prev_side == r["side"])}
            prev_i, prev_side = i, r["side"]
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
            rows.append(row)
        for i, b in enumerate(bars):
            if (_minute(b["t"]) or 0) < ANCHOR_MIN:
                continue
            for name, h in HORIZON_BARS.items():
                j = i + h
                if j < len(close):
                    controls[name].append(close[j] - close[i])
    return rows, controls, {"files": n_files, "expiry": n_expiry}


def _stat(rows, key):
    v = [r[key] for r in rows if r[key] is not None]
    if not v:
        return None
    return {"n": len(v), "mean": st.mean(v), "med": st.median(v),
            "hit": sum(1 for x in v if x > 0) / len(v)}


def _fmt(s):
    if s is None:
        return f"{'--':>26}"
    return (f"{s['mean']:+7.1f} {s['med']:+7.1f} "
            f"{s['hit'] * 100:4.0f}% n={s['n']:<4}")


def _line(label, rows):
    mfe = _stat(rows, "mfe")
    mae = _stat(rows, "mae")
    m1 = f"{mfe['mean']:+6.1f}" if mfe else "   n/a"
    m2 = f"{mae['mean']:+6.1f}" if mae else "   n/a"
    print(f"  {label:<26}{_fmt(_stat(rows, '+15m'))} {_fmt(_stat(rows, '+30m'))}"
          f"  {m1} {m2}")


def report(idx, rows, controls, meta):
    total = len(rows)
    primary = [r for r in rows if r["anchored"] and r["first"]]
    print(f"\n{'=' * 100}")
    print(f"{idx} -- {meta['files']} sessions ({meta['expiry']} monthly-expiry)"
          f" -- {total} raw fires, {len(primary)} first-of-run post-09:25")
    if not rows:
        print("  no records at all")
        return primary
    hdr = (f"  {'segment':<26}{'+15m avg':>8}{'med':>8}{'hit':>5}{'':>7}"
           f"{'+30m avg':>8}{'med':>8}{'hit':>5}{'':>7}{'MFE':>7}{'MAE':>7}")
    print(hdr)
    print("  " + "-" * 98)
    _line("PRIMARY (first, >=09:25)", primary)
    for side in ("BUY", "SELL"):
        for band in ("d2", "d3", "u3"):
            rs = [r for r in primary if r["side"] == side and r["band"] == band]
            if rs:
                _line(f"  {side} {band}", rs)
    print()
    for trap in ("CLEAR", "SUSPECT", "UNKNOWN"):
        rs = [r for r in primary if r["trap"] == trap]
        if rs:
            _line(f"  trap={trap}", rs)
    print()
    _line("all fires (no dedup)", [r for r in rows if r["anchored"]])
    _line("pre-09:25 (spec: no read)", [r for r in rows if not r["anchored"]])
    nometa = [r for r in primary if not r["meta"]]
    withmeta = [r for r in primary if r["meta"]]
    if nometa and withmeta:
        _line("capture, no _meta", nometa)
        _line("backfilled, _meta", withmeta)
    exp = [r for r in primary if r["expiry"]]
    if exp:
        _line("monthly-expiry sessions", exp)
    ctl15, ctl30 = controls["+15m"], controls["+30m"]
    if ctl30:
        print(f"\n  CONTROL every post-09:25 bar: +15m long "
              f"{st.mean(ctl15):+.1f} (med {st.median(ctl15):+.1f}), "
              f"+30m long {st.mean(ctl30):+.1f} (med {st.median(ctl30):+.1f}), "
              f"{sum(1 for x in ctl30 if x > 0) / len(ctl30):.0%} up, "
              f"n={len(ctl30)}")
        print(f"  (a short's control is the negation; |control| is the bar "
              f"a signal must clear)")
    return primary


def main():
    pooled = []
    for idx in INDICES:
        rows, controls, meta = collect(idx)
        pooled.extend(report(idx, rows, controls, meta))
    print(f"\n{'=' * 100}")
    print(f"POOLED first-of-run post-09:25 -- WARNING: the three indices "
          f"co-move on the same days;\nan effect that only survives pooling "
          f"is a warning, not a result")
    _line("POOLED", pooled)
    print("\nFutures points, no costs, fixed horizons -- not a trading rule. "
          "The two-leg CONFIRM is not on trial\nhere (single series -> UNKNOWN "
          "by construction). Treat as the first measurement, not the verdict.")


if __name__ == "__main__":
    main()
