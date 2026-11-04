# Working notes — Fable, 3 Nov 2026 option flow × OI study

Files here (all written by me; nothing outside this folder touched):

| file | what |
|---|---|
| `load.py` | loaders: scrip map, Dext per contract per minute, chain per minute (last snapshot in the minute), fut1m, VIX, Jarvis calls, messages |
| `study.py` | the per-strike table, the 3-min window WHO (`window`), the four groups (`sides`), the word (`word_of`, `held`), the export (`--json` → `day.json`); `python -I -X utf8 docs/optflow/fable/study.py [NIFTY|SENSEX] [3|5]` prints the read |
| `day.json` | the embedded data (926 KB): per index per minute spot / fut / fut OI / VIX / Jarvis word; per strike per minute OI, ltp+avg, 3-min dOI, delta, WHO code, BADA cell; cap / floor groups; the word; pushes; alerts; +15 hindsight |
| `mockup.tpl.html` + `make_mockup.py` | the page template and the embedder → `mockup.html` (953 KB, standalone, light, IIFE, no external files) |
| `REPORT.md` | the deliverable |

## Clean-room declaration
- I did NOT open `docs/optflow/mockups/`, `docs/optflow/replays/`, `optflow/map.html`, or any `*.html` under `docs/kahani/review/mockup/`.
- I did NOT read README "The reads behind it" (lines 137–189) before writing section (c). After writing (c) I still have not read it; the comparison in REPORT (c-end) is therefore owed to the next session (see "Open" below).
- **Accidental exposure:** my first `sed -n '1,120p' docs/optflow/README.md` printed lines 44–66, "How to read the Battlefield" (a strikes × time grid of 5-min blocks: red/green blocks, hollow = cover, grey = not writers, dots = biggest hit, spot line, CAP/FLOOR/LEAN pills). I stopped at the headings after that. My design is deliberately NOT a strikes × time heatmap: it is a live ladder at ONE minute with a time scrubber, the answer first, labels in words, and the last 30 min as a strip of words. The one thing both must share is "rows are strikes", which is the domain, not a design.

## Decisions I made (so the next session does not re-derive them)
1. **Units:** OI and volume in quantity, as the chain and Dext give them. Dext's day volume matched the chain's cumulative `vol` within 1.2 % on 5 contracts checked → same units, same source. L = lakh qty. NIFTY lot 75, SENSEX lot 20.
2. **The OI minute:** the chain's last snapshot inside the minute. OI changed in 291 of 319 minutes at 23700 CE, so 1-min OI is real, not a 3-min step. A window's dOI uses the last known OI at each end; OI older than 2 min at the window's end → `OI?` (never zero).
3. **The window:** her 3-min bar, rolling per minute in the export (window = (m−3, m]); the printed read uses aligned windows from 09:15. Everything at minute m uses minutes ≤ m.
4. **WHO (per strike per window):** dOI sign × aggressor sign. Aggressor = Dext delta (lifted offer − hit bid) with |delta| ≥ 0.2 × |dOI| [I]; else MIXED (posted both ways). A volume-based cut (|delta| ≥ 15 % of volume) called everything MIXED because ATM option |delta| is ~11 % of volume at the median: the OI change is the right yardstick.
   - +OI, sellers hitting → **WRITE** (likh rahe: writers pressing)
   - +OI, buyers lifting → **BUY** (kharid rahe: buyers in a hurry, writers posting)
   - −OI, buyers lifting → **COVER** (bhaag rahe: writers buying back)
   - −OI, sellers hitting → **DUMP** (nikal rahe: option longs leaving)
