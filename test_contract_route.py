"""`/api/contract` assembly -- live.py's session walk, leg builder, params.

Everything here runs with an INJECTED fetch: no token, no network, no clock
dependence. The live numbers (bar counts, first closes, first OI) are checked
against the raw Dhan response separately -- see .superpowers/sdd/task-4-report.md.

Families:
  1. Session walk       -- N sessions oldest-first, weekends skipped, a
                           weekend request snaps back to a day that traded.
  2. Alignment          -- bars / vwap / oi / bar_days are 1:1 by index.
  3. VWAP resets daily  -- session 2's first bar carries session 2's own
                           anchor, never session 1's cumulative volume.
  4. Gaps               -- an empty session and a failing fetch are BOTH
                           listed, with reasons that distinguish them, and
                           nothing is interpolated across the hole.
  5. Interval sampling  -- resampling never moves a band (spec invariant 6).
  6. forming            -- always null, always with a stated reason.
  7. Param validation   -- a bad side is a hard error, before any I/O.
"""

from datetime import datetime, timedelta, timezone

import pytest

import contract_bars
import live

IST = timezone(timedelta(hours=5, minutes=30))


def _payload(day, n=5, base=100.0, vol=10.0, oi0=500000):
    """A synthetic rest_intraday response: n 1-min bars from 09:15 IST."""
    t0 = datetime.strptime(day, "%Y-%m-%d").replace(
        hour=9, minute=15, tzinfo=IST).timestamp()
    return {
        "open": [base + i for i in range(n)],
        "high": [base + i + 2 for i in range(n)],
        "low": [base + i - 1 for i in range(n)],
        "close": [base + i + 1 for i in range(n)],
        "volume": [vol * (i + 1) for i in range(n)],
        "open_interest": [oi0 + 100 * i for i in range(n)],
        "timestamp": [t0 + 60 * i for i in range(n)],
    }


# ---- 1. session walk -------------------------------------------------------

def test_sessions_back_is_oldest_first_and_skips_weekends():
    # 2026-07-30 is a Thursday; walking back 4 must skip Sat 25 / Sun 26.
    assert live._sessions_back("2026-07-30", 4) == [
        "2026-07-27", "2026-07-28", "2026-07-29", "2026-07-30"]


def test_sessions_back_single_day_is_the_day_itself():
    assert live._sessions_back("2026-07-30", 1) == ["2026-07-30"]


def test_sessions_back_from_a_weekend_snaps_to_a_trading_day():
    # 2026-08-01 is a Saturday: the session that actually traded is Friday.
    assert live._sessions_back("2026-08-01", 1) == ["2026-07-31"]


# ---- 2/3. alignment and the per-session VWAP anchor ------------------------

def test_arrays_are_aligned_one_to_one_and_dated():
    sess = ["2026-07-29", "2026-07-30"]
    leg = live._leg_series(lambda d: _payload(d, n=5), sess, 1)
    n = len(leg["bars"])
    assert n == 10
    assert len(leg["vwap"]) == n
    assert len(leg["oi"]) == n
    assert len(leg["bar_days"]) == n
    assert leg["bar_days"] == ["2026-07-29"] * 5 + ["2026-07-30"] * 5
    assert set(leg["bars"][0]) == set(contract_bars.BAR_KEYS)
    assert set(leg["vwap"][0]) == set(contract_bars.BAND_KEYS)
    assert leg["oi"][0] == leg["bars"][0]["oi"]
    assert leg["gaps"] == []


def test_vwap_is_re_anchored_every_session():
    sess = ["2026-07-29", "2026-07-30"]
    # session 2 sits at a completely different price level; if the VWAP leaked
    # across the day boundary its first bar could not equal its own typical price
    leg = live._leg_series(
        lambda d: _payload(d, n=5, base=100.0 if d == sess[0] else 900.0),
        sess, 1)
    first_of_day2 = leg["bars"][5]
    tp = (first_of_day2["h"] + first_of_day2["l"] + first_of_day2["c"]) / 3.0
    assert leg["vwap"][5]["vwap"] == pytest.approx(tp)
    # and it is NOT the continuation of session 1
    assert leg["vwap"][5]["vwap"] != pytest.approx(leg["vwap"][4]["vwap"])


