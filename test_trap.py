"""trap.py / trap_log.py -- the trap layer (rev trap-1, docs/board/TRAP-PREREG-2026-10-04.md).

Pinned on Thu 2026-10-01 from two frozen fixtures: the sides grid (sides_2026-10-01.json.gz) and
the trap inputs (trap_2026-10-01.json.gz: warmap stamps, reader legs, xindex, NIFTY tape, pulled,
oi_prev). The rules were fixed 2026-10-04 02:11 IST; a failing test means a rule moved.

Nothing here tests that a read is RIGHT about the market (CLAUDE.md rule 9).
"""
import gzip
import json
import os
from datetime import datetime

import trap
import trap_log
from test_sides import _load, _read

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "test", "fixtures", "trap_2026-10-01.json.gz")
_F = {}


def _fx():
    if not _F:
        with gzip.open(FIX, "rt", encoding="utf-8") as f:
            _F.update(json.load(f))
    return _F


def _trap(idx, **kw):
    fx = _fx()
    d = fx["idx"][idx]
    minutes, opens, book, kal = _load(idx)
    fp = next(minutes[t]["spot"] for t in sorted(minutes) if minutes[t].get("spot") is not None)
    prev = {float(k): {s: tuple(v[s]) for s in ("ce", "pe")} for k, v in d["oi_prev"].items()}
    args = dict(first_print=fp, legs=d["legs"], xin=fx["xin"], tape=d["tape"], pulled=d["pulled"],
                oi_prev=prev, book=book)
    args.update(kw)
    return trap.read(idx, fx["stamps"], _read(idx), **args)


def _ev(out, level, state):
    return [e for e in out["events"] if e["level"] == level and e["state"] == state]


def test_nifty_pdl_is_a_gap_induce_at_the_open_and_pdc_is_reached_1001_never_broken():
    out = _trap("NIFTY")
    g = _ev(out, "PDL", "INDUCED")[0]
    assert g["t"] == "09:15:00" and g["gap"] and g["dir"] == "DOWN"
    # pre-registered FAILED needs price back THROUGH the level by a band: NIFTY's 09:24 reversal stopped
    # under PDL, so the rules read no failure there (the narrative's "failed" is the low reversing)
    assert not [e for e in _ev(out, "PDL", "FAILED") if e["t"] < "09:30:00"]
    assert _ev(out, "PDC", "REACHED")[0]["t"].startswith("10:01")
    assert not _ev(out, "PDC", "INDUCED") and not _ev(out, "PDC", "FAILED")       # PDC never broken


def test_sensex_pdc_induced_1007_failed_1013():
    out = _trap("SENSEX")
    assert _ev(out, "PDC", "INDUCED")[0]["t"].startswith("10:07") and _ev(out, "PDC", "INDUCED")[0]["dir"] == "UP"
    assert _ev(out, "PDC", "FAILED")[0]["t"].startswith("10:13")
    assert _ev(out, "PDC", "INDUCED")[0]["x2_verdict"] is not None               # xindex X2 logged at the induce


def test_the_release_1210_travels_with_new_shorts_on_the_1213_1259_leg():
    out = _trap("NIFTY")
    r = next(x for x in out["releases"] if "12:00" <= x["from"] and x["t"] <= "12:10")
    assert (r["t"], r["level"], r["dir"], r["loaded"], r["forced"]) == ("12:10", "OPEN", -1, "ce", 2)
    assert (r["who"], r["who_word"], r["who_leg"]) == ("new_shorts", "chalega", "12:13–12:59")
    assert r["act"] == "PE kaat ×9"                                            # the side that made it POWER, in her words
    assert next(x for x in _trap("SENSEX")["releases"] if x["t"] == "12:25")["act"] == "CE likh ×4 · PE kaat ×4"
    assert r["tape_with"] is not None and r["tape_why"] is None                  # NIFTY: raw tape fields
    tv = _ev(out, "OPEN", "TRAVELLING")[0]
    assert tv["t"].startswith("12:10") and tv["target"]["px"] == 22500.0 and tv["who"] == "new_shorts"
    s = _trap("SENSEX")
    assert all(x["tape_with"] is None and x["tape_why"] == trap.TAPE_THIN for x in s["releases"])
    lines = out["lines"]
    assert lines["trap"] and lines["chhoota"].startswith(("▼", "▲", "koi release"))


def test_oi_prev_shows_yesterdays_book_without_touching_the_0915_baseline():
    out = _trap("NIFTY")
    s = next(x for x in out["slots"] if x["t"] == "09:20")
    assert s["prev_oi_top2_pe"] and s["prev_underwater_pe"] in (0, 1, 2)
    assert _trap("NIFTY", oi_prev=None)["slots"][0]["prev_oi_top2_pe"] is None


def test_an_open_slot_and_a_future_stamp_are_never_read():
    out = _trap("NIFTY", now="12:10")
    assert all(e["t"] < "12:10:00" for e in out["events"]) and out["slots"][-1]["t"] == "12:05"


def test_a_restart_replay_supersedes_the_earlier_process_and_is_never_counted_twice(tmp_path):
    w = tmp_path / "warmap"
    w.mkdir()
    row = lambda ts, to="APPROACH": json.dumps({"idx": "NIFTY", "level": "PDC", "px": 22600.0, "to": to,
                                                 "ts": f"2026-10-01T{ts}"})
    # process 1 observed 09:22 and 09:40; process 2 replayed to 10:05 (twice: a third start replayed again)
    (w / "warmap_2026-10-01.jsonl").write_text("\n".join([row("09:22:10"), row("09:40:05", "DWELL"),
                                                          row("10:21:30", "BREAK")]) + "\n")
    (w / "warmap_2026-10-01_backfill.jsonl").write_text("\n".join([row("09:22:00"), row("09:40:00", "DWELL"),
                                                                   row("09:22:00"), row("09:41:00", "DWELL"),
                                                                   row("10:05:00", "REJECT")]) + "\n")
    st = trap_log.Day("2026-10-01", root=str(tmp_path)).stamps()
    assert [(r["ts"][11:], r.get("backfill", False)) for r in st] == [
        ("09:22:00", True), ("09:41:00", True), ("10:05:00", True), ("10:21:30", False)]


def test_the_trap_log_guard_and_once_only(tmp_path):
    d, day = str(tmp_path), "2026-10-01"
    rows = [{"kind": "state", "t": "12:10:12", "key": "12:10:12|OPEN@22543.7|INDUCED", "state": "INDUCED"},
            {"kind": "state", "t": "12:10:12", "key": "12:10:12|OPEN@22543.7|TRAVELLING", "state": "TRAVELLING"},
            {"kind": "slot", "t": "12:10", "src": "live"}]

    def at(hm, dd=1):
        return datetime(2026, 10, dd, int(hm[:2]), int(hm[3:]), 30)
    assert trap_log.append(day, "NIFTY", rows, at("09:14"), d) == 0
    assert trap_log.append(day, "NIFTY", rows, at("15:31"), d) == 0
    assert trap_log.append(day, "NIFTY", rows, at("00:00", 2), d) == 0
    assert trap_log.append("2026-09-30", "NIFTY", rows, at("12:30"), d) == 0
    assert trap_log.append(day, "NIFTY", rows, at("12:11"), d) == 3             # two states at one time: two keys
    assert os.listdir(d) == ["trap_2026-10-01.jsonl"]
    assert trap_log.append(day, "NIFTY", rows, at("12:12"), d) == 0             # once
    import sides_log
    sides_log._SEEN.clear()
    assert trap_log.append(day, "NIFTY", rows, at("12:20"), d) == 0             # a restart re-reads the file