5. **"Moved" floor [I]:** NIFTY 1.5L qty (2,000 lots) per strike per 3 min; groups 2×. SENSEX 2,500 qty (125 lots): its ATM option volume was ~1/65 of NIFTY's on 3 Nov (measured), rounded to a sayable number. BADA cell [I]: one price in one minute ≥ 5L qty NIFTY (6,667 lots) / 8,000 qty SENSEX (400 lots).
6. **Groups:** CAP = CE at/above spot, FLOOR = PE at/below spot, ITM CE = CE below spot, ITM PE = PE above spot (yesterday's writers who are now under water).
7. **The word:** score cap COVER +2 / BUY +1 / DUMP −1 / WRITE −2, floor WRITE +2 / DUMP +1 / BUY −1 / COVER −2. |S| ≥ 3 FUEL; |S| = 2 from one side named by that side (LID / FLOOR UP / LID BREAKING / FLOOR BREAKING); |S| = 1 BUYERS; 0 → PIN (both WRITE) / SQUEEZE / BUYERS OUT / QUIET. The said lean needs 2 consecutive 3-min closes (Jarvis's ACT_CLOSES); the said word is the latest close's word of that lean.
8. **The trapped gauge:** OI built today ≥ 4 × the floor, and the chain's day-VWAP (`avg`) vs ltp: writers under water at ltp ≥ 1.25 × avg; buyers at ltp ≤ 0.75 × avg. (Aggressive-buy VWAP vs aggressive-sell VWAP from Dext were within 0.5 of each other at every strike, so they do not separate the two sides' cost; the day VWAP + OI built does.)

## Measured on 3 Nov (NIFTY, [M])
- Fut 23,525 → 23,780 (+255). Day L 23,522 at 09:15, day H 23,800 at 13:40. Fut OI 201.5k → 192.0k lots (−9,500, short-covering day). VIX 15.51 → 16.22 (13:17) → 15.66. Expiry day for the 03 NOV weeklies.
- Jarvis NIFTY: 304 rows, 15 word changes, lean ▲ from 09:18, 0 flips, PALAT? 0. SENSEX: 304 rows, 14 changes, never TREND. Gaps 14:22–14:42, 14:42–15:20 (A214).
- Flow lean (3-min closes, 125): agrees ▲ with Jarvis 56, ▼ vs Jarvis ▲ 42, flat 26. Flow lean sign flips: 8.
- Pushes (24): OI answer × flow WHO at the answer minute: TOOT+COVER 4, TOOT+DUMP 3, TOOT+QUIET 1, TIKI+WRITE 2, TIKI+BUY 1, TIKI+MIXED 1, NAHI+WRITE 5, NAHI+BUY 3, NAHI+COVER 1, NAHI+MIXED 1, NAHI+QUIET 1, NAHI+DUMP 1. `who` on the handshake was null on 22 of 24.
- SELL setup alerts (7 distinct): with cap WRITE at the alert, 3 of 4 were lower at +30 min; with cap BUY/QUIET/MIXED, 0 of 3.

## Round 2 (same evening)
- README "The reads behind it" read AFTER (c); the comparison is REPORT R2.1. Design clean room still held (no mockups / replays / map.html opened).
- Corrections: `study.py main()` printed bars one minute late vs her grid (fixed: bars 09:15–09:17 …); the export was already on her grid. (a)-2, (a)-6, (b)-3/4/5/6, (c) labels and D3 corrected in REPORT R2.2; the veto is withdrawn (no word change; both forms forward-logged).
- OI cadence: the exchange's OI changes every ~63 s; a one-minute shift moves 26 % of per-strike labels (mostly across the QUIET floor), none of the key-moment group words. `firm` = same label under both alignments (624 of 972), exported and drawn faint when not firm.
- Aggressor check against the chain's 11-s bid/ask: 1,112 agree / 885 disagree / 1,261 undecided — the proxy cannot carry the kill check; needs ticks.
- `mockup-v2.html` (from `mockup-v2.tpl.html`, derived by `patch_v2.py`): buyer / seller cells in §1h terms, 9 strikes, firm labels, 12 px minimum, no %, "Float 440" mode. v1 kept.

## Round 3 (2 Nov, same evening)
- 2 Nov fetched in full by the coordinator (68/68 contracts). `load.CUR["day"]` switches the day; `study.py --json` writes `day.json` (3 Nov, v1's shape) and `days.json` (both days, v2). `secondlook.py` counts every Round-2 survivor on each day as two columns.
- Held: OI cadence 63 s, FIRM ~64 %, the flow lean 8× noisier than Jarvis's, the mirror (DOWN FUEL = cap WRITE/DUMP + floor COVER with puts lifted) in the 12:53–13:14 leg, the first-hour unanimity condition (silent at W2 A2). Did not hold: TOOT-by-DUMP (2 of 4 vs COVER 2 of 8), the fade stamp (1 of 4 vs 5 of 9). Not testable: NAHI+WRITE/BUY, PIN (1 DTE), "writers return".
- Corrections carried: 3 Nov TOOT-by-DUMP is 1 of 3 with the push (14:24's sign); the fade count at the last close ≤ alert is 4 of 4 / 0 of 3.
- v2: day switch, arrows only on FUEL words, held() first word at a close (`patch_r3.py` after `patch_v2.py`).

## Round 4 (00:25–01:30, 4 Nov; no server touched)
- `round4.py` (+ `round4_out.txt`): pullback anatomy (2 Nov pause log; 3 Nov call-log states), the signal × flow matrix (trigger_log zone3 arms, msg-stream fades + fronts gate, handshake speed, speed / effort / VPIN at pause starts, Sides × flow × f15), the option-implied delta (Σ (lifted − hit) × chain delta / 75) vs the futures' Dext delta (61471), the writer-gamma profile. Reuses `docs/optflow/brainstorm/strike_bands.py`.
- Findings: healthy pullback = defending WRITE, ITM C/D, implied delta with the leg, ATM premium > its VWAP; the one reversal (2 Nov 10:55) = ITM W, implied against, premium < VWAP, VPIN p0.13; the pin (3 Nov 13:43) = cap WRITE 12 of 17. Options do not lead the futures (lag-0 corr, futures first at both 2 Nov flips); options are the fuel (×330–620 in delta volume), not the clock. A218's "at the band → stall" 3 of 4, "mid-band → continues" 1 of 4. Open-drive SELL arms stopped 7 of 8, all LEGAL by §1d.

## Round 5 (01:20–02:30, 4 Nov; no server touched)
- Five days (28, 29, 30 Oct, 2, 3 Nov). `load.fut()` now falls back to Dext's futures OHLC/footprint when fut1m is missing (28 Oct OHLC+OI; 29 Oct = mid of h/l, said in FUT_SRC); missing jarvis/msg/vix logs return empty. `study.py --json` exports the five days (NIFTY; SENSEX on 2–3 Nov) into `days.json` (4.3 MB; mockup-v2 NOT rebuilt — it still embeds the 2-day file it was built with).
- `round5.py` (+ `round5_out.txt`): events fixed before outcomes (3 largest 15-min moves a day), mechanism by futures OI + the group words, lead-in pieces at every close, false alarms per piece and for the conjunction. Result: short covering = 8 of 15 fastest moves; the lead-in conjunction (trapped · stalled · near) fired 3 times in 1,250 closes and preceded none; the first cover preceded 4 of 13 by 3–12 min; inside the move the cascade is near-simultaneous (5 of 8) and the wall migrates 1–3 steps (4 of 8). Design: SQUEEZE ON as a state stamp with a pre-registration text, no forecast word.

## Round 6 scale (fixed before counting; the market was open, no server touched)
- Option row for `prints.rebin`: 1 % of the bar's close premium, rounded to the 0.05 tick, floor 0.05 — a ₹80 option in ₹0.80 rows, a ₹8 one in ₹0.10: ten rows to a "point", as the futures ladder gives.
- Imbalance unit: `IMB_MIN_LOTS` 5 is read as 5 × 7,500 qty = 37,500 qty (500 lots) at one row — a tenth of a wall move (OI_MOVE 1.5L); `IMB_RATIO` 3 and `STACK_RUN` 3 unchanged.
- Big cells three ways: qty ≥ 5L (as before); ₹ ≥ 2 crore of premium at one cell (5L × ₹40, an ATM-sized print); delta-lots ≥ 2,000 (qty × |chain delta| / 75, the size of a wall move in index terms). `rank.py` BADA (p90 of the futures reference) not transferable, not used.
- Bars: her 3-min grid, per-price cells merged over the bar, o/c = chain ltp at the previous/this close, h/l from Dext. `round6.py`, output `round6_out.txt`; REPORT R6.

## Round 7 result + data note
- Today's 09:17 scrip-master download dropped the expired 03 NOV contracts; `load.recover_map(day)` rebuilds file → strike by matching each Dext file's 3-min delta at her closes to `days.json`'s `dl` (≥ 20 exact closes), cached in `scrip_recovered.json` (40/43/41/32/25 contracts). `load.dext` uses it automatically when the scrip master lacks the expiry. days.json must not be regenerated without the mapping (chicken-and-egg): keep `scrip_recovered.json`.
- ABSORPTION at the strike's own band held more than bare touches on 4 of 5 days (REPORT R7.1); IGNITION coincident with the first cover (3 of 8) or after (2), never before; the 10:35 climax was missed by the fixed CLIMAX form (AT u2, not beyond u3) — noted, not retuned; the 13:17 23,700 CE break read CLIMAX + IGNITION with the 23,700 PE at its own d2 and writers pressing.

## Open
- The play speed and the 9 / 5-strike heights are guesses; her word.
- SENSEX: its own option flow read here; §1q unchanged, hers to sign.
- Expiry afternoons: the bridge and the chain recorder would need the next expiry from 13:00 (R2.5 v); hers.
- The per-premium "wall" read (README's 80 wall) is a real gap in my design: a chip per strike from Dext's price cells.
