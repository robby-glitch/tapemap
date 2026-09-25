# PRE-REGISTRATION DRAFT — THE HOLD / FOLD WINDOW, rev 5b (rev 5 written 2026-09-25 16:33 IST; rev 5a 17:20; rev 5b 17:50, by the clock; NOT SIGNED, before any code, UNTESTED)

**Rev 5b** answers the second pass of `REV5-VALIDATE2-REVIEW.md` (17:34). Its verdicts were:
option A SIGNABLE; option B SIGNABLE with should-fixes; "A on a 5-minute grid" NOT YET. Every item
is listed in §H. Wherever the text below says "rev 5a", read it as this draft.

**Base:** `PREREG-merged.md` rev 4, signed 2026-09-25 01:42 (sha256
`e7f50391da94a6a14b76ccc6dff5bc993c1b306859baaee8a78e36a7744709d0`, re-checked 17:20: unchanged).
**Everything rev 5a does not name stands in rev 4, word for word.** Rev 4 stays the rule in force
until Mary signs this. Nothing below is a result.

**What it answers.**
- `REVIEW-2026-09-25.md`:
  - **P0-1 [REG]:** the line breaks on one 1-minute close with zero buffer (§A);
  - **P0-9:** after a FOLD, the STOP shows a line that did not break (§B);
  - **P0-4:** the PAYERS row's precedence (§C);
  - **§3 "Copy and wording", items 6–15** (§D).
- **Rev 5a** answers the adversarial review `REV5-VALIDATE2-REVIEW.md` (verdict NOT YET): must-fix
  M1–M6 and should-fix S1–S7, each listed in §H.

**Her words, 2026-09-24:** *"identifying direction is never my problem but holding a trade is:
closing too early on my trade, getting panicked with even 1 single red candle, or holding a bad
trade in FOMO and not getting out."*

**What had been seen when this was written, so nobody has to guess:**
- the REVIEW, and the adversarial review of rev 5;
- both live replies for her 09-25 trades (`/api/hold?id=…&rows=brief` and `&rows=1`, GET,
  `sigma=0`, read 16:14);
- the rev 4 probe table;
- NIFTY's 09-25 index 1-minute candles (Upstox REST, read 16:2x);
- today's NIFTY OI grid (`/api/oihist`, GET, read 17:1x).

**How the two options came to be.**
- **Option A** (the 3-minute close) was given before any run; rev 5 disclosed it (§E).
- **Option B** (a frozen one-candle buffer) was written in rev 5a on the adversarial review's text
  (its Q1). The review had seen the closes around each break but ran no candidate.
- **B's disclosure run (§E) was done after B's text was fixed.** Nothing in either text was moved
  after it.
- The late-candle rule (§A.0.4) was written from the server's code (`_hold_facts`,
  `_hold_candles`), not from any row.

---

## A. THE LINE BREAK — two complete texts. She signs one.

**The choice is Mary's.** This draft does not recommend by outcome. Each option states its
principle (§A.5), and §E discloses both on the same 35 trades. Whichever she signs replaces:
- rev 4 §2 "Broken = …";
- §3 rule 3;
- the §6 row "break";
- the WATCH hint's line item.

The other option is kept, unsigned, in an appendix of the merged file (§H).

### A.0 Common to both options

**A.0.1 The grid.**
- The session's 3-minute grid from 09:15: 09:15–09:17, …, 15:27–15:29, 125 bars.
- It is the zone machine's grid (CLAUDE.md rule 3; `band_rotation.SCORED_INTERVAL` = 3), and the
  candle of her Kite chart (§1c, her 3-minute export).
- **A bar's close** is the 1-minute close of its last minute: the 12:00 bar closes on the 12:02
  candle. A wick is never a break.

**A.0.2 What stays as rev 4.**
- L, its source, its one-way trail on confirmed 5-minute pivots, and its room, printed from the
  1-minute close every minute.
- The writer's danger-side line, which breaks by the same option as a buyer's.
- **The first bar read** is the first bar whose last minute is after the entry read minute. That
  includes the bar the entry minute sits in.
- Rule 3 cannot fire at the entry minute (M5, unchanged).

**A.0.3 Between two closes.**
- The line's state (broken or not) changes only when a bar's close is read, and stands until the
  next close is read.
- That state is the line's input to the unlatched verdict (§7).
- A forming minute whose 1-minute close is already through the line or the break level:
  - **the word does not change;**
  - the room row prints "through your line by N pts [M] — the 3-min bar closes at HH:MM";
  - under B it adds how far is still left to the break level: "through your line by 1.4 pts [M]
    — 3.5 pts to go to the break level 23,070.3; the 3-min bar closes at HH:MM" (review S-g);
  - this is display only, not a WATCH item.

