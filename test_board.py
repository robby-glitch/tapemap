"""BOARD rev 3's server half -- the pure reads, on a TREND day and a RANGE day.

Her rule: the app must not be biased to one day. So every read below is
pinned on BOTH reference days the mockup was designed against
(docs/mockups/board-chess-rev3-2026-09-24-notes.md §4-§5), from one frozen
fixture of the inputs the server holds (`test/fixtures/board_NIFTY_...gz`):
  * Thu 2026-09-24, the trend day: PE 23,200 built to 12:31 and folded at
    12:33 as spot broke 23,200; the put ladder folded a strike at a time.
  * Wed 2026-09-23, the range day: the trend box reads NEITHER most of the day.
The strings are the mockup generator's own (its rules were fixed before either
day was read through them), so a drift in any rule is a failing test here.

Nothing here tests that a read is RIGHT about the market -- only that the
rules say what they said. A passing suite is not evidence (CLAUDE.md rule 9).
"""
import gzip
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

import board
import fronts
import live
import trendbox

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test", "fixtures",
                   "board_NIFTY_2026-09-23_24.json.gz")
PRIOR = {"2026-09-23": "2026-09-22", "2026-09-24": "2026-09-23"}
IST = timezone(timedelta(hours=5, minutes=30))


@pytest.fixture(scope="module")
def fx():
    with gzip.open(FIX) as f:
        return json.load(f)


def _day(fx, day):
    d = fx["days"][day]
    opens = {}
    for k, (oc, op) in d["open"].items():
        if oc is not None:
            opens[(float(k), "ce")] = oc
        if op is not None:
            opens[(float(k), "pe")] = op
    return d, opens


def _peak(d, t):
    return {(float(k), side): v for k, (ce, pe) in d["peak"][t].items()
            for side, v in (("ce", ce), ("pe", pe)) if v is not None}


def _trend(fx, day, t):
    tr = fx["trend"]
    return trendbox.rows(tr["m1"][PRIOR[day]], tr["m1"][day], tr["m30"], tr["d1"], day, t)


def _read(fx, day, t, **kw):
    d, opens = _day(fx, day)
    return board.read(fronts.cut(d["minutes"], t), _peak(d, t), opens, d["facts"][t], d["marks"],
                      _trend(fx, day, t), idx="NIFTY", **kw)


# ---------------------------------------------------------------- folds and FIRST (§6.1)

def test_the_put_ladder_folds_a_strike_at_a_time_on_the_trend_day(fx):
    evs = fronts.folds(fx["days"]["2026-09-24"]["minutes"])
    puts = [(e["k"], e["high_at"], e["t"]) for e in evs if e["side"] == "PE" and e["k"] in (23250.0, 23200.0, 23150.0)]
    # the staircase the board shows (notes §9): 23,250 -> 23,200 -> 23,150, on the server's grid
    assert (23250.0, "11:04", "11:14") in puts
    assert (23200.0, "12:31", "12:33") in puts
    assert (23150.0, "13:23", "13:27") in puts
    assert all(e["high"] > 0 for e in evs)             # a front that never built can never fold


def test_first_fold_is_a_top_two_front_on_both_days(fx):
    for day, want in (("2026-09-24", ("CE", 23300.0, "10:58", "10:29")),
                      ("2026-09-23", ("CE", 23400.0, "10:20", "10:15"))):
        d, opens = _day(fx, day)
        m = {t: r for t, r in d["minutes"].items()}
        f = board.first_fold(m, fronts.folds(m), opens)
        assert (f["side"], f["k"], f["t"], f["high_at"]) == want, day


def test_folds_are_causal_so_a_later_read_never_redecides_an_earlier_one(fx):
    m = fx["days"]["2026-09-24"]["minutes"]
    whole = fronts.folds(m)
    noon = fronts.folds(fronts.cut(m, "12:40"))
    assert noon == [e for e in whole if e["t"] <= "12:40"]


# ---------------------------------------------------------------- the headline (§6.2)

