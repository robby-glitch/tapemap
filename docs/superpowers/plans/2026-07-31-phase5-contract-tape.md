# Phase 5 — the option contract tape (backend)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Why now:** the operator's own setup
(`docs/superpowers/specs/2026-07-31-operator-band-rotation-setup.md`) reads σ
bands **on option premium**, a series this tool does not compute. Nothing in
that setup can be detected until it exists. This plan builds the series and the
route only — the detector and the chart come after.

**Design source:** `docs/superpowers/specs/2026-07-29-contract-tape-design.md`
sections 1–2 (the `/api/contract` shape and where the data comes from). Read it.

## Facts verified against the live API, 2026-07-30 night — build on these

- **`toDate` is EXCLUSIVE.** `dhan_fetch.rest_intraday` passes
  `fromDate=day, toDate=day`, which returns **zero bars**. With
  `toDate = day + 1` the same call returns **375 real 1-min bars** carrying
  `open/high/low/close/volume/timestamp/open_interest`. Verified on NIFTY
  security id `65852` for 2026-07-30 (first closes 61.5 / 55.15 / 64.8, OI
  1796860 → 1770145 → 1734525). A two-day range returned 750 bars, so the
  endpoint pages days back-to-back as expected.
- Both existing callers (`dhan_fetch.py:176` FUT, `:187` options) hit this, so
  `fetch_chain_day` currently always fails at "empty FUT response". It fails
  loudly rather than writing bad data — no cached file is suspect.
- `chain_live.resolve_expiry(dhan, today, under_id, under_seg)` works and
  returned `2026-08-04` (next weekly).
- `live._atm_ids(strike, cfg)` resolves CE/PE ids for **any** strike given a
  `cfg` that includes `expiry` — verified `{'CE': '65852', 'PE': '65853'}` for
  strike 24350. `cfg` comes from `instruments.INSTRUMENTS[idx]` **plus** an
  `expiry` key the caller must add; it is not there by default.
- `chain_live._client(tok)` builds the SDK client (`dhanhq(DhanContext(cid,
  tok))`); the client id comes from `DHAN_CLIENT_ID` or `.dhan_client`.
- Token validity is checkable via `chain_live.token_status(tok)`.

## Global Constraints

- Branch `feature/dashboard-v2`. This plan is **backend only** — do not touch
  `ui-v2/` or `ui/`. Run the frontend gates anyway to prove they are untouched.
- Gates each commit: `python -m pytest -q` (**102 passing now**) ·
  `corepack pnpm --dir ui-v2 exec tsc --noEmit` · `corepack pnpm --dir ui-v2
  build`. `pnpm` is not on PATH — always `corepack pnpm`.
- **A GateGuard hook denies the first Write/Edit per file and the first Bash
  call.** State the facts it asks for in plain text, then retry the identical
  call. It is not a permission failure.
- **Honesty rules bind.** Never invent a bar. A session Dhan does not serve is a
  **gap**, listed and rendered as a gap, never interpolated. A missing forming
  candle is `null`, never the last completed candle held open. Every computed
  number must be sourceable to a fetched field.
- **Causality:** VWAP and σ at bar *i* use bars ≤ *i* only. Replay is truncation.
- **UI renders, engine decides** — every band value is computed here, server
  side. The browser will only reshape.
- Rate limit: the data APIs are capped at 5 req/s; the existing code sleeps
  0.22–0.25s between calls. Keep that.
- Network calls need a wall-clock deadline (the 2026-07-27 frozen-tape
  precedent). Reuse the established pattern rather than a bare `timeout=`.

---

### Task 1: fix `rest_intraday`'s date range, with a regression test

**Files:** modify `dhan_fetch.py`; create/extend a test.

The bug and its proof are in the facts block above. `toDate` must be the day
**after** `day` (calendar +1 is sufficient; the endpoint returns only trading
days). Keep the public signature `rest_intraday(token, sec_id, instrument, day,
oi=False)` — callers pass a single session and should keep doing so.

Add a docstring line recording that `toDate` is exclusive, because the next
person will otherwise "simplify" it straight back to `toDate=day`.

**Test without network:** the function builds a request body; assert the body's
`fromDate`/`toDate` for a given `day` (e.g. `2026-07-30` → `toDate`
`2026-07-31`), and that a month/year boundary rolls correctly
(`2026-07-31` → `2026-08-01`, `2026-12-31` → `2027-01-01`). Do NOT write a test
that calls the API.

Gate + commit.

---

### Task 2: `contract_bars.py` — premium bars and their own VWAP/σ

**Files:** create `contract_bars.py`, `test_contract_bars.py`.

Pure computation, stdlib only, no I/O — the same isolation as
`chain_metrics.py` and `structure.py`, and **never imported by `engine.py`**.
Fetching belongs to the caller; this module receives already-fetched series.

1. **`to_bars(payload) -> list[dict]`** — reshape one `rest_intraday` response
   (parallel arrays `open/high/low/close/volume/timestamp/open_interest`) into
   `[{"t": "HH:MM", "o","h","l","c","v","oi"}]`, IST, sorted by time. Arrays of
   unequal length are a defect in the feed: truncate to the shortest and record
   how many rows were dropped, never zip-pad. A non-finite value makes that bar
   `None`, not 0.

