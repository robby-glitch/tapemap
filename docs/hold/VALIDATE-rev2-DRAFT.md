# PRE-REGISTRATION DRAFT — THE VALIDATE WORD: GO · WAIT · NO (rev 2b; rev 2 written 2026-09-25 16:37 IST, rev 2a 17:20, rev 2b 17:55, by the clock; NOT SIGNED, before any code, UNTESTED)

**Rev 2b** answers the second pass of `REV5-VALIDATE2-REVIEW.md` (17:34, verdict on rev 2a NOT
YET). Its two new must-fixes and two should-fixes are listed in §8. Wherever the text below says
"rev 2a", read it as this draft.

**Base:** `VALIDATE-PREREG.md` rev 1, signed 2026-09-25 13:20 (sha256
`6f1d9047dbdd699e6356e445b9287fc07a7cf719bdea5ea8018d06c849757db5`, re-checked 17:20: unchanged).
Rev 1 stays in force, and keeps writing rev 1 press rows, until rev 2a is signed and coded. Nothing
below is a result.

**Her words:**
- 2026-09-25 ~12:10: *"i want the validate button there when i choose the strike ce or pe and
  weather i long or short it … and than it should tell weather the app the thinks i should take it
  or not or confidence score maybe"*;
- 2026-09-24: *"identifying direction is never my problem but holding a trade is"*.

**What it fixes:**
- `REVIEW-2026-09-25.md`: **P0-2, P0-3, P1-2, P1-3, P1-4, P1-5 and P1-17 [REG]**, and REVIEW §3
  copy items 1–5;
- rev 2a answers `REV5-VALIDATE2-REVIEW.md` Part 2 (verdict NOT YET): M1–M3 and S1–S7, each listed
  in §8.

**What it changes and reads.**
- It changes **no rule** of the window (rev 4, or rev 5a whichever option she signs) or of THE PLAN
  (rev 3).
- It reads their registered objects at the latest finished minute. It also reads:
  - the zone machine's own per-bar state on the last closed 3-minute bar, picked as §1.1 registers
    it (not as any display picks it);
  - the zone machine's logged gate;
  - the index's own 1-minute candles, which the window's line already reads.
- **Its facts and its outcome are the same whichever rev 5a option she signs** (§1.3, §3).
- Until §4 is judged, the word carries DRAFT.
- It is never a size, never an order and never a percentage. **It gates nothing; she decides.** A
  WAIT or a NO does not stop an entry, and the window has to be right for trades she never presses
  VALIDATE for.

**What had been seen when this was written, so nobody has to guess:**
- the REVIEW and the adversarial review;
- rev 1, `validate.py` and `test_validate.py`;
- the two saved replies, and the 14:12 screenshot, with their rev 1 words;
- the live replies of her two 09-25 trades;
- today's NIFTY index candles and OI grid (GETs).

**What was fixed before measuring, and what after.**
- The noise window and statistic were fixed **before** today's candles were fetched.
- Rev 2a's target rule (§3) and setup rule (§1.1) come from the adversarial review's principles
  (its M2 and S1).
- The three checks' rev 2a words and outcomes (§6) were computed **after**. They moved one word,
  disclosed there.
- **Rev 2b's pick (§1.1) and stratum (§4) were written *after* the three checks' zone states,
  gates, lines, noise and targets had been seen.** Their rules are the second pass's own list (M1:
  line > noise; M2: the exact tie, both pockets, and a pocket with a waiting machine). The tie rule
  was chosen on the buyer's principle.
  - None of those rules is exercised by the three checks. Each had exactly one active machine, so
    no pocket or tie decided anything.
  - Their re-read moved no word. The stratum took 14:12 out of the judged set.

---

## 1. The facts — for a BUYER (long CE / long PE)

**Four facts are counted,** each WITH / AGAINST / NEITHER.
- **A NEITHER that is an absence carries its kind** (CLAUDE.md rule 6), and the three kinds are
  never rendered alike: "checked, none — …", "could not check — …", "not shown — …".
- **A NEITHER that is a read** (WATCH, a gate read illegal) **says what was read**, and carries
  `absence: null`.

| # | fact | WITH you | AGAINST | NEITHER |
|---|---|---|---|---|
| 1 | **Your setup**: the zone machine's own state on the last closed 3-min bar, picked by §1.1 | the picked machine is in your direction, gate legal | it is in the other direction, gate legal | gate illegal, or a tie both ways (reads) · no machine active (*checked, none*) · not live yet, gate not read, record unreadable (*could not check*) |
| 2 | **Right now**: the window's entry check, read now | HOLD | FOLD, a broken setup | WATCH (a read) · PATA NAHI (*could not check*) |
| 3 | **Room**: your line, the noise, and the target | the line is farther than one candle's noise, **and** the target is at least as far as the line | the line is **within** one candle's noise, **or** the target is nearer than the line | the line blind, the noise unreadable, or the walls unreadable (*could not check*) |
| 4 | **Paying**: the window's quiet-clock test at the check minute | something paid this minute | — (no against state; §1.4) | nothing paying (*checked, none*) · OI blind (*could not check*) |

### 1.1 Your setup (P0-3; review S1; second-pass M2)

**The source is this registration, and not any display.** A later edit to a screen cannot move this
fact.

**Its inputs, all recorded values on the last 3-minute bar closed by the check minute (bar b, the
bar whose last minute is at or before the check minute):**
- the **zone** machine's per-bar state on each side. This is §1b's registered zone rule, armed at d2
  / u2: `band_rotation.run_states(…, band="d2")` and its SELL mirror at u2, published per bar as
  `zone_state` / `zone_state_sell` on the day's 3-minute future bars;
