"""ZONE-3M (docs/setup-review/ZONE-3M-PREREG.md, draft §1r): the zone machine on bands computed on its own 3-minute bars,
beside the 1-minute-sigma zone. Pure: the 26 Oct NIFTY candles are a literal below; nothing here reads data/."""
import json
import os

import band_rotation
import contract_bars
from band_rotation import run_states

# ---- Task 1: the 09:25 anchor's span, and the one date ---------------------------------------------------------------

VWAP, SD = 100.0, 5.0
D2, D3, U2, U3 = VWAP - 2 * SD, VWAP - 3 * SD, VWAP + 2 * SD, VWAP + 3 * SD


def _bar(t, low, high, close):
    """One flat bar on fixed bands: VWAP 100, sigma 5 (d2 90, d3 85, u2 110, u3 115)."""
    return {"t": t, "o": close, "h": high, "l": low, "c": close, "vwap": VWAP, "u1": VWAP + SD, "d1": VWAP - SD,
            "u2": U2, "d2": D2, "u3": U3, "d3": D3}


def test_span_one_is_the_label_rule_byte_for_byte():
    """Every existing caller passes no span: the default must be the old `minute >= 09:25`, on every machine."""
    bars = [_bar("09:18", 84.0, 116.0, 100.0), _bar("09:21", 84.0, 116.0, 100.0), _bar("09:24", 84.0, 116.0, 100.0),
            _bar("09:25", 84.0, 116.0, 100.0), _bar("09:27", 84.0, 116.0, 100.0), _bar("09:30", 95.0, 117.0, 116.5),
            _bar("09:33", 83.0, 105.0, 84.0), _bar("09:36", 90.0, 99.0, 98.0)]
    for kw in ({}, {"band": "d2"}, {"side": "SELL"}, {"side": "SELL", "band": "u2"}):
        for stop in (None, band_rotation.OPERATOR_STOP_PTS):
            old = run_states(bars, stop_pts=stop, **kw)
            assert json.dumps(old) == json.dumps(run_states(bars, stop_pts=stop, span=1, **kw)), kw
    assert [s["entry"] for s in run_states(bars)] == band_rotation.detect_index_run(bars)


def test_span_three_lets_the_0924_bar_arm_and_span_one_does_not():
    """Rule 4: a bar is eligible when it holds a minute at or after 09:25 (label + 3 > 09:25)."""
    bars = [_bar("09:21", 95.0, 99.0, 97.0), _bar("09:24", 89.5, 93.0, 91.0), _bar("09:27", 92.0, 96.0, 95.5)]
    one = run_states(bars, stop_pts=20.0, band="d2")
    three = run_states(bars, stop_pts=20.0, band="d2", span=3)
    assert [s["state"] for s in one] == ["WAITING", "WAITING", "WAITING"]
    assert [s["state"] for s in three] == ["WAITING", "ARMED", "TRIGGERED"]
    assert three[1]["arm"] == {"rearm": False, "band": "d2", "extreme": 89.5, "first_i": 1, "first_t": "09:24"}
    assert three[2]["entry"]["stop"] == D2 - 20.0


def test_the_0921_bar_never_arms_even_at_span_three():
    """09:21 + 3 = 09:24: the bar holds no minute at or after 09:25."""
    assert run_states([_bar("09:21", 89.0, 93.0, 91.0)], band="d2", span=3)[0]["state"] == "WAITING"


def test_zone3_from_is_the_one_date_the_first_november_session():
    """One switch, one date (27 Oct is NIFTY's monthly expiry and the roll)."""
    assert band_rotation.ZONE3_FROM == "2026-10-28"


# ---- Task 2: bands computed on the bars themselves -------------------------------------------------------------------

def _row(t, h, l, c, v):
    """A composite 3-min index row (resample_index's shape), sampled 1-min bands deliberately WRONG (999)."""
    return {"t": t, "fut": {"o": c, "h": h, "l": l, "c": c, "v": v, "oi": None,
                            **{k: 999.0 for k in contract_bars.BAND_KEYS}}, "ce": None, "pe": None}


