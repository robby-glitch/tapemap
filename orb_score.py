"""Score a classic Opening Range Breakout (ORB) on the 15-minute frame.

THE RULE ON TRIAL (the textbook one, stated so deviations are visible):
  * The opening range is the FIRST 15-minute candle, 09:15-09:29.
  * The signal is the first 15-minute bar AFTER it whose CLOSE is outside the
    range -- close above ORH = long, close below ORL = short. Close-based,
    not wick-based: a wick entry cannot be replayed without intrabar data.
  * One trade per day, the first breakout, whichever side. No re-entry.
  * Entry at that bar's close (same pessimism as rotation_score / signal_review:
    the bar that made the signal is already spent).

MEASURED, signed by the trade's direction:
  * +30m / +60m forward moves (2 / 4 bars of 15m) and TO-CLOSE (the classic
    ORB hold), each excluded when the session ends first, never zero-filled.
  * MFE / MAE from entry to session close -- what a stop would have to survive.
  * CONTROL: the same horizons over EVERY 15-minute bar, no signal involved,
    plus the unconditional hold from the second bar's close to session close.
    On a trend day every breakout "works"; the spread is the finding.
  * Median beside every mean; per-index BEFORE pooled (co-moving indices).

SEGMENTS, because a pooled ORB number hides everything that matters:
  * LONG vs SHORT breakouts.
  * NARROW vs WIDE opening range (split at the index's own median OR width) --
    the classic claim is that a narrow OR travels further.
  * EARLY (break by 11:00) vs LATE -- the classic claim is that late breaks fail.
  * Provenance: live capture (no _meta) vs backfilled contract (_meta).

Days whose feed did not start at 09:15 are skipped and counted -- an opening
range built on a late first bar is a different object, not a worse estimate.

    python orb_score.py
"""

import statistics as st

import contract_bars as cb
from squeeze_score import load

INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
HORIZON_BARS = {"+30m": 2, "+60m": 4}
EARLY_HHMM = "11:00"


def collect(idx):
    days = load(idx)
    rows, skipped, nobreak = [], 0, 0
    controls = {k: [] for k in HORIZON_BARS}
    controls["hold"] = []
    for day, D in sorted(days.items()):
        b15 = cb.resample(D["bars"], 15)
        if len(b15) < 6 or b15[0]["t"] != "09:15":
            skipped += 1
            continue
        orh, orl = b15[0]["h"], b15[0]["l"]
        close = [b["c"] for b in b15]
        high = [b["h"] for b in b15]
        low = [b["l"] for b in b15]
        # control: every bar after the OR bar
        for i in range(1, len(b15)):
            for name, h in HORIZON_BARS.items():
                if i + h < len(close):
                    controls[name].append(close[i + h] - close[i])
        controls["hold"].append(close[-1] - close[1])
        hit = None
        for i in range(1, len(b15)):
            if close[i] > orh:
                hit = (i, 1)
                break
            if close[i] < orl:
                hit = (i, -1)
                break
        if hit is None:
            nobreak += 1
            continue
        i, d = hit
        row = {"day": day, "t": b15[i]["t"], "dir": d, "px": close[i],
               "orw": orh - orl, "expiry": D["expiry"],
               "meta": D["fut_id"] is not None,
               "early": b15[i]["t"] <= EARLY_HHMM,
               "last": i == len(b15) - 1}
        for name, h in HORIZON_BARS.items():
            j = i + h
            row[name] = None if j >= len(close) else d * (close[j] - close[i])
        row["toclose"] = None if row["last"] else d * (close[-1] - close[i])
        hs, ls = high[i + 1:], low[i + 1:]
        if hs:
            row["mfe"] = d * ((max(hs) if d > 0 else min(ls)) - close[i])
            row["mae"] = d * ((min(ls) if d > 0 else max(hs)) - close[i])
        else:
            row["mfe"] = row["mae"] = None
        rows.append(row)
    return rows, controls, {"files": len(days), "skipped": skipped,
                            "nobreak": nobreak}


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
            f"{s['hit'] * 100:4.0f}% n={s['n']:<3}")


def _line(label, rows):
    mfe = _stat(rows, "mfe")
    mae = _stat(rows, "mae")
    m1 = f"{mfe['mean']:+7.1f}" if mfe else "    n/a"
    m2 = f"{mae['mean']:+7.1f}" if mae else "    n/a"
    print(f"  {label:<24}{_fmt(_stat(rows, '+30m'))} "
          f"{_fmt(_stat(rows, 'toclose'))}  {m1} {m2}")


def report(idx, rows, controls, meta):
    print(f"\n{'=' * 100}")
    print(f"{idx} -- {meta['files']} sessions: {len(rows)} breakouts, "
          f"{meta['nobreak']} never broke, {meta['skipped']} skipped (late feed)")
    if not rows:
        return rows
    print(f"  {'segment':<24}{'+30m avg':>8}{'med':>8}{'hit':>5}{'':>6}"
          f"{'to-close avg':>12}{'med':>8}{'hit':>5}{'':>5}{'MFE':>8}{'MAE':>8}")
    print("  " + "-" * 98)
    _line("ALL (first break)", rows)
    _line("  LONG break", [r for r in rows if r["dir"] > 0])
    _line("  SHORT break", [r for r in rows if r["dir"] < 0])
    med_w = st.median([r["orw"] for r in rows])
    _line(f"  narrow OR (<{med_w:.0f}p)", [r for r in rows if r["orw"] < med_w])
    _line(f"  wide OR (>={med_w:.0f}p)", [r for r in rows if r["orw"] >= med_w])
    _line(f"  early (<= {EARLY_HHMM})", [r for r in rows if r["early"]])
    _line(f"  late  (>  {EARLY_HHMM})", [r for r in rows if not r["early"]])
    nometa = [r for r in rows if not r["meta"]]
    withmeta = [r for r in rows if r["meta"]]
    if nometa and withmeta:
        _line("  capture, no _meta", nometa)
        _line("  backfilled, _meta", withmeta)
    exp = [r for r in rows if r["expiry"]]
    if exp:
        _line("  monthly-expiry days", exp)
    c30, hold = controls["+30m"], controls["hold"]
    print(f"\n  CONTROL every 15m bar: +30m long {st.mean(c30):+.1f} "
          f"(med {st.median(c30):+.1f}, {sum(1 for x in c30 if x > 0) / len(c30):.0%} up, "
          f"n={len(c30)}); hold 09:45->close long {st.mean(hold):+.1f} "
          f"(med {st.median(hold):+.1f})")
    return rows


def main():
    pooled = []
    for idx in INDICES:
        rows, controls, meta = collect(idx)
        pooled.extend(report(idx, rows, controls, meta))
    print(f"\n{'=' * 100}")
    print("POOLED -- WARNING: the three indices co-move; an effect that only "
          "survives pooling is a warning, not a result")
    _line("POOLED", pooled)
    print("\nFutures points, no costs, close-based entries, one trade per day. "
          "No stop/target -- MFE/MAE show what\nany exit rule has to work with. "
          "First measurement, not a verdict.")


if __name__ == "__main__":
    main()
