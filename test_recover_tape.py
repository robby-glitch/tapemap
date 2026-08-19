"""recover_tape -- the refusals matter more than the happy path.

A reconstructed tape feeds `trigger_log.score`, so a file this writes decides
what a forward-logged row's outcome IS. The three refusals below are what stop
it from replacing "no cached session" with a silently worse answer.
"""

import json

import pytest

import recover_tape


def _rows(n, day="2026-08-13", start_h=9, start_m=15):
    """`n` one-minute Kite candles: [ISO stamp, o, h, l, c, v, oi]."""
    out = []
    for i in range(n):
        m = start_h * 60 + start_m + i
        out.append([f"{day}T{m // 60:02d}:{m % 60:02d}:00+05:30",
                    100.0 + i, 101.0 + i, 99.0 + i, 100.5 + i, 500, 1000 + i])
    return out


def test_the_layout_matches_the_loader():
    # squeeze_score._paths: NIFTY flat, every other index in a subdirectory.
    assert recover_tape.path_for("NIFTY", "2026-08-13").endswith(
        "backtest/fut_2026-08-13.json")
    assert recover_tape.path_for("SENSEX", "2026-08-13").endswith(
        "backtest/SENSEX/fut_2026-08-13.json")


def test_stamps_become_epoch_and_a_stray_day_is_dropped():
    rows = _rows(3) + [["2026-08-12T09:15:00+05:30", 1, 2, 0.5, 1.5, 10, 20]]
    out = recover_tape.to_payload(rows, "SENSEX", "2026-08-13")
    assert len(out["timestamp"]) == 3           # the 08-12 bar is not ours
    assert all(isinstance(t, float) for t in out["timestamp"])
    assert out["timestamp"] == sorted(out["timestamp"])
    assert out["open_interest"][0] == 1000.0
    assert out["_meta"]["source"].startswith("kite historical")


def test_a_thin_session_is_refused_not_written(tmp_path, monkeypatch):
    monkeypatch.setattr(recover_tape, "BT", str(tmp_path))
    with pytest.raises(SystemExit) as e:
        recover_tape.write("SENSEX", "2026-08-13", _rows(40))
    assert "under 60" in str(e.value)
    assert not list(tmp_path.rglob("*.json"))   # nothing written


def test_an_existing_capture_is_never_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(recover_tape, "BT", str(tmp_path))
    dst = tmp_path / "SENSEX" / "fut_2026-08-13.json"
    dst.parent.mkdir(parents=True)
    dst.write_text('{"live": "capture"}', encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        recover_tape.write("SENSEX", "2026-08-13", _rows(200))
    assert "already exists" in str(e.value)
    assert json.loads(dst.read_text(encoding="utf-8")) == {"live": "capture"}


def test_a_written_tape_loads_through_the_scorer_s_own_reader(tmp_path,
                                                              monkeypatch):
    # The whole point: what this writes must survive contract_bars.to_bars,
    # which is the ONE path score/f15/f30 read a session through.
    import contract_bars as cb
    monkeypatch.setattr(recover_tape, "BT", str(tmp_path))
    path, n = recover_tape.write("SENSEX", "2026-08-13", _rows(200))
    assert n == 200
    payload = json.load(open(path, encoding="utf-8"))
    bars = cb.to_bars(payload)
    assert len(bars) == 200
    assert bars[0]["t"] == "09:15"
    assert bars[0]["oi"] == 1000.0
