# tapemap/test_frame_api.py
"""POST /api/frame stores the tape and answers have_bars; a bad interval is refused with a reason."""
import json
import server


class _Req:
    """The smallest stand-in for the handler: only what do_POST reads."""
    def __init__(self, path, body):
        self.path, self._b = path, json.dumps(body).encode()
        self.headers = {"Content-Length": str(len(self._b))}
        self.out = []
        self.poller, self.chains, self.payloads = None, None, {}
        class R:  # noqa
            def __init__(s, b): s.b = b
            def read(s, n): return s.b
        self.rfile = R(self._b)
    def _json(self, body, code=200): self.out.append((code, json.loads(body)))


def _tape(interval=5, n=3):
    return {"kind": "frame", "session": f"NIFTY-I|{interval}m|2026-09-11", "idx": "NIFTY", "interval": interval,
            "closed": [{"t": 1757563500000 + i * 300000, "o": 1, "h": 2, "l": 0, "c": 1, "vol": 10, "delta": 1, "buy": 5, "sell": 4, "oi": 1, "fromTicks": True} for i in range(n)],
            "forming": None, "bands": [], "walls": [], "broke": [], "events": [], "taps": [], "rowSize": 5, "futPx": 1.0}


def test_frame_post_stores_the_tape_and_answers_have_bars(tmp_path, monkeypatch):
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    req = _Req("/api/frame", _tape(n=3))
    server.Handler.do_POST(req)
    code, j = req.out[-1]
    assert code == 200 and j["ok"] is True and j["have_bars"] == 3
    assert server._SENSES["tape"]["NIFTY"]["doc"]["session"] == "NIFTY-I|5m|2026-09-11"
    assert "coverage" in j          # frame.build's own coverage rides the reply
    # the five-question frame, not the nine blocks: every object is on the wire and the record flag is a bool
    for k in ("head", "where", "trapped", "walls", "tape", "setup"):
        assert isinstance(j[k], dict), k
    assert isinstance(j["record"]["written"], bool) and "log_row_written" not in j and "strip" not in j


def test_after_the_close_the_frame_is_the_last_session_snapshot(tmp_path, monkeypatch):
    """2026-09-23: GoCharting kept drawing bars after 15:30 and each one reached
    the build, the frame record, the ladder file and the scorer -- 81 rows and
    2.5 MB after the close. Bars and marks stamped 15:30 or later never arrive."""
    import tape_log
    from datetime import datetime, timedelta, timezone
    ist = timezone(timedelta(hours=5, minutes=30))
    ms = lambda h, m: int(datetime(2026, 9, 23, h, m, tzinfo=ist).timestamp() * 1000)
    out = server._session_only({"closed": [{"t": ms(15, 20)}, {"t": ms(15, 25)}, {"t": ms(15, 30)}, {"t": ms(16, 0)}],
                                "forming": {"t": ms(16, 5)}, "events": [{"t": ms(15, 29)}, {"t": ms(15, 31)}]})
    assert [b["t"] for b in out["closed"]] == [ms(15, 20), ms(15, 25)]
    assert out["forming"] is None and [e["t"] for e in out["events"]] == [ms(15, 29)]
    assert server._session_only({"forming": {"t": ms(15, 25)}})["forming"] == {"t": ms(15, 25)}   # in session: kept
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    bars = [dict(_tape()["closed"][0], t=ms(15, m)) for m in (15, 20, 25, 30, 35)]
    req = _Req("/api/frame", {**_tape(), "closed": bars})
    server.Handler.do_POST(req)
    assert req.out[-1][1]["have_bars"] == 3                                   # 15:15, 15:20, 15:25
    assert len(server._SENSES["tape"]["NIFTY"]["doc"]["closed"]) == 3


def test_frame_post_refuses_a_non_5m_interval_with_a_reason(tmp_path):
    req = _Req("/api/frame", _tape(interval=1))
    server.Handler.do_POST(req)
    code, j = req.out[-1]
    assert code == 200 and j["ok"] is False and "5" in j["why"] and "interval" in j["why"]


