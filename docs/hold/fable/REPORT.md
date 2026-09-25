# HOLD / FOLD window — Fable's report

Written 2026-09-25 00:40 IST, after the replay. RULES.md was written first
(2026-09-24 23:40) and has not been edited above its §10.

## 1. What is here

| file | what |
|---|---|
| `docs/hold/fable/RULES.md` | the hold / fold logic, written before any replay; §10 logs what the data made me want to change (nothing applied) |
| `docs/hold/fable/index.html` | the prototype: trade list, custom picker, the floating window, the minute-by-minute replay. Open over http (scripts do not run from `file://` in the preview pane); `python -m http.server` in the folder is enough |
| `docs/hold/fable/hold.js` | the engine — ONE implementation, used by the page and by the report script |
| `docs/hold/fable/data.js` | the frozen replay record, 8 MB: five index-days (NIFTY 09-21/22/23, SENSEX 09-23/24), every finished minute's fronts, grounds facts, the four (role, direction) family reads, trend rows, 5-min pivots, per-strike premiums from the chain grid, her 29 round trips + 2 writer examples |
| `docs/hold/fable/scratch/build.py` | GET-only builder: `fronts.read` (causal running peak), `grounds._oi/_cvd/_flow`, `trendbox.rows`, `prints.with_cvd/bar_flags` over `ux_log.read_bars`, the chain grid from `data/chain/…jsonl` shaped like `ChainState.minutes`, index 1-min candles from Upstox REST |
| `docs/hold/fable/scratch/report.js`, `report_rows.json` | the per-trade rows below, and the engine's invariant checks (latch, one-way trail) — 7,058 minute-rows checked |

Nothing outside `docs/hold/fable/` was written. No `.py` in the repo, no
`data/`, no UI source touched. The server was not restarted.

## 2. The window, as the trader sees it

390 px wide, light, draggable by its header, collapses to one line. The
premium's own candles feed nothing but the grey P&L line. The only colour on
it is the verdict.

**First** — one word in the header: **HOLD** (green on pale green), **WATCH**
(amber), **FOLD** (white on red, with *since HH:MM*). On FOLD the whole header
turns pale red; on HOLD the header is white. Next to it: the trade
(`SENSEX 73900 PE · long ×60 · 9 min`).

**Second** — one sentence under the header, the reason in facts: on HOLD
"line 74,037 holds (175 pts of room) · fuel unclear · flow quiet · trend 3 of 3
with you"; on WATCH the one family against her and its fact; on FOLD the fact
that broke it: "SENSEX closed 73,702 above your line 73,690 (5m swing high
14:15)".

**Third** — four rows, each a state word and its fact, tagged [M]/[I]:
STRUCTURE (the line, its source, the room in points), FUEL (the §1d front
sentence), FLOW (CVD since / rank / prints, with "fill runs: could not check"
when they cannot be read), TREND (5m · 15m · 1h words).

**Footer**, grey: "entered 13:40 into HOLD · 73900 PE 190.03 → 321.70 · P&L
+7,900 [M] · read 14:12, last finished minute".

**Collapsed**: `FOLD · 73900 PE · line 73,690 (BROKEN) · fuel unclear · flow
quiet · 2 of 3 with you · 101 min · since 14:35`.

Calm on one red candle because nothing in the verdict reads the premium or a
1-min swing: the fastest input is a 1-min index close against a 5-min pivot
that is at least 10 minutes old; FUEL moves on 15-min OI slopes, FLOW on
closed 5-min ladder bars. Shouts on a break because FOLD latches, turns the
header red, and names the fact.

Not shown, deliberately: the engine's headline. On 09-24 its WAIT / SPENT
calls were CONTRADICTED by the tool's own grounding at her exits; the window
reads the families the grounding reads, not the call.

## 3. The rules in brief (full text: RULES.md)

- A trade is (index, strike, CE/PE, long/short). `want` = the index direction
  it needs. A **buyer** bets the move in `want` is being paid for; a
  **writer** bets the move the other way is exhausted — so writers use
  grounds' *exhaust* reads on the danger direction, buyers its *move* reads
  on `want`. Nothing new for writers.
