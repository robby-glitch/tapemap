# WAR, compact: design notes (2026-09-24)

Mockup: `war-compact-2026-09-24.html` (self-contained, 645 KB, data embedded, no network).
Generator: `gen_war_compact.py`. It reads the `/api/oihist` and `/api/warmap` payloads saved at
00:47 IST 2026-09-24, while the server still held 2026-09-23, plus `data/chain/chain_<IDX>_2026-09-23.jsonl`
read-only. Every front, state and `broke` comes from `fronts.read` / `fronts.cut` / `fronts.broke`.
For BANKNIFTY and SENSEX the generator asserts that its close view equals the fronts the server
served. Nothing live changed: no edits to `ui-v2/src`, `.py`, the extensions or `data/`, and no restart.

Views: NIFTY / BANKNIFTY / SENSEX × **Live read at 13:36** (the record cut at 13:36, peak OI as the
poller held it then) and **After close**. Dark and light. Hover a row; click the map to pin a cursor.

---

## 1. Layout: what the eye reads first, second, third

```
┌ answer strip ─────────────────────────────────────────────────────┬ meta / hover readout ┐
│ 1  CE 23,400 stopped adding first — 10:15, spot 23,375 — gave back │ NIFTY · 13:36        │
│    39.0L of its 64.1L build; unwinding by §1d since 10:20.         │ spot · ATM · rows    │
│    None of the four top fronts is adding. Then: CE 23,500 13:28 …  │                      │
├ map (982 px) ─────────────────────────────────┬ ladder (206) ┬ rail (328) ─────────────┤
│ 2  strike rows at price, CE lane above the     │ 3 CE │k│ PE  │ 4 cards, in the order    │
│    strike line / PE below, 5-min cells,        │ bar = OI now │   the fronts stopped:    │
│    spot drawn over, ticks at each front's high │ │ = session  │   state · rank · spark   │
│    ◆ stopped  ◇ §1d unwinding (event row)      │ high, boxes  │   stopped HH:MM @ spot   │
│                                                │ = top two    │   → §1d unwinding @ spot │
├ legend (1 line) · provenance (2 lines: record, cadence, feed window, re-baseline, levels) ┤
```

1. **The answer strip** holds one sentence built from the server's `broke`: who stopped adding first,
   when, the spot then, and how much of the build is gone. Under it, the other three fronts in the
   order they stopped, and whether any is still adding. Direction appears only inside that mechanism.
2. **The map** shows where the ground was taken and when, with spot walking through it. Colour gives
   how much is held on one scale for the whole map. Height gives the share of the front's own high
   still held, so a front that is giving back visibly collapses toward its strike line inside the ring
   of its high. Ink ticks mark each top front's high to the minute; a dashed tick marks where §1d first
   read it unwinding.
3. **The ladder** is pinned to the map's right edge ("now") and shares its rows. It is the book as it
   stands: absolute OI now, a tick at the session high, and the server's top two per side boxed and
   numbered. A pinned cursor adds a dashed bar for OI at that minute.
4. **The rail** has four cards, one per front, ordered by when they stopped. Each shows the state word
   plus a geometry glyph, the rank, a session sparkline with the high and the unwind stamp, and the two
   stamps with the spot at each.

Every word stays in the answer strip, the rail, the legend or the provenance line. The map carries only
axis times, strike prices and brass level codes in its gutter.

## 2. Strike window: ±6, a union that follows spot, rows never scroll away

**Rule:** a row exists for every strike that was within ±6 strikes of the ATM at **any** minute of
the record so far. At minute *t*, a cell is drawn only if its strike was within ±6 of *that minute's*
ATM. Otherwise it is **hatched neutral: "outside ±6 of ATM then (not shown)"**, never a zero.

- **Why ±6 and not ±8:** §1d ranks among the 9 strikes nearest spot (±4), so ±6 gives two strikes of
  context each side. The feed subscribes ±8 around the ATM at startup (`STRIKES_EACH_SIDE = 8`) and
  does not re-centre, so ±6 is the widest window that survives two strikes of drift before near-ATM
  cells land on strikes the feed never carried. At ±8 that happens on the first strike of drift.
