"""trader.py -- the paper desk: both sides fire, every refusal is logged,
risk rules bind, the book survives a restart, and nothing writes off-hours."""

import json
from datetime import datetime
from types import SimpleNamespace

import trader as trader_mod


IN_HOURS = datetime(2026, 8, 24, 10, 30)      # a Monday, mid-session
LATE = datetime(2026, 8, 24, 15, 20)          # past square-off
OFF_HOURS = datetime(2026, 8, 22, 10, 30)     # a Saturday


def _doc(spot=25000.0, prem=100.0, bid_off=-1.0, ask_off=1.0):
    strikes = []
    for k in range(24600, 25500, 100):
        leg = {"ltp": prem, "bid": prem + bid_off, "ask": prem + ask_off,
               "oi": 1000.0, "oi_chg": 10.0, "vol": 500.0,
               "iv": 0.14, "delta": 0.5, "gamma": 0.0005}
        pe = dict(leg, delta=-0.5)
        strikes.append({"k": float(k), "ce": dict(leg), "pe": pe})
    return {"ok": True, "ts": "10:30:00", "spot": spot, "atm": 25000,
            "expiry": "2026-08-27", "strikes": strikes, "metrics": {}}


def _view(gear="UNKNOWN", conv="NONE", bias="UNKNOWN"):
    return SimpleNamespace(gear=gear, conviction=conv, bias=bias,
                           worst_leg=None)


def _t(tmp_path):
    return trader_mod.Trader(state_path=str(tmp_path / "state.json"),
                             trades_path=str(tmp_path / "trades.jsonl"),
                             decisions_path=str(tmp_path / "dec.jsonl"))


def test_pin_posts_offers_beyond_the_expected_move(tmp_path):
    t = _t(tmp_path)
    t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=IN_HOURS)
    quotes = t.quoter.resting
    assert len(quotes) == 2                      # one wing each side
    rights = {q.right for q in quotes}
    assert rights == {"CE", "PE"} and all(q.side == "SELL" for q in quotes)
    # posted beyond the expected move (ATM straddle = 200 pts here)
    ce = next(q for q in quotes if q.right == "CE")
    pe = next(q for q in quotes if q.right == "PE")
    assert ce.strike >= 25200.0 and pe.strike <= 24800.0
    kinds = [r["kind"] for r in t.decisions]
    assert kinds.count("post") == 2


def test_a_maker_fill_opens_a_position_with_the_rule9_sentence(tmp_path):
    t = _t(tmp_path)
    t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=IN_HOURS)
    ce = next(q for q in t.quoter.resting if q.right == "CE")
    # the bid rallies up to our offer: we get lifted
    t.on_chain("NIFTY", _doc(prem=ce.px, bid_off=0.0, ask_off=2.0),
               _view("PIN"), {}, {}, now=IN_HOURS)
    opens = t.book.open_positions()
    assert opens, "the crossed offer must have become a position"
    assert all(p.forced_who for p in opens)      # rule 9 rides every entry
    assert all(l.mode == "maker" for p in opens for l in p.legs)


def test_cascade_takes_the_short_covering_scalp_and_exits_when_it_dies(tmp_path):
    t = _t(tmp_path)
    cr = {"trapped_side": "ce", "worst_leg": "25000CE", "drain": True,
          "drain_rank": 0.95}
    t.on_chain("NIFTY", _doc(), _view("CASCADE", "FORCED", "BULL"), cr, {},
               now=IN_HOURS)
    opens = t.book.open_positions()
    assert len(opens) == 1
    p = opens[0]
    assert p.strategy == "BUY_CASCADE" and p.legs[0].side == "BUY"
    assert p.legs[0].right == "CE" and p.legs[0].mode == "taker"
    assert "trapped ce writers" in p.forced_who
    # cascade ends -> the scalp closes itself, but only after the cool-off.
    # UPDATED 2026-08-24: this test asserted a close on the FIRST non-CASCADE
    # snapshot, which is why the flicker survived to the live morning -- the
    # old contract was the defect. `drain` is top-decile, so one quiet tick
    # proves nothing; CASCADE_COOL of them do.
    for _ in range(trader_mod.CASCADE_COOL):
        t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=IN_HOURS)
    assert t.book.open_positions() == []
    assert any(r["kind"] == "exit" and "cascade over" in r["detail"]
               for r in t.decisions)