# ---- 3b. Dhan's over-fetch: a one-day request can return two sessions ------

def _two_sessions(day_a, day_b, n=4):
    """One payload carrying two trading days back to back -- what Dhan really
    returns for an older `day` once toDate is sent as day + 1 (measured
    2026-07-31: fromDate 07-28 / toDate 07-29 -> 750 bars across BOTH days)."""
    a, b = _payload(day_a, n=n, base=100.0), _payload(day_b, n=n, base=900.0)
    return {k: list(a[k]) + list(b[k]) for k in a}


def test_over_fetched_next_session_is_filtered_out():
    raw = _two_sessions("2026-07-28", "2026-07-29")
    leg = live._leg_series(lambda d: raw, ["2026-07-28"], 1)
    assert len(leg["bars"]) == 4                 # NOT 8: the 29th is not ours
    assert set(leg["bar_days"]) == {"2026-07-28"}
    # the over-fetch is reported, not silently dropped
    assert leg["served_by_request"]["2026-07-28"] == {"2026-07-28": 4,
                                                      "2026-07-29": 4}


def test_over_fetch_does_not_leak_into_the_next_sessions_vwap():
    raw = _two_sessions("2026-07-28", "2026-07-29")
    leg = live._leg_series(lambda d: raw, ["2026-07-28", "2026-07-29"], 1)
    assert leg["bar_days"] == ["2026-07-28"] * 4 + ["2026-07-29"] * 4
    # each session re-anchors: its first bar's VWAP is its own typical price
    for i in (0, 4):
        b = leg["bars"][i]
        assert leg["vwap"][i]["vwap"] == pytest.approx(
            (b["h"] + b["l"] + b["c"]) / 3.0)


def test_one_session_reports_what_dhan_served_and_what_was_lost():
    raw = _two_sessions("2026-07-28", "2026-07-29", n=3)
    mine, served, lost = live._one_session(raw, "2026-07-29")
    assert served == {"2026-07-28": 3, "2026-07-29": 3}
    assert lost == 0
    assert len(mine["close"]) == 3
    assert mine["close"] == raw["close"][3:]


def test_one_session_counts_ragged_and_unreadable_rows_as_lost():
    raw = _payload("2026-07-30", n=4)
    raw["volume"] = raw["volume"][:3]            # ragged feed: one row short
    raw["timestamp"][0] = "not-an-instant"       # unplaceable in any session
    mine, served, lost = live._one_session(raw, "2026-07-30")
    assert served == {"2026-07-30": 2}
    assert lost == 2                             # 1 ragged + 1 bad timestamp
    assert len(mine["close"]) == 2


def test_a_session_dhan_never_served_is_a_gap_even_when_bars_came_back():
    # asking for the 29th but being handed only the 28th must NOT silently
    # relabel the 28th's bars as the 29th's
    raw = _payload("2026-07-28", n=5)
    leg = live._leg_series(lambda d: raw, ["2026-07-29"], 1)
    assert leg["bars"] == []
    assert leg["gaps"] == ["2026-07-29"]
    assert "2026-07-28" in leg["gap_reasons"]["2026-07-29"]


# ---- 4. gaps ---------------------------------------------------------------

def test_empty_session_is_a_gap_and_nothing_is_interpolated():
    sess = ["2026-07-29", "2026-07-30"]

    def fetch(d):
        return {} if d == "2026-07-29" else _payload(d, n=5)

    leg = live._leg_series(fetch, sess, 1)
    assert leg["gaps"] == ["2026-07-29"]
    assert len(leg["bars"]) == 5                 # only the session that had bars
    assert set(leg["bar_days"]) == {"2026-07-30"}
    assert "no usable bars" in leg["gap_reasons"]["2026-07-29"]
    assert "rolling-ATM" in leg["gap_reasons"]["2026-07-29"]


def test_failing_fetch_is_a_gap_with_a_different_reason():
    sess = ["2026-07-29", "2026-07-30"]

    def fetch(d):
        if d == "2026-07-29":
            raise TimeoutError("no response in 25s")
        return _payload(d, n=3)

    leg = live._leg_series(fetch, sess, 1)
    assert leg["gaps"] == ["2026-07-29"]
    # an error is a different fact about the world than an empty session
    assert leg["gap_reasons"]["2026-07-29"].startswith("fetch failed:")
    assert "TimeoutError" in leg["gap_reasons"]["2026-07-29"]
    assert len(leg["bars"]) == 3


