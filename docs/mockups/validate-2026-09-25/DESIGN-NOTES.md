# Validate tab + Hold / Fold window: design notes

File: `validate-design.html` (self-contained; Google Fonts + Lucide 0.469.0 from jsDelivr).
Data: the three real replies in this folder, injected verbatim between the `/*__DATA__*/`
and `/*__END__*/` markers. GO and NO are marked ILLUSTRATIVE on screen (see below).

Deep links for review: `#empty` `#loading` `#c0943` `#c0935` `#go` `#no` `#in` `#fcol` `#fopen`.
Add `:deep` to any of them to open the detail (e.g. `#in:deep`).

---

## Step 1: Direction

**Aesthetic, in one line:** a Swiss railway departure board printed on a trade slip. Warm
paper and black ink, one word set at 88 px, and colour only when the verdict speaks.

The broker chart beside it is loud. This screen stays quiet, so the one loud thing on it
(the word) is readable from across the desk in under two seconds.

### Palette (light only)

| Token | Hex | Role |
|---|---|---|
| `--bg` | `#F3F1EB` | warm paper; the page |
| `--surface` | `#FAF9F5` | the slip column, the app bar |
| `--surface-raised` | `#FFFFFF` | the verdict band, the inputs, the float |
| `--surface-sunk` | `#EAE7DF` | hover wash, skeletons |
| `--border` / `--border-strong` | `#DCD7CC` / `#B8B1A3` | hairlines / control edges |
| `--text-primary` | `#17160F` | ink; section rules (2 px) and selected segments |
| `--text-secondary` | `#4A463E` | sentences |
| `--text-muted` | `#736D62` | labels, `[M]`/`[I]` tags |
| `--accent` | `#2441A3` | **her hand**: the VALIDATE button and the focus ring, nothing else |
| `--positive` | `#1A7641` | GO, HOLD, ✓ |
| `--caution` | `#A35E00` | WAIT, WATCH |
| `--negative` | `#B3261E` | NO, FOLD, ✕, and the red header (NO / FOLD only) |
| `--unknown` | `#6B665E` | PATA NAHI |

