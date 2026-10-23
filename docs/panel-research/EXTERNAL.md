# Right-panel research: external tools (EXTERNAL.md)

Date: 2026-10-20. Scope: what the best order-flow and OI tools measure for **pace, speed, side, OI velocity, trend and cross-index**, and how they show it.

**Evidence tags** (on every claim):

| tag | meaning |
|---|---|
| **[D]** | Documented definition: vendor manual, help page, API doc. |
| **[V]** | Vendor claim: marketing or product page, no formula given. |
| **[P]** | Practitioner opinion: forum, blog, educational post. |
| **[A]** | Academic or peer-reviewed work. |
| **[I]** | My own inference, not from a source. |
| **[N]** | Searched for it and found nothing public. |

**Her data, for the "needs" notes** (from `memory/upstox-api-facts.md` plus the brief):
- **Upstox `full`:** LTP, cumulative volume (`vtt`), `oi`, 5 depth levels a side, `tbq`/`tsq`. It arrives as **~2–3 snapshots a second, not tick-by-tick**. There is **no aggressor flag, no trade count and no per-level order count**.
- **Upstox `full_d30`:** 30 levels, Plus plan, NSE only. The 30-level count has not yet been confirmed live.
- **OI baseline:** `oi_chg` has to be computed against a 09:15 REST baseline.
- **GoCharting footprint:** buy and sell volume per price per bar. GoCharting does not document how it classifies the sides **[N]**.

---

## 0. Bottom line

1. **Every pace tool answers the same question: "rate now ÷ rate normally".** The best documented form is Jigsaw's Pace of Tape: a 20-second needle on a scale built from the last 20 minutes **[D]**. The rest use a fixed threshold you type in (Quantower, GoCharting, Sierra Chart, MotiveWave manual mode) or a simple moving average (MotiveWave, ATAS).
2. **None of these tools make "normal" depend on time of day [N], even though the vendors say activity drops at lunch** (ATAS **[D]**). A flat 20-minute baseline will over-call fast at the open and under-call it at 12:30.
3. **No vendor publishes an "OI velocity" with a formula [N].**
   - What exists is OI change per chosen interval: Sensibull at 3 minutes, IIFL up to 60 minutes, HDFC at 15 minutes.
   - Fyers "OI Spurts" uses undisclosed "internal significance criteria" **[D]**. OI Pulse "Big OI Movement" is "AI-based" **[V]**.
   - **Nobody shows OI acceleration.** This is open ground.
4. **Acceleration is almost never a number.** Tools show it indirectly:
   - a short window against a long window (Jigsaw);
   - a peak-hold marker, where the needle sitting below the marker means slowing (Jigsaw);
   - delta change from one bar to the next (Sierra Chart, ATAS, NinjaTrader);
   - delta since the bar's high or low (NinjaTrader).
5. **The side split depends on per-trade aggressor data, which she does not have.** The repo has already shown that quote-rule CVD on snapshots is a coin flip on balanced intervals (`sweep.py:115-130`).
   - The one well-evidenced pressure measure she *can* compute is **order-flow imbalance (OFI) from best-bid and best-ask queue changes** (Cont, Kukanov and Stoikov) **[A]**. It uses depth snapshots, which she has.
6. **Trend fusion in the field has one shape: a 2×2 of price direction × OI direction, or a flow line plotted against the price line.**
   - The best-documented failures are cumulative delta read as direction, CVD divergence used as a reversal call, aggregate PCR, premium-based build-up labels near expiry, and VPIN.

---

## 1. Order-flow pace and speed

### 1.1 ATAS
- **Speed of Tape [D blog]**
  - Formula: `Speed = number / time`, with time always in seconds.
  - What it counts: trades, volume, delta, buys or sells.
  - Display: a histogram where a taller bar means a faster tape, plus a moving average. Bars over the threshold are painted whole, yellow by default.
  - **Autofilter** is on by default and is per instrument; the algorithm is not disclosed. With it off, you set the threshold yourself (example: "per 15 seconds").
  - Run two copies to split the sides: buy speed in green, sell speed in red.
  - ATAS's own caveat **[V]**: speed alone is "not very informative". Read it near significant levels together with volume. Each instrument has its own typical speed, and activity drops at lunch and before weekends.
  - ATAS support says to use it on tick or volume charts only **[D]**.
- **Order Flow Rhythm [V]:** a red/green bar whose brightness shows trade speed. It is Speed of Tape drawn differently.
- **Cluster Statistic [D blog]:** a grid of rows under each bar.
  - Rows: Asks, Bids, Delta, Delta/Volume %, Session Delta, Session Delta/Volume %, Max Delta, Min Delta, **Delta Change** (bar to bar), Volume, **Volume/Second**, Session Volume, Trades Count, Height, Time.
  - How the cells are coloured is not documented **[N]**.
- **Big Trades [D help]**
  - Modes: Cumulative Trades (prints aggregated by an undisclosed ATAS algorithm) or Separate Trades.
  - **Autofilter** works only in Cumulative mode, at Strong, Medium or Weak intensity. It is set once at first run and does not update live. It aims for **about 10 prints a day** and looks back at most one week.
  - Manual mode uses Min/Max volume.
  - Markers grow with volume relative to Min Volume. Buy, sell and in-between trades each get their own colour. Alerts are available.
- **Smart Tape [V]:** reassembles split exchange prints into one order and lets you filter by size. With a filter on, "the tape speed slows down", which makes it easier to read.
- **CVD Pro [V]:** can build a CVD from only large or only small trades.
- **DOM Levels / Smart DOM [V]:** a heatmap of resting volume. Smart DOM columns include Trades, Depth Changes, Liquidity Map and a mini footprint. Latest trades are highlighted (2024 update).

### 1.2 Bookmap
- **Volume dots [D]**
  - Size: an undisclosed algorithm "scales the volume of trades at a particular pixel-time against the instrument's average trade volume". So dot size is relative, not absolute.
  - Colour: buyer and seller colours drawn as a gradient, a solid split or a pie. A dot can show total volume or delta.
  - Clustering options: Smart, By time, By volume, By price, By price and aggressor.
  - Filter: a minimum trade size per pixel. A burst of small trades inside one pixel can still pass it.
- **CVD [D]**
  - Reset: "Reference Points" set when accumulation starts again; there is also a Reset Now button.
  - Size filters: minimum and maximum accountable trade size.
  - Range: the visible chart or the session. Values can change a lot when the visible range changes.
- **Stops & Icebergs Tracker (SIT) [D]:** two CVDs, one for stops and one for icebergs.
  - **Accumulation modes:** `SUM`, `EXPONENTIAL` (50% decay every T), `RESET` every T, `SLIDING` window of width T, and `SAME_SIDE_SUM` (adds up until the other side trades).
  - Alerts fire when at least V trades inside T. They are text or synthesized voice.
  - **Needs market-by-order data (MBO). She does not have it.**
- **Large Lot Tracker [D]:** an estimate of the largest single resting order at a price. Thresholds are set against the total at that level and against the largest visible level. It is an algorithmic estimate, not exchange data.
- **Volume Imbalance widget [D]:** `(DAV − SAV) / (DAV + SAV)`, where DAV and SAV are buy and sell aggressor volume.
  - Settings: a range in time or price intervals, a weighted smoothing factor, a sound alert at a threshold.
  - Display: a widget at the right edge, signed and coloured by side.
