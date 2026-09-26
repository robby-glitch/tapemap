# PRE-REGISTRATION DRAFT — THE EXPRESSION: BUY THE OPTION, OR SELL THE OTHER SIDE; THE SELLER IN VALIDATE; THE SELLER IN THE WINDOW — REVISION b (rev 0 written 2026-09-26 00:16 IST; rev a 01:25; rev b written 01:47 IST by the clock, before its run; NOT SIGNED, UNTESTED)

**Status.** This is a DRAFT. Nothing below is a result. Nothing here is in force until Mary signs it.

**The record of how it got here:**
- **Rev 0 (00:16) and rev 0a (00:32)** were each fingerprinted before their run. Rev 0a changed fact 5 after rev 0's run. The
  history is in §G.
- **Rev a (01:25)** answers the adversarial review `docs/hold/EXPRESSION-REVIEW.md` (01:11), whose verdict was **NOT YET on
  A, B and C**.
- **Rev a's text of §A–§C, §E and §F was fingerprinted before its disclosure run** (§D.0). §D was written after that run.
- §G lists every edit to the rules made after a fingerprint, including the three that rev 0a left out (review M5).
- **Rev b (01:47)** takes two trader decisions made **after rev a's rows were seen**, on principle, and is fingerprinted
  before its run (§D.0):
  - the strike rule inherits rev 5 option B's one-candle buffer (§C.2);
  - the word shows its margin: BUY / SELL, LEANS BUY / LEANS SELL, EITHER, STAND ASIDE (§A.4).

**Decisions taken as the trader.** Where the review left a choice, these were decided on her standing delegation and
conveyed by the coordinator on 2026-09-26. Her words: *"Think yourself as the trader and you are building the for youself"*.
- the word is read on the 3-minute close (M3);
- the outcome is in R-multiples (M1);
- an unreadable straddle refuses SELL (M4);
- the signed reach, and a close through the strike always folds (M7); rev b adds rev 5 B's one-candle buffer to it;
- her option's own expiry, else FOLD (M8);
- the kill clause judges total and majority (M9);
- the grid writer population and its horizon (M6);
- the refusal split (M2);
- the far-strike rule (Q3).
- **rev b, after rev a's rows were seen:** the strike rule with rev 5 B's buffer; the word's strength shown as LEANS.

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
  BUY votes. §D.3 shows the co-occurrence.

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
  - *Sources:* the both-legs-rising skip that her profile lists in her validated spine, and that the desk's setup table
    calls S5 (design notes).
  - The seller-desk design's "straddle rising while spot flat = vega attack" (the models' design, not her words).
- **otherwise the straddle rose:** FOR BUY. "A straddle bought at {t−15} is up {x} pts [M]: the move paid more than time
  took — the index moved {m} pts {with / against} your direction [M]".
- **the straddle fell:** FOR SELL. "A straddle sold at {t−15} is up {x} pts [M]: time took more than the move paid — the
  index moved {m} pts {with / against} your direction [M]".
- **unchanged:** NEITHER, a read.
- **a premium missing, or `t − 15` before 09:15:** NEITHER, could not check, and **R4 refuses SELL** (§A.4).

