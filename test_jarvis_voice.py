"""jarvis_voice: the model behind one seam, fenced to the card (Jarvis v3 Task 7). No network, no real key: every test
points DIR and KEYS at tmp, and the providers are fakes (an injected callable, a fake `anthropic` module, a fake urlopen)."""
import json
import sys
import types

import pytest

import jarvis_voice as jv

CARD = {"ok": True, "idx": "NIFTY", "day": "2026-11-02", "at": "10:42", "asof": "10:42:51", "live": True,
        "word": "TREND ▼", "state": "HOLD", "lean": -1, "since": "09:56",
        "count": {"with": 4, "against": 1, "N": 6, "unread": 2,
                  "pieces": [{"k": "wf7", "side": "with", "text": "writers ±7 DOWN (CE +12.1L · PE −14.0L / 3 min)"},
                             {"k": "wall_ahead", "side": "against", "text": "wall ahead 22,900s PE 186L BUILDING"},
                             {"k": "fut_oi", "side": "with", "text": "fut OI fresh shorts +612 lots / 30 min"}]},
        "leg": "leg ▼ TREND 103 pts · 2.5σ · TOOT 09:51 · origin 23,135f 09:35 · extreme 23,002f 10:04",
        "expression": {"buyer": "buy the PE on a pullback to d1 22,990f, not chased · needs +62 pts today",
                       "seller": "sell the CE at / above 23,000s (23,043f): call writers are writing it · IV 13.4 vs RV 9.8 → rich",
                       "pick": "seller"},
        "wrong_line": "PALAT? if back past 22,938f (0.35 of the leg) · PALAT at 22,886f",
        "walls": {"ce": {"k": 23000, "f": 23043.0, "oi": 147.0, "state": "BUILDING"},
                  "pe": {"k": 22900, "f": 22943.0, "oi": 186.0, "state": "BUILDING"}},
        "health": {"missing": [], "notes": ["note 09:02 RBI 11:00 today"]},
        "voice": {"lines": ["old voice 77,777"], "provider": "claude", "fell_back": False, "why": None}}
ENGINE = [CARD["word"], CARD["leg"], CARD["wrong_line"]]
GOOD = "TREND ▼ since 09:56 · WITH 4 · AGAINST 1 · wrong if back past 22,938f"


REAL_LATER = jv.later        # conftest makes later a no-op in every test (no thread outlives one); the hook tests restore it


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(jv, "DIR", str(tmp_path / "jarvis"))
    monkeypatch.setattr(jv, "KEYS", str(tmp_path / "keys"))
    for k, v in (("_WORD", {}), ("_PREOPEN", set()), ("_SEQ", {})):
        monkeypatch.setattr(jv, k, v)
    (tmp_path / "keys").mkdir()
    return tmp_path


def _log(tmp_path):
    p = tmp_path / "jarvis" / f"voice_{jv._today()}.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def say(text):
    return lambda system, user: text


# ---- the fence (code, never prompt) ----

def test_the_fence_rejects_a_made_up_number():
    assert jv.fence("TREND ▼ holds while the wall at 22,751s stands", CARD) == "fence: number not in the card"
    assert jv.fence("2192", CARD)            # ensure_ascii=False: the card's "→ rich" is not "→ rich", so no 2192


def test_the_fence_rejects_a_percent_or_a_rate_word():
    assert jv.fence("WITH 4 · writers 4% stronger", CARD) == "fence: rate sign"
    for ln in ("writers 4％ down", "a good chance of 22,900s", "odds favour TREND ▼", "confidence high", "likelihood low",
               "probably TREND ▼"):
        assert jv.fence(ln, CARD) == "fence: rate sign", ln


def test_the_fence_rejects_an_order_word():
    for ln in ("buy 5 lots now", "square off at 22,938f", "square-off at 22,938f", "squareoff at 22,938f",
               "go short below 22,886f", "consider shorting the CE", "shorted at 22,938f", "place it at 22,938f"):
        assert jv.fence(ln, CARD) == "fence: order word", ln
    assert jv.fence("fut OI fresh shorts", CARD) is None            # shorts: the card's OI noun


def test_the_fence_holds_the_count_to_the_card():
    assert jv.fence("WITH 4 · AGAINST 1", CARD) is None
    assert jv.fence("WITH 1 · AGAINST 4", CARD) == "fence: count mismatch"
    assert jv.fence("WITH 4", {"ok": True, "count": None, "x": 4}) == "fence: count mismatch"


def test_the_fence_rejects_four_lines_and_a_long_line():
    assert "4 lines" in jv.fence("\n".join([GOOD] * 4), CARD)
    assert "140" in jv.fence("TREND ▼ " + "x" * 140, CARD)


def test_the_fence_rejects_an_empty_reply():
    assert jv.fence("  \n ", CARD)


def test_the_fence_accepts_a_good_reply():
    assert jv.fence(GOOD + "\nwall ahead 22,900s PE 186L BUILDING · TOOT 09:51", CARD) is None


def test_numbers_normalise_indian_and_western_grouping_and_decimals():
    card = dict(CARD, extra={"oi": 2305100, "iv": 13.40})
    assert jv.fence("OI 23,05,100 · IV 13.4 · 186.0", card) is None
    assert jv.fence("OI 2,305,100", card) is None
    assert jv.fence("OI 23,05,101", card)


