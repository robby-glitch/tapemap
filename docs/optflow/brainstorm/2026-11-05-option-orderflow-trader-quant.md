# Option order flow for NIFTY: the trader's map and the quant's filters

Written 2026-11-05 by Fable, before any build, on her word: "first look independently as a trader ... 3 mins is late ...
I want to use it in the opening trade as well ... how to filter noise from real moves ... attack it every way possible."
Draft 1. The Opus attack on it is `2026-11-05-opus-attack.md` (next to this file); the design that survives both is the spec.

Conventions as the repo's: **[M]** measured from `data/`, **[I]** inferred or chosen, counts never rates, a missing value is
never a zero. Nothing here is registered. Nothing here places an order.

---

## 0. The one structural finding: the tool needs three clocks, and today it has one

Every option-flow read in this repo today runs on her 3-minute close, and the Dext footprint behind it arrives one to two
minutes after the minute closes. For the WHO behind a 20-minute leg that is fine. For a scalp, and for the first ten minutes
of the day, it is a report about a move that is over.

What the record can actually deliver, measured on 4 Nov [M]:

| clock | source | what it carries | latency | recorded today? |
|---|---|---|---|---|
| **tick** (per trade, ~65 updates a minute on the future; options similar) | Upstox v3 socket, `full` mode, ATM ±3 CE/PE already subscribed for `senses` | ltp, ltq, ltt, vtt (cum. volume), 5-level bid/ask with sizes, tbq/tsq, OI, IV, delta, gamma, atp | seconds | **No.** The chain recorder samples it every ~10 s (5-6 snapshots a minute) into `data/chain/`; the futures' ticks are logged (`book_log`), the options' are not |
| **minute** | Dext footprint (`data/dext/`) | per-price buy/sell volume, minute delta, high/low, 40-60 price levels a minute at ATM | 1-2 min after the close | Yes, ATM ±5 |
| **close** (her 3-min bar) | chain OI × Dext delta | WHO per strike, group words, walls | 2-4 min | Yes (studies only; no module) |
| **context** (minutes to hours) | chain IV, futures OI (RASAD), VIX, profile, cross-index, DTE, clock | regime | — | Yes, scattered |

The exchange publishes OI roughly every 63 s [M, R2.3]. So nothing that needs OI can be faster than a minute, and anything
that crosses OI with flow is honest only at two minutes or more (the FIRM test). **Flow alone can be read at the tick.**
That is the design: the tick clock answers *is the push being lifted or hit right now*; the close clock answers *who is
behind it*; they are never forced into one number.

The cheapest high-value build in this whole document is therefore not a read at all: **record the option ticks** the socket
already delivers, with the same row shape as `book_log`, for the ATM ±3 contracts already subscribed. Without it the opening
read and the scalp read have no data, and every day it is not running is a day of record lost.

---

## 1. The trader's map: who is in this market and what forces them

