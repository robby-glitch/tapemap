# VALIDATE 2 — the design (Fable, 2026-10-06, after the close)

Design only. Nothing tracked was edited; the server was only GET-read (no `log=` parameter, ever); the scratch
replays live in `scratch/`. Light mode, no charts, no odds, [M]/[I] on every number, three absences, every level
spot AND fut, Hinglish chips on every glyph, no candle-close gate anywhere, no order path. A word that decides
(GO / WAIT / NO, the PULLBACK / GAVE UP read, the ZONE-ALONE line) is pre-registered in `PREREG-DRAFT.md` before
it shows live; the in-trade HOLD / FOLD stays fold.py rev 6, untouched.

Her brief, in one line: *validate first whether the trade fits the market, say if there is a better one, watch every
second — more so in a trade — and give me the whole day's read with levels when I press, the way you would.* The
14:57 read she liked is the floor; this beats it by running on all three indices, every second, and in a trade.

---

## 0. The decisions, up front

| # | question | the trader's decision |
|---|---|---|
| 1 | MARKET READ: generator | **Deterministic**, composed off the engine's own cached replies (`read2.py`, composition only — the warmap/frame precedent: it measures nothing new except the three small sums named in §7). Sections in a fixed order (§2), 14–22 lines, each sentence [M]/[I]-tagged with its absence kind. An LLM polish is a **later, optional, number-locked** layer (§2.6): no key on her machine today, so it is not in the evening build and the screen never depends on it. |
| 2 | VALIDATE: the checks | **Ten counted checks + five printed** (§3), every one answered by a module that already runs. The word is **GO / WAIT / NO**, decided by counts and vetoes, never odds (§3.4). A writer gets the same word (nine counted: a writer has no next wall). |
| 3 | BETTER TRADE | **The board**: 18 candidates (per index: the 4 ATM legs + the ITM PE sale + the ITM CE sale — how she sells), each through the same ten checks via the existing IF YOU WERE IN engine, ranked lexicographically (§4). Three named slots: *same thesis, better expression* · *opposite thesis* · *other index*. "Your trade is the best on the board" / "nothing clean — stand aside" have exact rules. |
| 4 | IN TRADE | **Every second** off the fold_live loop that already ticks at 1 s (its read cache goes to 1 s for an index with an open trade). The engine's word stays the decision. Beside it: the **KYA BADLA SINCE ENTRY ledger**, the **ZONE-ALONE line** (shown, never a fold), the **PULLBACK / GAVE UP read** by her definition, and the **W-BLEED gauge** that sees the slow leak the z/√n event cannot (§5). |
| 5 | Unique | Picked: **the ledger** (entry frozen, diffed every second, each row WITH/AGAINST) and **WHO IS IN PAIN** (the counterparty row: writers under water or comfortable at her strike and both walls). Considered and dropped: §6. |
| 6 | Layout | One 760-px column beside the broker (§8): ABHI strip (always) · the mode card (READ / VALIDATE / IN TRADE) · LEVELS TO WATCH (always). Enter = press. |
| 7 | Cadence, honestly | Book ticks real-time; chain every ~10 s; VPIN per bucket (~2–5 min); GoCharting bars only while its tab is visible. "Every 1 s" = recompute on the newest row each second and **print each input's age** on the strip. Nothing invents a fresher number than the feed gave. |

---

## 1. What exists, and what each piece answers (the reuse map)

