"""run_states(band=...) -- THE ZONE armed at the near edge (§1b, UNSCORED).

The zone rule is the operator's stated setup: the sky-blue 2σ→3σ shading,
where reaching d2 IS the event and d3 is only the far edge. It runs on the
SAME machine as §5c -- one loop, one window, one lock -- with only the arming
band changed, so these tests pin three things: the d2 arm fires where the d3
machine still waits, the receipt names the band it really armed on, and the
default path stays byte-identical to what §5c always produced.

Fixtures are the flat index shape from test_band_rotation_run.py: VWAP 100,
sigma 5, so d2 is 90 and d3 is 85, readable at a glance.
"""

import band_rotation
from band_rotation import run_states

VWAP = 100.0
SD = 5.0
D3 = VWAP - 3 * SD          # 85.0
D2 = VWAP - 2 * SD          # 90.0
U2 = VWAP + 2 * SD          # 110.0

OPEN_MIN = 9 * 60 + 30


def _t(i, base=OPEN_MIN, step=3):
    m = base + step * i
    return f"{m // 60:02d}:{m % 60:02d}"


def _bar(t, low, high, close, **over):
    b = {"vwap": VWAP, "u1": VWAP + SD, "d1": VWAP - SD,
         "u2": U2, "d2": D2, "u3": VWAP + 3 * SD, "d3": D3}
    b.update({"t": t, "o": close, "h": high, "l": low, "c": close})
    b.update(over)
    return b


def test_the_zone_arms_at_d2_where_the_d3_machine_still_waits():
    # Low touches d2 (90) but never d3 (85): the event per §1b.
    bars = [_bar(_t(0), 89.5, 95.0, 92.0), _bar(_t(1), 91.0, 94.0, 93.0)]
    zone = run_states(bars, band="d2")
    d3 = run_states(bars)
    assert zone[0]["state"] == "ARMED"
    assert d3[0]["state"] == "WAITING"


def test_the_zone_receipt_names_the_band_it_armed_on():
    # Arm at d2, then a later close above the arming bar's high triggers.
    bars = [_bar(_t(0), 89.5, 93.0, 91.0), _bar(_t(1), 92.0, 96.0, 95.5)]
    zone = run_states(bars, stop_pts=20.0, band="d2")
    entry = zone[1]["entry"]
    assert entry is not None and entry["band"] == "d2"
    assert "touched d2 90.00" in entry["trigger"]
    assert "d3" not in entry["trigger"]
    # The stop measures from the band it armed on: d2 - 20.
    assert entry["stop"] == D2 - 20.0


def test_the_sell_zone_is_the_u2_mirror():
    bars = [_bar(_t(0), 105.0, 110.5, 107.0), _bar(_t(1), 102.0, 106.0, 102.5)]
    zone = run_states(bars, stop_pts=20.0, side="SELL", band="u2")
    assert zone[0]["state"] == "ARMED"
    entry = zone[1]["entry"]
    assert entry is not None and entry["side"] == "SELL" and entry["band"] == "u2"
    assert "touched u2 110.00" in entry["trigger"]
    assert entry["stop"] == U2 + 20.0


def test_the_default_band_is_untouched():
    # §5c's population must not move: no band argument == band="d3", including
    # the receipt sentence, on a session that arms and fires the old rule.
    bars = [_bar(_t(0), 84.0, 88.0, 86.0), _bar(_t(1), 87.0, 92.0, 91.0),
            _bar(_t(2), 90.0, 93.0, 92.0)]
    assert run_states(bars, stop_pts=20.0) == \
        run_states(bars, stop_pts=20.0, band="d3")


def test_the_zone_rides_the_live_payload_beside_5c_not_inside_it():
    # `_at_interval` publishes zone_state/zone_state_sell as siblings of
    # run_state, 1:1 with the bars — reusing the interval suite's fixtures.
    import live
    import test_index_interval as tii
    out = live._at_interval(tii._session(tii._inert(60)), 3)
    assert len(out["zone_state"]) == len(out["bars"])
    assert len(out["zone_state_sell"]) == len(out["bars"])
    # tii's "inert" bars sit at low 88 — below d2 (90) but above d3 (85):
    # invisible to §5c, an armed setup to the zone. The separation IS the test.
    assert any(s["state"] != "WAITING" for s in out["zone_state"])
    assert all(s["state"] == "WAITING" for s in out["run_state"])


def test_a_d2_only_session_never_reaches_the_d3_population():
    # The separation the docs demand: a zone entry adds NOTHING to §5c's rows.
    bars = [_bar(_t(0), 89.0, 93.0, 91.0), _bar(_t(1), 92.5, 97.0, 96.0)]
    zone = run_states(bars, band="d2")
    d3 = run_states(bars)
    assert any(s["entry"] for s in zone)
    assert not any(s["entry"] for s in d3)


def test_score_admits_zone_rows_as_their_own_population(tmp_path):
    # Outcome-filling is §5e's machinery, so `score` fills rule:"zone" rows —
    # but legacy (untagged) rows stay quarantined exactly as before.
    import json
    import trigger_log
    log = tmp_path / "log.jsonl"
    rows = [
        {"day": "2026-08-19", "index": "NIFTY", "t": "11:12", "side": "BUY",
         "band": "d2", "rule": "zone", "px": 24110.0, "level": 24100.0,
         "closed_bar": True},
        {"day": "2026-08-19", "index": "NIFTY", "t": "11:12", "side": "BUY",
         "band": "d3", "px": 24110.0, "closed_bar": True},  # legacy: no rule
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                   encoding="utf-8")
    trigger_log.score(path=str(log), quiet=True)
    out = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
    zone, legacy = out[0], out[1]
    # The zone row was ADMITTED: it is either scored or carries an explicit
    # unscored reason (this test machine may lack the cached session).
    assert zone.get("f30") is not None or zone.get("unscored")
    # The legacy row stays quarantined BY RULE: no outcome, no reason field.
    assert legacy.get("f30") is None and not legacy.get("unscored")
