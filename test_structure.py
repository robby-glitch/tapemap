"""structure.py -- the four test families from spec section 7 ("Testing").

Every sequence below is hand-built from the DEFINITIONS in section 7's table,
never from another implementation's output (the section 7 IP line). Each row is
`(o, h, l, c)` as an OFFSET from a base price so the same table can be
replayed at NIFTY, BANKNIFTY and SENSEX levels by scaling.

Families:
  1. Geometry     — each structure fires exactly where its definition says
                    and NOWHERE else (asserted as per-kind counts, not just
                    membership).
  2. Causality    — compute(bars[0..N]) filtered to born <= k is byte-equal to
                    compute(bars[0..k]); a swing does not exist before its
                    confirming bars.
  3. Index independence — the same table x1, x2.35 (BANKNIFTY) and x3.2
                    (SENSEX) yields identical structures.
  4. Confirmation separable — flow inputs absent => every structure UNKNOWN,
                    never UNCONFIRMED; flow present => real CONFIRMED /
                    UNCONFIRMED verdicts whose receipts name the numbers.
"""

from collections import Counter

import structure

BASE = 24000.0                 # NIFTY-ish; x2.35 -> BANKNIFTY, x3.2 -> SENSEX


def _seq(rows, scale=1.0, vol=None, oi=None, drop_fut=()):
    """Payload bar dicts (session_json shape) from (o,h,l,c) offset rows.

    vol / oi are optional per-bar lists; when None the flow keys are ABSENT
    from the FUT leg entirely (the "flow inputs absent" case of family 4).
    Indices in `drop_fut` get a null FUT leg (session_json never does this for
    FUT, but compute() must not crash if it ever did).
    """
    bars = []
    for i, (o, h, l, c) in enumerate(rows):
        if i in drop_fut:
            bars.append({"t": f"09:{15 + i:02d}", "fut": None,
                         "ce": None, "pe": None})
            continue
        f = {"o": (BASE + o) * scale, "h": (BASE + h) * scale,
             "l": (BASE + l) * scale, "c": (BASE + c) * scale,
             "oi": 1000, "v": 100}
        if vol is not None:
            f["vol_r"] = vol[i]
        if oi is not None:
            f["oi_slope"] = oi[i]
        bars.append({"t": f"09:{15 + i:02d}", "fut": f, "ce": None, "pe": None})
    return bars


def _counts(structs):
    return Counter(s["kind"] for s in structs)


def _one(structs, kind):
    hits = [s for s in structs if s["kind"] == kind]
    assert len(hits) == 1, f"expected exactly one {kind}, got {hits}"
    return hits[0]


# --------------------------------------------------------------- sequences

# The "story": a swing high, a BOS through it, then a swing low and a CHoCH
# back through that. Highs/lows chosen so exactly one pivot of each side forms
# where intended (verified by the count assertions below). Every non-zero body
# is a DIFFERENT size on purpose: the impulse test is a percentile rank over
# bodies, and equal bodies could reorder by one float bit once the table is
# replayed at 2.35x / 3.2x, which would make the scaling test flaky rather
# than wrong.
#            o     h     l     c
STORY = [(  0.0,  1.0, -1.0,  0.0),   # 0
         (  0.0,  2.0, -1.0,  0.0),   # 1
         (  0.0,  3.0, -1.0,  0.0),   # 2
         (  0.0, 10.0, -4.0,  0.0),   # 3  pivot HIGH  (+10)
         (  0.0,  3.0, -5.0,  0.0),   # 4
         (  0.0,  2.0, -6.0,  0.0),   # 5
         (  0.0,  1.0, -7.0,  0.0),   # 6  pivot LOW (-7); SWING_H born here
         (  1.0, 12.0,  0.0, 11.5),   # 7  close 11.5 > 10 -> BOS up
         ( 11.0, 13.0, 10.0, 12.0),   # 8
         ( 12.0, 13.0, 11.0, 12.0),   # 9  SWING_L(-7) born here
         ( 12.0, 12.0, 10.0, 10.8),   # 10
         ( 11.0, 11.0,  5.0,  6.0),   # 11 pivot LOW (+5)
         (  6.0,  8.0,  6.0,  7.4),   # 12
         (  7.0,  9.0,  7.0,  8.6),   # 13
         (  8.0, 10.0,  8.0,  9.8),   # 14 SWING_L(+5) born here
         (  9.0,  9.0,  2.0,  3.0)]   # 15 close 3 < 5 -> CHoCH down

