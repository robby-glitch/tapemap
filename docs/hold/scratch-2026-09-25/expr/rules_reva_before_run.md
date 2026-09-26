# PRE-REGISTRATION DRAFT — THE EXPRESSION: BUY THE OPTION, OR SELL THE OTHER SIDE; THE SELLER IN VALIDATE; THE SELLER IN THE WINDOW — REVISION a (rev 0 written 2026-09-26 00:16 IST; rev a written 01:25 IST by the clock, before its run; NOT SIGNED, UNTESTED)

**Status.** This is a DRAFT. Nothing below is a result. Nothing here is in force until Mary signs it.

**The record of how it got here:**
- **Rev 0 (00:16) and rev 0a (00:32)** were each fingerprinted before their run. Rev 0a changed fact 5 after rev 0's run. The
  history is in §G.
- **Rev a (01:25)** answers the adversarial review `docs/hold/EXPRESSION-REVIEW.md` (01:11), whose verdict was **NOT YET on
  A, B and C**.
- **Rev a's text of §A–§C, §E and §F was fingerprinted before its disclosure run** (§D.0). §D was written after that run.
- §G lists every edit to the rules made after a fingerprint, including the three that rev 0a left out (review M5).

**Decisions taken as the trader.** Where the review left a choice, these were decided on her standing delegation and
conveyed by the coordinator on 2026-09-26. Her words: *"Think yourself as the trader and you are building the for youself"*.
- the word is read on the 3-minute close (M3);
- the outcome is in R-multiples (M1);
- an unreadable straddle refuses SELL (M4);
- the signed reach, and a close at or through the strike always folds (M7);
- her option's own expiry, else FOLD (M8);
- the kill clause judges total and majority (M9);
- the grid writer population and its horizon (M6);
- the refusal split (M2);
- the far-strike rule (Q3).

**One decision is left to her, and asked as one yes/no question in §C.7:** does the reach apply on expiry day?

**What it amends, and what it leaves alone** (review S9, S16):
- It **adds** THE EXPRESSION (§A) to the Validate tab and to a new forward log.
- It **amends VALIDATE rev 2** for writers only (§B):
  - **§1.6** (a writer gets a word);
  - **§2** (the word was "for a buyer");
  - **§3** (writer press rows and outcome rows; the outcome key gains `role`);
  - **§4** (it was "buyers only"; two writer populations are added).
  Buyer facts, words, outcomes and rows do not move.
- It **amends the window for writers only** (§C):
  - **rev 4 §2 / §3 rule 3**, with the reach, rule 3r and rule 3s;
  - **rev 4 §1's principle "no candle of the premium is an input"**, which now **changes for writers**: the window reads
    the ATM straddle's premiums to decide a writer's fold;
  - **rev 4 §7 / rev 5 §F**, for how 3r and 3s stamp (§C.5), and W-R's unit (§C.4).
- It **amends PLAN §2.6's display:** a writer's STOP adds the reach line and the held loss.
- **Buyers are untouched.** No buyer rule of the window (rev 4 + rev 5 B), THE PLAN (rev 3a) or VALIDATE (rev 2) moves.
  Buyer clocks do not restart (§E.4).

**Her words, 2026-09-25:**
> "i buy and sell option as per the market condition if its better to sell options than i will sell options with out any
> worry . so has to both ways so if any trade pops up engine should be able to tell me weather to buy any option make sense
> or selling the otherside because let say market is going up either i can go for call buy but it engine things its better
> to sell the put at this location than i would sell option . . So this engine has to be good in that too . Think yourself
> as the trader and you are building the for youself"

And, 2026-09-24: *"identifying direction is never my problem but holding a trade is"*.

**Quotes and attribution (review M5e).** Only text in quotation marks with "her words" is hers, verbatim. Everything else is
named by source:
- **the band-rotation spec** (`docs/superpowers/specs/2026-07-31-operator-band-rotation-setup.md`): its prose was written
  from her answers, and it quotes her separately;
- **the seller-desk design** (`seller-desk-doctrine`): the design Fable and Opus converged on in an exercise she ordered on
  2026-08-25, adopted into her desk. It is not her words;
