# UI v2 Dashboard (`ui-v2/`) — the frontend that is becoming the product

## Status — read this first

**2026-07-29: the direction changed.** v2 is no longer a parallel experiment.
The decision is that **v2 becomes the product** and v1 (`ui/`) stays live and
untouched until v2 reaches parity, then retires.

Two consequences that reverse what this document used to say:

1. **v2 is no longer read-only against the backend.** Two backend fixes now
   live on `feature/dashboard-v2` and belong on `main` as well, because they
   affect v1 too — see "Backend changes owed to main" below.
2. **v1 is no longer the destination for new frontend work.** New UI work goes
   into `ui-v2/`. v1 gets correctness fixes only.

Everything below reflects the state as of the last commit on this branch.

## What it is

A React dashboard, originally generated in Figma Make and then live-wired to
the real backend. It renders the same options-tape intelligence as `ui/` with
richer visual panels (spike radar, overlaid chart, strike heatmap, action-zone
level map, net-flow pressure histogram) and a build step.

## Working on v1 and v2 independently

They remain **completely separable at the file level**. Nothing in one is
imported by the other; they meet only at the JSON contract.

| | **v1** | **v2** |
| --- | --- | --- |
| Folder | `ui/` | `ui-v2/` |
| Stack | Vanilla HTML/CSS/JS, no build step | React 19 + Vite + Tailwind 4 + Recharts + TS |
| Entry | `ui/index.html` + `app.js` + `style.css` | `ui-v2/src/App.tsx` + `data.ts` |
| Served by | `server.py` static, port 8765 | its own Vite dev server, port 5173 |
| Git | `main` | `feature/dashboard-v2` |
| Cache-busting | **must** bump `?v=N` in `ui/index.html` on every change | handled by Vite |

**To work on v1 only:** check out `main`, edit `ui/`, run
`python server.py live 8765`, open `http://127.0.0.1:8765`. Bump `?v=N` for
`style.css` / `app.js` in `ui/index.html` or browsers serve a stale copy — this
has bitten before.

**To work on v2 only:** check out `feature/dashboard-v2`, run a backend on
8765 (any mode), then `corepack pnpm --dir ui-v2 dev` and open
`http://localhost:5173`. Never edit `ui/` from this branch.

**To change the backend:** it serves both, so treat it as its own unit of work
and land it on `main`. Anything under `ui-v2/` never belongs on `main` until
the branch merges.

