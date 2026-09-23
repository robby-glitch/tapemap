"""A week-old day kept as .jsonl.gz reads exactly like the plain file (daylog.py, 2026-09-23)."""
import json

import book_log
import daylog
import record_read


def test_the_book_record_reads_the_same_day_once_compressed(tmp_path, monkeypatch):
    monkeypatch.setattr(book_log, "DIR", str(tmp_path))
    p = tmp_path / "book_NIFTY_2026-09-01.jsonl"
    p.write_text("".join(json.dumps({"t": i, "ltp": float(i)}) + "\n" for i in range(1, 4)), encoding="utf-8")
    plain = list(book_log.read_rows("2026-09-01", "NIFTY"))
    assert daylog.compress_old("2026-09-23", dirs=(str(tmp_path),))[0] == 1 and not p.exists()
    assert daylog.exists(str(p)) and list(book_log.read_rows("2026-09-01", "NIFTY")) == plain == \
        [{"t": 1, "ltp": 1.0}, {"t": 2, "ltp": 2.0}, {"t": 3, "ltp": 3.0}]


def test_the_frame_record_reads_the_same_day_once_compressed(tmp_path):
    p = tmp_path / "frame_2026-09-01.jsonl"
    p.write_text("".join(json.dumps({"day": "2026-09-01", "idx": "NIFTY", "ts": f"09:{35 + i}", "setup": {},
                                     "tape": {"events": [{"t": i, "kind": "run", "p": 1.0}]}}) + "\n"
                         for i in range(3)), encoding="utf-8")
    plain = record_read.read("2026-09-01", "NIFTY", path=str(p))
    assert plain[0]                                              # the plain day reads rows
    assert daylog.compress_old("2026-09-23", dirs=(str(tmp_path),))[0] == 1 and not p.exists()
    assert record_read.read("2026-09-01", "NIFTY", path=str(p)) == plain


def test_today_and_the_last_week_are_never_compressed(tmp_path):
    for day in ("2026-09-15", "2026-09-16", "2026-09-22", "2026-09-23"):
        (tmp_path / f"senses_{day}.jsonl").write_text('{"t": "09:15:00"}\n', encoding="utf-8")
    daylog.compress_old("2026-09-23", dirs=(str(tmp_path),))
    assert sorted(x.name for x in tmp_path.iterdir()) == [                # 09-16 is 7 days back: kept plain
        "senses_2026-09-15.jsonl.gz", "senses_2026-09-16.jsonl", "senses_2026-09-22.jsonl", "senses_2026-09-23.jsonl"]
