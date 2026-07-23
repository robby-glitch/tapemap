# Code Standards

## General

- Keep modules small and single-purpose; analytics only in engine.py/gamma.py.
- Fix root causes; never layer workarounds over defects.
- Every event message follows `"HEAD — evidence"` (em-dash separator); the UI
  splits on `" — "`. Never break this contract.
- No fabricated data anywhere — every number shown traces to a bar or an
  engine computation.

## Python (engine.py, analyze.py, server.py, gamma.py, dhan_fetch.py)

- Python 3.13; stdlib only for engine/server/analyze. `dhanhq` allowed only
  in dhan_fetch.py (and prefer direct `urllib` REST when the SDK lacks a
  flag, e.g. `oi:true`).
- No absolute market thresholds — percentile-rank cutoffs only, each with a
  one-line justification comment (architecture invariant 1).
- All features causal: computed from bars ≤ current index (invariant 2).
- Column access for TradingView CSVs by index (headers contain mojibake).
- Timestamps: IST (UTC+5:30); Dhan epochs converted explicitly.
- Rate limits: ≥0.22s sleep between Dhan data calls (5/s cap).
- Credentials only at runtime, never hardcoded: token via env `DHAN_TOKEN` or
  `.dhan_token`; client id via env `DHAN_CLIENT_ID` or `.dhan_client`
  (`dhan_fetch._client_id()`). All gitignored. Token refreshable in-app via
  POST `/api/token` (⟳ TOKEN button) — validated, never logged.

## JavaScript (ui/app.js)

- Vanilla ES2020+, no dependencies, no build step, no external CDNs (offline
  requirement).
- UI derives display state ONLY from engine JSON (`/api/data`) — no analytics
  re-derivation from raw bars beyond formatting.
- Event kind → color/loudness maps live in one place (`EVC`, `LOUD`, `COL`).
- `font-variant-numeric: tabular-nums` for every numeric display.

## Styling (ui/style.css)

- All colors via CSS custom properties in `:root` — no hardcoded hex in
  rules or JS-injected styles beyond the token values themselves.
- Color = meaning only: slate balance/neutral, amber coiling/trap-risk,
  violet armed/strike, green/red direction, cyan gamma/MM layer.
- 0px border radius (industrial flat), 1px borders for structure, no
  shadows/glassmorphism.
- Dark only. `min-width: 1180px` guard; horizontal scroll below that.

## v2 frontend (ui-v2/ — separate stack)

- `ui-v2/` uses a **different stack** — React 19 + TypeScript + Tailwind 4 +
  Vite + Recharts, **with a build step** (`corepack pnpm build`; `pnpm` isn't on
  PATH, use `corepack pnpm`). This is intentionally distinct from v1's no-build,
  no-dependency, offline vanilla standard above.
- These v1 standards are **unchanged** and continue to govern `ui/`. v2 lives
  only on branch `feature/dashboard-v2` and consumes the `/api` backend
  read-only. See `context/ui-v2-dashboard.md`.

## API / Data

- `/api/data` response shape is a contract; additive changes only (new keys
  fine; never rename/remove existing ones — and per workflow rules: engine
  first, regression gate, then UI consumes new keys).
- Fetched artifacts land in `data/` with deterministic names
  (`chain_<YYYY-MM-DD>.json`).

## File Organization

- `engine.py` / `gamma.py` — analytics (pure; gamma.py has no I/O).
- `analyze.py` / `server.py` — glue and serving.
- `dhan_fetch.py` — all external data access.
- `ui/` — presentation only.
- `context/` — specs; `data/` — data; scratch experiments go to the session
  scratchpad, never the repo root.
