# The professional tool: Fable's blueprint, revised

**Written:** 2026-09-28, after the close. Read-only: nothing edited, started or posted.
**Revises:** `1-fable-blueprint.md`, against `2-opus-critique-of-fable.md`, `1-opus-blueprint.md`, and H v3 (`H-reader-spec-v3.md`, `H-changes-v3.md`, both present and final).
**Re-checked tonight [M]:** `data/chain/chain_NIFTY_2026-09-28.jsonl` (the 22850 PE series, the wall ranking at 09:30 and 14:28), `data/book/book_NIFTY_2026-09-28.jsonl` (the visible depth span), and every FIRST FIRES line in `scratchpad/fb/*.txt`.
**Tags:** [M] measured, [I] inferred, (h) hand-picked.

---

## 0. What changed and why

| # | the critique said | checked | what changed |
|---|---|---|---|
| 1 | The one entry refusal says NO to her own put (room 41 < give-up 56–72) | **True** [M]: forward 22940.6, wall 22900 PE, G 23013 → 22997 | **The refusal is gone.** Room and give-up are printed as two distances; nothing refuses. Three amber clauses instead (§3). |
| 2 | "22850 PE giving all along [M]" is false; the [M] was never run | **True** [M]: seven new highs 10:40–14:01, the real give was −55L in 27 min, 14:01→14:28 | **AT THE WALL is no longer a word.** It is a line, profit-gated, event-born (the OI event on the wall ahead, frozen with its time), in her-side colour, silent (§2.4). My [M] is withdrawn. |
| 3 | The replay table reports held-breach times where flow + OI fired first | **True**: I printed `flow_held` first fires | Table rebuilt from the traces with the engine's actual first fire (§2.6). |
| 4 | On losers the 2-close confirmation never bought a better exit; today's call −25 v −17 | **True** in 8 of 8 | **Two modes, grafted from Opus:** loser = acceptance alone; winner = flow + OI or the held breach, whichever first; backstop at her entry. |
| 5 | "Pros bank into a holding wall" would print at −25% on today's call | True: A was picked against F, not her entry | The bank line only when G is past her entry (winner mode). In a loser the only line is where the trade is wrong. |
| 6 | SELL only in a box misses how she sells (ATM/ITM with the trend); BUY keyed on fights flips 8/h | True (how-she-sells, 09-26) | Expression rewritten: selling with the trend is first-class; the read is at bucket closes, 2-close confirmed, frozen when the mark row opens (§3.2). |
| 7 | GAVE UP persistence unspecified | True | GAVE UP stays until I'M OUT; the live read continues on the line under it, never in its place (§2.3). |
| 8 | Premium at G: linear delta under-states expiry gamma | True | Read from the chain's own prices at the same distance, not from a greek (§7). |
| 9 | Precedence hides BEHIND YOU / TIRING for hours | True | AT THE WALL is a line; **TIRING is a clause, not a word**, which also halves the 24 Sep word rate (§2.3). |
| 10 | No chip gate; ZONE and VPIN churn | True: 8.4–11.6/h on 3 trades | ≤ 6/h is an acceptance gate. ZONE becomes event-born; VPIN leaves on 2 closes past zero (§2.5). |
| 11 | "One wall rule" is three; day-high keeps an abandoned wall | Half true: one ranking, two windows. The 14:28 example is wrong: at 14:28 the forward was 22824.6, so 22850 PE was in the money and no candidate under any rule [M] | Ranking is by **current** OI with the 2-close hold (§2.2); the two windows are named as two. |
| 12 | Live face before shadow; chart trust after the roll; Trade tab hidden; knobs for her | All true | Build order is Opus's: plumbing before Wednesday, `fold.py` in shadow, faces on her signature. Trade tab stays in the strip. `FOLD_NEEDS` and "her two numbers" are gone; the held-breach count is 2, decided here (§8, §9). |
| 13 | Resting liquidity at G is a touch read, not a lead | True. My measure: the five visible levels each side span a median 11 pts, 90th pct 13.6 [M] (28 Sep; theirs 2–4 is one side). G sat 18–72 pts away | Scoped to "while price is at G or at A" (§6.2). |

**Kept against the critique, with the evidence:** the held breach on winners (Opus took it: 24 Sep +98 v +81); the three screens; SENSEX never borrows NIFTY's clock; the October record on 09-29; the extra chart-trust checks; the falsifiers for TIRING and FAILED; the forward\* reference everywhere; the tabs cut in §1.

