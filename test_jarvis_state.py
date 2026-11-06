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