*Why the sentence names the move's sign* (review S6): the straddle is direction-free. On 1,144 of rev 0a's 2,288 FOR BUY
minutes (the review's count) the move had gone **against** her direction. "BUY CE — the move out-paid time" after a fall would otherwise read as
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

**The word (rev b)**, in this order. `b` and `s` are the FOR BUY and FOR SELL counts, and the **lead** is the named leg's
count minus the other's.
1. **could not check** when the line cannot be set at the close (no index candle, or the close not landed);
2. **both refused: STAND ASIDE · both refused**, naming each refusal;
3. **only SELL refused:**
   - a lead of 2 or more: **BUY {CE|PE} · selling refused**, with the codes;
   - a lead of exactly 1: **LEANS BUY {CE|PE} · selling refused**;
   - a tie: **STAND ASIDE · tie, selling refused**: "the facts tie {b}–{s}, and selling is refused: nothing leads to
     buying";
   - selling leads: **STAND ASIDE · led**: "the facts favour selling, {s} to {b}, but selling is refused: {why}";
4. **only BUY refused:** mirrored (SELL / LEANS SELL · buying refused; STAND ASIDE · tie; STAND ASIDE · led);
5. **neither refused (on the count):**
   - a lead of 2 or more: **BUY** or **SELL**;
   - a lead of exactly 1: **LEANS BUY** or **LEANS SELL**;
   - a tie: **EITHER**: "EITHER — the facts split {b}–{s}" (review S2). At 0–0 it reads "nothing separates them".

**The word's strength is in the word** (rev b, the trader's decision after rev a's rows):
- **There is no threshold number.** "Exactly 1" means a single fact decides the word, and "2 or more" means more than one
  does.
- **LEANS is a word of its own:** on screen, in the log (`strength: "lead" | "leans" | "tie"`, `lead: n`), and in the
  falsifiers, where LEANS and BUY / SELL are separate populations, never pooled (§E.2).

**The tie with one leg refused is STAND ASIDE** (rev b).
- **Rev a named the open leg at a tie** ("BUY · selling refused" at b = s). The review singled that out as "the word to
  worry about".
- Under rev b's rule that the margin shows in the word, a tie cannot be EITHER when one leg is closed. The open leg leads by
  nothing, so the word is STAND ASIDE · tie.
- **This is the drafter's reading** of the decision "STAND ASIDE when refused". It is flagged in §G and §H for the trader to
  confirm.

**The split is kept everywhere** (review M2): on screen, in the log (`named_by: "count" | "refusal"`, `refusal: [codes]`) and in
the falsifiers (§E.2).
- A word named because the other leg is refused is **never** dressed as, pooled with, or judged as a word on the count.
- *Why:* a word on the count compares two live legs. A word by refusal had one leg that was never an alternative, so it
  tests the refusal, not the facts.

**Named choices, none of them a number:**
- a leg is refused by its own rules, not outvoted;
- a refused leg's lead, or a tie, makes STAND ASIDE, never a vote for the other leg;
- a tie of live legs is EITHER;
- one fact's lead is LEANS;
- the word is read at the 3-minute close.

### A.5 Which strike, and which expiry, each leg is

**Both legs are the chain record's resolved expiry for that index** (`upstox_instruments.resolve`, the nearest live one),
named on screen: "expiry {date}, {n} days" or "0DTE" (review S8). The facts are strike-free, so the strike is a print, not an
input.

**BUY: the ATM strike** (spot rounded to the step; the side log's `atm.k`). Her words: *"i often trade itm or atm so which
option i m holding hardly matters"*. It is printed "ATM {k}; one strike ITM reads the same facts".

**SELL (rev a, coordinator Q3).** **A sale is never placed in the money:** rule 3s (§C.2) would fold it at its first close.
K₀ is the nearest strike at or beyond spot on the sold option's out-of-the-money side: for a PE sale the highest strike ≤
spot, and for a CE sale the lowest strike ≥ spot.
1. **At the wall behind the sale** (fact 3's wall), when that wall lies **within one ATM straddle** of spot. That is its
   signed out-of-the-money distance r_w ≤ S, with S the ATM straddle of the same expiry at `t`.
   - When the wall is "at" spot on the in-the-money side (inside SHIELD's half-step tolerance), the sale goes to K₀, and the
     wall stands at the money beside it.
   - Otherwise it goes at the wall's strike, the farther from spot of the wall and K₀.
2. **When the wall lies beyond one straddle** (r_w > S): **at the money, out-of-the-money side: K₀.** The defended wall still
   stands behind it, farther out.
   - The print: "SELL PE {k} (ATM) — the defended floor {kw} sits {r_w} pts out, beyond one ATM straddle ({S} pts [M]); a sale
     at the floor would be {r_w/S:.1f} straddles out".
3. **S unreadable:** SELL is refused (R4).
4. **No wall:** "not shown" (R6).

*Why the rule, inherited:*
- **one ATM straddle** is §C's reach unit (the market's price of the move to that expiry). A strike one straddle out sits
  near 0.2 delta under the usual lognormal reading [I] (the review's independent check). That is the seller-desk design's
  first delta lamp.
- **K₀** is the side log's `atm.k`, or its neighbour on the out-of-the-money side: never in the money. There the sale has
  about the buy's Δ, and by parity the comparison is nearly the straddle's (§A.1).
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
- **The word is close to a coin flip at its margin.** Many words are named by one fact (§D.2).
  - Rev b says so **in the word**: LEANS BUY / LEANS SELL.
  - The since-clock shows whether a 3–2 is new or has stood.
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
| 3 | **Cushion**: the danger line against the noise, and what the line costs against what you collect | line > one candle's noise **and** P ≥ X | line ≤ noise **or** X > P | line blind, noise unreadable, or no greeks (*could not check*) |
| 4 | **Time is paying**: the fixed straddle (§A.3 fact 5) | the straddle fell | both legs rose | the straddle rose by a move, or unchanged (a read) · unreadable (*could not check*) |

**1 Right now.** The buyer's object (VALIDATE §1.2), read for the short leg, with rev 4 §4's writer clauses. Rule 3 cannot
fire at entry (M5), so §C does not touch it.

**2 Your wall [M].** Your side's §1d top two, the nearest to spot of those at or between spot and your strike (inclusive, half
a step): BUILDING with a build, WITH; else NEITHER, a read. It has no AGAINST: a squeeze is inside Right now, as VALIDATE §1.4
keeps payers and flow inside Right now.

**3 Cushion [M and I]**, in VALIDATE §1.3's order:
1. line or noise unreadable: could not check;
2. line ≤ noise: AGAINST ("your danger line is {s} pts away — inside one candle's range");
3. no greeks for your strike and expiry: could not check;
4. X > P: AGAINST ("your line is worth {X} of premium [I]; you collect {P} [M]"). X is PLAN §2.1's writer formula,
   |Δ|·R + ½·Γ·R², with R the unrounded line distance and the broker's Δ, Γ [M];
5. otherwise: WITH.

**When the line lies at or beyond your strike** (line distance ≥ your strike's signed OTM distance from spot), X is still
computed, and it is **flagged** (review S10, the "state it" option): "[I] — your line lies beyond your strike, where this
second-order estimate is least trustworthy (PLAN §7)".
- *Why not "could not check":* an at-the-money sale, which is §A.5's far-wall placement and parity's cleanest comparison,
  always has its danger line beyond its strike. Reading it blind would blind the writer's word exactly where rev a places
  sales.
- The danger past the strike is rule 3s's job (§C.2).

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
- **Not scored**, each shown with its reason: no greeks; the line not set; X > P ("checked,
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
- **Rule 3s adds one hard stop for every writer, always:** a 3-minute close through her strike by **more than one frozen
  median 1-minute candle** folds her. That is rev 5 option B's own buffer (rev b).

### C.2 The rule

At each 3-minute close, for a **writer**, read two numbers [M]:
- **R**, signed (review M7): the distance from the close to her strike **on the strike's OTM side**. That is k − close for a
  short CE, and close − k for a short PE. R ≤ 0 means the close is at or through her strike.
- **B_k** (rev b): **exactly rev 5 §A.2's B**, with its measure, window, freeze, clamp and fallback, read for the strike's line.
  - It is the median high − low of the index's own 1-minute candles over the 15 finished minutes ending at the minute the
    strike's line is set, which is her entry read. All 15 must be present.
  - It is frozen. The strike never trails, so B_k is read once, and rev 5's clamp (never away) can never bind.
  - Fewer than 15 candles at entry: buffer 0 until B_k can be read, at the first later minute with its own 15, then frozen.
    That is rev 5's named fallback and its one move away.
  - The strike's break level is **k + B_k** for a short CE and **k − B_k** for a short PE, printed from entry beside the
    strike.
- **S** (review M8): **the ATM straddle of her option's own expiry** at that close's minute, the ATM CE plus the ATM PE of
  that expiry. When the day's chain record does not carry her option's expiry, or does not price its ATM pair that minute,
  **S is unreadable**.

Then, in order:
1. **Rule 3s — the strike, always, with rev 5 B's buffer** (rev b). At any close, broken line or not, held or not: a close
   **beyond the strike's break level** (R < −B_k, strict) → **FOLD, rule 3s**. "{IDX}'s {bar} bar closed {|R|} pts through
   your strike {k} — {|R| − B_k} past one candle ({B_k} pts [M], read {B_at})".
   - *Principle:* her line rule, signed as rev 5 B, says a close inside one normal candle is noise. The strike is a line, so
     the same rule applies. **A zero-buffer strike stop (rev a) contradicted signed rev 5.**
   - A sale made more than one candle in the money folds at its first close, and the entry check says so at entry.
2. **At a close that rule 3 reads as a break** (rev 5 option B):
   - S unreadable: **FOLD, rule 3** ("could not check the reach: {why} — the line decides");
   - R ≤ S: **FOLD, rule 3**, as today, adding "your strike is {R} pts out, inside one ATM straddle ({S} pts [M], the
     market's price of the move to {expiry})";
   - R > S: **held.** The word is **WATCH**, tag **LINE BROKEN · HELD**:
     > "The line broke at the {bar} close ({by} pts past {L}). Your strike is {R} pts out, outside one ATM straddle ({S} pts
     > [M], the market's price of the move to {expiry}). ≈ ₹{Y} [I] of premium between here and the fold level. FOLD at the
     > first 3-min close with your strike within one straddle, or through your strike by more than one candle."
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
  - a close through her strike by more than one candle folds her whatever S says (3s).
- **What it cannot close:** only closes are read (rev 5's grid). One 3-minute bar can carry price through her strike and
  back inside the bar. On an expiry afternoon a single bar can be as wide as the straddle: SENSEX 09-24 at 15:29 had S 20.05
  against a 139.3-pt bar (review M7). The held loss and P_max (§C.4) are printed and logged for that reason.
- **What the buffer costs** (rev b): a close up to one candle through her strike does not fold her by 3s. That is the price of
  not folding on noise, the same price rev 5 B already pays at the line.
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
  strike 58–78 OTM. **Rule 3s closes it:** a close through the strike by more than one candle folds her.
- Rev 4 §4's own-side and payers-adding clauses stand, and so do W1 and W2.

### C.6 Flagged

- **This clause was written after seeing the 09-24 writer replay's folds and premiums, and after the review's numbers.** Its
  unit is the seller-desk design's; its scale is one, as "one candle" is.
- 3s and the signed R were decided as the trader after the review showed the holes. **3s's buffer (rev b) was decided
  after rev a's rows showed the zero-buffer stop's cost.**
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
  - It folds at the first 3-min close with the strike inside one straddle (3r), at any close more than one candle through
    the strike (3s), or by rules 4 / 6.
- **If NO:** on the sold option's expiry day, a line break folds her exactly as today (rev 5 option B, rule 3). Rule 3s still
  applies. The reach applies only off expiry, where on her days S was 250–600 pts and nearly every sale sits inside it, so it
  will rarely bind.
- **Until she answers,** §C is unsigned, and the draft recommends neither answer.

---

## D. DISCLOSURE (rev a) — written 2026-09-26 01:40 IST by the clock, after rev a's fingerprinted run

**In-sample hindsight** on four frozen days and one live day. These are counts and rows, never a rate. **None of it counts
toward §E**, and no word is scored against an outcome on the grid. Every figure here is a construction property, or one of
her own entries' rows.

### D.0 Method, fingerprints, limits, and one incident

**Fingerprints** (`sha256sum` of this file):
- rev 0 `eca1afe0…2b6c` (00:21);
- rev 0a `5ddc16d1…a654` (00:33);
- **rev a** `79d7daa68fd9cc5bc3bd56396fafe184f65e7c7e99d13ca033bb061b5db1162d` (01:28, `rules_reva_before_run.md`);
- after the two smoke-test fixes (§G 01:31), **rev a as run**
  `cd210306eba4f668856f91985fd1071074c5b7a2ee7247f8f9e7391b36dfddf5` (01:32, `rules_reva_asrun.md`);
- the draft as the review read it, `d7c4a4de…4015`, kept as `draft_as_reviewed_d7c4a4de.md`.

**Scratch** (the session scratchpad `expr/`):
- `expr_a.py` implements rev a once, reusing rev 0a's helpers in `expr.py`;
- `run_a.py` does the run.

Its outputs are in `expr/reva/`:
- `stability.json` and `silence_detail.json` (both cadences, per index-day);
- `facts_3m.json`;
- `entries.json` and `tables_a.md`;
- `seller_0924.json`;
- `grid.json` and `grid_sell_hold.json`.

`expr/rev0a/silence_detail.json` is rev 0a's own detail, regenerated from its code.

**The incident** (it also answers review M5c):
- **What happened:** `expr.py` changes its working directory into the repo (`os.chdir`). So two outputs written from inline
  scratch scripts with relative paths landed in the repo root:
  - `tapemap/silence_detail.json` (00:40), which is rev 0a's `silence_detail.json` that the review found "missing";
  - `tapemap/rev0a/silence_detail.json` (01:37).
- **When and how it was fixed:** both were found at 01:38 by `git status` and moved into `expr/rev0a/`. The first is now
  `silence_detail_0040_from_the_inline_run.json`, and it matches rev 0a's §D.1 exactly.
- **What else was touched:** no other repo file. `data/` was never opened. The server was not touched, and nothing was
  POSTed.

**The inputs** are as rev 0a's §D.0:
- the frozen facts;
- the 09-24 frozen OI grids, ranked by the open plus the running high [I];
- **nearer-only fronts on 09-22 and 09-23** [I];
- Black-76 greeks [I], not the broker's;
- [I] candles on NIFTY and BANKNIFTY 09-24;
- 09-21 not frozen;
- 09-25 without premiums.

**S of "her option's expiry":** on every frozen day, the fixture's chain was the expiry of the options it priced. So the
straddle read is that expiry's.

### D.1 Words and silence at the registered cadence, the 3-minute close

There are 125 closes per index-day and direction, 2,250 in all.

| index-day | dir | BUY (count · by refusal) | SELL (count · by refusal) | EITHER | STAND ASIDE (both · led) | changes · direct BUY↔SELL | median run | BUY/SELL named by one fact |
|---|---|---|---|---|---|---|---|---|
| NIFTY 09-22 (0DTE) | UP | 31 (9 · 22) | 42 (42 · 0) | 4 | 48 (31 · 17) | 34 · 6 | 6 min | 37 of 73 |
| | DOWN | 27 (17 · 10) | 46 (46 · 0) | 27 | 25 (20 · 5) | 34 · 5 | 6 min | 33 of 73 |
| SENSEX 09-22 | UP | 42 (16 · 26) | 44 (43 · 1) | 11 | 28 (16 · 12) | 51 · 19 | 6 min | 41 of 86 |
| | DOWN | 42 (19 · 23) | 45 (45 · 0) | 10 | 28 (16 · 12) | 35 · 10 | 6 min | 41 of 87 |
| BANKNIFTY 09-22 | UP | 42 (8 · 34) | 13 (13 · 0) | 3 | 67 (47 · 20) | 31 · 8 | 6 min | 23 of 55 |
| | DOWN | 44 (10 · 34) | 47 (46 · 1) | 4 | 30 (16 · 14) | 34 · 8 | 3 min | 34 of 91 |
| NIFTY 09-23 (range) | UP | 43 (38 · 5) | 36 (36 · 0) | 25 | 21 (3 · 18) | 62 · 25 | 3 min | 46 of 79 |
| | DOWN | 46 (5 · 41) | 19 (19 · 0) | 12 | 48 (26 · 22) | 46 · 8 | 3 min | 18 of 65 |
| SENSEX 09-23 | UP | 32 (30 · 2) | 53 (53 · 0) | 23 | 17 (1 · 16) | 47 · 16 | 6 min | 50 of 85 |
| | DOWN | 30 (10 · 20) | 39 (39 · 0) | 16 | 40 (16 · 24) | 45 · 2 | 3 min | 29 of 69 |
| BANKNIFTY 09-23 | UP | 40 (35 · 5) | 40 (40 · 0) | 15 | 30 (17 · 13) | 53 · 14 | 4.5 min | 42 of 80 |
| | DOWN | 52 (5 · 47) | 18 (17 · 1) | 10 | 45 (27 · 18) | 33 · 6 | 6 min | 19 of 70 |
| NIFTY 09-24 (trend down) [I candles] | UP | 29 (23 · 6) | 10 (10 · 0) | 20 | 66 (62 · 4) | 36 · 2 | 6 min | 20 of 39 |
| | DOWN | 74 (71 · 3) | 23 (23 · 0) | 19 | 9 (3 · 6) | 44 · 12 | 6 min | 55 of 97 |
| SENSEX 09-24 (0DTE, trend down) | UP | 52 (14 · 38) | 8 (8 · 0) | 30 | 35 (26 · 9) | 42 · 2 | 3 min | 22 of 60 |
| | DOWN | 69 (68 · 1) | 27 (26 · 1) | 13 | 16 (6 · 10) | 47 · 15 | 6 min | 57 of 96 |
| BANKNIFTY 09-24 [I candles] | UP | 52 (24 · 28) | 34 (34 · 0) | 15 | 24 (19 · 5) | 38 · 11 | 6 min | 44 of 86 |
| | DOWN | 62 (53 · 9) | 36 (36 · 0) | 18 | 9 (8 · 1) | 40 · 16 | 6 min | 60 of 98 |
| **total, of 2,250** | | **809 (455 · 354)** | **580 (576 · 4)** | **275** | **586 (360 · 226)** | **752 · 185** | 6 min | **671 of 1,389** |

**Silence at the 3-minute close: 586 of 2,250 closes, all STAND ASIDE.**
- 360 of those are both legs refused. In all of them the long leg's entry check folds, so they gather on the counter-trend
  direction.
- None is "could not check": the 30 minutes with no index candle all fell between closes.

**Every minute, for comparison** (6,750 reads):
- BUY 2,395 (1,366 on the count · 1,029 by refusal);
- SELL 1,794 (1,779 · 15);
- EITHER 774;
- STAND ASIDE 1,757 (1,069 both · 688 led);
- could not check 30.
- **Silent on 1,787.**

**Refusal-named words are not rare.** 354 of the 809 BUYs at the close were named because SELL was refused. They are kept
apart everywhere (§A.4, §E.2).

### D.2 Stability under both cadences (review M3)

| | read every minute | **read at the 3-minute close (registered)** |
|---|---|---|
| reads | 6,750 | 2,250 |
| word changes, of transitions | 1,398 of 6,732 | **752 of 2,232** |
| changes per index, per direction, per session | about 78 | **about 42** |
| median life of a word | 2 minutes | **6 minutes** (two bars) |
| runs that last a single read | 530 of 1,416 | **355 of 770** |
| direct BUY ↔ SELL flips | 369 | **185** |
| BUY / SELL words named by one fact | 2,077 of 4,189 | **671 of 1,389** |
| of those, on the count | 1,767 of 3,145 | **569 of 1,031** |

The review's count for rev 0a, every minute, was: 1,340 changes, median 2 minutes, 498 of 1,358 runs of one minute, 365
direct flips, and 2,077 of 4,198 BUY/SELL minutes by one fact.

**Plainly.** The 3-minute close halves the changes per session and triples the median life of the word. **It does not make the
word stable.**
- It still changes at about one close in three (752 of 2,232).
- Nearly half its runs last a single bar (355 of 770).
- 185 of its changes are a **direct BUY ↔ SELL flip**, about one bar transition in twelve.
- About half its BUY / SELL words stand on a single fact (671 of 1,389).

At the 3-minute close the word is still close to a coin flip at its margin. That is why the since-clock and the count are
printed, and it is §H.2's open item.

### D.3 Facts, refusals, co-occurrence and the sell strike, at the 2,250 closes

| fact | FOR BUY | FOR SELL | NEITHER |
|---|---|---|---|
| SPEED | 1,008 | — | 1,242 |
| ROOM (with S1's noise step) | 1,138 | 707 | 405 |
| SHIELD | — | 537 | 1,713 |
| REGIME | 567 | 1,116 | 567 |
| PREMIUM | 766 | 1,316 | 168 |

**Refusals, per close** (a close can carry several):

| refusal | closes |
|---|---|
| R1 | 355 |
| R2 | 311 |
| R3 | 98 |
| R4, both legs rose | 24 |
| **R4, could not check** | **138** |
| R5 | 372 |
| R6 | 440 (over-fired on 09-22 and 09-23: nearer-only fronts) |

**Co-occurrence** (review S5). The facts co-vote by regime, so the count is not independent evidence:

| pair (both votes) | together | if independent |
|---|---|---|
| SHIELD SELL · ROOM SELL (a pin) | 294 | 169 |
| SPEED BUY · REGIME BUY (a trend) | 331 | 254 |
| REGIME BUY · PREMIUM BUY | 217 | 193 |
| REGIME SELL · PREMIUM SELL | 686 | 653 |
| SPEED BUY · ROOM BUY | 470 | 510 |

**Where the sale was placed (Q3)**, at the 580 SELL words:

| placement | SELL words |
|---|---|
| at the wall | 478 |
| at K₀, because the wall sat at the money on the in-the-money side | 83 |
| at K₀, because the wall lay beyond one straddle | 19 |

The wall's distance in straddles at SELL words had quartiles of 0.09 / 0.19 / 0.34. The far case is rare, and it happened on
the expiry afternoon.

### D.4 At her 29 entries, the word on the screen at her entry (the last 3-minute close at or before her read minute)

Facts are marked B = FOR BUY, S = FOR SELL, · = NEITHER, in the order SPEED · ROOM · SHIELD · REGIME · PREMIUM. "Four facts" is the
same count with fact 5 dropped (review S7; shown, not used).

| # | entry (read · the close read) | dir | **word** (rev a, 3-min) | b–s | facts | refused | since · was | 1-min read (rev a) | rev 0a | four facts | BUY leg | SELL leg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 09-21 13:59 NIFTY 23300CE | UP | **could not check** — never frozen | | | | | | same | | | |
| 2 | 09-22 09:41 · 09:41 NIFTY 23300CE | UP | **STAND ASIDE · both** | 1–3 | · S S B S | R5, R1 | since 09:41 · was SELL PE | STAND ASIDE · both | STAND ASIDE | STAND ASIDE · both | CE 23,450 | PE 23,400 · at the wall · 0.57 S |
| 3 | 09-22 10:31 · 10:29 NIFTY 23550PE | DOWN | **SELL CE** | 1–3 | B S S · S | — | since 10:26 · was EITHER | EITHER | EITHER | SELL CE | PE 23,450 | CE 23,450 · at the wall · 0.15 S |
| 4 | 09-22 10:41 · 10:41 NIFTY 23550PE | DOWN | **BUY PE** | 3–2 | B B S S B | — | since 10:41 · was SELL CE | BUY PE | BUY PE | EITHER | PE 23,400 | CE 23,450 · at the wall · 0.65 S |
| 5 | 09-22 10:42 · 10:41 NIFTY 23550PE | DOWN | **BUY PE** | 3–2 | B B S S B | — | since 10:41 · was SELL CE | SELL CE | SELL CE | EITHER | PE 23,400 | CE 23,450 · at the wall · 0.65 S |
| 6 | 09-22 10:43 · 10:41 NIFTY 23550PE | DOWN | **BUY PE** | 3–2 | B B S S B | — | since 10:41 · was SELL CE | SELL CE | SELL CE | EITHER | PE 23,400 | CE 23,450 · at the wall · 0.65 S |
| 7 | 09-22 10:51 · 10:50 NIFTY 23500PE | DOWN | **SELL CE** | 2–3 | B S S S B | — | since 10:44 · was BUY PE | SELL CE | SELL CE | SELL CE | PE 23,350 | CE 23,450 · at the wall · 0.79 S |
| 8 | 09-22 13:47 · 13:47 NIFTY 23500PE | DOWN | **BUY PE** | 3–1 | B B · S B | — | since 13:47 · was BUY PE · sell refused | BUY PE | BUY PE | BUY PE | PE 23,350 | CE 23,400 · at the wall · 0.81 S |
| 9 | 09-23 09:17 · 09:17 NIFTY 23450CE | UP | **STAND ASIDE · led** | 0–1 | · · · S · | R3, R4cnc | since 09:17 | STAND ASIDE · led | STAND ASIDE | STAND ASIDE · led | CE 23,400 | not shown |
| 10 | 09-23 09:46 · 09:44 NIFTY 23450CE | UP | **STAND ASIDE · both** | 1–3 | · S S S B | R5, R1 | since 09:44 · was SELL PE | STAND ASIDE · both | STAND ASIDE | STAND ASIDE · both | CE 23,400 | PE 23,350 · K₀ (wall at the money, ITM side) · -0.09 S |
| 11 | 09-23 09:48 · 09:47 NIFTY 23400PE | DOWN | **SELL CE** | 2–3 | B B S S S | — | since 09:32 · was STAND ASIDE · led | SELL CE | SELL CE | EITHER | PE 23,400 | CE 23,400 · at the wall · 0.06 S |
| 12 | 09-23 09:59 · 09:59 NIFTY 23450CE | UP | **SELL PE** | 0–4 | · S S S S | — | since 09:59 · was STAND ASIDE · led | SELL PE | SELL PE | SELL PE | CE 23,400 | PE 23,350 · K₀ (wall at the money, ITM side) · -0.1 S |
| 13 | 09-23 10:18 · 10:17 NIFTY 23450CE | UP | **SELL PE** | 0–4 | · S S S S | — | since 10:17 · was BUY CE · sell refused | SELL PE | SELL PE | SELL PE | CE 23,400 | PE 23,350 · K₀ (wall at the money, ITM side) · -0.06 S |
| 14 | 09-23 10:32 · 10:32 NIFTY 23450CE | UP | **BUY CE** | 3–2 | B S S B B | — | since 10:23 · was SELL PE | BUY CE | BUY CE | EITHER | CE 23,400 | PE 23,400 · at the wall · 0.01 S |
| 15 | 09-23 11:06 · 11:05 NIFTY 23450CE | UP | **BUY CE** | 3–2 | B S S B B | — | since 11:05 · was SELL PE | BUY CE | BUY CE | EITHER | CE 23,400 | PE 23,400 · at the wall · 0.09 S |
| 16 | 09-23 11:31 · 11:29 SENSEX 74900CE | UP | **SELL PE** | 2–3 | B S S B S | — | since 11:26 · was BUY CE | SELL PE | SELL PE | EITHER | CE 74,900 | PE 74,700 · at the wall · 0.34 S |
| 17 | 09-24 09:41 · 09:41 SENSEX 74200PE | DOWN | **EITHER** | 2–2 | · B S B S | — | since 09:41 · was SELL CE | EITHER | EITHER | BUY PE | PE 74,200 | CE 74,300 · at the wall · 0.31 S |
| 18 | 09-24 10:18 · 10:17 SENSEX 74200PE | DOWN | **BUY PE** | 2–1 | · S · B B | — | since 10:17 · was SELL CE | BUY PE | BUY PE | EITHER | PE 74,100 | CE 74,300 · at the wall · 0.6 S |
| 19 | 09-24 12:31 · 12:29 SENSEX 74100PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | since 12:20 · was EITHER | BUY PE | BUY PE | BUY PE | PE 74,000 | CE 74,200 · at the wall · 0.55 S |
| 20 | 09-24 12:34 · 12:32 SENSEX 74000PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | since 12:20 · was EITHER | BUY PE | BUY PE | BUY PE | PE 74,000 | CE 74,200 · at the wall · 0.66 S |
| 21 | 09-24 12:43 · 12:41 SENSEX 74000PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | since 12:20 · was EITHER | BUY PE | BUY PE | BUY PE | PE 74,000 | CE 74,200 · at the wall · 0.6 S |
| 22 | 09-24 13:25 · 13:23 SENSEX 74000PE | DOWN | **SELL CE** | 1–2 | · S · B S | — | since 13:23 · was BUY PE | SELL CE | SELL CE | EITHER | PE 74,000 | CE 74,200 · at the wall · 0.6 S |
| 23 | 09-24 13:40 · 13:38 SENSEX 73900PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | since 13:35 · was EITHER | BUY PE | BUY PE | BUY PE | PE 73,900 | CE 74,200 · at the wall · 0.9 S |
| 24 | 09-24 13:42 · 13:41 SENSEX 73900PE | DOWN | **BUY PE** | 2–1 | · S · B B | — | since 13:35 · was EITHER | BUY PE | BUY PE | EITHER | PE 73,900 | CE 74,200 · at the wall · 0.98 S |
| 25 | 09-24 13:43 · 13:41 SENSEX 73900PE | DOWN | **BUY PE** | 2–1 | · S · B B | — | since 13:35 · was EITHER | BUY PE | BUY PE | EITHER | PE 73,900 | CE 74,200 · at the wall · 0.98 S |
| 26 | 09-24 13:44 · 13:44 SENSEX 73800PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | since 13:35 · was EITHER | BUY PE | BUY PE | BUY PE | PE 73,800 | CE 73,800 · K₀ (wall beyond one straddle) · 1.19 S |
| 27 | 09-24 13:53 · 13:53 SENSEX 73800PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | since 13:35 · was EITHER | BUY PE | BUY PE | BUY PE | PE 73,700 | CE 73,700 · K₀ (wall beyond one straddle) · 1.37 S |
| 28 | 09-24 13:56 · 13:56 SENSEX 73800PE | DOWN | **BUY PE** | 2–1 | · S · B B | — | since 13:35 · was EITHER | BUY PE | BUY PE | EITHER | PE 73,700 | CE 73,700 · K₀ (wall beyond one straddle) · 1.47 S |
| 29 | 09-24 14:22 · 14:20 SENSEX 73800PE | DOWN | **EITHER** | 2–2 | B S · B S | — | since 14:14 · was SELL CE | SELL CE | SELL CE | BUY PE | PE 73,600 | CE 73,700 · K₀ (wall beyond one straddle) · 1.52 S |

**The words at her 29 entries:**

| word | entries |
|---|---|
| BUY | 16 |
| SELL | 7 |
| EITHER | 2 |
| STAND ASIDE | 3 |
| could not check | 1 |

**Silent at 4 of 29.**
- **Every BUY and SELL at her entries was named on the count;** none was named by refusal.
- **The 3-minute close changed four entries** against the every-minute read:
  - #3: EITHER → SELL CE;
  - #5 and #6: SELL CE → BUY PE, because the 10:41 close stands until 10:44. So the 10:41 / 10:42 flip rev 0a showed at her
    entries is gone;
  - #29: SELL CE → EITHER.
- **Against rev 0a:** the same four. No entry word moved by S1, R4 or Q3 alone.

**What each leg did afterwards, in R-multiples on their shared line** (M1). Each leg's P&L over the next 30 finished minutes,
from her read minute, is divided by its PLAN §2.1 premium at risk to L at that minute, on [I] greeks. G = the long R − the
short R. Then comes the sold leg under the window, and the writer's word (§B) on it. The folds are in seller points at the
fold.

| # | BUY leg R +30 | SELL leg R +30 | G | index 30-min move vs d | the sold leg: rev 5 B · §C YES · §C NO (seller pts at the fold) | sold leg to 15:29 | writer word · 30 min · to 15:29 |
|---|---|---|---|---|---|---|---|
| 1 | | | | | could not check | | |
| 2 | 0.16 | 0.51 | -0.35 | +13.0 with | 09:41 r6 +0.0 · 09:41 r6 +0.0 · 09:41 r6 +0.0 | -44.3 | NO · neither · stop |
| 3 | 1.86 | 0.61 | 1.25 | +50.6 with | 14:14 r3 +15.55 · 14:14 r3 +15.55 · 14:14 r3 +15.55 | 32.45 | WAIT · neither · target · line beyond strike |
| 4 | 0.25 | 0.13 | 0.12 | +5.6 with | 14:14 r3 +8.15 · 14:14 r3 +8.15 · 14:14 r3 +8.15 | 25.05 | WAIT · neither · neither · line beyond strike |
| 5 | -0.24 | 0.04 | -0.28 | +2.5 with | 14:14 r3 +5.4 · 14:14 r3 +5.4 · 14:14 r3 +5.4 | 22.3 | WAIT · neither · neither · line beyond strike |
| 6 | -0.05 | 0.06 | -0.11 | +4.5 with | 14:14 r3 +6.9 · 14:14 r3 +6.9 · 14:14 r3 +6.9 | 23.8 | WAIT · neither · neither · line beyond strike |
| 7 | -0.38 | -0.05 | -0.33 | -20.7 against | 14:14 r3 +3.9 · 14:14 r3 +3.9 · 14:14 r3 +3.9 | 20.8 | WAIT · neither · neither · line beyond strike |
| 8 | -4.76 | -9.3 | 4.54 | -51.2 against | 14:14 r3 -17.25 · 14:14 r3 -17.25 · 14:14 r3 -17.25 | 14.5 | WAIT · target · target |
| 9 | -0.05 | no strike | — | -5.0 against | — | — | — |
| 10 | -0.11 | 0.19 | -0.3 | -3.2 against | 09:46 r6 +0.0 · 09:46 r6 +0.0 · 09:46 r6 +0.0 | 31.25 | NO · stop · stop |
| 11 | -0.63 | -0.42 | -0.21 | -19.7 against | 10:19 r6 -10.8 · 10:19 r6 -10.8 · 10:19 r6 -10.8 | -17.45 | GO · neither · stop · line beyond strike |
| 12 | 0.62 | 0.66 | -0.04 | +21.4 with | 10:05 r6 +0.95 · 10:05 r6 +0.95 · 10:05 r6 +0.95 | 29.95 | WAIT · neither · target · line beyond strike |
| 13 | 0.58 | 0.42 | 0.16 | +27.2 with | 13:32 r3 +12.4 · 13:32 r3 +12.4 · 13:32 r3 +12.4 | 22.7 | GO · neither · target · line beyond strike |
| 14 | 0.25 | 0.25 | 0.0 | +17.0 with | 13:32 r3 +11.65 · 10:35 r3s -2.15 · 10:35 r3s -2.15 | 23.3 | GO · neither · target · line beyond strike |
| 15 | 0.11 | 0.02 | 0.09 | +8.5 with | 13:32 r3 +1.5 · 13:32 r3 +1.5 · 13:32 r3 +1.5 | 13.15 | GO · neither · neither · line beyond strike |
| 16 | 0.08 | 0.06 | 0.02 | -3.3 against | 13:29 r3 +5.3 · 13:29 r3 +5.3 · 13:29 r3 +5.3 | 29.1 | GO · neither · neither · line beyond strike |
| 17 | 0.03 | 0.09 | -0.06 | +5.5 with | 10:43 r4 +29.2 · 10:43 r4 +29.2 · 10:43 r4 +29.2 | 129.15 | GO · neither · target · line beyond strike |
| 18 | -0.24 | -0.08 | -0.16 | -19.2 against | 10:43 r4 +1.6 · 10:43 r4 +1.6 · 10:43 r4 +1.6 | 101.55 | WAIT · neither · target · line beyond strike |
| 19 | 0.44 | 0.05 | 0.39 | +31.7 with | 14:38 r3 +66.2 · 14:45 r4 +70.6 (held 14:38) · 14:38 r3 +66.2 | 99.35 | WAIT · neither · target |
| 20 | -0.37 | -0.27 | -0.1 | -38.0 against | 14:38 r3 +58.2 · 14:45 r4 +62.6 (held 14:38) · 14:38 r3 +58.2 | 91.35 | WAIT · neither · target |
| 21 | -0.35 | -0.08 | -0.27 | -21.7 against | 14:38 r3 +63.5 · 14:45 r4 +67.9 (held 14:38) · 14:38 r3 +63.5 | 96.65 | WAIT · neither · target |
| 22 | 6.07 | 1.96 | 4.11 | +302.0 with | 14:38 r3 +49.35 · 14:45 r4 +53.75 (held 14:38) · 14:38 r3 +49.35 | 82.5 | GO · target · target |
| 23 | 1.85 | 0.51 | 1.34 | +216.1 with | 14:38 r3 +26.2 · 14:45 r4 +30.6 (held 14:38) · 14:38 r3 +26.2 | 59.35 | WAIT · neither · target |
| 24 | 1.55 | 0.48 | 1.07 | +208.5 with | 14:38 r3 +26.2 · 14:45 r4 +30.6 (held 14:38) · 14:38 r3 +26.2 | 59.35 | WAIT · neither · target |
| 25 | 0.83 | 0.33 | 0.5 | +169.1 with | 14:38 r3 +22.3 · 14:45 r4 +26.7 (held 14:38) · 14:38 r3 +22.3 | 55.45 | WAIT · neither · neither |
| 26 | 0.52 | 0.29 | 0.23 | +107.1 with | 14:38 r3 +42.9 · 14:38 r3 +42.9 · 14:38 r3 +42.9 | 175.9 | WAIT · neither · target · line beyond strike |
| 27 | 0.39 | 0.29 | 0.1 | +120.4 with | 14:38 r3 +11.2 · 14:02 r3s +4.15 · 14:02 r3s +4.15 | 192.4 | WAIT · neither · neither · line beyond strike |
| 28 | 0.16 | 0.16 | 0.0 | +63.3 with | 14:38 r3 -10.5 · 14:02 r3s -17.55 · 14:02 r3s -17.55 | 170.7 | WAIT · neither · neither · line beyond strike |
| 29 | -0.71 | -0.19 | -0.52 | -154.8 against | 14:38 r3 -35.15 · 14:35 r3s -14.7 · 14:35 r3s -14.7 | 146.05 | WAIT · neither · neither · line beyond strike |

**In rows, not rates:**
- **When her direction was right** (the move went "with", 18 scored entries), the buy leg's R was the higher at 11, the lower
  at 5, and equal at 2 (#14, #28).
  - The five lower: #2, #5, #6, #12, #17 (G −0.35 / −0.28 / −0.11 / −0.04 / −0.06).
  - Her 09-24 afternoon puts: #22–#24 carried G +4.11 / +1.34 / +1.07, and #25–#28 carried G +0.5 to 0.0.
- **When it was wrong** ("against", 9 scored), the sell leg's R was the higher at 7 (#7, #10, #11, #18, #20, #21, #29).
  - At #8 the line sat 9.8 pts away. Both legs lost many R (−4.76 and −9.3), and the buy leg lost less.
  - At #16 (a 3.3-pt move) both made a little.
- **The 09-24 afternoon K₀ sales** (#26–#29, the wall beyond one straddle):
  - #27 and #28 (CE 73,700) were folded by rule 3s at 14:02, and #29 at 14:35, all before rev 5 B's 14:38 line fold. CE 73,700
    ended at 0.15.
  - #26 (CE 73,800) folded at 14:38 by rule 3.
- **The writer's word on the 27 sell legs** (#9 had no sale):
  - "line beyond strike" is flagged at 17 (§B.1). Near-ATM sales put the line beyond the strike.
  - At 30 minutes: target 2 (#8, #22), stop 1 (#10), neither 24.
  - To 15:29, shown: target 14, stop 3.

### D.5 Her 09-25 NIFTY entries (rev a)

The facts at the 3-minute close before each entry (09:33, 11:59 and 12:02) are **not in the frozen record**. The words below
are read at the read minute, from the same pieces rev 0a used [I proxy]. No 09-25 premium was frozen, so fact 5 cannot read,
and **R4 refuses SELL at all three**.
- That R4 is the frozen record's gap, not the market's. Live, fact 5 would read.

| entry (read) | dir | the word (rev a) | b–s | facts | what moved against rev 0a |
|---|---|---|---|---|---|
| 09:36 PE (her words; the saved 09:35 check) | DOWN | **STAND ASIDE · led:** "the facts favour selling, 3 to 0, but selling is refused: R4 — could not check: no premium frozen" | 0–3 | · S S S ? | M4: SELL CE → STAND ASIDE. This goes against the one in-sample row it touches: the index never came within 95 pts of CE 23,200. |
| 12:01:21 CE (marked) | UP | **BUY CE · selling refused (R4)** | 1–1 | B · · S ? | S1: ROOM went FOR BUY → NEITHER (the line 1.65 pts away, inside one candle of 4.9). M4 then names BUY by refusal at a tie. |
| 12:05:28 PE (marked) | DOWN | **BUY PE · selling refused (R4)** | 2–1 | B B · S ? | The word is unchanged; it is now named by refusal. |

### D.6 The seller on 09-24 under rev a's §C: signed R, rule 3s, both answers to §C.7

These are her 13 put entries read as sales of the call at the same strike (the handoff's replay).
- **At 14:38** the ATM straddle was 321.6 pts [M] and the index closed 73,764.02. Every sold call was out of the money, so
  signed R equals the old unsigned R.

| sold call (entries) | at entry | rev 5 B (as built) | **§C, YES** | **§C, NO** | at 15:29 |
|---|---|---|---|---|---|
| 74,200 (09:41, 10:18) | 174.7 · 138.6 | 10:43 rule 4, at 138.2 | the same | the same | 0.15 |
| 74,100 (12:31) | 138.0 | 14:38 rule 3, at 47.55 | **held at 14:38** (R +336 > S 321.6). **P_max 53.25 while held**, then 14:45 rule 4 at 42.45 | 14:38 rule 3, at 47.55 | 0.15 |
| **74,000 (12:34, 12:43)** | 171.7 · 178.1 | 14:38 rule 3, at 67.75 | **13:05 rule 3s, at 191.65**: the 13:03–13:05 bar closed 25.4 pts through 74,000 | **the same 3s fold** | 0.2 |
| 74,000 (13:25) | 157.05 | 14:38 rule 3, at 67.75 | the same (R 236 ≤ 321.6) | the same | 0.2 |
| 73,900 (13:40, 13:42, 13:43) | 157.65 · 154.25 · 140.4 | 14:38 rule 3, at 95.9 | the same (R 136) | the same | 0.1 |
| 73,800 (13:44, 13:53, 13:56, 14:22) | 176.0 · 145.05 · 127.65 · 107.45 | 14:38 rule 3, at 133.1 | the same (R 36) | the same | 0.1 |

**The result, stated against itself:**
- **The reach still does not rescue 09-24.** Under YES it holds one sale (74,100) for seven minutes, and its premium rose to
  53.25 above the break's 47.55 before rule 4 folded it at 42.45. Under NO it folds at 14:38 as today.
- **Rule 3s costs on the record.** It folds the two 74,000 sales at 13:05 at 191.65, where rev 5 held them to 14:38 at
  67.75, and both expired at 0.2. The fold came on a 25-pt close through the strike, which is the kind of one-candle poke rev
  5 B's buffer exists to ignore.
- **3s at every close is a zero-buffer stop at the strike.** On the grid and at her entries it also folds at-the-money sales
  on the first close past the strike (§D.7). This is disclosed, not tuned. Its scope is §H.3.

### D.7 The grid: scorability (M1), the writer population (M6), held breaks (M9) and 3s

- **Units:** 216 (nine index-days × two directions × twelve closes from 09:44).
  - **Words at the units:** SELL 55 · BUY 41 on the count and 36 by refusal · EITHER 35 · STAND ASIDE 49 (35 both · 14 led).
- **G (R-multiples) scored at 160 of 216.** Not scored: no sell strike 44, no premium 6, no greeks 6.
- **The writer population (ii),** at the 165 units with a sell strike:
  - **words:** GO 60 · WAIT 81 · NO 24; in the stratum 133;
  - **at 30 minutes:** target 24 · stop 33 · neither 82 · not scored 26;
  - **to 15:29 (shown):** target 49 · stop 48 · neither 42 · not scored 26.
  - **That is 57 resolved at 30 minutes over three sessions,** about 19 a session. P1-W's 15 GO and 15 WAIT inside the stratum
    are within reach in 10–30 sessions, which rev 0's her-presses-only population never was.
- **The window on those 165 sold legs (§C, YES)**, the first FOLD:

  | first FOLD | legs |
  |---|---|
  | rule 3 | 64 |
  | rule 6 | 48 |
  | rule 4 | 27 |
  | **rule 3s** | **13** |
  | none by 15:29 | 13 |

- **Rule 3s on the grid** fired at 13 legs. It fired before rev 5 B's fold at 8, and at the same minute at 5.
  - Of the 8, the premium at the 3s fold was lower than at rev 5's fold at 7 and higher at 1.
  - One SENSEX 09-24 ATM call (73,700) folded at 14:35 by 3s and expired at 0.15.
- **Held breaks, W-R's unit, keyed (index, bar, L, side):** two distinct on the grid, both SENSEX 09-24.
  - **14:38 CE:** the 74,200 and 74,300 legs, and the handoff's 74,100. Every leg folded at 14:45 by rule 4. P_b → P_x (P_max)
    per strike:
    - 74,100: 47.55 → 42.45 (53.25);
    - 74,200: 33.3 → 28.9 (37.05);
    - 74,300: 23.5 → 19.9 (26.4).
  - **15:29 PE 73,500:** held at the last close (R 80.5 > S 20.05), and it ended at 0.15.
  - **None counts toward W-R.**

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
| the word | refusals, then the count; a lead of 2 or more BUY / SELL, of exactly 1 LEANS, a tie EITHER, a tie with a leg refused STAND ASIDE; `named_by` and `strength` kept apart | **named choices** (M2; rev b) |
| strikes | BUY ATM; SELL at the wall within one straddle, else ATM | side log `atm.k`; §C's unit (Q3) |
| expiries | both legs the chain's resolved expiry; S of her option's own expiry | `upstox_instruments.resolve` (S8, M8) |
| writer facts | Right now · Your wall · Cushion (noise, the strike range, X vs P) · Time is paying | VALIDATE rev 2 §1.2 / §1.3; PLAN §2.1; §A fact 5 |
| writer target · horizon | P − X, 1:1 in premium · 30 min judged, to 15:29 shown | PLAN §2.1; VALIDATE §3's 30 (M6) |
| the reach | signed R against S of her expiry, scale 1× | **named choice**; seller-desk design's unit; ≈ 0.2 Δ [I] |
| rule 3s (rev b) | a close beyond k ± B_k, always; B_k = rev 5 §A.2's B read at her entry, frozen, with its fallback | rev 5 option B, signed |
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
- **Count units** are those where neither leg was refused. Rev b splits them into five words, each its own population:
  **BUY**, **LEANS BUY**, **EITHER**, **LEANS SELL**, **SELL**. LEANS is never pooled with BUY / SELL.
- **Refusal units** are their own rows, with their codes and their strength, never pooled with count units:
  - BUY / LEANS BUY · selling refused;
  - SELL / LEANS SELL · buying refused.
- **STAND ASIDE · led** and **STAND ASIDE · tie** are judged, each on its own count. **STAND ASIDE · both refused** is shown,
  not judged: it re-tests rev 4 B4 and VALIDATE P2 (the entry FOLD), which judge it already.

**The claims:**
- **BUY and LEANS BUY, each on its own:** the median G at its units is **larger** than at the count units that do not
  point to buying (EITHER, LEANS SELL and SELL).
- **SELL and LEANS SELL, each on its own:** the median G at its units is **smaller** than at the count units that do not
  point to selling (EITHER, LEANS BUY and BUY).
- **Shown, not judged:** the medians in order, BUY ≥ LEANS BUY ≥ EITHER ≥ LEANS SELL ≥ SELL. That shows whether the strength
  the word prints is real.
- **EITHER:** the median |G| at EITHER units is smaller than at BUY units, **and** smaller than at SELL units, each separately
  (S2). The same against LEANS is shown.
- **STAND ASIDE · led and STAND ASIDE · tie, each on its own:** the median of max(long R, short R), the better leg, is lower
  at its units than at count units.
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
- **BUY, SELL, LEANS BUY or LEANS SELL:** withdrawn. Where it would have been named, the read says "EITHER — {word}
  withdrawn on {date}", with its count.
- **EITHER:** a tie prints the count and no word.
- **STAND ASIDE · led or · tie:** the refusals are re-registered; until then the word carries "its falsifier failed on
  {date}".
- **Short of 15 by 30 sessions:** inconclusive, and the word stays DRAFT.

**Her presses and entries** (the read when a trade was in front of her) are shown, never judged, and never pooled with the
grid.

### E.3 The logs, additive, write-once (`hold_log`'s discipline)

**`data/hold/expr_<day>.jsonl` (new).** One row per 3-minute close, per index, per direction: 750 rows a day. It is written
live by `_hold_tick` and completed by the close-time import.
- **The backfill runs off the request path** (review Q5): about 750 expression reads, each with two window reads. The 09-18
  wedge is the precedent.

```
{kind: "expr", day, t, idx, d, word, strength: "lead"|"leans"|"tie", lead, named_by: "count"|"refusal", refusal: [codes],
 since, was: {word, until},
 nb, ns, facts: [[name, state, absence, text]...],
 buy:  {side, k, expiry, px, delta, gamma, entry},
 sell: {side, k, expiry, px, delta, gamma, entry, placement: "wall"|"atm", wall: {k, state, r_w}|null, r_over_S},
 S, line, noise, regime_board, drag, expiry_line, blind: [...], word_1m, unit: bool, prereg: "expr-b", tag: "I"}
```

On a unit close, an **outcome row** is written once its 30 minutes have finished:

```
{kind: "expr_outcome", day, t, idx, d, word, strength, lead, named_by, refusal,
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
- `fold_rule: "3r" | "3s"`, and `strike: {k, B_k, B_at, level}` from entry (rev b);
- `writer_clause: "reach-b"`;
- `expiry_day: her §C.7 answer`.

`prereg` keeps its rev 5 value, so buyer rows do not change label.

**Day state:** nothing new. R, S and P_max are read from the day's chain record, which a restart re-reads.

### E.4 The forward clocks

| clause | changed here? | its forward record |
|---|---|---|
| the expression, §E.2 | new | Starts at its first session after the code (`prereg: "expr-b"`). |
| VALIDATE, buyers (P1, P2) | no | **Continues.** The `expr` key is additive. |
| VALIDATE, writers, (i) presses and (ii) grid | new | Starts at the first session after the code (`rev: "2W"`). Earlier writer presses (`word: null`) are rev 2's record, never pooled. |
| the window, buyers | no | **Continues.** |
| the window, writers (W1, W2, the writer clauses 1–7) | yes: rule 3 for writers, plus 3r and 3s | **Reset for writers only** (`writer_clause: "reach-b"`). Rev 5's writer rows stay rev 5's record. |
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

1. **THE EXPRESSION**, one word at 88 px: **BUY CE** · **SELL PE** · **LEANS BUY CE** · **LEANS SELL PE** · **EITHER** ·
   **STAND ASIDE**.
   - **LEANS is part of the word, not a caption.** It is set in the same Barlow at half the size, on the line above the leg
     ("LEANS / BUY CE"), so a one-fact word can never be read as a lead.
   - Under it, one line: **"since 11:44 · was EITHER until 11:44 · read at the 11:44 close"**.
   - Then the count: "3 for buy · 1 for sell · 1 neither — of 5, a count, not odds", then DRAFT.
   - **A word named by refusal says so in the word's own line, in the caution ink:** "BUY CE — selling refused (R4 — could
     not check: …)".
   - **EITHER reads "the facts split 2–2".**
   - **STAND ASIDE says which:** both refused; "the facts favour selling, 3 to 0, but selling is refused: …"; or "the facts
     tie 1–1, and selling is refused: nothing leads to buying".
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
    FOLD at the first 3-min close with your strike within one straddle, or through your strike by more than one candle".
  - **No row says "safe", "won't reach", or anything like it.**
- **The strike row, always, for writers:** "your strike {k} · breaks on a 3-min close {above / below} {k ± B_k} — one
  median candle, {B_k} pts [M], read {B_at} (rule 3s) — {R} pts out".
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

**`silence_detail.json`** (review M5c) **was written, but into the repo root, not the scratch folder.** `expr.py` changes the
working directory into the repo, so the inline script's relative path landed there.
- It was found at 01:38 by `git status` and moved into the scratch folder, with a second stray file of the same cause
  (§D.0).
- The rev a text first said "never written". That was wrong, and it is corrected here.
- Rev a's run writes its own copy, and rev 0a's is kept.

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
- **S5:** the co-occurrence is disclosed (§D.3).
- **S6:** the parity argument is in §A.1 / §A.3, and fact 5's sentence names the move's sign.
- **S7:** fact 5's rows, and the claims with fact 5 dropped, are shown forward.
- **S8:** each leg's expiry, R/S and Δ are printed, and on 0DTE the setup-table row (printed, not a refusal).
- **S9:** every VALIDATE section amended is listed.
- **S10:** the line at or beyond the strike is flagged ("state it"), in the Cushion and in the R-multiple. The first text
  read "could not check"; §G's 01:31 entry says why that changed.
- **S11:** what the 30-minute writer test mostly tests.
- **S12:** safety copy is removed and banned.
- **S13:** W-R is keyed (index, bar, L, side), median across strikes, with per-strike rows.
- **S14:** 3r and 3s are line-family stamps.
- **S15:** closed by 3s.
- **S16:** rev 4 §1's principle is stated as changing for writers.
- **S17:** what the rule is, where she signs (§C.1), and the held loss.

**Rev a's fingerprint** is in §D.0, taken before its run.

**01:31, after rev a's first fingerprint (01:28) and before its full run: two inconsistencies between rev a's own rules,
found in a smoke test.** The smoke test read four SENSEX 09-24 minutes: 09:20, 12:31, 13:44 and 14:22, DOWN.
1. **A sale could be placed in the money.** "ATM" by rounding, and a wall "at" spot inside SHIELD's half-step tolerance, can
   sit up to half a step in the money. The smoke test placed CE 73,600 with spot at 73,636. Rule 3s would then fold the sale
   at its first close.
   - **Fixed:** a sale is never placed in the money. K₀, the nearest strike at or beyond spot on the OTM side, replaces
     "ATM", and an in-the-money "at" wall hands the sale to K₀ (§A.5).
   - SHIELD's fact is unchanged.
2. **S10's "could not check" collided with the ATM placement.** An at-the-money sale always has its danger line beyond its
   strike, so the writer's Cushion and the R-multiple would read blind on exactly those sales.
   - **Fixed:** the review's other S10 option, "state it". X is computed and flagged as least trustworthy there (PLAN §7's
     own caveat).
- **Both are principle fixes, not tunings.** The smoke test's four words had been seen when they were made.
- The text was fingerprinted again before the full run (§D.0).

**01:32–01:40:** rev a's full run (`run_a.py`), then the run-length and grid 3s extras.

**01:38: the stray files** were found and moved (§D.0). No rule moved.

**01:40–01:55: §D written after the run.** Its "in rows" prose was checked against the tables before it went in, and three
miscounts in the first wording were fixed then:
- 11 of **18**, not 17;
- the G range of the 09-24 puts;
- the K₀ fold rows are #27–#29, not #26–#29.

No rule moved after the run. **Rule 3s's cost (§D.6, §D.7) is disclosed, not tuned; its scope is raised in §H.3.**

**Rev b, 2026-09-26 01:47 IST (clock). Two trader decisions, made on her standing delegation, on principle, and made after
rev a's rows were seen.** Both were conveyed by the coordinator.

1. **The strike rule inherits rev 5 option B's buffer.**
   - **The rule:** a writer is FOLDed on a 3-min close through her strike by more than one frozen median 1-minute candle, at
     every close, held or not. It uses exactly rev 5 §A.2's B: its measure, window, freeze, clamp (which never binds, since
     the strike never trails) and fallback. No new number.
   - **Principle:** the line rule she signed says a close inside one candle is noise. The strike is a line. A zero-buffer
     strike stop contradicted signed rev 5.
   - **What had been seen:** rev a's §D.6 / §D.7, where the zero-buffer 3s folded the 09-24 74,000 sales on a 25-pt poke, and
     at-the-money sales on their first close past the strike.
2. **The word shows its margin.** The words are BUY / SELL for a lead of 2 or more, LEANS BUY / LEANS SELL for a lead of
   exactly 1, EITHER on a tie, and STAND ASIDE when refused.
   - LEANS is its own word in the logs and the falsifiers, a separate population never pooled with BUY / SELL.
   - **What had been seen:** rev a's §D.2, where half the BUY / SELL words stood on a single fact.
   - **The drafter's reading, flagged:** a tie with one leg refused reads STAND ASIDE · tie. Rev a named the open leg there.
     It is for the trader to confirm (§H.2).

**Rev b also fixes the scratch folder's defect:** `expr.py` no longer changes its working directory, and every script writes to
absolute paths inside `expr/`. Nothing can land in the repo again.

**Fingerprinted before its run** (§D.0). §C.7 stays the question, unanswered.

---

## H. What this draft could not resolve

1. **The expiry-day question (§C.7)** is hers. §C cannot be signed without it.
2. **The word's margin: decided in rev b.** A one-fact lead reads LEANS, with no threshold number (§A.4).
   - Still open: the tie with one leg refused reads STAND ASIDE. That is the drafter's reading of "STAND ASIDE when refused",
     for the trader to confirm.
3. **Rule 3s's scope: decided in rev b.** Rev 5 B's own buffer, at every close (§C.2). Rev a's cost is in §D's rev a history,
   and rev b's re-run is in §D.6 and §D.7.
4. **ROOM leans BUY** where no holding wall is in the way and the line is outside one candle. It is inherited from VALIDATE's
   target, and judged forward.
5. **Rule 3s folds a sale made more than one candle in the money at its first close.** §A.5 never places one, but a press
   at an in-the-money strike is her own. A deliberate in-the-money sale is not supported by this window; hers to say if it
   should be.
6. **Only closes are read.** A bar can carry price through her strike and back (§C.3). P_max and the held loss show it; they
   do not prevent it.
7. **Her "90-minute write guard"** has no text in the repo. **IV against realised vol** is not computed per minute. Neither is
   used.
8. **The disclosure's inputs** are partly [I]:
   - Black-76 greeks, not the broker's;
   - nearer-only fronts on 09-22 and 09-23;
   - [I] candles on two 09-24 indices;
   - 09-21 and the 09-25 premiums not frozen;
   - for 09-25, the facts at the 3-minute close before each entry not frozen (§D).
   The forward rows are the only evidence.
9. **The owed code changes when she signs** (none made here):
   - the `expr_<day>` log at the 3-minute close, with the backfill off the request path;
   - the outcome key's `role`, with `_hold_tick`'s `has()` changed with it;
   - the writer rows' `reach` / `held` / `3r` / `3s` keys, and the expiry-day answer;
   - PLAN §2.6's display, change-log line and §1f hash;
   - **tests:**
     - the word order and `named_by`;
     - R4 failing closed;
     - ROOM's noise step;
     - the K₀ placement (never in the money; the far wall; the in-the-money "at" wall);
     - signed R and 3s, including a held writer whose close lands through the strike by more than S;
     - S of her own expiry;
     - the held loss;
     - W-R's total test;
     - the outcome key collision.
