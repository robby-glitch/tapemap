# Review: `docs/hold/PLAN-PREREG.md` rev 1a — THE PLAN: stop · next rung · room

Independent review, same role as `docs/hold/opus/PREREG-REVIEW*.md`. Checked
against `PREREG-merged.md` rev 4 (the window the PLAN sits beside, unchanged),
`hold.py`, `fronts.py`, `board.py` (`fronts.read`, `board.still_folded`,
`board.state_words`), CLAUDE.md's house rules, and one streamed line of
`data/chain/chain_NIFTY_2026-09-24.jsonl` (13 MB files — read with
`readline()`, never loaded whole).

## What checks out

- **Payers' wall, both legs.** §1's table (Q = PAYERS) makes a long CE's rung
  a CE wall *above* and a long PE's rung a PE wall *below* — "strictly beyond
  the index in her direction" reduces to exactly that, correctly, for both.
- **Greeks and sign convention.** Streamed line 1 of
  `chain_NIFTY_2026-09-24.jsonl`: CE delta ∈ (0,1), **PE delta negative**
  (e.g. k=23250: CE Δ 0.522, PE Δ −0.4769), gamma positive on both legs at
  the same strike. The formula uses `|Δ|` throughout, so the PE sign never
  enters it — worked by hand: for a long option, an adverse move of `room`
  points gives ΔV = Δ·ΔS + ½Γ·ΔS² with ΔS signed to the adverse side; using
  `|Δ|` collapses CE and PE to the same `|Δ|·R − ½ΓR²` expression, and the
  mirror-signed writer case to `|Δ|·R + ½ΓR²`. Both clamp directions
  (0…premium) are stated for the buyer; correct.
