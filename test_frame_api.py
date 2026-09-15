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
        {"expiry": "2026-09-16", "days": [{"zone_state": [{"state": "ARMED"}], "zone_state_sell": []}]}).encode())
    book = server._book_for(req, "NIFTY")
    assert book["zone_state"] == [{"state": "ARMED"}] and book["zone_state_sell"] == []
