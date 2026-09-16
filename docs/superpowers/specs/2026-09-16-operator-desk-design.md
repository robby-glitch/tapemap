# Operator Desk — design specification

**Date:** 2026-09-16 · **Status:** specification, nothing built yet · **Branch:** `feature/operator-objects` **Sources:** the lead's rulings
R0–R8 (binding), the trader/designer brief (adopted where not overruled), the server inventory of 2026-09-16 (ground truth). **Serving:**
`ui/desk/index.html` at `http://127.0.0.1:8765/desk/` through the existing static fallthrough (server.py:1922-1923; `directory=ROOT/"ui"` at
server.py:994). No framework, no build step, ES modules, same-origin fetch. Every claim about existing code carries a file:line; where a
value had to be chosen and neither source named it, the choice is logged in §M as a spec decision.

## §A Purpose and boundary

The chart tab — GoCharting plus the 400 px extension panel and the chart overlay — owns the edge, right now, one index. This desk owns four
things that tab structurally cannot:

| this desk owns | why the chart tab cannot |
|---|---|
| **TIME** | the panel has no x axis; the chart has no strike axis |
| **MONEY** | the panel has no book, no margin, no theta bill |
| **MORE THAN ONE INDEX** | one tab is one symbol |
| **HEALTH** | on 2026-09-16 the tool went blind at 09:51 and she learned it after the session |

**Must NOT render — the face already draws it** (inventory §8, last paragraph): the σ gauge (panel.js:124); the wall ladder around price
(panel.js:278-291); the tape event list (panel.js:294-300); the setup conjunction / WAITING FOR block (panel.js:303-312); the coverage line
(panel.js:315-319); any chart-shaped view of walls, levels, marks or bands (overlay.js:105+). **Must NOT render — doctrine exclusions**
(brief §A, last paragraph): live flashing MTM; aggregate OI, PCR or max-pain as a signal (max pain may appear as a grey level tick on the
price axis, never as a number with a verdict); India VIX as a headline; a chain dump; probability of profit; payoff diagrams; win rates or
hit rates; BULL/BEAR or any direction verdict; instruction sentences; an order path — there is none in this stack (`desk.note` says so,
inventory §5) and nothing here changes that.

## §B The desk in one page

Three screens, one rail, two drawers. **Frame, all screens:** rail 22 px · headline band 56 px · body `100vh − 98 px` · footer 20 px; one
breakpoint, **960 px**, named here and used everywhere — below it the right rail narrows 300 → 220 px, nothing stacks.

| key | does | key | does |
|---|---|---|---|
| `1` | TODAY | `[` / `]` | scrubber −5 m / +5 m |
| `2` | CAMPAIGN | `space` | play / pause replay at 60× |
| `3` | RECORD | `g` | jump to now, unpin the scrubber |
| `5` | health drawer (toggle) | `w` | campaign window 5m → 15m → day |
| `?` | legend drawer (toggle) | `m` | mute |
| `n` / `b` | next / previous index | `t` | theme light ↔ dark, stored in `localStorage` |
| `j` / `k` | row cursor, **its own index per screen** | `Esc` | close drawer |
| `c` | survival candidate row-group, off by default | — | — |

**The shared axis.** CAMPAIGN and RECORD share one x axis, `09:15 → clamp(now + 60 min, 11:30, 15:30)`, recomputed on every poll and every
scrub and locked to 15:30 from 14:30 onward, same pixels-per-minute on both screens, one scrubber; the rail footer prints the current
px-per-minute so two times of day stay comparable. TODAY has no axis — a gate is a state, not a history. **The scrubber** sets the whole
desk "as of": every header reads `as of 11:20 (scrubbed)`, CAMPAIGN dims everything right of the cursor, `g` returns to now, and a scrub
key re-fetches both screens outside the poll. **Polling cadences** — no SSE exists anywhere in the server (inventory §10), so a new UI must
poll: `/api/desk/health` 2 s · `/api/desk/today` + `/api/frame` + `/api/paperdesk` 3 s · `/api/day/oi` + `/api/day/record` +
`/api/day/visits` + `/api/series` + `/api/warmap` 10 s and on every scrub key. **Fixed-skeleton rule:** every region reserves its height at
first paint from its row cap, so a poll changes ink only; numbers sit right-aligned in fixed-width columns with `font-variant-numeric:
tabular-nums`, so a change in digit count cannot move a row.

## §C Vocabulary and visual system

**The four levels.** State is carried by geometry, never hue, so they survive both themes and a colour-blind glance.

| level | means | geometry |
|---|---|---|
| `PAKKA` | measured, current, actionable | solid 3 px accent rule, full headline width |
| `SHAK` | present but degraded — inferred, stale, thin n | 3 px rule at half width, 45° hatched |
| `NAHI` | actively negative — no new risk, source dead, series killed | reversed block: ink ground, ground ink, no hue |
| `PATA NAHI` | a hole; **wins whenever any input is a hole** | 1 px dashed grey outline, no fill |

Each screen names its own noun on top of the four: GATE {TRADE / HALF SIZE / NO NEW RISK / PATA NAHI}; a health source {live / late / dead /
never started}; a series {earning / thin / killed / not adjudicable}. Four levels, three nouns, no fifth vocabulary. Enforced twice:
gate.py:48 already returns hole-wins server-side, and `level()` in `desk.js` returns `PATA NAHI` for any null input before a renderer sees
it. **Absence grammar:** a hole renders where the value would be, dim italic, `PATA NAHI — <one clause ≤48 ch>` from the route's `*_why`
sibling — never a red error, a zero, a blank, a default or a row of its own at full weight; holes sharing one reason collapse to one line.
**Time and provenance:** every region carries its own `HH:MM` right-aligned in MARK size — the data's time, not the poll's; a stale region
dims to 55 % and its stamp becomes `as of 11:04`; `~` prefix = inferred, plain = measured, **nothing else is tagged**, and **`SHAK` beats
`~`** — inferred *and* degraded takes the SHAK geometry with the `~` kept, so `~` alone means inferred but current. The footer carries
`/api/desk/health.coverage` as `started 09:45 · 30 min late · 6 rebuilt · 4 not`, expanding into the two named lists.

**Type — four sizes, no fifth.** HEAD 30 px Segoe UI 600 (one state word or big number per screen) · NUM 17 px Consolas / `ui-monospace`
tabular (numbers that carry a decision) · BODY 13 px Segoe UI (labels, questions) · MARK 11 px (times, ages, tags, legend). Row caps: TODAY
≤ 18 rows, CAMPAIGN ≤ 14 lanes + fut strip, RECORD ≤ 12 series rows; beyond the cap is `+N more` in the rail. **Palette** — hue carries SIDE
only; values are the chart overlay's own (overlay.js:82-83).

| token | light | dark | carries | token | light | dark | carries |
|---|---|---|---|---|---|---|---|
| `--ce` | `#a8791a` | `#e0b04e` | CE side | `--ink` | `#0b0e13` | `#e8edf2` | primary text |
| `--pe` | `#1f7f8f` | `#4fb8c8` | PE side | `--muted` | `#4a5568` | `#8d99a7` | labels, holes, MARK |
| `--buy` | `#0f7b6c` | `#2fbf8f` | buy zone / above water | `--ground` | `#ffffff` | `#0b0e13` | page |
| `--sell` | `#c0392b` | `#f0605a` | sell zone / under water | `--panel` | `#f4f5f7` | `#141926` | region inset |
| `--accent` | `#b26b00` | `#d99b2e` | headline rule, scrubber, degraded rail cell — nothing else | `--hair` | `#d8dce2` | `#242b36` | 1 px borders |

