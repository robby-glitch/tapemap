# Review: `EXPRESSION-PREREG-DRAFT.md` (the expression, the writer in VALIDATE, the writer's reach)

Independent adversarial review, in the role and form of `REV5-VALIDATE2-REVIEW.md`. Written 2026-09-26
01:11 IST (read from the clock). This is the only repo file written. No server was touched, nothing was
POSTed, no `&log=1` was used, `data/` was not opened, and nothing was committed.

**The draft as read:** sha256 `d7c4a4defdeec9a02d57782821de8f12234c6731175ac49ced02760666494015`, mtime
00:48:18 IST.

**What I checked against:**
- `PREREG-merged.md` rev 4, `PREREG-rev5.md` (option B), `VALIDATE-PREREG.md` rev 2, `PLAN-PREREG.md`
  rev 3a, `HANDOFF-2026-09-25.md`;
- both "better trade" reports (`opus/`, `fable/`), for how the last read went silent;
- the doctrine the draft cites: `seller-desk-doctrine.md`, `delta-drag-the-buyers-tax.md`,
  `desk-scale-and-scope.md`, `two-regimes-and-setups.md`, and the band-rotation spec
  (`docs/superpowers/specs/2026-07-31-operator-band-rotation-setup.md`) that the draft quotes;
- the code the rules and logs come from: `hold_log.key`, `server._hold_tick` (the side log's `atm`),
  `upstox_instruments.resolve` (which expiry the chain poller tracks);
- the drafter's scratch (`expr/`): `expr.py`, `run.py`, the two fingerprinted copies, every output.

**What I ran, all read-only, in my own scratch folder (`scratchpad/review_expr/`):**
- `sha256sum` of both fingerprinted copies, and `diff` rev 0 → rev 0a → the draft as read.
- The drafter's `expr.py`, imported unchanged (no bytecode written), over the same nine frozen
  index-days, both directions, to read **construction properties only**: how often the word changes,
  the margin it is named by, which words exist only because the other leg was refused, how often the
  facts vote together, where the sell strike sits in straddles, where ROOM's line sits against the
  noise, and the 3-minute moves against the ATM straddle late on expiry.
- **One outcome-side check, not split by any word:** at the grid units the fixtures can price, which
  leg's % moved more (M1). It says nothing about which word was right.

**What I did not run:** no word was scored against an outcome, and no candidate rule was run.

---

## The drafter's own disclosures, judged

### 1. Fact 5 (PREMIUM) was changed after the first run

**Principled? Yes, on the principle. I would have required the change before any run.**
- Rev 0 read the *current* ATM strike's two legs against their own session VWAPs. The strike is
  re-centred every minute. So after a rise, the CE at the new ATM strike averaged when it was OTM and
  cheap, and the PE when it was ITM and dear, and "rotated" follows from the displacement alone. That
  is rev 4 §8's re-centring defect in a new place.
- **The draft under-sells rev 0a's best argument.** By put–call parity (CE − PE = F − K), a long CE
  minus a short PE at one strike is a long CE plus a long PE, which is a long straddle. So "did the
  fixed straddle gain" **is** "did buying beat selling", with direction cancelled exactly. Fact 5 is
  the one fact that reads the expression question directly. §A.2 should say so (S6).

**Chosen for its outcome? The risk is real, and it has to be visible.**
- The change was large, and it went one way:
  - words BUY 3,817 → 2,464 and SELL 871 → 1,734 (both totals reproduce from `rev0/silence.json` and
    `silence.json`);
  - all four entry words it moved went toward SELL: #16 EITHER → SELL, #17 BUY → EITHER, #22 BUY → SELL,
    #29 BUY → SELL.
- That is toward the draft's evident aim, a read that can say SELL. The lean was also foreseeable,
  because time wins most short windows (H.3 says so itself).
- Forward-only judgement protects the falsifier. What is owed is that the post-run fact stays visible
  forward (S7).

**Is the disclosure complete? No (M5).**
- **Three rule-text edits after the rev 0a fingerprint are not in §G:**
  - fact 5's own "equal" case moved absence kind. The fingerprint (`rules_rev0a_before_run.md`) reads
    *"equal, a premium missing at either end, or `t − 15` before 09:15: NEITHER, could not check"*; the
    draft now reads *"equal: NEITHER, a read"*;
  - *"So the count cannot lean by construction"* was struck after §D.1 showed ROOM and PREMIUM
    leaning;
  - §C.4's best-day sentence was rewritten, beyond the dedup that §G does log.
- **The header** says *"Two clarifications were made … §G lists them"*. That is not true as written.
- **An output is missing.** §D.0 lists `silence_detail.json`; it is not in `expr/`.
- **Two things are not said:** that every moved entry word went toward SELL, and the alternative not
  taken (drop fact 5 and count four).

### 2. The reach does not rescue 09-24

- **Honest, and it reproduces.** `seller_0924.json` gives S 321.6 at 14:38, R 36 / 136 / 236 / 336 /
  436, and 74,100 held then folded at 14:45 by rule 4, 47.55 → 42.45.
- **The unit is defensible, but not on the authority the draft gives it.**
  - *"Her own seller doctrine names that unit"* is not accurate. `seller-desk-doctrine.md` is the design
    Fable and Opus converged on in an exercise she ordered (2026-08-25). It is not her words.
  - Her own words on the ATM straddle carry an expiry exception the draft omits: *"since today was
    sensex expiry so that why otherwise atm straddle is ideal"* (band-rotation spec, 07-31).
  - The reach binds almost only on expiry afternoons. Off expiry the straddle on the fixtures was
    250–600 pts (NIFTY 09-24 and SENSEX 09-22, the two off-expiry index-days checked), so nearly every
    sold strike is inside it and the line decides as today.
  - **An independent check the draft could cite:** under the usual lognormal reading, one ATM straddle
    is about 0.8 σ of the move to expiry, so a strike one straddle out sits near 0.2 delta [I]. That is
    the same doctrine's first delta lamp (0.20). So the 1× scale is not arbitrary.
- **Sound on its own terms? Coherent, with two holes** (M7 unsigned R, M8 the wrong expiry's
  straddle).
- **Is the hard risk control kept? Partly.**
  - Near strikes fold at the line, and rules 4, 6 and the latch are untouched.
  - But the two holes let a writer be held in the money, and W-R's majority test cannot see the tail
    (M9).

### 3. The other disclosures

- **ROOM leans BUY.** It is inherited, but 871 of its 4,329 FOR BUY minutes had the line **inside one
  candle**, where VALIDATE's own §1.3 order never reaches the target comparison (S1). On the NIFTY
  09-23 range day, 103 of ROOM's 499 BUY minutes were of that kind.
- **An unreadable straddle does not refuse SELL.** It must fail closed, by the draft's own §C.2.4
  principle (M4).
- **The writer's 30-minute outcome rarely resolves.** P1-W is then out of reach (M6).
- **The far sell strike.** It is rarer than the 09-24 rows suggest (Q3). The far cases are expiry
  afternoons (S8).

### 4. Silence

- **Acceptable, and correctly described.**
  - At her entries it was silent on 4 of 29, one of them the unfrozen 09-21.
  - On the grid, silence gathers on the counter-trend direction. There, "both refused" means the long
    leg's entry check folds (R5 is the only buy refusal), so the word is true: the direction she would
    take reads broken.
- **Silence is not this read's weakness. Instability is (M3).**

---

## Part A — THE EXPRESSION

### What checks out

- **Fingerprints verify:** `rules_before_run.md` → `eca1afe0…2b6c`; `rules_rev0a_before_run.md` →
  `5ddc16d1…a654`. §D.1's totals and both `tally.json` files reproduce.
- **"One wall, one fact" holds strictly.**
  - `validate.geometry` drops GIVING WAY walls from ROOM's target, and SPEED reads them.
  - SHIELD and ROOM read opposite sides.
  - No strike is read twice.
- **The refusal order is principled, and printed honestly.**
  - A refused leg's majority makes STAND ASIDE, never a vote for the other leg.
  - A word named by refusal says so on screen.
- **Buyers are untouched.**
  - No buyer fact, word, outcome or key of VALIDATE rev 2 moves, and the `expr` key is additive.
  - `hold_log.key` recomputes keys from stored rows, so adding `role` to outcome keys keeps old rows
    readable. The `has()` call in `_hold_tick`'s VALIDATE outcome writer must change with it (a code
    note).
