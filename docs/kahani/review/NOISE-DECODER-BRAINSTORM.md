# The noise decoder: pause or reversal, read causally — brainstorm, measurements, design

30 Oct 2026, after the close. Her words: *"understand noise is also give a message weather its trend continuation and just
pausing or pausing to reverse ... improve it to atleast 9 on 10 and it should be able to read like you would as a trader."*

Written by a trader-quant subagent, read-only. Every number is [M] measured on the record or [I] inferred (a threshold,
a rationale). Counts, never rates. Levels: s = spot strike, f = futures. Scripts (scratchpad, not the repo):
`nd/dump_frames.py` (cache `jarvis.build(day, NIFTY, None)` per day), `nd/events.py` (label), `nd/analyze*.py`
(measure), `nd/p1p2.py` (the P1/P2 claims), `nd/absorb.py`, `nd/decoder.py` (the design, replayed), `nd/counts.py`.

---

## 0. Record used

| Day | Minutes on the frame | Live from | Holes | Dext 1-min delta | Use |
|---|---|---|---|---|---|
| 12 Oct | 168 (09:17–13:41, hole 11:20–12:58) | 09:17 | 1 | 168 | morning only |
| 13 Oct | 45 | 09:17 | 0 | 45 | **not used** (45 min) |
| 16 Oct | 32 | 09:23 | 2 | 32 | **not used** (32 min) |
| 19 Oct | 369 | 09:17 | 1 | 369 | full |
| 21 Oct | 373 | 09:17 | 0 | 373 | full |
| 22 Oct | 374 | 09:17 | 1 | 374 | full |
| 23 Oct | 376 | 09:15 | 0 | 376 | full |
| 26 Oct | 360 | 09:32 | 0 | 360 | full |
| 27 Oct | 377 | 09:15 | 0 | 167 (Dext missing after ~12:00; flow from the book) | full; **monthly expiry** |
| 28 Oct | 377 | 11:07 (morning rebuilt) | 1 | 377 | full |
| 29 Oct | 377 | 09:15 | 0 | 377 | full |
| 30 Oct | 299 (78 min lost to the outages) | 09:15 | 6 | 299 | full, with holes |

[M] 10 usable days, 9 of them full. The frame's futures price and VWAP match the saved full tape (`bars1.json`) to
the point at 10:00 / 11:30 / 14:00 on 30 Oct. `build()` reads the .gz days itself; nothing needed rewriting.

---

## 1. The events, defined before the numbers were read

All on 1-min futures bars; everything below is causal (minute i reads minutes ≤ i).

| Term | Definition [I] | Why this |
|---|---|---|
| U | max(σ of the session VWAP, 0.1 % of price) | the stack's unit (HOLD v2, marks TOOTA) |
| leg | swing from an origin to an extreme, ≥ 40 pts | ~0.2 %; below it is tick noise |
| leg reverses | retrace ≥ max(½ leg, 1U) from the extreme | the trader's "the leg is gone" line |
| PAUSE event | first minute the leg (≥ 40 pts) retraces ≥ 0.5U from its extreme, or makes no new extreme for 9 min | what she sees on a 3-min chart |
| one event per extreme | a new event only after a real new extreme (≥ 0.25U past the last one) | no re-firing inside a drift |
| CONTINUATION | a new extreme ≥ 0.25U past the old one within 45 min, before any reversal | the hold was right |
| REVERSAL | the leg reverses (above) within 45 min, before a new extreme | the hold was wrong |
| UNRESOLVED | neither in 45 min | long pause |
| clean | no book hole in the 15 min before the event or inside its 45-min window | 30 Oct's outages, 12 Oct's hole |

[M] Events labelled: **144**, clean **137**: CONT 70, REV 49, UNRESOLVED 18.

| Day | events | CONT | REV | UNRES | note |
|---|---|---|---|---|---|
| 12 Oct | 6 | 5 | 0 | 1 | morning only |
| 19 Oct | 13 | 4 | 7 | 2 | |
| 21 Oct | 13 | 9 | 1 | 3 | −346, long unwinding |
| 22 Oct | 22 | 9 | 10 | 3 | two-way day |
| 23 Oct | 13 | 5 | 5 | 3 | |
| 26 Oct | 13 | 5 | 5 | 3 | |
| 27 Oct | 22 | 9 | 12 | 1 | monthly expiry |
| 28 Oct | 19 | 12 | 6 | 1 | +131, fresh longs |
| 29 Oct | 7 | 5 | 0 | 2 | +239, one-way |
| 30 Oct | 16 | 8 | 6 | 2 | 78 min blind |

The 30 Oct list matches the day's story: 10:17 (the 10:16–10:19 low) → REV at 10:55; 10:57 / 11:23 / 11:42 (the up-leg's
pauses) → CONT; 12:07 (the top) → unresolved (the window crossed the 12:41 hole); 13:44 (the pullback low) → REV at 14:23.

**Split that decides everything: 65 of 119 resolved events are before 10:00** (35 CONT / 30 REV). After 10:00: 35 CONT /
19 REV. The open is a different regime (§3).

---

## 2. What a trader sees at the pause, measured (leg frame: + = with the leg)

Full tables in `nd/analyze*.py` output. Rows = count of events where the read is true, CONT a/n vs REV a/n.
Per-day columns are given where the row matters, as `CONT a/n | REV a/n`.

### 2a. After 10:00 (CONT 35 / REV 19)

| Read at the pause minute | CONT | REV | per day (CONT \| REV) | verdict |
|---|---|---|---|---|
| **Jarvis's word WITH the leg** | 14/35 | 5/19 | | it leans in 14 of 35 holds |
| Jarvis's word NO TRADE | 19/35 | 11/19 | | the flicker |
| Jarvis's word AGAINST the leg | 0/35 | 0/19 | | never warns |
| leg reached ≥ 1.5σ before the pause | **23/35** | **6/19** | 19:2/2\|0/4 21:4/4\|0/0 22:2/4\|2/5 27:4/7\|3/6 28:5/8\|1/1 30:3/4\|0/0 | **separates** |
| leg reached ≥ 2σ | 15/35 | 3/19 | | |
| price now inside 1σ | 12/35 | **14/19** | 19:0/2\|4/4 22:2/4\|3/5 26:3/3\|2/2 27:2/7\|4/6 28:4/8\|0/1 | **separates** (rotation, not trend) |
| at the day's extreme | 15/35 | 5/19 | | mild |
| leg ≥ 100 pts | 27/35 | 13/19 | | no (after 10:00) |
| **writers ±7 9-min lean WITH the leg ≥ +10L** | 24/34 | **17/19** | | **the writers lag: with the leg in 17 of 19 reversals** |
| writers ±7 9-min lean AGAINST ≤ −10L | 4/34 | 0/19 | | never at a reversal |
| the leg's own writer fuel ≥ +10L (origin→extreme) | 22/34 | 10/19 | | mild: the LEG had fuel |
| **first strike ahead: OI rose ≥ 2L in 9 min** | **14/34** | **2/19** | 19:0/2\|1/4 21:4/4\|0/0 23:1/1\|0/1 26:1/3\|0/2 27:2/7\|0/6 28:2/4\|0/0 30:3/4\|0/0 | **separates, 6 days** |
| first strike ahead: OI fell ≥ 2L in 9 min | 8/34 | 10/19 | 27 Oct carries it: 5/7 \| 6/6 (expiry unwind) | mild once 27 Oct is set aside |
| wall ahead (§1d front) UNWINDING | 16/33 | 5/18 | | mild, same way |
| a TOOT with the leg during the leg | 24/35 | 10/19 | | mild |
| a push WITH the leg in the last 10 min | 23/35 | 9/19 | | mild |
| 3-min delta against the leg | 13/35 | **13/19** | 22:3/4\|3/5 27:1/6\|4/5 28:0/7\|0/1 | **separates, noisy** |
| 3-min delta with the leg ≥ +100 | 13/35 | 3/19 | | |
| speed decayed to ≤ ⅓ of the leg's max | 24/35 | 13/19 | | **no: decay is what a pause IS** |
| speed FAST against (≥ 2× median) | 2/35 | 3/19 | | rare, clean |
| Sides fuel with the leg | 12/12 | 5/5 | | lagging, like ±7 |
| all 3 in sync with the leg | 10/35 | 5/19 | | no |
| fut OI over the leg ≤ −500 (covering / unwind) | 16/35 | 8/19 | 21:4/4\|0/0 | day-level, §4.5 |
| OI churn (gross ≥ 3× net, ±7, 3 min) | 8/34 | 7/19 | | mild toward REV |
| retrace already ≥ 0.35 of the leg | 2/35 | 4/19 | | |
| pullback effort ≤ 0.7× the leg's (lots / pt) | 24/29 | 15/18 | | **no: every pullback is thin** |
| pullback effort ≥ 1.5× the leg's (absorption) | 1/29 | 0/18 | | **almost never fires** |
| pullback delta ≤ −0.25 of the leg's delta | 5/22 | 4/16 | | no |

