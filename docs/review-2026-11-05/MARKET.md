# 5 Nov 2026 (Thu): the tape, from raw data only

Written 15:35–15:58 IST, after the close. **Independent read.** No engine verdicts were opened: nothing from jarvis, calls, read, decode, grade, hold, messages or raftaar, no card/frame API, no NOTEPAD rows about today.

- [M] = measured from the files listed at the end. [I] = my inference as a trader.
- Lots: NIFTY 65 (`v2feed.LOTS`). OI is in L = lakh of qty, her unit.
- Levels are tagged **f** (futures) or **s** (spot). The basis was +14 at 09:16, +65 at the 13:48 high and +38 at the close [M].

---

## 0. Data health (read before anything else)

| Source | State |
|---|---|
| NIFTY fut 1-min (Upstox `fut1m`) | full, 09:15–15:30 [M] |
| NIFTY fut footprint (Dext `NSE-61471`, 1-min with price cells) | full, 378 min, 09:15–15:32 [M] |
| NIFTY chain (`chain_NIFTY`) | 1,892 snaps, ~12 s apart. **The strike window was fixed all day at 23950–24750** [M]. At the close the ATM was 24550, so ATM +7 (24900) was not recorded: 24800–24900 CE writers after 13:30 are unread. |
| SENSEX chain | **The window was fixed at 77300–78900.** Spot crossed 78900 at about 12:30 and closed at 79310. **From about 13:00, every SENSEX strike at or above spot is unrecorded** [M]. The second half's SENSEX call writers cannot be read from this file. |
| Prev-day base | 4 Nov's last NIFTY snap covers only 23550–24350. OI change vs yesterday exists only for strikes ≤ 24350. Higher strikes use today's 09:16 as base [M]. |
| SENSEX futures | thin (240–1,080 qty per min). Not used for flow (§1q). SENSEX is read on NIFTY flow + SENSEX OI. |

---

## 1. NIFTY: the day in chapters

**Frame.**
- 4 Nov fut: O 23712, L 23700.5 at 09:15, H 23988 at 14:49, C 23970. That was a trend-up day [M].
- Today fut: **O 24320 (gap +350 f; +380 s), H 24641.6 at 13:48, L 24311 at 09:15, last 24575** [M].
- Spot: O 24340.7, L 24309.8 at 09:32:56, H 24576.5 at 13:48:13, last 24536.6 [M].
- Fut OI fell from 134.8 L to 128.5 L (−9,750 lots on the day; −14,966 lots vs 4 Nov close) while price rose 255 f from the open [M]. **The whole day was a short-covering rally**, not fresh longs [M].
- Session VWAP (3-min hlc3 on fut, [I] approximation of her bands): price sat at or above **u2** from 09:36 to 14:15 [M]. In her frame this was a one-sided trend day; the u2 "sell zone" was a trap all day [I].
- VIX 14.59 → 15.2 (09:30) → 15.33 (13:00) → **15.77 (14:30)** → 15.69. VIX rose with price: calls were bid [M].

