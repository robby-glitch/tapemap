"""Guards for the 2026-07-27 outage fixes: ATM-id caching (no per-cycle
scrip-master download), loud failure on unresolvable legs, and the disk-cache
freshness rule."""
import os
import time

import pytest

import instruments
import live

ROWS = [
    {"UNDERLYING_SYMBOL": "NIFTY", "INSTRUMENT": "OPTIDX",
     "SM_EXPIRY_DATE": "2026-07-28", "OPTION_TYPE": "CE",
     "STRIKE_PRICE": "23850", "SECURITY_ID": "1001"},
    {"UNDERLYING_SYMBOL": "NIFTY", "INSTRUMENT": "OPTIDX",
     "SM_EXPIRY_DATE": "2026-07-28", "OPTION_TYPE": "PE",
     "STRIKE_PRICE": "23850", "SECURITY_ID": "1002"},
    {"UNDERLYING_SYMBOL": "NIFTY", "INSTRUMENT": "OPTIDX",
     "SM_EXPIRY_DATE": "2026-07-28", "OPTION_TYPE": "CE",
     "STRIKE_PRICE": "23900", "SECURITY_ID": "1003"},
    {"UNDERLYING_SYMBOL": "NIFTY", "INSTRUMENT": "OPTIDX",
     "SM_EXPIRY_DATE": "2026-07-28", "OPTION_TYPE": "PE",
     "STRIKE_PRICE": "23900", "SECURITY_ID": "1004"},
    # different expiry: must never be picked for 2026-07-28
    {"UNDERLYING_SYMBOL": "NIFTY", "INSTRUMENT": "OPTIDX",
     "SM_EXPIRY_DATE": "2026-08-25", "OPTION_TYPE": "CE",
     "STRIKE_PRICE": "23850", "SECURITY_ID": "9999"},
]
CFG = {"under_sym": "NIFTY", "expiry": "2026-07-28", "step": 100}


def test_atm_ids_resolves_and_caches(monkeypatch):
    calls = {"n": 0}

    def fake(force=False):
        calls["n"] += 1
        return ROWS

    monkeypatch.setattr(instruments, "_load_scrip", fake)
    live._ids_cache.clear()
    assert live._atm_ids(23850.0, CFG) == {"CE": "1001", "PE": "1002"}
    assert live._atm_ids(23850.0, CFG) == {"CE": "1001", "PE": "1002"}
    assert calls["n"] == 1                 # second call served from cache

    # strike migration is a NEW key -> one more scan, correct ids
    assert live._atm_ids(23900.0, CFG) == {"CE": "1003", "PE": "1004"}
    assert calls["n"] == 2


def test_atm_ids_missing_leg_raises(monkeypatch):
    monkeypatch.setattr(instruments, "_load_scrip",
                        lambda force=False: ROWS[:1])   # CE only, no PE
    live._ids_cache.clear()
    with pytest.raises(RuntimeError):
        live._atm_ids(23850.0, CFG)


def test_atm_ids_far_strike_raises(monkeypatch):
    # nearest listed strike is 500 pts away (> one 100-pt step): a truncated
    # scrip master must fail loudly, never chart a far contract
    monkeypatch.setattr(instruments, "_load_scrip", lambda force=False: ROWS)
    live._ids_cache.clear()
    with pytest.raises(RuntimeError):
        live._atm_ids(23350.0, CFG)


def test_cache_fresh_today_and_size(tmp_path):
    f = tmp_path / "scrip_master.csv"
    f.write_bytes(b"x" * 6_000_000)
    assert instruments._cache_fresh(f)                  # big + written today

    f.write_bytes(b"x" * 100)
    assert not instruments._cache_fresh(f)              # too small = truncated


def test_cache_fresh_rejects_yesterday(tmp_path):
    f = tmp_path / "scrip_master.csv"
    f.write_bytes(b"x" * 6_000_000)
    old = time.time() - 2 * 86400
    os.utime(f, (old, old))
    assert not instruments._cache_fresh(f)


def test_cache_fresh_missing_file(tmp_path):
    assert not instruments._cache_fresh(tmp_path / "nope.csv")


# ── current-expiry resolution + option pivots (2026-08-01) ──────────────────
# The operator trades the CURRENT expiry only; the tape used to resolve its
# option legs at cfg["expiry"], which resolve_dynamic sets from the FUTURES
# (monthly) contract. These lock the fix and the new opt_pivots block.

def test_nearest_opt_expiry_picks_current_not_monthly(monkeypatch):
    monkeypatch.setattr(instruments, "_load_scrip", lambda force=False: ROWS)
    live._opt_exp_cache.clear()
    # Before the near expiry: pick it, not the monthly.
    assert live._nearest_opt_expiry("NIFTY", "2026-07-27") == "2026-07-28"
    # ON expiry day the current expiry stays current until close (>=, not >).
    live._opt_exp_cache.clear()
    assert live._nearest_opt_expiry("NIFTY", "2026-07-28") == "2026-07-28"
    # After it rolls, the next one (here the monthly) becomes current.
    live._opt_exp_cache.clear()
    assert live._nearest_opt_expiry("NIFTY", "2026-07-29") == "2026-08-25"
    # No expiry at all fails loudly rather than charting a guess.
    live._opt_exp_cache.clear()
    with pytest.raises(RuntimeError):
        live._nearest_opt_expiry("NOSUCH", "2026-07-27")


def test_floor_pivots_matches_this_repos_convention():
    p = live._floor_pivots(100.0, 90.0, 95.0)
    assert p["P"] == pytest.approx(95.0)
    assert p["R1"] == pytest.approx(100.0) and p["S1"] == pytest.approx(90.0)
    assert p["R2"] == pytest.approx(105.0) and p["S2"] == pytest.approx(85.0)
    # R3 = H + 2(P-L) — live.py's convention, NOT the vendor CSV's P + 2(H-L).
    assert p["R3"] == pytest.approx(110.0) and p["S3"] == pytest.approx(80.0)


def test_opt_pivots_math_absence_and_cache(monkeypatch):
    calls = {"n": 0}

    def fake_intraday(tok, sec_id, instrument, day, oi=False, seg="NSE_FNO"):
        calls["n"] += 1
        if sec_id == "1001":               # CE traded yesterday
            return {"high": [104.0, 110.0], "low": [92.0, 95.0],
                    "close": [100.0, 101.0]}
        return {}                          # PE has no prior session

    monkeypatch.setattr(live, "_intraday", fake_intraday)
    monkeypatch.setattr(live.time, "sleep", lambda s: None)
    live._opt_piv_cache.clear()
    cfg = {"under_sym": "NIFTY", "expiry": "2026-07-28",
           "prev_day": "2026-07-27", "fut_seg": "NSE_FNO"}
    ids = {"CE": "1001", "PE": "1002"}

    out = live._opt_pivots("tok", cfg, 23850.0, ids)
    # CE: pivots from ITS OWN H/L/C, receipts included.
    assert out["ce"]["H"] == 110.0 and out["ce"]["L"] == 92.0 and out["ce"]["C"] == 101.0
    assert out["ce"]["P"] == pytest.approx((110.0 + 92.0 + 101.0) / 3.0)
    assert out["why"]["ce"] is None
    # PE: absent leg is None WITH a reason — never invented.
    assert out["pe"] is None and "no prior session" in out["why"]["pe"]
    # Cache: a second call fetches nothing new (yesterday cannot change).
    n = calls["n"]
    again = live._opt_pivots("tok", cfg, 23850.0, ids)
    assert calls["n"] == n and again["ce"] == out["ce"]
