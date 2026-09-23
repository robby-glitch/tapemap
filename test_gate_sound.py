"""signals.gate_sound -- the fade gate on the face (§1d). One case per policy line."""
import signals

CE_UNW = {"side": "CE", "k": 23400.0, "state": "UNWINDING", "peak_at": "10:15"}
CE_STL = {"side": "CE", "k": 23400.0, "state": "STALLED", "peak_at": "10:15"}
CE_BLD = {"side": "CE", "k": 23400.0, "state": "BUILDING", "peak_at": "11:20"}
LEGAL = {"legal": True, "veto": False, "front": CE_BLD, "why": "CE 23400 still building"}
ILLEGAL = {"legal": False, "veto": False, "front": CE_UNW, "why": "CE 23400 gave up its build at 10:15"}
STALLED = {"legal": False, "veto": False, "front": CE_STL, "why": "CE 23400 stopped building at 10:15"}
VETO = {"legal": False, "veto": True, "front": CE_BLD, "why": "engine says NO FADE"}
UNKNOWN = {"legal": None, "veto": None, "front": None, "why": "near-ATM fronts not read"}


def tap(sound="soft"):
    return {"side": "sell", "state": "ARMED", "sound": sound, "mute_why": None if sound else "x", "fired_at": None}


def trig(sound="firm"):
    return {"side": "sell", "state": "LIVE", "sound": sound, "mute_why": None, "fired_at": "11:15"}


def test_tap_follows_the_gate():
    assert signals.gate_sound(tap(), LEGAL)["sound"] == "soft"
    out = signals.gate_sound(tap(), ILLEGAL)
    assert out["sound"] is None and out["sound_ungated"] == "soft"
    assert out["mute_why"] == "no fade · CE 23400 unwinding 10:15"
    assert out["gate"]["legal"] is False
    assert out["gate"]["note"] == "CE writers covering — ceiling not defended"
    assert len(out["gate"]["label"]) <= 40
    unk = signals.gate_sound(tap(), UNKNOWN)
    assert unk["sound"] == "soft" and unk["gate"]["legal"] is None   # a blind gate never silences


def test_veto_reads_as_the_engine():
    out = signals.gate_sound(tap(), VETO)
    assert out["sound"] is None and "NO FADE" in out["mute_why"] and out["gate"]["note"] is None


def test_trigger_needs_a_legal_gate_to_be_firm():
    assert signals.gate_sound(trig(), LEGAL, g_reach=LEGAL, g_fire=LEGAL)["sound"] == "firm"
    assert signals.gate_sound(trig(), UNKNOWN, g_reach=LEGAL, g_fire=UNKNOWN)["sound"] == "soft"
    # illegal at the trigger: silent -- unless the tap was legal and already rang
    assert signals.gate_sound(trig(), ILLEGAL, g_reach=ILLEGAL, g_fire=ILLEGAL)["sound"] is None
    warn = signals.gate_sound(trig(), ILLEGAL, g_reach=LEGAL, g_fire=ILLEGAL)
    assert warn["sound"] == "warn" and warn["gate"]["label"].startswith("stand down")


def test_in_trade_reason_gone_warns_once_stall_only_notes():
    gone = signals.gate_sound(trig(), ILLEGAL, g_reach=LEGAL, g_fire=LEGAL)
    assert gone["sound"] == "warn" and gone["gate"]["label"].startswith("reason gone")
    vetoed = signals.gate_sound(trig(), VETO, g_reach=LEGAL, g_fire=LEGAL)
    assert vetoed["sound"] == "warn"
    stall = signals.gate_sound(trig(), STALLED, g_reach=LEGAL, g_fire=LEGAL)
    assert stall["sound"] == "firm" and "watch it" in stall["gate"]["note"]


def test_the_gate_never_unmutes():
    out = signals.gate_sound(tap(None), LEGAL)
    assert out["sound"] is None and out["mute_why"] == "x"
    assert signals.gate_sound(trig(None), ILLEGAL, g_reach=LEGAL, g_fire=LEGAL)["sound"] is None


def test_banknifty_never_rings_firm():
    out = signals.gate_sound(trig(), LEGAL, g_reach=LEGAL, g_fire=LEGAL, idx="BANKNIFTY")
    assert out["sound"] == "soft" and "BNF" in out["gate"]["caveat"]


