# RIDE build: adversarial review (2026-10-21)

**Reviewer:** an independent agent. It edited no file except this one.
**Spec:** `docs/setup-review/RIDE-PREREG.md`, sha256 `dcb306a11ad662291a25094e7db3288aeacc3367be403d2364900302843aff7e`, verified unchanged.
**Code reviewed:** `ride.py`, `test_ride.py`, `tools/ride_score.py`, the RIDE parts of `confluence_log.py`, `frame_v2.bars3`, and the `server.py` hook (lines 5794–5797).

## Overall verdict: SHIP AFTER FIXES

- **No BLOCKER.**
  - No look-ahead was found. Two independent replays on real days confirm it (§A).
  - No R or premium can be computed before the §6 gate.
  - The live hook cannot raise.
  - No existing row, gate, beep or frame key changes.
- **One MAJOR:** the pullback-depth stamp is wrong on most real rows. It does not touch any entry, gate or R, but the
  forward log is write-once, so fix it before the first forward row.
- **Before any `--run`,** add a READINGS list (MINOR 2) and settle the band reading (MINOR 3). A re-run may not
  change a definition, so these must be fixed first.

## What was run (read-only)

**Tests and the dry scorer**
- `python -m pytest -q test_ride.py test_confluence.py test_frame_v2.py`: **61 passed**, exit 0.
- The full suite: see the end of this file.
- `python tools/ride_score.py` (dry): it ran in 1 m 43 s, printed counts only (no R, premium or rate), and wrote no
  file. `data/confluence_log.jsonl` and `data/confluence/` still do not exist.
  - Counts: 51 index-days, §E 73, OI ✓ 30, FLOW ✓ 48, OI+FLOW 18, RIDE 18 (7 / 5 / 2 / 4).
  - The gate is SHUT.

**Replay 1, entries against the face.** On each 3-min close, the reviewer rebuilt the face's own
`frame_v2.compose(...)["plan"]` with X, the READ timeline and the card all cut at that close. It compared this to
`ride.entries` on the full-day inputs.
- **Identical on 15 index-days:** 23 Sep, 24 Sep, 1 Oct, 8 Oct and 12 Oct, all three indices.
- This includes 24 Sep NIFTY, the day where the builder says the day-end band would differ.
- In the same script, `bars3`'s default output was JSON-byte-identical to a literal copy of the pre-change function.

**Replay 2, the write-time cut.** For 43 §E entries over six days, the reviewer ran `ride.evaluate` twice:
- on the full-day chain grid and book;
- on the records as they stood when the live row is written: book frames that had **arrived** by the window's last
  close + GRACE, and chain snapshots stamped by then.

All 43 are identical. That covers OI, FLOW, GC and the entry.

**Timing on 19 Oct**
- **Light check:** 0.04–0.10 s with a warm Day; v2feed's lock is held for ≤ 0.10 s.
- **Heavy, when a row is due:** 0.85–1.0 s in all; v2feed's lock is held for only 0.15 s of it. The rest is FADE's
  `inputs()` under `confluence_log._lock`.
- **Cold Day:** 3.4 s, once. The face pays this anyway.

**JSON check:** 25 real rows (8 Oct, 24 Sep and 12 Oct) were built exactly as `log_ride` builds them, and all
serialize. These are the rows used in MAJOR 1.

## Findings

### MAJOR

**1. The pullback-depth stamp is not this pullback's depth** (`ride.py:253-260`)
- **What it does now:**
  - the leg's start is the open of the first bar at or after the READ's `since`;
  - `pull` is the highest high (▼) of all leg bars after the leg extreme, up to the §E bar.
- **First failure, the leg start.** The READ usually names a trend at 09:45, half an hour into the move. So "the
  leg" is a sliver and the ratio blows up.
- **Second failure, the pull point.** `pull` is not this pullback's high. A later pullback with no new extreme
  repeats the deepest bounce since the extreme.
- **On real rows:**
  - 8 Oct BANKNIFTY 09:48: 327%. The leg is one bar, so the result is (h − l) / (o − l).
  - 8 Oct NIFTY 09:57: 199%.
  - 24 Sep BANKNIFTY 10:30 and 13:36, three hours apart: **both 801.0%**.
  - 12 Oct BANKNIFTY 10:12: 631%.
  - 18 of the 25 rows built read above 100%, and 2 are None. A pullback deeper than its leg is not a pullback.
- **Declared vs undeclared.** Deviation 7 declared only "excluding the extreme bar". The switch from the §E bar's high
  (the plan's version) to "the maximum high since the extreme" is undeclared.
- **Smallest fix:**
  - ▼: `ext` = the lowest low of the leg bars before bar i.
  - `start` = the highest high of the leg bars up to that extreme.
  - `pull` = **bar i's own high**, the poke that made the §E trigger.
  - ▲ is the mirror.
  - Also stamp the three raw prices `{start, ext, pull}`, so any later definition can be applied without touching
    the write-once rows.
- **Impact:** a stamp only. It never gates and is not in §4.

### MINOR

**1. Retry on failure has no backoff** (`confluence_log.py:342-345`)
- `_ride_slot` is set only on success, so a deterministic failure in the heavy stage re-runs on **every** 15-s
  refresh cycle for the rest of the session.
- Each re-run is about 1 s, holding `confluence_log._lock`, which FADE's `log_new` takes on every cycle of all three
  index threads. It also holds v2feed's lock for 0.15 s.
- **Failure surface:** FADE's `inputs()` brings in things RIDE never reads. These are `prior()` (a `json.load` of a
  `data/backtest` file), the decoder/ofd marks and READ_DIR.
