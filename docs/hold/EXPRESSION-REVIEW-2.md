# Second review: `EXPRESSION-PREREG-DRAFT.md` rev c (the expression, the writer in VALIDATE, the writer in the window)

Independent adversarial second pass, in the form of `REV5-VALIDATE2-REVIEW.md` and `EXPRESSION-REVIEW.md`.
Written 2026-09-26 19:05 IST (read from the clock). This is the only repo file written. No server was
touched, nothing was POSTed, `data/` was not opened, and nothing was committed.

**The draft as read:** sha256 `4f29d91fe1eaea9278ce211eace8f8f9916bf011646743a8ddd5ea2e8777ffe1` [M], mtime
2026-09-26 18:45:16 IST [M]. It matches the hash I was given, and it is the copy committed in `e1f17d6`.

**What I read:**
- the draft, in full; the first review (`EXPRESSION-REVIEW.md`); the copy it read
  (`draft_as_reviewed_d7c4a4de.md`, hash verified) and rev b's final text (`draft_revb_final_4607a153.md`, hash verified);
- the six fingerprint copies (`rules_*.md`), each hashed;
- the signed rules the draft cites: rev 4 (`PREREG-merged.md` "Why this exists", §1–§4, §7), rev 5 (`PREREG-rev5.md`
  §A.0–§A.2, §F, §G), VALIDATE rev 2 (§1.2–§1.6, §2–§4), PLAN §2.1;
- `HANDOFF-2026-09-26.md`, and her standing decisions in memory (`both-ways-expression`, `no-trades-after-3pm`,
  `trader-decides-ui-questions`, `seller-desk-doctrine`);
- the drafter's scripts (`expr.py`, `expr_a.py`, `expr_b.py`, `expr_c.py`, `run_c.py`, `gen_D_c.py`) and every rev c output.

**What I ran, all read-only, in my own scratch folder (`scratchpad/review2/`), Python with `-B`:**
- `sha256sum` of the draft and every fingerprint; `diff` of rev c's fingerprint against the draft, and of rev b's final
  text against rev c's fingerprint.
- **Reproduction** of §D.1 (all 18 rows and the totals), §D.2, §D.3, §D.4 (all 29 rows and the word counts), §D.6 (both
  tables) and §D.7 from `revc/*.json` and `reva/facts_3m.json`.
- **One construction probe** (`probe.py`), importing the drafter's rev c code unchanged, over the same nine frozen
  index-days at the 3-minute closes. It reads only construction properties:
  - which refusal codes stand behind each word named by refusal;
  - which grid writer units fall in §B.3's stratum, under each of its two readings (below);
  - how often a sale at the **rounded** ATM strike sits more than one median candle in the money.
- `git status` before and after: nothing landed in the repo.

**What I did not run:** no word was scored against an outcome, and no candidate rule was run. **Not showing you:** I did not
join §D.4's words to its R-multiple rows, and I report no outcome split by word.

---

## 1. Are M1–M9 closed?

All nine are closed in the text. §G's rev a entry describes what the text now does. Two of the fixes left
leftovers behind, and they are new defects (§3 below, B-M1 and C-M4).

| item | status | where, and what the text does |
|---|---|---|
| **M1** the outcome unit | **CLOSED** | §E.2 (lines 1084–1105): R-multiples on the shared line, PLAN §2.1's two formulas, G = long R − short R, the sizing named, split with / against / flat, judged pooled and in *with*; % rows shown. |
| **M2** refusal words pooled | **CLOSED** | §A.4 (290–294) `named_by`; §E.2 (1112–1121) count and refusal populations never pooled, the sell-refusal claim (1138–1141); §E.3 logs; §F.1 caution ink. |
| **M3** stability | **CLOSED** | §A.2 (122–136) the 3-minute close and the since-clock; §D.2 both cadences; §E.2 the 1-minute read kept visible (1151). The cadence was decided on her delegation, not put to her; disclosed (line 26). |
| **M4** R4 fails open | **CLOSED** | §A.4 R4 (247–250): could not check refuses SELL; S unreadable too. §D.5 restates 09-25 09:36 as STAND ASIDE · led. |
| **M5** disclosure, attribution | **CLOSED** | §G (1341–1371): the three edits, the header, `silence_detail.json`, the direction of the moved words, the alternative not taken. Attributions (67–75, 219–225, 447–448, 507–510). I checked the quotes: "which side stops first increasing their positions…" is in research-findings §1d; "almost forms mirror charts", "otherwise atm straddle is ideal" and "1:1 atleast" are in the band-rotation spec [M]. |
| **M6** writer word unreachable | **CLOSED**, with a leftover | §B.3 (458–473): population (ii) and the horizon fixed. But the stratum text now contradicts itself (**B-M1**). |
| **M7** unsigned R | **CLOSED** | §C.2 (524–525, 539–543): R is signed; rule 3s; the held loss (562–564). Rev b added the buffer. See **B/C-M3** for what 3s now does at entry. |
| **M8** wrong expiry | **CLOSED** | §C.2 (534–536): S of her option's own expiry, else FOLD; §A.5 names each leg's expiry. |
| **M9** W-R blind to the tail | **CLOSED** | §C.4 (596–625): majority, the total in points per index, the total in S pooled, best day removed, P_max logged, the worst break printed. |

