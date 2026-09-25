# Quant Tower India: how it reads option data, and what the WAR tab should take from it

Research note, 2026-09-24. Public material only: product pages, public docs, the
public Telegram preview, and YouTube videos (titles, descriptions, auto-captions
and paused frames). No account was created, no login was used, nothing was
downloaded. Tags: **[S]** means seen in the source at the URL given. **[I]** means
my inference. **[?]** means I could not verify it.

---

## 0. The answer in six lines

- "Quant Tower India" is **Quantower India** (quantower.in), the Indian edition of
  the Quantower trading platform, run by Quantower Technologies Pvt Ltd, Mumbai.
  Certainty is high, about 85%. The reasons are in §1.
- The "really good" option analysis is two tools that are not in the stock chain
  or analyzer: **Options Surface**, a heatmap of every strike's OI over time drawn
  on the spot chart, and **ODX Profiles**, a third-party add-on that shows each
  strike's rupee buying and selling per candle as a mirrored ladder beside the chart.
- Options Surface is the closest public relative of Mary's WAR tab. Its presenter
  reads it the way her rule does: ATM strikes only, peak time, peak value, then the
  give-back.
- The compression trick worth taking: **one cell per strike per time bin, colour for
  magnitude, rows placed at their strike price on the spot axis, spot candles drawn
  over them.** In their demos, 16 to 64 strikes over several days fit in one chart pane.
- Most of their *reading rules* fail her doctrine: 4-colour build-up labels, per-strike
  PCR "zones" with close-above and close-below rules, ₹8–10 Cr arrow thresholds, the
  "3+ arrows" setup, and 64-strike windows.
- They sell no GEX, max pain, IV-rank or skew tool, and no scanner. A GEX profile and
  a scanner are things users ask them for in the comments [S].

---

## 1. What the tool is, and how sure I am

| Fact | Tag |
|---|---|
| quantower.in is run by Quantower Technologies Private Limited, Chembur, Mumbai. It is a multi-asset, broker-neutral platform with 40+ panels. | [S] https://quantower.in/ |
| It connects to Indian brokers including **Upstox, Dhan, Zerodha, Fyers, 5paisa, AngelOne, Kotak Neo, IIFL, Shoonya, CompositEdge, Nirmal Bang, Gill**, and to data feeds. | [S] https://quantower.in/connections |
| Plans are Free, Lite (₹800/month) and Advanced (priced per segment). Add-ons: **Options Dynamix Indicators (ODX) ₹1,300/month**, which is third-party and needs Advanced; **STF Fair Price ₹999/month**; **STF Big Move ₹1,200/month**. | [S] https://quantower.in/pricing |
| 5paisa distributes it under the URL slug `quant-tower-exe`. | [S] https://www.5paisa.com/technology/quant-tower-exe |
| The YouTube channel "Quantower India" has about 8.5K subscribers. There is a public Telegram channel `QuantowerIndia`. | [S] https://www.youtube.com/c/QuantowerIndia, https://t.me/s/QuantowerIndia |

**Why I think this is what she means.** The product name is literally "Quantower
India", and people say and write it as "Quant Tower". 5paisa's URL spells it
`quant-tower`. The channel's own Hindi auto-captions render the greeting as
"...टावर यूजर्स" [S, gGue13TQ7zU]. The India edition also carries option-data
visualisations that are distinctive enough for a trader to remember: Options
Surface and ODX.

**The other candidate, at about 10%.** Quantsapp (quantsapp.com) is a separate and
much larger Indian options-analytics app. If she meant Quantsapp, this note does
not cover it. The global Quantower (quantower.com) runs on the same engine but
does not carry the India-only option tools described below [I].

---

## 2. Every way it analyses option data

### A. Options Surface (built in; first released Sept 2022; "the best options data analytical tool" in their own title)

