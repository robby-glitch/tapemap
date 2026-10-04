# tapemap/test_validate_live.py
"""The Validate build (Mary's validate-tab-spec.md, her decisions 2026-10-05 00:45, adapted to her house rules): the trade
record's thesis / roles / acks / re-plans / tags on /api/hold/trades, the live in-trade read (/api/validate), and its
minute log. The spec's §10 acceptance tests, adapted: lamps AUTO, no candle-close gate, no order path, the engine's word
the decision, the spec's own action words logged beside it as `shadow`."""
import json
import os

import pytest

import decoder_log
import server
import story
import trade_record
import validate_live
from test_frame_api import _Req
from test_story_panel import _fold, _post_marked

DAY = "2026-09-11"
M = lambda hm: story.day_ms(DAY, hm)                                  # noqa: E731
FX = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_validate_30sep.json"), encoding="utf-8"))
TR = {"id": "NIFTY-22800CE-long-100000", "idx": "NIFTY", "k": 22800.0, "side": "CE", "role": "long", "t0": "10:00:00", "p0": 120.0,
      "qty": 0, "exit_t": None}


def _bars(n=12, o=22800.0, rng=20.0):
    return [{"t": M("09:15") + i * 300000, "o": o, "h": o + rng / 2, "l": o - rng / 2, "c": o} for i in range(n)]


def _view(chips=("WITH", "QUIET", "WITH", "QUIET"), fut=22800.0, E=22800.0, G=22760.0, A=22850.0, events=(), clause="", headline="HOLD"):
    f = _fold(entry="10:00", E=E, fut=fut, events=events, headline=headline)
    f["view"].update(chips=dict(zip("ZFOV", chips)), sentences={}, G={"px": G}, A={"px": A}, clause=clause)
    return f


def _read(tr=None, fold=None, now="10:30", closed=None, **kw):
    return validate_live.read(dict(TR) if tr is None else tr, fold or _view(), DAY, M(now), _bars() if closed is None else closed, **kw)


# ---- 30 SEP, her 22750 CE: replayed through the live read at 10:35 and 11:10 -------------------------------------
def _fx(now):
    m = FX["moments"][now]
    return validate_live.read(FX["trade"], m["fold"], FX["day"], story.day_ms(FX["day"], now), m["closed"], m["decoder"], m["vwap"],
                              m["forming"], m["chain"], m["walls"], [FX["trade"]])


def test_30_sep_at_10_35_the_reversal_count_is_already_two_or_more_while_the_engine_says_hold():
    v = _fx("10:35:10")
    assert v["word"] == "HOLD", "the engine's word, verbatim: it held for another 41 minutes"
    assert v["reversal"]["met"] >= 2, v["reversal"]
    met = {x["key"] for x in v["reversal"]["items"] if x["met"]}
    assert {"initiation", "writing"} <= met, met                    # PEHAL ▼ 10:30 and 22750 CE written 43.5L -> 49.2L
    assert v["lamps"]["oi"]["state"] == "R" and v["lamps"]["oi"]["since"].startswith("10:35") and not v["lamps"]["oi"]["acked"]
    assert v["shadow"]["cut_2of4"] and v["shadow"]["word"] == "CUT", "the spec's CUT rides beside the engine, unsigned"
    assert v["level"]["inval"] == 22769 and v["level"]["to_inval"] > 0 and v["noise_floor"] > 0


def test_30_sep_at_11_10_the_read_still_answers_and_vpin_is_against():
    v = _fx("11:10:40")
    assert v["word"] == "HOLD" and v["lamps"]["vpin"]["state"] == "R" and v["lamps"]["oi"]["since"] == "10:35:00"
    assert v["reversal"]["of"] == 4 and all(x["text"] for x in v["reversal"]["items"])


# ---- §10.1 no exit prompt on AMBER --------------------------------------------------------------------------------
def test_with_flow_amber_no_exit_prompt_and_the_word_stays_the_engines():
    v = _read(fold=_view(chips=("WITH", "QUIET", "QUIET", "QUIET"), fut=22790.0))
    assert v["word"] == "HOLD" and v["prompt"] is None and v["prompt_why"]
    assert v["shadow"]["amber_no_exit"] and v["shadow"]["word"] == "HOLD — pullback, not reversal"
    f = _read(fold=_view(chips=("WITH", "QUIET", "QUIET", "QUIET"), fut=22790.0, headline="FOLD · 22769 accepted · 10:29"))
    assert f["word"].startswith("FOLD") and f["shadow"]["amber_no_exit"], "FOLD stays FOLD; the spec's hold is only logged"


