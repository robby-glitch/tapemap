# tapemap/test_frame.py
"""frame.py composes the five-question frame (spec §C + §E). Synthetic tape and book; no recorded day is a target."""
import frame


def _bar(i, o, h, l, c, delta=0, oi=100000):
    return {"t": (1000 * 60 * 5 * i) + 1_780_000_000_000, "o": o, "h": h, "l": l, "c": c, "delta": delta, "oi": oi}


def _tape(n=14):
    closed = [_bar(i, 23500 - 20 * i, 23510 - 20 * i, 23480 - 20 * i, 23490 - 20 * i, delta=-5, oi=100000 + 1000 * i) for i in range(n)]
    bands = [{"vwap": 23400.0, "sigma": 50.0, "d2": 23300.0, "d3": 23250.0, "u2": 23500.0, "u3": 23550.0}] * n
    return {"session": "NIFTY-I|5m|2026-09-15", "idx": "NIFTY", "closed": closed, "bands": bands, "rowSize": 5, "futPx": 23222.0, "lot": 65,
            "walls": [{"price": 23230.0, "side": -1, "size": 600, "hits": 1, "since": "15:20", "snapshot": False},
                      {"price": 23195.0, "side": 1, "size": 280, "hits": 3, "since": "09:20", "snapshot": True}],
            "broke": [{"side": 1, "brokenT": closed[3]["t"]}], "taps": [],
            "events": [{"t": closed[-1]["t"], "kind": "absorption", "p": 23230.0}, {"t": closed[-2]["t"], "kind": "initiative", "p": 23300.0}]}


def _book():
    return {"warmap": {"heat": [{"k": 23200, "ce_oi": 3e6, "ce_chg": 1e6, "ce_pain": 0, "ce_conf": 0.5, "pe_oi": 5e6, "pe_chg": 2e6, "pe_pain": 40.0, "pe_conf": 0.8}],
                       "levels": [], "sequence": {}},
            "minutes": {"15:26": {"k": {"23200": (1e6, 2e6)}}, "15:27": {"k": {"23200": (1.5e6, 2.1e6)}}, "15:28": {"k": {"23200": (2e6, 2.2e6)}}, "15:29": {"k": {"23200": (3e6, 2.5e6)}}},
            "spot": 23187.0, "expiry": "2026-09-29", "zone_state": None, "zone_state_sell": None, "vpin_pct": 0.3, "senses": None, "ivrv": None,
            "pivots": {"P": 23400.0, "R1": 23500.0, "S1": 23300.0, "R2": 23600.0, "S2": 23200.0, "R3": 23700.0, "S3": 23100.0},
            "coverage": {"server_up": "09:14", "late_min": 0, "reconstructed": [], "not_reconstructable": []}}


def test_shape_and_head():
    f = frame.build(_tape(), _book(), "15:30")
    assert set(f) >= {"ok", "idx", "ts", "day", "interval", "have_bars", "lot", "missing", "coverage", "events", "taps", "head", "record", "where", "trapped", "walls", "tape", "setup"}
    assert f["day"] == "2026-09-15" and f["interval"] == "5m" and f["have_bars"] == 14
    assert f["head"]["symbol"] == "NIFTY-I" and f["head"]["expiry"] == "2026-09-29" and f["head"]["dte"] == 14
    assert f["head"]["gate"]["level"] == "PATA NAHI" and f["head"]["gate"]["tag"] == "I"
    assert f["record"] == {"written": False}
    for blk in ("head", "where", "trapped", "walls", "tape", "setup"):
        assert "title" not in f[blk] and "items" not in f[blk], "no block chrome on the wire"


def test_where_numbers_and_edge_sign():
    w = frame.build(_tape(), _book(), "15:30")["where"]
    assert w["warm"] and w["px"] == 23222.0 and w["vwap"] == 23400.0 and w["sigma"] == 50.0
    assert abs(w["z"] - (-3.56)) < 0.01
    assert w["buy_zone"] == [23250.0, 23300.0] and w["sell_line"] == 23550.0
    assert w["edge"]["side"] == "buy" and w["edge"]["d"] == 23222.0 - 23300.0     # negative: price is past the −2σ edge
    assert w["open"] == 23500 and w["high"]["p"] == 23510 and w["low"]["p"] == 23480 - 20 * 13
    assert w["from_open"] == 23222.0 - 23500 and w["off_extreme"]["which"] == "low"
    assert w["hour"]["bars"] == 12 and w["hour"]["travel"] > 0 and isinstance(w["hour"]["net"], float)


def test_where_before_warm_and_without_bands():
    w = frame.build(_tape(), _book(), "09:20")["where"]
    assert not w["warm"] and w["z"] is None and w["buy_zone"] is None and "09:25" in w["zone_why"]
    t = _tape(); t["bands"] = []
    w = frame.build(t, _book(), "15:30")["where"]
    assert w["z"] is None and w["zone_why"] == "no bands on the tape yet"


