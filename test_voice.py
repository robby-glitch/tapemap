"""THE ONE VOICE (voice.py, NOTEPAD A52): the ladder's order, the first trigger, EXIT's source, TIGHTEN's 60 s, seq, and
the shadow lines kept off the open trade but on its receipt."""
import copy

import fold
import voice

DAY = "2026-10-21"
T = lambda hms: fold.ms(DAY, hms)                                     # noqa: E731
TR = {"idx": "NIFTY", "k": 23000, "ty": "PE", "side": "BUY", "p0": 174.85, "entry_t": "10:07:30"}


def rep(now="10:30:00", headline="HOLD", clause="behind you: flow, OI", chips=None, words=(), **kw):
    v = {"headline": headline, "clause": clause, "t": T(now), "ts": now, "d": -1, "E": 23003.0, "fut": 22990.0,
         "G": {"px": 23052}, "units": {"basis_ix": 30.0}, "prem": {"now": 190.0, "at_G": 150.0},
         "chips": chips or {"Z": "QUIET", "F": "WITH", "O": "WITH", "V": "QUIET"},
         "chip_since": {"Z": "10:07:39", "F": "10:10:00", "O": "10:12:00", "V": "10:07:39"},
         "W": {"k": 23100, "side": "CE", "oi": 9.0e6, "peak": 10.0e6, "upd": 3, "off": 0.0, "bleed_t": None}}
    v.update(kw)
    return {"ok": True, "id": "x", "trade": TR, "view": v, "words": list(words)}


def h2(**kw):
    b = {"ok": True, "E": 23003.0, "line0": 23052.0, "line_fut": 23040.0, "line_spot": 23010.0, "moves": [], "lock_t": None,
         "v2_exit": {"how": "open", "t": None, "px": None}}
    b.update(kw)
    return b


def run(r, h, now="10:30:00", mem=None):
    return voice.ladder(r, h, T(now), {} if mem is None else mem, lambda px: (round(px / 150, 1), "[I]"))


def test_hold_reads_the_two_strongest_with_facts_oi_first():
    v = run(rep(), h2())
    assert v["state"] == "HOLD" and v["l3"] == "why: CE 23100 writers building · flow saath"
    assert v["l1"] == "▼ 23000 PE · 22 min · +13 pts (₹+15)"                 # futures points: d × (fut − E)
    assert v["r_now"] == 0.27 and v["pts"] == 13                            # R stays in the fields (and the map's detail)
    assert v["l2"] == "stop 23,040f / 23,010s ≈ ₹154 · BE lock at 22,905f" and v["stop_src"] == "HOLD v2"   # E − 2R


def test_the_ladder_shows_the_highest_state():
    W = {"k": 23100, "side": "CE", "oi": 8.8e6, "peak": 10.0e6, "upd": 20, "off": 0.12, "bleed_t": "10:20:00"}
    v = run(rep(W=W), h2())                                               # price WITH her: munafa booking, a gauge (A61)
    assert v["state"] == "HOLD" and v["gauge"].startswith("W-BLEED 23100 CE −12.0% off 100.0L peak · 20 upd")
    assert run(rep(W=W, fut=23010.0), h2())["state"] == "WARN"            # price against her + the wall off: GAVE UP
    v = run(rep(W=W, fut=23010.0, headline="FOLD · 23052 accepted · 10:29", words=[{"t": "10:29:00", "headline": "FOLD · 23052 accepted · 10:29"}]), h2())
    assert v["state"] == "EXIT" and v["reason"] == "FOLD — 23,052 accepted (fold engine)"
    assert [a["state"] for a in v["active"]] == ["EXIT", "WARN"]          # both run; the cautious one shows


def test_warn_names_the_first_trigger_with_its_number():
    zone, since = {"Z": "WITH", "F": "QUIET", "O": "QUIET", "V": "QUIET"}, {"Z": "10:25:00", "F": "10:24:00", "O": "10:26:00"}
    words = [{"t": "10:20:00", "headline": "PAST GIVE-UP · 23,052 crossed"}]
    v = run(rep(headline=words[0]["headline"], clause="23,052 crossed · fut 23,060", words=words, chips=zone, chip_since=since), h2())
    assert v["state"] == "WARN" and v["reason"].startswith("PAST GIVE-UP — 23,052 crossed · fut 23,060") and v["trig_t"] == "10:20"
    v = run(rep(chips=zone, chip_since=since), h2())
    assert v["reason"].startswith("ZONE ALONE — OI quiet · flow quiet") and v["trig_t"] == "10:26"