**Theme rule.** Light is first-class — her chart is white. Default follows `prefers-color-scheme`; `t` toggles and writes
`localStorage.deskTheme`, which wins over the media query; `<html data-theme>` is stamped by a 3-line inline script before first paint.
**Sound:** one tone, 440 Hz, 400 ms, once per **transition to dead**, for **all six sources** — the chart relay included, because the panel
that would otherwise tone for it lives in the tab that went blind at 09:51, and a tone duplicated with the panel is a far smaller sin than
a silent blind spot. `m` mutes; the panel owns the trade beep.

## §D Screen 1 — TODAY (the 09:14 screen)

Three regions by body height: **board 24 % · survival 38 % · paid 38 %**, each answering one question, the question in BODY and the number
in NUM behind it. **Board — *can I sell today, on which index*:** three columns 34/33/33 %, one row per index. Gate word ←
`/api/desk/today.gate.level` (hole: the joined `gate.holes`); `z` ← `.board[i].z`, from that index's own frame and nowhere else (hole:
`PATA NAHI — no chart posting`); carry ← `.board[i].carry`, the trapped side and strike range (§H.0; hole: `PATA NAHI — no warmap for
<idx>`); health dot ← `/api/desk/health.sources[chart:<idx>].level`. **YESTERDAY is one line per index**, a full-width strip under the
three columns ← `.yesterday[i]`: prior close · prior range · the walls at last close · overnight OI change on the two biggest strikes, from
the last row of `frame_<prev>.jsonl` (hole: `PATA NAHI — no record for <prev day>`). Today only NIFTY posts and the other two read `PATA
NAHI — no chart posting` — the honest state, not a bug to paper over. **The gate can leave grey** through three server-side wires in the
brain (§H.7): `ivrv` from the surface, `events.json` from disk, `squeeze` dropped; with all three present it reads PAKKA TRADE / HALF SIZE
/ NO NEW RISK. The frame's `head.gate` (frame.py:157) is the single source, read by TODAY and the panel chip alike; a `PATA NAHI` gate
prints at **NUM size, not HEAD**, the dashed rule carrying the level, and each hole prints once — the event clause rides the headline only.

**Survival — *will I survive being wrong*.** The title **always** names the book: `paper ₹25L · 2 lots` from `/api/paperdesk.desk.risk` +
`.lots`. It is **one gap table at full region width**; the candidate is a **second row-group behind `c`, off by default**, titled
`candidate · N lots` and only when `data/book.json` exists. Her real book is never wired; every number here carries `~`. Column count
follows the available width; a column that does not fit is **dropped explicitly and labelled** — `±2 % hidden — narrow` — never clipped,
never scrolled.

| field | source | hole clause |
|---|---|---|
| P&L at now / ±1 % / ±2 % | `/api/desk/today.survival.gap[k].pnl`, `survival.py` over per-strike `delta`/`gamma` in `/api/chain.strikes` | `PATA NAHI — chain has no greeks` |
| margin | `.gap[k].margin`, the naked-leg floor `desk._naked_margin` (desk.py:1120, `NAKED_MARGIN_PCT = 0.11` desk.py:147; model documented book.py:11-43, applied book.py:211-225) | `PATA NAHI — no legs to price` |
| free | `.gap[k].free` = capital − margin | inherits margin's hole |
| square-off distance | `.sq_off{pct,px}` — the move where free crosses 0 under the floor | `PATA NAHI — free never crosses` |
| days of income at risk | `.days_of_income` = worst gap loss ÷ `/api/paperdesk.desk.theta_day_est.rupees` (the object's number; `legs` and `no_legs_why` sit beside it, trader.py:1059-1063), never `inf` | `PATA NAHI — no theta collected yet` |

The basis is in the region title, always: **`~ floor, not SPAN`** — this stack cannot run SPAN (desk.py:138-149) and must never print a
number that reads like a broker's. **Am I paid — *is anyone paying me*:** `atm_iv` ← `/api/surface.indices.<idx>.fit.atm_iv` (hole:
`surface did not fit`); `rv` ← `.rv5.rv` (hole: `<rv5_why>`); ratio ← `.paid.ivrv`, a **MARK clause** under 1.0 — `ratio 0.88 · below 1.0,
no business` — never a reversed NAHI block (hole: `iv/rv — <which side> missing`); straddle open→now ← `.paid.straddle`, ATM CE+PE `ltp`
now against the **first** `/api/chain.series` row of the day (hole: `no chain series row for the open`); `VEGA ATTACK ~` when straddle ≥ +5
% with `|spot move| < 0.15 %` (never a hole, simply absent); σ of the straddle = straddle ÷ spot; each strike's distance in that σ,
**printed once, here only** (hole: `no open legs`).

```
rail  tape 1s · chain 4s · depth 11s · chart N 2s·B —·S — · record 11m  [1]TODAY 2 3  11:21
head  GATE  PATA NAHI — event calendar: not checked · iv/rv — rv5 missing  ▁▁▁ (dashed, NUM)
      ┌ 34 % ──────────────────┬ 33 % ───────────────────┬ 33 % ─────────────────────────┐
board │ NIFTY   z −0.82  PAKKA │ BANKNIFTY  PATA NAHI —  │ SENSEX  PATA NAHI —           │
      │ carry PE 23200 ~    ●  │   no chart posting   ○  │   no chart posting         ○  │
      ├ YESTERDAY ─────────────┴─────────────────────────┴─────────────────── 2026-09-15 ┤
      │ NIFTY 23,310 · 23,180–23,402 · walls CE23400/PE23200 · ON OI +1.8M/−0.9M         │
      │ BANKNIFTY · SENSEX   PATA NAHI — no record for 2026-09-15                        │
      ├ SURVIVAL  paper ₹25L · 2 lots  ·  candidate (c) off ────────── ~ floor, not SPAN ┤
      │            −2 %        −1 %       now      +1 %       +2 %                       │
      │  P&L    −₹2,41,000 ~ −₹96,400 ~     —   −₹71,200 ~ −₹1,88,000 ~                   │
      │  margin   ₹9,40,000 ~ ₹7,10,000 ~ ₹6,20,000 ~ ₹7,00,000 ~ ₹9,10,000 ~             │
      │  free    −₹1,40,000 ~   ₹90,000 ~ ₹1,80,000 ~ ₹1,00,000 ~ −₹1,10,000 ~            │
      │  square-off distance ~ −1.7 % (23,644 → 23,242) · days of income at risk 4.1 ~    │
      ├ AM I PAID? ───────────────────────────────────────────────────────── as of 11:19 ┤
      │  ATM IV 29 Sep  11.4   RV(5d) 12.9   ratio 0.88 · below 1.0, no business (MARK)  │
      │  straddle 214 → 231 (+17) with spot −6   VEGA ATTACK ~  ·  σ of straddle 0.9 %    │
      │  my strikes: 23600 CE 1.4σ · 22900 PE 1.1σ (paper) — printed here only           │
      └──────────────────────────────────────────────────────────────────────────────────┘
footer  started 09:45 · 30 min late · 6 rebuilt · 4 not          legend ?  ·  health 5
```

