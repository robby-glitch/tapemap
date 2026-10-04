# tapemap/test_story_panel.py
"""The GoCharting panel round (2026-10-04, orderflow-desk docs/PANEL-DESIGN-2026-10-04): the day as chapters, the
decoder's count beside her trade (never the engine's word), the out-of-the-ordinary highlights and their 3-minute
life, the HOLD-vs-DECODER minute log behind the market-hours gate, and anytime-start from the decoder log."""
import json
import os

import decoder_log
import server
import story
from test_decoder_build import DAY, _dec, _e1, _post_at

M = lambda hm: story.day_ms(DAY, hm)                                  # noqa: E731
BAR = story.BAR_MS


def _bars(h0="09:15", n=24, o=22800.0, step=-2.0):
    t0 = M(h0)
    return [{"t": t0 + i * BAR, "o": o + i * step, "h": o + i * step + 6, "l": o + i * step - 6, "c": o + (i + 1) * step}
            for i in range(n)]


def _ev(kind, hm, side, state="CONFIRMED", at=None, split=None, p=22790.0, chip=None, shown=True, **kw):
    t = M(hm)
    return {"id": f"{kind}@{t}@{p}", "kind": kind, "t": t, "time": hm, "p": p, "side": side, "state": state, "at": at,
            "split": split, "shown": shown, "chip": chip or f"{kind} {hm}", "chips": [chip or f"{kind} {hm}"],
            "en": f"{kind} at {hm}", **kw}


def _fold(d=1, entry="10:00", E=22800.0, fut=22780.0, events=(), headline="HOLD", ok=True):
    return {"ok": ok, "id": "NIFTY-22800CE-long-100000", "trade": {"entry_t": entry + ":00", "exit_t": None},
            "view": {"headline": headline, "clause": "nothing behind you now", "d": d, "E": E, "fut": fut,
                     "chips": {"Z": "WITH", "F": None, "O": None, "V": None}, "events": list(events), "frozen": False}}


BAND = {"kind": "band", "name": "neeche band", "z": -1.7}


# ---- CHAPTERS: the whole day, contiguous, the current one last -------------------------------------------------------
def test_chapters_cover_the_whole_day_from_the_first_bar_to_now():
    dec = _dec([_e1(t=M("10:10"), p=22790.0, side=1), _ev("E7", "11:30", -1, chip="CVD ulta ▼")])
    trap = {"events": [{"kind": "state", "t": "10:42:10", "level": "PDH", "px": 22753.2, "state": "INDUCED", "dir": "UP", "src": "live"},
                       {"kind": "state", "t": "10:55:00", "level": "PDH", "px": 22753.2, "state": "FAILED", "src": "live"}]}
    ch = story.chapters(dec, _bars(), DAY, trap, now_ms=M("11:20"))["items"]
    assert ch[0]["start"] == "09:15" and ch[0]["name"].startswith("SHURU"), "the day starts at the first bar"
    assert ch[-1]["end"] == "abhi" and ch[-1]["current"] and not any(c["current"] for c in ch[:-1])
    assert all(a["end"] == b["start"] for a, b in zip(ch, ch[1:])), "no hole between chapters"
    names = [c["name"] for c in ch]
    assert any(n.startswith("BADA SELLER") or n.startswith("BADA BUYER") for n in names), names
    fail = next(c for c in ch if c["name"].startswith("FAIL"))
    assert "buyers phanse" in fail["name"] and fail["side"] == -1, "a failed UP break traps the buyers"
    assert all(len(c["chips"]) <= 3 and c["asar"] is not None for c in ch)


def test_a_restart_rebuilds_the_morning_from_the_decoder_log_tagged():
    logged = [_e1(t=M("09:40"), p=22810.0, side=-1)]
    ch = story.chapters(_dec([]), _bars(), DAY, None, logged=logged, now_ms=M("11:00"))["items"]
    first_print = next(c for c in ch if c["name"].startswith("BADA"))
    assert first_print["src"] == ["log"], "an event only the log kept is tagged log, never blended as live"
    both = story.chapters(_dec([_e1(t=M("09:40"), p=22810.0, side=-1)]), _bars(), DAY, None, logged=logged)["items"]
    assert next(c for c in both if c["name"].startswith("BADA"))["src"] == ["live"], "the page's own post wins"


