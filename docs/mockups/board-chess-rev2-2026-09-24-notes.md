# BOARD rev 2: design note, 2026-09-24

**Mockup:** `board-chess-rev2-2026-09-24.html`. It is self-contained, **light only** (no toggle, no
storage) and a replay of **2026-09-23** from the record. Nothing on the server or in the repo
changed, and rev 1's files are untouched.

This revision follows Fable 5.1's review (`docs/review/fable-trader-review-board-war-2026-09-24.md`):
part 3 is the brief, and all of part 4's fixes are applied (see §4 below). It also carries Mary's
decisions from tonight: light only, the ladder is the chessboard, and her §1d rule is used exactly
as written, with no invented smoothing. The forced/released slot is left empty on purpose.

**Generator** (scratchpad, read-only against the repo): `gen_rev2.py`, which extends rev 1's
`gen_board.py`, plus `rev2_template.html` and `render_rev2.py`. Every front, state, peak, gate and
grounding comes from `fronts.read`, `fronts._state`, `fronts.fade_gate`, `fronts.broke`,
`grounds.facts` and `grounds.ground` on the record. The page ranks and re-decides nothing.

---

## 1. The size it was built for, measured rather than assumed

| what | measured |
|---|---|
| Her screen, as her own Chrome reports it | **1536 × 864 CSS px** (1920×1080 at 125%). The work area is 1536 × 816. |
| Her Chrome viewport, maximized | **1536 × 695**. It drops to 639 while the "controlled by automated software" bar is showing. |
| The ui-v2 shell above the tab content, live | GlanceBar 72 + answer band 150 + MACHINE strip 35 + tab strip 46 = **303 px**. That is 341 px when the NOT LIVE banner shows. |
| Board tab area inside today's shell | **≈ 392 px**, which is not enough for this design or any honest main page. |

**The page fills whatever it is given, at real size, and never scales.** It is verified with zero
truncated or overflowing lines on all 1,122 replay minutes (3 indices × every minute) at:
- **1536 × 639 in her Chrome**;
- 1536 × 690 and 1600 × 690;
- **1536 × 577** with its own index strip removed.

That last size is the one that matters for wiring. On the Board tab, collapse the global answer band
and the MACHINE strip, because the board's own answer line replaces them. Move index switching and
the three mini-ladders into the GlanceBar, which already shows the three indices. The board then fits
in her real window under the GlanceBar and the tab strip. Without that, it does not fit as a tab.

## 2. What the eye reads, in order

```
┌ NIFTY ▤ first CE 23,400 10:15 · ITM 20 · 61% gone │ BANKNIFTY ▤ … │ SENSEX ▤ … │ ◀ ━━━●━━ ▶ 13:36 │ 13:36 close ┐  mini-ladders
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│ Sellers pressing into PE 23,400 (OTM 20), which stopped building at 13:31 — CE 23,400 (ITM 20)  │ 22px, one line
│ is the side giving back                                                                         │
│ OI  CE unwinding since 10:20 · PE stopped 13:31 │ CVD −514/15m · rank .94 │ FLOW 8 sell / 1 buy │ 14px lamps
│     stamps ±1 min · futures: longs exiting      │ 2nd tape −534: same sign│ print side inferred │ 11px doubts
│ FIRST TO STOP AND GIVE BACK CE 23,400 … stamped once · LATEST STOP … · ENGINE CAUTION → CONTRADICTED │ 11px
├ THE PATH (spot, levels, dwell boxes) ─┬ THE BOOK (ladder) ┬ THE PIECES (4) ┬ WHAT CAN HAPPEN ────────┤
│ same price axis as the ladder ────────► CE ◄│strike│► PE  │ CE 23,400 ITM 20│ ▲ UP TO 23,450 +30      │
│ dwell clock in the header             │ boxes, spot line  │ UNWINDING …     │ WHO PAYS · PAYING NOW?  │
│ ◧ high / ▨ first §1d unwind on ranks  │ shade = §1d's 9   │ forced/released │ PRESSING? · REFUSED IF  │
│                                       │                   │ — pending §1d   │ ▼ DOWN TO … (5 rows)    │
│                                       │                   │ addendum        │ FADE u2 … · FADE d2 …   │
├ WHOSE MOVE (both tapes' CVD, runs) ───┴ MOVES: last 5 · open the full log ▸ ───────────────────────┤
└ provenance / the re-baseline disclosure (amber) ──────────────────────────────────────────────────┘
```

