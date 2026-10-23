# MECHANICS ATTACK: the zone setup, read by a prop-desk index-options trader

Written 2026-10-20, a market holiday (Dussehra [V]). The lens is market mechanics, execution and craft. A separate
auditor checks the records, so nothing is re-scored here.

**House rules kept.** There is no hit rate, win rate or expectancy of mine, no backtest, and no result. It is advisory
only. Any number quoted comes from her own records, and the section is named.

**Tags:**
- **[M]** is in her records.
- **[I]** is my inference as a trader.
- **[V]** was checked on the web today. Most of the sources are secondary; they are listed at the end.
- **[U]** is not verified.

---

## 0. My read in six lines

1. **The edge is real in kind.** A stretch in a broad index caused by flow reverts; a stretch caused by information
   does not. Everything below is about telling the two apart **before** the touch.
2. **d2→d3 glues two trades together.**
   - A quiet **POCKET** fade at 2.0–2.4σ.
   - An **EXHAUSTION** reversal at d3 and beyond.

   Her three records disagree only because each one measures a different half.
3. **Her 5-year record already holds the three most valuable filters:** the first touch, before 13:15, and DTE ≥ 2.
   The zone rule dropped all three.
4. **§1d is the right gate for the pocket and the wrong gate for the exhaustion.** On the face it also silences the
   exhaustion arm.
5. **Buying a CE to fade a fall is usually the worst expression,** because IV is bid at the low. Sell the PE instead,
   and buy only once the trade becomes a RIDE.
6. **A fade and a ride need opposite hold rules.** Her "I exit too early" problem lives mostly in the RIDE.

---

## 1. The mechanism: why NIFTY reverts from 2–3σ, and when it can't

### 1.1 What actually pulls price back [I]

| Force | How it works in NIFTY | Weight |
|---|---|---|
| **Temporary impact decays** | NIFTY is a 50-stock basket with futures/cash arbitrage and many liquidity providers. A burst of one-sided flow moves price further than its information justifies, and that impact decays once the burst stops. | the main reason (POCKET) |
| **Forced flow overshoots** | Stop cascades (put writers buying back, longs stopped out) run past fair value. Once the forced inventory is exhausted, price retraces ([[operator-thesis]]). | the d3 reason (EXHAUSTION) |
| **VWAP as a benchmark** | Institutional baskets worked against VWAP buy passively below it and sell above it. | a weak pull, not a magnet |
| **Dealer gamma** | The US story (dealers long gamma, so price pins) mostly does **not** hold here. Indian option buyers are retail and don't hedge. The hedgers are prop writers who are **short** gamma, so their hedges amplify moves. Pinning is mainly an expiry-afternoon effect near very large strikes. | unreliable. Her 14 Aug note found the gamma regime anti-predictive both times (n=1) [M §1b] |

So the edge is not "price goes back to VWAP". It is two narrower things:
- **noise in a quiet tape reverts** (POCKET);
- **forced flow, once spent, retraces** (EXHAUSTION).

### 1.2 VWAP and σ are cumulative, so the band has blind spots [I]

- **Early, 09:15–09:45:** σ comes from a handful of bars, and VWAP is dominated by the opening print.
  - Since 8 Dec 2025 the current-month future opens from a pre-open call auction [V]. The first bar therefore carries a
    large single-price lump of volume.
  - Bands are narrow and they lurch. A 2σ touch at 09:30 costs only a few points of movement.
  - Her 5-year pocket starts at 09:45 [M profile]. §1b(d) logged a 09:30 signal with "only 5 index band readings" [M].
- **Late:** the session σ is mostly the morning's.
  - An afternoon expansion runs faster than the band can widen, so price walks it. On 14 Aug u3 went 24467 → 24486
    while price walked up [M §1b].
  - After a wild morning it works the other way: a quiet afternoon never reaches the band.
- **VWAP moves toward price on a trend day.** A long fade "reaching VWAP" can be VWAP coming down to a flat price.
  Count a fade in index points, never as "VWAP reached".
- **Frozen versus live σ.** I read her "frozen pocket" as the band frozen at the touch.
  - Use **frozen** levels for the trade: stop and target fixed at the arm, so they don't drift.
  - Use a **live**, short-window range for the regime question. The 30-minute range percentile is already in the
    payload as `rng_r`.
  - The two answer different questions.
- **Which bands measure depth.** The tool's bands are 2–8% wider than her Kite chart [M §1c]. The READ-V2 3-minute
  bands match Kite within about 2 points [M READ-V2 §1]. Depth thresholds (2.4σ) must be read on bands that match her
  chart.

### 1.3 When the mechanism is off, and how it shows **before** the touch