# STORY only ever exercises CHoCH on a DOWN break (structure.py:296-301) --
# the mirror branch, an UP break while trend == -1 (structure.py:292), is
# never visited by any table above, so mutating that line to always emit
# "BOS" passes every existing test. Full negation (o,h,l,c) -> (-o,-l,-h,-c)
# swaps every high/low/close role consistently (unlike the h/l-only flip
# `test_swing_low_mirrors` uses on TENT, which gets away with leaving o/c
# alone only because TENT's o and c are both always 0): the first break in
# STORY (up, trend 0 -> 1) becomes a DOWN break (trend 0 -> -1), and the
# second break (down, against trend 1 -> CHoCH) becomes an UP break against
# trend -1 -> CHoCH up, the untested branch. STORY[:8] is appended after it
# unchanged, so the trend-flip-then-break pattern that opened STORY (a fresh
# SWING_H born 6 bars in, broken on the 7th) recurs once more -- but this
# time trend is already +1 from the CHoCH, so the same shape must classify
# as BOS, not CHoCH, proving the flip actually took effect.
CHOCH_UP_STORY = [(-o, -l, -h, -c) for (o, h, l, c) in STORY] + STORY[:8]

# Two swing highs 0.2 apart -> EQH (tolerance is a FRACTION of the session's
# own realised range: 0.05 * 17.0 = 0.85 at the confirming bar).
EQ_ROWS = [(0.0,  1.0, -1.0, 0.0),    # 0
           (0.0,  2.0, -2.0, 0.0),    # 1
           (0.0,  3.0, -3.0, 0.0),    # 2
           (0.0, 10.0, -4.0, 0.0),    # 3  pivot HIGH +10.0
           (0.0,  3.0, -5.0, 0.0),    # 4
           (0.0,  2.0, -6.0, 0.0),    # 5
           (0.0,  1.0, -7.0, 0.0),    # 6
           (0.0,  2.0, -6.0, 0.0),    # 7
           (0.0,  3.0, -5.0, 0.0),    # 8
           (0.0,  9.8, -4.0, 0.0),    # 9  pivot HIGH +9.8  (0.2 apart)
           (0.0,  3.0, -5.0, 0.0),    # 10
           (0.0,  2.0, -6.0, 0.0),    # 11
           (0.0,  1.0, -7.0, 0.0)]    # 12 both swings + the EQH born here

# same shape, second high 5.0 away -> outside tolerance, no pool
NOEQ_ROWS = [r if i != 9 else (0.0, 5.0, -4.0, 0.0)
             for i, r in enumerate(EQ_ROWS)]

