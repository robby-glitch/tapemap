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


# ---- Task 9a: §6a, managing an open zone trade (display only; she decides) --------------------------------------------

def _trade_frame(pts, lad=lambda T: 60.0):
    """A SELL at u2 11:00 (close 11:02, 24,095): VWAP 24,050 sigma 30, the median 1-min candle 2 pts, the CE at the
    band (24,100) on the ladder every minute at lad(clock minute)."""
    d = _frame(_path(pts))
    n = len(d["mins"])
    d.update(vwap=[24050.0] * n, sd=[30.0] * n)
    d["ladder"] = {t: {"ce": {24100: lad(555 + j)}, "pe": {}} for j, t in enumerate(d["mins"])}
    return d


def _tc(d, **kw):
    """A card as mstate.card makes it (Task 8) plus the logged u3 / d3: SELL 11:00, stop = the trigger candle's high."""
    js = [d["mins"].index(m) for m in ("11:00", "11:01", "11:02")]
    return dict({"t": "11:00", "close": "11:02", "known": "11:03", "side": "SELL", "px": 24095.0,
                 "stop": max(d["fhi"][j] for j in js), "u3": 24150.0, "d3": 23950.0, "u3_why": None,
                 "verdict": "TAKE · smaller target", "targets": [["VWAP", 24050.0]],
                 "signs": [{"k": "wall", "ok": True, "text": "24,100s CE at the band +0.0L / 9 min", "strike": 24100}]},
                **kw)


# into u2, the trigger, then a slow creep to 0.5 pt under the 24,111 stop from 11:05, held 15 min, then down to VWAP
CREEP = [(0, 24000), (105, 24110), (107, 24095), (110, 24109.5), (125, 24109.5), (140, 24040)]
FAST = [(0, 24000), (105, 24110), (107, 24095), (110, 24130), (140, 24130)]
BREAK = [(0, 24000), (105, 24110), (107, 24095), (110, 24109.5), (125, 24109.5), (128, 24125), (140, 24125)]
ADDUP = [(0, 24000), (105, 24110), (107, 24095), (110, 24109.5), (125, 24109.5), (128, 24160), (140, 24160)]


def test_widen_shows_after_six_slow_minutes_near_the_stop_and_the_target_ends_it():
    d = _trade_frame(CREEP)
    E = {e["t"]: e for e in mstate.trade(d, _tc(d), _rows(d, vol="CONTRACTING"))}
    assert min(E) == "11:03" and not any(c.startswith("WIDEN") for c in E["11:10"]["chips"])   # 5 min near: hidden
    assert E["11:11"]["chips"][:2] == ["WIDEN · stop → beyond u3 24,150f", "risk to u3: 55 pts [M]"]
    assert E["11:11"]["risk"] == 55.0 and E["11:11"]["why"][0].startswith("WIDEN 11:11: writers tike: 24,100s CE")
    assert E["11:33"]["open"] is False and E["11:33"]["chips"][-1] == "target VWAP 24,050f ✓ — trade poora"
    assert max(E) == "11:33"
    x = {e["t"]: e for e in mstate.trade(d, _tc(d), _rows(d, vol="EXPANDING"))}     # TREND ▲ + EXPANDING vs a SELL
    assert not any(c.startswith("WIDEN") for e in x.values() for c in e["chips"])
    assert "no WIDEN: TREND ▲ + EXPANDING against the trade" in x["11:11"]["why"]
    assert "%" not in json.dumps([E, x])


def test_a_fast_stop_says_it_was_not_the_trade():
    d = _trade_frame(FAST)
    tr = mstate.trade(d, _tc(d), _rows(d, vol="CONTRACTING"))
    assert [e["t"] for e in tr] == ["11:03", "11:04"] and tr[-1]["open"] is False
    assert tr[-1]["chips"][-1] == "stop hua — yeh trade nahi tha · 24,111f · fast — straight through (WIDEN needs 6 min)"
    assert "%" not in json.dumps(tr)


