# Deferred — decided to do later, not forgotten

Opened 2026-08-07 at the operator's request: *"isko baad m krte h ek file m ye
sb rkhna jo baad m krna h"*.

**What belongs here.** Work that was found, measured, and consciously postponed.
Not a wishlist — every entry carries the measurement that found it, so the next
session can act without re-deriving anything. An entry with no evidence does not
belong in this file.

**What does NOT belong here.** The rules register is `CHECKLIST.md`; strategy
verdicts are `research-findings.md`; the styling backlog is `ui-audit.md`;
finished work is `progress-tracker.md`. This file links to those rather than
restating them.

---

## 0 · THREE DECISIONS OWED BY THE OPERATOR — nothing waits on code

These block real work and must not be guessed. Two of them were guessed once
already today and both guesses were wrong (CHECKLIST C13).

1. **The CALL-heavy threshold** for the short's target extension. No percentage
   given. 40% is the only number in the record and it sits there as a REJECTED
   entry filter (C11) — borrowing it would borrow a number from a question it
   was never asked. Best answered by watching the live CALL-heavy % for a
   session or two rather than picking in the abstract.
2. **Does an ARMED buy close a short, or only a TRIGGERED one?** ARMED exits
   sooner and more often; TRIGGERED is the actual signal.
3. **What "pass" means for the live forward test** (§5e) — per-trade points,
   hit rate, or a ratio against the 20-point stop. §5f's evidence argues for
   **median and hit rate, not mean**: at n≈19 the mean is hostage to one or two
   trades on BOTH sides.

Once 1 and 2 land, the short-exit rules in
`docs/superpowers/specs/2026-08-08-operator-short-exit.md` can be built.

## 1 · Premium / discount is measured on the wrong range · BACKEND

**Status:** operator has seen the numbers and deferred the fix. The three
options below were put to them; none chosen yet.

`structure.py:482` takes the working range from `prev_sh` / `prev_sl` — the
previous confirmed swing high/low pair. Those are 1-minute fractal pivots, so
two consecutive swings sit 8–16 points apart on NIFTY.

Measured live, 2026-08-07 (NIFTY, 385 bars):

| | |
|---|---|
| session range | 24601 → 24707 (106 pts), equilibrium **24654** |
| published PREMIUM | 24655 → 24663 |
| published DISCOUNT | 24647 → 24655 |
| so the range used | **16 points** |
| PD pairs per session | **56** |

So it publishes the premium/discount of the last 1-minute micro-swing, not of
the leg being traded. ICT's premium/discount is a **dealing range** read.

**This is not a crash and must not be smuggled in as a "bug fix".**
`structure.py`'s own comment records the box counts (44/43/57 per day) as
measured, so the current behaviour is deliberate. Changing it is a change of
DEFINITION, which is the operator's call, and a backend change, which CHECKLIST
F2 says must be separate and explicitly agreed.

Options as put to the operator:
1. **Swing pair with a minimum size** (e.g. range ≥ 1σ, ~22 pts today) — the
   ICT dealing range. Recommended. Collapses 56 pairs to a handful.
2. **Session high → low** — one stable pair all day; goes wide by the close and
   on a trending day the "discount" half marks where price was this morning.
3. **Leave it** — then the 16-point band keeps claiming to be a premium/discount
   zone, which is the thing that looked wrong.

Needs: the change, tests (432 now), and a note in `CHECKLIST.md`.

## 2 · Structure lines carry no text · FRONTEND

**Status:** operator deferred — *"isko rehnde filhall"*.

`LevelsOverlay.drawStructures` labels only `confirm === 'CONFIRMED'`.

**Measured on the live 2026-08-07 payload: that yields ZERO.** Not "few" —
nothing in the session is CONFIRMED, so the rule deletes 100% of the labels.
Of ~93 marks actually drawn (12 OB boxes, 58 swing ticks, 18 EQH/EQL pools,
3 PD lines, 2 range bands) only the 3 prior-day lines carry text, because those
have their own always-label branch.

The rule was written to thin 479 labels off ~180 structures. That pressure is
gone: FVG (~85 boxes) and BOS/CHOCH were dropped on 2026-08-07, so a label
budget now exists.

Direction proposed, not yet chosen: label by KIND, not by `confirm` — OB /
EQH / EQL / PD always named (~35 labels), swings left unlabelled (58 is the
noise problem), and let confirmation keep doing what it already does through
opacity and the dashed border.