- **STRUCTURE [M], hard, new:** a line L = the last 5-min swing (trendbox's
  PIV = 2) beyond price at entry, else the session extreme; trails one way on
  new confirmed pivots; **broken** by a 1-min index close beyond it, buffer 0;
  latched.
- **FUEL [M]** = `grounds._oi`, **FLOW [I]** = `grounds._cvd` + `_flow`
  merged, **TREND [I]** = the 5m/15m/1h rows voted — all existing reads,
  unchanged parameters.
- **FOLD** = structure broken, or 2 of the 3 soft reads AGAINST; **WATCH** =
  1 against; **HOLD** = none. FOLD latches. Blind reads count as neither; a
  blind structure is PATA NAHI.
- The entry minute is the last *finished* minute before the fill (the board's
  rule), so a 13:41:38 fill is read at 13:40.

## 4. Her 13 SENSEX exits on 2026-09-24

Read minute in brackets. "first FOLD → prem" is the first FOLD after that
entry had she stayed, and the premium then. Close = 15:29 premium.

| # | trade | in → out | took ₹ | at entry | at exit | why, at exit | first FOLD → prem | close |
|---|---|---|---|---|---|---|---|---|
| 1 | 74200 PE ×20 | 09:42 179.25 → 09:47 203 | +475 | HOLD (09:41), 170 pts room | **HOLD** (09:46) | line 74,327 holds 165 · fuel burning (PE 74000 covering) · flow quiet · trend 2 of 3 | 10:37 → 179.15 | 620.05 |
| 2 | 74200 PE ×40 | 10:19 222.60 → 10:23 234 | +456 | WATCH (10:18) | **WATCH** (10:22) | flow: divergence — new low 74,125 at 10:15 with CVD −22 above its 09:55 trough −80 | 10:37 → 179.15 | 620.05 |
| 3 | 74100 PE ×40 | 12:32 202.35 → 12:33 216 | +546 | WATCH (12:31) | **WATCH** (12:32) | flow: divergence at the 12:25 low (CVD −49 above −80) | 14:35 → 448.10 | 519.85 |
| 4 | 74000 PE ×40 | 12:35 179.80 → 12:38 161 | −752 | WATCH (12:34) | **WATCH** (12:37) | flow: divergence at the 12:30 low | 14:35 → 366.25 | 418.25 |
| 5 | 74000 PE ×20 | 12:44 167.95 → 12:50 160 | −159 | WATCH (12:43) | **WATCH** (12:49) | flow: divergence at the 12:35 low | 14:35 → 366.25 | 418.25 |
| 6 | 74000 PE ×20 | 13:26 184.20 → 13:27 220 | +716 | HOLD (13:25), 70 room | **HOLD** (13:26) | line 74,037 holds 151 · fuel unclear · flow with you · trend 3 of 3 | 14:35 → 366.25 | 418.25 |
| 7 | 73900 PE ×60 | 13:41 190.03 → 13:43 192.98 | +177 | HOLD (13:40), 175 room | **HOLD** (13:42) | line holds 179 · fuel unclear · flow quiet · trend 3 of 3 | 14:35 → 290.90 | 318.75 |
| 8 | 73900 PE ×40 | 13:43 206.55 → 13:43 207.30 | +30 | HOLD (13:42) | **HOLD** (13:42) | same minute as #7 | 14:35 → 290.90 | 318.75 |
| 9 | 73900 PE ×20 | 13:44 230.45 → 13:44 237.60 | +143 | HOLD (13:43) | **HOLD** (13:43) | line holds 215 | 14:35 → 290.90 | 318.75 |
| 10 | 73800 PE ×40 | 13:45 211.05 → 13:46 217.05 | +240 | HOLD (13:44) | **HOLD** (13:45) | line holds 300 | 14:35 → 223.60 | 219.20 |
| 11 | 73800 PE ×20 | 13:54 252.15 → 13:55 240 | −243 | WATCH (13:53), flow against | **HOLD** (13:54) | line holds 390 · flow with you · trend 3 of 3 | 14:35 → 223.60 | 219.20 |
| 12 | 73800 PE ×20 | 13:57 267.40 → 13:58 297 | +592 | HOLD (13:56) | **HOLD** (13:57) | line holds 424 | 14:35 → 223.60 | 219.20 |
| 13 | 73800 PE ×20 | 14:23 287.45 → 14:23 294.80 | +147 | HOLD (14:22) | **HOLD** (14:22) | line holds 401 · fuel unclear (both fronts unwinding) · flow with you · trend 3 of 3 | 14:35 → 223.60 | 219.20 |

