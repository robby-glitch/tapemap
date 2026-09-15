"""The morning seed: an 11:00 start must still get a 09:15 basis.

The hazard this guards is Ledger.feed's FIRST observation writing
`unwatched = oi` -- a ledger the live path already touched has written the
morning off permanently, so the seed must REBUILD, not top up.
"""
import chainside


def _legs(k=23500.0):
    """Two hours of a CE writing itself up, 09:15 -> 11:15, premium falling."""
    oi = {f"{9 + (m // 60):02d}:{m % 60:02d}": 1_000_000 + (m - 15) * 10_000
          for m in range(15, 121)}
    px = {t: 120.0 - i * 0.5 for i, t in enumerate(sorted(oi))}
    return {k: {"ce": (oi, 1_000_000, px), "pe": ({}, None, {})}}


def test_seed_gives_a_real_basis_and_session_coverage():
    cs = chainside.ChainSide()
    n = cs.seed_from_rest(_legs())
    assert n == 1, "one leg had data, one was empty"
    led = cs._led[(23500.0, "ce")]
    assert led.basis is not None
    # premium fell 120 -> ~67 while OI was built, so the writers' volume
    # weighted basis must land inside that range, not at either end
    assert 67.0 < led.basis < 120.0, led.basis
    assert led.confidence() == "session", led.confidence()


def test_rebuild_not_topup_when_live_touched_first():
    """The bug: seeding a ledger the live path already opened."""
    cs = chainside.ChainSide()
    cs.seed = "running"                      # as maybe_seed would have set it
    cs.on_snapshot("11:20:00", [{"k": 23500.0,
                                 "ce": {"oi": 2_200_000, "ltp": 60.0},
                                 "pe": {"oi": 1, "ltp": 1.0}}])
    touched = cs._led[(23500.0, "ce")]
    assert touched.unwatched == 2_200_000, "live wrote the morning off"
    assert cs._buf, "the live observation must be buffered, not dropped"

    cs.seed_from_rest(_legs())
    led = cs._led[(23500.0, "ce")]
    assert led is not touched, "must be a FRESH ledger, not the touched one"
    assert led.unwatched == 1_000_000, "seeded from the 09:15 bar"
    assert led.confidence() == "session"
    assert cs.seed == "done" and cs._buf == []


def test_a_leg_the_seed_missed_keeps_its_live_ledger():
    cs = chainside.ChainSide()
    cs.on_snapshot("11:20:00", [{"k": 99999.0,
                                 "ce": {"oi": 500, "ltp": 5.0},
                                 "pe": {"oi": 1, "ltp": 1.0}}])
    keep = cs._led[(99999.0, "ce")]
    cs.seed_from_rest(_legs())
    assert cs._led[(99999.0, "ce")] is keep, "a partial morning beats a dropped leg"
    assert (23500.0, "ce") in cs._led


def test_seed_never_runs_off_upstox(monkeypatch):
    monkeypatch.setenv("TAPEMAP_BROKER", "dhan")
    cs = chainside.ChainSide()
    cs.idx = "NIFTY"
    cs.maybe_seed([{"k": 23500.0}])
    assert cs.seed.startswith("off"), cs.seed
