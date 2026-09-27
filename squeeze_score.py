"""The cached-session loader: data/backtest/ -> banded 3-minute bars.

`trigger_log.score` reads every cached session through `load`, and
`eod_capture` / `recover_tape` write files in the layout `_paths` reads.

This file was the scorer for the "squeeze + falling OI" hypothesis, which
research-findings §2 rejected. The scorer is retired under the §5 stop rule;
only its loader stays, because the forward record is scored through it.
"""

import glob
import json
import os
from datetime import date, timedelta

import band_rotation
import contract_bars as cb

BT = "data/backtest"
# minutes per bar; the operator reads 3-min charts. Read from band_rotation
# rather than restated, so the interval this scorer measures on and the one the
# live tape publishes cannot drift apart -- see SCORED_INTERVAL there.
INTERVAL = band_rotation.SCORED_INTERVAL


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
