"""Runs of three: causal percentile, gap, side, in-place growth (spec 2026-09-20 §G)."""
import runs

T = 1789098300000


def F(sec, side, q, hidden=False):
    return {"ltt": T + sec * 1000, "side": side, "p": 100.0, "q": q, "hidden": hidden}


def _warm(r, n=50, sizes=(65, 130, 195, 260, 325), start=0):
    """Fifty fills, ten of each size, 10 s apart (no run can form): the sorted
    window is 10x65..10x325 and index int(50*0.9)=45 lands on 325 -- so 'big'
    is >= 325 units (5 lots) and a 65-unit fill is clearly small."""
    for i in range(n):
        r.on_fill(F(start + i * 10, 1 if i % 2 else -1, sizes[i % len(sizes)]))


def test_nothing_fires_under_min_n_and_why_says_so():
    r = runs.Runs(lot=65)
    assert r.why() == "fewer than 50 fills in the last 20 minutes — the percentile has nothing to rank against"
    for i in range(49):
        assert r.on_fill(F(i, 1, 65_000)) is None
    assert r.events == [] and r.window_n == 49


def test_three_big_same_side_fills_inside_three_seconds_fire_once_then_grow():
    r = runs.Runs(lot=65)
    _warm(r)                                         # threshold 325 units = 5 lots
    assert r.on_fill(F(600, 1, 650)) is None
    assert r.on_fill(F(602, 1, 650)) is None
    ev = r.on_fill(F(604, 1, 650))
    assert ev is not None and ev["kind"] == "run" and ev["side"] == 1 and ev["n"] == 3
    assert ev["from_t"] == T + 600_000 and ev["to_t"] == T + 604_000 and ev["t"] == ev["to_t"]
    assert ev["qty"] == 30 and ev["thr"] == 5 and ev["src"] == "ux" and ev["tag"] == "I" and ev["p"] == 100.0
    assert ev["why"] == "3 buys ≥ 5 lots inside 3 s — each in the top decile of the last 20 min"
    assert r.on_fill(F(606, 1, 650)) is None         # the same run, still pressing
    assert len(r.events) == 1 and r.events[0]["n"] == 4 and r.events[0]["to_t"] == T + 606_000 and r.events[0]["qty"] == 40
    assert r.why() is None


def test_a_gap_over_three_seconds_restarts_the_run():
    r = runs.Runs(lot=65)
    _warm(r)
    r.on_fill(F(600, 1, 650)); r.on_fill(F(602, 1, 650))
    assert r.on_fill(F(606, 1, 650)) is None         # 4 s after the last: a new run of one
    assert r.on_fill(F(607, 1, 650)) is None and r.on_fill(F(608, 1, 650)) is not None


def test_a_big_opposite_fill_breaks_the_run_a_small_one_does_not():
    r = runs.Runs(lot=65)
    _warm(r)
    r.on_fill(F(600, 1, 650)); r.on_fill(F(601, -1, 65)); r.on_fill(F(602, 1, 650))   # small sell ignored
    assert r.on_fill(F(603, 1, 650)) is not None
    r2 = runs.Runs(lot=65)
    _warm(r2)
    r2.on_fill(F(600, 1, 650)); r2.on_fill(F(601, -1, 650)); r2.on_fill(F(602, 1, 650))  # big sell breaks
    assert r2.on_fill(F(603, 1, 650)) is None


def test_the_percentile_is_causal_the_judged_fill_is_not_in_its_own_window():
    """Window = sizes 65*1..65*50, so the causal bar (index 45 of 50) is 46*65 = 2990.
    A fill of 45*65 = 2925 must NOT qualify. If the fill were inserted before being
    judged, the 51-value window's index 45 would be 2925 itself and it WOULD --
    and the second and third such fills would then complete a run at 602 s."""
    r = runs.Runs(lot=65)
    for i in range(50):
        r.on_fill(F(i * 10, 1 if i % 2 else -1, 65 * (i + 1)))
    assert r.on_fill(F(600, 1, 2925)) is None
    assert r.on_fill(F(601, 1, 2925)) is None           # once inserted, 2925 IS the bar: this one qualifies (run of 1)
    assert r.on_fill(F(602, 1, 2925)) is None           # run of 2 -- a non-causal window would have fired here
    assert r.on_fill(F(603, 1, 2925)) is not None       # run of 3


def test_a_fill_with_no_side_neither_joins_nor_breaks():
    r = runs.Runs(lot=65)
    _warm(r)
    r.on_fill(F(600, 1, 650)); r.on_fill(F(601, 0, 650)); r.on_fill(F(602, 1, 650))
    assert r.on_fill(F(603, 1, 650)) is not None


def test_a_lotless_run_says_units_not_lots():
    r = runs.Runs()                                  # no lot -- _lots is a no-op
    _warm(r)
    r.on_fill(F(600, 1, 650)); r.on_fill(F(602, 1, 650))
    ev = r.on_fill(F(604, 1, 650))
    assert ev["unit"] == "units" and "units" in ev["why"] and "lots" not in ev["why"]
    assert ev["qty"] == 1950 and ev["thr"] == 325             # unscaled -- still units


def test_the_window_forgets_fills_older_than_twenty_minutes():
    r = runs.Runs(lot=65)
    _warm(r)                                         # last at 490 s
    r.on_fill(F(490 + 1201, 1, 650))                 # everything before is out of the window
    assert r.window_n == 1