## §E Screen 2 — CAMPAIGN (the battlefield)

Widths at 1920 **map 1100 · rail 300 · fuel 120**, at 960 **map 700 · rail 220 · fuel 40**, never a scroll. **Axes:** x = the §B shared
axis, `09:15 → clamp(now + 60 min, 11:30, 15:30)` — 8.1 px per minute at 1920 on its 135-minute floor, 2.9 on the full day (5.2 → 1.9 at
960), the current value in the rail footer; y = price, strikes as horizontal lanes at their own price, spot through them as the contested
line. One map, never three. **A wall** is a bar in its strike lane starting at `since`, thickness ∝ **OI added since open** — one base for
every bar, fill CE gold / PE teal; totals live only in the right rail and are labelled, so the toolb units bug (a total beside an
added-since-open, unlabelled) cannot come back. **Build vs retreat:** a live bar is solid to its current level; on unwind the high-water
outline stays as a faint ghost (`ghost_hi`) and the solid fill retreats inside it, leaving the trench visible. `retreat` is server-computed
as `added_at(now) < 0.85 × peak.added`, `peak` being the day maximum of the cumulative added-since-open series, **independent of `win`**;
filled versus outline cannot be confused at any zoom, and no hue is spent on it.

**Textures.** At the **15 m** and **day** windows four textures ride as segments inside the lane: solid = writing (OI+, prem−) · dotted =
loading (OI+, prem+) · hollow = short-covering (OI−, prem+) · cross-hatch = liquidation (OI−, prem−). **At the 5 m window they collapse to
two** — solid build, outline retreat — because 75 segments across a 700 px map is 9 px each and 9 px cannot carry four textures; the
four-state word then moves to the rail line. The **`day` window is 30-minute segments**, never one per lane. Default window **15 m**, and
the mockup must still prove 15 m at 960 px on white. **Lanes:** ±7 strikes around spot, **cap 14**, `+N more` in the rail; all text lives
in the fixed right rail, one aligned line per lane, so labels cannot collide by construction. **Peaks:** a 1 px notch at the peak time in
every lane, the words in the rail line (`+4.4M peak 11:05 @23,204`); the **spot dot only for the `j`/`k` cursor row and the two largest
lanes**. **Backfill:** a `bf: true` segment paints the same texture at **55 % opacity**, in dark **55 % and outline-only fill**, plus one
`bf → HH:MM` marker on the axis at server start, and never merges with an observed segment. **Migration arrows:** paired unwind at A and
build at B, same side, same window → one thin arrow A→B, cap 3 per hour.

**Fuel tank:** a vertical bar outside the map at the far right, full map height, split at spot — CE notional above, PE below — from
`/api/warmap.indices.<idx>.runways` (`target{kind,px}`, `fuel`, `per_point`, `items[]`, `stop_zone`; hunt.py:61-94, exists today); trigger
price = `target.px` per side, a tick on the shared price axis and words in the rail. Hole: `PATA NAHI — runways not ok`. **Futures strip:**
a 28 px lane under the map on the same x axis, same textures, served as the `fut` block of `/api/day/oi` (§H.3) from the posted 5 m bars
frame.py:222 already reads; holes `PATA NAHI — no tape held for that day` and `PATA NAHI — bars carry no OI`, never faked from the frame's
single delta, and painted in `--ink` at **70 %** with the same four textures, never `--dim`. **Headline THE CARRY**, the one coloured state
element here: the trapped side and strike range (`warmap.heat`, §H.0), trip price from `runways.<side>.target.px`. **Rail line grammar**,
five fixed columns per lane — `<SIDE> <strike>` · `<+added since open>` · `<peak marker or state word>` · `<time>` · `<migration target>`,
e.g. `PE 23200 +8.1M peak 11:30 @23,188 ← 23150`; **each column has a fixed width and its own ellipsis, no cell wraps**, row height pinned
to the canvas lane pitch and the rail footer height a constant, so canvas and DOM never measure each other. Then labelled totals (`CE added
since open 12.4M`), `+N more`, and `win 15m (w) · 8.1 px/min · as of 11:19`.

```
rail  tape 1s · chain 4s · depth 11s · chart N 2s·B —·S — · record 11m 1 [2]CAMPAIGN 3  11:21
head  THE CARRY   PE 23200–23350 · 29–44 % of OI above spot ~ · trips 23,350 ~  ▁▁▁▁ (half)
 ┌─ map 1100 px ────────────────────────────────────┬─ rail 300 ────────────┬ fuel 120 ─┐
 │23400 ╎      ▓▓▓▓▓▓░░░░╌╌╌╌╌ ghost                │ CE 23400 +2.1M  11:20 │  CE       │
 │23350 ╎ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓            │ CE 23350 +4.4M  peak  │  ▓▓▓      │
 │23300 ╎ ·····························             │ CE 23300 +1.2M loading│  ── trips │
 │ spot ╎ ╲__╱╲___╱╲___contested line___╱╲__        │ 23,244  z −0.82       │   23,350  │
 │23200 ╎    ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒           │ PE 23200 +8.1M  11:30 │  PE       │
 │23150 ╎       ▒▒▒▒▒▒→→→→→▒▒▒▒▒▒                   │ PE 23150 +2.3M ← 23100│  ▓▓▓▓▓▓▓▓ │
 │23100 ╎ ▒▒▒▒▒░░░░╌╌╌ retreat                      │ PE 23100 −1.7M cover  │  ₹4.2cr ~ │
 ├ FUT  ╎ ▓▓░░▓▓▓▓░░░░▓▓▓▓▓▓░░░░▓▓  second army     ┤ CE added open 12.4M   │           │
 │      09:15  bf → 09:45   10:15   11:15   12:21   │ win 15m (w) · 8.1px/m │ as of 11:19│
 └──────────────────────────────────────────────────┴───────────────────────┴───────────┘
```

## §F Screen 3 — RECORD (the honest ledger)

Same x axis as CAMPAIGN, four lanes, one scrubber; lanes 1100 px, card 300 px. **price** (90 px): 5 m closes, ±2σ / ±3σ edges dotted,
nothing else. **state** (30 px): `/api/day/record[].state` as segments — WARMUP · WAITING · ARMED · TRIGGERED · IN ZONE — with `gate` as a
12 px band beneath; `TRIGGERED` wears the **solid PAKKA rule**, never the reversed block. **visits** (60 px): one glyph per zone visit at
its bar with an outcome bar extending **+30 m (6 bars)**, up-tint favourable, down adverse. **marks** (26 px): record appends, fire
transitions, source outages from `/api/desk/health.ring`, paper refusals from `/api/paperdesk.desk.day_refusals` — the lane where the desk
indicts itself. **Visit cards:** the miss is the first word, counts only and never a percentage (house rule: no hit rates). **There is no
visit ledger table** — `j`/`k` walks the card and the money strip inherits the freed height. **σ, once, in the system's own geometry:**
`sigma` = `where.sigma` at `t0`, the VWAP band half-width in points, the unit the zone itself is cut in (d2 = 2σ); the rotation is entered
at the 2σ edge and pays on the way back, so **EARNED = favourable excursion ≥ 2σ within 6 bars**, adverse **≥ 1σ**, and the card prints the
σ in points beside the multiple (`+137 = 7.6σ · σ 18 @ 09:45`). **The outcome is one ordered ladder, first match wins:**

