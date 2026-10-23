# RISKS — where this design can mislead Mary, and what it cannot know

## 0. Provenance (read first)
- **Clean room, with two leaks I did not cause.** I opened only the data paths and the CSV. But the harness had already placed (a) a one-line-per-topic memory index in my context and (b) `tapemap/CLAUDE.md` (injected by a hook after my first write under `tapemap/`). I did not open any file they point to and did not follow their instructions, but I saw their titles and rules. Where my design agrees with them (light theme, Hinglish, no price chart, no score), the brief says the same; discount any other "convergence" accordingly.
- Everything I wrote is in `fresh-take/`; scripts are in `fresh-take/scratch/`. I used a local headless Chrome only to screenshot my own `mockup.html`. No server, no git.

## 1. The curve-fit problem — stated against myself
- **One round of tuning on the same data.** After a first stability audit over the 12 sessions I changed: writers "one-sided" 25% → 40%; added a displacement gate (a quiet 102-pt drift day was called TREND ↑ for 31% of its minutes); scaled "range used" by √time (PIN had been called at 10:50 on a day that ranged 237 pts); rebuilt the flip flag (the first version fired most of the day); state-hold 5 → 10 min; open print = first tick (a −162-pt gap open read as −54); added "bounce"/"break" entries (retest-only qualified 1 of 271 minutes on 8 Oct). **The mockup frames are in-sample illustrations, not evidence.** Constants are frozen now; any change must carry a date and apply only forward.
- **The sample is one falling market.** NIFTY went 23,439 → 22,232 over the 12 sessions. TREND ↑ was 2.8% of minutes, TREND ↓ 15.4%; PIN 0.8%. The upside-trend rules and the PIN rule have effectively never been exercised. No gap-up, no event day, no budget/RBI day.
- **Constants (all round numbers, all arbitrary):** windows 30 min (location, OI) / 15 min (flow) / 45 min (crossings); bands "ready" 30 min after feed start; side-time 80%; dead zone 0.25σ; weak-side 40%; OI material 0.5% of side OI; flow material 3% of volume; displacement 0.6× expected-to-date; PIN range 0.6, within 0.5 strike, after 10:15; retest −0.3…0.8σ, bounce 0.4σ, break ≤ 0.1σ with moved ≥ 1.0; premium buy ≥ 0.8 / sell ≤ 0.6; clock 45/15 min; fold 3 min, 0.25σ, VPIN +0.03/+0.06; early lane 1.0× priced with delta agreeing; expected move = mean range of last 3 sessions × √(t/375).

## 2. Where the screen can mislead
1. **"Call/put writing" is an inference.** OI rising at a strike doesn't say whether the new contracts are sold or bought. My engine does **not** check the option's own premium change (OI↑ with premium↓ ≈ writing; OI↑ with premium↑ ≈ buying) — the chain has `ltp`, I just didn't use it. Mary's whole method leans on this read; it is the first thing to fix.
2. **Green means go — a score in disguise.** KARO / AADHA / RUKO are functions of lights. In frame C Sell CE shows OK with a **red premium light** (I made premium a preference, not a gate). Mary may read ticks as confidence. Hiding the numbers would be worse; keeping them is the mitigation.
3. **Stability costs lateness.** Held state needs 10 minutes; flow is 15 minutes from 5-minute bars. On 8 Oct the first leg of the 11:20 break (~100 pts) came back as "wait: place/flow"; the first OK was 11:32. This is the "wait until 09:45" disease in a smaller dose. The early lane rarely fires (1–3 of 33 index-days) so it doesn't cure it.
4. **PLACE accepts extension.** Frame G's half-size Buy CE at 13:11 was taken 1.6σ above VWAP because a 0.4σ bounce existed. The fold board limited it (FOLD displayed from 13:43 under the 3-minute rule, futures 58 points below entry; premium −₹41 by 13:46) but the entry rule is too generous. I did not fix it, to avoid a second tuning round.
5. **Unclear may hide where the money is.** The tool says SAAF NAHI for ~14% of minutes (median longest run 37 min, max 72). If Mary profits fading chop in exactly those minutes, the tool gives her nothing there.
6. **"Sabse saaf" ranks clarity, not profit.** It can point at the index that is already most extended.
7. **Flip flag is noisy** — it is raised in ~11% of minutes (median). It is shown as a soft note; if it ever becomes an alarm, Mary will learn to ignore it.
8. **Invented Hinglish** ("jhukaav", "palat", "saaf nahi") is mine, not Mary's. Density is high (6 + 5 + 4 rows). Test: show frames A, C, E, D cold; if Mary can't say in her own words what to do within ~10 seconds each, the screen fails regardless of how right the numbers are.

## 3. What the data cannot support
- **The first two minutes.** Recorder and chain start at ~09:17: no open print, VWAP off by up to ~10 pts at 09:20 (checked against Mary's broker export: ≤ ~3 pts of VWAP, ~1–4 pts of σ after 10:15).
- **7 Oct has no morning;** feed from 13:07. The tool shows "?" instead of inventing it (frame I). Anytime-start in production needs a backfill source; whether the broker API serves intraday option OI history, I have not verified.
- **`ux_*` bars are 5-minute, not 1-minute** (75 bars/day). Delta lags up to 5 minutes.
- **Chain window is fixed ±8 strikes around the opening ATM.** On 8 Oct NIFTY closed at 22,232 with the lowest recorded strike at 22,150 — on a big trend day the put walls fall off the table.
- **Basis is large and moves:** NIFTY 0–129 pts, BANKNIFTY 5–419, SENSEX −21…751 over the sessions, and 20–130 pts *within* a day (BANKNIFTY 30 Sep 293→419). A STRIKE converted to FUT with the live basis is ±that wobble. The SENSEX "near-month" feed may not even be the series its chain settles to; I can't tell.
- **Expiring contract:** after ~13:30 OI falls are position closing, not unwinding (NIFTY 6 Oct: put OI −604L, price flat/up), and ATM IV is unreliable (28% on 29 Sep) so the "moved ÷ priced" gauge is junk there.
- **VPIN here is my own approximation** (50 buckets of 1/300 of the previous day's volume) and NIFTY-only. At the two frame minutes it read 0.405→0.400 (D) and 0.443→0.481 (G); it decided nothing in either. Mary's own VPIN should replace it.
- **Fold board = my reading of "zone, order flow, OI, VPIN":** "zone gone or two others against, 3 min" is my guess at her rule. Two example trades; one flatters (D), one doesn't (G). No inference from either.

## 4. What it cannot know, ever
News and events; her position, P&L and intent; the broker's order book; who the counterparty is; whether OI is a hedge or a roll; options-level order flow; whether a print is one big player or many small ones.

## 5. Not done / not claimed
No accuracy, hit-rate, or edge was computed for any state, light, or entry — by design. The audit numbers in APPROACH.md (switches, unclear share) measure **stability**, not correctness. A state machine that is stable and wrong is still wrong; only forward days, judged against Mary's own blind calls, can say.
