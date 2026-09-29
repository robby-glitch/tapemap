# The pro tool: blueprint 6 (the judge, after both reviews)

**Written:** 2026-09-28, late evening. Read-only on code and data. Nothing was edited, started, posted or committed outside `docs/pro-tool/`.
**Replaces:** `4-final-blueprint.md`. It applies every MUST-FIX in `5-review-trader.md` (score 5/10) and `5-review-safety.md`, or rebuts it with evidence in §13.
**The one amendment she signs:** `6-amendment.md`. **Her one page:** `6-for-mary.md`.
**Re-checked tonight [M]:** `git status` and line counts of `data/trigger_log.jsonl` (working 2,005; HEAD 402; newest backup 1,995); `frame.py:263` (the frame's `fut_oi` is built from the bars the extension posts); `server.py:1354` (the Trade tab pools 5 prior GoCharting tape days); `server.py:2873` (only `/api/hold/*` checks `Sec-Fetch-Site`); `sw.js:2` (the extension posts `/api/frame` from its service worker).
**New replays tonight [M]:** `scratchpad/j6/` — `expr_rel.py` (a relative wall-pace expression on the 8 marks), `run_j6.py` (G never loosens, all 9 trades), `run_x.py` (the expiry-afternoon rule on 22 Sep, buys, sells and the re-entry). Built on the trader reviewer's `t5/reader_t5.py`, two env flags added (`NEVER_LOOSEN`, `EXP_PLAIN`).
**Tags:** [M] measured, [I] inferred, (h) hand-picked threshold.

---

## 0. Her question, answered

> "as a trader who made a trade will he fold exactly [on one condition]?"

**No.** A professional asks three questions, at different places, and says in advance what would change his mind.

1. **Is the trade wrong?** Price has been *accepted* past the level he entered on. That is a stop. It does not wait for OI, for a candle, or for anything else.
2. **Are my defenders gone?** Once the trade is paying (the give-up has trailed past the entry), he gives it rope. He folds when the flow is accepted past the give-up **and** the writers behind him have really come off their peak, or when that acceptance simply holds. A winner never goes back through his entry.
3. **Is the trade done?** The tape never named a top in this sample. The tool gives no bank verdict. It shows the wall ahead in numbers, the premium's peak and what has been given back. She banks.

**The distinction her rule needs.** She said: "if these are behind me I will hold, and if not I will fold." A pro splits "not behind me" in two:
- **quiet** (nobody is pushing either way): the trade is resting. He holds, and knows what would take him out.
- **against** (flow, OI or VPIN turned on him **at his level**): that is the fold, once price confirms it.

**Her put today, on this engine.** 23000 PE at 120.4, 09:30.
- At **14:12**, where she left at **164.8** [M], the four reads were: zone quiet, flow quiet (no fight in 10 buckets), OI quiet (22900 CE writers *stopped* adding), VPIN with her [M]. Nothing was against her. The new screen says exactly that: **"HOLD · behind you: VPIN · nothing against you"**, and line 2: "out if 22924 is accepted and held 2 buckets, or accepted while 22900 CE writers leave".
- The wall ahead line read "22850 PE · 145.6L, peak 151.7L 14:01". By 14:20 it read 98.5L: the writers under the move pulled 47L in eight minutes [M]. The put printed 210.6 at 14:20 and 236.95 at 14:38 [M].
- That is one trade. It shows the shape, not the odds.

---

## 1. What the reviews changed

| # | MUST-FIX | done | evidence |
|---|---|---|---|
| T1 | Headline and chips disagree | **Fixed.** The clause under the headline is now built from the four reads: "behind you: …", "against you: …", or "nothing behind you now, nothing against you". The tape words (pullback, tiring, failed low) move into the FLOW row. | At H2 14:12 the headline said "tiring" with 3 reads quiet; at A1 14:00 it said "HOLD · failed low" with flow and OI against [M]. The clause now changes only when a read changes, so its flicker is bounded by the chips' (it ran 44 times on H1 as a tape word). |
| T2 | Expiry afternoon | **Fixed, flagged post hoc.** After 13:30 on expiry day, once trailed, G steps to the best future since entry less θ at every bucket close her way; FOLD on plain acceptance, no OI wait. The premium line splits in-the-money and time value on expiry day. | A1: +77 → **+199** at 14:12:45 [M, j6]. The short mirror S1: +58 → +84 [M]. A2, S2 unchanged [M]. On non-expiry days the same trail cost H2 +71 → +35 [M, t5], so it is expiry-only. Designed on the one expiry trade: 29 Sep is its first unseen day. |
| T3 | The re-entry read is not the answer to the whipsaw | **Fixed.** It is a read, printed as unproven, with its falsifier. The whipsaw has no answer yet, and the blueprint says so. | Taken as a trade it lost 3 of 3: −29, −11, −43 [M, t5]. A 3-minute acceptance floor also lost (A5 −10 → −19, A6 −17 → −25, A1 +77 → +58) [M, t5]. |
| T4 | OI event floor | **Fixed:** n ≥ 3 updates and a drop ≥ 3 % (h) of the wall, on top of 3σ√n. | 12 of 21 events had ≤ 3 updates and 1.1–3.9 % dips; all were withdrawn. The floor keeps 8 of 21 and changes no exit [M, t5]. |
| T5 | The expression's "not adding" | **Fixed, replayed.** BUY needs the wall ahead loading *slower* than her defenders (both as % of their own OI over the last 6 min). The calendar votes (expiry eve, expiry day) are removed. | The literal rule read SELL at all 8 marks [M, re-run tonight]. The relative rule reads BUY at A1 (+264) and H1 (+154), SELL at the other six [M, j6, in-sample, n = 8]. The expiry-day BUY rule as written would have read SELL at A1 (wall ahead +6.8 % in 6 min) [M]: it forbade the very trade it was written for. |
| T6 | Gate table split | **Fixed.** Mechanical / hand-picked / sold / re-entry, each trade's peak-before-exit and give-back, never sums alone. §4.8 does it here. | Mechanical six under blueprint 4: +3, median −11 %. Hand-picked two: +169 [M, t5]. |
| T7 | G never loosens | **Fixed.** A new give-up may only tighten, touched or not. A refused loosening is logged. | H2 13:34 loosened 22913 → 22924; R-A2 14:38 by 16 [M]. Never-loosen changes **no exit** on all 9 trades [M, j6]. |
| T8 | Seller sentences | **Fixed.** Three seller sentences (§4.7). The expiry-afternoon rule applies to the short identically. | Same engine, same numbers; for a short, a stall is time working for her. |
| T9 | Chip gate on all five days | **Kept as a gate** (P2-04), with ZONE event-born and VPIN's 2-close exit, ex-FLOW ≤ 6/h. | 3 of 8 trades ran 6.6–7.1/h [M, t5]. |
| T10 | 22 Sep plumbing disclosed | **Fixed** in every table: no prior session on disk, so the bucket is the day's own first 15 minutes (not causal); no VPIN rows. | [M, t5 headers] |
| S1 | trigger_log exposed | **Fixed as P0-01.** Copy it out now; forbid `stash`, `reset --hard`, `checkout .`, `clean` in every brief; her commit of the staged untracking comes first. | Working 2,005 lines, HEAD 402, backup 1,995 lacks today's 10 rows [M, re-counted tonight]. |
| S2 | The contract match is circular | **Fixed.** Match GoCharting's bar OI against the Upstox ux bar's OI through a new frame field; 2 % tolerance on closed bars; TapeMap down = not trusted; `g.ahead` only when the last loaded bar's date is `frame.day`. | `frame.py:263` builds `fut_oi` from the posted bars [M]. Same-contract disagreement ≤ 0.93 % [M, safety]. |
| S3 | Never HOLD when blind | **Fixed.** A fourth headline, **CAN'T CHECK since hh:mm · why**, with rules for each hole (§4.6). | — |
| S4 | Leak guard | **Fixed as P1-01**, with the restart test extended (exit, reopen). | Leaks on 08-24, 09-19, 09-28 [M, safety]. |
| S5 | The 30 Sep roll for the Trade tab | **Fixed as P1-03.** Prior tape days on or before the Sep expiry are dropped, with a reason. BUGFIX #6 committed and running before 30 Sep 09:15. | `server.py:1354` [M]. |
| S6 | No Upstox stamp on GoCharting rows | **Fixed in P1-04.** | `tape_log.py:4-6` [M, safety]. |
| S7 | Amendment mechanics | **Fixed** in `6-amendment.md`: no signed file is edited; signature and hash live in `research-findings.md` §1i; in force from the first session the rev 6 face is live; her commit of the file is the proof of order. | — |
| S8 | Unseen days in the gate | **Fixed.** 29 Sep (expiry) and 30 Sep (the roll) are reported separately as unseen; 22–28 Sep are named as design days. | — |
| S9 | The shadow verdict in hours | **Fixed.** Logged only during hours; shown in RECORD after 15:30; live on DESK only if she says so. | — |
| S10 | Resume | **Fixed.** Causal recompute on the arrival clock; logged words win on screen; a difference writes a `diverged` row; rows on events and bucket closes only. | — |
| S11 | `/api/hold` cost | **Fixed.** Incremental fold, a timing assertion, no day-file read on a request. | Day book files about 60 MB [safety]. |
| S12 | P1-02 over-scoped | **Fixed.** Tokens, `<details>` state kept, skip unchanged HTML, `test/panel.mjs` in `npm test` and `verify`. Full patching stays in P3-03. | — |
| S-extra | `/api/frame` accepts any site's POST | **Fixed, narrowed** (§13, R3). | `server.py:2873` guards only `/api/hold/*` [M]. |
| S-extra | Three alternatives could each replace the trailed rule | **Fixed.** One primary alternative, named now: the held breach alone. | — |

---

## 2. The debate's calls that stand

These are blueprint 4's settled rows. Nothing in the reviews overturned them.

| call | why it stands |
|---|---|
| **Losers: acceptance alone, no time floor** | A time floor cost 33 pts over 4 losers (Opus `PL_*`), and a 3-minute floor lost again tonight (T3). |
| **Winners: flow + OI, or the held breach, or the backstop** | 24 Sep +98 against +81. The backstop fired in none of the 8 but is the only rule that stops a winner going red in a 15-minute V. |
| **Three headline states, plus CAN'T CHECK** | Headline changes 0–0.7/h against 4–8/h for six words [M]. |
| **The word is FOLD** | Her word. "Out" collides with her I'M OUT button. |
| **The wall ahead is numbers only, no bank verdict** | The same 3σ√n event on 22850 PE fired four times and withdrew three before the real unwind [M]. |
| **"Winner/loser" never shown** | Line 2 states the out-condition, which is what the mode means. |
| **The front month's volume is the bucket** | Oct traded as the far month; its own volume would speed the clock the wrong way. |
| **§1d, the fade gate, is untouched** | It feeds `trigger_log.jsonl`. One wall ranking governs the new engine and every face; §1d keeps its own. |
| **The re-entry read costs the move back** | 25 Sep: out 86.65, read at 10:24 with the premium at 100.9 [M]. |

**Still unsolved, stated.** The whipsaw on a busy open (acceptance can stand in 55–80 s; A5 folded at −10 and was back inside 49 s later [M]). The 0DTE option that bleeds inside its give-up (R-A2: −47 % in 45 min, the future never near G [M]); the engine is premium-blind by her rule, so the tool shows the time value falling and she decides. Whether "no bank verdict" helps her hold longer: only her log can say.

---

## 3. The trader's day

| moment | one glance | where |
|---|---|---|
| **Pre-open, 09:00–09:15** | Contract and flags (expiry, eve, roll). Yesterday's high/low/close **for this contract**. The two biggest walls each side, from the last same-expiry snapshot, or "could not check" and why. Feeds alive. | DESK header + THE DAY |
| **The open** | Who the gap trapped against yesterday's close [I]. The first fight. Every read from its first mark ("n of 5"). Moneyness "could not check: chain from 09:17" until the first chain snapshot. | DESK · FLAT |
| **Flat** | NEXT FIGHT above and below, and what confirms each. After a FOLD, the re-entry read, marked unproven. | DESK · FLAT, the panel |
| **Entering** | IF YOU WERE IN: the headline it would show, line 2, G and the premium there, the wall ahead in numbers, buy-or-sell with its two numbers, the amber clauses. | DESK, the panel's mark row |
| **In a trade** | Headline + what is behind / against her; line 2 (the out-condition); premium, peak, given back, at G; the wall ahead; four rows. | DESK and the panel, identical |
| **Expiry afternoon** | The give-up now follows the best price; the premium split into in-the-money and time. | both |
| **Exiting** | FOLD with its reason, frozen. Never a size, never a fraction. | both |
| **After, and close** | The trade's word history. The shadow engine's words for the day (until she signs). Falsifier counts, never rates. `trigger_log` rows as they are. | RECORD |
| **Any time** | When each wall was built, whether it holds, and which front retreats. | WAR |

"Flat by 15:00 (your practice)" shows in the header from 14:45. After 15:00 the entry face carries the amber clause. Display only, never a rule.

---

## 4. The hold and exit engine, exactly (`fold.py`)

### 4.1 What the son checks, in order, before he changes his mind

1. Where is price against my give-up?
2. Was it accepted there, or poked?
3. At the level: initiative, or absorbed?
4. Am I trailed past my entry (a free trade), or not?
5. Did the writers defending me leave **after** I entered, and by enough to matter?
6. The wall ahead: loading or covering (numbers)?
7. VPIN: is informed flow with me?
8. Is it expiry afternoon? Then my give-up follows my best price.
9. What have I given back? What is time value doing? The clock.
10. Can the tool see right now? If not, it says so.

**These never move him:** a candle close, a trend box, a quiet clock, her S1–S4 lines, OI off its peak while price holds his level, a read going quiet, or one minute of anything.

### 4.2 Units

- **bucket** = 3 (h) × the median 1-minute volume, pooled over ≤ 5 (h) prior sessions **of the front-month series** (Sep until its expiry, Oct from 30 Sep). A day with no prior session on disk uses its own first 15 minutes, flagged "not causal before 09:30".
- **B** = today's median 1-minute range so far (the pooled prior value until 5 bars). **θ** = 2B, **w** = B/2.
- **Median bucket duration so far** (3 minutes until 5 buckets exist) is the acceptance clock.
- **F\*** = future − the median of (future − (K + C − P)) over strikes with |Δ| > 0.3, over the last 15 (h) chain minutes. Before 15 minutes exist it uses what exists, tagged "basis n of 15 min [I]". Before the first chain snapshot (about 09:17), F\* does not exist: moneyness, W and A read "could not check: chain from 09:17"; G can still be seeded from a fight, which needs only the future. `spot` is never a reference.

### 4.3 Fights, levels, traps, G, W (H v3 §4, §6.1, §7.1–7.3, one change)

- **Fights:** one-sided bucket = sure imbalance ≥ ½ and |b − s| > 2G (guessed volume). A sweep is signed by price only at |Δp| ≥ θ, tagged "by price [I]". Fights fix on the next bucket of another kind.
- **G, the give-up:**
  - seeded at the mark from the newest fight before entry (if her side won it and trading is ≥ w her side of it), else the defending wall + w;
  - re-set on each win by her side (a new epoch), **only if the new G is tighter**;
  - **G never loosens, touched or not.** A refused loosening is logged. Priced: no exit changes on 9 trades [M, j6].
- **W**, the wall that sets G: the most OI on the defending side between F\* and G, chosen only when G is set.
- **FAILED** needs a new extreme ≥ w beyond the old one, rejected ≥ w. **TIRING:** 2 stalled closes in a 5-bucket window to enter, 2 non-stalled to leave.

### 4.4 One wall ranking, two windows

- **The ranking:** current OI (not day-high), near-ATM, beyond F\* by w. A new choice must stand 2 bucket closes, or F\* must be w through the old wall. `fold.py` owns it. **`fronts.py` is not touched** (§1d's parameters; `trigger_log.py` imports it).
- **W** (behind her): the §4.3 rule. **A** (ahead): the nearer of the top two on the far side, at K + basis, at least w beyond her entry.

### 4.5 The OI event, acceptance, the fold

- **OI event, on W only:**
  - (peak since reference − OI) ≥ 3 (h) σ √n, σ = 1.4826 × the median |ΔOI| of the 15 updates before the peak, floor 1 lot;
  - **and** n ≥ 3 (h) updates since the peak **and** the drop ≥ 3 % (h) of the peak;
  - live until W prints above that peak (withdrawn, re-armed) or her side sets a new G; one at a time; logged with z, n and %.
- **Acceptance:** from the first print at or beyond G, sum the lots at or beyond it; accepted at **1 bucket** of lots over **≥ the median bucket duration**; a print w back inside restarts the tally before acceptance, or withdraws it after. **No tally spans a data hole** (§4.6).
- **Mode:** *trailed* if d·(G − E) > 0, where E is the future at her mark; else *at entry*. Re-read whenever G changes.

| mode | FOLD fires on | reason printed |
|---|---|---|
| **at entry** | acceptance beyond G | "FOLD · 22997 accepted" |
| **trailed** | acceptance beyond G **and** a live OI event on W, same epoch | "FOLD · 22900 CE writers gave up 11:42, 22925 accepted" |
| **trailed** | **held breach:** the acceptance stands 2 (h) more bucket closes and ≥ 2 (h) × the median bucket duration, with no win by her side and no print w back inside | "FOLD · 22925 accepted and held 2 buckets" |
| **trailed** | **backstop:** acceptance beyond E ∓ w | "FOLD · back through your entry 22941" |
| **trailed, expiry day after 13:30 (h)** | G steps to (best future since entry) − d·θ at each bucket close her way (tighten only); **plain acceptance** beyond G folds, no OI wait | "FOLD · expiry afternoon: 23308 accepted" |

Why the expiry row: expiring OI coming off its peak after 13:30 is partly expiry closing, not writers giving up [I, safety]; and gamma makes a 15-minute V common. A1 22 Sep: G sat 73 points (7B) away from 13:01 to 14:15 because no seller-won fight fixed; the put gave back 187 points of entry premium in 19 minutes under HOLD [M, t5]. With the row: out at 14:12:45 at +199 %, against +77 [M, j6].

- **PAST GIVE-UP** (trailed only): G accepted, no FOLD yet. Amber, no sound. Line 2 counts: "22925 accepted 14:37 · 1 of 2 buckets · 22900 CE writers holding".
- **OI alone** is an OI row AGAINST with its time, and no sound. **STOPPED** (15 updates without a new high) turns the row QUIET; it never folds.
- **One sound:** FOLD, two low tones, once per epoch, ever. Ids are kept across reloads, so a reload is silent.

### 4.6 CAN'T CHECK (the fourth headline)

HOLD is a positive claim. A HOLD that has stopped looking is the costliest lie on the screen for a trader whose problem is holding.

| hole | headline | what still runs |
|---|---|---|
| **No G** (no fight her side and no wall read, e.g. before 09:17) | "CAN'T CHECK · no give-up yet: no fight her way, chain from 09:17" | Line 2: "a give-up is set at the first fight her way or the first wall read" |
| **Order flow silent** ≥ 30 s (h) between 09:15 and 15:30 | "CAN'T CHECK since 11:42 · order-flow feed silent 45 s" | The last live read under it, grey. G and W carry through. Any tally in progress restarts after the hole. |
| **TapeMap was down** (a stretch with no book rows) | After restart, the hole shows in detail: "could not check 11:02–11:09: TapeMap was down, no rows recorded" | No tally or OI event spans it. |
| **Chain stale** > 180 s (h) | Headline unchanged. OI row: "could not check: chain 4 min old". Line 2 adds "OI blind: held breach and backstop still watch" | The flow + OI fold cannot fire; at-entry acceptance, held breach, backstop and the expiry row still can. Premium at G: "could not check" past 60 s. |
| **TapeMap unreachable** (panel) | "your trade: could not check · TapeMap not reachable" | Never FLAT. |

### 4.7 The headline, the clause, line 2, after the fold

| headline | look | clause |
|---|---|---|
| **HOLD** | ink | built from the four reads, her order: "behind you: flow, OI" · "against you: OI since 13:45 · behind you: VPIN" · "nothing behind you now, nothing against you". Never a count, never a colour for a count. |
| **PAST GIVE-UP** | amber | the count (§4.5) |
| **FOLD · reason · hh:mm** | ink block | frozen |
| **CAN'T CHECK since hh:mm** | grey | why (§4.6) |

The tape words move into the FLOW row: "sellers won 11:04 at 22879", "pullback since 12:28", "failed low 11:56", "tiring 6 min". The clause changes only when a read changes, so it is bounded by the chip gate.

**The seller's sentences** (same engine with d flipped, same numbers):
- TIRING → "stalled: time is working for you";
- PULLBACK → "pullback inside your give-up: time still yours";
- won her way → "behind you: the move away from your strike".

**Line 2 always says, before it happens, what takes her out:**
- *at entry:* "out if 22997 is accepted";
- *trailed:* "out if 22925 is accepted and held 2 buckets, or accepted while 22900 CE writers leave · never back through 22941";
- *OI event live:* "22900 CE writers left 11:42 (−4.1 %): acceptance past 22925 now takes you out";
- *expiry afternoon:* "expiry: your give-up follows your best · out if 23308 is accepted".

**After FOLD:** the headline stays frozen with its reason and time until she presses I'M OUT or unmarks; the line under it reads live ("still marked · now: your side won again 12:35"); it never reverts in place.

**Premium at G and at A [I]:** the chain's own price at K′ = K + F\* − G (or A), interpolated between the two nearest strikes (within 0.5 of actual on the 22 Sep expiry exit [M]); chain older than 60 s: "could not check: chain 70 s old".

**Peak and given back [M]:** the best premium since entry, its time, and now against it. **On expiry day:** "CE 36.0 = 12 in the money + 24 time [I]", so a 0DTE option bleeding inside its give-up is visible (R-A2).

### 4.8 The four rows (her order: ZONE · FLOW · OI · VPIN)

States: WITH, AGAINST, QUIET, CAN'T CHECK. No score, no count.

- **ZONE:** H v3's level rule, event-born (a level is born, broken by F\* w through it, or taken by a fixed fight). Its sentence must agree with its chip (at H2 14:12 the chip was QUIET while its text said "behind you: 22892" [M]; a P2-01 test). The row also names her zone machine's state (d2→d3 / u2→u3, armed or triggered, the 09:25 anchor kept) as a sentence, never a vote.
- **FLOW:** the newest fixed fight within 10 buckets, plus the tape word. Event-born; exempt from the chip gate.
- **OI:** W building (new since-reference high within 15 updates) = WITH; an OI event live (§4.5, with its floor) = AGAINST, with its time; stopped = QUIET.
- **VPIN** (10 buckets): in at lead ≥ 2, out only after 2 (h) closes past zero. CAN'T CHECK under 10 live buckets; backfilled buckets tagged, never counted.

Condition-born changes need 2 bucket closes.

### 4.9 The replay this rests on

8 trades, 5 days, to 15:00, % of entry premium [M]. **Design days: 22–28 Sep.** The thresholds were chosen on them; this table describes, it does not prove. **22 Sep:** no prior session on disk (bucket from the day's own first 15 minutes, not causal) and no VPIN rows.

| trade | kind | best | blueprint 4 exit | **blueprint 6 exit** | peak before exit → given back |
|---|---|---|---|---|---|
| A1 22 Sep put @ 47.75 (expiry) | mechanical | +264 | +77 · 14:19 | **+199 · 14:12:45** expiry row | +264 → 65 |
| A2 22 Sep call @ 43.65 | mechanical | +78 after −61 | −42 · 13:51 | −42 · 13:51 | +13 → 55 |
| A3 23 Sep put @ 122.3 | mechanical | +3 | −12 · 12:04 | −12 · 12:04 | +2 → 14 |
| A4 25 Sep put @ 111.6 | mechanical | +42 | +7 · 10:08 flow + OI | +7 · 10:09 held (the 2.3 % OI dip no longer counts) | +35 → 28 |
| A5 25 Sep call @ 96.5 | mechanical | +53 after −29 | −10 · 09:47 | −10 · 09:47 (noise: back inside in 49 s) | — |
| A6 28 Sep call @ 84.05 | mechanical | 0 | −17 · 10:16 | −17 · 10:16 (today's rules: −61 unstopped) | — |
| H1 24 Sep put @ 102.65 | hand-picked | +154 | +98 · 14:39 held | +98 · 14:39 | +153 → 55 |
| H2 28 Sep put @ 120.4 (hers) | hand-picked | +97 | none · +71 at 15:00 | none · +71 at 15:00 | +92 → 21 |

| population | blueprint 4 | blueprint 6 |
|---|---|---|
| mechanical six | +3 (median −11) | **+125** (median −11); +122 of it is the expiry row **on the one trade it was designed on** |
| hand-picked two | +169 | +169 |
| sold mirrors S1–S8 (same seconds, the other side, d flipped) | +63 | +89 (S1 +58 → +84; the rest unchanged) |
| re-entry reads R-A5, R-A4, R-A2 | −29, −11, −43 | unchanged: the read is unproven (§6) |

Sources: t5 (`PF_*`, `S_*`, `R_*`, `PA_*`, `PX_*`), j6 (`NL_*`, `X_*`). The OI floor changes no exit [M, t5]. Headline changes 0–0.7/h; FOLD sounds 0–0.37/h; chips ex-FLOW 1.2–7.1/h before ZONE and VPIN were made event-born (P2-04 re-runs it). **n = 8 describes; the forward log ranks.**

### 4.10 Writers and SENSEX

- **Writers:** the same engine with d flipped, the seller's sentences (§4.7). Her short strike, against F\*, is always a level. No reach and no strike stop (her 26 Sep answers). The expiry row applies to the short identically; short gamma needs it most.
- **SENSEX:** its future prints a median 7–10 lots per 5-min bar [M]. FLOW and VPIN read "could not check: SENSEX future, n lots this bucket". G = the defending wall + w. Acceptance = price beyond G for SENSEX's own median bucket time, flagged [I]. Modes, backstop and the expiry row apply. It never borrows NIFTY's clock.

---

## 5. Entry

**No GO, no NO.** The entry face is the in-trade face for a hypothetical mark, headed **IF YOU WERE IN · long 23000 PE**: the headline and clause it would show; line 2; G and the premium there [I]; the wall ahead in numbers and the premium there [I]; her strike's premium against its day VWAP, as σ, printed, never counted; days to expiry.

**Room and give-up are two printed distances; nothing refuses.** Her +97 % put had 41 pts of room against a 56–72 pt give-up at 09:30 [M].

**Three amber clauses** (facts, not verdicts): "you would enter past your give-up"; "you would enter at the 22900 PE writers (132.0L)"; "after 15:00: your practice is no new trades".

**Buy the option, or sell the other side.** Read at bucket closes, 2 closes to confirm, ATM on F\*, her strike when she names one. **Frozen when the mark row opens.** Printed with its two numbers, always:

> "BUY · the 22900 PE wall ahead +6.8 % in 6 min, your 23450 CE defenders +9.9 %"

| read | when |
|---|---|
| **BUY the option** | the newest fixed fight her way was initiative, **and** the wall ahead is loading slower than her defenders (% of own OI over 6 min (h)) |
| **SELL the other side, ATM (ITM in a trend)** | the wall ahead is loading at least as fast as her defenders; or her side's last win was absorption; or TIRING is live |
| **EITHER** | neither holds |

- R2 (never sell into a squeeze) and R4 (never sell a bid straddle) stay from EXPRESSION rev e.
- **Expiry eve and expiry day are no longer votes.** They print as facts (days to expiry; on expiry day the time-value split). Both calendar rules read SELL at the trades they were meant to allow [M].
- **Shown on the face only if the gate says it is not a constant** (it prints both BUY and SELL across the design and unseen marks, with R2/R4 checked). Otherwise the face reads "not showing you: the buy-or-sell read is in test" and the rows keep logging.
- The sale is folded by the same engine with d flipped. Forward-logged from day one; counts, never odds.

---

## 6. Flat

- **Line one:** "NEXT FIGHT · above 22907 · below 22852", the two nearest strong levels (walls by the one ranking, held levels, trapped shelves, the contract's prior day, her bands), with hysteresis w. Within w of one: "AT 22899 (22900 CE wall) · above 22919 · below 22885".
- **Under each, what confirms it:** "above: lifts at 22905–22910 followed by price **and** 22900 CE off its peak: calls"; the mirror below, for puts.
- **When both halves fire:** a frozen, silent event, **"SELLERS GAVE UP AT 22907 · 11:42"**. She presses Mark if she takes it.
- **The re-entry read, after a FOLD** (unproven, and printed so): "stop run failed at 23094: sellers absorbed at 23134, 10:24 · CE now 100.9 v your exit 86.65 · unproven: 0 of 3 in replay". Silent; falsified if G is accepted again within 20 min. It is logged against the at-entry FOLD's own whipsaw column (§4 of the amendment), so the log can rank it.
- **THE DAY:** one paragraph, ≤ 6 numbers: fights won by each side, value migration, the box, unreleased shelves, expiry and roll lines.
- **After a move:** the nearest trapped shelf each side, the newest marked new.

---

## 7. The two faces

### 7.1 The panel: 400 px, LIGHT, fixed frame

Her put at 14:12 on 28 Sep, the state from `PF_H2_0928_PE` (fut 22877.3) with blueprint 6's clause:

```
NIFTY SEP FUT · 14:12 · contract ✓ · chart placed
long 23000 PE · 120.4 · 09:30                              [ I'M OUT ]
HOLD · behind you: VPIN · nothing against you  ZONE·  FLOW·  OI·  VPIN▪
out if 22924 is accepted and held 2 buckets, or accepted while 22900 CE writers leave · never back through 22945
PE 166.0 +38% · peak 182.7 +52% 11:16 · at 22924 ≈ 134 [I]
ahead 22850 PE · 27 pts · 145.6L, peak 151.7L 14:01 [M]
ZONE  no level born or broken since 13:32
FLOW  no fight in the last 10 buckets · tiring 31 min
OI    22900 CE 240.4L, writers stopped adding (quiet) [M]
VPIN  2 of 10 buckets one-sided, your way
▸ detail
```

Chips: ▪ with you · ▫ against · · quiet · ? could not check.

| budget | value |
|---|---|
| numbers with detail closed | ≤ 24 |
| colours | 5: blue helps buyers, red helps sellers, amber watch, ink hers, grey reference/absence |
| height above detail | ≤ 480 px |
| sounds | 1 class: FOLD |
| headline changes | ≤ 1 an hour (gate) |
| condition-chip changes | ≤ 6 an hour ex-FLOW (gate) |
| chart | 3 + 3 levels, 7 glyphs |

**No flicker:** events frozen at birth; words computed once per event batch; condition-born chips take 2 closes; a named wall holds 2 closes; G is a staircase that only tightens; the DOM is patched, never rebuilt (P3-03; tonight's minimal fix keeps `<details>` open, P1-06).

**Anytime:** the panel GETs `/api/hold/trades` before its first frame; TapeMap down reads "could not check: TapeMap not reachable", never FLAT.

### 7.2 DESK (the Validate tab, renamed)

- The same header, lines and rows at 2× size. The check slip on the left, keys unchanged (C/P, B/S, ↑↓, Enter).
- Detail open by default: the G staircase with refused loosenings, OI events with z, n, % and σ, acceptance tallies, holes, chip history, the trade's words, and the alternative-exit columns (plain acceptance, flow + OI, held breach alone, backstop) marked "logged, not in force".
- The flat half: NEXT FIGHT, THE DAY, the re-entry read, the VPIN gauge as a detail block.

### 7.3 Mark my trade (both screens, one record)

- Mark trade → CE/PE → (BUY/SELL) → MARK: three clicks, four for a sale. Strike prefilled ATM on F\*, with ◂ ▸ steps labelled ATM / ITM 1 / OTM 1. The entry premium is frozen when the row opens; she types her fill.
- The panel posts through `sw.js` to `/api/hold/trades` (the door refuses cross-site POSTs, `server.py:2873`). Build test first: log the `Sec-Fetch-Site` and `Origin` that `sw.js` really sends; the door admits `none`, same-origin, or an `Origin` of exactly `chrome-extension://<id>` from config.
- The record persists in `data/day_state/`; a restart never loses it (already true and tested, `test_hold_route.py::test_a_restart_reads_the_same_window` [M, safety]).

### 7.4 Chart marks and trust (the extension)

- **Every mark comes from TapeMap's event log at its frozen (time, price).** The extension only maps (t, p) to pixels.
- **Glyphs:** ▲▼ fight won; with a white dot, won by price [I]; ▬ absorbed; hatched ▬ disputed; ⌃⌄ failed extreme; ▸ her entry; ■ FOLD. **Lines:** the give-up as a dashed staircase (older steps at 55 %); W and A dotted with a strike chip at K + basis.
- **Cut from the chart:** ROUND lines, the flat σ pocket, the event strip, per-strike pain chips, trap discs, the BANK ◆. 5 px glyph floor.
- **Trust:**
  - with no date tick, fit **only** TapeMap's session day (`frame.day`); with TapeMap unreachable there is no `frame.day`, and the fit reads "not trusted: TapeMap not reachable", never "every loaded day";
  - `g.ahead` (minutes of the last loaded session) is offered only when the last loaded bar's date equals `frame.day`;
  - **contract match against Upstox, not against itself:** GoCharting's bar OI against the ux bar's `oi` (a new frame field: the last N ux bars `{t, oi}`), matched when |ΔOI| ≤ 2 % (h) of OI on the same bar `t`, closed bars only (same contract: worst 0.93 % [M]; Sep v Oct differ by millions);
  - hysteresis: 2 bad to pause, 2 good to resume; paused: one tag, "chart shows another day / contract since hh:mm; marks paused, panel live".
- **Named in her commit message** (acceptable, known): `loaded` keyed by day of month (two months collide), cells no longer veto a label fit, a disagreeing paint needs 2 strikes (one stale frame). `test/session-2026-09-10.ofd.json` was rewritten 15m → 5m in the working copy; confirm who did it before committing.

---

## 8. Remove, keep, add

### 8.1 Removed (through the one amendment where a rule is signed)

| what | where | why |
|---|---|---|
| The session-high line, the 3-min close, noise B; Room, Cushion and the plan's ₹ risk from it | `hold.py`, rev 5 §A, PLAN §2.1 | A candle close. She banned it. |
| Trend as a fold family and as WATCH; `trendbox`; expression REGIME and ROOM | `hold.py`, `validate.py`, `expression.py` | Not one of her four |
| The quiet clock, PERSIST = 3, the FOLD latch and heal; rev 5 §C "adding beats a live fold" | `hold.py` | The latch froze a wrong FOLD all day on 28 Sep |
| The 15-mark OI warm-up, 4-bar flow warm-up, 3-min expression cadence, as inputs to her trade | `hold.py`, `validate.py`, `expression.py` (`fronts.py` stays as §1d's) | Everything reads from its first mark |
| GO / WAIT / NO; the Room ratio; `FOLD_NEEDS` | `validate.py`, H §1 | The mode picks the rule |
| Spot as the moneyness reference | `board.itm/nearer`, plan rung, hold ITM/OTM, expression ATM (never §1d) | 24–46 pts off on 28 Sep [M] |
| Four of five wall rules | `board.py`, `plan.py`, `expression.py` | One ranking; §1d excepted |
| **Expiry eve and expiry day as expression votes** | the expression table | They read SELL at the trades they were written to allow [M] |
| **The tape word as the headline clause** | the face | It contradicted the four reads at the moments that decided the day [M] |
| `gate.py` (always PATA NAHI), `senses`/`ivrv` None fields, the ballot, `watch.py`, the breadth footer, ROUND, both WRONG IFs, the event strip, the flat σ bands, the dark panel | `frame.py`, `panel.js`, `overlay.js` | Fields that never fill, or duplicate her chart |
| BANK ZONE, REACHED, WALL BROKE, the Γ premium term, "pros bank" copy | both drafts | Chain-own prices replace Γ |
| Glass, Heat, Tape, Flow, Chain, OI Flow, Map, Events, Signals (→ RECORD), VPIN tab (→ DESK detail), Board (→ DESK · FLAT) | `App.tsx` | No moment of her day needs them |
| `/api/calls` as a screen | `grounds.py` | Its forward-log rows stay |

### 8.2 Kept, untouched

- Her orders: the Dhan/Upstox fallback; `structure.py`, `band_rotation.py`'s two-leg stack, `contract_pair.py`; the Trade tab and its chart (`vendor/`); `/api/surface`, `/api/drag`, `/api/paper_fill`; the zone's 09:25 anchor.
- **`data/trigger_log.jsonl`**, never rewritten. **§1d** and the zone machine.
- `ladder.side_of`; the thesis table for four roles; "premium is never an input to the verdict" (the time-value split is shown, never read by the engine); three absence sentences; [M]/[I]; no order path; LIGHT.

### 8.3 Added, each in shadow first (logged, gating nothing)

1. **The event log** `data/fold/fold_<IDX>_<day>.jsonl` (§10).
2. **Resting liquidity, at G or A only:** "offers at 22925 stacked 1.2k, 60 % pulled this bucket".
3. **Big prints:** a fill ≥ the 99th percentile of today's fill sizes so far [M], at a level, its side if signed [I]. One line in FLOW.
4. **Failed auction at a day extreme,** on FLAT.
5. **The next-weekly chain on expiry days.**
6. **The GoCharting tick post,** used only to dispute a fight. Kill: more than 1 fight in 3 disputed over 30 sessions.
7. **VPIN fed from the ladder's fills,** one classifier; a new series with its own clock.
8. **`oi_prev`**, the previous-close OI, same expiry, additive. `oi_chg`'s meaning unchanged.

---

## 9. Data truth

| defect | handling |
|---|---|
| **Spot v forward:** 24–46 pts on 28 Sep [M] | F\* everywhere moneyness is judged, except §1d; its first minutes tagged "basis n of 15 min" |
| **Guessed-side volume, 24–59 %** [M] | |b − s| > 2G and imbalance ≥ ½; sweeps signed by price at θ, [I] |
| **Three tapes disagree (63–65 %)** [M] | VPIN from ladder fills; GoCharting disputes only |
| **Book and chain start about 09:17** [M] | "blind before 09:17:19, 1,639 lots unseen"; the 09:15 bar never scored; pre-09:15 subscription last (P6-05) |
| **Rows about 2 min late** [M] | A tick-built minute, reconciled later, tagged (P6-05); resume admits rows by their own clocks (§10) |
| **OI baseline = the 09:15 candle** | `oi_prev`; missing = "could not check", never 0. 30 Sep: could not check unless REST supplies it (P2-05) |
| **A feed goes silent or TapeMap is down** | CAN'T CHECK (§4.6); no tally spans a hole |
| **No contract on the records** | `ik` + `expiry` on book, ux and chain rows; GoCharting tape rows get `ik: null, ik_why: "GoCharting continuous NIFTY-I; contract not declared"` (P1-04) |
| **The roll: Sep expires 29 Sep, Oct from 30 Sep** | BUGFIX #6 committed and running before 30 Sep 09:15. The Trade tab's prior levels and naked POCs drop tape days on or before the Sep expiry, `prior_why` "the Sep future expired 29 Sep; earlier days are another contract" (P1-03). Bucket and B pool the front month. PDH/PDL/PDC are the contract's own (`live._pivots` on `cfg["fut_id"]` [M, safety]). `fut_oi` blind in the expiry week (P1-02). The chart contract match against Upstox (P1-05). |
| **Expiry day** | Expiring OI off its peak after 13:30 is partly expiry closing [I]: hence the expiry row folds on plain acceptance. The Sep future's FLOW and VPIN include roll-spread legs [I, not measured]. EXPIRY · Γ in the header after 13:30. |
| **fit.js session jump; circular contract match** | §7.4, P1-05 |
| **Restart** | §10 |

---

## 10. The forward record and build discipline

**Before any agent builds (P0-01):**
- Copy `data/trigger_log.jsonl` (2,005 rows) outside the repo, and keep today's 10 rows' copy with it.
- She commits the staged untracking first (HEAD's 402-line copy overwrites the live file on any stash or reset), then BUGFIX #1–6 and the extension diff, after their tests pass.
- Every build brief forbids `git stash`, `git reset --hard`, `git checkout .`, `git clean`, and any whole-tree checkout.

**Tests never touch her data (P1-01):** the conftest autouse fixture and `server._isolate_mock_writers` redirect `day_state.DIR`, `hold_log.DIR`, `chain_live.CHAIN_DIR`, `calls_log.DIR`, `frame_log.DIR`, `senses.DIR`, `trigger_log.PATH`, `data/fold/` and the backfill path, besides the three already there.

**The event log (P2-02):**
- One row per event and one per bucket close, never per batch (1 Hz to 15:29 would be tens of MB a trade, the load that wedged the server on 09-18).
- Every row carries `rev`, `thresholds_sha`, `code_sha`, and `shadow: true` until the face is in force.
- **Resume:** a restart recomputes causally from the recorded inputs, admitting a book row by its arrival `t` and a chain row by its own `ts`. Words already logged win on screen and are never re-emitted; an event the recompute would have emitted differently writes a `diverged` row. Tallies, TIRING, chip hysteresis and the σ window come from the recompute.
- **The test:** after the close, recompute the whole day from disk against the live shadow log: zero `diverged` rows. No restart in market hours is needed or allowed.

**The server path (P2-03):** fold runs incrementally inside the poller; `/api/hold` reads its state and never a day file; a timing assertion in the test. During hours the shadow engine only logs; RECORD shows its words after 15:30; live on DESK only on her say-so.

**`/api/frame` (P1-07):** refuse a POST whose `Sec-Fetch-Site` is `cross-site` unless its `Origin` is exactly the extension's. `/api/paper_fill` is not guarded until PaperDesk's sender is checked (her order keeps it working).

---

## 11. Build phases

Nothing ships in market hours; she starts the server; commits on her word.

**Phase 0, tonight, her hands:** P0-01.

**Phase 1, tonight and Tuesday after the close (no method change), in this order:**
1. P1-01 the leak guard and the restart test;
2. P1-02 `fut_oi` blind in the expiry week, SENSEX flow blind;
3. P1-03 the roll for the Trade tab (live before 30 Sep 09:15; she restarts after Tuesday's close);
4. P1-04 contract stamps with the `server.py` threading;
5. P1-05 the extension fit and the Upstox contract match (with its frame field);
6. P1-06 the panel's minimal fix;
7. P1-07 the `/api/frame` guard.

Extension reload for P1-05/P1-06: only if every node test passes and she is at the desk before 09:10; otherwise the extension as it runs today. After a reload, F5 GoCharting (the relay orphans).

**Tuesday 29 and Wednesday 30 Sep, she is told plainly:** rev 5 is still in force. Its latch froze a wrong FOLD all day on 28 Sep, and nothing can change it without her signature. On expiry day the Sep future's flow carries roll legs [I].

**Phase 2, this week, the engine in shadow:** P2-01 `fold.py`; P2-02 the log; P2-03 the wiring; P2-04 the gate; P2-05 `oi_prev`; P2-06 the backfill to disk.

**The gates (P2-04, `6-gate-table.md`, written after her commit of `6-amendment.md`):**
- design days 22–28 Sep and **unseen days 29 Sep (expiry) and 30 Sep (the roll)**, reported apart;
- trades split mechanical / hand-picked / sold / re-entry, each with exit, best, peak-before-exit and give-back;
- no FOLD on arrival; FOLD sounds ≤ 1/h; headline ≤ 1 change/h; condition chips ≤ 6/h ex-FLOW (median over the day's trades) with ZONE event-born and VPIN's 2-close exit;
- CAN'T CHECK printed over every data hole found on disk, and never HOLD inside one;
- the ZONE sentence agrees with its chip on every row;
- the expression prints both BUY and SELL across the marks (else it stays off the face);
- a post-close recompute of one live shadow day: zero `diverged` rows.

The gate can run Wednesday after the close. The earliest she can sign is Wednesday night.

**Phase 3, on her signature, the faces:** P3-01 DESK; P3-02 the retired rules out (tag `pre-rev6`), `/api/hold` from `fold.read`; P3-03 the panel patched and mark-my-trade; P3-04 the marks from the event log. **Rev 6 is in force from the first session this face is live;** that date goes into §1i.

**Phase 4:** P4-01 entry, P4-02 flat, P4-03 the expression, each forward-logged from day one.
**Phase 5, the cuts:** tabs, dead fields, board on F\*. One commit per group, tagged before.
**Phase 6, the missing reads, in shadow:** resting liquidity and big prints, failed auction, the next-weekly chain, VPIN from fills, the tick-post dispute, the pre-09:15 subscription last.

---

## 12. The ceiling, stated

- Eight trades on five days describe; thirty forward sessions decide. Counts, never rates.
- The expiry row was designed on one expiry trade. 29 Sep is its first unseen day; it needs 15 expiry afternoons to be judged, which is months.
- The log must answer first: on a trailed trade, does the held breach alone beat rev 6's rule (the one named alternative)? Does the backstop ever fire? Does a screen that says "nothing against you" let her hold longer than she did at 14:12 today?

---

## 13. Rebuttals

Everything above is accepted in substance. Where a fix was narrowed or replaced, the evidence is here.

**R1. Trader T5, "replay before registering": replayed tonight, and the calendar votes go.** The relative rule (wall ahead v her defenders, % of own OI over 6 min) reads BUY at A1 and H1 and SELL at the other six [M, `j6/expr_rel.py`, rule written in the file before running]. Two honest limits: it is in-sample on 8 marks, and "pressing" was counted as initiative (with initiative only, A1 reads EITHER). So the rule is registered, forward-logged, and shown on the face only if the gate finds it is not a constant on the unseen days too. The calendar votes are not kept: the expiry-day rule read SELL at A1 (+264) and expiry eve reads SELL at H2 (+97), her own trade [M].

**R2. Trader T2, the expiry afternoon: accepted, with the in-sample flag the reviewer did not state.** The +199 comes from the one expiry trade the rule was shaped on. It is registered because the mechanism is sound (expiring OI unwinds for reasons other than surrender; gamma makes V's; G stood 7B away for 74 minutes), and because it costs nothing elsewhere on 22 Sep (A2, S2 unchanged; R-A2 unchanged at −43 [M]). It has its own falsifier and its own kill row in the amendment.

**R3. Safety, "the same one-line guard on every POST": narrowed to `/api/frame`.** `/api/paper_fill` is PaperDesk's POST, kept by her order. Its sender path was not checked tonight; if it posts from a content script on a broker page, a `cross-site` refusal would break it silently. The guard therefore refuses only `cross-site` requests without the extension's `Origin`, on `/api/frame` now; `/api/paper_fill` follows once its sender is read.

**R4. Safety, the expiry-day header disclosure: said to her in words, not built tonight.** A ui-v2 change the night before expiry, to a face that rev 6 replaces, is risk without a decision attached. `6-for-mary.md` tells her plainly, and rev 6's header carries EXPIRY · Γ.

**R5. Safety, "calls and hold rows carry no code version": only for the new log.** Rev 6's rows carry `code_sha`. Adding a field to rev 5's and the calls' signed populations mid-window is itself a change to them; the rule "every restart happens after the close" keeps them separable by date, and it holds.

**R6. Trader T1, "a sentence, never a count": kept, and the four-reads clause is not a vote.** "Nothing behind you" does not fold her; "against you at your level" plus acceptance does. The screen shows the difference; her 14:12 exit is the case it is for.
