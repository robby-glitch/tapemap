# UI v2 Dashboard (`ui-v2/`) — parallel React frontend

## What it is

`ui-v2/` is a **second, independent frontend** for TapeMap: a high-fidelity
React dashboard, originally generated in Figma Make and then **live-wired** to
the real backend. It renders the same live options-tape intelligence as the
production `ui/`, but with a modern-fintech-minimal look (dark, layered cards,
Recharts) and richer visual panels (spike radar, overlaid chart, strike
heatmap, action-zone level map, net-flow pressure histogram).

It exists so the dashboard can be evolved **without any risk to v1**. It is a
parallel experiment, not a replacement — v1 remains the production UI.

## THE SEPARATION MODEL (why this doc exists)

v1 and v2 are two fully separate frontends that share **only** the read-only
backend API. Keep them apart.

| | **v1 — production** | **v2 — experimental** |
| --- | --- | --- |
| Folder | `ui/` | `ui-v2/` |
| Stack | Vanilla HTML/CSS/JS, **no build step** | React 19 + Vite + Tailwind 4 + Recharts + TypeScript (**has a build step**) |
| Served by | `server.py` (static, port 8765) | its own Vite dev server (port 5173) |
| Git | on `main`, shipped | **only** on branch `feature/dashboard-v2` — not merged, not pushed |
| Backend/engine changes | — | **ZERO** — consumes the API read-only |

- They share **only** the read-only backend API — `/api/data` and `/api/chain`
  on `127.0.0.1:8765`. v2 makes **no** backend, engine, or `ui/` changes.
- Working on v2 never touches v1's `ui/` or the Python engine, and vice versa.
  A change to one frontend cannot break the other because they share no code —
  only the JSON contract.
- v1 continues to be the production dashboard on `main`, byte-for-byte
  unchanged by any v2 work.

**Rule of thumb:** if you are working on v2, you edit files under `ui-v2/` on
`feature/dashboard-v2` and nothing else. If you need a new backend field, that
is a v1/engine change on `main` — a different unit of work.

## How to run

