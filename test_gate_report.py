"""The nightly table: every §D field, its why when null, and never a verdict."""
import sys
import os
import json
import time

import book_log
import tape_log
import ux_log
from test_frame_api import _ladder_doc, _ux_seed
from test_ladder import R, T0

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import gate_report  # noqa: E402


def test_report_prints_every_session_field_and_no_verdict(capsys):
    doc = _ladder_doc()
    tape_log.append(doc, "2026-09-11", "NIFTY")
    _ux_seed()
    ux_log._STATE.clear()
    assert gate_report.main("NIFTY", "2026-09-11") == 0
    out = capsys.readouterr().out
    for k in ("bars_joined", "poc_rows_median", "poc_within_1", "delta_sign_agree", "vol_ratio_median",
              "va_overlap", "hvn_jaccard", "lvn_jaccard", "exact_frac", "hidden_frac", "unknown_frac"):
        assert k in out, k
    assert "[M]" in out
    low = out.lower()
    assert "pass" not in low and "fail" not in low and "verdict" not in low


def test_report_says_which_record_is_missing(capsys):
    assert gate_report.main("NIFTY", "2026-09-11") == 2
    out = capsys.readouterr().out
    assert "no GoCharting record for NIFTY on 2026-09-11" in out and "no ux record for NIFTY on 2026-09-11" in out


def test_an_empty_book_file_gets_its_own_sentence(capsys):
    """Rule 6: a book file that exists but closes no bar is "checked, nothing",
    not "could not check"."""
    import os
    import book_log
    p = book_log.day_path("2026-09-11", "NIFTY")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").close()
    assert gate_report.main("NIFTY", "2026-09-11") == 2
    out = capsys.readouterr().out
    assert "the book file holds no frame that closes a bar" in out and "no book file" not in out


def test_against_today_the_open_bin_is_left_alone_and_the_sentence_prints(capsys):
    """Run against TODAY, live server or not: rebuild must not close the bin
    the book file ends inside (§ "no second writer can land the open bin") --
    the rebuild's `close_last` follows `day == today`, and the table gets one
    more line saying why the day looks short."""
    day = time.strftime("%Y-%m-%d")
    tape_log.append(_ladder_doc(day=day), day, "NIFTY")

    # bin 0 closes (the frame at T0+300_500 crosses into bin 1); bin 1 then
    # takes one more frame and the file ends there, still open.
    rows = [R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 300_500, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 320_000, 1130, 100.05, 65, [[100.00, 65]], [[100.05, 65]])]
    p = book_log.day_path(day, "NIFTY")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    before = ux_log.read_bars(day, "NIFTY")
    assert before == []                          # nothing landed yet
    assert gate_report.main("NIFTY", day, 65, 0.05) == 0
    out = capsys.readouterr().out
    assert ("the last bin is still open — its frames are not in a closed bar "
            "yet; run again after close for the full day") in out

    after = ux_log.read_bars(day, "NIFTY")
    assert [b["t"] for b in after] == [T0]        # bin 0 only -- bin 1 (open) never landed


def test_against_a_past_day_the_last_bin_always_lands(capsys):
    """A day that has since rolled: the book file's last bin was never
    followed by a closing frame while the server was running that day (the
    day rolled first), so the LIVE stream -- close_last=False -- left it
    open forever. gate_report against a PAST day must always rebuild
    (dropping the `not ux` guard for that branch), landing the one bin only
    `close_last=True` ever closes -- and write-once (`_land`'s `seen`) makes
    the call idempotent when bin 0 was already landed by a prior process."""
    day = "2026-08-01"
    tape_log.append(_ladder_doc(day=day), day, "NIFTY")

    # bin 0 closes at the frame crossing into bin 1; bin 1 then takes one
    # more frame and the book file ends there, still open -- exactly what a
    # day roll leaves behind.
    rows = [R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 300_500, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 320_000, 1130, 100.05, 65, [[100.00, 65]], [[100.05, 65]])]
    p = book_log.day_path(day, "NIFTY")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    # the server-style path first: only bin 0 lands, bin 1 is left for a
    # stream that will never come (the day already rolled).
    ux_log.state("NIFTY", day, 65, 0.05)
    ux_log.rebuild(day, "NIFTY", 65, 0.05, close_last=False)
    assert [b["t"] for b in ux_log.read_bars(day, "NIFTY")] == [T0]
    ux_log._STATE.clear()

    assert gate_report.main("NIFTY", day, 65, 0.05) == 0
    after = ux_log.read_bars(day, "NIFTY")
    assert [b["t"] for b in after] == [T0, T0 + 300_000]      # bin 1 now lands
    assert len([b for b in after if b["t"] == T0 + 300_000]) == 1  # exactly once


def test_todays_sentence_prints_even_when_the_day_is_reported_incomplete(capsys):
    """An early-session run against TODAY, before any record exists: exit 2
    (both records missing) must still explain itself -- the open-bin
    sentence, not just the two "missing" lines."""
    day = time.strftime("%Y-%m-%d")
    assert gate_report.main("NIFTY", day) == 2
    out = capsys.readouterr().out
    assert f"no GoCharting record for NIFTY on {day}" in out
    assert f"no ux record for NIFTY on {day}" in out
    assert ("the last bin is still open — its frames are not in a closed bar "
            "yet; run again after close for the full day") in out


def test_lot_falls_back_to_gocharting_when_the_dump_has_none(monkeypatch, capsys):
    """No LOT on the command line and no dump: `main` must resolve the SAME
    lot the server would have used (spec §B/§J.12's second fallback) and
    write the ux bars at that unit, not at gcd -- and the printed line names
    the source."""
    day = "2026-08-03"
    doc = _ladder_doc(day=day)
    doc["lot"] = 75
    tape_log.append(doc, day, "NIFTY")
    monkeypatch.setattr(gate_report.upstox_instruments, "lot_tick",
                        lambda idx: (_ for _ in ()).throw(Exception("no dump")))

    rows = [R(T0 + 1000, 1000, 100.00, 65, [[100.00, 65]], [[100.05, 65]]),
            R(T0 + 300_500, 1065, 100.05, 65, [[100.00, 65]], [[100.05, 65]])]
    p = book_log.day_path(day, "NIFTY")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    assert gate_report.main("NIFTY", day) == 0
    out = capsys.readouterr().out
    assert "lot 75 (ofd)" in out

    rows_written = ux_log.read_bars(day, "NIFTY")
    assert rows_written and all(r.get("lot_src") == "ofd" for r in rows_written)
