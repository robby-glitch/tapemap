"""receipts.py: the import (flat-to-flat trips, FIFO lots, idempotent, backed up), post-track, re-entry tax, adds dumped,
fear and amber exits, and the KPI -- avg hold of winners vs losers.

Two tradebooks. test/fixtures/tradebook_synthetic.csv is committed: seven made-up fills (SYN- ids, no account) that exercise
FIFO pairing, an add dumped, a re-entry tax and an idempotent re-import. Her REAL Sep 21-24 Zerodha tradebook carries her
account's trade / order ids and fills, so it lives in data/fixtures-private/ (never committed); the tests that read it skip
with the reason when it is absent."""
import json
import os

import pytest

import receipts as R

HERE = os.path.dirname(os.path.abspath(__file__))
SEP = os.path.join(HERE, "data", "fixtures-private", "tradebook_2026-09-21_24.csv")
SYN = os.path.join(HERE, "test", "fixtures", "tradebook_synthetic.csv")
HEAD = "symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,order_execution_time,expiry_date\n"


def row(sym, day, bs, q, p, tid, t, exp="2026-09-30"):
    return f"{sym},,{day},NSE,FO,,{bs},false,{q},{p},{tid},9{tid},{day}T{t},{exp}\n"


def sep():
    """her real Sep 21-24 tradebook, private: skip (with the reason) where it is not on disk"""
    if not os.path.exists(SEP):
        pytest.skip("her real tradebook is private (data/fixtures-private/tradebook_2026-09-21_24.csv, never committed) and is not on this machine")
    with open(SEP, encoding="utf-8") as fh:
        return fh.read()


def syn():
    with open(SYN, encoding="utf-8") as fh:
        return fh.read()


# ---- the synthetic tradebook: everything a committed test needs -----------------------------------------------------
def test_synthetic_fifo_add_dumped_reentry_tax():
    fills, skipped = R.read_csv(syn())
    assert len(fills) == 7 and not skipped
    a, b, c = R.trips(fills)
    assert a["id"] == "NIFTY-23300CE-long-100000" and a["qty"] == 130 and a["p0"] == 102.0 and a["exit_px"] == 110.0
    assert R.hold_s(a) == 180 and R.fifo_hold_s(a) == 150.0                # FIFO: lot 1 held 3:00, lot 2 held 2:00
    assert [(x["t"], x["after_s"]) for x in R.adds_dumped(a)] == [("10:01:00", 120)]   # the add sold inside 2 bars
    for t in (a, b, c):
        t["_exit_px"] = t["exit_px"]
    re_ = R.reentries([a, b, c])
    assert len(re_) == 1 and re_[0]["from"] == a["id"] and re_[0]["to"] == b["id"] and re_[0]["tax"] == 5.0
    assert c["id"] == "SENSEX-74000PE-long-110000" and R.hold_s(c) == 90


def test_synthetic_kpi(tmp_path):
    d = str(tmp_path)
    R.import_write(R.import_plan(syn(), d), d, today="2026-10-05")
    sb = R.build(d, os.path.join(d, "no-chain"), today="2026-09-24")["scoreboard"]["all"]
    assert (sb["n"], sb["n_win"], sb["n_loss"]) == (3, 2, 1)
    assert sb["avg_hold_win_s"] == 135.0 and sb["avg_hold_loss_s"] == 720.0     # winners 3:00 and 1:30; the loser 12:00
    assert sb["adds_dumped"] == 1 and sb["reentry_tax_events"] == 1 and sb["reentry_tax_pts"] == 5.0


# ---- the import ---------------------------------------------------------------------------------------------------------
def test_trips_flat_to_flat_named_as_the_server_names_them():
    text = HEAD + row("NIFTY2693023300CE", "2026-09-23", "buy", 65, 100, 1, "10:00:00") + \
        row("NIFTY2693023300CE", "2026-09-23", "buy", 65, 104, 2, "10:01:00") + \
        row("NIFTY2693023300CE", "2026-09-23", "sell", 130, 110, 3, "10:03:00") + \
        row("SENSEX2610174000PE", "2026-09-23", "buy", 20, 200, 4, "11:00:00")          # still open at the file's end
    fills, skipped = R.read_csv(text)
    assert not skipped and len(fills) == 4
    ts = R.trips(fills)
    a, b = ts
    assert a["id"] == "NIFTY-23300CE-long-100000" and a["src"] == "import"
    assert a["qty"] == 130 and a["p0"] == 102.0 and a["exit_px"] == 110.0 and a["exit_t"] == "10:03:00"
    assert R.hold_s(a) == 180 and R.fifo_hold_s(a) == (180 + 120) / 2      # lot 1 held 3 min, lot 2 held 2 min
    assert b["exit_t"] is None and b["exit_px"] is None                     # open: no exit, no receipt


