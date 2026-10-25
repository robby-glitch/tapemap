"""fold_live.py (pro-tool P2-03, API-v3.md): the rev 6 engine run live -- incremental, cached, logged, isolated.

Synthetic recorded rows from test_fold (the recorders' shapes). The proofs: the live run reads what a
restart's recompute reads and the log holds no `diverged` row; logged words win; a request serves the
cache (p95 flat in the day's size) and never a day file; an engine failure is a why and never breaks
/api/hold or /api/frame; the catching-up sentences; IF YOU WERE IN off the copied market read; an exit
freezes the view; the routes."""
import json
import statistics
import time

import pytest

import fold
import fold_live
import day_state
import fold_log
import server
from test_fold import DAY, PATH_A, PE, inputs
from test_frame_api import _Req, _tape
from test_hold_route import MARK, _get, _post, fx, srv  # noqa: F401  (fixtures by name)
from test_senses_api import _Cap

TID = "NIFTY-23000PE-long-091530"
REC = {"id": TID, "idx": "NIFTY", "k": 23000.0, "side": "PE", "role": "long", "t0": "09:15:30", "p0": 100.0, "qty": 65,
       "exit_t": None, "src": "marked"}
T0, END = fold.ms(DAY, "09:20:00"), fold.ms(DAY, "09:48:00")
KEYS = ("ts", "kind", "text")


@pytest.fixture(autouse=True)
def live(tmp_path, monkeypatch):
    """A fresh engine table and the loop's seams pointed at tmp; returns the marked-trades list the seams read."""
    monkeypatch.setattr(fold_log, "_seen", {})
    monkeypatch.setattr(fold_live, "_ENG", {})
    monkeypatch.setattr(fold_live, "_Q", {})
    trades = []
    monkeypatch.setattr(server, "_hold_trades", lambda: trades)      # the routes read the same list (the POST door appends to it)
    monkeypatch.setattr(fold_live, "_CFG", dict(day_fn=lambda: DAY, trades_fn=lambda: list(trades), lot_fn=lambda i: 65,
                                                contract_fn=lambda i: {}, chain_dir_fn=lambda: str(tmp_path),
                                                vpin_path_fn=lambda: str(tmp_path / "vpin_fast.jsonl"), mock=True))
    return trades


def _cut(inp, t):
    return ([r for r in inp["book"] if r["t"] <= t], [r for r in inp["chain"] if fold.ms(DAY, r["ts"]) <= t],
            [r for r in inp["vpin"] if fold.ms(DAY, r["at"]) <= t])


def _engine(inp, upto, trades=()):
    """The engine as a start at `upto` leaves it: the rows so far installed, the states built, the reads cached."""
    eng = fold_live.Engine("NIFTY", DAY, lot=65, prior=inp["prior"], mock=True)
    eng.install(*_cut(inp, upto))
    fold_live._ENG["NIFTY"] = eng
    eng.sync(list(trades))
    eng.refresh(upto + 1)
    return eng


def _stream(eng, inp, t0, t1, trades, step=60000):
    """The live day from t0 to t1: rows pushed as the recorders would, the loop ticked once a minute."""
    for t in range(t0, t1, step):
        fold_live.push("NIFTY", "book", [r for r in inp["book"] if t < r["t"] <= t + step])
        fold_live.push("NIFTY", "chain", [r for r in inp["chain"] if t < fold.ms(DAY, r["ts"]) <= t + step])
        fold_live.push("NIFTY", "vpin", [r for r in inp["vpin"] if t < fold.ms(DAY, r["at"]) <= t + step])
        now = t + step + fold_live.LAG_MS
        eng.absorb(now)
        eng.sync(list(trades))
        eng.refresh(now)


def _ev(events):
    return [(e["ts"], e["kind"], e["text"], e["row"]["headline"], e["row"]["line2"]) for e in events]


def _get_fold(path):
    cap = _Cap(path)
    server.Handler.do_GET(cap)
    return cap.sent


