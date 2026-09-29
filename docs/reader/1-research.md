# 1. Research: what a world-class order-flow reader reads, and how to tell one when we see it

**Role:** the researcher in the design debate. This file establishes ground truth. It designs nothing.
**Written:** 2026-09-29, after the close of the Sep NIFTY monthly expiry.
**Readers:** the designers, and the judge who will score their designs.

**How to read the tags:**
- **[Sn]** is a numbered source; the full list, with author, year and URL, is at the end.
- **[unsourced]** is my own reasoning or arithmetic, or something I could not find a source for.
- **[secondary]** means the only support is a vendor or education page, or a search-result excerpt I could not open in full.
- **[internal]** is this project's own measurement, taken from the memory files or the repo, not from the web.

---

## 0. The answer in ten lines

1. **Every school reads the leg, not the bar.** Wyckoff and Weis read effort per wave [S1][S3]. Auction theory reads the auction and its extremes [S5][S7]. The footprint teachers insist on stacks of three or more, never one cell [S9], and on divergences only at swing starts and levels, never across the session [S11].
2. **Effort versus result is the core read, and it has a number.** Kyle's lambda is the price change per unit of signed flow [S19]. Amihud's ratio is |return| per unit of volume [S20]. It is meaningful only as a *rank* against today's other legs, because the slope depends on book depth [S17].
3. **Delta alone is not direction.** Delta says who was aggressive. OI says whether positions opened or closed [S14][S15]. Price says what it achieved. The read needs all three.
4. **On expiry and roll days the classic OI table breaks.** The expiring contract's OI goes to zero by construction [S14]. Roll flow is not sentiment [S15][S16]. The directional information moves to the next month and to the options.
5. **Our delta is inferred, not observed.**
   - Upstox is a snapshot feed [S57].
   - NSE vendor feeds are one-second snapshots [S55].
   - GoCharting does not disclose how it classifies trades [S58].
   - In the literature, classifiers mislabel roughly 19–24% of trades [S28].
6. **VPIN is disputed.** At best it is a gauge of one-sidedness. It is not a validated early warning [S25][S26][S27].
7. **Microstructure explains the most common false read.** One patient participant splitting a big order produces a long run of same-sign delta with little price movement [S22][S23]. That says someone is working an order. It does not say the market is going up.
8. **Professionals put context and location first** [S39]. They re-aggregate prints before judging size [S35][S37]. They reset their levels on the new contract at the roll [S16].
9. **Honesty is part of the product.**
   - No edge claims without a forward record [S64].
   - Label every inferred quantity as inferred.
   - Show data holes.
   - "No read" is a valid output.
10. **29 Sep, 13:30–15:30** (§0.1) is the pass/fail case. On that leg a world-class reader says "short covering into expiry, absorbed; not bullish; now look at Oct". Our tool said nothing at leg scale and printed micro traps inside the base.

### 0.1 The test case: 29 Sep 2026, NIFTY Sep future, 13:30–15:30

| Quantity (as given) | Value | Derived [unsourced arithmetic] |
|---|---|---|
| Bars with positive delta | 18 of 25 | 72% of bars one-sided |
| Cumulative delta | about +7,060 lots | |
| Price change | about +40 pts | about **5.7 pts per 1,000 lots** of net buying |
| Futures OI | 7.86M → 7.12M qty (lot = 65) | about **−11,385 lots**, which is **−9.4%** of the open Sep position |

**Note on the window.** The F&O session now closes at **15:40**, not 15:30 (since 3 Aug 2026 [S41][S42]). So the Sep contract traded for 10 more minutes after this window. Pass criteria below use the full session.

| Lens | What it looks at | Its verdict on this leg |
|---|---|---|
| Wyckoff effort vs result [S1][S2] | Large effort, small result | Someone is absorbing the buying |
| OI table [S14][S15] | Price up, OI down | Short covering, not new longs |
| Delta + OI [secondary] + reasoning [unsourced] | Aggressor = buyers, and positions are closing | The aggressive buyers were closing shorts |
| Order-sign memory [S23] | 72% same-sign bars | Looks like one or a few split orders being worked, not broad new demand |
| Roll mechanics [S16] + [secondary] | Shorts roll by buying Sep and selling Oct | Part of the positive Sep delta can be roll flow. **Check Oct before calling anything.** |
| Expiry [S14] | Sep OI must reach 0 by settlement | The OI fall is partly mechanical; its *rate* and *who did it* are the information |
| CVD divergence [S12] | Price and CVD both rose | **No** classic divergence. The read lives in efficiency, not divergence [unsourced] |

**The professional read:** short covering into expiry, absorbed by passive sellers. Not bullish. The direction question moves to Oct OI and delta for the same window, and to the options chain.

**How to settle the Oct question** [unsourced reasoning]:
- If Oct OI rose by a similar amount with negative delta, the shorts **rolled**. Bearish positioning was kept.
- If Oct OI stayed flat, the shorts **closed**. The fuel for a squeeze is gone.

---

## A. Findings by topic

### A1. Wyckoff: effort vs result, absorption, climaxes, springs and upthrusts

- **The three laws** are supply and demand, cause and effect, and effort and result [S1].
- **Effort vs result.**
  - Volume is effort and price is result. Harmony between them confirms a move [S1].
  - Large effort with little result is a sign of a tiring trend [S1].
  - High volume with little movement means someone is absorbing the move [S2].
- **Scale.** Effort vs result can be judged per bar, but Wyckoff practitioners also compare it across waves and legs [S2].
  - Weis's modern adaptation argues that price unfolds in waves rather than in equal time periods.
  - It sums volume per wave, so each wave's effort can be compared with its price progress [S3].