1. Start the backend on port 8765 (live or replay — v2 doesn't care which):
   - `python server.py live 8765` (live), or an existing session already on 8765.
   - It must serve `GET /api/data?idx=NIFTY|BANKNIFTY|SENSEX` and
     `GET /api/chain?idx=...`.
2. Start the v2 dev server:
   ```bash
   cd ui-v2
   corepack pnpm install
   corepack pnpm dev
   ```
   Open the printed URL — default `http://localhost:5173`.

Notes:
- `pnpm` is **not on PATH** in this environment; use `corepack pnpm` (Node's
  bundled corepack shim). Same for `corepack pnpm build` / `corepack pnpm exec tsc --noEmit`.
- Vite proxies `/api` → `http://127.0.0.1:8765` (see `ui-v2/vite.config.ts`), so
  the browser talks same-origin and there is no CORS issue and no backend change.
- Build check: `corepack pnpm build` (Vite) + `corepack pnpm exec tsc --noEmit`
  (types). Both are expected to pass clean.

## Architecture

Two source files carry the whole app:

### `src/data.ts` — the live-data layer
- Exports the TypeScript types plus a `useLiveData(fallback)` React hook.
- On mount and **every 5s**, it fetches `/api/data` **and** `/api/chain` for all
  three indices (NIFTY, BANKNIFTY, SENSEX) **in parallel**, and maps each
  engine response into the exact UI shapes the components consume
  (`INDICES`, `READS`, `KEY_LEVELS`, `ORDER_FLOW`, `CHAIN_DATA`,
  `EVENTS_BY_IDX`, `CHART_DATA`, `HEAT`, `PRESSURE`, `MAP`).
- Returns `{ data, loading, error, lastUpdated }`.
- **Fault tolerant:** a failing index keeps its last-good mapping (falling back
  to the bundled MOCK on first paint), so one bad index can't blank the board.
- **MOCK fallback:** the app first-paints a bundled MOCK dataset (so there's no
  blank screen), then swaps to live. Pre-open, when `/api/data` returns no bars
  for the day, every index legitimately falls back to MOCK — the glance bar
  shows an amber `reconnecting…` chip so the mock state is never mistaken for
  live. The MOCK is deliberately varied/believable but is clearly a fallback.

### `src/App.tsx` — all components, single file
- Every component lives here; the live dataset is provided through a React
  context (`DataCtx`) and read via a `useData()` helper, falling back to the
  module-level `MOCK_*` constants while loading.
- Design tokens live in the `T` object (dark, modern-fintech-minimal:
  `#0B0E14` bg, `#141926` cards, violet `#8B5CF6` accent, green/red direction,
  amber caution). Rounded cards, 1px borders, tabular-nums mono for numbers.

Data flow: `useLiveData` → maps engine JSON → `DataCtx.Provider` → tab
components read via `useData()`. Same 5s cadence as the engine's live loop.

## Tabs / features

- **Heat** (landing) — **Live Spike Radar.** Rows = the 3 indices; 8 columns =
  `FUT VOL`, `FUT OI`, `CE VOL`, `CE OI`, `PE VOL`, `PE OI`, `GAMMA`, `SQZ`.
  Each cell's hue = direction (green bull / red bear / slate neutral), brightness
  = the rank/intensity, and a cell **glows with a ⚡** when it spikes (volume/OI
  rank ≥0.8, a gamma **regime flip**, or squeeze score ≥0.3). A header chip shows
  the live spike count. Lets you see, at a glance, which instrument's futures or
  option legs are firing.
- **Tape** — the trading view. A **real intraday chart** (Recharts) with the bold
  price line + depth fill, amber VWAP, faint ±1σ band, a **readable time axis**
  (hour-boundary ticks, not ~400 crammed labels), and the **key levels drawn ON
  the chart** as horizontal reference lines (pivots, CALL/PUT OI walls, dealer
  PIN, floor/cap, traps), Y-scaled to the near-price **action zone**. Alongside:
  a left **Key Levels rail**, a plain-English **order-flow readout** + MM
  perspective + volatility stats, and a **diverging pressure histogram** below
  the chart (bucketed net order-flow — green bars up = net buying, red down =
  net selling, height = strength).
- **Chain** — **Strike Heatmap.** CE-OI | GEX | STRIKE | PE-OI heat table centred
  on ATM (±6 strikes): CE/PE cells shaded by OI, a GEX strip colored by sign,
  wall/ATM markers. Above it, four stat cards: PCR, Max Pain, GEX regime, Squeeze.
- **Events** — plain-English event feed (newest first) translating engine event
  kinds (TRAP-SPRUNG, SQUEEZE-RISK, GAMMA-PIN, etc.) into readable lines with
  the original evidence, color-coded bull/bear/neutral.
- **Validate** — a trade checker: enter strike/side/position, get a confidence
  score + gate checks driven off the current read (timing/direction).
- **Map** — **real action-zone level map.** A vertical price axis (zoomed to the
  action zone, not the whole day) plotting the real levels: pivots (R3–S3), OI
  walls (CALL/PUT), dealer PIN, floor/cap, VWAP, ±1σ, session hi/lo, and trap
  flags — each a colored dot + leader + right-gutter label, with off-scale
  clamping. **No fabricated levels.**

Across the top (all tabs): a **cross-index scanner** (the 3 indices with price/
change/state and a computed "LOOK HERE" highlight on the most tradeable one) and
**THE READ** — a labeled `TIMING` / `DIRECTION` summary plus a one-line play,
straight from the engine's ctx.

## Honesty note

Every level and signal shown comes from **real engine/API fields** — pivots,
`wall_up`/`wall_dn`, `ctx.pin`, `ctx.floor`/`ctx.cap`, `f.vwap`/`u1`/`d1`,
`vol_r`/`oi_r`/`oi_slope`/`prem_d`, squeeze/GEX metrics, `day.events`. There are
**no invented price levels** (an earlier draft's fabricated PDH/PDL/WPP were
removed). The MOCK dataset exists only as a pre-open / first-paint fallback and
is clearly signalled as such by the `reconnecting…` chip — it is never presented
as live.

## Build history (commits on `feature/dashboard-v2`)

- `b6b8798` — live-wire the Figma app: `useLiveData` hook, `/api` proxy, MOCK
  fallback, wired all tabs to real data.
- `7139ec7` — heatmaps: market heat grid, strike heatmap, pressure tape (first pass).
- `817adf3` — real action-zone level Map (pivots, walls, pin, floor/cap, traps);
  removed fabricated PDH/PDL/WPP.
- `bef8cb7` — real intraday chart with levels overlaid + readable time axis.
- `bda7e36` — pressure tape redesigned as a diverging net-flow histogram.
- `93c63dd` — heat grid redesigned as a live spike radar (vol/OI/gamma/squeeze).

## Known polish / next steps

- **Live verification at open (~09:15 IST):** built and verified pre-open on
  MOCK; the mapping auto-switches mock→live when the backend produces bars.
  Re-check each tab against live data at the open.
- **Minor label crowding** when levels cluster tightly (Map / chart reference
  lines) — de-dup is in place but very close clusters can still crowd labels.
- Consider **persisting the active index/tab** (e.g. URL or localStorage) so a
  refresh keeps context.
- The tab-switch "bug" seen during testing was a **viewport/coordinate artifact**
  of the automated harness, **not a real bug** — the tabs work.