2. **`vwap_bands(bars) -> list[dict]`** — session VWAP anchored at the first bar
   plus ±1/2/3σ, appended per bar as `vwap,u1,d1,u2,d2,u3,d3`.
   **Reuse `live.py`'s existing VWAP/σ routine rather than writing a second
   one** — find it first. The spec's reason is explicit: two derivations drift
   and then v1 and v2 disagree about the same band. If it cannot be reused
   as-is, extract it so both call one implementation, and say so in the commit.
   Cumulative, causal: bar *i* uses bars 0..*i*.

3. **`resample(bars, minutes)`** — 2/3/5/15-minute aggregation from the 1-minute
   series. **VWAP is computed on the 1-minute series and then sampled, never
   recomputed on aggregated bars** (spec §2), so changing interval must never
   move a band. There is a test for exactly this.

**Tests (TDD, write first):** reshape incl. ragged arrays and non-finite values ·
VWAP/σ against a hand-computed 5-bar fixture · causality (bands over
`bars[0..N]` truncated at k equal bands over `bars[0..k]`) · **interval
invariance** (3-minute bands equal the 1-minute bands sampled at 3 minutes) ·
empty input returns empty, never throws.

Gate + commit.

---

### Task 3: `contract_pair.py` — the 09:20 premium-matched leg picker

**Files:** create `contract_pair.py`, `test_contract_pair.py`.

From the operator spec: pick **a CE at one strike and a PE at another** whose
premiums are nearly equal shortly after the open — tolerance **±30 (NIFTY)**,
**±50 (BANKNIFTY, SENSEX)** — and follow that pair all day. It is a
premium-parity pair, **not** one strike where CE ≈ PE, and the two legs are
generally neither delta-neutral nor equidistant from spot.

`pick_pair(chain_rows, idx, tol=None) -> {"ce": {...}, "pe": {...}, "why": str}`
where `chain_rows` is a chain snapshot's per-strike rows (each carrying
`strike`, `ce.ltp`, `pe.ltp`).

- Return the pair minimising `abs(ce_ltp - pe_ltp)` subject to that difference
  being within tolerance.
- **Tie/multiple-candidate rule is UNCONFIRMED with the operator.** Implement
  nearest-to-ATM as the tie-break, name it in `why`, and mark it clearly in the
  docstring as an assumption to confirm — do not bury it.
- No pair inside tolerance → return `None` with a reason. Never widen the
  tolerance silently to force a pair.
- `why` names the actual numbers, per invariant #7.

**Tests:** exact-match pair · nearest-within-tolerance · nothing within
tolerance → `None` + reason · per-index tolerance (30 vs 50) · a tie resolved
by the documented rule · rows with a missing `ltp` skipped, not treated as 0.

Gate + commit.

---

### Task 4: `GET /api/contract` — the route

**Files:** modify `server.py`; add fetching glue where the existing fetch
helpers live (`dhan_fetch.py` / a small function in `live.py` — follow whatever
the surrounding code already does; do not invent a new module for one function).

| Param | Meaning | Default |
|---|---|---|
| `idx` | NIFTY · BANKNIFTY · SENSEX | NIFTY |
| `strike` | any strike | the picked pair's |
| `side` | CE · PE | both |
| `interval` | 1 · 2 · 3 · 5 · 15 | 3 |
| `days` | sessions back | 1 |

Response follows spec §2's shape: `bars`, `vwap` (aligned 1:1), `oi`, `pair`
(the Task 3 result), `gaps[]`, `forming`, `live_error`.

- **`forming` is `null` for now** and the field must say why (the poller feeds
  it, and that is a later task). Do not fake it from the last completed bar.
- **`gaps[]`**: a requested session Dhan serves no bars for is listed here.
  `mental-map.md` records that the expired-option feed is rolling-ATM, so a
  strike far from spot on an earlier day may genuinely have no history. Measure
  it; do not assume.
- One index's failure must not take down another — per-index try/except with
  `log.exception`, matching `server.py`'s existing `/api/data` handling.
- Multi-day is a loop, one call per session, respecting the 5 req/s cap.

**Verification (do this, it is the point of the task):** the token is valid and
the market is closed, so fetch **2026-07-30** for NIFTY and check the route's
own numbers against the raw API response — bar count 375, first closes 61.5 /
55.15 / 64.8, OI starting 1796860. Report the actual numbers you get.

Gate + commit.

---

### Task 5: docs + ledger (controller)

Update `context/ui-v2-dashboard.md` (a Phase 5 section, and move the relevant
Open items), the operator spec's build-order list, and
`.superpowers/sdd/progress.md`. Record the `toDate` finding prominently — it is
the kind of thing that gets reintroduced.

---

## Explicitly NOT in this plan

- The band-rotation detector (buy −2/−3σ reversing, sell +3σ reversing) — needs
  this series first.
- The live **forming candle** from the `ChainPoller` tick stream — cannot be
  verified until the market opens; own task, own session.
- Any frontend. The option chart, the pair selector UI, the detector's
  rendering: all later.
- `contract_tape.py`'s four states (ABSORPTION/IGNITION/EXHAUSTION/BUILD) from
  spec §1 — a separate analytic, and the operator's own setup outranks it.