def test_times_count_as_numbers():
    assert jv.fence("TREND ▼ since 09:56", CARD) is None
    assert jv.fence("TREND ▼ since 10:42", dict(CARD, at="10:41")) is None     # asof 10:42:51 holds 10:42
    assert jv.fence("TREND ▼ since 9:56", CARD) is None           # the hour zero-padded
    assert jv.fence("TREND ▼ since 09:57", CARD) == "fence: number not in the card"


def test_the_old_voice_is_not_a_source_of_numbers():
    assert jv.fence("77,777", CARD)


def test_a_verbatim_clause_of_the_expression_may_carry_its_order_word():
    assert jv.fence('seller: "sell the CE at / above 23,000s (23,043f): call writers are writing it"', CARD) is None
    assert jv.fence("sell the CE at 23,000s", CARD)                 # not a verbatim clause


def test_her_question_numbers_are_hers_to_quote():
    assert jv.fence("22,800 is not in today's frame · nearest wall 22,900s PE", CARD, "what if 22800 breaks") is None
    assert jv.fence("22,800 is not in today's frame", CARD)


# ---- speak ----

def test_no_key_gives_the_engine_lines_and_says_so():
    out = jv.speak(CARD)
    assert out == {"lines": ENGINE, "provider": "engine", "fell_back": True, "why": "no key"}


def test_the_engine_lines_are_the_cards_why_when_it_has_them():
    assert jv.speak(dict(CARD, why=["a", "b", "c", "d"]))["lines"] == ["a", "b", "c"]
    assert jv.engine_lines({"ok": False, "why": "could not check — no frame built yet"}) == ["could not check — no frame built yet"]
    assert jv.engine_lines({"ok": True})                          # never blank


def test_a_card_that_could_not_build_is_never_sent():
    calls = []
    out = jv.speak({"ok": False, "why": "could not check — no frame"}, provider=lambda s, u: calls.append(1) or GOOD)
    assert out["fell_back"] and not calls and out["lines"] == ["could not check — no frame"]


def test_an_injected_provider_that_passes_the_fence_speaks():
    seen = {}

    def fake(system, user):
        seen.update(system=system, user=user)
        return GOOD + "\n"

    out = jv.speak(CARD, provider=fake)
    assert out == {"lines": [GOOD], "provider": "injected", "fell_back": False, "why": None}
    assert "never" in seen["system"].lower() and "TREND ▼" in seen["user"] and "77,777" not in seen["user"]


@pytest.mark.parametrize("reply, check", [("TREND ▼ · wall 22,751s", "number not in the card"), ("writers 4% down", "rate sign"),
                                          ("buy 5 lots", "order word"), ("\n".join([GOOD] * 4), "4 lines")])
def test_a_reply_that_fails_the_fence_falls_back_and_names_the_check(reply, check):
    out = jv.speak(CARD, provider=say(reply))
    assert out["fell_back"] and out["lines"] == ENGINE and out["provider"] == "injected" and check in out["why"]


@pytest.mark.parametrize("reply, kept_out", [("TREND ▼ · wall 22,751s", "22,751"), ("writers 4% down", "%"),
                                             ("writers 4％ down", "％"), ("buy 5 lots", "buy"), ("buy 5 lots", "lots"),
                                             ("a good chance of TREND ▼", "chance")])
def test_what_the_fence_keeps_out_never_reaches_the_why_or_the_log(_tmp, reply, kept_out):
    out = jv.speak(CARD, provider=say(reply))
    row = json.dumps(_log(_tmp), ensure_ascii=False)
    assert out["fell_back"] and kept_out not in json.dumps(out, ensure_ascii=False) and kept_out not in row
    assert "%" not in row and "%" not in json.dumps(out, ensure_ascii=False)


def test_a_provider_error_falls_back_by_its_class_name_only(_tmp):
    def boom(system, user):
        raise RuntimeError("sk-ant-SECRET in a message")

    out = jv.speak(CARD, provider=boom)
    assert out["fell_back"] and out["why"] == "injected call failed — RuntimeError"
    assert "SECRET" not in json.dumps(_log(_tmp))


def test_the_log_row_shape(_tmp):
    jv.on_change(CARD, provider=say(GOOD))
    jv.answer(CARD, "why?", provider=say(GOOD))
    rows = _log(_tmp)
    assert [r["kind"] for r in rows] == ["change", "ask"]
    for r in rows:
        assert {"at", "t", "idx", "kind", "provider", "in_tokens", "out_tokens", "lines", "fell_back", "why"} <= set(r)
        assert r["idx"] == "NIFTY" and r["lines"] == [GOOD] and r["fell_back"] is False and len(r["t"]) == 8
    assert rows[1]["q"] == "why?"
    assert "%" not in json.dumps(rows)


