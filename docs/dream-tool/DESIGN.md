# AANKH — the dream tool. Design and brainstorm (Fable, 27 Oct 2026)

Her ask, verbatim: *"a live right on chart decoding everything live … as the setup armed it needs check what happened
before in data … when the setup fired it should figure or mark the target, stop loss … now live on every candle … it
should be able to anticipate … figure out noise from real data … go insane completely. its a dream tool for me."*

AANKH ("the eye") is the screen that does those five jobs on her NIFTY futures 5-minute chart, from the record TapeMap
already keeps. The mockup (`mockup/dream.html`) replays five real days minute by minute; `mockup/dream_facts.py` extracts
the record read-only, `mockup/dream_build.py` is the brain, the page only draws. Every rule below was run over all five
days; where a rule fails, REPORT.md says so.

Conventions: **[M]** measured from the record · **[I]** an inference on measured data · *s* spot · *f* futures ·
agreement is always a COUNT (n/N), never a %.

---

## 0. First principles that shaped it

1. **The read lives ON the chart.** Pins where things happen, lines where they matter, a side column that is numbers and
   pills, never a paragraph (26 Oct, 6 Oct rules).
2. **Noise is measured against the day's own baseline.** Every number is ranked against the same number's earlier values
   TODAY (prints.pct_rank, strict, six samples before any rank). Grades: **NOISE** < p70 · **HALKA** (whisper) < p90 ·
   **ASLI** (real) ≥ p90 · **ZOR** (loud) = above every earlier value. The same scale for lots, OI change, writers' lead
   change, volume. A fixed number ("400 lots") is never used to grade. [M]
3. **The machine stays registered.** The zone (§1b / §1r), its ∓20 stop, FADE / RIDE / FADE-D / HOLD v2, the fade gate's
   fronts (§1d) and the one-sided meter (§1o) are called, never re-implemented. What AANKH adds is read-side: a check
   around the arm, a level set around the fire, a voice per candle, a map ahead, a grade on every event. Where a new rule
   would be needed, §8 writes it as a PROPOSED registration for her signature.
4. **Three sentences.** Every piece that cannot be read says why (chain purana, record 09:32 se, roll week kachcha).
   A missing piece lowers N; it is never a zero and never a ✗.
5. **One basis per minute.** Every level drawn in futures is converted with THAT minute's basis (fut 1-min close − the
   chain's spot at that minute), never a constant (13–74 pts drift inside a day). Labels show both: `22,866f|22,847s`.

---

## 1. Every read, graded (the brainstorm)

Each line: what it detects · data (file · module) · [M]/[I] · how it separates noise from real · where it is on the screen
(S = shown in the mockup, D = designed only, G = needs recording).

### 1.1 Order-flow microstructure (NIFTY futures tape)