def test_writers_leaving_the_band_hide_widen_and_the_stop_says_why():
    d = _trade_frame(BREAK, lad=lambda T: 60.0 if T < 660 else 60.0 - (T - 660))     # the CE at the band -1L a minute
    E = {e["t"]: e for e in mstate.trade(d, _tc(d), _rows(d, vol="CONTRACTING"))}
    assert not any(c.startswith("WIDEN") for e in E.values() for c in e["chips"])
    assert E["11:21"]["open"] is False and E["11:21"]["chips"][-1] == (
        "stop hua — yeh trade nahi tha · 24,111f · writers at 24,100s CE leaving -9.0L / 9 min · effort: could not check")


def test_add_once_while_the_widen_stands_and_the_hard_line_ends_both_lots():
    d = _trade_frame(ADDUP)
    c1, c2 = _tc(d), _tc(d, t="11:12", close="11:14", known="11:15", px=24105.0)
    mstate.trades(d, [c1, c2], _rows(d, vol="CONTRACTING"))
    E = {e["t"]: e for e in c1["trade"]}
    assert c2["trade"] is None and c2["in_trade"] == "11:00"                     # folded: the ADD, never a 2nd trade
    assert not any(c.startswith("ADD") for c in E["11:14"]["chips"])
    assert E["11:15"]["chips"] == ["WIDEN · stop → beyond u3 24,150f", "ADD 1 · avg 24,100f · stop beyond u3 24,150f",
                                   "risk to u3: 55 + 45 = 100 pts (dono lot) [M]"] and E["11:15"]["risk"] == 100.0
    assert E["11:21"]["open"] is True                                            # past the old stop: widened, still open
    assert E["11:23"]["open"] is False and E["11:23"]["chips"][-1] == "u3 ke paar 3-min close 24,160f — dono lot band"
    assert max(E) == "11:23" and "%" not in json.dumps(c1["trade"])


def test_a_copy_of_the_same_touch_is_never_the_add():
    """I1: 14:05 / 14:06 style -- the touch logged twice (1 min apart, the copy written late) is folded, never ADD 1."""
    d = _trade_frame(ADDUP)
    c1, dup = _tc(d), _tc(d, t="11:01", close="11:03", known="11:15", px=24105.0)
    mstate.trades(d, [c1, dup], _rows(d, vol="CONTRACTING"))
    assert dup["trade"] is None and dup["in_trade"] == "11:00"
    assert any(c.startswith("WIDEN") for e in c1["trade"] for c in e["chips"])
    assert not any(c.startswith("ADD") for e in c1["trade"] for c in e["chips"])
    assert all(e["risk"] in (None, 55.0) for e in c1["trade"])                  # one lot, never "dono lot"


def test_no_add_after_a_broken_widen_and_no_third_adjustment():
    d = _trade_frame(ADDUP, lad=lambda T: 60.0 if T <= 672 else 60.0 - 3 * (T - 672))   # writers leave from 11:13
    c1, c2 = _tc(d), _tc(d, t="11:12", close="11:14", known="11:15", px=24105.0)
    mstate.trades(d, [c1, c2], _rows(d, vol="CONTRACTING"))
    E = {e["t"]: e for e in c1["trade"]}
    assert E["11:15"]["chips"] == ["WIDEN · stop → beyond u3 24,150f", "WIDEN toota — ADD nahi", "risk to u3: 55 pts [M]"]
    assert not any(c.startswith("ADD") for e in E.values() for c in e["chips"])
    assert any(w.startswith("WIDEN broken 11:13: writers at 24,100s CE leaving -3.0L") for w in E["11:15"]["why"])
    assert E["11:23"]["chips"][-1] == "u3 ke paar 3-min close 24,160f — trade band"


