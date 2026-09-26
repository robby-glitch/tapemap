# Third review: `EXPRESSION-PREREG-DRAFT.md` rev d (the expression, the writer in VALIDATE, the writer in the window)

Independent adversarial third pass, in the form of `EXPRESSION-REVIEW.md` and `EXPRESSION-REVIEW-2.md`.
Written 2026-09-26 19:49 IST (read from the clock; the review began at 19:33). This is the only repo file written. No
server was touched, nothing was POSTed, `data/` was not opened, and nothing was committed.

**The draft as read:** sha256 `592d9948d5cb3a4fb81642c4217551a68d882b5248551eef6bcb4fb63f04f10f` [M], mtime
2026-09-26 19:32:45 IST [M]. It matches the hash I was given. I hashed it again at 19:48, and it had not changed.

**What I read:**
- the draft, in full; both earlier reviews;
- rev c's and rev d's fingerprint copies (`rules_revc_before_run.md` `64ad9d7f…2010`, `rules_revd_before_run.md`
  `78b5f86c…d260`, both hashes verified [M]);
- the signed rules the draft amends or inherits: rev 4 (`PREREG-merged.md` "Why this exists", §1–§4, §7 W1/W2, §11.2),
  rev 5 (`PREREG-rev5.md` §A.0, §D items 7–8 and 14, §F.4), VALIDATE rev 2 (§1.6, §2);
- the live window's writer code: `hold.py` (`read`, `_holders`, the squeeze at line 470), `ui-v2/src/hold/HoldWindow.tsx`
  and `parts.tsx`;
- rev d's code (`expr_d.py` over `expr_c.py`, `expr_a.py`, `expr.py`), `run_d.py`, every file in `revd/`, the run log, and
  rev c's saved outputs in `revc/`;
- `HANDOFF-2026-09-26.md`, and the memory notes `how-she-sells`, `both-ways-expression`, `no-trades-after-3pm` and
  `trader-decides-ui-questions`.

**What I ran, all read-only, in my own scratch folder (`scratchpad/review3/`), Python with `-B` and
`PYTHONDONTWRITEBYTECODE=1`:**
- `diff` of rev d's fingerprint against the draft, and of rev c's fingerprint against rev d's, section by section.
- **Reproduction** of §D.1 (all 18 rows and the totals), §D.2, the refusal-word table, §D.4 (all 29 rows and the counts),
  §D.6 (both tables), §D.7 and §D.8 from `revd/*.json`, and a field-by-field comparison of `revd/stability.json` with
  `revc/stability.json`.
- **An independent re-run of "no word moved"** (`percl.py`): rev c's `expression_c` and rev d's `expression_d`, each in its
  **own fresh process**, at all 2,250 closes, then compared close by close (`cmp.py`). The same pass read the rev d writer
  word at the ATM sale of every close, to see which of §A's sell refusals it can stand beside.
- **One construction probe at the 216 grid units** (`units.py`): whether writer NO lines up with R1, and which units the
  code leaves "not scored".
- `git status` before and after.

**What I did not run:** no word was scored against an outcome, and no candidate rule was run. **Not showing you:** I did not
join any word to an outcome row. Of the writer outcome I read only whether a unit *can* be scored.

---

## 1. Are the second review's items closed?

