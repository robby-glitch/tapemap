# Board overhaul — 2026-10-03 (round 1)

Mary, 2026-10-03: *"the board … its shit to be honest … so much data it hardly make any sense or tell any
thing … i need complete overhaul"*, and in the same message: *"oi flow is the only thing here i like because
that works actually."*

Built as `ui-v2/src/board/Board.tsx`, mounted on the Board tab. `BoardRev3.tsx` stays on disk, unmounted, for
comparison; its `useBoardGlance` still feeds the GlanceBar.

## Why OI Flow works for her, and what carries over

OI Flow is plain, runs in time order, has one word per row and uses the strikes she picks. The old Board was
the opposite: a 15-strike ladder, 4 cards, 2 six-row "squares", 5 lamps, a mirror read, a 7-row trend box, a
75-bar clock and a log. That is about 300 numbers in one screen, and most rows said "could not check" whenever
the GoCharting extension was off.

What carries over: **time order, one word per piece, her strikes** (the four §1d fronts), and honest absence.
What does not: OI Flow's summed BULLISH/BEARISH. She reads OI at the strike, not summed, so the Board does not
duplicate it.

## The one job

**In one look: which side's near-money writers stopped first and are giving OI back (by her §1d rule, the fuel),
and where the next reaction point is each way.**

That is her chess board:
- **what has happened** is each front's day, build → stop → give back, with the peak time stamped;
- **what is happening** is each front's state now;
- **what can happen** is the next retail reaction point up and down, and which writers stand between price and it.

## On screen, top to bottom

| # | piece | the decision it serves |
|---|---|---|
| 1 | **THE READ.** One Hinglish verdict, e.g. `PUT WRITERS CHHOD RAHE HAIN`, with a fuel chip `▼ fuel neeche · 10:41` | Which side to stand with. Her rule: the side that stops first, then gives back, is forced, and that is the fuel. |
| 2 | One English fact line about the leading front: when it stopped, since when it is giving back, how much was built and how much is left, and **how far price moved against or for those writers since their peak** | Is it real? Price moving *against* them is the squeeze. Price moving *in their favour* while they give back looks like profit-taking. The forced/released rule is hers (§1d addendum, held), so this is shown as a fact and not judged. |
| 3 | **The count**, per side over the four fronts: e.g. `PUT: 2 chhod rahe · CALL: 1 ruka · 1 likh raha` | Confidence, as a count of agreeing pieces. Never a %. |
| 4 | **Agli ladai upar / neeche** chips: the next reaction point each way, with label and distance | Where price travels next (her thesis: PDH/PDL, weekly H/L, round numbers). |
| 5 | **THE BOARD.** Rows in price order: the next 2 levels above spot, the four fronts, the spot line, the next 2 levels below spot. Each front row shows its side and strike, ITM/OTM, built today vs carried in, an OI sparkline 09:15→15:30 (OI built since the open), the peak stamped `ruka HH:MM` with the given-back wedge after it, and its state now in Hinglish plus English | The pieces where they stand. Below the spot line a CE front means call writers are in the money, and empty space between spot and a level is an open runway. The time axis shows who stopped first. |
| 6 | **KRAM** (right column): the four fronts' stamps in time order, newest first, and the day's first leaver | OI Flow's virtue: plain, one word per row, in time order. |
| 7 | Footer: as of, grid coverage, the rule, and what is *not shown* | The three absences kept apart. |