# EQ_ROWS/NOEQ_ROWS clear EQ_FRAC * rng by such a wide margin (0.2 apart on a
# 0.85 tolerance, or 5.0 apart -- nowhere close) that absolutizing EQ_FRAC *
# rng (structure.py:271,281) to a constant like 0.85 still passes every test
# above, at every scale: the margin swallows the difference between a
# relative and an absolute threshold. These two tables instead put the
# separation at ~0.94x / ~1.06x the tolerance -- close enough that only the
# relative rule gets both sides right at every scale; a hard-coded constant
# starts disagreeing with the relative rule the moment the price offsets are
# rescaled (BANKNIFTY/SENSEX), because the constant does not rescale with
# them. rng is pinned at 18.0 (hi_run 12.0, lo_run -6.0) so tol = 0.05*18 =
# 0.9 exactly; separation 0.846 = 0.94*0.9 (fires), 0.954 = 1.06*0.9 (absent).
EQ_NEAR_FIRE_ROWS = [
    (0.0,  1.0, -1.0, 0.0),
    (0.0,  2.0, -2.0, 0.0),
    (0.0,  3.0, -3.0, 0.0),
    (0.0, 12.0, -4.0, 0.0),      # pivot HIGH +12.0 -> hi_run
    (0.0,  3.0, -5.0, 0.0),
    (0.0,  2.0, -6.0, 0.0),
    (0.0,  1.0, -6.0, 0.0),      # -6.0 -> lo_run
    (0.0,  2.0, -6.0, 0.0),
    (0.0,  3.0, -5.0, 0.0),
    (0.0, 11.154, -4.0, 0.0),    # pivot HIGH +11.154: 0.846 below the first
    (0.0,  3.0, -5.0, 0.0),
    (0.0,  2.0, -6.0, 0.0),
    (0.0,  1.0, -6.0, 0.0),
]

# mirror: separation just OVER the tolerance (1.06x) -- must stay absent at
# every scale, not merely at 1x.
EQ_NEAR_NOFIRE_ROWS = [r if i != 9 else (0.0, 11.046, -4.0, 0.0)
                       for i, r in enumerate(EQ_NEAR_FIRE_ROWS)]

# Same discrimination for the FVG floor (structure.py:305), scaled DOWN
# instead of up: FVG_MIN_FRAC is only 1% of rng to begin with, so shrinking
# the table (0.3x) separates a relative floor from an absolutized one more
# sharply than growing it would. rng is pinned at 20.0 (hi_run 19.0, lo_run
# -1.0) so floor = 0.01*20 = 0.20 exactly; the gap is 0.21 -- just over the
# relative floor at every scale, but under a floor absolutized to 0.20 (the
# value this floor happens to take on THIS table at 1x) the instant the
# table is shrunk to 0.3x, since 0.3*0.21 = 0.063 < 0.20.
FVG_NEAR_FLOOR_ROWS = [
    (0.0, 1.0, -1.0, 0.0),
    (0.0, 1.0, -1.0, 0.0),
    (0.0, 1.0, -1.0, 0.0),       # h = +1.0
    (0.0, 1.0, -1.0, 0.0),
    (1.21, 19.0, 1.21, 1.21),    # l = +1.21 -> gap 0.21 over rng 20.0
]

# a gap that is real and positive (clears the strict `<` at structure.py:307
# on its own) but sits BELOW the relative floor -- unlike the zero-gap
# "touch" case in test_fvg_is_a_three_bar_gap_and_a_touch_is_not_one, which
# is rejected by the strict `<` before the floor check is ever reached and so
# cannot tell the two guards apart, this one reaches the floor check and is
# rejected there alone.
FVG_SUBFLOOR_ROWS = [
    (0.0, 1.0, -1.0, 0.0),
    (0.0, 1.0, -1.0, 0.0),
    (0.0, 1.0, -1.0, 0.0),
    (0.0, 1.0, -1.0, 0.0),
    (1.15, 19.0, 1.15, 1.15),    # l = +1.15 -> gap 0.15, under the 0.20 floor
]

# five quiet bars then one impulsive up bar; bar 4 is the last DOWN candle
OB_UP = [(0.0, 1.0, -1.0, 0.2),       # 0  up
         (0.2, 1.0, -1.0, 0.4),       # 1  up
         (0.4, 1.0, -1.0, 0.2),       # 2  down
         (0.2, 1.0, -1.0, 0.4),       # 3  up
         (0.4, 1.0, -1.0, 0.2),       # 4  DOWN  <- the order block
         (0.2, 6.0,  0.0, 5.5)]       # 5  impulse up, closes above bar 4's high