@pytest.mark.parametrize("day,t,text", [
    ("2026-09-24", "12:33", "Nobody pressing · PE 23,200 (ITM 25) folded 12:33, 11% off its 12:31 high · "
                            "next put wall PE 23,150 (25 below) stopped adding"),
    ("2026-09-24", "12:35", "Sellers leaning · PE 23,200 (ITM 27) folded 12:33, 11% off its 12:31 high · "
                            "next put wall PE 23,150 (at spot) stopped adding"),
    ("2026-09-24", "13:30", "Sellers pressing · PE 23,150 (OTM 1) folded 13:27, 21% off its 13:23 high · "
                            "no sized put build below spot inside the nine"),
    ("2026-09-24", "12:24", "Nobody pressing · PE 23,250 (ITM 55) folded 11:14, 26% off its 11:04 high · "
                            "next put wall PE 23,200 (at spot) stopped adding"),
    ("2026-09-23", "13:36", "Sellers pressing · PE 23,450 (ITM 30) folded 13:36, 8% off its 13:31 high · "
                            "next put wall PE 23,400 (at spot) stopped adding"),
    ("2026-09-23", "15:26", "Nobody pressing · CE 23,450 (OTM 19) folded 14:30, 40% off its 14:15 high · "
                            "no sized call build above spot inside the nine"),
])
def test_the_headline_names_the_latest_fold_near_spot(fx, day, t, text):
    assert _read(fx, day, t)["headline"]["text"] == text


def test_the_headline_never_names_a_front_that_never_built(fx):
    """0j.2: PE 23,300 was the nearer PE front at 09:31 and had never built; the
    headline says the put side has no built front instead of naming it."""
    hd = _read(fx, "2026-09-24", "09:31")["headline"]
    assert "never built" not in hd["text"] and "PE 23,300" not in hd["text"]
    assert "no put front of the top 2 built today" in hd["text"] and hd["fold"] is None


def test_the_first_fifteen_marks_are_forming_not_a_read(fx):
    d, opens = _day(fx, "2026-09-24")
    hd = board.read(fronts.cut(d["minutes"], "09:20"), None, opens)["headline"]
    assert hd["text"].startswith("Fronts forming") and hd["fold"] is None


# ---------------------------------------------------------------- built today vs carried (§6.3), the defender

def test_the_gate_defender_is_described_honestly_and_left_unchanged(fx):
    r = _read(fx, "2026-09-24", "12:33")
    buy = r["defender"]["buy"]
    assert (buy["k"], buy["side"]) == (23000.0, "PE")                  # §1d's #1, not re-ranked
    assert buy["flags"][0] == "never built today"
    assert buy["flags"][1].startswith("the farther wall, 175 pts; the nearer is PE 23,200 (#2, unwinding)")
    pe = {f["k"]: f for f in r["fronts"] if f["side"] == "PE"}
    assert pe[23000.0]["built"] == "never" and pe[23000.0]["built_label"] == "NEVER BUILT"
    assert pe[23200.0]["nearer"] and not pe[23000.0]["nearer"]
    # open + change is the absolute OI now, and the share is the high over (open + high)
    f = pe[23200.0]
    assert f["now_oi"] == f["open"] + f["chg"]
    assert f["share"] == pytest.approx(f["peak"] / (f["open"] + f["peak"]), abs=1e-3)
    assert f["built"] == ("today" if f["share"] >= 0.5 else "carried")


# ---------------------------------------------------------------- agreement (§6.5): a count, never odds

def test_agreement_is_a_count_on_both_days(fx):
    a = _read(fx, "2026-09-24", "12:35")["agreement"]
    assert (a["head"]["dir"], a["head"]["n"], a["head"]["against"], a["head"]["read"]) == (-1, 4, 0, 5)
    assert [f["k"] for f in a["fam"]] == ["OI", "CVD", "FLOW", "TAPE", "TREND"]
    assert "a count, not odds" in a["head"]["text"] and "%" not in a["head"]["text"]
    b = _read(fx, "2026-09-23", "13:36")["agreement"]
    votes = {f["k"]: f["v"] for f in b["fam"]}
    assert (b["head"]["dir"], b["head"]["n"], b["head"]["against"]) == (-1, 2, 1)
    assert votes["TAPE"] == 1 and votes["TREND"] == 0                   # the tape against, the trend box NEITHER


