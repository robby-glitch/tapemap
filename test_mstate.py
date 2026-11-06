"""test_mstate.py -- the market state (plan docs/superpowers/plans/2026-11-06-jarvis-market-state.md). Synthetic frames
only: pure functions, no record, no clock."""
import json

import mstate


def _hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def _path(points):
    """[(minute index, price), ...] -> one price per minute, straight lines between the points."""
    out = []
    for (i0, p0), (i1, p1) in zip(points, points[1:]):
        out += [p0 + (p1 - p0) * (k - i0) / (i1 - i0) for k in range(i0, i1)]
    return out + [points[-1][1]]


def _frame(px, idx="NIFTY", rows=None):
    """A jarvis.build-shaped frame from 09:15, one futures price a minute (spot 40 below, VWAP flat at the open)."""
    n = len(px)
    mins = [_hm(555 + i) for i in range(n)]
    return {"ok": True, "day": "2026-11-05", "idx": idx, "mins": mins, "fut": list(px), "fo": list(px),
            "fhi": [p + 1 for p in px], "flo": [p - 1 for p in px], "spot": [p - 40 for p in px],
            "vwap": [px[0]] * n, "sd": [20.0] * n, "step": 50, "timeline": [{"fronts": []} for _ in range(n)],
            "legs": {"rows": rows or [{"t": m, "lean": 0, "word": "NO LEG", "leg": None} for m in mins]},
            "ctx": {"opt": {}}, "wf_ce": [None] * n, "wf_pe": [None] * n}


# 09:15 24,000 -> 10:00 24,200 (H) -> 10:15 24,120 (HL) -> 10:45 24,300 (HH) -> 11:00 24,220 (HL) -> 11:30 24,400
# -> 12:00 24,150 (through the HL line)
ZIG = _path([(0, 24000), (45, 24200), (60, 24120), (90, 24300), (105, 24220), (135, 24400), (165, 24150)])


def test_hh_then_hl_confirms_trend_up_and_the_line_is_the_hl():
    rows, piv = mstate.fold(_frame(ZIG))
    assert [p["lab"] for p in piv][:5] == ["L", "H", "HL", "HH", "HL"]
    first = next(r for r in rows if r["word"] == "TREND ▲")
    assert "11:00" < first["t"] < "11:30" and first["line"] == "line 24,219 (HL 11:00)"
    assert first["why"] == "TREND ▲: HH 24,301 (10:45) then HL 24,219 (11:00) held" and first["since"] == first["t"]
    assert all(r["word"] in ("OPENING", "RANGE") for r in rows if r["t"] < first["t"])   # one HL alone is not a trend


def test_a_close_through_the_hl_by_more_than_a_candle_ends_it_as_range():
    rows, _ = mstate.fold(_frame(ZIG))
    end = next(r for r in rows if r["t"] > "11:30" and r["word"] != "TREND ▲")
    assert end["word"] == "RANGE" and end["why"].startswith("structure: a 3-min close")
    assert "below the HL 24,219 (11:00)" in end["why"]
    assert all(r["word"] == "TREND ▲" for r in rows if "11:30" <= r["t"] < end["t"])   # no flicker before it


def test_writers_giving_up_ends_the_trend():
    d = _frame(ZIG)
    k = d["mins"].index("11:41")                              # 11:41 is a 3-min close; spot is 24,316 then
    for j in range(k, len(d["mins"])):
        d["timeline"][j] = {"fronts": [{"k": 24300.0, "side": "PE", "state": "UNWINDING", "peak_at": "11:30",
                                        "oi": 80.0, "chg": -9.0, "peak": 12.0}]}
    rows, _ = mstate.fold(d)
    assert rows[k - 1]["word"] == "TREND ▲" and rows[k]["word"] == "RANGE"
    assert rows[k]["why"].startswith("writers gave up: 24,300s PE UNWINDING")


def test_a_trend_leg_reads_unconfirmed_and_low_efficiency_reads_range():
    px = _path([(0, 24000), (40, 24150)])
    mins = [_hm(555 + i) for i in range(len(px))]
    leg = {"dir": 1, "quality": "TREND", "pts": 150, "origin": 24000.0, "origin_t": "09:15"}
    rows = [{"t": m, "lean": 1, "word": "OPENING", "leg": leg} for m in mins]
    out, _ = mstate.fold(_frame(px, rows=rows))
    assert out[-1]["word"] == "TREND ▲ (leg, unconfirmed)" and out[-1]["line"] == "line 24,000 (origin 09:15)"
    chop = _path([(0, 24000)] + [(5 * k, 24000 + (30 if k % 2 else -30)) for k in range(1, 12)] + [(60, 24010)])
    mins = [_hm(555 + i) for i in range(len(chop))]
    out, _ = mstate.fold(_frame(chop, rows=[{"t": m, "lean": 1, "word": "TREND", "leg": leg} for m in mins]))
    assert out[-1]["word"] == "RANGE" and out[-1]["why"].startswith("RANGE: a TREND leg, but efficiency")


