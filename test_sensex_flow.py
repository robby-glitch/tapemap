"""SENSEX-NIFTY-FLOW (docs/hold/SENSEX-NIFTY-FLOW-PREREG.md, a DRAFT): NIFTY's pushes as SENSEX lines (§1.2), NIFTY's flat
FLOW chip in her direction on a copy of the reply (§1.3), the stamps, and the flags OFF leaving every path today's."""
import copy
import os

import pytest

import hold2
import sensex_flow as sf
import voice

S13 = 13 * 3600


def push(s, d, o=22500.0, c=22480.0, U=20.0):
    return {"s": s, "t": hold2.hm(s // 60), "close": s // 60 + 5, "d": d, "origin": o, "c": c, "U": U, "size": 3.0, "R": 0.5,
            "src": "gc"}


def bar(s, o, c, vol=100):
    return {"s": s, "e": s + 300, "o": o, "h": max(o, c) + 5, "l": min(o, c) - 5, "c": c, "vol": vol, "delta": -50, "src": "ux"}


def _ms(m):
    return (m * 60 - 19800) * 1000 + 86400000 * 20000         # any day: IST minute m


def test_signed_on_from_the_signing_day_for_sensex_only():
    assert sf.ON is True and sf.FROM == "2026-10-25" and sf.SHA8 == "9e2831b5" and sf.on("SENSEX") and not sf.on("NIFTY")


def test_a_nifty_push_takes_the_sensex_bar_of_its_slot_its_sigma_and_a_slot_without_one_is_skipped():
    sx = [bar(S13 - 300, 73500.0, 73480.0), bar(S13, 73470.0, 73400.0)]
    P, skip = sf.translate([push(S13, -1), push(S13 + 300, -1)], sx)
    assert len(P) == 1 and P[0]["origin"] == 73470.0 and P[0]["c"] == 73400.0 and P[0]["src"] == "NIFTY"
    assert P[0]["U"] == max(hold2.sigmas(sx)[1], 0.001 * 73470.0) and P[0]["t"] == "13:00" and P[0]["close"] == 785
    assert P[0]["n_origin"] == 22500.0 and P[0]["n_src"] == "gc" and P[0]["d"] == -1
    assert [x["t"] for x in skip] == ["13:05"]
    P0, _ = sf.translate([push(S13, -1)], [bar(S13, 73470.0, 73400.0, vol=0)])      # no volume: sigma 0, the 0.1 % floor
    assert P0[0]["U"] == pytest.approx(73.47)
    assert sf.line(None, "no NIFTY reference day before 2026-10-22", sx) == (
        None, "push ? — could not check: NIFTY flow not read (no NIFTY reference day before 2026-10-22)", [])


def test_the_sensex_line_moves_on_the_translated_push_through_hold2_live_and_the_default_is_unchanged():
    view = {"headline": "HOLD", "d": -1, "E": 73450.0, "fut": 73420.0, "units": {"basis_ix": 100.0}}
    tr = {"id": "x", "idx": "SENSEX", "t0": "12:55:30", "thesis": {"inval": 73600.0}}
    bars1 = [{"t": _ms(m), "o": 73420, "h": 73430, "l": 73410, "c": 73420} for m in range(775, 791)]
    sx = [bar(S13 - 300, 73500.0, 73480.0), bar(S13, 73470.0, 73400.0)]
    P, why, skip = sf.line([push(S13, -1)], None, sx)
    w = hold2.live(tr, view, 790, bars1, [], sx, None, why, {}, pushes_=P)
    assert w["line_fut"] == round(73470.0 + 0.25 * P[0]["U"], 2) and w["moves"][0]["src"] == "NIFTY"
    keep = hold2.live(tr, view, 790, bars1, [], sx, {}, "push ? ref nahi — SENSEX", {})
    assert keep == hold2.live(tr, view, 790, bars1, [], sx, {}, "push ? ref nahi — SENSEX", {}, pushes_=None)
    assert keep["line_fut"] == 73600.0 and keep["text"].endswith("push ? ref nahi — SENSEX")   # today's: the trail inactive
    sf.stamp(w, [push(S13 + 300, -1), push(S13 + 600, 1), push(S13 - 1200, -1)], tr["t0"], 800)
    assert "(NIFTY PUSH ▼ 13:00)" in w["text"] and w["why"].startswith("NIFTY PUSH ▼ 13:00 origin 73,470f")
    assert w["text"].endswith(" · NIFTY push 13:05 · SENSEX bar ?") and w["push_src"] == "NIFTY"   # her way, after entry only


def flat(chip, asof="13:01:00", ok=True):
    return {"ok": ok, "asof": asof, "why": None if ok else "could not check — the engine is catching up",
            "rows": {"flow": {"chip": chip, "sentence": "sellers won 12:55 at 22,742"}}}


def test_niftys_flat_flow_chip_in_her_direction():
    c = sf.flow_chip
    assert [c(1, flat(x))[0] for x in ("BUYERS", "SELLERS", "QUIET", "CAN'T CHECK")] == ["WITH", "AGAINST", "QUIET", "CAN'T CHECK"]
    assert [c(-1, flat(x))[0] for x in ("BUYERS", "SELLERS")] == ["AGAINST", "WITH"]
    assert c(1, flat("SELLERS"), "13:01:40")[1] == "NIFTY flow: sellers won 12:55 at 22,742"
    assert c(1, flat("BUYERS", ok=False)) == ("CAN'T CHECK", "could not check — NIFTY flow not read (could not check — the engine is catching up)")
    assert c(1, flat("BUYERS", asof="12:58:30"), "13:01:00") == ("CAN'T CHECK", "could not check — NIFTY flow not read (NIFTY read 12:58:30, trade 13:01:00)")
    assert c(1, {"ok": True, "rows": {}}) == ("CAN'T CHECK", "could not check — NIFTY flow not read (no NIFTY flow row)")
    assert c(1, None)[0] == "CAN'T CHECK"                               # missing is never a zero, never SENSEX's


def rep(ts="13:01:00", chips=None, **kw):
    v = {"headline": "HOLD", "clause": "behind you: zone", "t": _ms(781), "ts": ts, "d": 1, "E": 73520.0, "fut": 73530.0,
         "G": {"px": 73300}, "units": {"basis_ix": 90.0}, "prem": {"now": 195.0},
         "chips": chips or {"Z": "WITH", "F": "WITH", "O": "QUIET", "V": "CAN'T CHECK"},
         "sentences": {"Z": "behind you", "F": "buyers won 12:58 at 73,520", "O": "quiet", "V": "x"},
         "rows": {"flow": {"chip": "WITH", "sentence": "buyers won 12:58 at 73,520"}},
         "chip_since": {"Z": "13:00:10", "F": "13:00:20", "O": "13:00:10", "V": "13:00:10"}}
    v.update(kw)
    return {"ok": True, "id": "SENSEX-73400CE-long-130000", "view": v, "words": [],
            "trade": {"idx": "SENSEX", "k": 73400, "ty": "CE", "side": "BUY", "p0": 191.0, "entry_t": "13:00:00"}}


def test_the_flow_shown_is_niftys_on_a_copy_and_the_voice_reads_it_labelled():
    r, mem = rep(), {}
    keep = copy.deepcopy(r)
    out = sf.flow_view(r, flat("SELLERS"), mem)
    assert r == keep                                                     # the engine's reply is never written
    v = out["view"]
    assert v["chips"]["F"] == "AGAINST" and v["sentences"]["F"] == "NIFTY flow: sellers won 12:55 at 22,742"
    assert v["rows"]["flow"] == {"chip": "AGAINST", "sentence": "NIFTY flow: sellers won 12:55 at 22,742"}
    assert out["flow_src"] == v["flow_src"] == "NIFTY" and v["chip_since"]["F"] == "13:01:00"
    assert {k: v[k] for k in ("headline", "G", "E", "fut")} == {k: keep["view"][k] for k in ("headline", "G", "E", "fut")}
    assert sf.flow_view(rep("13:02:00"), flat("SELLERS", "13:02:00"), mem)["view"]["chip_since"]["F"] == "13:01:00"
    assert sf.flow_view(rep("13:03:00"), flat("QUIET", "13:03:00"), mem)["view"]["chip_since"]["F"] == "13:03:00"
    vc = sf.relabel(voice.ladder(out, None, _ms(781), {}))
    assert vc["state"] == "WARN" and vc["reason"] == "ZONE ALONE — OI quiet · NIFTY flow against"
    assert "NIFTY flow against" in vc["l3"] and all("NIFTY flow" in a["reason"] for a in vc["active"] if a["key"] == "ZONE")
    w = sf.relabel(voice.ladder(sf.flow_view(rep(), flat("BUYERS"), {}), None, _ms(781), {}))
    assert w["l3"] == "why: NIFTY flow saath · zone peeche"
    frozen = rep(frozen=True)
    assert sf.flow_view(frozen, flat("SELLERS"), {}) is frozen          # her exit's view stays as the engine froze it


def test_push_src_stamps_only_when_on_and_from_the_signing_day(monkeypatch):
    assert [sf.push_src("SENSEX", d) for d in ("2026-10-24", "2026-10-25")] == ["SENSEX-ux", "NIFTY"]   # signed 25 Oct
    assert sf.push_src("NIFTY", "2026-10-27") is None
    monkeypatch.setattr(sf, "ON", False)
    assert sf.push_src("SENSEX", "2026-10-27") is None                   # OFF: rev 3 / §1m rows, unstamped


def _poison(monkeypatch):
    monkeypatch.setattr(sf, "ON", False)                                 # OFF must restore rev 3 / §1m exactly
    def boom(*a, **k):
        raise AssertionError("sensex_flow entered with the flag OFF")
    for name in ("translate", "line", "stamp", "flow_chip", "flow_view", "relabel"):
        monkeypatch.setattr(sf, name, boom)


def test_off_the_server_reply_and_the_scorer_never_enter_the_amendment(monkeypatch):
    import server
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import hold2_score
    _poison(monkeypatch)
    monkeypatch.setattr(server, "_hold2", lambda r, trades: None)
    monkeypatch.setattr(server, "_VOICE", {})
    tr = {"id": "SENSEX-73400CE-long-130000", "idx": "SENSEX", "t0": "13:00:00", "k": 73400, "side": "CE", "role": "long", "p0": 191.0}
    r = rep()
    out = server._in_trade(r, [tr])
    assert out["view"] is r["view"] and "flow_src" not in out and out["voice"]["l3"] == "why: flow saath · zone peeche"

    class D:
        def pushes(self, idx, day):
            assert idx == "SENSEX"
            return None, "push ? ref nahi — SENSEX", {}, []

        def ride(self, idx, day):
            return {}
    s = hold2_score.score({"setup": "RIDE", "index": "SENSEX", "day": "2026-10-27"}, D())
    assert "push_src" not in s and s["why"] == "no 1-min futures bar from the ticks"


@pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "book",
                                                    "book_SENSEX_2026-10-22.jsonl")), reason="the 22 Oct record is not here")
def test_off_the_22_oct_replay_never_enters_the_amendment(monkeypatch):
    import book_log
    import decoder_log
    import tape_log
    import voice_path
    for mod, sub in ((book_log, "book"), (tape_log, "tape"), (decoder_log, "decoder")):   # read-only: the real record
        monkeypatch.setattr(mod, "DIR", os.path.join(voice_path.DATA, sub))
    _poison(monkeypatch)
    c = {"day": "2026-10-22", "lot": 20, "end": "13:04:00", "tr": {"id": "SENSEX-73400CE-long-130000", "idx": "SENSEX",
         "k": 73400.0, "side": "CE", "role": "long", "t0": "13:00:00", "p0": None, "exit_t": "13:25:00"}}
    p = voice_path.run(c)
    assert [x["voice"]["state"] for x in p] == ["HOLD"] * len(p) and p and p[0]["t"] == "13:01"   # today's 22 Oct replay
    assert all("NIFTY" not in (x["hold2_text"] or "") and "NIFTY" not in (x["voice"].get("l4") or "") for x in p)