| item | status | where, and what the text does now |
|---|---|---|
| **B-M1** the stratum's stale "line inside the strike" | **CLOSED** | §B.3 lines 494–496: the stratum is Cushion's WITH as §B.1 defines it (line > noise and P ≥ X); units with the line at or beyond the strike are kept, flagged and shown split. §E.1 line 958 matches. The code agrees (`expr_d.py` line 112) [M]. |
| **B-M2** a writer's GO on an unread risk fact | **CLOSED** | §B.2 lines 440–447 and §E.1 line 959: could not check on Your wall, Cushion or Time is paying reads WAIT. `expr_d.word_of` implements it, with self-checks. At the 2,250 closes, **no GO stands beside R3 or R4** [M]. A related contradiction is still open (**B-N1**, §3). |
| **B/C-M3** GO, then a first-close fold by 3s | **MOOT** | Rule 3s is withdrawn (§C.2 lines 534–535). No strike rule is left to fold a sale at its first close. |
| **C-M4** 3s pooled into 7b-B, no fate of its own | **MOOT** | 3s is withdrawn; 7b-B is untouched (§C.2, §E.4 line 1117). |
| **A-T1** §H.2 "still open" | **CLOSED** | §H.2 lines 1459–1460: STAND ASIDE · led is registered and confirmed. |
| **A-T2** "hers to say" on the expiry-day straddle | **CLOSED** | Decided as the trader: §A.3 lines 240–242, §E.1 line 953, §H.1 line 1457. |
| **A-T3** "her one decision", "can be signed" | **CLOSED** | Header line 51 names what is still hers (the 90-minute write guard). "Can be signed" appears nowhere in §A–§C, §E, §F or §H [M: grep]. |
| **A-T4** LEANS has two meanings | **CLOSED** | §A.4 lines 291–292. |
| **A-T5** 121 of 169 refused ties carry R6 | **CLOSED** | §D.1 lines 662–675, reproduced (§2). |
| **A-T6** reachability of the refusal populations | **CLOSED** | §D.1 lines 676–677 and §D.7 lines 895–897. Its R6-unscored half is **MOOT**: rev d prices every sale, and R6 units are scored (§E.2 line 990). |
| **A-T7** rev a's 185 flips not comparable | **CLOSED** | §D.2 lines 705–706. |
| **A-T8** §D.4's sold leg vs §D.6's | **CLOSED** | §D.4 lines 748–749 names the ATM leg with rev c's strike beside it. §D.6 line 853 names "the call at the same strike". The 13:05-3s-vs-14:38 clash it guarded against is gone with 3s. |
| **A-T9** SHIELD, "defended floor" | **CLOSED** in the draft's own copy | WALL in §A.3 lines 163, 167 and 196, §E.1 line 951 and §D.3. "A wall is where writers are adding, not a bound on price" at lines 200–201. "Defended floor" is gone [M: grep]. The window's signed copy still says "the floor holds" (C-T6, §3). |
| **A-T10** the writer's card if §B is unsigned | **CLOSED** | §A.7 lines 366–367. §F.1's card (line 1160) does not repeat it (optional, A-T17). |
| **A-T11** "rev 4 §1's principle" | **CLOSED** | Header line 62, §C.2 line 537: rev 4, "Why this exists". |
| **B-S1** §E.1 "the strike range" | **CLOSED** | §E.1 line 958. |
| **C-S1 – C-S5** | **MOOT** | All five were about the reach and 3s, which are withdrawn. "250–600" is gone [M: grep]. |

**The second review's "Mary's to decide":** item 1 (in-the-money sales) and item 2 (the reach off expiry) are answered by
her. Item 3 was decided as the trader (A-T2).

---

## 2. Does the disclosure hold?

**The fingerprint holds.**
- The draft outside §D and §G's post-run lines (1442–1450) is **byte-identical** to `rules_revd_before_run.md` [M: diff].
  That includes the header and §H. The rules did not move after rev d's run.
- The timestamps are in order [M]: fingerprint 19:22:43; `expr_d.py` 19:24:01; `run_d.py` 19:25:43; outputs 19:27:21–
  19:27:58; the draft 19:32:45.
- Rev c → rev d's rule changes are each logged in §G's rev d entry (lines 1391–1441) [M: I diffed the two fingerprints].
- **In the rules sections, no withdrawn object is left as a live rule.** I grepped §A–§C, §E, §F and §H for the reach, 3r,
  3s, K₀, r/S, "defended", "floor", "can be signed", W-R, held loss, `sell_hold`, SHIELD and B_k [M]. Every hit is a
  withdrawal notice, a history line, the ban sentence at line 200, or PLAN's DEFENDED front state (line 182).

**"No word moved" is genuine, not an artefact.**
- **Independent processes.** In fresh processes, one per revision, all 2,250 closes gave **0 words moved, 0 buy-refusal
  sets moved, and 0 sell-refusal codes added or removed at any close** [M]. `run_d.py` computed its own comparison in the
  same process as rev d; mine did not share state.
- **Against rev c's saved run.** Every field shared by `revd/stability.json` and `revc/stability.json` is identical, in the
  totals and in all 36 index-day × cadence rows [M].
