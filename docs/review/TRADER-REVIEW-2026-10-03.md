# TRADER REVIEW — the whole TapeMap tool, 2026-10-03

**The chair:** a 20-year Indian index-options prop trader (NIFTY / BANKNIFTY / SENSEX weeklies, intraday, buying and writing) who reads Python.
**The question for every piece:** does it help Mary make money, or avoid losing it, between 09:15 and 15:00 — or is it noise?

**How this was done (read-only).**
- No code was edited, no server was started or restarted, nothing was committed, nothing was written under `data/`. This report is the only file written.
- Throw-away scripts ran from the session scratchpad only: `exit_read.py` (`fold.read` at each of her 1 Oct exit seconds) and the data counts.
- Code was read at today's HEAD on `feature/operator-objects` (`55c8449`, committed this afternoon: DESK index switch, RECORD day picker, `_prem_at` basis fix, `live._upstox_bars` today-only).
- Evidence: `data/fold/*`, `data/hold/*`, `data/day_state/*`, `data/trigger_log.jsonl`, `data/chain/*`, `data/book/*`, `data/tape/*`, `data/calls/*`, `data/desk_log.jsonl`, `data/warmap/*`, the VPIN logs, and the 7-review replay (`docs/pro-tool/7-review-2026-10-03/REPLAY.md`: 45 replays, which reproduce the 30 Sep live log event for event).
- Her 1 Oct fill prices come from her tradebook (`Downloads/tradebook-ZVP031-FO.csv`, read-only). They are not in `data/`.
- **The 1 Oct engine words are a replay** (`src: import`, written 3 Oct). No mark reached the server that day.
- Tags: [M] measured from rows; [I] inferred. Rows are described; no rate is printed. (h) = hand-set threshold.

---

## 0. The prior findings, checked against today's code

| prior finding (source) | still true today? | evidence |
|---|---|---|
| The CVD rank ranks against itself 09:35–09:44 (AUDIT bug 1) | **Fixed** | `grounds.py:83-89` ranks only earlier changes, needs ≥ `MIN_PRIOR`, else "could not check" |
| The FOLD latch froze a wrong word all day (AUDIT §0) | **Changed, not gone.** Rev 6 keeps the FOLD headline frozen until I'M OUT; line 2 reads live ("still marked · now: …") | `fold.py:1020-1022`, `fold.py:1038-1040` |
| Moneyness judged on the chain's spot (AUDIT correction) | **Fixed in the live engine** (F*). **Still true** in `expression.py`, board, plan, validate | `fold.py:562-575`; `expression.py:66-74` |
| The OI baseline is the 09:15 candle, so gap-trapped inventory is hidden (bug 7) | **Still true.** No `oi_prev` anywhere (P2-05 not built) | `upstox_chain.py:72-77`; `grep oi_prev` finds nothing |
| `built = peak > 0` (bug 8) | **Still true** (it feeds the rev 5 loop and the expression) | `server.py:1716`, `server.py:1755` |
| The futures picker has no date filter (bug 13, the Wednesday dead future) | **Fixed.** On 30 Sep book, ux, senses and reader all name the Oct futures (NIFTY `NSE_FO\|48704`) [M] | `upstox_instruments.py:174-201` |
| VPIN's tick-rule classifier disagrees with the ladder (bug 11) | **Still true**, and VPIN is now one of the four votes | `vpin.py:137-167`; `fold.py:957-971` |
| SENSEX order flow is not a real read (bug 14) | **Half fixed.** `grounds.THIN_FLOW` blinds it (`grounds.py:56,151`), and so does xindex. **The live hold engine `fold.py` does not.** | §3 item 4 |
| The chain and the book start at about 09:17 (AUDIT §6) | **Still true.** First chain rows 09:17:03–09:17:19 on 29 Sep, 30 Sep and 1 Oct, though the server was up at 09:09 [M] | data counts, §7 |
| Rev 6 removes the "nine tabs you don't use" (6-for-mary) | **Not done.** 14 tabs, and **the app opens on Heat** | `App.tsx:1576` `useState<Tab>('Heat')`, `App.tsx:1596` |
| The expression shows only if its gate finds it is not a constant (blueprint §5, P4-03) | **Not built.** Rev e is computed and logged every 3-min close; no mounted screen shows it | `server.py:2521-2620`; `ui-v2/src/pro/*` has no expression; `HoldTab.tsx:363` (which showed it) is unmounted |
| Kill-list item 8: each I'M OUT while HOLD showed, with the premium at +20 and +40 min ("the question the tool exists for") | **Not built** | `6-amendment.md:156`; no code writes it |
| The `regime` shadow gate's `would_block` is always empty (PONYTAIL §4.3) | **Still true** | `regime.py:87,125`: no production caller passes `setups` |
| `/api/frame` guard, leak guard, contract stamps (blueprint P1) | **Done**, apart from: VPIN rows carry no contract (`inst: "NIFTY-FUT"` only), `trigger_log` has no `ik`, and fold rows have `ik: null` [M] | commit `9c0615e` |
| `_prem_at` priced through the wrong basis (7-review D2) | **Fixed today** | `fold.py:1064` |
| Midnight copies in `trigger_log.jsonl` | **Root cause fixed** (`55c8449`). 98 recent copies were removed on her word. **375 older copies (6 Aug–18 Sep) remain**, and there is a **new defect: 36 untagged SENSEX rows written 1 Oct 13:59:47** for bars up to 239 min earlier, on a grid shifted by one minute [M] | memory `hold-desk-review-2026-10-03`; §7 |

---

## 1. Overall rating: **4 / 10**

**Would I trade off this screen tomorrow? No.** I would keep the DESK open beside my broker on NIFTY as a hold-discipline aid, and ignore it on SENSEX.

**What is good.** The rev 6 engine is the most honest hold logic this repo has had:
- a structural give-up that only tightens;
- acceptance, not touch;
- an OI event sized against noise;
- three absence sentences that mostly hold.

**What fails.** On her real day it failed at the three things that pay.

1. **On 1 Oct it never knew she was in a trade.** She made 11 round trips and marked none. Nine were SENSEX 0DTE, and the DESK was NIFTY-only until this afternoon.
2. **At her exit second, the four reads could not tell a loser from a winner.**
   - The morning SENSEX calls, where the engine's own path led to −39 % to −57 %, read "behind you: flow, OI" or "behind you: zone, flow, OI".
   - The afternoon puts, which it held to +159 % to +198 %, read "behind you: flow, OI".
   - She banked −16 to +21 points on the calls and −12 to +23 on the puts [M, tradebook]. Her fast exits were right on the losers and wrong on the winners, and the screen gave her nothing to tell them apart (§3, item 2).
3. **On SENSEX, two of the four reads are blind or noise.**
   - VPIN is NIFTY-only.
   - FLOW is read off a future that printed a median 4 lots a minute.
   - The unit clock never has a prior session.

