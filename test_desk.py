"""The selector: which structure the market is paying for, and which it is not.

The tests that matter most are the REFUSALS. A selector that always names a
trade is a salesman, and the two ways this one must refuse are:

  `test_below_the_flip_every_short_premium_structure_stands_aside`
      the regime says no, and every premium seller obeys it

  `test_a_structure_this_stack_cannot_build_says_what_is_missing`
      a directional spread is BLOCKED with "a direction view" named, never
      quietly omitted -- an absent row reads as "not considered".
"""
import math

import desk
import gamma
import surface

F = 24_400.0
T = 7.0 / 365.0
A, B, C = 0.130, -0.55, 4.0


def _chain(bump=None, quotes=None):
    """`quotes`: {k: {"ce": {"bid":.., "ask":..}, "pe": {...}}} merged in, for
    the liquidity tests -- absent by default, matching every other test here."""
    rows = []
    for k in [F + i * 50 for i in range(-10, 11)]:
        x = math.log(k / F)
        iv = A + B * x + C * x * x + (bump or {}).get(k, 0.0)
        ce = {"ltp": gamma.bs_price(F, k, iv, T, "C"), "iv": iv, "oi": 900_000.0}
        pe = {"ltp": gamma.bs_price(F, k, iv, T, "P"), "iv": iv, "oi": 1_100_000.0}
        ce.update(((quotes or {}).get(k) or {}).get("ce") or {})
        pe.update(((quotes or {}).get(k) or {}).get("pe") or {})
        rows.append({"k": k, "ce": ce, "pe": pe})
    return rows


def _surf(bump=None, quotes=None):
    return surface.read("NIFTY", "2026-08-28", _chain(bump, quotes), F, T)


def _doc(spot=F, flip=F - 220, pain=F, ok=True, bump=None, quotes=None):
    return {"ok": ok, "spot": spot, "flip_px": flip, "gex": 2.4e9,
            "max_pain": pain, "strikes": _chain(bump, quotes)}


# both wings rich, and the strikes beyond them cheap
RICH_BOTH = {24700: 0.020, 24000: 0.020, 24900: -0.018, 23900: -0.018}


# --------------------------------------------------------------------------
# the regime read -- what the dealers' book is forced to do
# --------------------------------------------------------------------------

def test_above_the_flip_reads_damping():
    r = desk.regime_from_chain(_doc(spot=F, flip=F - 220))
    assert r.above_flip is True and r.state == "DAMPING"
    assert any("DAMPS" in w for w in r.why)


def test_below_the_flip_reads_amplifying():
    r = desk.regime_from_chain(_doc(spot=F, flip=F + 220))
    assert r.above_flip is False and r.state == "AMPLIFYING"
    assert any("AMPLIFIES" in w for w in r.why)


def test_no_chain_is_unknown_which_is_not_neutral():
    """An absent regime must never read as a permissive one."""
    r = desk.regime_from_chain(None)
    assert r.state == "UNKNOWN" and r.above_flip is None
    assert any("not the same as neutral" in w for w in r.why)
    assert desk.regime_from_chain({"ok": False}).state == "UNKNOWN"


def test_the_expected_move_comes_from_the_atm_straddle():
    r = desk.regime_from_chain(_doc())
    atm = gamma.bs_price(F, F, A, T, "C") + gamma.bs_price(F, F, A, T, "P")
    assert abs(r.expected_move - atm) < 1.0


# --------------------------------------------------------------------------
# the refusals
# --------------------------------------------------------------------------

def test_below_the_flip_every_short_premium_structure_stands_aside():
    """Hedging amplifies below the flip. A premium seller that ignores that is
    short gamma into an amplifier."""
    d = desk.decide(_surf(RICH_BOTH),
                    desk.regime_from_chain(_doc(flip=F + 300)))
    by = {c.name: c for c in d.candidates}
    # jade_lizard included deliberately: it caps the UPSIDE tail and leaves
    # the short put naked, which is the side an amplifying regime punishes.
    for n in ("short_strangle", "iron_condor", "short_straddle_pin",
              "jade_lizard"):
        assert by[n].status == "STAND_ASIDE", n
        assert by[n].why


