# PRE-REGISTRATION DRAFT — THE EXPRESSION: BUY THE OPTION, OR SELL THE OTHER SIDE; THE SELLER IN VALIDATE; THE SELLER IN THE WINDOW (written 2026-09-26 00:16 IST by the clock, before any run, NOT SIGNED, UNTESTED)

**Status.** This is a DRAFT. Nothing below is a result. Nothing here is in force until Mary signs it, after an adversarial
review.
- §A–§C and §E–§F were written before any rule below was run on any minute of any day, and fingerprinted (§D.0) before the
  first run.
- **One fact moved after the first run:** fact 5, PREMIUM (rev 0a). The reason is a principle (rev 4 §8's one-contract
  rule), but the counts were in view when it moved. §G records when and why, and §D shows both versions.
- Two clarifications were made while implementing and disclosing; §G lists them.
- §D was added after the runs.

**What it amends, and what it leaves alone.**
- It **adds** one read, THE EXPRESSION (§A), to the Validate tab.
- It **amends** VALIDATE rev 2 §1.6 for a writer only (§B): a SELL press gets GO / WAIT / NO.
- It **amends** the window's rule 3 for a writer only (§C). This is the item rev 4 §9.2 left open ("a wider structure for
  writers is hers to register or reject").
- **Buyers are untouched.** No buyer rule of the window (rev 4, amended by rev 5 option B), THE PLAN (rev 3a) or VALIDATE
  (rev 2) moves by one word. Buyer clocks do not restart (§E.4).

**Her words, 2026-09-25:**
> "i buy and sell option as per the market condition if its better to sell options than i will sell options with out any
> worry . so has to both ways so if any trade pops up engine should be able to tell me weather to buy any option make sense
> or selling the otherside because let say market is going up either i can go for call buy but it engine things its better
> to sell the put at this location than i would sell option . . So this engine has to be good in that too . Think yourself
> as the trader and you are building the for youself"

And, 2026-09-24: *"identifying direction is never my problem but holding a trade is"*.

**So the question this answers is narrow.** Direction is hers. Given her direction at a minute, the read answers one
question: **which leg expresses it: buy the option in the direction, sell the option on the other side, either, or
neither.** It is not a second VALIDATE. VALIDATE still answers "should I take it" for each leg. It does not re-decide
direction either: that was the read that went silent.

**What had been seen when this was written, so nobody has to guess:**
- every signed text named in the HANDOFF, the two reviews, and both "better trade" reads with their reports;
- `hold.py`, `plan.py`, `validate.py`, `board.py`, `trendbox.py`, `fronts.py`, `drag.py`, `gamma.py`, and the heads of
  `surface.py` / `desk.py`;
- the frozen fixtures' structure (which fields exist on which day);
- the 09-24 seller replay's output (`replay_0924_writer.py`, this session): the window folded 11 sold calls at 14:38, by
  rule 3, and 2 at 10:43, by rule 4. The CE premiums at 14:38 were 47.55–133.1, and every one ended at 0.1–0.2.
- **Not seen before writing:** any expression word, fact count, straddle, reach or writer word at any minute. The one
  exception is the 14:38 premiums just listed. §C was written knowing them, and is flagged so (§C.6).

---

## A. THE EXPRESSION READ

### A.1 The question, and why it speaks

Given a direction `d` (UP or DOWN), the read compares two legs at the finished minute `t`:
- **LONG** the option in the direction: CE for UP, PE for DOWN;
- **SHORT** the option on the other side: PE for UP, CE for DOWN.

**The two legs share one thesis.** In rev 4 §1's table, a long CE and a short PE have the same `d` (+1). So do a long PE
and a short CE (−1). They have the same line, the same payers and the same holders. They differ in exactly four places:
- **speed.** A buyer rents the move and needs it fast ("the drag number"). A writer needs only its absence.
- **risk shape.** A buyer's loss stops at the premium. A writer's loss is open-ended, so she needs a wall behind her strike.
- **what a range does.** A range taxes a buyer and pays a writer (her doctrine: a confirmed pin is a seller's gear).
- **which rent is winning.** A long straddle gains when the move out-pays the decay, and a short one when time wins. Her
  own words from the band-rotation spec: *"both legs decaying together … is just theta on a dead day"*.

The read counts facts that answer those four differences, and **only** those. Facts that hurt both legs alike (flow
against, trend against, the thesis broken) are not counted. Each leg's own entry check already carries them (§A.3).

**Why it speaks where the "better trade" reads did not.** Both round-3 reads gated a day word on REGIME, which needs the
price rows **and** the OI read to agree. OI reads BOTH LEAVING on about half of every day, so the gate was shut 9 minutes
in 10. This read differs in three ways:
- **nothing gates it except the two legs' own refusals** (§A.3);
- **the price rows are one counted fact** (REGIME, §A.2 fact 4). They are the side read of rev 4 §10, which already speaks
  price-led;
- **the question is relative.** A minute with little evidence still separates the legs whenever one fact does. A tie reads
  EITHER, which is a word: "both are open; nothing separates them".

It is silent (STAND ASIDE, or "could not check") only when both legs are refused by their own rules, or when a refused
leg has more facts for it than the leg that is not refused. §D reports how often that happened on her days, as counts. It
is a disclosure, not a target.

### A.2 The five facts, each FOR BUY · FOR SELL · NEITHER

Each fact is read at `t`, every input cut to `t`, from objects the app already computes.
- Each is tagged [M] or [I].
- A NEITHER that is an absence carries its kind: "checked, none", "could not check" or "not shown". A NEITHER that is a
  read says what was read.
- The count is "n for buy · n for sell · n neither — of 5, a count, not odds".

| # | fact | FOR BUY | FOR SELL | NEITHER |
|---|---|---|---|---|
| 1 | **SPEED**: is anyone being forced your way right now? | the window's "paid" at `t` (rev 4 §3 rule 5; VALIDATE rev 2 §1.4) | — (no sell state) | nothing paying at `t` (*checked, none*) · OI blind (*could not check*) |
| 2 | **ROOM**: the next wall that holds, against your line | no wall in the way, or the target is at least as far as the line | the target is nearer than the line | the line or the walls cannot be read (*could not check*) |
| 3 | **SHIELD**: is the wall behind the sale defended? | — (no buy state) | that wall is BUILDING with a build today | that wall is STALLED or UNWINDING (a read) · no such wall, or OI blind (each also a refusal, §A.3) |
| 4 | **REGIME**: the price rows, the side read (rev 4 §10.1) | the side read names your direction's side | "no side" | the side read names the other side (a read) · a row forming (*could not check*) |
| 5 | **PREMIUM** (rev 0a, §G): whose rent won over the last 15 minutes, on one fixed straddle | the straddle rose: **the move out-paid time** | the straddle fell: **time won** | both legs rose (a read; it refuses SELL, §A.3) · a premium missing, or before 09:30 (*could not check*) |

**Max four each way.** SPEED is buy-only and SHIELD is sell-only; the other three are two-sided. So neither leg has more
facts available to it. Which facts lean on real days is §D.1's to show.

**1 SPEED [M on I].** It is exactly VALIDATE rev 2 §1.4's "Paying", read for the long leg. That is the window's own
quiet-clock "paid" at `t`, off `now.clock.paid_last == t`:
- the payers' nearer front is UNWINDING (not both leaving), or
- a payers'-side fold is live (rev 5 §C keeps a live fold as "paid" for the clock), or
- flow is with you by the strict rule (`board.aggression`).

*Why it favours buying:* a forced move is a fast move, and speed is the only thing that beats the rent. A writer is paid
whether the move is fast or absent.

*Why there is no sell state:* "nothing paying" is one minute's absence. Payers adding in the way is the ROOM fact's wall.
So a sell state here would count that wall twice.

**2 ROOM [M].** This is VALIDATE rev 2 §1.3's target and line distance, unrounded, as `validate.geometry` computes them.
- **The target:** PLAN's rung re-read with every GIVING WAY wall removed. That is the nearest sized payers'-side front
  beyond the index that is DEFENDED or STALLED; else the session extreme beyond; else none.
- **The line:** |close − L|, rev 5's L itself, not its break level.
- **The reading:**
  - target ≥ line, or no target: FOR BUY ("room to run");
  - target < line: FOR SELL ("the move is capped at {k}, {r} pts away, nearer than your line at {s}. A buyer's reward is
    shorter than her risk; a writer does not need the move").
  - A tie is FOR BUY, as VALIDATE's tie is WITH.

*One wall, one fact.* A wall that is giving way is SPEED's wall. ROOM never reads it, because VALIDATE's target removes
it. So no strike is read twice.

The noise half of VALIDATE's Room ("your line is inside one candle") is **not** counted here. It is the same line for both
legs, so it separates neither. It stays in each leg's own VALIDATE word.

**3 SHIELD [M].** It reads **the wall behind the sale**:
- the nearest to spot of the sold side's §1d top two (`fronts.read`, the running peak, rev 4 §2's ranking);
- that sits **at or beyond spot** on the sold option's out-of-the-money side: a PE front at or below spot for a PE sale, a
  CE front at or above spot for a CE sale. "At" is within half a strike step, i.e. the ATM strike.

That wall is FOR SELL when it reads BUILDING with a build today (`built`, peak change since the open > 0). The sentence:
"{Hw} at {k} are adding — the {floor / ceiling} behind the sale is defended [M]".

*Why:* her OI rule. The side that keeps adding is the side not being forced. A writer who sells there is joining the
writers who hold. A wall that has stalled or is leaving is not counted: "winners cashing in" is not a defence for a new
sale.

*Why not the window's "nearer" front:* the nearer front can sit behind price (in the money for the sold option). That is
a wall price has already run over, not one between price and a strike.

**4 REGIME [I].** It is exactly rev 4 §10.1's side vote on trendbox's 5m / 15m / 1h rows at `t`:
- ≥ 2 of 3 UP and none DOWN: CALLS;
- ≥ 2 of 3 DOWN and none UP: PUTS;
- else no side.

The reading:
- the named side is your direction's side (CALLS for UP, PUTS for DOWN): FOR BUY ("a trend pays a buyer's gamma; a
  writer's best case is the premium she sold");
- "no side": FOR SELL ("the rows read range; time pays a writer while a buyer pays rent waiting");
- the other side: NEITHER, a read ("the rows trend against your direction; each leg's entry check carries it").

*Why price-led, and why counted rather than gated:* this is the variant both round-3 reads proposed (Fable's variant B,
Opus's B-11.1) and that §10 registered for the side read. Its known cost is the lag at turns, 10–60 minutes (rev 4 §10.5).
It is disclosed, not tuned.

*The board's REGIME word* (price AND OI agreeing) is **printed, not counted.** Counting it would count these rows and the
fronts (facts 2 and 3) a second time. It is also the gate that went silent.

**5 PREMIUM [M], rev 0a (replaced after the first run; §G says when and why).** It reads **one straddle, fixed for the
window**: the CE and PE of the strike that was ATM at `t − 15`, which is spot at `t − 15` rounded to the step. Both premiums
are read at `t − 15` and at `t`, from the chain record's minute closes. **One contract, never re-centred** (rev 4 §8).
- **both legs rose** (CE up **and** PE up): NEITHER, a read. It is her S5 skip ("both legs rising"), and it refuses SELL
  (R4): *the straddle is being bid on both legs*, which is the seller doctrine's vega alarm;
- otherwise, **the straddle rose** (CE + PE at `t` > at `t − 15`): FOR BUY. "A straddle bought at {t−15} is up {x} pts
  [M]: the move paid more than time took";
- **the straddle fell:** FOR SELL. "A straddle sold at {t−15} is up {x} pts [M]: time took more than the move paid". Her
  words: *"both legs decaying together … is just theta on a dead day"*;
- **equal:** NEITHER, a read ("the straddle is unchanged");
- **a premium missing at either end, or `t − 15` before 09:15:** NEITHER, could not check.

*Why a straddle and why this question:* a long ATM straddle gains exactly when the realised move beats the decay (gamma
against theta). "Which rent is winning" **is** the buyer-against-seller question, measured without an IV model. It is the
seller doctrine's Q3 ("paisa mil raha hai?") read off prices. The ATM straddle is the anchor of her band-rotation setup
(*"yeah straddle is about right because they almost forms mirror charts"*).

*Why the strike fixed at `t − 15`:* a strike chosen at `t` would be the one spot has just reached. A straddle is cheapest
at the money, so its change would be biased toward "fell" by the choice of strike alone.

*Why 15:* `QUIET` = `fronts.SLOPE_MARKS` = 15, the window the window's own clock and the noise already use.

*Why this and not the drag number:* drag and this fact measure the same contest (the move against the rent), and counting
both would count it twice. This one reads **both** legs, on one contract, over the last 15 minutes. `drag.Board` reads one
leg, anchored at the open's strike (which drifts away from both of hers). It is also silent until the index has moved
enough (`OWED_FLOOR`), and on the wrong side. Drag is **printed** beside the read as "the drag number" (§A.6).

*What rev 0 read, and why it was replaced* (§G): the board's mirror at the current ATM strike, each leg against its own
session VWAP. Because the ATM strike moves with spot, "one leg above, one below" mostly records that spot has left where
that strike's premiums averaged. That is a price-displacement read, which counts REGIME a second time.

### A.3 The refusals, each leg's own, and the word

**Refusals** are rules a leg must pass whatever the count. They are inherited or principled, and each is printed with its
reason.

**BUY is refused when:**
- **R5.** The long leg's entry check reads FOLD at `t` (rev 4 §3's entry check, rev 5 unchanged at entry): "you would
  enter a broken setup".

**SELL is refused when any one holds.** A writer's loss is open-ended, so she gets more refusals:
- **R1.** The short leg's entry check reads FOLD at `t` (rev 4 §3 with §4's writer clauses: rule 4 or 6 for a writer).
- **R2.** **Your side is leaving under a squeeze.** The window's YOUR SIDE row for the short leg reads AGAINST: her own
  side's nearer front is UNWINDING, held 3 minutes, while spot moves toward her strike (rev 4 §4). *Never sell into a
  squeeze.* A writer's buy-back is the cascade's fuel (her operator thesis).