- **Absorption.** Strong hands (Wyckoff's "Composite Operator") take in supply and remove it from the market [S1].
- **Climaxes, springs and upthrusts** [S4, secondary]:
  - A selling or buying climax is extreme, urgent volume near the end of a move.
  - A spring is a brief false break below range support that quickly returns.
  - An upthrust is the mirror: a brief false break above resistance.
- **Adaptation note** [unsourced]:
  - Wyckoff's "effort" was *unsigned* volume; he had no aggressor data.
  - Using *signed* effort (delta) is a modern extension, not canon.
  - A reader should show both kinds of effort, because they can disagree. For example, heavy volume with near-zero delta is two-sided absorption.

### A2. Auction market theory (Steidlmayer; Dalton)

- **Origin.** Peter Steidlmayer developed Market Profile at the CBOT in the 1980s; the CBOT handbook followed in 1985 [secondary]. The foundational book is *Markets and Market Logic* (1986) [S67], a bibliographic reference I did not open.
- **Value area.** It covers roughly 70% of the session's activity [secondary].
- **Initiative vs responsive** [S5] (CBOT study guide, via excerpt) and [S6]:
  - Activity is judged against the **previous day's value area**.
  - Initiative buying happens within or above prior value; initiative selling within or below it.
  - Responsive buying happens below value; responsive selling above it.
  - The impact of other-timeframe traders shows in extremes, range extension and TPO count.
- **Excess and poor extremes.**
  - Excess (a tail, or a sharp rejection at an extreme) marks the end of one auction and the start of another [S8].
  - A "lazy" extreme without a tail is a poor high or poor low [S8].
  - Dalton's view: every day should have tails at both ends to complete the structure. Missing tails suggest an incomplete auction [S7].
- **Single prints** are acceleration levels. They act as support or resistance until the market trades back through them [S7].
- **Profile shapes.**
  - A P-shape (sharp rise, then acceptance at the top) is read as **short covering**. A b-shape is read as long liquidation [S13].
  - The same article warns that both shapes can also mark reversals when they appear against the prevailing direction [S13].
  - The P = short covering reading is widely attributed to Dalton's *Markets in Profile* [secondary]. I did not verify the page.
- **Caveat.** Dalton's camp describes Market Profile as a way of understanding the market, not a ready-made trading system [S7].
- **On 29 Sep** [unsourced]: a +40-pt afternoon lift that builds acceptance near its top while OI falls is the textbook P and short-covering signature. Whether the afternoon profile was actually P-shaped is a data question for the judge.

### A3. Footprint reading

- **How bid and ask volume are assigned (Sierra Chart)** [S10]. Sierra uses the first rule that applies, from most to least accurate:
  1. an exchange-provided aggressor flag, 100% accurate (CME, EUREX and others);
  2. the trade price compared with the bid and ask;
  3. tick direction;
  4. the previous classification.
  - Numbers Bars need one-tick data with bid and ask; otherwise they are "less accurate".
- **Imbalances.**
  - A horizontal imbalance compares bid and ask at the same price.
  - A diagonal imbalance compares the bid at one price with the ask one tick higher [S10].
- **Stacking.** Three or more consecutive imbalances mean one side overwhelmed the other across several levels. One cell on its own is noise [S9].
- **Absorption.** Anomalous volume at a level, plus clear one-side dominance, plus price staying in place [S9].
- **Finished vs unfinished auction.**
  - A zero at the bar's extreme on the losing side means the auction finished.
  - Non-zero values on both sides mean it is unfinished, and the market often returns [S9].
- **Exhaustion.** Thin, one-sided prints at an extreme after an extended move, meaning the aggressor ran out [secondary]. Sierra-ecosystem studies ("Candle Taper", "Ended Auction") target this [secondary].
- **Context over pattern** [S39]:
  - Absorption in the middle of nowhere means little; the same print at a session low is information.
  - Absorption can simply be institutions exiting or rebalancing. Without follow-through it is neutral, not directional.
- **GoCharting** defines delta as volume traded at the offer minus volume traded at the bid [S58].
  - It does not say how it decides "at the offer" on NSE data: flag, quote rule or tick rule.
  - It claims tick-by-tick NSE data for footprints [S58].

### A4. The price / volume / OI table and its failure cases

| Price | OI | Classic reading [S14][S15] |
|---|---|---|
| Up | Up | New longs |
| Down | Up | New shorts |
| Up | Down | **Short covering** |
| Down | Down | Long liquidation (long unwinding) |

**Known failure cases:**

- **Roll periods.** Volume and OI spike during rollover. These are technical adjustments to keep positions, not new sentiment [S15].
- **Hedging.** High volume with flat or falling OI can be hedging, which masks the directional bias [S15].
- **Expiry.** At expiry every open position in the contract is closed, so OI goes to zero [S14]. A falling near-month OI in expiry week is therefore partly mechanical.
- **Intraday OI accuracy.** Zerodha Varsity added a 2016 note warning readers who rely on intraday OI to check its accuracy first [S14].
- **Who and why.** OI never tells you who opened a position or why [secondary]. A rising OI on a down-move can be aggressive new shorts, or a hedger buying protection.
- **Exit flow mistaken for interest.** In the expiring contract, exit flow is easy to mistake for real trading interest [S16].

**What delta adds** [unsourced synthesis]:
- The table says whether positions **opened or closed**. Delta says **which side was aggressive**.
- Positive delta with falling OI means the aggressive buyers were mainly *closing* shorts. One education source reads exactly this combination as short covering [secondary].
- Adding effort vs result gives a fifth state the four-row table cannot express: **covering (or liquidation) absorbed.** The closers push, a passive side takes the other side, and price barely moves. That is the 29 Sep leg.

### A5. Cumulative delta and its divergences

- **Definitions** [S12]:
  - Bearish divergence: price makes a higher high while CVD fails to.
  - Bullish divergence: price makes a lower low while CVD makes a higher low.
- **When CVD misleads** [S12]:
  - Divergences can persist for a long time before price responds.
  - Market conditions change.
  - Volume filters that do not suit the instrument distort it.
- **The session-scale trap** [S11]:
  - A fund working a TWAP algorithm all day produces persistent one-sided delta while the other side absorbs it.
  - ATAS's principle: CVD shows the effort and price shows the result, and the result matters more.
  - Do not scan for divergences across the whole session. Look at the first 30–60 minutes, at swing beginnings and at key levels.
  - Anchor CVD to the day and reset it daily.
- **Why one-sided delta persists** [S23]:
  - Order signs have long memory because large orders are split into many child orders of the same sign.
  - A run of positive bars is what one patient buyer looks like. It is not evidence of many independent buyers.
- **On 29 Sep** [unsourced]:
  - CVD and price both rose, so a divergence detector correctly finds nothing.
  - A reader built only on divergence therefore stays silent on this leg. The information is in *efficiency* (A6, Kyle's lambda) and *OI*, not in divergence.

### A6. Microstructure literature, in trader terms

**Order-flow imbalance (OFI)** [S17]:
- **Finding.** Over short intervals, price changes are driven mainly by OFI: the net change in supply and demand *at the best bid and ask*, counting limit orders, cancellations and market orders.
  - The relation is linear, and its slope is inversely proportional to market depth.
  - It is robust to intraday seasonality and stable across time scales.
  - The relation between price changes and **trade volume**, by contrast, is noisy and less robust.
- **Multi-level OFI.** Adding deeper book levels improves out-of-sample fit [S18].
- **Trader terms.** What the queues at the touch *do* (fill, refill, get pulled) explains price better than the traded tape alone.
- **Our feed** [unsourced / internal]: Upstox's five-level snapshots at about 2–3 per second allow an *approximate* OFI. Events between snapshots are invisible.

**Kyle's lambda: effort vs result in numbers.**
- **Definition.** In Kyle's model the price moves linearly with net signed order flow, and the slope, lambda, is the price impact per unit of flow [S19].
- **Estimation.** In practice lambda is estimated by regressing price change on signed flow over a window [secondary].
- **Amihud's ratio** |return| ÷ volume [S20] is a simpler proxy. Goyenko, Holden and Trzcinka found it performs well at measuring price impact [S21].
- **Trader terms.** "Points per 1,000 lots of net delta" is the lambda of a leg; "points per 1,000 lots of volume" is its Amihud.
  - Because the slope scales with 1/depth [S17], and depth changes through the day and thins on roll days [S16], only the **rank against today's other legs** is meaningful [unsourced].
  - On 29 Sep the afternoon leg is about 5.7 pts per 1,000 lots of net buying. Whether that is "low" is decided by the day's distribution, not by a constant.

**Square-root impact and order splitting.**
- Impact is concave in size, the "square-root law". Because liquidity near the price is thin, large orders have to be split to be digested [S22].
- Splitting creates long memory in the signs of orders [S23].
- **Trader terms.** Doubling the delta does not double the move. A long run of same-sign flow with small impact is the *normal* signature of one patient participant meeting liquidity. It is not automatically "absorption by a defender".

**VPIN.**
- **Definition** [S24]. Volume is bucketed in **volume time**, and each bucket's buy–sell imbalance is averaged over recent buckets. It is a measure of order-flow toxicity, updated without estimating hidden parameters.
- **Critiques:**
  - It is a poor predictor of short-run volatility. It peaked *after* the flash crash, not before. By construction it is correlated with volume and volatility [S25].
  - Bulk volume classification (BVC) is inferior to the tick rule, and VPIN's apparent volatility "prediction" comes from BVC's classification errors, which grow with volatility [S26].
  - Results differ substantially depending on the classification scheme. Identified "toxic periods" disagree in more than 60% of cases [S27].
- **Trader terms.** VPIN measures how one-sided the flow is per unit of volume. It is not direction and not a proven early warning. Its raw level is not comparable across days [S25].
- **In this repo** [internal]: the VPIN module reports a percentile of this session only. A cross-day reference was tried and rejected, because expiry days are a different regime.

**Trade classification: the aggressor problem.**
- **Lee–Ready** (1991) combines a quote rule with the tick rule [S32]. That is a bibliographic reference I did not open.
- **Accuracy on Nasdaq** [S28]: the quote rule is 76.4% correct, the tick rule 77.7% and Lee–Ready 81.1%. Errors concentrate in trades inside the quotes, large trades and high-volume periods [S28, via excerpt].
- **Tick rule vs BVC** [S29]: the tick rule and Lee–Ready classify better than BVC. Yet order imbalances built from either explain returns and liquidity comparably.
- **The counter-view** [S30]: BVC is better linked to proxies of *informed* trading.
- **Consequence for informed-trading estimates.** Misclassification biases them downward [S31].
- **Trader terms** [unsourced arithmetic]:
  - If a fraction *m* of trades is mislabelled symmetrically, measured delta = true delta × (1 − 2m).
  - At m = 0.2, delta is understated by 40%. The **sign** survives when flow is lopsided; the **size** does not.
- **Snapshot feeds** [internal]:
  - Every trade inside one snapshot gets one sign.
  - The repo's own analysis (`sweep.py`) shows that signing a whole interval by its last print is right with probability p² + (1−p)². That is a coin flip on balanced intervals, so it only informs when the flow is already lopsided.

### A7. What professional tools offer, and what pros say separates reads from noise

| Tool | Order-flow features | What it assumes | Note |
|---|---|---|---|
| **Bookmap** | Resting-liquidity heatmap; volume dots (total or delta); CVD; Large Lot Tracker; Absorption add-on [S34] | Deep book. Iceberg and stop detection uses **CME market-by-order (MBO)** data via Rithmic [S33] | Native iceberg detection *requires* MBO order IDs [S33] |
| **ATAS** | Footprint clusters; Cluster Search (abnormal volume, delta or trade count); **Smart Tape** (re-aggregates fragmented prints); Big Trades; DOM Levels; Speed of Tape [S35] | Tick data with aggressor | Teaches stacks of 3+ [S9] and scale discipline for divergence [S11] |
| **Sierra Chart** | Numbers Bars (bid/ask per price, diagonal imbalance, dominant-side %) [S10]; TPO and volume profile [secondary] | 1-tick data with bid/ask; says accuracy drops without it [S10] | Most explicit about its classification hierarchy |
| **Jigsaw (daytradr)** | Depth & Sales; Reconstructed Tape (re-aggregation to see size); Summary Tape; Auction Vista (depth + flow history) [S37][secondary] | Futures feeds (CQG, Rithmic and others) [secondary] | Davies: order flow is read like a story, not a rigid rule set [S37] |
| **Quantower** | Cluster chart; DOM Surface (book heatmap); Power Trades (large aggressive orders in short time); TPO [S36] | Tick data with aggressor | |
| **Exocharts** | Footprint; profiles; heatmap; **OI** and CVD plugins; cluster detection [S38] | Crypto and futures feeds | One of few with OI next to flow |
| **TradingLite** | Web heatmap and footprint (crypto) | Crypto books | Reported as having suspended operations [S38] |
| **GoCharting** | Footprint; delta; CVD; imbalance; absorption; OI per bar; NSE coverage [S58] | Claims NSE tick-by-tick [S58] | Classification method undisclosed [S58] |

**What professionals say separates a real read from noise:**
1. **Context, then location, then confirmation.** Ask "does this level matter?" before trusting any footprint signal [S39].
2. **Clusters, not cells.** Three or more stacked imbalances, not one [S9].
3. **Scale discipline.** Look for divergence at swing starts and levels only. Weight the result over the effort [S11].
4. **Re-aggregate prints before judging size.** This is the reason Smart Tape and the Reconstructed Tape exist [S35][S37].
5. **Know whether the aggressor side is flagged by the exchange or inferred** [S10].
6. **At the roll,** switch to the contract with more volume and OI, reset VWAP, POC and levels, and do not mistake exit flow for interest [S16].

**Gap in the western tools** [unsourced observation]: none of them ships a built-in *delta × OI × price read over a leg*. OI is at most a separate plugin (Exocharts). The OI-centric read that Indian index options need is a gap in these tools, not a solved feature we can copy.

### A8. Indian specifics

**Calendar and session:**
- **Expiry day.** Since 1 Sep 2025, NSE equity derivatives expire on **Tuesday**. Monthly contracts expire on the last Tuesday, or the previous trading day if that is a holiday [S40]. 29 Sep 2026 is the last Tuesday of September, so it is the Sep monthly expiry.
- **Session hours.** Since **3 Aug 2026** the F&O session ends at **15:40** [S41][S42].
- **Closing Auction Session (CAS)** for F&O-eligible stocks runs from **15:15 to 15:35** in the cash market [S41][S42]:
  - 15:20–15:30 order entry;
  - 15:28–15:30 random close;
  - 15:30–15:35 matching.
- **Settlement: sources disagree.** A pre-launch article says the derivatives settlement VWAP window moved to 15:10–15:40 [S41]. Later sources say derivatives settle off the CAS closing price [S43][S44, snippet only]. SEBI reviewed this and **retained CAS** on 10 Sep 2026 [S43]. **The exact index-futures final-settlement formula must be checked against the NSE circular** [unsourced gap].
- **Consequence** [unsourced]: from 15:15 onward the futures trade while their cash underlyings are in auction. Late-session futures flow on expiry is not like any other time of day.

**Margin and roll mechanics:**
- **Calendar-spread margin on expiry day.** Since 10 Feb 2025 there is **no calendar-spread margin benefit on expiry day** for the expiring contract [S45]. The rule comes from SEBI circular SEBI/HO/MRD/TPD-1/P/CIR/2024/132 of 1 Oct 2024. This pushes rolling to *before* expiry day [S45].
  - [unsourced inference] What is still open on expiry day is disproportionately positions that chose to close, or roll late at full margin.
- **Rollover measures** [S46]:
  - Rollover % = (mid + far month OI) ÷ total OI across series × 100.
  - Rollover cost = (next price − current price) ÷ current price × 100.
  - High rollover with a rising premium is read as bullish continuation. High rollover with a falling cost of carry is read as bearish.
  - Rollovers are most active in the last 3–5 days, peaking on expiry day [S47].
- **Who does what.** Shorts roll by buying the near month and selling the next; longs do the reverse [secondary]. NSE offers dedicated spread and roll order types ("SP", 2L/3L) [secondary].
  - **How NSE spread-book executions print on each leg's tape, and whether they carry an aggressor side: [unsourced].**
  - The CME analogue: spread-leg trades are sent without a trade summary and can have **no defined aggressor** (AggressorSide = 0) [S49].
- **Basis.** The next month trades at a premium that reflects cost of carry [S48], and futures converge to settlement at expiry [S47].

**How professionals read the next month on roll days** [S16]:
- Switch when the new contract consistently has more volume and OI.
- Reset VWAP, POC and levels on it.
- Expect choppy, VWAP-style roll execution rather than conviction.
- Do not read institutional exit flow in the expiring contract as genuine interest.

**Expiry-day manipulation precedent** [S53]:
- SEBI's interim order against Jane Street (3 Jul 2025) covered 18 expiry days. It describes aggressive morning buying of BANKNIFTY constituents and their futures, reversed in the afternoon, and an "extended marking the close" pattern, all serving large option positions.
- [unsourced inference] Expiry-day index flow can be driven by option-book economics, not direction. A reader must not read it naively.

**Options and the futures link:**
- **Parity.** Put–call parity gives a synthetic forward: forward ≈ K + C − P, with discounting [S50]. The futures and the options must agree through it. A persistent gap means carry, financing or stale quotes [S50 + unsourced].
- **Pinning.**
  - US stocks with listed options cluster at strike prices on expiration days, and hedge rebalancing and manipulation both contribute [S51].
  - S&P 500 futures are pulled to the at-the-money strike on serial-option expiries [S52].
  - For NIFTY, the evidence for pinning and "max pain" is mixed [secondary].
- **Writer OI walls as support and resistance** are practitioner lore, widely used in India [secondary]. I found no peer-reviewed NIFTY test [unsourced].
- **Who wins.** Individual traders lost money in 93% of cases in FY22–FY24. Proprietary traders and FPIs made profits, 96–97% of them from algorithmic trading [S54]. That is the base rate any "edge" claim sits against.

**Order sizes and hidden size:**
- NSE F&O has broker-side **iceberg orders**, which slice a large order into legs sized by the freeze quantity [S60]. Exchange freeze limits for index derivatives were revised in 2024 [S60].
- [unsourced inference] A large participant can appear as many exchange orders, so "big print" filters understate size. That is why re-aggregation tools exist [S35].

**Retail data feeds:**
- **NSE products.** NSE sells one-second snapshots at Level 1, 5-level and 20-level depth, plus a tick-by-tick (TBT) feed [S56].
- **Vendor feeds.** Vendors largely receive the same consolidated one-second snapshot [S55]:
  - the number of trades per second is unknown;
  - zero-volume ticks appear when only quotes change;
  - order-flow tools that need "traded at bid or ask" are limited by this.
- **Upstox.**
  - Staff say to expect about 2–3 ticks per second per instrument in full_d30 mode [S57].
  - Upstox's help centre says snapshot data does not capture the trades inside the interval [S57].
  - Upstox depth carries no per-level order counts [internal].
- **NSE MTBT** (true tick-by-tick) is colocation-only [internal]. Its trade file names the buy and sell order of every execution [S59, via a third-party parser]. **I could not verify an explicit aggressor flag** [unsourced]; the aggressor would have to be inferred by replaying the book.
- **OI cadence.** OI is sent at snapshot cadence, not per trade [secondary]. Per-bar OI change is therefore a difference between snapshots [unsourced].

### A9. Timeframes, legs and self-calibration

- **Seasonality.** Intraday volatility (and activity) follows a strong periodic U-shape, so raw intraday levels are not comparable across times of day [S61]. A "large" reading at 09:20 and one at 13:00 need different yardsticks.
- **Activity clocks.** López de Prado argues for sampling by activity (tick, volume and dollar bars) and for "information-driven" imbalance bars. These sample when signed flow departs from its expectation and have better statistical properties than time bars [S62]. VPIN is built on the same volume clock [S24].
- **Percentiles, not raw values.** VPIN users rank it as a percentile rather than reading the raw level [secondary]. Raw VPIN mechanically tracks volume and volatility [S25].
- **Leg segmentation.**
  - Weis waves cut price into swings and sum the volume per swing [S3].
  - Directional-change "intrinsic time" cuts the series at reversals of a preset size δ. After each reversal there is an overshoot that averages about δ [S63].
  - Either gives an objective, repeatable leg cut. Scaling δ to today's realized range is my inference [unsourced].
- **Why single-bar detectors are noisy:**
  - Single cells and bars fail the footprint teachers' own tests [S9][S11].
  - The price–trade-volume relation is noisy at short scales [S17].
  - Many detectors × many bars × many parameters guarantees false positives. Overfitting through repeated configuration is the documented failure mode [S64].
- **This project's own two failures** [internal]:
  - *Ranking against the session so far* made the first minutes rank against themselves, so every flow looked "pressing" and produced a false FOLD. That is the flow-rank bug.
  - *Ranking against a cross-day history* was rejected for VPIN, because expiry days are a different regime.
  - The literature points to a third option, a time-of-day-matched reference [S61]. Section D5 turns this into a choice the designers must make.

---

## B. THE WORLD-CLASS RUBRIC

**How the judge scores it.** Replay 29 Sep 2026 from 09:15 to 15:40 strictly as-of: each read uses only the data available at its timestamp. Also replay one ordinary non-expiry day, to catch rules that only work on expiry. Each capability is pass or fail on the observable behaviour stated. The **non-negotiables** (H1–H8) are gates: failing any one fails the design.

### R1. Leg segmentation
- **What it is:** cutting the session into legs and auctions (up-swing, down-swing, balance) with a reversal threshold scaled to today's volatility. Legs are not defined by bar count.
- **Why pros need it:**
  - Effort vs result is judged per wave [S2][S3].
  - Single bars are noise [S9][S11].
  - A directional-change cut is objective and repeatable [S63].
- **Pass on 29 Sep:**
  - At 14:30 and again at 15:40, the reader names the afternoon as one leg, or a base with named sub-legs, starting near 13:30. It gives the start and end times, the price range and the bar count.
  - A second replay produces the same cut.
  - Fail: 25 separate bar verdicts.
- **Data:** 5-min OHLC (GoCharting) or Upstox ticks, plus today's realized range.

### R2. Effort vs result per leg (the lambda read)
- **What it is:** for each leg, report:
  - net delta, volume, price change and OI change;
  - result per effort as points per 1,000 lots of net delta (Kyle-style) and per 1,000 lots of volume (Amihud-style);
  - both ranked against today's other legs.
- **Why pros need it:**
  - Effort vs result is Wyckoff's third law [S1].
  - Lambda and Amihud are its numbers [S19][S20][S21].
  - A rank, not a constant, because the slope depends on depth [S17].
- **Pass on 29 Sep:**
  - Once the leg is a few bars old, and on every bar after, the reader states roughly: "+7,060 lots net buying for +40 pts, about 5.7 pts per 1,000 lots; rank k of n today".
  - If the leg ranks low, it says in words "heavy buying, little progress".
  - Fail: no leg-level efficiency at all, which is what the old tool did.
- **Data:** bar delta, bar volume, close, and the leg cut from R1.

### R3. Delta × OI × price: who opened, who closed, who was aggressive
- **What it is:** classifying each leg into one of five states:
  - new longs;
  - new shorts;
  - short covering;
  - long liquidation;
  - **covering or liquidation absorbed**, when the aggressive closers make little progress.
- **Why pros need it:**
  - The OI table gives open vs close [S14][S15].
  - Delta gives the aggressor.
  - Effort vs result gives absorption [S1].
  - Delta alone misleads [S11][S12].
- **Pass on 29 Sep:**
  - The reader labels 13:30–15:30 "short covering into expiry, absorbed; not new buying; not bullish", with its numbers (OI about −11.4k lots, −9.4% of open Sep; CVD about +7.06k lots; +40 pts).
  - At no point in that window does it say "buyers in control" or "bullish" on delta alone.
- **Data:** per-bar OI (GoCharting "Open Int" / "OI Chng"), bar delta, price.

### R4. Expiry and roll mode
- **What it is:** awareness of the contract calendar. In expiry week and on expiry day the reader:
  - treats the near-month OI fall as partly mechanical;
  - tracks next-month OI, volume and delta alongside the near month;
  - computes rollover % and rollover cost;
  - flags when next-month volume passes near-month volume;
  - knows the session ends at 15:40 and that closing and settlement mechanics changed in Aug 2026.
- **Why pros need it:** [S14][S15][S16][S41][S42][S43][S45][S46][S47].
- **Pass on 29 Sep:**
  - From the open, and already on 28 Sep, the reader says "Sep expiry today; Sep OI goes to zero; positioning is read in Oct".
  - For 13:30–15:30 it shows Oct OI change and Oct delta for the same window, and resolves which case occurred:
    - (a) shorts rolled: Oct OI up by a comparable amount, with Oct delta negative; or
    - (b) shorts closed: Oct OI flat.
  - It prints rollover % after the close.
  - Fail: Sep delta read as directional without the roll caveat.
- **Data:**
  - Oct future bars or ticks and OI (a second GoCharting symbol, or Upstox);
  - the instrument expiry calendar (read from instrument data, never computed from a weekday) [internal].

### R5. Absorption at a named level (multi-bar)
- **What it is:** repeated one-sided aggression at or near a price over several bars, with no acceptance beyond it. The reader reports:
  - the level;
  - the aggressive side;
  - the quantity absorbed;
  - how many bars it lasted.
- **Why pros need it:**
  - It is the footprint definition of absorption [S9] and Wyckoff's absorption [S2].
  - Location decides whether it matters, and on its own it is neutral [S39].
- **Pass on 29 Sep:**
  - The reader names the afternoon ceiling where positive delta repeatedly failed to extend price, and counts the bars.
  - It says "absorbed here", not "reversal here", unless follow-through appears.
- **Data:** the GoCharting price ladder (bid and ask volume per row) and bar delta.

### R6. CVD divergence, at structure only
- **What it is:** divergence checked only at swing extremes and key levels, on a CVD anchored to today:
  - price makes a higher high while CVD makes a lower high;
  - price makes a lower low while CVD makes a higher low.
- **Why pros need it:** [S12], and the scale discipline in [S11].
- **Pass on 29 Sep:**
  - The reader reports **no** bearish divergence on the afternoon leg, because CVD and price both rose, and does not invent one.
  - Its "not bullish" call comes from R2 and R3.
  - It never scans for divergence across the whole session.
- **Data:** CVD and the swing points from R1.

### R7. Auction completeness at the extremes
- **What it is:** at each leg extreme, report:
  - whether the auction finished (a zero or thin print on the losing side at the edge) or is unfinished (two-sided);
  - poor highs and lows;
  - tails and excess;
  - single prints.
- **Why pros need it:** [S9][S7][S8].
- **Pass on 29 Sep:**
  - At the afternoon high, the reader states "finished" or "unfinished", with the bid and ask numbers at the top price.
  - An unfinished high is carried as a level likely to be revisited, labelled with *its contract* (Sep), because Sep stops trading today.
- **Data:** the footprint ladder at the extremes, and volume or TPO by price.

### R8. Initiative vs responsive, in value context
- **What it is:** the developing value area and POC compared with the prior day's value. Each leg is tagged initiative (outside value, moving away) or responsive (moving back toward value).
- **Why pros need it:** auction market theory [S5][S6][S7].
- **Pass on 29 Sep:**
  - The reader tags the afternoon leg as initiative or responsive, with the reference prices.
  - A +40-pt leg inside value is called rotational or responsive, not a trend.
- **Data:** volume at price (from the footprint ladder) and the prior session's profile.

### R9. Stacked imbalances as evidence, not signals
- **What it is:** three or more consecutive diagonal imbalances in one direction, attached as *evidence* to the leg read (R3 and R8). They are never standalone signals.
- **Why pros need it:**
  - The definitions come from [S9][S10].
  - Classification error inflates single-cell noise [S28][S29].
- **Pass on 29 Sep:**
  - Stacks inside the afternoon leg appear as "initiative buying at X–Y" inside the leg read.
  - They create no standalone buy marks inside the base.
- **Data:** the footprint ladder.

### R10. Profile shape of the leg and the session
- **What it is:** naming the shape: P, b, D, or double distribution.
- **Why pros need it:** P = short covering and b = long liquidation, each with a context caveat [S13].
- **Pass on 29 Sep:**
  - If the afternoon built acceptance at its top after the lift while OI fell, the reader names "P-shape, short-covering signature", consistent with R3.
  - If the shape does not match, it says so rather than forcing agreement.
- **Data:** volume at price.

### R11. Confirmation from the options side
- **What it is:**
  - strike-wise call and put OI change near the money over the same window;
  - the synthetic forward (K + C − P) compared with the future;
  - whether each wall holds;
  - the pull toward strikes near expiry.
- **Why pros need it:** parity [S50]; pinning [S51][S52]; writer walls as practitioner lore [secondary].
- **Pass on 29 Sep:**
  - For 13:30–15:30 the reader reports whether call writers held or added above, and whether put writers covered or added below.
  - It says whether that agrees with "covering absorbed".
  - The expiring series is labelled *expiring*, and next week's series is named as the one that carries forward.
- **Data:** Upstox option-chain OI per strike (snapshots) and option last traded prices.

### R12. Toxicity gauge (VPIN) as regime, not direction
- **What it is:** VPIN in volume time, shown as a percentile of today (or of a matched regime) and labelled experimental.
- **Why pros need it:** the claim is in [S24]; the critiques are in [S25][S26][S27].
- **Pass on 29 Sep:**
  - The reader shows the afternoon's VPIN percentile, captioned "one-sidedness per unit of volume; not direction".
  - On expiry it notes that roll and unwind buckets inflate the reading.
  - VPIN alone never flips a read.
- **Data:** Upstox ticks, through the existing `vpin.py` [internal].

### R13. Self-calibrated thresholds
- **What it is:**
  - every "large", "unusual" or "pressing" is a rank against today's own distribution, time-of-day matched where history allows;
  - the warm-up period is explicit.
- **Why pros need it:** seasonality [S61]; activity clocks [S62]; raw levels are not comparable [S25]; and this project's own flow-rank bug [internal].
- **Pass on 29 Sep:**
  - No rule contains a fixed lot count.
  - At 09:20 the reader says "warming, no rank yet" instead of "pressing".
  - At 13:30 every rank shows its sample size.
- **Data:** today's own series, plus a time-of-day profile if one is kept.

### R14. Persistence, hysteresis, one event = one mark
- **What it is:**
  - a read, once stated, persists until a *named* invalidation happens;
  - states change only past a margin;
  - each market event produces exactly one mark with a stable id;
  - marks never vanish silently.
- **Why pros need it:**
  - Order flow is read as a sequence, like a story [S37].
  - The rest is [internal]: the E review counted 41 flips of the OI row, and the same print was marked as absorption on one bar and as a trap on the next.
- **Pass on 29 Sep:**
  - Between 13:30 and 15:40 the leg read changes only when a named condition fires, such as acceptance above the leg high with OI rising.
  - The flip count is reported, and each flip gives its reason.
  - No print is marked both "absorption" and "trap".
- **Data:** none beyond the reads themselves.

### R15. Sequence over single-bar detectors
- **What it is:** single-bar patterns (traps, spikes) are subordinate to the leg and auction context. Inside a balance they are demoted or suppressed.
- **Why pros need it:** [S9][S11][S39][S64].
- **Pass on 29 Sep:**
  - The judge counts standalone "trap" calls inside the 13:30–15:30 base that the leg read does not support.
  - Pass = zero.
- **Data:** the leg state from R1–R3.

### R16. Agreement between tapes
- **What it is:** comparing, per leg, the GoCharting footprint delta with the Upstox tick-rule delta (and option flow). The reader reports whether they agree or are disputed.
- **Why pros need it:**
  - Classification methods disagree [S27][S28][S29].
  - A snapshot tape cannot be trusted alone [S55][S57].
- **Pass on 29 Sep:**
  - The reader states whether both tapes show net buying on the afternoon leg.
  - If they disagree, the read carries "disputed" and its confidence drops.
- **Data:** both feeds.

### R17. Day structure and the running story
- **What it is:** a whole-day classification (trend, normal, rotational, double distribution, expiry day), where the current leg sits in it, and a one-sentence day read that updates.
- **Why pros need it:** Dalton's day types [S6][secondary]; context first [S39].
- **Pass on 29 Sep:** after the close the reader summarises: "morning: ___; afternoon: short covering into Sep expiry, absorbed; positioning moved to Oct: ___ (rolled or closed)".
- **Data:** everything above.

### R18. Read relative to a position (her hold-or-fold frame)
- **What it is:** given a position (instrument, side, entry time and price), each of her four factors is reported as WITH or AGAINST, with its evidence:
  - **zone**;
  - **order flow**;
  - **OI**;
  - **VPIN**.
  "Gave up" is named the moment her side stops. Nothing is ever gated on a candle close.
- **Why pros need it:**
  - It is her stated method [internal].
  - Asking "is the market doing what it should if I'm right" is the standard tape-reader question [unsourced].
- **Pass on 29 Sep:**
  - Take a hypothetical long NIFTY CE entered at 13:45 on the positive delta.
  - The reader shows: flow WITH; OI AGAINST (covering, not new longs); zone under the absorbing ceiling; VPIN percentile shown.
  - It never calls the trade "confirmed" on delta alone, and it never waits for a bar close to say any of this.
- **Data:** all of the above, plus the position input.

### Non-negotiables for honesty (gates)

- **H1. No edge claims.**
  - Nothing on screen may show a win rate, "high probability", an expectancy or a back-tested percentage, unless it was measured *forward* on her own recorded sessions and shows n, the date range and the base rate.
  - Why: backtest overfitting is the documented failure [S64]. SEBI's retail algo framework prohibits return claims [S65, secondary]. Individual traders' base rate is a 93% loss rate [S54].
- **H2. Observed vs inferred.**
  - Delta is always labelled *inferred*: GoCharting's method is undisclosed, and Upstox uses the tick rule on snapshots.
  - OI change is labelled *snapshot-differenced*.
  - The label goes wherever the number goes [S10][S55][S57][S58].
- **H3. Data holes are visible.**
  - Gaps, the age of stale data, a disconnected extension and missing bars are shown as holes.
  - Nothing is ever interpolated or carried forward as if it were fresh.
- **H4. Warm-up honesty.** Percentile reads stay mute, and say they are mute, until their sample exists [internal: flow-rank bug].
- **H5. As-of integrity.**
  - Every read is stamped with its time and the as-of time of its data.
  - Past reads are frozen: no repainting.
  - A revision is appended as a new read, never an overwrite.
- **H6. Contract identity.**
  - Every number names its contract (Sep or Oct).
  - Contracts are never spliced silently across the roll.
  - The expiry-day caveat is automatic [S16].
- **H7. "No read" is a valid output.** When evidence conflicts, or the data cannot support a read, the reader says so. Silence is preferred to noise [S39].
- **H8. Anytime start.**
  - After a mid-session restart, the reader backfills what can be rebuilt exactly and labels what cannot [internal: anytime-start rule].
  - A restarted reader must not produce reads the uninterrupted one would not have.

---

## C. Known limits: what our data cannot do (nobody promises these)

| # | Impossible or unreliable | Why | What can honestly be said instead |
|---|---|---|---|
| 1 | **True aggressor side** | Upstox is a snapshot feed of about 2–3 ticks per second [S57]. Vendor NSE feeds are one-second snapshots [S55]. GoCharting's method is undisclosed [S58]. NSE MTBT is colocation-only, and no aggressor flag could be verified [S59][internal][unsourced]. Classifiers err on about 19–24% of trades [S28]. | "Inferred delta." The sign is fairly reliable when flow is lopsided. The size is understated by about (1 − 2m) [unsourced arithmetic]. |
| 2 | **Trade count and individual trade sizes** (Upstox) | One-second snapshots do not carry the trades in the interval [S55][S57]. Broker icebergs slice large orders [S60]. | Leg-level aggregates only. A "big trade" read needs GoCharting's claimed TBT, which the data audit must verify. |
| 3 | **Icebergs and hidden size** | Native detection needs market-by-order data (Bookmap uses CME MBO) [S33]. We have market-by-price depth only, and Upstox gives no order counts [internal]. | At most a low-confidence "refill" inference from repeated replenishment in snapshots [unsourced]. |
| 4 | **Spoofing vs genuine pulls** | Needs order-level adds and cancels. Snapshots cannot tell a cancel from a fill between frames [S55][unsourced]. | "Liquidity at X disappeared" without attribution. |
| 5 | **Who opened or closed** | OI does not identify participants [S15][secondary]. Participant-wise OI (FII / Pro / Client) is published end of day only [unsourced]. | "Positions closed on net; the aggressive side was the buyers." |
| 6 | **Separating roll or spread flow from directional flow in the near month** | Spread-leg executions mix into the tape. The CME analogue marks them as having no aggressor [S49]. NSE's treatment is [unsourced]. | On roll days, near-month delta is flagged "contaminated by roll", and direction is read from Oct and the options. |
| 7 | **Precise intraday OI** | OI arrives at snapshot cadence, not per trade [secondary]. Zerodha Varsity warns about intraday OI accuracy [S14]. | OI change per leg, not per tick, and labelled as snapshot-differenced. |
| 8 | **Validated predictive claims** | VPIN's early-warning claim is disputed [S25][S26][S27]. I found no published out-of-sample footprint edge on NIFTY [unsourced: absence]. | Describe states, not probabilities. Forward-logged record only (H1). |
| 9 | **Reading the closing auction** | CAS runs in cash stocks, which are not in our feed. Sources disagree on the settlement mechanism [S41][S42][S43][S44]. | "From 15:15 the cash underlyings are in auction; late futures flow is expiry-distorted." |
| 10 | **SENSEX depth parity with NIFTY** | Upstox D30 depth is NSE-only [internal]. | Degrade the SENSEX reads and say so. |
| 11 | **Absolute thresholds across days** | Lambda, OFI and VPIN depend on depth and regime [S17][S25]. Expiry days are their own regime [internal]. | Ranks within today, or within a matched regime (see D5). |

---

## D. Five places where the literature and practice disagree (the designers must pick a side)

### D1. What *is* "order flow": traded delta, or book imbalance?
- **Literature:**
  - Price changes follow OFI at the touch (adds, cancels and fills). The relation with trade volume is noisy and less robust [S17].
  - Adding deeper levels helps further [S18].
- **Practice:** footprints, CVD and delta are all trade-based [S10][S12]. GoCharting gives us exactly that.
- **Stakes on 29 Sep:** only book imbalance can *show* the passive seller refilling the offer, which is absorption observed directly. Delta can only imply it from low efficiency.
- **Choose:** delta primary with OFI as a second tape (from Upstox 5-level snapshots), or OFI primary. Either way, say which one each read rests on.

### D2. Absorption: a reversal signal, or ordinary liquidity?
- **Practice:** a defender at the level. Wyckoff treats absorption at support as bullish [S2][secondary]. The footprint canon reads it as a large participant controlling the level [S9].
- **Literature:** impact is concave, and split metaorders make one-sided, low-impact flow the *normal* state [S22][S23]. Practitioners also say absorption alone is neutral without follow-through [S39].
- **Choose:** absorption as a *signal*, or as a *state of efficiency* that needs follow-through, a location and OI before it means anything.

### D3. Is the OI table directional on expiry and roll days?
- **Indian education practice:** OI change is read directionally every day [S14][S47].
- **Against that:**
  - Roll spikes are technical, not sentiment [S15].
  - Expiring OI goes to zero by construction [S14].
  - Exit flow gets mistaken for interest [S16].
  - The calendar-spread margin rule reshapes who is still open on expiry day [S45].
- **Choose:** switch off the near-month OI read on expiry day (and decide from when); read combined OI across series [S46]; or read the next month only.

### D4. VPIN: early warning, or artefact?
- **For:** Easley, López de Prado and O'Hara present it as a toxicity measure that warns of stress [S24].
- **Against:**
  - Andersen and Bondarenko find it follows volume and volatility and is poor at prediction [S25].
  - Its volatility "prediction" is a classification artefact [S26].
  - Toxic periods disagree across classification schemes in more than 60% of cases [S27].
- **Practice:** a gauge.
- **Choose:** a gauge shown as context; one factor in her hold/fold four; or drop it. Also decide the bucket size and the reference distribution.

### D5. Calibration and clock: fixed thresholds on time bars, or ranks on legs?
- **Practice:** fixed rules on clock bars: three stacked imbalances, ratio thresholds, big-trade size filters [S9][S35].
- **Literature:**
  - activity clocks [S62];
  - waves and legs [S3][S63];
  - time-of-day seasonality [S61];
  - raw levels are not comparable across days [S25].
- **A second split inside "ranks"** [internal]:
  - A **session-own** reference is blind during warm-up. That is the flow-rank bug.
  - A **cross-day** reference mixes regimes. That is why the VPIN history reference was rejected.
  - A **time-of-day-matched, regime-matched** reference is the literature's answer [S61], but it needs history the project has refused to trust across expiries.
- **Choose:** the unit (5-min bar or leg), the reference (session, cross-day, or matched), and what happens during warm-up.

---

## Sources

| # | Author(s) | Year | Title / venue | URL |
|---|---|---|---|---|
| S1 | Fraser, B. | 2015 | "The Laws of Wyckoff," StockCharts | https://articles.stockcharts.com/article/articles-wyckoff-2015-12-the-laws-of-wyckoff |
| S2 | Villahermosa, R. | n.d. | "The Law of Effort vs Result," Trading Wyckoff | https://tradingwyckoff.com/en/effort-vs-result/ |
| S3 | Weis, D. H. | 2013 | *Trades About to Happen* (Wiley); wave-volume summary in ATAS, "How to use the Weis Waves indicator" (n.d.) | https://www.amazon.com/Trades-About-Happen-Adaptation-Wyckoff/dp/0470487801 ; https://atas.net/atas-possibilities/indicators/how-to-use-the-weis-waves-indicator/ |
| S4 | Villahermosa, R.; FXOpen (secondary) | n.d. | Spring, upthrust and climax definitions | https://tradingwyckoff.com/en/spring-shakeout/ ; https://fxopen.com/blog/en/the-wyckoff-trading-method/ |
| S5 | Chicago Board of Trade | 1980s–90s | *A Six-Part Study Guide to Market Profile* (read via excerpt; the PDF was too large to fetch) | https://www.profiletrading.com/cbot-a-six-part-study-guide-to-market-profile.pdf |
| S6 | Dalton, J., Jones, E., Dalton, R. | 1990; 2nd ed. 2013 | *Mind Over Markets* (Wiley), bibliographic; initiative/responsive definitions via secondary summaries | https://www.wiley.com/en-us/shop/general-finance-investments/mind-over-markets-power-trading-with-market-generated-information-updated-edition-2nd-edition-p-9781118531730 |
| S7 | ATAS | 2020 | "Analyzing TPO: 5 important elements in Jim Dalton's opinion" | https://atas.net/volume-analysis/basics-of-volume-analysis/analyzing-tpo-5-important-elements-in-jim-daltons-opinion/ |
| S8 | Rajandran R. | 2016 | "Market Profile – Excess (End of Auction)," Marketcalls | https://www.marketcalls.in/market-profile/market-profile-excess-end-of-auction.html |
| S9 | ATAS Learn | n.d. | "Footprint Chart Patterns: Stacking, Absorption & Auction Types" | https://learn.atas.net/volume-basics/volume-analysis/footprint-patterns |
| S10 | Sierra Chart | n.d. | "Numbers Bars" documentation | https://www.sierrachart.com/index.php?page=doc%2FNumbersBars.php |
| S11 | ATAS Learn | n.d. | "Divergence Scale and Practical Workflow" (the session CVD divergence trap) | https://learn.atas.net/volume-basics/volume-analysis/divergence-scale-and-workflow |
| S12 | Burgstaller, M. | 2023 | "Cumulative Volume Delta (CVD): How to Read & Trade It," ATAS | https://atas.net/blog/cvd-pro/ |
| S13 | NinjaTrader | 2026 | "Understanding the 4 common volume profile shapes" | https://ninjatrader.com/futures/blogs/trade-futures-understanding-the-4-common-volume-profile-shapes/ |
| S14 | Rangappa, K. | n.d. (note dated 2016) | "Open Interest," Zerodha Varsity, Module 4, ch. 12 | https://zerodha.com/varsity/chapter/open-interest/ |
| S15 | Bookmap | 2024 (updated) | "Interpreting Open Interest in Futures Markets for Better Trades" | https://bookmap.com/blog/interpreting-open-interest-in-futures-markets-for-better-trades |
| S16 | Bookmap | 2025 | "Trading Around Expiry: How Futures Liquidity Shifts When Contracts Roll Over" | https://bookmap.com/blog/trading-around-expiry-how-futures-liquidity-shifts-when-contracts-roll-over |
| S17 | Cont, R., Kukanov, A., Stoikov, S. | 2014 | "The Price Impact of Order Book Events," *J. Financial Econometrics* 12(1):47–88 | https://arxiv.org/abs/1011.6402 |
| S18 | Xu, K., Gould, M., Howison, S. | 2019 | "Multi-Level Order-Flow Imbalance in a Limit Order Book" | https://arxiv.org/abs/1907.06230 |
| S19 | Kyle, A. S. | 1985 | "Continuous Auctions and Insider Trading," *Econometrica* 53(6) | https://www.econometricsociety.org/publications/econometrica/1985/11/01/continuous-auctions-and-insider-trading |
| S20 | Amihud, Y. | 2002 | "Illiquidity and Stock Returns," *J. Financial Markets* 5:31–56 | https://www.cis.upenn.edu/~mkearns/finread/amihud.pdf |
| S21 | Goyenko, R., Holden, C., Trzcinka, C. | 2009 | "Do Liquidity Measures Measure Liquidity?" *JFE* 92:153–181 | https://www.sciencedirect.com/science/article/abs/pii/S0304405X09000099 |
| S22 | Tóth, B., Lempérière, Y., Deremble, C., de Lataillade, J., Kockelkoren, J., Bouchaud, J.-P. | 2011 | "Anomalous Price Impact and the Critical Nature of Liquidity," *Phys. Rev. X* 1:021006 | https://arxiv.org/abs/1105.1694 |
| S23 | Lillo, F., Farmer, J. D. | 2004 | "The Long Memory of the Efficient Market," *SNDE* 8(3) | https://www.degruyterbrill.com/document/doi/10.2202/1558-3708.1226/html |
| S24 | Easley, D., López de Prado, M., O'Hara, M. | 2012 | "Flow Toxicity and Liquidity in a High-frequency World," *RFS* 25(5):1457–1493 | https://academic.oup.com/rfs/article-abstract/25/5/1457/1569929 |
| S25 | Andersen, T. G., Bondarenko, O. | 2014 | "VPIN and the Flash Crash," *J. Financial Markets* 17:1–46 | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1881731 |
| S26 | Andersen, T. G., Bondarenko, O. | 2015 | "Assessing Measures of Order Flow Toxicity and Early Warning Signals for Market Turbulence," *Review of Finance* 19(1):1–54 | https://academic.oup.com/rof/article-abstract/19/1/1/2886427 |
| S27 | Pöppe, T., Moos, S., Schiereck, D. | 2016 | "The Sensitivity of VPIN to the Choice of Trade Classification Algorithm," *JBF* 73:165–181 | https://ideas.repec.org/a/eee/jbfina/v73y2016icp165-181.html |
| S28 | Ellis, K., Michaely, R., O'Hara, M. | 2000 | "The Accuracy of Trade Classification Rules: Evidence from Nasdaq," *JFQA* 35(4) | https://www.researchgate.net/publication/227347340_The_Accuracy_of_Trade_Classification_Rules_Evidence_from_Nasdaq |
| S29 | Chakrabarty, B., Pascual, R., Shkilko, A. | 2015 | "Evaluating Trade Classification Algorithms: BVC versus the Tick Rule and Lee-Ready," *JFM* 25:52–79 | https://ideas.repec.org/a/eee/finmar/v25y2015icp52-79.html |
| S30 | Easley, D., López de Prado, M., O'Hara, M. | 2016 | "Discerning Information from Trade Data," *JFE* 120(2):269–285 | https://ideas.repec.org/a/eee/jfinec/v120y2016i2p269-285.html |
| S31 | Boehmer, E., Grammig, J., Theissen, E. | 2007 | "Estimating the Probability of Informed Trading: Does Trade Misclassification Matter?" *JFM* | https://www.sciencedirect.com/science/article/abs/pii/S138641810600036X |
| S32 | Lee, C., Ready, M. | 1991 | "Inferring Trade Direction from Intraday Data," *Journal of Finance* 46(2) (bibliographic; not opened) | n/a |
| S33 | Bookmap | n.d. | "Stops and Icebergs: How to Detect Hidden Orders Using MBO Data"; "MBO Bundle" | https://bookmap.com/blog/stops-and-icebergs-how-to-detect-hidden-orders-using-mbo-data ; https://bookmap.com/mbo-bundle/ |
| S34 | Bookmap | n.d. | Features page | https://bookmap.com/en/features |
| S35 | ATAS | n.d. | "Big Trades" (help); "Smart Tape" (blog); platform overview | https://help.atas.net/en/support/solutions/articles/72000602332-big-trades ; https://atas.net/blog/smart-tape/ ; https://atas.net/blog/getting-acquainted/ |
| S36 | Quantower | n.d. | Help: "Power Trades"; "Cluster chart" | https://help.quantower.com/quantower/analytics-panels/chart/power-trades ; https://help.quantower.com/quantower/analytics-panels/chart/volume-analysis-tools/cluster-chart |
| S37 | Davies, P. (Jigsaw Trading) | 2014 | "Introduction to Order Flow"; Lesson 6, "Reconstructed Tape" | https://www.jigsawtrading.com/wp-content/uploads/2014/02/IntroductionToOrderFlow.pdf ; https://www.jigsawtrading.com/learn-to-trade-free-order-flow-analysis-lessons-lesson6/ |
| S38 | Exocharts (n.d.); ATAS (2026) | n.d. / 2026 | Exocharts features; "The Best Heat Maps in 2026" (TradingLite status) | https://exocharts.com/features.html ; https://atas.net/blog/best-heatmap-trading-software-2026/ |
| S39 | MB Trading (Substack) | n.d. | "Order Flow Through the Auction Lens (Part 4/6)" | https://mbtradingllc.substack.com/p/order-flow-through-the-auction-lens-7fc |
| S40 | ICICI Direct; SEBI | 2025 | "Revised expiry days for NSE F&O"; SEBI circular, May 2025 | https://www.icicidirect.com/futures-and-options/articles/revised-expiry-days-for-nse-futures-and-options ; https://www.sebi.gov.in/legal/circulars/may-2025/final-settlement-day-expiry-day-for-equity-derivatives-contracts_94189.html |
| S41 | Kotak Neo (uncredited) | 2026-06-01 | "NSE extends derivatives trading to 3:40 PM from 03 August 2026" | https://www.kotakneo.com/news/market-news/nse-derivatives-trading-extended-3-40-pm-august-2026-closing-auction/ |
| S42 | Lodha, N. | 2026-08-03 | "New F&O closing auction rules," NiftyTrader | https://www.niftytrader.in/markets/new-fo-closing-auction-rules-india-2026/ |
| S43 | Ved, V. | 2026-09-11 | "SEBI reviews derivatives settlement price; CAS stays," Kotak Neo | https://www.kotakneo.com/news/regulations/closing-auction-session-sebi-derivatives-settlement-price/ |
| S44 | Balas, V. | 2026 | "A Settlement Price the Market Declines to Adopt: Evidence from India's Closing Auction," SSRN (search snippet only) | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7502458 |
| S45 | ICICI Securities; SEBI | 2025; 2024 | "Calendar spreads in F&O after SEBI's new rules"; circular SEBI/HO/MRD/TPD-1/P/CIR/2024/132 | https://www.icicidirect.com/futures-and-options/articles/calendar-spreads-in-f-o-after-sebi-s-new-rules-what-you-need-to-know ; https://www.cse-india.com/upload/upload/Oct_011024.pdf |
| S46 | ICICI Direct | 2022 | "Demystifying rollover and rollover percentage" | https://www.icicidirect.com/ilearn/futures-and-options/articles/demystifying-rollover-and-rollover-percentage |
| S47 | Kadam, R. | 2026 (updated) | "Futures Roll-Over: Interpreting Basis, Cost-of-Carry & Open Interest," 5paisa | https://www.5paisa.com/stock-market-guide/derivatives-trading-basics/futures-rollover-basis-cost-of-carry-open-interest |
| S48 | Rangappa, K. | 2018 | "Calendar Spreads," Zerodha Varsity, Module 10, ch. 15 | https://zerodha.com/varsity/chapter/calendar-spreads/ |
| S49 | CME Group | n.d. | "MDP 3.0 – Trade Summary" (AggressorSide = 0; spread legs) | https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457418925/MDP+3.0+-+Trade+Summary |
| S50 | CME Group; AnalystPrep | n.d. | "Put-Call Parity"; "Put-Call-Forward Parity" | https://www.cmegroup.com/education/courses/introduction-to-options/put-call-parity ; https://analystprep.com/cfa-level-1-exam/derivatives/put-call-forward-parity-european-options/ |
| S51 | Ni, S. X., Pearson, N. D., Poteshman, A. M. | 2005 | "Stock Price Clustering on Option Expiration Dates," *JFE* 78(1):49–87 | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=519044 |
| S52 | Golez, B., Jackwerth, J. C. | 2012 | "Pinning in the S&P 500 Futures," *JFE* 106(3):566–585 | https://ideas.repec.org/a/eee/jfinec/v106y2012i3p566-585.html |
| S53 | Oxford Business Law Blog; ECGI | 2025 | Analyses of SEBI's interim order against Jane Street (3 Jul 2025) | https://blogs.law.ox.ac.uk/oblb/blog-post/2025/07/jane-street-and-expiry-day-trap-unpacking-sebis-crackdown-algorithmic ; https://www.ecgi.global/publications/blog/expiry-day-and-the-governance-of-algorithmic-trading-the-jane-street-episode |
| S54 | SEBI | 2024-09-23 | Press release: 93% of individual F&O traders incurred losses, FY22–FY24 | https://www.sebi.gov.in/media-and-notifications/press-releases/sep-2024/updated-sebi-study-reveals-93-of-individual-traders-incurred-losses-in-equity-fando-between-fy22-and-fy24-aggregate-losses-exceed-1-8-lakh-crores-over-three-years_86906.html |
| S55 | Rajandran R. | 2019 | "Tick Data Vendors and Quality of Tick Datafeeds," Marketcalls | https://www.marketcalls.in/softwares/data-vendors-and-quality-of-datafeeds.html |
| S56 | Marwaha, K. | 2016 | "The 4 Levels of Real Time Data from NSE, BSE & MCX," TrueData | https://www.truedata.in/blog/levels-real-time-data-nse-bse-mcx |
| S57 | Upstox community (Ketan, staff); Upstox Help Centre | 2025-11-04; n.d. | "Ticks per second for websocket"; "Snapshot vs TBT data" | https://community.upstox.com/t/ticks-per-second-for-websocket/12349 ; https://upstox.com/help-center/what-is-the-difference-between-snapshot-data-and-tick-by-tick-tbt-data-263407/ |
| S58 | GoCharting | n.d. | "NSE market data"; "Delta & cumulative delta bars"; "Cluster (footprint) charts" | https://gocharting.com/trading/market-data/nse ; https://gocharting.com/docs/orderflow/delta-and-cumulative-delta-bars ; https://gocharting.com/docs/orderflow/cluster-aka-footprint-chart |
| S59 | NSE (spec not opened: fetch timed out); nsetick release notes | 2024; n.d. | MTBT API Specification v6.3; nsetick v0.2.0 ("NSE's trade file names the buy and sell order of every execution") | https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Realtime_CM_CD_TBT%20ver%206.3.pdf ; https://github.com/arnav127/nsetick/releases/tag/v0.2.0 |
| S60 | Zerodha Support; TeamLease RegTech | n.d.; 2024 | "What are iceberg orders"; NSE circular on quantity freeze limits for indices (28 Mar 2024) | https://support.zerodha.com/category/trading-and-markets/charts-and-orders/order/articles/iceberg-orders ; https://teamleaseregtech.com/updates/article/31037/nse-issued-a-circular-regarding-quantity-freeze-limit-for-indices/ |
| S61 | Andersen, T. G., Bollerslev, T. | 1997 | "Intraday Periodicity and Volatility Persistence in Financial Markets," *J. Empirical Finance* 4:115–158 | https://finance.martinsewell.com/stylized-facts/volatility/AndersenBollerslev1997b.pdf |
| S62 | López de Prado, M. | 2018 | *Advances in Financial Machine Learning*, ch. 2 (Wiley), via study notes | https://reasonabledeviations.com/notes/adv_fin_ml/ |
| S63 | Glattfelder, J. B., Dupuis, A., Olsen, R. B. | 2011 | "Patterns in High-Frequency FX Data: Discovery of 12 Empirical Scaling Laws," *Quantitative Finance* 11(4) | https://www.researchgate.net/publication/46462361_Patterns_in_high-frequency_FX_data_Discovery_of_12_empirical_scaling_laws |
| S64 | Bailey, D., Borwein, J., López de Prado, M., Zhu, Q. J. | 2014 | "Pseudo-Mathematics and Financial Charlatanism," *Notices of the AMS* 61(5):458–471 | https://www.ams.org/notices/201405/rnoti-p458.pdf |
| S65 | SEBI (circular 4 Feb 2025; extension Sep 2025); return-claim ban per secondary summary | 2025 | "Safer participation of retail investors in algorithmic trading" | https://www.sebi.gov.in/legal/circulars/sep-2025/extension-of-timeline-for-implementation-of-sebi-circular-dated-february-04-2025-on-safer-participation-of-retail-investors-in-algorithmic-trading-_96979.html |
| S66 | Jim Dalton Trading | n.d. | "Poor high and poor low" (live-commentary page; thin on definition) | https://jimdaltontrading.com/livedata/poor-high-and-poor-low/ |
| S67 | Steidlmayer, J. P., Koy, K. | 1986 | *Markets and Market Logic* (Porcupine Press) (bibliographic; not opened) | n/a |

**Internal references** (the project's own measurements, not web sources):
- the memory notes `upstox-api-facts`, `vpin-shadow-module`, `flow-rank-first-minutes-bug`, `anytime-start-rule` and `orderflow-reader-redesign-2026-09-28`;
- the `sweep.py` classification note (quoted in `upstox-api-facts`).