def test_bands_on_is_the_session_recurrence_on_the_rows_own_hlcv():
    rows = [_row("09:15", 110.0, 100.0, 105.0, 300.0), _row("09:18", 108.0, 98.0, 99.0, 200.0),
            _row("09:21", 101.0, 95.0, 96.0, 100.0)]
    want = contract_bars.vwap_sigma([(r["fut"]["h"], r["fut"]["l"], r["fut"]["c"], r["fut"]["v"]) for r in rows])
    assert contract_bars.bands_on(rows) == want
    flat = [dict(r["fut"], t=r["t"]) for r in rows]                       # resample's flat shape, same numbers
    assert contract_bars.bands_on(flat) == want


def test_an_unreadable_row_is_none_and_adds_nothing():
    rows = [_row("09:15", 110.0, 100.0, 105.0, 300.0), {"t": "09:18", "fut": None, "ce": None, "pe": None},
            _row("09:21", 101.0, 95.0, 96.0, 100.0)]
    got = contract_bars.bands_on(rows)
    assert got[1] is None
    assert got[2] == contract_bars.vwap_sigma([(110.0, 100.0, 105.0, 300.0), (101.0, 95.0, 96.0, 100.0)])[1]
    assert contract_bars.bands_on([{"t": "09:15", "h": None, "l": 1.0, "c": 1.0, "v": 1.0}]) == [None]


def test_with_bands_replaces_only_the_band_keys_on_a_copy():
    rows = [_row("09:15", 110.0, 100.0, 105.0, 300.0), {"t": "09:18", "fut": None, "ce": None, "pe": None},
            _row("09:21", 101.0, 95.0, 96.0, 100.0)]
    before = json.dumps(rows)
    b = contract_bars.bands_on(rows)
    out = contract_bars.with_bands(rows, b)
    assert json.dumps(rows) == before                                       # not mutated
    assert {k: out[0]["fut"][k] for k in contract_bars.BAND_KEYS} == b[0]
    assert out[0]["fut"]["h"] == 110.0 and out[0]["ce"] is None
    assert out[1] == rows[1]                                                # the future did not print: left as it is
    flat = contract_bars.with_bands([{"t": "09:15", "h": None, "l": 1.0, "c": 1.0, "v": 1.0, "d2": 5.0}], [None])
    assert flat[0]["d2"] is None and flat[0]["l"] == 1.0                     # unreadable: None, never the old value


# ---- Task 3: the 3-min payload, its switch, and the 26 Oct acceptance ------------------------------------------------

# 26 Oct 2026 NIFTY near-month futures, the exchange's 1-min candles 09:15-09:32: (t, o, h, l, c, v). From
# /api/data?idx=NIFTY&interval=1 read that afternoon (scratchpad nifty_1m.json, days[-1].bars[i].fut). [M]
OCT26_NIFTY_FUT_1M = [
    ("09:15", 22560.0, 22570.0, 22530.0, 22535.0, 75075.0),
    ("09:16", 22531.0, 22575.0, 22525.6, 22575.0, 17420.0),
    ("09:17", 22576.0, 22579.3, 22520.0, 22520.0, 24180.0),
    ("09:18", 22520.0, 22525.6, 22505.6, 22505.6, 16445.0),
    ("09:19", 22510.0, 22519.0, 22500.0, 22500.0, 14430.0),
    ("09:20", 22495.0, 22501.8, 22480.8, 22495.1, 12675.0),
    ("09:21", 22496.4, 22498.0, 22470.0, 22476.3, 21840.0),
    ("09:22", 22474.6, 22475.0, 22462.0, 22470.0, 17485.0),
    ("09:23", 22473.2, 22490.1, 22465.0, 22465.0, 9555.0),
    ("09:24", 22465.0, 22474.8, 22454.0, 22470.0, 20150.0),
    ("09:25", 22474.3, 22475.0, 22447.0, 22450.0, 27365.0),
    ("09:26", 22447.8, 22480.0, 22440.0, 22475.0, 39520.0),
    ("09:27", 22473.1, 22475.4, 22459.7, 22470.4, 12220.0),
    ("09:28", 22472.0, 22497.2, 22462.1, 22488.0, 35555.0),
    ("09:29", 22494.0, 22538.8, 22488.0, 22534.1, 25805.0),
    ("09:30", 22532.1, 22549.0, 22520.0, 22524.1, 32955.0),
    ("09:31", 22530.0, 22540.0, 22512.0, 22524.5, 10465.0),
    ("09:32", 22525.0, 22535.0, 22497.3, 22501.0, 12870.0),
]