def test_tape_reads_could_not_check_without_a_footprint_record(fx):
    d, opens = _day(fx, "2026-09-24")
    r = board.read(fronts.cut(d["minutes"], "12:35"), _peak(d, "12:35"), opens, d["facts"]["12:35"],
                   None, _trend(fx, "2026-09-24", "12:35"), idx="BANKNIFTY")
    tape = next(f for f in r["agreement"]["fam"] if f["k"] == "TAPE")
    assert tape["v"] is None and tape["fact"].startswith("could not check") and "BANKNIFTY" in tape["fact"]
    assert r["agreement"]["head"]["read"] == 4


# ---------------------------------------------------------------- the trend box (§6.6): not biased to one day

def test_the_same_rules_read_the_trend_day_as_a_trend_and_the_range_day_as_a_range(fx):
    counts = {}
    for day in ("2026-09-24", "2026-09-23"):
        c = {}
        for t in sorted(fx["days"][day]["minutes"]):
            w = trendbox.strong(_trend(fx, day, t))["word"]
            c[w] = c.get(w, 0) + 1
        counts[day] = c
    assert counts["2026-09-24"] == {"NEITHER": 134, "BEARS": 240}
    assert counts["2026-09-23"] == {"NEITHER": 319, "BULLS": 56}


def test_regime_needs_price_and_oi_to_agree(fx):
    r = _read(fx, "2026-09-24", "12:35")["trend"]
    assert r["regime"]["word"] == "TREND DOWN" and r["strong"]["word"] == "BEARS"
    r = _read(fx, "2026-09-24", "12:30")["trend"]
    assert r["regime"]["word"] == "NOT AGREED" and r["regime"]["price"][0] == "TREND DOWN"   # the put side still writing
    r = _read(fx, "2026-09-23", "13:36")["trend"]
    assert r["regime"]["word"] == "NOT AGREED" and r["regime"]["price"][0] == "CHOP"
    assert r["strong"] == {"word": "NEITHER", "n": [1, 2, 4, 0]}


def test_the_trend_box_never_uses_the_forming_bar(fx):
    """A 5m bar opened 12:30 is closed only once 12:34 is finished; until then
    the row reads the 12:25 bar last, and the price is the finished minute's."""
    tr = fx["trend"]
    rows = trendbox.candles(tr["m1"]["2026-09-24"])
    at = {r[1]: r for r in rows}
    a = trendbox.rows(tr["m1"]["2026-09-23"], tr["m1"]["2026-09-24"], tr["m30"], tr["d1"], "2026-09-24", "12:33")
    b = trendbox.rows(tr["m1"]["2026-09-23"], tr["m1"]["2026-09-24"], tr["m30"], tr["d1"], "2026-09-24", "12:34")
    assert a["px"] == at["12:33"][5] and b["px"] == at["12:34"][5]
    last5 = [x for x in trendbox.agg(rows, 5) if trendbox.slot_end(x[1], 5) <= trendbox._m("12:33")][-1]
    assert last5[1] == "12:25"
    assert trendbox.rows([], [], [], [], "2026-09-24", "12:00") is None          # nothing yet: None, never a zero row


# ---------------------------------------------------------------- PCR and coverage

def test_pcr_is_text_over_the_grid_and_says_it_drifts(fx):
    p = _read(fx, "2026-09-24", "12:33")["pcr"]
    assert p["v"] == pytest.approx(0.755, abs=0.006) and "drifts, no timing" in p["text"] and p["tag"] == "M"


def test_a_grid_with_a_hole_is_not_whole_so_first_is_not_stamped_off_it(fx):
    m = {t: r for t, r in fx["days"]["2026-09-24"]["minutes"].items() if not "10:59" <= t < "13:14"}
    cov = board.coverage(sorted(m))
    assert not cov["whole"] and cov["holes"] == ["10:58–13:14"]
    d, opens = _day(fx, "2026-09-24")
    r = board.read(fronts.cut(m, "13:30"), _peak(d, "13:30"), opens)
    assert r["first"] is None and r["first_why"].startswith("could not check") and "10:58–13:14" in r["first_why"]


