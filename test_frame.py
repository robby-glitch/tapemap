# tapemap/test_frame.py
"""frame.py composes the five-question frame (spec §C + §E). Synthetic tape and book; no recorded day is a target."""
import frame


def _bar(i, o, h, l, c, delta=0, oi=100000):
    # bars start at 09:15 IST (frame._hhmm(1_780_026_340_000) == "09:15"): the warm-up rule is judged on the tape's own clock
    return {"t": (1000 * 60 * 5 * i) + 1_780_026_340_000, "o": o, "h": h, "l": l, "c": c, "delta": delta, "oi": oi}


def _tape(n=14):
    closed = [_bar(i, 23500 - 20 * i, 23510 - 20 * i, 23480 - 20 * i, 23490 - 20 * i, delta=-5, oi=100000 + 1000 * i) for i in range(n)]
    bands = [{"vwap": 23400.0, "sigma": 50.0, "d2": 23300.0, "d3": 23250.0, "u2": 23500.0, "u3": 23550.0}] * n
    return {"session": "NIFTY-I|5m|2026-09-15", "idx": "NIFTY", "closed": closed, "bands": bands, "rowSize": 5, "futPx": 23222.0, "lot": 65,
            "walls": [{"price": 23230.0, "side": -1, "size": 600, "hits": 1, "since": "15:20", "snapshot": False},
                      {"price": 23195.0, "side": 1, "size": 280, "hits": 3, "since": "09:20", "snapshot": True}],
            "broke": [{"side": 1, "brokenT": closed[3]["t"]}], "taps": [],
            # 23260.0, not 23300.0: inside the buy zone but more than one row from every wall/OI/prior-day row,
            # so it exercises the zone fallback in _place rather than colliding with the PDL level at 23300.0.
            "events": [{"t": closed[-1]["t"], "kind": "absorption", "p": 23230.0}, {"t": closed[-2]["t"], "kind": "initiative", "p": 23260.0}]}