- **Why, by construction.** R1 and R2 read the short leg's entry check and YOUR SIDE, and neither reads the strike:
  - the squeeze in `hold.py` (line 470) is the sign of `dpx` against `d`, which is direction, not distance to the strike;
  - so moving the sale to the ATM strike at 1,473 closes [M] could not move them.
  - R4's new "S at `t`" clause never fired alone: R4-could-not-check is 138 in both revisions [M].

**The tables reproduce** from `revd/*.json`:

| table | reproduced? |
|---|---|
| **D.1** | Yes: all 18 index-day rows, the totals (BUY 293 (209 · 84), LEANS BUY 516 (246 · 270; 169 ties), EITHER 275, LEANS SELL 325 (323 · 2), SELL 255 (253 · 2), STAND ASIDE 586 (360 · 226)), and the every-minute line [M]. **The refusal-word table:** 84/60/39 · 101/51/35 · 169/121/105 · 226/112/96 · 360/96/5 · 4/0/0 [M]. |
| **D.2** | Yes: 1,010 of 2,232; 3 min; 562 of 1,028; 11; 185; 841 of 1,389; per minute 1,957 / 2 / 869 / 8 / 369 / 2,556 of 4,189 [M]. |
| **D.3** | The refusal table matches `revd/refusals.json` (R1 355, R2 311, R3 98, R4 24, R4 could not check 138, R5 372, R6 440) [M]. The facts and co-occurrence are rev a's: the facts code is unchanged (`expression_d` calls `expression_a`), and the second review reproduced them. "478 / 102" matches the second review's 478 / 83 + 19. |
| **D.4** | Yes, all 29 rows. **BUY 7, LEANS BUY 9, SELL 3, LEANS SELL 4, EITHER 2, STAND ASIDE 3 (2 · 1), could not check 1** [M]. No entry word moved from rev c's file [M]. **20 sold legs moved** from a rev c strike, and #9 is newly priced (21 differ in all, as the text says) [M]. **Writer GO 7 / WAIT 19 / NO 2**, and the could-not-check clause moved none [M]. **The line beyond the strike at 27 of 28** [M]. |
| **D.5** | **Could not check its facts**, as in the second review: the three rows are written by hand, and the 09-25 facts at the close were never frozen. Rev d changes nothing that reads them. |
| **D.6** | Yes: 74,200 10:43 rule 4 at 138.2 · 22.15 · 0.15; 74,100 14:38 rule 3 at 47.55 · 33.55 · 0.15; 74,000 67.75 · 50.2 · 0.2; 73,900 95.9 · 76.1 · 0.1; 73,800 133.1 · 111.2 · 0.1 [M]. The 216 legs: 108 / 54 / 35 / 19, and 48 on an expiry day [M]. |
| **D.7** | Yes: 216 units, 26 / 51 / 35 / 41 / 14 / 49, with every count · refusal split. **G scored at 204** (12 not: 6 no premium, 6 no greeks); rev c's committed §D says 160 [M]. **The writer population** GO 72 / WAIT 109 / NO 35; in the stratum 72 / 77 / 21 = 170; beyond the strike 71 / 74 / 19 = 164; 196 of 216 beyond; resolved 78 (all in the stratum), 127 to 15:29, 38 not scored [M]. |
| **D.8** | Yes: 36 of 216 units; 18 legs start at 15:14; 19 unfolded to 15:29; 14.0 / 17.55 / 19.8 / 21.9; 116.05 [M]. |

**The code implements the fingerprinted text,** read against the five places named:
- **§A.4 R4:** `expr_d.py` line 31 adds "could not check" when S at `t` is unread; "both rose" and fact 5 unread are
  `expr_a`'s.
- **§A.5:** the sale is the buy's `k` (lines 23, 34). It is priced at every close, R6 included.
- **§B.1 fact 2:** `wall_behind` (lines 42–45) is the same test as §A's fact 3 in `expr_a` (lines 56–58). OI blind is could
  not check; no wall is NEITHER, not could not check, as §B.1's table says.
- **§B.2:** `word_of` (lines 48–54).
- **§B.3:** the stratum (line 112). **One mismatch, inherited from rev a's code:** §B.3's "not scored" list does not match
  what the code leaves unscored (B-T1, §3).
