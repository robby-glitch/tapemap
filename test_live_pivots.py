"""live._pivots on an empty prior session: a stated absence, never a crash.
2026-09-07 to 09-15 this raised ValueError on max([]) inside build_session,
which killed both zone machines, trigger_log and the gear reading -- silently."""
import live


def _cfg():
    return {"under_sym": "NIFTY", "prev_day": "2026-09-14", "fut_id": "1",
            "fut_seg": "NSE_FNO"}


def test_empty_prior_session_yields_none_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(live, "_intraday", lambda *a, **k: {"high": [], "low": [], "close": []})
    live._piv_cache.clear()
    assert live._pivots("tok", _cfg()) is None
    assert ("NIFTY", "2026-09-14") not in live._piv_cache   # a later fetch may still land


def test_bars_without_pivots_carry_bands_and_no_pivot_keys():
    d = {"timestamp": [1757907900, 1757907960], "open": [100.0, 101.0], "high": [101.0, 102.0],
         "low": [99.0, 100.0], "close": [100.5, 101.5], "volume": [10, 12]}
    bars = live._bars(d, None)
    assert len(bars) == 2 and "VWAP" in bars[0] and "D2" in bars[0]
    assert "R1" not in bars[0] and "P" not in bars[0]