### 2b. One 3-min bar later (+3 min, outcome still open: CONT 31 / REV 17)

| Read at +3 | CONT | REV | per day (CONT \| REV) |
|---|---|---|---|
| **retrace still < 0.20 of the leg** | **21/31** | **5/17** | 21:2/2\|0/0 22:2/4\|1/5 26:2/3\|0/2 27:3/6\|1/5 28:6/7\|1/1 30:4/4\|0/0 |
| **retrace past 0.35 of the leg** | **0/31** | **6/17** | 19:0/2\|1/3 22:0/4\|2/5 26:0/3\|2/2 27:0/6\|1/5 |
| back inside 1σ | 10/31 | 12/17 | |
| 3-min delta against ≥ 150 | 1/31 | 3/17 | |
| speed FAST against | 0/31 | 3/17 | |
| writers 3-min lean against ≤ −5L | 5/28 | 4/17 | no |

### 2c. Before 10:00 (CONT 35 / REV 30) — the open is its own regime

| Read | CONT | REV | verdict |
|---|---|---|---|
| leg reached ≥ 2σ | 20/35 | 19/30 | σ means nothing before 10:00 (σ is tiny) |
| leg ≥ 100 pts | 10/35 | 2/30 | only a 100-pt opening leg is a leg |
| price inside 1σ now | 11/35 | 17/30 | mild |
| the leg's writers FOUGHT it (fuel ≤ −10L) | 19/35 | 13/30 | writers sold the open drive and were run over: trapped inventory |
| fresh fut OI over the leg ≥ +500 | 8/35 | 2/30 | mild |
| no push with the leg at all | 30/35 | 27/30 | pushes rarely exist yet (the 30-min norm is warming) |

### 2d. Who opened the first strike ahead (premium minus delta × spot move, handshake's `who_opened`), after 10:00

| k1 ahead, 9 min | WRITERS | KHAREEDAR | ? |
|---|---|---|---|
| OI rose ≥ 2L | CONT 8/31 · REV 1/18 | CONT 5/31 · REV 0/18 | 0 |
| OI fell ≥ 2L | CONT 2/31 · REV 4/18 | CONT 6/31 · REV 6/18 | 0 |

[M] Whoever opens it, OI **building** at the strike ahead during a pause goes with continuation. Her thesis read at the
next strike: inventory loading at k1 is what the next leg traps. OI **leaving** k1 is sponsors leaving (option longs
closing, or writers lifting) — nothing to trap.

### 2e. Absorption bursts (a 3-min delta ≥ 3× its median, with the last 30 min's move), all days

| Burst | then a clean new extreme (30 min) | then retraced 0.5U | both / neither | n |
|---|---|---|---|---|
| did NOT extend the leg 0.25U within 5 min ("absorbed") | 9 | 24 | 23 | 56 |
| extended within 5 min | 3 | 7 | 5 | 15 |

[M] A ≥ 3× burst is a stall sign either way (31 of 71 retraced, 12 made a clean extreme). 29 Oct alone had 10 absorbed
bursts and 2 reversals; as a RISK input it hurt the trend day (§6). It is a **note**, not a word.

---

## 3. What separates, across days — and what does not

**Separates (the design uses these):**

| # | Read | Trader rationale | Evidence |
|---|---|---|---|
| S1 | **Leg quality before the pause**: after 10:00, ≥ 80 pts, reached ≥ 1.5σ or had a TOOT, or was fuelled (Jarvis's own UP/DOWN at any minute of the leg) | a leg that reached the band on fuel is a trend; one that stalls mid-band is a rotation | ≥1.5σ: 23/35 vs 6/19; the composite "after 10:00 & ≥80 & ≥1.5σ": 22 CONT vs 6 REV; false otherwise 13 vs 13 |
| S2 | **Pullback depth after one 3-min bar**: < 0.20 of the leg = pause; ≥ 0.35 = reversal in progress | her chart: a shallow flag vs a third given back | 21/31 vs 5/17; 0/31 vs 6/17; 5 days each way |
| S3 | **Inventory at the first strike ahead**: OI rising ≥ 2L / 9 min = the next leg is being loaded; falling = sponsors leaving | trapped inventory is the fuel (her thesis) | rose: 14/34 vs 2/19 on 6 days; fell: weak once expiry day is out |
| S4 | **Location now**: inside 1σ after a 1.5σ leg = the leg is being given back | the band is the trend's home | 12/35 vs 14/19; +3: 10/31 vs 12/17 |
| S5 | **Flow against with speed**: 3-min delta against ≥ 150 with speed ≥ 2× | the pullback has conviction | FAST against 0/31 vs 3/17; delta against 13/35 vs 13/19 (noisy alone) |
| S6 | **Time of day**: before 10:00 a 40–80-pt leg is a rotation; only ≥ 100 pts with a TOOT is a leg | the opening auction | 65 of 119 events are before 10:00; 100-pt: 10/35 vs 2/30 |
| S7 | **The day's futures-OI quadrant** over 30 min (not 5-min bursts) | short-covering / long-unwinding days keep going; the 500-lot/5-min bar found 0 runs on 19 Oct (−2,308 lots) and 1 on 30 Oct (−2,678) | 21 Oct: 9/9 CONT, long unwinding −9,620; 28 Oct: 11/12 CONT, fresh longs +5,891 |
| S8 | **Leg flips so far today** = day type | a day that gives legs back at half keeps doing it | flips by 12:00: 29 Oct 0, 12 Oct 0, 21 Oct 1 vs 22 Oct 7, 27 Oct 15, 28 Oct 12, 19 Oct 7; after the 2nd flip 22 Oct ran 8 CONT / 8 REV |

**Does not separate (and the design says so on screen):**

| Read | Why it fails | Evidence |
|---|---|---|
| **writers ±7 lean at the pause** | the writers follow price: put writers add below every rise; they are with the leg at 17 of 19 reversals, so a "switch" is read AFTER the turn | 24/34 vs 17/19; lean against never at a REV; a true SWITCH (cap adding + floor leaving) 3 times in 119 |
| Sides at the pause | same lag, 5-min slots | with the leg 12/12 vs 5/5 |
| speed decay | decay IS the pause | 24/35 vs 13/19 |
| pullback effort / absorption | pullbacks are thin in both; ≥ 1.5× fires once in 47 | §2a, §2e |
| all 3 in sync | a second vote, not a first | 10/35 vs 5/19 |
| OI churn, range compression | mild / rare | 8/34 vs 7/19; compression 4 vs 1 |
| the writers' lean before 10:00 | writers who fight the open get trapped: lean against = fuel, not a warning | 19/35 CONT had the writers against the leg |

**So what does noise say?** Measured, the pause's own flow says little (thin, decaying, writers lagging). The message is
in (a) what the leg was before the pause, (b) how deep the pause goes after one bar, (c) whether the next strike is
loading, and (d) the rare burst against. "Writers first" is right for the LEG's direction and fuel (S1, S7); at the
PAUSE the writers are a lagging confirmation and the screen must say "lagging" next to them.

---

## 4. The P1 / P2 items, tested on the record (not one day)

### 4.1 P1-3 "the call leans and holds" — supported, and it is the biggest lift

[M] At the 54 after-10:00 pauses Jarvis read NO TRADE 30 times and WITH 19; on 30 Oct 11:00–12:10 it flipped UP ↔ NO
TRADE 8 times. The decoder (§5) holds the LEG as the lean: 30 Oct 11:00–12:10 lean changes **0**; 29 Oct lean changes
**0** all day (closed +239); word changes inside the lean are TREND ↔ PAUSE·hold, not UP ↔ NO TRADE.

### 4.2 P1-4 "let absorption speak at a σ extreme" — not supported as written

[M] 2/3 signs on 10 days: 45. Blocked 30 (10 right by "reversed ≥ 0.5U with no new extreme in 30 min"), spoken 15 (4
right). At |z| ≥ 1.8: 6 signs, 2 right. Absorption ≥ 2× effort at a pause: 1 of 47. The 30 Oct 13:44 bottom is real, but
the rule that catches it (a ≥ 3× burst with the leg that fails to extend, §2e) hurt 29 Oct (10 such bursts, 2 reversals).
**Design:** the burst is a NOTE on the pause line ("climactic −2,228 at 13:42, no new low in 5 min"); it becomes a word
only with S2/S4 company.

### 4.3 P1-5 "RISK needs a move behind it" — the sketch is backwards on this record

[M] 39 RISK events on 10 days: went against ≥ 0.5U in 30 min **15**, new extreme first **12**, new extreme later 1,
neither 11. 17 of 39 had < 25 pts of leg behind them. The 7 with a real move (≥ 50 pts, within 0.5U of the extreme):
new extreme first **4**, against 1, neither 2. The "move behind it" filter keeps the ones that were mostly wrong and drops
14 of the 15 right ones. **Design:** RISK is retired as a word; its ingredient (a 2× delta spike against while the
writers pause) joins S5 as one risk item among several, and PALAT? needs two.

### 4.4 P1-6 "NAHI with the fuel running = absorbing" — not supported

[M] 116 NAHI pushes with 15/30-min outcomes:

| writers' state at the push | n | 15 min: went on ≥ 15 | rotated ≤ −15 | 30 min: ≥ 25 | ≤ −25 |
|---|---|---|---|---|---|
| fuel WITH the push (Sides REAL/BACKED, ±7 leg, or ±7 push) | 38 | 10 | 15 | 14 | 13 |
| fuel AGAINST the push | 30 | 5 | 7 | 7 | 6 |
| no fuel read | 48 | 12 | 19 | 10 | 18 |

A NAHI with the fuel running rotated as often as it went on. The three 30 Oct cases were one day. **Design:** NAHI stays
"no answer"; the push's meaning comes from the LEG state (in a trend leg a NAHI is one knock among several; in a
rotation it is nothing) — never from the fuel alone.