**Why ink-blue is the one accent.** The screen gives her a market verdict in green, amber
and red. Her own action has to be a colour that can never be read as a verdict. Blue ink is
the colour of her hand on the slip, and it appears on exactly one control: the button she
asked for. Everything else she touches (the selected segments, I'M IN) is black ink.

### Fonts: three jobs, three faces

- **Barlow Condensed 600/700** sets the app's *vocabulary*: GO / WAIT / NO,
  HOLD / WATCH / FOLD / PATA NAHI, WITH YOU / AGAINST / NEITHER, GIVING WAY / DEFENDED. Its
  shapes come from road signage, and condensed caps make a tall word that still fits the
  column. That is what "from across the desk" needs.
- **IBM Plex Sans 400/500/600** sets sentences and labels. The server's fact sentences are
  long, and they need a calm, open text face.
- **IBM Plex Mono 400/500** sets every number and time. The figures are tabular, and it is
  the same family as Plex Sans, so the two sit together.

Rule: a word from the vocabulary is Barlow, a sentence is Plex Sans, a number is Plex Mono.

### Scales

- Spacing: 4 / 8 / 12 / 16 / 24 / 32 / 48 (`--s1`…`--s7`), used exclusively.
- Type: 11 / 12 / 14 / 16 / 20 / 28 / 40 / 56 / 88 (`--t11`…`--t88`).
  - 88: the verdict word.
  - 56: the word in the float.
  - 40: the count.
  - 28: the number she acts on.
  - 11: the tags.
- Radius: 4 on controls, 6 on the band and the float. Nothing above 12.
- Motion:
  - 160 ms `cubic-bezier(.2,0,0,1)` on hover and active;
  - a 180 ms fade when an answer lands;
  - a slow opacity pulse on the loading skeleton;
  - all of it off under `prefers-reduced-motion`.

### Layout at 1536 × 695

The slip (296 px): index, strike (the ATM strike marked), CE/PE, BUY/SELL, qty, VALIDATE,
then "Took it?" with the fill time, fill price and I'M IN.

The answer, top to bottom:
1. The echo line: exactly which contract this answer is for.
2. The verdict band: WORD | count + "a count, not odds" | sentence + "what would have to
   change".
3. The five facts (flexible width) beside the numbers (336 px: STOP, NEXT WALL, PREMIUM,
   DELTA).
4. A sticky "Deeper detail" bar.

Everything she acts on sits above 695 px, and the detail is one click away. The layout is
asymmetric on purpose: the eye goes word → count → sentence → facts, and the numbers wait
on the right.

In a trade the same tab swaps:
- the slip becomes her marked trade, plus a legend of the four hold words;
- the facts become "what it said since you entered".

### How each of her hard rules is met

- **Light only.** No dark styles exist.
- **No charts.** Nothing draws price. "Since you entered" is a list of time ranges, not a
  bar.
- **No %, no probability, no confidence.** The count is the only score, labelled "a count,
  not odds" everywhere it appears. (See the open question on "24% off" below.)
- **No size, no order.** Qty is her input. "Nothing is sent to your broker" appears in the
  app bar, under VALIDATE, on the trade card and in the float footer. I'M IN only marks a
  trade.
- **P&L** is never on the collapsed line. In the open views it is 12 px, secondary ink, no
  colour, tagged `[I]`.
- **Three absences, three looks, none of them a zero:**
  - `checked, none`: a solid border and the search-x icon ("we looked; empty");
  - `could not check`: a dashed border, italic, and the eye-off icon ("we could not see");
  - `not shown`: a hatched fill and the ban icon ("withheld on purpose").
- **`[M]` / `[I]`** on every measured or inferred number, taken from the reply's own `tag`
  fields. Her own inputs (strike, qty, fill) are labelled "your fill" instead: they are
  neither measured nor inferred by the tool.
- **DRAFT** stamp in the app bar and in the float footer, so it survives the pop-out. Its
  tooltip carries the pre-registration line.
- **Colour** only on the verdict word, the ✓ / ✕ / – marks (Lucide `check` / `x` / `minus`),
  and the red header for NO and FOLD.
- **Indian formatting** via `Intl` `en-IN`: 23,121.6 · ₹2,881 · ₹1,339.

### States in the file

**A · Before:**
- empty (explains GO / WAIT / NO and names the five facts);
- loading (skeleton, button reads CHECKING…);
- 09:43 WAIT 4/5 and 09:35 WAIT 1/5 (both real);
- GO and NO (both illustrative).

**Live states:**
- stale: change any control after an answer and the answer dims, with "press VALIDATE
  again";
- a contract that has no reply here: SENSEX or BANKNIFTY, or another strike → a `not shown`
  answer.

**B · In:** the 10:00 hold (real): HOLD since 09:56, the runs, the numbers, and the rows,
plan and side read in the detail.

**C · Window:**
- collapsed to one line: `HOLD · NIFTY 23200 PE · line 23,121.6 · 65 pts room · checked,
  none against · since 09:56`;
- open, 400 px wide;
- hidden on the Validate tab;
- the ⧉ button pops it out through Chrome Document Picture-in-Picture. The same element
  moves into the pop-out and back, and there is a message when the API is missing.

**The illustrative verdicts, exactly what was changed:**
- **GO** is the 09:43 reply with Room to run set to *neither*, and a sentence that states
  the GO rule.
- **NO** is the 09:35 reply with Your setup read from the real 09:39 `BUY d2` arm in the
  09:43 reply's `zone.arm`, marked *against*. That gives 3 against.

All other texts and numbers are the real replies.

---

## Step 4: Self-critique (a harsh design lead, first build)

1. **The BUY/SELL control ran together as "BUYlong SELLshort".** The qualifier was jammed
   inline in a 70 px segment, and it looked unfinished.
   *Fixed:* the segment stacks the verb over a small qualifier (`BUY` / `long`).
2. **The count jumped sideways between states.** The word column was sized to the word, so
   GO, WAIT and HOLD each put "4 of 5" at a different x. Across a desk that reads as a
   layout glitch.
   *Fixed:* fixed minimum tracks (256 / 200 px), so word, count and sentence hold the same
   edges in every state.
3. **The numbers column did not share the grid.**
   - The facts opened with a heavy 2 px rule; the numbers had none, and the two columns
     started at different heights.
   - A stray right-aligned "INDEX LEVEL" read like a second column header.

   *Fixed:*
   - a shared 2 px rule with the labels on one baseline;
   - "STOP · index level" as one label;
   - tighter number blocks, so PREMIUM and DELTA clear 695 px even on the tall 09:35
     answer.
4. **The detail and the float were squeezed tables.**
   - The rows (LINE / PAYERS / …) were a four-column grid inside a 350 px column. That left
     160 px of text and five-line wraps.
   - The float's run list collapsed into stacked blocks, and the window was 670 px tall.

   *Fixed:*
   - the detail rows are two lines each (NAME · STATE, then the fact);
   - in the float, the runs are single ellipsised lines and the contract moved into the
     header (641 px);
   - the collapsed float stays one line and never shows P&L.
5. **Small things that looked amateur:**
   - "of" vanished on the red NO band (a specificity bug);
   - the empty state numbered STOP / WALL / PREMIUM / DELTA as if they were steps;
   - the native time picker clipped "09:44:0";
   - the in-trade slip was 300 px of dead paper.

   *Fixed:*
   - the contrast on the red band;
   - an unnumbered list for the numbers;
   - picker chrome removed from the inputs;
   - the slip now carries the legend of the four hold words (HOLD / WATCH / FOLD / PATA NAHI),
     which is also where PATA NAHI gets taught.

Also fixed along the way:
- at 1024 px the three-across number blocks collided; they are now two-up and wrap;
- the "Deeper detail" bar fell below 695 px on 09:35; it is now sticky;
- on narrow screens, the answer scrolls into view after VALIDATE;
- checked for horizontal overflow at 375 px in every state: none.

---

## Open questions for Mary

- **"(24% off)" / "(25% off)"** appears inside the server's own fact sentences. It is OI
  given back, not a probability, and it is kept verbatim because it is server text. If the
  "never a percentage" rule covers it too, the fix belongs in the server's sentence, not in
  this screen.
- The pop-out needs one click in real Chrome (116+). It could not be exercised headless;
  the code follows the documented `documentPictureInPicture.requestWindow` pattern.
