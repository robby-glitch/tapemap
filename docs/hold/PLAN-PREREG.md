# PRE-REGISTERED — THE PLAN: STOP · NEXT RUNG · ROOM (rev 3, written 2026-09-25 09:00 IST; rev 2a signed 09:31; the band rung, rev 3, signed 13:20; before any code, UNTESTED)

A second registration, beside the hold window's (`PREREG-merged.md` rev 4, signed 2026-09-25 01:42).
It is needed because that window's §5 reads "never a target, a stop price", and this adds a stop and
the next place the move must fight. **The window's rules are not changed by one word.** Nothing
below is a result. Until §6 passes, every line of it carries DRAFT.

**Her decisions, 2026-09-25, verbatim:**
- "think for yourself building a tool to tell you if you can hold your trade target you can aim for
  stoploss one should look for";
- on who takes the runner out, and on booking at a defended wall: "again depends on market leave the
  size to me".

So the plan **never** sizes, never says "book" or "exit", and never merges its two exits into one.
It prints the facts; she decides.

**What had been seen when this was written:**
- A description of her 29 round trips of 09-22 → 09-24 (`plan_rows.py` in the session scratchpad):
  - the line at entry;
  - the nearest swing, the session extreme and the nearest sized wall in the way;
  - what the index and her premium did to 15:29.
- The six scenarios drawn from those rows.

Every object below already exists in the signed window (§2 of rev 4), in §1d, or in the chain
record. **No number was chosen by looking at those rows, and no new number is introduced.**

## 1. Why

Her rows, in-sample, described:
- **Well-placed entries were exited in minutes.** Examples: 09-24 12:32 SENSEX 74100PE, +₹546 taken
  when the line held to 14:35 at +240 pts; 09-23 10:00 NIFTY 23450CE, −₹507 before the ceiling in
  its way folded.
- **Late entries far from structure were exited fast, correctly.** Example: 09-24 13:57 SENSEX
  73800PE, entered 378 pts from the line with no wall in the way; +₹592 taken, and it was −187 pts
  by 15:25.

A fixed target would have repeated the first leak: the nearest swing was touched within minutes on
most of them. What she lacks is not a price. It is, at entry and at each obstacle, **which kind of
trade this is**.

## 2. The three lines, every finished minute, beside the window's word

Every input is cut to the finished minute `t`, exactly as the window's §2. **Buyers only** (long CE
/ long PE). A writer's plan is the stop alone (§2.6).

**2.1 STOP [M]: the line.**
- It is the window's line L itself: the same construction, trail and break, and the same blind rule.
- Shown: the index level, its room in points, and the premium at risk if it broke now.
  - The risk is a second-order Taylor expansion, per unit × qty:
    - **for a buyer**, `|Δ| × room − ½ × Γ × room²`, because gamma cushions a holder, clamped to
      between 0 and the premium now, since a buyer cannot lose more than the premium;
    - **for a writer**, `|Δ| × room + ½ × Γ × room²`, because gamma hurts a writer.
  - Δ and Γ are the broker's own delta and gamma for her strike-side in the chain record's latest
    snapshot at or before `t`. That makes the estimate [I] on [M] greeks.
  - (rev 1a, 09:10: the gamma sign was one formula for both roles; corrected before any review
    or signature.)
  - "could not check — no greeks for this strike in the chain record" when absent.
  - The line is in **index points** because her chart is the index. The premium figure is an
    estimate, and on 0DTE it is labelled so.

**2.2 NEXT RUNG [M]: the next wall in the way.**
- From `fronts.read` at `t`: the nine strikes nearest spot, top 2 per side by the running session
  peak, the window's §2 ranking.
- The rung is the nearest **sized** front (peak change since the open > 0) on the side that must
  pay for her move, **strictly beyond the index in her direction**:
  - a long PE's rung is a PE front below the index;
  - a long CE's rung is a CE front above.
- If none: the session extreme in her direction, if it lies beyond the index, labelled "session
  low / high — no sized wall inside the nine".