- **It speaks.**
  - At her entries it named a leg at 25 of 29 (BUY 14 · SELL 9 · EITHER 2).
  - On the grid it spoke on 5,003 of 6,750 minutes.
  - The round-3 gate is gone.

### Must-fix

**M1 — The outcome does not measure the expression.**

§E.2: *"The outcome for each leg is its premium at the 30th finished minute against the unit minute, as
a % of the unit-minute premium: long: (p30 − p0) / p0; short: (p0 − p30) / p0. The gap is G = long % −
short %."*; §E.1: *"rev 4 §7's unit (% of premium)"*.

- **% of own premium is a buyer's return on outlay.**
  - A writer has no outlay. Her premium is her maximum gain, and her capital is margin.
  - So short % is capped at +100% and unbounded below, while long % is floored at −100% and unbounded
    above. G subtracts two different quantities.
- **The two legs are different contracts:** ATM bought, and sold at the wall.
  - For the same index move, the further-OTM leg swings more in %.
  - On a 0DTE afternoon a far sale's % runs toward +100% whatever happened.
  - So G's size is set by where the wall sits, not by which expression was better.
  - Unconditioned check: at 91 of the 169 grid units the fixtures price, the sold leg's % was the
    larger in magnitude (median |short %| / |long %| 1.14). That is with the median sale only 0.19
    straddles OTM.