# ---- §10.3 / §10.4 the noise floor and the trail lock ---------------------------------------------------------------
def test_the_trail_is_locked_until_t1_or_1r_and_a_trail_inside_noise_is_warned():
    v = _read()
    assert v["noise_floor"] == 30.0 and not v["trail_unlock"]["unlocked"] and v["trail_unlock"]["at"] == 22840.0, v["trail_unlock"]
    up = _read(fold=_view(fut=22852.0))                             # past T1 22850: unlocked, a trail proposed at structure
    assert up["trail_unlock"]["unlocked"] and up["trail_unlock"]["proposal"] == 22790.0
    near = _read(fold=_view(fut=22852.0), closed=_bars()[:-3] + [{"t": M("10:15"), "o": 22840, "h": 22855, "l": 22840, "c": 22850}] * 3)
    assert near["trail_unlock"]["inside_noise"] and "inside noise" in near["trail_unlock"]["warn"], near["trail_unlock"]


# ---- §10.5 over-lot exits are impossible; §10.2 friction + FEAR_EXIT --------------------------------------------------
def test_a_role_cannot_record_more_lots_out_than_it_holds():
    tr = dict(TR, roles=[{"id": "CORE", "role": "CORE", "lots": 1}, {"id": "BANKER", "role": "BANKER", "lots": 1}])
    assert "holds 1 lot" in trade_record.apply(tr, "role_exit", {"role_id": "BANKER", "lots": 2}, "10:20:00", 0)
    assert trade_record.apply(tr, "role_exit", {"role_id": "BANKER", "exit_reason": "TARGET_1", "exit_px": 140}, "10:20:00", 0) is None
    assert "no open lot BANKER" in trade_record.apply(tr, "role_exit", {"role_id": "BANKER"}, "10:21:00", 0), "already out"
    assert not tr.get("exit_t"), "CORE still in: the trade is open"
    assert trade_record.apply(tr, "role_exit", {"role_id": "CORE", "exit_reason": "TARGET_2"}, "10:40:00", 5.0) is None
    assert tr["exit_t"] == "10:40:00" and tr["exit_at"] == 5.0, "every lot out: the trade's own exit is set, the engine freezes"


def test_an_old_mark_without_roles_is_one_core_lot():
    rs = trade_record.roles(dict(TR, qty=0))
    assert len(rs) == 1 and rs[0]["role"] == "CORE" and rs[0]["lots"] == 1


def test_fear_exit_is_tagged_by_her_word_or_by_the_clock():
    tr = dict(TR)
    assert trade_record.apply(tr, "role_exit", {"role_id": "CORE", "exit_reason": "FEAR_EXIT", "exit_note": "scared of the 22800 wall"}, "10:05:00", 1) is None
    assert "FEAR_EXIT" in tr["tags"] and tr["roles"][0]["exit_note"].startswith("scared")
    read = {"timer": {"fear_zone": True}, "reversal": {"met": 0}, "shadow": {"amber_no_exit": True}, "lamps": {"flow": {"state": "A"}}}
    tr2 = dict(TR)
    trade_record.apply(tr2, "role_exit", {"role_id": "CORE"}, "10:05:00", 1, read)
    assert {"FEAR_EXIT", "AMBER_EXIT"} <= set(tr2["tags"]) and tr2["lamps_at_exit"] == {"flow": "A"} and tr2["reversal_at_exit"] == 0
    tr3 = dict(TR)
    trade_record.apply(tr3, "role_exit", {"role_id": "CORE"}, "10:05:00", 1, {**read, "reversal": {"met": 2}, "shadow": {}})
    assert "FEAR_EXIT" not in tr3.get("tags", []), "two reversal conditions met: a reason, not fear"


def test_the_fear_clock_runs_from_green_by_the_noise_floor():
    closed = _bars(9) + [{"t": M("10:00"), "o": 22800, "h": 22835, "l": 22795, "c": 22830}]
    v = _read(fold=_view(fut=22831.0), closed=closed, now="10:06")
    assert v["timer"]["green_since"] == "10:00:00" and v["timer"]["fear_zone"], v["timer"]
    late = _read(fold=_view(fut=22831.0), closed=closed, now="10:30")
    assert not late["timer"]["fear_zone"], "past a third of the typical 20 min"


