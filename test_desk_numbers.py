"""Realized vol, the number the rebuilt DESK screen had to declare as missing.

`server._rv5` reads it off the tool's own captured bars; these pin its method
and its stated absences.
"""

import json
import math


# ---- realized vol ----------------------------------------------------------

def _write_session(d, day, closes):
    (d / f"fut_{day}.json").write_text(
        json.dumps({"close": closes, "timestamp": list(range(len(closes)))}),
        encoding="utf-8")


def test_rv5_is_computed_from_the_last_close_of_each_cached_session(
        tmp_path, monkeypatch):
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    d = tmp_path / "data" / "backtest"
    d.mkdir(parents=True)
    closes = [24000.0, 24120.0, 24000.0, 24180.0, 23980.0, 24100.0]
    for i, c in enumerate(closes):
        _write_session(d, f"2026-08-{10 + i:02d}", [c - 5, c])
    rv, why = server._rv5("NIFTY")
    assert why is None and rv["tag"] == "M"
    assert rv["sessions"] == 6 and rv["n_returns"] == 5

    rets = [math.log(b / a) for a, b in zip(closes, closes[1:])]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    assert rv["rv"] == round(math.sqrt(var) * math.sqrt(252.0), 4)


def test_too_few_sessions_is_a_reason_not_a_number(tmp_path, monkeypatch):
    """A vol printed off two sessions is noise wearing a number's clothes."""
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    d = tmp_path / "data" / "backtest"
    d.mkdir(parents=True)
    _write_session(d, "2026-08-10", [24000.0])
    _write_session(d, "2026-08-11", [24100.0])
    rv, why = server._rv5("NIFTY")
    assert rv is None and "need at least" in why


def test_a_missing_cache_says_so_rather_than_returning_zero(tmp_path,
                                                            monkeypatch):
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    rv, why = server._rv5("BANKNIFTY")
    assert rv is None and why


def test_the_other_indices_are_read_from_their_own_subdirectory(tmp_path,
                                                                monkeypatch):
    """NIFTY sits at the top level of data/backtest/; BANKNIFTY and SENSEX
    under their own folders. Reading the wrong one would quietly report
    NIFTY's vol under another index's name."""
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    d = tmp_path / "data" / "backtest" / "BANKNIFTY"
    d.mkdir(parents=True)
    for i, c in enumerate([52000.0, 52400.0, 52100.0, 52600.0, 52200.0,
                           52500.0]):
        _write_session(d, f"2026-08-{10 + i:02d}", [c])
    rv, why = server._rv5("BANKNIFTY")
    assert why is None and rv["sessions"] == 6


def test_a_corrupt_capture_is_skipped_not_zero_filled(tmp_path, monkeypatch):
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    d = tmp_path / "data" / "backtest"
    d.mkdir(parents=True)
    for i, c in enumerate([24000.0, 24120.0, 24000.0, 24180.0, 23980.0]):
        _write_session(d, f"2026-08-{10 + i:02d}", [c])
    (d / "fut_2026-08-20.json").write_text("{not json", encoding="utf-8")
    rv, why = server._rv5("NIFTY")
    # five good sessions remain -> four returns, still publishable
    assert why is None and rv["n_returns"] == 4


def test_the_annualization_basis_travels_with_the_number(tmp_path,
                                                          monkeypatch):
    """252 trading days here vs 365 calendar in T. Comparing RV to IV is the
    whole point of having this, so the mismatch must not be silent."""
    import server
    monkeypatch.setattr(server, "ROOT", tmp_path)
    d = tmp_path / "data" / "backtest"
    d.mkdir(parents=True)
    for i, c in enumerate([24000.0, 24120.0, 24000.0, 24180.0, 23980.0,
                           24100.0]):
        _write_session(d, f"2026-08-{10 + i:02d}", [c])
    rv, _ = server._rv5("NIFTY")
    assert "252" in rv["basis_note"] and "365" in rv["basis_note"]
