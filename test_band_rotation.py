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
  4. Trap       -- CLEAR / SUSPECT / UNKNOWN off pre-move band width rank.
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
           ce_oi=None, pe_oi=None, scale=1.0, holes=()):
    """The canonical CONFIRMED scenario, with knobs for what each test breaks.

    CE fires at `trig`; PE tags its +2 sigma at `other_tag` and is back below
    it by `trig`; both books are decelerating.
    """
    trig_rows = {trig: trig_row} if trig is not None else {}
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

def test_trap_clear_when_the_move_emerged_from_compression():
    # Wide all session, then five compressed bars, then the break.
    sds = [10.0] * 15 + [2.0] * 5 + [10.0]
    out = detect(_scene(trig_row=BUY_D2_SD10, sds=sds))
    assert out[20]["trap"] == "CLEAR"
    assert "rank" in out[20]["trap_why"]


def test_trap_suspect_when_band_width_was_already_wide():
    sds = [2.0] * 15 + [10.0] * 6
    out = detect(_scene(trig_row=BUY_D2_SD10, sds=sds))
    assert out[20]["trap"] == "SUSPECT"


def test_trap_unknown_with_too_little_session_history_never_clear():
    out = detect(_scene(n=8, trig=7, other_tag=3))
    assert out[7]["trap"] == "UNKNOWN"
    assert out[7]["trap"] != "CLEAR"
    assert "history" in out[7]["trap_why"]


def test_trap_width_is_normalised_so_a_bigger_premium_is_not_wider():
    sds = [10.0] * 15 + [2.0] * 5 + [10.0]
    small = detect(_scene(trig_row=BUY_D2_SD10, sds=sds))
    big = detect(_scene(trig_row=BUY_D2_SD10, sds=sds, scale=9.0))
    assert small[20]["trap"] == big[20]["trap"] == "CLEAR"


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
    sds = [10.0] * 15 + [2.0] * 5 + [10.0]
    ref = _shape(detect(_scene(trig_row=BUY_D2_SD10, sds=sds)))
    assert ref
    for k in (0.4, 3.0, 8.0, 25.0):
        got = _shape(detect(_scene(trig_row=BUY_D2_SD10, sds=sds, scale=k)))
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
    for name in ("ROTATION_WINDOW", "OI_WINDOW", "TRAP_LOOKBACK",
                 "TRAP_MIN_HISTORY"):
        assert isinstance(getattr(band_rotation, name), int)
    assert 0.0 < band_rotation.COMPRESSION_RANK < 1.0
