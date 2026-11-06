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


# ---- Task 8: the zone card --------------------------------------------------------------------------------------------

def test_the_legality_table():
    up = {"word": "TREND ▲", "dir": 1}
    rng = {"word": "RANGE", "dir": 0}
    assert mstate.legal(up, "EXPANDING", "BUY", "10:30")[0] == "with"
    assert mstate.legal(up, "EXPANDING", "SELL", "12:30") == (
        "fade", "TREND ▲ + EXPANDING: a fade only if the band stopped expanding and the writers at it hold")
    assert mstate.legal(up, "CONTRACTING", "SELL", "13:51")[0] == "fade"
    assert mstate.legal(up, "NORMAL", "SELL", "13:51")[0] == "fade"            # EXPANDING adds the band + wall need
    assert mstate.legal(rng, "CONTRACTING", "SELL", "11:00")[0] == "range"
    assert mstate.legal(rng, "EXPANDING", "BUY", "11:00") == (None, "RANGE + EXPANDING: stand aside")
    assert mstate.legal(up, "CONTRACTING", "BUY", "09:40")[0] is None          # before 09:45
    assert mstate.legal(up, "CONTRACTING", "BUY", "15:03", dte=0)[0] is None   # 0 DTE after 15:00
    assert "%" not in json.dumps([mstate.legal(up, v, s, "11:00") for v in ("EXPANDING", "NORMAL", None) for s in "BS"])


def _zone_frame():
    """A climb into u2 by 11:00 (NIFTY fut), BANKNIFTY / SENSEX flat (no new highs), the CE strike at the band adding
    5L in 9 min, VWAP 24,050 with sigma 30 (u2 24,110, d1 24,020)."""
    px = _path([(0, 24000), (60, 24030), (105, 24110), (120, 24090)])
    d = _frame(px)
    n = len(px)
    d.update(vwap=[24050.0] * n, sd=[30.0] * n, bnf=[54000.0] * n, sx=[79000.0] * n)
    d["ladder"] = {"11:02": {"ce": {24100: 60.0}, "pe": {}}, "10:53": {"ce": {24100: 55.0}, "pe": {}}}
    return d


def test_the_signs_at_the_band_are_a_count_with_reasons():
    d = _zone_frame()
    i = d["mins"].index("11:02")
    piv = [{"kind": "H", "lab": "H", "px": 24000, "t": "10:00", "known": "10:10"},
           {"kind": "H", "lab": "HH", "px": 24060, "t": "10:30", "known": "10:40"}]
    S = {s["k"]: s for s in mstate.signs(d, i, {"side": "SELL", "effort": {"x": 2.4}}, piv)}
    assert S["band"]["ok"] is True and S["band"]["text"].startswith("u2 24,110f vs 24,110f")
    assert S["wall"]["ok"] is True and S["wall"]["text"].startswith("24,100s CE at the band +5.0L / 9 min")
    assert S["effort"]["ok"] is True
    assert S["sync"]["ok"] is True and "BANKNIFTY did not" in S["sync"]["text"]
    assert S["mature"]["ok"] is True and S["mature"]["text"].startswith("push no. 3 up")
    B = {s["k"]: s for s in mstate.signs(d, i, {"side": "BUY"}, piv)}
    assert B["effort"]["ok"] is None and B["effort"]["text"].startswith("effort: not read at a low")
    assert "%" not in json.dumps([S, B])