- **Writer NO lines up with R1 at all 216 units** (35 each) [M].

**Her 15:00 practice still gates nothing.** Rev d removed `after_1500` from the window's rows, the only place it was added.

---

## 3. What came in with rev d

### Her answers: registered faithfully?

**Mostly yes. Three places read more into her words than they say.**

| the coordinator's reading | follows from her words? |
|---|---|
| **"Fold as today, everywhere"**: no reach, on or off expiry | **Yes.** She chose it in the question tool. |
| **No strike stop at all** | **Yes, fairly.** She sells "atm or even itm" on purpose and says her exits are "zones and levels oder flow and oi read". A strike stop would fold her own entries. |
| **The sale is named at the ATM strike** | **Yes, as a registration for the read.** "atm" is the first strike she names. §A's facts and refusals are strike-free [M: nothing moved at 1,473 re-struck closes]. The in-the-money case is printed ("one strike ITM reads the same facts"). **Over-read (attribution):** "the same strike as the buy" is parity's choice, the draft's, not her words. Yet §A.5 line 332 and §E.1 line 956 label the rule "her words" (A-T16). |
| **"Her danger is her level or zone breaking … The window already folds on exactly those: rule 3 at her line, and rules 4 and 6"** (§C.2 lines 540–541) | **Over-read.** The window's line is rev 4 §2's L: the last 5-minute swing beyond price, trailing. It is not her drawn zone. Rule 6 also counts the TREND rows (5m / 15m / 1h price structure). "Exactly those" should read "the window's own version of those" (C-T1). Whether that line is the level she means for a sale is **hers to confirm**. It does not block: it is the line she signed for both roles. |
| **"The line's one-candle buffer stays (rev 5 B, signed)"** | **Correct handling of an ambiguous remark.** "i dont care about candle" could reach rev 5 B's buffer. Rev 5 B is signed, and the draft keeps it and says so in words she can correct. **Hers to confirm**, not blocking. |
| **Header line 25: "no strike stop, in her words"** | **Attribution only.** "No strike stop" is the reading; her words are the quote (A-T16). |

### Is anything now inconsistent with a trader who sells at the money, or in the money in a trend?

1. **R2 says "while spot moves toward her strike"** (§A.4 lines 259–260). For a sale in the money, the squeeze is spot
   moving *away* from the strike. The code reads direction (the `dpx` sign against `d`, `hold.py` line 470), so the
   behaviour is right and the sentence is wrong. The "ATM" sale is in the money by rounding at **108 of 216** grid units
   [M]. Text only (A-T12).
2. **Rev 4's own writer text, which §C keeps, has the same geometry:**
   - §4's "toward her strike";
   - W1's "while spot moves away from her strike";
   - the window's copy (rev 5 §D item 7″, `hold.py` lines 713–714): "spot moving toward your strike — a squeeze" and
     "your strike is farther from spot than at entry".

   For her in-the-money sales each reads the wrong way round. W1 is not yet computed by any code [M: grep]. §C should say
   how the unchanged text reads for such a sale: by her direction, as rev 4 §4's own "(grounds' `dpx` sign)" and the live
   code do. The copy fix is owed separately (C-T3).
3. **§A.1 line 114, "she needs a wall behind her strike."** Fact 3's wall is behind *the sale*: at or beyond spot, on the
   out-of-the-money side. For a sale at or in the money it is not behind the strike (A-T13).
4. **Cushion for a sale in the money** (§B.1 fact 3). P carries intrinsic value, so P ≥ X nearly always holds there, and
   the Cushion reads mostly its noise test [I]. It is flagged as least trustworthy, but not explained. Disclosure (B-T3).
5. **The expression's SELL is a time-beats-move word.** In a trend SPEED, REGIME and (usually) PREMIUM vote BUY by
   construction, so §A will seldom name her in-the-money trend sale. By parity that is not a contradiction: at one strike,
   buying the call beat selling the put exactly when the straddle rose. But she should be told that §A does not endorse
   that trade, and that only §B reads it, at her press (A-T15).

### New defects