`pnpm` is not on PATH here — use `corepack pnpm` (Node's bundled shim), also
for `corepack pnpm build` and `corepack pnpm exec tsc --noEmit`. Vite proxies
`/api` → `127.0.0.1:8765` for both `server` and `preview` (see
`ui-v2/vite.config.ts`), so the browser talks same-origin with no CORS.

Launch configs live in `.claude/launch.json`: `tapemap-live-8765` (live),
`tapemap-mock-8765` (replay + mock chain, works offline), `tapemap-v2` (Vite).

## Backend changes owed to main

These are on the branch and affect **both** frontends. Merge them back:

- `chain_live.py` — `_publish` forwards `ce_pk`/`pe_pk` (session-high OI per
  book) into each strike row. Without it the field is computed and dropped.
- `server.py` — `/api/data` no longer falls back to the DEFAULT index when the
  requested one has no payload. It used to answer `?idx=BANKNIFTY` with
  NIFTY's tape, so three panels showed one session under three names.

## THE HONESTY RULES (hard-won — do not regress these)

An audit of v2 found **five instances of one pattern: a fallback rendered as
fact.** A trading screen that shows invented data indistinguishable from real
data is worse than one that shows an error. The rules that came out of it:

1. **A fallback must never look like live data.** The MOCK dataset exists so
   the first paint isn't blank. Whenever it is showing, say so at full width —
   not with a small chip beside believable prices.
2. **Failure is per index, not global.** One dead index must not inherit
   another's data or hide behind two healthy ones. `useLiveData` returns
   `dead: IndexKey[]`; dead indices strike their price and name themselves.
3. **Never compute a number you cannot source.** The old Validate tab added
   `Math.random()` to its own confidence score and hardcoded two of four gates
   to pass. Every displayed check must derive from a real field or not appear.
4. **Never invent a greek.** The feed returns `delta`/`gamma` as **null**.
   Delta is computed via Black–Scholes; if the inputs are missing the UI says
   "delta unavailable", it does not guess.
5. **Guard NaN at the source.** The chain publishes `expiry: "MOCK"` in fixture
   mode; an Invalid Date turned every greek into NaN, and because NaN
   comparisons are all false it fell through to the *wrong* branch and printed
   a confident falsehood. Ensure helpers always return finite values.
6. **Replay must be causal.** Everything bar-derived is truncated to the shown
   bar via a single `cutoff`. The strike ladder genuinely cannot be replayed
   (no per-strike history in the payload) so `Chain.aligned` is false while
   scrubbed and the ladder says it is a live snapshot.

## Architecture

### `src/data.ts` — the live-data layer

- Types plus `useLiveData(fallback)`, returning
  `{ data, loading, error, lastUpdated, barCount, at, dead }`.
- Every 5s it fetches `/api/data` and `/api/chain` for all three indices in
  parallel and maps them into the shapes the components consume (`INDICES`,
  `READS`, `KEY_LEVELS`, `ORDER_FLOW`, `CHAIN_DATA`, `EVENTS_BY_IDX`,
  `FOCUS_BY_IDX`, `CHART_DATA`, `HEAT`, `PRESSURE`, `MAP`).
- Raw payloads are retained so **replay** re-maps in memory: `at(idx)` renders
  any bar, `barCount(idx)` sizes the scrub. No re-fetching.
- `mapIndex(D, C, at?)` — `at` is the replay bar index; see honesty rule 6.
- `evDir()` — per-kind event direction. A keyword scan cannot do this: "BULL
  TRAP SPRUNG" contains BULL and is bearish, a +2σ BAND-REVERSAL is a fade,
  DIVERGENCE at a HIGH is bearish. `ui/app.js`'s version is the authority.
- `buildFocusFeed()` — port of v1's FOCUS: drops STATE churn and `[LOW]` band
  tags, blocks a kind+direction repeating inside 10 min, silences a *quiet*
  kind echoing the log's direction within 8 min, and collapses a contradictory
  minute into one CONFLICT line. Measured 35% reduction on a real session.
- `validateTrade()` — deterministic trade check; see Validate below.

### `src/App.tsx` — all components, single file

- Components read the dataset through `DataCtx` via `useData()`.
- **Design tokens** live in `T`. Colour carries exactly one meaning each:
  **brass `#E0A852` is structure** (levels, walls, pins, σ-bands, ATM, positive
  GEX, READY) and **green/red are direction only**. Before this, purple meant
  "spring" while green/red also meant up/down, so hue resolved to neither.
- **ANSWER band** above the tabs, always visible: price, direction/timing
  chips, the read, structural chips (max pain + distance, GEX with book-zone
  context, PCR/squeeze) and a **CHANGES IF** line naming the nearest level
  either side. The read appears here **once** — it used to be repeated in
  `GlanceBar` as well.
- **Replay transport**: play/pause, 1/3/8/25×, bar clock, range, RETURN TO
  LIVE. Entering replay starts at the last 60 bars.
- **TokenCapture**: clipboard first, password field fallback, posts to
  `/api/token`. The token is never logged, echoed or rendered; the input is
  `type=password` and cleared before any await. Present in the command bar and
  inside the NOT LIVE banner.

## Tabs

- **Heat** (landing) — Live Spike Radar. Rows = the 3 indices, 8 columns
  (`FUT VOL`, `FUT OI`, `CE VOL`, `CE OI`, `PE VOL`, `PE OI`, `GAMMA`, `SQZ`).
  Hue = direction, brightness = intensity, ⚡ = spike. **Dead indices show
  "no tape" and are excluded from the spike count** — they used to render mock
  rows with invented signals like "⚡ AMPLIFIED-UP".
- **Tape** — intraday chart (Recharts) with VWAP, ±1σ, levels drawn on the
  chart, key-levels rail, plain-English order flow, MM perspective, and a
  diverging net-flow pressure histogram.
- **Chain** — CE-OI | GEX | STRIKE | PE-OI heat table around ATM, with an
  **OffPeak badge** (from 8%, amber at 30%) showing how far each book has
  fallen from its own session high. Four stat cards above.
- **Events** — the narrative feed with a **FOCUS** toggle (default on,
  persisted). Chain `wall_log` events (WALL-MIGRATION / ROLE-FLIP) are merged
  in and **protected from cropping**: the feed keeps the last 10 overall plus
  the last 3 structural.
- **Validate** — a real trade check. Strike comes from a select of the live
  ladder; premium, intrinsic/time split and breakeven update as you choose.
  Six gates, each computed: method-read alignment, **move required to break
  even vs the move the ATM straddle is pricing**, contract fit by computed
  delta, dealer regime read differently for buyer and seller, heaviest book
  between spot and breakeven, and bid-ask as a share of premium.
- **Map** — action-zone level map: pivots, OI walls, PIN, floor/cap, VWAP,
  ±1σ, session hi/lo, trap flags. No fabricated levels.

## Build history (`feature/dashboard-v2`)

- `b6b8798` live-wire the Figma app · `7139ec7` heatmaps · `817adf3` level map
- `bef8cb7` intraday chart · `bda7e36` pressure histogram · `93c63dd` spike radar
- `4225db0` answer band, one-meaning colour, stop showing fake prices as real
- `7a0d03e` consume the new chain fields (wall events, book zone, OI peaks)
- `cf50e50` FOCUS feed port + event-direction fix
- `ccea71b` replay scrub, made causal (v1's was not)
- `57d3320` validator rewrite — the old score was partly random
- `3b5e9c6` stop serving one index's tape under another's name
- `92a7bf7` heat radar dead-index rows; map trap causality
- `a27780e` Dhan token capture

## Open items

- **Verify against a live session.** Everything since 2026-07-28 was verified
  against the mock-chain fixture because Dhan was unreachable
  (`getaddrinfo failed` for `api.dhan.co`). Two things are coded and
  typechecked but have never rendered: the **OffPeak badge** (nothing in the
  fixture is 8% off peak) and the FOCUS **"+N agreeing"** merge.
- **Merge the two backend fixes to `main`** (see above).
- **Performance**: `useLiveData` re-maps three indices every 5s, and replay
  re-maps on every scrub tick. Fine at 375 bars; the first thing to feel slow
  if multiple days are ever loaded.
- Consider persisting active index/tab across refresh.
- v1 parity: the porting list is complete — new chain fields, FOCUS, replay
  scrub and token capture are all done.