def test_book_for_reads_zone_state_from_days0(monkeypatch):
    """derive_payload nests zone_state under days[0]; the book must read it there."""
    req = _Req("/api/frame", _tape())
    req.payloads = {"NIFTY": {"payload": None}}
    monkeypatch.setattr(server, "payload_at", lambda box, iv: json.dumps(
        {"expiry": "2026-09-16", "days": [{"zone_state": [{"state": "ARMED"}], "zone_state_sell": [],
                                             "pivots": {"P": 23400.0, "R1": 23500.0, "S1": 23300.0}}]}).encode())
    book = server._book_for(req, "NIFTY")
    assert book["zone_state"] == [{"state": "ARMED"}] and book["zone_state_sell"] == []
    assert book["pivots"] == {"P": 23400.0, "R1": 23500.0, "S1": 23300.0}     # the prior session's floor pivots ride the book


def test_the_record_is_rescored_once_per_closed_bar_not_once_per_post(monkeypatch):
    """2026-09-18: `score_frame.write` reads, parses, rescores and rewrites the
    WHOLE day file. At 55 MB across 2,026 rows, with the extension posting every
    few seconds, each request held a 55 MB parse; the process reached 2.2 GB with
    ~70 sockets in CLOSE_WAIT and stopped accepting connections, twice, without
    raising. Nothing the scorer fills can change until a bar closes."""
    import server
    calls = []
    monkeypatch.setattr(server.score_frame, "write",
                        lambda day, bars, **k: calls.append(len(bars)))
    server._SCORED_BARS.clear()

    def post(idx, nbars):
        # the guard exactly as the POST handler applies it
        if nbars != server._SCORED_BARS.get(idx):
            server._SCORED_BARS[idx] = nbars
            server.score_frame.write("2026-09-18", [{}] * nbars)

    for _ in range(40):          # forty posts inside one five-minute bar
        post("NIFTY", 12)
    assert calls == [12], "a post that closed no new bar must not rewrite the file"

    post("NIFTY", 13)            # the bar closes
    assert calls == [12, 13]

    post("BANKNIFTY", 13)        # a different index keeps its own count
    assert calls == [12, 13, 13]


def test_frame_post_records_the_ladder_bars_and_marks(tmp_path, monkeypatch):
    import tape_log
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    tape_log._seen_bars.clear(); tape_log._seen_marks.clear()
    doc = _tape(n=2)
    for b in doc["closed"]:
        b["ladder"] = [{"p": 1.0, "b": 3, "s": 1, "bt": 2, "st": 1}]
    doc["events"] = [{"t": doc["closed"][0]["t"], "kind": "absorption", "side": 1, "p": 1.0, "size": 3}]
    doc["rowAnchor"] = 0
    req = _Req("/api/frame", doc)
    server.Handler.do_POST(req)
    assert req.out[-1][1]["ok"] is True
    bars = tape_log.read_bars("2026-09-11", "NIFTY")
    assert len(bars) == 2 and bars[0]["ladder"] == [{"p": 1.0, "b": 3, "s": 1, "bt": 2, "st": 1}]
    assert len(tape_log.read_marks("2026-09-11", "NIFTY")) == 1
    server.Handler.do_POST(_Req("/api/frame", doc))     # the every-second re-post
    assert len(tape_log.read_bars("2026-09-11", "NIFTY")) == 2


from test_senses_api import _Cap as _SensesCap   # the GET harness, one copy in the tree


class _Cap(_SensesCap):
    """The senses harness plus the one Handler method /api/tape reaches: `_idx()`
    (a real method on `Handler`, bound here so `self._idx()` resolves)."""
    _idx = server.Handler._idx


