# tapemap/test_signals.py
"""signals.py: the ballot (spec §A.4), and the state machine (spec §A.2, §A.5-A.8).

Synthetic tape and book throughout: no recorded day is a target, and no
number from the 2026-09-16 study appears here or in the module.
"""
import pytest

import signals as sig
import visit


def _tape(n=14, fut=23270.0):
    closed = [{"t": (1000 * 60 * 5 * i) + 1_780_026_340_000, "o": 23500 - 20 * i,
               "h": 23510 - 20 * i, "l": 23480 - 20 * i, "c": 23490 - 20 * i}
              for i in range(n)]
    bands = [{"vwap": 23400.0, "sigma": 50.0, "d2": 23300.0, "d3": 23250.0,
              "u2": 23500.0, "u3": 23550.0}] * n
    return {"session": "NIFTY-I|5m|2026-09-15", "idx": "NIFTY", "interval": 5,
            "rowSize": 5, "closed": closed, "bands": bands, "futPx": fut,
            "forming": None, "walls": [], "broke": [], "events": [], "taps": []}


def _v(t):
    """The visit these votes are cast inside: buy@10:00, bar 9 of the tape."""
    v = visit.current(t, [], "buy")
    assert v is not None and v["visit_key"] == "buy@10:00"
    return v


def _wall(px=23290.0, since="10:05", snapshot=False):
    return {"price": px, "side": 1, "size": 400, "hits": 2, "since": since,
            "snapshot": snapshot}


def _sweeps(n_buy=6, n_sell=1, qty=100.0, t="10:05:10"):
    return ([{"det": "sweep", "kind": "swept", "side": "buy", "qty": qty, "t": t,
              "inst": "NIFTY-FUT"}] * n_buy
            + [{"det": "sweep", "kind": "swept", "side": "sell", "qty": qty, "t": t,
                "inst": "NIFTY-FUT"}] * n_sell)


def _oi(chg=1.0e6, pain=6.2, conf="session"):
    """One PE strike under the edge (fresh writing) and one above it (under
    water). Prices are in the futures frame, as frame._walls emits them."""
    return [{"kind": "PE", "p": 23280.0, "strike": 23250.0, "oi": 2.2e7, "chg": chg,
             "pain": 0.0, "pain_tag": "I", "conf": conf},
            {"kind": "PE", "p": 23360.0, "strike": 23330.0, "oi": 1.1e7, "chg": -1.0e5,
             "pain": pain, "pain_tag": "I", "conf": "low"}]


def test_a_single_measured_vote_passes_and_names_which():
    t = _tape(); t["walls"] = [_wall()]
    o = sig.votes(t, [], [], "buy", _v(t))
    assert o["n"] == 1 and o["threshold"] == 1 and o["passed"] is True
    assert o["passed_why"] is None and o["of"] == 4
    w = next(i for i in o["items"] if i["key"] == "wall")
    assert w["ok"] is True and w["src"] == "observed" and w["tag"] == "M"
    assert w["why"] is None and w["label"] and w["t"] == "10:05"


def test_no_votes_does_not_pass_and_says_so_in_one_clause():
    t = _tape()
    o = sig.votes(t, [], [], "buy", _v(t))
    assert o["n"] == 0 and o["passed"] is False
    assert o["passed_why"] and len(o["passed_why"]) <= 48


def test_oi_is_never_the_reason_on_its_own():
    """True on most visits where it is measurable -- background, not a filter,
    and the only inferred vote on the ballot. It adds weight and can never be
    the reason a sound happened (spec §A.4)."""
    t = _tape()
    o = sig.votes(t, _oi(), [], "buy", _v(t))
    oi = next(i for i in o["items"] if i["key"] == "oi")
    assert oi["ok"] is True and oi["tag"] == "I"
    assert o["n"] == 1 and o["passed"] is False
    assert o["passed_why"] == "one vote, and it is OI"


def test_oi_plus_one_measured_vote_passes():
    t = _tape(); t["walls"] = [_wall()]
    o = sig.votes(t, _oi(), [], "buy", _v(t))
    assert o["n"] == 2 and o["passed"] is True and o["passed_why"] is None


def test_a_null_vote_never_moves_n_and_prints_why_it_could_not_be_checked():
    t = _tape()
    o = sig.votes(t, [], [], "buy", _v(t))
    for key in ("depth", "oi"):
        it = next(i for i in o["items"] if i["key"] == key)
        assert it["ok"] is None and it["src"] is None
        assert it["why"] and len(it["why"]) <= 48
    assert o["measurable"] == 2 and o["n"] == 0


