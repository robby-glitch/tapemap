"""What a capture has to survive: being LOADED again.

The failure this guards is not a crash. `squeeze_score.load` wraps its parse in
`except Exception: continue`, so a capture written in the wrong shape does not
raise -- the session simply never appears, indistinguishable from one that was
never captured. And a capture written with the wrong timezone loads fine while
placing every bar at the wrong minute, which would silently score §5c rows
against a tape shifted off the session.

So the central test round-trips: build a session, write it, then re-derive it
through `to_bars -> vwap_bands -> resample` exactly as `squeeze_score.load`
does, and assert the clock survived.
"""
import json
import os
from datetime import timedelta

import contract_bars as cb
import eod_capture as EC

DAY = "2026-08-13"
# 09:15 IST on DAY, the session's first minute. Written as an explicit instant
# so the test pins the offset rather than recomputing it the same (possibly
# wrong) way the code under test does.
OPEN_TS = cb.datetime(2026, 8, 13, 9, 15, tzinfo=cb.IST).timestamp()


def _payload(n=375, day_label="Aug 13 LIVE", built=OPEN_TS, bars=None):
    """A server payload with `n` one-minute bars from 09:15."""
    if bars is None:
        bars = []
        for i in range(n):
            hh, mm = divmod(9 * 60 + 15 + i, 60)
            bars.append({"t": f"{hh:02d}:{mm:02d}",
                         "fut": {"o": 1000.0 + i, "h": 1002.0 + i,
                                 "l": 999.0 + i, "c": 1001.0 + i,
                                 "v": 100.0 + i, "oi": 5000.0 + i}})
    return {"built_at": built, "expiry": "2026-08-25",
            "days": [{"day": day_label, "bars": bars}]}


def _reload(path):
    """`squeeze_score.load`'s derivation, verbatim, on one file."""
    payload = json.load(open(path, encoding="utf-8"))
    return payload, cb.resample(cb.vwap_bands(cb.to_bars(payload)), 3)


def test_capture_round_trips_through_the_loader(tmp_path):
    path, n, why = EC.capture("SENSEX", fetch=lambda i: _payload(),
                              root=str(tmp_path))
    assert why is None and n == 375
    assert path.endswith("fut_2026-08-13.json")
    # Non-NIFTY sits in a subdirectory; NIFTY is flat. Getting this wrong means
    # `_paths` never globs the file.
    assert "SENSEX" in path

    payload, bars = _reload(path)
    assert set(payload) >= {"open", "high", "low", "close", "volume",
                            "timestamp", "open_interest"}
    # The clock survived the epoch round-trip. This is the silent-corruption
    # guard: a wrong offset still loads, just at the wrong minutes.
    one_min = cb.to_bars(payload)
    assert one_min[0]["t"] == "09:15"
    assert one_min[-1]["t"] == "15:29"
    # And it came back BANDED at 3 minutes, which is what §5c is measured on.
    assert bars[0]["t"] == "09:15"
    assert "u3" in bars[0] and "d3" in bars[0]
    # load() drops anything under 60 bars; a real session must clear it.
    assert len(bars) >= 60


def test_nifty_is_written_flat_not_in_a_subdirectory(tmp_path):
    path, _n, why = EC.capture("NIFTY", fetch=lambda i: _payload(),
                               root=str(tmp_path))
    assert why is None
    assert path == EC.path_for("NIFTY", DAY, str(tmp_path))
    assert "NIFTY" not in path.replace(str(tmp_path), "")


def test_short_session_is_refused_not_written(tmp_path):
    """The exact shape `load` would swallow: fewer than 60 bars."""
    path, n, why = EC.capture("SENSEX", fetch=lambda i: _payload(n=30),
                              root=str(tmp_path))
    assert path is None and n == 0
    assert "30" in why and "60" in why
    assert not list(tmp_path.rglob("*.json"))


def test_rolled_server_is_refused(tmp_path):
    """Midnight roll: the payload still parses, but holds no day with bars.

    This is the 2026-08-13 failure. It must report a reason, never write an
    empty session that would later read as 'the trade went flat'.
    """
    p = _payload()
    p["days"] = []
    _path, _n, why = EC.capture("SENSEX", fetch=lambda i: p, root=str(tmp_path))
    assert why and "rolled" in why
    assert not list(tmp_path.rglob("*.json"))


def test_missing_built_at_refuses_rather_than_guessing_today(tmp_path):
    _path, _n, why = EC.capture("SENSEX", fetch=lambda i: _payload(built=None),
                                root=str(tmp_path))
    assert why and "built_at" in why