OB_DOWN = [(0.2,  1.0, -1.0,  0.0),   # 0  down
           (0.0,  1.0, -1.0, -0.2),   # 1  down
           (-0.2, 1.0, -1.0,  0.0),   # 2  up
           (0.0,  1.0, -1.0, -0.2),   # 3  down
           (-0.2, 1.0, -1.0,  0.0),   # 4  UP  <- the order block
           (0.0,  0.5, -6.0, -5.5)]   # 5  impulse down, closes below its low

# same impulse, but every prior candle is up: no opposing candle to mark
OB_NONE = [(0.0, 1.0, -1.0, 0.2),
           (0.2, 1.0, -1.0, 0.4),
           (0.4, 1.0, -1.0, 0.6),
           (0.6, 1.0, -1.0, 0.8),
           (0.8, 1.2, -1.0, 1.0),
           (1.0, 6.0,  0.0, 6.3)]

# a 7-bar tent: one pivot high, monotonically falling lows so no pivot low
TENT = [(0.0,  1.0, -1.0, 0.0),
        (0.0,  2.0, -2.0, 0.0),
        (0.0,  3.0, -3.0, 0.0),
        (0.0,  5.0, -4.0, 0.0),       # 3  pivot HIGH
        (0.0,  3.0, -5.0, 0.0),
        (0.0,  2.0, -6.0, 0.0),
        (0.0,  1.0, -7.0, 0.0)]       # 6  confirms it


# =============================================== family 1: geometry

def test_swing_high_is_a_pivot_over_n_bars_each_side():
    st = structure.compute(_seq(TENT))
    assert _counts(st) == {"SWING_H": 1}, st
    s = _one(st, "SWING_H")
    assert s["hi"] == s["lo"] == round(BASE + 5.0, 2)
    assert (s["i0"], s["i1"], s["born"], s["dir"]) == (0, 6, 6, 1)


def test_swing_needs_strictly_higher_than_both_wings():
    # flatten the right wing to equal the pivot: a plateau is not a fractal
    rows = [r if i != 4 else (0.0, 5.0, -5.0, 0.0) for i, r in enumerate(TENT)]
    assert structure.compute(_seq(rows)) == []


def test_swing_low_mirrors():
    rows = [(o, -l, -h, c) for (o, h, l, c) in TENT]   # flip the tent
    st = structure.compute(_seq(rows))
    assert _counts(st) == {"SWING_L": 1}, st
    s = _one(st, "SWING_L")
    assert s["hi"] == s["lo"] == round(BASE - 5.0, 2)
    assert s["dir"] == -1


def test_fvg_is_a_three_bar_gap_and_a_touch_is_not_one():
    #  bar 0..3 cap at +1; bar 4 opens a gap above bar 2's high
    rows = [(0.0, 1.0, -1.0, 0.0),
            (0.0, 1.0, -1.0, 0.0),
            (0.0, 1.0, -1.0, 0.0),     # h = +1.0
            (0.0, 1.0, -1.0, 0.0),
            (3.5, 6.0,  2.5, 3.5),     # l = +2.5 > h[2] = +1.0  -> bullish FVG
            (5.0, 7.0,  1.0, 5.0)]     # l = +1.0 == h[3]        -> NOT a gap
    st = structure.compute(_seq(rows))
    assert _counts(st) == {"FVG": 1}, st
    g = _one(st, "FVG")
    assert (g["i0"], g["i1"], g["born"], g["dir"]) == (2, 4, 4, 1)
    assert (g["lo"], g["hi"]) == (round(BASE + 1.0, 2), round(BASE + 2.5, 2))


def test_fvg_sub_floor_gap_is_not_a_gap():
    # a real, positive gap (0.15) that clears the strict `<` on its own but
    # sits under the relative floor (0.20) -- rejected by the floor alone,
    # which the touch case above (rejected by the strict `<` first) cannot
    # demonstrate since the two guards mask each other there.
    assert structure.compute(_seq(FVG_SUBFLOOR_ROWS)) == []


