# tapemap/test_watch.py
"""watch.py: the watch list (spec §B). Synthetic ladder and machines.

Nothing here is an entry, and the tests assert that as hard as they assert
the promotion rules -- a row that grew a `side` or a `target` would be the
failure mode §H.1 names.
"""
import pytest

import watch


def _row(kind, p, **kw):
    r = {"kind": kind, "p": float(p), "d": None, "size": None, "since": None,
         "leaned": None, "snapshot": False, "oi": None, "chg": None, "pain": None,
         "pain_tag": None, "conf": None, "state": None, "tests": None,
         "last_outcome": None, "strike": None, "agree": None}
    r.update(kw)
    return r


def _ladder():
    return [
        _row("CE", 23300.0, strike=23270.0, oi=2.21e7, chg=4.3e6, pain=6.2,
             pain_tag="I", conf="session", agree="B 23300", state="held"),
        _row("B", 23300.0, size=600, leaned=3, since="10:02", agree="CE 23270",
             state="held"),
        _row("PE", 23250.0, strike=23220.0, oi=1.84e7, chg=-2.0e6, pain=0.0,
             pain_tag="I", conf="session", state="held"),
        _row("PDH", 23400.0, state="APPROACH", tests=2, last_outcome="REJECT"),
        _row("ROUND", 23450.0, state="IDLE"),
        _row("S", 26000.0, size=100, leaned=1, since="09:30", state="held"),
    ]


def _dwell(px=23300.0, held_s=240):
    return {"active": False, "holding": True, "level": {"kind": "CE", "px": px},
            "held_s": held_s, "band": 12.5, "tag": "I"}


def _sequence():
    return {"PDH@23400.0": {"state": "APPROACH", "kind": "PDH", "px": 23400.0,
                            "tests": 2, "last_outcome": "REJECT", "target": None},
            "ROUND@23450.0": {"state": "IDLE", "kind": "ROUND", "px": 23450.0,
                              "tests": 0, "last_outcome": None, "target": None}}


def _runways():
    return {"ok": True, "tag": "I", "richer": "UP",
            "up": {"target": {"kind": "PDH", "px": 23400.0}, "dist": 100.0,
                   "fuel": 41200000, "per_point": 412000, "items": [],
                   "stop_zone": {"lo": 23412.5, "hi": 23425.0, "tag": "I",
                                 "basis": "inferred"}, "why": "x"},
            "down": {"target": None, "fuel": None, "per_point": None, "items": [],
                     "why": "no known level in this direction within the map"}}


def _minutes():
    return {"12:45": {"spot": 23200.0, "k": {23270: (1.0e6, 0.0), 23220: (0.0, 2.0e6)},
                      "px": {23270: (80.0, 40.0), 23220: (30.0, 90.0)}},
            "12:52": {"spot": 23240.0, "k": {23270: (3.0e6, 0.0), 23220: (0.0, 1.0e6)},
                      "px": {23270: (70.0, 45.0), 23220: (28.0, 95.0)}},
            "13:00": {"spot": 23270.0, "k": {23270: (4.3e6, 0.0), 23220: (0.0, 0.8e6)},
                      "px": {23270: (65.0, 50.0), 23220: (25.0, 99.0)}}}


def _peaks():
    return {(23270, "ce"): 2.4e7, (23220, "pe"): 1.9e7}


def _build(**kw):
    # sigma 150 -> a radius of 225 points, which reaches the PDH at 23400 and
    # the ROUND at 23450 and does not reach the 26000 wall.
    a = dict(walls_rows=_ladder(), spot=23240.0, sigma=150.0, basis=30.0,
             dwell=_dwell(), sequence=_sequence(), seq_fired=[],
             runways=_runways(), minutes=_minutes(), peaks=_peaks(), prior=None)
    a.update(kw)
    return watch.build(**a)


def test_the_header_is_permanent_and_says_it_is_not_an_entry():
    w = _build()
    assert w["note"] == watch.NOTE
    assert "none of these is an entry" in watch.NOTE


def test_no_row_carries_a_side_a_direction_or_a_target():
    w = _build()
    for r in w["rows"] + (w["broken"] or []):
        for banned in ("side", "direction", "dir", "target", "entry", "stop_px"):
            assert banned not in r, f"{banned} on a watched row is §H.1 broken"