| Off-condition | Why | Tape tell | OI / options tell |
|---|---|---|---|
| **Trend day** | information or fresh positioning; VWAP follows price | 0 VWAP crosses since 09:30, which held by 11:00 on every trend day [M O1]; closes riding the 1σ–2σ lane [M READ-V2 §1]; a 2nd or later d2 tag with no VWAP visit between | one side's writers absent at 09:45, \|A\| ≥ 0.8 [M O2]; futures OI rising while price falls = fresh shorts [M O3] |
| **Short-gamma cascade** | writers' stop buybacks and hedges amplify the move | 30-minute range percentile ≥ p90 and rising; 1-minute candles widening | the defending front unwinds strike by strike (PE 22,550 → 22,500 → 22,450) [M O6] |
| **News / information** | permanent repricing | VPIN high | **both legs rising** (the straddle is bid), which is her own skip rule [M profile] |
| **Gap day** | overnight information | the gap is not met by the opposite writers, or record opposing flow [M O5]; her gap-fade is dead [M §2] | — |
| **Expiry, DTE 0–1** | ATM gamma is huge; the outcome is a pin or a blow-up, both fat-tailed | her 5-year record: "expiry-day fades lost worst of all" [M PaperDesk pocket gate] | ATM OI dominates everything |
| **After 13:15** | σ is stale; close-related flows | her 5-year record: late-session fades lost [M] | — |
| **After ~15:15 (since 3 Aug 2026)** | the F&O stocks go into the cash closing auction, with no continuous matching; index futures and options trade on to 15:40 [V] | the spot index freezes or turns indicative while futures move | basis noise |
| **BANKNIFTY** | it trends (see A8) | — | — |

A pro answers "is the reverting machine on today?" at 09:45 and checks it again at every band touch. A pro does not
wait for the touch to ask.

---

## 2. The strongest attacks, ranked

### A1. The zone glues two trades together, and her three records each measure one half. **HIGH**

**The three records:**
- **5-year, about 1,200 sessions.** The first 2.0–2.4σ touch, 09:45–13:15, DTE ≥ 2, works. Deeper than 2.4σ: "the
  band is breaking, not holding — deep fades lost" [M PaperDesk `bands.js` / `core.js`].
- **TapeMap, 65 sessions.**
  - A d3 touch plus a close above the reference bar's high survives (§5c, n=19) [M].
  - d2 entries as a population are "noise everywhere — 180 NIFTY signals ≈ coin flip" [M §2].
- **The zone, §1b.** It arms at d2, fires on the reversal, and is unscored [M].

**Why they don't contradict:** there are two mechanisms.
- **POCKET** (2.0–2.4σ, first touch, quiet tape) is liquidity noise.
  - It works with an early, shallow entry.
  - It dies as depth grows, which is the band breaking.
- **EXHAUSTION** (beyond 2.4σ, typically d3, after a fast leg) is forced flow overshooting.
  - It works only **after** the forcing has ended. "A close above the reference high" tests exactly that.
  - Entering it at the touch, which is the 5-year record's "deeper than 2.4σ" bucket, loses.
- **The 180 d2 entries are a mixture:**
  - pockets that should be taken;
  - pockets that are the 2nd or 3rd touch inside a trend;
  - exhaustion legs entered too early.

  That mixture is why they average out to a coin flip.

**On the tape:**
- **Pocket:** a slow drift into the band, the range percentile low to middling, both sides writing, VWAP crosses
  climbing.
- **Exhaustion:** a one-way leg, the range percentile at p90 or above, and writers quitting strike by strike. Then a
  climax bar, then failed follow-through: heavy sell delta with no new low.

**The cost of the glue:** one trigger, one stop, one gate and one hold for two trades with opposite needs (A4, A5, A7).

### A2. Trend days: the band walks, the zone keeps arming, and nothing switches it off before the touch. **HIGH**

- **22 Sep:** 10 BUY arms during one fall. Two of them came in the same minute the engine said "NO FADE — negative
  gamma" [M §1d].
- **8 Oct:** the zone armed BUY all day, and the gate refused 23 of 26 [M day-test].
- **Mechanism.** On a trend day VWAP chases price and σ grows as price walks. That puts d2 **inside** the trend's 1σ–2σ
  lane [M READ-V2 §1], and that lane is where trend sellers **add**. Every new low re-tags d2.
- **The missing clause.** Her 5-year rule says **first** touch. The zone has no first-touch clause. Its re-arm clause
  collapses falling lows into one reference, but each new reference without a VWAP visit is still a fresh arm.
- **How a pro catches it.** The gate catches most of it, bar by bar. A pro catches it once, at 09:45, from the day card,
  and doesn't look at the d2 buy zone again until the day type changes.

### A3. Her own three best refusals are missing from the zone, and the calendar has moved. **HIGH, and the cheapest fix**

- **What the zone and §5c have:** a 09:25 start and flat by 15:15. They have no 13:15 cutoff, no DTE and no first-touch
  clause [M].
- **How DTE is counted:** calendar days to the index's own expiry [M PaperDesk `core.js`].
  - The NIFTY weekly moved to Tuesday and SENSEX to Thursday in Sep 2025 [V].
  - Her refusals (DTE < 2) now fall on **Monday and Tuesday for NIFTY** and on **Wednesday and Thursday for SENSEX**.
    The old data never refused those weekdays.
  - **Reason in DTE, never in weekdays.**
