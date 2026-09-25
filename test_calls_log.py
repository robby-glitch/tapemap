"""calls_log: one row per index per engine bar, never twice, even across a restart."""
import json

import calls_log


def _out(idx, t, status="CONTRADICTED"):
    return {"ok": True, "idx": idx, "t": t, "why": None,
            "calls": [{"call": "CAUTION", "kind": "range", "status": status}], "facts": {}}


def test_a_bar_is_written_once_and_a_restart_does_not_write_it_again(tmp_path, monkeypatch):
    monkeypatch.setattr(calls_log, "DIR", str(tmp_path))
    monkeypatch.setattr(calls_log, "_seen", {})
    assert calls_log.append("2026-09-24", "NIFTY", _out("NIFTY", "13:36"), 1.0)
    assert not calls_log.append("2026-09-24", "NIFTY", _out("NIFTY", "13:36", "BACKED"), 2.0)   # first shown wins
    assert calls_log.append("2026-09-24", "SENSEX", _out("SENSEX", "13:36"), 3.0)
    monkeypatch.setattr(calls_log, "_seen", {})                                                   # the restart
    assert not calls_log.append("2026-09-24", "NIFTY", _out("NIFTY", "13:36"), 4.0)
    assert calls_log.append("2026-09-24", "NIFTY", _out("NIFTY", "13:39"), 5.0)
    rows = [json.loads(x) for x in open(calls_log.path("2026-09-24"), encoding="utf-8")]
    assert [(r["idx"], r["t"], r["calls"][0]["status"]) for r in rows] == [
        ("NIFTY", "13:36", "CONTRADICTED"), ("SENSEX", "13:36", "CONTRADICTED"), ("NIFTY", "13:39", "CONTRADICTED")]


def test_a_reply_with_no_engine_bar_is_not_a_row(tmp_path, monkeypatch):
    monkeypatch.setattr(calls_log, "DIR", str(tmp_path))
    monkeypatch.setattr(calls_log, "_seen", {})
    assert not calls_log.append("2026-09-24", "NIFTY", {"ok": False, "t": None, "why": "no engine bar"}, 1.0)
    assert not calls_log.append("2026-09-24", "NIFTY", None, 1.0)
    assert not list(tmp_path.iterdir())
