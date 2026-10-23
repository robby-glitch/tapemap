# UI — one screen, five questions, in the order Mary asks them

`mockup.html` (1245×720, light, offline). The 11 buttons at the bottom replay **real recorded minutes**; every number on a frame uses only data up to that minute (including the day-strip, which stops at "now"). Frames come from 7 different sessions; Pre, A, B, C, D are 8 Oct, so treat those as one day.

## Design principle
The screen is a **reading order**, not a dashboard: *Which index → what kind of day → what to do → where → (in a trade) why I'm in and whether those reasons still hold.* Mary has a price chart on her broker; this screen never redraws it. It carries what the chart cannot: OI by side and by level, who is writing, flow, cheap-vs-rich, the state history, and her own entry reasons.

## What is on screen
1. **Top bar** — date/clock, phase chip (SHURU / SUBAH / DOPAHAR / CLOSE-OUT), expiry-today chip, minutes to 15:00, light legend, "sirf salaah · koi order nahi".
2. **Index strip** (3 cards: NIFTY / BANKNIFTY / SENSEX) — state word + arrow, since-when, CE-vs-PE writing bar, σ position, EXPIRY chip. The tool's pick carries "★ SABSE SAAF" (clearest, not "best"). Click a card to read it below. *Answers: which index.*
3. **Col 1 · Kaisa din** — the day type in one word (TREND ↓ / JHUKAAV / CHOP / PIN / PALAT? / DRIVE / SAAF NAHI), how long it has held, and six rows, each = one measured fact + one light: **Kahan** (vs VWAP, side-time), **Kaun likh raha** (CE vs PE, 30 min), **Flow** (15-min delta), **Futures OI vs price**, **Din ki chaal** (range used), **Option sasta/mehnga** (moved ÷ priced; before 10:15 it becomes **Drive** from the open). Bottom box: **what would change this read.** *Answers: pin/chop/trend, and why.*
4. **Col 2 · Kya karna hai** — banner (KARO / AADHA SIZE / RUKO), then only the live expressions among Buy CE · Sell PE · Buy PE · Sell CE, each with five lights (**jagah · OI · flow · premium · time**), strike/premium/lot value, and a one-line reason. Below: **what is missing** (named: "sellers wapas", "bounce ≥ 0.4σ") and, if a trade is legal, **the four fold reasons written out in advance.** *Answers: take or wait, buy or sell.*
   **In a trade** this column becomes **Trade mein**: position strip (strike, entry, premium now, points, ₹/lot), the **reasons I entered on**, a HOLD / WATCH / FOLD banner, and a four-row **fold board** (ZONE · FLOW · OI · VPIN, each "at entry → now") plus the first target.
5. **Col 3 · Kahan** — one ladder, **all levels converted to futures**, each with a tag **FUT** or **STRIKE** (spot-strike OI walls, converted with the live basis, printed in the banner: "FUT = SPOT +53"). Rows: VWAP, ±1σ/±2σ, day high/low, open print, yesterday's POC/VAH/VAL/HVN/LVN (dated), CE/PE walls, pin strike; distance in points and σ; "ABHI" row highlighted. Under it, the walls with OI, 30-min change and futures-equivalent. *Answers: where.*
6. **Din ka safar** — one colour strip per index of the state held at each minute, up to now only; red line at 15:00. Shows *when* the day changed and how long it was unclear.

## What Mary does with it
**At the open.** Pre-open frame: yesterday's value/OI walls, who expires, a blank for *her* event note, and a "kab kya pata chalega" timeline (09:17 / ~09:27 / ~09:47 / 10:15). At 09:20 (frame A) all three say SAAF NAHI and the screen says why in numbers ("OI flow ke liye 7 min aur"). She does nothing — or, if one index prints DRIVE (frame J: BANKNIFTY, 1.3× the 30-min priced move with delta behind it), she may take **half size** with the fold plan already written under it (delta flips / open print reclaimed 3 min). By ~09:47 (frame B) a lean appears; TREND needs the writers and the move.

**A clean move.** Frame C (8 Oct 11:32): glance at the strip (NIFTY ★, BANKNIFTY disagrees — noted), col 1 shows six ticks, col 2 shows KARO with Buy PE / Sell CE, and **premium** tells her which: options cheap → buy edge, Sell CE's premium light is red. She picks her strike, enters on her broker, taps the row to log it (the tool then stores the entry reasons). Nothing else changes for her.

**An unclear market.** Frames A, E, I. Banner says RUKO; col 1's last box says what would make it clear; col 2 lists what is missing in her words. One screen, one instruction. Frame E (5 Oct 10:30): NIFTY and SENSEX SAAF NAHI, BANKNIFTY CHOP — and the tool still refuses to name a side where the writers disagree. Frame I (7 Oct, feed started 13:07): lights go "?" and the day-type is capped; the tool does not estimate a morning it didn't see.

**In a trade.** Frames D and G. She reads col 2 only: the four lights against *her own* entry state. D (8 Oct 12:10, Sell CE): flow turned against but zone and OI intact → **WATCH**, hold. G (30 Sep 13:46, Buy CE at half size): zone slid, flow and OI flipped → **FOLD**. FOLD needs 3 minutes of the same reading — never a candle close.

## Language and legibility rules (Mary's, applied)
- Light theme only. Labels ≤ 6 words, Hinglish connectors, English trading nouns (VWAP, writing, flow).
- No symbol without its legend (top bar). Lights are **shape + colour**: ✓ saath · ~ aadha · ✕ ulta · ? pata nahi. "?" is *not* a zero and not a guess.
- Every level says FUT or STRIKE; the basis is on the card; there is never a bare number you can't place.
- No win rate, hit rate or confidence anywhere. Status words (KARO / AADHA / RUKO) are functions of visible lights; the lights show their numbers, so Mary can disagree with a specific one.
- Honest degradation is visible: JALDI chip (< 30 min of feed), ADHOORA DATA chip (late start), "badal raha: X" when the raw read differs from the held read.

## Deliberately absent
Price chart · P&L history · option-chain table · Greeks · news · order buttons · tabs · any "score". If a number does not change what Mary does in one of the four moments above, it is not here.
