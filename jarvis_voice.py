"""jarvis_voice.py -- THE VOICE: the model behind one seam, fenced to the card (Jarvis v3 Task 7; plan
docs/superpowers/plans/2026-10-31-jarvis-v3-weekend.md, the CARD contract; why: docs/kahani/review/JARVIS-VISION-2026-10-31.md §5).
  speak(card, question=None, provider=None)   narrate an ACTION-word change (effort low) or answer her question (medium)
  on_change(card) / answer(card, question)    the server hook's two doors (a daemon thread per change; the cmd kind `ask`)
  brief(levels, last_call_rows, notes)        the pre-open brief: one call with web search, <= 6 lines, every web item [web]
  fence(text, card, ...)                      THE FENCE, in code: numbers only from the card (or her question), no %, no
                                              order word, <= 3 lines of <= 140 chars -> None, or the failed check
  changed / later / preopen                   the server's hook: the ACTION-word test, one daemon thread per call, and the
                                              brief's door on the Jarvis loop (weekday 09:00–09:15, once a day)
THE SEAM: `provider` is a callable (system_text, user_text) -> str (tests inject one, reported as "injected"); None -> the
key files decide at call time: keys/anthropic.txt -> Claude (the `anthropic` SDK, imported lazily), else keys/gemini.txt ->
Gemini (urllib), else the engine. A key is read per call, held only in that call's closure, never cached, logged or printed.
The rules engine owns every fact and verdict; the voice only narrates the card. ANY failure -- no key, no SDK, the cap, a
refusal, an error, the fence -- gives the engine's own lines with fell_back true and a why, so the face never goes blank.
`provider` names who was ASKED ("engine" when nobody was): the budget counts every other row in data/jarvis/voice_<day>.jsonl.
Display only. No order path. Counts, never a %."""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime

import jarvis_log
from chain_live import IST

DIR = os.path.join("data", "jarvis")
KEYS = "keys"                 # anthropic.txt / gemini.txt / gemini_model.txt / cap.json (git-ignored; keys/README.md)
CAP = 80                      # model calls a day when keys/cap.json is absent [I: the plan's number; ~60 changes + asks a day]
MODEL = "claude-opus-5-5"
GEMINI_MODEL = "gemini-flash-latest"
CLAUDE_URL = "https://api.anthropic.com"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_TOKENS = 4000             # [I] adaptive thinking counts against max_tokens on Opus 5.5; 600 cut the brief off
TIMEOUT_S = 60                # [I] one call, non-streaming: a 4000-token answer with thinking needs the room; every call runs
                              #     on its own daemon thread (later), none blocks a pass or a request
BRIEF_TIMEOUT_S = 90          # [I] the brief's call: up to 3 web searches before it writes
ASK_RESERVE = 10              # [I] the day's last 10 calls are hers: narrations stop at cap - 10, an `ask` may use them all
MAX_LINES, MAX_CHARS, BRIEF_LINES = 3, 140, 6
WEB_SEARCH = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}
THINKING = "thinking — the card's voice fills in a moment"      # the cmd reply to `ask` while the voice answers
NUM = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?|\d+(?:,\d+)*(?:\.\d+)?")     # a time HH:MM[:SS], or digits with , and .
RATE = re.compile(r"[%％٪]|\bper\s?cent\w*|\bprobab\w*|\bodds\b|\bchances?\b|\bconfiden\w*|\blikelihood\b|"
                  r"\b(?:hit|win)\s+rate", re.I)                    # percent, percentage (point), the fullwidth and Arabic signs
ORDER = re.compile(r"\b(buy(?:s|ing)?|sell(?:s|ing)?|lots?|orders?|plac(?:e|es|ed|ing)|square[\s-]*off|squar(?:e|ing)|"
                   r"short(?:ing|ed)?|long|exit\s+now)\b", re.I)     # `shorts` (fresh shorts, an OI noun) stays out
