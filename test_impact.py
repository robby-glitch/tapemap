"""Kyle's lambda off attributed volume: a synthetic slope is recovered (spec 2026-09-20 §G)."""
import impact
from test_ladder import R, T0


def _row(sec, bid, ask):
    return R(T0 + sec * 1000, 1000, (bid + ask) / 2, 65, [[bid, 65]], [[ask, 65]])


def test_fewer_than_120s_of_frames_is_a_sentence():
    im = impact.Impact(lot=65, tick=0.05)
    im.on_frame(_row(0, 100.00, 100.05), [])
    r = im.read()
    assert r["lambda"] is None and r["why"] == "fewer than 120 s of frames" and r["tag"] == "I"


def test_a_known_slope_is_recovered_in_lots_per_tick():
    """Every 130 units (2 lots) of net buying moves mid one tick: lambda = 0.5 ticks/lot -> 2 lots per tick."""
    im = impact.Impact(lot=65, tick=0.05)
    mid = 100.00
    im.on_frame(_row(0, mid, mid + 0.05), [])
    for s in range(1, 130):
        mid = round(mid + 0.05, 2)
        im.on_frame(_row(s, mid, mid + 0.05), [{"ltt": T0 + s * 1000, "side": 1, "p": mid, "q": 130, "hidden": False}])
    r = im.read()
    assert r["n"] >= 120 and abs(r["lots_per_tick"] - 2.0) < 1e-6 and r["why"] is None


def test_no_signed_volume_in_the_window_is_its_own_sentence():
    im = impact.Impact(lot=65, tick=0.05)
    for s in range(0, 130):
        im.on_frame(_row(s, 100.00, 100.05), [])
    assert im.read()["why"] == "no signed volume in the window"


def test_pct_ranks_lambda_against_the_session_so_far():
    im = impact.Impact(lot=65, tick=0.05)
    mid = 100.00
    im.on_frame(_row(0, mid, mid + 0.05), [])
    for s in range(1, 400):
        q = 130 if s < 250 else 65                      # the market thins: fewer lots per tick later
        mid = round(mid + 0.05, 2)
        im.on_frame(_row(s, mid, mid + 0.05), [{"ltt": T0 + s * 1000, "side": 1, "p": mid, "q": q, "hidden": False}])
    r = im.read()
    assert r["lots_per_tick"] < 2.0 and r["pct"] is not None and r["pct"] > 0.5