def test_every_session_empty_yields_no_bars_and_all_gaps():
    sess = ["2026-07-29", "2026-07-30"]
    leg = live._leg_series(lambda d: {}, sess, 1)
    assert leg["bars"] == [] and leg["vwap"] == [] and leg["oi"] == []
    assert leg["gaps"] == sess


# ---- 5. interval sampling never moves a band -------------------------------

def test_resampling_samples_the_bands_it_does_not_recompute_them():
    sess = ["2026-07-30"]
    one = live._leg_series(lambda d: _payload(d, n=6), sess, 1)
    three = live._leg_series(lambda d: _payload(d, n=6), sess, 3)
    assert len(three["bars"]) == 2
    # each 3-min bucket carries the bands of its LAST 1-minute bar, verbatim
    for j, i in enumerate((2, 5)):
        assert three["vwap"][j] == one["vwap"][i]


# ---- 5b. the shared axis: both legs index the same minute ------------------

def test_legs_are_joined_on_one_axis_not_by_position():
    # the reproduced failure: CE has only 07-30, PE has 07-29 and 07-30, so
    # index 0 used to compare 07-30 09:15 against 07-29 09:15
    sess = ["2026-07-29", "2026-07-30"]
    ce = live._leg_series(
        lambda d: _payload(d, n=5) if d == "2026-07-30" else {}, sess, 1)
    pe = live._leg_series(lambda d: _payload(d, n=5), sess, 1)
    assert len(ce["bars"]) == 5 and len(pe["bars"]) == 10   # before the join

    legs = {"CE": ce, "PE": pe}
    axis = live._shared_axis(legs)
    for leg in legs.values():
        live._align_to_axis(leg, axis)

    assert len(axis) == 10
    for leg in legs.values():
        for key in ("bars", "vwap", "oi", "bar_days"):
            assert len(leg[key]) == len(axis)
    # every slot means the same session and minute on BOTH legs
    for i, (day, t) in enumerate(axis):
        for leg in legs.values():
            assert leg["bar_days"][i] == day
            if leg["bars"][i] is not None:
                assert leg["bars"][i]["t"] == t
    # CE is explicitly absent for the whole of 07-29 rather than shifted onto it
    assert ce["bars"][:5] == [None] * 5
    assert all(b is not None for b in ce["bars"][5:])
    assert all(b is not None for b in pe["bars"])


def test_a_minute_one_leg_never_traded_is_null_never_carried_forward():
    def ce_fetch(d):
        p = _payload(d, n=4)
        return {k: v[:2] + v[3:] for k, v in p.items()}   # CE misses 09:17

    ce = live._leg_series(ce_fetch, ["2026-07-30"], 1)
    pe = live._leg_series(lambda d: _payload(d, n=4), ["2026-07-30"], 1)
    legs = {"CE": ce, "PE": pe}
    axis = live._shared_axis(legs)
    for leg in legs.values():
        live._align_to_axis(leg, axis)

    assert [t for _d, t in axis] == ["09:15", "09:16", "09:17", "09:18"]
    assert ce["bars"][2] is None                 # the minute it did not print
    assert ce["vwap"][2] is None and ce["oi"][2] is None
    # and NOT the previous bar repeated, which would invent a print
    assert ce["bars"][1]["t"] == "09:16"
    assert ce["bars"][3]["t"] == "09:18"         # not shifted up into the hole


def test_a_single_leg_is_unchanged_by_the_join():
    leg = live._leg_series(lambda d: _payload(d, n=5), ["2026-07-30"], 1)
    before = [dict(b) for b in leg["bars"]]
    axis = live._shared_axis({"CE": leg})
    live._align_to_axis(leg, axis)
    assert leg["bars"] == before
    assert axis == [("2026-07-30", b["t"]) for b in before]
    assert leg["axis_collisions"] == 0