**What neither of us solved, still:** the 15-minute expiry-gamma V (22 Sep +264 → +77); PULLBACK ↔ BEHIND YOU alternation on trend days (fights are fights; the word follows them); and the early-bank pull, which this revision removes by rule but only the forward log can confirm.

---

## 1. The trader's day, and the screen for each moment

| moment | one glance | screen |
|---|---|---|
| **Pre-open** | Yesterday's high/low/close/POC *for this contract*; the two biggest walls each side of the forward from yesterday's last same-expiry snapshot; expiry / roll / feeds alive | DESK · FLAT header + THE DAY |
| **The open** | Who the gap trapped, against yesterday's close [I]; the first fight; chain, book and VPIN reading from their first mark ("n of 5 bars", never "blind until 09:35") | DESK · FLAT |
| **Flat** | "Next fight: 22901 above · 22885 below", what confirms a put or a call at each; the re-entry read after an exit | DESK · FLAT (§4) |
| **Entering** | The four reads at this level; where G would sit and the premium there; the wall ahead and the premium there; buy or sell the other side; the amber clauses | DESK · IF YOU ENTER NOW (§3) |
| **In a trade** | The word; the four chips; G and P&L at it; given back since the peak; the wall you played for and its writers' state (winner mode only) | DESK · IN A TRADE and the panel (§2, §5) |
| **Exiting** | GAVE UP with its two facts, frozen; never a size | same |
| **After** | Who is trapped now, the next fight, the trade's word history | FLAT, RECORD |
| **End of day** | Her marked trades beside the engine's words; falsifier counts, never rates | RECORD |
| **Any time** | When each wall was built, is it held, which front retreats | WAR |