def test_a_row_it_cannot_read_is_named_never_dropped_silently():
    _, skipped = R.read_csv(HEAD + row("NIFTYFUT", "2026-09-23", "buy", 65, 100, 1, "10:00:00"))
    assert len(skipped) == 1 and "NIFTYFUT" in skipped[0]


def test_import_is_idempotent_and_backs_the_day_file_up(tmp_path):
    d = str(tmp_path)
    with open(os.path.join(d, "day_2026-09-23.json"), "w", encoding="utf-8") as fh:
        json.dump({"day": "2026-09-23", "hold_trades": [], "drag_day": {"NIFTY": [1]}}, fh)
    plan = R.import_plan(syn(), d)
    assert sum(len(x["new"]) for x in plan["days"].values()) == 3 and plan["fills"] == 7
    out = R.import_write(plan, d, today="2026-10-05", stamp="T")
    assert os.path.exists(os.path.join(d, "day_2026-09-23.json.bak-import-T"))       # the backup before the write
    doc = json.load(open(os.path.join(d, "day_2026-09-23.json"), encoding="utf-8"))
    assert doc["drag_day"] == {"NIFTY": [1]} and len(doc["hold_trades"]) == 2          # her other keys kept
    assert doc["hold_trades"][0]["fill_ids"] == ["SYN-T1", "SYN-T2", "SYN-T3"]
    assert set(out["wrote"]) == {"2026-09-23", "2026-09-24"}
    again = R.import_plan(syn(), d)
    assert sum(len(x["new"]) for x in again["days"].values()) == 0                    # re-importing adds nothing
    assert sum(len(x["have"]) for x in again["days"].values()) == 3


def test_her_real_tradebook_imports_29_round_trips(tmp_path):
    d = str(tmp_path)
    plan = R.import_plan(sep(), d)
    assert sum(len(x["new"]) for x in plan["days"].values()) == 29 and plan["fills"] == 64
    R.import_write(plan, d, today="2026-10-05")
    assert sum(len(x["new"]) for x in R.import_plan(sep(), d)["days"].values()) == 0


def test_today_is_handed_back_for_the_live_list_never_written_under_it(tmp_path):
    d = str(tmp_path)
    plan = R.import_plan(HEAD + row("NIFTY2693023300CE", "2026-10-05", "buy", 65, 100, 1, "10:00:00")
                         + row("NIFTY2693023300CE", "2026-10-05", "sell", 65, 101, 2, "10:01:00"), d)
    out = R.import_write(plan, d, today="2026-10-05")
    assert [t["id"] for t in out["for_today"]] == ["NIFTY-23300CE-long-100000"] and not out["wrote"]
    assert not os.path.exists(os.path.join(d, "day_2026-10-05.json"))


def test_the_door_refuses_like_a_mark():
    plan = R.import_plan(HEAD + row("NIFTY2693023300CE", "2026-09-23", "buy", 65, 100, 1, "16:00:00"), "nowhere",
                         door=lambda st, src: (None, "entry time must be inside 09:15-15:29"))
    assert plan["days"]["2026-09-23"]["refused"] and not plan["days"]["2026-09-23"]["new"]


# ---- per trade --------------------------------------------------------------------------------------------------------
def test_post_track_and_left_on_table():
    tr = {"id": "x", "day": "d", "k": 100, "side": "PE", "role": "long", "t0": "10:00:00", "exit_t": "10:05:00", "p0": 50}
    s5 = R.sec("10:05:00")
    series = [(s5 - 10, 60.0), (s5 + 300, 70.0), (s5 + 600, 75.0), (s5 + 900, 90.0), (s5 + 1200, 65.0), (s5 + 1800, 62.0)]
    pt = R.post_track(tr, 60.0, series)
    assert pt["p10"] == 75.0 and pt["p20"] == 65.0 and pt["p30"] == 62.0
    assert pt["max_fav"] == 90.0 and pt["max_fav_t"] == "10:20:00" and pt["left_on_table_pts"] == 30.0 and pt["complete"]
    short = dict(tr, role="short")                                      # a writer's favourable is the lowest premium
    assert R.post_track(short, 60.0, series)["left_on_table_pts"] == 0.0


def test_post_track_says_why_when_it_cannot():
    tr = {"id": "x", "day": "d", "k": 100, "side": "PE", "role": "long", "t0": "10:00:00", "exit_t": "10:05:00"}
    assert R.post_track(tr, 60.0, []).get("why", "").startswith("could not check")
    assert R.post_track(dict(tr, exit_t=None), 60.0, [(1, 1.0)])["why"].startswith("not shown")