def test_a_duplicated_slot_keeps_the_first_bar_and_is_counted():
    leg = {"bars": [{"t": "09:15", "c": 1.0}, {"t": "09:15", "c": 2.0}],
           "vwap": [{"vwap": 1.0}, {"vwap": 2.0}], "oi": [10, 20],
           "bar_days": ["2026-07-30", "2026-07-30"]}
    axis = live._shared_axis({"X": leg})
    live._align_to_axis(leg, axis)
    assert len(axis) == 1
    assert leg["bars"][0]["c"] == 1.0            # a slot cannot hold two bars
    assert leg["axis_collisions"] == 1


def test_axis_rule_states_the_join_and_forbids_carrying_forward():
    assert "null" in live.AXIS_RULE
    assert "carried forward" in live.AXIS_RULE


def test_build_contract_emits_the_axis_and_aligns_both_legs(monkeypatch):
    import chain_live

    monkeypatch.setattr(chain_live, "read_token", lambda: "tok")
    monkeypatch.setattr(chain_live, "token_status", lambda t: {"ok": True})
    monkeypatch.setattr(chain_live, "_client", lambda t: object())
    monkeypatch.setattr(chain_live, "_with_deadline",
                        lambda fn, s, label: fn())
    monkeypatch.setattr(chain_live, "resolve_expiry",
                        lambda *a, **k: "2026-08-04")
    monkeypatch.setattr(live, "_atm_ids",
                        lambda k, cfg: {"CE": "111", "PE": "222"})

    def fetch(sec_id, day):
        # the CE leg is missing the older session entirely
        if sec_id == "111" and day == "2026-07-29":
            return {}
        return _payload(day, n=5)

    out = live.build_contract("NIFTY", strike=24200, side="BOTH", interval=1,
                              days=2, day="2026-07-30", chain_rows=[],
                              fetch=fetch)

    assert len(out["axis"]) == 10
    assert out["axis"][0] == ["2026-07-29", "09:15"]
    assert out["axis_rule"] == live.AXIS_RULE
    ce, pe = out["legs"]["CE"], out["legs"]["PE"]
    for leg in (ce, pe):
        assert len(leg["bars"]) == len(out["axis"])
    assert ce["bars"][:5] == [None] * 5          # CE never traded on the 29th
    assert all(b is not None for b in pe["bars"])
    # same index, same minute, same session -- the whole point of the axis
    for i, (day, t) in enumerate(out["axis"]):
        for leg in (ce, pe):
            if leg["bars"][i] is not None:
                assert (leg["bar_days"][i], leg["bars"][i]["t"]) == (day, t)


# ---- 5c. rotation rides that same axis, as a sibling of the legs -----------

def _osc(day, n, side, spike_at):
    """A payload that oscillates (so sigma is non-degenerate) and then, at
    `spike_at`, pierces the band and closes back inside it -- the operator's
    tag-AND-reverse. CE spikes DOWN (a BUY trigger), PE spikes UP so the pair
    is rotating rather than both legs decaying together."""
    t0 = datetime.strptime(day, "%Y-%m-%d").replace(
        hour=9, minute=15, tzinfo=IST).timestamp()
    base0 = 100.0 if side == "CE" else 200.0
    p = {k: [] for k in ("open", "high", "low", "close", "volume",
                         "open_interest", "timestamp")}
    for i in range(n):
        base = base0 + (2.0 if i % 2 else -2.0)
        hi, lo = base + 1.0, base - 1.0
        if i == spike_at:
            if side == "CE":
                lo = base0 - 20.0
            else:
                hi = base0 + 60.0
        p["open"].append(base)
        p["high"].append(hi)
        p["low"].append(lo)
        p["close"].append(base)
        p["volume"].append(10.0)
        p["open_interest"].append(500000 + 1000 * i if side == "CE"
                                  else 700000 - 1000 * i)
        p["timestamp"].append(t0 + 60 * i)
    return p