**A.0.4 Missing and late candles (M5).** The code is the model here.
- **How the server finishes a minute.** A minute is finished when its index candle lands. The
  server waits for it at most `fronts.STALE_MIN` = 3 minutes (`server.py` `_hold_facts`: "A MINUTE
  IS FINISHED WHEN ITS INDEX CANDLE HAS LANDED").
- **How a late candle arrives.** After the wait, the minute is read without its candle. The candle
  is asked for again at most every `HOLD_REFETCH_S` = 15 s (`_hold_candles`). When it lands, that
  minute's record is rebuilt (`r["ix"] is None and t in ix`), and `hold.read` is pure and re-read
  over the whole record. **Rows already logged stay as written** (write-once, rev 4 §8).

The rules:
- **A missing candle inside a bar, when the last due close has been read.**
  - The minute reads **normally**. The line's state is carried (A.0.3); OI, flow and trend do not
    read that candle.
  - Only the room row says "could not check — no candle for HH:MM".
  - **Not PATA NAHI:** the rule could check.
- **A due close that has not landed** (a bar's last-minute candle still missing after the wait).
  - The line **cannot say whether that bar broke**, so it is blind: "could not check — the {bar}
    bar's close has not landed".
  - The word is PATA NAHI, unless a FOLD is latched (M1, unchanged).
  - It stays blind until a close is read. That is either the late candle, or the next bar's close.
- **A late close is read at the minute its candle lands, never before and never back-dated.**
  - Its reading minute (`read_at`) is the first finished minute whose facts carry the candle.
  - **A break found on a late close is a FOLD stamped at `read_at`, never at the bar's minute.**
  - The sentence names both: "FOLD 12:36 — the 12:30–12:32 bar's close (read late, at 12:36)…".
  - Blind rows already written for the minutes between keep what they said.
  - The one tone fires at `read_at`.
  - **§7's FOLD stamp is `read_at`**, the minute she could act. Clause 7's break unit is the bar,
    the tape event.
- **Every bar's close is read once.** A late close is read even if a later bar has already closed.
- **Restarts and imports.**
  - The first live reading minute of every late close, `read_at`, is written **once** into the
    trade's day state and read back on a restart. So a restart re-reads what was read live; the
    record alone would read the close as if on time.
  - Option B's frozen `B` and its minute are kept the same way.
  - The close-time import of an unmarked trade has no live reading. It reads every close at its own
    bar, and its rows are `src: import`, shown apart (rev 4 S5).
- **A close first read from a backfill** (review S-b; the anytime-start rule).
  - **When:** a marked trade's close was never read live, because the server was down across that
    bar and a restart backfilled the candle. There is then no `read_at`.
  - **How it is read:** at its own bar, because that is the only honest reading of the record.
  - **It is tagged:** the row and the latch carry `read_at: null, backfill: true`, and the sentence
    says "(read from backfill after a restart at HH:MM)".
  - **How §7 reads it:** the FOLD stamp is the bar minute, **flagged `backfill`**. It is shown apart
    in every §7 and clause-7 count, and each clause must also hold with the backfilled stamps
    removed. They are never blended with stamps read live.

**A.0.5 The latch (both options).** It is set once and never changes.
- **Rule 3:**
  ```
  {t: read_at, rule: 3, bar: "HH:MM–HH:MM",
   L, src, px: the bar's close [M],
   by: |px − L| to 0.1 [M]}
  ```
  Option B adds `B`, `B_at`, `level`, and `by_level`: |px − level| to 0.1 [M].
- **Rules 4, 5 and 6:**
  ```
  {t, rule, why, L and src: the line as it stood at the FOLD minute}
  ```
  `px` and `by` are null. The field names `L`, `px` and `by` are the ones tonight's code writes.

**A.0.6 Heal (S5).** The sentence and clause 7a use **one** definition.
- A heal is the first later bar close **not beyond the L that broke**. The test is the break's own
  strict comparison (`hold.py` line 174): for a long CE / short PE, beyond is `px < L`. A close
  exactly on L is a heal.
- It is judged against L, never against option B's break level.
- The sentence reads: "· the break has healed since HH:MM (a 3-min close back on your side of
  {L}) — a re-entry is a new trade".
- **When another rule reads FOLD on the unlatched state that minute** (review S-f), it adds "— but
  {rule 4 / 5 / 6's name} reads FOLD now". The sentence must never invite a re-entry into a setup the
  window would refuse. Rev 4's code required the whole unlatched verdict to be HOLD or WATCH; this
  keeps that check as words.
- For rules 4–6 the heal wording is rev 4's.

### A.1 OPTION A — the 3-minute close, buffer 0

> **Broken** = the close of a 3-minute index bar (A.0.1) beyond **L**, buffer 0.
> - Beyond is strict: `px < L` for a long CE / short PE; `px > L` for a long PE / short CE.
> - The line on her screen is the level that breaks: "line 23,075.2 · breaks on a 3-min close
>   below it".
> - **WATCH hint, item (a):** "{IDX} closes a 3-min bar {below / above} {L} — {room} pts away [M];
>   next close {HH:MM}".
> - **Kill clause:** §F, clause 7-A.

### A.2 OPTION B — the 3-minute close, one frozen median candle past the line

> **Broken** = the close of a 3-minute index bar (A.0.1) beyond **the break level**, where the
> break level is **L − B** for a long CE / short PE and **L + B** for a long PE / short CE. Beyond is
> strict.
>
> **B [M]** = the median high − low of the index's own 1-minute candles over the 15 finished
> minutes ending at the minute L was **set** (the entry read) or **last trailed**.
> - All 15 must be present.
> - It is **the same measure as VALIDATE rev 2a §1.3**:
>   - the window is inherited, `QUIET` = `fronts.SLOPE_MARKS` = 15;
>   - the statistic is the median;
>   - the scale is one candle, from her words.
>
> **B is frozen with L.**
> - It is read again only when L trails, and never in between.
> - The break level is **a fixed price**, printed beside L on every surface from the minute L
>   exists: "line 23,075.2 · breaks on a 3-min close below 23,070.3 — one median candle, 4.9 pts
>   [M], read 12:00".
> - A fast bar cannot widen it, because it was read before the bar.
>
> **On a trail, the break level never moves away from price** (review S-d). This is rev 4's own
> trail principle ("one way … never away"), applied to the level.
> - When L trails, the new level is the **nearer to price** of the old level and the new L ∓ B,
>   with B read at the trail.
> - If the old level is kept, the row says so and records `clamped: true`. B keeps the value
>   measured at the trail.
>   - The print reads: "breaks below 23,349.9 — kept; the 10:25 trail would have moved it 0.9 pts
>     away" (NIFTY 09-23, her 09:47 call).
>   - The latch's `level` is always the level actually in force, and `by_level` is measured against
>     it.
> - **In-sample,** the clamp binds on 2 trails (3 trade rows) and changes no first FOLD (§E.1).
>
> **Fewer than 15 candles at that minute** (before 09:29, or a candle missing):
> - B is "could not check — n of 15 candles";
> - until B is read, the line breaks at **buffer 0**, and the row says so;
> - B is read at the first later minute whose own 15-minute window is complete, then frozen.
> - *This fallback is a named choice. It folds more than B, never less.* Every break it produces
>   carries `B: null` (the same key as §G; review S-e).
>
> **The latch** records L, B, `B_at`, the break level, the bar, its close, `by` past L and
> `by_level` past the break level (A.0.5).
>
> **WATCH hint, item (a):** "{IDX} closes a 3-min bar {below / above} {level} (your line {less /
> plus} one candle, {B} pts [M]) — {n} pts away; next close {HH:MM}".
>
> **Kill clause:** §F, clause 7-B.
>
> **The coupling, stated here and in VALIDATE rev 2a:**
> - The window's B and VALIDATE's noise are one measure, read once each.
> - VALIDATE's Room reads **L**, not the break level, under both options: "your line is inside one
>   candle's range".
> - So VALIDATE's facts do not change with this choice, and its outcome reads no break rule
>   (VALIDATE rev 2a §3). Nothing restarts there if B is signed or later killed.
> - PLAN's STOP (§2.1, "the window's line L itself") keeps showing L. Under B it also shows the
>   break level. Its premium-at-risk figure stays measured to L and is labelled so. Both need a
>   PLAN change-log line (§H).

### A.3 The 5-minute close — named as a candidate, not written out

The line is a 5-minute swing (trendbox, PIV 2, 5-minute bars), so a 5-minute close would be the
line's own grid. **It is a candidate that is not written out here, and it cannot be signed from
this draft.**
- **Why it is not written out.** It is not a third principle. It is a time-only rule with the
  distance still zero, which is A's side of the choice between **time only** (A) and **time and
  distance** (B).
- **Why A reads 3 minutes.** 3 minutes is the candle she watches (her Kite chart, §1c) and the zone
  machine's bar. Both are registered.
