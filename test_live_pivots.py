"""live._pivots on an empty prior session: a stated absence, never a crash.
2026-09-07 to 09-15 this raised ValueError on max([]) inside build_session,
which killed both zone machines, trigger_log and the gear reading -- silently."""
import engine
import live


def _cfg():
    return {"under_sym": "NIFTY", "prev_day": "2026-09-14", "fut_id": "1",
            "fut_seg": "NSE_FNO"}


def test_empty_prior_session_yields_none_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(live, "_intraday", lambda *a, **k: {"high": [], "low": [], "close": []})
    live._piv_cache.clear()
    assert live._pivots("tok", _cfg()) is None
    assert ("NIFTY", "2026-09-14") not in live._piv_cache   # a later fetch may still land


def test_bars_without_pivots_carry_bands_and_no_pivot_keys():
    d = {"timestamp": [1757907900, 1757907960], "open": [100.0, 101.0], "high": [101.0, 102.0],
         "low": [99.0, 100.0], "close": [100.5, 101.5], "volume": [10, 12]}
    bars = live._bars(d, None)
    assert len(bars) == 2 and "VWAP" in bars[0] and "D2" in bars[0]
    assert "R1" not in bars[0] and "P" not in bars[0]


def test_session_run_survives_pivotless_bars_end_to_end():
    """The crash this task exists to eliminate happened one frame downstream
    of _pivots -> None: Session.minute() and session_json() both indexed
    pivot keys with `[...]` instead of `.get(...)`, so a mature session
    (i >= engine.MATURITY) still raised KeyError even after _bars stopped
    raising. Reproduces live.py:1140-1153's build_session path directly:
    >=25 bars (past MATURITY) built via live._bars(d, None), fed into a
    Session the way live.py constructs one, run() to maturity, then
    session_json() -- neither may raise, and the pivots must come out as
    None (stated absence), never as a number or a crash."""
    n = 25
    base_ts = 1757907900  # 2025-09-15 09:15 IST, 60s apart
    d = {"timestamp": [base_ts + 60 * i for i in range(n)],
         "open":   [100.0 + i * 0.1 for i in range(n)],
         "high":   [101.0 + i * 0.1 for i in range(n)],
         "low":    [99.0 + i * 0.1 for i in range(n)],
         "close":  [100.5 + i * 0.1 for i in range(n)],
         "volume": [10 + i for i in range(n)]}
    bars = live._bars(d, None)
    assert len(bars) == n

    # live.py:1140-1153: Session(day_lbl + " LIVE", fut, ce, pe, quiet=True,
    # strike=strike, t_days=t_days, basis=basis or 0.0). CE/PE bars are the
    # same dict shape _bars produces for any of the three legs; reused here
    # since only the FUT-side pivot-absence path is under test.
    s = engine.Session("test LIVE", bars, bars, bars, quiet=True,
                        strike=100.0, t_days=1.0, basis=0.0)
    s.run()
    js = engine.session_json(s)
    assert js["pivots"]["P"] is None


def test_no_common_minute_yet_is_a_why_not_an_indexerror(monkeypatch):
    """8 Oct 09:12-09:16: the future had its first bar, the ATM legs not yet -> zero common minutes -> IndexError in
    engine.session_json and a traceback per index per cycle. Now the same honest 'no bars yet' payload as before 09:15."""
    t0 = 1791431100                                            # 2026-10-08 09:15 IST
    fut = {"open": [22600.0], "high": [22610.0], "low": [22590.0], "close": [22605.0], "volume": [100.0], "timestamp": [t0]}
    empty = {"open": [], "high": [], "low": [], "close": [], "volume": [], "timestamp": []}
    monkeypatch.setattr(live, "_token", lambda: "tok")
    monkeypatch.setattr(live, "_intraday", lambda tok, sid, kind, day, **k: fut if kind == "FUTIDX" else empty)
    monkeypatch.setattr(live, "_nearest_opt_expiry", lambda *a: "2026-10-13")
    monkeypatch.setattr(live, "_atm_ids", lambda *a: {"CE": "c", "PE": "p"})
    monkeypatch.setattr(live, "_pivots", lambda *a: None)
    monkeypatch.setattr(live.time, "sleep", lambda s: None)
    cfg = {"under_sym": "NIFTY", "fut_id": "f", "fut_seg": "NSE_FO", "expiry": "2026-10-27", "step": 50}
    out = live.build_session(cfg, spot=22550.0)
    assert "error" in out and b"first minute is forming" in out["error"]


def test_a_holiday_prior_weekday_steps_back_to_the_last_session(monkeypatch):
    """5 Oct 2026: prev_day was Fri 2 Oct, a holiday -- no bars, no pivots all day and a warning every 16 s. The prior
    SESSION (Thu 1 Oct) has bars: the pivots come from it."""
    asked = []

    def intraday(tok, sid, kind, day, **k):
        asked.append(day)
        return {"high": [22500.0, 22600.0], "low": [22300.0, 22400.0], "close": [22400.0, 22422.0]} if day == "2026-10-01" \
            else {"high": [], "low": [], "close": []}
    monkeypatch.setattr(live, "_intraday", intraday)
    live._piv_cache.clear()
    piv = live._pivots("tok", {"under_sym": "NIFTY", "prev_day": "2026-10-02", "fut_id": "x", "fut_seg": "NSE_FO"})
    assert asked == ["2026-10-02", "2026-10-01"] and piv is not None
    assert abs(piv["P"] - (22600.0 + 22300.0 + 22422.0) / 3) < 1e-6
