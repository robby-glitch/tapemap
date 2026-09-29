"""xindex.py: determinism, no repaint, each state, the gating, the churn cap, the thin SENSEX, CAN'T CHECK on holes."""
import copy
import json
from datetime import datetime

import xindex as X

BASE = int(datetime.fromisoformat("2026-09-29T00:00:00+05:30").timestamp() * 1000)
WAIT = {"buy": {"state": "WAITING"}, "sell": {"state": "WAITING"}}


def at(hhmm):
    return BASE + (int(hhmm[:2]) * 60 + int(hhmm[3:])) * 60000


def leg(d, px0, px1, t0, t1, cls="rotation", agg=0, ab=False, back=0.0, ux="ok"):
    return {"dir": d, "px0": px0, "px1": px1, "pts": px1 - px0, "t0": at(t0), "t1": at(t1), "confirmed_at": at(t1) + 60000,
            "now": px1 - d * back, "back": back, "ux": {"state": ux, "why": "no book" if ux == "cant" else None},
            "who": {"class": cls, "aggressor": agg, "absorbed": ab, "roll": False, "expiring": False}}


def snap(asof, forming=None, legs=(), ruler=20.0, zone=WAIT, walls=None, au=("TREND", 1, None), ok=True):
    px = forming["now"] if forming else 100.0
    return {"ok": ok, "why": None if ok else "reader failed", "ruler": ruler, "legs": list(legs), "forming": forming,
            "auction": {"state": au[0], "d": au[1], "band": au[2]}, "t_last": asof - 60000, "px": px,
            "zone": zone, "zone_why": None if zone is not None else "no zone state", "walls": walls}


def up(asof, **kw):
    """An index pushing up: a 3-ruler forming leg, still at its extreme."""
    f = leg(1, 1000, 1060, "09:40", X.hm(asof - 60000), **kw)
    return f


def run(seq):
    st, outs = None, []
    for asof, snaps in seq:
        o, st = X.step(asof, snaps, st)
        outs.append(o)
    return outs, st


def trio(asof, n=None, b=None, s=None):
    d = lambda: snap(asof, up(asof))                                   # noqa: E731
    return {"NIFTY": n or d(), "BANKNIFTY": b or d(), "SENSEX": s or d()}


def test_sheet_holds_every_threshold():
    assert set(X.TH) == {k for k, _, _ in X.SHEET}
    assert all(why for _, _, why in X.SHEET)
    for k in ("MATCH", "TOL", "AWARD_ZONE", "AWARD", "MARGIN", "HOLD", "COOL", "CAP", "FREEZE", "THIN_IDX"):
        assert k in X.TH


def test_determinism_and_no_repaint():
    seq = [(at(t), trio(at(t))) for t in ("09:30", "09:33", "09:36", "09:39", "09:42")]
    a, _ = run(copy.deepcopy(seq))
    b, _ = run(copy.deepcopy(seq))
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
    # a prefix run is the full run's prefix
    c, st = run(copy.deepcopy(seq[:3]))
    assert json.dumps(c, sort_keys=True, default=str) == json.dumps(a[:3], sort_keys=True, default=str)
    # the same bar again, with different data, returns the stored output: nothing repaints
    again, _ = X.step(seq[2][0], trio(seq[2][0], n=snap(seq[2][0], ok=False)), st)
    assert json.dumps(again, sort_keys=True, default=str) == json.dumps(a[2], sort_keys=True, default=str)


def test_state_words_with_levels():
    t = at("10:00")
    armed = {"buy": {"state": "ARMED", "level": 990.0, "ref": 1010.0, "stop": 970.0}, "sell": {"state": "WAITING"}}
    o, _ = X.step(t, trio(t, n=snap(t, leg(-1, 1050, 995, "09:40", "09:59"), zone=armed)))
    r = o["idx"]["NIFTY"]
    assert r["word"] == "ban_sakta" and r["D"] == 1
    assert r["levels"]["start"] == 1010.0 and r["levels"]["kill"] == 970.0 and "trigger" in r["levels"]["confirm"]
    trade = {"buy": {"state": "IN_TRADE", "level": 990.0, "stop": 970.0}, "sell": {"state": "WAITING"}}
    o, _ = X.step(t, trio(t, n=snap(t, up(t), zone=trade)))
    assert o["idx"]["NIFTY"]["word"] == "chal_raha" and o["idx"]["NIFTY"]["levels"]["kill"] == 970.0
    o, _ = X.step(t, trio(t))
    r = o["idx"]["NIFTY"]
    assert r["word"] == "chal_raha" and r["levels"]["start"] == 1000 and r["levels"]["kill"] == 1060 - 20.0
    spent = leg(1, 1000, 1060, "09:40", "09:55", back=15.0)            # 3 rulers, 0.75 ruler back from its extreme
    o, _ = X.step(t, trio(t, n=snap(t, spent)))
    assert o["idx"]["NIFTY"]["word"] == "ho_gaya" and o["idx"]["NIFTY"]["word_dir"] == 1
    rng = snap(t, leg(1, 1000, 1025, "09:50", "09:59"), au=("RANGE", 0, [990.0, 1030.0]))
    o, _ = X.step(t, trio(t, n=rng))
    r = o["idx"]["NIFTY"]
    assert r["word"] == "ban_sakta" and r["levels"]["up"] == 1050.0 and r["levels"]["down"] == 970.0


