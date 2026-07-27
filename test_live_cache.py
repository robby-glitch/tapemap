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