- **Orderbook Imbalance widget [D]:** `(BOS − SOS) / (BOS + SOS)` over N levels, a % distance from the best bid/ask, or all levels.
  - Option: "lower rate for farther levels", an exponential weighting so nearer levels count more. Sound alert available.
  - **She can compute this from 5 levels.**
- **Pace:** no native pace indicator found **[N]**. One NexusFi commenter said Bookmap's visuals made one unnecessary **[P]**.
- **Practitioner verdict [P]:** stops and icebergs are "not the game changer you may think it is". The heatmap's value is "picking out the persistent large limit orders" (zerosumnasdaq).

### 1.3 Sierra Chart
- **Numbers Bars Calculated Values [D]**
  - `Ask Volume per Second` and `Bid Volume per Second` = the bar's total ask (bid) volume ÷ the bar's duration in seconds.
  - `Volume/Sec` = the bar's volume ÷ its seconds.
  - Other values: `AskV − BidV`, `Positive/Negative Delta Total`, **`AskV − BidV BarDiff`** (this bar's delta minus the previous bar's), `AskV %`, `BidV %`, `(AskV − BidV) %`, and day-cumulative versions.
  - There is **no "trades per second" value [N]**.
- **Side classification [D]:** in order of preference:
  1. The exchange aggressor flag where the feed has it (CME, EUREX, NASDAQ TotalView).
  2. Otherwise, at or below the bid is a sell and at or above the ask is a buy.
  3. Between the two, tick direction combined with bid/ask direction, or whichever side is nearer.
  4. An unchanged price keeps the previous side.
  5. Final fallback: tick direction.
- **Numbers Bars colouring [D]:** fixed compare thresholds, either percent (0.25 / 0.50 / 0.75) or actual volume (100 / 200 / 300).
- **Cumulative Delta Bars [P forum]:** volume, trade-count and up/down-tick versions exist. They need 1-tick storage to be accurate.
- **Pulling/Stacking DOM column [P vendor]:** the data is kept only while the column is on the Chart DOM.

### 1.4 Jigsaw daytradr: the best-documented pace design
- **Pace of Tape (POT) Smart Gauge [D manual]**
  - **Needle:** activity over `POT Lookback` seconds. "20 seconds worked really well in our testing."
  - **Scale:** `POT Average Time` minutes, default **20**. This is what defines low, normal and excessive.
  - **Red max marker:** the highest needle value since the last reset, a peak-hold. Reset moves it back to the current needle.
  - **"Red zone"** means excessive activity. `POT Tuner` lowers sensitivity for markets that spend too long in it (DAX is the example).
  - **Market Balance shading:** blue for buy imbalance and red for sell imbalance, filling up to 50% of the gauge, over `Market Balance Lookback (Seconds)`. Half the gauge blue means all trading was buying.
  - The unit the gauge measures (trades or volume) is **not stated [N]**.
  - Use **[D]**: at a breakout level, "whether traders are aggressively entering" or "stepping back". Optimus also says to compare pace across correlated markets (S&P, Nasdaq, Dow) **[V]**.
- **Summary Tape [D]**
  - A new row prints **only when a trade happens at a new bid or ask**. Quote-only moves add no row.
  - Each row carries a delta, either cumulative or per row.
  - Colour: green or red price when the price ticks up or down out of the area; green or red delta when delta rose or fell.
  - Delta is "since I opened the window" unless Reset Delta is set to session.
- **Reconstructed Tape [D]:** rebuilds CME-split prints into one order.
  - Settings: `Display Duration` (prints disappear after N seconds), `Block Trade` size gets its own colour, `Size Filter`, `Print Mode` All / Buy Only / Sell Only, and the `Fuzzy` or `CME Split` algorithm.
  - `Update Interval Prints`: the most prints shown per **250 ms**. "25 appears to be the sweet spot." This is explicit throttling of display speed.
- **Depth & Sales "Current Trades" [D]**
  - Contracts traded at the inside bid/ask "this time around".
  - **It resets when price leaves the level and comes back**, but a return within **2500 ms is ignored**, so a flickering price does not wipe the count.
  - Buy and sell histogram backgrounds are sky blue and plum.
- **Auction Vista [V]:** "Large Trade Circles" from a proprietary algorithm.

### 1.5 MotiveWave
- **Speed of Tape [D]**
  - `Speed Interval (sec)`: the window, e.g. ticks in the last 15 seconds.
  - Statistic: Ticks, Volume, Ask Volume, Bid Volume, or Delta Volume (ask − bid).
  - **Auto Filter Period** is an SMA. A signal fires when the value crosses above the SMA. A manual `Filter Count` is the alternative.
  - Display: bars above the filter are highlighted, with optional up/down markers on crossings.

### 1.6 Quantower
- **Power Trades [D]**
  - The core rule: `Total Volume` must trade inside `Time Interval, sec`. The worked example is 2,000 ES contracts in 3 seconds.
  - Other settings: `Min/Max Trade Volume` per trade, `Zone Height` in ticks, `Level2 level count` (feeds an Imbalance column and a "Level 2 Ratio" column), `Filter by Delta %` (watch zones "above/below 50%"), and `Filter by Basis Ratio %`.
  - Colour by delta sign; alert sound.
  - **Every threshold is fixed** **[D]**. History is scanned, so it is slow on deep history.
- **Time Histogram / Time Statistics [D]:** per-bar values: trades, buy and sell trades, volume, buy and sell %, delta, delta %, cumulative delta, **average size (buy and sell)**, largest single trade, and filtered volume above a size.

### 1.7 NinjaTrader Order Flow+
- **Volumetric Bars [D]:** per-bar statistics:
  - Trades, Volume, Buy and Sell volume, Delta, Delta %, **Delta change** (against the previous bar), Max delta and Min delta inside the bar.
  - **Delta SH** = delta since price last touched the bar's high (usually negative). **Delta SL** = delta since the low (usually positive).
  - Cumulative delta.
  - Delta type: `BidAsk` (needs bid/ask tick history) or `UpDownTick`.
  - Imbalance defaults: ratio **1.5**, minimum delta **10**.
  - Shading is by delta, at `Strength sensitivity` 20, and **resets every session**. Colour is comparable within a day but not across days.
- **Order Flow Cumulative Delta [P staff forum]:** Bid/Ask mode (a mid print repeats the last side) or Up/Down Tick mode. Session mode or bar mode.
- **Trade Detector [D]:** three modes:
  1. volume held at a fixed bid or ask across bars;
  2. large volume at a price inside a bar;
  3. large single ticks.
  - It has a minimum volume threshold only, and needs bid/ask-stamped history.

### 1.8 Exocharts, TradingLite, GoCharting, Deepcharts
- **Exocharts [V]:** aggregated market orders ("aggregate limit orders into market orders"), trade filters, delta cluster and delta profile. No speed measure is documented **[N]**.
- **TradingLite:** no public documentation retrieved **[N]**.
- **GoCharting [D docs]**
  - Bar statistics: Trades, Buy and Sell trades, Volume, Buy and Sell volume %, Delta, Delta % (`Delta / Volume × 100`), Cumulative Delta, VWAP / BVWAP / SVWAP, POC. **There is no volume-per-second or bar-duration row.**
  - Power Trades Scanner: a fixed `Total Volume` within `Time Interval (sec)`, live only, shown as bubbles.
  - Delta alert at a custom threshold **[V]**.
  - The page says delta = BUY − SELL market orders, but **the classification method is not documented [N]**.