def test_a_checked_and_not_met_vote_is_false_not_null():
    """Three sentences, never one: found nothing is not could not check."""
    t = _tape()
    o = sig.votes(t, _oi(), _sweeps(n_buy=1, n_sell=9), "buy", _v(t))
    d = next(i for i in o["items"] if i["key"] == "depth")
    assert d["ok"] is False and d["why"] and o["measurable"] == 4


def test_the_depth_vote_needs_both_the_ratio_and_the_count():
    t = _tape()
    assert next(i for i in sig.votes(t, [], _sweeps(6, 1), "buy", _v(t))["items"]
                if i["key"] == "depth")["ok"] is True
    assert next(i for i in sig.votes(t, [], _sweeps(4, 0), "buy", _v(t))["items"]
                if i["key"] == "depth")["ok"] is False, "4 sweeps is under the floor"
    assert next(i for i in sig.votes(t, [], _sweeps(6, 5), "buy", _v(t))["items"]
                if i["key"] == "depth")["ok"] is False, "ratio under 1.5"


def test_a_backfilled_vote_is_shown_and_does_not_count():
    """The anytime-start rule applied to the ballot: a reconstructed morning
    may be drawn, but only what the brain WATCHED happen rings a bell."""
    t = _tape(); t["walls"] = [_wall(snapshot=True)]
    o = sig.votes(t, [], [], "buy", _v(t))
    w = next(i for i in o["items"] if i["key"] == "wall")
    assert w["ok"] is True and w["src"] == "backfill"
    assert o["n"] == 0 and o["passed"] is False


def test_evidence_from_before_the_reach_is_not_this_visits_evidence():
    t = _tape(); t["walls"] = [_wall(since="09:20")]
    o = sig.votes(t, [], [], "buy", _v(t))
    assert next(i for i in o["items"] if i["key"] == "wall")["ok"] is False


def test_a_wall_of_the_wrong_side_is_not_a_vote():
    t = _tape()
    t["walls"] = [dict(_wall(), side=-1)]
    o = sig.votes(t, [], [], "buy", _v(t))
    assert next(i for i in o["items"] if i["key"] == "wall")["ok"] is False


def test_an_event_four_rows_off_the_edge_is_not_a_vote():
    t = _tape()
    far = t["closed"][-1]["t"]
    t["events"] = [{"t": far, "kind": "absorption", "p": 23300.0 + 4 * 5}]
    assert next(i for i in sig.votes(t, [], [], "buy", _v(t))["items"]
                if i["key"] == "event")["ok"] is False
    t["events"] = [{"t": far, "kind": "absorption", "p": 23300.0 + 2 * 5}]
    assert next(i for i in sig.votes(t, [], [], "buy", _v(t))["items"]
                if i["key"] == "event")["ok"] is True


def test_the_ballot_refuses_anything_that_is_not_an_oi_row():
    """§H.1 enforced by the signature, not by discipline: a tape wall or a
    prior-day level handed in as an OI row is a bug, and it raises here rather
    than quietly becoming a vote."""
    t = _tape()
    with pytest.raises(ValueError):
        sig.votes(t, [{"kind": "PDH", "p": 23500.0}], [], "buy", _v(t))


def test_every_why_fits_on_the_card():
    t = _tape()
    o = sig.votes(t, [], [], "buy", _v(t))
    for it in o["items"]:
        assert it["why"] is None or len(it["why"]) <= 48
        assert (it["why"] is None) == (it["ok"] is True)


def _zs(rows):
    """A zone_state list at the payload's own 3-minute labels. `arm` is
    non-None only on arming bars, exactly as run_states emits it."""
    return rows


def _armed(first_t="10:00", state="ARMED", entry=None, left=3):
    return {"i": 0, "t": first_t, "state": state, "ref_i": 0, "ref_high": 23310.0,
            "level": 23300.0, "stop": None, "candles_left": left,
            "arm": {"rearm": False, "band": "d2", "extreme": 23290.0,
                    "first_i": 0, "first_t": first_t},
            "entry": entry, "exit_why": None, "readable": True}


