# BOARD rev 3: design note, 2026-09-24

**Mockup:** `board-chess-rev3-2026-09-24.html` (self-contained, about 10.5 MB, light only, no storage). It
replays **both** days from the record: **Thu 2026-09-24** (the trend day) and **Wed 2026-09-23** (the
range day), for all three indices. It opens on 09-24 NIFTY 12:35. Its URL takes `?day=`, `?idx=` and
`?t=HH:MM|close`.

**Nothing in the repo changed** apart from this file and the notes. No `ui-v2/src`, no `.py`, no
extension and no `data/` file was touched. The server was not restarted, and only GET calls were made:
the TapeMap GET endpoints, plus Upstox GET candles read through TapeMap's own `upstox_feed.read_token()`
and `upstox_rest.UA`. The token was never printed.

**Generator:** in the session scratchpad (`…/fbeb76c4-…/scratchpad/`). It runs:
- `cap24.py`, a GET capture of the live server;
- `fetch_up.py`, which reads Upstox index candles and the deep-OTM legs;
- `fetch_mirror.py`, which reads Upstox for ATM ±2 option legs and the future;
- `g1.py` and `g2.py`, rev 1 and rev 2's generators parameterised by day;
- `g3.py`, the rev 3 layer;
- `rev3_template.html`, rendered by `render_rev3.py`.

The rules are called from the repo's pure modules and never copied: `fronts`, `grounds`, `ladder`,
`runs`, `contract_bars.vwap_sigma` and `live._floor_pivots`.

**Her rule arrived mid-build and reshaped the page:** *"i dont want them as chart on my screen at all
because i have them on my broker screen."*
- The price path, the CVD line and every candle are gone.
- The board now **reads** her charts for her instead of redrawing them, through the mirror read and
  the trend box.
- It shows what a broker chart cannot: OI, the fronts, the folds, the defended levels, deep OTM and
  agreement.
- The only drawn series left are OI (the book, the 5-minute ΔOI bars and the deep-OTM lines), because
  OI is not on her broker screen.

---

## 1. Size, measured

| what | value |
|---|---|
| The board (the Board tab area) | **1536 × 577**, fixed and never scaled. Verified at 1536 × 695 CSS px, DPR 1, light. |
| The strip above it | A **GlanceBar stand-in** (44 px) with index switching and the three mini-ladders, as rev 2's wiring item 1 asks. It also carries the mockup-only controls: day switch, scrubber and frozen moments. In the app, these live in the real GlanceBar (72 px) and replay bar: 72 + tab strip 46 + 577 = 695. |
| Overflow check | 749 renders (every 3rd minute × 3 indices × 2 days) plus the 18 frozen-moment renders. **0 JS errors, 0 panels or cards overflowing, body width 1536.** Long single lines end in an ellipsis and carry the full text as a tooltip. |

## 2. What the eye reads, in order

```
┌ GLANCEBAR: NIFTY ▤ fold PE 23,200 12:33 · ▼ BREAKING │ BANKNIFTY ▤ … │ SENSEX ▤ … │ (mockup: day · scrub · moments) ┐
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1  Sellers leaning · PE 23,200 (ITM 27) folded 12:33, 11% off its 12:31 high · next put wall PE 23,150 …  22px │
│ 2  LEVEL UNDER ATTACK [DRAFT] ▼ PE 23,200 [BREAKING] spot 27 below · 3 of 3 attack facts: …  ▲ CE 23,200 [HOLDING] │
│ 2  ▼ DOWN · 4 of 5 agree [I] │ OI ▼ … │ CVD ▼ … │ FLOW ▼ … │ TAPE · … │ TREND ▼ …   (a count, not odds)        │
│    FOLDS puts 23,250 11:14 → … → 23,200 12:33 · calls … · FIRST FOLD … · ENGINE (small) … → BACKED/CONTRADICTED  11px │
├ 3 THE BOOK (the board) ───────┬ THE PIECES (4) ──┬ WHAT CAN HAPPEN ─────────────┬ THE MIRROR READ ─────────────┤
│ fold    CE ◄│strike│► PE  fold│ CE #1 · CE #2    │ ▲ UP TO … [level chip]      │ chips 23,100…23,300 ATM      │
│ 12:31→  ▮today ▯carried  │high│ PE #1 · PE #2    │ WHO PAYS / PAYING NOW? /    │ CE z · band · pivots         │
│ □ top 2 · ▭ defended level    │ ITM/OTM · TODAY/ │ PRESSING? / AT THE LEVEL /  │ PE z · band · pivots         │
│ level tags PDH·PDC·OPEN·H·L·d2 │ CARRIED · nearer │ REFUSED IF · ▼ DOWN TO …    │ VS FUTURES confirms/diverges │
│ - - spot · her nine shaded     │ ⚑ gate defender  │ FADE u2 · FADE d2 (§1d)     ├ TREND (floating, docked) ────┤
│                                │                  │                             │ 1m…D rows · REGIME · STRONG   │
├ THE OI CLOCK: ΔOI per 5 min (followed strikes) · flush? draft · deep OTM per side ┬ MOVES: last 4 · full log ▸ ─┤
└ provenance · amber disclosures ───────────────────────────────────────────────────────────────────────────────────┘
```