def test_a_row_without_u3_could_not_check_never_a_zero():
    d = _trade_frame(CREEP)
    tr = mstate.trade(d, _tc(d, u3=None, d3=None), _rows(d, vol="CONTRACTING"))
    assert all(e["chips"][0] == "u3: could not check — u3 not logged (row before 6 Nov)" for e in tr)
    assert all(e["risk"] is None for e in tr)
    assert not any(c.startswith(("WIDEN", "ADD", "risk")) for e in tr for c in e["chips"])
    assert tr[-1]["chips"][-1] == "target VWAP 24,050f ✓ — trade poora"            # the stop and target still read
    zc = mstate.card(_zone_frame(), Z, _rows(_zone_frame()), [])                  # Z has no u3: the card says None
    assert zc["u3"] is None and zc["signs"][1]["strike"] == 24100
    assert "%" not in json.dumps(tr)


def test_the_trade_is_causal():
    d = _trade_frame(ADDUP)
    rows, c2 = _rows(d, vol="CONTRACTING"), _tc(d, t="11:12", close="11:14", known="11:15", px=24105.0)
    full, N = mstate.trade(d, _tc(d), rows, [c2]), len(d["mins"])
    for e in full:                                                               # minute j reads minutes <= j only
        j = d["mins"].index(e["t"])
        cut = {k: (v[:j + 1] if isinstance(v, list) and len(v) == N else v) for k, v in d.items()}
        assert mstate.trade(cut, _tc(d), rows[:j + 1], [c2])[-1] == e


def test_a_hole_never_counts_as_near_and_a_stop_after_it_says_so():
    d = _drop(_trade_frame(CREEP), "11:08")                                       # absent: the near count restarts 11:09
    E = {e["t"]: e for e in mstate.trade(d, _tc(d), _rows(d, vol="CONTRACTING"))}
    assert not any(c.startswith("WIDEN") for c in E["11:14"]["chips"]) and E["11:15"]["chips"][0].startswith("WIDEN")
    d = _drop(_trade_frame([(0, 24000), (105, 24110), (107, 24095), (110, 24109.5), (117, 24109.5), (118, 24130),
                            (140, 24130)]), *[_hm(m) for m in range(666, 673)])
    tr = mstate.trade(d, _tc(d), _rows(d, vol="CONTRACTING"))                     # crossed right after 11:06-11:12
    assert tr[-1]["chips"][-1] == "stop hua — yeh trade nahi tha · 24,111f · how: could not check — 11:06–11:12 not on the record"


def test_cards_survive_a_raising_open_trade_walk(monkeypatch):
    def boom(*a, **k):
        raise KeyError("x")
    monkeypatch.setattr(mstate, "trade", boom)
    d2 = _zone_frame()
    d2["zone"] = [Z]
    out = mstate.cards(d2, _rows(d2), [])
    assert out and all(c["trade"] is None and c["trade_why"] == "open trade: could not check — KeyError" for c in out)


def test_a_take_is_never_folded_into_an_earlier_skip_card():
    d = _trade_frame(CREEP)
    sk, tk = _tc(d, verdict="SKIP"), _tc(d, t="11:07", close="11:09", known="11:10", px=24100.0)
    mstate.trades(d, [sk, tk], _rows(d, vol="CONTRACTING"))
    assert tk["in_trade"] is None and tk["trade"]


def test_a_skip_cards_end_chip_never_reads_as_her_trade():
    d = _trade_frame(CREEP)
    tr = mstate.trade(d, _tc(d, verdict="SKIP"), _rows(d, vol="CONTRACTING"))
    assert tr[-1]["chips"][-1] == "SKIP tha · target VWAP 24,050f ✓"
    f = mstate.trade(_trade_frame(FAST), _tc(_trade_frame(FAST), verdict="SKIP"), _rows(_trade_frame(FAST), vol="CONTRACTING"))
    assert f[-1]["chips"][-1].startswith("SKIP tha · stop hua")


def test_a_gap_the_trade_survives_says_what_was_not_checked():
    d = _drop(_trade_frame(CREEP), "11:08")
    tr = mstate.trade(d, _tc(d), _rows(d, vol="CONTRACTING"))
    assert "11:08–11:08 not on the record: stop / target not checked" in tr[-2]["why"]


