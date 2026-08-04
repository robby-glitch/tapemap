"""band_rotation.detect_index_run -- the operator's ACTUAL two-candle d3 rule.

Specified by the operator on 2026-08-05 and pre-registered in
`context/research-findings.md` §5c. It is NOT the rule `_trigger` implements,
and the difference is the whole point of this file:

    _trigger          ONE bar pierces d3 AND closes back above it.
    detect_index_run  a bar TOUCHES d3 (it may close far below); a LATER bar
                      closes above THAT bar's high. Entry is that close.

Fixtures use the flat index shape (`t` plus the band keys on one dict), which
`_index_bar` accepts directly. VWAP is 100 and sigma is 5, so d3 is 85 and
every number below can be read at a glance.

Families:
  1. Arm / trigger  -- touch with no close-back; a wick is not a trigger.
  2. Reference walk -- a new lower low moves it, and restarts its clock.
  3. Window         -- the last bar inside it counts; one past it does not.
  4. Gate           -- the operator's 09:25 anchor.
  5. Re-fire        -- VWAP unlocks; a known stop unlocks sooner.
  6. Isolation      -- the one-candle path is byte-for-byte unaffected.
  7. Junk input     -- never raises, never fabricates.
"""

import band_rotation
from band_rotation import detect_index, detect_index_run

VWAP = 100.0
SD = 5.0
D3 = VWAP - 3 * SD          # 85.0
D2 = VWAP - 2 * SD          # 90.0

BANDS = {"vwap": VWAP,
         "u1": VWAP + SD, "d1": VWAP - SD,
         "u2": VWAP + 2 * SD, "d2": D2,
         "u3": VWAP + 3 * SD, "d3": D3}

OPEN_MIN = 9 * 60 + 30      # 09:30 -- comfortably past the 09:25 anchor


def _t(i, base=OPEN_MIN, step=3):
    """The i-th 3-minute label of a session starting at `base`."""
    m = base + step * i
    return f"{m // 60:02d}:{m % 60:02d}"


def _bar(t, low, high, close, **over):
    """One flat index bar. `o` is irrelevant to this rule and tracks close."""
    b = dict(BANDS)
    b.update({"t": t, "o": close, "h": high, "l": low, "c": close})
    b.update(over)
    return b


# A bar that can do nothing: it never reaches d3 (85) and never rises to VWAP.
def _inert(t):
    return _bar(t, 88.0, 94.0, 91.0)


# Touches d3 and closes BELOW it -- the old rule cannot fire on this, the new
# one arms on it. This single bar is the difference between the two rules.
def _touch(t, high=95.0):
    return _bar(t, 84.0, high, 84.5)


# -- 1. arm / trigger ------------------------------------------------------

def test_a_touch_that_closes_below_the_band_still_arms_and_then_triggers():
    bars = [_touch(_t(0)), _bar(_t(1), 91.0, 97.0, 96.0)]
    out = detect_index_run(bars)
    assert out[0] is None                      # arming is not a signal
    rec = out[1]
    assert rec is not None
    assert rec["side"] == "BUY" and rec["band"] == "d3"
    assert rec["ref_i"] == 0 and rec["ref_high"] == 95.0
    assert rec["level"] == D3 and rec["waited"] == 1


def test_the_one_candle_rule_does_not_fire_on_that_same_setup():
    """The two detectors genuinely disagree -- which is why both exist."""
    bars = [_touch(_t(0)), _bar(_t(1), 91.0, 97.0, 96.0)]
    assert all(r is None for r in detect_index(bars))


def test_a_wick_through_the_reference_high_is_not_a_trigger():
    bars = [_touch(_t(0)),                        # ref high 95
            _bar(_t(1), 90.0, 99.0, 94.0),        # pokes 99, closes 94
            _bar(_t(2), 92.0, 97.0, 96.0)]        # closes 96 -> trigger
    out = detect_index_run(bars)
    assert out[1] is None
    assert out[2] is not None and out[2]["waited"] == 2


def test_a_close_exactly_at_the_reference_high_does_not_trigger():
    bars = [_touch(_t(0)), _bar(_t(1), 90.0, 96.0, 95.0)]
    assert detect_index_run(bars)[1] is None


