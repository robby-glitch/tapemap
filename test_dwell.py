"""dwell.py -- the trap detector fires on a real dwell, and says why not
otherwise. The positive case is asserted first: a detector whose suite only
ever checks the quiet path passes whether or not it can fire at all (the
chainside drain lesson, applied at birth)."""

import dwell


def _strikes(ce_oi=1000.0, pe_oi=1000.0):
    out = []
    for k in (24900, 24950, 25000, 25050, 25100):
        out.append({"k": k,
                    "ce": {"oi": ce_oi, "ltp": 100.0, "bid": 99.0, "ask": 101.0},
                    "pe": {"oi": pe_oi, "ltp": 100.0, "bid": 99.0, "ask": 101.0}})
    return out


LEVELS = [{"kind": "PDL", "px": 25000.0, "stable": True, "frame": "index"}]


def _calibrated(w, spot=25000.0):
    """Feed enough 1-minute samples to calibrate the band. Non-monotonic
    moves on purpose -- a monotonic warm-up hides percentile traps."""
    for i, wiggle in enumerate((0, 3, -2, 4, -3, 2, -4)):
        w.on_snapshot(i * 60.0, spot + wiggle, _strikes(), [])
    return w


def test_band_is_absent_until_calibrated_and_says_so():
    w = dwell.DwellWatch()
    r = w.on_snapshot(0, 25000.0, _strikes(), LEVELS)
    assert not r["active"] and "calibrating" in r["why"]
    assert w.band() is None


def test_a_real_dwell_fires_and_measures_what_loaded():
    w = _calibrated(dwell.DwellWatch())
    t0 = 1000.0
    # hold at PDL while PE OI builds -- the trap being set
    for n in range(8):
        r = w.on_snapshot(t0 + n * 60.0, 25001.0,
                          _strikes(pe_oi=1000.0 + n * 500.0), LEVELS)
    assert r["active"] is True
    assert r["level"] == {"kind": "PDL", "px": 25000.0}
    assert r["held_s"] >= dwell.DWELL_MIN_S
    assert r["oi_added_pe"] > 0 and r["loaded_side"] == "pe"
    assert r["buyers_crossing"] is not None    # ltp sits at mid in the fixture
    assert r["tag"] == "I"                     # the attribution, forever


def test_leaving_the_band_ends_the_hold():
    w = _calibrated(dwell.DwellWatch())
    w.on_snapshot(1000.0, 25001.0, _strikes(), LEVELS)
    assert w.read["holding"]
    r = w.on_snapshot(1010.0, 25200.0, _strikes(), LEVELS)
    assert not r["active"] and "not at any known level" in r["why"]
    # a fresh return starts a NEW hold, not a resumed one
    r2 = w.on_snapshot(1020.0, 25001.0, _strikes(), LEVELS)
    assert r2["held_s"] == 0


def test_no_spot_is_a_stated_absence():
    w = dwell.DwellWatch()
    r = w.on_snapshot(0, None, _strikes(), LEVELS)
    assert not r["active"] and "no spot" in r["why"]
