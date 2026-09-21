"""The nightly table: every §D field, its why when null, and never a verdict."""
import sys
import os

import tape_log
import ux_log
from test_frame_api import _ladder_doc, _ux_seed

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
