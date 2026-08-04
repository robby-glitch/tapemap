"""Does the operator's d3 band-reversal generalize to F&O STOCK futures?

WHY (2026-08-04, operator asked directly). The setup is validated on NIFTY
(72% hit, med +21 @30m) and echoes on SENSEX; BANKNIFTY inverts. Indices are
baskets — a single stock has idiosyncratic news, wider spreads and gappier
tape, so generalization is a QUESTION, not an assumption.

WHAT THIS DOES, in one command:
  1. RESOLVE  front-month NSE stock futures from data/scrip_master.csv.
  2. FETCH    1-min bars + OI per session via dhan_fetch.rest_intraday,
              2026-06-02 -> 2026-08-01 (Dhan serves nothing older — HANDOFF
              §5), sliced with _one_session (the toDate gotcha), cached to
              data/backtest/STOCKS/<SYM>/fut_<ISO>.json with _meta. Cached
              files are never re-fetched, so re-runs are free and offline.
  3. SCORE    the same trial rotation_score ran on the indices: banded 3-min
              bars (vwap_bands THEN resample — the validated order),
              detect_index, first-of-run post-09:30 BUY d3/d2 and SELL,
              forward +15/+30m, per-stock before pooled, with controls.

UNITS. Stocks trade at wildly different prices, so moves are scored in
PERCENT of entry (x100). NIFTY's +21 pts on 24,600 ≈ +0.085% for comparison.

    python stock_score.py                    # default liquid-8 list
    python stock_score.py RELIANCE SBIN ...  # your own symbols
"""

import csv
import glob
import json
import os
import statistics as st
import sys
import time
from datetime import date, timedelta

import band_rotation as br
import contract_bars as cb
import dhan_fetch as DF

DEFAULT = ("RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN",
           "INFY", "TATAMOTORS", "BAJFINANCE", "ADANIENT")
START, END = "2026-06-02", "2026-08-01"
ROOT = os.path.join("data", "backtest", "STOCKS")
ANCHOR = "09:30"                 # the operator's own gate
HORIZ = {"+15m": 5, "+30m": 10}  # 3-min bars
MFE_BARS = 10


def resolve(sym):
    """Front-month NSE FUTSTK row for one underlying, or None."""
    with open(os.path.join("data", "scrip_master.csv"),
              encoding="utf-8", errors="replace") as f:
        rows = [r for r in csv.DictReader(f)
                if r["EXCH_ID"] == "NSE" and r["INSTRUMENT"] == "FUTSTK"
                and r["UNDERLYING_SYMBOL"] == sym]
    if not rows:
        return None
    # nearest expiry = front month; the AUG contract in Aug 2026
    key = "SM_EXPIRY_DATE" if "SM_EXPIRY_DATE" in rows[0] else None
    if key:
        rows.sort(key=lambda r: r.get(key) or "9999")
    return rows[0]