- **Deepcharts [V]:** speed of tape with min/max filters and a window in seconds.

### 1.9 Synthesis: how "fast" is decided

| Method | Who | Weakness |
|---|---|---|
| Fixed user threshold | Quantower, GoCharting, Sierra Chart colour thresholds, MotiveWave Filter Count, ATAS manual mode | Breaks across days and regimes. "Adjust the settings until the output looks right" **[P NexusFi]**. |
| Rolling average (SMA or minutes) | MotiveWave SMA cross, ATAS MA on the histogram, Jigsaw 20-minute scale | Ignores time of day: the lunch lull and the open. |
| Event-rate target | ATAS Big Trades autofilter (about 10 a day, ≤1 week lookback, set once) | Calibrated once, not live. |
| Position in a historical range | SpotGamma HIRO gauge against 5-day and 30-day ranges **[V]**; NYSE TICK ±1000 ≈ 95% of readings **[P, 2011 data]** | Needs history. |
| Multiple of a baseline | Market Chameleon: "unusual" if more than **2× the 90-day average** **[D glossary]** | Daily, not intraday. |
| Compared with neighbours | StockMojo: compare a strike "against its neighbours rather than against a fixed threshold" **[V]** | Cross-sectional only. |

- **Not found anywhere [N]:** a z-score, or a time-of-day percentile, for tape speed.
- The intraday U-shape is documented: U-shaped 1-minute volatility in Nifty futures (MPRA, unrefereed) **[A-ish]**, and U- or J-shaped volume in general **[A]**.

### 1.10 Synthesis: acceleration and sides
- **Acceleration, as shown in practice:**
  - short window against long window (Jigsaw needle against its scale);
  - **peak-hold** (Jigsaw red marker; needle below it = slowing);
  - first difference per bar (Sierra Chart `BarDiff`, ATAS `Delta Change`, NinjaTrader `Delta change`);
  - **delta since the extreme** (NinjaTrader `Delta SH/SL`);
  - decaying accumulators (Bookmap `EXPONENTIAL` or `SLIDING`);
  - SMA crossings (MotiveWave markers).
  - A second derivative shown as a number: **not found [N]**.
- **Sides:** four documented methods:
  - the exchange aggressor flag (Sierra Chart on CME);
  - comparing the print with bid/ask (NinjaTrader BidAsk, Sierra Chart);
  - the tick rule (NinjaTrader UpDownTick);
  - order-ID MBO logic (Bookmap SIT).
  - Upstox gives none of these at trade level. GoCharting's per-bar buy/sell split is the only aggressor-like source she has.
- **What works [P/V]:**
  - speed read at a level together with volume (ATAS);
  - pace at a breakout (Jigsaw);
  - filtering the tape so it slows (ATAS);
  - counters that reset when context changes (Jigsaw);
  - side shading inside the pace gauge (Jigsaw).
