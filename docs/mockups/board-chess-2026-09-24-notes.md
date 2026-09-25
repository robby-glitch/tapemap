# BOARD as a chess board: design note, 2026-09-24

**Mockup:** `board-chess-2026-09-24.html`. It is self-contained: open the file in a browser. It is a
replay of **2026-09-23** from the record, it is not live, and nothing on the server changed.
**Generator:** `board-chess-2026-09-24-gen.py`. It is the reference for the three `[I]` layers the
server does not have yet (§4). It imports `fronts`, `grounds` and `runs` rather than re-implementing them.

Her ask was *"the page which can tell exactly what has happened and whats happening and what can
happen … like chess board which has all the pieces and how they placed"*. That gives three
questions, and the page answers them in three fixed places:

| her question | where on the page |
|---|---|
| what's happening now (whose move) | **the answer line** at the top, the engine's call with its grounding status beside it, and the **WHOSE MOVE** strip |
| where the pieces stand | **the board**: armies at their strikes, reaction levels, her pockets and price |
| what has happened | the **same board to the left of NOW**, plus the **MOVES** scoresheet. Click a move to replay to it |
| what can happen | **NEXT SQUARES**: arrows on the board plus the **WHAT CAN HAPPEN** cards. They state conditions and never give odds |

---

## 1. Layout at 1600×900, in the order the eye takes it

1. **First, the answer line.** One mechanism sentence at 22px, in her read model's order:
   aggression, then the side that pays, then the response. At 13:36 it reads *"Sellers pressing into
   PE 23400 writers who stopped adding at 13:31 — no defender building at 23400."* Under it, at 14px,
   are both fronts' state and the CVD/flow fact. On the right is the engine's call with its status
   (BACKED / THIN / CONTRADICTED / PATA NAHI) and one line each for OI, CVD and FLOW. When no call
   was recorded, the chip says **UNGROUNDED** and gives the reason.
2. **Second, the board.** It is drawn in the index-spot frame across 09:15–15:30. The **strikes are
   the ranks.** Every strike near ATM carries its army: CE writers above the rank (coral) and PE
   writers below it (teal). Thickness is the OI built since 09:15. Geometry shows the rule's state
   minute by minute: **solid = building, light = stopped, hatched = giving back**. The four current
   pieces (top 2 per side, served by `fronts.read`) are drawn at full weight and every other near
   strike is faint. Far strikes are not drawn. Each piece carries a **peak stamp** giving time,
   size and spot at the peak, and ◧/▨ ticks mark the minute the rule confirmed a stall or a
   give-back. The other layers are:
   - the index path drawn as a line, with the day's H/L;
   - brass reaction levels (PDH, PDL, PDC, PWH, PWL, OPEN), with off-board levels named at the edge
     with their distance;
   - her pockets (d2→d3 teal, u2→u3 coral) and VWAP;
   - notation on the path: taps ○, zone arms ◇ and triggers ◆, and a slash through a mark when the
     fade gate said ILLEGAL.

   The part of the day not yet played is shaded. **Threat lines** run from NOW to the next two
   squares in each direction, and the gutter names each square with its distance and two
   condition marks (● met, ✕ against, ◐ not yet, ? could not check).
3. **Third, the right rail, read top to bottom:**
   - **PIECES:** the four fronts with vs-spot (ITM/OTM), OI now, built, peak and time, and sequence
     with off-peak %. The one that broke first is highlighted. A futures line follows.
   - **WHAT CAN HAPPEN:** an UP card and a DOWN card. Each gives the first and second square, the
     two conditions that take it (*the paying writers give back* and *the aggressors press*) with
     yes/no/not yet and the fact, what refuses it, and the fade gate at her pocket on that side.
     Below the cards are the NEITHER (range) line and HOW FAR (toxicity) / WHICH (drag).
   - **MOVES:** the scoresheet, newest at the bottom. Hovering a move draws a guide on the board;
     clicking it replays to that minute.
4. **The WHOSE MOVE strip** sits under the board on the same clock. It shows Upstox CVD (solid),
   GoCharting CVD (dashed, same scale, NIFTY only) and fill runs (▲ buy / ▼ sell), with the
   15-minute window that grounds reads shaded.
