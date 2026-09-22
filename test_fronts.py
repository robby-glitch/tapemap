"""The near-ATM fronts and the fade gate -- §1d, pre-registered 2026-09-23.

The shape under test is the one the live grid had on 2026-09-22: NIFTY fell
23475 -> 23370 between 10:20 and 10:50, and the put front that should have
defended the lower band, PE 23400, peaked at 10:19 and gave back most of its
build. Every fixture below is built to that shape, with synthetic round
numbers -- no production rows.
"""

import fronts


def _grid(times, spot, per_strike):
    """``{"HH:MM": {"spot": .., "k": {strike: (ce, pe)}}}`` from per-strike series.

    `per_strike` is ``{strike: (ce_series, pe_series)}``, each series as long as
    `times`.
    """
    return {t: {"spot": spot,
                "k": {k: (ce[i], pe[i]) for k, (ce, pe) in per_strike.items()}}
            for i, t in enumerate(times)}


def _flat(v, n):
    return [v] * n


def _ramp(a, b, n):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


TIMES = [f"{9 + (15 + i) // 60:02d}:{(15 + i) % 60:02d}" for i in range(40)]


def test_the_front_that_peaked_first_is_the_one_named():
    """PE gave back its build after peaking early; CE never stopped."""
    n = len(TIMES)
    pe = _ramp(0, 200, 20) + _ramp(200, 60, n - 20)      # peaks at mark 19
    ce = _ramp(0, 300, n)                                # never stops
    rows = fronts.read(_grid(TIMES, 23400.0, {23400.0: (ce, pe)}))
    pe_front = fronts.side_front(rows, "PE")
    ce_front = fronts.side_front(rows, "CE")
    assert pe_front["state"] == fronts.UNWINDING
    assert pe_front["peak_at"] == TIMES[19]
    assert pe_front["from_peak"] < 0
    assert ce_front["state"] == fronts.BUILDING
    assert fronts.broke(rows) is pe_front


def test_a_far_strike_never_enters_the_read():
    """Her rule: 23700 PE writers are irrelevant. NEAR keeps them out."""
    n = len(TIMES)
    per = {23400.0 + 50 * i: (_ramp(0, 10, n), _ramp(0, 10, n)) for i in range(12)}
    per[23400.0] = (_ramp(0, 300, n), _ramp(0, 300, n))
    ks = {f["k"] for f in fronts.read(_grid(TIMES, 23400.0, per))}
    assert 23400.0 in ks
    # the nine nearest of a 50-point ladder starting AT spot reach 23800 at
    # most; anything past that is out of the window by construction
    assert max(ks) <= 23400.0 + 50 * (fronts.NEAR - 1)


def test_ranking_uses_peak_oi_so_an_unwound_front_stays_visible():
    """A front that gave back 70% must not drop out of the top two."""
    n = len(TIMES)
    big = _ramp(0, 200, 10) + _ramp(200, 20, n - 10)     # huge, then gone
    small = _ramp(0, 90, n)                              # steady, now larger
    g = _grid(TIMES, 23400.0, {23400.0: (_flat(0, n), big),
                               23450.0: (_flat(0, n), small)})
    peak = {(23400.0, "pe"): 9_000_000, (23450.0, "pe"): 3_000_000}
    top = fronts.side_front(fronts.read(g, peak), "PE")
    assert top["k"] == 23400.0          # ranked on peak OI, not on `chg`
    assert top["state"] == fronts.UNWINDING


def test_fade_is_illegal_when_its_defender_gave_up():
    n = len(TIMES)
    pe = _ramp(0, 200, 20) + _ramp(200, 60, n - 20)
    rows = fronts.read(_grid(TIMES, 23400.0, {23400.0: (_ramp(0, 300, n), pe)}))
    gate = fronts.fade_gate(rows, "buy")
    assert gate["legal"] is False
    assert gate["defender"] == "PE"
    assert "23400" in gate["why"]
    # the same tape, faded the other way, still has its defender
    assert fronts.fade_gate(rows, "sell")["legal"] is True


def test_the_engine_veto_beats_a_building_defender():
    n = len(TIMES)
    rows = fronts.read(_grid(TIMES, 23400.0,
                             {23400.0: (_ramp(0, 300, n), _ramp(0, 300, n))}))
    assert fronts.fade_gate(rows, "buy")["legal"] is True
    vetoed = fronts.fade_gate(rows, "buy",
                              plays=["NO FADE at 23360 - negative gamma; "
                                     "continuation only"])
    assert vetoed["legal"] is False
    assert vetoed["veto"] is True


def test_an_unrelated_play_is_not_a_veto():
    n = len(TIMES)
    rows = fronts.read(_grid(TIMES, 23400.0,
                             {23400.0: (_ramp(0, 300, n), _ramp(0, 300, n))}))
    gate = fronts.fade_gate(rows, "buy",
                            plays=["RIDE the hedge flow - dips toward VWAP "
                                   "are entries, not exits"])
    assert gate["legal"] is True
    assert gate["veto"] is False


def test_a_missing_grid_is_pata_nahi_and_never_legal():
    """"Could not check" must not render as "checked and found nothing"."""
    for empty in ({}, None, {"09:15": {"spot": None, "k": {}}}):
        assert fronts.read(empty) == []
    gate = fronts.fade_gate([], "buy")
    assert gate["legal"] is None
    assert gate["why"] == "near-ATM fronts not read"


def test_json_string_strike_keys_read_the_same_as_numbers():
    """In memory the grid is keyed by number; over HTTP it is keyed by string."""
    n = len(TIMES)
    g = _grid(TIMES, 23400.0, {23400.0: (_ramp(0, 300, n), _ramp(0, 120, n))})
    as_num = fronts.read(g)
    as_str = fronts.read({t: {"spot": r["spot"],
                              "k": {str(int(k)): v for k, v in r["k"].items()}}
                          for t, r in g.items()})
    assert [(f["side"], f["k"], f["state"]) for f in as_num] == \
           [(f["side"], f["k"], f["state"]) for f in as_str]


def test_a_flat_front_is_stalled_not_unwinding():
    n = len(TIMES)
    flat = _ramp(0, 200, 20) + _flat(200, n - 20)
    rows = fronts.read(_grid(TIMES, 23400.0, {23400.0: (_ramp(0, 300, n), flat)}))
    assert fronts.side_front(rows, "PE")["state"] == fronts.STALLED
    # stalled still fails the gate: the defender stopped adding
    assert fronts.fade_gate(rows, "buy")["legal"] is False


def test_nobody_broke_yet_means_no_front_is_named():
    n = len(TIMES)
    rows = fronts.read(_grid(TIMES, 23400.0,
                             {23400.0: (_ramp(0, 300, n), _ramp(0, 300, n))}))
    assert fronts.broke(rows) is None


def test_a_bad_side_is_refused_rather_than_guessed():
    gate = fronts.fade_gate([{"side": "PE", "k": 1.0, "state": "BUILDING",
                              "peak_at": "09:20"}], "sideways")
    assert gate["legal"] is None
    assert gate["defender"] is None


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_"):
            _fn(); print("ok", _name)