COUNT = re.compile(r"\b(with|against)\s+(\d+)\b(?![,.]\d)", re.I)   # WITH 4 · AGAINST 1, any case; never a level (22,900s)
log = logging.getLogger("jarvis_voice")
_LOCK = threading.Lock()
_WORD = {}                    # idx -> (day, the ACTION word the call log said last): changed()'s memory
_PREOPEN = set()              # days the pre-open brief was tried by this process (brief() keeps the once across a restart)

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
The leg's words, verbatim: TREND, HOLD, WATCH, PALAT?, PALAT, ROTATION, OPENING, NO LEG, CAN'T SEE, RANGE (the
lean flipped inside the writers' box: no side).

The fence: code reads your reply after you write it. A number not in the card, a level without the s / f the card gives it,
a sign the card does not write, a %, an order word, a fourth line or a line over 140 characters throws the whole reply away
and the engine's own lines are shown instead."""

CHANGE_TASK = ("The ACTION word just changed to the card's `word` (since the card's `since`). In at most 3 lines: what it "
               "reads now, writers first, and the card's wrong-line.")
BRIEF_TASK = ("The pre-open brief, before 09:15 IST. Search the web for: today's scheduled events for Indian markets, the "
              "global cues overnight, and the NIFTY / SENSEX expiry. At most 6 lines (this replaces the 3-line rule). Start "
              "every line taken from the web with [web]; numbers from the web may appear only on [web] lines; any other line "
              "quotes only the CONTEXT above.")


class _Fallback(Exception):
    """A named reason to fall back, used verbatim as the why (no key, cap reached, refused, max_tokens, key file unreadable)."""


def _now():
    return datetime.now(IST)


def _today():
    return _now().strftime("%Y-%m-%d")


def _path(day=None):
    return os.path.join(DIR, f"voice_{day or _today()}.jsonl")


def _rows(day=None):
    """The day's voice rows in order; [] when there is no file. Read leniently: a torn character or line costs itself,
    never the card, the brief or the day."""
    try:
        with open(_path(day), encoding="utf-8", errors="replace") as f:
            out = []
            for ln in f:
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(r, dict):
                    out.append(r)
            return out
    except OSError:
        return []


def _calls_today():
    """Today's model calls: every logged row whose provider was asked (not the engine). FAILS CLOSED: the log is opened for
    append (made when absent) before any call, so a log that cannot open or read is "log cannot open" and no call is made --
    the cap can never go blind."""
    try:
        os.makedirs(DIR, exist_ok=True)
        with open(_path(), "a+", encoding="utf-8", errors="replace") as f:     # one torn character never stops the day
            f.seek(0)
            n = 0
            for ln in f:
                try:
                    n += json.loads(ln).get("provider") not in (None, "engine")
                except (ValueError, AttributeError):       # a torn or foreign line costs itself
                    continue
            return n
    except (OSError, UnicodeError):
        raise _Fallback("log cannot open") from None


def _write(row):
    """Append one row -> None, or "log unwritable" (fail-soft: the lines still reach her)."""
    try:
        with _LOCK:
            os.makedirs(DIR, exist_ok=True)
            with open(_path(), "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    except OSError:
        return "log unwritable"
    return None


def _read(name):
    """A file under KEYS, stripped, or None when absent. Read at call time; the caller never keeps it past the call. UTF-8
    (Notepad's BOM or not) or UTF-16 by its BOM (PowerShell 5.1's `echo key > keys\\anthropic.txt`); anything else raises
    _Fallback("key file unreadable") -- never the bytes, which a UnicodeDecodeError's repr would carry."""
    p = os.path.join(KEYS, name)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "rb") as f:
            b = f.read()
        return b.decode("utf-16" if b[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig").strip() or None
    except (OSError, UnicodeError):
        raise _Fallback("key file unreadable") from None


def _cap():
    try:
        return int(json.loads(_read("cap.json") or "")["calls_per_day"])
    except (ValueError, KeyError, TypeError, _Fallback):
        return CAP


def engine_lines(card):
    """The engine's own lines: the card's `why` (first three) when it carries one -- THE CARD contract has no `why` key, so a
    contract card gives [word, leg, wrong_line] with the absent ones dropped. Never blank, never raises."""
    c = card if isinstance(card, dict) else {}
    w = c.get("why")
    w = [w] if isinstance(w, str) else list(w) if isinstance(w, (list, tuple)) else []
    out = [str(x) for x in w if x][:3] or [str(x) for x in (c.get("word"), c.get("leg"), c.get("wrong_line")) if x]
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


def _marks(text):
    """Each non-time number of `text` -> (sign, token, suffix). sign: "+" / "−" when one stands right before it (a hyphen
    after a letter or digit is a dash: 2026-11-02, 22,900s-23,000s); suffix: the letters glued right after it, lower-cased
    -- "s" / "f" for a level (S / F are the same suffix), a unit otherwise (186L -> "l", 2.5σ, 23000CE -> "ce") -- or ""
    when bare."""
    out = []
    for m in NUM.finditer(text):
        if ":" in m.group(0):
            continue
        a, b = m.start(), m.end()
        pre, pre2 = text[a - 1] if a else "", text[a - 2] if a > 1 else ""
        sign = "" if pre2.isalnum() else {"+": "+", "-": "−", "−": "−"}.get(pre, "")
        u = re.match(r"[^\W\d_]+", text[b:])
        out.append((sign, _norm(m.group(0)), u.group(0).lower() if u else ""))
    return out


def _leaves(x, strs, nums):
    """The card's text (every string) and its raw numbers apart: a strike held as a number is not the card WRITING it bare."""
    if isinstance(x, str):
        strs.append(x)
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        nums.append(x)
    elif isinstance(x, dict):
        for v in x.values():
            _leaves(v, strs, nums)
    elif isinstance(x, (list, tuple)):
        for v in x:
            _leaves(v, strs, nums)


def _is_level(t):
    return 4 <= len(t.split(".")[0]) <= 6          # 1,000 to 9,99,999: a NIFTY / SENSEX / BANKNIFTY price


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
    web's numbers. I5: a level (4-6 digits) keeps the s / f the card's text gives it, a bare level passes only where the
    card's text (or her question) has it bare, and a signed number needs that sign in the card (its text, or a raw negative)."""
    lines = _lines(text)
    if not lines:
        return "fence: empty reply"
    if len(lines) > max_lines:
        return f"fence: {len(lines)} lines (at most {max_lines})"
    src = {k: v for k, v in card.items() if k != "voice"} if isinstance(card, dict) else card
    allowed = set(_tokens(json.dumps(src, ensure_ascii=False, default=str) + " " + str(question or "")))
    allowed |= {t[:5] for t in allowed if t.count(":") == 2}        # 10:42:51 in the card holds 10:42
    quotable = _quotable(src)
    cnt = src.get("count") if isinstance(src, dict) else None
    strs, nums = [], []
    _leaves(src, strs, nums)
    marks = [mk for s in strs + [str(question or "")] for mk in _marks(s)]
    pairs, bare = {(t, f) for _, t, f in marks if f}, {t for _, t, f in marks if f == ""}
    signed = {(g, t) for g, t, _ in marks if g} | {("−", _norm(str(-v))) for v in nums if v < 0}
    # each why NAMES the check and never echoes what it kept out: the why lands on the card's voice and in the log
    for ln in lines:
        if len(ln) > MAX_CHARS:
            return f"fence: a line of {len(ln)} chars (at most {MAX_CHARS})"
        if RATE.search(ln):
            return "fence: rate sign"
        rest = ln
        for q in quotable:
            rest = rest.replace(q, " ")
        if ORDER.search(rest):
            return "fence: order word"
        if web and ln.startswith("[web]"):                          # the web's own item: the card's count and numbers do not bind it
            continue
        for k, n in COUNT.findall(ln):                              # WITH 1 · AGAINST 4 uses card numbers, swapped
            if not isinstance(cnt, dict) or str(cnt.get(k.lower())) != n:
                return "fence: count mismatch"
        if any(t not in allowed for t in _tokens(ln)):
            return "fence: number not in the card"
        for g, t, f in _marks(ln):
            if g and (g, t) not in signed:
                return "fence: a sign not in the card"
            if _is_level(t) and f and (t, f) not in pairs:
                return ("fence: a level's s / f not as the card writes it" if f in ("s", "f") else
                        "fence: a level's unit not as the card writes it")
            if _is_level(t) and f == "" and t not in bare:
                return "fence: a level without s or f"
    return None


def _claude(anthropic, key, system, user, effort, web):
    kw = {"model": MODEL, "max_tokens": MAX_TOKENS, "output_config": {"effort": effort},
          "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
          "messages": [{"role": "user", "content": user}]}
    if web:
        kw["tools"] = [WEB_SEARCH]
    # base_url pinned: the SDK otherwise sends her key to $ANTHROPIC_BASE_URL when a shell has it set (Claude Code's does)
    with anthropic.Anthropic(api_key=key, base_url=CLAUDE_URL, timeout=BRIEF_TIMEOUT_S if web else TIMEOUT_S,
                             max_retries=1) as client:
        r = client.messages.create(**kw)
    if r.stop_reason == "refusal":
        raise _Fallback("refused")
    if r.stop_reason not in ("end_turn", "stop_sequence"):
        raise _Fallback(str(r.stop_reason))                   # max_tokens (cut off), pause_turn (web search unfinished)
    u = r.usage
    tin = sum(getattr(u, k, None) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    blocks = list(r.content)
    last = max((i for i, b in enumerate(blocks) if str(b.type).endswith("_tool_result")), default=-1)
    # the answer is what follows the last search result: "let me search…" before it is not a line for her
    return _join(b.text for b in blocks[last + 1:] if b.type == "text"), tin, getattr(u, "output_tokens", None)


def _join(parts):
    """Text blocks -> one text. Joined with "" because web search splits ONE cited sentence into several blocks; a [web]
    item a block starts without a line break before it still gets its own line."""
    return re.sub(r"(?<!\n)\[web\]", "\n[web]", "".join(parts)).lstrip("\n")


def _gemini(key, system, user, web):
    """algo_ai's ai_sentiment._call_gemini shape, on urllib; the search tool for the brief only."""
    model = _read("gemini_model.txt") or GEMINI_MODEL
    body = {"contents": [{"parts": [{"text": system + "\n\n" + user}]}]}
    if web:
        body["tools"] = [{"google_search": {}}]
    req = urllib.request.Request(f"{GEMINI_URL}/{urllib.parse.quote(model)}:generateContent", data=json.dumps(body).encode(),
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=BRIEF_TIMEOUT_S if web else TIMEOUT_S) as r:
        d = json.loads(r.read())
    um = d.get("usageMetadata") or {}
    text = _join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
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


def _why(e, name=None):
    """An exception -> its class name (and HTTP status), NEVER its text: a message or repr can carry the key or its bytes."""
    code = getattr(e, "status_code", None) or getattr(e, "code", None)
    cls = type(e).__name__ + (f" {code}" if isinstance(code, int) else "")
    return f"{name} call failed — {cls}" if name else cls


def _run(kind, idx, src, q, user, fall, effort, provider, max_lines, web=False, blocked=None):
    """Pick, cap, call, fence, log -> the result dict. Every failure on the way (the key file, the pick, the cap read, the
    call, the fence) is a why inside the one try; nothing raises out of here."""
    name, tin, tout, text = "engine", None, None, ""
    try:
        if blocked:
            raise _Fallback(blocked)
        who, fn = ("injected", provider) if provider else _pick(effort, web)
        if who == "engine":
            raise _Fallback(fn)
        if _calls_today() >= _cap() - (0 if kind == "ask" else ASK_RESERVE):   # ponytail: two threads can pass together
            raise _Fallback("cap reached" if kind == "ask" else f"cap reached ({ASK_RESERVE} kept for her asks)")
        name = who                                   # from here on the provider was asked: the row counts against the cap
        out = fn(PREFIX, user)
        text, tin, tout = out if isinstance(out, tuple) else (out, None, None)
        why = fence(text, src, q, max_lines, web)
    except _Fallback as e:
        why = str(e)
    except Exception as e:                           # noqa: BLE001 -- any error is a fallback; its class names it, never its text
        why = _why(e, None if name == "engine" else name)
    lines = (fall(why) if callable(fall) else fall) if why else _lines(text)
    res = {"lines": lines, "provider": name, "fell_back": bool(why), "why": why}
    bad = _write({"at": int(time.time()), "t": _now().strftime("%H:%M:%S"), "idx": idx, "kind": kind, "provider": name,
                  "in_tokens": tin, "out_tokens": tout, "lines": lines, "fell_back": bool(why), "why": why, "q": q})
    if bad:
        res["why"] = f"{why} · {bad}" if why else bad
    return res


def _guard(card, e):
    """The last door: an error outside _run still answers with the engine's lines."""
    return {"lines": engine_lines(card), "provider": "engine", "fell_back": True, "why": _why(e)}


def speak(card, question=None, provider=None):
    """The voice over one card -> {"lines", "provider", "fell_back", "why"}; one log row; NEVER raises. Her notes ride in the
    card's health.notes (the server builds it with jarvis_cmd's notes); the card's old `voice` and its `brief` (the web's
    numbers) are never sent or quoted."""
    try:
        c = {k: v for k, v in card.items() if k not in ("voice", "brief")} if isinstance(card, dict) else {}
        task = f"HER QUESTION: {question}" if question else CHANGE_TASK
        user = "CARD " + json.dumps(c, ensure_ascii=False, default=str) + "\n\n" + task
        return _run("ask" if question else "change", c.get("idx"), c, question, user, engine_lines(c),
                    "medium" if question else "low", provider, MAX_LINES, blocked=None if c.get("ok") else "no card")
    except Exception as e:                           # noqa: BLE001
        return _guard(card, e)


def on_change(card, provider=None):
    """The server hook when the logged ACTION word changes (run it in a daemon thread)."""
    return speak(card, provider=provider)


def answer(card, question, provider=None):
    """The cmd kind `ask`."""
    return speak(card, question, provider)


def brief(levels, last_call_rows, notes, provider=None):
    """THE PRE-OPEN BRIEF: one call with web search, <= 6 lines, every web item [web]; once a day (a brief already said
    today is returned from the log, no call). The fence holds every non-[web] line to the levels, rows and notes given.
    NEVER raises."""
    try:
        said = [r for r in _rows() if r.get("kind") == "brief" and not r.get("fell_back")]
        if said:
            return {"lines": said[-1]["lines"], "provider": said[-1]["provider"], "fell_back": False, "why": None,
                    "at": str(said[-1].get("t") or "")[:5] or None}      # re-served: the time it was SAID
        src = {"levels": levels, "last_calls": last_call_rows, "notes": notes}
        user = "CONTEXT " + json.dumps(src, ensure_ascii=False, default=str) + "\n\n" + BRIEF_TASK
        return _run("brief", None, src, None, user, _brief_fall, "medium", provider, BRIEF_LINES, web=True)
    except Exception as e:                           # noqa: BLE001
        return {"lines": _brief_fall(_why(e)), "provider": "engine", "fell_back": True, "why": _why(e)}


def _brief_fall(why):
    return [f"pre-open brief: could not check — {why}"]


# ---- the server's hook (server.py: _jarvis_log, _jarvis_cmd, _jarvis_loop) ----------------------------------------------

def changed(day, idx, word):
    """The hook's test, once per new call-log row: True when idx's ACTION word moved (one call per change, never per pass).
    A day's first look compares with the log's row before this one (anytime-start: a restart is not a change; the day's
    first word is)."""
    last = _WORD.get(idx)
    if last and last[0] == day:
        old = last[1]
    else:
        rows = jarvis_log.read(day, idx)
        old = rows[-2].get("word") if len(rows) > 1 else None
    _WORD[idx] = (day, word)
    return bool(word) and word != old


_SEQ = {}                     # store key -> the newest call started: an older answer never overwrites a newer one


def later(store, key, fn):
    """fn() on a daemon thread, its result into store[key]: no voice call blocks a pass or a request. fn is speak / answer /
    on_change / preopen, which never raise; a crash anyway is logged and stored as the engine's fallback. -> the thread."""
    with _LOCK:
        mine = _SEQ[key] = _SEQ.get(key, 0) + 1

    def run():
        try:
            res = fn()
        except Exception as e:                       # noqa: BLE001
            log.exception("jarvis voice")
            res = {"lines": [], "provider": "engine", "fell_back": True, "why": _why(e)}
        n = _now()
        with _LOCK:
            if isinstance(res, dict) and _SEQ.get(key) == mine:
                x = {"at": n.strftime("%H:%M")}        # when it spoke, unless the result knows better (a brief
                x.update(res)                            # re-served after a restart keeps the time it was said)
                x["day"] = n.strftime("%Y-%m-%d")
                store[key] = x

    t = threading.Thread(target=run, daemon=True, name="jarvis-voice")
    t.start()
    return t


def _last_calls(day):
    """The newest call log before `day`: its final row per index (word, leg, wrong-line, prices); [] when there is none."""
    try:
        days = sorted(f[5:15] for f in os.listdir(jarvis_log.DIR) if f.startswith("call_") and f[5:15] < day)
    except OSError:
        return []
    last = {}
    for r in jarvis_log.read(days[-1]) if days else ():
        last[r.get("idx")] = {k: r.get(k) for k in ("day", "idx", "t", "word", "state", "fut", "spot", "leg", "wrong_line")}
    return list(last.values())


def preopen(store, card_fn, notes_fn, now=None):
    """THE PRE-OPEN BRIEF's door for the server's Jarvis loop: the first tick of a weekday's 09:00–09:15 IST, once a day per
    process, starts brief() on its own thread (later, store["brief"]; its own BRIEF_TIMEOUT_S) over the NIFTY card's levels
    (where / walls / lines, when it has them), the last call log's final row per index and her notes -> the thread; None
    on every other tick. The card and notes are fetched on that thread, never on the loop's."""
    n = now or _now()
    day = n.strftime("%Y-%m-%d")
    if n.weekday() >= 5 or not "09:00" <= n.strftime("%H:%M") < "09:15" or day in _PREOPEN:
        return None
    _PREOPEN.add(day)

    def run():
        try:
            c = card_fn()
            levels = {k: c.get(k) for k in ("where", "walls", "lines")} if isinstance(c, dict) and c.get("ok") else None
            return brief(levels, _last_calls(day), notes_fn())
        except Exception as e:                       # noqa: BLE001
            return {"lines": _brief_fall(_why(e)), "provider": "engine", "fell_back": True, "why": _why(e)}

    return later(store, "brief", run)


def _of(x, day):
    return x if isinstance(x, dict) and x.get("day") == day else None


def for_card(store, idx, day=None):
    """The card's `voice` (idx's newest result today: <= 3 lines) and `brief` (today's pre-open brief, all day:
    {"lines", "at"}, <= 6 lines). After a restart the store is empty: the day's voice log fills it once (anytime-start),
    a newer result in memory always wins."""
    day = day or _today()
    if store.get("_restored") != day:
        newest = {}
        for r in _rows(day):
            newest["brief" if r.get("kind") == "brief" else r.get("idx")] = r
        with _LOCK:                                  # later() stores under the same lock: a live answer is never undone
            store["_restored"] = day
            for k, r in newest.items():
                if k and not _of(store.get(k), day):
                    store[k] = {"lines": list(r.get("lines") or []), "provider": r.get("provider"),
                                "fell_back": r.get("fell_back"), "why": r.get("why"), "q": r.get("q"), "day": day,
                                "at": str(r.get("t") or "")[:5]}
    b = _of(store.get("brief"), day)
    return _of(store.get(idx), day), ({"lines": list(b.get("lines") or [])[:BRIEF_LINES], "at": b.get("at")} if b else None)
