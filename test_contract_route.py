"""`/api/contract` assembly -- live.py's session walk, leg builder, params.

Everything here runs with an INJECTED fetch: no token, no network, no clock
dependence. The live numbers (bar counts, first closes, first OI) are checked
against the raw Dhan response separately -- see .superpowers/sdd/task-4-report.md.

Families:
  1. Session walk       -- N sessions oldest-first, weekends skipped, a
                           weekend request snaps back to a day that traded.
  2. Alignment          -- bars / vwap / oi / bar_days are 1:1 by index.
  3. VWAP resets daily  -- session 2's first bar carries session 2's own
                           anchor, never session 1's cumulative volume.
  4. Gaps               -- an empty session and a failing fetch are BOTH
                           listed, with reasons that distinguish them, and
                           nothing is interpolated across the hole.
  5. Interval sampling  -- resampling never moves a band (spec invariant 6).
  6. forming            -- always null, always with a stated reason.
  7. Param validation   -- a bad side is a hard error, before any I/O.
"""

from datetime import datetime, timedelta, timezone

import pytest

import contract_bars
import live

IST = timezone(timedelta(hours=5, minutes=30))


def _payload(day, n=5, base=100.0, vol=10.0, oi0=500000):
    """A synthetic rest_intraday response: n 1-min bars from 09:15 IST."""
    t0 = datetime.strptime(day, "%Y-%m-%d").replace(
        hour=9, minute=15, tzinfo=IST).timestamp()
    return {
        "open": [base + i for i in range(n)],
        "high": [base + i + 2 for i in range(n)],
        "low": [base + i - 1 for i in range(n)],
        "close": [base + i + 1 for i in range(n)],
        "volume": [vol * (i + 1) for i in range(n)],
        "open_interest": [oi0 + 100 * i for i in range(n)],
        "timestamp": [t0 + 60 * i for i in range(n)],
    }


# ---- 1. session walk -------------------------------------------------------

def test_sessions_back_is_oldest_first_and_skips_weekends():
    # 2026-07-30 is a Thursday; walking back 4 must skip Sat 25 / Sun 26.
    assert live._sessions_back("2026-07-30", 4) == [
        "2026-07-27", "2026-07-28", "2026-07-29", "2026-07-30"]


def test_sessions_back_single_day_is_the_day_itself():
    assert live._sessions_back("2026-07-30", 1) == ["2026-07-30"]


def test_sessions_back_from_a_weekend_snaps_to_a_trading_day():
    # 2026-08-01 is a Saturday: the session that actually traded is Friday.
    assert live._sessions_back("2026-08-01", 1) == ["2026-07-31"]


# ---- 2/3. alignment and the per-session VWAP anchor ------------------------

def test_arrays_are_aligned_one_to_one_and_dated():
    sess = ["2026-07-29", "2026-07-30"]
    leg = live._leg_series(lambda d: _payload(d, n=5), sess, 1)
    n = len(leg["bars"])
    assert n == 10
    assert len(leg["vwap"]) == n
    assert len(leg["oi"]) == n
    assert len(leg["bar_days"]) == n
    assert leg["bar_days"] == ["2026-07-29"] * 5 + ["2026-07-30"] * 5
    assert set(leg["bars"][0]) == set(contract_bars.BAR_KEYS)
    assert set(leg["vwap"][0]) == set(contract_bars.BAND_KEYS)
    assert leg["oi"][0] == leg["bars"][0]["oi"]
    assert leg["gaps"] == []


def test_vwap_is_re_anchored_every_session():
    sess = ["2026-07-29", "2026-07-30"]
    # session 2 sits at a completely different price level; if the VWAP leaked
    # across the day boundary its first bar could not equal its own typical price
    leg = live._leg_series(
        lambda d: _payload(d, n=5, base=100.0 if d == sess[0] else 900.0),
        sess, 1)
    first_of_day2 = leg["bars"][5]
    tp = (first_of_day2["h"] + first_of_day2["l"] + first_of_day2["c"]) / 3.0
    assert leg["vwap"][5]["vwap"] == pytest.approx(tp)
    # and it is NOT the continuation of session 1
    assert leg["vwap"][5]["vwap"] != pytest.approx(leg["vwap"][4]["vwap"])


# ---- 3b. Dhan's over-fetch: a one-day request can return two sessions ------

def _two_sessions(day_a, day_b, n=4):
    """One payload carrying two trading days back to back -- what Dhan really
    returns for an older `day` once toDate is sent as day + 1 (measured
    2026-07-31: fromDate 07-28 / toDate 07-29 -> 750 bars across BOTH days)."""
    a, b = _payload(day_a, n=n, base=100.0), _payload(day_b, n=n, base=900.0)
    return {k: list(a[k]) + list(b[k]) for k in a}


def test_over_fetched_next_session_is_filtered_out():
    raw = _two_sessions("2026-07-28", "2026-07-29")
    leg = live._leg_series(lambda d: raw, ["2026-07-28"], 1)
    assert len(leg["bars"]) == 4                 # NOT 8: the 29th is not ours
    assert set(leg["bar_days"]) == {"2026-07-28"}
    # the over-fetch is reported, not silently dropped
    assert leg["served_by_request"]["2026-07-28"] == {"2026-07-28": 4,
                                                      "2026-07-29": 4}