| read | detects | data | tag | noise vs real | screen |
|---|---|---|---|---|---|
| Δ per bar, graded | who pressed this candle | `tape_NIFTY` buy/sell/delta · GoCharting | M | rank vs the day's bars so far | S · Δ strip, tooltip |
| CVD trajectory | whether the pressing is cumulative or spent; peak/trough and drawdown | same, cumulative | M | off-peak in units of the leg's own Δ range | S · CVD line; IN-TRADE "CVD peak se neeche" |
| **BADA PRINT** | one price absorbing a lot in one bar (her 198K/300K misses, A62) | `ladder` max single-price b or s; decoder E1 | M | ZOR only when above every earlier bar's biggest print | S · filled pin |
| ABSORB | ≥ ASLI Δ against the leg that bought < 3 pts/100 lots and no new extreme | bars | I | ASLI/ZOR by Δ grade | S · pin |
| ROKA / THAKAN / PHANSE / ZOR / KHALI | the extension's own marks, placed when the bar closes, TOOTA known only from its own break time | `ofd_marks2` | M (I for the name) | by lots vs the day's bar deltas | S · pins |
| STACK | stacked imbalances (3+ diagonal rows) on the moving side | `prints.bar_flags` (the extension's math) | M | 1 stack HALKA, 2+ ASLI | S · pin + spike piece |
| unfinished auction | a bar whose extreme traded both sides ≥ 2% vol: it gets revisited | `prints.bar_flags` | M | shown in tooltip only | S · tooltip |
| **EFFORT per point** | lots/pt at a fresh extreme vs the day median: ≤ ½× at a low = cheap low (continuation), ≥ 2× at a high = expensive high (reversal). The one flow read that survived two holdouts | `book_NIFTY` 1-s · `effort.py` | I | survivor bands only; the mirrors read "nahi" | S · pin + ARM piece |
| 1-min Δ (the forming bar) | the candle building, sided by the book | `book_NIFTY` · `confluence.book_flow` | I (side) | — | S · forming candle |
| reader legs + WHO | 1-min legs with delta × OI × price class (new longs / covering / new shorts / liquidation / rotation / absorbed) and effort-vs-result rank | `reader_NIFTY` | I | the reader's own rank vs today's legs | D · tooltip of the leg (not drawn, the 5-min leg is) |
| runs (3 big same-side fills) | aggression arriving in a burst | `runs.py` on ladder fills | I | ≥ p90 fills in 20 min | D · needs the fills log per day |
| sweep vs pulled | levels gone WITH volume (aggression) vs WITHOUT (liquidity leaving) | `sweep.py` on consecutive depth | I | kind field | D · G: depth per frame is in `book_*`, heavy to replay |
| impact (lots per tick) | how thin the market is now | `impact.py` | I | pct vs session | D |
| VPIN percentile | books being adversely selected: expansion risk, direction-blind | `vpin_fast.jsonl` | I | session percentile; TOXIC ≥ p80, SHAANT ≤ p50 | S · strip + ARM piece + spike piece |
| feed disagreement (A112) | GC and Upstox disagreeing on a bar's side by > half its volume = a block/roll print, not flow | `tape` vs `ux` delta | M | — | S · tooltip shows both deltas; D: a "side vivaad" pin |

### 1.2 OI composition (the chain)

| read | detects | data | tag | noise vs real | screen |
|---|---|---|---|---|---|
| **LIKH (writers' lead)** | aaj likha PE − CE on the nine strikes ATM ± 4, as % of the pair, per minute | `chain_NIFTY` · read.writers' window | M | ±15% = a side (§1o); change over 15 min ±10 | S · strip + ARM pieces LIKH / LIKH 15m |
| **FRONTS (§1d)** | the top-2 strikes per side by session-peak OI: BUILDING / STALLED / UNWINDING, per minute, causally cut | `fronts.read` on `confluence.chain_grid` | M | state changes held 3 min before they are events | S · ARM pieces, LIKH events, GAVE-UP exit |
| PE WALL / CE WALL | heaviest absolute OI strike per side (floor / ceiling) | chain | M | — | S · level rail, pools, targets |
| MAX PAIN | the pin strike | chain | M | — | S · rail |
| fut OI × price per bar | SL KAT RAHE / NAYE KHARIDAR / LONG NIKAL / NAYE BECHNE | `fut_<day>` 1-min OI, `ux` bars | I | OI change graded ≥ HALKA AND price change graded ≥ HALKA, else nothing | S · pins, OI strip ticks, takat vote |
| fut OI 15-min quadrant | who is running (fuel vs no fuel) | same | I | graded 15-min ΔOI | S · AAGE "kaun bhaag raha", ARM piece FUT OI |
| FUEL (READ-2) | 40-min fut ΔOI ≥ p80 of reference days | `rank_ref` | M | vs reference days at the same clock | D · needs rank_ref for days before 20 Oct |
| trapped inventory / pain | writer basis vs price, pain per (strike, side) | `trapped_inventory.py`, `chainside.py` | I | — | D · the hunt map (`hunt.py`) could rank up/down fuel |
| cross-index OI | BANKNIFTY / SENSEX PE lead on their nine | `chain_BANKNIFTY/SENSEX` | M | ±15% | S · ARM piece X OI |
| xindex walls | OI added within reach per index, agreement across three | `xindex` | M | vote per index | D · tooltip |
| **roll** | near-month fut OI carries the roll in expiry week | — | — | every fut-OI read tagged "kachcha" and never counted in takat | S · header note, pins, pieces |

### 1.3 Options-side reads (designed, not in the mockup)

- **Premium path of the ATM** at a zone touch: did the option make a lower low with the future (buyers absent) or a higher
  low (sellers leaning)? `chain` ltp per strike per snapshot. [M] D.
- **IV change on the nine** over the last 15 min: writers pricing a move (IV ↑ while OI ↑) vs selling calm. `chain` iv. [M] D.
- **Writing vs buying** (read.writing_vs_buying, WB_MIN 25 vol-pts): inside ±0.25 vol-pt they cannot be told apart; say so. [I] D.
- **Straddle move used** (`u`, Validate rev 3): share of the day's 1σ already spent in her direction; ≥ 0.9 → AGAINST a
  new trade. [M] D.
- **Expected move** (trademap EM) as a ceiling on targets: T3 beyond 1 EM is "aaj ke liye bahut door". [I] D.

### 1.4 Volatility / regime / day type

| read | data | tag | screen |
|---|---|---|---|
| §1o one-sided meter (TREND/PIN/CHOP/MIXED) at every close, causal | `onesided.meter` | I | S · ARM piece DIN |
| σ of her 3-min bands (the stack's U) | `contract_bars` 3-min | M | S · risk in σ, SL pool offset 0.25σ, line trail |
| 30-min range percentile (the §1b rng_r split: band rejection vs walking the band) | bars | M | D · one more ARM piece once pre-registered |
| compression/trap filter | — | — | **dead (§2)**, not revived |
| gamma regime (regime.py) | — | — | shadow only; anti-predictive n=1 (§1b); not used |

### 1.5 Cross-index lead / lag

| read | data | tag | screen |
|---|---|---|---|
| X2 EXTREMES: at the latest push did BANKNIFTY / SENSEX take their own swing high/low (TOOK / FAILED) → CONFIRMED / DIVERGENT | `xindex` | M | S · ARM piece X PRICE, XDIV pins |
| X1 SYNC (SAATH ▲▲▲ / ALAG) with sizes in each index's own ruler | `xindex` | M | S · SYNC events (held two rows) |
| X3 LEAD (who turned first, minute stamps) | `xindex` | M | D · tooltip |
| SENSEX = NIFTY flow + SENSEX OI (§1q) | — | — | the mockup is NIFTY; a SENSEX view reuses every flow read and swaps the chain |

### 1.6 Basis and book depth

- **Display basis** [M]: the house basis, fold.py's `BIX_MS` (A60): the MEDIAN of the raw per-snapshot basis samples
  (futures LTP from the 1-s book − the chain's spot at the same second) over the last 3 minutes. The raw per-minute
  number jumped 10–20 pts minute to minute (chain-snapshot timing against the futures minute, not carry); the 3-min
  median moves under 8 pts a minute except at the 15:15 cash-auction freeze. Every s|f pair, every converted level and
  the basis cell use it. Shown always; no vote (it is the roll and the carry, not a side). S.
- **A level's native number never changes.** PD/PW/PM levels are spot-native, the prior-day profile and session
  extremes futures-native, walls and max pain strike-native (spot frame); only the other frame converts, live, with the
  3-min basis. When one kind sits in both frames the kind names the frame ("PDL s 22,848" / "PDL f 22,866"); within 5 pts
  after conversion the two become one row ("PDL 22,848s|22,866f").
- **Basis vs its day median** [I]: futures sold harder than cash into a low (hedgers) — too shaky to vote; D.
- **Shelves and vacuums** (`pools.py`) [M arithmetic]: the terrain of resting size. D; needs the depth replay.

### 1.7 Levels and terrain

Level set used by FIRE and AAGE, each with its frame and source [M]:
PDH/PDL/PDC (spot ≤ 15:15 from the prior chain day; futures from the exchange candles), PWH/PWL (prior ISO week), PMH/PML/PMC
(prior calendar month, recorded sessions), OPEN, prior-day POC/VAH/VAL and HVN/LVN (5-pt bins over the prior tape day's
ladders), today's developing HVN/LVN (bins over closed bars), session high/low ("stops upar/neeche"), PE/CE walls and max
pain (converted with the minute's basis), unbroken ROKA/THAKAN/PHANSE/KHALI marks, round numbers (last resort).

### 1.8 Her setups as arms

| arm kind | in the mockup | note |
|---|---|---|
| ZONE touch d2/u2 on HER 3-min bands (§1r), every re-arm, the machine's own 10-candle expiry | S | the mockup sets ZONE-3M's date to each replayed day, as A110's replay did |
| FADE-D location (new extreme) | D | `faded.py` episodes; add as a second arm kind with the same 12 pieces |
| RIDE pullback (READ-2 §E) | D | `ride.py`; the 23 Oct rip had no zone entry — RIDE is the arm that would have fired |

---

## 2. The five jobs, specified

### A · ARM CHECK (job A) — at the zone's first arm, and re-read at every close while armed or in trade

Twelve pieces, each read at or before the arm minute, each ✓ saath / ✗ khilaaf / · neutral / ? could-not-check with its
number. **n = ✓ count, N = pieces that could be read.** The count is never a probability.

| piece | ✓ for a BUY (SELL mirrored) | source | tag |
|---|---|---|---|
| LIKH | PE lead ≥ +15% | writers per minute | M |
| LIKH 15m | lead change over 15 min ≥ +10 | same | M |
| PE FRONT (defending, §1d) | BUILDING (STALLED ·, UNWINDING ✗) | fronts.read, causal cut | M |
| CE FRONT (attacking) | UNWINDING (STALLED ·, BUILDING ✗) | same | M |
| CVD 15m | last 3 bars' Δ / vol ≥ +0.05 (§1o's share) | bars | M |
| Δ THAK | last bar's Δ against the side ≤ 25% of the leg's biggest same-side bar (FADE-D 2a), or already with the side | bars | M |
| VPIN | session pct ≤ 0.5 (toxic ≥ 0.8 ✗) | vpin_fast | I |
| EFFORT | a survivor read in the last 30 min: cheap low ✗ for a BUY; expensive high ✓ for a SELL | effort.py | I |
| FUT OI 15m | price down + OI up (fresh shorts = fuel for the squeeze) ✓; price down + OI down (liquidation) ✗ · roll week → ? | 1-min OI | I |
| X PRICE | peers FAILED to take their low (DIVERGENT) ✓; all TOOK ✗ | xindex X2 | M |
| X OI | mean BNF/SNX PE lead ≥ +15% | peer chains | M |
| DIN | TREND with ✓ / against ✗; CHOP/PIN ✓; MIXED · | onesided (§1o) | I |

"What came before" sits above the tiles: the last 15 min in numbers (pts, Δ, OI, lead then → now).

### B · FIRE (job B) — at the 3-min entry close

- **ENTRY** E = the entry bar's close (registered). **STOP** = the machine's (`d2 − 20` / `u2 + 20`), never changed.
- **SL POOL** [I]: the nearest reaction level beyond the setup's extreme within 2.5× the risk (PD/PW/PM levels, prior-day
  POC/VA/HVN, OI wall on the same side, session low/high, unbroken marks; never LVN, round, max pain), placed 0.25σ past
  it — "PDL 22,435f · 0.25σ beyond = SL pool". It is where the hunt would go, not a second stop.
- **TARGETS** T1–T3 [I]: VWAP (§1i) and the next reaction levels in the direction, sorted by distance, deduped within 8
  pts, none under max(½ risk, 10 pts), each with its kind, frame and R. LVNs are corridors, never targets.
- **At entry the twelve pieces are re-read**; a defending front already UNWINDING at entry is flagged red (every such
  trade in the replay exited within one close).

### C · IN TRADE (job C) — every 5-min close (and the stop/line every minute on the 1-min candles)

One state from the ladder, the most cautious active one:

- **EXIT**: the stop or the trailed line traded (1-min intrabar, never a close) · the defending front UNWINDING with price
  on its writers' losing side by 0.25σ (§1m A1+A2, "CE 22,800 CHHOD GAYE") · 15:20 · an opposite zone entry ("ULTA ZONE
  ENTRY", shown, not an exit rule).
- **SOCHO (think)**: a real change named — BADA PRINT against, Δ against > ½ the leg's biggest bar, PALTA against, the
  defending front unwinding in profit ("munafa booking"), fresh OI against (never counted in roll week) — when the leg
  is in pullback or two decel signs are on.
- **TIGHTEN**: the HOLD v2 idea — a ≥ ASLI push bar in the trade's direction moves the line to its origin + 0.25σ, only
  toward price; breakeven lock at MFE ≥ 2R.
- **HOLD** with the phase: **ZOR BADH RAHA** (takat 3/4) · **CHAL RAHA** (2) · **RUK RAHA** (≤ 1) · **PULLBACK · koi
  badlaav nahi** (23.6–61.8% retrace with no change named).
- Each close's line: `takat n/N · thak n/4 · Δ · OI · lead · R · MFE`. T1/T2/T3 touches are marked, never exits.

### D · ANTICIPATE (job D) — always, from the last close

- **UPAR / NEECHE liquidity**: the three nearest reaction levels each side with distance (levels, walls, session extremes,
  unbroken marks, today's HVN; LVNs excluded from the list).
- **CORRIDOR**: the wall ahead in the leg's direction, the next shelf past it, the points between, and whether an LVN
  (prior day's or today's) sits in between → "KHALI (LVN)".
- **KAUN BHAAG RAHA**: the 15-min fut OI × price quadrant, graded.
- **SPIKE RISK n/5**: flow bhaari (vol ≥ ASLI) · Δ rising three bars on the moving side · a stack on the moving side ·
  VPIN toxic · LVN ahead.

### E · NOISE vs REAL (job E) — always

The grade scale of §0.2 on every event; the chart draws by grade: NOISE never, HALKA a dot, ASLI a chip (a dot after 45
min), ZOR a filled chip with a ring. Five chips at most on screen, ranked ZOR → kind importance → recency. The TAPE lists
all but noise, newest first, with the grade dot. Hysteresis: a front's state must hold 3 minutes; SYNC two rows; VPIN
re-arms under p60; effort reads collapse within 10 minutes.

---

## 3. The screen

**Layout (1440 × 900, light).** Header: day tabs, play, clock, scrubber, speed, notes (ROLL WEEK · record from).
Left 1040 px: the chart (a rolling 4-hour window, her 3-min zone rings in azure, VWAP, the leg shaded by who is winning
with depth = takat, levels as rails on the right with frame chips, pins with Hinglish chips, E/STOP/LINE/SL POOL/T lines
with distance), then three strips: Δ bars + CVD, fut OI (amber in roll week), PE − CE lead area + VPIN percentile.
Right 392 px: NOW (state pill, headline, numbers), the 12 tiles, PLAN, AAGE, TAPE (with jump buttons to the day's moments).

**First second:** the state pill and the headline — `HOLD · BUY  CHAL RAHA` / `ARMED BUY · 4/11 saath 2 khilaaf` /
`EXIT  PE 22,700 CHHOD GAYE` — and the E / STOP lines with "33 door".
**First five seconds:** the tiles (which pieces agree), the leg colour, the SL POOL and T1, the last three tape lines.
**Hover:** a bar's facts sheet: o/h/l/c, spot, basis, Δ and its grade, buy/sell, vol, UX Δ (feed disagreement), OI change
and read, lead and its 15-min change, takat, retrace %, CVD, the big print, stacks, unfinished auction, a filled slot.

**What stays quiet:** nothing animates while nothing happens; a chip pulses for 6 minutes after its event; the shade
changes only with the leg. **Keyboard:** ← → a minute, shift for five, space to play. `?d=YYYY-MM-DD&t=HH:MM` opens a moment.

---

## 4. What the replay shows the rules doing (summary; REPORT.md has the minutes)

- The twelve-piece check separated the red-leg buys from the one that held: 21 Oct 11:18 arm 0/11 (5 khilaaf), 12:36
  0/11 (8 khilaaf); 8 Oct 10:33 2/12 (6), 12:00 2/12 (6); 26 Oct's bottom read 2/8 → 4/10 as the record filled (late
  start) and its PE front built through the pullback.
- The voice held the 26 Oct BUY 69 minutes through a 61% pullback ("koi badlaav nahi"), trailed the line on two ZOR
  pushes and gave it up only to the opposite zone entry.
- The §1m gave-up exit fired at the first close after entry eleven times; ten were trades that went on to lose. It also
  exited the 22 Oct 11:18 SELL at +0.28R before +153 — the front's peak minute was two hours stale (§8.3).
- The writers' lead voted against the day's best trade (21 Oct 09:45 SELL, PE lead +34, +148 pts): the PE writers were
  the trapped side, not the defenders (§8.2).

---

## 5. Gaps (what needs new recording or a new rule)

1. **Next-month futures in roll week (A119)**: record the next contract from ~7 sessions before expiry; read near + next
   OI together. Until then every fut-OI read is "kachcha" and uncounted.
2. **Monthly and weekly levels**: `levels.py` has no monthly fetch; the mockup builds PMH/PML/PMC from recorded chain spots
   (19 of ~22 September sessions, holes named). Needs daily index candles (Upstox daily REST) cached per day.
3. **Prior-week levels** on roll-week days came from 3 recorded sessions (13–15 Oct unrecorded).
4. **Late starts** (26 Oct from 09:32): the twelve pieces are "?" before the record; the arm at 09:24 reads 0/1. Backfill
   of the chain from 09:15 (A106/A107's pattern) would fill LIKH / FRONTS; the book cannot be backfilled.
5. **rank_ref** before 20 Oct: FUEL (READ-2) could not be shown on 8 Oct.
6. **Depth replay** for sweeps / pulled quotes / shelves: the 1-s book is recorded (12 MB/day); the replay needs a
   per-day fills log to be cheap.
7. **SENSEX/BANKNIFTY footprints**: Upstox bars only (no GoCharting), fine for the cross-index pieces; a SENSEX AANKH view
   needs §1q's flow mapping (NIFTY's) — one switch.
8. **Marks v1 on days before 5 Oct** lack `status_t`; TOOTA is unknown there.

---

## 6. What to build first (ranked by what helps HER trade)

1. The twelve-piece ARM CHECK on every zone arm, every minute, with the "before 15 min" line (the 21 Oct and 8 Oct
   losers were all low counts with named khilaaf pieces).
2. FIRE's SL POOL and T1–T3 from the full level set with the frame on every price (she asked for exactly this).
3. The per-candle voice with PULLBACK · koi badlaav nahi vs SOCHO naming the change.
4. Day-relative grading of prints and OI (BADA PRINT as ZOR only above every earlier print) — the A62 misses.
5. AAGE's corridor and spike count (the 23 Oct 13:40 breakout showed stack ▲ 7 rows + SL kat rahe + flow bhaari).
6. The GAVE-UP exit with a fresh peak reference (§8.3) — then it becomes a real exit, not a first-close refusal.
7. FADE-D and RIDE as arm kinds (the 23 Oct rip).

---

## 7. House-rule compliance

No order path. Nothing under `data/` written. `telegr/` never opened. Server untouched. No hit/win rate or % anywhere;
counts only. Every price s|f with the minute's basis. Light theme. Hinglish chips with numbers; the machine's own
sentences (triggers, fronts' states) kept. Roll week tagged. No look-ahead: every series is cut at the replayed minute,
marks appear at their bar's close and break at their own `status_t`, xindex/reader/decoder rows at their write time.

---

## 8. PROPOSED registrations (for her signature; nothing here is live)

**8.1 ARM CHECK n/N as a stamp, never a gate.** Log the twelve pieces beside every zone arm row (trigger_log / zone3) from
the day she signs; score which pieces separate after n ≥ 20 arms per side. Kill any piece that does not.

**8.2 LIKH read as "who is trapped" at the arm, not "who defends".** On 21 Oct the PE lead (+34%) voted against the
09:45 SELL that ran 148 pts; the PE 23,000 front then UNWOUND at 10:30. Her own thesis (stops are liquidity) says the
side that loaded at the reaction point is the fuel. Proposal: at a SELL arm, PE writers BUILDING into the touch counts as
fuel (✓), not defense (✗), when the CE front is UNWINDING; mirror for a BUY. Decide on forward arms, not on 21 Oct.

**8.3 GAVE-UP peak reference freshness.** §1m A1 compares price with the spot at the front's PEAK minute. When that peak
is older than 60 minutes (22 Oct CE 22,800 peaked 09:24; the exit fired 11:40 on a falling price) the reference is stale.
Proposal: use the front's peak within the last 60 minutes, or the entry-minute spot when the peak is older. Forward only.

**8.4 Target distance floor.** A target under max(½ risk, 10 pts) is not a target (dropped 26 Oct's "T1 pHVN 0.1R").
