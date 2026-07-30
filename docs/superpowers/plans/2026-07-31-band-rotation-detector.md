# The band-rotation detector

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Spec:** `docs/superpowers/specs/2026-07-31-operator-band-rotation-setup.md` —
the operator's own dictated setup. Read it first; it is the authority, and its
quotes carry meaning the paraphrase loses.

**What now exists to build on (Phase 5, commits `0f1a482`..`db01275`):**
`contract_bars.py` gives premium bars with the leg's own VWAP + ±1/2/3σ
(`vwap,u1,d1,u2,d2,u3,d3`), `contract_pair.py` picks the ATM-anchored
premium-matched pair, and `/api/contract` serves both legs **on one shared
`(day, t)` axis with explicit `null` where a leg has no bar** — so the two legs
can finally be indexed together, which is exactly what this detector needs.

## Global Constraints

- Branch `feature/dashboard-v2`. Backend only — do not touch `ui-v2/` or `ui/`.
- New module `band_rotation.py`: pure stdlib, **no I/O**, **never imported by
  `engine.py`** — same isolation as `structure.py` / `contract_bars.py`.
- Gates: `python -m pytest -q` (**195 now**) · `corepack pnpm --dir ui-v2 exec
  tsc --noEmit` · `corepack pnpm --dir ui-v2 build`. `pnpm` is not on PATH.
- **A GateGuard hook denies the first Write/Edit per file and the first Bash
  call** — state the facts it asks for, then retry the identical call.
- **Causality is absolute.** A signal at bar *i* may read bars ≤ *i* only. No
  next-bar confirmation, no lookahead of any kind. `detect(bars[0..N])`
  truncated at *k* must equal `detect(bars[0..k])`, and there is a test.
- **No absolute market thresholds.** The band levels themselves are the
  operator's thresholds and are relative by construction (σ of that leg's own
  VWAP). Everything else — OI deceleration, band-width compression — must be a
  rank or a sign over the session so far, never a hardcoded quantity.
- **Every signal carries its receipt** — the numbers that fired it, per
  invariant #7. A signal whose inputs were unavailable is `UNKNOWN` with a
  reason, never silently absent and never downgraded to "did not fire".
- **Expiry day is out of scope** (see the spec, and `contract_pair.py`'s
  docstring). Do not special-case it, do not tune anything to fit it.

---

### Task 1: `band_rotation.py` — the detector

**Files:** create `band_rotation.py`, `test_band_rotation.py`. TDD.

**Input:** the two legs' aligned series — for each index *i*: the CE bar and
band values, the PE bar and band values, either possibly `None` (the shared
axis carries nulls). Design the signature around what `/api/contract` actually
returns; read it rather than assuming.

**Output:** one record per bar index, aligned 1:1, `None` when nothing fired:

```
{"i": int, "side": "BUY"|"SELL", "leg": "CE"|"PE",
 "band": "d2"|"d3"|"u3",          # the band actually tagged
 "trigger": str,                   # receipt: the tag and the reversal, with numbers
 "confirm": "CONFIRMED"|"UNCONFIRMED"|"UNKNOWN",
 "confirm_why": str,               # the other leg + the OI read, with numbers
 "trap": "CLEAR"|"SUSPECT"|"UNKNOWN",
 "trap_why": str}
```

**The trigger — tag AND reversal.** The operator: *"tag or wick is enough but
has to reverse from the last band"*.

- BUY: the leg's `low <= d2` (or `<= d3`, stronger — record which) **and** the
  same bar closes back above that band. A tag alone is not a signal.
- SELL: the mirror — `high >= u3` and the same bar closes back below it. Note
  the operator's own asymmetry: they buy at −2σ **or** −3σ but sell only at
  **+3σ**. Do not "fix" that into symmetry.
- Same-bar rejection is the definition **because causality forbids waiting for
  the next bar**. Record this in the docstring as an interpretation of "has to
  reverse" and flag it as worth confirming with the operator — the alternative
  reading (reversal confirmed by the following bar) is not implementable
  without lookahead and would change what fires.

**The confirmation — the other leg rotating.** The opposite leg must be
*coming down from* its +2/+3σ: it tagged its upper band within a recent window
and is now below it. The window is in bars; make it a named constant with its
reasoning, and note that no operator value exists for it (an assumption).

**The OI condition — deceleration, not a peak.** The operator was explicit:
*"oi is lagging so we need to prempt by the change... the rate of change of oi
is declining now"*. So: OI slope over a window, and the **slope of that slope
negative on BOTH legs**. Compute it here from the `oi` series (the engine's
`oi_slope` is a different series — the index books, not these strikes). Sign
and rank only; no absolute lot counts.

**Positioning must NOT veto.** *"suppose book is put heavy but put prices are
touching the last band so we can except a bounce from there"*. If you find
yourself adding a filter that suppresses a signal because the book is heavy on
the side being bought, you have deleted the operator's edge. There is a test.

**The trap filter.** *"smart money always make possition is narrow change once
they load there position than the market start moving"*. Band width **before**
the move is the tell:

- `CLEAR` — the bars preceding the move sat in compressed band width (low rank
  over the session so far), i.e. the move emerged from a coil.
- `SUSPECT` — band width was already wide/expanding when the move happened.
- `UNKNOWN` — too little session history to rank yet. Say so; do not default to
  `CLEAR`, which would read as "we checked and it is fine".

Band width is computed on **the premium series' own bands** (`u1 - d1`
normalised by `vwap`), ranked over the session so far — the operator was
describing the chart they watch, which is the option chart.

**Tests, at minimum:** each trigger side fires exactly where its definition
says and nowhere else · a tag with no reversal does NOT fire · causality by
truncation, comparing full records not lengths · the OI condition requires
deceleration on both legs · a heavy book on the bought side does not suppress
(the positioning test) · trap `CLEAR` vs `SUSPECT` vs `UNKNOWN` · a `None` leg
bar yields `UNKNOWN` confirmation, never a fabricated one · index independence
(the same shaped series scaled to BANKNIFTY/SENSEX premium magnitudes yields
the same signals — proves no absolute threshold crept in).

Gate + commit.

---

### Task 2: surface it on `/api/contract`

**Files:** modify wherever `/api/contract` is assembled (`live.py`'s
`build_contract`, `server.py`'s handler). Additive only.

Attach the detector's per-bar records as a sibling of the legs, aligned to the
same shared axis. Never recompute anything client-side later — this is the
"UI renders, engine decides" boundary.

**Verify against real data**, as Phase 5's tasks did: run it over a real cached
or fetched session and report how many signals fired, of which how many were
`CONFIRMED` and how many `trap: SUSPECT`. A detector that fires on half the
bars is miscalibrated and better found now.

Gate + commit.

---

## Explicitly NOT in this plan

- **Exits.** Band-to-band with ≥1:1 is the operator's buy-side rule, but the
  **seller's stop and decay target are undecided** and must not be invented.
- **The regime selector** (PINNED/COILING favours selling, a moving day favours
  buying). It needs the index-side regime joined to the contract series; own
  task once this one is proven.
- **Expiry-day behaviour** — unspecified by the operator.
- Any UI.