**S1–S17, briefly:** S1 CLOSED (§A.3 168–182). S2 CLOSED (§A.4 269; §E.2 1130). S3 CLOSED. S4 CLOSED (1108–1111). S5
CLOSED (§D.3). S6 CLOSED (§A.1 103–106; fact 5's sentence names the move's sign). S7 CLOSED (1148–1151). S8 CLOSED (§A.5,
§A.7). S9 CLOSED (header 41–48). **S10 CLOSED, with a leftover:** §B.1 moved to "state it" at 01:31, but §B.3's stratum and
§E.1's writer row still carry the old "could not check" reading (B-M1). S11 CLOSED (464–466). **S12 CLOSED for the reach;**
the same rule is not yet applied to the wall's copy (A-T9). S13 CLOSED. **S14 answered, but the answer pools 3s into rule 3's
falsifier** (C-M4). S15 CLOSED by 3s. S16 CLOSED (the principle sits in rev 4's opening "Why this exists", line 33, not in
§1: A-T11). S17 CLOSED.

---

## 2. Does the disclosure hold?

**The fingerprint holds.**
- `rules_revc_before_run.md` hashes to `64ad9d7f868cfbc7ec7754785966c0a19c46899b4b6219a89fc1dfae90332010` [M], as §D.0 says.
- Its diff against the current draft touches only:
  - lines 10–11 (a header sentence about which revs were fingerprinted);
  - §D (674 onward, to the start of §E);
  - §G's post-run lines and §H [M].
- **§A–§C and §E–§F are byte-identical to the fingerprint** [M]. The rules did not move after rev c's run.
- Rev b → rev c's rule changes (the refused tie, the expiry-day NO, `after_1500`, the refusal populations judged on their
  own) are each logged in §G's rev c entry [M: I diffed rev b's final text against the fingerprint].

**The tables reproduce** from `revc/*.json`, and D.3 from `reva/facts_3m.json`:

| table | reproduced? |
|---|---|
| **D.1** | Yes: all 18 index-day rows and the totals: BUY 293 (209 · 84), LEANS BUY 516 (246 · 270; 169 ties), EITHER 275, LEANS SELL 325, SELL 255, STAND ASIDE 586 (360 · 226) [M]. The every-minute line reproduces too. |
| **D.2** | Yes: 1,010 of 2,232 changes, 562 of 1,028 single-read runs, 11 strong flips, 185 side flips, 841 of 1,389 LEANS; per minute 1,957 / 869 / 8 / 369 / 2,556 of 4,189 [M]. |
| **D.3** | Yes, as rev a's: the facts, refusals, co-occurrence and placement (478 / 83 / 19; quartiles 0.09 / 0.19 / 0.34) [M]. |
| **D.4** | Yes, all 29 rows (word, lead, b–s, refusals, since, was, the three fold columns, B_k). **BUY 7, LEANS BUY 9, SELL 3, LEANS SELL 4, EITHER 2, STAND ASIDE 3, could not check 1** [M]. No entry word moved from rev b; only #8's "was" changed [M]. The 4.4-pt difference on #19–#25 holds [M]. |
| **D.5** | **Could not check its facts.** The three rows are written by hand in `gen_D_c.py` (lines 204–206), from rev b's rows with rev c's tie rule applied. The rule is applied correctly (12:01's 1–1 tie with R4 becomes LEANS BUY CE · selling refused). The 09-25 facts at the close were never frozen, so nothing re-reads them. |
| **D.6** | Yes: the 13 sold calls (rev 5 B, NO, YES, the 14:59 and 15:29 premiums, B_k) and the grid table: 64 / 48 / 27 / 13 / 13 → 71 / 48 / 22 / 13 / 11, held breaks 7 legs → none, 4 early 3s folds (3 lower, 1 higher), 9 at the same close, 154 → 161 [M]. The seven legs the answer moved are as listed [M]. |
| **D.7** | Yes: 216 units, 26 / 51 / 35 / 41 / 14 / 49 [M]. |
| **D.8** | Yes: 14.0, 17.55, 19.8, 21.9; 141.45; 116.05; 25 of 165; 22 of 165; 36 of 216 [M]. |

**Her 15:00 practice does not act as a gate anywhere.** I read every mention of 15:00, 14:59, `after_1500`, cutoff and CAS
in §A–§C and §E–§F. `after_1500` is written and read by nothing; it changes no word, fold or falsifier. The one 14:59
clause (§E.2's `short` units) was in the draft before her words: it is in the copy the first review read [M].

**Disclosure gaps, all text** (A-T5, A-T6, A-T8 below):
- 121 of rev c's 169 refused ties carry R6 [M], and R6 over-fires on 09-22 and 09-23, the nearer-only days (§D.3's own note).
  So most of rev c's in-sample effect sits on a fixture gap. §D does not say so.
- Some refusal populations will almost never reach their count, and some refusal units can never be scored (§3, A).
- §D.4's "sold leg" and §D.6's "sold call" are different legs at different strikes, and the text does not say so.

---

## 3. What came in with revs a, b and c

### The trader decisions made on her delegation, judged

| decision | principled or tuning? | disclosed honestly, with what had been seen? |
|---|---|---|
| **The 3-minute cadence** (rev a) | **Principled.** It is the house's canonical bar, her chart's candle and rev 5's grid. It changes *when* the word is read, not which leg is named. | **Yes.** Decided after rev 0a's per-minute counts (the review's). §D.2 shows both cadences. |
| **LEANS for a one-fact margin** (rev b) | **Principled.** There is no threshold number; it changes labels and populations, not which leg is named. | **Yes.** Decided after rev a's §D.2 showed half the words standing on one fact (§G, 1474–1477). |
| **The refused tie reads LEANS "· other refused"** (rev c) | **Principled.** Direction is hers, and one expression is open. It is its own population. | **Mostly.** §G lists what had been seen. **Missing:** 121 of the 169 ties carry R6 [M] (A-T5). **Also:** §A.4's own sentence "LEANS means a single fact decides" is no longer true for LEANS by refusal (A-T4). |
| **3s inherits rev 5 B's buffer** (rev b) | **Principled.** Her line rule, signed as B, says a close inside one candle is noise, and the strike is a line. It was not tuned further: the 74,000 sales still fold at 13:05. | **Yes** (§C.6, §G). The buffer does not reach the born-in-the-money case (B/C-M3). |
| **STAND ASIDE · led stays silent** (rev 0's choice, kept in rev c) | **Principled, and I confirm it as the trader's reading.** When the facts favour the closed leg, the open leg is the worse expression by the count. Naming it would push her into the leg the facts argue against. | It is registered in §A.4 (287–288). **§H.2 still calls it "open"** (A-T1). |

### Stale text left by a later revision

- **§H.2**: it calls STAND ASIDE · led "still open, for the trader", although §A.4 registers it. Confirmed (A-T1).
- **§H.1**: its headline is current. Its "still hers" (should fact 5 and the placement also set the ATM straddle aside on
  expiry day?) is a genuinely open question, not a stale one. But a signed text cannot carry "hers to say" (A-T2).
- **The header, line 38**: it says "her one decision". §H.1, §H.5 and §E.1 (her "90-minute write guard") each name
  something else as hers (A-T3).
- **§B.3's stratum (line 476) and §E.1's writer row (line 1062)**: both are left over from rev a's pre-01:31 text (B-M1).
- **"Can be signed"**, at lines 38–39, 573, 669–670 and 1537: the draft passes a verdict on itself (A-T3).

### Rules that contradict each other, or fail open

**B-M1: §B.3's stratum contradicts its own definition, and the disclosure code used the other reading.**
- **The text** (line 476): *"the writer's Cushion WITH geometry (line > noise, the line inside the strike, P ≥ X)"*.
- **Where it came from.** "The line inside the strike" dates from rev a's first fingerprint (01:28), when §B.1 read "could
  not check" for a line beyond the strike. At 01:31 §B.1 changed to "state it": X is computed and flagged. The Cushion's WITH
  no longer requires the line inside the strike, but the stratum's parenthetical was not updated. Neither was §E.1's row,
  "Cushion (noise, the strike range, X vs P)" [M: `rules_reva_before_run.md` lines 425 and 612].
- **What the disclosure used.** `expr_a.writer_word_a` (line 220) computes the stratum as line > noise and P ≥ X, without
  "the line inside the strike".
- **What each reading keeps** [M, the probe, over the 165 grid writer legs]:

  | stratum | GO | WAIT | NO | total |
  |---|---|---|---|---|
  | as the code computes it (line > noise, P ≥ X) | 60 | 58 | 15 | 133 |
  | as the text reads (adding "the line inside the strike") | 36 | 42 | 13 | 91 |

  49 of the 165 legs have the line at or beyond the strike [M].
- **So P1-W and P2-W judge different populations,** depending on which sentence the builder follows. §B.1's own reason for
  "state it" ("reading it blind would blind the writer's word exactly where rev a places sales") argues for the code's
  reading.
- **Fix, with no number:**
  - the stratum is Cushion's WITH as §B.1 defines it, line > noise and P ≥ X;
  - units with the line beyond the strike are shown split, and not excluded;
  - §E.1's row reads "Cushion (noise, X vs P; flagged when the line lies beyond the strike)".
  - Either reading can reach its counts (the resolved units in the stratum were 57 of 133 and 50 of 91 [M]). This is
    a definition to settle, not a reachability problem. It is a method detail, not Mary's.

**B-M2: a writer's GO can stand on an unread safety input, on a sale that §A refuses.**
- **VALIDATE's GO allows one NEITHER** (§B.2 inherits rev 2 §2). For a writer, three of the NEITHERs are absences of her risk
  facts:
  - **Your wall, "OI blind (could not check)":** with OI blind, the entry check reads "HOLD · structure only". That is a HOLD,
    which `validate._right_now` maps to WITH [I, from rev 4 §3 rule 2 and the code]. So Right now WITH, Your wall NEITHER,
    Cushion WITH and Time is paying WITH read **GO**. At the same minute §A refuses that sale by **R3**, "a writer does not
    sell a wall she cannot see".
  - **Time is paying, "unreadable (could not check)":** GO is possible, while §A refuses by **R4 — could not check**.
  - **Cushion, "no greeks (could not check)":** GO is possible without knowing the line's cost against the premium. This is
    the writer's core risk fact.
- **§F.1 shows both on one screen.** The dimmed SELL card carries "selling refused (R3)", and a GO beside it.
- **The draft's own principle** (§A.4 R4, §C.2: "an unread safety input fails closed", adopted as review M4) says this is
  fail-open.
- **Fix, with no number:** for a writer, could not check on Your wall, Cushion or Time is paying reads **WAIT, never GO**
  ("not there yet: could not check {fact}"). A read NEITHER keeps its one allowed place. Not Mary's.

**B/C-M3: a sale made more than one candle in the money: VALIDATE can say GO, and the window folds it at its first close
with no move. The promised warning is not registered.**
- **§C.2** (line 543): *"A sale made more than one candle in the money folds at its first close, and the entry check says so
  at entry."*
- **§B.1** (lines 394–395): *"Rule 3 cannot fire at entry (M5), so §C does not touch it."* Rev 4's entry check reads only
  rules 4 and 6 at entry. **No registered sentence or rule makes the entry check "say so".**
- **So B can read GO** (Right now HOLD, Cushion WITH on a premium that includes intrinsic, time paying) on a press that C is
  registered to fold at the next 3-minute close, unless the index moves her way by more than the excess.
- **It is not rare, and not only "a deliberate in-the-money sale"** (§H.5's framing). §A.5 never places a sale in the money,
  but her own press can:
  - a sale at the **rounded** ATM strike sits more than one median candle in the money on **734 of 2,250** side-closes over
    the nine index-days [M], about one close in three;
  - by index: NIFTY 281, SENSEX 223, BANKNIFTY 230, each of 750 [M];
  - her words: *"i often trade itm or atm"*.
- **Why it matters.** This is the window's purpose (a) turned around. A sale folded on its first bar with nothing moved is
  "closing too early on my trade".
- **Fix, with no number** (B_k is rev 5 B's one measure, and VALIDATE already reads it as the noise). At the press and at
  entry, when her strike is already beyond k ± B_k:
  - the entry check prints "your strike is already {x} pts through, more than one candle ({B_k} pts [M]); rule 3s folds
    this sale at the first 3-min close unless the index is back inside {level}";
  - the writer's Right now reads it as AGAINST, so the word is NO.
- **Whether a born-in-the-money sale should be folded at all is Mary's** (§H.5). The fix only makes B and C agree.

**C-M4: rule 3s is pooled into rule 3's falsifier, and has no kill clause of its own.**
- **§C.5** (lines 629–632): *"7b-B counts them as rule-3 stamps (`fold_rule` ∈ {3, 3r, 3s}, shown split by sub-rule)"*.
- **Rev 5 §F.3:** if 7b-B fails, "rule 3 is re-registered, with no candidate on file". So the strike rule's stamps can kill
  the writers' **line** rule. A 3s fold is not a line break.
  - 3r belongs there: it is a line break's fold, delayed by the reach.
  - 3s does not. Pooling it breaks house rule 5.
- **And 3s itself can never be killed.** §C.4: *"If it dies … rule 3s stays."* 7a-B never sees a 3s fold, because its unit
  is the line break.
- **3s is not rare.** It is the first fold on 13 of 165 grid legs, and on #27–#29 of her entries [M]. Its noise cost is on
  the record: 74,000 folded at 191.65 at 13:05, and the call stood at 67.75 at 14:38 and 50.2 at 14:59 [M].
- **Fix, with no number:**
  - 7b-B reads `fold_rule` ∈ {3, 3r}; 3s is shown beside it and judged apart.
  - 3s gets a stated fate. Either:
    - **(a)** 7a-B's own heal test read at the strike. The unit is distinct strike breaks keyed (index, bar, k, side). A
      heal is a close back on her side of k within 15 clock minutes. More than half healing re-registers 3s's buffer, at
      ≥ 15 and ≥ 10 sessions, by 30. Or:
    - **(b)** the plain sentence "3s has no kill clause: it is a hard stop on an open-ended short; its cost is shown, never
      judged".
  - The choice is a method detail on her delegation.

### Other new items (should-fix, text only unless marked)

- **C-S1: a held writer with OI blind.** Rules 4 and 6 need OI, and on SENSEX FLOW is mostly blind. So while held, only 3r
  and 3s can fold her. §F.2's WATCH hint "lists every condition that alone folds her". It must mark 4 and 6 "could not
  check" then.
- **C-S2: say the reach's real domain.** S is read from the chain record, which carries one resolved (nearest) expiry per
  index [I, the first review's reading of `upstox_instruments.resolve`]. So the reach can hold only a sale of the nearest
  expiry, on a day that is not its expiry day. Every other sale's S is unreadable, and it folds at the line.
- **C-S3: say what DRAFT means for the reach.** Held breaks come off expiry only, and none occurred on the four days [M].
  W-R will very likely stay short of 15, so the reach stays DRAFT **and in force**: a stop-loosening rule on an open-ended
  short that may never be judged [I]. Put this to her plainly (Mary's list).
- **C-S4: where 3s and 3r sit in rev 4 §3's first-match order.**
  - Rev 4 lists rule 3 before 4 and 6. The scratch (`expr_b.reach_b`) tests 4 and 6 before 3s and 3 at the same close.
  - The fold minute is the same either way, but the stamp label is not, and 7b and clause 5 read the label.
  - One sentence settles it. Choose the scratch's order, so that the builder reproduces §D.
- **C-S5: §C.7's "S was 250–600 pts on her days"** (line 663) should read "on the two off-expiry index-days the first
  review checked (NIFTY 09-24, SENSEX 09-22)".
- **B-S1: §E.1 line 1062, "the strike range",** is fixed with B-M1.

---

## 4. The trader lens

**Part A, at the moment a setup pops.**
- **It is usable.** She gets one leg with its strike and expiry, a count that says it is a count, a since-clock, and each
  leg's own VALIDATE word side by side.
  - It names a leg at 1,664 of 2,250 closes [M].
  - At her 29 entries it named one at 25 [M].
  - It answers her question, "buy the call or sell the put here", in one word.
- **Where it is weak, in plain words:**
  - **It changes a lot.** The word changes at 1,010 of 2,232 closes [M]. Its median life is one bar. 562 of its 1,028 runs
    last a single read [M]. The since-clock is what makes it usable: a word that has stood for four bars and one that
    appeared this bar are not the same read.
  - **Most of its directional words are weak.** 841 of 1,389 are LEANS [M]. Treat LEANS as "either, with a tilt".
  - **Before about 09:30 it can never say SELL** (R3 and R4 by construction). Open-drive trades will always read BUY-side
    or STAND ASIDE.
  - **LEANS BUY · selling refused is the commonest directional word,** 270 of 516 LEANS BUY closes. 172 of those 270 rest
    on R6, "no wall behind the sale" [M], and in-sample R6 is inflated by the nearer-only fronts on 09-22 and 09-23.
  - **The sale sits near the money.** At SELL words it was a median 0.19 straddles out (quartiles 0.09 / 0.19 / 0.34) [M].
    That is a real near-ATM short with real gamma, not a far strike.
  - **The falsifier is lenient** (inherited from VALIDATE). Each claim is a direction on medians at ≥ 15 units, so a word
    with no edge can pass it for a while. It is a safeguard against a word that is wrong, not proof that a word is right.

**Part C, for an open-ended short.**
- **On her option's expiry day** it is today's window plus a hard strike stop (3s). That is tighter than today, never looser.
  Good.
- **Off expiry**, a sale of the nearest expiry with its strike more than one ATM straddle out (S was 250–600 pts on the two
  index-days checked [M]) can be held through a line break.
  - While held, the adverse move can run from the line to "strike within one straddle" before 3r folds her. The printed held
    loss is a Taylor estimate over a long distance [I].
  - **The backstops:** 3r, 3s, and rules 4 and 6 while OI reads (C-S1).
- **What it cannot see:** only closes are read, so a bar can go through the strike and back inside it (§C.3).
- **3s is the right idea for a writer, with two costs:**
  - it folds on a poke through the strike that reverses (09-24's 74,000, above);
  - as written, it folds about a third of sales at the rounded ATM strike at their first close with no move (B/C-M3).
- **The seller-desk design's own line** (the models' design, not her words): with execution free, "stops get TIGHTER not
  wider (scratch and re-enter freely)". A fold at the line is cheap for her to undo. The reach loosens a stop to save a
  re-entry that costs her nothing. That is a reason to ask her whether she wants the reach off expiry at all (Mary's list).

---

## 5. Verdicts

### Part A: **SIGNABLE WITH TEXT EDITS**

None of these changes a rule, a number or a population:
- **A-T1 §H.2:** close it. STAND ASIDE · led is registered in §A.4 on rev 0's named choice, and confirmed here as the
  trader's reading.
- **A-T2 §H.1:** record a decision in place of "hers to say".
  - Recommended as the trader: fact 5 and §A.5 keep reading the ATM straddle on expiry day. Parity is exact on any day, her
    quote concerns the band-rotation anchor, and §A.5 already prints the S4 row on 0DTE.
  - If the coordinator would rather ask her, ask before signing: a "yes" changes A's rule and is a new revision.
- **A-T3 header line 38:** replace "her one decision" with the list of what is still hers (§H.5; the 90-minute write
  guard). Remove "can be signed" at lines 38–39, 573, 669–670 and 1537.
- **A-T4 §A.4 (lines 271–275):** "LEANS: a single fact decides, or, by refusal, a tie (printed 'the facts tie')".
- **A-T5 §D.1 / §G rev c:** 121 of the 169 refused ties carry R6, which over-fires on 09-22 and 09-23 [M].
- **A-T6 §D.7 / §E.2, the reachability of each refusal population:**
  - SELL · buying refused and LEANS SELL · buying refused occurred at 4 of 2,250 closes and 0 of 216 units [M]. Expect
    them to end inconclusive and DRAFT [I].
  - A unit whose refusal includes R6 is never scored (no sell strike): 60 of 84 BUY · selling refused closes, 172 of 270
    LEANS BUY · selling refused, and 112 of 226 STAND ASIDE · led [M]. So are all 9 grid BUY · selling refused units [M].
- **A-T7 §D.2:** rev a's "185 direct BUY ↔ SELL flips" is not comparable. Rev a had no LEANS, so every directional word was
  "strong".
- **A-T8 §D.4:** name the sold leg's strike and placement (e.g. #19–#22: CE 74,200 at the wall). Say that §D.6 reads a
  different leg, the call at her own strike. Otherwise #20 and #21's "14:38 r3" and §D.6's "74,000 … 13:05 rule 3s" read as
  a contradiction.
- **A-T9 copy** (§A.3 lines 151, 155, 184; §A.5 line 323; §F.1 lines 1272–1274):
  - "SHIELD" → "the wall behind the sale";
  - "the defended floor" → "the building PE wall";
  - once: "a wall is where writers are adding, not a bound on price" (S12's rule, applied to the wall).
- **A-T10 §A.7 / §F.1:** until §B is signed, the writer's card shows VALIDATE rev 2 §1.6's writer screen, not a §B word.
- **A-T11:** "rev 4 §1's principle" (header line 51, §C.3 line 589) → rev 4's opening "Why this exists" (line 33).

### Part B: **NOT YET**

| blocker | a new number? | only Mary's? |
|---|---|---|
| **B-M1** the stratum's stale "line inside the strike" (line 476; §E.1 line 1062): the text and the disclosure code judge different populations (91 against 133 legs [M]) | no | no (method detail) |
| **B-M2** a writer's GO can stand on an unread risk fact (OI blind, straddle unreadable, no greeks) while §A refuses the same sale (R3, R4): it fails open | no | no |
| **B/C-M3** GO on a sale more than one candle in the money, which 3s folds at its first close with no move; "the entry check says so" is not registered | no (B_k is inherited) | the fix, no; whether such sales should fold at all, **yes** (§H.5) |

The four facts, the outcome, both populations and the key change are sound.

### Part C: **NOT YET**

| blocker | a new number? | only Mary's? |
|---|---|---|
| **B/C-M3** (as above) | no | the underlying question, yes |
| **C-M4** 3s pooled into 7b-B as a rule-3 stamp (it can kill the line rule); 3s has no kill clause of its own | no (7a-B's own definitions) | no |

Should-fix with them: C-S1 to C-S5. Her NO is registered correctly, fails closed, and reproduces on 09-24.

---

## 6. Mary's to decide

1. **(§H.5, behind B/C-M3)** Does she sell in the money, or at the rounded ATM strike when it sits in the money? As
   written, about one such close in three [M] is a sale that folds at its first 3-minute close without a move. Keep that
   (and VALIDATE says NO), or let 3s read only sales made out of the money?
2. **(not blocking)** Off expiry, keep the reach, or "fold as today" everywhere, with 3s added?
   - For keeping it: it rarely binds, and binds only for a nearest-expiry sale more than one straddle out.
   - Against: its kill clause will likely never reach 15, so it stays in force unjudged, and free execution makes a fold
     cheap to undo.
   - Her expiry-day answer's words ("fold as today") are the natural place to ask it.
3. **(only if the coordinator prefers asking to deciding, A-T2)** On expiry day, should fact 5 and the sale's placement also
   set the ATM straddle aside?

**Not hers:** STAND ASIDE · led. Confirmed here as the trader's reading.

---

## Summary

| part | verdict | blockers | text edits |
|---|---|---|---|
| **A** the expression | **SIGNABLE WITH TEXT EDITS** | none | A-T1 to A-T11 |
| **B** the writer in VALIDATE | **NOT YET** | B-M1 stratum text vs code · B-M2 GO on an unread risk fact (fails open vs R3 / R4) · B/C-M3 GO then a first-close 3s fold | B-S1 |
| **C** the writer in the window | **NOT YET** | B/C-M3 · C-M4 3s pooled into 7b-B, no fate of its own | C-S1 to C-S5 |

**M1–M9 are all closed.** No blocker needs a new number. One question behind B/C-M3 is hers; the fixes themselves are
method details on her delegation.

`git status --short docs/` after this review: only `docs/hold/EXPRESSION-REVIEW-2.md` added.
