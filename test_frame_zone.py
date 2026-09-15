# tapemap/test_frame_zone.py
"""2026-09-11 09:45: the tape's −3.19σ tap on the futures, pinned against the
real machine only -- the flow half (absorption/exhaustion/trap) is supplied
explicitly here rather than re-derived, because the tape's own absorption
detector lives in the extension (board.js, tested in test/engine.mjs), not
in this repo. 2026-09-09 14:10 (the mid-range long that lost 85 points) must
read WAITING and never fire, flow present or not. Regression fixtures, not
targets: nothing here is tuned; the assertions follow from the rule as
written. Pinned against frame.build(...)["setup"] (spec §C + §E) -- the old
zone() block is gone, but every case it protected still must hold."""
import json
import os

import band_rotation
import frame

FIX = r"C:\Users\kaam\Desktop\Go charting\orderflow-desk\test"


def _tape(day, upto_hhmm):
    j = json.load(open(os.path.join(FIX, f"session-{day}.ofd.json"), encoding="utf-8"))
    bars = sorted(j["bars"], key=lambda b: b["t"])
    bars = [b for b in bars if frame._hhmm(b["t"]) <= upto_hhmm]
    pv = pv2 = vv = 0.0; bands = []
    for b in bars:
        tp = (b["h"] + b["l"] + b["c"]) / 3; pv += tp * b["vol"]; pv2 += tp * tp * b["vol"]; vv += b["vol"]
        m = pv / vv; s = max(0.0, pv2 / vv - m * m) ** 0.5
        bands.append({"t": b["t"], "vwap": m, "sigma": s, "u1": m + s, "d1": m - s, "u2": m + 2 * s, "d2": m - 2 * s, "u3": m + 3 * s, "d3": m - 3 * s})
    return {"kind": "frame", "session": f"NIFTY-I|5m|{day}", "idx": "NIFTY", "interval": 5, "rowSize": 5,
            "futPx": bars[-1]["c"], "closed": bars, "forming": None, "bands": bands, "walls": [], "broke": [],
            "events": [], "taps": []}


def _machine(tape):
    # `_index_bar` (band_rotation.py:731) passes a flat bar through unchanged,
    # and `run_states`/`_run_read` (band_rotation.py:893-900, 1050) key off
    # LOWERCASE t/l/h/c/vwap plus the band by its own lowercase name ("d2") --
    # the brief's upper-case keys are what `_index_bar`'s DAY-ROW `fut` shape
    # documents, not what a FLAT row is read as. Extending, not replacing: the
    # upper-case keys still ride along for any reader that wants them.
    bars = [{"T": frame._hhmm(b["t"]), "O": b["o"], "H": b["h"], "L": b["l"], "C": b["c"], "V": b["vol"],
             **{k.upper(): v for k, v in bd.items() if k != "t"},
             "t": frame._hhmm(b["t"]), "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "vol": b["vol"],
             **{k: v for k, v in bd.items() if k != "t"}} for b, bd in zip(tape["closed"], tape["bands"])]
    return band_rotation.run_states(bars, stop_pts=band_rotation.OPERATOR_STOP_PTS, band="d2")


def _machine_sell(tape):
    """The mirror of `_machine`: same flat-bar shape, the SELL side, armed at
    the near edge (u2) per C2 / spec §6."""
    bars = [{"T": frame._hhmm(b["t"]), "O": b["o"], "H": b["h"], "L": b["l"], "C": b["c"], "V": b["vol"],
             **{k.upper(): v for k, v in bd.items() if k != "t"},
             "t": frame._hhmm(b["t"]), "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "vol": b["vol"],
             **{k: v for k, v in bd.items() if k != "t"}} for b, bd in zip(tape["closed"], tape["bands"])]
    return band_rotation.run_states(bars, stop_pts=band_rotation.OPERATOR_STOP_PTS, side="SELL", band="u2")