- **Holidays.** An expiry on a holiday moves to the previous trading day [V]. 20 Oct is Dussehra, a holiday on the
  secondary lists [V].
  - If so, the NIFTY weekly expired on **Mon 19 Oct**, and the PREOPEN line "Tomorrow (Tue 20 Oct) is NIFTY weekly
    expiry" is wrong.
  - 19 Oct, the day she traded the 23,200 PE, is then a **DTE 0 day** in every log.
  - This is an item for the auditor. Confirm it against the NSE notice.

### A4. §1d vetoes the exhaustion fades it should pass, and the face silences them. **HIGH for d3, LOW for pockets**

- **Mechanism of a fall into d3.** The near-ATM PE writers are being run over, and their buybacks are the fuel. At the
  exhaustion low the PE front is at its least-building moment, stalled or unwinding. That is exactly when §1d says
  ILLEGAL.
- **Her records already say this.**
  - At a d3 low the flow is structurally call-heavy, and put-heaviness arrives **after** the turn [M §4].
  - A 40% put-heavy veto would have removed 10 of 12 signals, including 9 winners [M §4].
  - §1d's "building" test is the same idea at a finer grain.
- **For the POCKET, §1d is exactly right.** A quiet 2σ dip with PE writers still adding is a defended floor.
  - 19 Oct at 11:45 is a textbook illegal pocket: NIFTY sat at the range floor.
  - The PE side went −44L / −64L / −45L at 23,000 / 23,050 / 23,100, while CE added +94L at 23,000. The floor's
    defenders had left.
  - The range broke into a trend at 13:46 [M PREOPEN log]. The gate would have kept her out.
- **The harm today.** The log keeps every row, which is right. But `signals.gate_sound` makes an illegal tap silent and
  grey [M fade-gate-on-the-face]. The best d3 reversals therefore arrive **silent** on her screen.
- **What the exhaustion needs from OI is the opposite read:**
  - the forced side's **unwind decelerating** (her own second-derivative idea, applied to the unwind instead of the
    build);
  - **fresh CE writing at the new ATM**, which becomes trapped fuel if the low holds.
  - One caution from §4 (post-hoc, n=12): the two worst trades had ΔCE ≥ 3.5× ΔPE. **Moderate** fresh CE writing is
    fuel; a one-sided CE wall is a lid [M §4].

### A5. "Fires on the reversal" is still undefined where it matters. At d2 it enters halfway to target, into the trend seller's entry. **MED–HIGH**

- **Still open:** §1b(a), the two-candle close above the reference high versus the one-candle reclaim [M].
- **The geometry is inverted.**
  - At a d2 arm the reference bar's high is often near d1.5.
  - An entry there leaves about 1.5σ to VWAP, against a d3 − 20 stop that is more than 1.5σ away.
  - A trigger built for d3 inverts the pocket trade's geometry.
- **Two signed rules collide.**
  - On a trend-down day, the bar that closes above the reference high is the pullback into −1σ…VWAP.
  - READ-V2 §E registers that same zone as the trend **SELL** entry [M].
  - So two of her signed rules fire opposite trades on the same bar, and the day card has to decide which one is live.
- **The whipsaw guard a pro uses:** confirmation from the market where the money is.
  - On the trigger bar the legs **rotate**: CE premium up, PE premium down.
  - They are **not both rising**.

  Both are her own rules: "the CE/PE pair must rotate" and the both-legs-rising skip [M profile].

### A6. Expressing the fade by buying the option. **MED–HIGH: her P&L lives here, and nothing scores it**

- **IV at a lower-band touch is bid** [I]. In NIFTY, falls come with IV up and the put skew steepening; rallies come
  with IV falling. A CE bought to fade a fall is bought at elevated IV, and it loses vega as the reversion calms things.
- **The pocket's target is small.** It is VWAP: a short index move, and §5c's median at +30m on d3 entries is modest
  [M].
  - At ATM delta ≈ 0.5 she gets half of that move.
  - Theta over a 15–60 minute hold comes off it, and so does vega.
  - On grinding days the drag record shows a third to 88% of the owed move eaten [M delta-drag; delta assumed at 0.5].
- **Buying wins only on SPEED:** a fast exhaustion reversal that turns into a RIDE beyond VWAP, where gamma pays.
- **The mirror at the top** [I]. On a rally IV is low, so a top fade is better **bought** (the PE is cheap) than sold.
  Selling the CE collects thin premium and is short gamma into a squeeze.
- **Expiry day.**
  - Buying ATM at 0 DTE is a gamma lottery.
  - Selling it carries the extra 2% ELM on short options on expiry day [V] and the closing-auction settlement jump [V].
  - Her pocket rule already refuses DTE < 2, so the fade never meets expiry day. The RIDE can.