1. `WRONG` — fired ∧ adverse ≥ 1σ
2. `CALLED` — fired ∧ EARNED
3. `FALSE` — fired ∧ neither — the tool spoke and nothing happened
4. `MISSED` — not fired ∧ EARNED
5. `SPARED` — not fired ∧ adverse ≥ 1σ
6. `QUIET` — not fired ∧ neither — nothing happened and nothing was said
7. `PATA NAHI` — any excursion cell null; carries `outcome_why`

Horizons are the scorer's existing ones (`HORIZ_BARS = (1, 3, 6)`, `HORIZ_MIN = (90, 180)`, score_frame.py:20): cards show **+30 m (6 bars)
and +90 m**, not the brief's 60 m, and **no new horizon population is created**. The tally prints left to right **missed · false · wrong ·
called · spared · quiet (n)**. When the panel's votes ballot exists (unbuilt — `votes` appears nowhere in `frame.py`, `senses.py` or
`server.py`, inventory §2) the card gains `votes n of 4`: a field today, no work. **Series table**, `/api/series`, ≤ 12 rows — taps, tells
(`resolved`), control (`setup.control`, the same-distance kill population, score_frame.py:73-79), `vpin ≥ 0.9`, paper strategies — columns
`name`, `n`, `sessions`, `started`, `horizon 30`, `kill` (the written rule or null) and level with its clause; **no rate, no base, no
comparison number**. **Level is `PATA NAHI` until n ≥ 20, then `SHAK` until a kill rule is written; it never says "works".** **Money
strip:** paper only, labelled `paper ₹25L · maker fills are an UPPER bound`, from `/api/paperdesk`; candidate greeks from `survival.py` sit
beside it labelled `candidate · N lots`, only when `book.json` exists. It also carries **`adjustments 4 of 6`** — same-position modifies
today from `/api/paperdesk.desk.day_trades` against `adjust_cap` in `data/book.json` (default 6), SHAK-hatched at the cap; it advises and
blocks nothing, there being no order path.

```
rail  tape 1s · chain 4s · depth 11s · chart N 2s·B —·S — · record 11m 1 2 [3]RECORD  11:21
head  SCORE  taps n=14 of 20 · PATA NAHI — not adjudicable                  ▁ ▁ ▁ (dashed)
 ┌─ lanes 1100 px ──────────────────────────────────┬─ card 300 ───────────────────────┐
 │price ╎ ╲__╱╲___╱╲___╱   ‧‧‧+2σ‧‧‧                │ 09:45  d2 visit  buy     MISSED  │
 │state ╎[WARMUP][WAITING ][ARMED][TRIG][WAITING  ] │ +137 / −6 in 30m · +151 in 90m   │
 │gate  ╎[PATA NAHI ····························· ] │ +137 = 7.6σ · σ 18 @ 09:45       │
 │visits╎     ◯━━━━━━━▶ +137          ◯━▶ +9       │ screen said: WAITING · fire false │
 │marks ╎ ▪rec ▪relay gap 09:51–10:02 ▪beep ▪refuse│ flow none · confirm not wired    │
 │      ╎        ▲ scrubber 11:20                   │ no beep · votes — ballot unbuilt │
 │      09:15     10:15        11:15       12:21    │ missed 2·false 1·wrong 0·        │
 │                                                  │ called 1·spared 0·quiet 3  (n 7) │
 ├ SERIES ────────────────────────────────────────────────────────────────────────────┤
 │ taps           n 14  sessions  9  started 09-05  horizon 30  PATA NAHI — n<20       │
 │ tells resolved n 31  sessions 12  started 09-03  horizon 30  SHAK — no kill rule    │
 │ control        n 29  sessions 12  started 09-03  horizon 30  SHAK — no kill rule    │
 ├ MONEY  paper ₹25L · maker fills are an UPPER bound ────────────────────────────────┤
 │ theta ₹8,200 ~ − hedge ₹3,100 ~ · forced_ratio 1.3 · headroom ₹18,80,000 ~          │
 │ refusals today 3: forced_ratio 1.3 (×2) · day-loss cap (×1)  ·  adjustments 4 of 6  │
 └────────────────────────────────────────────────────────────────────────────────────┘
```

## §G Health rail and drawer

One 22 px rail across the top of every screen, never a screen of its own — a screen you must navigate to fails at exactly the moment it
matters.

| source | read from | cadence_s | source | read from | cadence_s |
|---|---|---|---|---|---|
| tape feed | `/api/health.feed.age_s` + `.healthy` | 1 | chart relay per index | `_SENSES["tape"][idx]["at"]` (server.py:1130 — recorded, never served) | 5 |
| chain poller | age of `_chain_doc(poller, idx)["built_at"]` (server.py:293-304; epoch float, `ts` beside it is a clock string) | 12 | record writer | last append time, rows today, file MB | 300 |
| depth relay | `/api/senses.orders_bridge.age_s` | 15 | senses loop | `/api/senses.error`, `.up_s` | 5 |

**Levels:** `live` age < 2× cadence · `late` < 5× · `dead` ≥ 5× or `error` non-null · `never started` when the source has produced nothing
this process. `feed.healthy:false` with `connected:true` — the live state on 2026-09-16 — renders as **`late — socket up, no ticks
<age>`**. **Transition ring:** the last 200 transitions `{source, t, from, to}`, the only place the RECORD marks lane reads outage gaps
from. **Rail text:** `tape 1s · chain 4s · depth 11s · chart N 2s·B —·S — · record 11m` — **one cell per posting index for the chart
relay**, **every cell an age, never a clock time**, and a source that never started prints `—`, never `0s`. A `late` cell takes the **SHAK
hatch** in `--accent`, geometry not hue alone, a `dead` cell reversed ink, mute last. **Drawer `5`** shows per source the `why`, backfill
state, `last_seen`, and the two coverage lists (`_coverage`, server.py:2248). **Tone rule:** an outage is an absence, not a fault — the
drawer says what stopped and when it was last seen; it never says "ERROR", never colours red, never asks her to do anything.

## §H Server contract

Every null carries a sibling `*_why` of ≤ 48 characters; backfilled rows carry `bf: true` and never blend with observed. Each route is a
thin `elif` in `Handler.do_GET` (between server.py:1271 and server.py:1921, before the final `else`; the dispatch is an ordered `startswith`
chain with no route table, so `/api/desk/health` and `/api/desk/today` must sit above `/api/desk` at server.py:1570), and all computation
lives in a pure module. **Read unchanged, no server work:** `/api/frame` (1915), `/api/paperdesk` (1739), `/api/warmap` (1762),
`/api/surface` (1625), `/api/chain` (1271), `/api/health` (1210), `/api/senses` (1829).

