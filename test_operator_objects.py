"""test_operator_objects.py -- both modules born against the Aug-19 fixture.

The fixture's known answers, established live during the session:
  * morning futures build concentrated 09:15-09:44 at ~24135-24160
  * by ~10:40 those longs were underwater; 10:15-10:44 OI fell into a falling
    price -- loss-side exits, not shorting (the aggregate-OI lie of the day)
  * the 11:06 flush must NOT fire the forcing detector (no drain, vol not extreme)
  * CE covering 14:25->14:38: OI -1.85M while ltp rose 117.4->130.8 -- forced
  * futures: ignition bar 14:33 (vol 104,195 ~= session max), drain print 14:36
    (-29,835) -> detector must FIRE long by 14:36, and not before 14:30
Run: python test_operator_objects.py   (or pytest)
"""
import json
from pathlib import Path

from trapped_inventory import Ledger
from forcing import ForcingDetector

# House convention (see test_chain_metrics.py): fixtures live in data/ and are
# located relative to this file, so the suite runs from any working directory.
FIXTURE = Path(__file__).parent / "data" / "aug19_fixture.json"
FIX = json.loads(FIXTURE.read_text(encoding="utf-8"))


def _fut_stream():
    for b in FIX["fut_1m_am"]:
        yield b["t"], b["oi"], b["c"], b["v"]
    for b in FIX["fut_3m_pm"]:
        yield b["t"], b["oi"], b["c"], b["v"]


# ── Ledger: basis, pain, and the aggregate-OI lie ─────────────────────────
def test_morning_basis_and_trapped_longs():
    led = Ledger(side="both")
    pain_at_1041 = None
    for t, oi, c, v in _fut_stream():
        led.feed(t, oi, c)
        if t == "10:41":
            pain_at_1041 = led.trapped(c)
    assert led.basis is not None
    snap_basis = None
    for t, oi, c, v in _fut_stream():
        pass
    # basis after the morning build sits inside the build zone
    led2 = Ledger(side="both")
    for t, oi, c, v in _fut_stream():
        led2.feed(t, oi, c)
        if t == "09:44":
            snap_basis = led2.basis
    assert 24125 <= snap_basis <= 24160, snap_basis
    side, pain = pain_at_1041
    assert side == "long" and pain > 20, (side, pain)


def test_unwind_classified_as_forced_not_short_buildup():
    led = Ledger(side="both")
    window = []
    for t, oi, c, v in _fut_stream():
        ev = led.feed(t, oi, c)
        if ev and "10:15" <= t <= "10:44":
            window.append(ev)
    forced = [e for e in window if e.kind == "forced_exit"]
    assert forced, "10:15-10:44 OI decline must classify as loss-side exits"
    assert all(e.trapped_side == "long" for e in forced)


def test_ce_covering_is_forced_exit_without_needing_basis_history():
    # sparse chain snapshots: 14:25 -> 14:38, OI -1.85M with price RISING.
    led = Ledger(side="short")
    s1 = FIX["chain_snapshots"][2]["strikes"]["24100CE"]   # 14:25
    s2 = FIX["chain_snapshots"][3]["strikes"]["24100CE"]   # 14:38
    led.feed("14:15", s1["oi"] - 300000, s1["ltp"] - 25)   # seed: tail of the build [I]
    led.feed("14:25", s1["oi"], s1["ltp"])                 # +300k written into ~105-117
    ev = led.feed("14:38", s2["oi"], s2["ltp"])
    assert ev.kind == "forced_exit" and ev.trapped_side == "short", ev
    assert ev.d_oi < -1_800_000


# ── Forcing detector: fires on the real cascade, silent on the fake ──────
def _run_detector():
    led = Ledger(side="both", min_flow=0)
    det = ForcingDetector(led)
    verdicts = {}
    for t, oi, c, v in _fut_stream():
        verdicts[t] = det.on_bar(t, oi, c, v)
    return verdicts


def test_fires_on_cascade_and_only_there():
    v = _run_detector()
    fired = [t for t, vd in v.items() if vd.state == "FIRE"]
    assert "14:36" in fired, f"must fire on the drain print; fired={fired}"
    assert all(t >= "14:33" for t in fired), f"no fire before ignition; fired={fired}"
    assert v["14:36"].direction == "long"


def test_silent_on_the_1106_flush():
    v = _run_detector()
    for t in ("11:06", "11:07", "11:08"):
        if t in v:
            assert v[t].state != "FIRE", f"{t}: flush must not fire (no drain)"


def test_arming_is_not_a_signal():
    v = _run_detector()
    arming = [t for t, vd in v.items() if vd.state == "ARMING"]
    for t in arming:
        assert v[t].direction is None, "ARMING must never carry a direction"


if __name__ == "__main__":
    import sys, traceback
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_")]
    bad = 0
    for f in fns:
        try:
            f(); print(f"PASS  {f.__name__}")
        except Exception:
            bad += 1; print(f"FAIL  {f.__name__}"); traceback.print_exc(limit=2)
    sys.exit(1 if bad else 0)