India's index option market is a market of **writers** (prop desks, HNIs, the institutional short-vol book) against
**buyers** (retail, overwhelmingly, lifting offers in weeklies). The money is on the writing side (memory, `operator-thesis`;
the repo's own reads are built on it). Everything below follows from who is *forced*:

| participant | position | what forces them | what it looks like in the data | speed |
|---|---|---|---|---|
| **Writers** (short gamma) | short CE above, short PE below, often both | price through their strike; margin; expiry | OI at the strike falls **while buyers lift** (they are the aggressor, buying back): COVER. Then the next strike up gets written (the wall migrates 1-3 steps, 4 of 8 fast moves [M, R5]) | fastest moves of the day: 8 of 15 largest 15-min moves were short covering [M, R5] |
| **Writers defending** | same | a push into their strike that they can absorb | big aggressive buys at one premium, premium does not progress (the "80 wall", 3 Nov), OI at the strike *rises*: WRITE with sellers hitting | the wall holds for minutes to an hour; the break, when it comes, is the COVER above |
| **Buyers chasing** | long CE on a rise, long PE on a fall | FOMO at the extreme; theta | OI rises with buyers lifting at the top of the move (BUY), then OI falls with sellers hitting (DUMP) when it fails: the trapped-buyer signature (3 Nov 10:35, 11:30) | minutes |
| **Yesterday's writers** (now ITM after a gap) | under water | the gap itself | first 5 minutes: ITM CE (gap up) or ITM PE (gap down) OI falls with buyers lifting: inventory adjustment, the opening's fuel | the first 2-8 minutes |
| **Vol traders** | straddles / strangles both ways | an IV move | CE and PE both lifted (or both hit) at the same strike, net delta flow ≈ 0, IV moves | any |
| **Hedgers / spreaders** | multi-leg | margin, a view with a cap | opposite aggression at adjacent strikes in the same minute, similar size; nets to a small delta | any |

**The futures tape is the clock, the options are the fuel.** On every in-sample day the option flow moved in the same 3-min
bar as the futures, never earlier, and the delta volume in options is 330-620× the futures' [M, R4]. So the honest claim is
not "options lead". It is: *the futures tell you a move is happening; the options tell you whether it is forced (writers
running, which continues) or chased (buyers lifting, which fails), and at which strike the next forced flow sits.* The
proven futures read, effort per point (Kyle λ) at the extreme, survived the 291-row audit as the only timer. The options
read must be built to sit beside it, not to replace it.

---

## 2. How the pieces connect (the system, not a list)

```
                       CONTEXT (slow)                 CLOSE (2-4 min)               MINUTE (1-2 min)          TICK (seconds)
                 DTE · IV vs open · VIX ·       WHO per strike (OI × flow)      footprint per premium     signed flow per trade
                 fut OI run (RASAD) · profile   group words · walls · SQUEEZE   absorption · stacks ·     imbalance at the touch
                 (VAH/VAL/POC) · cross-index    PIN · trapped · implied delta   exhaustion · POC          IV tick · CVD(strike)
                        │                              │                               │                        │
                        ▼                              ▼                               ▼                        ▼
   1. which lens?  ──►  2. who is behind the lean?  ──►  3. is the push absorbed    ──►  4. is it being lifted
   (open / mid /        (writers running = fuel;          or breaking at the            or hit RIGHT NOW,
    expiry pm /         buyers chasing = fades;           premium? where is the         and how fast
    vol event)          both writing = pin)               writers' last defence?        (λ, speed, accel)
                                                                                                 │
                                                           ◄──── invalidation runs the other way ────┘
                                       (strike WHO flips COVER→WRITE · premium back under its VWAP · λ absorption at the high)
```

Reads only flow left to right. A tick-layer signal with no close-layer WHO behind it is a scalp with no thesis; a close-layer
FUEL word with the tick layer hitting bids is a thesis with no entry. The screen shows the four with their own clocks
stamped (`tick 09:21:40 · min 09:20 · close 09:20 · ctx`), so she always knows how stale each one is.

---

## 3. Noise: where it comes from, and the filter for each

This is the part the earlier AI brainstorm never did. Every filter below is [I] until the forward log says otherwise.

| # | noise source | why it fools a naive reader | filter |
|---|---|---|---|
| 1 | **Retail buyer baseline.** Aggressive buying is the resting state of a NIFTY weekly; positive delta on a strike is not news | raw CE buying reads "bullish" all day | Read every flow number against the strike's **own-day distribution** (rolling median and p90 of \|delta\| and volume, from the 6th bar) and, before that, the **same-slot reference from prior days** (`rank.py`'s pattern). Sellers hitting is rarer per unit and more informative; **COVER is the strongest read because it is forced** |
| 2 | **Moneyness.** 1 L of a 15-delta option is not 1 L of ATM | far strikes flood qty-based thresholds; on expiry day 1,311 "big" cells by qty vs 16 by delta [M, Sonnet] | Aggregates in **delta-lots** (qty × \|chain delta\| / 75); per-strike WHO stays in qty because OI is in qty; big prints sized three ways (qty, ₹ premium, delta-lots) and kept only in the day's top decile |
| 3 | **IV, not direction.** CE and PE premiums both rise on a flat index | "CE buying + PE buying" reads as two signals | Decompose the minute's premium change: dP ≈ Δ·dS + ½Γ·dS² + Vega·dIV + Θ·dt, with Δ and Γ from the chain and Vega from Black-Scholes on the chain's IV. Label the minute **DIRECTIONAL / VOL / DECAY** by which term dominates. A VOL minute's flow is not a directional read |
| 4 | **Spreads and hedges.** Buy ATM CE + sell OTM CE is a bull spread, not two opinions | per-strike sums double count | Net the delta-lots **across the whole CE ladder and the whole PE ladder** before reading direction; show the per-strike split as the WHO. Flag **PAIRED** when adjacent strikes show opposite aggression of similar size (within 30 %) in the same minute: a candidate spread, never proof |
| 5 | **The OI clock (63 s).** A minute's OI change can belong to the previous minute's trades | WHO at 1 min flips with a one-minute shift (26 % of labels [M, R2.3]) | WHO is computed only at ≥ 2-min windows and marked **FIRM** when both alignments agree; the tick layer never touches OI; the screen never says "writers covering" from flow alone |
| 6 | **Aggressor misclassification.** Dext's buy/sell method is theirs; a sampled quote (the chain's 10 s) agreed with Dext on 1,112 of 2,000 undecided-excluded minutes [M, R2] | a signed flow that is wrong a third of the time | At the tick: quote rule **at trade time** (ltt against the book at that instant), midpoint = undecided, with BVC (bulk volume classification on the 10-s premium change and its own σ) as the tie-breaker. Measure tick-vs-Dext sign agreement per minute every day as a **data-quality number** (allowed: it is not a hit rate) and show it |
| 7 | **The open (09:15-09:17).** Options open cold, no auction; the first minute is overnight limits crossing (ATM CE 09:15: 8.1 L qty, 62 price levels, range 70.85-111.45 [M, 4 Nov]) | the biggest delta of the day with no meaning | Minutes 0-1 read nothing but *where the first equilibrium forms* (the 09:16 POC) and the gap; directional reading starts at minute 2 and is tagged OPENING until 09:45 (§5) |
| 8 | **Expiry day.** Gamma huge, deltas near 0 or 1, writers defend round strikes all afternoon | every threshold floods; a pin looks like a fight | DTE is a regime key: thresholds and references by DTE bucket (0, 1-2, 3+); the PIN lens from 13:00 on 0 DTE (R4) |
| 9 | **Sparse strikes.** Far OTM prints a few lots a minute | QUIET/MIXED churn | the moved floor (1.5 L qty / 3 min [I]) stays; per-strike reads outside ATM ±3 are shown faded and never vote |
| 10 | **Gaps in the record.** Bridge down, chain hole, late start | a silent zero looks like calm | The three sentences: a value, "dekha, kuch nahi", "dekh nahi paaye" with the reason. The tick recorder's coverage is a health line |
| 11 | **Time of day.** 11:30-13:30 is thin; 14:00 unwind; 15:15 CAS freeze | mid-day "big" is small | same-slot references by day-part (the `rank.py` parts: 09:15-10:00, 10:00-12:00, 12:00-13:30, 13:30-15:15) |
| 12 | **Her own lot.** She posts, not crosses, at prop size | the tool could be reading her | Not filterable; noted. Her marked trades are stamped on the log so a study can exclude the minutes around them |

