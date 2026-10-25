"""Forward cells are written once. A second pass is a no-op byte for byte.
The setup's control is logged with the tell so a kill can execute."""
import copy
import score_frame
import frame
from test_frame import _tape, _book

BARS = [{"t": 1757563500000 + i * 300000, "o": 100 + i, "h": 101 + i, "l": 99 + i, "c": 100.5 + i, "vol": 1} for i in range(40)]
ROW = {"day": "2026-09-11", "idx": "NIFTY", "ts": "09:45",
       "taps": [{"t": BARS[5]["t"], "i0": 5, "side": 1, "price": 99.0, "z": -2.1, "ex": {}}],
       "walls": {"rows": [{"p": 110.0, "kind": "S", "state": "held"}, {"p": 95.0, "kind": "PE", "state": "held"}]},
       "setup": {"tells": [{"name": "PIN", "target": "110", "negation": "close under 100"}]}}


def test_frame_build_output_round_trips_through_score_frame():
    """I2: frame.build's return must carry the shape score_frame.score reads
    (a real bug: build() used to have no `taps` key at all, so the scorer
    ran against nothing). Round-trip a real build() output and confirm the
    tap actually gets an excursion filled."""
    t = _tape()
    t["taps"] = [{"t": t["closed"][5]["t"], "i0": 5, "side": 1, "price": t["closed"][5]["c"], "z": -2.1, "ex": {}}]
    fr = frame.build(t, _book(), "15:30")
    assert fr["taps"], "frame.build must carry the tape's taps forward"
    row = {"ts": fr["ts"], "taps": fr["taps"], "walls": fr["walls"], "setup": fr["setup"]}
    scored = score_frame.score([row], t["closed"])
    assert scored[0]["taps"][0]["ex"].get("1") is not None


def test_cells_fill_once_and_a_second_pass_changes_nothing():
    one = score_frame.score([copy.deepcopy(ROW)], BARS)
    assert one[0]["taps"][0]["ex"]["1"] == 1.0 and one[0]["taps"][0]["ex"]["6"] == 6.0
    assert one[0]["setup"]["tells"][0]["resolved"] == "target"
    assert one[0]["setup"]["control"] and all("resolved" in c for c in one[0]["setup"]["control"])
    two = score_frame.score(copy.deepcopy(one), BARS)
    assert two == one


def test_tell_stays_unresolved_not_frozen_none_until_bars_exist_past_ts():
    """A tell whose row.ts is after every bar we currently have can't be
    answered yet (px0 is None). Under write-once semantics setting
    resolved=None there would freeze it there forever -- so the key must be
    left ABSENT instead, letting a later pass (once bars exist) fill it."""
    row = {"day": "2026-09-11", "idx": "NIFTY", "ts": "13:00", "taps": [],
           "walls": {"rows": []},
           "setup": {"tells": [{"name": "PIN", "target": "110", "negation": "close under 100"}]}}
    one = score_frame.score([copy.deepcopy(row)], BARS)  # BARS ends 12:50 -- nothing after 13:00 yet
    assert "resolved" not in one[0]["setup"]["tells"][0]

    later_bars = BARS + [{"t": BARS[-1]["t"] + (i + 1) * 300000, "o": 105 + i, "h": 106 + i,
                           "l": 104 + i, "c": 105 + i, "vol": 1} for i in range(6)]
    two = score_frame.score(one, later_bars)
    assert "resolved" in two[0]["setup"]["tells"][0]


def test_setup_tells_resolve_against_walls_rows_and_write_control_on_setup():
    """The brief's shape: setup.tells target/negation resolve, and control is
    read from walls.rows and written onto setup (not onto walls)."""
    row = {"day": "2026-09-11", "idx": "NIFTY", "ts": "09:45", "taps": [],
           "walls": {"rows": [{"p": 110.0, "kind": "S", "state": "held"}, {"p": 95.0, "kind": "PE", "state": "held"}]},
           "setup": {"tells": [{"name": "DOWN", "target": "23250", "negation": "close back above 23300"}]}}
    scored = score_frame.score([copy.deepcopy(row)], BARS)
    assert "resolved" in scored[0]["setup"]["tells"][0]
    assert scored[0]["setup"]["control"] and all("resolved" in c for c in scored[0]["setup"]["control"])
    assert {c["p"] for c in scored[0]["setup"]["control"]} == {110.0, 95.0}
    assert "control" not in scored[0]["walls"]