def test_only_the_defined_risk_spread_survives_an_amplifying_regime():
    """A vertical is long and short the same wing -- defined, level-neutral
    and regime-neutral. It is the one structure that should still stand."""
    d = desk.decide(_surf({24700: 0.020, 24900: -0.020}),
                    desk.regime_from_chain(_doc(flip=F + 300)))
    live = [c.name for c in d.candidates if c.status == "DEPLOYABLE"]
    assert live == ["vertical_relative_value"]


def test_a_structure_this_stack_cannot_build_says_what_is_missing():
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    by = {c.name: c for c in d.candidates}
    assert by["calendar"].status == "BLOCKED"
    assert any("second expiry" in m for m in by["calendar"].missing)
    for n in ("bull_put_spread", "bear_call_spread", "risk_reversal",
              "strip_strap"):
        assert by[n].status == "BLOCKED"
        assert any("direction view" in m for m in by[n].missing), n


def test_an_unfitted_surface_blocks_everything():
    s = surface.read("NIFTY", "x", [], F, T)
    d = desk.decide(s, desk.regime_from_chain(_doc()))
    assert not d.fit_ok and d.best is None
    assert all(c.status == "BLOCKED" for c in d.candidates)


def test_a_flat_surface_offers_no_mispricing_trade():
    """Nothing off the curve means nothing to HARVEST -- every structure whose
    case rests on a residual must decline.

    The pin straddle is the deliberate exception: its case is the regime, not
    the surface, so it survives a flat curve. It must then carry an edge of
    about zero and say the pin is the whole argument -- a trade resting on an
    [I], marked as one."""
    d = desk.decide(_surf(), desk.regime_from_chain(_doc()))
    by = {c.name: c for c in d.candidates}
    for n in ("vertical_relative_value", "short_strangle", "iron_condor"):
        assert by[n].status != "DEPLOYABLE", n
    pin = by["short_straddle_pin"]
    assert pin.status == "DEPLOYABLE"
    assert abs(pin.edge) < 1e-6, "a flat curve cannot fund a measured edge"
    assert any("the pin is the whole case" in w for w in pin.why)


# --------------------------------------------------------------------------
# what it does select
# --------------------------------------------------------------------------

def test_a_rich_and_a_cheap_strike_on_one_side_is_a_relative_value_spread():
    """The only structure that needs NO VOL-LEVEL view: long and short the
    same wing, so 'is vol rich' never enters. It is emphatically NOT
    spot-neutral -- see test_a_vertical_is_directional_and_the_hedge_says
    _which_way."""
    d = desk.decide(_surf({24700: 0.020, 24900: -0.020}),
                    desk.regime_from_chain(_doc()))
    rv = {c.name: c for c in d.candidates}["vertical_relative_value"]
    assert rv.status == "DEPLOYABLE"
    assert [l.side for l in rv.legs] == ["SELL", "BUY"]
    assert rv.legs[0].strike == 24700 and rv.legs[1].strike == 24900
    assert any("VOL-neutral" in w for w in rv.why)
    assert any("NOT spot-neutral" in w for w in rv.why)


def test_both_wings_rich_above_the_flip_is_a_strangle():
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    st = {c.name: c for c in d.candidates}["short_strangle"]
    assert st.status == "DEPLOYABLE"
    assert {l.strike for l in st.legs} == {24700, 24000}
    assert all(l.side == "SELL" for l in st.legs)


def test_cheap_wings_beyond_the_body_upgrade_it_to_a_condor():
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    ic = {c.name: c for c in d.candidates}["iron_condor"]
    assert ic.status == "DEPLOYABLE" and len(ic.legs) == 4
    buys = [l for l in ic.legs if l.side == "BUY"]
    assert {l.strike for l in buys} == {24900, 23900}


