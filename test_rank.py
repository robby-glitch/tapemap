"""test_rank.py -- RANK (rank.py, decode-loop Phase 1): the label rules, the same-clock and day-kind buckets, the
two-source delta rule, the single-source cap (D5), the rank-gated positioning words, and no look-ahead."""
import datetime

import rank

DAY = "2026-10-20"
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
T0 = int(datetime.datetime.fromisoformat(DAY).replace(tzinfo=IST).timestamp() * 1000)


def tab(xs, nd=12):
    t = rank.quant(xs)
    t["nd"] = nd
    return t


def test_tags_ties_record_and_provisional():
    assert rank.tag_of(5) == "BAHUT KAM" and rank.tag_of(50) == "noise" and rank.tag_of(75) == "notable"
    assert rank.tag_of(95) == "BADA" and rank.tag_of(95, record=True) == "RECORD" and rank.tag_of(None) == "?"
    # a count shared by half the days sits mid-run: "0 crosses" is not BAHUT KAM when half the days had 0
    assert rank.pct_vals([0, 0, 0, 0, 1, 2, 3, 4], 0) == 25.0
    L = rank.label(7, 96.0, 17)
    assert L["tag"] == "BADA" and L["prov"] is True                      # N < 30 days: provisional
    assert rank.label(7, 96.0, 31)["prov"] is False


def test_thin_is_capped_and_a_single_source_is_tagged_not_capped():
    assert rank.label(500, 99.0, 12, thin=True)["tag"] == "notable"
    one = rank.label(500, 99.0, 12, single="UX")
    assert one["tag"] == "BADA" and one["single"] == "UX" and one["capped"] is None   # 2026-10-19: absent != contrary


def test_two_sources_same_sign_both_p70_is_a_signal_else_disagree():
    big = lambda raw, p: dict(rank.label(raw, p, 12), raw=raw)             # noqa: E731
    yes = rank.two_source(big(400, 95), big(600, 92), 400, 600)
    assert yes["tag"] == "BADA" and yes["src"] == "GC+UX ✓"
    flip = rank.two_source(big(400, 95), big(-600, 92), 400, -600)       # both here, signs differ: capped
    assert flip["tag"] == "notable" and flip["src"] == "sources disagree" and flip["capped"] == "sources disagree"
    half = rank.two_source(big(400, 95), big(90, 40), 400, 90)           # both here, one >= p70 and one not: capped
    assert half["tag"] == "notable" and half["src"] == "sources disagree"
    alone = rank.two_source(big(400, 99), None, 400, None)               # the second source ABSENT: not capped
    assert alone["tag"] == "BADA" and alone["single"] == "GC" and alone["src"] == "GC only"


def test_day_kinds_rank_only_against_their_own_kind():
    days = [f"2026-10-{d:02d}" for d in range(1, 13)]
    kinds = {d: ("EXPIRY" if n < 3 else "NORMAL") for n, d in enumerate(days)}
    marks = {"days": days, "ce": {"36000": [1000 if kinds[d] == "EXPIRY" else n * 10 for n, d in enumerate(days)]}}
    normal = rank.by_mark(marks, kinds, "NORMAL", "ce", 36000, 500)
    assert normal["n"] == 9 and normal["tag"] == "RECORD"                   # above every normal day
    exp = rank.by_mark(marks, kinds, "EXPIRY", "ce", 36000, 500)
    assert exp["tag"] == "?" and "only 3 EXPIRY" in exp["why"]             # too few expiry days: no rank, said so
    assert rank.day_kind(DAY, DAY, "2026-10-27") == "EXPIRY"
    assert rank.day_kind("2026-10-27", "2026-10-27", "2026-10-27") == "ROLL"
    assert rank.day_kind(DAY, "2026-10-21", "2026-10-27", "NSE_FO|2", "NSE_FO|1") == "ROLL"


def test_signed_pools_rank_size_and_keep_the_sign_apart():
    t = tab(list(range(-100, 101)))
    L = rank.by_part({"cvd40": [t] * 4}, "cvd40", 40000, -95)
    assert L["pct"] >= 90 and L["tag"] == "BADA" and L["pct_sign"] < 5      # big, and on the selling side


def _rows(n, delta=10, last=None):
    out = [{"t": T0 + (9 * 3600 + 15 * 60 + i * 300) * 1000, "o": 22500.0, "h": 22505.0, "l": 22495.0, "c": 22500.0,
            "vol": 100, "delta": delta, "oi": 1_000_000} for i in range(n)]
    if last is not None:
        out[-1]["delta"] = last
    return out


def _ref(idx="BANKNIFTY"):
    days = [f"2026-10-{d:02d}" for d in range(1, 13)]
    small = tab([0.5 + k / 100 for k in range(200)])                      # SIZE: everything under ~2.5x the slot median
    pools = {"ux": {"size": [small] * 4, "bvol": [tab(range(50, 150))] * 4, "cvd40": [tab(range(-200, 201))] * 4,
                    "foi40": [tab([x / 100 for x in range(-50, 51)])] * 4, "share": [tab([0.1] * 50)] * 4}}
    if idx == "NIFTY":
        pools["gc"] = dict(pools["ux"])
    slots = {str(k): 10 for k in range(37, 62)}
    return {"id": "rank-test", "before": DAY, "read": {"kinds": {d: "NORMAL" for d in days}, "last_ik": None,
            "marks": {}, "pool": {"NORMAL": pools}, "slot": {"NORMAL": {"ux": slots, "gc": slots}}}}