def test_a_card_judges_at_the_close_with_stop_and_targets():
    d = _zone_frame()
    rows = [{"t": t, "word": "TREND ▲", "dir": 1, "vol": {"word": "EXPANDING"}} for t in d["mins"]]
    z = {"t": "11:00", "side": "SELL", "band": "u2", "px": 24095.0, "gate": {"legal": False, "why": "CE 24500 gave up"}}
    c = mstate.card(d, z, rows, [])
    assert c["verdict"] == "TAKE · smaller target" and c["known"] == "11:03"       # band stopped, CE at it adding
    assert c["why"].startswith("TREND ▲ + EXPANDING: a fade only if the band stopped expanding")
    d2 = _zone_frame()
    d2["ladder"]["11:02"]["ce"][24100] = 40.0                                     # the CE at the band LEAVING (-15L)
    c2 = mstate.card(d2, z, rows, [])
    assert c2["verdict"] == "SKIP" and "writers at it leaving" in c2["why"]
    assert c["gate"]["why"] == "CE 24500 gave up"                                # her gate shown, unchanged
    rows = [dict(r, vol={"word": "CONTRACTING"}) for r in rows]
    c = mstate.card(d, dict(z, effort={"x": 2.5}), rows, [])
    assert c["verdict"] == "TAKE · smaller target" and c["targets"] == [["VWAP", 24050.0]]
    assert c["stop"] == max(d["fhi"][d["mins"].index(m)] for m in ("11:00", "11:01", "11:02"))
    assert mstate.card(d, dict(z, side="BUY", band="d2"), [dict(r, word="TREND ▼", dir=-1) for r in rows],
                       [])["kind"] == "fade"                                     # a BUY in TREND ▼ is a fade
    s = mstate.card(d, dict(z, side="BUY", band="d2"), rows, [])                # no PE on the ladder: wall unchecked
    assert s["kind"] == "with" and s["verdict"] == "TAKE · smaller target" and s["targets"] == [["VWAP", 24050.0]]
    assert "wall: could not check — 23,950s PE not on the ladder" in s["why"] and "not holding" not in s["why"]
    d["ladder"]["11:02"]["pe"][23950] = 30.0
    d["ladder"]["10:53"]["pe"][23950] = 28.0                                      # the PE at d2 adding: writers behind
    s = mstate.card(d, dict(z, side="BUY", band="d2"), rows, [])
    assert s["verdict"] == "STRONG" and s["targets"][1][0] == "u1"
    assert mstate.card_line(c).startswith("ZONE u2 · close 24,095f · TAKE · smaller target (4 of 5 read)")
    assert "%" not in json.dumps([c, c2, s, mstate.card_line(c), mstate.card_line(s)])


def test_a_late_row_is_shown_from_when_it_was_written():
    import datetime
    import fold
    d = _zone_frame()
    rows = [{"t": t, "word": "RANGE", "dir": 0, "vol": {"word": "NORMAL"}} for t in d["mins"]]
    at = datetime.datetime(2026, 11, 5, 13, 48, 40, tzinfo=fold.IST).timestamp()
    c = mstate.card(d, {"t": "11:00", "side": "SELL", "band": "u2", "px": 24095.0, "at": at}, rows, [])
    assert c["known"] == "13:49" and c["late"] and c["close"] == "11:02" and c["verdict"] == "TAKE"   # 13:48:40 -> 13:49
    assert "%" not in json.dumps([c, mstate.card_line(c)])


def _drop(d, *ts):
    """The frame with clock minutes ts absent (a hole in the record): every per-minute list loses them."""
    n = len(d["mins"])
    keep = [j for j, m in enumerate(d["mins"]) if m not in ts]
    for k, v in d.items():
        if isinstance(v, list) and len(v) == n:
            d[k] = [v[j] for j in keep]
    return d


def _rows(d, word="TREND ▲", D=1, vol="EXPANDING"):
    return [{"t": t, "word": word, "dir": D, "vol": {"word": vol}} for t in d["mins"]]


Z = {"t": "11:00", "side": "SELL", "band": "u2", "px": 24095.0}


def test_could_not_check_is_never_a_negative():
    d = _zone_frame()
    del d["ladder"]["10:53"]                                                     # the wall cannot be read
    c = mstate.card(d, dict(Z, side="BUY", band="d2"), _rows(d), [])              # with-trend, wall unchecked
    assert c["verdict"] == "TAKE · smaller target" and "wall: could not check — " in c["why"]
    assert "not holding" not in c["why"]
    f = mstate.card(d, Z, _rows(d), [])                                           # EXPANDING fade, wall unchecked
    assert f["verdict"] == "SKIP" and "wall: could not check — 24,100s CE not on the ladder at 10:53" in f["why"]
    assert "leaving" not in f["why"] and "still expanding" not in f["why"]
    d = _drop(_zone_frame(), "10:59")                                             # sign 1's reference minute absent
    b = mstate.card(d, Z, _rows(d), [])
    assert b["signs"][0]["ok"] is None and b["signs"][0]["text"] == "band: could not check — 10:59 missing"
    assert b["verdict"] == "SKIP" and "band: could not check — 10:59 missing" in b["why"]
    assert "%" not in json.dumps([c, f, b] + [mstate.card_line(x) for x in (c, f, b)])


