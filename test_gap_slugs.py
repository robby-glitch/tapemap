"""tools/gap_slugs.py lists, never rewrites: the ux bars a feed gap turned into a slug (25 Oct review, A67)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import gap_slugs  # noqa: E402


def test_lists_a_gap_with_volume_and_skips_a_clean_pair(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs("data/book")
    os.makedirs("data/tape")
    T0 = 1789098300000                                     # 09:15:00 IST
    rows = [{"t": T0 + 1000, "cts": T0 + 1000, "ltt": T0 + 1000, "vtt": 1000},
            {"t": T0 + 2000, "cts": T0 + 2000, "ltt": T0 + 2000, "vtt": 1065},      # clean: 1 s
            {"t": T0 + 92_000, "cts": T0 + 92_000, "ltt": T0 + 92_000, "vtt": 14_975}]  # 90 s gap
    with open("data/book/book_NIFTY_2026-09-11.jsonl", "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))
    with open("data/tape/ux_NIFTY_2026-09-11.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"t": T0, "delta": 215, "vol": 216}) + "\n")
    gap_slugs.main(set())
    out = capsys.readouterr().out.splitlines()
    assert out[2:] == ["| 2026-09-11 | NIFTY | 09:15 | 90s | 13910 | 215 | 216 |"]
