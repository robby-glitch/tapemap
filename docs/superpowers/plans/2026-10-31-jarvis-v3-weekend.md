# Jarvis v3 (the weekend build) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** By Monday 2 Nov 09:15 IST, Jarvis speaks one word that holds, decided by the writers, reads what the tool already measures, remembers what it said, reaches her phone and her terminal, takes her commands (including a broker-neutral `/mark`), and carries a fenced model voice behind one seam. Display only. No order path.

**Architecture:** `jarvis.py` stays THE brain (one causal `build(day, idx, upto)` per index per minute); `legs.py` stays the leg. New: a per-minute forward log of what the live frame said (`jarvis_log.py`), a command grammar shared by every face (`jarvis_cmd.py`, `POST /api/jarvis/cmd`), a small card for the faces (`GET /api/jarvis/card`), a terminal face (`tools/jarvis_cli.py`), the model voice behind one seam (`jarvis_voice.py`), and the evening sheet (`tools/jarvis_review.py`). The faces (`jarvis2.html`, the Dext extension) render the card; they decide nothing.

**Tech Stack:** Python 3.13 stdlib (the server is `http.server`-based; no new runtime dependency except the optional `anthropic` SDK, imported lazily), pytest 9, the existing record modules, the static `jarvis2.html` page (no build step), the Dext extension (plain JS, its own node tests).

**Source documents (read the parts named in each task, not all of it):** `docs/kahani/review/JARVIS-REVIEW-2026-10-31.md` (the rating, §5 plan, §6 inventory), `docs/kahani/review/JARVIS-VISION-2026-10-31.md` (§3 capabilities, §4 the decision stack, §5 the brain + the fence), `docs/kahani/review/ALGO-AI-TAKE-2026-10-31.md` (T1–T7), `docs/kahani/review/GAPS-AND-LIVE-CHECKLIST.md` (§3 inputs, §4 the order of the call), `docs/live/NOTEPAD.md` rows A185–A202.

## Global Constraints

Each exists because a past build hurt her. Copy them into every brief; the reviewer checks them.

- **No order path, ever.** Nothing places, routes, pre-fills or suggests an order. Any command containing an order word (`buy`, `sell`, `lots`, `order`, `place`, `square`, `exit now`) is refused with the exact reply `I read, I don't place.` and logged.
- **Never a hit rate, win rate, probability, odds or confidence % on any screen line, log line, Telegram line or card field.** Agreement is a COUNT: `WITH 4 · AGAINST 1`. Fractions of a measured quantity are fine (`range used 0.7 of EM`, `0.35 of the leg`).
- **A missing value is never a zero.** A piece that cannot be read says `could not check — <why>` and is excluded from N. Rule 6: "checked and found nothing", "could not check" and "not shown" are three different sentences.
- **Every price level says spot (`s`) or futures (`f`)**: `22,800s`, `23,051f`, or both `22,800s (22,851f)`. The basis is `fold.BIX_MS` (3-min median), never a constant.
- **English words on screen, the engine's sentences verbatim.** Word table (spec §16.2): WALL, PUSH, TESTED ×n · broke n, HELD / DEFENDED / BROKEN / TRAPPED / BREAK FAILED, FUEL / FUEL SPENT, NEW FLOOR / NEW CEILING, CONTINUES / PINNED / REVERSAL, ROTATE / CONTINUE / UNCLEAR, NO TRADE: quiet / can't see / shock. The leg's words stay TREND / HOLD / WATCH / PALAT? / PALAT / ROTATION / OPENING / NO LEG / CAN'T SEE.
- **Writers first, both ways.** The count's order is GAPS §4: writers (Sides, ±7, the wall ahead, the last answer, trapped) → futures OI → flow and speed → cross-index → her setup. Every read has a buyer line AND a seller line.
- **Causal.** `jarvis.build(day, idx, upto)` reads minutes < upto only; `test_causal_prefix` and `test_the_reads_are_causal_too` must keep passing. A read never changes when later minutes arrive.
- **Thresholds are [I]** with a reason in a comment and a NOTEPAD line; registered rules §1b–§1r (`research-findings.md` §1) are never changed. `legs.py`'s constants may move only as this plan says.
- **Reuse before building; delete copies.** Call the module that already owns a read (`sides`, `fronts`, `handshake`, `effort`, `onesided`, `levels`, `rank`, `confluence_log`, `expression`, `voice`/`hold2`, `trademap.em`, `gamma`). Never add a fourth leg engine, a second fuel, a sixth call-maker.
- **Tests never write under `data/`** (`conftest.py` redirects every DIR to tmp); record tests are skipped when the day's files are absent; a toy frame covers the rule.
- **No live server.** Never start, stop or restart the TapeMap server (8765), Vite (5173) or her 8787 page server. Never read or print `telegr/*`, `.upstox_token`, `keys/*`. A static `python -m http.server` on a port ≥ 8790 for a page check is fine; kill it after.
- **Light theme only.** On screens: numbers, pills, cells of ≤ 6 words; never paragraphs.
- **SENSEX reads NIFTY's order flow + SENSEX's own OI (§1q). BANKNIFTY's chain is too small to answer. She trades on several brokers; Upstox is only the data feed; nothing reads broker positions.**
- **Commit per task on `feature/operator-objects`, locally, never push.** `git add` only the files you touched. Commit message: one line `Jarvis v3 Task N: <what>`, body as needed, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **The measurement bar for the word:** on the 25-day replay (`jarvis.days()`), ACTION-word changes per day ≤ 15 (today 78 / 52 / 79 on 21 / 29 / 30 Oct); PALAT? episodes vs true lean flips (21 Oct today 9 vs 0 → ≤ 2); opening lean announcements before 10:00 on 30 Oct 7 → 0.

---

## File ownership (parallel waves; two agents never touch the same file)

| wave | task | owns |
|---|---|---|
| 1 | 1 BRAIN-A | `jarvis.py`, `legs.py`, `test_jarvis.py`, `test_legs.py`, `tools/jarvis_measure.py` (new) |
| 1 | 2 SERVER | `server.py`, `messages.py`, `telegram_in.py`, `telegram_out.py`, `jarvis_log.py` (new), `jarvis_cmd.py` (new), their tests, `conftest.py` (one DIR line) |
| 1 | 3 FACE | `docs/kahani/review/mockup/jarvis2.html` |
| 1 | 4 TERMINAL + REVIEW | `tools/jarvis_cli.py` (new), `tools/jarvis_review.py` (new), `test_jarvis_cli.py`, `test_jarvis_review.py`, `eod_capture.bat` (one line) |
| 2 | 5 BRAIN-B | `jarvis.py`, `test_jarvis.py` (after Task 1) |
| 2 | 6 BRAIN-C | `jarvis.py`, `legs.py`, `thresholds.py` (new), `jarvis_thresholds.json` (new), tests (after Task 5) |
| 2 | 7 VOICE | `jarvis_voice.py` (new), `test_jarvis_voice.py`, `.gitignore` (one line), `keys/README.md` (new); a 10-line hook in `server.py` and `tools/jarvis_cli.py` (after Tasks 2 and 4) |
| 2 | 8 DEXT | `C:\Users\kaam\Desktop\dext extension\dext-decoder\dext-decoder\{lib/jarvis.js, lib/panel-render.js, lib/overlay.js, manifest.json, test/*}` (after Task 2) |

## The CARD contract (every face, the terminal and the voice read this; Task 2 serves it, Task 1 and 5 fill it)

`GET /api/jarvis/card?idx=NIFTY` → JSON ≤ 10 KB, built from the cached frame of `/api/jarvis` (no extra build). Keys absent in the frame are `null`, never invented.

