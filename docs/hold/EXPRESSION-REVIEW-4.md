# Fourth review: `EXPRESSION-PREREG-DRAFT.md` rev e (verification of the third review's items)

Written 2026-09-26 20:00 IST (read from the clock; begun 19:57). This is the only repo file written. No server was touched,
nothing was POSTed, `data/` was not opened, and nothing was committed. Scratch: `scratchpad/review3/`, Python with `-B`.

**What I read and checked:**
- **The draft:** sha256 `f92ed0902f44d733b231205249df7535fd325f50ffdfe9fa297fce840eea61fd` [M], hashed at 19:57 and again at
  19:59, unchanged. It matches the hash I was given.
- **Rev e's fingerprint:** `rules_reve_before_run.md` `fb583979…0cc9` [M]. The timestamps are in order [M]: fingerprint
  19:54:14, `expr_e.py` 19:54:38, `run_e.py` 19:55:21, `reve/writer.json` 19:56:21, the draft 19:57:22.
- **What I ran:**
  - `diff` of the fingerprint against the draft, and of rev d's fingerprint against rev e's;
  - `expr_e.py`'s self-check (it prints "ok");
  - an independent reproduction of `reve/writer.json` from my own rev d run (`percl_d.json`), made in a separate process
    for the third review;
  - `git status` before and after.
- **What I did not run:** no word was crossed with an outcome, and no candidate rule was run.

## 1. B-N1 is closed, as specified

- **The text.** §B.2 (GO: "… and the wall behind the sale exists") and the paragraph after it register the rule: with no
  wall (§A's R6) the word is **WAIT**, "not there yet: no wall behind the sale (R6)". It is WAIT, not NO, because NO stays
  the entry FOLD. §E.1's writer-GO row, §F.1's card ("its writer word is then WAIT") and the tests in §H agree.
- **The code implements exactly that.** `expr_e.gate` turns GO into WAIT only when OI is read (`not blind`) and
  `wall_behind` is `None`. That is §A's R6 test (`expr_a` lines 59–64): the same function, spot and step.
  - **OI blind** is already WAIT under rev d's could-not-check clause, so the gate rightly skips it. Its reason stays
    "could not check your wall", not R6. That matches §A, where blind is R3, not R6.
  - NO and WAIT pass through unchanged.
- **It binds as it should** [M]:
  - 131 closes and 12 units move from GO to WAIT, all on 09-22 and 09-23;
  - **no GO stands beside any §A sell refusal now** (0 of 2,250).

## 2. Were the text edits applied faithfully?

**Yes, all of them:** A-T12 to A-T17, B-T1 to B-T3 and C-T1 to C-T6, each where §G says. **None changes a judged rule, a
number or a population.** Two notes:
- **B-T1 took the code's side.** X > P is now "scored, only the stop can resolve", and the line inside one candle is "not
  scored". Both groups are outside the stratum, so P1-W and P2-W read neither. This matches the code rev a–e ran.
- **C-T3 registers a reading of signed text:** "toward / away from her strike" in rev 4 §4 and W1 reads by her direction,
  the `dpx` sign. It follows rev 4 §4's own parenthetical and the live code (`hold.py` line 470), and W1 has no code yet.
  Her sign on C adopts it; say so if she asks.

**Outside §D and §G's post-run lines (1521–1525), the draft is byte-identical to rev e's fingerprint** [M]. The header is
included.

## 3. Anything new or stale in rev e? Four text items, none a rule

- **H-1, line 1:** the title still says "REVISION d". Make it "REVISION e".
- **H-2, the header's "Decisions taken as the trader" (lines 36–48):** add rev e's line: "after rev d's rows and the third
  review: a writer's GO also needs the wall behind the sale (B-N1)". §G calls it decided as the trader, and the list omits
  it.
- **D-1, §D.0 "The repo" (lines 645–646):** it still reports only rev d's `git status`. Add rev e's: only its scratch
  (`expr_e.py`, `run_e.py`, `reve/`, `reve_run_out.txt`, `rules_reve_before_run.md`), this draft, and the review files
  [M: my `git status`].
- **C-1, §C.3 (line 588) and §H (line 1541):** the owed copy amendment names only the squeeze sentence. Rev 5 §D item 7″'s
  other sentence, "winners cashing in — your strike is farther from spot than at entry", reads the wrong way round for a
  sale in the money too. Name both.

**Checked, and none found:**
- a withdrawn object left live;
- a rule that fails open;
- a contradiction between §A and §B on one card;
- an unsaid change to a signed rule.

## 4. The rev e numbers in §D reproduce

| claim (§D) | `reve/writer.json` | my own rev d run, gated |
|---|---|---|
| closes: GO 633 · WAIT 1,262 · NO 355; 131 moved; 0 GO beside a sell refusal | yes [M] | yes [M] |
| units: GO 60 · WAIT 121 · NO 35 (rev d 72 · 109 · 35) | yes [M] | yes [M] |
| moved units: SENSEX 09-22 1, BANKNIFTY 09-22 2, NIFTY 09-23 2, SENSEX 09-23 3, BANKNIFTY 09-23 4 | yes [M] | yes [M] |
| stratum 60 / 89 / 21 = 170; beyond 59 / 86 / 19 = 164; 196 beyond; 78 resolved, all in the stratum; 127; 38 not scored | yes [M] | — |
| her entries: GO 7 · WAIT 19 · NO 2, none moved (no entry has "no wall"); rev d's word re-derived and matching its file | yes [M] | — |

## 5. Verdicts

| part | verdict | edits (none changes a rule, a number or a population) |
|---|---|---|
| **A** the expression | **SIGNABLE WITH TEXT EDITS** | H-1, H-2 (the shared header) |
| **B** the writer in VALIDATE | **SIGNABLE WITH TEXT EDITS** | H-1, H-2; D-1 (disclosure) |
| **C** the writer in the window | **SIGNABLE WITH TEXT EDITS** | H-1, H-2; C-1 |

**No blocker remains.** Still hers to confirm, none blocking, as in §H:
- whether the window's line is her level when she sells;
- whether rev 5 B's one-candle buffer stays;
- her "90-minute write guard".

**`git status --short docs/`:**
- **Before:** the draft modified; untracked `EXPRESSION-REVIEW-2.md`, `EXPRESSION-REVIEW-3.md`, rev d's scratch and rev e's
  scratch (`expr_e.py`, `run_e.py`, `reve/`, `reve_run_out.txt`, `rules_reve_before_run.md`).
- **After:** the same, plus only `docs/hold/EXPRESSION-REVIEW-4.md` [M].