- **Evidence it is rare:** all 73 rows of the dry scan built without error.
- FADE's `log_new` has the same retry pattern.
- **Fix:** set `_ride_slot[index] = slot` in the `except` too (a failure retries next bar), or allow one retry.

**2. No READINGS list in `tools/ride_score.py`**
- §6 is "the same as §1i Amendment 1". That amendment adopted FADE's builder readings *as printed in
  `confluence_score.py`'s header* and stored in its JSON.
- RIDE's readings are recorded nowhere the one-shot carries. They are:
  - deviations 1–9;
  - the control skipping §E entries that close after 15:00 (`ride_score.py:118`, the same as FADE reading 8);
  - the FLIP-basis reading (MINOR 3);
  - 'OI at the bar's last minute'.
- **Fix:** add a `READINGS` list, print it in the dry header and put it in `result()`.

**3. The trail reads FLIP fut as `flip + row basis` even when the frame's basis band is not ok** (`ride.py:129-132`, `:155`)
- On recorded days, **896 of 3,313** closes with a TREND/LEAN FLIP (27%) have the band not ok. Most are early days
  with "expiry unknown, fixed band 20..120".
- On those closes, the extension frame (`read_part._fut`) shows no FLIP fut. `read.card`, the Read tab, does show
  `flip + basis`.
- So the builder's choice matches one face and not the other. It changes R, so it is a definition and must be
  settled before `--run`.
- **Recommendation as a trader:** keep the builder's choice. The Read tab is her landing page, and the row basis is
  the READ's own number. **Declare it** in READINGS.

**4. The "§1d gate, where logged" stamp is missing** (`ride.py:263-265`)
- The spec lists it among the §1 stamps. RIDE rows have no `gate` field.
- A §E entry has no trigger_log zone row, so the honest value is null with a reason.
- **Fix:** add `"gate": None, "gate_why": "no logged §1d gate for a §E entry"`, or look up a zone row on the same
  bar.

**5. The dry table counts late triggers as "could not check"** (`ride_score.py:134-137`, `:147-150`)
- `_any()` returns None when no window bar closes by 15:00.
- So OI cnc and FLOW cnc (1 / 1 / 1 / 0) are exactly the trig>15:00 column, and there are zero real
  could-not-checks.
- **Fix:** count late triggers separately, e.g. skip `e["late"]` rows in the ok / cnc columns.

**6. `flip_dist` mixes two moments** (`ride.py:261-265`)
- The FLIP is read at the §E bar. E is the RIDE entry, up to 9 minutes later, when a newer READ mark may exist.
- **Fix:** read the FLIP at the RIDE entry bar when there is one.

**7. Test gaps.** None of the tests is tautological, but these behaviours are untested:
- the "line never moved past price" rule (7b);
- any ▲ `outcome` / `trade` mirror;
- `_basis_at` equal to `compose`'s basis. This is the core of deviation 1; only replay 1 above shows it.
- the same-slot throttle skip.

Two smaller test issues:
- `test_no_look_ahead...` uses six identical bars, so a peek at `b3[j+1]` would go unseen.
- `test_run_is_refused_by_main...` calls `main()`, which does `os.chdir(HERE)`. This leaks cwd, though it is a
  no-op from `tapemap/`.

**8. Mock isolation holds for writes, not for reads**
- Under `--mock-chain`, rows go to `data/mock/confluence_log.jsonl`, because the hook reads `confluence_log.PATH` at
  call time.
- But `v2feed.DATA` is not redirected, so §E and the READ come from the real `data/`, while OI and FLOW come from
  `data/mock/`.
- Harmless, since the writes are isolated. The face behaves the same way. Just know that mock RIDE rows are not a
  coherent replay.

**9. No index guard between the light and heavy loads** (`confluence_log.py:328-336`)
- `ent["i"]` from the light `b3` indexes the heavy `b3`, which is rebuilt about 1 s later.
- They are equal in practice: the newest bar closed at least 60 s earlier, and holes do not fill in.
- **Fix:** assert `full["b3"][e["i"]]["e"] == _sec(e["t"])` and skip the row otherwise.

### Not RIDE's defect, but Mary should know

- **§E refuses for the whole day** when more than one 3-min slot since 09:15 has no futures tick (`frame_v2._holes`,
  MAX_MISS = 1).
- A server started after about 09:21 therefore logs **zero** RIDE rows that day.
- A mid-session restart gap of more than about 3–6 min stops new §E entries for the rest of the day. Rows written
  before the gap stay.