Sum of what she took: ₹2,368 [M]. Eight of the thirteen lasted a minute or
less, so the window had exactly one reading for them — the entry read.

What the table says, in rows, not as a score:

- At **nine** exits the window said HOLD; at **four** it said WATCH (all on
  the same fact: a CVD divergence at a new low — the aggressors not paying for
  the low). It said FOLD at **none** of her exits. *(Corrected 2026-09-25 from
  "eight / five" after Opus's review: #11 was WATCH at entry and HOLD at exit;
  the table above was already right.)*
- The afternoon leg: from 12:31 to 14:34 the window never said FOLD. The one
  entry she took at the start of it (#3, 74100 PE at 202.35, 12:32) held to
  the window's 14:35 FOLD would have been 448.10, +245.75 a unit, +₹9,830 on
  40 [M]. Her eleven afternoon round trips together took ₹1,437 [M]. This is
  one row, not a sum over overlapping fantasies — she would not have made
  entries 4–13 while holding #3.
- The morning: after #1 the window said FOLD at 10:37 at 179.15 — flat to her
  179.25 entry — and the PE then went 154 (11:19) → 620 (close). See §6.

## 5. The other three days

| day | trade | in → out | took ₹ | at entry | at exit | first FOLD → prem (why) | close |
|---|---|---|---|---|---|---|---|
| 09-21 | N 23300 CE ×65 | 14:00 179.60 → 14:10 168 | −754 | HOLD (13:59), 40 room; fuel & flow **could not check** (no chain, no ladder record for 09-21) | HOLD (14:09) | 14:29 → could not check (expired 09-22 weekly, no record) — structure: closed 23,449 under 23,450 | — |
| 09-22 | N 23300 CE ×65 | 09:42 166.40 → 10:20 159.15 | −471 | WATCH (09:41), flow against | HOLD (10:19) | 10:21 → 155.15 (structure: closed 23,448 under the 09:55 swing low 23,450) | 28.85 |
| 09-22 | N 23550 PE ×65 | 10:32 134.80 → 10:38 144.05 | +601 | WATCH (10:31), trend against (5m/15m still UP) | HOLD (10:37) | 11:14 → 164.25 (structure by **2 pts**: 23,393 over 23,391 + fuel: PE 23400 building) | 220.70 |
| 09-22 | N 23550 PE ×65 | 10:42 174.75 → 10:42 186.95 | +793 | HOLD (10:41) | HOLD | 11:14 → 164.25 | 220.70 |
| 09-22 | N 23550 PE ×65 | 10:43 175.05 → 10:43 171.60 | −224 | HOLD | HOLD | 11:14 → 164.25 | 220.70 |
| 09-22 | N 23550 PE ×65 | 10:44 171.50 → 10:44 174 | +163 | HOLD | HOLD | 11:14 → 164.25 | 220.70 |
| 09-22 | N 23500 PE ×65 | 10:52 146.15 → 10:55 133 | −855 | HOLD (10:51) | HOLD (10:54) | 11:14 → 120.10 | 170.60 |
| 09-22 | N 23500 PE ×65 | 13:48 181.50 → 13:54 203.20 | +1,410 | HOLD (13:47), **10** room | HOLD (13:53), 36 room | 14:14 → 133.95 (structure: closed 23,383 over the 13:15 swing high 23,344) | 170.60 |
| 09-23 | N 23450 CE ×65 (1) | 09:18 100 → 09:25 99 | −65 | HOLD (09:17), flow could not check (first ladder bars) | HOLD (09:24) | 09:57 → 92.55 (fuel: CE 23400 building in the way + flow) | 107 |
| 09-23 | N 23450 CE (2) | 09:47 99.40 → 09:49 91.75 | −497 | **WATCH** (09:46), flow: CVD −529 while price +9.8 | WATCH | 09:57 → 92.55 | 107 |
| 09-23 | N 23400 PE ×65 | 09:49 125 → 09:53 124.20 | −52 | HOLD (09:48) | WATCH (09:52), divergence at the 09:45 low | 10:17 → 109.05 (structure) | 81.80 |
| 09-23 | N 23450 CE (3) | 10:00 98.60 → 10:09 90.80 | −507 | **WATCH** (09:59) | **FOLD** (10:08) | **10:00 → 95.10** (fuel + flow against) — she held nine minutes inside a FOLD | 107 |
| 09-23 | N 23450 CE (4) | 10:19 101.85 → 10:31 105 | +205 | HOLD (10:18), 43 room | HOLD (10:30) | 12:47 → 119.75 (structure: closed 23,443 under the 12:30 swing low) | 107 |
| 09-23 | N 23450 CE (5) | 10:33 106.45 → 11:04 106 | −29 | HOLD (10:32) | WATCH (11:03), divergence at the 10:55 high | 12:47 → 119.75 | 107 |
| 09-23 | N 23450 CE (6) | 11:07 115.65 → 11:16 110 | −367 | **WATCH** (11:06), divergence at the 11:10 high | WATCH | 12:47 → 119.75 | 107 |
| 09-23 | S 74900 CE ×20 | 11:32 215.25 → 11:40 200 | −305 | HOLD (11:31), 269 room | WATCH (11:39), divergence at the 11:30 high | 12:32 → 224 (fuel: CE 75000 building + flow) | 166.15 |
| 09-24 | **writer** S 74500 CE ×20 (example: the #1 CE front by peak at 11:00) | 11:00 61.35 → open | — | HOLD (10:59), **16** room | — | 11:19 → 63.95 (structure: closed 74,232 over the 11:00 swing high 74,203) | **0.15** |
| 09-23 | **writer** N 23400 CE ×65 (example, same rule at 10:30) | 10:30 129.50 → open | — | **FOLD at entry** (fuel: CE 23400 unwinding — covering paying the move; trend 2 of 3 UP) | — | 10:29 → 129.15 | 135.30 |

**The 09-23 re-entries, which is what the coordinator asked about.** Six buys
of the same call between 09:18 and 11:16, net −₹1,261. The window's entry
reads were HOLD, WATCH, WATCH→FOLD (one minute in), HOLD, HOLD, WATCH. The
three WATCH/FOLD entries lost ₹1,371 between them; the three HOLD entries
netted +₹111, and the only winner (4) was a HOLD entry that the window would
have carried to 12:47 at 119.75, +17.90 a unit against her +3.15. On a range
day the recurring word was WATCH, and its recurring fact was the same one:
*new high without a new CVD high*. That is P4 in RULES.md, about half right:
the state came from the tape, not from the trade, but it was WATCH more often
than FOLD, and WATCH only informs.

The second writer example is the FOMO guard working on a bad entry: the rule
"short the #1 CE front by peak" picked an in-the-money call at 10:30 (spot
23,415, strike 23,400) and the window said FOLD before she pressed sell.

## 6. Where it would have misled her — both kinds

**(a) FOLD or WATCH on a trade that was right** — her problem of leaving early,
which a wrong FOLD reproduces:

1. **09-24, 10:37, the 74200 PE.** FOLD on fuel + flow: PE 74000 read BUILDING
   again for a few minutes after its 10:22 fold, and CVD diverged at the 10:25
   low. Premium at the FOLD 179.15; low 154.25 at 11:19; then 195 (11:30), 290
   (13:00), 620 (close). Held from #1 the FOLD was flat; from #2 it was
   −43.45 a unit, −₹1,738 on 40. The fall resumed 55 minutes later. This is a
   real type-(a) error, and it came from a reversal in an OI slope over 15
   marks — the front "adding again" while still under its peak. The window
   printed exactly that, so she would have seen a 15-minute slope, not a
   conviction. It is still a wrong FOLD.
2. **09-22, 11:14, the 23550 / 23500 PEs.** Structure broke by **two points**
   (close 23,393 over a 10:55 swing high of 23,391) with fuel already against
   (PE 23400 building). The 23550 PE was 164 at the FOLD, then ranged 158–271
   and closed 220.70; the 23500 PE was 120 at the FOLD and closed 170.60. For
   the 10:32 entry the FOLD still took +29.45; for the 10:52 entry it took
   −26.05 against her −13.15. Buffer 0 was a registered choice; this is what it
   costs. It is recorded in RULES.md §10 and not changed.
3. **The writer example, 09-24 11:19.** The short 74500 CE at 61.35 was
   FOLDed at 63.95 on a 29-point structure break and expired at 0.15. The
   window had said "16 pts of room" at entry; the last 5-min swing high was
   sixteen points over the index. The rule has no minimum-room clause, on
   purpose; the number was on the screen and a trader decides what to do with
   sixteen points.

**(b) HOLD while the reason was going** — her problem of holding a bad trade,
which a silent window reproduces:

4. **09-24, the last hour.** Entries 11–13 (73800 PE at 252 / 267 / 287,
   13:54–14:23) read HOLD or WATCH; the low printed at 14:24; the window's
   FOLD came at 14:35 at 223.60: −28.55, −43.80 and −63.85 a unit. The tape
   facts that said "exhaustion" were on the window's own fold list — CE 74200
   folded 13:39 with spot 73,880, CE 74000 folded 14:12 with spot 73,648, the
   winners cashing in at spot — but grounds' FUEL read stayed FLAT ("both
   fronts unwinding — no direction") because its #1 CE front by session-peak
   OI was 74300, seven hundred points away. That is RULES.md §8.5 exactly; it
   is proposed in §10 as a separate registration and **not** applied, because
   applying it tonight would be tuning to this day.
5. **09-22, 13:48 → 14:14.** HOLD for 27 minutes while the 23500 PE went 206
   (13:56) → 222.50 (14:00) → 133.95 (14:14): NIFTY bounced 94 points in
   fourteen minutes inside an intact structure (line 23,344, 36 pts of room at
   her exit). On expiry day an in-the-money option moves one-for-one with the
   index, so 36 points of room was ₹2,340 on 65. She took +21.70 at 13:54 — a
   better exit than the window's. The window was right about the thesis (the
   line held until 14:14) and silent about the give-back. It is not a
   profit-taking tool and was not designed to be one; RULES.md §8.6 (the
   mirror's DIVERGES — the option has stopped paying) is the candidate for
   that read, and it is not applied.
6. **Sub-minute trades.** Eight of the 09-24 trades and four of the 09-22
   scalps lasted a minute or less. The window cannot manage a ten-second trade;
   it can only say, before the buy, whether the reason exists. On this record
   that entry read was WATCH on 9 of 31 entries and FOLD on 1.

**Blind spots that are not errors but must be said:** on 09-21 FUEL and FLOW
could not check (no chain or ladder record that day), so the verdict ran on
structure and trend only; the replay's FLOW has no fill runs (the day record
holds bars, not fills — live, the book feeds `runs.Runs`), which the window
prints as "fill runs: could not check"; the fronts' peak ranking uses the
running peak as of the minute, so the #1 front can switch between two minutes
and flip FUEL, which happened at 10:37 on 09-24.

## 7. The predictions in RULES.md §8, against the record

Unlatched state at every finished minute (the entry read a fresh trade would
have got), per day and (role, direction):

| day | buyer UP | buyer DOWN | writer UP | writer DOWN |
|---|---|---|---|---|
| NIFTY 09-22 | H 132 / W 185 / F 58 | H 232 / W 123 / F 20 | 132 / 119 / 124 | 274 / 81 / 20 |
| NIFTY 09-23 (range) | 164 / 201 / 10 | 197 / 99 / 79 | 240 / 124 / 11 | 157 / 105 / 113 |
| SENSEX 09-23 (range) | 225 / 135 / 15 | 101 / 170 / 104 | 278 / 90 / 7 | 130 / 170 / 75 |
| SENSEX 09-24 (trend down) | 14 / 209 / 152 | **179 / 182 / 14** | 14 / 185 / 176 | 285 / 82 / 8 |

- **P1** held: on the trend day the with-trend buyer read FOLD on 14 of 375
  minutes, and the against-trend buyer read FOLD or WATCH on 361 of 375.
- **P2** is weak: on 09-23 four of the six NIFTY CE entries were WATCH within
  two ladder bars (three at entry); on 09-24 five of thirteen were WATCH at
  entry. Four-of-six against five-of-thirteen is a lean, not evidence.
- **P3** held for with-trend directions (3–7 distinct structure-break minutes
  per day from twelve staggered entries) and did not for the counter-trend
  direction on 09-22 and 09-24 (8–9): a line against the trend is broken again
  and again, which is the rule doing its job.
- **P4** half held (§5 above).

None of this is a result. Four days, thirty-one trades, one week.

## 8. What she must pre-register before a live verdict

From RULES.md §8, unchanged: (1) STRUCTURE — 5-min PIV = 2 pivot, the 1-min
close, buffer 0, the one-way trail, the latch; (2) the verdict map — hard
structure, 2-of-3 soft, WATCH at 1, latch; (3) the writer mapping —
exhaust-of-danger; (4) the trend-row vote. The reads themselves (grounds',
trendbox's, §1d's) are already registered with their own kill conditions.

The falsifier as written: over 30 forward sessions, the option's favourable
excursion over the next 30 minutes after a FOLD minute must be worse than after
a HOLD minute in the same trade type; FOLD must not fire on the majority of
in-trade minutes on trend days; the result must survive removing the single
worst trade. Otherwise the map is deleted, not tuned.

Two candidates the record argues for, each needing its **own** registration
before it touches the verdict (RULES.md §10 A and B): the near-spot wall fold
("winners cashing in") as a FUEL against for buyers, and the premium's
DIVERGES as a "the option has stopped paying" read.

## 9. Wiring, smallest first

1. **`hold.py` + `GET /api/hold?idx=&strike=&side=&role=&entry=HH:MM:SS&qty=`.**
   A port of `hold.js` (structure + the vote + the map, ~150 lines, pure), fed
   by what `/api/board` already assembles per finished minute: `fronts.read`
   on the poller's grid, `grounds.facts` on `_ux_reply`'s bars and runs,
   `trendbox.rows`, and the index 1-min candles `live.build_session` already
   re-fetches. Pivots come from those candles with trendbox's own `agg` and
   PIV. The trade (entry minute, L, the FOLD latch) is written to
   `data/day_state/` next to FIRST, so a restart re-reads the same L and the
   same FOLD — the anytime-start rule.
2. **A forward log, `data/hold/hold_<day>.jsonl`**: one row per finished
   minute per open trade — verdict, the four reads, the premium — appended by
   the same route (as `calls_log` does for `/api/calls`), never rewritten. The
   falsifier in §8 is answered from these rows and nowhere else.
3. **The window, `/hold.html`**: the body of `index.html`'s `#win` polling
   `/api/hold` every 5 s, plus the picker (index, strike, side, long/short,
   qty, entry time defaulting to now). "Present on any window or tab" is not a
   thing a browser tab can be; the smallest honest answer is Chrome's
   Document Picture-in-Picture (`documentPictureInPicture.requestWindow`, one
   call, Chrome 116+): a real always-on-top window that floats over every tab
   and over the broker screen. Fallback: the GoCharting extension's content
   script already injects into tool tabs and can inject this one.
4. **One bell**, on the transition into FOLD only. WATCH is silent.
5. **Later, after their own registrations:** the premium line from
   `/api/contract`'s VWAP ±σ (the mirror's wording), and the near-spot wall
   fold.

No new dependency, no new process, no order path.