| question on the screen | module that already answers it | endpoint today | new? |
|---|---|---|---|
| HOLD / PAST GIVE-UP / FOLD, give-up G, wall behind W, wall ahead A, the four chips Z/F/O/V, premium at G / at A, time value, expiry-afternoon | `fold.py` rev 6 via `fold_live.py` (1-s loop) | `/api/fold?id=`, `/api/fold/flat?idx=`, `/api/fold/ifin?idx=&k=&ty=&side=` | no |
| IF YOU WERE IN for any (k, ty, side) now | `fold_live.Engine.ask_ifin` (deep copy of the flat read, marked at the last chain row) | `/api/fold/ifin` | reused as the board's engine |
| the flat market: next fight above / below with its confirm sentence, whose day, value, boxed / trending, GAVE UP at a wall | `fold.State.flat_view` | `/api/fold/flat` | + `vwap`, `cvd`, `sess` fields (§7) |
| TREND / PIN-CHOP / TWO-SIDED / EARLY with evidence chips and the level that changes it | `daytype.py` (`server._daytype_reply`) | rides `/api/calls` | no |
| the top-2 fronts per side: OI now, peak and when, giving back since when, % off, DEFENDED / GIVING WAY / STALLED | `fronts.py` + `board.py` | `/api/board?idx=` | no |
| the day's folds, the defender, PCR text, the trend box | `board.py`, `trendbox.py` | `/api/board` | no |
| CVD over 15 min, its rank, divergence at the top / bottom, big fill runs, futures OI change | `grounds.py` facts | `/api/calls` | no |
| the day as chapters, big prints at levels, the decoder's count beside her trade, highlights | `story.py` | `/api/story?idx=` | no (GoCharting-dependent; §2.2 names the fallback) |
| trap states at levels (reached / dwell / induced / failed / released) | `trap.py` | `/api/trap` | no |
| OI flow per 5-min slot, POWER, forced chip | `sides.py` | `/api/sides` | no |
| cross-index: sync, extremes TOOK / EQUAL / FAILED, who turned first, walls, LOOK HERE | `xindex.py` via `xindex_live` | `/api/xindex` | no |
| VPIN percentile (shadow) | `vpin.py` | `/api/vpin` | no |
| expression BUY / LEANS BUY / SELL / LEANS SELL / EITHER / STAND ASIDE per direction, the buy and sell cards | `expression.py` (`server._expr_reply`) | `/api/hold/expr` | no |
| reversal N/4, theta per 15 min, timers, trail lock | `validate_live.py` (frame-dependent) | `/api/validate` | no |
| book absorption / sweeps / depth pulls on the Upstox ladder (no GoCharting needed) | `senses.py` (`sweep`, `absorption`, `depth_pull`) | `/api/senses` | no |
| PDH / PDL / PDC / PWH / PWL / OPEN / ROUND / max pain, each with its frame | `levels.py`, `chain_metrics.py` | inside `/api/warmap` | no |
| feed health and ages | `feed_health.py` | `/api/feed/gc`, rides `/api/fold*` | no |
| cooldown / flip timers, her typical hold | `trade_record.py`, `receipts.py` | `/api/validate`, `/api/receipts` | no |
| **the ten checks, the word, the board ranking, the ledger, zone-alone, pullback / gave-up, W-bleed** | — | — | **`validate2.py`, new, pure** |
| **the market read composed, PIN, PCR shift, levels to watch with confirms / denies, the falsifier line** | — | — | **`read2.py`, new, pure** |
| **the face** | `ui-v2/src/pro` (Pro.tsx = the DESK; Float) | `/pro.html` | **`Validate2.tsx`, new, mounted as the Validate tab** |

What is NOT on the new face, deliberately: the rev 4/5 hold window line (`hold.py`, a 3-minute-close break — she said never gate on a candle close; it keeps logging), VALIDATE rev 2's four facts (`validate.py`; its `/api/hold/check` keeps its own record), PLAN's rung. They stay alive and untouched; the new tab simply does not draw them.

---

## 2. THE MARKET READ — what it says, in what order

One press (or Enter with nothing in the slip). `GET /api/read?idx=NIFTY` (the focused index leads; the other two get one line each in §2.1 and §2.3 and their own candidates in §2.9). The reply carries a **facts packet** (every number the text uses, keyed) and the **text** (sections of sentences). The face prints the text; the packet is what any later polish layer is checked against.

Length: 14–22 lines on a normal day; a section with nothing to say prints its absence sentence and takes one line.