def test_the_decoder_log_reads_back_its_events_with_their_newest_state(monkeypatch):
    _post_at(monkeypatch, DAY, "10:00")
    evs = decoder_log.read_events(DAY, "NIFTY")
    assert len(evs) == 1 and evs[0]["kind"] == "E1" and evs[0]["state"] == "BAAKI"
    assert decoder_log.read_events(DAY, "BANKNIFTY") == [] and decoder_log.read_events("2026-09-10", "NIFTY") == []


# ---- THE DECODER'S COUNT BESIDE HER TRADE -------------------------------------------------------------------------
def test_trade_read_counts_against_and_behind_her_side_since_entry():
    dec = _dec([_ev("E2", "09:50", -1),                                  # before her entry: not counted
                _ev("E2", "10:05", -1),                                  # against a long
                _ev("E3", "10:10", 1, split="absorbed"),                 # buyers absorbed = against
                _ev("E4", "10:15", -1, state="FAILED"),                  # a failed seller stack = behind
                _ev("E7", "10:20", 1, state="FAILED")])                  # a failed divergence counts nothing
    r = story.trade_read(dec, _fold(entry="10:00"), None, DAY)["read"]
    assert (r["against"], r["behind"]) == (2, 1), r["items"]
    assert r["word"] == "PULLBACK", "price below entry, no print / trap / naye run against: a pullback"
    assert "beside the engine's word" in r["note"]


def test_gave_up_needs_a_print_at_a_level_a_trap_failure_or_two_bars_of_new_shorts():
    dec = _dec([_e1(t=M("10:05"), p=22790.0, side=-1)])
    dec["events"][0]["at"] = BAND
    r = story.trade_read(dec, _fold(entry="10:00"), None, DAY)["read"]
    assert r["word"] == "GAVE UP" and r["word_t"] == "10:10" and "BADA SELLER" in r["word_because"] and r["word_why"] is None
    per = [{"t": M("10:05"), "quad": "naye short"}, {"t": M("10:10"), "quad": "naye short"}, {"t": M("10:15"), "quad": "dono taraf"}]
    r2 = story.trade_read(_dec([], per), _fold(entry="10:00"), None, DAY)["read"]
    assert r2["word"] == "GAVE UP" and r2["against"] == 1 and "×2 bars" in r2["items"][0]["chip"]
    r3 = story.trade_read(_dec([], per[:1]), _fold(entry="10:00"), None, DAY)["read"]
    assert r3["word"] == "PULLBACK", "one bar of new shorts is not yet a give-up"
    up = story.trade_read(dec, _fold(entry="10:00", fut=22820.0), None, DAY)["read"]
    assert up["word"] is None and up["word_why"], "price with her: no word, and the reason"


def test_trade_read_is_none_with_its_reason_when_flat_or_the_engine_failed():
    for f in (None, {"ok": False, "why": "could not check"}, _fold(headline=None)):
        out = story.trade_read(_dec([]), f, None, DAY)
        assert out["read"] is None and out["read_why"]


# ---- HIGHLIGHTS: each tier on its trigger, gone after 3 minutes -----------------------------------------------------
def _hl(now, **kw):
    dec = kw.pop("dec", _dec([]))
    fold = kw.pop("fold", None)
    tr = story.trade_read(dec, fold, kw.get("trap"), DAY)["read"]
    return story.highlights(dec, fold, {"read": tr}, DAY, M(now), **kw)


def test_red_fires_on_fold_past_give_up_a_print_against_her_and_the_decoder_flip():
    fold = _fold(entry="10:00", events=[{"kind": "fold", "t": M("10:20"), "text": "FOLD · 10:20"}])
    assert [h["kind"] for h in _hl("10:21", fold=fold)] == ["FOLD"] and _hl("10:21", fold=fold)[0]["tier"] == "red"
    pg = _fold(entry="10:00", events=[{"kind": "touch", "t": M("10:20"), "text": "give-up 22769 touched"}])
    assert _hl("10:20:30", fold=pg)[0]["kind"] == "PAST GIVE-UP"
    dec = _dec([_e1(t=M("10:05"), p=22790.0, side=-1)])
    dec["events"][0]["at"] = BAND
    hs = _hl("10:11", dec=dec, fold=_fold(entry="10:00"))
    kinds = {h["kind"]: h["tier"] for h in hs}
    assert kinds.get("PRINT AGAINST") == "red" and kinds.get("DECODER FLIP") == "red"
    assert "BADA PRINT" not in kinds, "the same print is red for her trade, not amber twice"


