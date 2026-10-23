# Opus × Sonnet debate — 2026-10-09 (two rounds), the joint design

All numbers are Sonnet's measurements on its scratch engine. They come from 33 index-days (22 Sep – 8 Oct), are in-sample, cover one falling market, and are descriptive only: no outcomes and no rates of success.

## Settled
1. **Data first.**
   - **Strike window.** The chain is a fixed 17 strikes around the opening ATM all day (verified: 8 Oct NIFTY 22,150–22,950, close 22,232). Above/below lopsided ≥ 2:1 in 45% of 2,079 five-minute samples. A symmetric window changed the writer verdict in 17% of samples and in 25% of the TREND samples.
   - **Writing vs buying.** In CE-only windows, near-ATM OI build came mostly with IV rising in 467 of 755; PE-only in 271 of 579. That test is confounded by market-wide IV, so the fix is an IV/premium residual against the ATM-wide move.
   - **Smaller fixes.** Take day high/low from ticks, and print the basis live.
2. **Day read = THE READ (reuse, no third engine).** Words map to KHEL: TREND → RIDE full, LEAN → RIDE half, RANGE → FADE, WAIT → BAITHO.
   - **Port from Sonnet:** a displacement gate (TREND needs ≥ 0.6× the expected move to date from the open), no TREND before 10 min of OI flow, a PIN flag inside RANGE that allows selling only, "?" on partial data, and veto-fast/permit-slow timing (first ▼ on 8 Oct at 09:29 instead of 09:41, about +2 state changes a day).
   - **Keep from READ:** FLIP and QUIT.
   - The read's 5-minute exits never drive a trade fold.
3. **The read vetoes WHICH side, fast; location decides WHEN.** Her fade gate refused 23 of 26 fires on 8 Oct.
4. **Headline** = KHEL (RIDE ▲ / RIDE ▼ / FADE / BAITHO) + PREMIUM (moved ÷ IV-priced: kharido or becho) + SIZE (full or half). The six day words survive only as evidence subtitles.
5. **Entry = her zone.**
   - **FADE:** buy d2→d3, sell u2→u3, behind the fade gate.
   - **RIDE:** the first 1σ touch of the lane only, one entry per lane. If no agreeing 1-min delta arrives within 5 minutes, drop it. The FLOW light reads "pending" for those 5 minutes.
6. **Entry contract + fold board.** ZONE, FLOW, OI and VPIN, each at entry vs now. A reading must hold 3 minutes. Never a candle close.
7. **Event chips, not states.** First-stop (in TREND only, once per episode: median 1 per index-day, max 3, zero on 12 of 33), QUIT, DRIVE. PALAT is no longer a day word; its logic becomes the counter-side veto until VWAP is reclaimed for 3 minutes.
8. **Density.** One decision per column, in her words; every other row is on tap.
9. **Forward only.** Her blind calls, frozen constants, half size until the lights earn trust, no scores.

## Last disagreement (Opus conceded)
The question was whether to enter at the touch or wait for an agreeing 1-minute delta. In 94 of 117 first ±1σ touches inside an allowed side, the delta already agreed. For the other 23, the median wait was 2 minutes, at a median cost of 0.00σ (IQR −0.19 to +0.16σ, max 0.40σ). **Default:** touch plus no opposing 1-minute delta. Scale-in is optional and her call.

## Biggest risk
The OI writer read feeds every gate. If it is biased by window geometry, or by buying that looks like writing, every gate is biased. That is why it is build item 1.
