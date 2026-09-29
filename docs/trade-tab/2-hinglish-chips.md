# Trade tab: 2. Hinglish chips

**Her ask (2026-09-29, after the close):** "i have really this problem of remembering these symbol that why i want a chip so that i understand whats its telling in hinglish would be much better"

**The rule:** every symbol on the chart can be read without the key.
- A line always carries a chip at the right edge.
- A point mark (▲▼ ▬ P A E C) carries a chip beside its glyph. It shows by default when the mark is among the newest 6, or when it sits at a named level. Every other mark shows its chip on hover.
- Chips stack; a chip that still collides is dropped and its glyph stays.
- Point glyphs and their chips fade with age.
- **CHIPS**, a toggle on the strip, is on by default. Off, the lines carry plain numbers.
- The left panel's key becomes a Hinglish glossary. The engine's sentences in the left panel stay verbatim, in English.

## How each side was checked (so a chip can never contradict its source)

| mark | source | what `side` means | checked in |
|---|---|---|---|
| ▲▼ won | engine (`fold.py`) | the winner. Text: "sellers won at 22716 …" | `fold.py:470,474` |
| ▬ absorbed | engine | the **absorbed** party. Text: "165 lots of sellers absorbed at 22700". The holder is the other side, and the engine's own level text for the same run says "165 lots of buyers held". | `fold.py:472, 531` |
| ═ trapped | engine | the trapped party. Text: "429 lots of buyers trapped at 22728" | `fold.py:344` |
| P | extension (`board.js`) | +1 means "bought at the prior bar's high, price now below them": trapped **buyers**, so a possible **top**. −1 means trapped sellers at a low, so a possible bottom. **`/api/tape` stores this raw side**: the tape posts `m.local.events` (`main.js:220 → :269`). GoCharting **paints** P by the flipped side (`main.js:169`), the side that won there, so a buyers-trapped P is red on her chart. The tab flips P's **colour** only (`chips.paintSide`), never its words. | `board.js:96-97`, `shell/main.js:169, 220, 269` |
| A | extension | the **defender**. +1: "sold at X and the bar closed above it: buyers defended". | `board.js:85-89` |
| E | extension | −(the leg's direction). −1 means a new high on weak volume: the buyers are tired. | `board.js:112` |
| C | extension | 0: unresolved | `board.js:93` |

**P, settled 2026-09-29 (supervisor, after a retraction).**
- The words follow board.js's raw side: +1 = buyers trapped = top.
- The colour follows GoCharting: +1 is painted red.
- Every P today is +1, each at the prior 5m bar's high (22618 against 22622 at 10:00; 22705 against 22704 at 15:15).
- **The fact first, the prediction only at a swing extreme (supervisor, final).** The chip always says who is trapped. It adds "· top ban sakta" (or "· bottom ban sakta") only when the P sits within max(2 × rowSize, 0.25 × range) of the highest high (lowest low) of the chart's up-to-12 bars already closed before it. The range is those bars' high to low, and at least 3 bars are needed. Everywhere else the chip adds "(chhota trap)".
- It is labelling, not a verdict, and it never looks ahead.
- A named level makes the glyph heavy, never the words.
- **Today at 5m (rowSize 5):**
  - the 10:10–10:30 P's (22612–22618) sit 108–145 pts under their hour's high, so they read "(chhota trap)";
  - the 15:20 P at 22705 is 9.8 pts under the hour's high of 22714.8, inside the 15.2 tolerance, so it reads "· top ban sakta".
  - On 3m the bars are the last 36 minutes, so the label can differ.

**The words are the Events tab's own** (`hinglish.ts`, read through `glossOf`). Her ask was "the chip it used to produce earlier was good all that you find will find in event tab". The reused captions are:
- MAAL KHAPAYA (absorption);
- THAKAN (climax);
- TRAP;
- DUM NAHI (the Events tab's word for a new level without flow, used for exhaustion);
- "sahara" (ROLE-FLIP);
- "khula" (SQUEEZE-KHULA).

Words are invented only where the Events tab has none: fights won, NEXT FIGHT, walls, her trade, and zone entries.

**The contradiction guard.** An engine chip is built from the mark's `side` only when the engine's own text names the same party. Otherwise the chip shows the engine's words unchanged.

## The vocabulary

| symbol | chip (Hinglish) | colour | example today | tag |
|---|---|---|---|---|
| ▲ fight won, buyers | **Buyers jeete · 22637** | teal | 11:10 "Buyers jeete · 22637 (sirf price se)" | [M]; "(sirf price se)" is [I] |
| ▼ fight won, sellers | **Sellers jeete · 22614** | red | 10:02 | [M] / [I] |
| ▬ held (engine, book) | **Buyers ne roka · 165 lots** / **Sellers ne roka · 202 lots** | the holder's | 09:19, "165 lots of sellers absorbed" → "Buyers ne roka · 165 lots" | [M] |
| ═ trapped, not released | **Buyers phase · 429 lots** / **Sellers phase · … lots** | the trapped side's | 12:28 at 22728 | [M] |
| ═ released (hover only) | **Sellers ka trap khula · 22612** | the side named | 11:02 | [M] |
| P (footprint, yours) | **Buyers phase (P) · 22618 (chhota trap)** / **Buyers phase (P) · 22705 · top ban sakta** / **Sellers phase (P) · … · bottom ban sakta** | GoCharting's: the flipped side, so buyers-trapped is red | 10:10 and 10:30: "(chhota trap)"; 15:20: "Buyers phase (P) · 22705 · top ban sakta" | [I] |
| A (footprint, yours) | **Buyers ne maal khapaya (A) · …** / **Sellers ne maal khapaya (A) · 22615** | the defender's | 10:05 at B 22620: side −1 | [I] |
| E (footprint, yours) | **Buyers ka DUM NAHI (E) · 22695** / **Sellers ka DUM NAHI (E) · 22672** | the extension's side colour | 09:20 at S 22675 → "Sellers ka DUM NAHI (E) · 22672" | [I] |
| C (footprint, yours) | **THAKAN (C) · 22616** | grey | 15:20 | [I] |
| ━ NEXT FIGHT | **Agli ladai upar · 22728** / **Agli ladai neeche · 22701** / **Ladai yahin · 22899** | ink | flat, live only | [M] |
| ┈ a named wall (flat) | **22750 CE writers ki deewar**, plus " · badh rahi / ruk gayi / hat rahi" when a state exists | grey | 22750 CE, 22650 PE | [M] |
| GAVE UP (flat) | **Sellers ne haar maani · 22907 · 11:42** | ink | none today | [M] |
| ▸ her entry | **Aapki entry · 113.95** (a faint line at the future's price when she marked) | ink | 22800 PE | [M] |
| ╌ give-up | **Yahan galat · 22711** | the engine's word: ink HOLD · amber PAST GIVE-UP · red FOLD · grey CAN'T CHECK | review of the 22800 PE | [M] |
| ┈ W, the wall behind | **Peeche ki deewar (sahara) · 22700 CE**, plus " · badh rahi" | grey | "· badh rahi" (W.state = building) | [M] |
| ┈ A, the wall ahead | **Aage ki deewar · 22600 PE · 21 pts**, plus the state after her restart | ink | 22600 PE | [M] |
| ○ OI event on W | **22700 CE writers hat gaye · 11:42 (−4.1%)** | ink | none today | [M] |
| ■ FOLD | **FOLD yahan · 13:45** | red | none on the chart today | [M] |
| zone entry | **Zone BUY d2 · 09:39 · 3m** / **Zone SELL u2 · 12:18 · 3m** | teal / red | both, today | [M] |
| closed trade hairline | **Entry 22800 PE · 09:18** / **Nikle · 09:35** | grey | today | [M] |
| pivots | quiet number chips: **S1 22697.2** | grey | reference, not a read | [M] |

The state words map W's vocabulary: building → "badh rahi" · stopped → "ruk gayi" · off → "hat rahi".

## The glossary (left panel, one line each)

- ▲ ▼ — ladai kisne jeeti (engine) · "sirf price se" = [I]
- ▬ — roka: ek taraf ka bada order doosri taraf ne khapa liya (engine, book)
- ═ — phase hue log, abhi nikle nahi (engine)
- P — TRAP: kaun phasa · top / bottom ban sakta sirf pichhle 12 bar ke high / low par, warna chhota trap (footprint)
- A — MAAL KHAPAYA: kisne saara maal khapaya, bhaav hila nahi (footprint, aapka)
- E — DUM NAHI: naya high / low, flow saath nahi (footprint)
- C — THAKAN: move ke aakhir mein sabse tez volume (footprint)
- ━ — agli ladai: upar / neeche
- ┈ — writers ki deewar (strike + basis) · peeche = sahara, aage = rok
- shaded — aapka zone, 3-min (d2→d3 buy · u2→u3 sell)
- ▸ — aapki entry · ╌ yahan galat (give-up)
- The P, A, E and C chips are the extension's read [I]; the rest are the engine's.

## Built, 2026-09-29 evening

**Where it lives:**
- `ui-v2/src/trade/chips.ts`: the words, the side mapping, the contradiction guard, and the glossary.
- `LevelsOverlay.ts`: the placement.
  - Line chips sit at the right edge. They stack one chip-height with a leader, or are dropped.
  - Point chips try right, above-right, below-right, then left. A chip that fits nowhere is dropped; the glyph stays.
  - Age fade runs from 1.0 when new to 0.4 at four hours.
- `Side.tsx`: the glossary, headed NISHAAN KA MATLAB.
- `Callout.tsx`: the hover card shows the chip, with the engine's own sentence under it.

**Other changes:**
- The mid-chart labels are gone: NEXT FIGHT, give-up, W/A and trapped-shelf text.
- **CHIPS** is on by default and remembered in `localStorage` as `trade.chips`. Off gives 0 point chips and number chips on the lines.

**Measured chip counts.** The overlay canvas carries a `data-chips` attribute with them. With the defaults, today (NIFTY, after the close):

| view | chart size | line chips | point chips shown, of point marks in view | zone entry pills |
|---|---|---|---|---|
| 5m | small pane, about 430 px wide | 7 | 6 of 51 | 2 |
| 5m | about 970 px wide | 7 | 9 of 51 | 2 |
| 5m | as in `shots/nifty-5m-chips.jpg` | 7 | 11 of 51 | 2 |
| 3m | as in `shots/nifty-3m-chips.jpg` (the chart opens on 09:15–12:45) | 7 | 11 of 33 | 2 |
| `?tradeview=` 5m | as in `shots/tradeview-NIFTY-22800PE-chips.jpg` | 7 | 13 of 51 | 2 |

- The 7 line chips at 5m flat are: 2 walls, the trapped shelf, NEXT FIGHT up and down, S1 and S2.
- The 7 in the tradeview are: entry, give-up, W, A, the shelf, and 2 pivots.
- Hovering a bar adds the chips of its marks (6 → 8 in one check).

Screenshots: `shots/nifty-5m-chips.jpg`, `shots/nifty-3m-chips.jpg`, `shots/tradeview-NIFTY-22800PE-chips.jpg`. They were re-taken after the Events-tab wording and the P colour fix.