### 2.1 AAJ KA DIN — the day in one line per index [I on M]
`{IDX} · {daytype} since {t} · {whose day: buyers' day, 7 fights to 3} · {spot now} spot / {fut} fut (basis {b}) · range {lo}–{hi} spot · {boxed in value {val}–{vah} since {t} | trending above value} · VWAP {vwap} fut {above/below, since}`
Sources: daytype, fold flat `day`, flat `sess` + `vwap` (§7), basis_ix. Example from today 14:57: *NIFTY · TWO-SIDED since 13:28 · buyers' day (9 fights to 2) · 22,709 spot / 22,781 fut (basis 72) · range 22,569–22,730 spot · boxed 22,676–22,730 since 12:40 · above VWAP 22,756 fut since 11:05.*

### 2.2 KAHANI — the day so far as chapters [I]
`story.chapters` verbatim (start–end · name · sentence · asar). When the decoder is not posting, the chapters come from the trap stamps alone and the line says so (`trap_why`). When neither exists, the fallback is the book's own marks (`fold.flat.marks`: walls named, fights won, absorbed, trapped) grouped by fight — "kahani from the book, GoCharting not posting". Never silent: a day always has a story from Upstox alone.

### 2.3 TEENO — the three indices against each other [M stamps, I meaning]
From `xindex` X2/X3 at the latest push: *the 14:07 high: SENSEX topped the same minute [M]; BANKNIFTY did not confirm (its high 12:48) [M] — a divergent push, the kind that fails [I]*. Plus daytype's peers chip. SENSEX is a witness (thin tape), said each time.

### 2.4 OI — pin, ceiling, floor, who built / left since when, PCR shift [M]
- **PIN**: the strike inside the nine with the largest CE+PE OI where both legs are ≥ half their side's largest; printed with both legs: *pin 22,700 (CE 309L · PE 407L)*. (`read2.pin`, §7.)
- **CEILING**: the top-2 CE fronts above spot (board fronts): *22,750 CE 296L / 22,800 CE 309L — flat since 14:00 (peaks 14:46 / 14:10, 11 % and 22 % off)*. State words are fronts.py's.
- **FLOOR**: the top-2 PE fronts below spot: *22,700 PE 407L → 374L, giving back since 14:27 (−8 %); 22,600 PE −47 % off its 12:37 peak — the floor is leaving*.
- **PCR(9)**: near-ATM nine strikes, now vs 09:30 vs one hour ago: *PCR 1.52 (1.75 at 14:00, 1.36 at 10:03)* (`read2.pcr9`, §7).
- Who built today vs carried in: board's `built_label`.

### 2.5 ORDER FLOW (fut) [M lots / I side]
- Fights: the last three fixed fights from flat `marks` (*sellers won 14:46 at 22,775; buyers held 407 lots at 14:56*), the trapped / absorbed ones named at their price.
- CVD: grounds' 15-min fact (*CVD −1,852 with price +5.6, rank 1.00 of today's 15-min moves*) and the day path from the ladder (*CVD peaked 14:07 at the high; lower high 14:39; ~53K net selling since* — flat `cvd`, §7); divergence at the top / bottom when grounds flags it.
- VWAP acceptance: price vs VWAP and whether this minute opened there.
- Big prints at levels: story E1 when GoCharting posts; else the senses' absorption rows on the Upstox ladder (*absorbed ×3 at 22,775–22,780 13:40–13:52, ratio 2.7*) — Upstox-only, so this line never goes blind with the tab.

### 2.6 VPIN [I, shadow]
*toxicity 0.84 pct of today (shadow) · 4 of 10 buckets one-sided, sellers' way* — the fold flat row plus the percentile. One line.

### 2.7 GHADI — expiry and time [M]
Per index: *NIFTY 0DTE — 33 min to close, ATM straddle time value 41 burns to 0 [I]; expiry afternoon: give-ups follow the best (fold)* · *BANKNIFTY 21 DTE* · *SENSEX 2 DTE*. From 14:45: *your 15:00 practice — 3 min* (reminder, blocks nothing).