def test_one_rich_wing_is_not_a_strangle():
    d = desk.decide(_surf({24700: 0.020}), desk.regime_from_chain(_doc()))
    st = {c.name: c for c in d.candidates}["short_strangle"]
    assert st.status == "BLOCKED"
    assert any("BOTH sides" in m for m in st.missing)


def test_spot_far_from_max_pain_is_not_a_pin():
    d = desk.decide(_surf(RICH_BOTH),
                    desk.regime_from_chain(_doc(pain=F + 900)))
    pin = {c.name: c for c in d.candidates}["short_straddle_pin"]
    assert pin.status == "STAND_ASIDE"
    assert any("too far to call a pin" in w for w in pin.why)


def test_put_skew_makes_the_jade_lizard_eligible():
    """Index skew is puts over calls, which is the crowded side."""
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    jl = {c.name: c for c in d.candidates}["jade_lizard"]
    assert jl.status == "DEPLOYABLE"
    assert [l.side for l in jl.legs] == ["SELL", "SELL", "BUY"]
    assert any("crowded side" in w for w in jl.why)


# --------------------------------------------------------------------------
# edge is a description, never a forecast
# --------------------------------------------------------------------------

def test_selling_rich_and_buying_cheap_both_add_to_edge():
    d = desk.decide(_surf({24700: 0.020, 24900: -0.020}),
                    desk.regime_from_chain(_doc()))
    rv = {c.name: c for c in d.candidates}["vertical_relative_value"]
    assert rv.edge > 0


def test_the_ranking_prefers_more_captured_mispricing_per_rupee_of_margin():
    """The real score is edge per rupee of margin, not raw edge -- a wide,
    naked structure can carry a bigger raw edge than a tight defined-risk one
    while paying far less per rupee actually at risk."""
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    live = [c for c in d.candidates if c.status == "DEPLOYABLE"]
    assert d.best == live[0].name
    assert all(live[i].edge_per_margin >= live[i + 1].edge_per_margin
               for i in range(len(live) - 1))


def test_deployable_sorts_above_stand_aside_above_blocked():
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    seen = [desk._ORDER[c.status] for c in d.candidates]
    assert seen == sorted(seen)


def test_no_candidate_ever_reports_a_confidence():
    """Status, never a probability. `edge` describes what is harvested; it
    does not forecast what it pays."""
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    for c in d.candidates:
        assert not hasattr(c, "confidence")
        assert c.status in ("DEPLOYABLE", "STAND_ASIDE", "BLOCKED")
    assert any("NOT confidence" in w for w in d.why)


def test_the_thinnest_leg_is_reported_so_size_can_be_judged():
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    for c in d.candidates:
        if c.status == "DEPLOYABLE":
            assert c.thinnest_oi is not None and c.thinnest_oi > 0


# --------------------------------------------------------------------------
# the live payload's real shape
# --------------------------------------------------------------------------

def test_the_metrics_are_read_from_where_the_live_payload_puts_them():
    """The chain nests flip_px, gex_total and max_pain under `metrics`. Read
    flat they are all None, the regime is UNKNOWN, and every premium structure
    is BLOCKED -- total silence from one nesting level. Caught on the first
    live chain; no synthetic fixture had the real shape."""
    doc = {"ok": True, "spot": 24220.25, "strikes": _chain(),
           "metrics": {"flip_px": 23987.23, "flip_status": "FOUND",
                       "gex_total": 19786.89, "max_pain": 24250,
                       "pcr_oi": 0.92}}
    r = desk.regime_from_chain(doc)
    assert r.flip_px == 23987.23
    assert r.gex == 19786.89
    assert r.max_pain == 24250
    assert r.above_flip is True and r.state == "DAMPING"


def test_a_flat_payload_still_works():
    """Older payloads put them at the top level; the fallback keeps them."""
    r = desk.regime_from_chain({"ok": True, "spot": 24220.0, "strikes": [],
                                "flip_px": 24000.0, "gex": 5.0,
                                "max_pain": 24200})
    assert r.flip_px == 24000.0 and r.gex == 5.0 and r.max_pain == 24200
    assert r.state == "DAMPING"