def test_a_highlight_lives_three_minutes_then_is_gone():
    fold = _fold(entry="10:00", events=[{"kind": "fold", "t": M("10:20"), "text": "FOLD · 10:20"}])
    h = _hl("10:23", fold=fold)
    assert h and not h[0]["fading"], "still there, full, at exactly 3 minutes"
    assert _hl("10:23:01", fold=fold)[0]["fading"], "then it fades (20 s), never a blink"
    assert _hl("10:23:21", fold=fold) == [], "and is gone"
    assert _hl("10:19:59", fold=fold) == [], "never before it happened"


def test_amber_fires_on_a_new_print_a_trap_state_power_vpin_weekly_and_cant_check():
    dec = _dec([_e1(t=M("10:05"), p=22790.0, side=1)], per=[{"t": M("10:05"), "step": True, "quad": "OI step"}])
    trap = {"events": [{"kind": "state", "t": "10:09:00", "level": "PDL", "px": 22600.0, "state": "RELEASED", "dir": 1, "src": "live"}],
            "slots": [{"t": "10:10", "power": True, "pdir": 1, "episode_t0": "09:55"}]}     # a slot's t is its END mark
    three = {"t": "10:10", "n_weekly_power": 2, "dir_weekly": 1}
    hs = _hl("10:11", dec=dec, trap=trap, slots=trap["slots"], three=three, vpin={"pct": 0.86, "since_ms": M("10:08")},
             cant=[{"what": "OI", "t_ms": M("10:09"), "block": "flat"}])
    got = {h["kind"] for h in hs if h["tier"] == "amber"}
    assert {"BADA PRINT", "OI STEP", "TRAP", "POWER", "WEEKLY 2/2", "VPIN", "CANT CHECK"} <= got, got
    pushti = _hl("10:06", slots=[{"t": "10:05", "power": True, "pdir": -1, "episode_t0": "10:05"}])
    assert pushti[0]["kind"] == "PUSHTI"
    fold = _fold(entry="10:00", events=[{"kind": "chip", "t": M("10:12"), "chip": "OI", "old": "AGAINST", "new": "CAN'T CHECK"}])
    assert any(h["kind"] == "CANT CHECK" and h["block"] == "trade" for h in _hl("10:13", fold=fold))


def test_blue_fires_when_evidence_behind_her_grows_and_her_print_level_holds_a_test():
    dec = _dec([_e1(t=M("10:05"), p=22790.0, side=1), _ev("E2", "10:10", 1)])
    dec["events"][0]["tests"] = [M("10:10")]                            # the 10:10 bar traded at his price and held
    hs = _hl("10:15:30", dec=dec, fold=_fold(entry="10:00", fut=22810.0))
    kinds = {h["kind"]: h["tier"] for h in hs}
    assert kinds.get("BEHIND GROWS") == "blue" and kinds.get("LEVEL HOLDS") == "blue", hs
    assert [h["tier"] for h in hs] == sorted((h["tier"] for h in hs), key=story.TIERS.index), "red first, then amber, then blue"


def test_compose_all_keeps_every_why_pair_and_leaves_the_engine_word_alone():
    from test_frame import _why_pairs
    fold = _fold(entry="10:00")
    for f, bars, dec in ((None, _bars(), _dec([_e1(t=M("10:05"), side=-1)])), (fold, _bars(), _dec([_e1(t=M("10:05"), side=-1)])),
                         (None, [], _dec([])), (fold, [], None)):
        out = story.compose_all(dec, 22780.0, DAY, M("10:12"), bars, f)
        bad = [(k, v, w) for _, k, v, w in _why_pairs(out) if (v is None) == (w is None)]
        assert not bad, bad
    assert fold["view"]["headline"] == "HOLD" and "decoder" not in fold["view"], "the engine's reply is read, never written"


# ---- THE MINUTE LOG: once per trade per minute, behind the market-hours gate ---------------------------------------
def test_minute_log_writes_once_per_trade_per_minute():
    f = _fold()
    r = story.trade_read(_dec([]), f, None, DAY)["read"]
    assert decoder_log.minute(DAY, "NIFTY", "10:21", f, r) is True
    assert decoder_log.minute(DAY, "NIFTY", "10:21", f, r) is False, "the same minute twice is one row"
    assert decoder_log.minute(DAY, "NIFTY", "10:22", f, r) is True
    assert decoder_log.minute(DAY, "NIFTY", "10:23", {"ok": False}, None) is False, "no engine word, no row"
    rows = [json.loads(l) for l in open(decoder_log.minute_path(DAY), encoding="utf-8")]
    assert [x["minute"] for x in rows] == ["10:21", "10:22"]
    assert rows[0]["engine"]["headline"] == "HOLD" and rows[0]["decoder"]["against"] == 0
    decoder_log._MIN_SEEN.clear()                                       # a restart reads the keys back off the file
    assert decoder_log.minute(DAY, "NIFTY", "10:22", f, r) is False