1. **The sentence, first.** It follows her grammar: who is pushing, into which writers (and whether
   they are ITM or OTM), what those writers are doing by §1d, and which side is giving back. Direction
   appears only inside that mechanism.
2. **The lamps under it, second.** OI, CVD and FLOW each give a fact and its doubt. The second tape's
   CVD over the same 15 minutes sits beside the CVD lamp and turns amber only when its sign is
   opposite. The story line follows: FIRST TO STOP AND GIVE BACK (stamped once), LATEST STOP (the
   rule's stamp now), and the engine's words with their grounding status. When no call was recorded,
   it says so.
3. **The ladder, third: the chessboard.** It is WAR's mirrored ladder:
   - CE bars left, PE bars right, absolute OI now;
   - │ marks the session high;
   - the server's top two per side are boxed and numbered;
   - §1d's nine strikes are shaded and the other rows dimmed;
   - the brass spot line shows which writers are in the money.

   It shares its price axis with the path, so the path runs straight into the book.
4. **Then the pieces and the squares.**
   - The four fronts sit in stable places (CE #1, CE #2, PE #1, PE #2). ITM/OTM is the loudest chip on
     each card. Each card gives the rule's state in §1d's own words, the high with the spot at the
     high, and an empty dashed slot: *forced / released — pending §1d addendum*.
   - WHAT CAN HAPPEN gives, for each direction, five rows: square, who pays, paying now?, pressing?,
     refused if. Both fade gates share one row.

The path is context. It carries spot, brass levels, her pockets (NIFTY), **dwell boxes** with the
dwell clock in its header, and one ◧ (high) and one ▨ (first §1d unwind after it) on each piece's
rank. Taps and zone arms are small marks. The full move log opens over the right side. Click any move
to replay the board to that minute.

## 3. The frozen moments, as the page reads them

- **NIFTY 13:36.**
  - *Sentence:* "Sellers pressing into PE 23,400 (OTM 20), which stopped building at 13:31 —
    CE 23,400 (ITM 20) is the side giving back."
  - *Lamps:* OI "CE unwinding since 10:20 · PE stopped 13:31". CVD −514 / 15 min, rank 0.94, price
    −26.9. The **second tape reads −534 over the same window, the same sign.** FLOW 8 sell / 1 buy,
    which clears the size floor.
  - *Engine:* "CAUTION — no edge defined right now" → **CONTRADICTED** (OI ✗, CVD ✗, FLOW ✗).
  - *Dwell:* last parked at 23,450 for 13 min (13:17→13:30), then rejected; during it CE 23,450
    −1.5L and PE 23,300 +1.4L.
  - *Squares:*
    - DOWN to 23,400: who pays is PE 23,400 (OTM 20); paying now, **not yet**; pressing, **yes**.
    - UP to 23,450: who pays is CE 23,400 (ITM 20); paying now, **yes**; pressing, **no, sellers are**.
  - *Fade gates:* both **ILLEGAL**.
- **NIFTY close, drawn to 15:26.** A restart at 15:27 re-read the 09:15 OI baseline: 11 of 38 legs
  moved, by up to 8.7L, with no trade behind it. WAR found this first, and the page says it in amber;
  15:27–15:29 "could not be checked".
  - *Sentence:* "Nobody pressing · writers leaving both sides of 23,400: CE 23,400 79% off its 10:15
    high, PE 23,400 39% off its 13:31 high."
  - The second tape reads **OPPOSITE** here: +112 against −20, in amber.
- **BANKNIFTY 13:36.** "Nobody pressing · CE 56,500 (ITM 25) adding again, still 0.9L under its 10:19
  peak · PE 56,500 (OTM 25) stopped building at 12:43". This is the P1 fix, in `fade_gate`'s own
  words.
- **SENSEX 13:36.** "Nobody pressing — too thin to read" (the P2 fix). The OI lamp says in amber that
  stamps are **±3 min** because BSE OI steps about every 3 minutes.

## 4. Fable's fixes, one by one

| # | fix | done |
|---|---|---|
| P1 | never "building/defending" for a front ≥15% under its high | Every surface uses `fronts.fade_gate`'s wording: *"adding again, still X L under its HH:MM peak"*. That covers the sentence, the OI lamp, the cards and PAYING NOW?. "Defending" does not appear. |
| P2 | size floor on "pressing/leaning" | The word needs grounds' CVD strength (rank ≥ .5 leaning, ≥ .8 pressing) **and** grounds' own flow-dominance rule (≥ 2 prints and twice the other side), in the same direction. With 0/0 prints or runs that cannot rank, it says "too thin to read". A strong CVD that the prints do not confirm reads "CVD leans sellers, prints 2 sell / 2 buy", with no aggression word. |
| P3 | cards get their width, nothing truncated; 2nd tape by the CVD lamp | UP sits over DOWN at full column width, five rows each. There are **0 truncated lines** on all 1,122 minutes. The "then next square" hint gives way (hidden, 50 of 2,244 card-minutes) before a first line would wrap. The second tape's window CVD is beside the lamp. |
| P4 | legs, not minutes | Ribbons are gone and the ladder replaces them, which was Fable's own alternative. History uses WAR's milestones only: the high (`peak_at`) and the first §1d UNWINDING read after it. **No debounce, no smoothing**, per Mary. The state shown is the rule's state at the cursor minute. |
| P5 | design to 1600×690, no scaling | Measured instead: see §1. The layout fills its container at real size and never scales. |
| P6 | stamp "first" once | FIRST = the first front today that §1d read stopped **and then unwinding** (her words: "stops first … then unwinding"). It is stamped at that minute and never re-decided. LATEST STOP is the rule's own latest high among non-building fronts. NIFTY: CE 23,400 (high 10:15, unwinding 10:20). BANKNIFTY: PE 56,500 (09:25 / 09:40). SENSEX: PE 74,700 (09:24 / 09:36). |
| P7 | WAR: dim outside the nine | The shared ladder shades §1d's nine and draws the other rows' bars at lighter weight. The map lanes and event row belong to the WAR tab (the other agent). |
| P8 | drop dark / its persistence | Light only. There is no toggle and no `localStorage`. |
| 9 (M) | forced vs released | An empty, labelled slot on every front. **Not computed, not looked at for 09-23.** |
| 10 (M) | NEAR = 9 on BANKNIFTY/SENSEX | Still her question (below). The ladder shows the 57,000 bars dimmed outside the nine. |
| 11 (M) | persistence on UNWINDING | She gave no preference, so nothing was invented. The page shows the rule's own state and its first-unwind stamp. |
| 12 (S) | record grounded calls; persist 09:15 baselines | Both are on the server list below. The replay shows an engine call on only 36 of 375 NIFTY minutes, and the NIFTY close stops at 15:26. |

Also cut: *"the fuel is on that side"*, the threat lines and gutter, the HOW FAR / WHICH line, the
66-row move list (now the last 5 plus the full log on a button), the futures line where it cannot be
read (it now appears only when grounds names the quadrant), and dark mode.

Also added: the dwell clock and dwell boxes, ITM/OTM as the loudest attribute of a front, the story
line, and mini-ladders for all three indices.

## 5. Where I disagreed with Fable, and why

1. **The second tape does not doubt the 13:36 CONTRADICTED.** Fable §2.6 quotes GoCharting "+1,128
   over the same window". That number was rev 1's cumulative-since-open figure. Over grounds' own
   15-minute window GoCharting read **−534** against Upstox **−514**, the same sign. The tapes do
   disagree over the whole day (bar-level sign agreement is 64%), and the lamp says so in amber when
   the window disagrees, as at 15:26.
2. **No "failed-aggression watch" in the headline.** It needs a price-response threshold that nobody
   has pre-registered. At 13:36 price *did* follow the selling (−26.9 in 15 minutes), so the label
   would have been wrong at that minute. The CVD lamp prints CVD and the price change side by side,
   so she can read failed aggression herself.
3. **The ladder sits at the path's NOW edge, not in the first column.** They share one price axis,
   the same arrangement as WAR. The book as it is now sits next to where price is now, and next to
   the squares that name its strikes.
4. **Fable's size target is not her tab area** (§1). Her width is 1536, not 1600. Her whole Chrome
   viewport is about 695, and the current shell leaves the Board about 392. That is a shell change
   (§1), not a design choice.
5. **"Latest: PE 23400 13:31"** in Fable's sketch: by the rule, the latest stop at 13:36 is **PE
   23,300 at 13:34**. The page prints the rule's own stamp.
6. **Dwell boxes are the war map's own episodes, not a new clock.** On 09-23 they ran 4–17 minutes
   (NIFTY 23,450: 12:08, 12:54, 13:17, 14:15), not a 41-minute box. Merging them into longer "parked"
   spans would need a new rule, which is hers to make.

## 6. Element → source, and M or I

| element | live source | tag |
|---|---|---|
| sentence, squares' yes/no, the P1 and P2 floors | **new** pure module over `fronts` + `grounds` facts (gen_rev2 `sentence`, `squares`, `aggression`, `paying` are the reference) | [I] wording on [M]/[I] facts |
| OI lamp, cards, PAYING NOW? | `/api/oihist` `fronts[]` (+ `?asof=`), plus **new** `unwind_at` per front (WAR's `fronts.since`) | [M] |
| CVD lamp, PRESSING? | `/api/calls` `facts.cvd`, `facts.flow` (grounds) | [I] print side |
| 2nd-tape doubt | `/api/tape?day=` `bars[].cvd` over grounds' window (NIFTY only, since the extension sits on one chart) | [I] |
| ladder: bar / tick / box / shade | absolute OI per minute (**new**, WAR wiring 7; the replay uses `data/chain`), `peak[]`, `fronts[]`, **new** `near` | [M] |
| FIRST / LATEST | **new**: stamped server-side once per day and **persisted in `day_state`**, so a restart rebuilds the same stamp (anytime-start) | [M] by rule |
| dwell boxes and clock | **new** reader of `data/warmap/warmap_<day>.jsonl` (DWELL → BREAK/REJECT); load = Δ`k` of §1d's nine over the dwell | dwell [I], load [M] |
| levels | `/api/warmap` `levels[]` (PDH/PDL/PDC/PWH/PWL/OPEN) | [M] |
| pockets, taps | `/api/frame` `where`, `taps` (NIFTY only); `/api/data` bands for all three (verify at 09:20) | [M] on her chart, drawn at basis [I] |
| engine words | `/api/calls` (**record them**, addition below) | status [I] |
| fade gates | `fronts.fade_gate` for both sides | [I] |
| moves | **new** composition: milestones + war-map transitions + trigger_log + runs + divergences | per row |

## 7. What wiring needs, smallest first

1. **ui-v2 shell:** on the Board tab, hide the global answer band and the MACHINE strip, and put
   index switching plus the mini-ladders in the GlanceBar. Without this the board cannot fit (§1).
2. `/api/oihist`: add `marks`, `near`, and `unwind_at` on each front.
3. `/api/oihist?asof=HH:MM` + `oi_now`. The as-of peak is `open + max(chg ≤ asof)` with `open = peak
   − max chg`.
4. `/api/warmap?log=1`: the day's level transitions and dwell episodes.
5. **Record the grounded calls** per closed 3-min bar (`data/calls/calls_<day>.jsonl`, in session
   only).
6. **Persist the 09:15 OI baselines** across a restart (WAR §7.8). Until then, mark `rebased` minutes.
7. The FIRST stamp, persisted in `day_state`.
8. The pure `board` module (sentence, squares, floors), with the kill condition proposed in rev 1's
   notes.
9. The moves composition endpoint.

## 8. Questions only she can answer

- **Near ATM = nine strikes, or a distance?** On BANKNIFTY and SENSEX, nine strikes reach ±400
  points. On 09-23 the CE/PE 57,000 straddle was a top-2 BANKNIFTY front for 202 minutes, 400+
  points from spot. §1d's parameter, hers.
- **Forced vs released:** the slot waits for the §1d addendum. Nothing was computed.
