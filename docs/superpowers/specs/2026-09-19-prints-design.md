# Prints — GoCharting's ladder, recorded and drawn in ui-v2

**Date:** 2026-09-19 · **Status:** specification, nothing built yet · **Branch:** `feature/operator-objects`
**Sources:** the operator's ruling of 2026-09-19 ("GoCharting is ~₹1500/month; replace it eventually, keep it until
the replacement is complete"), the four research briefs of 2026-09-19 (Upstox API, feed architecture, rendering,
order-flow algorithms), and the two codebases read in full on 2026-09-19. Every claim about existing code carries a
file:line. Where a value had to be chosen and no source named it, the choice is logged in §J.

**Read first:** `START-HERE.md` §0, `CLAUDE.md` rules 5–7 and 9, and
`C:\Users\kaam\Desktop\Go charting\orderflow-desk\docs\BRIEF-for-the-builder.md` §0 (the reading layer is
protected; this spec touches none of it). Paths below written as `orderflow-desk/...` are under that folder.

---

## §A Purpose and boundary

**What this is.** The first half of replacing GoCharting: its footprint prints — per-price buy and sell volume with
trade counts, which the `orderflow-desk` extension already receives off GoCharting's Web Worker
(`orderflow-desk/src/shell/tap.js:39`, `src/engine/adapter.js:74–83` and `:125–150`) — carried over the existing
`POST /api/frame` wire, written to a forward record on this server, and drawn as a cells chart in `ui-v2`.

**What it is not.** It is not an Upstox-derived tape (that is spec 2, with its replacement gate), not a DOM or
heatmap (the extension sees no depth from GoCharting — grep of `adapter.js`/`main.js`/`tap.js` for depth/orderbook
is empty), not a signal, and not a verdict. It draws counts of executed prints. Every number on it is `[M]`.

**The trajectory it serves.** While GoCharting is open, this record is the ground truth. Spec 2 builds the same
cell shape from Upstox snapshots, tagged `[I]`, and measures it against this record per bar and per price. The
operator states the pass bar before reading that number. Until it passes, GoCharting stays. Nothing in this spec
assumes it ever passes.

**Done-condition, stated now (CLAUDE.md rule 9; `frame.py:19–26` precedent):** after five live sessions with the
Prints tab available, if the operator still opens GoCharting's own footprint rather than Prints for any read, the
pane is not finished; the reason goes in `context/DEFERRED.md`, named, and the pane is fixed or removed. There is
no kill clock on a view; there is one on a claim, and the claim lives in spec 2.

**Two populations, one word — the naming rule.** `ui-v2/src/trade/footprint.ts` already means *the extension's
event record* (its docstring, lines 4–12). GoCharting calls the chart a footprint. This spec uses **prints** for the
cells, **ladder** for the raw per-price rows a bar carries, and never `footprint` for either (CLAUDE.md rule 5).

---

## §B The wire — one extension change

`orderflow-desk/src/shell/main.js:234` projects each closed bar for the POST as
`{t, o, h, l, c, vol, delta, buy, sell, oi, fromTicks}` and drops `ladder`. Line 235 projects `forming` as
`{t, o, h, l, c}`.

**Change.** Both projections gain `ladder: b.ladder`. The doc gains `rowAnchor` beside `rowSize` (`main.js:244`;
`rowAnchor` is detected at `main.js:219` and today reaches only the overlay, `main.js:222`). Nothing else in the
extension changes. `manifest.src.json:4` and `recorder.js:39` `OFD_VERSION` both move `0.2.0 → 0.3.1` (README already
says v0.3.0; the two version fields are brought level in the same edit). `node build.mjs`, then reload at
`chrome://extensions` AND reload the GoCharting tab (HANDOFF.md, "Chrome caches unpacked content scripts").

**Cost, measured.** The extension posts the whole day's closed bars once a second (`main.js:231–234`). A full
5-minute NIFTY day is 75–78 bars carrying 2,200–3,900 ladder rows (`Go charting/NIFTY-I_5m_2026-09-1[1178].ofd.json`,
measured 2026-09-19); at 46 bytes a row that is ~140 KB per POST at 15:30, ~2 ms to parse. The server's cap is 4 MB
and its own comment already budgets "a whole 5m day with ladders is ~1 MB" (`server.py:1170`).
`ponytail:` full-day ladders every post; send only bars past the reply's `have_bars` if it ever costs.