def test_a_straddle_always_has_two_legs():
    """Selecting legs by richness emitted a ONE-LEGGED 'straddle' whenever only
    one side cleared the bar -- a naked short option wearing a straddle's name.
    Found on the first live chain. The pin justifies the trade; richness is
    only evidence."""
    # only the call side is rich; the put side is on the curve
    d = desk.decide(_surf({24450: 0.020}), desk.regime_from_chain(_doc()))
    pin = {c.name: c for c in d.candidates}["short_straddle_pin"]
    assert pin.status == "DEPLOYABLE"
    assert len(pin.legs) == 2, "a straddle is two legs or it is not a straddle"
    assert {l.right for l in pin.legs} == {"CE", "PE"}
    assert all(l.side == "SELL" for l in pin.legs)


def test_a_pin_with_no_rich_leg_says_the_pin_is_the_whole_case():
    d = desk.decide(_surf(), desk.regime_from_chain(_doc()))
    pin = {c.name: c for c in d.candidates}["short_straddle_pin"]
    assert pin.status == "DEPLOYABLE" and len(pin.legs) == 2
    assert any("the pin is the whole case" in w for w in pin.why)


# --------------------------------------------------------------------------
# what the first live open taught, at 09:42 IST on 2026-08-21
# --------------------------------------------------------------------------

def test_no_crossing_with_positive_gex_is_damping_not_unknown():
    """flip_status NO_CROSSING means GEX never changes sign in range -- a
    STRONGER statement than a flip, not a weaker one. Read as UNKNOWN it
    blocked the whole catalog on three indices at once, in exactly the
    condition selling premium wants."""
    doc = {"ok": True, "spot": 24243.0, "strikes": _chain(),
           "metrics": {"flip_px": None, "flip_status": "NO_CROSSING",
                       "gex_total": 35637.18, "gex_regime": "POSITIVE",
                       "max_pain": 24250}}
    r = desk.regime_from_chain(doc)
    assert r.above_flip is True and r.state == "DAMPING"
    assert any("one side of the gear" in w for w in r.why)


def test_no_crossing_with_negative_gex_is_amplifying():
    doc = {"ok": True, "spot": 24243.0, "strikes": _chain(),
           "metrics": {"flip_px": None, "flip_status": "NO_CROSSING",
                       "gex_total": -8000.0, "max_pain": 24250}}
    r = desk.regime_from_chain(doc)
    assert r.above_flip is False and r.state == "AMPLIFYING"


def test_no_crossing_with_no_gex_stays_unknown():
    doc = {"ok": True, "spot": 24243.0, "strikes": _chain(),
           "metrics": {"flip_px": None, "flip_status": "NO_CROSSING",
                       "gex_total": None, "max_pain": 24250}}
    assert desk.regime_from_chain(doc).state == "UNKNOWN"


def test_a_statistically_extreme_but_worthless_residual_is_refused():
    """Live NIFTY had rmse 0.080 vol pts, so z >= 1.5 needed only 0.12 vol
    points -- and the 'best' trade was a deep-OTM put spread worth 23 paise a
    unit with net edge ZERO. A z-score says how UNUSUAL, never how much."""
    # deep-OTM strikes carry little vega, so a residual that clears z on a
    # tight fit is still worth almost nothing in rupees
    tiny = {23900: 0.0005, 23950: -0.0005}
    d = desk.decide(_surf(tiny), desk.regime_from_chain(_doc()))
    rv = {c.name: c for c in d.candidates}["vertical_relative_value"]
    assert rv.status == "BLOCKED"
    assert any("floor" in m for m in rv.missing)


def test_the_richest_pair_is_chosen_not_the_first_side_checked():
    """Checking CE then PE and taking the first hit picked a deep-OTM put
    spread over a near-money call spread worth many times more."""
    d = desk.decide(_surf({24450: 0.020, 24500: -0.020,
                           23800: 0.020, 23750: -0.020}),
                    desk.regime_from_chain(_doc()))
    rv = {c.name: c for c in d.candidates}["vertical_relative_value"]
    assert rv.status == "DEPLOYABLE"
    assert rv.legs[0].right == "CE", "near-money legs carry far more vega"