- **R3.** **OI is blind** (fronts forming, the grid stale, fronts not read). *A writer does not sell a wall she cannot see.*
- **R4.** **Both legs of the fixed straddle rose over the last 15 minutes** (fact 5). *Never sell into a bid straddle.*
- **R6.** **No wall behind the sale:** none of the sold side's top two sits at or beyond spot. *The floor (or ceiling) is
  already behind price.* "The put writers at {k} are in the money; nothing sits between price and any put you would sell."

**The word**, applied in this order. `b` and `s` are the FOR BUY and FOR SELL counts.
1. **Could not check** when the line cannot be set at `t` (no index candle): "could not check — no {IDX} candle for {t};
   the line can't be set".
2. **Both refused:** **STAND ASIDE**, naming each refusal.
3. **Only SELL refused:** **BUY {CE|PE}** if `b ≥ s`. Else **STAND ASIDE**: "the facts favour selling, {s} to {b}, but
   selling is refused: {why}".
4. **Only BUY refused:** **SELL {PE|CE}** if `s ≥ b`. Else STAND ASIDE, mirrored.
5. **Neither refused:** **BUY** if `b > s`; **SELL** if `s > b`; **EITHER** if `b = s`.

**A word named because the other leg is refused says so.** "BUY CE — selling is refused (R3: OI blind); 1 for buy · 0 for
sell". It is never dressed as "the facts favour buying".

**Named choices, none of them a number:**
- a leg is refused by its own rules, not outvoted;
- a refused leg's majority makes STAND ASIDE, never a vote for the other leg;
- a tie is EITHER.

### A.4 Which strike each leg is

**Inherited, not invented. The facts are strike-free** (they read the index, the fronts and one straddle fixed at
`t − 15`), so the strike is a print, not an input.

- **BUY: the ATM strike.** That is spot rounded to the step, the strike the side log records as `atm.k` and `/api/board`
  defaults to. Her words: *"i often trade itm or atm so which option i m holding hardly matters"*. It is printed "ATM
  {k}; one strike ITM reads the same facts".
- **SELL: at the wall behind the sale** (fact 3's wall). Printed: "SELL {PE} {k} — at the {floor} {k}, {n} pts OTM,
  {BUILDING / STALLED / UNWINDING} [M]; your line {L} sits {m} pts {above / below} it".
  - *Why at the wall:* it is where the side that holds is writing. One strike further out would sell behind a wall the read
    has not looked at.
  - **Not shown** when there is no such wall (R6 then refuses SELL): "not shown — no {floor} front at or beyond spot among
    the top two".
- **Each leg's premium** is printed with its minute, [I] (the chain record's last trade). There is no size, no order path
  and no "book".

### A.5 When it is read

- **On every VALIDATE press.** The press states the direction: long CE or short PE is UP; long PE or short CE is DOWN. So
  the read comes with every answer, whichever leg she pressed.
- **Every finished minute, per index, for both directions, in the forward log** (§E.3). This makes it computable on days
  she never presses, as the side log is.
- **When her zone setup fires.** Your setup (VALIDATE §1.1) names a direction on its closed bar, so the tab can show the
  read for that direction before she presses. It is display only, and it pre-fills nothing.

### A.6 Printed with it, not counted

- **The drag number** (`/api/drag`): "today a correct buyer was paid {paid} of {owed} owed since {anchor} [M]". It is not
  counted, because fact 5 reads the same contest, the move against the rent (§A.2).
- **The expiry line** (rev 4 §10.3). On 0DTE it is followed by: "theta is fastest and gamma largest today. The first pays
  a writer, the second hunts her; §B and §C read both".
- **The board's REGIME** (price and OI), both halves.
- **Each leg's VALIDATE word** (the buyer's rev 2; the writer's, §B), in its own card.
- **For the sell leg, the reach** (§C): "your strike {n} pts from the index · one ATM straddle {S} pts [M]".
- **Not shown, and said so:** "not shown — a size", "not shown — an order", "not shown — odds: the count is a count".

### A.7 Hazards recorded now

- **REGIME lags at turns** by 10–60 minutes (rev 4 §10.5). At a V-turn it keeps counting the old trend for buying, or "no
  side" for selling.
- **ROOM reads FOR BUY whenever no sized wall is in the way.** On a day of leaving walls that is most minutes, because
  VALIDATE's leaving-wall rule widened the target (VALIDATE rev 2 S-b).
- **PREMIUM cannot read before 09:30** (it needs `t − 15`). A 15-minute straddle change is a short window: one fast
  minute can flip it. It is not smoothed, as the side read is not.
- **SELL is refused whenever OI is blind** (R3). That is the first ~15 minutes of every session, and any stale grid. In
  those minutes the read can say only BUY or STAND ASIDE, never SELL or EITHER.
- **BANKNIFTY** trends and inverts reversion tests (research-findings §3). The read is not specialised per index; it
  prints the index beside the word.
- **The dead list, so nobody conflates:** "selling any upper band" (research-findings §2) is a directional *index* fade at
  u2 / u3. SELL here is short premium on the side opposite her own direction. It inherits nothing from that row and revives
  nothing.

---

## B. THE SELLER IN VALIDATE (amends VALIDATE rev 2 §1.6 for a writer only)

A SELL press (short CE or short PE) now gets **GO / WAIT / NO** from four writer facts. The buyer's word, facts, outcome and
record are unchanged.

### B.1 The writer's four facts, each WITH · AGAINST · NEITHER

| # | fact | WITH | AGAINST | NEITHER |
|---|---|---|---|---|
| 1 | **Right now**: the window's entry check for the short leg | HOLD | FOLD, which makes the word NO | WATCH (a read) · PATA NAHI (*could not check*) |
| 2 | **Your wall**: the wall between spot and your strike | a front of your side, at or between spot and your strike, BUILDING with a build | — (no against state; a squeeze is inside Right now) | none there, or not building (a read) · OI blind (*could not check*) |
| 3 | **Cushion**: the danger line against the noise, and what the line costs against what you collect | line > one candle's noise, **and** the premium you collect ≥ the premium at risk to the line | line ≤ one candle's noise, **or** the premium at risk to the line > the premium you collect | the line blind, the noise unreadable, or no greeks (*could not check*) |
| 4 | **Time is paying**: the fixed straddle over the last 15 minutes (§A.2 fact 5) | the straddle fell: time won | both legs rose: the straddle bid | the straddle rose by a move (a read) · a premium missing (*could not check*) |