- **What turns into noise [P]:**
  - raw speed without context (ATAS's own caveat);
  - highlights that stay on screen. A Medved Trader user calls them "visually distracting" and asks for a timed fade.
  - pace settings that cannot be backtested (NexusFi);
  - stops and icebergs (zerosumnasdaq).

---

## 2. OI rate and speed in options

### 2.1 Indian tools
- **Sensibull [D blog]**
  - **Intraday OI chart** at **3-minute timestamps**: pick a start and end time to see the OI change in that window, with replay (2022).
  - 2024 page:
    - OI-change bars per strike, with the start and end OI in the tooltip, **Call OI red and Put OI green**;
    - 2 weekly + 2 monthly expiries at once;
    - "Future OI vs Time" labelled with the 4 build-up states.
  - End-of-day bhavcopy OI appears as a separate **"7:30 pm" tick**. It captures institutional OI that is not in the live close.
  - **No speed or rate metric and no fastest-strike ranking [N]**.
- **Opstra (Definedge) [V]:** Futures Buildup screener ("1 day open interest change and price change"), "Put Call OI Dynamics", OI charts, heatmap.
  - Data delay: about 1 minute on the paid plan and 15 minutes free, per an old forum post **[P]**.
- **Quantsapp [V]**
  - **Intraday Movers:** a bubble chart in quadrants of % price change × % OI change.
  - OI change tracked "from specific date and time".
  - The option chain updates every minute.
  - The build-up framework appears in their education pages.
- **iCharts [D help]:** call and put OI indicators that can be merged onto straddle charts. Intraday options data starts 2 Aug 2018. Nothing on speed **[N]**.
- **NiftyTrader [V]:** live OI-change pages measured against the previous day, plus a reading guide (rising call OI = resistance).
- **OI Pulse [V, via Scribd]:** "Big OI Movement" flags strikes with big real-time OI change, "AI based", split into calls and puts, live or historical. The criteria are undisclosed.
- **StockMock, TradingTick:** no public OI-speed documentation found **[N]**.
- **Dhan Options Trader [D FAQ]:** an OI Analysis dashboard showing OI, OI change, PCR, Volume PCR, option and futures build-up, and multi-strike OI.
  - Change in OI is measured against the **previous day's close by default**, or a "Custom Reference".
- **Fyers [D help]** (not on her list, but documented):
  - **OI Spurts:** a "sudden and significant increase" over a selected interval. "Only strikes that meet internal significance criteria appear."
    - Columns: strike, price change, total OI, OI change in the interval, volume.
    - Views: Gainers by OI and Gainers by premium.
  - **Trending OI:** up to 20 strikes as lines.
  - **OI Interpretation:** a 4-state label per interval. "Some intervals may not show classifications if price and OI changes do not meet the defined conditions." **This is a dead-band.**
- **IIFL InstaOptions [D]:** Trending OI = cumulative OI change for chosen strikes over any interval up to 60 minutes. Sentiment = put OI change − call OI change.
- **HDFC Securities [V]:** a 15-minute OI build-up analyser that splits contracts into **fresh and square-off**.
- **StockMojo [V]**
  - **Total Vol/OI** = cumulative volume ÷ OI. **Interval Vol/OI** = per-minute volume ÷ OI. "Spikes flag the exact moments turnover surges at a level."
  - Rule of thumb:
    - high Vol/OI with rising OI = active build-up;
    - high Vol/OI with flat OI = churn (ATM on expiry day);
    - above 3 with falling OI = rapid unwinding.
  - The vendor calls these "tendencies, not fixed rules".
- **GoCharting [D docs]**
  - **OI Sense:** compares the day's price % change with the day's OI % change. Four colour bands: Long Build Up green, Short Build Up red, Short Covering orange, Long Unwinding cyan.
    - Thresholds are at **zero only**. It also says to "focus on significant OI changes", with no cutoff given.
  - **OI Heatmap:** day-over-day OI change %, with user-set "critical levels".

### 2.2 Global tools
- **CME QuikStrike Open Interest Heatmap [D]**
  - Matrix of strike × expiry showing OI, **% OI change**, volume or volume change, for puts, calls or total.
  - Comparison against 1 day, 1 week or 1 month.
  - **Diverging colour:** white→green for positive-only values, red→white→green for signed changes.
  - **Most Active Strikes:** the top 20 by volume, OI, or **OI change**.
  - **Vol2Vol:** intraday volume by strike, placed in standard deviations from ATM.
- **Market Chameleon [D]:** relative volume = today ÷ average daily volume. "Unusual" = more than **2× the 90-day average**.
- **SpotGamma HIRO [V]:** sums the estimated delta-hedging notional of every option trade.
  - Lines: Calls, Puts, Next Expiry, plotted against price.
  - **"Strength of Signal" gauge** places the live value within its **5-day and 30-day ranges**.
  - The formula is proprietary.
- **Unusual Whales [D API / blog]:** **Market Tide / net premium** = ask-side premium − bid-side premium. Mid prints are excluded.
  - Buckets: 1 minute and 1 second, as deltas you sum yourself.
  - Their own caveat: ask-side ≠ buy. A JBLU example shows one 5,000-lot bid-side call that was a **close** flipping net premium from +$18.7k to −$443k.

### 2.3 Synthesis
- **How speed is judged:**
  - undisclosed criteria (Fyers Spurts, OI Pulse);
  - neighbour comparison (StockMojo);
  - range position (HIRO);
  - multiples of a baseline (Market Chameleon, volume only).
  - **Nobody normalises ΔOI per interval by that strike's own normal, and nobody shows OI acceleration [N].**
- **How the fastest-building strikes are shown:**
  - rank tables (CME top 20 by OI change, Fyers gainers by OI);
  - strike × expiry heatmap with a diverging palette (QuikStrike);
  - per-strike bars with start and end values (Sensibull);
  - one line per strike over time (Fyers Trending OI, ≤20 strikes);
  - quadrant bubbles (Quantsapp).
- **Telling writers from buyers:**
  - The industry standard is the price × OI quadrant on the option's own premium **[D, many]**.
  - Adding IV is a practitioner heuristic only: OI up with IV down = "writers getting more comfortable … wall being built" (Tradejini) **[P]**. **No product found that does it [N].**
  - HDFC's fresh vs square-off split is the only vendor-claimed attempt to separate opening from closing flow **[V]**.
- **Data timing, which limits any OI velocity:**
  - Exchange OI is said to arrive "about every 3 minutes". This is a Quant Tower presenter's claim, recorded in `docs/research/quant-tower-india-2026-09-24.md` **[P]**.
  - NSE circulars say broadcast items refresh at a fixed interval or are event-driven **[D]**.
  - Upstox: `oi` arrives only in `full` or `option_greeks` mode, and change is not sent; you compute it **[D forum staff]**.
  - Intraday OI ≠ final OI (Sensibull's bhavcopy tick; Zerodha forum) **[P]**.
  - **[I] Measure the cadence from her own minute file (count the minutes where OI did not change) before choosing the velocity window.**

---

## 3. Trend from flow plus OI

### 3.1 How dashboards fuse them
1. **Quadrant state** of price direction × OI direction. Used by GoCharting OI Sense, Fyers, Dhan, Sensibull futures and Quantsapp bubbles **[D]**.
   - The only one with a documented dead-band is Fyers ("may not show classifications" when the changes fall below its conditions).
2. **A flow line against the price line, read as agree or diverge:**
   - SpotGamma HIRO: rising with price = confirmation, price up with HIRO down = "reversal warning" **[V]**;
   - Unusual Whales net premium against price **[D]**;
   - CVD against price.
3. **Pace and side in one widget:** Jigsaw POT plus Market Balance **[D]**.
4. **Effort vs result** (Wyckoff's third law): heavy volume or delta with little price progress = absorption, and it matters most at a key level **[P, StockCharts / Pruden]**.
5. **Breadth:** NYSE TICK and ADD. A persistently one-sided TICK suggests a trend day, and fading its extremes on such a day is risky **[P]**.
6. **[A] OFI:** price changes over short intervals are "mainly driven" by order-flow imbalance at the best quotes. The relation is linear, with a slope inversely proportional to depth, and it is less noisy than volume-based relations (Cont, Kukanov, Stoikov 2014).

### 3.2 What is known to mislead
- **Cumulative delta read as direction.** "Delta simply describes how traders have chosen to execute their orders" (tendex) **[P]**.
  - Worked example: a passive buyer on the bid gives delta −600 while price climbs from 100 to 105.
  - The value depends on the reset point: Bookmap "Reference Points"; Jigsaw's delta is "since I opened the window" **[D]**.
- **CVD divergence used as a reversal call.**
  - No published statistics were found **[N]**.
  - Vendors themselves call it "a warning, not a trigger", and NexusFi calls hidden divergence "a continuation setup" **[P]**.
  - Mixed bar sizes can create it artificially (futures.io) **[P]**.
- **Aggregate PCR.**
  - Its meaning changes with OI vs volume, extremes persist, and the bands are arbitrary.
  - No peer-reviewed Nifty study was found **[P / N]**.
- **Premium-based build-up labels on options.**
  - Writers drive much of options OI. Premium falls on theta alone, so "short build-up" becomes the default label on a quiet day **[P / I]**.
  - Near expiry, "traditional labels often fail" **[P]**.
  - "'Long buildup' is not a buy signal" (Rupeezy) **[P]**.
  - Rollovers and hedges distort the reading **[P]**.
- **Net premium / ask-side as intent.** Closes are counted as opens (the JBLU example) **[D blog]**.
- **VPIN.**
  - "Its predictive content is due primarily to a mechanical relation with the underlying trading intensity."
  - It peaked *after* the flash crash, depends on when you start counting, and flips sign under standard trade classification (Andersen & Bondarenko) **[A]**.
- **Baselines that ignore time of day** (lunch lull, U-shape) **[D ATAS / A]**.

---

## 4. Cross-instrument / other-index watch

- **Pace compared across correlated markets** (S&P, Nasdaq, Dow): Jigsaw's suggested use **[V]**.
- **SMT divergence** (ES / NQ / YM):
  - In a zone of highs, one index takes out its previous high and its partner does not. The mirror case applies at lows.
  - The two swings must be close in time ("Monday NQ vs Tuesday ES is not an SMT").
  - The author says there is "no public statistic" on it and treats it as a confirmation layer **[P]**.
- **Breadth:** about 95% of TICK readings fall within ±1040 (2011 data). Thresholds are often set from the recent distribution **[P]**.
- **Index contribution:** the points each stock adds to Nifty or Bank Nifty, with top lifters and draggers.
  - It shows "green on 2–3 heavyweights" while the broad market falls (Stockezee) **[V]**.
  - Top 10 ≈ 53% of Nifty weight; HDFC Bank ~9.9%, ICICI ~9.4%, RIL ~8.0% (StockMojo, Sep 2026) **[V]**.
- **Nifty vs Bank Nifty divergence** read as sector rotation, with VIX as context **[P]**.
- **Relative strength construction [P]:**
  - % change from a session anchor for both instruments, then their difference;
  - or a plain or normalised ratio;
  - optionally **ATR-normalised**, so the more volatile index does not always look "stronger";
  - a flip of the RS line against its MA = leadership changing.
- **Compact displays found:**
  - watchlist heat strips (QuikStrike-style diverging cells);
  - a gauge per market (Jigsaw);
  - RS lines.
  - No vendor shows a one-row "other index state" combining flow, OI and pace **[N]**.
- **Her data:** NIFTY, BANKNIFTY and SENSEX futures already share one Upstox socket.
  - SENSEX is BSE: no `full_d30` and no TBT.
  - Heavyweight stocks would add keys, well within `full` mode's 2,000-key cap.

---

## 5. Panel design lessons

- **Change aversion is real [V/P].** Bloomberg's UX team "conceals complexity", and a 2008 font swap drew a strong user reaction that was later toned down. Lesson: fixed cell positions, and never reflow.
- **Colour-vision safety [D].** Bloomberg estimates about 20,000 Terminal users have colour-vision deficiency. It ships alternate palettes for deuteranopia and protanomaly (`PDFU COLORS`). Red against green alone is unsafe.
- **A diverging palette with a white zero [D].** QuikStrike uses red→white→green for signed changes.
  - **[I]** On a light theme, small changes fade into white, so colour itself suppresses noise. This is also a precedent for a light, white-based heatmap.
- **Throttle the display, not the data [D].** Jigsaw's `Update Interval Prints`: at most N prints per 250 ms, with 25 called the "sweet spot".
- **Flash, then fade [D].** AG Grid separates `cellFlashDuration` and `cellFadeDuration` (default class duration 500 ms; documented examples 300 ms hold + 700 ms fade).
  - **[P]** Highlights that stay until the next opposite change are "visually distracting" (Medved forum).
- **Grace windows stop flicker [D].** Jigsaw's 2500 ms "brief departure" rule keeps a counter from resetting when price flickers.
- **Peak-hold [D].** Jigsaw's red max marker shows "was faster, now slowing" without a second number.
- **Rarity by construction [D].** The ATAS autofilter targets about 10 events a day. "Unusual" stays rare, so it still means something.
- **Relative sizing [D].** Bookmap dots are scaled against the instrument's average trade volume. NinjaTrader shading resets each session, so it is comparable within a day only.
- **Placement [D].** Bookmap imbalance widgets sit at the right edge beside the chart, signed and coloured by side, with a sound alert at a threshold.
- **Word-sized graphics [D].** Tufte: sparklines are "data-intense, design-simple, word-sized graphics" that fit inside a table cell.
- **Muted by default [P, paraphrase].** Few (2008, *Practical Rules for Using Color in Charts*) uses soft colours for most data and bright or dark colours only for what needs attention. The PDF could not be text-extracted this session, so treat this as a paraphrase.
- **[I] Applied to her rules (light theme, grid, ≤6-word cells, judged against normal):**
  - every row = `value · ×normal · ↑↓ (accelerating or decelerating) · since HH:MM`;
  - grey ink while inside the normal band, colour only beyond it;
  - tabular numerals, fixed columns, numbers refreshed at most every 250–500 ms;
  - flash for about 300 ms + fade 700 ms **only when a band is crossed**, not on every tick.

---

## 6. Every measure found

| Tool | Measure | Exact definition | Normal-vs-fast method | Display | Tag |
|---|---|---|---|---|---|
| ATAS | Speed of Tape | count ÷ seconds; count = trades, volume, delta, buys or sells | Autofilter per instrument (undisclosed) or manual | Histogram + MA; bars over threshold yellow | D |
| ATAS | Order Flow Rhythm | Speed of Tape shown as intensity | Brightness | Red/green bar | V |
| ATAS | Cluster Statistic Volume/Second | bar volume ÷ seconds | None stated | Grid row under bars | D |
| ATAS | Delta Change | this bar's delta − previous bar's | None | Grid row | D |
| ATAS | Max/Min Delta | intrabar extreme delta | None | Grid row | D |
| ATAS | Big Trades | aggregated or separate prints ≥ filter | Autofilter about 10/day, ≤1 week, set at start | Sized markers, side colours, alert | D |
| ATAS | CVD Pro | CVD from large-only or small-only trades | Size filter | Line | V |
| Bookmap | Volume dots | volume per pixel-time | Scaled vs instrument's average trade size | Bubbles, buyer/seller gradient | D |
| Bookmap | CVD | Σ(buy aggr − sell aggr) from reference point | Size filters | Line | D |
| Bookmap | SIT CVDs | stop-aggressor and iceberg-passive volume | ≥V within T; SUM, EXP, RESET, SLIDING, SAME_SIDE | Two lines, voice alert | D |
| Bookmap | Large Lot Tracker | largest single resting order (estimate) | Share of level total and of largest level | White line on book bars | D |
| Bookmap | Volume Imbalance | (DAV − SAV)/(DAV + SAV) | Smoothing + alert threshold | Right-edge widget | D |
| Bookmap | Orderbook Imbalance | (BOS − SOS)/(BOS + SOS) over N levels | Alert at % | Right-edge widget | D |
| Sierra Chart | Ask/Bid Volume per Second | side volume ÷ bar seconds | None | Calculated value | D |
| Sierra Chart | Volume/Sec | bar volume ÷ bar seconds | None | Calculated value | D |
| Sierra Chart | AskV − BidV BarDiff | bar delta − previous bar delta | None | Calculated value | D |
| Sierra Chart | Numbers Bars colouring | per-price volume or delta | Fixed 0.25 / 0.50 / 0.75 or 100 / 200 / 300 | Cell colour | D |
| Sierra Chart | Cumulative Delta Bars | session cumulative (volume, trades or up/down tick) | None | OHLC bars | P |
| Jigsaw | Pace of Tape | activity over 20 s against a 20-min scale | Scale from recent activity; red zone; Tuner | Gauge, needle, red peak-hold | D |
| Jigsaw | Market Balance | buy vs sell share over N s | Up to 50% fill | Blue/red shading in the gauge | D |
| Jigsaw | Summary Tape | row per new bid/ask traded; delta per row | None | Green/red rows | D |
| Jigsaw | Reconstructed Tape | split prints rebuilt into orders | Block Trade size; size filter | Tape; prints expire after N s | D |
| Jigsaw | Current Trades | traded at inside bid/ask "this time around" | Resets on return; 2.5 s grace | Blue/plum histogram | D |
| MotiveWave | Speed of Tape | statistic over Speed Interval seconds | SMA (Auto Filter Period) cross, or count | Highlighted bars, markers | D |
| Quantower | Power Trades | Total Volume within Time Interval s | Fixed values | Zones, table, sound | D |
| Quantower | Average size (buy/sell) | mean trade size per bar | None | Histogram / statistics | D |
| NinjaTrader | Delta %, Delta change | bar delta ÷ volume; Δ vs previous bar | None | Bar statistics | D |
| NinjaTrader | Delta SH / SL | delta since bar high / since low | None | Bar statistics | D |
| NinjaTrader | Imbalance | diagonal ratio ≥1.5 and Δ ≥10 | Fixed | Cell highlight | D |
| NinjaTrader | Trade Detector | 3 modes of large volume | Min volume | Markers | D |
| GoCharting | Bar statistics | trades, volume, delta, delta % | None | Rows under bars | D |
| GoCharting | Power Trades | Total Volume within Time Interval s | Fixed | Bubbles, live only | D |
| GoCharting | OI Sense | day price % vs day OI % → 4 states | Zero only | Colour bands | D |
| GoCharting | OI Heatmap | day-over-day OI change % | User "critical levels" | Grid | D |
| Sensibull | Intraday OI change | ΔOI between two 3-min stamps | None | Per-strike bars, replay | D |
| Sensibull | Future OI vs Time | 4 build-up states | None stated | Line + tooltip | D |
| Fyers | OI Spurts | sudden significant ΔOI in an interval | "Internal significance criteria" | Ranked table | D |
| Fyers | OI Interpretation | 4 states per interval | Dead-band ("may not show") | Table | D |
| IIFL | Trending OI | cumulative ΔOI over ≤60 min; PE − CE | None | Lines | D |
| HDFC Securities | OI build-up | 15-min snapshot, fresh vs square-off | None stated | Table | V |
| StockMojo | Interval Vol/OI | per-minute volume ÷ OI | Compare to neighbours; 1–3 typical ATM | Line, spikes | V |
| Quantsapp | Intraday Movers | % price vs % OI | Quadrant | Bubble chart | V |
| OI Pulse | Big OI Movement | big real-time ΔOI by strike | "AI based" | List, calls/puts | V |
| Dhan | Change in OI | OI − previous close (or custom reference) | None | Chain / charts | D |
| CME QuikStrike | OI Heatmap | OI, %ΔOI, volume, Δvolume by strike × expiry | Heat; vs 1 day, 1 week, 1 month | Red-white-green matrix | D |
| CME | Most Active Strikes | top 20 by volume, OI or ΔOI | Rank | Table | D |
| Market Chameleon | Relative volume | today ÷ average daily volume | Unusual > 2× 90-day | Table | D |
| SpotGamma | HIRO | Σ estimated hedge delta-notional | Gauge vs 5-day and 30-day range | Lines vs price | V |
| Unusual Whales | Net premium / Market Tide | ask-side − bid-side premium, mid excluded | None | Call and put lines vs price | D |
| NYSE | TICK | upticks − downticks | ±1000 (≈95%, 2011) | Line | P |
| Academic | OFI (Cont, Kukanov, Stoikov) | Σ signed changes of best bid and ask queues | Regression slope ∝ 1/depth | n/a | A |

---

## 7. Ten things worth stealing (ranked by value to her)

1. **Two-window pace gauge with a peak-hold (Jigsaw POT).**
   - What: a short-window rate shown as **×normal** against a longer baseline, plus a marker for the session's or level's peak. A needle below the peak means slowing; a short window above the medium window means accelerating.
   - Why: it answers "speed of change vs normal" directly. Making the baseline **time-of-day aware** fixes the one hole every vendor leaves.
   - Data: futures volume per second from `vtt` increments on Upstox snapshots (**she has it**). A trades-per-second version would need trade counts, which she lacks.
2. **OI velocity per strike against that strike's own normal, ranked (Fyers Spurts + CME Most Active + StockMojo neighbours).**
   - What: ΔOI per publish interval ÷ that strike's typical |ΔOI| at this time of day. Acceleration = this interval against the previous one. Show the top 2 per side.
   - Why: nobody publishes this. It is exactly her "rate of change of OI and the speed it is building", and it ignores the small ± changes she calls noise.
   - Data: Upstox `oi` plus the 09:15 REST baseline (**she has it**). Check the OI cadence first, from her own minute file.
3. **A bounded side share, not raw delta (Bookmap Volume Imbalance, Jigsaw Market Balance).**
   - What: `(B − S)/(B + S)` over a rolling window, between −1 and +1, judged against normal.
   - Why: it separates "fast and one-sided" from "fast and two-way". A bounded ratio has no reset-point dependence, unlike CVD.
   - Data: needs an aggressor split. GoCharting gives buy/sell per bar (**bar resolution only**). Quote-rule splits on Upstox snapshots are a coin flip (`sweep.py`), so do not build it that way.
4. **Order-flow imbalance from the best bid and ask (Cont, Kukanov, Stoikov) [A].**
   - What: a signed sum of changes in the best bid and ask queues. It tracks price change linearly, with a slope inversely proportional to depth.
   - Why: it is buyer vs seller **pressure per unit time without trade-level aggressor data**. It is the best-evidenced flow measure in this report.
   - Data: Upstox 5-level snapshots (**she has it**). Caveat: at 2–3 snapshots a second, events inside a snapshot are lost.
5. **The price × OI state with a dead-band (Fyers "no classification").**
   - What: label build-up or covering **only when |ΔOI| and |Δprice| are beyond normal**; otherwise "flat". On options, phrase it as the writer's side and flag theta near expiry.
   - Why: it removes the default "short build-up" label that falls out of a quiet, decaying day.
   - Data: **she has it**.
6. **A one-row cross-index strip (Jigsaw across markets, SMT, RS normalised by ATR).**
   - What: for each of NIFTY, BANKNIFTY and SENSEX: % from open ÷ ATR, pace ×normal, OI state, and an **"extreme not confirmed"** flag when one index makes the new high or low and its partner does not, close in time.
   - Why: it is her explicit "eye at other index". The leader/laggard reading becomes a pill, not a chart.
   - Data: **she has it** (one socket). SENSEX depth stays at 5 levels.
7. **Volume ÷ OI per interval per strike (StockMojo).**
   - What: high Vol/OI with rising OI = fresh positioning; with flat OI = churn.
   - Why: it tells writing pressure apart from day-trader churn at the same strike, an inference no vendor makes explicit.
   - Data: Upstox `vtt` + `oi` per option leg (**she has it**).
8. **Event-rate calibration of "unusual" (ATAS autofilter: about 10 a day, ≤1 week lookback).**
   - What: pick each threshold so it fires a fixed number of times a day on her own history.
   - Why: "unusual" stays rare by construction, matching her "two bells a day" design, and the threshold tracks the regime. Recompute at the start of each session, as ATAS does.
   - Data: her recorded sessions (**she has it**).
9. **Delta since the bar's high or low, and bar-to-bar delta change (NinjaTrader Delta SH/SL, Sierra Chart BarDiff).**
   - What: how much aggression has come in since the extreme.
   - Why: it shows exhaustion or absorption at an extreme without CVD's lag or reset problem.
   - Data: needs intrabar aggressor sequence. Partly possible with GoCharting per-bar buy/sell; true SH/SL needs ticks with side, which **she does not have**.
10. **Context-reset counters with a grace window, plus display throttling (Jigsaw Current Trades and Update Interval).**
    - What: "since price came to this level" numbers that do not reset on a 2.5 s flicker, with display refresh capped (25 prints / 250 ms).
    - Why: it reads flow at **levels** (her OI liquidity-hunt thesis), and it is the documented anti-flicker technique.
    - Data: **she has it**.

---

## 8. Five things that are noise

1. **Raw cumulative delta read as trend or direction.**
   - Delta records how orders were executed, not intent: a passive buyer gives delta −600 into a +5 rally (tendex) **[P]**.
   - Its value depends on an arbitrary reset (Bookmap reference points; Jigsaw "since I opened the window") **[D]**.
   - On her Upstox snapshots, quote-rule CVD scores `p²+(1−p)²`, which is 50% on balanced intervals (`sweep.py:115-130`, repo analysis) **[I]**.
2. **CVD divergence used as a reversal trigger.**
   - There are no published statistics anywhere **[N]**.
   - Vendors call it "a warning, not a trigger", and NexusFi reads hidden divergence as **continuation**: the same pattern called both ways **[P]**.
   - Mixed bar sizes can manufacture it (futures.io) **[P]**.
3. **Aggregate PCR.**
   - It is a contrarian read whose extremes persist, and the Nifty "bands" are self-described guides, not thresholds.
   - OI-based and volume-based PCR differ. No peer-reviewed Nifty evidence was found **[P / N]**.
4. **Build-up labels on option premiums without a dead-band.**
   - Writers drive options OI, and theta lowers premium on its own, so "short build-up" is the default on quiet days **[P / I]**.
   - Labels "often fail" near expiry, and "long buildup is not a buy signal" (Rupeezy) **[P]**.
   - Even Fyers suppresses labels below its conditions **[D]**.
   - GoCharting's thresholds are at zero, so it labels every ±1 contract **[D]**.
5. **VPIN as a toxicity or crash gauge.**
   - "A poor predictor of short run volatility". It peaked **after** the flash crash, not before.
   - Its predictive content is "a mechanical relation with the underlying trading intensity". It depends on when counting starts and reverses under standard trade classification (Andersen & Bondarenko) **[A]**.
   - Her VPIN shadow module should be judged against plain volume pace before it earns a cell **[I]**.

**Also noise, weaker evidence:**
- **Fixed-size "power trade" or "big trade" thresholds and raw speed numbers with no baseline.** ATAS itself says speed alone is "not very informative", and fixed thresholds have to be tuned "until it looks right" (NexusFi).
- **Stops and icebergs.** They need MBO data, and a practitioner says they are "not the game changer".
- **Ask-side net premium read as buying.** Closes are counted (JBLU).

---

## 9. Data she does not have

| Need | Used by | Her status |
|---|---|---|
| Per-trade aggressor flag | Sierra Chart, NinjaTrader BidAsk, Bookmap dots and CVD, Jigsaw tapes | **No.** Upstox gives snapshots; GoCharting gives a per-bar split (method undocumented). |
| Trade count / trade sizes | ATAS trades/sec, Quantower average size, Big Trades, Reconstructed Tape | **No** (only `vtt` increments per snapshot) |
| Market-by-order (MBO) | Bookmap SIT, Large Lot Tracker accuracy | **No.** NSE MTBT is colocation-only. |
| Depth beyond 5 levels | Orderbook Imbalance over N>5 levels, depth history | `full_d30` exists (Plus, NSE-only); the 30 levels are not yet confirmed live. |
| Per-level order counts | Wall vs cluster | **No** on Upstox; Dhan `Full` has them (data plan lapsed). |
| Option trade side (bid or ask) | Unusual Whales net premium, HIRO | **No.** Approximating from LTP vs quote in snapshots has the same coin-flip problem. |
| OI at sub-3-minute resolution | Any OI "speed" finer than the publish cadence | Bounded by the exchange cadence (~3 min claimed); measure it. |

---

## 10. Sources

**Order flow**
- ATAS Speed of Tape: https://atas.net/blog/alternative-analysis-of-the-smart-tape-with-the-speed-of-tape-indicator-in-atas/
- ATAS support, Speed of Tape usage: https://support.atas.net/en/knowledge-bases/2/articles/424-please-explain-how-to-use-speed-of-tape-indicator
- ATAS Big Trades help: https://help.atas.net/en/support/solutions/articles/72000602332-big-trades
- ATAS Cluster Statistic: https://atas.net/fr/blog/cluster-statistic-basics/
- ATAS Smart Tape: https://atas.net/modules/smart-tape/
- ATAS Smart DOM: https://atas.net/modules/smart-dom/
- ATAS indicators overview: https://atas.net/blog/atas-indicators/
- ATAS CVD Pro (German): https://atas.net/de/features/indicators/
- Bookmap traded-volume visualisation: https://www.bookmap.com/knowledgebase/docs/KB-SettingUpAndOperating-HeatmapTradedVolumeVisualization
- Bookmap CVD: https://bookmap.com/knowledgebase/docs/KB-Indicators-CVD
- Bookmap Stops & Icebergs Tracker: https://bookmap.com/knowledgebase/docs/Addons-SIT
- Bookmap SIT forum: https://bookmap.com/forum/viewtopic.php?p=4450
- Bookmap Large Lot Tracker: https://bookmap.com/knowledgebase/docs/KB-Indicators-LLT
- Bookmap Volume Imbalance: https://bookmap.com/knowledgebase/docs/Addons-Volume-Imbalance
- Bookmap Orderbook Imbalance: https://bookmap.com/knowledgebase/docs/Addons-Orderbook-Imbalance
- Sierra Chart Numbers Bars: https://www.sierrachart.com/index.php?page=doc/NumbersBars.php
- Sierra Chart cumulative delta (NexusFi): https://nexusfi.com/sierra-chart/7879-sierra-chart-cumulative-delta.html
- Jigsaw manual, Pace of Tape: https://daytradr.jigsawtrading.com/pot.html
- Jigsaw manual, Summary Tape: https://daytradr.jigsawtrading.com/summary.html
- Jigsaw manual, Reconstructed Tape: https://daytradr.jigsawtrading.com/recon.html
- Jigsaw manual, Current Trades: https://daytradr.jigsawtrading.com/dscurr.html
- Optimus Futures on Jigsaw: https://optimusfutures.com/Platforms/Jigsaw-daytradr.php
- MotiveWave Speed of Tape: https://docs.motivewave.com/guides/volume-order-flow-analysis-guide/speed-of-tape
- Quantower Power Trades: https://help.quantower.com/analytics-panels/chart/power-trades
- Quantower Time Histogram: https://help.quantower.com/analytics-panels/chart/volume-analysis-tools/time-histogram
- NinjaTrader Volumetric Bars: https://static.ninjatrader.com/support/helpGuides/nt8/order_flow_volumetric_bars.htm
- NinjaTrader Trade Detector: https://ninjatrader.com/support/helpGuides/nt8/order_flow_trade_detector.htm
- NinjaTrader delta plotting (forum): https://forum.ninjatrader.com/forum/ninjatrader-8/platform-technical-support-aa/1092092-delta-plotting
- NinjaTrader up/down tick volume (forum): https://forum.ninjatrader.com/forum/ninjatrader-8/platform-technical-support-aa/1119989-order-flow-cumulative-delta-up-down-tick-volume
- Exocharts: https://exocharts.com/
- GoCharting order flow features: https://gocharting.com/features/orderflow
- GoCharting docs, basics of order flow: https://gocharting.com/docs/orderflow/basics-of-orderflow
- GoCharting docs, bar statistics: https://gocharting.com/docs/orderflow/bar-statistics
- GoCharting docs, Power Trades Scanner: https://gocharting.com/docs/orderflow/power-trades-scanner
- Platform overview (practitioner): https://zerosumnasdaq.substack.com/p/an-overview-of-orderflow-platforms
- Delta critique (practitioner): https://tendex.substack.com/p/cumulative-delta-is-not-a-measure
- NexusFi on delta divergence: https://nexusfi.com/a/market-structure/delta-divergence-futures-trading
- NexusFi pace-of-tape threads: https://nexusfi.com/showthread.php?p=881719
- Medved Trader, fade highlights: https://forums.medvedtrader.com/topic/530-quotegrid-fade-highlights-after-some-time

**OI**
- Sensibull intraday OI charts: https://blog.sensibull.com/2022/07/13/introducing-intraday-oi-charts/
- Sensibull enhanced OI page: https://blog.sensibull.com/2024/03/08/enhanced-open-interest-page/
- Sensibull live options charts: https://blog.sensibull.com/2023/01/13/live-options-charts-multi-straddle-strangle-charts/
- Opstra: https://opstrabeta.definedge.com/
- Opstra futures build-up: https://opstra.definedge.com/futures/buildup
- Opstra/Sensibull data delay (TradingQnA): https://tradingqna.com/t/how-to-get-live-oi-data/98242
- Quantsapp: https://www.quantsapp.com/
- Quantsapp, futures OI build-up: https://www.quantsapp.com/learn/articles/Use-Futures-OI-build-up-to-avoid-getting-caught-in-pullback-Shubham-Agarwal-325
- iCharts options documentation: https://www.icharts.in/opt/Documentation.php
- NiftyTrader Bank Nifty OI change: https://www.niftytrader.in/bank-nifty-live-oi-change/
- OI Pulse (Scribd addendum): https://www.scribd.com/document/505156771/Addendum
- Dhan, OI analysis: https://dhan.co/support/platforms/options-trader/what-is-oi-analysis/
- Dhan, previous-day reference: https://dhan.co/support/platforms/options-trader/what-does-the-previous-day-reference-mean-in-change-in-oi/
- Dhan, build-up: https://dhan.co/support/platforms/options-trader/what-is-buildup-in-options-and-futures/
- Fyers OI Spurts: https://support.fyers.in/portal/en/kb/articles/what-is-oi-spurts-in-options-analytics
- Fyers Trending OI: https://support.fyers.in/portal/en/kb/articles/what-is-trending-oi-in-options-analytics
- Fyers OI Interpretation: https://support.fyers.in/portal/en/kb/articles/what-is-oi-interpretation-in-options-analytics
- IIFL multi-strike OI: https://help.indiainfoline.com/portal/en/kb/articles/what-is-multi-strike-oi
- HDFC Securities ProTerminal F&O overview: https://hdfcsec.com/proterminal-page-get-an-overview-of-the-fo-market
- StockMojo NIFTY Vol/OI: https://stockmojo.in/multistrike-voloi/nifty
- GoCharting OI Sense: https://gocharting.com/docs/orderflow/open-interest-sense-oi-sense
- GoCharting OI Heatmap: https://gocharting.com/docs/orderflow/open-interest-heatmap
- CME QuikStrike OI Heatmap user guide: https://www.cmegroup.com/tools-information/quikstrike/quikstrike-user-guide-open-interest-heatmap.html
- CME volume and OI tools: https://www.cmegroup.com/tools-information/quikstrike/volume-open-interest-tools.html
- Market Chameleon unusual option volume: https://marketchameleon.com/Learn/unusual-options-activity
- Market Chameleon instructional video: https://marketchameleon.com/Instructional-Stock-and-Options-Trading-Videos/11/Unusual-Option-Volume
- SpotGamma HIRO: https://spotgamma.com/hiro-indicator/
- Unusual Whales net premium tool: https://unusualwhales.substack.com/p/how-to-use-the-net-premium-tool-on
- Unusual Whales NetFlow API type: https://api.unusualwhales.com/docs/kafka/types/NetFlow
- Upstox community, change in OI: https://community.upstox.com/t/oi-change-not-available/3316
- NSE FO real-time L1/L2 spec: https://nsearchives.nseindia.com//web/mediaattachment/2026-08/Real_time-FO-L1L2-V1.11.pdf
- Zerodha forum, intraday OI: https://tradingqna.com/t/is-the-live-open-interest-oi-data-being-provided-by-exchanges-correct/7208

**Trend and misleads**
- Cont, Kukanov, Stoikov, *The Price Impact of Order Book Events*: https://arxiv.org/abs/1011.6402
- Andersen & Bondarenko on VPIN: https://repec.econ.au.dk/repec/creates/rp/11/rp11_50.pdf
- Kellogg, "The Trouble with VPIN": https://insight.kellogg.northwestern.edu/article/the_trouble_with_vpin
- Chakrabarty et al. (2015), trade classification: https://ideas.repec.org/a/eee/finmar/v25y2015icp52-79.html
- Wyckoff laws (StockCharts): https://stockcharts.com/articles/wyckoff/2015/12/the-laws-of-wyckoff.html
- Rupeezy, OI build-up: https://support.rupeezy.in/support/solutions/articles/21000005166-what-is-oi-buildup-long-and-short-buildup
- Tradejini, OI and price: https://www.tradejini.com/blogs/how-to-interpret-open-interest-and-price-data-a-traders-guide
- Tradejini, writer's option chain: https://www.tradejini.com/blogs/understanding-the-option-chain-like-a-writer
- StockMojo, PCR: https://stockmojo.in/learn/put-call-ratio-explained/
- ShareIndia, PCR: https://www.shareindia.com/knowledge-center/trading-investment-strategies/put-call-ratio-in-stock-market
- Singh & Gangwar, Nifty futures intraday volatility (MPRA): https://mpra.ub.uni-muenchen.de/89689/
- Intraday volume forecasting (U/J shape): https://arxiv.org/pdf/2505.08180

**Cross-index**
- SMT divergence: https://www.eltraderfinanciado.com/en/blog/smt-divergence
- NexusFi on NYSE TICK: https://nexusfi.com/a/indicators/nyse-tick-index-futures-trading
- Stockezee index contribution: https://www.stockezee.com/index-contribution
- StockMojo NIFTY weightage: https://stockmojo.in/index-weightage/nifty
- indmoney, Nifty vs Bank Nifty divergence: https://www.indmoney.com/blog/stocks/nifty-falls-bank-nifty-rises-market-rotation-september-30-2026

**Design**
- Bloomberg, concealing complexity: https://www.bloomberg.com/company/stories/how-bloomberg-terminal-ux-designers-conceal-complexity
- Bloomberg, colour accessibility: https://www.techatbloomberg.com/blog/designing-the-terminal-for-color-accessibility/
- Bloomberg UX accessibility: https://www.bloomberg.com/ux/accessibility/
- AG Grid flashing cells: https://www.ag-grid.com/javascript-grid-flashing-cells/
- AG Charts flash on update: https://ag-grid.com/charts/react/flash-on-update.md
- Tufte, sparklines: https://www.edwardtufte.com/notebook/sparkline-theory-and-practice-edward-tufte/
- Few (2008), *Practical Rules for Using Color in Charts*: https://www.makinggood.ac.nz/media/1257/few_2008_rules_for_using_color.pdf

**Internal, for context only**
- `memory/upstox-api-facts.md`
- `tapemap/docs/research/quant-tower-india-2026-09-24.md` (the ~3-min OI cadence claim)
- `tapemap/sweep.py:115-130` (the quote-rule coin-flip argument)