def test_long_scalp_takes_its_target(tmp_path):
    t = _t(tmp_path)
    cr = {"trapped_side": "pe", "drain": True, "drain_rank": 0.9}
    t.on_chain("NIFTY", _doc(prem=100.0),
               _view("CASCADE", "FORCED", "BEAR"), cr, {}, now=IN_HOURS)
    p = t.book.open_positions()[0]
    entry = p.legs[0].entry_px                   # bought at the ask, 101
    # premium runs +30%: mark crosses the +25% target -> closed at the bid,
    # and the same-tick cooldown must stop it re-buying the still-live
    # trigger at the worse price
    up = entry * 1.30
    t.on_chain("NIFTY", _doc(prem=up),
               _view("CASCADE", "FORCED", "BEAR"), cr, {}, now=IN_HOURS)
    assert t.book.open_positions() == []
    assert t.book.realized_total > 0
    assert any("no same-tick re-entry" in r["detail"] for r in t.decisions
               if r["kind"] == "refusal")


def test_dir_after_grab_fires_on_a_named_run(tmp_path):
    t = _t(tmp_path)
    wm = {"seq_fired": [{"to": "RUN", "level": "PDL", "px": 24900.0,
                         "target": {"kind": "ROUND", "px": 24800.0}}],
          "sequence": {}}
    t.on_chain("NIFTY", _doc(), _view("CASCADE"), {}, wm, now=IN_HOURS)
    opens = t.book.open_positions()
    assert len(opens) == 1
    p = opens[0]
    assert p.strategy == "DIR_AFTER_GRAB"
    assert p.legs[0].right == "PE"               # target below spot -> puts
    assert "stops beyond PDL" in p.forced_who


def test_risk_rules_refuse_and_the_refusal_is_logged(tmp_path):
    t = _t(tmp_path)
    cr = {"trapped_side": "ce", "drain": True, "drain_rank": 0.9}
    wm = {"seq_fired": [{"to": "RUN", "level": "PDH", "px": 25100.0,
                         "target": {"kind": "ROUND", "px": 25400.0}}],
          "sequence": {}}
    # tick 1 fills BUY_CASCADE + DIR_AFTER_GRAB (2 open = MAX_OPEN)
    t.on_chain("NIFTY", _doc(), _view("CASCADE", "FORCED", "BULL"), cr, wm,
               now=IN_HOURS)
    # same strategy, same index again: the dupe reason must win
    t.on_chain("NIFTY", _doc(), _view("CASCADE", "FORCED", "BULL"), cr, {},
               now=IN_HOURS)
    # a DIFFERENT index is not a dupe, so the cap is the honest reason
    t.on_chain("SENSEX", _doc(), _view("CASCADE", "FORCED", "BULL"), cr, {},
               now=IN_HOURS)
    refusals = [r for r in t.decisions if r["kind"] == "refusal"]
    assert any("already holding" in r["detail"] for r in refusals)
    assert any("MAX_OPEN" in r["detail"] for r in refusals)


def test_eod_squares_off_everything(tmp_path):
    t = _t(tmp_path)
    cr = {"trapped_side": "ce", "drain": True, "drain_rank": 0.9}
    t.on_chain("NIFTY", _doc(), _view("CASCADE", "FORCED", "BULL"), cr, {},
               now=IN_HOURS)
    assert t.book.open_positions()
    t.on_chain("NIFTY", _doc(), _view("CASCADE", "FORCED", "BULL"), cr, {},
               now=LATE)
    assert t.book.open_positions() == []
    assert t.quoter.resting == []
    assert any("EOD square-off" in r["detail"] for r in t.decisions)


