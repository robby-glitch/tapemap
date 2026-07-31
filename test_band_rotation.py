"""band_rotation.py -- the operator's own setup, band extreme + reversal.

Fixtures use the shape `live.build_contract` really returns (read from
`live._leg_series` / `live._align_to_axis`): one leg is
``{"bars": [...], "vwap": [...], "oi": [...], "bar_days": [...]}`` with every
array indexed by the SHARED axis, so `CE.bars[i]` and `PE.bars[i]` are the same
minute of the same session -- or an explicit `None` where that leg did not
print. Bars carry `contract_bars.BAR_KEYS` (`t,o,h,l,c,v,oi`), bands carry
`BAND_KEYS` (`vwap,u1,d1,u2,d2,u3,d3`).

Families:
  1. Trigger    -- BUY at d2/d3, SELL only at u3, tag alone never fires.
  2. Confirm    -- the other leg rotating, plus OI DECELERATION on both legs.
  3. Positioning-- a heavy book on the side being bought must NOT suppress.
  4. Trap       -- CLEAR / SUSPECT / UNKNOWN off the pre-move PRICE range:
                    its trailing rank, its dwell, its direction, and the
                    operator's 09:25 anchor.
  5. Causality  -- truncation reproduces full records, byte for byte.
  6. Independence -- the same shape at BANKNIFTY/SENSEX premium magnitudes
                    yields the same signals (no absolute threshold crept in).
  7. Junk input -- never raises, never fabricates.
"""

import band_rotation
from band_rotation import detect

DAY = "2026-07-30"
VWAP = 100.0
SD = 5.0

# Bars that cannot fire anything: at sd=2 d2=96 and low is 99; at sd=10
# u3=130 and high is 101. Deliberately inert at every band width used here.
FILL = (99.0, 101.0, 100.0)
BUY_D2_SD5 = (89.0, 101.0, 100.0)      # low 89 <= d2 90, closes 100 above it
BUY_D3_SD5 = (84.0, 101.0, 100.0)      # low 84 <= d3 85, closes 100 above it
TAG_NO_REV = (89.0, 92.0, 88.0)        # low 89 <= d2 90 but closes 88 below
SELL_U3_SD5 = (99.0, 116.0, 100.0)     # high 116 >= u3 115, closes 100 below
TAG_U2_REV = (99.0, 111.0, 100.0)      # +2 sigma tag + reversal: NOT a sell
BUY_D2_SD10 = (79.0, 101.0, 100.0)     # d2 is 80 when sd is 10
UP_FROM_D2 = (89.0, 101.0, 89.5)       # the mirror rotation tag (lower band)

# Price-range rows for the trap family. Each is inert against every band used
# here; only the HIGH/LOW SPREAD differs, which is the whole point -- the
# compression read is on price, and the bands never move in these scenes.
WIDE = (95.0, 105.0, 100.0)            # spread 10.00
NARROW = (99.9, 100.1, 100.0)          # spread  0.20
TIGHT = (99.95, 100.05, 100.0)         # spread  0.10


