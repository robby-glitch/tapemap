# Right panel v3: critique (Sonnet, 20 Oct 2026, as a discretionary index-options trader and a terminal UI designer)

**Read:** `PANEL-DESIGN-DRAFT.md`, `INTERNAL.md`, `EXTERNAL.md`, `mockup/NOTES.md`, `mockup/frames.json` (all 15 frames), the three screenshots.
**Tags:** [M] = I measured it, script in `scratch/cs_*.py`, run `python -X utf8 -B -I cs_<name>.py` from `scratch/`. [B] = the mockup builder's number. [I] = my inference.
**Nothing here is a hit rate.** Persistence and firing numbers describe the inputs, as INTERNAL does. They are never to be printed on the panel.

---

## 0. Bottom line

1. **The four questions are right. The build is wrong in the places that matter on the days that matter.** On the three frames you named, the mockup is empty (16 Oct 10:00), nearly right with two wrong words (16 Oct 11:05), and blind (19 Oct 14:30).
2. **The day-kind split is the wrong cure for the wrong disease.** [M] Futures volume on expiry days is *lower* than on normal days (49.8k vs 57.9k lots/day, 12 full days). Option OI on expiry days is *1.9×* higher (gross ATM±2 activity 2,467L vs 1,304L, 27 days). What both need is not a kind filter. It is **the same slot reference for all days, multiplied by today's own tempo.** On the data, that single rule removes the day-volume flag (Spearman 0.94 to 0.10) and puts expiry days on par with normal days (flow 10.2% vs 9.9% of windows at or above p90; OI 9.1% vs 10.3%). Same-kind references leave 19 Oct blind (0% coverage).
3. **"Speed" as built is mostly vocabulary.**
   - The 5m/30m flow ratio flips side 38% of the time every 5 minutes.
   - The OI ratio is a ratio of *nets*. On 16 Oct 11:05, `tez ↑` (31.9×) was an hour that went −91, +40, −18, +79 lakh: gross 227L, net 9.9L. That is churn, not acceleration.
4. **TREND as a 4-arrow vote is a description of the leg that just ended.** It printed `3/4 saath ▼` at the 16 Oct low, and it prints blank under a `RIDE ▼` header on 19 Oct. The READ already says direction. What the panel can add is **who fed the leg, and who has stopped feeding it.**
5. **The truth of 19 Oct 14:30, which the panel cannot say today.** The leg was fed for 15 minutes (13:15–13:30): flow sellers 71% (GC) / 66% (UX), call writing +174L (p100), put unwinding −158L (p96). All of the −52 pts came then. Nothing has fed it since: flow last fed it at 13:30, OI at 13:40, futures OI never, and BANKNIFTY refuses (it is +0.85% off NIFTY, rank p100 of 24 days). Price has been pinned for 60 minutes.
6. **My revised panel is §4. It is 30 rows at 44 characters, down from about 33.** It is built from the rules in §3, and every number in it is recomputed from the recorded files [M].

---

## 1. Verdict per block