def test_the_pin_straddle_is_exempt_from_the_economic_floor():
    """Its case is the regime, not a residual -- and it says so."""
    d = desk.decide(_surf(), desk.regime_from_chain(_doc()))
    pin = {c.name: c for c in d.candidates}["short_straddle_pin"]
    assert pin.status == "DEPLOYABLE" and abs(pin.edge) < desk.MIN_EDGE_RS
    assert any("the pin is the whole case" in w for w in pin.why)


# --------------------------------------------------------------------------
# structure LEGALITY -- shape first, richness second. What the live open on
# 2026-08-20 actually got wrong: `short_strangle: SELL 24,650 CE / SELL
# 24,250 PE` with spot at 24,238 -- the put was twelve points from spot, an
# ATM point wearing a wing's name. A z-score alone cannot tell a wing from
# noise; these tests pin the two checks that now stand between them.
# --------------------------------------------------------------------------

def test_a_rich_point_inside_the_expected_move_is_not_a_strangle_wing():
    """The exact live bug: a point close enough to spot to be noise, not a
    wing, must not be chosen even though it clears the richness bar."""
    # 24350 is 50 points from spot F=24400 -- far inside half an expected
    # move (~175 pts here) -- yet bumped rich enough to clear Z_EDGE alone.
    d = desk.decide(_surf({24700: 0.020, 24350: 0.03}),
                    desk.regime_from_chain(_doc(bump={24700: 0.020, 24350: 0.03})))
    st = {c.name: c for c in d.candidates}["short_strangle"]
    assert st.status == "BLOCKED"
    assert any("expected moves on BOTH sides" in m for m in st.missing)
    assert not st.legs


def test_wings_that_are_not_delta_balanced_are_refused():
    """Both wings clear richness AND the expected-move floor, but one sits
    far closer to the money than the other -- a directional bet, not a
    market-neutral structure, and this stack has no direction view."""
    bump = {24900: 0.02, 24200: 0.02}     # 500pts vs 200pts from spot
    d = desk.decide(_surf(bump), desk.regime_from_chain(_doc(bump=bump)))
    st = {c.name: c for c in d.candidates}["short_strangle"]
    assert st.status == "BLOCKED"
    assert any("not delta-balanced" in m for m in st.missing)


def test_expected_move_unavailable_blocks_the_strangle_by_name():
    """No ATM straddle price -> cannot judge whether a wing sits outside the
    move it would need to. BLOCKED with the reason, not a silent guess."""
    doc = {"ok": True, "spot": F, "flip_px": F - 220, "gex": 2.4e9,
           "max_pain": F, "strikes": []}   # no strikes -> no ATM straddle
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(doc))
    st = {c.name: c for c in d.candidates}["short_strangle"]
    assert st.status == "BLOCKED"
    assert any("expected move unavailable" in m for m in st.missing)


# --------------------------------------------------------------------------
# risk: max loss, breakevens -- and naked structures say UNBOUNDED, not a
# fake number
# --------------------------------------------------------------------------

def test_a_defined_risk_spread_reports_max_loss_and_a_breakeven():
    d = desk.decide(_surf({24700: 0.020, 24900: -0.020}),
                    desk.regime_from_chain(_doc()))
    rv = {c.name: c for c in d.candidates}["vertical_relative_value"]
    assert rv.risk == "DEFINED"
    assert rv.max_loss is not None and rv.max_loss > 0
    assert len(rv.breakevens) == 1


def test_the_condor_max_loss_never_exceeds_the_wider_wing_width():
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    ic = {c.name: c for c in d.candidates}["iron_condor"]
    assert ic.risk == "DEFINED"
    call_w = ic.legs[2].strike - ic.legs[0].strike
    put_w = ic.legs[1].strike - ic.legs[3].strike
    assert ic.max_loss <= max(call_w, put_w) + 1e-6
    assert len(ic.breakevens) == 2


