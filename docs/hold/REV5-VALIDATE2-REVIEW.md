# Review: `PREREG-rev5-DRAFT.md` (the window, rev 5) and `VALIDATE-rev2-DRAFT.md` (the word, rev 2)

Independent adversarial review, in the same role as `PLAN-REVIEW.md` and `PLAN-ADDENDUM-REVIEW.md`.
Written 2026-09-25 17:03 IST (read from the clock). This is the only file written. No server was
touched, nothing was POSTed, no `log=1` was used, and nothing was committed.

**What I checked against:**
- `PREREG-merged.md` rev 4, `VALIDATE-PREREG.md` rev 1 and `PLAN-PREREG.md` rev 3;
- research-findings §1e–§1g, and `REVIEW-2026-09-25.md`;
- the code the logs come from: `hold.py`, `hold_log.py`, `validate.py`, `plan.py`,
  `band_rotation.py` and the `_hold_*` functions in `server.py`;
- the drafter's scratch: `rev5/probe3.py`, `probe3_table.txt`, `noise.py`, `outcome.py`, the two live
  replies and today's NIFTY 1-minute file;
- the 16:04 backup in `scratchpad/orig`.

**What I ran, all read-only:**
- **The frozen fixtures** (`docs/hold/opus/scratch/facts_*.json.gz`): does the index close change on
  every minute, or only on 3-minute boundaries? It changes on every minute, at all three positions in
  the bar. No position has larger moves or larger ranges.
- **The six frozen breaks:** the 1-minute closes around each one, to see where in the bar each fell.
- **Today's NIFTY 1-minute file:** the 15-minute medians at 12:00, 12:02, 12:04, 12:30 and 12:32.
- **A `diff`** of this evening's `hold.py`, `validate.py` and `plan.py` against the 16:04 backup.

**What I did not run:** no candidate rule (buffer, two closes, 5-minute close) over any trade. While
verifying §E I saw the closes around each break. Nothing below rests on them, and this review is not
a disclosure run of any candidate.

---

## Part 1 — `PREREG-rev5-DRAFT.md`

### What checks out

- **§E reproduces.**
  - The rev 4 column matches `probe_rev3.txt` row for row.
  - The 12 rule-3 FOLDs are 6 distinct breaks. All six fall on a bar's last minute: 11:14, 14:14,
    10:17, 12:47, 14:35 and 10:11 are each 2 minutes past a 3-minute boundary from 09:15.
  - The fixture really is 1-minute data (checked above), so "0 moved" is real. It is not an artefact
    of 3-minute data.
- **"7 of 8 smaller than one median candle" holds**, including today's two, whose medians the table
  does not print:
  - 12:02 broke by 1.4 against a median of 4.9;
  - 12:32 broke by 0.6 against a median of 4.4.
- **The 12:00 WATCH-at-entry example is faithful.** The live rows show CE 23,150 and PE 23,150 both
  folded at 11:56. So both of these are true: VALIDATE §6's "Paying WITH (a CE 23,150 fold live)" and
  this draft's "put writers at 23,150 folded 11:56".
- **§C moves neither the word nor the clock.** Verified in `hold.py`:
  - rules 4, 6 and 7 read `qA` directly (lines 281, 291, 300);
  - the clock reads the raw `q_pays` / `q_fold` (line 273);
  - only the row's state, its fact and the count change.
- **These match the code:**
  - the 125-bar grid;
  - the first bar read (`i > e`, as in rev 4);
  - the server's 3-minute wait for a late candle (`server.py:1971`);
  - the additive §8 keys.
- **The disclosure is unusually honest.** It says outright three things against its own rule:
  - the primary rule leaves the motivating case unchanged;
  - 7 of 8 breaks were noise-sized;
  - its own clause 7a would likely fire.

### Must-fix

**M1 — The case against the buffer is contradicted by the companion draft, and it argues against a
version nobody has to register.**

- **The contradiction.**
  - §A.6 #2: *"CLAUDE.md rule 3 supplies a unit of time for this stack. Nothing supplies a unit of
    distance."* and *"Its statistic (the median) and its scale (one candle) have no precedent in the
    line."*
  - VALIDATE rev 2, written four minutes later, registers exactly that unit for exactly this line:
    - §1.3: *"The median is **a new choice of statistic** … 'one typical candle', her own unit of
      panic ('even 1 single red candle'). The scale is 1×, with no multiplier."*
    - §5: *"the scale is her words, with no multiplier"*.
  - Her words are a unit of distance in one draft and "nothing" in the other. Both cannot be signed
    as written.
- **The strawman.** The other three objections are to a buffer that *"moves every minute with the
  tape"*. Nothing requires that.
  - A buffer frozen when L is set or trailed is a level.
  - It is printed on her chart from the minute L exists.
  - The latch records that same printed level.
  - A fast bar cannot widen it, because it was read before the bar.
  - Freezing it answers all three objections: "not the line on her chart", "a level no chart ever
    showed", and "widest exactly when the tape is fastest".
- **The candidate that answers both defects was not considered.**
  - The draft: *"A 3-minute close with a buffer was not considered: two changes and two new choices
    at once."*
  - P0-1 names two defects, and §A.5 says so itself. The combined rule is the only candidate that
    answers both.
  - If VALIDATE rev 2 is signed, the combined rule's statistic and scale are the same two choices
    already made there. It adds no new number, and only the one named fallback in Q1.
- **The line's own grid is missing.** The line is a 5-minute swing (trendbox, PIV 2, 5-minute bars).
  Rule 3's "3-minute is canonical" is the zone machine's grid (`SCORED_INTERVAL`, `RUN_WINDOW`),
  which the line does not use.
  - A 5-minute close is the line's most native time rule, and it is not named.
  - The best argument for 3 over 5 is not made either: 3 minutes is the candle on her Kite chart
    (research-findings §1c). That argument cuts both ways (Q1).
- **Fix.**
  - Strike "Nothing supplies a unit of distance" and the "no precedent" line.
  - Name the 5-minute close, with the reason it was not chosen.
  - Write the buffer as a complete, frozen-level clause; Q1 gives one. Her choice in the box is then
    between two complete texts, not between a complete text and a strawman.
  - Which rule leads is hers to sign. The draft does not have to change its lead to be signable, but
    it must stop arguing against a version it is not offering.
  - §F's *"If it dies: the distance candidate (§A.6 #2) is the one on file"* currently points at the
    strawman. Point it at the frozen clause.

**M2 — §E's claim that the 12:02 case "is caught before the trade" is false as stated. Her second
live trade shows why.**

- §E: *"VALIDATE rev 2 … reads that entry's ROOM as AGAINST … That is where this case is caught,
  before the trade, not by moving the line after it."*
- **(a) VALIDATE blocks nothing.** Its own header: *"It gates nothing; she decides."* A WAIT does not
  stop the entry, and the window still folds her on the next noise-sized close.
- **(b) Her 12:01 CE was not a VALIDATE press.** VALIDATE §6: *"They were not VALIDATE presses."* The
  window has to be right for trades she enters without pressing.
- **(c) The 12:04 PE was not caught either.**
  - VALIDATE §6 reads its Room as WITH: *"stop 25 pts, outside the noise (5.3 pts [M])"*.
  - It still folded, on a 0.6-point 3-minute close, because by 12:30 the line had trailed to the
    12:10 swing high.
  - VALIDATE checks the noise once, at entry. The line trails toward price afterwards, so the check at
    entry cannot see a trailed line.
- **Fix.**
  - Replace the sentence with what is true. VALIDATE flags a line inside the noise at the check
    minute, for checks she presses. Nothing covers a line that trails inside the noise later; on the
    record, that is the PE.
  - State this in §A.5 as the known cost of zero buffer.

**M3 — Copy item 12 smuggles a PLAN rule change: it names the line as her exit.**

- Item 12: *"≈ ₹{X} [I] of premium between here and the line — the exit after a 3-min close through
  it costs more"*.
