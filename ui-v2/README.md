# TapeMap Dashboard v2 (live-wired)

A high-fidelity React dashboard for the TapeMap options-tape tool. This is the
Figma-generated UI with its mock data replaced by a **live data layer** that
fetches the real Python backend and maps it into the shapes the components
already consume. The components are unchanged; only the data source was swapped.

Stack: Vite 8 + React 19 + Recharts 3 + Tailwind CSS v4 (TypeScript).

## How to run

1. **Start the Python backend** (serves JSON on port 8765). Either use an
   already-running live session, or start one:

   ```bash
   python server.py live 8765
   ```

   It must respond at:
   - `http://127.0.0.1:8765/api/data?idx=NIFTY|BANKNIFTY|SENSEX`
   - `http://127.0.0.1:8765/api/chain?idx=NIFTY|BANKNIFTY|SENSEX`

2. **Start the dashboard** (from this `ui-v2/` folder):

   ```bash
   pnpm install
   pnpm dev
   ```

   Open the Vite URL it prints (default `http://localhost:5173`).

The Vite dev server proxies `/api` → `http://127.0.0.1:8765` (see
`vite.config.ts`), so the browser talks same-origin and there are no CORS issues.

## How the live layer works

- `src/data.ts` exports the target TypeScript types plus a `useLiveData(fallback)`
  React hook. On mount and every 5s it fetches `/api/data` and `/api/chain` for
  all three indices in parallel, maps each response into the component shapes
  (`INDICES`, `READS`, `KEY_LEVELS`, `ORDER_FLOW`, `CHAIN_DATA`, `EVENTS_BY_IDX`,
  `CHART_DATA`), and returns `{ data, loading, error, lastUpdated }`.
- A failing index is tolerated: the hook keeps the last-good mapping for that
  index (falling back to the bundled mock on first paint).
- `src/App.tsx` keeps the original mock constants renamed as `MOCK_*` fallbacks,
  provides the live dataset through a `DataCtx` React context, and each tab reads
  it via a `useData()` helper.

## Scripts

- `pnpm dev` — start the dev server (with the `/api` proxy).
- `pnpm build` — production build (`vite build`). Run `pnpm exec tsc --noEmit`
  for a standalone type check.
- `pnpm preview` — preview the production build.

## Notes

- The old `ui/` app in the repo root is untouched.
- This app expects the backend on `127.0.0.1:8765`. Change the proxy target in
  `vite.config.ts` if the backend runs elsewhere.