- **the desk's setup table** (`two-regimes-and-setups`: S1–S5 and the regime → game map): design notes, not her words;
- **the operator thesis** (`operator-thesis`): the stack's design notes, not her words;
- **her profile** (the assistant's memory of her system): a description, not her words.

**The question this answers is narrow.** Direction is hers. Given her direction at a 3-minute close, the read answers: **which
leg expresses it: buy the option in the direction, sell the option on the other side, either, or neither.** It is not a
second VALIDATE (each leg keeps its own VALIDATE word), and it does not re-decide direction.

**What had been seen when rev a was written:** everything listed for rev 0 (the signed texts, the reviews, the "better
trade" reads, the modules), plus:
- rev 0 and rev 0a's own runs (§G, and the scratch outputs);
- the adversarial review and every number in it.

**Rev a's new rules were written after those numbers were read.** Each change is logged in §G with its reason, and none was
run before its fingerprint.

---

## A. THE EXPRESSION READ

### A.1 The question, and why it speaks

Given a direction `d` (UP or DOWN), the read compares two legs:
- **LONG** the option in the direction: CE for UP, PE for DOWN;
- **SHORT** the option on the other side: PE for UP, CE for DOWN.

**The two legs share one thesis.** In rev 4 §1's table a long CE and a short PE have the same `d` (+1), as do a long PE and
a short CE (−1). They have the same line, the same payers and the same holders. They differ in four places:
- **speed.** A buyer rents the move and needs it fast (the drag number). A writer needs only its absence.
- **risk shape.** A buyer's loss stops at the premium. A writer's is open-ended, so she needs a wall behind her strike.
- **what a range does.** A range taxes a buyer and pays a writer (the desk's two-regimes table: "confirmed pin → sell").
- **which rent is winning.** By put–call parity (CE − PE = F − K, discounted), a long CE's P&L minus a short PE's P&L at one
  strike **is** a long straddle's P&L, with direction cancelled exactly. So "did buying beat selling" is "did the straddle
  gain" (review S6).

**The read counts facts that answer those four differences, and only those.** Facts that hurt both legs alike (flow
against, trend against, a broken thesis) are carried by each leg's own entry check (§A.3).

**Why it speaks where the "better trade" reads did not:**
- nothing gates it except each leg's own refusals;
- the price rows are one counted fact;
- the question is relative, so a tie is a word (EITHER).

**It is silent (STAND ASIDE, or "could not check") only when:**
- both legs are refused by their own rules; or
- a refused leg has more facts for it than the leg that is not refused.

§D gives the counts. They are a disclosure, not a target.

### A.2 When it is read: the 3-minute close (review M3)

The word is read **at each close of the 09:15 3-minute grid**: the 125 closes at 09:17, 09:20 … 15:29, which are rev 5
A.0.1's grid. Every input is cut to that close's minute.
- **It stands until the next close.**
- **Under it:** "since HH:MM · was {word} until HH:MM", as rev 4 §5 prints the window's since-clock.
- **Why the 3-minute close:** it is the house's canonical bar (CLAUDE.md rule 3), the candle of her chart (rev 5 A.0.1), and
  the grid the window's own line now breaks on. Read every minute, rev 0a's word lived a median two minutes (review M3),
  which is not a word she can act on. §D.2 discloses the flip counts under both cadences.
- **A due close whose candle has not landed:** "could not check — the {bar} close has not landed", until a close is read.
- **A late close** is read when its candle lands (rev 5 A.0.4, `read_at`), never back-dated.
- **A VALIDATE press between closes** shows the word of the last close, labelled "read at the HH:MM close". The legs'
  premiums are printed at the press minute [I], with their minute.
  - Each leg's own VALIDATE word is read at the press minute, by VALIDATE's own rule, which is unchanged.
  - So the tab can show an expression word one or two minutes older than the VALIDATE words beside it, and it says so.

### A.3 The five facts, each FOR BUY · FOR SELL · NEITHER

Each fact is tagged [M] or [I].
- A NEITHER that is an absence carries its kind: "checked, none", "could not check" or "not shown". A NEITHER that is a
  read says what was read.
- The count is "n for buy · n for sell · n neither — of 5, a count, not odds".
- The count is not independent evidence. The facts co-vote by regime: a pin can give up to three SELL votes, and a trend two
  BUY votes. §D.5 shows the co-occurrence.

| # | fact | FOR BUY | FOR SELL | NEITHER |
|---|---|---|---|---|
| 1 | **SPEED**: is anyone being forced your way right now? | the window's "paid" at `t` (rev 4 §3 rule 5; VALIDATE rev 2 §1.4) | — | nothing paying (*checked, none*) · OI blind (*could not check*) |
| 2 | **ROOM**: the next wall that holds, against your line, in VALIDATE §1.3's own order | the line outside one candle, and the target at least as far as the line, or no target | the line outside one candle, and the target nearer than the line | **the line inside one candle** (a read: "the reward comparison is not read") · line, noise or walls unreadable (*could not check*) |
| 3 | **SHIELD**: is the wall behind the sale defended? | — | that wall is BUILDING with a build today | STALLED or UNWINDING (a read) · no such wall, or OI blind (also a refusal) |
| 4 | **REGIME**: the price rows, the side read (rev 4 §10.1) | the side read names your direction's side | "no side" | the other side (a read) · a row forming (*could not check*) |
| 5 | **PREMIUM**: whose rent won over the last 15 minutes, on one fixed straddle | the straddle rose (the move out-paid time) | the straddle fell (time won) | both legs rose (a read; refuses SELL) · unchanged (a read) · unreadable (*could not check*; refuses SELL) |

**Max four each way.** SPEED is buy-only and SHIELD is sell-only; the other three are two-sided.

**1 SPEED [M on I].** This is VALIDATE rev 2 §1.4's "Paying", read for the long leg: the window's own quiet-clock "paid" at
`t`. That means any one of:
- the payers' nearer front is UNWINDING (not both leaving);
- a payers'-side fold is live (rev 5 §C keeps a live fold as paid for the clock);
- flow is with you by the strict rule.

*Why it favours buying:* a forced move is a fast move, and speed is what beats the rent. A writer is paid whether the move is
fast or absent.

*Why no sell state:* payers adding in the way is ROOM's wall, so counting it here would count it twice.

**2 ROOM [M], in VALIDATE rev 2 §1.3's own order** (rev a, review S1). The line is |close − L| (rev 5's L itself), unrounded.
The noise is `hold.noise`. The target is PLAN's rung with every GIVING WAY wall removed: the nearest sized payers'-side front
beyond the index that is DEFENDED or STALLED; else the session extreme beyond; else none.
1. line blind, or noise unreadable: NEITHER, could not check;
2. **line ≤ noise: NEITHER, a read.** "Your line is inside one candle's range — the reward comparison is not read". A tie is
   inside;
3. walls unreadable: NEITHER, could not check;
4. target < line: FOR SELL. "The move is capped at {k}, {r} pts away, nearer than your line at {s}; a buyer's reward is
   shorter than her risk, and a writer does not need the move";
5. otherwise, including no target: FOR BUY ("room to run"). A tie is FOR BUY, as VALIDATE's tie is WITH.

*One wall, one fact.* A giving-way wall is SPEED's wall, and ROOM's target removes it, so no strike is read twice.

*Why the noise step is back:* the line is shared by both legs, so the noise separates neither leg and is not counted as a
fact. But comparing a target with a line that one candle will reach is a comparison VALIDATE's own order never makes.

**3 SHIELD [M].** It reads **the wall behind the sale**: the nearest to spot of the sold side's §1d top two (`fronts.read`,
the running peak) that sits **at or beyond spot** on the sold option's out-of-the-money side. "At" is within half a strike
step.
- That wall is FOR SELL when it reads BUILDING with a build today (`built`).
- *Why:* her words set the reading, *"always check which side stops first increasing their positions and then unwinding"*.
  That the side still adding is the side not being forced, and that a new sale joins it, is **this draft's** inference.
- *Why not the window's nearer front:* the nearer front can sit behind price (in the money for the sold option).

**4 REGIME [I].** This is rev 4 §10.1's side vote on the 5m / 15m / 1h rows:
- the named side is your direction's: FOR BUY ("a trend pays a buyer's gamma; a writer's best case is the premium she sold");
- "no side": FOR SELL ("the rows read range; time pays a writer while a buyer pays rent waiting");
- the other side: NEITHER, a read.

It is price-led and counted, not gated (both round-3 reads' proposed variant, and §10's own rule). Its known cost is the lag
at turns (rev 4 §10.5). The board's REGIME word (price AND OI) is **printed, not counted**: it would count these rows and the
fronts a second time, and it is the gate that went silent.

**5 PREMIUM [M] (rev 0a's fact; changed after the first run, §G).** It reads **one straddle, fixed for the window**: the CE
and PE of the strike that was ATM at `t − 15` (spot at `t − 15` rounded to the step), at `t − 15` and at `t`, from the chain
record's minute closes. One contract, never re-centred (rev 4 §8).
- **both legs rose:** NEITHER, a read, and **R4 refuses SELL** ("the straddle is being bid on both legs").
- **otherwise the straddle rose:** FOR BUY. "A straddle bought at {t−15} is up {x} pts [M]: the move paid more than time
  took — the index moved {m} pts {with / against} your direction [M]".
- **the straddle fell:** FOR SELL. "A straddle sold at {t−15} is up {x} pts [M]: time took more than the move paid — the
  index moved {m} pts {with / against} your direction [M]".
- **unchanged:** NEITHER, a read.
- **a premium missing, or `t − 15` before 09:15:** NEITHER, could not check, and **R4 refuses SELL** (§A.4).

*Why the sentence names the move's sign* (review S6): the straddle is direction-free. On 1,144 of rev 0a's 2,288 FOR BUY
minutes the move had gone **against** her direction. "BUY CE — the move out-paid time" after a fall would otherwise read as
momentum.

*Why a straddle:* by parity (§A.1) it is the one fact that reads the expression question directly. A long ATM straddle gains
exactly when the realised move beats the decay.
- The band-rotation spec's prose names the other state, *"both legs decaying together, which is just theta on a dead day"*.
  That is the spec's sentence, not a quote of hers.
- Her own words make the ATM straddle the anchor of that setup: *"yeah straddle is about right because they almost forms
  mirror charts"*.
- **They also set an expiry exception:** *"since today was sensex expiry so that why otherwise atm straddle is ideal"*.

*Why the strike is fixed at `t − 15`:* a straddle is cheapest at the money. So a strike chosen at `t` would bias the change
toward "fell".

*Why 15:* `QUIET` = `fronts.SLOPE_MARKS` = 15.

*Why not the drag number:* drag and this fact measure the same contest, so counting both would count it twice. Drag reads one
leg anchored at the open's strike and is silent until the index has moved. It is **printed** (§A.7).

### A.4 The refusals, each leg's own, and the word

**BUY is refused when:**
- **R5.** The long leg's entry check reads FOLD at `t` (rev 4 §3): "you would enter a broken setup".

**SELL is refused when any one holds:**
- **R1.** The short leg's entry check reads FOLD at `t` (rule 4 or 6 with rev 4 §4's writer clauses).
- **R2.** **Your side is leaving under a squeeze.** The window's YOUR SIDE row for the short leg reads AGAINST: her own
  side's nearer front UNWINDING, held 3 minutes, while spot moves toward her strike (rev 4 §4). "Never sell into a squeeze".
  The operator thesis, which is design notes, puts it this way: a writer's forced buy-back is the cascade's fuel.
- **R3.** **OI is blind**: fronts forming, the grid stale, or fronts not read. "A writer does not sell a wall she cannot
  see."
- **R4 (rev a: fails closed; review M4).** Fact 5 reads **both legs rose**, **or fact 5 could not check**, **or the ATM
  straddle at `t` of the sale's expiry cannot be read** (§A.5 needs it).
  - "Never sell into a bid straddle, and never sell one you cannot see": "R4 — could not check: {why}".
  - This is §C.2's own principle: an unread safety input fails closed.
- **R6.** **No wall behind the sale:** none of the sold side's top two sits at or beyond spot. "The {floor} is already behind
  price."

**The word**, in this order, with `b` and `s` the FOR BUY and FOR SELL counts:
1. **could not check** when the line cannot be set at the close (no index candle, or the close not landed);
2. **both refused: STAND ASIDE · both refused**, naming each refusal;
3. **only SELL refused:**
   - `b ≥ s`: **BUY {CE|PE} · selling refused**, with the codes (e.g. "BUY CE — selling refused (R4 — could not check: no
     premium at 09:20); 1 for buy · 1 for sell");
   - otherwise: **STAND ASIDE · led**: "the facts favour selling, {s} to {b}, but selling is refused: {why}";
4. **only BUY refused:**
   - `s ≥ b`: **SELL {PE|CE} · buying refused**;
   - otherwise: **STAND ASIDE · led**, mirrored;
5. **neither refused (on the count):**
   - **BUY** if `b > s`;
   - **SELL** if `s > b`;
   - **EITHER** if `b = s`: "EITHER — the facts split {b}–{s}" (review S2). At 0–0 it reads "nothing separates them".

**The split is kept everywhere** (review M2): on screen, in the log (`named_by: "count" | "refusal"`, `refusal: [codes]`) and in
the falsifiers (§E.2).
- A word named because the other leg is refused is **never** dressed as, pooled with, or judged as a word on the count.
- *Why:* a word on the count compares two live legs. A word by refusal had one leg that was never an alternative, so it
  tests the refusal, not the facts.

**Named choices, none of them a number:**
- a leg is refused by its own rules, not outvoted;
- a refused leg's majority makes STAND ASIDE, never a vote for the other leg;
- a tie is EITHER;
- the word is read at the 3-minute close.

### A.5 Which strike, and which expiry, each leg is

**Both legs are the chain record's resolved expiry for that index** (`upstox_instruments.resolve`, the nearest live one),
named on screen: "expiry {date}, {n} days" or "0DTE" (review S8). The facts are strike-free, so the strike is a print, not an
input.

**BUY: the ATM strike** (spot rounded to the step; the side log's `atm.k`). Her words: *"i often trade itm or atm so which
option i m holding hardly matters"*. It is printed "ATM {k}; one strike ITM reads the same facts".

**SELL (rev a, coordinator Q3):**
1. **At the wall behind the sale** (fact 3's wall), when that wall lies **within one ATM straddle** of spot. That is its
   signed out-of-the-money distance r_w ≤ S, with S the ATM straddle of the same expiry at `t`.
2. **When the wall lies beyond one straddle** (r_w > S): **at the money.** That is the nearest strike to spot on the sold
   side, and the defended wall still stands behind it, farther out.
   - The print: "SELL PE {k} (ATM) — the defended floor {kw} sits {r_w} pts out, beyond one ATM straddle ({S} pts [M]); a sale
     at the floor would be {r_w/S:.1f} straddles out".
3. **S unreadable:** SELL is refused (R4).
4. **No wall:** "not shown" (R6).

*Why the rule, inherited:*
- **one ATM straddle** is §C's reach unit (the market's price of the move to that expiry). A strike one straddle out sits
  near 0.2 delta under the usual lognormal reading [I] (the review's independent check). That is the seller-desk design's
  first delta lamp.
- **ATM** is the side log's `atm.k`. At the money the sale has the buy's Δ, and by parity the comparison is exactly the
  straddle's (§A.1).
- **Any strike between ATM and a far wall would be an invented placement.**
- A sale at a wall beyond one straddle expresses "no crash", not her direction (review Q3). The far cases on her days were
  expiry afternoons.

**Printed beside the sale** (review S8):
- its distance in straddles of its own expiry (r/S);
- its Δ [M];
- the wall's strike and state;
- the line's position against the strike;
- **on 0DTE**, one row from the desk's setup table (design notes, not a rule here): *"S4 expiry flush — logged, not traded ·
  expiry afternoon → neither"*. It is printed, and it never refuses.

**Each leg's premium** is printed with its minute [I]. There is no size, no order path and no "book".

### A.6 When it is read, and where

- At each 3-minute close, per index, for both directions, in the forward log (§E.3).
- On every VALIDATE press: the last close's word, for the direction of the leg she pressed (long CE and short PE are UP; long
  PE and short CE are DOWN).
- When her zone setup names a direction on its closed bar. This is display only, and it pre-fills nothing.

### A.7 Printed with it, not counted

- **The drag number** (`/api/drag`): "today a correct buyer was paid {paid} of {owed} owed since {anchor} [M]".
- **The expiry line** (rev 4 §10.3), with each leg's expiry named. On 0DTE it adds: "theta is fastest and gamma largest
  today: the first pays a writer, the second hunts her; §B and §C read both".
- **The board's REGIME,** both halves.
- **Each leg's VALIDATE word:** the buyer's rev 2 word, and the writer's (§B).
- **For the sell leg:** R/S of its own expiry, Δ, and on 0DTE the setup-table row (§A.5).
- "Not shown — a size", "not shown — an order", "not shown — odds: the count is a count".

### A.8 Hazards recorded now

- **REGIME lags at turns** by 10–60 minutes (rev 4 §10.5).
- **ROOM still reads FOR BUY** whenever no holding wall is in the way and the line is outside one candle (VALIDATE's own
  target rule).
- **The word is close to a coin flip at its margin.** Many words are named by one fact (§D.2). The count and the since-clock
  are printed so she can see a 3–2 that is new from one that has stood.
- **SELL is refused whenever OI is blind or the straddle cannot be read.** The straddle needs `t − 15`, so SELL is refused
  in every session until about 09:30 (R3 and R4). Those closes can read only BUY or STAND ASIDE.
- **BANKNIFTY** trends and inverts reversion tests (research-findings §3). The index is printed beside the word.
- **The dead list, so nobody conflates:** "selling any upper band" (research-findings §2) is a directional **index** fade.
  SELL here is short premium on the side opposite her direction. It revives nothing.

---

## B. THE SELLER IN VALIDATE (amends VALIDATE rev 2 §1.6, §2, §3 and §4, for writers only)

A SELL press gets **GO / WAIT / NO** from four writer facts. The buyer's word, facts, outcome, key and record do not move.

### B.1 The writer's four facts, each WITH · AGAINST · NEITHER

| # | fact | WITH | AGAINST | NEITHER |
|---|---|---|---|---|
| 1 | **Right now**: the window's entry check for the short leg | HOLD | FOLD, which makes the word NO | WATCH (a read) · PATA NAHI (*could not check*) |
| 2 | **Your wall**: the wall between spot and your strike | a front of your side at or between spot and your strike, BUILDING with a build | — | none there, or not building (a read) · OI blind (*could not check*) |
| 3 | **Cushion**: the danger line against the noise, and what the line costs against what you collect | line > one candle's noise **and** P ≥ X | line ≤ noise **or** X > P | line blind, noise unreadable, no greeks, **or the line beyond your strike** (*could not check*) |
| 4 | **Time is paying**: the fixed straddle (§A.3 fact 5) | the straddle fell | both legs rose | the straddle rose by a move, or unchanged (a read) · unreadable (*could not check*) |

**1 Right now.** The buyer's object (VALIDATE §1.2), read for the short leg, with rev 4 §4's writer clauses. Rule 3 cannot
fire at entry (M5), so §C does not touch it.

**2 Your wall [M].** Your side's §1d top two, the nearest to spot of those at or between spot and your strike (inclusive, half
a step): BUILDING with a build, WITH; else NEITHER, a read. It has no AGAINST: a squeeze is inside Right now, as VALIDATE §1.4
keeps payers and flow inside Right now.

**3 Cushion [M and I]**, in VALIDATE §1.3's order:
1. line or noise unreadable: could not check;
2. line ≤ noise: AGAINST ("your danger line is {s} pts away — inside one candle's range");
3. **the line lies at or beyond your strike** (line distance ≥ your strike's signed OTM distance from spot): could not
   check, "your line is beyond your strike — the formula does not reach" (rev a, review S10). A second-order expansion over a
   distance past the strike is outside its range;
4. no greeks for your strike and expiry: could not check;
5. X > P: AGAINST ("your line is worth {X} of premium [I]; you collect {P} [M]"). X is PLAN §2.1's writer formula,
   |Δ|·R + ½·Γ·R², with R the unrounded line distance and the broker's Δ, Γ [M];
6. otherwise: WITH.

*The +½Γ term is where 0DTE enters*: a near line on an expiry afternoon reads AGAINST where the same line on a Monday would
not.

**4 Time is paying [M].** Fact 5 of §A, read once:
- the straddle fell: WITH;
- both legs rose: AGAINST;
- the straddle rose by a move: NEITHER ("the move out-paid time for 15 minutes: selling pays only if it stops").

### B.2 The word, for a writer (amends VALIDATE §2, which read "for a buyer")

VALIDATE rev 2 §2's rule, inherited:
- **NO:** Right now is AGAINST.
- **GO:** Right now is HOLD, no fact is AGAINST, and at most one is NEITHER.
- **WAIT:** everything else, naming what would have to change, or what is not there yet.

It is printed "{w} with · {a} against · {n} neither — of 4, a count, not odds".

**Printed, not counted:**
- **Your setup** (VALIDATE §1.1, read with the writer's `d`). *Why not counted:* direction is hers; this word is about
  surviving the sale. Counting it would also let the zone SELL machine (u2) vote for every short CE, and fading the upper band
  is on the dead list.
- **Your option's σ against its own session VWAP.** *Why not counted:* it has no registered direction for a writer, and fact 4
  reads whether time is winning without that ambiguity.
- The expiry line; the reach (§C); X [I]; the drag number.

### B.3 The writer's outcome, its populations and its judgement (amends VALIDATE §3 and §4)

**The outcome.** It is the geometry the word read, frozen at the check minute:
- **target:** your option's per-minute premium (the chain record's minute close [M]) falls to **P − X** or below. The
  premium decayed by as much as the line would have cost, before the line was touched. That is 1:1 in premium.
  - *Attribution:* *"1:1 atleast"* is hers, **about a buyer's band-to-band exit** (band-rotation spec). Applying 1:1 to a
    writer's decay is this draft's choice.
- **stop:** the index's 1-minute high (a short CE) or low (a short PE) reaches the static L at the check.
- **`first`:** `target`, `stop`, `same minute`, or `neither`.
- **Not scored**, each shown with its reason: no greeks; the line not set; the line beyond the strike; X > P ("checked,
  none — no target below zero").
- `short` and `gaps` as VALIDATE §3.
- It reads no break rule, no trail and no reach.
- *Known asymmetry:* the stop end reads the index's range, and the target end reads the premium's close. That favours `stop`,
  the conservative direction for judging GO.

**The horizon, fixed now** (review M6; coordinator item 6):
- **30 finished minutes, judged.** It is inherited: VALIDATE §3 and rev 4 §7's horizon. On the grid (population ii) the
  units are 30 minutes apart, so no two judged windows overlap, which is VALIDATE's own reason for 30. A longer judged
  horizon would overlap the grid's units, and the judgement would then count one afternoon many times.
- **To 15:29, shown, never judged,** beside each row: "and to the close: {first}". Time pays a writer, so the session is
  her natural horizon. It is shown so the short window's blind spot stays visible.
- **What the 30-minute test mostly tests** (review S11): off expiry, 30 minutes of decay is small. So "premium falls by X
  before L" mostly means the index moved about R away, which is a direction test. On expiry afternoons decay does most of
  the work. The rows are split by 0DTE / not.

**Two populations, never pooled, each judged on its own count** (review M6):
- **(i) her writer presses:** the first writer press per (index, `d`) per 30 minutes, whatever its word (VALIDATE §3's
  unit). Her record so far has no writer presses: all 29 of her trades were long.
- **(ii) the grid writer population:** at every expression unit (§E.2), the writer word (§B.1–B.2) on the expression's
  SELL leg (its strike and expiry, §A.5), with the same outcome. The word is logged whatever the expression said, and the
  population is judged on its own count. It exists so the writer word can reach its counts without her having to sell.

**The judgement** is VALIDATE rev 2 §4's form, per population:
- **the stratum:** the writer's Cushion WITH geometry (line > noise, the line inside the strike, P ≥ X), identical for GO,
  WAIT and NO;
- **P1-W:** GO(target)·WAIT(stop) > WAIT(target)·GO(stop);
- **P2-W:** NO less often, the same way;
- **when:** each at ≥ 15 resolved units of its word and ≥ 15 resolved WAIT units in the stratum, and ≥ 10 sessions; by 30
  sessions;
- the best day removed (rev 5 §F.2);
- co-timed sets reduced;
- the rows split 0DTE / not, and UP / DOWN, shown.

**If P1-W fails** in either population (or reverses without the best day), the writer's word is deleted, and the facts stay as
a checklist. **If P2-W fails,** a writer's NO is withdrawn. Short of 15 by 30 sessions, it is inconclusive and DRAFT. WAIT is
the control.

**The owed key change** (amends VALIDATE §3): `hold_log.key` for an outcome row becomes `(idx, t, d, role, "outcome")`, with
role defaulting to "long" for existing rows.
- A long CE and a short PE share `d`, so without it they collide.
- `_hold_tick`'s `has()` check must change with it.
- Tests are owed.

---

## C. THE SELLER IN THE WINDOW: THE REACH (amends rule 3 for writers only)

### C.1 Why, and what it is where she signs (review S17)

**On 09-24 the window folded 11 sold calls at 14:38**, by rule 3, on the bounce off the 14:24 low. Every one ended at 0.1–0.2.

**The line is a buyer's structure.** A writer is short an option. Her danger is her strike being reached, and her loss is
open-ended. So for a writer, a swing break matters by how near it brings price to her strike, against **the market's own
price of the move to her option's expiry: the ATM straddle of that expiry.**
- The unit "strike distance in σ of the straddle" is from the **seller-desk design** (Fable and Opus, 2026-08-25, adopted into
  her desk), not her words.
- **Her own words set the ATM straddle aside on expiry day:** *"since today was sensex expiry so that why otherwise atm
  straddle is ideal"*. §C.7 asks her about that directly.

**What the rule is, plainly:**
- **It binds only when her strike is farther than one straddle out.** Off expiry, S was 250–600 pts on the index-days the
  review checked, so nearly every sale sits inside it and the line decides exactly as today.
- **Its domain is far-out-of-the-money sales on an expiry afternoon.** On the record that was two breaks, both SENSEX 09-24
  after 14:38, held seven minutes each.
- **Rule 3s adds one hard stop for every writer, always:** a 3-minute close at or through her strike folds her.

### C.2 The rule

At each 3-minute close, for a **writer**, read two numbers [M]:
- **R**, signed (review M7): the distance from the close to her strike **on the strike's OTM side**. That is k − close for a
  short CE, and close − k for a short PE. R ≤ 0 means the close is at or through her strike.
- **S** (review M8): **the ATM straddle of her option's own expiry** at that close's minute, the ATM CE plus the ATM PE of
  that expiry. When the day's chain record does not carry her option's expiry, or does not price its ATM pair that minute,
  **S is unreadable**.

Then, in order:
1. **Rule 3s — the strike, always** (coordinator item 4). At any close, broken line or not, held or not: **R ≤ 0 → FOLD,
   rule 3s**. "{IDX} closed {|R|} pts through your strike {k} [M]". A sale made in the money folds at its first close, and
   the entry check says so at entry.
2. **At a close that rule 3 reads as a break** (rev 5 option B):
   - S unreadable: **FOLD, rule 3** ("could not check the reach: {why} — the line decides");
   - R ≤ S: **FOLD, rule 3**, as today, adding "your strike is {R} pts out, inside one ATM straddle ({S} pts [M], the
     market's price of the move to {expiry})";
   - R > S: **held.** The word is **WATCH**, tag **LINE BROKEN · HELD**:
     > "The line broke at the {bar} close ({by} pts past {L}). Your strike is {R} pts out, outside one ATM straddle ({S} pts
     > [M], the market's price of the move to {expiry}). ≈ ₹{Y} [I] of premium between here and the fold level. FOLD at the
     > first 3-min close with your strike within one straddle, or at or through your strike."
3. **While held, every later close re-reads R and S:**
   - R ≤ S, or S unreadable: **FOLD, rule 3r ("the reach")**, stamped at its `read_at`;
   - a heal (rev 5 A.0.6: a close back on her side of the L that broke) ends the held state, and a later break is read by
     this rule again.
4. **Unchanged:** rules 4 and 6 (they fold a held writer at once), the latch, PATA NAHI on a due close not landed, and no quiet
   clock.

**The held loss [I], printed every minute while held** (review S17, M7). It is PLAN §2.1's writer premium at risk from here
to the fold level: |Δ|·(R − S) + ½·Γ·(R − S)² × qty, on the broker's Δ, Γ for her strike [M]. It is labelled "≈ ₹{Y} [I] of
premium between here and the fold level". It is an estimate, and is never "at risk if", never "safe", never "won't reach".

**Copy that implies safety is not allowed** (review S12). The straddle is the market's price of the move, not a bound on it.
A strike just outside it is well within reach. Every sentence names S as "the market's price of the move to {expiry}".

**The expiry-day switch** is her answer to §C.7. Until she answers, §C cannot be signed.

### C.3 What closes the FOMO trap, and what it cannot close

- **Decay is inside S.** The straddle shrinks with time, so on an expiry afternoon the same strike becomes farther in
  straddles.
- **The trap is closed from three sides:**
  - price toward her strike shrinks R;
  - a bid straddle (vol expanding) grows S;
  - a close at or through her strike folds her whatever S says (3s).
- **What it cannot close:** only closes are read (rev 5's grid). One 3-minute bar can carry price through her strike and
  back inside the bar. On an expiry afternoon a single bar can be as wide as the straddle: SENSEX 09-24 at 15:29 had S 20.05
  against a 139.3-pt bar (review M7). The held loss and P_max (§C.4) are printed and logged for that reason.
- **The principle that changes** (review S16): rev 4 §1's "no candle of the premium is an input" no longer holds for
  writers.
  - The window now reads the ATM straddle's premiums to decide a writer's fold.
  - Her own option's premium is still not an input to the word. Its greeks enter only the printed held loss.

### C.4 Its kill clause, W-R, forward rows only (review M9, S13)

**The unit** is a **held break**: a writer's first line break read R > S.
- It is keyed **(index, bar, L, side)**, as rev 5 §F.1 keys a distinct break by bar and line.
- Trades and strikes that share it count once. The break's figures are the **median across its strikes**, as 7b's are, and
  the per-strike rows are shown.

**Its figures [M]:**
- **P_b:** her option's premium at the break close, what folding at the line would have bought back;
- **P_x:** the premium at her first FOLD after it, any rule including 3r and 3s, or at 15:29 (`to_close`) if none;
- **P_max:** **logged:** the highest premium between the break close and that fold, what her margin saw while held;
- **S_b:** the straddle at the break.

**The clause dies if any one holds** (coordinator item 5):
- **(a) the majority:** P_x > P_b on more than half of the held breaks;
- **(b) the total, in premium points:** Σ(P_x − P_b) > 0 over the held breaks, per index;
- **(b′) the total, pooled across indices** in units of the straddle at the break: Σ(P_x − P_b)/S_b > 0.

Each test also counts with the best day removed (the session whose removal moves it most toward failing).

**Printed beside the verdict:** the single worst held break (the largest P_x − P_b, with its P_max), whatever the verdict.

**Two populations, never pooled, each judged on its own count:**
- (i) her writer trades, marked and imported;
- (ii) the expression grid's SELL legs (§E.3 `sell_hold`), each re-read by the window from its unit to 15:29.

It dies if **either** judged population fails. **When:** ≥ 15 held breaks in a population and ≥ 10 sessions, by 30 at the
latest. Short of that, inconclusive and DRAFT.

**If it dies,** writers' rule 3 is rev 5 option B's again, and rule 3s stays. The signed text is on file.

### C.5 How 3r and 3s stamp, and the hazard 3s closes (review S14, S15)

- **3r and 3s are line-family FOLD stamps for writers:**
  - **clause 1** counts them as FOLD stamps;
  - **7b-B** counts them as rule-3 stamps (`fold_rule` ∈ {3, 3r, 3s}, shown split by sub-rule);
  - **7a's unit** is the first line break, whatever folded first, so a held break is 7a's unit.
- **The hazard** (review S15): under rev 4 / 5 today, a writer whose line lies beyond her own strike can sit in the money on
  HOLD with no break. The record has four such sales, the NIFTY 09-22 CE 23,450 legs, with the line 78–99 pts away and the
  strike 58–78 OTM. **Rule 3s closes it:** a close through the strike folds her.
- Rev 4 §4's own-side and payers-adding clauses stand, and so do W1 and W2.

### C.6 Flagged

- **This clause was written after seeing the 09-24 writer replay's folds and premiums, and after the review's numbers.** Its
  unit is the seller-desk design's; its scale is one, as "one candle" is.
- 3s and the signed R were decided as the trader after the review showed the holes.
- **W-R judges it on forward rows only.**

### C.7 THE ONE QUESTION FOR MARY: the reach on expiry day

> Mary, you said about the ATM straddle: *"since today was sensex expiry so that why otherwise atm straddle is ideal"*.
> When you have **sold** an option and it is **that option's expiry day**, and the index closes a 3-min bar through your
> danger line: should the window keep your sale open (WATCH, not FOLD) as long as your strike is farther from the index
> than the ATM straddle?
> **YES or NO?**

- **If YES:** the reach applies on expiry day as on any other day.
  - This is where it does nearly all its work. On the record it bound only on SENSEX 09-24 after 14:38.
  - A sale outside one straddle rides a line break (WATCH · LINE BROKEN · HELD), with the held loss on screen.
  - It folds at the first 3-min close with the strike inside one straddle (3r), at any close at or through the strike (3s),
    or by rules 4 / 6.
- **If NO:** on the sold option's expiry day, a line break folds her exactly as today (rev 5 option B, rule 3). Rule 3s still
  applies. The reach applies only off expiry, where on her days S was 250–600 pts and nearly every sale sits inside it, so it
  will rarely bind.
- **Until she answers,** §C is unsigned, and the draft recommends neither answer.

---

## D. DISCLOSURE (rev a) — *written after rev a's fingerprinted run; see §D.0*

*(pending the run)*

---

## E. PARAMETERS, FALSIFIERS, LOGS, CLOCKS

### E.1 Parameters: inherited, or named

| item | value | from |
|---|---|---|
| cadence | the 3-minute closes of the 09:15 grid (125 a day) | CLAUDE.md rule 3; rev 5 A.0.1; **named choice** (M3) |
| SPEED | the window's "paid" at the close | rev 4 §3 rule 5; VALIDATE rev 2 §1.4 |
| ROOM | VALIDATE §1.3's order: line ≤ noise NEITHER; target < line SELL; else BUY | VALIDATE rev 2 §1.3 (rev a, S1) |
| SHIELD | the nearest of the sold side's top two at or beyond spot (half a step), BUILDING with a build | §1d; `fronts.read`; board's `built` |
| REGIME | §10.1's vote | rev 4 §10 |
| PREMIUM | the straddle of the strike ATM at `t − 15`, CE + PE at `t` against at `t − 15`; both legs up reads NEITHER and R4 | `QUIET` = 15; rev 4 §8; her ATM-straddle words, **with her expiry exception** |
| refusals | R1, R2, R5 the window's; R3, R4 (fails closed), R6 named | §A.4 |
| the word | refusals, then the count; a tie EITHER; `named_by` kept apart | **named choice** (M2) |
| strikes | BUY ATM; SELL at the wall within one straddle, else ATM | side log `atm.k`; §C's unit (Q3) |
| expiries | both legs the chain's resolved expiry; S of her option's own expiry | `upstox_instruments.resolve` (S8, M8) |
| writer facts | Right now · Your wall · Cushion (noise, the strike range, X vs P) · Time is paying | VALIDATE rev 2 §1.2 / §1.3; PLAN §2.1; §A fact 5 |
| writer target · horizon | P − X, 1:1 in premium · 30 min judged, to 15:29 shown | PLAN §2.1; VALIDATE §3's 30 (M6) |
| the reach | signed R against S of her expiry, scale 1×; 3s at R ≤ 0, always | **named choice**; seller-desk design's unit; ≈ 0.2 Δ [I] |
| held loss | PLAN §2.1's writer formula to the fold level (R − S) | PLAN §2.1 |
| W-R | (index, bar, L, side), median across strikes; majority, total points, total in S; best day removed; P_max logged | rev 5 §F.1 / 7b; **named** (M9) |
| expression units | the 3-minute closes at 09:44, 10:14 … 15:14 (the 10th close and every 10th after), per (index, `d`) | the 30-minute horizon on the canonical grid |
| expression outcome | R-multiples on the shared line: each leg's P&L over 30 finished minutes ÷ its PLAN §2.1 premium at risk to L | PLAN §2.1's two formulas (M1) |

**No new number.** The new uses of inherited numbers are 3 (the grid), 15, 30, 1× (the straddle, as 1× the candle) and half a
step. Every named choice above is a new registration if changed.

**Not used, and why:**
- **her "90-minute write guard"** has no text in the repo; it is hers to state;
- **IV against realised vol** is not computed per minute by anything the window reads.

### E.2 A falsifier per word, forward rows only (review M1, M2, S2–S4, S7)

**The units** are the 3-minute closes at **09:44, 10:14 … 15:14**, per (index, `d`), fixed in advance whatever the word.
- 09:44 is the 10th close, the first at least 30 minutes after the open. Every 10th close after is 30 minutes on.
- The word at a unit is the word read at that close.

**The outcome, in R-multiples on the one line both legs share** (review M1; coordinator item 2). For each leg at the unit
minute:
- **risk to L:** PLAN §2.1's own formula, with R = |close − L| unrounded and the broker's Δ, Γ [M] for that leg's strike and
  expiry:
  - a buyer: |Δ|·R − ½·Γ·R², clamped to [0, premium];
  - a writer: |Δ|·R + ½·Γ·R².
- **P&L** over the next 30 finished minutes: long, p30 − p0; short, p0 − p30.
- **R-multiple** = P&L ÷ risk to L. **G** = the long R-multiple − the short R-multiple.
- **The sizing it embeds, named:** equal premium at risk to the same stop, which is how a stop-based trader sizes. No number
  is new.
- **Not scored, shown with its reason:**
  - either leg's risk unreadable (no greeks);
  - the buyer's clamp at 0;
  - the writer's line at or beyond her strike (§B.3's range rule);
  - no sell strike (R6).
- **Shown beside G, never judged:** G in points / S at the unit; each leg's % of its own premium (rev 0a's unit, kept
  visible); MFE and MAE.

**Every claim is split by the index's 30-minute move relative to `d`:** *with* (her direction was right), *against*, or
*flat*.
- **It is judged on the pooled units, and must also hold in the *with* split.** Her direction is hers, so the read must not
  win only where she was wrong.
- The *against* and *flat* splits are shown.

**The populations** (M2, S3, S4):
- **UP and DOWN are separate populations, each judged on its own count** (S4). They are mirror pairs sharing fact 5 at one
  minute.
- **Indices are pooled** within a direction to reach the counts. They are shown per index, and each verdict must hold with
  co-timed sets reduced (NIFTY, then SENSEX, then BANKNIFTY).
- **Count units** are those where neither leg was refused: BUY, SELL and EITHER on the count.
- **Refusal units** (BUY · selling refused; SELL · buying refused) are their own rows, with their codes, never pooled with
  count units.
- **STAND ASIDE · led** is judged. **STAND ASIDE · both refused** is shown, not judged: it re-tests rev 4 B4 and VALIDATE P2
  (the entry FOLD), which judge it already.

**The claims:**
- **BUY (count):** the median G at BUY-count units is **larger** than at the other count units (SELL-count and EITHER).
- **SELL (count):** the median G at SELL-count units is **smaller** than at the other count units (BUY-count and EITHER).
- **EITHER:** the median |G| at EITHER units is smaller than at BUY-count units, **and** smaller than at SELL-count units,
  each separately (S2).
- **STAND ASIDE · led:** the median of max(long R, short R), the better leg, is lower at STAND ASIDE · led units than at count
  units.
- **The sell refusals** (R1–R4; R6 cannot be scored): the median short R-multiple where SELL was refused is lower than at
  SELL-count units. It is shown per code.
  - If it fails, the refusals are re-registered.
  - R5 (the buy refusal) is the window's entry FOLD and is judged there.

**When and how:**
- at **≥ 15 units of that word, per direction, and ≥ 10 sessions**, and in any case at **30 sessions**;
- it must survive **removing the best day** (the session whose removal moves the comparison most toward failing);
- it must also hold with the `short` units (after 14:59) removed.

**Kept visible, shown and never judged** (review S7):
- G at fact 5's FOR BUY and at its FOR SELL units;
- every claim recomputed with fact 5 dropped (the four-fact count, from the logged facts);
- each claim on the 1-minute read of the same unit minute (logged, §E.3), so the cadence choice stays visible.

**If a word fails:**
- **BUY or SELL:** withdrawn. Where it would have been named, the read says "EITHER — {word} withdrawn on {date}", with its
  count.
- **EITHER:** a tie prints the count and no word.
- **STAND ASIDE · led:** the refusals are re-registered; until then the word carries "its falsifier failed on {date}".
- **Short of 15 by 30 sessions:** inconclusive, and the word stays DRAFT.

**Her presses and entries** (the read when a trade was in front of her) are shown, never judged, and never pooled with the
grid.

### E.3 The logs, additive, write-once (`hold_log`'s discipline)

**`data/hold/expr_<day>.jsonl` (new).** One row per 3-minute close, per index, per direction: 750 rows a day. It is written
live by `_hold_tick` and completed by the close-time import.
- **The backfill runs off the request path** (review Q5): about 750 expression reads, each with two window reads. The 09-18
  wedge is the precedent.

```
{kind: "expr", day, t, idx, d, word, named_by: "count"|"refusal", refusal: [codes], since, was: {word, until},
 nb, ns, facts: [[name, state, absence, text]...],
 buy:  {side, k, expiry, px, delta, gamma, entry},
 sell: {side, k, expiry, px, delta, gamma, entry, placement: "wall"|"atm", wall: {k, state, r_w}|null, r_over_S},
 S, line, noise, regime_board, drag, expiry_line, blind: [...], word_1m, unit: bool, prereg: "expr-a", tag: "I"}
```

On a unit close, an **outcome row** is written once its 30 minutes have finished:

```
{kind: "expr_outcome", day, t, idx, d, word, named_by, refusal,
 long:  {side, k, p0, p30, pnl, risk, r_mult, pct, mfe, mae},
 short: {side, k, p0, p30, pnl, risk, r_mult, pct, mfe, mae} | "not scored — why",
 G, G_pts_over_S, move: {pts, split: "with"|"against"|"flat"}, short_window: bool, co_timed: [...],
 writer: {facts, X, word, first_30, first_1529},                                   -- §B.3 population (ii)
 sell_hold: {key: [idx, bar, L, side], R, S_b, held, fold_t, fold_rule, P_b, P_x, P_max, to_close} | null}  -- §C.4 (ii)
```

**`data/hold/check_<day>.jsonl` (additive):**
- every press gains `expr: {word, named_by, refusal, since, nb, ns, facts, legs}`;
- writer presses gain `rev: "2W"`, `word` and the writer `facts`; buyer presses keep `rev: "2"`;
- writer outcome rows carry `role: "short"`, `target: {P, X, level}`, `stop`, `first_30` and `first_1529`;
- the outcome key gains `role` (§B.3).

**`data/hold/hold_<day>.jsonl` (additive, writer rows only):**
- `reach: {k, R, S, S_expiry, atm, outside}` on every bar-close row;
- `held: {key, bar, L, t, R, S, P_b, P_max_so_far, loss_to_fold} | null`;
- `fold_rule: "3r" | "3s"`;
- `writer_clause: "reach-a"`;
- `expiry_day: her §C.7 answer`.

`prereg` keeps its rev 5 value, so buyer rows do not change label.

**Day state:** nothing new. R, S and P_max are read from the day's chain record, which a restart re-reads.

### E.4 The forward clocks

| clause | changed here? | its forward record |
|---|---|---|
| the expression, §E.2 | new | Starts at its first session after the code (`prereg: "expr-a"`). |
| VALIDATE, buyers (P1, P2) | no | **Continues.** The `expr` key is additive. |
| VALIDATE, writers, (i) presses and (ii) grid | new | Starts at the first session after the code (`rev: "2W"`). Earlier writer presses (`word: null`) are rev 2's record, never pooled. |
| the window, buyers | no | **Continues.** |
| the window, writers (W1, W2, the writer clauses 1–7) | yes: rule 3 for writers, plus 3r and 3s | **Reset for writers only** (`writer_clause: "reach-a"`). Rev 5's writer rows stay rev 5's record. |
| §C.4 W-R | new | Starts with the writer reset, **after her §C.7 answer**. |
| §10 side read, PLAN P1 / P2 | no | Continue. |
| PLAN §2.6 (a writer's STOP) | display: the reach line and the held loss | A PLAN change-log line and a new §1f hash; no PLAN rule moves. |

Test browsers strip `&log=1`. Nothing is logged by a test.

---

## F. THE UI, IN WORDS

The rules for both screens:
- LIGHT only, and no charts;
- never a size, and never an order path;
- the three absences are never rendered alike;
- every number is tagged [M] or [I];
- the vocabulary is in Barlow and numbers in Plex Mono (`hold.css`).

### F.1 The Validate tab: "BUY CE vs SELL PE", when a setup pops up

**The slip is unchanged.** She picks CE / PE, long / short and a strike, and presses VALIDATE. When her zone setup names a
direction on its closed bar, a quiet line reads "setup: BUY d2 armed, 11:42 bar — the expression for UP is ready".

**The answer, top to bottom:**

1. **THE EXPRESSION**, one word at 88 px: **BUY CE** · **SELL PE** · **EITHER** · **STAND ASIDE**.
   - Under it, one line: **"since 11:44 · was EITHER until 11:44 · read at the 11:44 close"**.
   - Then the count: "3 for buy · 1 for sell · 1 neither — of 5, a count, not odds", then DRAFT.
   - **A word named by refusal says so in the word's own line, in the caution ink:** "BUY CE — selling refused (R4 — could
     not check: …)".
   - **EITHER reads "the facts split 2–2".**
   - **STAND ASIDE says which:** both refused, or "the facts favour selling, 3 to 0, but selling is refused: …".
   - The leg's ink is black (her instrument, not a verdict colour). STAND ASIDE is caution ink.
2. **Two cards, side by side.** The named leg carries a 2 px ink rule. A refused card is dimmed with its reason, and never
   hidden. Each card keeps its own I'M IN.
   - **Left, "BUY CE 23,100 · ATM · expiry 2026-09-29, 4 days":** the premium and its minute [I], Δ [M], the leg's own
     VALIDATE word at 40 px (read at the press minute), and its entry-check word.
   - **Right, "SELL PE 23,050 · at the floor · 0.4 straddles out · Δ −0.31 [M]":** the wall's strike and state, "your line
     23,061.5 sits 11.5 pts above your strike", the premium [I], and the writer's VALIDATE word (§B).
     - When placed ATM because the wall is beyond one straddle: "SELL PE 23,100 (ATM) — the defended floor 22,850 sits 250
       pts out, beyond one ATM straddle (180 pts [M])".
     - On 0DTE: "S4 expiry flush — logged, not traded · expiry afternoon → neither (the desk's setup table)".
3. **The five facts:** a table with the columns FOR BUY · FOR SELL · NEITHER, one mark per row, the sentence under it with its
   tag.
   - Fact 5's sentence names the move's sign.
   - A NEITHER shows its kind (the `Abs` styles), or "a read".
4. **Printed, not counted,** one line each: the drag number; the expiry line; the board's REGIME (both halves); each leg's σ
   against its VWAP.
5. **Not shown:** "a size", "an order", "odds", once per surface.

**When she pressed SELL directly,** the same block shows for her direction. The writer's card is always on the right.

**When the whole read is absent** ("could not check — the 12:30–12:32 close has not landed"), that replaces the word in the
hatched style.

### F.2 The floating window: a sold option

**The head:** "SOLD PE 22,900 · NIFTY · expiry 2026-09-29" and "YOU ARE SHORT". The word, its since-clock and its tag (LINE
BROKEN · HELD, NOISE, OI BLIND). The noise wording is "The premium you sold is up" (rev 5 §D item 8).

**The rows:**
- **The line row** (a short PE's danger is down): "danger line 23,061.5 (5m swing low 11:25) · breaks below 23,056.6 — 9
  pts away [M]".
- **The reach row, writers only:**
  - "your strike 192 pts out · one ATM straddle 118 pts [M], the market's price of the move to 29 Sep — outside: a line
    break is a WATCH for you";
  - inside: "… — inside: the line decides";
  - held: "held since 12:05 · strike 160 pts out, straddle 118 · ≈ ₹{Y} [I] of premium between here and the fold level ·
    FOLD at the first 3-min close with your strike within one straddle, or at or through your strike".
  - **No row says "safe", "won't reach", or anything like it.**
- **The strike row, always, for writers:** "a 3-min close at or through {k} folds you (rule 3s) — {R} pts out".
- **YOUR SIDE** replaces HOLDERS, and there is **no quiet clock**: "not shown — a writer has no quiet clock; time pays her".

**The footer,** in neutral ink:
- "sold at 92.00 · now 61.50 [I] · decayed 30.50 of 92.00";
- while held, "highest since the break: {P_max} [M]";
- the expiry line;
- the premium at risk to the line [I] (PLAN §2.1).

**The WATCH hint** lists every condition that alone folds her: the reach close, the strike close (3s), rule 4's writer items,
and rule 6's families.

**Collapsed:** `WATCH · SOLD NIFTY 22900 PE · line broken 12:05, held — strike 160 · straddle 118 · ≈ ₹Y to fold · since 12:05`.

**One tone** fires on the transition into FOLD (3, 3r and 3s included). There is nothing on WATCH or HOLD.

---

## G. Change log

**Rev 0, 2026-09-26 00:16 IST (clock).**
- §A–§C and §E–§F were written before any run.
- Fingerprinted at 00:21, sha256 `eca1afe0debf687d56d8e35d4d42c475280b6f01267e7431b6cb6271da2e2b6c`
  (`rules_before_run.md`).

**00:27, during implementation.** §C.2 item 4 was silent on a close *while held* whose straddle cannot be read. It was made
to fold, the conservative reading. At that point only rev 0's word counts had printed, and nothing of §C.

**Rev 0a, 00:32: fact 5 replaced after rev 0's run, on principle, with the counts in view.**
- **What was seen:** rev 0's fact 5 (the current ATM pair against its session VWAPs) read FOR BUY on 5,434 of 6,720 minutes.
- **Why it moved:** rev 4 §8's re-centring defect. **Consequential edits:** R4 and §B fact 4 read the new object; the §F.2
  example was corrected.
- **Fingerprinted before its run:** sha256 `5ddc16d1357e41f4feb99a7ad4cb78a7b737e6bb701bbcb33316dcfad15a9654`
  (`rules_rev0a_before_run.md`).
- **The direction of the change** (review M5d, disclosed now):
  - every entry word it moved went **toward SELL**: #16 EITHER → SELL, #17 BUY → EITHER, #22 BUY → SELL, #29 BUY → SELL;
  - the grid moved BUY 3,817 → 2,464 and SELL 871 → 1,734.
  That is the direction of the draft's evident aim, a read that can say SELL, and the lean was foreseeable, because time wins
  most short windows.
- **The alternative not taken:** drop fact 5 and count four.
  - It was not taken because by parity fact 5 is the one fact that reads the expression question directly (§A.1).
  - Forward, every claim is also shown recomputed with fact 5 dropped (§E.2, S7).

**After the rev 0a fingerprint and before the review, three rule-text edits that §G did not log** (review M5a, logged now):
1. **Fact 5's "equal".** The fingerprint read "equal, a premium missing at either end, or `t − 15` before 09:15: NEITHER,
   could not check". The draft changed "equal" to "NEITHER, a read". That changed an absence kind, after rev 0a's run.
2. **"So the count cannot lean by construction" was struck** after §D.1 showed ROOM and PREMIUM leaning.
3. **§C.4's best-day sentence was rewritten.** It went from "or if the comparison reverses when the best day is removed" to
   "dies if that is true once the best day is removed … (rev 5 §F.2)", beyond the dedup, which was logged.

**00:43.** §C.4's unit gained a dedup (logged then).

**00:34–00:47.** §D and §H were added.

**The header's "two clarifications … §G lists them" was not true** as written (review M5b). This header replaces it.

**`silence_detail.json`** (review M5c) was listed in §D.0 but never written: the inline script that was to write it did not
leave the file. Rev a's run writes it, and a rev 0a copy (`rev0a/silence_detail.json`) is regenerated from rev 0a's code so
the counts it backed can be checked.

**The draft as the review read it** (sha256 `d7c4a4de…4015`, mtime 00:48) is kept in the scratch folder as
`draft_as_reviewed_d7c4a4de.md`.

**Rev a, 2026-09-26 01:25 IST (clock), written before its run.** One entry per review item. Every change below was written
after the review's numbers were read.

**The must-fixes:**
- **M1, the outcome unit:** "% of own premium" is replaced by **R-multiples on the one shared line**: PLAN §2.1's two formulas,
  G = long R − short R. Every claim is split by the index's 30-minute move (with / against / flat), and must hold pooled and in
  *with*. The % rows are shown. Decided as the trader (item 2).
- **M2, refusal-named words:** `named_by` / `refusal` in the words, the screen, the logs and the falsifiers. Count units and
  refusal units are never pooled, and the sell refusals get their own claim (§E.2). Item 7.
- **M3, stability:** the word is **read on the 3-minute close** (§A.2), with a since-clock. The flip counts and the one-fact
  share are disclosed under both cadences in §D.2, from a re-run as a disclosure, not a tuning pass. The unit grid moves to the
  closes at 09:44 + 30k. Item 1.
- **M4, R4 fails closed:** an unreadable fact 5, or S unreadable, refuses SELL. The 09-25 09:35 row is restated in §D. Item 3.
- **M5, disclosure and attribution:**
  - the three edits above;
  - the header;
  - `silence_detail.json`;
  - the direction of the four moved words and the alternative not taken;
  - every attribution. "Both legs decaying together" is the spec's prose; "1:1 atleast" is hers, about a buyer's exit; the
    seller-desk design is the models'; her expiry exception is quoted with the ATM straddle; the desk's setup table and the
    operator thesis are design notes; the OI reading is quoted verbatim, with the inference marked as the draft's.
  - Item 8.
- **M6, the writer word's reachability:** population (ii), the grid SELL legs, is added. The horizon is fixed now: 30
  minutes judged (inherited, non-overlapping on the grid), to 15:29 shown. S11's sentence is added. Item 6.
- **M7, the unsigned R:** R is signed.
  - **Rule 3s:** a close at or through her strike **always** folds a writer: at every close, held or not, broken or not.
    "Always" is read literally, as decided by the trader (item 4). This also closes S15's hazard, which the review had left
    to her. **She signs it.**
  - The held loss is printed (PLAN §2.1), and no copy implies safety.
- **M8, the wrong expiry:** S is the ATM straddle **of her option's own expiry**, else the reach cannot be read and the line
  folds her. It is the same for every reach print and for R/S.
- **M9, W-R's tail:** it dies on the majority **or** on the total premium-point cost (per index, and pooled in units of S),
  each also with the best day removed. P_max is logged, and the worst held break is printed. Item 5.

**Q3, the sell strike** (coordinator item 9): at the wall within one ATM straddle of its expiry, else at the money, with the
wall behind it (§A.5). §D discloses what it names.

**The expiry-day exception** (coordinator item 4): **not decided.** It is asked as one yes/no question in §C.7, and §C cannot be
signed without her answer.

**The should-fixes, all taken:**
- **S1:** ROOM reads line ≤ noise as NEITHER. This was proposed by the review after ROOM's lean was seen, and taken on
  principle (VALIDATE §1.3's own order).
- **S2:** EITHER reads "the facts split b–s", and its claim compares with BUY-count and SELL-count each.
- **S3:** STAND ASIDE is split into both refused (shown; re-tests B4 / P2) and led (judged).
- **S4:** UP and DOWN are separate populations, and indices are pooled within one, stated.
- **S5:** the co-occurrence is disclosed (§D.5).
- **S6:** the parity argument is in §A.1 / §A.3, and fact 5's sentence names the move's sign.
- **S7:** fact 5's rows, and the claims with fact 5 dropped, are shown forward.
- **S8:** each leg's expiry, R/S and Δ are printed, and on 0DTE the setup-table row (printed, not a refusal).
- **S9:** every VALIDATE section amended is listed.
- **S10:** the line at or beyond the strike reads "could not check — the formula does not reach", in the Cushion and in the
  R-multiple.
- **S11:** what the 30-minute writer test mostly tests.
- **S12:** safety copy is removed and banned.
- **S13:** W-R is keyed (index, bar, L, side), median across strikes, with per-strike rows.
- **S14:** 3r and 3s are line-family stamps.
- **S15:** closed by 3s.
- **S16:** rev 4 §1's principle is stated as changing for writers.
- **S17:** what the rule is, where she signs (§C.1), and the held loss.

**Rev a's fingerprint** is in §D.0, taken before its run.

---

## H. What this draft could not resolve

1. **The expiry-day question (§C.7)** is hers. §C cannot be signed without it.
2. **The word's margin.** Read at the 3-minute close, the word still carries many one-fact margins (§D.2). The since-clock
   and the count show it; nothing hides it. Whether a one-fact margin should read EITHER is **not** registered: it would
   invent a threshold.
3. **ROOM leans BUY** where no holding wall is in the way and the line is outside one candle. It is inherited from VALIDATE's
   target, and judged forward.
4. **Rule 3s folds a sale made in the money at its first close.** A deliberate in-the-money sale is not supported by this
   window. Hers to say if it should be.
5. **Only closes are read.** A bar can carry price through her strike and back (§C.3). P_max and the held loss show it; they
   do not prevent it.
6. **Her "90-minute write guard"** has no text in the repo. **IV against realised vol** is not computed per minute. Neither is
   used.
7. **The disclosure's inputs** are partly [I]:
   - Black-76 greeks, not the broker's;
   - nearer-only fronts on 09-22 and 09-23;
   - [I] candles on two 09-24 indices;
   - 09-21 and the 09-25 premiums not frozen;
   - for 09-25, the facts at the 3-minute close before each entry not frozen (§D).
   The forward rows are the only evidence.
8. **The owed code changes when she signs** (none made here):
   - the `expr_<day>` log at the 3-minute close, with the backfill off the request path;
   - the outcome key's `role`, with `_hold_tick`'s `has()` changed with it;
   - the writer rows' `reach` / `held` / `3r` / `3s` keys, and the expiry-day answer;
   - PLAN §2.6's display, change-log line and §1f hash;
   - **tests:**
     - the word order and `named_by`;
     - R4 failing closed;
     - ROOM's noise step;
     - the far-wall ATM placement;
     - signed R and 3s, including a held writer whose close lands through the strike by more than S;
     - S of her own expiry;
     - the held loss;
     - W-R's total test;
     - the outcome key collision.
