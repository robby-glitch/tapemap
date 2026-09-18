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
    hist, base, _px = cb._minute_leg("K", "tok", fetch)
    assert base == 1000
    assert hist == {"09:15": 1000.0, "09:16": 1500.0, "09:17": 1200.0}


def test_premium_rides_off_the_same_candle_as_the_oi():
    """The UI's OI x premium paint needs both axes, and the candle already
    carries both -- so the premium half costs no extra request and no extra
    rate-limit budget. A LEVEL, not a change from the open: `k` is a change
    because the live chain publishes `oi_chg`, and there is no such convention
    for premium."""
    fetch = _fetch_of({"K": _candles([("09:15", 41.25, 1000),
                                      ("09:16", 55.80, 1500)])})
    _hist, _base, px = cb._minute_leg("K", "tok", fetch)
    assert px == {"09:15": 41.25, "09:16": 55.80}


def test_an_instrument_that_served_nothing_is_not_an_error():
    """A strike that never traded is a real answer, not a failure."""
    assert cb._minute_leg("K", "tok", _fetch_of({})) == ({}, None, {})


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


def test_the_rebuilt_grid_carries_premium_per_strike(monkeypatch):
    """The point of the whole follow-up: after a late start the UI can compute
    OI-change AND premium-change per window for the morning, so the 4-state
    paint fills instead of staying half-blind."""
    g = _grid(monkeypatch, _both_sides())
    assert g["09:15"]["px"][24000] == (10.0, 20.0)
    assert g["09:16"]["px"][24000] == (11.0, 21.0)


def test_premium_and_oi_always_cover_the_same_marks(monkeypatch):
    """They come off the SAME candle, and `candles_to_arrays` drops any row
    whose OHLC will not parse -- so a row cannot contribute OI without also
    contributing a close. That is why premium does not gate the mark: it
    cannot be the thing that is missing.

    Pinned because the alternative was believed and tested for on the way
    here: a fixture with a null close looks like "OI but no premium" and is
    actually a row that never reaches either series. The `.get(m)` in
    `minute_grid` stays as the honest shape if that ever changes -- a None
    there would mean "not observed", never a zero premium.
    """
    g = _grid(monkeypatch, _both_sides())
    for m, rec in g.items():
        assert set(rec["px"]) == set(rec["k"]), m
        assert all(None not in pair for pair in rec["px"].values()), m


def test_a_leg_that_serves_nothing_still_drops_the_whole_mark(monkeypatch):
    """The OI rule is unchanged by premium riding along: `oi_flow` SUMS the
    row, so a mark missing one strike shows a dip that never happened."""
    fetch = _fetch_of({
        "24000CE": _candles([("09:15", 10.0, 1000), ("09:16", 11.0, 1600)]),
        "24000PE": _candles([("09:15", 20.0, 2000)]),          # no 09:16
    })
    g = _grid(monkeypatch, fetch)
    assert "09:16" not in g


def test_every_rebuilt_mark_says_it_was_rebuilt(monkeypatch):
    """The non-negotiable: backfilled data stays distinguishable from
    live-observed data end to end. `src` travels WITH the mark rather than in
    a parallel structure, because a parallel structure is somewhere for two
    truths to drift apart."""
    g = _grid(monkeypatch, _both_sides())
    assert all(rec["src"] == "backfill" for rec in g.values())


def test_the_live_writer_sets_no_src_so_absent_means_observed():
    """`ChainState.update` is the socket's own path. If it ever started
    writing a `src`, "absent means observed" would quietly stop being true and
    every backfilled row would read as live."""
    import inspect

    from chain_metrics import ChainState
    body = inspect.getsource(ChainState.update)
    assert '"src"' not in body and "'src'" not in body


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


def test_the_flag_reaches_the_trending_oi_rows(monkeypatch):
    """End to end: a mark rebuilt from candles must be readable AS rebuilt on
    the row a screen renders. The morning of a server started at 11:00 is
    worth having and is not the same evidence as an observation -- REST
    candles carry no IV, no greeks and nothing gamma-weighted."""
    from chain_metrics import ChainState
    st = ChainState()
    st.minutes = {
        "09:15": {"spot": 24000.0, "k": {24000: (0.0, 0.0)}, "src": "backfill"},
        "09:30": {"spot": 24050.0, "k": {24000: (500.0, -200.0)},
                  "src": "backfill"},
        "11:00": {"spot": 24100.0, "k": {24000: (900.0, -100.0)}},
    }
    rows = {r["time"]: r for r in st.oi_flow(interval=15)}
    assert rows["09:30"]["backfill"] is True
    assert rows["11:00"]["backfill"] is False


