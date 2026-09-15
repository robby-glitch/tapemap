"""Forward cells are written once. A second pass is a no-op byte for byte.
The WATCH control is logged with the tell so a kill can execute."""
import copy
import score_frame
import frame
from test_frame import TAPE, BOOK

BARS = [{"t": 1757563500000 + i * 300000, "o": 100 + i, "h": 101 + i, "l": 99 + i, "c": 100.5 + i, "vol": 1} for i in range(40)]
ROW = {"day": "2026-09-11", "idx": "NIFTY", "ts": "09:45",
       "taps": [{"t": BARS[5]["t"], "i0": 5, "side": 1, "price": 99.0, "z": -2.1, "ex": {}}],
       "ladder": {"rows": [{"p": 110.0, "kind": "S", "state": "held"}, {"p": 95.0, "kind": "PE", "state": "held"}]},
       "watch": {"tells": [{"name": "PIN", "target": "110", "negation": "close under 100"}]}}


def test_frame_build_output_round_trips_through_score_frame():
    """I2: frame.build's return must carry the shape score_frame.score reads
    (a real bug: build() used to have no `taps` key at all, so the scorer
    ran against nothing). Round-trip a real build() output and confirm the
    tap actually gets an excursion filled."""
    fr = frame.build(TAPE, BOOK, "10:20")
    assert fr["taps"], "frame.build must carry the tape's taps forward"
    row = {"ts": fr["ts"], "taps": fr["taps"], "ladder": fr["ladder"], "watch": fr["watch"]}
    scored = score_frame.score([row], TAPE["closed"])
    assert scored[0]["taps"][0]["ex"].get("1") is not None


def test_cells_fill_once_and_a_second_pass_changes_nothing():
    one = score_frame.score([copy.deepcopy(ROW)], BARS)
    assert one[0]["taps"][0]["ex"]["1"] == 1.0 and one[0]["taps"][0]["ex"]["6"] == 6.0
    assert one[0]["watch"]["tells"][0]["resolved"] == "target"
    assert one[0]["watch"]["control"] and all("resolved" in c for c in one[0]["watch"]["control"])
    two = score_frame.score(copy.deepcopy(one), BARS)
    assert two == one


def test_tell_stays_unresolved_not_frozen_none_until_bars_exist_past_ts():
    """A tell whose row.ts is after every bar we currently have can't be
    answered yet (px0 is None). Under write-once semantics setting
    resolved=None there would freeze it there forever -- so the key must be
    left ABSENT instead, letting a later pass (once bars exist) fill it."""
    row = {"day": "2026-09-11", "idx": "NIFTY", "ts": "13:00", "taps": [],
           "ladder": {"rows": []},
           "watch": {"tells": [{"name": "PIN", "target": "110", "negation": "close under 100"}]}}
    one = score_frame.score([copy.deepcopy(row)], BARS)  # BARS ends 12:50 -- nothing after 13:00 yet
    assert "resolved" not in one[0]["watch"]["tells"][0]

    later_bars = BARS + [{"t": BARS[-1]["t"] + (i + 1) * 300000, "o": 105 + i, "h": 106 + i,
                           "l": 104 + i, "c": 105 + i, "vol": 1} for i in range(6)]
    two = score_frame.score(one, later_bars)
    assert "resolved" in two[0]["watch"]["tells"][0]