def test_the_book_survives_a_restart(tmp_path):
    t = _t(tmp_path)
    cr = {"trapped_side": "ce", "drain": True, "drain_rank": 0.9}
    t.on_chain("NIFTY", _doc(), _view("CASCADE", "FORCED", "BULL"), cr, {},
               now=IN_HOURS)
    pid = t.book.open_positions()[0].pid
    t2 = _t(tmp_path)                            # same paths: reload
    assert [p.pid for p in t2.book.open_positions()] == [pid]


def test_off_hours_keeps_the_ledger_shut(tmp_path):
    t = _t(tmp_path)
    t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=OFF_HOURS)
    assert not (tmp_path / "dec.jsonl").exists()
    # the in-memory tail still shows what would have been logged
    assert any(r["kind"] == "post" for r in t.decisions)


def test_state_names_the_paper_honesty_line(tmp_path):
    t = _t(tmp_path)
    s = t.state()
    assert s["paper"] is True
    assert "UPPER bound" in s["note"] and "no order path" in s["note"]


def test_mock_isolation_keeps_replay_out_of_the_live_record(monkeypatch):
    """The 2026-08-24 replay leak: a --mock-chain server must not share one
    forward-log path with the live record. server._isolate_mock_writers
    redirects every writer under data/mock/, and Trader must bind the
    redirected constants at call time, not def time."""
    import os
    import desk_log
    import sequence as sequence_mod
    import server

    server._isolate_mock_writers()
    try:
        mock = os.path.join("data", "mock")
        assert trader_mod.STATE.startswith(mock)
        assert trader_mod.TRADES.startswith(mock)
        assert sequence_mod.day_path("2026-08-24").startswith(mock)
        assert desk_log.surface_path("2026-08-24").startswith(mock)
        assert desk_log.DESK_LOG_PATH.startswith(mock)
        t = trader_mod.Trader()          # no args, like server.py builds it
        assert t.state_path.startswith(mock)
        assert t.trades_path.startswith(mock)
    finally:                             # never leave the module redirected
        trader_mod.DIR_ = os.path.join("data", "paper_desk")
        trader_mod.STATE = os.path.join(trader_mod.DIR_, "state.json")
        trader_mod.TRADES = os.path.join(trader_mod.DIR_, "trades.jsonl")
        sequence_mod.DIR = os.path.join("data", "warmap")
        desk_log.SURF_DIR = os.path.join("data", "surface")
        desk_log.DESK_LOG_PATH = os.path.join("data", "desk_log.jsonl")


def test_a_one_snapshot_cascade_does_not_round_trip_the_scalp(tmp_path):
    """The 2026-08-24 flicker: `drain` is a TOP-DECILE reading, so CASCADE
    lasts one snapshot by construction (measured 23 of 23 that morning). An
    exit on the first non-CASCADE tick closed every scalp in 10s and the
    strategy never once expressed its thesis. It must now survive
    CASCADE_COOL quiet snapshots -- and still exit after them."""
    t = trader_mod.Trader(state_path=str(tmp_path / "s.json"),
                          trades_path=str(tmp_path / "t.jsonl"),
                          decisions_path=str(tmp_path / "d.jsonl"))
    doc, cr = _doc(), {"trapped_side": "ce", "worst_leg": "25000CE",
                       "drain_rank": 1.0, "drain": True}
    t.on_chain("NIFTY", doc, _view("CASCADE", "FORCED", "BULL"), cr, None,
               now=IN_HOURS)
    held = [p for p in t.book.open_positions() if p.strategy == "BUY_CASCADE"]
    assert held, "the cascade scalp never opened"

    # the very next snapshot is quiet -- the old code closed here
    for _ in range(trader_mod.CASCADE_COOL - 1):
        t.on_chain("NIFTY", doc, _view("UNKNOWN"), cr, None, now=IN_HOURS)
        assert any(p.strategy == "BUY_CASCADE"
                   for p in t.book.open_positions()), \
            "closed inside the cool-off: the flicker is back"

    t.on_chain("NIFTY", doc, _view("UNKNOWN"), cr, None, now=IN_HOURS)
    assert not any(p.strategy == "BUY_CASCADE"
                   for p in t.book.open_positions()), \
        "never closed: a scalp with no exit is worse than a flickering one"


