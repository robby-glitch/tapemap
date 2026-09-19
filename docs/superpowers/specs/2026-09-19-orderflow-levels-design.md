# Order-flow levels and marks on the Trade chart — from GoCharting's ladder, with a second opinion

**Date:** 2026-09-19 · **Status:** specification, nothing built yet · **Branch:** `feature/operator-objects`
**Supersedes:** `2026-09-19-prints-design.md` (§B–§E of it carry over verbatim; its §F cells chart is dropped).
**Sources:** the operator's rulings of 2026-09-19 — no cells chart; *absorption, exhaustion, HVN/LVN, POC/VAH/VAL,
naked POC, stacked imbalance, unfinished auction, delta and CVD* **on the existing candle chart**; doubt that the
extension's absorption/exhaustion/climax detection is correct; and *"look first, decide later"* as the way to
settle that doubt. Plus the four research briefs of 2026-09-19 and both codebases read in full. Every claim about
existing code carries a file:line; every chosen value is logged in §J.

**Read first:** `START-HERE.md` §0, `CLAUDE.md` rules 4–7 and 9, `context/research-findings.md` §5 (the
pre-registration rule), and `C:\Users\kaam\Desktop\Go charting\orderflow-desk\docs\BRIEF-for-the-builder.md` §0.
Paths written `orderflow-desk/...` are under that folder. **The extension's reading layer is protected and this
spec changes none of it** — it adds one field to a projection and reads what the extension already sends.

---

## §A Purpose and boundary

**What ships.** On the Trade tab (`ui-v2/src/trade/`), drawn by the overlay it already has:

| the operator asked for | source | drawn as | tag |
|---|---|---|---|
| HVN / LVN | the day's ladders | faint band / dashed band across the chart | `[M]` |
| session POC, VAH, VAL | the day's ladders | horizontal lines | `[M]` |
| prior-day POC, VAH, VAL and **naked POC**s | prior days' ladders from the record | lines; a naked POC ends where price first touches it | `[M]` |
| stacked imbalance, unfinished auction | each bar's ladder | small marks at the bar's own time and price | `[M]` |
| delta per bar, CVD | each bar's ladder | a candl indicator pane under the candles | `[M]` |
| **a second opinion** on absorption / exhaustion / climax | each bar's ladder, vendor-standard definitions | hollow glyphs beside the extension's filled A / E / C — **never merged** | `[I]` |

**What does not ship.** No new tab, no cells chart, no change to the extension's detectors, **no scoring yet**
(§K), no Upstox-derived anything (spec 2), no hit rate ever (CLAUDE.md rule 4).

**Already there, untouched.** The extension's four marks — A absorption, E exhaustion, P trap, C climax — are on
the Trade chart today (`trade/TradeTab.tsx:428, :953, :1016`; glyphs at `trade/LevelsOverlay.ts:1051–1133`),
coloured by side since `f97f876`. This spec adds beside them; it does not replace or restyle them.

**The doubt, and how it is settled.** The extension's rules are explicit (`orderflow-desk/src/engine/board.js:68–100`,
`:103–115`): a "big" one-sided cluster is one ranking in the top 20 % of the session's clusters so far; absorption
is such a cluster the bar closed past, or a bar with ≥ 25 % net one-way volume that moved < 30 % of a median
range; exhaustion is a new leg extreme on ≤ 60 % of the leg's strongest delta; climax is ≥ 3× median volume with
both sides ≥ 35 %. These are one author's definitions with no ground truth — Sierra, ATAS and Bookmap each define
absorption differently (research brief, algorithms §7). So the tool draws **two independent readings** from the
same prints and the operator looks at both for five sessions. Then, and only then, she states the pass bar and
scoring is pre-registered (§K). Nothing in this spec decides which family is right.