- The face behaves identically, so "§E unchanged" holds.
- **Start the server before 09:18.**

## The declared deviations

| # | Deviation | Verdict | Why |
|---|---|---|---|
| 1 | Causal basis band per close, fed to §E | **ACCEPT** | It is exactly what the face's `compose` showed at each close: replay 1, 15/15 index-days. One fixed band would show entries the face never showed. |
| 2 | Light/heavy two-stage load | **ACCEPT** | The light check holds v2feed's lock for ≤ 0.1 s per 3 min per index. See MINOR 9 for the index guard. |
| 3 | Throttle once per bar after grace; retry on failure | **ACCEPT, with MINOR 1's fix** | The slot is aligned to bar close + 1 min, and a row is due exactly then. Retry needs a backoff. |
| 4 | Hook passes `path=confluence_log.PATH` | **ACCEPT** | Read at call time, as `log_new` does, so mock isolation holds. |
| 5 | `_server()` instead of `import server` | **ACCEPT** | The live process gets `__main__`, so there is no second module body. Tools import once. |
| 6 | 15:20 mark named `"15:20"` | **ACCEPT** | The same price as FADE's convention (the 15:19 bar's close, i.e. 15:20:00). Naming only. |
| 7a | FLIP only from rows reading the ride's own direction | **ACCEPT** | An opposite READ's FLIP sits beyond price anyway. Harmless belt-and-braces. |
| 7b | The line never moved past price | **ACCEPT** | Moving through price would be a close-triggered exit or an impossible fill. "Only toward price" supports it. Untested (MINOR 7). |
| 7c | A 1-min hole read at the next bar's open | **ACCEPT** | Tested. Gave-up is never skipped. |
| 7d | Pullback depth excluding the extreme bar | **REJECT as built** | The exclusion itself is fine. The undeclared change to "the maximum high since the extreme", plus the leg start at `since`, gives 104–801% (MAJOR 1). |
| 8 | DTE to the options expiry; `flip_dist` fallback; peers | **ACCEPT** | She trades the weekly options, and the frame's basis keeps the futures expiry. The fallback to the §E close is sensible. Peers are causal (`_upto` at the §E bar). |
| 9 | Expressions at END times | **ACCEPT** | The chain minute before the END is FADE's §5 convention. |

## Checklist: what holds

**Look-ahead**
- `entries`: per-close `plan` with rows, basis and bars as of that close. Replay 1.
- `evaluate`: OI at close − 1, FLOW on [close − 20, close), GC whole-bar. Replay 2.
- `closes_after` and the stamps: `_upto` at each close and `b3[:i+1]`.
- `_basis_at`: spot, row basis and `parity_basis` all use data at or before e.
- `ride_inputs`: X is cut at now, and the arrays are copied out under v2feed's lock.

**Matches the spec**
- OI ✓: the trend front is BUILDING and the defender is not BUILDING (fronts has only three states).
- FLOW ✓:
  - ▼: t5 ≤ −0.10, t15 ≤ +0.10;
  - ▲: t5 ≥ +0.10, t15 ≥ −0.10;
  - GC, NIFTY only: ≥ +0.10 (▼) / ≤ −0.10 (▲) is a disagreement; absent GC is not.
- VWAP side: the close on the trend side of the bar's live session VWAP.
- Cutoff: the entry bar closes at or before 15:00. The hold uses 1-min bars < 15:20, and the last gave-up close is
  15:18.
- Line: max(max(trigger high, VWAP at entry) + 0.25σ, E + 0.5σ), with σ frozen at the entry bar. ▲ is mirrored.
- Trail: only toward price.
- Gave-up: UNWINDING only, at a 3-min close, after the intrabar line check in the same minute. STALLED is stamped.
- R uses `line0` throughout.
- Control: `trade(d, b3[i], b3[i])` from c0 with the same `outcome`.

**The gate**
- `_outcomes` is reachable only through `collect(run=True)`, after `can_run`.
- `--rerun` is gated too. `--run` refuses once `ride_first_look.json` exists. Every mode checks the sha.
- Forward rows are counted only on index-days the scan does not hold, so there is no double count.
- Dry output: counts only.

**Live safety**
- `log_ride` catches everything, and the hook wraps it again.
- Lock order is always `confluence_log._lock` → `v2feed._LOCK`, so there is no deadlock.
- Write-once is keyed `("RIDE", day, index, t)` and re-read at a restart.
- The day comes from the clock. After midnight the new day is empty, and late rows are written at 15:31 on the same
  day.

**Unchanged behaviour**
- FADE rows only gain `"setup": "FADE"`. FADE keys are unchanged, and no other code reads the file.
- `bars3`'s default output is byte-identical.
- `frame_v2.plan` is untouched.

## Full suite

- **The reviewer's run:** `python -m pytest -q -x -p no:cacheprovider` gave **1728 passed, 1 skipped**, exit 0, in
  7 m 53 s. This matches the builder's count.
- Afterwards, `data/confluence_log.jsonl` and `data/confluence/` still do not exist.