def test_bearish_fvg_mirrors():
    rows = [(0.0, 1.0, -1.0, 0.0),
            (0.0, 1.0, -1.0, 0.0),
            (0.0, 1.0, -1.0, 0.0),     # l = -1.0
            (0.0, 1.0, -1.0, 0.0),
            (-3.5, -2.5, -6.0, -3.5),  # h = -2.5 < l[2] = -1.0 -> bearish FVG
            (-5.0, -1.0, -7.0, -5.0)]  # h = -1.0 == l[3]       -> NOT a gap
    st = structure.compute(_seq(rows))
    assert _counts(st) == {"FVG": 1}, st
    g = _one(st, "FVG")
    assert (g["i0"], g["i1"], g["born"], g["dir"]) == (2, 4, 4, -1)
    assert (g["lo"], g["hi"]) == (round(BASE - 2.5, 2), round(BASE - 1.0, 2))


def test_bos_then_choch_on_the_story_and_nothing_else():
    st = structure.compute(_seq(STORY))
    # two order blocks: the doji-heavy tent makes any real body rank top-20%,
    # which is the percentile rule doing exactly what it is told
    assert _counts(st) == {"SWING_H": 1, "SWING_L": 2, "BOS": 1,
                           "CHOCH": 1, "FVG": 2, "OB": 2}, _counts(st)
    bos = _one(st, "BOS")
    assert (bos["i0"], bos["born"], bos["dir"]) == (3, 7, 1)
    assert bos["hi"] == bos["lo"] == round(BASE + 10.0, 2)   # the level broken
    ch = _one(st, "CHOCH")
    assert (ch["i0"], ch["born"], ch["dir"]) == (11, 15, -1)
    assert ch["hi"] == ch["lo"] == round(BASE + 5.0, 2)


def test_choch_fires_on_an_up_break_once_a_down_trend_is_established():
    # STORY only ever breaks trend down-then-CHoCH; this table breaks trend
    # up-then-CHoCH instead (structure.py:292, the branch STORY never visits)
    # and then shows the flip stuck: a second up-break afterward is BOS again.
    st = structure.compute(_seq(CHOCH_UP_STORY))
    bos = sorted([s for s in st if s["kind"] == "BOS"], key=lambda s: s["born"])
    choch = [s for s in st if s["kind"] == "CHOCH"]
    assert len(bos) == 2 and len(choch) == 1, (bos, choch)
    # first break: down, no trend yet to contradict -> BOS; trend 0 -> -1
    assert (bos[0]["i0"], bos[0]["born"], bos[0]["dir"]) == (3, 7, -1), bos[0]
    # second break: up, against the now-established down-trend -> CHOCH
    ch = choch[0]
    assert (ch["i0"], ch["born"], ch["dir"]) == (11, 15, 1), ch
    # trend is now +1: the next up-break is BOS again, not CHOCH
    assert (bos[1]["i0"], bos[1]["born"], bos[1]["dir"]) == (19, 23, 1), bos[1]


def test_eqh_pairs_two_swing_highs_inside_a_relative_tolerance():
    st = structure.compute(_seq(EQ_ROWS))
    assert _counts(st) == {"SWING_H": 2, "SWING_L": 1, "EQH": 1}, _counts(st)
    e = _one(st, "EQH")
    assert (e["i0"], e["i1"], e["born"], e["dir"]) == (3, 9, 12, 1)
    assert (e["lo"], e["hi"]) == (round(BASE + 9.8, 2), round(BASE + 10.0, 2))


def test_eqh_does_not_fire_outside_the_tolerance():
    st = structure.compute(_seq(NOEQ_ROWS))
    assert _counts(st) == {"SWING_H": 2, "SWING_L": 1}, _counts(st)