# ---------------------------------------------------------------- the mirror read (§6.7)

def _arrays(rows, day):
    base = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=IST)
    return {"timestamp": [int((base + timedelta(hours=int(r[0][:2]), minutes=int(r[0][3:5]))).timestamp()) for r in rows],
            "open": [r[1] for r in rows], "high": [r[2] for r in rows], "low": [r[3] for r in rows],
            "close": [r[4] for r in rows], "volume": [r[5] for r in rows], "open_interest": [r[6] for r in rows]}


def _mirror_legs(fx):
    """The legs exactly as /api/contract assembles them (live._leg_series at 5 min),
    with each leg's prior-session floor pivots (live._floor_pivots)."""
    m = fx["mirror"]
    legs = {}
    for side in ("CE", "PE"):
        leg = live._leg_series(lambda d, s=side: _arrays(m[s]["day"], d), [m["day"]], 5)
        pr = m[side]["prior"]
        H, L, C = max(r[2] for r in pr), min(r[3] for r in pr), pr[-1][4]
        leg.update(strike=23200.0, pivots=dict(live._floor_pivots(H, L, C), H=H, L=L, C=C), pivots_day=m["prior"])
        legs[side] = leg
    return legs, live._leg_series(lambda d: _arrays(m["fut"], d), [m["day"]], 5)["bars"]


def test_the_mirror_reads_the_break_the_way_the_notes_do(fx):
    """Notes §4, 12:34: PE 23,200 z +2.3 (+2σ…+3σ), CE z −1.9; fut new low 12:30 → CONFIRMS."""
    legs, fut = _mirror_legs(fx)
    r = board.mirror(legs, fut, "12:34", expiry=fx["mirror"]["expiry"])
    ce, pe = r["legs"]["CE"], r["legs"]["PE"]
    assert (pe["t"], round(pe["z"], 1), pe["band"]) == ("12:30", 2.3, "+2σ…+3σ")
    assert (ce["t"], round(ce["z"], 1), ce["band"]) == ("12:30", -1.9, "−2σ…−1σ")
    assert r["vs_futures"]["word"] == "CONFIRMS" and r["vs_futures"]["fut"] == {"kind": "low", "t": "12:30"}
    assert r["vs_futures"]["draft"] is True and r["vs_futures"]["tag"] == "I"
    # the nearest prior-session pivot above and at-or-below the close
    assert pe["pivots"]["below"]["name"] == "R3" and pe["pivots"]["above"] is None
    assert pe["pivots"]["above_why"].startswith("checked, none")
    # 12:33: the 12:30 bar is not closed yet, so the read is still the 12:25 bar
    assert board.mirror(legs, fut, "12:33")["legs"]["PE"]["t"] == "12:25"


def test_vs_futures_diverges_and_splits_on_its_own_rule():
    def bars(hl):
        return [{"t": f"09:{15 + 5 * i:02d}", "o": 0, "h": h, "l": lo, "c": 0} for i, (h, lo) in enumerate(hl)]
    fut = bars([(10, 5), (11, 6), (9, 3)])                                   # a new futures low at 09:25
    pe_up, pe_flat = bars([(5, 4), (6, 5), (9, 5)]), bars([(9, 4), (8, 5), (7, 5)])
    ce_dn, ce_flat = bars([(5, 4), (6, 5), (6, 3)]), bars([(5, 2), (6, 3), (6, 3)])
    word = lambda ce, pe: board.vs_futures({"bars": ce}, {"bars": pe}, fut, "09:29")["word"]   # noqa: E731
    assert word(ce_dn, pe_up) == "CONFIRMS"
    assert word(ce_flat, pe_flat) == "DIVERGES"
    assert word(ce_flat, pe_up) == "SPLIT"
    assert board.vs_futures({"bars": ce_dn}, {"bars": []}, fut, "09:29")["word"] is None    # could not check, never a verdict


