"""Guard for the 2026-07-30 Dhan intraday date-range bug: rest_intraday sent
fromDate == toDate == day, but the /v2/charts/intraday endpoint treats toDate
as EXCLUSIVE, so that combination returns zero bars every single time (proven
live against NIFTY security id 65852: toDate = day + 1 returned 375 real 1-min
bars, toDate = day returned none). fetch_chain_day's two callers (FUT and each
option leg) each pass one calendar day, so the fix must add the day internally
via _intraday_body while keeping rest_intraday's public signature untouched.
These tests exercise body construction only -- no network calls."""
from dhan_fetch import _intraday_body


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