def _with_absorption(tape):
    """The flow half, supplied: the tape's absorption detector lives in the
    extension (board.js, tested in test/engine.mjs). setup() only asks whether
    an absorption/exhaustion/trap event sits within 3 rows of the zone edge."""
    last = tape["closed"][-1]
    return dict(tape, events=[{"t": last["t"], "kind": "absorption", "side": 1, "p": last["l"], "size": None}])


def test_0911_0945_is_armed_at_the_tap_by_the_rule():
    tape = _tape("2026-09-11", "09:45")
    S = frame.build(tape, {"zone_state": _machine(tape), "senses": {"confirm": "UNKNOWN"}}, "09:45")["setup"]
    assert S["state"] in ("ARMED", "TRIGGERED"), S["state"]
    assert S["reached"] is True and S["fire"] is False and S["flow"] == []   # zone alone never fires
    # setup.ref (was ref_high pre-Task-1-review): the arming bar's high, live off the real machine
    assert S["ref"] == 23314.0 and S["candles_left"] == 10


def test_0911_0945_fires_only_when_flow_is_supplied_at_the_zone():
    tape = _with_absorption(_tape("2026-09-11", "09:45"))
    S = frame.build(tape, {"zone_state": _machine(tape), "senses": {"confirm": "UNKNOWN"}}, "09:45")["setup"]
    assert S["reached"] and any(f["kind"] == "absorption" for f in S["flow"]) and S["fire"] is True and S["visit"]
    S2 = frame.build(tape, {"zone_state": _machine(tape), "senses": {"confirm": "UNCONFIRMED"}}, "09:45")["setup"]
    assert S2["fire"] is False, "a chain UNCONFIRMED vetoes the beep even with tape flow present"


def test_0911_0945_a_flow_event_four_rows_away_is_not_flow():
    """The flow check is 3 rows either side of the edge (rowSize=5 here): an
    absorption print 4 rows (20 pts) off the armed level must not count, so
    the zone reads ARMED with no flow rather than firing."""
    tape = _tape("2026-09-11", "09:45")
    book = {"zone_state": _machine(tape), "senses": {"confirm": "UNKNOWN"}}
    level = frame.build(tape, book, "09:45")["setup"]["level"]
    last = tape["closed"][-1]
    far = dict(tape, events=[{"t": last["t"], "kind": "absorption", "side": 1, "p": level + 4 * tape["rowSize"], "size": None}])
    S = frame.build(far, book, "09:45")["setup"]
    assert S["flow"] == [] and S["fire"] is False


def test_0909_1410_is_waiting_and_never_fires_even_with_flow():
    tape = _with_absorption(_tape("2026-09-09", "14:10"))
    S = frame.build(tape, {"zone_state": _machine(tape), "senses": {"confirm": "UNKNOWN"}}, "14:10")["setup"]
    assert S["state"] == "WAITING" and S["reached"] is False and S["fire"] is False


def test_0911_1345_the_sell_machine_is_chosen_and_active_by_the_rule():
    """C2's mirror of test_0911_0945_is_armed_at_the_tap_by_the_rule. The
    handoff's trigger_log records a SELL rearm at 14:03 on the 3-minute feed
    (extreme 23517.4); on this 5-minute fixture the same leg reads ARMED at
    11:10, TRIGGERED at 12:00, IN_TRADE from 12:05 -- and by the rule it is
    still IN_TRADE straight through the bar the task named (13:45) and the
    whole 13:35-13:55 window (the next rearm is 14:00, just outside it):

        13:35 IN_TRADE
        13:40 IN_TRADE
        13:45 IN_TRADE
        13:50 IN_TRADE
        13:55 IN_TRADE

    So the bar the task expected either WAITING or ARMED/TRIGGERED is
    actually the third state C2's own selection rule treats as "the sell
    machine is active" (ARMED/TRIGGERED/IN_TRADE). The buy machine (d2)
    reads WAITING for the same window (verified directly), so C2's tie-break
    -- "sell if in_sell or the sell machine is ARMED/TRIGGERED/IN_TRADE and
    the buy machine is not" -- picks sell on that clause alone; in_sell is
    False at 13:45 (fut is nowhere near u2). The assertion below follows
    that rule as written, not a nudge to force ARMED."""
    tape = _tape("2026-09-11", "13:45")
    book = {"zone_state": _machine(tape), "zone_state_sell": _machine_sell(tape), "senses": {"confirm": "UNKNOWN"}}
    S = frame.build(tape, book, "13:45")["setup"]
    assert S["state"] == "IN_TRADE"
    assert S["state"] in ("ARMED", "TRIGGERED", "IN_TRADE")   # C2's own "active" set
    assert S["reached"] is True
    assert S["side"] == "sell", "the sell machine, not the buy one, must be chosen"