- **Why it is not a word-swap** (the second pass's must-fix). The 3-minute grid runs through the
  whole text:
  - the 125 bars of §A.0.1;
  - clause 7's heal window, the closes at +3 … +15 (§F.1);
  - the late-break cutoff after 15:14;
  - the hint's "closes a 3-min bar";
  - the §6 row.
  On a 5-minute grid, 15 minutes holds three closes and the cutoff moves. It also has no disclosure
  run.
- **If she wants it,** it needs its own complete text and its own §E rows before a signature. **The
  earlier "one-word change" sentence is struck.**
- **The honest cost of A's argument.** On her chart, a single 3-minute close 0.4 pts through the
  line *is* "1 single red candle". A moves the one-candle fold from a 1-minute candle to a 3-minute
  candle, at any distance.

**Two consecutive 1-minute closes** are also not a candidate.
- It reads the 1-minute candles the review found too noisy, twice.
- It sits on no grid the stack uses.
- "Two" has no source as a close-count.

### A.4 What each option does to P0-1

**P0-1 names two defects:** a single 1-minute close (time) and zero buffer (distance).
- **A** answers the time defect only.
- **B** answers both.

**What neither option does.** VALIDATE gates nothing: a WAIT does not stop an entry, and she decides
(VALIDATE's own header).
- **Her 12:01 CE was never VALIDATE-pressed**, and neither was the 12:05 PE. The window has to be
  right for trades she enters without pressing.
- **VALIDATE reads the noise once, at the check minute.** The line trails toward price afterwards,
  so VALIDATE cannot see a trailed line.
- **On the record, that is the PE.** Its line trailed at 12:25 to the 12:10 swing high, 10 pts from
  price. Under A it then folded on a 0.6-pt close.
- **Under A this is a known, unmitigated cost** of zero buffer: a line that trails into the noise
  folds on the noise.
- **Under B the buffer is re-read at every trail.** So B covers a trailed line whose break stays
  within one candle of the noise read at that trail (§E). A break deeper than that still folds; on
  the PE, at 13:59, 7.8 pts past L (review S-g).

### A.5 For her decision. The principle of each, and what signing it costs.

> **A — the principle.** A break is a close of her chart's own candle through her structure. How
> far through does not matter, exactly as rev 4 read it, but read on the 3-minute candle and never
> on a 1-minute poke that recovers inside its bar.
>
> **What signing A costs, from §E:**
> - it moves 1 of 35 FOLDs and keeps the 12:02 CE FOLD;
> - in-sample, 5 of 8 rule-3 breaks, and 9 of 14 first line breaks, healed within 15 minutes;
> - if the forward rows look like that, clause 7-A kills rule 3. §7's window record then restarts
>   a second time, and she trades on it until ≥ 15 breaks and ≥ 10 sessions are in;
> - VALIDATE's clock no longer restarts (VALIDATE rev 2a §3).
>
> **B — the principle.** A break is a 3-minute close past the line by more than one typical candle
> of the tape's own noise. The noise is measured when the line is drawn, frozen, and printed as a
> level. Her "one single red candle" is, by construction, not enough to fold her.
>
> **What signing B costs, from §E:**
> - it moves 13 of 35 FOLDs, and removes none;
> - most frozen line FOLDs become quiet-clock FOLDs 1–6 minutes later;
> - the CE still folds at 12:05, on a close 8.0 pts through the line and 3.1 pts through the level;
> - the PE holds to 13:59, past her 13:23 exit;
> - in-sample, 1 of 3 rule-3 breaks, and 4 of 12 first line breaks, healed within 15 minutes;
> - it adds a printed level and a named fallback (buffer 0 before 15 candles);
> - it needs `B` and `B_at` kept in day state;
> - PLAN's risk figure stays measured to L, one candle short of the fold.
>
> **Either way, the rows above are disclosed, not chosen on.** If she picks after reading §E, the
> change log records that the choice was made after seeing these rows (as rev 4's S1 did).

---

## B. The display after a FOLD (clarification, not a rule change; P0-9, review S4 and S7)

Once FOLD is latched, the window shows the line from the latch, not the trailed line. "The STOP"
here means the window's line row, PLAN's STOP block and the collapsed line.

**What the STOP shows:**
- **After a rule-3 FOLD:** the line that broke, "broke 12:02 by 1.4 pts [M]". Under B it also
  names the break level: "broke 12:05 by 8.0 pts [M] (3.1 past the break level 23,070.3)".
- **While the index is through it:** "past it by N pts".
- **After a heal (A.0.6):** "broke 12:02 · the index is back N pts {above / below} it", never a
  bare positive room that reads as a live plan.
- **After a rule-4, 5 or 6 FOLD:** the line at the FOLD minute, "held at the FOLD HH:MM".

**The trailed line is detail only:** "the line has since moved to 23,109.1 (5m swing low 14:25) —
detail; a re-entry is a new trade with its own line".

**Collapsed:** `FOLD · contract · line 23,075.2 broke 12:02 by 1.4 pts · since 12:02`.

**Why.** After a FOLD the plan has ended. Rev 4 §3.1 already says the FOLD "shows the time it fired
and the fact".

**The logs.**
- §8's `line` keeps the trailed L (rev 4, unchanged). `latch` is additive (§G).
- **`plan.stop.L` in PLAN's §5 key keeps logging the trailed L** (its registered meaning; the
  `_hold_row` plan key). Only the display changes.
- PLAN §2.1 says STOP is the line "with its trail". Showing the untrailed line after a FOLD is a
  change to PLAN's display, so it needs a line in PLAN's change log and a new §1f hash (§H).
- Hiding PLAN's NEXT WALL after a FOLD (P0-9's last bullet) is also PLAN's, for the same entry.

---

## C. PAYERS precedence — her decision, recorded (P0-4; review S1)

**The case.** On one minute the payers' nearer front is BUILDING, held 3 minutes ("payers
against"), **and** a payers'-side fold is still live.

**What the PAYERS row reads.** **AGAINST**, "writers adding in your way (held 3 min)", with the fold
as a clause: "…; the PE 22,850 fold of 09:52 is still with you".

**The row's precedence:**
1. both sides leaving: flat;
2. payers against: AGAINST, with any live fold as a clause;
3. UNWINDING: for;
4. a live fold: for;
5. adding, not yet held 3 minutes: flat, "n of 3";
6. otherwise: flat.

**Her decision.** The REVIEW tagged the row-state half of P0-4 "her call". **Mary decided it on
2026-09-25, in the evening, in reply to the review:** *"fix every issue there is like has i told u
this has to be the best thing in this app"*.

**What shipped, and when.**
- The change is in `hold.py` tonight (`_payers` tests `qA` first).
- It **ships before this revision is signed**, so the 09-26 rows log rev 4's rules with this row
  precedence.
- **The word is unchanged:** rules 4, 6 and 7 read `qA` directly.
- **The quiet clock is unchanged:** a live payers' fold still counts as **paid** (§3 rule 5).
- The 33-trade probe test stays green.
- What changes:
  - the PAYERS row's state and its fact;
  - the count;
  - `payers.state` in the forward row, on overlap minutes only.

**The half that was a bug.** Printing a for-fact as the WATCH / FOLD reason was a bug against §3's
own text: the entry check names "the one fact against", and the collapsed line names "the one
against-fact".

**What she sees on such a minute.** Both are true, and both are printed: "WATCH — Put writers at
23,100 adding in your way (held 3 min) — adding again [M]; the PE 22,850 fold of 09:52 is still with
you", together with "paid last 09:55".

**Known, and left as registered: the side read (§10.2) keeps its own order**, "UNWINDING, or a live
payers' fold = for; BUILDING = against".
- So on an overlap minute, §10's count has payers "for" while the window's PAYERS row reads
  AGAINST.
- §10's count is printed, and no clause judges it (§10.6 reads side stamps and `stamp_track`).
- Aligning it is a one-line §10 change, offered and not made here.

---

## D. Copy: the window's own registered sentences (REVIEW §3, items 6–15; review M3, M4 and S7)

**Placeholders:**
- `{Pw}` / `{Hw}`: the payers' / holders' writers, "Put writers" or "Call writers" (lower case
  mid-sentence);
- `{k}`: the strike;
- `{sw}`: `board.state_words`, unchanged;
- `{off}` and `{since}`: its fields for an UNWINDING front;
- `{opt}`: put or call;
- `{cap}`: "ceiling above" when the holders are CE writers, "floor below" when they are PE writers;
- `{IDX}`: the index.

Every fact keeps its [M] / [I] tag.

| # | where | rev 4 | rev 5a template → example |
|---|---|---|---|
| 6 | PAYERS, for (UNWINDING) | "PE 23,000 giving back since 09:36 (24% off) — the writers your move forces are leaving" | "{Pw} at {k} are covering — OI {off}% off its peak, giving back since {since} [M] — fuel for your {opt}" → "Put writers at 23,000 are covering — OI 24% off its peak, giving back since 09:36 [M] — fuel for your put". **Writer:** "— in your favour". |
| 6′ | PAYERS, for (a live fold) | "PE 22,850 folded 09:52, 9% off its 09:39 high" | "{Pw} at {fk} folded {ft} — {off}% off their {high_at} high [M] — fuel for your {opt}" |
| 7 | HOLDERS, for | "CE 23,100 still adding (+73.5L) — holding" | "{Hw} at {k} {sw} [M] — the {cap} you holds" → "Call writers at 23,100 still adding (+73.5L) [M] — the ceiling above you holds" |
| 7′ | HOLDERS, against | "… — the side holding your trade is leaving" | "{Hw} at {k} {sw} [M] — the {cap} you is leaving". **Writer (YOUR SIDE):** "{Hw} at {k} (your side) {sw} [M] — " followed by rev 4 §4's own-side clause. |
| 7″ | HOLDERS, a live fold | "PE 23,150 folded 11:56 — the floor stepped" | **Buyer:** "{Hw} at {fk} folded {ft} — the {cap} you stepped [M]" → "Put writers at 23,150 folded 11:56 — the floor below you stepped [M]". **Writer (her own side, rev 4 §4):** "{Hw} at {fk} (your side) folded {ft} [M] — " followed by one of: "spot moving toward your strike — a squeeze" (against); "winners cashing in — your strike is farther from spot than at entry" (for); or "could not check — no ladder window yet". |
| 8 | HOLD · noise | "HOLD · noise — what holds this trade has not changed: …" | Word: **HOLD · NOISE**. **Buyer:** "Your premium is red; the reason has not changed: {s1}; {s2}. Line {room} pts away [M]." **Writer:** "The premium you sold is up; the reason has not changed: …". The condition is rev 4 §3.8's own, signed by role. Short forms: "{pw} covering", "{pw} folded {ft}", "the {ceiling / floor} holds", "flow with you", "the trend rows with you". A plain HOLD: "HOLD — the reason stands: {s1}; {s2}. Line {room} pts away [M]." |
| 9 | WATCH hint | a sentence joined with "or", missing rule 4's cases | **A list headed "FOLD if any one of:".** Every item alone folds her from the current state (§D.1). |
| 10 | WATCH, payers against with a live fold (§C) | "WATCH — PE 22,850 folded 09:52, 9% off its 09:39 high" | "WATCH — {Pw} at {k} adding in your way (held 3 min) — {sw} [M]; the {Q} {fk} fold of {ft} is still with you" |
| 11 | collapsed, nothing against | "checked, none — against" | "nothing against you", followed by " · {family} could not check" for each blind family (e.g. "nothing against you · flow could not check"). A blind family is never folded into "nothing". |
| 12 | STOP risk (**PLAN §3's sentence**, carried through PLAN's change log) | "≈ ₹72 [I] at risk if it broke now" | **"≈ ₹{X} [I] of premium between here and the line"**. No "exit", and no break rule named (PLAN §2.5: never "exit"; never one exit). Under B, PLAN adds the break level as its own line (§A.2). |
| 13 | OI blind | "HOLD · structure only — OI could not check: fronts forming: …, 7 so far" | Word: **HOLD · OI BLIND**. Sentence: "could not check OI: {why}; {what reads} decide{s}". `{what reads}` is built from the rows that read at that minute ("the line and trend decide; flow could not check — too thin to read"). For fronts forming, `{why}` = "fronts forming, {n} of 15 marks (OI reads from about {HH:MM} [I])". On WATCH / FOLD the suffix is "(OI blind — could not check: {why})". |
| 14 | PATA NAHI | "PATA NAHI — could not check — no index candle at 12:31" | Entry minute with no candle: "PATA NAHI — no {IDX} candle for {t}; the line can't be set." A due close not landed (A.0.4): "PATA NAHI — the {bar} bar's close has not landed; the line can't say whether it broke. Last word: {W} since {since}." With no earlier word: "Last word: none yet since entry." |
| 15 | entry check, FOLD at entry | "You entered into a broken setup — the reason was already gone at HH:MM, because …" | "You entered into a broken setup — the reason was already gone (read {et}): {why}." **The check (server):** "If you enter now, you enter into a broken setup — the reason is already gone (read {asof}): {why}." |

### D.1 The WATCH hint (item 9; review M4)

The hint lists **every** condition that alone would fold her from the current unlatched state.
Rev 4 §3.7 promises that WATCH "always says what would turn it into FOLD".

- **(a) Rule 3, the line.** Option A's or option B's item (§A.1 / §A.2). While the line is blind:
  "the line could not check — {why}".
- **(b) Rule 4, positioning flipped**, by state:
  - payers against, holders not yet: "the {hw} {above / below} leave for 3 min — {n} of 3";
  - holders against, payers not yet: "{pw} add in your way for 3 min — {n} of 3";
  - neither: "the {hw} leave for 3 min **and** {pw} add in your way for 3 min";
  - OI blind: "positioning could not check — {why}".
  - **For a writer,** "holders against" is her own side leaving *under a squeeze* (rev 4 §4). When
    `dpx` is blind: "positioning flip could not check — no ladder window yet". Rule 4 is then
    unavailable to her, as rev 4 S-a says.
- **(c) Rule 5, buyers only:** "nothing pays for 15 readable min — quiet {n} of 15".
- **(d) Rule 6, two families.** The families are OI ({pw} adding in your way for 3 min), flow (CVD
  strong and prints dominant) and trend (2 of 5m / 15m / 1h).
  - With one family against: "one more family turns against you: {the others, joined 'or'}".
  - With none against: "two families turn against you, of: {the three}".
  - **A blind family is marked, not offered:** "flow (could not check now — too thin to read)". It
    cannot count while it is blind (rev 4 §3.6).

**The rev 4 §3 WATCH-at-entry example, restated** (her 12:01 CE, read 12:00, from the live reply;
option A's line item):

*"You entered into WATCH — put writers at 23,150 folded 11:56 — the floor below you stepped [M]; it
becomes FOLD if any one of: NIFTY closes a 3-min bar below 23,075.2 — 2 pts away [M], next close
12:02 · the put writers below leave for 3 min and call writers add in your way for 3 min · two
families turn against you, of: call writers adding in your way for 3 min, flow (CVD strong and
prints dominant), the trend rows (2 of 5m / 15m / 1h) · nothing pays for 15 readable min — quiet 0
of 15."*

Under option B, the first item reads: "NIFTY closes a 3-min bar below 23,070.3 (your line less one
candle, 4.9 pts [M]) — 7 pts away, next close 12:02".

### D.2 The FOLD reasons, and the FOLD-at-entry example

- **Rule 3 (A):** "FOLD — the line is broken: {IDX}'s {bar} bar closed {px}, {by} pts {below /
  above} your line {L} ({src}) [M]".
  → "…NIFTY's 12:00–12:02 bar closed 23,073.8, 1.4 pts below your line 23,075.2 (5m swing low
  11:25) [M]".