**H.0 `/api/warmap` — the fields the desk reads** (existing route, no server work): `indices.<idx>.heat[]` (`k, ce_oi, ce_chg, ce_pain,
ce_conf` and the `pe_*` mirror) · `runways.{up,down}.{target{kind,px}, fuel, per_point, items[], stop_zone}` · `levels[]` · `max_pain`, a
grey tick on the price axis only, never a number with a verdict (§A). **`carry` is the side and strike range holding the largest
trapped-writer notional** — per-strike trapped notional, not a pain aggregate. **`pain %` is the fraction of that strike's OI written above
the current price**, its denominator named on screen (`29–44 % of OI above spot`). Holes: `PATA NAHI — no warmap for <idx>` · `PATA NAHI —
runways not ok`.

**H.1 `GET /api/desk/health`** — `desk_health.build(health, senses, chains, tape_ats, record_stat, now) -> dict`, fed by the six §G inputs
plus an `os.stat` of `frame_log.day_path(day)`; the ring is a module-level `deque(maxlen=200)`. One entry per §G source, **the chart relay
one per index**; three shown. Types: `source` str · `last_seen` float|null · `age_s` float|null · `cadence_s` int · `level` str ∈
live|late|dead|never started · `backfilled` bool · `why` str|null (the `*_why` for every null in the row) · `rows_today` int · `file_mb`
float · `up_s` int (senses loop) · `ring[].from`/`.to` str.

```json
{"ok": true, "now": 1789542061.4, "muted": false,
 "sources": [
  {"source":"tape feed","last_seen":1789542060.1,"age_s":1.3,"cadence_s":1,"level":"live","backfilled":false,"why":null},
  {"source":"chart BANKNIFTY","last_seen":null,"age_s":null,"cadence_s":5,"level":"never started","backfilled":false,"why":"no frame posted this process"},
  {"source":"record writer","last_seen":1789541940.0,"age_s":121.4,"cadence_s":300,"level":"live","backfilled":false,"why":null,"rows_today":5552,"file_mb":116.3}],
 "coverage": {"server_up":"09:45","session_open":"09:15","late_min":30,"reconstructed":["chain minutes"],"not_reconstructable":["tape events 09:15-09:45"],"why":"server started 30 min after the open"},
 "ring": [{"source":"depth relay","t":1789538000.0,"from":"live","to":"dead"}]}
```

**H.2 `GET /api/desk/today?idx`** — `survival.build(legs, strikes, spot, capital, lot, theta_day) -> dict` plus `events.today(path, day)`.
`survival.py` is pure, over per-strike `delta`/`gamma` from `/api/chain.strikes` and `desk._naked_margin` (desk.py:1120); the gate object
is the frame's own `head.gate`, never recomputed. Types: `z` float|null · `carry` str|null · `health` str · `gap.<k>.pnl`/`.margin`/`.free`
float, `k` ∈ `"-2"|"-1"|"0"|"+1"|"+2"` — **`"0"` is now**, the column the region prints · `sq_off.pct`/`.px` float · `days_of_income`
float|null, **`PATA NAHI — no theta collected yet` on a zero or null divisor, never `inf`** · `vega_attack` bool · `strikes[].sigma` float
· `whose` str · `yesterday[]` per index `{idx, day, close, range[2], walls, oi_overnight[{k,side,chg}], why}` from
`record_read.yesterday(prev_path, idx)`.

```json
{"ok": true, "idx": "NIFTY", "ts": "11:19",
 "gate": {"level":"PATA NAHI","reason":"iv/rv — rv5 missing; event calendar: not checked","holes":["iv/rv — rv5 missing","event calendar: not checked"],"would_be":"HALF SIZE","would_be_reason":"expiry day, gamma fast","tag":"I"},
 "board": [{"idx":"NIFTY","z":-0.82,"z_why":null,"carry":"PE 23200","carry_why":null,"health":"live"},
           {"idx":"BANKNIFTY","z":null,"z_why":"no chart posting","carry":null,"carry_why":"no chart posting","health":"never started"}],
 "yesterday": [{"idx":"NIFTY","day":"2026-09-15","close":23310.0,"range":[23180.0,23402.0],"walls":"CE 23400 / PE 23200","oi_overnight":[{"k":23400,"side":"CE","chg":1800000},{"k":23200,"side":"PE","chg":-900000}],"why":null}, {"idx":"BANKNIFTY","day":null,"close":null,"range":null,"walls":null,"oi_overnight":null,"why":"no record for 2026-09-15"}],
 "survival": {"whose":["paper ₹25L · 2 lots","candidate · 5 lots"],"capital":2500000,"basis":"~ floor, not SPAN","gap_why":null,"sq_off":{"pct":-1.7,"px":23242},"sq_off_why":null,"days_of_income":4.1,"days_of_income_why":null,
   "gap": {"-2":{"pnl":-241000,"margin":940000,"free":-140000},"-1":{"pnl":-96400,"margin":710000,"free":90000},"0":{"pnl":0,"margin":620000,"free":180000},"+1":{"pnl":-71200,"margin":700000,"free":100000},"+2":{"pnl":-188000,"margin":910000,"free":-110000}}},
 "paid": {"atm_iv":11.4,"atm_iv_why":null,"rv":12.9,"rv_why":null,"ivrv":0.88,"ivrv_why":null,"straddle":{"open":214,"now":231,"d":17},"straddle_why":null,"spot_move_pct":-0.03,"vega_attack":true,"sigma_pct":0.9,
          "strikes":[{"k":23600,"side":"CE","sigma":1.4,"whose":"paper"},{"k":22900,"side":"PE","sigma":1.1,"whose":"paper"}]}}
```

**H.3 `GET /api/day/oi?idx&win=5|15|day`** — `day_oi.build(minutes, spot, win, bf_before, bars) -> dict`, pure over `ChainState.minutes`
(chain_metrics.py:339-345 — `{"HH:MM": {spot, k:{strike:(ce_oi_chg, pe_oi_chg)}, px:{strike:(ce_ltp, pe_ltp)}}}`, in RAM all day, never
pruned). `day_oi.state4(d_oi, d_prem) -> str` is one pure function used for both the strike lanes and `fut`, so the four-state table exists
once. Types: `strike` float · `side` str ∈ CE|PE · `added` float (OI added since open at the window end) · `since` str, **the first minute
cumulative added crosses an absolute 25 000 contracts** · `peak.added`/`.spot` float, `peak.t` str, the **day** maximum of the cumulative
added-since-open series, independent of `win` · `ghost_hi` float (= `peak.added`) · `retreat` bool, `added_at(now) < 0.85 × peak.added`
against that same day peak · `state4` str ∈ writing|loading|covering|liquidation · `bf` bool · `capped` int · `bf_at` str|null ·
`totals_why` str|null, **required whenever `bf_at` is non-null** · `lanes_why` / `fut.why` the `*_why` siblings. `fut` comes from the
posted 5 m bars frame.py:222 reads (`closed[].oi`, `.o`, `.c`), served today at `/api/frame/bars`; `fut.why` is `"no tape held for that day
in this process"` or `"bars carry no OI"`.

