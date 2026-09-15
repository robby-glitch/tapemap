"""hunt.py -- the runway map ranks fuel, names its target, and counts what
it could NOT project out loud."""

import hunt

LEVELS = [
    {"kind": "PDH", "px": 25200.0, "stable": True},
    {"kind": "PDL", "px": 24800.0, "stable": True},
    # pin physics, not a destination -- must never be a runway target
    {"kind": "GAMMA_FLIP", "px": 25050.0, "stable": False},
]


def _leg(k, side, oi=1000, ltp=100.0, basis=90.0, delta=0.5):
    return {"k": k, "side": side, "oi": oi, "ltp": ltp, "basis": basis,
            "delta": delta if side == "ce" else -delta}


def test_runways_refuse_without_a_band_or_spot():
    assert hunt.runways(None, LEVELS, [], 10.0)["ok"] is False
    r = hunt.runways(25000.0, LEVELS, [], None)
    assert r["ok"] is False and "band" in r["why"]


def test_targets_are_reaction_points_never_the_flip():
    r = hunt.runways(25000.0, LEVELS, [], 10.0)
    assert r["up"]["target"] == {"kind": "PDH", "px": 25200.0}
    assert r["down"]["target"] == {"kind": "PDL", "px": 24800.0}


def test_fuel_counts_underwater_writers_and_names_the_richer_side():
    legs = [_leg(25100, "ce", oi=2000),          # CE writers: up-move fuel
            _leg(24900, "pe", oi=100)]           # thin PE side
    r = hunt.runways(25000.0, LEVELS, legs, 10.0)
    assert r["up"]["fuel"] > 0
    assert r["up"]["items"][0]["k"] == 25100
    assert r["richer"] == "UP"
    # the inference is labeled, with its basis stated
    assert r["up"]["stop_zone"]["tag"] == "I"
    assert "invisible" in r["up"]["stop_zone"]["basis"]
    assert r["tag"] == "I"


def test_a_leg_without_delta_is_counted_out_loud_not_skipped_silently():
    legs = [_leg(25100, "ce", delta=None)]
    legs[0]["delta"] = None
    r = hunt.runways(25000.0, LEVELS, legs, 10.0)
    assert r["up"]["fuel"] == 0
    assert "NOT counted" in r["up"]["why"]


def test_no_level_ahead_is_a_stated_absence():
    r = hunt.runways(25000.0, [{"kind": "PDL", "px": 24800.0}], [], 10.0)
    assert r["up"]["target"] is None
    assert "no known level" in r["up"]["why"]