def _ladder_doc(day="2026-09-11", n=8):
    doc = _tape(n=n)
    doc["session"] = f"NIFTY-I|5m|{day}"
    doc["rowAnchor"] = 0
    for i, b in enumerate(doc["closed"]):
        b.update({"o": 100 + i, "h": 104 + i, "l": 99 + i, "c": 101 + i, "vol": 20 + i, "buy": 12, "sell": 8 + i, "delta": 4 - i})
        b["ladder"] = [{"p": 100.0 + i, "b": 9, "s": 1, "bt": 3, "st": 1}, {"p": 101.0 + i, "b": 2, "s": 8, "bt": 1, "st": 2}]
    doc["events"] = [{"t": doc["closed"][1]["t"], "kind": "absorption", "side": 1, "p": 101.0, "size": 9}]
    doc["forming"] = {"t": doc["closed"][-1]["t"] + 300000, "o": 1, "h": 2, "l": 0, "c": 1, "vol": 3, "delta": 1, "buy": 2, "sell": 1,
                      "ladder": [{"p": 1.0, "b": 2, "s": 1, "bt": 1, "st": 1}]}
    return doc


def _isolate(tmp_path, monkeypatch):
    import tape_log
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    tape_log._seen_bars.clear(); tape_log._seen_marks.clear()
    server._SENSES["tape"].pop("NIFTY", None)


def test_api_tape_live_when_the_extension_posted_within_15s(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc()))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["ok"] is True and j["src"] == "live" and j["interval"] == 5 and j["tag"] == "M"
    # the ladder is NOT on the wire (spec §D, amended at the final review): 81 % of
    # the bytes, no consumer. It stays in the record.
    assert len(j["bars"]) == 8 and "ladder" not in j["bars"][0] and "cvd" in j["bars"][0] and "stacks" in j["bars"][0]
    assert "ladder" not in j["forming"] and j["forming"]["poc"] is not None and j["forming_why"] is None
    assert j["levels"]["session"]["poc"] is not None and isinstance(j["levels"]["nodes"], list)
    assert j["levels"]["prior"] == [] and j["levels"]["prior_why"] == "no earlier day in the record yet"
    assert j["marks"]["ofd"][0]["src"] == "ofd" and all(m["src"] == "tm" and m["tag"] == "I" for m in j["marks"]["tm"])
    assert j["marks"]["ofd_why"] is None                     # marks present: no sentence to say
    assert j["rowSize"] == 5 and j["rowAnchor"] == 0


def test_api_tape_file_when_the_extension_is_silent(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc()))
    server._SENSES["tape"]["NIFTY"]["at"] -= 60          # a minute of silence
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["ok"] is True and j["src"] == "file" and len(j["bars"]) == 8
    assert j["forming"] is None and "not posting" in j["forming_why"]
    assert j["marks"]["ofd"] and j["marks"]["ofd"][0]["kind"] == "absorption"


def test_api_tape_neither_is_the_third_sentence(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    assert cap.sent["ok"] is False and "no prints record for NIFTY on 2026-09-11" in cap.sent["why"]


def test_api_tape_prior_days_and_naked_from_the_record(tmp_path, monkeypatch):
    import tape_log
    _isolate(tmp_path, monkeypatch)
    for day in ("2026-09-09", "2026-09-10"):
        tape_log._seen_bars.clear(); tape_log._seen_marks.clear()
        server.Handler.do_POST(_Req("/api/frame", _ladder_doc(day=day)))
    tape_log._seen_bars.clear(); tape_log._seen_marks.clear()
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc(day="2026-09-11")))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert [p["day"] for p in j["levels"]["prior"]] == ["2026-09-10", "2026-09-09"]
    assert j["levels"]["prior_why"] is None
    assert isinstance(j["levels"]["naked"], list)