def test_word_needs_an_event_or_two_bars():
    t1, t2, t3 = at("10:00"), at("10:03"), at("10:06")
    o1, st = X.step(t1, trio(t1))
    assert o1["idx"]["NIFTY"]["word"] == "chal_raha"
    spent = lambda t: snap(t, leg(1, 1000, 1060, "09:40", "09:55", back=15.0))   # noqa: E731
    o2, st = X.step(t2, trio(t2, n=spent(t2)), st)
    assert o2["idx"]["NIFTY"]["word"] == "chal_raha"                  # one bar is a wiggle
    o3, st = X.step(t3, trio(t3, n=spent(t3)), st)
    assert o3["idx"]["NIFTY"]["word"] == "ho_gaya"                    # two bars in a row is a change


def zone_buy(t, state="ARMED"):
    return {"buy": {"state": state, "level": 990.0, "ref": 1010.0, "stop": 970.0}, "sell": {"state": "WAITING"}}


def test_gating_zone_plus_two_or_four_without():
    t = at("10:00")
    # NIFTY: her zone BUY armed + the push down absorbed + BANKNIFTY armed the same side = 3 lines with the zone
    dn_abs = leg(-1, 1050, 995, "09:40", "09:59", agg=-1, ab=True)
    b = snap(t, leg(-1, 2050, 1995, "09:40", "09:59"), zone=zone_buy(t))
    o, _ = X.step(t, {"NIFTY": snap(t, dn_abs, zone=zone_buy(t)), "BANKNIFTY": b, "SENSEX": snap(t, up(t))})
    assert o["idx"]["NIFTY"]["n_for"] >= 3 and o["idx"]["NIFTY"]["lines"]["zone"]["vote"] == 1
    assert o["look"]["idx"] == "NIFTY" and "of" in o["look"]["line"] and "%" not in o["look"]["line"]
    # no zone: flow + WHO + sync = 3 -> not enough
    n3 = snap(t, up(t, cls="new_longs", agg=1))
    o, _ = X.step(t, trio(t, n=n3))
    assert o["idx"]["NIFTY"]["n_for"] == 3 and o["look"]["idx"] is None
    # ... add the walls = 4 -> awarded
    n4 = snap(t, up(t, cls="new_longs", agg=1), walls={"vote": 1, "why": "PE likh rahe 1,000 (+900 lots/15m)"})
    o, _ = X.step(t, trio(t, n=n4))
    assert o["idx"]["NIFTY"]["n_for"] == 4 and o["look"]["idx"] == "NIFTY"
    # 2 for (flow, WHO) against 2 (CE lid, peers the other way) -> the margin fails
    t2 = at("10:03")
    bad = snap(t2, up(t2, cls="new_longs", agg=1), walls={"vote": -1, "why": "CE likh rahe"})
    peers = {"BANKNIFTY": snap(t2, leg(-1, 2060, 2000, "09:50", "10:02")), "SENSEX": snap(t2, leg(-1, 60, 0, "09:50", "10:02"))}
    o, _ = X.step(t2, {"NIFTY": bad, **peers})
    r = o["idx"]["NIFTY"]
    assert r["n_against"] >= 2 and o["look"]["idx"] != "NIFTY"


def good(t):
    return snap(t, up(t, cls="new_longs", agg=1), walls={"vote": 1, "why": "PE likh rahe"})


def dull(t):
    return snap(t, leg(1, 1000, 1030, "09:40", X.hm(t - 60000), back=12.0))


def test_cooldown_and_the_cap():
    st, outs = None, []
    t = at("09:30")
    for k in range(60):                     # alternate a qualifying and a dull NIFTY every bar
        n = good(t) if k % 2 == 0 else dull(t)
        o, st = X.step(t, trio(t, n=n), st)
        outs.append(o)
        t += 3 * 60000
    looks = [o["look"]["idx"] for o in outs]
    # an award, a release, then no new award inside COOL bars
    for k in range(1, len(looks) - 2):
        if looks[k - 1] and not looks[k]:
            assert not any(looks[k + 1:k + 1 + int(X.TH["COOL"])])
    assert st["flips6"] == 0
    assert st["changes"] <= int(X.TH["CAP"]) and st["capped"]
    assert "cap" in outs[-1]["look"]["line"]


