# The pro tool: a blueprint (Opus)

**Written:** 2026-09-28, after the close. Design and replay only. No code, data or server was touched. Nothing was posted, tested or started.
**The chair:** 20 years in NIFTY/SENSEX options, building this for my own son.
**Read first:**
- the redesign set A–H, including `H-reader-spec-v3.md` and `H-changes-v3.md`;
- `TRADER-AUDIT` (its CORRECTION first), `PONYTAIL-REVIEW`, `BUGFIX-2026-09-28`;
- her doctrine files.

Fable's blueprint in this folder was deliberately **not** read, so the two designs stay independent.

**My replay:** `scratchpad/pro1/reader_pro.py` and `run.py`.
- It is H's `reader6.py` with the rules below added. The unchanged mode reproduces every v3 exit in H §11.2 exactly.
- It covers 8 trades on all five recorded days with a book (22, 23, 24, 25 and 28 Sep), read-only.

**Tags:** [M] measured, [I] inferred, (h) hand-picked.

---

## 0. The decisions, in one page

1. **Two kinds of exit, never mixed up.**
   - **The trade is wrong:** price was *accepted* beyond the level I was playing for. This is a stop. It is not negotiable and it does not wait for OI.
   - **The trade is done:** it reached the wall ahead and that wall is holding. This is where a pro banks, and it is a read, not a command.

   Today's v3 treats both as one mechanical trigger, flow AND OI. That is how her pre-registered call went −61% with no fold. Her question, "will he fold exactly on one condition?", has the answer **no**. He asks two different questions at two different places.

2. **A winner earns more benefit of the doubt than a loser.**
   - **Loser mode:** while her give-up price is still on the losing side of her entry, price acceptance alone says OUT.
   - **Winner mode:** once the give-up has trailed past her entry, it takes her own rule to fold her: flow accepted past the give-up **and** the writers defending her coming off their peak. Two things must break, not one.
   - **The backstop:** a winner that is accepted back through her entry is OUT. A winner never becomes a loser.

   This is the pro's asymmetry. It is also her brief: help her HOLD winners, and never let the tool sit on a loser.

3. **OI tells me *where* the level is and *who* is defending it. Price tells me whether the defence held.** OI alone never exits. I tested an "OI off-peak + a fight lost near the level" early exit: it took the 24 Sep trend out at +3% instead of +81%. Rejected.
4. **BANK ZONE is new.** It shows when the trade reaches the next wall ahead (top-2 OI near ATM, her own reading rule) and that wall shows it is holding.
   - Evidence of holding: tiring, a failed extreme, or the other side winning a fight there.
   - On her own put today it printed at +28%, +48% and **+90% at 14:38:42**, five seconds before the day's best print (+97%).
   - It is a read with one soft tone. It never states a size.
5. **One engine, `fold.py`, one record, two faces.** The Validate tab and the GoCharting panel show the same word, from the same event log, which survives a restart.
6. **No GO on entry.** The entry screen shows *what the engine would say if you were in now*, the give-up (the risk) and the wall ahead (the room). She pulls the trigger.
7. **Fourteen tabs become six.** Every screen maps to a moment in the trader's day, or it goes.
8. **One amendment, "PRO-1", signed once.** It replaces the candle-close line, the latch, trend-as-a-fold and GO/WAIT/NO, and it forward-logs every word so each can be scored.

---

## 1. The trader's day, and the screen for each moment

| moment | what a pro needs, in one glance | screen |
|---|---|---|
| **Pre-open, 09:00–09:15** | The contract (expiry, roll day?). Yesterday's high/low/close *for this contract*. The walls carried in: top-2 CE and top-2 PE by OI near ATM, from yesterday's last snapshot, same expiry. What day it is: expiry, the day before, or a roll day. | **Board**, top strip |
| **The open, 09:15–09:30** | Who the gap trapped: in-the-money writers covering against *yesterday's close*, not the 09:15 candle. The first fights at the gap edge. The zone's 09:25 anchor (kept). | **Board** + the panel |
| **Flat** | The next fight above and below, and what would confirm each. | **Board** "NEXT FIGHT" line + the panel |
| **Entering** | Location (at a level, not in the middle); flow at that level; the wall behind building; room against risk; the give-up price. | **Validate** (check) + the panel's mark control |
| **In a trade** | One word; her four chips; the give-up; premium now, at the give-up and at the wall ahead; the one fact behind the word. | **Validate** + the panel, identical |
| **Exiting** | OUT with its reason, or BANK ZONE with its wall. | Both, one sound class each |
| **After a trade** | The trade's word history; whether a re-entry read exists (a stop run that failed). | The panel's detail; **Record** |
| **End of day** | Her trades, the engine's words, trigger_log rows, falsifier counts (counts, never rates); tomorrow's flags (expiry, roll). | **Record** |