def test_a_leg_with_no_candles_or_no_closed_bar_says_which():
    assert board.mirror_leg({"bars": [], "strike": 1.0}, "12:00")["why"].startswith("could not check")
    one = {"bars": [{"t": "09:15", "c": 5}], "vwap": [{"vwap": 5, "u1": 5}], "strike": 1.0}
    assert board.mirror_leg(one, "09:17")["why"].startswith("checked, none")
    flat = board.mirror_leg(one, "09:19")
    assert flat["z"] is None and "σ = 0" in flat["why"]                       # a missing value is never a zero


# ================================================================ the route: GET /api/board, /api/oihist
import server                                            # noqa: E402
from test_senses_api import _Cap as _SensesCap           # noqa: E402  (the GET harness, one copy in the tree)


class _Cap(_SensesCap):
    _idx = server.Handler._idx


class _St:
    pass


class _Poller:
    """The two things the board reads off the chain poller: its grid/peak
    state and its latest raw snapshot (oi and oi_chg per leg)."""

    def __init__(self, fx, day="2026-09-24", drop=None):
        d, opens = _day(fx, day)
        st = _St()
        st.minutes = {t: r for t, r in d["minutes"].items() if not (drop and drop[0] <= t < drop[1])}
        st.peak = _peak(d, "15:29")
        last = d["minutes"][max(d["minutes"])]["k"]
        self.states = {"NIFTY": st}
        self.prevs = {"NIFTY": {"strikes": [
            {"k": float(k), "ce": {"oi": opens[(float(k), "ce")] + c, "oi_chg": c},
             "pe": {"oi": opens[(float(k), "pe")] + p, "oi_chg": p}} for k, (c, p) in last.items()]}}


@pytest.fixture
def route(fx, monkeypatch, tmp_path):
    """/api/board with its REST and disk feeders replaced by the fixture, the
    clock held, and day_state in tmp. Counts what was computed."""
    import day_state
    monkeypatch.setattr(server, "_BOARD", server._board_fresh())
    monkeypatch.setattr(day_state, "DIR", str(tmp_path / "day_state"))
    monkeypatch.setitem(server._SENSES, "drag_day", {})
    monkeypatch.setitem(server._SENSES, "day_restored", 0)
    today = server.time.strftime("%Y-%m-%d")
    clock = {"now": "15:45"}
    monkeypatch.setattr(server, "_board_clock", lambda: (today, clock["now"]))
    d = fx["days"]["2026-09-24"]
    calls = {"facts": 0, "trend": 0, "mirror": 0}
    legs, fut = _mirror_legs(fx)

    def facts(idx, day, asof, fr):
        calls["facts"] += 1
        return d["facts"].get(asof), d["marks"]

    def trend(idx, day, asof):
        calls["trend"] += 1
        return _trend(fx, "2026-09-24", asof), None

    def mirror(idx, asof, kce, kpe):
        calls["mirror"] += 1
        return board.mirror(legs, fut, asof, expiry="2026-09-29")
    monkeypatch.setattr(server, "_board_facts", facts)
    monkeypatch.setattr(server, "_board_trend", trend)
    monkeypatch.setattr(server, "_board_mirror", mirror)
    return {"calls": calls, "clock": clock, "poller": _Poller(fx), "today": today}


def _get(path, poller):
    cap = _Cap(path, poller=poller)
    server.Handler.do_GET(cap)
    return cap.sent


def test_the_board_route_composes_every_block_and_serves_repeats_from_the_cache(route):
    a = _get("/api/board?idx=NIFTY", route["poller"])
    assert a["ok"] is True and a["idx"] == "NIFTY" and a["asof"] == "15:29"      # after the close: the last session minute
    for k in ("headline", "fronts", "defender", "folds", "first", "agreement", "trend", "mirror", "pcr", "grid", "not_shown"):
        assert k in a, k
    assert a["first"]["t"] == "10:58" and a["first"]["src"].startswith("stamped by this process")
    assert a["mirror"]["strikes"] == {"CE": 23050.0, "PE": 23050.0}                  # ATM by default
    # three different absences, three different sentences (house rule 6)
    assert all(v.startswith("not shown") for v in a["not_shown"].values())
    assert "level_under_attack" in a["not_shown"] and "flush" in a["not_shown"]
    n = dict(route["calls"])
    for _ in range(5):
        assert _get("/api/board?idx=NIFTY", route["poller"]) == a
    assert route["calls"] == n == {"facts": 1, "trend": 1, "mirror": 1}           # nothing heavy per request


