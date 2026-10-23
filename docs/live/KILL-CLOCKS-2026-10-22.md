# KILL CLOCKS · read 2026-10-22 · gap A21

`§1d 17 of 10 sessions` `VPIN 34 of 30` `direction.py 36 of 30` `nothing retired` `her decision`

**Rules for this page.** Rows are described against each clock's own stated condition. No hit rate, no win rate, no
score. `[M]` = read from a file. `[I]` = a reading I had to make where the text is not literal, named as such. A missing
value is never 0. Nothing was written to `data/`; every outcome below was computed read-only in the scratchpad.

| Clock | Condition found in | Forward log | Sessions [M] | A21 said |
|---|---|---|---|---|
| §1d fade gate | `research-findings.md` §1d | `data/trigger_log.jsonl` `gate` | 17 (23 Sep → 22 Oct) | 15 |
| VPIN | `vpin.py` docstring, memory | `data/vpin_log.jsonl` | 34 (25 Aug → 22 Oct) | 32 |
| `direction.py` | its docstring, HANDOFF-DESK §8.7 | `data/desk_log.jsonl` | 36 (24 Aug → 22 Oct) | 34 |

VPIN's and `direction.py`'s conditions are **not** in `research-findings.md` [M] (searched for "vpin", "direction",
"kill"). My counts include 22 Oct; a session = a day with at least one forward row.

---

## 1. §1d · the fade-gate falsifier

**The condition (§1d, written 2026-09-23 00:40).** Falsified if ANY of:

| Clause | Text, short |
|---|---|
| (a) | the illegal set's MAE is no worse than the legal set's |
| (b) | illegal on fewer than 1 in 10 fade arms over 10 sessions |
| (c) | the result collapses once the single worst leg is removed |

**Readings I had to make** [I]. §1d names MAE but no window, no statistic and no "leg". So:

| Point | Reading |
|---|---|
| MAE | the log's own row measure, `trigger_log._outcome` |
| Window | anchor close → 15:15, bar extremes, stop not obeyed |
| Statistic | median MAE per set |
| Comparison | per index (points differ ~10× across indices) |
| Populations | `zone` (d2/u2) and `5c` (d3/u3) apart |
| "Fade arms" | arm rows only |
| PATA NAHI | its own set, never legal |
| Worst leg | the (day, side) with the most negative summed illegal MAE |

Recomputed MAE matched every stored MAE (0 mismatches) [M].

**Rows: zone arms, 23 Sep → 22 Oct** [M]

| Index | Arms | Legal | Illegal | Pata nahi | MAE legal, median | MAE illegal, median | Scored legal / illegal |
|---|---|---|---|---|---|---|---|
| NIFTY | 203 | 36 | 140 | 27 | −82.1 | −90.3 | 18 / 104 |
| BANKNIFTY | 158 | 27 | 110 | 21 | −253.4 | −171.2 | 22 / 98 |
| SENSEX | 205 | 27 | 152 | 26 | −202.9 | −271.1 | 26 / 117 |
| All zone | 566 | 90 | 402 | 74 | — (not pooled) | — | 66 / 319 |

**The worst illegal leg removed** [M]: it is 21 Oct BUY on all three (the trend-down day).

| Index | MAE legal | MAE illegal | Gap, illegal worse by |
|---|---|---|---|
| NIFTY | −81.4 | −83.5 | 2.1 (was 8.2) |
| BANKNIFTY | −239.0 | −147.4 | −91.6 (illegal less adverse) |
| SENSEX | −202.9 | −253.9 | 51.0 (was 68.2) |

**Clause by clause**

| Clause | NIFTY | BANKNIFTY | SENSEX | Tag |
|---|---|---|---|---|
| (a) illegal no worse | not met (−90.3 vs −82.1) | **met** (−171.2 vs −253.4) | not met (−271.1 vs −202.9) | [M] |
| (b) binds < 1 in 10 | not met (140 of 203 illegal) | not met (110 of 158) | not met (152 of 205) | [M] |
| (c) collapses w/o worst leg | **met** (gap 8.2 → 2.1) | (a) already met | not met (gap 51.0) | [I] |

**The `5c` population, kept apart** [M]: legal arms scored n 1 (NIFTY), 3 (BANKNIFTY), 11 (SENSEX). Under 15 per side,
so INCONCLUSIVE on every index.

| Index | 5c arms | Legal | Illegal | Pata nahi | MAE legal, median | MAE illegal, median |
|---|---|---|---|---|---|---|
| NIFTY | 32 | 1 | 25 | 6 | −218.6 (n 1) | −153.3 (n 18) |
| BANKNIFTY | 29 | 6 | 15 | 8 | −325.6 (n 3) | −217.3 (n 14) |
| SENSEX | 61 | 11 | 46 | 4 | −354.9 (n 11) | −402.4 (n 29) |

**What could not be checked**

| Item | Count | Why | Tag |
|---|---|---|---|
| Zone rows with no MAE | 187 | no cached 1-min session (A19) | [M] |
| Rows 9–22 Oct in the file | 224 | scorer not run since 8 Oct (N9) | [M] |
| Gate blind (pata nahi) days | 7 Oct 33/34 · 9 Oct 25/27 · 16 Oct 15/15 arms | gate read PATA NAHI | [M] |