def test_existing_file_is_not_clobbered_without_force(tmp_path):
    first, _n, why = EC.capture("SENSEX", fetch=lambda i: _payload(),
                                root=str(tmp_path))
    assert why is None
    before = json.load(open(first, encoding="utf-8"))["_meta"]["bars"]

    # A second capture of a SHORTER day must not replace the fuller record.
    _p2, _n2, why2 = EC.capture("SENSEX", fetch=lambda i: _payload(n=200),
                                root=str(tmp_path))
    assert why2 and "already exists" in why2
    assert json.load(open(first, encoding="utf-8"))["_meta"]["bars"] == before

    _p3, n3, why3 = EC.capture("SENSEX", fetch=lambda i: _payload(n=200),
                               root=str(tmp_path), force=True)
    assert why3 is None and n3 == 200


def test_a_bar_missing_a_field_is_dropped_whole(tmp_path):
    """Positional arrays: a gap in one column would pair the wrong minute's
    price with the next minute's volume, so the bar goes entirely."""
    p = _payload()
    del p["days"][0]["bars"][5]["fut"]["v"]
    p["days"][0]["bars"][9]["fut"]["oi"] = None
    path, n, why = EC.capture("SENSEX", fetch=lambda i: p, root=str(tmp_path))
    assert why is None and n == 373

    payload, _bars = _reload(path)
    assert payload["_meta"]["dropped"] == 2
    assert all(len(payload[k]) == 373 for k in
               ("open", "high", "low", "close", "volume", "timestamp",
                "open_interest"))
    # The dropped minute is genuinely absent, not zero-filled.
    assert "09:20" not in [b["t"] for b in cb.to_bars(payload) if b]


def test_min_bars_still_matches_the_loader_that_drops_them():
    """MIN_BARS mirrors a constant in ANOTHER file, and drift is silent.

    `squeeze_score.load` skips a session with `len(bars) < 60` using a bare
    `continue`. If that number ever rises, `eod_capture` keeps happily writing
    sessions between the two thresholds and every one of them is dropped on
    load -- reported to the operator as "captured", read by the scorer as
    "never existed". Nothing else in the suite would notice.
    """
    src = open("squeeze_score.py", encoding="utf-8").read()
    assert f"len(bars) < {EC.MIN_BARS}" in src, (
        f"eod_capture.MIN_BARS is {EC.MIN_BARS} but squeeze_score.load no "
        f"longer drops at that count -- captures between the two thresholds "
        f"would be written and then silently ignored")


def test_capture_reports_a_dead_server_as_a_reason(tmp_path):
    def boom(_idx):
        raise OSError("connection refused")

    path, n, why = EC.capture("SENSEX", fetch=boom, root=str(tmp_path))
    assert path is None and n == 0
    assert "could not read the live tape" in why and "server" in why


# --------------------------------------------------------------------------
# 5c -- preserving the day's surface fit log and desk_log snapshot alongside
# the OHLC bars above. Neither is broker-sourced, so neither can be refetched
# once a machine's local copy is gone -- unlike the bars `capture` writes.
# --------------------------------------------------------------------------

def test_capture_desk_record_copies_both_files(tmp_path, monkeypatch):
    src_surf_dir = tmp_path / "src_surface"
    src_surf_dir.mkdir()
    src_surf = src_surf_dir / "surface_2026-08-24.jsonl"
    src_surf.write_text('{"idx": "NIFTY", "a": 0.15}\n', encoding="utf-8")
    src_desk = tmp_path / "src_desk_log.jsonl"
    src_desk.write_text('{"idx": "NIFTY", "field": "gear"}\n',
                        encoding="utf-8")

    monkeypatch.setattr(EC, "SURF_SRC_DIR", str(src_surf_dir))
    monkeypatch.setattr(EC, "DESK_LOG_SRC", str(src_desk))

    root = str(tmp_path / "backtest")
    out = EC.capture_desk_record("2026-08-24", root=root)

    surf_path, surf_why = out["surface"]
    desk_path, desk_why = out["desk_log"]
    assert surf_why is None and desk_why is None
    assert surf_path == os.path.join(root, "surface_2026-08-24.jsonl")
    assert desk_path == os.path.join(root, "desk_log_2026-08-24.jsonl")
    assert open(surf_path, encoding="utf-8").read() == src_surf.read_text(
        encoding="utf-8")
    assert open(desk_path, encoding="utf-8").read() == src_desk.read_text(
        encoding="utf-8")


