"""Overnight gap-fade, scored as a TEST OF THE REGIME MAP.

Three independent measurements (squeeze_score, rotation_score, orb_score) drew
the same picture: NIFTY mean-reverts intraday, BANKNIFTY trends. A gap is the
purest overnight stretch there is -- displacement from yesterday's close with
zero intraday information yet. If the regime map is real it must predict gap
behaviour too.

PRE-REGISTERED PREDICTIONS (written before the first run; anything found
beyond these three is hypothesis-generation, not evidence -- contrarian.py's
discipline):
  P1. NIFTY gap-fade is +EV: fading the open toward prior close pays, and
      most gaps fill.
  P2. BANKNIFTY gap-fade fails or inverts: its gaps run rather than fill.
  P3. Large gaps fill less often than small ones (gap-and-go).

THE RULE. Gap = today's first bar OPEN minus the prior cached session's last
CLOSE, paired only when the two files are <= 4 calendar days apart (a missing
session in between would mis-measure the gap; those pairs are skipped and
counted). Fade = trade TOWARD prior close: short a gap-up, long a gap-down.
Entry at the CLOSE of the first 3-minute bar (the house pessimism: the open
itself is not tradeable). Exit at the FILL (first touch of prior close, from
bar 2 on) or at session close, whichever comes first. No stop -- MFE/MAE show
what a stop rule would have to work with.

MEASURED per index, then pooled with the usual co-movement warning:
fill rate, median time-to-fill, P&L (fill-or-EOD) mean/median/hit, MFE/MAE
to EOD, segmented by gap direction, |gap| tercile, expiry, provenance.
CONTROL: the unconditional long hold from the same entry bar to session close
across ALL paired days -- the drift a signed result must clear.

    python gap_score.py
"""

import statistics as st
from datetime import date

from squeeze_score import load

INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
MAX_PAIR_GAP_DAYS = 4


def collect(idx):
    days = load(idx)
    order = sorted(days)
    rows, unpaired = [], 0
    controls = []
    for prev, today in zip(order, order[1:]):
        if (date.fromisoformat(today) - date.fromisoformat(prev)).days > MAX_PAIR_GAP_DAYS:
            unpaired += 1
            continue
        pbars, tbars = days[prev]["bars"], days[today]["bars"]
        prior_close = pbars[-1]["c"]
        open_px = tbars[0]["o"]
        entry = tbars[0]["c"]
        gap = open_px - prior_close
        d = -1 if gap > 0 else 1          # fade: toward prior close
        close = [b["c"] for b in tbars]
        high = [b["h"] for b in tbars]
        low = [b["l"] for b in tbars]
        controls.append(close[-1] - entry)
        fill_i = None
        for i in range(1, len(tbars)):
            touched = (low[i] <= prior_close) if d < 0 else (high[i] >= prior_close)
            if touched:
                fill_i = i
                break
        if fill_i is not None:
            pnl = d * (prior_close - entry)
        else:
            pnl = d * (close[-1] - entry)
        hs, ls = high[1:], low[1:]
        rows.append({
            "day": today, "gap": gap, "agap": abs(gap),
            "gpct": abs(gap) / prior_close * 100, "dir": d,
            "filled": fill_i is not None,
            "fill_t": tbars[fill_i]["t"] if fill_i is not None else None,
            "pnl": pnl,
            "eod": d * (close[-1] - entry),
            "mfe": d * ((max(hs) if d > 0 else min(ls)) - entry) if hs else None,
            "mae": d * ((min(ls) if d > 0 else max(hs)) - entry) if hs else None,
            "expiry": days[today]["expiry"],
            "meta": days[today]["fut_id"] is not None,
        })
    return rows, controls, unpaired


def _stat(rows, key):
    v = [r[key] for r in rows if r[key] is not None]
    if not v:
        return None
    return {"n": len(v), "mean": st.mean(v), "med": st.median(v),
            "hit": sum(1 for x in v if x > 0) / len(v)}


def _line(label, rows):
    if not rows:
        return
    p = _stat(rows, "pnl")
    mfe = _stat(rows, "mfe")
    mae = _stat(rows, "mae")
    fills = [r for r in rows if r["filled"]]
    ft = sorted(r["fill_t"] for r in fills)
    med_t = ft[len(ft) // 2] if ft else " --  "
    m1 = f"{mfe['mean']:+7.1f}" if mfe else "    n/a"
    m2 = f"{mae['mean']:+7.1f}" if mae else "    n/a"
    print(f"  {label:<26}{len(rows):>4} {len(fills) / len(rows) * 100:5.0f}% "
          f"{med_t:>6}  {p['mean']:+8.1f} {p['med']:+8.1f} {p['hit'] * 100:4.0f}%"
          f"  {m1} {m2}")


def report(idx, rows, controls, unpaired):
    print(f"\n{'=' * 100}")
    print(f"{idx} -- {len(rows)} paired gap days ({unpaired} pairs skipped: "
          f"cache hole > {MAX_PAIR_GAP_DAYS}d)")
    if not rows:
        return rows
    print(f"  {'segment':<26}{'n':>4} {'fill%':>5} {'med-t':>6}  "
          f"{'P&L avg':>8} {'med':>8} {'hit':>5}  {'MFE':>7} {'MAE':>7}")
    print("  " + "-" * 96)
    _line("ALL gap-fades", rows)
    _line("  gap UP (short)", [r for r in rows if r["dir"] < 0])
    _line("  gap DOWN (long)", [r for r in rows if r["dir"] > 0])
    qs = st.quantiles([r["agap"] for r in rows], n=3)
    _line(f"  small |gap| (<{qs[0]:.0f}p)", [r for r in rows if r["agap"] < qs[0]])
    _line(f"  mid   |gap|", [r for r in rows if qs[0] <= r["agap"] < qs[1]])
    _line(f"  large |gap| (>={qs[1]:.0f}p)", [r for r in rows if r["agap"] >= qs[1]])
    nometa = [r for r in rows if not r["meta"]]
    withmeta = [r for r in rows if r["meta"]]
    if nometa and withmeta:
        _line("  capture, no _meta", nometa)
        _line("  backfilled, _meta", withmeta)
    _line("  monthly-expiry days", [r for r in rows if r["expiry"]])
    print(f"\n  CONTROL long hold entry->close, all paired days: "
          f"{st.mean(controls):+.1f} (med {st.median(controls):+.1f}, "
          f"{sum(1 for x in controls if x > 0) / len(controls):.0%} up, n={len(controls)})")
    return rows


def main():
    pooled = []
    for idx in INDICES:
        rows, controls, unpaired = collect(idx)
        pooled.extend(report(idx, rows, controls, unpaired))
    print(f"\n{'=' * 100}")
    print("POOLED -- WARNING: the three indices gap together on the same "
          "mornings; a pooled effect is a warning, not a result")
    print(f"  {'segment':<26}{'n':>4} {'fill%':>5} {'med-t':>6}  "
          f"{'P&L avg':>8} {'med':>8} {'hit':>5}  {'MFE':>7} {'MAE':>7}")
    _line("POOLED", pooled)
    print("\nVERDICT vs the pre-registered predictions is read off the tables "
          "above -- P1 NIFTY fade +EV;\nP2 BANKNIFTY fails/inverts; P3 large "
          "gaps fill less. Futures points, no costs, no stop.\n"
          "First measurement, not a verdict.")


if __name__ == "__main__":
    main()