Sources: webinar 2022-09-28 https://www.youtube.com/watch?v=cg3zxXKrA8E ·
expiry-hour recording 2022-09-29 https://www.youtube.com/watch?v=Q7NPeF5qJPU ·
second webinar 2023-08 https://www.youtube.com/watch?v=GiR-ixLdmZo ·
Telegram posts #191–#221, #277–#283 https://t.me/s/QuantowerIndia?before=209 ,
https://t.me/s/QuantowerIndia?before=287

**Setup [S].**
- The indicator goes on the **spot** chart. Its settings are underlier, expiry,
  days of history (they suggest 5, and at most 10), interval, **number of strikes
  "from ATM up and down"** (12, 16, 32 or 64 shown), and one data point per pane.
- It needs a feed that serves **historical OI and tick history**. TrueData, TT
  Blaze, IIFL, CompositEdge, Nirmal Bang and Gill were named. 5paisa was not
  supported at launch.
- It was sold in the "All-in-One" package. **Current availability [?]:** the public
  help site (help.quantower.in) has no Options Surface page. The last public demo I
  found is Aug 2023.

**Screen form [S, frames seen].**
- Each chart pane is a heatmap. A **row is a strike, drawn at that strike's price
  on the spot price axis**. A **column is a time bin**. The **spot candles are drawn
  over the heatmap**, so you can watch price walk into a band.
- CE and PE sit in **two side-by-side panes** with the same axes.
- Hovering a cell shows expiry, strike, the option's value (OI), and the net change.
  Build-up cells also show price value and price change.
- For expiry day they laid out a **10-pane grid**: NIFTY and BANKNIFTY ×
  {per-strike PCR, CE ΔOI, PE ΔOI, CE build-up, PE build-up}, all on one monitor.

**The data points:**

| # | Data point | What it shows / how it is computed | Colour | Tag |
|---|---|---|---|---|
| A1 | **Change in OI, interval by interval** | ΔOI per strike per bin. They recommend a 30-min bin, and say 5-min "whipsaws". | Blue = OI added (lighter or brighter = bigger), red = OI shed; darker = smaller | [S] |
| A2 | **Change in OI from the start of the session** | Cumulative ΔOI from the prior day's OI, per strike. The presenter compares it to cumulative delta. At a 5-min bin it draws as continuous horizontal bands. | Brightest blue = largest add. As it turns negative it goes dark blue → dark red → bright red (largest unwinding). | [S] |
| A3 | **OI build-up** | Price change × OI change → one of four states per strike per bin | Red = short build-up, green = long build-up, blue = short covering, orange/yellow = long liquidation | [S] |
| A4 | **Per-strike PCR** | PE OI ÷ CE OI for each strike | Blue where calls dominate (strikes above spot), red where puts dominate. A **pale blue/pink band near PCR ≈ 0.9–1.1** is the "light blue zone". Pink = above 1. | [S] |
| A5 | Volume delta per strike | Announced in Sept 2022 with bugs still open | — | [?] could not confirm it shipped |

**How their own presenter reads it (2023 webinar) [S].** This is the part closest
to Mary's rule:
- He says he is looking at the at-the-money strikes, not the out-of-the-money ones.
- He expects morning straddle writing at ATM until about 9:30–10:00.
- One example: the 44,000 CE built to a **peak of 2,33,650 at about 10:55**, then was
  shed as the market rallied. Writers then reappeared **three strikes higher**.
- He reads a strike's OI peaking and then falling (2.73L → 2.64L) as a possible turn.
- He says a real trend shows OI building **across the board**, while a turn shows
  reductions at particular strikes.
- He puts the question as "where exactly the open interest is peaking".

**What the PCR zone is used for [S].** The "light blue zone" is used as support
and resistance with a rule: a close below the zone gives a short, with a stop above
it. Telegram posts read it as, for example, "resistance shifted to 38,900".

**Data cadence claim [S, their claim].** In the Q&A they say exchange OI reaches
everyone about **once every 3 minutes**. That limits how precisely any peak time can
be stamped. See the check in §5.