def test_capture_desk_record_reports_a_missing_source_as_a_reason(tmp_path,
                                                                   monkeypatch):
    """No surface fit and no desk_log yet -- e.g. a day the market never
    opened -- is a NAMED reason, never a silent no-op or a fabricated empty
    file."""
    monkeypatch.setattr(EC, "SURF_SRC_DIR", str(tmp_path / "no_such_dir"))
    monkeypatch.setattr(EC, "DESK_LOG_SRC", str(tmp_path / "no_such_file"))
    out = EC.capture_desk_record("2026-08-24", root=str(tmp_path / "bt"))
    assert out["surface"][0] is None and "does not exist" in out["surface"][1]
    assert out["desk_log"][0] is None and "does not exist" in out["desk_log"][1]


def test_capture_desk_record_does_not_clobber_without_force(tmp_path,
                                                              monkeypatch):
    src_desk = tmp_path / "src_desk_log.jsonl"
    src_desk.write_text('{"a": 1}\n', encoding="utf-8")
    monkeypatch.setattr(EC, "SURF_SRC_DIR", str(tmp_path / "no_such_dir"))
    monkeypatch.setattr(EC, "DESK_LOG_SRC", str(src_desk))

    root = str(tmp_path / "backtest")
    first = EC.capture_desk_record("2026-08-24", root=root)
    assert first["desk_log"][1] is None

    src_desk.write_text('{"a": 1}\n{"a": 2}\n', encoding="utf-8")
    second = EC.capture_desk_record("2026-08-24", root=root)
    assert second["desk_log"][0] is None
    assert "already exists" in second["desk_log"][1]
    # The first, shorter capture is still the one on disk.
    dst = os.path.join(root, "desk_log_2026-08-24.jsonl")
    assert open(dst, encoding="utf-8").read() == '{"a": 1}\n'

    third = EC.capture_desk_record("2026-08-24", root=root, force=True)
    assert third["desk_log"][1] is None
    assert open(dst, encoding="utf-8").read() == '{"a": 1}\n{"a": 2}\n'


def test_a19_a_dead_server_falls_back_to_the_sessions_own_upstox_candles(tmp_path, monkeypatch):
    """A19: 9 Oct was lost because the only source was the running server. With the server down the run reads the
    same Upstox 1-min candles the tape is built from, for the contract the book record stamped that day (roll-aware),
    and writes the file the loader reads; with no book on a past day it refuses rather than guess across a roll."""
    import book_log
    import recover_tape
    import upstox_feed
    import upstox_rest
    monkeypatch.setattr(recover_tape, "BT", str(tmp_path / "bt"))
    monkeypatch.setattr(EC, "capture", lambda idx, force=False: (None, 0, "could not read the live tape -- is the server up?"))
    monkeypatch.setattr(EC, "session_day", lambda now=None: "2026-10-09")
    monkeypatch.setattr(upstox_feed, "read_token", lambda path=None: "tok")
    asked = []

    def historical(key, tok, day, interval="1minute"):          # newest first, Upstox's own shape
        asked.append((key, day))
        t0 = cb.datetime(2026, 10, 9, 9, 15, tzinfo=cb.IST)
        return [[(t0 + timedelta(minutes=i)).isoformat(), 1.0, 2.0, 0.5, 1.5, 10, 100] for i in range(375)][::-1]
    monkeypatch.setattr(upstox_rest, "historical", historical)
    os.makedirs(book_log.DIR, exist_ok=True)
    with open(book_log.day_path("2026-10-09", "NIFTY"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"t": 1, "ik": "NSE_FO|48704", "expiry": "2026-10-27"}) + "\n")
    assert EC.main(["eod_capture.py", "NIFTY", "BANKNIFTY"]) == 1                        # BANKNIFTY: no book
    assert asked == [("NSE_FO|48704", "2026-10-09")]
    got = json.load(open(recover_tape.path_for("NIFTY", "2026-10-09"), encoding="utf-8"))
    assert got["_meta"]["fut_id"] == "NSE_FO|48704" and got["_meta"]["expiry"] == "2026-10-27"
    assert got["_meta"]["source"] == EC.UPSTOX and len(got["timestamp"]) >= EC.MIN_BARS
    assert not os.path.exists(recover_tape.path_for("BANKNIFTY", "2026-10-09"))


def test_a19_the_session_a_run_is_for():
    at = lambda *a: cb.datetime(*a, tzinfo=cb.IST)                                    # noqa: E731
    assert EC.session_day(at(2026, 10, 22, 15, 35)) == "2026-10-22"                    # the 15:35 run
    assert EC.session_day(at(2026, 10, 23, 9, 20)) == "2026-10-22"                     # a late catch-up run
    assert EC.session_day(at(2026, 10, 24, 16, 10)) == "2026-10-23"                    # Saturday: Friday's
    assert EC.session_day(at(2026, 10, 26, 11, 0)) == "2026-10-23"                     # Monday morning: Friday's