def test_exit_names_its_source_and_the_earlier_rule_wins():
    words = [{"t": "10:29:00", "headline": "FOLD · 23052 accepted · 10:29"}]
    v = run(rep(headline=words[0]["headline"], words=words), h2(how="line_init", touched_t="10:27"))
    assert v["reason"] == "stop hit 23,040f (HOLD v2)" and v["src"] == "HOLD v2" and v["trig_t"] == "10:27"
    v = run(rep(headline=words[0]["headline"], words=words), h2(how="line_push", touched_t="10:33"))
    assert v["reason"] == "FOLD — 23,052 accepted (fold engine)" and v["src"] == "fold engine"
    v = run(rep(), h2(how="mark"))
    assert v["state"] == "EXIT" and v["reason"] == "15:20 — spot 15:15 se frozen (HOLD v2)" and v["trig_t"] == "15:20"   # the CAS freeze


def test_v2_gave_up_warns_never_exits_and_a_later_trail_or_lock_answers_it():
    gu = dict(gave_up_t="10:28", v2_exit={"how": "gave_up", "t": "10:28", "px": 23020.0})
    v = run(rep(), h2(**gu))
    assert v["state"] == "WARN" and v["reason"] == "CE front gave up @ 23,020f · line 23,040f (HOLD v2)"
    mv = [{"t": "10:25", "at": "10:30", "from": 23040.0, "to": 23021.0}]
    assert run(rep(), h2(moves=mv, **gu))["state"] == "HOLD"                # the line trailed her way after it
    assert run(rep(), h2(lock_t="10:29", **gu))["state"] == "HOLD"          # or the lock engaged after it
    assert run(rep(), h2(moves=[dict(mv[0], at="10:20")], **gu))["state"] == "WARN"   # a move before it answers nothing
    assert run(rep(), h2(how="line_push", touched_t="10:40", **gu))["state"] == "EXIT"   # the line itself is still the stop


def test_tighten_is_an_event_for_60_s_and_the_first_look_is_the_baseline():
    mem = {}
    assert run(rep(), h2(), "10:30:00", mem)["state"] == "HOLD"              # her first look: never an event
    mv = [{"t": "10:30", "at": "10:31", "from": 23040.0, "to": 23021.0}]
    v = run(rep(now="10:31:05"), h2(moves=mv, line_fut=23021.0), "10:31:05", mem)
    assert v["state"] == "TIGHTEN" and v["reason"] == "stop 23,040→23,021f (HOLD v2 trail)"
    assert run(rep(now="10:31:50"), h2(moves=mv, line_fut=23021.0), "10:31:50", mem)["state"] == "TIGHTEN"
    assert run(rep(now="10:32:06"), h2(moves=mv, line_fut=23021.0), "10:32:06", mem)["state"] == "HOLD"
    v = run(rep(now="10:40:00"), h2(moves=mv, lock_t="10:40"), "10:40:00", mem)
    assert v["state"] == "TIGHTEN" and v["reason"] == "BE lock ✓ 23,003f (HOLD v2)" and "BE lock ✓ 10:40" in v["l2"]
    assert run(rep(), h2(moves=mv * 2), "10:30:00", {})["state"] == "HOLD"   # a restart: what it finds is the baseline


def test_seq_moves_only_on_a_state_change():
    mem, W = {}, {"k": 23100, "side": "CE", "oi": 8.8e6, "peak": 10.0e6, "upd": 20, "off": 0.12, "bleed_t": "10:20:00"}
    a = 23010.0                                                           # price against her: GAVE UP is the WARN
    seqs = [run(r, h2(), "10:30:00", mem)["seq"] for r in (rep(), rep(), rep(W=W, fut=a), rep(W=W, fut=a), rep(W=dict(W, upd=21), fut=a), rep())]
    assert seqs == [1, 1, 2, 2, 2, 3]


