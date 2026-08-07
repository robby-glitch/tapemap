"""Rebuilding a morning must not invent one.

Every case injects `fetch`, so nothing here touches the network or a token.
The rules being pinned are the ones that would fail SILENTLY if broken: a
wrong baseline shifts every row without raising, a missing side written as 0.0
reads as "flat" rather than "not observed", and a reconstruction that
overwrote a recorded mark would replace an observation with a guess.

Live agreement is measured against the socket's own recording rather than
asserted here: 2026-08-07, 122 overlapping marks, per-strike oi_chg exact on
82% of values, and the AGGREGATE the table actually shows within a median
1.45% -- the same order as the 1-2% `oi_flow` already documents against the
reference tool it was reverse-engineered from.
"""

import chain_backfill as cb


def _candles(rows, day="2026-08-07"):
    """What `upstox_rest.intraday` actually returns: a bare list of
    `[iso_ts, o, h, l, c, volume, open_interest]`, NEWEST FIRST. `rows` is
    given oldest-first for readability and reversed here, so a test reads in
    session order while the fixture stays wire-accurate."""
    return [[f"{day}T{t}:00+05:30", c, c, c, c, 0, oi]
            for t, c, oi in reversed(rows)]


def _fetch_of(by_key):
    def fetch(key, _tok):
        return by_key.get(key, [])
    return fetch


# ---- baseline ---------------------------------------------------------------

def test_the_baseline_is_the_days_first_candle():
    """`oi_chg` means "since the open" on the live path too, so this anchor is
    the whole comparison. Off by one candle shifts every row and raises
    nothing."""
    fetch = _fetch_of({"K": _candles([("09:15", 100.0, 1000),
                                      ("09:16", 101.0, 1500),
                                      ("09:17", 102.0, 1200)])})
    hist, base = cb._minute_oi("K", "tok", fetch)
    assert base == 1000
    assert hist == {"09:15": 1000.0, "09:16": 1500.0, "09:17": 1200.0}


def test_an_instrument_that_served_nothing_is_not_an_error():
    """A strike that never traded is a real answer, not a failure."""
    assert cb._minute_oi("K", "tok", _fetch_of({})) == ({}, None)


# ---- the grid ---------------------------------------------------------------

def _keys_of(_k):
    return {"CE": "24000CE", "PE": "24000PE"}


def _grid(monkeypatch, fetch, strikes=(24000,)):
    monkeypatch.setattr(cb, "_spot_series",
                        lambda i, t, f=None: {"09:15": 24000.0, "09:16": 24010.0})
    return cb.minute_grid("NIFTY", list(strikes), "tok", gap_s=0,
                          fetch=fetch, keys_of=_keys_of)


def _both_sides():
    return _fetch_of({
        "24000CE": _candles([("09:15", 10.0, 1000), ("09:16", 11.0, 1600)]),
        "24000PE": _candles([("09:15", 20.0, 2000), ("09:16", 21.0, 1700)]),
    })


def test_change_is_measured_from_the_open_not_the_previous_mark(monkeypatch):
    g = _grid(monkeypatch, _both_sides())
    assert g["09:15"]["k"][24000] == (0.0, 0.0)        # the open is its own zero
    assert g["09:16"]["k"][24000] == (600.0, -300.0)


def test_spot_rides_along(monkeypatch):
    assert _grid(monkeypatch, _both_sides())["09:16"]["spot"] == 24010.0


def test_a_mark_missing_one_side_is_dropped_not_zero_filled(monkeypatch):
    """The bug this caught against live data on 2026-08-07. A side with no
    candle written as 0.0 claims "no change"; the truth is "not observed" --
    and `oi_flow` SUMS the row, so a partial mark shows a dip that never
    happened."""
    fetch = _fetch_of({
        "24000CE": _candles([("09:15", 10.0, 1000), ("09:16", 11.0, 1600)]),
        "24000PE": _candles([("09:15", 20.0, 2000)]),          # no 09:16
    })
    g = _grid(monkeypatch, fetch)
    assert "09:15" in g and "09:16" not in g


def test_a_strike_with_no_baseline_drops_the_mark(monkeypatch):
    fetch = _fetch_of({
        "24000CE": _candles([("09:15", 10.0, 1000)]),
        "24000PE": {"data": {"candles": []}},
    })
    assert _grid(monkeypatch, fetch) == {}


# ---- merging into a live state ---------------------------------------------

class _State:
    def __init__(self, minutes=None):
        self.minutes = dict(minutes or {})


def test_a_recorded_mark_is_never_overwritten(monkeypatch):
    """An observation always beats a reconstruction. The socket saw what it
    saw; this is rebuilt from candles and yields to it."""
    monkeypatch.setattr(cb, "minute_grid",
                        lambda *a, **k: {"09:15": {"spot": 1.0, "k": {1: (9, 9)}}})
    st = _State({"09:15": {"spot": 999.0, "k": {1: (1, 1)}}})
    assert cb.backfill_minutes(st, "NIFTY", [1], "tok", before=None) == 0
    assert st.minutes["09:15"]["spot"] == 999.0


def test_nothing_at_or_after_the_first_recorded_mark_is_written(monkeypatch):
    monkeypatch.setattr(cb, "minute_grid", lambda *a, **k: {
        "09:15": {"spot": 1.0, "k": {1: (1, 1)}},
        "12:38": {"spot": 2.0, "k": {1: (2, 2)}},
        "12:39": {"spot": 3.0, "k": {1: (3, 3)}},
    })
    st = _State()
    assert cb.backfill_minutes(st, "NIFTY", [1], "tok", before="12:38") == 1
    assert sorted(st.minutes) == ["09:15"]


def test_with_no_recorded_marks_everything_is_fair_game(monkeypatch):
    monkeypatch.setattr(cb, "minute_grid", lambda *a, **k: {
        "09:15": {"spot": 1.0, "k": {1: (1, 1)}},
        "09:16": {"spot": 2.0, "k": {1: (2, 2)}},
    })
    assert cb.backfill_minutes(_State(), "NIFTY", [1], "tok", before=None) == 2


# ---- the poller's side of the hook -----------------------------------------

def test_the_poller_does_not_backfill_on_dhan(monkeypatch):
    """Dhan's REST does not serve per-strike option OI history in this shape.
    Half a morning is worse than none, so that path declines outright."""
    import chain_live
    monkeypatch.setattr(chain_live, "_broker", lambda: "dhan")
    called = []
    monkeypatch.setattr(cb, "start_backfill", lambda *a, **k: called.append(a))
    p = chain_live.ChainPoller.__new__(chain_live.ChainPoller)
    p.states = {"NIFTY": _State()}
    p._kick_backfill("NIFTY", {"strikes": [{"k": 1}]})
    assert called == []


def test_a_broken_backfill_never_takes_the_poller_down(monkeypatch):
    """A missing morning is worse than no morning; both are far better than a
    chain poller that will not start."""
    import chain_live
    monkeypatch.setattr(chain_live, "_broker", lambda: "upstox")
    monkeypatch.setattr(cb, "start_backfill",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    p = chain_live.ChainPoller.__new__(chain_live.ChainPoller)
    p.states = {"NIFTY": _State()}
    p._kick_backfill("NIFTY", {"strikes": [{"k": 1}]})   # must not raise