**The ladder's shape, verbatim from the extension** (`adapter.js:88`, `:159`): `[{p, b, s, bt, st}, …]` sorted by
`p` ascending — price at GoCharting's tick precision, buy lots, sell lots, buy trades, sell trades. `b`/`s` are in
**lots** (`adapter.js` `lots()`), as every number the extension emits is; `lot` rides the doc (`main.js:244`).

**`fromTicks` is the honesty tag and already exists.** `true`: the bar was built from every `RECEIEVEDTRADE`
tick (`adapter.js:125–150`). `false`: rebuilt from GoCharting's `FOOTPRINT/V2` snapshot, a coarser re-aggregation
(`session.js:26–27` refuses to overwrite a tick-built bar with one). `partial` bars never reach `closed`
(`session.js:47`). The record keeps the tag; the face shows it (§F).

---

## §C The record — `tape_log.py`

A new module in the shape of `frame_log.py` (`frame_log.py:1–31`): `DIR = os.path.join("data", "tape")`,
`day_path(day, idx) → data/tape/tape_<idx>_<day>.jsonl`, one file per index per day. **Its own file, never
`data/frame/`**: the frame log is the decision record, appended on signature change (`frame_log.py:5–8`); prints are
measurements, appended once per bar, and a reader of either must never have to filter the other out
(`senses.py:13–22` states the rule for `trigger_log.jsonl`; it applies here unchanged).

**`append_closed(doc, day, idx) → int`** — called from the `/api/frame` POST beside
`frame_log.append_if_changed` (`server.py:1191`), before the lock is taken, exactly as that call is.

- **Write-once per bar.** A module-level `_seen: dict[(day, idx) → set[t]]`, seeded from the file the first time a
  `(day, idx)` is touched (streamed line by line — `record_read.py:54–62` is the pattern; a torn last line is
  skipped, never fatal). A bar whose `t` is in the set is not written again. So the every-second re-post writes
  nothing after the first time, and a server restart does not re-append the day.
- **Row = the bar as posted, plus what makes the file self-describing:**
  `{t, o, h, l, c, vol, buy, sell, delta, oi, fromTicks, ladder, rowSize, rowAnchor, lot, session, idx, day}`.
  A bar with no `ladder` key (an extension older than 0.3.1) is written with `ladder: null` — the file records what
  arrived, and the reader says why it is null (§D).
- **The forming bar is never written.** It is served from memory (§D) and discarded; a forming bar's ladder changes
  every tick and a record of it would be a record of nothing (START-HERE.md §6, "never score a forming bar" —
  drawing it is fine, recording it is not).
- **Fail-soft, opened per call, `"a"` mode** — `senses.py:_append` verbatim. A write failure is counted on
  `tape_log.failed` and never reaches the POST reply's `ok`.
- **Anytime-start is free.** The extension replays GoCharting's loaded history when the tab opens
  (`record_read.py:9–12`; `adapter.js:64–112`), so a server started at 11:00 receives 09:15 onward on the next POST.
  Those bars carry `fromTicks: false`; that is the backfill tag, and it was there before this spec.

**Registration (all three, or the change is not done):**
1. `server._isolate_mock_writers` gains `tape_log.DIR = os.path.join(mock, "tape")` (`server.py:2177–2198`).
2. `test_day_state.py:97–98`'s pinned name list gains `"tape_log.DIR"`.
3. `.gitignore` gains `data/tape/` under the `data/senses/` block, with the reason: GoCharting-sourced, ~0.2 MB/day,
   not refetchable from any broker, one forward population, never pooled.

---

## §D The API — `GET /api/tape`

`GET /api/tape?idx=NIFTY&day=YYYY-MM-DD` (both optional; defaults `NIFTY`, today). Added to the `do_GET` chain
beside `/api/frame/bars` (`server.py:2036`). Reply:

```
{ ok, idx, day, interval: 5, rowSize, rowAnchor, lot, tag: "M",
  src: "live" | "file",
  bars: [ { t, o, h, l, c, vol, buy, sell, delta, oi, fromTicks, ladder, cells } ],
  forming: { t, o, h, l, c, ladder, cells } | null,  forming_why,
  profile: { poc, vah, val, nodes: [{p, vol, kind: "HVN"|"LVN"}] } | null,  profile_why,
  ladder_why, why }
```