def test_api_tape_ladder_why_when_a_bar_lacks_one(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    doc = _ladder_doc()
    del doc["closed"][0]["ladder"]
    server.Handler.do_POST(_Req("/api/frame", doc))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    assert "predates ladders" in cap.sent["ladder_why"]


def test_api_tape_ladder_why_also_fires_on_an_empty_ladder(tmp_path, monkeypatch):
    """Extension 0.3.1 posts `[]` for a bar it has no ladder for, so the test is
    falsy, not `is None` -- an empty ladder is still a bar without one."""
    _isolate(tmp_path, monkeypatch)
    doc = _ladder_doc()
    doc["closed"][0]["ladder"] = []
    server.Handler.do_POST(_Req("/api/frame", doc))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    assert "predates ladders" in cap.sent["ladder_why"]


def test_api_tape_levels_why_when_no_bar_carries_a_ladder(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    doc = _ladder_doc()
    for b in doc["closed"]:
        b["ladder"] = []
    server.Handler.do_POST(_Req("/api/frame", doc))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["levels"]["session"] is None and j["levels"]["why"] == "no bar with a ladder yet"
    assert j["levels"]["nodes"] == []


def test_api_tape_ofd_why_live_case_is_its_own_sentence(tmp_path, monkeypatch):
    """The live branch has no marks file to check at all -- it's neither of the
    file branch's two sentences, it's a third: the extension hasn't posted a
    detection yet today."""
    _isolate(tmp_path, monkeypatch)
    doc = _ladder_doc()
    doc["events"] = []
    server.Handler.do_POST(_Req("/api/frame", doc))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["src"] == "live" and j["marks"]["ofd"] == []
    assert j["marks"]["ofd_why"] == "the extension has detected nothing yet today"


def test_api_tape_ofd_why_keeps_no_file_apart_from_nothing_detected(tmp_path, monkeypatch):
    """Rule 6: the seeded days hold BARS only -- no marks file was ever written
    for them -- and that is a different fact from a day the extension watched
    and detected nothing on."""
    import tape_log
    _isolate(tmp_path, monkeypatch)
    doc = _ladder_doc()
    doc["events"] = []
    server.Handler.do_POST(_Req("/api/frame", doc))
    server._SENSES["tape"]["NIFTY"]["at"] -= 60          # read the record, not the live doc
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    why = cap.sent["marks"]["ofd_why"]
    assert cap.sent["marks"]["ofd"] == [] and "no marks file for NIFTY on 2026-09-11" in why
    assert "seeded from an export" in why
    # the file exists and holds nothing: the OTHER sentence
    open(tape_log.marks_path("2026-09-11", "NIFTY"), "w", encoding="utf-8").close()
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    assert cap.sent["marks"]["ofd_why"] == "the extension detected nothing on this day"


def test_api_tape_an_empty_kind_event_is_dropped_by_the_record_and_the_wire(tmp_path, monkeypatch):
    import tape_log
    _isolate(tmp_path, monkeypatch)
    doc = _ladder_doc()
    doc["events"] = [{"t": doc["closed"][1]["t"], "kind": "", "side": 1, "p": 101.0, "size": 9}]
    server.Handler.do_POST(_Req("/api/frame", doc))
    assert tape_log.read_marks("2026-09-11", "NIFTY") == []          # the record
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    assert cap.sent["src"] == "live" and cap.sent["marks"]["ofd"] == []   # the live wire


# --- spec 2026-09-20-upstox-tape §E: the ux object -------------------------------

def _ux_seed(day="2026-09-11"):
    """Two closed ux bars whose t match _ladder_doc's first two bars."""
    import ux_log
    from test_ladder import R
    T = 1757563500000
    rows = [R(T + 1000, 1000, 100.0, 65, [[100.0, 65]], [[101.0, 65]]),
            R(T + 2000, 1065, 101.0, 65, [[100.0, 65]], [[101.0, 65]]),            # exact buy at 101
            R(T + 300_500, 1130, 100.0, 65, [[100.0, 65]], [[101.0, 65]]),         # exact sell at 100, bin 1
            R(T + 600_500, 1130, 100.0, 65, [[100.0, 65]], [[101.0, 65]])]         # bin 2: closes bin 1
    ux_log.state("NIFTY", day, 65, 1.0)
    ux_log.on_frames([("NIFTY", r) for r in rows], day)


def _isolate_ux(tmp_path, monkeypatch):
    import book_log
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setitem(server._SENSES, "book", book_log.Book())
    server._SENSES["ux"].clear()


def test_api_tape_ux_absent_is_the_first_sentence(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc()))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    ux = cap.sent["ux"]
    assert ux["src"] == "ux" and ux["tag"] == "I" and ux["bars"] == [] and ux["agree"] is None
    assert ux["why"] == "no book record for NIFTY on 2026-09-11 — the server was not recording (book_log predates it, or the feed never connected)"
    assert ux["levels"]["why"] == ux["why"] and ux["agree_why"] == ux["why"] and ux["marks"]["runs_why"] == ux["why"]


def test_api_tape_ux_book_but_no_bar_yet_is_the_second_sentence(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    server._SENSES["book"].book_from["NIFTY"] = "09:15:03"
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc()))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    assert cap.sent["ux"]["why"] == "book record from 09:15:03, no bar closed yet"