def test_a_short_is_cut_when_the_premium_inflates(tmp_path, monkeypatch):
    """2026-08-24, P7: shorts had a decay TARGET and no STOP, so the one leg
    with unbounded loss was the one that could not be cut. A SELL_CREST ran
    153.55 -> 357.55 and was closed by the 15:18 clock alone: Rs -12,240
    against +5,502 from the other twelve trips.

    DAY_LOSS_CAP is lifted here ON PURPOSE. It is the reason the defect was
    invisible live -- the winners masked the loser, so the aggregate never
    breached -- and in this fixture the measured lot size (oi/vol GCD on
    synthetic strikes) makes one position large enough that the cap fires
    first and hides what is under test. Real sizing is nowhere near it:
    P7's credit was 153.55 x 60 = Rs 9,213, so a -50% stop cuts at about
    Rs -4,600, far inside the Rs 25,000 cap."""
    monkeypatch.setattr(trader_mod, "DAY_LOSS_CAP", 10_000_000.0)
    t = _t(tmp_path)
    t.on_chain("NIFTY", _doc(), _view("PIN"), {}, {}, now=IN_HOURS)
    ce = next(q for q in t.quoter.resting if q.right == "CE")
    t.on_chain("NIFTY", _doc(prem=ce.px, bid_off=0.0, ask_off=2.0),
               _view("PIN"), {}, {}, now=IN_HOURS)
    shorts = [p for p in t.book.open_positions()
              if all(l.side == "SELL" for l in p.legs)]
    assert shorts, "no short to test the stop against"
    entry = shorts[0].legs[0].entry_px

    # premium 1.6x the credit -> frac ~ -0.60, past SHORT_STOP (-0.50)
    t.on_chain("NIFTY", _doc(prem=entry * 1.6, bid_off=0.0, ask_off=2.0),
               _view("PIN"), {}, {}, now=IN_HOURS)
    assert not [p for p in t.book.open_positions()
                if all(l.side == "SELL" for l in p.legs)],         "the short survived a 60% adverse move -- the stop is gone again"
    assert any(r["kind"] == "exit" and "cut" in r["detail"]
               for r in t.decisions), "cut without saying so"


def test_a_one_snapshot_cascade_does_not_arm_the_crest(tmp_path):
    """The other half of the same 2026-08-24 defect. SELL_CREST arms on
    `prev_gear == CASCADE and gear != CASCADE`, and 23 of 23 cascades lasted
    ONE snapshot -- so every flicker 'ended a cascade' and invited a short.
    P7 was that short. A cascade must now SURVIVE CASCADE_MIN snapshots
    before its ending means anything."""
    cr = {"trapped_side": "ce", "worst_leg": "25000CE",
          "drain_rank": 1.0, "drain": True}

    # one snapshot of CASCADE, then quiet -- must NOT arm
    t = _t(tmp_path)
    t.on_chain("NIFTY", _doc(), _view("CASCADE", "FORCED", "BULL"), cr, {},
               now=IN_HOURS)
    t.on_chain("NIFTY", _doc(), _view("UNKNOWN"), cr, {}, now=IN_HOURS)
    assert not any(p.strategy == "SELL_CREST" for p in t.book.open_positions())
    assert not any(q.tag == "SELL_CREST" for q in t.quoter.resting
                   if hasattr(q, "tag")), "a flicker still armed the crest"

    # a cascade that SURVIVES gets its ending honoured
    t2 = _t(tmp_path / "b")
    for _ in range(trader_mod.CASCADE_MIN):
        t2.on_chain("NIFTY", _doc(), _view("CASCADE", "FORCED", "BULL"), cr,
                    {}, now=IN_HOURS)
    assert t2._last_casc_len.get("NIFTY", 0) == 0    # run still open
    t2.on_chain("NIFTY", _doc(), _view("UNKNOWN"), cr, {}, now=IN_HOURS)
    assert t2._last_casc_len["NIFTY"] >= trader_mod.CASCADE_MIN, \
        "the surviving cascade's length was not recorded"