**Also missing:**
- Her own ZONE is not one of her four reads.
- The buy-vs-sell expression is silent on every live screen.
- Around the DESK sit 14 tabs (the app opens on Heat) that still print max pain, "PCR < 1 → Bearish lean", GEX, and an engine verdict that the research record scored below doing nothing. Its grounding check (`calls`) marks it CONTRADICTED more often than any other status on every index and day but one (SENSEX 29 Sep, where THIN leads) [M].

**What saves the 4.** The structural give-up held her afternoon puts to +159–198 %, and the 7-review's NIFTY zone sells to +55 … +92 % at 15:00. **The money is in the patience, not in the reads.** It is not uniformly better than her:
- On 29 Sep the engine's hold would have turned her +66 % exit into a +25 % FOLD.
- On the 1 Oct morning calls its path to the FOLD cost 39–57 % of premium, where she took −16 to +21 points.

---

## 2. Every read that reaches a screen

**Rating /10:** would a desk act on it, today, as built.
**"Fwd" (forward-scored):** **Y** = rows are logged before the outcome **and** a reader adjudicates the kill clock. **rows** = rows exist but nothing reads them back. **N** = no forward rows.

### 2a. The DESK (Validate tab = `/pro.html`), the floating window and the GoCharting panel: one engine, `fold.py` rev 6

| read | rating | decision it informs | fwd | verdict |
|---|---|---|---|---|
| Headline HOLD / PAST GIVE-UP / FOLD / CAN'T CHECK, plus give-up G and line 2 (`fold.py:785-809, 1019-1055`) | **6** | Stay or get out; what will take her out, said before it happens | rows. Outcome rows at +20 min (`fold_log.py:126`). **No reader:** RECORD drops them (`fold_live.py:486`) | **keep**; add the reader |
| Premium card: now, peak, given back, at G, at A, and on expiry intrinsic + time (`fold.py:1072-1086`) | **7** | What the give-up costs in rupees; a 0DTE bleed | n/a (display) | **keep** |
| ZONE row (`fold.py:893-920`) | **3** | Nothing she uses. It is a generic level map (prior H/L/C/POC, open, day H/L, 20-lot "trapped" fights, walls), **not her zone**. The zone-machine sentence is never fed in (`fold_live.py:202-203` has no `zone`). Its chip flipped 128 times across the 9 SENSEX replays on 1 Oct [M] | rows | **merge**: her zone machine in, the levels as its sentence |
| FLOW row: the newest fixed fight plus the tape word (`fold.py:921-941`) | **6 NIFTY / 1 SENSEX** | Is someone pushing against me? | rows | **keep on NIFTY, blind on SENSEX** (`grounds.THIN_FLOW` already does) |
| OI row: W building / stopped / off by 3σ√n (`fold.py:119-162, 942-956`) | **6** | Did my defenders leave? | rows | **keep**; fix the W swap (§3 item 6) |
| VPIN row: 10 fast buckets, signed (`fold.py:957-971`) | **4 NIFTY / 0 BANKNIFTY, SENSEX** | Is informed flow with me? | rows; VPIN's own kill clock has no reader (§4) | **keep on NIFTY** with one classifier, and say "NIFTY only" on the others |
| IF YOU WERE IN (`fold.py:1354-1375`) | **6** | What the trade would look like before she clicks | rows (`ifin`) | **keep**; make it the default flat face |
| FLAT: NEXT FIGHT, confirms, THE DAY, "SELLERS GAVE UP AT", re-entry (`fold.py:1162-1302`) | **5** | Where the next fight is | rows; re-entry is "0 of 3 in replay" | **keep**; re-entry stays marked unproven |
| RECORD (`fold_live.py:477-503`, `Record.tsx`) | **5** | After the close: did the word help her hold? | n/a | **keep**; add kill-list item 8 (§3 item 11) |
| Feed alarm band (`feed_health.py`, `FeedBand.tsx`) | **7** | Is the tape I am reading alive? Its SLOW state changed 22–28 times a day [M] | n/a (integrity) | **keep** |
| "flat by 15:00 · your practice" in amber from 14:45 (`Pro.tsx`, `panel.js:231`) | **7** | Her 15:00 practice, display only | n/a | **keep** |
| FOLD tone: 520 Hz in ui-v2 (`hold/store.ts:97-104`), 330 Hz ×2 in the extension (`main.js:89-93`) | **7** | Get out | n/a | **keep**, but make it one tone across both faces |

### 2b. The main app (`ui-v2`, 14 tabs) and its chrome

| read | rating | decision it informs | fwd | verdict |
|---|---|---|---|---|
| MACHINE strip: her zone machine, 3-min, 09:25 anchor, §1d gate (`App.tsx:1476`, `zone3.ts`) | **8** | Her setup: armed or triggered | **Y**, with two gaps: `trigger_log.py score` (`:962`) runs only by hand (`:1171-1175`), and the pass bar is still hers to state | **keep: her edge** |
| Signals tab: the forward record's rows, with the §1d chip (`SignalsTab.tsx`) | **6** | Reviewing her setup's rows | Y (the same two gaps) | **keep** |
| Trade tab: futures chart, zone on 3m, Hinglish chips, the rev 6 side panel (`trade/*`) | **5** | — | — | **her keep-order** |
| Trade tab legs / cross-index panel, off by default (`legs.tsx`; `reader.py`, `xindex.py`) | **3** | "Who is in this leg." The xindex word flipped 17–25 times a day [M] | rows; no outcome by design | **demote** to after-close until signed |
| War tab: walls over time (`WarTab.tsx`, `/api/oihist`) | **6** | When a wall was built and whether it still holds: OI read at levels | n/a | **keep** |
| Board tab (`BoardRev3.tsx`, `board.py`) | **4** | Fronts carried / built today, the defender. It has the `built = peak > 0` bug; its d2/u2 pockets come from the extension's **5-min** bands (`BoardRev3.tsx:391`) while the MACHINE strip uses the canonical 3-min; and it prints "FOLD" / "1ST FOLD" for an OI front unwinding (`fronts.py:338-370`), the DESK's exit word | n/a | **merge into WAR** |
| GlanceBar's **LOOK HERE** and state word (`App.tsx:236-253`, `data.ts:745-788`) | **2** | It steers her eye to the index with the most "backed" engine calls | calls rows; no reader | **cut** (the legs panel's xindex LOOK HERE is a second, different LOOK HERE) |
| ANSWER band on every tab except Board, Validate and Trade (`App.tsx:1768`): engine direction and timing chips, engine headline, **MAX PAIN · GEX · PCR · SQUEEZE**, and "changes if" levels that include max pain (`App.tsx:1349-1455`, `1643-1644`) | **2** | Nothing she uses. The engine stream as a signal scored −0.1 / −6.2 against a +4.1 do-nothing control (START-HERE §2). Its own grounding marks it CONTRADICTED most often [M]. The aggregates are what her thesis says not to read | calls rows; no reader | **cut the aggregates and the verdict chips** |
| Chain tab: "PCR < 1 → Bearish lean", "Max Pain: Expiry magnet" (`App.tsx:660-661`). A missing PCR renders as "0.00 · Bearish lean" (`data.ts:902`) | **1** | Retail framing; a missing value read as a bearish signal | N | **cut the stat cards** |
| Heat tab, **the landing tab** (`App.tsx:954, 1576`) | **2** | A spike radar | N | **cut**, or at least stop it being the default |
| Glass tab (`one/GlassBoard.tsx`) | **2** | A trial since 08-11 with no verdict | N | **cut** |
| Tape, Events and Map tabs (`App.tsx:456, 770, 868`) | **2** | Fossils (09-19 spec, PONYTAIL §2) | N | **cut** |
| OI Flow tab (`App.tsx:1109`) | **3** | Per-strike OI change | N | **merge into WAR** |
| Flow tab (`FlowTab.tsx`) | **3** | The day's order flow, after the fact | N | **demote** to RECORD |
| VPIN tab (`VpinTab.tsx`) | **3** | The toxicity percentile. The first percentile prints only at 09:44–10:07 [M] | rows; no reader | **merge** into the DESK detail |

