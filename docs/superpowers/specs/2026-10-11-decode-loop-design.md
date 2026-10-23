# THE DECODE LOOP — design spec (for Mary's review)

**Status: DRAFT, 2026-10-11. Not approved, not built, not committed.** It comes out of the 8–9 Oct brainstorm, a live
reading session on 9 Oct, and two rounds with Sonnet 5.5 (`docs/fresh-take/DEBATE.md`, its critique of 9 Oct).
Nothing in it is built until Mary approves this file. Mary's Monday (12 Oct) session is the first test of the read.

---

## 1. The problem in one paragraph

TapeMap measures plenty: delta, CVD, footprint, VWAP bands, writers per strike, futures OI, IV and VPIN. It still does
not **read** the market. On 9 Oct, reading by hand every 20–40 minutes, the read that worked always had the same six
steps: **measure → rank (big or noise?) → list what matters → state → plan → score the last plan.** The tool has
step 1 and part of step 4. The pieces never became one read, and the missing steps are why.

The hand read itself failed in ways the missing steps would have caught:

| 9 Oct, said by hand | Its real size | The step that would have stopped it |
|---|---|---|
| "+238 / +340 aggressive buying" | 5-min delta at pct 81 / 87 (none ≥ p90) | RANK |
| "+1,833 lots fresh longs, a quality upgrade" | futures-OI move below p90 | RANK |
| "PE writers quitting, the flip test fired" | PE −29L at ATM±2 = pct 63 | RANK |
| "call writers capping 22,500–22,600" | fresh CE adds at pct 19–25; the wall was yesterday's OI | RANK + stock ≠ flow |
| absorption marks read backwards | — | one meaning per mark, written down |
| no morning delta "available" | GoCharting had it from 09:15 | COVERAGE (fixed 9 Oct, §6 D3) |
| the READ flipped at 11:45 and 12:00 on a normal dip | dip at pct 63, VWAP never crossed | STATE break rule (§5.3) |
| BANKNIFTY's significant afternoon flow and OI missed | flow pct 91, OI × price pct 100 | cross-index pass (§5.2) |

**What a good read was built from on 9 Oct:**
1. The opening CVD was a RECORD.
2. The CE writing was the lowest of 12 sessions (an absence).
3. All three indices had 0 VWAP crosses.

Everything after 10:00 was noise. The design makes the tool see it that way.

## 2. Mary's rules this design obeys (not up for change here)

