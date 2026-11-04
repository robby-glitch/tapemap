# Option order flow: the design (2026-11-05)

Status: DESIGN, approved by the operator on 2026-11-05 ("Yes, write the spec") after two rounds: Fable's trader-and-quant
brainstorm (`docs/optflow/brainstorm/2026-11-05-option-orderflow-trader-quant.md`) and Opus's attack on it
(`docs/optflow/brainstorm/2026-11-05-opus-attack.md`). Where the two disagree, this document says which won and why.
Conventions as the repo's: **[M]** measured, **[I]** inferred or chosen; counts, never rates; a missing value is never a
zero; no order path. Nothing here changes a registered rule (§1b–§1s); new reads are pre-registered before they are counted.

---

## 1. What this is for, in her words and in ours

Her words (4–5 Nov): "3 mins is late", "I like scalping as well", "I want to use it in the opening trade", "how to filter
noise from real moves", "I kind of like the confidence %".

Ours: the option record answers **who is behind a move** (writers running, writers defending, buyers chasing) and **whether
resting at a premium is about to be picked off**. The futures tape remains the timer (effort per point is the one read that
survived the 291-row audit). The tool must serve three horizons with three clocks, never one number:

| clock | question it answers | latency | source |
|---|---|---|---|
| **frame** (seconds) | is this strike being lifted or hit right now, and is posting here toxic | ~1–7 s | Upstox v3 socket, `full` mode (new recorder) |
| **minute** | where in the premium is the push absorbed or breaking | 1–2 min | Dext footprint, `data/dext/` (exists) |
| **close** (2–3 min) | who opened or closed: WRITE / BUY / COVER / DUMP per strike, the group word, walls, squeeze, pin | 2–4 min | chain OI × Dext delta (exists as studies; no module) |
| **lens** (slow) | which reads are allowed now: DTE, open, IV vs open, futures OI run, profile position | — | exists, scattered |