def test_api_tape_ux_bars_levels_marks_impact_and_agreement(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    _ux_seed()
    server.Handler.do_POST(_Req("/api/frame", _ladder_doc()))
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["ok"] is True and len(j["bars"]) == 8                       # GoCharting untouched
    ux = j["ux"]
    assert ux["why"] is None and len(ux["bars"]) == 2 and "ladder" not in ux["bars"][0]
    assert ux["bars"][0]["exact"] == 1 and ux["bars"][0]["cvd"] == 1 and ux["bars"][1]["cvd"] == 0
    assert ux["bars"][0]["poc"] == 100.0 and ux["bars"][0]["partial"] is False
    assert ux["levels"]["session"]["poc"] == 100.0 and ux["levels"]["why"] is None
    assert ux["lot"] == 65 and ux["lot_src"] == "given" and ux["frames_per_s"] is not None
    assert ux["marks"]["runs"] == [] and isinstance(ux["marks"]["runs_why"], str)
    assert ux["impact"]["tag"] == "I" and isinstance(ux["impact"]["why"], str)
    ag = ux["agree"]
    assert ag["tag"] == "M" and ag["bars_joined"] == 2 and ag["poc_rows_median"] == 0 and ux["agree_why"] is None


def test_api_tape_ux_without_gocharting_stands_alone(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    _ux_seed()
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["ok"] is True and j["src"] == "file" and j["bars"] == [] and j["rowSize"] == 5
    assert j["levels"]["why"] == "no GoCharting record for NIFTY on 2026-09-11 — ux stands alone"
    assert j["ux"]["agree"] is None
    assert j["ux"]["agree_why"] == "GoCharting record absent for this day — ux stands alone, flags on the default grid"
    assert len(j["ux"]["bars"]) == 2


def test_api_tape_neither_record_is_still_the_third_sentence(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-11")
    server.Handler.do_GET(cap)
    assert cap.sent["ok"] is False and "no prints record for NIFTY on 2026-09-11" in cap.sent["why"]


def _write_ux_bar(day, idx, t, lot_src):
    import ux_log
    bar = {"t": t, "o": 100.0, "h": 100.0, "l": 100.0, "c": 100.0, "vol": 1, "buy": 1, "sell": 0,
           "unknown": 0, "unpriced": 0, "delta": 1, "oi": None, "fromTicks": True, "ladder": [],
           "rowSize": None, "rowAnchor": 0, "lot": 65, "lot_src": lot_src, "lot_why": None,
           "tick": 0.05, "tick_src": "given", "frames": 1, "exact": 1, "reconstructed": 0,
           "hidden": 0, "vtt_resets": 0, "lot_mismatch": 0, "levels_seen": 2,
           "partial": False, "partial_why": None, "src": "ux", "idx": idx, "day": day}
    ux_log._write_lines(ux_log.day_path(day, idx), [bar])


def test_api_tape_ux_lot_why_fires_only_when_the_lot_is_gcd_inferred(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    _write_ux_bar("2026-09-13", "NIFTY", 1757563500000, "gcd")
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-13")
    server.Handler.do_GET(cap)
    ux = cap.sent["ux"]
    assert ux["lot_src"] == "gcd"
    assert ux["lot_why"] == "lot inferred by gcd -- vol_ratio is not yet a measurement of the feed"


def test_api_tape_ux_lot_why_is_none_when_the_lot_came_from_the_dump(tmp_path, monkeypatch):
    _isolate_ux(tmp_path, monkeypatch)
    _write_ux_bar("2026-09-14", "NIFTY", 1757563500000, "dump")
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-14")
    server.Handler.do_GET(cap)
    ux = cap.sent["ux"]
    assert ux["lot_src"] == "dump" and ux["lot_why"] is None


def test_api_tape_ux_lot_why_names_a_lotless_day(tmp_path, monkeypatch):
    """No lot inferred yet (no traded volume) is not the gcd day -- it gets
    the bar's own `lot_why`, not the gcd sentence."""
    _isolate_ux(tmp_path, monkeypatch)
    import ux_log
    bar = {"t": 1757563500000, "o": None, "h": None, "l": None, "c": None, "vol": 0, "buy": 0, "sell": 0,
           "unknown": 0, "unpriced": 0, "delta": 0, "oi": None, "fromTicks": True, "ladder": [],
           "rowSize": None, "rowAnchor": 0, "lot": None, "lot_src": None,
           "lot_why": "no traded volume yet to infer a lot from",
           "tick": 0.05, "tick_src": "given", "frames": 1, "exact": 0, "reconstructed": 0,
           "hidden": 0, "vtt_resets": 0, "lot_mismatch": 0, "levels_seen": 2,
           "partial": False, "partial_why": None, "src": "ux", "idx": "NIFTY", "day": "2026-09-16"}
    ux_log._write_lines(ux_log.day_path("2026-09-16", "NIFTY"), [bar])
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-16")
    server.Handler.do_GET(cap)
    ux = cap.sent["ux"]
    assert ux["lot"] is None and ux["lot_src"] is None
    assert ux["lot_why"] == "no traded volume yet to infer a lot from"


def test_api_tape_ux_lot_why_says_mixed_when_the_days_bars_disagree_on_source(tmp_path, monkeypatch):
    """A day that crossed a dump outage: earlier bars landed at gcd, later
    ones once the dump came back -- the LAST bar's lot_src alone would hide
    that the bars are not one unit, so the mixed sentence overrides it (worse
    than the plain gcd sentence, which it takes priority over)."""
    _isolate_ux(tmp_path, monkeypatch)
    _write_ux_bar("2026-09-17", "NIFTY", 1757563500000, "gcd")
    _write_ux_bar("2026-09-17", "NIFTY", 1757563500000 + 300_000, "dump")
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-17")
    server.Handler.do_GET(cap)
    ux = cap.sent["ux"]
    assert ux["lot_src"] == "dump"          # the last bar's, as before
    assert ux["lot_why"] == ("mixed lot provenance across the day's bars: dump, gcd"
                             " — the bars are not in one unit")


def test_api_tape_ux_agree_why_when_no_ux_bar_shares_a_t_with_gocharting(tmp_path, monkeypatch):
    """Both records exist for the day, but at disjoint `t`s -- GoCharting's bars
    shifted one day later than the ux bars' own default `t`s (_ux_seed's), each
    filed under 2026-09-15 so the join has two non-empty sides and zero overlap."""
    _isolate_ux(tmp_path, monkeypatch)
    doc = _tape(n=2)
    for b in doc["closed"]:
        b["t"] += 86_400_000
        b["ladder"] = [{"p": 100.0, "b": 1, "s": 1, "bt": 1, "st": 1}]
    doc["session"] = "NIFTY-I|5m|2026-09-15"
    doc["rowAnchor"] = 0
    server.Handler.do_POST(_Req("/api/frame", doc))
    _ux_seed(day="2026-09-15")
    cap = _Cap("/api/tape?idx=NIFTY&day=2026-09-15")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["ux"]["agree"] is None
    assert j["ux"]["agree_why"] == "no GoCharting bar shares a t with any ux bar — nothing to compare"


def test_the_frame_door_refuses_another_sites_post_and_admits_the_extension(tmp_path, monkeypatch):
    """P1-07: sw.js posts cross-site from its chrome-extension:// origin; a web page's cross-site
    POST is refused before anything is stored or recorded. No header at all (curl) passes."""
    _isolate(tmp_path, monkeypatch)

    def post(headers):
        req = _Req("/api/frame", _ladder_doc())
        req.headers.update(headers)
        server.Handler.do_POST(req)
        return req.out[-1]
    code, j = post({"Sec-Fetch-Site": "cross-site", "Origin": "https://evil.example", "Sec-Fetch-Mode": "no-cors"})
    assert code == 403 and j["ok"] is False and "another site" in j["why"]
    assert "NIFTY" not in server._SENSES["tape"]
    for h in ({"Sec-Fetch-Site": "cross-site", "Origin": "chrome-extension://abcdefghijklmnopabcdefghijklmnop"},
              {"Sec-Fetch-Site": "none", "Origin": "chrome-extension://abcdefghijklmnopabcdefghijklmnop"},
              {"Sec-Fetch-Site": "none"}, {"Sec-Fetch-Site": "same-origin"}, {"Sec-Fetch-Site": "same-site"}, {}):
        code, j = post(h)
        assert code == 200 and j["ok"] is True, h


def test_the_frame_carries_the_upstox_oi_reference(tmp_path, monkeypatch):
    """P1-05: the last UX_OI_N Upstox ladder bars' {t, oi} ride the frame for the extension's
    contract match, with their why when the ladder has no closed bar."""
    _isolate(tmp_path, monkeypatch)
    t0 = 1757563500000
    monkeypatch.setattr(server, "_ux_bars", lambda idx, day: [{"t": t0 + i * 300000, "oi": 11_654_500 + i, "vol": 3} for i in range(30)])
    req = _Req("/api/frame", _ladder_doc())
    server.Handler.do_POST(req)
    j = req.out[-1][1]
    assert len(j["ux_oi"]) == server.UX_OI_N and j["ux_oi"][-1] == {"t": t0 + 29 * 300000, "oi": 11_654_529} and j["ux_oi_why"] is None
    monkeypatch.setattr(server, "_ux_bars", lambda idx, day: [])
    req = _Req("/api/frame", _ladder_doc())
    server.Handler.do_POST(req)
    assert req.out[-1][1]["ux_oi"] is None and req.out[-1][1]["ux_oi_why"] == "no closed Upstox ladder bar yet"


def test_api_vpin_is_blind_off_nifty_with_the_lot_count(monkeypatch):
    """P1-02: the gauge is on the NIFTY future only; SENSEX reads could-not-check with its lots."""
    monkeypatch.setattr(server, "_ux_bars", lambda idx, day: [{"t": 1, "vol": 8.0}])
    cap = _Cap("/api/vpin?idx=SENSEX")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["ok"] is True and j["series"] is None and j["state"] == {} and j["inst"] == "SENSEX-FUT"
    assert j["why"] == "could not check — SENSEX future, 8 lots this bucket"
    monkeypatch.setattr(server, "_ux_bars", lambda idx, day: [])
    cap = _Cap("/api/vpin?idx=SENSEX")
    server.Handler.do_GET(cap)
    assert cap.sent["why"] == "could not check — SENSEX future: no closed ladder bar yet"
