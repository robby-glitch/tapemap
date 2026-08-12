"""The --json snapshot signal_review writes for the Trade tab's callout.

The card renders a number from this file, so the file's SHAPE is a promise
about what the card is allowed to claim. These tests pin the promise:

  * claim-strength buckets are exported, with n and hit alongside every rate;
  * PER-KIND numbers are NOT, because per-kind n runs 1-5 on one session and
    "100% - 2/2" reads as a measurement no matter how it is styled;
  * the control ships with them, because a hit rate with nothing to compare
    against is not a result;
  * the disclosure and method sentences travel WITH the numbers rather than
    living only in a docstring nobody renders.

The last one is the point of the whole file. C13 refused the fixed 30-minute
exit as a trading rule, and these numbers are scored on exactly that clock --
so the sentence saying so has to be impossible to render the numbers without.
"""
import json

import signal_review as sr


def _day(events, closes):
    """A minimal /api/data day: one bar per close, one event per entry.

    Bars carry the `fut` block score() filters on, and event times line up
    with bar times so every event is scorable.
    """
    bars = [{"t": f"{9 + i // 60:02d}:{i % 60:02d}",
             "fut": {"c": c, "h": c + 1, "l": c - 1}}
            for i, c in enumerate(closes)]
    return {"day": "2026-07-30", "bars": bars, "events": events}


def _trap(t):
    """A TRAP-SPRUNG event: a `call` kind that evDir resolves to DN."""
    return {"t": t, "kind": "TRAP-SPRUNG", "msg": "BULL TRAP SPRUNG at 24700"}


def _press(t):
    """A PRESS event: a `lean` kind that evDir resolves to UP."""
    return {"t": t, "kind": "PRESS", "msg": "PE writers pressing -> BULLISH"}


def _snapshot(events, closes):
    day = _day(events, closes)
    bars, close, _high, _low, scored, _und = sr.score(day)
    return sr.summary("NIFTY", day, bars, close, scored)


# 40 bars falling 1 point each, so a DN-called signal is right and the
# unconditional long control is wrong -- the two must not come out the same.
FALLING = [24700 - i for i in range(40)]


def test_claim_buckets_carry_n_and_hit():
    snap = _snapshot([_trap("09:00")], FALLING)
    assert snap["claim"]["call"] == {"n": 1, "hit": 1, "avg30": 30.0}


def test_per_kind_numbers_are_not_exported():
    """The load-bearing exclusion: no kind name may reach the snapshot.

    Not "is absent today" -- must STAY absent. If a future edit adds a
    per-kind block, this fails and the reason is in this file's docstring.
    """
    snap = _snapshot([_trap("09:00"), _press("09:01")], FALLING)
    blob = json.dumps(snap)
    for kind in ("TRAP-SPRUNG", "PRESS", "kinds", "by_kind"):
        assert kind not in blob


def test_control_is_present_and_independent_of_the_signals():
    """Same bars, different events -> identical control.

    The control describes the session, not the signals; if it ever moved with
    the event list it would have stopped being a control.
    """
    a = _snapshot([_trap("09:00")], FALLING)
    b = _snapshot([_press("09:00"), _trap("09:02")], FALLING)
    assert a["control"] == b["control"]
    assert a["control"]["n"] == len(FALLING) - 30
    # Every bar falls, so a long never wins over any 30-bar window.
    assert a["control"]["hit"] == 0


def test_a_called_direction_can_beat_the_control():
    """The DN call scores +30 while the long control scores -30.

    Without this the suite would pass on a summary that signed nothing.
    """
    snap = _snapshot([_trap("09:00")], FALLING)
    assert snap["claim"]["call"]["avg30"] > 0
    assert snap["control"]["avg30"] < 0


def test_disclosure_and_method_travel_with_the_numbers():
    snap = _snapshot([_trap("09:00")], FALLING)
    assert snap["disclosure"] == sr.DISCLOSURE
    assert snap["method"] == sr.METHOD
    # The refusal C13 wrote down has to be legible in the payload itself.
    assert "not a trading rule" in snap["method"]
    assert "SIGNAL QUALITY" in snap["method"]


def test_provenance_names_the_session_not_just_the_run_date():
    """A snapshot generated on a Sunday describes Friday's tape.

    `generated` and `session` are different questions and must stay separate
    fields -- collapsing them is how a stale number starts looking fresh.
    """
    snap = _snapshot([_trap("09:00")], FALLING)
    assert snap["session"] == "2026-07-30"
    assert snap["horizon_min"] == 30
    assert snap["index"] == "NIFTY"
    assert "generated" in snap and snap["generated"] != snap["session"]


def test_empty_claim_block_when_nothing_scored():
    """An undirected-only session exports no bucket rather than a zero one."""
    quiet = {"t": "09:00", "kind": "CHOP", "msg": "chop"}
    snap = _snapshot([quiet], FALLING)
    assert snap["claim"] == {}
    assert snap["scored"] == 0


class TestParseArgs:
    """--json must not disturb the positional invocation already in use."""

    def test_defaults(self):
        assert sr.parse_args([]) == ("NIFTY", "8765", None)

    def test_existing_positional_invocation_is_untouched(self):
        assert sr.parse_args(["BANKNIFTY", "8765"]) == ("BANKNIFTY", "8765", None)

    def test_json_without_path_uses_the_default(self):
        assert sr.parse_args(["--json"]) == ("NIFTY", "8765", sr.DEFAULT_JSON)

    def test_json_with_path(self):
        assert sr.parse_args(["NIFTY", "--json", "out.json"]) == (
            "NIFTY", "8765", "out.json")

    def test_json_between_positionals_keeps_both(self):
        assert sr.parse_args(["SENSEX", "--json", "o.json", "9000"]) == (
            "SENSEX", "9000", "o.json")

    def test_json_greedily_eats_the_next_token(self):
        """Documented sharp edge: `--json BANKNIFTY 8765` reads BANKNIFTY as
        the output PATH, not the index. Pinned so the behaviour is a decision
        rather than a surprise -- put --json last, or give it a path."""
        assert sr.parse_args(["--json", "BANKNIFTY", "8765"]) == (
            "8765", "8765", "BANKNIFTY")
