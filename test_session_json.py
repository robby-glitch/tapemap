"""session_json() must emit every FUT bar, even when an option leg is missing.

The old behaviour intersected the FUT series with ATM option availability:
a minute where the CE or PE did not print silently deleted a future bar we
actually have. Harmless for the three-book view, wrong for an index-only
chart (Tape Chart Phase 1) — and dishonest either way: the bar existed.
"""
from types import SimpleNamespace

from engine import session_json


def _bar(t, px, oi=1000, v=50):
    return {"T": t, "O": px, "H": px + 2, "L": px - 2, "C": px + 1,
            "VWAP": px, "U1": px + 5, "D1": px - 5, "U2": px + 10,
            "D2": px - 10, "U3": px + 15, "D3": px - 15,
            "OI": oi, "V": v, "f": {"z": 0.5, "vol_r": 0.4}}


def _sess(fut_ts, ce_ts, pe_ts):
    piv = {"P": 100.0, "R1": 105.0, "R2": 110.0, "R3": 115.0,
           "S1": 95.0, "S2": 90.0, "S3": 85.0}
    fut = [dict(_bar(t, 100.0), **piv) for t in fut_ts]
    return SimpleNamespace(
        day="TEST", strike=100.0, fut_bars=fut, events=[],
        books={"FUT": SimpleNamespace(bars=fut),
               "CE": SimpleNamespace(bars=[_bar(t, 10.0) for t in ce_ts]),
               "PE": SimpleNamespace(bars=[_bar(t, 12.0) for t in pe_ts])},
        gamma=SimpleNamespace(track={}), ctx_track={}, setup_track={})


def test_missing_option_leg_keeps_fut_bar():
    s = _sess(fut_ts=["09:15", "09:16", "09:17"],
              ce_ts=["09:15", "09:17"],           # CE skipped 09:16
              pe_ts=["09:15", "09:16", "09:17"])
    bars = session_json(s)["bars"]
    assert [b["t"] for b in bars] == ["09:15", "09:16", "09:17"]
    gap = bars[1]
    assert gap["fut"]["c"] == 101.0               # the FUT data we actually have
    assert gap["ce"] is None                      # missing leg is explicit, not faked
    assert gap["pe"] is not None


def test_complete_rows_unchanged():
    s = _sess(fut_ts=["09:15", "09:16"],
              ce_ts=["09:15", "09:16"],
              pe_ts=["09:15", "09:16"])
    bars = session_json(s)["bars"]
    assert len(bars) == 2
    for b in bars:
        for leg in ("fut", "ce", "pe"):
            assert b[leg]["o"] is not None
            assert set(b[leg]) >= {"o", "h", "l", "c", "vwap", "u1", "d1",
                                   "u2", "d2", "u3", "d3", "oi", "v", "z"}
