# BOARD and WAR, reviewed as the trader at the desk — Fable 5.1, 2026-09-24

**What I reviewed.** `docs/mockups/board-chess-2026-09-24.html` and `docs/mockups/war-compact-2026-09-24.html`,
their notes, the generator, `docs/research/quant-tower-india-2026-09-24.md`, `fronts.py`, research-findings §1d,
and the memory files named in the brief. Both pages rendered **light** (both files open with `data-mode="light"`;
the BOARD note still says dark is the default — the note is stale, the file is right) at **1600×900**, at
13:36 and 15:29 on NIFTY, at 09:20 and 10:36 on NIFTY, at 12:36 and 13:36 on BANKNIFTY, at 13:36 on SENSEX, and
WAR at 13:36 and after close on all three. I clicked the bookmarks, scrubbed from a move, hovered a move (guide
drawn), hovered and pinned on the WAR map (readout and the ladder's dashed cursor bar appeared), and switched
index and view. Every number I quote below I read off the page or out of the embedded record. Nothing was
edited, nothing restarted, no writes anywhere but this file.

Her ask was a chess board: what has happened, what is happening, what can happen. My ratings are against that
ask and against her rules, not against the effort. The effort is obvious. The scores are not.

---

## 1. Ratings

| criterion | BOARD | WAR |
|---|---|---|
| Answers the trader's question in 3 seconds | **6** | **7** |
| Tells the truth, including the honest absences | **7** | **9** |
| You could act on it | **5** | **6** |
| Readability and density on a laptop | **4** | **7** |
| Faithful to HER rules | **7** | **8** |
| Looks and feels like a prop-desk tool, not a data dump | **6** | **8** |
| **Overall** | **6 / 10** | **7.5 / 10** |
| **The two together, BOARD as main page with WAR as its drill-down** | **6 / 10** | |

### BOARD, line by line

- **3 seconds — 6.** The 22px sentence at 13:36 (*"Sellers pressing into PE 23400 writers who stopped adding
  at 13:31 — no defender building at 23400"*) reads in one breath and is in her order: aggression, who pays,
  response. That is the right first line. But the eye does not stop there: the board panel under it is 60% of
  the page and is the noisiest thing on it (see §2.1), and the engine box top-right shares the answer row and
  competes with the sentence. On 339 of 375 replay minutes that box is an apology (*"not recorded … could not
  check"*), so on most scrubs the prime top-right slot carries no information.
- **Truth — 7.** The absences are kept apart and named: UNGROUNDED with the reason, *"fronts forming — 6 of 15
  marks"* at 09:20 with every condition `? could not check`, SENSEX's *"peak times ±3 min"* in amber, *"zone:
  could not check — no frame for BANKNIFTY"*. Good. Three deductions, all real: (a) BANKNIFTY 13:36, PIECES
  says **"CE 56,500 … +0.2L … +1.1L 10:19 … building"** and the UP card says *"CE 56500 still adding (+0.2L) —
  defending"* for a front **82% below its own peak**. §1d's own text forbids exactly that rendering (*"the face
  must not say 'still building' about a front far under its peak; it names the distance instead"*), and
  `fronts.fade_gate` already words it correctly (*"adding again, still X L under its HH:MM peak"*); the board's
  `position()` and `renderPieces` do not. (b) SENSEX 13:36 headline: **"Sellers leaning into PE 74500 writers"**
  on **CVD −10** (rank 0.63 because SENSEX futures barely trade), **0 sell / 0 buy prints of size**, and *"fill
  runs could not rank — fewer than 50 fills"*. Ten contracts of delta is not sellers leaning. The word is chosen
  by rank alone (`gen.py:568`) with no floor on size. (c) *"the fuel is on that side"* is an [I] verdict printed
  in 22px as fact, and on NIFTY it names PE at 10:00, CE from 11:00 to 13:00, and PE again at 15:00 (when CE
  23400 is 63% off its peak and PE 23400 is 19% off) because `broke()` prefers UNWINDING over STALLED and
  re-decides every minute.
- **Act on it — 5.** At 13:36 the page earns its keep by what it refuses: both pockets' fades are ILLEGAL with
  the reason, no square has both conditions met, NEITHER is "no". A skip, correctly. What it does not do is
  tell me the next thing to watch. Three minutes later (13:39, move 51) PE 23400 turned "giving back", the DOWN
  card would have read **●● — sellers press, PE 23400 gives back**, and the market went **up** 38 points to
  23,458 and **never touched 23,400** for the rest of the day (spot min after 13:36: 23,410 at 15:03). One day
  is not a verdict on anything. It is a demonstration that *"gives back"* without the price relation is half a
  test: PE writers giving OI back while price moves **away** from their strike are being released, not forced.
  The board reads the sequence and not the side of the strike price is on (§4, fix 9). Also, I cannot read the
  cards without hovering: **6 of the 14 single-line elements in the two cards are truncated at full 1600
  width** — every REFUSED IF line, the fact under each condition, the fade-gate reason.
- **Laptop — 4.** The stage is a fixed 1600×900 scaled by `min(w/1600, h/900)`. In the app it will sit under
  the GlanceBar, tab strip and replay bar; WAR's own note measures that area at **~690 px**, which scales the
  BOARD to **0.77** and its 11px labels to **~8.5px**. It was designed for 210 pixels of height it will not
  have. At full size: peak stamps collide with the price path (NIFTY *"CE 23,400 peak 10:15"* sits on the path
  and the 10:36–11:15 diamonds; BANKNIFTY *"CE 56,500 peak 10:19"* is crossed by the path; SENSEX *"PE 74,500
  peak 13:13"* is drawn on the time axis), the *"not yet played"* label overprints the PE 23,300 stamp, and
  the bottom-left zone notice overprints the PDL label on BANKNIFTY and SENSEX.
- **Her rules — 7.** Near ATM only, top 2 by absolute OI per side, the sequence with peak time and spot at peak,
  hue = side, no BULL/BEAR, [M]/[I] on every number, no odds, three absences, light by default. All present.
  Deductions are (a)–(c) above, plus: her playbook's dwell → load → run is in the scoresheet (*"dwell at round
  23,450 — price parked, positions loading"* ×3) but nowhere on the squares that are supposed to say what can
  happen.
- **Prop-desk feel — 6.** Stable grid, three sizes, the PIECES table and the MOVES scoresheet are desk-grade
  and the index tabs' one-liners (*"CE 23,400 broke first · 10:15"*) are the kind of glance a desk actually
  uses. The board panel is not desk-grade: nine layers (ribbons, hatch, ◧▨ ticks, taps, diamonds, slashes,
  stamps, brass, pockets, threat lines) in one 1084×560 SVG.

### WAR, line by line

- **3 seconds — 7.** The answer strip is her rule as a sentence: *"CE 23,400 stopped adding first — 10:15,
  spot 23,375 — and has given back 39.0L of its 64.1L build; unwinding by §1d since 10:20."* Then the other
  three in the order they stopped. The rail's four cards repeat it with a sparkline each. That answers "who
  stopped first" without looking at the map. The map itself does not answer in 3 seconds (below).
- **Truth — 9.** The best discipline in either mockup. Three absences kept apart and drawn differently
  (hatched = outside ±6 then, amber dashed = feed never carried it, lighter = rebuilt minute); ±1m / ±3m
  **measured** per index and printed on every stamp; STALLED at 13:36 not rounded up to UNWINDING because the
  eye sees a drop, with the first-unwinding minute stamped separately (13:37 @ 23,426); the close drawn to
  15:26 with the re-baseline defect disclosed in amber. That last one is a real find (11 of 38 legs moved up to
  8.66L on the 15:27 restart with no trade behind it) and it means the server's own close read for CE 23,400
  is contaminated. WAR found it by refusing to draw a number it could not trust.
- **Act on it — 6.** As a drill-down: yes. I can check a fade's legality by eye from the rail, and the ladder
  tells me where the book stands now against its session high. It has no aggression and no price relation, by
  design, and that is right for a drill-down. On BANKNIFTY at 13:36 the ladder shows **57,000 CE as the biggest
  bar on the screen** and boxes **56,500 CE (10.9L) as #1** because 57,000 is outside §1d's nine at that
  spot. I would stop and ask which one I am supposed to believe. That is the method question (§4, fix 10),
  not WAR's fault, and WAR at least shows me why with the shading.
- **Laptop — 7.** 514–524 px, no scroll, measured in the browser — real. Deductions: lanes are 8px, so the
  height channel (share of own high still held) is 1–8px and the "ruin" is invisible without the ring; the
  event-row labels 13:28 / 13:31 / 13:34 overlap on NIFTY; the amber "could not check" dashes at the top rows
  read as clutter on BANKNIFTY and SENSEX.
- **Her rules — 8.** Ranks by session-high absolute OI (and names the `ranked` bug in `WarTab.tsx` that ranks by
  peak change — the wrong rule), near-ATM shading, no engine verdict, build-up colours and PCR and max pain
  rejected in the research with reasons, nothing recorded after the close. Deduction: the map draws all ±6
  rows at equal weight when her rule says the nine and the top two are what matter; the four fronts are marked
  by a 3px side-tab and a bold label.
- **Prop-desk feel — 8.** The mirrored ladder (CE | strike | PE, absolute OI now, session-high tick, boxes by
  rank, dashed bar at the pinned minute) is the best single element on either page. The rail cards are the
  second best.

### The two together — 6

The concept is right: sentence → pieces → what can happen → moves on the main page, the OI history on a
drill-down. The execution puts the OI history on both pages, and the copy on the BOARD is the worse one (five
strikes, per-minute state as geometry, stamps colliding) while taking 60% of the main page. Meanwhile the thing
only the main page can show — her playbook, the dwell and the load and the stops as a sequence at a level —
is on neither, except as rows in a 66-row scoresheet.

---

## 2. Critique

### 2.1 The board panel is a barcode, not a chessboard (BOARD, every index, every time after ~10:30)

The ribbons draw §1d's state **per minute** as solid / light / hatched. The state flickers: on NIFTY the record
has **29 state changes on CE 23400, 27 on PE 23400, 52 on CE 23500** (13:30–13:50 on PE 23400 reads
`SSSSSSSUUUUSUUUUUUUUS`). So every ribbon is a stripe of alternating fills with ◧ and ▨ ticks sprinkled along
it, and the sequence her rule is built on — build, then stall, then unwind, once — is not readable off it. The
scoresheet already debounces this into legs (3 minutes, one "stopped adding" per leg). The board should draw
what the scoresheet decided, not what the raw rule said every minute.

Where the eye gets lost, specifically: NIFTY 13:36, the 23,400 rank. Coral above, teal below, hatch over both
from 10:22, ticks at 10:11 / 10:20 / 12:03 / 13:16, the "CE 23,400 peak 10:15" stamp on the path, the zone
diamonds ◇◆ with slashes at 10:36–12:24 on the same path, the pocket outline, VWAP dotted, OPEN brass line
under it. I count nine marks within 40 pixels of the 10:36 arm. A chess board has one piece per square.

### 2.2 The sentence says more than the facts hold

- SENSEX 13:36: *"Sellers leaning"* on CVD −10 and zero prints of size. The word comes from rank alone.
- BANKNIFTY 13:36: *"CE 56500 still adding (+0.2L) — defending"*, 82% under its 10:19 peak. §1d says name the
  distance.
- BANKNIFTY 13:36: *"CE 56400 writers stopped first (09:49), the fuel is on that side"*: a 1.3L build that is
  now 0.4L **below its open**, rendered in PIECES as *"stopped −134%"*. WAR says the same thing honestly
  (*"gave back all 1.3L and sits 42.1K below its open"*). "Stopped −134%" is not a sentence a trader parses.
- NIFTY, whole day: *"the fuel is on that side"* flips PE → CE → PE. The morning's story (CE 23400 stopped at
  10:15, 94% gone by the close) is lost from the headline by 15:00 because CE 23400 happened to be STALLED
  rather than UNWINDING at that minute and `broke()` prefers unwinding.
- NIFTY 13:36, the framing: the sentence takes the aggressor's side (*"no defender building"* implies the
  sellers get through). The doctrine's question is *"whose aggression is failing?"* Sellers pressing 8-to-1
  into a side that is not giving back is, by the operator thesis, the failed-aggression read, and that is what
  the day did. The page had every fact for that reading and chose the other emphasis.

### 2.3 "What can happen" is clipped and half a test

Six of fourteen lines truncated at full width; the REFUSED IF line, the fact under each condition and the fade
reason are the lines cut. Two conditions per square: *the paying writers give back* and *the aggressors
press*. The first is read from OI alone. PE 23400 "giving back" from 13:39 with price rising away from 23,400
counts as fuel for the DOWN square. Forced and released look identical to this test. The price relation is on
the page — PIECES prints **ITM 20 / OTM 20** in 11px grey — and it is the single most explanatory fact of the
day: CE 23400 was **ITM** and unwinding (call writers paying), PE 23400 was **OTM** and stalled (nobody paying).
The day drifted up. That fact deserves the loudest position on a front, not the quietest.

### 2.4 Built for 900 pixels it will not have

Fixed stage, scaled. ~690 px in the app → 0.77 → 11px labels at ~8.5px, 14px body at ~10.8px. WAR measured its
own tab area and designed to it; BOARD did not. Everything in 2.1 gets 23% worse.

### 2.5 WAR's map gives noise the same ink as the answer

At NIFTY 13:36 the brightest stripes are 23,400 PE (right), 23,300 PE, 23,500 CE — and 23,650 / 23,700 CE,
which her rule says are hedges and premium collection. Equal colour scale across ±6 rows, four fronts marked by
a 3px tab. The ladder already shades §1d's nine; the map should too. Then the four fronts own the ink and the
map answers in 3 seconds like the strip does.

### 2.6 Smaller things, each specific

- BOARD's CVD lamp says CONTRADICTED at 13:36 on Upstox side attribution (−514) while GoCharting's tape read
  **+1,128** over the same window and the two agree on sign on **64% of bars**. That disagreement is in the
  WHOSE MOVE gutter, truncated (*"GoCharting CVD +1,128 vs Upstox -…"*). The one number that decides the
  status should carry its own doubt next to the ✗, not in a clipped footnote.
- BOARD MOVES: *"CE 23500 stopped adding — peak +34.9L at 10:15"* (row 17) and *"CE 23500 stopped adding — peak
  +34.9L at 11:45"* (row 32): same front, same number, twice. Legitimate by the leg rule (it re-built to the
  same level), reads as a duplicate. Say *"re-built to its 10:15 level and stopped again"*.
- BOARD NEXT SQUARES gutter: `●✕` / `◐●` glyph pairs with no key on the page; the labels truncate at 30
  characters (*"CE 23400 wall · PE 23400 wall"* survives, most do not).
- BOARD light toggle persists in localStorage; one click and dark sticks across reloads. She hates dark. Either
  drop the toggle or do not persist it.
- BOARD futures line on BANKNIFTY / SENSEX: *"too small against today's own 15-min changes to read"* on every
  minute I looked at. If it is unreadable all day on two of three indices it should not hold a line.
- WAR: *"1.2L off"* for CE 23,500 in the sub-line reads as a fact of movement when 1.2L is inside the stall
  band of a 39.5L front. Fine in the rail (which says STALLED), misleading in prose.
- WAR event row: three stops in six minutes (13:28, 13:31, 13:34) print on top of each other.
- WAR BANKNIFTY / SENSEX: the amber "could not check" dashes on 57,200 and 75,500/75,600 sit at the top of the
  map in the reader's first fixation. Correct, but they should be quieter than the answer.
- Both: after 15:30 nothing is drawn or recorded — verified on the page footers. Good. BOARD's drag sample
  series has 18:12 samples in `day_state` (their §6g) — not on the page, but it will be the next leak.

### 2.7 What is right and should not be touched

The PIECES table (front, vs-spot, OI now, built, peak · time, sequence · off peak, "first" highlighted) is her
rule as a table and is the best thing on the BOARD. The WAR ladder and rail. The index tabs' one-liners. The
answer sentence's grammar (aggression → who pays → response). The absence discipline on both pages. The
scrubber and the click-a-move replay. The 09:20 "fronts forming" state. None of this needs redesign.

---

## 3. How I would want it made for myself

Suppose I run her book: NIFTY / BANKNIFTY / SENSEX, buy and write, OI as positioning, zero cost, posting not
crossing, flat most of the day by doctrine. I want one screen that answers "where is price parked, who is
loading there, and which way do the stops run" and then stays out of the way.

### The main page

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ NIFTY  ▎CE 23400 stopped 10:15, ITM, 61% gone ▎  BANKNIFTY ▎… ▎  SENSEX ▎… ▎     13:36  ⏮ ▶ │  36px
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Sellers pressing into a put wall that is not paying — CE 23400 (ITM) is the side giving  │  22px, one line
│ back; PE 23400 (OTM) stalled 13:31. Failed-aggression watch.                              │
│ OI ✗ CE 23400 unwinding [M]   CVD ✗ −514 / 15m rank .94 [I] (2nd tape disagrees)   FLOW ✗ 8:1 [I] │  14px lamps
│ engine: CAUTION — no edge · CONTRADICTED                                                  │  11px, demoted
├───────────────────────┬──────────────────────────────────────┬───────────────────────────┤
│ THE BOOK (ladder)     │ THE PATH (spot, day, index frame)    │ WHAT CAN HAPPEN           │
│  CE ◄│ 23,500 │► PE   │  levels · pockets · dwell boxes      │ UP  → 23,450 round        │
│ ■■■■│ 23,450 │▪       │  ◧▨ only on the 4 fronts, once per  │  who pays: CE 23400 (ITM) │
│ ▨▨▨ 1│ 23,400 │1 ■■■■■■│  leg · taps/arms as small marks     │  paying now: yes, 61% off │
│      │ 23,350 │▪       │                                      │  aggression: no (CVD −514)│
│  ▪  2│ 23,300 │2 ■■■   │  parked: 23,450 · 41 min (12:08→)   │  refused: CE adds again / │
│ dim rows outside the 9│  loaded there: PE 23400 +22L         │  absorption at 23,450     │
│ tick = session high   │  stops: below 23,400 → OPEN 23,352   │ DOWN → 23,400 wall        │
│ box = top 2 by OI     │                                      │  who pays: PE 23400 (OTM) │
│                       │                                      │  paying now: not yet      │
│                       │                                      │  aggression: yes, 8:1     │
│                       │                                      │  refused: PE adds again / │
│                       │                                      │  absorption at 23,400     │
│                       │                                      │ fade u2 ILLEGAL · d2 ILLEGAL│
├───────────────────────┴──────────────────────────────────────┼───────────────────────────┤
│ WHOSE MOVE: CVD (both tapes, same scale) + runs, 15-min window│ LAST 5 MOVES · open log ▸ │  110px
└──────────────────────────────────────────────────────────────┴───────────────────────────┘
   designed at 1600 × 690, no scaling; three sizes 22 / 14 / 11
```

**What I look at, in order.**
1. **The sentence and the three lamps.** One line, her grammar, then OI / CVD / FLOW each with its fact and
   its doubt (the second tape's sign beside the CVD lamp). The engine's words under them in 11px. If the lamps
   disagree with the engine, I see it without reading a box.
2. **The ladder.** WAR's ladder, promoted to the main page. Who is loaded, at which strike, how far off the
   session high, ITM or OTM, the four fronts boxed, the rest dimmed. This is the chess board: pieces on
   squares. Not ribbons.
3. **The squares.** For each direction: the square, **who pays** (the front on that side, and whether it is
   ITM), **are they paying now** (giving back with the price relation), **is anyone pressing**, **what refuses
   it**. Five short rows, never truncated, both fade gates on one line at the bottom.

The path panel is context, not the answer. It carries spot, levels, pockets, the **dwell boxes** (where price
parked, for how long, and what loaded there — her playbook's step 2, which is the only thing on this page that
is hers alone), and one ◧ or ▨ per leg on the four fronts. Nothing else on the path.

**Cut.** The ribbons and every per-minute state drawn as geometry. *"The fuel is on that side"* as a headline
verdict. The threat lines and the NEXT SQUARES gutter (the cards say it). The 66-row scoresheet on the main
page: keep the last five and a link. The HOW FAR / WHICH line (toxicity and drag are a drill-down). The
futures-quadrant line on any index where it cannot be read. The dark toggle.

**Add.** The dwell clock (*"parked at 23,450 · 41 min · PE 23400 +22L during it"*). ITM/OTM as the loudest
attribute of a front. The price relation on give-back (forced vs released — her call, §4 fix 9). A session
story line that never re-decides: *"first stop today: CE 23400 10:15 · latest: PE 23400 13:31"*. Mini-ladders
for the two indices not in focus (Quant Tower's small multiples, done as ladders not heatmaps).

**How "what can happen" should be expressed.** Not as arrows and not as a probability. As a mechanism with its
tests: *if price goes to X, these writers pay; they are / are not already paying; someone is / is not pressing;
this is what refuses it.* Every cell a fact with a tag, every "not yet" and "could not check" kept distinct.
That is what the cards try to be. Give them the width and the price relation and they are it.

### The WAR

Keep WAR nearly as it is. It is the OI record and it is honest. Three changes: dim rows outside §1d's nine on
the map (the ladder already does), promote the height channel by giving lanes 12px where the row count allows
(NIFTY's 15 rows fit at 12px inside the 340 cap), and stack the event-row labels. Add the dwell boxes on the
spot line so the map shows load-at-a-level, not just load. Nothing else. The ladder moves to the BOARD as well;
WAR keeps its copy with the pinned-minute cursor.

---

## 4. Top fixes, smallest and most valuable first

**P** = presentation, the builder decides as the trader. **M** = changes her method, only she decides.
**S** = server, needed before anything wires.

1. **P — Never say "building" or "defending" for a front ≥15% under its own peak.** BANKNIFTY 13:36 CE 56500.
   `fronts.fade_gate` already has the sentence (*"adding again, still X L under its HH:MM peak"*); use it in
   `position()`, `renderPieces` and the cards. One line each.
2. **P — "Leaning / pressing" needs a size floor, not only a rank.** No aggression word when prints of size are
   0/0 or runs could not rank (SENSEX 13:36). Say *"nobody pressing — too thin to read"*.
3. **P — Give the cards their width.** Stack UP over DOWN full-width, or drop the second column of the right
   rail; zero truncated lines at 1600. Move the second tape's sign next to the CVD lamp.
4. **P — Draw legs, not minutes.** Ribbons (if kept) take their state from the scoresheet's debounced legs, not
   `fronts._state` per minute; one ◧ and one ▨ per leg on the four fronts only. Or replace the ribbons with the
   ladder (§3).
5. **P — Design to 1600×690 and stop scaling.** Measure the app's real tab area first, as WAR did.
6. **P — Stamp "first" once.** Show *first stop today* and *latest stop* as two facts; never re-decide the
   headline's "first" from the current minute's state.
7. **P — WAR: dim rows outside §1d's nine on the map; stack the event-row labels; 12px lanes when rows ≤ 15.**
8. **P — Drop the dark toggle's persistence** (or the toggle). She hates dark.
9. **M — Give-back with the price relation.** A front unwinding while price sits through / moves toward its
   strike is being *forced*; unwinding while price moves away is being *released*. §1d today reads the sequence
   only. On 09-23 the ITM front (CE 23400) was the forced one and the day drifted up; PE 23400's afternoon
   give-back was a release. One day, no verdict — but it is the question her playbook asks (stops as liquidity
   run *into* a level), and the cards cannot answer it without this stamp. Hers to accept, pre-register, and
   log forward.
10. **M — NEAR = 9 on BANKNIFTY and SENSEX.** 57,000 CE was the biggest bar on the ladder and outside the nine
    at 13:36; it was a top-2 front for 202 minutes earlier. Both notes flag it. Options are a distance instead
    of a count, or hysteresis on window membership so a strike does not enter and leave the nine as spot
    crosses one point. Her parameter.
11. **M — Should UNWINDING require persistence?** The flicker (52 flips on CE 23500) is the rule's, not the
    face's. If she wants the state itself debounced, that is a §1d parameter. If not, fix 4 handles the face.
12. **S — Record the grounded calls** (BOARD note addition 5) — without it `grounds.py`'s kill clock has
    nothing to judge and the BOARD's engine box is empty on replay. **S — Persist the 09:15 OI baselines
    across a restart** (WAR note §7.8) — the close read of CE 23,400 currently carries 8.66L of re-baseline.
    Both are about 20 lines and both are truth fixes, not features.
