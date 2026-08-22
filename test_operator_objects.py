"""test_operator_objects.py -- trapped_inventory, born against the Aug-19 fixture.

`forcing.py` (the S2 checklist -- FUEL+IGNITION arm a window, DRAIN inside it
FIREs) was deleted 2026-08-22: superseded by `fuse.py` + `regime.py`, which
turn the same three conditions into a gear (`fuse.verdict()` ->
`regime.decide()`), replay against any session and are wired into the live
server. Its coverage here (the cascade-fires / 1106-flush-is-silent / arming-
carries-no-direction tests) went with it; see `test_fuse.py` and
`test_regime.py` for the equivalent behaviour on the surviving modules.

The fixture's known answers, established live during the session:
  * morning futures build concentrated 09:15-09:44 at ~24135-24160
  * by ~10:40 those longs were underwater; 10:15-10:44 OI fell into a falling
    price -- loss-side exits, not shorting (the aggregate-OI lie of the day)
  * CE covering 14:25->14:38: OI -1.85M while ltp rose 117.4->130.8 -- forced
Run: python test_operator_objects.py   (or pytest)
"""
import json
from pathlib import Path

from trapped_inventory import Ledger

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