### 2.8 LEVELS TO WATCH — three above, three below, spot AND fut, each with confirms / denies
From `fold.levels(t)` (walls at K + basis, trapped / held / won fights, day high / low, open, yesterday's, value) merged with `levels.py` statics (PDH / PDL / PDC / ROUND, index frame → fut by adding basis_ix), de-duplicated within w, nearest first. Each line: `{spot} spot / {fut} fut · {what} · confirms {dir}: {sentence} · denies: {sentence}`. The confirm sentence is fold's own (`next_fight.confirm`: lifts / hits followed by price, the wall off its peak, VPIN turning); the deny sentence is its mirror (the wall building, a fight won the other way, price back through by w). Written once in `read2.level_lines` (§7).

### 2.9 BEST TRADE NOW — the board (§4), top three, both ways, all three indices
*1 · SELL NIFTY 22,700 CE @ 30 ATM — GO, 7 with · 0 against · 2 neither: ceiling holding, floor leaving, sellers won the last fight, SENSEX topped with NIFTY · keep all if close ≤ 22,700 spot, breakeven 22,730 spot · invalid: 22,730 spot accepted (fut 22,802) or 22,750 CE off its peak.*
Or: *nothing clean — stand aside: the best of 18 reads WAIT with 4 with, 2 against (order flow, cross-index). It changes if: …*

### 2.10 YEH READ BADLEGA AGAR — what changes the read
The two or three facts the read leans on, as falsifiers with levels: *22,750 CE off its 14:46 peak by 15 % · buyers win a fight above 22,818 fut (22,746 spot) · 22,700 PE rebuilt above 407L*. Stamped when they happen (the ABHI strip re-reads every second and the line turns amber with the time).

### 2.6b The optional LLM polish (later, not in the evening build)
If `ANTHROPIC_API_KEY` is set, `read2_llm.py` sends the packet + the template text to `claude-sonnet-5-5` with one instruction: rewrite in her voice, ≤ 18 lines, **every number verbatim from the packet, no new numbers, no odds words**. The server extracts every numeric token from the reply and refuses the whole reply if any token is absent from the packet's number set (strings as printed); a refusal serves the template. The polished text is labelled *[I · prose]* and the template stays one click under it. The screen is complete without it; this is a nicety, not a dependency.

---

## 3. VALIDATE A TRADE

### 3.1 Input
The slip (exists on the DESK; reused): index · strike (chain picker, ATM default) · CE / PE · BUY / SELL · price (optional; the chain's LTP otherwise). Enter or the VALIDATE button. A press is a GET; it is logged **only** with `log=1`, which the face sends and a test never does (house convention).

### 3.2 The engine under it
One `/api/fold/ifin` read for (k, ty, side) — the rev 6 engine's own read for a mark made now (G, W, A, chips, premiums) — plus the cached replies of daytype, expression, board fronts, grounds, xindex, vpin. No file is read on a press.

### 3.3 The ten counted checks (each WITH / AGAINST / NEITHER, an absence carrying its kind)

| # | check | why a pro runs it | WITH | AGAINST | NEITHER |
|---|---|---|---|---|---|
| 1 | **RIGHT NOW** — the engine's word for a mark made now | would the hold engine throw you out at the door? | HOLD | FOLD or PAST GIVE-UP | CAN'T CHECK (could not check) |
| 2 | **DAY / TREND** — daytype + the trend rows | a buyer needs a leg; a seller sells WITH the trend (ATM/ITM) or into a pin | TREND her way, or PIN/CHOP for a writer; trend rows ≥ 2 her way and none against | TREND the other way; rows ≥ 2 against | TWO-SIDED / EARLY / mixed rows (a read) |
| 3 | **EXPRESSION** — expression.py's word for her direction and for the other | is the option the right instrument, or is selling the other side the better expression? | the word matches her role (BUY ↔ buy, SELL ↔ sell) or EITHER | the word is the other role (→ the better-expression slot), or her way is STAND ASIDE while the other way has a word (the engine leans the other way) | STAND ASIDE both ways |
| 4 | **WALL BEHIND (W)** — the writers who defend her | if they leave, nobody is holding the floor / ceiling under her | building | off (the engine's event) | stopped |
| 5 | **WALL AHEAD (A)** — the writers her target must break (buyer only) | the next wall caps the move; writers leaving there pay her | off (leaving) | building AND within 2 B of price | stopped, or building but farther |
| 6 | **ORDER FLOW** — the engine's FLOW chip + CVD | who won the last fight, and is the move paid for | chip WITH | chip AGAINST | QUIET (CAN'T CHECK = could not check) |
| 7 | **VPIN** — the engine's VPIN chip | one-sided toxic flow her way or against | WITH | AGAINST | QUIET (fewer than 10 buckets = could not check; NIFTY is the only gauge) |
| 8 | **CROSS-INDEX** — the latest 30-min push, confirmed by the other two? | a push nobody else confirms fails; a push against her that everyone confirms is the trend | push her way, both took it; or push against her, neither took it | push her way, neither took it; or push against her, both took it | one took it |
| 9 | **ROOM** — invalidation vs target, in points | the stop must be outside one candle; the target at least as far | to-G > B and (no A, or to-A ≥ to-G) | to-G ≤ B, or to-A < to-G | no give-up yet (could not check) |
| 10 | **PAYING** — the payers' top-2 fronts (CE above for an up trade, PE below for a down trade) | the move needs somebody forced to pay for it | any UNWINDING | all BUILDING | STALLED / mixed |

A writer: #5 is *not shown — a writer has no next wall; time is her target*; the other nine count.

### 3.4 Printed, never counted
MONEYNESS (delta, intrinsic, time value; *deep ITM = a futures position in option's clothing* at |delta| ≥ 0.85) · SPREAD (bid / ask in ticks — she posts, so it is revenue) · CLOCK (time, DTE, expiry-day theta of her strike per 15 min [I], the 15:00 practice) · WHO IS IN PAIN (§6) · PCR(9) now / an hour ago.

### 3.5 The word
- **NO**: RIGHT NOW is AGAINST, **or** ≥ 2 AGAINST among the six structural checks {DAY/TREND, EXPRESSION, WALL BEHIND, WALL AHEAD, ORDER FLOW, CROSS-INDEX} (hold rev 4's "two families" principle).
- **GO**: RIGHT NOW is WITH, 0 AGAINST anywhere, ≤ 1 could-not-check, and ≥ 6 WITH.
- **WAIT**: everything else; it names each AGAINST as *what would have to change* and, with nothing against, the NEITHERs as *not there yet*.
- Shown with it: *{w} with · {a} against · {n} neither · {c} could not check — of {10|9}, a count, not odds.*

### 3.6 The levels under the word
- **invalid** = G from the engine, printed fut AND spot (G − basis_ix), with its person: *where the 22,700 PE writers stand* (W) and *premium there ≈ {at_G} [I]*.
- **T1** = A (the wall ahead) fut / spot, *premium there ≈ {at_A} [I]*; **T2** = the second-ranked front beyond A on the payers' side, with the same interpolated premium; both say *only if {wall} comes off its peak* when that wall is building.
- **reward vs invalidation**: *+{to_A} for −{to_G} pts (fut)* — two numbers, no ratio.
- A writer: *keep all if close {≤ / ≥} {K} spot · breakeven {K ∓ p0} spot · invalid: {G} accepted / {W} writers leave*.

---

## 4. BETTER TRADE — the search and the rank

### 4.1 Candidates (18)
Per index with a running engine: ATM BUY CE · ATM SELL PE · ATM BUY PE · ATM SELL CE · ITM SELL PE (ATM + 1 step) · ITM SELL CE (ATM − 1 step). Her ways of expressing a view, nothing far OTM. Each candidate is one `ifin` read (cached 10 s while asked; a press asks all six of its index, the read asks all 18) through the same ten checks.

### 4.2 Rank — lexicographic, deterministic, no score
1. word: GO < WAIT < NO
2. more WITH
3. fewer AGAINST
4. fewer could-not-check
5. index: NIFTY, BANKNIFTY, SENSEX (`instruments.ENABLED`, liquidity)
6. ATM before ITM

### 4.3 The three named slots, from the ranked list
- **same thesis, better expression**: the best candidate with her index and direction and the other role;
- **opposite thesis**: the best with her index and the other direction;
- **other index**: the best outside her index.
Each slot prints its word, counts, and what is against it. The top three overall are printed too.

### 4.4 Sentences
- *your trade is the best on the board* — no candidate ranks strictly above hers (hers is re-ranked with the same key).
- *better: …* — the first candidate strictly above hers, with its slot name.
- *nothing clean — stand aside* — the top of the board is NO, or WAIT with < 5 WITH; then *it changes if* lists the top candidate's AGAINST checks as falsifiers.

---

## 5. IN TRADE — every second

### 5.1 Plumbing
`fold_live.run` already ticks every 1 s and feeds rows 2 s after their key; its read cache refreshes every 3 s. Change: `READ_EVERY_S` → 1 for any index with an open marked trade (the flat indices stay at 3). `GET /api/validate2?idx=` composes from caches only (the engine's reply, the entry snapshot, feed ages, vpin, grounds). The face polls it every 1 s (≈ 5 KB).

### 5.2 What the face shows, top to bottom
1. **The engine's word** verbatim (HOLD / PAST GIVE-UP / FOLD) with its clause and line 2 (*out if 22,788 is accepted …*), premium now / peak / given back, time in trade. The sound and the FOLD tone stay the engine's.
2. **The ages strip**: book 0.2 s · chain 8 s · VPIN 1:40 · GoCharting dead since 15:14 — each input's age, every second. An input past its own staleness (chain > 180 s, book > 30 s) turns its rows CAN'T CHECK — the engine's rule, printed.
3. **The four chips** with *since* and the sentence each, as today.
4. **KYA BADLA SINCE ENTRY — the ledger** (§6.1), one row per fact, entry value → now, tagged WITH / AGAINST / —.
5. **ZONE ALONE** (§5.3) when it applies.
6. **PULLBACK / GAVE UP** (§5.4) when price is against her.
7. **W-BLEED gauge** (§5.5), always, one line.
8. **Reversal N/4** (validate_live) when the frame is alive, else *could not check — GoCharting not posting; the book reads above stand*.
9. **Expiry theta per 15 min**, the 15:00 practice from 14:45.
10. The MARKET READ and VALIDATE (another idea) buttons stay one press away: *it's even more important when I'm in a trade*.

### 5.3 The zone-alone problem, shown honestly
The replay (`docs/hold/ZONE-ALONE-REPLAY-2026-10-06.md`) proved that turning *zone alone never holds if OI and flow disagree* into a FOLD cuts her biggest winners (09-24 SENSEX 74200 PE at 171 → ran to 641; 09-22 23550 PE) while folding losers earlier. So it is **not a fold**. It is a named line, amber, with the facts and both histories:

> **ZONE ALONE since 11:05** · the zone is the only thing behind you · OI QUIET since 11:05 (22650 CE 169L, −15.6 % off its 200.7L peak, 35 updates, no new peak) · flow AGAINST since 10:43 · the engine's FOLD has not come. Out if: 22,770 fut accepted (premium there ≈ 38) · or 22650 CE writers leave (event). On this row the record holds both: losers held here (today, 10-05, 09-30) and winners that ran from here (09-24, 09-22). Your call.

Rule (shown, logged, never a verdict): ZONE is WITH and neither FLOW nor OI is WITH, for ≥ 2 bucket closes (CONFIRM). It clears when OI or FLOW turns WITH, or on the engine's FOLD.

### 5.4 PULLBACK vs GAVE UP — her definition, as a read beside the word
Printed only when the future is on the wrong side of her entry (fut vs E by d). [I], unsigned until its own forward count. The registered wording is PREREG-DRAFT.md §3.2:
- **OFF** := the engine's OI event on W, **or** W ≥ 10 % off its peak with ≥ 15 updates since the peak, not yet rebuilt (no new W peak since).
- **PULLBACK · HOLD stands** := not OFF, and no fight won against her inside the last 10 buckets (or the last one against her was ABSORBED).
- **GAVE UP** := OFF.
- **UNDECIDED** := not OFF, but a fight was won against her inside the last 10 buckets (flow pressing, the wall holding).
Each prints its two facts and its own falsifier (*turns back to PULLBACK if W makes a new peak*). It changes nothing in HOLD / FOLD. It is counted forward (PREREG §4.3 P6) to see whether GAVE UP minutes end in the engine's FOLD more often than PULLBACK minutes. REPLAY.md §3 shows it on three paths: today GAVE UP from 10:48 (57 min before the FOLD), the 09-24 winner's pullback a near miss (10 % reached with 11–14 updates, cleared on the new peak), 09-28 nothing printed.

### 5.5 The W-BLEED gauge (the slow leak)
Today at 10:44 the 22650 CE wall was −11 % and at 11:08 −15.6 % off its peak while the OI chip read WITH, then QUIET: the event test is `z = drop / (σ·√n) ≥ 3` with σ from the last 15 updates, and a slow bleed inflates σ as it goes. The gauge prints the plain number every second: *W 22650 CE: peak 200.7L 10:3x → 175.5L (−12.6 %) over 20 min, 15 updates, no new peak [M]* (10:48); its chip turns amber at ≥ 10 % off with ≥ 15 updates (h; OI_NOISE_N). It does not fold; it feeds §5.4 and the ledger.

---

## 6. UNIQUE — what she has not seen in a tool

### 6.1 KYA BADLA SINCE ENTRY — the ledger (picked)
At the mark the server freezes an **entry snapshot** (fut, spot, W oi/peak, A oi/peak, PCR(9), CVD, VWAP side, fights count, VPIN pct, premium, chips, daytype). Every second the face shows entry → now per row with the move and a WITH / AGAINST tag by her direction:

| fact | at entry 10:03 | now 10:48 | read |
|---|---|---|---|
| fut / spot | 22,741 / 22,657 | 22,749 / 22,665 (+8 against) | AGAINST |
| W (the wall behind you) | 22700 CE 229.4L | **22650 CE since 10:28** · 175.5L, −12.6 % off its 200.7L peak, 15 updates, no new peak | AGAINST |
| 22650 PE writers under you | 189.0L | 266.4L (+77L; +136L by 11:45) | AGAINST |
| fights since entry | — | buyers 2 (10:22, 10:43) · sellers 1 (10:27) | AGAINST |
| VWAP side | above (against) | above | AGAINST |
| premium | 55.0 | 48.65 (peak 65.2 at 10:22, given back 16.5) | — |
| zone | behind you: 22,788 | behind you: 22,770 (sellers won 10:22) | WITH |
| PCR(9) · CVD since entry | 1.36 · 0 | computed live from the grid and the ladder (not rebuilt in this design) | — |

Every number above is from the recorded chain and book [M]. A trade that is losing shows a column of AGAINST; the chips alone showed HOLD · behind you: zone, OI. This is the row she would have read at 10:48.

### 6.2 WHO IS IN PAIN — the counterparty row (picked)
The chain carries each leg's day-average traded price (`avg`). chain_metrics already uses *ltp ≥ 1.3 × avg* as "writers under water". Printed at her strike and both walls: *22650 PE: ltp 56 vs avg 73 — writers comfortable · 22700 CE: ltp 39 vs avg 30 — writers near their average · 22600 PE: ltp 37 vs avg 54 — writers comfortable*. The side in pain is the side that must move; a wall whose writers are comfortable is a wall that holds. [I] (avg is the day's traded average, not the writers' own).

### 6.3 Considered, not picked
- A "replay this press" button (what VALIDATE said at 10:03): useful, but RECORD already holds the engine's words per trade; add later as a row there.
- Pin-magnet distance with time left: folded into §2.4 / §2.7 as text.
- "Who topped first" clock: xindex X3 already prints it; it rides §2.3.
- A size suggestion: never ("leave the size to me").

---

## 7. The small new measurements (declared, so nothing hides inside composition)
1. `fold.flat_view` adds `vwap` (session VWAP off the ladder bars), `cvd` (per-minute cumulative b − s, [I] side), `sess` (hi / lo with times) — three sums over data the state already holds.
2. `read2.pin(chain)`: §2.4's definition.
3. `read2.pcr9(grid, t)`: PE/CE OI over `fronts.nine` at t, at 09:30 and at t − 60 min.
4. `read2.level_lines`: the merge and the confirms / denies sentences (§2.8).
5. `validate2.bleed(W)`: % off peak and updates since the peak, from `_OIWatch` (already tracked).
Everything else is a read of an existing reply.

---

## 8. One screen, 1080p beside the broker
A 760-px column (the broker keeps ~1,150 px), 1,000 px tall, no scroll in the two always-on bands:

```
┌ ABHI · 15:12:31 · ages book 0.2s chain 8s VPIN 1:40 GC dead 15:14 ───────── 15:00 practice: past ┐
│ NIFTY 0DTE  22,716 / 22,781 fut  TWO-SIDED 13:28  buyers' 9–2  boxed 22,676–730  Z QUIET F SELLERS O BUYERS V SELLERS │
│ BANKNIFTY 21d  55,180 / 55,405   RANGE   …                                                        │
│ SENSEX 2d   73,165 / 73,390      RANGE   …  (thin tape)                                           │
├ the mode card ─────────────────────────────────────────────────────────────────────────────────┤
│  [ slip: NIFTY · 22700 · CE · SELL · 30 ]  [ VALIDATE ]            [ MARKET READ ]  (Enter)      │
│  … the verdict / the read / the in-trade face …                                                  │
├ LEVELS TO WATCH · NIFTY ────────────────────────────────────────────────────────────────────────┤
│ ▲ 22,750 spot / 22,845 fut · 22750 CE writers 296L (ceiling) · confirms up: lifts … off its peak · denies: … │
│ ▲ 22,730 / 22,814 · the day high 14:07 · …                                                       │
│ ▲ 22,718 / 22,802 · 353 lots of buyers trapped 12:39 · …                                         │
│ ▼ 22,700 / 22,775 · 407 lots of buyers held 14:56 · …                                           │
│ ▼ 22,696 / 22,764 · 22700 PE writers 374L (floor, leaving) · …                                   │
│ ▼ 22,676 / 22,756 · VWAP · …                                                                     │
└ checked, nothing · could not check · not shown ────────────────────────────────────────────────┘
```
Always visible: ABHI (three indices, ages, the practice reminder) and LEVELS. On press: the mode card swaps. In a trade the mode card is the in-trade face and the two buttons shrink to a row. Every chip has a Hinglish tag in its hover and inline (saath / khilaaf / ruko / check nahi; likh rahe / kaat rahe; pahuncha / toota / fail). Light only; the DESK's `pro.css` tokens.

---

## 9. What this does NOT do
No order path. No size. No percentage anywhere. No candle-close gate. No new fold rule — the three new reads (zone-alone, pullback / gave-up, W-bleed) are printed beside the engine's word and counted forward; `PREREG-DRAFT.md` says how they are judged and when they are deleted.
