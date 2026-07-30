# UI v2 Dashboard (`ui-v2/`) — the frontend that is becoming the product

## Picking this up fresh — do these four things first

1. **Be on the right branch.** `git checkout feature/dashboard-v2`. All v2 code
   and this document live there; `ui-v2/` does not exist on `main`.
2. **Start a backend on 8765**, then the Vite server. Configs are in
   `.claude/launch.json`:
   - `tapemap-live-8765` → real market data (needs a valid Dhan token).
   - `tapemap-mock-8765` → replay + mock chain. **Works offline.** Serves only
     NIFTY; BANKNIFTY/SENSEX correctly report "no tape" — that is the fix
     working, not a bug.
   - `tapemap-v2` → `corepack pnpm --dir ui-v2 dev`, opens on 5173.
3. **Expect a token prompt.** Dhan tokens are daily. If the tape is dead, click
   **⟳ TOKEN** in the UI (clipboard, or a password field if the browser blocks
   clipboard access). Never log, echo or render the token.
4. **Read THE HONESTY RULES below before changing any display.** Five separate
   bugs in this app came from one habit: showing a fallback as if it were real.

Gates before you commit: `corepack pnpm exec tsc --noEmit`, `corepack pnpm
build`, and `python -m pytest -q` from the repo root (43 tests — the two
newest are `test_session_json.py`). Verify in the
browser in a **fresh tab** — React hook-order warnings after an edit are HMR
artifacts and do not reproduce on a clean load.

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

## Backend changes and where they live

The engine serves both frontends, so a backend change is its own unit of work
and belongs on `main`.

**Already merged to `main` (`c2fc677`)** — nothing owed:
- `chain_live.py` `_publish` forwards `ce_pk`/`pe_pk` (session-high OI per
  book) into each strike row; without it the field was computed and dropped.
- `server.py` `/api/data` no longer falls back to the DEFAULT index. It used to
  answer `?idx=BANKNIFTY` with NIFTY's tape, so three panels showed one session
  under three names.

**Still only on this branch** (`e6a134e`), because the tab that uses it is here:
- `chain_metrics.ChainState.minutes` + `oi_flow()`, and `server.py`'s
  `/api/oiflow` route. Take these to `main` if v1 ever needs the table, or let
  them ride along when the branch merges.

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

## Four bugs from the Trade tab, findable only by rendering

1. `session_json()` in `engine.py` dropped a whole FUT bar whenever either
   option leg was missing, silently intersecting the futures series with ATM
   option availability. Fixed on `main` (`c91c9d5`) with a test; v1's
   three-book view now re-applies that intersection explicitly at its display
   boundary in `ui/app.js` `setDay`, so v1 rendering is unchanged.
2. A `<canvas>` is a **replaced** element, so `position:absolute; inset:0`
   does **not** stretch it — it takes its intrinsic size from its
   `width`/`height` attributes. The overlay rendered at device-pixel size
   (1.25× too large) and every level line misaligned until its CSS size was
   set explicitly alongside the backing store.
3. React `StrictMode` (on in `main.tsx`) remounts effects in dev, destroying
   and recreating the chart engine — but a `useRef` holding the previous
   `{day, barCount}` survives that remount, so the data effect took its
   `updateLast` path against a brand-new empty engine and the chart held
   **one** candle instead of 375. A fresh engine must always be given the
   full `setData`.
4. Sizing the chart with a hardcoded `calc(100vh - Npx)` is wrong here,
   because the height of the dashboard chrome above the tab is
   content-dependent (the ANSWER band wraps differently per index and
   state). The available height is measured instead, and re-measured after
   every render — measuring only on mount left a stale height when switching
   from a dead index, overflowing the page by 227px.

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
- **Trade** — Phase 1 of the Tape Chart: the index futures tape on the
  vendored CandL Charts canvas engine, VWAP+σ overlay, OI pane, MAP levels,
  replay cursor. See "Tape Chart, Phase 1" below.
- **Tape** — intraday chart (Recharts) with VWAP, ±1σ, levels drawn on the
  chart, key-levels rail, plain-English order flow, MM perspective, and a
  diverging net-flow pressure histogram.
- **Chain** — CE-OI | GEX | STRIKE | PE-OI heat table around ATM, with an
  **OffPeak badge** (from 8%, amber at 30%) showing how far each book has
  fallen from its own session high. Four stat cards above.
