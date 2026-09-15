"""Forward cells are written once. A second pass is a no-op byte for byte.
The WATCH control is logged with the tell so a kill can execute."""
import copy
import score_frame

BARS = [{"t": 1757563500000 + i * 300000, "o": 100 + i, "h": 101 + i, "l": 99 + i, "c": 100.5 + i, "vol": 1} for i in range(40)]
ROW = {"day": "2026-09-11", "idx": "NIFTY", "ts": "09:45",
       "taps": [{"t": BARS[5]["t"], "i0": 5, "side": 1, "price": 99.0, "z": -2.1, "ex": {}}],
       "ladder": {"rows": [{"p": 110.0, "kind": "S", "state": "held"}, {"p": 95.0, "kind": "PE", "state": "held"}]},
       "watch": {"tells": [{"name": "PIN", "target": "110", "negation": "close under 100"}]}}


def test_cells_fill_once_and_a_second_pass_changes_nothing():
    one = score_frame.score([copy.deepcopy(ROW)], BARS)
    assert one[0]["taps"][0]["ex"]["1"] == 1.0 and one[0]["taps"][0]["ex"]["6"] == 6.0
    assert one[0]["watch"]["tells"][0]["resolved"] == "target"
    assert one[0]["watch"]["control"] and all("resolved" in c for c in one[0]["watch"]["control"])
    two = score_frame.score(copy.deepcopy(one), BARS)
    assert two == one
