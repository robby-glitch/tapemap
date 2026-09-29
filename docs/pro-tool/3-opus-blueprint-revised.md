# The pro tool: blueprint, revised (Opus)

**Written:** 2026-09-28, after the close. Design and replay only: no code, data or server touched; nothing posted, started or committed.
**Revises:** `1-opus-blueprint.md` (PRO-1), against `2-fable-critique-of-opus.md`. Also read: `1-fable-blueprint.md`, `3-fable-blueprint-revised.md` (it appeared while I worked), and H v3 (`H-reader-spec-v3.md`, `H-changes-v3.md`, unchanged since 15:32).
**Replay:** `scratchpad/pro3/reader_p3.py` + `run3.py`; traces `PF_*` (this design), `PT_*` (mode by trail), `PL_*` (time floor on losers), `PC_*` (a chip variant). 8 trades, 5 days, read-only.
**Tags:** [M] measured, [I] inferred, (h) hand-picked.

---

## 0. What changed and why

| # | the critique said | I checked | result |
|---|---|---|---|
| 1 | BANK ZONE fires on stale evidence, on broken walls, and never reads the wall's OI | **True** [M]: 5 of the replay's 10 tones fired in the same second as REACHED, on evidence carried from before; 2 banked walls already broken (`s.banked` never checks `s.broke`) | I built the strict version: evidence only after the reach, wall not broken, the wall's own writers not leaving. It still fired 3 times in 4 on walls that broke 33–110 min later while the trade ran on, and missed both real tops (§3.5). **BANK ZONE, its tone and its glyph are gone.** The wall ahead is a line of numbers, never a verdict. |
| 2 | Winner mode's only floor is her entry; a slow bleed never fires | **True** by construction | **The held breach is taken for winners:** flow + OI, **or** an acceptance that stands 2 more bucket closes and ≥ 2× the median bucket time. 24 Sep: +98 instead of +81. |
| 3 | The entry backstop | It never decided an exit in 8 trades [M] (it fired once, 25 Sep 14:05, four hours after that trade's exit). With the held breach, G past entry is always crossed first. | **Cut.** One rule fewer. |
| 4 | Loser mode has no whipsaw guard at the open | **Half true.** The 25 Sep 09:47 acceptance was 512 lots, two full buckets, over 80 s. It was not thin, it was fast. Putting the time floor on losers (`PL_*`) costs **33 points over the 4 losers** (−114 v −81), and turns the 22 Sep call into a NOISE exit at −53 instead of a REAL one at −42 [M]. | **Kept:** losers leave on first acceptance. The whipsaw is answered by the re-entry read (§5), not a slower stop. |
| 5 | The mode keys on her fill: "the disposition effect written into the engine" | **The label is backwards.** The disposition effect is selling winners too soon and riding losers; PRO does the reverse, which is her stated problem. **The substance I tested:** the mode keyed on the market ("her side has won since entry", `PT_*`) gives identical exits on all 8 [M], but it puts 2 losing trades (22 Sep call, 23 Sep put) under the patient law while they were losing. | **Kept on the fill.** A stop past entry is a free trade; that is the money reason to give it rope, and it is the only reason. The mode never shows on screen as "winner/loser"; line 2 states the out-condition. |
| 6 | Word and chip flicker: 8.0 words/h on 24 Sep, "gate stated then not applied" | **True.** | **The headline is now three states: HOLD, PAST GIVE-UP, OUT.** Behind you, pullback, tiring and failed become the clause under HOLD. Headline changes: **0–0.7 an hour on all 8** [M] (24 Sep: 4 changes in 5.5 h). Chips still fail ≤ 6/h on 4 of 8; §6 says what is gated and what is not. |
| 7 | WALL BROKE re-labels the give-up; changed no exit | **True** | **Cut** (all PRO-2 runs have it off; exits unchanged). |
| 8 | "the give-up for the rest" implies a size | **True** | Gone with BANK ZONE. |
| 9 | Phase 0(d) OI baseline is null on Wednesday | **True**: Tuesday's last snapshot is the expiring weekly; the 6 Oct series was never recorded | Out of Phase 0. It works from **Thursday** (Wednesday records the 6 Oct series as front weekly). Wednesday says "could not check: the 6 Oct series was not recorded before today". |
| 10 | Six tabs are still six | **True** | **DESK** (Validate + Board's flat half, subject to her Board mockup review), **WAR**, **RECORD**, the **Trade** tab kept visible (her order), and the panel. |
| 11 | `FOLD_NEEDS` removes her hand | **Rejected.** Her brief tonight: "rather than asking, whatever is the best practice". A knob on the stop is a knob a son turns mid-trade. Fable's own revision now agrees. | No switch. The forward log keeps every alternative column so the question is answered by her data, not by her mid-trade. |
| 12 | The 09:15–09:16 backfill lives only in memory | **True** (`chain_backfill.py:241-268`, audit §6) | Added to data truth and Phase 1. |

**Grafted from Fable's two documents:**
- **Premium at G from the chain's own prices** (the strike at the same distance from F\*), not greeks. I tested it on 22 Sep's expiry put against the actual premium at the exit (83.55): chain-own 83.1–84.0, linear 84.1–85.2, my Δ + ½Γ 89.7–93.5 [M]. My v1 gamma term was wrong on the one day I cited it for.
- **Ranking walls by current OI**, not day-high (day-high keeps a wall whose writers have gone).
- **After OUT, a live line under the frozen word**, never a revert in place.
- **SENSEX on its own clock; resting liquidity only while price is at G or A** (the visible book spans ~5 pts each side); falsifiers for TIRING and FAILED; the expression frozen when the mark row opens.

**Where Fable's revision and this one still differ:**
- **Its wall-ahead line prints "pros bank into a wall that holds"** while A is "adding". On her put that is 10:42–14:28, three and a half hours under the day's best trade: the early-bank pull, in words. I print numbers only (§3.5).
- **Its backstop.** I cut it (#3).
- **Its word set.** Its word set still alternates PULLBACK ↔ BEHIND YOU on trend days ("fights are fights"). Mine moves both to the clause, so the headline only changes on the out-condition.

**Corrected in my own v1:**
- "With free execution, re-entry costs the spread." False. It costs the move back. 25 Sep call: OUT at 86.65, re-entry read at 10:24 at 100.9 [M].

---

## 1. The decisions, in one page

1. **Two questions, asked at two places.**
   - **Is the trade wrong?** Price is *accepted* past the level she entered on. That is a stop, and it does not wait for OI.
   - **Is the trade done?** The tool does not answer this with a verdict. In this sample, nothing in the tape named a top (§3.5). It shows the wall ahead in numbers, the premium's peak and what has been given back. She banks.
2. **A trade whose give-up has trailed past her entry gets her own rule, plus a floor.**
   - Her rule: flow accepted past G **and** the writers behind her leaving.
   - The floor: the acceptance stands two more bucket closes.
   - Before that, first acceptance is OUT.
3. **One headline, three states: HOLD · PAST GIVE-UP · OUT.**
   - Everything else is the clause under HOLD, or a row.
   - One sound: OUT.
4. **Line 2 always says, before it happens, exactly what would take her out.**
5. **One engine (`fold.py`), one record, one event log, two faces.** Shadow first, faces on her signature.
6. **No GO, no NO.** The entry screen is the in-trade screen for a hypothetical mark, plus three amber clauses.
7. **Three screens plus the kept Trade tab and the panel.**
8. **One amendment, PRO-2, signed once.** No switches in it.

---

## 2. The trader's day, and the screen for each moment

| moment | one glance | where |
|---|---|---|
| **Pre-open** | Contract and expiry/roll flags. Yesterday's high/low/close *for this contract*. The walls each side of F\*, from the last same-expiry snapshot (or "could not check" and why). | DESK header, THE DAY |
| **Open** | Who the gap trapped against yesterday's close [I]. The first fight. Every read live from its first mark ("n of 5"). | DESK · FLAT |
| **Flat** | NEXT FIGHT above and below, and what would confirm each. The re-entry read after an OUT. | DESK · FLAT, the panel |
| **Entering** | IF YOU WERE IN: the headline it would show, G and the premium there, the wall ahead, the expression. | DESK, the panel's mark row |
| **In a trade** | Headline, 4 chips, the out-condition, the premium with its peak and what is given back, the wall ahead. | DESK and the panel, identical |
| **After / close** | The trade's word history, falsifier counts (never rates). | RECORD |
| **Any time** | When each wall was built and whether it is held. | WAR |

**Cut** (as v1): Glass, Heat, Tape, Flow, Chain, OI Flow, Map, Events, the VPIN tab, `App.tsx`'s mock first paint.
- Board's regime / trapped / plays lines fold into DESK · FLAT. Her review of the Board mockup decides the layout.
- **Trade stays in the strip.** Hiding it needs her word.

---

## 3. Hold and exit

### 3.1 What I check before I change my mind (unchanged in order, one edit)

1. Where is price against my give-up?
2. Was it accepted there, or poked?
3. Initiative or absorption at the level?
4. Did the writers behind me leave after I entered?
5. Is the wall ahead loading or covering?
6. VPIN.
7. Tiring, or a failed extreme?
8. What have I given back?
9. The clock.

**Edit to item 7:** a failed extreme *my* way at the wall ahead is a fact to weigh. It is not a signal to bank: the replay says it is usually a pause before the wall breaks (§3.5).

**What never moves me:**
- a candle close;
- a trend box;
- a quiet clock;
- her S1–S4 lines;
- OI off-peak while price still holds my level;
- one minute of anything.

### 3.2 The engine (`fold.py`, pure, stdlib)

**H v3 unchanged:**
- bucket, B, θ = 2B, w = B/2;
- F\* = the options' forward;
- fights, levels, traps;
- **G**: seeded at the mark, re-set on her side's wins, locked once touched;
- **W**, the wall that sets G;
- the OI event (≥ 3σ√n off the since-entry peak, withdrawn on a rebuild);
- acceptance (one bucket at or beyond G over ≥ the median bucket time, reset by a print w back inside);
- FAILED, TIRING;
- chips confirmed on 2 closes.

**Changes:**

| rule | exact form |
|---|---|
| **Wall ranking** | One ranking, by **current** OI, near-ATM top-2 beyond F\* by w, with the 2-close hold. W = the most current OI between F\* and G, chosen when G is set. A = the nearer top-2 on the far side, at K + basis, at least w beyond her entry. |
| **Mode** | *trailed-past-entry* if d·(G − E) > 0 (E = her entry future price), else *at-entry*. Re-read when G changes; G only steps on wins, so the mode cannot flap. |
| **OUT, at-entry** | acceptance beyond G |
| **OUT, trailed-past-entry** | (acceptance **and** a live OI event on W, same epoch) **or** the held breach: the acceptance stands 2 (h) more bucket closes and ≥ 2× the median bucket time, with no win by her side and no print w back inside |
| **PAST GIVE-UP** | trailed-past-entry, accepted, neither condition yet. Line 2 counts: "22925 accepted 14:37 · 1 of 2 buckets · 22900 CE writers holding". |
| **Premium at G and at A [I]** | the premium of the same-type strike at K′ = K + F\* − G (resp. A), interpolated between the two nearest strikes. Chain older than 60 s: "could not check: chain 70 s old". |
| **Peak and given back [M]** | best premium since entry with its time; now against it |

**Removed from PRO-1:**
- the entry backstop;
- WALL BROKE and its tightening;
- BANK ZONE and REACHED as words;
- the Γ term.

**SENSEX:**
- FLOW and VPIN read CAN'T CHECK with the lot count;
- G = the defending wall + w;
- acceptance runs on **SENSEX's own** median bucket time, flagged.

### 3.3 The headline, the clause, and after OUT

| headline | look | sound | clause / line 2 |
|---|---|---|---|
| **HOLD** | ink | none | Clause, one of: `behind you · won 11:04` · `pullback since 12:28` · `tiring since 11:14` · `failed low 11:56` · `no read yet`. Line 2 is the out-condition. |
| **PAST GIVE-UP** | amber | none | "22925 accepted 14:37 · 1 of 2 buckets · writers holding" |
| **OUT · 22925 accepted** / **OUT · 22925 accepted, 22900 CE writers left 11:42** / **OUT · 22925 held 2 buckets** | ink block | two low tones, once per epoch, ids kept across reloads | frozen with its time |

**Line 2, before anything happens:**
- at-entry: "out if 22997 is accepted";
- trailed: "out if 22925 is accepted and held 2 buckets, or accepted while 22900 CE writers leave";
- when the OI event is already live, line 2 says so: "22900 CE writers left 11:42: acceptance past 22925 now takes you out".

This is what her question asked for: what would change the decision, named before it happens.

**After OUT:**
- the headline stays until she presses I'M OUT or unmarks;
- the line under it keeps reading live ("still marked · now: your side won again 12:35");
- it never reverts in place.

### 3.4 Pullback or invalidation (unchanged, compact)

- **Pullback:** price short of G, or past G and not accepted; flow absorbed or the other side tiring; the wall behind building.
- **Invalidation:** accepted beyond G. At-entry: that alone. Trailed: plus the writers leaving, or held two buckets.

The row prints it in numbers, e.g. "22925 accepted: 270 lots over 5 min · 22900 CE 240.0 → 235.9L at 11:42".

### 3.5 The trade is done? What the tape said in this sample

**The strict "done" read I built** (evidence only after the reach, wall not yet broken by θ, the wall's own writers not leaving by their own noise, in profit):

| fired | trade then | the wall | what followed |
|---|---|---|---|
| 22 Sep 12:28 | put +117% | 23350 PE, writers at their high 271.2L | broke 13:01; the put went to +264 |
| 25 Sep 09:47 | put +26% | 23100 PE 141.4L (peak 157.6L) | held; the trade exited +7 at 10:08 |
| 28 Sep 09:48 | her put +18% | 22900 PE 121.8L (peak 132.0L) | broke 10:41; the put went to +97 |
| 28 Sep 12:28 | her put +28% | 22850 PE 133.6L, at its high | broke 14:18; +97 |

**Missed both tops:**
- **22 Sep, 13:54 (+221):** the 23300 PE writers were *leaving* (356.4 → 261.9L at 13:54:42). That is fuel, not a wall holding.
- **28 Sep, 14:38 (+90):** there was no evidence after the reach.

**Fable's "holding / giving" as a word would toggle.** The 3σ√n event on the 22850 PE fired and withdrew **9 times between 10:42 and 14:16** [M].

**So the wall ahead is one line of numbers, in every mode:**

> ahead 22850 PE · 37 pts · 123.3L, peak 124.4L 11:37 [M]

- No word, no colour for side, no sound.
- A wall's writers pulling 55L in 27 minutes shows as the number falling. Her eyes read it; the tool does not name it "fuel" or "holding".

**What protects the winner:**
- the give-up and the held breach;
- the peak-and-given-back line;
- her 15:00 practice.

**Known ceiling:** the 15-minute expiry-gamma V (22 Sep +264 → +77). No structure trail catches it. The given-back line shows it as it happens; she decides.

### 3.6 The replay: 8 trades, 5 days, to 15:00

P&L in % of entry premium [M]; exit = the engine's actual first OUT.

| trade | best | v3 | flow alone | PRO-1 | time floor on all (`PL`) | **PRO-2** (`PF`) |
|---|---|---|---|---|---|---|
| 22 Sep put @ 47.75 (expiry) | +264 | +77 | +68 (whipsaw) | +77 | +77 | **+77 · 14:19** (flow + OI; held 14:24 +70) |
| 22 Sep call @ 43.65 | +78 after −61 | −42 | −42 | −42 | −53 (noise) | **−42 · 13:51** |
| 23 Sep put @ 122.3 | +3 | −12 | −12 | −12 | −15 | **−12 · 12:04** |
| 25 Sep put @ 111.6 | +42 | +7 | +13 | +7 | +7 | **+7 · 10:08** |
| 25 Sep call @ 96.5 | +53 after −29 | −19 | −10 | −10 | −21 | **−10 · 09:47** (noise; re-entry read 10:24) |
| **28 Sep call @ 84.05** | 0 | none, −61 | −17 | −17 | −25 | **−17 · 10:16** |
| 24 Sep put (hindsight) @ 102.65 | +154 | +81 | +116 | +81 | +98 | **+98 · 14:39** (held) |
| **28 Sep put, hers** @ 120.4 | +97 | none, +71 | none | none | none | **none · +71 at 15:00** |
| **sum** | | +102 | +187 | +155 | +139 | **+172** |

**Noise [M]:**
- OUT sounds: 0–0.37 an hour.
- Headline changes: 0–0.7 an hour.
- Clause changes: 0.4–8.0 an hour. That is the fight tape, and it lives under the headline.
- Chip changes: 4.4–11.8 an hour.

**Honesty:**
- n = 8 describes; it does not rank.
- Flow alone summed higher. It won on 24 Sep and on the 25 Sep put, and on 22 Sep it whipsawed out at 11:28 of a +264% trade.
- The forward log keeps all four columns: plain acceptance, flow + OI, held, and PRO-2.

---

## 4. Entry

**The in-trade face for a hypothetical mark**, headed IF YOU WERE IN:
- the headline and clause it would show;
- line 2 (what would take her out);
- G and the premium there [I];
- the wall ahead in numbers and the premium there [I];
- premium against its day VWAP [M];
- days to expiry.

**Room and give-up are two printed distances. Nothing refuses.**
- Her +97% put had 41 pts of room against a 56–72 pt give-up at 09:30.
- A ratio refuses trend trades at the first wall, which is the wall that gives.

**Three amber clauses:**
- "you would enter past your give-up";
- "you would enter at the 22900 PE writers (132.0L)", as a fact, not "where pros bank";
- "after 15:00: your practice is no new trades".

**The expression** (grafted from Fable's revision, which follows how she sells):
- read at bucket closes, 2-close confirmed, every minute, ATM on F\*;
- **frozen when the mark row opens.**

| read | when |
|---|---|
| **BUY the option** | the newest fixed fight her way was initiative, **and** the wall ahead is not adding, **and** it is not expiry day |
| **SELL the other side, ATM (ITM in a trend)** | any of: expiry day or eve; her side's last win was absorption, or TIRING is live; the wall ahead is adding; a box (both walls adding, VPIN quiet) |
| **EITHER** | neither holds |

- R2 (never sell into a squeeze) and R4 (never sell a bid straddle) stay from EXPRESSION rev e.
- The sale is folded by the same engine with d flipped: no reach, no strike stop.
- Shadow first, forward-logged. Counts, never odds.

---

## 5. Flat, and the re-entry read

**NEXT FIGHT · above 22907 · below 22852**, with what confirms each:
- "sellers give up when lifts at 22905–22910 are followed by price **and** 22900 CE comes off its peak: calls";
- the mirror for puts.

When both halves fire, the flat word is a frozen event with no sound: **SELLERS GAVE UP AT 22907 · 11:42**.

**Re-entry read:**
- **Trigger:** after an OUT, trading comes back w inside G and her side then wins a fixed fight.
- **What it prints:** "stop run failed at 23094: sellers absorbed at 23134, 10:24", with the premium now against her exit (100.9 v 86.65 on 25 Sep) [M].
- **Cost:** it costs the move back, not the spread.
- Silent, shadow-logged.
- **Falsifier:** G accepted again within 20 min.

---

## 6. The faces

### 6.1 The panel, 400 px, LIGHT

This is her put at 11:42 on 28 Sep, the real state from `PF_H2_0928_PE`. The writers behind her have just come off their peak while price sits short of her give-up. Her rule says hold, and the screen says so.

```
NIFTY SEP FUT · 11:42 · contract ✓ · chart placed
long 23000 PE · 120.4 · 09:30                              [ I'M OUT ]
HOLD · tiring since 11:14               ZONE▫  FLOW·  OI▫  VPIN·
22900 CE writers left 11:42: acceptance past 22925 now takes you out
PE 155.6 +29% · peak 182.7 +52% 11:16 · at 22925 ≈ 136 +13% [I]
ahead 22850 PE · 37 pts · 123.3L, peak 124.4L 11:37 [M]
OI    22900 CE 240.0L → 235.9L at 11:42 [M]; 22925 not reached
FLOW  no fight in the last 10 buckets
ZONE  at 22892: buyers held 141 lots [M lots, I side]
VPIN  1 of 10 buckets one-sided
▸ detail
```

Chips: ▪ with you · ▫ against · · quiet.

**Budgets:**

| | budget |
|---|---|
| **Numbers** | ≤ 24 with detail closed |
| **Colours** | 5: blue buyers, red sellers, amber, ink, grey |
| **Sounds** | 1 class: OUT |
| **Headline changes** | ≤ 1 an hour. Acceptance gate; met 8/8 [M]. |
| **Chip changes** | ≤ 6 an hour for the condition-born chips (ZONE, OI, VPIN) |

- **FLOW is exempt from the chip gate.** It is event-born and it *is* the fight tape; delaying it hides the tape. I set that after seeing the data, and it is flagged post hoc.
- **ZONE still fails on trend days** (22 changes on 24 Sep). Fable's two candidates go to replay before the signature:
  - ZONE event-born: it changes on level birth, break, or a fight;
  - VPIN out only after 2 closes past zero.
- A variant I tried, FLOW turning against only on fights within θ of G, changed nothing (`PC_*`).

**No flicker:**
- the DOM is patched, never rebuilt (`panel.js:515`);
- words are computed once per event batch;
- events are frozen at birth.

**Anytime:**
- the panel GETs `/api/hold/trades` through `sw.js` before its first frame;
- TapeMap down reads "your trade: could not check: TapeMap not reachable", never FLAT.

### 6.2 Mark my trade, chart marks, trust (v1 §5.2–5.3, with deltas)

**Mark my trade:**
- Mark trade → CE/PE → MARK;
- strike prefilled ATM on F\*, with ATM / ITM 1 / OTM 1 steps;
- the entry premium is frozen when the row opens;
- she can type her fill;
- `sw.js` → `/api/hold/trades` after the `Sec-Fetch-Site: none` build test;
- the trade persists in `data/day_state/`.

**Glyphs:**
- ▲▼ won;
- ▲▼ with a dot for "by price" [I];
- ▬ absorbed;
- hatched ▬ for a disputed fight;
- ⌃⌄ failed;
- ▸ her entry;
- ■ OUT.

**The BANK ◆ is removed.** The give-up is a dashed staircase. The walls are dotted lines with a strike chip at K + basis.

**Trust:**
- fit only `frame.day` (the `fit.js:194–203` session-jump bug);
- fitted latest bar within one bar;
- bar OI = TapeMap's future OI (the contract match);
- hysteresis 2 bad / 2 good;
- one tag while paused: "chart shows another day / contract since hh:mm; marks paused, panel live".

### 6.3 DESK

- The same headline, line 2 and rows as the panel, at 2× size.
- The check slip on the left.
- Detail open by default:
  - the G staircase;
  - OI events with z and σ;
  - acceptance tallies;
  - chip history;
  - the trade's words.
- The flat half: NEXT FIGHT, THE DAY, and the re-entry read.

---

## 7. Remove and add

**Remove.** Everything in v1 §6.1 stands:
- the session-high line and its close;
- trend as a fold;
- the quiet clock;
- the latch, heal and PERSIST;
- the warm-ups;
- GO/WAIT/NO;
- the 3-min expression on spot;
- the dead frame fields;
- the dark panel;
- the SMC layer;
- five wall rules → one ranking.

Plus:
- BANK ZONE, REACHED and WALL BROKE;
- the entry backstop;
- the Γ premium term;
- `FOLD_NEEDS`;
- the words PULLBACK / BEHIND YOU / TIRING / FAILED as headlines (they become clauses).

**Kept by her order:**
- the Dhan/Upstox fallback;
- `structure.py`, `band_rotation.py`'s two-leg stack, `contract_pair.py`;
- the Trade tab and its chart;
- `/api/surface`, `/api/drag`, `/api/paper_fill`;
- the zone's 09:25 anchor;
- `trigger_log.jsonl`, untouched.

**Add, each in shadow first:**
1. **Resting liquidity** only while price is at G or at A: offers stacked or pulled within the visible book, about 5 pts each side [M]. It is the acceptance's companion, never a lead.
2. **Big prints:** ≥ the 99th percentile of today's fill sizes [M], side if the ladder signed it [I].
3. **The event log**, `data/fold/fold_<IDX>_<day>.jsonl`. A restart replays it and never recomputes.
4. **The next-weekly chain on expiry days.**
5. **The GoCharting tick post** for disputes only.
6. **The re-entry read and the peak/given-back line.**

---

## 8. Data truth (v1 §7 stands; changes)

| defect | handling |
|---|---|
| **Bucket and B across the roll** | A change against both v1 designs [I]. Bucket and B pool the **front-month series**: Sep until its expiry, Oct from Wednesday. The far month trades a fraction of the front's volume before the roll, so Oct's own pre-roll record would shrink the bucket and speed the clock, the wrong way. Price levels (PDH/PDL/PDC) are the contract's own: Oct's Tuesday candle by REST at 09:00, else "could not check", never Sep's shifted by carry. |
| **OI baseline** | Previous session's last snapshot, same expiry, else "could not check". Wednesday 30 Sep: could not check (6 Oct unrecorded). From Thursday: it works. |
| **Morning backfill, 09:15–09:16, in memory only** | Written to disk, tagged backfilled, so a 09:20 restart keeps it. |
| **Premium at G / A** | Chain-own prices at K′ (§3.2). Tested on 22 Sep: within 0.5 of the actual at the exit [M]. |
| **Resting liquidity reach** | The five visible levels span about 5 pts each side. It is a touch read, scoped as such. |
| Spot v forward, guessed-side volume, three tapes, book from 09:17, 2-min-late rows, fit.js, VPIN first buckets, chain staleness, restart | As v1 §7. |

---

## 9. Build order (nothing in market hours; she starts the server; commits on her word)

**Phase 0: Tuesday after the close, before Wednesday's first October session. Plumbing only.**

| item | what |
|---|---|
| a | The `fit.js` single-day fit and the contract match, with the node fixture test: a chart with no date tick whose margin time exists on Friday must read "not trusted". |
| b | Contract stamps on every recorded row. |
| c | The panel to LIGHT tokens, patch-not-rebuild. |

Plus one `day_state` restart test. Nothing else touches the live path before Wednesday.

**Phase 1: this week, `fold.py` in shadow.**
- Built from `scratchpad/pro3/reader_p3.py` (PF settings).
- One `__main__` self-check: her 28 Sep put reads no OUT; the 28 Sep call reads OUT at 10:16.
- Appends to `data/fold/`.
- It is visible only as one grey line in DESK detail.
- Also in this phase:
  - the backfill to disk;
  - the same-expiry baseline (useful from Thursday);
  - front-month pooling for bucket and B.
- **Gates before she is asked to sign:**
  - every recorded day replayed with no OUT on arrival;
  - ≤ 1 sound an hour;
  - headline ≤ 1 change an hour;
  - the condition chips ≤ 6 an hour after the ZONE/VPIN candidates;
  - a mid-session restart replays identical words.

**Phase 2: on her signature.**
- DESK's hold section and the panel switch to `fold.read`.
- `hold.py`'s removed rules go in the same commit, tagged `pre-pro2`.
- The marks come from the event log.
- Mark-my-trade goes through `sw.js`.

**Phase 3:** the entry face, the expression, NEXT FIGHT, the re-entry read.

**Phase 4:** the cuts, one commit per group, tagged before.

**Phase 5:** the reads in §7, the SENSEX policy, and the pre-09:15 subscription last.

---

## 10. PRO-2: the one amendment she signs

**It closes:**
- rev 4 §1–§8;
- rev 5 §A–§G;
- VALIDATE rev 2 §1.2–§5;
- EXPRESSION rev e §A.2–§E.2;
- PLAN rev 3 §2.1.

Their rows stay in their own populations.

**It registers:**
- §3.2's rules and every threshold with its (h) mark;
- §3.3's headline, clauses and line 2;
- the wall-ahead line as numbers;
- premium from chain-own prices;
- §4's entry face and expression;
- §5's flat read and re-entry read;
- the fields each row logs, **including every alternative OUT column** (plain acceptance, flow + OI, held) for every marked trade.

**No switch and no count is asked of her.**

**Falsifiers, logged 30 sessions, shown as counts only:**

| read | wrong if |
|---|---|
| OUT, at-entry | back inside G by w within 20 min |
| OUT, flow + OI | the same, or W rebuilt above the event's peak within 20 min |
| OUT, held | back inside G by w within 20 min |
| PAST GIVE-UP | ended withdrawn (counted against those that ended OUT) |
| pullback clause | G accepted within 20 min |
| tiring / failed clause | a new extreme her way by θ within 20 min |
| re-entry read | G accepted again within 20 min |

**What the log must answer, not me:**
- On a trade trailed past entry, does waiting for the writers beat the held breach alone? 22 Sep says wait; 24 Sep says don't.
- Does a screen with no bank verdict help her hold longer? That is her stated problem, and the reason this tool exists.
