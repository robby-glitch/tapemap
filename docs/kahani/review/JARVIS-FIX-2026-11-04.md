# Jarvis fix, 4 Nov 2026 (her "first fix jarvis issues and do a thorough investigation")

Done without touching the live server: no start, stop or restart, and no `/api/jarvis` frame or replay call. The replays
ran in my own process after 15:46, one day at a time (about 4 s each).
- Every `.py` change goes live only at her restart.
- The page change goes live at a reload of the Jarvis tab.
- **Nothing is committed.**

Counts and moments only, never a rate. [M] means measured, [I] means inferred.

NOTEPAD rows:
- A229, the range guard;
- A230, flat vs blind;
- A231, SENSEX (§1q and handshake.SPEAK);
- A232, how much of the move is used;
- A233, the Jarvis page.

Another session added its own row "A229" later the same day (13:26, the server starved again). It reuses this
report's first id; that row is not mine and I left it as written.

---

## 0. What was read

- `CLAUDE.md`, `START-HERE.md` §0, NOTEPAD A196–A228.
- `JARVIS-REVIEW-2026-10-31.md`, the v3 weekend plan.
- `GAPS-AND-LIVE-CHECKLIST.md`: §2.8 says "both add = range / pin, a seller's day".
- Fable's `REPORT.md` (a) and R2.2.
- The code: `jarvis.py`, `jarvis_log.py`, `legs.py`, `jarvis_thresholds.json`, `sensex_flow.py`, `handshake.py` (its
  `SPEAK` rule), `fronts.py` (§1d), `onesided.py` (§1o).