**Cuts (as v1):** Glass, Heat, Tape, Flow, Chain, OI Flow, Map, Events, Board rev 3 (its lines become DESK-FLAT line one and THE DAY), the VPIN tab (its gauge's forward log continues unseen). **Trade stays in the strip** until she says otherwise: her order kept its chart, and hiding it is not an agent's cut. `App.tsx`'s mock first paint goes (Opus): invented prices on first render are a lie.

---

## 2. The exit and the hold, as a professional makes it

### 2.1 What I check before I change my mind

1. **Accepted beyond the point where I am wrong, or touched?** A stop-run touches; a breach trades there for a while.
2. **At the level, initiative or absorbed?** Hits at my floor with price not following: pullback. Hits followed by price: the other side winning.
3. **Did my defenders give up after I entered?** The wall that sets my give-up: building, stopped, or off its peak by more than its own noise. Only since entry counts.
4. **Am I a winner or a loser right now?** Not by premium: by whether my give-up has trailed past my entry. A winner earns the benefit of the doubt; a loser does not.
5. **Am I at the wall I played for, and are its writers leaving or adding?** Only worth asking as a winner.
6. **Tiring?** Lowers what I expect; never an exit alone.
7. **Informed flow with me?** VPIN from the same fills the ladder books.
8. **Given back since the peak, and the clock.** Expiry gamma after 13:30; her 15:00 practice.

Her sentence, "somebody gave up, OI stopped building or off from the peak", is checks 1 + 3, and it is the *winner's* rule. A loser is wrong on location and does not wait for OI. Opus was right that these are two questions asked at two places; v1 had one rule with a time floor on top, which cost 8 points on the trade that mattered.

### 2.2 The engine: `fold.py`, one instance per marked trade

**Clock, noise, fights, levels, traps, G, W, the OI event, acceptance: H v3 §3–§7, unchanged.** Every threshold is a count on the volume clock, a ratio, a multiple of B, or a multiple of the strike's own OI noise.

**One ranking, two windows (fixes v1's "one wall rule"):**
- The ranking is by **current OI** on the defending side, with the §4 hold (a new choice must stand 2 bucket closes, or the forward is w through the old wall). Day-high is dropped: it can only keep a wall whose writers have left. On 28 Sep current and day-high gave the same top three at 09:30 and at 14:28 [M], so nothing in the replay moves.
- **W** (behind her): the most current OI between F and G; chosen only when G is set (H §6.1).
- **A** (ahead): the nearer of the top two by current OI beyond F by w on the far side, at K + basis, at least w beyond her entry.

**Mode** (grafted): `winner` if d·(G − E) > 0, E her entry future price; else `loser`. Re-read whenever G changes; G only steps on wins, so it cannot flap.

| mode | GAVE UP fires on |
|---|---|
| **loser** | acceptance beyond G (1 bucket of business over ≥ the median bucket time, no print w back inside) |
| **winner** | acceptance **and** a live OI event on W in the same epoch (her rule), **or** the held breach: an acceptance that stands 2 (h) more bucket closes and ≥ 2× the median bucket time with no win by her side and no print w back inside (v1 A, kept, winner only) |
| **backstop** | winner mode: acceptance beyond E ∓ w. A winner never becomes a loser. |

The held-breach count is **2**, decided here as a trader, not offered to her. `FOLD_NEEDS` is gone: the mode picks the rule, there is nothing to flip.

### 2.3 The words

Precedence: GAVE UP > PAST GIVE-UP > the newer of FAILED LOW/HIGH and the newest fight's winner > NO READ. Words are computed once per event batch.

| word | moved by | style · sound |
|---|---|---|
| **GAVE UP · level lost / gave up: 22900 CE writers left 11:42 / back through your entry · hh:mm** | §2.2, by mode | ink block · two low tones, once per epoch, ids kept across reloads |
| **PAST GIVE-UP** | winner mode: G accepted, W still holding | amber · none. Row: "out if 22900 CE writers leave, or if 22941 (your entry) is accepted" |
| **FAILED LOW / HIGH** | H §7.1 (new extreme ≥ w, rejected ≥ w) | ink · none |
| **PULLBACK · since hh:mm** | the other side won the newest fight; G not accepted | amber tint · none |
| **BEHIND YOU** | her side won the newest fight | ink · none |
| **NO READ** | no fight and no wall yet | grey |

**TIRING is a clause on the word, not a word:** "BEHIND YOU · tiring 6 min". In (2 stalled closes in 5), out (2 non-stalled), as H. On 24 Sep this removes every TIRING transition from the 44 word changes; what remains is fights (PULLBACK ↔ BEHIND YOU), which are the tape.

**After GAVE UP:** the word stays, frozen with its reason and time, until she presses I'M OUT or unmarks. The line under it keeps reading live: "still marked · now: your side won again 12:35". It never reverts in place. On 28 Sep's call the acceptance withdrew at 12:29 and returned at 12:34; the son would have seen GAVE UP 10:16 the whole time, with the live line changing beneath it.

### 2.4 The wall ahead: a line, not a word

Shown only in winner mode, never sounded, never a fraction:
- **"at 22850 PE, the wall you played for · writers pulled 55L since 14:01 [M]"** when the same 3σ√n OI event fires on A (event-born, frozen with its time, ink in her-side colour: writers leaving the wall ahead is her fuel, not a warning);
- **"at 22850 PE · writers adding, high 12:51 · pros bank into a wall that holds"** when business is within θ of A for 2 closes and A made a new since-reference high within 15 updates;
- otherwise "at 22850 PE · n min" with no clause.

On her put this prints nothing before 10:17 (loser mode), then the bare line from 10:42, "adding" through the seven new highs, and the pulled-55L line at 14:28, 10 minutes before the day's best print. On today's call it prints nothing at all: the trade was never a winner.

### 2.5 The four chips, and the gate

ZONE · FLOW · OI · VPIN as H §2, with two changes for churn (ZONE 12–22 and VPIN 8–16 changes per trade were the offenders [M]):
- **ZONE is event-born:** it changes when a level is born, broken (F w through it) or taken by a fixed fight; proximity ("trading within w of their level") is the ZONE row's sentence, not the chip.
- **VPIN** enters at lead ≥ 2 as before and **leaves only after 2 closes past zero** (h).

**Acceptance gate, from Opus:** ≤ 6 chip changes an hour and ≤ 4 word changes an hour on every recorded trade, or the chip rule is wrong and goes back to replay. v3 met the chip bar on 4 of 8; the two changes above are re-run before Phase 1 ships.

### 2.6 The replay, corrected: 8 trades, 5 days, exits by the engine's actual first fire [M]

| trade | best | mode at exit | **this engine** | v3 flow + OI | Opus PRO-1 |
|---|---|---|---|---|---|
| 22 Sep put @ 47.75 | +264 | winner from 10:42 | **+77 · 14:19** (flow + OI; held would be 14:24 +70) | +77 | +77 |
| 22 Sep call @ 43.65 | +78 after −61 | loser | **−42 · 13:51** | −42 | −42 |
| 23 Sep put @ 122.3 | +3 | loser | **−12 · 12:04** | −12 | −12 |
| 25 Sep put @ 111.6 | +42 | winner from 09:39 | **+7 · 10:08** (whipsaw; held 10:09 +7) | +7 | +7 |
| 25 Sep call @ 96.5 | +53 after −29 | loser | **−10 · 09:47** (whipsaw, withdrawn 49 s later) | −19 | −10 |
| **28 Sep call @ 84.05** | 0 | loser | **−17 · 10:16** | none, −61 | −17 |
| 24 Sep put (hindsight) @ 102.65 | +154 | winner from 11:58 | **+98 · 14:39** (held; flow + OI 14:55 +81) | +81 | +81 |
| **28 Sep put, hers** @ 120.4 | +97 | winner from 10:17 | **none · +71 at 15:00** | none | none |
| sum | | | **+172** | +102 | +155 |

What it says: losers leave at their level (−42, −12, −10, −17); winners hold through pullbacks (her put through 09:48–10:17 and the 12:29 push; 24 Sep through two withdrawn acceptances). n = 8 describes; the forward log ranks. The 25 Sep call at −10 is a shake-out; a loser shaken out that later runs to +53 is a re-entry (§4), not a regret.

**Falsifiers, logged 30 sessions, counts only:** GAVE UP (loser) wrong if back inside G by w within 20 min; (winner) the same or W rebuilt above the event's peak; the wall-ahead "pulled" line wrong if A rebuilds above the peak within 20 min; PULLBACK wrong if G is reached; TIRING / FAILED wrong on a new extreme by θ; PAST GIVE-UP wrong if the entry is lost.

**Writers:** the same engine with d flipped; her short strike against the forward is always a level.

---

## 3. Entry

### 3.1 No GO, no NO

The entry check is the in-trade face for a hypothetical mark, headed **IF YOU ENTER NOW**: the four chips with their sentences; **give-up:** where G would sit, why, and the premium there [I]; **room:** A, its OI and state, the premium there [I]; **what falsifies it**; **premium / theta:** her strike against its day VWAP (σ, printed, never counted), days to expiry, the expiry-eve flag.

Room and give-up are two printed distances. **Nothing refuses.** The 41-point room against a 56-point give-up on her put was the trade of the day because the wall ahead gave; a ratio refuses every trend trade at its first wall.

Three amber clauses, never a big word: "you would enter past your give-up"; "you would enter at the wall ahead, where pros bank"; "after 15:00: your practice is no new trades".

### 3.2 The expression: buy the option, or sell the other side

Her practice (09-26): she sells ATM or ITM *with* the trend, and exits by zones, levels, flow and OI, never the strike. So the expression is a choice between two directional trades, read at bucket closes, confirmed on 2 closes, and **frozen when the mark row opens** (so it cannot flip with fights at 8 an hour):

| read | when |
|---|---|
| **BUY the option** | the newest fixed fight her way was pushed (initiative) **and** A is off its peak or covering (fuel), and it is not expiry day |
| **SELL the other side, ATM (ITM in a trend)** | her direction, and any of: expiry day or eve (theta is hers); the last fight her way was absorbed rather than pushed, or tiring is live (a grind, not an impulse); A is adding (the move will be earned, not given); or a box (both walls adding, VPIN quiet) |
| **EITHER** | neither set holds |

Refusals stay EXPRESSION rev e's R2 (never sell into a squeeze) and R4 (never sell a bid straddle). ROOM and REGIME go with the line and the trend. The sale is folded by the same engine, d flipped: no reach, no strike stop.

---

## 4. Flat

Line one: **"Next fight: 22901 above · 22885 below"**, the two nearest strong levels (walls, held levels, trapped shelves, the prior day), hysteresis w; within w of one: "At 22899 (22900 CE wall) · 22919 above · 22885 below".
Under each, the confirmation that makes it a trade (Opus, grafted): "above: lifts at 22905–22910 followed by price **and** 22900 CE off its peak: sellers gave up, calls"; "below: hits at 22860 followed by price and 22850 PE off its peak: puts". When both halves fire the flat word is an event, frozen, silent: "SELLERS GAVE UP AT 22907 · 11:42".
**Re-entry read** (grafted): after GAVE UP, if trading comes back w inside G and her side then wins a fight, FLAT says "stop run failed at 22925: sellers won again 12:35". With free execution a re-entry costs the spread; a missed exit cost 61%.
AFTER A MOVE and THE DAY as v1.

---

## 5. The faces

One frame, both screens; one poller (`/api/hold?id=`, and `fold` inside `/api/frame`); the panel is the same blocks at 400 px.

```
│ NIFTY OCT FUT · read 11:42ᴹ · contract ✓ · chart placed     │ header (EXPIRY · Γ after 13:30; "flat by 15:00" from 14:45)
│ long 23000 PE · 120.4 · 09:30                  [ I'M OUT ]   │ her trade, or MARK TRADE
│ BEHIND YOU · tiring 6 min    ZONE▪ FLOW▪ OI▫ VPIN▫           │ line one: word + clause + chips
│ gives up above 22925 · set 11:05 · winner · at it ≈ 150 (+25%)│ line two: G, mode, P&L at G [I]
│ PE 175.5 (+46%) · peak +46% 11:14                            │ line three: premium, given back
│ at 22850 PE, the wall you played for · writers adding, high 12:51 │ line four (winner only)
│ FLOW  sellers won 11:04 at 22879 (369 v 42) [M]              │ four rows, one sentence,
│ OI    22900 CE writers building, high 11:41 [M] (writers [I])│ one tag each
│ VPIN  4 of 10 buckets one-sided, 3 sell [M]                  │
│ ZONE  behind you: the 22900–22907 lid, 7 pushes absorbed [M] │
│ THE DAY  one paragraph                                       │
│ ▸ detail                                                     │
```

**Budgets:** ≤ 24 numbers with detail closed; 5 colours (blue helps buyers, red helps sellers, amber watch, ink hers, grey reference/absence; in a trade WITH means her side); 5 blocks; ≤ 480 px above detail; 3 + 3 levels on the chart; 7 glyphs; sounds: GAVE UP only.
**No flicker:** events frozen at birth; condition-born chips 2 closes; a named wall holds 2 closes; the give-up is a staircase; **the DOM is patched, never rebuilt** (`panel.js:515`'s innerHTML rebuild kills `<details>`, B §2.9, grafted).
**Marks on the chart:** from the event log at frozen (time, price); ▲▼ pushed, △▽ pressing, ▬ absorbed, ⌃⌄ failed, ▸ entry, ■ GAVE UP, dashed give-up staircase, dotted wall lines with strike chips at K + basis; a 5 px glyph floor, nothing removed at any zoom. Cut: ROUND lines, the flat σ pocket, the event strip, per-strike pain chips, trap discs.
**Chart trust:** price fit, time fit, **fit only TapeMap's session day** (`fit.js:194–203` is the session-jump bug), fitted latest bar within one bar, **bar OI = TapeMap's future OI** (contract match), hysteresis 2 bad / 2 good. Any failure: "chart shows another day / contract since hh:mm; marks paused, panel live".
**Mark my trade, both screens:** Mark trade → CE/PE → MARK; strike prefilled ATM against F\* with ATM / ITM 1 / OTM 1 steps; the entry premium frozen when the row opens; she types her fill; the panel posts through `sw.js` to `/api/hold/trades` after the `Sec-Fetch-Site: none` build test; restarts never lose it (`data/day_state/`). TapeMap down reads "your trade: could not check — TapeMap not reachable", never FLAT.
**Light only. No candle words. "Flat by 15:00" is a reminder, never a rule.**

---

## 6. Remove, and what is missing

### 6.1 Remove (inside the one amendment)

| what | where | why |
|---|---|---|
| The session-high line, 3-min close, Noise B; Room, Cushion, the plan's ₹ risk from it | `hold.py`, rev 5 B, PLAN 3 §2.1 | A candle close; she banned it |
| Trend as a fold family and WATCH; `trendbox` | `hold.py`, validate, expression | Not one of her four |
| The quiet clock, PERSIST = 3, the FOLD latch and heal | `hold.py` | Time rules on a lagging read; the latch froze a wrong FOLD all day |
| 15-mark OI warm-up, 4-bar flow warm-up, 3-min expression cadence | `fronts.py`, `grounds.py`, `expression.py` | Everything reads from its first mark, "n of 5" |
| Five wall rules | fade gate, board.nearer, board headline, plan rung, expression WALL | §2.2: one ranking, two windows, `fronts.py` owns it |
| Spot as the moneyness reference | `board.itm/nearer`, plan, hold ITM/OTM, expression ATM | Off by 24–46 pts on 28 Sep [M] |
| GO / WAIT / NO; the Room ratio; `FOLD_NEEDS` | `validate.py`, v3 §1 | §3, §2.2 |
| `gate.py` (always PATA NAHI), `senses`/`ivrv` None fields, the ballot, `watch.py`, breadth footer, ROUND, both WRONG IFs, the event strip, σ bands drawn flat, the dark panel theme, the mock first paint | frame.py, panel.js, overlay.js, App.tsx | Fields that can never fill, or duplicate her chart |
| The tabs in §1; `/api/calls` as a screen; `runs.py`'s name for fights | App.tsx, grounds.py | No moment needs them; the forward-log rows stay |

Kept by her order and untouched: Dhan/Upstox fallback, `structure.py`, `band_rotation.py`, `contract_pair.py`, the Trade tab and its chart files, `/api/surface`, `/api/drag`, `/api/paper_fill`, the zone's 09:25 anchor, `trigger_log.jsonl`.

### 6.2 Missing, that a professional would demand (each ships in shadow, gating nothing)

1. **Resting liquidity, scoped honestly.** The book's five levels span a median 11 pts, 90th pct 13.6 [M]. It reads only while price is at G or at A: "offers at 22925 stacked 1.2k, 60% pulled this bucket". It is the acceptance's companion (offers pulled while price sits beyond G = the breach holding), never a lead.
2. **Big prints:** a fill ≥ the 99th percentile of today's sizes so far [M], at a level, side if the ladder signed it [I]. One line in FLOW.
3. **Failed auction at a day extreme** in FLAT (FAILED already covers it in a trade).
4. **The roll and expiry** (§7); the next-weekly chain on expiry days.
5. **SENSEX policy:** its future prints a median 7–10 lots per 5-min bar [M]. FLOW and VPIN read CAN'T CHECK with the count; no fights, no traps; ZONE and OI as NIFTY; in a trade the fold is the loser/winner split on OI plus price beyond G for **SENSEX's own** median bucket time, flagged. It never borrows NIFTY's clock.
6. **The GoCharting tick post** (`adapter.js:133–151` has sides), used only to dispute a fight; tape agreement printed in RECORD. Kill: > 1 fight in 3 disputed over 30 sessions → FLOW stops printing sides.
7. **The persisted event log** `data/fold/fold_<IDX>_<day>.jsonl` with every threshold in force; a restart replays to byte-equal words.

---

## 7. Data truth

| defect | handling |
|---|---|
| **Spot v forward:** the chain's spot runs 24–46 pts under strike + CE − PE (28 Sep) [M] | F\* = future − 15-min median basis over strikes with \|Δ\| > 0.3, everywhere moneyness, ATM or a wall is judged; `spot` is never a reference |
| **Premium at G and at A [I]** | Read from the chain's own prices: the premium of the strike whose distance from F\* now equals her strike's distance from G (K′ = K + F\* − G), interpolated between the two nearest strikes. Market prices carry the convexity a linear delta misses; the feed's greeks are a model. Logged against her fills as a falsifier. Chain older than 60 s: "could not check — chain 70 s old". |
| **Guessed-side volume 24–59%** [M] | \|b − s\| > 2G and imbalance ≥ ½; sweeps signed by price at θ, tagged [I]; else "could not check: n of 270 guessed" |
| **Three tapes disagree** (63–65%) [M] | VPIN rebuilt from the ladder's fills; GoCharting disputes only |
| **Book and chain start 09:17** [M] | Subscribe before 09:15, centred on the previous close; until then "blind before 09:17:19, 1,639 lots unseen"; the 09:15 bar never scored |
| **The roll, 09-29 → Oct** | BUGFIX #6 is in. Tonight, if she restarts: the recorder also writes the Oct future's book and ux on 09-29 so Wednesday's bucket, B and prior-day levels are Oct's own. If not: Oct's first 15 minutes (h), flagged, and prior-day levels "could not check", never Sep's shifted by carry. Every row gets an `expiry` / `instrument_key` stamp; `fut_oi` breadth blind for the near contract in expiry week. |
| **Expiry day** (09-29: NIFTY weekly + Sep future + BANKNIFTY monthly) | The OI event runs on the expiring series against its own closing pace (H §8, post hoc, flagged); the OI row says so; EXPIRY · Γ in the header after 13:30 |
| **OI baseline = the 09:15 candle** (hid 23100 PE −26L on 28 Sep) [M] | Baseline = the previous session's last snapshot, same expiry, else the 09:15 candle and it says so; missing = "could not check", never 0 |
| **Rows 2 minutes late** [M] | The 1-minute candle built from socket ticks; REST reconciles later, tagged |
| **fit.js session jump** [M] | Single-day candidates from `frame.day` plus the contract match; a test: a chart with no date tick whose margin time exists on Friday must read "not trusted" |
| **VPIN first buckets / backfill** | CAN'T CHECK until 10 live buckets; backfilled buckets tagged, never counted |
| **Restart** | The event log replays; the trade returns from `day_state`; the test diffs a rebuilt day against the live log |

---

## 8. Build order (nothing in market hours; she starts the server; commits on her word)

**Phase 0 — tonight and Tuesday after the close, before Wednesday's first October session. Plumbing, no method change.** (a) `fit.js` single-day fit and the contract match; (b) contract stamps on every recorded row; (c) the Oct future recorded on 09-29 (tonight, if she restarts; else the flagged fallback); (d) the yesterday-close OI baseline, same expiry; (e) the panel to LIGHT tokens, patch-not-rebuild. Tests: the fit fixture in node, the existing roll test, one `day_state` restart test. This is Opus's order and it is right: the roll bites Wednesday, and my v1 had chart trust "next week".

**Phase 1 — `fold.py` in shadow, this week.** Pure, stdlib, fixture-first from `scratchpad/fb/reader7.py`, with one `__main__` self-check: her put reads no GAVE UP; the 28 Sep call reads GAVE UP · level lost at 10:16. `server.py` runs it for every marked trade and appends to `data/fold/`. Visible only as one grey line in Validate's detail: "shadow · rev 6 says: PULLBACK". `hold.py` (rev 5 with BUGFIX #1–6) keeps the face as signed. **Gates before she is asked to sign:** every recorded day replayed with no fold on arrival, ≤ 1 sound/h, ≤ 6 chip changes/h, ≤ 4 word changes/h, exits printed against the best; a mid-session restart replays identical words. The shadow needs one live session to prove the restart; the gates run tonight on disk. So her signature can be Wednesday after the close, and the face Thursday.

**Phase 2 — on her signature: the faces.** Validate's hold section switches to `fold.read`; `hold.py`'s removed rules go in the same commit, tagged `pre-rev6`; `/api/frame` carries `fold`; the panel rebuilt to §5 with mark-my-trade via `sw.js` and marks from the event log.

**Phase 3 — entry, flat, expression:** IF YOU ENTER NOW, the amber clauses, the expression at bucket closes, NEXT FIGHT with confirmations, the re-entry read. Each forward-logged from day one.

**Phase 4 — the cuts** (§1, §6.1), one commit per group, tagged before. **Phase 5 — the missing reads in shadow** (§6.2), pre-09:15 subscription last because it touches the feed.

---

## 9. The amendment she signs once (rev 6)

Rev 4 §1–§8 and §10, rev 5 §A–§G, VALIDATE 2 §1.2–§5, EXPRESSION e §A.2–§E.2, PLAN 3 §2.1 close as they stand; their rows stay in their own populations.

Rev 6 registers: the four chips and their event/condition rules; the words, the TIRING clause and their precedence; G / W / A with one ranking and two windows; the OI event; acceptance; the two modes, the held breach (2 closes, 2× time) and the backstop; the wall-ahead line, profit-gated and silent; GAVE UP persistence; the forward\* reference; premium at G from the chain's own prices; the entry face with no refusal and three amber clauses; the expression with selling-with-trend first-class; the flat confirmations and the re-entry read; every threshold with its (h) mark; the falsifiers; the fields each row logs.

**Nothing is asked of her but the signature.** No switch, no count, no knob a son turns mid-trade.

*Ceiling, stated:* eight trades on five days describe. Thirty forward sessions decide; the tool prints counts, never rates. What the log must answer first: in winner mode, does waiting for the writers beat the held breach alone (22 Sep says wait, 24 Sep says do not), and does the silent wall-ahead line stop her banking early, or merely stop the tool telling her to.
