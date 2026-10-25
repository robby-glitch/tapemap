"""tools/messages_replay.py: a day's stream rebuilt READ-ONLY from its READ and DECODE logs, the Telegram lines marked TG."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import messages_replay  # noqa: E402


def test_rebuilds_the_day_and_marks_the_telegram_lines(tmp_path, capsys):
    read = [{"kind": "mark", "idx": "NIFTY", "t": "09:50", "word": "WAIT", "dir": 0},
            {"kind": "mark", "idx": "NIFTY", "t": "09:55", "word": "LEAN", "dir": -1, "flip": 22800.0, "since": "09:55"}]
    dec = [{"idx": "NIFTY", "T": "09:55", "call": {"text": "▼ leg jaari · 5/7", "kind": "JAARI", "d": 0, "c": 5, "of": 7,
                                                   "signs": []}, "leg": {"d": -1, "ext": {}}, "setups": []}]
    for sub, rows in (("read", read), ("decode", dec)):
        os.makedirs(tmp_path / sub)
        (tmp_path / sub / f"{sub}_2026-10-23.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    assert messages_replay.main("2026-10-23", data=str(tmp_path)) == 0
    out = capsys.readouterr().out.splitlines()
    assert "TG 09:55  NIFTY  WAIT → LEAN ▼ · 5/7 saath · flip 22,800s" in out
    assert "   09:55  NIFTY  ▼ leg jaari · 5/7 saath" in out
    assert any(x.startswith("READ 1 · LEG 1 · SETUP 0 · DIN 0 · TG 1") for x in out)
    assert messages_replay.main("2026-10-22", data=str(tmp_path)) == 1         # no logs: said, not an empty stream