def _sessions():
    d, out = date.fromisoformat(START), []
    end = date.fromisoformat(END)
    while d <= end:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def fetch(sym, row, tok):
    """Cache every missing session. Returns (cached, fetched, empty)."""
    os.makedirs(os.path.join(ROOT, sym), exist_ok=True)
    cached = fetched = empty = 0
    for day in _sessions():
        path = os.path.join(ROOT, sym, f"fut_{day}.json")
        if os.path.exists(path):
            cached += 1
            continue
        try:
            raw = DF.rest_intraday(tok, row["SECURITY_ID"], "FUTSTK",
                                   day, oi=True)
            # _one_session returns (payload, served, lost) — unpack it
            one, _served, _lost = DF._one_session(raw, day)
            n = len((one or {}).get("open") or [])
        except Exception:
            n, one = 0, None
        time.sleep(0.25)                      # Data API: 5 req/s
        if n < 60:                            # holiday / no data: skip, no file
            empty += 1
            continue
        one["_meta"] = {"symbol": sym, "sec_id": row["SECURITY_ID"],
                        "expiry": row.get("SM_EXPIRY_DATE"),
                        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(one, f)
        fetched += 1
    return cached, fetched, empty


def load(sym):
    """{day: banded 3-min bars} — the validated pipeline, stocks edition."""
    out = {}
    for p in sorted(glob.glob(os.path.join(ROOT, sym, "fut_*.json"))):
        day = os.path.basename(p)[4:14]
        try:
            payload = json.load(open(p))
            bars = cb.resample(cb.vwap_bands(cb.to_bars(payload)), 3)
        except Exception:
            continue
        if len(bars) >= 60:
            out[day] = bars
    return out


def score(sym):
    days = load(sym)
    rows = []
    controls = {k: [] for k in HORIZ}
    for day, bars in sorted(days.items()):
        close = [b["c"] for b in bars]
        high = [b["h"] for b in bars]
        low = [b["l"] for b in bars]
        recs = br.detect_index(bars)
        prev_i = prev_side = None
        for i, r in enumerate(recs):
            if r is None:
                continue
            d = 1 if r["side"] == "BUY" else -1
            first = not (prev_i == i - 1 and prev_side == r["side"])
            prev_i, prev_side = i, r["side"]
            if not first or (r["t"] or "") < ANCHOR:
                continue
            px = close[i]
            row = {"day": day, "t": r["t"], "side": r["side"],
                   "band": r["band"], "px": px}
            for name, h in HORIZ.items():
                j = i + h
                row[name] = (None if j >= len(close)
                             else d * (close[j] - px) / px * 100)
            hs = high[i + 1:i + 1 + MFE_BARS]
            ls = low[i + 1:i + 1 + MFE_BARS]
            if hs:
                row["mfe"] = d * ((max(hs) if d > 0 else min(ls)) - px) / px * 100
                row["mae"] = d * ((min(ls) if d > 0 else max(hs)) - px) / px * 100
            else:
                row["mfe"] = row["mae"] = None
            rows.append(row)
        for i, b in enumerate(bars):
            if (b.get("t") or "") < ANCHOR:
                continue
            for name, h in HORIZ.items():
                j = i + h
                if j < len(close):
                    controls[name].append((close[j] - close[i]) / close[i] * 100)
    return days, rows, controls


def _stat(rows, key):
    v = [r[key] for r in rows if r[key] is not None]
    if not v:
        return None
    return {"n": len(v), "mean": st.mean(v), "med": st.median(v),
            "hit": sum(1 for x in v if x > 0) / len(v)}


def _line(label, rows):
    s30 = _stat(rows, "+30m")
    if not s30:
        return
    s15 = _stat(rows, "+15m")
    mfe, mae = _stat(rows, "mfe"), _stat(rows, "mae")
    print(f"  {label:<22}n={s30['n']:<4}"
          f"+15m {s15['mean']:+6.3f}%/{s15['med']:+6.3f} {s15['hit']:4.0%}  "
          f"+30m {s30['mean']:+6.3f}%/{s30['med']:+6.3f} {s30['hit']:4.0%}  "
          f"MFE {mfe['mean']:+6.3f} MAE {mae['mean']:+6.3f}")


def main():
    syms = [s.upper() for s in sys.argv[1:]] or list(DEFAULT)
    try:
        tok = open(".dhan_token").read().strip()
    except OSError:
        tok = None
    pooled = {"BUY d3": [], "BUY d2": [], "SELL u3": []}
    for sym in syms:
        row = resolve(sym)
        if row is None:
            print(f"\n{sym}: not in the scrip master (F&O list changes) — skipped")
            continue
        if tok:
            c, f, e = fetch(sym, row, tok)
            note = f"{c} cached, {f} fetched, {e} empty"
        else:
            note = "no .dhan_token — cache only"
        days, rows, controls = score(sym)
        print(f"\n{sym} ({row['SECURITY_ID']}, exp {row.get('SM_EXPIRY_DATE')})"
              f" — {len(days)} sessions [{note}]")
        buckets = {"BUY d3": [r for r in rows if r["side"] == "BUY" and r["band"] == "d3"],
                   "BUY d2": [r for r in rows if r["side"] == "BUY" and r["band"] == "d2"],
                   "SELL u3": [r for r in rows if r["side"] == "SELL"]}
        for k, rs in buckets.items():
            _line(k, rs)
            pooled[k].extend(rs)
        c30 = controls["+30m"]
        if c30:
            print(f"  control +30m long: {st.mean(c30):+.3f}% "
                  f"(med {st.median(c30):+.3f}, {sum(1 for x in c30 if x > 0) / len(c30):.0%} up)")
    print(f"\n{'=' * 88}\nPOOLED across stocks — stocks co-move with the index; "
          f"treat pooled numbers as a hint, not a result")
    for k, rs in pooled.items():
        _line(k, rs)
    print(f"\nNIFTY yardstick, same units: BUY d3 med ≈ +0.085% @30m, 72% hit. "
          f"Percent of entry, no costs,\nfixed horizons — not a trading rule. "
          f"First measurement, not a verdict.")


if __name__ == "__main__":
    main()