- **What has never been scored.** The option leg has never been scored; every number is the index [M §5c caveat].
  §1h's PREMIUM fact (the straddle rising versus falling) is the right ingredient [M]. **Skew by side** is the missing
  one.

### A7. One hold window serves two trades. **MED–HIGH: her stated problem**

- **The fade's evidence.** It was measured twice [M §1, §5c]:
  - moving to breakeven costs about 13 points a trade;
  - trailing below VWAP costs about 7;
  - the +6-minute read is negative before the trade works.

  Folding a fade before VWAP, on "OI stopped building" or a flow wobble, repeats that leak.
- **The ride's evidence.**
  - On all 5 clean trend days, the day's extreme came after 13:30 [M O4].
  - A CVD divergence at a new extreme was followed by a further extreme 16 of 19 times [M ORDERFLOW-STUDY, SEEN days].

  Folding a ride on a divergence, or on one red bar, is her "exit too early".
- **The mismatch.** Her four fold reads (zone, flow, OI, VPIN) are **ride** reads. For a fade, only the structural
  line should count until VWAP.

### A8. The SELL side and BANKNIFTY. **MED: already dead-listed; the risk is habit**

**Why the upper band behaves differently [I]:**
- **Covering destroys its own fuel.**
  - Rallies here were short covering: futures OI fell on every up day, while declines were fresh shorts [M O3].
  - When covering ends, the rally pauses, but nobody is forced to sell. The fresh shorts from a fall are forced buyers
    later.
  - That matches the record. Selling u3 had a negative centre, mostly small losses and a few jackpots [M §5f].
- **Skew.** Falls are fast and convex, driven by put writers' stops. Rallies grind with IV falling. Falls overshoot;
  rallies walk.
- **Structural bid.** Domestic dip-buying puts a bid under the lower band, with no matching offer over the upper band
  [I; size U].

**Why BANKNIFTY inverts reversion [I + V]:**
- **No weekly expiry since 20 Nov 2024** [V]. One weekly benchmark is allowed per exchange, and NSE's weekly is NIFTY.
  The short-dated writer gamma that sits near spot on NIFTY every week is thin on BANKNIFTY.
- **Concentration.**
  - Under the old rules it had 12 names, the top name up to 33% and the top three about 62% [V].
  - SEBI's caps (at least 14 names, the top one ≤ 20%, the top three ≤ 45%) were phased in, with the deadline
    extended to 31 Mar 2026 [V]. Whether they were completed is [U].
  - A BANKNIFTY stretch is often one bank's information, which is §3's single-stock problem.
- **Engineered expiry moves.** SEBI's interim order of 3 Jul 2025 against Jane Street concerned BANKNIFTY index moves
  on expiry days, engineered against options positions [V]. Her L3 thesis is real, and it lived in BANKNIFTY.

**What I'd do:**
- **BANKNIFTY is RIDE-only, never a fade.** It also serves as NIFTY's information check (R12).
- **No fade at u2, ever.**
  - A top is an EXHAUSTION trade only: u3 or beyond, buy aggression failing, and a big seller print whose OI later
    confirms new shorts [M big-prints].
  - Express it by **buying the PE**.

### A9. S2 is a chase, in a market where breakouts fade. **LOW–MED**

- **S1 is supported.** NIFTY's 15-minute ORB breakouts fade [M §2]. That is S1 (sweep-and-reclaim) seen from the
  other side: the breakout is the stop run, and the reclaim is the trade. S1 is the EXHAUSTION trade when it happens at
  a legible level.
- **S2 is the losing side.** S2 buys minutes 1–5 of an ignition, which is the losing side of the ORB record unless OI
  shows the inventory draining.
- **Execution.** At her size, the fill in minute 1 of a cascade is the trade's whole cost [I].

### A10. Old data versus the 2024–26 market. **MED: it touches every number she leans on**

- The 5-year record straddles regime changes in expiries, lot sizes, margins, the open and the close (§5).
- **What transfers:** its refusals, because they rest on mechanism (DTE, the clock, depth).
- **What doesn't:** weekday effects, point sizes, and anything counted in lots.

---

## 3. Refinements, ranked by value

**Class:**
- **(a)** a pure clarification;
- **(b)** a new rule, to be pre-registered before use and logged forward;
- **(c)** display only.

### R1. Carry her own three refusals into the zone. (b): her rule, but new to the zone

- **Stamp four fields on every zone arm.** They ride alongside the row and never suppress it.
  - `first_touch`: the first d2 tag of the session on that side, or the first after a VWAP visit.
  - `before_1315`.
  - `dte`: calendar days to that index's own weekly expiry. A holiday moves the expiry to the previous trading day.
  - `pocket_ok`: all three hold.
- **Why:** they come from her ~1,200-session record and cost nothing. Counted in DTE, their mechanism survives the
  calendar change.

### R2. Split the zone into POCKET and EXHAUSTION, each with its own geometry. (b)