## 2b · ~~The SETUP CHECK panel is BUY-only~~ · **DONE 2026-08-08**

The panel now reads both machines and NAMES the side it is showing (a
`BUY · d3` / `SELL · u3` badge beside the state word). A side that is not
WAITING wins; with both live the BUY side shows and a caution line says the
sell side is armed too, because picking silently would hide half the machine
and preferring the scored side is the only defensible tie-break.

The 68.4% / n=19 note is swapped out on a sell for the sentence saying that
side has no score. A number belonging to one rule must not ride along beside
another.

## 3 · Left-edge level labels · FRONTEND

**Status:** open in `ui-audit.md` under Readability as **FAILING**; the operator
circled it on 2026-08-07 and then redirected to the line weights instead.

Three faults in one place:
- the price is drawn **twice** — in the left label and again in the right-axis
  chip;
- on collision the left label is **dropped**, so a level can end up with no name
  anywhere;
- 8.5–11px against the σ ribbon fills is under-contrast.

Direction proposed, not yet chosen: name on the left in a filled chip, price on
the right axis only, and de-collide by **nudging** rather than dropping.

## 4 · ~~The stop is not published~~ · **DONE 2026-08-09**

Done exactly as specified: one field. `band_rotation._stop_px(level, stop_pts,
sell)` is now the single expression, called by BOTH the re-fire lock and the
published field — the file's own warning above `OPERATOR_STOP_PTS` says two
copies of a risk parameter drift silently, and a stop the chart draws differing
from the stop the lock enforces is that failure. It is emitted on every
`run_state` bar beside `level`, and on the entry record.

`RunState.stop` is **optional** in TypeScript on purpose: a server on older code
omits it, and the panel then shows NO stop line rather than computing `level`
minus 20. Absence is the correct rendering of "the server did not say".

SETUP CHECK now pairs it with the line to beat (`Todna hai > X` / `Stop < Y`),
muted rather than red — theme.ts reserves red for direction, and a stop is not
a bearish call.

Tests: `test_band_rotation_run.py` §7, six of them, including the BUY/SELL
mirror (a short's stop sits ABOVE the band) and the assertion that a moving
reference does NOT move the stop.

**Not yet seen on screen.** 2026-08-09 is a Sunday and the session carries no
bars, so no setup can arm and the line cannot render. First live look is
Monday, alongside the collection check.

## 5 · MERA READ ships empty · needs the OPERATOR, not code

The panel's third group is the operator's own rules and starts empty. Asked
twice on 2026-08-07 what those rules are; not answered. Seeding it with three
invented lines is exactly what CHECKLIST A2 forbids, so it stays empty until
they say what goes in it.

## 6 · Hinglish stops at the Trade tab's chrome

Done: the SETUP CHECK panel, the stat strip, the toggles and their tooltips,
the disclosure lines, the legend, the `Chhupa hua:` line, EngineReadPanel's
labels, ZoneRead's `Kahan` group.

Still English: **ZoneRead's body sentences** ("no EQH pool above", "formed;
sweep not tracked"), the **leg panes** (`LegChart`), and **`App.tsx`'s CHAIN
STALE banner** plus the glance bar and ANSWER band.

Deliberately never translated, and this must survive any future pass: every
string the BACKEND authored and the UI quotes verbatim — `ctx.vwhy`, `ctx.line`,
`ctx.breadth`, `ctx.plays`, the setup fields, `trap_why`, `confirm_why`,
`structuresWhy`, `rotationRunWhy`, `flowWhy`. Translating a quote breaks
EngineReadPanel's stated promise that it shows the engine's own read.

## 7 · The session key reads oddly

`day` arrives as the literal string **`"Aug 07 LIVE"`** — no year, and with
`LIVE` inside the key. The UI renders it verbatim (A2), and `dayPrecision`
already discloses the missing year. Owed decision: fix the key at source, or
have the panel show only the date part.

## 8 · The styling backlog is elsewhere

`ui-audit.md` holds the P1/P2 items — contrast, focus indicators, ARIA,
`prefers-reduced-motion`, `transition: width`, the side-tab borders, 22
hard-coded hex values, `tabular-nums`. The operator's standing decision on
2026-08-06 is *"changes live market mein karenge"*. The SETUP CHECK panel meets
all of them from the start; the rest of the app does not.
