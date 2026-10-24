"""VALIDATE rev 3 (docs/hold/VALIDATE-PREREG-rev3.md): every changed vote at its boundaries, the could-not-check paths and
the #10 spent pop from the 22 Oct 13:00 SENSEX numbers -- the face's engine.js run in node (test/validate3_harness.cjs).
Skipped when node is not installed."""
import json
import os
import shutil
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(HERE, "test", "validate3_harness.cjs")
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def run(*calls):
    r = subprocess.run(["node", HARNESS], input=json.dumps(list(calls)), capture_output=True, text=True, encoding="utf-8",
                       timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    for o in out:
        assert o["ok"], o.get("err")
    return [o["out"] for o in out]


def v(fn, *args):
    return {"fn": fn, "args": list(args)}


# ---- #2 DAY / TREND ------------------------------------------------------------------------------------------------

def test_day_vote_table():
    got = run(
        v("dayVote", "TREND", 1, 1.5, "buy", 1), v("dayVote", "TREND", -1, 0.1, "buy", 1),
        v("dayVote", "TREND", -1, 2.0, "sell", -1),                       # TREND her way stays WITH whatever u reads
        v("dayVote", "RANGE", 0, 0.90, "buy", 1), v("dayVote", "RANGE", 0, 0.8999, "buy", 1),
        v("dayVote", "RANGE", 0, 0.90, "sell", 1), v("dayVote", "RANGE", 0, -0.90, "buy", 1),
        v("dayVote", "RANGE", 0, -0.8999, "buy", -1), v("dayVote", "RANGE", 0, 0.5, "sell", -1),
        v("dayVote", "RANGE", 0, None, "buy", 1), v("dayVote", "RANGE", 0, None, "sell", 1),
        v("dayVote", "OTHER", 0, 1.5, "buy", 1), v("dayVote", "OTHER", 0, -1.5, "sell", 1))
    assert got == ["WITH", "AGAINST", "WITH",
                   "AGAINST", "NEITHER", "AGAINST", "WITH",
                   "NEITHER", "WITH", "NEITHER", "WITH", "NEITHER", "NEITHER"]


def test_weekdays_for_the_expected_move():
    assert run(v("weekdays", "2026-10-23", "2026-10-27"), v("weekdays", "2026-10-22", "2026-10-22"),
               v("weekdays", "2026-10-24", "2026-10-25"), v("weekdays", "2026-10-27", "2026-10-23")) == [3, 1, None, None]


# ---- #4 / #5 walls: DEFENDING vs ROLLING ----------------------------------------------------------------------------

def test_wall_vote_rolling_is_neither_and_unchecked_roll_keeps_the_base():
    got = run(v("wallVote", "BUILDING", True, False, False), v("wallVote", "BUILDING", False, False, False),
              v("wallVote", "BUILDING", None, False, False), v("wallVote", "UNWINDING", True, False, False),
              v("wallVote", "UNWINDING", False, False, False), v("wallVote", "STALLED", False, False, False),
              v("wallVote", "UNWINDING", True, True, True), v("wallVote", "UNWINDING", False, True, True),
              v("wallVote", "BUILDING", False, True, True), v("wallVote", "BUILDING", False, True, False),
              v("wallVote", "BUILDING", True, True, True), v("wallVote", None, False, False, False))
    assert got == ["NEITHER", "WITH", "WITH", "NEITHER", "AGAINST", "NEITHER",
                   "NEITHER", "WITH", "AGAINST", "NEITHER", "NEITHER", "NEITHER"]


# ---- #6 ORDER FLOW --------------------------------------------------------------------------------------------------

def test_effort_vote_boundaries_and_failed_mirrors():
    H, L = (lambda x: {"at": "HIGH", "x": x}), (lambda x: {"at": "LOW", "x": x})
    got = run(v("effortVote", H(2.0), 1), v("effortVote", H(1.99), 1), v("effortVote", H(2.0), -1),
              v("effortVote", L(0.5), -1), v("effortVote", L(0.51), -1), v("effortVote", L(0.5), 1),
              v("effortVote", L(2.5), -1), v("effortVote", H(0.3), 1),          # the failed mirrors: no vote
              v("effortVote", {"at": None, "x": 3.0}, 1), v("effortVote", {"at": "HIGH", "x": None}, 1), v("effortVote", None, 1))
    assert got == ["AGAINST", None, "WITH", "WITH", None, "AGAINST", None, None, None, None, None]


def test_quadrant_vote_new_money_covering_flat_roll():
    q = lambda doi, px, roll=False: {"doi": doi, "oi": 1_000_000, "px10": px, "B": 10, "roll": roll}  # noqa: E731
    got = run(v("quadVote", q(5000, 30), 1), v("quadVote", q(5000, 30), -1), v("quadVote", q(5000, -30), -1),
              v("quadVote", q(-5000, 30), 1), v("quadVote", q(-5000, -30), -1),
              v("quadVote", q(1499, 30), 1), v("quadVote", q(1500, 30), 1),       # 0.15 % of OI = flat below
              v("quadVote", q(5000, 9.9), 1), v("quadVote", q(-5000, 30, True), 1), v("quadVote", q(5000, 30, True), 1),
              v("quadVote", None, 1))
    assert [g["st"] for g in got] == ["WITH", "AGAINST", "WITH", "NEITHER", "NEITHER", "NEITHER", "WITH",
                                      "NEITHER", "CNC", "WITH", "CNC"]
    assert got[3]["word"] == "short covering" and got[4]["word"] == "long liquidation" and got[5]["word"] == "fut OI flat"


def test_flow_vote_effort_first_and_could_not_check_paths():
    W, A, N, C = ({"st": s} for s in ("WITH", "AGAINST", "NEITHER", "CNC"))
    got = run(v("flowVote", "AGAINST", False, W), v("flowVote", None, False, W), v("flowVote", None, True, A),
              v("flowVote", None, True, C), v("flowVote", None, False, C), v("flowVote", None, True, N))
    assert got == ["AGAINST", "WITH", "AGAINST", "CNC", "NEITHER", "NEITHER"]


# ---- #10 PAYING: the spent pop --------------------------------------------------------------------------------------

def test_pay_vote_spent_pop_and_the_base():
    got = run(v("payVote", ["STALLED", "UNWINDING"], True), v("payVote", ["STALLED", "UNWINDING"], False),
              v("payVote", ["BUILDING", "BUILDING"], False), v("payVote", ["BUILDING", "BUILDING"], True),
              v("payVote", ["BUILDING", "STALLED"], False), v("payVote", [], True))
    assert got == ["AGAINST", "WITH", "AGAINST", "AGAINST", "NEITHER", "NEITHER"]


def _snap(idx, spots, T, step=100, fights=()):
    """A snap-like object for freshOf / tapeOf: chain rows every 60 s ending at T."""
    n = len(spots)
    return {"idx": idx, "x": {"t": [T - 60 * (n - 1 - k) for k in range(n)], "spot": spots}, "tf": T, "i": n - 1,
            "spot": spots[-1], "step": step, "thin": idx == "SENSEX", "fights": list(fights)}


# the 22 Oct 13:00 SENSEX numbers (the replay's own read): the 30-min high 73,575.1 spot at 12:55, spot 73,455.2 at 13:00,
# payers CE 74000 STALLED / CE 73500 UNWINDING (35.4 % off its 12:49 peak), DECODE 12:55 exhaust {d +1, bar 12:50}
T1300, T1255 = 13 * 3600, 12 * 3600 + 55 * 60
EXH = {"t": "12:55", "exhaust": {"d": 1, "bar": "12:50", "close": "12:55", "ratio": -1.676},
       "effort": {"at": None, "x": None, "t": None, "why": "not read — SENSEX futures are too thin"}}
PATH = [73300.0] * 20 + [73450.0, 73500.0, 73540.0, 73560.0, 73575.1, 73560.0, 73520.0, 73490.0, 73470.0, 73460.0, 73455.2]


def test_spent_pop_22oct_1300_is_not_fresh_so_the_base_with_stands():
    fr, = run(v("freshOf", _snap("SENSEX", PATH, T1300), 1))
    assert fr["fresh"] is False and fr["ext"] == 73575.1 and fr["at"] == T1300 - 6 * 60   # 120 pts off a 6-min-old high
    assert run(v("payVote", ["STALLED", "UNWINDING"], False)) == ["WITH"]


def test_spent_pop_at_the_fresh_high_fires_where_the_tape_is_read_and_is_unread_on_sensex():
    at_high = PATH[:25]                                                    # 12:55: spot at the 30-min high it just set
    dq = {"c": T1255 - 300, "b": EXH}
    nifty_fr, nifty_tp, sx_tp = run(v("freshOf", _snap("NIFTY", at_high, T1255), 1),
                                    v("tapeOf", _snap("NIFTY", at_high, T1255 + 60), 1, dq),
                                    v("tapeOf", _snap("SENSEX", at_high, T1255 + 60), 1, dq))
    assert nifty_fr["fresh"] is True
    assert nifty_tp == {"names": ["EXHAUST 12:50"], "unread": None}       # NIFTY-like: the pop is spent -> AGAINST
    assert run(v("payVote", ["STALLED", "UNWINDING"], bool(nifty_tp["names"]))) == ["AGAINST"]
    assert sx_tp == {"names": [], "unread": "SENSEX tape patla"}           # SENSEX: could not check, the base stands


def test_tape_windows_15_min_and_a_longs_expensive_high_only():
    T = 11 * 3600
    blk = lambda e=None, ex=None: {"c": T - 300, "b": {"t": "10:55", "effort": e or {}, "exhaust": ex}}  # noqa: E731
    got = run(v("tapeOf", _snap("NIFTY", [1.0], T), 1, blk({"at": "HIGH", "x": 2.0, "t": "10:45"})),
              v("tapeOf", _snap("NIFTY", [1.0], T), 1, blk({"at": "HIGH", "x": 2.0, "t": "10:44"})),
              v("tapeOf", _snap("NIFTY", [1.0], T), 1, blk({"at": "HIGH", "x": 1.99, "t": "10:59"})),
              v("tapeOf", _snap("NIFTY", [1.0], T), -1, blk({"at": "LOW", "x": 2.5, "t": "10:59"})),
              v("tapeOf", _snap("NIFTY", [1.0], T), -1, blk(ex={"d": 1, "bar": "10:50", "close": "10:55"})),
              v("tapeOf", _snap("NIFTY", [1.0], T, fights=[{"side": 1, "res": "ABSORBED", "t": T - 900}]), 1, {"why": "DECODE not loaded"}),
              v("tapeOf", _snap("NIFTY", [1.0], T), 1, {"why": "DECODE stale (10:40)"}))
    assert got[0]["names"] == ["effort 2.0×"] and got[1]["names"] == [] and got[2]["names"] == []
    assert got[3]["names"] == []                                           # >= 2x at a LOW is noise: never a tape read
    assert got[4]["names"] == []                                           # EXHAUST on the other leg
    assert got[5] == {"names": ["ABSORB 10:45"], "unread": None}
    assert got[6] == {"names": [], "unread": "DECODE stale (10:40)"}


# ---- the whole word on a synthetic day ------------------------------------------------------------------------------

def _payload():
    """A tiny NIFTY-shaped day (all three indices the same): spot 22,600 -> 22,700 by 11:00, the 09:20 ATM straddle 120
    (expiry Tue 27 Oct from Fri 23 Oct: N = 3, 1σ = 120 / 0.8 / √3 = 86.6), flat futures OI, a VPIN-less tape."""
    t0, t1 = 9 * 3600 + 17 * 60, 11 * 3600
    ts = list(range(t0, t1 + 1, 60))
    ks = [22450 + 50 * k for k in range(8)]
    spot = [22600 + 100 * max(0, (t - 9 * 3600 - 20 * 60)) / (t1 - 9 * 3600 - 20 * 60) for t in ts]
    leg = lambda: {"oi": [[1000 + 10 * j for j in range(8)] for _ in ts], "ltp": [[60 * 20] * 8 for _ in ts],  # noqa: E731
                   "d": [[50] * 8 for _ in ts], "avg": [[60] * 8 for _ in ts]}
    bars = [[t, round((22620 + 100 * max(0, (t - 9 * 3600 - 20 * 60)) / (t1 - 9 * 3600 - 20 * 60)) * 10), 10, 6]
            for t in range(t0, t1 + 1, 10)]
    x = {"t": ts, "spot": spot, "atm": [round(s / 50) * 50 for s in spot], "ks": ks, "ce": leg(), "pe": leg(), "bars": bars,
         "futoi": [[t - t % 60, 1_000_000] for t in ts], "expiry": "2026-10-27", "futExpiry": "2026-10-27", "step": 50,
         "lot": 65, "slowEvery": 1}
    return {"ok": True, "day": "2026-10-23", "idx": {i: x for i in ("NIFTY", "BANKNIFTY", "SENSEX")}, "vpin": []}


def test_validate_rev3_counts_nine_or_eight_prints_vpin_and_says_no_on_a_spent_chop_breakout():
    dec = {"t": "10:55", "onesided": {"type": "CHOP", "dom": 60, "flips": 3, "crosses": 5},
           "effort": {"at": "HIGH", "x": 2.3, "t": "10:54"}, "exhaust": None}
    P, T = _payload(), 11 * 3600
    buy, sell, sx, rev = run({"fn": "validate", "payload": P, "decode": {"NIFTY": dec}, "call": ["NIFTY", 22700, "CE", "BUY", None, T, T]},
                             {"fn": "validate", "payload": P, "decode": {"NIFTY": dec}, "call": ["NIFTY", 22700, "PE", "SELL", None, T, T]},
                             {"fn": "validate", "payload": P, "decode": {}, "call": ["SENSEX", 22700, "CE", "BUY", None, T, T]},
                             {"fn": "REV"})
    st = lambda r, n: next(c for c in r["checks"] if c["name"] == n)  # noqa: E731
    assert buy["rev"] == rev and rev.startswith("3 (VALIDATE-PREREG-rev3 a4186306")
    assert buy["counts"]["of"] == 9 and sell["counts"]["of"] == 8
    assert st(buy, "VPIN")["st"] == "PR" and st(sell, "VPIN")["st"] == "PR"
    assert st(buy, "DAY / TREND")["st"] == "AGAINST" and "115%" in st(buy, "DAY / TREND")["cell"]    # 100 / 86.6 her way
    assert st(sell, "DAY / TREND")["st"] == "AGAINST"                     # SELL PE = long the extension
    assert st(buy, "ORDER FLOW")["st"] == "AGAINST" and st(buy, "ORDER FLOW")["cell"] == "high 2.3× mehenga"
    assert buy["word"] == "NO" and sell["word"] == "NO"
    assert st(sx, "ORDER FLOW")["st"] == "CNC" and st(sx, "DAY / TREND")["cell"].endswith("chal chuka")
    early, = run({"fn": "validate", "payload": P, "decode": {}, "call": ["NIFTY", 22600, "CE", "BUY", None, 9 * 3600 + 18 * 60, 11 * 3600]})
    assert "EM ?" in st(early, "DAY / TREND")["cell"]                    # causal: the 09:20 row is not read at 09:18