- **Why a union, not fixed and not a sliding window:** a sliding ±6 moves rows under the eye, and the
  question "where was the wall at 10:15" needs the wall to stay where it was. A fixed window at the
  open drops the strikes spot walked into. With the union, rows are only ever *added at an edge* when
  spot extends the day's range. That is rare, and it is a whole-map shift, never a reorder.
- **Entering and leaving over time** is the hatch: the 23,050 and 23,100 rows on NIFTY 2026-09-23
  switch between hatched and drawn as spot moved (see the 13:36 view).
- **A strike inside ±6 that the feed never carried** is drawn **amber dashed: could not check**.
  Measured on 2026-09-23 by the close: BANKNIFTY 57,200 (404 strike-minutes) and SENSEX
  75,500/75,600 (356).
- **Height:** 22 px per strike (8 px CE lane, 1 px strike line, 8 px PE lane, 5 px gap), capped at
  340 px, so a big trend day thins rows (minimum 12 px) instead of growing the tab.
  NIFTY 2026-09-23: 15 rows, 23,050–23,750, 330 px.

## 3. Space

| | Today (`WarTab.tsx`) | This design |
|---|---|---|
| Plot height | 740 px (`PLOT_H`) | 330 px (NIFTY, 15 rows), max 340 |
| Whole tab at 1600 px width | ≈ 890 px **[I]**: the 1220×820 viewBox scales to ≈ 819 px, plus card and page padding. The rail (300 px wide) runs ≈ 820 px. | **519–523 px [M]** (measured in Chrome for all six views) |
| Fits a 1600×900 laptop? | No. After browser UI, the taskbar, GlanceBar, tab bar and replay bar there are about 575–600 px, so it scrolls. | Yes, with a margin. |

Strikes drawn: all 17–19 that the day ever carried, down to 15 near ATM. The height saved is about 40%;
the plot is 55% shorter.

## 4. Time resolution (checked, as asked)

**No, the minutes do not step every ~3 min on NSE. They do on BSE.** Near-ATM legs (§1d's 9 strikes,
both sides, whole session) **[M]**:

| Index | Minute-to-minute reads that changed | Minutes between changes |
|---|---|---|
| NIFTY | 6,509 / 6,732 = **97%** | 1 min: 6,288 · 2: 201 · 3: 2 |
| BANKNIFTY | 6,282 / 6,732 = **93%** | 1: 5,847 · 2: 391 · 3: 21 · 4–5: 5 |
| SENSEX (BSE) | 2,500 / 6,732 = **37%** | 2: 755 · **3: 1,725** · 5–6: 2 |

In the 10-second NIFTY log, OI changes land 50–70 s apart. So NIFTY and BANKNIFTY stamps are good to
**±1 min** and SENSEX stamps to **±3 min**. The design prints this per index: `±1m` / `±3m` on every
rail stamp, in the legend, and in the provenance line. It is read from the measured cadence, not
hard-coded. Quant Tower's "every 3 minutes" holds for BSE only.

## 5. Every element → source field