- **OI Flow** — Trending OI. One row per clock mark: call and put OI **added
  since the open** across the selected strikes, their difference, strength,
  change-in-direction, PCR, day high/low breaks and a bullish/bearish call.
  Interval selector (5/15/30/60) and per-strike toggles. Served by
  `/api/oiflow`; see "Trending OI" below for the exact semantics, which were
  validated against a reference tool on real 2026-07-28 data.
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

## Trending OI (`/api/oiflow`) — semantics, verified not assumed

Two things the column labels make easy to get wrong. Both cost a wrong first
attempt, both are now locked by tests:

1. **"Call OI added" is Dhan's cumulative day CHANGE per strike (`oi_chg`),
   not the outstanding OI.** Summing outstanding OI gives ~1.8x the numbers
   and the wrong PCR (1.04 where the reference read 1.18).
2. **Each row is the chain AS AT its clock mark** — a sampled series, not an
   average over the interval that follows. Bucketing it the other way shifts
   every row by one mark.

```
call/put    = sum of per-strike oi_chg over the selected strikes
diff        = put - call                pcr = put / call
strength    = diff / max(call, put)     (signed)
chg_dir     = diff(t) - diff(t-1)
chg_dir_pct = chg_dir / |diff(t-1)|
sentiment   = BULLISH when diff > 0
brk         = a NEW day high/low made inside that mark (DHB / DLB)
```

Checked against six reference rows on our own 2026-07-28 capture: call/put
within 0.2-2.7%, PCR within 0.04, sentiment identical on all six; the residual
is sampling instant. Break detection independently found DHB 24041.0 at 11:00
where the reference showed D.H.B. (24040.9).

`ChainState` retains the **last snapshot of each minute per strike**
(`self.minutes`, a few hundred KB), so one grid serves every interval with no
re-reading. Aggregation is server-side on purpose: the raw chain is ~180 MB a
day and must never reach the browser.

## Tape Chart, Phase 1 (`ui-v2/src/trade/`) — the Trade tab

Phase 1 of the design in `docs/superpowers/specs/2026-07-29-contract-tape-design.md`;
implementation plan `docs/superpowers/plans/2026-07-30-tape-chart-phase1.md`.

- **No new backend route.** Everything comes from `/api/data` as it already
  stood, plus `/api/chain` for two chain levels.
- **Vendored library**: `ui-v2/src/vendor/candl/` — CandL Charts
  (`github.com/rahulsangam7/Candl`, `@candllabs/charts`, Apache-2.0), pinned
  at `538938105834d9231860d639e4b03956e5f3dd67`, 58 files (upstream `src/` +
  LICENSE + NOTICE) compiled from source by Vite because the package isn't on
  npm and its `files` field ships only `dist`. **Pristine, never edited** —
  adaptations live beside it in `src/trade/`. Provenance + re-vendoring steps:
  `ui-v2/src/vendor/VENDOR.md`. Required `noUnusedLocals`/`noUnusedParameters:
  false` in `ui-v2/tsconfig.json` (upstream compiles with both off).
- **Our code**, four files in `src/trade/`: `indicators.ts` (pure reshaping
  of payload arrays into the engine's `IndicatorRenderData` — a 7-output
  VWAP+σ overlay and a 1-output OI pane; computes nothing — plus
  `dayBase`/`dayPrecision` for session-date handling), `LevelsOverlay.ts`
  (the only file touching the engine's coordinate system; re-queries its
  converters every frame to draw the `MAP` levels), `ContractChart.tsx`
  (mounts the engine, feeds `setData`/`updateLast`, drives
  `setReplayCursor`), `TradeTab.tsx` (composition + the stat-strip header).
- **New shared module `ui-v2/src/theme.ts`**: the design tokens `T` were a
  module-local const in `App.tsx` (used 236 times); moved here so `trade/`
  could share them without a circular import from `App.tsx`. `App.tsx` now
  imports `T` from `theme.ts`; all 11 token values unchanged.
- **`data.ts`**: new `TapeBar` type and a `tapeBars(idx)` selector on
  `useLiveData` returning `{ day, bars }` — the **full** day, deliberately
  never truncated for replay, because the engine's own replay cursor does
  the clipping and truncating the array would additionally resize the
  chart's time axis. Also `Chain.flipPx` now surfaces the chain's `flip_px`,
  computed server-side and previously dropped on the floor by the mapping.