def test_a_touch_needs_the_low_to_reach_the_band():
    """86 never reaches d3 85, so nothing ever arms."""
    bars = [_bar(_t(0), 86.0, 95.0, 87.0), _bar(_t(1), 91.0, 97.0, 96.0)]
    assert all(r is None for r in detect_index_run(bars))


# -- 2. the reference walks down with the move -----------------------------

def test_a_new_lower_low_moves_the_reference():
    bars = [_touch(_t(0), high=95.0),             # ref high 95
            _bar(_t(1), 80.0, 90.0, 82.0),        # lower low -> ref high 90
            _bar(_t(2), 85.0, 92.0, 91.0)]        # 91 > 90, but < 95
    rec = detect_index_run(bars)[2]
    assert rec is not None, "must trigger off the NEW reference, not the old"
    assert rec["ref_i"] == 1 and rec["ref_high"] == 90.0


def test_a_falling_run_is_one_setup_not_a_stack_of_them():
    bars = [_touch(_t(0)),
            _bar(_t(1), 80.0, 93.0, 81.0),
            _bar(_t(2), 76.0, 91.0, 77.0),
            _bar(_t(3), 88.0, 95.0, 92.0)]        # 92 > 91 -> one trigger
    out = detect_index_run(bars)
    assert [i for i, r in enumerate(out) if r] == [3]
    assert out[3]["ref_i"] == 2


def test_a_lower_low_restarts_the_countdown():
    """Assumption flagged in §5c, locked here so it cannot drift silently."""
    W = band_rotation.RUN_WINDOW
    # The re-armed reference must sit ABOVE the inert bars' close (91), or they
    # would trigger it themselves and the window would never be exercised.
    bars = [_touch(_t(0)),
            _bar(_t(1), 80.0, 93.0, 82.0)]        # ref moves to index 1
    while len(bars) < 1 + W:
        bars.append(_inert(_t(len(bars))))
    bars.append(_bar(_t(1 + W), 88.0, 96.0, 94.0))  # exactly W bars after
    out = detect_index_run(bars)
    assert out[1 + W] is not None and out[1 + W]["ref_i"] == 1
    assert out[1 + W]["waited"] == W


# -- 3. the window ---------------------------------------------------------

def test_a_trigger_on_the_last_bar_of_the_window_still_counts():
    W = band_rotation.RUN_WINDOW
    bars = [_touch(_t(0))] + [_inert(_t(i)) for i in range(1, W)]
    bars.append(_bar(_t(W), 88.0, 97.0, 96.0))
    out = detect_index_run(bars)
    assert out[W] is not None and out[W]["waited"] == W


def test_one_bar_past_the_window_is_too_late():
    W = band_rotation.RUN_WINDOW
    bars = [_touch(_t(0))] + [_inert(_t(i)) for i in range(1, W + 1)]
    bars.append(_bar(_t(W + 1), 88.0, 97.0, 96.0))
    assert all(r is None for r in detect_index_run(bars))


# -- 4. the 09:25 gate -----------------------------------------------------

def test_a_touch_before_0925_does_not_arm():
    early = 9 * 60 + 15
    bars = [_touch(_t(0, base=early)),                        # 09:15
            _bar(_t(1, base=early), 91.0, 97.0, 96.0)]        # 09:18
    assert all(r is None for r in detect_index_run(bars))


def test_a_bar_with_no_clock_label_does_not_arm():
    b0 = _touch(_t(0))
    b0.pop("t")
    bars = [b0, _bar(_t(1), 91.0, 97.0, 96.0)]
    assert all(r is None for r in detect_index_run(bars))


# -- 5. the re-fire lock ---------------------------------------------------

def _entry_then(*rest):
    """A completed entry (indices 0-1) followed by whatever `rest` supplies."""
    return [_touch(_t(0)), _bar(_t(1), 91.0, 97.0, 96.0), *rest]


def test_a_second_setup_is_suppressed_until_vwap_is_touched():
    bars = _entry_then(_touch(_t(2)), _bar(_t(3), 91.0, 97.0, 96.0))
    out = detect_index_run(bars)
    assert out[1] is not None
    assert out[3] is None, "still in the trade -- VWAP was never reached"


