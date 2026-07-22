# Multi-Index TapeMap — Design Spec

**Date:** 2026-07-23
**Status:** ✅ IMPLEMENTED (2026-07-23). Backend + UI switcher built and verified live off-hours (chain analyser per index; futures-bar TAPE/validator/scan paths await a market-hours session — see "Verification state" below). Plan: `docs/superpowers/plans/2026-07-23-multi-index-tapemap.md`.
**Goal:** Extend TapeMap from NIFTY-only to three indices — **NIFTY, BANKNIFTY (NSE), SENSEX (BSE)** — switchable from a header control, all served by one backend.

## Context / why

The tape-reading method is index-agnostic: the engine (`engine.py`), chain analytics (`chain_metrics.py`), option math (`gamma.py`), and the entire UI logic (validator, scanner, MAP, chain analyser in `ui/app.js`) operate on FUT+CE+PE bars and an option-chain snapshot — none of it cares which index produced the data. Only the **data-feed layer** is hardwired to NIFTY:

- `live.py`: `FUT_ID="61093"`, `EXPIRY`, `PREV_DAY`, `STEP=100`, futures segment `NSE_FNO`.
- `chain_live.py`: `UNDER_ID=13, UNDER_SEG="IDX_I"`, `WINDOW_PTS=1500`.
- `server.py`: starts one chain poller + one live payload; serves single `/api/data` and `/api/chain`.
- `ui/`: no index concept.

So the work is: parameterize the feed by instrument, serve per-index payloads from one backend, and add a UI index switcher. **No engine / metrics / validator / scan changes.**

## Decisions (from brainstorming)

- **Serving:** one backend, tab switcher. Server polls all enabled indices and serves keyed payloads; UI flips instantly.
- **SENSEX:** included — Dhan plan has BSE F&O access.
- **ID/expiry resolution:** auto-resolve volatile identifiers (futures security-id, current expiry, prior trading day) at startup from Dhan's scrip master + `expiry_list`; only the daily `.dhan_token` stays manual.
- **UI:** header segmented pill `NIFTY | BANKNIFTY | SENSEX`, separate from the TAPE/DATA view tabs.

## Architecture

### 1. Instrument registry — new `instruments.py`

Single source of truth. Static config per index; volatile fields resolved at startup.

```python
INSTRUMENTS = {
  "NIFTY":     {"under_id": 13, "under_seg": "IDX_I", "chain_seg": "NSE_FNO",
                "fut_seg": "NSE_FNO", "step": 100, "window": 1500, "under_sym": "NIFTY"},
  "BANKNIFTY": {"under_id": 25, "under_seg": "IDX_I", "chain_seg": "NSE_FNO",
                "fut_seg": "NSE_FNO", "step": 100, "window": 2000, "under_sym": "BANKNIFTY"},
  "SENSEX":    {"under_id": 51, "under_seg": "IDX_I", "chain_seg": "BSE_FNO",
                "fut_seg": "BSE_FNO", "step": 100, "window": 2500, "under_sym": "SENSEX"},
}
DEFAULT = "NIFTY"
ENABLED = ["NIFTY", "BANKNIFTY", "SENSEX"]
```

- `resolve_dynamic(cfg, dhan/tok)` → fills `fut_id`, `expiry`, `prev_day` from the scrip-master CSV + `expiry_list`. Cached per process; re-resolvable.
- All identifiers here are **verified against live Dhan during implementation** (see Unknowns).

### 2. Feed parameterization

- **`live.py`**: `build_payload(cfg)` — takes an instrument config dict instead of module globals. `_pick_strike` keyed by index (per-index sticky-ATM state, e.g. `_stick[idx]`). Futures intraday uses `cfg["fut_seg"]` and resolved `fut_id`. Returns the same JSON shape as today plus an `"index"` field.
- **`chain_live.py`**: `ChainPoller(configs)` accepts a **list** of instrument configs. Holds one `ChainState` per index and one `box` per index (`self.boxes[idx]`). `option_chain` / `expiry_list` calls use each cfg's `under_id` / `under_seg` / `chain_seg`. `normalize()` window filter uses `cfg["window"]`. Warm-start replay keyed per index (`data/chain/chain_<IDX>_<date>.jsonl`).

### 3. Multi-index serving — `server.py`

- `live` mode builds `payloads = {idx: {"payload": ...}}` and starts a `ChainPoller(ENABLED configs)` exposing `chains = {idx: box}`.
- **Handler routing:** parse `idx` query param (default `NIFTY`); `/api/data?idx=…` → `payloads[idx]`, `/api/chain?idx=…` → `chains[idx]`. Unknown idx → fall back to default.
- **Rate limit (Dhan ~1 option-chain / 3s):** a single chain-poller thread **round-robins** the enabled indices — one `option_chain` request per iteration, sleeping ~3.5s between requests → each index refreshes ~every `3.5s × N` (~10s for 3). Live futures payloads refresh in one sequential loop over indices every `REFRESH_S`.

### 4. UI switcher — `ui/index.html` + `ui/app.js`

- **Markup:** a segmented pill in `<header>` (near the brand): `NIFTY | BANKNIFTY | SENSEX`. Active index highlighted.
- **State:** `S.index` (default `NIFTY`). Every data/chain fetch appends `?idx=${S.index}` — the `/api/data` poller, the chain poll in `renderMap`, `refreshValModal`, `fetchChain`, and `scanRefresh`.
- **Switch handler:** on pill click → set `S.index`, clear per-index-dependent state (`S.day`, `S.mapChain`, `S.valStrike/valSide`, scan/chain timers), refetch `/api/data?idx=…`, re-render. Title/labels reflect the index.
- Strike dropdowns (±6 around ATM), validator, scanner, chain analyser, MAP all already derive from the payload's `strikes`/`atm`/`metrics` — they work per-index with no further change.

