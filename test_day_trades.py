"""The paper day, read back from the LOG instead of from memory.

`closed_today` came off the in-memory book, so the 23:32 restart on 2026-08-25
truncated a screen the operator actually reads to 20 rows while
`trades.jsonl` held all 62 round trips. Same durability asymmetry the drag
trace had; this pins the fix.

The other half is the WHY. It used to live only in `decisions_<day>.jsonl`,
which carries no pid, while the trade row carried the pid and no why -- two
files with no join key, so "kya liya kb kyu liya" was unanswerable per trade
from the durable record. The writer now stamps it on the trade row.
"""

import json
from datetime import datetime

import trader as trader_mod
from trader import day_accounting, pair_trades


def _open(pid, ts="10:00:00", px=100.0, qty=60, side="BUY", idx="NIFTY",
          strategy="BUY_CASCADE", **kw):
    return dict({"day": "2026-08-25", "ts": ts, "pid": pid, "idx": idx,
                 "strategy": strategy, "kind": "open", "side": side,
                 "strike": 24200.0, "right": "CE", "px": px, "qty": qty,
                 "mode": "maker"}, **kw)


def _close(pid, ts="10:05:00", px=110.0, qty=60, side="SELL", idx="NIFTY",
           strategy="BUY_CASCADE"):
    return {"day": "2026-08-25", "ts": ts, "pid": pid, "idx": idx,
            "strategy": strategy, "kind": "close", "side": side,
            "strike": 24200.0, "right": "CE", "px": px, "qty": qty,
            "mode": "taker"}


# ---- pairing ---------------------------------------------------------------

def test_a_round_trip_pairs_into_one_row():
    (t,) = pair_trades([_open("P1"), _close("P1")])
    assert t["pid"] == "P1" and t["state"] == "CLOSED"
    assert t["entry_px"] == 100.0 and t["exit_px"] == 110.0
    assert t["realized"] == round((110.0 - 100.0) * 60, 2)
    assert t["hold_s"] == 300
    assert t["instrument"] == "24200CE"
    assert t["mode"] == "maker" and t["exit_mode"] == "taker"


def test_a_short_round_trip_realizes_the_other_way():
    (t,) = pair_trades([_open("P1", side="SELL", px=110.0),
                        _close("P1", side="BUY", px=100.0)])
    assert t["realized"] == round((100.0 - 110.0) * 60 * -1, 2) > 0


def test_partial_fills_are_averaged_quantity_weighted():
    """A plain mean would price 10@100 + 1@200 as 150 -- the arithmetic that
    makes a losing trade look flat."""
    (t,) = pair_trades([_open("P1", px=100.0, qty=100),
                        _open("P1", ts="10:00:30", px=200.0, qty=10),
                        _close("P1", px=150.0, qty=110)])
    assert t["entry_px"] == round((100 * 100 + 200 * 10) / 110.0, 2)
    assert t["qty"] == 110 and t["partial_fills"] is True


def test_a_still_open_position_is_returned_not_dropped():
    """A screen that silently omits the running trade is how a book gets
    misread."""
    (t,) = pair_trades([_open("P1")])
    assert t["state"] == "OPEN" and t["exit_px"] is None
    assert t["realized"] is None and t["hold_s"] is None


def test_rows_come_back_in_entry_order():
    ts = [t["pid"] for t in pair_trades(
        [_open("P2", ts="11:00:00"), _close("P2", ts="11:01:00"),
         _open("P1", ts="09:20:00"), _close("P1", ts="09:21:00")])]
    assert ts == ["P1", "P2"]


def test_a_close_without_an_open_is_not_invented():
    assert pair_trades([_close("P9")]) == []


def test_an_unparseable_timestamp_gives_no_hold_rather_than_zero():
    (t,) = pair_trades([_open("P1", ts="oops"), _close("P1")])
    assert t["hold_s"] is None


# ---- the why ---------------------------------------------------------------

def test_a_why_on_the_trade_row_is_used_and_marked_durable():
    (t,) = pair_trades([_open("P1", forced_who="trapped ce writers",
                              forced_why="drain rank 1.0"), _close("P1")])
    assert t["why"] == "drain rank 1.0"
    assert t["forced_who"] == "trapped ce writers"
    assert t["why_src"] == "trade row" and t["why_missing"] is None


def test_a_historical_row_recovers_its_why_from_the_decisions_join():
    """Rows written before 2026-08-26 have no why on them. The decisions log
    has it but no pid, so this is a three-field join -- and it says so."""
    why_by = {("NIFTY", "BUY_CASCADE", "10:00:00"):
              {"forced_why": "drain rank 1.0", "forced_who": "ce writers"}}
    (t,) = pair_trades([_open("P1"), _close("P1")], why_by)
    assert t["why"] == "drain rank 1.0"
    assert "decisions-log join [I]" in t["why_src"]


def test_a_why_that_cannot_be_recovered_is_null_with_a_reason():
    """Never a blank that reads as "no reason was given"."""
    (t,) = pair_trades([_open("P1"), _close("P1")], {})
    assert t["why"] is None and t["why_src"] is None
    assert "not durably logged" in t["why_missing"]