def test_touching_vwap_unlocks_the_next_setup():
    bars = _entry_then(_bar(_t(2), 95.0, VWAP, 99.0),   # high reaches VWAP
                       _touch(_t(3)),
                       _bar(_t(4), 91.0, 97.0, 96.0))
    out = detect_index_run(bars)
    assert out[1] is not None and out[4] is not None


def test_a_known_stop_unlocks_immediately_when_it_is_hit():
    """'Stopped out -> arm immediately.' The stop-out bar dives through d3, so
    it both releases the lock AND becomes the next reference in the same pass;
    its high is then the level to beat."""
    stop = D3 - 20.0                                   # 65.0
    tail = (_bar(_t(2), stop - 1.0, 80.0, 70.0),       # low 64 <= stop 65
            _bar(_t(3), 75.0, 85.0, 81.0))             # 81 > 80 -> fires
    out = detect_index_run(_entry_then(*tail), stop_pts=20.0)
    assert out[3] is not None and out[3]["ref_i"] == 2
    # Without a stop the lock is VWAP-only, and nothing here reaches VWAP, so
    # the same bars stay silent -- suppression, never an invented signal.
    assert all(r is None for r in detect_index_run(_entry_then(*tail))[2:])


# -- 6. the one-candle path is untouched -----------------------------------

def test_the_old_detector_still_fires_its_own_rule():
    bars = [_bar(_t(0), 84.0, 101.0, 100.0)]           # pierces d3, closes above
    rec = detect_index(bars)[0]
    assert rec is not None and rec["side"] == "BUY" and rec["band"] == "d3"
    assert "the same bar closed" in rec["trigger"]


def test_the_two_receipts_can_never_be_confused():
    """trigger_log.py parses the one-candle sentence; the new one must not
    look like it."""
    old = detect_index([_bar(_t(0), 84.0, 101.0, 100.0)])[0]["trigger"]
    new = detect_index_run([_touch(_t(0)),
                            _bar(_t(1), 91.0, 97.0, 96.0)])[1]["trigger"]
    assert "the same bar closed" in old
    assert "the same bar closed" not in new
    assert "above that candle's high" in new


def test_an_index_run_signal_is_never_confirmed_and_says_why():
    rec = detect_index_run([_touch(_t(0)), _bar(_t(1), 91.0, 97.0, 96.0)])[1]
    assert rec["confirm"] == "UNKNOWN"
    assert rec["confirm_why"] == band_rotation.SINGLE_SERIES_CONFIRM_WHY
    assert rec["leg"] == band_rotation.INDEX_LEG


# -- 7. shape and junk -----------------------------------------------------

def test_records_are_one_slot_per_bar_and_aligned():
    bars = [_inert(_t(i)) for i in range(6)]
    bars[2] = _touch(_t(2))
    bars[3] = _bar(_t(3), 91.0, 97.0, 96.0)
    out = detect_index_run(bars)
    assert len(out) == len(bars)
    assert out[3]["i"] == 3 and out[3]["t"] == _t(3)


def test_a_session_boundary_clears_a_live_reference():
    bars = [_touch(_t(0)), _bar(_t(1), 91.0, 97.0, 96.0)]
    days = ["2026-08-04", "2026-08-05"]
    assert all(r is None for r in detect_index_run(bars, days=days))


def test_a_missing_band_does_not_arm():
    b0 = _touch(_t(0))
    b0["d3"] = None
    bars = [b0, _bar(_t(1), 91.0, 97.0, 96.0)]
    assert all(r is None for r in detect_index_run(bars))


def test_junk_input_never_raises():
    assert detect_index_run(None) == []
    assert detect_index_run([]) == []
    assert detect_index_run("nope") == []
    assert detect_index_run([None, 3, "x"]) == [None, None, None]


def test_a_null_bar_keeps_its_slot():
    bars = [_touch(_t(0)), None, _bar(_t(2), 91.0, 97.0, 96.0)]
    out = detect_index_run(bars)
    assert len(out) == 3 and out[1] is None
    assert out[2] is not None and out[2]["ref_i"] == 0