- **Rev 4 §7 used % of premium differently.** It compared one leg with itself across stamps and
  indices, never a long against a short. Inheriting it here is a change of meaning, not an
  inheritance.
- **Points alone do not fix it.**
  - At equal strikes, parity makes points exact: long CE pts − short PE pts is the straddle's P&L.
  - With a far wall, one lot each is not the same bet (Δ about 0.5 against a small Δ), so points
    reward direction, not expression.
- **Fix.** Register a unit both legs share by construction, name the sizing it embeds, and say why.
  - **Recommended: R-multiples on the one line both legs share.** Each leg's premium change over +30
    is divided by its own premium at risk to L at the unit minute.
    - The formula is PLAN §2.1's, as registered: a buyer's |Δ|R − ½ΓR², clamped to [0, premium]; a
      writer's |Δ|R + ½ΓR².
    - Δ and Γ are the broker's [M] greeks, so the figure is [I] on [M].
    - G is the long R-multiple less the short R-multiple.
    - The sizing it embeds is equal premium at risk to the same stop, which is how a stop-based
      trader sizes. It is her 1:1 lens, and no number is new.
    - No greeks: "not scored — could not check", shown.
  - **Shown, never judged:** G in points / S (the ATM straddle at the unit minute), and the % rows.
  - **Show every claim split** by the index's 30-minute move relative to `d` (with / against). Her
    claim is that direction is hers, so the read must not win only on the units where her direction
    was wrong.

**M2 — Words named because the other leg is refused are pooled with words named on the count.**

§A.3 rule 3: *"Only SELL refused: BUY {CE|PE} if `b ≥ s`"*; §E.2 judges "BUY units" as one population.

- **999 of the 2,464 BUY minutes (41%) exist because SELL was refused.** 416 of them were at a **tied**
  count, so without the refusal they would read EITHER.
- **The refusal codes:** R6 alone 579, R2 177, R2 + R6 117, R3 56, R4 54, and small combinations.
- The R6 units are not scored (no sell strike). That leaves about 290 scorable BUY-by-refusal minutes
  in-sample (R2, R3, R4) inside the BUY claim, where they test the refusals, not the facts.
- SELL-by-refusal was 13.
- **Fix.** §E.2 judges "BUY on the count" and "SELL on the count". Words named by refusal are their own
  rows, shown with the refusal code, and never pooled. (STAND ASIDE likewise, S3.)

**M3 — The word's stability is neither disclosed nor marked, and it is the property that decides
whether she can act on it.**

§F.1: *"THE EXPRESSION, one word, at the 88 px size the VALIDATE word uses today"*. There is no
since-clock.

- **On the nine index-days, both directions:**
  - the word changed 1,340 times, about 74 changes per session per direction;
  - its median run is **2 minutes**, and 498 of 1,358 runs lasted one minute;
  - it flipped **directly BUY ↔ SELL 365 times**;
  - **2,077 of the 4,198 BUY / SELL minutes (49%) were named by a margin of one fact.**
- **§D.2 shows it at her own entries:** #4 10:41 BUY PE 3–2, then #5 10:42 SELL CE 2–3, one minute and
  one fact (ROOM) apart.
