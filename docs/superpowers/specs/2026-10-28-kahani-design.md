# KAHANI: the live story of each wall fight, and the band's verdict (design, 28 Oct 2026)

**Status:** DRAFT spec, **rev 2** (28 Oct evening): the trader review is folded in as §14, which supersedes §3–§8 where they differ, and the JARVIS face she chose is §15, refined by her §16 choices (English words; the face is the Trade tab with a JARVIS right panel; the Claude brain), whose build order §16.6 supersedes §12 and §15.7. Her approvals: the design, 28 Oct ~16:45 ("yes i think it completes everything write spec"); the Jarvis demo, ~21:30 ("yes this is it this my dream"). Uncommitted until she says commit.
**Evidence:** NOTEPAD A137 (the breakout read), A138 (the replay and six gaps), A139 (the day's final read), A140 (when the covering stopped), A141 (her band and the verdict), A142 (this spec, and two corrections).
**Builds on:** `handshake.py` (A132), `fronts.py` (§1d), the zone machine (§1b / §1r), the message stream (A101) and the replay page `docs/speed/breakout/`.
**Standing rules it obeys:** read-like-claude (live from day one; the record is the evening review, never a gate); read changes, not levels; tool, not essay; Hinglish chips with numbers; light mode; s / f tags; no %, no rate, no order path.

---

## 1. Why: what 28 Oct showed

The tool measured every piece of the 12:44 breakout, but no piece reached her as a story:

| What was true | What the screen did |
|---|---|
| Six pushes into the 22,700s CE wall got no answer while the wall shrank (11:25–12:48) | Never shown. A NAHI never goes on the stream, by design |
| Futures shorts covered −2,153 lots from 12:40 to 12:59 | Never shown. THE READ's fuel said "could not check" all day |
| The covering stopped at 13:00 (the high was 22,875.5f) | Never shown. My own 13:05 read used the since-12:00 total and called for more upside at the top |
| 22,700s CE was unwinding from its 10:37 peak | The 12:12 ZONE SELL said "✓ CE likh rahe"; TOP BAN SAKTA said 4/4 |
| The laptop slept from 12:54:12 to 13:00:20 | The handshake turned the 6 missed minutes into a fake push of +3,534 lots |
| The answers to the 12:44, 12:49 and 12:53 pushes (the first known at 12:47) | On screen at 12:49:50, 13:00:36 and 13:01:40 (the last two waited for the laptop to wake) |

**The missing part is synthesis, not measurement.** KAHANI joins the existing parts into one story per wall fight. That story answers the question her VWAP band asks at every arm: will it rotate, or continue?

## 2. The reading order (the method, every read, every index)

| # | Question | Source |
|---|---|---|
| 0 | **Can we see?** Data holes, missing sources | book gaps > 60 s, missing chain minutes, Dext absent (§6.4) |
| 1 | **Where are the walls?** The top-2 per side: building or unwinding, how far off their peak | `fronts.read` (§1d, unchanged) |
| 2 | **Who is hitting, and is it working?** Read pushes as a **sequence**, not single events | `handshake` pushes and answers |
| 3 | **Fuel now:** the futures OI run, its kind and its direction | §3.2 |
| 4 | **Who is building behind price?** Writers or buyers | `handshake.behind` / TIKI |
| 5 | **Who is trapped?** | futures OI built at worse prices [I]; writers past their strike |
| 6 | **Do the other indices agree?** | the same read on the twin index |
| 7 | **One call**, the line that makes it wrong, and two scenarios | §4, §6.6 |
| 8 | **Evening:** every call against what happened | the forward log and the replay (§6.3, §6.6) |

## 3. KAHANI: the life of a wall fight

### 3.1 The fight

There is one active fight per index. It is held at the wall price is pressing on: the §1d front within 2 steps ahead of price, in the direction of the last push (or of the last 15 minutes' move when no push has come yet). A fight ends in one of three ways:
- price leaves the wall by more than 2 steps without a TOOT ("ghoom gaya");
- it reaches an ending (§3.4);
- a new wall becomes the one ahead.

The ended fight stays in the day's list.

### 3.2 RASAD (fuel), the one new measure

The input is the futures OI per minute. Sources, in order:
- the index's own book, from `handshake.load`'s `oim`, the last OI of each minute;
- after a hole, the Upstox REST 1-min bars, fetched once and tagged `rest`. They survive outages: on 28 Oct they were complete through the sleep.

The bar is `handshake.FUT_LOTS`: NIFTY 500 lots, BANKNIFTY 200, SENSEX 10 [I]. The bar is used, never re-tuned.

| Term | Definition |
|---|---|
| `w5(m)` | OI(m) − OI(m−5), in lots |
| `p5(m)` | futures price(m) − price(m−5) |
| **RUN starts** | the first minute with \|w5\| ≥ bar. Kind COVER (w5 < 0) or FRESH (w5 > 0) |
| **RUN lives** | while OI makes a new extreme in its kind's direction (a new low for COVER, a new high for FRESH) at least once every 3 minutes |
| **KHATAM** | the 3rd minute with no new extreme. Stamped with the last extreme's minute and the run's total lots |
| **Direction**, each minute of a live run | sign of `p5`: COVER with price up = shorts covering, fuel ▲; COVER with price down = longs closing, fuel ▼; FRESH up = fresh longs ▲; FRESH down = fresh shorts ▼; \|p5\| < 5 pts = "?" |
| **Hole** | any minute missing inside the 5-minute window or the 3-minute check means "?" (could not check). It is never FLAT, never KHATAM |

Why runs and not the raw window [M], NIFTY Nov futures on 28 Oct:
- The raw 5-minute window at 500 lots changed state 10 times between 12:10 and 13:02 (COVER, FLAT, COVER, ...).
- The run rule gives exactly two runs in that hour:
  - COVER 12:10–12:11, −775 lots, KHATAM at 12:14;
  - COVER 12:40–12:59, −2,153 lots with price +122f, **KHATAM at 13:02 (22,830f), 2 minutes after the 22,875.5f high**.
- The same rule over the whole day: FRESH 09:20–09:53 (+9,887, KHATAM 09:56), FRESH 10:00–10:18 (+2,621 with price −124f: fresh shorts on the fall, KHATAM 10:21), FRESH 10:48–10:51 (+609, KHATAM 10:54), then the two covers above.

### 3.3 The chapters

One chapter is current; each change is stamped once.

| Chapter | When (all from existing parts) | Chip |
|---|---|---|
| **DEEWAR** | the fight's wall is BUILDING or STALLED (§1d), no push into it yet | `DEEWAR 22,700s CE +57.1L` |
| **DASTAK n** | ≥ 1 push into the wall, none answered TOOT / PHANS. Counts pushes and answers | `DASTAK ×5 · jawab 0` |
| **THAKAN** | DASTAK while the wall is UNWINDING (§1d state: ≥ 15 % off its own peak, with a falling slope) | `THAKAN · deewar −24L peak se` |
| **TOOT** | a push into the wall answered TOOT or PHANS | `TOOT 12:44 · −3.7L (3 min)` |
| **RASAD** | after a TOOT: the fuel run (§3.2), with lots and direction | `RASAD cover ▲ −2,153` / `RASAD KHATAM 13:02` |
| **NAYA FLOOR / CAP** | inside RASAD: an opposite push answered TIKI, or `handshake.floor_cap` (WRITERS behind price) | `NAYA FLOOR 22,700s PE +4.3L` |

### 3.4 The endings (after KHATAM)

| Ending | Rule |
|---|---|
| **CHAL** | a new run starts in the move's direction. The fight moves to the next wall ahead (a new DEEWAR) |
| **PIN** | after KHATAM, and before any new run or TOOT, at least one push each way answered NAHI / TIKI; or the two sides' top fronts sit within 1 step of price and are both BUILDING / STALLED |
| **PALAT** | an opposite push answered TOOT at the floor or cap behind price |

28 Oct, by these rules (to be reproduced by the engine, §8):
- DEEWAR 10:37;
- DASTAK ×5 (11:25, 11:57, 12:08, 12:26, 12:40);
- THAKAN from the minute §1d turns 22,700s CE to UNWINDING (§8 measures it; at 12:06 §1d read STALLED, A136, while the wall was already about 40 % off its 10:37 peak);
- TOOT 12:44 (RASAD cover from 12:40);
- NAYA FLOOR 22,700s PE at 12:49 (TIKI +4.3L);
- TOOT 12:53;
- KHATAM 13:02;
- PIN by 13:30: the 13:19 ▼ push NAHI at 22,700s PE and the 13:26 ▲ push NAHI.

## 4. The band verdict: GHUMEGA / CHALEGA / SAAF NAHI

Her zone (§1b / §1r) asks the question at the band: d2→d3 buy, u2→u3 sell. Its arm, trigger, entry and stop are unchanged. KAHANI answers at the **ARM** (the early read) and again at the **TRIGGER**. It is three words, plus the pieces as ✓ / ✗ / ? with their numbers, never a %.

A SELL wants fuel ▼ and its defender is the CE wall. A BUY wants fuel ▲ and its defender is the PE wall (`fronts.DEFENDER`). The pieces depend on the chapter, because the question changes once a wall has broken:

**(a) Fade at a standing wall** (no TOOT on the band side in the last 30 min):

| Piece | ✓ | ✗ |
|---|---|---|
| FUEL | no live run, or a live run driving the trade's way | a live run driving against the trade |
| WALL | the defender front BUILDING / STALLED | UNWINDING (THAKAN) |
| DASTAK | the last push into the band side in 15 min answered NAHI / TIKI | TOOT / PHANS |

**(b) Exhaustion after a break** (a TOOT on the band side in the last 30 min):

| Piece | ✓ | ✗ |
|---|---|---|
| FUEL | KHATAM, or a run turned the trade's way | the run still driving against the trade |
| NEXT PUSH | the first push into the new extreme after the LATEST TOOT answered NAHI / TIKI | answered TOOT / PHANS again |
| ULTA PUSH | the first push the trade's way after the latest TOOT answered TOOT at the floor or cap behind | TIKI (the floor held) |

An ULTA PUSH answered NAHI is shown as "·" and not counted: the floor neither broke nor was defended.

**Verdict:**
- **CHALEGA:** FUEL ✗; or (a) WALL ✗ and DASTAK ✗; or (b) NEXT PUSH ✗.
- **GHUMEGA:** at least 2 ✓ and no ✗.
- **SAAF NAHI:** everything else.

Shown as n/N, where N counts the checkable pieces. A "?" piece is shown and never counted.

**Two more lines with the verdict:**
- **Rotation target:** the nearer of the NAYA FLOOR / CAP and her u1 / VWAP.
- **Wrong-line:** a new run against the trade (`galat agar: fut OI phir −500/5m`).

**What the rows say** [M] (hand-computed from the rules above; §8 makes the engine reproduce them; rows, not rates):

| Trigger | Pieces | Verdict | Next 30 min (fut) |
|---|---|---|---|
| 28 Oct 12:12 SELL 22,704.3f | (a) FUEL ✗ (COVER run from 12:10, −723 lots in 5 min with price +9.3f), WALL ? (§8 measures the §1d state; 12:06 read STALLED), DASTAK ✓ (12:08 NAHI) | **CHALEGA** (FUEL ✗ alone decides it) | +14 / −53, stopped at 22,745f |
| 28 Oct 13:03 SELL 22,821f | (b) FUEL ✓ (KHATAM 13:02), NEXT PUSH ? (the 13:01 push is the sleep artifact), ULTA PUSH ? | **SAAF NAHI** 1/1 | +66 / −9; its 8-pt stop (22,829f) was taken at 13:12 first |
| 28 Oct 13:15 SELL 22,802f | (b) FUEL ✓ (spent, no new run), NEXT PUSH ?, ULTA PUSH ? (13:19 comes later: NAHI at 22,700s PE) | **SAAF NAHI** 1/1 | +47 / −28; then PIN |
| 27 Oct 12:51 SELL (A129) | (b) NEXT PUSH ✓ (12:44 NAHI), ULTA PUSH ✓ (12:49 PE −9.9L), FUEL: measured by §8 | **GHUMEGA** ≥ 2/2 | −146 from the trigger by 14:16 |
| 27 Oct 14:18 BUY (A129) | (a) DASTAK ✓ (14:04 / 14:11 / 14:15 NAHI), FUEL ✓ (flat), WALL: measured by §8 | **GHUMEGA** ≥ 2/2 | +65 |
| 28 Oct 09:42 / 09:54 / 10:24 | no pushes (the book began at 11:07); fuel only | **SAAF NAHI** | — |

**Honest limits:**
- The rules come from the same two days. That is why every verdict is live from day one and scored every evening, and why §8 replays every recorded zone trigger before anyone reads the rows as more than rows.
- On 28 Oct the formal rule reads both afternoon sells as SAAF NAHI. The fuel was spent but nothing confirmed. The PIN that followed agrees with that, not with my hand-call of GHUMEGA in A141.

## 5. Indices

| Index | Pushes | Answers said? | Fuel | Walls |
|---|---|---|---|---|
| NIFTY | its own flow | yes (the validated bar) | its own futures OI | its own |
| SENSEX | NIFTY's flow (§1q) | not yet (the answer bar is owed, handshake.SPEAK) | NIFTY's fuel (§1q's twin rule; SENSEX futures are too thin, A25) [I] | its own |
| BANKNIFTY | its own flow | not yet (no strike can cross 3L) | its own (bar 200) | its own |

Where an answer is not said, the verdict uses FUEL and WALL only and says why: "jawab padh nahi sakte (bar baaki)".

## 6. Architecture

### 6.1 The brain: one place, the server

| Unit | Does | Depends on |
|---|---|---|
| `handshake.py` (changed, §7) | pushes and answers; a hole-safe flow | the record (unchanged I/O) |
| **`kahani.py`** (new, pure) | `fuel(oim, px, upto)` → runs and the state per minute; `story(inp, fronts_at, fuel, upto)` → the day's fights, chapters, stamps and current line; `verdict(zone_row, story, fuel)` → the band verdict | `handshake` rows, `fronts.read`, the futures minutes. No I/O, causal: `upto` only |
| `kahani.load(day, idx)` | the one loader: `handshake.load` + the chain grid with per-minute peaks for `fronts.read` + the REST backfill on a hole + today's zone3 rows from `trigger_log` | the record files (read only) |
| `server._kahani_pass` | inside `_msg_pass`, once per new minute (as `_hs_pass`), fail-soft per index | `kahani.load` |

### 6.2 One endpoint
`GET /api/kahani?idx=&day=&upto=` returns:
- the current fight and its chapter chain;
- the fuel (run, lots, direction, KHATAM time);
- the verdicts of today's zone arms and triggers;
- the coverage (§6.4);
- the stamps;
- the ladder grid (the per-minute strike OI the face draws).

Today is served from memory. A past `day`, or an `upto`, is replayed from the record on request; this replay is refused 09:15–15:40 except for today.

### 6.3 Forward log
`data/kahani/kahani_<day>.jsonl` is write-once by key:
- every chapter stamp;
- every verdict, with its pieces, the +15 / +30 points and stop-hit, filled at the close.

No verdict on the verdicts, no rate.

### 6.4 Coverage ("dikh nahi raha")
Every read carries the minutes it could not see, each with its reason:
- a book gap > 60 s (with its span);
- a missing chain minute;
- no Dext for the contract;
- the REST backfill used (tagged).

Three sentences, never one: checked-and-nothing, could-not-check, and not-shown each get their own rendering.

### 6.5 Anytime-start
At start, the day is replayed from the record step by step, so an 11:12 start reads exactly what a run that never stopped would have read. A morning the book never saw stays "?", with its reason.

### 6.6 The faces (render only, no logic)

**1. The LADAI tab (ui-v2).** Light theme. The face is today's replay page, made live. It has two modes:
- **LIVE** follows now;
- **REPLAY** has a day picker, play / scrub / speed and chapter chips. This mode is the evening review.

Its layout:
- **Hero:** the chapter chain of the current fight, one line ABHI with the wrong-line, and two lines ▲ / ▼ (the scenarios).
- **Ladder:** PE left, CE right, peak ghosts, the price marker, ◆ push stamps with their answers at the struck strike, the DASTAK count.
- **Fuel card:** the run, its lots and direction, the last 30 min as bars.
- **Coverage box.**
- **The verdict rows** for today's zone arms and triggers.

**2. The stream and the Float.** One `KAHANI` line, **only on a chapter change or a verdict**. A single NAHI never gets a line; it shows as the DASTAK count.

**3. In a trade.** `_hs_voice`'s l6 line reads the fight:
- a TOOT at her defending wall with a run against her: WARN line;
- a push against her answered NAHI: PULLBACK · HOLD line;
- a new run against her: WARN line.

These lines are added after the ladder, exactly like today's l6. The voice's state and stop are never read or changed.

**4. Telegram.**
- The band verdict goes with her ZONE alert at the TRIGGER, the one zone moment that already reaches Telegram (messages.OFF keeps an ARM silent, A131). That is what she asked for. The ARM verdict is screen-only.
- TOOT with a run, RASAD KHATAM after a run of at least 2× the bar, and PALAT stay screen-only until she says otherwise.
- Budget: at most 6 KAHANI lines per index per day.

**5. The GoCharting ribbon.** The chapter under the bars, and ◆ with its answer: the last step, after the faces above have been seen live.

## 7. Step 1: data truth (fixes that come first)

| Fix | Rule |
|---|---|
| **The sleep artifact** (her yes, 28 Oct) | in `handshake.book_flow`, a trade whose previous book row is more than 60 s older is not counted, and the minute it lands in is dropped from the flow. `pushes`' `d2` then has no value across a hole, so no push can be born from a catch-up. The same rule is kept by `palat` (one copy). Check: the 28 Oct record gives no 13:01 push, and every other 28 Oct push is unchanged |
| **The answer lag** | first measure: each pass's duration and each chain minute's landing time go into the log. Then fix the measured cause, not a guess (the candidate: `handshake.load` re-reads the whole day's book every pass). Target: a TOOT on screen ≤ 30 s after its chain minute lands |
| **The fuel source** | §3.2 uses the book's own futures OI with the REST backfill. THE READ's rank-pool fuel is untouched and keeps saying "could not check" where it cannot |
| **Coverage** | §6.4, the same truth in the stream's HEALTH line |

## 8. Testing (one test file, and the replay)

`test_kahani.py`, reading the record and never writing under `data/`:
1. **Fuel:** a frozen 28 Oct NIFTY futures OI fixture (inline, from the REST minutes) gives exactly the runs listed in §3.2: FRESH 09:20 / KHATAM 09:56, FRESH 10:00 / 10:21, FRESH 10:48 / 10:54, COVER 12:10 / 12:14, COVER 12:40 / KHATAM 13:02. A hole in the window gives "?".
2. **The hole:** book rows with a 374 s gap → no push at 13:01; all other 28 Oct pushes unchanged.
3. **Causality:** for every minute m, `story(..., upto=m)` equals the prefix of the full-day story. No minute ≥ m is read.
4. **The 28 Oct story:** DASTAK ×5 before 12:44, TOOT 12:44, NAYA FLOOR 22,700s PE 12:49, TOOT 12:53, KHATAM 13:02, PIN at 13:30 (the 13:26 push's answer). THAKAN's minute is reported, not asserted.
5. **The verdicts:** 28 Oct 12:12 CHALEGA; 13:03 SAAF NAHI; 13:15 SAAF NAHI; 27 Oct 12:51 GHUMEGA; 27 Oct 14:18 GHUMEGA.

**The rule text in §3–§4 wins.** If the engine disagrees with a hand-computed row, the hand row is re-checked and corrected. It is never the reason to tune a threshold. A threshold change is a new rev (`kahani-2`) with its reason in the NOTEPAD.

**The replay:** `docs/kahani/replay_zone.py` (read-only) runs every recorded day's zone3 triggers through `verdict`. Each row has the pieces, the verdict, +15 / +30 and stop-hit, written to `docs/kahani/REPLAY.md`. No rate. Her pass bar is hers, stated before she reads the rows.

## 9. What stays untouched

- §1b / §1r (her zone: arm, trigger, entry, stop, `trigger_log`).
- §1d (`fronts.py` parameters; KAHANI calls `fronts.read`, never changes it).
- §1i–§1q, THE READ, DECODE.
- The voice ladder's state and stop.
- `palat.py`'s checks, until she signs §10.
- The existing message kinds.
- The Dhan fallback, the Trade chart, the PaperDesk routes.

## 10. Hers to sign (method, not presentation)

1. **TOP / BOTTOM BAN SAKTA's futures check:** read KAHANI's FUEL piece (a live run toward the extreme ✗; KHATAM or no run ✓) instead of "FLAT only". 28 Oct 12:20 is why: the 4/4 counted covering as a top, and it was the rally's fuel.
2. **The ZONE line's "CE / PE likh rahe · lead" piece:** read the §1d defender state. On 28 Oct 12:15 it said "✓ CE likh rahe +24.1" while 22,700s CE was 24L off its peak. Until she signs, the two are shown side by side.

Everything else here was decided as the trader (her standing rule) and is listed in §11.

## 11. Decided as the trader, and why

- **Runs, not windows,** for fuel: the window flickers 10 times in an hour (§3.2).
- **NAHI as a count,** never a line: the sequence is the information ("dastak ×5 · jawab 0"); a single NAHI is noise.
- **The verdict depends on the chapter:** before a break the question is "is the wall holding"; after it, "is the fuel spent".
- **Telegram only for the verdict** at first: she asked for that confidence; the other lines earn their place on screen first.
- **SENSEX takes NIFTY's fuel:** §1q's twin rule; SENSEX futures are too thin to carry a run.
- **The replay is the same tab as live:** one face, so the evening review reads exactly what the day showed.

## 12. Build order (superseded by §15.7)

| Step | What | Her action |
|---|---|---|
| 1 | Data truth (§7) | restart |
| 2 | `kahani.py`, `/api/kahani`, the forward log, `test_kahani.py`, the zone replay rows | restart (the same one as 1 if both are ready) |
| 3 | The LADAI tab (live + replay), the KAHANI stream line, the l6 voice line | none for the tab (Vite); restart for the lines |
| 4 | The verdict on her ZONE Telegram alert | restart |
| 5 | The GoCharting ribbon | extension reload |

## 13. Open

- The 8-point stop on the 28 Oct 13:03 SELL (taken by a 9-point poke before a 66-point fall) is an observation about the zone's stop, not part of this spec.
- The BANKNIFTY / SENSEX answer bar is still owed (handshake.SPEAK).
- Nothing from 27 or 28 Oct is committed yet (Phase 0 / 1, A125 / A126, the Speed tab, docs/speed, the launch.json edit, this spec).


---

## 14. Rev 2: what the trader review changed (28 Oct evening)

This section **supersedes** §3–§8 wherever they differ.

- **Sources:**
  - `docs/kahani/review/` holds Fable's 90 questions, my answers with measurements (ROUND1-ANSWERS.md), first principles by scenario (ROUND2-SCENARIOS.md) and the additions (ROUND2-ADDITIONS.md).
  - NOTEPAD A143–A145.
- **Status:** each item is decided as the trader unless marked hers.

| # | Change | Why [M] |
|---|---|---|
| 1 | **handshake-2: a TOOT is stamped only if the crossing holds at the next chain minute** (or at m+4, if that comes first); otherwise it is `wapas`, which counts as NAHI. Live, the chip reads `TOOT?` until then | 17 of 103 NIFTY answers over 16 days un-crossed by m+4; 13 of those were TOOT → NAHI |
| 2 | **The verdict is a timeline: ARM → TRIGGER → +5 → +10.** The TRIGGER Telegram line shows its empty pieces (`SAAF NAHI 1/1 · 2 ?`). One follow-up line is sent if the word changes within 10 min of the trigger while price is within 1 step of entry | 0 of the 5 §4 rows read GHUMEGA at the trigger. 27 Oct 12:51's ULTA TOOT was known at 12:53, after the trigger |
| 3 | **The WALL piece reads the held state.** It enters THAKAN / KHISAK after 3 UNWINDING marks and leaves after 3 BUILDING marks. The raw §1d state shows as small text, and §1d is untouched | The raw state flipped the verdict 6 times between 11:40 and 11:51 on 28 Oct |
| 4 | **The (a) FUEL memory belongs to the fight**, not a 30-minute clock: an ending clears it. A dead run under 2× the bar shows `·`; at 2× or more it reads ✗ | 28 Oct 13:32–13:37 read CHALEGA → SAAF NAHI → GHUMEGA on a pinned market |
| 5 | **Context (b) lasts until the fight ends** (an ending or a new fight) | A 30-minute clock drops the broken-wall story while it is still running |
| 6 | **Chapters added:** KHISAK (a wall unwinding with no push); PHANSE (writers under water, including price 2 steps through with no TOOT). **PALAT has two forms**: the wall form and the fuel form (a run the other way after KHATAM). PIN's second clause becomes a context chip; 20 min with no push after KHATAM reads KHAMOSH | First principles (ROUND2-SCENARIOS) |
| 7 | **NAYA FLOOR needs a flip:** the same strike's other side must be UNWINDING or TOOT'd. Both sides building means PIN evidence | 28 Oct 22,700: CE −34L off its peak while PE +27L |
| 8 | **Fuel rules:** <ul><li>the book is primary;</li><li>a minute whose last book row comes before :50 s is a hole;</li><li>a minute with no OI change does not advance the KHATAM clock;</li><li>run lots count from OI(start−5), never from before the previous run's last extreme;</li><li>the direction is stamped at the start, re-stamped after 3 minutes the other way;</li><li>w5 minutes start at 09:16 or later;</li><li>the \|p5\| floor is 5 pts on NIFTY, 15 on BANKNIFTY;</li><li>**roll week (T−3 → expiry): near + next summed; "?" on the near month's expiry day.** Fable argues for the next month alone (disputed); the Nov roll week's rows settle it</li></ul> | The book alone gave a false KHATAM at 12:54 (minute 12:54 held 12 s). OI publishes once a minute (median gap 60.2 / 60.6 s). Oct contract on 21 Oct: COVER in 10 of 10 runs. Nov contract alone on 27 Oct: one FRESH run, +44,325 |
| 9 | **Data truth adds:** <ul><li>the chain backfill seeds §1d's peaks (anytime-start);</li><li>after a chain hole, REST backfills the 9 near strikes × 2 sides;</li><li>the next-month future is subscribed;</li><li>Dext delta is scale-checked against the book's, then the push median runs on the book alone</li></ul> | On 28 Oct the 10:37 peak was never seen (the chain began at 11:07) |
| 10 | **§4 rows corrected:** <ul><li>12:12 WALL ✗, so CHALEGA stands on two pieces;</li><li>both 27 Oct rows have FUEL "?" (Oct expiry) and read SAAF NAHI at the trigger;</li><li>12:51 becomes GHUMEGA 2/2 at 12:53;</li><li>each row is tagged with its population (27 Oct = `zone`, 28 Oct = `zone3`; never pooled)</li></ul> | ROUND1-ANSWERS findings 2–4 |
| 11 | **Geometry is spot** (strikes; `handshake` reads the chain's spot), **fuel is fut**, and a zone level converts to spot with `fold.BIX_MS` | Basis +62…+95 on 28 Oct |
| 12 | **Renames:** the rotation target becomes `pehla padav` (her VWAP / u1). The in-trade line says `khatra`, never the ladder's words | Her "the wall ahead, never a target"; `voice.py` owns WARN / EXIT |
| 13 | **Expiry:** an `EXPIRY` chip, and after 14:30 TOOT / PALAT pieces read "?". **JHATKA** guard: a 1-min fut move ≥ 3× its 30-min median plus both near fronts dropping makes the verdict "?" for 5 min. After 15:00: `3 baje ke baad` (display only) | First principles |
| 14 | **Built, read forward as rows:** <ul><li>the TOOT tally by side (`TOOT ▲ 0 · ▼ 4`);</li><li>the paani-mein ledger (fut lots under water);</li><li>the lag on the face (`pata 12:47 · screen 12:49:50`);</li><li>ummeed-vs-asal rows;</li><li>the young-wall chip;</li><li>`teeno saath`.</li></ul> **Candidates, reproduced on the replay rows first:** the soft ✓ at the extreme, context (c) for the open, the WHO bar in vol points | 08 / 21 Oct: TOOT ▲ 0 against ▼ 4 / 5; ~10K lots under water on 28 Oct [I] |

## 15. JARVIS: the face she chose (28 Oct ~21:30)

**Her words:** "yes this is it this my dream and ai in my chart with me tell me whats market is doing in real analysing everything and making a best judgement out of current situation ... if i tell it to draw something on chart is should be able to do that tell it to look for any level it looks at it and maybe send me a telegram message . shrt story should be able to tell me no trade zones if nothing significant is happening".

**The reference:** `docs/kahani/review/mockup/jarvis.html` (NOTEPAD A145).

### 15.1 What Jarvis is
KAHANI's frame, rendered as a companion on her chart:
- **The bubble:** an orb that thinks, then a typed line; chips with numbers; `aage kya` ▲ / ▼ and `galat agar`. It sits above or below the live candle and is linked to it.
- **The levels it marks:** walls with OI, floors, `agla deewar`, her zone level. Every one is tagged s / f.
- **The markers:**
  - ◆ a push, travelling to its wall, then its answer chip;
  - her trigger with its verdict pill;
  - pins for past notes (hover to read);
  - the RASAD tank;
  - the dark band for what it could not see.

Jarvis explains, judges, draws, watches and alerts. **It never places an order**, whatever the request.

### 15.2 NO TRADE: a state, with its reason and what ends it

| State | When | The bubble says |
|---|---|---|
| **KHAMOSH** | no live run; no TOOT / PHANS / TIKI in 15 min; the fight is not in THAKAN / TOOT / RASAD; any zone verdict is SAAF NAHI | `NO TRADE · kuch khaas nahi (13:34 se) · tab tak ruko: RASAD ≥500/5m ya koi TOOT` |
| **ANDHERA** | a book or chain hole, or less than 10 min of push history | `NO TRADE · dikh nahi raha (laptop soya 12:54)` |
| **JHATKA** | §14 row 13 | `NO TRADE 5 min · jhatka (news?)` |
| **EXPIRY / 3 BAJE** | after 14:30 on the index's own expiry; after 15:00 | display only, her practice |

The NO TRADE state is screen only. The chart dims a little and the bubble shrinks to one line. It never goes to Telegram.

### 15.3 Commands (typed into the bubble first; one grammar; deterministic code)

| She types | Jarvis does |
|---|---|
| `22,750f pe line` / `line 22,700s` | draws a level (kept for the day, drawn by the extension) |
| `zone 22,680–22,720f` | draws a box |
| `22,800s dekho, aaye to batao` / `watch 22,800s` | a server watch. On touch (spot or fut, as tagged), it sends **Telegram plus a bubble line carrying the KAHANI read at that moment** (fight, dastak / jawab, fuel, verdict). At most 10 watches a day; they are hers, so they sit outside KAHANI's 6-line budget |
| `hatao 22,750` / `sab hatao` / `list` | removes or lists drawings and watches |
| `kya ho raha?` / `kyun?` / `aage kya?` / `galat kab?` | answered from the current frame, in the bubble's own sentences |
| anything with an order (`buy`, `sell 5 lots`, `order`) | `main order nahi lagata, sirf padhta hoon` |
| anything else | `samjha nahi` plus the command list |

### 15.4 Voice (J5)
- **Jarvis speaks** (`speechSynthesis`, an en-IN / hi-IN voice) only the major lines: TOOT, KHATAM, a verdict, a watch hit. There is a mute toggle.
- **Jarvis listens** on push-to-talk (Chrome's Web Speech, hi-IN) into the same §15.3 grammar.
- **Hers to accept:** Chrome's recognizer sends the audio to Google. A local recognizer is a later option.

### 15.5 The conversation brain (J5, hers to approve)
Free-form questions can be answered by Claude through the API.
- **Inputs:** only the current frame JSON and the day's stamps.
- **Rules:** every number must come from the frame; no rate; no order language.
- **Hers:** this needs her API key and her OK on the cost per question.
- **Until then:** templated answers only.

### 15.6 Where it runs
- **Brain (server):** `/api/kahani` (§6.2) plus `POST /api/jarvis/cmd`.
  - Drawings and watches persist in `data/jarvis/jarvis_<day>.jsonl` (write-once events), so they survive a restart (the anytime-start rule).
  - Watch hits go through `telegram_out`.
- **Live face:** the GoCharting extension, which draws the bubble, levels and markers on her chart (render only).
- **The evening:** the LADAI tab replays the day with this same bubble over the recorded candles. It is the evening review she approved in the demo. Live, the bubble lives on her chart and never redraws price.

### 15.7 Build order (supersedes §12). Each step is built after the close; the restart is hers

| Step | What | Her action |
|---|---|---|
| **J1** | **Data truth:** <ul><li>the handshake hole fix (her yes, 28 Oct);</li><li>partial-minute holes;</li><li>answer lag measured, then fixed (≤ 30 s from landing);</li><li>coverage;</li><li>the chain backfill seeding §1d peaks;</li><li>handshake-2's hold rule</li></ul> | restart |
| **J2** | **Brain:** `kahani.py` with §14, the NO TRADE states, `/api/kahani`, the forward log, `test_kahani.py`, the zone replay rows (by population) | restart |
| **J3** | **Face:** the LADAI tab (`jarvis.html` made real on `/api/kahani`, live + replay), then the GoCharting bubble, levels and markers | Vite reload; extension reload |
| **J4** | **Commands:** the typed box; draw / zone / watch → Telegram / ask (templated); `/api/jarvis/cmd`; watches that survive a restart | restart |
| **J5** | **Voice** (speak + push-to-talk); the Claude conversation brain if she approves §15.5 | her key, if she wants it |

## 16. Her choices, 28 Oct ~22:10 (these supersede §15 where they differ)

**Her words:** "change it to english thats fine and i can manage we do it like the animation you created on my trade tab inside my our own tool maybe in future we can market it its a good concept ... in the right panel we have jarvis and in chart we have like in the animation you showed jarvis.html is almost my dream i will add voice to it and i want your brain to it".

### 16.1 Where Jarvis lives: the Trade tab, in her own tool
- **The chart:** the Trade tab's futures chart (`ui-v2/src/trade/`, lightweight-charts) carries what `jarvis.html` showed:
  - the bubble, anchored above or below the live candle (`priceToCoordinate` / `timeToCoordinate`);
  - the levels it marks, with OI and s / f tags;
  - ◆ pushes travelling to the wall, then their answer chips;
  - her triggers with their verdict pills;
  - note pins;
  - the fuel tank;
  - the blind band.
- **Why the chart is allowed:** the Trade tab is the one place TapeMap draws a chart. She called it "our playground" on 29 Sep.
- **The right panel is JARVIS:**
  - the live feed of what it said (newest on top; each line with its time and numbers);
  - the current state (fight, fuel, verdict, NO TRADE with its reason);
  - the command box (§15.3);
  - later, the voice controls.
- **The panel down the left of the chart stays as it is.**
- **The GoCharting overlay** is not built for now. Her standing goal is to retire GoCharting (6 Oct), and the same frame could feed it later.
- **The evening replay** is the same Trade tab with a day picker and scrub, as in the demo.

### 16.2 The words are English
Every word ships with its number and a plain meaning on hover.

| Spec word | On her screen |
|---|---|
| DEEWAR | **WALL** (`WALL 22,700s CE · 92L`) |
| DHAKKA / push | **PUSH** (`PUSH ▲ +434 lots`) |
| DASTAK ×n · jawab j | **TESTED ×5 · broke 0** |
| NAHI / TIKI / TOOT / PHANS / wapas | **HELD / DEFENDED / BROKEN / TRAPPED / BREAK FAILED** |
| THAKAN / KHISAK | **WEAKENING** (tested while unwinding) / **RETREATING** (unwinding, untested) |
| RASAD · KHATAM | **FUEL** (`FUEL: shorts covering −2,146 lots`) · **FUEL SPENT** |
| NAYA FLOOR / CAP | **NEW FLOOR / NEW CEILING (flip)** |
| PHANSE | **TRAPPED WRITERS** |
| CHAL / PIN / PALAT | **CONTINUES / PINNED / REVERSAL** |
| GHUMEGA / CHALEGA / SAAF NAHI | **ROTATE / CONTINUE / UNCLEAR** |
| KHAMOSH / ANDHERA / JHATKA | **NO TRADE: quiet / NO TRADE: can't see / NO TRADE: shock** |
| aage kya · galat agar · pehla padav | **NEXT · WRONG IF · FIRST STOP** |
| teeno saath · paani mein · ummeed vs asal | **ALL THREE IN SYNC · UNDERWATER · EXPECTED vs ACTUAL** |

The internal names follow the product. The engine is `jarvis.py` (it was `kahani.py` in §6), the endpoint is `GET /api/jarvis?idx=&day=&upto=` plus `POST /api/jarvis/cmd`, and the log is `data/jarvis/`.

### 16.3 The brain: the rules engine, plus Claude (her "i want your brain to it")
There are two layers, and they never mix:
1. **The rules engine (`jarvis.py`)** produces every fact and every verdict. It is deterministic, the same every time, scored every evening, and causal. It is the only thing that marks a level, sets the verdict or declares NO TRADE.
2. **Claude (Anthropic API)** is the voice and the conversation:
   - it turns the frame into her bubble lines when something changes;
   - it answers her free questions ("why?", "what if it breaks 22,800?").
   - **Inputs:** only the current frame JSON, the day's stamps and her levels and watches.
   - **Rules in its prompt:** every number must come from the frame; it never changes the engine's verdict; no rate, no %; no order language.
   - The engine's verdict is shown beside Claude's words, so the two can never silently disagree.

**Hers:**
- the Anthropic API key (kept in a git-ignored file, like the Telegram token);
- the monthly spend cap.

**Decided as the trader:**
- Claude is called on a change or on her question, never every second.
- A model in the latest Claude family (the exact model chosen at J5 against cost).
- With no key, or on an API failure, the bubble falls back to the engine's fixed sentences and says so. The face never goes blank.

### 16.4 Voice
She adds it, to the §15.4 shape: it speaks only the major lines; push-to-talk feeds the same command grammar; there is a mute toggle.

### 16.5 Product-ready, not product-built
She may market it later. So the boundaries stay clean:
- one frame API between brain and face;
- no personal paths in the face;
- the key files git-ignored.

Nothing is built for other users now (YAGNI). This only stops us from closing the door.

### 16.6 Build order (supersedes §15.7)

| Step | What | Her action |
|---|---|---|
| **J1** | Data truth (§15.7 J1, unchanged) | restart |
| **J1b** | **Refill a gap after reconnect, as if alive** (her ask, 28 Oct ~23:45). (1) Order flow: Dext / GoCharting re-sends the bars after a reconnect ([M]: 12 Oct, a 99-min book gap, Dext had 99 of 99 minutes; 16 Oct, 85 of 85); J1 already keeps Dext's minutes and skips only the book's broken ones. 28 Oct had 0 Dext minutes because Dext never landed for the Nov contract (NSE-61471): fix that. (2) Chain OI: `chain_backfill` refills only once, at start; a mid-day gap (a sleep with no restart: 28 Oct 12:55–12:59 stayed missing) must be refilled from Upstox REST on wake, never clobbering observed minutes. (3) Price + fut OI: Upstox REST 1-min (complete through 28 Oct's sleep), tagged `rest`. (4) The loaders (`handshake.load`, `jarvis.load`) read `chain_backfill` too (base OI = observed OI − its change). (5) On wake, Jarvis replays the blind minutes in order and says one catch-up line (`WHILE I WAS BLIND 12:54–13:00: wall 22,700s CE broke 12:57 · shorts covered −2,146 · high 22,875.5f · fuel spent 13:02`), every stamp at its true minute, tagged backfilled. Not rebuildable: the 1-second book (bid / ask per trade): flow then comes from Dext only | restart; extension reload for the Dext fix |
| **J2** | The brain: `jarvis.py` with §14, the NO TRADE states, `/api/jarvis`, the forward log, the tests, the zone replay rows | restart |
| **J3** | The face: the Trade tab chart layer (bubble, levels, markers) plus the JARVIS right panel (feed + state), live and replay. **Reference design (her choice, 29 Oct ~03:10: "jarvis2 (Fable's)"): `docs/kahani/review/mockup/jarvis2.html` + `JARVIS2-DESIGN.md`**: header (fut / spot / basis / BANKNIFTY / SENSEX / day H-L), the state strip (FIGHT · FUEL · SPEED · ALL 3 · VERDICT both sides · ROOM), crosshair readout, her zones shaded, delta pane, 1m / 3m, OI by strike on the price axis, answer-pending probe, timeline scrubber, the right panel (last-trigger card, feed, command box, voice toggle), the evening-review end card | none (Vite) |
| **J4** | Commands in the panel: draw / zone / watch → Telegram / remove / list / ask (engine sentences) | restart |
| **J5** | The Claude brain (§16.3) plus voice | her API key and cap; she adds voice |

## 17. Managing the trade: her asks, 29 Oct ~01:45 (decided as the trader; the J2 brain carries them)

**Her words:** "the speed thing which we have built that tells us by which the move is flowing and second we can book profit it the move is stalling or getting weaker like as i said we need to flexible as per the market condition and we have bands as well i like to trail .as well or maybe in a good trade where data is getting stronger or one sided plus if all 3 index are moving in same direction plus a red candle on green delt on top of a move or a green candle on red delta . like today at 1 oclock it was a red candle but delta was positive plus sign of absorption and exhaustion".

**Her 1 o'clock example, measured [M]** (Dext 0.8.1 footprint, NIFTY Nov fut, 28 Oct):

| Bar | Candle | Delta | Volume | What it is |
|---|---|---|---|---|
| 12:57–12:59 (3m) | GREEN, close 22,848f | +1,105 | 1,543 lots | the last strong push |
| 13:00–13:02 (3m) | RED, high 22,875.5f | +374 | 1,970 lots (the heaviest) | red candle on green delta at the top |
| 13:03–13:05 (3m) | RED | +99 | 763 lots | exhaustion |

**Her bands** are the session VWAP (hlc3) ± 1 / 2 SD. Rebuilt from the 1-minute bars, they match her zone's logged u2 within about 1 point (12:09: 22,723.9 vs 22,724.5; 13:00: 22,811.2 vs 22,809.4).

**The reads** are computed causally on her 3-minute bars (from 09:15). The demo `mockup/jarvis.html` already shows every one of them.

| Read | Rule |
|---|---|
| **SPEED** | \|3-min delta\| against its own median so far: FAST ≥ 2×, SLOW ≤ 0.5×, with its direction. A gauge, plus a chip on events [I] |
| **TOP / BOTTOM SIGNS n/3** | At a fresh 30-min high or low, three signs: (1) a candle against its delta (red on +delta at a high, green on −delta at a low); (2) absorption: lots per point ≥ 2× the day's 3-min median (effort.py's idea); (3) exhaustion: the bar's delta under half the strongest of the two bars before it. **It speaks at 2 of 3. While a fuel run still drives into the extreme, it is noted, not called** ("fuel still running: not a top yet"). A small tail after a big run has spent (≥ 2× the bar, spent ≤ 10 min ago) does not block the call |
| **ALL 3 IN SYNC** | NIFTY fut, BANKNIFTY and SENSEX all moved ≥ 10 / 25 / 35 pts the same way in 5 min [I]. Shown as a chip (on pushes, MANAGE) and on the gauge, never a line of its own |
| **MANAGE** | After each of her triggers, read at her 3-min closes for 45 min. It speaks only on a change, ≥ 6 min apart: **HOLD** (≥ +15 pts and the data with her: speed, all 3, fuel), **BOOK / TRAIL TIGHT** (≥ +15 pts and any sign against: opposite TOP / BOTTOM SIGNS, speed or all 3 against, fuel against), **AGAINST YOU** (below 0 and 2 signs against). Each line names her **trail band**: the nearest of d2 / d1 / VWAP / u1 / u2 beyond price. Guidance only: she places and moves her own stop |

**What 28 Oct read under these rules** (rows, not rates):
- 13:03: **TOP SIGNS 3/3** at 22,876f.
- 12:45, 12:48 and 12:57: TOP SIGNS while the cover run was live, so "not a top yet" (the breakout continued).
- Her 09:54 SELL: HOLD at +114 pts (10:18), then BOOK / TRAIL TIGHT at +120 pts (10:24), as BOTTOM SIGNS 2/3 appeared at 22,567f.
- Her 13:03 SELL: HOLD at +56 pts (13:21), trail at u2.

**Hers to know:**
- The thresholds (2×, 0.5×, +15 pts, 10 / 25 / 35 pts, 6 min) are [I]: decided as the trader, read forward as rows, a new rev only with a reason in the NOTEPAD.
- SPEED here is a flow-pace read. RAFTAAR's OI speed (`docs/speed/`) joins it in J2; it does not replace it.
- **Build:** J2 (`jarvis.py`) computes these per minute, J3 draws them on the Trade tab, and her marked trade (`voice.py`'s trade) replaces the zone triggers as MANAGE's subject.

**§17 amendment, 29 Oct 10:45 (her catch):** FUEL has two legs, and both already exist; Jarvis reuses them and builds no third.
- the futures OI run (§3.2 RASAD);
- the **Sides read** (`sides.py`, `/api/sides`, shown on the Board): REAL / BACKED / CAPPED / FLAT, call or put writers COV / ADD, and `fuel_side` with its top-2 under water.

The signs rule's "fuel still driving" check counts either one. On 29 Oct, Sides read REAL from 10:20 to 10:30 (call writers covering) while futures OI was flat, so the 10:18 TOP SIGNS would have read "not a top yet". Every live read starts from `/api/board` and `/api/sides`.

**§17 amendment 2, 29 Oct 11:00 (her ask): WRITER FLOW ±7.** Per minute, the 3-minute OI change summed over ATM ±7 strikes, for each side. This is a display read beside Sides; Sides' 9-strike definition is untouched.
- **FUEL ▲:** CE covering ≤ −10L **and** PE building ≥ +10L together. ▼ is the mirror.
- **WRITERS STOPPING (top / bottom risk):** after a fuel stretch, three things together:
  - the covering side goes ≥ −2L or turns to adding;
  - the building side drops under half of its leg peak;
  - delta and speed fade.
- Thresholds [I] come from 29 Oct's legs (NOTEPAD A164).
- **On 29 Oct:**
  - 10:08–10:11: CE −47.0L / PE +27.1L.
  - At the 10:30–10:41 top, CE covering went to 0 and then to +7.2L, PE building fell from +27.1L to +4.9L, and delta turned to −462.