**Two populations, one word.** `ui-v2/src/trade/footprint.ts` is the extension's event record and stays so. The
new server-side detections are the **`tm` family**; the extension's are the **`ofd` family**; every mark carries
`src`. Levels computed from ladders arrive under their own `levels` object on `/api/tape` (amended 2026-09-19 at the
final review: there is no `src` field — the object is the population) so they are never confused with the OI walls
(`_WALL_KINDS`, `frame.py:56`) or the pivot-derived PDH/PDL/PDC (`structure.py:320`).

---

## §B The wire — one extension change (carried over from the Prints spec §B)

`orderflow-desk/src/shell/main.js:234–235`: the closed-bar and forming-bar projections gain `ladder: b.ladder`;
the doc gains `rowAnchor` beside `rowSize` (`:244`; detected at `:219`). Version `0.2.0 → 0.3.1` in
`manifest.src.json:4` and `recorder.js:39`. `node build.mjs`, reload at `chrome://extensions`, reload the
GoCharting tab. Cost measured at ~140 KB per one-second POST at 15:30, ~2 ms to parse, under the 4 MB cap the
server already budgets for "a whole 5m day with ladders" (`server.py:1170`).

**Events need no change.** `board()` accumulates every bar's detections for the whole session
(`board.js:162–187`, `events.push(...)` per bar, then `exhaustion(bars)`), and `main.js:203` posts them all each
second. Each is `{t, kind, side, p, size}`; `side` is present since the extension's 2026-09-19 build.

`fromTicks` stays the honesty tag: `true` built from every tick, `false` rebuilt from GoCharting's coarser
snapshot (`session.js:26–27`).

---

## §C The record — `tape_log.py` (carried over, plus the marks file)

Shape of `frame_log.py` (`:1–31`): `DIR = data/tape`, fail-soft append opened per call (`senses.py:_append`),
seeded seen-sets so a restart never re-appends, forming bar never written. Two files per index per day — two
populations, two files, never one:

- **`data/tape/tape_<idx>_<day>.jsonl`** — one row per **closed bar**, write-once by `t`:
  `{t, o, h, l, c, vol, buy, sell, delta, oi, fromTicks, ladder, rowSize, rowAnchor, lot, session, idx, day}`.
  Measurements. The prior-day levels of §E read these files for earlier days.
- **`data/tape/ofd_marks_<idx>_<day>.jsonl`** — one row per **extension mark**, write-once by `(t, kind, p, side)`:
  `{t, kind, side, p, size, src: "ofd", idx, day}`. Today these marks survive only inside `data/frame/` rows
  (the last four per frame, `frame.py:356`) and are recovered by de-duplication (`record_read.py:65–75`); a
  scorer needs each mark once, with its bar. This file is that. **The `tm` family is not recorded** — it is a pure
  function of the bar file and recomputes byte-identically; recording a derivation beside a measurement is how
  `vpin_backfill` had to be split from `vpin_log` (`.gitignore:30–34`).

`append(doc, day, idx)` is called from the `/api/frame` POST beside `frame_log.append_if_changed`
(`server.py:1191`), before the lock. Registration: `_isolate_mock_writers` gains `tape_log.DIR`
(`server.py:2177–2198`); `test_day_state.py:97–98` pins the name; `.gitignore` gains `data/tape/` with the reason
(GoCharting-sourced, ~0.3 MB/day, not refetchable from any broker, two forward populations in their own files).
Anytime-start is free: the extension replays GoCharting's loaded history on tab open (`record_read.py:9–12`).

---

## §D The API — `GET /api/tape?idx=NIFTY&day=YYYY-MM-DD`

Beside `/api/frame/bars` in `do_GET` (`server.py:2036`). Built from the live doc when the extension posted within
15 s (`_SENSES["tape"][idx]`, `server.py:1193`; `FRAME_STALE_MS`, `orderflow-desk/src/shell/main.js:53`), else
streamed from the files (`record_read.py:1–15` discipline — never a whole-file `json.load` on a handler thread).

