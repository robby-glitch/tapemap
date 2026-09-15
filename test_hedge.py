"""The short-variance hedger: band math, the brake, and the ledger.

PAPER ONLY, and one test below pins that there is no order path in the module
at all -- house rule 10 is the one rule that cannot be traded away for a
feature, so it gets an assertion rather than a comment.

The arithmetic here decides real (paper) positions, so every branch is
constructed rather than sampled: a hedger that silently rounds to zero lots, or
hedges an incomplete delta, or keeps rebalancing past its brake, fails in ways
that look like normal operation from the outside.
"""

import json

import hedge


# ---- the plan --------------------------------------------------------------

def test_inside_the_band_is_not_a_hedge():
    assert hedge.plan(0.4, 0.0) is None
    assert hedge.plan(-0.99, 0.0) is None


def test_the_band_is_reached_not_merely_approached():
    """>= the band, so exactly one lot of delta triggers."""
    p = hedge.plan(1.0, 0.0)
    assert p and p["side"] == "SELL" and p["lots"] == 1


def test_a_long_delta_is_hedged_by_SELLING_futures():
    p = hedge.plan(1.6, 0.0)
    assert p["side"] == "SELL" and p["lots"] == 2
    assert p["residual_after"] == -0.4


def test_a_short_delta_is_hedged_by_BUYING_futures():
    p = hedge.plan(-2.2, 0.0)
    assert p["side"] == "BUY" and p["lots"] == 2
    assert p["residual_after"] == -0.2


def test_the_hedge_already_on_is_counted():
    """A future's delta is 1.0 per unit, so inventory nets against the option
    book directly. Ignoring it would re-hedge the same exposure every tick."""
    assert hedge.plan(1.5, -1.5) is None          # already neutral
    p = hedge.plan(3.0, -1.0)                     # 2.0 residual left
    assert p["side"] == "SELL" and p["lots"] == 2


def test_bankers_rounding_cannot_produce_a_zero_lot_hedge():
    """Python's round(0.5) is 0. A 0-lot hedge would be a no-op that still
    burned a brake slot and wrote a ledger row claiming a rebalance."""
    assert round(0.5) == 0                        # the trap, pinned
    p = hedge.plan(0.5, 0.0, band=0.5)
    assert p["lots"] == 1


def test_an_unknown_delta_is_never_hedged_as_if_it_were_flat():
    """None must not collapse to 0.0. A book whose greeks did not arrive has
    an UNKNOWN delta; treating it as neutral makes the hedger a random
    position generator."""
    assert hedge.plan(None, 0.0) is None


# ---- the inventory ---------------------------------------------------------

def _book():
    b = hedge.HedgeBook()
    b.roll_day("2026-08-25")
    return b


def test_a_fill_sets_the_basis_and_counts_against_the_brake():
    b = _book()
    f = b.apply("NIFTY", "SELL", 1, 65, 24200.0, "10:00", 1.0, 0.0)
    assert b.leg("NIFTY").lots == -1
    assert b.leg("NIFTY").qty == -65
    assert b.leg("NIFTY").vwap == 24200.0
    assert f.realized == 0.0 and b.used("NIFTY") == 1


def test_adding_in_the_same_direction_re_averages():
    b = _book()
    b.apply("NIFTY", "SELL", 1, 65, 24200.0, "10:00", 1.0, 0.0)
    b.apply("NIFTY", "SELL", 1, 65, 24300.0, "11:00", 1.0, 0.0)
    assert b.leg("NIFTY").vwap == 24250.0
    assert b.leg("NIFTY").lots == -2


def test_closing_a_short_hedge_into_a_rally_realizes_the_LOSS():
    """THE NUMBER THE MODULE EXISTS FOR. Sold futures at 24,200 to hedge a
    long delta; spot rallies; buying back at 24,300 costs money. That loss IS
    the realized-vol bill, and it must come out negative."""
    b = _book()
    b.apply("NIFTY", "SELL", 1, 65, 24200.0, "10:00", 1.0, 0.0)
    f = b.apply("NIFTY", "BUY", 1, 65, 24300.0, "11:00", -1.0, 0.0)
    assert f.realized == round((24300.0 - 24200.0) * 65 * -1, 2)
    assert f.realized < 0
    assert b.leg("NIFTY").lots == 0 and b.leg("NIFTY").vwap is None


