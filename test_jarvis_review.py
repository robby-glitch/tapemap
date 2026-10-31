"""tools/jarvis_review.py: the evening sheet -- what Jarvis said today, her trades against it, counts only."""
import json
import os
import sys

import day_state

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import jarvis_review  # noqa: E402

DAY = "2026-10-29"


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def _shown(t):                                   # a row for minute t is first on her screen ~1:20 later
    m = int(t[:2]) * 60 + int(t[3:]) + 1
    return f"{m // 60:02d}:{m % 60:02d}:20"


def _toy(tmp_path, pause=True):
    d = tmp_path / "jarvis"
    d.mkdir()
    words = [("10:00", "TREND ▼", 23010.0), ("10:01", "TREND ▼", 23000.0), ("10:02", "PALAT? ▼", 23005.0),
             ("10:03", "PALAT? ▼", 23008.0), ("10:04", "TREND ▼", 22995.0), ("10:05", "TREND ▼", 22990.0)]
    _jsonl(d / f"call_{DAY}.jsonl", [
        {"day": DAY, "idx": "NIFTY", "t": t, "shown": _shown(t), "word": w, "state": "HOLD", "lean": -1, "since": "10:00",
         "count": {"with": 4, "against": 1, "N": 6}, "fut": f, "spot": f - 43, "blind": t == "10:04"} for t, w, f in words])
    if pause:
        _jsonl(d / f"pause_{DAY}.jsonl", [{"t": "10:02", "i": 2, "word": "HOLD", "alive": [], "risk": [], "missing": [],
                                            "at3": None, "after": {"outcome": "CONT", "t": "10:05", "min": 3},
                                            "day": DAY, "idx": "NIFTY", "rev": "x"}])
    _jsonl(d / f"cmd_{DAY}.jsonl", [
        {"at": 1, "t": "10:01:05", "idx": "NIFTY", "kind": "watch", "text": "watch 22800s", "ok": True,
         "reply": "watching 22,800s (1 of 10 today)", "src": "cli"},
        {"kind": "watch_hit", "id": 1, "idx": "NIFTY", "t": "10:05", "px": 22800.4, "frame": "s",
         "card": {"word": "TREND ▼", "count": {"with": 4, "against": 1}, "answer": None}}])
    day_state.save(DAY, {"hold_trades": [{"id": "NIFTY-23000PE-long-100130", "idx": "NIFTY", "k": 23000.0, "side": "PE",
                                          "role": "long", "t0": "10:01:30", "p0": 174.85, "qty": 0, "exit_t": "10:04:10"}]})
    return d


def test_the_sheet_on_a_toy_day(tmp_path):
    d = _toy(tmp_path)
    p = jarvis_review.run(DAY, data_dir=str(d))
    assert p == os.path.join(str(d), f"review_{DAY}.md")
    s = _read(p)
    assert "NIFTY · word changes: 2" in s
    assert "10:00 TREND ▼ (2 min) → 10:02 PALAT? ▼ (2 min) → 10:04 TREND ▼ (2 min)" in s
    assert "NIFTY · PALAT? said 1× · came true 0×" in s
    assert "NIFTY · blind 1 min · 10:04" in s
    # the rows ON HER SCREEN: at 10:01:30 the 10:00 row (shown 10:01:20); at 10:04:10 the 10:02 row (the 10:03 row shows
    # at 10:04:20, the 10:04 row at 10:05:20) -- never the minute she clicked in
    assert ("NIFTY 23000 PE long @174.85 · in 10:01:30 TREND ▼ (WITH 4 · AGAINST 1) · out 10:04:10 PALAT? ▼"
            " · fut 23,010.0f → 23,005.0f · +5.0 pts her way") in s
    assert "watches set 1 · hit 1" in s
    assert "10:01 NIFTY set watch 22800s" in s and "10:05 NIFTY hit 22,800.4s · id 1" in s
    assert "pauses 1 · CONT 1 · REV 0 · UNRESOLVED 0 · window open 0" in s
    assert "every input was on disk" in s
    assert "%" not in s


def test_no_look_ahead_a_stale_row_gaps_and_a_null_word(tmp_path):
    d = tmp_path / "jarvis"
    d.mkdir()
    rows = [("10:00", "TREND ▲"), ("10:01", "TREND ▲"), ("10:02", "HOLD ▲"), ("10:06", "HOLD ▲"), ("10:07", "HOLD ▲"),
            ("10:08", None), ("10:09", "HOLD ▲")]           # no `shown`: an older row shape; 10:03-10:05 not on the record
    _jsonl(d / f"call_{DAY}.jsonl", [{"idx": "NIFTY", "t": t, "word": w, "count": {"with": 3, "against": 2},
                                      "fut": 23000.0 + i} for i, (t, w) in enumerate(rows)])
    _jsonl(d / f"cmd_{DAY}.jsonl", [{"kind": "watch_hit", "id": 2, "t": "10:07", "px": 22800.4}])
    day_state.save(DAY, {"hold_trades": [{"idx": "NIFTY", "k": 23000.0, "side": "CE", "role": "long", "t0": "10:02:30",
                                          "p0": 120.0, "exit_t": "10:05:30"}]})
    s = _read(jarvis_review.run(DAY, data_dir=str(d)))
    assert "NIFTY · word changes: 1" in s                                     # TREND → HOLD; the null stretch is not a change
    assert ("10:00 TREND ▲ (2 min) → 10:02 HOLD ▲ (gap 10:03–10:05) → 10:08 could not check — no word (1 min)"
            " → 10:09 HOLD ▲ (1 min)") in s
    trade = next(x for x in s.splitlines() if x.startswith("- NIFTY 23000 CE long"))
    # in at 10:02:30: a row without `shown` counts from the minute before hers (10:01), never 10:02's HOLD
    assert "in 10:02:30 TREND ▲ (WITH 3 · AGAINST 2)" in trade
    assert "out 10:05:30 could not check — no call row near 10:05 (last 10:02)" in trade
    assert "pts her way" not in trade and "fut points could not check — no call row on her screen at both ends" in trade
    assert "10:07 index not logged hit frame not logged · id 2" in s and "22,800.4" not in s   # never an untagged price


def test_the_sheet_is_read_only_on_her_marks_file(tmp_path):
    d = tmp_path / "jarvis"
    p = day_state.path_for(DAY)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("{torn")
    s = _read(jarvis_review.run(DAY, data_dir=str(d)))
    assert "could not check — the marks file did not read" in s
    assert _read(p) == "{torn"                                                # left where it was, byte for byte


def test_an_absent_pause_log_is_named(tmp_path):
    d = _toy(tmp_path, pause=False)
    s = _read(jarvis_review.run(DAY, data_dir=str(d)))
    assert "could not check — no pause log" in s
    assert "NIFTY · word changes: 2" in s                                     # the rest still reads


def test_nothing_on_disk_says_so_line_by_line(tmp_path):
    d = tmp_path / "jarvis"
    s = _read(jarvis_review.run(DAY, data_dir=str(d)))
    for what in ("no call log", "no pause log", "no command log", "no marks file"):
        assert f"could not check — {what}" in s
    assert "word changes: 0" not in s and "came true 0" not in s             # absent is never a zero