```
{ ok, idx, day, interval: 5, rowSize, rowAnchor, lot, src: "live"|"file",
  bars:   [ { t, o, h, l, c, vol, buy, sell, delta, cvd, fromTicks,
              stacks: [{side, low, high, run}], unfinished_high, unfinished_low } ],   // [M]
  levels: { session: {poc, vah, val} | null, prior: [{day, poc, vah, val}], naked: [{day, poc, touched_t|null}],
            nodes: [{p, vol, kind: "HVN"|"LVN"}], tag: "M", why },
  marks:  { ofd: [{t, kind, side, p, size, src:"ofd"}],           // as posted, [I], the extension's
            tm:  [{t, kind, side, p, size, why, src:"tm"}] },     // §E, [I], this server's
  ladder_why, forming_why, why }
```

Three sentences (CLAUDE.md rule 6): `src: "live"` · `src: "file"` with `forming_why: "extension not posting for
<n>s — showing the record"` · `ok: false, why: "no prints record for <idx> on <day> — GoCharting was on another
index, or the extension never posted"`. `ladder_why` is set when any bar lacks a ladder (extension < 0.3.1);
`levels.why` when fewer than one ladder-bearing bar exists. `prior` and `naked` are empty with `why` on the first
recorded day — *"no earlier day in the record yet"*, never an empty list without a sentence.
**Amended 2026-09-19 at the final review:** `marks.ofd_why` is `null` whenever `marks.ofd` is non-empty; when it's
empty, which sentence fires depends on the branch, not just on file existence — `src: "live"` has no marks file to
check at all, so it gets its own sentence: `"the extension has detected nothing yet today"`. On `src: "file"`:
`"no marks file for <idx> on <day> — the record was seeded from an export, which carries none"` when no marks file
exists for the day, else `"the extension detected nothing on this day"` — because "no file" and "nothing detected"
are the two sentences rule 6 keeps apart, and §K's scorer reads this field (three facts, three sentences — the
re-review caught the live case). And the served `bars[]` and `forming` do **not**
carry `ladder`: it was 81 % of the reply's bytes with no consumer; the ladder stays in the record, which is its
point. `ladder_why` tests for a missing OR empty ladder (`not b.get("ladder")`), since extension 0.3.1 posts `[]`
for a bar without one.

Computed per request by `prints.py`; ~3,000 rows a day, sub-millisecond. `ponytail:` no cache until a profiler names it.

---

## §E `prints.py` — pure, stdlib, no I/O, no clock

