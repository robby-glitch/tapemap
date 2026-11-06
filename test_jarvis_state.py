"""test_jarvis_state.py -- the market state wired into Jarvis (plan docs/superpowers/plans/2026-11-06-jarvis-market-state.md):
jarvis.py, jarvis_log.py and server.py. Toy frames, plus record checks skipped when the day is absent. Kept apart from
test_jarvis.py so its own edits never mix with these."""
import json

import pytest

import jarvis
from test_jarvis import _call_toy, _has, _toy, record  # noqa: F401  (record is a fixture)


def test_her_zone_trigger_no_longer_votes_in_the_count():
    """Spec 2026-11-06 §2: zone triggers never vote in the trend count again (5 Nov: the 12:30 NIFTY sell voted against
    a trend the writers backed). The trigger is the zone card's."""
    d = _toy()
    d["zone"] = [{"t": "10:30", "side": "SELL", "px": 23010.0}]
    d["reads"] = jarvis.reads(d)
    d["legs"] = {"rows": [{"t": m, "lean": -1, "word": "TREND", "leg": {"dir": -1}} for m in d["mins"]],
                 "day": {"flips": [0] * 40, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    c = jarvis.count(d, 39)
    assert "setup" not in jarvis.PIECES and [p["k"] for p in c["pieces"]] == list(jarvis.PIECES)
    assert not any("trigger" in p["text"] for p in c["pieces"]) and c["N"] == c["with"] + c["against"]


def _state_rows(d, word="TREND ▼", D=-1):
    return [{"t": m, "word": word, "dir": D, "conf": True, "since": "10:12",
             "why": "TREND ▼: LL 22,990 (10:06) then LH 23,040 (10:09) held", "line": "line 23,040 (LH 10:09)",
             "eff": 0.61, "vx": 0, "price": "fut", "expiry": None,
             "vol": {"word": "EXPANDING", "since": "10:20", "up": 2, "down": 0, "read": 4, "gauges": []}}
            for m in d["mins"]]


def test_the_state_word_leads_and_the_action_word_becomes_a_chip():
    d = _call_toy()
    d["reads"]["action"] = jarvis.action_words(d)
    old = jarvis.call(d)                                          # a frame with no state: the ACTION word, as before
    assert old["word"] == old["action"]["said"] and old["mstate"] is None and old["chips"] == []
    d["mstate"] = _state_rows(d)
    c = jarvis.call(d)
    assert c["word"] == "TREND ▼" and c["since"] == "10:12" and c["action"]["said"] == old["word"]
    assert c["chips"][0] == old["word"] and c["mstate"]["vol"]["word"] == "EXPANDING"
    assert c["mstate"]["chip"] == "neeche ka trend · 23,040" and c["mstate"]["grade"] in ("healthy", "tired", "fuel blind")
    assert c["why"][0].startswith("state: TREND ▼ · EXPANDING since 10:12 — TREND ▼: LL")
    assert c["buyer"] == old["buyer"] and c["wrong_line"] == old["wrong_line"]   # the expressions follow the ACTION word
    rows = jarvis.calls(d)
    assert rows[-1]["word"] == "TREND ▼" and rows[-1]["action"]["said"] == old["word"]
    assert "%" not in json.dumps(c, default=str)


def test_the_grade_reads_the_count_for_the_trend_and_never_flips_it():
    assert jarvis._grade({"with": 3, "against": 1}, 1, 1) == "healthy"
    assert jarvis._grade({"with": 3, "against": 1}, 1, -1) == "tired"        # the count is for the other lean: mirrored
    assert jarvis._grade({"with": 0, "against": 0}, -1, -1) == "fuel blind"  # HOLD with nothing voting is not allowed
    assert jarvis._grade({"with": 2, "against": 0}, 0, 1) is None           # no trend: no grade


@pytest.mark.skipif(not _has("2026-11-05"), reason="5 Nov record not present")
def test_5nov_every_minute_has_a_state_and_the_open_drive_is_spoken(record):
    """Spec §9 row 1, observed on the record: SENSEX's leg qualified at 09:43, so the word reads TREND ▲ (unconfirmed)
    before 10:00 instead of a silent OPENING."""
    d = jarvis.build("2026-11-05", "SENSEX", None)
    assert len(d["mstate"]) == len(d["mins"]) and not any("market state failed" in x for x in d["health"]["notes"])
    assert any(r["word"].startswith("TREND ▲") for r in d["mstate"] if "09:36" <= r["t"] <= "10:00")


def test_grade_keeps_blind_and_flat_apart():
    """Rule 6: nothing voted because the pieces could not be checked (blind) vs checked and took no side (flat)."""
    assert jarvis._grade({"with": 0, "against": 0, "flat": 0, "blind": 3}, -1, -1) == "fuel blind"
    assert jarvis._grade({"with": 0, "against": 0, "flat": 2, "blind": 1}, -1, -1) == "fuel flat"
    assert jarvis._grade({"with": 1, "against": 1, "flat": 2, "blind": 0}, -1, -1) == "healthy"


import jarvis_log  # noqa: E402

DAY = "2026-11-02"


def _srow(t, word="TREND ▲"):
    return {"t": t, "word": word, "dir": 1, "conf": True, "since": "10:40", "why": "TREND ▲: HH then HL held",
            "line": "line 23,000 (HL 10:30)", "eff": 0.5, "vx": 1, "price": "fut", "expiry": None,
            "vol": {"word": "NORMAL", "since": "10:30", "up": 1, "down": 0, "read": 4,
                    "gauges": [{"k": "vix", "vote": 0, "text": "VIX +0.10"}]}}


def test_the_call_row_carries_the_action_and_the_self_line_counts_palatq_from_it():
    fr = {"day": DAY, "idx": "NIFTY", "mins": ["10:42"], "fut": [1.0], "spot": [1.0],
          "call": {"at": "10:42", "word": "TREND ▲", "action": {"said": "PALAT? ▲"}, "mstate": {"vol": {"word": "EXPANDING"}}}}
    r = jarvis_log.row(fr, 1793596371)
    assert r["word"] == "TREND ▲" and r["action"] == "PALAT? ▲" and r["vol"] == "EXPANDING"
    rows = [dict(r, t="10:40", action="HOLD ▲"), dict(r, t="10:41", action="PALAT? ▲"), dict(r, t="10:42", action="PALAT ▼")]
    s = jarvis_log.self_line(rows, 1.0)
    assert s.startswith("TREND ▲ since 10:40") and "PALAT? said 1× · came true 1×" in s


def test_the_state_log_is_write_once_and_tags_a_late_minute_backfill():
    fr = {"ok": True, "day": DAY, "idx": "NIFTY", "mins": ["10:40", "10:41"], "call": {},
          "mstate": [_srow("10:40"), _srow("10:41")]}
    for j in (0, 1):
        assert jarvis_log.write(DAY, "NIFTY", jarvis_log.state_row(fr, j, 1793596371, "live" if j else "backfill"),
                                kind="state") is True
    assert jarvis_log.write(DAY, "NIFTY", jarvis_log.state_row(fr, 1, 1793596400, "live"), kind="state") is False
    rows = jarvis_log.read(DAY, "NIFTY", kind="state")
    assert [(x["t"], x["src"]) for x in rows] == [("10:40", "backfill"), ("10:41", "live")]
    assert rows[0]["votes"] == {"vix": 0} and rows[0]["vol"] == "NORMAL" and jarvis_log.read(DAY, "NIFTY") == []


def test_the_server_writes_every_minute_of_a_late_start_once(monkeypatch):
    """Anytime-start: a first live build at 10:42 writes 10:40 as backfill and 10:41 live; the next minute adds one row."""
    import time
    from datetime import datetime
    from chain_live import IST
    from test_jarvis_log import CALL, _srv, frame
    server, clock = _srv(monkeypatch, (2026, 11, 2, 10, 42, 25))

    def fake(day, idx, upto, fill=False):
        ms = [f"{m // 60:02d}:{m % 60:02d}" for m in range(640, upto)]
        return dict(frame(), day=day, idx=idx, mins=ms, call=dict(CALL, at=ms[-1]), mstate=[_srow(m) for m in ms])
    monkeypatch.setattr(jarvis, "build", fake)
    server._jarvis_reply({"idx": ["NIFTY"]})
    assert [(r["t"], r["src"]) for r in jarvis_log.read(DAY, "NIFTY", kind="state")] == [("10:40", "backfill"),
                                                                                         ("10:41", "live")]
    clock["now"] = datetime(2026, 11, 2, 10, 43, 25, tzinfo=IST)
    monkeypatch.setattr(server, "JARVIS_TTL_S", 0)
    server._jarvis_reply({"idx": ["NIFTY"]})
    assert [(r["t"], r["src"]) for r in jarvis_log.read(DAY, "NIFTY", kind="state")][-1] == ("10:42", "live")
    assert len(jarvis_log.read(DAY, "NIFTY", kind="state")) == 3 and time.time()


def test_the_card_passes_the_state_the_action_and_the_chips():
    fr = {"ok": True, "day": DAY, "idx": "NIFTY", "mins": ["10:41"], "fut": [1.0], "health": {"notes": []},
          "call": {"word": "TREND ▲", "mstate": {"word": "TREND ▲", "chip": "upar ka trend · 23,000"},
                   "action": {"said": "WATCH ▲"}, "chips": ["WATCH ▲", "fuel tired"]}}
    c = jarvis_log.card(fr)
    assert c["mstate"]["chip"] == "upar ka trend · 23,000" and c["action"]["said"] == "WATCH ▲"
    assert c["chips"] == ["WATCH ▲", "fuel tired"]


def test_a_late_first_build_writes_every_minute_backfill(monkeypatch):
    """F1: the newest minute is live only within jarvis.BLIND_MIN of its end; a 16:30 start writing 15:39 is backfill."""
    from test_jarvis_log import CALL, _srv, frame
    server, _ = _srv(monkeypatch, (2026, 11, 2, 16, 30, 0))
    ms = ["15:38", "15:39"]
    monkeypatch.setattr(jarvis, "build", lambda day, idx, upto, fill=False: dict(
        frame(), day=day, idx=idx, mins=ms, call=dict(CALL, at=ms[-1]), mstate=[_srow(m) for m in ms]))
    server._jarvis_reply({"idx": ["NIFTY"]})
    assert [r["src"] for r in jarvis_log.read(DAY, "NIFTY", kind="state")] == ["backfill", "backfill"]


@pytest.mark.skipif(not _has("2026-11-05"), reason="5 Nov record not present")
def test_5nov_zone_rows_carry_when_they_were_written_and_never_a_score(record):
    d = jarvis.build("2026-11-05", "SENSEX", None)
    z = [x for x in d["zone"] if not x.get("kind")]
    assert z and all({"at", "gate", "effort"} <= set(x) for x in z)
    assert not any(k in x for x in d["zone"] for k in ("mfe", "mae", "stop_hit", "f15", "f30", "scored_at"))
    assert len(d["nf"]) == len(d["mins"]) and d["nf"][-1] is not None


def test_the_zone_card_shows_from_when_it_was_known_for_45_minutes(monkeypatch):
    monkeypatch.setattr(jarvis, "MANAGE_WIN", 5)
    d = _call_toy()
    d["reads"]["action"] = jarvis.action_words(d)
    d["mstate"] = _state_rows(d)
    card = {"t": "10:05", "close": "10:07", "known": "10:09", "late": False, "side": "BUY", "band": "d2", "px": 23010.0,
            "level": None, "state": "TREND ▼", "vol": "EXPANDING", "kind": None, "verdict": "SKIP",
            "why": "TREND ▼ + EXPANDING: no bottom fades", "signs": [{"k": "wall", "ok": None, "text": "wall: could not check"}], "n": 0, "N": 0, "stop": 23000.0, "stop_why": None,
            "targets": [["VWAP", 23080.0], ["u1", 23100.0]], "gate": {"legal": True, "why": "PE 22900 still building"}}
    d["zone_cards"] = [card]
    assert jarvis.call(jarvis.cut_at(d, 8))["zone"] is None                      # 10:08: not known yet
    c = jarvis.call(jarvis.cut_at(d, 9))
    assert c["zone"]["verdict"] == "SKIP" and c["zone"]["line"].startswith("ZONE d2 · close 23,010f · SKIP · stop 23,000f")
    assert any(x.startswith("zone: ZONE d2") for x in c["why"])
    assert jarvis_log.card(dict(ok=True, day=DAY, idx="NIFTY", mins=["10:09"], fut=[1.0], health={"notes": []},
                                call=c))["zone"]["verdict"] == "SKIP"
    W = jarvis.MANAGE_WIN                                                        # known 10:09 (idx 9): shown through idx 9+W-1
    assert jarvis.call(jarvis.cut_at(d, 9 + W - 1))["zone"] is not None          # just before the boundary
    assert all(jarvis.call(jarvis.cut_at(d, k))["zone"] is None for k in (9 + W, 9 + W + 1, len(d["mins"]) - 1))
    fr = dict(d, zone_cards=[card, dict(card, known="10:30")])
    assert [z["band"] for z in jarvis_log.state_row(fr, 9, 0, "live")["zone"]] == ["d2"]


@pytest.mark.skipif(not _has("2026-11-05"), reason="5 Nov record not present")
def test_5nov_sensex_zone_card_is_causal_the_cut_full_build_equals_the_11_00_build(record):
    full = jarvis.build("2026-11-05", "SENSEX", None)
    i = full["mins"].index("11:00")
    part = jarvis.build("2026-11-05", "SENSEX", jarvis._m("11:00") + 1)
    assert part["mins"][-1] == "11:00"
    cut = jarvis.cut_at(full, i)
    assert jarvis.call(cut)["zone"] == jarvis.call(part)["zone"]
    assert jarvis_log.state_row(full, i, 0, "live")["zone"] == jarvis_log.state_row(part, i, 0, "live")["zone"]
    for fr in (full, part):
        assert all(c["known"] >= c["close"] for c in fr["zone_cards"] if c.get("close"))
        for k in range(len(fr["mins"])):
            z = jarvis.call(jarvis.cut_at(fr, k))["zone"]
            assert z is None or z["known"] <= fr["mins"][k]
            assert all(r["t"] <= fr["mins"][k] for r in jarvis_log.state_row(fr, k, 0, "live")["zone"])


def test_the_open_trade_rides_on_the_zone_card_and_never_shows_a_later_minute():
    d = _call_toy()
    d["reads"]["action"] = jarvis.action_words(d)
    d["mstate"] = _state_rows(d)
    tr = [{"t": "10:09", "open": True, "chips": ["WIDEN · stop → beyond d3 22,950f", "risk to d3: 60 pts"],
           "why": ["WIDEN 10:09: writers tike: 22,900s PE +1.0L / 9 min"], "risk": 60.0},
          {"t": "10:12", "open": False, "chips": ["d3 ke paar 3-min close 22,940f — trade band"], "why": [], "risk": 60.0}]
    card = {"t": "10:05", "close": "10:07", "known": "10:09", "late": False, "side": "BUY", "band": "d2", "px": 23010.0,
            "level": None, "state": "TREND ▼", "vol": "EXPANDING", "kind": "fade", "verdict": "TAKE · smaller target",
            "why": "TREND ▼ + EXPANDING: a fade only if the band stopped", "signs": [], "n": 2, "N": 4, "stop": 23000.0,
            "stop_why": None, "targets": [["VWAP", 23080.0]], "gate": None, "u3": None, "d3": 22950.0, "u3_why": None,
            "trade": tr, "in_trade": None}
    d["zone_cards"] = [card]
    c = jarvis.call(jarvis.cut_at(d, 10))                                        # 10:10
    assert "trade" not in c["zone"] and c["zone"]["open"]["of"] == "10:05" and c["zone"]["open"]["t"] == "10:09"
    assert c["zone"]["open"]["chips"][0] == "WIDEN · stop → beyond d3 22,950f"
    assert any("open 10:05: WIDEN · stop → beyond d3 22,950f" in x for x in c["why"])
    e = jarvis.call(jarvis.cut_at(d, 12))["zone"]["open"]                        # 10:12: the hard line
    assert e["open"] is False and e["chips"] == ["d3 ke paar 3-min close 22,940f — trade band"]
    assert "%" not in json.dumps(c["zone"])