def test_eql_mirrors():
    rows = [(o, -l, -h, c) for (o, h, l, c) in EQ_ROWS]
    st = structure.compute(_seq(rows))
    assert _counts(st) == {"SWING_L": 2, "SWING_H": 1, "EQL": 1}, _counts(st)
    e = _one(st, "EQL")
    assert (e["i0"], e["i1"], e["born"], e["dir"]) == (3, 9, 12, -1)


def test_order_block_is_the_last_opposing_candle_before_the_impulse():
    st = structure.compute(_seq(OB_UP))
    assert _counts(st) == {"OB": 1}, st
    b = _one(st, "OB")
    assert (b["i0"], b["i1"], b["born"], b["dir"]) == (4, 5, 5, 1)
    assert (b["lo"], b["hi"]) == (round(BASE - 1.0, 2), round(BASE + 1.0, 2))


def test_bearish_order_block_mirrors():
    st = structure.compute(_seq(OB_DOWN))
    assert _counts(st) == {"OB": 1}, st
    b = _one(st, "OB")
    assert (b["i0"], b["i1"], b["born"], b["dir"]) == (4, 5, 5, -1)


def test_no_order_block_without_an_impulse():
    # same table, last bar's body no larger than the rest -> not impulsive
    rows = OB_UP[:-1] + [(0.2, 1.0, -1.0, 0.4)]
    assert structure.compute(_seq(rows)) == []


def test_no_order_block_without_an_opposing_candle():
    assert structure.compute(_seq(OB_NONE)) == []


def test_empty_and_null_fut_legs_are_survivable():
    assert structure.compute([]) == []
    assert structure.compute(None) == []
    st = structure.compute(_seq(STORY, drop_fut={4}))
    assert isinstance(st, list)
    bars = _seq(STORY, drop_fut={4})
    for s in st:                        # every index must land on a real leg
        for k in ("i0", "i1", "born"):
            assert bars[s[k]]["fut"] is not None, (s, k)


# =============================================== family 2: causality

def test_truncation_equals_recomputation_without_flow():
    bars = _seq(STORY)
    full = structure.compute(bars)
    for k in range(len(bars)):
        assert [s for s in full if s["born"] <= k] == structure.compute(
            bars[:k + 1]), f"truncation mismatch at bar {k}"


def test_truncation_equals_recomputation_with_flow():
    vol = [0.5] * 16
    vol[8] = 3.0
    oi = [10] * 16
    oi[11] = -900
    bars = _seq(STORY, vol=vol, oi=oi)
    full = structure.compute(bars)
    for k in range(len(bars)):
        assert [s for s in full if s["born"] <= k] == structure.compute(
            bars[:k + 1]), f"truncation mismatch at bar {k}"


def test_a_swing_does_not_exist_before_its_confirming_bars():
    bars = _seq(TENT)
    for k in range(6):                              # bars 0..5: not yet born
        assert structure.compute(bars[:k + 1]) == [], k
    assert len(structure.compute(bars[:7])) == 1     # bar 6 confirms it


def test_every_structure_is_born_at_or_after_its_span():
    for rows in (STORY, EQ_ROWS, OB_UP, OB_DOWN, TENT):
        for s in structure.compute(_seq(rows)):
            assert s["i0"] <= s["i1"] <= s["born"], s
            assert s["lo"] <= s["hi"], s
            assert s["kind"] in ("FVG", "OB", "BOS", "CHOCH", "EQH", "EQL",
                                 "SWING_H", "SWING_L"), s
            assert s["dir"] in (1, -1), s


def test_fvg_hi_is_always_strictly_above_lo():
    # a floor that let a zero- or negative-width box through would be a gap
    # the UI cannot draw; check every FVG the suite's sequences produce, not
    # just the ones the dedicated FVG tests happen to construct.
    fvgs = []
    for rows in (STORY, EQ_ROWS, NOEQ_ROWS, OB_UP, OB_DOWN, TENT,
                 CHOCH_UP_STORY, FVG_NEAR_FLOOR_ROWS):
        fvgs += [s for s in structure.compute(_seq(rows)) if s["kind"] == "FVG"]
    assert fvgs, "no FVG anywhere -- this test would be proving nothing"
    for g in fvgs:
        assert g["hi"] > g["lo"], g


