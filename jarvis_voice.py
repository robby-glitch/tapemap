"""jarvis_voice.py -- THE VOICE: the model behind one seam, fenced to the card (Jarvis v3 Task 7; plan
docs/superpowers/plans/2026-10-31-jarvis-v3-weekend.md, the CARD contract; why: docs/kahani/review/JARVIS-VISION-2026-10-31.md §5).
  speak(card, question=None, provider=None)   narrate an ACTION-word change (effort low) or answer her question (medium)
  on_change(card) / answer(card, question)    the server hook's two doors (a daemon thread per change; the cmd kind `ask`)
  brief(levels, last_call_rows, notes)        the pre-open brief: one call with web search, <= 6 lines, every web item [web]
  fence(text, card, ...)                      THE FENCE, in code: numbers only from the card (or her question), no %, no
                                              order word, <= 3 lines of <= 140 chars -> None, or the failed check
THE SEAM: `provider` is a callable (system_text, user_text) -> str (tests inject one, reported as "injected"); None -> the
key files decide at call time: keys/anthropic.txt -> Claude (the `anthropic` SDK, imported lazily), else keys/gemini.txt ->
Gemini (urllib), else the engine. A key is read per call, held only in that call's closure, never cached, logged or printed.
The rules engine owns every fact and verdict; the voice only narrates the card. ANY failure -- no key, no SDK, the cap, a
refusal, an error, the fence -- gives the engine's own lines with fell_back true and a why, so the face never goes blank.
`provider` names who was ASKED ("engine" when nobody was): the budget counts every other row in data/jarvis/voice_<day>.jsonl.
Display only. No order path. Counts, never a %."""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime

import confluence_log
from chain_live import IST

DIR = os.path.join("data", "jarvis")
KEYS = "keys"                 # anthropic.txt / gemini.txt / gemini_model.txt / cap.json (git-ignored; keys/README.md)
CAP = 80                      # model calls a day when keys/cap.json is absent [I: the plan's number; ~60 changes + asks a day]
MODEL = "claude-opus-5-5"
GEMINI_MODEL = "gemini-flash-latest"
CLAUDE_URL = "https://api.anthropic.com"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_TOKENS = 600              # [I] the plan's number; thinking counts against it -- a cut-off shows as why "stopped: max_tokens"
TIMEOUT_S = 30                # [I] one call; `ask` waits on it, a change runs in its own thread
MAX_LINES, MAX_CHARS, BRIEF_LINES = 3, 140, 6
WEB_SEARCH = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}
NUM = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?|\d+(?:,\d+)*(?:\.\d+)?")     # a time HH:MM[:SS], or digits with , and .
RATE = re.compile(r"%|\bper\s?cent\b|\bprobabilit|\bodds\b|\b(?:hit|win)\s+rate", re.I)
ORDER = re.compile(r"\b(buy(?:s|ing)?|sell(?:s|ing)?|lots?|orders?|plac(?:e|es|ed|ing)|square\s+off|short|long|exit\s+now)\b",
                   re.I)
_LOCK = threading.Lock()

PREFIX = """You are the voice of Jarvis, a read-only market reader for one Indian index-options trader (NIFTY, SENSEX).
The rules engine owns every fact and every verdict. You narrate its card. You never change its word, its count or its lines.

Rules:
- At most 3 lines, each at most 140 characters, plain English. No greeting, no preamble, no markdown.
- Quote only numbers that appear in the card JSON or in her question, as the card writes them. Never compute, round or invent one.
- Every price level keeps its s (spot) or f (futures) suffix exactly as the card writes it.
- Never write %, a probability, odds, a hit rate or a win rate. Agreement is a count: WITH 4 · AGAINST 1.
- Never write buy, sell, lots, order, place, square off, short, long or exit now, except inside an exact quote of one
  " · " clause of the card's expression.buyer or expression.seller line. You read; you never place or suggest an order.
- A missing value is never a zero: say "could not check" and why, as the card says it.
- Writers first: writers, then futures OI, then flow and speed, then cross-index, then her setup.

The state words, verbatim: WALL, PUSH, TESTED ×n · broke n, HELD, DEFENDED, BROKEN, TRAPPED, BREAK FAILED, FUEL, FUEL SPENT,
NEW FLOOR, NEW CEILING, CONTINUES, PINNED, REVERSAL, ROTATE, CONTINUE, UNCLEAR, NO TRADE: quiet / can't see / shock.
The leg's words, verbatim: TREND, HOLD, WATCH, PALAT?, PALAT, ROTATION, OPENING, NO LEG, CAN'T SEE.

The fence: code reads your reply after you write it. A number not in the card, a %, an order word, a fourth line or a line
over 140 characters throws the whole reply away and the engine's own lines are shown instead."""

CHANGE_TASK = ("The ACTION word just changed to the card's `word` (since the card's `since`). In at most 3 lines: what it "
               "reads now, writers first, and the card's wrong-line.")
