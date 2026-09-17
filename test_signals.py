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
