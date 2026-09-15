"""book.py -- the risk core: marks honest, margin conservative, attribution
refuses partial answers, distance-to-forced computed from declared stress."""

import book


def _leg(**kw):
    d = dict(strike=25000.0, right="CE", side="SELL", qty=130,
             entry_px=100.0, entry_ts="10:00:00", iv0=0.14, delta0=0.5,
             vega0=10.0)
    d.update(kw)
    return book.PaperLeg(**d)


def _q(bid=99.0, ask=101.0, ltp=100.0, delta=0.5, gamma=0.001, iv=0.14):
    return {"bid": bid, "ask": ask, "ltp": ltp, "delta": delta,
            "gamma": gamma, "iv": iv}


def test_open_close_realized_arithmetic():
    b = book.Book(1_000_000)
    p = b.open("NIFTY", "SELL_PIN", 2, [_leg()], "10:00:00", 25000.0,
               "buyers", "drag", "PIN")
    r = b.close(p, {0: (80.0, "taker")}, "11:00:00")
    assert r == 2600.0                      # (100-80) x 130, short side
    assert b.realized_total == 2600.0
    assert p.state == "CLOSED" and p.legs[0].exit_px == 80.0


def test_mark_prefers_mid_and_states_absence():
    assert book.mark_px(_q()) == (100.0, "mid")
    assert book.mark_px({"ltp": 55.0}) == (55.0, "ltp")
    px, why = book.mark_px({})
    assert px is None and "no quote" in why


def test_attribution_decomposes_and_sums():
    b = book.Book(1_000_000)
    p = b.open("NIFTY", "BUY_CASCADE", 2,
               [_leg(side="BUY", entry_px=100.0)], "10:00", 25000.0,
               "writers", "drain", "CASCADE")
    m = b.mark_position(p, {(25000.0, "CE"): _q(bid=119.0, ask=121.0,
                                                iv=0.15)}, 25100.0)
    a = m["attribution"]
    assert a is not None and a["tag"] == "I"
    assert a["delta"] == round(0.5 * 100.0 * 130, 2)          # 6500
    assert a["vega"] == round(10.0 * 0.01 * 130, 2)           # 13
    assert round(a["delta"] + a["vega"] + a["theta_gamma_resid"], 2) \
        == m["unrealized"]


def test_attribution_refuses_when_context_missing():
    b = book.Book(1_000_000)
    p = b.open("NIFTY", "X", 2, [_leg(side="BUY", delta0=None)],
               "10:00", 25000.0, "", "", "")
    m = b.mark_position(p, {(25000.0, "CE"): _q()}, 25050.0)
    assert m["attribution"] is None
    assert "refusing" in m["attribution_why"]


def test_margin_short_uses_naked_floor_and_long_uses_premium():
    b = book.Book(1_000_000)
    short = b.open("NIFTY", "S", 2, [_leg()], "t", 25000.0, "", "", "")
    m, note = b.margin_position(short, 25000.0, 65)
    assert m == 0.11 * 25000.0 * 65 * 2                # per lot x 2 lots
    assert "naked" in note
    lng = b.open("NIFTY", "L", 2, [_leg(side="BUY")], "t", 25000.0,
                 "", "", "")
    m2, note2 = b.margin_position(lng, 25000.0, 65)
    assert m2 == 100.0 * 130 and "[M]" in note2


def test_risk_reports_forced_ratio_and_honest_absence():
    b = book.Book(1_000_000)
    assert b.risk({})["forced_ratio"] is None          # nothing to stress
    b.open("NIFTY", "S", 2, [_leg()], "t", 25000.0, "", "", "")
    r = b.risk({"NIFTY": {"spot": 25000.0, "lot_size": 65,
                          "expected_move": 150.0,
                          "mark": {"net_delta": -65.0, "net_gamma": 0.1}}})
    assert r["margin_used"] == round(0.11 * 25000 * 65 * 2, 0)
    stressed = abs(-65.0) * 150.0 + 0.5 * 0.1 * 150.0 ** 2
    assert r["stressed_need"] == round(r["margin_used"] * 2.0 + stressed, 0)
    assert r["forced_ratio"] == round(1_000_000 / r["stressed_need"], 2)
    assert r["tag"] == "I"


def test_round_trip_persistence():
    b = book.Book(500_000)
    p = b.open("SENSEX", "S", 2, [_leg()], "t", 81000.0, "who", "why", "PIN")
    p.day = "2026-08-24"
    b2 = book.Book.from_dict(b.to_dict())
    assert b2.capital == 500_000
    assert b2.positions[0].pid == p.pid
    assert b2.positions[0].legs[0].entry_px == 100.0
    assert b2.positions[0].day == "2026-08-24"
    # ids keep advancing, never collide
    p2 = b2.open("NIFTY", "S", 2, [_leg()], "t", 25000.0, "", "", "")
    assert p2.pid != p.pid