def test_the_budget_cap_keeps_the_last_10_calls_for_her_asks(_tmp):
    (_tmp / "keys" / "cap.json").write_text('{"calls_per_day": 12}')
    calls = []

    def count(system, user):
        calls.append(1)
        return GOOD

    outs = [jv.speak(CARD, provider=count) for _ in range(3)]       # narrations stop at 12 - 10
    assert len(calls) == 2 and outs[2]["why"] == "cap reached (10 kept for her asks)" and outs[2]["provider"] == "engine"
    asks = [jv.answer(CARD, "why?", provider=count) for _ in range(11)]
    assert len(calls) == 12 and asks[-1]["why"] == "cap reached" and not asks[-2]["fell_back"]
    jv.speak(CARD)                                                  # no-key rows are not calls
    assert jv._calls_today() == 12


def test_one_torn_character_never_stops_the_budget(_tmp):
    jv.speak(CARD, provider=say(GOOD))
    with open(jv._path(), "ab") as f:
        f.write(b'{"provider": "claude", "x": "\xff\xfe"}\n\x80\x81 torn\n')
    jv.speak(CARD, provider=say(GOOD))
    assert jv._calls_today() == 3 and not jv.speak(CARD, provider=say(GOOD))["fell_back"]


def test_the_cap_defaults_to_80(_tmp):
    assert jv._cap() == 80
    (_tmp / "keys" / "cap.json").write_text("not json")
    assert jv._cap() == 80


# ---- the providers (fakes; no network) ----

class _Block:
    def __init__(self, type, text=""):
        self.type, self.text = type, text


def _fake_sdk(monkeypatch, text=GOOD, stop="end_turn", blocks=None):
    seen = {}

    class Messages:
        def create(self, **kw):
            seen["kw"] = kw
            usage = types.SimpleNamespace(input_tokens=900, cache_read_input_tokens=4000, cache_creation_input_tokens=None,
                                          output_tokens=120)
            texts = [text] if isinstance(text, str) else text
            content = blocks or [_Block("thinking")] + [_Block("text", t) for t in texts]
            return types.SimpleNamespace(stop_reason=stop, content=content, usage=usage)

    class Anthropic:
        def __init__(self, **kw):
            seen["client"], seen["closed"] = kw, False
            self.messages = Messages()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            seen["closed"] = True
            return False

    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=Anthropic))
    return seen


