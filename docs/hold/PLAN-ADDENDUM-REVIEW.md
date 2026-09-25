# Review: `docs/hold/PLAN-ADDENDUM-rev3.md` — §2.7 THE BAND RUNG

Independent review, same role as `docs/hold/PLAN-REVIEW.md`. Checked against
the signed `PLAN-PREREG.md` rev 2a, `band_rotation.run_states` (the zone
machine, arm/rearm/re-fire-lock mechanics), `fronts.fade_gate`/`DEFENDER`,
`trigger_log.py`'s `_arm_rows`/`_gate_at`, CLAUDE.md's house rules, and 28
2026-09-25 rows in `data/trigger_log.jsonl` (grepped, never loaded whole).

## What checks out

- **The addendum's own table is accurate.** Grepped NIFTY 09:33/09:36/09:39/
  09:42/09:51/09:54 rows match its narrative verbatim, including the exact
  `gate.why` strings ("PE 23000 stopped building at 09:36", "... gave up its
  build at 09:36", "... still building").
- **"The opposite fade" resolves to a real, already-stored field.**
  `DEFENDER = {"buy": "PE", "sell": "CE"}` — the zone's own native fade at d2
  is BUY (bet the PUT writers hold, i.e. a bounce), which is exactly the bet
  *against* a long PE's continuation. So "opposite fade legal" ⇔ the same
  `gate.legal` already stamped by `_gate_at` on that band's own `rule:"zone",
  kind:"arm"` row — no second gate call, no new number.
- **No "exit"/"book"/size in any printed string** — the one occurrence of
  those words is in prose describing the rule, not in a rendered string.
  P2's falsifier bar (≥15/side, ≥10 sessions, 30 at latest, survives dropping
  the best day) is copied verbatim from rev 2a §6, nothing chosen fresh.
- **Touch individuation is unambiguous**: "the first 3-min bar… one per
  (trade, band)" has no S1-style retest gap — it's the first touch, full
  stop, no second reading possible.

## Must-fix

**M1 — the band word is computable only when the zone machine's arm
mechanism actually fires on that bar, and the addendum never says what
happens when it doesn't.** `run_states` only emits a fresh `arm` dict (and
therefore a fresh `gate`) on a bar that (a) is a first touch past
`ANCHOR_MINUTE`, or (b) extends the reference to a new further extreme
(`rearm: True`) — confirmed on today's own d2 rows (23108.5→23098.8→
23080.7→23076.3, one arm per new low). A bar that sits at/through the band
*without* setting a fresh extreme gets **no** `arm` row at all (state stays
ARMED, `arm=None` on that bar) — nothing to attach a gate to, not even
`legal: None`. Worse: if an earlier same-band trigger's re-fire lock is
still open (hasn't hit stop or reached VWAP), arming is suppressed
*entirely* until it clears — a real scenario if her entry follows an earlier
same-direction zone trigger that session. "Could not check — PATA NAHI" as
written describes a gate object that *was* read and came back inconclusive;
it does not cover "there is no zone arm row for this bar to read a gate
from," which is a different absence and needs its own sentence. Fix: name
the exact lookup ("the `gate` on the `rule:"zone", kind:"arm"` row at this
band whose `t` matches this touch bar, `side` = the band's own native
direction — BUY at d2, SELL at u2") and add the third case: no such row
exists (not armed / lock still open) → say so, distinctly from PATA NAHI.

## Should-fix

**S1 — P1 (wall) and P2 (band) samples can fire off the same underlying
move in the same minute.** They're correctly kept as separate populations
(different row kind, never pooled), but a single sharp move can touch both
her rung *and* the band in the same 3-min bar, handing both falsifiers a
sample drawn from the same cause in overlapping 15-minute windows —
correlated, not independent, across the two studies. Not a rule violation
(each stays internally correct), but worth one disclosed sentence, the way
"survive removing the best day" already guards the single-session version
of this same risk.

**S2 — the entry-timing fact tags a compound sentence with one blanket
`[I]`.** "entered N min after… at HH:MM" is `[M]` (read straight off
`trigger_log`'s clock); only "the premium had moved ±P" is `[I]` (a chain
lookup). CLAUDE.md rule 7 wants each number tagged for what it is — split
the tag rather than covering both under `[I]`.

**S3 — the future's σ and the index's points sit side by side with nothing
stopping a fast read from treating them as one scale.** The addendum is
explicit that nothing is converted (correct — no invented conversion), but
"BAND d2 · now z −1.2 · target z −2" next to "STOP … 101 pts" is exactly the
kind of juxtaposition a 20-year eye skims as commensurable distance. One
clause stating the two numbers can never be netted or compared as distance
would close the gap the way S3 in the first review closed the "giving way"
inversion for puts.

## Notes, not fixes

- Band width is not fixed intraday (today's own d2 level moved 23115.69 →
  23077.42 across four rearm rows) — already self-disclosed under "early in
  the session the bands are narrow," and the σ framing is exactly the right
  answer to that, not a new problem.
- The mixed-series outcome (P2's `next15` measured on the index, anchored to
  a timestamp set by the future's own band) is the same "shown side by side,
  never converted" choice already declared unsolved — consistent, not
  hidden.

## Verdict: **NOT YET**

One must-fix: **M1** — pin down the exact field the band word reads, and add
the missing third case (no zone arm row exists for this touch at all) that
"could not check" does not currently cover. S1–S3 are small, precise, and do
not require moving any inherited number.
