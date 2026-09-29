# The order-flow reader: final design (supervisor), 2026-09-29 night

This merges four rounds, each written up in this folder:
- `1-research.md`: 67 sources, rubric R1–R18 and honesty gates H1–H8;
- `2-data-audit.md`: the data;
- `3-current-reader-audit.md`: the current tool on 29 Sep;
- `4-design-fable.md` and `4-design-opus.md`: two blind designs, each with a Rev 2;
- `5-critique-by-*.md`: the cross-critiques;
- `6-judgement.md`: an independent judge who re-checked the numbers against the data files.

**Nothing is built.** Every rule below is pre-registered; she signs one threshold sheet before anything reaches her chart.

---

## 1. The answer to her question

**Today's tool is not professional grade.**
- The judge scores it 1 pass, 10 partial and 15 fail.
- It fails three honesty gates: it hides data holes, it has no honest warm-up, and its marks repaint on zoom.

**Built and passed, the merged design is a professional-grade reader of NSE index futures on the data a retail desk can get.**
- At the read that matters most for Indian index traders, **who is opening vs closing, across the roll**, it goes further than Bookmap, ATAS or Sierra Chart. None of them reads delta × OI × price per leg, or the expiring vs continuing contract.
- **It is not "world class" in the full sense.** Every buy/sell side we have is inferred from 1-second snapshots: Upstox, and GoCharting's undisclosed method. Our two tapes disagree in sign on about 31% of bars.
- What would close that gap is an **NSE tick-by-tick feed through a licensed vendor**, where the exchange names the aggressor. With it, the same design reads the true aggressor, trade sizes and spread legs. Icebergs and cancel-versus-fill need order-level data, a further step.

I won't call it world class until that feed exists. I will call it the most honest and most India-specific order-flow reader she can get on retail data, once it passes 10 shadow sessions including the 27 Oct expiry.

## 2. What 29 Sep taught us

The judge verified every item here against the files.

| What | Fact |
|---|---|
| Her afternoon question | Sep: Cum Δ +7,060 lots for about +40 pts with OI −10.8k, so shorts covered into settlement. **Oct: +25.7k OI with price +69, and the spread 111 → 178 against about 120 carry. Positions were built long in October; combined OI +14.9k.** Reading Sep alone gave the wrong direction; both designers and I made that mistake first. |
| Session end | **15:40 since 3 Aug**. TapeMap cuts at 15:30 in about 30 places, a live data-loss bug. The Upstox candles for 29 Sep run to 15:39. |
| Feed silence | GoCharting sent nothing 12:26 → 16:08. Nobody was told. |
| Repaint | Marks recompute when the GoCharting row size changes on zoom; 13 of 57 marks changed on 29 Sep. |
| Two tapes | GoCharting and Upstox disagree in delta sign on 23 of 74 bars, both turns included. |
| Blocks and spreads | The 10:05–10:07 "4,528-lot buy" is almost certainly a calendar-spread leg: Oct OI +5.1k the same minute, and missing from the exchange candle. |
| OI batching | The minute OI change exceeds the minute's volume on 59 of 384 minutes. It is a publication step, not positioning. |
| Closing auction | Spot is frozen from 15:15 to 15:29, so every basis or convergence number after 15:15 is invalid. |
| Her zone machine | The best reader of the day: BUY d2 09:39 and SELL u2 12:18, both extremes. **Untouched.** |

## 3. What gets built

Base: design B Rev 2. Taken from A: the ruler frozen at the open, the extension heartbeat, the check that marks a print as a spread leg when the other month's OI mirrors it, and restraint on the chart. All 18 of the judge's must-fixes apply.

### 3.1 Plumbing: live fixes, not reads

| # | Fix | Why |
|---|---|---|
| ~~P1~~ | **Dropped, her decision 2026-09-29:** "leave the part of recording till 15:40 pm … there is going to a change soon". The reads use whatever session the data carries, and say so. | — |
| **P2a** | **Only in the monthly roll window, for each of NIFTY, BANKNIFTY and SENSEX** (her decision: "look at the last expiray the month;y expiry"). From 5 sessions before that index's monthly futures expiry through expiry day, poll the continuing contract's 1-minute REST candles (price, volume, OI) every minute. The expiry date comes from the instrument master; nothing is hard-coded. Weekly expiries are options only and need no futures capture. | Without it every monthly roll day is misread (29 Sep) |
| **P2b** | In the same window, subscribe to the continuing contract's book, so its Δ exists. The GoCharting POST carries its contract. | Oct-side delta on roll days |
| **P3** | Feed health measured from the data (post arrival, bar lag, volume versus Upstox, a tab heartbeat), not from timers, because Chrome throttles hidden tabs. States: LIVE / SLOW / DEAD. On DEAD, a black band on every face: **"GoCharting bhej nahi raha · 12:26 se · tab kholo / F5"**, and every GoCharting-dependent read goes to CAN'T CHECK. | 12:26–16:08 went unseen |
| **P4** | Repair short bars: a truncated tick bar is flagged and re-posted as a revision, never silently kept. | The 12:25 bar made a false E |
| **P5** | The batched-OI screen and the closing-auction freeze flags. | The two traps above |

