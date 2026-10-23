# Right panel v3, design v2 mockup: notes (20 Oct 2026, after the close; round 3 = V2 §D)

**Run:** `python -B build_panel.py` rebuilds `frames.json`, `mockup.html` and the self-check at the end of this file (about
one minute).
- It reads recorded files only: no HTTP, no server, nothing written outside this folder.
- `mockup.html?only=<id>` shows one frame. That is how `shots-v3/` (all 15 frames) were taken, with headless Chrome at
  1720×820.

**Earlier rounds stay reachable:**
- round 2 pictures: `shots-v2/` (the face before §D);
- round 1: `mockup-v1.html`, `NOTES-v1.md` and `shots/`.

**Design:** `../PANEL-DESIGN-V2.md` (§A measures, §B face, §C pass bar, §D round-3 rendering decisions).
- Its measures are `../CRITIQUE-SONNET.md` §3, and the scratch scripts `../scratch/cs_*.py` are their reference code. Their
  formulas and loaders are reused here.
- The one change from the scripts: references are **prior days only**, where they used leave-one-day-out.

**Frames:** the same 15 and the same seed (20261020).
- Random draws: 19 Oct 12:40, 12 Oct 14:25 and 9 Oct 14:35.
- The last two fall after that day's recording stopped (12 Oct: 13:41; 9 Oct: 14:05).

## Round 3: the pass bar (§C), judged on the pictures in `shots-v3/`
| Frame | Asked | Verdict |
|---|---|---|
| **19 Oct 14:30** | Leg fed only 13:15–13:30; nothing since; BANKNIFTY refuses; < 2 s | **Pass.** One caveat remains: the `✓` rests on the house two-source rule. UX's −0.31 is inside its band of 0.38. |
| **16 Oct 11:05** | The rally leg, the pullback, sellers pressing it; the PUT wave fading; call churn | **Pass on the picture. The words still don't print.** |
| **16 Oct 10:00** | What happened since the low, as far as the data existed; `?` where it died | **Pass, mostly.** The covering is visible as a last-known number, never as a word. |
| **Expiry vs normal** | Similar rates; nothing blind on 19 Oct | **Pass.** See the firing table. No block is `?` on any 19 Oct frame. |

What each picture shows, frame by frame:

| Frame | What the picture shows |
|---|---|
| **19 Oct 14:30** | **Header:** `LEG ▼ 13:15–14:25 −69` (READ-anchored; 13:15 is RIDE's since-time; 14:25 is the 22,871f low). **Stretch row:** `13:15–30 ▼53`, the panel's only strong red tilt bar, with `✓ saath`. **Pullback row:** `abhi ▲17 24% wapas 14:25 se`, with a near-empty tilt bar. **Rasad:** `flow 13:37` and `OI 13:40` are grey (stale), `fut —` is dashed (never fed), and `BNF ✗` has a red outline. **DOOSRE INDEX:** the dark `NIFTY se +0.85%` chip and `low ✗`. |
| **16 Oct 11:05** | **Leg and pullback:** `LEG ▲ 09:35–10:35 +246` in green. Below it, in red, `abhi ▼44 18% wapas 10:40 se`, with a red tilt bar (GC sellers 65%, p88) pressing the pullback. **Ladder:** the tilt reads red / red / green (sellers now, buyers in the 45 min before). **Burst:** `10:55`, a red bar. **OI:** the PUT columns shrink (`+116 +88 +27 −7`, green fading to a red stub), and the CALL columns alternate (`−91 +40 −18 +79`), which is churn visible as a shape. **Words:** no `dheema` or `churn` prints. At OI tempo `aaj 2.4×`, neither side's build is tinted for today, and the word gate needs it. |
| **16 Oct 10:00** | **Leg and pullback:** `LEG ▼ 09:15–09:35 −176` (from the opening high to the 22,908 low), then `abhi ▲126 72% wapas 09:40 se` with a faint green tilt bar (GC buyers 57%, p54). That is the thin lift. **Dead feed:** `fut OI −0.2L · 09:50 tak` in amber italics. The Upstox book died at 09:48. The last 15-min change is −0.2L, rank p39, so no `covering` word; the number shows it as it was known. **Rasad:** `OI 09:55` is solid, `fut ?` is amber (the feed is dead), and BNF is ✓. **Honest states:** the stale READ, PLAN's `?` and the `bad mein aaya` tags. |

## Firing table (a description of the inputs, not a hit rate)
**Definitions:**
- **Lit:** a cell in the block passes its rule's gate (tint threshold or word) now. For LEG it means a feeder fed the main
  leg within 15 minutes, or the pullback is pressed beyond the band.
- **Quiet:** computed, and nothing passes.
- **?:** the block's main cells could not be computed.
- The bars are drawn continuously (§D1), so "quiet" does not mean invisible.

| Block | Normal (11 frames): lit / quiet / ? | Expiry (4 frames, all 19 Oct): lit / quiet / ? |
|---|---|---|
| LEG | 5 / 6 / 0 | 2 / 2 / 0 |
| KAUN DABA RAHA | 6 / 3 / 2 | 4 / 0 / 0 |
| KAUN LIKH RAHA | 5 / 4 / 2 | 4 / 0 / 0 |
| DOOSRE INDEX | 8 / 1 / 2 | 2 / 2 / 0 |

The two normal-day `?` frames are the random draws after the recorders stopped. On those frames the OI and futures rows now
show their last known values in amber (`−15L · 14:06 tak`).

**Words** (gated by §A6's N-based thresholds, as decided):
- Flow `tez ho raha` / `thak raha`: still **0 of 15**. Speed is now carried by the pace and tilt bar ladders, e.g. 16 Oct
  10:25 pace 1.7× / **3.2×** / 1.1×.
- OI words: 1 of 15 (`dheema`, PUT, 9 Oct 10:30).

## §D as built (round 3)
**D1 · Continuous intensity.**
- The strength is a function of the rank: 0.10 below p50, 0.30 at p70, 0.80 at p90, 1.0 from p97, linear in between.
- It drives every pace bar, tilt bar and OI column, and the CALL/PUT numbers.
- Words, tokens, rasad "fed" and the stretch `✓` keep their gates. The gate is §A6's N-based cut.

**D2 · Tilt.**
- A diverging bar on a centre line: sellers go left in red, buyers right in green.
- Length = share − 50%. The half-track of 30 px is 30 points, so 51% is a 1 px stub and 65% is 15 px.
- Two sources, same sign: the length is the weaker source's. The strength is `min(stronger, max(weaker, 0.78))`, a
  continuous form of `rank.two_source`: both strong → the weaker speaks; one strong → capped at 0.78.
- Opposite signs: each source draws its own **hatched** half-bar on its own side.
- One source: its own bar, plus a `GC` / `UX` tag.

**D3 · Pace.**
- A slate bar 40 px long = × normal, capped at 3×, strength by rank, with `1.2×` beside it.
- The ladder is a shape: in 16 Oct 10:25, 1.7× / 3.2× / 1.1× reads as a spike in the last 15 min.

**D4 · OI quarters.**
- Four real columns per side, oldest → newest, 9 px wide, up to 14 px up (adding) or 14 px down (cutting) from a midline.
- One scale per side: max(the side's biggest |quarter|, 2 × the slot's median raw |quarter|), so noise stays short.
- **Each column's strength is its own quarter's tempo-free rank**, at that quarter's end. Its colour is the side it
  favours (call add red, put add green, cuts the other way).
- Each side sits in a light box, so a CALL "cut" column never runs into the PUT columns below. Values and ranks are on
  hover.

**D5 · LEG = main leg + current pullback.**
- **Threshold:** max(50, 0.5 × IV-priced 30-min σ), with σ = spot × ATM IV × √(30 ÷ (252 × 375)).
  - The IV is the last recorded chain row at or before T; a dead chain keeps its last IV, shown on hover.
  - It is 50 pts on 9, 12 and 16 Oct, and 72 pts on 19 Oct (expiry ATM IV 31–39%).
- **READ fresh and RIDE:** the main leg runs from the READ's since-time to the extreme since then.
- **Otherwise the zigzag** (`board.js legs()` on 5-min closes):
  - if the open leg is a reversal smaller than the leg before it, the earlier leg is the main leg and the open one is the
    pullback;
  - otherwise the open leg is the main leg.
- **The start** is the true high or low within 15 min before the close-based pivot (J9). Closes put the 16 Oct pivot at
  09:45; the low is 22,908 at 09:35.
- **The leg's end time** is the last bar that still tested the extreme, within 0.1 × the threshold (J10). For 16 Oct the
  23,154.6 high was set at 10:15 and retested to 10:35, so the pullback runs from 10:40.
- **The pullback row:** `abhi ▼44`, then `18% wapas 10:40 se` (`pura wapas` at 100% or more). Then the pullback's
  two-source tilt bar (who is pressing it) and its pace. It is shown when |pullback| ≥ 0.1 × the threshold, else
  `extreme par`.
- **Rasad** is measured on the main leg. A feeder whose data stops before T and never fed reads `?`, not `—` (J11).
- The stretch row (the biggest 15-min stretch of the main leg) stays.

**D6 · Dead feeds.**
- The last known value from up to 2 h back, in amber italics, with its clock: `−0.2L · 09:50 tak`.
- Applies to the futures OI row, the CALL/PUT rows when the chain is dead, and BANKNIFTY's pace.
- When the last known value passes its gate, its word is added.
- The KAUN DABA ladder still reads `?` on a dead feed (scope note).

**D7 · BNF chip.**
- At NIFTY's spot extreme of the main leg, did BANKNIFTY's spot within 15 min either side reach its own extreme of the
  main leg, within 0.05%?
- `✓` (ink outline) or `✗` (red outline). `?` (amber) when a spot is missing.
- There is no time and no "fed" state.

**D8 · SIRF BADE `×N`** merges only marks of the same bar, family **and price**. 19 Oct 14:30 shows
`13:20 Z 22,915f` and `13:20 Z 22,888f ×2` as separate rows.

## What is still wrong
1. **The words are still silent** (flow 0/15, OI 1/15).
   - The gates are working as written: the tint threshold, a monotone ladder held for 3 evaluations, and the OI word gate.
   - With continuous bars, the picture now carries speed, so the words may not be needed. If Mary wants words, the gate
     has to loosen. For example, drop the 3-evaluation hold for flow, or gate OI words on the per-quarter ranks that
     §D4 now draws.
2. **The 19 Oct leg is "fed" only through the house two-source cap.** UX alone is inside its band. Under "both sources
   beyond", the stretch would be `shaant` and the flow chip `—`. That is still a choice someone has to sign.
3. **"The smaller reversal is the pullback" calls deep retracements pullbacks:** 16 Oct 10:00 is 72% wapas, 19 Oct 09:55
   68%, 9 Oct 10:30 87%. A trader might call a 70–90% retrace a new leg. A cut, such as "≥ 62% back is a new leg", would
   be a new rule.
4. **A READ-anchored leg that went the wrong way** reads `LEG ▼ 13:15–13:15 −8 · abhi ▲19 pura wapas` (12 Oct 13:30). It
   is honest but ugly: the READ says down and price is up.
5. **The 16 Oct covering is a number, not a word.** The 15-min futures OI change that ends when the feed died (09:33–09:48,
   −0.2L) ranks p39. The bigger 09:35–09:45 drop (−0.43L, Sonnet) does not fit a 15-min window ending at 09:48.
6. **Expiry IV lifts the zigzag to 72 pts** (19 Oct). The legs are coarser exactly on the day with the most movement. On a
   dead chain the IV is stale (16 Oct uses 09:48's).
7. **Hatched disagreement** still draws ±3% source splits (19 Oct 14:30 15m). They are now two small hatched stubs and
   quiet.
8. **The dead-feed scope** is the OI, futures and BANKNIFTY pace rows only. The flow ladder on a dead feed still reads `?`.
9. **The two random post-recording frames** show stale SIRF BADE marks with no age, as in round 2.

## §A measures, exactly as built (round 2; §D changes noted)
Every threshold is in the block at the top of `build_panel.py`.

**A1 · normal = slot reference × today's tempo (Sonnet #1).**
- Flow: `x = lots[T−W, T) ÷ (median of the same window on prior days × tempo^w)`.
  - tempo = today's lots from the open to T−15 ÷ the median of prior days' same cumulative;
  - w = min(1, minutes since 09:15 ÷ 60);
  - at least 5 prior days;
  - all day kinds pooled;
  - the rank pool is the same x for every prior day (its normal from the other prior days) at every 5-min window end.
- OI: the activity is the gross |15-min ATM±2 build|, both legs, summed in 15-min steps from the open on strikes fixed at
  T−15 (`cs_oi_norm`). w = min(1, minutes ÷ 90). Ranks are `|value| ÷ tempo^w` against the same on prior days at window
  ends T−15…T+15 (`cs_strike_rank1430`).
- **UX cumulative across a hole:** the first Upstox minute after a recorder hole carries the hole's volume (vtt
  differences). So the cumulative is exact with a record that starts by 09:17 and a minute ending at the clock. *Windows*
  still drop that minute (§A10).
- **Tempo needs the whole cumulative from the open.**
  - 9 Oct: Upstox starts 10:11, and GC lacks 3 bars by 13:50, so pace reads `? tempo nahi`.
  - 16 Oct: Upstox starts 09:23, so it is GC all morning.
- `aaj 0.8×` / `aaj 2.6×` print once per block, uncoloured. `EXP` is a header chip and never a filter.

**A2 · LEG + rasad (Sonnet #2). Superseded in part by §D5 (main leg + pullback, threshold, start, end); the feeders below are unchanged except §D7 for BANKNIFTY.**
- **The leg:**
  - when the READ is RIDE and fresh (row ≤ 5 min old), its since-time;
  - otherwise the last leg of `board.js legs()` (a 25-pt zigzag on 5-min closes), ported, on GC bars with candles filled
    [I] from the orderflow-desk session files.
- **Row 1 (where the points came from):** the leg's biggest 15-min stretch on the 5-min grid, with its points and its
  two-source tilt bar.
- **Row 2:** everything since that stretch.
- **Mark:**
  - `✓ saath` = the combined tilt is tinted in the leg's direction;
  - `ulte` = a source is beyond its band the other way;
  - `shaant ✓` otherwise.
- **rasad** = the last time each feeder fed the leg. A window counts once it ends at least 5 min into the leg, so a
  10-minute-old leg is still checked. The feeders:
  - flow: the 15-min combined tilt is tinted in the leg's direction (1-min stride on UX, 5-min on GC);
  - OI: the ATM±2 side build is tinted and points the leg's way. A down leg means call writing or put unwinding;
  - fut: |ΔOI15| is tinted with price in the leg's direction. **J5: either OI sign counts** (naye short / long nikal
    for a down leg). `cs_rasad_oi` counted only OI up;
  - BANKNIFTY: the last minute its spot made a new extreme since the leg began, plus `✗` when NIFTY set a session extreme
    in the last 15 min that BANKNIFTY did not confirm.
- **Chip states:**
  - solid ink if fed within 15 min;
  - grey if stale;
  - dashed `—` if never fed (checked);
  - amber `?` if it could not be checked.

**A3 · KAUN DABA RAHA = PACE + TILT ladders + burst (Sonnet #3, #4).**
- Pace: x for 5m, 15m, and the 45 min before the last 15. Tilt: (b − s) ÷ (b + s) on the same three windows, per source.
- **The pace source is one source (J1).** UX is used when it has the cumulative and all three windows, then GC, then
  whichever has the cumulative.
- **Tilt shows both sources** where they exist.
- **Tilt bands:** |tilt| at the N-based cut (A6) for that width and source, from prior days at every 5-min end.
  Examples (16 prior UX days, 19 GC days, before 19 Oct):

  | Source | 15m band | 45m band |
  |---|---|---|
  | UX | 0.38 | 0.29 |
  | GC | 0.27 | 0.21 |

- A tilt needs ≥ 60 lots.
- **Words:** `tez ho raha` when 5m > 15m > 45m and the 5m cell is tinted; `thak raha` when 5m < 15m < 45m and the 45m cell
  is tinted. Tilt also needs one sign across all three. The shape must hold at T, T−1 and T−2 (UX) or T, T−5 and T−10
  (GC). Otherwise no word.
- **The 45m cell** cannot exist before 10:15 (GC) / 10:18 (UX). It reads `10:15 se` in grey, never `—` or `?`.
- **Burst:** the latest 5-min window in the last 90 min whose pace is tinted. The line shows:
  - the window's end time;
  - its x and its tilt bar;
  - the futures move, as an arrow and points;
  - `px ulta` when price and delta oppose beyond 4 pts and 10% of the lots, else `px ✓`.

  It goes grey after 30 min. With no burst the line reads `shaant ✓`.

**A4 · KAUN LIKH RAHA.**
- **CALL / PUT:**
  - the 15-min ATM±2 build (tinted by its tempo-free rank);
  - **four quarter blocks**, oldest → newest, on strikes fixed at T;
  - a word. First match wins:
    - `churn`: gross ≥ 4×|net| and tinted;
    - `nikal rahe`: the last quarter < 0 beyond the quarter noise floor (the median raw |q| of prior days) and the hour
      net < 0;
    - `badh raha`: S·n ≥ 2, the last quarter > 0 and the net > 0;
    - `dheema`: S·n ≤ 0.8 and tinted.
  - The word also needs either the 15-min build or the hour gross to be tinted, and it must hold on 3 evaluations, 5 min
    apart.
- **Tokens (Sonnet #6):**
  - a strike prints if its tempo-free rank against its own ATM+j pool is tinted **and** it carries ≥ 25% of the side's
    gross ATM±2 change;
  - adjacent same-sign strikes merge;
  - at most two `deewar` rows (adds) and one `nikal` row (unwinds), each with its distance from spot (`56 neeche`);
  - `pin K` on an expiry day when CE and PE both pass at one strike (it never fired).
- **fut OI:** |ΔOI15| ranked plainly against prior days. When tinted, a word by price direction; otherwise `shaant ✓`;
  `? OI nahi` when either end is missing.

**A5 · DOOSRE INDEX (Sonnet #7).**
- `din %` (spot from the open; the open is the first spot minute, by 09:20).
- **Spread to NIFTY:** ranked |spread| at the same clock against prior days (≥ 10 days). It is tinted only past the N-cut
  **and** at ≥ 0.15%, with a **neutral slate** tint, because a divergence is not a side.
- **SENSEX:** `= NIFTY` when quiet.
- **Confirm:** `high/low ✓` or `✗` only after a test, i.e. NIFTY set a session extreme in the last 15 min. Otherwise blank.
- **J4:** a peer within 0.05% of its own extreme has "confirmed". σ is cut and V2 gives no tolerance; this one is mine.
- **BANKNIFTY extras:**
  - pace two-sided: ≤ p15 grey italic, ≥ p85 tinted;
  - its OI state (the stronger tinted ATM±2 leg, else `OI shaant ✓`).
- No SENSEX pace.

**A6 · tints by N (Sonnet #8).**
- p80 at ≥ 20 days, p85 at 10–19, p90 at 5–9. Loud is +10, capped at p97.
- One header chip, `ref Nd`, shows the smallest N behind the flow, OI and peer blocks. No `kam data` and no N anywhere else.

**A7 · three states.** `shaant ✓` is ink. `—` is a dashed or grey dash: never fed, checked. `?` is amber, with its reason
on hover and in the `?` line. A window the clock does not allow yet (`10:15 se`) is a fourth, grey, so it is never
mistaken for any of the three.

**A8 · PLAN prints spot and fut.**
- Spot is `fut − basis`, rounded to 10 as `≈`. It is `?s` when the basis is implausible (19 Oct 09:55 / 11:30, 16 Oct
  10:25 / 11:05).

**A9 · SIRF BADE.**
- Order: KHEL-relevant first (RIDE: marks favouring its side), then newest. ≤ 3 rows.
- One row per bar and family: same-bar marks merge with `×N`, keeping the first one's price.
- The P/R/T/Z/B legend sits under its title.

**A10 · hygiene.**
- The first Upstox minute after a hole is left out of every window.
- `READ hh:mm ka` shows in amber when the READ row is more than 5 min old.
- **`bad mein aaya`** (grey italic) on a block whose inputs would not have existed live at T:
  - a REST-backfilled OI or spot minute counts only if the poller recorded a row after it, by T;
  - a GC snapshot bar (`fromTicks:false`, replayed after a gap) counts only if a ticked bar followed it, by T.

## §B face, as honoured
- **B1 (tilt):** superseded by §D2 (diverging bar). Round 2 drew one bar per window.
  - Green = buyers, red = sellers; length = the winner's share.
  - **Hatched grey** when GC and UX disagree in sign; a small `GC` / `UX` when only one exists. Exact numbers are on hover.
  - **J2:** the bar is anchored at the winner's edge (sellers grow from the left, buyers from the right). A quiet grey bar
    therefore still shows its side, and "length = share" is kept.
- **B2:** superseded by §D3 (pace bar). Round 2: pace is `1.2×`. Quiet is grey text; tinted is a light slate chip; loud is a dark slate chip. Pace has no side, so
  it has no green or red.
- **B3:** no p-numbers and no N on the face. They are on hover. The only face numbers of that kind are `ref Nd` and
  `aaj x×`.
- **B4:** ▲▼ appear only on price (LEG points, burst move, din %, PLAN side). Speed words are bold ink.
- **B5:** green / red for side, grey for quiet, amber only for could-not-check (and the stale READ). The tinted spread and
  the pace chips use neutral slate.
- **B6:** four rasad chips. flow / OI / fut carry a time: solid ink, grey, dashed `—`, or amber `?`. BNF is ✓ / ✗ only (§D7).
- **B7:** superseded by §D4. Round 2: four quarter blocks per side, up for adds and down for cuts, on a common lakh scale per frame. They are coloured
  by the side they favour when tinted, grey otherwise.
- **B8:** 360 px wide, 12 px minimum type. Every panel fits 820 px; the in-page overflow check fires on none of the 15.
  The tallest is 19 Oct 14:30, at about 800 px.
- **B9:** judged as a picture. The verdicts are above.

## Round 2: what was wrong in V2 (kept for the record; items 2, 4, 6, 7, 8, 11 are addressed by §D)
1. **Two of Sonnet's numbers disagree.**
   - Rasad's check used p80 bands (0.30–0.36). §A6 sets p85 at 10–19 days, which is UX 0.38.
   - The 19 Oct leg's flow passes only through the house `rank.two_source` cap (J3).
   - Someone has to pick: "both beyond", or "one beyond, capped".
2. **The N-based cut is a knife edge.** GC sits at 19 days (p85). One more recorded day drops it to p80, and the 16 Oct
   handover would tint. The face will change overnight with no change in the market.
3. **Tempo absorbs the OI story on busy-OI days.** On 16 Oct 11:05 (`aaj 2.4×`) and 10:25 (`2.2×`) the PUT/CALL builds
   are quiet for today, so `churn` / `dheema` / `badh raha` cannot print. That is "unusual for today", by design. But it
   is exactly the frame the pass bar wants those words on.
4. **The 25-pt zigzag at 5-min resolution flips on small swings** (16 Oct 09:35 → 09:40 → 09:45; 10:50 → 10:55).
   - The LEG often describes a 15-minute wiggle. "Since the low" and "the handover at 10:40" are not the leg it picks.
   - The READ is RIDE-fresh on only 5 of 15 frames, so the zigzag carries the rest.
5. **The speed words almost never print** (0/15 for flow, 1/15 for OI). Speed is carried by the shape of the bars alone.
   That may be right, but the words cost design attention and code for something nobody will see.
6. **Hatching fires on ±3% disagreements** (19 Oct 14:30, 15m: GC −4% vs UX +6%). It is grey, so quiet, but it is the
   most textured object in the ladder.
7. **"Length = the winner's share"** makes every bar at least half full. A 51% bar and a 64% bar differ by about 8 px.
   The edge anchoring (J2) is what makes a grey bar readable at all.
8. **The BNF chip can be solid and ✗ at once** (12 Oct 13:30: BANKNIFTY made a new leg low at 13:17, then refused
   NIFTY's newer low). This is correct, and it reads as a contradiction.
9. **Tempo needs a clean cumulative from the open.** Late recorder starts (9 Oct 10:11, 16 Oct 09:23 on Upstox) and three
   missing GC bars (9 Oct) blank pace for the rest of the day.
10. **SIRF BADE `×3` merges same-bar marks at different prices.** Only the first price is shown.
11. **The covering at the 16 Oct low has nowhere to live.** The fut row is the current 15 minutes, and the data died at
    09:48. V2 has no "last known" state for a dead feed.

## Judgement calls (V2 is silent)
| # | Call | Why |
|---|---|---|
| J1 | One pace source: UX first, then GC (each ranked against its own history only) | UX rolls at 1 minute in history; GC is only 5-min bars |
| J2 | Tilt bar anchored at the winner's edge | So a grey (quiet) bar still shows its side; length stays the share |
| J3 | Two sources, same sign, one beyond its band → tinted, capped below loud (`rank.two_source`, Mary's 19 Oct amendment) | Sonnet's ✓ / shaant / ulte does not cover this case |
| J4 | Confirm tolerance 0.05% of price | σ is cut, and no tolerance was given |
| J5 | fut feeds the leg with either OI sign when price moves the leg's way | "fut means the futures OI change" (Sonnet #2); `cs_rasad_oi` counted OI-up only |
| J6 | A rasad window counts once it ends ≥ 5 min into the leg | A 10-min-old leg would otherwise be all `?` |
| J7 | `10:15 se` (grey) for the 45m cell before it can exist | `—` means "never fed" and `?` means "data died"; this is neither |
| J8 | Speed-word cells: `tez` needs the 5m cell tinted, `thak` the 45m cell | Sonnet #9 says "its cell is tinted" without naming the cell |
| J9 | A zigzag main leg starts at the true high / low within 15 min before its close-based pivot | Closes pick the pivot (16 Oct 09:45); the trader's low is 09:35 |
| J10 | The leg ends at the last bar that tested the extreme (within 0.1 × the threshold); the pullback starts after it | The 16 Oct top was a 10:15–10:35 plateau |
| J11 | A feeder whose data stops before T and never fed reads `?`, not `—` | `—` means "checked, never"; a dead feed was not checked |
| J12 | BNF confirms if, within 15 min of NIFTY's leg extreme, its own spot reached its leg extreme within 0.05% | §D7 gives the meaning, not the test |

<!-- SELF-CHECK: generated by build_panel.py; everything below this line is rewritten on every run -->

## Self-check: the inputs behind every new cell (generated)

x = lots ÷ (median of the same window on prior days × tempo^w). Ranks are against the same x on prior days; "tint" is the N-based cut (p80 / p85 / p90), "loud" +10. Text form of the pictures: `[bech 71%]` = a red tilt bar at 71%, `*` = loud, `[+60 +91 +23 +54]` = the four OI blocks oldest→newest.

### 2026-10-16 10:00 (NORMAL day)

```
NIFTY  FADE 09:45 se  [READ 09:50 ka]   10:00
  23,034f | ≈23,030s   -0.1% din   ref 17d
LEG ▼ 09:15–09:35 -176   (zigzag)
  09:15–09:30  ▼132  [bech 60% s0.3 GC]  shaant ✓
  abhi ▲126  72% wapas 09:40 se  [kharid 57% s0.2 GC]  0.7×(s0.1)
  rasad  flow —  OI 09:55  fut ?  BNF ✓
KAUN DABA RAHA   (aaj 1.0× · GC · bad mein aaya)
        5m      15m     pichle45
  pace  1.3×(s0.2)  0.7×(s0.1)  10:15 se
  tilt  [kharid 54% s0.1 GC]  [kharid 52% s0.1 GC]  10:15 se
  burst  shaant ✓
KAUN LIKH RAHA   (aaj 1.1× · bad mein aaya)
  CALL  +35L  [+81L(p61) +35L(p47)]
  PUT  +23L  [−0.2L(p1) +23L(p41)]
  fut OI  −0.2L · 09:50 tak
DOOSRE INDEX   (bad mein aaya)
  BANKNIFTY  ▼0.2%  NIFTY se −0.09%
  pace  1.0× · 09:33 tak  OI shaant ✓
  SENSEX  ▼0.0%  = NIFTY
SIRF BADE   (P phase · R roka · T thakan · Z zor · B bada · ✕ toota)
  09:35 P Sellers phase 22,915f 43K
  09:25 T Sellers thake 22,946f ✕
PLAN  
  ? plan: fut ticks 5/15 nahi
? READ 09:50 se ruka · +1 …
```

- **LEG**: down main leg (zigzag, threshold 50 pts, ATM IV 0.132 at 09:48) from 23,084 at 09:15 to the extreme 22,908, last tested 09:35 = -175.9; now 23,034, pullback +126.4 (72% back) since 09:40
  - pullback tilt: GC b1338 s1006 (+0.14, p54) → shaant
  - stretch 09:15→: -132.5 pts; tilt GC b1852 s2732 (-0.19, band 0.27) → shaant
  - rasad (main leg): flow never, oi 09:55, fut ?, bnf {"word": "\u2713", "nifty_t": "09:36", "near": 55545.2, "ext": 55545.2, "tol": 27.7726}
- **pace 5m** (GC): lots 929 (b 499 / s 430) → x 1.33, p63 of 17 days, tempo 0.99, level 0
- **pace 15m** (GC): lots 1621 (b 846 / s 775) → x 0.73, p28 of 17 days, tempo 0.99, level 0
- **pace pichle45** (GC): the GC record begins 09:15; the window starts 09:00
- **tilt 5m**: GC b499 s430 +0.07 (band 0.38) → GC
- **tilt 15m**: GC b846 s775 +0.04 (band 0.27) → GC
- **tilt pichle45**: none → None
- **ladder words at T, T−1, T−2 evaluations**: pace [None, None, None] · tilt [None, None, None]
- **CALL**: 15m +35L (p47 of 24 days, tempo 1.14), quarters oldest→newest +81.3 +35.4, hour-gross pn/a, word at T−10/T−5/T [None, None, None] → None
- **PUT**: 15m +23L (p41 of 24 days, tempo 1.14), quarters oldest→newest -0.2 +23.0, hour-gross pn/a, word at T−10/T−5/T [None, None, None] → None
- **fut OI**: none
- **BANKNIFTY**: din -0.19%, spread -0.09% p13 of 23 days, confirm None
- **SENSEX**: din -0.04%, spread +0.06% p68 of 22 days, confirm None

### 2026-10-16 11:05 (NORMAL day)

```
NIFTY  FADE 09:45 se  [READ 09:50 ka]   11:05
  23,110f | ? spot   +0.2% din   ref 17d
LEG ▲ 09:35–10:35 +246   (zigzag)
  09:50–10:05  ▲113  [kharid 58% s0.2 GC]  shaant ✓
  abhi ▼44  18% wapas 10:40 se  [bech 65% s0.7 GC]  1.1×(s0.2)
  rasad  flow 10:29 (grey)  OI 10:35 (grey)  fut ?  BNF ✓
KAUN DABA RAHA   (aaj 1.2× · GC · bad mein aaya)
        5m      15m     pichle45
  pace  1.2×(s0.2)  1.1×(s0.2)  1.3×(s0.4)
  tilt  [bech 63% s0.3 GC]  [bech 64% s0.7 GC]  [kharid 58% s0.3 GC]
  burst 10:55  2.2×(s0.7)  [bech 74% s0.9 GC]  ▼8  px ✓
KAUN LIKH RAHA   (aaj 2.4× · bad mein aaya)
  CALL  +79L  [−91L(p76) +40L(p62) −18L(p31) +79L(p72)]
  PUT  −6.7L  [+116L(p82) +88L(p87) +27L(p46) −6.7L(p7)]
  fut OI  −0.2L · 09:50 tak
DOOSRE INDEX   (bad mein aaya)
  BANKNIFTY  ▼0.1%  NIFTY se −0.29%
  pace  1.0× · 09:33 tak  call likh
  SENSEX  ▲0.3%  = NIFTY
SIRF BADE   (P phase · R roka · T thakan · Z zor · B bada · ✕ toota)  +6 aur
  10:50 B Bada seller 23,092f 20K
  10:45 T Sellers thake 23,080f
  10:40 Z Sellers ka zor 23,095f
PLAN  
  ? plan: fut ticks 26/36 nahi
? READ 09:50 se ruka · +3 …
```

- **LEG**: up main leg (zigzag, threshold 50 pts, ATM IV 0.132 at 09:48) from 22,908 at 09:35 to the extreme 23,155, last tested 10:35 = +246.5; now 23,110, pullback -44.4 (18% back) since 10:40
  - pullback tilt: GC b1007 s1852 (-0.30, p88) → ✓
  - stretch 09:50→: +112.8 pts; tilt GC b1571 s1122 (+0.17, band 0.27) → shaant
  - rasad (main leg): flow 10:29, oi 10:35, fut ?, bnf {"word": "\u2713", "nifty_t": "10:36", "near": 55863.2, "ext": 55863.2, "tol": 27.9316}
- **pace 5m** (GC): lots 530 (b 197 / s 333) → x 1.20, p57 of 17 days, tempo 1.17, level 0
- **pace 15m** (GC): lots 1781 (b 649 / s 1132) → x 1.07, p52 of 17 days, tempo 1.17, level 0
- **pace pichle45** (GC): lots 8982 (b 5189 / s 3793) → x 1.31, p76 of 17 days, tempo 1.20, level 0
- **tilt 5m**: GC b197 s333 -0.26 (band 0.38) → GC
- **tilt 15m**: GC b649 s1132 -0.27 (band 0.27) → GC
- **tilt pichle45**: GC b5189 s3793 +0.16 (band 0.21) → GC
- **ladder words at T, T−1, T−2 evaluations**: pace [None, None, None] · tilt [None, None, None]
- **burst**: `{"t": "10:55", "x": 2.199015693306541, "p": 85.6, "n": 17, "buy": 208.0, "sell": 607.0, "dpx": -7.900000000001455, "ulta": false, "old": false}`
- **CALL**: 15m +79L (p72 of 29 days, tempo 2.42), quarters oldest→newest -90.9 +39.6 -17.8 +79.0, hour-gross p51, word at T−10/T−5/T [None, None, None] → None
- **PUT**: 15m −6.7L (p7 of 29 days, tempo 2.42), quarters oldest→newest +116.1 +87.9 +27.2 -6.7, hour-gross p53, word at T−10/T−5/T ['dheema', None, None] → None
- **fut OI**: none
- **BANKNIFTY**: din -0.05%, spread -0.29% p73 of 22 days, confirm None
- **SENSEX**: din +0.32%, spread +0.08% p67 of 21 days, confirm None

### 2026-10-19 14:30 (EXPIRY day)

```
NIFTY  RIDE ▼ 13:15 se · 1h15  EXP   14:30
  22,888f | ≈22,860s   -1.2% din   ref 12d
LEG ▼ 13:15–14:25 -69   (READ)
  13:15–13:30  ▼53  [bech 66% s0.8]  ✓ saath
  abhi ▲17  24% wapas 14:25 se  [bech 51% s0.1]  1.0×(s0.1)
  rasad  flow 13:37 (grey)  OI 13:40 (grey)  fut —  BNF ✗ (red)
KAUN DABA RAHA   (aaj 0.8×)
        5m      15m     pichle45
  pace  1.0×(s0.1)  1.1×(s0.2)  0.9×(s0.1)
  tilt  [bech 51% s0.1]  [ulte bech 52 | kharid 53]  [kharid 52% s0.2]
  burst 14:25  2.1×(s0.7)  [ulte bech 53 | kharid 66]  ▼19  px ulta
KAUN LIKH RAHA   (aaj 2.6×)
  CALL  +54L  [+60L(p79) +90L(p79) +23L(p39) +54L(p58)]
  PUT  +17L  [+59L(p82) +102L(p90) +11L(p22) +17L(p26)]
  deewar  PUT 22,750–800*  +64L  56 neeche
  deewar  CALL 22,850  +41L  6 neeche
  nikal  PUT 22,900  −31L  43 upar
  fut OI  +0.1L  shaant ✓
DOOSRE INDEX
  BANKNIFTY  ▼0.3%  NIFTY se +0.85%  low ✗
  pace  0.4×(s0.0)  OI shaant ✓
  SENSEX  ▼1.2%  = NIFTY  low ✓
SIRF BADE   (P phase · R roka · T thakan · Z zor · B bada · ✕ toota)  +13 aur
  14:25 B Bada seller 22,878f 14K
  13:20 Z Sellers ka zor 22,915f
  13:20 Z Sellers ka zor 22,888f ×2
PLAN  TREND
  SELL ▼ ARMED  22,923–23,002f  ≈22,900–22,980s
  KILL VWAP  23,002f  ≈22,980s
  T1 −2σ  22,844f  ≈22,820s
? 25 chhote marks
```

- **LEG**: down main leg (READ, threshold 72 pts, ATM IV 0.352 at 14:29) from 22,940 at 13:15 to the extreme 22,871, last tested 14:25 = -69.0; now 22,888, pullback +16.9 (24% back) since 14:25
  - pullback tilt: GC b314 s350 (-0.05, p16); UX b321 s340 (-0.03, p7) → shaant
  - stretch 13:15→: -53.1 pts; tilt GC b741 s1858 (-0.43, band 0.27); UX b894 s1702 (-0.31, band 0.38) → ✓
  - rasad (main leg): flow 13:37, oi 13:40, fut never, bnf {"word": "\u2717", "nifty_t": "14:27", "near": 55438.7, "ext": 55369.2, "tol": 27.6846}
- **pace 5m** (UX): lots 662 (b 321 / s 340) → x 0.98, p48 of 13 days, tempo 0.82, level 0
- **pace 15m** (UX): lots 2670 (b 1420 / s 1248) → x 1.14, p57 of 13 days, tempo 0.82, level 0
- **pace pichle45** (UX): lots 4156 (b 2410 / s 1734) → x 0.86, p30 of 12 days, tempo 0.85, level 0
- **tilt 5m**: GC b314 s350 -0.05 (band 0.38); UX b321 s340 -0.03 (band 0.47) → agree
- **tilt 15m**: GC b1277 s1393 -0.04 (band 0.27); UX b1420 s1248 +0.06 (band 0.38) → ulte
- **tilt pichle45**: GC b2150 s2006 +0.03 (band 0.21); UX b2410 s1734 +0.16 (band 0.29) → agree
- **ladder words at T, T−1, T−2 evaluations**: pace [None, None, None] · tilt [None, None, None]
- **burst**: `{"t": "14:25", "x": 2.135945101852319, "p": 85.7, "n": 13, "buy": 765.0, "sell": 388.0, "dpx": -18.599999999998545, "ulta": true, "old": false}`
- **CALL**: 15m +54L (p58 of 27 days, tempo 2.60), quarters oldest→newest +60.2 +90.5 +23.4 +54.1, hour-gross p56, word at T−10/T−5/T [None, None, None] → None
- **PUT**: 15m +17L (p26 of 27 days, tempo 2.60), quarters oldest→newest +59.2 +102.5 +10.9 +16.7, hour-gross p54, word at T−10/T−5/T [None, None, None] → None
- **token** PUT 22,750/22,800: +64L, p94, 58% of the side gross → deewar
- **token** CALL 22,850: +41L, p87, 49% of the side gross → deewar
- **token** PUT 22,900: −31L, p85, 28% of the side gross → nikal
- **fut OI**: UX 15m +0.05L, p8 of 12 days
- **BANKNIFTY**: din -0.31%, spread +0.85% p100 of 17 days, confirm low ✗
- **SENSEX**: din -1.23%, spread -0.08% p71 of 17 days, confirm low ✓