```json
{"ok": true, "idx": "NIFTY", "day": "2026-11-02", "at": "10:42", "asof": "10:42:51", "live": true,
 "word": "TREND ▼", "state": "HOLD", "lean": -1, "since": "09:56",
 "count": {"with": 4, "against": 1, "N": 6, "unread": 2,
           "pieces": [{"k": "sides", "side": "with", "text": "Sides 10:40 REAL · put writers covering"},
                      {"k": "wf7", "side": "with", "text": "writers ±7 DOWN (CE +12.1L · PE −14.0L / 3 min)"},
                      {"k": "wall_ahead", "side": "against", "text": "wall ahead 22,900s PE 186L BUILDING"},
                      {"k": "answer", "side": "with", "text": "last answer 10:38 22,950s PE ±2 BROKEN"},
                      {"k": "trapped", "side": "?", "text": "could not check — Sides has no closed slot"},
                      {"k": "fut_oi", "side": "with", "text": "fut OI fresh shorts +612 lots / 30 min"},
                      {"k": "speed", "side": "against", "text": "speed ▲ ×2.3 FAST against"},
                      {"k": "all3", "side": "with", "text": "all 3 ▼ (N −14 · BN −31 · SX −52 / 5 min)"},
                      {"k": "setup", "side": "?", "text": "no trigger today"}]},
 "leg": "leg ▼ TREND 103 pts · 2.5σ · TOOT 09:51 · origin 23,135f 09:35 · extreme 23,002f 10:04",
 "pause": {"line": "PAUSE ▼ · hold · clean", "alive": ["…"], "risk": ["…"]},
 "how_much": {"line": "day TREND ▼ · range used 0.5 of EM · σ 26 · VIX could not check · CPR narrow", "rows": ["…"]},
 "where": {"stop": "23,136f (zone)", "pool": "PWH 23,155s", "t1": "pVAH 23,058f", "t2": "PE wall 23,008s (23,051f)", "room": "44 to MAX PAIN"},
 "expression": {"buyer": "buy the PE on a pullback to d1 22,990f, not chased · needs +62 pts today [I ×1.15] · EM left 40 → thin",
                "seller": "sell the CE at / above 23,000s (23,043f): call writers are writing it · IV 13.4 vs RV 9.8 → rich · fold = HOLD v2 line",
                "pick": "seller"},
 "wrong_line": "PALAT? if back past 22,938f (0.35 of the leg) · PALAT at 22,886f",
 "up": "▲ if 23,000s (23,043f) CE breaks (BROKEN) with writers ±7 ▲ → 23,100s", "dn": "▼ if …",
 "walls": {"ce": {"k": 23000, "f": 23043.0, "oi": 147.0, "state": "BUILDING"}, "pe": {"k": 22900, "f": 22943.0, "oi": 186.0, "state": "BUILDING"}},
 "lines": {"q35": 22938.0, "half": 22886.0},
 "no_trade": null,
 "health": {"missing": [], "notes": ["Dext footprint missing since 10:39 · newest 3 min from the book"]},
 "self": "TREND ▼ since 09:56 · −200 so far · PALAT? said 3× · came true 0× · blind 0 min",
 "pushes": [{"t": "10:38", "dir": -1, "lots": -612, "k": 22950, "side": "PE", "ans": "TOOT", "held_at": "10:41", "via": "band"}],
 "watches": [{"id": 3, "level": 22800.0, "frame": "s", "set": "10:12", "hit": null}],
 "voice": null}
```

- `word` = the ACTION word (Task 1). `state` = the leg's raw word. `since` = when the ACTION word last changed.
- `count` (Task 1), `how_much` / `where` / `expression.pick` (Task 5; `null` until then), `self` and `watches` (Task 2), `voice` (Task 7).
- Every level string carries `s` / `f`. No `%` anywhere.

## The COMMAND grammar (Task 2 owns the parser; Tasks 3, 4, 8 send text to it)

`POST /api/jarvis/cmd` body `{"idx": "NIFTY", "text": "<one line>"}` → `{"ok": true|false, "kind": "<kind>", "reply": "<one line>", "lines": ["…"], "state": {"watches": [...], "lines": [...], "zones": [...]}}`. Also `GET /api/jarvis/cmd?idx=` → the same `state`.

| she types | kind | what happens | reply |
|---|---|---|---|
| `line 22750f` / `line 22,700s` | line | persisted level for the day | `line 22,750f drawn` |
| `zone 22680-22720f` | zone | persisted box | `zone 22,680–22,720f drawn` |
| `watch 22800s` (also `watch 22800f`) | watch | persisted; max 10 a day; the senses loop checks spot (s) or fut (f) each pass; on touch → one stream line + Telegram line carrying the card's word, count and last answer; a watch fires once | `watching 22,800s (3 of 10 today)` |
| `remove 22750` / `clear` / `list` | remove / clear / list | persisted removal; list prints lines, zones, watches | `removed 22,750` / `cleared 4` / the list |
| `mark NIFTY 23000 PE buy 325` / `mark SENSEX 74000 CE sell 98.85` (qty optional: `qty 150`) | mark | calls the SAME handler as the Float's `POST /api/hold/trades {op: mark}` (server.py ~4946); her Float mark wins; `src: "cmd"` in the record | `marked NIFTY 23000 PE buy @325 · the voice is on` |
| `flat` / `flat NIFTY` | flat | the same handler, `op: exit` | `flat · receipt 11:42` |
| `note RBI 11:00 today` | note | persisted; shown in the card's `health.notes` for the day and handed to the voice | `noted` |
| `why` / `why?` | why | the frame's `call.why` lines, verbatim | the lines |
| `next` / `what next` | next | `call.up` and `call.dn` | two lines |
| `status` / `now` | status | the card's word · count · leg · health, one line each | the lines |
| `wrong when` / `wrong when?` | wrong | `call.wrong_line` | one line |
| `what if 22800 breaks` / `if 22800` | whatif | if the level is a wall in the card: the matching scenario (`up` / `dn`) and that wall's row; else `I don't have 22,800 in today's frame; nearest: 22,850s PE, 22,750s PE` | lines |
| `ask <free text>` | ask | Task 7's voice; until then `voice not configured — the engine's lines:` + the `why` lines | lines |
| `replay 2026-10-21 10:30` | replay | terminal only (Task 4): GET `/api/jarvis?day=&upto=` and print the card at that minute | the card |
| anything with an order word | refused | logged, nothing done | `I read, I don't place.` |
| anything else | help | the grammar | the list |

Persisted events: `data/jarvis/cmd_<day>.jsonl`, one row per command `{"at": <epoch s>, "t": "HH:MM:SS", "idx": "NIFTY", "kind": "watch", "text": "watch 22800s", "ok": true, "reply": "...", "src": "page|cli|telegram"}`; a watch hit appends `{"kind": "watch_hit", "id": 3, "t": "11:42", "px": 22800.4, "frame": "s", "card": {"word": ..., "count": ..., "answer": ...}}`. Write-once, append-only; a restart rebuilds today's state from the file (anytime-start).

## The CALL LOG contract (Task 2 writes it; Tasks 4, 5 read it)

`data/jarvis/call_<day>.jsonl`, one row per index per frame minute, written by the server right after a LIVE build whose last minute is new for that index (never on replays, never on a cache hit):

```json
{"day": "2026-11-02", "idx": "NIFTY", "t": "10:42", "at": 1793596371, "shown": "10:42:51",
 "word": "TREND ▼", "state": "HOLD", "lean": -1, "since": "09:56",
 "count": {"with": 4, "against": 1, "N": 6}, "fut": 23010.5, "spot": 22967.3,
 "leg": "…", "wrong_line": "…", "missing": ["…"], "notes": ["…"], "blind": false}
```