def test_old_shape_row_without_setup_or_walls_is_left_byte_identical():
    """Pre-Task-1 rows already in data/frame/*.jsonl carry ladder/watch, not
    walls/setup. score() must not crash on them and must add nothing."""
    row = {"day": "2026-09-11", "idx": "NIFTY", "ts": "09:45", "taps": [],
           "ladder": {"rows": [{"p": 110.0, "kind": "S", "state": "held"}]},
           "watch": {"tells": [{"name": "PIN", "target": "110", "negation": "close under 100"}]}}
    before = copy.deepcopy(row)
    scored = score_frame.score([row], BARS)
    assert scored[0] == before


def test_write_survives_a_torn_line_and_keeps_rows_appended_mid_rewrite(tmp_path, monkeypatch):
    """3 Oct: one torn line made every later write raise, and a row appended between the read and the swap was
    lost. Now the torn line is dropped and an append that lands mid-rewrite rides into the new file."""
    import json
    import frame_log
    p = tmp_path / "frame_2026-09-11.jsonl"
    p.write_text(json.dumps(ROW) + "\n" + 'OSE", "to": "NOT OPEN' + "\n" + json.dumps(dict(ROW, ts="10:00")) + "\n", encoding="utf-8")
    real = score_frame.score

    def score_then_append(rows, bars):                # another POST appends while this one scores
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(ROW, ts="10:05")) + "\n")
        return real(rows, bars)
    monkeypatch.setattr(score_frame, "score", score_then_append)
    assert score_frame.write("2026-09-11", BARS, path=str(p)) == 2
    out = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
    assert [r["ts"] for r in out] == ["09:45", "10:00", "10:05"] and out[0]["taps"][0]["ex"]["1"] == 1.0
    assert not frame_log.LOCK.locked()


def test_write_scores_only_the_posting_index_rows(tmp_path):
    """25 Oct review D1 / A65: the day file holds every index, but the POST's bars belong to one. A SENSEX row
    filled from NIFTY's bars is a wrong outcome, written once and never corrected."""
    import json
    p = tmp_path / "frame_2026-09-11.jsonl"
    p.write_text(json.dumps(ROW) + "\n" + json.dumps(dict(ROW, idx="SENSEX")) + "\n", encoding="utf-8")
    score_frame.write("2026-09-11", BARS, path=str(p), idx="NIFTY")
    out = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
    assert out[0]["taps"][0]["ex"]["1"] == 1.0
    assert out[1]["taps"][0]["ex"] == {} and "resolved" not in out[1]["setup"]["tells"][0]


def test_a_hollow_bar_skips_its_own_cell_and_never_stops_the_rest():
    """25 Oct review D4 / A66: one bar with no close made every write that day raise (45 failures on 9 Oct,
    19 on 19 Oct), so nothing after it was ever scored."""
    bars = copy.deepcopy(BARS)
    bars[8]["c"] = None                                   # the tap's i0 5 + 3
    out = score_frame.score([copy.deepcopy(ROW)], bars)
    ex = out[0]["taps"][0]["ex"]
    assert ex["1"] == 1.0 and ex["6"] == 6.0 and "3" not in ex
    assert out[0]["setup"]["tells"][0]["resolved"] == "target"


def test_a_hollow_tap_bar_leaves_the_cells_empty_and_raises_nothing():
    """25 Oct review D4: no close at the tap's own bar means nothing to measure from; ex stays {}."""
    bars = copy.deepcopy(BARS)
    bars[5]["c"] = None                                   # the tap's own bar (i0 = 5)
    out = score_frame.score([copy.deepcopy(ROW)], bars)
    assert out[0]["taps"][0]["ex"] == {}


def test_a_hollow_minute_horizon_bar_skips_only_that_cell():
    """25 Oct review D4: the +90m cell reads bars[5 + 90 // 5]; a hollow one leaves "90m" absent, "1" still fills."""
    bars = copy.deepcopy(BARS)
    bars[23]["c"] = None                                  # the tap's i0 5 + 90 min / 5
    ex = score_frame.score([copy.deepcopy(ROW)], bars)[0]["taps"][0]["ex"]
    assert "90m" not in ex and ex["1"] == 1.0


def test_a_hollow_first_bar_after_the_row_does_not_leave_its_tells_unscored():
    """25 Oct review D4: px0 was after[0]["o"]; a hollow first bar (o and c None) left the tell and control unscored
    forever. ROW.ts 09:45 -> BARS[3] (09:50) is the first bar after it."""
    bars = copy.deepcopy(BARS)
    bars[3]["o"] = bars[3]["c"] = None
    out = score_frame.score([copy.deepcopy(ROW)], bars)
    assert out[0]["setup"]["tells"][0]["resolved"] == "target"
    assert out[0]["setup"]["control"]
