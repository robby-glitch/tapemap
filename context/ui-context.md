# UI Context

## Theme

Dark only. No light mode. The design language is a purpose-built trading
instrument — "Modern Industrial Minimalism" (per the approved Stitch V2
"Replay Dashboard" direction): near-black layered surfaces, rigid grid, 1px
structural borders, zero decoration, color reserved strictly for meaning.
Built for 6-hour continuous market-hours use.

## Colors

All components must use these tokens (defined in `ui/style.css :root`) — no
hardcoded hex values in rules.

| Role                  | CSS Variable | Value                  |
| --------------------- | ------------ | ---------------------- |
| Page background       | `--bg`       | `#0a0d14`              |
| Panel surface         | `--pan`      | `#0e121b`              |
| Raised surface        | `--pan2`     | `#111726`              |
| Border                | `--edge`     | `#1e2739`              |
| Primary text          | `--ink`      | `#dbe6f5`              |
| Muted text            | `--dim`      | `#8090a8` (raised from #66748c for contrast) |
| Armed / strike        | `--vio`      | `#8b5cf6`              |
| Coiling / trap risk   | `--amber`    | `#ffbf00`              |
| Direction up          | `--up`       | `#2ec27e`              |
| Direction down        | `--dn`       | `#ff5f6b`              |
| Balance / neutral     | `--slate`    | `#5d6b84`              |
| Gamma / MM layer      | `--gamma`    | `#3fc1c9` (cyan — reserved for gamma strip/events) |

Semantic rule: a color never decorates; it always encodes state or direction.

## Typography

| Role                 | Font                     | Variable |
| -------------------- | ------------------------ | -------- |
| UI text              | Segoe UI / system-ui     | body `font` |
| Data receipts / mono | Cascadia Code, Consolas  | `--mono` |

Numbers always `font-variant-numeric: tabular-nums`. Hierarchy: state word
(17px+) > hero card headlines (16px 800) > body (12.5px) > receipts (11px
mono) > labels (9.5–10px letterspaced caps).

## Border Radius

| Context    | Value |
| ---------- | ----- |
| Everything | `0` — industrial flat, no exceptions |

## Component Library

None. Vanilla HTML/CSS/JS only (offline requirement, no build step). Reusable
patterns live as CSS classes: `.card` (+ `.trap/.mo/.calm/.fired` variants),
`.ev` (+ `.loud`), `.lrow` (+ `.stk/.live`), `.book`, `.ph` (panel header).

## Layout Patterns

- Shell: header (brand · day tabs · state chip · clock/play/speed) →
  book strip (3 tiles) → [MM/gamma strip — planned] → main 3-column grid
  (300px narrative rail | 1fr hero panels | 252px level ladder) → footer
  (scrubber + carry strip).
- Hero panels stack vertically: TRAP RADAR above MOMENTUM WINDOWS.
- Ladder rows sorted by price descending; LIVE row is the loudest element
  on screen (violet fill, 19px price); strike row violet-tinted; Stage-2
  adds FLIP and WALL rungs (cyan) when GEX data present.
- `min-width: 1180px`; below that the page scrolls horizontally, never
  reflows.

## DATA Tab — Option Chain Analyser (2026-07-21)

- Full-viewport overlay (body.dataMode), fed ONLY by `/api/chain` (5s poll,
  active tab only — cleared on switch back to TAPE). Zero client analytics.
- Structure: `#chTop` 7-cell strip (SPOT · PCR · MAX PAIN · GEX regime
  ▲/▼ glyphed · FLIP · ATM IV/skew · SQUEEZE) → `#chWrap` grid (ladder 1fr |
  300px side rail).
- Ladder (`.crow`, 21px rows, keyed by strike, patched in place): CE OI bar |
  ΔOI | IV | LTP ‖ STRIKE ‖ LTP | IV | ΔOI | PE OI bar | dealer-GEX
  diverging bar. OI bars tinted by writer score (cyan `--gamma` writer /
  red buyer / slate mixed); MP + WALL chips on strike cell; SPOT (violet)
  and FLIP (dashed cyan) overlay lines interpolated between rows.
- Side rail: PAIN MAP (squeeze % bar + verdict + per-strike trapped/unwind/
  premium receipts) and 4 SVG sparklines (PCR · GEX · spot/flip/maxpain ·
  squeeze).
- Fallback: `/api/chain` 404 → `#dataView.legacy` shows the old widget grid
  (`#dvTop/#dvGrid`) + amber `#lgNote` notice (replay days w/o chain data).

## Icons

No icon library. Text glyphs only: ▲▼ (OI/direction), ⚠ (trap), ◆
(momentum), — (empty note). Sharp geometric characters, consistent with the
flat instrument aesthetic.

## TAPE-view strips added 2026-07-21 (post-critique)

Top-of-view banners (DOM order under <header>), all rendered from engine ctx
fields — zero client-side analytics:
- `#expiryBar` (magenta) — expiry master-regime. renderExpiry(ctx) shows it
  ONLY when ctx.t_exp<=1.0 (0DTE badge <=0.5): pin + ATM IV + "crushed" flag +
  "SELL PREMIUM · fade to pin · trend labels unreliable — theta rules".
  `:empty{display:none}` when not expiry.
- `#ctxBar` gained `#pinChip` (◎ PIN k · px±d) between #breadth and #ctxLine —
  dealer pin magnet; magenta=PINNED, cyan=CEILING/FLOOR; empty→hidden.
- `#volStrip` under #mmStrip — REALIZED σ / 30m RANGE+pctile / BANDS pctile /
  INSIDE ±1σ / ATM IV+rank / fused COILED-EXPANDED-NORMAL tag. renderVol(ctx,g).
ctx fields consumed: z, bw_r, iv_ce/pe, ivr_ce/pe, pin{k,dist,regime}, t_exp.

Narrative log: `#feed` is now a real scroll viewport (main grid-row
minmax(0,1fr) + min-height:0 on #railLog/#feed) — auto-pins to newest event.
"TODAY SO FAR" beats WRAP (full engine head; the old JS 64-char slice removed).
New event kinds: `CHOP` (#c9a24a; chop-suppressed pivot re-cross); TRAP/
DIVERGENCE lines carry `×N` when merged.

CACHE-BUST DISCIPLINE: bump `style.css?v=` and `app.js?v=` in index.html on
EVERY ui edit (browser serves stale files otherwise). Currently style v=14 / app v=18.

## TAPE-view additions (post-review, 2026-07-23)

- **Price ribbon** (`#ribbon`, between #volStrip and <main>): FUT close +
  VWAP + ±2σ envelope + colored LOUD-event dots (tooltips) + a future-mask &
  amber cursor. `renderRibbon(i)` builds the SVG once per day (cached on
  `S._ribbonSig = day + ":" + bars.length`), moves only cursor/mask per frame.
  Drag anywhere on it to scrub. Hidden in DATA mode.
- **rAF render throttle**: `render()` is a requestAnimationFrame-coalescing
  wrapper around `_render()` — 25× playback (20ms timer) collapses to one
  paint/frame.
- **Keyboard**: Space play/pause, ←/→ step, Shift+←/→ jump to nearest LOUD
  event (`seekEvent`), Home/End. Guarded so typing in inputs/selects is not
  hijacked (`e.target.matches?.(...)`).
- **Feed click-to-seek**: each `.ev` row carries `data-t`; clicking scrubs to
  that minute. ×N-merged rows show the collapsed timestamps as a tooltip
  (`ev.data.times`).
- **Status banner** (`#liveBanner`, amber; green `.ok`): `showBanner(msg, ok)`
  / `hideBanner()` surface live_error, live-refresh failure, chain/token errors,
  server-unreachable; dismiss + 5-min mute. Token messages embed a capture
  button.
- **⟳ TOKEN button** (`#tokBtn` in #controls): `captureToken()` reads the
  clipboard, sanity-checks the JWT, POSTs `/api/token`; a `type=password` paste
  field is the fallback. `postToken` → `pollUntilLive()` pulls the tape in
  within seconds. Token never stored in localStorage/console/DOM text.
- **Persistence** (localStorage `tapemap.*`, `lsGet`/`lsSet`): index, view,
  speed, chain sub-tab restored on boot.