**Non-goals.** No direction score from options alone (options moved in the same 3-min bar as the futures on every in-sample
day, never earlier [M, R4]; the 1-second lead-lag test in §6 is how that claim gets re-examined, not assumed). No dealer GEX.
No Telegram until she signs a build. No change to §1q (SENSEX reads NIFTY's futures flow): SENSEX option flow is recorded and
shown as its own, labelled, never used in a registered read.

---

## 2. The facts the design rests on (all [M] unless tagged)

1. **The lot is 65.** `v2feed.LOTS["NIFTY"] == 65`; the GCD of 159,726 Dext price-cell volumes on 4 Nov is 65; the GCD of
   the futures' `ltq` is 65. Fable's study and §1s's C8 divided by 75: every delta-lot number there, including the 2,000
   "wall move", is 15 % small. **The engine reads the lot from `v2feed.LOTS` and checks it against the day's GCD; a mismatch
   is a health line.**
2. **No recorder has ever caught 09:15.** First chain rows 09:16:19 / 09:17:25 / 09:18:52 (2 / 3 / 4 Nov); the 4 Nov futures
   book starts 09:17:02. The morning start is a manual double-click of `start-v2.bat` with an interactive token check.
3. **The socket is a snapshot stream, not a tick feed.** On the 4 Nov futures, 7,077 of 15,193 volume-changing frames carry
   more volume than their `ltq`; `ltq` holds 29 % of the day's volume; arrival minus `ltt` is 1.6 s median, 6.6 s p90. Option
   frames behave the same or worse [I].
4. **The chain's fields are not synchronous.** `ltp` sits outside its own row's bid/ask on 39–52 % of strike-sides. The
   vendor greeks (`delta`, `gamma`, `iv`) are computed off that `ltp`. Any quote rule or decomposition on chain rows is noise.
5. **OI publishes about every 63 s** and moves every minute from the first snapshot (3 Nov 23500 PE: +2.5 L, +2.3 L, +1.6 L,
   +1.6 L per minute from 09:17). A one-minute shift moves 26 % of 1-min WHO labels, none of the key group words.
6. **The chain's `oi_chg` is against a 09:15 REST baseline** (`upstox_chain.prev_oi`, `upstox_rest.baselines`), not the
   prior close; a leg whose baseline failed writes 0 (A125).
7. **Her profitable population was scalps ≤ 5 min** (n 31, sum +192, median +6, worst −18.8); the leak was 5–30 min holds
   (n 13, sum −122.7) [A78]. She posts, she does not cross: the spread is her revenue.
8. **Option frames already arrive.** `upstox_chain` subscribes ATM ± `SUBSCRIBE_EACH_SIDE` CE/PE in `full` mode; `book_log`
   records only the futures' frames off `feed.on_frame`. The option frames are decoded and dropped.

---

## 3. Architecture

```
Upstox v3 socket (full)            Dext desktop ──bridge──► data/dext/            chain poller ──► data/chain/
   │ on_frame (decode step)                                   (exists)                            (exists; starts late)
   ├─ book_log      (futures, exists)
   └─ optframe_log  (options, NEW, Phase 1) ──► data/optframe/optframe_<IDX>_<day>.jsonl
                                                          │
            ┌─────────────────────────────────────────────┼──────────────────────────────┐
            ▼                                             ▼                              ▼
   optflow_frame.py (Phase 3)                options_flow.py (Phase 2)          optflow_min.py (Phase 5)
   frame flow · markout · stale-quote gap    WHO per strike · groups · word     absorption · stacks · POC ·
   option λ · parity F* · straddle label     walls · squeeze · pin · trapped    exhaustion · big prints
            │                                             │                              │
            └──────────────────────┬──────────────────────┴──────────────────────────────┘
                                   ▼
                           lens.py (Phase 4): DTE · open · IV vs open · RASAD · profile · cross-index
                                   ▼
                     jarvis.build attaches {options, frame, minute, lens}; jarvis.call adds the lines;
                     jarvis_log.card carries the ladder; server._jarvis_log writes the forward logs
                                   ▼
            the five-line ladder on the Jarvis card (each line stamped with its own clock)
```

Each module is pure (no I/O, no clock) with a thin loader that reads the record incrementally with `tailread.rows`. Every
module is correct at any start time: it reads what is on disk, tags what is backfilled, and says what it cannot see.

### 3.1 Modules

| file | phase | what it does | reads | writes |
|---|---|---|---|---|
| `optframe_log.py` | 1 | records every changed option frame for ATM ± `OPTFRAME_EACH_SIDE` (5 [I], Dext's set; the socket subscribes ±16, `SUBSCRIBE_EACH_SIDE`) CE/PE, same discipline as `book_log` (deque on the feed thread, flushed by the senses pass, change-only, restart-safe) | `feed.on_frame` | `data/optframe/optframe_<IDX>_<day>.jsonl` |
| `start_watch` (in `feed_health.py`) | 1 | the first-row time of every recorder today, and a BLOCKING health line when any started after 09:14:30 | the day files | `/api/health.coverage` |
| `tools/morning_start.ps1` + a Task Scheduler entry | 1 | starts `start-v2.bat` at 09:05 if the token is valid; pops the login window otherwise | — | — |
| `options_flow.py` | 2 | the close layer: WHO per strike, groups, word, said lean, walls, squeeze, pin, trapped; the §1s definitions with the lot fixed and the first window at 09:21 | `data/dext/`, `data/chain/`, `data/chain_backfill/`, the frame's fronts | — |
| `optflow_log.py` | 2 | the forward logs, write-once per (idx, close) | — | `data/optflow/close_<day>.jsonl`, later `frame_<day>.jsonl`, `min_<day>.jsonl`, `open_<day>.jsonl` |
| `optflow_frame.py` | 3 | frame flow, undecided share, markout, stale-quote gap, touch vs her size, option λ, parity F*, straddle label, VPIN(opt), risk reversal | `data/optframe/`, `data/book/` | — |
| `optflow_open.py` | 4 | the opening read (gap, straddle vs prior close, first-OI vs prior close), R5 shadow stamps | optframe, chain, prior day's chain | `open_<day>.jsonl` |
| `lens.py` | 4 | the context gather as one dict | existing modules | — |
| `optflow_min.py` | 5 | footprint reads per minute | `data/dext/` | — |

Thresholds: every [I] number in `jarvis_thresholds.json` under `optflow.`, with a `_why` line, re-read per build.
`optflow.py` (the Battlefield) imports the scrip lookup from `options_flow` instead of carrying its own.

**Built 5 Nov, ahead of the phases (shadow):** `optflow/optladder.py` (the ladder's compute, the §1s rules with lot 65 and the first
WHO at 09:23), `optflow/structures.py` (the read's trade: the structure that expresses the said word, priced per lot, status never a
score), `optflow/ladder.html` served at `/ladder` and `/ladder.json` by the Battlefield process on 8790, and the `Options` tab in
ui-v2 as an iframe of it. Phase 2's `options_flow.py` replaces `optladder`'s compute behind the same JSON shape.

---

## 4. Phase 1: record first (build before any read)

**Why first.** Every day without option frames is a day the frame layer, the opening read and the lead-lag test cannot use.
Every day a recorder starts after 09:15 is a day the opening read has no data. Both are true today.

### 4.1 `optframe_log.py`

The row (exchange units; `k` and `sd` from the subscription's meta; synthetic values):

```
{"t": 1793764022653, "cts": 1793764022000, "key": "NSE_FO|12345", "k": 23800, "sd": "CE",
 "ltt": 1793764022100, "ltp": 142.5, "ltq": 130, "vtt": 215605, "oi": 1375387,
 "iv": 0.1556, "dl": 0.49, "gm": 0.0009, "atp": 139.8,
 "tbq": 43770, "tsq": 52170, "b": [[142.3, 650], [142.25, 1300]], "a": [[142.5, 455], [142.55, 910]]}
```

- One file per index per day; rows only for frames that changed (`book_log._sig` plus `oi`, `iv`); rows at or before the
  file's last `t` refused (restart-safe); overflow counted, never raised; opened per flush in append mode.
- Which keys: of the chain poller's subscribed option keys (ATM ± `SUBSCRIBE_EACH_SIDE` = 16 today), the ATM ±
  `OPTFRAME_EACH_SIDE` (5 [I]) nearest the poller's spot, re-chosen as spot moves, so a row names its strike. SENSEX and
  BANKNIFTY the same. Widening to the full subscribed set is one constant, if disk allows.
- `/api/health.coverage` gains `optframe`: first row, last row, rows, dropped, and the strikes covered.
- `daylog` compresses it like the book (the same `.gz` rule).
- Size: the futures book is ~65 MB a day; 22 option legs, the ATM ones at the futures' rate and the wings far below it, are
  ~600 MB a day uncompressed [I]. Acceptable on this disk; if not, the depth levels drop to two a side (the touch and the
  next), which is all Phase 3 needs.

### 4.2 The start

- `feed_health.start_watch(day)`: the first `t` of today's book, optframe, chain and Dext files; **BLOCKING** in the card
  (`recorders live 09:17:02 · open NOT recorded`) when any is after 09:14:30 or absent in market hours.
- `tools/morning_start.ps1`: validates the token the way `start-v2.bat` does; if valid, starts the server detached (the rule
  from 2026-08-25); if not, opens the login window and the card says `token: login needed`. Task Scheduler entry at 09:05
  on weekdays, documented beside the existing `TapeMap EOD capture` task. Her morning stays the same when the token is
  fresh; the difference is that the server is up before she sits down.

### 4.3 Tests

`test_optframe_log.py`: a decoded option frame becomes the row (every field); an unchanged frame is a heartbeat; a replayed
row is refused; `start_watch` names the late recorder and says why; the lot check flags a GCD that is not the feed's lot.

---

## 5. Phase 2: the close layer (`options_flow.py`) and the caption

### 5.1 Definitions (the §1s text binds C1–C8; the two changes below are amendments to be filed as §1s Amendment 2)

- **Lot** from `v2feed.LOTS`, checked against the day's GCD (§2.1). C8's delta-lots use it.
- **Window.** Her 3-min close; **the first WHO window is the first close at or after 09:21** (the 09:15 cross dominates
  the first OI print; OI? before that). A 2-min window is allowed where FIRM passes [I], else 3.
- **WHO per strike per window:** dOI from the last known OI at each end (older than 2 min at the end → OI?); delta = Σ Dext
  minute delta (none → FLOW?); |dOI| < `optflow.OI_MOVE` (1.5 L qty NIFTY / 2,500 SENSEX [I]) → QUIET; else
  sign(delta) at `optflow.AGG_X` × |dOI| (0.2 [I]) → WRITE (+OI, sellers) / BUY (+OI, buyers) / COVER (−OI, buyers) /
  DUMP (−OI, sellers), else MIXED; FIRM when the one-minute-shifted window agrees.
- **Groups** at the close by the chain's spot: CAP (CE ≥ spot), FLOOR (PE ≤ spot), ITM CE, ITM PE; the group word by the
  C4 rule on the sums at 2× the floor.
- **Word and lean** by the study's score table (UP FUEL … QUIET); the said word changes only at two consecutive closes.
- **Walls:** the frame's existing fronts (top-2 OI per side, building / holding / leaving) with the wall strike's own WHO.
- **Covering alarm:** ≥ `optflow.COVER_N` (3 [I]) strikes on one side at COVER in one close.
- **Trapped gauge** and **R1–R4** exactly as pre-registered, as shadow stamps into `close_<day>.jsonl`.
- **Her own strike-minute** is greyed: a marked trade's strike and the minutes around her fills are stamped `hers` and
  excluded from walls (Opus F12).

### 5.2 Output per close (the contract the card, the log and the tests share)

```
{"idx": "NIFTY", "t": "10:50", "win": 3, "lot": 65,
 "word": "UP BUYERS", "lean": 1, "said": "UP BUYERS", "since": "10:47",
 "groups": {"CAP": {"word": "BUY", "doi": 370000, "delta": 61000, "n": 4, "known": 4}, "FLOOR": {...}, "ITM_CE": {...}, "ITM_PE": {...}},
 "strikes": {"23700CE": {"who": "COVER", "firm": true, "doi": -4600000, "delta": 1900000, "vol": 8100000, "oi": 26700000, "stale": false}},
 "cover": {"side": "CE", "n": 3, "doi": -4600000},
 "walls": {"ce": {"k": 24000, "oi": 5023200, "state": "building", "who": "WRITE"}, "pe": {...}},
 "stamps": [{"read": "R3", "dir": 1, "k": 23700}],
 "caption": "options 10:50 · UP BUYERS · cap kharid rahe +3.7L · floor shaant · cover nahi dekha · wall 24000 CE likh rahe",
 "why": ["flow: 22 of 22 strikes read", "oi: chain 10:49:51"],
 "cant": null}
```

`cant` carries the reason when the close could not be read (`"no Dext file for today's expiry — is the bridge running?"`,
`"chain older than 2 min"`), and the caption then says `options: dekh nahi paaye — <reason>`. The three states never merge.

### 5.3 Wiring

- `jarvis._build` attaches `d["options"] = options_flow.frame(day, idx, upto, memo)`; the loader keys its memo on the Dext
  and chain file states so a build re-reads only what grew.
- `jarvis.call` adds `why: "options: …"` and `c["options"] = {word, lean, said, since, caption, cover, walls}`;
  `jarvis_log.card` passes `options` through; `jarvis_log.row` adds `opt_word`, `opt_lean`, `opt_cover` (a NOTEPAD line for
  the contract change).
- `server._jarvis_log` also calls `optflow_log.write_close(day, idx, row)` for a live frame whose close is new: write-once.
- `conftest.STR_PATHS` gains `optflow_log.DIR` and `optframe_log.DIR`.
- SENSEX: computed on SENSEX's own option flow and OI, captioned `SENSEX options (apna flow)`; never enters a registered read.

### 5.4 Tests and fixtures

`test_options_flow.py` on synthetic rows: each WHO quadrant, QUIET, MIXED, OI?, FLOW?, stale, FIRM, the group words, the
word table, the two-close rule, the covering alarm, the lot check, the first window at 09:21, the three states.
`test/fixtures/optflow/`: slices of the 2 Nov 23300 CE/PE record (12:25–13:05) and the 3 Nov 23600/23700 CE/PE record
(10:20–10:40, 13:00–13:20) with their chain minutes and a fixture-local id→strike map (the 03 NOV contracts have left the
scrip master). Assertions: 12:30 2 Nov CE DUMP and PE BUY; 13:18 3 Nov 23700 CE COVER with the alarm; 11:55 3 Nov CE DUMP,
not COVER (the wrong call the README records).

---

## 6. Phase 3: the frame layer (`optflow_frame.py`)

All reads per subscribed contract from `optframe` rows; the futures from `book` rows; deltas **from mids**
(Black-Scholes on the mid with IV implied from the mid, r = 0), never the vendor's.

- **Frame flow.** Per frame, dV = Δvtt. Sign by the **previous frame's** touch (Lee-Ready's prior quote): ltp ≥ prior ask
  → +1; ≤ prior bid → −1; inside → undecided. Undecided volume is split by BVC on the residual mid change
  (Δmid − Δ·dF over the frame, against the contract's own 1-s σ), and counted as undecided. Publish **the undecided share**
  per minute per strike beside the signed sums; it is the error bar and a daily data-quality number.
- **Agreement with Dext** per minute per strike: sign agreement and undecided share, logged and shown. Nothing in Phase 3
  is read on the card until a week of frames shows the agreement.
- **Sums:** signed qty and signed delta-lots over 10 / 30 / 60 s per contract, per side (CE ladder, PE ladder), and the net
  implied delta across both; per **moneyness slot** (ATM, ±1, ±2, ±3), not per contract, so spot drift does not move the
  series under the number.
- **Filters:** same-slot reference from prior recorded post-7-Sep-2026 days until the 6th minute; a cross-sectional z
  (median and MAD across ATM ±3 on the same side, same minute); a futures residual (the per-strike signed delta-lots
  regressed on the futures' signed lots over the day so far, ranked on the residual).
- **Markout** (toxicity): Σ signed dV × (mid at t + 30 s − trade price), per strike per minute, in ticks and in ₹.
- **Stale-quote gap:** option mid − (mid at the last frame + Δ·dF since), in ticks: the lag of the option quote behind
  the futures; positive at a resting offer means it is about to be lifted by an arb.
- **Touch:** spread in ticks, best size against her resting size (from day_state's marked trade when there is one), size at
  level 2.
- **Option λ:** Δpremium mid per signed delta-lot over 5 min against the strike's own-day median; shown beside the futures λ.
- **Parity-implied future:** F* = K + C_mid − P_mid at ATM minus the futures mid, per second; the lead-lag test
  (Hasbrouck information share at 1 s) is the measurement that decides whether "options never lead" stands. Logged, not read.
- **Straddle label:** ATM straddle mid vs futures over the window: |Δstraddle| large with |dF| small → VOL; the call-put
  mid difference tracking dF with a flat straddle → DIRECTIONAL; else MIXED. 1-min on 3+ DTE, 3-min on 0–1 DTE.
- **VPIN(opt)** on equal-volume buckets of ATM ±2 volume, a toxicity regime flag; **risk reversal** from the 0.25-delta
  mids and its 15-min change.
- **Dropped from the brainstorm** (inverted or noise in the futures audit, no reason to expect better on options): depth
  imbalance "asks thinning", delta acceleration, sign persistence, CVD per contract since 09:15.

---

## 7. Phase 4: the opening read (`optflow_open.py`) and the lens

### 7.1 Readable at 09:16–09:17 (needs Phase 1)

1. **The gap:** the futures auction price vs the prior close, in σ of the prior day's range (and vs GIFT at 09:08 when a
   source exists; else "GIFT: not read").
2. **The straddle:** the ATM straddle mid from 09:15:30, once each leg's spread is ≤ 2 % of its premium, against the prior
   close's straddle adjusted for one session's decay: **BID** (paying for movement) or **OFFERED** (writers selling the gap).
3. **The overnight cross:** the first OI update minus the prior close per strike, where the prior close is the previous
   day's last chain snapshot for the same contract (tagged `prior: chain`), else the 09:15 REST baseline (tagged
   `prior: rest`), else "could not check".

**The opening types [I, to pre-register as R5 before any count]:** **GO-leaning** (gap with the straddle bid) and
**FADE-leaning** (gap with the straddle offered), plus **UNREADABLE**. NO GAP is a lens flag, not a type. The first FIRM
WHO at 09:21 confirms or contradicts the type; the card shows both, stamped OPENING until 09:45.

### 7.2 R5 and R6 (shadow stamps, the §1s pattern; the texts are written before the first row)

- **R5 OPENING TYPE.** Stamp at 09:17; outcomes at +15 and +30 min in futures points **and** in the ATM option's excess
  return (Δmid − Δ·dF, Muravyev); pass bar owed by the operator; under 15 per type inconclusive; the kill: GO and FADE end
  the same at n ≥ 15 each.
- **R6 FRAME FLOW AT A BAND TOUCH.** At an R1 band touch, the 60-s frame flow on that strike (`lift` / `hit` /
  `two-sided`, with the undecided share) and the markout of the prior 60 s; outcomes at +5 and +15; the kill: the
  `lift` and `hit` cells end the same at n ≥ 15.

### 7.3 `lens.py`

One dict: DTE and expiry calendar; day part; OPENING (to 09:45); IV vs 09:20 and VIX vs open; RASAD run state; profile
position vs the day's and prior day's VAH / VAL / POC; cross-index sync; the first-hour TREND candidate when the leg
qualifies. The lens **gates** which reads show (PIN only on 0 DTE after 13:00; OPENING types only before 09:45); it never
votes.

---

## 8. The ladder on the card, and scalp mode

Five lines, each stamped with its own clock:

```
lens   ctx       OPENING · 2 DTE · IV −0.4 vs open · fut COVER LIVE · below VAL
who    close     UP FUEL · cap 23700 bhaag rahe −46L ×3 · floor likh rahe · wall 23750 CE holding        [09:21]
where  min       23700 CE: 80 wall absorbed 3× · last defence 20.9L sold @34.15 · POC 36.2 · close above  [09:20]
now    frame     23700 CE: quote lag +2 ticks · touch 455 vs your 1,300 · markout +1.5 (aggressors won) · fut λ 2.1× [09:21:40]
ends   all       5:00 clock · mid back through entry VWAP · fut λ absorption · markout against                [—]
```

**Scalp mode** (her marked trade's horizon ≤ 5 min, or her toggle):
- lines `lens` and `who` may only **veto** an entry (they grey `now`); after a fill they are not shown;
- the card shows the 5:00 clock, the markout and `ends` only;
- every hold past 5:00 is logged with the ladder as it stood at entry, and the evening sheet counts those rows first.

This is the guard against the one way the tool could cost her most: handing a scalp a story to hold for through the 5–30
minute horizon where she loses (A78).

**Confidence.** Now: a count, `4 of 6 agree`, with the dissenters named. After a read's forward window closes and she has
stated the pass bar: that read's frequency with its n per cell (`COVER × AT BAND → STALL 11 of 15`), never a bare %, never
a weighted sum.

---

## 9. Phase 5: the minute layer (`optflow_min.py`)

From the Dext per-price cells, per contract per minute: absorption at a premium row (1 % bins, 0.05 floor; one-sided
aggressive volume ≥ own-day p90 with next-minute progress ≤ one bin), confirmed against the futures footprint at the same
minute before it is called a defended level; stacked diagonal imbalances (≥ 3 cells at ≥ 3 : 1); the minute POC and
acceptance; unfinished auction at the extreme; big prints in the day's top decile by delta-lots and by ₹ premium; exhaustion
as a mark only. All [I]; all marks, never words; a tick-floor caveat for premiums under ₹5. Designed here, built after
Phase 3's agreement numbers exist.

---

## 10. Error handling, anytime-start, health

- Every loader reads what is on disk; a file that is missing or stale yields the reason, never a zero.
- Backfilled minutes (chain_backfill, the bridge's catch-up) are tagged `backfill` and never pooled with observed rows.
- A build that raises leaves no memo; the next is cold (Jarvis's rule).
- Forward logs are write-once per key, fail-soft, under `data/optflow/`; the mock server points them at the mock dir.
- `/api/health.coverage`: recorder start times, optframe rows and dropped, Dext strikes covered, the lot check, the
  undecided share (Phase 3), chain age.

---

## 11. House rules, and what this design bends

**Bent, on her word:** one clock → three clocks; A78's "don't build for sub-5-min scalps" reopened (with the scalp-mode
guard); a frequency with its n after a window instead of no number at all.

**Kept:** no order path; pre-register before counting (R5, R6 written before the first row); no hit rate or confidence %;
[M]/[I] on every number; populations apart (close, frame, min, open are four logs); the three states never merge;
anytime-start; registered rules untouched (§1s gets Amendment 2 for the lot and the 09:21 window, filed before Phase 2 runs).

---

## 12. Build order and what each phase delivers

1. **Phase 1, recorders** — `optframe_log.py`, `start_watch`, the morning task. Done when: a day's optframe file exists for
   NIFTY and SENSEX, the card says when each recorder went live, and a late start is a red line.
2. **Phase 2, the close layer** — `options_flow.py`, `optflow_log.py`, the caption on the card, `close_<day>.jsonl`, the
   §1s Amendment 2 filed. Done when: the fixtures pass, the caption is live, and the Battlefield imports the shared scrip
   lookup.
3. **Phase 3, the frame layer** — after one week of frames. Done when: the undecided share and the Dext agreement are on the
   health line and `now` is on the card in scalp mode.
4. **Phase 4, the opening read and the lens** — R5 and R6 texts filed first. Done when: the opening type is stamped at
   09:17 on a recorded day and `open_<day>.jsonl` exists.
5. **Phase 5, the minute layer** — last.

Each phase gets its own implementation plan from this document. Phase 1 is small and should ship before the next session.

---

## 13. Decisions that are hers (named, not assumed)

- SENSEX option flow in any registered read (§1q is hers to change).
- The scheduled 09:05 start (it changes her morning only when the token is stale).
- The scalp-mode toggle versus inferring it from the marked trade's horizon.
- The pass bars for R5 and R6, stated before any evaluation is read.
- Telegram for SQUEEZE ON / wall break / trap, after the caption has run forward.