1. **First, the sentence (22 px).** It names who is pressing (rev 2's size floor kept), then **the latest
   front near spot to fold**, with ITM/OTM, how far it is off its high and its high time. Then comes
   who defends next on that side.
2. **Second, the threat and the count.**
   - The LEVEL UNDER ATTACK line gives each defended level's state, drawn as geometry: HOLDING solid,
     TESTED dashed, BREAKING hatched. It is marked **DRAFT**.
   - The agreement row counts five evidence families, each with its fact and its doubt. It is stated as
     *a count, not odds*.
   - The engine's own words drop to the 11 px story line with their grounding status.
3. **Third, the book: the chessboard.**
   - CE bars run left and PE bars right, absolute OI now. **Carried in** (OI at the open) is light and
     **built today** is solid, so a gap day's new walls stand out from the legacy ones at a glance.
   - │ marks the session high, and □ boxes the top 2 with their rank.
   - The **defended level is framed** on its strike.
   - The **latest fold** of each strike-side is printed at the edge (high → first §1d unwinding), so the
     staircase reads straight down the put side.
   - Levels (PDH/PDC/PDL/OPEN/PWH/PWL, the day's H/L, her d2/u2 pockets) are tags on the strike rows.
     No price series is drawn.
   - Clicking a strike follows it or drops it.
4. **Then:** the pieces, the squares, the mirror read, the trend box, and the OI clock and moves at the
   bottom.

## 3. The nine points

| # | ask | how rev 3 does it |
|---|---|---|
| 1 | Headline = the latest front forced near spot; never a never-built front; engine words small | The headline takes the latest **fold** that is still folded and near spot. The fold rule (§6.1) needs a sized positive build, so PE 23,000 (−13.5L from the open) can never headline. The engine's verdict and its status sit in 11 px in the story line; on 09-24 it comes from `data/calls/`. |
| 2 | Built today vs carried in; both top 2; which is nearer; the defender honestly | Every front card and every ladder bar splits into **carried in** (OI at the open) and **built today**. The card chip reads TODAY nn% or CARRIED nn% or NEVER BUILT. The nearer of each side's two is marked. The #1 card carries **⚑ GATE DEFENDER** and says in amber when it is *never built today* or *the farther wall, N pts; the nearer is … (#2, state)*. §1d's ranking is untouched: the gate still ranks by session-peak absolute OI. |
| 3 | The OI clock: folded stamps, deep-OTM strip, flush draft, PCR demoted | **Folds** show on the book edges, in the story line (FOLDS puts … → … · calls …) and in the moves list, each stamped once. The **deep OTM** is 10 strikes beyond the server's ±8 grid on each side, Upstox 1-min OI, drawn as two lines of change since the open. **Flush?** is a dashed amber band on the ΔOI lane, labelled DRAFT. **PCR** is text only, labelled *drifts, no timing*. |
| 4 | Level under attack, DRAFT | See §6.4 for the draft. It shows in the answer's second line, as the chip on each square, as the frame on the book and in the moves (◈, tagged draft). §4 gives the 12:24–12:34 read. |
| 5 | Floating trend box | It is docked in the right rail's slot, **draggable** by its title bar, **collapsible** to one line (`1m▼ 3m▼ 5m▼ 15m▼ 1h▼ 4h· D▼ · TREND DOWN · BEARS`) and double-click docks it. It is text only, with no sparklines. Its definitions are in §6.6 and in its title tooltip. |
| 6 | Confidence = agreement, not a probability | *▼ DOWN · 4 of 5 agree · 0 against · 0 not read · a count, not odds.* Each family shows its vote (▲ ▼ · ?), its fact and its doubt (§6.5). Nothing is a percentage. A measured confidence waits for ~30 sessions of the calls log. |
| 7 | Strike selection like OI Flow | On the book, **the strike label is the chip**. The default is **her nine** (the nine nearest spot, moving with it). Clicking makes an explicit set (brass wash), and "nine ⟲" resets it. The set drives the book's ink, the fold stamps and the OI clock's ΔOI bars. The mirror read has its own chips (ATM ±2, default ATM). |
| 8 | Not biased to one day | The day switch holds 09-24 and 09-23. Frozen moments are 09-24 12:24 / 12:30 / 12:35 / 13:30 and 09-23 13:36 / close. The same rules read the two days differently (§5). |
| 9 | Size | 1536 × 577, real size, never scaled (§1). |

## 4. What the board says at 12:24–12:34 on 09-24 (NIFTY), the "knows early" moment

These are read off the rendered page, minute by minute.

| min | spot | headline (22 px) | level under attack (draft) | agreement | engine (small) |
|---|---|---|---|---|---|
| 12:20 | 23,201 | Nobody pressing · CE 23,300 stopped building at 12:00 · PE 23,200 (OTM 1) still adding (+44.5L) · no fold near spot yet | ▼ PE 23,200 **TESTED**, 1 of 3: initiative sellers 12:10 @ 23,201 | ▼ 3 of 5, 1 against | WAIT … CONTRADICTED |
| 12:24 | 23,195 | Nobody pressing · PE 23,250 (ITM 55) folded 11:14 · next put wall PE 23,200 (at spot) stopped adding | ▼ PE 23,200 **TESTED**, 2 of 3: stopped adding at its 12:23 high · initiative sellers 12:10 | ▼ 3 of 5 | WAIT … CONTRADICTED |
| 12:30 | 23,188 | same, with PE 23,200 still adding | ▼ **HOLDING** (it is adding to its 12:31 high; the 12:10 print aged out) | ▼ 2 of 5, 1 against (OI) | WAIT … CONTRADICTED |
| **12:33** | 23,175 | **PE 23,200 (ITM 25) folded 12:33, 11% off its 12:31 high** · next put wall PE 23,150 stopped adding | ▼ **TESTED**, 1 of 3: PE 23,200 giving back | ▼ 2 of 5 | WAIT … CONTRADICTED |
| 12:34 | 23,176 | same | TESTED. The mirror reads PE 23,200 z +2.3 (+2σ…+3σ), CE z −1.9; fut new low 12:30 → **CONFIRMS** | ▼ 2 of 5 | WAIT … CONTRADICTED |
| **12:35** | 23,173 | **Sellers leaning** · PE 23,200 folded 12:33 … | ▼ **BREAKING, 3 of 3**: giving back · initiative sellers 12:30 @ 23,200 · sellers leaning, price following | **▼ 4 of 5**; trend box REGIME **TREND DOWN**, STRONG **BEARS** | GO — one-sided tape → BACKED |

**What this shows.**
- §1d read PE 23,200 **UNWINDING at 12:33**, two minutes after its high, because the falling 15-minute
  slope cleared 5% of its high.
- The live board headlined PE 23,000 throughout. PE 23,200 appeared only in its small detail line, and
  0j.2 caught the UNWINDING read by hand at 12:47.
- Rev 3 names it in the 22 px line at 12:33, and the defended level reads BREAKING at 12:35.
- The 12:30–12:34 lag is real: the CVD and footprint facts sit on 5-min bars, and the 12:30 bar closes
  at 12:35. It is the rule's latency, not a display choice.

**Honest caveats, n = 1, a description only.**
- The same draft also read **BREAKING at 11:35–11:36**, 55 minutes early. The floor was swept at 11:55
  and held until 12:30.
- As drafted, TESTED covers much of the session.

## 5. The four frozen moments, and why the design is not tuned to one day

- **09-24 12:30.** HOLDING at PE 23,200 and ▼ 2 of 5. The trend box reads BEARS 5/7 with the regime NOT
  AGREED (price says TREND DOWN, but OI says TREND UP because the put side is still writing).
- **09-24 13:30.** *Sellers pressing · PE 23,150 (OTM 1) folded 13:27, 21% off its 13:23 high · no sized
  put build below spot inside the nine.*
  - ▼ PE 23,200 BREAKING; ▼ 4 of 5; REGIME TREND DOWN; BEARS.
  - The flush? draft is marked at 13:25 (grid −29.5L in 5 min, deep puts falling).
  - Mirror: fut new low 13:25 → CONFIRMS (PE new high, CE new low).
  - Engine: GO → BACKED.
- **09-23 13:36.** *Sellers pressing · PE 23,450 (ITM 30) folded 13:36 · next put wall PE 23,400 (at spot)
  stopped adding.*
  - Both levels TESTED; ▼ 2 of 5 with **TAPE ▲ against**.
  - The trend box reads **NEITHER** (2 down, 1 up, 4 range) and the regime **NOT AGREED (CHOP / both
    leaving)**.
  - Mirror: CE +0.1σ, PE −0.7σ around VWAP.
  - The engine was not recorded (calls were first logged 09-24), and the page says so.
- **09-23 close, drawn to 15:26** (the 15:27 re-baseline is disclosed in amber). *Nobody pressing · CE
  23,450 (OTM 19) folded 14:30.* NEITHER, NOT AGREED, and a flush? draft at 15:10 (a closing unwind; see
  §7).

**Across whole days** (NIFTY, minutes):

| read | 09-24 | 09-23 |
|---|---|---|
| STRONG BEARS | 240 | 0 |
| STRONG BULLS | 0 | 56 |
| STRONG NEITHER | 134 | 316 |
| regime TREND DOWN | 32 | 0 |
| regime PIN/CHOP | 5 | 46 |

The same rules read the trend day as a trend and the range day as a range.

## 6. Exact definitions (all display rules, [I], fixed before either day was read through them)

### 6.1 Fold [M on §1d]

A strike is a fold when:
- it is inside §1d's nine at that minute;
- its build is sized, meaning its high change since 09:15 is > 0 and ≥ 15% of the biggest build on its
  side inside the nine (rev 1's size rule);
- `fronts._state` reads it UNWINDING for the first time after that high.

The fold is stamped at that minute and never re-decided. A new high re-arms it. FIRST FOLD is the day's
first fold of a §1d top-2 front, stamped once.

### 6.2 Headline (0j.2)

- It opens with the aggression clause, carrying rev 2's P2 floor (grounds' CVD rank ≥ .5 AND its flow
  rule, ≥2 prints and 2× the other side).
- It then names **the latest fold still folded**: no new high since, and §1d not reading it BUILDING.
- The fold must be **near spot**, meaning within one strike of spot or ITM (spot through the strike on
  the writers' losing side).
- The headline adds *next {put|call} wall*: the nearest sized, unfolded build on that side, within one
  strike or beyond spot, with its §1d state.
- If there is no near fold, it names the nearer of each side's top 2, and never one that never built.

### 6.3 Built today vs carried in [M]

- open = absolute OI − change since 09:15;
- share = high build ÷ (open + high build);
- **TODAY** when share ≥ 50%, **CARRIED** when it is under 50%, **NEVER BUILT** when the high build is
  ≤ 0.

The defender flags are *never built today* (a high build ≤ 0) and *the farther wall* (the #1 is not the
nearer of the two).

### 6.4 LEVEL UNDER ATTACK, DRAFT (pending her pre-registration, gates nothing)

**The level.**
- For DOWN it is the §1d top-2 PE front with the highest strike ≤ spot + 1 strike.
- For UP it is the top-2 CE front with the lowest strike ≥ spot − 1 strike.
- It is **in contact** when |spot − level| ≤ 1 strike. Otherwise it reads NO CONTACT.

**Three attack facts.**
1. **OI:** the defender is STALLED or UNWINDING by §1d, or never built.
2. **Tape at the level, last 15 min:** an initiative print or a stacked imbalance in the attack
   direction within ½ strike of the level. It is read in futures prices shifted by that bar's basis,
   from GoCharting and TapeMap marks plus both tapes' stacks. The hold side is absorption or exhaustion
   on the defending side.
3. **CVD against price:** the attack side is pressing by the P2 floor AND the 15-min price change is
   the same sign. If pressing but price does not follow, it reads *absorbed*.

**States.**
- **BREAKING:** the defender is UNWINDING AND the tape or CVD attacks.
- **TESTED:** any attack fact.
- **HOLDING:** in contact, with none.

### 6.5 Agreement

It counts five families: ▲ up, ▼ down, · no vote, ? could not check.

| family | votes when | source |
|---|---|---|
| **OI** [M] | ▼ when the nearer PE front is not writing and the nearer CE is; ▲ mirrored; no vote when both sides write or neither does | §1d |
| **CVD** [I] | sign of grounds' 15-min CVD at rank ≥ .5 | grounds' own family rule |
| **FLOW** [I] | grounds' dominance rule | grounds |
| **TAPE** [I] | footprint events in 15 min (initiative/absorption/exhaustion by their bull/bear side), ≥2 and 2× | NIFTY only; *could not check* on BANKNIFTY/SENSEX, which have no footprint marks |
| **TREND** [I] | the box's STRONG | the trend box |

The head is the larger side: *n of 5 agree · k against · m not read*. Never a probability.

### 6.6 The trend box (on the INDEX's own Upstox candles; the forming bar is never used)

**Rows: 1m, 3m, 5m, 15m, 1h, 4h, D.**
- Intraday bars are aligned to 09:15 and run across sessions, so the overnight gap is inside the window.
- 1h is 09:15–10:14 … 15:15–15:29.
- 4h is 09:15–13:14 and 13:15–15:29.

**Each row uses 20 closed bars.**
- **POS** = (price now − 20-bar mean) / 20-bar σ. It reads up at ≥ +1, down at ≤ −1.
- **SWINGS** = the last two pivot highs and lows, where a pivot beats the 2 bars either side. HH·HL is
  up, LH·LL is down, and anything else is mixed.
- **SLOPE** = the least-squares line through the 20 closes, its rise across the window ÷ σ. It reads up
  at ≥ +1 and down at ≤ −1.
- A row is **UP** when ≥ 2 of the 3 say up and none says down (DOWN is mirrored). Otherwise it is
  **RANGE**. With fewer than 20 bars, it is *forming*.

**REGIME.**
- **TREND** when the 5m, 15m and 1h rows all point one way **and** OI agrees (the nearer §1d front on one
  side has stopped while the other side writes, which is §6.5's OI read).
- **PIN / CHOP** when two of those three rows read RANGE **and** both sides' nearer fronts are writing.
- Otherwise **NOT AGREED**, with both halves printed.

**STRONG.**
- **BULLS** at ≥ 4 UP rows and ≤ 1 DOWN;
- **BEARS** mirrored;
- otherwise **NEITHER**, with the counts.

**Why the index and not futures VWAP.** The index prints no volume, so a VWAP needs the future. Futures
roll and expire (the SENSEX near future expired 09-24). The 20-bar mean ±σ is the same band shape and has
one definition on all three indices.

### 6.7 The mirror read (the coordinator's addition)

- **z** = (the premium's last closed 5-min close − its session VWAP) / σ, and the band it sits in. The
  band is `contract_bars.vwap_sigma` over 1-min rows, sampled at each bar's last minute, which is
  **exactly** what `/api/contract` serves. This was checked against a live payload (CE/PE 23,100, 09-24).
- **Pivots:** `live._floor_pivots` on the leg's prior session, giving the nearest P/R1–3/S1–3 above and
  below.
- **VS FUTURES [I]** looks at the futures' latest new session low (or high). It asks whether the PE
  printed a new session high and the CE a new session low in the same 5-min bar (mirrored for highs).
  - Both yes reads CONFIRMS, both no reads DIVERGES (*put buyers not paying up*), and one of each reads
    SPLIT.
  - This is her reading as she states it, drafted, not registered.

### 6.8 Flush? DRAFT (her proposed rule, pending pre-registration, gates nothing)

A 5-minute bar from 09:30 on is marked when **all three** hold:
1. the whole grid's OI change in that bar is the most negative of the session so far;
2. deep-OTM OI on either side also fell in that bar;
3. a fold was stamped inside the previous 60 min ("after a break").

There is deliberately **no size threshold**. That number is hers.

### 6.9 Deep OTM and PCR

**Deep OTM [M]:** 10 strikes beyond the server's own ±8 grid on each side, on the nearest live expiry,
from Upstox 1-min OI, forward-filled. For NIFTY 09-24 the puts are 22,350–22,800: 331.1L at 13:25 →
318.5L at 13:50. 0j.7 used 22,300–22,800 and got 358.8 → 343.3; it is the same shape on a different set.

**PCR [M]** is ΣPE / ΣCE absolute OI on the ±8 grid, text only.

## 7. What needs her pre-registration before it may gate anything

1. **Level under attack.** Display and forward-log only; §5 stop rule, no backtest. As drafted:
   - TESTED fires most of each session, because a STALLED defender counts as an attack.
   - BREAKING fires in bursts: NIFTY 09-24 39 minutes, first at **11:35**; 09-23 12 (down) + 26 (up).

   Hers to fix:
   - does STALLED count?
   - how long must BREAKING persist?
   - is contact one strike?
   - the falsifier.
2. **Flush candle.** As drafted it fires 3–6 times per index-day:
   - NIFTY 09-24: 10:40, 11:05, **13:25**.
   - NIFTY 09-23: 11:05, 11:30, 12:00, 15:10, including closing unwinds.

   Hers to fix: a size threshold (13:25 was −29.5L against −7.4L at 10:40), the deep-OTM confirmation
   window, a time-of-day cut, and the falsifier.
3. **Anything that could gate:**
   - the headline's near-spot filter;
   - the OI vote;
   - the regime;
   - the mirror's CONFIRMS/DIVERGES.

   All are display-only [I]. None may feed `setup.gate`, the zone machine or trigger_log without a §1d-
   style pre-registration.
4. **Forced / released** stays an empty, labelled slot. She said yes, then **held** the addendum.
   - The headline's "ITM or within a strike" filter is a snapshot of the price relation, not her
     classifier.
   - If she registers the addendum, it replaces that filter.
5. **§1d is unchanged.** Near = nine strikes, top 2 by session-peak absolute OI, 15% / ±5% / 15 marks.
   The 0j.4 options (a)/(b)/(c) are still hers. The page only *describes* the defender.

## 8. Wiring plan, smallest first

1. **Shell (ui-v2, Board tab only).** Hide the global answer band and the MACHINE strip. Index switching
   and the mini-ladders go into the GlanceBar. Without this, nothing fits (rev 2 §1).
2. **`/api/oihist` `+open`** per strike (`oi − chg`, one subtraction). The book's carried/built split is
   then client-side.
3. **`fronts.folds(minutes)`**, a pure function of about 40 lines reusing `_state`. It serves the
   staircase, the headline's fold and FIRST. It rides on `/api/oihist`. **FIRST is persisted in
   `day_state`** (anytime-start).
4. **A pure `board.py`:**
   - the headline;
   - built share, nearer and defender flags;
   - the agreement over `/api/calls` facts plus `/api/tape` marks plus the trend rows;
   - PCR.

   It is one function per minute, testable on the fixture.
5. **Trend box, `trendbox.py` (pure) plus REST.** It is fed by:
   - `upstox_rest.intraday(index_key, tok, "1minute")` once a minute per index;
   - `upstox_rest.historical(index_key, tok, prior_day, "1minute")` once a day;
   - `upstox_rest.daily_range(index_key, tok, frm, to, "30minute")` and `…"day"` once a day, cached as
     `levels.py` already does.

   The endpoints are `/v2/historical-candle/intraday/{key}/1minute`,
   `/v2/historical-candle/{key}/1minute/{d}/{d}`, `/v2/historical-candle/{key}/30minute/{to}/{from}` and
   `/v2/historical-candle/{key}/day/{to}/{from}`. REST backfill is exact, so a 13:00 start reads like a
   09:15 one.
6. **Mirror read.** `/api/contract` already serves the legs, bands, pivots and `index_series`; the read
   is about 60 lines, client-side or in `board.py`. **Fix first:** `live._opt_pivots` builds H/L/C from
   prior-day candles through ~15:39. By the house rule it should stop at 15:29. On PE 23,100: server
   L 17.7 / C 18.35 against in-session 19.35 / 19.65. The mockup uses the in-session values.
7. **Deep OTM.** Take 20 legs per index beyond the grid, from `upstox_rest.intraday` every 5 min (20
   calls per index) or subscribed on the socket in full mode (inside the 2,000-key budget). The OI per
   candle makes the backfill exact.
8. **Only after she registers them:** level-under-attack and flush. Forward-log them to a new
   `data/board/board_<day>.jsonl` (gzipped by daylog, nothing after 15:30) so each gets a kill clock.

## 9. Found on the way (checked, not fixed)

- **The server's 09:15 baseline differs from Upstox's finished 09:15 candle on 9 of 34 NIFTY legs**
  (09-24), all near the money: PE 23,300 92.1L against 86.0L, and PE 23,350 +28%. The baseline is read
  inside the first minute.
  - Result: PE 23,300's 09:41 high (raw) sits **under** the server's baseline, so on the server's grid PE
    23,300 never built.
  - The board's put staircase is therefore **23,250 (11:04 → 11:14) → 23,200 (12:31 → 12:33) → 23,150
    (13:23 → 13:27)**, not 0j.7's "23,300 09:41 → …".
  - Which baseline §1d means is a data question to settle before wiring.
- **The calls log disagrees with 0j.5's timing.** The engine verdict read *GO — one-sided tape / dealer
  hedging amplifies* **BACKED** on the 12:33–12:45 bars. It went back to WAIT at 12:48–12:51 and
  13:00–13:24, then GO again from 13:27. 0j.5's "GO first appeared at 13:27" matches a different string
  (the headline's "GO — MOVE RUNNING DOWN"). The engine flickered; demoting it still stands.
- **Rev 2's re-baseline check fired falsely on BANKNIFTY 09-24.** One leg (55,100 CE) moved ±60 all day.
  Rev 3's check needs ≥3 legs in one minute; 09-23 NIFTY 15:27 (11 legs) is still caught.
- **Rev 2's FIRST stamped a never-built front on 09-24** (PE 23,300, peak 0 at 09:15, stamped 09:31),
  which is the 0j.2 defect in rev 2 itself. Rev 3's FIRST needs a sized positive build.
- **SENSEX 09-24 was its weekly expiry day** (and its near future's). Its OI reads are expiry-day reads.
- **BANKNIFTY and SENSEX have no footprint marks** (the extension charts NIFTY only), so TAPE reads *could
  not check* there.

## 10. Where I disagree with the brief

1. **"Forced" stays off the face.** The forced/released addendum is held. The headline says *folded* and
   shows ITM/OTM. "Near spot" (one strike, or ITM) is my display rule, flagged in §7.4.
2. **The staircase in the brief is raw-Upstox, not the server's grid** (§9). The board shows the
   server's, because that is what §1d runs on.
3. **Level under attack is not yet a clean early warning.** It did say BREAKING at 12:35. It also said so
   at 11:35 while the floor held, and TESTED is common. I left it untuned. The persistence and threshold
   are hers to register, not mine to fit on the day it worked.
4. **"n of 5 agree" overstates independence.**
   - FLOW already counts stacked imbalances.
   - TREND is price, which CVD partly tracks.
   - On BANKNIFTY/SENSEX, TAPE is unreadable.

   I keep the count because she asked for it, print each family's source and doubt, and never call it
   confidence.
5. **The trend box uses the index's 20-bar mean ±σ, not VWAP** (§6.6).
6. **The ±8 grid is the limit of "wherever we have OI data".** The chips can only follow strikes the
   server records. Rows beyond it show as amber dashed boxes: *could not check*.

## 11. Element → source, and M or I

| element | live source | tag |
|---|---|---|
| headline, next wall, fold stamps, FIRST | `/api/oihist` minutes + `fronts._state` (**new** `folds`, `board.py`) | [M] on §1d, wording [I] |
| book bars, high, top 2, carried/built | `/api/oihist` `peak`, `fronts`, chain record abs OI, **new** `open` | [M] |
| level tags | `/api/warmap` levels, the day's H/L, `/api/frame` zone (NIFTY) | [M] |
| fronts cards, defender flags | `fronts.read` + **new** extras | [M] facts, flags [I] |
| level under attack | fronts + `/api/tape` marks/stacks + `/api/calls` facts | **DRAFT [I]** |
| agreement | `/api/calls` facts, `/api/tape` marks, trend box | [I] |
| engine words | `/api/calls` (recorded since 09-24) | status [I] |
| fade lines | `fronts.fade_gate` with the recorded plays | [I] |
| OI clock ΔOI, PCR | chain grid | [M] |
| deep OTM | Upstox 1-min candles (**new** poll) | [M] |
| flush? | grid + deep + folds | **DRAFT [I]** |
| mirror read | `/api/contract` legs, bands, pivots, `index_series` | z / pivots [M], confirm [I] |
| trend box | Upstox index candles (**new**) | [I] |
| moves | rev 2's composition + folds + drafts | per row |
