"""test_vix_log.py -- T2, the India VIX record (vix_log.py). conftest points vix_log.DIR at tmp: nothing here touches data/."""
import datetime
import json
import os

import pytest

import vix_log

IST = vix_log.IST


def _at(hm, day="2026-11-02"):
    return datetime.datetime.fromisoformat(f"{day}T{hm}:20").replace(tzinfo=IST)


def _c(hm, close, day="2026-11-02"):
    return [f"{day}T{hm}:00+05:30", close, close, close, close, 0, 0]


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setattr(vix_log, "STATE", dict(vix_log.STATE, last_ok=None, last_row=None, written=0, backfill=0, failed=0,
                                               why="no read yet this process"))
    monkeypatch.setattr(vix_log, "_SEEN", {})


def test_the_reader_on_a_toy_file_keeps_good_rows_in_time_order():
    os.makedirs(vix_log.DIR)
    with open(vix_log.path_for("2026-11-02"), "w", encoding="utf-8") as f:
        f.write("\n".join([json.dumps({"ts": "09:16", "vix": 13.1}), "{torn", json.dumps({"ts": "09:15", "vix": 12.8}),
                           json.dumps({"ts": "09:17", "vix": 0}), json.dumps({"ts": "9:18", "vix": 13.0}),
                           json.dumps({"ts": "09:19", "vix": None})]) + "\n")
    assert vix_log.rows("2026-11-02") == [{"ts": "09:15", "vix": 12.8}, {"ts": "09:16", "vix": 13.1}]
    assert vix_log.rows("2026-10-30") == []                      # no file: no rows, never a zero


def test_write_takes_closed_candles_once_and_tags_a_late_start_backfill():
    day = [_c("09:14", 12.0), _c("09:15", 12.8), _c("09:16", 12.9), _c("11:05", 13.3), _c("11:06", 13.4),
           _c("11:07", 13.5), _c("10:00", 13.0, day="2026-10-30")]
    out = vix_log.write("2026-11-02", day, _at("11:07"))         # a server started at 11:07
    assert [r["ts"] for r in out] == ["09:15", "09:16", "11:05", "11:06"]   # no pre-open, no forming 11:07, no other day
    assert [r.get("src") for r in out] == ["backfill", "backfill", "backfill", None]
    assert vix_log.write("2026-11-02", day, _at("11:07")) == []  # once only
    vix_log._SEEN.clear()                                        # a restart re-reads the file: still once
    assert [r["ts"] for r in vix_log.write("2026-11-02", day, _at("11:08"))] == ["11:07"]
    assert [r["ts"] for r in vix_log.rows("2026-11-02")] == ["09:15", "09:16", "11:05", "11:06", "11:07"]


def test_a_bad_minute_is_counted_and_named_and_the_next_minute_writes():
    def boom():
        raise OSError("HTTP Error 503: Service Unavailable")
    assert vix_log.tick(_at("10:00"), boom) == []
    h = vix_log.health()
    assert h["failed"] == 1 and h["why"] == "read failed at 10:00: OSError: HTTP Error 503: Service Unavailable"
    assert vix_log.tick(_at("10:01"), lambda: [_c("09:59", 13.2), _c("10:00", 13.3)]) != []
    h = vix_log.health()
    assert h["failed"] == 1 and h["why"] is None and h["written"] == 2 and h["backfill"] == 1
    assert h["last_row"] == "2026-11-02 10:00" and h["key"] == "NSE_INDEX|India VIX"


def test_tick_reads_nothing_outside_market_hours_and_says_so():
    called = []
    assert vix_log.tick(_at("09:10"), lambda: called.append(1)) == []
    assert vix_log.tick(_at("11:00", day="2026-11-01"), lambda: called.append(1)) == []    # a Sunday
    assert not called and vix_log.health()["why"] == "no read: outside market hours (11:00)"
    assert vix_log.tick(_at("10:00"), lambda: []) == []
    assert vix_log.health()["why"] == "no VIX candle today by 10:00"
