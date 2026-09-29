# The pro tool: final blueprint (the judge's merge)

**Written:** 2026-09-28, after the close. Read-only on code and data. Nothing was edited, started, posted or committed outside `docs/pro-tool/`.
**Merges:** `3-fable-blueprint-revised.md` and `3-opus-blueprint-revised.md`, after both critiques (`2-*.md`), both originals (`1-*.md`), H v3 (`H-reader-spec-v3.md`, `H-changes-v3.md`, final at 15:32), G v2, TRADER-AUDIT (its CORRECTION first), PONYTAIL-REVIEW, BUGFIX-2026-09-28 and her doctrine files.
**Re-checked tonight [M]:** `chain_NIFTY_2026-09-28.jsonl` (her put, the 22850 PE wall, the forward), `book_NIFTY_2026-09-28.jsonl` (visible depth), `fit.js` and its uncommitted diff, `panel.js:515`, the `/api/hold/*` door in `server.py`. Script: `scratchpad/judge/ev.py`.
**Tags:** [M] measured, [I] inferred, (h) hand-picked.
**The one amendment she signs:** `4-amendment-draft.md`.

---

## 0. Her question, answered

> "as a trader who made a trade will he fold exactly [on one condition]?"

**No.** A professional asks two different questions, at two different places, and says in advance what would change his mind.

1. **Is the trade wrong?** Price has been *accepted* past the level he entered on. That is a stop. It does not wait for OI.
2. **Are my defenders gone?** Only once the trade is paying for itself (the give-up has trailed past the entry) does he give it rope. Then he folds on her own rule: the flow is accepted past the give-up **and** the writers behind him came off their peak. He also folds if that acceptance simply holds, and he never lets a winner go back through his entry.
3. **Is the trade done?** The tape in this sample never named a top (§3.6). So the tool gives no bank verdict. It shows the wall ahead in numbers, the peak premium and what has been given back. She banks.

**Her put today, on this engine.** 23000 PE at 120.4, 09:30.
- The screen reads HOLD all day. Line 2 names what would take her out, in advance.
- At **14:12**, where she exited at **164.8** [M], the screen still read HOLD. The wall ahead line read: "ahead 22850 PE · 145.6L, peak 151.7L 14:01".
- By 14:20 that line read 98.5L: the writers under the move pulled 47L in eight minutes [M]. The put printed 210.6 at 14:20 and 236.95 at 14:38 [M].
- The tool never told her to bank. The number falling was the fuel, and she could see it.

---

## 1. Who won each disagreement, and why