def test_zero_dte_says_gamma_both_ways_from_14_and_no_hold_from_15():
    d = _frame([24000.0] * 351)                                   # 09:15 .. 15:05
    d["ctx"]["dte"] = 0
    rows, _ = mstate.fold(d)
    at = {r["t"]: r["expiry"] for r in rows}
    assert at["13:59"] is None and at["14:00"] == "EXPIRY: gamma both ways"
    assert at["15:00"] == "EXPIRY: gamma both ways · no hold for the close"
    d["ctx"]["dte"] = 1
    assert all(r["expiry"] is None for r in mstate.fold(d)[0])
    d["ctx"].pop("dte")                                           # rule 6: unknown dte is said, not read as "not expiry"
    at = {r["t"]: r["expiry"] for r in mstate.fold(d)[0]}
    assert at["13:59"] is None and at["14:00"].startswith("EXPIRY: could not check")


# ---- Task 12: the cross-index read -------------------------------------------------------------------------------------

def test_prem_reads_the_premium_beyond_delta():
    d = _frame([24000.0] * 10)
    chain = {"09:16": {"spot": 23990.0, "ce": {24000: {"ltp": 100.0, "delta": 0.5}}, "pe": {24000: {"ltp": 110.0, "delta": -0.5}}},
             "09:19": {"spot": 24010.0, "ce": {24000: {"ltp": 112.0, "delta": 0.55}}, "pe": {24000: {"ltp": 99.0, "delta": -0.45}}}}
    assert mstate._prem(d, d["mins"].index("09:19"), chain) == {"ce": 2.0, "pe": -1.0}
    assert mstate._prem(d, d["mins"].index("09:18"), chain) == {"ce": None, "pe": None}


def _xf(idx, d=1, unwind=None, wf=(None, None), vol="NORMAL", prem=None):
    mins = [_hm(600 + i) for i in range(10)]
    fr = [{"k": 24000.0, "side": unwind, "state": "UNWINDING"}] if unwind else []
    return {"ok": True, "idx": idx, "mins": mins, "timeline": [{"fronts": fr} for _ in mins],
            "wf_ce": [wf[0]] * 10, "wf_pe": [wf[1]] * 10,
            "mstate": [{"t": m, "word": "TREND ▲" if d > 0 else "RANGE", "dir": d, "vol": {"word": vol},
                        "prem": prem or {"ce": None, "pe": None}} for m in mins]}


def test_trend_day_rotation_and_could_not_check():
    x = mstate.cross({n: _xf(n, unwind="CE") for n in mstate.IDXS}, "10:09")
    assert x["sync"]["dir"] == 1 and x["sync"]["n"] == 3 and x["day"].startswith("TREND DAY ▲")
    x = mstate.cross({"NIFTY": _xf("NIFTY"), "SENSEX": _xf("SENSEX", 0), "BANKNIFTY": _xf("BANKNIFTY", 0)}, "10:09")
    assert x["day"].startswith("ROTATION: NIFTY ▲ alone") and x["sync"] is None
    x = mstate.cross({"NIFTY": _xf("NIFTY")}, "10:09")
    assert x["day"] is None and x["why"] == ["SENSEX: could not check — no frame at 10:09",
                                             "BANKNIFTY: could not check — no frame at 10:09"]
    assert mstate.cross({n: dict(_xf(n), day="2026-11-04") for n in mstate.IDXS}, "10:09", "2026-11-05")["why"][0] \
        == "NIFTY: could not check — no frame at 10:09"                           # another day's frame is never a peer
    assert mstate.cross({n: _xf(n, unwind="CE") for n in mstate.IDXS}, "10:12")["why"][0] \
            == "NIFTY: could not check — its last minute 10:09, over 2 min behind 10:12"   # stale: named, not counted