def _card(t="10:15"):
    return {"t": t, "w": {"cls": "QUIET", "ce": 0, "pe": 0, "A": 0.0}, "f": {"cvd": 50, "vol": 900}}


def test_a_single_source_index_reads_its_own_rank_tagged_1_src_d5():
    """BANKNIFTY / SENSEX flow is Upstox only (spec §4, D5): tagged "1 src" -- and, since the 2026-10-19 amendment,
    NOT capped: a bar 50x its slot's median is RECORD · 1 src (no second source exists to disagree)."""
    X = {"t": [], "expiry": "2026-10-27", "fut_expiry": "2026-10-27", "lot": 30}
    ux = _rows(12, last=500)                                              # 09:15 .. 10:10, the 10:10 bar huge
    r = rank.card_ranks(_ref(), "BANKNIFTY", DAY, X, _card(), [], ux, None)
    assert r["bar"]["tag"] == "RECORD" and r["bar"]["single"] == "UX" and not r["bar"].get("capped")


def test_9_oct_record_opening_reads_record_gc_only_while_a_disagreement_still_caps():
    """9 Oct: GoCharting's 09:15-10:00 CVD +6,244 was above every reference day while Upstox was not yet ticking
    (server up 10:10; the READ's flow to 10:10 is GoCharting's own bars). An absent source is not a disagreeing one."""
    days = [f"2026-09-{d:02d}" for d in range(14, 24)]
    ref = _ref("NIFTY")
    ref["read"]["marks"]["gc"] = {"days": days, "cvd": {"36000": [(-1) ** n * (300 + 300 * n) for n in range(10)]}}
    ref["read"]["kinds"].update({d: "NORMAL" for d in days})
    X = {"t": [], "expiry": "2026-10-13", "fut_expiry": "2026-10-27", "lot": 65}
    gc = [dict(r, delta=694) for r in _rows(12)]                         # 9 x 694 = 6,246 by 10:00
    rows = [{"t": "10:00", "flow": {"cvd": 6246, "vol": 9000, "gc": "10:00"}}]
    card = {"t": "10:15", "w": {"cls": "QUIET"}, "f": {"cvd": 6300, "vol": 9900, "gc": "10:10"}}
    r = rank.card_ranks(ref, "NIFTY", "2026-10-09", X, card, rows, [], gc)
    assert r["open"]["raw"] == 6246 and r["open"]["tag"] == "RECORD" and r["open"]["src"] == "GC only"
    assert not r["open"].get("capped")


def test_nifty_needs_both_sources_and_a_later_bar_changes_nothing_no_look_ahead():
    X = {"t": [], "expiry": "2026-10-27", "fut_expiry": "2026-10-27", "lot": 65}
    ux, gc = _rows(12, last=500), _rows(12, last=480)
    r = rank.card_ranks(_ref("NIFTY"), "NIFTY", DAY, X, _card(), [], ux, gc)
    assert r["bar"]["tag"] == "RECORD" and r["bar"]["src"] == "GC+UX ✓"       # 48x its slot: above every day
    later = rank.card_ranks(_ref("NIFTY"), "NIFTY", DAY, X, _card(), [], ux + _rows(20)[12:], gc + _rows(20)[12:])
    assert later["bar"] == r["bar"]                                        # bars after the mark are never read
    gc[-1]["delta"] = -480                                                # both present, signs differ: capped
    dis = rank.card_ranks(_ref("NIFTY"), "NIFTY", DAY, X, _card(), [], ux, gc)["bar"]
    assert dis["src"] == "sources disagree" and dis["tag"] == "notable" and dis["capped"] == "sources disagree"


def test_positioning_words_wait_for_the_rank():
    big, small = {"pct": 92.0}, {"pct": 40.0}
    assert rank.likhna_word({"cls": "CALL"}, big, small)["word"] == "CALL LIKH RAHE"
    w = rank.likhna_word({"cls": "CALL"}, small, small)
    assert w["gated"] and "likh rahe" not in w["word"].lower() and "noise" in w["word"]
    assert rank.fuel_word(+5, +10) == "naye long" and rank.fuel_word(+5, -10) == "naye short"
    assert rank.fuel_word(-5, +10) == "covering" and rank.fuel_word(-5, -10) == "long chhod rahe"


def test_running_totals_stop_at_a_hole_never_guess():
    bs = rank.bars_of(_rows(10))
    fm = rank.flow_marks(bs)
    assert fm[36000]["cvd"] == 90                                          # 09:15 .. 09:55, nine bars of +10
    holed = rank.bars_of([r for n, r in enumerate(_rows(10)) if n != 4])   # the 09:35 bar missing
    fm = rank.flow_marks(holed)
    assert fm[34500]["cvd"] == 40 and fm[34800]["cvd"] is None and fm[36000]["cvd"] is None
    assert rank._gap_why(holed, 36000, "GC").endswith("GC 09:35 bar missing")