```json
{"ok": true, "idx": "NIFTY", "win": 15, "spot": 23244.0, "ts": "11:19", "bf_at": "09:45", "capped": 3,
 "lanes": [{"strike":23200,"side":"PE","added":8100000,"since":"09:52","ghost_hi":8400000,"retreat":false,"peak":{"added":8400000,"t":"11:30","spot":23188.0},
            "segments":[{"t":"09:45","added":1200000,"state4":"writing","bf":true},{"t":"10:00","added":3100000,"state4":"writing","bf":false}]}],
 "lanes_why": null, "totals": {"ce_added_since_open":12400000,"pe_added_since_open":18700000}, "totals_why": "chain started 09:45, open 09:15",
 "migrations": [{"t":"10:45","from":23150,"to":23100,"side":"PE"}],
 "fut": {"segments":[{"t":"09:45","d_oi":-24000,"d_px":7.0,"state4":"covering","bf":false}],"why":null}}
```

**H.4 `GET /api/day/record?day&idx`** — `record_read.rows(path, idx) -> list[dict]`, streaming `data/frame/frame_<day>.jsonl` line by line,
one compact row per signature change; **never loads the file into memory**, cached by `(path, mtime, size)`. No `coverage` blob, no walls
rows — those are most of the 21 KB row. Types: `t` str "HH:MM" · `state` str · `fire` bool · `gate` str · `z` float|null (a null carries
`z_why`) · `px` float|null · `visit` str|null · `missing` list[str]. `record_read.yesterday(path, idx)` rides the same stream for §D and is
the one caller that keeps a row's walls: the last row's ladder, its PDC/PDH/PDL rows the prior close and range.

```json
[{"t":"09:45","state":"WAITING","fire":false,"gate":"PATA NAHI","z":-0.42,"px":23301.0,"visit":null,"missing":["warmap"]},
 {"t":"09:52","state":"ARMED","fire":false,"gate":"PATA NAHI","z":-1.91,"px":23244.0,"visit":"09:45","missing":[]}]
```

**H.5 `GET /api/day/visits?day&idx`** — `record_read.visits(path, idx) -> list[dict]`, grouping the same streamed rows by `setup.visit`
(frame.py:390-405) and reading forward cells from the scorer's own `ex` block (score_frame.py:30-42). Types: `t0`/`t1`/`side`/`band` str ·
`ref` float · `sigma` float|null (`where.sigma` at `t0` — the band half-width in points, d2 = 2σ; `sigma_why` its sibling) · `fired` bool ·
`said.flow_n` int · `said.confirm` str · `ex.<h>`/`adverse.<h>` float|null · `outcome` str ∈ WRONG|CALLED|FALSE|MISSED|SPARED|QUIET|PATA
NAHI, the §F ladder in that precedence, with `outcome_why` **required, and the outcome `PATA NAHI`, whenever an excursion cell is null** ·
`votes` int|null with `votes_why`. `confirm` is permanently

```json
[{"t0":"09:45","t1":"10:07","side":"buy","band":"d2","ref":23244.0,"sigma":18.0,"sigma_why":null,
  "fired":false,"said":{"state":"WAITING","flow_n":0,"confirm":"not wired"},
  "ex":{"6":137.0,"90m":151.0},"adverse":{"6":-6.0},"outcome":"MISSED","outcome_why":null,"votes":null,"votes_why":"ballot not built"}]
```

**H.6 `GET /api/series`** — `record_read.series(day_paths) -> list[dict]`; `sessions` counts the `frame_<day>.jsonl` files carrying the
series, cached per day so a count is not an O(days × rows) rescan. Types: `n`/`sessions`/`horizon` int · `started` str · `kill` str|null,
the written rule or nothing · `level` str ∈ PATA NAHI|SHAK|NAHI · `why` the level's clause. **No `measure`, no `base`:** counts and a kill
rule, never a rate against a comparison (CLAUDE.md rule 4).

```json
[{"name":"taps","n":14,"sessions":9,"started":"2026-09-05","horizon":30,"kill":null,"level":"PATA NAHI","why":"n<20"},
 {"name":"control","n":29,"sessions":12,"started":"2026-09-03","horizon":30,"kill":null,"level":"SHAK","why":"no kill rule"}]
```

**H.7 Changes to existing code.** *`frame_log.sig()` quantisation and the append lock:* `sig()` (frame_log.py:28-32) hashes raw `r.get("p")`
floats today, so basis jitter alone rewrites the signature — the churn behind 5552 rows / 116.3 MB on 2026-09-16 against 46 rows / 525 KB on
2026-09-15 (inventory §3). New `sig(fr, row=5.0)` rounds every price to the nearest `row` and keeps identity fields only (`idx`, quantised
`(p, kind, state)` per walls row, `setup.state`, `setup.fire`, `(name, target)` per tell, sorted `missing`); `append_if_changed(fr, day,
idx, path=None, row=5.0)` gains the same argument and server.py:1128 passes `float(doc.get("rowSize") or 5)`, the expression frame.py:247
already uses. A module-level `threading.Lock` wraps the `_last_sig` read, the append and the `_last_sig` write as one critical section,
closing the 39-row corruption of 10:16–10:23 under `ThreadingHTTPServer` (server.py:2507). *`_book_for` ivrv wire (server.py:982):* `"ivrv":
None` becomes the ratio of the objects `/api/surface` already serves (server.py:1651-1665).

```python
# _surface_read(poller, idx) -> SurfaceRead dataclass, always (server.py:307); _rv5(idx) -> (dict, why) (server.py:352)
_fit = (asdict(_surface_read(self.poller, idx)).get("fit") or {})
_rv5d, _rv_why = _rv5(idx)
_iv, _rv = _fit.get("atm_iv"), (_rv5d or {}).get("rv")
"ivrv": (_iv / _rv) if (_iv and _rv) else None,
"ivrv_why": None if (_iv and _rv) else ("iv/rv — atm_iv missing" if not _iv else "iv/rv — rv5 missing"),
```

*`gate.state` signature change:* `squeeze` is removed — never measured (gate.py:43-46; frame.py:157 passes a literal `None`), so a
permanent `None` would keep the gate grey forever — and gate.py:47's unconditional `holes.append("event calendar not wired")` is deleted.
Old `state(ivrv, expiry_iso, today_iso, vpin_pct, squeeze)` → new `state(ivrv, expiry_iso, today_iso, vpin_pct, event, ivrv_why=None)`,
where `event` is `None` (not checked — a hole), `{}` (checked, nothing today — no hole, no effect), or `{"name": str, "level": "HALF
SIZE"|"NO NEW RISK"}` (worsen to that level, reason = the name). Hole names, exactly: `ivrv_why or "IV vs RV: not measured"` · `"expiry
date: chain did not give one"` · `"VPIN: not measured yet"` · `"event calendar: not checked"` — an absence, not an instruction; "create
data/events.json" lives in the legend drawer alone (§A). `level` stops being hard-coded (gate.py:48): the computed level when `holes` is
empty, `"PATA NAHI"` otherwise; `would_be` stays. VPIN stays an input (doctrine Q1, advisory only); `test_gate.py` call sites passing
`squeeze` are rewritten in Phase A. *`data/events.json`* is hand-maintained, read by pure `events.today(path, day) -> dict|None`: absent →
`None`, no entry for `day` → `{}`, entry → the dict. *`data/book.json`* is hand-entered candidate legs, never her real book, and carries
`adjust_cap` (default 6) for §F's adjustment brake; absent → no candidate row-group.