def test_0911_visit_id_is_stable_across_bars_of_the_same_armed_reference():
    """visit must not change every bar just because the last-closed-bar time
    moved -- the extension beeps once per distinct visit. 09:45 and 09:50 are
    both ARMED off the SAME reference bar (ref_i=6, the 09:25 setup's latest
    rearm; verified directly against band_rotation.run_states), so their
    visit ids must be equal. The 2026-09-11 fixture only ever arms one setup
    all day (one rearming reference from 09:25 to the 09:55 TRIGGERED, then
    WAITING for the rest of the session) -- there is no second, separately
    armed touch in this fixture to assert a difference against, so this test
    only asserts the equality, as the task allows."""
    t945 = _tape("2026-09-11", "09:45")
    t950 = _tape("2026-09-11", "09:50")
    S945 = frame.build(t945, {"zone_state": _machine(t945), "senses": {"confirm": "UNKNOWN"}}, "09:45")["setup"]
    S950 = frame.build(t950, {"zone_state": _machine(t950), "senses": {"confirm": "UNKNOWN"}}, "09:50")["setup"]
    assert S945["state"] == "ARMED" and S950["state"] == "ARMED"
    assert S945["visit"] == S950["visit"]


def test_0911_visit_is_the_earliest_bar_of_a_contiguous_d2_touch_run_before_arming():
    """Before the machine has armed a reference (state PATA NAHI / not yet
    active), a live d2 touch still needs a stable visit id: it anchors on the
    EARLIEST bar of the contiguous run of bars touching d2, not the latest,
    so the id does not drift bar to bar while the touch is still running.
    Built directly off the bands rather than the real machine, since this
    exercises the pre-arm fallback path specifically (no zone_state at all)."""
    tape = _tape("2026-09-11", "09:45")
    closed, bands = tape["closed"], tape["bands"]
    lvl = bands[-1]["d2"]
    # force the last two bars to be touching d2 (a contiguous run), the ones before not
    for i in (-2, -1):
        closed[i] = dict(closed[i], l=lvl - 1.0)
        bands[i] = dict(bands[i], d2=lvl)
    closed[-3] = dict(closed[-3], l=lvl + 50.0)
    tape = dict(tape, futPx=lvl, closed=closed, bands=bands)
    S = frame.build(tape, {"senses": {"confirm": "UNKNOWN"}}, "09:45")["setup"]
    assert S["reached"] is True and S["visit"] == f"buy@{frame._hhmm(closed[-2]['t'])}"


def test_when_both_machines_are_active_the_more_recent_arm_is_the_setup_and_sell_wins_ties():
    tape = _tape("2026-09-11", "13:45")
    buy = [{"state": "ARMED", "ref_i": 10, "ref_high": 23400.0, "level": 23390.0, "candles_left": 5}]
    sell = [{"state": "ARMED", "ref_i": 40, "ref_high": 23520.0, "level": 23530.0, "candles_left": 5}]
    S = frame.build(tape, {"zone_state": buy, "zone_state_sell": sell, "senses": None}, "13:45")["setup"]
    assert S["side"] == "sell"
    S2 = frame.build(tape, {"zone_state": [dict(buy[0], ref_i=50)], "zone_state_sell": sell, "senses": None}, "13:45")["setup"]
    assert S2["side"] == "buy"
    S3 = frame.build(tape, {"zone_state": [dict(buy[0], ref_i=40)], "zone_state_sell": sell, "senses": None}, "13:45")["setup"]
    assert S3["side"] == "sell", "exact tie goes to sell"