| Element | Source | Tag |
|---|---|---|
| Cell colour (√ scale, one scale per map; full = largest near-ATM `k` drawn) | `/api/oihist` `minutes[t].k[strike][0/1]` | [M] |
| Cell height = share of its own high still held | same series, running max computed on the client (geometry, not a rule) | [M] |
| Ring (strength = brightness of the high × share gone) | same | [M] |
| Hatched hue = below its own open | `k < 0` | [M] |
| Hatched neutral = outside ±6 of ATM then | `minutes[t].spot` → ATM(t) = spot rounded to the strike step | [M] |
| Amber dashed = could not check | strike missing from `minutes[t].k` while within ±6; minute gaps > 5 (`GAP`) | [M] |
| Lighter cell = rebuilt minute | `minutes[t].src == "backfill"` / `backfill_marks` (weight × 0.45, same hue) | [M] |
| Spot line | `minutes[t].spot`, broken on holes | [M] |
| Front rows, ranks, boxes, state word, "FIRST" | `/api/oihist` `fronts[]` (`k, side, oi, chg, peak, peak_at, from_peak, slope, state`), `broke`, `fronts_why` | [M] (server tags rows M; the state is §1d's rule applied to measured series) |
| High tick + ◆ time | `fronts[].peak_at` | [M] ±1/±3 min |
| Spot at the high | `minutes[peak_at].spot` (a lookup, not a rule) | [M] |
| Dashed tick, ◇ and "→ §1d: unwinding HH:MM @ spot" | **new** `fronts[].unwind_at`, the first §1d UNWINDING after `peak_at` (see wiring 6) | [M] by rule |
| Ladder bar = OI now | `/api/warmap` `indices[idx].heat[].ce_oi / pe_oi` (already fetched by WarTab for levels) | [M] |
| Ladder tick = session high | `/api/oihist` `peak[]` (absolute OI, **no time**; drawn only on the ladder, never blended into `k`) | [M] |
| Ladder dashed = OI at cursor | **new** absolute OI per minute (wiring 7) | [M] |
| Ladder shading = the strikes §1d ranks among | **new** `near` (wiring 5) | [M] |
| Brass levels (OPEN, PDH, PDL, PDC, PWH, PWL) | `/api/warmap` `indices[idx].levels[]` (ROUND is dropped because every row is a round strike; walls and max pain are dropped because the ladder shows the book) | [M] |
| Re-baseline warning | **new** server mark (wiring 8); in the mockup, measured from the chain log | [M] |

What is deliberately **not** on WAR: the engine's verdict (CAUTION/GO), rupee flow, PCR, max pain,
build-up colours, hit rates and scores.

## 6. The two frozen moments, as the screen reads them

- **NIFTY 13:36 live.** CE 23,400 stopped first (10:15 @ 23,375) and has given back 39.0L of 64.1L;
  §1d has read it unwinding since 10:20. None of the four top fronts is adding: CE 23,500 stopped
  13:28, PE 23,400 13:31 @ 23,435 (6.1L off its 127.0L high), PE 23,300 13:34. At 13:36 §1d says PE
  23,400 is **STALLED, not unwinding**: 4.8% off its high, and its slope of −4.8L sits inside the 5% band of 6.3L. It first
  reads UNWINDING at **13:37 @ 23,426**, one minute later. The screen says exactly that. It does not
  round "stalled" up to "unwinding" because the eye sees a drop. This was the minute the engine said
  CAUTION. WAR does not show the engine; it shows that both sides' biggest near-ATM fronts had
  stopped adding.
- **NIFTY after close** is drawn to **15:26** only; see §8. CE 23,400 has given back 50.8L of 64.1L.
  PE 23,400 has been unwinding since 13:37 and is 49.4L off its high. PE 23,300 has been unwinding
  since 13:47, and CE 23,500 stopped at 14:08 and has been unwinding since 14:20.
- **CE 23,500 at 13:36** shows STALLED with "→ §1d: unwinding 13:32". §1d flickered UNWINDING at
  13:32 and back to STALLED. The stamp is the *first* unwinding read after the high, and the word is
  the state *now*. Both are the server's. The stamp never flickers and no debounce is invented.

## 7. What changes, smallest first

**UI only (`ui-v2/src/war/WarTab.tsx`), no server change:**

1. Consume `fronts`, `fronts_why` and `broke` from `/api/oihist` (already served). **Delete the
   `ranked` sort** (line 363), which ranks by peak *change* and is the wrong rule (§1d ranks by
   session-high absolute OI). The answer strip, rail cards, row marks and ladder boxes are all built
   from `fronts`. If `fronts` is null, print `fronts_why` as "could not check", never "no fronts".
2. Replace the bands with cells. Rows come from the ±6 union; add the per-minute `near()` hatch and
   the not-carried amber. Set `PLOT_H = rows × 22 ≤ 340`; cells are 5-min × 12 px, colour √(k/vmax),
   height k/runmax. Keep `GAP = 5` holes, the session axis 09:15–15:30 and backfill weight (four facts
   kept).
3. Add the ladder: `heat[].ce_oi/pe_oi` from the `/api/warmap` response WarTab already fetches, and
   `peak[]` for the tick.
4. Put the hover readout in the answer strip's meta column. Click-to-pin cursor is local state.
   Everything else on the page stays.

**Server (each optional; without it the element is omitted, never recomputed in TypeScript):**

5. `near`: the strikes `fronts.read` ranked among. One field in the `/api/oihist` reply, or have
   `read` return it. It drives the ladder shading.
6. `unwind_at` per front: a `fronts.since(minutes, k, side)` helper that rolls `_state` once over the
   front's own series (about 15 lines, O(n)). `frame.py` and `trigger_log.py` could stamp it too. It
   drives the dashed tick, the ◇ and the "→ §1d" line.
7. Absolute OI per minute (`oi` beside `k` in `ChainState.minutes` and `chain_backfill`) enables the
   cursor-time ladder. It costs about +50% payload (~350 → ~520 KB per index).
8. **A defect found while designing, separate from WAR.** A restart re-reads the 09:15 OI baselines,
   and on 2026-09-23 they came back different. NIFTY's restart at 15:27 moved the baseline of
   **11 of 38 legs, by up to 8.66L** (CE 23,400 +8.66L, PE 23,350 +8.18L). So `k` jumps with no
   trade behind it: CE 23,400 went 13.3L → 4.1L between 15:26 and 15:27. The server's own close read
   carries this: its "UNWINDING" slope for CE 23,400 includes 8.66L of re-baseline. BANKNIFTY and
   SENSEX were not affected. Root-cause fix: persist the baselines in `day_state` so a restart reuses
   them. Until then, stamp `rebased` marks like `backfill_marks`, and WAR draws those minutes amber
   ("could not check"). The mockup's NIFTY close is drawn to 15:26 for this reason.

A caveat that is not a change: `fronts.read` treats a strike missing from a minute as a real 0.0. On a
day when a restart re-centres the subscription window, missing means "not carried", not zero. It was
harmless on 2026-09-23 because those strikes were outside the nine.

## 8. Decisions, one line each

- **Colour for magnitude, height for give-back.** Colour ranks walls across strikes. Length, the more
  precise channel, carries the one fraction §1d is built on: how much of its own high is gone.
- **√ colour scale, one scale per map.** It keeps zero, order and cross-strike comparison, and stops a
  127L front from washing out every 30L front. Exact numbers live in the rail.
- **5-minute cells, minute-exact ticks.** The bin only paints; the stamp never moves into the bin.
- **Ticks and names only for the server's four fronts, plus the hovered row.** Thirty anonymous
  ticks is how the previous map became unreadable.
- **The ring's strength scales with the share given back.** A 2% dip leaves no visible ring and a
  ruin keeps its walls, with no threshold invented in the UI.
- **Rail ordered by when each front stopped.** The order is the sequence she reads, so the first card
  answers "who stopped first".
- **The session axis stays full width in a live read.** It gives the same geometry at 09:15, 13:36 or
  after a restart, so the anytime-start rule holds.
- **The ladder shows absolute OI and the map shows change.** They are different units, so they sit on
  different panels and are never blended (fact 2).
- **Per-index ±1m / ±3m.** SENSEX OI really does arrive every ~3 min; an unqualified SENSEX stamp
  would overstate precision.
- **No engine verdict on WAR.** WAR is the OI record; the engine's word lives elsewhere.

## 9. Questions that would change her method (not presentation)

1. **Do the fronts read the ±4 she used to see, or the ±6 she now sees?** §1d's `NEAR = 9` (±4) is
   pre-registered. At BANKNIFTY 13:36 the largest CE build on screen (57,000, 13.4L at 13:36) sits outside
   the nine and is not boxed. The shading shows why. Widening it is her call, logged forward, not a
   UI change.
2. **Should "unwinding" require persistence?** §1d's state flips STALLED↔UNWINDING minute to minute
   (CE 23,500 at 13:32 → 13:36). The design shows only the first unwinding read after the high. If
   she wants the rule itself to require N minutes, that is a §1d parameter.