### B. ODX: Options Dynamix Indicators (third-party add-on, ₹1,300/month on Advanced)

Sources: https://www.youtube.com/watch?v=uTJRFkXnqic (webinar, 2024-01-03, Hindi) ·
https://www.youtube.com/watch?v=n5Hupz3U2CI (full guide, 2026-02-20) ·
https://www.youtube.com/watch?v=yUgG6lDGoYo (Total Buy Sell Aggregator, 2025-02-11) ·
https://www.youtube.com/watch?v=gGue13TQ7zU (intro, 2023) · playlist
https://www.youtube.com/playlist?list=PL3niiUZFo7CaKIPG_ATS-V4WDq9lNdbyP

| # | Indicator | What it shows / how it is computed | Screen form | Tag |
|---|---|---|---|---|
| B1 | **ODX Profile** | For each strike, **net buying or selling in rupees** (L/Cr) for CE and PE, in **one selected candle** and in the **live candle**. Built from tick-level trades. It updates live, unlike the ~3-min OI. | A **mirrored ladder**: strike labels in a centre column, CE bar on the left, PE bar on the right, green = buy, red = sell. It is **pinned to the right edge of the chart ("stick to right")**. Two ladders sit side by side, one for the selected candle and one for live. The default is 12–16 strikes; they suggest 16–20 for NIFTY and 22–24 for BANKNIFTY. | [S] |
| B1a | How the buy/sell split is made | Not published. Aggressor classification (trade at ask = buy, at bid = sell) × LTP × quantity, summed per strike per candle, is the likely method. A viewer asked how there can be selling without buying, which suggests it is aggressor-side. | — | [I] |
| B1b | Arrows and highlights | Up or down arrows appear when \|value\| ≥ a threshold: **₹8 Cr on NIFTY 5-min**, or ₹10 Cr in the 2024 webinar. A **yellow box** marks ≥ ₹15 Cr. Below-threshold bars are dimmed and above-threshold bars are brightened. | on the ladder | [S] |
| B1c | Their reading rules | Follow the sellers, since selling takes margin. **₹10 Cr+ of OTM selling in one candle is read as "market not going there"**; the presenter says three months of notes back it. Skip the 9:15 candle. **3+ arrows** makes a setup. | — | [S] |
| B2 | **ODX Custom OI Profile** | The same ladder, but ΔOI per strike for the selected candle or a custom range. Bright = increase, dark = decrease. | ladder | [S] |
| B3 | **ODX Range Profile** | B1 summed over a selected range of candles | ladder | [S] |
| B4 | **Multi Metrics Aggregator → Total Buy Sell Aggregator** | Per candle, **buys summed across the strike window drawn upward and sells drawn downward**, each split into CE and PE. The panel shows the strike range it covers (for example 25,100–26,050). Its purpose is to show **which candle to click** in B1. | A mirrored histogram under the price chart, with a legend box of Buy/Sell × CE/PE in Cr and threshold highlights | [S] |
| B5 | Options Price profile | The option LTP per strike at the selected bar, drawn as a ladder | ladder | [S, frame] |
| B6 | ODX Scalper, Volume Surge, Imbalances, Cumulative Delta | Order-flow tools on the chart, not option-chain analysis | — | [S], out of scope |

### C. The rest of the options surface area