def test_walls_rows_prior_day_and_agreement():
    W = frame.build(_tape(), _book(), "15:30")["walls"]
    assert all(W["rows"][i]["p"] >= W["rows"][i + 1]["p"] for i in range(len(W["rows"]) - 1))
    tape_rows = {r["kind"]: r for r in W["rows"] if r["kind"] in ("S", "B")}
    assert tape_rows["S"]["size"] == 600 * 65 and tape_rows["S"]["leaned"] == 1 and tape_rows["B"]["snapshot"] is True
    assert tape_rows["S"]["agree"] is None
    oi = [r for r in W["rows"] if r["kind"] == "PE"][0]
    assert oi["p"] == 23200 + (23222.0 - 23187.0) and oi["pain"] == 40.0 and oi["pain_tag"] == "I" and oi["agree"] is None
    prior = {r["kind"]: r["p"] for r in W["rows"] if r["kind"] in ("PDH", "PDL", "PDC")}
    assert prior == {"PDH": 23500.0, "PDL": 23300.0, "PDC": 23400.0}     # H = 2P − S1, L = 2P − R1, C = 3P − H − L
    assert W["prior_why"] is None and W["basis"] == 35.0 and W["cap"] == 3 and W["floors_taken"] == 1
    assert all(r["d"] == round(r["p"] - 23222.0, 1) for r in W["rows"])


def test_walls_agreement_within_one_row():
    t, b = _tape(), _book()
    b["spot"] = 23222.0 - 35.0
    b["warmap"]["heat"][0]["k"] = 23195.0 - 35.0 + 3      # a PE strike three points from the B wall in the futures frame
    W = frame.build(t, b, "15:30")["walls"]
    bw = [r for r in W["rows"] if r["kind"] == "B"][0]; pe = [r for r in W["rows"] if r["kind"] == "PE"][0]
    assert bw["agree"] == f"PE {23195.0 - 35.0 + 3:.0f}" and pe["agree"] == "B 23195"


def test_walls_absences():
    t, b = _tape(), _book()
    b["warmap"] = None; b["pivots"] = None
    W = frame.build(t, b, "15:30")["walls"]
    assert W["oi_why"] == "tapemap did not answer" and W["prior_why"] and [r["kind"] for r in W["rows"]] == ["S", "B"]
    b = _book(); b["spot"] = None
    assert "spot" in frame.build(t, b, "15:30")["walls"]["oi_why"]


def test_trapped():
    T = frame.build(_tape(), _book(), "15:30")["trapped"]
    assert T["writers"]["side"] == "PE" and T["writers"]["worst"] == {"k": 23200, "pain": 40.0, "conf": 0.8} and T["writers"]["tag"] == "I"
    assert T["writers"]["ce_chg"] == 1e6 and T["writers"]["pe_chg"] == 2e6
    assert T["window"]["t0"] == "15:26" and T["window"]["t1"] == "15:29" and T["window"]["minutes"] == 3 and T["window"]["ce"] == 2e6
    assert T["pace"]["ce"] == 1.0 and 0 < T["pace"]["pe"] <= 1
    assert T["fut_oi"] == {"d_oi": 13000, "d_px": round(23230 - 23500, 1)}
    assert T["gear"] is None and T["gear_why"] == "senses not answered"
    b = _book(); b["warmap"] = None; b["minutes"] = None
    T = frame.build(_tape(), b, "15:30")["trapped"]
    assert T["writers"] is None and T["writers_why"] and T["window"] is None and T["window_why"] and T["pace"] is None and T["pace_why"]


def test_tape_events_named_by_place():
    Tp = frame.build(_tape(), _book(), "15:30")["tape"]
    assert Tp["events"][0]["kind"] == "absorption" and Tp["events"][0]["at"] == {"kind": "wall", "label": "at S 23230"}
    assert Tp["events"][1]["kind"] == "initiative" and Tp["events"][1]["at"] == {"kind": "zone", "label": "in the buy zone"}
    assert Tp["aggressor"] == {"side": "sellers", "rank": None}
    t = _tape(); t["events"] = []; t["closed"] = []
    Tp = frame.build(t, _book(), "15:30")["tape"]
    assert Tp["events"] == [] and Tp["aggressor"] is None and Tp["aggressor_why"]


def test_setup_falsifier_carries_the_number_and_no_else_tell():
    S = frame.build(_tape(), _book(), "15:30")["setup"]
    assert S["side"] == "buy" and S["state"] == "PATA NAHI" and "run_states" in S["state_why"]
    assert S["falsifies"] == "a close past 23250 (−3σ) held for 3 bars"
    assert S["confirm"] == {"value": "not wired", "why": "the /api/senses assembly is not factored out yet; the beep is tape-only", "tag": "I"}
    assert all(t["name"] != "ELSE" for t in S["tells"]) and all(t["tag"] == "I" for t in S["tells"])
    assert "trap" not in S
    S = frame.build(_tape(), _book(), "09:20")["setup"]
    assert S["state"] == "WARMUP" and S["falsifies"] == "nothing to falsify before σ exists"


def test_each_object_fails_alone():
    t = _tape(); t["walls"] = [{"price": "bad"}]        # raises inside walls only
    f = frame.build(t, _book(), "15:30")
    assert f["walls"]["rows"] == [] and f["walls"]["why"] and f["where"]["z"] is not None and f["setup"]["falsifies"]


def test_missing_and_events_strip():
    f = frame.build(_tape(), {"coverage": {}}, "15:30")
    assert set(f["missing"]) == {"warmap", "chain minutes"}
    assert {e["kind"] for e in f["events"]} >= {"absorption", "initiative", "wall", "lost"}