`jarvis_log.read(day, idx) -> list[dict]` (rows in order; `[]` when absent). `jarvis_log.self_line(rows, fut_now) -> str | None`: `TREND ▼ since 09:56 · −200 so far · PALAT? said 3× · came true 0× · blind 12 min` where "since" is the first row of the current unbroken word, "so far" = `lean × (fut_now − fut at since)`, "said" counts rows whose word starts with `PALAT?` grouped into episodes (consecutive rows), "came true" = episodes followed by a `PALAT` row within 45 min [I], "blind" = rows with `blind: true`. `None` when there are no rows.

---

### Task 1: BRAIN-A — the word that holds, decided by the writers

**Files:**
- Modify: `jarvis.py` (the `call()` function ~line 849; `reads()` ~line 1146; constants block ~line 1048; `calls()` ~line 1076)
- Modify: `legs.py` (constants ~line 30–80; the leg start at `if d_ == 0:` ~line 215; the word block ~line 425–445)
- Create: `tools/jarvis_measure.py`
- Test: `test_jarvis.py`, `test_legs.py`

**Interfaces:**
- Consumes: `jarvis.build(day, idx, upto, fill)` (unchanged signature), `legs.read(d, chain, marks)`.
- Produces (every later task relies on these exact names):
  - `jarvis.count(d, i) -> dict`: `{"with": int, "against": int, "N": int, "unread": int, "pieces": [{"k": str, "side": "with"|"against"|"?", "text": str}]}` for frame `d` at minute index `i`, pieces in GAPS §4 order with the keys `sides, wf7, wall_ahead, answer, trapped, fut_oi, speed, all3, setup`.
  - `jarvis.action_words(d) -> list`: the per-minute ACTION series, also stored as `d["reads"]["action"]`: `[{"word": str, "lean": int, "since": "HH:MM", "count": {...}, "why": str}]` (same length as `d["mins"]`).
  - `jarvis.call(d)` returns, in addition to today's keys: `"word"` = the ACTION word (with the lean arrow as today), `"state"` = the leg's raw word (`row["word"]` of `legs`), `"since"`, `"count"` (the dict above), `"action_why"` (one line: which rule set the word). `"v1"` stays.
  - `legs.LEG_MIN_U = 2.0` (new, [I]); `legs.read` rows before 10:00 carry `word == "OPENING"` with `lean` still set.

**The rules (decided as the trader; every number [I] with the reason beside it):**