- **b's close** on the near future, and b's own bands d3, d2, u2 and u3;
- the zone rows `trigger_log` wrote for those machines (`rule: "zone"`), with their §1d `gate`.

**Active** means ARMED, TRIGGERED or IN_TRADE.
- **WAITING is not active**, including WAITING with `exit_why` set (the re-fire lock has just
  cleared at VWAP or at the stop). A lock that has opened is no setup.
- **Nothing here needs a number.** An arm lives the machine's own `RUN_WINDOW` = 10 bars, and a
  trigger lives while its re-fire lock is open (IN_TRADE, until VWAP or the stop). Both are the
  machine's own state.

**The pick, in full, applied in this order:**
1. **Not live yet.** Bar b starts before 09:25 (the machine's own gate, "Gated at 09:25 off the bar's
   own clock label"), or b's bands have not formed (σ = 0, so u2 ≤ d2).
   - Result: **could not check** — "the zone machine is not live yet ({why})".
   - **This is also the both-pockets case.** A close inside both pockets needs crossed bands, so it
     is always read here, never picked.
2. **Neither machine active.** Result: **checked, none** — "the zone machine is waiting on both
   sides; its last event was {…}, {HH:MM} bar".
3. **Exactly one machine active.** That machine is picked, **whatever the pocket**.
   - **A pocket whose own machine is WAITING does not pick it.** A price in the band without an arm
     is no setup: the machine is locked, or has not re-armed.
   - That case is printed as context, not counted: "price closed in the buy pocket, but that machine
     is waiting — {lock open since HH:MM | no arm}".
4. **Both machines active:**
   - **(a)** b's close is inside exactly one pocket (d3 ≤ close ≤ d2, or u2 ≤ close ≤ u3): that
     side's machine. Price is at that band at the close.
   - **(b)** Otherwise, the machine whose **event bar** is later. For ARMED, the event bar is its
     reference bar (`ref_i`). For TRIGGERED or IN_TRADE, it is the bar whose `entry` is set in that
     machine's own per-bar list.
   - **(c) An exact tie** (the same event bar), or an event bar that cannot be read: **NEITHER, a
     read**. "The zone machine points both ways on the {HH:MM} bar", with both printed.
   - **The buyer's tie rule, and its principle.** A tie says nothing about her direction, so it is
     resolved toward **neither** side.
     - The MACHINE strip resolves every tie to BUY ("the scored side").
     - The extension's frame resolves it to SELL ("the seller's tool").
     - Neither is a buyer's principle, and inheriting either would put a vote on a coin the machine
       did not toss.

**The fact's state, from the picked machine:**
- **WITH:** your direction, and the §1d gate on its event's logged zone row is legal. That row is
  the arm row at its reference bar (a re-arm writes a new row), or its trigger row.
- **AGAINST:** the other direction, gate legal.
- **NEITHER, a read:** gate illegal. "BUY d2 armed, 09:39 bar — gate illegal (PE 23000 stopped
  building at 09:36): the other side's fade is refused".
- **NEITHER, could not check:** the zone row is missing, or its gate is not read (`legal: null`),
  or the tape record could not be read.

The text always gives the machine, the state, the band, the event bar, and for an arm the candles
left.

**Where this fact and the MACHINE strip on her screen can differ.** The strip's code was read:
`ui-v2/src/machine.ts` (`liveMachine`, `machineWord`), `ui-v2/src/App.tsx` (`MachineStrip`) and
`ui-v2/src/data.ts`. Rev 2a's claim that they "cannot disagree" was false, and is withdrawn.
1. **They read different machines.**
   - The strip reads `run_state` / `run_state_sell`: the §5c **d3** BUY line machine and its §5d **u3**
     SELL mirror (`band_rotation.RUN_BAND = "d3"`, `SELL_RUN_BAND = "u3"`).
   - This fact reads the **zone** machine (d2 / u2), which is what rev 1's "Your setup" and the
     `rule: "zone"` rows read. CLAUDE.md rule 5 keeps the two apart.
   - **So the two can differ on any bar.** On 09-25 the zone SELL machine triggered on the 09:33 bar
     while the u3 line machine was WAITING. At 14:12, both SELL machines happened to be ARMED on the
     same 14:03 reference.
2. **They pick differently.** The strip shows SELL only when SELL is "live" and BUY is not. "Live"
   includes a lock that has just opened (BAAHAR), BUY wins every tie, and there are no pockets.
3. **They read different bars and prices.**
   - The strip reads the payload's **last bar, which is the forming bar**, on live prices. At 14:12
     its "7 candle baaki" was the forming 14:12 bar's count.
   - This fact reads the **last closed** bar: the 14:09 bar, with 8 left.
   - Inside a forming bar the two can differ even on the same machine.
4. **A third reader, the GoCharting extension's frame** (`frame.py` `_pick_side`), uses the live
   future price, the `WARM_HHMM` wall clock, and SELL on ties.

**What P0-3 actually was.** At 14:12 the strip was showing the u3 **line** machine ARMED SELL, while
rev 1's fact printed a 70-minute-old **zone** trigger (BUY d2, 13:00).
- That was two machines, plus a stale event.
- Rev 2b removes the stale event: it reads the zone machine's *state*, and at 14:12 that was ARMED
  SELL.
- It states the machine difference instead of claiming agreement.
- **Flagged for the UI, not decided here:** the strip reads the line machine, while CLAUDE.md rule 3
  says "the setup is a ZONE".

### 1.2 Right now (P1-4)