- **What PLAN registers:**
  - §2.5: *"The plan never prints 'exit'"*, and *"Which one governs her exit is hers: 'depends on
    market'"*;
  - the header: the plan *"never merges its two exits into one"*.
- **What the sentence does:**
  - It assumes she exits at the line's close. That merges the two exits and chooses for her.
  - PLAN's own "not shown — a single exit" line uses the word only to refuse to name an exit.
  - It also writes rev 5's "3-min close" into PLAN, which would be false if rev 5 is not signed.
- **Fix:** drop the clause: "≈ ₹{X} [I] of premium between here and the line". Or state the fact
  without an exit: "… a break is read at the 3-min bar's close, not at the line". Either way it goes
  through PLAN's own change log and hash, as the draft already says.

**M4 — The re-registered WATCH hint (item 9) says "any one of", but it misses rule 4.**

- Item (b) appears *"only when payers are against and holders not yet"*. The mirror case is missing.
- **The missing case:** holders are against (held 3 minutes) and payers are not yet.
  - One event then folds her: payers adding in her way for 3 minutes is rule 4, FOLD.
  - The hint prints (c) instead, "two families turn against you", because holders-against is not one
    of the families. It tells her she needs two things when one folds her.
- **With neither against,** rule 4's pair (holders leave AND payers add) is absent from the list
  altogether.
- **The gap is inherited.** Rev 4's code has it: `_hint` adds the rule-4 item only when
  `qA and not rA` (`hold.py:444`). Rev 5 re-registers the same list as rule-derived text. Rev 4 §3
  rule 7 promises that WATCH "always says what would turn it into FOLD".
- **Fix.**
  - Add (b′), only when holders are against and payers not yet: "{pw} adding in your way for 3 min —
    {n} of 3".
  - With neither against, add (b″): "the {hw} leave for 3 min **and** {pw} add in your way for
    3 min".
  - Do the same for writers; rule 4 applies to them (rev 4 M2).
  - When FLOW is blind, drop flow from (c) or mark it "could not check" (rev 4 §3.6). Otherwise the
    list names a family that cannot turn.

**M5 — §A.3's blind rules contradict §A.2, and they contradict how the code reads a late candle.**

- **(a) A missing candle mid-bar is not blind for the rule.**
  - §A.3: *"A candle missing inside the bar … That minute is blind and reads PATA NAHI."*
  - §A.2: *"The line's state changes only at a bar's close. Broken or not broken, it then stands
    until the next close."*
  - Mid-bar, nothing the verdict reads is missing. The line's state is carried over, and OI, flow and
    trend do not read that candle. Only the room cannot be printed.
  - So PATA NAHI there is a "could not check" when the rule *could* check (CLAUDE.md rule 6).
  - Rev 4 made the minute blind because it read the break every minute. That reason is gone.
  - **Fix:** either read the minute normally, with "room: could not check — no candle for HH:MM", or
    give a reason that survives §A.2.
- **(b) A late candle revives a "closeless" bar.**
  - §A.3: *"A candle missing at the bar's last minute: the bar has no close … the bar cannot break
    the line."*
  - `hold.read` is pure, and it is re-run over the whole record on every tick.
  - `_hold_facts` re-reads a minute when its candle lands late (`server.py:2007`,
    `r["ix"] is None and t in ix`).
  - So when a late candle lands (a REST backfill after the 3-minute wait), the bar has a close again,
    and a FOLD appears stamped at that past minute. By then, rows saying PATA NAHI have already been
    written for that minute.
  - "Cannot break the line" is not what the code would do. Rev 4 §2's restart-exactness says the late
    candle is the fact.
  - **Fix:** say which rule governs. One lean choice that keeps restart-exactness:
    - the close is read when its candle lands;
    - a break found late is stamped at its bar's last minute;
    - rows already written keep what was read at the time;
    - the tone fires when the FOLD is first read;
    - the falsifier's FOLD stamp is the latch minute.
  - Then write test 3 with a late-landing candle, not only a missing one.

**M6 — Clause 7a needs four definitions before it can be computed without judgement.**

- **"On her side."** At buffer 0 a close can sit exactly on L. The record already has one: NIFTY
  09-23, L 23,443.7, and the 12:48 close sat 0.0 from it. That minute is not a bar close, so it is
  moot there, but the same will happen on a close.
  - Define a heal as "a bar close not beyond L", using the same strict test as the break
    (`hold.py:174`).
- **Late breaks.** A break at 15:20 has three closes left, not five. Say whether such breaks are
  excluded, counted, or shown apart, as `stamp_track` does with `short`.
- **A bar with no close inside the 15 minutes.** Say that it is not a heal, and that the 15 minutes
  are clock minutes.
- **Which trades.** 7a is a property of the tape, so imported trades (`src: import`) should count.
  Rev 4 never said whether §7 reads imports; say it for clause 7.

### Should-fix

**S1 — §C: the row-state half of P0-4 was "her call", and the code changed before she signed.**

- **What each document says.**
  - The REVIEW tagged P0-4 [BUG] / [HER CALL]: *"The word is unchanged; the row state and the count
    change. That is her call."*
  - §C says instead: *"It is being fixed in code on 2026-09-25 evening, as a bug against §2's own
    definition."*
- **Half of that is right.**
  - Printing a for-fact as the WATCH/FOLD reason was a bug against §3. The entry check names "the one
    fact against", and the collapsed line shows "the one against-fact".
  - The row's single state and the count were never registered. Choosing their precedence is a
    choice.
- **Tonight's code already has it.** The diff against the 16:04 backup shows `_payers` testing `qA`
  first (`hold.py:377-381`). If rev 5 is not signed before the open, the 09-26 rows log rev 4's rules
  with a row precedence nobody registered.
- **Fix.** Record her words on the row precedence in §C, or say that the row-state part stays out of
  the running code until she signs.
- **The side read differs, and should say so.**
  - §10.2's payers fact keeps its own registered order, for first: *"UNWINDING, or a live payers'
    fold = for; BUILDING = against"*.
  - So on an overlap minute, the side read counts the payers "for" while the window's PAYERS row reads
    AGAINST.
  - Say that this is known, or align the two through §10's own change log.

**S2 — §E should say how improbable "0 moved" is.**
- Six of six distinct breaks landed on a bar's last minute. If breaks fell at random within the bar,
  that is about 1 in 729. Seven of eight, counting today's, is about 1 in 390.
- The fixture changes its close on every minute, so this is a coincidence, not an artefact.
- It follows that "the 3-minute close moves none of the 33" says nothing about what the rule will do
  forward. Forward, about two in three first crossings will fall inside a bar.
- §A.5's *"moves none of the 33 frozen FOLDs"* should carry that sentence.

**S3 — Reset only what rule 3 moves.**
- §F resets *"B1–B5, W1–W2 and falsifier clauses 1–6"*.
- B4 and clause 2 count FOLDs at the entry minute, and rule 3 cannot fire there (rev 4 M5, restated in
  §A.1). Rev 5 does not touch them, so they can keep their record.
- This is REVIEW §6's "no defect fast-path" complaint, and here honouring it costs nothing.

**S4 — The latch's field names, and PLAN's logged STOP after a FOLD.**
- **Field names.** §A.4 and §G name the latch fields `close`, `by`, `bar`. The code that landed
  tonight records `L`, `px`, `by` (`hold.py:323-324`). Pick one name.
- **PLAN's logged L.** §B makes PLAN's STOP show the latched line after a FOLD, and says §8's `line`
  keeps the trailed L. It does not say which L `plan.stop.L` logs (`server.py:2319`). State it.
- **PLAN's change log.** PLAN §2.1 says STOP is the line, with its "trail". Showing the untrailed line
  after a FOLD is a change to PLAN's display, so it belongs in PLAN's change-log entry alongside the
  §4 row.

**S5 — One word, two heals.**
- **The sentence's heal.** In code, it is the first minute the *unlatched* verdict is HOLD or WATCH
  (`hold.py:314`). That reads the trailed L, and it also needs no rule-4, 5 or 6 FOLD.
