"""Guards for the Dhan intraday date range and for the per-session slice.

The endpoint's `toDate` has NO single rule. Measured live 2026-07-31 (NIFTY
index, security id 13 / IDX_I), reproducing and correcting the 2026-07-30
measurement::

    07-30 -> 07-30:    0 bars      07-30 -> 07-31:  375 (07-30 only)
    07-29 -> 07-29:  375 bars      07-29 -> 07-30:  375 (07-29 only)
    07-28 -> 07-28:  375 bars      07-28 -> 07-29:  750 (07-28 AND 07-29)
    07-27 -> 07-27:  375 bars      07-27 -> 07-28:  750 (07-27 AND 07-28)

It is EXCLUSIVE for the newest session only -- which is why `day + 1` is the
default -- and INCLUSIVE for older ones, where `day + 1` returns the NEXT
session too. The earlier claim that `fromDate == toDate` always returns zero
bars is false, and believing it is what let `chain()` write two sessions into
one `data/chain_<day>.json`: `_series` labels bars "HH:MM" with no date, so
the second session is invisible in the file and `gex_run.run`'s `{t: j}`
alignment collapses it last-wins, pairing day-1 futures with day-2 option
closes. Hence `_one_session`, and hence the duplicate-timestamp guard.

No network calls: body construction and an injected `fetch`."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import dhan_fetch
from dhan_fetch import _intraday_body, _one_session, _series

IST = timezone(timedelta(hours=5, minutes=30))


def _payload(day, n=4, base=100.0, oi=True):
    """A synthetic rest_intraday response: n 1-min bars from 09:15 IST."""
    t0 = datetime.strptime(day, "%Y-%m-%d").replace(
        hour=9, minute=15, tzinfo=IST).timestamp()
    d = {"open": [base + i for i in range(n)],
         "high": [base + i + 2 for i in range(n)],
         "low": [base + i - 1 for i in range(n)],
         "close": [base + i + 1 for i in range(n)],
         "volume": [10.0 * (i + 1) for i in range(n)],
         "timestamp": [t0 + 60 * i for i in range(n)]}
    if oi:
        d["open_interest"] = [500000 + 100 * i for i in range(n)]
    return d


def _two_sessions(day_a, day_b, n=4, oi=True):
    """What Dhan really returns for an older day: BOTH sessions in one array."""
    a = _payload(day_a, n=n, base=100.0, oi=oi)
    b = _payload(day_b, n=n, base=900.0, oi=oi)
    return {k: list(a[k]) + list(b[k]) for k in a}


def _ids():
    return {k: {"CE": f"CE{k}", "PE": f"PE{k}"}
            for k in dhan_fetch.CHAIN_STRIKES}


def test_to_date_is_day_plus_one():
    body = _intraday_body("65852", "FUTIDX", "2026-07-30", False)
    assert body["fromDate"] == "2026-07-30"
    assert body["toDate"] == "2026-07-31"


def test_to_date_rolls_over_month_boundary():
    body = _intraday_body("65852", "FUTIDX", "2026-07-31", False)
    assert body["fromDate"] == "2026-07-31"
    assert body["toDate"] == "2026-08-01"


def test_to_date_rolls_over_year_boundary():
    body = _intraday_body("65852", "FUTIDX", "2026-12-31", False)
    assert body["fromDate"] == "2026-12-31"
    assert body["toDate"] == "2027-01-01"


def test_oi_passed_through_as_bool():
    body = _intraday_body("65852", "OPTIDX", "2026-07-30", True)
    assert body["oi"] is True
    body = _intraday_body("65852", "OPTIDX", "2026-07-30", False)
    assert body["oi"] is False
    body = _intraday_body("65852", "OPTIDX", "2026-07-30", 1)
    assert body["oi"] is True  # truthy non-bool must still coerce to bool


def test_other_fields_unchanged():
    body = _intraday_body("65852", "FUTIDX", "2026-07-30", False)
    assert body["securityId"] == "65852"
    assert body["exchangeSegment"] == "NSE_FNO"
    assert body["instrument"] == "FUTIDX"
    assert body["interval"] == "1"


def test_to_day_is_settable_for_the_v1_live_path():
    # live._intraday consumes the response whole (build_payload charts the
    # current session, _pivots reads the prior session's H/L/C), so it pins
    # toDate = day rather than over-fetching a second session it never slices.
    body = _intraday_body("13", "FUTIDX", "2026-07-29", True, "NSE_FNO",
                          to_day="2026-07-29")
    assert body["fromDate"] == body["toDate"] == "2026-07-29"


def test_live_and_dhan_fetch_share_one_body_builder_and_one_slicer():
    import live
    assert live._one_session is _one_session
    assert live._intraday_body is _intraday_body


# ---- the per-session slice, and why chain() cannot skip it -----------------

def test_unsliced_two_session_response_hides_duplicates_behind_hhmm():
    # the corruption this guard exists for: 8 bars, only 4 distinct labels,
    # which is exactly what gex_run's {t: j} alignment collapses last-wins.
    s = _series(_two_sessions("2026-07-28", "2026-07-29"))
    assert len(s["t"]) == 8
    assert len(set(s["t"])) == 4


def test_chain_writes_one_session_from_a_two_session_response(tmp_path):
    day, nxt = "2026-07-28", "2026-07-29"
    fut_raw = _two_sessions(day, nxt, oi=False)
    opt_raw = _two_sessions(day, nxt, oi=True)

    def fetch(sec_id, instrument, oi):
        return opt_raw if instrument == "OPTIDX" else fut_raw

    path = dhan_fetch.chain(day, fetch=fetch, ids=_ids(), out_dir=str(tmp_path))
    out = json.loads(Path(path).read_text())

    assert out["date"] == day
    t = out["fut"]["t"]
    assert len(t) == 4                       # NOT 8: the 29th is not ours
    assert len(set(t)) == 4                  # and no minute appears twice
    assert out["fut"]["c"] == fut_raw["close"][:4]
    for k in out["strikes"]:
        for side in ("ce", "pe"):
            s = out["strikes"][k][side]
            assert len(s["t"]) == 4 == len(set(s["t"]))
            assert len(s["oi"]) == 4
    # the over-fetch is recorded rather than quietly discarded
    assert out["served_by_request"]["fut"] == {day: 4, nxt: 4}


def test_duplicate_timestamps_raise_rather_than_write(tmp_path):
    day = "2026-07-28"
    fut_raw = _payload(day, n=4, oi=False)
    fut_raw["timestamp"][2] = fut_raw["timestamp"][1]     # same minute twice
    opt_raw = _payload(day, n=4, oi=True)

    def fetch(sec_id, instrument, oi):
        return opt_raw if instrument == "OPTIDX" else fut_raw

    with pytest.raises(ValueError, match="duplicated timestamp"):
        dhan_fetch.chain(day, fetch=fetch, ids=_ids(), out_dir=str(tmp_path))
    assert list(tmp_path.iterdir()) == []     # nothing was written


def test_duplicate_in_an_option_leg_also_refuses_to_write(tmp_path):
    day = "2026-07-28"
    fut_raw = _payload(day, n=4, oi=False)
    opt_raw = _payload(day, n=4, oi=True)
    opt_raw["timestamp"][3] = opt_raw["timestamp"][0]

    def fetch(sec_id, instrument, oi):
        return opt_raw if instrument == "OPTIDX" else fut_raw

    with pytest.raises(ValueError, match="duplicated timestamp"):
        dhan_fetch.chain(day, fetch=fetch, ids=_ids(), out_dir=str(tmp_path))
    assert list(tmp_path.iterdir()) == []


def test_a_response_holding_only_another_session_is_refused_not_relabelled(
        tmp_path):
    # asking for the 29th and being handed only the 28th must not write the
    # 28th's bars under the 29th's name
    raw = _payload("2026-07-28", n=4)

    def fetch(sec_id, instrument, oi):
        return raw

    assert dhan_fetch.chain("2026-07-29", fetch=fetch, ids=_ids(),
                            out_dir=str(tmp_path)) is None
    assert list(tmp_path.iterdir()) == []


def test_one_session_reports_what_dhan_served_and_what_was_lost():
    raw = _two_sessions("2026-07-28", "2026-07-29", n=3)
    mine, served, lost = _one_session(raw, "2026-07-29")
    assert served == {"2026-07-28": 3, "2026-07-29": 3}
    assert lost == 0
    assert mine["close"] == raw["close"][3:]