def test_thin_sensex():
    t = at("10:00")
    o, _ = X.step(t, trio(t, s=snap(t, up(t, cls="new_longs", agg=1))))
    r = o["idx"]["SENSEX"]
    assert r["lines"]["flow"]["vote"] is None and "patla" in r["lines"]["flow"]["why"]
    assert r["lines"]["who"]["vote"] is None and "patla" in r["lines"]["who"]["why"]
    # SENSEX with everything but her zone never reaches the bar (4 of 4 checkable lines are impossible without it)
    s = snap(t, up(t, cls="new_longs", agg=1), walls={"vote": 1, "why": "PE likh rahe"})
    o, _ = X.step(t, {"NIFTY": dull(t), "BANKNIFTY": dull(t), "SENSEX": s})
    assert o["look"]["idx"] != "SENSEX"
    # SENSEX alone going the other way does not break NIFTY/BANKNIFTY sync
    o, _ = X.step(t, trio(t, s=snap(t, leg(-1, 60, 0, "09:50", "09:59"))))
    assert o["sync"]["state"] in ("SAATH", "KAMZOR") and "patla" in o["sync"]["chip"]


def test_cant_check_on_holes_freeze_and_early():
    t = at("10:00")
    stale = snap(t, up(t))
    stale["t_last"] = t - 10 * 60000
    o, _ = X.step(t, trio(t, n=stale))
    r = o["idx"]["NIFTY"]
    assert not r["ok"] and r["word"] == "cant" and all(x["vote"] is None and x["why"] for x in r["lines"].values())
    assert o["look"]["idx"] != "NIFTY"
    o, _ = X.step(t, trio(t, n=snap(t, up(t), zone=None)))
    assert o["idx"]["NIFTY"]["lines"]["zone"]["vote"] is None and "zone" in o["idx"]["NIFTY"]["lines"]["zone"]["why"]
    o, _ = X.step(t, trio(t, n=snap(t, up(t, ux="cant"))))
    assert o["idx"]["NIFTY"]["lines"]["flow"]["vote"] is None
    late = at("15:18")
    o, _ = X.step(late, trio(late, n=good(late)))
    assert o["look"]["idx"] is None and "15:15" in o["look"]["line"]
    assert all(r["word"] == "cant" for r in o["idx"].values()) and o["sync"]["state"] == "CANT"
    early = at("09:27")
    o, _ = X.step(early, trio(early, n=good(early)))
    assert o["look"]["idx"] is None


def test_extremes_confirmed_and_divergent():
    t = at("11:00")
    def hi(base, new):
        prior = [leg(1, base - 50, base, "10:00", "10:10"), leg(-1, base, base - 40, "10:10", "10:20")]
        return snap(t, leg(1, base - 40, new, "10:20", "10:58"), legs=prior)
    ev = X.extremes({"NIFTY": hi(1000, 1030), "BANKNIFTY": hi(2000, 2030), "SENSEX": hi(3000, 3030)},
                    {"NIFTY": True, "BANKNIFTY": True, "SENSEX": True}, t, 1)
    assert ev["verdict"] == "CONFIRMED" and ev["chip"].startswith("Teeno")
    ev = X.extremes({"NIFTY": hi(1000, 1030), "BANKNIFTY": hi(2000, 1980), "SENSEX": hi(3000, 3030)},
                    {"NIFTY": True, "BANKNIFTY": True, "SENSEX": True}, t, 1)
    assert ev["verdict"] == "DIVERGENT" and ev["ends"] == {"BANKNIFTY": 2000} and "BANKNIFTY ne nahi" in ev["chip"]
    # the thin SENSEX failing alone is a witness, not a divergence
    ev = X.extremes({"NIFTY": hi(1000, 1030), "BANKNIFTY": hi(2000, 2030), "SENSEX": hi(3000, 2980)},
                    {"NIFTY": True, "BANKNIFTY": True, "SENSEX": True}, t, 1)
    assert ev["verdict"] == "CONFIRMED" and "patla" in ev["chip"]


def test_walls_vote_and_noise():
    def row(ce, pe):
        return {"expiry": "2026-10-06", "strikes": [{"k": k, "ce": {"oi": ce.get(k, 0)}, "pe": {"oi": pe.get(k, 0)}}
                                                    for k in range(900, 1101, 50)]}
    then = row({}, {})
    now = row({1050: 650}, {950: 65000})
    w = X.walls(now, then, 1000.0, 40.0, 65)
    assert w["vote"] == 1 and "PE likh rahe" in w["why"] and "%" not in w["why"]
    w = X.walls(row({1050: 65000}, {950: 650}), then, 1000.0, 40.0, 65)
    assert w["vote"] == -1
    w = X.walls(row({1050: 65000}, {950: 65000}), then, 1000.0, 40.0, 65)
    assert w["vote"] == 0 and "dono" in w["why"]
    assert X.walls(None, then, 1000.0, 40.0, 65) is None


def test_audit_is_clean_on_a_sequence():
    seq = [(at(t), trio(at(t), n=good(at(t)))) for t in ("09:30", "09:33", "09:36", "09:39")]
    outs, _ = run(seq)
    assert all(X.audit(o) == [] for o in outs)