def _post_marked(monkeypatch, now_day, now_hm):
    import fold_live
    monkeypatch.setattr(fold_live, "frame", lambda idx, trades: (_fold(), None))
    return _post_at(monkeypatch, now_day, now_hm)


def test_the_post_logs_the_minute_in_session_only_and_serves_the_story(monkeypatch):
    for now_day, now_hm in (("2026-09-13", "11:00"), (DAY, "16:10")):
        _post_marked(monkeypatch, now_day, now_hm)
        assert not os.path.exists(decoder_log.minute_path(DAY)), (now_day, now_hm)
    _post_marked(monkeypatch, DAY, "10:21")
    rows = [json.loads(l) for l in open(decoder_log.minute_path(DAY), encoding="utf-8")]
    assert len(rows) == 1 and rows[0]["minute"] == "10:21" and rows[0]["engine"]["headline"] == "HOLD"
    st = server._SENSES["frame"]["NIFTY"]["story"]
    assert {"chapters", "trade_read", "highlights", "book", "trap", "now_ms", "hold_ms"} <= set(st)
    assert st["chapters"]["items"][0]["start"] == "09:35" and st["trade_read"]["trade_id"] == "NIFTY-22800CE-long-100000"


# ---- for the DESK (the Validate-tab agent's asks, 2026-10-04): the flat lean, a past day's chapters, RECORD's +20 / +40 ----
def test_the_flat_lean_counts_up_and_down_since_the_current_chapter():
    dec = _dec([_ev("E2", "09:30", 1),                                   # before the chapter: not in the lean
                _e1(t=M("10:05"), p=22790.0, side=-1), _ev("E3", "10:15", 1, split="absorbed"), _ev("E2", "10:20", 1)])
    out = story.compose_all(dec, 22780.0, DAY, M("10:30"), _bars(), None)
    ln = out["lean"]
    assert out["lean_why"] is None and ln["since"] == "10:10", ln          # the BADA SELLER opened the current chapter
    assert (ln["up"], ln["down"]) == (1, 2) and "never a %" in ln["why"]
    assert out["trade_read"] is None, "flat: no trade count, the lean instead"
    none = story.compose_all(_dec([]), None, DAY, M("10:30"), [], None)
    assert none["lean"] is None and none["lean_why"]


def _get(path):
    from test_frame_api import _Req
    req = _Req(path, {})
    server.Handler.do_GET(req)
    return req.out[-1][1]


def test_a_past_days_story_comes_off_the_saved_logs_only():
    decoder_log.append(_dec([_e1(t=story.day_ms("2026-09-10", "10:05"), p=22790.0, side=1)]), [], "2026-09-10", "NIFTY")
    body = _get("/api/story?idx=NIFTY&day=2026-09-10")
    assert body["ok"] and body["past"] and body["src"] == "log" and body["events_logged"] == 1, body
    ch = body["chapters"]["items"]
    assert any(c["name"].startswith("BADA") and c["start"] == "10:10" and c["src"] == ["log"] for c in ch), ch
    empty = _get("/api/story?idx=NIFTY&day=2026-09-09")
    assert empty["ok"] is False and "no decoder log and no trap log" in empty["chapters"]["items_why"]
    assert _get("/api/story?idx=NIFTY&day=09-10")["ok"] is False


def test_record_carries_her_strikes_premium_20_and_40_minutes_after_her_exit():
    import fold_live
    chain = [{"ts": "11:36:54", "strikes": [{"k": 22750, "ce": {"ltp": 138.8}, "pe": {"ltp": 90.0}}]},
             {"ts": "11:59:59", "strikes": [{"k": 22750, "ce": {"ltp": 150.0}, "pe": {"ltp": 80.0}}]}]
    tr = {"k": 22750.0, "side": "CE", "exit_t": "11:16:50"}
    later, why = fold_live.prem_after_exit(chain, tr, 127.55)
    assert why is None and later[0]["min"] == 20 and later[0]["prem"] == 138.8 and later[0]["vs_exit"] == 11.25
    assert later[1]["prem"] is None and "no chain snapshot 11:56–11:59" in later[1]["why"], "11:59:59 is past 3 min: a why, never a zero"
    assert fold_live.prem_after_exit(chain, {**tr, "exit_t": None}, None) == (None, "still open")