def _t(i):
    m = 9 * 60 + 15 + i
    return "%02d:%02d" % (m // 60, m % 60)


def _band(vwap, sd):
    return {"vwap": vwap, "u1": vwap + sd, "d1": vwap - sd,
            "u2": vwap + 2 * sd, "d2": vwap - 2 * sd,
            "u3": vwap + 3 * sd, "d3": vwap - 3 * sd}


def _decel(n, base=100000.0, step=500.0, drop=20.0):
    """OI still building but the RATE of building falls every bar."""
    out, cur, inc = [], base, step
    for _ in range(n):
        out.append(cur)
        cur += inc
        inc -= drop
    return out


def _accel(n, base=100000.0, step=100.0, rise=20.0):
    out, cur, inc = [], base, step
    for _ in range(n):
        out.append(cur)
        cur += inc
        inc += rise
    return out


def _rows(n, overrides=None):
    rows = [FILL] * n
    for i, r in (overrides or {}).items():
        rows[i] = r
    return rows


def _leg(rows, oi, sds=None, vwap=VWAP, sd=SD, scale=1.0, day=DAY):
    """rows[i] is None (this leg did not print) or (low, high, close)."""
    bars, bands, ois, days = [], [], [], []
    for i, r in enumerate(rows):
        s = (sds[i] if sds else sd) * scale
        if r is None:
            bars.append(None)
            bands.append(None)
            ois.append(None)
        else:
            low, high, close = (v * scale for v in r)
            bars.append({"t": _t(i), "o": close, "h": high, "l": low,
                         "c": close, "v": 1000.0, "oi": oi[i]})
            bands.append(_band(vwap * scale, s))
            ois.append(oi[i])
        days.append(day)
    return {"bars": bars, "vwap": bands, "oi": ois, "bar_days": days}


def _fired(out):
    return [r for r in out if r is not None]


def _shape(out):
    """The categorical part of every record -- no formatted numbers."""
    return [(r["i"], r["side"], r["leg"], r["band"], r["confirm"], r["trap"])
            for r in _fired(out)]


def _scene(n=21, trig=20, trig_row=BUY_D2_SD5, trig_leg="CE",
           other_tag=14, other_tag_row=TAG_U2_REV, sds=None,
           ce_oi=None, pe_oi=None, scale=1.0, holes=(), pre=None):
    """The canonical CONFIRMED scenario, with knobs for what each test breaks.

    CE fires at `trig`; PE tags its +2 sigma at `other_tag` and is back below
    it by `trig`; both books are decelerating. `pre` overwrites rows on the
    TRIGGERING leg -- the run-up the trap filter reads.
    """
    trig_rows = dict(pre or {})
    if trig is not None:
        trig_rows[trig] = trig_row
    other_rows = {other_tag: other_tag_row} if other_tag is not None else {}
    if trig_leg == "PE":
        trig_rows, other_rows = other_rows, trig_rows
    ce_rows, pe_rows = _rows(n, trig_rows), _rows(n, other_rows)
    for i in holes:
        pe_rows[i] = None
    ce = _leg(ce_rows, ce_oi or _decel(n), sds=sds, scale=scale)
    pe = _leg(pe_rows, pe_oi or _decel(n, base=80000.0), scale=scale)
    return {"CE": ce, "PE": pe}


# ---------------------------------------------------------------- 1. trigger

def test_buy_fires_on_a_d2_tag_with_a_same_bar_reversal():
    out = detect(_scene())
    assert len(out) == 21
    assert _shape(out) == [(20, "BUY", "CE", "d2", "CONFIRMED", "SUSPECT")]
    rec = out[20]
    assert "89.00" in rec["trigger"] and "90.00" in rec["trigger"]
    assert "100.00" in rec["trigger"]


def test_a_tag_with_no_reversal_does_not_fire():
    # Identical to the firing case except the bar closes BELOW the band it
    # tagged. The touch is not the signal; the reversal is.
    assert _fired(detect(_scene(trig_row=TAG_NO_REV))) == []


def test_a_d3_tag_is_reported_as_d3_not_d2():
    out = detect(_scene(trig_row=BUY_D3_SD5))
    assert _shape(out) == [(20, "BUY", "CE", "d3", "CONFIRMED", "SUSPECT")]
    assert "85.00" in out[20]["trigger"]


def test_sell_needs_u3_a_u2_reversal_is_not_a_sell():
    # The operator's asymmetry, encoded: buy at -2 OR -3 sigma, sell only at
    # +3. A +2 sigma tag that reverses is not a sell and must not be
    # "symmetrised" into one.
    assert _fired(detect(_scene(trig_row=TAG_U2_REV, other_tag=None))) == []
    out = detect(_scene(trig_row=SELL_U3_SD5, other_tag_row=UP_FROM_D2))
    assert _shape(out) == [(20, "SELL", "CE", "u3", "CONFIRMED", "SUSPECT")]
    assert "116.00" in out[20]["trigger"] and "115.00" in out[20]["trigger"]


def test_a_sell_tag_with_no_reversal_does_not_fire():
    assert _fired(detect(_scene(trig_row=(99.0, 117.0, 116.5)))) == []


def test_nothing_fires_where_nothing_touches_a_band():
    assert _fired(detect(_scene(trig=None, other_tag=None))) == []


# ---------------------------------------------------------------- 2. confirm

def test_confirmation_needs_the_other_leg_coming_down_from_its_upper_band():
    out = detect(_scene(other_tag=None))
    assert out[20]["confirm"] == "UNCONFIRMED"
    assert "did not tag" in out[20]["confirm_why"]

    out = detect(_scene())                      # PE tagged u2 six bars back
    assert out[20]["confirm"] == "CONFIRMED"
    assert "110.00" in out[20]["confirm_why"]   # the u2 it came down from


def test_a_stale_rotation_tag_outside_the_window_does_not_confirm():
    # Same tag, but 20 bars back rather than 6: the pair is not rotating now.
    out = detect(_scene(n=32, trig=31, other_tag=5))
    assert out[31]["confirm"] == "UNCONFIRMED"


def test_the_other_leg_must_be_back_below_the_band_it_tagged():
    # It tagged u2 and is still sitting on it at the trigger bar -- stretched,
    # not rotating.
    out = detect(_scene(other_tag=20, other_tag_row=(109.0, 111.0, 111.0)))
    assert out[20]["confirm"] == "UNCONFIRMED"


def test_oi_deceleration_is_required_on_both_legs():
    base = detect(_scene())
    assert base[20]["confirm"] == "CONFIRMED"

    slowing = detect(_scene(ce_oi=_accel(21)))
    assert slowing[20]["confirm"] == "UNCONFIRMED"
    assert "CE" in slowing[20]["confirm_why"]

    slowing = detect(_scene(pe_oi=_accel(21, base=80000.0)))
    assert slowing[20]["confirm"] == "UNCONFIRMED"
    assert "PE" in slowing[20]["confirm_why"]


def test_oi_read_is_rank_and_sign_only_not_a_lot_count():
    # The same OI SHAPE at a hundred times the size decides the same way.
    big = [v * 100.0 for v in _decel(21)]
    assert detect(_scene(ce_oi=big))[20]["confirm"] == "CONFIRMED"


def test_too_little_oi_history_is_unknown_not_confirmed():
    out = detect(_scene(n=9, trig=8, other_tag=4))
    assert out[8]["confirm"] == "UNKNOWN"
    assert "OI" in out[8]["confirm_why"]


def test_a_missing_other_leg_bar_yields_unknown_never_a_fabricated_read():
    out = detect(_scene(holes=(20,)))
    assert out[20]["side"] == "BUY"            # our own leg still triggered
    assert out[20]["confirm"] == "UNKNOWN"
    assert "did not print" in out[20]["confirm_why"]


def test_a_hole_inside_the_rotation_window_is_unknown_not_absence():
    # No tag among the bars we could read, but bars we could not read sit
    # inside the window: that is "we cannot tell", not "it did not happen".
    out = detect(_scene(other_tag=None, holes=(14, 15)))
    assert out[20]["confirm"] == "UNKNOWN"


def test_a_single_leg_request_confirms_nothing_rather_than_inventing_it():
    legs = _scene()
    out = detect({"CE": legs["CE"]})
    assert out[20]["side"] == "BUY"
    assert out[20]["confirm"] == "UNKNOWN"


# ------------------------------------------------------------ 3. positioning

def test_a_heavy_book_on_the_bought_side_does_not_suppress_the_signal():
    """The operator: 'suppose book is put heavy but put prices are touching
    the last band so we can except a bounce from there'. Buying the PE while
    the PE book is enormous is the setup, not a reason to stay out."""
    n = 21
    light = detect(_scene(trig_leg="PE", trig_row=BUY_D2_SD5,
                          other_tag_row=TAG_U2_REV))
    # The same PE book, 250x bigger and 5 million lots deep: put-heavy, and
    # the leg being bought is the put.
    heavy_oi = [v * 250.0 + 5_000_000.0 for v in _decel(n, base=80000.0)]
    heavy = detect(_scene(trig_leg="PE", trig_row=BUY_D2_SD5,
                          other_tag_row=TAG_U2_REV, pe_oi=heavy_oi))

    assert _shape(light) == [(20, "BUY", "PE", "d2", "CONFIRMED", "SUSPECT")]
    assert _shape(heavy) == _shape(light)


# ------------------------------------------------------------------- 4. trap

def _coil(n=21, wide_to=15, box=NARROW):
    """Wide range all session, then a coil of `box` bars up to the trigger."""
    return {**{i: WIDE for i in range(wide_to)},
            **{i: box for i in range(wide_to, n - 1)}}


def _taper(a, b, spread=0.30, step=0.02):
    """A coil that keeps TIGHTENING: bar `a` spans `spread` and every bar
    after it a step less, so each rolling range reading is a new low and the
    dwell can run the whole length of it. Everything before `a` is WIDE."""
    rows = {i: WIDE for i in range(a)}
    for k in range(a, b):
        half = (spread - step * (k - a)) / 2
        rows[k] = (100.0 - half, 100.0 + half, 100.0)
    return rows


def test_trap_clear_when_price_coiled_into_the_move():
    out = detect(_scene(pre=_coil()))
    rec = out[20]
    assert rec["trap"] == "CLEAR"
    assert "rank" in rec["trap_why"] and "narrowing" in rec["trap_why"]
    assert rec["trap_dwell"] == 5
    assert "for 5 consecutive bar(s)" in rec["trap_why"]


def test_the_band_envelope_does_not_decide_it_price_does():
    """The operator's own chart is a WIDE +/-1 sigma region with price
    grinding in a thin strip inside it. Widening every band while leaving
    price alone must not change the verdict, and squeezing every band while
    price keeps swinging must not manufacture one."""
    coil = _coil()
    tight_bands = detect(_scene(pre=coil, sds=[1.0] * 21))
    wide_bands = detect(_scene(pre=coil, sds=[5.0] * 21))
    assert tight_bands[20]["trap"] == wide_bands[20]["trap"] == "CLEAR"

    # No coil in price; bands squeezed hard right before the move. The old
    # band-width filter called this compression -- it is not.
    squeezed = detect(_scene(sds=[10.0] * 15 + [3.0] * 5 + [10.0],
                             trig_row=BUY_D2_SD10))
    assert _shape(squeezed) == [(20, "BUY", "CE", "d2", "CONFIRMED",
                                 "SUSPECT")]


def test_trap_suspect_says_what_it_measured_and_asserts_no_expansion():
    """Regression: the receipt used to claim 'bands were already wide ... no
    prior coil' at every non-CLEAR rank, including a session where the range
    never changed at all. It must state the measurement, not an event."""
    rec = detect(_scene())[20]                 # every bar the same width
    assert rec["trap"] == "SUSPECT"
    why = rec["trap_why"]
    assert "already wide" not in why and "expanding" not in why
    assert "rank 1.00" in why and "not in the bottom 30%" in why
    assert "flat" in why                       # what the range actually did


def test_a_narrow_range_that_is_already_expanding_is_suspect():
    """*'the whole vwap bands are expanding not narrowing or staying flat'* --
    the level alone is not enough, the direction of change is a second read.
    Here the range still ranks in the bottom 30% but it has already started
    opening up, so the coil was breaking before the trigger bar."""
    n = 31
    pre = {**{i: WIDE for i in range(20)},
           **{i: TIGHT for i in range(20, 25)},
           **{i: NARROW for i in range(25, 30)}}
    rec = detect(_scene(n=n, trig=30, other_tag=24, pre=pre))[30]
    assert rec["trap"] == "SUSPECT"
    assert "bottom 30%" in rec["trap_why"]     # it WAS narrow
    assert "expanding" in rec["trap_why"]      # and that is why it failed
    assert rec["trap_dwell"] == 10


def test_dwell_counts_how_long_the_range_has_stayed_that_narrow():
    """*'is its a good thing to notice ... for how long the price are in this
    range'*. A coil that keeps tightening for 15 bars reports 15; a five-bar
    one reports five; a session that never compressed reports none. The count
    is a separate reading from the rank and never changes the verdict."""
    n = 61
    long_coil = detect(_scene(n=n, trig=60, other_tag=54,
                              pre=_taper(45, 60)))[60]
    assert long_coil["trap"] == "CLEAR"
    assert long_coil["trap_dwell"] == 15
    assert "for 15 consecutive bar(s)" in long_coil["trap_why"]

    short_coil = detect(_scene(pre=_coil()))[20]
    assert short_coil["trap"] == "CLEAR"
    assert short_coil["trap_dwell"] == 5

    flat = detect(_scene())[20]                 # never compressed at all
    assert flat["trap_dwell"] == 0
    assert "not holding a narrow range" in flat["trap_why"]


def test_no_compression_verdict_before_the_operators_0925_anchor():
    """*'by 9:25 we have the values for vwap standard deviation and from there
    we judge'*. The anchor is read off the bar's own clock label, so it lands
    at 09:25 whatever the bar interval is."""
    early = detect(_scene(n=11, trig=9, other_tag=4))[9]     # 09:24
    assert early["trap"] == "UNKNOWN"
    assert "09:25" in early["trap_why"] and "09:24" in early["trap_why"]

    # One bar later is past the anchor -- and still UNKNOWN, but now for the
    # honest reason that there is nothing to rank against yet.
    late = detect(_scene(n=12, trig=10, other_tag=4))[10]    # 09:25
    assert late["trap"] == "UNKNOWN"
    assert "history" in late["trap_why"] and "09:25" not in late["trap_why"]


def test_an_unlabelled_bar_is_unknown_rather_than_assumed_late_enough():
    legs = _scene(pre=_coil())
    legs["CE"]["bars"][20] = dict(legs["CE"]["bars"][20], t=None)
    rec = detect(legs)[20]
    assert rec["trap"] == "UNKNOWN"
    assert rec["trap_dwell"] is None
    assert "clock" in rec["trap_why"]


def test_trap_range_is_normalised_so_a_bigger_premium_is_not_wider():
    coil = _coil()
    small = detect(_scene(pre=coil))
    big = detect(_scene(pre=coil, scale=9.0))
    assert small[20]["trap"] == big[20]["trap"] == "CLEAR"
    assert small[20]["trap_dwell"] == big[20]["trap_dwell"]


def test_the_rank_is_trailing_not_session_so_far():
    """The first version ranked against the session so far, which -- because
    sigma accumulates from the 09:15 anchor -- measured how LATE it was. The
    same coil must read the same whether it sits early or late in a session."""
    early = detect(_scene(n=21, trig=20, other_tag=14, pre=_coil()))[20]
    late = detect(_scene(n=61, trig=60, other_tag=54,
                         pre=_coil(n=61, wide_to=55)))[60]
    assert early["trap"] == late["trap"] == "CLEAR"
    assert early["trap_dwell"] == late["trap_dwell"] == 5


# --------------------------------------------------------------- 4b. one bar

def test_when_both_legs_fire_on_one_bar_the_loser_is_named_not_dropped():
    """Both legs at their extremes on one minute is the operator's rotation in
    its purest form. One record still comes out -- but the hit that lost the
    tie-break is named, so a consumer can see that it qualified."""
    n = 21
    ce = _leg(_rows(n, {20: BUY_D2_SD5}), _decel(n))
    pe = _leg(_rows(n, {20: BUY_D3_SD5}), _decel(n, base=80000.0))
    out = detect({"CE": ce, "PE": pe})
    assert len(_fired(out)) == 1               # still exactly one per bar
    rec = out[20]
    assert (rec["leg"], rec["band"]) == ("PE", "d3")     # deeper sigma wins
    assert rec["also"] == ["CE low 89.00 <= d2 90.00 and the same bar closed "
                           "100.00 back above it"]
    assert "qualified on this same bar" in rec["trigger"]


def test_an_equal_sigma_tie_goes_to_ce_and_still_names_the_pe_hit():
    n = 21
    ce = _leg(_rows(n, {20: BUY_D2_SD5}), _decel(n))
    pe = _leg(_rows(n, {20: BUY_D2_SD5}), _decel(n, base=80000.0))
    out = detect({"CE": ce, "PE": pe})
    assert len(_fired(out)) == 1
    assert (out[20]["leg"], out[20]["band"]) == ("CE", "d2")
    assert out[20]["also"] and out[20]["also"][0].startswith("PE low")


def test_a_lone_hit_names_no_other_leg():
    assert detect(_scene())[20]["also"] is None


# -------------------------------------------------------------- 5. causality

def test_truncation_reproduces_the_full_records_exactly():
    """Bar i is a function of bars <= i, so replaying half the session must
    reproduce the first half's records field for field -- not merely the same
    number of them."""
    legs = _scene(n=21, trig=20, other_tag=14)
    legs["CE"]["bars"][12] = dict(legs["CE"]["bars"][12],
                                  l=89.0, h=101.0, c=100.0)
    full = detect(legs)
    assert full[12] is not None and full[20] is not None

    for k in (13, 15, 18, 21):
        cut = {s: {"bars": leg["bars"][:k], "vwap": leg["vwap"][:k],
                   "oi": leg["oi"][:k], "bar_days": leg["bar_days"][:k]}
               for s, leg in legs.items()}
        assert detect(cut) == full[:k], f"replay diverged at k={k}"


def test_a_later_bar_cannot_change_an_earlier_record():
    legs = _scene(n=21, trig=12, other_tag=6)
    before = detect(legs)
    legs["CE"]["bars"][20] = dict(legs["CE"]["bars"][20], l=1.0, c=100.0)
    assert detect(legs)[:13] == before[:13]


def test_sessions_do_not_bleed_into_each_other():
    # Two sessions on one axis: yesterday's compression cannot rank today's
    # bar, and yesterday's tag cannot confirm today's trigger.
    n = 21
    legs = _scene(n=n, trig=20, other_tag=14)
    for leg in legs.values():
        leg["bar_days"] = [DAY] * 15 + ["2026-07-31"] * 6
    out = detect(legs)
    assert out[20]["confirm"] == "UNCONFIRMED"   # the tag is in the prior day
    assert out[20]["trap"] == "UNKNOWN"          # only 7 bars of today


# ----------------------------------------------------------- 6. independence

def test_index_independence_the_same_shape_at_any_premium_magnitude():
    """NIFTY premiums live near 100, BANKNIFTY/SENSEX near 1000. Scaling the
    whole series must not change a single signal -- if it does, an absolute
    market threshold crept in."""
    coil = _coil()
    ref = _shape(detect(_scene(pre=coil)))
    assert ref and ref[0][-1] == "CLEAR"
    for k in (0.4, 3.0, 8.0, 25.0):
        got = _shape(detect(_scene(pre=coil, scale=k)))
        assert got == ref, f"scale {k} changed the signals"


# ------------------------------------------------------------- 7. junk input

def test_junk_input_returns_empty_and_never_raises():
    assert detect(None) == []
    assert detect({}) == []
    assert detect({"CE": None, "PE": None}) == []
    assert detect({"CE": {"bars": [], "vwap": [], "oi": []}}) == []


def test_a_none_bar_on_the_firing_leg_simply_has_no_record():
    legs = _scene()
    legs["CE"]["bars"][20] = None
    legs["CE"]["vwap"][20] = None
    assert _fired(detect(legs)) == []


def test_a_missing_band_is_not_treated_as_zero():
    legs = _scene()
    legs["CE"]["vwap"][20] = dict(legs["CE"]["vwap"][20], d2=None, d3=None)
    assert _fired(detect(legs)) == []


def test_a_whole_contract_payload_is_accepted_too():
    legs = _scene()
    payload = {"legs": legs, "axis": [[DAY, _t(i)] for i in range(21)]}
    assert detect(payload) == detect(legs)


def test_the_named_constants_are_documented_windows_not_price_levels():
    for name in ("ROTATION_WINDOW", "OI_WINDOW", "RANGE_WINDOW",
                 "TRAIL_WINDOW", "TRAIL_MIN"):
        assert isinstance(getattr(band_rotation, name), int)
    assert 0.0 < band_rotation.COMPRESSION_RANK < 1.0
    # The one clock time in the module is the operator's own 09:25 anchor --
    # a session landmark, not a market level.
    assert band_rotation.ANCHOR_HHMM == "09:25"
    assert band_rotation.ANCHOR_MINUTE == 9 * 60 + 25