| | POCKET | EXHAUSTION |
|---|---|---|
| **Arm** | the first d2 touch, depth ≤ 2.4σ, 09:45–13:15, DTE ≥ 2 | low ≤ d3 (depth > 2.4σ), after a leg |
| **Trigger** | a one-candle reclaim of the frozen d2 | §5c: a close above the reference bar's high |
| **Confirm** | the legs rotate; not both legs rising | the same, plus sell delta failing (no new low on heavy delta) |
| **Gate** | §1d building | §1d shown but not gating, until it is judged by depth (R4) |
| **Stop** | beyond 2.4σ frozen at the arm, plus one median 1-minute candle (rev 5 B's buffer) | d3 − 20 (§5c) |
| **Target** | VWAP, counted in points | VWAP; then RIDE only on R5's conversion test |
| **Per day** | once per side (first touch) | once per side |

**Notes on the split:**
- **Parameters are inherited.** 2.4σ is hers, the buffer is rev 5 B's, the stop is §5c's. Nothing new needs a grid.
- **Two choices are mine** [I], and both go in the registration:
  - using 2.4σ as a **stop** (her record uses it as an entry refusal);
  - "once per side" for the exhaustion trade.
- **The two trades hand over cleanly.** The pocket's stop at 2.4σ is the exhaustion's arm: when a pocket dies, an
  exhaustion candidate is born.
- **No re-cut is needed.** The kind follows from the depth at the arm, so past rows can be labelled without re-cutting
  anything.

### R3. Day card before band. (b)

- **TREND** (READ-V2's word): no POCKET fade against it. One EXHAUSTION per side per day is allowed, to VWAP only.
- **RANGE:** both trades.
- **WAIT / no read:** neither.
- **Already half built.** READ-V2 shows an arm against the READ as "read ke khilaaf · chup" [M]. Make that the
  registered order of precedence.

### R4. Split §1d's judging by depth. Register it now, before its rows are read. (b) + (c)

- **(b)** Add one line to §1d's judging: report the legal/illegal MAE comparison separately for arms at depth ≤ 2.4σ and
  at depth > 2.4σ. Written before the rows are read, this is not a re-cut.
- **(c) On the face:** an exhaustion arm that the gate calls illegal shows **grey with its reason** ("PE front
  unwinding — normal at an exhaustion low"), not silent.
  - This changes a behaviour she approved on 23 Sep.
  - It is my disagreement, and it is hers to sign.

### R5. Two hold modes. (b)

- **FADE mode.**
  - The hard line only: R2's stop.
  - No breakeven, and no fold on flow, OI or VPIN before VWAP.
  - At VWAP the fade is finished. Past VWAP, trail band to band [M §1].
- **Converting a fade to a RIDE at VWAP.** All three must hold. For a long:
  - a 3-minute close beyond VWAP;
  - the opposite side's front quitting (the CE writers at the new ATM leaving);
  - flow ranked notable or above the same way.
- **RIDE mode.** Only §5.3's break rule can end it [M decode spec]:
  - a 3-minute futures close beyond VWAP against her, by ≥ 0.25σ;
  - two ranked against-signals inside 40 minutes;
  - or the writers flip.

  CVD divergence is a chip, never a fold. Strike-by-strike quits continuing her way mean **hold**.
- **The fold board names its mode,** so a fade is never folded by a ride's rule, and the reverse.

### R6. Expression by side and kind. (c) now; (b) later as a counted §1h fact

| Situation | Expression | Why |
|---|---|---|
| Lower-band POCKET, DTE ≥ 2 | sell the ATM (or ITM) PE | IV is bid at the low; delta, vega and theta all pay as it reverts |
| Lower-band EXHAUSTION | sell the PE; add a bought CE only after the RIDE conversion | after VWAP, speed pays for the gamma; before it, vega and time cost |
| Upper band (exhaustion only) | buy the PE | IV is cheap on rallies; a sold CE is thin premium, short gamma into a squeeze |
| RIDE at DTE 0–1 | an ITM option (high delta, small time value), or sell the opposite ATM/ITM | ATM options at 0–1 DTE melt; she already sells ATM/ITM in trends [M how-she-sells] |
| Both legs rising | nothing | her skip rule [M] |

The index line and the stop stay the same. The option is the vehicle, not the setup.

### R7. Answer §1b(a)–(d) as a trader (she delegated method questions). (a)

- **(a) Trigger:** a one-candle reclaim for POCKET. The two-candle trigger for EXHAUSTION; on §5c it halved the
  stop-outs [M].
- **(b) Stop:** POCKET beyond 2.4σ plus the buffer. EXHAUSTION at d3 − 20.
- **(c) "Market condition is right":**
  - the day card is not TREND against the trade;
  - `rng_r` is not expanding;
  - §1d is building (pocket only).
- **(d) Opening gate:**
  - Keep the 09:25 anchor in the log; that is her choice, for a clean record [M how-she-sells].
  - Trade nothing from the zone before 09:45. That is her own 5-year start, and the pre-open auction distorts the first
    bars [V].

### R8. A "band walk" strip on the face. (c)

One line per index, holding the six tells of §1.3 so they are visible **before** the touch:
- VWAP crosses since 09:30;
- consecutive closes in the 1σ–2σ lane;
- d2 tags with no VWAP visit between them;
- the `rng_r` percentile;
- the legs (rotating or both rising);
- DTE.

### R9. Record hygiene for the new market. (a)

- **Fields on every row:**
  - `dte` per index;
  - `expiry_day`;
  - `monthly_roll_week`. Near-month futures OI falls as positions roll, and that reads as covering or long exit;
  - the lot-size era;
  - OI in **units, never lots**. A NIFTY lot was 25, then 75, then 65 across 2024–26 [V].
- **19 Oct:** confirm the Dussehra expiry shift, then tag the day DTE 0.
- **15:30–15:40 is not recorded.** F&O trades to 15:40, but she decided on 29 Sep not to record those minutes [M
  `feed_health.py`]. They fall outside her 15:00 practice anyway.

### R10. Make both-legs-rising a field on every zone arm. (b), her own validated skip

A straddle bid at the band means the market is pricing information. It is the cleanest information-versus-noise test
available.

### R11. S1, S2, S5 and the phases. (a) for the mapping, (c) for the tags

- **S1 becomes the EXHAUSTION trade at a legible level:** PDL, a round number, an ORB edge, or a top-2 strike. Tag it
  "level pe sweep" for higher conviction; the rules are unchanged.
- **S2 is logged, not traded,** until it has n ≥ 20 of its own. That is her own sizing doctrine [M two-regimes].
- **S5, the skip, is a first-class row on every surface.** It funds the others [M].
- **The phases map cleanly:** balance → POCKET, run → RIDE, end → EXHAUSTION.

### R12. BANKNIFTY is ride-only, plus a cross-index check. (c)

- **BANKNIFTY zone arms** show "BANKNIFTY: fade nahi". The beep is already capped soft [M].
- **When NIFTY tags d2 while BANKNIFTY trends the same way** with its own BADA evidence, show the chip "banks le ja rahe
  — stretch information ho sakta". Banks are a large slice of NIFTY [I].

---

## 4. What I would keep exactly as is

| Keep | Why |
|---|---|
| d2 as the moment to **look** | it is the first unusual stretch, and attention is cheap |
| 3-minute canonical, triggers on closed bars only | 1-minute at d2 is noise; forming bars lied twice on 14 Aug [M] |
| Touch nothing until VWAP; no breakeven | measured twice. NIFTY re-tests the entry zone before it rotates, because liquidity providers re-test |
| Trail band to band above VWAP | the runners kept their run [M §1] |
| §1d logged alongside, never editing the log | it is the only way the gate can ever be judged |
| Near-ATM top-2 OI per side; the sequence build → stall → unwind | right. Far-OTM OI is hedging, and delta-based position limits (Dec 2025) make far OTM even cheaper to carry [V] |
| Buy side only as the scored edge; no selling at u2 | the mechanism in A8 agrees with the records |
| BANKNIFTY not faded | A8 |
| Bands left wider than Kite (false negatives only) | a ~5-point miss at 3σ never changes a trade |
| Fold on zone / flow / OI / VPIN, never a candle (for rides) | A7 |
| Her 15:00 practice, display only | from ~15:15 the F&O stocks are in the auction; the index can freeze while futures trade to 15:40 [V] |
| No backtests; forward logs decide | — |
| "Always side with the operator" | EXHAUSTION is exactly that: take the other side only after the forced flow is done |

---

## 5. Market structure 2024–26, and what it does to the band

| When | Change | Tag | Effect on the setup [I] |
|---|---|---|---|
| 20 Nov 2024 | **One weekly benchmark per exchange:** NSE kept NIFTY, BSE kept SENSEX. Index lots rose to a ~₹15L minimum contract (NIFTY 25→75, BANKNIFTY 15→30, SENSEX 10→20). An extra 2% ELM on short options on expiry day. | V (which weeklies were discontinued, and when: U) | The "an expiry every weekday" era ended. Short-dated gamma now sits on 2 days a week. BANKNIFTY is monthly-only. |
| Feb 2025 | Upfront premium from option buyers. No calendar-spread margin benefit on expiry day. | V | Thinner small-retail buying. Writers carry less naked gamma into expiry day. |
| Apr–Dec 2025 | Intraday position-limit monitoring; a new MWPL; delta-based (FutEq) OI for limits from Dec 2025. | V (secondary; dates vary by source) | Big writers can reshape near-ATM versus far-OTM size, so read OI near ATM only. |
| Sep 2025 | NIFTY expiry moved Thursday → Tuesday; SENSEX → Thursday. | V | Her DTE ≥ 2 now refuses Mon + Tue (NIFTY) and Wed + Thu (SENSEX). |
| Jul 2025 – Jan 2026 | BANKNIFTY lot 30→35→30; NIFTY 75→65 for contracts from Jan 2026. | V | Thresholds in lots don't compare across eras; use units. |
| 3 Jul 2025 | SEBI interim order against Jane Street over BANKNIFTY expiry days. | V | The L3 pattern is real, and it is now policed. |
| late 2025 – Mar 2026 | BANKNIFTY: at least 14 names, top ≤ 20%, top three ≤ 45%. | V; completion U | Less one-bank risk from here on; older BANKNIFTY data is more concentrated. |
| 8 Dec 2025 | F&O pre-open 09:00–09:15 for current-month futures, and for next-month futures in the last 5 trading days before expiry. Options are excluded. | V | The 09:15 bar is an auction lump inside VWAP, so σ is unreadable before ~09:45. |
| 3 Aug 2026 | Closing Auction Session in cash for F&O stocks. F&O normal market to 15:40. The F&O close price stays the VWAP of the last 30 minutes. Index settlement comes from the auction closes. | V (secondary; auction timings differ by source) | Bands after 15:15 are not comparable with old data. On expiry the settlement can jump away from the 15:15 index [V example]. Her 15:00 practice is mechanically right. |

**What it means for intraday mean reversion** [I; not measured]:
- **Non-expiry days now carry less short-dated gamma near spot** than the pre-Nov-2024 market did. The pin that used
  to come from some index's 0 DTE every day is gone. Reversion now has to come from liquidity noise and spent forced
  flow, which is exactly what POCKET and EXHAUSTION trade.
- **Expiry-day behaviour is concentrated:** Tuesday for NIFTY, Thursday for SENSEX. BANKNIFTY, monthly-only, should
  trend more cleanly than it did in the weekly era.
- **Fewer small retail option buyers** [U] means less retail stop fuel at reaction points. The stop-run playbook still
  works at legible levels, but the near-ATM writers' fuel matters more than retail stops.
- **Her 5-year record transfers by mechanism.** Depth, clock and DTE should carry over. Weekday effects, point sizes and
  anything counted in lots should not.

---

## 6. Monday 26 Oct: how I'd trade it (one page)

**Calendar** [V; check the NSE notices]:
- **Tue 27 Oct:** NIFTY weekly, NIFTY monthly and BANKNIFTY monthly all expire. All NSE index expiries are on Tuesday.
- **Thu 29 Oct:** SENSEX weekly.

| Index | DTE Monday | Zone fades | My role |
|---|---|---|---|
| NIFTY | 1 | refused (her DTE ≥ 2) | RIDE only, if the card says TREND |
| SENSEX | 3 | POCKET allowed, 09:45–13:15 | fades live here, if the card says RANGE **and** SENSEX futures trade enough to read σ |
| BANKNIFTY | 1 | never | RIDE only, on its own BADA evidence |

**Roll week.** October futures OI drains into November, and futures OI × price "fuel" reads as covering when it is
really a roll [I]. Read fuel off October + November combined, or skip it on Monday. The November future also goes
through the pre-open in the last 5 days [V].

**Before 09:45: no trades from the zone.**
- The gap against Friday 23 Oct's close and value, and who met it: writers and flow rank [M O5].
- The opening CVD rank.
- The legs: rotating, or both rising?

**At the 09:45 day card** [M O1/O2]:
- **TREND:** 0 crosses, \|A\| ≥ 0.8 with one side absent, flow ≥ p80.
  - RIDE via READ-V2 §E pullbacks: −1σ…VWAP on a down day, the mirror on an up day.
  - Expression: an ITM option, or sell the opposite ATM/ITM. Nothing is held overnight. The 2% ELM applies on Tuesday,
    not Monday.
  - Hold by the break rule.
  - No NIFTY band fades at all.
- **RANGE:** crosses climbing, both sides writing, \|A\| < 0.3.
  - **NIFTY:** sit (DTE 1).
  - **SENSEX, POCKET only:**
    - setup: the first 2σ touch, a one-candle reclaim, the legs rotating, §1d building;
    - expression: sell the ATM PE at the lower band;
    - management: the stop beyond 2.4σ plus the buffer; nothing until VWAP; done at VWAP.
  - **Upper band:** no sale.
- **No read:** sit.

**During the day:**
- **A NIFTY d3 EXHAUSTION after a run:** on DTE 1 I'd still pass. If she takes it: the §5c trigger, a d3 − 20 stop,
  sell the PE, and nothing until VWAP.
- **13:15:** no new fades. **15:00:** flat (her practice).
- **Log for every arm:** the kind (pocket or exhaustion), DTE, the roll-week flag and the legs. Log her blind calls at
  09:45 / 11:00 / 12:30 / 14:00 beside them.

**If she trades earlier in the week:**

| Day | NIFTY DTE | SENSEX DTE | Fade status |
|---|---|---|---|
| Wed 21 Oct | 6 | 1 | NIFTY pocket open; SENSEX refused |
| Thu 22 Oct | 5 | 0 | NIFTY open; SENSEX refused |
| Fri 23 Oct | 4 | 6 | both open |

---

## 7. Where I disagree with her, in one place

1. **"Reaching d2 IS the event."** As the moment to look, yes. As one trade, no: it is two trades.
2. **§1d silencing the face.** That is right for pockets and wrong for d3 exhaustions.
3. **Fading the upper band.** I wouldn't, and never at u2. At an exhausted top, buy the PE.
4. **Buying the CE to fade a fall.** It is usually the worst vehicle. Sell the PE.
5. **Folding a fade on OI or flow before VWAP.** Her own measurements say no.
6. **Trading the zone before 09:45.** I wouldn't. Keep the 09:25 anchor for the log only.
7. **S2.** It is a chase: log it, don't trade it.

---

## Sources (web, checked 2026-10-20; secondary unless the domain is nseindia.com)

**Expiry and margin rules (Nov 2024 – Feb 2025):**
- [Zerodha: SEBI's new rules for index derivatives](https://zerodha.com/z-connect/business-updates/sebis-new-rules-for-index-derivatives-heres-whats-changing)
- [Business Standard: SEBI tightens norms](https://www.business-standard.com/amp/markets/capital-market-news/sebi-tightens-norms-for-equity-derivatives-trading-124100300354_1.html)
- [ICRA comment on the circular](https://www.icra.in/Rating/DownloadResearchSpecialCommentReport?id=5964)

**Lot sizes:**
- [Rupeezy: lot sizes, Nov 2024](https://rupeezy.in/blog/bse-nse-lot-size-changes-for-index-derivatives)
- [Fyers: revision in index lot sizes, 2025](https://fyers.in/notice-board/revision-in-index-derivatives-contracts-lot-size/)
- [Zerodha bulletin: lot sizes from Dec 2025](https://zerodha.com/marketintel/bulletin/429705/revision-in-lot-size-of-index-derivative-contracts-from-december-30-2025)

**Expiry days and holidays:**
- [Business Standard: Thursday → Tuesday expiry](https://www.business-standard.com/markets/news/nse-bids-adieu-to-thursday-expiry-as-dates-swap-come-into-effect-explained-125082800635_1.html)
- [Share.Market: weekly expiry days](https://www.share.market/buzz/insights/weekly-expiry-days-in-indian-fo-markets/)
- [AlgoTest: 2026 holidays and expiry shifts](https://algotest.in/blog/share-market-holiday/)
- [ClearTax: NSE holidays 2026](https://cleartax.in/s/nse-holidays-2026)

**Pre-open and position limits:**
- [Business Standard: F&O pre-open from 8 Dec](https://www.business-standard.com/amp/markets/capital-market-news/nse-to-commence-pre-opening-session-in-f-o-segment-from-december-08-125110400728_1.html)
- [Value Research: SEBI rewrites F&O rules](https://www.valueresearchonline.com/stories/224848/sebi-rewrites-fo-rules-to-curb-expiry-day-speculation/)
- [Bajaj Broking: new F&O limits](https://www.bajajbroking.in/blog/sebi-notifies-new-f-and-o-rules-with-higher-index-limits-and-risk-measures)

**Closing auction:**
- [Angel One: F&O to 15:40, CAS](https://oga-prod.angelone.in/news/market-updates/nse-extends-equity-derivatives-trading-hours-till-3-40-pm-starting-august-3-2026-set-to-introduce-closing-auction-session-in-equity-cash-segment)
- [Motilal Oswal: CAS from 3 Aug 2026](https://www.motilaloswal.com/learning-centre/2026/8/introduction-of-closing-auction-session-cas-from-03-august-2026)
- [NSE: CAS page](https://www.nseindia.com/static/products-services/closing-auction-session)
- [Multibagg: NIFTY close and CAS settlement](https://www.multibagg.ai/market-pulse/articles/nifty-close-cas-settlement-explained-cmsrsjkn300290zloj3e8uojr)
- [Policy Circle: CAS and derivatives settlement](https://www.policycircle.org/?p=49645)

**BANKNIFTY composition:**
- [Business Standard: BANKNIFTY 14 stocks, caps](https://www.business-standard.com/amp/markets/news/sebi-increases-bank-nifty-stocks-to-14-from-12-caps-top-stock-s-weight-125103100269_1.html)
- [Business Standard: deadline to FY26](https://www.business-standard.com/markets/capital-market-news/exchanges-get-time-till-fy26-to-align-banknifty-finnifty-and-bankex-with-sebi-rules-125103100382_1.html)

**Jane Street order:**
- [Oxford Law blog: Jane Street and the expiry-day trap](https://blogs.law.ox.ac.uk/oblb/blog-post/2025/07/jane-street-and-expiry-day-trap-unpacking-sebis-crackdown-algorithmic)
- [Moneylife: Jane Street order](https://moneylife.in/article/jane-street-accused-of-massively-rigging-indias-derivatives-market-sebi-orders-ban-escrow-of-rs4843-crore-illegal-gains/77585.html)