- If the index is at or through that extreme: "no wall in the way — price discovery".
- The rung is shown **at all times** with the three words of §2.4, and the raw §1d state beside it
  [M] (S2):
  - **DEFENDED** if the front reads BUILDING;
  - **GIVING WAY** if it reads UNWINDING, or a live fold stands on that strike (within 15 minutes
    AND `board.still_folded`, the window's S3), which reads "folded HH:MM";
  - **STALLED** otherwise.
- Every word carries whose favour it is in, for a call and a put alike (S3). "Support giving way" is
  good news for a put buyer, the reverse of a futures trader's instinct:
  - DEFENDED is "the writers in your way are holding — against your move until they give";
  - GIVING WAY is "the writers in your way are leaving — in your favour";
  - STALLED is "the writers in your way stopped adding — neither yet".

**2.3 ROOM [M].** Two numbers, never a ratio shown as odds: `rung N pts · stop M pts`.
- When N < M, one sentence: "you risk more points to the line than the next rung is away".
- When there is no rung: "no wall in the way — the stop is M pts behind you".
- This is the entry line as well, printed beside the window's entry check.

**2.4 AT THE RUNG.** A rung is touched at the first finished minute whose 1-min index low (a
long PE) or high (a long CE) reaches the rung's strike or level.
- **One touch per (trade, strike, side)** (S1). A retest of the rung while it is still selected
  is not a new touch.
- After a hand-over, a different strike is a new touch.

At the touch minute the plan prints one word, the §2.2 word as it stands at that minute:
- **DEFENDED** if the rung front reads BUILDING;
- **GIVING WAY** if it reads UNWINDING, or a live fold stands on it;
- **STALLED** otherwise.

A session-extreme rung has no writers to read. Its touch prints "session low / high touched — no
wall read there", and it is not counted in §6.

From the next minute the rung is recomputed by §2.2, so a wall that gave way hands over to the next
one. There is no size advice and no "book" (her decision).

**2.5 THE RUNNER: two exits, side by side, never merged.**
- `the line: <L>, M pts` and `the window: <word · rule · since>`.
- The side read (rev 4 §10) is printed beside them as the market's context.
- Which one governs her exit is hers: "depends on market".
- The plan never prints "exit". The window's FOLD keeps its own meaning and its tone.

**2.6 A writer.** STOP only: the danger-side line (rev 4 §4), with the room and the premium at
risk from Δ and Γ. There is no rung, because time pays a writer and rev 4 §4 already reads her
side's wall.

**2.7 THE BAND RUNG (rev 3, from `PLAN-ADDENDUM-rev3.md` rev 3a, signed 13:20).**

**Buyers only; a writer's plan stays the stop alone.**

**The rung.** For a long PE the band rung is **d2** on the zone machine's own session-VWAP bands of
the near future (3-minute). For a long CE it is **u2**. It is shown beside the wall rung of §2.2,
never merged with it:
- `BAND d2 · now z −1.2 · target z −2`;
- the distance is in σ, because the bands are on the future and the line is on the index. No
  points are converted between the two.
- **The BAND line carries its own units clause (S3):** "σ on the future — not points, never
  comparable with the stop's index points".

**Its word** comes from the zone machine's own §1d gate on the **opposite fade** at that band (M1).
- **The exact lookup:** the `gate` on the `data/trigger_log.jsonl` row with `rule: "zone"`,
  `kind: "arm"`, `index` = hers, `side` = the band's own native fade (BUY at d2, SELL at u2), and
  `t` = the touch bar. `DEFENDER` makes "BUY legal at d2" mean the put writers at the band are
  building.
- It is read at the band only, meaning the 3-min bars that the zone machine itself arms at ±2σ.

Four outcomes, **each its own sentence, never merged**:
- **GIVING WAY:** `gate.legal` is false. "The floor/ceiling at the band is giving way — in your
  favour; the move may run past the band".
- **DEFENDED:** `gate.legal` is true. "The floor/ceiling at the band is defended — against your
  move".
- **could not check:** `gate.legal` is null (PATA NAHI), printed with `gate.why`.
- **checked, none:** there is no zone arm row for this bar at all. The machine did not arm there,
  either because the bar set no fresh extreme or because an earlier same-band trigger's re-fire
  lock is still open. It prints "the zone machine did not arm at this bar — no band word; the
  last word stands (HH:MM)", or "no band word yet" if there was none.

**The opposite trigger** (BUY d2 for a put, SELL u2 for a call) is printed as an event with its
time and legality, e.g. "BUY d2 triggered 09:54 (legal) — the other side has taken over".
- It is a fact, not an instruction.
- As in rev 2a, the plan never says "exit" or "book", and never sizes. Which one governs is hers.

**The entry line** gains one fact when a same-side zone trigger preceded her entry that session:
"entered N min after the SELL u2 trigger at HH:MM [M, trigger_log's clock]; the premium had moved
±P since [I, the chain record's last trade]". Each number carries its own tag (S2). It is a
description of timing, never a gate.

## 3. What is shown

**Open window:** three lines under the window's four rows:
- `STOP 74,114.9 · 101 pts · ≈ ₹X at risk [I]`;
- `RUNG PE 74,000 · 14 pts · GIVING WAY — the writers in your way are leaving — in your favour · UNWINDING, folded 12:27 [M]`;
- `ROOM rung 14 · stop 101`.

**At a touch:** the word, with the time.

**Collapsed:** the window's line gains `· rung 14 pts giving way`. **Never P&L, never a size.**

**Not shown, and said so:**
- "not shown — a size: the plan leaves the size to you";
- "not shown — a single exit: the line and the window both stand; you choose".

Three absences as ever: "checked, none" / "could not check — why" / "not showing you — why".

## 4. Parameters: all inherited, none new

| object | value | from |
|---|---|---|
| the line, trail, break, blind | as rev 4 §2 / §6 | the signed window |
| the nine, top 2, running peak, §1d state | 9 · 2 · §1d | fronts / rev 4 §2 |
| sized | peak change since the open > 0 | board (`built`) |
| fold liveness | ≤ 15 min AND still folded | rev 4 S3 |
| touch | the 1-min index low / high reaches the level; one per (trade, strike, side) | rev 4's candle |
| next15 | max favourable index excursion over the 15 finished minutes after touch, from the touch close; to 15:29 flagged short | rev 4 §7's extremum |
| premium at risk | Taylor to 2nd order on the broker's Δ, Γ; −½Γ for a buyer (clamped 0…premium), +½Γ for a writer | chain record |

Changing any one is a new registration.

## 5. The forward log

The window's trade row (rev 4 §8, `data/hold/hold_<day>.jsonl`) gains one additive key, and no
field is changed:

Two row shapes (M2). Neither is ever rewritten.

```
the trade's per-minute row (rev 4 §8), one additive key:
  plan: {stop: {L, room, risk, risk_why}, rung: {src: "wall"|"session"|"none", side, k, room, word, state, fold_t},
         touch: null | {k, side, word}}          -- set on the touch minute's row only

its own row, written once the touch's window has finished (the stamp_track discipline):
  {kind: "rung_touch", trade_id, touch_t, idx, k, side, word, close_at_touch,
   next15: {pts, to, short}}                      -- keyed (trade_id, touch_t)
```

`next15.pts` [M] is the **maximum favourable index excursion** over the 15 finished minutes after
the touch minute, measured from the touch minute's 1-min close (M1). It is the extremum, as in rev 4
§7, never the value at the 15th minute:
- a long PE: the close at touch minus the lowest 1-min low;
- a long CE: the highest 1-min high minus the close at touch;
- never below 0.

A touch after 15:14 is measured to 15:29 and flagged `short: true`, never padded.

**The band rung's row (rev 3).**

- Each band touch (the first 3-min bar at ±2σ after her entry) gets its own write-once
  `band_touch` row: `{trade_id, t, band, word, gate_why, opposite_trigger_t|null, next15}`, with
  `next15` exactly as §5 (M1) defines it.
- One per (trade, band).

## 6. Prediction and falsifier, committed in advance (forward rows only)

- **P1.** After a GIVING WAY touch, the index goes further in her direction over the next 15
  finished minutes than after a DEFENDED touch. Two distributions of points, medians and full rows
  shown, split by index, never a rate.
- **Falsifier.** P1 is judged once ≥ 15 touches of each word **and** ≥ 10 sessions exist, and in
  any case at 30 sessions.
  - If P1 does not hold, or it reverses when the single best day is removed, the rung's WORD is
    deleted.
  - STOP and ROOM stay as display: they are distances, not claims.
- **Inconclusive.** At 30 sessions with fewer than 15 of either word, the words stay DRAFT.

**P2.** After a GIVING WAY band touch, the index goes further in her direction over the next 15
finished minutes than after a DEFENDED band touch.
- The unit is rev 2a §6's: two distributions, medians and full rows, split by index, never a rate.
- It is judged at at least 15 of each and at least 10 sessions, and by 30 sessions at the latest.
- It must survive removing the best day.
- If it fails, the band words are deleted, and the band stays as a level.

**Disclosed (S1).** One sharp move can touch her wall rung and the band in the same 3-min bar.
That hands P1 and P2 a sample from the same cause, in overlapping windows.
- The two stay separate populations (different row kinds, never pooled).
- A band touch in the same bar as a wall touch carries `also_wall_touch: true`, so the overlap can
  be counted, and each falsifier can be read with those rows removed.

## 7. Unsolved, stated

- **A wall beyond the nine** is not seen. The rung says "no sized wall inside the nine", never
  "none".
- **The ceiling or floor stepping a strike** (rev 4 §9.1) looks like GIVING WAY followed by a new
  DEFENDED rung one strike on. Whether that is the move continuing or ending is what P1 measures.
- **On 0DTE afternoons with both sides unwinding,** most rungs read GIVING WAY or are absent. The
  stop and the room carry the plan there.
- **The premium at risk is an estimate:** a Taylor expansion is least trustworthy exactly where
  gamma is largest, on expiry. Hence [I], and the stop is stated in index points.

**The band rung (rev 3):**

- **The bands are on the future, the line and the walls on the index.** The two are shown side by
  side, never converted.
- **Early in the session the bands are narrow.** Today u2 → d2 took 6–9 minutes, so the band is
  reached fast and the word carries the plan.
- **She named "the sellers getting aggressive" as a hold reason.** The window's ORDER FLOW row
  already reads it (strict: CVD strong AND prints dominant). Today it read FLAT at 09:39 (CVD −7,
  3 sell / 5 buy prints) and WITH her from 09:52. No change is proposed to that row.

## 8. Change log

- **rev 1a:** the gamma term's sign, split by role (a buyer −½Γ clamped 0…premium; a writer +½Γ).
  Found checking the reviewer's delta-sign question, before any signature.
- **rev 2:** the fixes from `docs/hold/PLAN-REVIEW.md` (Sonnet, the independent reviewer; its
  verdict on rev 1a was NOT YET):
  - **M1:** `next15` is the maximum favourable excursion (rev 4 §7's extremum) from the touch close,
    to 15:29 and flagged short after 15:14.
  - **M2:** the §5 schema is printed as two row shapes; `next15` lives only on its own
    `rung_touch` row.
  - **S1:** one touch per (trade, strike, side).
  - **S2:** the rung shows the §2.4 word at all times, with the raw §1d state beside it.
  - **S3:** every word says whose favour it is in, so a put screen does not read backwards.
  - Nothing inherited moved; no new number was introduced.
- **rev 2a:** the reviewer's second pass was SIGNABLE. Its one cosmetic carry-over is fixed: §3's example
  shows the raw §1d state beside the word.
- **rev 3:** the band rung (§2.7), its `band_touch` row (§5), P2 (§6) and its unsolved items (§7),
  merged verbatim from `PLAN-ADDENDUM-rev3.md` rev 3a (sha256 `ea068017…bf26`; Sonnet NOT YET on rev 3,
  M1 and S1–S3 fixed in 3a). Signed by the operator 2026-09-25 13:20, her word "sign". Nothing in
  §1–§6 of rev 2a moved; no new number.
- **rev 3a (2026-09-25 21:00, a pointer, no PLAN rule moves):** the STOP the plan prints is the window's line, and
  the window's break is now `PREREG-rev5.md` option B (signed 19:40): a 3-minute close beyond L by more than one
  frozen median 1-minute candle. The STOP line prints that break level beside L, and its premium sentence reads
  "≈ ₹X [I] of premium between here and the line" (rev 5 §D item 12). §4's "the line, trail, break, blind — as
  rev 4" now reads "as rev 4, the break as rev 5 option B".