**1 Right now.** It is the same object as the buyer's (VALIDATE §1.2), read for the short leg. It carries the writer's own
clauses (rev 4 §4):
- the squeeze;
- payers adding as OI's "against" in rules 4 and 6;
- the writer's trend rule.

Rule 3 cannot fire at entry (M5), so §C does not touch this fact.

**2 Your wall [M].** Your side's §1d top two, the nearest to spot of those at or between spot and your strike (inclusive,
half a step of tolerance):
- BUILDING with a build today: WITH;
- else NEITHER, a read: "the defended {floor} is at {k}, beyond your strike: price reaches your strike before it tests the
  wall", or "{k} {STALLED / UNWINDING}".

*No AGAINST state.* Your side leaving under a squeeze is the window's YOUR SIDE "against", already inside Right now. This
mirrors VALIDATE §1.4 ("payers adding and flow against are already inside Right now").

**3 Cushion [M, and I].** The order of evaluation, as VALIDATE §1.3's:
1. **Line or noise unreadable:** could not check.
   - The line is L itself (rev 5), on the danger side, exactly as the window reads it.
   - The noise is `hold.noise`, the one measure rev 5 B and VALIDATE already read.
2. **Line distance ≤ noise:** AGAINST, "your danger line is {s} pts away — inside one candle's range (median {m} pts)". A
   tie is AGAINST.
3. **No greeks for your strike** in the chain record at `t`: could not check.
4. **X > P:** AGAINST, "your line is worth {X} of premium [I]; you collect {P} [M]. The line costs more than the sale can
   pay".
   - X is the premium at risk to the line: **PLAN §2.1's writer formula**, |Δ|·R + ½·Γ·R², with R the unrounded line
     distance and Δ, Γ the broker's own [M] for your strike.
   - P is your option's premium at `t`.
5. Otherwise: **WITH**.

This is the writer's Room. A buyer's Room asks whether the target is at least as far as the line, in index points. A
writer's reward is premium, so hers asks whether the premium she collects is at least what the line would cost her, **in
premium**, from the formula PLAN already registers.

*The +½Γ term is where 0DTE enters.* On an expiry afternoon Γ is largest, so X balloons, and a near line reads AGAINST
where the same line on a Monday would not. That is "decay left" and "gamma / expiry risk" in one registered formula, with
no new number.

**4 Time is paying [M].** The writer's analogue of the buyer's Paying. A buyer is paid by forced flow; a writer is paid by
time. Whether time is winning right now is the fixed straddle's last 15 minutes (§A.2 fact 5).
- the straddle fell: WITH ("a straddle sold at {t−15} is up {x} pts [M]");
- both legs rose (the straddle bid): AGAINST;
- the straddle rose by a move (one leg up, the other down): NEITHER, a read ("the move out-paid time for 15 minutes:
  selling pays only if it stops");
- it is fact 5 of §A, **the same object, read once**.

### B.2 The word, for a writer: VALIDATE rev 2 §2's rule, inherited

- **NO:** Right now is AGAINST (the window's FOLD at entry).
- **GO:** Right now is HOLD, **no** fact is AGAINST, and **at most one** is NEITHER.
- **WAIT:** everything else. It names each AGAINST as "what would have to change", or, with nothing against, each NEITHER
  as "not there yet".

It is shown with "{w} with · {a} against · {n} neither — of 4, a count, not odds".

**Printed, not counted, for a writer:**
- **Your setup** (VALIDATE §1.1, read with the writer's `d`). *Why not counted:* direction is hers. The writer's word is
  about surviving the sale. Counting it would also let the zone SELL machine (u2) vote for every short CE, and fading the
  upper band is on the dead list.
- **Your option's σ against its own session VWAP.** *Why not counted:* no registered direction. For a writer, "above its
  VWAP" is either a spike worth selling or price moving toward her strike. The fixed straddle (fact 4) reads whether time
  is winning without that ambiguity.
- The expiry line; the reach (§C); the premium at risk to the line [I]; the drag number.

### B.3 The writer's outcome, and its judgement

**What it measures.** It measures the geometry the word read, frozen at the check minute, as VALIDATE rev 2 §3 does for a
buyer, over the 30 finished minutes after the check:
- **target reached:** your option's per-minute premium (the chain record's minute close [M]) falls to **P − X** or below.
  That is: *the premium decayed by as much as the line would have cost you, before the line was touched.* 1:1 in premium
  (her words: *"1:1 atleast"*);
- **stop reached:** the index's 1-minute high (a short CE) or low (a short PE) reaches the static L at the check;
- **`first`:** `target`, `stop`, `same minute`, or `neither`.
- **Not scored**, each with its reason:
  - "could not check — no greeks at {t}";
  - "could not check — the line could not be set";
  - "checked, none — the reward read AGAINST (X > P): no target below zero". This is outside the stratum anyway.
- `short` after 14:59, `gaps` for minutes with no candle or no premium. Both as VALIDATE §3.

**What it reads, and does not.** It reads **no break rule, no trail and no reach rule** (§C). So no window revision
restarts it.

*Known asymmetry, stated:* the stop end reads the index's high and low; the target end reads the premium's minute close.
The chain record carries the minute's premium, not its range. The asymmetry favours `stop`, which is the conservative
direction for judging GO.

**The unit** is VALIDATE §3's: the first **writer** press per (index, `d`) per 30 minutes, whatever its word.
- Writer units are **their own population**, never pooled with buyer units. A long CE and a short PE share `d`, and they
  must never collide.

**The judgement** is VALIDATE rev 2 §4's form, inherited whole, on writer units only.
- **The stratum:** the writer's Cushion WITH geometry, **line > noise and P ≥ X**, identical for GO, WAIT and NO.
- **P1-W:** GO units reach the target first more often, relative to the stop, than WAIT units. It is computed as
  GO(target)·WAIT(stop) > WAIT(target)·GO(stop).
- **P2-W:** NO units less often, the same way.
- **When:** each at ≥ 15 resolved units of its word **and** ≥ 15 resolved WAIT units in the stratum, and ≥ 10 sessions;
  in any case by 30 sessions.
- **The best day** is removed as rev 5 §F.2 defines it.
- **Co-timed sets** are reduced as VALIDATE §4.
- **If P1-W fails** (or reverses without the best day), the writer's word is deleted, and the four facts stay as a
  checklist.
- **If P2-W fails,** a writer's NO is withdrawn. The screen then prints the window's entry verdict in its place.
- **Short of 15 by 30 sessions:** inconclusive, DRAFT.
- WAIT is the control and is never judged.

---

## C. THE SELLER IN THE WINDOW: THE REACH (amends rule 3 for a writer only)

### C.1 Why

**On 09-24 the window folded 11 sold calls at 14:38**, by rule 3, on the bounce off the 14:24 low. Every one of those calls
ended at 0.1–0.2.

**The line is a buyer's structure.** A buyer is long the move. A 5-minute swing break says her move has failed, and her
loss is the premium. A writer is short an **option**. Her danger is her **strike** being reached, and her loss is
open-ended.

**For a writer, a swing break matters by how near it brings price to her strike, against how far the market itself
expects price can still travel before expiry.** Her own seller doctrine names that unit: *"strike distance in σ of the
straddle — not points; 240 points means different things Monday vs Thursday"*. The market's own price for the expected
move to expiry is the ATM straddle.

### C.2 The rule

At a 3-minute close that rule 3 reads as a break (rev 5 option B: beyond L ∓ B, strict), a **writer** is read:
- **R** [M]: |her strike − the bar's close|;
- **S** [M]: the ATM straddle at that close's minute. That is the ATM CE plus the ATM PE premium, the side log's own
  `atm: {k, ce_px, pe_px}` (rev 4 §8), already logged every minute.

Then:
1. **R ≤ S: FOLD, rule 3, as now.** The sentence adds: "your strike is {R} pts away, inside one ATM straddle ({S} pts
   [M])".
2. **R > S: held.** The word is **WATCH**, tag **LINE BROKEN · HELD**:
   > "The line broke at the {bar} close ({by} pts past {L}); your strike is {R} pts away, outside one ATM straddle ({S} pts
   > [M]). The market's own expected move to expiry does not reach it. FOLD at the first 3-min close that brings your
   > strike within one straddle."
3. **While held, every later 3-min close re-reads R and S.**
   - The first close with **R ≤ S** is **FOLD, rule 3r ("the reach")**, stamped at its `read_at` (rev 5 A.0.4).
   - A **heal** (rev 5 A.0.6: a close back on her side of the L that broke) ends the held state. The line then trails and
     breaks as usual, and a new break is read by this rule again.
4. **S unreadable at any close where the reach is read** (a break close, or a close while held; no ATM premium for that
   minute): she is **FOLDed** (rule 3 at a break close, 3r while held). *Could not check the reach, so the line decides.*
   This is conservative, never lenient.
5. **Unchanged:**
   - rules 4 and 6 (they fold a held writer at once);
   - the latch;
   - PATA NAHI on a due close not landed (rev 5 A.0.4);
   - no quiet clock (rev 4 §4).

### C.3 What respects decay, and what keeps it from being a FOMO trap

- **Decay is inside S.** The straddle shrinks with time, so the same strike becomes farther in straddles as expiry nears.
  A writer is held through more swing breaks on an expiry afternoon than on a Monday, and the rule needs no clock and no
  number to do it.