- **Clause 7a's heal.** A 3-minute close back across the *latched* L.
- **The gap.** §D's "(a 3-min close back inside {L})" does not say which L.
- **Fix:** use 7a's definition for the sentence, so that the screen and the falsifier count the same
  thing.

**S6 — Clause 7's triggers and populations.**
- **7b's trigger.** 7b compares rule-3 FOLD stamps with noise stamps, but it is triggered only by
  "≥ 15 distinct rule-3 breaks". Add "≥ 15 noise stamps", as rev 4 clause 1 has.
- **7b's unit.** 7b counts per trade, and five trades shared the 09-22 11:14 break. That is the very
  pseudo-replication 7a's unit avoids. Show 7b deduplicated by break id as well, and say which of the
  two is judged.
- **Inconclusive.** "Inconclusive … the window stays DRAFT" should read "*that population's* window"
  (rev 4 clause 6).
- **Shared breaks.** A break shared by a buyer's line and a writer's danger-side line counts once in
  each population. Say so.

**S7 — Copy that states more than is true.**
- **Item 13.** "the line, flow and trend decide" is false when flow is blind. Flow was blind in every
  morning reply, and on SENSEX it is blind most minutes.
  - The stated reason for departing from "PRICE ONLY" (*"because flow is read too"*) fails in exactly
    those minutes.
  - Build the clause from what actually reads.
- **Item 11.** "nothing against you" can print when a family could not be checked (flow too thin to
  read). Add the blind family to the collapsed line. Otherwise it reads as "checked, none" over
  something that was not checked.
- **Item 7″** has no writer form. A writer's own-side fold reads *for* when spot moves away (rev 4 §4).
- **Item 8.** "Your premium is red" is ambiguous for a writer.
- **§B, after a heal.** "past it by N pts" becomes a positive room to the broken line ("6 pts"). That
  can read as a live plan again, which is exactly P0-9's complaint. Consider "broke 12:02 · the index
  is back N pts above it".

### Notes, not fixes
- **The method is fully disclosed:** scratch only, run on the 16:04 backup (not tonight's file), with
  the harness named. The "grid shifted one minute" check is a good control.
- **§E's CE median uses the entry's window.** It uses 11:46–12:00, the entry's window. The break's own
  window, 11:48–12:02, gives the same 4.9, so nothing changes.

### Verdict: **NOT YET**

Must-fix M1–M6.
- M1 and M2 are about what the draft asks her to decide.
- M3 and M4 are registered sentences that would tell her something false.
- M5 and M6 are definitions that the code and the falsifier need.

None of them needs a new number.

---

## Part 2 — `VALIDATE-rev2-DRAFT.md`

### What checks out

- **The setup's age is exact for an arm.**
  - `ago` counts from the event bar's last minute (`server.py:2212-2215`,
    `seen = bar_last_minute(t, 3)`).
  - The zone machine drops a reference when `i − ref_i > RUN_WINDOW` (`band_rotation.py:1079`).
  - So "`ago` ≤ 30" is exactly "within the 10 bars after the arm bar".
  - A re-arm writes a new arm row (PLAN-ADDENDUM-REVIEW), so the latest arm's clock restarts just as
    the machine's does.
- **The word is strike-free, as §2 claims.**
  - Every fact reads the index, the fronts or the zone rows.
  - The premium reaches `hold.read` only through the noise tag, which no fact reads.
  - So the unit's argument against strike-shopping holds.
- **"Three AGAINST without a FOLD cannot occur" is right.** Paying has no AGAINST state, and Right now
  AGAINST is already NO. So only Setup and Room can be AGAINST without a FOLD, which is at most two.
- **The outcome is read on the index, in points.** That removes the cheap-strike bias P1-17 named.
- **Units cannot overlap.** Within one (index, direction), no two units' 30-minute windows overlap.
- **The one in-view choice is properly disclosed.** "Latest event, either side" is flagged as made
  with 09:43 on screen, and it is shown to move no word.
- **Right now is unaffected by rev 5.** Rule 3 cannot fire at entry.

### Must-fix

**M1 — The outcome row cannot yet be written the way the draft describes.**

- **(a) Nothing is named to write it.**
  - §3: *"It is written once its 30 finished minutes are in"*.
  - The check route logs only on a press (`log=1`, `server.py:2285`). Nothing runs 30 minutes after a
    check.
  - `_hold_tick` writes only trade rows and side rows.
  - **Fix.** Name the writer: the per-minute tick, for presses whose 30 minutes have finished,
    completed by the close-time import (the `stamp_track` pattern).
  - Say that it re-creates the hypothetical trade from the press row: idx, read minute, d, and
    t0 = read minute + 1, as `_hold_check` does.
- **(b) The log key collides.**
  - `hold_log.key("check", r)` is `(idx, t, k, side, role)` (`hold_log.py:32-33`).
  - An outcome row has no k, side or role, so a long-CE outcome and a long-PE outcome at the same
    (idx, t) get the same key.
  - Whether the second one is written then depends on whether both land in the same `append` call.
  - §3's *"Keyed (idx, t, d, 'outcome')"* needs a new branch in `key()`. That code change is owed, and
    it is not listed.
- **(c) Late outcomes are undefined.**
  - After 14:59 the outcome window is cut short at 15:29.
  - §4 excludes only `same minute` and `not scored`. So a late GO that runs out of time scores
    `neither`, and that counts against P1.
  - Say whether these `short` units are counted, excluded, or shown apart.
- **(d) A blind line at the check minute is undefined.** If the line is blind or cannot be set at the
  check minute, `hold.read` returns no line and `first` has no value. Add "not scored — could not
  check: {why}".

**M2 — The outcome mixes two principles, and the mix ties the word's clock to rev 5's fate.**