def _book():
    # k=23100 (not 23200): placed at 23100+35=23135 in the futures frame, more than one row (5) from either
    # tape wall (S 23230, B 23195) -- the agreement tests set their own k when they want a match.
    return {"warmap": {"heat": [{"k": 23100, "ce_oi": 3e6, "ce_chg": 1e6, "ce_pain": 0, "ce_conf": 0.5, "pe_oi": 5e6, "pe_chg": 2e6, "pe_pain": 40.0, "pe_conf": 0.8}],
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
    assert f["record"]["written"] is False
    for blk in ("head", "where", "trapped", "walls", "tape", "setup"):
        assert "title" not in f[blk] and "items" not in f[blk], "no block chrome on the wire"


def test_where_numbers_and_edge_sign():
    w = frame.build(_tape(), _book(), "15:30")["where"]
    assert w["warm"] and w["px"] == 23222.0 and w["px_why"] is None and w["vwap"] == 23400.0 and w["sigma"] == 50.0
    assert abs(w["z"] - (-3.56)) < 0.01
    assert w["buy_zone"] == [23250.0, 23300.0] and w["sell_line"] == 23550.0 and w["sell_zone"] == [23500.0, 23550.0]
    assert w["edge"]["side"] == "buy" and w["edge"]["d"] == 23222.0 - 23300.0     # negative: price is past the −2σ edge
    assert isinstance(w["edge"]["d"], float)
    assert w["open"] == 23500 and w["high"]["p"] == 23510 and w["low"]["p"] == 23480 - 20 * 13
    assert w["from_open"] == 23222.0 - 23500 and isinstance(w["from_open"], float)
    assert w["off_extreme"]["which"] == "low" and isinstance(w["off_extreme"]["d"], float)
    assert w["hour"]["bars"] == 12 and w["hour"]["travel"] > 0 and isinstance(w["hour"]["net"], float)


def test_where_px_why_when_no_futures_price():
    t = _tape(); t["futPx"] = None
    w = frame.build(t, _book(), "15:30")["where"]
    assert w["px"] is None and w["px_why"] == "no futures price on the tape"
    assert w["z"] is None and w["edge"] is None      # covered by px_why, no separate why (spec ruling)


def test_where_before_warm_and_without_bands():
    t1 = _tape(); t1["closed"], t1["bands"] = t1["closed"][:1], t1["bands"][:1]   # one bar, 09:15, closes 09:20: the tape's clock is before 09:25 whatever the wall clock says
    w = frame.build(t1, _book(), "15:30")["where"]
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
    assert tape_rows["S"]["pain_tag"] is None and tape_rows["S"]["strike"] is None    # CE/PE only (spec ruling)
    oi = [r for r in W["rows"] if r["kind"] == "PE"][0]
    assert oi["p"] == 23100 + (23222.0 - 23187.0) and oi["pain"] == 40.0 and oi["pain_tag"] == "I" and oi["agree"] is None
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


def test_walls_agreement_exactly_one_row_is_inclusive():
    """Spec ruling: "within one row" is inclusive, not exclusive -- a strike exactly one rowSize (5 here) from
    a wall agrees with it. (An earlier plan fixture put a strike exactly one row away and asserted NO
    agreement; that fixture was wrong, not the rule.)"""
    t, b = _tape(), _book()
    b["spot"] = 23222.0 - 35.0
    b["warmap"]["heat"][0]["k"] = 23195.0 - 35.0 + 5      # exactly one row (5 pts) from the B wall
    W = frame.build(t, b, "15:30")["walls"]
    bw = [r for r in W["rows"] if r["kind"] == "B"][0]; pe = [r for r in W["rows"] if r["kind"] == "PE"][0]
    assert bw["agree"] == f"PE {23195.0 - 35.0 + 5:.0f}" and pe["agree"] == "B 23195"


def test_walls_absences():
    t, b = _tape(), _book()
    b["warmap"] = None; b["pivots"] = None
    W = frame.build(t, b, "15:30")["walls"]
    assert W["oi_why"] == "tapemap did not answer" and W["prior_why"] and [r["kind"] for r in W["rows"]] == ["S", "B"]
    b = _book(); b["spot"] = None
    assert "spot" in frame.build(t, b, "15:30")["walls"]["oi_why"]


def test_trapped():
    T = frame.build(_tape(), _book(), "15:30")["trapped"]
    assert T["writers"]["side"] == "PE" and T["writers"]["worst"] == {"k": 23100, "pain": 40.0, "conf": 0.8} and T["writers"]["tag"] == "I"
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


def test_tape_event_at_a_prior_day_level_is_a_level_not_a_wall():
    """spec ruling: tape.events[].at.kind is "level" (not "wall") for PDH/PDL/PDC/ROUND/FLIP rows, label
    "at PDH 23500"; a wall wins a tie against a level at the same distance."""
    t = _tape()
    t["events"] = [{"t": t["closed"][-1]["t"], "kind": "initiative", "p": 23300.0}]      # exactly the PDL row
    Tp = frame.build(t, _book(), "15:30")["tape"]
    assert Tp["events"][0]["at"] == {"kind": "level", "label": "at PDL 23300"}


def test_a_down_tell_targets_below_its_own_trigger():
    """8 Oct 09:30: the DOWN tell's trigger was the biggest PE pool 300 pts away (close < 22,250) and its target the
    -3 sigma band 22,524 -- above the trigger, so score_frame scored it as an UP tell and called it falsified."""
    heat = [{"k": 22200, "pe_oi": 7e6, "ce_oi": 1e6}, {"k": 22400, "pe_oi": 5.7e6, "ce_oi": 1e6},
            {"k": 22100, "pe_oi": 4e6, "ce_oi": 1e6}, {"k": 22600, "pe_oi": 1e6, "ce_oi": 9e6}]
    closed, bn = [{"c": 22510.0}], {"d3": 22524.0}
    down = [t for t in frame._tells({"warmap": {"heat": heat}}, closed, 50.0, bn) if t["name"] == "DOWN"][0]
    trig = float(down["negation"].split()[-1])
    assert down["k"] == 22200 and trig == 22250.0
    assert float(down["target"]) == 22150.0 < trig                 # the next pool under the floor, not the band above
    alone = [h for h in heat if h["k"] != 22100]                     # no pool under the floor and -3 sigma above it
    down = [t for t in frame._tells({"warmap": {"heat": alone}}, closed, 50.0, bn) if t["name"] == "DOWN"][0]
    assert down["target"] is None


def test_setup_falsifier_carries_the_number_and_no_else_tell():
    S = frame.build(_tape(), _book(), "15:30")["setup"]
    assert S["side"] == "buy" and S["state"] == "PATA NAHI" and "run_states" in S["state_why"]
    assert len(S["state_why"]) <= 48
    assert S["falsifies"] == "a close past 23250 (−3σ) held for 3 bars"
    assert S["confirm"] == {"value": "not wired", "why": "senses assembly not factored out; tape-only beep",
                             "why_full": "the /api/senses assembly is not factored out yet; the beep is tape-only", "tag": "I"}
    assert len(S["confirm"]["why"]) <= 48
    assert all(t["name"] != "ELSE" for t in S["tells"]) and all(t["tag"] == "I" for t in S["tells"])
    assert "trap" not in S
    t1 = _tape(); t1["closed"], t1["bands"] = t1["closed"][:1], t1["bands"][:1]   # one bar closed at 09:20: WARMUP on the tape's clock, not the wall clock
    S = frame.build(t1, _book(), "15:30")["setup"]
    assert S["state"] == "WARMUP" and S["falsifies"] == "nothing to falsify before σ exists"


def test_setup_ref_is_ref_high_on_buy_and_ref_low_on_sell():
    """spec ruling (Task 4 review): setup.ref replaces setup.ref_high, reading ref_high off the buy machine
    and ref_low off the sell machine (band_rotation.run_states emits ref_low for SELL)."""
    t = _tape()
    buy_last = {"state": "ARMED", "ref_i": 5, "ref_high": 23310.0, "level": 23300.0, "candles_left": 4}
    S = frame.build(t, dict(_book(), zone_state=[buy_last]), "15:30")["setup"]
    assert S["side"] == "buy" and S["ref"] == 23310.0 and "ref_high" not in S
    sell_last = {"state": "ARMED", "ref_i": 5, "ref_low": 23540.0, "level": 23550.0, "candles_left": 4}
    b = dict(_book(), zone_state=None, zone_state_sell=[sell_last])
    S = frame.build(t, b, "15:30")["setup"]
    assert S["side"] == "sell" and S["ref"] == 23540.0


def test_each_object_fails_alone():
    t = _tape(); t["walls"] = [{"price": "bad"}]        # raises inside walls only
    f = frame.build(t, _book(), "15:30")
    assert f["walls"]["rows"] == [] and f["walls"]["why"] and f["where"]["z"] is not None and f["setup"]["falsifies"]


def test_missing_and_events_strip():
    f = frame.build(_tape(), {"coverage": {}}, "15:30")
    assert set(f["missing"]) == {"warmap", "chain minutes"}
    assert {e["kind"] for e in f["events"]} >= {"absorption", "initiative", "wall", "lost"}
    assert f["events_why"] is None


def test_window_change_is_a_difference_of_cumulative_marks():
    minutes = {"09:16": {"k": {"23300": (10e6, 5e6)}}, "09:31": {"k": {"23300": (15e6, 3e6)}}}
    assert frame.window_change(minutes, "09:16", "09:31") == {23300: (5e6, -2e6)}
    assert frame.window_change(minutes, "09:16", "09:20") == {}      # a mark missing on either end is an empty answer


def test_a_level_with_no_machine_state_is_not_a_row():
    """A warmap level with no sequence-machine state is not a row (the chart draws the line); one with state
    is, carrying state/tests/last_outcome."""
    t, b = _tape(), _book()
    b["warmap"]["levels"] = [{"kind": "ROUND", "px": 23300.0, "frame": "index"}]
    W = frame.build(t, b, "15:30")["walls"]
    assert "ROUND" not in {r["kind"] for r in W["rows"]}
    b["warmap"]["sequence"] = {"ROUND@23300.0": {"state": "held", "tests": 2, "last_outcome": "bounce"}}
    W = frame.build(t, b, "15:30")["walls"]
    row = next(r for r in W["rows"] if r["kind"] == "ROUND")
    assert row["state"] == "held" and row["tests"] == 2 and row["last_outcome"] == "bounce"


def _why_pairs(node, skip=("state",)):
    """Every (dict, key, value, why) where `key` has a sibling `f'{key}_why'` in the same dict, except `state`
    (setup.state's hole value is the string "PATA NAHI", not None, and state_why also annotates the non-hole
    WARMUP state -- a different, documented pattern, so it is the one field this sweep does not check)."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k not in skip and not k.endswith("_why") and f"{k}_why" in node:
                yield node, k, v, node[f"{k}_why"]
        for v in node.values():
            yield from _why_pairs(v, skip)
    elif isinstance(node, list):
        for item in node:
            yield from _why_pairs(item, skip)


def test_every_why_is_non_null_exactly_when_its_field_is_null():
    """The contract's own rule: every field that can be null carries a sibling `*_why` that is non-null exactly
    when the field is null. Walked recursively over build()'s whole output, on three inputs: the full fixture,
    an empty book, and a tape with no futures price."""
    frames = [frame.build(_tape(), _book(), "15:30"),
              frame.build(_tape(), {}, "15:30"),
              frame.build(dict(_tape(), futPx=None), _book(), "15:30")]
    checked = 0
    for f in frames:
        for _, k, v, why in _why_pairs(f):
            assert (v is None) == (why is not None), f"{k}: value={v!r} why={why!r}"
            checked += 1
    assert checked > 0, "the sweep found no x/x_why pairs at all -- it is not walking the frame"


def test_the_signal_and_the_ballot_ride_on_the_setup():
    f = frame.build(_tape(), _book(), "15:30")
    S = f["setup"]
    assert "signal" in S and "votes" in S
    assert S["signal"]["visit_key"] == S["visit"], "one visit key, not two"
    assert S["signal"]["intent"] == "fade to VWAP"
    assert S["votes"]["of"] == 4 and S["votes"]["threshold"] == 1
    assert len(S["votes"]["items"]) == 4


def test_breadth_says_it_could_not_check_when_the_chain_has_no_two_marks():
    b = _book(); b["minutes"] = {}
    B = frame.build(_tape(), b, "15:30")["breadth"]
    assert B["t0"] is None and B["written_ce"] is None
    assert B["counts_why"] and len(B["counts_why"]) <= 48
    assert B["strikes_seen"] == 0, "a count of nothing, not a missing count"


def test_the_watch_list_rides_under_walls_and_carries_its_permanent_header():
    import watch
    f = frame.build(_tape(), _book(), "15:30")
    W = f["walls"]["watch"]
    assert W["cap"] == 8 and W["note"] == watch.NOTE
    assert (W["why"] is not None) == (W["rows"] == [])


def test_breadth_is_a_top_level_object_with_no_direction_in_it():
    import breadth as br
    import json as _json
    f = frame.build(_tape(), _book(), "15:30")
    B = f["breadth"]
    assert B["window_min"] == 15 and B["note"] == br.NOTE
    blob = _json.dumps(B).upper()
    for banned in br.BANNED_WORDS:
        assert banned not in blob


def test_the_depth_vote_is_measurable_once_sweeps_are_on_the_book():
    b = _book()
    b["sweeps"] = [{"det": "sweep", "kind": "swept", "side": "buy", "qty": 100.0,
                    "t": "10:05:10", "inst": "NIFTY-FUT"}] * 6
    f = frame.build(_tape(), b, "15:30")
    d = next(i for i in f["setup"]["votes"]["items"] if i["key"] == "depth")
    assert d["ok"] is not None, "with rows on the book DEPTH is no longer unknowable"


def test_the_ballot_never_sees_a_level_row():
    """§H.1 by construction: only CE/PE rows are handed over, so a PDH or a
    tape wall cannot originate anything. If the composer ever hands the whole
    ladder across, signals._only_oi raises, _safe turns the whole setup into
    its own `why`, and this assertion is what catches it."""
    f = frame.build(_tape(), _book(), "15:30")
    assert "why" not in f["setup"], f["setup"].get("why")
    assert "why" not in f["walls"], f["walls"].get("why")


def test_a_degenerate_sigma_is_not_warm_even_after_the_anchor():
    """2026-09-17 09:32: sigma 1.41 against a 23,300 price, past 09:25, so `warm` was True and z
    printed +31 with the sell zone thirty points BELOW price. A time gate is not a quality gate.
    With the reach latched that phantom visit consumes the side's first ordinal and silences the
    real one. The band must be wide enough that 2 sigma names a zone."""
    v = 23286.0
    narrow = {"vwap": v, "sigma": 1.41, "d2": v - 2.82, "d3": v - 4.23, "u2": v + 2.82, "u3": v + 4.23}
    tape = {"bands": [narrow], "futPx": 23320.0, "rowSize": 5}
    w = frame._where(tape, [], "09:32")
    assert w["warm"] is False
    assert w["z"] is None
    assert w["buy_zone"] is None and w["sell_zone"] is None
    assert "too narrow" in w["zone_why"]

    # the same minute with a real session band stays warm and still measures z
    real = {"vwap": v, "sigma": 18.0, "d2": v - 36, "d3": v - 54, "u2": v + 36, "u3": v + 54}
    w2 = frame._where({**tape, "bands": [real]}, [], "09:32")
    assert w2["warm"] is True
    assert w2["z"] is not None
    assert w2["zone_why"] is None


def test_the_futures_oi_is_blind_in_the_expiry_week():
    """P1-02: the tape day is 15 Sep; a future expiring 16 Sep is rolling, one expiring 29 Sep is not."""
    b = _book(); b["fut_expiry"] = "2026-09-16"
    T = frame.build(_tape(), b, "15:30")["trapped"]
    assert T["fut_oi"] is None and T["fut_oi_why"] == "the Sep future is rolling into Oct"
    b["fut_expiry"] = "2026-09-29"
    assert frame.build(_tape(), b, "15:30")["trapped"]["fut_oi"] == {"d_oi": 13000, "d_px": round(23230 - 23500, 1)}


def test_the_frame_carries_the_upstox_oi_reference_with_its_why():
    """P1-05: the contract match needs an OI that is not GoCharting's own."""
    f = frame.build(_tape(), _book(), "15:30")
    assert f["ux_oi"] is None and f["ux_oi_why"] == "no closed Upstox ladder bar yet"
    b = _book(); b["ux_oi"] = [{"t": 1, "oi": 100}]
    f = frame.build(_tape(), b, "15:30")
    assert f["ux_oi"] == [{"t": 1, "oi": 100}] and f["ux_oi_why"] is None