def test_a_naked_structure_never_reports_a_fake_max_loss():
    """The strangle and the pin straddle are both naked both sides -- risk is
    UNDEFINED, and max_loss is None, never a number standing in for
    'unbounded'."""
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    by = {c.name: c for c in d.candidates}
    for n in ("short_strangle", "short_straddle_pin"):
        c = by[n]
        assert c.risk == "UNDEFINED"
        assert c.max_loss is None
        assert len(c.breakevens) == 2


def test_the_jade_lizard_is_undefined_risk_despite_a_capped_upside():
    """The naked put makes the STRUCTURE's risk undefined even though the
    call spread on top is priced and capped -- reporting a max loss here
    would read as the whole position's ceiling when it is only the upside's."""
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    jl = {c.name: c for c in d.candidates}["jade_lizard"]
    assert jl.risk == "UNDEFINED" and jl.max_loss is None
    assert len(jl.breakevens) >= 1


# --------------------------------------------------------------------------
# margin [I] -- a documented floor, never SPAN
# --------------------------------------------------------------------------

def test_defined_risk_margin_is_the_max_loss_floor():
    d = desk.decide(_surf({24700: 0.020, 24900: -0.020}),
                    desk.regime_from_chain(_doc()))
    rv = {c.name: c for c in d.candidates}["vertical_relative_value"]
    assert rv.margin_per_lot == rv.max_loss * d.lot_size
    assert "[I]" in rv.margin_model
    assert "SPAN" not in rv.margin_model or "NOT" in rv.margin_model


def test_naked_margin_is_never_presented_as_span():
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    st = {c.name: c for c in d.candidates}["short_strangle"]
    assert st.margin_per_lot is not None and st.margin_per_lot > 0
    assert "[I]" in st.margin_model
    assert "NOT" in st.margin_model and "SPAN" in st.margin_model


def test_two_naked_legs_cost_less_than_twice_one_naked_leg():
    """Opposite-side legs cannot both blow out at once -- the model must not
    charge a strangle two full single-leg margins."""
    single = desk._naked_margin(F, 75, 1)
    double = desk._naked_margin(F, 75, 2)
    assert single < double < 2 * single


# --------------------------------------------------------------------------
# the score: edge per rupee of margin, and per rupee of max loss where
# defined
# --------------------------------------------------------------------------

def test_edge_per_margin_is_computed_for_every_deployable_candidate():
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    for c in d.candidates:
        if c.status == "DEPLOYABLE":
            assert c.edge_per_margin is not None


def test_edge_per_max_loss_exists_only_when_risk_is_defined():
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    for c in d.candidates:
        if c.status != "DEPLOYABLE":
            continue
        if c.risk == "DEFINED":
            assert c.edge_per_max_loss is not None
        else:
            assert c.edge_per_max_loss is None


# --------------------------------------------------------------------------
# sizing: capital in, lots out, capped by the thinnest leg's own liquidity
# --------------------------------------------------------------------------

def test_lots_follow_from_stated_capital_not_a_passed_in_label():
    d5 = desk.decide(_surf({24700: 0.020, 24900: -0.020}),
                     desk.regime_from_chain(_doc()), capital=5 * desk.ONE_CRORE)
    d1 = desk.decide(_surf({24700: 0.020, 24900: -0.020}),
                     desk.regime_from_chain(_doc()), capital=1 * desk.ONE_CRORE)
    rv5 = {c.name: c for c in d5.candidates}["vertical_relative_value"]
    rv1 = {c.name: c for c in d1.candidates}["vertical_relative_value"]
    assert rv5.lots > rv1.lots > 0
    assert rv5.lots_per_cr == rv1.lots_per_cr, "a per-crore rate is capital-independent"