- **No order path, ever.** The tool is advisory; it never sizes a position and never places an order.
- **Measurements:** never print a win rate, hit rate or confidence. Report rows. Tag every number **[M]** (measured) or **[I]** (inferred).
- **Data integrity:** the forward logs decide. No new backtests or cache-slicing for edges. Anytime start: backfill exactly, tag what was rebuilt, and say "?" with a reason for what is missing.
- **Screen:** light mode only. A terminal-like tool, not an essay: grids, pills, cells of six words or fewer, 1245×720 with no scroll. Hinglish chips with numbers. Every level in **spot and fut**. No price charts (she has her broker's chart).
- **Her trading rules:**
  - Fold on **zone, flow, OI or VPIN — never a candle close.**
  - The 15:00 cutoff is her practice, shown on screen only.
  - Her setups as signed: the zone (d2→d3 buy, u2→u3 sell) behind the fade gate, and `READ-V2-PREREG.md` §E/F/V/D.
- **How work is done:** surgical changes, one test per fix. No market-hours restarts unless she asks. Commit only on her word.
- **Tabs:** OI Flow stays as it is. Other tabs move under LAB, nothing deleted without her word.

## 3. The loop

```
MEASURE ──► RANK ──► LEDGER ──► STATE ──► PLAN ──► SCORE        (every 5-min mark; the fold board every few seconds)
   │          │         │          │         │         └ forward log, rows after the close
   │          │         │          │         └ 2–3 if-then rows, thresholds taken from RANK
   │          │         │          └ THE READ (read.py), new break rule; KHEL · PREMIUM · SIZE
   │          │         └ flat, time-ordered; notable+ AND absences; day-level vs last-40-min; cross-index pass
   │          └ raw · pct · N · tag; size and sign apart; scale units; thin-volume and two-source rules
   └ existing modules + COVERAGE ("?" with a reason for what this process cannot see)
                                                    AI READ (display only, built last) reads LEDGER, writes prose
```

Each box is one module with one job, testable alone. Its input and output are a plain dict or JSON. No box reads
another box's internals.

## 4. RANK — "kitna bada?" (the first thing built)

**What it does:** given a measurement, return how unusual it is against recorded history at the same clock.

```
rank(metric, idx, value, sec_of_day, day_kind) ->
  {raw, unit, pct_mag, pct_sign, n, tag, provisional, scale, why}
```

- **Reference distributions are built after the close** from recorded days *before* today, one file per metric and
  index (`data/rank/<metric>_<idx>.json`), so the live day never ranks against itself or the future.
- **Same clock:** values are compared within day-parts (09:15–10:00, 10:00–12:00, 12:00–13:30, 13:30–15:15).
- **Size and direction are ranked separately.** `pct_mag` ranks |value|. `pct_sign` is shown but never gates
  anything, because the history is mostly one falling market and signed values rank extreme by construction.
- **Day kinds are kept apart:** NORMAL, EXPIRY (that index's expiry day) and ROLL (the futures roll). An expiry day
  never ranks against normal days. A bucket with too few days says so.
- **Tags:**

  | Tag | Rule | On screen |
  |---|---|---|
  | `BAHUT KAM` | pct_mag ≤ 10 | shown: absence is evidence (9 Oct: CE writing lowest of 12) |
  | noise | 10 < pct_mag < 70 | grey, collapsed |
  | notable | 70 ≤ pct_mag < 90 | normal |
  | BADA | pct_mag ≥ 90 | bold |
  | RECORD | above every day in N | bold + "N din me sabse" |

- **Provisional:** while N < 30 the tag carries a small "N=11" and the screen never hides the raw number. Order
  flow has about 11–16 days today; OI has about 30 (chain from 20 Aug).
- **Scale units beside the percentile, needing no history:** range ÷ IV-priced day σ; moved ÷ priced (30 and 60 min);
  z versus VWAP. These read correctly from day one.
- **Thin volume:** a delta or print rank in a bar whose volume is ≤ p10 carries "thin" and cannot be BADA.
- **Two delta sources (GoCharting, Upstox):**
  - Each is ranked against **its own** history. Sonnet measured a median offset of −2,029 lots/day (Upstox below GoCharting), with volumes within 1–4%.
  - Delta counts as a signal only if **both** sources are ≥ p70 with the same sign. Otherwise the chip says "sources disagree" and the reading is treated as noise.
  - A single source (BANKNIFTY, SENSEX, or the minutes after a restart) is capped at notable.
  - The daily offset is logged as a health number.

**Rate of change and volume (Mary, 18 Oct):** a delta, a CVD move or a delta flip is judged by **how fast it changes
against normal, together with volume and its rate of change**, never by its level alone. *Original proposal below
(Opus, 18 Oct): **superseded** by the revision after it, and kept only for the record.*

| Metric | Definition | NIFTY normal (median / p70 / p90) [M, GC, 17 days to 12 Oct, N=1,169 bars] |
|---|---|---|
| 5-min delta | net lots in the bar | 77 / 139 / 338 lots |
| delta ÷ volume | how one-sided the bar is | 0.18 / 0.27 / 0.43 |
| **flip swing** | Δ(bar) − Δ(previous bar) when the sign changes | 173 / 269 / **549** lots |
| **CVD slope** | net lots per minute over 15 min | 12 / 22 / **49** lots/min |
| **slope change** | CVD slope now minus 15 min ago (acceleration) | 16 / 29 / **63** lots/min |
| **RVOL** | bar volume ÷ the median at the same 15-min slot on other days | 1.0 / 1.5 / **2.6** |
| **volume acceleration** | bar volume ÷ the mean of the last 15 min | 0.88 / 1.20 / **1.94** |
| price result | the bar's move in σ (for effort vs result) | to measure in Phase 1 |

**Revised after Sonnet's study (18 Oct, `docs/fresh-take/FLOW-STATE-STUDY.md`)**

**What changed:**
- **Dropped as inputs:** flip swing (it equals |Δ_now| + |Δ_prev|), acceleration (inside a random-sign null), volume
  acceleration (overlaps RVOL), and PATLA as a state (it became a chip).
- **Ranking:** delta is now ranked within its own time slot (pooled ranks over-flag the open). RVOL also gets a
  within-day version, because same-slot RVOL tracks day volume (ρ 0.95).
- **My hand-checked examples were removed.** Only 4 of 7 reproduce under the written rules (12 Oct 10:15 fails PUSH;
  16 Oct 10:15's top fell inside the bar).

**FLOW STATE (candidate; SEEN; no gate until a dated prereg).** The unit is the last 5 minutes, re-evaluated **every
minute**, per index and per source (GC and Upstox ranked apart, leave-one-day-out, rebuilt after each close). Every
threshold shows its day-bootstrap range and N (e.g. NIFTY GC p90 |Δ| = 338, range 281–397). SENSEX is read on 15-min
bars with a ≥ 30-lot floor.

| Input | Definition |
|---|---|
| SIZE | \|Δ\| ÷ the same-slot median \|Δ\| of other days (rank) |
| SHARE | \|Δ\| ÷ volume (scale-free); NIFTY GC p90 0.43 |
| RVOL | bar volume ÷ the median of today's previous 12 bars (the same-slot RVOL is shown beside it) |
| RESULT R | sign(Δ) × (close − open) ÷ the same-slot median bar range |
| RUN | Δ over the last 15 min has the same sign? (chip) |

| State | Rule | Meaning |
|---|---|---|
| **PUSH ▲/▼** | SIZE ≥ p90 and R ≥ +0.25 | big delta, price followed |
| **CLIMAX** | SIZE ≥ p90 and R < +0.25 (R < 0 = *ulta*) | effort without result |
| **ROKA** | RVOL ≥ p90 and SIZE ≤ p70 | volume without delta (absorption-type) |
| **noise** | SIZE, SHARE, RVOL all ≤ p70 | ignore |
| **no read** | every other bar (56% of bars) | absence of a state, said so; never called noise |

**Chips, never states:**
- EK-TARFA (SHARE ≥ p90 on RVOL < p70).
- RUN.
- The flip, shown as "−X → +Y".

**Rules around the states:**
- **Thin gate:** volume ≤ p10 of the slot can be neither PUSH nor CLIMAX.
- **Sources:** a state shows only when GC and Upstox agree; otherwise "sources disagree". They disagree on delta sign
  in 223 of 766 NIFTY bars, and PUSH agrees in only 9 of 25.
- **Tags, not suppression:** expiring contract after 15:00, first day on a new contract, roll week.

**What the states do NOT do (measured, SEEN):** they describe the bar; **they make no claim about the next move.**

| State | WITH / AGAINST | Its baseline |
|---|---|---|
| PUSH | 22 / 13 | shifted placebo 73 / 44 |
| CLIMAX | 13 / 10 | at its baseline |
| ROKA | 18 / 21 | at its baseline |

- Reversal marks on CLIMAX/ROKA bars showed no sign of doing better (era B 3 / 9, n = 17).
- Reading a 60:40 split would take about 25 decided rows per cell, which is **about 130–160 sessions**.
- So the states log forward (P-FS1–6 in the study file) and serve as vocabulary and a noise filter, not as entries.

**The metrics, Phase 1 (each already measured somewhere in the repo):**

| Metric | Window | Source |
|---|---|---|
| 5-min delta; delta ÷ volume | bar | GoCharting tape (NIFTY), Upstox ux (all) |
| CVD change | 40 min | same |
| opening CVD | 09:15–10:00 | same |
| volume | 5 min, 30 min | same |
| largest single-price cell | bar | tape ladders |
| futures OI change, in lots and % of OI | 40 / 60 min | book |
| option OI change at ATM ±2, CE and PE | 30 min | chain |
| day writers: CE build, PE build, A, at nine strikes | day | chain (READ, symmetric window §6 D1) |
| VWAP crosses since 09:30; z | day / now | futures bands |
| moved ÷ priced; range ÷ priced day σ | 30–60 min / day | chain IV + futures |

## 5. LEDGER, STATE, PLAN, SCORE

### 5.1 COVERAGE (part of MEASURE)
For each index and source, this lists what this process can and cannot see, with the reason. For example: "OI 09:15–10:10
REST-rebuilt [I]", "GoCharting 11:15 bar missing", "SENSEX 531 lots all session, too thin". Anything that
depends on a missing input shows "?", never zero (CLAUDE.md rule 6).

### 5.2 LEDGER
A flat, time-ordered list of every ranked reading that is notable or above, or `BAHUT KAM`. Each line has the time, a Hinglish chip,
the raw value, the rank, N, the source and [M]/[I].

There are two sections: **DIN (day-level)** and **ABHI (last 40 min)**. Noise is not listed. A single "baaki sab noise" line
carries the count. This is how 9 Oct would have looked:

```
DIN   09:15–10:00  CVD +6,244        RECORD (7 din)      kharidar haavi      [M] GC
DIN   09:35        CE 22,350/22,400 bhage · QUIT                             [M]
DIN   13:38        CE likhna +46L    BAHUT KAM (12 din)  calls nahi likh rahe [M]
DIN   all day      VWAP cross 0      (3 indices)         trend nishaan        [M]
ABHI  13:30        vol 86–200/5m     BAHUT KAM           tape mara hua · thin [M]
ABHI  12:50–13:50  BANKNIFTY fut OI +0.68%, px +172  BADA   naye long         [M]
      baaki sab noise (14 readings)
```

**Cross-index pass:** one line saying which index carries the confirmation and which has none ("BANKNIFTY
confirm kar raha · NIFTY flat"). Chapters (drive / balance / test) are **deferred** until Mary asks for them; Sonnet
flagged them as a third classifier.

### 5.3 STATE — THE READ, upgraded (read.py stays the engine)
The data inputs change (§6), plus one rule:
- **Break rule (replaces "any 5-min close past FLIP"):** the held word breaks on either
  - a 3-min futures close beyond VWAP, on the wrong side, by ≥ 0.25σ, or
  - two against-signals, each notable or above, in the last 40 minutes, or
  - the existing writers-flip.

  The against-signals are: the 40-min CVD change against; futures OI × price against (new positions the other
  way); the supporting writers' 30-min OI drop at ATM ±2; a single-price print against at a level.

  A lone normal-sized dip never breaks it. On 9 Oct this would have held TREND ▲ through 11:45 and 12:00 [I, to be
  shown on the replay before build].
- From the debate: the displacement gate (TREND needs a move ≥ 0.6× the expected move to date); no TREND before 10 minutes of
  OI flow; a PIN flag inside RANGE allows selling only; veto fast, permit slow (enter a side after 2 min, leave after 10).
- **KHEL:**

  | READ word | KHEL |
  |---|---|
  | TREND | RIDE (full) |
  | LEAN | RIDE (half) |
  | RANGE | FADE |
  | WAIT | BAITHO |

- **PREMIUM:** moved ÷ priced ≥ 0.8 means buying works; ≤ 0.5 means selling works; between, no call. Expiry-day IV is marked "?".
- **SIZE:** full only when the day-level evidence is notable or above **and** nothing against it is notable or above in ABHI. Otherwise half.

### 5.4 PLAN
2–3 if-then rows per index, from STATE and the levels (VWAP ±σ, prior and today's value, walls, FLIP), in spot and fut.
**Entry rules are the already-registered ones, unchanged:**
- `READ-V2-PREREG.md` §E: TREND ▲ buys VWAP…+1σ on low ≤ +1σ, close > +1σ, bar delta > 0; stop on a 3-min close < VWAP. Mirror for ▼.
- RANGE uses her zone machine.

**Opening drive (09:15–09:45), Mary's "I'll miss the drive" point:**
- READ-V2 §E has no zone before 09:45.
- A **DRIVE** row is proposed: the first-15-min move and delta are both BADA, and every bar is on one side of VWAP.
- Half size; kill = back through the open print for 3 minutes.
- Whether it fires on 9 Oct is checked on the replay, not claimed. Sonnet measured NIFTY's first-30-min move at
  pct 82 (notable, not BADA) and its first-bar delta share at pct 100, so the exact thresholds are part of that prereg.
- It is a **new gate**, so it gets its own dated prereg before Phase 3, never an edit to READ-V2.

RANK only supplies the thresholds in the words ("sell bar ≥ 400 lots = p90 aaj ke hisaab se") and the fold board's
"is this against-signal real?" test. Changing a gate, rather than a label, needs a new dated prereg.

**Fold board, in a trade:** ZONE / FLOW / OI / VPIN, each shown as "at entry → now" with its rank. A reading counts
against her only at notable or above, held 3 minutes. Never a candle.

### 5.5 SCORE
Every plan row is written once to `data/plan/plan_<day>.jsonl` (time, index, row, trigger, kill, target, the ranks behind
it). After the close: TRIGGERED / KILLED / TARGET / NEITHER as rows. No rate, no mean.

Mary's blind drill (her own call at fixed times, written before she looks) is logged next to it.

### 5.6 AI READ (last, display only)
- A "Market Read" button sends Claude **only** the LEDGER and STATE JSON.
- **Rules:**
  - typed claims, each citing ledger ids;
  - strong verbs ("aggressive", "fresh longs", "flip") only for BADA or RECORD lines;
  - a mandatory "noise" list;
  - numbers checked against the ledger;
  - logged and scored like a plan.
- It **never** feeds STATE, PLAN or the fold board. Sonnet's point: today's errors used *correct* numbers with the wrong word,
  so a numbers check alone does not make it safe.

## 6. Data fixes (Phase 0, before or alongside RANK)

| # | Fix | Why | Status |
|---|---|---|---|
| D1 | Chain window | The recorder keeps 17 fixed strikes around the opening ATM. On 8 Oct spot left the window and the 9-strike writer read went lopsided (Sonnet: changed 25% of TREND samples). Recentre or widen the recorder; the READ uses a symmetric window and shows "?" at the edge. | open |
| D2 | Writing vs buying | OI up does not say sold or bought. Use an IV / premium residual per strike against the ATM-wide move, tagged [I]. | open |
| D3 | GoCharting flow backfill on a late start | READ FLOW was blind before the first Upstox tick | **built 9 Oct** (`read.Flow(pre)`, `server._read_gc_pre`, one test; suite 1,637 passed). Uncommitted. |
| D4 | Missing GoCharting bar after a restart | 9 Oct 11:15 bar absent from `tape_NIFTY` | open, investigate `tape_log` re-post |
| D5 | BANKNIFTY / SENSEX flow | Upstox only, so single-source by rule (§4); check whether the extension can feed them | open |
| D6 | Day high/low from ticks; basis printed live | Sonnet's frame-C bug; spot/fut confusion | open |
## 7. Screens

- **Phase 1 adds no new screen.** RANK appears beside every number on the existing Read tab, the answer band and its chips.
  Example: `CVD +6,244 · RECORD 7d` or `delta +238 · p81 · noise`. A small "N=11" marks a provisional rank.
- **Phase 4 cockpit (designed in detail only after Phase 1 is in use), on one 1245×720 screen:**
  - three index cards (KHEL · PREMIUM · SIZE, lines in spot|fut, the cross-index line);
  - the LEDGER (DIN / ABHI);
  - the PLAN rows;
  - in a trade, the fold board replaces the PLAN.

  Everything else lives under LAB. OI Flow stays.

## 8. Build order and "done" tests

| Phase | What | Done when (checked on Mary's screen) |
|---|---|---|
| 0 | D1, D2, D4, D5, D6 + COVERAGE | each fix has its test that fails on the old code; COVERAGE shows the 9 Oct gaps by name |
| 1 | RANK + labels on existing screens | a replay of 9 Oct marks every bar after 10:00 noise/notable, and the opening CVD, the CE absence and 0 crosses as RECORD / BAHUT KAM; live on a Monday |
| 2 | LEDGER + cross-index pass | the 9 Oct ledger matches §5.2 in substance, with nothing added by hand |
| 3 | STATE break rule + PLAN | the 9 Oct replay holds TREND ▲ through 11:45 / 12:00; plan rows show the 12:00 VWAP retest |
| 4 | Cockpit screen | Mary uses it a full session without opening another tab |
| 5 | SCORE + blind drill | first forward week logged; rows, no rates |
| 6 | AI READ | its words match the ranks on 5 sessions; display only |

Each phase is usable alone and stops if Mary says so. The first implementation plan covers **Phases 0–1 only**; each
later phase gets its own plan after the previous one has been used live.

On 9 Oct, D3 (already built) gives the right read at 09:45. Phase 1 would have marked the midday as noise. Phase 3's
break rule would have kept the read through 12:00 [I, shown on the replay before build].

## 9. How we know it works (not a backtest)

- **Live == replay:** each module gets a no-look-ahead test, like `test_read.py`'s.
- **Forward only:** the replay pre-registration (`docs/fresh-take/REPLAY-PREREG.md`, Opus §9b amendments) still needs
  Mary's signed pass bar. Rows are labelled LIVE / UNSEEN / SEEN, and SEEN days can fail a rule but never pass one.
- **Mary's blind drill:** at 09:45, 11:00, 12:30 and 14:00 she writes her own call before looking; disagreements are logged.

## 10. Not in scope

Order placement · win rates or confidence · new backtests for edges · price charts · dark mode · position sizing ·
news/event detection (Mary writes the event note herself) · options-side order flow (no data).

## 10b. What the live reads showed (9–16 Oct, 7 sessions) — candidates, not rules

Full-day outcomes come from Upstox's futures history (it covers the unrecorded 14–15 Oct). n = 7, a mostly trending
week with one range day. Every item becomes a rule only through a dated prereg and forward days.

| # | Observation [M] | Design candidate |
|---|---|---|
| O1 | **VWAP crosses after 09:30 split the day types:** trend days 0–4 (8, 9, 12, 13, 15, 16 Oct); range day 14 (14 Oct). Matches her CSV (6/8 Oct: 0, 7 Oct: 13). By 11:00, "0 so far" held on every trend day | crosses-so-far is a first-class gauge on the day card |
| O2 | **Writer one-sidedness at 09:45 matched trend quality:** \|A\| ≥ 0.8 → a clean trend from the open (8, 9, 13); A 0.32 → a trend confirmed only at 11:05 (12); A ≈ 0.1 → a shakeout, then a small trend (16). The *absent* side carried the signal | **09:45 DAY CARD:** \|A\| and the absent side · opening-flow rank · crosses so far · gap vs yesterday's close and value |
| O3 | **Rallies were short covering, declines were fresh shorts:** futures OI fell on every up day (−823 / −2,157 / −9,502) and rose on every down day (+6,081 / +1,735). Covering rallies paused when covering ended (9 Oct midday) | a **FUEL label** per move: covering / new longs / new shorts / long exit, ranked |
| O4 | **Trend-day extremes came late:** after 13:30 on all 5 clean trend days, after 15:00 on 3 (8, 12, 13 Oct). Holding through midday noise was right every time | **trend-day hold rule** = §5.3's break rule (only a VWAP cross or ranked against-signals). Her 15:00 practice stays display-only |
| O5 | **A gap's fate was set in the first 10–30 min by who met it:** call writers sold the 12 Oct gap (CE 372L by 09:25) and BANKNIFTY sold at a record pace, so it failed; no call writing plus record buying on 9 and 13 Oct, so those held | gap row on the day card: "gap ko kaun mila" (writers + flow ranks) |
| O6 | **Writers quitting strike by strike marked the legs:** PE 22,550 → 22,500 → 22,450 (12 Oct 10:35 / 10:55 / 11:15); CE quits right before the drives (9 Oct 09:35, 13 Oct 09:45) | QUIT lines in the LEDGER, shown as a sequence |
| O7 | **NIFTY trended, BANKNIFTY chopped more** (BANKNIFTY crosses 11 / 9 / 17 on 8 / 14 / 16 Oct); BANKNIFTY was the better trade only with its own BADA evidence | cross-index pass picks the index with ranked evidence |
| O8 | **The extension's TRAP marks ("sellers / buyers phase", glyph P) and absorption caught 16 Oct's low (22,915 at 09:35–09:40; low 22,908) and high (23,140 at 10:15–10:20; high 23,155)** | marks into the LEDGER with their rank; study below |
| O9 | If-then plans with levels worked better than calls (12 Oct targets hit twice); the day was never scored after the close | §5.5 SCORE from Upstox's history every evening |

**Studies requested by Mary (18 Oct), running with Sonnet 5.5 on recorded days (labelled SEEN; rows, not rates):**
1. **Prior-day HVN/LVN:** at each touch, does price accept (time and closes beyond) or reject (turn ≥ X)? How do order-flow
   traders use them? Should they become LOCATION rows or entry zones?
2. **Delta and CVD for holding:** how traders hold with them (CVD trend with price, divergence at extremes, effort vs
   result), and what CVD did during the pullbacks that held vs the ones that broke on our trend days.
3. **The extension's marks** (trap / absorption / exhaustion / climax / initiative / vacuum and the decoder events),
   logged live since 21 Sep: what followed each, where the labels confuse ("sellers phase" at a bottom), and how to
   improve them.

**Results (Sonnet 5.5, 18 Oct, `docs/fresh-take/ORDERFLOW-STUDY.md`; SEEN / FORWARD-LOGGED rows; about 150 cells, so
multiple-comparisons risk is high; most n < 30):**

- **Marks.** Logged live since 21 Sep, in two builds:
  - **Era A (21 Sep – 1 Oct)** binned at her chart's zoom (the same tape gave 36, 15 or 144 marks), and **graded big prints backwards**: the 29 Sep 300K buyer was logged as "sellers defended".
  - **Era B (from 5 Oct, decoder 0.4.0)** is the current logic.
  - **Outcomes, era B** (0.5σ WITH the winner first / AGAINST first, within 60 min):

    | Mark | WITH / AGAINST |
    |---|---|
    | trap | 15 / 14 |
    | absorption | 28 / 27 |
    | exhaustion | 9 / 17 |
    | initiative | 27 / 24 |
    | vacuum | 10 / 10 |

    That is close to what a mark with no information would show.
  - **Day extremes:** era B caught 4 of 13 (6 of 13 within 20 pts). 16 Oct caught both, with about 10 marks around them.
  - **12 Oct** (down-trend): buyer-winner marks went 4 against, 1 with.
  - **Read:** as a firehose of 36+ marks a day they don't separate; the memorable hits come with many misses. Filters (rank, place, trend context) are **untested**, not disproven.
- **Prior-day nodes:** 34 first touches, ACCEPT 10 / REJECT 22. Levels shifted ±30 pts (placebo) gave 18 / 44: **real nodes look like random levels at this n.**
- **CVD for holding:**
  - It did not separate pullbacks that held from ones that broke (NIFTY 9 vs 9; BANKNIFTY 7 of 18 held vs 6 of 11 broke).
  - **A CVD divergence at a new extreme was followed by a further extreme 16 of 19 times**, so a divergence is a poor exit and would cut winners early (fits O4).

**Candidates added (each needs a dated prereg; the extension items need Mary's word, since it is separate code):**

| # | Candidate |
|---|---|
| P-OF1 | Marks drawn only at rank ≥ p90 **and** at a place (σ band, prior/today node, VWAP), tagged with- or counter-trend. Log both a hold test and a 0.5σ-first test forward, on a fixed build |
| P-OF2 | Clear Hinglish names: trap → **"BECHNE WALE PHANSE ▲" / "KHARIDNE WALE PHANSE ▼"**; absorption → **"KHAREEDAR NE ROKA ▲" / "BECHNE WALE NE ROKA ▼"**. The log carries the trapped side and the winner as separate fields |
| P-OF3 | Prior-day POC / VAH / VAL / HVN / LVN stay **LOCATION rows only**, not entry zones. An interior-LVN prereg with a built-in placebo needs ≥ 25 first touches per class first |
| P-OF4 | CVD divergence = an **information chip, never a fold**. Flow fold = a counter-trend 15-min delta ≥ p80 **and** price back within 0.5σ of VWAP (zone + flow, her rule). An opposite BADA print or ranked absorption against you at your level is a candidate fold tell |
| P-OF5 | Every mark row stamped with the extension build and row size. Drop vacuum, the climax chart mark, and exhaustion on trend days. (Sonnet's bar-gap alarm is **not** added: Mary dropped the feed alarm on 18 Oct) |

## 11. For Mary to decide

1. Approve this spec, or mark what to change.
2. Sign the replay pass bar (`REPLAY-PREREG.md` §8 + §9b), or change it.
3. Monday: we watch the market together. The live read that day is the first check of §4–5 on a day nobody has seen.

---

**Evidence and sources:**
- 9 Oct ranks: opening CVD +6,244 vs prior −2,218…+3,807; writers A −0.87 to −0.89; 0 crosses on three indices; midday NIFTY delta ≤ pct 87; NIFTY CVD 40-min pct 11–48; NIFTY futures OI 40-min pct 10–21.
- Sonnet: GC/Upstox delta offset; BANKNIFTY flow pct 91 and OI × price pct 100; the symmetric window changed 25% of TREND samples.
- Files: `docs/fresh-take/` (APPROACH, UI, RISKS, DEBATE, REPLAY-PREREG), `docs/read/READ-V2-PREREG.md`, `docs/cockpit/HANDOFF-2026-10-09.md`.