def test_a_hedge_that_reverses_re_bases_on_the_new_fill():
    b = _book()
    b.apply("NIFTY", "SELL", 1, 65, 24200.0, "10:00", 1.0, 0.0)
    f = b.apply("NIFTY", "BUY", 3, 65, 24300.0, "11:00", -3.0, 0.0)
    assert f.realized < 0                       # the short leg's bill
    assert b.leg("NIFTY").lots == 2             # net long after the flip
    assert b.leg("NIFTY").vwap == 24300.0


def test_indices_do_not_share_a_hedge_inventory():
    """Hedging BANKNIFTY delta with NIFTY futures would be wrong, so the
    inventories are separate and so are the brakes."""
    b = _book()
    b.apply("NIFTY", "SELL", 1, 65, 24200.0, "10:00", 1.0, 0.0)
    assert b.leg("BANKNIFTY").lots == 0 and b.used("BANKNIFTY") == 0


def test_a_new_day_resets_counters_but_never_the_basis():
    b = _book()
    b.apply("NIFTY", "SELL", 1, 65, 24200.0, "10:00", 1.0, 0.0)
    b.roll_day("2026-08-26")
    assert b.used("NIFTY") == 0                 # counters reset
    assert b.leg("NIFTY").lots == -1            # inventory does not
    assert b.leg("NIFTY").vwap == 24200.0       # nor is it re-based


def test_the_brake_reports_hit_at_the_cap():
    b = _book()
    for i in range(hedge.MAX_HEDGES_DAY):
        assert not b.braked("NIFTY")
        b.apply("NIFTY", "SELL", 1, 65, 24200.0 + i, "10:00", 1.0, 0.0)
    assert b.braked("NIFTY")


def test_the_book_survives_a_round_trip_through_state_json():
    b = _book()
    b.apply("NIFTY", "SELL", 1, 65, 24200.0, "10:00", 1.0, 0.0)
    back = hedge.HedgeBook.from_dict(b.to_dict())
    assert back.leg("NIFTY").lots == -1
    assert back.leg("NIFTY").vwap == 24200.0
    assert back.used("NIFTY") == 1


def test_a_state_written_before_the_hedger_existed_loads_empty():
    assert hedge.HedgeBook.from_dict({}).leg("NIFTY").lots == 0


# ---- the ledger rows -------------------------------------------------------

def test_the_gap_row_is_sized_and_says_hedging_does_not_cover_it():
    g = hedge.gap_exposure(-130.0, 0.002, 120.0)
    assert g["rupees"] == round(130.0 * 120.0 + 0.5 * 0.002 * 120.0 ** 2, 0)
    assert "UNHEDGED" in g["note"]


def test_an_unsizable_gap_is_a_stated_absence_not_a_zero():
    assert hedge.gap_exposure(None, None, 120.0)["rupees"] is None
    assert "net delta is unknown" in hedge.gap_exposure(None, None, 120.0)["why"]
    assert hedge.gap_exposure(-130.0, None, None)["rupees"] is None


def test_the_daily_row_adds_theta_and_the_hedge_bill():
    r = hedge.daily_row("2026-08-25", "NIFTY", 4000.0, -1500.0, 3,
                        hedge.gap_exposure(-130.0, 0.002, 120.0), -0.2)
    assert r["net_variance"] == 2500.0
    assert r["hedges_used"] == 3 and r["hedges_max"] == hedge.MAX_HEDGES_DAY
    assert "bundles theta + gamma" in r["theta_method"]
    assert r["shadow"] is True and r["paper"] is True


def test_an_unattributable_theta_refuses_rather_than_reporting_zero():
    """book.mark_position refuses a partial decomposition; the ledger must
    carry that refusal through instead of turning it into a 0 that would read
    as "no theta was collected"."""
    r = hedge.daily_row("2026-08-25", "NIFTY", None, -1500.0, 3,
                        hedge.gap_exposure(None, None, None), None)
    assert r["theta_collected"] is None and r["net_variance"] is None
    assert "partial decomposition is refused" in r["theta_why"]


def test_no_row_ever_carries_a_rate_or_a_win_count():
    """House rule 4. The ledger describes rupees; the verdict is the
    operator's, over sessions, against a bar she states first."""
    rows = [hedge.daily_row("2026-08-25", "NIFTY", 4000.0, -1500.0, 3,
                            hedge.gap_exposure(-130.0, 0.002, 120.0), -0.2),
            hedge.refusal_row("2026-08-25", "10:00", "NIFTY", "why", 1.0, 2)]
    banned = ("win_rate", "winrate", "hit_rate", "hitrate", "expectancy",
              "accuracy", "wins", "losses", "confidence")
    for r in rows:
        for k in r:
            assert k not in banned, k