def test_a_utf16_key_file_reads_by_its_bom(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_bytes("sk-ant-SECRET\r\n".encode("utf-16"))   # PowerShell 5.1's `echo k > f`
    seen = _fake_sdk(monkeypatch)
    assert jv.speak(CARD)["provider"] == "claude" and seen["client"]["api_key"] == "sk-ant-SECRET"


@pytest.mark.parametrize("raw", [b"\xff\xfeA", b"\x80sk-ant-SECRET"])          # torn UTF-16; not UTF-8 and no BOM
def test_an_unreadable_key_file_is_a_named_fallback_never_a_raise(_tmp, monkeypatch, raw):
    (_tmp / "keys" / "anthropic.txt").write_bytes(raw)
    _fake_sdk(monkeypatch)
    for out in (jv.speak(CARD), jv.answer(CARD, "why?"), jv.on_change(CARD)):
        assert out == {"lines": ENGINE, "provider": "engine", "fell_back": True, "why": "key file unreadable"}
    assert "SECRET" not in json.dumps(_log(_tmp)) and jv._calls_today() == 0


def test_a_utf8_bom_key_file_reads_the_bare_key(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_bytes("﻿sk-ant-SECRET \r\n".encode("utf-8"))   # Notepad's UTF-8 with BOM
    seen = _fake_sdk(monkeypatch)
    assert jv.speak(CARD)["provider"] == "claude" and seen["client"]["api_key"] == "sk-ant-SECRET"


@pytest.mark.parametrize("card", [None, "TREND ▼", ["TREND ▼"], 7, {"ok": True, "why": 5}, {"ok": True, "why": {"a": 1}}])
def test_speak_never_raises_on_a_bad_card(card):
    out = jv.speak(card, provider=say(GOOD))
    assert set(out) == {"lines", "provider", "fell_back", "why"} and out["lines"] and all(isinstance(x, str) for x in out["lines"])


def test_any_error_is_a_fallback_named_by_its_class_only(monkeypatch):
    def boom(effort, web):
        raise ValueError("sk-ant-SECRET")

    monkeypatch.setattr(jv, "_pick", boom)
    out = jv.speak(CARD)
    assert out == {"lines": ENGINE, "provider": "engine", "fell_back": True, "why": "ValueError"}
    assert jv.answer(CARD, "q")["why"] == "ValueError" and jv.brief(LEVELS, [], [])["why"] == "ValueError"


def test_a_log_that_cannot_open_makes_no_call_the_budget_fails_closed(_tmp, monkeypatch):
    calls = []
    (_tmp / "jarvis" / f"voice_{jv._today()}.jsonl").mkdir(parents=True)   # the day's log is a folder: it cannot open
    out = jv.speak(CARD, provider=lambda s, u: calls.append(1) or GOOD)
    assert not calls and out["fell_back"] and out["lines"] == ENGINE and out["why"] == "log cannot open · log unwritable"


def test_an_unwritable_log_still_returns_the_lines(_tmp, monkeypatch):
    (_tmp / "a_file").write_text("x")
    monkeypatch.setattr(jv, "DIR", str(_tmp / "a_file"))          # makedirs on a file -> OSError
    monkeypatch.setattr(jv, "_calls_today", lambda: 0)            # past the budget's open, the write itself fails
    out = jv.speak(CARD, provider=say(GOOD))
    assert out == {"lines": [GOOD], "provider": "injected", "fell_back": False, "why": "log unwritable"}
    assert jv.speak(CARD)["why"] == "no key · log unwritable"


def test_cited_blocks_join_into_lines_and_each_web_item_starts_one(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_text("k")
    seen = _fake_sdk(monkeypatch, text=["[web] RBI policy at ", "10:00", " today", "[web] US CPI 18:00 IST\n", "PDH 23,155s"])
    out = jv.brief(LEVELS, [], [])
    assert out["lines"] == ["[web] RBI policy at 10:00 today", "[web] US CPI 18:00 IST", "PDH 23,155s"] and seen["closed"]


def test_claude_call_shape_and_key_handling(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_text("sk-ant-SECRET\n")
    seen = _fake_sdk(monkeypatch)
    out = jv.speak(CARD)
    assert out == {"lines": [GOOD], "provider": "claude", "fell_back": False, "why": None}
    kw = seen["kw"]
    assert seen["client"]["api_key"] == "sk-ant-SECRET" and seen["client"]["base_url"] == "https://api.anthropic.com"
    assert kw["model"] == "claude-opus-5-5" and kw["max_tokens"] == 600 and kw["output_config"] == {"effort": "low"}
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"} and "thinking" not in kw and "temperature" not in kw
    assert "tools" not in kw
    jv.answer(CARD, "what next?")
    assert seen["kw"]["output_config"] == {"effort": "medium"} and "what next?" in seen["kw"]["messages"][0]["content"]
    rows = _log(_tmp)
    assert rows[0]["in_tokens"] == 4900 and rows[0]["out_tokens"] == 120
    assert "SECRET" not in (_tmp / "jarvis" / f"voice_{jv._today()}.jsonl").read_text(encoding="utf-8")
    assert "SECRET" not in json.dumps(out)


def test_claude_refusal_falls_back(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_text("k")
    _fake_sdk(monkeypatch, stop="refusal")
    out = jv.speak(CARD)
    assert out["fell_back"] and out["why"] == "refused" and out["lines"] == ENGINE


def test_a_cut_off_reply_falls_back(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_text("k")
    _fake_sdk(monkeypatch, stop="max_tokens")
    assert jv.speak(CARD)["why"] == "max_tokens"


def test_an_unfinished_web_search_falls_back(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_text("k")
    _fake_sdk(monkeypatch, text=WEB, stop="pause_turn")
    out = jv.brief(LEVELS, [], [])
    assert out["fell_back"] and out["why"] == "pause_turn"


def test_no_sdk_is_a_named_fallback_not_an_error(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_text("k")
    monkeypatch.setitem(sys.modules, "anthropic", None)            # import anthropic -> ImportError
    out = jv.speak(CARD)
    assert out == {"lines": ENGINE, "provider": "engine", "fell_back": True, "why": "anthropic SDK not installed"}
    assert jv._calls_today() == 0


def test_gemini_via_urllib(_tmp, monkeypatch):
    (_tmp / "keys" / "gemini.txt").write_text("g-SECRET")
    seen = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"candidates": [{"content": {"parts": [{"text": GOOD}]}}],
                               "usageMetadata": {"promptTokenCount": 3000, "candidatesTokenCount": 40}}).encode()

    def urlopen(req, timeout=None):
        seen.update(url=req.full_url, key=req.get_header("X-goog-api-key"), body=json.loads(req.data))
        return Resp()

    monkeypatch.setattr(jv.urllib.request, "urlopen", urlopen)
    out = jv.speak(CARD)
    assert out == {"lines": [GOOD], "provider": "gemini", "fell_back": False, "why": None}
    assert seen["url"].endswith("/models/gemini-flash-latest:generateContent") and seen["key"] == "g-SECRET"
    assert list(seen["body"]) == ["contents"] and "TREND ▼" in seen["body"]["contents"][0]["parts"][0]["text"]
    (_tmp / "keys" / "gemini_model.txt").write_text("gemini-2.5-pro\n")
    jv.speak(CARD)
    assert "/models/gemini-2.5-pro:" in seen["url"]
    assert "SECRET" not in json.dumps(_log(_tmp)) and _log(_tmp)[0]["in_tokens"] == 3000


def test_anthropic_key_wins_over_gemini(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_text("k")
    (_tmp / "keys" / "gemini.txt").write_text("g")
    _fake_sdk(monkeypatch)
    assert jv.speak(CARD)["provider"] == "claude"


# ---- the pre-open brief ----

LEVELS = {"PDH": "23,155s", "PDL": "22,870s", "PDC": "23,010s"}
WEB = ("[web] RBI policy 10:00 today\n[web] US CPI 18:00 IST · Dow −180 overnight\n[web] NIFTY weekly expiry Tue 4 Nov\n"
       "PDH 23,155s · PDL 22,870s")


def test_the_brief_with_web_search(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_text("k")
    seen = _fake_sdk(monkeypatch, text=WEB)
    out = jv.brief(LEVELS, [{"t": "15:29", "word": "TREND ▼"}], ["note 08:50 RBI 10:00"])
    assert out["fell_back"] is False and len(out["lines"]) == 4
    assert seen["kw"]["tools"] == [{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}]
    assert _log(_tmp)[-1]["kind"] == "brief"
    again = jv.brief(LEVELS, [], [])                                # once a day
    assert again["lines"] == out["lines"] and len(_log(_tmp)) == 1


def test_the_brief_is_fenced():
    out = jv.brief(LEVELS, [], [], provider=say("PDH 23,999s"))     # a made-up number off a [web] line
    assert out["fell_back"] and out["why"] == "fence: number not in the card"
    out = jv.brief(LEVELS, [], [], provider=say("[web] Dow −0.4%"))
    assert out["fell_back"] and out["why"] == "fence: rate sign"
    assert jv.brief(LEVELS, [], [], provider=say("\n".join(["[web] x"] * 7)))["fell_back"]
    assert jv.brief(LEVELS, [], [])["why"] == "no key"


def test_the_count_check_reads_any_case_and_never_a_level():
    assert jv.fence("with 1 · against 4", CARD) == "fence: count mismatch"
    assert jv.fence("With 4 · Against 1", CARD) is None
    assert jv.fence("price sits with 22,900s PE at 186L", CARD) is None
    assert jv.brief(LEVELS, [], [], provider=say("[web] RBI with 25 bps")) ["fell_back"] is False   # a web item: not the count


def test_the_rate_check_catches_percentage_points_and_the_arabic_sign():
    assert jv.fence("a 0.5 percentage point move", CARD) == "fence: rate sign"
    assert jv.fence("writers 4٪ down", CARD) == "fence: rate sign"


def test_the_brief_keeps_only_the_text_after_the_last_search_result(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_text("k")
    blocks = [_Block("text", "Let me search for 99 things."), _Block("server_tool_use"), _Block("web_search_tool_result"),
              _Block("text", "Searching again."), _Block("server_tool_use"), _Block("web_search_tool_result"),
              _Block("text", "[web] RBI policy 10:00 today")]
    _fake_sdk(monkeypatch, blocks=blocks)
    assert jv.brief(LEVELS, [], [])["lines"] == ["[web] RBI policy 10:00 today"]


# ---- the server's hook (Phase B) ----

import jarvis_log                                                    # noqa: E402

DAY = "2026-11-02"
TODAY = jv._today()
FRAME = {"ok": True, "day": DAY, "idx": "NIFTY", "asof": "10:41:30", "live": True, "mins": ["10:41"],
         "fut": [23010.5], "spot": [22967.3],
         "call": {"at": "10:41", "word": "TREND ▼", "state": "HOLD", "lean": -1, "since": "09:56", "leg": "leg ▼ TREND 103 pts",
                  "why": ["writers ±7 DOWN", "wall ahead 22,900s PE 186L BUILDING"], "wrong_line": "PALAT? if back past 22,938f"}}


def _at(t, **call):
    return dict(FRAME, mins=[t], call=dict(FRAME["call"], at=t, **call))


def test_changed_is_a_word_move_never_a_pass_or_a_restart():
    jarvis_log.write(DAY, "NIFTY", {"t": "10:40", "word": "TREND ▼"})
    jarvis_log.write(DAY, "NIFTY", {"t": "10:41", "word": "TREND ▼"})
    assert jv.changed(DAY, "NIFTY", "TREND ▼") is False            # a restart: the log's row before says the same word
    assert jv.changed(DAY, "NIFTY", "TREND ▼") is False            # the next pass
    assert jv.changed(DAY, "NIFTY", "PALAT? ▼") is True
    assert jv.changed(DAY, "NIFTY", None) is False
    assert jv.changed("2026-11-03", "SENSEX", "OPENING") is True   # a day's first word


def test_later_runs_on_a_daemon_thread_and_the_newest_call_wins():
    import threading
    store, go = {}, threading.Event()
    slow = REAL_LATER(store, "k", lambda: go.wait(5) and {"lines": ["old"]})
    REAL_LATER(store, "k", lambda: {"lines": ["new"]}).join(5)
    go.set()
    slow.join(5)
    assert store["k"]["lines"] == ["new"] and slow.daemon
    assert store["k"]["day"] == jv._today() and len(store["k"]["at"]) == 5            # stamped when it spoke
    REAL_LATER(store, "x", lambda: 1 / 0).join(5)
    assert {k: store["x"][k] for k in ("lines", "provider", "fell_back", "why")} == \
        {"lines": [], "provider": "engine", "fell_back": True, "why": "ZeroDivisionError"}


def test_preopen_once_on_a_weekday_between_9_and_915(monkeypatch):
    from datetime import datetime
    from chain_live import IST
    jarvis_log.write("2026-10-30", "NIFTY", {"t": "15:29", "word": "TREND ▼", "fut": 23010.5})
    jarvis_log.write("2026-10-30", "NIFTY", {"t": "15:30", "word": "HOLD ▼", "fut": 23011.0})
    jarvis_log.write("2026-10-30", "SENSEX", {"t": "15:30", "word": "TREND ▲"})
    seen, asked, store = {}, [], {}
    monkeypatch.setattr(jv, "later", REAL_LATER)
    monkeypatch.setattr(jv, "brief", lambda levels, rows, notes: seen.update(levels=levels, rows=rows, notes=notes) or {"b": 1})
    card = lambda: asked.append(1) or {"ok": True, "where": {"stop": "23,136f (zone)"}, "walls": None, "lines": None}  # noqa
    notes = lambda: ["note 08:50 RBI 10:00"]                       # noqa: E731
    mon = lambda h, m: datetime(2026, 11, 2, h, m, tzinfo=IST)      # noqa: E731
    assert jv.preopen(store, card, notes, mon(8, 59)) is None and jv.preopen(store, card, notes, mon(9, 15)) is None
    assert jv.preopen(store, card, notes, datetime(2026, 11, 1, 9, 5, tzinfo=IST)) is None and not asked   # a Sunday
    t = jv.preopen(store, card, notes, mon(9, 5))                   # on its own thread: the loop never waits on it
    t.join(5)
    assert t.daemon and store["brief"]["b"] == 1 and jv.preopen(store, card, notes, mon(9, 6)) is None   # once a day
    assert seen["levels"] == {"where": {"stop": "23,136f (zone)"}, "walls": None, "lines": None}
    assert [(r["idx"], r["word"]) for r in seen["rows"]] == [("NIFTY", "HOLD ▼"), ("SENSEX", "TREND ▲")]
    assert seen["notes"] == ["note 08:50 RBI 10:00"] and asked == [1]


@pytest.fixture
def srv(monkeypatch):
    import time
    import server
    monkeypatch.setattr(jv, "later", lambda store, key, fn: REAL_LATER(store, key, fn).join(5))   # the real thread, joined
    for k, v in (("_JVOICE", {}), ("_LAST_LOGGED", {}), ("_JCMD", {})):
        monkeypatch.setattr(server, k, v)
    monkeypatch.setattr(server, "_JARVIS", {"NIFTY": (None, time.time(), FRAME)})
    return server


def test_the_hook_narrates_a_word_change_with_the_frames_why(srv):
    srv._jarvis_log(FRAME)
    v = srv._JVOICE["NIFTY"]
    assert v["lines"] == FRAME["call"]["why"] and v["why"] == "no key"        # the engine's own lines, from call.why
    assert srv._jarvis_card("NIFTY")["voice"] == v
    srv._JVOICE.clear()
    srv._jarvis_log(_at("10:42"))                                   # the same word a minute on: no call
    assert srv._JVOICE == {}
    srv._jarvis_log(_at("10:43", word="PALAT? ▼"))
    assert srv._JVOICE["NIFTY"]["fell_back"] is True
    assert srv._VOICE is not srv._JVOICE                            # the trade ladder's memory is not the card's voice


def test_ask_answers_on_the_card_and_telegram_waits_for_it(srv):
    r = srv._jarvis_cmd("NIFTY", "ask is the floor holding", "page")
    assert r["kind"] == "ask" and r["reply"] == jv.THINKING and r["lines"] == []
    v = srv._JVOICE["NIFTY"]
    assert v["q"] == "is the floor holding" and v["lines"] == FRAME["call"]["why"]
    t = srv._jarvis_cmd("NIFTY", "ask why", "telegram")
    assert t["reply"] == "voice fell back — no key" and t["lines"] == FRAME["call"]["why"]
    srv._JARVIS.clear()
    assert srv._jarvis_cmd("NIFTY", "ask anything", "page")["ok"] is False      # no frame: jarvis_cmd says why, no call


class _Resp:
    def __init__(self, doc):
        self.b = json.dumps(doc, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.b




def _cli():
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import jarvis_cli
    return jarvis_cli


def test_the_terminal_ask_waits_for_a_slow_answer(monkeypatch):
    jarvis_cli = _cli()
    cards = []                                                      # the card's voice, look by look

    def fake(req, timeout=None):
        if req.full_url.endswith("/api/jarvis/cmd"):
            return _Resp({"ok": True, "kind": "ask", "reply": jv.THINKING, "lines": []})
        return _Resp({"ok": True, "voice": cards.pop(0) if len(cards) > 1 else cards[0]})

    monkeypatch.setattr(jarvis_cli.urllib.request, "urlopen", fake)
    s = jarvis_cli.Session("http://127.0.0.1:8765", "NIFTY")
    waits = []
    s.sleep = waits.append
    old = {"lines": ["an older narration"], "fell_back": False, "q": None}
    ans = {"lines": ["A1", "A2"], "provider": "claude", "fell_back": False, "why": None, "q": "is the floor holding"}
    cards[:] = [None, old, old, old, ans]                           # four looks without her answer, the fifth has it
    assert s.handle("ask is the floor holding") == "\n".join([jv.THINKING, "A1", "A2"])
    assert waits == [jarvis_cli.ASK_POLL_S] * 5
    waits.clear()
    cards[:] = [old]                                                # never answers: the wait ends at 2 x the model's call
    assert s.handle("ask is the floor holding").endswith(
        "the voice has not answered in 60 s — `now` shows the card's voice when it does")
    assert sum(waits) >= jarvis_cli.ASK_WAIT_MAX_S and len(waits) == 40
    cards[:] = [dict(ans, fell_back=True, why="no key")]
    assert s.handle("ask is the floor holding").endswith("A2\nvoice fell back — no key")
    import jarvis_cmd
    s.voice = lambda q, asked=None: [q]                             # the question the terminal waits for == the server's q
    for t in ("ask is the floor holding", "ask  is   the floor holding?", "ASK Why now"):
        assert s.handle(t).splitlines()[-1] == jarvis_cmd.parse(t)["text"]


def test_now_renders_the_voice_and_the_days_brief():
    jarvis_cli = _cli()
    base = {"idx": "NIFTY", "day": TODAY, "at": "10:42", "word": "TREND ▼"}
    out = jarvis_cli.render_card(dict(base, voice={"lines": ["TREND ▼ since 09:56 · WITH 4", "wrong past 22,938f"],
                                                    "fell_back": False}, brief={"lines": ["[web] RBI 10:00", "PDH 23,155s"],
                                                                                "at": "09:05"})).splitlines()
    i = out.index("VOICE     TREND ▼ since 09:56")
    assert out[i + 1:i + 3] == ["          WITH 4", "          wrong past 22,938f"]
    i = out.index("BRIEF     at 09:05")
    assert out[i + 1:i + 3] == ["          [web] RBI 10:00", "          PDH 23,155s"]
    out = jarvis_cli.render_card(dict(base, voice={"lines": ["x"], "fell_back": True, "why": "no key"}))
    assert "VOICE     fell back — no key" in out.splitlines() and "BRIEF" not in out
    assert "voice" not in jarvis_cli.render_card(base).split("NOT IN CARD")[-1]      # optional: never named absent


# ---- Phase B fixes: the brief's timeout and line, the card's brief, the restore, Telegram ----

def test_the_brief_has_its_own_longer_timeout_and_says_why_it_fell_back(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_text("k")
    seen = _fake_sdk(monkeypatch, text=WEB)
    jv.brief(LEVELS, [], [])
    assert seen["client"]["timeout"] == jv.BRIEF_TIMEOUT_S == 90
    jv.speak(CARD)
    assert seen["client"]["timeout"] == jv.TIMEOUT_S == 30
    (_tmp / "keys" / "anthropic.txt").unlink()
    monkeypatch.setattr(jv, "_today", lambda: "2026-11-03")       # a fresh day: today's brief is not reused
    assert jv.brief(LEVELS, [], [])["lines"] == ["pre-open brief: could not check — no key"]


def test_the_card_restores_the_days_voice_and_brief_after_a_restart(_tmp):
    jv.on_change(CARD, provider=say(GOOD))
    jv.answer(CARD, "is the floor holding", provider=say("wall ahead 22,900s PE 186L BUILDING"))
    jv.on_change(dict(CARD, idx="SENSEX"))                          # no key: SENSEX's newest is a fallback row
    jv.brief(LEVELS, [], [], provider=say(WEB))
    store = {}                                                      # a restart: memory is empty
    v, b = jv.for_card(store, "NIFTY")
    assert v["lines"] == ["wall ahead 22,900s PE 186L BUILDING"] and v["q"] == "is the floor holding" and v["day"] == TODAY
    assert b == {"lines": WEB.splitlines(), "at": b["at"]} and len(b["at"]) == 5
    assert jv.for_card(store, "SENSEX")[0]["fell_back"] is True and jv.for_card(store, "BANKNIFTY")[0] is None
    store["NIFTY"] = {"lines": ["newer, in memory"], "day": TODAY}
    assert jv.for_card(store, "NIFTY")[0]["lines"] == ["newer, in memory"]           # memory wins after the restore
    assert jv.for_card({}, "NIFTY", day="2026-10-30") == (None, None)               # another day: nothing invented


def test_the_brief_stays_on_the_card_all_day_beside_the_narration(srv, monkeypatch):
    from datetime import datetime
    from chain_live import IST
    monkeypatch.setattr(jv, "brief", lambda levels, rows, notes: {"lines": ["[web] RBI 10:00"], "provider": "injected",
                                                                   "fell_back": False, "why": None})
    jv.preopen(srv._JVOICE, lambda: srv._jarvis_card("NIFTY"), lambda: [], datetime(2026, 11, 2, 9, 5, tzinfo=IST))
    c = srv._jarvis_card("NIFTY")
    assert c["brief"]["lines"] == ["[web] RBI 10:00"] and c["voice"] is None          # the brief is not NIFTY's voice
    srv._jarvis_log(FRAME)                                          # the first change narrates; the brief stays
    c = srv._jarvis_card("NIFTY")
    assert c["voice"]["lines"] == FRAME["call"]["why"] and c["brief"]["lines"] == ["[web] RBI 10:00"]
    sent = {}
    monkeypatch.setattr(jv, "_run", lambda kind, idx, src, *a, **k: sent.update(src=src) or
                        {"lines": ["x"], "provider": "engine", "fell_back": True, "why": "no key"})
    jv.speak(dict(c, why=["w"]))
    assert "brief" not in sent["src"] and "voice" not in sent["src"]   # the web's numbers never feed the narration


def test_telegram_ask_survives_a_broken_card_and_keeps_its_q(srv, monkeypatch):
    def boom(idx):
        raise RuntimeError("card")

    monkeypatch.setattr(srv, "_jarvis_card", boom)
    t = srv._jarvis_cmd("NIFTY", "ask why", "telegram")
    assert t["reply"] == "voice fell back — no card" and t["lines"] == ["could not check — the card failed (RuntimeError)"]
    assert srv._JVOICE["NIFTY"]["q"] == "why"


# ---- Phase B fix 2: (q, asked), the card never failed by the voice, the brief's own time ----

def test_a_repeated_question_waits_for_its_own_answer(monkeypatch):
    jarvis_cli = _cli()
    q = "is the floor holding"
    before = {"lines": ["the 10:40 answer"], "fell_back": False, "q": q, "asked": "10:40:00", "at": "10:40"}
    new = {"lines": ["the 10:42 answer"], "fell_back": False, "q": q, "asked": "10:42:01", "at": "10:42"}
    looks = [before, before, new]                                    # the card holds the same words' older answer first

    def fake(req, timeout=None):
        if req.full_url.endswith("/api/jarvis/cmd"):
            return _Resp({"ok": True, "kind": "ask", "reply": jv.THINKING, "lines": [], "asked": "10:42:01"})
        return _Resp({"ok": True, "voice": looks.pop(0) if len(looks) > 1 else looks[0]})

    monkeypatch.setattr(jarvis_cli.urllib.request, "urlopen", fake)
    s = jarvis_cli.Session("http://127.0.0.1:8765", "NIFTY")
    waits = []
    s.sleep = waits.append
    assert s.handle("ask " + q) == "\n".join([jv.THINKING, "the 10:42 answer"]) and len(waits) == 3


def test_the_terminal_stops_waiting_on_a_card_that_cannot_build(monkeypatch):
    jarvis_cli = _cli()

    def fake(req, timeout=None):
        if req.full_url.endswith("/api/jarvis/cmd"):
            return _Resp({"ok": True, "kind": "ask", "reply": jv.THINKING, "lines": [], "asked": "10:42:01"})
        return _Resp({"ok": False, "why": "could not check — no frame built yet"})

    monkeypatch.setattr(jarvis_cli.urllib.request, "urlopen", fake)
    s = jarvis_cli.Session("http://127.0.0.1:8765", "NIFTY")
    waits = []
    s.sleep = waits.append
    assert s.handle("ask why").endswith("could not check — no frame built yet") and len(waits) == 1


def test_the_voice_block_says_when_it_spoke():
    out = _cli().render_card({"idx": "NIFTY", "word": "TREND ▼", "voice": {"lines": ["TREND ▼ since 09:56 · WITH 4"],
                                                                         "fell_back": False, "at": "10:43"}}).splitlines()
    i = out.index("VOICE     at 10:43")
    assert out[i + 1:i + 3] == ["          TREND ▼ since 09:56", "          WITH 4"]


def test_each_ask_carries_its_asked_time_on_the_reply_and_the_answer(srv, monkeypatch):
    from datetime import datetime
    from chain_live import IST
    monkeypatch.setattr(srv, "_ist", lambda now=None: datetime(2026, 11, 2, 10, 42, 1, tzinfo=IST))
    r = srv._jarvis_cmd("NIFTY", "ask is the floor holding", "page")
    assert r["asked"] == "10:42:01" and srv._JVOICE["NIFTY"]["asked"] == "10:42:01"
    t = srv._jarvis_cmd("NIFTY", "ask why", "telegram")
    assert t["asked"] == "10:42:01" and srv._JVOICE["NIFTY"]["q"] == "why"


def test_a_torn_voice_log_never_fails_the_card(srv, monkeypatch):
    jv.on_change(CARD, provider=say(GOOD))
    with open(jv._path(), "ab") as f:
        f.write(b'\x80\x81 torn {"kind":\n')
    c = srv._jarvis_card("NIFTY")                                    # restored from the good row, the torn one skipped
    assert c["ok"] and c["voice"]["lines"] == [GOOD]

    def boom(store, idx, day=None):
        raise RuntimeError("voice")

    monkeypatch.setattr(jv, "for_card", boom)
    c = srv._jarvis_card("NIFTY")
    assert c["ok"] and c["voice"] is None and c["brief"] is None and c["word"] == FRAME["call"]["word"]


def test_a_brief_re_served_after_a_restart_keeps_the_time_it_was_said(monkeypatch):
    from datetime import datetime
    from chain_live import IST
    jv._write({"at": 0, "t": "09:01:30", "idx": None, "kind": "brief", "provider": "claude", "in_tokens": 1,
               "out_tokens": 1, "lines": ["[web] RBI 10:00"], "fell_back": False, "why": None, "q": None})
    monkeypatch.setattr(jv, "later", REAL_LATER)
    store = {}
    jv.preopen(store, lambda: {"ok": False}, lambda: [], datetime(2026, 11, 2, 9, 10, tzinfo=IST)).join(5)
    assert store["brief"]["lines"] == ["[web] RBI 10:00"] and store["brief"]["at"] == "09:01"
    assert jv.for_card(store, "NIFTY")[1] == {"lines": ["[web] RBI 10:00"], "at": "09:01"}
