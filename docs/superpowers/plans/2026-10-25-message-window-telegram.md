# Message window + Telegram alerts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved spec `docs/superpowers/specs/2026-10-25-message-window-telegram-design.md` (NOTEPAD A101). Her words: "sometime i miss the signals it genrate and not able to decipher whats its telling, on these many screen". The plan delivers:
- one server-built **message stream**: one line per CHANGE in a read the tool already logs;
- the floating window as the **message window**, flat and in a trade;
- an outbound **Telegram** subset;
- a read-only **replay**.

**Architecture:**
- **`messages.py` (pure).** Today's READ log + DECODE log rows → READ / LEG / SETUP / DIN messages. It also turns the voice into TRADE and the recording check into HEALTH. Each message carries a `line` that every face shows verbatim.
- **`server.py`.** A pass every 20 s on its own thread writes each new message once to `data/messages/msg_<day>.jsonl` and keeps today's stream and NOW in memory. `_in_trade` hands it the voice. `GET /api/messages?since=` serves that memory and never computes.
- **`telegram_out.py`.** It gates the alert subset (market hours, a fresh close, once per key, 6 a minute), queues it, and sends it from one daemon thread with stdlib `urllib`. It is OFF without `telegr/chat.txt`.
- **`tools/telegram_setup.py`.** It writes `telegr/chat.txt` from `getUpdates`.
- **`ui-v2/src/pro/Float.tsx` + `pro/api.ts`.** The Float polls the stream on its existing poll. Flat: NOW + the last 10 lines. In a trade: the voice on top, the lines below.
- **`tools/messages_replay.py`.** It rebuilds a past day read-only.

**Tech Stack:** Python 3.13 (`C:\Python313`) stdlib only (`urllib`, `queue`, `threading`), pytest; React 19 + TypeScript in ui-v2 (no test runner; gates are `tsc` + `vite build` + a render check). No new dependency.

## Spec corrections found against the code (read before Task 1)

Each was measured on the real files. The plan builds the corrected version.

1. **SETUP comes from DECODE's setup chips, not `confluence_log.jsonl`.**
   - That log writes a row only once the setup's window has CLOSED. On 23 Oct [M]:
     - FADE-D rows landed 30–36 min after the episode start;
     - the BANKNIFTY FADE 10:19 row landed at 12:46;
     - 12 of its 14 rows never fired (`entry: null`).
   - The two that fired are exactly DECODE's two chip turns to an entry, at the same close (DECODE logs each 5-min close a grace minute after it, so the line lands about a minute later):
     - BANKNIFTY RIDE SELL, entry bar 10:45 (`MATCH`);
     - BANKNIFTY FADE-D BUY, entry 13:15 (`line 54,078 · 0.0R`).
   - DECODE *calls* the registered setups (`decode._fade` / `_ride` / `_fade_d`). It never re-implements them.
2. **DECODE's `call.d` is the deceleration COUNT, not a direction.**
   - The direction is the row's `leg.d`. `call.c` is the continuation count.
   - The agree rule (`messages.agree`):
     - JAARI reads the leg's way with `c/7`;
     - THAK reads against the leg with `d/7`;
     - `saath` when that way is the message's, `khilaaf` when against.
   - There are **four** outcomes, not three: `mila d/c` (checked, mixed), `saaf nahi` (checked, no leg), `?` (no DECODE row for that close). CLAUDE.md rule 6 forbids collapsing them.
3. **LEG holds through MILA / saaf nahi.** On 23 Oct [M] each index had 30–37 kind changes, but only 14–17 JAARI ↔ THAK turns or flips. Counting MILA would double the window's churn.
4. **Telegram dedupes on the message key `(idx, kind, t, word[, trade id])`, not `(idx, kind, t)`.**
   - 23 Oct had two different SENSEX QUITs at 13:40 and two at 13:45.
   - There is also a **freshness gate** the spec did not state: a line is sent only when its close is within 10 min of now. A restart rebuilds the morning into the window, never into her phone.