def test_the_count_says_how_many_were_read():
    d = _zone_frame()
    c = mstate.card(d, Z, _rows(d), [])                                           # effort not given: 1 sign unread
    assert c["n"] == 3 and c["N"] == 4 and "· 3 of 4 read · 1 not read" in c["why"]
    assert "(3 of 4 read · 1 not read)" in mstate.card_line(c) and "of 5" not in mstate.card_line(c)
    assert "%" not in json.dumps([c, mstate.card_line(c)])


def test_volatility_that_could_not_be_checked():
    up, rng = {"word": "TREND ▲", "dir": 1}, {"word": "RANGE", "dir": 0}
    for v in ("?", None):
        assert mstate.legal(up, v, "BUY", "11:00") == ("with", "TREND ▲: the with-trend pullback band · vol: could not check")
        k, why = mstate.legal(up, v, "SELL", "11:00")
        assert k == "fade" and why.endswith("vol: could not check — held to the EXPANDING rule")
        assert mstate.legal(rng, v, "SELL", "11:00") == (
            None, "RANGE + ?: vol: could not check — RANGE trades band to band only when not EXPANDING")
    d = _zone_frame()
    d["ladder"]["11:02"]["ce"][24100] = 40.0                                      # the CE at the band leaving
    c = mstate.card(d, dict(Z, effort={"x": 2.5}), _rows(d, vol="?"), [])         # 3 tired signs, still held to EXPANDING
    assert c["verdict"] == "SKIP" and "writers at it leaving" in c["why"]
    r = mstate.card(d, Z, _rows(d, "RANGE", 0, None), [])
    assert r["verdict"] == "SKIP" and r["kind"] is None
    assert "%" not in json.dumps([c, r, mstate.card_line(c), mstate.card_line(r)])


def test_a_hole_in_the_trigger_bar_is_a_skip_with_the_minute():
    d = _drop(_zone_frame(), "11:01")
    c = mstate.card(d, Z, _rows(d), [])
    assert c["verdict"] == "SKIP" and c["stop"] is None and c["stop_why"] == "stop: could not check — 11:01 missing"
    assert "stop: could not check — 11:01 missing" in c["why"]
    assert "stop: could not check — 11:01 missing" in mstate.card_line(c)
    h = _drop(_zone_frame(), "11:02")                                             # the close itself is a hole
    k = mstate.card(h, Z, _rows(h), [])
    assert k["verdict"] == "SKIP" and k["why"] == "close 11:02 not on the record"
    assert mstate.card_line(k) == "ZONE u2 · close 24,095f · SKIP · close 11:02 not on the record"
    late = _zone_frame()                                                         # not yet in the frame: no card
    assert mstate.card(late, dict(Z, t=late["mins"][-1]), _rows(late), []) is None
    assert "%" not in json.dumps([c, k, mstate.card_line(c), mstate.card_line(k)])


def test_the_wall_is_read_at_the_band_her_trigger_armed_on():
    d = _zone_frame()
    c = mstate.card(d, dict(Z, level=24160.0), _rows(d), [])                      # 24,160 - 40 basis -> the 24,150 CE
    w = c["signs"][1]
    assert w["k"] == "wall" and w["ok"] is None and "24,150s CE" in w["text"] and "recomputed" not in w["text"]
    assert mstate.card_line(c).startswith("ZONE u2 24,160f · close 24,095f · SKIP")
    r = mstate.card(d, Z, _rows(d), [])                                           # no level: the 1-min band, said so
    assert r["signs"][1]["text"].endswith("band recomputed — level not logged")
    assert "%" not in json.dumps([c, r, mstate.card_line(c), mstate.card_line(r)])