def test_adds_dumped_within_two_bars():
    fills, _ = R.read_csv(sep())
    dumped = [(t["id"], a["after_s"]) for t in R.trips(fills) for a in R.adds_dumped(t)]
    # the spec's own example: 74200PE, add at 229.55, the whole 40 sold 39 s later
    assert ("SENSEX-74200PE-long-101911", 39) in dumped and len(dumped) >= 2


def test_an_add_role_exited_within_two_bars_counts_too():
    tr = {"id": "x", "role": "long", "fills": [], "roles": [
        {"id": "c", "role": "CORE", "lots": 1, "entry_t": "10:00:00"},
        {"id": "a", "role": "ADD", "lots": 1, "entry_t": "10:02:00", "exit_t": "10:05:00", "entry_px": 10}]}
    assert len(R.adds_dumped(tr)) == 1


def test_reentry_tax_same_direction_within_15_min():
    fills, _ = R.read_csv(sep())
    ts = R.trips(fills)
    for t in ts:
        t["_exit_px"] = t["exit_px"]
    re_ = R.reentries(ts)
    taxed = [x for x in re_ if x["tax"] is not None and x["tax"] > 0]
    assert len(taxed) >= 4                                               # the spec's acceptance: >= 4 re-entry-tax events
    # the spec's 23450CE ladder: 98.6 -> 101.85 -> 106.45 -> 115.65, each re-bought above the last exit
    ladder = [(x["exit_px"], x["reentry_px"]) for x in re_ if x["from"].startswith("NIFTY-23450CE") and x["day"] == "2026-09-23"]
    assert (90.8, 101.85) in ladder and (106.0, 115.65) in ladder
    other = [x for x in re_ if not x["same_leg"]]
    assert other and all(x["tax"] is None and x["why"].startswith("not shown") for x in other)


def test_fear_and_amber_need_their_evidence():
    base = {"id": "x", "day": "2026-10-05", "idx": "NIFTY", "k": 100, "side": "CE", "role": "long", "t0": "10:00:00",
            "exit_t": "10:01:00", "p0": 100, "exit_px": 110}
    r = R.receipt(dict(base), None, None, 1200)
    assert not r["fear"] and r["fear_clock_only"]                       # green in 60 s, but no flow lamp recorded
    r = R.receipt(dict(base, lamps_at_exit={"flow": {"state": "GREEN"}}), None, None, 1200)
    assert r["fear"]                                                     # the spec's clock rule, flow not red
    r = R.receipt(dict(base, lamps_at_exit={"flow": "RED"}), None, None, 1200)
    assert not r["fear"]
    r = R.receipt(dict(base, tags=["FEAR_EXIT"], exit_t="10:30:00"), None, None, 1200)
    assert r["fear"]                                                     # her record's tag decides
    words = [{"t": "10:00:00", "headline": "HOLD", "after_exit": False}]
    assert R.receipt(dict(base, reversal_at_exit=1), None, words, 1200)["amber"]
    assert not R.receipt(dict(base, reversal_at_exit=2), None, words, 1200)["amber"]
    r = R.receipt(dict(base), None, words, 1200)
    assert not r["amber"] and r["amber_unverified"]                    # HOLD at exit, reversal not recorded: apart


def test_exit_premium_says_where_it_came_from():
    tr = {"id": "x", "k": 1, "side": "CE", "role": "long", "t0": "10:00:00", "exit_t": "10:05:00"}
    assert R.exit_px(dict(tr, exit_px=5))[1] == "her fill"
    assert R.exit_px(dict(tr, roles=[{"lots": 1, "exit_px": 4}, {"lots": 3, "exit_px": 8}])) == (7.0, "her roles' exits")
    assert R.exit_px(tr, [(R.sec("10:04:00"), 6.0), (R.sec("10:06:00"), 9.0)]) == (6.0, "the chain at her exit (not her fill)")
    assert R.exit_px(tr)[0] is None


# ---- the KPI -----------------------------------------------------------------------------------------------------------
def test_kpi_on_her_sep_21_24_tradebook(tmp_path):
    d = str(tmp_path)
    R.import_write(R.import_plan(sep(), d), d, today="2026-10-05")
    out = R.build(d, os.path.join(d, "no-chain"), today="2026-09-24")
    sb = out["scoreboard"]["all"]
    assert sb["n"] == 29 and sb["n_win"] == 15 and sb["n_loss"] == 14
    # THE KPI. Her winners: median 69 s, every one but a +3.15 scratch out inside 5.5 min; the average is 150.9 s
    # (2.5 min), pulled up by that one 11.5-min scratch (23450CE 10:19:52-10:31:21). The spec's "< 2 min average"
    # holds for the median and for the 14 winners without the scratch (112.5 s), not for all 15 -- reported as is.
    assert sb["median_hold_win_s"] == 69 and sb["avg_hold_win_s"] == 150.9
    assert sb["avg_hold_loss_s"] > 2 * sb["avg_hold_win_s"]             # losers held longer: the asymmetry the spec names
    assert sb["adds_dumped"] >= 2 and sb["reentry_tax_events"] >= 4
    assert out["scoreboard"]["today"]["n"] == 13                          # 24 Sep's trips
    assert out["typical_src"].startswith("seed")                         # no chain in this folder: the 20-min seed


