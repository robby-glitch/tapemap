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


def test_capture_reports_a_dead_server_as_a_reason(tmp_path):
    def boom(_idx):
        raise OSError("connection refused")

    path, n, why = EC.capture("SENSEX", fetch=boom, root=str(tmp_path))
    assert path is None and n == 0
    assert "could not read the live tape" in why and "server" in why