def test_the_writer_now_stamps_the_why_onto_the_trade_row():
    """The defect this batch fixed, pinned at the writer rather than only at
    the reader."""
    import inspect
    src = inspect.getsource(trader_mod.Trader._open_from_fill)
    assert '"forced_why"' in src and '"forced_who"' in src


def test_the_decisions_log_now_carries_a_pid():
    """Without it the why and the position it justified sat in two files with
    no join key."""
    import inspect
    assert "pid" in inspect.getsource(trader_mod.Trader._log)


# ---- accounting ------------------------------------------------------------

def test_accounting_nets_rupees_and_counts_per_key():
    trades = pair_trades([
        _open("P1"), _close("P1", px=110.0),
        _open("P2", idx="SENSEX"), _close("P2", idx="SENSEX", px=90.0)])
    by = day_accounting(trades, "idx")
    assert by["NIFTY"]["net"] == 600.0 and by["NIFTY"]["trades"] == 1
    assert by["SENSEX"]["net"] == -600.0


def test_an_open_trade_is_counted_apart_from_a_flat_one():
    """Letting a running position sum as 0 would read as a scratch trade."""
    by = day_accounting(pair_trades([_open("P1")]), "idx")
    assert by["NIFTY"]["open"] == 1 and by["NIFTY"]["trades"] == 0
    assert by["NIFTY"]["net"] == 0.0


def test_accounting_never_computes_a_rate():
    """House rule 4, asserted at the source so a helpful future edit fails."""
    import inspect
    src = inspect.getsource(day_accounting)
    for w in ("win", "hit_rate", "hitrate", "expectancy", "accuracy",
              "/ len(", "pct"):
        assert w not in src, w
    by = day_accounting(pair_trades([_open("P1"), _close("P1")]), "idx")
    assert set(by["NIFTY"]) == {"net", "trades", "open"}


# ---- through the real trader ------------------------------------------------

def _seed(tmp_path, rows, decisions=None):
    (tmp_path / "trades.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    if decisions is not None:
        (tmp_path / "dec.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in decisions), encoding="utf-8")
    return trader_mod.Trader(state_path=str(tmp_path / "state.json"),
                             trades_path=str(tmp_path / "trades.jsonl"),
                             decisions_path=str(tmp_path / "dec.jsonl"))


def test_the_day_survives_a_restart_because_it_is_read_from_the_log(tmp_path):
    """THE BUG THIS BATCH EXISTS FOR. A fresh Trader has an EMPTY in-memory
    book -- exactly a restart -- and must still serve every round trip."""
    rows = []
    for i in range(30):
        rows += [_open(f"P{i}", ts=f"10:{i:02d}:00"),
                 _close(f"P{i}", ts=f"10:{i:02d}:30")]
    t = _seed(tmp_path, rows)
    st = t.state({})
    assert st["closed_today"] == []              # memory is empty
    assert len(st["day_trades"]) == 30           # the log is not
    assert st["day"] == "2026-08-25"


def test_the_latest_session_is_served_not_the_calendar_day(tmp_path):
    """The operator reviews after the close, often past midnight. A calendar
    read would blank the screen at 00:00 on the session she is looking at."""
    t = _seed(tmp_path, [_open("P1"), _close("P1")])
    st = t.state({})
    assert st["day"] == "2026-08-25"
    assert st["day_is_calendar_today"] == (
        datetime.now().strftime("%Y-%m-%d") == "2026-08-25")


def test_only_the_served_day_is_included(tmp_path):
    old = dict(_open("P0"), day="2026-08-24")
    t = _seed(tmp_path, [old, _open("P1"), _close("P1")])
    assert [x["pid"] for x in t.state({})["day_trades"]] == ["P1"]


def test_refusals_come_through_with_their_reasons(tmp_path):
    dec = [{"ts": "2026-08-25T09:19:28", "kind": "refusal", "idx": "NIFTY",
            "strategy": "BUY_CASCADE", "pid": None,
            "detail": "already holding this strategy on this index",
            "evidence": {}},
           {"ts": "2026-08-25T09:20:00", "kind": "entry", "idx": "NIFTY",
            "strategy": "BUY_CASCADE", "pid": "P1", "detail": "x",
            "evidence": {}}]
    t = _seed(tmp_path, [_open("P1"), _close("P1")], dec)
    r = t.state({})["day_refusals"]
    assert len(r) == 1 and "already holding" in r[0]["why"]


def test_a_missing_trade_log_is_a_reason_not_an_empty_day(tmp_path):
    t = trader_mod.Trader(state_path=str(tmp_path / "s.json"),
                          trades_path=str(tmp_path / "nope.jsonl"),
                          decisions_path=str(tmp_path / "d.jsonl"))
    st = t.state({})
    assert st["day_trades"] is None and st["day_trades_why"]


def test_the_served_payload_carries_both_accountings(tmp_path):
    t = _seed(tmp_path, [_open("P1"), _close("P1", px=110.0)])
    st = t.state({})
    assert st["by_index"]["NIFTY"]["net"] == 600.0
    assert st["by_strategy"]["BUY_CASCADE"]["net"] == 600.0
    assert "No hit rate" in st["accounting_note"]