# =============================================== family 3: index independence

def _shape(structs):
    return [(s["kind"], s["i0"], s["i1"], s["born"], s["dir"],
             s["confirm"]) for s in structs]


def test_same_structures_at_banknifty_and_sensex_scale():
    vol = [0.5] * 16
    vol[8] = 3.0
    oi = [10] * 16
    for rows in (STORY, EQ_ROWS, NOEQ_ROWS, OB_UP, OB_DOWN, TENT):
        n = len(rows)
        base = structure.compute(_seq(rows, vol=vol[:n], oi=oi[:n]))
        assert base, rows            # a scaling test on nothing proves nothing
        for scale in (2.35, 3.2):    # BANKNIFTY, SENSEX
            got = structure.compute(
                _seq(rows, scale=scale, vol=vol[:n], oi=oi[:n]))
            assert _shape(got) == _shape(base), (scale, rows)
            for a, b in zip(base, got):
                assert abs(a["hi"] * scale - b["hi"]) <= 0.02, (scale, a, b)
                assert abs(a["lo"] * scale - b["lo"]) <= 0.02, (scale, a, b)


def test_eqh_near_boundary_tolerance_stays_relative_across_scale():
    # every decision in test_same_structures_at_banknifty_and_sensex_scale
    # clears its margin so widely that absolutizing EQ_FRAC * rng to a
    # constant (e.g. 0.85, structure.py:271,281) still passes it at every
    # scale. This table's separation sits at ~0.94x the relative tolerance,
    # which only a genuinely relative rule keeps firing once the table is
    # rescaled to BANKNIFTY/SENSEX levels.
    for scale in (1.0, 2.35, 3.2):
        st = structure.compute(_seq(EQ_NEAR_FIRE_ROWS, scale=scale))
        _one(st, "EQH")  # raises if it is not there, at every scale


def test_eqh_just_over_the_near_boundary_stays_absent_across_scale():
    # mirror of the above: ~1.06x the tolerance, must stay absent everywhere
    for scale in (1.0, 2.35, 3.2):
        st = structure.compute(_seq(EQ_NEAR_NOFIRE_ROWS, scale=scale))
        assert not [s for s in st if s["kind"] == "EQH"], (scale, st)


def test_fvg_near_floor_gap_stays_relative_across_scale():
    # same discrimination for FVG_MIN_FRAC (structure.py:305); scaling DOWN
    # to 0.3x is what exposes an absolutized floor here, since the floor is
    # only 1% of rng to begin with and the gap is chosen just over it.
    for scale in (1.0, 0.3, 2.35, 3.2):
        st = structure.compute(_seq(FVG_NEAR_FLOOR_ROWS, scale=scale))
        _one(st, "FVG")


# =============================================== family 4: confirmation

def test_absent_flow_is_unknown_never_unconfirmed():
    for rows in (STORY, EQ_ROWS, OB_UP, OB_DOWN, TENT):
        st = structure.compute(_seq(rows))
        assert st, rows
        for s in st:
            assert s["confirm"] == "UNKNOWN", s
            assert s["confirm_why"], s
            assert any(ch.isdigit() for ch in s["confirm_why"]), s
        assert not [s for s in st if s["confirm"] == "UNCONFIRMED"]


def test_flow_present_confirms_an_eqh_formation():
    # NB: this checks flow on the second pivot's FORMATION bar (bar 9 here,
    # where the pivot itself completes), not a later sweep through the
    # pool -- structure.py cannot see bars after `born` (invariant 2), so a
    # sweep read is a different, later-born question this receipt is
    # careful not to claim an answer to. See the module docstring's
    # deferred-work note.
    vol = [0.5] * 13
    vol[9] = 3.0                       # the pivot's own bar came on expanded volume
    oi = [10] * 13
    oi[9] = -1500                      # ... with OI unwinding
    e = _one(structure.compute(_seq(EQ_ROWS, vol=vol, oi=oi)), "EQH")
    assert e["confirm"] == "CONFIRMED", e
    assert "3.00" in e["confirm_why"] and "-1500" in e["confirm_why"], e
    assert "formation" in e["confirm_why"], e