| Chapter | Time | What happened (numbers [M]) |
|---|---|---|
| Open | 09:15–09:30 | Gap +350 f. Open 5-min bar: delta **+1,160 lots (11× the 5-min median of 106)**, fut OI −3,406 lots (shorts covering the gap). Put writers flooded in: PE ±7 **+103 L, 09:20 → 09:30** (24300 PE 2.6 → 59 L; 24000 PE 27 → 42 L). Call writers wrote 24300/24350/24400 above (CE 24300 51 → 81 L by 09:36). |
| First dip | 09:30–09:35 | Fut 24380 → 24330; spot day low 24309.8 at 09:32:56. Delta −719 (6.8×). OI −2,310 (longs unwinding, not new shorts). Fut touched d2 (24338 f). PE writers kept adding (+27 L). |
| Open drive | 09:36–09:55 | Fut 24347 → **24470** (09:55); spot 24325 → 24439.8 (09:54). 1-min delta +577 at 09:40 (**14.8×, the day's biggest minute**). A 748-lot buy cell at 24400 f (09:40; 93 % one-sided; only 17 % of the bar, so not BADA). Writers: CE cover + PE add for 4 slots running (PE +122 L in 20 min). |
| Morning top | 09:46–09:55 | New highs on falling CVD (+2,113 at 09:46 → +1,777 at 09:55): a divergence. Fut at u2. |
| Pullback | 09:55–10:12 | Fut 24470 → 24384.5 (−86); spot to 24376. Delta −196 / −217 / −363. Writers flipped: **PE cover + CE add = fuel DOWN, 10:00–10:10** (CE +30 L). |
| Dead zone | 10:15–11:25 | Fut 24384–24441, a 57-pt box. Volume 194–880 lots per 5 min (the open did 11,030). Writers flat; both add 09:50–10:50 (pin). Quiet, correctly. |
| Step up | 11:30–11:45 | Fut 24441 → 24472 (11:36). CE ±7 **−32.8 L in 11:30–11:35**. **BADA BUYER 419 lots at 24460 f, bar 11:40–11:45** (70× median cell; the only BADA of the day). Fut OI +93 / +284 (fresh longs). Capped by **CE 24500 = 108 L, the day's biggest wall**. |
| Grind | 11:45–12:59 | Fut 24440–24494, creeping up. PE 24400 kept building (70.7 → 106.5 L by 13:00): **the floor moved from 24300 to 24400 s**. CE 24500 still 101.6 L. A 100-pt writers' box, 24400–24500 s. |
| **Second half: the break** | 13:00–13:02 | Fut through 24500 f (13:00 H 24500, 13:01 24511). 1-min delta +285, then **+411 (10.5×)**. The 5-min bar did +723 (6.9×). CE 24400 writers ran (87.3 → 75.8 L in 6 min). Spot 24452: the 24500 s strike was not yet crossed. |
| Fuel confirms | 13:10–13:25 | CE cover + PE add for 3 slots (CE −44 L, PE +32 L). PE 24500 43.8 → 57.2 L: the floor moved up to 24500 s. Spot 24463 → 24489. |
| **THE LEG** | 13:30–13:50 | Fut 24531 → **24641.6 (13:48)**; spot 24490 → **24576.5 (13:48:13)**. Call writers across ±7 covered **−121 L in 30 min** (−35.6 L in 13:35–13:40, −40.0 L in 13:45–13:50), the day's biggest writer move. **Spot crossed 24500 at 13:36. CE 24500 went 100.6 → 79.5 L: the morning's biggest wall broke.** CE 24400 went 61.7 → 48.4 L. PE 24500 60.6 → 81.0 L and PE 24550 6.4 → 19.4 L: the floor followed price. Fut OI −1,386 lots in the 13:45 bar (shorts covering). 1-min delta +461 at 13:42 (11.8×). CE 24500 premium 131 → 209. |
| Top / pause | 13:48–14:14 | Fut 24585–24629, no new high. Writers both add 13:50–14:00 (range). **CE 24600 held (59.7 → 61.4 L); spot never reached 24600 (max 24576.5).** Delta flat to negative. |
| Pullback | 14:15–14:24 | Fut 24614 → 24551 (−63); spot 24558 → **24501.3 (14:24)**. Delta −222 / −273 / −366 (2.1× / 2.6× / 3.5×). Fut OI +406 / +348 / +180 (fresh shorts). PE writers covered (−20.7 L in 14:20–14:25; PE 24500 87.4 → 79.7 L). CE +13.8 L (14:25–14:30): **fuel DOWN, briefly**. |
| Floor holds | 14:24–14:36 | Spot held 24500 s: the broken CE wall became the floor. Fut +45 in the 14:30 bar with OI **−1,599 lots** (shorts covering). Spot 24517 → 24551.7 by 14:36. CE 24500 went 153 → 187. |
| Late distribution | 14:45–15:00 | Delta −233 / −299 / −218 (2.2× / 2.8× / 2.1×). OI +355 / +619 / +390 (fresh shorts). Price only −14 (24607 → 24593 f), so sellers were absorbed. CVD fell from +4,274 to +3,524 (divergence). The cap pressed down: CE 24600 76.4 L (14:55), CE 24550 47.4 L (14:52). **SENSEX made a new high at 14:52; NIFTY did not.** |
| Close | 15:00–15:30 | Fut 24571–24610, last 24575. Writers covered on both sides (CE −42 L, PE −61 L over ±7): squaring before the close, not direction. After her 15:00 cut-off. |

**Range:**
- fut 330.6 (24311 → 24641.6); spot 266.7 (24309.8 → 24576.5) [M].
- Morning leg +123 f. Afternoon leg 24494 → 24641.6 = **+148 f in 48 min (13:00–13:48)** [M].

**What started the second half:**
- Three things landed together at 13:00 [M]:
  - futures crossed 24500 f with a 10.5× delta minute;
  - the CE 24400 / 24500 writers started covering;
  - put writers moved their floor up to 24500.
- The structure had been building since 12:00 (PE 24400 at 106 L) [I]. Writers had already turned "CE cover + PE add" at 12:20–13:00 (CE −20 L, PE +32 L), so 13:00 was the trigger, not a surprise [M/I].

---

## 2. NIFTY writers by strike (ATM ±7 as far as the window allows)

**CE (call writers):**

| Strike (s) | Built | Peak | Close | What happened [M] |
|---|---|---|---|---|
| 24000–24250 | carried from 4 Nov | 82.5 / 48.6 / 62.9 L at 09:16 | −63 / −31 / −44 L | Yesterday's call writers, deep ITM after the gap. **Trapped overnight**; covered all day. |
| 24300 | 09:16–09:36 (+38 L) | 88.2 L at 09:36 | 32.7 L (−55.5) | **Trapped.** Wrote the open, under water from 09:40; most of the cover came 13:00–14:00 (58 → 40 L). |
| 24350 | 09:16–11:09 | 65.9 L at 11:09 | 18.5 L (−47.4) | **Trapped** by the 11:30 step and the 13:00 break. |
| 24400 | 09:16–11:27 (+71 L) | **107.9 L at 11:27** | 34.7 L (−73.2) | **The day's biggest trapped book.** Covering ran 12:30 → 14:00 (93.6 → 46.1 L); fastest 13:00–13:30 (−23.6 L). |
| 24450 | to 12:47 | 47.7 L at 12:47 | 17.8 L (−29.9) | Trapped in the leg (45.9 → 22.2 L, 13:00 → 14:00). |
| **24500** | open (93.5 L) → 11:18 | **110.4 L at 11:18** | 65.3 L (−45.2) | **The wall that broke.** Held 11:18–13:34 (≥ 96 L). Spot crossed at 13:36; 100.6 → 79.5 L by 13:50. Partly rebuilt to 84.3 L by 15:00 once spot sat above it. |
| 24550 | 14:00–14:52 | 47.4 L at 14:52 | 42.1 L | **New cap written after the high** (29 → 47 L). |
| **24600** | all day | 76.4 L at 14:55 | 67.7 L | **The wall that held.** Spot never touched it; writers added +15 L after 13:48. |
| 24650–24750 | flat | — | — | 24700 at ~61 L all day; a far cap. |

**PE (put writers): the floor migrated up all day** [M]:

| Time | Floor (biggest PE at or below spot) |
|---|---|
| 09:30 | 24300 = 59 L |
| 10:00 | 24300 = 88 L |
| 13:00 | 24400 = 106.5 L |
| 14:03 | 24500 = 87.7 L |
| 14:58 | 24550 = 38.2 L |

- Put writers built **+280 L across ±7 by 10:00** and +498 L at the peak (14:00) [M]. They stayed on the right side all day. The closest calls were 10:44 (spot 24347 vs the 24350 PE) and 14:24 (spot 24501.3 vs the 24500 PE) [M].
- The one scare: **14:20–14:30, PE 24500 87.4 → 75.0 L and PE 24400 104.9 → 95.5 L** as spot hit 24501.3. The floor held [M].

**The 2×2 by half-hour (±7):**

| Half-hour | State |
|---|---|
| 09:20–09:50 | PE add (floor) |
| 09:50–10:50 | both add (pin) |
| 10:50–11:20 | flat |
| 11:20–11:50 | **fuel UP** |
| 11:50–12:20 | flat |
| 12:20–12:50 | PE add |
| 12:50–13:20 | **fuel UP** (CE −67 L / PE +39 L) |
| 13:20–13:50 | **fuel UP** (CE −121 L / PE +44 L) |
| 13:50–14:20 | PE add |
| 14:20–14:50 | **fuel DOWN** (CE +19 L / PE −39 L) |
| 14:50–15:25 | both cover (squaring) |

**PCR in the window** (change only): 0.44 (09:30) → 0.91 (13:00) → **1.36 (14:00)** → 1.21 (15:29) [M].

---

## 3. NIFTY order flow (Dext footprint, futures)

**CVD (lots), with the moves that matter [M]:**

| Time | CVD | Note |
|---|---|---|
| 09:15 | 0 | |
| 09:30 | +1,047 | |
| 09:34 | +328 | the dip |
| 09:46 | **+2,113** | morning peak |
| 10:14 | +1,163 | pullback |
| 11:44 | +2,083 | |
| 12:59 | +2,686 | |
| **13:48** | **+5,301** | day peak |
| 14:29 | +4,140 | |
| 14:46 | +4,250 | |
| 15:00 | +3,524 | |
| 15:30 | +3,022 | |

**Divergences [M]:**
- **09:46–09:55: price made 5 new highs while CVD fell from +2,113 to +1,777.** The top came at 09:55, then −86 f.
- 13:30–13:48: CVD rose with price at every new high (+4,103 → +5,301). No divergence at the day high: the high came from writers stopping (both add at 13:50) and from the CE 24600 cap, not from a CVD failure [M/I].
- **14:45–15:00: CVD fell from +4,274 to +3,524 while price held ~24595–24607 f.** Sellers were absorbed; it led into the close's −30 f drift.

**Big minutes** (|1-min delta| ≥ 3× the median of 39 lots):
- 09:17 +509 (13.1×)
- 09:40 **+577 (14.8×)**
- 09:31 −336 (8.6×)
- 10:19 −348 (8.9×)
- 11:40 +401 (10.3×)
- **13:01 +411 (10.5×)**
- **13:42 +461 (11.8×)**
- 14:46 +242 (6.2×)
- No sell minute after 10:19 reached 6× [M].

**BADA PRINT** (her decoder E1 rule, as written in `ui-v2/public/validate2/engine.js` lines 711–727):
- Rule: per closed 5-min bar, the largest one-price cell with one side ≥ 50× the session's median cell, ≥ 25 % of the bar and ≥ 80 % one-sided, after 6 warm-up bars.
- Applied to the Dext footprint, it fired once: **11:40–11:45, BADA BUYER 419 lots at 24460 f (70× median cell, 50 % of the bar)** [M].
- The Upstox tick ladder (`ux_NIFTY`) gives the same single print (bar 11:40, 24460 f, 135× median cell) [M].
- Near-misses that failed only the 25 %-of-bar test:
  - 09:40 at 24400 f: 748-lot buyer (93 % one-sided);
  - 13:40 at 24600 f: 388-lot buyer;
  - 13:00 at 24500 f: 263-lot buyer (96 % one-sided). This is the break print at the round number [M].

**Futures OI quadrants (15-min) [M]:**
- Short cover: 09:15–10:00, 13:15–14:00, 14:30–14:45.
- Fresh shorts: 14:15–14:30 and 14:45–15:00 (+934 and +917 lots).
- Fresh longs only at 11:15–11:45 and 13:00–13:15.
- **The rally was fuelled by shorts leaving, not longs arriving** [M]. The two fresh-short pockets after 14:15 were the only bearish OI of the day [M].

---

## 4. THE BIG MOMENTS (yardstick)

Prices are futures (f) unless tagged s. Premiums are the NIFTY 10-Nov weekly (DTE 3) from the chain [M]. "Action" is my trader call [I], made with her 15:00 cut-off.

| # | Time (IST) | Direction | What happened (numbers [M]) | Action [I] |
|---|---|---|---|---|
| 1 | **09:15–09:20** | ▲ gap | Gap +350 f / +380 s over 4 Nov's close (23970 f). Open bar delta +1,160 lots (11×), fut OI −3,406 lots (short cover). PE writers +68 L in 09:20–09:25. | Don't chase the gap. Sellers: **sell PE** (writers are writing puts). Buyers wait for the first dip. |
| 2 | **09:30–09:35** | ▲ (dip to buy) | Fut 24380 → 24330 at d2 (24338 f); spot low 24309.8 at 09:32:56 (day low). Delta −719 (6.8×) but OI −2,310 lots (long unwind, not shorts). PE writers still adding (+27 L; PE 24300 at 59 L). | **Buy CE / sell PE 24300.** d2 touch with put writers adding. CE 24350 143 (09:30) → 172 (10:00). |
| 3 | **09:36–09:55** | ▲ open drive | Fut 24347 → 24470 (+123); spot to 24439.8. 1-min delta +577 at 09:40 (14.8×). CE cover + PE add 4 slots running (PE +122 L). | Hold CE. |
| 4 | **09:46–10:12** | ▼ top, then pullback | 5 new highs on falling CVD (+2,113 → +1,777) at u2. Then PE cover + CE add (fuel DOWN, 10:00–10:10); fut −86 to 24384.5 (10:12). | **Book CE at 09:50–09:55.** A PE scalp is legal but small (−86 f). Sellers: sell CE 24500 (108 L cap). |
| 5 | 10:15–11:25 | — | 57-pt box, volume 194–880 lots per 5 min, writers flat. | **Stay out.** Quiet was correct here. |
| 6 | **11:30–11:45** | ▲ step | Fut 24441 → 24472. CE ±7 −32.8 L (11:30–11:35). **BADA BUYER 419 lots at 24460 f (11:40–11:45)**, the only BADA of the day. Fresh longs (+377 lots OI). Capped by CE 24500 (108 L). | Small CE or **sell PE 24400** (floor building 70.7 → 106.5 L by 13:00). Target is the 24500 wall, not beyond. |
| 7 | **13:00–13:02** | ▲ **SECOND-HALF START** | Fut breaks 24500 f; 1-min delta +411 (10.5×), 5-min +723 (6.9×). CE 24400 writers −11.5 L in 6 min; a 263-lot buy cell at 24500 f (96 % one-sided). Had been building since 12:20 (CE −20 L / PE +32 L). | **Buy CE** (24500 CE 112) / **sell PE 24400–24450**. This was the alert the screen needed. |
| 8 | 13:10–13:25 | ▲ confirm | CE cover + PE add 3 slots running (CE −44 L / PE +32 L). PE 24500 43.8 → 57.2 L: the floor moves to 24500 s. | Add / hold CE. Sellers roll the PE up to 24500. |
| 9 | **13:30–13:50** | ▲ **THE LEG** | Fut 24531 → **24641.6 at 13:48**; spot 24490 → 24576.5. **CE writers −121 L in 30 min.** Spot crossed 24500 at 13:36; **CE 24500 wall broke** (100.6 → 79.5 L). Fut OI −1,386 lots (13:45 bar). 1-min delta +461 (11.8×) at 13:42. VIX 15.43 → 15.73. CE 24500 131 → 209. | Hold CE; trail. **Anyone short CE 24400 / 24500: exit now.** This was the loudest moment of the day. |
| 10 | **13:48–14:14** | ■ top / pause | No new high after 13:48. Writers both add (13:50–14:00); **CE 24600 holds** (spot max 24576.5); delta flat to negative. | **Book CE** (24500 CE ~205 at 13:50). Sellers: **sell CE 24600**. |
| 11 | **14:15–14:24** | ▼ pullback | Fut 24614 → 24551 (−63); spot to 24501.3 (14:24). Delta −222 / −273 / −366 (to 3.5×). Fresh shorts +934 lots. PE 24500 writers −7.7 L; CE +13.8 L (fuel DOWN). | Trail or exit CE. A nimble PE scalp (24500 PE 126 → 146). No new longs until the floor answers. |
| 12 | **14:24–14:36** | ▲ floor held | Spot held 24500 s (low 24501.3); the old CE wall is now the floor. Fut +45 in the 14:30 bar with OI **−1,599 lots** (short cover). | **Buy CE on the retest** (24500 CE 153 at 14:24 → 187 at 14:36) / **sell PE 24500**. Out by 15:00. |
| 13 | **14:45–15:00** | ▼ distribution | Delta −233 / −299 / −218 (2.1–2.8×) with OI +355 / +619 / +390 (fresh shorts) while price held ~24595 f. CVD −750. CE 24600 to 76.4 L, CE 24550 to 47.4 L. **SENSEX new high 14:52, NIFTY none.** | **Close all longs.** No new trade (her 15:00 rule). |
| 14 | 15:00–15:25 | — | Both sides cover (CE −42 L, PE −61 L), spot −12. | After 15:00: none. |

---

## 5. SENSEX (spot + SENSEX OI, NIFTY flow)

**The day [M]:**
- Prev close 77301.4. **Open 78740.2: gap +1,439 (+1.86 %, vs NIFTY +1.59 %).**
- Low 78553.5 at 09:32:52. High **79463.8 at 14:52:13**. Last 79310 (15:29). Range 910.
- **Today was SENSEX expiry (0 DTE).** ATM IV ran from 0.29 to 0.99 / 1.25 into the close, and OTM PE 78500–78900 went to 0.2–0.3 [M].

**Agreement with NIFTY [M]:**
- Same-minute low (09:32:52 vs 09:32:56).
- Same morning top (78992.3 at 09:55:18 vs 09:54:08).
- Same dead box (10:15–12:00, 78640–78881).
- Same writer turn: 11:20–12:50 CE cover + PE add (fuel UP) on SENSEX vs 11:20–11:50 on NIFTY.
- Same leg: SENSEX 78981 (12:50) → 79434 (13:50), +453; NIFTY's leg was 13:00–13:48.

**SENSEX led** the second half by about 30 min [M]:
- Spot crossed 78900, its biggest CE strike, at about 12:25–12:40. NIFTY broke its 24500 s wall only at 13:36.
- **SENSEX CE writers broke first:** CE 78800 went 55.0 L (11:31) → 17.4 L (13:30); CE 78900 went 51.8 L (12:19) → 22.9 L (13:30) → 14.1 L (14:00).

**Disagreement [M]:**
- **14:52: SENSEX makes a new high at 79463.8; NIFTY spot does not** (24565 vs 24576.5 at 13:48).
- In the 14:20–14:30 dip, SENSEX gave −180 (79434 → ~79255) while NIFTY spot hit its 24500 floor.

**Expiry convexity (0DTE CE) [M]:**
- CE 78900: 153.7 at 12:00 → 223 at 13:00 → **531.5 at 14:00 → 552 at 15:00**.
- CE 78800: 293 at 13:00 → 649 at 15:00.
- **The day's biggest premium move on either index sat in SENSEX 0DTE calls, 13:00–14:00.**

**SENSEX big moments [M → action I]:**

| Time | Direction | What happened | Action |
|---|---|---|---|
| 09:32 | ▲ | Low; PE writers +178 L across the window in the first 35 min. | Same as NIFTY #2: **buy CE / sell PE**. |
| **12:25–12:50** | ▲ **SENSEX early break** | Spot through 78900; CE 78800 / 78900 writers start covering; PE writers add (+44 L, 12:20–12:50). | **Buy SENSEX 0DTE CE** (78900 CE ~194 at 12:30). |
| **13:00–13:50** | ▲ **the leg** | +453; CE 78900 −24 L by 13:30. | Hold; book into 13:50 (78900 CE ~531 at 14:00). |
| 14:20–14:30 | ▼ | −180. | Trail. |
| 14:52 | ■ | New high without NIFTY: non-confirmation. | **Book everything**; 0DTE, past 14:30, inside her 15:00 cut-off. |

**SENSEX blind spot [M]:** from about 13:00, every SENSEX strike above spot was outside the recorded window (77300–78900). Any screen built from `chain_SENSEX` saw no call wall and no call-writer flow for the whole second half. Its "PE cover" numbers after 13:20 are puts far ITM-out (OTM 0DTE puts going to zero), not a bearish signal [I].

---

## 6. Day summary

1. Gap-up short-covering trend day: NIFTY +350 f at the open, then fut OI −9,750 lots as price added another 320 f; it closed 24575 f [M].
2. Put writers built under price all day and moved the floor 24300 → 24400 → 24500 → 24550 s. Call writers at 24300–24500 were trapped and covered −45 to −73 L each [M].
3. The morning (09:30–09:55, +140 f) and the dead zone (10:15–11:25) were readable. The one BADA print (11:40, 419-lot buyer at 24460 f) marked the step toward the 24500 wall [M].
4. **The second half started at 13:00** (fut through 24500, 10.5× delta minute, CE 24400 covering) and peaked **13:30–13:50**: CE ±7 −121 L, the 24500 s wall broke at 13:36, 24641.6 f at 13:48. The 14:24 retest of 24500 s held; 14:45–15:00 was distribution under a new 24550/24600 cap [M].
5. SENSEX (0DTE) agreed and led by about 30 min (78900 broke at about 12:30), made its high at 14:52 without NIFTY, and its recorded chain was blind above 78900 for the whole second half [M].

---

## 7. Files used (raw only)

- `tapemap/data/tape/fut1m_NIFTY_2026-11-05.json`, `fut1m_NIFTY_2026-11-04.json`: fut 1-min OHLCV + OI.
- `tapemap/data/tape/fut1m_SENSEX_2026-11-05.json`, `fut1m_SENSEX_2026-11-04.json`: checked only, thin, not used for flow.
- `tapemap/data/dext/dext_NSE-61471_2026-11-05.jsonl`: NIFTY fut 1-min footprint (delta, CVD, price cells, BADA).
- `tapemap/data/tape/ux_NIFTY_2026-11-05.jsonl`: Upstox 5-min tick ladder (BADA cross-check).
- `tapemap/data/chain/chain_NIFTY_2026-11-05.jsonl`, `chain_NIFTY_2026-11-04.jsonl` (last line): strikes, OI, LTP, IV.
- `tapemap/data/chain/chain_SENSEX_2026-11-05.jsonl`, `chain_SENSEX_2026-11-04.jsonl` (last line).
- `tapemap/data/vix/vix_2026-11-05.jsonl`.
- Rule source: `tapemap/ui-v2/public/validate2/engine.js` (BADA PRINT, lines 711–727). Method: `docs/kahani/review/GAPS-AND-LIVE-CHECKLIST.md`.
- Scripts (scratch, not committed): `fut.py`, `chain.py`, `detail.py`, `vwap.py` in the session scratchpad.
- **Not read:** Dext option-strike footprints (`dext_BSE-*`, `dext_NSE-399xx/400xx`), `senses_*`, `book_*`. That is option-side aggression and the order book; there was no time before 16:00 and RAM was low.