### 2c. The GoCharting panel's other voices (`orderflow-desk` v0.3.1)

| read | rating | decision | fwd | verdict |
|---|---|---|---|---|
| The rev 6 face, the same as the DESK (`panel.js`) | 6 | as 2a | as 2a | keep |
| Signal tones at a zone reach: soft 660 / firm 880 / warn 330×2 (`main.js:77-86`; `signals.py` ballot; §1d `gate_sound`) | **4** | "Look now" | **rows:** `signals.py` writes nothing itself; the visits ride in the frame log, where `score_frame.py` fills their +1/+3/+6-bar cells. Nothing computes its "kill at n = 30 fired" comparison (`signals.py:36-41`) | **keep, but see §3 item 3**: on 1 Oct the §1d warn stood her down on the day's two best NIFTY trades |
| ZONE + FLOW fallback beep (`main.js:87-88`) | 1 | A fallback for a server that predates the signal object | N | **cut** |
| Dead-feed tone (`main.js:251-253`) | 7 | The tape went dead | n/a | keep |
| Chart marks from the fold events: fights, trapped, the G staircase, W/A (`overlay.js:229-285`) | 5 | Where the fights were | rows | keep (reads placed on her chart, not a redrawn chart) |
| The bell's tooltip, "one sound: FOLD" (`panel.js:232`) | — | It plays five kinds of tone (`main.js:84, 88, 93, 253, 94`) | — | fix the label, or cut down to two sounds |

### 2d. Computed every poll and reaching no decision (§4)

- `gate.py`: the seller's TRADE / **HALF SIZE** / NO NEW RISK. It reads "PATA NAHI" on every frame row on all three days [M], is rendered nowhere, and its vocabulary is a size, which this tool must never print.
- The rev 5 hold loop (`server.py:2760-2781`), with validate's GO/WAIT/NO, the plan and the rev e expression rows. The expression flipped its word 33–70 times per direction per day [M].
- The `regime` / `fuse` gear (`desk_log.jsonl`): flipped 44–68 times a day on NIFTY [M], with no screen.
- `regime.would_block` (always `[]`).
- `breadth` (imported at `server.py:37` and never used), `watch` (`frame.walls.watch`, never rendered), `impact` (`ux.impact`, never drawn), `ux_gate.session` (`ux.agree`, never drawn).
- `/api/senses` (about 1M rows a day in `data/senses/`), `/api/surface` and `/api/drag`: no reader in either face. The last two are her keep-order (PaperDesk).
- Her keep-order: `structure.py` (`structures` never drawn) and the `/api/contract` two-leg rotation (no caller).

---

## 3. TOP IMPROVEMENTS, ranked by money

Each item gives the problem with its evidence, how it costs her, and the smallest root-cause fix. Nothing here is built. Rule changes need her signature (the house order: after the close, on her word).

### 1. The engine must already be reading her trade before she clicks

**Problem.**
- The tool knows a trade only by MARK.
- On 1 Oct she made 11 round trips, each held 14 s to 4 min, and marked none. Nine were SENSEX, and the DESK was NIFTY-only (fixed in `55c8449`).
- A mark still takes CE/PE → BUY/SELL → strike → type the fill → MARK (`Mark.tsx`).
- IF YOU WERE IN is a toggle that needs a pick (`Pro.tsx`).

**Cost.** Every other improvement is worth zero on a trade the engine does not see.

**Fix.**
- Make IF YOU WERE IN the default flat face, for the ATM CE **and** the ATM PE of the active index, each read BUY and SELL. It already refreshes every 10 s when on (`fold_live.IFIN_EVERY_S`).
- A mark becomes one click on the leg she took, with the entry premium prefilled from the chain; she corrects it afterwards.
- "ATM" is the strike nearest F\*. Today the MARK slip takes the chain's spot ATM (`chain_live.py:270`, `pro/api.ts:131`, `pro/Mark.tsx:13, 20, 38`) while the engine reads the trade off F\*.
- After the close, the tradebook import (done by hand on 3 Oct, `src: import`) becomes a button on RECORD.
- No broker link.

### 2. Say PULLBACK vs GAVE UP in the headline clause, and say it for winners too

**Problem.**
- Her problem is exiting winners early.
- The engine's PULLBACK word lives only inside the FLOW row (`fold.py:884`). The clause under HOLD is a list of chips (`fold.py:1006-1017`).
- At her exit seconds on 1 Oct the clause could not separate her losers from her winners [M, `fold.read` at each exit second; fills from her tradebook]:

| trade | her exit (fill) | clause at that second | the engine's path after it [M] |
|---|---|---|---|
| SENSEX 72400 CE @ 237.25 | 10:01:26, +21.0 | HOLD · behind you: flow, OI | FOLD 11:26 at 143.6 (−39 %) |
| SENSEX 72400 CE @ 276.05 ×40 | 10:06:02, −16.05 | HOLD · behind you: zone, flow, OI | FOLD 11:26 at 143.6 (−48 %) |
| SENSEX 72400 PE @ 223.97 ×40 | 12:08:08, +16.0 | HOLD · behind you: flow, OI | FOLD 13:05 at 668.3 (+198 %) |
| SENSEX 72300 PE @ 224.1 | 12:11:09, +6.9 | HOLD · behind you: flow, OI | FOLD 13:05 at 580.3 (+159 %) |
| SENSEX 72300 PE @ 296.9 | 12:29:18, +23.1 | HOLD · behind you: zone, flow, OI | FOLD 12:41 at 274.0 (−8 %), then 580.3 at 13:05 |