**Three sentences, never collapsed (CLAUDE.md rule 6):**

| state | `ok` | `src` | how it is decided | what is said |
|---|---|---|---|---|
| the extension is posting | true | `live` | `_SENSES["tape"][idx]` exists (`server.py:1193`), its `doc.session` ends in `day`, and `time.time() − at < 15` — the same boundary the extension uses for the frame (`orderflow-desk/src/shell/main.js:53`, `FRAME_STALE_MS`) | bars from the doc, `forming` from the doc |
| the extension is silent but the day was recorded | true | `file` | no live doc, `tape_log.day_path(day, idx)` exists | bars from the file, `forming: null`, `forming_why: "extension not posting for <n>s — showing the record"` (or `"…since server start"`) |
| neither | false | — | no doc, no file | `why: "no prints record for <idx> on <day> — GoCharting was on another index, or the extension never posted"` |

`ladder_why` is set whenever any served bar has `ladder: null`: `"extension predates ladders (orderflow-desk < 0.3.1)"`.
`profile_why` is set when `profile` is null: `"no bar with a ladder yet"`.

`cells` and `profile` are computed on the way out by `prints.py` (§E) — the server is the brain, the face draws
(`orderflow-desk/docs/2026-09-15-one-tool-map.md` §1). Computed per request from the bars served; a full day is
~3,000 rows and sub-millisecond, so no cache. `ponytail:` recompute per request; memoise on `(day, idx, len(bars),
forming.t, forming.vol)` if a profiler ever names it.

