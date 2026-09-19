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