5. **HEALTH.**
   - A silent GoCharting tab is already `RECORDING NAHI: GoCharting` (`_recording`'s 2-min frame check).
   - A **dead server cannot send anything**, so Telegram cannot say "server down". The Float's existing `NOT LIVE since` covers the screen only.
   - `_recording()` answers from 09:20, so "TapeMap live · recording ok" lands at the first pass ≥ 09:20, not 09:15.
6. **The READ log is written only while something polls `/api/read`.** 5173's index header does, on every tab (NOTEPAD A95). With 5173 closed there are no READ lines; DECODE lines still come from the GoCharting frames.
7. **The voice's state lives in memory only.** `data/hold/map_<day>.jsonl` holds trademap events, not voice states. So TRADE is observed in `server._in_trade`, which both `/api/fold?id=` and the frame POST call (`server.py:4832`, `:5700`).
8. **ui-v2 is hot-reloaded into her open 5173 by her running Vite.** A half-applied Task 5 would break her live screen. Task 5 runs only after 15:40 IST or on a weekend.

## Global Constraints

- **Paths and baseline.**
  - Repo `C:\Users\kaam\Desktop\operator mode\tapemap`, branch `feature/operator-objects`. Run everything from the repo root.
  - ui-v2 commands run from `tapemap\ui-v2`.
  - Suite: `python -m pytest -q`. Baseline: 1993 collected = 1991 pass, 1 skipped, 1 known flaky (`test_v2feed.py::test_serve_caches_full_and_answers_delta`, NOTEPAD A49, passes alone).
- **Her processes run.**
  - Never start or stop the TapeMap server (8765) or Vite (5173). The controller restarts nothing.
  - Server changes go live at her own restart after a close.
- **ui-v2 edits (Task 5) only after 15:40 IST or on a weekend:** her Vite hot-reloads them into her live screen. Python edits are safe at any hour: the running server never re-imports `server.py`, and `messages.py` / `telegram_out.py` are new.
- **Data.** Never write under `tapemap/data/` from tests. Tests use `tmp_path`; conftest's `STR_PATHS` redirects every writer. The two tools only read `data/`.
- **Commits.** Implementers do not commit. The controller commits after review, and only after Mary says commit (Task 7). The commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Editing.**
  - Edits are exact strings only: no reformatting, renames or line-ending churn. Keep each file's line endings. Measured by bytes on 25 Oct:

    | Line endings | Files |
    |---|---|
    | CRLF | `server.py`, `conftest.py`, `ui-v2/src/pro/api.ts`, `ui-v2/src/hold/hold.css`, `docs/live/NOTEPAD.md`, `CLAUDE.md` |
    | LF | `ui-v2/src/pro/Float.tsx` |
    | LF (new files) | every new file in this plan |

  - **After each edit to a CRLF file, check it by bytes:**

    ```
    python -c "import sys;b=open(sys.argv[1],'rb').read();print(b.count(b'\r\n'),b.count(b'\n'))" server.py
    ```

    The two numbers must be equal for a CRLF file, and the first must be 0 for an LF file.
  - If a CRLF file now has bare LFs, fix only that file. This is safe because these files are 100% CRLF:

    ```
    python -c "import sys;p=sys.argv[1];b=open(p,'rb').read();open(p,'wb').write(b.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))" server.py
    ```

  - After each task, `git diff --stat` must show only the lines that task changed.
- **THE TOKEN.**
  - Never open, print, log, paste or commit `tapemap/telegr/bot.txt` or its token.
  - Tests build a fake token-shaped string at runtime. conftest points `telegram_out.DIR` at `tmp_path`, so no test can read the real file.
  - No test makes a network call: every send goes through the `telegram_out._open` seam, faked.
- **No new read or signal: only changes in existing reads.** No `%` confidence, no hit rate.
- **Never touch:**
  - the registered rules §1i–§1q;
  - `engine.py`, `band_rotation.py`, `fronts.py`, `signals.py`, `frame.py`, `read.py`, `decode.py`, `voice.py`, `confluence_log.py`;
  - any forward log's existing rows;
  - `data/trigger_log.jsonl`.
- **The Fact-Forcing Gate hook** may ask an agent for facts before its first Bash or edit: importers, the API, the data schema, the user's instruction. State them briefly and retry. The user's instruction is: *"Spec looks good. I sent /start to my bot. Plan and build it."*

## Interfaces (every task's names, exact)

**A message** (a dict; written to `data/messages/msg_<day>.jsonl` and served as is):

| Field | Value |
|---|---|
| `t` | `"HH:MM"`: the close it is about (TRADE: the voice's `trig_t`; HEALTH: the pass minute) |
| `idx` | `"NIFTY"` / `"BANKNIFTY"` / `"SENSEX"`, or `"ALL"` for HEALTH |
| `kind` | `"READ"` / `"LEG"` / `"SETUP"` / `"DIN"` / `"TRADE"` / `"HEALTH"` |
| `dir` | `-1` / `0` / `1` |
| `word` | `str` |
| `agree` | `str` (None only for HEALTH) |
| `level` | `str` with an `s` / `f` tag, or None |
| `why` | `str` or None |
| `key` | `"idx\|kind\|t\|word[\|id]"` |
| `line` | the one line every face shows |
| `at` | epoch s, set by `server._msg_write` |
| `ev` | `"WORD"` / `"QUIT"` (READ only) |
| `id` | the trade id (TRADE only) |

**`messages.py`:**
- constants: `ARROW`, `KINDS`, `OFF`, `TRADE_ON`;
- builders:
  - `key(m) -> str`, `line(m) -> str`, `_msg(t, idx, kind, d, word, agree_, level, why, **extra) -> dict`;
  - `name(word, d=0, ff=False) -> str`, `agree(row, d) -> str`;
  - `build(read_rows, decode_rows) -> list[dict]`, `now_rows(read_rows, decode_rows, idxs) -> list[dict]`;
  - `trade(tr, v, was, row, hm) -> dict | None`, `health(rec, was, hm) -> dict | None`.
- A NOW row is `{idx, dir, word, line, why}`.

**`server.py`:**
- state: `MSG_DIR`, `MSG_EVERY_S = 20`, `_MSG_LOCK`, `_msg_fresh() -> dict`, `_MSG`;
- writers:
  - `_msg_load(day)` (the caller holds `_MSG_LOCK`);
  - `_msg_write(day, msgs, now=None) -> list`;
  - `_msg_pass(now=None)`, `_msg_voice(tr, v, now=None)`;
- readers: `_msg_reply(since=0.0) -> dict`, `_msg_loop()`;
- `GET /api/messages?since=<epoch s>` → `{ok: True, day, asof: "HH:MM:SS", now: [...], msgs: [...], tag: "I"}` or `{ok: False, why}`.

**`telegram_out.py`:**
- config: `DIR`, `API`, `TOKEN_RE`, `CAP = 6`, `TIMEOUT_S = 8`, `RETRIES = 2`, `FRESH_S = 600`, `QUIET_S = 3600`, `TICK_S = 2`, `OPEN_HM`, `CLOSE_HM`;
- state: `_open`, `_ON`, `_Q`, `_SENT`, `_HELD`, `_USED`, `_FAIL`;
- functions:
  - `scrub(s)`, `token()`, `chat()`, `config()`;
  - `wants(m)`, `gate(m, d)`, `offer(msgs, now=None) -> int`, `plan(lines, used) -> (texts, n)`;
  - `send(tok, chat_id, text) -> bool`, `_failed(err, now=None)`, `_drain(now=None) -> list`, `_run()`, `start()`.

**Tools:**
- `tools/telegram_setup.py`: `UPDATES_TIMEOUT`, `latest_private(updates) -> (chat_id, first_name) | None`, `main() -> int`.
- `tools/messages_replay.py`: `DATA`, `IDXS`, `_rows(path)`, `main(day, as_json=False, data=DATA) -> int`.

**`ui-v2/src/pro/api.ts`:**
- types: `Msg`, `NowRow`, `Msgs`;
- `S.msgs: Msgs | null`;
- `msgsOn()`.

---

### Task 1: `messages.py`, the pure builder

**Files:**
- Create: `messages.py`
- Test: `test_messages.py`

**Interfaces:** Produces every `messages.*` name above. Consumes nothing (pure: no I/O, no clock).

- [ ] **Step 1: Write the failing tests.** Create `test_messages.py`:

```python
"""THE MESSAGE STREAM's builder (messages.py): one line per CHANGE in a read the server already logs, with DECODE's count
at that close. Fixture READ / DECODE / setup / DIN / voice / recording rows; pure, so no file and no clock."""
import messages


def mark(t, word, d=0, idx="NIFTY", **kw):
    return dict(kind="mark", idx=idx, t=t, word=word, dir=d, **kw)


def ev(t, event, d, text, idx="NIFTY", en="", **kw):
    return dict(kind="event", idx=idx, t=t, event=event, dir=d, text=text, en=en, **kw)


def dec(T, kind="JAARI", ld=-1, d=0, c=5, idx="NIFTY", setups=(), ty=None):
    return {"idx": idx, "T": T, "call": {"text": "x", "kind": kind, "d": d, "c": c, "of": 7,
                                         "signs": ["CVD leg low pe", "Δ leg ke saath"]},
            "leg": None if ld is None else {"d": ld, "ext": {"t": T, "fut": 22790.0, "spot": 22740.0}},
            "setups": list(setups), "onesided": {"type": ty}}


def lines(ms, kind):
    return [m["line"] for m in ms if m["kind"] == kind]


def test_read_word_changes_once_from_the_marks():
    """One line per change of THE READ's held word (word, arrow, flow+fuel). BAN RAHA is never named, a repeat says nothing,
    and the line carries DECODE's count at that close and the READ's own level (spot)."""
    rr = [mark("09:40", "BAN RAHA"), mark("09:45", "WAIT"), mark("09:55", "LEAN", -1, flip=22800.0, since="09:55"),
          ev("09:55", "FORM", -1, "LEAN ▼ bana · FLIP 22,800", en="the read formed"),
          mark("10:00", "LEAN", -1, flip=22800.0), mark("10:05", "TREND", -1, src="flow+fuel", flip=22780.0),
          mark("10:10", "RANGE", 0, box={"top": {"k": 22900}, "bottom": {"k": 22700}}),
          ev("10:10", "BREAK", 1, "TREND ▼ · flow+fuel khatam · price ulta TREND")]
    dr = [dec("09:55", c=5), dec("10:05", "THAK", d=4, c=1), dec("10:10", "MILA", d=2, c=3)]
    ms = messages.build(rr, dr)
    assert lines(ms, "READ") == ["09:55  NIFTY  WAIT → LEAN ▼ · 5/7 saath · flip 22,800s",
                                 "10:05  NIFTY  LEAN ▼ → TREND ▼ · flow+fuel · 4/7 khilaaf · flip 22,780s",
                                 "10:10  NIFTY  TREND ▼ · flow+fuel → RANGE · mila 2/3 · box 22,700–22,900s"]
    read = [m for m in ms if m["kind"] == "READ"]
    assert read[0]["why"] == "the read formed" and read[0]["dir"] == -1 and read[0]["ev"] == "WORD"
    assert read[0]["key"] == "NIFTY|READ|09:55|WAIT → LEAN ▼"
    assert read[-1]["why"] == "TREND ▼ · flow+fuel khatam · price ulta TREND"          # a BREAK's own words win


def test_agree_reads_decodes_count_and_its_way():
    """JAARI reads its leg's way (c/7), THAK against it (d/7); saath / khilaaf against the message, DECODE's arrow when the
    message has no way. mila, saaf nahi and ? stay three different sentences (CLAUDE.md rule 6)."""
    up = dec("10:00", "JAARI", ld=1, c=5)
    assert messages.agree(up, 1) == "5/7 saath" and messages.agree(up, -1) == "5/7 khilaaf"
    assert messages.agree(up, 0) == "▲5/7"
    assert messages.agree(dec("10:00", "THAK", ld=1, d=4), -1) == "4/7 saath"
    assert messages.agree(dec("10:00", "MILA", d=2, c=3), 1) == "mila 2/3"
    assert messages.agree(dec("10:00", "SAAF_NAHI", ld=None), 1) == "saaf nahi"
    assert messages.agree(None, 1) == "?"
    assert messages.agree(dict(dec("10:00"), call={"text": "?", "kind": "SAAF_NAHI"}), 1) == "?"


def test_leg_moves_only_on_jaari_thak_or_a_flip():
    """MILA, saaf nahi and an unread close keep the last leg read: 23 Oct had 30-37 kind changes an index [M], 14-17 of
    them JAARI / THAK turns."""
    dr = [dec("09:35", "JAARI"), dec("09:40", "MILA", d=2, c=3), dec("09:45", "JAARI"), dec("09:50", "THAK", d=4, c=2),
          dec("09:55", "SAAF_NAHI", ld=None), dec("10:00", "JAARI", ld=1, c=6)]
    assert lines(messages.build([], dr), "LEG") == ["09:35  NIFTY  ▼ leg jaari · 5/7 saath",
                                                    "09:50  NIFTY  ▼ leg thak raha · 4/7 khilaaf",
                                                    "10:00  NIFTY  ▲ leg jaari · 6/7 saath"]


def test_setup_fires_on_match_and_again_only_after_it_clears():
    """A FADE / RIDE / FADE-D chip turning MATCH (or an entry's HOLD v2 state) is one SETUP line with the leg's extreme
    (fut). The chip staying live says nothing; it fires again only after it went back to ARMED or —."""
    def s(state, nm="FADE-D", side="BUY"):
        return [{"name": nm, "side": side, "checks": {}, "state": state}]
    dr = [dec("13:05", "THAK", d=4, setups=s("ARMED")), dec("13:10", "THAK", d=4, setups=s("MATCH")),
          dec("13:15", "THAK", d=4, setups=s("line 22,700 · +0.2R")), dec("13:20", "THAK", d=4, setups=s("—")),
          dec("13:25", "THAK", d=4, setups=s("MATCH")), dec("13:30", "THAK", d=4, setups=s("MATCH", "RIDE", "SELL"))]
    ms = messages.build([], dr)
    assert lines(ms, "SETUP") == ["13:10  NIFTY  FADE-D BUY · 4/7 saath · 22,790f",
                                  "13:25  NIFTY  FADE-D BUY · 4/7 saath · 22,790f",
                                  "13:30  NIFTY  RIDE SELL · 4/7 khilaaf · 22,790f"]
    assert [m["why"] for m in ms if m["kind"] == "SETUP"] == ["MATCH", "MATCH", "MATCH"]


def test_din_changes_and_a_quit_is_its_own_read_line():
    """The day type speaks on a change only (an unread type keeps the last); a QUIT is a READ line of its own."""
    dr = [dec("09:20", "SAAF_NAHI", ld=None, ty="MIXED"), dec("09:25", ty="MIXED"), dec("11:00", c=7, ty="TREND ▼"),
          dec("11:05", ty=None), dec("11:10", ty="TREND ▼"), dec("14:40", ty="CHOP")]
    rr = [ev("10:10", "QUIT", -1, "22,600 PE likhne wale bhage · +37.2L → +15.1L · paar +78", k=22600.0, side="PE")]
    ms = messages.build(rr, dr)
    assert lines(ms, "DIN") == ["09:20  NIFTY  din MIXED · saaf nahi", "11:00  NIFTY  din TREND ▼ · 7/7 saath",
                                "14:40  NIFTY  din CHOP · ▼5/7"]
    q = [m for m in ms if m.get("ev") == "QUIT"]
    assert [m["line"] for m in q] == ["10:10  NIFTY  22,600 PE likhne wale bhage · ?"]
    assert q[0]["why"].startswith("22,600 PE likhne wale bhage · +37.2L")


def test_now_rows_one_per_index_with_a_reason_when_missing():
    rr = [mark("10:00", "LEAN", -1, since="09:55"), mark("10:05", "TREND", -1, src="flow+fuel", since="09:55"),
          mark("10:05", "RANGE", idx="SENSEX", since="10:05")]
    dr = [dec("10:05", c=6), dec("10:05", "THAK", d=4, idx="SENSEX")]
    assert [r["line"] for r in messages.now_rows(rr, dr, ["NIFTY", "BANKNIFTY", "SENSEX"])] == [
        "NIFTY  TREND ▼ · flow+fuel · 6/7 saath · since 09:55", "BANKNIFTY  read abhi nahi",
        "SENSEX  RANGE · ▲4/7 · since 10:05"]


def test_trade_and_health_are_changes_only():
    tr = {"id": "t1", "idx": "NIFTY"}
    v = {"ok": True, "state": "WARN", "d": -1, "trig_t": "11:07", "stop_f": 22780.0,
         "reason": "CE front gave up @ 22,780f · line 22,780f (HOLD v2)"}
    m = messages.trade(tr, v, "HOLD", dec("11:05", "THAK", d=4), "11:08")
    assert m["line"] == "11:07  TRADE  WARN · CE front gave up @ 22,780f · 4/7 khilaaf · stop 22,780f"
    assert m["key"] == "NIFTY|TRADE|11:07|WARN|t1" and m["id"] == "t1"
    assert messages.trade(tr, v, "WARN", None, "11:08") is None                        # the same state: said already
    assert messages.trade(tr, dict(v, state="HOLD"), "WARN", None, "11:08") is None     # HOLD is the quiet state
    assert messages.trade(tr, {"ok": False, "why": "x"}, None, None, "11:08") is None
    ok = {"ok": True, "missing": [], "text": None}
    nahi = {"ok": False, "missing": ["book", "GoCharting"], "text": "RECORDING NAHI: book, GoCharting"}
    assert messages.health(None, None, "09:16") is None
    assert messages.health(ok, None, "09:20")["line"] == "09:20  HEALTH  TapeMap live · recording ok"
    assert messages.health(ok, "TapeMap live", "09:21") is None
    assert messages.health(nahi, "TapeMap live", "11:02")["line"] == "11:02  HEALTH  RECORDING NAHI · book, GoCharting"
    assert messages.health(nahi, "RECORDING NAHI", "11:03") is None
    assert messages.health(ok, "RECORDING NAHI", "11:09")["line"] == "11:09  HEALTH  RECORDING OK"


def test_build_is_the_same_whatever_the_row_order():
    """Anytime-start: the same rows give the same stream, however the logs were appended."""
    rr = [mark("09:55", "LEAN", -1, flip=22800.0), ev("10:10", "QUIT", -1, "a", k=22600.0, side="PE"),
          ev("10:10", "QUIT", -1, "b", k=22550.0, side="PE"), mark("10:10", "WAIT")]
    dr = [dec("09:55"), dec("10:10", "THAK", d=4, ty="MIXED")]
    assert messages.build(rr, dr) == messages.build(rr[::-1], dr[::-1])
```

- [ ] **Step 2: Run them and see them fail.**

Run: `python -m pytest -q test_messages.py`
Expected: an ERROR at collection, `ModuleNotFoundError: No module named 'messages'`.

- [ ] **Step 3: Implement.** Create `messages.py`:

```python
"""messages.py -- THE MESSAGE STREAM: what the tool already said, one line per CHANGE, for the floating window and
Telegram (spec docs/superpowers/specs/2026-10-25-message-window-telegram-design.md; NOTEPAD A101).

Mary, 25 Oct: "sometime i miss the signals it genrate and not able to decipher whats its telling, on these many screen".
NOTHING NEW IS READ: every message is a change in a read the server already logs, write-once.
  READ    THE READ's held word (word, arrow, flow+fuel) changes at a closed mark; a QUIT event   data/read/read_<day>.jsonl
  LEG     DECODE's call turns JAARI <-> THAK or its leg flips; MILA / saaf nahi keep the last    data/decode/decode_<day>.jsonl
  SETUP   a FADE / RIDE / FADE-D chip turns MATCH, or an entry's HOLD v2 state                   the same DECODE rows
  DIN     the one-sided meter's day type changes (TREND ▲ / ▼, CHOP, MIXED)                      the same DECODE rows
  TRADE   the one voice turns TIGHTEN / WARN / EXIT (server._in_trade -> `trade`)
  HEALTH  RECORDING NAHI starts / clears; the day's first look says "TapeMap live" (server._recording -> `health`)
SETUP reads DECODE's chips, not confluence_log: that log writes a row once the setup's window has CLOSED (23 Oct [M]:
FADE-D rows 30-36 min after the start) and 12 of its 14 rows that day never fired; the two that did (BANKNIFTY RIDE
10:45, FADE-D 13:15) are exactly DECODE's two chip turns, at the same close, logged a grace minute after it.
AGREE is DECODE's count at that close, never a %. DECODE's call.d / call.c are the decel / continuation COUNTS; the way is
the leg's d. JAARI reads the leg's way with c/7, THAK against it with d/7: "saath" when that way is the message's,
"khilaaf" when against; a message with no way shows DECODE's arrow and count. "mila d/c" (checked, mixed), "saaf nahi"
(checked, no leg) and "?" (no DECODE row for that close) stay separate sentences.
PURE: no I/O, no clock -- the server hands in the day's rows, so a restart rebuilds the same stream (anytime-start).
DISPLAY ONLY: gates nothing; the faces and Telegram show `line` verbatim. [I]
"""
from __future__ import annotations

import re

ARROW = {1: "▲", -1: "▼", 0: ""}
KINDS = ("HEALTH", "READ", "SETUP", "LEG", "DIN", "TRADE")    # the order of one close's lines
OFF = ("—", "ARMED")                                          # a setup chip that has not fired
TRADE_ON = ("TIGHTEN", "WARN", "EXIT")


def _n(x):
    return "?" if x is None else f"{x:,.0f}"


def key(m):
    """The write-once key within a day: idx | kind | t | word, and the trade id for TRADE."""
    return "|".join(str(x) for x in (m["idx"], m["kind"], m["t"], m["word"]) + ((m["id"],) if m.get("id") else ()))


def line(m):
    """The one line every face and Telegram show: HH:MM  IDX  what · agree · level. TRADE / HEALTH: the kind, and the why's
    first clause."""
    lbl = m["kind"] if m["kind"] in ("TRADE", "HEALTH") else m["idx"]
    head = m["word"]
    if m["kind"] in ("TRADE", "HEALTH") and m.get("why"):
        head += " · " + re.sub(r"\s*\([^)]*\)\s*$", "", str(m["why"]).split(" · ")[0])
    return f"{m['t']}  {lbl}  " + " · ".join(x for x in (head, m.get("agree"), m.get("level")) if x)


def _msg(t, idx, kind, d, word, agree_, level, why, **extra):
    m = dict(t=t, idx=idx, kind=kind, dir=d, word=word, agree=agree_, level=level, why=why, **extra)
    m["key"], m["line"] = key(m), line(m)
    return m


def name(word, d=0, ff=False):
    """THE READ's held word as the faces say it (read._name): "TREND ▼ · flow+fuel", "LEAN ▲", "RANGE"."""
    return f"{word}{' ' + ARROW[d] if d else ''}{' · flow+fuel' if ff else ''}"


def agree(row, d):
    """DECODE's count at this close against direction d (module docstring). Never blank, never a 0."""
    c = (row or {}).get("call") or {}
    k, ld = c.get("kind"), ((row or {}).get("leg") or {}).get("d")
    if not row or c.get("text") in (None, "?"):
        return "?"
    if k == "SAAF_NAHI":
        return "saaf nahi"
    if k == "MILA":
        return f"mila {c.get('d')}/{c.get('c')}"
    if k not in ("JAARI", "THAK") or ld not in (1, -1):
        return "?"
    way, n = (ld, c.get("c")) if k == "JAARI" else (-ld, c.get("d"))
    of = c.get("of") or 7
    return f"{ARROW[way]}{n}/{of}" if not d else f"{n}/{of} {'saath' if way == d else 'khilaaf'}"


def _level(r):
    """THE READ's level: a TREND / LEAN's FLIP, a RANGE's box walls -- spot, as the READ reads them."""
    if r.get("flip") is not None:
        return f"flip {_n(r['flip'])}s"
    bx = r.get("box") or {}
    lo, hi = (bx.get("bottom") or {}).get("k"), (bx.get("top") or {}).get("k")
    return f"box {_n(lo)}–{_n(hi)}s" if lo is not None and hi is not None else None


def build(read_rows, decode_rows):
    """The day's market messages (READ, LEG, SETUP, DIN) from its READ and DECODE log rows, oldest first: each a change
    from the close before it. A row without an index or a close is skipped."""
    dec = sorted((r for r in decode_rows if r.get("idx") and r.get("T")), key=lambda r: (r["T"], r["idx"]))
    at = {(r["idx"], r["T"]): r for r in dec}
    evs = [e for e in read_rows if e.get("kind") == "event" and e.get("idx") and e.get("t")]
    out, held = [], {}
    for r in sorted((r for r in read_rows if r.get("kind") == "mark" and r.get("idx") and r.get("t")),
                    key=lambda r: (r["t"], r["idx"])):
        if r.get("word") in (None, "BAN RAHA"):              # the first 30 minutes are read, never named
            continue
        i, t, s = r["idx"], r["t"], (r["word"], r.get("dir") or 0, r.get("src") == "flow+fuel")
        was, held[i] = held.get(i, ("WAIT", 0, False)), s
        if s == was:
            continue
        here = [e for e in evs if (e["idx"], e["t"]) == (i, t)]
        why = (next((e.get("text") for e in here if e.get("event") == "BREAK"), None)
               or next((e.get("en") for e in here if e.get("event") in ("FORM", "UP", "DOWN")), None))
        out.append(_msg(t, i, "READ", s[1], f"{name(*was)} → {name(*s)}", agree(at.get((i, t)), s[1]), _level(r), why,
                        ev="WORD"))
    for e in evs:
        if e.get("event") == "QUIT":                         # a big writer wall near spot gave back half its build
            d = e.get("dir") or 0
            out.append(_msg(e["t"], e["idx"], "READ", d, f"{_n(e.get('k'))} {e.get('side')} likhne wale bhage",
                            agree(at.get((e["idx"], e["t"])), d), None, e.get("text"), ev="QUIT"))
    leg, live, din = {}, {}, {}
    for r in dec:
        i, t, c, lg = r["idx"], r["T"], r.get("call") or {}, r.get("leg") or {}
        ld = lg.get("d")
        if c.get("kind") in ("JAARI", "THAK") and ld in (1, -1) and leg.get(i) != (c["kind"], ld):
            leg[i] = (c["kind"], ld)                         # MILA / saaf nahi / ? keep the last leg read
            out.append(_msg(t, i, "LEG", ld, f"{ARROW[ld]} leg {'jaari' if c['kind'] == 'JAARI' else 'thak raha'}",
                            agree(r, ld), None, " · ".join((c.get("signs") or [])[:2]) or None))
        on = {(s.get("name"), s.get("side")): str(s.get("state")) for s in r.get("setups") or ()
              if s.get("name") and s.get("side") in ("BUY", "SELL") and str(s.get("state") or "—") not in OFF}
        ext = lg.get("ext") or {}
        for (nm, side), state in on.items():
            if (nm, side) not in live.get(i, {}):
                d = 1 if side == "BUY" else -1
                out.append(_msg(t, i, "SETUP", d, f"{nm} {side}", agree(r, d),
                                None if ext.get("fut") is None else f"{_n(ext['fut'])}f", state))
        live[i] = on
        ty = (r.get("onesided") or {}).get("type")
        if ty and din.get(i) != ty:                          # None (could not check) keeps the last type
            was, din[i] = din.get(i), ty
            d = 1 if "▲" in ty else -1 if "▼" in ty else 0
            out.append(_msg(t, i, "DIN", d, f"din {ty}", agree(r, d), None, None if was is None else f"pehle {was}"))
    return sorted(out, key=lambda m: (m["t"], KINDS.index(m["kind"]), m["idx"], m["word"]))


def now_rows(read_rows, decode_rows, idxs):
    """NOW, one line per index: THE READ's latest logged mark, DECODE's count at that close, since when."""
    dec = {(r.get("idx"), r.get("T")): r for r in decode_rows}
    last = {}
    for r in read_rows:
        if r.get("kind") == "mark" and r.get("idx") and r.get("t") and r["t"] >= (last.get(r["idx"]) or {}).get("t", ""):
            last[r["idx"]] = r
    out = []
    for i in idxs:
        r = last.get(i)
        if r is None:
            out.append({"idx": i, "dir": 0, "word": None, "line": f"{i}  read abhi nahi",
                        "why": "could not check — no READ mark logged yet today"})
            continue
        d = r.get("dir") or 0
        parts = [name(r.get("word") or "?", d, r.get("src") == "flow+fuel"), agree(dec.get((i, r["t"])), d)]
        if r.get("since"):
            parts.append(f"since {r['since']}")
        out.append({"idx": i, "dir": d, "word": r.get("word"), "line": f"{i}  " + " · ".join(parts), "why": f"mark {r['t']}"})
    return out


def trade(tr, v, was, row, hm):
    """THE ONE VOICE's turn into TIGHTEN / WARN / EXIT as a message (`was`: its last state for this trade; `row`: the
    trade index's latest DECODE row), else None -- the same state, HOLD, or no voice."""
    st = (v or {}).get("state")
    if not (v or {}).get("ok") or st == was or st not in TRADE_ON:
        return None
    d = v.get("d") or 0
    return _msg(v.get("trig_t") or hm, tr["idx"], "TRADE", d, st, agree(row, d),
                None if v.get("stop_f") is None else f"stop {_n(v['stop_f'])}f", v.get("reason"), id=tr["id"])


def health(rec, was, hm):
    """server._recording ({ok, missing, text}; None outside 09:20-15:30) as a message, else None: the day's first look
    says "TapeMap live", then RECORDING NAHI once when it starts and RECORDING OK once when it clears."""
    if rec is None:
        return None
    if not rec.get("ok"):
        return None if was == "RECORDING NAHI" else _msg(hm, "ALL", "HEALTH", 0, "RECORDING NAHI", None, None,
                                                           ", ".join(rec.get("missing") or ()) or None)
    if was is None:
        return _msg(hm, "ALL", "HEALTH", 0, "TapeMap live", None, None, "recording ok")
    return _msg(hm, "ALL", "HEALTH", 0, "RECORDING OK", None, None, None) if was == "RECORDING NAHI" else None
```

- [ ] **Step 4: Run them and see them pass.**

Run: `python -m pytest -q test_messages.py`
Expected: 8 passed. (Planned and checked in memory against this exact code on 25 Oct.)

---

### Task 2: The server wiring: the pass, the write-once record, `GET /api/messages`, isolation, a restart

**Files:**
- Modify: `server.py`:
  - the imports (after `import voice_path`);
  - a new block after `_health_safe`;
  - `_in_trade` (one line after `sensex_flow.relabel`);
  - the `do_GET` route (before `/api/read`);
  - `_isolate_mock_writers`;
  - `main()` (one thread after `daylog`).
- Modify: `conftest.py` (`STR_PATHS`: one line).
- Test: `test_messages_server.py` (new). `test_leak_guard.py` gains one parametrized case automatically.

**Interfaces:**
- Consumes: `messages.build` / `now_rows` / `health` / `trade` / `TRADE_ON` (Task 1).
- Consumes from `server.py`: `server._recording`, `_health_safe`, `_ist`, `READ_DIR`, `DECODE_DIR`, `confluence_log._rows`, `instruments.ENABLED`.
- Produces the `server._msg_*` names and the route listed in Interfaces.

- [ ] **Step 1: Write the failing tests.** Create `test_messages_server.py`:

```python
"""THE MESSAGE STREAM's server half (server._msg_*): the pass writes each message once, a restart rebuilds the same stream,
the voice's turn is one TRADE line even across a restart, a weekend writes nothing, and GET /api/messages serves NOW + the
lines after ?since=. Every writer is under tmp_path (conftest STR_PATHS); the clock is handed in."""
import json
import os
from datetime import datetime

import pytest

import server
from chain_live import IST
from test_senses_api import _Cap

DAY = "2026-10-23"                                             # a Friday
OK = {"ok": True, "missing": [], "text": None}
READ = [{"kind": "mark", "idx": "NIFTY", "t": "09:50", "word": "WAIT", "dir": 0},
        {"kind": "mark", "idx": "NIFTY", "t": "09:55", "word": "LEAN", "dir": -1, "flip": 22800.0, "since": "09:55"},
        {"kind": "event", "idx": "NIFTY", "t": "09:55", "event": "FORM", "dir": -1, "text": "LEAN ▼ bana · FLIP 22,800",
         "en": "the read formed"}]
DECODE = [{"idx": "NIFTY", "T": "09:55", "call": {"text": "▼ leg jaari · 5/7", "kind": "JAARI", "d": 1, "c": 5, "of": 7,
                                                  "signs": ["CVD leg low pe"]},
           "leg": {"d": -1, "ext": {"t": "09:50", "fut": 22790.0, "spot": 22740.0}}, "setups": [],
           "onesided": {"type": "MIXED"}}]


def at(h, m, s=0, day=DAY):
    y, mo, d = (int(x) for x in day.split("-"))
    return datetime(y, mo, d, h, m, s, tzinfo=IST).timestamp()


def _put(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def _disk(day=DAY):
    p = os.path.join(server.MSG_DIR, f"msg_{day}.jsonl")
    return [json.loads(x) for x in open(p, encoding="utf-8")] if os.path.exists(p) else []


@pytest.fixture(autouse=True)
def _day(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "READ_DIR", str(tmp_path / "read"))
    monkeypatch.setattr(server, "_MSG", server._msg_fresh())
    monkeypatch.setattr(server, "_recording", lambda now=None: OK)
    for day in (DAY, "2026-10-24"):
        _put(os.path.join(server.READ_DIR, f"read_{day}.jsonl"), READ)
        _put(os.path.join(server.DECODE_DIR, f"decode_{day}.jsonl"), DECODE)


def test_the_pass_writes_each_message_once_and_a_restart_rebuilds_the_same_stream(monkeypatch):
    server._msg_pass(at(10, 7))
    rows = _disk()
    assert [r["line"] for r in rows] == ["09:55  NIFTY  WAIT → LEAN ▼ · 5/7 saath · flip 22,800s",
                                         "09:55  NIFTY  ▼ leg jaari · 5/7 saath", "09:55  NIFTY  din MIXED · ▼5/7",
                                         "10:07  HEALTH  TapeMap live · recording ok"]
    assert {r["at"] for r in rows} == {round(at(10, 7), 3)}
    monkeypatch.setattr(server, "_MSG", server._msg_fresh())          # a restart: memory gone, the record stays
    server._msg_pass(at(10, 8))
    assert _disk() == rows
    rep = server._msg_reply(0)
    assert [m["key"] for m in rep["msgs"]] == [r["key"] for r in rows] and rep["asof"] == "10:08:00"
    assert [r["line"] for r in rep["now"]] == ["NIFTY  LEAN ▼ · 5/7 saath · since 09:55", "BANKNIFTY  read abhi nahi",
                                               "SENSEX  read abhi nahi"]
    assert server._msg_reply(at(10, 7))["msgs"] == []


def test_the_route_serves_now_and_the_lines_after_since():
    cap = _Cap("/api/messages?since=0")
    server.Handler.do_GET(cap)
    assert cap.sent["ok"] is False and cap.sent["why"].startswith("could not check")    # before the first pass
    server._msg_pass(at(10, 7))
    for path in ("/api/messages?since=0", "/api/messages?since=abc", "/api/messages"):
        cap = _Cap(path)
        server.Handler.do_GET(cap)
        assert cap.sent["ok"] is True and len(cap.sent["msgs"]) == 4 and len(cap.sent["now"]) == 3
    cap = _Cap(f"/api/messages?since={at(10, 7)}")
    server.Handler.do_GET(cap)
    assert cap.sent["msgs"] == []


def test_a_voice_turn_is_one_trade_line_even_across_a_restart(monkeypatch):
    tr = {"id": "t1", "idx": "NIFTY"}
    v = {"ok": True, "state": "WARN", "d": -1, "trig_t": "11:07", "stop_f": 22780.0,
         "reason": "CE front gave up @ 22,780f · line 22,780f (HOLD v2)"}
    server._msg_voice(tr, v, at(11, 7, 30))
    server._msg_voice(tr, v, at(11, 7, 40))                              # every face's poll: still one line
    monkeypatch.setattr(server, "_MSG", server._msg_fresh())
    server._msg_voice(tr, v, at(11, 8))                                  # a restart while it is still WARN
    server._msg_voice(tr, dict(v, state="HOLD"), at(11, 20))             # HOLD is quiet
    server._msg_voice(tr, dict(v, trig_t="11:30"), at(11, 30, 10))       # a new WARN
    assert [r["line"] for r in _disk()] == ["11:07  TRADE  WARN · CE front gave up @ 22,780f · 5/7 saath · stop 22,780f",
                                            "11:30  TRADE  WARN · CE front gave up @ 22,780f · 5/7 saath · stop 22,780f"]


def test_a_weekend_writes_nothing():
    """24 Oct is a Saturday: a stray DECODE row (the server ran on 25 Oct and logged SAAF_NAHI rows) is not a session."""
    server._msg_pass(at(10, 7, day="2026-10-24"))
    assert _disk("2026-10-24") == []
    rep = server._msg_reply(0)
    assert rep["ok"] is True and rep["msgs"] == [] and rep["now"][0]["line"].startswith("NIFTY  LEAN ▼")
```

- [ ] **Step 2: Run them and see them fail.**

Run: `python -m pytest -q test_messages_server.py`
Expected: 4 ERRORS in setup, `AttributeError: module 'server' has no attribute '_msg_fresh'`.

- [ ] **Step 3: Implement.** Make seven replacements in `server.py` (CRLF), then one in `conftest.py` (CRLF).

**(a) The import.** Replace

```python
import voice_path                # the voice replayed over a past marked trade (A56), GET /api/voice_path
```

with

```python
import voice_path                # the voice replayed over a past marked trade (A56), GET /api/voice_path
import messages                  # THE MESSAGE STREAM (A101): one line per change of an existing read, GET /api/messages
```

**(b) The block, after `_health_safe`.** Replace

```python
        log.exception("/api/health: %s", fn.__name__)
        return None


def _frame_chain(poller, idx):
```

with

```python
        log.exception("/api/health: %s", fn.__name__)
        return None


# ---- THE MESSAGE STREAM (messages.py; spec 2026-10-25-message-window-telegram, NOTEPAD A101) --------------------------
#
# What the tool already said, one line per CHANGE, for the floating window and Telegram. A pass every MSG_EVERY_S on its own
# thread (_msg_loop) reads today's READ and DECODE logs and the recording check; _in_trade hands in the voice. Each message
# is written ONCE to MSG_DIR/msg_<day>.jsonl (weekdays from 09:15; a late start writes the morning late, and its `at` says
# so) and kept in memory with NOW; GET /api/messages serves that memory and never computes. DISPLAY ONLY: nothing here
# reaches a gate, a beep rule, the engine or trigger_log.
MSG_DIR = os.path.join("data", "messages")         # the stream's write-once record, msg_<day>.jsonl (_msg_write)
MSG_EVERY_S = 20                                   # close + the read log's 60 s grace + <= 20 s: a line ~1.5 min after its close
_MSG_LOCK = threading.Lock()


def _msg_fresh():
    return {"day": None, "items": [], "keys": set(), "voice": {}, "health": None, "now": [], "asof": None}


_MSG = _msg_fresh()


def _msg_load(day):
    """(the caller holds _MSG_LOCK) Today's record into memory, once per day: a restart knows what was already said, the last
    voice state per trade and the last HEALTH word."""
    if _MSG["day"] == day:
        return
    items = [r for r in confluence_log._rows(os.path.join(MSG_DIR, f"msg_{day}.jsonl")) if r.get("key")]
    _MSG.update(_msg_fresh(), day=day, items=items, keys={r["key"] for r in items},
                voice={r["id"]: r["word"] for r in items if r.get("kind") == "TRADE" and r.get("id")},
                health=next((r["word"] for r in reversed(items) if r.get("kind") == "HEALTH"), None))


def _msg_write(day, msgs, now=None):
    """Each message whose key is not in today's record: stamped `at` (epoch s), appended to MSG_DIR/msg_<day>.jsonl ONCE and
    kept in memory. Weekdays from 09:15 only: a Sunday's stray DECODE rows are not a session. -> the new ones. Fail-soft: a
    disk error is logged and nothing is kept, so the next pass tries again."""
    from datetime import date as _date
    if _date.fromisoformat(day).weekday() >= 5 or _ist(now).strftime("%H:%M") < "09:15":
        return []
    t = round(time.time() if now is None else now, 3)
    with _MSG_LOCK:
        _msg_load(day)
        new, seen = [], set(_MSG["keys"])
        for m in msgs:
            if m["key"] not in seen:
                seen.add(m["key"])
                new.append(dict(m, at=t))
        if not new:
            return []
        try:
            os.makedirs(MSG_DIR, exist_ok=True)
            with open(os.path.join(MSG_DIR, f"msg_{day}.jsonl"), "a", encoding="utf-8") as f:
                f.write("".join(json.dumps(m, ensure_ascii=False) + "\n" for m in new))
        except OSError:
            log.exception("message log")
            return []
        _MSG["items"].extend(new)
        _MSG["keys"].update(m["key"] for m in new)
    return new


def _msg_pass(now=None):
    """One pass: today's READ and DECODE logs -> the market messages (messages.build, pure: a restart rebuilds the same
    stream), the recording check -> HEALTH, each written once; NOW rebuilt for the faces."""
    d = _ist(now)
    day, hm = d.strftime("%Y-%m-%d"), d.strftime("%H:%M")
    rr = list(confluence_log._rows(os.path.join(READ_DIR, f"read_{day}.jsonl")))
    dr = list(confluence_log._rows(os.path.join(DECODE_DIR, f"decode_{day}.jsonl")))
    rec = _health_safe(lambda: _recording(now))
    with _MSG_LOCK:
        _msg_load(day)
        h = messages.health(rec, _MSG["health"], hm)
    _msg_write(day, messages.build(rr, dr) + ([h] if h else []), now)
    with _MSG_LOCK:
        if h and h["key"] in _MSG["keys"]:
            _MSG["health"] = h["word"]
        _MSG.update(now=messages.now_rows(rr, dr, instruments.ENABLED), asof=d.strftime("%H:%M:%S"))


def _msg_voice(tr, v, now=None):
    """THE ONE VOICE's turn into TIGHTEN / WARN / EXIT, once, into the stream (messages.trade). The last state per trade is
    memory, seeded from today's record (_msg_load), so a restart does not say it twice. Called by _in_trade on every fold
    read and frame POST: O(1) unless the state changed. Fail-soft: never the voice's failure."""
    try:
        if not (v or {}).get("ok"):
            return
        d = _ist(now)
        day, hm = d.strftime("%Y-%m-%d"), d.strftime("%H:%M")
        with _MSG_LOCK:
            _msg_load(day)
            was = _MSG["voice"].get(tr["id"])
            _MSG["voice"][tr["id"]] = v["state"]
        if was == v["state"] or v["state"] not in messages.TRADE_ON:
            return
        rows = [r for r in confluence_log._rows(os.path.join(DECODE_DIR, f"decode_{day}.jsonl")) if r.get("idx") == tr["idx"]]
        m = messages.trade(tr, v, was, max(rows, key=lambda r: str(r.get("T")), default=None), hm)
        if m:
            _msg_write(day, [m], now)
    except Exception:
        log.exception("message voice")


def _msg_reply(since=0.0):
    """GET /api/messages: NOW per index and today's messages written after `since` (epoch s), from the pass's memory."""
    with _MSG_LOCK:
        if _MSG["asof"] is None:
            return {"ok": False, "why": "could not check — the message stream has not read today yet (its first pass runs "
                                        "at the start)"}
        return {"ok": True, "day": _MSG["day"], "asof": _MSG["asof"], "now": list(_MSG["now"]),
                "msgs": [m for m in _MSG["items"] if (m.get("at") or 0) > since], "tag": "I"}


def _msg_loop():
    """The pass at the start, then every MSG_EVERY_S; never raises (a failed pass is logged, the next one retries)."""
    while True:
        try:
            _msg_pass()
        except Exception:
            log.exception("message pass")
        time.sleep(MSG_EVERY_S)


def _frame_chain(poller, idx):
```

**(c) `_in_trade`: the voice's turn.** Replace

```python
            if rep.get("flow_src"):
                sensex_flow.relabel(out["voice"])
```

with

```python
            if rep.get("flow_src"):
                sensex_flow.relabel(out["voice"])
            _msg_voice(tr, out["voice"])                 # the stream's TRADE kind: a change of state, once (fail-soft)
```

**(d) The route.** Replace

```python
        elif urlsplit(self.path).path == "/api/read":
```

with

```python
        elif urlsplit(self.path).path == "/api/messages":
            # THE MESSAGE STREAM (messages.py, A101): NOW per index + today's messages written after ?since= (epoch s), from
            # the pass's memory -- never computed on the request. Display only; never a 500.
            try:
                since = float((parse_qs(urlsplit(self.path).query).get("since") or ["0"])[0])
            except ValueError:
                since = 0.0
            self._json(json.dumps(_msg_reply(since), ensure_ascii=False, default=str).encode())
        elif urlsplit(self.path).path == "/api/read":
```

**(e) Mock isolation.** Replace

```python
    global VALIDATE_DIR, IMPORT_DIR
    VALIDATE_DIR = os.path.join(mock, "validate")                   # F12: Validate's press log (_validate_press)
    IMPORT_DIR = os.path.join(mock, "receipts")                     # F13a: the tradebook import marks (_receipts_import)
```

with

```python
    global VALIDATE_DIR, IMPORT_DIR, MSG_DIR
    VALIDATE_DIR = os.path.join(mock, "validate")                   # F12: Validate's press log (_validate_press)
    IMPORT_DIR = os.path.join(mock, "receipts")                     # F13a: the tradebook import marks (_receipts_import)
    MSG_DIR = os.path.join(mock, "messages")                        # A101: the message stream's record (_msg_write)
```

**(f) The thread, in `main()`.** Replace

```python
                         daemon=True, name="daylog").start()
        if poller is not None:
```

with

```python
                         daemon=True, name="daylog").start()
        # THE MESSAGE STREAM (A101): its pass on its own thread, live and --mock-chain alike (a mock run's record is under
        # data/mock/, _isolate_mock_writers)
        threading.Thread(target=_msg_loop, daemon=True, name="messages").start()
        if poller is not None:
```

**(g) Check the bytes of `server.py`** with the Global Constraints command: both numbers equal.

**(h) `conftest.py`.** Replace

```python
             "server.IMPORT_DIR": "receipts",                 # F13a: the tradebook import marks (server._receipts_import)
```

with

```python
             "server.IMPORT_DIR": "receipts",                 # F13a: the tradebook import marks (server._receipts_import)
             "server.MSG_DIR": "messages",                    # A101: the message stream's record (server._msg_write)
```

Check the bytes of `conftest.py`.

- [ ] **Step 4: Run the new file and the guards, and see them pass.**

Run: `python -m pytest -q test_messages_server.py test_messages.py test_leak_guard.py test_feed_health.py test_hold_route.py`
Expected: all pass.
- `test_leak_guard.py` now has one more case, `server.MSG_DIR`.
- `test_hold_route.py` exercises `_in_trade`, and `_msg_voice` writes only under the tmp `MSG_DIR`.

---

### Task 3: `telegram_out.py`: config, the gate, dedupe, the cap, the queue + thread, urllib, no token in logs

**Files:**
- Create: `telegram_out.py`
- Modify: `server.py`:
  - the import;
  - `_msg_write` (one line);
  - `_isolate_mock_writers` (one line);
  - `main()` (two lines).
- Modify: `conftest.py` (`STR_PATHS`: one line).
- Test: `test_telegram_out.py` (new); append one test to `test_messages_server.py`.

**Interfaces:**
- Produces the `telegram_out.*` names listed in Interfaces.
- `offer(msgs, now)` is called by `server._msg_write` with the newly written messages. It is a no-op until `start()`.
- Consumes: `messages._msg` (tests), `chain_live.IST`.

- [ ] **Step 1: Write the failing tests.** Create `test_telegram_out.py`:

```python
"""telegram_out.py (spec 2026-10-25-message-window-telegram §4): OFF without chat.txt, the token read from its line, the
alert subset, the gate (market hours, a fresh close, once per key), 6 sends a minute with the rest as one batch, the date on
the day's first line, two retries, a failure logged once an hour and never with the token. No test reaches the network:
every send goes through a faked `_open`, and conftest points DIR at tmp_path, so her real telegr/ is never read."""
import json
import os
import queue
import urllib.error
import urllib.parse
from datetime import datetime

import pytest

import messages
import telegram_out as tg
from chain_live import IST

FAKE = "4242" + ":" + "x" * 35        # token-shaped, made up here: never hers


def at(h, m, s=0, day="2026-10-23"):
    y, mo, d = (int(x) for x in day.split("-"))
    return datetime(y, mo, d, h, m, s, tzinfo=IST)


def msg(t, kind="SETUP", word="FADE-D BUY", ev=None):
    m = messages._msg(t, "NIFTY", kind, 1, word, "4/7 saath", None, None)
    return dict(m, ev=ev) if ev else m


class _R:
    """A urlopen() reply."""
    def __init__(self, body):
        self.b = json.dumps(body).encode()

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setattr(tg, "_ON", False)
    monkeypatch.setattr(tg, "_Q", queue.SimpleQueue())
    monkeypatch.setattr(tg, "_SENT", set())
    monkeypatch.setattr(tg, "_HELD", [])
    monkeypatch.setattr(tg, "_USED", {"minute": None, "n": 0, "day": None})
    monkeypatch.setattr(tg, "_FAIL", {"at": 0.0})
    monkeypatch.setattr(tg, "_open", lambda *a, **k: pytest.fail("a test reached the network seam unfaked"))


def _config(chat=True):
    os.makedirs(tg.DIR, exist_ok=True)
    with open(os.path.join(tg.DIR, "bot.txt"), "w", encoding="utf-8") as f:
        f.write(f"key: {FAKE}\nbot: https://t.me/tapemap_x_bot\n")
    if chat:
        with open(os.path.join(tg.DIR, "chat.txt"), "w", encoding="utf-8") as f:
            f.write("777\n")


def test_off_without_chat_txt_and_the_token_is_found_on_its_line():
    assert tg.config() is None                                           # nothing there at all
    _config(chat=False)
    assert tg.token() == FAKE and tg.chat() is None and tg.config() is None
    _config()
    assert tg.config() == (FAKE, "777")


def test_the_alert_subset():
    """SETUP; READ to LEAN / TREND, or a QUIT; TRADE WARN / EXIT; every HEALTH. LEG, DIN, RANGE / WAIT churn stay home."""
    assert tg.wants(msg("10:05")) and tg.wants(msg("09:20", "HEALTH", "TapeMap live"))
    assert tg.wants(msg("10:05", "READ", "RANGE → LEAN ▼", "WORD"))
    assert tg.wants(msg("10:05", "READ", "TREND ▼ · flow+fuel → TREND ▼", "WORD"))
    assert not tg.wants(msg("10:05", "READ", "LEAN ▼ → RANGE", "WORD"))
    assert not tg.wants(msg("10:05", "READ", "TREND ▼ → WAIT", "WORD"))
    assert tg.wants(msg("10:10", "READ", "22,600 PE likhne wale bhage", "QUIT"))
    assert not tg.wants(msg("10:05", "LEG", "▼ leg jaari")) and not tg.wants(msg("10:05", "DIN", "din CHOP"))
    assert tg.wants(msg("11:07", "TRADE", "WARN")) and tg.wants(msg("11:07", "TRADE", "EXIT"))
    assert not tg.wants(msg("11:07", "TRADE", "TIGHTEN"))


def test_the_gate_is_market_hours_and_a_fresh_close():
    assert tg.gate(msg("10:05"), at(10, 6)) and tg.gate(msg("10:05"), at(10, 15))
    assert not tg.gate(msg("10:05"), at(10, 16))                         # a restart's rebuilt morning stays in the window
    assert not tg.gate(msg("10:05"), at(10, 6, day="2026-10-24"))        # Saturday
    assert not tg.gate(msg("09:10"), at(9, 12)) and not tg.gate(msg("15:35"), at(15, 40))
    assert tg.gate(msg("15:35"), at(15, 39))


def test_offer_queues_each_message_once_and_only_when_started(monkeypatch):
    assert tg.offer([msg("10:05")], at(10, 6).timestamp()) == 0           # not started: the suite, a mock run
    monkeypatch.setattr(tg, "_ON", True)
    m = msg("10:05")
    assert tg.offer([m, m, msg("10:05", "LEG", "▼ leg jaari"), msg("09:40")], at(10, 6).timestamp()) == 1
    assert tg.offer([m], at(10, 7).timestamp()) == 0
    assert tg._Q.get_nowait() == "10:05  NIFTY  FADE-D BUY · 4/7 saath" and tg._Q.empty()


def test_the_cap_is_six_a_minute_and_the_rest_go_as_one_batch():
    L = [f"l{i}" for i in range(9)]
    assert tg.plan(L, 0) == (["l0", "l1", "l2", "l3", "l4", "+4 ek saath:\nl5\nl6\nl7\nl8"], 6)
    assert tg.plan(L[:3], 4) == (["l0", "+2 ek saath:\nl1\nl2"], 2)
    assert tg.plan(L[:3], 6) == ([], 0) and tg.plan([], 0) == ([], 0) and tg.plan(L[:2], 0) == (["l0", "l1"], 2)


def test_drain_sends_the_days_first_line_with_the_date(monkeypatch):
    _config()
    sent = []

    def fake(req, timeout=None):
        assert timeout == tg.TIMEOUT_S
        sent.append(urllib.parse.parse_qs(req.data.decode()))
        return _R({"ok": True})
    monkeypatch.setattr(tg, "_open", fake)
    tg._Q.put("10:05  NIFTY  FADE-D BUY")
    tg._Q.put("10:06  NIFTY  b")
    assert tg._drain(at(10, 6, 2).timestamp()) == ["Fri 23 Oct\n10:05  NIFTY  FADE-D BUY", "10:06  NIFTY  b"]
    assert [s["chat_id"] for s in sent] == [["777"], ["777"]]
    tg._Q.put("x")
    assert tg._drain(at(10, 7).timestamp()) == ["x"]                      # same day: no second date
    for i in range(7):
        tg._Q.put(f"y{i}")
    out = tg._drain(at(10, 7, 30).timestamp())                            # 10:07 has sent one: 5 sends left
    assert out == ["y0", "y1", "y2", "y3", "+3 ek saath:\ny4\ny5\ny6"] and len(sent) == 8


def test_a_failing_send_retries_twice_and_logs_once_an_hour_without_the_token(monkeypatch, caplog):
    calls = []

    def down(req, timeout=None):
        calls.append(req.full_url)
        raise urllib.error.URLError(f"no route to {req.full_url}")       # the URL carries the token
    monkeypatch.setattr(tg, "_open", down)
    with caplog.at_level("WARNING", logger="tapemap"):
        assert tg.send(FAKE, "777", "x") is False and len(calls) == 3
        assert tg.send(FAKE, "777", "x") is False and len(calls) == 6
    assert caplog.text.count("telegram: a send failed") == 1
    assert FAKE not in caplog.text and "<token>" in caplog.text
    seq = iter([urllib.error.URLError("flaky"), None])

    def flaky(req, timeout=None):
        e = next(seq)
        if e:
            raise e
        return _R({"ok": True})
    monkeypatch.setattr(tg, "_open", flaky)
    assert tg.send(FAKE, "777", "x") is True
```

Append to `test_messages_server.py`:

```python
def test_new_lines_reach_the_telegram_queue_once(monkeypatch):
    """server._msg_write hands every NEW message to telegram_out.offer; its subset and freshness gate pick the two that go."""
    import queue
    import telegram_out
    monkeypatch.setattr(telegram_out, "_ON", True)
    monkeypatch.setattr(telegram_out, "_Q", queue.SimpleQueue())
    monkeypatch.setattr(telegram_out, "_SENT", set())
    server._msg_pass(at(10, 0))
    server._msg_pass(at(10, 1))                                          # nothing new: nothing offered
    got = []
    while not telegram_out._Q.empty():
        got.append(telegram_out._Q.get_nowait())
    assert got == ["09:55  NIFTY  WAIT → LEAN ▼ · 5/7 saath · flip 22,800s", "10:00  HEALTH  TapeMap live · recording ok"]
```

- [ ] **Step 2: Run them and see them fail.**

Run: `python -m pytest -q test_telegram_out.py test_messages_server.py::test_new_lines_reach_the_telegram_queue_once`
Expected:
- `test_telegram_out.py` ERRORS at collection, `ModuleNotFoundError: No module named 'telegram_out'`;
- the server test FAILS (also on that import, or with `got == []`).

- [ ] **Step 3: Implement.** Create `telegram_out.py`:

```python
"""telegram_out.py -- THE MESSAGE STREAM's outbound Telegram alerts (spec docs/superpowers/specs/
2026-10-25-message-window-telegram-design.md §4; NOTEPAD A101).

OUTBOUND ONLY: sendMessage to her one chat. No command is ever read back; nothing here places an order. The text is the
window's own line (messages.line), the day's first one prefixed with the date.
  WHAT    `wants`: SETUP; READ to LEAN / TREND, or a QUIT; TRADE WARN / EXIT; every HEALTH line. LEG, DIN and RANGE /
          WAIT churn stay in the window.
  GATE    `gate`: weekdays 09:15-15:40 IST, and the message's own close within FRESH_S of now -- a restart rebuilds the
          morning into the window, never into her phone. `offer` queues each (day, key) once.
  CAP     `plan`: at most CAP sends a minute; past that, the rest of the minute go as ONE batch message.
  SENDER  one daemon thread (`start`, from server.main, never under --mock-chain), stdlib urllib, TIMEOUT_S, RETRIES more
          tries; a failure is logged at most once an hour and never raised into the server.
CONFIG (hers, git-ignored telegr/): bot.txt holds the token (the token-shaped line; a "key: " prefix is fine), chat.txt the
chat id (tools/telegram_setup.py writes it). No chat.txt: OFF, and the window still works. THE TOKEN lives only in the
request URL: never in a log line, a message, or any text this module writes (`scrub`).
"""
from __future__ import annotations

import json
import logging
import os
import queue
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime

from chain_live import IST

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegr")
API = "https://api.telegram.org/bot{}/{}"
TOKEN_RE = re.compile(r"\d+:[A-Za-z0-9_-]{30,}")
CAP, TIMEOUT_S, RETRIES = 6, 8, 2
FRESH_S, QUIET_S, TICK_S = 600, 3600, 2       # a line older than 10 min is not sent; a failure logged once an hour
OPEN_HM, CLOSE_HM = "09:15", "15:40"
log = logging.getLogger("tapemap")
_open = urllib.request.urlopen                # the one network seam: tests replace it, so no test reaches Telegram
_ON = False
_Q = queue.SimpleQueue()                      # lines offered, for the sender thread
_SENT = set()                                 # (day, key) already queued
_HELD = []                                    # over this minute's cap: the next minute's first send
_USED = {"minute": None, "n": 0, "day": None}
_FAIL = {"at": 0.0}


def scrub(s):
    """Any token-shaped text out of a string bound for a log or a screen."""
    return TOKEN_RE.sub("<token>", str(s))


def token():
    """Her bot token from telegr/bot.txt (its token-shaped line), or None."""
    try:
        with open(os.path.join(DIR, "bot.txt"), encoding="utf-8") as f:
            m = TOKEN_RE.search(f.read())
    except OSError:
        return None
    return m.group(0) if m else None


def chat():
    """Her chat id from telegr/chat.txt, or None (Telegram is OFF)."""
    try:
        with open(os.path.join(DIR, "chat.txt"), encoding="utf-8") as f:
            c = f.read().strip()
    except OSError:
        return None
    return c if re.fullmatch(r"-?\d+", c) else None


def config():
    """(token, chat id) when both are there, else None: OFF."""
    t, c = token(), chat()
    return (t, c) if t and c else None


def wants(m):
    """The alert subset (spec §4)."""
    k, w = m.get("kind"), str(m.get("word") or "")
    if k in ("SETUP", "HEALTH"):
        return True
    if k == "TRADE":
        return w in ("WARN", "EXIT")
    return k == "READ" and (m.get("ev") == "QUIT" or w.split(" → ")[-1].startswith(("LEAN", "TREND")))


def gate(m, d):
    """Weekdays 09:15-15:40 IST (d: an aware IST datetime), and the message's own close within FRESH_S of d."""
    if d.weekday() >= 5 or not OPEN_HM <= d.strftime("%H:%M") < CLOSE_HM:
        return False
    try:
        h, mi = (int(x) for x in str(m.get("t"))[:5].split(":"))
    except ValueError:
        return False
    return -60 <= d.hour * 3600 + d.minute * 60 + d.second - (h * 3600 + mi * 60) <= FRESH_S


def offer(msgs, now=None):
    """server._msg_write hands every newly written message here. The subset that passes the gate is queued once per (day,
    key); a no-op until start() (the suite, a --mock-chain run). -> how many were queued."""
    if not _ON:
        return 0
    d = datetime.fromtimestamp(time.time() if now is None else now, IST)
    n = 0
    for m in msgs:
        k = (d.strftime("%Y-%m-%d"), m.get("key"))
        if wants(m) and gate(m, d) and k not in _SENT:
            _SENT.add(k)
            _Q.put(m["line"])
            n += 1
    return n


def plan(lines, used):
    """(texts, sends) for one tick: every line alone while this minute has room under CAP; past it, the rest go as ONE batch
    message; with no room left, nothing until the next minute."""
    free = CAP - used
    if not lines or free <= 0:
        return [], 0
    if len(lines) <= free:
        return list(lines), len(lines)
    rest = lines[free - 1:]
    return list(lines[:free - 1]) + [f"+{len(rest)} ek saath:\n" + "\n".join(rest)], free


def send(tok, chat_id, text):
    """One sendMessage, RETRIES more tries on failure -> True when Telegram said ok. Never raises."""
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}).encode()
    err = "no reply"
    for _ in range(1 + RETRIES):
        try:
            with _open(urllib.request.Request(API.format(tok, "sendMessage"), data=body), timeout=TIMEOUT_S) as r:
                rep = json.loads(r.read().decode("utf-8") or "{}")
            if rep.get("ok"):
                return True
            err = f"Telegram said: {rep.get('description') or 'not ok'}"
        except Exception as e:  # noqa: BLE001 -- a send never raises into the server
            err = f"{type(e).__name__}: {e}"
    _failed(err)
    return False


def _failed(err, now=None):
    t = time.time() if now is None else now
    if t - _FAIL["at"] >= QUIET_S:
        _FAIL["at"] = t
        log.warning("telegram: a send failed (%s); the window still has every message", scrub(err))


def _drain(now=None):
    """One sender tick: the queued lines, sent within the cap (the day's first with the date). -> the texts sent."""
    d = datetime.fromtimestamp(time.time() if now is None else now, IST)
    minute, day = d.strftime("%Y-%m-%d %H:%M"), d.strftime("%Y-%m-%d")
    if _USED["minute"] != minute:
        _USED.update(minute=minute, n=0)
    while True:
        try:
            _HELD.append(_Q.get_nowait())
        except queue.Empty:
            break
    texts, n = plan(_HELD, _USED["n"])
    if not texts:
        return []
    _HELD.clear()
    _USED["n"] += n
    cfg = config()
    if cfg is None:                               # chat.txt missing: OFF -- the lines stay in the window only
        return []
    if _USED["day"] != day:
        _USED["day"] = day
        texts[0] = f"{d.strftime('%a %d %b')}\n{texts[0]}"
    for x in texts:
        send(cfg[0], cfg[1], x)
    return texts


def _run():
    while True:
        time.sleep(TICK_S)
        try:
            _drain()
        except Exception as e:  # noqa: BLE001 -- the sender never dies and never raises into the server
            _failed(f"sender tick: {type(e).__name__}: {e}")


def start():
    """server.main calls this once, live only (never under --mock-chain): the sender thread. While chat.txt is missing
    Telegram stays OFF; tools/telegram_setup.py can write it at any time, with no restart. Logs ON / OFF, never the token."""
    global _ON
    if _ON:
        return
    _ON = True
    threading.Thread(target=_run, name="telegram", daemon=True).start()
    log.info("telegram: %s", "ON -- alerts go to her chat" if config()
             else "OFF -- no telegr/chat.txt yet (python tools/telegram_setup.py)")
```

Then make four replacements in `server.py` (CRLF).

**(a) The import.** Replace

```python
import messages                  # THE MESSAGE STREAM (A101): one line per change of an existing read, GET /api/messages
```

with

```python
import messages                  # THE MESSAGE STREAM (A101): one line per change of an existing read, GET /api/messages
import telegram_out              # ...and its outbound Telegram subset (telegr/; OFF without chat.txt, never under --mock-chain)
```

**(b) `_msg_write` offers the new lines.** Replace

```python
        _MSG["items"].extend(new)
        _MSG["keys"].update(m["key"] for m in new)
    return new
```

with

```python
        _MSG["items"].extend(new)
        _MSG["keys"].update(m["key"] for m in new)
    telegram_out.offer(new, now)                   # the alert subset, gated and capped there; a no-op until start()
    return new
```

**(c) Mock isolation.** Replace

```python
    MSG_DIR = os.path.join(mock, "messages")                        # A101: the message stream's record (_msg_write)
```

with

```python
    MSG_DIR = os.path.join(mock, "messages")                        # A101: the message stream's record (_msg_write)
    telegram_out.DIR = os.path.join(mock, "telegr")                 # A101: a rehearsal never finds her chat (and never starts)
```

**(d) `main()` starts the sender, live only.** Replace

```python
        threading.Thread(target=_msg_loop, daemon=True, name="messages").start()
```

with

```python
        threading.Thread(target=_msg_loop, daemon=True, name="messages").start()
        if not mock_chain:                           # a rehearsal never reaches her phone
            telegram_out.start()
```

Check the bytes of `server.py`.

**(e) `conftest.py`.** Replace

```python
             "server.MSG_DIR": "messages",                    # A101: the message stream's record (server._msg_write)
```

with

```python
             "server.MSG_DIR": "messages",                    # A101: the message stream's record (server._msg_write)
             "telegram_out.DIR": "telegr",                    # A101: her token + chat id -- no test can read the real ones
```

Check the bytes of `conftest.py`.

- [ ] **Step 4: Run them and see them pass.**

Run: `python -m pytest -q test_telegram_out.py test_messages_server.py test_messages.py test_leak_guard.py`
Expected: all pass. `test_leak_guard.py` now has one more case, `telegram_out.DIR`, under `tmp_path` and under `data/mock`.

---

### Task 4: `tools/telegram_setup.py`: her chat id, once

**Files:**
- Create: `tools/telegram_setup.py`
- Test: `test_telegram_setup.py`

**Interfaces:**
- Consumes: `telegram_out.token`, `API`, `TIMEOUT_S`, `DIR`, `send`, `scrub`, and the `_open` seam (looked up at call time, so a test's fake applies).
- Produces:
  - `telegram_setup.latest_private(updates) -> (chat_id: str, first_name: str) | None`;
  - `telegram_setup.main() -> int` (0: saved and sent).

- [ ] **Step 1: Write the failing tests.** Create `test_telegram_setup.py`:

```python
"""tools/telegram_setup.py: the newest PRIVATE chat from getUpdates becomes telegr/chat.txt and hears "TapeMap connected ✓";
the token is never printed. A fake opener (no network), and conftest points telegram_out.DIR at tmp_path."""
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import telegram_out as tg  # noqa: E402
import telegram_setup  # noqa: E402

FAKE = "4242" + ":" + "y" * 35        # token-shaped, made up here
UPD = {"ok": True, "result": [
    {"update_id": 5, "message": {"chat": {"id": -100, "type": "group", "title": "desk"}, "text": "/start"}},
    {"update_id": 7, "message": {"chat": {"id": 777, "type": "private", "first_name": "Mary"}, "text": "/start"}},
    {"update_id": 6, "message": {"chat": {"id": 555, "type": "private", "first_name": "Old"}, "text": "hi"}}]}


class _R:
    def __init__(self, body):
        self.b = json.dumps(body).encode()

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _bot():
    os.makedirs(tg.DIR, exist_ok=True)
    with open(os.path.join(tg.DIR, "bot.txt"), "w", encoding="utf-8") as f:
        f.write(f"key: {FAKE}\nbot: https://t.me/tapemap_x_bot\n")


def _fake(updates, sent):
    def fake(req, timeout=None):
        if req.data is None:                                    # GET getUpdates
            assert req.full_url.endswith("/getUpdates")
            return _R(updates)
        sent.append(urllib.parse.parse_qs(req.data.decode()))   # POST sendMessage
        return _R({"ok": True})
    return fake


def test_the_newest_private_chat_is_saved_and_told_connected_without_printing_the_token(monkeypatch, capsys):
    _bot()
    sent = []
    monkeypatch.setattr(tg, "_open", _fake(UPD, sent))
    assert telegram_setup.main() == 0
    with open(os.path.join(tg.DIR, "chat.txt"), encoding="utf-8") as f:
        assert f.read() == "777\n"
    assert sent == [{"chat_id": ["777"], "text": ["TapeMap connected ✓"], "disable_web_page_preview": ["true"]}]
    out = capsys.readouterr()
    assert "Mary" in out.out and FAKE not in out.out + out.err


def test_no_private_chat_writes_nothing_and_says_send_start(monkeypatch, capsys):
    _bot()
    sent = []
    monkeypatch.setattr(tg, "_open", _fake({"ok": True, "result": UPD["result"][:1]}, sent))
    assert telegram_setup.main() == 1
    assert not os.path.exists(os.path.join(tg.DIR, "chat.txt")) and sent == []
    assert "/start" in capsys.readouterr().out
```

- [ ] **Step 2: Run them and see them fail.**

Run: `python -m pytest -q test_telegram_setup.py`
Expected: an ERROR at collection, `ModuleNotFoundError: No module named 'telegram_setup'`.

- [ ] **Step 3: Implement.** Create `tools/telegram_setup.py`:

```python
"""tools/telegram_setup.py -- connect TapeMap's Telegram alerts to her chat, once (spec 2026-10-25-message-window-telegram §4).

    1. In Telegram, send /start to her bot (Telegram keeps it for getUpdates about 24 hours).
    2. python tools/telegram_setup.py

Reads the token from telegr/bot.txt (telegram_out.token), asks getUpdates for the newest PRIVATE chat that wrote to the
bot, writes its id to telegr/chat.txt (git-ignored, as bot.txt) and sends "TapeMap connected ✓" there. The token is never
printed, logged or written anywhere else. Outbound only: the bot is never asked to read commands later.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import telegram_out  # noqa: E402

UPDATES_TIMEOUT = telegram_out.TIMEOUT_S


def latest_private(updates):
    """The newest private chat in a getUpdates reply -> (chat id, first name), or None."""
    best = None
    for u in (updates or {}).get("result") or ():
        ch = ((u.get("message") or u.get("edited_message") or {}).get("chat")) or {}
        if ch.get("type") == "private" and ch.get("id") is not None and (best is None or u.get("update_id", 0) > best[0]):
            best = (u.get("update_id", 0), str(ch["id"]), ch.get("first_name") or "")
    return best[1:] if best else None


def main():
    tok = telegram_out.token()
    if not tok:
        print("telegr/bot.txt has no bot-token line -- nothing done.")
        return 1
    try:
        req = urllib.request.Request(telegram_out.API.format(tok, "getUpdates"))
        with telegram_out._open(req, timeout=UPDATES_TIMEOUT) as r:
            got = json.loads(r.read().decode("utf-8") or "{}")
    except Exception as e:  # noqa: BLE001 -- said plainly, the token scrubbed
        print("Telegram did not answer: " + telegram_out.scrub(f"{type(e).__name__}: {e}"))
        return 1
    hit = latest_private(got)
    if not hit:
        print("No private chat has written to the bot lately. Send /start to the bot in Telegram, then run this again.")
        return 1
    chat_id, who = hit
    os.makedirs(telegram_out.DIR, exist_ok=True)
    with open(os.path.join(telegram_out.DIR, "chat.txt"), "w", encoding="utf-8") as f:
        f.write(chat_id + "\n")
    if not telegram_out.send(tok, chat_id, "TapeMap connected ✓"):
        print(f"Saved the chat ({who or 'private chat'}) to telegr/chat.txt, but the test message did not go through "
              "(the reason is above). Run this again.")
        return 1
    print(f"Saved the chat ({who or 'private chat'}) to telegr/chat.txt. Sent: TapeMap connected ✓")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
```

- [ ] **Step 4: Run them and see them pass.**

Run: `python -m pytest -q test_telegram_setup.py test_telegram_out.py`
Expected: all pass.

- [ ] **Step 5: The one real network call in this plan.** Run it once, on her word, because she said she sent /start; spec §4 step 3 lets the controller run it.

Run: `python tools/telegram_setup.py`
Expected, one of two:
- `Saved the chat (<her first name>) to telegr/chat.txt. Sent: TapeMap connected ✓`, and the message is on her phone.
- `No private chat has written to the bot lately…`. Telegram keeps updates about 24 h and her /start was on 25 Oct, so ask her to send /start again, then rerun.

Never print `chat.txt` or `bot.txt` to check it. Check the shape with:

```
python -c "import telegram_out as t; print('ON' if t.config() else 'OFF')"
```

---

### Task 5: The Float flat face: NOW + the last 10 lines; in a trade, the voice on top

**Only after 15:40 IST or on a weekend:** her Vite hot-reloads these files into her live 5173.

**Files:**
- Modify: `ui-v2/src/pro/api.ts` (CRLF):
  - the types;
  - `S`, `s`;
  - the module lets;
  - `poll()`;
  - `msgsOn()`.
- Modify: `ui-v2/src/pro/Float.tsx` (LF):
  - the header;
  - the import;
  - the state and effects;
  - the flat branch;
  - the messages below the voice.
- Modify: `ui-v2/src/hold/hold.css` (CRLF): append.

**Interfaces:**
- Consumes: `GET /api/messages?since=` (Task 2), the existing `j()` / `chime()` / `tone()`, and `ls()` in the Float.
- Produces:
  - `export type Msg`, `NowRow`, `Msgs`;
  - `S.msgs: Msgs | null`;
  - `export function msgsOn(): void`.

**Behaviour:**
- Only the page that mounts the Float (5173's `App.tsx`) polls the stream; `pro.html` does not.
- The sound is the existing `chime → tone` only, on a NEW SETUP line or a TRADE line with word WARN / EXIT. The first read and a reload are silent.
- Flat ✕ is remembered (`pro.float.msgs`), and a bottom-right pill brings it back.
- Unread = `at` after her last look (window focus or pointer over the lines), remembered in `pro.float.seen`.

- [ ] **Step 1: `api.ts` (CRLF).** Make six replacements.

**(a) The types.** Replace

```ts
                      l4?: string; l5?: string; detail?: { text: string; tip?: string | null }[]; map_why?: string }   // the TRADE MAP (trademap.py)
```

with

```ts
                      l4?: string; l5?: string; detail?: { text: string; tip?: string | null }[]; map_why?: string }   // the TRADE MAP (trademap.py)
// THE MESSAGE STREAM (server messages.py, GET /api/messages; spec 2026-10-25-message-window-telegram): the server's lines, verbatim
export type Msg = { key: string; t: string; idx: string; kind: string; dir: number; word: string; agree: string | null; level: string | null
                    why: string | null; at: number; line: string; id?: string }
export type NowRow = { idx: string; dir: number; word: string | null; line: string; why?: string | null }
export type Msgs = { day: string | null; asof: string | null; now: NowRow[]; items: Msg[]; last: number; why: string | null }
```

**(b) `S`.** Replace

```ts
                  lot: Record<string, number> }
```

with

```ts
                  lot: Record<string, number>
                  /** THE MESSAGE STREAM (/api/messages): NOW + today's lines, newest first; polled only where the Float is mounted */
                  msgs: Msgs | null }
```

**(c) The initial store.** Replace

```ts
let s: S = { idx: IDX0, loaded: false, trades: [], tradesWhy: null, fold: {}, flat: null, engineWhy: null, ifin: null, chain: null, feed: null, story: null, validate: null, lot: {} }
```

with

```ts
let s: S = { idx: IDX0, loaded: false, trades: [], tradesWhy: null, fold: {}, flat: null, engineWhy: null, ifin: null, chain: null, feed: null, story: null, validate: null, lot: {}, msgs: null }
```

**(d) The module lets.** Replace

```ts
let busy = false, again = false, timer: number | undefined, ifinK: number | null = null
```

with

```ts
let busy = false, again = false, timer: number | undefined, ifinK: number | null = null
let wantMsgs = false                                                     // msgsOn(): only the page with the Float polls the stream
const MSG0: Msgs = { day: null, asof: null, now: [], items: [], last: 0, why: null }
const MSG_OLD = 'could not check — /api/messages did not answer (server purana hai? restart karein)'
```

**(e) The poll job.** Replace

```ts
  await Promise.all(jobs)
```

with

```ts
  if (wantMsgs) jobs.push((async () => {                                  // THE MESSAGE STREAM: the lines after the last one seen
    const old = s.msgs
    try {
      const r = await j<{ ok: boolean; why?: string; day?: string; asof?: string; now?: NowRow[]; msgs?: Msg[] }>(`/api/messages?since=${old?.last ?? 0}`)
      if (!r.ok) { n.msgs = { ...(old ?? MSG0), why: cc(r.why) }; return }
      const warm = !!old && old.day === r.day, keep = warm ? old!.items : [], have = new Set(keep.map(m => m.key))
      const add = (r.msgs ?? []).filter(m => !have.has(m.key))
      n.msgs = { day: r.day ?? null, asof: r.asof ?? null, now: r.now ?? [], why: null,
                 last: Math.max(warm ? old!.last : 0, ...add.map(m => m.at)),
                 items: [...keep, ...add].sort((a, b) => b.t.localeCompare(a.t) || b.at - a.at).slice(0, 200) }
      const loud = warm ? add.filter(m => m.kind === 'SETUP' || (m.kind === 'TRADE' && (m.word === 'WARN' || m.word === 'EXIT'))) : []
      if (loud.length) chime('msg', loud[loud.length - 1].key)           // the existing tone, once a line across pages; a first read is silent
    } catch { n.msgs = { ...(old ?? MSG0), why: MSG_OLD } }
  })())
  await Promise.all(jobs)
```

**(f) `msgsOn`.** Replace

```ts
export function setIfin(k: number | null) {
  if (k === ifinK) return
  ifinK = k
  if (!FIXTURE) poll()
}
```

with

```ts
export function setIfin(k: number | null) {
  if (k === ifinK) return
  ifinK = k
  if (!FIXTURE) poll()
}

/** the Float (flat or in a trade) shows THE MESSAGE STREAM: only the page that mounts it polls /api/messages */
export function msgsOn() {
  if (wantMsgs) return
  wantMsgs = true
  if (!FIXTURE) poll()
}
```

Check the bytes of `api.ts`: both numbers equal.

- [ ] **Step 2: `Float.tsx` (LF).** Make eight replacements, **in this order** so each old string is unique when it is applied.

**(a) The header.** Replace

```tsx
// in-trade face. It exists only while she is in a trade; the tone is the DESK poller's (sound_id). No order path.
```

with

```tsx
// in-trade face. In a trade the voice is on top; flat (26 Oct, docs/superpowers/specs/2026-10-25-message-window-telegram-
// design.md §3) it is the MESSAGE WINDOW: NOW per index and the last 10 changes, the server's lines verbatim (messages.py),
// with the lines below the voice in a trade too. The tone is the DESK poller's (sound_id; a SETUP / WARN / EXIT line). No order path.
```

**(b) The import.** Replace

```tsx
import { hms, isDown, tradeOp, useStore, type Trade } from './api'
```

with

```tsx
import { hms, isDown, msgsOn, tradeOp, useStore, type Trade } from './api'
```

**(c) The flat window's state.** Replace

```tsx
  const show = open.some(t => !closed.includes(ck(t)))
```

with

```tsx
  const show = open.some(t => !closed.includes(ck(t)))
  // flat: the message window, open unless her ✕ (remembered); the pill bottom-right brings it back
  const [mOpen, setMOpenS] = useState(() => ls('pro.float.msgs') !== '0')
  const setMOpen = (x: boolean) => { ls('pro.float.msgs', x ? '1' : '0'); setMOpenS(x) }
  // unread = written after her last look (the window focused, or the pointer over the lines); kept across reloads
  const [seen, setSeen] = useState(() => Number(ls('pro.float.seen') || 0))
  const lastAt = st.msgs?.last ?? 0
  const look = () => { if (lastAt > seen) { ls('pro.float.seen', String(lastAt)); setSeen(lastAt) } }
```

**(d) The effects.** Replace

```tsx
  useEffect(() => { if (!show && pip) pip.close() }, [show, pip])
```

with

```tsx
  useEffect(() => { if (pip && (open.length ? !show : !mOpen)) pip.close() }, [show, pip, open.length, mOpen])   // flat, her ✕ shuts the pop-out too
  useEffect(() => msgsOn(), [])                                         // this page polls the stream
  useEffect(() => {                                                     // unread lines stay bold until the window is focused
    const ws = [window, pip].filter((w): w is Window => !!w)
    ws.forEach(w => w.addEventListener('focus', look))
    return () => ws.forEach(w => w.removeEventListener('focus', look))
  })
```

**(e) The style moves up** (it is placed above the flat branch in (h)). Replace

```tsx
  const cls = `hv float ${min ? 'col' : 'open'}${red ? ' red' : ''}${pip ? ' in-pip' : ''}`
  const style: CSSProperties | undefined = pip ? undefined
    : pos ? { left: Math.max(0, Math.min(pos.x, window.innerWidth - W - 8)), top: pos.y, right: 'auto', bottom: 'auto', ...(min ? {} : { width: W, maxHeight: 'calc(100vh - 32px)' }) }
    : min ? undefined : { width: W, maxHeight: 'calc(100vh - 32px)' }
```

with

```tsx
  const cls = `hv float ${min ? 'col' : 'open'}${red ? ' red' : ''}${pip ? ' in-pip' : ''}`
```

**(f) The record's alarm moves up** (it is placed in (h)). Replace

```tsx
  // F13 (25 Oct review, A76): the record's two alarms ride the window too, above the voice -- RECORDING NAHI (the server's
  // words) and, after 15:30, the tradebook import; the window exists only in a trade, so flat the 5173 bar carries both
  const rec = intake?.recording && !intake.recording.ok ? intake.recording.text : null
  const alarm = (rec || intake?.tradebook?.due) && <div className="fl-rec">
    {rec && <b className="no">{rec}</b>}
    {intake?.tradebook?.due && <a href={new URL('/pro.html?tab=record', location.href).href} target="_blank" rel="noopener">tradebook aaj import nahi</a>}
  </div>
  const win = <div ref={box} className={cls} style={style}>
```

with

```tsx
  const win = <div ref={box} className={cls} style={style}>
```

**(g) The lines below the voice.** Replace

```tsx
    {msg && <p className="fine" style={{ padding: '4px 12px' }}>{msg} <button type="button" className="link" onClick={() => setMsg(null)}>dismiss</button></p>}
    {!min && (!vc || vOpen) && <>{vc && mapEl}{vc && line}
```

with

```tsx
    {msg && <p className="fine" style={{ padding: '4px 12px' }}>{msg} <button type="button" className="link" onClick={() => setMsg(null)}>dismiss</button></p>}
    {!min && msgsEl}{/* the message stream, below the voice (§3) */}
    {!min && (!vc || vOpen) && <>{vc && mapEl}{vc && line}
```

**(h) The flat branch, and the shared chrome.** Replace

```tsx
  if (!show || !cur) return null

  const others = open.filter(t => t.id !== cur.id)
  const btns = <span className="fl-btns">
    <button type="button" className={`btn btn-sm ${red ? 'btn-out' : ''}`} disabled={busy} onClick={() => out(cur)}>{arm === cur.id ? 'CONFIRM OUT' : "I'M OUT"}</button>
    {!pip ? <button type="button" className="icon-btn" title="Pop out on top of every window" aria-label="Pop out" onClick={popOut}><Ico n="PiP" /></button>
          : <button type="button" className="icon-btn" title="Back into the tab" aria-label="Back into the tab" onClick={() => pip.close()}><Ico n="Undo" /></button>}
    <button type="button" className="icon-btn" title={min ? 'Open' : 'Collapse to one line'} aria-label={min ? 'Open' : 'Collapse'} onClick={() => setMin(!min)}><Ico n={min ? 'ChevronUp' : 'ChevronDown'} /></button>
```

with

```tsx
  // the chrome both faces share: pop out over the broker window, collapse to one line
  const chrome = <>
    {!pip ? <button type="button" className="icon-btn" title="Pop out on top of every window" aria-label="Pop out" onClick={popOut}><Ico n="PiP" /></button>
          : <button type="button" className="icon-btn" title="Back into the tab" aria-label="Back into the tab" onClick={() => pip.close()}><Ico n="Undo" /></button>}
    <button type="button" className="icon-btn" title={min ? 'Open' : 'Collapse to one line'} aria-label={min ? 'Open' : 'Collapse'} onClick={() => setMin(!min)}><Ico n={min ? 'ChevronUp' : 'ChevronDown'} /></button>
  </>
  const style: CSSProperties | undefined = pip ? undefined
    : pos ? { left: Math.max(0, Math.min(pos.x, window.innerWidth - W - 8)), top: pos.y, right: 'auto', bottom: 'auto', ...(min ? {} : { width: W, maxHeight: 'calc(100vh - 32px)' }) }
    : min ? undefined : { width: W, maxHeight: 'calc(100vh - 32px)' }
  // F13 (25 Oct review, A76): the record's two alarms ride the window, flat and in a trade -- RECORDING NAHI (the server's
  // words) and, after 15:30, the tradebook import
  const rec = intake?.recording && !intake.recording.ok ? intake.recording.text : null
  const alarm = (rec || intake?.tradebook?.due) && <div className="fl-rec">
    {rec && <b className="no">{rec}</b>}
    {intake?.tradebook?.due && <a href={new URL('/pro.html?tab=record', location.href).href} target="_blank" rel="noopener">tradebook aaj import nahi</a>}
  </div>
  // THE MESSAGE STREAM (§3): NOW per index, then the last 10 changes, newest first, the server's lines verbatim; bold =
  // written after her last look. LEG / DIN are the background (muted); READ / SETUP / TRADE / HEALTH are the news
  const items = (st.msgs?.items ?? []).slice(0, 10)
  const msgsEl = <div className="fl-msgs" onPointerEnter={look}>
    {!st.msgs && <p className="ml">messages padh rahe…</p>}
    {st.msgs?.why && <p className="ml why">{st.msgs.why}</p>}
    {(st.msgs?.now ?? []).map(r => <div key={r.idx} className="now" title={r.why ?? undefined}>{r.line}</div>)}
    {!!items.length && <hr />}
    {items.map(m => <div key={m.key} title={m.why ?? undefined}
      className={`ml k-${m.kind}${m.kind === 'TRADE' ? ` w-${m.word}` : ''}${m.at > seen ? ' new' : ''}`}>{m.line}</div>)}
    {st.msgs && !st.msgs.why && !items.length && <p className="ml">aaj abhi koi message nahi</p>}
  </div>
  if (!open.length) {                                                  // FLAT: the message window (§3)
    const unread = (st.msgs?.items ?? []).filter(m => m.at > seen).length
    if (!mOpen) return <button type="button" className="hv-back" onClick={() => setMOpen(true)}>messages{unread ? ` · ${unread} naye` : ''}</button>
    const fwin = <div ref={box} className={`hv float ${min ? 'col' : 'open'}${pip ? ' in-pip' : ''}`} style={style}>
      {alarm}
      <div className="fl-line" {...grip}>
        <span className="word fw">MESSAGES</span>
        <span className={`vage${down ? ' dead' : ''}`}>{down ? `NOT LIVE since ${since}` : ageOf(st.msgs?.asof ?? undefined, now)}</span>
        {min && <span className="mid">{items[0]?.line}</span>}
        <span className="fl-btns">{chrome}
          <button type="button" className="icon-btn" title="Close the messages — the pill bottom-right brings them back" aria-label="Close" onClick={() => setMOpen(false)}><Ico n="X" /></button></span>
      </div>
      {msg && <p className="fine" style={{ padding: '4px 12px' }}>{msg} <button type="button" className="link" onClick={() => setMsg(null)}>dismiss</button></p>}
      {!min && msgsEl}
    </div>
    if (pip) return <>{createPortal(fwin, pip.document.body)}<div className="hv-back">The messages are popped out on top <button type="button" onClick={() => pip.close()}>bring them back</button></div></>
    return fwin
  }
  if (!show || !cur) return null

  const others = open.filter(t => t.id !== cur.id)
  const btns = <span className="fl-btns">
    <button type="button" className={`btn btn-sm ${red ? 'btn-out' : ''}`} disabled={busy} onClick={() => out(cur)}>{arm === cur.id ? 'CONFIRM OUT' : "I'M OUT"}</button>
    {chrome}
```

Check the bytes of `Float.tsx`: the first number is 0.

- [ ] **Step 3: `hold.css` (CRLF): append.** Replace

```css
.hv .fl-rec .no{color:var(--negative)}.hv .fl-rec a{color:var(--caution)}
```

with

```css
.hv .fl-rec .no{color:var(--negative)}.hv .fl-rec a{color:var(--caution)}
/* THE MESSAGE WINDOW (26 Oct; spec 2026-10-25-message-window-telegram §3): NOW per index, then the stream -- the server's lines */
.hv .fl-msgs{display:flex;flex-direction:column;gap:2px;padding:var(--s2) var(--s3);border-bottom:1px solid var(--border);font:400 var(--t12)/18px var(--f-num);max-height:360px;overflow-y:auto}
.hv .fl-msgs .now{font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hv .fl-msgs .ml{color:var(--text-primary);overflow-wrap:anywhere}
.hv .fl-msgs .ml.k-LEG,.hv .fl-msgs .ml.k-DIN{color:var(--text-muted)}
.hv .fl-msgs .ml.k-SETUP{color:var(--accent)}
.hv .fl-msgs .ml.w-WARN{color:var(--caution)}.hv .fl-msgs .ml.w-EXIT{color:var(--negative)}
.hv .fl-msgs .ml.new{font-weight:700}
.hv .fl-msgs .ml.why{color:var(--text-muted)}
.hv .fl-msgs hr{border:0;border-top:1px solid var(--border);margin:2px 0}
button.hv-back{cursor:pointer}
```

Check the bytes of `hold.css`: both numbers equal.

- [ ] **Step 4: The type check and the build.** From `tapemap\ui-v2`:

Run: `.\node_modules\.bin\tsc --noEmit -p .`
Expected: no output, exit 0.

Run: `npx vite build`
Expected: `✓ built in …`. It writes only `ui-v2/dist/`, which is git-ignored.

- [ ] **Step 5: The controller's render check (light theme, against a fixture, on her running Vite).**
  1. Do not start Vite. Open a NEW tab, not hers, at `http://127.0.0.1:5173/?fixture=1`. `FIXTURE` stops the pro store's polling, so the store is filled by hand.
  2. Run in the page:

     ```js
     localStorage.setItem('pro.float.seen', '1000'); localStorage.removeItem('pro.float.msgs'); location.reload()
     ```

  3. After the reload, run in the page:

```js
const api = await import('/src/pro/api.ts')
const L = (t, idx, kind, dir, word, rest, at) => ({ key: `${idx}|${kind}|${t}|${word}`, t, idx, kind, dir, word, agree: null, level: null, why: 'fixture', at, line: `${t}  ${idx}  ${word}${rest}` })
api.put({ loaded: true, trades: [], fold: {}, engineWhy: null, msgs: { day: '2026-10-23', asof: new Date().toTimeString().slice(0, 8), last: 2000000003, why: null,
  now: [{ idx: 'NIFTY', dir: -1, word: 'TREND', line: 'NIFTY  TREND ▼ · 5/7 khilaaf · since 13:40' },
        { idx: 'BANKNIFTY', dir: -1, word: 'TREND', line: 'BANKNIFTY  TREND ▼ · 4/7 saath · since 13:35' },
        { idx: 'SENSEX', dir: 0, word: 'RANGE', line: 'SENSEX  RANGE · ▲4/7 · since 13:45' }],
  items: [L('13:15', 'BANKNIFTY', 'SETUP', 1, 'FADE-D BUY', ' · 4/7 saath · 54,189f', 2000000003),
          L('11:15', 'NIFTY', 'READ', -1, 'WAIT → TREND ▼', ' · mila 2/3 · flip 22,500s', 2000000002),
          L('10:50', 'BANKNIFTY', 'LEG', -1, '▼ leg jaari', ' · 5/7 saath', 1),
          L('09:55', 'BANKNIFTY', 'READ', -1, 'RANGE → LEAN ▼', ' · 7/7 saath · flip 54,800s', 1)] } })
```

  4. Expected (screenshot):
     - a light, bordered window bottom-right with **MESSAGES** and an age;
     - three NOW lines (semibold), a rule, four lines newest first;
     - 13:15 bold in the accent blue, 11:15 bold, 10:50 muted, 09:55 plain;
     - no dark surface anywhere.
  5. Move the pointer over the lines: the bold clears.
  6. Click ✕: a `messages` pill is bottom-right. Click it: the window is back.
  7. **In a trade.** Run:

```js
api.put({ trades: [{ id: 'fx1', idx: 'NIFTY', k: 22700, side: 'PE', role: 'long', t0: '10:55:00', p0: 80, qty: 65, exit_t: null }],
  fold: { fx1: { ok: true, id: 'fx1', asof: new Date().toTimeString().slice(0, 8), view: { headline: 'HOLD · writers saath', clause: 'writers saath' },
    voice: { ok: true, state: 'WARN', seq: 2, l1: '▼ 22700 PE · 12 min · +18 pts (₹+1170) · prem +9%', l2: 'stop 22,780f / 22,730s ≈ ₹62',
             l3: 'why: CE front gave up @ 22,780f', trig_t: '11:07', active: [] } } } })
```

     Expected: the WARN voice block (amber edge) on top as today, the same NOW + lines below it, then `detail ▸`.
  8. Clean up:

     ```js
     localStorage.removeItem('pro.float.seen'); localStorage.removeItem('pro.float.msgs')
     ```

     Close the tab.

---

### Task 6: `tools/messages_replay.py <day>` (read-only), then verify on 23 Oct

**Files:**
- Create: `tools/messages_replay.py`
- Test: `test_messages_replay.py`

**Interfaces:**
- Consumes: `messages.build` / `now_rows` and `telegram_out.wants`.
- Produces:
  - `messages_replay.main(day, as_json=False, data=DATA) -> int` (0 ok, 1 no logs). It prints only and writes nothing.
  - `messages_replay._rows(path)`, which is gzip-aware.

- [ ] **Step 1: Write the failing test.** Create `test_messages_replay.py`:

```python
"""tools/messages_replay.py: a day's stream rebuilt READ-ONLY from its READ and DECODE logs, the Telegram lines marked TG."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import messages_replay  # noqa: E402


def test_rebuilds_the_day_and_marks_the_telegram_lines(tmp_path, capsys):
    read = [{"kind": "mark", "idx": "NIFTY", "t": "09:50", "word": "WAIT", "dir": 0},
            {"kind": "mark", "idx": "NIFTY", "t": "09:55", "word": "LEAN", "dir": -1, "flip": 22800.0, "since": "09:55"}]
    dec = [{"idx": "NIFTY", "T": "09:55", "call": {"text": "▼ leg jaari · 5/7", "kind": "JAARI", "d": 0, "c": 5, "of": 7,
                                                   "signs": []}, "leg": {"d": -1, "ext": {}}, "setups": []}]
    for sub, rows in (("read", read), ("decode", dec)):
        os.makedirs(tmp_path / sub)
        (tmp_path / sub / f"{sub}_2026-10-23.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    assert messages_replay.main("2026-10-23", data=str(tmp_path)) == 0
    out = capsys.readouterr().out.splitlines()
    assert "TG 09:55  NIFTY  WAIT → LEAN ▼ · 5/7 saath · flip 22,800s" in out
    assert "   09:55  NIFTY  ▼ leg jaari · 5/7 saath" in out
    assert any(x.startswith("READ 1 · LEG 1 · SETUP 0 · DIN 0 · TG 1") for x in out)
    assert messages_replay.main("2026-10-22", data=str(tmp_path)) == 1         # no logs: said, not an empty stream
```

- [ ] **Step 2: Run it and see it fail.**

Run: `python -m pytest -q test_messages_replay.py`
Expected: an ERROR at collection, `ModuleNotFoundError: No module named 'messages_replay'`.

- [ ] **Step 3: Implement.** Create `tools/messages_replay.py`:

```python
"""tools/messages_replay.py -- READ-ONLY: a day's MESSAGE STREAM rebuilt from its READ and DECODE logs by the server's own
builder (messages.build), oldest first; the lines Telegram would have sent are marked TG (telegram_out.wants -- the 10-min
freshness gate is live-only). TRADE and HEALTH exist only in the live record, data/messages/msg_<day>.jsonl: they are listed
after the stream when the server ran that day, never rebuilt. Writes nothing.

    python tools/messages_replay.py 2026-10-23
    python tools/messages_replay.py 2026-10-23 --json      the /api/messages reply shape (now + msgs), for a face check
"""
import gzip
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import messages  # noqa: E402
import telegram_out  # noqa: E402

DATA = os.path.join(HERE, "data")
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")        # instruments.ENABLED


def _rows(path):
    """A day file's rows (its .gz once daylog compressed it); a torn line is skipped; missing -> nothing."""
    for p in (path, path + ".gz"):
        if os.path.exists(p):
            with (gzip.open if p.endswith(".gz") else open)(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(r, dict):
                        yield r
            return


def main(day, as_json=False, data=DATA):
    rr = list(_rows(os.path.join(data, "read", f"read_{day}.jsonl")))
    dr = list(_rows(os.path.join(data, "decode", f"decode_{day}.jsonl")))
    if not rr and not dr:
        print(f"{day}: no READ or DECODE log on disk -- nothing to rebuild")
        return 1
    ms, now = messages.build(rr, dr), messages.now_rows(rr, dr, IDXS)
    if as_json:                                    # `at` = the order, so a face sorts them as the server would
        print(json.dumps({"ok": True, "day": day, "asof": "15:31:00", "now": now,
                          "msgs": [dict(m, at=i + 1) for i, m in enumerate(ms)]}, ensure_ascii=False))
        return 0
    for m in ms:
        print(("TG " if telegram_out.wants(m) else "   ") + m["line"])
    n = Counter(m["kind"] for m in ms)
    print(f"READ {n['READ']} · LEG {n['LEG']} · SETUP {n['SETUP']} · DIN {n['DIN']} · TG {sum(map(telegram_out.wants, ms))}"
          " (rebuilt; TRADE and HEALTH are live-only)")
    for r in _rows(os.path.join(data, "messages", f"msg_{day}.jsonl")):
        if r.get("kind") in ("TRADE", "HEALTH"):
            print(("TG " if telegram_out.wants(r) else "   ") + str(r.get("line")) + "   [live record]")
    print("NOW at the day's last mark:")
    for r in now:
        print("    " + r["line"])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if a != "--json"]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0], "--json" in sys.argv[1:]))
```

- [ ] **Step 4: Run it and see it pass.**

Run: `python -m pytest -q test_messages_replay.py`
Expected: PASS.

- [ ] **Step 5: Verify on 23 Oct (read-only).**

Run: `python -I tools/messages_replay.py 2026-10-23`

Expected [M] (the builder was run in memory on 23 Oct's real logs on 25 Oct):
- **The count line:** `READ 35 · LEG 46 · SETUP 2 · DIN 12 · TG 32 (rebuilt; TRADE and HEALTH are live-only)`. READ is 12 word changes + 23 QUITs.
- **Among the lines:**

  ```
  TG 09:55  BANKNIFTY  RANGE → LEAN ▼ · 7/7 saath · flip 54,800s
  TG 10:00  BANKNIFTY  LEAN ▼ → TREND ▼ · flow+fuel · 6/7 saath · flip 54,800s
  TG 10:05  BANKNIFTY  TREND ▼ · flow+fuel → TREND ▼ · 6/7 saath · flip 54,700s
  TG 10:45  BANKNIFTY  RIDE SELL · 4/7 saath · 54,298f
  TG 13:15  BANKNIFTY  FADE-D BUY · 4/7 saath · 54,189f
     13:55  NIFTY  TREND ▼ → RANGE · ▼5/7 · box 22,500–22,700s
  ```

- **No churn flood.** None of these show:
  - SENSEX's RANGE re-forms (14:05, 14:25, 14:35, 14:40, 15:30);
  - the same-word re-anchors (BANKNIFTY TREND ▼ 13:35 / 15:30, SENSEX LEAN ▼ 13:40).

Read it as a trader: the 09:55 BNF LEAN ▼ and its upgrade, the RIDE and FADE-D entries, the afternoon's CE writers fleeing. If the count line or any of the six lines differs, stop and report the difference: the A101 row (Task 7) carries these numbers.

---

### Task 7: Verify, record, commit on her word

**Files:**
- Modify: `docs/live/NOTEPAD.md` (CRLF): the A101 row, after A100.
- Modify: `CLAUDE.md` (CRLF): one current-state bullet, and the pytest line.

- [ ] **Step 1: Run the full suite.**

Run: `python -m pytest -q`
Expected:
- 2018 collected (1993 + 25 new: 8 messages, 5 server (4 in Task 2 + 1 in Task 3), 7 telegram, 2 leak-guard cases, 2 setup, 1 replay) = 2016 pass, 1 skipped;
- at most the 1 known flaky A49 test.

Any other failure: stop, and fix the cause.

- [ ] **Step 2: Check the diff.** Run `git diff --stat` and `git status --short`.
  - **Changed:** `server.py` (one block + six short edits), `conftest.py` (2 lines), `Float.tsx`, `api.ts`, `hold.css`, `.gitignore` (the `telegr/` lines, already uncommitted).
  - **New:** `messages.py`, `telegram_out.py`, `tools/telegram_setup.py`, `tools/messages_replay.py`, and the five test files.
  - No file shows a whole-file rewrite.
  - `git status --short telegr` prints NOTHING, and `git check-ignore -q telegr/bot.txt telegr/chat.txt && echo ignored` prints `ignored`.

- [ ] **Step 3: NOTEPAD A101.** Replace

```
| A100 | 25 Oct Phase 4 final review | **The panel's [detail] state is remembered** (`ofd.vdet`): if it was left open before, Monday's first trade shows the full panel until one click shuts it | `panel.js:213` | Tell her; nothing to fix | NOTED |
```

with

```
| A100 | 25 Oct Phase 4 final review | **The panel's [detail] state is remembered** (`ofd.vdet`): if it was left open before, Monday's first trade shows the full panel until one click shuts it | `panel.js:213` | Tell her; nothing to fix | NOTED |
| A101 | 25 Oct (her ask) | **She misses the tool's signals across the screens and cannot tell what it is saying** | spec `docs/superpowers/specs/2026-10-25-message-window-telegram-design.md` | THE MESSAGE STREAM: one line per change of an existing read (READ / LEG / SETUP / DIN / TRADE / HEALTH; agree = DECODE's count, never a %), the Float flat and in a trade, Telegram's subset | FIXED (26 Oct, uncommitted; live at her restart): `messages.py`, `GET /api/messages`, `data/messages/msg_<day>.jsonl`, `telegram_out.py` (OFF until `tools/telegram_setup.py` writes `telegr/chat.txt`), `tools/messages_replay.py`. 23 Oct rebuilt [M]: READ 35 (12 word changes + 23 QUITs) · LEG 46 · SETUP 2 (BNF RIDE SELL 10:45, BNF FADE-D BUY 13:15) · DIN 12 · TG 32; e.g. `09:55 BANKNIFTY RANGE → LEAN ▼ · 7/7 saath · flip 54,800s`. Spec corrections: SETUP from DECODE's chips (confluence_log writes after the window closes, 30–36 min late on 23 Oct); LEG holds through MILA; agree has four answers; Telegram once per message key, only within 10 min of its close. WATCH: QUIT is 23 of 32 Telegram lines on 23 Oct; a dead server sends nothing; no READ lines while 5173 is closed (A95) |
```

Check the bytes of `NOTEPAD.md`.

- [ ] **Step 4: CLAUDE.md.** Make two replacements.

Replace

```
- **The face:** the GoCharting extension v2.12 (0.5.12) in `C:\Users\kaam\Desktop\Go charting\orderflow-desk\dist-v2`. See its `docs/V2-BUILD-REPORT.md`.
```

with

```
- **The face:** the GoCharting extension v2.12 (0.5.12) in `C:\Users\kaam\Desktop\Go charting\orderflow-desk\dist-v2`. See its `docs/V2-BUILD-REPORT.md`.
- **The message stream (26 Oct, A101):**
  - **What:** `messages.py` turns changes in the existing reads into one line each (READ / LEG / SETUP / DIN / TRADE / HEALTH; agree = DECODE's count, never a %).
  - **Where:** a server thread writes each once to `data/messages/msg_<day>.jsonl`, and `GET /api/messages?since=` serves it. The Float shows it flat and in a trade (the voice on top).
  - **Telegram:** `telegram_out.py` sends the subset (SETUP, READ to LEAN / TREND, QUIT, TRADE WARN / EXIT, HEALTH) on weekdays 09:15–15:40, 6 a minute. It is OFF without `telegr/chat.txt` (`tools/telegram_setup.py`), and the token in `telegr/bot.txt` is never logged.
  - **Replay:** `tools/messages_replay.py <day>`.
```

Replace

```
python -m pytest -q            # 1993 collected: 1991 pass, 1 skipped, 1 known flaky (test_v2feed serve-cache, NOTEPAD A49), as of 2026-10-25 (review Phase 4, the cuts)
```

with

```
python -m pytest -q            # 2018 collected: 2016 pass, 1 skipped, 1 known flaky (test_v2feed serve-cache, NOTEPAD A49), as of 2026-10-26 (message window + Telegram, A101)
```

Check the bytes of `CLAUDE.md`.

- [ ] **Step 5: Show Mary, and wait for her word.** Show `git diff --stat` and the diff. Say plainly:
  - **What she will see after her restart:**
    - the floating window stays on screen when she is flat, as MESSAGES: NOW per index and the last 10 changes, newest first;
    - in a trade, the voice on top and the lines below;
    - one tone on a SETUP or a voice WARN / EXIT line.
  - **Telegram:**
    - `TapeMap live · recording ok` at about 09:20;
    - then SETUP, READ to LEAN / TREND, QUIT, TRADE WARN / EXIT, and RECORDING NAHI / OK;
    - at most 6 a minute, nothing older than 10 min;
    - OFF until `chat.txt` exists.
  - **What stays untouched:** every read and rule (§1i–§1q), the engine, the zone machine, the voice's own ladder, every forward log's rows, `trigger_log`.
  - **The limits:**
    - a dead server cannot send a Telegram;
    - no READ lines while 5173 is closed;
    - on 23 Oct, 23 of the 32 Telegram lines would have been QUITs (watch a week).
  - **When it goes live:** at her next restart after a close: `stop.bat`, `start-v2.bat`, and F5 on 5173.

- [ ] **Step 6: Commit, ONLY after she says commit.** First sweep the staged diff for a token, without printing one:

```bash
git add messages.py telegram_out.py tools/telegram_setup.py tools/messages_replay.py test_messages.py test_messages_server.py test_telegram_out.py test_telegram_setup.py test_messages_replay.py server.py conftest.py .gitignore ui-v2/src/pro/Float.tsx ui-v2/src/pro/api.ts ui-v2/src/hold/hold.css docs/live/NOTEPAD.md CLAUDE.md docs/superpowers/specs/2026-10-25-message-window-telegram-design.md docs/superpowers/plans/2026-10-25-message-window-telegram.md
git diff --cached --name-only | grep -i "telegr/" && echo "STOP: a telegr/ file is staged"
git diff --cached | python -c "import re,sys; print('STOP: token-shaped text staged' if re.search(rb'\d{6,}:[A-Za-z0-9_-]{30,}', sys.stdin.buffer.read()) else 'clean')"
```

Expected:
- the `grep` prints nothing;
- the sweep prints `clean`. The tests' fake is built as `"4242" + ":" + "x" * 35` in source, so it is never token-shaped text.

Then commit:

```bash
git commit -m "message window + Telegram alerts (A101)

- messages.py: one line per change of an existing read (READ / LEG / SETUP / DIN / TRADE / HEALTH), agree = DECODE's count
- server: a pass every 20 s writes each once to data/messages/msg_<day>.jsonl; GET /api/messages?since=; _in_trade's voice turns
- telegram_out.py: the alert subset in market hours, fresh closes only, once per key, 6 a minute; OFF without telegr/chat.txt
- tools/telegram_setup.py (chat id from getUpdates), tools/messages_replay.py (read-only)
- the Float: the message window flat, the lines under the voice in a trade

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: After her first restart (read-only checks, in market hours).**
  - `tapemap.log` has `telegram: ON` (or `OFF -- no telegr/chat.txt yet`), and no `message pass` traceback.
  - `data/messages/msg_<today>.jsonl` exists after 09:20. Its first row is `HEALTH  TapeMap live · recording ok`, and it is on her phone.
  - Spot-check three lines against the Read tab and the DECODE block at the same close. Each must say what they said, with the same arrow and count.