| Block | Verdict | Why, as a trader |
|---|---|---|
| **Header** | **FIX (small)** | Keep the READ pill, `f \| s`, the clock, and the stale `READ 09:50 ka` tag. Add the leg age (`1h15`), an `EXP` chip, and **one** `ref 11d` chip. That chip replaces the `kam data` printed on every block, which carries no information. Move the P/R/T/Z/B/✕ legend to SIRF BADE's title; it is chart vocabulary, not header vocabulary. On 19 Oct the header says `RIDE ▼` while every block under it is blank: a verdict with nothing under it. |
| **KAUN DABA RAHA** | **FIX hard. Keep the question, replace the contents** | Four defects, all [M]: (1) Per-side "× normal" repeats the total. corr(log x_buy, log x_total) is 0.79 and sell is 0.85, so 63% and 72% of each side's variance is just "the market is busy". The new information is the tilt. (2) The speed words (`tez`, `dheema`) flicker. The ratio keeps its side of 1.0 five minutes later only 62% of the time, for total, buy and sell alike (n = 4,008). (3) `peak se neeche` on both sides is the same burst described twice, as a negative. At 14:30 on 19 Oct both peaks are 14:24 / 14:26. (4) EK-TARFA needs two sources both ≥ p70 *and* agreeing. Sources agree on delta sign only 70.6%, so the headline cell is grey most of the time by construction (it reached `GC+UX ✓` on 1 of 5 eligible frames [B]). |
| **KAUN LIKH RAHA** | **KEEP the block, FIX speed and tokens** | This is the best block: ATM±2 per side, a REST tag, per-strike tokens. But the speed ratio is wrong (§3 #5) and "sabse tez strike" is chosen by rank against a 5-day pool (§3 #6). `palat` is the wrong word for a fading wave (16 Oct 11:05 PUT: +116, +88, +27, −7 is `dheema`). |
| **TREND** | **CUT as a count. Replace with LEG / rasad** | An agreement count over the same trailing windows peaks when the leg ends. A trader reads agreement as confirmation exactly when it is exhaustion. Rendering also breaks the house rule: on 19 Oct the four arrows print `·` for inputs that were **not rankable** (`? ref kam` in the blocks above), so "could not check" looks like "checked, quiet". |
| **DOOSRE INDEX** | **FIX** | BANKNIFTY is the only peer with information; SENSEX is NIFTY's echo. Cut σ (RMS of 14 prior days) and SENSEX pace. Print `% from open` and the **spread to NIFTY**, ranked. Print a confirm word only when it was actually tested. §3 #7. |
| **SIRF BADE** | **KEEP, FIX order** | Newest first, with age, one row per bar and kind. 19 Oct 14:30 shows `13:20 Z` twice (74 minutes old) under `14:25 B`: it is one event, shown stale. |
| **PLAN** | **KEEP, FIX levels** | House rule: every level as spot and futures. The header does it; PLAN prints `ZONE 22,923–23,002f`, `KILL VWAP 23,002f`, `T1 22,844f` in futures only. The basis is one constant (about 28 pts on 19 Oct: 22,888f vs ≈22,860s). |
| **`?`** | **KEEP, FIX the three states** | One line plus `…` is right. But "checked, nothing" needs its own positive rendering (`shaant ✓`, or `—` for "this feeder never fed"), so it never shares a glyph with `?`. |

---

## 2. What a trader needs at the three moments

### 16 Oct 10:00, just after the low (09:35, 22,915; now 23,034f, +119)
**What I need to know:**
1. Was the low flushed and defended? [M] The 09:35 GC bar: sellers 1,128 vs buyers 472 (−41%). The next bar flipped +36%. The flush landed on the 22,900 put wall: the 09:40 frame had PE 22,900 +46L.
2. Is the bounce bought, or just shorts covering? [M] Since the low, GC delta is only +332 lots (buyers 57%, 1,338 vs 1,006) for +119 pts: a thin lift. Futures OI went 17.087M at 09:35 to 17.044M at 09:45, down 42k units: shorts covering. The OI feed died at 09:48.
3. The READ says FADE: don't chase.

**What the mockup gives:** almost nothing. Two grey `peak` times, EK-TARFA grey, CALL +35L and PUT +23L grey, FUT OI `? OI nahi`, TREND blank, PLAN `? fut ticks 5/15 nahi`. Only the SIRF BADE `P 09:35` helps.

**Verdict: fails.** Part of it is a data hole (Upstox gone from 09:48; GC snapshot bars carry no OI). But the design also fails on its own terms. At 09:40 the panel printed `3/4 saath ▼ price ▼ call likh ▼ fut` *at the low*, and by 10:00 the low had aged out of every 15-minute window. A clock-anchored panel cannot answer "what has happened since the low". A leg-anchored one can (§3 #2).

### 16 Oct 11:05, pullback inside the rally (high 23,145 at 10:36, now 23,104)
**What I need to know:**
1. The handover. [M] Buyers ran 09:50–10:35 (6,402 vs 4,195 lots, tilt +21%). Sellers have run since 10:40 (1,007 vs 1,852, −30%). The flip is at the 10:36 high. Over the last 15 minutes the tilt is −27%; over the 45 before that it is +16%.
2. The OI wave. [M] PUT builds, oldest to newest (fixed strikes): +116, +88, +27, −7. The floor-builders' wave is over. CALL: −91, +40, −18, +79: call writers returning at 23,100 / 23,150 / 23,200.
3. Walls are tests, not verdicts. 23,150 is 46 pts above spot, and the brief says the day later printed 23,155. I am not scoring the panel on that. It is why a wall must show its distance, not a colour that says "favours down".

**What the mockup gives:** the best frame of the three. `sellers 64%` (p87), `CALL +79L ▮▮▮▮▮ tez ↑ 23,200 +19L`, `2/4 saath`, three SIRF BADE rows. It reads coherently.

**Wrong words:** `tez ↑` should be `churn`; PUT `palat` should be `dheema`. **Missing facts:** the handover time (10:40), futures OI (`? OI nahi`), and a fresh READ (`09:50 ka` while the FADE pill still prints).

**Verdict: nearly right, two wrong words, one missing fact.**

### 19 Oct 14:30, trend-down afternoon (RIDE ▼ since 13:15, 22,888f)
**What I need to know:**
1. Is the leg still being fed? [M] Leg price: 22,940 (13:14) to 22,887 (13:29) to 22,888 (14:29). **All −52 pts came in the first 15 minutes.**
   - Flow in 13:15–13:30: sellers 71% (GC) and 66% (UX), both sources agree.
   - OI at 13:30: call writing +174L (p100), put unwinding −158L (p96).
   - Since 13:30: flow tilt GC 0% / UX +12% (both inside the band). OI feeding ended 13:40. Futures OI never fed (ranks p1–p45).
2. What happened at 14:19–14:27? [M] A 2.2× window (14:25: buyers 66%, 765 vs 388 lots) with price −19: effort without result. Then a new low (22,871f; 22,849 spot at 14:27) and a bounce to 22,888f.
3. Who writes where? [M] Re-centred below spot after the burst. Tempo-free ranks: PUT 22,750 +30L p93 and 22,800 +34L p93, CALL 22,850 +41L p85, PUT 22,900 −31L p83.
4. Does BANKNIFTY confirm? [M] No. BANKNIFTY is −0.32% on the day, NIFTY −1.2%, SENSEX −1.2%. The spread of +0.85% is p100 of 24 days.

**What the mockup gives:** every flow cell `? ref kam`; TREND blank under `RIDE ▼`; `peak se neeche` twice (the 14:19–14:27 burst, as a negative); the loudest cell is **SENSEX −3.0σ, which is NIFTY's own move** (spread −0.06%, p52); BANKNIFTY's p100 divergence prints as `−0.5σ` plus a `✗`; and the "fastest" CALL strike is `22,950 −15L` (p70 tempo-free, 18% of the side's change).

**Verdict: fails by blindness.** The OI structure and the `✗` are right. The money was made in 13:15–13:30. The one exit-relevant fact (the leg has been unfed for an hour) is invisible. I am not proposing an exit rule: folds stay zone / flow / OI / VPIN. The LEG rows feed the flow and OI lamps with information, not instructions.

---

## 3. The top 10 changes, ranked

### Direct answers to the four things you asked

| Question | Answer | Rule # |
|---|---|---|
| How should "normal" be defined? | **A mix: slot median over all prior days × today's tempo.** Prior-days-only (the draft) keeps the day-volume flag. Today-only (trailing 60 min) is blind for 65 minutes and absorbs a sustained trend. | 1 |
| How to show buyers and sellers, rate and speed? | **Total pace and tilt, each on a 5m / 15m / previous-45m ladder, plus a last-burst line.** Speed is the *shape* of the ladder. Per-side lots go on hover. | 3, 4, 9 |
| What is "trend" next to the READ word? | **Leg health, not a vote.** The READ gives direction and since-time. The panel adds who fed the leg, when each feeder last fed it, and who refuses. | 2 |
| How should OI build speed work without blowing up? | **Gross, not net.** Four 15-min quarters on fixed strikes, a bounded share, and a churn word. Print the four numbers. | 5 |

### Test 1: which "normal" (NIFTY, Upstox 1-min, 12 full days, leave-one-day-out; `cs_norm_test.py`) [M]
| Definition | Day-volume flag (Spearman of per-day share ≥ p90 vs day volume) | Expiry vs normal share ≥ p90 | Expiry coverage |
|---|---|---|---|
| A. slot median, all days pooled, raw | **0.94** | 7.9% vs 11.0% | 100% |
| AK. same-kind slot median (the draft) | 0.93 | no value | **0%** |
| **C. slot median × tempo** | **0.10** | **10.2% vs 9.9%** | 100% |
| B. own trailing 60 min | −0.35 | 11.2% vs 9.4% | 91% (first 65 min blind) |

### Test 2: the same for OI (36 chain days, 27 usable, 3 expiry; `cs_oi_norm.py`) [M]
| Definition | Expiry vs normal share ≥ p90 | Spearman with day activity | Expiry coverage |
|---|---|---|---|
| A. all days, raw | **18.2% vs 8.8%** | 0.89 | 100% |
| AK. same kind (the draft) | no value | 0.84 | **0%** |
| **C. all days × tempo** | **9.1% vs 10.3%** | **−0.01** | 100% |

Test caveat: it is leave-one-day-out for power. The live rule is **prior days only**, which is stricter. The first five days of history have no normal. The tests used cumulative activity to T; the `T−15` form in rule 1 (so a burst cannot normalise itself) was re-run for flow and holds (Spearman 0.11; expiry 10.5% vs normal 9.7%). The OI test was not re-run with `T−15`.

---

### 1. Normal = slot reference × today's tempo. One rule for flow and OI. Delete the day-kind split.
- **Rule:** `x(T,W) = value ÷ ( median over all prior days of the same clock window × tempo(T)^w )`.
  - `tempo(T)` = today's cumulative activity from the open to **T−15** ÷ the median of prior days' same cumulative at the same clock. Using T−15 stops a burst from normalising itself.
  - Activity: futures lots for flow; gross |15-min ATM±2 build|, both legs, for OI.
  - `w = min(1, minutes since open ÷ 60)` for flow, `÷ 90` for OI. At least 5 prior days (house `MIN_DAYS`).
  - Ranks: rank `x` against the same `x` built for each prior day, with that day left out of its own normal (the draft already does this).
- **Show the tempo once**, as a fact: `aaj 0.8×` (flow) and `aaj 2.9×` (OI, expiry). It is the day's temperature and is never coloured.
- **Day kind stays** as the `EXP` chip and a hover. It no longer selects the reference.
- **Data:** `pr_1m_*` and chain, as INTERNAL §3 and §5. No new data. Retires G5 for flow and replaces the kind filter in OI.
- **Limits:** a day that is hot from the open raises the afternoon's normal. That is the design: "unusual for today". The hot day is itself visible in the tempo chip.

### 2. TREND becomes LEG with `rasad` (who last fed it).
- **Leg:** the READ's since-time while the READ is RIDE. Otherwise the last confirmed 25-pt zigzag leg from GC bars, the one `v2.fuel` already uses. **Use the zigzag whenever the READ is older than 5 minutes.** On 16 Oct the READ was `09:50 ka` for 75 minutes; the zigzag lives in the page and does not go stale.
- **Rows:**
  - **Price:** points since the leg started and how many came in the first 15 minutes.
  - **Flow:** the tilt over the leg's biggest 15-minute stretch, and the tilt since it, per source (`GC | UX`). `✓` if both are beyond the band and agree, `shaant` if inside, `ulte` if opposite.
  - **`rasad`:** the last time each feeder printed at or above the tint threshold *in the leg's direction*. Flow means the 15-minute tilt; OI means the side build; fut means the futures OI change. `—` means it never fed this leg (checked). `?` means could not check. The last cell is BANKNIFTY's confirm (#7).
- **No count, no %.** Ink and grey only.
- **Data:** GC 5-min bars in the page and `session.since()` (INTERNAL §1, "no panel row uses it"), chain minutes, Upstox 1-min.
- **Check on 19 Oct [M]:** flow last fed at 13:30 (15m sellers beyond 0.30–0.36, both sources). Call writing last ≥ p80 at 13:40. Futures OI: never.
- **Caveat (EXTERNAL §8.1):** cumulative delta depends on its anchor. Print the anchor time on the row, show the two sources separately, and never let this row alert on its own.

### 3. Per-side × normal becomes PACE + TILT ladders (who is pressing, speeding up or tiring).
- **PACE:** total lots over 5m, 15m, and the previous 45m (non-overlapping), each as `×normal` (#1). Total volume needs no side inference.
- **TILT:** `(b − s) ÷ (b + s)` over the same three windows, per source. Tint only if `|tilt|` ≥ the tint threshold (#8) of `|tilt|` **for that width and that source**. UX NIFTY p80: 5m 0.44, 15m 0.36, 60m 0.26 [M]. GC has its own table; sources are never ranked against each other (INTERNAL §2.2).
- **Words:**
  - `daba rahe`: |T15| ≥ band, |T5| ≥ |T15|, and T45 not opposite.
  - `thak rahe`: T15 and T45 the same side beyond band, and |T5| ≤ ½|T15|.
  - `haath badla`: T15 and T45 opposite, both ≥ p60.
  - otherwise `shaant ✓`.
  - Sources: `GC+UX ✓` both beyond band and agreeing; `ulte` opposite signs with either beyond band.
- **Per-side lots/min** (for example 19 Oct 14:30: buy 64, sell 68) go on hover, as facts and never coloured. This answers "both sides separately" without printing the same number twice.
- **Why [M]:**
  - A 0.15 dead-band is not silence. A 15-min tilt beyond it appears in 61% of windows. NIFTY UX |tilt| over 15 min: p50 0.19, p70 0.30, p80 0.36, p90 0.43.
  - Persistence of the side over the next non-overlapping window is 62–65% at 3–15 min and 55% at 30 min. At a band of 0.30–0.35, `daba rahe` keeps its side 81–86% (n = 93 and 71 evaluations). That is input persistence, never printed.
  - **Chattiness:** at 0.15, `daba rahe` fires 6.1 episodes a day. At about 0.35 it fires 3.7 a day. The `haath badla` word fires 2.6 a day at 0.15 and 0.3 a day at 0.25. So it is a display of two numbers (the `pehle45` column) with a word only when both clear p60.
- **Retires:** the per-side 5m/30m speed words, and the peak marker (→ #4).

### 4. Last burst replaces the peak marker.
- **Rule:** the latest 5-minute window in the last 90 minutes with total `x` ≥ the tint threshold (#8). Print the time, `×normal`, the winner's share, and the price move over that window. Add `px ulta` when delta and price move opposite ways beyond a dead-band (|Δpx| ≥ 4 pts and |delta| ≥ 10% of the window's lots), else `px ✓`. Fade to grey after 30 minutes; drop after 90.
- **Data:** Upstox 1-min, GC 5-min bars.
- **Evidence [M]:** 82 windows at or above p90 over 12 days. Delta and price move the same way in 47, opposite ways in 14, and one of them is under the dead-band in 21. So `px ulta` is rare and not constant.
- **On 19 Oct:**
  - 13:25: 3.5×, p96, sellers 73%, price −26. The origin of the leg.
  - 14:25: 2.2×, p86, buyers 66%, price −19.
  - The draft's `peak se neeche` ×2 is this burst described twice as a negative, with no side and no price.
- **Descriptive only.** It is a fact about effort and result, not a reversal call (EXTERNAL §8.2).

### 5. OI speed: gross, bounded, four quarters shown. Drop `(15m ÷ 15) ÷ (60m ÷ 60)`.
- **Rule:** on ATM±2 strikes **fixed at T**, take `q0..q3`, the four consecutive 15-minute builds per side (L). Print them oldest to newest, for example `−91 +40 −18 +79`. Let `S = |q0| ÷ Σ|qi|`. Words, **first match wins, in this order**:
  - `churn`: Σ|qi| ≥ 4 × |Σqi| and Σ|qi| ≥ the tint threshold. (The hour oscillated; the latest quarter is just the latest swing. This must come before `palat`, or 16 Oct 11:05 CALL would print `palat`.)
  - `palat`: sign(q0) ≠ sign(q1+q2+q3), and both beyond the quarter noise floor (slot median |q|). A q0 below the floor does not count as a turn.
  - `tez`: S × n ≥ 2.0 and q0 has the sign of Σq.
  - `dheema`: S × n ≤ 0.8 and Σ|qi| ≥ the tint threshold (the wave was big, the last quarter is small).
  - `lagatar`: all quarters the same sign, none of the above.
  - Here `n` is the number of quarters available. Words begin at **10:02** with n = 3, not 10:16.
- **Show the strip and words only if the side's 15-min build *or its hour gross* is tinted.** Otherwise they live in the hover. (On 19 Oct 14:30 the hour gross is p58 / p46 tempo-free, so both strips stay in the hover.)
- **Data:** chain minutes (INTERNAL §5), already used by the builder.
- **Evidence [M], 36 chain days:** 949 "loud" side-quarters (|q0| ≥ p70 = 31L).
  - The draft's ratio exceeded 10× in 10% (p99 66×, max 473×) and was negative in 15%.
  - Its median is 2.2×, so the 1.5× word fires on **67%** of loud cells. It means "loud", not "faster".
  - Cause is netting: in 32% of loud cells the prior 45 minutes netted the *opposite* way.
  - 16 Oct 11:05 CALL: −91, +40, −18, +79 (gross 227L, net 9.9L) was labelled `tez ↑`; it is `churn`.
  - 16 Oct 11:05 PUT: +116, +88, +27, −7 was labelled `palat`; it is `dheema`.
  - `S` spreads sensibly across loud cells (p25 0.23, p50 0.36, p75 0.52): `tez` 28%, `dheema` 19%.
  - Persistence of the class 15 min later is the same as the draft's (73% vs 70%). The gain is not predictiveness; it is not lying.

### 6. Strike tokens: concentration plus a tempo-free rank, merged, never rank-only.
- **Rule:** a token prints only if (a) its tempo-free rank (#1) ≥ the tint threshold, **and** (b) |Δ| ≥ 25% of that side's gross ATM±2 change. Adjacent strikes on the same side that both pass merge into one range with the sum. Show `deewar` (adds, max 2 lines) and `nikal` (unwinds, 1 line). Distance from spot goes in the hover. If CE and PE both pass at one strike on an expiry day, add `pin K`.
- **Evidence [M], 19 Oct 14:30, tempo-free ranks against 27 days:**

| Token | Change | Rank | Share of side's gross | Prints? |
|---|---|---|---|---|
| PUT 22,750 | +29.8L | p93 | 27% | yes, merged |
| PUT 22,800 | +33.7L | p93 | 31% | yes, merged |
| CALL 22,850 | +40.6L | p85 | 49% | yes |
| PUT 22,900 | −30.8L | p83 | 28% | yes (unwind) |
| CALL 22,950 | −14.6L | p70 | 18% | **no** (the draft's pick) |

- The draft picked `22,950 −15L` at p71.7 against a cut of p70 = 14.2L, from a pool of 120 values over **5 expiry days** [B]. That is an effective sample of 5.

### 7. Peers: `% from open` and the spread to NIFTY, ranked. No σ. SENSEX gets price only.
- **Rule:**
  - Always print `% from open` for BANKNIFTY and SENSEX, grey, as facts.
  - Rank only the **spread to NIFTY** (peer % − NIFTY %, from open) against prior days at the same clock (N ≥ 10), and tint only if it is ≥ the tint threshold **and** |spread| ≥ 0.15% in absolute terms.
  - `high/low confirm nahi ✗` only when NIFTY set a session extreme in the last 15 minutes and the peer did not. Otherwise print nothing, **not** `saath ✓`.
  - BANKNIFTY also gets pace, ranked two-sided (thin ≤ p15, loud ≥ p85), and its OI state.
  - SENSEX gets no pace and no flow: at 14:30 on 19 Oct it traded 40 lots in 15 minutes, and INTERNAL G3 says it is lattice noise below 15 minutes.
- **Evidence [M], 36 days, spot from the chain rows:**
  - |SENSEX − NIFTY| at 14:30: median 0.06%, p90 0.12%. It is NIFTY's echo.
  - |BANKNIFTY − NIFTY|: median 0.18%, p90 0.76%.
  - 19 Oct 14:30: BANKNIFTY +0.85% (**p100** of 24 days); SENSEX −0.06% (p52).
  - The draft prints SENSEX `▼−3.0σ` loud, which is NIFTY's own −1.2%, and BANKNIFTY's p100 as `−0.5σ`. σ is an RMS over 14 days; a trader cannot calibrate it.
  - **Why the 0.15% floor:** at 16 Oct 10:00 SENSEX's 0.07% spread ranks p82. A rank alone would tint a difference no trader can see.
- **Data:** chain `spot` for all three (36 days), and `frame.peers` (G8).

### 8. Tint thresholds scale with N; one `ref Nd` chip.
- **Rule:** tint at p80 if N ≥ 20 days, p85 if 10–19, p90 if 5–9, nothing below 5. Loud is +10 points, capped at p97. Below the threshold the number prints grey. Remove `kam data` from every block. The header chip shows the smallest N of the blocks shown; the hover lists each.
- **Why:** p70 means about 30% of ranked cells are non-grey by construction. The pools are 78–120 values from 5–13 days, so the effective N is days, and a 1.7-point margin (p71.7 vs p70) printed a token [B]. "Noise stays silent" needs a cut that tightens as the sample shrinks.

### 9. Speed vocabulary: no arrows, bold not colour, and it must persist.
- **Rule:**
  - ▲▼ mean direction only. Speed has **no arrow**. Colour means side only. Speed words are bold ink.
  - Speed is the *shape* of the ladder (5m vs 15m vs previous-45m for pace and tilt; the four quarters for OI).
  - A word prints only if its cell is tinted **and** the shape holds on 3 consecutive evaluations (1-min stride for flow, 5-min for OI).
- **Why:** the builder flags that a red `tez ↑` reads as "price up" [B]. On the 16 Oct 11:05 screenshot it sits beside call *writing*, which is bearish. The 62% flow persistence above is the other half.

### 10. Honest blanks, fixed rows, first-hour anchors, spot and futures.
- **Rule:**
  - Computed-and-quiet prints `shaant ✓` (ink). Not computed prints `? why` (grey italic). **Never `·` for both.** This fixes TREND on expiry.
  - Rows stay in fixed positions on feed loss (`? UX nahi` in the same row).
  - First hour: use since-open anchors. GC covers NIFTY flow from 09:15. OI uses "aaj likha" against the 09:15 REST baseline. Flow speed words start at 09:47 and OI words at 10:02, not 10:16.
  - PLAN and SIRF BADE print key levels as spot and futures.
  - SIRF BADE: newest first, with age, one row per bar and kind.
- **Why:** 09:15–10:45 is when trends are born, and it is where the draft is blindest (INTERNAL G10).

---

## 4. The revised panel (19 Oct 14:30, 44 columns, 30 rows)

```
NIFTY  RIDE ▼ 13:15 se · 1h15   EXP   14:30
22,888f | ≈22,860s  −1.2% din · ref 11d
15:00 mein 30m baaki
────────────────────────────────────────────
LEG ▼ 13:15 se     −52f · sab pehle 15m mein
  13:15–30  bechne GC 71 | UX 66%       ✓
  13:30 se  GC 0 | UX +12     shaant ✓
  rasad flow 13:30 · OI 13:40 · fut — · BNF✗
KAUN DABA RAHA   5m   15m pehle45  aaj 0.8×
  pace ×normal 1.0×  1.2×    0.9×
  tilt GC|UX  −5|−3 −4|+6  +3|+16 shaant ✓
  burst 14:25 2.2× khareed 66% px −19 ulta
KAUN LIKH RAHA   15m · ATM±2      aaj 2.9×
  CALL  +54L   ·
  PUT   +17L   ·
  deewar  PUT 22,750–800 +64L     ▮▮▮▮▮
          CALL 22,850 +41L        ▮▮▮▯▯
  nikal   PUT 22,900 −31L         ▮▮▮▯▯
  fut OI  +0.1L · 75m             —
DOOSRE INDEX         din %   NIFTY se
  BANKNIFTY        −0.3%    +0.85 ▮▮▮▮▮
    low confirm nahi ✗ · pace 0.3× · OI flat
  SENSEX           −1.2%    −0.06 = NIFTY
SIRF BADE  +14 aur  B bada·Z zor·✕ toota
  14:25 B  Bada seller 22,878f 14K
  13:20 Z  Sellers ka zor 22,915f
PLAN  TREND
  SELL ▼ ARMED  ZONE 22,923–23,002f  +35
  KILL VWAP 23,002f  T1 −2σ 22,844f +114/−44
? could not check: SNX OI bahar · +3 …
```

**How to read it, and where each number comes from [M] unless marked.**
- **`rasad`** = the last time each feeder fed the leg. `—` means checked, never. `BNF✗` is BANKNIFTY's confirm.
  - Flow 13:30 and OI 13:40 are from `cs_rasad1430.py` and `cs_rasad_oi.py`. Futures OI ranks were p1–p45 over the leg.
- **LEG numbers:** the 13:15–13:30 sellers' share is GC 71% (741 vs 1,858) and UX 66% (894 vs 1,702). Since 13:30 the tilt is GC +0.4% (printed `0`) and UX +12%.
- **Pace ladder:** 1.03× / 1.19× / 0.86×. The day tempo is 0.82× (cumulative 38,246 lots vs a median of 46,889). OI tempo 2.86×.
- **Tilt ladder:** 5m GC −5% / UX −3%; 15m GC −4% / UX +6%; previous 45m GC +3% / UX +16%. All inside the bands, hence `shaant ✓`.
- **Burst:** 14:25, 2.17× (p86), buyers 66% (765 vs 388), futures price −18.6 pts between the closes at 14:19 and 14:24.
- **OI:** the grey `CALL +54L` is p52 and `PUT +17L` is p28 tempo-free (15-min builds). The hours' gross (CALL 228L, PUT 189L) is p58 and p46. The tokens are the tempo-free ranks in #6. Hover strips: CALL `+60 +91 +23 +54`, PUT `+59 +103 +11 +17`. They stay silent here because both sides' hours are ordinary for today's tempo.
- **Peers:** NIFTY −1.17%, BANKNIFTY −0.32%, SENSEX −1.23% from open (spot). The BANKNIFTY spread rank is p100 of 24 days; `pace 0.3×` and `OI flat` are the builder's trace [B] (88 lots vs a median 260; ce15 p2.7, pe15 p65). The `✗` is the builder's too.
- **SIRF BADE and PLAN rows** are copied from the mockup frame [B], unchanged except that the 13:20 duplicate is merged. PLAN's key levels still need their spot equivalents (#10).
- **Tinted at 14:30:** PUT 22,750–800 (p93), CALL 22,850 (p85), PUT 22,900 (p83), the burst (p86), BANKNIFTY (p100). That is five cells on an expiry day that really had action. A quiet day will tint one to three.

**Same OI block on 16 Oct 11:05, to show the speed fix:**
```
KAUN LIKH RAHA   15m · ATM±2
  CALL  +79L  −91 +40 −18 +79   churn
  PUT    −7L  +116 +88 +27 −7   dheema
  deewar  CALL 23,200 +19L        ▮▮▮▮▮
```
(The CALL strip and `churn` are [M]. The PUT `dheema` is [M] on shape but its hour-gross rank was not computed.)

---

## 5. What NOT to add

| Do not add | Why the data cannot carry it |
|---|---|
| A 1-minute or 3-minute pace or speed | A 3-min rate is 74% minute-shuffle noise on NIFTY, 80% on BANKNIFTY, 92% on SENSEX; 58% of top-decile 3-min windows are one minute. GC has no history below 5 min (INTERNAL §3, G1). |
| Acceleration as a first difference (flow or OI) | Keeps its sign 38% of the time; lag-5 ρ −0.33 to −0.47; mechanically tied to its own previous window. OI's change in build is 1.15× the build itself (INTERNAL §4–5). |
| A per-minute or "3-min OI rate", especially on SENSEX | The exchange publishes OI every 60 s on NSE and 160 s on BSE. A 3-min SENSEX rate is one or two updates (G4). |
| SENSEX flow or pace | 40 lots in 15 min on 19 Oct; 91–93% i.i.d. (G3). |
| A second-source tag for BANKNIFTY or SENSEX | No GC feed for them (G2). Label `UX only`. |
| Who is buying vs writing options as volume | Not measured as a series (G6). The `senses` sweep rows are unstudied. Don't print flow that does not exist. |
| Any trend "strength", score, %, or "confidence" | House rule. And the agreement count's persistence was never shown. |
| CVD as direction, or CVD divergence as a reversal call | Reset-point dependent; no statistics anywhere; mixed bar sizes manufacture it (EXTERNAL §8). The LEG row prints its anchor and never alerts alone. |
| VPIN as a gauge on this panel | EXTERNAL §8.5: "mechanical relation with trading intensity". Judge it against plain pace first. |
| Order-flow imbalance from the 5-level book (Cont-Kukanov-Stoikov) | Best-evidenced in EXTERNAL, but INTERNAL did not measure it, and at 2–3 snapshots a second the events inside a snapshot are lost. Shadow-measure it; do not face it yet. |
| Vol/OI, IV-residual "writing vs buying", or per-strike OI "rate per minute" | Data exists (`vol`, `iv` per leg), but unstudied; `wb` is not on the frame. Single-strike OI churns 2.3× its net in 30 min. Study first. |
| Index contribution, breadth (advance/decline) | Needs keys not subscribed. |
| Probability words ("likely to continue") | House rule. |

---

## 6. Verification of the builder's own findings

| Builder finding | My check |
|---|---|
| Expiry days go blind | **Confirmed.** Cause is the same-kind reference (coverage 0%), not volume. Futures expiry volume is lower; OI is higher. Tempo, not kind. |
| Both sides print `peak se neeche` together; it is total volume | **Confirmed.** The 19 Oct peaks at 14:24 / 14:26 are the same burst. corr(log x_buy, log x_total) is 0.79 (sell 0.85). |
| TREND `3/4 saath` at the 16 Oct low | **Confirmed** (frame 16 Oct 09:40). A 15-min vote describes the leg that just ended. |
| ↑/↓ used for direction and for speed | **Confirmed** on the 11:05 screenshot. |
| OI speed ratio blows up on a near-zero base | **Confirmed, but the mechanism is netting.** 10% of loud cells exceed 10×; 15% are negative; the median is 2.2×. Cure is a gross base. |
| "Sabse tez strike" disagrees with its row | **Confirmed**, and on 19 Oct it is a p70 pick from a 5-day pool. |
| Peers print `saath ✓` when nothing was tested (10 of 30) | **Consistent** with the frames I read; the confirm word must be blank when untested. |
| `kam data` on every block | **Confirmed** on every block that printed a ranked cell. One `ref Nd` chip replaces it. |
| EK-TARFA reached `GC+UX ✓` on 1 of 5 | **By construction**: two sources must both clear p70 *and* agree (they agree on delta sign 70.6%). |
| SIRF BADE cut to 3 rows went stale | **Confirmed** (19 Oct 14:30: two `13:20 Z` rows, 74 min old). |
| Width, not height, is the constraint | **Confirmed.** 44 columns. |

**Defects the builder did not list (all [M] unless marked [B]):**
- **p70 tint** lights about 30% of ranked cells by construction (#8).
- **Clock-anchored windows** cannot answer "since the low" (#2).
- **TREND `·`** renders could-not-check as checked-quiet on expiry, and the header contradicts it (#10).
- **SENSEX −3.0σ is a duplicate of NIFTY's move**; BANKNIFTY's p100 divergence is under-shown (#7).
- **`palat` is the wrong word** for a fading wave (#5).
- **PLAN prints futures-only levels** against the house rule (#10).
- **GC and UX disagree on the 60-min tilt on 19 Oct** (0% vs +12%) while agreeing on the 13:15–13:30 burst. A single-source print would have hidden this.

---

## 7. Limits, and what I got wrong on the way

- **All SEEN days.** 12 full Upstox days; 36 chain days (27 usable for the OI normal, 3 of them expiry); bars within a day are not independent. Tests are leave-one-day-out. The live rule is prior-days-only and therefore stricter.
- **Upstox side is inferred [I].** The two sources disagree in size and sometimes sign. The tilt bands above are UX numbers; GC needs its own.
- **16 Oct is a data-hole day.** The 10:00 and 11:05 verdicts are partly about the holes. The design findings (aged-out windows, netting, wrong words) stand without them.
- **I corrected one error of my own.** I first misaligned the 13:15–13:30 burst by one 5-minute window (UX sellers −1,194 lots). The aligned numbers are UX −808 (66%) and GC −1,117 (71%). Every number in this file is the aligned one.
- **The test thresholds (0.15 / 0.30 / 0.35 for tilt, p80 / p85 / p90 for tints) are descriptive**, to keep episodes to about 3–4 a day. They should be re-fitted when 30 sessions exist.
- **Next step, not done:** compute the proposed cells in `build_panel.py` on the same 15 frames, then forward-log in shadow for ten sessions. The 20 Oct session has no data (INTERNAL: no recording since 19 Oct).

**Scripts (all in `scratch/`, read-only on `data/`, run from that folder with `python -X utf8 -B -I`):**
`cs_norm_test.py` (Test 1) · `cs_oi_norm.py` (Test 2) · `cs_flow_test.py` (side structure, tilt persistence, bursts, 19 Oct 14:30) · `cs_states.py`, `cs_tilt_pct.py` (state frequency, tilt percentiles) · `cs_oi_test.py` (OI ratio vs bounded form) · `cs_strike_rank1430.py`, `cs_oi_rank1430.py`, `cs_rasad_oi.py`, `cs_rasad1430.py` (19 Oct OI and feeders) · `cs_spread.py`, `cs_peers_gc.py` (peers, GC cross-check) · `cs_d16.py` (16 Oct GC bars) · `cs_final_nums.py`, `cs_prior45.py` (panel numbers).