def test_sizing_is_capped_by_the_thinnest_legs_own_liquidity():
    """A huge capital number cannot size past what the thinnest leg's OI can
    actually support."""
    thin = {24700: {"ce": {"oi": 50.0}}}     # collapse this leg's OI to almost nothing
    d = desk.decide(_surf({24700: 0.020, 24900: -0.020}, thin),
                    desk.regime_from_chain(_doc(bump={24700: 0.020, 24900: -0.020},
                                                quotes=thin)),
                    capital=100 * desk.ONE_CRORE)
    rv = {c.name: c for c in d.candidates}["vertical_relative_value"]
    assert rv.lots < 10
    assert "liquidity" in rv.liquidity_note


def test_a_wide_quote_that_swallows_the_edge_blocks_the_candidate():
    """A leg whose own bid/ask spread is worth more than the edge captured
    makes the edge unrecoverable even resting inside the spread."""
    wide = {24700: {"ce": {"bid": 50.0, "ask": 500.0}}}   # absurd spread
    bump = {24700: 0.020, 24900: -0.020}
    d = desk.decide(_surf(bump, wide),
                    desk.regime_from_chain(_doc(bump=bump, quotes=wide)))
    rv = {c.name: c for c in d.candidates}["vertical_relative_value"]
    assert rv.status == "BLOCKED"
    assert any("swallow the edge" in m for m in rv.missing)
    assert not rv.legs


def test_a_missing_quote_never_blocks_on_silence():
    """No bid/ask on the feed is not evidence of a bad one -- the existing
    fixtures carry none, and none of them should be liquidity-blocked."""
    d = desk.decide(_surf({24700: 0.020, 24900: -0.020}),
                    desk.regime_from_chain(_doc()))
    rv = {c.name: c for c in d.candidates}["vertical_relative_value"]
    assert rv.status == "DEPLOYABLE"


def test_capital_and_lot_size_are_carried_on_the_decision():
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    assert d.capital == desk.DEFAULT_CAPITAL
    assert d.lot_size == desk.LOT_SIZE["NIFTY"]


def test_lot_size_can_be_overridden_explicitly():
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()), lot_size=40)
    assert d.lot_size == 40


def test_a_pin_that_trades_cheap_to_the_curve_stands_aside():
    """Exempt from the floor is not licence to be negative. A negative edge is
    the surface saying both legs are CHEAP -- the market is offering the
    straddle, not paying for it. Shipped without this guard the pin ranked
    BEST on two of three indices live, at Rs -0.90 and Rs -4.62 a unit."""
    d = desk.decide(_surf({24400: -0.02, 24450: -0.02}),
                    desk.regime_from_chain(_doc()))
    pin = {c.name: c for c in d.candidates}["short_straddle_pin"]
    assert pin.edge is not None and pin.edge < 0, "fixture must go cheap"
    assert pin.status == "STAND_ASIDE"
    assert any("not paying for it" in w for w in pin.why)
    # legs kept on purpose: what it WOULD have sold, beside why it is not
    assert len(pin.legs) == 2 and pin.risk == "UNDEFINED"


def test_best_never_names_a_structure_that_earns_nothing():
    """`best` is the one field a reader acts on."""
    for bump in ({}, {24400: -0.02, 24450: -0.02}, RICH_BOTH):
        d = desk.decide(_surf(bump), desk.regime_from_chain(_doc()))
        if d.best:
            c = {x.name: x for x in d.candidates}[d.best]
            assert (c.edge_per_margin or 0.0) > 0, d.best


# --------------------------------------------------------------------------
# direction: every vol trade carries it whether it means to or not
# --------------------------------------------------------------------------

def test_every_deployable_structure_names_its_net_delta():
    """A position whose largest risk goes unnamed is not a recommendation.
    Live on 2026-08-21 the 'level-neutral' vertical carried +0.359 delta a
    unit -- several crore of direction, from a module that BLOCKS directional
    structures for want of a direction view."""
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()))
    live = [c for c in d.candidates if c.status == "DEPLOYABLE"]
    assert live, "fixture must produce something"
    for c in live:
        assert c.net_delta is not None, c.name
        assert c.hedge_note, c.name