**Carried over verbatim from the Prints spec §E**, parity-pinned bar by bar against `decode.js`/`market.js`/`board.js`
over `orderflow-desk/test/session-2026-09-11.ofd.json` via a committed expected-output file generated once by
`tools/gen_prints_expected.mjs`: `rebin` (`decode.js:12–22`), `imbalances` → flags and `stacks`
(`decode.js:25–43`, ratio 3, min 5 lots, run 3, the `max(·,1)` zero floor), `unfinished_high/low`
(`decode.js:54–58`, floor `max(3, 2 % of vol)` on the raw ladder's extreme rows), per-bar `poc`, `profile`
(`market.js:47–63`, the paired-row 70 % expansion), `nodes` (`board.js:192–200`, 5-point bins, top 3 = HVN,
≤ 0.35 × median = LVN). The per-bar cells themselves are computed but **not served** — nothing draws them.

**New in this spec:**

- **`delta`** = `buy − sell` per bar as posted (lots). **`cvd`** = running sum of `delta` over the day's closed
  bars in time order, **anchored at the session open and reset daily** (§J.1). Both `[M]`.
- **`prior_levels(days)`** — `profile()` over each of the last **5** recorded days (`market.js:priors(k, 5)`, the
  extension's own depth), newest first; each gives `{day, poc, vah, val}`.
- **`naked(days, today_bars)`** — a prior day's POC is naked until a **later** bar's `[l, h]` straddles it
  (`market.js:75`, the extension's rule: one touch by range, a wick counts). `touched_t` is the first such bar's `t`,
  or null. Gap-overs are left as the extension leaves them (§J.2).
- **The `tm` family** — three detectors from the vendor-standard definitions in the algorithms brief, each
  self-calibrated on the session so far in the project's own style (`README.md` Principles: *"No absolute
  price/size thresholds… percentile-so-far"*), each with a one-sentence `why` in the extension's voice:

  | kind | rule (per closed bar `b`, session-so-far percentiles `pct(·)`) | side |
  |---|---|---|
  | `absorption` (Sierra effort-vs-result, brief §7.3) | `pct(\|delta\|) ≥ 0.75` **and** `pct(h − l) ≤ 0.50` **and** the close disagrees with the delta: `delta > 0 and c ≤ o`, or `delta < 0 and c ≥ o` | `−sign(delta)` (the side that absorbed), at `h` when delta > 0, `l` when < 0 |
  | `exhaustion` (ATAS delta divergence at a new extreme, brief §6.5, sign only) | `h > max(h)` of the previous **6** bars **and** `delta ≤ 0` → bearish; `l < min(l)` of the previous 6 **and** `delta ≥ 0` → bullish | `−1` at `h` / `+1` at `l` |
  | `climax` (volume-shape, brief §7.5) | `pct(vol) ≥ 0.90` **and** `\|delta\| / vol ≤ 0.15` | `0`, at `h` if `c > (h+l)/2` else `l` |

  **`pct(x)` is the fraction of prior bars STRICTLY below `x`** — not `board.js rankIn`'s `<=`. Amended
  2026-09-19 during implementation: with `<=`, every bar of a constant-volume series ranks 1.0 and the climax
  rule fires on every quiet bar; with strict-below a tie ranks 0, a spike ranks 1.0, and a bar tying an earlier
  maximum still ranks ≥ 0.9 and fires. The thresholds themselves are unchanged.
  Percentiles need `MIN_N = 6` prior bars (`board.js:19`, the same floor); earlier bars fire nothing and the
  reply says so once (`marks.tm_why: "first six bars: nothing to rank against"`). The `0.75 / 0.50 / 0.90 / 0.15 /
  6` are §J.3, stated once and pinned by test; they are not tuned in this spec and must not be tuned before §K.

- **Every number is tagged** (CLAUDE.md rule 7): counts and profiles `[M]`; both mark families `[I]` — a definition
  applied to prints is an inference, whoever wrote the definition.

---

## §F Drawing — the Trade tab, existing seams only

**Poll.** `trade/tape.ts` → `useTape(index)`: `/api/tape?idx=`, **30 s**, tab-local, first read unconditional,
`document.hidden` guard on repeats — `trade/footprint.ts:60–92` in shape. Levels move once per 5-minute bar; 30 s is
the cadence that endpoint family already settled on (`footprint.ts:47–57`).

**Props and getters.** `TradeTab` passes `prints={tape.reply}` beside `marks={footprint.events}` (`TradeTab.tsx:953`);
`ContractChart` forwards it; `startLevelsOverlay` gains `getPrints()` beside `getMarks()`
(`LevelsOverlay.ts:startLevelsOverlay`). Null draws nothing; TradeTab prints the reply's `why` in the legend line
under the chart, beside the existing marks sentence (`TradeTab.tsx:1016–1030`).

**Levels** (the PDH/PDL/PDC pass at `LevelsOverlay.ts:666–686` is the pattern — a line and a right-edge label):
session POC `pal.accent` dashed; VAH / VAL `pal.textMuted` dashed; prior-day POC/VAH/VAL the same, fainter, labelled
with the day; naked POC `pal.accent` thin, drawn from its day's first bar to `touched_t` or the right edge; HVN
`wash(pal.ink, 0.10)` band, LVN dashed outline — the `BAND_RGB` annulus idea, one hue. Levels are prices; **they
draw at any chart interval.**

**Per-bar marks** (`[M]`): a stack is a 1 px bracket on the bar's price span `[low, high]` in the side's colour; an
unfinished auction is a 3 px tick just outside the bar's high or low. Placed by the bar's own `t` and prices via
`timeToX`/`priceToY`, **never snapped to a candle** — the rule `footprint.ts:21–27` already states for marks, so a
5-minute mark sits correctly on a 3-minute chart.

**The `tm` family**: the same four shapes as the `ofd` family (`LevelsOverlay.ts:1051–1060` — shelf, chevron,
diamond) but **stroke only, no fill, lowercase letter** `a` / `e` / `c`, drawn in a second pass on the opposite side
of the bar so neither family's de-overlap pool (`MARK_PRIO`, `:1104`) ever touches the other's. Hover on either
family shows its `why` (the extension's marks carry none — the tooltip says so rather than inventing one).

**Delta and CVD** ride candl's own indicator path, not the overlay: `trade/indicators.ts:buildIndicators` gains a
`placement: 'pane'` entry (`vendor/candl/indicators/types.ts:4`) with two outputs, `delta` (histogram if candl's
`PlotStyle` has one, else a line, coloured by sign) and `cvd` (line, `pal.ink`), values aligned 1:1 with the chart's
bars. **Only when the Trade tab's interval is 5 or 15** (`live.INTERVALS`, `live.py:932`): the record is 5-minute,
15 sums exactly, 3 and 1 do not divide it. At 3 or 1 the pane is absent and the legend says *"delta 5-min record se
hai — is chart ke <n>-min bars se nahi jud sakta; 5 ya 15 par dekho"* — the third sentence, never a misaligned pane.

**Nothing on the Trade tab prints a direction verdict from any of this** (parked-deletions plan,
`docs/superpowers/plans/2026-09-18-ui-v2-doctrine-deletions.md`): a level is a level, a mark is a mark, CVD is a line.

---

## §G Tests

| file | pins |
|---|---|
| `test_tape_log.py` | bars write-once by `t`; marks write-once by `(t, kind, p, side)`; re-POST writes 0; restart seeds from both files; forming never written; a bar without `ladder` → `ladder: null`; `_isolate_mock_writers` redirects `tape_log.DIR` and `test_day_state.py:89–99` names it |
| `test_prints.py` | the §E parity fixture bar by bar (rows, flags, stacks, unfinished, poc, profile, nodes); `cvd` is the prefix sum and resets across days; `prior_levels` on two synthetic days; `naked` touched by a wick, untouched, and gap-over-left-naked; the three `tm` detectors — each fires on a hand-built bar that meets its rule and stays silent on one that misses by one percentile step; the first six bars fire nothing and say why; `tm` output is identical on two calls (pure) |
| `test_frame_api.py` | a POST with ladders and events lands both files; `GET /api/tape` live / file / neither — three replies, three sentences; `ladder_why`, `levels.why`, `prior.why` on a first day; `tag` fields present and never `"M"` on a `tm` mark |
| `ui-v2` | `npm run typecheck` green; then a recorded day served from files (`data/tape/` seeded from `orderflow-desk/test/session-2026-09-11.ofd.json` through a one-off `tools/seed_tape_from_ofd.py`) rendered in the browser pane at 5 min and at 3 min: levels and marks present at both, the delta pane present only at 5. **Not automated** — `ui-v2` has no test runner; stated so it is never read as covered. |

Suite stays green; counts bumped in `README.md`, `CLAUDE.md`, `START-HERE.md`, `context/research-findings.md`
(`test_docs_claims.py:47–65`).

---

## §H Docs and registrations

`.gitignore` (§C) · `_isolate_mock_writers` + pin list (§C) · `context/HANDOFF.md` dated entry (what shipped, the
parity fixture's provenance, the five-session look, the bar still owed) · `orderflow-desk/HANDOFF.md` file-map line
for `main.js` and version 0.3.1 · `START-HERE.md` §3: `tape_log.py` beside `frame_log.py`, and `ui-v2` no longer
ABANDONED in the diagram (restored 2026-09-18, `start-v2.bat:6–9`) · test counts (§G) ·
`context/research-findings.md`: **nothing** — no result exists to record, and §K's pre-registration is the
operator's to write, not this spec's.

---

## §I Out of scope, deliberately

| deferred | why | where |
|---|---|---|
| the scorer for both mark families | the bar is owed by the operator after five sessions of looking (§K); building the scorer first invites reading numbers before the bar is stated | after §K |
| Bookmap's per-level adaptive absorption | a second `tm` absorption rule is a second thing to look at before the first has been looked at | when §K asks for it |
| the Upstox-derived family and the replacement gate | needs this record running first | spec 2 |
| ticks instead of ladders (1/3-minute delta) | one adapter change; nothing here needs it | spec 3 |
| a cells / footprint chart | the operator does not want one | dropped |
| touching `board.js` / `read.js` | protected (`BRIEF-for-the-builder.md` §0) | never in this line |
| tuning `0.75 / 0.50 / 0.90 / 0.15 / 6` | tuning before a bar is stated is the §5 stop rule's exact target | after §K, pre-registered |

---

## §J Spec decisions — choices neither source named

1. **CVD anchors at the session open and resets daily.** The brief records no cross-platform default (Sierra toggles
   it, TradingView anchors, Quantower rolls). This stack's own rule for percentiles — *"a percentile is only honest
   over ONE population"* (`context/HANDOFF.md`, VPIN entry) — says the same of a cumulative: yesterday's delta is a
   different population. Daily.
2. **Naked POC test = a bar's range straddles it, wick counts** — the extension's own rule (`market.js:75`), so the
   two tools agree on which POCs are naked. Gap-overs stay naked; that is what the extension does and what the
   operator is comparing against. Revisit with the record, not before.
3. **`tm` thresholds as percentiles: absorption `≥ 0.75` |delta| and `≤ 0.50` range; climax `≥ 0.90` vol and
   `≤ 0.15` lopsidedness; exhaustion over the previous 6 bars.** The brief gives Sierra's worked example as absolute
   contracts (150 on ES) and ATAS's windows in minutes (30 min ≈ 6 five-minute bars). Absolute lot counts violate
   the README principle; percentile-so-far is how every threshold in `board.js` is already expressed. The exact
   quantiles are round numbers stated once, pinned by test, and **not tuned** until §K.
4. **Only the three doubted kinds get a `tm` reading.** Trap and vacuum were not doubted and have no clean vendor
   definition; the unfinished-auction flag uses the extension's rule (parity) rather than ATAS's strict zero, because
   it is drawn as a `[M]` bar flag, not as a competing opinion.
5. **Delta pane only at 5 and 15 minutes.** A 5-minute quantity cannot be honestly split onto 3-minute bars; a pane
   that was silently wrong at 3 minutes is the §0.4 σ-band problem again. Absent with a sentence.
6. **The `tm` glyphs are hollow versions of the `ofd` glyphs, not new shapes.** She reads the four shapes fluently
   (`LevelsOverlay.ts:1053`); the question is *do the two families agree*, and the fastest read of agreement is the
   same shape twice — one filled, one hollow — on the same bar.
7. **Marks are recorded once each in their own file; `tm` marks are not recorded.** Measurement vs derivation, the
   `vpin_log` / `vpin_backfill` split.

---

## §K The look, then the bar — the operator's, in order

1. Five live sessions with everything in §A drawn. She compares both families against what she sees on GoCharting.
   Nothing is scored; no number is printed.
2. She states, in `context/research-findings.md` as a **pre-registered** section (§5's rule): what a correct mark
   means — the horizon (in bars), the excursion direction, and the margin over the unconditional control — and
   whether the two families are judged separately or as agreement.
3. Only then is a scorer written, in the shape of `score_frame.py` (`_fill_tap`, `HORIZ_BARS = (1, 3, 6)`, the
   control), over `data/tape/ofd_marks_*.jsonl` and the recomputed `tm` marks, filling forward cells once.
   `trigger_log.py`'s refusal to print a rate applies to it unchanged.
4. Kill condition, declared now: a family whose marks, at n ≥ 30 per kind, do not beat the unconditional control at
   the stated horizon by the stated margin is drawn faint and then removed — the `frame.py:19–26` form.

The one thing this spec must not do is answer step 2 for her.