BRIEF_TASK = ("The pre-open brief, before 09:15 IST. Search the web for: today's scheduled events for Indian markets, the "
              "global cues overnight, and the NIFTY / SENSEX expiry. At most 6 lines (this replaces the 3-line rule). Start "
              "every line taken from the web with [web]; numbers from the web may appear only on [web] lines; any other line "
              "quotes only the CONTEXT above.")
BRIEF_FALL = "pre-open brief: could not check — the voice fell back"


class _Fallback(Exception):
    """A provider's named reason to fall back (refused, cut off)."""


def _now():
    return datetime.now(IST)


def _today():
    return _now().strftime("%Y-%m-%d")


def _path():
    return os.path.join(DIR, f"voice_{_today()}.jsonl")


def _rows():
    return list(confluence_log._rows(_path()))


def _calls_today():
    """Today's model calls: every logged row whose provider was asked (not the engine)."""
    return sum(1 for r in _rows() if r.get("provider") not in (None, "engine"))


def _write(row):
    with _LOCK:
        os.makedirs(DIR, exist_ok=True)
        with open(_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _read(name):
    """A file under KEYS, stripped, or None. Read at call time; the caller never keeps it past the call."""
    try:
        with open(os.path.join(KEYS, name), encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


def _cap():
    try:
        return int(json.loads(_read("cap.json") or "")["calls_per_day"])
    except (ValueError, KeyError, TypeError):
        return CAP


def engine_lines(card):
    """The engine's own lines: the card's `why` (first three) when it carries one -- THE CARD contract has no `why` key, so a
    contract card gives [word, leg, wrong_line] with the absent ones dropped. Never blank."""
    c = card or {}
    w = c.get("why")
    w = [w] if isinstance(w, str) else list(w or [])
    out = w[:3] or [x for x in (c.get("word"), c.get("leg"), c.get("wrong_line")) if x]
    return out or ["could not check — the card has no word yet"]


def _norm(t):
    if ":" in t:                                     # a time: one token, the hour zero-padded
        h, rest = t.split(":", 1)
        return f"{int(h):02d}:{rest}"
    t = t.replace(",", "")                           # Indian 23,05,100 and Western 2,305,100 alike
    if "." in t:
        t = t.rstrip("0").rstrip(".")                # 186.0 == 186, 13.40 == 13.4
    return t.lstrip("0") or "0"


def _tokens(text):
    return [_norm(t) for t in NUM.findall(text)]


def _lines(text):
    return [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]


def _quotable(src):
    """The expression lines and each of their ` · ` clauses: the only text an order word may stand in, quoted verbatim."""
    ex = src.get("expression") if isinstance(src, dict) else None
    out = set()
    for k in ("buyer", "seller"):
        s = ex.get(k) if isinstance(ex, dict) else None
        if isinstance(s, str) and s.strip():
            out |= {s.strip(), *(c.strip() for c in s.split(" · ") if c.strip())}
    return sorted(out, key=len, reverse=True)


def fence(text, card, question=None, max_lines=MAX_LINES, web=False):
    """THE FENCE (code, never prompt) -> None when the reply may be shown, else the failed check. The allowed numbers are the
    card's JSON (its old `voice` left out) plus her own question's; with `web` (the brief) a line starting [web] may carry the
    web's numbers. ponytail: signs are not compared (−200 vs +200 passes); compare signed tokens if the model ever flips one."""
    lines = _lines(text)
    if not lines:
        return "fence: empty reply"
    if len(lines) > max_lines:
        return f"fence: {len(lines)} lines (at most {max_lines})"
    src = {k: v for k, v in card.items() if k != "voice"} if isinstance(card, dict) else card
    allowed = set(_tokens(json.dumps(src, ensure_ascii=False, default=str) + " " + str(question or "")))
    allowed |= {t[:5] for t in allowed if t.count(":") == 2}        # 10:42:51 in the card holds 10:42
    quotable = _quotable(src)
    for ln in lines:
        if len(ln) > MAX_CHARS:
            return f"fence: a line of {len(ln)} chars (at most {MAX_CHARS})"
        m = RATE.search(ln)
        if m:
            return f"fence: no % or rate ({m.group(0)})"
        rest = ln
        for q in quotable:
            rest = rest.replace(q, " ")
        m = ORDER.search(rest)
        if m:
            return f"fence: order word '{m.group(0).lower()}'"
        if web and ln.startswith("[web]"):
            continue
        for raw, t in zip(NUM.findall(ln), _tokens(ln)):
            if t not in allowed:
                return f"fence: number {raw} not in the card"
    return None


def _claude(anthropic, key, system, user, effort, web):
    kw = {"model": MODEL, "max_tokens": MAX_TOKENS, "output_config": {"effort": effort},
          "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
          "messages": [{"role": "user", "content": user}]}
    if web:
        kw["tools"] = [WEB_SEARCH]
    # base_url pinned: the SDK otherwise sends her key to $ANTHROPIC_BASE_URL when a shell has it set (Claude Code's does)
    r = anthropic.Anthropic(api_key=key, base_url=CLAUDE_URL, timeout=TIMEOUT_S, max_retries=1).messages.create(**kw)
    if r.stop_reason == "refusal":
        raise _Fallback("refused")
    if r.stop_reason not in ("end_turn", "stop_sequence"):
        raise _Fallback(f"stopped: {r.stop_reason}")
    u = r.usage
    tin = sum(getattr(u, k, None) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return "".join(b.text for b in r.content if b.type == "text"), tin, getattr(u, "output_tokens", None)


def _gemini(key, system, user, web):
    """algo_ai's ai_sentiment._call_gemini shape, on urllib; the search tool for the brief only."""
    model = _read("gemini_model.txt") or GEMINI_MODEL
    body = {"contents": [{"parts": [{"text": system + "\n\n" + user}]}]}
    if web:
        body["tools"] = [{"google_search": {}}]
    req = urllib.request.Request(f"{GEMINI_URL}/{urllib.parse.quote(model)}:generateContent", data=json.dumps(body).encode(),
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        d = json.loads(r.read())
    um = d.get("usageMetadata") or {}
    text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
    return text, um.get("promptTokenCount"), um.get("candidatesTokenCount")


def _pick(effort, web):
    """-> (provider, fn(system, user)) or ("engine", why). The key lives in the closure for this one call."""
    key = _read("anthropic.txt")
    if key:
        try:
            import anthropic                         # lazy: the server runs without the SDK
        except ImportError:
            return "engine", "anthropic SDK not installed"
        return "claude", lambda system, user: _claude(anthropic, key, system, user, effort, web)
    key = _read("gemini.txt")
    if key:
        return "gemini", lambda system, user: _gemini(key, system, user, web)
    return "engine", "no key"


def _run(kind, idx, src, q, user, fall, effort, provider, max_lines, web=False, blocked=None):
    name, fn = ("engine", blocked) if blocked else ("injected", provider) if provider else _pick(effort, web)
    tin = tout = None
    if name == "engine":
        why = fn
    elif _calls_today() >= _cap():                   # ponytail: two threads can pass this together; at most one call per index over
        name, why = "engine", "cap reached"
    else:
        try:
            out = fn(PREFIX, user)
            text, tin, tout = out if isinstance(out, tuple) else (out, None, None)
            why = fence(text, src, q, max_lines, web)
        except _Fallback as e:
            why = str(e)
        except Exception as e:                       # noqa: BLE001 -- any error is a fallback; its class names it, never its text
            code = getattr(e, "status_code", None) or getattr(e, "code", None)
            why = f"{name} call failed — {type(e).__name__}" + (f" {code}" if isinstance(code, int) else "")
    lines = fall if why else _lines(text)
    n = _now()
    _write({"at": int(time.time()), "t": n.strftime("%H:%M:%S"), "idx": idx, "kind": kind, "provider": name,
            "in_tokens": tin, "out_tokens": tout, "lines": lines, "fell_back": bool(why), "why": why, "q": q})
    return {"lines": lines, "provider": name, "fell_back": bool(why), "why": why}


def speak(card, question=None, provider=None):
    """The voice over one card -> {"lines", "provider", "fell_back", "why"}; one log row. Her notes ride in the card's
    health.notes (the server builds it with jarvis_cmd's notes); the card's old `voice` is never sent or quoted."""
    c = {k: v for k, v in (card or {}).items() if k != "voice"}
    task = f"HER QUESTION: {question}" if question else CHANGE_TASK
    user = "CARD " + json.dumps(c, ensure_ascii=False, default=str) + "\n\n" + task
    return _run("ask" if question else "change", c.get("idx"), c, question, user, engine_lines(c),
                "medium" if question else "low", provider, MAX_LINES, blocked=None if c.get("ok") else "no card")


def on_change(card, provider=None):
    """The server hook when the logged ACTION word changes (run it in a daemon thread)."""
    return speak(card, provider=provider)


def answer(card, question, provider=None):
    """The cmd kind `ask`."""
    return speak(card, question, provider)


def brief(levels, last_call_rows, notes, provider=None):
    """THE PRE-OPEN BRIEF: one call with web search, <= 6 lines, every web item [web]; once a day (a brief already said
    today is returned from the log, no call). The fence holds every non-[web] line to the levels, rows and notes given."""
    said = [r for r in _rows() if r.get("kind") == "brief" and not r.get("fell_back")]
    if said:
        return {"lines": said[-1]["lines"], "provider": said[-1]["provider"], "fell_back": False, "why": None}
    src = {"levels": levels, "last_calls": last_call_rows, "notes": notes}
    user = "CONTEXT " + json.dumps(src, ensure_ascii=False, default=str) + "\n\n" + BRIEF_TASK
    return _run("brief", None, src, None, user, [BRIEF_FALL], "medium", provider, BRIEF_LINES, web=True)