def test_the_board_reads_the_last_finished_minute_never_the_one_in_progress(route):
    route["clock"]["now"] = "12:34"                                                # 12:34 is still forming
    a = _get("/api/board?idx=NIFTY", route["poller"])
    assert a["asof"] == "12:33"
    assert a["headline"]["text"].startswith("Nobody pressing · PE 23,200 (ITM 25) folded 12:33")
    route["clock"]["now"] = "12:36"
    b = _get("/api/board?idx=NIFTY", route["poller"])
    assert b["asof"] == "12:35" and b["headline"]["text"].startswith("Sellers leaning")
    assert route["calls"]["facts"] == 2                                           # one computation per minute


def test_a_strike_choice_moves_only_the_mirror(route):
    a = _get("/api/board?idx=NIFTY", route["poller"])
    b = _get("/api/board?idx=NIFTY&ce=23100&pe=23000", route["poller"])
    assert b["mirror"]["strikes"] == {"CE": 23100.0, "PE": 23000.0} and b["headline"] == a["headline"]
    assert route["calls"]["facts"] == 1 and route["calls"]["mirror"] == 2
    far = _get("/api/board?idx=NIFTY&strike=24000", route["poller"])
    assert far["mirror"]["ok"] is False and far["mirror"]["why"].startswith("not shown")
    assert route["calls"]["mirror"] == 2                                          # a far strike costs no REST


def test_first_is_persisted_and_a_restart_rereads_it_rather_than_redeciding_it(route):
    import day_state
    _get("/api/board?idx=NIFTY", route["poller"])
    server._save_day_state()
    saved = day_state.load(route["today"])["board_first"]["NIFTY"]
    assert (saved["side"], saved["k"], saved["t"]) == ("CE", 23300.0, "10:58")
    # the restart: fresh process state, and a day_state that says something else
    server._BOARD.clear()
    server._BOARD.update(server._board_fresh())
    day_state.save(route["today"], {"drag_day": {}, "board_first": {"NIFTY": dict(saved, t="11:09", k=23400.0)}})
    server._load_day_state()
    a = _get("/api/board?idx=NIFTY", route["poller"])
    assert (a["first"]["k"], a["first"]["t"]) == (23400.0, "11:09")               # re-read, never re-decided
    assert a["first"]["src"].startswith("restored")
    assert _get("/api/oihist?idx=NIFTY", route["poller"])["first"]["t"] == "11:09"


def test_a_backfill_landing_after_the_close_is_not_served_stale(route, fx):
    p = _Poller(fx, drop=("10:59", "13:14"))                                     # a restart's hole, backfill pending
    a = _get("/api/board?idx=NIFTY", p)
    assert a["first"] is None and "10:58–13:14" in a["first_why"] and a["grid"]["whole"] is False
    p.states["NIFTY"].minutes = dict(fx["days"]["2026-09-24"]["minutes"])        # the backfill lands
    b = _get("/api/board?idx=NIFTY", p)
    assert b["grid"]["whole"] is True and b["first"]["t"] == "10:58"


def test_oihist_gains_open_folds_and_first_additively(route):
    j = _get("/api/oihist?idx=NIFTY", route["poller"])
    for k in ("ok", "fronts", "broke", "minutes", "peak", "backfill_marks"):         # nothing it served before is gone
        assert k in j, k
    op = {(r["k"], r["side"]): r["oi"] for r in j["open"]}
    snap = route["poller"].prevs["NIFTY"]["strikes"][0]
    assert op[(snap["k"], "ce")] == snap["ce"]["oi"] - snap["ce"]["oi_chg"]          # oi - chg, one subtraction
    assert j["folds_asof"] == "15:29" and any(f["t"] == "12:33" and f["k"] == 23200.0 for f in j["folds"])
    assert j["first"]["t"] == "10:58"
    assert route["calls"] == {"facts": 0, "trend": 0, "mirror": 0}                  # the grid only: no REST, no tape