### 5. Untouched (reused verbatim)

`engine.py`, `chain_metrics.py`, `gamma.py`, and all validator / scan / MAP / chain-analyser logic in `ui/app.js`.

## Data flow

```
Dhan REST ──► live.build_payload(cfg)  ──► payloads[idx].box ──► /api/data?idx=  ──► UI (S.index)
          └─► chain_live.ChainPoller([cfg]) round-robin ──► chains[idx].box ──► /api/chain?idx=
```

## Error handling / degradation

- Per-index isolation: a failed poll for one index tags that index's payload with `error` and keeps the last good snapshot (existing behaviour, now per-index) — the other indices keep serving.
- Token expiry / BSE-access failure surfaces on the affected index's payload only; NIFTY/BANKNIFTY unaffected if SENSEX's BSE feed fails.
- Unknown `idx` param → default to NIFTY (never 500).

## Testing / verification

- Unit: `instruments.resolve_dynamic` returns plausible fut_id/expiry per index (mock scrip master).
- Live (server on :8767, market hours): `/api/data?idx=BANKNIFTY` and `/api/chain?idx=SENSEX` return non-empty, correctly-keyed payloads with sane ATM/strikes/step.
- UI: switching the header pill reloads each index; chain analyser, validator (±6 strikes), and scanner render per-index with zero console errors; rapid switching doesn't leak pollers/timers.
- Rate limit: confirm no Dhan throttle errors across a few minutes of 3-index round-robin.

## Resolved facts (confirmed against live Dhan, 2026-07-23)

The design's "honest unknowns" were all resolved during Task 0 discovery:

1. **Chain underlyings** (for `option_chain`/`expiry_list`): NIFTY `(13,"IDX_I")`, BANKNIFTY `(25,"IDX_I")`, **SENSEX `(51,"IDX_I")`** — `IDX_I` works for all three, including SENSEX on BSE. No BSE-specific `under_seg` is needed.
2. **`chain_seg` is vestigial** — `option_chain(under_id, under_seg, expiry)` takes only two ids; `chain_seg` is kept in the registry for documentation but never passed. Only `fut_seg` (`NSE_FNO` / `BSE_FNO`) matters, and it drives *both* futures and option intraday-chart calls per index.
3. **Nearest futures** (auto-resolved each startup, values as of 2026-07-23): NIFTY `61093`/2026-07-28, BANKNIFTY `61088`/2026-07-28, SENSEX `1144507`/2026-07-30.
4. **Scrip master:** `https://images.dhan.co/api-data/api-scrip-master-detailed.csv`. Relevant columns: `SECURITY_ID`, `UNDERLYING_SYMBOL`, `INSTRUMENT` (`FUTIDX`/`OPTIDX`), `SM_EXPIRY_DATE` (`YYYY-MM-DD`), `STRIKE_PRICE`, `OPTION_TYPE` (`CE`/`PE`), `EXCH_ID` (`NSE`/`BSE`).
5. **SENSEX option symbols are the generic `BSXOPT`** (not `SENSEX-…`). So `live._atm_ids` was generalized to match option legs on `UNDERLYING_SYMBOL`/`OPTION_TYPE`/`STRIKE_PRICE` from the detailed CSV (uniform across NSE/BSE), and it picks the *nearest listed strike* so a step mismatch never leaves a leg unresolved. (This was NOT in the original plan — `_atm_ids` parameterization was folded into Task 2.)
6. **Steps/windows:** step 100 for all three (BANKNIFTY/SENSEX near-ATM strikes are 100-apart; confirmed 57100 and 76800 are listed). Windows: NIFTY 1500, BANKNIFTY 2000, SENSEX 2500.
7. **Rate limit:** round-robin at `RR_GAP_S=3.5s` between indices → each index refreshes ~every 10.5s for 3 indices; a 3-minute soak showed advancing timestamps and zero throttle errors.

## Verification state (what a new AI must know)

- **Verified live off-hours:** instruments registry, chain poller (all 3 indices, isolation + soak), `/api/data?idx=` & `/api/chain?idx=` routing, and the UI pill switcher (chain analyser renders per index, no console errors, no leaked pollers).
- **Awaits a market-hours session (9:15–15:30 IST):** the futures/option **session-bar** paths — `live.build_payload` producing bars, and therefore the TAPE view, VALIDATE popup, SCAN, and MAP. These are blank for **every** index (NIFTY included) while the market is closed, because Dhan's intraday charts API serves no bars off-hours. The code paths are identical to the already-verified chain routing, so this is a data-availability wait, not a code gap. At open: load `http://localhost:8767/`, switch the pill, confirm each index's TAPE/VALIDATE(±6 strikes, T1/T2/T3)/SCAN populate from its own bars.
- **GEX overlay stays NIFTY-only** (optional local file); the switcher clears `S.gex` when leaving NIFTY so its gamma levels never bleed onto other indices.

## Out of scope (YAGNI)

- Simultaneous side-by-side multi-index view (tabs switch, not split-screen).
- Historical/replay multi-index (replay stays NIFTY-oriented; live is the target).
- Persisting the selected index across reloads (defaults to NIFTY each load).

## Note

This project is **not a git repository**, so the spec is written to disk but not committed. If the user wants version control, run `git init` first.