# ---- the law ---------------------------------------------------------------

def test_there_is_no_order_path_in_this_module():
    """House rule 10, asserted rather than trusted: this stack has never
    placed an order and must not learn how. A hedger is exactly the shape of
    module where someone would be tempted."""
    import inspect
    src = inspect.getsource(hedge)
    for token in ("place_order", "dhanhq", "upstox_api", "requests.post",
                  "urllib.request", "place_gtt", "modify_order"):
        assert token not in src, token


def test_the_ledger_dir_is_read_at_call_time_so_a_mock_run_can_be_isolated(
        monkeypatch):
    """The 2026-08-24 replay-leak rule applied to the newest writer."""
    monkeypatch.setattr(hedge, "LEDGER_DIR", "data/mock/paper_desk")
    assert hedge.ledger_path("2026-08-25").replace("\\", "/") == \
        "data/mock/paper_desk/hedge_2026-08-25.jsonl"


def test_the_isolation_function_redirects_the_hedge_ledger():
    import inspect

    import server
    assert "hedge_mod.LEDGER_DIR" in inspect.getsource(
        server._isolate_mock_writers)


# ---- through the real trader tick ------------------------------------------
# Unit tests prove the arithmetic; these prove the WIRING, which is where a
# module that is "done" usually turns out not to be.

from datetime import datetime                                    # noqa: E402

import book as book_mod                                          # noqa: E402
import trader as trader_mod                                      # noqa: E402
from test_trader import _doc, _t, _view                          # noqa: E402

IN_HOURS = datetime(2026, 8, 24, 10, 30)
LATE = datetime(2026, 8, 24, 15, 20)


def _short_ce(t, qty=2000, delta0=0.5):
    """A short CE big enough that its delta clears the band whatever the
    chain's measured lot size turns out to be."""
    leg = book_mod.PaperLeg(strike=25000.0, right="CE", side="SELL", qty=qty,
                            entry_px=100.0, entry_ts="10:00", iv0=0.14,
                            delta0=delta0, vega0=1.0)
    t.book.open(idx="NIFTY", strategy="TEST", lots=2, legs=[leg], ts="10:00",
                spot0=25000.0, forced_who="test", forced_why="test",
                gear="PIN")


def test_a_short_call_gets_hedged_by_BUYING_futures(tmp_path, monkeypatch):
    """A naked short CE is short delta. Left alone it is a directional bet;
    the whole premise of short variance is that the direction gets hedged away
    and only IV-minus-RV is left."""
    monkeypatch.setattr(hedge, "LEDGER_DIR", str(tmp_path))
    t = _t(tmp_path)
    _short_ce(t)
    t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=IN_HOURS)
    assert t.hedge.leg("NIFTY").lots > 0          # bought futures
    assert t.hedge.used("NIFTY") == 1


def test_the_hedge_is_not_repeated_while_delta_stays_inside_the_band(
        tmp_path, monkeypatch):
    """The band is the whole point: a continuous hedger on a 10s tick would
    churn the ledger and, at a real broker, the book."""
    monkeypatch.setattr(hedge, "LEDGER_DIR", str(tmp_path))
    t = _t(tmp_path)
    _short_ce(t)
    for _ in range(5):
        t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=IN_HOURS)
    assert t.hedge.used("NIFTY") == 1             # once, not five times


def test_an_incomplete_delta_refuses_to_hedge_and_says_so(tmp_path,
                                                          monkeypatch):
    """book.mark_position now names legs whose greeks did not arrive. Sizing
    a futures trade against that partial sum is the failure this guards."""
    monkeypatch.setattr(hedge, "LEDGER_DIR", str(tmp_path))
    t = _t(tmp_path)
    _short_ce(t)
    doc = _doc()
    for s in doc["strikes"]:
        s["ce"].pop("delta")                      # greeks did not arrive
        s["pe"].pop("delta")
    t.on_chain("NIFTY", doc, _view("PIN"), {}, {}, now=IN_HOURS)
    assert t.hedge.leg("NIFTY").lots == 0         # nothing hedged
    st = t.state({"NIFTY": doc})["hedge"]["indices"]["NIFTY"]
    assert st["delta_why"] and "PARTIAL" in st["delta_why"]


