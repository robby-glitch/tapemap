# Architecture Context

## Stack

| Layer     | Technology                          | Role                                    |
| --------- | ----------------------------------- | --------------------------------------- |
| Engine    | Python 3.13, stdlib only            | Feature computation, states, events, gamma layer |
| Server    | Python `http.server` (stdlib)       | Static UI + `/api/data` · `/api/chain` · `/api/gex` · POST `/api/token` |
| UI (v1)   | Vanilla HTML/CSS/JS, no build step  | Production "Replay Dashboard" (`ui/`), SVG where needed |
| UI (v2)   | React 19 + Vite + Tailwind 4 + Recharts + TS | **Separate, parallel** frontend `ui-v2/` (branch `feature/dashboard-v2` only) — see `context/ui-v2-dashboard.md` |
| Data      | Dhan REST v2 (`dhanhq` SDK + direct `urllib` for `oi:true`) | Historical 1-min OHLCV+OI, chain, live feed later |
| Ground truth | TradingView CSV exports in `data/` | 3 labeled days for regression        |

No frameworks, no bundlers, no external fonts/CDNs. The UI must work offline.

## System Boundaries

- `engine.py` — ALL analytics: features, ranks, states, events, gamma layer,
  JSON export. The only place trading logic lives.
- `analyze.py` — thin adapter: CSVs → engine → UI JSON.
- `server.py` — serving only; zero analytics. Also POST `/api/token`
  (validate via chain_live.token_status → write .dhan_token → hot-reload the
  poller; token never logged). Crash-proof live startup: binds immediately with
  "starting up" payloads and resolves instruments + builds the tape in the
  background, so a stale/missing token can't stop boot.
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
- `ui/` — rendering only. Parses engine output; computes NO analytics. This is
  the **v1 production UI** on `main`, unchanged by any v2 work.
- `ui-v2/` — a **separate, parallel React/Vite frontend** (branch
  `feature/dashboard-v2` only; not merged/pushed). Consumes the same `/api/data`
  · `/api/chain` backend **read-only** — makes ZERO engine/backend/`ui/` changes.
  Fully documented in `context/ui-v2-dashboard.md`.
- `data/` — ground-truth CSVs (protected) + fetched day/chain JSON.
- `context/` — these spec files; the source of truth for behavior.
- `archive/` — old replay_*.txt regression baselines + superseded UI
  prototypes (meridian/redesign/tapemap/tapescroll/variant-*); design history,
  never imported by production code. `gan-harness/` likewise.

## Storage Model

- **Flat files only.** No database.
- `data/*.csv` — TradingView ground truth (read-only, never regenerate).
- `data/chain_<date>.json`, `data/day_<date>_*.csv` — Dhan-fetched artifacts.
- `data/chain/chain_<date>.jsonl` — live chain snapshots (one per 5s poll,
  auto-persisted); `data/chain_sample.jsonl` — synthetic mock fixture
  (regenerate via `python make_chain_fixture.py`).
- `.dhan_token` — single-line JWT, expires ~24h, local only, gitignored,
  never embedded in code. `.dhan_client` — numeric client id, gitignored.
- Plans live in `C:\Users\kaam\.claude\plans\` (latest: the post-review
  remediation plan). Gamma-layer + multi-index specs are under
  `docs/superpowers/`.

## Auth and Access Model

- Dhan: access token from env `DHAN_TOKEN` or `.dhan_token` (both gitignored);
  client id from env `DHAN_CLIENT_ID` or a `.dhan_client` file (never in source).
  Token can be refreshed at runtime via POST `/api/token` (the ⟳ TOKEN button),
  which validates and hot-reloads the poller. Data APIs rate-limited 5 req/s
  (sleep ≥0.22s between calls).
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
  OI-retention → next-day-bias read. On non-expiry days it is now WRITER-AWARE
  (2026-07-23): retention counts in the direction of who holds the book
  (writer-built = defended; buyer-built = inverted; clamped at 0), using
  gamma.w scores which are appended to the message.
See progress-tracker.md "TAPE-view critique refinements" + the 2026-07-23
post-review entry for full detail/gates.