### 4.5 P2-8 the slow futures-OI trend — supported, and it is the day's spine

| Day | price | fut OI (lots) | quadrant | runs the 500-lot/5-min bar found | 30-min quadrant minutes (\|ΔOI\| ≥ 500 & \|Δpx\| ≥ 15) |
|---|---|---|---|---|---|
| 12 Oct (am) | −234 | +585 | fresh shorts | 0 | ▼ fresh 24 |
| 19 Oct | −221 | −2,308 | long unwinding | **0** | ▼ fresh 3 |
| 21 Oct | −346 | −9,620 | long unwinding | 10 | ▼ unwind 99 · ▲ cover 43 |
| 22 Oct | +103 | −11,201 | short covering | 8 | ▲ cover 84 · ▼ unwind 69 · ▲ fresh 22 |
| 23 Oct | −188 | −7,137 | long unwinding | 15 | ▼ unwind 91 |
| 26 Oct | +271 | −541 | mixed | 9 | ▲ fresh 56 · ▼ unwind 62 · ▲ cover 43 · ▼ fresh 30 |
| 27 Oct | +73 | −25,388 | expiry unwind | 13 | ▲ cover 100 · ▼ unwind 58 |
| 28 Oct | +131 | +5,891 | fresh longs | 13 | ▲ cover 65 · ▲ fresh 38 · ▼ fresh 31 |
| 29 Oct | +239 | −2,255 | short covering | **2** | ▲ cover 68 · ▲ fresh 24 |
| 30 Oct | +105 | −2,678 | short covering | **1** | ▲ cover 48 |

[I] Bar: |ΔOI| ≥ 500 lots AND |Δprice| ≥ 15 pts over 30 min, read every minute. Words: fresh longs / fresh shorts / short
covering / long unwinding, with the lots. It is a context line, never a direction call on its own.

### 4.6 P2-7 the fight re-anchor — supported; the fix is to anchor the fight to the LEG

| Day | fights | minutes on the main wall | of them > 2 steps from price |
|---|---|---|---|
| 29 Oct | 22,700s PE from 09:15, never ended | 361 | **315** |
| 21 Oct | 23,000s CE from 10:34 (price fell 346) | 283 | 243 |
| 19 Oct | 23,000s PE from 09:17 | 359 | 152 |
| 28 Oct | 22,700s CE / 22,600s PE | 91 + 128 | 50 + 88 |
| 22 Oct | 22,800s CE | 158 | 72 |
| 30 Oct | 23,000s CE | 299 | 3 |

**Design:** the fight's wall = the first §1d front ahead of the LEG (k1 or the top-2 front within 2 steps), re-anchored
whenever the leg flips (PALAT) or price is > 2 steps past it for 15 min [I]. The chapters (DASTAK / TOOT / RASAD /
KHATAM) stay as they are; only the wall they are told about moves.

---

## 5. The design: LEG → PAUSE → PALAT, a state machine with hysteresis

One object replaces "the call flickers": **the LEG**. Jarvis keeps every sense; this changes what the top line says.

### 5.1 States and words