def test_the_brake_stops_hedging_and_refuses_loudly(tmp_path, monkeypatch):
    """When the brake binds the book runs UNHEDGED, which is a materially
    different state and must never be reached quietly."""
    monkeypatch.setattr(hedge, "LEDGER_DIR", str(tmp_path))
    t = _t(tmp_path)
    _short_ce(t)
    t.hedge.roll_day("2026-08-24")
    t.hedge.hedges_today["NIFTY"] = hedge.MAX_HEDGES_DAY   # brake pre-loaded
    t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=IN_HOURS)
    assert t.hedge.leg("NIFTY").lots == 0
    refusals = [d for d in t.decisions
                if d["kind"] == "refusal" and d["strategy"] == "DELTA_HEDGE"]
    assert refusals and "BRAKE" in refusals[0]["detail"]
    assert "UNHEDGED" in refusals[0]["detail"]
    st = t.state({"NIFTY": _doc()})["hedge"]["indices"]["NIFTY"]
    assert st["brake_hit"] is True and st["brake_why"]


def test_eod_flattens_the_hedge_and_writes_the_daily_row(tmp_path,
                                                          monkeypatch):
    """A hedge held past the options it hedges is an outright overnight
    futures position -- the exact risk this module removes."""
    monkeypatch.setattr(hedge, "LEDGER_DIR", str(tmp_path))
    t = _t(tmp_path)
    _short_ce(t)
    t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=IN_HOURS)
    assert t.hedge.leg("NIFTY").lots > 0
    t.on_chain("NIFTY", _doc(spot=25100.0), _view("PIN"), {}, {}, now=LATE)
    assert t.hedge.leg("NIFTY").lots == 0         # flat overnight
    rows = [json.loads(l) for l in
            open(hedge.ledger_path("2026-08-24"), encoding="utf-8")]
    daily = [r for r in rows if r["kind"] == "daily"]
    assert len(daily) == 1
    assert daily[0]["gap_exposure"] is not None
    assert daily[0]["hedges_max"] == hedge.MAX_HEDGES_DAY


def test_the_hedger_never_moves_the_paper_desks_own_risk(tmp_path,
                                                          monkeypatch):
    """SHADOW, structurally. Hedge inventory inside book.Book would move
    forced_ratio and therefore trader's FORCED_MIN entry gate -- a shadow
    module steering the live paper desk."""
    monkeypatch.setattr(hedge, "LEDGER_DIR", str(tmp_path))
    t = _t(tmp_path)
    _short_ce(t)
    t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=IN_HOURS)
    assert t.hedge.leg("NIFTY").lots != 0          # a hedge really is on
    rights = {l["right"] for p in t.book.to_dict()["positions"]
              for l in p["legs"]}
    assert "FUT" not in rights                     # and it is not in the book


def test_the_hedge_survives_a_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(hedge, "LEDGER_DIR", str(tmp_path))
    t = _t(tmp_path)
    _short_ce(t)
    t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=IN_HOURS)
    lots, used = t.hedge.leg("NIFTY").lots, t.hedge.used("NIFTY")
    again = _t(tmp_path)
    assert again.hedge.leg("NIFTY").lots == lots
    assert again.hedge.used("NIFTY") == used


def test_off_hours_writes_no_hedge_ledger(tmp_path, monkeypatch):
    """Same gate as every other forward log here."""
    monkeypatch.setattr(hedge, "LEDGER_DIR", str(tmp_path))
    t = _t(tmp_path)
    _short_ce(t)
    t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {},
               now=datetime(2026, 8, 22, 10, 30))      # a Saturday
    import os
    assert not os.path.exists(hedge.ledger_path("2026-08-22"))


def test_the_api_section_carries_the_paper_and_shadow_honesty(tmp_path,
                                                              monkeypatch):
    monkeypatch.setattr(hedge, "LEDGER_DIR", str(tmp_path))
    t = _t(tmp_path)
    _short_ce(t)
    t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=IN_HOURS)
    h = t.state({"NIFTY": _doc()})["hedge"]
    assert h["paper"] is True and h["shadow"] is True and h["tag"] == "I"
    assert "no order path" in h["note"]
    n = h["indices"]["NIFTY"]
    assert n["band_lots"] == hedge.BAND_LOTS
    assert n["hedges_max"] == hedge.MAX_HEDGES_DAY
    assert "hedge_cost_today" in n and "gap_exposure" in n