def test_coil_then_escape_is_a_display_only_warning():
    coil = {n: _xf(n, 0, wf=(12.0, 11.0), vol="CONTRACTING") for n in mstate.IDXS}
    assert mstate.cross(coil, "10:09")["alert"] is None                         # a coil alone says nothing
    esc = dict(coil, NIFTY=_xf("NIFTY", 0, wf=(-12.0, 0.0), vol="CONTRACTING", prem={"ce": 0.4, "pe": None}),
               SENSEX=_xf("SENSEX", 0, wf=(-15.0, 1.0), vol="CONTRACTING"))
    for n in ("NIFTY", "SENSEX"):                                               # the coil was 8-10 min ago
        esc[n]["wf_ce"][:3], esc[n]["wf_pe"][:3] = [12.0] * 3, [11.0] * 3
    a = mstate.cross(esc, "10:09")["alert"]
    assert a.startswith("box ban gaya, writers bhaag rahe — bada move ho sakta hai ▲")
    assert "premium beyond delta: NIFTY bid · SENSEX could not check" in a and "never a prediction" in a and "%" not in a


def test_sync_counts_say_how_many_were_read_and_opening_is_not_range():
    two = {n: _xf(n, unwind="CE") for n in ("NIFTY", "SENSEX")}
    x = mstate.cross(two, "10:09")
    assert x["sync"]["of"] == 2 and "in 2 of 2 read · 1 could not check" in x["sync"]["text"]
    allr = {n: _xf(n, unwind="CE") for n in mstate.IDXS}
    assert "in 3 of 3 read:" in mstate.cross(allr, "10:09")["sync"]["text"]
    opening = {"NIFTY": _xf("NIFTY"), "SENSEX": _xf("SENSEX", 0), "BANKNIFTY": _xf("BANKNIFTY", 0)}
    for r in opening["BANKNIFTY"]["mstate"]:
        r["word"] = "OPENING"
    x = mstate.cross(opening, "10:09")
    assert x["day"] is None and "BANKNIFTY: no swing confirmed yet" in x["why"]       # not checked, so no ROTATION
    unconfirmed = {n: _xf(n, unwind="CE") for n in mstate.IDXS}
    for r in unconfirmed["SENSEX"]["mstate"]:
        r["word"] = "TREND ▲ (leg, unconfirmed)"
    assert mstate.cross(unconfirmed, "10:09")["day"] is None


def test_coil_after_the_run_is_not_a_coil_and_a_blind_premium_is_named():
    esc = {n: _xf(n, 0, wf=(12.0, 11.0), vol="CONTRACTING") for n in mstate.IDXS}
    for n in ("NIFTY", "SENSEX"):
        esc[n]["wf_ce"][:3], esc[n]["wf_pe"][:3] = [-12.0] * 3, [0.0] * 3        # the run is EARLY ...
    for n in ("NIFTY", "SENSEX"):
        esc[n]["wf_ce"][3:], esc[n]["wf_pe"][3:] = [12.0] * 7, [11.0] * 7         # ... the coil comes after it
    esc["BANKNIFTY"] = _xf("BANKNIFTY", 0)
    assert mstate.cross(esc, "10:09")["alert"] is None
    ok = {n: _xf(n, 0, wf=(12.0, 11.0), vol="CONTRACTING") for n in mstate.IDXS}
    for n in ("NIFTY", "SENSEX"):
        ok[n]["wf_ce"][:3], ok[n]["wf_pe"][:3] = [12.0] * 3, [11.0] * 3
        ok[n]["wf_ce"][3:], ok[n]["wf_pe"][3:] = [-12.0] * 7, [0.0] * 7
    ok["NIFTY"] = _xf("NIFTY", 0, wf=(-12.0, 0.0), vol="CONTRACTING", prem={"ce": 0.0, "pe": None})
    ok["NIFTY"]["wf_ce"][:3], ok["NIFTY"]["wf_pe"][:3] = [12.0] * 3, [11.0] * 3
    a = mstate.cross(ok, "10:09")["alert"]
    assert a and "SENSEX could not check" in a and "NIFTY not bid" in a and "none" not in a