def _flat1():
    """The candles as flat 1-min bars with their 1-min session bands (vwap_bands: the engine's own recurrence)."""
    return contract_bars.vwap_bands([{"t": t, "o": o, "h": h, "l": l, "c": c, "v": v, "oi": None}
                                     for t, o, h, l, c, v in OCT26_NIFTY_FUT_1M])


def _ones():
    """engine.session_json's 1-min rows: the fut leg with its 1-min bands, no option legs."""
    return [{"t": b["t"], "fut": b, "ce": None, "pe": None} for b in _flat1()]


def _out(interval=3, **day):
    import live
    return live._at_interval(dict({"bars": _ones(), "events": []}, **day), interval)


def test_the_3m_payload_carries_zone3_beside_zone_and_leaves_its_bars_alone():
    out = _out()
    n = len(out["bars"])
    assert len(out["bands3"]) == len(out["zone3_state"]) == len(out["zone3_state_sell"]) == n
    assert out["bars"] == list(contract_bars.resample_index(_ones(), 3))     # sampled 1-min bands, untouched
    assert out["zone_state"] == run_states(out["bars"], stop_pts=band_rotation.OPERATOR_STOP_PTS, band="d2")
    for k in (1, 5, 15):                                                     # a 3-minute rule: published at 3 only
        other = _out(k)
        assert not {"bands3", "zone3_state", "zone3_state_sell", "zone3_on"} & set(other)


def test_zone3_on_is_the_sessions_date_against_the_one_switch():
    """The screens' one switch: computed always, shown only from band_rotation.ZONE3_FROM. A session with no date is
    not shown -- never assumed late enough. A live session carries its ISO date from build_session."""
    import inspect
    import live
    assert _out(date="2026-10-27")["zone3_on"] is False
    assert _out(date="2026-10-28")["zone3_on"] is True
    assert _out()["zone3_on"] is False
    assert any(s["entry"] for s in _out(date="2026-10-27")["zone3_state"])  # computed before its date all the same
    assert 'js["date"] = today' in inspect.getsource(live.build_session)


def test_acceptance_26_oct_nifty_zone3_arms_0924_and_enters_0927():
    """The registration's acceptance (in-sample, described only): on 3-min bands the 09:24 bar's low 22,440.0 reached
    d2 22,445.1 and armed; the 09:27 close 22,534.1 beat the arm bar's high 22,480.0; stop 22,425.1. The 1-min-sigma
    zone armed nothing there: its d2 at that bar was 22,434.1."""
    out = _out()
    t = [b["t"] for b in out["bars"]]
    i24, i27 = t.index("09:24"), t.index("09:27")
    f24, f27 = out["bars"][i24]["fut"], out["bars"][i27]["fut"]
    assert f24["l"] == 22440.0 and round(out["bands3"][i24]["d2"], 1) == 22445.1
    assert out["zone3_state"][i24]["arm"] == {"rearm": False, "band": "d2", "extreme": 22440.0,
                                             "first_i": i24, "first_t": "09:24"}
    e = out["zone3_state"][i27]["entry"]
    assert e["side"] == "BUY" and e["band"] == "d2" and e["ref_high"] == 22480.0 and f27["c"] == 22534.1
    assert round(e["level"], 1) == 22445.1 and round(e["stop"], 1) == 22425.1
    assert round(f24["d2"], 1) == 22434.1                                     # the sampled 1-min d2
    assert all(s["arm"] is None and s["entry"] is None for s in out["zone_state"])
    assert all(s["arm"] is None for s in out["zone3_state_sell"])


# ---- Task 4: trigger_log logs zone3 under its own rule, from the one date --------------------------------------------

def _payload():
    return {"interval": 3, "days": [_out()]}


def _fresh(tmp_path):
    import trigger_log
    trigger_log._seen = None
    return str(tmp_path / "log.jsonl")