- **Rule 3 (B):** the same, plus "— {by_level} past the break level {level} (one candle, {B} pts,
  read {B_at}) [M]".
  → "…NIFTY's 12:03–12:05 bar closed 23,067.2, 8.0 pts below your line 23,075.2 (5m swing low
  11:25) — 3.1 past the break level 23,070.3 (one candle, 4.9 pts, read 12:00) [M]".
- **A late close:** "FOLD {read_at} — … the {bar} bar's close (read late, at {read_at}) …".
- **Rule 4:** "FOLD — positioning flipped: {payers against}; and {holders against}".
- **Rule 5:** unchanged.
- **Rule 6:** "FOLD — two families against you: {fam 1}; and {fam 2}".

**FOLD at entry** (NIFTY 09-23, read 09:46; exact to the templates on the frozen facts):

*"You entered into a broken setup — the reason was already gone (read 09:46): two families against
you: call writers at 23,400 adding in your way (held 3 min) — still adding (+56.1L) [M]; and flow
against you: CVD -529 since 09:30 (rank 0.67) · 2 sell / 0 buy prints of size [I]."*

### D.3 Tests (`test_hold.py` as it stood at 16:45)

**These assertions change:**
- **79–80:** the entry-check FOLD example.
  - The prefix becomes "…the reason was already gone (read 09:46): two families against you: ".
  - `"CE 23,400"` becomes `"call writers at 23,400"`.
  - "writers adding in its way (held 3 min)" becomes "adding in your way (held 3 min)".