**B-N1 (blocker for B): a writer's GO can stand beside §A's R6 refusal of the same sale, on the same wall.**
- **Rev d made the two walls one object** (§B.1 line 405: "Exactly §A.3 fact 3's wall behind the sale").
  - §A refuses SELL when that wall is absent (R6, line 268: "no wall behind the sale").
  - §B reads the same absence as NEITHER, "checked, none" (line 398), which is VALIDATE's one allowed NEITHER.
  - So Right now HOLD, Your wall none, Cushion WITH and Time WITH read **GO**.
- **Rev d also prices and prints every R6 sale** (§A.5 line 340, §F.1 line 1160: "dimmed with R6's reason, and still
  priced"). The writer's word now appears on that dimmed card: "selling refused — the PE wall is already behind price"
  beside "GO".
- **Measured** [M]:
  - writer GO beside a §A sell refusal at **131 of 2,250 closes**, and at **12 of 216 grid units**;
  - every one is **R6 alone**; no GO stands beside R1, R2, R3 or R4.
  - All 131 fall on **09-22 and 09-23**, the nearer-only fixture days where R6 over-fires. How often a full-fronts
    session will show it is "could not check".
- **Why it matters:**
  - It is the contradiction B-M2 was fixed to remove. §B.2's own reason (line 446) is "one minute could show SELL refused
    … in §A beside a GO in §B", and the clause covers R3 and R4 but not R6.
  - It also cuts against her own OI read. With none of the sold side's top two at or beyond spot, her side's writers sit
    on the wrong side of price, and a new sale joins them.
  - The buyer's side has no such gap: R5 is the entry FOLD, which is VALIDATE's NO.
- **Fix, with no number:** for a writer, GO also needs the wall behind the sale. With none, the word is WAIT: "not there
  yet: no wall behind the sale (R6)". It is WAIT, not NO, because NO stays the entry FOLD, as P2-W reads it.
  - This moves 12 grid units' words from GO to WAIT in-sample [M: construction count]. It is a rule change, so it needs a
    fingerprinted rev e and its run.
  - It is a method detail, not Mary's.
- **The weaker alternative:** keep GO and print "§A refuses this sale (R6); this word reads your press" beside it. That
  leaves two answers on one card, so I do not recommend it.

**Text-only defects** (none changes a rule, a number or a population):
- **B-T1, §B.3's "not scored" list contradicts the code.**
  - The code leaves the **32** units with the line inside one candle unscored: Cushion is AGAINST before X is read [M].
    §B.3 does not list them.
  - §B.3 lists X > P as not scored, but the code scores those **8** units [M]; only the stop can resolve there.
  - Neither group is in the stratum, so no judged population moves. But §D.7's "not scored: 38 · to 15:29: 127" follow the
    code, not the text.
  - Fix: list "the line inside one candle (X is not read)", and say which way X > P goes. Note it in §D.7.
- **B-T2, §E.3's log cannot compute §B.3's split.** The stratum's "line at or beyond the strike" needs spot or a flag.
  The `expr` row carries `line`, `noise` and `sell.k`, but not spot or L. Add `beyond_strike: bool` to the `writer` object,
  or `spot` to the row.
- **A-T14, §E.2's "not scored" list lacks "a premium missing".** That is 6 of the 12 unscored grid units [M].
- **C-T2, rev 4 §11.2 item 2 is left dangling.** It reads: "the line half (a minimum-room clause, or a wider structure
  for writers) is hers to register or reject". Her "fold as today, everywhere" answers it. §C should say so, and that W1
  keeps testing the line.
- **C-T4, §C.3 lines 555–556: "a fold costs her little to undo".** Brokerage is zero, but statutory charges are rebated
  only on a close at least ₹1 positive. A fold at her line usually closes at a loss, so it pays them [I].
- **C-T5, §F.2 line 1177 quotes "YOU ARE SHORT" as the live window.** That string is in neither `ui-v2/src` nor `hold.py`
  [M: grep]. What is live:
  - "short · qty {q} · in HH:MM" (`HoldWindow.tsx` 218);
  - YOUR SIDE (`hold.py` 709);
  - "not shown — a writer has no quiet clock; time pays her" (`hold.py` 589);
  - "none — a writer: the stop alone" (`HoldWindow.tsx` 249).
