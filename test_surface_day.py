"""The /api/surface day strip's reader, on a synthetic log where the answer
is arithmetic: open/now/hi/lo picked correctly, other indices and bad lines
ignored, absent file a stated None, and the size-keyed cache actually
invalidating when the log grows."""
import json

import desk_log
import server


def _write(p, rows):
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n",
                 encoding="utf-8")


def _row(t, idx, a, b=-0.5):
    return {"ts": f"2026-08-24T{t}:00", "idx": idx, "a": a, "b": b, "c": 150.0}


def test_day_story_reads_open_now_hi_lo(tmp_path, monkeypatch):
    p = tmp_path / "surface_x.jsonl"
    _write(p, [_row("09:16", "NIFTY", 0.10, -0.9),
               _row("11:32", "NIFTY", 0.124),
               _row("10:00", "BANKNIFTY", 0.99),   # another index, ignored
               _row("15:29", "NIFTY", 0.118, 0.0)])
    monkeypatch.setattr(desk_log, "surface_path", lambda *a, **k: str(p))
    server._SURF_DAY_CACHE.clear()
    d = server._surface_day("NIFTY")
    assert d["n"] == 3
    assert d["open"] == {"t": "09:16", "a": 0.10, "b": -0.9}
    assert d["now"]["t"] == "15:29" and d["now"]["b"] == 0.0
    assert d["hi"] == {"t": "11:32", "a": 0.124}
    assert d["lo"] == {"t": "09:16", "a": 0.10}
    assert len(d["series"]) == 3


def test_absent_file_and_absent_index_are_none(tmp_path, monkeypatch):
    monkeypatch.setattr(desk_log, "surface_path",
                        lambda *a, **k: str(tmp_path / "missing.jsonl"))
    server._SURF_DAY_CACHE.clear()
    assert server._surface_day("NIFTY") is None
    p = tmp_path / "surface_y.jsonl"
    _write(p, [_row("09:16", "BANKNIFTY", 0.12)])
    monkeypatch.setattr(desk_log, "surface_path", lambda *a, **k: str(p))
    assert server._surface_day("NIFTY") is None


def test_cache_invalidates_when_the_log_grows(tmp_path, monkeypatch):
    p = tmp_path / "surface_z.jsonl"
    _write(p, [_row("09:16", "NIFTY", 0.10), _row("09:17", "NIFTY", 0.11)])
    monkeypatch.setattr(desk_log, "surface_path", lambda *a, **k: str(p))
    server._SURF_DAY_CACHE.clear()
    assert server._surface_day("NIFTY")["n"] == 2
    _write(p, [_row("09:16", "NIFTY", 0.10), _row("09:17", "NIFTY", 0.11),
               _row("09:18", "NIFTY", 0.12)])
    assert server._surface_day("NIFTY")["n"] == 3
