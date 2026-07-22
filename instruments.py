"""Instrument registry: one config per tradable index. Static fields live here;
volatile fields (futures security-id, current expiry, prior trading day) are
resolved at startup from the Dhan scrip master + expiry_list.

All identifiers below were confirmed against live Dhan on 2026-07-23:
  - detailed scrip-master cols: SECURITY_ID, UNDERLYING_SYMBOL, INSTRUMENT
    (FUTIDX/OPTIDX), SM_EXPIRY_DATE (YYYY-MM-DD), STRIKE_PRICE, OPTION_TYPE,
    EXCH_ID (NSE/BSE).
  - option_chain(under_id, under_seg, expiry) works with under_seg="IDX_I"
    for all three indices, including SENSEX on BSE (chain_seg is unused by the
    chain API and kept only for documentation).
  - nearest futures: NIFTY 61093 / BANKNIFTY 61088 / SENSEX 1144507.
  - fut_seg is the F&O exchange segment for intraday charts (NSE_FNO / BSE_FNO)
    and is used for both futures and option legs of each index.
"""
import csv
import io
import urllib.request
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
SCRIP_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"

INSTRUMENTS = {
    "NIFTY":     {"under_id": 13, "under_seg": "IDX_I", "chain_seg": "NSE_FNO",
                  "fut_seg": "NSE_FNO", "step": 100, "window": 1500,
                  "under_sym": "NIFTY"},
    "BANKNIFTY": {"under_id": 25, "under_seg": "IDX_I", "chain_seg": "NSE_FNO",
                  "fut_seg": "NSE_FNO", "step": 100, "window": 2000,
                  "under_sym": "BANKNIFTY"},
    "SENSEX":    {"under_id": 51, "under_seg": "IDX_I", "chain_seg": "BSE_FNO",
                  "fut_seg": "BSE_FNO", "step": 100, "window": 2500,
                  "under_sym": "SENSEX"},
}
DEFAULT = "NIFTY"
ENABLED = ["NIFTY", "BANKNIFTY", "SENSEX"]

# confirmed detailed-scrip-master column names (Task 0, 2026-07-23)
COL_SID, COL_UND, COL_INSTR, COL_EXP = (
    "SECURITY_ID", "UNDERLYING_SYMBOL", "INSTRUMENT", "SM_EXPIRY_DATE")


def get(idx):
    """Shallow copy of the static config for `idx` (raises KeyError if unknown)."""
    return dict(INSTRUMENTS[idx])


def _load_scrip():
    with urllib.request.urlopen(SCRIP_URL, timeout=60) as r:
        raw = r.read().decode("utf-8", "ignore")
    return list(csv.DictReader(io.StringIO(raw)))


def resolve_futures_id(rows, under_sym, today):
    """Nearest non-expired monthly future for `under_sym`.

    `rows` are parsed scrip-master dicts; `today` is 'YYYY-MM-DD'. Returns
    (security_id, expiry). Options rows (INSTRUMENT=OPTIDX) are excluded by the
    'FUT' substring test; expired contracts by the date compare."""
    cands = [r for r in rows
             if r.get(COL_UND) == under_sym
             and "FUT" in (r.get(COL_INSTR) or "")
             and (r.get(COL_EXP) or "") >= today]
    if not cands:
        raise RuntimeError(f"no unexpired future for {under_sym}")
    r = min(cands, key=lambda x: x.get(COL_EXP))
    return r[COL_SID], r[COL_EXP]


def _prev_trading_day(today):
    """Prior weekday (Sat/Sun skipped; holidays not modelled — YAGNI)."""
    d = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=IST) - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def resolve_dynamic(cfg, tok, today, rows=None):
    """Augment `cfg` in place with fut_id, expiry, prev_day and return it.

    `tok` is accepted for signature parity / future auth needs; the scrip
    master is a public CSV so it is not currently used. Pass pre-loaded `rows`
    to resolve several indices from ONE scrip-master download instead of one
    per index."""
    if rows is None:
        rows = _load_scrip()
    cfg["fut_id"], cfg["expiry"] = resolve_futures_id(rows, cfg["under_sym"], today)
    cfg["prev_day"] = _prev_trading_day(today)
    return cfg