**The one rule for all of it:** a number is a signal only relative to its own normal (strike, slot, DTE). The raw number is
shown beside its rank, never alone.

---

## 4. The reads, by clock

### 4a. Tick layer (new; needs the recorder)

Per subscribed contract (ATM ±3, CE and PE), per trade:

- **signed qty** = ltq × side, side by quote rule at ltt (+1 lifted the ask, −1 hit the bid, 0 at mid → BVC share);
- **delta-lots** = signed qty × |delta| / 75;
- rolling **10-s, 30-s, 60-s** sums per contract and per side (CE ladder, PE ladder), and the **net implied delta** across both;
- **CVD(strike)** since 09:15;
- **touch imbalance**: best-bid size vs best-ask size, and the 5-level ratio, at the moment of the trade;
- **IV tick**: the chain IV per update, and its 60-s change;
- **speed** = |60-s delta-lots| / the same-slot median [I]; **acceleration** = the change of that speed over the last three
  30-s windows, sign only. (Acceleration on OI is noise by construction, 63-s clock [M, F6]; on flow it is not.)

What it may say: `lift` / `hit` / `two-sided` for the last 60 s per side, with size rank; `IV up/down with price`
(chase vs comfortable); `touch: bids stacking / asks stacking`. What it may never say: who opened or closed (that needs OI).