1. **The count** (`jarvis.count`). For the lean `L` (+1 / −1 from the legs row; when no leg, use the vote's direction if any, else the count is all `?`). Each piece says with / against / `?`:
   - `sides`: `sides_fuel(slot) == L` → with; `== -L` → against; `CAPPED` (both add) → against a TREND word, `?` otherwise; no slot → `?` ("could not check — Sides has no closed slot").
   - `wf7`: the writers row: `state in (UP, DOWN, BACK)` with `dir == L` → with; `dir == -L` → against; `push == L` (one-sided covering) → with; `PAUSED` → `?` text "writers ±7 PAUSED"; `None` (chain not read) → `?`.
   - `wall_ahead`: the nearest front on the lean's side ahead of spot (CE above for ▲, PE below for ▼): `UNWINDING` → with; `BUILDING` → against; `STALLED` → `?`; none in range → `?` "no wall ahead in 2 steps".
   - `answer`: the last answered push within 15 min: a push the lean's way answered `TOOT`/`PHANS` → with; the lean's way `TIKI` (writers) or `NAHI` → against; against the lean `TIKI`(writers) → with (the floor/cap behind holds); against the lean `TOOT` → against; `GHUSE` (buyers) counts as `?` text "buyers in at the wall"; none → `?`.
   - `trapped`: Sides `uw` (top-2 under water) on the side the lean hurts (CE writers for ▲) `>= 1` → with; `0` → `?`; no slot → `?`.
   - `fut_oi`: the legs DAY line's 30-min quadrant (`d["legs"]["day"]["fut_oi"][i]`): fresh longs / short covering → with for ▲ (mirror ▼); the opposite → against; `None` → `?` "no 30-min story".
   - `speed`: `FAST` the lean's way → with; `FAST` against → against; else `?` (NORMAL/SLOW say nothing).
   - `all3`: `sync.dir == L` → with; `== -L` → against; `0` or `None` → `?`.
   - `setup`: her latest zone3 trigger today (from `d["zone"]` with `px`) still inside its 45-min window: its side agrees with the lean → with; disagrees → against; none → `?`.
   - `N = with + against`; `unread` = pieces with `?`. A `?` never counts against.
2. **The ACTION word** (computed per minute into `reads["action"]`, read by `call()` at the last minute):
   - Candidates come from the leg's raw word: `NO LEG` / `OPENING` / `ROTATION` / `PALAT` pass through as themselves. Before 10:00 (`m < legs.OPEN_M`) the word is `OPENING` with the lean shown (the lean still flips with the geometry; it is not announced as a word).
   - On a TREND leg: raw `TREND` → candidate `TREND` if `with >= against + 2` [I: two more voices than against; the dream mockup's n/N separated 0/11 from 6/10], else `HOLD`; raw `HOLD` → `HOLD` if `with >= against`, else `WATCH`; raw `WATCH` → `WATCH`; raw `PALAT?` → `PALAT?`.
   - **Two closes to change** [I]: the ACTION word is sampled at her 3-min closes (`(m - 555) % 3 == 2`); a new candidate becomes the word only when the SAME candidate appears at two consecutive closes. Exceptions that change at once: `PALAT` (the lean flipped), `CAN'T SEE` (blind), and a `TOOT`/`PHANS` answer AGAINST the lean on the wall behind (EXIT-class; the word becomes `WATCH` at once, its why names the break).
   - `PALAT?` additionally needs the raw `PALAT?` at two consecutive closes OR `retrace >= legs.DEEP` (0.35) [I].
   - `NO TRADE` (quiet / can't see) overrides when `reads["notrade"]` covers the minute and there is no TREND leg; `CAN'T SEE` overrides everything (as today).
   - `since` = the first minute the current word was set. `why` = `"<rule> · WITH n · AGAINST m"` e.g. `TREND: with ≥ against + 2 · WITH 4 · AGAINST 1` or `HOLD: two closes · WITH 2 · AGAINST 2`.
3. **The leg's floor scales with the day** (`legs.py`): `LEG_MIN_U = 2.0` [I]; a leg is `>= max(LEG_MIN, LEG_MIN_U * U)` where `U = max(sd[i], 0.001 * fut[i])` (the function `U_at` already exists). Reason: before 10:00 σ is 10–15 pts, so a 40-pt swing is noise; 30 Oct flipped the lean 7× in 38 min.
4. **SENSEX reads NIFTY's flow (G13)**: in `build()`, when `idx == "SENSEX"` and `data["flow"]` is all `None`, take NIFTY's `flow` for the same day/upto (build NIFTY's `delta`/`flow` series via the same code path; cache it in a module dict for the call) and set `flow_src` to `"N"`; the health note says `flow from NIFTY (§1q)`. **BANKNIFTY (G14)**: when `_readable(day, "BANKNIFTY", …)` is False for the BANKNIFTY frame itself, `health.notes` gets one line `BANKNIFTY chain OI too small to answer pushes (G14)` and `call.missing` carries it; pushes stay in the frame (the faces decide how to draw them).
5. **`tools/jarvis_measure.py`**: `python tools/jarvis_measure.py 2026-10-21 2026-10-29 2026-10-30` or `--all` (every day of `jarvis.days()["NIFTY"]`), `fill=True`, prints one table row per day: `day | minutes | word changes (raw state) | ACTION changes | PALAT? episodes | true flips | opening lean flips (<10:00) | NOT_READ`, and a last line with totals. `--json path` writes the rows. Nothing written under `data/`.

- [ ] **Step 1: Measure before.** Run `python tools/jarvis_measure.py 2026-10-21 2026-10-29 2026-10-30` (write the script first; it must run on today's code and report the raw word as both columns). Paste the table into your report as BEFORE.
- [ ] **Step 2: Failing tests (toy frame).** In `test_jarvis.py` add, using the existing `test_reads_on_a_toy_frame` frame builder as the pattern:

```python
def _toy(n=40, lean=-1):
    """A 40-minute down-leg from 10:00 with every count piece settable."""
    fut = [23100.0 - 3 * i for i in range(n)]
    d = {"mins": [f"{10 + i // 60:02d}:{i % 60:02d}" for i in range(n)], "fut": fut, "fo": [x + 1 for x in fut],
         "fhi": [x + 2 for x in fut], "flo": [x - 2 for x in fut], "spot": [x - 50 for x in fut], "delta": [-40] * n,
         "fvol": [120] * n, "bnf": [54000.0 - 8 * i for i in range(n)], "sx": [74000.0 - 12 * i for i in range(n)],
         "vwap": [23080.0] * n, "sd": [20.0] * n, "oi": [16000.0] * n, "step": 50, "bar": 500,
         "timeline": [{"fuel": None, "fuel_state": "-", "fronts": [{"k": 22900.0, "side": "PE", "state": "UNWINDING", "oi": 90.0, "chg": -4.0, "peak": 94.0}]}] * n,
         "runs": [], "pushes": [], "zone": [], "holes": [], "chain_missing": [], "fights": [],
         "sides": [{"t": "10:05", "c": "ADD", "p": "COV", "word": "REAL", "fuel_side": "pe", "uw": 2}],
         "wf_ce": [12.0] * n, "wf_pe": [-14.0] * n, "upto": "10:40", "live_from": "09:15"}
    return d

def test_count_reads_writers_first_and_never_counts_a_question_mark():
    d = _toy()
    d["reads"] = jarvis.reads(d)
    d["legs"] = {"rows": [{"t": m, "lean": -1, "word": "TREND", "leg": {"dir": -1}} for m in d["mins"]],
                 "day": {"flips": [0] * len(d["mins"]), "fut_oi": [None] * len(d["mins"])}, "pauses": [], "missing": []}
    c = jarvis.count(d, len(d["mins"]) - 1)
    assert [p["k"] for p in c["pieces"]][:5] == ["sides", "wf7", "wall_ahead", "answer", "trapped"]
    assert c["pieces"][0]["side"] == "with" and c["pieces"][2]["side"] == "with"      # Sides REAL pe-fuel, wall ahead UNWINDING
    assert c["pieces"][5]["side"] == "?"                                             # no 30-min story: could not check
    assert c["N"] == c["with"] + c["against"] and c["unread"] >= 1
    assert "%" not in json.dumps(c)

def test_action_word_needs_two_closes_and_palat_at_once():
    d = _toy()
    d["reads"] = jarvis.reads(d)
    rows = [{"t": m, "lean": -1, "word": "TREND" if i < 20 else "WATCH", "leg": {"dir": -1}} for i, m in enumerate(d["mins"])]
    rows[30] = dict(rows[30], word="PALAT", lean=1)
    d["legs"] = {"rows": rows, "day": {"flips": [0] * 30 + [1] * 10, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    a = jarvis.action_words(d)                                   # the per-minute ACTION series reads() stores
    assert a[5]["word"] == "TREND" and a[21]["word"] == "TREND"  # one close saying WATCH does not flip it
    assert a[26]["word"] == "WATCH"                              # two consecutive closes do (10:23 and 10:26)
    assert a[30]["word"] == "PALAT" and a[30]["since"] == "10:30"   # the lean flip speaks at once
    assert all("%" not in x["why"] for x in a)
```

- [ ] **Step 3: Failing tests (the record).** Add, skipped when the day is absent, the plan's bar:

```python
@pytest.mark.skipif(not _has("2026-10-21"), reason="21 Oct record not present")
def test_21oct_the_word_holds_in_a_one_way_leg(record):
    d = jarvis.build("2026-10-21", "NIFTY", None, fill=True)
    words = [c["word"] for c in jarvis.calls(d)]
    changes = sum(1 for a, b in zip(words, words[1:]) if a != b)
    assert changes <= 15, changes                                 # was 78
    palatq = sum(1 for a, b in zip(words, words[1:]) if b.startswith("PALAT?") and not a.startswith("PALAT?"))
    assert palatq <= 2, palatq                                    # was 9 in a 473-pt down leg that reversed 0 times
    assert any(w.startswith("TREND ▼") for w in words[35:50])     # the first-hour trend call survives (09:50-10:05)

@pytest.mark.skipif(not _has("2026-10-30"), reason="30 Oct record not present")
def test_30oct_the_opening_is_not_announced(record):
    d = jarvis.build("2026-10-30", "NIFTY", None, fill=True)
    early = [c["word"] for c in jarvis.calls(d) if c["at"] < "10:00"]
    assert all(w.startswith("OPENING") or w in ("NO LEG",) for w in early), set(early)
```

- [ ] **Step 4: Run them to see them fail.** `python -m pytest test_jarvis.py -q -k "count or action or 21oct or 30oct"` → FAIL (names undefined / counts too high).
- [ ] **Step 5: Implement** `count`, `action_words` (stored as `reads["action"]`), the `call()` changes, the legs floor, G13/G14. Keep every existing key in `call()`'s return. Keep `calls()` fast (it cuts the frame per minute: the action series is already per-minute, so `call()` at a cut reads `reads["action"][i]`).
- [ ] **Step 6: Run** `python -m pytest test_jarvis.py test_legs.py -q` → all pass, including `test_causal_prefix`, `test_the_reads_are_causal_too`, `test_the_call_has_both_expressions_a_wrong_line_and_no_rate`.
- [ ] **Step 7: Measure after.** `python tools/jarvis_measure.py --all` → paste the whole table (25 days) into the report as AFTER. Every day must meet the bar or the report says which day does not and why (do not tune a threshold to one day; two days minimum, and say so).
- [ ] **Step 8: NOTEPAD.** Append ONE row `A203` to `docs/live/NOTEPAD.md` after the `| A202 |` row, CRLF, one line (the file is CRLF; use a small Python binary edit as `docs/kahani/review/scripts` do): what changed, the [I] numbers with reasons, the before/after counts.
- [ ] **Step 9: Commit** `git add jarvis.py legs.py test_jarvis.py test_legs.py tools/jarvis_measure.py docs/live/NOTEPAD.md` and commit `Jarvis v3 Task 1: the word that holds (ACTION word, the WITH/AGAINST count, LEG_MIN 2U, G13/G14)`.

---

### Task 2: SERVER — the call log, the card, the commands, the stream, Telegram

**Files:**
- Create: `jarvis_log.py`, `jarvis_cmd.py`
- Modify: `server.py` (`_jarvis_reply` ~line 4659; the GET router near `/api/jarvis` ~line 5777; the POST router near `/api/hold/` ~line 4945; `_senses_loop` ~line 627 for the watch check; `_msg_pass` ~line 4718; `/api/health`), `messages.py` (`KINDS`, a builder for JARVIS lines), `telegram_out.py` (`wants`), `telegram_in.py` (route commands other than `/now` `/last` to `jarvis_cmd`), `conftest.py` (redirect `jarvis_log.DIR` and `jarvis_cmd.DIR` to tmp)
- Test: `test_jarvis_log.py`, `test_jarvis_cmd.py`, `test_messages.py` (one test), `test_telegram_in.py` (one test), `test_jarvis.py` (the route test pattern `_Cap` from `test_senses_api`)

**Interfaces:**
- Consumes: the cached frame in `server._JARVIS[idx]` (built by `jarvis.build`); `jarvis.call`'s keys incl. Task 1's `word`, `state`, `since`, `count` (be tolerant: a frame built before Task 1 lands lacks them → `null`); the Float's mark handler (`/api/hold/trades {op: mark|exit}`, server.py ~4946: call the same function the POST route calls, never a copy); `telegram_out.offer/plan/send` and its budget; `messages.key/line`.
- Produces: `GET /api/jarvis/card?idx=` (the CARD contract above); `POST /api/jarvis/cmd` and `GET /api/jarvis/cmd?idx=` (the COMMAND grammar above); `jarvis_log.write(day, idx, row)`, `jarvis_log.read(day, idx)`, `jarvis_log.self_line(rows, fut_now)` (the CALL LOG contract); `jarvis_cmd.parse(text) -> {"kind", ...}` (pure), `jarvis_cmd.Day(day)` (state rebuilt from the file; `apply(idx, text, frame, src) -> reply dict`; `check_watches(idx, spot, fut, hm) -> [hits]`); `messages` kind `"JARVIS"` with lines `HH:MM  IDX  TREND ▼ · WITH 4 · AGAINST 1 · since 09:56` on a word change and `HH:MM  IDX  CAN'T SEE · blind since 12:41` once; `/api/health` key `code_changed_since_start: {"n": 2, "files": ["jarvis.py", "legs.py"]}`.

**Rules:**
1. **The log** is written only when `live` and the frame's last minute is new for that idx (keep `_LAST_LOGGED = {idx: "HH:MM"}`); a replay or a cache hit never writes. Write-once per (idx, t): `jarvis_log.write` skips a duplicate. Directory `data/jarvis/`, created on first write. `DIR` is a module constant conftest redirects.
2. **The card** is assembled from the cached frame only (`_JARVIS[idx]`); if there is no frame yet, `{"ok": false, "why": "could not check — no frame built yet"}`. Size: assert ≤ 10 KB in the test with a real 29 Oct frame (skip if absent). `self` comes from `jarvis_log.self_line(read(day, idx), fut_now)`.
3. **Commands**: `jarvis_cmd.parse` is pure (no I/O) and tested on every row of the grammar table above plus the refusals (`buy 5 lots`, `sell PE`, `place order`, `square off now` → kind `refused`, reply exactly `I read, I don't place.`). `Day.apply` persists `line/zone/watch/remove/clear/note/mark/flat` rows and answers the read-only ones from the frame. `mark`/`flat` call the server's existing mark/exit function with a doc `{"idx", "k", "side": "CE"|"PE", "role": "buy"|"sell", "p0": price, "qty": optional, "src": "cmd"}` — read the handler first and pass exactly what it expects; the reply names the trade id. Watch levels carry `frame` `s`/`f`; the senses loop checks hits every pass using the latest spot (chain) and fut (book LTP) for the idx; a hit fires once, writes the `watch_hit` row with the card's `word`, `count` and last `answer`, appends a stream message (kind JARVIS) and offers one Telegram line through the existing budget.
4. **The stream**: `messages.py` gets kind `"JARVIS"` in `KINDS` (after `DIN`, before `TRADE`) built from `jarvis_log.read` rows: one line per `word` change (`since` is the key's `t`), `CAN'T SEE` once per blind stretch, a watch hit line. Telegram `wants()` lets JARVIS lines through within the existing per-day budget (no new budget constant). Nothing else in the stream changes.
5. **Telegram in**: `telegram_in.answer` keeps `/now` and `/last`; any other text from her chat goes to `jarvis_cmd` (strip a leading `/`; `idx` defaults to NIFTY, or the first word if it is NIFTY / SENSEX / BANKNIFTY); the reply is the command's `reply` (+ `lines` joined), still ≤ CAP a minute.
6. **Health**: `code_changed_since_start` compares mtimes of `*.py` in the tapemap dir (not `data/`, not tests) against the process start time.
7. Every route follows the existing GET/POST patterns in `server.py` (CORS the way `/api/jarvis` does it, JSON through the server's helper, 8 KB POST cap).

- [ ] **Step 1: Failing tests** for `jarvis_cmd.parse` (every grammar row + 4 refusals + 2 help cases), `jarvis_log.write/read/self_line` (a 6-row toy log: `TREND ▼` from 09:56 with fut 23,100 → 22,900 now, two PALAT? episodes one followed by PALAT in 20 min → `TREND ▼ since 09:56 · −200 so far · PALAT? said 2× · came true 1× · blind 0 min`), the card route (`_Cap` pattern; a mock frame injected into `server._JARVIS`), the cmd route (watch → GET state shows it; `mark` reaches the hold handler: assert the trades list grew via `server._hold_trades()` in the test's tmp dirs), a watch hit through `jarvis_cmd.Day.check_watches`, one `messages` JARVIS test, one `telegram_in` routing test. Run → FAIL.
- [ ] **Step 2: Implement** `jarvis_log.py`, `jarvis_cmd.py`, the server routes, the loop hook (fail-soft: a cmd/log error never takes a pass down — follow `_hs_voice`'s fail-soft style), `messages`/`telegram_out`/`telegram_in` changes, `conftest.py` DIR lines.
- [ ] **Step 3: Run** `python -m pytest test_jarvis_log.py test_jarvis_cmd.py test_messages.py test_telegram_in.py test_jarvis.py test_messages_server.py -q` → pass, pristine.
- [ ] **Step 4: NOTEPAD** row `A204` (CRLF binary append after the last `| A20x |` row): the log, the card, the grammar, Telegram commands, `code_changed_since_start`.
- [ ] **Step 5: Commit** your files: `Jarvis v3 Task 2: call log, the card, commands (/mark, watches → Telegram), the stream`.

---

### Task 3: FACE — jarvis2.html renders the card and talks to the server

**Files:**
- Modify: `docs/kahani/review/mockup/jarvis2.html` (the state strip ~line 243 area, `renderBrain` ~line 419, `runCmd` ~line 1228, `checkWatches` ~line 1281, the right panel's top card)

**Interfaces:**
- Consumes: the CARD contract (`GET /api/jarvis/card?idx=`, through Vite at `http://localhost:5173/api/jarvis/card`) and the COMMAND grammar (`POST /api/jarvis/cmd`, `GET /api/jarvis/cmd`). Both may be absent (offline replay from a JSON file, or a server built before Task 2): then the page falls back to what it does today, and says `offline · commands stay on this page` in the command box placeholder.
- Produces: nothing other faces depend on.

**Rules:**
1. The right panel's top card shows, in this order, each as one line of ≤ 6-word cells: the ACTION `word` big with `state` small beside it and `since`; `WITH n · AGAINST m` with the pieces on hover (title attribute, one per line) and `?` pieces greyed; `leg`; `how_much.line` when present; `expression.buyer` and `expression.seller` as two rows, the `pick` row bolded; `wrong_line`; `no_trade` (reason · since · ends) when present; `self` when present; `health.missing` (red) and `health.notes` (grey).
2. Live mode (`?api=`): poll `/api/jarvis/card` every 20 s for the top card (cheap) and keep the 20 s frame poll for the chart. Replay mode (`?day=`): the card comes from `calls[i]` at the playhead as today; new fields render when present.
3. The command box sends every line to `POST /api/jarvis/cmd` when live; the reply's `reply` and `lines` go into the chat panel; `state.watches/lines/zones` from `GET /api/jarvis/cmd` replace the page-local arrays, so a reload keeps her drawings. Offline / replay: today's local JS grammar stays.
4. Light theme, Inter + JetBrains Mono as today, no new library, no `%` rendered anywhere, every level string shown verbatim (they carry `s`/`f`).
5. Verify in a browser: start `python -m http.server 8790 --bind 127.0.0.1` in the mockup directory, open `http://127.0.0.1:8790/jarvis2.html?d=data_30oct_fill.json`, scrub to 11:14 and 13:03, screenshot the right panel, confirm no console errors; then a second check with a hand-written `card_mock.json` (the contract example above) loaded via `?card=card_mock.json` (add this test-only query param: when present it renders that card instead of polling). Kill the server.

- [ ] **Step 1:** Read the page's `renderBrain`, `runCmd`, `checkWatches` and the panel markup. Write `card_mock.json` next to the page from the contract example.
- [ ] **Step 2:** Implement the card rendering (`renderCard(card)`), the `?card=` test hook, the live poll, the command POST with fallback.
- [ ] **Step 3:** Browser check as in rule 5; save the two screenshots to `docs/kahani/review/mockup/shots/v3_card_*.png`.
- [ ] **Step 4:** NOTEPAD row `A205` (CRLF append): what the page shows now, the test hook, the screenshots' names.
- [ ] **Step 5:** Commit: `Jarvis v3 Task 3: jarvis2 renders the card and sends commands to the server`.

---

### Task 4: TERMINAL + the evening sheet

**Files:**
- Create: `tools/jarvis_cli.py`, `tools/jarvis_review.py`
- Modify: `eod_capture.bat` (one line after the `pause_log.py` line)
- Test: `test_jarvis_cli.py`, `test_jarvis_review.py`

**Interfaces:**
- Consumes: the CARD contract, the COMMAND grammar, `GET /api/jarvis?day=&upto=&fill=1` (replay), the CALL LOG contract (`jarvis_log.read`), `data/jarvis/pause_<day>.jsonl` (`tools/pause_log.py` writes it: read that script for the row shape), `data/jarvis/cmd_<day>.jsonl`, her marks (`day_state.load(day)["hold_trades"]`, see `server._record_days` ~line 2337 for the shape).
- Produces: `python tools/jarvis_cli.py [--base http://127.0.0.1:8765] [--idx NIFTY] [--frame file.json]`; `python tools/jarvis_review.py [DAY]` → `data/jarvis/review_<day>.md`.

**Rules (the terminal):**
1. A prompt loop `jarvis> `; stdlib only (`urllib.request`, `json`, `readline` if available). Commands: `now` (print the card as a terminal block: word · state · since / WITH n · AGAINST m with the pieces / leg / how much / BUYER / SELLER / wrong when / NO TRADE / self / health), `why`, `next`, `status`, `wrong when`, `what if K`, `watch`, `line`, `zone`, `remove`, `clear`, `list`, `mark …`, `flat`, `note …`, `ask …` (all sent to `POST /api/jarvis/cmd` with `src: "cli"`), `replay DAY HH:MM` (GET the replay frame once per day, cache it in memory, print the card at that minute from `calls`), `idx NIFTY|SENSEX|BANKNIFTY`, `help`, `quit`. Every server error prints `could not check — <reason>`; a refused command prints the server's reply verbatim.
2. `--frame file.json` runs offline on a saved frame (for tests and the replay room): `now` and `replay` work from it; commands that need the server print `offline — <command> needs the server`.
3. Rendering: fixed-width columns, no colour codes required (optional ANSI if `sys.stdout.isatty()`), ≤ 6 words per cell, every level verbatim (`s`/`f`), never a `%`.

**Rules (the evening sheet, `tools/jarvis_review.py`):**
1. Inputs for `DAY` (default: today, IST): `call_<day>.jsonl`, `pause_<day>.jsonl`, `cmd_<day>.jsonl`, her marks for the day. Output `data/jarvis/review_<day>.md` with sections: **The word** (changes count, the sequence `09:56 TREND ▼ → 11:02 HOLD → …` with minutes held), **PALAT?** (episodes said / came true within 45 min, as counts), **Blind** (minutes, spans), **Her trades vs the word** (each mark: side, entry, the word at entry and its count, the word at exit, points), **Watches** (set / hit), **Pauses** (from the pause log: CONT / REV / UNRESOLVED counts), **Could not check** (every input file absent is its own line). Counts only; never a rate or a %.
2. `eod_capture.bat`: add after the `pause_log.py` line: `"C:\Python313\python.exe" tools\jarvis_review.py >> data\eod_capture.log 2>&1` with a REM line in the file's style.

- [ ] **Step 1: Failing tests.** `test_jarvis_cli.py`: `render_card(card_dict) -> str` on the contract example (asserts the word line, the count line, both expression rows, no `%`); `parse_cli("replay 2026-10-21 10:30")`; offline `now` from a saved frame file written by the test (a 3-minute toy with `call` keys). `test_jarvis_review.py`: a toy day in tmp (6 call rows, 1 pause row, 2 cmd rows, 1 mark) → the sheet contains `word changes: 2`, `PALAT? said 1× · came true 0×`, the trade row, and `could not check — no pause log` when the pause file is absent.
- [ ] **Step 2: Implement** both tools; keep each under ~250 lines; share nothing with the server except the HTTP contracts.
- [ ] **Step 3: Run** `python -m pytest test_jarvis_cli.py test_jarvis_review.py -q` → pass. Run `python tools/jarvis_review.py 2026-10-29` once (its inputs are mostly absent before Monday: the sheet must say so, line by line) and `python tools/jarvis_cli.py --frame docs/kahani/review/mockup/data_30oct_fill.json` with `now` then `replay 2026-10-30 11:14` then `quit` (pipe the commands in).
- [ ] **Step 4:** NOTEPAD row `A206`. **Step 5:** Commit: `Jarvis v3 Task 4: the terminal Jarvis and the evening sheet`.

---

### Task 5: BRAIN-B — read what the tool already measures (HOW MUCH, WHERE, EXPRESSION, her trade, the reads)

**Files:**
- Modify: `jarvis.py` (`call()`, `health()`'s `NOT_READ`, `build()`'s tail), `test_jarvis.py`

**Interfaces:**
- Consumes (read each module's docstring first; call it, never copy it): `trademap.em(rows, day)` (the day's 1σ her way from the 09:20 ATM straddle; `rows` = chain minutes as `trademap` expects — read `trademap.py:76`), `onesided` (§1o: `sides/votes/state/kind` on the frame's 5-min bars; mirror how `decode.py` calls it), `levels.static_levels(daily)` with `daily` built WITHOUT network from `data/backtest/<IDX>/fut_<prevday>.json` bars ≤ 15:15 (the CAS rule, `levels.fetch_daily`'s docstring) and the prior week's files for PWH/PWL, CPR width = `|tc − bc|` with `pivot = (H+L+C)/3`, `bc = (H+L)/2`, `tc = 2*pivot − bc` ([I], algo_ai's formula), `rank.py` (`rank_build` reference files under `data/rank/`: the same-slot median of |3-min delta| for the first 10 bars of the day, so `speed` reads `×` from 09:18 instead of `?`), `confluence_log.logged()` rows for the day/idx (ZONE ✓ OI ✓ FLOW ✓ / FADE-D / RIDE at the band), `data/read/read_<day>.jsonl` and `data/decode/decode_<day>.jsonl` (THE READ word and DECODE's call at the last close ≤ the frame's minute), `gamma` / `chain_metrics` (max pain from the chain row: use `chain_metrics`'s function if one exists), `sides.dte` / the chain's expiry for DTE, the decoder log `data/decoder/` for BADA PRINT rows at a wall (read `decoder_log.py`), `data/vpin_fast.jsonl` percentile (display only), her marked trade: `day_state.load(day)["hold_trades"]` for a past day and the live record file the server writes (read `server._hold_trades` ~3271 and `day_state.py`) for today — choose the open trade for `idx`.
- Produces in `call()`: `how_much` (`{"line", "rows"}`), `where` (`{"stop", "pool", "t1", "t2", "room"}` with `s`/`f` on every level; `null` fields named in `rows` as `could not check — …`), `expression.pick` + the enriched `buyer` / `seller` lines (`buyer` gains `needs +N pts today [I ×1.15] · EM left M`; `seller` gains `IV x vs RV y → rich|fair|cheap` and `fold = HOLD v2 line` when a line exists), `cross` (`{"read": "THE READ ▲ TREND 10:40", "decode": "DECODE ▼ thak 4/7 10:40", "board": null}`), `her_setup` (the confluence rows today), `expiry` (`{"dte": 0, "mode": "EXPIRY UNWIND after 14:00"}` or `null`), and `manage` keyed to her marked trade (the `trade` rows of `reads["trade"]`/`manage` use the marked trade when one is open for the idx; zone triggers only as the labelled fallback `subject: "zone trigger"`).
- `NOT_READ` shrinks to the rows with no source anywhere: book depth read, points per minute, IV per strike, India VIX (unless Task 6 adds it), and nothing else.

**Rules:**
1. **HOW MUCH** line: `day <§1o type> · range used <frac> of EM · σ <sd> · VIX <could not check> · CPR <narrow|wide> (<width> pts)`; `range used` = (day high − day low) / `em` from `trademap.em`; `could not check — no 09:20 straddle` when absent.
2. **WHERE**: stop = her zone's stop when a zone trigger is live (`d["zone"]` rows carry `stop`), else the PALAT line; pool = the first of PWH/PDH (for a short: beyond the stop) within 1.5 × the stop distance; T1 / T2 = the first two of {prior-day POC/VAH/VAL if the tape has them (skip if not; say so), the next wall the lean's way, MAX PAIN, PDL/PDH} the lean's way; room = points to the first of them. Every level printed in both frames where it is a strike (`22,900s (22,943f)`), native frame otherwise.
3. **EXPRESSION pick** [I, display only, for her signature if it ever becomes a rule]: on a `TREND` word with Sides `REAL`/`BACKED` the lean's way and IV ≥ RV × 1.15 → `seller`; on a fresh BROKEN the lean's way with the buyer's required move ≤ EM left → `buyer`; otherwise `null` with `pick_why: "no edge named"`. IV = the chain's ATM IV at the frame minute; RV = close-to-close σ of the last 6 sessions from `data/backtest/<IDX>/fut_*.json` daily closes (annualised the same way `server._realized_vol` does: read it and reproduce the formula, do not import the server). Required move = ATM option LTP × 1.15 [I] in points; EM left = `em − |fut − open|`.
4. **Her trade**: when an open marked trade exists for the idx, `reads["manage"]` and `reads["trade"]` are computed against it (entry `p0`, side, role buy/sell); the card's `expression` gains `in_trade: {"id", "side", "role", "pts", "word_at_entry"}`.
5. Every line says its source in `health.notes` when a source is absent (`levels: could not check — no fut_2026-10-31.json for the prior day`).

- [ ] **Step 1: Failing tests** (record, skip if absent): 29 Oct 11:00 `how_much.line` contains `range used` and `σ`; `where.t1` and `where.stop` carry `s` or `f`; `expression.pick in ("seller", "buyer", None)` and the buyer line contains `needs +` and `EM left`; `cross.read` is a string or `None`; `health["not_read"]` has ≤ 5 entries; the toy-frame reads still pass; `json.dumps(call)` has no `%`.
- [ ] **Step 2: Implement**, one read at a time, each with its `could not check`. **Step 3:** `python -m pytest test_jarvis.py test_legs.py -q` → pass (the causal tests included). Re-run `python tools/jarvis_measure.py 2026-10-21 2026-10-29 2026-10-30`: the ACTION counts must not change (the reads add lines, not words).
- [ ] **Step 4:** NOTEPAD row `A207` with each read's source and the [I] numbers (×1.15, IV/RV 1.15, CPR). **Step 5:** Commit: `Jarvis v3 Task 5: HOW MUCH, WHERE, EXPRESSION pick, her trade as MANAGE's subject, the reads wired`.

---

### Task 6: BRAIN-C — incremental build and thresholds that reload

**Files:**
- Modify: `jarvis.py` (`build()`), `legs.py` (constants), `server.py` (nothing unless the cache needs a hook; coordinate: the server agent is done by then)
- Create: `thresholds.py`, `jarvis_thresholds.json`
- Test: `test_jarvis.py`, `test_thresholds.py`

**Interfaces:**
- Produces: `jarvis.build(day, idx, upto, fill)` unchanged in signature and output; internally a per-`(day, idx, fill)` cache of the heavy intermediates (the book bars, `oim`, the chain `snaps`/`grid`/`peak`/`FR`/`ladder`, the handshake input, Dext candles) extended by new rows only (`tailread.rows` already returns the whole list; keep the row count seen and process the tail), with a full rebuild when any source shrank or when a refill rewrote earlier minutes (detect: the last processed minute's rows changed, or `chain_backfill.read_grid` grew). `thresholds.get("jarvis.FAST", 2.0)` reads `jarvis_thresholds.json` (re-read when its mtime changes); every `[I]` constant in `jarvis.py` and `legs.py` is looked up through it with its current value as the default; the JSON lists them with a one-line reason each.

**Rules:**
1. **Equality is the acceptance test**: for 21, 29 and 30 Oct (skip if absent), simulate the live day: build at upto 10:00, then 10:01, 10:02 … 10:20, then jump to 13:00 and 13:01; at each step compare `call`, `reads["action"]`, `timeline[-1]`, `pushes` and `verdict` with a COLD build (module cache cleared) at the same upto. Any difference fails the test and the task (report it; do not ship a divergent fast path).
2. **Cost**: `python -c` timing in the report: cold full day (today 3–4 s) vs one extra minute on a warm cache (target < 0.5 s, must be < 1 s).
3. Thread-safety: `server._JARVIS_LOCK` already serialises builds; the cache lives in the module and is only touched inside `build()`.
4. The thresholds file is the single place the [I] numbers live; `legs.py` keeps its constants as defaults and reads overrides through `thresholds`; a NOTEPAD line is still required for any change (say so in the JSON's header comment field `"_rule"`).

- [ ] **Step 1: Failing tests**: the equality test above; `test_thresholds.py`: a tmp JSON with one override → `thresholds.get` returns it; mtime change → re-read; missing file → defaults.
- [ ] **Step 2: Implement.** **Step 3:** `python -m pytest test_jarvis.py test_legs.py test_thresholds.py -q` → pass; paste timings. **Step 4:** NOTEPAD row `A208`. **Step 5:** Commit: `Jarvis v3 Task 6: incremental frame (< 1 s per minute) and jarvis_thresholds.json`.

---

### Task 7: VOICE — the model behind one seam, fenced

**Files:**
- Create: `jarvis_voice.py`, `keys/README.md`, `test_jarvis_voice.py`
- Modify: `.gitignore` (add `keys/*.txt`, `keys/cap.json`), `server.py` (≤ 15 lines: call `jarvis_voice.on_change(card)` in a daemon thread when the logged ACTION word changes; route cmd kind `ask` to `jarvis_voice.answer(card, question)`; expose the result as the card's `voice`), `tools/jarvis_cli.py` (the `ask` command prints `voice` lines when present)

**Interfaces:**
- Consumes: the CARD contract; `jarvis_log` rows; `data/jarvis/cmd_<day>.jsonl` notes.
- Produces: `jarvis_voice.speak(card, question=None, provider=None) -> {"lines": [str], "provider": "claude"|"gemini"|"engine", "fell_back": bool, "why": str|None}`; `jarvis_voice.brief(levels, last_call_rows, notes) -> dict` (the pre-open brief, one call with web search, ≤ 6 lines); the log `data/jarvis/voice_<day>.jsonl` (every call: `{"at", "t", "idx", "kind": "change|ask|brief", "provider", "in_tokens", "out_tokens", "lines", "fell_back", "why"}`).

**Rules:**
1. **Provider seam**: `keys/anthropic.txt` → Claude via the `anthropic` SDK (lazy import inside the function; `pip install anthropic` is allowed on this machine; if the import fails: `fell_back`, why `anthropic SDK not installed`); `keys/gemini.txt` → Gemini via `urllib` to `generativelanguage.googleapis.com` (the request shape from `algo_ai/ai_sentiment.py::_call_gemini`, without the search tool except for the brief). No key → `provider: "engine"`, `lines` = the engine's `why` lines (first three), `fell_back: true`, why `no key`. The key file is read at call time, never cached in a global, never logged.
2. **Model and call shape (Claude)**: `claude-opus-5-5`; `thinking` omitted; `output_config={"effort": "low"}` for the on-change narration, `"medium"` for a question; `max_tokens=600`; `system` = a cached prefix (`cache_control: {"type": "ephemeral"}`) holding: the English word table, her rules (no %, no order words, numbers only from the card, levels keep `s`/`f`, ≤ 3 lines, English), and the fence text; the user turn = the card JSON + the day's notes + (the question). The brief uses `tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}]` once, before 09:15, asked for: today's scheduled events for Indian markets, the global cues overnight, and NIFTY/SENSEX expiry, in ≤ 6 lines, every item labelled `[web]`.
3. **The fence (code, never prompt)**: after the reply, (a) every number token in the lines (digits with optional commas/decimals) must appear in the card's JSON text (normalise Indian grouping `23,05,100` and `23,051`); (b) no `%`; (c) no order word (`buy`, `sell`, `lots`, `order`, `place`, `square off`, `short`, `long` as verbs) — allowed in the card's own expression lines only when quoted verbatim from `expression.buyer/seller`; (d) ≤ 3 lines of ≤ 140 chars. A failure → `fell_back: true`, `lines` = the engine's lines, `why` names the failed check. Unit-test the fence with a fake provider that returns a line with a made-up number, one with `%`, one with `buy 5 lots`, one that is four lines.
4. **Budget**: `keys/cap.json` `{"calls_per_day": 80}` (default 80 when absent); past the cap → `fell_back`, why `cap reached`. Calls happen only on an ACTION-word change or her `ask`; never per pass.
5. The server hook never blocks a pass: a daemon thread per call, the result stored in `server._VOICE[idx]` and served in the card's `voice`; a failure is logged and the card shows `voice: {"provider": "engine", "fell_back": true, "why": "..."}`.
6. `keys/README.md`: three lines on which file to drop the key into, the cap file, and that the folder is git-ignored.

- [ ] **Step 1: Failing tests**: fence cases; `speak` with no key → engine lines; `speak` with a fake provider injected (`provider=lambda system, user: "…"`) → lines pass the fence; the budget cap; the log row shape. **Step 2: Implement.** **Step 3:** `python -m pytest test_jarvis_voice.py test_jarvis_cli.py -q` → pass. **Step 4:** NOTEPAD row `A209` (the seam, the fence, the cap; the cost estimate from the vision §5 as [I]). **Step 5:** Commit: `Jarvis v3 Task 7: the voice behind one seam, fenced to the card`.

---

### Task 8: DEXT — her chart face reads the card

**Files (outside this repo, not a git repo; back up first as the previous versions did: copy the folder to `dext-decoder.bak-v0.9.1-pre-card`):**
- Modify: `C:\Users\kaam\Desktop\dext extension\dext-decoder\dext-decoder\lib\jarvis.js` (the `face`/`panel`/`layer`/`Poller`), `lib\panel-render.js`, `lib\overlay.js` (A189 readability), `manifest.json` (0.9.1 → 0.9.2) and wherever the version is pinned a second time (`background.test` pins it: read `HANDOFF.md`), `test\*` (its own node tests: run them the way `HANDOFF.md` says)

**Interfaces:**
- Consumes: `GET http://127.0.0.1:8765/api/jarvis/card?idx=` (the CARD contract) INSTEAD of the 1.2 MB frame for the panel; the layer may keep the frame for walls/pushes/lines or read them from the card (`walls`, `lines`, `pushes` are in the card).
- Produces: the panel shows the ACTION word big with the state small, `WITH n · AGAINST m` (pieces on hover/expand), the leg line, HOW MUCH, BUYER / SELLER with the pick marked, wrong-line, NO TRADE reason, `self`, health; the Hinglish chips next to each word as `lib/jarvis.js` does today (`WORD_CHIP` already has `OPENING: "khula"`; add nothing new unless a new word appears). Only GET, only the index in the query (HANDOFF §4 unchanged).

**Rules:**
1. A189: at the chart's right edge the PALAT chips and push arrows pile under the footprint glyphs — chips of the last 10 minutes move to the gutter (the price-axis column) as short tags; BADA chips become `BADA 1,502` (number + one word); Dext's own per-bar numbers are never covered.
2. Light, English words + chip, verbatim engine sentences, no `%`.
3. Tests: the node suite (97 today) stays green and gains cases for `face(card)` on the contract example and for the fallback when `card` lacks `count`/`how_much` (older server).
4. Her reload is Monday; write the two-line "reload + F5" note into the report.

- [ ] **Step 1:** Read `HANDOFF.md`, `lib/jarvis.js`, the tests' runner. Back up the folder. **Step 2:** Failing node tests for `face(card)`. **Step 3:** Implement. **Step 4:** Run the suite; bump the version in both places. **Step 5:** NOTEPAD row `A210` in THIS repo (the Dext folder is not a git repo). No commit (not a git repo); the report names the backup folder.

---

### Task 9 (controller): integration

- Full suite: `python -m pytest -q -p no:cacheprovider --deselect test_v2feed.py::test_serve_caches_full_and_answers_delta` → all pass (2,142 + the new ones).
- `python tools/jarvis_measure.py --all` → the 25-day table in the final report; every day against the bar.
- Read the card for 21, 29, 30 Oct at 09:57, 10:40, 11:14, 13:45, 15:00 as a trader (`tools/jarvis_cli.py --frame …` or a script over `jarvis.calls`).
- Open `jarvis2.html` on the saved frame in the browser, screenshot the panel.
- Final whole-branch review (one reviewer, the most capable model) over `git merge-base` → HEAD.
- NOTEPAD summary row, memory, the report to her: what is live at her Monday restart, what she must do (stop.bat / start-v2.bat, Dext reload, drop a key into `keys/` if she wants the voice), what is not verified live.