def _rotation_contract(monkeypatch, spike_at=14, n=20, interval=1):
    import chain_live

    monkeypatch.setattr(chain_live, "read_token", lambda: "tok")
    monkeypatch.setattr(chain_live, "token_status", lambda t: {"ok": True})
    monkeypatch.setattr(chain_live, "_client", lambda t: object())
    monkeypatch.setattr(chain_live, "_with_deadline",
                        lambda fn, s, label: fn())
    monkeypatch.setattr(chain_live, "resolve_expiry",
                        lambda *a, **k: "2026-08-04")
    monkeypatch.setattr(live, "_atm_ids",
                        lambda k, cfg: {"CE": "111", "PE": "222"})

    def fetch(sec_id, day):
        return _osc(day, n, "CE" if sec_id == "111" else "PE", spike_at)

    return live.build_contract("NIFTY", strike=24350, side="BOTH",
                               interval=interval, days=1, day="2026-07-30",
                               chain_rows=[], fetch=fetch)


def test_rotation_is_one_slot_per_axis_index(monkeypatch):
    out = _rotation_contract(monkeypatch)
    rot = out["rotation"]
    assert len(rot) == len(out["axis"])
    for leg in out["legs"].values():
        assert len(rot) == len(leg["bars"])
    # a record's own `i` IS its position: a consumer zips it onto the bars
    for i, r in enumerate(rot):
        assert r is None or r["i"] == i


def test_rotation_is_the_engines_answer_not_a_second_derivation(monkeypatch):
    import band_rotation

    out = _rotation_contract(monkeypatch)
    axis = [tuple(a) for a in out["axis"]]
    # byte-for-byte what the detector says about the legs the payload carries,
    # so a UI can never disagree with the engine by recomputing it
    assert out["rotation"] == band_rotation.detect(out["legs"], axis)
    # and the whole payload is accepted as its own input (detect unwraps it)
    assert out["rotation"] == band_rotation.detect(out)


def test_a_real_trigger_surfaces_on_the_route_at_the_right_minute(monkeypatch):
    out = _rotation_contract(monkeypatch, spike_at=14)
    fired = [r for r in out["rotation"] if r]
    assert len(fired) == 1
    r = fired[0]
    assert (r["i"], r["side"], r["leg"], r["band"]) == (14, "BUY", "CE", "d3")
    # the slot it landed on is the minute the CE actually pierced
    day, t = out["axis"][r["i"]]
    assert (day, t) == ("2026-07-30", "09:29")
    assert out["legs"]["CE"]["bars"][r["i"]]["t"] == t
    assert out["legs"]["CE"]["bars"][r["i"]]["l"] == 80.0
    # the receipts are strings a human can check the numbers in
    assert "d3" in r["trigger"] and "back above it" in r["trigger"]
    assert r["confirm"] in ("CONFIRMED", "UNCONFIRMED", "UNKNOWN")
    assert r["trap"] in ("CLEAR", "SUSPECT", "UNKNOWN")
    assert r["confirm_why"] and r["trap_why"]


def test_rotation_is_null_where_nothing_fired(monkeypatch):
    out = _rotation_contract(monkeypatch, spike_at=99)   # never spikes
    assert out["rotation"] == [None] * len(out["axis"])


def test_rotation_is_additive_and_lives_beside_the_legs(monkeypatch):
    out = _rotation_contract(monkeypatch)
    # a sibling of `legs`, never a field inside one: at most ONE record exists
    # per bar even when both legs trigger, so it cannot belong to a leg
    assert "rotation" in out
    for leg in out["legs"].values():
        assert "rotation" not in leg
        for key in ("bars", "vwap", "oi", "bar_days"):
            assert len(leg[key]) == len(out["axis"])


def test_rotation_rule_states_the_ui_must_not_recompute():
    assert "never re-derive" in live.ROTATION_RULE
    assert "UNKNOWN" in live.ROTATION_RULE
    assert "axis" in live.ROTATION_RULE


# ---- 6/7. forming, and param validation before any I/O ---------------------

def test_forming_is_null_and_says_why():
    leg = live._leg_series(lambda d: _payload(d, n=2), ["2026-07-30"], 1)
    assert leg["forming"] is None
    assert "ChainPoller" in leg["forming_why"]
    assert "never synthesised" in leg["forming_why"]


def test_bad_side_is_rejected_before_any_network_call():
    with pytest.raises(ValueError, match="side must be CE, PE or BOTH"):
        live.build_contract("NIFTY", side="CALL",
                            fetch=lambda sec_id, d: _payload(d))
