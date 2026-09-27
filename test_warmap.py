"""warmap.py -- the assembled board: composition only, every absence stated,
nothing recomputed per HTTP read."""

import time
from datetime import datetime

import chainside
import warmap

IN_HOURS = datetime(2026, 8, 21, 10, 30)


def _doc(sec, spot, pe_oi=1000.0):
    strikes = []
    for k in (24900, 24950, 25000, 25050, 25100):
        strikes.append({"k": k,
                        "ce": {"oi": 1000.0, "ltp": 100.0, "oi_chg": 50.0,
                               "bid": 99.0, "ask": 101.0, "delta": 0.5},
                        "pe": {"oi": pe_oi, "ltp": 100.0, "oi_chg": 30.0,
                               "bid": 99.0, "ask": 101.0, "delta": -0.5}})
    return {"ok": True, "ts": "10:30:00", "sec": sec, "spot": spot,
            "strikes": strikes,
            "metrics": {"max_pain": 25000, "flip_px": 24950.0}}


def _stub_fetch(idx):
    return {"day": "x", "pd": {"date": "d", "h": 25150.0, "l": 24850.0,
                               "c": 25000.0}, "pw": None, "open": None}


def _fed_board(tmp_path):
    wm = warmap.WarMap("NIFTY", seq_path=str(tmp_path / "w.jsonl"),
                       fetch=_stub_fetch)
    cs = chainside.ChainSide()
    for n in range(8):
        sec = 34200 + n * 60
        cs.on_snapshot(str(sec), _doc(sec, 25000.0)["strikes"])
        wm.on_snapshot(_doc(sec, 25000.0 + (n % 3)), cs, now=IN_HOURS)
    return wm, cs


def test_the_board_assembles_every_object_and_states_absences(tmp_path):
    wm, cs = _fed_board(tmp_path)
    st = wm.state()
    assert st["ok"] is True
    for key in ("levels", "dwell", "runways", "heat", "sequence",
                "seq_log"):
        assert key in st, key
    # the daily fetch thread is async; wait for the stub to land, then feed
    # ONE more snapshot -- state() serves the last ASSEMBLED reading, never
    # a recompute, so the map picks up PDH on the next chain pace, not sooner
    for _ in range(200):
        if wm.levels.daily:
            break
        time.sleep(0.01)
    wm.on_snapshot(_doc(35000, 25001.0), cs, now=IN_HOURS)
    st = wm.state()
    assert any(l["kind"] == "PDH" for l in st["levels"])
    assert st["daily_why"] is None


def test_heat_carries_pain_from_the_ledgers(tmp_path):
    wm, cs = _fed_board(tmp_path)
    rows = wm.last["heat"]
    assert [r["k"] for r in rows] == sorted(r["k"] for r in rows)
    r = rows[0]
    assert r["ce_oi"] == 1000.0 and r["ce_chg"] == 50.0
    assert r["ce_pain"] is not None            # ledgers were fed, pain known


def test_heat_carries_the_ledgers_own_coverage_next_to_the_pain(tmp_path):
    """Without this the fuel tank cannot tell a basis built watching 90% of a
    wall from one that saw 10% after an 11:00 start -- the two produce the
    same-looking `_pain` and the second is nearly worthless.

    NOT a confidence score (house rule 4). It is `trapped_inventory.Ledger.
    confidence()`, a coverage statement about the ledger's own observation,
    the same string `Ledger.snapshot()` has always published.
    """
    wm, cs = _fed_board(tmp_path)
    r = wm.last["heat"][0]
    for side in ("ce", "pe"):
        assert side + "_conf" in r
        assert r[side + "_conf"] in (None, "none", "low", "session")
    # a fed ledger has a basis, so it is past "no ledger at all"
    assert r["ce_conf"] is not None


def _led_after(rows):
    """A ledger driven through a real `feed` sequence of `(oi, price)`.

    Every state below is CONSTRUCTED, never asserted by set membership -- the
    original test checked `conf in (None,"none","low","session")`, which
    passed happily while `"low"` was arithmetically unreachable and every
    wall claimed full coverage.
    """
    import trapped_inventory
    led = trapped_inventory.Ledger(side="short")
    for i, (oi, px) in enumerate(rows):
        led.feed(f"09:{15 + i:02d}", oi, px)
    return led