- **The two ends are read differently.**
  - The rung counts as reached on a 1-minute wick (PLAN §2.4's touch).
  - The stop counts as broken only by the window's close rule: a 1-minute close under rev 4, or a
    3-minute close under rev 5, which stamps up to 2 minutes after the crossing.
  - And *"Only the line counts as the stop; the window's other FOLD rules do not."*
- **The two principles:**
  - If the outcome measures **room**, the geometry the Room fact votes on, both ends should be read the
    same way: first passage, meaning the 1-minute low or high reaching the rung or L.
  - If it measures **her experience of the window**, the stop is the window's first FOLD, by any rule.
  - The draft's mix has neither one's justification.
- **The consequence.**
  - Because the outcome reads the break rule, rev 2's clock restarts whenever the break rule changes
    (§4).
  - Rev 5's own §E expects clause 7a to kill rule 3. That is a second restart, and the draft does not
    mention it.
- **The target and Room disagree about a GIVING WAY wall.**
  - §3: *"The rung is THE PLAN's rung at the check minute: a wall (whatever its word)"*.
  - §1.3: a GIVING WAY wall, *"Under Room … is read exactly as no wall"*.
  - So take a GO whose rung is a GIVING WAY wall 3 pts away. Room reads WITH, because that wall caps
    nothing, and the check then scores "rung first" almost by construction.
  - P1 is inflated by exactly the walls Room says are not in the way.
- **Fix.** Choose one principle and state it.
  - The choice that removes the coupling is a touch at both ends: first passage to the rung level or
    to L, on 1-minute highs and lows. Then nothing restarts when the break rule changes.
  - Make the target the first level Room caps with: skip GIVING WAY walls to the next sized front,
    else the session extreme. Or say why a GIVING WAY wall is a fair target.

**M3 — P1 and P2 are absolute majorities, with no control and no stated principle.**

- **The choice is listed, not justified.**
  - §5 lists *"a per-word majority in place of rev 1's GO-versus-NO comparison of excursions"* as a
    new choice. It gives no reason anywhere.
  - The REVIEW asked for a change of outcome and of unit (P1-17), not of the comparison.
- **The layout of the levels decides these majorities more than the word does.**
  - Take a GO whose rung is DEFENDED, STALLED or a session extreme. Room WITH requires that rung to be
    at least as far away as the stop.
  - For an index with no drift, the chance of reaching the farther level first is at most even. And
    "neither within 30 minutes" also counts against P1.
  - So P1 can fail for a word that does discriminate. For example, GO rung-first 6 of 16 against NO's
    1 of 16 deletes the word.
  - P2 counts "neither" as a success, so any word passes it whenever the stops and rungs are both far.
- **P1 is held hostage by NO.**
  - Judging needs *"≥ 15 scored GO units **and** ≥ 15 scored NO units"*.
  - A NO is a FOLD at entry on the first press of a 30-minute block, and rev 4 B4 predicts that FOLD
    at entry is a minority.
  - So the GO test can sit inconclusive for 30 sessions, waiting for NO units.
- **Fix.**
  - Keep rev 1's comparative form on the new outcome: GO units' rung-first count against NO units',
    with every row shown and WAIT shown as the control.
  - Or state the principle that makes an absolute majority the right test, and what it is judged
    against.
  - Either way, judge each word once it has its own ≥ 15 units.

### Should-fix

**S1 — The age window for a trigger rests on a fact that is only true of arms.**
- §1.1: *"It is the one window the machine gives an event to stay live."*
- `RUN_WINDOW` is how long an **arm** waits for a trigger (`band_rotation.py:1079`). A trigger's life
  in the machine is its re-fire lock, which stays open until the stop or VWAP.
- The draft already lists this as a "new use", so the use itself is disclosed. What needs fixing is
  the reason.
- Either say why 10 bars is right for a trigger, or read a trigger as live while its lock is open.
  That is the machine's own state, and it needs no number.

**S2 — Room compares a rounded room with an unrounded median.**
- `hold.line` rounds the room to a whole point (`hold.py:177`), and `plan.stop.room` carries that
  rounded value. The noise median is to 0.05.
- So a 4.6-point stop rounds to 5 and reads "outside" a 4.9 median.
- Compare the unrounded room, to 0.1 like `by`. Do the same for a tie against the cap.

**S3 — "A NEITHER always carries its absence kind" is false as written.**
- WATCH, "gate illegal" and "two events disagree" are all reads, and §3's own schema gives them
  `absence: null`.
- Say instead: a NEITHER that is an absence carries its kind; a NEITHER that is a read says what was
  read.

**S4 — Units across indices.**
- NIFTY and SENSEX units at the same minute are one market move.
- Flag co-timed units, as PLAN's `also_wall_touch` does, and let the judgement be read with them
  removed.
- Say whether P1 and P2 are judged pooled or per index. §4 says only that they are "shown split".

**S5 — Show the `not scored` units.**
- Three kinds of unit are never judged:
  - price discovery (no rung);
  - same-minute outcomes;
  - after M1(d), blind lines.
- Show their count beside P1 and P2, so that a word that is mostly GO in price discovery is visible.

**S6 — Copy gaps.**
- "Your stop is {s} pts away; the next wall ({side} {k}, {WORD}) is only {r}" has no form for a
  session-extreme cap.
- When Setup and Room are both AGAINST, say which sentence leads.
- **A divergence from PLAN to state.** The session-extreme touch is scored here but excluded from
  PLAN §6 ("not counted in §6"). That is fine for a separate registration. One line saying so stops a
  reader "fixing" one to match the other.

**S7 — §6 should say plainly what the 12:04 PE shows.**
- Room read WITH (25 pts against a noise of 5.3), and the trade still stopped on a 0.6-point break,
  because the line trailed.
- Room is a fact about the entry minute only. This is the same point as rev 5 M2, and it belongs in
  the disclosure of the fact that was meant to catch it.

### Verdict: **NOT YET**

Must-fix M1–M3.
- M1 is about whether the outcome can be computed at all.
- M2 and M3 decide whether the falsifier actually tests the word.

None of them needs a new number.

---

## Part 3 — The six questions

### Q1. Is the 3-minute close principled? Should the draft lead with a noise buffer?

**As a unit of time, the 3-minute close is principled. But it is cited for the wrong object, and it
answers only half of P0-1.**

- **The citation.** "3-minute is canonical" is rule 3 of the **zone**: the grid the bands and the
  machine run on. The line is a 5-minute swing on the index, so its own grid is 5 minutes. That
  candidate is not even named (M1).
- **The argument the draft does not make.** The strongest case for 3 minutes is that it is the candle
  on her Kite chart. That argument cuts both ways.
  - On her chart, a single 3-minute close 0.4 pts through the line *is* "1 single red candle".
  - The rule moves her panic from a 1-minute candle to a 3-minute one. It still folds on one candle,
    at any distance.
- **What a longer bar filters.** A close at the end of a longer bar filters only pokes that reverse
  inside the bar.
  - It is simply every third 1-minute close: it checks less often.
  - It never asks the close to be far from the line.
  - P0-1's defect, "a break the tape's own noise cannot trip", is a distance defect. The draft says so
    itself: *"It keeps the distance at zero, on purpose."*

**On principle, and not on the 12:02 row, the draft should not present the 3-minute close alone as
P0-1's fix.**
- The distance half needs a distance, and the stack now has one: VALIDATE rev 2's median 1-minute
  range.
- That measure has an inherited window (15), a named statistic (the median), and her own scale (one
  candle).
- The draft should lead with the combined rule, or at least set a complete, co-equal text beside the
  3-minute close. Which one leads is hers to sign.

**A signable noise-buffer clause, with no invented number:**

> **Broken** = the close of a 3-minute index bar (09:15 grid) beyond L by **more than B** [M].
> - **B** = the median high − low of the index's own 1-minute candles over the 15 finished minutes
>   ending at the minute L was set (the entry read) or last trailed. It is the same measure as
>   VALIDATE rev 2 §1.3:
>   - the window is `QUIET` = `fronts.SLOPE_MARKS` = 15;
>   - the statistic is the median;
>   - the scale is one candle.
> - **B is frozen with L.** It is read again only when L trails, never in between.
>   - The break level is L − B for a long CE or a short PE, and L + B for a long PE or a short CE.
>   - It is a fixed price, printed beside L on every surface from the minute L exists: "line 23,075.2 ·
>     breaks on a 3-min close below 23,070.3 — one median candle, 4.9 pts [M], read 12:00".
> - **Fewer than 15 candles at that minute:** B is "could not check — n of 15 candles".
>   - Until 15 candles exist, the line breaks at buffer 0, and the row says so.
>   - B is read at the first minute 15 candles exist, then frozen.
>   - *This fallback is a choice, and it is named: it folds more than signed rev 4 does, never less.*
> - **The latch records** L, B, the break level, the bar, its close, and how far past L and past the
>   break level it closed.
> - **The WATCH hint, item (a):** "NIFTY closes a 3-min bar below 23,070.3 (your line less one
>   candle) — N pts away; next close HH:MM".
> - **Clause 7a stays as it is.** A heal is a later 3-minute close back on her side of **L** within 15
>   minutes. It then tests whether one candle was enough.
> - **The coupling, stated in both files:** the window and VALIDATE read one noise measure. If the
>   window adopts B, the fold level is room + B away, so one of two things must happen:
>   - VALIDATE's "your stop is inside one candle's range" becomes "your line is inside one candle's
>     range"; or
>   - the noise half of Room is dropped as redundant.
>   - Choose one. Do not count the same noise twice.

If she chooses this after reading §E, the change log says so, as the draft already proposes. The full
disclosure run is then done before signing. I did not run it.

### Q2. Clause 7a: is it well-defined, computable forward, and not trivially pre-failed?

- **Computable: yes,** once the four definitions in rev 5 M6 are added.
  - It reads `line.px`, `line.bar_close` and `latch.L` from the trade rows. Those rows run to 15:29
    whatever she does (rev 4 §8).
  - The unit, a distinct break (index + bar + L), is right.
  - "More than half" and 15 minutes are both inherited.