# ---- one order: the live run is the recompute
def test_the_live_run_reads_what_a_restart_recomputes_and_the_log_has_no_diverged_row(live):
    inp = inputs(PATH_A)
    live.append(REC)
    eng = _engine(inp, T0, live)                       # a 09:20 start with the trade marked at 09:15:30: built from the rows so far
    e = eng.trades[TID]
    assert e["st"] is not None and e["res"]["diverged"] == 0
    _stream(eng, inp, T0, END, live)                   # ...then incremental to 09:48
    again = fold.read(dict(PE, trade_id=TID), inp, upto=END)
    assert _ev(e["st"].events) == _ev(again["events"]) and any(x["kind"] == "fold" for x in again["events"])
    rows = fold_log.read("NIFTY", DAY)
    ev = [r for r in rows if r["event"] not in ("outcome", "diverged")]
    assert [r["seq"] for r in ev] == [x["seq"] for x in e["st"].events] and not any(r["event"] == "diverged" for r in rows)
    r = e["reply"]
    assert r["ok"] and r["id"] == TID and r["trade"] == fold_live.api_trade(REC) and r["asof"] == "09:48:02"
    assert r["view"]["headline"].startswith("FOLD") and len(r["view"]["events"]) == fold_live.EVENTS_SHOWN
    assert r["words"][0]["headline"] and r["words"][-1]["headline"].startswith("FOLD") and all(set(w) == {"t", "headline", "clause", "prem", "pct", "after_exit"} for w in r["words"])
    # the restart after the close: the recompute from the same rows, against the live log -- nothing diverged, nothing re-emitted
    n = len(rows)
    eng2 = _engine(inp, END, live)
    assert eng2.trades[TID]["res"]["diverged"] == 0 and len(fold_log.read("NIFTY", DAY)) == n
    assert eng2.trades[TID]["reply"]["view"]["headline"] == r["view"]["headline"]