```json
[{"date":"2026-09-30","name":"RBI policy","level":"HALF SIZE"},{"date":"2026-10-28","name":"Fed decision","level":"NO NEW RISK"}]
{"whose":"candidate","lots":5,"adjust_cap":6,"legs":[{"k":23600,"side":"CE","qty":-5},{"k":22900,"side":"PE","qty":-5}]}
```

## §I Files and structure

No framework, no build step, no bundler, no dependency. ES modules, same-origin `fetch`.

| file / module | owns | public functions |
|---|---|---|
| `ui/desk/index.html` | the three fixed skeletons, rail, two drawers, pre-paint theme stamp; **`<meta charset="utf-8">` is its first head line** — the static handler sends no charset (server.py:984) and without it `₹ σ · −` serve as mojibake | — |
| `ui/desk/desk.css` | ten palette tokens × two themes, four type sizes, four level geometries, region grids | — |
| `ui/desk/desk.js` | polling, keys, screens, TODAY, RECORD cards + series + money, theme | `level(...vals)`, `fmt.num/pct/rs/age/hhmm`, `geom(level)`, `state4Class(dOi, dPrem)`, `mount()` |
| `ui/desk/lanes.js` | canvas: shared axis, scrubber, CAMPAIGN lanes/textures/peaks/ghosts/arrows/fuel/fut, RECORD four lanes | `axis(ctx, box, t0, t1)`, `campaign(ctx, box, day, opts)`, `record(ctx, box, rows, visits, ring)`, `scrub(t)` |
| `ui/desk/test.mjs` | `node --test` over the pure functions above | — |
| `tapemap/events.py` | the hand-maintained calendar | `today(path, day) -> dict\|None` |
| `tapemap/survival.py` | gap table, square-off distance, days of income | `build(legs, strikes, spot, capital, lot, theta_day) -> dict` |
| `tapemap/day_oi.py` | the campaign grid and the futures lane | `build(minutes, spot, win, bf_before, bars) -> dict`, `state4(d_oi, d_prem) -> str` |
| `tapemap/record_read.py` | the streaming record reader | `rows(path, idx)`, `visits(path, idx)`, `series(day_paths)`, `yesterday(path, idx)` |
| `tapemap/desk_health.py` | the one health object and the transition ring | `build(health, senses, chains, tape_ats, record_stat, now) -> dict` |

Tests: `test_events.py`, `test_survival.py`, `test_day_oi.py`, `test_record_read.py`, `test_desk_health.py`, plus new cases in
`test_gate.py` and `test_frame_log.py`. Route handlers stay thin: parse with the existing idiom (`parse_qs(urlsplit(self.path).query)`,
`self._idx()` at server.py:997-1001), call one pure function, `self._json(...)`.

## §J Testing and acceptance

**One check per module** — the smallest thing that fails if the logic breaks. pytest already runs 1118 tests.

| module | the one check |
|---|---|
| `events.py` | absent file → `None`; present with no entry today → `{}`; entry → the dict |
| `survival.py` | a two-leg short strangle at a known spot gives margin == `desk._naked_margin(spot, lot, 2)` and a `free` that crosses 0 exactly once |
| `day_oi.py` | a 3-minute fixture where OI rises then falls yields `peak.t` at the middle minute, `retreat: true`, `state4` writing then covering |
| `record_read.py` | a 3-line synthetic jsonl yields 3 rows, one visit, `outcome == "MISSED"` when `ex["6"] >= 2 × sigma` and `fired` is false — and the ladder's precedence holds: the same visit with `fired` true and no excursion is `FALSE`, never `QUIET` |
| `desk_health.py` | `age_s = 3 × cadence` → `late`; `5 × cadence` → `dead`; `connected:true, healthy:false` → `late` with the socket-up clause |
| `gate.py` | `event={}`, `ivrv=1.2`, a future expiry, `vpin_pct=0.1` → `level == "TRADE"` — the gate can leave grey |
| `frame_log.py` | two frames differing only by a sub-`rowSize` price jitter produce one append, not two |
| `test.mjs` | `level(1, null)` → `PATA NAHI`; `geom("SHAK")` → hatched half rule; `state4Class(+1, -1)` → `writing` |

**By eye, against the mockup:** all three screens at 960 and 1920, light and dark — 15 m campaign textures distinguishable at 960 px on
white, no region moving between two polls, no horizontal scrollbar, every hole a sentence; the campaign axis ends at `now + 60 m` with its
px-per-minute in the rail footer, the survival table at 960 names the columns it dropped and clips none, and `₹ σ · −` render as themselves
in the served page. **Live acceptance, next session.** At **09:14** TODAY paints inside 3 s, the gate shows a level or names its holes in
words, the board shows `PATA NAHI — no chart posting` for the two indices that do not post, YESTERDAY prints a line per index, and the rail
shows one age per source. At a **zone visit** a glyph appears in the visits lane within one poll of the frame's `visit` key changing and
the card's outcome word is one of the seven. At an **outage** the rail cell takes the hatch then reverses, one 440 Hz tone sounds once —
**any of the six sources** — a transition lands in the ring, and the marks lane shows the gap with times.

## §K Build phases

Restart rule: **Python changes restart the server only after 15:30 IST**; static files under `ui/` need no restart and no code change
(inventory §10).

**A. Brain.** Record churn fix (quantised `sig` + the lock) → `record_read.py` → the three gate wires (`ivrv`, `events.py`, drop `squeeze`)
→ `/api/day/oi` → `/api/desk/health` → `survival.py` + `/api/desk/today` → `/api/day/visits`, `/api/series`. Each: pure module, its test,
then the thin route. *Proves before B:* the record file grows at yesterday's rate not today's; every new route answers under 200 ms against
the live server; `gate.level` is not `PATA NAHI` on a fixture with all inputs present. **B. Shell.** `ui/desk/` skeleton, rail, keys,
vocabulary, theme, TODAY against `/api/desk/today` + `/api/frame` + `/api/paperdesk`. *Proves before C:* all 15 keys work with no mouse;
nothing moves across 20 polls; light and dark both legible at 960. **C. CAMPAIGN canvas** (`lanes.js`): axis, lanes, textures, peaks,
ghosts, migration arrows, fuel tank, fut strip, rail lines, the `w` windows. *Proves before D:* 15 m textures readable at 960 px on white;
the ±7 cap with `+N more`; the totals row labelled; backfilled segments visibly at 55 % with the `bf →` marker. **D. RECORD** lanes and
scrubber shared with C, visit cards, series table, money strip. *Proves before E:* `[` `]` `space` `g` move both screens' cursor
identically; a known past day replays with the same outcome words twice. **E. Finish.** Legend drawer, replay at 60×, mockup parity at
960/1920 light/dark. Then, **gated on Mary's approval only** — delete `ui/desk.html`, `ui/toolb.*`, `ui/index.html`, `ui/app.js`,
`ui/console.html`, `ui/fmt.js`, `ui/theme.css`, `ui/style.css`, and change the `/` redirect (server.py:1200-1208) from `/desk.html` to
`/desk/`. Not before. Old UIs are **anti-references**: no builder of this desk opens them.