The reply is built from the file by streaming (`record_read.py`'s discipline, `:1–15`): a whole-file `json.load`
on this thread is the thing that wedged the server twice on 2026-09-18.

---

## §E `prints.py` — pure, stdlib, no I/O, no clock

A port of the extension's own arithmetic, function for function, so the two tools cannot disagree about a cell.
Defaults verbatim from `orderflow-desk/src/engine/decode.js:6`: `IMB_RATIO = 3`, `IMB_MIN_LOTS = 5`, `STACK_RUN = 3`.

**`rebin(ladder, row_size, anchor=0.0) → rows`** — `decode.js:12–22`. Row key is
`round((p − anchor) / row_size) * row_size + anchor`, rounded to 4 places; `b, s, bt, st` summed; sorted by `p`.
Sums stay exact.

**`imbalances(rows) → (flags, stacks)`** — `decode.js:25–43`, the convention the four vendors agree on and the
extension already uses: for adjacent rows `dn = rows[i−1]`, `up = rows[i]`, **buy imbalance at `up` when
`up.b ≥ IMB_MIN_LOTS and up.b ≥ IMB_RATIO × max(dn.s, 1)`**; **sell imbalance at `dn` when
`dn.s ≥ IMB_MIN_LOTS and dn.s ≥ IMB_RATIO × max(up.b, 1)`**. The `max(·, 1)` floor is the zero-side rule; it is
the extension's and is kept, not the research brief's `allow_zero=False` — parity with the tool being replaced
wins (§J.1). `flags[i] ∈ {+1, −1, 0}`; a sell flag never overwrites a buy flag on the same row
(`decode.js:30`, `flags[i−1] || −1`). `stacks` = maximal runs of equal non-zero flags with length ≥ `STACK_RUN`,
each `{side, low, high, run}`.

**`bar_cells(bar, row_size, anchor) → cells`** — the per-bar object the face draws:
`{rows: [{p, b, s, bt, st, imb}], stacks, poc, unfinished_high, unfinished_low, delta, vol}`.
`poc` = the row with the largest `b + s` (first on ties — `decode.js:53`, strict `>`). `unfinished_high` =
top **ladder** row (not rebinned — `decode.js:54–58` reads `bar.ladder[-1]`) has `b ≥ m and s ≥ m` where
`m = max(3, vol × 0.02)`; `unfinished_low` likewise on the bottom row. A bar with `ladder: null` gets
`cells: null`.

**`profile(bars) → {poc, vah, val, total, rows} | None`** — `market.js:47–63`, **including its paired-row
expansion**: from the POC, compare the next two rows up against the next two rows down, take the larger pair whole,
until the accumulator reaches 70 % of total; ties go up (`up >= dn`). This is the classic CBOT stepping. The
research brief's single-row Sierra/CQG algorithm gives a slightly different VAH/VAL; the extension's is kept so
Prints and the extension's panel name the same value area (§J.2). Bars with `ladder: null` contribute nothing.

**`nodes(profile) → [{p, vol, kind}]`** — `board.js:192–200` verbatim: bin `profile.rows` into 5-point buckets
(`round(p / 5) × 5`), `med` = median bucket volume (`vals[len >> 1]`, or 1), the top **3** buckets by volume are
`HVN`, any bucket with `vol ≤ 0.35 × med` is `LVN`, everything else is dropped; sorted by `p`.

**Every value is a count of prints and is `[M]`.** `prints.py` emits no tag field because there is nothing
inferred in it; `/api/tape` says `"tag": "M"` once at the top level.

**Parity pin, the test that matters.** A committed file
`test/fixtures/prints_expected_2026-09-11.json`, generated **once** by a checked-in node script
(`tools/gen_prints_expected.mjs`) that imports `orderflow-desk/src/engine/decode.js` and `market.js` and runs
them over `orderflow-desk/test/session-2026-09-11.ofd.json` (77 bars, 7,833 trades; already the fixture
`test_visit.py:16` and `test_frame_zone.py:17` load) at `rowSize = 5, rowAnchor = 0`. `test_prints.py` runs
`prints.py` over the same bars and asserts equality bar by bar: rows, flags, stacks, poc, unfinished flags, and the
session `poc/vah/val/nodes`. If the two ever diverge, the failure names the bar and the field.

---

## §F The Prints tab — `ui-v2/src/prints/`

**The slot.** `Tape` is a fossil: `TapeTab` (`App.tsx:740`) renders Recharts over the mock `KEY_LEVELS` /
`ORDER_FLOW` / `CHART_DATA` (`App.tsx:98`). It becomes **`Prints`**: the `Tab` union (`App.tsx:68`), the `tabs`
array (`:2153`) and the render line (`:2474`) change `'Tape'` → `'Prints'`; `TapeTab` is deleted. The mock inputs
stay — `GlassBoard.tsx` and `data.ts` still reference them and their deletion is parked
(`docs/superpowers/plans/2026-09-18-ui-v2-doctrine-deletions.md`). No other file references `'Tape'` (grep,
2026-09-19).

**Files.**

| file | does | depends on |
|---|---|---|
| `prints/tape.ts` | `useTape(index): {reply, why}` — polls `/api/tape?idx=` every **2 s**, tab-local, first read unconditional, `document.hidden` guard on repeats only — `trade/footprint.ts:60–92` verbatim in shape. Returns the whole reply; computes nothing. | `/api/tape` |
| `prints/PrintsTab.tsx` | the tab: header line (index · `src` · `fromTicks` count · `rowSize`), the chart, the absence sentence when `ok:false`, the `ladder_why` / `forming_why` lines when set | `tape.ts`, `PrintsChart.tsx` |
| `prints/PrintsChart.tsx` | its own candl engine, `createChartEngine(host, {theme, pricePrecision: 2, chartType: 'hollow'})` (`trade/ContractChart.tsx:140` pattern; `'hollow'` is in `CHART_TYPES`, `vendor/candl/chart/types.ts:9`), fed **the reply's own bars** as candles — never `/api/data`'s, so a candle and its cells are one population (§J.3). `setData` on day/index change, `updateLast` for the forming bar (`ContractChart.tsx:224–246` discipline). Mounts `CellsOverlay`. | candl, `CellsOverlay.ts` |
| `prints/CellsOverlay.ts` | the canvas pass — `trade/LevelsOverlay.ts:startLevelsOverlay` in shape: absolute canvas over the host, dpr-sized, `engine.getMainConverters()` and `getMainPaneRect()` re-queried every frame, redraw only when the signature (bars length, forming `t`+`vol`, viewport, mode) changes | candl `Converters` |

**No interval switch on this tab.** The record is 5-minute (`main.js:233` posts `interval` from the chart;
`server.py:1177` refuses anything else). GoCharting is 5-minute. Prints matches it exactly so it can be judged
against it. 3-minute cells arrive with spec 3 (ticks instead of ladders), not here.

**What the overlay draws, per bar, from `bar.cells`** (the cell column spans `timeToX(t)` to `timeToX(t + 300000)`;
a row spans `priceToY(p + rowSize/2)` to `priceToY(p − rowSize/2)`):

- **bid cell** (left half) `s` in `pal.bear`-tinted fill, **ask cell** (right half) `b` in `pal.bull`-tinted fill,
  intensity ∝ the row's share of the bar's largest row; text `s × b` per the LOD ladder below.
- **imbalance**: `imb = −1` → the bid cell in solid `pal.bear`; `imb = +1` → the ask cell in solid `pal.bull`.
- **stacks**: a 1 px outline around the run, `pal.bear`/`pal.bull`.
- **POC row**: a 1 px `pal.accent` rule across the column.
- **unfinished auction**: a short tick outside the column at the bar's high / low.
- **under each bar**, one line: `Δ ±delta · vol` — the `readBar.line` shape (`decode.js:74`), lots, `[M]`.
- **forming bar**: dashed column outline, cells drawn, **never** an imbalance or stack flag (§C, never score a
  forming bar); the `fromTicks: false` bars get a hatched column background, the tag made visible.
- **session**: `profile.poc / vah / val` as full-width lines (`pal.accent`, `pal.textMuted` ×2), `nodes` as faint
  bands (`HVN` `wash(pal.ink, 0.10)`, `LVN` dashed) — the `BAND_RGB` annulus idea from `LevelsOverlay.ts`, one hue.

**Level of detail** (from the renderer verified on 2026-09-19, `awahab07/lightweight-orderflow-charts`
`FootprintSeriesRenderer.ts`, MIT; ported as rules, not code): bar width ≥ 38 px → full `s × b` text;
≥ 20 px → the larger side only; < 20 px → shaded cells, no text. Rows under 3 px are skipped. Font =
`clamp(floor(min(11, barWidth × 0.28)), 7, 11)`, computed **once per frame**, `context.font` set once per pass.
Text is what costs; it is removed before it does.

**Hover.** The overlay hit-tests its own geometry (column from `xToTime`, row from `yToPrice` snapped to
`rowSize`) and draws a pill: `<p> · bid <s> (<st>) · ask <b> (<bt>)`, `pillText` from `trade/hinglish.ts` for the
Hinglish. No engine support needed and none used.

**Absence.** `ok: false` renders the sentence, not a chart — verbatim shape from `trade/footprint.ts:143`:
*"is index ka prints record hi nahi hai — GoCharting kisi aur index par hai, ya extension ne post nahi kiya"*.
`src: "file"` renders the chart **and** `forming_why` in the header. Never an empty pane.

**Drawing tools.** candl's, untouched. The overlay never consumes pointer events except hover (pointer-events:
none; hover reads `mousemove` on the host as `LevelsOverlay` does).