- Candle colours aligned to `T.bull`/`T.bear` through the library's
  sanctioned `setSettings()` hook, not by editing the vendored theme (whose
  own candles are teal/red).
- Replay is causal at both layers: the engine's `setReplayCursor(index)`
  clips every series-derived layer, and the header reads the shown bar, not
  the newest.
- **Honesty behaviours**: an index with no tape shows a full-width notice
  and draws no chart at all (verified: zero canvases). `MAX PAIN` and
  `GEX FLIP` are drawn only when live — the chain is a snapshot with no
  per-strike history, the same reason `Chain.aligned` goes false while
  scrubbing. `GEX FLIP` is omitted entirely when the chain's flip price is
  `null` rather than inventing a level. A session key with no year (the CSV
  replay keys are `Jul 15`/`Jul 16`/`Jul 17`) is disclosed in the header and
  in a line beneath it, because the chart's date axis then infers the year —
  the month, day and intraday clock are real.

**Verified** against the `tapemap-mock-8765` replay backend (`Jul 17`, 375
bars) in a real browser: 156 candle clusters spanning 99.6% of the plot
width with both up and down candles; the overlay canvas rect exactly
matching the chart canvas rect; header values matching the payload
bar-for-bar (`15:29`, `24344.0`, `15.10M`, `375 / 375`); scrubbing to bar 101
clipping the chart to 102 clusters and the header reading `10:55 / 24228.0 /
15.26M / 101 / 375`; `MAX PAIN 24300` drawn while live; BANKNIFTY rendering
zero canvases with the no-tape notice; zero console errors.

**Not yet verified — a genuine live session.** In particular the
minute-rollover path in `ContractChart` (where a bar count that grows by
exactly one writes the now-final previous bar before appending the new one)
cannot be exercised by the static replay fixture — only the same-minute
refresh path is. Also unverified live: `GEX FLIP` actually drawing, since the
mock chain's `flip_px` is `null`.

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
- `0e390b6` context files brought in line with reality
- `93b3f9d` merge main (backend fixes landed there as `c2fc677`)
- `e6a134e` Trending OI — `/api/oiflow` + OI Flow tab
- `dce8e99` vendor CandL charting engine @5389381 (Apache-2.0, source-compiled)
  · `b2e7ff8` tapeBars() — full-day FUT series · `e727383` trade/indicators —
  reshape payload series into CandL render data
- `c2a9bba` parse the real month/day from replay session keys · `d3faf35`
  trade/LevelsOverlay — MAP levels via engine converters · `b262abb`
  trade/ContractChart — CandL mount, live updates, replay cursor
- `65f845e` TradeTab — stat-strip header, honest date disclosure, shared
  tokens · `eca05f6` clamp the replay cursor at both ends; amber for REPLAY ·
  `a412c0d` Trade tab — index tape on the CandL engine
- `10c6e44` size the overlay canvas in CSS px; measure the chart's available
  height · `2ed4e2a` give a freshly created chart engine the full series ·
  `57039d8` re-measure the chart's available height after every render ·
  `a008eeb` keep level labels clear of the chart's own legend row

## Open items

- **Trade tab: verify against a genuine live session.** The
  `tapemap-mock-8765` fixture only exercises the same-minute refresh path;
  the minute-rollover path in `ContractChart` and a live-drawing `GEX FLIP`
  (mock `flip_px` is `null`) are coded and typechecked but never rendered.
- **Verify against a live session — this is the top item.** Everything after
  the 2026-07-28 close was verified against the mock-chain fixture, which
  serves only NIFTY and restarts at 09:15. Three things are coded, typechecked
  and never actually rendered:
  - the **OffPeak badge** (nothing in the fixture is 8% off its peak),
  - the FOCUS **"+N agreeing"** merge (no qualifying minute in that data),
  - **OI Flow at depth** — the fixture only ever accumulates a few marks with
    its own strikes (23900-24700), not a real ladder across a full day.
- **Performance**: `useLiveData` re-maps three indices every 5s, and replay
  re-maps on every scrub tick. Fine at 375 bars; the first thing to feel slow
  if multiple days are ever loaded.
- Consider persisting active index/tab across refresh.
- v1 parity: the porting list is complete — new chain fields, FOCUS, replay
  scrub and token capture are all done.
