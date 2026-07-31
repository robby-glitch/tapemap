"""band_rotation.py -- the operator's own setup, band extreme + reversal.

Fixtures use the shape `live.build_contract` really returns (read from
`live._leg_series` / `live._align_to_axis`): one leg is
``{"bars": [...], "vwap": [...], "oi": [...], "bar_days": [...]}`` with every
array indexed by the SHARED axis, so `CE.bars[i]` and `PE.bars[i]` are the same
minute of the same session -- or an explicit `None` where that leg did not
print. Bars carry `contract_bars.BAR_KEYS` (`t,o,h,l,c,v,oi`), bands carry
`BAND_KEYS` (`vwap,u1,d1,u2,d2,u3,d3`).

The INDEX series is the second input and rides the same shape (that is what
`live._leg_series` returns when pointed at the futures security id). Every
trap fixture drives it and nothing else: the trigger is on the option leg, the
squeeze is on the index -- *"squeeze on index entry on option chart"*.

Families:
  1. Trigger    -- BUY at d2/d3, SELL only at u3, tag alone never fires.
  2. Confirm    -- the other leg rotating, plus OI DECELERATION on both legs.
  3. Positioning-- a heavy book on the side being bought must NOT suppress.
  4. Trap       -- CLEAR / SUSPECT / UNKNOWN off the INDEX band width: its
                    trailing rank, its dwell, its direction, the operator's
                    09:25 anchor, and their own 2026-07-30 reference session.
  5. Causality  -- truncation reproduces full records, byte for byte.
  6. Independence -- the same shape at BANKNIFTY/SENSEX magnitudes yields the
                    same signals (no absolute threshold crept in).
  7. Junk input -- never raises, never fabricates.
"""

import band_rotation
from band_rotation import detect

DAY = "2026-07-30"
DAY2 = "2026-07-31"
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

# Option-premium rows whose only difference is the HIGH/LOW SPREAD. Version
# two of this module ranked exactly this and it is now inert by design: the
# compression read left the premium entirely.
WIDE = (95.0, 105.0, 100.0)            # spread 10.00
NARROW = (99.9, 100.1, 100.0)          # spread  0.20

# The index band width used wherever a test is NOT about compression. It never
# changes, so it ranks 1.00, is never compression, and every such test gets a
# definite SUSPECT instead of an UNKNOWN that would hide which gate it is
# really exercising.
FLAT_W = 100.0
LEVEL = 24000.0                        # a NIFTY-ish index level