**Six screens:** Board · Validate · War (OI drill-down) · Trade (chart, kept by her order) · Record · the GoCharting panel.

**Cut:**

| tab | why |
|---|---|
| **Glass** (`one/`) | A trial since 08-11 with no verdict; Board rev 3 replaced it. |
| **Heat** ("Live Spike Radar") | Moves constantly and changes no decision: a slot machine. |
| **Tape** | Already called a fossil in the 09-19 spec. |
| **Flow** | A time-axis price line. Her flow is the footprint on GoCharting; the fights live in Validate's detail. |
| **VPIN** | She ordered it (09-23). Its read moves to the VPIN chip and row on every screen, so the tab adds a second place to look for the same thing. The server route stays. |
| **Chain** | PCR, max pain, GEX: aggregate OI. Her reading rule says near-ATM top-two only. |
| **OI Flow**, **Map** | Duplicates of Board/War. |
| **Events** | The engine's event stream is dead as a signal (−0.1 against a +4.1 do-nothing control). |
| **Signals** | Becomes **Record**: the same trigger_log view, plus her marked trades and the fold log. |

Also: `App.tsx`'s mock first paint (L79–388) goes. Invented prices on first render are a lie.

---

## 2. The exit and the hold, as a pro makes it

### 2.1 What I check before I change my mind

In this order, every time price moves against me:

1. **Where is price against my give-up?** Short of it, this is a pullback until proven otherwise.
2. **Was it *accepted* there?** Business traded beyond it for a normal stretch of time, or a poke that came straight back? Stop runs poke; real moves accept.
3. **Who is winning at the level:** initiative (price follows the aggressor) or absorption (price doesn't)? A loss of the level by absorption failing is real. A spike into a wall that absorbs it is a gift.
4. **Did the side defending me give up *after* I entered?** Is the wall behind me off its peak by more than its own noise, or still building?
5. **Is the wall ahead loading or covering?** Loading shrinks my room. Covering is my fuel.
6. **VPIN:** is informed flow one-sided against me? It sharpens attention. On its own it is not a reason.
7. **Is the move tiring, or did an extreme fail?** A failed extreme *my* way at the wall ahead is where I bank. A failed extreme *against* me is a gift.
8. **What have I already given back?** Premium now, at the give-up, and my peak.
9. **The clock:** expiry gamma after 13:30 on a Tuesday; her 15:00 practice.

**What never moves me:**
- a candle close;
- a trend box;
- a quiet clock;
- her S1–S4 lines;
- OI off-peak with price still holding my level;
- a single minute of anything.

### 2.2 The engine (`fold.py`, one pure module, stdlib, no I/O)

Units, all the session's own (H §3):
- **bucket** = 3 × the median 1-min volume, pooled over up to 5 prior sessions *of the same contract*;
- **B** = today's median 1-min range; **θ = 2B** (a full swing); **w = B/2** (the noise unit);
- **F\*** = the options' forward: future − the 15-min median of (future − (K + C − P)).

**Kept from v3, unchanged:**
- fights (R1);
- levels (R2), traps (R3);
- the **give-up G**:
  - seeded at the mark from the newest fight before entry, else the defending wall + w;
  - re-set on each win by her side;
  - locked once touched, so it tightens but never loosens;
- **W**, the wall that sets G: the most OI between F and G, chosen only when G is set;
- the **OI event**: a drop ≥ 3·σ·√n from the peak since reference, where σ is that strike's own robust one-update noise, withdrawn when W rebuilds above that peak;
- **acceptance**: one bucket of lots traded at or beyond G, over at least the session's median bucket time, reset by a print w back inside;
- FAILED needing ≥ w; TIRING 2 in / 2 out;
- chips confirmed on 2 bucket closes (condition-born only).

**Changed and added (PRO-1):**

| rule | exact form | why it is scale-free |
|---|---|---|
| **Mode** | `winner` if G is on the profit side of her entry future price (d·(G − E) > 0), else `loser`. Re-evaluated whenever G changes. | a sign, no number |
| **OUT, loser mode** | acceptance beyond G | own volume and own time |
| **OUT, winner mode** | acceptance beyond G **and** a live OI event on W, in the same epoch (her sentence) | as above + the strike's own noise |
| **OUT, backstop** | in winner mode, acceptance beyond E ∓ w (her entry, by the noise unit) | own clock, w |
| **PAST GIVE-UP** | winner mode, G accepted, W still holding. Amber, no sound. The row says "out if 22900 CE writers leave, or if price is accepted through your entry 22941". | no new threshold |
| **The wall ahead, A** | the top-2 ahead-side strikes by OI among the 19 nearest F\* (her rule: near ATM, the most and the second most), placed at K + basis, at least w beyond her entry | her OI rule; NEAR = 9, as the audit kept |
| **REACHED** | a bucket's VWAP is within w of A or beyond it | w |
| **BANK ZONE** | after REACHED and still less than θ past A: the trade is in profit, and the wall shows it is holding (TIRING, a FAILED extreme, or the other side wins a fight after the reach). Once per wall. | existing events, θ |
| **WALL BROKE** | a bucket's VWAP is ≥ θ past A. The broken wall becomes her level: G tightens to A ∓ θ (never loosens). The row reads "22850 PE floor broke 14:18: now your roof". | θ |
| **Premium at G and at A** | P + Δ·x + ½Γ·x² from the chain's own greeks [I]. The linear form under-states the give-back on expiry gamma; on 22 Sep it read +113% where the fill was +77%. | chain greeks |
| **Peak** | her best premium since entry, with its time [M] | a fact, not a trigger |

**Dropped from v3:** the `FOLD_NEEDS` switch. The trade's state picks the mode, so there is nothing for her to flip.

### 2.3 The words (one per moment; precedence top-down)

| word | look | sound | moved by |
|---|---|---|---|
| **OUT · level lost 22925** | ink block | two low tones, once per epoch | loser mode: acceptance beyond G |
| **OUT · gave up: 22900 CE writers left 11:42** | ink block | same | winner mode: acceptance + W's OI event |
| **OUT · back through your entry** | ink block | same | winner-mode backstop |
| **PAST GIVE-UP** | amber | none | winner mode: G accepted, W not off |
| **BANK ZONE · 22800 PE floor holding** | ink outline, amber fill | one soft high tone, once per wall | reached A + a holding event, in profit |
| **FAILED LOW / HIGH** | amber, ink border | none | H §7.1 |
| **PULLBACK · since 12:28** | amber tint | none | the other side won the newest fight; price still her side of G |
| **TIRING · 23 min** | amber tint | none | 2 stalled bucket closes |
| **BEHIND YOU** | ink | none | her side won the newest fight |
| **NO READ** | grey | none | no fight and no wall yet |

- **After OUT,** the word stays OUT until she presses I'M OUT or unmarks. Then she is flat.
- **RE-ENTRY READ:** if trading comes back w inside G and her side then wins a fight within the same session, the flat screen says "stop run failed at 22925: sellers won again 12:35".
  - With free execution, re-entry costs her the spread.
  - A missed exit cost −61% today.

### 2.4 Pullback or invalidation: how the screen says it

| | PULLBACK (hold) | INVALIDATION (OUT) |
|---|---|---|
| **Price** | short of G, or past it and not accepted | accepted beyond G |
| **Flow at the level** | the other side won a fight, but the level held (absorbed), or they are tiring | initiative through, and it stayed |
| **The wall behind** | building or at peak (OI chip WITH/QUIET) | off its peak by more than its own noise (winner mode needs this) |
| **The row prints** | "pullback: sellers still defend 22925; 22900 CE 240.0L, high 11:41" | "22925 accepted: 270 lots over 5 min, 22900 CE off 240.0 → 235.9L at 11:42" |

### 2.5 The replay: 8 trades, 5 days

**The pre-registered trades** are G's rule (first failed high → put, first held low → call, 09:30–13:30, ATM on F\*), plus the same rule on 28 Sep. **Hindsight:** 24 Sep. **Hers:** today. Scored to 15:00, her practice. P&L is % of entry premium.

| trade | best | v3 (flow + OI always) | flow alone | **PRO-1** (mode at exit) | BANK ZONEs before exit |
|---|---|---|---|---|---|
| 22 Sep put, 23450 PE @ 47.75 (expiry) | +264 at 14:00 | +77, 14:19 | +68, 11:28 (whipsaw) | **+77, 14:19** (winner) | 11:20 +82 · 12:01 +132 · **13:54 +221** |
| 22 Sep call, 23350 CE @ 43.65 | +78 (after −61) | −42 | −42 | **−42** (loser) | none |
| 23 Sep put, 23450 PE @ 122.3 | +3 | −12 | −12 | **−12** (loser) | none |
| 25 Sep put, 23150 PE @ 111.6 | +42 | +7 (whipsaw) | +13 | **+7** (winner; whipsaw by the 20-min test) | 09:47 +26 |
| 25 Sep call, 23150 CE @ 96.5 | +53 (after −29) | −19 | −10 (whipsaw) | **−10** (loser; whipsaw) | none |
| **28 Sep call, 22950 CE @ 84.05** | 0 | **none: −61 at 15:00** | −17 | **−17, 10:16** (loser) | none |
| 24 Sep put (hindsight) @ 102.65 | +154 at 13:59 | +81 | +116 (withdrawn 8 s later) | **+81, 14:55** (winner) | 12:32 +37 |
| **28 Sep put, hers**, 23000 PE @ 120.4 | +97 at 14:38:47 | none, +71 at 15:00 | none | **none, +71 at 15:00** | 09:45 +28 · 11:57 +48 · **14:38:42 +90** |
| *sum of exits* | | +102 | +187 | **+155** | |

**What it shows [M]:**
- **Holds winners through pullbacks.**
  - Her put held through the 12:29 push to 22907. Words there: PULLBACK, give-up 22925 untouched.
  - The 22 Sep put held through an 11:28 acceptance, as PAST GIVE-UP, because the writers stayed. It then ran to +264%.
  - 24 Sep held through two acceptances (14:03 and 14:37) until the writers left at 14:55.
- **Cuts losers at the level.** The −61% call exits at −17%. All four losers exit at their level (−42, −12, −10, −17), no worse than v3 and 44 points better on today's call.
- **It still hands back most of one winner.** On 22 Sep it exits at +77% of a +264% move.
  - The drop from 23347 to 23286 (13:50–14:00) was a sweep with no fixed fight, so G stayed 100 pts away at 23385.
  - The rally from 23286 to 23399 then took 15 minutes on expiry gamma.
  - BANK ZONE at +221% (13:54) was the pro's exit, and the screen then read "PE 153 (+221%) · at give-up ≈ 102".
  - **Known ceiling:** a structure trail cannot catch a 15-minute V on expiry gamma. The bank read and the give-back line are the protection, and she decides.
- **Tried and rejected, on the same run:**

  | variant | result |
  |---|---|
  | OI + a lost fight near G as an early exit | 24 Sep at +3% |
  | tighten a full swing from the best after the first bank | today's put out at +19%; 2.9 sounds/h |
  | WALL BROKE tightening | changed no exit in 8 trades. Kept, flagged: it exists for sweeps with no fixed fight. |
- **Noise:**
  - OUT sounds 0–0.37 an hour;
  - BANK ZONE at most 3 a day (22 Sep, today);
  - words 0.4–4.6 an hour, **8.0 on the 24 Sep trend** (PULLBACK/BEHIND alternation, as in v3).

- **Honesty:** n = 8. This is how each rule fails, not a ranking. Flow alone summed higher, and this sample cannot tell whether that is luck. I chose PRO-1 because it matches her rule for winners and a stop for losers, and every choice is logged forward (§9).

### 2.6 Trailing, banking and the clock

- **Trail:** G moves only when her side wins a fight, or a wall ahead breaks by θ. It never loosens once touched. **No time trail, no premium trail:** premium is shown, never an input, as rev 5 kept.
- **Bank:** BANK ZONE names the wall and the evidence. The line under it says "pros bank into walls that hold; the give-up for the rest stays 22831". **Never a fraction.**
- **Expiry day:**
  - the header shows **EXPIRY · Γ** after 13:30;
  - the premium-at-G uses Δ + ½Γ;
  - the OI event runs on the expiring series against its own closing pace. That is H §8, post hoc, flagged.
- **15:00:** from 14:45 the header shows "flat by 15:00 (your practice)". After 15:00 the entry check says "after 15:00: your practice is no new trades". Display only, never a rule.

---

## 3. Entry

### 3.1 What a pro checks

1. **Location:** at a level where a fight happened (held, won, or a trapped shelf), not in the middle. The POC is a magnet: "no edge in the middle".
2. **Flow at that level:** her side won the newest fixed fight there, by initiative or by the other side being absorbed.
3. **The wall behind:** building or at its peak, not off it.
4. **The wall ahead:** is it loading faster than the one behind (room shrinking), or covering (fuel)?
5. **VPIN:** not one-sided against her.
6. **Room against risk:** points and premium to A (the bank zone) and to G (the stop).
7. **The clock:** expiry gamma, 15:00.
8. **What falsifies it:** G, printed before she enters.

### 3.2 How the tool says it: no GO

**The big word is the engine's word for a hypothetical mark at this second,** so she sees before entry exactly what she will see after:

```
IF YOU WERE IN · long 23000 PE   BEHIND YOU     ZONE▪ FLOW▪ OI▪ VPIN▫
give-up 22925 · 18 pts · ≈ 150 (−14%)      wall ahead 22850 PE · 39 pts · ≈ 178 (+20%)
sellers won 11:04 at 22879 (369 v 42) · 22900 CE building, high 11:41
```

**Three refusals** print as an amber clause, not a big NO:
- "you would enter past your give-up" (PAST GIVE-UP at entry);
- "you would be entering *at* the wall ahead: where pros bank, not enter" (BANK ZONE at entry);
- "after 15:00".

**No ratio, no score, no count of chips.**

**Why no GO:** the audit showed the GO/WAIT/NO word being decided by inputs she does not use (the line, the trend), and it said WAIT through her best entry.
- A word that tells her *what the market is doing at this level* can't be wrong in that way.
- A GO invites the son to stop reading.

**The expression** (EXPRESSION rev e, moved to every minute, ATM on F\*, her strike when she names one):
- **BUY the direction** when room to A ≥ the distance to G, and the wall ahead is not building faster than the one behind.
- **SELL the other side** (ATM/ITM, her practice) when the market is boxed (price between two held levels less than 2θ apart), or A is within G's distance, or TIRING is live.

  The box pays the seller and taxes the buyer. One line, with its reason. Counts, never odds.

---

## 4. Flat: the next fight

**Line one** (Board and panel):
- "NEXT FIGHT · above 22907 · below 22852";
- within w of a level: "AT 22888 · buyers held 13:26".

**Under each fight, the confirmation that turns it into a trade,** in C §4's form:
- **Above:** "sellers give up when lifts at 22905–22910 are followed by price **and** 22900 CE comes off its peak". That means calls.
- **Below:** "buyers give up when hits at 22860 are followed by price **and** 22850 PE comes off its peak". That means puts.

When both halves fire, the flat word becomes **"SELLERS GAVE UP AT 22907 · 11:42"**: an event, frozen, with no sound. It is the entry read, and she presses Mark if she takes it.

**The re-entry read** (§2.3) lives here after an OUT.

---

## 5. The faces

### 5.1 The GoCharting panel: 400 px, fixed frame, LIGHT

```
NIFTY OCT FUT · 11:42 · contract ✓ · chart placed            │ header (EXPIRY · Γ, 15:00 when due)
long 23000 PE · 120.4 · 09:30                 [ I'M OUT ]     │ position (or the Mark control)
BEHIND YOU                    ZONE▪  FLOW▪  OI▫  VPIN▫        │ line 1: word + her four chips
give-up 22925 · set 11:05 · winner: needs flow + OI           │ line 2: frozen give-up + mode
PE 175.5 +46% · peak 184 11:16 · at give-up ≈ 150 +25%        │ line 3: premium [I]
ahead 22850 PE floor · 29 pts · ≈ 200                         │ line 4: the wall ahead / BANK ZONE
FLOW  sellers won 11:04 at 22879 (369 v 42)                   │ four rows, one sentence each,
OI    22900 CE writers building, high 11:41                   │ one grey tag per row
VPIN  4 of 10 buckets one-sided, 3 sell                       │
ZONE  behind you: the 22900–22907 lid (7 pushes absorbed)     │
▸ detail                                                      │
```

**Budgets:**

| | budget |
|---|---|
| **Numbers** | ≤ 24 with detail closed |
| **Colours** | 5: blue buyers, red sellers, amber, ink, grey. Chips carry no colour for side in a trade: WITH means her side. |
| **Sounds** | 2 classes: OUT (two low tones, once per epoch, ever; ids kept, so a reload is silent) and BANK ZONE (one soft tone, once per wall) |
| **Chip changes** | ≤ 6 an hour. This is an acceptance gate; v3 met it on 4 of 8, and ZONE is the offender. |
| **Word changes** | ≤ 4 an hour |

**No flicker:**
- words are computed once per event batch;
- chips change on events or after 2 bucket closes;
- **the DOM is patched, never rebuilt** (`panel.js:515`'s `innerHTML` rebuild kills `<details>` and tooltips, B §2.9).

**Anytime:**
- the panel GETs `/api/hold/trades` through `sw.js` before its first frame;
- TapeMap down reads "your trade: could not check — TapeMap not reachable", never FLAT.

### 5.2 Mark my trade (both screens, one record)

This is F-face §6 with G's flaw fixed:
- **The control:** Mark trade → CE/PE → MARK: three clicks.
- **Strike and premium:**
  - the strike is prefilled ATM **against F\***, with ◂ ▸ steps labelled ATM / ITM 1 / OTM 1;
  - **the entry premium is frozen from the snapshot at the moment the row opens**;
  - she can type her fill.
- **The wire:**
  - the panel posts through the service worker to `/api/hold/trades` (`server._hold_trade` already validates the fields);
  - Validate's "I'm in" posts the same op;
  - the record persists in `data/day_state/` (`_load_day_state`).
- **Build gate:** one test that `Sec-Fetch-Site: none` reaches the server from `sw.js` before anything relies on it. Fallback: allow exactly `Origin: chrome-extension://<id>` from config.

### 5.3 Chart marks: placed once, zoom-proof

**Every mark comes from TapeMap's event log with a frozen (time, price).** The extension never re-detects or re-places a mark; `fit` only maps (t, p) to pixels.

**Seven glyph kinds:**

| glyph | meaning |
|---|---|
| ▲▼ filled | fight won (book) |
| ▲▼ with a white dot | won by price [I] |
| ▬ | absorbed, level held |
| hatched grey ▬ | disputed |
| ⌃⌄ amber | failed extreme |
| ▸ ink | her entry |
| ■ ink | OUT |
| ◆ ink outline | BANK ZONE, on the wall line |

**Lines:**
- the give-up as a dashed ink staircase: it steps only on a new G, older steps at 55%;
- the wall ahead and the wall behind as dotted lines, with a strike chip in one frame: "22850 PE", placed at K + basis.

**Cut from the chart:**
- ROUND lines;
- the flat σ-band pocket fill (GoCharting draws her study);
- the event strip;
- the forming-bar outline;
- per-strike "pain" chips;
- trap/release discs. Trapped shelves appear only as a level chip.

**Zoom:**
- one 12 px floor; below it a glyph collapses to a 3 px tick and never vanishes;
- stamps only on the newest 3 events.

**Trust:**
- **fit.js may only fit TapeMap's session day** (`frame.day`). The "no date tick → every day is a candidate" path (`fit.js:194–203`) is the session-jump bug: Friday explains 12:30 and wins.
- **Contract match:** GoCharting's bar OI must equal TapeMap's future OI.
- **Hysteresis:** pause after 2 failed fits, resume after 2 good.
- **Paused marks** show one tag: "chart shows another day / contract since hh:mm; the panel is still live".

### 5.4 The Validate tab

**The same five lines and four rows as the panel,** at 2× size, with room for:
- the **check slip** (left, unchanged keys C/P B/S ↑↓ Enter);
- **detail open by default:**
  - the give-up staircase as a list;
  - every OI event with z and σ;
  - acceptance tallies;
  - the chip history;
  - the whole day's words for this trade.

**Removed from it:** everything in §6.1 that renders here, plus "(buffer 0 until the candle is read)" and, once PRO-1 is signed, the DRAFT stamp.

---

## 6. Remove, and add

### 6.1 Rules and fields that go (all inside PRO-1)

| what | where | why |
|---|---|---|
| The session-high line with a 3-min close; noise B | `hold.py:221–370, 142–149` | A candle close. She banned it. |
| Trend as a fold family, and as WATCH | `hold.py:485–506`; expression REGIME | Not one of her four. |
| The quiet clock | `hold.py:478–498` | A time rule, not a market read. |
| The FOLD latch and "heal"; PERSIST = 3 | `hold.py:518–541, 620–630, 47` | Her rule is present tense. |
| The 15-mark OI warm-up; the 4-closed-bar flow warm-up | `fronts.py:49`, `grounds.py:50` | Everything reads from 09:15. |
| GO/WAIT/NO | VALIDATE rev 2 | §3. |
| The 3-min expression cadence; ATM on spot | `expression.py:57, 80–94` | Every minute, on F\*. |
| GATE chip (always PATA NAHI), ballot outside a visit, `setup.confirm`, `trapped.gear`, `aggressor.rank` | `gate.py:59`, `frame.py` | They can never fill. |
| Panel: WATCHED LEVELS, TAPE AT THE EDGE, breadth, DOWN/PIN tells, candle WRONG IF, "chain not wired" | `panel.js`, `frame.py` | B §1. |
| The dark panel theme | `panel.js:11` | Light only. |
| The SMC layer; trap=CLEAR compression dimming | tape core | Dead; the second is actively harmful. |
| **Five different "wall" rules** | fade gate, hold/board, board headline, plan rung, expression | **One rule:** near-ATM top-2 by OI, beyond F\* by w, with 2-close hysteresis (H §4). `fronts.py` owns it. |

**Also:**
- whatever of the ponytail §2 list today's cleanup did not already delete;
- its §3 items 6 (Glass), 7 (dark mode), 8 (`ui/console.html`) and 9 (the HANDOFF diary).

**Kept by her order:**
- the Dhan/Upstox fallback;
- `structure.py`, `band_rotation.py`'s two-leg stack, `contract_pair.py`;
- the Trade tab's chart (and `vendor/candl`, which it uses);
- PaperDesk's routes;
- the zone's 09:25 anchor.

### 6.2 What a pro demands that is missing (each ships in shadow first: logged, gating nothing)

1. **Resting liquidity at the lid** [M]. This is Bookmap's best give-up tell, from the depth TapeMap already records (`book_NIFTY`). It prints in the FLOW row only when price is within θ of G or A: "offers at 22905–22910: 1.2k lots, 60% pulled in 2 min".
2. **Big prints** [M size, I side]. A single fill ≥ ⅓ bucket, at a level, named in the FLOW row.
3. **The persisted event log,** `data/fold/fold_<day>.jsonl`. A restart replays it; it never recomputes.
4. **Next-weekly chain on expiry day.** Tomorrow's walls are next week's writers.
5. **SENSEX policy:** "OI + price" mode. FLOW reads CAN'T CHECK ("SENSEX future: median 10 lots a bar"). G = the defending wall + w. Acceptance is price beyond G for the NIFTY-derived median bucket time, labelled. BANKNIFTY is off the default screens.
6. **The re-entry read** (§2.3) and **peak premium** (§2.2).

---

## 7. Data truth

| defect | effect | handling |
|---|---|---|
| **Spot vs forward:** the chain's spot runs 33–49 pts under the options' forward | every ATM, ITM and wall off by a strike | All moneyness on F\*. "ATM" within w. Spot is never used. `board.itm`, `board.nearer`, the plan rung, hold ITM/OTM and the expression ATM all move to F\*. |
| **Guessed-side volume, 24–59%** (`ladder.py:126` books hidden volume on the primary side) | a false side | A side counts only when \|b−s\| > the bucket's guessed volume and imbalance ≥ ½. Otherwise "two-sided". Sweeps are signed by price ≥ θ, tagged "by price [I]". The side word is the [I] part and carries the tag. |
| **Three tapes disagree** (ladder / GoCharting 5-min / VPIN tick rule; 58–63% agreement) | 09:56 was called three ways | **VPIN is rebuilt from the ladder's fills,** one classifier. GoCharting is a dispute check only: a disputed fight is hatched and waits for price. The day's agreement % is printed in Record. |
| **The book starts at 09:17** (1,639 lots unseen today) | a blind open | Subscribe book and chain before 09:15, centred on the future or yesterday's close. Until then FLOW reads "could not check: book from 09:17". |
| **OI baseline is the 09:15 candle** | the gap's covering is hidden | Baseline = yesterday's last snapshot, **same expiry only**, else the 09:15 candle, said so. A missing baseline is null, never 0. |
| **Validate rows 2 min late** (REST 1-min candle) | late words | A tick-built minute, reconciled with REST later, tagged. |
| **The futures roll** (Sep expires 09-29; Oct from 09-30) | dead contract; buckets and prior levels from the wrong contract; a chart that rolled early | The expired-future filter is done (BUGFIX #6). Then: a contract stamp on every row (ux, vpin, book, chain); bucket and B pooled only from the same contract, else its first 15 min, flagged; PDH/PDL/PDC fetched for the new contract by REST at 09:00; the chart contract match (§5.3); the futures-OI "longs exiting" read blinded in expiry week (it is the roll). |
| **fit.js session jump** | every mark vanishes or lands on Friday | Single-day candidates from `frame.day`; "chart shows another day" tag (§5.3). |
| **VPIN first buckets / backfill candle-signed** | fake early toxicity | VPIN reads CAN'T CHECK until 10 live buckets; backfilled buckets are tagged and never counted. |
| **Chain snapshot staleness** | a wrong premium-at-G | Older than 60 s reads "premium: could not check — chain 70 s old". |
| **Restart** | recomputed history | The event log replays; thresholds are causal; the trade comes back from `day_state`. |

---

## 8. Build order: each phase shippable, each after the close, restart by her, commit on her word

**Phase 0: before Wednesday's open (roll day). Plumbing only, no method change.**

| item | what |
|---|---|
| a | The `fit.js` single-day fix and the contract match (extension). |
| b | The panel to LIGHT tokens, and patch-not-rebuild (extension). |
| c | Contract stamps on every recorded row. |
| d | Yesterday-close OI baseline, same expiry. |

- **Test:** `node` on the fit fixture; the `test_upstox_instruments` roll test (exists); one new `test_day_state` restart test.
- **What goes live first:** these four, because Wednesday's roll breaks the chart and the reads without them.

**Phase 1: `fold.py` in shadow, plus the event log.**
- `fold.py` is written as PRO-1 §2, pure, with one `__main__` self-check against the 28 Sep fixture: her put reads no OUT, and the 28 Sep call reads OUT at 10:16.
- `server.py` calls it for every marked trade and appends to `data/fold/fold_<day>.jsonl`. It stays **invisible** except for one grey line in Validate's detail: "shadow · PRO-1 says: PULLBACK".
- hold.py keeps running, as signed.
- **Acceptance:** `reader_pro.py` run on every recorded day passes G's gates:
  - no OUT on arrival;
  - ≤ 1 sound an hour;
  - ≤ 6 chip changes an hour;
  - every exit printed against the best.

  A mid-session restart must replay the identical words.
- She reads the PRO-1 amendment and signs, or doesn't.

**Phase 2: after her signature. The faces.**
- Validate's hold section switches to `fold.read`; hold.py's removed rules go in the same commit, with a `pre-pro1` tag.
- `/api/frame` carries `fold.read(trade)`.
- The extension panel is rebuilt to §5.1, with mark-my-trade via `sw.js` (the header test first) and marks from the event log.

**Phase 3: entry and flat.**
- The hypothetical-mark check;
- the expression every minute on F\*;
- NEXT FIGHT with its confirmations;
- the re-entry read.

**Phase 4: the cuts** (§1 tabs, §6.1). One commit per group, tagged before. Nothing live depends on them.

**Phase 5: the missing reads, in shadow:**
- resting liquidity;
- big prints;
- the next-weekly chain;
- SENSEX mode;
- pre-09:15 subscription (last, because it touches the feed and needs a quiet morning to verify).

---

## 9. PRO-1: the one amendment she signs

**It closes:**
- PREREG-merged rev 4 §1–§8 fold clauses;
- rev 5 §A.0–§G (the line, the latch, heal, precedence);
- VALIDATE rev 2 §1.2–§5;
- EXPRESSION rev e §A.2–§E.2;
- PLAN rev 3 §2.1 (risk measured to G, not the line).

**It registers:**
- §2.2's rules;
- §2.3's words;
- §3's entry read and expression;
- §4's flat read;
- the thresholds, all tagged (h);
- **the falsifiers, logged 30 sessions, shown only as counts:**

| read | wrong if |
|---|---|
| OUT (loser) | back inside G by w within 20 min |
| OUT (winner) | the same, or W rebuilt above its peak within 20 min |
| BANK ZONE | the wall ahead broken by θ within 20 min |
| PULLBACK | G accepted |
| PAST GIVE-UP | the entry lost |
| WALL BROKE | price back through the wall by w within 20 min |

**The one open question the forward log answers, not me:** in winner mode, does waiting for the writers (her rule) beat price alone? The replay split on it (22 Sep for her rule, 24 Sep against). The log keeps both columns.