def test_a_row_outside_one_and_a_half_sigma_is_not_watched():
    """The radius scales with the day: sigma, never a fixed point count."""
    w = _build()
    assert all(abs(r["p"] - 23240.0) <= watch.RADIUS_SIGMA * 150.0 for r in w["rows"])
    assert 26000.0 not in [r["p"] for r in w["rows"]]


def test_every_row_names_what_promoted_it():
    w = _build()
    assert w["rows"], "the ladder has promotable rows"
    for r in w["rows"]:
        assert r["promoted_by"] in ("agree", "sequence", "leaned", "oi_top3")


def test_agree_is_always_watched_and_flagged():
    w = _build()
    r = next(r for r in w["rows"] if r["kind"] == "CE" and r["p"] == 23300.0)
    assert r["promoted_by"] == "agree" and "AGREE" in r["flags"]


def test_a_level_the_machine_is_engaging_is_watched_and_an_idle_one_is_not():
    """Both are inside the radius; APPROACH means price is engaging the PDH
    and IDLE means the ROUND is just a number on a chart."""
    w = _build()
    ps = [r["p"] for r in w["rows"]]
    assert 23400.0 in ps and 23450.0 not in ps


def test_held_dwell_fuel_and_closing_are_flags_and_no_number_is_summed():
    w = _build()
    pdh = next(r for r in w["rows"] if r["p"] == 23400.0)
    assert "HELD" in pdh["flags"] and pdh["tests"] == 2
    assert pdh["fuel"] == 41200000 and pdh["fuel_tag"] == "I" and "FUEL" in pdh["flags"]
    assert pdh["stop_zone"] == 23412.5
    ce = next(r for r in w["rows"] if r["kind"] == "CE")
    assert "DWELL" in ce["flags"] and ce["dwell_min"] == 4
    assert "CLOSING" in ce["flags"] and ce["closing_pts_min"] is not None
    for r in w["rows"]:
        assert "danger" not in r and "score" not in r


def test_the_list_is_ordered_by_how_many_flags_are_met_and_the_count_is_not_printed():
    w = _build()
    counts = [len(r["flags"]) for r in w["rows"]]
    assert counts == sorted(counts, reverse=True)
    for r in w["rows"]:
        assert "flag_count" not in r and "n_flags" not in r


def test_the_cap_is_eight_and_shown_says_how_many_got_through():
    rows = _ladder() + [_row("B", 23240.0 + i, size=500, leaned=3, since="10:00",
                             state="held") for i in range(12)]
    w = _build(walls_rows=rows)
    assert w["cap"] == 8 and len(w["rows"]) == 8 and w["shown"] == 8


def test_an_empty_list_says_which_of_the_two_silences_it_is():
    w = _build(walls_rows=[])
    assert w["rows"] == [] and w["why"] == "the war map did not answer"
    w2 = _build(walls_rows=[_row("S", 26000.0, size=100, leaned=1, state="held")])
    assert w2["rows"] == [] and w2["why"] == "no ladder row within 1.5\u03c3 of spot"
    assert w["why"] != w2["why"], "two silences, never one sentence"


def test_a_broken_level_stays_on_screen_with_its_peak_and_its_break_minute():
    fired = [{"level": "PE", "px": 23250.0, "from": "DWELL", "to": "BREAK",
              "spot": 23241.0, "band": 12.5, "direction": "DOWN",
              "ts": "2026-09-18T11:03:07"},
             {"level": "PE", "px": 23250.0, "from": "BREAK", "to": "RUN",
              "spot": 23241.0, "band": 12.5,
              "target": {"kind": "ROUND", "px": 23150.0},
              "ts": "2026-09-18T11:03:07"}]
    w = _build(seq_fired=fired)
    b = next(b for b in w["broken"] if b["p"] == 23250.0)
    assert b["broke_at"] == "11:03" and b["broke_spot"] == 23241.0
    assert b["target_named"] == 23150.0 and b["role"] is None
    assert b["peak_oi"] == 1.9e7 and b["peak_at"] == "12:45" and b["peak_spot"] == 23200.0
    assert 0.5 < b["unwound_frac"] < 0.7