def test_zone3_is_logged_under_its_own_rule_with_its_bands_tag(tmp_path, monkeypatch):
    import trigger_log
    path = _fresh(tmp_path)
    monkeypatch.setattr(band_rotation, "ZONE3_FROM", "2000-01-01")
    assert trigger_log.log_new("NIFTY", _payload(), None, ones=_ones(), path=path) == 2
    arm, entry = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert (arm["kind"], arm["rule"], arm["bands_on"], arm["t"], arm["side"], arm["band"]) == \
        ("arm", "zone3", "3m", "09:24", "BUY", "d2")
    assert arm["extreme"] == 22440.0 and arm["ref_high"] == 22480.0 and round(arm["level"], 1) == 22445.1
    assert arm["t_1m"] == "09:26" and arm["interval"] == 3
    assert "kind" not in entry and (entry["rule"], entry["bands_on"], entry["t"], entry["px"]) == \
        ("zone3", "3m", "09:27", 22534.1)
    assert round(entry["level"], 1) == 22445.1
    assert trigger_log.log_new("NIFTY", _payload(), None, ones=_ones(), path=path) == 0      # written once


def test_before_its_date_zone3_is_computed_but_never_logged(tmp_path, monkeypatch):
    import trigger_log
    path = _fresh(tmp_path)
    monkeypatch.setattr(band_rotation, "ZONE3_FROM", "2999-01-01")
    pl = _payload()
    assert any(s["entry"] for s in pl["days"][0]["zone3_state"])            # computed
    assert trigger_log.log_new("NIFTY", pl, None, ones=_ones(), path=path) == 0
    assert not os.path.exists(path)


# ---- Task 5: scored on its own bands, shown apart ---------------------------------------------------------------------

def _rows():
    lvl = run_states(contract_bars.with_bands(_out()["bars"], _out()["bands3"]), band="d2", span=3)[4]["entry"]["level"]
    base = {"at": 1.0, "day": "2026-10-26", "index": "NIFTY", "side": "BUY", "band": "d2", "rule": "zone3",
            "bands_on": "3m", "level": lvl, "closed_bar": True}
    return [dict(base, kind="arm", interval=3, t="09:24", ref_high=22480.0, extreme=22440.0, rearm=False,
                 first_t="09:24"),
            dict(base, t="09:27", px=22534.1)]


def _cached(monkeypatch):
    """The scorer's own cache shape: squeeze_score.load's `resample(vwap_bands(...), 3)` -- sampled 1-min bands."""
    import trigger_log
    flat3 = contract_bars.resample(_flat1(), 3)
    monkeypatch.setattr(trigger_log, "_load_sessions",
                        lambda idx: {"2026-10-26": {"bars": flat3}} if idx == "NIFTY" else {})
    return flat3


def test_a_zone3_row_is_scored_on_its_own_bands_and_its_arm_replayed_with_its_span(tmp_path, monkeypatch):
    import trigger_log
    path = _fresh(tmp_path)
    flat3 = _cached(monkeypatch)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in _rows()) + "\n")
    changed, skipped = trigger_log.score(path, quiet=True)
    arm, entry = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert skipped == 0 and changed == 2
    assert arm["triggered"] is True and arm["trigger_t"] == "09:27" and arm["trigger_why"] is None
    assert round(arm["stop_px"], 1) == round(entry["stop_px"], 1) == 22425.1
    assert arm["bands_on"] == entry["bands_on"] == "3m"                       # the tag survives the scorer
    b3 = contract_bars.bands_on(flat3)[-1]                                   # the 09:30 bar, on 3-min bands
    assert entry["bands"]["u1"] == "09:30"
    assert entry["bands"]["sigma"] == round((22549.0 - b3["vwap"]) / (b3["vwap"] - b3["d1"]), 2)


def test_show_prints_zone3_apart_from_the_zone_and_arm_tables(tmp_path, capsys):
    import trigger_log
    path = _fresh(tmp_path)
    five = {"kind": "arm", "day": "2026-10-26", "index": "NIFTY", "t": "09:40", "side": "BUY", "band": "d3",
            "rule": "5c", "level": 22400.0, "extreme": 22399.0, "closed_bar": True}
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in _rows() + [five]) + "\n")
    trigger_log.show(path)
    out = capsys.readouterr().out
    assert "ZONE-3M (bands on 3-min bars, logged from 2026-10-28" in out and "1 entry, 1 arm row." in out
    assert "\n1 ARM rows" in out                                             # the 5c arm only