- **Fold liveness, touch, DEFENDED/GIVING WAY/STALLED.** `still_folded`
  (board.py:190) already guards on "not currently BUILDING," so a live fold
  and BUILDING can never coincide — the touch-word priority (DEFENDED beats
  GIVING WAY beats STALLED) is well-ordered, exhaustive over fronts.py's
  three states, and causal (reads only `fronts.read` cut to `t`).
  Session-extreme and writer cases are both handled and excluded/absent
  correctly (§2.4's last line; §2.6).
- **Her two decisions.** No occurrence of "exit" or "book" in any printed
  string; STOP and the window's word are shown side by side, never merged;
  no size is proposed anywhere (the one `qty` multiply in §2.1 scales an
  **existing** position's rupee risk, it does not choose one). §4's
  parameter table introduces no new number — everything traces to rev 4,
  `fronts`, or `board`.
- **No hit rates.** §6 is medians/full-rows/counts throughout, split by
  index, "never a rate" — matches CLAUDE.md rule 4 and rev 4's own style.

## Must-fix

**M1 — §6's P1 excursion is not pinned down.** "The index goes further in
her direction over the next 15 finished minutes" does not say *how* —
the value at minute+15 (an endpoint), or the best point reached inside the
window (an extremum)? Rev 4 §7 deliberately defines its own "Excursion" as
an extremum, not an endpoint, for exactly this reason (a single late
reversal shouldn't flip the reading). Left open, two honest
implementations of this same registration would score the same touches
differently — the "no parameter chosen after data" guarantee depends on
this being fixed **before** any row is logged, not decided while coding it.
Fix: state whether `next15.pts` is the max favourable index excursion over
the 15 finished minutes after touch (recommended, matches rev 4's own
practice) or the point-15 value, and say so in §4's parameter table too.

**M2 — §5's schema contradicts its own prose on write-once.** The printed
block shows `touch` and `next15` as two keys of the *same* `plan` object on
the trade's per-minute row, commented "on a touch row only, filled by the
row 15 finished minutes later" — read literally, that asks the row written
at the touch minute to be edited 15 minutes after it was written, which
breaks rev 4 §8's "never rewritten." The sentence right after it says the
opposite: `next15` lives on its *own* `rung_touch` row, keyed `(trade,
touch minute)`. The prose is right and consistent with rev 4's append-only
discipline; the schema block is not. Fix: print two row shapes — the
per-minute trade row carries `stop`, `rung`, `touch` only; a separate
`rung_touch` row (its own key, `trade_id` + `touch_t`) carries `next15` —
so an implementer reading only the code block can't be led into an in-place
edit.

## Should-fix

**S1 — Touch individuation is undefined.** If the selected rung doesn't
give way and gets poked more than once (a retest, index bounces off the
same still-current wall twice), does each poke fire a new touch/`next15`
sample, or only the first touch of that strike? Left open, a single
choppy session at one wall can quietly inflate "≥15 touches" with
correlated, non-independent samples — the same failure mode §6's
"collapses if the single best day is removed" clause exists to catch, but
for the whole session rather than one wall. State the rule (suggest: one
touch per `(trade, k, side)`; a retest of the still-selected rung is not a
new touch).

**S2 — Which words the rung shows *before* a touch is inconsistent.** §2.2
says the rung's ongoing state is "the front's §1d state at `t`" (i.e. raw
BUILDING/STALLED/UNWINDING), but §3's own worked example prints "giving
way" continuously, pre-touch, in the open window. §2.4's DEFENDED/GIVING
WAY/STALLED mapping is clearly what's meant everywhere the rung is shown,
not a word invented only at the instant of touch — say so in §2.2 directly.

**S3 — "Giving way" reads backwards for a put.** A support wall below
"giving way" is *good* news for a long PE (the floor is being paid through,
her move is easier) — the opposite of how "support giving way" ordinarily
reads to an equities/futures eye (support breaking = bad). The long-CE case
doesn't have this inversion (a ceiling giving way above is the ordinary
bullish reading both ways). One clause tying the word explicitly to
"favours you" / "against you" would stop a fast reader from applying the
wrong instinct to a put screen at speed.

## Notes, not fixes

- In-sample only, zero evidential weight, not tuned to it: I did not re-derive
  her 29 round-trip rows from `facts_*.json.gz` / `trades.json` — the §1
  motivation reads as narrative, not a registered rule, so nothing there
  needed testing for ambiguity beyond what M1/S1/S2 already found
  analytically.
- The trade object needed for the Δ/Γ lookup (`k`, the strike) is not
  listed in `hold.py`'s own `read()` docstring, but it is present on trade
  dicts elsewhere in the tree (`test_hold.py:37`) — the object exists, only
  the docstring is silent on it. No fix needed.
- §2.2's rung independently re-derives `fronts.read`'s full top-2-per-side
  output rather than reusing `hold.py`'s already-reduced per-minute
  `CE`/`PE` (nearer-only) fields — necessary, since "strictly beyond the
  index" sometimes needs the *farther* of the two, and confirmed
  computable from the same function the window already calls.
- 09:15 bootstrap (fronts forming, line = session extreme so far) is
  inherited from rev 4 unchanged and already self-disclosed via the
  existing blind-rules text; the PLAN adds nothing new to misread there.

## Verdict: **NOT YET**

Must-fix before signing: **M1** (pin down what "goes further… over the next
15 minutes" measures) and **M2** (make the §5 schema block match its own
write-once prose). Both are small, precise edits, not re-registrations —
nothing in rev 4 or in the PLAN's own inherited parameters needs to move.

## Second review: rev 2

Checked rev 2 (§8 change log) against rev 1a's M1/M2/S1–S3.

- **M1 — closed.** §4 and §5 now both say `next15.pts` is the **maximum
  favourable index excursion** over the 15 finished minutes after touch,
  measured from the touch minute's 1-min close, floored at 0, per-side
  formula spelled out (PE: close − lowest low; CE: highest high − close),
  explicitly "never the value at the 15th minute." Matches rev 4 §7's own
  extremum practice. No ambiguity left.
- **M2 — closed.** §5 now prints two row shapes: the per-minute trade row
  carries `stop`, `rung`, `touch` only; a separate `rung_touch` row (keyed
  `trade_id` + `touch_t`) carries `next15`, written once the window has
  finished. Prose and schema now agree, and both say "never rewritten."
- **S1 — closed.** §2.4: "one touch per (trade, strike, side)... a retest
  of the rung while it is still selected is not a new touch," with a
  hand-over to a different strike explicitly counted as a new touch.
- **S2 — closed.** §2.2 now states directly that the rung shows the §2.4
  word "at all times," with the raw §1d state beside it, and §2.4
  cross-references "the §2.2 word as it stands" rather than restating a
  second definition.
- **S3 — closed.** §2.2 adds the favour clause verbatim for all three
  words (DEFENDED against her, GIVING WAY in her favour, STALLED neither),
  naming the put-support reversal explicitly.

**No new number.** Every addition (the touch-close baseline, the 15:14 late-
touch cutoff, the per-strike touch key) is arithmetic or wording on top of
numbers already in rev 4 or already in the PLAN; nothing was chosen fresh.

**One residual, not blocking.** §2.2's rule now requires the raw §1d state
("BUILDING"/"UNWINDING"/"STALLED") to be shown beside the derived word at
all times, but §3's worked example (`RUNG PE 74,000 · 14 pts · giving way
(folded 12:27)`) was not updated to show it — an implementer building the
screen from §3 alone would under-render what §2.2 now asks for. Cosmetic:
the fact was already computed (fronts.py's own state), nothing new to
compute, no forward-log field affected, no falsifier affected. Fix the
example line in §3 before or alongside first build, not before signing.

### Verdict: **SIGNABLE**

No must-fixes remain. One should-fix carried forward (update §3's example
to show the raw §1d state alongside the word, per §2.2's own new text).