- **C-T6, §A.3's ban vs the window's signed copy.** §A.3 now says no sentence calls a wall "a floor that holds". The
  window, which §C keeps unchanged, prints "the floor holds" / "the ceiling above you holds" on a writer's own side (rev 5
  §D items 7 and 8, `hold.py` 726). Scope the ban to the expression and the Validate tab, and disclose the window's copy.

**Checked, and none found:**
- a rule that fails open (besides B-N1, which is a contradiction on a known absence, not an unread input);
- a falsifier that cannot be computed, other than B-T2's shown split;
- a population that can never reach its count, beyond the two already disclosed: SELL and LEANS SELL · buying refused,
  and her writer presses;
- an unsaid change to VALIDATE rev 2, rev 4, rev 5 B or PLAN. §B's clauses amend VALIDATE §1.6, §2, §3 and §4, as the
  header lists.
- safety-implying copy in the draft's own text (C-T6 is the window's signed copy).

---

## 4. The trader lens

**At the moment a setup pops, part A plus the writer's word is usable, and simpler than rev c.**
- **One word for one question:** buy the call, or sell the put, **at the same strike**. The sale is now her sale: at the
  money, not a strike parked behind a far wall.
- **Two cards side by side,** each with its own VALIDATE word. The writer's NO is exactly the window's entry FOLD
  (35 of 35 at the grid units [M]).
- **A since-clock,** and a count that says it is a count.

**Still weak, in plain words:**
- **The word changes a lot.** It changes at 1,010 of 2,232 closes, and 562 of its 1,028 runs last a single read [M]. Read
  the since-clock before the word.
- **Most directional words are weak.** 841 of 1,389 are LEANS [M]. Read LEANS as "either, with a tilt".
- **It cannot say SELL before about 09:30** (R3 and R4, by construction).
- **LEANS BUY · selling refused is the commonest LEANS BUY:** 270 of 516, and 172 of those rest on R6 [M], inflated by the
  nearer-only days.
- **It will seldom endorse her trend sale.** In a trend the facts vote BUY. Her in-the-money trend sale is read only by
  §B at her press.
- **Two answers on one card (B-N1).** On an R6 minute the tab can say "selling refused — no wall behind the sale" and "GO"
  on the same card.
- **The writer's Cushion leans on a flagged estimate on almost every sale she makes.** The line lies beyond the strike at
  196 of 216 grid units [M] and at 27 of her 28 entries [M]. X is a Taylor estimate there, which PLAN §7 calls least
  trustworthy. For a sale in the money, P ≥ X nearly always passes [I].
- **The window's line is a 5-minute swing, not her zone.** If her zone sits farther out, the window folds her sale before
  her level breaks. 09-24 is the example: 11 sold calls folded at 14:38 by rule 3, and each ended at 0.1–0.2 [M]. She
  chose "fold as today", and it is disclosed.
- **The judged writer test off expiry mostly tests direction** (S11, disclosed). The falsifiers are lenient: they guard
  against a word that is wrong, and do not prove one right.

---

## 5. Verdicts

### Part A: **SIGNABLE WITH TEXT EDITS**

None of these changes a rule, a number or a population:
- **A-T12, §A.4 R2 (lines 259–260):** "while spot moves against her direction (rev 4 §4's `dpx` sign; for a sale out of the
  money, toward her strike)".
- **A-T13, §A.1 line 114:** "a wall behind her strike" → "a wall behind the sale (fact 3)".
- **A-T14, §E.2 "Not scored":** add "a premium missing".
- **A-T15, §A.8:** add a hazard. In a trend SPEED, REGIME and PREMIUM vote BUY by construction, so SELL is a
  time-beats-move word. Her in-the-money trend sale is read by §B at her press, not endorsed by §A.
- **A-T16, attribution** (header line 25, §A.5 line 332, §E.1 line 956): "her words" covers only the quote. "No strike
  stop" is the reading of her words (§C.2), and "the same strike as the buy" is the draft's choice, by parity.
- **A-T17 (optional), §F.1 line 1160:** repeat §A.7's fallback: "or VALIDATE rev 2 §1.6's writer screen if §B is
  unsigned".

### Part B: **NOT YET**