### 3.2 The reads: `reader.py`, pure functions, append-only log, SHADOW first

1. **Canonical minute:** the exchange candle gives price, volume and OI; the book gives Δ. One volume universe per ratio.
2. **Legs,** the unit of reading.
   - Directional change with the ruler **frozen at the open**: 3 × the prior sessions' unit, about 29 pts on NIFTY. It never re-sizes intraday; that was the old flow-rank bug.
   - Confirmed on 1-minute closes, so a restart rebuilds the same cut.
   - Her give-up levels stay live on price, never waiting for a close.
   - Legs are grouped as TREND / RANGE / BREAKOUT.
3. **Effort vs result per leg:** points per 1,000 lots on both tapes, spread and block prints excluded, ranked against **today's** completed legs only, with n shown. It is honestly silent in the warm-up.
4. **WHO is acting per leg** (delta × OI × price): new longs / short covering / new shorts / long liquidation, plus ABSORBED. OI is read with a one-update tolerance.
5. **Roll and expiry mode,** in the last 5 sessions before expiry.
   - Sep numbers are labelled "expiring". The direction read moves to the **continuing contract**: Oct's own price × OI class, combined OI, the calendar spread, and Oct − spot before 15:15.
   - Four named cases: pure roll / roll plus build / closed / mixed.
   - It never says "bullish" or "bearish"; it names who did what.
6. **Absorption at a named level:** a state, never a reversal call, with the book as a witness.
7. **CVD divergence only at swing extremes and key levels,** on both tapes.
8. **Finished vs unfinished extremes,** by the ATAS rule; the judge corrected an inversion in round 2.
9. **Tape agreement:** when GoCharting and Upstox disagree, the read says SPLIT, never a false certainty.
10. **FLOW-row word for her hold/fold engine:** WITH / PULLBACK / AGAINST / SPLIT / CAN'T CHECK. It is shadow-logged beside the current row, and replaces it only on her signature.
11. **Day story:** one line per leg, e.g. *"13:30–15:29 · Sep: shorts covered into expiry (Δ +7.1k, OI −10.8k) · Oct: positions built long (+25.7k, +69 pts, spread rich) · combined +14.9k"*.

### 3.3 Her P/A/E/C marks

**Kept.** They are hers and they work. The fixes:
- the detection row is **frozen per day**, so zoom can never change a mark;
- TapeMap's record is the authority on reload;
- E may fire again in a leg on a weaker new extreme, so the 09:35 low gets its E;
- P says "chhota trap" unless it sits at a swing extreme, and it is demoted inside a RANGE;
- block and spread prints are screened out.

**Before this goes live, she sees the list of marks that would change on past days.**

### 3.4 The face: professional, not "AI slop"

- **Two hues plus grey.** Blue is buyers, vermilion is sellers, grey is reference or absence, and black inverse is alarms only. LIGHT mode.
- **Type:** Inter with tabular numbers, weights 400/600, and a small, consistent marker grammar. No big discs, no thick bars.
- **At most 9 reader objects on the chart:** the current leg, two walls per side with their lean count, NEXT FIGHT, her marks, and the feed band. Everything carries a **Hinglish chip with its number** (her standing rule).
- **A leg table on the Trade tab,** and the day story in one line.
- **Every number is tagged [M] or [I].** Delta is **[I]**, because the side is inferred. No hit rates, ever.

## 4. Validation: descriptive, never an edge claim

- **Replay over every recorded day** (6 days with both tapes, plus 28 Sep as an ordinary day). It checks only that each read truthfully describes the tape, against pre-registered churn and misdescription bars. No outcome scoring, no hit rates (house rule 2).
- **A shadow run for 10 sessions, including the 27 Oct expiry.** Reads are logged, and shown only on a shadow toggle.
- **Falsifiers per read** are written in the threshold sheet.

## 5. What she decides, and when

| When | Her decision |
|---|---|
| **Decided 2026-09-29 night** | P1 (15:40) dropped. P2 only in each index's monthly roll window: built before the October window opens, 5 sessions before the Oct expiry. |
| After P3 is built | Sound on DEAD, once the hidden-tab measurement is in |
| After R-a..R-f have run in shadow | The one threshold sheet (about 20 numbers, each with its reason) |
| After 10 shadow sessions incl. 27 Oct | The chart objects go live (F4), and the FLOW word replaces the row (F5) |
| Anytime | Whether to buy an NSE tick-by-tick feed through a licensed vendor. The only step that makes "world class" literally true. |

**Size:** about 4–6 weeks of careful work, with plumbing first. The first shadow data flows as soon as the leg engine (R-a) lands.