---

## §G Tests

| file | pins |
|---|---|
| `test_tape_log.py` | append writes N rows each carrying `ladder`; the same POST again writes 0; a new module instance seeded from the file writes 0 (restart); a bar without `ladder` is written with `null`; forming is never written; `_isolate_mock_writers` redirects `tape_log.DIR`; the registry pin in `test_day_state.py:89–99` names it |
| `test_prints.py` | the §E parity fixture, bar by bar; hand cases: a one-row ladder (no imbalance possible), `IMB_MIN_LOTS` boundary (4 vs 5), the zero-side floor (`b=15, s=0` → buy imbalance), a stack of exactly `STACK_RUN`, a stack of `STACK_RUN−1` (none), `profile` on two bars, `nodes` top-3 and the `0.35 × med` edge, `ladder: null` → `cells: null` and excluded from `profile` |
| `test_frame_api.py` | the existing `_Req`/`_tape` pattern (`test_frame_api.py:7–24`): a POST with ladders stores them (`_SENSES["tape"]…doc.closed[0].ladder`) and the file has them; `GET /api/tape` live (doc fresh) / file (doc absent, file present) / neither — three replies, three sentences; `ladder_why` set when a bar lacks one |
| `ui-v2` | `npm run typecheck` green. Then a recorded day (`/api/tape?day=2026-09-11` served from a file copied into `data/tape/`) rendered in the browser pane beside `orderflow-desk/test/replay-2026-09-11.html` and GoCharting's own screen. **Not automated** — `ui-v2` has no test runner (`ui-v2/package.json`, no vitest), and adding one is not in this spec. Stated here so it is never read as covered. |