- Research-findings §1q and §1s.
- The data:
  - the live call logs of 2, 3 and 4 Nov (the log starts on 2 Nov, so 28, 29 and 30 Oct exist only as replays);
  - the DECODE logs (§1o's day type as logged);
  - the chain records (SENSEX vs NIFTY OI scale).

---

## 1. Root causes, with the minute evidence

### 1.1 The word flickers on a range day (issue 1)

**4 Nov NIFTY.** The live log shows 26 word changes over the day [M]. The offline replay reproduces the morning
word for word and gives 25 for the day:
- 10:00–10:59: 8 changes; 11:00–11:59: 7;
- 6 were PALAT (a lean flip, spoken at once) and 6 were PALAT?.

Each flip was a swing inside the 23,750–23,970f box:

| minute | word | the leg that ended (legs.py) | half of it | fut at the flip |
|---|---|---|---|---|
| 10:29 | PALAT ▼ | ▲ 270 pts, 23,701f 09:15 → 23,970f 09:29 (the opening drive) | 135 | 23,823 |
| 10:50 | PALAT ▲ | ▼ 152 pts, 23,970 → 23,818 | 76 | 23,906 |
| 10:57 | PALAT ▼ | ▲ 91 pts, 23,818 → 23,909 (ROTATION, 0.2σ) | 46 | 23,852 |
| 11:13 | PALAT ▲ | ▼ 114 pts, 23,909 → 23,795 | 57 | 23,854 |
| 11:32 | PALAT ▼ | ▲ 94 pts, 23,795 → 23,889 (TREND at **0.0σ**, "fuelled 11:20") | 47 | 23,835 |
| 12:26 | PALAT ▲ | ▼ 138 pts, 23,889 → 23,751 | 69 | 23,825 |

Each swing ran the same three-word cycle, about 20 minutes long:
1. PALAT, at once;
2. ROTATION or HOLD, after two closes;
3. PALAT?, at one close once 0.35 of the leg is back;
4. then PALAT again.

That is 3 changes a swing: 11 in the 63 minutes from 10:35 to 11:38.

Why, rule by rule:
1. **The lean is a swing rule with no idea of a box.**
   - `legs.read` flips the lean when a leg gives back half of itself (`REV_FRAC` 0.5, with a 1U floor of 24 pts that day).
   - Inside a 200-pt box, every 90–150-pt swing counts as a leg (`LEG_MIN` 40) and every 45–76-pt return is a flip.
   - The 1U floor never binds.
2. **The two flip words skip the two-close rule by design.**
   - `action_words` speaks PALAT at once (an EXIT-class event).
   - It speaks PALAT? at one close once 0.35 of the leg is back (`legs.DEEP`).
   - `ACT_CLOSES` guards only TREND, HOLD, WATCH and ROTATION, so it cannot stop this cycle.
3. **A swing re-qualifies as TREND cheaply.**
   - The ▲ leg 23,795 → 23,889 read TREND at 0.0σ because Jarvis's own vote (the writers plus one more read) said UP
     at 11:20 ("fuelled").
   - So the next pullback became PALAT?, not a quiet ROTATION.
4. **Nothing in the word reads the writers' box.**
   - The count reads only the wall AHEAD, in the lean's direction.
   - Her 2×2 ("both add = range / pin") lives only in the 29 Oct vote's RANGE word, which the ACTION word never used.

What §1d's own fronts say about 4 Nov [M] (top-2 per side among the nine nearest, by peak OI):

| minute | CE fronts | PE fronts | spot |
|---|---|---|---|
| 10:20 | 24,000 stalled +39L · 23,900 building +59L | **23,900 building +68L** (peak +70L) · 23,700 stalled | 23,868 |
| 10:29 | 24,000 building · 23,900 building +62L | **23,900 UNWINDING +55L** · 23,700 unwinding | 23,831 |
| 11:13 | 24,000 building +61L · 23,900 stalled +67L | 23,600 building · **23,900 UNWINDING +43L** | 23,813 |
| 12:26 | 24,000 stalled · 23,900 stalled +73L | 23,600 UNWINDING · 23,900 UNWINDING +37L | 23,798 |

**The "box" was not what it looked like from 10:29 to 11:05.**
- The 23,900 PE writers (+70L by 10:20) were covering. They were in the money as spot fell under 23,900, and their
  +70L was down to +43L by 11:13.
- Meanwhile call writers built 23,900 and 24,000.
- That is her 2×2's **PE cover + CE add = ▼ fuel**. By the writers, the ▲ flips at 10:50 and 11:13 went against them.

The record's other inputs for a guard (no new indicator):
- **§1o's day type** (DECODE log) read MIXED all of 4 Nov [M].
  - It cannot switch a guard ON; it can switch one OFF.
  - It read TREND ▲ on 3 Nov from 10:45 (NIFTY), on 29 Oct from 12:00, and on 2 Nov SENSEX 10:50–12:15.
- **Wall distance** (A218): walls sat 4–6 steps out on the 2 Nov range day, and a floor hugged spot (0.2–2.6 steps) on
  the 3 Nov trend day.
  - On 4 Nov the nearest PE front below spot sat 2–4 steps out (23,700 / 23,600).
  - Distance alone does not separate the days. What does is whether a side was **covering**: call writers covered on
    3 Nov; on 4 Nov, after 11:05, both sides wrote or held.
- **Legs small relative to the box**: each swing turned inside the walls.

### 1.2 "k could not check" lumped two sentences together (issue 2)

- `count()` gives every piece a `side`: with, against or "?".
- The page printed every "?" as "could not check".
- At 3 Nov 09:29 the "5 could not check" were:
  - 4 checked with no side: Sides CAPPED, no answered push, speed SLOW, no trigger;
  - 1 missing: fut OI needs 30 min.
- That breaks house rule 6 on the page, the card and the log (the log kept only with / against / N).

### 1.3 SENSEX's count is starved (issue 3)

Verified rather than taken on trust:
- **§1q's flow is already wired live.**
  - Every SENSEX row of 2, 3 and 4 Nov reads NIFTY's flow (`flow_src` N) [M].
  - The line "flow from NIFTY (§1q)" sat in `health.notes`, which the call log stores as `missing`, so it **read as a
    gap**. Fable (REPORT (a)) and the brief took it as "G13 still open". It is how the flow is made, not a gap.
- **The "7 could not check" were mostly checked-no-side pieces** (the lumping in 1.2). Replay of 3 Nov SENSEX after
  10:00, 332 minutes [M]:

  | piece | state over the 332 minutes |
  |---|---|
  | `wf7` | flat 292 · blind 40 · never with or against |
  | `fut_oi` | flat 332 |
  | `answer` | **against 116**, every one "HELD" · flat 214 |
  | `trapped` | with 155 · blind 177 |

- **Root cause 1: the count counted answers the handshake says it cannot read.**
  - `handshake.py`: "a BANKNIFTY or SENSEX push can never cross 3L and every one would read NAHI … never said until
    then" (`SPEAK = ("NIFTY",)`).
  - On 3 Nov all 19 SENSEX pushes answered NAHI [M].
  - The count read the lean's own push HELD as AGAINST on 116 minutes: a false vote against every ▲ leg.
- **Root cause 2: SENSEX's own OI is read on NIFTY-sized bars.**
  - SENSEX's ±7 writer flow on 3 Nov: median |3-min change| 0.5L CE / 0.6L PE, p90 1.6 / 1.9L, **0 minutes ≥ 10L**
    (`WF_L`).
  - NIFTY the same day: 16.9 / 19.6L, with 206 / 234 minutes ≥ 10L [M].
  - `legs.FUT_LOTS` (500 lots / 30 min) is never reached by SENSEX's thin futures.
  - §1q is not at fault here. Scaling these bars needs new [I] numbers, which are hers (§5).

### 1.4 TREND comes late (issue 4)

- On 3 Nov every TREND ▲ came at or near a top: 10:35, 11:59 and 13:20.
- The count's pieces confirm a move that has already printed.
- The word logic is not changed (per the brief). What she lacked was how much of the move the leg had already used.
- In the replay at those moments [M]:

  | minute | leg | EM used | how_much's "range used" |
  |---|---|---|---|
  | 09:29 (OPENING) | 136 pts | 0.80 of EM | 0.80 |
  | 10:35 | 182 pts | **1.07 of EM** | 1.07 |
  | 11:59 | 210 pts | **1.24 of EM** | 1.24 |
  | 13:20 | 252 pts | **1.48 of EM** | 1.48 |

  At each of the three TREND stamps, the leg had already used more than one EM.

### 1.5 The Jarvis page (issue 5)

Before today's first frame:
- The header showed the 28 Oct demo copy: "NIFTY Nov fut · 28 Oct · replay from recorded + backfilled numbers".
- The intro card showed the 28 Oct paragraphs.
- Live and replay had no visible difference.
- The header showed no freshness: A221's `oldLine()` ages the call only inside the box.

---

## 2. The fixes

| NOTEPAD | File · function | Diff (+/−) | Check added |
|---|---|---|---|
| A229 | `jarvis.py` `_box` (new), `action_words`, `said`, `_walls` / `_basis` (moved out of `call`, shared), `call` (RANGE has no side in WHERE / EXPRESSION); `jarvis_thresholds.json` `BOX_STEPS`; `jarvis_voice.py` names RANGE | jarvis.py +83 / −24 in all; json +2; voice +2 / −1 | `test_the_range_guard_holds_range_inside_the_writers_box` (toy: RANGE at once, held over two more flips, leaves at 2 closes past a wall; a covering wall or §1o TREND → PALAT as before) |
| A230 | `jarvis._count_of`, `jarvis_log._cnt3`, `jarvis_cmd` status, `tools/jarvis_cli.py`, the page | log +5 / −1, cmd +3 / −2, cli +3 / −2 | `test_a_question_mark_is_flat_or_blind_never_one`; the log-row contract test updated |
| A231 | `jarvis.health` (the §1q line → `method`), `jarvis.count` (answer piece obeys `handshake.SPEAK`) | in jarvis.py | `test_niftys_flow_on_sensex_is_method_not_a_gap`, `test_an_index_whose_answers_are_not_said_never_counts_them` |
| A232 | `jarvis.call` (the leg line) | in jarvis.py | `test_the_leg_line_says_how_much_of_em_it_used` |
| A233 | `docs/kahani/review/mockup/jarvis2.html` | +40 / −9 | tested on a scratch copy in the browser (below) |

Tests: 93 lines added, 3 changed, in `test_jarvis.py`. Three existing assertions now also expect the new `state` key
and the method line.

### A229: the range guard (`jarvis._box`, `action_words`, `said`)

**When the writers hold a box** at minute i (all read off the frame, causal):
1. Both walls are there: the nearest CE wall at or above spot and the nearest PE wall at or below it, among §1d's
   fronts (top-2 a side, read only).
2. **Neither wall is covering.** Covering means UNWINDING held for 3 minutes: this file's own Q17 hold
   (`unwinding_held`).
   - §1d reads UNWINDING on any 15-min slope falling more than 5% of the peak, so a wall at the threshold flickers.
   - Example: the 23,900 CE read STALLED at 11:31 and UNWINDING at 11:32 only, and that one minute broke the box at
     the flip.
3. The leg turned inside the walls: its extreme is within **one strike step** of the box (`BOX_STEPS` 1 [I]), in spot
   terms (futures less the 3-min basis).
4. **§1o's day type**, as DECODE last logged it by that minute, is not TREND.
5. The chain was seen that minute: a carried wall is not a box.

**What the word does:**
- A PALAT inside the box is said as **RANGE** (at once, no arrow) instead of PALAT ▲ / ▼.
- RANGE then holds while the box holds: every candidate is RANGE, quiet or not, but never over CAN'T SEE.
- When the box breaks (a wall covering, the leg past a wall by more than a step, or §1o TREND), the leg's own word
  returns by the two-close rule.
- A PALAT outside a box is spoken at once, as before.
- RANGE enters **only through an in-box PALAT**, so a trend day's pauses (PALAT?, with no flip) never become RANGE.

**The lines it shows** reuse the 29 Oct vote's own RANGE lines:
- "wrong if: a 3-min close outside <PE wall> – <CE wall>";
- "no buyer trade mid-range";
- "sell outside the range: CE at / above …, PE at / below …".

WHERE and EXPRESSION get no side, so there is no T1 / T2 toward a lean the word says is not there. The card's `lean`
stays the leg's (its own chip, as for OPENING).

### A230: flat vs blind

- Every piece carries a `state`:
  - **with**;
  - **against**;
  - **flat**: checked, takes no side;
  - **blind**: could not check (its text says so).
- The count adds `flat` and `blind`. `unread` (= flat + blind) stays, because Dext reads it.
- The call log's `count` now carries `flat`, `blind` and `pieces: {k: state}` for every minute.
- The page prints "WITH 2 · AGAINST 1 · 4 flat · 2 blind", with blind in red when > 0, and FLAT / BLIND per piece on
  hover.
- The terminal and `status` print flat / blind.

### A231: SENSEX

1. "flow from NIFTY (§1q)" moves from `health.notes` (= the call's `missing`) to `health.method`.
2. An index outside `handshake.SPEAK` (SENSEX, BANKNIFTY) has its `answer` piece **not counted** (state flat): "not counted —
   SENSEX's answers are logged, not said: the 3L answer bar is NIFTY's (handshake.SPEAK)".
   - Review change (4 Nov evening): first built as blind ("could not check"). The data is there and left out by design,
     so blind would put a red "1 blind" on every SENSEX minute: rule 6's "not showing you", never "could not check".
   - The handshake rule itself is unchanged; Jarvis now obeys it.
   - Reverting it is one line.

§1q is unchanged.

### A232: how much of the move is used (display only)

- The leg line carries the leg's points over `trademap.em`'s EM once EM is known:
  `leg ▲ TREND 182 pts · 1.07 of EM · 2.3σ · …`.
- The word logic is unchanged, and how_much's "range used" stays.

### A233: the Jarvis page (`docs/kahani/review/mockup/jarvis2.html`)

- **A header pill** shows which page this is:

  | pill | colour | when |
  |---|---|---|
  | LIVE | green | today, from the brain |
  | STALE | red | exactly when A221's `oldLine()` fires |
  | REPLAY | blue | a recorded day |
  | DEMO | grey | the 28 Oct file |

- **Live freshness:** `LIVE · call 12:41 · as of 12:41:25 · 35 s old`, refreshed every 5 s. Before any frame it reads
  `LIVE · waiting for today's first frame`.
- **No demo copy:**
  - a live page hides the 28 Oct intro card at once;
  - while loading, a replay's intro and header name its own day and index;
  - the evening-review title names the replayed day.
- RANGE is drawn grey (no side); the count shows flat / blind.

How it was tested: on a scratch copy served from its own port, with no TapeMap call.
- DEMO.
- LIVE before any frame: an unreachable API, so the retry line shows; an arrow key pressed before the frame does not
  crash it.
- LIVE with a stale card: `STALE · call 10:42 · as of 10:42:51 · 150 min old`.
- REPLAY with a v4 card: RANGE grey, "WITH 2 · AGAINST 1 · 4 flat · 2 blind".
- Zero JS errors (the only console lines were the deliberately unreachable test API).
- The copy was then put in place byte for byte.

---

## 3. Before and after (offline replay, my own process, after 15:46)

How it was measured:
- `jarvis.build(day, idx, None, fill=False)`: the record as live saw it, refills included.
- The ACTION word at every minute, computed twice on the same frame:
  - **before** = the range guard off and the index's answers counted, as before today;
  - **after** = this code.
- The replay's "before" reproduces the live log of 4 Nov word for word from 10:00 to 14:47, except one word: TREND ▲
  at 13:35 live, 13:38 in the replay (a later refill).
- Live-log totals (what she saw): 2 Nov NIFTY 23 / SENSEX 31; 3 Nov 15 / 14; 4 Nov 26 / 30.

**Word changes per day [M]:**

| Day | NIFTY before → after | SENSEX before → after | Notes |
|---|---|---|---|
| 29 Sep | 27 → **20** | not replayed | 11:10 PALAT ▲ → RANGE (box 22,600–22,700s, both stalled); HOLD ▲ at 11:17 once price broke 22,700 (before 11:14) |
| 28 Oct | 20 → **19** | not replayed | 10:55 PALAT ▲ → RANGE (box 22,500–22,600s, both stalled) |
| 29 Oct (trend ▲) | 15 → 15 | 25 → **22** | NIFTY unchanged |
| 30 Oct | 14 → 14 | not replayed | the 10:55 PALAT ▲ (a real turn: the leg ran to 23,173) kept: no box |
| 2 Nov | 20 → 20 | 31 → **27** | NIFTY's two flips had a covering wall or §1o TREND |
| 3 Nov (trend ▲) | 15 → 15 | 15 → **11** | NIFTY unchanged (0 lean flips); SENSEX lost its false AGAINST toggles |
| 4 Nov (range) | 25 → **22** | 29 → **19** | see below |

**4 Nov NIFTY, the brief's window:**
- 10:35–11:38: **11 → 7** changes.
- 11:00–11:59: 7 → 3.
- 10:00–12:59: 18 → 15.

| minute | before | after |
|---|---|---|
| 10:50 | PALAT ▲ | **RANGE** (23,700s PE · 23,900s CE stalled) |
| 10:56 / 10:57 | ROTATION ▲ / PALAT ▼ | same: the 23,700 PE's covering held 3 min, so no box (the ▼ fuel of 1.1) |
| 11:13 | PALAT ▲ | **RANGE** (23,600s PE building – 23,900s CE stalled) |
| 11:17 / 11:26 / 11:32 / 11:38 | ROTATION ▲ / PALAT? ▲ / PALAT ▼ / HOLD ▼ | RANGE held |
| 12:20 | (HOLD ▼ since 11:38) | HOLD ▼: the box broke at the 12:15 low (23,751) |
| 12:26 | PALAT ▲ | PALAT ▲: the 23,600 PE covering, no box |

**3 Nov, the TREND moments:** TREND ▲ at 10:35, 11:59 and 13:20 are unchanged. Their leg lines now read 1.07, 1.24
and 1.48 of EM. SENSEX on 3 Nov **still never says TREND**: its ±7 and fut-OI pieces stay flat all day (§5.1), so it rarely
reaches WITH ≥ AGAINST + 2.

**What got worse [M]:**
- **2 Nov SENSEX: HOLD ▼ came 15 min later** (12:50 → 13:05). It said RANGE from 12:33 while fut went 75,600 → 75,476.
  - The box was 75,000–75,400s, 4 steps wide (A218's range-day width).
  - The ▼ HOLD before had been said at 75,563.
- **4 Nov NIFTY: HOLD ▼ at 12:20**, five minutes after the 12:15 low (23,774f), then PALAT ▲ at 12:26.
  - Before, the screen had held HOLD ▼ since 11:38.
- **28 Oct NIFTY: HOLD ▲ came 3 min later** (11:05 → 11:08, 22,662 → 22,651).
- **29 Sep NIFTY: HOLD ▲ came 3 min later** (11:14 → 11:17, as price broke the 22,700 CE wall).
- **2 Nov SENSEX added a TREND ▲ at 15:26** (75,698), from the count without the false AGAINST.

---

### Tests

- `python -m pytest -q` after the close: **2334 passed, 4 skipped, 1 xfailed** (the strict 21 Oct bar, unchanged),
  **1 failed**: `test_no_buyer_pick_while_the_word_says_no_new_one`.
  - It expected PALAT at 29 Sep 11:12; the word is now RANGE there.
  - Its purpose is unchanged and still holds: no buyer pick while the word says no new entry (`pick` None).
  - Its precondition now accepts RANGE; re-run: passed.
- New checks: 5 tests in `test_jarvis.py` (range guard, flat / blind, EM line, the §1q method line, SPEAK), plus the
  log-row contract in `test_jarvis_log.py`.

## 4. What I did not change, and why

- **No registered rule** (§1b–§1s).
  - §1d's fronts and §1o's meter are read, never changed.
  - §1q is unchanged: its flow was already wired.
  - `handshake.SPEAK` is unchanged; Jarvis now obeys it.
- **`legs.py` is untouched**: the lean, PALAT, PALAT?, `LEG_MIN`, `REV_FRAC`, `DEEP`.
  - The guard sits in the ACTION word, where the two-close rule lives.
  - The leg's state (`state` on the card) still says PALAT, so the evening review and the pause log see the raw swing.
- **Not changed in the ACTION word:**
  - the two-close rule and `ACT_LEAD`;
  - the count's pieces and their order;
  - PALAT at once outside a box;
  - the wall-behind BROKEN rule;
  - CAN'T SEE;
  - OPENING before 10:00.
- **The TREND logic** (issue 4 is display only).
- **Thresholds**: `jarvis_thresholds.json` gains only `BOX_STEPS` at 1, with its reason. The live server ignores a name
  it does not know until her restart.
- **The Dext extension** (its own repo): it reads `unread` as before and shows RANGE as a word. Flat / blind and a grey
  RANGE on her chart face are a Dext change.

## 5. Open items that are hers

1. **SENSEX's OI bars.** These are NIFTY-sized:
   - ±7 `WF_L` 10L;
   - the handshake's 3L answer bar (`SPEAK`);
   - `legs.FUT_LOTS` 500 lots.

   SENSEX's ±7 sum runs at about 1/30 of NIFTY's (3 Nov medians 0.5 vs 16.9L). A SENSEX bar is a new [I] number per
   index, a scale like handshake's own `FUT_LOTS` table. Until it is set, SENSEX cannot say TREND on most days.
2. **"Writers decide the lean."** The ▲ flips at 10:50 and 11:13 on 4 Nov went against her 2×2 (23,900 PE covering +
   call writers adding = ▼ fuel). Stopping a PALAT that flips against the writers' fuel would be a legs.py rule:
   hers.
3. **The first-hour line** ("TREND forming since 09:26", Fable rank 1): her call. Not built.
4. **Option flow in the count** (a vote): the studies say sentence + `who` only until the forward log says otherwise
   (R2.2). Not built.
5. **SQUEEZE ON / PIN** words: pre-registered shadow under §1s; the replay script comes first. Not built.
6. **RANGE and flat / blind on her Dext chart face**: a Dext change.
7. **`BOX_STEPS`** (1 strike step) is [I]. On the next range day, check the call log for a false break that left RANGE
   (4 Nov 12:15 is the one on record).
