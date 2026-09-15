"""The day must survive the evening -- and must not survive into tomorrow.

The operator, verbatim: *"7:30pm ko bhi kholu to dekh paaoun kya hua"* and
*"abhi to ui he khali ho jaata"*. A post-close restart used to erase the
buyer's-tax day trace, which lived only in the process.

Two failures are pinned here because both would be SILENT. A file that loaded
across days would open tomorrow morning on yesterday's tax, rendering
confidently and wrongly. And a --mock-chain replay that wrote through the live
path would do to `data/day_state/` exactly what the 2026-08-24 leak did to the
paper desk and the war map: 33 hours of fixture looped into the record.
"""

import json

import day_state


def test_a_day_round_trips(tmp_path):
    rows = [{"t": "09:16", "frac": 0.33, "side": "ce"},
            {"t": "09:17", "frac": None, "side": None}]
    day_state.save("2026-08-25", {"drag_day": {"NIFTY": rows}}, dir_=tmp_path)
    assert day_state.load("2026-08-25", dir_=tmp_path)["drag_day"]["NIFTY"] == rows


def test_a_none_in_the_trace_is_kept_because_a_gap_is_a_fact():
    """`drag.py` refuses to invent a rate, so most samples are None. Dropping
    them on the way to disk would turn a gap into a shorter day."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        rows = [{"t": "09:16", "frac": None, "side": None}]
        day_state.save("2026-08-25", {"drag_day": {"NIFTY": rows}}, dir_=d)
        back = day_state.load("2026-08-25", dir_=d)["drag_day"]["NIFTY"]
        assert back == rows and back[0]["frac"] is None


def test_yesterdays_file_is_not_todays_day(tmp_path):
    """The whole reason `load` takes a day. Opening tomorrow morning on
    yesterday's trace renders a plausible, wrong session -- and nothing would
    raise."""
    day_state.save("2026-08-24", {"drag_day": {"NIFTY": [{"t": "09:16"}]}},
                   dir_=tmp_path)
    assert day_state.load("2026-08-25", dir_=tmp_path) == {}


def test_a_file_whose_stamp_disagrees_with_its_name_is_refused(tmp_path):
    """Belt and braces: the `day` INSIDE the document is what is checked, so a
    renamed or hand-copied file cannot smuggle another session in."""
    p = tmp_path / "day_2026-08-25.json"
    p.write_text(json.dumps({"day": "2026-08-24", "drag_day": {"NIFTY": []}}),
                 encoding="utf-8")
    assert day_state.load("2026-08-25", dir_=tmp_path) == {}


def test_missing_and_unreadable_both_start_the_day_cold(tmp_path):
    assert day_state.load("2026-08-25", dir_=tmp_path) == {}
    (tmp_path / "day_2026-08-25.json").write_text("{not json",
                                                  encoding="utf-8")
    assert day_state.load("2026-08-25", dir_=tmp_path) == {}


def test_a_save_leaves_no_temp_file_behind(tmp_path):
    """Atomic rewrite: the whole ring is the value, so a torn write would
    corrupt rather than truncate. `os.replace` is the guard, and a stray .tmp
    would mean it did not run."""
    day_state.save("2026-08-25", {"drag_day": {}}, dir_=tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["day_2026-08-25.json"]


def test_a_new_series_can_be_added_without_a_schema_change(tmp_path):
    day_state.save("2026-08-25", {"drag_day": {}, "something_later": [1, 2]},
                   dir_=tmp_path)
    assert day_state.load("2026-08-25", dir_=tmp_path)["something_later"] == [1, 2]


# ---- the isolation rule -----------------------------------------------------

def test_a_mock_run_cannot_write_into_the_live_day_state(monkeypatch):
    """The 2026-08-24 replay-leak rule, applied to every writer added since.
    A replay must never share a path with the record it rehearses for."""
    import server
    monkeypatch.setattr(day_state, "DIR", "data/day_state")
    monkeypatch.setattr(server, "VPIN_BACKFILL_LOG", "data/vpin_backfill.jsonl")
    server._isolate_mock_writers()
    assert day_state.DIR.replace("\\", "/") == "data/mock/day_state"
    assert "mock" in server.VPIN_BACKFILL_LOG.replace("\\", "/")


def test_every_new_writer_is_named_in_the_isolation_function():
    """A writer added without a line here leaks silently and is only found
    33 hours later. Pin the list by source so a new one is a failing test,
    not an incident."""
    import inspect

    import server
    src = inspect.getsource(server._isolate_mock_writers)
    for name in ("day_state.DIR", "VPIN_BACKFILL_LOG", "VPIN_LOG",
                 "desk_log.SURF_DIR", "trader_mod.STATE", "sequence_mod.DIR"):
        assert name in src, f"{name} is not redirected for a --mock-chain run"


# ---- what the server does with it -------------------------------------------

def test_the_restore_repopulates_the_ring_and_says_how_many(monkeypatch,
                                                            tmp_path):
    import server
    monkeypatch.setattr(day_state, "DIR", str(tmp_path))
    day = server.time.strftime("%Y-%m-%d")
    day_state.save(day, {"drag_day": {"NIFTY": [{"t": "09:16", "frac": 0.3,
                                                 "side": "ce"}]}},
                   dir_=tmp_path)
    server._SENSES["drag_day"] = {}
    server._SENSES["day_restored"] = 0
    server._load_day_state()
    assert server._SENSES["day_restored"] == 1
    assert list(server._SENSES["drag_day"]["NIFTY"])[0]["t"] == "09:16"
    # a deque, so the live loop can keep appending to it with its own bound
    assert server._SENSES["drag_day"]["NIFTY"].maxlen == 3000
    server._SENSES["drag_day"], server._SENSES["day_restored"] = {}, 0


def test_restored_rows_are_not_tagged_backfill(monkeypatch, tmp_path):
    """They were OBSERVED, by an earlier process on the same day. Tagging them
    as reconstructed would claim the tool guessed when it did not -- the
    mirror image of the mistake the vpin backfill guards against."""
    import server
    monkeypatch.setattr(day_state, "DIR", str(tmp_path))
    day = server.time.strftime("%Y-%m-%d")
    rows = [{"t": "09:16", "frac": 0.3, "side": "ce"}]
    day_state.save(day, {"drag_day": {"NIFTY": rows}}, dir_=tmp_path)
    server._SENSES["drag_day"] = {}
    server._load_day_state()
    back = list(server._SENSES["drag_day"]["NIFTY"])
    assert all("backfill" not in r for r in back)
    server._SENSES["drag_day"], server._SENSES["day_restored"] = {}, 0


def test_a_save_and_a_restore_close_the_loop(monkeypatch, tmp_path):
    """The whole point, end to end: what the loop wrote at 15:29 is what a
    19:30 cold start reads back."""
    from collections import deque

    import server
    monkeypatch.setattr(day_state, "DIR", str(tmp_path))
    server._SENSES["drag_day"] = {
        "NIFTY": deque([{"t": "14:59", "frac": 0.88, "side": "pe"}],
                       maxlen=3000)}
    server._save_day_state()
    server._SENSES["drag_day"] = {}
    server._load_day_state()
    assert list(server._SENSES["drag_day"]["NIFTY"])[0]["frac"] == 0.88
    server._SENSES["drag_day"], server._SENSES["day_restored"] = {}, 0