def _after(t, state="ARMED", entry=None, left=2):
    return {"i": 1, "t": t, "state": state, "ref_i": 0, "ref_high": 23310.0,
            "level": 23300.0, "stop": None, "candles_left": left, "arm": None,
            "entry": entry, "exit_why": None, "readable": True}


def _entry(t="10:15"):
    return {"i": 1, "t": t, "side": "BUY", "leg": "index", "band": "d2",
            "trigger": "index low touched d2 23300 at 10:00, then closed 23320 "
                       "above that candle's high 23310 3 bars later",
            "also": None, "confirm": "UNKNOWN", "confirm_why": "single series",
            "trap": "UNKNOWN", "trap_why": "no index series", "trap_dwell": None,
            "ref_i": 0, "ref_high": 23310.0, "level": 23300.0, "waited": 3,
            "stop": None}


def test_a_reached_but_unarmed_visit_names_the_intent_and_the_target():
    t = _tape()
    s, o = sig.build(t, [], "buy", [], [], "10:10")
    assert s["state"] == "REACHED" and s["state_why"] is None
    assert s["visit_key"] == "buy@10:00" and s["is_edge"] is True
    assert s["side"] == "buy" and s["intent"] == "fade to VWAP" and s["not_a"] is None
    assert s["target"] == 23400.0 and s["target_why"] is None


def test_the_sell_side_says_what_it_is_not():
    t = _tape(fut=23520.0)
    for i, b in enumerate(t["closed"]):
        t["closed"][i] = dict(b, h=23520.0)           # every bar tags u2
    s, _o = sig.build(t, [], "sell", [], [], "10:10")
    assert s["side"] == "sell" and s["not_a"] == "outright short"
    assert s["intent"] == "fade to VWAP" and s["target"] == 23400.0


def test_armed_then_live_only_when_the_ballot_passes():
    t = _tape(); t["walls"] = [_wall()]
    zs = _zs([_armed(), _after("10:15", state="TRIGGERED", entry=_entry())])
    s, o = sig.build(t, zs, "buy", [], [], "10:20")
    assert o["passed"] is True and s["state"] == "LIVE"
    assert s["fired_at"] == "10:15" and s["trigger_px"] is not None
    t2 = _tape()                                       # no wall: no measured vote
    s2, o2 = sig.build(t2, zs, "buy", [], [], "10:20")
    assert o2["passed"] is False and s2["state"] == "ARMED"


def test_a_reference_that_expired_without_an_entry_is_void():
    t = _tape()
    zs = _zs([_armed(), _after("10:45", state="WAITING", left=None)])
    s, _o = sig.build(t, zs, "buy", [], [], "10:50")
    assert s["state"] == "VOID" and s["state_why"] is None


def test_the_falsifier_is_frozen_at_the_arm_bar_and_says_when():
    t = _tape()
    zs = _zs([_armed()])
    s, _o = sig.build(t, zs, "buy", [], [], "10:10")
    f = s["falsifier"]
    assert f["px"] == 23250.0 and f["frozen_at"] == "10:00" and f["drifted"] is False
    assert "5-minute close past 23,250" in f["rule"] and "3 bars" in f["rule"]


def test_the_falsifier_says_so_when_the_live_band_has_walked_away_from_it():
    t = _tape()
    t["bands"] = [dict(b) for b in t["bands"]]
    t["bands"][-1] = dict(t["bands"][-1], d3=23250.0 - 0.3 * 50.0)
    zs = _zs([_armed()])
    s, _o = sig.build(t, zs, "buy", [], [], "10:10")
    assert s["falsifier"]["drifted"] is True and s["falsifier"]["px"] == 23250.0


def test_candles_are_not_counted_blind():
    """A hole in the tape's own timestamp series between the arm bar and now
    means the close of a bar was never seen. candles_left HOLDS at its last
    seen value, candles_blind is true, and blind_since names the minute. The
    bars here are 5 minutes apart from 09:15, so dropping index 10 and 11
    removes 10:05 and 10:10 and the hole opens at 10:05."""
    t = _tape()
    t["closed"] = t["closed"][:10] + t["closed"][12:]
    zs = _zs([_armed(), _after("10:05", left=2)])
    s, _o = sig.build(t, zs, "buy", [], [], "10:30")
    assert s["candles_blind"] is True and s["blind_since"] == "10:05"
    assert s["candles_left"] == 3, "the 10:05 row's count was never seen"