- The same words appear on both kinds. What did the work was the structural give-up and the trail, and the clause names neither.
- On 28 Sep she left at +30 % with all four WITH; the put made +97 % (REPLAY §2).
- The GAVE UP draft says of itself: "It only cuts losers" (AMENDMENT-DRAFT §4).

**Cost.**
- The +159 % to +198 % rows above.
- The zone sells held to +55 / +77 / +81 / +92 % at 15:00 (REPLAY §1 rows 38, 41, 43, 44).
- **The other side:** on 29 Sep her +66 % exit beat the engine's +25 % FOLD, and on 1 Oct the engine's patience cost 94–132 points per unit on the morning calls. A clause that only ever says "hold" would hurt her. It has to name the defender's state.

**Fix (one function, display only).** In `_live_words` (`fold.py:1006`):
- Lead the clause with **"pullback · 22700 PE writers still there 119.4L · out only if 22769 is accepted"** when all of these hold, in both modes:
  - the tape word is PULLBACK;
  - W is building or stopped (not off);
  - the future is still at least w on her side of G (a pullback that has reached the give-up is not a pullback);
  - nothing is accepted past G.
- When W is off, lead with **"gave up 10:35 · 22700 PE writers −5.4 %"**.
- The amendment draft already writes the pullback line for losers; extend it to trailed trades.
- No new word, no new sound.
- **Replay it on the 1 Oct morning calls before it ships.** There the 72400 PE writers kept adding until 12:09 while the call bled from −29 % at the G touch (10:28) to −39 % at the FOLD (11:26). The "at least w from G" condition is what keeps the line silent there; the replay must show it does.

### 3. The §1d fade gate stood her down on the day's best NIFTY trades: add "under pressure"

**Problem.** §1d marks a fade illegal when the defending front stops building (`fronts.py:233-280`), whatever way price went. On a down day the call writers took profit as price fell away from them, and the gate read that as surrender.

NIFTY zone entries, 29 Sep–1 Oct [M: `trigger_log.jsonl` `gate`; outcomes from the IF-YOU-WERE-IN rows in REPLAY §1]:

| entry | gate | why | long ATM PE / CE at 15:00 (high) |
|---|---|---|---|
| 29 Sep 12:18 SELL | illegal | CE 22700 gave up its build at 10:59 | +28 % (+110 %) |
| 30 Sep 09:30 SELL | **legal** | CE 22700 still building | +31 % (+49 %) |
| 30 Sep 10:27 SELL | illegal | CE 22700 gave up its build at 09:57 | +55 % (+73 %) |
| 30 Sep 13:03 SELL | illegal | CE 23000 stopped building at 12:22 | +77 % (+95 %) |
| 1 Oct 10:12 SELL | illegal | CE 22700 gave up its build at 09:58 | +81 % (+196 %) |
| 1 Oct 10:39 SELL | illegal | engine says NO FADE — negative gamma, continuation only | +92 % (+213 %) |
| 29 Sep 09:39; 30 Sep 11:00, 11:27, 14:45; 1 Oct 13:00 BUY | illegal | PE writers gave up | +13, −34, −28, −2, +3 % |

- The gate is right about the fades against the day's move and wrong about the sells with it.
- The NO FADE veto is side-blind by design (`fronts.py:57-61`), so negative gamma vetoed a sell that agreed with continuation.
- The extension turns an illegal gate into the `warn` tone (`signals.py:566-573`, `main.js:83-85`): two low notes meaning "stand down", sounded on trades that went +81 % and +92 %.

**Cost.** Six rows, three trending days, one regime. They are rows, not proof, and her 5-year record outranks them. But a wrong stand-down tone costs the whole trade.