- **Not trivially pre-failed in logic, but pre-failed in expectation.** That comes from how the rule
  is built, not from this sample.
  - With buffer 0, the break and the heal are two crossings of the same level.
  - A close a fraction of a point past L needs only a fraction of a point back to heal.
  - So any zero-width rule, at a level that price keeps revisiting, will heal on noise-sized breaks.
    The clause measures exactly the distance the rule leaves at zero.
  - The in-sample record agrees (5 of 8), and the draft says so: *"If the forward rows look like this
    record, §F's clause 7a kills rule 3 as registered here."*
- **The cost of signing it anyway, which is not in the decision box:**
  - she trades on a rule the record says folds on noise, until there are ≥ 15 distinct breaks and
    ≥ 10 sessions;
  - then *"§7's record restarts again"*, a second full reset of the window;
  - VALIDATE rev 2's clock restarts as well, because its outcome reads the break rule (VALIDATE M2).
  - Put that cost in the box.
- **With a buffer, the same clause becomes a fair test:** is one candle enough?

### Q3. VALIDATE's outcome: can it be computed for every check? Is the unit free of pseudo-replication?

**Case by case:**
- **A buyer's check with a wall rung:** computable once VALIDATE M1 is fixed (the writer, the key,
  `short`, the blind line). As written, the target disagrees with Room about GIVING WAY walls (M2).
- **A session-extreme rung:** scored, and computable. It counts as reached when the 1-minute high or
  low reaches the extreme as it stood at the check. This differs from PLAN §6, which excludes session
  touches; say so (S6).
- **No rung ("price discovery"):** `not scored`, excluded from P1 and P2, and shown. Computable.
  Report the count (S5).
- **A writer:** no outcome row by construction (`word: null`, "hers needs its own registration").
  Her presses are logged and nothing is judged. That is honest and computable. It simply means she has
  no falsifier.

**The unit is free of pseudo-replication within (index, direction).**
- The word and the outcome are both strike-free, so three strikes pressed in one minute are one unit.
- Units are at least 30 minutes apart, so no two units' windows overlap.

**Three dependencies remain:**
- NIFTY and SENSEX units at the same minute are one market move (S4).
- A long CE and a long PE on one index at one minute read the same price path.
- Units on one trend day depend on each other, and only the best-day removal guards against that.

**One design effect to state.**
- The unit is her first press in the block, whatever its word. So a WAIT at 10:00 hides a GO at 10:10.
- That is deterministic and resists word-shopping, and it is right.
- But it means the GO count depends on when she first presses.

### Q4. Do the two drafts interact, and is the coupling stated?

They interact in five places. Only one is fully stated, and one is stated only in part.

1. **One noise measure, two verdicts.** VALIDATE registers the median 1-minute range as the stop's
   noise. Rev 5 rejects the identical measure for the line, and says no unit of distance exists.
   - *Not stated as a contradiction.* Rev 5 §A.5 only calls it "a pre-trade floor, not a break rule".
2. **The division of labour.** Noise is handled before the trade by VALIDATE, and the trade itself
   runs at zero buffer. That is the two drafts' joint design.
   - It is stated only as rev 5 §E's "caught before the trade".
   - That claim fails for trades she does not press, for WAITs she overrides, and for trailed lines
     (rev 5 M2, VALIDATE S7). *Not stated correctly.*