def test_gave_up_needs_price_against_her_and_the_wall_off():
    W = {"k": 23100, "side": "CE", "oi": 8.8e6, "peak": 10.0e6, "upd": 20, "off": 0.12, "bleed_t": "10:20:00"}
    v = run(rep(W=W, fut=23010.0), h2())
    assert [a["key"] for a in v["active"]] == ["GAVEUP"]                   # W-BLEED alone is never a WARN (A61)
    assert v["reason"] == "GAVE UP — 23100 CE writers −12.0% off its 100.0L peak · fut -7 vs entry"
    v = run(rep(W=W), h2())                                                # price with her: munafa booking, no WARN
    assert v["active"] == [] and v["state"] == "HOLD" and v["gauge"].endswith("· gauge, not a give-up alone")


def test_not_read_yet_says_why_and_receipt_names_the_shadow_lines():
    assert run({"ok": False, "why": "could not check — catching up"}, None)["why"] == "could not check — catching up"
    rows = [{"id": "x", "line": "POP", "how": "pop", "sh": {"t": "13:05", "R": 0.6}},
            {"id": "x", "line": "EFFORT", "how": "v2", "sh": {"t": "13:25"}}, {"id": "x", "line": "CHOP", "how": "open", "sh": {}}]
    r = voice.receipt({"id": "x", "exit_t": "13:25:04"}, 76.2, rows)
    assert r["text"] == "you exited 13:25 @ ₹76 · POP would say 13:05 (+0.6R) · EFFORT — · CHOP —"
    assert "could not check" in voice.receipt({"id": "y", "exit_t": "13:25"}, None, rows)["why"]


def test_the_server_keeps_shadows_off_the_open_trade_and_puts_them_on_the_receipt(monkeypatch, tmp_path):
    import json
    import server
    tr = {"id": "x", "idx": "NIFTY", "t0": "10:07:30", "k": 23000, "side": "PE", "role": "long", "p0": 174.85}
    sh = [{"line": "POP", "text": "POP · …", "how": "open"}]
    monkeypatch.setattr(server, "_hold2", lambda rep, trades: None if trades[0].get("exit_t") else dict(h2(), shadow=sh, shadow_why=None))
    monkeypatch.setattr(server, "_VOICE", {})
    r = rep()
    keep = copy.deepcopy(r)
    out = server._in_trade(r, [tr])
    assert r == keep and "shadow" not in out["hold2"] and "shadow_why" not in out["hold2"]
    assert out["voice"]["ok"] and out["voice"]["state"] == "HOLD" and "receipt" not in out
    monkeypatch.setattr(server, "SHADOW_DIR", str(tmp_path))
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "13:30"))
    (tmp_path / f"shadow_{DAY}.jsonl").write_text(json.dumps({"id": "x", "line": "POP", "how": "pop", "sh": {"t": "13:05", "R": 0.6}}) + "\n")
    out = server._in_trade(rep(prem={"now": 76.0}), [dict(tr, exit_t="13:25:04")])
    assert "voice" not in out and out["receipt"]["text"] == "you exited 13:25 @ ₹76 · POP would say 13:05 (+0.6R) · EFFORT ? · CHOP ?"


def test_the_engine_hands_the_wall_bleed_and_the_chip_times():
    import fold_live

    class W_:
        key, pk, pk_i, j = (23100, "ce"), 100.0, 2, 24
    st = type("S", (), {})()
    st.Ww, st.since = W_(), {"ZONE": T("10:07:39"), "FLOW": None, "OI": T("10:12:00"), "VPIN": None}
    oi = [90, 95, 100] + [99] * 10 + [92, 89, 91, 89, 88, 88, 89, 88, 87, 86, 85, 84]     # 25 updates; off >= 10 % from i=15
    st.oiu = {W_.key: [(T("10:00:00") + 60000 * i, x) for i, x in enumerate(oi)]}
    v = {"W": {"k": 23100, "side": "CE", "oi": 84, "peak": 100.0}}
    fold_live._voice_facts(st, v)
    assert v["chip_since"] == {"Z": "10:07:39", "F": None, "O": "10:12:00", "V": None}
    assert v["W"]["upd"] == 22 and v["W"]["off"] == 0.16 and v["W"]["bleed_t"] == "10:17:00"   # i=17: 2+15, the run's start
    assert voice.bleed(v["W"])