| Tool | What it is | Tag |
|---|---|---|
| **Option Analytics panel** (stock Quantower) | A chain ("desk") with price, OI, IV, the five Greeks, several series at once and a custom strike depth. The analyzer draws payoff and Greek profiles and What-If lines (up to 5) for time and vol. | [S] https://help.quantower.in/analytics-panels/option-analytics.md , https://quantower.in/options-trading-features |
| **Large option trade alerts** | A watchlist of every strike carries a "Trade value" column (LTP × quantity per tick). Alerts fire at > ₹50L and > ₹1Cr, colour the row, and link to Time & Sales, which shows the aggressor side. | [S] https://www.youtube.com/watch?v=heDQ2AHN-hI |
| **Futures OI build-up watchlist template** | The same four-colour scheme applied to futures, filtered at ±5% OI change, with open = high and open = low flags | [S] Telegram #227–229 |
| **Straddle premium used as a range** | Telegram commentary took an ATM straddle of 240–250 and read it as the expected day range. The "highest OI increase" strike is highlighted light blue. This is commentary, not a separate tool. | [S] Telegram #220 |
| **STF Fair Price / STF Big Move** | Third-party. Uses volume and OI to give a "fair price" and to say whether writers or buyers dominate. The method is not published. | [?] could not verify, not public |
| **Not offered** | GEX or dealer gamma (a user asks for a "Dynamic Gex profile"), max pain, IV-rank, skew or term charts, scanners (users ask for an ODX scanner) | [S] comments on https://www.youtube.com/watch?v=YqZmQJuKkYs , https://www.youtube.com/watch?v=uTJRFkXnqic |

---

## 3. What users call "really good"

- **History across the whole chain on one chart.** The presenter's own pitch in the
  2022 Q&A is that other platforms show only the current interval, while this
  shows what happened before. Viewers agreed in the Q&A [S].
- **All strikes on a single screen**, so you do not have to page through a chain
  [S, 2023 webinar].
- **ODX is tick-live, while OI is slow and two-way.** Their argument is that OI can
  rise only a little while a lot of selling happened, and the rupee flow shows it [S].
- **Comments** [S]:
  - Positive: "Outstanding analysis", "brilliantly designed", "Great presentation".
  - Sceptical: whether it still works once every retailer has it, a request to see
    it traded live, a note that the method is "Outdated" after the expiry change,
    confusion about packages, and a question about how selling can happen without
    buying.
- **My read [I].** The draw is the *picture*: price walking into a coloured wall of
  OI, and the wall changing colour behind it. The draw is not the signal rules. The
  rules are thresholds and folklore.

---

## 4. Judged against Mary's doctrine

Her rule, briefly: near ATM only; the top two strikes by **absolute** OI per side;
the **sequence** (building → stops building → unwinding) is the answer; the side
that stalls first and then gives OI back is the fuel; the **peak time and the spot
at that time** are the stamp. House rules: no hit rates or scores, [M] or [I] on
every number, missing is never zero, no BULL/BEAR headlines.

