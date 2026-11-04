# Option order-flow reader: design (Sonnet, clean room, 4 Nov 2026)

Files here: `mockup.html` (standalone, real data), `mockup.tpl.html` (template), `export.py` (builds the data and the page), `data_2026-11-03.json`, `data_2026-11-04.json`.
Rebuild with `python -I -X utf8 export.py` (read-only on `data/`; re-run for a fresher 4 Nov). NIFTY only: SENSEX runs the same engine but is not exported.

## The principle

**Options are the WHO, not the WHEN.** So the screen never says "go". It answers, in this order: *who is on each side right now (and is it real), is anyone running (covering), where is the wall and which side stopped first, is anything abnormal for that strike's own day.* Every number is read against the strike's own day-normal and its own premium VWAP bands; nothing is read against a fixed threshold except the two she already trusts (1.5L OI move, 2,000 delta-lots).

Direction A (recommended): **one answer strip, one strike ladder (CE | strike | PE), a drill-down for one strike.** The Float (440 px) is the same data cut to six cells, a pullback check, ATM +/- 2, the walls and the last four changes.
Direction B ("B: Kya badla"): the same engine as **a change log**, one line per event, newest first. Cheaper to glance at in a long session; worse for "which strike" questions. Kept as a second tab, not a second product.

Light mode, grids and pills, cells of six words or fewer, Hinglish chip with a number on every symbol, every level tagged `s` (spot) or `f` (futures), no price or premium candles, no %, no win rates, no order button. The scrubber (arrow keys too) steps her 3-min closes; every number on screen uses data up to that close only. A mark's outcome appears only once the next close exists.

## Her ideas, and where each lives