**The two predictions, described (not the falsifier)** [M]

| Day | Type | Zone arms | Illegal | Legal |
|---|---|---|---|---|
| 21 Oct | trend down | 64 | 55 | 9 |
| 22 Oct | chop | 32 | 24 | 8 |

**22 Oct rows that matter to a trader** [M]

| Row | Gate | MFE to 15:15 | MAE to 15:15 |
|---|---|---|---|
| NIFTY BUY arm 09:33 | ✗ veto "NO FADE" | +231.7 | −10.0 |
| NIFTY BUY entry 09:36 | ✗ veto | +215.0 | −7.6 |
| BANKNIFTY BUY entry 09:42 | ✗ veto | +500.0 | −80.0 |
| NIFTY SELL arm 11:12 (the top) | ✗ "CE 23000 gave up 10:11" | +200.4 | −11.2 |
| NIFTY SELL entry 11:18 (the top) | ✗ "CE 22800 stalled since 09:24" | +165.7 | −25.9 |
| NIFTY SELL arm 09:30 | ✓ | +35.0 | −218.6 |
| SENSEX SELL arm 09:30 | ✓ | +106.8 | −647.5 |

**What a kill would touch** [M]: the face's ring-or-silence rule (`signals.gate_sound`, the "fade gate on the face",
commit 7b83e6f). The forward log keeps every row either way; the gate is a stamp beside them.

**Bar:** met on NIFTY (clause c) and BANKNIFTY (clause a); not met on SENSEX. Met only under my MAE reading, because §1d
never fixed the window.

---

## 2. VPIN · the toxicity gauge (NIFTY-FUT, shadow)

**The condition (`vpin.py` docstring; memory `vpin-shadow-module.md`).** Over 30 sessions, pct ≥ 0.90 must precede a
range expansion at better than base rate, or the module dies.

**What the condition leaves undefined** [M]: searched in `vpin.py`, the memory file and `context/HANDOFF.md`.

| Term | Defined? |
|---|---|
| "range expansion" (size) | no |
| the window after pct ≥ 0.90 | no |
| "base rate" (per bucket, per hour, per session?) | no |

**Rows** [M]

| Item | Value |
|---|---|
| Log | `data/vpin_log.jsonl`, 1,538 buckets, NIFTY-FUT only, all `shadow` |
| Sessions | 34 |
| Covered 10:00 → 15:00 | 25 |
| Late start (after 10:00) | 2 Sep, 3 Sep, 9 Sep, 18 Sep, 7 Oct, 9 Oct |
| Early end (before 15:00) | 9 Oct, 12 Oct, 13 Oct, 16 Oct |
| Buckets stamped after 15:30 | 16 sessions, all before the 23 Sep fix |
| Sessions with ≥ 1 bucket pct ≥ 0.90 | 20 |
| Sessions with none | 14 (22 Oct among them) |
| Not pooled | `vpin_fast.jsonl` 2,805 rows · `vpin_backfill.jsonl` 4 rows |

**Structural note** [I]: `pct` is a percentile of the same session so far, so what counts as "high" moves with each
session's own history. A base rate for "pct ≥ 0.90" has to be defined on that moving scale.

**Bar:** cannot be checked. Choosing "range expansion", the window and the base rate now, after 34 sessions are on
disk, would be fitting (§5). They have to be registered first, then counted forward only (N11).

---

## 3. `direction.py` · the direction view

**The condition (`direction.py` docstring; HANDOFF-DESK §8 item 7).** After ~30 scored sessions, FORCED views must
resolve in the named direction more often than LEANING ones, else rewrite. If neither beats naming no direction, delete.

**Rows** [M]

| Item | Value |
|---|---|
| Log | `data/desk_log.jsonl`, transitions only |
| Fields logged | gear 3,017 · deployable 1,353 · conviction 1,236 · oi_dir 324 |
| Sessions | 36 |
| Conviction → LEANING | 617 |
| Conviction → NONE | 576 |
| Conviction → FORCED | 43, all on 24 Aug |
| FORCED since 25 Aug | 0 in 35 sessions |
| Named direction (BULL / BEAR) logged | nowhere: desk_log, surface, frame, calls, senses |
| "Resolve": horizon or size | not defined |
| A scorer for direction views | none found in `tools/` |

**Bar:** cannot be checked, for three separate reasons [M]:

| Reason | Effect |
|---|---|
| The named direction was never logged | nothing to resolve against |
| "Resolve" has no horizon or size | no outcome definition |
| FORCED fired on 1 of 36 sessions | the comparison has no FORCED side |

---

## 4. For Mary to decide

| Clock | Line |
|---|---|
| §1d | **KILL** — falsifier met on NIFTY (clause c) and BANKNIFTY (clause a), not on SENSEX; under my MAE-window reading, so CANNOT CHECK is also a fair ruling. |
| VPIN | **CANNOT CHECK** — "range expansion", its window and the base rate were never defined; register them, then count forward (N11). |
| direction.py | **CANNOT CHECK** — the named direction was never logged and FORCED has not fired since 24 Aug; log `bias` and restart the clock, or retire it (N10). |