def test_a_vertical_is_directional_and_the_hedge_says_which_way():
    d = desk.decide(_surf({24450: 0.020, 24600: -0.020}),
                    desk.regime_from_chain(_doc()))
    rv = {c.name: c for c in d.candidates}["vertical_relative_value"]
    if rv.status != "DEPLOYABLE":
        return
    assert abs(rv.net_delta) > 0.05, "a two-strike vertical is never flat"
    # the hedge must oppose the exposure, or it is not a hedge
    assert rv.hedge_units is not None
    assert (rv.hedge_units < 0) == (rv.net_delta > 0)


def test_the_vertical_no_longer_claims_to_be_neutral_outright():
    """It is neutral in VOL and emphatically not in SPOT. Saying only the
    first is the omission that made it dangerous."""
    d = desk.decide(_surf({24450: 0.020, 24600: -0.020}),
                    desk.regime_from_chain(_doc()))
    rv = {c.name: c for c in d.candidates}["vertical_relative_value"]
    if rv.status != "DEPLOYABLE":
        return
    joined = " ".join(rv.why)
    assert "VOL-neutral" in joined and "NOT spot-neutral" in joined


def test_a_leg_with_no_iv_refuses_to_sum_a_delta():
    """One unpriceable leg makes the total a lie, so there is no total."""
    c = desk.Candidate("x", "DEPLOYABLE",
                       legs=[desk.Leg("SELL", 24400.0, "CE", iv=None)])
    desk._delta_book(c, 24400.0, 7 / 365, 75)
    assert c.net_delta is None and not c.hedge_note


# --------------------------------------------------------------------------
# lot size: measured off the wire, never assumed
# --------------------------------------------------------------------------

def test_the_lot_size_is_measured_from_the_chains_own_gcd():
    """Every oi and vol the exchange publishes is a whole number of LOTS in
    units, so the GCD across a chain IS the lot size. It was hardcoded 75/35/20
    and simply WRONG -- the live chain and the operator both give 65/30/20,
    which had been scaling every sizing figure by ~15%."""
    for lot in (65, 30, 20):
        rows = [{"k": 24000 + i * 50,
                 "ce": {"oi": lot * (900 + i), "vol": lot * (30 + i)},
                 "pe": {"oi": lot * (700 + i), "vol": lot * (44 + i)}}
                for i in range(9)]
        assert desk.lot_size_from_chain(rows) == lot


def test_a_chain_too_thin_to_measure_declines():
    assert desk.lot_size_from_chain([]) is None
    assert desk.lot_size_from_chain(None) is None
    assert desk.lot_size_from_chain(
        [{"ce": {"oi": 650}, "pe": {"oi": 650}}]) is None


def test_a_coincidental_small_factor_is_not_a_lot_size():
    """Every value merely being even must not 'derive' a lot size of 2 and
    size a crore-scale book against it."""
    rows = [{"k": i, "ce": {"oi": 2 * (i + 1), "vol": 2 * (i + 7)},
             "pe": {"oi": 2 * (i + 3), "vol": 2 * (i + 11)}} for i in range(9)]
    assert desk.lot_size_from_chain(rows) is None


def test_a_measured_lot_size_beats_the_fallback_table():
    rows = [{"k": 24000 + i * 50,
             "ce": {"oi": 65 * (900 + i), "vol": 65 * (30 + i)},
             "pe": {"oi": 65 * (700 + i), "vol": 65 * (44 + i)}}
            for i in range(9)]
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()),
                    strikes=rows)
    assert d.lot_size == 65 and d.lot_size_src == "measured"


def test_an_assumed_lot_size_says_so_out_loud():
    """Every sizing figure rides on it, so a fallback must be visible."""
    d = desk.decide(_surf(RICH_BOTH), desk.regime_from_chain(_doc()),
                    strikes=[])
    assert d.lot_size_src == "assumed"
    assert any("ASSUMED" in w for w in d.why)


def test_the_fallback_table_matches_the_real_sizes():
    assert desk.LOT_SIZE == {"NIFTY": 65, "BANKNIFTY": 30, "SENSEX": 20}