def test_logged_words_win_and_a_different_recompute_writes_diverged(live):
    inp = inputs(PATH_A)
    live.append(REC)
    eng = _engine(inp, T0, live)
    _stream(eng, inp, T0, END, live)
    p = fold_log.path("NIFTY", DAY)
    rows = [json.loads(x) for x in open(p, encoding="utf-8")]
    seed = next(r for r in rows if r["event"] == "seed")
    seed["headline"], seed["clause"] = "HOLD · as logged", "the logged clause"
    with open(p, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    fold_log._seen.clear()
    eng2 = _engine(inp, END, live)
    e = eng2.trades[TID]
    assert e["res"]["diverged"] == 1 and sum(1 for r in fold_log.read("NIFTY", DAY) if r["event"] == "diverged") == 1
    r = e["reply"]
    assert {k: r["words"][0][k] for k in ("t", "headline", "clause")} == {"t": seed["ts"], "headline": "HOLD · as logged", "clause": "the logged clause"}
    assert r["view"]["resumed"] is True                # the screen shows the logged words while nothing newer is read


# ---- performance and isolation (safety S11)
def _long_day(hours=4):
    segs, sides = [], ((-1, -0.1), (0, 0.0), (1, 0.1), (0, 0.0))
    for i in range(hours * 12):
        s, dp = sides[i % 4]
        segs.append((fold.hms(fold.ms(DAY, "09:15:00") + i * 300000), 300, s, dp))
    return inputs(segs)


def test_a_request_serves_the_cache_and_its_p95_does_not_grow_with_the_day(live, monkeypatch):
    def p95(path, n=40):
        ts = []
        for _ in range(n):
            t0 = time.perf_counter()
            assert _get_fold(path)["ok"]
            ts.append(time.perf_counter() - t0)
        return statistics.quantiles(ts, n=20)[18]
    live.append(REC)
    small = inputs(PATH_A[:3])
    _engine(small, fold.ms(DAY, "09:26:00"), live)
    # no request may read a day file: every reader raises for the rest of the test
    for target in ("read_rows",):
        monkeypatch.setattr(fold_live.book_log, target, lambda *a, **k: (_ for _ in ()).throw(AssertionError("a request read a day file")))
    monkeypatch.setattr(fold_live, "_jsonl", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a request read a day file")))
    monkeypatch.setattr(fold_live.tape_log, "read_bars", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a request read a day file")))
    a = p95(f"/api/fold?id={TID}")
    big = _long_day(4)
    eng = _engine(big, big["book"][-1]["t"], live)
    assert len(eng.rows["book"]) > 10 * len(small["book"])
    b = p95(f"/api/fold?id={TID}")
    assert b <= 2 * a + 0.01, (a, b)
    assert _get_fold(f"/api/fold/flat?idx=NIFTY")["ok"]


def test_an_engine_failure_is_a_why_and_never_breaks_the_hold_window_or_the_frame(live, srv, monkeypatch, tmp_path):
    inp = inputs(PATH_A)
    live.append(REC)
    eng = _engine(inp, T0, live)
    assert eng.trades[TID]["reply"]["ok"] and eng.flat_read["ok"]
    monkeypatch.setattr(fold.State, "feed", lambda self, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    _stream(eng, inp, T0, T0 + 120000, live)
    for path in (f"/api/fold?id={TID}", "/api/fold/flat?idx=NIFTY"):
        out = _get_fold(path)
        assert out["ok"] is False and out["why"] == "could not check — the engine failed: RuntimeError: boom", path
    # the old window (rev 5) does not know the engine exists
    assert _post("/api/hold/trades", MARK, srv)["ok"]
    assert _get("/api/hold?id=NIFTY-23200PE-long-122030", srv)["ok"]
    # the frame: the engine's failure rides on it as a why, the frame itself is served
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    monkeypatch.setattr(server, "_hold_trades", lambda: [dict(REC)])
    req = _Req("/api/frame", _tape(n=3))
    server.Handler.do_POST(req)
    code, fr = req.out[-1]
    assert fr["ok"] and fr["fold"]["ok"] is False and "the engine failed" in fr["fold"]["why"] and fr["flat"] is None
    monkeypatch.setattr(fold_live, "frame", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("frame boom")))
    req = _Req("/api/frame", _tape(n=3))
    server.Handler.do_POST(req)
    code, fr = req.out[-1]
    assert fr["ok"] and fr["fold"] == {"ok": False, "why": "could not check — the engine failed: frame boom"} and fr["flat"] is None


def test_the_frame_carries_flat_when_no_trade_is_open(live, monkeypatch, tmp_path):
    _engine(inputs(PATH_A[:3]), fold.ms(DAY, "09:26:00"))
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    req = _Req("/api/frame", _tape(n=3))
    server.Handler.do_POST(req)
    fr = req.out[-1][1]
    assert fr["ok"] and fr["fold"] is None and fr["flat"]["ok"] and set(fr["flat"]["rows"]) == {"zone", "flow", "oi", "vpin"}
    assert fr["flat"]["next_fight"] is None or set(fr["flat"]["next_fight"]) == {"above", "below"}
    assert fr["chain"] == {"ok": False, "why": "could not check — no chain snapshot yet"}      # _Req has no poller


def test_the_frame_carries_the_open_trades_view_whole(live, monkeypatch, tmp_path):
    """The panel renders the view as the engine gives it: units (with basis), d, G, A, W and the last 12 events,
    each with its time -- nothing trimmed but the event count (fold.py's own fields pass through)."""
    inp = inputs(PATH_A)
    live.append(REC)
    _engine(inp, END, live)
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    req = _Req("/api/frame", _tape(n=3))
    server.Handler.do_POST(req)
    fr = req.out[-1][1]
    v = fr["fold"]["view"]
    assert fr["ok"] and fr["flat"] is None and fr["fold"]["ok"] and fr["fold"]["id"] == TID
    assert v["units"]["basis"] is not None and v["d"] == -1 and v["G"]["px"] and v["W"]["k"] and "A" in v
    assert 0 < len(v["events"]) <= fold_live.EVENTS_SHOWN and all(e["ts"] and e["t"] and e["kind"] for e in v["events"])
    assert set(v["rows"]) == {"zone", "flow", "oi", "vpin"} and v["prem"]["now"] and v["sound_id"]


def test_the_frame_carries_her_open_trade_on_another_index_and_this_index_never_reads_it(live, monkeypatch, tmp_path):
    """25 Oct review F6 / A70 (DEV-FACES F04): she trades SENSEX on the NIFTY chart (§1q), and NIFTY's page is the one that
    posts. The frame carried `fold` only for an open trade on the POST's own index, so the panel read FLAT mid-trade with
    NIFTY MARK buttons. Now: her most recent open marked trade on any index, its idx in fold.trade, and open_n. NIFTY's own
    flat read still rides, and NIFTY's story (and the HOLD-vs-DECODER log) never take the SENSEX trade."""
    import story
    sx = dict(REC, id="SENSEX-81200CE-long-100500", idx="SENSEX", k=81200.0, side="CE", t0="10:05:00")
    bn = dict(REC, id="BANKNIFTY-54000PE-long-094000", idx="BANKNIFTY", k=54000.0, t0="09:40:00")
    live.extend([dict(REC, exit_t="09:30:00"), bn, sx])          # NIFTY's own trade is closed: nothing open on this index
    told = []
    monkeypatch.setattr(story, "compose_all", lambda *a, **k: told.append(a[5]) or {})   # a[5]: the fold the story reads
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    old = _Req("/api/frame", _tape(n=3))                         # a 0.5.10 page: no `away` -- it must never get another index's trade
    server.Handler.do_POST(old)
    assert old.out[-1][1]["fold"] is None
    req = _Req("/api/frame", dict(_tape(n=3), away=1))           # a 0.5.11 page opts in
    server.Handler.do_POST(req)
    fr = req.out[-1][1]
    assert fr["ok"] and fr["fold"]["id"] == sx["id"] and fr["fold"]["trade"]["idx"] == "SENSEX" and fr["fold"]["open_n"] == 2
    assert fr["flat"] is not None                                # NIFTY's flat read is this chart's own
    assert told == [None, None]                                  # the NIFTY story never reads the SENSEX trade


def test_a_chart_symbol_that_does_not_parse_to_an_index_never_gets_another_indexs_trade(live, monkeypatch, tmp_path):
    """25 Oct final review (F6): an `away` page whose chart symbol did not parse posts idx NIFTY26OCTFUT. No trade is
    "mine" there, so the opt-in handed it her SENSEX trade -- and an extension that cannot parse the chart's index would
    treat it as its own and draw its lines. The opt-in counts only on a known index."""
    live.append(dict(REC, id="SENSEX-81200CE-long-100500", idx="SENSEX", k=81200.0, side="CE", t0="10:05:00"))
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    req = _Req("/api/frame", dict(_tape(n=3), away=1, idx="NIFTY26OCTFUT"))
    server.Handler.do_POST(req)
    assert req.out[-1][1]["ok"] and req.out[-1][1]["fold"] is None


class _ChainPoller:
    """prevs / boxes as chain_live.ChainPoller publishes them: the latest normalized snapshot per index."""
    def __init__(self, sec, mode="live"):
        self.prevs = {"NIFTY": {"ts": "10:00:00", "sec": sec, "spot": 23012.0, "atm": 23000, "strikes": [
            {"k": 22950, "ce": {"ltp": 120.0}, "pe": {"ltp": 40.0}},
            {"k": 23000, "ce": {"ltp": 90.0}, "pe": {"ltp": 55.0}},      # nearest the spot: F* = 23000 + 90 - 55 = 23035
            {"k": 23050, "ce": {"ltp": 60.0}, "pe": {"ltp": 80.0}}]}}
        self.boxes = {"NIFTY": {"mode": mode}}


def test_frame_chain_is_the_latest_snapshot_with_atm_on_the_forward_and_a_stale_flag():
    from datetime import datetime
    from chain_live import IST, _sec_of_day
    now = _sec_of_day(datetime.now(IST))
    c = server._frame_chain(_ChainPoller(now - 30), "NIFTY")
    assert c["ok"] and c["ts"] == "10:00:00" and c["step"] == 50 and c["F"] == 23035.0 and c["atm"] == 23050   # not the spot's 23000
    assert c["strikes"] == [{"k": 22950, "ce": 120.0, "pe": 40.0}, {"k": 23000, "ce": 90.0, "pe": 55.0}, {"k": 23050, "ce": 60.0, "pe": 80.0}]
    assert "stale" not in c and 25 <= c["age_s"] <= 40 and c["tag"] == {"M": ["strikes", "ts"], "I": ["F", "atm"]}
    old = server._frame_chain(_ChainPoller(now - 400), "NIFTY")
    assert old["stale"] is True and old["stale_why"] == "chain snapshot 6 min old" and old["atm"] == 23050
    rb = server._frame_chain(_ChainPoller(now - 30, mode="restored"), "NIFTY")
    assert rb["stale"] is True and rb["stale_why"] == "rebuilt from the day file, not a live snapshot"
    assert server._frame_chain(None, "NIFTY") == {"ok": False, "why": "could not check — no chain snapshot yet"}


# ---- anytime start
def test_the_catching_up_sentences_until_the_engine_is_ready(live):
    live.append(REC)
    eng = fold_live._ENG["NIFTY"] = fold_live.Engine("NIFTY", DAY, lot=65, mock=True)
    why = lambda: _get_fold(f"/api/fold?id={TID}")["why"]   # noqa: E731
    assert why() == "could not check — the engine is catching up (reading the day's files)"
    eng.install([], [])
    eng.sync(live)
    assert why() == "could not check — the engine is catching up (no chain snapshot yet)"
    eng.progress = (500, 2000)
    assert why() == "could not check — the engine is catching up (500 of 2000 rows)"
    assert _get_fold("/api/fold/flat?idx=NIFTY")["why"] == "could not check — the engine is catching up (500 of 2000 rows)"
    assert _get_fold("/api/fold?id=nope")["why"] == "could not check — no marked trade nope today"
    assert _get_fold("/api/fold/flat?idx=SENSEX")["why"] == "could not check — the engine has not started on this index"


def test_the_loop_makes_the_engine_reads_the_files_once_and_goes_incremental(live, tmp_path):
    """tick(): the queue -> the engine (made on first use, the day files read once -- empty here) -> the cache."""
    inp = inputs(PATH_A[:3])
    end = inp["book"][-1]["t"]
    fold_live.push("NIFTY", "book", inp["book"])
    fold_live.push("NIFTY", "chain", inp["chain"])
    fold_live.push("NIFTY", "vpin", inp["vpin"])
    fold_live.push("BANKNIFTY", "book", inp["book"])          # read all day too (she trades all three)
    fold_live.push("FINNIFTY", "book", inp["book"])           # not hers, no trade there: dropped at the queue, never held
    fold_live.tick(end + fold_live.LAG_MS + 1)
    eng = fold_live._ENG["NIFTY"]
    assert eng.loaded and len(eng.rows["book"]) == len(inp["book"]) and eng.flat is not None and "FINNIFTY" not in fold_live._ENG
    assert list(fold_live._ENG)[:2] == ["NIFTY", "BANKNIFTY"] and len(fold_live._ENG["BANKNIFTY"].rows["book"]) == len(inp["book"])
    assert not fold_live._Q.get("FINNIFTY") and eng.flat_read["ok"] and eng.flat_read["asof"] == fold.hms(end + fold_live.LAG_MS + 1)
    # a repeat of the same rows (a re-published payload, a re-flushed batch) is not fed twice
    fold_live.push("NIFTY", "chain", inp["chain"][-3:])
    fold_live.tick(end + fold_live.LAG_MS + 5000)
    assert len(eng.rows["chain"]) == len(inp["chain"])


# ---- IF YOU WERE IN, the exit, the record
def test_ifin_is_the_market_read_copied_and_marked_now(live):
    inp = inputs(PATH_A)
    end = fold.ms(DAY, inp["chain"][-1]["ts"])       # the last recorded row is a chain row: the mark is at its ts
    eng = _engine(inp, end)
    q = {"idx": ["NIFTY"], "k": ["23000"], "ty": ["PE"], "side": ["BUY"]}
    first = fold_live.reply("/api/fold/ifin", q, [])
    assert first["ok"] is False and first["why"] == "could not check — reading 23000 PE BUY now (first look)"
    eng.refresh(end + fold_live.READ_EVERY_S * 1000 + 1)
    got = fold_live.reply("/api/fold/ifin", q, [])
    ref = fold.ifin(inp, 23000, "PE", "BUY", upto=end)
    v = got["view"]
    assert got["ok"] and v["ifin"] is True and v["trade"]["p0"] == ref["p0"] and v["entry_t"] == ref["entry_t"]
    assert (v["headline"], v["line2"], v["G"]["px"], v["A"] and v["A"]["k"]) == (ref["headline"], ref["line2"], ref["G"]["px"], ref["A"] and ref["A"]["k"])
    assert eng.flat.trade is None                     # the copy never touched the market read
    rows = fold_log.read("NIFTY", DAY)
    assert rows and all(r["src"] == "ifin" and r["trade_id"].startswith("ifin:") for r in rows)   # logged as ifin, once per look
    eng.refresh(end + 2 * fold_live.IFIN_EVERY_S * 1000)
    assert len(fold_log.read("NIFTY", DAY)) == len(rows)
    assert fold_live.reply("/api/fold/ifin", {"idx": ["NIFTY"], "k": ["x"]}, [])["why"] == "could not check — ifin needs k, ty CE|PE and side BUY|SELL"


def test_an_exit_freezes_the_view_at_the_exit_and_a_changed_record_rebuilds(live):
    inp = inputs(PATH_A)
    live.append(REC)
    eng = _engine(inp, END, live)
    v = eng.trades[TID]["reply"]["view"]
    assert v["frozen"] is False and "exit_t" not in v
    live[0]["exit_t"] = "09:40:00"                    # the exit door: the same record, changed in place
    eng.sync(live)
    eng.refresh(END + 10000)
    v = eng.trades[TID]["reply"]["view"]
    ref = fold.read(dict(PE, trade_id=TID), inp, upto=END, exit_t="09:40:00")
    assert v["frozen"] is True and v["exit_t"] == "09:40:00" and v["prem"]["now"] == ref["prem"]["now"] and v["ts"] == "09:40:00"
    rec = fold_live.reply("/api/fold/record", {"day": [DAY]}, live)
    t = rec["trades"][0]
    assert rec["ok"] and t["id"] == TID and t["exit"] == {"t": "09:40:00", "prem": ref["prem"]["now"], "pct": ref["prem"]["pct"]}
    assert t["peak_before_exit"]["prem"] == ref["prem"]["peak"] and t["given_back"] == ref["prem"]["given_back"] and t["words"]
    assert all(w["after_exit"] == (w["t"] > "09:40:00") for w in t["words"])   # the engine reads on after her exit, and says so
    # a day gone from memory reads off the files: the same trade, the same words, the exit premium from the logged rows
    day_state.save(DAY, {"hold_trades": [dict(live[0])]})
    fold_live._CFG["day_fn"] = lambda: "2026-01-02"
    past = fold_live.reply("/api/fold/record", {"day": [DAY]}, live)
    p = past["trades"][0]
    assert past["ok"] and p["id"] == TID and p["trade"]["exit_t"] == "09:40:00" and p["exit"]["t"] == "09:40:00"
    assert [(w["t"], w["headline"]) for w in p["words"]] == [(w["t"], w["headline"]) for w in t["words"]]
    assert all(w["after_exit"] == (w["t"] > "09:40:00") for w in p["words"]) and p["exit"]["at"] <= "09:40:00"
    assert fold_live.reply("/api/fold/record", {"day": ["2026-01-05"]}, live) == {"ok": True, "day": "2026-01-05", "trades": []}
    fold_live._CFG["day_fn"] = lambda: DAY
    live[0]["exit_t"] = None                          # reopen: rebuilt again, live again
    eng.sync(live)
    eng.refresh(END + 20000)
    assert eng.trades[TID]["reply"]["view"]["frozen"] is False
    live.clear()
    eng.sync(live)
    assert eng.trades == {} and _get_fold(f"/api/fold?id={TID}")["why"] == f"could not check — no marked trade {TID} today"


def test_a_trade_without_an_entry_premium_says_so(live):
    live.append(dict(REC, p0=None))
    eng = _engine(inputs(PATH_A[:3]), fold.ms(DAY, "09:26:00"), live)
    assert eng.trades[TID]["reply"]["why"] == f"could not check — no entry premium was marked for {TID}"


# ---- the old window's plumbing (rev 5 stays; fixes a and b)
def test_after_her_exit_the_old_window_shows_the_premium_at_the_exit_not_the_latest():
    """Plumbing fix (a), 2026-09-29: her 10:20 exit showed P&L at 15:29's premium. After exit_t every row's premium
    and P&L are the exit minute's (the finished minute before it, as the entry reads). On the frozen hold fixtures."""
    import hold
    from test_hold import _read, _trades
    tr = next(t for t in _trades() if _read(t)[0] and "c" in _read(t)[0]["rows"][-1]["prem"])
    rows = _read(tr)[0]["rows"]
    xt = rows[len(rows) // 2]["t"]                     # she marks out 30 s into the minute after xt: xt is the exit read
    out = _read(dict(tr, exit_t=hold.hm(hold.mm(xt) + 1) + ":30"))[0]["rows"]
    xi = next(i for i, r in enumerate(out) if r["t"] == xt)
    assert [r["prem"] for r in out[:xi + 1]] == [r["prem"] for r in rows[:xi + 1]]     # before the exit: unchanged
    assert all(r["prem"] == out[xi]["prem"] for r in out[xi:]) and out[-1]["t"] == rows[-1]["t"]
    assert rows[-1]["prem"]["c"] != out[xi]["prem"]["c"]                                  # the latest print differs: it is not shown


def test_the_latch_rule_is_its_own_field_never_a_checked_none_sentence(srv):
    tid = _post("/api/hold/trades", MARK, srv)["trades"][0]["id"]
    a = _get(f"/api/hold?id={tid}", srv)
    assert "rule_note" in a["absent"]
    if a["fold"]:
        assert a["absent"]["checked_none"] is None and a["absent"]["rule_note"] == "nothing un-latches a FOLD; a re-entry is a new trade"
    else:
        assert a["absent"]["checked_none"] == "checked, none — no FOLD rule has matched since your entry" and a["absent"]["rule_note"] is None
    assert not any("un-latches" in (a["absent"]["checked_none"] or "") for _ in [0])