- **179–180:** the §C fact text, per item 10.
- **199:** the hint's join, per D.1.
- **209:** rules 4–6 now carry `L` and `src`.

**These are unchanged:**
- 81–82;
- 205–207;
- the 33-trade probe, which stays green under **A** because nothing moved.
- **Under B the probe changes:** 11 frozen rows move (§E), and the table must be re-pinned to B's
  rows.

**New tests owed:**
- NIFTY 09-25 frozen and pinned: the CE at 12:02 (A) / 12:05 (B); the PE at 12:32 (A) / 13:59 (B);
- a forming minute through the line: the word does not change;
- a missing mid-bar candle: not PATA NAHI;
- a due close missing: PATA NAHI;
- **a late-landing close:** its FOLD is stamped at `read_at`, not at the bar, and a restart reads
  the same;
- B's fallback before 09:29;
- §C on `hold_trade_1000.json`'s real 09:55 minute.

---

## E. Disclosed — options A and B, run on the same 35 trades

**Method.**
- **Scratch only** (session scratchpad `rev5/`):
  - `probe3.py` (A);
  - `probeB.py` (A and B in one run; `probeB_table.txt`, `probeB_out.json`);
  - `liveB.py` (today's two trades; `liveB_out.txt`).
- `hold.line` was replaced in-process by each option's copy. The copy changes only the break.
- It ran on the as-built rev 4 `hold.py` (the 16:04 backup, sha256 `774c3ec8…`), with
  `test_hold.py`'s harness.
- **Today's two trades.** Their line comes from today's REST candles and `hold.pivots`, which
  reproduce the live L values 23,075.2, 23,084.8, 23,091.6 and 23,121.6. Rules 4–6 are rebuilt from
  the live per-minute rows.
  - `qA` is read from the *partner* trade's HOLDERS row, because it is the same nearer front and
    rev 4's precedence could print a fold over it.
  - **The rebuild reproduces both live rev 4 FOLDs**: 12:02 by rule 3, and 12:30 by rule 3.
- **No repo file was written.** Counts and rows only, never a rate.

### E.1 The 35 trades, A beside B

In the table, a line fold is shown by how far its close went past L; B also shows the break level
and when it was read.

| trade | entry | rev 4 | **A** | **B** |
|---|---|---|---|---|
| 09-22 09:42 NIFTY 23300CE | FOLD | 09:41 two | 09:41 two | 09:41 two |
| 09-22 10:32 / 10:42 / 10:43 / 10:44 NIFTY 23550PE, 10:52 23500PE (5, one break) | WATCH ×4, HOLD | 11:14 line, 2.5 past L | same | **11:20 quiet** (B 6.65 @11:10; the level 23,397.4 held at the 11:14 and 11:17 closes) |
| 09-22 13:48 NIFTY 23500PE | WATCH | 14:14 line, 38.5 | same | 14:14 line, 38.5 past L, 33.0 past level (B 5.55 @13:47) |
| 09-23 09:18 NIFTY 23450CE | HOLD | 09:44 quiet | same | same |
| 09-23 09:47 NIFTY 23450CE | FOLD | 09:46 two | same | same |
| 09-23 09:49 NIFTY 23400PE | WATCH | 10:17 line, 1.5 | same | **10:19 two** (B 5.25 @10:15) |
| 09-23 10:00 NIFTY 23450CE | WATCH | 10:05 two | same | same |
| 09-23 10:19 / 10:33 / 11:07 NIFTY 23450CE (3, one break) | HOLD | 12:47 line, 0.4 | same | **12:52 quiet** (B 4.3 @12:45) |
| 09-23 11:32 SENSEX 74900CE | HOLD | 12:44 quiet | same | same |
| 09-24 09:42 SENSEX 74200PE | WATCH | 10:16 quiet | same | same |
| 09-24 10:19 SENSEX 74200PE | HOLD | 10:43 flipped | same | same |
| 09-24 12:32 / 12:35 / 12:44 SENSEX puts | HOLD | 13:14 quiet | same | same |
| 09-24 13:26 / 13:41 / 13:43 / 13:44 / 13:45 / 13:54 SENSEX puts | WATCH / HOLD | 14:08 quiet | same | same |
| 09-24 13:57 SENSEX 73800PE | HOLD | 14:10 quiet | same | same |
| 09-24 14:23 SENSEX 73800PE | HOLD | 14:35 line, 11.9 | same | **14:36 quiet** (B 30.23 @14:30) |
| EX 09-23 09:57 SENSEX zone BUY | WATCH | 10:11 line, 0.5 | same | **12:44 quiet** (B 19.64 @09:59) |
| EX 09-23 09:57 NIFTY zone BUY | WATCH | 10:05 two | same | same |
| EX 09-23 11:15 NIFTY WRITER short | WATCH | 11:18 flipped | same | same |
| EX 09-24 10:30 SENSEX WRITER short CE | HOLD | 10:43 flipped | same | same |
| EX 09-24 09:45 SENSEX WRITER short PE | FOLD | 09:44 two | same | same |
| **live: NIFTY 23100 CE, fill 12:01:21 @ 113.55, read 12:00** | WATCH | 12:02 line, 1.4; premium 111.20 [I] | **12:02 line, 1.4**, unchanged | **12:05 line**: the 12:03–12:05 bar closed 23,067.2, 8.0 past L, 3.1 past level 23,070.3 (B 4.9 @12:00); premium 111.35 [I] |
| **live: NIFTY 23200 PE, fill 12:05:28 @ 155.40, read 12:04** | WATCH | 12:30 line, 2.7; premium 144.55 [I] | **12:32 line, 0.6**; premium 146.40 [I] | **13:59 line**: L trailed to 23,055.45 at 13:25 (B 5.3 @13:25, level 23,060.75); the 13:57–13:59 bar closed 23,063.2, 7.8 past L, 2.45 past level; premium 151.30 [I] |

**The counts, side by side:**

| | **A** | **B** |
|---|---|---|
| unchanged / moved / disappeared, of 35 | **34 / 1 / 0** | **22 / 13 / 0** |
| the 12:02 CE | **stays at 12:02** (the 12:00 bar's own close), by 1.4 | **moves to 12:05**, by rule 3 (8.0 past L) |
| the 12:04 PE | **moves to 12:32**, on a smaller break (0.6) | **moves to 13:59**, by rule 3 on the trailed line. It is HOLD / WATCH through her 13:23 exit. |
| entry verdicts changed | 0 of 35 | 0 of 35 |
| where the moved FOLDs went | — | frozen: 10 to the quiet clock (rule 5) 1–6 min later (or 2 h 33 min, EX SENSEX); 1 to two families (10:19); live: 2 later line folds |

**Why A moved none of the 33.** All 12 frozen rule-3 FOLDs (6 distinct breaks) landed on a bar's
last minute.
- The fixture changes its close on every minute. The review checked all three positions in the bar.
- If the first crossing fell on any of the bar's three minutes alike, six of six on the last minute
  is one arrangement in 729. Seven of eight, with today's, is about one in 390.
- **So "A moves none of the 33" says nothing about what A will do forward.** Forward, about two in
  three first crossings should fall inside a bar, where A reads them later (review S2).

**Premium at the FOLD**, in points from entry [I]: all rows are in `probeB_table.txt`. Under B's
moved frozen rows:
- the 11:14 trades: +29.4 / −10.5 / −10.8 / −7.2 / −26.1 at 11:14, and +34.1 / −5.8 / −6.2 / −2.6 /
  −21.2 at 11:20;
- 10:17 → 10:19: −14.2 → −19.2;
- 12:47 → 12:52: +17.0 / +12.3 / +3.1 → +20.3 / +15.7 / +6.5;
- 14:35 → 14:36: −67.9 → −93.7;
- EX SENSEX, 10:11 → 12:44: −27.2 → +110.0.

Shown so nobody has to guess; neither option was written on them.

### E.2 The closes around each break (what the review saw; bar-last minutes marked *)

| break | 1-minute index closes [M] |
|---|---|
| NIFTY 09-22 11:14 (PE, L 23,390.75) | 11:11* 23,382.2 · 11:12 23,383.15 · 11:13 23,387.95 · **11:14* 23,393.3** · 11:15 23,391.35 · 11:16 23,394.25 · 11:17* 23,396.35 · 11:18 23,392.6 |
| NIFTY 09-22 14:14 (PE, L 23,344.05) | 14:11* 23,325.75 · 14:12 23,339.4 · 14:13 23,333.5 · **14:14* 23,382.6** · 14:15 23,373.95 · 14:16 23,376.55 · 14:17* 23,385.45 |
| NIFTY 09-23 10:17 (PE, L 23,384.0) | 10:14* 23,364.85 · 10:15 23,374.45 · 10:16 23,378.85 · **10:17* 23,385.45** · 10:18 23,392.5 · 10:19 23,393.25 · 10:20* 23,394.85 |
| NIFTY 09-23 12:47 (CE, L 23,443.7) | 12:44* 23,448.85 · 12:45 23,449.6 · 12:46 23,444.85 · **12:47* 23,443.3** · 12:48 23,443.75 · 12:49 23,446.5 · 12:50* 23,448.85 |
| SENSEX 09-24 14:35 (PE, L 73,689.95) | 14:32* 73,661.08 · 14:33 73,644.89 · 14:34 73,657.28 · **14:35* 73,701.88** · 14:36 73,718.76 · 14:37 73,727.67 · 14:38* 73,764.02 |
| SENSEX 09-23 10:11 (CE, L 74,629.1) | 10:08* 74,680.64 · 10:09 74,662.54 · 10:10 74,659.34 · **10:11* 74,628.56** · 10:12 74,629.7 · 10:13 74,644.32 · 10:14* 74,646.4 |
| NIFTY 09-25 CE (L 23,075.2) | 11:59* 23,076.25 · 12:00 23,076.85 · 12:01 23,075.45 · **12:02* 23,073.8** (A) · 12:03 23,063.35 · 12:04 23,066.65 · **12:05* 23,067.2** (B) · 12:06 23,065.3 |
| NIFTY 09-25 PE (L 23,084.8, then 23,055.45) | 12:29* 23,082.45 · **12:30 23,087.5** (rev 4) · 12:31 23,087.95 · **12:32* 23,085.4** (A) · 12:33 23,082.65 · 12:35* 23,074.95 · … · 13:56* 23,054.45 · 13:57 23,050.05 · 13:58 23,053.8 · **13:59* 23,063.2** (B) · 14:00 23,089.25 · 14:02* 23,095.0 |

**How the breaks compare with the noise.** The medians are over the 15 minutes to each break [M],
and in the review's re-check they include today's two.
- **7 of 8** rule-3 breaks under A were smaller than one median candle: 12:02 broke by 1.4 against
  4.9, and 12:32 by 0.6 against 4.4.

### E.3 Heals, both options, on the one definition (A.0.6 and F.1)

The units are distinct breaks, per population. A heal is a later 3-minute close not beyond the L
that broke, within 15 clock minutes.

| | **A** | **B** |
|---|---|---|
| rule-3 FOLD breaks | 8 (6 frozen + 2 live); **5 healed**: 11:14→11:20, 12:47→12:50, SENSEX 10:11→10:14, CE 12:02→12:11, PE 12:32→12:35 | 3 (09-22 14:14, CE 12:05, PE 13:59); **1 healed**: CE 12:05→12:11 |
| first line break of each trade, whatever folded first (clause 7a's unit, F.1) | buyers 11, **6 healed**; writers 3, **3 healed** | buyers 9, **2 healed**; writers 3, **2 healed** |

**All in-sample; none counts toward §F.**
- **If the forward rows look like this, 7a-A fires** for buyers (more than half healed), **and 7a-B
  does not.**
- The heal clause measures exactly the distance A leaves at zero (review Q2). That is a property of
  the construction, stated before the numbers, and the numbers agree.

**7a's unit changed in rev 5a, and this is when it was fixed (review S-c).**
- Rev 5 counted distinct **rule-3 FOLD** breaks. Rev 5a counts each trade's **first line break,
  whatever rule folded first**.
- **The change was made after both units' in-sample counts had been computed** (the second row
  above was run first, for comparison, and then adopted as the unit).
- **The reason is principle, not the count.** Under B most line breaks come *after* another rule has
  folded, so a rule-3-only unit would barely see B's line at all. The heal is a property of the tape
  and the line, not of which rule won.
- Both units point the same way on both options, so the change moves no conclusion. It is disclosed
  because it was made with the counts in view.

**B's never-away clamp (§A.2, rev 5b), run on the same trades** (`probeBc.py`):
- It binds on 2 trails (3 trade rows): NIFTY 09-23 10:25, by 0.9 pts, and SENSEX 09-23 13:10, by
  3.34 pts, the latter shared by two trades.
- It changes **no** first FOLD among the 33, and never binds on today's two (both trails there moved
  the level nearer).
- §E.1's B column is therefore unchanged by it.

### E.4 What VALIDATE does and does not do here (review M2)

- VALIDATE flags a line inside one candle of price **at the check minute, for checks she presses.**
  Nothing more.
- **It gates nothing.** Neither live trade was a VALIDATE press.
- **Nothing in VALIDATE covers a line that trails into the noise later.** On the record that is the
  PE: VALIDATE's Room would have read WITH at 12:04 (24.95 pts against a median of 5.3), and the
  line trailed to 10 pts at 12:25.
- **Under A,** that case is uncovered: it folded at 12:32 on 0.6 pts.
- **Under B,** the trail re-reads the buffer, and the PE held to 13:59.

---

## F. Falsifiers for the changed clause, and the forward clocks

### F.1 Clause 7's definitions (both options; review M6 and S6)

- **The unit for 7a** is a **distinct first line break**.
  - It is each trade's first line break (`line.broken_at` in the rows, which run to 15:29 whatever
    she does, rev 4 N3), **whatever rule folded first**.
  - It is keyed (index, bar, L, population).
  - Trades that share it count once.
  - A break shared by a buyer's line and a writer's danger-side line counts once **in each**
    population.