def test_the_board_says_why_before_the_first_minute(route):
    route["clock"]["now"] = "09:15"
    a = _get("/api/board?idx=NIFTY", route["poller"])
    assert a["ok"] is False and a["why"].startswith("could not check")
    none = _get("/api/board?idx=NIFTY", None)
    assert none["ok"] is False and "no state" in none["why"]


# ---------------------------------------------------------------- what can happen: the squares (rev 2's, rev 3's words)
LEVELS = [{"kind": "PWL", "px": 23116.1, "label": "PWL 23,116.1 (week of 2026-09-15)"},
          {"kind": "OPEN", "px": 23221.8, "label": "day open 23,221.8"}]


def test_what_can_happen_names_the_next_squares_and_who_pays_there(fx):
    """09-24 12:35, the mockup's own read: down to round 23,150 (-22.8) then PWL;
    the put writers at PE 23,200 are paying and the sellers are pressing."""
    q = _read(fx, "2026-09-24", "12:35", levels=LEVELS)["squares"]
    dn, up = q["dn"], q["up"]
    assert [(x["px"], x["dist"], x["labels"]) for x in dn["sq"]] == [
        (23150.0, -22.8, ["round 23,150"]), (23116.1, -56.8, ["PWL 23,116.1"])]
    assert dn["who"]["text"] == "put writers at PE 23,200 — ITM 27 · carried in (58% of its high was there at the open)"
    assert dn["paying"] == {"yn": "yes", "text": "unwinding since 12:33, 11% off its 12:31 high", "tag": "M"}
    assert dn["press"]["yn"] == "yes" and dn["press"]["text"].startswith("sellers leaning")
    assert dn["refused"] == "PE 23,200 adds again, or absorption prints at 23,200"
    assert up["sq"][0]["px"] == 23200.0 and up["who"]["text"].startswith("call writers at CE 23,200 — OTM 27 · built today")
    assert up["paying"]["yn"] == "no" and up["press"]["yn"] == "no"
    assert q["levels_why"] is None
    # the draft level-under-attack read is NOT here (it waits for her pre-registration)
    blob = json.dumps(q)
    assert not any(w in blob for w in ("HOLDING", "TESTED", "BREAKING", "%\"", "odds\": 0"))


def test_what_can_happen_says_which_absence(fx):
    d, opens = _day(fx, "2026-09-24")
    q = board.read(fronts.cut(d["minutes"], "12:35"), _peak(d, "12:35"), opens)["squares"]
    assert q["levels_why"].startswith("could not check")                   # no levels: said, not hidden
    assert q["dn"]["press"]["yn"] == "could not check"                     # no facts: blind, never a "no"
    q = board.squares([], 100.0, 50.0, None, None, [], [])
    assert q["up"]["who"]["text"].startswith("could not check") and q["up"]["paying"]["yn"] == "could not check"
    none = board.squares([], 100.0, None, None, None, [], [])
    assert none["up"] is None and none["up_why"].startswith("checked, none")


def test_levels_landing_after_the_close_reach_the_squares(route, monkeypatch):
    """After 15:30 the minute key stops moving, so the war map's daily levels
    landing late must re-key the board, or the squares stay level-blind all evening."""
    monkeypatch.setattr(server, "_board_levels", lambda idx: None)
    a = _get("/api/board?idx=NIFTY", route["poller"])
    assert a["squares"]["levels_why"].startswith("could not check")
    monkeypatch.setattr(server, "_board_levels", lambda idx: LEVELS)
    b = _get("/api/board?idx=NIFTY", route["poller"])
    assert b["squares"]["levels_why"] is None and b["headline"] == a["headline"]
    assert "PWL 23,116.1" in json.dumps(b["squares"])
