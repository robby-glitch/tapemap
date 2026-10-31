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


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(jv, "DIR", str(tmp_path / "jarvis"))
    monkeypatch.setattr(jv, "KEYS", str(tmp_path / "keys"))
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


def test_the_budget_cap(_tmp):
    (_tmp / "keys" / "cap.json").write_text('{"calls_per_day": 2}')
    calls = []

    def count(system, user):
        calls.append(1)
        return GOOD

    outs = [jv.speak(CARD, provider=count) for _ in range(3)]
    assert len(calls) == 2 and outs[2]["why"] == "cap reached" and outs[2]["provider"] == "engine"
    jv.speak(CARD)                                                  # no-key rows are not calls
    assert jv._calls_today() == 2


def test_the_cap_defaults_to_80(_tmp):
    assert jv._cap() == 80
    (_tmp / "keys" / "cap.json").write_text("not json")
    assert jv._cap() == 80


# ---- the providers (fakes; no network) ----

class _Block:
    def __init__(self, type, text=""):
        self.type, self.text = type, text


def _fake_sdk(monkeypatch, text=GOOD, stop="end_turn"):
    seen = {}

    class Messages:
        def create(self, **kw):
            seen["kw"] = kw
            usage = types.SimpleNamespace(input_tokens=900, cache_read_input_tokens=4000, cache_creation_input_tokens=None,
                                          output_tokens=120)
            texts = [text] if isinstance(text, str) else text
            return types.SimpleNamespace(stop_reason=stop, content=[_Block("thinking")] + [_Block("text", t) for t in texts],
                                         usage=usage)

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


def test_a_utf16_key_file_is_a_named_fallback_never_a_raise(_tmp, monkeypatch):
    (_tmp / "keys" / "anthropic.txt").write_bytes("sk-ant-SECRET\r\n".encode("utf-16"))   # PowerShell 5.1's `echo k > f`
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


def test_an_unwritable_log_still_returns_the_lines(_tmp, monkeypatch):
    (_tmp / "a_file").write_text("x")
    monkeypatch.setattr(jv, "DIR", str(_tmp / "a_file"))          # makedirs on a file -> OSError
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