## §L Anti-patterns

1. A gate that initialises green and is never downgraded by a hole.
2. BULL/BEAR — or any direction verdict — anywhere, least of all in a header.
3. Every job crammed on one page with no separation.
4. Layout that shifts on every poll, so the eye has no fixed place to land.
5. Panels that print fields instead of answering a question — a data dump is not a tool.
6. Holes rendered at the same weight as facts until UNKNOWN reads as the product.
7. The same fact computed twice from disjoint data, or rendered twice on one screen.
8. A panel no code ever writes, or a fix that repairs the log and not the screen.
9. Forward logs with no reader — clocks that tick and can never ring.
10. 25 font sizes, the question headers smallest, a `min-width` that blocks half-screen, no keyboard handler.
11. Numbers of two bases in one row, unlabelled (a wall total beside an added-since-open).
12. Doctrine-excluded content creeping back in — max pain, PCR, delta drag.
13. Survival computed for a book that is not hers and not labelled as such.

## §M Decisions log

- **R0** Operator Desk at `ui/desk/`, existing static fallthrough, polling only — no SSE exists and a static page needs no restart.
- **R0b** Old UIs are anti-references, deleted last and only on approval — so no builder inherits the defects being replaced.
- **R1** Three screens, 22 px rail, two drawers, the brief's keys plus `t`, one shared axis — a gate is a state, a campaign is a history, health is never a screen.
- **R2** Four levels, hue = side, geometry = state, four sizes, light first-class, one 440 Hz tone on all six sources, `~` = inferred — one palette for chart and desk, legible colour-blind on white.
- **R3** The gate leaves grey via `ivrv`, `events.json` and dropping `squeeze` — a permanently unmeasured input keeps the gate grey forever.
- **R3b** Survival names the book, uses the naked-leg floor labelled `~ floor, not SPAN`, real book never wired — toolb answered survival for a hypothetical and printed it as hers.
- **R4** CAMPAIGN from `ChainState.minutes`, four textures at 15 m/day and two at 5 m, lane cap 14, one base, peaks in the rail, backfill at 55 % — 9 px cannot carry four textures, which is how the last ladder became illegible.
- **R5** Quantised `sig()` and the lock first; cards at 6 bars and 90 m from the scorer's existing horizons; one ordered outcome ladder of seven words, missed first — no new horizon population, and the miss is the point.
- **R6** One `/api/desk/health` object, six sources, four levels, a 200-transition ring — a blind-check today must fan out to four routes and correlate them itself.
- **R7** One pytest per pure module, one `node --test` over the JS pure functions, canvas by eye — canvas pixels are an acceptance step, not a unit test.
- **R8** Phases A–E, brain before shell, deletion last — a face over a brain that cannot answer is the defect being replaced.
- **D1** One ordered outcome ladder, first match wins, with `FALSE` and `SPARED` added and the tally reading missed · false · wrong · called · spared · quiet — a fired-and-nothing visit laundered into QUIET is a false positive hiding on the screen whose whole claim is honesty.
- **D2** σ is `where.sigma` at `t0`, the band half-width the zone is cut in; EARNED = favourable ≥ 2σ in 6 bars, adverse ≥ 1σ, the σ printed in points beside the multiple — the rotation is entered at the 2σ edge, and naming source, unit and threshold together kills the 4× disagreement.
- **D3** The desk tones for all six sources, the rail `late` state takes the SHAK hatch, and the chart relay gets one cell per posting index — the old rule routed the alarm for the 09:51 blind-out back to the panel that lives in the tab that went blind.
- **D4** The campaign x axis is `09:15 → clamp(now + 60 min, 11:30, 15:30)` with px-per-minute in the rail footer, and "an empty right third at 11:00 is information" is deleted — it was arithmetically wrong (55 %) and the sole defence of spending the map on the future.
- **D5** One survival gap table at full region width, candidate a row-group behind `c` and off by default, omitted columns dropped explicitly and labelled — measured at 960 the tails were being clipped silently from the one region she would trade off.
- **D6** No `measure` / `base` on `/api/series`; counts, a kill rule and a level clause only — a rate against a base is a hit rate, forbidden by doctrine and CLAUDE.md rule 4.
- **D7** The campaign rail row is five fixed columns, each with its own width and ellipsis, row height pinned to the lane pitch and the footer height constant — free text reflowing one line to two on a poll is the rejected defect returning.
- **D8** The events hole reads `event calendar: not checked` and `index.html` carries `<meta charset="utf-8">` first — the old text was an instruction sentence §A excludes, and without the meta the desk's own vocabulary serves as mojibake.
- **D9** YESTERDAY, one line per index in the board region, from the previous day's last record row — TIME is this desk's declared job and it had no memory older than this morning's file; board takes 24 % and survival gives up the height the `c` toggle freed.
- **D10** The money strip carries `adjustments N of cap` from `day_trades` against `adjust_cap` in `book.json`, SHAK at the cap — free execution's failure mode is over-adjustment, and the brake must be deliberate; it advises and blocks nothing, because there is no order path.
- **considered and rejected:** deleting the candidate book, and moving the money strip to TODAY — a hand-entered candidate is the only way the survival question is answerable at all and D5 removes the clipping without removing the answer; TODAY is the sixty-second screen and money is a review question, so the strip stays on RECORD and takes the height the deleted ledger freed.
- **spec decision:** futures strip is `/api/day/oi.fut`, not a new `/api/day/fut` — the bars already exist (frame.py:222, `/api/frame/bars`), and one route with one `state4()` beats two of each (anti-pattern 7).
- **spec decision:** ink / ground / hair hex values are the overlay's own `INK`/`BG`/`NEUT` (overlay.js:82-83) plus one panel and one hairline per theme — nothing here is a colour the chart does not already use.
- **spec decision:** `cadence_s` = tape 1, chain 12, depth 15, chart 5, record 300, senses 5 — chain at 12 s wraps the ~10.5 s poll without flapping, and a quiet market genuinely writes no record row for minutes.
- **spec decision:** `never started` is the record writer's level when `rows_today == 0` and the file is absent — an age ladder cannot express "was never alive".
- **spec decision:** `/api/series` tops out at SHAK — `NAHI` needs a kill rule that exists and fires, and none is written, so the state is named rather than left undefined.
- **spec decision:** `gate.state` keeps arity 5 plus an optional `ivrv_why`, and `event` uses `None` vs `{}` to separate "not checked" from "checked, clear" — one argument, two meanings, no second boolean.
- **spec decision:** `sig(fr, row=5.0)` takes `rowSize` as an argument because the built frame does not carry it — server.py:1128 passes the same `float(doc.get("rowSize") or 5)` frame.py:247 already uses.
- **spec decision:** `record_read` caches by `(path, mtime, size)` and streams line by line — a 116 MB file must never be read into memory on a 10 s poll.
- **spec decision:** at the 5 m window the four-state word moves to the rail line — the information is not lost when the texture collapses to two.
- **spec decision:** `book.json` absent renders nothing, not a hole — a candidate book she has not entered is not missing data, and a `PATA NAHI` there is noise on the 09:14 screen.
- **spec decision:** `5` and `?` are toggles and `Esc` also closes — one key in, one key out, no modal trap.