def test_mute_why_is_set_exactly_when_sound_is_null():
    for s, g, r, f in [(tap(), ILLEGAL, None, None), (tap(), LEGAL, None, None),
                       (trig(), ILLEGAL, ILLEGAL, ILLEGAL), (trig(), LEGAL, LEGAL, LEGAL)]:
        out = signals.gate_sound(s, g, g_reach=r, g_fire=f)
        assert (out["sound"] is None) == (out["mute_why"] is not None)


def test_the_tap_reads_its_own_bar_not_the_live_flicker():
    # legal at the tap bar, illegal now: the tap stays what it was (soft, full mark) and says so
    out = signals.gate_sound(tap(), ILLEGAL, g_reach=LEGAL)
    assert out["sound"] == "soft" and out["gate"]["legal"] is True
    assert "a trigger would stand down" in out["gate"]["note"]
    assert out["gate"]["reach"]["legal"] is True and out["gate"]["fire"] is None   # handed back to freeze


def test_frame_freezes_the_tap_gate_for_the_visit():
    """frame.build reuses the previous frame's frozen tap gate for the SAME visit
    (book['signal_prior']) and never for another visit."""
    import frame
    from test_frame_zone import _tape, _machine
    tape = _tape("2026-09-11", "09:45")
    book = {"zone_state": _machine(tape), "senses": {"confirm": "UNKNOWN"}}
    s1 = frame.build(tape, book, "09:45")["setup"]["signal"]
    assert s1["visit_key"] and s1["gate"] is not None and "sound_ungated" in s1
    frozen = {"legal": False, "why": "frozen at the tap", "veto": False, "front": None, "final": True}
    prior = dict(s1, gate={**s1["gate"], "reach": frozen, "fire": None})
    s2 = frame.build(tape, dict(book, signal_prior=prior), "09:45")["setup"]["signal"]
    assert s2["gate"]["reach"]["why"] == "frozen at the tap"
    if not s2.get("fired_at"):
        assert s2["gate"]["legal"] is False and s2["sound"] is None
    s3 = frame.build(tape, dict(book, signal_prior=dict(prior, visit_key="another visit")), "09:45")["setup"]["signal"]
    assert s3["gate"]["reach"]["why"] != "frozen at the tap"
    # a read taken before the bar's last minute reached the grid is NOT final and is never reused
    unsettled = dict(s1, gate={**s1["gate"], "reach": dict(frozen, final=False), "fire": None})
    s4 = frame.build(tape, dict(book, signal_prior=unsettled), "09:45")["setup"]["signal"]
    assert s4["gate"]["reach"]["why"] != "frozen at the tap"


def test_a_bars_own_veto_decides_its_gate_not_todays_latest_plays():
    """The restart blocker: a tap's gate uses THAT bar's engine plays (book['plays_at'],
    the ctx trigger_log stamps from), so a veto that has since aged out of the latest
    bar can never re-read the tap as legal -- and the read is final once the grid holds
    the bar's last minute."""
    import frame
    from test_frame_zone import _tape, _machine
    from test_fronts import _grid, _ramp, TIMES
    tape = _tape("2026-09-11", "09:45")                        # a buy visit reached at 09:25
    n = len(TIMES)
    grid = _grid(TIMES, 23300.0, {23300.0: (_ramp(0, 300, n), _ramp(0, 300, n))})   # PE defender building
    base = {"zone_state": _machine(tape), "minutes": grid, "plays": []}               # latest bar: no veto
    veto = frame.build(tape, dict(base, plays_at={"09:25": ["NO FADE at 23290 - negative gamma; "
                                                          "continuation only"]}), "09:45")["setup"]["signal"]["gate"]
    assert veto["reach"]["legal"] is False and veto["reach"]["veto"] is True and veto["reach"]["final"] is True
    clean = frame.build(tape, dict(base, plays_at={"09:25": []}), "09:45")["setup"]["signal"]["gate"]
    assert clean["reach"]["legal"] is True and clean["reach"]["final"] is True
    # the bar missing from plays_at (not yet closed on the 3-min payload): read, but never frozen
    assert frame.build(tape, base, "09:45")["setup"]["signal"]["gate"]["reach"]["final"] is False