- **Fix. No number is needed.**
  - Disclose these counts in §D; they are construction properties.
  - Print "since HH:MM · was {word} until HH:MM" under the word, as rev 4 §5 does for the window's
    word.
  - Register **when** the word is read and put the choice to her with these counts: every finished
    minute (as now), or at the 3-minute close (her candle; rev 5 A.0.1's grid). The §E.2 grid unit
    reads the word at one minute, so that choice also decides what the falsifier judges.

**M4 — R4 fails open, against the draft's own principle.**

H.4: *"An unreadable fact 5 does not refuse SELL as written. R4 fires only when read."* Against that,
§C.2.4: *"Could not check the reach, so the line decides. This is conservative, never lenient."*

- R4 is the only guard against selling into a bid straddle, the vega alarm. A safety refusal that is
  silent when it cannot read has failed open.
- **Fix:** "fact 5 could not check → SELL refused (R4 — could not check: {why})".
- Disclose that it moves the 09-25 09:35 row from SELL CE 0–3 to STAND ASIDE ("the facts favour
  selling, 3 to 0, but selling is refused: the straddle could not be read").
- This decision goes against the one in-sample row it touches (that call never came within 95 pts),
  so it is not taken for the look.

**M5 — Disclosure and attribution (applies to A, B and C).**

- **(a)** Log in §G the three post-fingerprint rule edits listed above (disclosure 1): fact 5's
  "equal", the struck "cannot lean by construction" line, and §C.4's best-day sentence.
- **(b)** Correct the header's "Two clarifications … §G lists them".
- **(c)** Remove `silence_detail.json` from §D.0, or produce it.
- **(d)** Add the direction of the four moved entry words, and the alternative not taken.
- **(e)** Correct the attributions. She signs on her own words, so each quote must be hers or labelled:
  - *"both legs decaying together … is just theta on a dead day"* (§A.1, §A.2, §B.1) is the spec's
    prose (band-rotation spec, about line 96), not a quote of hers;
  - *"1:1 atleast"* (§B.3, §E.1) is hers, but about a **buyer's** band-to-band exit; say so;
  - *"Her own seller doctrine"* (§C.1): the doctrine is the two models' converged design, adopted into
    her desk, not her words;
  - *"her ATM-straddle anchor"* (§E.1, fact 5): quote her expiry exception with it.

### Should-fix

- **S1 — ROOM should follow VALIDATE §1.3's own order.**
  - When the line is inside one candle (line ≤ noise), read NEITHER, a read: "your line is inside one
    candle's range — the reward comparison is not read". Do not read FOR BUY ("room to run").
  - The draft's reason for dropping the noise half (*"It is the same line for both legs, so it separates
    neither"*) is right for the noise as a fact. It does not license comparing a target with a line the
    noise will hit.
  - It moves up to 871 minutes, all out of FOR BUY. Disclose it as proposed by this review after ROOM's
    lean was seen.
- **S2 — EITHER.**
  - 639 of the 805 EITHERs were 2–2. *"Both are open; nothing separates them"* misdescribes a split:
    two facts separate them each way. Say "the facts split {b}–{s}".
  - State whether EITHER's claim (*"smaller than at BUY and SELL units"*) compares with BUY and SELL
    pooled or with each.
- **S3 — STAND ASIDE.**
  - 1,069 of 1,717 are "both refused", which on a two-direction grid is mostly the counter-trend
    direction with the long leg folding at entry. Its claim there re-tests rev 4 B4 / VALIDATE P2.
  - Split "both refused" from "led". Judge "led" as the read's own contribution; show "both refused"
    and say what it re-tests.
- **S4 — The mirror pair and co-timing.**
  - At one (index, minute), the UP and DOWN units share fact 5 and the straddle. They are not
    independent.
  - *"UP before DOWN"* means the reduced check never tests DOWN.
  - Judge UP and DOWN as separate populations, each on its own 15. State whether the judgement pools
    indices; *"split by index and direction"* reads as display only.
- **S5 — Disclose fact co-occurrence in §D.** No rule change is needed; the count's hidden weights
  should be visible.

  | pair (both votes) | together | if independent |
  |---|---|---|
  | SHIELD SELL · ROOM SELL | 908 | 514 |
  | SPEED BUY · REGIME BUY | 981 | 749 |
  | REGIME BUY · PREMIUM BUY | 654 | 574 |
  | REGIME SELL · PREMIUM SELL | 2,068 | 1,961 |
  | SPEED BUY · ROOM BUY | 1,665 | 1,926 |

  A pin is one condition with up to three SELL votes (both walls, plus REGIME "no side").
- **S6 — Put the parity argument in §A.2, and print the move's sign in fact 5's sentence.**
  - 1,144 of the 2,288 fact-5 FOR BUY minutes had the 15-minute move **against** her direction.
  - That is correct by parity (the straddle is direction-free), but "BUY CE — the move out-paid time"
    after a fall will be read as momentum unless the sentence says which way the move went.
- **S7 — Keep the post-run fact visible forward.**
  - Show fact 5's own rows in the judge: G at its FOR BUY and its FOR SELL minutes, shown, not judged.
  - Show the §E.2 claims also recomputed with fact 5 dropped from the count; the logged facts allow it.
  - This is rev 4 S1's treatment: flag it, and let the forward rows show it.
- **S8 — Name each leg's expiry, and show the sale's distance.**
  - Both legs are the chain record's nearest expiry; say so.
  - On 0DTE, a SELL names her doctrine's setup S4, the expiry flush ("logged, not traded"), and its "expiry afternoon →
    neither". Print that row beside a 0DTE SELL. Do not refuse on it; that is unregistered.
  - Print the sale's distance in straddles (R/S, of that expiry) and its Δ [M] beside it. That registers
    H.5 as a print.

### Verdict A: **NOT YET**

- **M1 and M2** are the falsifier: as written it cannot say which expression paid, and it pools two
  kinds of BUY.
- **M3** is the trader lens: a word whose median life is two minutes needs its since-clock and its
  counts in front of her.
- **M4** is a safety refusal that fails open.
- **M5** is the record.

None needs a new number.

---

## Part B — THE SELLER IN VALIDATE

### What checks out

- **Cushion reads a registered formula.** X is PLAN §2.1's writer formula, and the target P − X is a
  1:1 in premium.
- **The stratum follows VALIDATE rev 2's precedent.** "Line > noise and P ≥ X" is the second pass's M1
  logic (geometry controlled for GO, WAIT and NO alike).
- **The inherited objects are reused, not copied.**
  - Right now reuses the window's writer clauses.
  - Your wall has no AGAINST, mirroring §1.4's reason.
  - Time is paying is fact 5, read once.
- **The populations are kept apart.** Writer units are never pooled, and the key collision is named,
  with its test owed.
- **The stop / target asymmetry** (index range against premium close) is disclosed, and it errs toward
  `stop`, which is the conservative direction.

### Must-fix

**M6 — P1-W and P2-W will not reach their counts.**

§B.3: *"The unit is VALIDATE §3's: the first **writer** press per (index, `d`) per 30 minutes"*; H.1
leaves the horizon open.

- **Her record has no writer presses to count.** All 29 of her marked trades are long. The three shorts
  in the fixtures are examples ("EX").
- **At 30 minutes, 24 of the 28 sell legs read `neither`.**
- With resolved-only counting inside a stratum, 15 resolved GO **and** 15 resolved WAIT writer presses
  within 30 sessions is not a realistic event. The word would ship DRAFT with no path to judgement.
- **Fix.**
  - Add a second population, never pooled: **the writer word on the expression grid's SELL leg at every
    unit.** §E.3 already writes that leg's strike, premium and line; add the four writer facts and X.
  - It gets the same outcome, stratum and P1-W / P2-W, judged on its own count, exactly as §C.4 already
    does for W-R.
  - **Register the horizon now:**
    - keep 30 finished minutes for the judgement (inherited; on the grid, the non-overlap reason
      holds);
    - show the to-15:29 outcome beside it, not judged.
  - H.1 is then closed.

(M5's attribution items apply here too: "1:1 atleast" and "decaying together".)

### Should-fix

- **S9 — List every section amended.** The header names VALIDATE rev 2 §1.6. The draft also amends:
  - §2, whose word is "for a buyer";
  - §3, with writer outcome rows and the outcome key `(idx, t, d, "outcome")` gaining `role`;
  - §4, which is "buyers only".
- **S10 — X is a second-order estimate, and the legs that left the stratum are outside its range.**
  - Nine of the ten sell legs outside the stratum left it on X > P (`entries.json`):
    - the four NIFTY 09-22 legs had the line **beyond the strike itself** (line 78–99 pts, strike 58–78
      OTM);
    - the five SENSEX 09-24 legs had the line 215–401 pts away.
  - A Taylor expansion over a distance comparable to, or beyond, the strike's own distance from spot is
    outside its range.
  - Either state that, or read "could not check — your line is beyond your strike; the formula does not
    reach" when R ≥ the strike's distance from spot.
- **S11 — Say what the 30-minute writer target tests.**
  - Off expiry, 30 minutes of decay is small. So "premium falls by X before L" mostly means the index
    moved about R away, which is a direction test.
  - Say so beside P1-W, and show the to-15:29 outcome (M6).

### Verdict B: **NOT YET**

M6: the falsifier as written cannot be reached. With M6 and M5's attributions fixed, B is signable. The
four facts are sound.

---

## Part C — THE SELLER IN THE WINDOW: THE REACH

### What checks out

- **It fails closed where it says it does.**
  - S unreadable folds.
  - A strike inside one straddle folds at the line exactly as today.
  - Rules 4 and 6, the latch, PATA NAHI on a due close, and "no quiet clock" are untouched.
- **§D.4 reproduces** from `seller_0924.json`, and its result is stated against itself: *"the reach
  does not rescue 09-24"*.
- **The unit's scale has an independent anchor**: one straddle out is about 0.2 delta (disclosure 2).
- **The dedup follows the principle of rev 5 §F.1:** one break is one event.

### Must-fix

**M7 — R is unsigned, so a writer can be "held" in the money.**

§C.2: *"**R** [M]: |her strike − the bar's close|"*. §C.3: *"A held writer can never sit through her
strike: R = 0 < S whenever S > 0."*

- **That claim needs a close exactly at the strike.** On 3-minute closes, price steps over it.
- A bar that closes through her strike by more than S reads R > S, so she is "held", in the money.
- **The draft places the rule's benefit late on expiry, and that is exactly where the hole is widest,**
  because the straddle is about one bar wide there:
  - SENSEX 09-24 at 15:29: S 20.05 against a 139.3-pt 3-minute bar;
  - NIFTY 09-22 at 15:29: S 20.95 against a 20.5-pt bar.
- The scratch implementation carries the same: `reach_read`, `R = abs(k - px)`.
- **Fix.**
  - R is the **signed** distance from the close to her strike, on the strike's OTM side: k − close
    for a short CE, close − k for a short PE.
  - R ≤ S folds, so a close at or through the strike (R ≤ 0) always folds.
  - Test owed: a held writer whose bar closes through the strike by more than S is FOLD 3r.

**M8 — S is the nearest expiry's straddle, not her option's.**

§C.2: *"**S** [M]: the ATM straddle at that close's minute … the side log's own `atm: {k, ce_px,
pe_px}`"*.

- **Where the side log's `atm` comes from.** It is priced from the chain poller's grid
  (`server._hold_tick`, `px` from `F["core"]["minutes"]`). That grid holds one resolved expiry per
  index: `upstox_instruments.resolve`, the nearest live one.
- **What goes wrong.** A sale in another expiry (next week's on a 0DTE afternoon, or the monthly) is
  measured against the wrong market's expected move.
- On a 0DTE afternoon the near straddle collapses (SENSEX 09-24: 168 at 15:20, 20 at 15:29). So a
  next-week short would read "outside one straddle" and be held on any break.
- **Fix.**
  - S is the ATM straddle **of her option's own expiry**.
  - If the day's chain record does not carry that expiry: "could not check the reach", and the line
    folds (the draft's own item 4).
  - The same applies to the §A.6 / §F reach prints and to S8's R/S.

**M9 — W-R cannot see the tail it exists for.**

§C.4: *"The clause dies if **P_x > P_b on more than half of the held breaks**"*, and *"It dies if
**either** judged population fails it. That is conservative, because the risk is open-ended."*

- **A majority count is the statistic a writer's tail hides from.** Ten holds that each save 5 pts and
  one that costs 150 pass it.
- **The path is not logged either.** Only the two endpoints are logged, not the path while held, which
  is what her margin sees.
- **Fix.**
  - Keep the majority test.
  - **Add:** it dies if the **total** of (P_x − P_b) over held breaks is > 0, in premium points. That is
    a total, not a rate. Judge it per index, and pooled in units of S at the break, each also with the
    best day removed.
  - Log **P_max**, the highest premium between the break close and the fold, in `sell_hold` and the
    writer's `held`.
  - Print the single worst held break beside the verdict.

(M5 applies: §C.4's best-day sentence, and "her own seller doctrine".)

### Should-fix

- **S12 — Copy that implies safety.**
  - *"The market's own expected move to expiry does not reach it"* (§C.2) tells an open-ended short
    she is safe. The straddle is the expected **size** of the move, not a bound on it, and a strike just
    outside it is well within reach.
  - Say instead: "outside one ATM straddle ({S} pts [M], the market's price of the move to {expiry})".
- **S13 — W-R's key departs from its precedent.**
  - It adds `strike` to rev 5 §F.1's (index, bar, L), so two strikes at one break count twice. 09-24's
    74,100 and 74,200 were one break at 14:38, and §D.4 counts them as "two distinct held breaks".
  - Key it (index, bar, L, side), take the median across strikes as 7b does, and show the per-strike
    rows.
- **S14 — Say how 3r enters the writers' clause 7.** Is `fold_rule: "3r"` a rule-3 stamp for 7b-B and
  a FOLD stamp for §7 clause 1?
- **S15 — The safety claim covers held writers only.**
  - Under rev 4 / 5 today, a writer whose line lies beyond her strike can be in the money on HOLD,
    with no break.
  - The record has four such sales: the NIFTY 09-22 CE 23,450 legs, with the line 78–99 pts away and
    the strike 58–78 OTM (S10).
  - The draft does not make this worse. State it, and leave the remedy to her.
- **S16 — Say that rev 4 §1's principle changes.** Rev 4 §1 reads *"No candle of the premium is an
  input."* The window now folds on ATM premiums. List this as a change of that principle, not as "it
  holds".
- **S17 — Say what the rule is, where she signs.**
  - It binds only beyond one straddle. On the record that was two breaks, both SENSEX 0DTE after 14:38,
    held seven minutes each.
  - Off expiry, S was 250–600 pts on the two index-days checked. Even on SENSEX 09-24 (0DTE) it was
    330–364 from 13:26 to 14:30, and it fell to 168 only by 15:20.
  - Its domain is far-OTM sales in the expiry-day afternoon: the ground her band-rotation words set
    aside for the ATM straddle, and her setup S4 (the expiry flush) logs rather than trades.
  - While held, print PLAN §2.1's writer premium at risk from here to the reach-fold level (R − S
    away), so the held loss is on screen [I].

### Verdict C: **NOT YET**

- **M7 and M8** are holes in a rule that loosens a stop on an open-ended position.
- **M9** is a kill clause that cannot see what kills a writer.

With those three fixed and S12 taken, C is signable as a DRAFT rule she chooses knowing its domain
(S17). None needs a new number.

---

## The six questions

### Q1. Does the read speak when she has a trade, without being a coin flip? Is EITHER on ties honest?

**It speaks.**
- At her entries it named a leg at 25 of 29.
- The round-3 gate that silenced the last read is gone.

**It is close to a coin flip at its margin.**
- 49% of its BUY / SELL minutes were named by a single fact.
- Its median word lives two minutes.
- It flipped BUY ↔ SELL directly 365 times.
- The rev 0 → 0a change moved 4 of her 29 words through one fact.
- The count is printed, which is honest. But without a since-clock and without the stability counts,
  she cannot tell a 3–2 that has stood for 20 minutes from one that appeared this minute (M3).

**EITHER is honest in kind, but its sentence is wrong.** At 2–2 (639 of 805) the facts split; they do
not fail to separate (S2).

**The word to worry about is BUY at a tie.** 416 minutes read BUY only because SELL was refused. The
screen says so, which is honest; the falsifier pools them, which is not (M2).

### Q2. Are the five facts independent, or do some double-count trend or the same wall?

**No object is read twice.** The draft's "one wall, one fact" holds, and SHIELD and ROOM read opposite
walls.

**They are correlated by regime:**
- **A pin** votes SELL through both walls (908 against 514 if independent), and a third time through
  REGIME "no side".
- **A trend** votes BUY through SPEED and REGIME together (981 against 749).
- **Fact 5 and REGIME are both price-led,** but only mildly co-voting (+5% SELL, +14% BUY).

**The facts separate on a different line from the draft's.** By parity, the expression question is the
straddle's P&L, so the line's distance, shared by both legs, separates nothing. ROOM's FOR BUY on lines
inside the noise (871 minutes) is therefore a lean the fact should not carry (S1).

Disclose the co-occurrence (S5). No fact must go.

### Q3. Is the sell strike's placement usable by a real seller?

**Mostly yes.**
- At SELL words the sale sat a median **0.19 straddles** OTM (quartiles 0.10 / 0.19 / 0.35), with real
  premium:

  | index | sale premium, median | ATM leg, median |
  |---|---|---|
  | NIFTY | 59.5 | 89.2 |
  | SENSEX | 183.5 | 237.0 |
  | BANKNIFTY | 331.0 | 335.4 |

- A near wall makes the sale an ATM short with the same Δ as the buy, which is the cleanest comparison
  there is.

**The far cases are rarer, and they are expiry afternoons.**
- 63 of the 1,734 SELL minutes were beyond one straddle: SENSEX 45, NIFTY 18, BANKNIFTY 0.
- The draft's 186–564 pts come from one SENSEX 0DTE afternoon. That is setup-S4 ground (the expiry flush), where a far sale
  expresses "no crash", not "up".

**Margin.** At her scale margin is not the constraint, but a far sale's premium per lot is small
against a similar margin.

**Do not refuse on it (unregistered).** Print R/S and Δ beside the sale, and the setup-S4 row on 0DTE (S8).
Make the comparison unit moneyness-proof (M1).

### Q4. Is the writer hold safe and useful? What would a signable one look like?

**Safe? Not as written.**
- Unsigned R can hold her in the money (M7).
- S can be the wrong expiry's straddle (M8).
- The kill clause counts heads, not money (M9).
- The copy implies "it won't reach" (S12).

**Useful? Barely, by construction.**
- Off expiry the straddle was 250–600 pts on the index-days checked, so the line decides exactly as
  today.
- On expiry afternoons it holds far-OTM shorts through swing breaks.
- It does not fold on noise; rev 5 B's buffer already does that job for every trade.

**A signable writer hold, with no new number:**
- the reach as written, with R signed, and a close at or through the strike always folding;
- S as the ATM straddle of her option's own expiry, else FOLD;
- the held loss printed as PLAN §2.1's writer premium at risk to the reach-fold level;
- W-R killing on the total premium cost and on the majority, both with the best day removed, with the
  worst hold and P_max shown;
- copy that never implies "won't reach";
- her explicit yes that it applies on expiry day, which her own words set aside for the straddle.

### Q5. Is every outcome and falsifier computable from the named logs, and do they answer the question?

**Computable, yes, with the owed key change.**
- `expr_<day>` carries p0, p30, mfe, mae and `sell_hold`.
- `check_<day>` carries the writer presses and outcomes.
- `hold_<day>` carries reach, held and 3r.
- §C.4's population (ii) needs the window re-run for a synthetic short from each unit. The close-time
  import can do that.
- **A note on cost:** the backfill runs 375 × 2 × 3 expressions per day, each with two window reads
  (the drafter's run took about 2 minutes for 6,750). It must never run inside a request path; the
  09-18 wedge is the precedent.

**Answering the question, no:**
- G does not measure which expression paid (M1).
- BUY pools two kinds (M2).
- UP and DOWN units are mirror pairs, and the reduced check never tests DOWN (S4).
- P1-W is out of reach (M6).
- W-R lacks P_max (M9).

### Q6. Anything that changes an existing signed rule without saying so?

**Not said, or said too narrowly:**
- **VALIDATE rev 2** §2, §3 (writer outcome rows, and the outcome key gaining `role`) and §4 are
  amended; the header names only §1.6 (S9).
- **Rev 4 §1's "no candle of the premium is an input"** changes for the window, and the draft says it
  "holds" (S16).
- **How 3r enters the writers' clause 7** is not said (S14).
- **W-R's key departs from rev 5 §F.1's** without saying so (S13).
- **After the rev 0a fingerprint**, three edits to the draft's own rules were made and not logged. They
  are not signed rules, but they are the same hygiene (M5).

**Said correctly:**
- the writer clocks reset and the buyer clocks continue;
- PLAN §2.6's reach line needs a change-log entry and a new §1f hash;
- rev 5 option B stays the writers' fallback if W-R dies.

**No buyer rule moves.** Verified against the VALIDATE rev 2 fields and `hold_log.key`.

---

## Summary

| part | verdict | must-fix |
|---|---|---|
| A — the expression | **NOT YET** | M1 the outcome unit · M2 the refusal-named words pooled · M3 stability undisclosed, no since-clock · M4 R4 fails open · M5 disclosure and attribution |
| B — the writer in VALIDATE | **NOT YET** | M6 P1-W / P2-W unreachable: add the grid population, fix the horizon now · M5 |
| C — the reach | **NOT YET** | M7 unsigned R holds her in the money · M8 S from the wrong expiry · M9 W-R blind to the tail · M5 |

**No new number is needed for any fix.** Each is a definition, a population, a sign, an expiry or a
disclosure.