| blocker | a new number? | only Mary's? |
|---|---|---|
| **B-N1** a writer's GO can stand beside §A's R6 refusal of the same sale, on the same wall: 131 of 2,250 closes and 12 of 216 units, all on the nearer-only days [M]. Fix: no wall behind the sale → WAIT, never GO. | no | no (a method detail) |

With it, text edits **B-T1** (the not-scored list against the code), **B-T2** (a `beyond_strike` flag in the log) and
**B-T3** (Cushion in the money: P ≥ X nearly always passes [I]). B-M1 and B-M2 are closed. The four facts, the outcome, both
populations and the key change are sound. The fix changes 12 in-sample words, so it needs a fingerprinted rev e and its run.

### Part C: **SIGNABLE WITH TEXT EDITS**

§C now registers no change: a writer is folded as today, by rev 4 + rev 5 B, which she has already signed. Nothing in it
can fail open. The edits:
- **C-T1, §C.2 lines 540–541:** "exactly those" → the window's own versions: L is rev 4 §2's line (the last 5-minute swing
  beyond price, trailing), not her drawn zone; rules 4 and 6 read the fronts, the flow **and the trend rows**.
- **C-T2, §C.1 or §C.2:** her answer settles rev 4 §11.2 item 2 (the line half is rejected), and W1 keeps testing the line.
- **C-T3, §C.3:** for a sale at or in the money, rev 4 §4's "toward her strike" and W1's "away from her strike" read by her
  direction (the `dpx` sign), as the live code does. The window's copy (rev 5 §D 7″) reads wrong for such a sale, and a
  copy amendment is owed, not made here.
- **C-T4, §C.3 lines 555–556:** statutory charges are rebated only on a close at least ₹1 positive; a fold at a loss pays
  them [I].
- **C-T5, §F.2:** quote the live window as it is. "YOU ARE SHORT" is not in it [M].
- **C-T6, §A.3 / §C.3:** scope the "floor" ban to the expression and the Validate tab. The window's signed copy "the floor
  holds" is unchanged.

---

## 6. Mary's to confirm (none blocks)

1. **Is the window's line her level when she sells?** It is the last 5-minute swing beyond price (rev 4 §2), the line she
   signed for both roles. Her words: "its always zones and levels".
2. **Does "i dont care about candle" leave rev 5 B's one-candle buffer on the line in place?** It is signed, and the draft
   keeps it, stated in §C.2 so she can correct it.
3. **Still hers, not asked:** her "90-minute write guard".

**Not hers (method details on her delegation):**
- B-N1's fix;
- the ATM strike as the named sale (her "atm" first; "the same strike" is parity's choice);
- whether the engine ever names the in-the-money strike;
- the `dpx` reading of "toward her strike";
- the log flag and the not-scored list.

---

## Summary

| part | verdict | blockers | text edits |
|---|---|---|---|
| **A** the expression | **SIGNABLE WITH TEXT EDITS** | none | A-T12 to A-T16 (A-T17 optional) |
| **B** the writer in VALIDATE | **NOT YET** | **B-N1** GO beside §A's R6 refusal on the same wall (no new number; not Mary's) | B-T1 to B-T3 |
| **C** the writer in the window | **SIGNABLE WITH TEXT EDITS** | none | C-T1 to C-T6 |

**Of the second review's items:** B-M1, B-M2, A-T1 to A-T11 and B-S1 are closed. B/C-M3, C-M4 and C-S1 to C-S5 are moot,
withdrawn with the reach and 3s. "No word moved" is genuine: two separate processes, 0 of 2,250 [M]. Every §D number I was
asked to check reproduces.

**`git status --short docs/`:**
- **Before this review:** `M EXPRESSION-PREREG-DRAFT.md`; untracked `EXPRESSION-REVIEW-2.md` and rev d's scratch (`expr_d.py`,
  `gen_D_d.py`, `gen_tables_d.py`, `revd/`, `revd_run_out.txt`, `rules_revd_before_run.md`, `run_d.py`).
- **After:** the same, plus only `docs/hold/EXPRESSION-REVIEW-3.md` [M].
- The repo root's `__pycache__` predates this review (09-25 20:34) and is gitignored. No `.pyc` is newer than the draft [M].