def test_a_broken_level_is_never_deleted_mid_session_and_re_enters_as_flipped():
    fired = [{"level": "PE", "px": 23250.0, "from": "DWELL", "to": "BREAK",
              "spot": 23241.0, "band": 12.5, "direction": "DOWN",
              "ts": "2026-09-18T11:03:07"}]
    w1 = _build(seq_fired=fired)
    w2 = _build(seq_fired=[], prior=w1)           # the break is not re-fired
    assert [b["p"] for b in w2["broken"]] == [23250.0]
    seq = dict(_sequence(), **{"PE@23250.0": {"state": "APPROACH", "kind": "PE",
                                              "px": 23250.0, "tests": 3,
                                              "last_outcome": "REJECT",
                                              "target": None}})
    w3 = _build(seq_fired=[], prior=w2, sequence=seq)
    assert next(b for b in w3["broken"] if b["p"] == 23250.0)["role"] == "flipped"


def test_a_level_that_broke_before_this_process_started_is_restored_and_tagged():
    # warmap._try_seed replays the morning through fresh machines and hands
    # its transitions over; a 13:00 start must still show the 11:03 break.
    replayed = [{"level": "PE", "px": 23250.0, "from": "DWELL", "to": "BREAK",
                 "spot": 23241.0, "band": 12.5, "direction": "DOWN",
                 "ts": "2026-09-18T11:03:07", "backfill": True, "src": "rest_1m"},
                {"level": "PE", "px": 23250.0, "from": "BREAK", "to": "RUN",
                 "spot": 23241.0, "band": 12.5,
                 "target": {"kind": "ROUND", "px": 23150.0},
                 "ts": "2026-09-18T11:03:07", "backfill": True, "src": "rest_1m"}]
    w = _build(seq_fired=[], seq_fired_backfill=replayed)
    b = next(b for b in w["broken"] if b["p"] == 23250.0)
    assert b["src"] == "restored", "a rebuilt break must never look live"
    assert b["broke_at"] == "11:03" and b["target_named"] == 23150.0
    assert w["broken_why"] is None, "a listed break needs no sentence"


def test_a_live_break_is_never_restated_as_a_reconstruction_of_itself():
    live = [{"level": "PE", "px": 23250.0, "from": "DWELL", "to": "BREAK",
             "spot": 23241.0, "band": 12.5, "ts": "2026-09-18T13:20:05"}]
    replayed = [{"level": "PE", "px": 23250.0, "from": "DWELL", "to": "BREAK",
                 "spot": 23244.0, "band": 12.5, "ts": "2026-09-18T11:03:07",
                 "backfill": True, "src": "rest_1m"}]
    w = _build(seq_fired=live, seq_fired_backfill=replayed)
    got = [b for b in w["broken"] if b["p"] == 23250.0]
    assert len(got) == 1 and got[0]["src"] == "live"
    assert got[0]["broke_at"] == "13:20", "the observation stands, not the rebuild"


def test_nothing_broken_is_never_a_silent_zero_and_says_which_silence_it_is():
    none = _build(seq_fired=[])                       # no replay has settled
    replayed = _build(seq_fired=[], seq_fired_backfill=[])   # one did, nothing fired
    for w in (none, replayed):
        assert not w["broken"], "nothing broke on either input"
        assert w["broken"] is None, "an empty list would read as a measured zero"
        assert w["broken_why"] and len(w["broken_why"]) <= 48
    assert none["broken_why"] != replayed["broken_why"], \
        "two silences, never one sentence"
    assert "not rebuilt" in none["broken_why"]
    # the contract's own rule, on this pair: why non-null exactly when null
    listed = _build(seq_fired=[{"level": "PE", "px": 23250.0, "from": "DWELL",
                                "to": "BREAK", "spot": 23241.0, "band": 12.5,
                                "ts": "2026-09-18T11:03:07"}])
    assert listed["broken"] and listed["broken_why"] is None


def test_a_row_that_grows_a_side_raises_rather_than_reaching_the_screen():
    with pytest.raises(ValueError):
        watch._forbid([{"p": 1.0, "side": "buy"}])