The window's entry check at the check minute. HOLD is WITH; FOLD is AGAINST, and makes the word NO;
WATCH or PATA NAHI is NEITHER.
- **Trend is counted here, and only here** (P1-2), as the window's veto.
- **Rule 3 cannot fire at entry** (the window's M5), so this fact is the same under rev 4 and under
  either rev 5a option.

### 1.3 Room: your line, the noise, the target (P0-2, P1-2; review M2, S2, S6)

**Three quantities.** All are measured **unrounded**: to 0.1 against the close, and the noise to
0.05.

- **Line distance [M]:** |close − L| at the check minute.
  - L is the window's line **L itself, under both rev 5a options.** Option B's break level (L ∓ B)
    is printed, not used.
- **Noise [M]:** the median high − low of the index's own 1-minute candles over the 15 finished
  minutes ending at the check minute.
  - All 15 must be present; otherwise "could not check — {n} of 15 candles".
  - The window is inherited: `QUIET` = `fronts.SLOPE_MARKS` = 15. The statistic, the median, is a
    new named choice ("one typical candle"). The scale, 1×, is her words.
  - **This is the measure rev 5a's option B uses for its buffer. It is one measure, read once
    here.**
- **The target [M]:** THE PLAN's rung (§2.2), **re-read with every GIVING WAY wall removed.**
  - That means: the nearest sized payers'-side front strictly beyond the index that is DEFENDED or
    STALLED; else the session extreme in her direction, if it lies beyond the index; else none
    ("no wall in the way — price discovery").
  - **A wall that is leaving caps nothing, so it cannot be the target either.** The same target is
    what the outcome measures (§3).
  - **The session extreme therefore caps more often** than in rev 2 (second-pass S-b). It now caps
    whenever every sized wall beyond the index is leaving, and not only when there is no sized wall
    at all. 09:43 is such a case (§6).

**Order of evaluation:**
1. The line is blind, or the noise is unreadable: could not check.
2. Line distance ≤ noise: **AGAINST**, "your line is inside one candle's range". A tie is AGAINST.
3. The walls are unreadable (PLAN's "the walls could not be read"): could not check.
4. Target distance < line distance: **AGAINST**. A tie is WITH.
5. Otherwise, including no target: **WITH**.

**Why Room reads L, not the fold level (the coupling with rev 5a).** Room is a fact about the
entry's geometry: her structure against price and against the next obstacle. It is not a fact about
the window's exit rule.
- So under option B, "your line is inside one candle's range" still reads AGAINST, and the sentence
  adds "(the window breaks one candle further, at {level})".
- Dropping the noise half under B was considered. It was not chosen, because then VALIDATE's facts
  would change with the window's option, and its record with them.

### 1.4 Paying: the holdability fact (P1-3)

The window's own "paid" at the check minute (rev 4 §3 rule 5), read off `now.clock.paid_last ==
asof`: payers UNWINDING (not both leaving), a live payers' fold, or flow with you by the strict
rule.
- **OI blind** that minute: "could not check — OI {why}". The clock does not count it (M3).
- **Nothing paying:** "checked, none — nothing paying at HH:MM: {the payers row}; flow {state}".
- **No AGAINST state.** Payers adding and flow against are already inside Right now.

**Why this holdability fact, and not the other two the reply could carry (unchanged from rev 2):**
- σ is the window's footer, "never an input": no direction is registered, and it is not fetched on
  a check.
- The expiry line is a sentence with no number and no registered direction, and it read "could not
  check" on both saved replies.

### 1.5 Printed, not counted

- **Market side (§10.4):** the trendbox vote, already inside Right now (rev 4 N4's precedent).
- **The expiry line (§10.3).**
- **σ:** "not shown — σ against VWAP: the window's footer, never an input".
- **The count of direction votes:** direction has one vote of four (Your setup).

### 1.6 A writer (P1-5)

**A writer gets no word, and the screen says so.** The outcome (§3) is target against stop, and a
writer has no target (PLAN §2.6). A GO, WAIT or NO for her could never be judged.

She gets:
- the window's entry verdict as the headline;
- Your setup and Right now;
- the line-against-noise half of Room, printed;
- "not shown — Paying: a writer has no quiet clock; time pays her";
- "not shown — a writer has no next wall; time is her target";
- once: "not shown — a GO / WAIT / NO for a writer: this word is judged on target against stop, and
  a writer has no target; hers needs its own registration."

Her presses are logged with `word: null`. No outcome row is written for her.

---

## 2. The word — for a buyer

- **NO:** Right now is AGAINST, i.e. the window's FOLD at entry.
- **GO:** Right now is **HOLD**, **no** fact is AGAINST, and **at most one** is NEITHER. That is
  rev 1's one allowed not-with, kept as a principle.
- **WAIT:** everything else. It names each AGAINST fact as "what would have to change". When nothing
  is against, it names each NEITHER as "not there yet".

Rev 1's "3 or more AGAINST" is removed. It cannot occur without a FOLD, and two AGAINST is half, not
more than half.

**Shown with it:**
- "{w} with · {a} against · {n} neither — of 4, a count, not odds";
- one sentence;
- the line, the noise and the target.

**The word is strike-free:** every fact reads the index.

**The sentences** (REVIEW §3 items 1–4; review S6):

| word | when | sentence |
|---|---|---|
| NO | rule 4 | "Positioning has flipped against your {opt} (read {t}): {pw} at {k} are adding in your way, and the {hw} {above / below} are covering." |
| NO | rule 6 | "Two families are against your {opt} (read {t}): {a}; {b}." |
| WAIT | Room AGAINST, noise | "Your line is {s} pts away — inside one candle's range (median {m} pts over the last 15 min [M])." Under rev 5a option B it adds: "(the window breaks one candle further, at {level})". |
| WAIT | Room AGAINST, a wall | "Your line is {s} pts away; the next wall ({side} {k}, {WORD}) is only {r} [M]." |
| WAIT | Room AGAINST, the session extreme | "Your line is {s} pts away; the session {low / high} ({level}) is only {r} — no sized wall inside the nine that is holding [M]." |
| WAIT | Your setup AGAINST | "{SIDE band} {armed / triggered / in trade}, {HH:MM} bar, gate legal — the other side's setup is live." |
| WAIT | two AGAINST | **Room's sentence leads.** Holding is the question; direction is hers. |
| WAIT | nothing against | "Nothing is against you, but only {w} of 4 line up. Not there yet: {the NEITHER facts, by name}." |
| GO | — | "Nothing is against you; {w} of 4 line up." |

---

## 3. The log and the outcome — `data/hold/check_<day>.jsonl`, write-once

### The press row

It keeps rev 1's key, (index, read minute, strike, side, role), and rev 1's fields, and adds these
(additive only):
```
rev: "2a", d: +1|-1,
facts: [[name, state, absence (none|blind|hidden|null), text]...],
setup: {machine, state, band, ref_t, candles_left, legal, why},
room: {line: pts, noise: pts, n, target: {src, side, k, pts, word}},
paid: true|false|null, word: GO|WAIT|NO|null (null = a writer)
```

### The outcome row (P1-17; review M1 and M2)

**What it measures (M2).** The outcome is the **geometry the word read, frozen at the check
minute**, and nothing that moves afterwards.
- **The stop** is **L as it stood at the check minute.** It is static: no trail, and no break rule.
- **The target** is **Room's target** (§1.3): PLAN's rung re-read with the leaving walls removed,
  as it stood at the check minute.
- **Both ends are read the same way,** as a first passage on 1-minute index highs and lows over the
  30 finished minutes after the check minute:
  - **target reached:** the 1-minute low (a long PE) or high (a long CE) reaches the target (PLAN
    §2.4's touch);
  - **stop reached:** the 1-minute high (a long PE) or low (a long CE) reaches L.
- **`first`** is whichever came first:
  - `target`;
  - `stop`;
  - `same minute`, when both come in one minute and cannot be ordered;
  - `neither`, when neither comes within the 30 minutes.
- **Consequences:**
  - the outcome reads **no break rule and no trail**, so rev 5a's option (A or B), and any later
    kill of rule 3, never restarts this clock;
  - a GIVING WAY wall is treated the same way in Room and in the outcome: in neither.

**Not scored**, each shown with its reason:
- "checked, none — no target (price discovery)";
- "could not check — the line could not be set at {t}: {why}". This is a blind line at the check
  (M1d);
- "could not check — the walls could not be read at {t}".

**A late check (M1c).** When the check is after 14:59, the window ends at 15:29 and the row is
flagged `short`.
- A short unit that resolves (`target` or `stop`) counts.
- A short `neither` is shown apart, and is excluded like every `neither`.
- A minute inside the window with no candle cannot touch. It is counted in `gaps`.

**Who writes it, and when (M1a): the `stamp_track` discipline.**
- The per-minute tick, `server._hold_tick(poller, idx)` (which today writes the side rows, the
  trade rows and `rung_touch`), also reads that day's buyer press rows for the index.
- For every (idx, read minute t, d) that has a rev 2a buyer press and **no outcome row yet**, whose
  window has finished (`asof` ≥ min(t + 30, 15:29)), it writes **one** outcome row.
- **It re-creates the checked trade from the press row** exactly as `_hold_check` does:
  - idx and d;
  - t0 = t + 1;
  - side CE for d = +1 and PE for d = −1;
  - role long.
- It reads L and the target at minute t from the same day facts, with **the same function the check
  route uses for Room**.
- The close-time import (`_hold_import`, which runs `_hold_tick` for every index) completes any
  window a dead minute missed.
- The facts are exact after a restart, so an outcome row written late is the row that would have
  been written live.

```
{kind: "check_outcome", day, t, idx, d, word, co_timed: [idx...], opposite_same_minute: bool,
 target: {src, side, k, pts}, stop: {L, pts}, noise: pts,
 first: "target"|"stop"|"same minute"|"neither"|"not scored", why: …|null,
 at: HH:MM|null, to: HH:MM, short: bool, gaps: n, tag: "M"}
```

**The key (M1b).** `hold_log.key("check", r)` is `(idx, t, k, side, role)` today. An outcome row
has no k, side or role, so a long-CE and a long-PE outcome at one (idx, t) would collide.
- **The additive change owed after signing:** a branch that returns `(idx, t, d, "outcome")` when
  `r["kind"] == "check_outcome"`.
- Press rows keep their key.

**The unit (P1-17).**
- The **first buyer press per (index, direction) per 30 minutes**, whatever its word. The next unit
  is the first press whose read minute is at least 30 minutes after the previous unit's.
- It is computed at judging time from the rows.
- **Why 30:** it is the outcome's horizon, so no two units' windows overlap.
- The word and the outcome are strike-free, so strike-shopping adds nothing.
- **Stated as a design effect:** a WAIT at 10:00 hides a GO at 10:10. The GO count depends on when
  she first presses. It is deterministic, and it resists word-shopping.
- **Flags:**
  - `co_timed`: another index has a unit in the same direction at the same read minute;
  - `opposite_same_minute`: a unit in the other direction on the same index and minute.

A check marks no trade; "I'm in" is the separate door.

---

## 4. Prediction and falsifier (forward rows only, buyers only; review M3)

**The comparison group is WAIT.** WAIT units are the checks the word did not call either way, and
the most plentiful. **Each word is judged against the WAIT units in the same geometry**, never on
its own majority.

**The control for geometry (first pass M3; second pass M1).**
- **The first bias.** A nearer target is reached first more easily, whatever the word.
- **The second bias.** A line inside one candle of price is touched almost surely on a
  first-passage outcome, whatever the word. The 12:00 CE's 1.65-pt line was touched at 12:01.
- **GO can have neither geometry.** It requires Room WITH: a line farther than one candle's noise,
  **and** a target at least as far as the line.
- **So both comparisons are made only inside Room's whole WITH geometry:**
  - **line pts > noise pts, and**
  - **target pts ≥ line pts**, both at the check, the same two comparisons Room makes.
- **The stratum is identical for GO, WAIT and NO.** GO and the WAIT control are compared only where
  geometry alone would have read WITH, so P1 tests **what the word adds beyond the geometry**. NO is
  compared with WAIT on the same footing.
- **Why the stratum was widened.** Rev 2a's stratum controlled only the target side. It left in
  WAIT units that were WAIT *because* their line sat inside the noise. Those are near-certain `stop`
  units, which tilted P1 toward passing and P2 toward failing by construction.
- **What this leaves untested, stated plainly.** Room's own noise half claims that "a line inside one
  candle gets hit". On a first-passage outcome that claim is **near-tautological**, and it is not
  tested here. Its real test is the window's (rev 5b clause 7: do breaks at the line heal on noise?).
- Units outside the stratum are shown, not judged.
- Every row prints the line, target and noise distances, so any imbalance left inside the stratum
  (the ratio of target to line) stays visible. That is a known limit.

**What is counted, per group in the stratum:**
- `target` units and `stop` units;
- `neither`, `same minute` and `not scored` are shown in full beside them, and excluded (review S5).

**P1 (GO).** Inside the stratum, GO units reach the target first **more often, relative to the
stop, than WAIT units do.**
- This is computed on the four counts as GO(target) × WAIT(stop) > WAIT(target) × GO(stop), which is
  the same statement.
- No share, rate or ratio is ever printed. The four counts are.
- The form is rev 4 B2's "more often … counts per population, described".

**P2 (NO).** Inside the stratum, NO units reach the target first **less often, relative to the
stop, than WAIT units do**, computed the same way.

**Pooling (review S4).**
- The counts are pooled across indices, so each word can reach 15, and are shown per index.
- The verdict must also hold with each co-timed set reduced to one unit (NIFTY, then SENSEX, then
  BANKNIFTY, the `instruments.ENABLED` order).

**The falsifier.** Each word is judged **on its own**:
- **P1** once there are ≥ 15 resolved (`target` + `stop`) GO units **and** ≥ 15 resolved WAIT units
  in the stratum, and ≥ 10 sessions;
- **P2** likewise, with NO in place of GO;
- each in any case at 30 sessions.

**The best day** (second-pass S-a) is the session whose removal moves **that comparison** (P1's or
P2's) most toward failing. This is the same definition as rev 5b §F.2.

**If P1 fails**, or reverses with its best day removed, **the word is deleted.** The four facts stay
as a printed checklist.

**If P2 fails**, or reverses with its best day removed, **NO is withdrawn.** The screen then prints the window's own entry verdict in its place ("the window
reads FOLD at entry"), and the check reads WAIT.

**If 15 NO units never come by 30 sessions**, P2 is **inconclusive**.
- NO stays DRAFT, and keeps its meaning: the window's FOLD at entry, whose frequency rev 4 §7 B4 and
  clause 2 already judge.
- **P1's verdict stands on its own.** P1 never waits for NO.

**If 15 GO units never come**, P1 is inconclusive and the word stays DRAFT.

WAIT is logged and never judged. It is the control.

---

## 5. Parameters — inherited unless named

| item | value | from |
|---|---|---|
| Your setup | the zone machine's state (d2 / u2) on the last closed 3-min bar, picked by §1.1's registered rule: active only; one active wins; if both are active, the pocket at b's close, else the later event bar; a tie reads NEITHER; not live before 09:25 or with crossed bands; gate from its logged zone row | §1b (the zone rule); `band_rotation.run_states` (`RUN_WINDOW` for arms, the re-fire lock for triggers); the machine's own 09:25 gate; §1d. **Named choice:** a tie reads NEITHER, the buyer's rule |
| line distance | \|close − L\| at the check, unrounded | rev 4 §2 (L); review S2 |
| noise: window · statistic · scale | 15 finished 1-min candles, all present · median · one candle | `QUIET` = `SLOPE_MARKS` = 15 · **named choice** · her words |
| target | PLAN's rung with GIVING WAY walls removed; else the session extreme beyond; else none | PLAN §2.2 / §2.4 / §2.7; review M2 |
| paying | rev 4 rule 5's "paid" at the check minute | rev 4 §3, M3 |
| GO · NO | HOLD, none against, ≤ 1 neither · FOLD | rev 1 §2; REVIEW P1-4 |
| unit | first buyer press per (index, direction) per 30 min | rev 4 §7's 30-minute horizon |
| outcome | first passage on 1-min highs / lows to the static target or the static L, 30 finished min, `short` after 14:59 | PLAN §2.4's touch; rev 4 §7's horizon; review M2 |
| comparison | against WAIT, inside Room's WITH geometry (line > noise **and** target ≥ line), on the four counts; ≥ 15 each; ≥ 10 sessions; ≤ 30; the best day = the removal that moves the comparison most toward failing | rev 4 B2's "more often, counts"; rev 4 §7; rev 1 §4; rev 5b §F.2 |

**No number is invented.**
- New uses of inherited numbers: 15 candles for the noise, and 30 minutes for the unit.
- Named choices that are not numbers:
  - the median;
  - the one-candle scale;
  - WAIT as the control;
  - the stratum (Room's whole WITH geometry);
  - a tie in the setup pick reads NEITHER (the buyer's rule, §1.1);
  - the cross-product form of "more often".

Changing any one is a new registration.

---

## 6. Disclosed

**The three saved checks, re-read under rev 2b.** All three are a long PE on NIFTY.

**Where each input came from:**
- **Noise and outcomes:** today's Upstox index candles (`nifty_1m_2026-09-25.json`).
- **The 09:43 target:** the OI grid (`/api/oihist`, GET 17:1x), read at 09:43 with the running peak
  approximated [I]. The top-2 PE fronts came out the same under three rankings: PE 23,000
  UNWINDING and PE 23,100 BUILDING.
- **Your setup is now read, not inferred** (second-pass M2).
  - The zone machine's per-bar states are the server's own `zone_state` / `zone_state_sell` on the
    day's 3-minute future bars (`/api/data?idx=NIFTY&interval=3`, GET 17:4x).
  - The gates are the zone rows (`/api/signals?rule=all&idx=NIFTY`, GET 17:4x; the server reads its
    own log, and nothing in `data/` was opened here).
  - Scratch: `data_NIFTY_3m.json`, `signals_NIFTY.json`.

| check | bar b | zone machines on b [M] | pick (§1.1) and gate [M] |
|---|---|---|---|
| **09:35** | 09:33–09:35 (future close 23,141.0; d2 23,119.9, u2 23,158.1: in no pocket) | SELL **TRIGGERED** (the 09:33 u2 trigger); BUY WAITING | one active, so **SELL**. Its trigger row reads legal, "CE 23200 still building", and it is your direction, so **WITH**. |
| **09:43** | 09:39–09:41 (close 23,100.9; d3 23,087.8, d2 23,102.5: in the **buy pocket**) | BUY **ARMED** (09:39 re-arm, 10 left); SELL WAITING (its lock cleared at VWAP on the 09:36 bar) | one active, so **BUY**. Its 09:39 arm row reads illegal, "PE 23000 stopped building at 09:36", so **NEITHER** (a read). |
| **14:12** | 14:09–14:11 (close 23,188.0; u2 23,203.0: in no pocket) | SELL **ARMED** (the 14:03 re-arm, 8 left); BUY WAITING | one active, so **SELL**. Its 14:03 arm row reads **illegal**, "CE 23100 gave up its build at 13:46". Your direction but illegal, so **NEITHER** (a read). |

**What was resolved.** The 14:12 gate was "could not check from the saved record" in rev 2a. It is
now read: **illegal**.
- The MACHINE strip's "ARMED · SELL · u3 · 7 candle baaki" on that screenshot was the **u3 line
  machine** on the **forming** 14:12 bar.
- The zone machine was also ARMED SELL on the same 14:03 reference, 8 left on the closed 14:09 bar.
- Neither display showed the zone arm's gate.

| check | rev 1 | rev 2 | rev 2a | **rev 2b facts** | **rev 2b** | in the judged stratum? | outcome (after; described) |
|---|---|---|---|---|---|---|---|
| **09:35** | WAIT, 1 · 2 · 2 | WAIT, 1 · 1 · 2 | WAIT, 1 · 1 · 2 | **Setup WITH.** **Right now NEITHER** (WATCH: PE 23,100 adding in your way). **Room AGAINST:** the line is 17.65 pts away, outside one candle (10.25 [M]), but the wall PE 23,100 DEFENDED is 3.95 pts away. **Paying NEITHER:** checked none; the put writers are adding, and flow could not check. | **WAIT**, 1 with · 1 against · 2 neither | **no**: target 3.95 < line 17.65 | **target first**, 09:36 |
| **09:43** | WAIT, 4 · 1 · 0 | **GO**, 3 · 0 · 1 | WAIT, 2 · 1 · 1 | **Setup NEITHER** (the BUY arm is illegal). **Right now WITH** (HOLD). **Room AGAINST:** the line is 72.8 pts away, outside one candle (11.05 [M]). PE 23,000 is GIVING WAY, so it is removed; PE 23,100 is above price; so the target is the session low 23,030.0, 18.8 pts away, nearer than the line. **Paying WITH:** PE 23,000 giving back, a live fold, paid last 09:43. | **WAIT**, 2 with · 1 against · 1 neither | **no**: target 18.8 < line 72.8 | **neither** in 30 minutes |
| **14:12** | NO, 1 · 3 · 1 | NO, 0–1 · 2 · 1–2 | NO, 0–1 · 2 · 1–2 | **Setup NEITHER** (the SELL arm is illegal). **Right now AGAINST** (FOLD, positioning flipped). **Room AGAINST:** the line is **2.65 pts** away, inside one candle (14.8 [M]). **Paying NEITHER.** | **NO**, 0 with · 2 against · 2 neither | **no** (was yes in rev 2a): line 2.65 ≤ noise 14.8 | **stop first**, 14:15 |

**The words:**
- **rev 1:** WAIT / WAIT / NO;
- **rev 2:** WAIT / GO / NO;
- **rev 2a:** WAIT / WAIT / NO;
- **rev 2b:** WAIT / WAIT / NO.

**What rev 2b changed on the record.**
- **The words did not change.** 14:12's count is now exact (0 · 2 · 2), because the gate was read.
- **The stratum did change.** 14:12 left it, because its line was inside the noise. So **none of
  the three saved checks is a judged unit.**
- That is the second-pass M1's point on real rows: a line 2.65 pts from price with 14.8-pt candles
  was a near-certain `stop`, and rev 2a's stratum would have counted it against NO's comparison.

**What moved 09:43 from GO to WAIT (rev 2a, kept).** It is M2's principle: the target and Room treat
a GIVING WAY wall alike.
- The leaving PE 23,000 is removed, so the target is the session low, 18.8 pts away.
- This change was made on the principle, before 09:43 was re-read.

**The setup reading's history.**
- Rev 2's "latest event, either side" was chosen with 09:43 in view.
- Rev 2a replaced it with the machine's own state, and claimed that state was the MACHINE strip's.
  That claim was false: the strip reads the line machine (§1.1).
- Rev 2b registers the full pick on the closed bar. The tie rule (NEITHER) was chosen for a buyer,
  on principle.
- **No tie, no both-pockets case and no picked-but-waiting case occurs in the three checks.** Each
  had exactly one active machine, so the new rules move nothing here.

**Her two live entries, for P0-2 and review S7.** They were **not VALIDATE presses**, and
VALIDATE gates nothing.
- **12:00, NIFTY 23100 CE:**
  - Room reads **AGAINST**: the line is 1.65 pts away, inside one candle (4.9 [M]).
  - Paying reads WITH (a CE 23,150 fold live).
  - Right now was WATCH.
  - Outcome: **stop first**, 12:01.
  - Stratum: **outside** (line 1.65 ≤ noise 4.9). This is the kind of row the rev 2b stratum
    keeps out of the comparison.
- **12:04, NIFTY 23200 PE:**
  - Room reads **WITH**: the line is 24.95 pts away, against a noise of 5.3. PE 23,000 was leaving
    and was removed; PE 23,100 is above price; so the target is the session low 23,030.0, at 36.65.
  - Outcome: **neither** in 30 minutes. The static L 23,091.6 was not reached; the 12:30 high was
    23,088.45.
  - Stratum: **inside** (line 24.95 > noise 5.3; target 36.65 ≥ line). This is the geometry P1
    judges.
  - **What this shows (S7):** Room is a fact about the check minute only. The window's line
    **trailed** to 23,084.8 at 12:25 and then folded the trade: at 12:30 under rev 4, at 12:32 under
    rev 5a's A, and at 13:59 under B.
  - Nothing in VALIDATE sees a trailed line. That is the window's to cover (rev 5a §A.4).

**Scratch** (session scratchpad `rev5/`; nothing written to the repo):
- `noise.py`;
- `outcome.py`;
- `oihist_NIFTY_1625.json`;
- `fp.py`, the first-passage run;
- `data_NIFTY_3m.json` (the zone states) and `signals_NIFTY.json` (the zone rows and their gates),
  both GETs from the running server.

---

## 7. The forward clock, and the tests that change

**Rev 1's record** (the 09-25 press rows, and those it keeps writing until rev 2a is coded) is rev
1's own.
- It is never pooled, and never judged by rev 2a's measure.
- Rev 1 is **retired unjudged**.
- **Rev 2a's clock starts** at its first session after the code lands.
- **It does not restart** when a rev 5a option is signed, or when clause 7 later re-registers rule
  3, because the outcome reads no break rule (§3).

**The anchor (review Q6).** On signing, rev 2a is **merged into `VALIDATE-PREREG.md` as rev 2**,
the way PLAN rev 3 was merged, and its sha256 goes into research-findings **§1g** beside rev 1's.

**`test_validate.py` as it stood at 16:45** has seven tests, and every one pins rev 1:
- the 0936 moment: the facts become four; 09:35 reads `[for, neither, against, neither]`, WAIT;
- GO: HOLD, none against, ≤ 1 neither;
- NO: only on FOLD;
- plain words and no %: the names become `["Your setup", "Right now", "Room", "Paying"]`, and "no %"
  applies to the word's own sentence and count;
- the absence kinds: they carry over, over four facts;
- the writer: her word is `None`, and `writer_note` is §1.6's line;
- fact one: it reads the zone machine's state on the closed bar by §1.1's pick, not the latest trigger
  or arm. The fixture's 72-minute-old BUY trigger plays no part.

**New tests owed:**
- the two saved replies. 14:12 needs its reply saved; only the screenshot exists;
- a line inside the noise reads AGAINST whatever the target;
- a leaving wall is removed from the target;
- the target-first and stop-first passages, including `same minute` and `short`;
- the unit rule on a strike-shopping minute;
- **the outcome key: a long CE and a long PE at one (idx, t) write two rows.**
- **the pick (§1.1), one test per rule:**
  - one machine active wins over a pocket whose machine is waiting;
  - with both active, the pocket at b's close wins;
  - with both active and no pocket, the later event bar wins;
  - an exact tie reads NEITHER;
  - crossed bands, or a bar before 09:25, is could not check;
  - a lock that has just opened (`exit_why`) is not active;
- **the stratum:** a WAIT unit with its line inside the noise is shown and not judged; one with
  line > noise and target ≥ line is judged.

---

## 8. Change log

**rev 2 DRAFT, 2026-09-25 16:37 IST.** Not signed.
- The facts: Your setup (latest event, 10 bars), Right now, Room (with noise), and Paying.
- Market side printed.
- The writer: no word.
- GO needs HOLD.
- The unit: first press per 30 minutes.
- The outcome: rung before stop.
- P1 and P2 as majorities.

**rev 2a DRAFT, 2026-09-25 17:20 IST (read from the clock).** Not signed. From
`REV5-VALIDATE2-REVIEW.md` Part 2. **Must-fixes:**
- **M1:**
  - **(a)** the outcome's writer: `_hold_tick` per minute, then the close-time import; the trade is
    re-created from the press row as `_hold_check` does.
  - **(b)** the key: an additive `hold_log.key` branch, `(idx, t, d, "outcome")`, owed after
    signing.
  - **(c)** `short`: counted when resolved; its `neither` is shown apart.
  - **(d)** a blind line or unreadable walls at the check: not scored, could not check, shown.
- **M2:**
  - the outcome is a first passage at **both** ends, on 1-minute highs and lows, to **static**
    levels as at the check;
  - the target is Room's target, PLAN's rung re-read with the GIVING WAY walls removed;
  - so the outcome reads no break rule and no trail, and no rev 5a choice restarts it;
  - Room and the outcome now treat a leaving wall alike. Rev 2's restart clause is deleted.
- **M3:**
  - each word is compared with the **WAIT** units inside the stratum "target at least as far as the
    line", on the four counts (rev 4 B2's "more often");
  - each word is judged on its own 15;
  - if 15 NO units never come, P2 is inconclusive and P1 stands alone;
  - if P2 fails, NO is withdrawn.

**Should-fixes, all taken:**
- **S1:** Your setup is the machine's own state, as the MACHINE strip reads it (arms by
  `RUN_WINDOW`, triggers while their lock is open). There is no borrowed window, and the fact cannot
  disagree with the strip.
- **S2:** unrounded distances; stated ties.
- **S3:** a NEITHER that is a read says what was read; a NEITHER that is an absence carries its kind.
- **S4:** co-timed and opposite-direction units are flagged; the counts are pooled and shown per
  index; the verdict must also hold with co-timed sets reduced.
- **S5:** not-scored, neither and same-minute counts are shown beside P1 and P2.
- **S6:**
  - the session-extreme sentence;
  - Room leads when two are AGAINST;
  - **stated divergence:** session-extreme touches are scored here and excluded from PLAN §6. These
    are separate registrations, and neither should be "fixed" to match the other.
- **S7:** the 12:04 PE disclosed. Room is a fact about the check minute only.

**Coupling with rev 5a, stated in both files:**
- one noise measure;
- Room reads L under both options, with option B's level printed;
- the outcome reads no break rule;
- VALIDATE gates nothing.

**Disclosed:** the words go WAIT / WAIT / NO under rev 2a. 09:43 moved GO → WAIT under M2's
principle, and this is disclosed.

**No number invented.**

**rev 2b DRAFT, 2026-09-25 17:55 IST (read from the clock).** Not signed. From the second pass of
`REV5-VALIDATE2-REVIEW.md` (17:34).
- **Second-pass M1, the stratum (§4):** the comparison is made only inside Room's whole WITH
  geometry, line > noise **and** target ≥ line, for GO, NO and the WAIT control alike.
  - P1 and P2 are restated inside it.
  - §4 says plainly that Room's noise half ("a line inside one candle gets hit") is near-tautological
    on a first-passage outcome, and is tested by the window's clause 7, not here.
  - On the record, 14:12 leaves the judged set, and none of the three saved checks is a judged unit.
- **Second-pass M2, the pick (§1.1):** "Your setup" is registered in full, on recorded values of the
  last closed 3-minute bar:
  - only active machines count;
  - one active machine wins, even over a pocket whose machine is waiting;
  - with both active, the pocket at the bar's close wins, else the later event bar;
  - an **exact tie reads NEITHER**, the buyer's rule: a tie says nothing about her direction, and
    neither display's default (BUY in the strip, SELL in the frame) is a buyer's principle;
  - crossed bands, which cover the both-pockets case, and bars before the machine's 09:25 gate are
    "could not check".
- **"Cannot disagree" is withdrawn.** The strip's code was read (`machine.ts` `liveMachine` /
  `machineWord`, `App.tsx` `MachineStrip`, `data.ts`). The strip reads the §5c/§5d **line** machine
  (d3 / u3) on the **forming** bar with its own pick. The fact reads the **zone** machine (d2 / u2)
  on the **closed** bar. §1.1 lists exactly where they can differ, and names this registration, not
  a display, as the source.
  - **Flagged, not decided:** the strip showing the line machine while "the setup is a ZONE"
    (CLAUDE.md rule 3).
  - Rev 2a's S1 line above ("as the MACHINE strip reads it") is superseded by this entry.
- **S-a:** the best day is the removal that moves the judged comparison most toward failing, as in
  rev 5b §F.2.
- **S-b:** §1.3 states that the session extreme now caps whenever every sized wall is leaving.
- **§6 re-read on the server's zone states and zone rows** (GET, `data_NIFTY_3m.json`,
  `signals_NIFTY.json`):
  - the setups are read, not inferred;
  - **14:12's gate is resolved: illegal** ("CE 23100 gave up its build at 13:46"), so Setup is
    NEITHER and the count is 0 · 2 · 2;
  - the words are unchanged: WAIT / WAIT / NO;
  - it is disclosed that the rev 2b rules were written after these values were seen, and that no
    rule is exercised by them.
- **No number invented.** One new named choice: the tie reads NEITHER.
