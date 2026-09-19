"""tools/seed_tape_from_ofd.py: the one-off that turns a recorded orderflow-desk
export into the ladder record. It REWRITES the files it creates to tag them
src:"seed", so both refusals below protect real rows from that rewrite."""
import importlib.util
import json
import os

import pytest

import tape_log

_spec = importlib.util.spec_from_file_location(
    "seed_tape_from_ofd", os.path.join(os.path.dirname(__file__), "tools", "seed_tape_from_ofd.py"))
seed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed)


def _export(tmp_path, interval="5m", n=2):
    j = {"session": f"NIFTY-I|{interval}|2026-09-11",
         "bars": [{"t": 1757563500000 + i * 300000, "o": 100, "h": 104, "l": 99, "c": 101,
                   "vol": 20, "buy": 12, "sell": 8, "delta": 4, "oi": 1, "fromTicks": False,
                   "ladder": [{"p": 100.0, "b": 9, "s": 1, "bt": 3, "st": 1}]} for i in range(n)],
         "events": [{"t": 1757563500000, "kind": "absorption", "side": 1, "p": 100.0, "size": 9}]}
    p = tmp_path / "export.json"
    p.write_text(json.dumps(j), encoding="utf-8")
    return str(p)


def test_it_refuses_a_day_that_already_has_a_bar_file(tmp_path):
    """The rewrite tags every row src:"seed". Run over a day the extension
    really recorded, it would relabel measurements as a reconstruction."""
    src = _export(tmp_path)
    seed.main(src, "NIFTY")
    before = open(tape_log.day_path("2026-09-11", "NIFTY"), encoding="utf-8").read()
    with pytest.raises(SystemExit) as e:
        seed.main(src, "NIFTY")
    assert "already exists" in str(e.value)
    assert open(tape_log.day_path("2026-09-11", "NIFTY"), encoding="utf-8").read() == before


def test_it_refuses_an_export_that_is_not_five_minute(tmp_path):
    with pytest.raises(SystemExit) as e:
        seed.main(_export(tmp_path, interval="1m"), "NIFTY")
    assert "5-minute" in str(e.value)
    assert not os.path.exists(tape_log.day_path("2026-09-11", "NIFTY"))


def test_the_marks_it_writes_are_tagged_seed_like_the_bars(tmp_path):
    seed.main(_export(tmp_path), "NIFTY")
    bars = tape_log.read_bars("2026-09-11", "NIFTY")
    marks = tape_log.read_marks("2026-09-11", "NIFTY")
    assert bars and all(b["src"] == "seed" for b in bars)
    assert marks and all(m["src"] == "seed" and m["kind"] == "absorption" for m in marks)