def test_week_of():
    assert R.week_of("2026-10-04") == "2026-09-28" and R.week_of("2026-10-05") == "2026-10-05"


# ---- the server's two routes, on a temp day folder (never data/) ---------------------------------------------------------
def test_server_import_preview_confirm_and_receipts(tmp_path, monkeypatch):
    import server
    import day_state
    d = str(tmp_path / "day_state")         # its own folder: the import mark (F13a) lands beside it, in tmp_path/receipts
    os.makedirs(d, exist_ok=True)
    monkeypatch.setattr(day_state, "DIR", d)
    monkeypatch.setattr(server, "_board_clock", lambda: ("2026-10-05", None))
    monkeypatch.setattr(server, "_save_day_state", lambda: None)
    monkeypatch.setitem(server._HOLD, "trades", [])
    monkeypatch.setitem(server._HOLD, "trades_day", "2026-10-05")
    pv = server._receipts_import(syn(), False)
    assert pv["ok"] and not pv["confirm"] and sum(len(x["new"]) for x in pv["days"].values()) == 3
    assert not os.listdir(d)                                             # a preview writes nothing
    done = server._receipts_import(syn(), True)
    assert sum(len(v) for v in done["wrote"].values()) == 3 and len(os.listdir(d)) == 2
    again = server._receipts_import(syn(), True)
    assert not again["wrote"]                                           # idempotent through the route too
    monkeypatch.setattr(server, "_receipts_words", lambda day: {})
    out = server._receipts_get()
    assert out["ok"] and out["scoreboard"]["all"]["n"] == 3 and out["scoreboard"]["all"]["adds_dumped"] == 1


def test_after_1530_a_recorded_day_with_no_import_is_due_and_a_confirmed_import_ends_it(tmp_path, monkeypatch):
    """25 Oct review F13a / A76 (TRADER F07): no tradebook import since 3 Oct. After 15:30 on a weekday whose book recorded,
    no confirmed import today makes /api/health's `tradebook.due` true (5173, the Float and Validate say "tradebook aaj
    import nahi" and link pro.html's RECORD, the existing import door). A confirmed import writes one row to
    data/receipts/import_<day>.jsonl and the nudge stops; a preview does not."""
    from datetime import datetime

    import book_log
    import day_state
    import server
    from chain_live import IST
    at = lambda h, m, mo=9, d=23: datetime(2026, mo, d, h, m, tzinfo=IST).timestamp()   # noqa: E731  (23 Sep, a Wednesday: the CSV's day)
    assert server._tradebook_due(at(15, 45)) == {"due": False}             # no book rows today: no session, no nudge
    for day in ("2026-09-23", "2026-10-05"):                               # both days recorded; only 23 Sep is in the CSV
        p = book_log.day_path(day, "NIFTY")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write("{}\n")
    assert server._tradebook_due(at(15, 29)) == {"due": False} and server._tradebook_due(at(15, 45)) == {"due": True}
    os.makedirs(str(tmp_path / "day_state"), exist_ok=True)
    monkeypatch.setattr(day_state, "DIR", str(tmp_path / "day_state"))
    monkeypatch.setattr(server, "_board_clock", lambda: ("2026-09-23", "15:45"))
    monkeypatch.setattr(server, "_save_day_state", lambda: None)
    monkeypatch.setitem(server._HOLD, "trades", [])
    monkeypatch.setitem(server._HOLD, "trades_day", "2026-09-23")
    assert server._receipts_import(syn(), False)["ok"] and server._tradebook_due(at(15, 46)) == {"due": True}   # a preview
    assert server._receipts_import(syn(), True)["ok"] and server._tradebook_due(at(15, 47)) == {"due": False}
    with open(os.path.join(server.IMPORT_DIR, "import_2026-09-23.jsonl"), encoding="utf-8") as f:
        assert len(f.readlines()) == 1
    # the mark goes on the CSV's days, not on the server's day: a 23 Sep CSV imported on 5 Oct leaves 5 Oct's nudge on
    monkeypatch.setattr(server, "_board_clock", lambda: ("2026-10-05", "15:48"))
    monkeypatch.setitem(server._HOLD, "trades_day", "2026-10-05")
    assert server._receipts_import(syn(), True)["ok"] and server._tradebook_due(at(15, 49, 10, 5)) == {"due": True}
    assert server._receipts_import(HEAD, True)["ok"] and server._tradebook_due(at(15, 50, 10, 5)) == {"due": False}   # an empty CSV (a no-trade day) clears today