5. **The header** has the index tabs, each with its own one-liner (*"CE 23,400 broke first ·
   10:15"*), a minute scrubber (← → keys, shift for 5 minutes), and bookmarks at **13:36** and
   **15:29**.

Three font sizes (22 / 14 / 11). Hue means side only. Caution amber is used only for disclosures:
CONTRADICTED, "could not check", and BSE OI stepping. Light is the default (she hates dark mode, 2026-09-24); a dark
toggle exists.

## 2. The frozen moments

- **13:36, NIFTY. The page opens here.** The replay reproduces the HANDOFF case on the rule's own
  numbers:
  - CVD **−514 since 13:20, rank 0.94**, which matches the HANDOFF exactly.
  - **8 sell / 1 buy** prints of size. The live header said 9 to 1; the replay counts fills up to
    13:36:59 from the rebuilt detector.
  - Futures OI −13,260 on −26.9 pts, which reads as *longs exiting*.

  One thing differs from the HANDOFF's wording. By the rule, **PE 23400 was STALLED at 13:36**
  (peak +127.0L at 13:31) and turned **UNWINDING at 13:37–13:39**. The board shows that turn happen
  two minutes later. The engine's "CAUTION — no edge defined right now" grounds as
  **CONTRADICTED**: OI is against (CE 23400 unwinding), CVD is against (one side pressing) and FLOW
  is against (one-sided).
- **15:29, the close.** *"Nobody pressing, and writers are leaving both sides — nobody is defending
  23400 from either side."* All four fronts are giving back: CE 23400 is 94% off its 10:15 peak and
  PE 23400 is 44% off its 13:31 peak. After 15:30 the page shows this last snapshot and nothing
  more.
- **Worth scrubbing to:**
  - **10:36.** A zone SELL armed at u2 with the fade **ILLEGAL**, because CE 23400 had stopped at
    10:15. One minute later 23,400 broke up, and the run to 23,450 arrived at 11:47.
  - **12:06–12:24.** SELL arms while the engine said **GO**.
  - **12:48, 13:11 and 14:34.** Three failed runs to PDH 23,489.
  - **BANKNIFTY at 12:36.** The CE and PE 57000 fronts sat 410 pts away (see §6).

## 3. Every element: where it comes from, and M or I

"Live" is the endpoint the wired page would read. "Mockup" is what this file was built from; the
source is a GET capture at 00:25 IST on 09-24, while the server still held 09-23, or `data/` read
read-only. I watched one payload of every endpoint listed below. `/api/calls`, `/api/frame`,
`/api/data` and `/api/tape` (today) had already rolled to 09-24 and were empty. For those, the
fields come from the same function or record the route serves: `grounds.ground`, the frame log,
and `/api/tape?day=`.

| element | live source · field | mockup source | tag |
|---|---|---|---|
| index path, ranks | `/api/oihist` · `minutes[HH:MM].spot`, `.k` keys | capture | [M]. The 09:15 `backfill_marks` mark is drawn at half weight |
| army thickness | `/api/oihist` · `minutes[..].k[strike] = [ce_chg, pe_chg]` | capture | [M] |
| army geometry per minute | **missing** (addition 3) | `fronts._state` per minute in the generator | [M] rule on [M] OI |
| the four pieces, broke first | `/api/oihist` · `fronts[]`, `broke` (plus `?asof=` for the scrubber, addition 2) | `fronts.read(fronts.cut(minutes,t), peak-as-of)`, with peak-as-of from `data/chain` (the same running max as `ChainState.peak`) | [M] |
| peak stamp, spot at peak | `fronts[].peak`, `peak_at` + `minutes[peak_at].spot` | same | [M]. ±3 min on SENSEX (§6) |
| OI now | **derivable**: `peak[] oi − max chg + chg` (addition 2 serves it as `oi_now`) | `data/chain` snapshot at the minute | [M] |
| reaction levels | `/api/warmap` · `indices.<idx>.levels[] {kind, px, label}`, kinds PDH/PDL/PDC/PWH/PWL/OPEN | capture | [M] |
| her pockets + VWAP | NIFTY: `/api/frame` · `where.buy_zone / sell_zone / vwap / px / warm`. All three indices: `/api/data` bands (**not watched tonight**, verify at 09:20) | `data/frame/frame_2026-09-23.jsonl`, drawn at basis = `where.px − spot`, 15-min median | pocket [M] on her chart. Position on this board [I] |
| taps | `/api/frame` · `taps[] {t, tx, side, price, z}` | frame log | [M] |
| zone arms/triggers + gate | `/api/signals?rule=all&day=&idx=` · `rows[] {t, kind, side, band, level, gate{legal,why}, ctx}` | capture, de-duplicated first-write-wins (§6) | row [M], gate [I] |
| engine call + status | `/api/calls?idx=` · `calls[] {text, status, oi/cvd/flow {state, fact, tag}}` | `grounds.ground` on 09-23 bars, runs and fronts, with ctx from the trigger_log rows and the 13:36 HANDOFF header | status [I] |
| CVD (Upstox), futures OI quadrant | `/api/tape?idx=&day=` · `ux.bars[].cvd`, `.oi`; `/api/calls` · `facts.fut_oi` | capture + `grounds.facts` | [I] side of print |
| CVD (GoCharting), agreement | `/api/tape` · `bars[].cvd`, `ux.agree.delta_sign_agree` | capture | [I] / [M] |
| fill runs | `/api/tape` · `ux.marks.runs[] {from_t, side, qty}`, `runs_why` | **replayed** from `data/book` via `ladder.step → runs.on_fill`, the server's own rebuild path. NIFTY 82 and BANKNIFTY 29 match the HANDOFF | [I] |
| level moves (break / run / hit / failed / dwell / reject) | **missing as a list** (addition 4). The route serves only `seq_fired` | `data/warmap/warmap_2026-09-23.jsonl`, the live forward log, not the backfill replay | [M] |
| tape events at a level | `/api/frame` · `tape.events[] {t, kind, p, side, at{kind,label}}` | frame log | [M] |
| toxicity | `/api/vpin` · `series[] {at, vpin, pct}` (NIFTY fut only) | `data/vpin_log.jsonl` | [I] |
| drag | `/api/drag` · `indices.<idx>.day.series[] {t, frac, side}` | `data/day_state/day_2026-09-23.json` | [M] |
| answer line | **missing** (addition 6) | `position()` in the generator | [I] |
| next squares, conditions | **missing** (addition 6) | `squares()` in the generator | [I] |
| fade at pocket | `fronts.fade_gate`, via `/api/frame setup.gate` today (NIFTY, one side) | `fronts.fade_gate(fr, side, plays=None)` for both sides | [I] |
| scoresheet | **missing** (addition 7) | composed in the generator | per row |

## 4. What the server needs to wire this, smallest first

None of this is built. Each item is additive, and none edits a pre-registered rule.

1. **`/api/oihist` gains `marks`** (the count of minute marks). *1 line.* The face can then say
   "fronts forming" for the first 15 minutes (§6-c) without touching `fronts.py`.
2. **`/api/oihist?asof=HH:MM` + `oi_now` on each front.** *About 10 lines, pure.* It returns
   `fronts.read(fronts.cut(minutes, asof), peak_asof)` and `broke`, where
   `peak_asof[k,side] = (peak − max chg) + max(chg ≤ asof)`. The open OI falls out of data already in
   memory, and I checked it against the record: PE 23400 open = 18,850,910 − 12,699,310 = 6,151,600
   at both 13:36 and the close. This is what makes the scrubber and anytime-start honest.
3. **`/api/oihist` gains `states`**, one string per near-ATM strike-side giving the rule's state
   per minute, from the same `fronts._state`. *About 10 lines.* The page must never compute the
   rule; the TypeScript copy was deleted once already.
4. **`/api/warmap?idx=&log=1`** returns the day's level transitions from
   `data/warmap/warmap_<day>.jsonl` (via `daylog.open_text`). *About 10 lines.* Today only the latest
   `seq_fired` is served.
5. **A record of the grounded calls.** Append `/api/calls` output once per new closed 3-min bar to
   `data/calls/calls_<day>.jsonl`, gated on `in_session`. *About 20 lines + a test.* Today a call is
   computed per request and never logged. That is why the replay has an engine call on only 36
   of 375 NIFTY minutes (the zone rows' 3-min bars plus the 13:36 header), and **why `grounds.py`'s own 30-session kill condition has no data to be judged
   on.**
6. **`squares.py`**, pure and stdlib, fed from `fronts`, `grounds.facts`, war-map levels, bands and
   spot. It returns `position {head, sub}` and `squares {up, dn, pin}` with conditions
   `{mode: met|against|notyet|blind, fact}`. It is served on `/api/calls` or a new `/api/board`.
   *About 120 lines + tests.* The generator's `position()` and `squares()` are the reference. It
   needs a kill condition at birth. Proposed, and hers to accept: *after 30 sessions, squares whose
   two conditions were both met are reached within the session no more often than squares with
   neither, so the conditions are noise and the cards go.*
7. **`/api/board/moves?idx=&day=`** composes items 3, 4 and 5 with trigger_log, taps and runs.
   *About 80 lines.* The generator's `build()` is the reference.
8. **Her pockets for all three indices.** The frame exists only for the index on the GoCharting
   chart. Read `/api/data` bands instead: check at 09:20 whether they are futures or spot, and serve
   the `basis` used, because the board is in the index frame.

## 5. Decisions taken as the trader (one line each)

- **Index frame.** The squares are strikes and the reaction levels are index levels. Her pockets
  are printed in fut numbers exactly as on her chart and drawn at the minute's basis. Futures bars
  would have put strikes 8–40 pts off: the NIFTY basis ran from 7.7 to 40.5 through the day.
- **The time axis is fixed at 09:15–15:30**, with the unplayed part shaded, so nothing rescales
  while the eye is on it.
- **Price range is the day's spot range ±1.5 strikes.** Live, it only widens at a new extreme. A
  front beyond it is named at the edge; it is never allowed to stretch the board.
- **Armies are OI built since the open, drawn as ribbons at their strike.** The sequence becomes
  geometry, which the eye reads faster than a table.
- **Four pieces at full weight, the rest of the 9 nearest faint, far strikes absent.** That is her
  rule. The WAR tab (another agent) owns the full ±6–8 strike heatmap drill-down.
- **The answer is a mechanism sentence**, and direction appears only inside it. There is no
  BULL/BEAR.
- **An unrecorded engine call shows as UNGROUNDED with the reason.** The page never carries a stale
  call forward.
- **"What can happen" is two squares each way, two conditions each, plus what refuses it and the
  fade gate on that side.** Those are her doctrine's own tests, and there are no odds anywhere.
- **Scoresheet: one move per leg.** A leg is BUILDING held 3 minutes with a new high, ending in one
  "stopped adding", then "giving back" (UNWINDING held 3 minutes), then "half its build gone".
  Repeats (rejects, taps, divergences) collapse into one row with an as-of count. A move is stamped
  when the rule confirms it, and the peak time rides in the text.
- **Absorption/exhaustion rows appear only at an OI wall or a prior-day level**, per the 2026-09-16
  rule.
- **The second tape's CVD is drawn dashed on the same scale and never blended.** A sign
  disagreement turns amber.
- **The futures quadrant is named only when grounds says both legs are big.**
- **Toxicity and drag get one line.** They are the tail of the read model, not a headline.
- **Excluded:** max pain, PCR, aggregate CE/PE walls, breadth counts, the seller gate. They are
  aggregate, or not the position.
- **The first 15 minutes say "fronts forming"**, not "stopped".
- **[I] display rules**, declared here and not tuned: debounce 3 min; a move needs a front ≥15% of
  the biggest; tap visits 20 min; reject groups 30 min; divergence groups 20 min; run clusters are
  15-min windows with ≥3 runs and ≥2× the other side.

## 6. Found while building it (reported, nothing fixed)

- **a. Nothing records the grounded calls.** See addition 5; `grounds.py`'s kill clock cannot run.
- **b. BANKNIFTY fronts reach 400+ pts.** `NEAR = 9` on 100-pt strikes is ±400. On 09-23,
  **CE 57000 and PE 57000 were top-2 fronts for 202 minutes**, 410+ pts from spot. The headline CE
  front flipped between 56500 and 57000 whenever spot crossed about 56,550, the point where 57000
  becomes the 9th-nearest strike. The board shows them off the board at the edge and does not
  re-rank. This is her method question (§7).
- **c. No "forming" state.** With fewer than 15 marks, every front's slope is about 0, so all of
  them read STALLED and `broke()` names one "stopped first" at 09:15.
- **d. The two tapes disagree on the day's CVD sign.** On NIFTY the Upstox ladder ended at −2,558
  and GoCharting at +2,280, and bar-delta sign agreed on only 64% of bars. The 13:36 CONTRADICTED
  rests on Upstox's side attribution, which is [I].
- **e. trigger_log has 7 BANKNIFTY 09-23 zone rows written twice.** The copies were all written at
  17:43:00 and carry `gate: null, "near-ATM fronts not read"`. `/api/signals`' zone count includes
  them. The page de-duplicates first-write-wins.
- **f. OI step size, measured.** NSE OI changed on 96% (NIFTY) and 92% (BANKNIFTY) of minute marks,
  so the research's "exchange OI steps every ~3 min" does not hold for NSE via Upstox. BSE/SENSEX
  was unchanged on 63% of minute marks, so SENSEX peak stamps carry ±3 min, and the page says so in
  amber.
- **g. The drag day trace has samples after 15:30** (`day_state` has samples stamped 18:12). The
  "nothing recorded after the close" rule does not cover it.

## 7. The one question that changes her METHOD

**Is "near ATM" nine strikes, or a distance?** On NIFTY, nine strikes is ±200 pts (about 0.85%). On
BANKNIFTY and SENSEX it is ±400 pts, and on 09-23 that made a 57000 straddle, 410 pts away, the
BANKNIFTY headline front for three hours. `NEAR` is §1d's pre-registered parameter, so any change
is hers to make. Everything else here is presentation and was decided above.