def test_premium_reaches_the_rows_for_the_selected_strikes():
    """What the UI joins on: `row.time` + `row.px[strike]`, differenced across
    rows for premium change per window -- the same rows that already carry
    `backfill`, so both axes of a mark are always one population."""
    from chain_metrics import ChainState
    st = ChainState()
    st.minutes = {
        "09:15": {"spot": 24000.0, "k": {24000: (0.0, 0.0), 24200: (0.0, 0.0)},
                  "px": {24000: (41.25, 88.6), 24200: (12.0, 150.0)},
                  "src": "backfill"},
        "09:30": {"spot": 24050.0, "k": {24000: (500.0, -200.0),
                                         24200: (900.0, -50.0)},
                  "px": {24000: (55.8, 70.1), 24200: (18.4, 132.0)},
                  "src": "backfill"},
    }
    rows = {r["time"]: r for r in st.oi_flow(interval=15, strikes=[24000])}
    assert rows["09:30"]["px"] == {24000: (55.8, 70.1)}   # selection only
    assert rows["09:30"]["backfill"] is True
    # premium CHANGE is the caller's subtraction over its own window
    assert round(rows["09:30"]["px"][24000][0]
                 - rows["09:15"]["px"][24000][0], 2) == 14.55


def test_a_book_wide_call_ships_no_per_strike_premium():
    """A premium sum across strikes is not a quantity, and the whole chain
    would be ~180KB per poll. Empty, and the endpoint says why."""
    from chain_metrics import ChainState
    st = ChainState()
    st.minutes = {"09:15": {"spot": 24000.0, "k": {24000: (0.0, 0.0)},
                            "px": {24000: (41.25, 88.6)}},
                  "09:30": {"spot": 24050.0, "k": {24000: (500.0, -200.0)},
                            "px": {24000: (55.8, 70.1)}}}
    assert all(r["px"] == {} for r in st.oi_flow(interval=15))


def test_a_mark_written_before_premium_existed_does_not_raise():
    """`_warm_start` replays this tool's own persisted snapshots, and a
    restart mid-upgrade can hand `oi_flow` a mark with no `px` key at all.
    Absent must read as empty, never as a KeyError that takes the table
    down."""
    from chain_metrics import ChainState
    st = ChainState()
    st.minutes = {"09:15": {"spot": 24000.0, "k": {24000: (0.0, 0.0)}},
                  "09:30": {"spot": 24050.0, "k": {24000: (500.0, -200.0)}}}
    assert [r["px"] for r in st.oi_flow(interval=15, strikes=[24000])] == [{}, {}]


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


def test_a_hole_in_the_middle_of_the_day_is_filled(monkeypatch):
    """2026-09-18: the server was down 10:59-13:13, so the poller recorded
    09:50 and 13:13 with nothing between. The caller passed the FIRST recorded
    mark as the cutoff, so every REST minute at or after 09:50 was skipped and
    the hole stayed empty. With the cutoff at NOW instead, the hole fills and
    the two observations are still not clobbered."""
    monkeypatch.setattr(cb, "minute_grid", lambda *a, **k: {
        "09:50": {"spot": 1.0, "k": {1: (9, 9)}},     # observed - must not move
        "11:00": {"spot": 2.0, "k": {1: (2, 2)}},     # the hole
        "12:00": {"spot": 3.0, "k": {1: (3, 3)}},     # the hole
        "13:13": {"spot": 4.0, "k": {1: (9, 9)}},     # observed - must not move
        "14:30": {"spot": 5.0, "k": {1: (5, 5)}},     # at/after now - left alone
    })
    st = _State()
    st.minutes["09:50"] = {"spot": 1.5, "k": {1: (1, 1)}}
    st.minutes["13:13"] = {"spot": 4.5, "k": {1: (4, 4)}}
    assert cb.backfill_minutes(st, "NIFTY", [1], "tok", before="14:30") == 2
    assert sorted(st.minutes) == ["09:50", "11:00", "12:00", "13:13"]
    assert st.minutes["09:50"]["spot"] == 1.5      # observation untouched
    assert st.minutes["13:13"]["spot"] == 4.5