- **Which trades:** marked **and imported** (`src: marked | import`). 7a is a property of the tape
  and the line.
- **Heal:** A.0.6. It is judged against the L that broke, with the break's strict test; a close
  exactly on L is a heal.
  - The window is **15 clock minutes** from the break bar's last minute: the closes at +3, +6, +9,
    +12 and +15.
  - A bar whose close was not read (its row was written without the candle) is not a heal. It does
    not extend the window.
- **Late breaks:** a break after 15:14 has fewer than five closes. It is flagged `short`, shown
  apart, and **excluded** from 7a's count, as a truncated window is never padded (`stamp_track`).
- **The unit for 7b** is rule-3 FOLD stamps (`fold_rule = 3`, stamped at `read_at`) against noise
  stamps. **7b is judged deduplicated.**
  - Each distinct break's excursion is the median of its stamps' excursions.
  - Noise stamps are deduplicated the same way, by (index, minute, direction).
  - The per-trade rows are shown too.
- **The excursion** is rev 4 §7's: the option's favourable excursion over 30 finished minutes, as a
  percentage of the stamp-minute premium.

### F.2 Clause 7-A (if she signs A)

Judged per population (buyers and writers never pooled), on the rows of the signed option only
(`prereg: "rev5-A"`, §G). **7a and 7b are judged separately, each on its own count** (review S-a):
- **7a:** at ≥ 15 distinct first line breaks and ≥ 10 sessions;
- **7b:** at ≥ 15 distinct rule-3 breaks **and** ≥ 15 noise stamps and ≥ 10 sessions;
- each in any case at 30 sessions.