def test_a_seen_signal_sounds_firm_and_an_unseen_one_sounds_soft():
    t = _tape(); t["walls"] = [_wall()]
    zs = _zs([_armed(), _after("10:15", state="TRIGGERED", entry=_entry())])
    s, _o = sig.build(t, zs, "buy", [], [], "10:20")
    assert s["state"] == "LIVE" and s["sound"] == "firm" and s["mute_why"] is None
    assert s["seen_at"] == s["fired_at"] == "10:15"
    # drop 10:10 and 10:15: the reach at 10:00 survives, the trigger bar does
    # not, so the brain did not watch it happen
    t2 = _tape(); t2["walls"] = [_wall()]
    t2["closed"] = t2["closed"][:11] + t2["closed"][13:]
    s2, _o2 = sig.build(t2, zs, "buy", [], [], "10:30")
    assert s2["state"] == "LIVE" and s2["candles_blind"] is True
    assert s2["sound"] == "soft" and s2["seen_at"] == "10:20" != s2["fired_at"]


def test_visit_two_draws_and_never_sounds():
    """The screen makes visit two attractive because it still draws
    beautifully (spec §H.7). It is grey, silent, tagged out_of_method so its
    rows can never pool with the edge population."""
    closed, bands = [], []
    # bars run 09:45 .. 10:20. The pocket is touched at 09:55, abandoned by the
    # 10:00 close (0.5 sigma back inside), and touched again at 10:15.
    lows = [23480, 23480, 23290, 23480, 23480, 23480, 23290, 23290]
    closes = [23470, 23470, 23300, 23340, 23470, 23470, 23300, 23300]
    for i, (lo, c) in enumerate(zip(lows, closes)):
        closed.append({"t": (1000 * 60 * 5 * i) + 1_780_026_340_000 + 1800000,
                       "o": 23470, "h": 23500, "l": lo, "c": c})
        bands.append({"vwap": 23400.0, "sigma": 50.0, "d2": 23300.0,
                      "d3": 23250.0, "u2": 23500.0, "u3": 23550.0})
    t = {"session": "NIFTY-I|5m|2026-09-15", "idx": "NIFTY", "interval": 5,
         "rowSize": 5, "closed": closed, "bands": bands, "futPx": 23290.0,
         "forming": None, "walls": [], "events": []}
    s, _o = sig.build(t, [], "buy", [], [], "10:30")
    assert s["visit_ordinal"] == 2 and s["is_edge"] is False
    assert s["sound"] is None and s["mute_why"] == "visit 2 - not your edge"
    assert s["out_of_method"] is True


def test_nothing_outside_the_window_ever_sounds():
    t = _tape(n=3, fut=23270.0)          # the provisional latch at 09:30
    s, _o = sig.build(t, [], "buy", [], [], "09:30")
    assert s["reached_at"] == "09:30" and s["in_window"] is False
    assert s["is_edge"] is False and s["sound"] is None
    assert s["mute_why"] == "09:30 - outside 09:45-13:15"
    assert s["out_of_method"] is True


def test_a_visit_with_no_bands_says_it_does_not_know():
    t = _tape(); t["bands"] = []
    s, o = sig.build(t, [], "buy", [], [], "10:10")
    assert s["state"] == "PATA NAHI" and s["state_why"] and len(s["state_why"]) <= 48
    assert o["n"] == 0


def test_every_nullable_field_has_its_why_and_no_why_exceeds_the_card():
    t = _tape()
    s, _o = sig.build(t, [], "buy", [], [], "10:10")
    for f, w in (("reached_at", "reached_at_why"), ("target", "target_why"),
                 ("falsifier", "falsifier_why")):
        assert (s[w] is not None) == (s[f] is None), f
        assert s[w] is None or len(s[w]) <= 48
    # state_why is the one exception the contract names: non-null exactly when
    # state is "PATA NAHI", not when state is null (it never is).
    assert (s["state_why"] is not None) == (s["state"] == "PATA NAHI")
    assert (s["mute_why"] is not None) == (s["sound"] is None)


def test_no_probability_word_reaches_the_object():
    import json as _json
    t = _tape(); t["walls"] = [_wall()]
    zs = _zs([_armed(), _after("10:15", state="TRIGGERED", entry=_entry())])
    s, o = sig.build(t, zs, "buy", [], [], "10:20")
    blob = _json.dumps([s, o]).lower()
    for banned in ("hit rate", "win rate", "expectancy", "probability",
                   "confidence", "%"):
        assert banned not in blob