| idea | form | how it appears | evidence reason |
|---|---|---|---|
| **short covering** | WORD + count | `bhaag rahe` chip (orange, the only outlined chip); strip cell "CE bhaag rahe x4 -46L, upar squeeze" when 3 or more strikes on one side cover at one close; "nahi (dekha)" when none; hatched "data nahi" when most strikes on that side have no flow. | The squeeze is seen HAPPENING (breaking strike, 3 to 5 strikes together), never forecast. |
| **who per strike** (likh / kharid / bhaag / nikal) | WORD | Chip with lakhs. Dashed border = not FIRM (label changes if the window shifts 1 min). | Her WHO grid, unchanged. |
| **own-day normal** | NUMBER | `pNN` beside every strike (max of volume and \|delta\| rank vs that strike's own earlier closes; bold from p80). `n/a` hatched before 6 closes. Implied delta also ranked against its own day. | `prints.pct_rank`, strict, minimum 6. |
| **change and rate of change** | NUMBER | Last 3 closes of dOI under each chip (`+5 +12 +31L`), `up-up` when it grows twice in a row; "palta" when implied delta flips; the drill-down lists 10 closes. | Her request; display only. |
| **own VWAP bands** | NUMBER + PILL | Premium with a triangle (above / below its own VWAP) and `u2 / u3+ / d2 / d3-` when the 3-min high or low touched that band. Not drawn before 09:44 (bands not yet readable). ATM CE and PE premium vs VWAP in the strip. | The study's "healthy pullback" tell: ATM premium holds above its own VWAP. |
| **absorption** | MARK | `ruka pNN` after a band touch with own-p90 effort and a small result; resolves to `tika` / `toota` only when the next close exists, else `agla close?`. | Held the band more often on 4 of 5 days, but unregistered and its first definition partly circular: a mark, never a sentence. |
| **exhaustion** | MARK | `thakaan`: new 6-close extreme with falling volume, delta and dOI. | Inconclusive, small n. |
| **climax** | MARK | `charam pNN`: beyond u3/d3 at own-p95 effort. Next close adds `delta palta` or `delta wahi`. | Same pattern was her 3 Nov 10:35 climax, a breakout at 13:17 and a day low on 2 Nov; only the next close tells. So never a word. |
| **ignition** | MARK | `bhadak`: own-p90 effort at/above u2 with writers covering. | Confirms a squeeze, never leads it. |
| **CVD / delta** | NUMBER | Per-strike aggressor delta each close; day CVD in the drill-down footer, as a count only. Implied index delta (lots) as the first cell. | CVD divergence flipped sign between days: no divergence mark. |
| **big prints** | MARK + cell | `bada print` cell and a pink diamond on the strike. Sized by delta-lots (qty x \|chain delta\| / 75 >= 2,000), then kept only if in the day's top decile (all of them while fewer than 10 exist). | By qty, 0DTE wings give 1,311 "big"; by delta, 16. On expiry day ITM options have delta near 1 so even delta-lots floods; the own-day filter handles it. |
| **stacked imbalance** | LEFT OUT | none | Did not separate. |
| **volume profile / premium POC** | LEFT OUT | Only day volume per strike in the drill-down (a number). | Premium POC did not separate. |
| **walls / trapped inventory** | WORD + NUMBER | Deewar #1/#2 per side (top two OI of the nine nearest strikes, her section 1d) with `badh raha / ruka / ghat raha` from the 6-min OI change, and "Pehle ruka: CE cap" (the fuel). Wall distance: `deewar paas / door`. | Her rule; wall distance is a regime read. |
| **pullback vs reversal** | 4 ticks | Leg (futures 15 min, at least 20f), then: defending writers still writing, the leg's ITM writers covering, implied delta with the leg, ATM premium above its VWAP. Shown as `n/4 pullback ke saath`, `ulta`, `dekha nahi`. | The 5-day study's list. Tagged [I]; two days; not a rule. |

## What she reads in 3 seconds

Top row, left to right: implied delta (sign, lots, own-day rank, "palta"), calls net chip, puts net chip, covering (yes / nahi dekha / data nahi), deewar #1 per side with its state, bada print count, ATM premium vs VWAP, wall distance. If one cell is orange, someone is running. Then the pullback strip. The ladder is for "which strike"; she clicks one for its last 10 closes.

## House rules, kept

- Three states are never merged: a value, `kuch nahi` (checked, found nothing), and a hatched `n/a` / `data nahi` (could not check: before 6 closes, before 09:44 for bands, strike with no flow file).
- Hinglish chip on each word, mark and wall; levels carry `s` or `f`; strikes are strikes, with steps from spot in `s`.
- No candles. Premium shows only as a number plus above/below its VWAP.

## 4 Nov 10:50 (real data, expiry 9 Nov)

Implied delta +24k lots (p80 of its own day); calls net `kharid rahe` +3.7L, puts net `nikal rahe` -2.8L (a buyer-led lift, not writers covering); no strike covering, shown as "nahi (dekha)"; deewar #1 24,000 CE (+2.7s) `badh raha`, 23,800 PE (-1.3s) `ghat raha`, so the floor stalled first; no big print; both ATM premiums still under their own VWAP (CE 186 vs 193, PE 179 vs 187). 23,900 CE is `shaant` +0.8L: the cap-breaks tell (OI falling with buyers lifting) has not appeared. Only the next closes can show it.

## Least sure of

1. **Big prints.** My level-qty bar finds 0 at 4 Nov up to 10:50, while her read says one 2,000+ delta-lot print. The footprint gives qty per price per minute, not single trades, so the two measures may differ.
2. **Own-day filter for big prints** (top decile, 10-print floor) is my choice, not the study's.
3. **Pullback ticks, the 6-min wall state and "squeeze = 3 strikes" thresholds** are display rules from two or three days, tagged [I].
4. **Absorption pending / resolved wording** shows next-close facts; it does not make the mark a signal.
5. Early closes (before 09:44): bands blank, ranks `n/a` until 6 closes. Fronts use chain OI over a 6-min window, which is coarse because exchange OI updates about every 63 s.
6. NIFTY only; SENSEX on NIFTY's flow (her section 1q) is not wired.

---

# Round 2: ONE READ (`mockup-v2.html`, v1 kept)

Mary: "i like some parts ... still lot of info to read, add it with jarvis reading once." I judged as a trader which parts earn their place.

## What stayed, what was cut

- **Stayed (the parts that earn it):** the WHO chips with a lakh number, the own-day rank `pNN`, the covering alarm, the top-two OI strikes (walls) with their state, "dekha, kuch nahi" versus "dekh nahi paaye", the scrubber.
- **Cut from always-visible:** the 9-cell answer strip (now one line under the lanes), the 4-tick pullback check (its ticks are the verdict pills when they matter), the 12-row 7-column ladder (now a two-row dot strip), the walls panel, the per-strike marks and band tags, the big-print and wall-distance cells, the change log as a screen.
- **Float, always visible, six elements:** (1) Jarvis's word and since-time; (2) nine vote pips; (3) two lanes, Jarvis vs options, with the verdict pills; (4) the strikes as shape; (5) the leg line; (6) the "ends:" line. A freshness bar sits on top and five tap buttons below.
- **Full page:** the same card plus a whole-day strip (Jarvis lane, options lane, a third thin "ghatna" lane) and one panel that is open by default (Strikes, ATM +/-3).

## Behind one tap

`Strikes` (ATM +/-3 table, chips, `pNN` only from p80, band tag only when touched, premium above/below its VWAP as a triangle), `Deewar` (OI top-2 per side), `9 reads` (Jarvis's pieces verbatim in four states), `Kya badla` (one stream: Jarvis word changes and option events), `Gaps`. Marks (absorption, climax, ignition) and big prints live in the Strikes panel and the day strip, and in the stream.

## How Jarvis and option flow read as one

- **One headline, Jarvis's word.** The option flow never gets its own word. It is the WHO behind it: a caption under the lanes, `options up +24k lots, p80, since 10:47, CE kharid rahe +3.7L`.
- **Two lanes of the same columns (her closes).** Top lane Jarvis's lean (green up, red down, hollow none, hatched no row), bottom lane the option-flow stance (own-day-ranked implied delta; hollow = checked, no side; hatched = could not check). A **black frame on both cells = the two disagree at that close.** Disagreement, and who flipped first, is a position on a strip, not a sentence.
- **Verdict pills, only what differs or is unconfirmed:** `SAHMAT up` / `ALAG: Jarvis down, options up`; then caveats the options do not confirm: `kharid rahe, cover nahi` (buyers lifting, not writers covering), `ATM prem < apna VWAP`, or the orange `CE bhaag rahe x4` when 3 or more strikes cover (the squeeze is happening).
- **The dot strip** replaces the ladder: CE row over PE row, 11 strikes, dot colour = who (same chip colours), size = size of the OI change, dashed hollow = not firm, hatched square = no data; a bar under the top-OI strike (blue building, orange unwinding); spot as a black line.
- **Borrowed from the other Jarvis panel:** the four vote states (with / against / flat / blind) with their own shapes, the freshness bar (REPLAY, LATEST CLOSE; STALE and NO FRAME cannot be judged from files), and the Hinglish glosses.

## The "could not check" fix

Jarvis lumps flat and blind in one "?". Here: filled pip = with or against; hollow pip with a solid edge = **flat, checked, found no side**; hatched amber dashed pip = **blind, the engine said "could not check"**. This works only where the piece text exists: the five 3 Nov moments (09:29, 10:11, 12:12, 13:20, 14:30), shown at the close that equals the minute or follows it by up to 2 min. Everywhere else the daily call log carries counts only (with, against, N), so the rest is drawn as a **third look, neutral hatched grey "? (alag nahi)"**, which can be mistaken for neither flat nor blind, and the Reads panel says why. The engine should send a `state` per piece; that is the real fix. The same split applies to the option side: `kuch nahi (dekha)` pill versus hatched `dekh nahi paaye` (too few strikes, before six closes for the own-day normal, band not readable before 09:44, strike with no flow file).

## 4 Nov at 10:50, what the files say

The brief's example (HOLD down) is the earlier call: Jarvis said HOLD down until 10:46, PALAT? down 10:47 to 10:49, and **PALAT up since 10:50** (2 with, 1 against, 6 unread). Option flow turned up **at 10:47**: three minutes before Jarvis. They agree at 10:50. The tell the options add: the lift is buyers (`CE kharid rahe`), no strike covering, and both ATM premiums are still under their own VWAPs, so it is not yet a squeeze. The lanes show the 10:47 to 10:49 disagreement as framed columns.

## Least sure of (round 2)

1. **Lane stance rule** (own-day rank at least p50, sign of implied delta) is mine; a quiet close shows hollow even when the day's trend is clear.
2. **Three looks for "?"** because the daily log has no per-piece state; the proper fix is on the engine side.
3. **Pieces for 12:12 and 14:30** appear at the closes 12:12-12:14 / 14:30-14:32 as recorded; they are not re-derived.
4. **Dots at a glance** are weaker than the table when the market is quiet (most dots tiny grey), by design, but she may want one more cue for the loudest strike.
5. Jarvis rows are minute rows `t`; the call for minute `t` was shown about a minute later, so the live screen lags the scrubber by that much. Not corrected.
6. NIFTY only. Jarvis files are read directly; `/api/jarvis` was never called.