- **The trap is closed from two sides.**
  - As price comes toward her strike, R shrinks.
  - As the straddle is bid (vol expanding: the seller doctrine's vega alarm), S grows.
  - Either one alone brings the fold nearer. A held writer can never sit through her strike: R = 0 < S whenever S > 0.
- **The hard control stays.**
  - A near strike (inside one straddle) folds at the line exactly as today.
  - A far strike folds at the first close inside one straddle.
  - Rules 4 and 6 fold her at once.
  - FOLD still latches, and ✕ still cannot dismiss it (the UI's rule).
- **What it does not do.** It reads no premium candle of her own option, so rev 4 §1's "no candle of the premium is an
  input" holds. S is the ATM straddle's level, the market's unit, not her P&L.

### C.4 Its kill clause (clause W-R), forward rows only

- **The unit** is a **held break**: a writer's first line break read R > S. It is keyed (index, bar, L, strike, side), and
  trades that share it count once, as rev 5 §F.1's distinct breaks do.
- **For each unit, two premiums [M]:**
  - **P_b** is her option's premium at the break close, what folding at the line would have bought back;
  - **P_x** is the premium at her first FOLD after it, any rule including 3r, or at 15:29 (flagged `to_close`) if none.
- **The clause dies** if **P_x > P_b on more than half of the held breaks** (holding through cost more than folding at the
  line would have). It also dies if that is true once the best day is removed. The best day is the session whose removal
  moves the count most toward failing (rev 5 §F.2).
- **Two populations, never pooled, each judged on its own count:**
  - (i) her writer trades, marked and imported;
  - (ii) the SELL leg of the expression's forward units (§E.3), re-read by the window from the unit minute to 15:29 and
    logged as `sell_hold`.
  It dies if **either** judged population fails it. That is conservative, because the risk is open-ended.
- **When:** at ≥ 15 held breaks in a population and ≥ 10 sessions, by 30 at the latest.
- **Short of 15 by 30 sessions:** inconclusive, and the clause stays DRAFT.
- **If it dies,** writers' rule 3 is rev 5 option B's again: the buyer's break, which is the signed rule today. That text
  is on file.

### C.5 The window's other writer clauses, unchanged

Rev 4 §4's own-side clause and payers-adding clause stand, and so do W1 and W2 (rev 4 §7). W1 ("a with-trend short is not
folded at all while spot moves away from her strike, line included") is the prediction this clause serves.

### C.6 Flagged, as rev 4's S1 flagged its writer clause

This clause was written **after** seeing the 09-24 writer replay's fold minutes and premiums (listed in the header). The
unit (the ATM straddle) is her doctrine's. Its scale is one, as "one candle" is. The straddle's value at 14:38 was **not**
computed before this text was fixed; §D.4 shows what the rule does there. **W-R judges it on forward rows only.**

---

## D. DISCLOSURE: the rules as written, run over her days (added 2026-09-26 00:34–00:47 IST by the clock, after the runs)

**In-sample hindsight on four frozen days and one live day.** These are counts and rows, never a rate. **None of it counts
toward §E's falsifiers**, and nothing in §A–§C was chosen on it, except where §G says so (fact 5, rev 0a).

### D.0 Method, fingerprints and limits

**Fingerprints** (the draft's own text, read with `sha256sum` before each run):
- **rev 0:** `eca1afe0debf687d56d8e35d4d42c475280b6f01267e7431b6cb6271da2e2b6c` (00:21);
- **rev 0a:** `5ddc16d1357e41f4feb99a7ad4cb78a7b737e6bb701bbcb33316dcfad15a9654` (00:33).

The copies are `rules_before_run.md` and `rules_rev0a_before_run.md`.

**Scratch only**, in the session scratchpad `expr/`:
- `expr.py`: the rules, implemented once;
- `run.py`: every minute, her entries and the 09-24 seller;
- `nifty25.py`: 09-25.

**Outputs:** `entries.json`, `silence.json`, `silence_detail.json`, `tally.json`, `seller_0924.json` and `tables.md`. Rev 0's
outputs are kept in `expr/rev0/`.

**What the run touched, and did not:**
- The window is `hold.py` as built (rev 5 option B). The fixtures load through `test_hold.py`'s own `_day` / `_trades`.
- §C's reach is applied over `hold.read`'s rows in scratch.
- No repo file was written except this draft. No server was touched, `data/` was not opened, and nothing was POSTed.

**Inputs, and their tags:**
- **Facts per minute:** `docs/hold/opus/scratch/facts_*.json.gz` [M / I as frozen].
- **ROOM's walls and SHIELD's wall:**
  - on 09-24, the frozen `/api/oihist` grid, ranked by the open plus the running high on the marks. That is the server's own
    fallback in `_hold_rec` [I ranking, M states];
  - **on 09-22 and 09-23 only the nearer front per side was frozen**, so those days read the nearer front alone [I]. This
    over-fires R6 there: a nearer front behind price leaves no second front to fall back on.
- **Premiums:** the fixtures' 1-minute closes.
- **§B's greeks:** Black-76 through `gamma.implied_vol` / `delta` / `gamma` on those closes [I].
  - F is the index (no future was frozen). T runs to 15:30 of the chain's expiry, read off the trade symbols: NIFTY 09-22
    weekly, NIFTY monthly 09-29, SENSEX 09-24.
  - **The live rule reads the broker's [M] greeks; these are not those.**
- **Index candles:** NIFTY 09-24 and BANKNIFTY 09-24 were rebuilt from chain spot [I] (the fixtures say so).
- **09-21 was never frozen.** 09-25 has no frozen premiums, so fact 5 and every premium there are "could not check".

### D.1 How often it speaks, on every finished minute of the nine frozen index-days, both directions (rev 0a)

The denominator is 375 minutes per index-day and direction, 6,750 in all. "Aside" is split into (both legs refused) and
(one leg refused, and that leg led the count).

| index-day | dir | BUY | SELL | EITHER | STAND ASIDE (both · led) | could not check |
|---|---|---|---|---|---|---|
| NIFTY 09-22 (0DTE) | UP | 90 | 117 | 23 | 143 (90 · 53) | 2 |
| | DOWN | 72 | 149 | 81 | 71 (58 · 13) | 2 |
| SENSEX 09-22 | UP | 110 | 140 | 39 | 84 (45 · 39) | 2 |
| | DOWN | 117 | 138 | 32 | 86 (50 · 36) | 2 |
| BANKNIFTY 09-22 | UP | 142 | 41 | 6 | 184 (135 · 49) | 2 |
| | DOWN | 129 | 137 | 8 | 99 (49 · 50) | 2 |
| NIFTY 09-23 (range) | UP | 142 | 107 | 65 | 60 (8 · 52) | 1 |
| | DOWN | 149 | 66 | 26 | 133 (76 · 57) | 1 |
| SENSEX 09-23 | UP | 112 | 150 | 64 | 47 (1 · 46) | 2 |
| | DOWN | 96 | 108 | 60 | 109 (51 · 58) | 2 |
| BANKNIFTY 09-23 | UP | 119 | 108 | 57 | 89 (49 · 40) | 2 |
| | DOWN | 163 | 55 | 22 | 133 (81 · 52) | 2 |
| NIFTY 09-24 (trend down) [I candles] | UP | 87 | 28 | 58 | 200 (187 · 13) | 2 |
| | DOWN | 226 | 68 | 52 | 27 (10 · 17) | 2 |
| SENSEX 09-24 (trend down, 0DTE) | UP | 178 | 22 | 81 | 94 (78 · 16) | 0 |
| | DOWN | 198 | 90 | 35 | 52 (21 · 31) | 0 |
| BANKNIFTY 09-24 [I candles] | UP | 155 | 103 | 37 | 78 (57 · 21) | 2 |
| | DOWN | 179 | 107 | 59 | 28 (23 · 5) | 2 |
| **total, of 6,750** | | **2,464** | **1,734** | **805** | **1,717 (1,069 · 648)** | **30** |

**Its silence on her days:** STAND ASIDE or could not check on **1,747 of 6,750** index-direction-minutes. That is a
disclosure, not a target.
- **1,069** of those are **both legs refused.**
  - In all of them the long leg's entry check reads FOLD. R5 is the only buy refusal, so a buy refusal is always that.
  - The short leg is refused too, mostly by its own entry check (R1).
  - So: *the direction she would be taking reads as a broken setup right now.*
- It gathers on the day's **counter-trend** direction: NIFTY 09-24 UP 200 against DOWN 27; SENSEX 09-24 UP 94 against DOWN
  52.
- **Could not check** is 30 minutes in all: the minutes with no index candle.

**The facts that drove the words** (`tally.json`, rev 0a, on the 6,720 index-direction-minutes where the line could be set,
STAND ASIDE included):

| fact | FOR BUY | FOR SELL | NEITHER |
|---|---|---|---|
| SPEED | 2,989 | — | 3,731 |
| ROOM | 4,329 | 2,119 | 272 |
| SHIELD | — | 1,629 | 5,091 |
| REGIME | 1,685 | 3,350 | 1,685 |
| PREMIUM | 2,288 | 3,934 | 498 |

**The refusals, per minute** (a minute can carry several):

| refusal | minutes |
|---|---|
| R1 | 1,054 |
| R2 | 919 |
| R3 | 272 |
| R4 | 90 |
| R5 | 1,105 |
| R6 | 1,319 (over-fired on 09-22 and 09-23: nearer-only fronts, §D.0) |

**Rev 0, disclosed as §G promises:**
- Its PREMIUM read FOR BUY on 5,434, FOR SELL on 1,118 and NEITHER on 168.
- Its words were BUY 3,817 · SELL 871 · EITHER 639 · STAND ASIDE 1,393 · could not check 30 (`rev0/silence.json`).
- It was silent on **1,423**.

### D.2 At her 29 entries (09-21 → 09-24), in her own direction

The read minute is the last finished minute before the fill.
- **Facts:** B = FOR BUY, S = FOR SELL, · = NEITHER, in the order SPEED · ROOM · SHIELD · REGIME · PREMIUM.
- **The BUY leg** is ATM.
- **The SELL leg** is at the wall behind the sale. Its distance from spot is in points. An "I" day (09-22 and 09-23) reads the
  nearer front only.

| # | entry (read minute) | dir | **the word** (rev 0a) | buy–sell | facts | refused | BUY leg | SELL leg | rev 0's word |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 09-21 13:59 NIFTY 23300CE | UP | **could not check**: 09-21 was never frozen | | | | | | same |
| 2 | 09-22 09:41 NIFTY 23300CE | UP | **STAND ASIDE** | 1–3 | · S S B S | R5, R1 | CE 23,450 | PE 23,400 (52 OTM) | STAND ASIDE 2–2 |
| 3 | 09-22 10:31 NIFTY 23550PE | DOWN | **EITHER** | 2–2 | B S S · B | — | PE 23,450 | CE 23,450 (23) | EITHER 2–2 |
| 4 | 09-22 10:41 NIFTY 23550PE | DOWN | **BUY PE** | 3–2 | B B S S B | — | PE 23,400 | CE 23,450 (62) | BUY PE 3–2 |
| 5 | 09-22 10:42 NIFTY 23550PE | DOWN | **SELL CE** | 2–3 | B S S S B | — | PE 23,400 | CE 23,450 (64) | SELL CE 2–3 |
| 6 | 09-22 10:43 NIFTY 23550PE | DOWN | **SELL CE** | 2–3 | B S S S B | — | PE 23,400 | CE 23,450 (58) | SELL CE 2–3 |
| 7 | 09-22 10:51 NIFTY 23500PE | DOWN | **SELL CE** | 2–3 | B S S S B | — | PE 23,350 | CE 23,450 (78) | SELL CE 2–3 |
| 8 | 09-22 13:47 NIFTY 23500PE | DOWN | **BUY PE** | 3–1 | B B · S B | — | PE 23,350 | CE 23,400 (66) | BUY PE 3–1 |
| 9 | 09-23 09:17 NIFTY 23450CE | UP | **STAND ASIDE** | 0–1 | · · · S · | R3 | CE 23,400 | PE 23,400 (9) | STAND ASIDE 0–1 |
| 10 | 09-23 09:46 NIFTY 23450CE | UP | **STAND ASIDE** | 0–4 | · S S S S | R5, R1 | CE 23,400 | PE 23,400 (18) | STAND ASIDE 0–4 |
| 11 | 09-23 09:48 NIFTY 23400PE | DOWN | **SELL CE** | 1–4 | B S S S S | — | PE 23,350 | CE 23,400 (27) | SELL CE 1–4 |
| 12 | 09-23 09:59 NIFTY 23450CE | UP | **SELL PE** | 0–4 | · S S S S | — | CE 23,400 | PE 23,400 (23) | SELL PE 0–4 |
| 13 | 09-23 10:18 NIFTY 23450CE | UP | **SELL PE** | 0–4 | · S S S S | — | CE 23,400 | PE 23,400 (8) | SELL PE 1–3 |
| 14 | 09-23 10:32 NIFTY 23450CE | UP | **BUY CE** | 3–2 | B S S B B | — | CE 23,400 | PE 23,400 (1) | BUY CE 3–2 |
| 15 | 09-23 11:06 NIFTY 23450CE | UP | **BUY CE** | 3–2 | B S S B B | — | CE 23,450 | PE 23,400 (29) | BUY CE 3–2 |
| 16 | 09-23 11:31 SENSEX 74900CE | UP | **SELL PE** | 1–3 | · S S B S | — | CE 74,900 | PE 74,700 (187) | EITHER 2–2 |
| 17 | 09-24 09:41 SENSEX 74200PE | DOWN | **EITHER** | 2–2 | · B S B S | — | PE 74,200 | CE 74,300 (108) | BUY PE 3–1 |
| 18 | 09-24 10:18 SENSEX 74200PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | PE 74,100 | CE 74,300 (185) | BUY PE 3–1 |
| 19 | 09-24 12:31 SENSEX 74100PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | PE 74,000 | CE 74,200 (186) | BUY PE 3–1 |
| 20 | 09-24 12:34 SENSEX 74000PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | PE 74,000 | CE 74,200 (226) | BUY PE 3–1 |
| 21 | 09-24 12:43 SENSEX 74000PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | PE 74,000 | CE 74,200 (214) | BUY PE 3–1 |
| 22 | 09-24 13:25 SENSEX 74000PE | DOWN | **SELL CE** | 1–2 | · S · B S | — | PE 74,000 | CE 74,200 (233) | BUY PE 2–1 |
| 23 | 09-24 13:40 SENSEX 73900PE | DOWN | **BUY PE** | 2–1 | · S · B B | — | PE 73,900 | CE 74,200 (338) | BUY PE 2–1 |
| 24 | 09-24 13:42 SENSEX 73900PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | PE 73,900 | CE 74,200 (341) | BUY PE 3–1 |
| 25 | 09-24 13:43 SENSEX 73900PE | DOWN | **BUY PE** | 4–0 | B B · B B | — | PE 73,800 | CE 74,200 (378) | BUY PE 4–0 |
| 26 | 09-24 13:44 SENSEX 73800PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | PE 73,800 | CE 74,200 (431) | BUY PE 3–1 |
| 27 | 09-24 13:53 SENSEX 73800PE | DOWN | **BUY PE** | 3–1 | B S · B B | — | PE 73,700 | CE 74,200 (509) | BUY PE 3–1 |
| 28 | 09-24 13:56 SENSEX 73800PE | DOWN | **BUY PE** | 2–1 | · S · B B | — | PE 73,700 | CE 74,200 (541) | BUY PE 2–1 |
| 29 | 09-24 14:22 SENSEX 73800PE | DOWN | **SELL CE** | 1–2 | · S · B S | — | PE 73,600 | CE 74,200 (564) | BUY PE 2–1 |

**The words at her 29 entries (rev 0a):**

| word | entries |
|---|---|
| BUY | 14 |
| SELL | 9 |
| EITHER | 2 |
| STAND ASIDE | 3 |
| could not check | 1 |

**It was silent at 4 of 29.** Rev 0's words were BUY 17 · SELL 6 · EITHER 2 · STAND ASIDE 3 · could not check 1. The two
versions differ at #16, #17, #22 and #29, all four through fact 5.

**What the other leg did afterwards** (described, hindsight). The sold leg is at the read's own strike; for #2 onward it was
always shown.
- "Seller pts" is the premium at the read minus the premium then, so + is the seller's gain.
- "Worst in 30" is the seller's worst mark in the next 30 minutes.
- "Her leg" is her own exit (premium points) and her option at +30 [M].
- The writer's word is §B's, for that sell leg. Its outcome is §B.3's, over 30 minutes.
- The window on the sold leg is its first FOLD: rule 5 B as built, then with §C. The figure is the seller's points at the
  fold.

| # | the other leg (sold) | premium at read | seller pts +15 · +30 · 15:29 | worst in 30 | her leg: exit · +30 | writer word | writer outcome (30 min) | the window: rev 5 B · with §C |
|---|---|---|---|---|---|---|---|---|
| 2 | PE 23,400 | 26.4 | +2.4 · +5.05 · −44.3 | +0.2 | −7.25 · +3.45 | NO | neither | 09:41 r6 0.0 · same |
| 3 | CE 23,450 | 32.5 | +9.05 · +13.15 · +32.45 | +1.7 | +9.25 · +46.9 | WAIT | neither | 14:14 r3 +15.55 · same |
| 4 | CE 23,450 | 25.1 | +3.9 · +4.65 · +25.05 | +1.25 | +12.2 · 0.0 | WAIT | neither | 14:14 r3 +8.15 · same |
| 5 | CE 23,450 | 22.35 | +0.15 · +1.3 · +22.3 | −1.5 | −3.45 · −2.4 | WAIT | neither | 14:14 r3 +5.4 · same |
| 6 | CE 23,450 | 23.85 | +2.0 · +2.0 · +23.8 | +0.35 | +2.5 · −3.2 | WAIT | neither | 14:14 r3 +6.9 · same |
| 7 | CE 23,450 | 20.85 | +1.2 · −1.8 · +20.8 | −2.7 | −13.15 · −26.0 | WAIT | neither | 14:14 r3 +3.9 · same |
| 8 | CE 23,400 | 14.55 | +5.45 · −24.3 · +14.5 | −24.3 | +21.7 · −61.9 | WAIT | target 13:53 | 14:14 r3 −17.25 · same |
| 9 | PE 23,400 | 116.2 | −6.8 · +2.5 · +35.05 | −9.05 | −1.0 · −1.15 | WAIT | not scored (fewer than 15 candles) | 09:44 r6 −0.55 · same |
| 10 | PE 23,400 | 116.9 | −1.3 · +2.45 · +35.75 | −13.9 | −7.65 · −3.95 | NO | stop 09:54 | 09:46 r6 0.0 · same |
| 11 | CE 23,400 | 118.0 | −3.6 · −8.6 · −17.45 | −8.6 | −0.8 · −17.7 | GO | neither | 10:19 r6 −10.8 · same |
| 12 | PE 23,400 | 115.45 | −7.5 · +9.75 · +34.3 | −11.1 | −7.8 · +4.25 | WAIT | neither | 10:05 r6 +0.95 · same |
| 13 | PE 23,400 | 107.3 | +3.8 · +9.85 · +26.15 | −1.65 | +3.15 · +8.6 | GO | neither | 13:32 r3 +14.5 · same |
| 14 | PE 23,400 | 104.45 | +6.4 · +6.15 · +23.3 | −2.15 | −0.45 · +3.35 | GO | neither | 13:32 r3 +11.65 · same |
| 15 | PE 23,400 | 94.3 | −3.85 · +0.85 · +13.15 | −5.55 | −5.65 · +1.5 | GO | neither | 13:32 r3 +1.5 · same |
| 16 | PE 74,700 | 161.1 | +8.7 · +7.45 · +29.1 | −9.3 | −15.25 · −3.1 | GO | neither | 13:29 r3 +5.3 · same |
| 17 | CE 74,300 | 129.3 | +11.9 · +7.1 · +129.15 | −4.3 | +23.75 · −4.7 | GO | neither | 10:43 r4 +29.2 · same |
| 18 | CE 74,300 | 101.7 | −10.15 · −7.3 · +101.55 | −15.3 | +11.4 · −35.25 | WAIT | neither | 10:43 r4 +1.6 · same |
| 19 | CE 74,200 | 99.5 | +5.65 · +1.85 · +99.35 | +0.45 | +13.65 · +11.45 | WAIT | neither | 14:38 r3 +66.2 · 14:45 r4 +70.6 |
| 20 | CE 74,200 | 91.5 | −2.35 · −14.15 · +91.35 | −14.15 | −18.8 · −38.25 | WAIT | neither | 14:38 r3 +58.2 · 14:45 r4 +62.6 |
| 21 | CE 74,200 | 96.8 | +0.5 · −3.95 · +96.65 | −12.3 | −7.95 · −27.0 | WAIT | neither | 14:38 r3 +63.5 · 14:45 r4 +67.9 |
| 22 | CE 74,200 | 82.65 | +23.15 · +44.8 · +82.5 | +7.1 | +35.8 · +196.9 | GO | target 13:26 | 14:38 r3 +49.35 · 14:45 r4 +53.75 |
| 23 | CE 74,200 | 59.5 | +21.65 · +25.4 · +59.35 | −0.3 | +2.95 · +133.07 | WAIT | neither | 14:38 r3 +26.2 · 14:45 r4 +30.6 |
| 24 | CE 74,200 | 59.5 | +27.35 · +24.8 · +59.35 | +3.9 | +0.75 · +111.2 | WAIT | neither | 14:38 r3 +26.2 · 14:45 r4 +30.6 |
| 25 | CE 74,200 | 55.6 | +24.4 · +19.85 · +55.45 | +3.9 | +7.15 · +79.3 | WAIT | neither | 14:38 r3 +22.3 · 14:45 r4 +26.7 |
| 26 | CE 74,200 | 51.7 | +19.25 · +15.2 · +51.55 | +2.9 | +6.0 · +30.6 | WAIT | neither | 14:38 r3 +18.4 · 14:45 r4 +22.8 |
| 27 | CE 74,200 | 41.4 | +5.75 · +17.0 · +41.25 | +0.4 | −12.15 · +40.3 | WAIT | neither | 14:38 r3 +8.1 · 14:45 r4 +12.5 |
| 28 | CE 74,200 | 36.2 | +2.6 · +12.05 · +36.05 | −4.8 | +29.6 · +15.85 | WAIT | neither | 14:38 r3 +2.9 · 14:45 r4 +7.3 |
| 29 | CE 74,200 | 27.9 | −3.6 · −5.25 · +27.75 | −9.15 | +7.35 · −125.3 | WAIT | neither | 14:38 r3 −5.4 · 14:45 r4 −1.0 |

**In rows, not rates:**
- **09-24, her 13 SENSEX puts.**
  - The words: BUY PE at 10, SELL CE at 2 (#22 13:25, #29 14:22), EITHER at 1 (#17).
  - The named call was CE 74,300 or 74,200, 108–564 pts out of the money, and it ended at 0.1–0.15.
  - At +30 the sold call was ahead at 9 and behind at 4 (#18, #20, #21, #29). Her put was ahead at 8 and behind at 5.
  - The two SELL CE minutes cut both ways:
    - at #22 her put made +196.9 in 30 minutes and the sold call +44.8;
    - at #29 (14:22, two minutes before the low) her put lost 125.3 in 30 minutes, while the sold call lost 5.25 and ended
      +27.75.
- **09-23, her NIFTY re-entries.**
  - At her two losing calls, #10 (−₹497) and #12 (−₹507), the read said STAND ASIDE (both legs refused) and SELL PE (0–4).
  - The sold PE 23,400 was −1.3 / −7.5 at +15, +2.45 / +9.75 at +30, and about +35 at 15:29. It was never folded by the
    line; rule 6 folded it at 09:46 / 10:05 at 0.0 / +0.95.
  - Her one winning re-entry, #13 (+₹205), read SELL PE 0–4.
- **09-22, expiry.**
  - The 10:31–10:51 put scalps read EITHER, BUY PE, then SELL CE three times. The sold CE 23,450 was ahead at +30 at 4 of
    those 5, and every one decayed to the close.
  - Her best trade, #8 (13:47, +₹1,410), read BUY PE 3–1. **Both** legs were behind at +30: her put −61.9, the sold call
    −24.3. The index turned.
- **§B, the writer's word at the 28 sell legs:**

  | writer word | sell legs |
  |---|---|
  | GO | 7 |
  | WAIT | 19 |
  | NO | 2 |

  | writer outcome (30 min) | sell legs |
  |---|---|
  | neither | 24 |
  | target | 2 (#8, #22) |
  | stop | 1 (#10, a NO) |
  | not scored | 1 |

  **The 30-minute writer outcome rarely resolves** (§H.1).
  - 10 of the 28 fell outside the writer's stratum, 9 of them because X > P: selling a far call whose line is worth more
    premium than the call itself.

### D.3 Her 09-25 NIFTY entries

What was frozen for 09-25:
- the index candles and zone rows (`nifty_2026-09-25.json`);
- the OI grid by GET at 16:25 (`oihist_NIFTY_1625.json`, ranked as §D.0);
- the live `/api/hold` rows of her two marked trades;
- the saved 09:35 check.

Flow, trend and the window's states are read off those rows. **No 09-25 premium was frozen**, so fact 5, R4 and every
premium figure are "could not check".

| entry (read) | dir | the word | buy–sell | facts | refused | BUY leg | SELL leg | the index afterwards [M] |
|---|---|---|---|---|---|---|---|---|
| 09:36 NIFTY 23200PE (her words; the saved 09:35 check) | DOWN | **SELL CE** | 0–3 | · S S S ? | — | PE 23,100 | CE 23,200 (96 OTM), the ceiling BUILDING | 30-min high 23,104.85 (09:36), low 23,036.05 (09:53). The index never came within 95 pts of the sold strike. The call's premium was not frozen. By her own account her PE (in about 150, out 160) ran to 181. |
| 12:01:21 NIFTY 23100CE (marked) | UP | **BUY CE** | 2–1 | B B · S ? | — | CE 23,100 | PE 23,100 (ATM), the floor STALLED | 30-min low 23,059.5 (12:04), high 23,088.45 (12:30). The CE was folded by the window at 12:05 (rev 5 B). The premium was 146.95 at 15:29. |
| 12:05:28 NIFTY 23200PE (marked) | DOWN | **BUY PE** | 2–1 | B B · S ? | — | PE 23,050 | CE 23,100 (33 OTM), the ceiling STALLED | 30-min high 23,089.85 (12:31), low 23,061.95 (12:08). The window folded it at 13:59 (rev 5 B). |

Facts at 09:35 (the SELL CE row):
- ROOM: FOR SELL. PE 23,100 was DEFENDED 3.95 pts away against a line 17.65 pts away. This is VALIDATE rev 2 §6's own
  target.
- SHIELD: FOR SELL. CE 23,200 was BUILDING.
- REGIME: FOR SELL. The rows read 5m UP · 15m RANGE · 1h DOWN, no side.
- SPEED: NEITHER. Nothing paid, and flow could not be read.

It was silent at 0 of 3.

### D.4 The seller on 09-24, under §C

These are her 13 put entries read as **sales of the call at the same strike**, the handoff's own replay (`replay_0924_writer.py`),
re-read with the reach.

At 14:38:
- the index closed **73,764.02**;
- the ATM straddle, 73,800 CE plus PE, was **321.6 pts [M]**, with 52 minutes to expiry;
- R for each strike was: 73,800 CE 36 · 73,900 CE 136 · 74,000 CE 236 · 74,100 CE 336 · 74,200 CE 436.

| sold call (entry) | at entry | rev 5 B: first FOLD, seller pts | with §C | at 15:29 |
|---|---|---|---|---|
| 74,200 (09:41) | 174.7 | 10:43 rule 4, +36.5 | the same | 0.15 (+174.55) |
| 74,200 (10:18) | 138.6 | 10:43 rule 4, +0.4 | the same | 0.15 (+138.45) |
| 74,100 (12:31) | 138.0 | 14:38 rule 3, +90.45 | **held at 14:38 (R 336 > S 321.6); 14:45 rule 4, +95.55** | 0.15 (+137.85) |
| 74,000 (12:34 · 12:43 · 13:25) | 171.7 · 178.1 · 157.05 | 14:38 rule 3, +103.95 · +110.35 · +89.3 | the same (R 236 ≤ 321.6) | 0.2 |
| 73,900 (13:40 · 13:42 · 13:43) | 157.65 · 154.25 · 140.4 | 14:38 rule 3, +61.75 · +58.35 · +44.5 | the same (R 136) | 0.1 |
| 73,800 (13:44 · 13:53 · 13:56 · 14:22) | 176.0 · 145.05 · 127.65 · 107.45 | 14:38 rule 3, +42.9 · +11.95 · −5.45 · −25.65 | the same (R 36) | 0.1 |

**The honest result: the reach does not rescue 09-24.**
- At 14:38 the market's own straddle still priced a 321.6-pt move to the close. Ten of the eleven line folds had strikes
  inside it, so they fold exactly as today.
- One (74,100) is held for seven minutes, until the window's own rule 4 folds it: put writers adding below the low, while
  the call writers leave under the bounce.
- **Every call still expired at 0.1–0.2.** The market over-priced the move that afternoon, and no principled writer rule
  here could have known that at 14:38. It is hindsight, and nothing was tuned toward it.

**The same rule on the read's own sell legs** (§D.2 #19–#29):
- The CE 74,200 (R 436) is held at 14:38, then folded at 14:45 by rule 4. The premium went 33.3 at the break to 28.9 at the
  fold, so holding cost nothing there.
- It is one contract at one close, so under §C.4's dedup it is **one** held break, not eleven.
- **In-sample on 09-24:** two distinct held breaks (74,100; 74,200). Both folded at 14:45 by rule 4, and P_x < P_b in both
  (47.55 → 42.45; 33.3 → 28.9). **Neither counts toward W-R.**
- **On 09-22 and 09-23,** every sold leg that the line folded had its strike inside one straddle, so §C changed no fold
  there. That covers the 09-22 afternoon CE 23,450 / 23,400 and the 09-23 PE 23,400 / 74,700.

---

## E. PARAMETERS, FALSIFIERS, LOGS, CLOCKS

### E.1 Parameters: inherited, or named

| item | value | from |
|---|---|---|
| SPEED | the window's "paid" at `t` | rev 4 §3 rule 5; VALIDATE rev 2 §1.4 |
| ROOM | VALIDATE §1.3's target (leaving walls out) against |close − L|, unrounded; a tie FOR BUY | VALIDATE rev 2 §1.3 |
| SHIELD | the nearest of the sold side's §1d top two at or beyond spot (half a step); BUILDING with a build | §1d; `fronts.read`; board's `built` |
| REGIME | §10.1's vote on 5m / 15m / 1h | rev 4 §10 |
| PREMIUM (rev 0a) | the straddle of the strike ATM at `t − 15`, CE + PE at `t` against at `t − 15`; both legs up reads NEITHER and R4 | `QUIET` = `SLOPE_MARKS` = 15; rev 4 §8's one-contract rule; her ATM-straddle anchor |
| refusals R1–R6 | as §A.3 | the window (R1, R2, R5); **named choices** (R3, R4, R6) |
| the word | refusals, then the count; a tie EITHER | **named choice** |
| strikes | BUY ATM; SELL at the wall behind the sale | side log `atm.k`; SHIELD's wall |
| writer facts | Right now · Your wall · Cushion (noise, X vs P) · Time is paying | VALIDATE rev 2 §1.2/§1.3; PLAN §2.1's writer formula; §A fact 5 |
| writer target | P − X, 1:1 in premium | PLAN §2.1; her "1:1 atleast" |
| writer word · unit · stratum · judgement | as VALIDATE rev 2 §2–§4 | inherited whole |
| the reach | R against S = the ATM straddle at the close, scale 1× | **named choice**; the unit is her seller doctrine's; the straddle is the side log's `atm` |
| expression units | the 30-minute grid from 09:45 (09:45, 10:15 … 15:15) per (index, `d`) | rev 4 §7's 30-minute horizon from the open |
| expression outcome | each leg's premium at +30 finished minutes, as % of its unit-minute premium | rev 4 §7's unit (% of premium); **the endpoint is a named choice** (§E.2) |

**No new number.**
- **New uses of inherited numbers:**
  - 30 minutes, for the unit grid and the outcome;
  - 15, 3 and half a step (the ATM rule);
  - 1× for the straddle, as 1× for the candle.
- **New named choices, not numbers:**
  - R3, R4 and R6;
  - the word's order;
  - the tie reading EITHER;
  - SHIELD's wall;
  - the sell strike at the wall;
  - the reach;
  - the endpoint.
- **Changing any one is a new registration.**
- **Not used, and why:**
  - **her "90-minute write guard"** (her profile's validated spine) has no text in the repo; it is hers to state before it
    can be used;
  - **IV against realised vol** (the seller doctrine's Q3) is not computed per minute by any module the window reads.

### E.2 A falsifier per word (the expression, §A), forward rows only

**The units** are the 30-minute grid per (index, `d`): 09:45, 10:15 … 15:15. They are fixed in advance, whatever the word,
and independent of her. At each, both legs are priced at their named strikes; if the sell strike is not shown, the unit is
not scored and is shown.

**The outcome** for each leg is its premium at the 30th finished minute against the unit minute, as a % of the unit-minute
premium:
- long: (p30 − p0) / p0;
- short: (p0 − p30) / p0.

The **gap** is G = long % − short %.

*Why the endpoint, not rev 4's favourable excursion:* an excursion credits a writer with decay she could bank only by
exiting at the best tick, and hides the adverse path that is her open-ended risk. The endpoint is what each leg paid if held
30 minutes. The favourable and adverse excursions are **shown** in every row, and never judged.

**The four claims.** Each is judged as two distributions: medians and full rows, split by index and direction, never a
rate.
- **BUY:** the median G at BUY units is **larger** than at all other scored units.
- **SELL:** the median G at SELL units is **smaller** than at all other scored units.
- **EITHER:** the median |G| at EITHER units is **smaller** than at BUY and SELL units: *a tie is where the choice matters
  least.*
- **STAND ASIDE:** the median of max(long %, short %), the better leg, is **lower** at STAND ASIDE units than at all other
  scored units: *where it stands aside, neither leg paid.*

**When and how each is judged.**
- At **≥ 15 units of that word and ≥ 10 sessions**, and in any case at **30 sessions**.
- It must **survive removing the best day**: the session whose removal moves that comparison most toward failing (rev 5
  §F.2's definition).
- It must also hold with the `short` units (after 14:59, to 15:29) removed, and with co-timed sets reduced: NIFTY, then
  SENSEX, then BANKNIFTY; UP before DOWN.

**If a word fails:**
- **BUY or SELL:** it is withdrawn. Where it would have been named, the read says "EITHER — {word} withdrawn on {date}", with
  its count.
- **EITHER:** a tie prints the count and no word.
- **STAND ASIDE:** the refusals R1–R6 are re-registered. Until then the word reads "STAND ASIDE — its falsifier failed on
  {date}; see the rows". The refusals are safety rules: nothing is lifted silently.
- **Short of 15 by 30 sessions:** inconclusive, and the word stays DRAFT.

**Her presses** (population (a): the read at each VALIDATE press and each trade entry) are **shown, never judged**, and never
pooled with the grid. They describe the read when a trade was in front of her.

### E.3 The logs, additive, write-once (`hold_log`'s discipline)

- **`data/hold/expr_<day>.jsonl` (new).** One row per finished minute, per index, per direction. It is written live by
  `_hold_tick` and completed by the close-time import (the anytime-start rule makes it exact).
  ```
  {kind: "expr", day, t, idx, d, word, nb, ns, facts: [[name, state, absence, text]...],
   refusals: {buy: [...], sell: [...]},
   buy:  {side, k, px, entry},                 -- entry = the long leg's entry verdict at t
   sell: {side, k, px, entry, wall: {k, state}|null, otm},
   line, noise, regime_board, drag, expiry, blind: [...], unit: bool, prereg: "expr-1", tag: "I"}
  ```
  Keyed (idx, t, d). On a unit minute (§E.2), an **outcome row** is written once its 30 minutes have finished (the
  `stamp_track` discipline):
  ```
  {kind: "expr_outcome", day, t, idx, d, word,
   long:  {side, k, p0, p30, pct, mfe, mae}, short: {side, k, p0, p30, pct, mfe, mae} | "not scored — why",
   G, short_window: bool, co_timed: [...],
   sell_hold: {first_break, R, S, held, fold_t, fold_rule, P_b, P_x, to_close} | null}   -- §C.4 population (ii)
  ```
  Keyed (idx, t, d, "outcome").
- **`data/hold/check_<day>.jsonl` (additive).**
  - Every press gains `expr: {word, nb, ns, facts, refusals, legs}`.
  - Writer presses gain `rev: "2W"`, `word`, and the writer `facts`. Buyer presses keep `rev: "2"` and every rev 2 field.
  - Writer outcome rows are `{kind: "check_outcome", role: "short", target: {P, X, level}, stop: {L, pts}, …}`.
  - **Owed key change** (additive): `hold_log.key` for an outcome row becomes `(idx, t, d, role, "outcome")`, with role
    defaulting to "long" for existing rows. Without it, a long-CE outcome and a short-PE outcome at one (idx, t) collide,
    because they share `d`. A test is owed: two roles at one (idx, t, d) write two rows.
- **`data/hold/hold_<day>.jsonl` (additive, writer rows only):**
  - `reach: {k, R, S, atm, outside}` on every bar-close row after a break;
  - `held: {bar, L, t, R, S} | null`;
  - `fold_rule: "3r"`;
  - `writer_clause: "reach-1"`.
  `prereg` keeps its rev 5 value, so buyer rows do not change label.
- **Day state:** nothing new. R and S are read from the day's chain record, which a restart re-reads exactly. A minute whose
  ATM premiums are missing reads "could not check the reach", and the break folds.

### E.4 The forward clocks

| clause | changed here? | its forward record |
|---|---|---|
| **The expression, §E.2** | new | Starts at its first session after the code lands (`prereg: "expr-1"`). |
| **VALIDATE, buyers** (P1, P2) | no | **Continues.** Buyer presses and outcomes are unchanged; the `expr` key is additive. |
| **VALIDATE, writers** (P1-W, P2-W) | new | Starts at its first session after the code (`rev: "2W"`). Writer presses written before it (`word: null`) are rev 2's record, never pooled. |
| **The window, buyers** (§7 B1–B5, clauses 1–7) | no | **Continue.** No buyer rule moves. |
| **The window, writers** (W1, W2; the writer population's clauses 1–7) | yes: rule 3 for writers | **Reset for writers only**, at the first session after the code (`writer_clause: "reach-1"`). Rev 5's writer rows stay rev 5's own record. |
| **§C.4, W-R** | new | Starts with the writer reset. |
| **§10 side read**, PLAN P1 / P2 | no | Continue. |
| **PLAN §2.6** (a writer's STOP) | display only: it adds the reach line | A PLAN change-log line and a new §1f hash, as rev 3a's pointer; no PLAN rule moves. |

**Test browsers strip `&log=1`,** as always. The expression is computed on every GET; nothing is logged by a test.

---

## F. THE UI, IN WORDS

This covers the Validate tab and the floating window. The rules for both:
- LIGHT only, and no charts;
- never a size, and never an order path;
- the three absences are never rendered alike;
- every number is tagged [M] or [I];
- the vocabulary is in Barlow and numbers in Plex Mono, as `hold.css` does today.

### F.1 The Validate tab: "BUY CE vs SELL PE", when a setup pops up

**The slip.**
- She picks CE or PE, long or short, and a strike, then presses VALIDATE, as today. The press states her direction.
- When her zone setup names a direction on its closed bar, a quiet line reads: "setup: BUY d2 armed, 11:42 bar — the
  expression for UP is ready". It is display only; she still presses.

**The answer, top to bottom.**

1. **THE EXPRESSION**, one word, at the 88 px size the VALIDATE word uses today: **BUY CE** · **SELL PE** · **EITHER** ·
   **STAND ASIDE**.
   - The leg's ink is black (her instrument, not a verdict colour). STAND ASIDE is in the caution ink.
   - Under it, one line: "2 for buy · 3 for sell · 0 neither — of 5, a count, not odds", then DRAFT.
2. **Two cards, side by side, one per leg.** The one the word names carries a 2 px ink rule.
   - **Left, "BUY CE 23,100 · ATM":** the premium and its minute [I]; the leg's own VALIDATE word (GO / WAIT / NO) at
     40 px; its entry check word; any refusal in caution ink ("refused — you would enter a broken setup (read 12:04)").
   - **Right, "SELL PE 23,050 · at the floor":** "the floor 23,050, 42 pts OTM, BUILDING [M] · your line 23,061.5 sits
     11.5 pts above it". Then the premium [I], the writer's VALIDATE word (§B), and the reach ("strike 42 pts · one ATM
     straddle 118 pts [M] — inside: the line decides"). Then any refusal.
   - A refused card is dimmed, with its reason. It is never hidden.
   - Each card keeps its own I'M IN. She takes whichever leg she wants, and the word does not choose for her.
3. **The five facts, as a table with three columns: FOR BUY · FOR SELL · NEITHER.** One mark per row, in its column, with
   the fact's sentence under it and its tag.
   - A NEITHER shows its kind: checked-none plain, could-not-check hatched, not-shown dotted (the `Abs` styles). Its words
     say "a read" when it is one.
4. **Printed, not counted,** one line each: the drag number; the expiry line; the board's REGIME (both halves); each leg's
   σ against its VWAP.
5. **Not shown:** "a size", "an order", "odds". Once per surface, not per card.

**When she pressed SELL directly,** the same block appears for her direction. The writer's card is on the right, always,
whichever leg she pressed, so the eye learns one layout.

**An absence of the whole read** ("could not check — no NIFTY candle for 12:31; the line can't be set") replaces the word,
in the hatched style. It is never an empty space.

### F.2 The floating window: a sold option

**The head.**
- "SOLD PE 23,050 · NIFTY" and a small "YOU ARE SHORT" label.
- The word (HOLD / WATCH / FOLD / PATA NAHI) and its since-clock, with its tag when it has one: LINE BROKEN · HELD, NOISE, OI
  BLIND.
- "The premium you sold is up" replaces "Your premium is red" (rev 5 §D item 8, already registered).

**The rows.**
- **The line row** (a short PE's danger is down) reads "danger line 23,061.5 (5m swing low 11:25) · breaks below 23,056.6
  — 9 pts away [M]".
- **A reach row, writers only.** The three states, for two different sales:
  - SOLD PE 23,050, spot 23,092: "your strike 42 pts from the index · one ATM straddle 118 pts [M] — inside: the line
    decides";
  - SOLD PE 22,900, spot 23,092: "your strike 192 pts · one ATM straddle 118 pts [M] — outside: a line break is a WATCH
    for you";
  - the same PE 22,900, after a break: "— held since 12:05 · FOLD at the first 3-min close that brings your strike within
    one straddle (now 160 pts against 118)".
- **YOUR SIDE** replaces HOLDERS (built today).
- **No quiet clock:** "not shown — a writer has no quiet clock; time pays her" (built).

**The footer,** in neutral ink:
- "sold at 92.00 · now 61.50 [I] · decayed 30.50 of 92.00";
- the expiry line;
- the premium at risk to the line [I] (PLAN §2.1).
It is a description, never odds, and never a size.

**The WATCH hint** lists every condition that alone folds her (rev 5 §D.1):
- the reach item ("a 3-min close that brings your strike within one ATM straddle — now 160 pts against 118");
- rule 4's writer items;
- rule 6's families.

**Collapsed:** `WATCH · SOLD NIFTY 22900 PE · line broken 12:05, held — strike 160 · straddle 118 · since 12:05`.

**The one tone** fires on the transition into FOLD, rule 3r included. There is nothing on WATCH or HOLD.

---

## G. Change log

- **Draft (rev 0), 2026-09-26 00:16 IST (clock).** §A–§C and §E–§F were written before any run. Fingerprinted at 00:21,
  sha256 `eca1afe0debf687d56d8e35d4d42c475280b6f01267e7431b6cb6271da2e2b6c`; the copy is `rules_before_run.md` in the
  scratch folder.
- **During implementation, before any reach result was read (00:27).** §C.2 item 4 was silent on a close *while held* whose
  straddle cannot be read. It now reads "at any close where the reach is read … FOLDed", the conservative reading. The
  script had raised on its first pass before any reach was computed. What had printed by then was the expression's word
  counts per index-day (rev 0's PREMIUM), and nothing of §C.
- **Rev 0a, 2026-09-26 00:32 IST (clock): fact 5 (PREMIUM) replaced after the first run, on principle, with the counts in
  view.**
  - **What was seen first:** rev 0's PREMIUM read FOR BUY on **5,434 of 6,720** index-direction-minutes (the nine frozen
    index-days, both directions), FOR SELL on 1,118 and NEITHER on 168 (`tally.json`).
  - **Why it moved:** the reason is rev 4 §8's own, not the count. The ATM strike moves with spot. So "one leg above its
    own session VWAP, the other below" mostly records that spot has left where that strike's premiums averaged. That is a
    price-displacement read, which counts REGIME a second time.
  - **What replaced it:** one contract fixed at `t − 15` (the side log's `stamp_track` principle), and the question a
    straddle answers directly: did the move out-pay the rent?
  - **Consequential edits** (the same object): R4 and §B fact 4 now read the same fixed straddle; §E.1's row; §A.7's hazard.
  - **Timing:** the new text was fingerprinted before it was run (§D.0). §D shows **both** versions' words at her entries,
    so the change can be judged by the reviewer and by her, not by this drafter.
  - **Also fixed then (wording, no rule):** §F.2's reach example had shown a held writer at 42 pts against a 118-pt
    straddle, which is inside and would fold. The example now uses a far strike, and the short PE's line row now reads the
    swing low.
- **2026-09-26 00:43 IST (clock), while writing §D.4, after its rows were read: §C.4's unit gains rev 5 §F.1's dedup.** It is keyed
  (index, bar, L, strike, side), and trades that share it count once.
  - **Why:** the read's own eleven 09-24 sell legs were one contract breaking at one close. Without the dedup, W-R would
    count one event eleven times: the pseudo-replication 7a's unit already rules out.
  - **Which way it moves:** it cuts W-R's count and changes no fold.
- **§D, §H: added 2026-09-26 00:34–00:47 IST (clock)**, after the rev 0a run.

---

## H. What this draft could not resolve, for the review and for her

1. **The writer's 30-minute outcome (§B.3) rarely resolves.**
   - On her days 24 of 28 sell legs read `neither` in 30 minutes. The target is a 1:1 premium decay of X, and with a line
     25–400 pts away, X is 10–85 pts of premium. Excluded `neither` units could starve P1-W for 30 sessions.
   - A writer's natural horizon is the session: *time pays her*. A to-15:29 window is the candidate.
   - **Not run, not chosen.** It changes §B.3's horizon, so it is the reviewer's to argue and hers to sign.
2. **ROOM reads FOR BUY whenever no holding wall is in the way.** That was 4,329 of 6,720 minutes. On the range day (NIFTY
   09-23) the read still named BUY more often than SELL in both directions (§D.1).
   - That is VALIDATE's own target rule, inherited. Whether a range day should read more SELL is exactly what §E.2's BUY
     and SELL clauses judge.
   - Not tuned.
3. **PREMIUM (rev 0a) leans SELL by economics.** Time wins most 15-minute windows: 3,934 SELL against 2,288 BUY. That is
   what an option seller earns on average, not a construction bias. It is stated so nobody "fixes" it.
4. **An unreadable fact 5 does not refuse SELL as written.** R4 fires only when read. R3 refuses SELL when OI cannot be seen,
   so the same principle ("do not sell what you cannot see") would refuse SELL when the straddle cannot be read, which is
   09:15–09:29 and any minute with no premium.
   - On 09-25 this decided one row: the 09:35 SELL CE, with fact 5 unreadable because no premium was frozen.
   - Hers or the reviewer's, one line either way.
5. **The sell strike can be far.** On 09-24 afternoon the call top two sat at 74,200 and 74,300, so "at the wall" meant
   186–564 pts OTM.
   - The rule is principled: sell where the holding side writes. The reach and X are printed so she sees the distance.
   - Whether a sale should be refused when the wall is beyond one straddle (outside the market's move, so little to collect)
     is **not** registered.
6. **SHIELD's wall and the window's YOUR SIDE can be two strikes.** SHIELD reads the nearest of the top two at or beyond spot;
   the window reads the nearer front. R2 reads the window's, as inherited. They can differ, and the screen prints both.
7. **Her "90-minute write guard"** (her validated spine, per her profile) has no text in the repo, so it is not used. It is
   hers to state.
8. **IV against realised vol** (the seller doctrine's Q3) is not computed per minute by anything the window reads. Fact 5 is
   its price-level stand-in; it is not an IV model.
9. **The disclosure's inputs.**
   - The greeks are Black-76 [I], not the broker's.
   - 09-22 and 09-23 had the nearer fronts only, which over-fires R6.
   - Two 09-24 indices ran on [I] candles.
   - 09-21 and the 09-25 premiums were not frozen.
   - The forward rows are the only evidence.
10. **The owed code changes when she signs** (none made here):
    - `hold_log.key` for outcome rows gains the role;
    - the `expr_<day>` log;
    - the writer rows' `reach` / `held` / `3r` keys;
    - PLAN §2.6's reach line and its change-log entry and §1f hash;
    - tests: the expression's refusals and word order; the fixed straddle; the reach held / healed / 3r, and S unreadable
      folding; the writer word; the outcome key collision.