def _t(i):
    m = 9 * 60 + 15 + i
    return "%02d:%02d" % (m // 60, m % 60)


def _band(vwap, sd):
    return {"vwap": vwap, "u1": vwap + sd, "d1": vwap - sd,
            "u2": vwap + 2 * sd, "d2": vwap - 2 * sd,
            "u3": vwap + 3 * sd, "d3": vwap - 3 * sd}


# ------------------------------------------------------------- index fixtures

def _ix_days(widths, days, t0=0, level=LEVEL, scale=1.0):
    """A leg-shaped INDEX series: reading `k` is a band `widths[k]` points
    wide (u3 - d3), centred on `level`, labelled `_t(t0 + k)` on `days[k]`."""
    bars, bands, out_days = [], [], []
    for k, w in enumerate(widths):
        half = w * scale / 2.0
        lvl = level * scale
        bars.append({"t": _t(t0 + k)})
        bands.append({"vwap": lvl,
                      "u1": lvl + half / 3.0, "d1": lvl - half / 3.0,
                      "u2": lvl + 2 * half / 3.0, "d2": lvl - 2 * half / 3.0,
                      "u3": lvl + half, "d3": lvl - half})
        out_days.append(days[k])
    return {"bars": bars, "vwap": bands, "bar_days": out_days}


def _ix(widths, day=DAY, t0=0, level=LEVEL, scale=1.0):
    return _ix_days(widths, [day] * len(widths), t0, level, scale)


def _flat(n, w=FLAT_W, day=DAY):
    return _ix([w] * n, day=day)


def _squeeze(n, wide=100.0, tail=(90.0, 80.0, 70.0, 60.0, 50.0)):
    """Wide all session, then a tail that keeps TIGHTENING into the move."""
    return [wide] * (n - 1 - len(tail)) + list(tail) + [wide]


def _n_of(legs):
    for leg in legs.values():
        if isinstance(leg, dict) and leg.get("bars"):
            return len(leg["bars"])
    return 0


def _run(legs, idx=None, n=None, **kw):
    """`detect` with an index series -- flat by default (see FLAT_W)."""
    if idx is None:
        idx = _flat(n or _n_of(legs))
    return detect(legs, index_series=idx, **kw)


# -------------------------------------------------------------- leg fixtures

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
    TRIGGERING leg -- the option-premium run-up, which the trap read no longer
    looks at and which several tests use to prove exactly that.
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
    out = _run(_scene())
    assert len(out) == 21
    assert _shape(out) == [(20, "BUY", "CE", "d2", "CONFIRMED", "SUSPECT")]
    rec = out[20]
    assert "89.00" in rec["trigger"] and "90.00" in rec["trigger"]
    assert "100.00" in rec["trigger"]


def test_a_tag_with_no_reversal_does_not_fire():
    # Identical to the firing case except the bar closes BELOW the band it
    # tagged. The touch is not the signal; the reversal is.
    assert _fired(_run(_scene(trig_row=TAG_NO_REV))) == []


def test_a_d3_tag_is_reported_as_d3_not_d2():
    out = _run(_scene(trig_row=BUY_D3_SD5))
    assert _shape(out) == [(20, "BUY", "CE", "d3", "CONFIRMED", "SUSPECT")]
    assert "85.00" in out[20]["trigger"]


def test_sell_needs_u3_a_u2_reversal_is_not_a_sell():
    # The operator's asymmetry, encoded: buy at -2 OR -3 sigma, sell only at
    # +3. A +2 sigma tag that reverses is not a sell and must not be
    # "symmetrised" into one.
    assert _fired(_run(_scene(trig_row=TAG_U2_REV, other_tag=None))) == []
    out = _run(_scene(trig_row=SELL_U3_SD5, other_tag_row=UP_FROM_D2))
    assert _shape(out) == [(20, "SELL", "CE", "u3", "CONFIRMED", "SUSPECT")]
    assert "116.00" in out[20]["trigger"] and "115.00" in out[20]["trigger"]


def test_a_sell_tag_with_no_reversal_does_not_fire():
    assert _fired(_run(_scene(trig_row=(99.0, 117.0, 116.5)))) == []


def test_nothing_fires_where_nothing_touches_a_band():
    assert _fired(_run(_scene(trig=None, other_tag=None))) == []


# ---------------------------------------------------------------- 2. confirm

def test_confirmation_needs_the_other_leg_coming_down_from_its_upper_band():
    out = _run(_scene(other_tag=None))
    assert out[20]["confirm"] == "UNCONFIRMED"
    assert "did not tag" in out[20]["confirm_why"]

    out = _run(_scene())                        # PE tagged u2 six bars back
    assert out[20]["confirm"] == "CONFIRMED"
    assert "110.00" in out[20]["confirm_why"]   # the u2 it came down from


def test_a_stale_rotation_tag_outside_the_window_does_not_confirm():
    # Same tag, but 20 bars back rather than 6: the pair is not rotating now.
    out = _run(_scene(n=32, trig=31, other_tag=5))
    assert out[31]["confirm"] == "UNCONFIRMED"


def test_the_other_leg_must_be_back_below_the_band_it_tagged():
    # It tagged u2 and is still sitting on it at the trigger bar -- stretched,
    # not rotating.
    out = _run(_scene(other_tag=20, other_tag_row=(109.0, 111.0, 111.0)))
    assert out[20]["confirm"] == "UNCONFIRMED"


def test_oi_deceleration_is_required_on_both_legs():
    base = _run(_scene())
    assert base[20]["confirm"] == "CONFIRMED"

    slowing = _run(_scene(ce_oi=_accel(21)))
    assert slowing[20]["confirm"] == "UNCONFIRMED"
    assert "CE" in slowing[20]["confirm_why"]

    slowing = _run(_scene(pe_oi=_accel(21, base=80000.0)))
    assert slowing[20]["confirm"] == "UNCONFIRMED"
    assert "PE" in slowing[20]["confirm_why"]


def test_oi_read_is_rank_and_sign_only_not_a_lot_count():
    # The same OI SHAPE at a hundred times the size decides the same way.
    big = [v * 100.0 for v in _decel(21)]
    assert _run(_scene(ce_oi=big))[20]["confirm"] == "CONFIRMED"


def test_too_little_oi_history_is_unknown_not_confirmed():
    out = _run(_scene(n=9, trig=8, other_tag=4))
    assert out[8]["confirm"] == "UNKNOWN"
    assert "OI" in out[8]["confirm_why"]


def test_a_missing_other_leg_bar_yields_unknown_never_a_fabricated_read():
    out = _run(_scene(holes=(20,)))
    assert out[20]["side"] == "BUY"            # our own leg still triggered
    assert out[20]["confirm"] == "UNKNOWN"
    assert "did not print" in out[20]["confirm_why"]


def test_a_hole_inside_the_rotation_window_is_unknown_not_absence():
    # No tag among the bars we could read, but bars we could not read sit
    # inside the window: that is "we cannot tell", not "it did not happen".
    out = _run(_scene(other_tag=None, holes=(14, 15)))
    assert out[20]["confirm"] == "UNKNOWN"


def test_a_single_leg_request_confirms_nothing_rather_than_inventing_it():
    legs = _scene()
    out = _run({"CE": legs["CE"]})
    assert out[20]["side"] == "BUY"
    assert out[20]["confirm"] == "UNKNOWN"


# ------------------------------------------------------------ 3. positioning

def test_a_heavy_book_on_the_bought_side_does_not_suppress_the_signal():
    """The operator: 'suppose book is put heavy but put prices are touching
    the last band so we can except a bounce from there'. Buying the PE while
    the PE book is enormous is the setup, not a reason to stay out."""
    n = 21
    light = _run(_scene(trig_leg="PE", trig_row=BUY_D2_SD5,
                        other_tag_row=TAG_U2_REV))
    # The same PE book, 250x bigger and 5 million lots deep: put-heavy, and
    # the leg being bought is the put.
    heavy_oi = [v * 250.0 + 5_000_000.0 for v in _decel(n, base=80000.0)]
    heavy = _run(_scene(trig_leg="PE", trig_row=BUY_D2_SD5,
                        other_tag_row=TAG_U2_REV, pe_oi=heavy_oi))

    assert _shape(light) == [(20, "BUY", "PE", "d2", "CONFIRMED", "SUSPECT")]
    assert _shape(heavy) == _shape(light)


# ------------------------------------------------------------------- 4. trap

def test_no_index_series_is_unknown_and_never_clear():
    """The whole point of the rebuild: the squeeze is read on the index. With
    no index series there is no read, and 'we could not check' must never be
    reported as 'we checked and it is fine'."""
    rec = detect(_scene(pre={i: NARROW for i in range(20)}))[20]
    assert rec["trap"] == "UNKNOWN"
    assert rec["trap_dwell"] is None
    assert "no index series was supplied" in rec["trap_why"]
    assert "never" in rec["trap_why"]          # ... fallen back to premium


def test_trap_clear_when_the_index_band_squeezed_into_the_move():
    rec = _run(_scene(), idx=_ix(_squeeze(21)))[20]
    assert rec["trap"] == "CLEAR"
    assert "rank" in rec["trap_why"] and "narrowing" in rec["trap_why"]
    assert "50.0 points" in rec["trap_why"]    # the width it really measured
    assert rec["trap_dwell"] == 5
    assert "for 5 consecutive bar(s)" in rec["trap_why"]


def test_the_option_leg_does_not_decide_it_the_index_band_does():
    """The correction of 2026-07-31, locked down in both directions. Version
    two of this module ranked the OPTION's price range; version one ranked the
    OPTION's band width over its own decaying VWAP. Neither may be able to
    move this verdict again."""
    n = 21
    coil = {**{i: WIDE for i in range(15)}, **{i: NARROW for i in range(15, 20)}}

    # (a) The index squeezed. Whatever the option premium did -- coiled,
    # swung, or had its own bands squeezed or blown out -- the answer is the
    # index's answer.
    sq = _ix(_squeeze(n))
    assert _run(_scene(), idx=sq)[20]["trap"] == "CLEAR"
    assert _run(_scene(pre=coil), idx=sq)[20]["trap"] == "CLEAR"
    assert _run(_scene(sds=[1.0] * n), idx=sq)[20]["trap"] == "CLEAR"
    wide_bands = _scene(sds=[10.0] * 15 + [3.0] * 5 + [10.0],
                        trig_row=BUY_D2_SD10)
    assert _run(wide_bands, idx=sq)[20]["trap"] == "CLEAR"

    # (b) The index did NOT squeeze. A hard coil in the premium must not
    # manufacture a CLEAR out of it.
    assert _run(_scene(pre=coil))[20]["trap"] == "SUSPECT"
    assert _run(_scene(pre=coil), idx=_flat(n))[20]["trap"] == "SUSPECT"


def test_trap_suspect_says_what_it_measured_and_asserts_no_expansion():
    """Regression: the receipt used to claim 'bands were already wide ... no
    prior coil' at every non-CLEAR rank, including a session where the width
    never changed at all. It must state the measurement, not an event."""
    rec = _run(_scene())[20]                   # every index reading the same
    assert rec["trap"] == "SUSPECT"
    why = rec["trap_why"]
    assert "already wide" not in why and "expanding" not in why
    assert "rank 1.00" in why and "not in the bottom 30%" in why
    assert "flat" in why                       # what the band actually did
    assert "100.0 points" in why


def test_a_tight_band_that_is_already_expanding_is_suspect():
    """*'the whole vwap bands are expanding not narrowing or staying flat'* --
    the level alone is not enough, the direction of change is a second read.
    Here the index band still ranks in the bottom 30% but it has already
    started opening up, so the squeeze was releasing before the trigger."""
    n = 31
    widths = ([100.0] * 20 + [40.0, 38.0, 36.0, 34.0, 32.0]
              + [33.0, 34.0, 35.0, 36.0, 37.0] + [100.0])
    rec = _run(_scene(n=n, trig=30, other_tag=24), idx=_ix(widths))[30]
    assert rec["trap"] == "SUSPECT"
    assert "bottom 30%" in rec["trap_why"]     # it WAS tight
    assert "expanding" in rec["trap_why"]      # and that is why it failed
    assert rec["trap_dwell"] == 10


def test_dwell_counts_how_long_the_index_band_has_stayed_that_tight():
    """*'is its a good thing to notice ... for how long the price are in this
    range'*. A squeeze that keeps tightening for 15 bars reports 15; a
    five-bar one reports five; a session whose band never moved reports none.
    The count is a separate reading from the rank and never gates."""
    n = 61
    long_taper = [100.0] * 45 + [45.0 - k for k in range(15)] + [100.0]
    long_coil = _run(_scene(n=n, trig=60, other_tag=54),
                     idx=_ix(long_taper))[60]
    assert long_coil["trap"] == "CLEAR"
    assert long_coil["trap_dwell"] == 15
    assert "for 15 consecutive bar(s)" in long_coil["trap_why"]

    short_coil = _run(_scene(), idx=_ix(_squeeze(21)))[20]
    assert short_coil["trap"] == "CLEAR"
    assert short_coil["trap_dwell"] == 5

    flat = _run(_scene())[20]                   # never compressed at all
    assert flat["trap_dwell"] == 0
    assert "not holding a tight width" in flat["trap_why"]


def test_no_compression_verdict_before_the_operators_0925_anchor():
    """*'by 9:25 we have the values for vwap standard deviation and from there
    we judge'*. The anchor is read off the bar's own clock label, so it lands
    at 09:25 whatever the bar interval is, and it is checked even when a
    perfectly good index series is sitting right there."""
    early = _run(_scene(n=11, trig=9, other_tag=4), idx=_ix(_squeeze(11)))[9]
    assert early["trap"] == "UNKNOWN"          # 09:24
    assert "09:25" in early["trap_why"] and "09:24" in early["trap_why"]

    # Past the anchor, but the index feed only starts at 09:18 -- so there are
    # 7 readings before the move where 10 are needed. Still UNKNOWN, and now
    # for the honest reason that there is not enough to rank.
    late = _run(_scene(n=12, trig=10, other_tag=4),
                idx=_ix([100.0] * 9, t0=3))[10]
    assert late["trap"] == "UNKNOWN"           # 09:25
    assert "7 index band reading(s)" in late["trap_why"]
    assert "09:25" not in late["trap_why"]


def test_an_unlabelled_bar_is_unknown_rather_than_assumed_late_enough():
    legs = _scene()
    legs["CE"]["bars"][20] = dict(legs["CE"]["bars"][20], t=None)
    rec = _run(legs, idx=_ix(_squeeze(21)))[20]
    assert rec["trap"] == "UNKNOWN"
    assert rec["trap_dwell"] is None
    assert "clock" in rec["trap_why"]


def test_the_rank_is_trailing_not_session_so_far():
    """The first version ranked against the session so far, which -- because
    it normalised by a DECAYING premium VWAP -- measured how LATE it was. The
    same index squeeze must read the same whether it sits early or late."""
    early = _run(_scene(n=21, trig=20, other_tag=14), idx=_ix(_squeeze(21)))[20]
    late = _run(_scene(n=61, trig=60, other_tag=54), idx=_ix(_squeeze(61)))[60]
    assert early["trap"] == late["trap"] == "CLEAR"
    assert early["trap_dwell"] == late["trap_dwell"] == 5


# ------------------------------------------- 4b. the operator's own session

# Their Kite export of NIFTY AUG FUT for 2026-07-30, +/-3 sigma width in
# points, reproduced from the CSV in the spec. Every figure is theirs.
PHASES = [("09:15", 104.7), ("09:25", 104.7), ("10:20", 93.0),
          ("10:40", 105.3), ("11:50", 100.9), ("12:30", 87.4),
          ("12:40", 163.7), ("13:00", 173.2), ("15:29", 172.3)]


def _reference_widths():
    """The phase table interpolated to one reading a minute from 09:15."""
    pts = [(int(t[:2]) * 60 + int(t[3:]) - (9 * 60 + 15), w) for t, w in PHASES]
    out = []
    for m in range(pts[-1][0] + 1):
        k = max(j for j in range(len(pts)) if pts[j][0] <= m)
        if k == len(pts) - 1:
            out.append(pts[k][1])
            continue
        (m0, w0), (m1, w1) = pts[k], pts[k + 1]
        out.append(w0 + (w1 - w0) * (m - m0) / (m1 - m0))
    return out


def _at_clock(hhmm, other_back=6):
    """A CONFIRMED trigger at wall-clock `hhmm` of the reference session."""
    i = int(hhmm[:2]) * 60 + int(hhmm[3:]) - (9 * 60 + 15)
    widths = _reference_widths()
    legs = _scene(n=i + 1, trig=i, other_tag=i - other_back)
    return _run(legs, idx=_ix(widths[:i + 1]))[i]


def test_the_operators_reference_squeeze_at_1230_reads_as_a_squeeze():
    """ACCEPTANCE. *"squeeze 2 ... 12:30 87.4 -- day's tightest"*. A correct
    implementation has to see the 11:50 -> 12:30 contraction."""
    rec = _at_clock("12:30")
    assert rec["trap"] == "CLEAR"
    assert "narrowing" in rec["trap_why"]
    assert "87." in rec["trap_why"]            # the width they quoted
    assert rec["trap_dwell"] >= 10             # a long, real coil


def test_the_1240_blast_out_of_it_is_not_a_squeeze():
    """ACCEPTANCE, the other half. *"blast 12:40 163.7"* -- by then the band
    has nearly doubled in ten minutes, so a trigger there broke out of an
    EXPANSION, not a coil, and must not be reported as clean."""
    rec = _at_clock("12:40")
    assert rec["trap"] == "SUSPECT"
    assert "expanding" in rec["trap_why"]
    assert rec["trap_dwell"] == 0

    # ... and the plateau after it is no better.
    assert _at_clock("13:00")["trap"] == "SUSPECT"


def test_the_reference_session_is_not_one_long_verdict():
    """The failure mode of version one was a filter that said the same thing
    all day (band width grew monotonically, so lateness WAS the verdict). On
    the operator's own session the answer must actually change."""
    seen = {_at_clock(t)["trap"] for t in
            ("10:20", "11:50", "12:30", "12:40", "13:00", "15:00")}
    assert seen == {"CLEAR", "SUSPECT"}


# --------------------------------------------------------------- 4c. one bar

def test_when_both_legs_fire_on_one_bar_the_loser_is_named_not_dropped():
    """Both legs at their extremes on one minute is the operator's rotation in
    its purest form. One record still comes out -- but the hit that lost the
    tie-break is named, so a consumer can see that it qualified."""
    n = 21
    ce = _leg(_rows(n, {20: BUY_D2_SD5}), _decel(n))
    pe = _leg(_rows(n, {20: BUY_D3_SD5}), _decel(n, base=80000.0))
    out = _run({"CE": ce, "PE": pe})
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
    out = _run({"CE": ce, "PE": pe})
    assert len(_fired(out)) == 1
    assert (out[20]["leg"], out[20]["band"]) == ("CE", "d2")
    assert out[20]["also"] and out[20]["also"][0].startswith("PE low")


def test_a_lone_hit_names_no_other_leg():
    assert _run(_scene())[20]["also"] is None


# -------------------------------------------------------------- 5. causality

def test_truncation_reproduces_the_full_records_exactly():
    """Bar i is a function of bars <= i, so replaying half the session must
    reproduce the first half's records field for field -- not merely the same
    number of them. The index series is bounded by the bar's own clock label,
    so this holds whether or not the index is truncated alongside the legs."""
    legs = _scene(n=21, trig=20, other_tag=14)
    legs["CE"]["bars"][12] = dict(legs["CE"]["bars"][12],
                                  l=89.0, h=101.0, c=100.0)
    idx = _ix(_squeeze(21))
    full = _run(legs, idx=idx)
    assert full[12] is not None and full[20] is not None

    for k in (13, 15, 18, 21):
        cut = {s: {"bars": leg["bars"][:k], "vwap": leg["vwap"][:k],
                   "oi": leg["oi"][:k], "bar_days": leg["bar_days"][:k]}
               for s, leg in legs.items()}
        cut_idx = {"bars": idx["bars"][:k], "vwap": idx["vwap"][:k],
                   "bar_days": idx["bar_days"][:k]}
        assert _run(cut, idx=idx) == full[:k], f"replay diverged at k={k}"
        assert _run(cut, idx=cut_idx) == full[:k], f"both cut, k={k}"


def test_a_later_index_reading_cannot_change_an_earlier_record():
    """The index join is by clock label, so nothing stops a caller handing in
    the WHOLE session's index series while replaying its first half. Bars
    after the trigger's label must be invisible to it."""
    legs = _scene(n=21, trig=12, other_tag=6)
    widths = _squeeze(21)
    before = _run(legs, idx=_ix(widths))[12]
    blown = widths[:13] + [9999.0] * 8
    assert _run(legs, idx=_ix(blown))[12] == before


def test_a_later_bar_cannot_change_an_earlier_record():
    legs = _scene(n=21, trig=12, other_tag=6)
    before = _run(legs)
    legs["CE"]["bars"][20] = dict(legs["CE"]["bars"][20], l=1.0, c=100.0)
    assert _run(legs)[:13] == before[:13]


def test_sessions_do_not_bleed_into_each_other():
    # Two sessions on one axis: yesterday's squeeze cannot rank today's bar,
    # and yesterday's tag cannot confirm today's trigger.
    n = 21
    legs = _scene(n=n, trig=20, other_tag=14)
    days = [DAY] * 15 + [DAY2] * 6
    for leg in legs.values():
        leg["bar_days"] = list(days)
    out = _run(legs, idx=_ix_days(_squeeze(n), days))
    assert out[20]["confirm"] == "UNCONFIRMED"   # the tag is in the prior day
    assert out[20]["trap"] == "UNKNOWN"          # only 5 index readings today
    assert "5 index band reading(s)" in out[20]["trap_why"]


def test_an_unlabelled_index_series_is_refused_across_sessions():
    """A series with no session labels is a single-session series. Joining it
    onto a two-day axis would let one day's band rank the other day's bar --
    the exact leak `bar_days` exists to stop -- so it is refused, not guessed
    at."""
    n = 21
    legs = _scene(n=n, trig=20, other_tag=14)
    days = [DAY] * 15 + [DAY2] * 6
    for leg in legs.values():
        leg["bar_days"] = list(days)
    idx = _ix(_squeeze(n))
    idx["bar_days"] = [None] * n
    rec = _run(legs, idx=idx)[20]
    assert rec["trap"] == "UNKNOWN"
    assert "no session labels" in rec["trap_why"] and "2 sessions" in rec["trap_why"]


# ----------------------------------------------------------- 6. independence

def test_index_independence_the_same_shape_at_any_magnitude():
    """NIFTY premiums live near 100 and the index near 24,000; SENSEX is
    ~80,000 with premiums to match. Scaling BOTH series must not change a
    single signal -- if it does, an absolute market threshold crept in. It
    works because a rank is invariant under rescaling and the direction test
    reads only a sign, so no normaliser is needed at all."""
    widths = _squeeze(21)
    ref = _shape(_run(_scene(), idx=_ix(widths)))
    assert ref and ref[0][-1] == "CLEAR"
    for k in (0.4, 3.0, 8.0, 25.0):
        got = _shape(_run(_scene(scale=k), idx=_ix(widths, scale=k)))
        assert got == ref, f"scale {k} changed the signals"


def test_the_index_level_itself_is_never_read():
    """Only the DISTANCE between the bands is. Sliding the whole index up or
    down without changing its width must not move a verdict."""
    widths = _squeeze(21)
    base = _run(_scene(), idx=_ix(widths))[20]
    for level in (1000.0, 24000.0, 82000.0):
        assert _run(_scene(), idx=_ix(widths, level=level))[20]["trap"] == \
            base["trap"]


# ------------------------------------------------------------- 7. junk input

def test_junk_input_returns_empty_and_never_raises():
    assert detect(None) == []
    assert detect({}) == []
    assert detect({"CE": None, "PE": None}) == []
    assert detect({"CE": {"bars": [], "vwap": [], "oi": []}}) == []


def test_a_junk_index_series_is_unknown_and_never_raises():
    for junk in (42, "no", [], {}, [None, 7], {"bars": "no"},
                 [{"t": "09:30"}], {"bars": [{"t": "09:30"}], "vwap": [None]}):
        rec = _run(_scene(), idx=junk)[20]
        assert rec["trap"] == "UNKNOWN", junk
        assert rec["trap_dwell"] is None


def test_a_flat_index_shape_is_accepted_too():
    """`/api/data`'s `day.bars[].fut` carries the band keys on the bar itself
    and `vwap` as a NUMBER, so the two accepted shapes cannot be confused."""
    widths = _squeeze(21)
    leg_shape = _run(_scene(), idx=_ix(widths))
    flat = []
    for k, w in enumerate(widths):
        flat.append({"day": DAY, "t": _t(k), "vwap": LEVEL,
                     "u3": LEVEL + w / 2.0, "d3": LEVEL - w / 2.0})
    assert _run(_scene(), idx=flat) == leg_shape


def test_a_none_bar_on_the_firing_leg_simply_has_no_record():
    legs = _scene()
    legs["CE"]["bars"][20] = None
    legs["CE"]["vwap"][20] = None
    assert _fired(_run(legs)) == []


def test_a_missing_band_is_not_treated_as_zero():
    legs = _scene()
    legs["CE"]["vwap"][20] = dict(legs["CE"]["vwap"][20], d2=None, d3=None)
    assert _fired(_run(legs)) == []


def test_a_whole_contract_payload_is_accepted_too():
    legs = _scene()
    idx = _ix(_squeeze(21))
    payload = {"legs": legs, "axis": [[DAY, _t(i)] for i in range(21)],
               "index": "NIFTY",              # the NAME, not the series
               "index_series": idx}
    assert detect(payload) == detect(legs, [(DAY, _t(i)) for i in range(21)],
                                     index_series=idx)
    assert detect(payload)[20]["trap"] == "CLEAR"


# ------------------------------------- 8. the INDEX side (`detect_index`)
#
# The same trigger, run on ONE series -- the index's own bars, as `/api/data`
# publishes them. What is verified here is (a) the acceptance case the operator
# found on their own chart, verbatim off the live tape, (b) that a single
# series never claims a confirmation it cannot have, and (c) that the trigger
# really is the SAME primitive the option path uses, not a copy that can drift.

# The live 2026-07-31 NIFTY 1-minute FUT tape, read straight off
# `/api/data?idx=NIFTY` while the market was open: (t, low, high, close,
# d2, d3, u3). 09:35-09:38 each TAG d2 and close BELOW it -- a touch is not a
# signal. 09:39 tags d2 and the SAME bar closes back above it, and price then
# ran to 24419 (~+34 points). The -3 sigma line was never reached (lows
# 24370-24371 against d3 24358-24377), so this is a d2 trigger, not a d3 one.
LIVE_0731 = [
    ("09:35", 24379.0, 24385.0, 24379.0, 24390.28, 24376.78, 24457.77),
    ("09:36", 24375.0, 24385.0, 24380.0, 24386.11, 24371.21, 24460.65),
    ("09:37", 24370.2, 24385.0, 24372.7, 24382.91, 24366.92, 24462.86),
    ("09:38", 24370.0, 24377.1, 24371.3, 24379.11, 24361.85, 24465.42),
    ("09:39", 24371.1, 24387.3, 24385.0, 24376.80, 24358.90, 24466.27),
    ("09:40", 24380.0, 24387.7, 24385.0, 24375.48, 24357.28, 24466.48),
]


def _fut(low, high, close, d2, d3):
    """A FUT block with the whole sigma ladder, derived from d2 and d3 alone.

    One sigma IS `d2 - d3`, so the rest of the ladder follows -- and
    `test_the_live_fixture_really_is_the_engines_own_sigma_ladder` checks the
    derived u3 against the u3 the live feed actually sent, which is what makes
    this a reconstruction of the real band rather than an invented one.
    """
    sd = d2 - d3
    vwap = d2 + 2 * sd
    return {"o": close, "h": high, "l": low, "c": close, "v": 1000.0,
            "oi": 100000.0, "vwap": vwap,
            "u1": vwap + sd, "d1": vwap - sd,
            "u2": vwap + 2 * sd, "d2": d2, "u3": vwap + 3 * sd, "d3": d3}


# 20 inert bars, 09:15-09:34, so the trap read has a population to rank the
# live rows against. SYNTHETIC: they carry no claim about what the real
# session's band did before 09:35, which is why no test below asserts a trap
# VERDICT on this fixture -- only the trigger, which reads one bar.
PAD_N = 20


def _live_rows(scale=1.0, upto=None):
    """`/api/data` day rows: the clock on the ROW, the bands under `fut`."""
    rows = []
    for k in range(PAD_N):
        rows.append({"t": _t(k), "ce": None, "pe": None,
                     "fut": _fut(24395.0 * scale, 24405.0 * scale,
                                 24400.0 * scale, 24320.0 * scale,
                                 24300.0 * scale)})
    for t, low, high, close, d2, d3, _u3 in LIVE_0731:
        rows.append({"t": t, "ce": None, "pe": None,
                     "fut": _fut(low * scale, high * scale, close * scale,
                                 d2 * scale, d3 * scale)})
    return rows if upto is None else rows[:upto]


def _at_t(out, t):
    for r in out:
        if r is not None and r["t"] == t:
            return r
    return None


def test_the_live_fixture_really_is_the_engines_own_sigma_ladder():
    """d2 and d3 are one sigma apart, so u3 is implied -- and the implied u3
    matches the u3 the live feed really sent.

    Not to the cent: `engine.session_json` rounds every band to 2dp on its
    own, so the reconstructed sigma (`d2 - d3`) carries up to 0.01 of error
    and `u3 = d2 + 5*sigma` up to 0.055 of it. 0.1 points on a 24,000 index is
    the rounding, not a different ladder.
    """
    for _t_, _l, _h, _c, d2, d3, u3 in LIVE_0731:
        assert abs(_fut(0, 0, 0, d2, d3)["u3"] - u3) <= 0.1


def test_the_index_d2_reversal_the_operator_caught_on_their_own_chart():
    """2026-07-31 09:39 NIFTY: the acceptance case, off the live tape."""
    out = band_rotation.detect_index(_live_rows())
    rec = _at_t(out, "09:39")
    assert rec is not None, "09:39 must fire -- the tag AND the reversal"
    assert (rec["side"], rec["band"], rec["leg"]) == ("BUY", "d2", "index")
    assert "24371.10" in rec["trigger"] and "24376.80" in rec["trigger"]
    assert "24385.00" in rec["trigger"]


def test_the_bars_that_only_tagged_the_band_do_not_fire():
    """09:35-09:38 each pierced d2 and closed BELOW it. A touch is not a
    signal -- *"tag or wick is enough but has to reverse from the last
    band"*."""
    out = band_rotation.detect_index(_live_rows())
    for t in ("09:35", "09:36", "09:37", "09:38"):
        assert _at_t(out, t) is None, t


def test_an_index_signal_is_never_confirmed_and_says_why():
    fired = _fired(band_rotation.detect_index(_live_rows()))
    assert fired
    for rec in fired:
        assert rec["confirm"] == "UNKNOWN"
        assert "no opposite leg" in rec["confirm_why"]
        assert rec["also"] is None      # no other leg could lose a tie-break


def test_index_records_are_one_slot_per_bar_and_aligned():
    rows = _live_rows()
    out = band_rotation.detect_index(rows)
    assert len(out) == len(rows)
    for i, rec in enumerate(out):
        if rec is not None:
            assert rec["i"] == i and rec["t"] == rows[i]["t"]


def test_the_index_trigger_is_the_same_primitive_the_option_path_uses():
    """One geometry, both entry points, one answer -- so a change to the
    trigger cannot silently apply to options and not to the index."""
    for row, side, band in ((BUY_D2_SD5, "BUY", "d2"),
                            (BUY_D3_SD5, "BUY", "d3"),
                            (SELL_U3_SD5, "SELL", "u3"),
                            (TAG_NO_REV, None, None),
                            (TAG_U2_REV, None, None)):
        low, high, close = row
        bands = _band(VWAP, SD)
        flat = [dict(bands, t=_t(0), o=close, h=high, l=low, c=close)]
        got = band_rotation.detect_index(flat)[0]
        leg = _leg([row], _decel(1))
        opt = _fired(detect({"CE": leg}))
        if side is None:
            assert got is None and opt == [], row
            continue
        assert (got["side"], got["band"]) == (side, band), row
        assert (opt[0]["side"], opt[0]["band"]) == (side, band), row


def test_an_index_bar_the_feed_never_sent_keeps_its_slot():
    rows = _live_rows()
    rows[PAD_N + 4]["fut"] = None       # the 09:39 bar, blanked
    out = band_rotation.detect_index(rows)
    assert len(out) == len(rows)
    assert out[PAD_N + 4] is None
    assert _at_t(out, "09:39") is None


def test_index_truncation_reproduces_the_earlier_records_exactly():
    """Causality: replaying a truncated series must reproduce the earlier
    records field for field -- nothing later may reach back."""
    full = band_rotation.detect_index(_live_rows())
    for cut in range(PAD_N, len(full) + 1):
        assert band_rotation.detect_index(_live_rows(upto=cut)) == full[:cut]


def test_index_signals_are_magnitude_independent():
    """The same shape at a SENSEX-sized level fires on the same bars with the
    same bands -- no absolute price threshold crept into the index path."""
    base = band_rotation.detect_index(_live_rows())
    big = band_rotation.detect_index(_live_rows(scale=3.3))
    assert [(r["i"], r["side"], r["band"]) for r in _fired(base)] == \
        [(r["i"], r["side"], r["band"]) for r in _fired(big)]


def test_detect_index_junk_input_returns_empty_and_never_raises():
    for junk in (None, {}, [], "no", 42, [None, None], [7, "x"],
                 [{"t": "09:30"}], [{"t": None, "fut": {}}],
                 [{"fut": {"l": 1, "h": 2, "c": 3}}]):
        out = band_rotation.detect_index(junk)
        assert isinstance(out, list)
        assert all(r is None for r in out), junk


def test_the_index_path_never_fabricates_a_compression_read():
    """One bar has nothing to rank against, so the trap is UNKNOWN -- never
    CLEAR, and never rounded to it."""
    bands = _band(VWAP, SD)
    low, high, close = BUY_D2_SD5
    one = [dict(bands, t="09:39", o=close, h=high, l=low, c=close)]
    rec = band_rotation.detect_index(one)[0]
    assert rec["trap"] == "UNKNOWN"
    assert rec["trap_dwell"] is None


def test_the_named_constants_are_documented_windows_not_price_levels():
    for name in ("ROTATION_WINDOW", "OI_WINDOW", "TRAIL_WINDOW", "TRAIL_MIN",
                 "TREND_WINDOW"):
        assert isinstance(getattr(band_rotation, name), int)
    assert 0.0 < band_rotation.COMPRESSION_RANK < 1.0
    # The width is a DIFFERENCE of two band names, never a points threshold.
    assert band_rotation.WIDTH_BANDS == ("u3", "d3")
    # The one clock time in the module is the operator's own 09:25 anchor --
    # a session landmark, not a market level.
    assert band_rotation.ANCHOR_HHMM == "09:25"
    assert band_rotation.ANCHOR_MINUTE == 9 * 60 + 25