**Verdict rule** (display [I] on §1d's own states; it calls nothing new):
- The leader is `fronts.broke` restricted to fronts that **built today** (peak > 0). That is the same filter
  `board.py`'s headline uses (rule 0j.2, "never a never-built front").
- Among them, the UNWINDING front with the earliest peak leads; if none is unwinding, the STALLED front with the
  earliest peak leads.
- A leader that is UNWINDING gives `… CHHOD RAHE HAIN` and the fuel chip (`▼ fuel neeche · HH:MM`, with the peak
  stamp).
- A leader that is only STALLED gives `… RUK GAYE`, and the chip says *watch* (`dekho · wapas dein to fuel neeche`),
  not fuel.
- When **both sides are at the same step**, it gives `DONO TARAF CHHOD RAHE` / `DONO TARAF RUK GAYE`. The chip is
  then neutral, `pehle PUT 10:41 · phir CALL 13:58`, and the fact line gives both sides.
  - Why: on 1 Oct the puts broke at 10:41 and the market fell ~300 pts to 22,258. Then the call writers, who had
    built 70–77% of their OI *today* on the way down, peaked at 13:58/14:24 and were squeezed by a 163-pt bounce
    into the close.
  - A red "fuel neeche" chip at 15:00 would have pointed at the spent side. The rule still names the earlier stamp
    first; the Board only declines to turn two facts into one arrow.
- No leader gives `DONO TARAF LIKH RAHE HAIN` (`koi nahi toota`).

A front that is BUILDING but at least 5% under its own peak reads `PHIR LIKH RAHE` ("adding again"), never "still
adding". That is the same 5% `board.paying` uses (Fable P1, 2026-09-28 audit bug 5).

**Levels used** for "agli ladai": PDH, PDL, PWH and PWL from `/api/warmap`, major round numbers from
`/api/warmap` (NIFTY 100, BANKNIFTY and SENSEX 500, from `levels.ROUND_STEPS`), and the day's high and low on the
grid's minute marks.
- Minor rounds (NIFTY 50s) are left out because they are every strike: the next one is always within 50 points
  and says nothing.
- OPEN and PDC are left out because they are not on her list.
- Max pain, GEX and the chain walls are left out because they are aggregates against her rule.

## Dropped from the old Board, and why

| old piece | why it went |
|---|---|
| THE BOOK (15 strikes × CE/PE bars, tags, chips) | All-strike data. Her rule is the top 2 per side near the money, and the four front rows *are* those, placed by price. |
| Rail cards, ⚑ GATE DEFENDER | Merged into the front rows. The §1d gate is the DESK's and Signals' business; the Board describes. |
| WHAT CAN HAPPEN squares (6 rows × 2: WHO PAYS / PAYING / PRESSING / AT THE LEVEL / REFUSED IF) | Collapsed into the level chips and level rows. PRESSING (CVD/flow) mostly read "could not check" off-extension, and the DESK carries order flow. "AT THE LEVEL" was a permanent "not shown". |
| Agreement, 5 lamps (OI/CVD/FLOW/TAPE/TREND) | Mixed families, mostly "could not check", and it changed every minute. Replaced by the count of her four fronts. |
| Mirror read (premium vs VWAP σ, pivots) | Premium is on her broker screen and the DESK. It updates constantly and decides nothing here. |
| Trend box (7 timeframes) | A price trend; she has charts. |
| OI clock (ΔOI per 5 min, 9 strikes summed) | An aggregate. The per-front sparklines show the same build and give-back at her strikes. |
| MOVES and the full log of folds (54 on 1 Oct) | Noise. KRAM keeps only the four pieces' stamps plus the day's first leaver. |
| PCR | An aggregate: "drifts, no timing". |
| The headline sentence | It said "folded", which is the DESK's exit word. Replaced by the verdict built from the same §1d states. |
| `/api/frame` d2/u2 pockets | They used the 5-min bands, not her 3-min zone. The zone lives on the MACHINE strip and the DESK. |

**Words.** The Board never says FOLD. It uses `ruka` (stopped adding), `chhodne lage` / `chhod rahe` (giving back),
`aaj sabse pehle chhoda` (the day's first to give back), and `likh rahe` (writing).

## Endpoint → piece (all existing; no backend change)

| piece | source |
|---|---|
| verdict, count, fact line, front rows (state, `peak_at`, `unwind_at`, `chg`, `peak`, `peak_spot`, `itm`, `built`/`share`, `open`, `now_oi`), the day's first leaver | `/api/board?idx=` → `fronts[]`, `first`, `asof`, `spot`, `step`, `grid`, `ok`/`why`, `not_shown` |
| sparklines, the day's high/low | `/api/oihist?idx=` → `minutes` (change since the open per strike and minute), cut to `board.asof` |
| levels | `/api/warmap?idx=` → `indices[idx].levels` (PDH/PDL/PWH/PWL, ROUND with `major`), `ok`/`why`/`daily_why` |

Polls: board 20 s, oihist 30 s, warmap 60 s (the old Board's rates), paused while the browser tab is hidden.

## Checked against three sessions (round 1)

Each payload was rebuilt from `data/chain/` through `fronts.read` / `board.read`, the functions the server calls.
The PDH/PDL/PWH/PWL in those fixtures are the prior sessions' chain spot highs and lows, an approximation; the rounds
are `levels.round_levels`. Screens were taken at her CSS viewport, 1229 wide, in `docs/board/`.

| shot | session | what the Board said | what happened after |
|---|---|---|---|
| 02 | NIFTY 1 Oct 12:00 (trend down) | PUT WRITERS CHHOD RAHE · fuel neeche · 10:41; PE 22,600 giving back since 10:52 | fell 150 pts to the close |
| 03 | NIFTY 23 Sep 12:30 (range, Wed) | CALL WRITERS CHHOD RAHE · fuel upar · 10:15; CE 23,400 now *below* the spot line (ITM 52); count `PUT 2 ruke`, KRAM top: puts stopped 12:28–12:30 | price had risen 77 pts after the 10:15 break, then sat in 23,400–23,500 |
| 04 | NIFTY 24 Sep 10:30 (trend, early) | PUT WRITERS RUK GAYE · *watch*; PE 23,000 shown as AAJ NAHI BANA and kept out of the verdict | puts broke at 12:31 |
| 05 | NIFTY 24 Sep 12:35 | PUT WRITERS CHHOD RAHE · fuel neeche · 12:31 | fell ~110 pts to the close |
| 06 | NIFTY 1 Oct 15:29 | DONO TARAF CHHOD RAHE · pehle PUT 10:41 · phir CALL 13:58; call writers 163 pts against them | close |
| 07 | NIFTY 23 Sep 15:29 | DONO TARAF CHHOD RAHE; calls gave back with price *against* them (72), puts with price *in their favour* (12) | close |
| 08 / 09 | BANKNIFTY, SENSEX 1 Oct 12:00 | call writers ITM below spot (BN); put side stopped (SENSEX) | — |
| 10 | NIFTY 1 Oct 09:22 | FRONTS BAN RAHE HAIN, 6 of 15 minutes, with the server's own sentence | — |
| 01 | live server, Saturday | BOARD PADHA NAHI JA SAKA + the server's reason; "not a calm market" | — |

The range day is where the stamp shows its limit. By her rule the 10:15 CALL break stays the headline all day, even
after the fuel is mostly spent (+64.1L → +25.8L at 12:30). The time on the chip and the L numbers say how old and how
spent it is. The fresh put stall shows in the count and at the top of KRAM.

## Open questions for Mary (method, not presentation)

1. **Forced vs released** (§1d addendum, held). The Board shows "price against them / in their favour since the
   peak" as a fact (23 Sep 15:29: puts giving back with price in their favour). Should that change the verdict?
2. **Both sides giving back.** Should the newer side lead (1 Oct: the 13:58 call squeeze)? Today the Board names
   both in order and gives no arrow.

## Known limits, said plainly

- `/api/board` and `/api/oihist` are memory-only and take no day parameter. A past session cannot be opened
  through the live endpoints. Round 1 checked the read on 23 Sep (range), 24 Sep (trend) and 1 Oct (trend)
  by rebuilding those days' payloads from `data/chain/` with the same pure functions (`fronts`, `board`) and
  feeding them to the screen in the browser only.
- `/api/board` stamps `day` with the wall date, not the data's session (UI review §5). The Board does not print
  that day; it prints the grid's as-of minute.
- The GlanceBar line above the Board still reads "fold CE …". It comes from `BoardRev3.glanceLine`, which was out
  of scope to touch this round (one-word fix: "writers left").
- On her laptop (1229 × ~556 CSS, with a live shell of ~119 px) the read and the board fit (the board ends at about
  536 px). The one-line footer can sit a few px below the fold when the fact line wraps (the both-sides case).
  On a weekend the NOT LIVE banner adds 38 px. If the glance bar wraps, that adds about 76 px more; that is the
  shell's business.
- `/api/board` still computes the mirror and trend on the server (REST, cached per minute), and this Board does not
  show them. Dropping that cost needs a server change; it was left alone.

## Round 2 — "the three indices together" (Mary, 2026-10-03)

**Part A, the check (done).**
- 1 Oct was rebuilt at 5-minute marks for NIFTY, BANKNIFTY and SENSEX through the real `ChainState.oi_flow`.
  - The grid is what the server held: the `data/chain_backfill/` marks plus the `data/chain/` snapshots.
  - Strikes are the OI Flow tab's default (every strike in the snapshot).
- The full table is in `oiflow-3idx-2026-10-01.txt`.
- `diff` is the tab's own Diff: **put added − call added**. Sentiment BULLISH means diff > 0.

What the table says:
- **Morning split (her claim holds on the SENTIMENT word).**
  - NIFTY BEARISH vs BANKNIFTY and SENSEX BULLISH at nearly every mark 09:20–12:05.
  - It was 3/3 only at 10:05–10:25 and 10:40–10:45, and price did not rise then.
  - But the direction column (chg_dir) was already 3/3 ▼ for 8 marks, 10:50–11:25. That was mostly call writers
    adding, during a smaller drift down in BANKNIFTY/SENSEX.
- **Lined up from 12:10.**
  - chg_dir was 3/3 ▼ 12:10–12:35 (6 marks), with put OI falling on all three in the same marks. Put writers were
    covering everywhere, again at 12:45–13:00 and 13:45–14:05.
  - The sentiment word turned 3/3 BEARISH only at 12:50 (BANKNIFTY flipped last) and stayed so to the close.
- **Spot lined up in the same marks:** 3/3 down at 12:10, 12:20–12:30 and 12:45–13:00. That is *with* the move, not
  ahead of it. Most of the fall (NIFTY 22,571 at 12:00 → 22,235 low) came after the 12:10 alignment.
- The late bounce shows the same way: chg_dir 3/3 ▲ 14:35–15:00, with call OI falling everywhere.

Other sessions (5-min agreement strips through the same function):
- **24 Sep (trend down):** sentiment 3/3 BEARISH at every mark from 09:20 to the close. chg_dir was mostly ▼, in short
  runs (the longest 4 marks).
- **23 Sep (range, Wed):**
  - Sentiment was 3/3 BULLISH from 10:20 to the close. It is cumulative, so it stuck.
  - chg_dir was 3/3 ▲ for 9 marks, 10:35–11:15, during the morning rise, then mostly mixed through the flat afternoon.
  - A late 3/3 ▼ run with put covering everywhere (14:45–15:15) brought no fall.
- **30 Sep:** chg_dir 3/3 ▲ 12:25–12:55, then 3/3 ▼ 13:45–14:00 and 14:15–14:50, with put covering everywhere. SENSEX
  fell 73,010 → 72,480 into the close. Spot's first 3/3 down run (13:30) came just before the flow lined up.
- **29 Sep:** chg_dir 3/3 ▼ 09:25–09:40 in the same marks as spot 3/3 ▼ (the morning dip); the afternoon was mixed.

Reading of it (rows described, nothing tuned, no rates):
- Agreement arrives **with** the move. The long runs matter; 1–2 mark agreements happen without a move.
- The **direction column, not the sentiment word,** separates the range afternoon from the trend.

**Part B: started, then stopped on Mary's order (she wants the table first).** What is in `Board.tsx` right now, and
live on 5173 by hot reload:
- **Polls:** `/api/board` for all three indices (was: the active index only) and `/api/oiflow?idx=…&interval=5`
  for all three.
- **New pure read `teenoOf`, rendered by `TeenoBox`:**
  - The count is on chg_dir at the newest mark every live index has.
  - A stale index (more than one mark behind) or a missing index never counts.
  - "N marks in a row" is counted.
  - The driver ("put writers covering everywhere") is printed only when all three share it.
  - Spot is a witness, "check nahi" after 15:15 (xindex FREEZE).
  - Sentiment is shown as a count.
  - The per-index fronts verdict comes from `readOf`.
- **Layout:** TEENO takes the read card's right column. The two "Agli ladai" chips moved into one line under the
  count. The "IDX · HH:MM tak" label was removed. Lanes went 40 → 38 px.
- **Reused:** `FlowRow` (`data.ts`), the OI Flow tab's URL, and the `/api/board` URL the glance bar already polls.
  From `xindex` / `9-cross-index-design.md`: the 15:15 freeze, the hole rule, the "spot agrees 74% of minutes"
  finding (so spot does not carry the count), and its words "saath / alag".
- **Not reused:** `xindex` itself. It is a structure read (reader legs, zone, walls in lots) on an unsigned shadow
  sheet, not her OI Flow measure.
- **Temporary:** `ui-v2/.board-fixtures/` holds fixtures for 1 Oct 10:30/11:00/12:30/13:30 and 23 Sep 13:30, all
  three indices. Delete after the Part B screenshots.

## Round 4: the sides read, built (2026-10-04)

**The one brain.** `tapemap/sides.py` is pure, with no I/O and no clock. The definitions are rev `sides-2`: fixed
2026-10-03 23:38 IST and amended 2026-10-04 00:25 IST (`real-vs-fake-2026-10-03.md` §2, §2a).
- Inputs: the OI Flow tab's own slot rows (`ChainState.oi_flow`), its minute grid, the open OI, the saved snapshot at
  each mark, and the previous session's scale.
- Output, per index per closed 5-minute slot: each side's state and size, her top-2 breadth, the read word, POWER,
  PUSHTI vs continuation, the forced chip, the episode facts, and the reason for anything it could not check.
- `three()` makes TEENO's two lines in both count models. **Mary's decision, 2026-10-04:** the weekly books (NIFTY +
  SENSEX, 0/1/2) are the count, with BANKNIFTY a tagged witness that is shown and never counted.
- The Board copies no rule.

**I/O.**
- `sides_log.py` holds the forward log, the saved-chain parser, and `BookTail` (an incremental tail of today's chain
  file).
- `server.py` adds `GET /api/sides` (all three indices plus `three`, or `?idx=` for one) and a `sides` thread that
  writes `data/sides/sides_YYYY-MM-DD.jsonl`:
  - every closed slot once, as a `kind:"slot"` row (Fable §5 fields, cross-index counts, §1d leader, empty `her_read`
    / `leg_traded`);
  - each slot's outcome once, as a `kind:"outcome"` row after t+30;
  - only in market hours, and only for a grid the chain built today.
- `daylog` gzips `data/sides/` with the other recorders.
- **Live only after Mary restarts the server.** Until then the Board says "could not check — server not restarted
  with the sides read yet".

**The screen.** The read card's right column changed:
- **Before (round 2):** TEENO on the netted OI Flow column.
- **Now:** the SIDES grid, CALL and PUT rows per index over the last 6 slots.
  - `likh` / `kaat` / `flat`;
  - a POWER cell boxed with its size and her top-2 breadth (`kaat×9 2/2`);
  - a PUSHTI cell inverse;
  - the read word under each slot, coloured only when POWER.

TEENO is now two lines under the verdict, both rendered from `three` (`line1_weekly`, `line2_weekly`):
- **Line 1:** fuel side, weekly count, each book's size, its forced chip and pushti time, and the BN witness.
- **Line 2:** the latest PUSHTI's age, points, `fuel N% gaya`, `asar`, and the back side.

Tags: expiry din, kal ka scale, 15:15, backfill, kal ka data nahi.

KRAM, the levels, the fronts board and the verdict are unchanged. The fronts board now starts lower: under a live shell
its first rows are above the fold and the rest is a short scroll. That was a trader's choice: the verdict and the
three-index read come first.

**Removed in round 4:**
- the round-2 netted TEENO and its six `/api/oiflow` and `/api/board` polls (now one `/api/sides` poll);
- the `.board-fixtures` test files.

**Round 4, rev `sides-3` (2026-10-04 01:25 IST, post-hoc; `real-vs-fake-2026-10-03.md` §2b).**
- The morning is now sized on the previous session's own 09:20–10:30 window.
- It reads CAN'T CHECK when that session is missing or was the index's expiry day.
- A morning POWER is a witness (`subah · … gina nahi`) that is never counted and never uses up the day's first sign.

**UI.** The SIDES grid opens collapsed: the latest slot plus any POWER/PUSHTI column of the last 6, with the full grid
one click away (`SIDES ▸ poora (6)`, remembered per viewer in localStorage). The freed width goes to TEENO's two
lines, which are the answer.

The frozen rerun is in `sides-all-sessions-rev3.txt`: 279 PUSHTI rows, 89 at or before 10:30 (rev `sides-2`: 146 of
294).

## Round 5 — the trap layer, SHADOW (2026-10-04, rev `trap-1`, pre-registered 02:11 IST)

Pre-registration: `TRAP-PREREG-2026-10-04.md` (and its 02:38 build addendum). Fable's framework:
`FABLE-TRAP-FRAMEWORK-2026-10-04.md`.

**Built:**
- `tapemap/trap.py`: pure; six states per (index, level); rules R1–R6; the three Board lines.
- `tapemap/trap_log.py`: the forward log `data/trap/trap_<day>.jsonl`, plus incremental readers of the recorders' own
  files.
- `server.py`: a `trap` thread reads every 15 s; `/api/trap?idx=`; the log is written in market hours only.
- `daylog` gzip and both leak guards: `conftest` and `_isolate_mock_writers`.

**Reused unchanged:**
- `levels.py`, `dwell.py` and `sequence.py`, through warmap's rows;
- `sides.py` rev sides-3 for the slots, POWER, forced and `outcome`;
- `reader_live`'s legs for WHO;
- `xindex_live`'s rows for X2/X3;
- `vpin_fast.jsonl`, `ux_NIFTY`, and `senses` for `tape_with` and `pulled`;
- yesterday's saved chain for `oi_prev`, through `sides_log.prev_session_path`;
- `sides_log`'s guard, now with a per-row `key` and a file `stem`.

**Board.** Under TEENO, collapsed as `TRAP · shadow ▸`, remembered per viewer. Opened, it shows the active index's
TRAP / CHHOOTA / AGLA lines verbatim from trap.py. Under them is each could-not-check sentence (stamps, reader,
xindex, tape, yesterday's chain). Before the server is restarted it reads `could not check — server not restarted
with the trap read yet`. No verdict, word, count or headline changed.

Screenshots of 1 Oct, NIFTY, at 1229×594:
- `18-trap-1210-collapsed.png` and `19-trap-1210-open.png`;
- `20-trap-1010-collapsed.png` and `21-trap-1010-open.png`;
- `22-trap-1240-collapsed.png` and `23-trap-1240-open.png`;
- `24-trap-live-not-restarted.png`, the running server.

The frozen read over all 27 sessions is in `trap-all-sessions.txt`.

**Fix, 2026-10-04 ~11:30 IST (Mary: "yes do all fixes").** The live yesterday-scale (`server._sides_kal`) now also
reads `chain_backfill.read_grid`, the REST walk's 09:15–09:16 marks that the saved chain file never held. That is the
same input every frozen run used. On 1 Oct, live and frozen now agree on all 75 slots of all three indices: POWER,
direction, first sign and forced. The sides fixture's stored scale was refreshed to the corrected value, and the 10:10
screenshots (20, 21) were retaken; TEENO at 10:10 now reads `koi power nahi`.

**Kill bars signed, 2026-10-04 ~11:10 IST, "sab haan".** They are in `FABLE-DAYS-ZONE-KILLBARS-2026-10-04.md` §3,
`TRAP-PREREG-2026-10-04.md` §5 and `real-vs-fake-2026-10-03.md` §2c, verbatim. The clock starts Mon 2026-10-05.