Rule 3 is re-registered if any of these holds:
- **7a.** On **more than half** of the distinct first line breaks, a heal comes within 15 minutes.
- **7b.** Rule-3 FOLD stamps are **not** followed by smaller excursions than noise stamps. It is
  judged as two distributions, medians and full rows, split by index, never a rate.
- **7c.** 7a's or 7b's result reverses when the single best day is removed. The best day is the
  session whose removal moves that comparison most toward failing.

**If it dies:** **option B's text (§A.2) is the one on file.** §7's record restarts, and the old rows
stay told apart by `prereg`.

**Inconclusive at 30 sessions,** per part and per population:
- **7a short of its 15:** rule 3 is inconclusive for that population, and its verdicts stay DRAFT.
- **7b short of its 15, but 7a judged:** 7b is **inconclusive and says so**. Rule 3 then stands or
  falls on 7a (and on 7a's own 7c) alone, and every verdict carries "7b not judged — fewer than 15
  rule-3 breaks".
- 7b never holds 7a hostage, and 7a never waits for 7b.

### F.3 Clause 7-B (if she signs B)

Everything is as 7-A, including the separate counts (rows `prereg: "rev5-B"`), with these
differences:
- **7a-B** tests whether **one candle is enough.** The heal is still a close back on her side of
  **L**, not merely back inside the break level.
- **7a-B is decidable at 30 sessions without 7b-B** (review S-a).
  - Its unit, each trade's first line break, comes whatever rule folded first. In-sample, B gave 12
    first line breaks against 3 rule-3 breaks.
  - **7b-B**, which needs 15 rule-3 breaks, is the part expected to be short under B, because B hands
    most breaks to the quiet clock (§E.1).
  - **If 7b-B is short at 30 sessions,** it is inconclusive, and B stands or falls on 7a-B alone,
    marked so. The rule-5 FOLDs that B produces instead are judged by §7 clause 5, which is unchanged
    in form.
- Breaks made under the fallback (buffer 0 before B is read, `B: null`) are **shown apart and
  excluded.** They are option A's breaks, not B's.
- Breaks at a clamped level (`clamped: true`, §A.2) are counted, and flagged.

**If it dies,** rule 3 is re-registered, with no candidate on file. Option A is weaker than B by
construction, so it is not B's fallback. §7's record restarts.

### F.4 The forward clocks

| clause | changed by rev 5a? | its forward record |
|---|---|---|
| §3 rule 3, the break | **yes** (A or B) | — |
| §7 B1–B3, B5, W1–W2 and falsifier clauses 1, 3 and 4 | They read FOLD stamps, noise stamps or the unlatched state, and rule 3 moves all of them. | **Reset** at rev 5a's first session after the code lands. Rev 4's rows stay rev 4's own record, **never pooled** (told apart by `prereg`). |
| **§7 B4 and clause 2** (FOLD at the entry minute) | **no.** Rule 3 cannot fire at the entry minute (M5). | **Continue** (review S3). |
| §7 clause 5 (rule 5's kill) | It reads rule-5 stamps against noise stamps. Under B, rule-3 folds turn into rule-5 folds (§E). | **Reset.** |
| §7 clause 6 (time bound) | follows the clauses above | per clause |
| §7 clause 7 (new) | new | Starts at rev 5a's first session. |
| §10, and §10.6 | no. It reads no line. | Continues. |
| PLAN P1 / P2 | no. A touch reads no verdict. | Continues. |
| VALIDATE rev 1 §4 | no. The entry check is untouched by rule 3. | Unaffected. It is retired on VALIDATE rev 2a's own terms. |
| **VALIDATE rev 2a** | **no.** Its outcome reads no break rule (rev 2a §3). | **No restart** when rule 3 is signed, or when clause 7 later kills it. |
| §B display, §D copy | display and copy | No reset. |
| §C precedence | row state only; her decision, shipped tonight | No reset. No clause reads `payers.state`. |

**Rev 4 §7's hazards, amended:**
- the hazard "buffer 0 produced a 2-point break on 09-22 11:14" now reads per option. Under A, the
  rule-3 breaks on the record were 0.4, 0.5, 1.5, 2.5, 11.9 and 38.5 pts, and live 0.6 and 1.4.
  Under B, they were 38.5 past L (33.0 past the level), and live 8.0 and 7.8 past L;
- "the latch keeps FOLD after a break price reverses within a minute" now reads **"… within a
  bar"**.

---

## G. What else moves in rev 4's text

**§6 parameters, rows changed or added:**

| parameter | value | from |
|---|---|---|
| break (A) | a 3-minute index close (09:15 grid) beyond L, buffer 0 | CLAUDE.md rule 3; `SCORED_INTERVAL` = 3; her chart (§1c) |
| break (B) | a 3-minute close beyond L ∓ B; B = the median 1-min high − low over 15 finished minutes at L's set or trail, all present, frozen; on a trail the level is the nearer to price of the old and the new (never away); buffer 0 until read (named fallback) | as A; `QUIET` = `SLOPE_MARKS` = 15; the median and one candle as VALIDATE rev 2b §1.3; rev 4's "never away" trail |
| the line between closes | the last read close's state | §A.0.3; no number |
| missing and late closes | a due close not landed is blind; a late close is read at `read_at` | §A.0.4; `STALE_MIN` = 3, `HOLD_REFETCH_S` = 15 (the server's own) |
| clause 7: heal window · majority | 15 clock minutes (five closes) · more than half | N5's reversal window, `FOLD_LIVE` · N1 / N5 |

**§8, the trade row. Additive keys only:**
```
line:  {…, px: the 1-min close [M], bar_close: true|false, read_at: HH:MM|null, backfill: bool,
        B: pts|null, B_at: HH:MM|null, level: price|null, clamped: bool},   -- B keys under B only
latch: null | {t, rule, bar, L, src, px, by, read_at, backfill,
               B, B_at, level, by_level, clamped},                          -- A.0.5
prereg: "rev5-A" | "rev5-B"
```

**`prereg`** names the option the row was written under (review S-e).
- Rev 4's rows lack the key.
- If clause 7 later kills the signed option and the other is signed, its rows are told apart by
  this value, never by a date.
- The unset buffer is `B: null` everywhere; there is no separate `b` flag.

**Day state (the trade's):** `read_at` of each late close and, under B, `B`, `B_at`, the level in
force, and `clamped`. Each is written once and read back on a restart (A.0.4).

---

## H. Change log

**rev 5 DRAFT, 2026-09-25 16:33 IST.** Not signed.
- §A: rule 3 on the 3-minute close.
- §B: display after a FOLD.
- §C: payers precedence.
- §D: copy items 6–15.
- §E: disclosed.
- §F: clause 7 and the clocks.
- §G: the §6 rows and §8 keys.

**rev 5a DRAFT, 2026-09-25 17:20 IST (read from the clock).** Not signed. From
`REV5-VALIDATE2-REVIEW.md`. **Must-fixes:**
- **M1:**
  - two complete, signable texts, **A** (the 3-minute close) and **B** (the 3-minute close past one
    frozen median candle, printed as a level), co-equal, with the choice hers;
  - struck: "nothing supplies a unit of distance" and "no precedent";
  - the 5-minute close is named as A on another grid, not a third principle, and not run;
  - A and B each get their own disclosure (§E.1) and kill clause (§F.2, §F.3);
  - 7-A's "on file" now points at B's complete text.
- **M2:**
  - "caught before the trade" is removed;
  - stated instead: VALIDATE gates nothing; neither live trade was pressed; VALIDATE cannot see a
    trailed line;
  - the PE is named as A's uncovered cost (§A.4, §E.4).
- **M3:** item 12 is now "≈ ₹{X} [I] of premium between here and the line": no "exit", no merged
  exits, and no break rule written into PLAN.
- **M4:** the WATCH hint lists every condition that alone folds her, including rule 4's three states,
  the writer's squeeze condition, and a blind flow marked rather than offered (§D.1).
- **M5:**
  - a missing mid-bar candle is not PATA NAHI when the line's state is carried;
  - a due close not landed is blind;
  - **a late close is read at `read_at`, and a FOLD is never stamped in the past;**
  - `read_at` (and B) are kept in day state for restart-exactness;
  - the import reads on time, `src: import`;
  - all of this is written against `_hold_facts` / `_hold_candles` as they stand.
- **M6:** heal, late breaks, closeless bars, and which trades (§F.1), for both options.

**Should-fixes, all taken:**
- **S1:** §C records her decision and its time, and that the change ships before signing. The side
  read's differing order is stated as known.
- **S2:** the 1-in-729 / 1-in-390 note, and what A's "0 moved" does not say.
- **S3:** B4 and clause 2 keep their record.
- **S4:** `px`; `plan.stop.L` logs the trailed L; PLAN's display change goes through PLAN's change
  log.
- **S5:** one heal definition.
- **S6:** 7b needs ≥ 15 noise stamps, is judged deduplicated, and is inconclusive per population;
  shared breaks count once per population.
- **S7:** items 13, 11, 7″, 8 and §B after a heal.

**Anchors (review Q6).** On signing, the chosen option and §B–§G are **merged into
`PREREG-merged.md` as rev 5**, the way PLAN rev 3 was merged verbatim from its addendum.
- The unchosen option goes into an appendix marked "not signed".
- The new sha256 goes into research-findings **§1e**, beside rev 4's, which stays as history.
- **PLAN** needs one change-log entry and a new §1f hash for:
  - §4's "break: as rev 4" → "as the window's registration in force";
  - item 12;
  - §B's STOP display after a FOLD (and NEXT WALL hidden);
  - under B, the break-level line.

**No number was invented.**
- New uses of inherited numbers:
  - the 3-minute grid (CLAUDE.md rule 3);
  - 15 candles for B (`QUIET` / `SLOPE_MARKS`);
  - 15 minutes and "more than half" for clause 7 (N5, N1).
- Named choices that are not numbers:
  - B's median and one-candle scale (shared with VALIDATE rev 2a);
  - B's buffer-0 fallback;
  - carrying the line's state between closes.

**Nothing Mary decided was reopened.**

**rev 5b DRAFT, 2026-09-25 17:50 IST (read from the clock).** Not signed. From the second pass of
`REV5-VALIDATE2-REVIEW.md` (17:34).
- **Second-pass must-fix, "A on a 5-minute grid" (§A.3):** the "one-word change" sentence is struck.
  - The 5-minute close is now named only as a candidate that is not written out.
  - The reason: it is a time-only rule on A's side of the choice, and the 3-minute grid runs through
    §A.0.1, §F.1, the 15:14 cutoff, the hint and §6.
  - It cannot be signed from this draft without its own complete text and §E rows.
- **S-a, 7a waits on 7b (§F.2, §F.3):** 7a and 7b are judged separately, each at its own ≥ 15.
  - 7a-B is decidable at 30 sessions without 7b-B.
  - A short 7b is inconclusive and says so, and rule 3 then stands on 7a alone, marked.
- **S-d, the level can move away (§A.2):** on a trail, the break level is the nearer to price of the
  old and the new, which is rev 4's "never away".
  - It is recorded with `clamped: true`.
  - In-sample it binds on 2 trails and changes no first FOLD (§E.3, `probeBc.py`). The second pass
    said it never happened in-sample; it did, on the frozen days, not on today's two.
- **S-e, the option in the rows (§G):** `prereg: "rev5-A" | "rev5-B"`, and `B: null` replaces `b:
  null`.
- **Also taken:**
  - **S-b:** a close first read from a backfill is tagged `backfill: true`, stamped at its bar,
    shown apart in §7, and every clause must hold without those stamps.
  - **S-c:** 7a's unit change is logged, with its timing (after both counts were seen) and its reason
    (§E.3).
  - **S-f:** the heal sentence adds "— but {rule} reads FOLD now" when another rule does.
  - **S-g:** B's forming-minute print shows the distance still to go to the level; §A.4's "covers
    exactly this case" is reworded.
- **No new number.** The clamp is rev 4's trail principle. `prereg`, `backfill` and `clamped` are
  labels, not parameters.