The suite stays green (`python -m pytest -q`, 1062 as of 2026-08-26 per `CLAUDE.md`); the new count goes into
`README.md`, `CLAUDE.md`, `START-HERE.md` and `context/research-findings.md` wherever `**N tests pass**` appears —
`test_docs_claims.py:47–65` fails the suite on purpose otherwise.

---

## §H Docs and registrations, the checklist

- `.gitignore` — `data/tape/` with reason (§C).
- `server._isolate_mock_writers` + `test_day_state.py` pin list (§C).
- `context/HANDOFF.md` — a dated entry: what shipped, the parity fixture's provenance, the done-condition.
- `orderflow-desk/HANDOFF.md` — file map line for `main.js` (ladder + rowAnchor in the POST), version 0.3.1.
- `START-HERE.md` §3 architecture block — one line: `tape_log.py` beside `frame_log.py`; `ui-v2` no longer ABANDONED
  in that diagram (it was restored 2026-09-18, `start-v2.bat:6–9`; the diagram is stale).
- Test counts, all four files (§G).

---

## §I Out of scope, deliberately

| deferred | why | where it goes |
|---|---|---|
| ticks instead of ladders | unlocks 1/3/15-minute cells built server-side; one adapter change (`adapter.js:125` already sees every tick) | spec 3 |
| the Upstox tape and the replacement gate | needs this record running first, to measure against | spec 2 |
| DOM / heatmap / order counts | no GoCharting source; Upstox 5-level + the Kite tap (`paperdesk/v1.21.1/src/ws-tap.js`) | its own design |
| a second interval on Prints | the record is 5-minute until spec 3 | spec 3 |
| memoising `/api/tape` | sub-millisecond today | when a profiler names it |
| sending only un-acked bars | ~140 KB/s over loopback is nothing | when it costs |
| deleting the mock data `TapeTab` read | used by `GlassBoard.tsx`; parked in the doctrine-deletions plan | that plan |
| drawing tools on this tab | candl's 61 are wired nowhere in `ui-v2` yet (`context/HANDOFF.md:1478–1486`) | v3's first chart task |

---

## §J Spec decisions — choices neither source named

1. **Zero-side floor is the extension's `max(·, 1)`, not the research brief's `allow_zero=False`.** The brief argues
   zero cells cluster at bar extremes and over-flag. The extension already lives with this and the operator reads
   its panel. Parity with the tool being replaced is the judging criterion; a different rule would make Prints
   disagree with the extension's own panel on the same bar. Revisit in spec 2 with the comparison data, not here.
2. **Value area is the paired-row expansion (`market.js:55–61`), not single-row.** Same reason. The brief documents
   both; Sierra exposes the choice as a toggle. One value per stack, the extension's.
3. **Candles come from the reply's bars, not `/api/data`.** The server's own bars are Upstox REST 1-minute
   aggregates (`live.build_session`); the extension's are GoCharting's. They differ by a tick or two on some bars.
   A cell column drawn over a candle from a different population would be the σ-band mismatch of §0.4 again, in a
   new place.
4. **`rowAnchor` is posted and used for rebin.** The extension calls it cosmetic (`main.js:219`) because its
   engine's events do not move with it; the face does, and Prints must sit on GoCharting's grid to be compared
   with it. The parity test pins at anchor 0, the extension engine's value, so the pin stays deterministic.
5. **`'hollow'` candles under the cells.** The outline is the price skeleton; a filled body would fight the cells
   for the same pixels. `'bars'` was the alternative; hollow keeps the wick and the open/close readable.
6. **2-second poll.** The POST is once a second; the forming bar's cells change with every tick but a face redrawn
   at 2 s reads as live. `footprint.ts` settled 30 s for a record that changes every ~11 s; this one changes every
   second. A WebSocket from the server is the obvious upgrade and is not built until 2 s is measured as too slow.
7. **Recorded from the POST, not from the extension's IndexedDB export.** The export is a real click
   (`HANDOFF.md`, "scripted clicks are dropped") and evictable; the POST already arrives every second. The record
   must not depend on anyone remembering to click.
8. **The tab is `Prints`, not `Tape`.** `tape` in this repo means the extension's whole document (`_SENSES["tape"]`,
   `frame.py:5`); reusing the word for the cells view would be a third meaning.
