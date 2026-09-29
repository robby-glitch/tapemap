# 5. Cross-critique by Designer B (Opus) of `4-design-fable.md`

**Written:** 2026-09-29, night.

**Method:** read-only. Every check was re-run in my scratch folder, `...\scratchpad\designB\`:
- `octs.py`: Sep/Oct by phase;
- `volcmp.py`: book volume vs exchange candles;
- `unfin.py`: finished/unfinished extremes;
- plus quick checks on B5, spot and the option chain.

**Sources:**
- `F:nn` = a line of `4-design-fable.md`.
- `O:` = my own `4-design-opus.md`.
- The new data is `docs/reader/data-2026-09-29/fut_{SEP,OCT}_1m.json`.

## 0. What the Oct file changes for both of us (read this first)

**The Oct file, by phase** (Upstox exchange 1-minute candles; OI in lots [M]):

| Window | Sep pts | Sep OI | Oct pts | Oct OI | Combined OI | Oct−Sep spread |
|---|---|---|---|---|---|---|
| 09:15–09:38 (drive) | −160 | −3,889 | −133 | +3,406 | −483 | 116 → 143 |
| 09:39–11:06 (base) | +16 | −8,057 | +19 | +12,616 | +4,559 | 138 → 141 |
| 11:07–11:14 (squeeze) | +93 | −1,028 | +80 | +727 | −301 | 151 → 137 |
| 11:15–12:01 (grind) | +53 | −1,162 | +65 | +4,237 | +3,075 | 131 → 142 |
| 12:02–12:33 (reversal) | −106 | −1,319 | −109 | +5,083 | +3,764 | 148 → 144 |
| 13:30–14:30 | +20 | −1,117 | +61 | +9,802 | +8,685 | 135 → **176** |
| 15:01–15:29 | +33 | −7,972 | +31 | +8,476 | +504 (a pure roll) | 166 → 164 |
| **13:30–15:29** | **+40** | **−10,791** | **+69** | **+25,726** | **+14,935** | 135 → 164 |

**Three facts neither design had:**

1. **The afternoon built positions in Oct with price rising.**
   - Oct OI rose +25.7k, 2.4× the Sep fall, while Oct's price went up.
   - The spread went rich (Oct−spot basis 149 → 189 at 14:30).
   - Combined OI was +14.9k.
   - Read with the ordinary OI table, Oct is **new longs**.
   - "Short covering, absorbed; not new buying; not bullish" is true **for Sep only**. Both designs, and the research's R3 pass line, called the whole market from the expiring contract.
2. **Sep's "little progress" is partly convergence.**
   - Sep−spot went from 14.2 to −1.9 over 13:30–15:29.
   - Spot rose +56.5 and Oct +68, while Sep rose +46 close-to-close.
   - About 16 points of the "absorbed" gap is the expiring premium dying, not a passive seller.
3. **The 10:07 block is a spread-type print.**
   - The exchange's regular 1-minute candle for 10:07 holds 684 lots; Upstox `vtt` holds 5,990.
   - The 4,523-lot print is not in the candle.
   - Oct OI jumped +5,134 in the same minute (215,476 → 220,610) as Sep OI jumped +4,651.
   - Over the day `vtt` exceeds the candle volume by 22% (16,568 lots; median 20 lots a minute). That gap is consistent with spread-leg executions [I], and it is unverified on other days.

---

## 1. Where the Fable design is WRONG

| # | Claim (line) | What the data says |
|---|---|---|
| W1 | The afternoon is "short covering into expiry, absorbed; not new buying; **not bullish**. Positioning moved to Oct: CAN'T CHECK" (F:274; also F:73 and F:267) | Oct shows new longs: +25.7k OI, +69 pts, basis richening. The Sep-only read is presented as the market read. My design made the same error (O §6). |
| W2 | Roll resolution: "(a) Oct OI +9.8k with Oct delta −7k: shorts rolled / (b) Oct OI flat: shorts closed" (F:80, F:71) | Oct delta does not exist in the only Oct source we now have (the REST candles have no side), so neither branch can fire. The rule also only imagines *shorts* rolling or closing. 29 Sep is a third case the rule has no word for: Oct OI far above the Sep fall, price up, spread widening. |
| W3 | Volume cross: "the minute Oct 5-minute volume first exceeds Sep's (from then on Oct is the leg-engine price)" (F:78) | On 29 Sep Oct volume exceeded Sep in **71 of 77** 5-minute bins, from **09:20**. The rule switches the leg engine to Oct at 09:20 and attaches Sep GoCharting delta to Oct legs. That is the splice its own falsifier forbids (F:302). Its walk-through never does it (F:251), so the rule and the replay disagree. |
| W4 | Leg effort attaches whole 5-minute bars "by their close time" (F:42), so the bar holding the pivot goes to the *next* leg | This produces false **ULTA FLOW** calls on 29 Sep:<br>• "UP 09:38→09:42 +63 on net −25 / −423: ULTA FLOW" (F:259). The minute tape for 09:39–09:42 shows UX Δ+251 (21% of volume): buyers. The −25/−423 is the 09:35 bar that *made the low*.<br>• "UP 12:33→12:41 +84 on −217 (ULTA FLOW)" (F:267). The minutes 12:34–12:41 show UX Δ+352 (36%). The −217 is the 12:30 flush bin. |
| W5 | "29 Sep: 11:30, 11:35, 12:25 become `short` bars" (F:189) | Its own threshold is "GoCharting lots ≥ 90% of Upstox" (F:21). 11:35 is 550 of 600 = **91.7%**, so it is complete by that rule. The rule misses the audit's truncated 11:35 bar (its last 36 s). |
| W6 | "12:05 high 22764: unfinished (b 93, s 0)" plus carried levels (F:98–99), and "ADHOORA LOW 22580" (F:257) | Consistent with its definition, but the definition marks **64 of 76** leg extremes "unfinished" across the six Tier-A days (`unfin.py`). A read that says "unfinished" 84% of the time does not discriminate. Each one becomes a carried level line, which is clutter. |
| W7 | "Afternoon box … POC 22684 at 68% of the range … P-shape, short-covering signature, consistent with OI −11.3k" (F:118) | 68% sits on the ⅔ boundary. With 5-point bins and the 22723 top the POC is at about 64% (D). The label flips on a one-point choice. It is then used to *confirm* the covering story that the Oct data overturns. |
| W8 | "Forming UP 11:06→12:01 … 52 pts/1,000 (pool p4) … heavy buying, little progress" (F:263), with the chip SHORT COVER ROKA (F:73) | It lumps the day's most efficient burst (11:06–11:14, 114–119 pts/1k on both tapes) with the grind (48–88), and calls the day's largest rally (+165) "absorbed". Oct over 11:15–12:01 shows +4.2k OI with price up: new Oct longs, not a capped move. |
| W9 | The base 09:42→10:07 is "DO TAPE ALAG → NO READ" after excluding **block bars** (F:50, F:259) | Excluding the whole 10:05 bin also throws away about +914 UX lots of non-block buying: the 10:07:50–10:08 frames as price ran 22599 → 22616. The dispute is manufactured by the exclusion method. Excluding the print itself leaves both tapes thin and the same sign (O R-10). |

**Checked and correct (credit where due):**
- B5 = 17.4 (it says 17.5).
- The option figures: 22600 PE −224,463 lots, 22800 CE −120,463, 22700 PE +45,448 over 13:30→15:29.
- No divergence at the 12:01 high on either tape.

---

## 2. Where the Fable design is BETTER than mine (and what I adopt)

| # | Fable | Why it beats mine | Adopt |
|---|---|---|---|
| B1 | δ **frozen at the open** from the pool (F:43) | My δ = 3·B(t) rose to 50 at 09:42 on the wide open, which made the morning cut late (base declared 11:02). Frozen at 3 × prior B (29.4), the base is declared **10:02** and the 22713–22748 top range shows (breakdown 12:27). 28 Sep is unchanged. Simpler and restart-proof. | **Yes** |
| B2 | Block **OI-step check**: "spread/roll or reporting artefact, not directional" (F:110–111) | The Oct file proves the 10:07 case. I had written "a position opened in one print" (O R-10). | **Yes**, with the candle-volume witness (§5) |
| B3 | Extension **heartbeat** `{tab_visible, ctx_alive, last_tick_ms}` (F:32) | Names the *cause* of a GoCharting death (discarded, orphaned or stalled), not only the fact. | **Yes**; I keep my Upstox-volume cross-check as the independent witness |
| B4 | **Sub-δ pullback named with its size**: "PULLBACK · −18 · seller nahi aaye" (F:140) | Her exact need, told while it happens. Mine only named a pullback once a counter-leg was confirmed. | **Yes** |
| B5 | P/A/E/C **computed in TapeMap**; the extension only draws (F:150, F:187) | Removes zoom and reload rebuilds at the root, and lets anytime start rebuild her marks. I left `board.js` in the page. | **Yes**, with a stronger gate (R4 below) |
| B6 | Options confirmation with concrete per-strike ΔOI and the synthetic forward (F:123–124) | Verified numbers; mine was thin (O R11 "weak"). | **Yes** |
| B7 | Regime test by **swapping the dump's expiry date** (F:287) | Proves the calendar is not a weekday. | **Yes** |
| B8 | Backfilled reads drawn **hollow** with a `.b` id (F:34) | Clearer than my "revision" text. | **Yes** |

---

## 3. Where the Fable design is RISKIER

| # | Risk | Evidence |
|---|---|---|
| R1 | **The fifth state rests on a cross-day yardstick.** "Absorbed" = eff < the pool's p25 (F:51, F:67). | The pool is n = 25 legs from 22–28 Sep: roll-week days, a regime the research warns about (D5). On **30 Sep (the first Oct day) the same-contract pool is empty**, so the key state has no yardstick exactly when a new contract starts. |
| R2 | **Close-gated rules.** Legs confirm on a 1-minute *close* (F:41); absorption runs need "closes below it" (F:85). | She said "i dont care about candle close". It is a small latency, but a visible breach of her standing rule. |
| R3 | **Divergence at every leg completion**, not only at auction structure (F:92). | Inside a box with persistent buying it fires repeatedly ("BULL DIV · UX" at 13:40 and 15:22, F:267, F:272), restating the absorption read as new chips. |
| R4 | **Porting her marks with a counts-only parity gate** (F:187: "counts per kind per day"). | Counts can match while individual marks move. She trusts these marks. The gate must be by **event id** (bar t, kind, price), and each difference must be shown to her. |
| R5 | **Outcome-reading in validation**: "for each completed leg, the next leg's direction and size are appended … The judge reads the pairs" (F:286). | That is scoring by eye, a back door to the backtest that house rule 2 forbids. |
| R6 | **The FLOW row text changes before the clock runs** (F:290). | Her signed rev 6 row changes wording on day 1. It needs her signature like any rule. |
| R7 | **Feed thresholds of 60/90 s** (F:31). | The band shows at 12:27:30, not 12:26:15. It is acceptable, but the heartbeat (B3) would allow 15 s. |
| R8 | **Carried levels multiply**: unfinished extremes (W6) plus "single prints … carried as levels" at 1-point rows (F:98). | At tick-level ladders, single-trade rows are common. Without a cap the Trade tab fills with lines. |

---

## 4. The three hardest questions Fable must answer before the judge

1. **The Oct data:** Oct OI +25.7k, price +69, spread 135 → 164, combined +14.9k, in the exact window you called "not new buying; not bullish". Your roll rule needs Oct delta, which the REST candles do not carry, and it only contemplates shorts rolling or closing. What does your reader print for 13:30–15:29 with the data that exists? And how does it tell the curve's positioning from the expiring contract's closing flow?
2. **Pivot attribution and the splice:** your bar-by-close-time attachment books the 09:35 and 12:30 selling bars to the next up legs (false ULTA FLOW; W4). Your volume-cross rule would move the leg engine to Oct at 09:20 on 29 Sep (W3). How are leg effort and contract identity kept honest at the one place a reader is judged: the turn?
3. **The yardstick for "absorbed":** on 30 Sep the same-contract pool is empty. On 29 Sep, 16 points of Sep's "missing progress" were convergence (Sep−spot 14 → −2). What is "absorbed" measured against on the first day of a contract? And how do you keep expiry convergence from being read as a passive seller?

---

## 5. My own corrections (changelog; applied as "Rev 2" in `4-design-opus.md`)

1. **Roll resolution rewritten without Oct delta.** It uses:
   - Oct's own price × OI table;
   - combined OI;
   - the Oct−Sep spread (or Oct−spot basis) as the roll-side witness.

   The 29 Sep afternoon now reads "Sep: covering, absorbed (closing flow). Oct: new longs +25.7k. Combined +14.9k: positions built long into October [I]." The retractions are listed in Rev 2.
2. **Expiry convergence.** The expiring contract's effort vs result is reported on spot-adjusted progress, with the convergence stated.
3. **Expiring-contract levels are checked in next-month terms.** 22723 Sep is about 22863 in Oct terms; Oct traded 22905.5 at 15:32, so the "ceiling" was Sep-only.
4. **Spread-leg witness.** Exchange candle volume vs `vtt` per minute. The 10:07 block is reclassified as a spread/roll print [I]. Adopted from B2.
5. **δ frozen at the open** (B1).
6. **Finished/unfinished follows the research's wording**, and is demoted to "two-way at the extreme" as the only drawn case. My earlier definition mislabelled 44 of 76 extremes "finished".
7. **Adopted from Fable:** B3, B4, B5 (with the id-level parity gate), B6, B7, B8.
8. **Self-score changes:** R3 is pass on Sep, partial on the curve (it needed Rev 2); R4 is partial → pass-able with the REST Oct feed; R7 is pass → partial.