def test_over_fetch_does_not_leak_into_the_next_sessions_vwap():
    raw = _two_sessions("2026-07-28", "2026-07-29")
    leg = live._leg_series(lambda d: raw, ["2026-07-28", "2026-07-29"], 1)
    assert leg["bar_days"] == ["2026-07-28"] * 4 + ["2026-07-29"] * 4
    # each session re-anchors: its first bar's VWAP is its own typical price
    for i in (0, 4):
        b = leg["bars"][i]
        assert leg["vwap"][i]["vwap"] == pytest.approx(
            (b["h"] + b["l"] + b["c"]) / 3.0)


def test_one_session_reports_what_dhan_served_and_what_was_lost():
    raw = _two_sessions("2026-07-28", "2026-07-29", n=3)
    mine, served, lost = live._one_session(raw, "2026-07-29")
    assert served == {"2026-07-28": 3, "2026-07-29": 3}
    assert lost == 0
    assert len(mine["close"]) == 3
    assert mine["close"] == raw["close"][3:]


def test_one_session_counts_ragged_and_unreadable_rows_as_lost():
    raw = _payload("2026-07-30", n=4)
    raw["volume"] = raw["volume"][:3]            # ragged feed: one row short
    raw["timestamp"][0] = "not-an-instant"       # unplaceable in any session
    mine, served, lost = live._one_session(raw, "2026-07-30")
    assert served == {"2026-07-30": 2}
    assert lost == 2                             # 1 ragged + 1 bad timestamp
    assert len(mine["close"]) == 2


def test_a_session_dhan_never_served_is_a_gap_even_when_bars_came_back():
    # asking for the 29th but being handed only the 28th must NOT silently
    # relabel the 28th's bars as the 29th's
    raw = _payload("2026-07-28", n=5)
    leg = live._leg_series(lambda d: raw, ["2026-07-29"], 1)
    assert leg["bars"] == []
    assert leg["gaps"] == ["2026-07-29"]
    assert "2026-07-28" in leg["gap_reasons"]["2026-07-29"]


# ---- 4. gaps ---------------------------------------------------------------

def test_empty_session_is_a_gap_and_nothing_is_interpolated():
    sess = ["2026-07-29", "2026-07-30"]

    def fetch(d):
        return {} if d == "2026-07-29" else _payload(d, n=5)

    leg = live._leg_series(fetch, sess, 1)
    assert leg["gaps"] == ["2026-07-29"]
    assert len(leg["bars"]) == 5                 # only the session that had bars
    assert set(leg["bar_days"]) == {"2026-07-30"}
    assert "no usable bars" in leg["gap_reasons"]["2026-07-29"]
    assert "rolling-ATM" in leg["gap_reasons"]["2026-07-29"]


def test_failing_fetch_is_a_gap_with_a_different_reason():
    sess = ["2026-07-29", "2026-07-30"]

    def fetch(d):
        if d == "2026-07-29":
            raise TimeoutError("no response in 25s")
        return _payload(d, n=3)

    leg = live._leg_series(fetch, sess, 1)
    assert leg["gaps"] == ["2026-07-29"]
    # an error is a different fact about the world than an empty session
    assert leg["gap_reasons"]["2026-07-29"].startswith("fetch failed:")
    assert "TimeoutError" in leg["gap_reasons"]["2026-07-29"]
    assert len(leg["bars"]) == 3


def test_every_session_empty_yields_no_bars_and_all_gaps():
    sess = ["2026-07-29", "2026-07-30"]
    leg = live._leg_series(lambda d: {}, sess, 1)
    assert leg["bars"] == [] and leg["vwap"] == [] and leg["oi"] == []
    assert leg["gaps"] == sess


# ---- 5. interval sampling never moves a band -------------------------------

def test_resampling_samples_the_bands_it_does_not_recompute_them():
    sess = ["2026-07-30"]
    one = live._leg_series(lambda d: _payload(d, n=6), sess, 1)
    three = live._leg_series(lambda d: _payload(d, n=6), sess, 3)
    assert len(three["bars"]) == 2
    # each 3-min bucket carries the bands of its LAST 1-minute bar, verbatim
    for j, i in enumerate((2, 5)):
        assert three["vwap"][j] == one["vwap"][i]


# ---- 6/7. forming, and param validation before any I/O ---------------------

def test_forming_is_null_and_says_why():
    leg = live._leg_series(lambda d: _payload(d, n=2), ["2026-07-30"], 1)
    assert leg["forming"] is None
    assert "ChainPoller" in leg["forming_why"]
    assert "never synthesised" in leg["forming_why"]


def test_bad_side_is_rejected_before_any_network_call():
    with pytest.raises(ValueError, match="side must be CE, PE or BOTH"):
        live.build_contract("NIFTY", side="CALL",
                            fetch=lambda sec_id, d: _payload(d))