# ---- §10.7 add gating, §6 acks -----------------------------------------------------------------------------------------
def test_an_add_only_when_flow_just_went_amber_to_green_and_not_within_two_bars_of_an_add():
    turn = [{"kind": "chip", "chip": "FLOW", "old": "QUIET", "new": "WITH", "t": M("10:28"), "ts": "10:28:00"}]
    v = _read(fold=_view(chips=("WITH", "WITH", "WITH", "QUIET"), events=turn))
    assert v["add"]["ok"] and v["add"]["add_stop"] == 22790.0, v["add"]
    assert not _read(fold=_view(chips=("WITH", "WITH", "WITH", "QUIET"), events=turn), now="10:40")["add"]["ok"], "the turn is older than a bar"
    assert not _read(fold=_view(chips=("WITH", "WITH", "WITH", "QUIET")))["add"]["ok"], "green all along is not a turn"
    tr = dict(TR)
    assert trade_record.apply(tr, "role_add", {"lots": 1, "add_stop": 22790, "entry_px": 130}, "10:26:00", 0) is None
    w = _read(tr=tr, fold=_view(chips=("WITH", "WITH", "WITH", "QUIET"), events=turn))
    assert not w["add"]["ok"] and "2 bars" in w["add"]["why"]
    assert [r["role"] for r in w["roles"]] == ["CORE", "ADD"] and w["roles"][1]["add_stop"] == 22790.0


def test_a_lamp_change_is_unacknowledged_until_she_clicks_it_and_the_ack_is_logged():
    ch = [{"kind": "chip", "chip": "OI", "old": "WITH", "new": "AGAINST", "t": M("10:20"), "ts": "10:20:00"}]
    tr = dict(TR)
    v = _read(tr=tr, fold=_view(chips=("WITH", "QUIET", "AGAINST", "QUIET"), events=ch))
    assert v["lamps"]["oi"] == {**v["lamps"]["oi"], "state": "R", "from": "G", "since": "10:20:00", "acked": False}
    assert trade_record.apply(tr, "ack", {"lamp": "oi", "from": "G", "to": "R", "t": "10:21:00"}, "10:21:00", 0) is None
    assert tr["acks"] == [{"t": "10:21:00", "lamp": "oi", "from": "G", "to": "R"}]
    assert _read(tr=tr, fold=_view(chips=("WITH", "QUIET", "AGAINST", "QUIET"), events=ch))["lamps"]["oi"]["acked"]


def test_replan_moves_targets_only_and_the_invalidation_is_locked():
    tr = dict(TR, thesis={"why": "seller exhaustion at -2σ", "t1": 22850, "t2": 22900, "inval": 22760, "src": {}, "locked_at": "10:00:00"})
    assert "targets only" in trade_record.apply(tr, "replan", {"t1": 22870, "inval": 22700}, "10:30:00", 0)
    assert trade_record.apply(tr, "replan", {"t2": 22950}, "10:30:00", 0) is None
    assert tr["thesis"]["t2"] == 22950 and tr["thesis"]["inval"] == 22760 and tr["replan"] == [{"t": "10:30:00", "t1": None, "t2": 22950.0}]
    assert "locked at entry" in trade_record.apply(tr, "thesis", {"thesis": {"inval": 22700}}, "10:31:00", 0)


# ---- the door: thesis + roles on a mark, FLIP and COOLDOWN warned and tagged, never refused --------------------------
@pytest.fixture
def door(monkeypatch):
    monkeypatch.setattr(server, "_HOLD", {"facts": {}, "locks": {}, "trades": [], "trades_day": None, "sigma": {}, "peaks": {}})
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "10:30"))
    monkeypatch.setattr(server, "_VAL_LAST", {})

    def post(body):
        req = _Req("/api/hold/trades", body)
        server.Handler.do_POST(req)
        return req.out[-1][1]
    return post


def test_a_mark_carries_her_thesis_and_roles_and_old_marks_still_work(door):
    old = door({"op": "mark", "idx": "NIFTY", "k": 22800, "side": "CE", "role": "long", "t0": "10:00:00", "p0": 120})
    assert old["ok"] and "roles" not in old["trades"][0], "a mark without the new fields is exactly what it was"
    new = door({"op": "mark", "idx": "NIFTY", "k": 22850, "side": "CE", "role": "long", "t0": "10:05:00", "p0": 100,
                "thesis": {"why": "buyer initiation at -2σ, PE writers covering", "t2": 22900}, "roles": {"CORE": 1, "BANKER": 1}})
    tr = new["trades"][-1]
    assert new["ok"] and tr["thesis"]["why"].startswith("buyer") and tr["thesis"]["src"] == {"t2": "her"}
    assert [r["role"] for r in tr["roles"]] == ["CORE", "BANKER"]
    bad = door({"op": "mark", "idx": "NIFTY", "k": 22900, "side": "CE", "role": "long", "t0": "10:06:00", "p0": 90, "thesis": {"why": "x" * 121}})
    assert not bad["ok"] and "120" in bad["why"]
    out = door({"op": "role_exit", "id": tr["id"], "role_id": "BANKER", "lots": 3})
    assert not out["ok"] and "holds 1 lot" in out["why"], "over-lot is refused at the door too"


