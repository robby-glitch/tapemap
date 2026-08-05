"""The cache must not thrash, and SENSEX must not be looked for on the NSE.

Both of these were real: the first version cached to ONE file holding whatever
index was asked for last, so with three indices enabled every rotation evicted
the previous one and re-downloaded a dump -- the 2026-07-27 frozen-tape failure
mode rebuilt. And SENSEX was looked up in the NSE dump, where it does not
exist, which is what took the live SENSEX build down on 2026-08-05.

No network: `fetch` is injected everywhere.
"""

import json

import pytest

import upstox_instruments as ui

DAY_MS = 86_400_000
FUTURE = 4_102_444_800_000                        # 2100-01-01, always ahead


def _dump(exch, name, fut_type):
    """A dump with one index row, one future and two strikes x CE/PE."""
    seg = f"{exch}_FO"
    rows = [{"segment": f"{exch}_INDEX", "trading_symbol": name,
             "name": name, "instrument_key": f"{exch}_INDEX|{name}"},
            {"segment": seg, "name": name, "instrument_type": fut_type,
             "instrument_key": f"{seg}|FUT", "expiry": FUTURE + DAY_MS,
             "strike_price": None, "trading_symbol": f"{name} FUT"},
            # noise the filter must drop
            {"segment": seg, "name": "SOMETHINGELSE", "instrument_type": "CE",
             "instrument_key": f"{seg}|NOISE", "expiry": FUTURE,
             "strike_price": 100.0, "trading_symbol": "NOISE"}]
    for k in (100.0, 200.0):
        for side in ("CE", "PE"):
            rows.append({"segment": seg, "name": name, "instrument_type": side,
                         "instrument_key": f"{seg}|{int(k)}{side}",
                         "expiry": FUTURE, "strike_price": k,
                         "trading_symbol": f"{name} {int(k)} {side}"})
    return rows


@pytest.fixture
def cached(tmp_path, monkeypatch):
    """Point the cache at tmp_path and count fetches per exchange."""
    monkeypatch.setattr(ui, "CACHE_FMT", str(tmp_path / "upstox_{}.json"))
    calls = []

    def fetch(exch):
        calls.append(exch)
        name = {"NSE": "NIFTY", "BSE": "SENSEX"}[exch]
        fut = "FUTIDX" if exch == "NSE" else "FUT"
        return _dump(exch, name, fut)

    return calls, fetch


def test_a_second_index_does_not_evict_the_first(cached, monkeypatch):
    """The thrash. Two indices, then both again: four loads, two fetches."""
    calls, fetch = cached
    monkeypatch.setattr(ui, "INDEX_SYMBOL", {"NIFTY": "nifty", "SENSEX": "sensex"})
    ui.load("NIFTY", fetch=fetch)
    ui.load("SENSEX", fetch=fetch)
    ui.load("NIFTY", fetch=fetch)
    ui.load("SENSEX", fetch=fetch)
    assert calls == ["NSE", "BSE"], "a dump was re-downloaded"


def test_each_index_gets_its_own_cache_file(cached, tmp_path, monkeypatch):
    calls, fetch = cached
    monkeypatch.setattr(ui, "INDEX_SYMBOL", {"NIFTY": "nifty", "SENSEX": "sensex"})
    ui.load("NIFTY", fetch=fetch)
    ui.load("SENSEX", fetch=fetch)
    names = sorted(p.name for p in tmp_path.glob("upstox_*.json"))
    assert names == ["upstox_nifty.json", "upstox_sensex.json"]
    blob = json.loads((tmp_path / "upstox_sensex.json").read_text())
    assert blob["name"] == "SENSEX"
    assert all(r["instrument_key"].startswith("BSE_FO|") for r in blob["rows"])


def test_sensex_is_read_from_the_bse_dump(cached, monkeypatch):
    """The live failure: SENSEX has no rows in the NSE dump at all."""
    calls, fetch = cached
    monkeypatch.setattr(ui, "INDEX_SYMBOL", {"SENSEX": "sensex"})
    assert ui.exchange("SENSEX") == "BSE"
    ui.load("SENSEX", fetch=fetch)
    assert calls == ["BSE"]


def test_the_bse_future_is_typed_FUT_not_FUTIDX(cached, monkeypatch):
    """NSE says FUTIDX, BSE says FUT. Accepting one spelling loses an index."""
    calls, fetch = cached
    monkeypatch.setattr(ui, "INDEX_SYMBOL", {"SENSEX": "sensex"})
    assert ui.fut_key("SENSEX", rows=ui.load("SENSEX", fetch=fetch)) == "BSE_FO|FUT"


def test_the_index_key_is_looked_up_not_guessed(cached, monkeypatch):
    calls, fetch = cached
    monkeypatch.setattr(ui, "INDEX_SYMBOL", {"NIFTY": "nifty", "SENSEX": "sensex"})
    assert ui.index_key("NIFTY", fetch=fetch) == "NSE_INDEX|NIFTY"
    assert ui.index_key("SENSEX", fetch=fetch) == "BSE_INDEX|SENSEX"


def test_a_renamed_index_row_fails_loudly(cached, monkeypatch):
    """A guessed key would subscribe fine and simply never tick."""
    calls, fetch = cached
    monkeypatch.setattr(ui, "INDEX_SYMBOL", {"NIFTY": "no such index"})
    with pytest.raises(RuntimeError, match="no NSE_INDEX row"):
        ui.index_key("NIFTY", fetch=fetch)


def test_an_unmapped_index_is_named_in_the_error():
    with pytest.raises(RuntimeError, match="no Upstox exchange mapped"):
        ui.exchange("MIDCPNIFTY")


def test_foreign_rows_are_not_cached(cached, monkeypatch):
    calls, fetch = cached
    monkeypatch.setattr(ui, "INDEX_SYMBOL", {"NIFTY": "nifty"})
    rows = ui.load("NIFTY", fetch=fetch)
    assert all("NOISE" not in r["instrument_key"] for r in rows)
    assert len(rows) == 5                         # 1 future + 2 strikes x CE/PE


def test_option_keys_returns_both_legs_or_raises(cached, monkeypatch):
    calls, fetch = cached
    monkeypatch.setattr(ui, "INDEX_SYMBOL", {"NIFTY": "nifty"})
    rows = ui.load("NIFTY", fetch=fetch)
    assert ui.option_keys(100.0, "NIFTY", rows=rows) == {
        "CE": "NSE_FO|100CE", "PE": "NSE_FO|100PE"}
    with pytest.raises(RuntimeError, match="not listed"):
        ui.option_keys(999.0, "NIFTY", rows=rows)