def test_a_late_start_on_a_built_wall_reads_low():
    """The operator's own case: open the laptop at 11:00, the CE wall is
    already 9.0M, and 0.5M more arrives by the close. The basis describes a
    twentieth of the wall, so the coverage must say so.

    THIS IS THE CASE THAT WAS BROKEN. Before the fix `seen_build` (0.5M) was
    compared against `size` (0.5M) and reported "session" -- full confidence
    in a basis built from 5% of the position."""
    led = _led_after([(9_000_000, 40.0), (9_500_000, 44.0)])
    assert led.unwatched == 9_000_000
    assert led.seen_build == 500_000
    assert led.confidence() == "low"


def test_a_wall_watched_from_scratch_reads_session():
    """A strike listed fresh this morning: nothing pre-existed, so every unit
    was watched joining and the basis speaks for the whole book."""
    led = _led_after([(0, 40.0), (600_000, 42.0), (1_000_000, 45.0)])
    assert led.unwatched == 0
    assert led.confidence() == "session"


def test_a_ledger_with_no_build_yet_reads_none():
    """Observed, but nothing has joined -- there is no basis to be confident
    about. Distinct from `None` (no ledger for this leg at all)."""
    led = _led_after([(9_000_000, 40.0), (9_000_000, 40.5)])
    assert led.basis is None and led.confidence() == "none"


def test_a_book_that_fully_drained_reads_none():
    """`size` back to zero: whatever the basis once described has left, so it
    describes nothing now."""
    led = _led_after([(0, 40.0), (500_000, 42.0), (0, 39.0)])
    assert led.size == 0 and led.confidence() == "none"


def test_the_three_states_are_all_reachable_and_ordered():
    """The regression guard. Watched share crossing 50% is the boundary, and
    the ladder must actually move -- a single expression that can only ever
    return one value is what shipped before."""
    seen = {_led_after(rows).confidence() for rows in (
        [(9_000_000, 40.0), (9_000_000, 40.5)],              # none
        [(9_000_000, 40.0), (9_500_000, 44.0)],              # low  (5%)
        [(100_000, 40.0), (1_000_000, 45.0)],                # session (90%)
    )}
    assert seen == {"none", "low", "session"}


def test_churn_does_not_buy_confidence_it_did_not_earn():
    """A book that builds and unwinds repeatedly accumulates `seen_build`
    while the pre-existing tranche stays unknowable. Deliberately cautious:
    overstating coverage is the failure that just happened."""
    led = _led_after([(10_000_000, 40.0),
                      (11_000_000, 42.0), (10_000_000, 41.0),
                      (11_000_000, 43.0), (10_000_000, 41.0),
                      (11_000_000, 44.0)])
    assert led.seen_build == 3_000_000            # gross builds watched
    assert led.confidence() == "low"              # against a 10M opening book


def test_the_old_dead_comparison_is_gone():
    """`seen_build` only grows and `size` shrinks on exits, so `seen_build >=
    size` is an invariant -- any comparison of the two can never reach "low".
    Pinned by source so the arithmetic cannot quietly regress."""
    import inspect

    import trapped_inventory
    src = inspect.getsource(trapped_inventory.Ledger.confidence)
    body = src.split('"""')[-1]
    assert "self.size * 0.5" not in body
    assert "self.unwatched" in body


def test_no_ledger_and_a_ledger_with_no_basis_are_two_different_answers():
    """`None` = there is no ledger for this leg. `"none"` = the ledger exists
    and has not seen a build yet. Collapsing them would say "we watched and
    saw nothing" when the truth is "we were not watching" -- house rule 6."""
    import trapped_inventory

    led = trapped_inventory.Ledger(side="short")
    assert led.confidence() == "none"           # exists, no basis yet
    rows = warmap.WarMap._heat(
        [{"k": 24000, "ce": {"oi": 1.0, "oi_chg": 0.0, "ltp": 10.0},
          "pe": {"oi": 1.0, "oi_chg": 0.0, "ltp": 10.0}}],
        type("CS", (), {"_led": {(24000, "ce"): led}})())
    assert rows[0]["ce_conf"] == "none"         # ledger present, nothing seen
    assert rows[0]["pe_conf"] is None           # no ledger for this leg at all


def test_a_cold_board_says_so_instead_of_serving_zeros():
    wm = warmap.WarMap("NIFTY", fetch=_stub_fetch)
    st = wm.state()
    assert st["ok"] is False and "no chain snapshot" in st["why"]


def test_boards_isolate_indices():
    b = warmap.Boards()
    assert b.for_index("NIFTY") is b.for_index("NIFTY")
    assert b.for_index("NIFTY") is not b.for_index("SENSEX")