| State | Word on screen | Enter | Leave |
|---|---|---|---|
| NO LEG | `NO LEG` | open | first 40-pt swing |
| ROTATION | `ROTATION ▲ · 57 pts · 2.6σ · no TOOT` | a leg that is not yet a trend | qualifies (below) or flips |
| TREND running | `TREND ▲ 135 pts · 2.6σ · TOOT · fuelled` | S1: after 10:00 ≥ 80 pts AND (≥ 1.5σ OR a TOOT with the leg) OR fuelled (Jarvis's UP/DOWN at any minute of the leg); before 10:00 ≥ 100 pts AND a TOOT | a pause, or a flip |
| PAUSE · hold | `PAUSE ▲ · hold` + the items | retrace ≥ 0.25U or no new extreme for 6 min | a real new extreme (≥ 0.25U past the pause's extreme) → running; or risk |
| PAUSE · watch | `PAUSE ▲ · watch` | one risk item, no alive item | |
| PALAT? | `PALAT? ▲ leg at risk` | retrace ≥ 0.35 of the leg, OR speed FAST against, OR ≥ 2 risk items | items clear for 3 min |
| PALAT | `PALAT ▼ — leg ▲ 218 gave back 120 (0.55): new leg ▼` | retrace ≥ max(½ leg, 1U) | the new leg starts as ROTATION |

**Hysteresis:** the lean (▲/▼) is the leg's direction and changes only at PALAT. Inside a lean the pause word holds for
3 min [I] unless the new word is PALAT? from FAST-against or the 0.35 retrace. (Still owed: a one-way hold so a stale
PALAT? is not carried, §7.)

### 5.2 The items (each with its number; the screen shows the list, nothing hidden)

| Risk items (against the leg) | Alive items (with the leg) |
|---|---|
| `retrace 0.36 of the leg` | `shallow 0.12 after 9 min` (needs ≥ 3 min) |
| `speed FAST against ×2.2` | `23,100s CE loading +10.0L / 9 min` (k1, the first strike ahead) |
| `3-min delta against −164` (≥ 150) | `push with the leg in 10 min` |
| `back inside 1σ (+0.4)` (after a ≥ 1.5σ leg) | `writers ±7 with +24L (lagging)` — always tagged lagging |
| `23,050s CE emptying −6.2L / 9 min` (weak: needs company) | |
| `push against TOOT the wall behind` | |
| note only: `climactic +736 at 12:00 with the leg, no new extreme in 5 min` | note only: `fut OI: ▲ short covering −839 lots / 30 min` (S7) |

Thresholds [I]: 0.25U pause, 0.35 / 0.50 of the leg, k1 ±2L / 9 min, delta 150 lots / 3 min, FAST = 2× the day's median
|3-min delta|, 1.5σ / 80 pts (100 pts + TOOT before 10:00). None was tuned to the outcomes: 0.25U and ½-leg are the
stack's existing lines, 2L is the handshake's CUT_L floor, 150 lots is the push floor, 80 pts ≈ 2U on a quiet day.

### 5.3 The header lines, in GAPS §4 order

```
HEALTH   blind 12:41–13:30 (book empty) → CAN'T SEE since 12:41 · last word not carried     (P0, as in the review)
DAY      flips so far 0 · fut OI ▲ short covering −839 lots / 30 min · all 3 ▲              (S8, S7, sync)
LEG      TREND ▲ 218 pts · 2.6σ · TOOT 11:30 · fuelled 11:00 · origin 22,955f · extreme 23,173f
PAUSE    hold · shallow 0.12 after 9 min · 23,100s CE loading +10.0L/9 · writers ±7 +20L (lagging)
WRONG    PALAT? if retrace past 23,097f (0.35) · or FAST against · PALAT at 23,064f (½ leg) — the lean ends there
BUYER    CE on the pullback to u1 23,116f, not chased · stop = the PALAT line
SELLER   sell the PE under the pullback low 23,146f (the floor the put writers are building, lagging) · same stop
```

Both ways, writers first: the LEG line names the fuel (fuelled = writers' 2×2 + ±7 agreed; TOOT = the wall gave);
the SELLER line is the side the writers are writing; the BUYER line is the band. Before 10:00 the LEG line reads
`OPENING · rotation ▲ 57 pts · no lean until 100 pts + TOOT`.

### 5.4 Wrong-line for each read

| Read | Its wrong-line |
|---|---|
| TREND / PAUSE·hold | PALAT? at 0.35 of the leg, PALAT at ½ (named in f) |
| PALAT? | a real new extreme (≥ 0.25U past the pause's extreme) within 15 min → back to hold, say "wrong-line hit" |
| ROTATION (no lean) | the leg qualifies (S1) → lean |
| k1 loading | the loaded strike TOOTs the other way (handshake) |
| fut OI quadrant | the 30-min read flips sign |
| DAY flips | a leg that runs ≥ 2σ with a TOOT ends the "two-way" tag for that leg |

### 5.5 What this leaves untouched

Every registered rule (§1b zone, §1d fronts, §1m HOLD v2, §1q SENSEX reads NIFTY's flow). The handshake, Sides, speed,
signs, the fight chapters, the message stream. The decoder reads their outputs; it does not replace them. SENSEX: the
same machine on SENSEX futures and its own chain, NIFTY's flow (§1q) — G13 (its empty flow) must be fixed first.

---

## 6. Replays, causal (what the decoder would have said; `nd/decoder.py`, absorption as a note)

### 6.1 30 Oct — the key moments (levels f unless s)

| Time | Decoder | Items | What happened | Jarvis then |
|---|---|---|---|---|
| 09:50 (the ▲ push into 23,000s CE) | `ROTATION ▲ 57 pts · 2.6σ · opening · no TOOT` | no lean | rotated −85 | RANGE ✓ |
| 10:10–10:15 | `TREND ▼ 99→108 pts · 1.9–2.1σ · fuelled` | | the leg to 22,955 | DOWN / NO TRADE |
| 10:16 | `PAUSE ▼ · hold` | TOOT 22,900s PE | | |
| 10:19 (the day's low) | `PAUSE ▼ · hold` | 22,900s PE emptying −9.5L; push with; ±7 +66L (lagging) | low 22,955 | NO TRADE; 10:21 bottom sign blocked |
| **10:21** | **`PALAT? ▼ leg at risk`** | back inside 1σ (+0.9) · 22,900s PE emptying −11.3L | 2 min after the low | — |
| 10:35–10:45 | `watch` → `PALAT?` (retrace 0.36, inside 1σ) | | | zone BUY 10:36 ✓ |
| 10:55 | `PALAT ▲ — leg ▼ 125 gave back 63 (0.50)` | | | |
| **11:00** | **`PAUSE ▲ · hold`** (fuelled: Jarvis's UP) | 23,000s CE loading +6.6L | +66 in 30 min | UP ✓ |
| 11:10 | `TREND ▲ 100 pts · 1.7σ · fuelled` | | | NO TRADE |
| 11:15 (pause 1) | `PAUSE ▲ · hold` | 23,050s CE emptying −4.9L (risk) · push with · ±7 +37L | +35 | NO TRADE ("▼: nothing") |
| 11:20 | `TREND ▲ 135 · 2.6σ` | | | |
| 11:25–11:30 (pause 2) | `PAUSE ▲ · hold` | shallow 0.18 after 5 min · 23,050s CE loading +2.5L | +40 | NO TRADE / UP |
| 11:40–11:45 (pause 3) | `PAUSE ▲ · hold` | shallow 0.16 after 6 min · push with | +60 to 23,173 | UP / NO TRADE |
| 11:50 | `TREND ▲ 173 · TOOT 23,100s CE` | | | |
| 11:55–12:07 (the top) | `PAUSE ▲ · hold` | 23,100s CE loading +7.0 → +10.0L · shallow 0.03–0.12 | range 23,124–23,167 for an hour | UP at 12:00/12:10 ✗ |
| **12:15** | **`PALAT? ▲`** | speed FAST against ×2.2 · delta −164 | withdrawn at 12:20 as price held | RISK 12:15 |
| 12:20–12:40 | `PAUSE ▲ · hold` | 23,100s CE loading +3.5 to +9.5L · shallow 0.13–0.17 after 22–42 min | then blind 12:41–13:30 | NO TRADE |
| 13:30–13:40 | `PALAT? ▲` | retrace 0.40–0.45 · inside 1σ | | DOWN 13:35 ✓ |
| 13:42 | `PALAT ▼ — leg ▲ 218 gave back 120 (0.55)` | | push ▼ −2,142 → TOOT 23,000s PE | |
| 13:44 (the pullback low) | `PAUSE ▼ · hold` | 23,000s PE emptying −3.2L · push with · ±7 +37L (lagging) · **note: climactic −2,214 at 13:42, no new low in 5 min** | low 23,053, then +70 | DOWN ~ |
| 13:47 (with the burst as a risk item, ABSORB=1) | `PALAT? ▼` | climactic + PE emptying | right, 3 min after the low; the same rule hurt 29 Oct | |
| 13:58–14:15 | `PAUSE ▼ · hold` | shallow 0.07–0.18 · 23,000s PE emptying | **wrong: the bounce ran to 23,121** | DOWN 14:00 ✗ |
| 14:20 → 14:23 | `watch` → `PALAT ▲ — leg ▼ 123 gave back 70 (0.57)` | | | |
| 14:25–15:30 | `ROTATION ▲ 71 pts · 1.1σ · no TOOT` | no lean | range 23,075–23,112 | DOWN 15:00 / 15:15 ✗ |

Lean changes 11:00–12:10: **0** (Jarvis: 8 flips). Lean changes all day: 10 (the opening rotations count).
Honest misses on 30 Oct: the 10:19 low read "hold ▼" for 2 min; the 12:00–12:40 top read "hold ▲" (the pullback was
0.13–0.17 of a 218-pt leg and 23,100s CE was loading: by its own rules a pause; the flush came while blind); 13:58–14:15
"hold ▼" into a +70 bounce (the 13:44 absorption was a note, not a word).

### 6.2 22 Oct — a two-way day (11 leg flips)

| Time | Decoder | What happened |
|---|---|---|
| 10:00 | `PALAT? ▲` retrace 0.45 · FAST against ×5.1 · delta −925 | the 10:00 TOP RISK: −112 in 30 min ✓ |
| 10:05 → 10:10 | `PAUSE ▼ hold` → `PALAT ▲` | a 99-pt ▼ leg gave back half in 5 min (whipsaw) |
| 10:13–11:30 | `PAUSE ▲ hold` (217-pt leg; 22,750s / 22,800s CE loading +3.4 to +5.1L) | the up-leg held |
| 11:40 → 11:45 | `watch` (inside 1σ) → `PALAT ▼ — 217 gave back 122` | REV ✓ (Jarvis NO TRADE) |
| 11:55–12:40 | `PAUSE ▼ hold` · fut OI ▼ long unwinding −3,880 / 30 min · 22,600s PE loading +2.7L | the down-leg held to 12:52 |
| 12:52 → 13:05 → 13:19 | `PALAT ▲` → `PALAT? ▲` (inside 1σ) → `PALAT ▼ — 189 gave back 95` | REV ✓ 14 min before the flip |
| 14:37–14:51 | `PAUSE ▲ hold` → `PALAT ▼` | REV; read as hold until the flip ✗ |

On a two-way day the decoder follows each leg and warns at 0.35; its lean is wrong for the first third of every reversal.
The DAY line (`flips so far 7 by 12:00`) is the only honest help: *"this day gives legs back at half; take at the band."*

### 6.3 28 Oct — a low, then a one-way afternoon

| Time | Decoder | What happened |
|---|---|---|
| 10:05–10:15 | `TREND ▼ 110→138 · 2.4–2.8σ · TOOT · fuelled` · fut OI ▼ fresh shorts +3,467 / 30 min | the morning leg |
| 10:26 (the day's low) | `PAUSE ▼ hold` · note: climactic +1,210 at 10:18, no new low | low 22,4xx |
| 10:35 → 10:45 → 10:55 | `hold` (inside 1σ · 22,500s PE loading +5.5L) → `PALAT? ▼` (retrace 0.41) → `PALAT ▲` | the reversal read 19 min after the low, at 0.35–0.41 |
| 11:05–13:00 | `PAUSE ▲ hold` / `TREND ▲ running` through 5 pauses · 22,650s CE loading +1.7 to +2.9L | +131 close; Jarvis NO TRADE at 4 of the 5 |
| 13:19 | `PALAT? ▲` FAST against ×3.0 · delta −298 | the TOP RISK Jarvis carried to the close (G2) |
| 13:30 → 14:00 | `watch` → `hold` (shallow 0.19 after 30 min) | price held ✓ |

### 6.4 29 Oct — one-way (+239), lean changes 0

| Time | Decoder | What happened |
|---|---|---|
| 09:45 | `PAUSE ▲ watch` (fuelled, inside 1σ) | 09:45 was my own wrong "rotation down" (A161) |
| 10:06 | `PAUSE ▲ hold` · 22,800s CE loading +4.0L | +50 |
| 10:18–10:30 | `TREND ▲ 193→253 · 3.0σ · TOOT · fuelled` | |
| 10:38 | `PALAT? ▲` FAST against ×6.1 · delta −613 | the 10:38 TOP RISK; −39 in 30 min, then sideways |
| 10:44–11:00 | `PALAT?` (delta against −190 / −167 · inside 1σ) | 3-min holds; price went sideways |
| 11:30–13:30 | `PAUSE ▲ hold` · shallow 0.11–0.14 after 60–180 min · inside 1σ noted | the long pause; Jarvis RISK 10:38–12:50 |
| 12:50 | `PALAT? ▲` push against TOOT the wall behind · inside 1σ | **wrong-line hit at the resumption** |
| 14:08–15:00 | `hold` / `TREND ▲ 338` / `hold` · 22,950s CE loading +5.3L | +90 to the close |

---

## 7. Score, honestly

### 7.1 On the 137 clean events (decoder vs Jarvis, same minutes, causal)

| After 10:00 | CONT (35) | REV (19) |
|---|---|---|
| Jarvis WITH / NO TRADE / RANGE / AGAINST | 14 / 19 / 2 / 0 | 5 / 11 / 3 / 0 |
| Decoder at +0: HOLD+TREND / WATCH / PALAT? / ROTATION | **28** / 1 / 3 / 3 | 9 / 0 / **6** / 4 |
| Decoder at +3 (outcome still open; 31 / 17): HOLD / PALAT? / ROTATION | **25** / 4 / 2 | 6 / **9** / 2 |

| Before 10:00 | CONT (35) | REV (30) |
|---|---|---|
| Decoder at +0: ROTATION / HOLD+TREND / PALAT? | 23 / 12 / 0 | 25 / 3 / 2 |

Per day after 10:00, HOLD/TREND said at +0 (CONT a/n | REV a/n): 19 Oct 2/2|1/4 · 21 Oct 4/4|0/0 · 22 Oct 3/4|**5/5** ·
23 Oct 1/1|0/1 · 26 Oct 1/3|1/2 · 27 Oct 6/7|1/6 · 28 Oct 7/8|1/1 · 30 Oct 3/4|0/0.

Lean changes per day: 12 Oct 1 · 19 Oct 8 · 21 Oct 2 · 22 Oct 12 · 23 Oct 8 · 26 Oct 8 · 27 Oct 16 · 28 Oct 12 · 29 Oct 0 ·
30 Oct 10. HOLD ↔ PALAT? flips per day: 10 to 36 (19 Oct 36, 26 Oct 35) — still too many (§7.3).

### 7.2 Self-score against 9/10 [I]

| Piece | Jarvis (review) | This design | Why not higher |
|---|---|---|---|
| the call leans and holds | 5 | **8** | 0 flips in the 30 Oct leg and all of 29 Oct; wrong for the first third of every reversal on a two-way day |
| pause vs reversal at the pause minute | — | **6** | 28/35 holds right; 9/19 reversals still read "hold" at the pause; the first warning is at 0.35 |
| pause vs reversal one bar later | — | **7** | 25/31 vs 9/17 |
| the opening | 7 (RANGE) | **7** | says "rotation, no lean" on 48 of 65; misses the 29 Oct opening trend until 10:06 |
| signs / absorption | 4 | **5** | demoted to a note; the 13:44 bottom is a note, not a word |
| RISK | 5 | **6** | retired as a word; its ingredient is one item among several |
| NAHI | 5 | **6** | no longer promises "absorbing"; meaning from the leg state |
| the fight | 3 | **7** (design) | anchored to the leg; not built |
| slow fut OI | 4 | **8** | the 30-min quadrant names every day's spine; context only |
| writers first | — | **7** | the LEG's fuel is writer-first; at the pause the writers are shown as lagging, which is the truth on 17 of 19 |
| **overall** | **6** | **7.5** | |

Not 9. What a 9 needs is in §7.3.

### 7.3 What still fails

1. **Reversals are read at 0.35 of the leg, not at the pause.** 9 of 19 after-10:00 reversals read "hold" at the pause
   minute. Nothing measured at the pause minute itself separates better than 14/34 vs 2/19 (k1 loading). The record is
   thin here: 19 reversals on 8 days.
2. **Two-way days.** 22 Oct: every reversal read "hold" first. The DAY flip count is a hint, not a rule; a rule needs more
   two-way days than the 3 on this record (19, 22, 27 Oct).
3. **Flicker inside the lean.** HOLD ↔ PALAT? flips 10–36 a day. Owed: PALAT? must persist 6 min or be confirmed at a
   3-min close before it is shown, and a stale PALAT? must not be carried by the 3-min hold (seen 30 Oct 09:40).
4. **The opening.** No lean before a 100-pt leg with a TOOT; 29 Oct's +138 by 09:55 was read as rotation. Thin: 10 opens.
5. **Absorption / climax.** Real on 30 Oct 13:44 and 28 Oct 10:18, noise on 29 Oct (10 bursts). A note until a rule that
   separates them exists; the candidate (burst + inside 1σ + k1 emptying) was not tested for lack of cases.
6. **Expiry day (27 Oct)** breaks the k1 read (everything unwinds): G9's "0 DTE after 14:00 = expiry unwind" tag is a
   precondition; the design has no expiry mode.
7. **SENSEX** untested (G13: its flow is empty in the frame). **BANKNIFTY** chain too small (G14).
8. **Blind minutes.** The decoder inherits the 78 lost minutes; P0's rebuild from the Upstox tape is the precondition for
   any 30 Oct afternoon read.
9. **"Who" at k1** (writers vs buyers) did not change the k1 verdict; kept as a tag, not a rule.
10. **One record, 10 days, no forward rows.** Every threshold is [I]; the pass bar for the decoder's words is owed by her
    before any count is read as a verdict (§5e).

---

## 8. Not checked / could not check

- 13 and 16 Oct (45 and 32 minutes); the 12 Oct afternoon (hole 11:20–12:58).
- BANKNIFTY and SENSEX legs (SENSEX flow empty in the frame, G13).
- Her GoCharting footprint marks (`data/tape/ofd_marks*`) against the events: BADA PRINT at the pause was not read.
- Book depth (pulls / stacking at k1), IV per strike, VIX: not in the frame.
- Jarvis's per-minute call on days other than 30 Oct was reconstructed from its components (`jarvis_word` in
  `nd/decoder.py`, the same rule as `jarvis.call`, health / quiet NO TRADE ignored); checked against the saved 30 Oct
  5-minute replay (`replay_calls.json`): the same word on all 59 calls whose minute is on the frame [M].
- Her live server, Vite and the page server were not touched; nothing was started or stopped.

---
---

# Round 2 — warning AT the pause, and killing the in-lean flicker

30 Oct, later. Same record, same 137 clean events, same rules. Scripts: `nd/r2.py` (the battery), `nd/xi.py`
(cross-index variants, the two 30 Oct misses minute by minute), `nd/prem.py` (premium sensitivity), `nd/comp2.py` (the
post-hoc composite), `nd/flicker.py` + `decoder.decode(fr, flicker=True, min_show=6)`. All reads causal; thresholds [I]
stated before counting; nothing tuned to the outcomes except where marked POST-HOC.

Round 1's weak points, as the coordinator put them: S2 (retrace past 0.35 at +3) confirms a reversal that is already
under way; 9 of 19 after-10:00 reversals read "hold" at the pause minute; the pause word flickered.

## R2.1 Her footprint marks — do not separate at the pause

**Source and timing.** `data/tape/ofd_marks2_NIFTY_<day>.jsonl` (v2: `kind`, `winner` ±1, `tier`, `prov`, `t` = the
5-min bar's start, inferred from the 09:25 exhaustion sitting at the 09:25–09:29 bar's high). No first-seen stamp, so
[I] a mark is known at **bar close + 1 min**; a mark whose first row is appended after a row with a bar ≥ 10 min later is
tagged *late* and counted separately. Near the extreme = bar within [extreme − 5 min, now] and price within 1U of the
extreme. Against the leg = `winner` = −leg of {absorption, exhaustion, trap, climax, E6 THAKAAN, E7 CVD ulta, E3
DABAAV, E1 BADA}; with the leg = `winner` = +leg of {initiative, E2, E5, vacuum, E1}.

[M] Marks exist for 8 days (none for 12 and 19 Oct); first rows appended late: 21 Oct 2, 26 Oct 3, 28 Oct 1, 29 Oct 2,
30 Oct 6, the rest 0.

| After 10:00 | +0 (CONT 35 / REV 19) | +3 (CONT 31 / REV 17) | per day (+0, CONT \| REV) |
|---|---|---|---|
| any mark against the leg near the extreme | 6/35 · 5/19 | 10/31 · 8/17 | 21:2/4\|0/0 22:0/4\|3/5 26:1/3\|1/2 28:1/8\|1/1 29:1/1\|0/0 30:1/4\|0/0 |
| absorption / exhaustion against (final, not late) | 5/35 · 2/19 | 7/31 · 5/17 | |
| trap / climax / CVD-ulta against | 1/35 · 3/19 | 3/31 · 4/17 | 22 Oct 3/5 carries it |
| BADA PRINT (E1) against | 0/35 · 0/19 | 0/31 · 2/17 | both 27 Oct |
| a mark WITH the leg at the extreme | 8/35 · 9/19 | 13/31 · 11/17 | 22:2/4\|4/5 26:2/3\|2/2 |
| any mark near the extreme at all | 11/35 · 9/19 | 18/31 · 13/17 | |

Verdict [I]: at the pause her marks show the fight, not its outcome. A mark **with** the leg at the extreme (initiative
/ vacuum into the high) is, if anything, the reversal's shape (climactic initiative), not the continuation's. Kept as an
item in the composite (R2.6) because it was the only item at the 28 Oct 10:26 low and 3 of 5 on 22 Oct; alone it is nil.

## R2.2 Cross-index non-confirmation — dead on this record

Three definitions, after 10:00, +0 (CONT 34 / REV 19):

| Definition | BANKNIFTY | SENSEX | either |
|---|---|---|---|
| its leg extreme ≥ 6 min before NIFTY's and 0.25 of its leg off (round-1 strict) | 1/34 · 1/19 | 0 · 0 | 1/34 · 1/19 |
| ≥ 3 min before and 0.1 of its leg off | 5/34 · 3/19 | 0 · 0 | 5/34 · 3/19 |
| not at its own 30-min extreme (0.05 %) when NIFTY made the leg extreme | 7/34 · 3/19 | 3/34 · 3/19 | 8/34 · 4/19 |
| its last 5 min into NIFTY's extreme went the other way | 2/34 · 2/19 | 0/34 · 1/19 | 2/34 · 2/19 |

[M] The three indices make their intraday extremes together; what divergence exists leans the wrong way (8/34 CONT vs
4/19 REV). Dropped from the composite and the design. (SENSEX spot here is the chain's cash index; G13 is unaffected.)

## R2.3 Premium vs futures — the one new read that survives, at +3

ATM trend-side option (CE in an up-leg) fixed at the extreme's ATM strike; x = (premium now − premium at the extreme)
− delta × (spot now − spot at the extreme), from the chain rows (the handshake's `who_opened` arithmetic). "Holding" =
x > +th (the option is bid more than the move explains); "bleeding" = x < −th.

| After 10:00 | +0 (n 19 / 15) | +3 (n 27 / 16) | +3 per day, holding (CONT \| REV) |
|---|---|---|---|
| holding, th 0.25 | 5/19 · 3/15 | **10/27 · 2/16** | 19:1/2\|0/3 21:1/2\|0/0 22:2/4\|0/5 23:1/1\|1/1 27:1/6\|1/5 28:2/3\|0/0 30:2/4\|0/0 |
| holding, th 0.5 | 4/19 · 3/15 | 9/27 · 2/16 | |
| holding, th 1.0 | 3/19 · 2/15 | 7/27 · 2/16 | |
| bleeding, th 0.5 | 11/19 · 12/15 | 14/27 · **14/16** | REV: 19:3/3 22:5/5 26:2/2 27:4/5 |
| premium peaked ≥ 6 min before futures (at the extreme) | 2/30 · 0/18 | 2/27 · 0/16 | no |
| last-3-min window, holding th 0.25 | 9/31 · 5/18 | 15/27 · 4/16 | |

[M] Stable across 0.25 / 0.5 / 1.0. [I] Trader reading: one bar into the pause, if the leg's option is still bid above
what delta explains, the option market has not given up on the leg (buyers holding, writers not pressing) → hold; a
reversal almost never shows that (2/16). Bleeding alone says little (14/27 CONT bleed too: a pause crushes vol), but
**no bleed = no reversal** on 7 days. At the pause minute itself the sample is thin (n 19/15) and the read is weak.

## R2.4 Pause shape

| After 10:00 | +0 (35 / 19) | +3 (31 / 17) | per day (+0, CONT \| REV) |
|---|---|---|---|
| **range of the pause ≤ 0.5 × the 9 min before the extreme (coiling)** | **21/35 · 7/19** | 12/31 · 4/17 | 21:3/4\|0/0 22:4/4\|2/5 26:1/3\|0/2 27:7/7\|3/6 28:2/8\|0/1 30:2/4\|0/0 |
| range ≥ the 9 min before | 2/35 · 2/19 | 3/31 · 5/17 | |
| pause ≥ 6 min old | 6/35 · 5/19 | 12/31 · 8/17 | no |
| ≥ 1 three-min bar closed against the leg | 14/35 · 11/19 | 20/31 · 15/17 | |
| ≥ 2 three-min bars closed against | 5/35 · 4/19 | 7/31 · 7/17 | weak |
| before 10:00: coiling | 24/35 · 24/30 | | nothing before 10:00 |

[I] Coiling (a tight flag) is a continuation shape after 10:00 on 6 days; its absence says little. Bars against: weak.

## R2.5 k1 robustness

| Read (9-min OI change, leg side, strikes ahead) | +0 all (34 / 19) | +0, 27 Oct out (27 / 13) | +3, 27 Oct out (24 / 12) |
|---|---|---|---|
| **k1 loading ≥ +2L** | 14/34 · 2/19 | **12/27 · 2/13** | 10/24 · 2/12 |
| k2 loading ≥ +2L | 9/34 · 4/19 | 7/27 · 3/13 | 5/24 · 3/12 |
| k1..k3 summed loading ≥ +4L | 9/31 · 3/14 | 8/26 · 3/11 | 7/23 · 2/10 |
| k1 emptying ≤ −2L | 8/34 · 10/19 | 3/27 · 4/13 | 5/24 · 5/12 |
| k2 emptying ≤ −2L | 11/34 · 8/19 | 6/27 · 4/13 | 4/24 · 4/12 |
| **k1..k3 summed emptying ≤ −4L** | 8/31 · 6/14 | 4/26 · 4/11 | **6/23 · 7/10** |
| k1 emptying AND inside 1σ after a ≥ 1.5σ leg | 0/34 · 2/19 | 0/27 · 1/13 | 0 · 0 |
| k1 emptying AND 3-min delta against ≥ 150 | 1/34 · 3/19 | 1/27 · 0/13 | 0/24 · 1/12 |

[M] Loading is a k1 read (the first strike ahead), robust with 27 Oct out, on 6 days. Emptying is better read over the
band k1..k3 and one bar late (7/10 vs 6/23, 27 Oct out: 22 Oct 4/4, 26 Oct 2/2, 19 Oct 1/3) — thin (10 reversals).
The AND-combinations with 1σ / delta are too rare to use (0–3 cases).

## R2.6 Composites at the pause minute

**Pre-registered (as the brief listed it):** any 2 of {k1 emptying, inside 1σ after a ≥ 1.5σ leg, 3-min delta against
≥ 150, footprint against (clean), cross-index non-confirmation}.

| After 10:00 | +0 (35 / 19) | +3 (31 / 17) | +0 per day (CONT \| REV) |
|---|---|---|---|
| ≥ 2 items | 1/35 · 6/19 | 1/31 · 6/17 | 22:0/4\|1/5 23:0/1\|1/1 26:1/3\|0/2 27:0/7\|3/6 … |
| ≥ 3 items | 1/35 · 1/19 | 0/31 · 2/17 | |
| 0 items | 17/35 · 5/19 | **11/31 · 1/17** | |

Clean when it speaks, but it speaks at 6 of 19 reversals: "inside 1σ after 1.5σ" is 1/35 · 2/19 at the pause minute (a
leg that reached 1.5σ is rarely back inside 1σ one minute into its pause; round 1's 12/35 · 14/19 "inside 1σ" were legs
that never reached 1.5σ, i.e. ROTATION, already in S1), delta against ≥ 150 is 4/35 · 3/19, cross-index 1 · 1.

**POST-HOC composite (built after the tables above were read; a forward-test candidate, not a finding):** any of
{band ahead emptying (k1 ≤ −2L or k1..k3 ≤ −4L), ATM trend-side premium bleeding vs delta (x < −0.5 from the extreme),
footprint against (clean), 3-min delta against ≥ 150, inside 1σ after a ≥ 1.5σ leg}.

| After 10:00 | +0 (35 / 19) | +0, 27 Oct out (28 / 13) | +3 (31 / 17) | +3, 27 Oct out (25 / 12) |
|---|---|---|---|---|
| ≥ 2 items | 9/35 · 12/19 | 8/28 · 7/13 | 10/31 · 14/17 | 7/25 · 10/12 |
| **≥ 3 items** | 1/35 · 2/19 | 1/28 · 1/13 | **0/31 · 6/17** | 0/25 · 4/12 |
| **0 items** | **14/35 · 0/19** | 13/28 · 0/13 | 6/31 · 0/17 | 6/25 · 0/12 |
| 0 items AND k1 loading | 6/35 · 0/19 | 5/28 · 0/13 | 2/31 · 0/17 | 2/25 · 0/12 |

Per day, 0 items at +0: CONT 19:1/2 21:2/4 22:3/4 27:1/7 28:6/8 30:1/4 — REV 0 on every day.
Per reversal at +0 (items as [band, premium, footprint, delta, 1σ]): 12 of 19 have ≥ 2; the 7 with one item are 19 Oct
10:32 / 11:14, 22 Oct 10:05 / 12:25, 26 Oct 12:58 (premium only), 27 Oct 11:23 (band only), 28 Oct 10:26 (footprint
only).

[I] What this gives, honestly: a **clean HOLD** at the pause minute (no item at all: 14 of 35 continuations, 0 of 19
reversals, six days) and a **clean warning one bar later** (≥ 3 items: 0 of 31 continuations, 6 of 17 reversals). The
middle (≥ 2 at the pause minute) is a WATCH: 12 of 19 reversals, but 9 of 35 continuations with it. The reversal is
still not *called* at the pause minute; it is *watched* there and called at +3 or at 0.35.

## R2.7 The flicker fix

Rule [I]: PALAT? shows only once its raw condition has held 6 consecutive minutes or holds at a 3-min close; it then
latches while the condition holds; once shown it stays on screen ≥ 6 min (`min_show`); it is never carried stale past
that. Hold / watch keep round 1's 3-min hold.

| Day | word-class changes, old → new | 11:00–12:10 | HOLD ↔ PALAT? flips | lean-relevant changes (not TREND↔HOLD, not HOLD↔WATCH) |
|---|---|---|---|---|
| 19 Oct | 72 → 55 | 17 → 12 | 36 → 19 | 56 → 39 |
| 21 Oct | 59 → 49 | 11 → 11 | 27 → 15 | 33 → 21 |
| 22 Oct | 92 → 84 | 11 → 12 | 26 → 14 | 67 → 51 |
| 23 Oct | 70 → 60 | 10 → 6 | 34 → 18 | 54 → 40 |
| 26 Oct | 73 → 60 | 17 → 12 | 35 → 24 | 56 → 47 |
| 27 Oct | 89 → 79 | 8 → 9 | 28 → 20 | 65 → 54 |
| 28 Oct | 70 → 68 | 14 → 14 | 13 → 9 | 37 → 35 |
| 29 Oct | 55 → 43 | 7 → 8 | 30 → 18 | 35 → 21 |
| 30 Oct | 57 → 51 | 10 → 10 | 13 → 9 | 37 → 32 |

30 Oct 11:00–12:10: the 10 word changes are all `TREND ▲ running` ↔ `PAUSE ▲ · hold` (same lean, same side); lean-
relevant changes 0 → 0. The lean (▲ / ▼) itself changes only at PALAT, as in round 1.

**Cost [M]:** of the 16 after-10:00 reversals round 1 warned, the new rule warns 14; the 2 lost were one-minute flashes
(22 Oct 12:25, flip 12:52; 27 Oct 10:04, flip 10:08); delay on the 14: 17 minutes in all (ten at +0/+1, two +2, two +5).
**Saved [M]:** false PALAT? on continuations 14 → 8 of 35; HOLD ↔ PALAT? flips roughly halved on 8 of 9 days.
**Still too many:** 9–24 HOLD ↔ PALAT? flips a day. The remaining ones are the 0.35-retrace and delta-against items
toggling at successive 3-min closes on two-way days (22, 26, 27 Oct).

## R2.8 The two 30 Oct misses, re-read minute by minute (`nd/xi.py`)

**13:44 pullback low (leg ▼ 11:58 23,173f → 13:42 23,053f, 120 pts):**

| Minute | retrace | PE band below k1..k3 (9 min) | ATM PE premium vs delta from the low | marks against (▲) | post-hoc items |
|---|---|---|---|---|---|
| 13:43 | 0.19 | −7.9L | −3.5 Rs | — | 2 (band, premium) |
| 13:44 | 0.27 | −14.2L | −3.4 | — | 2 |
| 13:47 | 0.10 | −17.0L | +0.1 | — | 1 |
| 13:51 | 0.39 | −22.9L | −6.8 | E7 CVD ulta ▲ (bar 13:45, known 13:51) | **3** |
| 13:58 | 0.07 | −9.6L | −2.8 | E7 | 2 |
| 14:05 | 0.16 | −12.9L | −9.7 | E7 | 2 |
| 14:16 | 0.39 | −18.0L | −15.4 | E7, absorption, exhaustion ▲ | 2 |

The put band below was emptying and the PE premium bleeding from the first minute: the down-leg's sponsors were gone at
the low. Post-hoc composite: WATCH at 13:43, PALAT? (≥ 3) at 13:51 — 7 min after the low, 32 min before the flip at
14:23. Round 1's decoder said "hold ▼" until 14:20.

**10:19 low (leg ▼ 09:52 23,080f → 10:16 22,955f, 125 pts):**

| Minute | retrace | z | k1 22,900s PE (9 min) | marks against (▲) | items |
|---|---|---|---|---|---|
| 10:19 | 0.16 | 1.64 | −9.5L | — | 1 |
| 10:20 | 0.20 | 1.41 | −8.4L | — | 1 |
| 10:21 | 0.30 | 0.88 | −11.3L | absorption ▲ KHAREEDAR NE ROKA 22,955 (bar 10:15, known 10:21) | **3** |
| 10:24 | 0.08 | 1.93 | −3.1L | absorption | 2 |

At the low itself one item; at 10:21 three (k1 emptying, back inside 1σ, her absorption mark) — PALAT? 2 min after the
low, the same minute round 1 reached by its own route. Nothing on the record warns at 10:19 itself.

## R2.9 What survives into the design (§5 amended)

| Change | Rule | Evidence |
|---|---|---|
| **HOLD (clean)** | at the pause minute: no post-hoc item and k1 loading → `PAUSE ▲ · hold · clean` | 14/35 · 0/19 (6 days); with loading 6/35 · 0/19 |
| **WATCH** | ≥ 2 post-hoc items at the pause minute | 12/19 reversals, 9/35 continuations |
| **PALAT?** | ≥ 3 items, or round 1's 0.35 / FAST-against; confirmed at a 3-min close or after 6 min, latched, shown ≥ 6 min | ≥ 3 at +3: 0/31 · 6/17 |
| new alive items | `ATM CE bid +1.2 vs delta` (premium holding, +3), `coiling 0.4× the leg's last 9 min` | 10/27 · 2/16; 21/35 · 7/19 |
| new risk items | `PE band below emptying −14L / 9 min` (k1..k3), `ATM PE bleeding −3.4 vs delta`, her mark against (named, with its bar) | R2.5, R2.3, R2.1 |
| dropped | cross-index non-confirmation; "k1 emptying AND …" combinations; pause age; bars against as a word | R2.2, R2.5, R2.4 |
| kept, weight nil | footprint marks shown on the PAUSE line as they are (kind, side, bar), never a word alone | R2.1 |

The header gains one line under PAUSE:

```
OPTION   ATM 23,100s CE bid +1.2 vs delta since the pause · band ahead 23,100–23,200s CE +4.1L / 9 min · her mark: none
```

## R2.10 Score after round 2

| Piece | Round 1 | Round 2 | Why |
|---|---|---|---|
| the call leans and holds | 8 | 8 | unchanged: lean changes only at PALAT |
| pause vs reversal at the pause minute | 6 | **7** | a clean HOLD exists (14/35 · 0/19); the reversal is WATCHED (12/19) not called; 9/35 false watches |
| pause vs reversal one bar later | 7 | **8** | ≥ 3 items 0/31 · 6/17 on top of S2; premium holding 10/27 · 2/16 |
| in-lean flicker | — | **7** | HOLD↔PALAT? halved, lean-relevant changes down a third; 9–24 flips a day remain |
| her footprint marks | — | 5 | shown, not weighed |
| **overall** | **7.5** | **8** | |

**What still blocks a 9**
1. The post-hoc composite is built on 19 reversals over 8 days after reading the tables; it must run forward (every
   pause logged with its items and outcome) before its counts mean anything. Her pass bar is owed first (§5e).
2. At the pause minute the best honest word for a coming reversal is WATCH (12 of 19), with 9 false watches in 35. A
   9/10 needs the reversal *called* there; nothing measured does it (R2.1–R2.5).
3. Two-way days (22, 26, 27 Oct): the lean is still wrong for the first third of each reversal, and the remaining
   HOLD↔PALAT? flips live there.
4. 27 Oct (monthly expiry) breaks every OI read (band emptying on 6 of 6 reversals *and* 5 of 7 continuations); an
   expiry mode is a precondition.
5. Before 10:00 nothing separates (R2.1–R2.6 before-10:00 rows: coiling 24/35 · 24/30, composite 0: 22/35 · 17/30).
6. Marks' first-seen time is not recorded; "bar close + 1 min" is an assumption, and 6 of 30 Oct's marks were appended
   late. A first-seen stamp in `ofd_marks2` would make R2.1 testable properly.
7. SENSEX / BANKNIFTY untested; 30 Oct's 78 blind minutes still blind.

---
---

# Merged decision (coordinator, 30 Oct 17:00, after checking both rounds)

**Checked [M]:**
- Rounds 1 and 2 reproduce from the scripts: `counts.py`, `comp2.py` (≥ 3 items at +3: 0/31 · 6/17) and `flicker.py`.
- The event labels are causal: the leg is tracked on minutes ≤ i, and the outcome is read only after.
- k1 = the first CE strike above spot in an up-leg (PE at or below spot in a down-leg), 9-min OI change.
- k1 loading is the read I got wrong live at 11:14 on 30 Oct: calls +10.6L at 23,000–23,150 in a pause, then +118.

**Not a finding yet:** the round-2 composite (clean HOLD 14/35 · 0/19; ≥ 3 items 0/31 · 6/17) was built after reading
the tables. It ships as a display read with a forward log, not as a verdict (house rule 4 / §5e: her pass bar first).

| # | What | Decision | Why |
|---|---|---|---|
| 0 | P0 from the day review: BLIND live + rebuild the lost minutes from the Upstox tape | **build first** | every read below is wrong on stale or missing minutes; 30 Oct lost 78 |
| 1 | The LEG object: lean = the leg's direction; changes only at PALAT (½ the leg, floored at 1U); TREND needs, after 10:00, ≥ 80 pts and (≥ 1.5σ, or a TOOT, or fuelled); before 10:00, ≥ 100 pts + TOOT, else OPENING / ROTATION | **build** | 0 lean flips in 30 Oct's 11:00–12:10 leg and all of 29 Oct (Jarvis: 8 and 0-but-NO-TRADE); 23/35 vs 6/19 |
| 2 | PAUSE words: HOLD (no risk item; "clean" + k1 loading named) · WATCH (≥ 2 risk items) · PALAT? (≥ 3 items, or 0.35 retrace, or FAST against; confirmed at a 3-min close or 6 min, latched, shown ≥ 6 min) | **build** | clean HOLD 14/35 · 0/19; ≥ 3 at +3 0/31 · 6/17; flicker halved |
| 3 | Items on screen, each with its number: alive = k1 loading, shallow, coiling, ATM premium holding vs delta, push with; risk = band ahead emptying (k1..k3), premium bleeding vs delta, 3-min delta against ≥ 150, FAST against, inside 1σ after a ≥ 1.5σ leg, her footprint mark against (named, with its bar) | **build** | §2, R2.3–R2.5; nothing hidden |
| 4 | Writers ±7 and Sides at a pause tagged "(lagging)"; they still name the LEG's fuel | **build** | with the leg at 17 of 19 reversals |
| 5 | DAY line: leg flips so far + the 30-min fut-OI quadrant (fresh longs / fresh shorts / short covering / long unwinding, lots) | **build** | names every day's spine (S7); flips = two-way warning (S8) |
| 6 | RISK retired as a word (its spike is one risk item); NAHI stays "no answer", read with the leg state | **build** | §4.3, §4.4 |
| 7 | The fight anchored to the leg (re-anchored at PALAT or 2 steps past for 15 min) | **build** | 29 Oct 315 of 361 min > 2 steps away |
| 8 | Forward log: every pause, its items, its word, its outcome at 45 min → `data/jarvis/pause_<day>.jsonl`; evening review | **build** | the only way the composite earns trust |
| 9 | Expiry mode (G9), SENSEX flow (G13), BANKNIFTY (G14), a first-seen stamp on her footprint marks (extension) | **precondition / owed** | 27 Oct breaks every OI read; marks untestable without the stamp |
| — | Dropped: cross-index non-confirmation, absorption as a word, "NAHI + fuel = absorbing", "RISK needs a move" | **drop** | R2.2, §4.2–§4.4 |

**Honest score [I]:**
- **On this record: 8 / 10.**
- **What decides 9:**
  - the forward log shows the clean HOLD and the ≥ 3-item warning holding up on new days (her pass bar);
  - the reversal gets *called* at the pause minute, not one bar later. Nothing measured does that yet.
- **Two-way days stay the weak spot.** On those, the DAY line's "legs given back at half today: take at the band" is the
  honest help.