| Method | Verdict | Why / how to fit her rule |
|---|---|---|
| A2 ΔOI since session start as a strike × time heatmap | **ADAPT** (core) | This is her `k` series with magnitude drawn as colour instead of band thickness, and that is the compression. Keep rows at strike price with spot drawn over them. Adapt it to: ±6–8 strikes, minute-precise peak stamps, "ruin" shown after the peak (§5), negatives never drawn as a thin positive. |
| A1 ΔOI per 30-min bin | **ADAPT** | A 30-min bin blurs the peak time by ±15 min, and that kills her stamp. Use the bin only as cell width. Encode the per-minute *slope sign* (building / flat / unwinding) inside the cell as a state, not as a separate pane. |
| Presenter's ATM-only, peak-then-give-back reading | **ADOPT** | Their human reading is her rule stated informally. It is external evidence that the picture supports the rule. |
| CE and PE in two side-by-side panes | **ADAPT** | For "which side stalls first" she needs CE and PE for the same strike at the same x. **Split each strike row into a CE half and a PE half** (side as hue, the same pairing the app uses), so the comparison is one eye-drop, not a pane jump. |
| 10-pane small-multiples grid | **ADAPT** (BOARD) | Use the idea, not the panes: NIFTY / BANKNIFTY / SENSEX mini-WARs side by side. |
| B1 mirrored ladder, pinned right, selected versus live | **ADOPT** layout, **ADAPT** content | The centre strike column with CE bars left and PE bars right is the most compact cross-section there is. Fill it with **absolute OI now, plus a tick at the peak**, not rupee flow. "Selected versus live" becomes "cursor time versus now". |
| B1b highlight box | **ADAPT** | Keep a box outline, but draw it **by rank**: the top-2 by absolute OI per side inside the window. Do not use a ₹ threshold. A rank is a fact; a threshold is a tuned signal. |
| B4 "which candle to look at" aggregator | **ADAPT** | Keep the job and change the source. Draw **event ticks on the time axis** where a top-2 front changes state (build → stall, stall → unwind), each stamped with time and spot. Do not sum buy and sell across 20 strikes, because that is aggregate. |
| B1 rupee net buy/sell per strike (the data itself) | **Candidate only [I]** | This is a new sense: aggressor-classified premium flow. TapeMap's Upstox full feed carries LTP, LTQ and depth for the ±3 senses strikes, so classification would be inferred [I]. If wanted, pre-register it (rule, parameters, falsifier, kill clock) and log it forward. Do not display it until then. |
| A3 four-colour build-up labels | **REJECT** | The retail futures-quadrant folklore. Each cell is labelled alone, so there is no sequence. For options, "long build-up" assumes who initiated the trade, which OI plus premium change cannot show. Direction is baked into the colour, which is a BULL/BEAR headline in disguise. |
| A4 per-strike PCR "light blue zone" plus close-below or close-above rule | **REJECT** as a signal · *ADAPT at most as a location* | A ratio with a 0.9–1.1 colour threshold and an entry/stop rule is a trading system with an implied hit rate. At most, trace the near-ATM strike where CE and PE absolute OI cross as a line [M], and draw no rule from it. |
| B1b/B1c arrows at ₹8–10 Cr, "3+ arrows", "₹10 Cr OTM selling = market won't go there" | **REJECT** | These are thresholds as signals with a claimed backtest. The OTM focus is exactly what her rule excludes (far strikes are hedges and premium collection). |
| 64 strikes, 5–20 days of history | **REJECT** width | Near ATM only: ±6–8. One session, 09:15 → 15:30, holes left as holes. |
| Aggregate buy/sell histogram, aggregate PCR | **REJECT** | Aggregate across the chain |
| STF Fair Price / Big Move | **REJECT** | A black box with a "who is dominating" verdict |
| Large-trade alerts ≥ ₹50L / ₹1Cr | **ADAPT, low priority** | A measured print near ATM strikes could appear as a marker on the WAR timeline [M]. No alert sound and no verdict. |
| Option Analytics desk and payoff analyzer | **REJECT** for WAR/BOARD | The seller doctrine already excludes payoff diagrams and chain dumps. |

---

## 5. Compressing ±6–8 strikes of OI-over-time into one small panel

A concrete shape built from the adopted and adapted items. It is a design input,
not a spec.