### 4b. Minute layer (Dext footprint, exists)

Per contract per minute, from the per-price cells:

- **absorption at a premium**: one price row (binned at 1 % of the premium, 0.05 tick floor [I, R6]) with aggressive one-sided
  volume ≥ own-day p90 and the premium's next-minute progress ≤ one bin: the wall. Confirm against the **futures footprint
  at the same minute** (underlying absorption, the audit's effort-per-point) before calling it a defended level;
- **stacked imbalances**: ≥ 3 consecutive diagonal cells at ≥ 3 : 1 [I, R6] in one direction;
- **exhaustion**: a new 6-bar premium extreme on falling volume, falling |delta| and falling |dOI| (Sonnet's `thakaan`),
  a mark only (inconclusive, small n);
- **minute POC** and whether the close is above or below it (acceptance);
- **unfinished auction**: both sides printed at the minute's high or low;
- **big print**: a cell in the day's top decile by delta-lots (and by ₹ premium for the ATM).

### 4c. Close layer (the WHO; the §1s pre-registration binds the definitions)

Unchanged from `OPTFLOW-READS-PREREG.md` C1-C8 and the Fable/Sonnet studies: WHO per strike (WRITE / BUY / COVER / DUMP /
MIXED / QUIET / OI? / FLOW?, FIRM), the four groups (CAP, FLOOR, ITM CE, ITM PE), the group word and the said lean (two
consecutive closes), the walls (top-2 OI per side, building / holding / leaving, with the wall strike's own WHO), the trapped
gauge (OI built today ≥ 4× the floor and premium ≥ 1.25× or ≤ 0.75× the day VWAP), the covering alarm (≥ 3 strikes one side),
R1-R4 as shadow stamps. One change: the window may be **2 minutes** where the FIRM test passes, 3 otherwise [I], so the
WHO reaches her a minute sooner when the data allows it.

### 4d. Context layer (exists, scattered; to be gathered into one `lens`)

- **DTE** and the expiry calendar (NSE weekly Tuesday, monthly; BSE Thursday): the regime key;
- **IV vs open** (ATM IV now / at 09:20) and **VIX vs open**: rising with price = chase; falling = writers comfortable;
- **futures OI run** (RASAD: FRESH / COVER, LIVE / SPENT): the futures' own fuel; COVER in futures + COVER at the cap is the
  two-legged squeeze;
- **profile position**: where price sits against the day's and the prior day's VAH / VAL / POC (the near-survivors: POC
  migration, LVN traverse) — a gate on which reads are allowed, never a vote;
- **cross-index**: NIFTY fresh high with BANKNIFTY below its 30-min high (near-survivor, 70 % vs 60 %) — a caution flag;
- **day part** and the **first-hour TREND tell** (the atlas: positive 9 of 11 when called 09:27-09:56, 0 of 9 after 10:00).

---

## 5. The opening read (09:15-09:45): what can honestly be said, minute by minute

Options open cold; futures arrive with an auction price (R3 regime since 7 Sep 2026, `research/opening-session-review.md`).
Minute 0's prints are the overnight book crossing. OI at 09:15 is yesterday's close plus whatever the first prints did.

| minute | what the data can say | what it must not say |
|---|---|---|
| 09:15 | the gap (fut auction price vs prior close, in σ of yesterday's range); the first equilibrium (09:16 POC per ATM strike); IV open vs yesterday's close (crush or bid) | any direction |
| 09:16-09:17 | tick layer: are the ATM CE/PE being lifted or hit, net implied delta sign, 30-s speed vs the same-slot reference of prior days | WHO (OI not yet trustworthy) |
| 09:18-09:20 | **inventory adjustment**: the ITM group (yesterday's writers, now under water after the gap) COVER or hold; the ATM/OTM group WRITE or not, at the first FIRM window | a "trend" |
| 09:20-09:30 | the opening type (below); the first walls; the first-hour TREND candidate if the leg qualifies | a said word before 2 closes agree |
| 09:30-09:45 | the normal lenses, tagged OPENING; her ZONE-3M anchor at 09:25 reads with the WHO at the band | — |

**The opening types** [I, to be pre-registered as R5 before any count]:

1. **GAP AND CAP.** Gap up; by the first FIRM window the ATM+1/+2 CE read WRITE (sellers hitting, OI up) and the ITM CE
   hold (no COVER); IV falling. Writers are selling the gap. Fade candidate; her u2 zone fits. Mirror for a gap down.
2. **GAP AND GO.** Gap up; ITM CE read COVER (OI down, buyers lifting); futures RASAD COVER run LIVE; no new cap writing
   at ATM+1/+2; IV holding or rising. Yesterday's writers are running: continuation, do not fade; the first-hour TREND
   candidate.
3. **TWO-SIDED.** CAP and FLOOR both WRITE in the first FIRM window: an early pin, a range day (common on 0-1 DTE).
4. **UNREADABLE.** OI? or FLOW? on the majority of ATM ±2: say so.

Why this is early enough: it reads at 09:18-09:20 from the tick layer and the first FIRM OI window, where today's first
3-min close is 09:17 and its Dext footprint lands at 09:19-09:20. It is not a forecast; it is the classification of what the
forced participants did in the first five minutes, which is the one thing the opening literature agrees is informative
(inventory adjustment, the weak form; §D of the review).

---

## 6. Scalping use: the ladder she reads in three seconds

A scalp (≤ 5 min hold) was her profitable population (A78: n 31, sum +192, median +6, worst −18.8 [M]); the leak was the
5-30 min hold. So the tool must not make the scalp slower. The ladder, each line with its clock:

1. **lens** (ctx): `OPENING · 2 DTE · IV −0.4 vs open · fut COVER LIVE · below VAL`
2. **who** (close): `UP FUEL · cap 23700 bhaag rahe −46L ×3 · floor likh rahe · wall 23750 CE holding`
3. **where** (min): `23700 CE: 80 wall absorbed 3× · last defence 20.9L sold @34.15 · POC 36.2 · close above`
4. **now** (tick): `CE lift 2,400 δ-lots / 60 s · p91 · accel + · asks thinning 1:3 · IV flat`
5. **ends** (all): `strike WHO → WRITE · premium < VWAP 38.1 · λ absorption at 23,720 · fut lean flips`

Line 4 is the entry trigger for a scalp; lines 1-3 are whether a scalp is allowed; line 5 is the exit. A scalp with lines
1-3 against it is shown as `tick ke saath, thesis nahi`.

---

## 7. The confidence question

She likes a confidence %. The repo forbids printing one (§5e), and the reason is good: every % this project ever printed
before a forward log existed turned out to be the sample describing itself. Both are right. The resolution:

- **Now:** a **count**, the way Jarvis already does it: `4 of 6 agree` (lens, WHO, where, now, futures λ, cross-index),
  with the dissenting pieces named. Never a %.
- **After 20 forward sessions per read** (the §1s window): the forward log's **frequency with its n** per cell, per DTE
  bucket, per day part: `COVER × AT BAND → STALL 11 of 15`. That is a % a trader can use, because it is the record's, not
  the tool's. It appears only once she has stated the pass bar, and it is shown with n beside it, never alone.
- **Never:** a weighted sum of signals rendered as a probability. Weights are gates here (§2), not averages.

---

## 8. From the pasted brainstorm: taken, changed, left

**Taken:** delta-equivalent flow (= C8, now at the tick); the premium decomposition into Δ / Γ / Vega / Θ terms as the
VOL-vs-DIRECTIONAL label; keeping transaction flow and position change as two measurements; the five questions (who is
aggressive, what exposure, where, what strategy, does the underlying confirm) as the four lines of §6; the invalidation list
as line 5; multi-leg as a netting discount and a PAIRED flag.

**Changed:** "the underlying has the final say" becomes "the futures are the clock, the options the fuel"; the 30/20/15/15/20
weights become gates; the LLM every five minutes becomes deterministic rules with an optional narrator; VWAP and order flow
on "NIFTY" become the futures' (spot has neither).

**Left:** dealer GEX (the Indian writer's sign is the opposite of the US dealer's and not knowable from public prints; the
gamma-flow proxy is kept as a map only); absorption read from option flow alone (needs the futures' confirmation); a
direction score from options alone (the studies say options do not lead).

---

## 9. Rules bent, rules kept

**Bent, on her word (4-5 Nov):**
- *One clock.* Three clocks (§0). The pre-registered close-layer definitions are unchanged; the faster layers are new reads
  with their own populations.
- *A78 "don't build for sub-5-min scalps".* Reopened: the scalps were the winning population and she asks for them. The
  5-30 min hold still gets the WHO and the voice.
- *No confidence %.* A frequency with its n, from the forward log, after the window (§7). Not before.

**Kept, because they protect her, not the repo:**
- No order path. Reads only.
- Pre-register before counting (§5c). The opening types and the tick-layer reads are written down as R5 and R6 before a
  single row is scored. Otherwise the open, the noisiest hour, will fit anything.
- Three sentences never merged; [M]/[I] on every number; populations apart (tick, minute, close, context are four logs).
- The futures' effort per point stays the timer; the options are not promoted above it until the record says so.

---

## 10. Measurement plan (what makes this a tool and not an opinion)

1. **Record first.** The option tick recorder from the next session, before any read. Every day without it is lost.
2. **Data quality, daily, shown:** tick-vs-Dext sign agreement per minute per strike; chain coverage; Dext coverage; OI clock
   lag. These are allowed numbers.
3. **Pre-register R5 (opening type) and R6 (tick-layer `lift`/`hit` at a band touch, 60-s window) with outcomes at +5 and
   +15 min, the way §1s did, with the pass bar owed by the operator and the kills written first.
4. **Forward log four populations**, write-once, replayable from the record at any start time (anytime-start).
5. **References before thresholds:** the same-slot distributions (`rank.py` pattern) for the first six bars and by DTE
   bucket, built from the recorded days, before any threshold is "tuned".
6. **Evening sheet:** rows described, never rated, until the window closes.

---

## 11. Build order (rough; the plan comes after the spec)

1. `optick_log.py`: the option tick recorder (row shape of `book_log`, ATM ±3 CE/PE, NIFTY and SENSEX; a health line).
2. `options_flow.py`: the close layer as designed (the §1s definitions, pure, fixtures from 2 and 3 Nov), plus the
   premium decomposition and the netting.
3. `optflow_tick.py`: the tick-layer sums, quote-rule and BVC, speed and acceleration, touch imbalance; its forward log.
4. `optflow_min.py`: the minute-layer footprint reads (absorption, stacks, exhaustion, POC, big prints).
5. `lens.py`: the context gather (DTE, IV vs open, RASAD, profile position, cross-index, day part) as one dict.
6. The ladder on the Jarvis card (five lines, five clocks); the opening types R5 and the tick read R6 as shadow stamps.
7. The evening replay and the data-quality sheet.

---

## 12. Questions for the attack

1. Does the Upstox `full` socket deliver every option trade, or conflated updates? (The future: 12,590 distinct ltt in
   20,001 rows [M].) If conflated, is BVC per 10 s honest enough for the tick layer?
2. Is OI in the first five minutes publishable at all, or is 09:15-09:20 OI a stale number? What does the exchange do?
3. Is the retail-baseline filter (own-day rank) enough, or does the tick layer need a cross-sectional filter (this strike
   vs all strikes at the same second) to catch a one-strike event?
4. Is the premium decomposition stable at 1 min on 0-1 DTE, where Γ dominates and IV is unstable? Or is the VOL/DIRECTIONAL
   label only honest at 3 min?
5. The opening types: are four enough, and is GAP AND GO separable from GAP AND CAP by minute 5 at all, or only by 09:30?
6. What is missing from the trader's map (§1)? Who else is forced?
7. Which of the twelve noise sources is under-weighted, and which filter is naive?
8. What would a scalper actually look at on line 4 (§6) that is not there?
9. What is the single most dangerous way this tool could fool her?
