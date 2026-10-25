# Message window + Telegram alerts (design)

| | |
|---|---|
| Date | Sun 25 Oct 2026 |
| Asked | "sometime i miss the signals it genrate and not able to decipher whats its telling, on these many screen so there can be message window which shows what the current market condition is as per the tool. side leaning a confidence score … important is put time in these messages i want this to connect to telegram and send me the signal alerts there" |
| Decided | Confidence = **agreement count** (her pick, 25 Oct), never a %, until 15+ forward outcomes per message kind exist. Design approved by her sending the bot path. |
| Status | Spec — awaiting her review. Nothing built. |

## 0. Rules this obeys

- **Nothing new is invented: no new reads.** Every message is a change in something the tool already computes (STOP S1, S3).
  - THE READ (`read.py`);
  - DECODE (`decode.py`);
  - the setups FADE / RIDE / FADE-D (`confluence_log`);
  - DIN (`onesided.py`);
  - the in-trade voice (`voice.py`);
  - the recording check (`_recording`).
- **Server only, one brain.** The stream is built in the server. The faces and Telegram render it verbatim.
- **Every message carries its time** (the close it is about, HH:MM IST) and a level tagged spot (`s`) or fut (`f`).
- **No % confidence.** Confidence is the agreement count. A measured count ("pichle 18 me 11 chale") is added only once 15+ forward outcomes of that message kind exist (§5e). That is a later, separate task.
- **Terminal copy, not prose.** At most about 10 words a line, Hinglish/English as the faces already speak. Light theme.
- **Advisory only.** No order path, and Telegram is outbound only: no bot commands.
- **Anytime-start.** A restart rebuilds today's stream from the write-once forward logs.

## 1. A message

`{t, idx, kind, dir, word, agree, level, why, at}`, one line on every face:

```
10:05  NIFTY   ▼ LEAN → TREND · 5/7 saath · flip 22,800s
10:35  SENSEX  FADE-D BUY · 73,152f · 4/7 saath
11:07  TRADE   WARN · CE front gave up · stop 22,780f
11:40  NIFTY   ▲ leg thak raha · 3/7 khilaaf
```

- **`t`:** the close the message is about.
- **`at`:** when it was written.
- **`agree`:** DECODE's sign count for that index at that close, `c/of` (of 7).
  - It reads `saath` when DECODE's direction matches the message's.
  - It reads `khilaaf` when DECODE's direction is against the message's.
  - It reads `?` when DECODE could not check.
  - It is never blank and never a 0.

## 2. What creates a message (on change only)

| Kind | When | Source |
|---|---|---|
| READ | THE READ forms, breaks, quits or upgrades (its existing `event` rows: FORM / BREAK / QUIT / UP) | `data/read/read_<day>.jsonl` events |
| LEG | DECODE's `call.kind` changes (JAARI ↔ THAK ↔ MILA) or its direction flips | `data/decode/decode_<day>.jsonl` |
| SETUP | FADE / RIDE / FADE-D enters, with side + level | `data/confluence_log.jsonl` entries |
| DIN | the day type changes (TREND ▲/▼ / CHOP / MIXED) | `decode.onesided` |
| TRADE | the voice's state changes (TIGHTEN / WARN / EXIT), with its stop | the voice at the frame / fold read |
| HEALTH | RECORDING NAHI starts or clears; NOT LIVE | `_recording()`, feed health |

A message is written once by `(day, idx, kind, t, word)` to `data/messages/msg_<day>.jsonl`. That file is the record she can scroll back through.

## 3. The message window: the floating window, always available

- **The change:** today the Float renders only in a trade. It becomes the message window **flat or in a trade**. Closing it stays her choice, and is remembered.
- **Top, NOW:** one row per index, for example:
  - `NIFTY ▼ TREND · 5/7 · since 09:55`
  - `SENSEX — RANGE · 2/7`
- **Below:** the last 10 messages, newest first. Unread lines are bold until the window is focused.
- **In a trade:** the voice block keeps the top, as today, with the messages below it.
- **Sound:** only a SETUP firing, or the voice going WARN / EXIT, through the existing sound ladder. No new sounds.
- **Endpoint:** `GET /api/messages?since=<at>` returns the NOW rows plus the messages after `since`. The Float polls it on its existing poll (8 s bound, one in flight).

## 4. Telegram

- **What is sent:** SETUP; READ to LEAN / TREND, or a QUIT; TRADE WARN / EXIT; RECORDING NAHI (once, and once when it clears); one `TapeMap live · recording ok` at the first message after 09:15.
- **What is not sent:** LEG, DIN and RANGE churn. They stay in the window.
- **Format:** the window's one line, prefixed with the date on the first message of the day.
- **Gate:**
  - weekdays, 09:15–15:40 IST;
  - one send per `(idx, kind, t)`;
  - at most 6 messages a minute, any over that held and sent as one batch line.
- **Sender:**
  - a server thread with a queue;
  - stdlib `urllib` POST to `https://api.telegram.org/bot<token>/sendMessage`;
  - an 8 s timeout and 2 retries;
  - a failure is logged once per hour, never raised, and never delays the market loop.
- **Config (hers, git-ignored):**
  - `tapemap/telegr/bot.txt` holds her bot token (already there);
  - `tapemap/telegr/chat.txt` holds her chat id, written by the setup tool.
  - Neither is ever logged, printed or committed (`telegr/` is in `.gitignore`).
  - With no `chat.txt`, Telegram is off and the window still works.
- **Setup:**
  1. She sends `/start` to her bot in Telegram.
  2. `python tools/telegram_setup.py` reads `bot.txt`, calls `getUpdates`, writes her chat id to `chat.txt`, and sends `TapeMap connected ✓`.
  3. She runs it, or says so and the controller runs it.

## 5. Tests and done

- **Pure builder:** fixture READ / DECODE / setup / DIN / voice rows produce the expected messages. Agreement and its `saath` / `khilaaf` / `?` are covered, as is "on change only" (no repeat on an unchanged close).
- **Write-once log:** a restart rebuilds the same stream.
- **Telegram sender:**
  - a fake HTTP server, so nothing is sent from tests;
  - the market-hours gate, dedupe and rate cap;
  - a missing `chat.txt` means off;
  - the token never appears in any log line.
- **Replay:** `python tools/messages_replay.py 2026-10-23` prints 23 Oct's stream, read-only. Done means a trader reads it and recognises the day: the 09:55 BNF LEAN ▼, the FADE-D entries, no churn flood.
- **Face:** the Float renders flat with NOW and messages, and in a trade with the voice on top. It is checked on 5173 against a fixture, in light theme.

## 6. Out of scope

- A % or measured outcome counts (a later task, once n ≥ 15 per kind).
- Any new read or signal.
- Two-way Telegram commands.
- Alerts outside market hours.
- The GoCharting panel getting the stream (it keeps its own face; reconsider after a week of use).
