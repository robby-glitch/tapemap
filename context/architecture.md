# Architecture Context

## Stack

| Layer     | Technology                          | Role                                    |
| --------- | ----------------------------------- | --------------------------------------- |
| Engine    | Python 3.13, stdlib only            | Feature computation, states, events, gamma layer |
| Server    | Python `http.server` (stdlib)       | Static UI + `/api/data` JSON            |
| UI        | Vanilla HTML/CSS/JS, no build step  | V2 "Replay Dashboard", SVG where needed |
| Data      | Dhan REST v2 (`dhanhq` SDK + direct `urllib` for `oi:true`) | Historical 1-min OHLCV+OI, chain, live feed later |
| Ground truth | TradingView CSV exports in `data/` | 3 labeled days for regression        |

No frameworks, no bundlers, no external fonts/CDNs. The UI must work offline.

## System Boundaries

- `engine.py` — ALL analytics: features, ranks, states, events, gamma layer,
  JSON export. The only place trading logic lives.
- `analyze.py` — thin adapter: CSVs → engine → UI JSON.
- `server.py` — serving only; zero analytics.
- `dhan_fetch.py` — all Dhan API access: instrument resolution, day fetch,
  chain fetch, conversion to engine format (incl. self-computed VWAP/σ/pivots).
- `gamma.py` (Stage 2) — Black-Scholes IV inversion, gamma, GEX profile.
  Pure math, no I/O.
- `chain_metrics.py` — full option-chain analytics (writer scores, chain
  GEX via gamma.py, max pain, PCR, IV skew, chain squeeze score). Pure
  computation, stdlib, no I/O; never imported by engine.py.
- `chain_live.py` — ChainPoller daemon: Dhan option_chain every 5s, expiry
  auto-resolve, snapshot normalization + jsonl persistence, --mock fixture
  replay. Feeds server.py's `/api/chain`; zero engine coupling.
- `ui/` — rendering only. Parses engine output; computes NO analytics.
- `data/` — ground-truth CSVs (protected) + fetched day/chain JSON.
- `context/` — these spec files; the source of truth for behavior.
- `gan-harness/`, `ui/variant-*.html`, `ui/redesign.html` — design-history
  archives; never imported by production code.

## Storage Model

- **Flat files only.** No database.
- `data/*.csv` — TradingView ground truth (read-only, never regenerate).
- `data/chain_<date>.json`, `data/day_<date>_*.csv` — Dhan-fetched artifacts.
- `data/chain/chain_<date>.jsonl` — live chain snapshots (one per 5s poll,
  auto-persisted); `data/chain_sample.jsonl` — synthetic mock fixture
  (regenerate via `python make_chain_fixture.py`).
- `.dhan_token` — single-line JWT, expires ~24h, local only, never committed
  or embedded in code.
- `C:\Users\kaam\.claude\plans\before-you-run-any-hashed-bubble.md` — approved
  gamma-layer plan.

## Auth and Access Model

- Dhan: access token from `.dhan_token`, client id 1111966509; Data APIs
  rate-limited 5 req/s (sleep ≥0.22s between calls).
- Server binds 127.0.0.1 only — never exposed to network.
- No user auth (single-operator local tool).

## Invariants

1. **No absolute thresholds.** Every feature is a percentile of the session's
   own expanding distribution or a rate-of-change vs its own baseline. Only
   relative cutoffs (percentile ranks) may appear, and each must be justified
   in a comment.
2. **Causality.** No feature may use future bars. Expanding ranks only. The
   replay engine must be identically usable as the live engine.
3. **Gamma layer is separate.** It NEVER modifies base signal logic,
   confidence, or wording. Base event stream must be byte-identical before
   and after gamma-layer changes (regression-checked by diffing replay
   output).
4. **UI renders, engine decides.** Any new analytic belongs in engine.py; the
   engine emits structured data + evidence strings ("HEAD — evidence"); the
   UI must not re-derive analytics from raw bars.
5. **Every signal carries its receipt.** No event without evidence text
   naming the actual numbers that triggered it.
6. **No order execution.** The tool never places, modifies, or cancels
   orders. Signal-only, permanently.
7. Ground-truth CSVs in `data/` are immutable.

## ctx payload + verdict additions (2026-07-21, TAPE critique refinements)

`Engine.context()` `ctx_track` now also carries (display-only, additive —
event stream unchanged, band_backtest still 219 tags):
- `z`, `bw_r` — realized σ-from-VWAP + band-width percentile
- `iv_ce/iv_pe`, `ivr_ce/ivr_pe` — ATM IV + IV rank (from GammaLayer)
- `pin` {k, dist, regime} — dealer pin (self.gamma.k) surfaced on the TAPE bar
- `t_exp` — real days-to-expiry (self.gamma.t; live.py computes from the
  expiry timestamp) — drives the expiry master-regime banner

Behavioral changes (all regression-clean vs replay_band2.txt / 219 band tags):
- **Verdict range-gated:** GO now requires `not(rng_r<0.30) and regime!=PINNED`;
  a compressed trend → WAIT "trend stalled". Kills GO-during-compression.
- **emit() merge:** recurring TRAP/DIVERGENCE with the same digit-normalized
  template within 20m collapse into a `×N` counter (scoped to those 2 kinds).
- **_cross_ev():** pivot crosses emit BREAK for the first 2/level/30m, then
  CHOP (intentional BREAK-stream change; BAND events unaffected).
- **carry_verdict():** on expiry (`self.gamma.t<=0.5`) emits EXPIRY SETTLEMENT
  (weekly options settle 15:30 — no overnight option carry) instead of the
  OI-retention → next-day-bias read.
See progress-tracker.md "TAPE-view critique refinements" for full detail/gates.