3. **VALIDATE's outcome reads the window's break rule.**
   - *Stated* for rev 5 signed after rev 2 (§4's restart).
   - *Not stated* for rev 5's own clause 7a replacing rule 3, which rev 5 §E expects.
4. **If the window ever adopts a buffer,** VALIDATE's "your stop is inside one candle's range" stops
   being true, because the fold level would be room + B away. *Not stated.*
5. **Right now** is untouched by rev 5, because rule 3 cannot fire at entry. *Stated,* and true.

- The simplest way to decouple items 3 and 4 is VALIDATE M2's outcome, read by a touch at both ends.
- The simplest way to make items 1 and 2 coherent is to sign the window's break with VALIDATE's own
  noise measure (Q1).

### Q5. Is each copy amendment wording only, or does it change a rule?

**Rev 5 §D and the FOLD reasons:**

| item | verdict |
|---|---|
| 6, 6′ (payers for) | Wording. "covering" for UNWINDING interprets the §1d state, fairly. |
| 7, 7′ (holders) | Wording. |
| 7″ (holders' fold) | Wording, but it has no form for a writer (S7). |
| 8 (HOLD · NOISE) | Wording, plus "Line {room} pts away", a fact already shown. The word stays HOLD with the tag noise, so noise stamps are unchanged. "Red" is ambiguous for a writer (S7). |
| 9 (WATCH hint) | **States rule content, and misstates it** (M4). |
| 10 (WATCH with a live fold) | Wording, consistent with §C. |
| 11 ("nothing against you") | Wording, but it hides a blind family (S7). |
| 12 (STOP risk) | **A PLAN rule change: it names the line as her exit** (M3). |
| 13 (HOLD · OI BLIND) | Wording, but its clause is false when flow is blind (S7). |
| 14 (PATA NAHI) | Wording. Its bar-close variant inherits M5. |
| 15 (entry FOLD) | Wording. |
| FOLD reasons, rules 3–6 | Wording. The rule-3 reason adds the bar and the size, which rev 4 §3.1 already requires ("the time it fired and the fact"). |
| the restated M5 example | Wording, and now exact to the code's output. It changes `test_hold.py:81-82`, as listed. |
| §B (display after a FOLD) | Display. It changes what PLAN's STOP shows, so it goes through PLAN's change log (S4). |
| §C (precedence) | **Not wording.** It changes the logged `payers.state` and the count. It is correctly listed under "what changes", but it is labelled a clarification, and the REVIEW called it her call (S1). |

**VALIDATE §2's sentences:** wording, with the gaps listed in S6.

### Q6. Forward-record hygiene: what stays comparable, what resets, and is it stated?

| record | what the drafts say | this review |
|---|---|---|
| rev 4 §7 (B1–B5, W1–W2, clauses 1–6) | Reset at rev 5's first session. Rev 4's rows are kept apart and never pooled. | Right for everything except **B4 and clause 2**, which rule 3 cannot reach; keep those running (S3). Rows are told apart by the new `prereg` key, which rev 4 rows lack. This is stated. |
| rows written between the P0-4 code change and rev 5's code | "`payers.state` differs on overlap minutes from the code fix onward. No clause reads it." | True, no clause reads it. But these are rev 4 rows written under a row precedence she has not signed (S1). |
| §10 side log and §10.6 | Continues. | Right: it reads no line. Its payers fact keeps "for first", unlike the window's row (S1). |
| PLAN P1 / P2 (`rung_touch`, `band_touch`) | Continue. PLAN §4's row is repointed by one change-log line. | Right: a touch reads no verdict. PLAN also takes item 12 and the §B STOP display. Each needs PLAN's change log and a new hash in §1f. |
| VALIDATE rev 1 | "Retired unjudged"; its rows are kept apart. | Right. Rev 1 stays in force, and keeps writing rev 1 press rows, until rev 2 is signed and coded. Rev 2 rows carry `rev: 2`. |
| VALIDATE rev 2 | Its clock starts at its first session after the code. It restarts if rev 5 is signed later. | It also restarts if rev 5's clause 7a replaces rule 3. That is not stated (VALIDATE M2, Q4). |
| research-findings §1e / §1g anchors | **Not mentioned in either draft.** | Each anchor says any later edit gets "a new hash here". Neither draft says two things: whether it is signed as its own file or merged into `PREREG-merged.md` / `VALIDATE-PREREG.md`, and which hash goes into §1e / §1g. Add one line to each change log. |

---

## Second pass — rev 5a and rev 2a (2026-09-25 17:34 IST, read from the clock)

**What was read.**
- **Both revised drafts, in full:**
  - `PREREG-rev5-DRAFT.md`, rev 5a, 17:23;
  - `VALIDATE-rev2-DRAFT.md`, rev 2a, 17:26.
- **The new scratch:**
  - `probeB.py`, with `probeB_table.txt`;
  - `liveB.py`, with `liveB_out.txt`;
  - `fp.py`.
- **The code the new text leans on:**
  - `frame._pick_side` and the call that feeds it (`frame.py:143-160`, `:419-425`);
  - `server._hold_import`;
  - `HOLD_REFETCH_S` (`server.py:1921`);
  - the `test_hold.py` lines that §D.3 cites.
- **Numbers re-checked against the scratch data:**
  - flow at 12:00 was readable ("flat"), so the restated WATCH example is right to offer it;
  - the PE's line was 10.15 pts from price after its 12:25 trail;
  - the 12:01 low was 23,074.3, so the CE's stop was touched at 12:01;
  - the 12:30–12:32 highs stayed under 23,091.6, so the PE's outcome is `neither`.
- **Same restrictions as before.** Nothing was run over any trade by me, nothing was written but this
  section, and no server was touched.

### Part 1b — `PREREG-rev5-DRAFT.md` rev 5a

**The first-pass must-fixes**

| | status | how |
|---|---|---|
| M1 | **resolved** | A and B are two complete, co-equal texts, and B is a frozen level, printed. "Nothing supplies a unit of distance" and "no precedent" are struck. The 5-minute close is named (§A.3). 7-A's "on file" now points at B's full text. Each option has its own disclosure (§E) and kill clause (§F.2, §F.3). |
| M2 | **resolved** | "Caught before the trade" is gone. §A.4 and §E.4 state that VALIDATE gates nothing, that neither live trade was pressed, and that the trailed PE is A's uncovered cost. |
| M3 | **resolved** | Item 12 now reads "≈ ₹{X} [I] of premium between here and the line": no exit and no break rule in PLAN. |
| M4 | **resolved** | §D.1 lists every single condition: rule 4 in all three states plus OI blind, the writer's squeeze and `dpx` blind, and a blind family marked rather than offered. The restated 12:00 example now carries rule 4's joint item. |
| M5 | **resolved** | §A.0.4, written against `_hold_facts` and `_hold_candles` as they stand (both verified): a mid-bar gap reads normally; a due close that has not landed is blind; a late close is read and stamped at `read_at`, never at the bar; `read_at` and B go into day state. One edge remains: S-b below. |
| M6 | **resolved** | §F.1 settles four things: a close exactly on L is a heal; breaks after 15:14 are `short` and excluded; a close that was never read neither heals nor extends the window; imported trades count. |

**The first-pass should-fixes.**
- **Taken:** S1 through S7.
- **§C records her decision:** *"fix every issue there is …"*. That is a blanket instruction, not a
  ruling on the row's precedence. But it answers the REVIEW, and what shipped is the REVIEW's own
  proposed fix word for word. I accept it as her call.

#### New in rev 5a

**M (new, 5-minute variant only) — "A can be signed with '5-minute' in place of '3-minute'. That is a
one-word change." It is not one word.**
- The 3-minute grid is written into several other places:
  - §A.0.1's 125 bars and their two justifications;
  - §F.1's heal window, "the closes at +3, +6, +9, +12 and +15";
  - the late-break cutoff, "after 15:14";
  - the hint's "closes a 3-min bar";
  - §G's §6 row.
- On a 5-minute grid, 15 minutes holds three closes, and the cutoff moves.
- The variant also has no disclosure run, unlike A and B.
- **Fix:** strike the sentence, or write the 5-minute text out in full with its own §E rows. This
  blocks only a 5-minute signature. It does not block A as written (3-minute) or B.

**Should-fix**
- **S-a. Judge 7a and 7b on their own counts.** Clause 7's trigger joins the two counts: "≥ 15
  distinct first line breaks **and** ≥ 15 distinct rule-3 breaks **and** ≥ 15 noise stamps".
  - Under B, rule-3 breaks are rare: 3 in-sample, because B hands most breaks to the quiet clock. So
    7a-B, the heal test, waits on 7b-B's count and may sit inconclusive for 30 sessions.
  - Judge 7a and 7b each at its own ≥ 15, which is the fix this draft's companion applied to
    VALIDATE's P1 and P2.
- **S-b. Tag a close first read from backfill.** A.0.4 says a late close is "never back-dated".
  - A close that was never read live (the server was down, then a restart backfilled it) has no
    `read_at`. By A.0.4's own restart clause, the record then "read[s] the close as if on time", so
    the FOLD is stamped at the past bar.
  - The anytime-start rule allows that only if it is tagged. Mark such reads as backfilled (for
    example `read_at: null, backfill: true`), say that the FOLD is stamped at the bar, and say how
    §7 reads that stamp.
- **S-c. 7a's unit was changed, and the change log does not say so.**
  - Rev 5 counted distinct **rule-3** breaks. Rev 5a counts each trade's **first line break,
    whatever rule folded first**.
  - The reason given is principled ("a property of the tape and the line"), and both units point the
    same way in-sample (§E.3).
  - But the change log's M6 entry lists only heal, late breaks, closeless bars and which trades. Add
    the unit change, and say whether it was fixed before §E.3's counts were taken.
- **S-d. Under B, the fold level can move away from price.**
  - On a trail, B is re-read. If the noise has grown by more than the distance L moved, then L ∓ B
    lands farther from price than the old level.
  - Rev 4's trail is "never away". This does not happen in-sample (both live trails moved the level
    nearer).
  - State it, or clamp it: on a trail, the level is the nearer of the old level and the new one.
- **S-e. The rows do not say which option they were written under.**
  - `prereg: "rev5a"` names neither the option nor the merged revision.
  - If 7-A kills A and B is signed, §F.2 says "§7's record restarts", and the rows must be told
    apart without relying on a date.
  - Use `"rev5-A"` / `"rev5-B"`. Also align §A.2's `b: null` with §G's `B: null`.
- **S-f. The heal sentence no longer checks the other rules.**
  - A.0.6 makes the heal a line-only fact. But "the break has healed … a re-entry is a new trade" can
    now print while rule 4, 5 or 6 reads FOLD on the unlatched state. Rev 4's code required the whole
    unlatched verdict to be HOLD or WATCH.
  - Add "— but {rule} reads FOLD now" when it does, so the sentence does not invite a re-entry into a
    setup the window would refuse.
- **S-g. Two small wording fixes.**
  - §A.4's "covers exactly this case" should read: B covers a trailed line whose break is within one
    candle of the noise read at the trail.
  - Under B, §A.0.3's forming-minute print should add the distance still to go to the break level.

**Verdict, rev 5a:**
- **Option A, as written (3-minute): SIGNABLE.** All six first-pass must-fixes are closed. The
  should-fixes above can go in before the merge or be carried as notes. None changes the rule.
- **Option A on a 5-minute grid: NOT YET.** The "one-word change" sentence must be struck or written
  out.
- **Option B: SIGNABLE.** Its text is complete: a frozen level, the named fallback, the latch, the
  hint, the day state and clause 7-B. S-a (7a-B's trigger), S-d (the level moving away) and S-e (the
  option in the rows) are the three most worth fixing before the merge.

### Part 2b — `VALIDATE-rev2-DRAFT.md` rev 2a

**The first-pass must-fixes**

| | status | how |
|---|---|---|
| M1 | **resolved** | **(a)** The writer is named: `_hold_tick` reads the day's buyer press rows and writes each finished window. The close-time import completes them (`_hold_import` does run `_hold_tick` for every index; verified). The trade is re-created as `_hold_check` does. **(b)** The `hold_log.key` branch is owed, with a test that two directions at one (idx, t) write two rows. **(c)** A `short` unit counts when resolved, and its `neither` is shown apart. **(d)** A blind line, or walls that cannot be read, is `not scored`. |
| M2 | **resolved** | The outcome is first passage at **both** ends, on 1-minute highs and lows, to the static target and static L as they stood at the check. The target is Room's target, with GIVING WAY walls removed, so Room and the outcome treat a leaving wall alike. The outcome reads no break rule, so the restart clause is gone. The 09:43 GO → WAIT that this caused is disclosed. |
| M3 | **resolved in form; see new M1** | Each word is compared with WAIT on four counts ("more often", rev 4 B2), inside a stratum. Each word is judged at its own ≥ 15, P1 no longer waits for NO, and P2 failing withdraws NO only. |

**The first-pass should-fixes.**
- **Taken:** S2 through S7.
- **Partly taken:** S1. It was taken by switching to the machine's own state, which brings in new M2
  below.

#### New in rev 2a

**M1 (new) — The stratum controls the target side of the geometry, but not the line side. The WAIT
control is therefore stacked against itself.**
- **The stratum.** §4 compares GO with WAIT only where "target ≥ line", because "a nearer target is
  reached first more easily, whatever the word". That is the right idea, applied to one end only.
- **Why one end is not enough.**
  - A GO requires Room WITH, so its line is **more than one candle** from price.
  - A WAIT unit in the stratum can be a WAIT *because* its line is inside one candle: Room AGAINST by
    noise.
  - On a first-passage outcome, a line 1.65 pts away with 4.9-pt candles is touched almost surely:
    the 12:00 CE was touched at 12:01.
  - With no drift, the chance of reaching the target first is line ÷ (line + target). Tiny lines give
    WAIT units systematically large target-to-line ratios, and so near-certain stop-first outcomes.
- **The effect on the judgement.**
  - P1 (GO against WAIT) is pushed toward passing by construction.
  - P2 (NO against WAIT) is pushed toward failing.
  - The draft calls this "a known limit … visible". But a known, one-directional bias in the judged
    comparison is what the stratum exists to remove.
- **Fix.** Make the stratum Room's whole geometry: **line > noise and target ≥ line**. GO and the
  control are then compared only where geometry alone would have read WITH, and P1 tests what the
  word adds beyond geometry.
  - The noise half's own claim, that a line inside one candle gets hit, is near-tautological on a
    first-passage outcome. Its real test lives in the window's clause 7, not here.
  - Say both things in §4.

**M2 (new) — Your setup reads "exactly as the MACHINE strip reads it", but the strip's rule is not
fully copied, and "cannot disagree" is false.**
- **The strip reads live values.** Its pocket uses the live future price, `in_sell = u2 ≤ futPx ≤
  u3` (`frame.py:419-420`), and its warm-up is a wall-clock time (`WARM_HHMM` = 09:25).
- **The fact reads "at the last 3-minute bar closed by the check minute".** So inside a bar the two
  can differ. And "the pocket at a closed bar" does not say which price decides it: the bar's close,
  or its high or low. Two honest implementations would diverge. The drafter's own 09:43 cell assumes
  "the 09:41 close".
- **Rules missing from §1.1** (`frame.py:143-160`):
  - an exact tie of reference bars, or a missing `ref_i`, picks **SELL**: "the seller's tool", now
    deciding a buyer's fact;
  - both pockets true picks SELL;
  - a pocket picks its machine **even if that machine is WAITING** while the other is active. §1.1's
    states do not cover a picked machine that is WAITING while the other is active;
  - neither machine active defaults to BUY, which §1.1 already handles as "checked, none".
- **Fix.**
  - Register the pick in full, on recorded values: the future's close of the last closed 3-minute
    bar against that bar's bands, and the tie and both-pocket rules. Choose and state the tie rule for
    a buyer rather than inheriting the seller's default silently.
  - Define the picked-but-WAITING state.
  - Replace "cannot disagree" with "reads the strip's rule on the closed bar; inside a forming bar the
    strip, which reads the live price, can differ".
  - Name the registration, not `frame.py`, as the source, so that a later display edit cannot move
    the fact.

**Should-fix**
- **S-a. "The best day" should match the judged quantity.** P1's best day is "the session with the
  most GO `target` units", and P2's is "the most NO `stop` units". The judged quantity is now a
  comparison against WAIT. Use rev 5a §F.2's definition: the session whose removal moves the
  comparison most toward failing.
- **S-b. The session extreme now caps more often.** With leaving walls removed, the session extreme
  becomes the cap whenever every wall is leaving, and not only when no sized wall exists. That is
  consistent with M2's principle, and 09:43 shows it. Say it in §1.3 in one line, so a reader sees
  that Room's cap widened as well as the target.

**Verdict, rev 2a: NOT YET.**
- The first pass's M1 and M2 are closed.
- M3 is closed in form, but its stratum brings in a one-directional bias (new M1).
- The machine-state setup is not fully defined (new M2).
- Both fixes are wording and definition only. Neither needs a new number or a new run.

### Second-pass summary

| draft | verdict | remaining must-fix |
|---|---|---|
| rev 5a, option A (3-minute, as written) | **SIGNABLE** | none |
| rev 5a, option A on a 5-minute grid | **NOT YET** | strike or write out "a one-word change" |
| rev 5a, option B | **SIGNABLE** | none (should-fix S-a, S-d and S-e before the merge) |
| VALIDATE rev 2a | **NOT YET** | new M1: the stratum must also require line > noise. New M2: register the machine pick in full, on the closed bar. |

---

## Third pass — rev 5b and VALIDATE rev 2b (2026-09-25 17:54 IST, read from the clock)

**What was read.**
- **Both drafts, in full:**
  - `PREREG-rev5-DRAFT.md`, rev 5b, 17:44;
  - `VALIDATE-rev2-DRAFT.md`, rev 2b, 17:48.
- **The strip's code:**
  - `ui-v2/src/machine.ts` (`liveMachine`, `machineWord`);
  - `ui-v2/src/App.tsx` (`MachineStrip`, and the props it is mounted with at `:2197-2204`);
  - `ui-v2/src/data.ts` (`run_state` alignment);
  - `live.py:1070-1097`, where `run_state` / `run_state_sell` / `zone_state` / `zone_state_sell`
    are built;
  - `band_rotation.py` `RUN_BAND`, `SELL_RUN_BAND` and the 09:25 arm gate (`:1102-1108`);
  - `frame._pick_side`.
- **The drafter's scratch:**
  - `data_NIFTY_3m.json` and `signals_NIFTY.json` (the server's zone states and zone rows, by GET);
  - `probeBc.py`.

**What was run, all read-only:**
- the per-bar zone and line machine states, the future close and the bands on the 09:33, 09:36,
  09:39, 14:03, 14:09 and 14:12 bars;
- the zone rows' gates on 09:33, 09:36, 09:39 and 14:03;
- **`probeBc.py` itself.** It writes nothing: `probeB_out.json` kept its 17:14 time.

No repo file other than this one was written, and no server was touched.

### 1. VALIDATE rev 2b: the two second-pass must-fixes

| | status | checked how |
|---|---|---|
| M1, the stratum | **resolved** | §4 judges GO, NO and the WAIT control only inside Room's whole WITH geometry: line > noise **and** target ≥ line. It says plainly that the noise half is near-tautological on a first-passage outcome and is tested by the window's clause 7. On the record, 14:12 leaves the judged set (line 2.65 ≤ noise 14.8) and the 12:00 CE is outside it. That is exactly the row the second pass was worried about. |
| M2, the pick | **resolved** | §1.1 registers the pick in full, on the last closed 3-minute bar, and names this registration, not a display, as the source. The rules: only active machines count; WAITING, including a just-opened lock, is not active; one active machine wins over a pocket whose machine is waiting; with both active, the pocket at b's close decides, else the later event bar; an exact tie reads NEITHER; a bar before 09:25 or crossed bands is "could not check". "Cannot disagree" is withdrawn. |

**Sub-checks on M2:**
- **Both pockets.** "A close inside both pockets needs crossed bands." This is correct: d3 ≤ c ≤ d2
  and u2 ≤ c ≤ u3 together force u2 ≤ d2, and that is only possible at σ = 0. Folding the case into
  step 1 is sound.
- **The 09:25 gate.** It matches the machine's own: it arms only on a bar whose own label is at or
  after `ANCHOR_MINUTE` (`band_rotation.py:1102-1108`). So "b starts before 09:25" is exactly "no
  bar the machine could have armed on".
- **The tie reads NEITHER.** This is a new choice, named in §5 with its principle: a tie says nothing
  about her direction, and neither display's default (BUY in the strip, SELL in the frame) is a
  buyer's rule. It is disclosed as written after §6's values were seen, and no rule is exercised by
  them: each check had exactly one active machine. **Accepted.**

### 2. The drafter's disclosure: is the fact on the zone machine alone, and are the stated differences true?

**The fact is on the zone machine alone: yes.**
- §1.1's inputs are `zone_state` / `zone_state_sell` and the `rule: "zone"` rows, nothing else.
- In `live.py:1093-1097` those are `run_states(…, band="d2")` and its SELL mirror at u2: §1b's
  registered zone rule. No line-machine field is read.
- CLAUDE.md rules 3 and 5 are kept.

**The stated differences, each checked against the code:**

| claim in §1.1 | code | true? |
|---|---|---|
| the strip reads `run_state` / `run_state_sell`, the §5c d3 line machine and its §5d u3 mirror | `MachineStrip` gets `tape.runState` / `tape.runStateSell` (`App.tsx:2197-2204`); `live.py:1070-1087` builds them with the default band, and `RUN_BAND = "d3"`, `SELL_RUN_BAND = "u3"` | **true** |
| the strip shows SELL only when SELL is live and BUY is not | `showSell = sellLive && !buyLive` (`machine.ts`) | **true.** "BUY wins every tie" understates it slightly: BUY wins whenever both are live, not only on an exact tie. |
| "live" includes a lock that has just opened (BAAHAR) | `state !== 'WAITING' \|\| exit_why != null`; `machineWord` gives BAAHAR for `exit_why` | **true** |
| the strip has no pockets | nothing in `liveMachine` reads a band | **true** |
| the strip reads the payload's last bar, which is the forming bar | `runState[runState.length - 1]`. At the 14:13:43 press the last bar was 14:12, and the arithmetic fits: the 14:03 reference gives 7 left on 14:12 and 8 on the closed 14:09 (both in `data_NIFTY_3m.json`) | **true** |
| the frame uses the live future price, the `WARM_HHMM` wall clock, and SELL on ties | `frame.py:419-420`, `WARM_HHMM = "09:25"`, `_pick_side` | **true** |
| on 09-25 the zone SELL machine triggered on 09:33 while the u3 line machine was WAITING | zone SELL TRIGGERED with `entry.t` 09:33; line SELL WAITING | **true** |
| at 14:12 both SELL machines were ARMED on the 14:03 reference | both ARMED, `ref_i` 96, 8 left on 14:09 and 7 on 14:12 | **true** |

**§6's re-read is exact.** Checked against the same data:
- **Bands and closes:** 09:33 close 23,141.0 against d2 23,119.91 and u2 23,158.06; 09:39 close
  23,100.9 inside d3 23,087.84 – d2 23,102.49; 14:09 close 23,188.0 against u2 23,203.04.
- **The 09:43 states:** BUY ARMED on the 09:39 re-arm with 10 left; SELL WAITING, with its lock
  cleared at VWAP on the 09:36 bar.
- **The three gates:** 09:33 SELL trigger legal ("CE 23200 still building"); 09:39 BUY arm illegal
  ("PE 23000 stopped building at 09:36"); 14:03 SELL arm illegal ("CE 23100 gave up its build at
  13:46").

So 14:12's setup is resolved as NEITHER, its count is 0 · 2 · 2, and the words stay WAIT / WAIT / NO.

**One consequence, flagged by the draft and not decided here.** P0-3's complaint was two panels
disagreeing on one screen. The strip showing the **line** machine while "the setup is a ZONE" is now
explained rather than removed. The fact's text names its machine ("the text always gives the
machine …"), so she can tell them apart. Whether the strip should read the zone machine is a UI
question for the operator, and it does not block this registration.

### 3. Rev 5b

- **The 5-minute sentence: struck.** §A.3 now says it "cannot be signed from this draft" and would
  need its own complete text and §E rows. **Closed.**
- **S-a, the separate counts: taken.**
  - 7a triggers at ≥ 15 distinct first line breaks.
  - 7b triggers at ≥ 15 distinct rule-3 breaks and ≥ 15 noise stamps.
  - A short 7b is inconclusive and says so, and rule 3 stands on 7a alone.
  - Every rule-3 break is also a trade's first line break, so 7a's count is never smaller than 7b's.
    7a can never wait on 7b.
- **S-d, the clamp: taken.** The level is "the nearer to price of the old level and the new L ∓ B",
  recorded `clamped: true`, with the latch's `level` the one actually in force.
- **S-e, the option in the rows: taken.** `prereg: "rev5-A" | "rev5-B"`, clause 7 reads "the rows of
  the signed option only", and `B: null` is one name.
- **Also taken:** S-b (`backfill: true`, stamped at the bar, shown apart, every clause must also hold
  without those stamps), S-c, S-f and S-g.
- **S-c's disclosure is honest.** The unit change was made after both units' counts were seen; it
  rests on principle; both units point the same way, so no conclusion moves.

**Does the clamp bind in-sample? The drafter is right, and the second pass was wrong.**
- I ran `probeBc.py`. It binds on **2 trails in 3 trade rows**:
  - NIFTY 09-23 10:25, on her 09:47 call: the level would have moved from 23,349.9 to 23,349.0,
    0.9 pts away;
  - SENSEX 09-23 13:10, shared by the 11:32 74900CE and the EX zone BUY: from 74,887.32 to 74,883.98,
    3.34 pts away.
- It changes **0** first FOLDs.
- The second pass's "This does not happen in-sample (both live trails moved the level nearer)" was
  true only of today's two trades. I had not checked the frozen days, and the sentence should have
  said so. The draft's correction stands.

**Should-fix, new in rev 5b (neither blocks):**
- **S-h. A clamped level misstates the hint.**
  - §A.2 keeps `B` as "the value measured at the trail" when the level is clamped. The WATCH hint
    template then prints "{level} (your line less one candle, {B} pts)".
  - On NIFTY 09-23 after 10:25 that would read "23,349.9 (your line less one candle, 6.6 pts)". But
    23,355.6 − 6.6 is 23,349.0.
  - When `clamped`, print the level as "kept at {level} (the {HH:MM} trail would have moved it N pts
    away)", as §A.2's own print already does, and not as "L less one candle".
- **S-i. "Never away" has one exception, and it should be written down.**
  - The clamp is scoped to trails, and correctly so. But the fallback's first read of B moves the
    level from L (buffer 0) out to L ∓ B, which is away from price.
  - That is the named fallback working as written, but a reader of "the break level never moves away
    from price" will miss it. Add one line: the fallback's first read of B is the one move away, and
    it is why the fallback "folds more than B, never less".
- **S-j (both drafts). Stale revision labels.**
  - Both headers say "wherever the text says rev 5a / rev 2a, read it as this draft".
  - That is fine for a draft, but a *logged value* cannot rely on it: VALIDATE §3's press row still
    writes `rev: "2a"`, and several "rev 5a's first session" clocks remain.
  - Normalise every label to the merged revision numbers ("rev 5", VALIDATE "rev 2") at the merge.

**A and B are both still SIGNABLE.** Nothing in rev 5b moves the rule of either option except B's
clamp. The clamp is rev 4's own principle, binds twice in-sample and changes no FOLD.

### 4. Any new must-fix

**None.** S-h, S-i and S-j are wording, and all three can be done at the merge.

### Third-pass summary

| draft | verdict | remaining must-fix |
|---|---|---|
| VALIDATE rev 2b | **SIGNABLE** | none (S-j: the logged `rev` value at the merge) |
| rev 5b, option A (3-minute) | **SIGNABLE** | none (S-j) |
| rev 5b, option B | **SIGNABLE** | none (S-h the clamped hint, S-i the fallback's one move away, S-j) |
| a 5-minute option | not in this draft | it needs its own complete text and §E rows |