**Fix (an amendment she signs; §1d's rows stay exactly as logged).**
- Count a defender as gone only if its OI came off **while price was coming at it**. This is the same condition 2 her GAVE UP draft uses.
- Make the NO FADE veto side-aware. Negative gamma says continuation, so it should veto only the fade that bets against the running move (a d2 BUY in a falling tape), not the u2 SELL that sells a bounce inside it.
- Until it is signed, print the direction in the reason ("CE 22700 writers covered as price fell away — profit, not surrender"), so the `warn` tone is not read as a verdict.

### 4. SENSEX and BANKNIFTY parity: two of the four reads are blind, and the clock never has a prior session

**Problems.**
- **VPIN is NIFTY-only.** It is computed for `NIFTY-FUT` only (`server.py:812-836`) and pushed to the engine only for NIFTY (`server.py:881`), and `fold.py:285` filters `inst == f"{idx}-FUT:fast"`. On SENSEX and BANKNIFTY the VPIN row is CAN'T CHECK every minute of every day. It read "0 of 10 VPIN buckets" at all 9 SENSEX exits on 1 Oct [M].
- **SENSEX FLOW is read off a thin future.** On 1 Oct the SENSEX future printed a median of **4 lots a minute** (p90 16; 52 zero-volume minutes; 3,137 lots all day), against 151 a minute for NIFTY [M]. Fold's bucket there was 27 lots. So "buyers won 09:49 at 72951" and "20 lots of sellers trapped" are what sat behind the calls that went to −48 %.
  - `grounds.THIN_FLOW` (`grounds.py:56`) and xindex already blind this; `fold.py` does not.
  - The reader tagged 34 of its 46 SENSEX legs `thin` that day [M].
- **There is never a prior session.** The prior pool is listed from **GoCharting tape files** (`tape_log.prior_days`, `tape_log.py:87-96`), which exist only for NIFTY (11 files; none for SENSEX or BANKNIFTY) [M].
  - `fold_live.py:428` then builds the sessions from the **book** files, and those exist for SENSEX from 22 Sep.
  - So every SENSEX and BANKNIFTY day runs on "the day's own first 15 minutes (not causal before 09:30)" [M: `units.bucket_src` at all 9 SENSEX exits].
- **Acceptance counted in lots is slow on a thin future.** On the 72400 CE marked 10:00:48, G (72938) was touched at 10:28:23 with the call at 168.9 (−29 %). The 27 lots that make "accepted" took until 11:26:25, when the call was at 143.6 (−39 %) [M, `fold_SENSEX_2026-10-01.jsonl`].

**Cost.** Nine of her 11 trades on 1 Oct were read with one honest read (OI) and two that were blind or noise. The "behind you: flow" on the losing calls was noise, and the stop came 58 minutes after the touch.

**Fix.**
- **(a)** Make `tape_log.prior_days` list `data/book/book_<IDX>_*.jsonl(.gz)`, the files the pool is actually built from. One line.
- **(b)** In `fold.py`, honour `grounds.THIN_FLOW`, as blueprint §4.10 already specifies:
  - FLOW reads "could not check: SENSEX future, n lots this bucket";
  - G comes from the wall + w;
  - acceptance is price held beyond G for SENSEX's own median bucket time, not a lot count.
- **(c)** On the other two indices, the VPIN row says "NIFTY future only", not "0 of 10 buckets".
- **Replay 1 Oct before (b) is signed.** The same thin-tape "sellers won" fights trailed G twelve times down the afternoon move that held the puts to +159–198 % (`fold_SENSEX_2026-10-01.jsonl`, 12:22–12:58 resets). A wall-based G must not lose that.

### 5. Sign GAVE UP (at entry), with one SENSEX caveat

**Problem.**
- At entry, rev 6 folds only on acceptance past G (`fold.py:795-796`). OI and VPIN against change the clause, never the word.
- There are 224 minute rows of HOLD with 2+ reads against, price against her and the premium bleeding (REPLAY §3 D1).
- Hers on 30 Sep: HOLD with OI and VPIN against from 10:44:11 to 11:11:11; FOLD at 11:16:33 at 127.55 (−23 %), at the local low [M, `fold_NIFTY_2026-09-30.jsonl`].
- **The rev 5 window, logged alongside, folded at 10:40 at 146.7** (`hold_2026-09-30.jsonl`, "payers and holders against") [M]. That is one row in which the engine being retired beat the new one by 36 minutes.

**Cost.** 30 Sep −23 → −14 %; 25 Sep −10 → −3 %; A2 −42 → −15 % (AMENDMENT-DRAFT §3). It cuts no trade that rev 6 held to a gain.

**Fix.**
- The draft as written (`docs/pro-tool/7-review-2026-10-03/AMENDMENT-DRAFT.md` §2).
- **Caveat for SENSEX:** its condition 3 never blocks there, because FLOW and VPIN are blind. On SENSEX it is OI plus price only. Until item 4 lands, SENSEX FLOW is **not** blind in `fold.py`, and its noise would block the rule.

### 6. Stop the W swap from erasing "OI against" in the same second

**Problem.**
- When her side wins, G re-sets and `_new_epoch` re-picks W (`fold.py:674-682` → `_pick_W` at `638-654`). That withdraws a live OI event.
- 30 Sep 11:11:11: "buyers won at 22826" moved G 22769 → 22803 at −15 %.
- W swapped from 22700 PE (119L) to 22750 PE (37L), and OI flipped AGAINST → WITH.
- The FOLD came five minutes later, at the local low (REPLAY D4; `fold_NIFTY_2026-09-30.jsonl` 11:11:11).

**Cost.** A false "OI with you" in the five minutes that mattered. The same swap happened on Z 09-30 11:00 and on Z 09-22.

**Fix.** In `_new_epoch`, keep W, and its live event, while the old W still lies between F* and the new G. Re-pick only when price has gone w through it. One condition.

### 7. Put her zone into her four reads

**Problem.**
- Her rule is "zone, order flow, OI, VPIN". The ZONE chip is a generic level map (`fold.py:893-920`).
- The zone machine's own state never reaches the engine. `fold.State` reads `inputs.get("zone")` (`fold.py:192`), but `fold_live.Engine.inputs()` never sets it (`fold_live.py:202-203`). So `rows.zone.machine` (`fold.py:1140-1141`, `Desk.tsx:50`) is always empty.
- The plumbing already exists:
  - `server._hold_zone` (`server.py:2188`): the latest trigger and arm, with their §1d gate and whether they agree with the trade's direction;
  - `server._xindex_zone` (`server.py:2224`), already fed to xindex.

**Cost.** In a long CE, an opposite u2→u3 SELL trigger (her own setup, against her) never reaches the hold read. Her validated edge is absent from the very decision she struggles with.

**Fix.**
- Pass a `zone_fn` seam into `fold_live.run`, as `xindex_live._CFG["zone"]` is.
- At reply time, put `_hold_zone(idx, day, now, d)` into `rows.zone.machine`. Display only.
- Making it the ZONE vote is an amendment for her signature: an opposite trigger with a legal gate = AGAINST; her side armed or triggered = WITH (as AUDIT §4 wrote it).

### 8. The expression: give her the numbers, not a silent model

**Problem.**
- She buys or sells by condition, so the tool should pick the leg.
- Rev e (`expression.py`) is computed at every 3-min close and logged, but shown on no screen.
  - It centres ATM on the chain's spot (`expression.py:66-74`).
  - It still votes REGIME (the trend box) and ROOM (the session-high line), both removed by rev 6.
  - Its word flipped 33–70 times per direction per day [M, `hold/expr_*`].
- Rev 6's replacement (BUY when the wall ahead loads slower than her defenders, blueprint §5) is not built.

**Cost.**
- The choice that matters most for a writer at the money, "sell the other side when the move will be slow", has no read.
- The drag (the buyer's tax, `drag.py`; measured at 33 / 37 / 88 % on 19 Aug) is computed and served at `/api/drag`, but shown only to PaperDesk.

**Fix.**
- On IF YOU WERE IN, print three numbers and no word:
  - the wall ahead's OI pace over 6 min;
  - her defenders' pace over 6 min (both from fold's own `Aw` / `Ww` series);
  - the drag now.
- The word (BUY / SELL / EITHER) waits for the gate rev 6 already wrote.
- Stop the rev e logging (§4).

### 9. Read the open: OI from yesterday's close, and the first two minutes

**Problem.**
- The OI baseline is the 09:15 candle (`upstox_chain.py:72-77`), so the gap's covering sits inside the baseline. On 28 Sep that hid 23100 PE −26.3L and 23000 PE −10.9L (AUDIT bug 7).
- The chain and the book start at 09:17 even with the server up at 09:09 [M]. Chain backfill covers only 09:15/09:16, and BANKNIFTY had none on 30 Sep [M].

**Cost.** Her anchor is 09:25. The 09:15–09:25 window is where trapped overnight inventory, her fuel, is largest, and the screen is blind or wrong in it.

**Fix.**
- `oi_prev` (blueprint P2-05): the previous session's last chain snapshot, **same expiry only**, saved at 15:30 and loaded at start. A missing value reads "could not check", never 0.
- Resolve and subscribe before 09:15, centred on the future's last price.

### 10. Re-centre the chain when price walks to its edge

**Problem.**
- The chain is resolved once a day, 8 strikes each side of the 09:15 spot (`upstox_instruments.py:65`, `upstox_chain.py:71`).
- On 1 Oct the SENSEX band was 71500–73100 all day, while spot traded down to 71300.66 [M, `chain_SENSEX_2026-10-01.jsonl`].
- NIFTY's low (22218) sat 1.4 strikes above its band's floor.

**Cost.** On a trend day, exactly when her puts were running, the strikes at and beyond F* drop off the chain. The wall ahead, "at A" and the ATM premium go blind.

**Fix.** When F* comes within 3 strikes of the band's edge, re-resolve and add the new keys (keep the old ones subscribed). Log each re-centre as a row.

### 11. Measure the one thing the tool exists for: "out while HOLD"

**Problem.**
- Kill-list item 8 is not written anywhere: "each trade where she pressed I'M OUT while HOLD showed, with the premium 20 and 40 minutes later … does it help her hold?" (`6-amendment.md:156`).
- The fold outcome rows (`fold_log.py:126`) are excluded from RECORD (`fold_live.py:486`), and no tool tallies them.

**Cost.** Without it, nobody can say after 30 sessions whether the DESK made her money. 1 Oct alone has 11 such rows, and 29 Sep shows they cut both ways.

**Fix.** In `past_record` (`fold_live.py:477`), for each trade:
- the word and the clause at her exit second;
- the premium at +20 and +40 min, from the logged rows;
- the engine's first FOLD after her exit, with its time and premium.

One line on RECORD, counts only.

### 12. One kill-clock reader for every shadow log

**Problem.** Twenty modules declare a kill clock; code adjudicates none of them [M, duplicates audit and data counts]:
- **No reader at all:** `vpin_log` ("pct ≥ 0.90 must precede a range expansion", 23 sessions logged); `calls/` (grounds); `desk_log` (`direction.py`'s FORCED vs LEANING, 25 sessions); `warmap/` (25 sessions); `xindex/`; `reader/`; `senses/`.
- **The signals ballot (kill at n = 30 fired):** its outcome cells are filled in the frame log (`score_frame.py`), but nothing computes the comparison its kill rule needs.
- **`regime.would_block`:** always `[]`.
- **Fold outcome rows:** written, but never tallied.

**Cost.** Modules that should die keep running and keep printing.

**Fix.**
- One `tools/kill_clocks.py`. For each log: sessions so far, cases so far, the falsifier's two columns as counts, and "inconclusive" under 15. Run it after the close.

---

## 4. CUT LIST

**Not on this list: her keep-orders.** The Dhan / Upstox fallback files and `start.bat`; `structure.py`, `band_rotation.py` (including the two-leg stack) and `contract_pair.py`; the Trade tab futures chart; PaperDesk's `/api/surface`, `/api/drag` and `/api/paper_fill`.

**A critique under her keep-order.** The two-leg rotation and OI-deceleration confirmation (`band_rotation.py:388-430`) is the half of her validated setup ("the pair must rotate", "front-runs the OI peak") that no screen shows:
- `/api/contract` has no caller.
- The live zone record is index-only, with `confirm` always UNKNOWN (`band_rotation.py:709-727`).

Keep it. But either show it on the MACHINE strip, or have the strip say it is not checked.

| cut / demote | why | what replaces it | risk |
|---|---|---|---|
| **The rev 5 hold loop** (`server.py:2760-2781`, `_hold_tick` `2383`): its `hold.py` window, `validate.py` GO/WAIT/NO, `plan.py`, and `expression.py` rev e logging | A second hold engine with no face (HoldTab and HoldWindow are unmounted). It stopped on BANKNIFTY at 09:44 on 30 Sep [M]. It wrote 495 rows on the 2 Oct holiday [M] | rev 6 `fold.py`, plus GAVE UP (which restores what rev 5's "payers and holders against" did on 30 Sep) | Its signed forward populations stop growing; the rows on disk stay. Tag before the cut |
| **ANSWER band aggregates and verdict chips** (`App.tsx:1349-1455`), and max pain as a level (`1643-1644`) | Max pain, PCR, GEX and SQUEEZE are aggregate reads her thesis rejects. Missing values render as readings ("Neutral", "Low"; `data.ts:927-929`). The engine verdict stream scored below doing nothing | Price, and "changes if" on walls from the one wall ranking | None for decisions |
| **GlanceBar LOOK HERE and the engine state word** (`App.tsx:236-253`; `data.ts:745-788, 1148-1167`) | It points her eye at the index with the most "backed" engine calls | The DESK index switch | None |
| **Chain tab stat cards** (`App.tsx:658-664`) | "PCR < 1 → Bearish lean"; "0.00" when the chain is missing | WAR | None |
| **Heat, Glass, Tape, Events and Map tabs**; make the DESK the default tab | No moment of her day uses them (blueprint §8.1, PONYTAIL §2–3). The app opens on Heat (`App.tsx:1576`) | DESK, WAR, Trade, Signals | She may open one by habit; ask once |
| **Board and OI Flow → WAR; VPIN tab → DESK detail; Flow tab → RECORD** | Four screens for one OI question. The Board's d2/u2 is the 5-min band, not her 3-min, and its "FOLD" (an OI front unwinding) collides with the DESK's exit word; until merged, call it "UNWOUND" | WAR, DESK | Low |
| **`gate.py`** (`frame.py:195`) | "PATA NAHI" on every frame row on all three days [M]; rendered nowhere; its vocabulary is a size (HALF SIZE) | nothing | None |
| **The `regime.py` shadow gate field** (`would_block` always `[]`, `regime.py:87,125`) | Its kill clock can never adjudicate | nothing (`direction.py` and `fuse.py` import regime, so cut only the gate field) | Low |
| **`breadth` import, `watch`, `impact`, `ux.agree`, `/api/senses`** | Computed every poll or frame, never rendered. `data/senses/` grows by about 1M rows a day [M] | nothing | Low. Keep `sweep` (it feeds the DEPTH vote) |
| **ZONE + FLOW fallback beep** (`orderflow-desk/src/shell/main.js:87-88`) | A fallback for a server that predates the signal object; a second sound class | the signal tone | None |
| **The 375 older midnight copies in `trigger_log.jsonl`** (6 Aug–18 Sep) **and the 36 late SENSEX rows of 1 Oct 13:59:47** | Copies, or untagged late rows; they pollute the zone population | the file without them, after a backup | **Her word first.** 21 and 22 Aug (0 of 9 and 2 of 7 match) need a look. The 13:59:47 rows' cause is not in the log |

---

## 5. Her edge in the code: do not touch

- **The zone machine:**
  - `band_rotation.run_states`, with `ANCHOR_MINUTE` 09:25 and the 3-minute `SCORED_INTERVAL`;
  - reaching d2 is the event, it fires on the reversal, and the re-fire lock stays;
  - **`data/trigger_log.jsonl`**, the one irreplaceable file;
  - `trigger_log.py`'s refusal to print a rate.
- **§1d, the fade gate, as a logged field** (`fronts.py`). Nothing is suppressed, so the population stays clean. Improvement 3 is an amendment she signs, not an edit.
- **The structural give-up that never loosens, and acceptance rather than touch** (`fold.py:610-624, 711-753`). This is what held her 1 Oct puts to +159–198 %.
- **The OI event sized against noise** (3σ√n, n ≥ 3, ≥ 3 %; `fold.py:146-154`). It is the only code that tells "writers left" from a wobble.
- **F\*, moneyness on the options' own forward** (`fold.py:562-575`), and `_prem_at` priced through the basis (`fold.py:1064`).
- **The premium is never an input to the verdict**; it is only displayed (`fold.py:1072-1086`).
- **The house rules on the screen:**
  - the three absence sentences and the `[M]` / `[I]` tags;
  - CAN'T CHECK as a fourth headline;
  - the feed alarm;
  - **no order path and no size**;
  - LIGHT only.
- **`ladder.side_of`**, the ladder's aggressor side. VPIN should be fed from it.
- **The 15:00 reminder, as display only.**

---

## 6. What a pro desk would add for her style (grounded in her method only)

- **0DTE mornings (SENSEX on Thursday, NIFTY on Tuesday).**
  - The engine's give-up was far from her 1 Oct morning calls: its path reached −39 % to −57 % of premium.
  - On 29 Sep (NIFTY 0DTE) her +66 % exit beat its +25 % FOLD [M].
  - The expiry-afternoon trail only starts at 13:30 (`fold.py:47`).
  - She refused a premium stop, so the honest fix is display: on expiry day, print "at your give-up: −48 %" in the headline line at the mark, not only in the premium card.
- **The open, 09:15–09:25:** improvements 9 and 1. Yesterday's walls (same expiry), who the gap trapped, and IF YOU WERE IN from 09:17.
- **The roll and the expiry week:**
  - The futures-OI quadrant is blinded in expiry week (`grounds.roll_why`, `grounds.py:60-71`).
  - The contract stamp and the prior-pool cut are in.
  - The 30 Sep roll read the Oct contracts [M]. Keep all of this.
- **Event days.** No calendar exists (`gate.py` says so). A pro desk marks RBI, budget and CPI mornings by hand. A one-line `data/events.json` she edits, printed in the DESK header, is enough. Never a gate.

---

## 7. Data-integrity risks that would make a read lie at 09:15

1. **The daily token** expires at 03:30, and a dead token looks like a quiet market. `/api/health` names the broker; keep the header showing it.
2. **Missing values rendered as readings** before the first chain arrives (~09:17):
   - PCR "0.00 · Bearish lean" (`data.ts:902`, `App.tsx:660`);
   - GEX "Neutral" (`data.ts:927`);
   - squeeze "Low" (`data.ts:929`);
   - regime "Neutral hedging" (`data.ts:845`);
   - the GlanceBar "LIVE" dot shows regardless (`App.tsx:397-400`).
   These break rule 6 ("a missing value is never a zero").
3. **The chain and the book start at about 09:17**, and the OI baseline is 09:15 (improvement 9).
4. **The SENSEX and BANKNIFTY prior pool is empty every day** (improvement 4a), so their units are non-causal before 09:30.
5. **The chain band is fixed at the 09:15 spot** (improvement 10).
6. **VPIN:**
   - the tick rule disagrees with the ladder (AUDIT bug 11, still open);
   - its rows carry no contract key;
   - its first percentile arrives at 09:44–10:07 [M].
7. **The forward record:**
   - 375 older midnight copies are still in it;
   - 36 untagged SENSEX rows were written at 13:59:47 on 1 Oct for bars 12:10 onward, on a grid one minute off the live rows;
   - `trigger_log` rows carry no `ik`.
8. **The expiry flag comes from the chain's own `expiry`** (`fold_live.py:283-291`). It worked live on 29 Sep (FOLDs at 13:34:29 and 13:45:20 under the expiry-afternoon row) [M]. But the marked trades carry `expiry: null` in the fold rows [M], so the record cannot show which contract a trade was read against. Print the chain's expiry in the DESK header.
9. **Logs written on non-trading days:**
   - `hold/side_2026-10-02` (495 rows, a holiday);
   - `xindex` on 2 Oct and on Saturday 3 Oct;
   - frame rows stamped 02:26–03:xx and 09:01/09:08, labelled with the previous day;
   - a torn line (6879) in `frame_2026-10-01.jsonl` [M].
   A post-close restart or a holiday must write nothing.

---

## 8. One market, many words: duplicates and contradictions that reach a screen

| concept | who computes it, and how | can they disagree in the same minute? |
|---|---|---|
| **"The wall": 9 rules in code, 6 on a screen** | fold G / W / A: current OI, 19 nearest **F\***, the nearer of the top 2 (`fold.py:542-560, 638-654`; DESK, Float, Trade, extension) · §1d fronts: session-**peak** OI, 9 nearest **spot**, top-1 for the gate (`fronts.py:105-174, 233-303`; Signals chip, extension warn tone, ANSWER band) · `board.nearer`, **either side of spot** (`board.py:77-80`; Board) · the Board's "next wall" (`board.py:265-285`) · GEX walls RES/SUP (`gamma.py:184-193`; Tape tab, ANSWER band) · CE_WALL / PE_WALL, the heaviest OI anywhere (`levels.py:124-137`; War) · CEILING / FLOOR / CONTESTED (`chain_metrics.py:555-576`; Events) · plan rung and expression WALL (logged only) | **Yes.** Spot against F\* (24–46 pts apart on 28 Sep), 9 strikes against 19, peak against current OI: the DESK and the Board can name different strikes in the same minute. §1d keeping its own is her order; the rest should collapse to fold's one ranking |
| **OI building / leaving** | §1d BUILDING / STALLED / UNWINDING: a 15-mark slope against its own peak (`fronts.py:95-102`) · fold building / stopped / off: 3σ√n since the mark (`fold.py:119-162`) · `board.paying` relabels BUILDING when ≥ 5 % under peak (`board.py:84-99`) | **Yes.** After a 3σ drop and a partial rebuild of more than 5 % of the peak, §1d reads BUILDING while fold stays "off" until a new peak: the Board says "still adding" while the DESK says "AGAINST: writers left". On 30 Sep 22700 PE they agreed within 4 minutes (§1d 10:31, fold 10:35:05) [M] |
| **Her setup's state** | the MACHINE strip WAITING / ARMED / TRIGGERED / TRADE MEIN / BAAHAR (`machine.ts:30`) · the extension's signal ARMED / LIVE / REACHED / SPENT / STOPPED / VOID (`signals.py:392-416`) · xindex ban sakta / chal raha / ho gaya | Two vocabularies for one machine; "ARMED" means different things in each |
| **d2 / u2** | the MACHINE strip on 3-min bands (`zone3.ts:55`) · the Board's pockets on the extension's 5-min bands (`BoardRev3.tsx:391`, `server.py:3087`) | **Yes.** Her canonical interval is 3-min |
| **Order-flow side** | the ladder's **quote rule** (`ladder.py:40-51`) feeds fold FLOW and grounds · VPIN's **tick rule** (`vpin.py:13, 137-167`) feeds the DESK's VPIN chip · grounds' CVD rank on 5-min bars · reader WHO per leg · three futures-OI quadrants (`grounds.py:131-141`, `data.ts:826-832`, `frame.py:263-268`) | **Yes.** Two classifiers on one future (AUDIT bug 11: at 09:56:37 on 28 Sep the ladder booked BUY and VPIN booked the bucket SELL); five windows (10 buckets, 15 min, 6 bars, per leg, 120 s) |
| **Regime** | "PIN" means four things: calm σ (`regime.py`), both nearer fronts writing (`board.py:335-353`), gamma walls (engine PINNED), trendbox PIN/CHOP · engine AMPLIFIED (Tape tab) vs GEX POSITIVE (Glass) | **Yes.** The Board can read PIN/CHOP while the ANSWER band reads GO |
| **ATM / moneyness** | fold's F\* (`fold.py:562-575`) · a second, different F\* for the extension's mark slip (`server.py:2876-2887`) · **the DESK's own MARK slip uses the chain's spot ATM** (`chain_live.py:270`, `pro/api.ts:131`, `pro/Mark.tsx:13, 20, 38`) · board, expression, hold, frame, §1d, watch: spot | **Yes.** The DESK prefills "ATM" off spot and then reads the trade off F\* |
| **The in-trade word** | rev 6 HOLD / PAST GIVE-UP / FOLD / CAN'T CHECK (on screen) · rev 5 HOLD / WATCH / FOLD / PATA NAHI (logged, no screen) | **Yes:** 30 Sep, rev 5 FOLD at 10:40, rev 6 HOLD until 11:16 [M] |
| **Same word, different thing, same screen set** | **FOLD**: the DESK's exit vs the Board's "1ST FOLD" (an OI front unwinding, `fronts.py:338-370`) · **STALLED**: an OI front vs the feed · **trapped**: four meanings (fold's fixed fight, the GoCharting P mark "chhota trap", band_rotation's CLEAR/SUSPECT, engine TRAP-SPRUNG) | **Yes.** "FOLD" on the Board while she holds is the worst of these |

**State vocabularies that reach a rendered screen today: 29.**

- **The DESK and its faces (`fold.py`):** HOLD / PAST GIVE-UP / FOLD / CAN'T CHECK · WITH / AGAINST / QUIET · BUYERS / SELLERS / QUIET (flat) · FAILED / PULLBACK / TIRING / BEHIND · won / absorbed / disputed / trapped / released (with INITIATIVE / ABSORBED / PRESSING) · the feed LIVE / SLOW / STALLED / DEAD (`feed_health.py:37`).
- **Her setup:** WAITING / ARMED / TRIGGERED / TRADE MEIN / BAAHAR (`machine.ts:30`) · CONFIRMED / UNCONFIRMED / UNKNOWN with CLEAR / SUSPECT (`band_rotation.py:1191-1192`) · LEGAL / NO FADE / gate ? (`SignalsTab.tsx:997-1001`) · the extension's ARMED / LIVE / REACHED / SPENT / STOPPED / VOID (`signals.py:392-416`).
- **The ANSWER band:** GO / READY / STAND ASIDE / CAUTION / WAIT and MOVE RUNNING / STALLING / SPENT (`engine.py:1072, 1143-1171`) · BULLISH / BEARISH / NEUTRAL / UNGROUNDED (`data.ts:770-771`) · BACKED / THIN / CONTRADICTED / PATA NAHI (`grounds.py:33-35`) · longs building / shorts covering / shorts building / longs exiting (`grounds.py:136-140`).
- **The Board (seven):** pressing / leaning · BUILDING / STALLED / UNWINDING · still adding / stopped building / giving back / never built · PIN / TREND UP / TREND DOWN / BOTH LEAVING · trendbox UP / DOWN / RANGE, TREND / PIN-CHOP, BULLS / BEARS / NEITHER · CONFIRMS / DIVERGES / SPLIT · FOLD / 1ST FOLD.
- **Other tabs:** FLOOR / CEILING / PINNED / AMPLIFIED (Tape) · POSITIVE / NEGATIVE / OUT-OF-ZONE (Glass) · Fresh shorts building / Longs adding / Positions covering (Tape, `data.ts:826-832`) · HIGH / ELEVATED / NORMAL / CALM (VPIN tab) · the Events kinds with CEILING / FLOOR / CONTESTED · the Trade chips ("top / bottom ban sakta", "chhota trap") · the reader's TREND / RANGE / BREAKOUT and WHO · xindex's ban sakta / chal raha / ho gaya.

Another ten are computed and shown nowhere: rev 5's word, GO / WAIT / NO, the expression's six, the plan's, the hold side, the gear, direction, oi_dwell, sequence, and `gate.py`.

**After the §4 cuts, about eight remain:** the in-trade headline, the in-trade and flat chips, the tape words, the fight marks, the feed, the MACHINE words and the §1d chip, plus the reader's words behind a toggle.

---

## 9. Noise budget (rows, not rates) [M]

| what | 29 Sep (expiry) | 30 Sep (roll) | 1 Oct |
|---|---|---|---|
| Her setup: `trigger_log` zone arms + entries | NIFTY 7 + 2, SENSEX 8 + 3 | NIFTY 28 + 7, BANKNIFTY 15 + 4, SENSEX 15 + 5 | NIFTY 15 + 3, BANKNIFTY 18 + 5, SENSEX 33 + 8 (plus 36 late rows) |
| FOLD events logged (a sound only while she is still marked; 29 Sep's three all came after her 09:35 exit) | NIFTY 3 | NIFTY 2 | replay only: NIFTY 2, SENSEX 23 |
| Fold chip flips Z / F / O / V | 38 / 16 / 6 / 15 (one trade, counted to the close; ex-FLOW 9.1 an hour against rev 6's budget of 6, which counts only while she is in) | 3 / 8 / 6 / 11 | SENSEX 128 / 76 / 36 / 9 over 9 trades |
| Engine-call status changes (`calls/`, the ANSWER band) | 80 / 98 / 86 (N / B / S) | 88 / 89 / 73 | 79 / 92 / 94 |
| Gear flips (`desk_log`, no screen) | NIFTY 44 | 55 | 68 |
| Rev e expression word flips per direction (no screen) | NIFTY 57 / 66 | 58 / 59 | 33 / 59 |
| xindex word flips (legs panel, off by default) | not on disk | 25 / 17 / 19 | 17 / 18 / 21 |
| Warmap transitions (no screen) | 773 | 873 | 1,072 |

The DESK headline is quiet: FOLD 2–3 times a day on NIFTY. The noise sits in the chips (ZONE most of all, because it re-reads at every born level), in the ANSWER band, and in the shadow machinery nobody sees.