def test_a_flip_inside_60_s_and_a_mark_inside_the_cooldown_are_tagged_not_refused(door, monkeypatch):
    a = door({"op": "mark", "idx": "NIFTY", "k": 22800, "side": "CE", "role": "long", "t0": "10:00:00", "p0": 120})["trades"][0]
    door({"op": "role_exit", "id": a["id"], "role_id": "CORE", "exit_reason": "STOPPED"})
    flip = door({"op": "mark", "idx": "NIFTY", "k": 22800, "side": "PE", "role": "long", "t0": "10:20:00", "p0": 110})
    assert flip["ok"] and set(flip["trades"][-1]["tags"]) == {"FLIP", "COOLDOWN"}
    cd, fl = trade_record.cooldown(flip["trades"], "NIFTY", flip["trades"][0]["exit_at"] + 30)
    assert cd["left_s"] == 570 and "STOPPED" in cd["why"] and fl["left_s"] == 30


def test_the_flat_read_carries_the_cooldown_timer():
    tr = dict(TR, exit_t="10:20:00", exit_at=1000.0, roles=[{"id": "CORE", "role": "CORE", "lots": 1, "exit_t": "10:20:00", "exit_reason": "RED"}])
    v = validate_live.read(None, None, DAY, 1100 * 1000, trades=[tr])
    assert v["word"] is None and v["cooldown"]["left_s"] == 500 and v["flip"] is None and v["flip_why"]


# ---- the minute log and the route ---------------------------------------------------------------------------------------
def test_the_minute_log_carries_the_lamps_reversal_prompt_shadow_and_acks_in_session_only(monkeypatch):
    monkeypatch.setattr(server, "_HOLD", {"facts": {}, "locks": {}, "trades": [], "trades_day": None, "sigma": {}, "peaks": {}})
    for now_day, now_hm in (("2026-09-13", "11:00"), (DAY, "16:10")):
        _post_marked(monkeypatch, now_day, now_hm)
        assert not os.path.exists(decoder_log.minute_path(DAY))
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "10:21"))
    server._HOLD["trades"], server._HOLD["trades_day"] = [dict(TR, acks=[{"t": "10:20:30", "lamp": "oi", "from": "G", "to": "R"}])], DAY
    _post_marked(monkeypatch, DAY, "10:21")
    row = [json.loads(l) for l in open(decoder_log.minute_path(DAY), encoding="utf-8")][-1]
    v = row["validate"]
    assert set(v["lamps"]) == {"zone", "flow", "oi", "vpin"} and isinstance(v["reversal_met"], int)
    assert set(v["shadow"]) == {"word", "amber_no_exit", "cut_2of4"} and v["acks"][0]["lamp"] == "oi" and "prompt" in v
    req = _Req("/api/validate?idx=NIFTY", {})
    server.Handler.do_GET(req)
    got = req.out[-1][1]
    assert got["in_trade"] and got["word"] == "HOLD" and got["reversal"]["of"] == 4
    assert server._SENSES["frame"]["NIFTY"]["story"]["trade_read"]["validate"]["trade_id"] == TR["id"], "mirrored into the story"


def test_every_why_is_non_null_exactly_when_its_field_is_null():
    from test_frame import _why_pairs
    reads = [_fx("10:35:10"), _fx("11:10:40"), _read(), _read(closed=[]), validate_live.read(None, None, DAY, M("10:30")),
             _read(fold=_view(G=None, A=None))]
    bad = [(k, v, w) for r in reads for _, k, v, w in _why_pairs(r) if (v is None) == (w is None)]
    assert not bad, bad


def test_the_slips_engine_label_survives_the_thesis_lock():
    import trade_record
    th, why = trade_record.thesis_from({"thesis": {"t1": 22800, "inval": 22700, "src": {"t1": "engine"}}}, "10:10:00")
    assert why is None and th["src"] == {"t1": "engine", "inval": "her"}