| # | disagreement | winner | the deciding evidence |
|---|---|---|---|
| 1 | Loser exit: acceptance alone (both revised), v1 time floor | **Both agree** | Opus `PL_*`: a time floor on losers cost 33 pts over 4 losers, and turned the 22 Sep call into a noise exit at −53 instead of a real one at −42. The whipsaw is answered by the re-entry read, not a slower stop. |
| 2 | Winner exit: flow + OI, or the held breach | **Both agree** (Fable's held breach, grafted by Opus) | 24 Sep: +98 v +81. It closes the slow-bleed hole the √n test cannot see. |
| 3 | The entry backstop (winner mode, acceptance back through E ∓ w) | **Fable: kept** | Opus is right that it decided no exit in 8 trades. It is kept anyway, because it is tail protection. Suppose price runs from G to E in less than about 2× the median bucket time. That is the expiry-gamma V (22 Sep: +264 → +77 in 15 min). The backstop's tally then completes before the held breach can, and it is the only rule that stops a winner going red. It costs no noise, because it can only fire past both G and E. |
| 4 | The headline: six words (Fable) or three states (Opus) | **Opus** | Headline changes fell to 0–0.7 an hour on all 8 trades, against 4–8 an hour. PULLBACK flashing 15 times on a trend day (G, 24 Sep) is a nudge out for the trader whose stated problem is holding. The fight tape moves to a clause under the headline. |
| 5 | The exit word: GAVE UP (Fable), OUT (Opus) | **Neither: FOLD** | FOLD is her word ("if these are behind me i will hold and not i will fold"). OUT would collide with her own **I'M OUT** button: the tool's read and her action must never share a word. "Gave up" lives in the reason: "FOLD · 22900 CE writers gave up 11:42, 22925 accepted". |
| 6 | The wall ahead: an event-born verdict plus "pros bank into a wall that holds" (Fable), or numbers only (Opus) | **Opus** | Tonight's replay of the same 3σ√n event on 22850 PE from 10:42 [M]: it **fired at 11:16, 11:57, 12:53 and 14:16**, and withdrew three times while the wall made new highs. Opus counted 9 with its harness; mine counts 4. Either way, Fable's "writers pulled" line would have printed three false times before the real unwind. Its "pros bank" clause would have stood under her put for 3.5 hours at +20% to +45%. Numbers with the peak show the 14:12–14:20 unwind plainly. |
| 7 | Show "winner/loser" on the face | **Opus: hidden** | A son reading "loser" trades his feelings. Line 2 states the out-condition, which is what the mode means. |
| 8 | Expression: BUY needs "A off its peak or covering" (Fable) or "A not adding" (Opus) | **Opus off expiry, Fable on expiry day** | Off expiry, "off its peak" flaps (see #6); "not adding" is stable. On expiry day, both drafts forbade BUY outright. That rules out the 0DTE impulse buy that paid +264% on 22 Sep and that she trades (the 24 Sep SENSEX puts). On expiry day, BUY therefore needs initiative **and** the wall ahead off its peak, because gamma only pays a buyer when writers are running. Otherwise SELL. |
| 9 | The chip gate: all four chips ≤ 6/h (Fable), or FLOW exempt (Opus) | **Opus, flagged post hoc** | FLOW is event-born and *is* the fight tape. Delaying it hides the tape. ZONE event-born and VPIN out after 2 closes (Fable's two candidates) go into the registration. Its signature waits for the gate table (P2-04). |
| 10 | Bucket and B across the roll: the Oct contract's own record (Fable) or front-month pooling (Opus) | **Opus** | Oct traded as the far month all month. Its own volume history would shrink the bucket and speed the clock on Wednesday, the wrong way. The front month's volume is the market's clock. Price levels (PDH/PDL/PDC) remain the **contract's own**, never Sep's shifted by carry. |
| 11 | The OI baseline in Phase 0 (Fable) | **Opus: not before Wednesday** | Tuesday's last snapshot is the expiring weekly, and the 6 Oct series was never recorded, so Wednesday reads "could not check". A cheaper route, graft [I]: if Upstox's REST option chain carries the previous close OI per leg, that gives Wednesday its baseline without a recording. P2-05 checks it with one call. |
| 12 | Resting liquidity: 11 pts (Fable) or 2–4 pts (Opus) | **Both right** | 28 Sep [M]: the five visible levels span a median 11.3 pts in total, 90th percentile 13.6; per side, a median 4.1 bid and 2.0 ask. It is a touch read, scoped to "while price is at G or A". |
| 13 | "One wall rule everywhere", including the fade gate (both) | **Neither: the judge's correction** | The fade gate is §1d, signed, and it feeds `trigger_log.jsonl`, the irreplaceable forward record. Changing its wall rule, or its moneyness reference, would split her zone population. **§1d keeps its own rule, untouched.** The one ranking governs the new engine and every face; a §1d change would be its own registration, which nobody is asking for. |
| 14 | The re-entry read: "costs the spread" (v1) | **Opus's correction** | It costs the move back. 25 Sep call: out at 86.65, re-entry read at 10:24 with the premium at 100.9 [M]. The read prints both. |
| 15 | Tabs | **Agreed** | DESK, WAR, RECORD, plus the Trade tab (her order) and the panel. Board's flat lines go into DESK · FLAT. Her pending Board-mockup review decides only the layout. |
| 16 | Build order | **Opus's, tightened** | Plumbing before Wednesday, the engine in shadow, faces on her signature. Phase 1 below is only what is safe to run on 09-29 and 09-30. |

**What neither side solved, stated.** The 15-minute expiry-gamma V: the backstop and the given-back line are the protection, and she decides. PULLBACK ↔ BEHIND YOU alternation on trend days: it lives in the clause now, which moves the flicker without removing it. Whether "no bank verdict" helps her hold: only her forward log can answer that.

---

## 2. The trader's day

| moment | one glance | where |
|---|---|---|
| **Pre-open, 09:00–09:15** | Contract and flags (expiry, eve, roll). Yesterday's high/low/close **for this contract**. The two biggest walls each side of F\*, from the last same-expiry snapshot, or "could not check" and why. Feeds alive. | DESK header + THE DAY |
| **The open** | Who the gap trapped, against yesterday's close [I]. The first fight. Every read from its first mark ("n of 5"), never "blind until 09:35". | DESK · FLAT |
| **Flat** | NEXT FIGHT above and below, and what confirms each. The re-entry read after a FOLD. | DESK · FLAT, the panel |
| **Entering** | IF YOU WERE IN: the headline it would show, line 2, G and the premium there, the wall ahead in numbers, the expression, the amber clauses. | DESK, the panel's mark row |
| **In a trade** | Headline + clause + 4 chips; line 2 (the out-condition); premium, peak, given back, at G; the wall ahead. | DESK and the panel, identical |
| **Exiting** | FOLD with its reason, frozen. Never a size, never a fraction. | both |
| **After, and close** | The trade's word history. Falsifier counts, never rates. `trigger_log` rows as they are. | RECORD |
| **Any time** | When each wall was built, whether it holds, and which front retreats. | WAR |

**"Flat by 15:00 (your practice)"** shows in the header from 14:45. After 15:00, the entry face carries the amber clause. It is display only and never a rule, and it goes if CAS changes.

---

## 3. The hold and exit engine, exactly (`fold.py`)

### 3.1 What the son checks, in order, before he changes his mind

1. Where is price against my give-up?
2. Was it accepted there, or poked?
3. At the level: initiative, or absorbed?
4. Am I trailed past my entry (a free trade), or not?
5. Did the writers defending me leave **after** I entered?
6. The wall ahead: loading or covering (numbers)?
7. VPIN: is informed flow with me?
8. Tiring, or a failed extreme?
9. What have I given back? The clock.

**These never move him:** a candle close, a trend box, a quiet clock, her S1–S4 lines, OI off peak while price holds his level, or one minute of anything.

### 3.2 Units (H v3 §3, one change)

- **bucket** = 3 (h) × the median 1-minute volume, pooled over ≤ 5 (h) prior sessions **of the front-month series**. Sep until its expiry, Oct from 30 Sep.
- **B** = today's median 1-minute range so far (the pooled prior value until 5 bars). **θ** = 2B, **w** = B/2.
- **Median bucket duration so far** (3 minutes until 5 buckets exist) is the acceptance clock.
- **F\*** = future − the 15-min (h) median of (future − (K + C − P)) over strikes with |Δ| > 0.3. Every judgement of ATM, ITM, "beyond" and "ahead" uses F\*. `spot` is never a reference.

### 3.3 Fights, levels, traps, G, W: H v3 §4, §6.1, §7.1–7.3, unchanged

- **Fights:** one-sided bucket = sure imbalance ≥ ½ and |b − s| > 2G (guessed volume). A sweep is signed by price only at |Δp| ≥ θ, tagged "by price [I]". Fights fix on the next bucket of another kind.
- **G, the give-up:**
  - seeded at the mark from the newest fight before entry (if her side won it and trading is ≥ w her side of it), else the defending wall + w;
  - re-set on each win by her side (a new epoch);
  - **locked once touched**: it tightens, never loosens, and a refused loosening is logged.
- **W**, the wall that sets G: the most OI on the defending side between F\* and G, chosen only when G is set.
- **FAILED** needs a new extreme ≥ w beyond the old one, rejected ≥ w. **TIRING:** 2 stalled closes in a 5-bucket window to enter, 2 non-stalled to leave.

### 3.4 One wall ranking, two windows

- **The ranking:** current OI (not day-high), near-ATM, beyond F\* by w. A new choice must stand 2 bucket closes, or F\* must be w through the old wall. `fold.py` owns it. **`fronts.py` is not touched:** it holds §1d's pre-registered parameters (NEAR, TOP_PER_SIDE, SLOPE_MARKS) and `trigger_log.py` imports it.
- **W** (behind her): the §3.3 rule.
- **A** (ahead): the nearer of the top two on the far side, placed at K + basis, at least w beyond her entry.
- **§1d's fade gate is not touched** (§1, #13).

### 3.5 The OI event, acceptance, and the fold

- **OI event, on W only (H §6.2):**
  - (peak since reference − OI) ≥ 3 (h) σ √n, σ = 1.4826 × the median |ΔOI| of the 15 updates before the peak, floor 1 lot;
  - live until W prints above that peak (withdrawn, re-armed) or her side sets a new G;
  - one at a time; logged with z.
- **Acceptance (H §7.3):**
  - from the first print at or beyond G, sum the lots at or beyond it;
  - accepted at **1 bucket** of lots over **≥ the median bucket duration**;
  - a print w back inside restarts the tally before acceptance, or withdraws the acceptance after it.
- **Mode:**
  - *trailed* if d·(G − E) > 0, where E is the future at her mark; else *at entry*;
  - re-read whenever G changes, so it cannot flap (G steps only on wins).

| mode | FOLD fires on | reason printed |
|---|---|---|
| **at entry** | acceptance beyond G | "FOLD · 22997 accepted" |
| **trailed** | acceptance beyond G **and** a live OI event on W, same epoch | "FOLD · 22900 CE writers gave up 11:42, 22925 accepted" |
| **trailed** | **held breach:** the acceptance stands 2 (h) more bucket closes and ≥ 2 (h) × the median bucket duration, with no win by her side and no print w back inside | "FOLD · 22925 accepted and held 2 buckets" |
| **trailed** | **backstop:** acceptance beyond E ∓ w | "FOLD · back through your entry 22941" |

- **PAST GIVE-UP** (trailed only): G accepted, none of the three yet. Amber, no sound. Line 2 counts: "22925 accepted 14:37 · 1 of 2 buckets · 22900 CE writers holding".
- **OI alone** is an OI chip AGAINST with its time, and no sound. **STOPPED** (15 updates without a new high) turns the chip QUIET; it never folds.
- **One sound:** FOLD, two low tones, once per epoch, ever. Ids are kept across reloads, so a reload is silent.

### 3.6 The headline, the clause, line 2, and after the fold

| headline | look | clause (one, newest wins) |
|---|---|---|
| **HOLD** | ink | `behind you · won 11:04 at 22879` · `pullback since 12:28` · `failed low 11:56` · `no read yet`, plus the suffix `· tiring 6 min` while TIRING holds |
| **PAST GIVE-UP** | amber | the count above |
| **FOLD · reason · hh:mm** | ink block | frozen |

**Line 2 always says, before it happens, what takes her out:**
- *at entry:* "out if 22997 is accepted";
- *trailed:* "out if 22925 is accepted and held 2 buckets, or accepted while 22900 CE writers leave · never back through 22941";
- *OI event live:* "22900 CE writers left 11:42: acceptance past 22925 now takes you out".

**After FOLD:**
- the headline stays, frozen with its reason and time, until she presses I'M OUT or unmarks;
- the line under it reads live: "still marked · now: your side won again 12:35";
- it never reverts in place;
- the re-entry read (§5) is offered on FLAT once she is out.

**Premium at G and at A [I]:**
- read from the chain's own prices: the same-type strike at K′ = K + F\* − G (or A), interpolated between the two nearest strikes;
- tested on the 22 Sep expiry exit: within 0.5 of the actual [M];
- chain older than 60 s: "could not check: chain 70 s old".

**Peak and given back [M]:** the best premium since entry, with its time, and now against it.

### 3.7 The four chips (her order: ZONE · FLOW · OI · VPIN)

States: WITH, AGAINST, QUIET, CAN'T CHECK. No score, no count of chips.

- **ZONE:** H v3's level rule, made event-born. It changes when a level is born, broken (F\* w through it) or taken by a fixed fight. Proximity is the ZONE row's sentence, not a chip change. The row also names her zone machine's state (d2→d3 / u2→u3, armed or triggered, the 09:25 anchor kept), which is VALIDATE §1.1's "your setup", kept as a sentence and never a vote.
- **FLOW:** the newest fixed fight within 10 buckets. Event-born; exempt from the chip gate.
- **OI:** W building (new since-reference high within 15 updates) = WITH; an OI event live = AGAINST, with its time; stopped = QUIET.
- **VPIN** (10 buckets, fed from the ladder's fills once P6-04 lands): enters at lead ≥ 2 and leaves only after 2 (h) closes past zero. CAN'T CHECK under 10 live buckets; backfilled buckets are tagged and never counted.

Condition-born changes need 2 bucket closes.

### 3.8 The replay this rests on (8 trades, 5 days, to 15:00; % of entry premium)

| trade | best | this engine | v3 flow + OI | notes |
|---|---|---|---|---|
| 22 Sep put @ 47.75 (expiry) | +264 | **+77 · 14:19** flow + OI | +77 | held breach 14:24 +70; backstop not reached |
| 22 Sep call @ 43.65 | +78 after −61 | **−42 · 13:51** | −42 | at entry |
| 23 Sep put @ 122.3 | +3 | **−12 · 12:04** | −12 | at entry |
| 25 Sep put @ 111.6 | +42 | **+7 · 10:08** | +7 | whipsaw by the 20-min test |
| 25 Sep call @ 96.5 | +53 after −29 | **−10 · 09:47** | −19 | whipsaw; the re-entry read 10:24 |
| **28 Sep call @ 84.05** | 0 | **−17 · 10:16** | none, −61 | the trade that cost money |
| 24 Sep put (hindsight) @ 102.65 | +154 | **+98 · 14:39** held | +81 | |
| **28 Sep put, hers** @ 120.4 | +97 | **none · +71 at 15:00** | none | she left at 14:12, +37 |
| **sum** | | **+172** | +102 | |

The exits are the two revised replays' `PF_*` column, identical in both. The backstop fired in none of the 8 [M, Opus]. Headline changes ran 0–0.7 an hour; FOLD sounds 0–0.37 an hour; chip changes 4.4–11.8 an hour before ZONE and VPIN were made event-born (their re-run is gate P2-04). **n = 8 describes; the forward log ranks.**

### 3.9 Writers and SENSEX

- **Writers:** the same engine with d flipped. Her short strike, against F\*, is always a level. No reach and no strike stop: her 09-26 answers.
- **SENSEX:** its future prints a median 7–10 lots per 5-min bar [M].
  - FLOW and VPIN read "could not check: SENSEX future, n lots this bucket".
  - G = the defending wall + w.
  - Acceptance = price beyond G for **SENSEX's own** median bucket time, flagged [I].
  - The modes and the backstop apply unchanged. It never borrows NIFTY's clock.

---

## 4. Entry

**No GO, no NO.** The entry face is the in-trade face for a hypothetical mark, headed **IF YOU WERE IN · long 23000 PE**:
- the headline and clause it would show;
- line 2;
- G, and the premium there [I];
- the wall ahead in numbers, and the premium there [I];
- her strike's premium against its day VWAP, as σ, printed and never counted;
- days to expiry.

**Room and give-up are two printed distances; nothing refuses.** Her +97% put had 41 pts of room against a 56–72 pt give-up at 09:30 [M]. A ratio refuses trend trades at the first wall, and that is the wall that gives.

**Three amber clauses** (facts, not verdicts):
- "you would enter past your give-up";
- "you would enter at the 22900 PE writers (132.0L)";
- "after 15:00: your practice is no new trades".

**The expression: buy the option, or sell the other side.**
- Read at bucket closes, 2 closes to confirm, ATM on F\*, her strike when she names one.
- **Frozen when the mark row opens.**

| read | when |
|---|---|
| **BUY the option** | *Off expiry:* the newest fixed fight her way was initiative (pushed), **and** the wall ahead is not adding. *On expiry day:* initiative **and** the wall ahead off its peak (its writers running). |
| **SELL the other side, ATM (ITM in a trend)** | any of: expiry eve, or expiry day without the BUY condition; her side's last win was absorption, or TIRING is live (a grind); the wall ahead is adding; a box (both walls adding, VPIN quiet) |
| **EITHER** | neither holds |

R2 (never sell into a squeeze) and R4 (never sell a bid straddle) stay from EXPRESSION rev e. The sale is folded by the same engine with d flipped. The expression is forward-logged from day one, and printed as counts, never odds.

---

## 5. Flat

- **Line one:** "NEXT FIGHT · above 22907 · below 22852", the two nearest strong levels (walls by the one ranking, held levels, trapped shelves, the contract's prior day, her bands), with hysteresis w. Within w of one: "AT 22899 (22900 CE wall) · above 22919 · below 22885".
- **Under each, what confirms it:**
  - "above: lifts at 22905–22910 followed by price **and** 22900 CE off its peak: calls";
  - the mirror below, for puts.
- **When both halves fire:** a frozen, silent event, **"SELLERS GAVE UP AT 22907 · 11:42"**. She presses Mark if she takes it.
- **The re-entry read, after a FOLD:**
  - when trading comes back w inside G and her side then wins a fixed fight: "stop run failed at 23094: sellers absorbed at 23134, 10:24 · CE now 100.9 v your exit 86.65";
  - silent; falsified if G is accepted again within 20 min.
- **THE DAY:** one paragraph, ≤ 6 numbers: fights won by each side, value migration, the box, unreleased shelves, and expiry and roll lines.
- **After a move:** the nearest trapped shelf each side, the newest marked new.

---

## 6. The two faces

### 6.1 The panel: 400 px, LIGHT, fixed frame

Her put at 11:42 on 28 Sep, the state from `PF_H2_0928_PE`:

```
NIFTY SEP FUT · 11:42 · contract ✓ · chart placed
long 23000 PE · 120.4 · 09:30                              [ I'M OUT ]
HOLD · tiring since 11:14              ZONE▫  FLOW·  OI▫  VPIN·
22900 CE writers left 11:42: acceptance past 22925 now takes you out
PE 155.6 +29% · peak 182.7 +52% 11:16 · at 22925 ≈ 136 +13% [I]
ahead 22850 PE · 37 pts · 123.3L, peak 124.4L 11:37 [M]
ZONE  at 22892: buyers held 141 lots [M lots, I side]
FLOW  no fight in the last 10 buckets
OI    22900 CE 240.0L → 235.9L at 11:42 [M] (writers [I])
VPIN  1 of 10 buckets one-sided
▸ detail
```

Chips: ▪ with you · ▫ against · · quiet · ? could not check.

| budget | value |
|---|---|
| numbers with detail closed | ≤ 24 |
| colours | 5: blue helps buyers, red helps sellers, amber watch, ink hers, grey reference/absence |
| blocks | header, position, line 1–4, four rows, detail |
| height above detail | ≤ 480 px |
| sounds | 1 class: FOLD |
| headline changes | ≤ 1 an hour (gate) |
| condition-chip changes | ≤ 6 an hour (gate) |
| chart | 3 + 3 levels, 7 glyphs |

**No flicker:**
- events are frozen at birth;
- words are computed once per event batch;
- condition-born chips take 2 closes;
- a named wall holds 2 closes;
- G is a staircase;
- **the DOM is patched, never rebuilt** (`panel.js:515`'s `innerHTML` rebuild kills `<details>`; confirmed tonight).

**Anytime:**
- the panel GETs `/api/hold/trades` before its first frame;
- TapeMap down reads "your trade: could not check: TapeMap not reachable", never FLAT.

### 6.2 DESK (the Validate tab, renamed)

- The same header, lines and rows at 2× size.
- The check slip on the left, keys unchanged (C/P, B/S, ↑↓, Enter).
- Detail open by default: the G staircase, OI events with z and σ, acceptance tallies, chip history, the trade's words, and the alternative-exit columns (plain acceptance, flow + OI, held, backstop) marked "logged, not in force".
- The flat half: NEXT FIGHT, THE DAY, the re-entry read, plus the VPIN gauge as a detail block (the VPIN tab's content).

### 6.3 Mark my trade (both screens, one record)

- Mark trade → CE/PE → (BUY/SELL) → MARK: three clicks, four for a sale.
- The strike is prefilled ATM on F\*, with ◂ ▸ steps labelled ATM / ITM 1 / OTM 1.
- **The entry premium is frozen when the row opens**, and the strike steps read the same snapshot. She types her fill.
- The panel posts through `sw.js` to `/api/hold/trades`, whose door already refuses cross-site POSTs (`server.py:2873`). Build test first: `Sec-Fetch-Site: none` from the service worker. Fallback: exactly `Origin: chrome-extension://<id>` from config.
- The record persists in `data/day_state/`; a restart never loses it.

### 6.4 Chart marks and trust (the extension)

**Every mark comes from TapeMap's event log at its frozen (time, price).** The extension only maps (t, p) to pixels.

**Glyphs:**
- ▲▼ fight won;
- ▲▼ with a white dot: won by price [I];
- ▬ absorbed;
- hatched ▬ disputed;
- ⌃⌄ failed extreme;
- ▸ her entry;
- ■ FOLD.

**Lines:**
- the give-up as a dashed staircase (older steps at 55%);
- W and A as dotted lines with a strike chip at K + basis.

**Cut from the chart:** ROUND lines, the flat σ pocket, the event strip, per-strike pain chips, trap discs, the BANK ◆. A 5 px glyph floor; nothing removed at any zoom.

**Trust:**
- **with no date tick, fit only TapeMap's session day** (`frame.day`). Today's uncommitted `fit.js` diff adds date ticks and today's margin, but still leaves every loaded day a candidate when no tick is painted. That is the session jump that draws marks on Friday or on both days.
- **Contract match:** GoCharting's bar OI (`main.js:242` already carries `oi`) against the frame's future-bar OI.
- Hysteresis: 2 bad to pause, 2 good to resume.
- Paused: one tag, "chart shows another day / contract since hh:mm; marks paused, panel live".

---

## 7. Remove, keep, add

### 7.1 Removed (through the one amendment where a rule is signed)

| what | where | why |
|---|---|---|
| The session-high line, the 3-min close, noise B; Room, Cushion and the plan's ₹ risk measured from it | `hold.py`, rev 5 §A, PLAN §2.1 | A candle close. She banned it. |
| Trend as a fold family and as WATCH; `trendbox`; expression REGIME and ROOM | `hold.py`, `validate.py`, `expression.py` | Not one of her four |
| The quiet clock, PERSIST = 3, the FOLD latch and heal; rev 5 §C "adding beats a live fold" | `hold.py` | Time rules on lagging reads; the latch froze a wrong FOLD all day on 28 Sep |
| The 15-mark OI warm-up, the 4-bar flow warm-up, the 3-min expression cadence, as inputs to her trade | `hold.py`, `validate.py`, `expression.py` (the new engine never reads them; `fronts.py` stays as §1d's) | Everything reads from its first mark, "n of 5" |
| GO / WAIT / NO; the Room ratio; `FOLD_NEEDS` | `validate.py`, H §1 | §4; the mode picks the rule, so there is no switch |
| Spot as the moneyness reference | `board.itm/nearer`, plan rung, hold ITM/OTM, expression ATM (never §1d) | 24–46 pts off on 28 Sep [M] |
| Four of five wall rules (hold/board nearer, board headline, plan rung, expression WALL) | `board.py`, `plan.py`, `expression.py` | One ranking (§3.4); §1d excepted |
| `gate.py` (always PATA NAHI), `senses`/`ivrv` None fields, the ballot, `watch.py`, the breadth footer, ROUND, both WRONG IFs, the event strip, the flat σ bands, the dark panel | `frame.py`, `panel.js`, `overlay.js` | Fields that can never fill, or duplicate her chart |
| BANK ZONE, REACHED, WALL BROKE, the Γ premium term, "pros bank" copy | both drafts | §1 #6; chain-own prices replace Γ |
| Glass, Heat, Tape, Flow, Chain, OI Flow, Map, Events, Signals (→ RECORD), the VPIN tab (→ DESK detail), Board (→ DESK · FLAT) | `App.tsx` | No moment of her day needs them. The unique reads the ponytail review found in Glass and Tape move to DESK detail or go, tagged before. |
| `/api/calls` as a screen | `grounds.py` | Its forward-log rows stay |

### 7.2 Kept, untouched

- Her orders: the Dhan/Upstox fallback; `structure.py`, `band_rotation.py`'s two-leg stack and `contract_pair.py`; the Trade tab and its chart (`vendor/`); `/api/surface`, `/api/drag`, `/api/paper_fill`; the zone's 09:25 anchor.
- **`data/trigger_log.jsonl`**, never rewritten.
- **§1d, the fade gate**, and the zone machine.
- `ladder.side_of`; the thesis table for four roles; "premium is never an input to the verdict"; the three absence sentences; [M]/[I]; no order path; LIGHT.

### 7.3 Added, each in shadow first (logged, gating nothing)

1. **The event log** `data/fold/fold_<IDX>_<day>.jsonl`, with every threshold in force. A restart replays it to byte-equal words and never recomputes.
2. **Resting liquidity, at G or A only:** "offers at 22925 stacked 1.2k, 60% pulled this bucket". It is the acceptance's companion, never a lead.
3. **Big prints:** a fill ≥ the 99th percentile of today's fill sizes so far [M], at a level, its side if the ladder signed it [I]. One line in FLOW.
4. **Failed auction at a day extreme,** on FLAT.
5. **The next-weekly chain on expiry days** (the walls ahead live there).
6. **The GoCharting tick post** (`adapter.js` has sides), used only to dispute a fight. Kill: more than 1 fight in 3 disputed over 30 sessions, and FLOW stops printing sides.
7. **VPIN fed from the ladder's fills,** one classifier (audit bug 11). It is a new series with its own clock beside the old gauge's.
8. **The previous-close OI field,** same expiry, additive (`oi_prev`). `oi_chg`'s meaning is not changed under the signed window.

---

## 8. Data truth

| defect | handling |
|---|---|
| **Spot v forward:** 24–46 pts on 28 Sep [M] | F\* everywhere moneyness is judged, except §1d |
| **Guessed-side volume, 24–59%** [M] | |b − s| > 2G and imbalance ≥ ½; sweeps signed by price at θ, [I]; else "two-sided" |
| **Three tapes disagree (63–65%)** [M] | VPIN from ladder fills; GoCharting disputes only; the day's agreement in RECORD |
| **Book and chain start about 09:17** [M] | Until pre-09:15 subscription (last, P6-05): "blind before 09:17:19, 1,639 lots unseen"; the 09:15 bar is never scored |
| **Rows about 2 min late** (REST 1-min candle) [M] | A tick-built minute, reconciled with REST later, tagged (P6-05) |
| **OI baseline = the 09:15 candle** | The new engine reads `oi_prev` (same expiry, previous close). Missing = "could not check", never 0. Wednesday 30 Sep: could not check unless REST supplies it (P2-05). |
| **09:15–09:16 backfill lives in memory only** | Written to disk, tagged backfilled (P1-05) |
| **No contract on the records** (book rows carry no `instrument_key` or expiry [M]) | Additive `ik` + `expiry` on every chain, book, ux, tape and VPIN row (P1-03). No tail is carried across two contracts. |
| **The roll: Sep expires 29 Sep, Oct from 30 Sep** | The expired-future filter is built (BUGFIX #6, uncommitted, live at her restart). Bucket and B pool the front month (§3.2). PDH/PDL/PDC are the contract's own, else "could not check". `fut_oi` is blind for the near contract in its expiry week (P1-04). The chart contract match (§6.4). |
| **Expiry day (29 Sep: NIFTY weekly + Sep future + BANKNIFTY monthly)** | The OI event runs on the expiring series against its own closing pace (H §8, post hoc, flagged). EXPIRY · Γ in the header after 13:30. Expiry-day BUY rule (§4). |
| **fit.js session jump** | §6.4, P1-01 |
| **Premium at G or A** | Chain-own prices; stale > 60 s = could not check |
| **Restart** | The event log replays; the trade returns from `day_state`; a test diffs a rebuilt day against the live log |

---

## 9. Build phases (nothing ships in market hours; she starts the server; commits on her word)

**Precondition, her word only:** commit tonight's BUGFIX #1–6 (tapemap working tree) and today's uncommitted extension fit/overlay work, after their tests pass. Both are already built; neither is a package below.

**Phase 1: tonight and Tuesday after the close. Safe for 29 and 30 Sep. No method change.**
- P1-01: the extension fit (single session day) and the contract match.
- P1-02: the panel to LIGHT, patched not rebuilt.
- P1-03: contract stamps on recorded rows.
- P1-04: `fut_oi` blind in the expiry week, and SENSEX flow blind.
- P1-05: the backfill to disk.
- P1-06: the `day_state` restart test.

**Phase 2: this week. The engine in shadow.**
- P2-01 `fold.py`; P2-02 the event log; P2-03 the server wiring (one grey line in DESK detail: "shadow · rev 6 says: HOLD · pullback since 12:28"); P2-04 the gate harness; P2-05 `oi_prev`.
- **Gates before she is asked to sign:** every recorded day replayed with no FOLD on arrival; FOLD sounds ≤ 1 an hour; headline ≤ 1 change an hour; condition chips ≤ 6 an hour with ZONE event-born and VPIN's 2-close exit; exits printed against the best; a mid-session restart replays identical words (one live session).
- The gate runs on disk tonight, so her signature can come Wednesday after the close.

**Phase 3: on her signature. The faces.**
- P3-01 DESK; P3-02 the retired rules out of `hold.py` and `validate.py` (tag `pre-rev6`), with `/api/hold` answering from `fold.read`; P3-03 the panel and mark-my-trade; P3-04 the marks from the event log.

**Phase 4: entry, flat, expression.** P4-01 to P4-03, each forward-logged from day one.

**Phase 5: the cuts.** P5-01 tabs, P5-02 dead fields, P5-03 board on F\* and the one ranking. One commit per group, tagged before.

**Phase 6: the missing reads, in shadow.** P6-01 to P6-05. The pre-09:15 subscription goes last, because it touches the feed and needs a quiet morning to verify.

---

## 10. The ceiling, stated

- Eight trades on five days describe; thirty forward sessions decide. The tool prints counts, never rates.
- The log must answer three questions first:
  - on a trailed trade, does waiting for the writers beat the held breach alone (22 Sep says wait, 24 Sep says don't)?
  - does the backstop ever fire?
  - does a screen with no bank verdict let her hold longer than she did at 14:12 today?