def test_eqh_unconfirmed_when_volume_is_ordinary():
    vol = [3.0] * 13
    vol[9] = 0.5                       # the tag was the quietest bar of the day
    oi = [10] * 13
    oi[9] = -1500
    e = _one(structure.compute(_seq(EQ_ROWS, vol=vol, oi=oi)), "EQH")
    assert e["confirm"] == "UNCONFIRMED", e
    assert "0.50" in e["confirm_why"], e


def test_eqh_unconfirmed_when_oi_is_building_not_unwinding():
    vol = [0.5] * 13
    vol[9] = 3.0
    oi = [10] * 13
    oi[9] = +1500                      # OI built into the tag: not a sweep
    e = _one(structure.compute(_seq(EQ_ROWS, vol=vol, oi=oi)), "EQH")
    assert e["confirm"] == "UNCONFIRMED", e
    assert "+1500" in e["confirm_why"], e


def test_a_flat_vol_r_series_is_unknown_not_a_verdict():
    # every bar identical: there is no distribution to rank against, so the
    # honest answer is "could not check", not "checked and found nothing"
    e = _one(structure.compute(_seq(EQ_ROWS, vol=[0.5] * 13, oi=[-10] * 13)),
             "EQH")
    assert e["confirm"] == "UNKNOWN", e
    assert "identical" in e["confirm_why"], e


def test_one_missing_flow_field_is_unknown():
    vol = [0.5] * 13
    vol[9] = 3.0
    e = _one(structure.compute(_seq(EQ_ROWS, vol=vol)), "EQH")   # no oi_slope
    assert e["confirm"] == "UNKNOWN", e
    assert "oi_slope" in e["confirm_why"], e


def test_fvg_confirmation_reads_the_creation_flow():
    vol = [0.5] * 16
    vol[8] = 3.0                      # the displacement that opened the gap
    oi = [10] * 16                    # ... on OI building through it
    st = structure.compute(_seq(STORY, vol=vol, oi=oi))
    gaps = {s["born"]: s for s in st if s["kind"] == "FVG"}
    assert gaps[8]["confirm"] == "CONFIRMED", gaps[8]
    assert "3.00" in gaps[8]["confirm_why"], gaps[8]
    # the second gap's own bar was ordinary -> checked, and flow said no
    assert gaps[12]["confirm"] == "UNCONFIRMED", gaps[12]


def test_chain_sourced_kinds_say_what_is_missing():
    vol = [0.5] * 16
    vol[8] = 3.0
    oi = [10] * 16
    st = structure.compute(_seq(STORY, vol=vol, oi=oi))
    for s in st:
        if s["kind"] in ("OB", "BOS", "CHOCH"):
            assert s["confirm"] == "UNKNOWN", s
            assert "chain" in s["confirm_why"], s
        if s["kind"] in ("SWING_H", "SWING_L"):
            assert s["confirm"] == "UNKNOWN", s


def test_flow_present_produces_both_verdicts():
    vol = [0.5] * 16
    vol[8] = 3.0
    oi = [10] * 16
    st = structure.compute(_seq(STORY, vol=vol, oi=oi))
    got = {s["confirm"] for s in st}
    assert "CONFIRMED" in got and "UNCONFIRMED" in got, got


if __name__ == "__main__":
    import sys
    mod = sys.modules[__name__]
    fns = [v for k, v in sorted(vars(mod).items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("PASS", fn.__name__)
    print(f"ALL PASS ({len(fns)} tests)")