def test_the_fold_is_causal():
    d = _frame(ZIG)
    full, _ = mstate.fold(d)
    k = 120
    cut = {key: (v[:k] if isinstance(v, list) and len(v) == len(d["mins"]) else v) for key, v in d.items()}
    cut["legs"] = {"rows": d["legs"]["rows"][:k]}
    part, _ = mstate.fold(cut)
    assert part == full[:k]


def test_no_rate_and_a_chip_with_its_number():
    rows, _ = mstate.fold(_frame(ZIG))
    assert "%" not in json.dumps(rows)
    up = next(r for r in rows if r["word"] == "TREND ▲")
    assert mstate.chip(up) == "upar ka trend · 24,219"


# ---- Task 2: the volatility state ---------------------------------------------------------------------------------------

def _flat(n=60, idx="NIFTY"):
    return _frame([24000.0] * n, idx=idx)


def test_each_gauge_votes_or_says_why_it_could_not_check():
    d = _flat()
    i = d["mins"].index("10:02")                                  # a 3-min close (09:15 + 3k + 2)
    G = {g["k"]: g for g in mstate.gauges(d, i)}
    assert list(G) == ["range", "straddle", "vix", "iv", "raftaar"]
    assert all(g["vote"] is None and "could not check" in g["text"] for g in G.values())
    d["fhi"][i] += 30                                             # a 32-pt bar against a 10-pt slot median: EXPANDING
    nm = ({(mstate._m("10:00") - 555) // 3: 10.0}, ("a", "b", "c", "d", "e"))
    chain = {"09:47": {"spot": 23995.0, "ce": {24000: {"ltp": 100.0, "delta": 0.5}},
                       "pe": {24000: {"ltp": 110.0, "delta": -0.5}}},
             "10:02": {"spot": 23997.0, "ce": {24000: {"ltp": 108.0, "delta": 0.5}},
                       "pe": {24000: {"ltp": 109.0, "delta": -0.5}}}}
    d["ctx"] = {"vix": [["09:47", 14.0, None], ["10:02", 14.5, None]],
                "opt": {"09:47": {"iv": 14.0}, "10:02": {"iv": 15.0}}}
    d["wf_ce"][i], d["wf_pe"][i] = -12.0, 0.0                     # call writers covering, puts not against: running
    G = {g["k"]: g for g in mstate.gauges(d, i, chain, nm)}
    assert {k: g["vote"] for k, g in G.items()} == {"range": 1, "straddle": 1, "vix": 1, "iv": 1, "raftaar": 1}
    assert G["straddle"]["text"].startswith("24,000s straddle 210.0 → 217.0") and "%" not in json.dumps(G)


def test_the_volatility_word_needs_two_closes(monkeypatch):
    d = _flat(90)
    votes = {t: ([1, 1, 0, None, 0] if t >= "10:05" else [-1, -1, 0, 0, None])
             for t in d["mins"] if (mstate._m(t) - 555) % 3 == 2}
    monkeypatch.setattr(mstate, "gauges", lambda d, i, chain=None, nm=None: [
        {"k": str(n), "vote": v, "text": ""} for n, v in enumerate(votes[d["mins"][i]])])
    rows, _ = mstate.fold(d)
    at = {r["t"]: r["vol"]["word"] for r in rows}
    assert at["09:17"] == "CONTRACTING"                           # the day's first close says it at once
    assert at["10:05"] == "CONTRACTING" and at["10:08"] == "EXPANDING"   # one close is not enough; two are
    assert rows[-1]["vol"]["since"] == "10:08" and rows[-1]["vol"]["up"] == 2


def test_the_bar_range_yardstick_reads_prior_sessions_only(tmp_path, monkeypatch):
    import squeeze_score
    monkeypatch.setattr(squeeze_score, "BT", str(tmp_path))
    assert mstate.norm("NIFTY", "2026-11-05") == ({}, ())          # nothing on the record: could not check, never zero


def test_a_stalled_vix_feed_cannot_check_not_shows_stale_as_current():
    d = _flat()
    i = d["mins"].index("10:02")
    d["ctx"] = {"vix": [["09:47", 14.0, None], ["09:52", 14.5, None]], "opt": {}}     # last row 10 min old
    G = {g["k"]: g for g in mstate.gauges(d, i)}
    assert G["vix"]["vote"] is None and "could not check" in G["vix"]["text"] and "09:52" in G["vix"]["text"]


def test_the_yardstick_excludes_the_day_itself(tmp_path, monkeypatch):
    import confluence_log
    import squeeze_score
    for day in ("2026-11-04", "2026-11-05"):
        (tmp_path / f"fut_{day}.json").write_text("{}")
    monkeypatch.setattr(squeeze_score, "BT", str(tmp_path))
    monkeypatch.setattr(confluence_log, "session", lambda idx, x: {"bars": [{"t": "09:15", "h": 10.0, "l": 4.0}]})
    slots, used = mstate.norm("NIFTY", "2026-11-05")
    assert used == ("2026-11-04",) and slots == {0: 6.0}