- **Rows.** Take the strikes within ±N (N = 6–8) of spot at *any* minute today.
  NIFTY with a ~300-point range gives about 17–22 rows. Place each row at its
  strike price on the spot axis (Options Surface) and draw the spot line or
  candles and her named levels over it (the app's brass).
  - **When a strike was outside ±N of spot at that minute, draw it hatched**, as
    "not near ATM then", never as zero. This keeps the near-ATM rule honest while
    spot drifts [I].
- **Split rows.** Each strike row has a CE half on top and a PE half below, in the
  app's side hues. At 7px per half, 22 rows take ~310px. The current plot is 740px.
- **Columns.** 5-min cells give 75 columns and fit ~900px at 12px each. **The peak
  stays at minute precision**: draw a tick inside its cell at the exact minute. The
  bin only paints the fill.
- **Cell fill.** Intensity = `k` (ΔOI since open), scaled to the day's maximum so
  strikes compare.
  - After a row's running-max minute, draw the cell as **an outline at peak level
    with the fill at the current level**. That is the "ruin" look her band already
    has, shrunk to a cell.
  - Negative `k` gets an empty cell with a mark, never a pale positive.
  - `backfill` minutes are drawn at reduced alpha, never in another hue (WAR fact 4).
- **Top-2 by absolute OI per side.** Outline those rows. This is a rank, not a
  threshold.
  - *Observation from reading WarTab.tsx [I]:* today's `ranked` sorts by the peak of
    **change** `k`. Her rule ranks by **absolute OI**. The payload's `peak[]` field is
    absolute OI but carries no time. Reconcile this deliberately; it is not changed here.
- **Pinned right ladder.** A mirrored CE | strike | PE bar ladder of absolute OI
  now, with a peak tick on each bar, sharing the row axis. The heatmap is history
  and the ladder is the present.
- **Time-axis event ticks.** Mark where a top-2 front goes build → stall and
  stall → unwind, with time and spot in the rail. Every word stays in the rail.
- **Alternative [I, not from Quant Tower].** Horizon charts (the band folded into 2–3
  intensity layers) keep length-based magnitude at about ⅓ the height. This is worth
  a side-by-side test against the heatmap, because colour judges magnitude less
  precisely than length.

**Check before trusting minute-level peak stamps.** Quant Tower's presenter
says exchange OI arrives about every 3 minutes [S, their claim]. If her
`/api/oihist` minutes also show OI stepping every ~3 min, the stamp has ±3-min
resolution, and the "10:19 peak, 10:20 drop" reading should carry that error bar.
This is testable from her own minute file: count the minutes where OI is unchanged.

---

## 6. For the BOARD ("chess board") page, the top three

1. **The mirrored near-ATM ladder** (ODX layout) for ±6–8 strikes, with the top-2 per
   side boxed by rank. The rail carries each front's state (building / stalled /
   unwinding), peak value, peak time and spot at peak. This is her strike-inventory
   and who-is-trapped square.
2. **Sequence event ticks** on the board's tape or timeline: the build → stall → unwind
   transitions of the top-2 fronts, which is the "which candle to look at" job done
   by her rule instead of by rupee totals.
3. **Three-index mini-WARs** (NIFTY / BANKNIFTY / SENSEX, from the 10-pane grid), about
   120px each, so she can see at a glance which index's near-ATM book is being forced.

---

## Sources

- https://quantower.in/ · https://quantower.in/connections · https://quantower.in/pricing ·
  https://quantower.in/options-trading-features · https://quantower.in/assets-and-brokers-features
- https://help.quantower.in/llms.txt · https://help.quantower.in/analytics-panels/option-analytics.md
- https://www.5paisa.com/technology/quant-tower-exe
- https://t.me/s/QuantowerIndia?before=209 · https://t.me/s/QuantowerIndia?before=240 ·
  https://t.me/s/QuantowerIndia?before=287
- Options Surface: https://www.youtube.com/watch?v=cg3zxXKrA8E ·
  https://www.youtube.com/watch?v=Q7NPeF5qJPU · https://www.youtube.com/watch?v=GiR-ixLdmZo
- ODX: https://www.youtube.com/watch?v=uTJRFkXnqic · https://www.youtube.com/watch?v=n5Hupz3U2CI ·
  https://www.youtube.com/watch?v=yUgG6lDGoYo · https://www.youtube.com/watch?v=gGue13TQ7zU ·
  https://www.youtube.com/watch?v=YqZmQJuKkYs ·
  https://www.youtube.com/playlist?list=PL3niiUZFo7CaKIPG_ATS-V4WDq9lNdbyP
- Large trades: https://www.youtube.com/watch?v=heDQ2AHN-hI
- ODX Scalper announcement: https://x.com/QuantowerIndia/status/1808025705474560244
- Alternative candidate, not researched: https://www.quantsapp.com/
