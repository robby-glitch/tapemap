# JARVIS — the world they haven't seen (31 Oct 2026, Saturday, market closed)

Written to be judged. Her brief: *"imagine you are seeing this project, your manager gave it to you and said this is
just inspiration. What do you think we should make it? You have to showcase why you are the best. They are judging you,
and you have to prove to them that they just scratched the surface with what we have. Show them the possibility, the
world they haven't seen, what can be done with it."* And: *"I think we need Jarvis to have all these decisions in it if
we have to make it smart and a real Jarvis."* Her correction the same day: *"no constraints, we can do anything, buying,
selling and everything."*

What was read: `JARVIS-REVIEW-2026-10-31.md` (yesterday's whole-stack review, 5.5/10), `ALGO-AI-TAKE-2026-10-31.md`,
`GAPS-AND-LIVE-CHECKLIST.md`, the kahani spec §15–§17, the dream-tool BRIEF / DESIGN / REPORT, `JARVIS-DAY-2026-10-30.md`,
`BEST-TRADES-ATLAS-2026-10-31.md`, `DECODE-GAPS-2026-10-30.md`, `NOISE-DECODER-BRAINSTORM.md`, NOTEPAD A140–A201,
`jarvis.py` / `legs.py` / `handshake.py` constants, `research-findings.md` §1–§2, oi-lab `flow/AUDIT.md`, the module
docstrings, and the nine `algo_ai` files (read only; `token.json` not opened). Record sizes were measured on
`data/` for 29 Oct. Conventions: **[M]** measured, with its source · **[I]** inferred · *s* spot · *f* futures ·
agreement is a COUNT, never a %. This builds on the review; it does not repeat it.

---

## 0. The one-paragraph answer

`algo_ai` is a well-made bet: it looks at the market once at the open, blends seven aggregate reads into one number,
asks a model for a three-word news mood, buys an option and babysits a rupee stop. It reads once and then watches its
own P&L. What is sitting in `tapemap/` is a market being *recorded* — the futures book at one second with five levels of
depth, the option chain every ten seconds on three indices, her footprint per price per minute — and a causal brain
that can rebuild what any minute of 25 days looked like *as it was known then*, with the option writers read strike by
strike, per minute, as rates. The difference is not features. It is the difference between a tool that places a bet and
a desk that reads. Everything below is what that desk can be, built from what is already on disk, with one line kept
where she drew it: Jarvis explains, judges, draws, watches, alerts and remembers; it never places an order, and it never
shows a probability.

---

## 1. The pitch

### 1.1 What algo_ai is [M: `README.md`, `option_signal.py`, `decision.py`, `ai_sentiment.py`, `engine.py`]

Nine Python files, 4,769 lines. One **Execute** = one analysis pass at the open: the heaviest OTM call wall and put wall
(ATM ±5) give a base probability `support/(support+resistance)`; seven signals (PCR level, VWAP side, a 15-min opening
range breakout, the gap, ATM OI change vs yesterday, a model's news sentiment, "momentum used") each nudge it ±5 points
(`combine_probability_signals`, clamped to [5 %, 95 %]); `decide_direction` reads CALL above 0.55, PUT below 0.45,
BOTH on a large gap, NO_TRADE when VIX's expected move is under 30 pts or under the ATM premium × 1.15. Then a loop:
₹ stop, ₹ target, a time exit, a 15:15 force exit, settings re-read every second, positions reconciled from the broker on
restart. One model call per run, fixed prompt, JSON-only, safe default NEUTRAL. `dry_run` defaults on. The README says
the weights are "not backtested". It is honest, tidy and small — and it is a **morning coin-flip with a safety net**: the
reads are aggregates (two walls, one ratio, one VWAP side), taken once; the market is not read again until the exit.

### 1.2 What is sitting in tapemap/ [M]

| | algo_ai | TapeMap + Jarvis |
|---|---|---|
| reads the market | once, at the open | every minute, 09:15–15:40, three indices |
| OI | two walls vs yesterday's close; PCR level | every strike, both sides, every ~10 s (2,101 chain snapshots on 29 Oct); writers at LEVELS per minute: fronts (§1d), Sides 2×2, WRITER FLOW ±7 per 3 min, the handshake push → answer at the strike and its band, who opened |
| order flow | none | the 1-s futures book (23,271 rows on 29 Oct, five levels each side), her footprint per price per minute (385 Dext candles), the GoCharting 5-min tape, pushes, effort per point, VPIN |
| record | none | 25 NIFTY days 22 Sep–30 Oct at full depth; 44 chain days back to 20 Aug; 2.9 GB; every forward log written before the outcome |
| replay | none | `jarvis.build(day, idx, upto)` is causal (reads minutes < upto only; `test_causal_prefix`): any minute of any day, as the screen knew it then |
| the model | a 3-word news nudge into the direction | (planned) the narrator over a measured frame, fenced to its numbers, never the verdict |
| honesty | a 0–100 "confidence", a 5–95 % probability | counts, "could not check", health that names every hole; no % anywhere, by rule |
| tests | 2 files | 2,081 collected (CLAUDE.md, 27 Oct); `test_jarvis` + `test_legs` 35 pass |
| modules | 9 | 265 `.py` at the top level (tests included), ~110 read modules |

### 1.3 The gap, named

algo_ai answers *"which option do I buy this morning?"* once. The desk in `tapemap/` can answer, every minute, the six
questions she said a read must answer — *where are we · who is hitting · is it working · who is adding or leaving ·
who is trapped · do the other indices agree* — and then the ones algo_ai cannot ask at all: *what did I say an hour ago
and was I right · what does this minute look like on the 25 days I have seen · what would end this trade · is this a
buyer's trade or a seller's · why?* The honest starting line (review, 31 Oct): Jarvis today is **5.5 / 10** — senses 8,
judgement 4, Jarvis-ness 2. This document is what the 8 can carry once the 4 and the 2 are built. Almost nothing below
needs new data. Most of it needs no new reads.

---

## 2. The moat they don't see

### 2.1 What one day records [M: `ls -la data/*2026-10-29*`, `wc -l`]

| record | cadence | 29 Oct (NIFTY unless noted) | what each row holds | read live by |
|---|---|---|---|---|
| `book/book_<IDX>` | ~1 s | 23,271 rows · 9.1 MB (SENSEX 13.0 MB) | ltp, ltq, volume, **fut OI**, 5 bid + 5 ask levels, total bid/ask qty, the contract | handshake's quote-rule flow, `effort.py`, VPIN, Jarvis's futures minute when Dext is missing |
| `chain/chain_<IDX>` | ~10 s | 2,101 snapshots · 13.2 MB × 3 indices | spot; per strike, both sides: OI, LTP, IV, delta | fronts, Sides, ±7, the handshake's answers, THE READ, Board, gamma |
| `dext/dext_NSE-61471` | 1 min | 422 rows · 723 KB | her footprint: per-price buy / sell volume per minute (Dext 0.8.1 v2) | pushes, legs, the decoder, BADA PRINT |
| `tape/tape_NIFTY` + `ofd_marks2` | 5 min | 221 KB + 96 KB | GoCharting footprint bars with ladders; the extension's marks | her method's bars; `rank.py` |
| `tape/ux_<IDX>` | 1 min | 446 KB | Upstox book-derived flow per index | §1q (SENSEX reads NIFTY's) |
| `senses/senses_<day>` | per event, 1-s | **940,094 rows · 256 MB** | sweep / pulled / absorption / depth-pull detectors on the 1-s book, 3 indices | **nothing live** (shadow) |
| forward logs | per close / event | read 253 · decode 225 · sides 424 · xindex 125 · handshake 105 · messages 91 · frame 589 passes (19.9 MB) · hold expr 1.5 MB · rank_ref · trap · warmap · calls 1.2 MB | what every module said, write-once, before the outcome | the evening (partly) |
| `confluence_log.jsonl` | per band signal | 176 rows, 21–30 Oct, 3 indices | her §1i / §1n / §1j band signals with their window | the panel; **not Jarvis** (A194) |
| `trigger_log.jsonl` | per arm / trigger | 3,004 rows since Aug | her zone, the one irreplaceable artefact | the zone machine, eod scorer |

Totals: `data/` = 2.9 GB with week-old days gzipped (`daylog.py`); 25 NIFTY book days (22 Sep → 30 Oct); 44 NIFTY chain
days (20 Aug → 30 Oct). Known holes (atlas §0, noise §0): 13–15 Oct unrecorded; 13 Oct 45 min, 16 Oct 32 min; 12 Oct ends
13:41; 26 Oct from 09:32; 28 Oct morning rebuilt from 11:07; 30 Oct lost 78 min to the internet (now saved per minute by
`jarvis.save_tape`); roll week 21–26 Oct carries the October future's roll (A119).

### 2.2 What is already computed (the inventory, condensed from the review §6)

| family | modules | reads |
|---|---|---|
| the writers | `fronts` (§1d top-2 per side: BUILDING / STALLED / UNWINDING, peak and slope), `sides` (the 2×2 per 5-min slot on nine strikes, scaled to yesterday's morning), `jarvis.reads` WRITER FLOW ±7 (3-min OI change summed ATM ±7, UP / DOWN / PAUSED / BACK / RISK), `handshake` (push → HELD / DEFENDED / BROKEN / TRAPPED / BREAK FAILED, at the strike and ±2, who opened), `trapped_inventory`, `chainside`, `warmap`, `chain_metrics`, `gamma` (Black-76 IV, dealer GEX, max pain) |
| order flow | `effort` (lots per point at a fresh extreme — the one read that survived two holdouts), `handshake.book_flow`, `prints` (POC / VAH / VAL / HVN / LVN / stacked imbalances, the extension's math ported), `ladder`, `impact` (lots per tick), `sweep` / `absorption` / `senses`, `vpin`, `palat` (TOP / BOTTOM BAN SAKTA from her P marks) |
| the leg and the word | `legs` (the LEG, pause vs reversal, HOLD / WATCH / PALAT?), `reader` (shadow legs), `decode` (trajectories + one call), `read` (THE READ, OI first), `board` (agreement n of 5), `signals`, `onesided` (§1o day type), `daytype`, `regime` |
| where | `levels` (PDH / PDL / PDC / PWH / PWL / OPEN / ROUND / MAX_PAIN / GAMMA_FLIP / walls, frame on every level), `pools` (where size rests), `hunt` (which runway pays), `dwell`, `trap` |
| her setups and her trade | `band_rotation` + `contract_bars` (the zone, §1b / §1r), `confluence` (§1i), `faded` (§1n), `ride` (§1j), `hold2` (§1m), `fold`, `plan`, **`voice`** (THE ONE VOICE: EXIT > WARN > TIGHTEN > HOLD), `trademap` (push, range used, pullback zone, premium path, W-BLEED), `sensex_flow` (§1q) |
| cross-index | `xindex` (X1 SYNC · X2 EXTREMES · X3 LEAD · X4 WALLS · X5 POTENTIAL · LOOK HERE as a count), `jarvis.reads` ALL 3 |
| the record of itself | `rank` ("kitna bada" against same-clock history), `coverage`, `feed_health`, `messages` (one line per change), `telegram_out` / `telegram_in` (`/now`, `/last`), `story`, `grounds` |
| the seller's desk | `surface` (which points on the smile are rich), `drag` (the buyer's tax, measured), `direction` |

Jarvis reads the first family and the leg. `jarvis.NOT_READ` (jarvis.py:779) plus A194 name **19 reads the tool already
has and Jarvis does not consume** — effort, onesided, levels / prints, rank, confluence_log, voice's marked trade, Board,
THE READ, gamma, xindex, PDH / PDL / PDC, range used vs EM, BADA PRINT, VPIN, dwell, PCR change, wall migration, DECODE
lines, footprint events — and five with no source anywhere (book depth read, points per minute, IV per strike, expiry
mode, India VIX).

### 2.3 What is unique — what no vendor screen and no algo_ai has

1. **Writers at levels, per minute, as rates.** Her method (GAPS §2.2, §2.8): in Indian index options the writers are the
   market. The tool reads the 2×2 (CE add / cover × PE add / cover → REAL / BACKED / CAPPED / SQUEEZE / HOLLOW / FLAT),
   the ±7 sum per 3 min with its peak and fade, the top-2 fronts' state, and the handshake. On 29 Oct the 10:08–10:11 leg
   read CE −47.0L / PE +27.1L; at the 10:30–10:41 top CE covering went to 0 then +7.2L and PE building fell to +4.9L
   [M, spec §17 amendment 2]. algo_ai has two walls and one ratio, once.
2. **The handshake.** 31 pushes on 29 Oct, all answered, 11 BROKEN / 16 no answer; every BROKEN / DEFENDED answer on
   27–30 Oct held at the next minute [M, review §2, DECODE-GAPS §3]; the band rule (G1) turned 24 → 16 "no answer".
3. **Causal replay.** `build(day, idx, upto)` reads minutes < upto only and `test_the_reads_are_causal_too` holds. The
   25-day atlas (57 calls, every minute's word) fell out of it in one evening [M, A192]. algo_ai cannot replay a day; it
   has no day.
4. **Health as a read.** CAN'T SEE replaced a stale UP that cost −38 on 30 Oct; Dext missing, chain missing, BANKNIFTY
   too small, late start, FILL — each named with its span (rule 6: "we could not check" is its own sentence).
5. **Pre-registration as a product feature.** §1b–§1r are signed with sha256 anchors; forward logs are written before
   outcomes; rule 4 forbids a hit rate on screen. This is a compliance function a prop desk pays for; here it is in the
   code (`trigger_log.py` refuses to print a rate).
6. **A research sieve already run.** oi-lab scored 291 read × variant × side rows over two holdouts [M, `flow/AUDIT.md`
   §3]: only **effort per point** survived (λ ≥ 2× at a fresh high → reversal 75 % vs 60 % base, n 87; λ ≤ 0.5× at a fresh
   low → continuation 77 % vs 54 %, n 119); **CVD divergence at highs is inverted** (47 % vs 60 %); **whole-book stacking is
   inverted** (32 % vs 44 %: "a stacking bid is a target, not a floor"); OI speed into the pivot was killed as look-ahead
   (AUDIT_OI E6). Most retail order-flow tools sell the inverted reads as features.
7. **Three indices as one market, with her rule.** `xindex` X1–X5; §1q SENSEX reads NIFTY's flow plus its own OI; SENSEX
   futures (687–3,419 lots a day) never vote.

---

## 3. The world they haven't seen: capabilities

Ranked by how much each helps HER trade at 09:20 with real money. Size: **evening** (one after-close build) · **week** ·
**month**. Every input named is on disk or in a module today unless marked *new*. algo_ai's column says what it cannot do.

| # | capability | what she sees on screen (English word · chip · number) | reads | size |
|---|---|---|---|---|
| 1 | **The word that holds** | `TREND ▼ since 09:56 · WITH 4 · AGAINST 1 (speed slow) · PALAT at 22,912f` | legs lean + a writers-first count: Sides, ±7, wall ahead, last answer, top-2 under water, fut-OI quadrant, speed, ALL 3, her setup | week |
| 2 | **One voice in her trade, and it knows she is in** | `HOLD · PULLBACK · no change (Δ +372, PE front BUILDING) · stop 22,517f (HOLD v2)` and `/mark NIFTY 23000 PE buy 325` from any face | `voice.py`, `hold2`, `trademap`, `fold`; the `/mark` grammar (T1a) | 2 evenings |
| 3 | **A buyer's line and a seller's line from one frame, and Jarvis picking** | `BUYER · CE 23,000 on the pullback · needs +62 pts today [I ×1.15] · EM left 40 → thin` / `SELLER · PE 22,900 ATM with trend · floor 22,900 PE 186L BUILDING · IV 13.4 vs RV 9.8 → rich · fold = HOLD v2 line` | §1h EXPRESSION (`expression.py`, logged in `data/hold/expr_<day>`: five facts, refusals R1–R6, the writer's word), `trademap.em`, `surface` (rich points), `server._realized_vol` (close-to-close, last sessions), `drag`, fronts, premium path (A57) | week |
| 4 | **NO TRADE as a first-class state** | `NO TRADE · quiet since 13:34 · ends when ±7 ≥ 10L/3 min or a wall BREAKS` / `NO TRADE · can't see since 12:41` / `NO TRADE · shock 5 min` | spec §15.2 states; Jarvis health; the call | evening |
| 5 | **The day atlas, live** | at 09:27–09:59: `FIRST HOUR · trend call window · legs flipped 0 · z 2.1 · at day low` → `ATLAS: this shape, 11 days: +9 / −2 (in-sample 19–30 Oct)`; at 11:30: `ATLAS: 10:00–12:59 call · 2 flips · inside 1σ · leg 140 → the losing shape (32 of 37)` | `BEST-TRADES-ATLAS` tables as a JSON the frame joins; legs day flips, z, location | evening |
| 6 | **Where: a level ledger with s / f on every line, FIRE from real levels** | `STOP 23,136f (zone) · SL POOL PWH 23,155s · T1 pVAH 23,058f · T2 PE wall 23,008s / 23,051f · ROOM 44 to MAX PAIN` | `levels`, `prints`, `pools`, `gamma`; the dream mockup's `dream_build.py` FIRE logic (built, five days replayed) | week |
| 7 | **A brain that knows its own record, intraday** | `TREND ▼ since 09:56 · −200 so far · PALAT? said 3× · came true 0× · blind 0 min today` | `data/jarvis/call_<day>.jsonl` (write-once per minute; does not exist yet), `legs` rows, health | 2 evenings |
| 8 | **Watches that reach her phone with the read at the touch** | Telegram: `22,800s touched 11:42 · ±7 DOWN −14L · last answer BROKEN 22,850 PE · fut OI covering −1,200 · WITH 3 · AGAINST 1` | `POST /api/jarvis/cmd`, `telegram_out` budget, the card | 2 evenings |
| 9 | **Magnitude, apart from direction** | `HOW MUCH · day CHOP · range used 0.7 EM · VIX 13.4 +0.6 since open · σ 26 · CPR narrow` | `onesided`, `trademap` l4, `levels` (CPR), India VIX quote (*new*: one Upstox quote per minute) | evening |
| 10 | **Cross-index as one market: lead and lag, not only sync** | `SENSEX led by 2 min · BANKNIFTY failed its low · DIVERGENT → ends at 23,000s` | `xindex` X2 / X3 (logs 125 rows a day, read by no face), ALL 3 | evening |
| 11 | **The pre-open brief** | 09:00: `TODAY · NIFTY expiry no · SENSEX expiry Thu · events: RBI 10:00 [web] · PDH 23,120s / PDL 22,955s / PDC 23,110s · walls at close 23,000 CE 147L · 22,900 PE 186L · yesterday: short-covering day +100, fut OI −3,200 · atlas window 09:27–09:59` | `levels`, the last chain snapshot, yesterday's `call_` log, one model call with web search, labelled context (T4) | evening |
| 12 | **The evening review that writes itself** | `31 Oct · word changed 14× · PALAT? 2 said / 1 true · blind 0 · her trades vs the word: SELL 09:54 +77 while TREND ▼ · the wrong line: 13:58 RISK at the low` | `call_<day>`, `tools/pause_log.py` (already in `eod_capture.bat`), her marks, messages | 2 evenings |
| 13 | **The replay room with "why?"** | scrub to 11:14 → the card as it stood → `why`: the eight `why` lines of `call()` at that minute → `what if 22,800 breaks?` answered from the frame | `jarvis2.html` scrubber (built), `jarvis.calls()` (built), the model Q&A fenced (§5) | evening (deterministic) |
| 14 | **The terminal companion** (her "inside my terminal") | `jarvis> now` · `why` · `watch 22800s` · `mark SENSEX 74000 CE buy 98.85` · `replay 2026-10-21 10:30` · `wrong when?` | `tools/jarvis_cli.py` (not yet; one file, zero cost) over the same `/api/jarvis/cmd` grammar | evening |
| 15 | **Expiry mode** (G9) | on 0 DTE after 14:00: `EXPIRY UNWIND · covering is not fuel · MAX PAIN 23,000s · pin distance 43 · gamma ×2.1 after 14:30` | `sides.dte`, `gamma` (max pain, GEX), the chain | evening to tag; week to read |
| 16 | **SHIFT and WHO** (G6, G5) | `CEILING MOVED UP 22,800 → 22,900 CE (−12L / +9L in 6 min)` · `BROKEN by writers buying back (fuel)` vs `BROKEN by buyers leaving (no fuel)` | per-strike 6-min change; `handshake.who_opened` mirrored | 2 evenings |
| 17 | **Noise graded against the day's own baseline** | one BADA chip a day, not forty: `BADA 1,502 lots · above every print today` ; `+n` chips collapse | `rank.py` same-clock medians (fixes the 10-bar warm-up blindness, A45 / A58), dream job E grades NOISE / WHISPER / REAL / LOUD | week |
| 18 | **Learning that is forward-judged, never backtested** | the evening sheet: `ARM CHECK pieces · n per cell · 14 / 20 to the bar` ; thresholds change only by her signature with a NOTEPAD line | `pause_<day>`, `call_<day>`, `confluence_log`, the atlas job rerun nightly | evening to automate; months to mature |
| 19 | **What the 1-second book can still give** | display only, graded: `PULLED 5 levels 520 lots at 23,100f` · `impact 3.2 lots/tick (thin)` · the forming 1-min candle sided by the book | `senses` (256 MB a day, read by nothing), `impact`, `ladder`, `handshake.book_flow` | month (a cheap per-day fills log) |
| 20 | **One 10 KB card, every face** | the same word on the Dext overlay, the Trade tab, the War tab, the terminal, Telegram, the phone | incremental per-day frame state; `GET /api/jarvis/card` (P1 #6) | 2 evenings |

### 3.1 The six that matter most, in a few lines each

**1 · The word that holds.** Today the word is the leg's STATE: honest minute by minute, so it changed 78 / 52 / 79 times
a day on the three replayed days and PALAT? fired nine times inside the 21 Oct 473-pt down leg that reversed zero times
[M, review §2]. The fix is three layers — LEAN (changes only at PALAT) → STATE (as now) → ACTION (spoken at her 3-min
close, needs two closes to change, an EXIT-class event speaks at once) — and the writers deciding: a WITH / AGAINST
count in GAPS §4 order with the pieces named. The dream mockup's 12-piece ARM CHECK already separated the 21 Oct red-leg
buys (0 / 11, 8 against) from the 26 Oct bottom that held, on five days, with no threshold tuned to any of them [M,
dream REPORT]. Proof on the 25-day replay: word changes → ≤ 15 a day; PALAT? episodes vs true flips (21 Oct 9 vs 0);
the opening (LEG_MIN = max(40, 2U); before 10:00 the word is OPENING) → 30 Oct's 7 flips in 38 min counted after.
algo_ai: one word a day, never revised.

**2 · One voice, and it knows she is in.** THE ONE VOICE (`voice.py`, EXIT > WARN > TIGHTEN > HOLD with one stop) and the
TRADE MAP are built and committed; Jarvis's MANAGE judges zone triggers instead — a second voice on a different subject
(review §3.4). The fix is a subject, not a module: MANAGE reads her marked trade. The blind spot in front of it: nothing
reads her positions, her marking stopped after 6 Oct (A22), and she trades on several brokers with Upstox only as the
data feed [M, ALGO-AI-TAKE T1, corrected 31 Oct]. So `/mark NIFTY 23000 PE buy 325` and `/flat` in one grammar on
Telegram, the terminal and the Jarvis box, writing to the same trade record her Float mark writes. Then the voice speaks
on every face the minute she is in. algo_ai reconciles from one broker; she needs broker-neutral.

**3 · Both lines, and Jarvis picking.** Her words: *"i buy and sell option as per the market condition … if engine
thinks it's better to sell the put at this location than i would sell option"* (25 Sep) and *"for selling also i look
for strike atm or even itm if the market is my side or there is a trend"* (26 Sep). §1h EXPRESSION is registered and
logged (`data/hold/expr_<day>.jsonl`, 1.5 MB on 29 Oct); Jarvis shows it and does not re-derive it. What the frame adds
to each line: the buyer's "is it worth paying for" (required move = ATM premium × 1.15 [I] against EM left,
`trademap.em`; the buyer's drag from `drag.py`), the seller's "is it paying me" (the chain's ATM IV against the server's
close-to-close realized vol, `server.py` RV_SESSIONS 6 [M], and `surface.py`'s rich points; the premium path and W-BLEED
gauge from `trademap`; the fold line from HOLD v2). The pick, as the trader
[I, for her signature if it becomes a rule]: TREND day + REAL / BACKED fuel + rich IV → **sell the other side ATM with
the trend**; a fresh BREAK with cheap premium and EM left ≥ the required move → **buy**; CHOP → the band is the seller's
place (her zone) and a buy needs a BREAK; 0 DTE after 14:00 → no new buy. Both lines always; the one Jarvis prefers is
marked, the other stays visible.

**4 · NO TRADE as a thing.** The seller's first question (seller doctrine, 25 Aug: *"the most profitable decision a
seller makes all year is not selling"*). On 30 Oct the call read NO TRADE 55 of 77 times, every one in the cleanest leg
saying "▼: nothing" [M, JARVIS-DAY §3]. The state exists in the spec (§15.2: quiet / can't see / shock / expiry / after
15:00); what is missing is the reason and the exit condition on the line, and silence on Telegram. One evening.

**5 · The atlas, live.** 25 days measured, descriptive, no rule [M, A192]: the first TREND call between 09:27 and 09:56
was positive on 9 of 11 days (7 ≥ +40); at or after 10:00 on 1 of 9 (0 ≥ +40); the losing calls were made 10:00–12:59
with the lean already flipped twice (32 of 37), inside 1σ (25 of 37), on a leg already ≥ 120 pts (13 of 37); on rotation
days the high and low formed in her zone, u2–u3 / d2–d3 (17 of 25 readable); the PALAT exit gave back 3,779 pts. These are
counts she can see *while it is happening*: the frame already has the clock, the flips, z and the leg size. The screen
says what shape today has and how many days looked like it — never a rate, and it says "in-sample 19–30 Oct" where it
is. algo_ai cannot compare today with any day.

**6 · Where, from real levels.** Her 27 Oct ask: *"mark the target, stop loss … previous day low, close, previous month
high … LVN, HVN … OI floor … any important level that we have here."* `dream_build.py` already does it on five replayed
days (REPORT: 21 Oct 09:45 FIRE 23,088f · stop 23,136f · SL pool PWH 23,155f · T1 pVAH 23,058f · T2 PE wall 23,008f · all
three touched). It lives in a mockup; it belongs in the frame, with the one-basis-per-minute rule (fold's 3-min median,
A60) and the native frame on every level.

### 3.2 On the rest

- **7 · Self-knowledge** needs the forward log that does not exist (`data/jarvis/` is absent [M]); `calls()` already
  recomputes the card per minute, so the log is a write. A Jarvis that can say *"I have cried wolf three times today"*
  is the one she can trust at the fourth.
- **8 · Watches** are "Telegram (simulated)" in page JS today (review §3.6); server-side they survive a reload and carry
  the read, not just the touch. Her 28 Oct words: *"tell it to look for any level it looks at it and maybe send me a
  telegram message."*
- **9 · Magnitude**: algo_ai's one good idea (`compute_volatility_confidence`), taken as named rows, never as its 0–100.
- **10 · Lead / lag**: `xindex` X3 stamps who turned first this time; §1q makes SENSEX one switch on the same brain.
- **11 · Pre-open brief**: the only place web search earns its cost (T4). One call, labelled context, never a vote.
- **12 · Evening review**: her standing rule is that the forward record *is* the review (26 Oct). Today the record of
  what the screen said is missing; with it the review is a render, not a recomputation (A175: refills change the past).
- **13 / 14 · Replay room and terminal**: both deterministic, both zero cost, both one file; the terminal is exactly
  algo_ai's `run_headless.py` shape (T7).
- **15 · Expiry**: 27 Oct poisoned every OI read (G9); `sides.dte` and `gamma.py` max pain already exist.
- **17 · Noise grading**: `rank.py` is the "kitna bada" she asked for and nobody wired; it also ends Jarvis's 10-bar
  morning blindness.
- **19 · The book**: display, never a vote — oi-lab's whole-book stacking is inverted and sign persistence is inverted;
  what survives is effort per point (live) and the honest pull / sweep description with its day grade.
- **20 · The card**: the whole day is rebuilt every 20 s (3–10 s, 1.2 MB) for three pollers and the GIL stalls refused
  connections (A180); the companion needs a per-day state that appends a minute and a 10 KB card.

---

## 4. Jarvis's decision stack — all of it, advisory

Her words: *"all these decisions in it."* One frame, one order (GAPS §4: writers before price), both ways always, every
stage naming its inputs and its "could not check". Nothing in it places an order.

| stage | the question | inputs (module / record) | on screen | could not check → |
|---|---|---|---|---|
| 0 **HEALTH** | can I see? | book holes, Dext minutes (D / B), chain gaps, clock lag (BLIND_MIN 2), BANKNIFTY readable?, late start | `every source live` / `CAN'T SEE since 12:41` / `Dext missing 13:25– (flow from the book)` | the word is CAN'T SEE; nothing else speaks |
| 1 **DAY TYPE / GEAR** | trend or rotation? which setup is legal? | `onesided` (§1o TREND / PIN / CHOP / MIXED), `daytype`, flips so far, the atlas shape, the clock (first hour / lull / after 14:30 / after 15:00) | `DAY · TREND ▼ since 12:50 · flips 1 · atlas: first-hour trend day` | `DAY · ? (fewer than 10 one-sided bars)` |
| 2 **LEAN** (the leg) | which way, and is this a pause or a reversal? | `legs` (LEG ≥ 40 pts, PALAT at ½ leg / 1U), the risk items (k1 loading, premium vs delta, coil, depth, marks) | `LEAN ▼ · leg 103 · PAUSE · HOLD (clean: k1 loading +3.2L)` | an item absent is named in `missing`, never a zero |
| 3 **THE COUNT** (writers first) | who is with the lean, who is against? | Sides word, ±7 state and push, wall ahead's state, last answer, top-2 under water, fut-OI quadrant, speed, ALL 3, her setup | `WITH 4 · AGAINST 1 (speed slow)` — pieces named on hover | a piece that cannot be read lowers N, never counts against |
| 4 **ACTION WORD** | what do I do with it? | LEAN + COUNT at a 3-min close, two closes to change; EXIT-class at once | `TREND ▼` / `HOLD` / `WATCH` / `PALAT` / `OPENING` / `NO TRADE (reason · ends when)` | blind → CAN'T SEE |
| 5 **HOW MUCH** | is there a move to pay for? | `trademap.em` and range used, σ, VIX change since open, CPR width, IV vs RV | `range used 0.7 EM · VIX +0.6 · σ 26` | each row says `?` with its reason |
| 6 **WHERE** | the stop, the pool, the targets, the room | `levels` (PDH / PDL / PDC / PWH / PWL / OPEN), `prints` (pHVN / pLVN / pPOC), walls and MAX PAIN (`gamma`), her zone's stop (§1b, never moved), the 3-min basis | `STOP 23,136f (zone) · SL POOL PWH 23,155s · T1 pVAH 23,058f · T2 PE wall 23,008s · ROOM 44` | a missing level kind is named (`no PW levels: 13–15 Oct unrecorded`) |
| 7 **EXPRESSION** | buy the option, or sell the other side? which strike? | §1h EXPRESSION (`expression.py`) as logged; the buyer's required move vs EM left; the seller's ATM IV vs realized (`server._realized_vol`), premium path, fold line; DTE; her practice (ATM / ITM with trend) | `BUYER · CE 23,000 · needs +62 · EM left 40 → thin` / `SELLER · PE 22,900 ATM · rich · fold = line 22,517f` with Jarvis's pick marked | `premium path ? (chain missing)` |
| 8 **WRONG-LINE + TWO SCENARIOS** | what makes this wrong; what happens next either way | `call()` already writes both: the level that ends the read, scenario ▲ / ▼ with triggers | `WRONG IF 22,800s PE adds ≥ 10L / 3 min` · `▼: 22,800 BREAKS → next floor 22,700 PE 92L` · `▲: BACK at 22,800 → VWAP 22,891f` | — |
| 9 **IN TRADE** | hold, tighten, warn, exit? | `voice.py` on her marked trade (`/mark`); `hold2` line and lock; `trademap` pullback zone, BADA at the level, W-BLEED gauge; §1q for SENSEX | `HOLD · PULLBACK · no change` / `TIGHTEN line 22,600f` / `WARN GAVE UP PE 22,700` / `EXIT line hit 13:46` | no mark → the zone trigger is the subject, labelled so |
| 10 **EXIT** | where did it end, and why | the voice's first-named reason; 15:20; her practice after 15:00 (a reminder) | `EXIT · stop · −23 · 13:46` | — |
| 11 **REVIEW + SELF-SCORE** | what did I say, what happened | `call_<day>`, `pause_<day>`, her marks, `confluence_log`; the atlas rerun | the evening sheet (counts) and the intraday line `PALAT? said 3× · true 0×` | a day with holes says how many minutes it could not score |

### 4.1 The stack on the record (what it would have said)

**29 Oct, a buyer's day and a seller's day at once** [M, atlas §2, JARVIS-DAY, A160–A173]. 09:54: LEAN ▲, leg 138, z 1.8,
writers BACK, fut OI fresh longs, ALL 3 ▲ → **TREND ▲ · WITH 5 · AGAINST 0** in the first-hour window. HOW MUCH: range
used 0.5 EM. WHERE: the wall ahead 22,800s CE (broke 10:08), PDH above. EXPRESSION: seller's line *SELL 22,700 PE ATM
with trend*; buyer's *BUY 22,800 CE on the pullback*; Jarvis's pick: seller (IV rich into a trend day). 10:38: ±7 RISK
at the top, delta −462 → **WATCH**, not PALAT (writers lag at a pause, 17 of 19 [M, noise §4]); the top held two hours
and the word should have said *WATCH · range · hold the sale*. 13:33–13:54 the afternoon leg on short covering (fut OI
−1,986 / 30 min, calls covering ITM): Sides REAL → the count turns WITH again. 14:06 her ask *"validate 74000 CE"*:
Validate said WAIT, not GO; 74,000 CE went 99 → 93.6 → 104.65 while call writers came back at 74,000 (78.7L → 84.4L) [M,
A170 / A172]. Both lines were right to be shown; the pick was the seller's.

**21 Oct, the day the zone fought the trend** [M, dream REPORT, atlas]. 09:45 SELL at 23,088f: ARM CHECK 1 / 7 with the
PE front BUILDING *against* it — and it ran +148. The writers' lead read "who defends" when it should have read "who is
trapped" (dream §8.2, a PROPOSED registration for her signature). 09:56 TREND ▼ (leg 103, z 2.5, ±7 DOWN, wall ahead
UNWINDING) → the first-hour trend shape; the stack says *ride (RIDE §1j), the band is not a top today*; the zone's five
BUYs 11:18–14:00 read 0 / 11 and 2 / 11 and 4 / 11 against — the count would have refused each; the per-candle voice
named the 14:00 trade's change 22 minutes before its stop.

**22 Oct, the trap** [M, atlas §4, dream REPORT]. CHOP by 11:30, 10 leg flips, three zone entries in 12 minutes. The
stack: DAY CHOP → the band is the place and the leg is a trap → **NO TRADE on the leg**, the seller's line at u2 / d2 with
VWAP as the first stop (23 of 24 band turns crossed it) and band-to-band as the big case (10 of 24, 81–308 pts). The
10:12 SELL arm read 6 / 10, the best count of the week.

### 4.2 Both ways, by construction

Every row of the stack has a CE and a PE mirror (DECODE-GAPS §1: every UP scenario has its DOWN with the sides swapped).
A seller is not an afterthought: her sale is a directional trade at the money, folded by the same four reads — zone,
order flow, OI, VPIN — never by a strike touch or a candle close (26 Sep, 28 Sep). The seller's half of the screen is
the seller doctrine's five questions in her shape: *bechna hai ya nahi* (NO TRADE / the gate), *kahan khadi hoon* (strike
distance in σ of the straddle, from `trademap.em`), *paisa mil raha hai* (the ATM IV against `server.py`'s realized vol, with `surface`'s rich points), *zinda rahungi* (the
fold line and ROOM to the next wall), *kitna kama rahi hoon* (the premium path, W-BLEED).

---

## 5. The brain: how it is built so it stays honest

```
          record (book 1 s · chain 10 s · Dext 1 min · tape · logs)          <- read-only, write-once
                               |
                     jarvis.build (causal, per minute, incremental)
                               |
      +------------------------+-------------------------+
      |                        |                         |
  RULES ENGINE             MEMORY                     COMMANDS & WATCHES
  every fact, every        call_<day>.jsonl           POST /api/jarvis/cmd (one grammar)
  verdict, the count,      pause_<day>.jsonl          cmd_<day>.jsonl, watches -> telegram_out
  the lines, health        the atlas (25 days -> n)   order words refused: "I read, I don't place"
  deterministic, tested    her marks + /note
      |                        |                         |
      +------------------------+-------------------------+
                               |
                    THE CARD (<= 10 KB, one per index per minute)
                               |
       +-----------+-----------+-----------+-----------+-----------+
    Dext overlay  Trade tab  jarvis2    terminal     Telegram    THE MODEL (the voice)
    (her chart)   (J3)       (replay)   (CLI)        (phone)     narrates on change, answers her,
                                                                  reads the card only, never the verdict
```

**The rules engine owns every fact and verdict** (spec §16.3, her choice). Deterministic, causal, logged every minute,
scored every evening. It is the only thing that marks a level, sets a word or declares NO TRADE.

**The model is the voice**, behind one seam (`jarvis_voice.py`: provider = Claude or Gemini, algo_ai's `ai_sentiment`
shape). It is called on an ACTION-word change or on her question, never per second. Input: a cached prefix (its rules,
the English word table, her standing rules) + the card + today's stamps + her watches + the question. Output ≤ 3 lines.
It never changes the verdict (the engine's word is printed beside it); it narrates, notices what no rule was taught
("the floor moved up twice while you were in; that is the third time today"), writes the pre-open brief, answers
"why?" from the `why` lines. On no key or any error the engine's fixed sentences show and say so. The face never goes
blank.

**How a question flows — "what if 22,800 breaks?"**
1. The command parser (deterministic) finds `22,800` → is it in the card? yes: `22,800s PE · 186L · BUILDING · floor`.
   Not in the card → `I don't have 22,800 in today's frame; nearest: 22,850 PE, 22,750 PE`.
2. The engine already holds scenario ▼ for the floor: `BREAKS → next floor 22,700s PE 92L · ROOM 100 · wrong if PE adds
   ≥ 10L / 3 min at 22,800`. That is the answer's skeleton.
3. The model gets the card + the scenario and writes ≤ 3 lines in English.
4. **The fence** (code, not prompt): every number in the answer must exist in the card or the scenario (digit tokens ⊆
   the card's set, Indian grouping normalised); no `%`; no order words (`buy`, `sell`, `lots`, `order`, `place`,
   `square off`); length ≤ 3 lines. Any failure → the engine's scenario sentence is shown with `(voice fell back)`.
5. The exchange is appended to `cmd_<day>.jsonl` with the card's minute, so the evening can read what she asked and what
   it said.

**Memory**: its own calls today (`call_<day>`), the pause log, the atlas (grows by one day every evening), her journal
(`/mark`, `/note RBI 11:00`), the NOTEPAD as the gap log. **Commands**: spec §15.3's grammar in English — `line`, `zone`,
`watch`, `remove`, `list`, `why?`, `next?`, `status`, `wrong when?`, `mark`, `flat`, `note`, `replay` — one grammar on
the chart box, the terminal and Telegram; persisted; anything with an order word gets *"I read, I don't place"*. **The
replay room**: `jarvis2.html` with the scrubber over `calls()`, plus `why` and the fenced Q&A at any past minute.

**Cost [I]**: at list price for `claude-opus-5-5` ($4 / $20 per M in / out, cache reads $0.20 per M; the skill's cache
of 2026-10-06), ~60 calls a day × ~5K in (4K cached prefix + 1K card) / 200 out ≈ $0.53 a day cached, $1.44 uncached;
the pre-open brief with web search ≈ $0.11. At ₹85–88 per $ that is **≈ ₹50–135 a day, ₹1,100–3,000 a month** on 22
sessions; `claude-sonnet-5-5` halves it. The `anthropic` SDK is not installed yet [M, review]; the key is hers, git-ignored
like `telegr/`, with a monthly cap she sets.

---

## 6. The judge's table: algo_ai vs this

| | algo_ai | TapeMap + Jarvis (today → with §3) |
|---|---|---|
| signals | 7 aggregates, equal ±5-pt hand weights, "not backtested" (README) | ~110 read modules; the writers at levels per minute; one read (effort per point) that survived two holdouts, three that were shown inverted and are not used |
| cadence | one call a day, at the open | every minute, held to a 3-min close, three indices → one card |
| the AI | a 3-word news mood nudging the direction | the narrator of a measured frame, fenced to its numbers, never the verdict; the one web search is the pre-open brief |
| honesty | 0–100 "confidence", 5–95 % probability on screen | counts (`WITH 4 · AGAINST 1`), "could not check", health first; no % by rule 4 |
| evidence | none kept | forward logs written before outcomes since Aug; 25 replayable days; a research sieve (291 rows) |
| in a trade | ₹ stop / target / time / 15:15 force exit, blind to the market | one voice: EXIT > WARN > TIGHTEN > HOLD from zone, order flow, OI, VPIN, the wall that gave up; the pullback told from the change |
| brokers | Zerodha Kite; buyer only; NIFTY (BANKNIFTY / FINNIFTY / MIDCPNIFTY named) | broker-neutral (Upstox is the feed only); buyer AND seller; NIFTY, SENSEX on NIFTY's flow + its own OI; BANKNIFTY says "too small to read" |
| state | `settings.json` | a recorded market, 2.9 GB, causal to the minute |
| what it does well, and what we take | the fence around the AI call (fixed prompt, JSON-only, safe default, provider seam, the prompt shown on the panel, her note appended) → **T4**; reconcile-on-restart → the broker-neutral **`/mark`** (T1a); dry-run discipline → our "display only, no order path"; hot-reloaded exit settings → **thresholds in one JSON, re-read per build, every change a NOTEPAD line** (T5); India VIX as context → **a VIX rate row** (T2); "is this CE worth paying for" → **required move vs EM left** (T3); magnitude apart from direction → **HOW MUCH** (T6); the headless console → the terminal Jarvis (T7) | |
| what we leave | ORB (dead, §2), gap → straddle (no edge; she sells rich IV), PCR level and OI-wall ratio → probability, the nudge sum, the 0–100 score, the AI as a direction vote, the ₹ loop, the Buy buttons, Kite | |

---

## 7. Roadmap, in evenings, with the measurement that proves each step

Nothing here changes a registered rule. Leg thresholds are [I] and move only with a NOTEPAD reason. Restarts are hers,
never in market hours.

| when | build | the number that proves it (on the 25-day replay unless live) |
|---|---|---|
| **week 1 (P0)** | LEAN → STATE → ACTION; LEG_MIN = max(40, 2U) and OPENING before 10:00; the WITH / AGAINST count; wire the 19 unread reads as named rows; SENSEX frame flow = NIFTY's; BANKNIFTY one line; RISK as an event (G2); SHIFT (G6); WHO on BROKEN (G5) | word changes a day 79 / 52 / 78 → **≤ 15**; PALAT? episodes vs true flips 21 Oct **9 vs 0 → ≤ 2**; 30 Oct opening lean flips **7 → ≤ 2**; `NOT_READ` **19 → 5**; SENSEX "?" minutes **384 → 0**; BANKNIFTY ticks **40 → 1** |
| **week 2 (P1)** | incremental frame + `GET /api/jarvis/card`; `data/jarvis/call_<day>.jsonl`; ACTION-word line on the stream and Telegram; `POST /api/jarvis/cmd` with persisted watches; `/mark` and `/flat` | build per pass **3–10 s → < 0.5 s**, card **≤ 10 KB**; refused connections under a Jarvis build **11 of 40 → 0 of 40** (A180's test); the first day with a `call_` log; Telegram lines a day within the budget; a watch that survives a restart |
| **week 3 (P2)** | `tools/jarvis_cli.py`; `jarvis_voice.py` with the fence; the pre-open brief; the self-knowledge line; the evening sheet renderer | fence violations caught (count) and fallbacks a day (count); the brief exists by 09:05; the sheet renders from logs alone |
| **week 4 (P3)** | Dext overlay readability (A189) reading the card; FIRE from the level ledger in the frame; expiry mode tag; HOW MUCH line; VIX quote; noise grades | chips at the right edge no longer pile (screenshot); every level s / f with the 3-min basis; 0-DTE afternoons say EXPIRY UNWIND |
| **month 2** | J3 (the Trade tab) or the Dext face as THE face (her word); the depth fills log; the atlas job nightly; the forward count sheet | the first ARM-CHECK cells reach n ≥ 20 (at 2–3 arms a day per side, ~2 weeks per cell); the atlas table grows from 25 to 45 days with the second half marked out-of-sample |

**Costs.** Everything except the model is zero: her laptop, the Upstox feed she already has, Telegram. The model is
≈ ₹50–135 a day [I] (§5), called on change only. GoCharting (₹1,800 a month) is the thing she wants to retire (6 Oct);
the Dext face reads the same card.

**What is still in-sample.** `legs.py`'s thresholds were set on 19–30 Oct; 22 Sep–16 Oct never touched them. The atlas's
first-hour shape holds in both halves (5 of 6 vs 0 of 5; 4 of 5 vs 0 of 4) but n is 11 and 9. The dream mockup's ARM
CHECK was read on five days. `effort.py`'s survivor bands are a hypothesis with a pass bar, 19 days. Every [I] stays [I]
until the evening sheet has counted it forward.

---

## 8. What not to build, and why

| do not build | why (source) |
|---|---|
| ORB, the overnight gap-fade, d2 line entries, selling any upper band, the compression / trap filter, squeeze + falling OI = fade, the SMC layer, the engine event stream, d3 on stocks | research-findings §2, the dead list: each REJECTED on its own scorer; some on five independent datasets |
| CVD divergence at highs as a reversal read | oi-lab AUDIT §3.2: INVERTED (47 % vs 60 % base, both holdouts); its control "CVD confirms the high" reversed more |
| whole-book bid / ask stacking as a floor or ceiling; five minutes of one-sided prints as continuation | AUDIT §3.2: inverted (32 % vs 44 %; 44 % vs 56 %). Depth is display, never a vote (§3 #19) |
| OI speed at an extreme as hold-vs-break | AUDIT_OI E6: killed, look-ahead (40 / 40 slow pivots "held") |
| VPIN as an exit sign; the slow VPIN alarm | A198 retracted (the window reached before the entry; one stream counted 3×); A199 scored the slow line on its own terms: KILL (35 alarms, 14 expanded, 14.1 expected) |
| a fourth leg engine, a second fuel, a sixth call-maker, a third in-trade voice | review §3.4: three leg engines, two voices and five call-makers already exist; Jarvis reads them, it does not join them |
| any hit rate, win rate, probability or confidence on a screen or in a design | CLAUDE.md rule 4; §5e: the bar is hers, stated before the numbers are read; under 15 per side is inconclusive |
| the AI as a direction nudge; PCR level; two walls vs yesterday's close | ALGO-AI-TAKE §3: the direction comes from the frame; OI is read at levels per minute; PCR counts only as a change |
| a GoCharting overlay in parallel with the Dext face | her goal is to retire GoCharting (6 Oct); one card, the faces she keeps |
| anything that places or routes an order | CLAUDE.md rule 10; see §9 for the only way that line moves |

---

## 9. Beyond today's rules (needs her signature)

Her correction: *"no constraints, we can do anything."* So this section imagines past the lines, and names the rule each
idea would change, so she can decide. Nothing here is built, planned or hinted at on a screen until she signs it. The
two lines she keeps are the first two rows.

| idea | what it would give her | the rule it changes | what it would need | the trader's view [I] |
|---|---|---|---|---|
| **B1 · Execution assistance.** A one-click order ticket pre-filled from the frame (instrument, strike from the EXPRESSION line, her lot setting, the HOLD v2 line as the stop, the level ledger's T1 as the target), opened in HER broker's own order form via a deep link or the clipboard; TapeMap never sends it | the thirty seconds between the word and the fill, with the strike and the stop already right | **CLAUDE.md rule 10, "no order path, ever"** — a pre-filled ticket is a path even when she presses the button; also the standing memory "never propose reading positions from a broker API" (28 Sep) | a per-broker link format; a confirm step she owns; a kill-switch; the ticket logged like a message | not before the word is quiet (≤ 15 changes a day) and has a forward log with a month on it. A brain at 5.5 / 10 should not be near a ticket. If ever: clipboard text first ("SELL NIFTY 22900 PE 1 lot · stop line 22,517f"), never a button |
| **B2 · Auto-marking fills.** Read-only positions from each broker she names, merged and tagged `src: <broker>`, so the voice knows she is in without `/mark` | the in-trade voice on every trade, including the ones she forgets to mark | not rule 10 (read-only), but the 28 Sep memory above and her 31 Oct correction (Upstox is the feed only) | a daily token per broker; a merge rule when two brokers hold the same strike; her Float mark still wins | T1(a) `/mark` first; this second, per broker, on her word (ALGO-AI-TAKE T1b) |
| **B3 · Bracket suggestions.** The stop / pool / T1–T3 as a bracket she can accept into the broker's form | the level ledger acting, not only showing | rule 10 (as B1) | B1 | the display half is §3 #6 and is allowed today; only the handoff to a form is beyond the line |
| **B4 · Model-scored reads.** A probability or confidence per read, from the forward log or from the model, on screen | the thing every vendor shows and she has asked never to see | **CLAUDE.md rule 4** ("never print a hit rate / win rate / expectancy / confidence score"); §5e (the bar is hers, stated first; under 15 per side inconclusive) | the forward log (§3 #7) with n ≥ 20 per cell, then a sheet she reads in the evening | counts already carry the information (`WITH 4 · AGAINST 1`; `11 days: +9 / −2`). The evening sheet may show counts per cell; a % on the live screen is the one line I would not cross even with her signature, because the atlas showed what a 9-of-11 looks like at n = 11 |
| **B5 · Self-tuning thresholds.** A scorer that moves `legs.py`'s [I] constants from the forward log, nightly | less evening work | the no-backtest stop rule (§5), "thresholds are [I] until judged forward", and the signature rule (a change is a new registration) | the sheet first; then each change proposed with its count, signed by her | a sheet that *proposes* a change with its count is fine; a loop that *applies* it is a backtest wearing a forward log's clothes |
| **B6 · A model that may change the verdict.** Model-first brain: the engine proposes, the model decides | "your brain in it" in the strongest sense | spec §16.3 (the rules engine owns every verdict; the two never mix) | nothing technical; everything in discipline | not now: the model is confidently wrong in a way no evening can score, and the verdict must be replayable to the minute. Let it narrate for a month; if its "what no rule was taught" lines earn a place in the sheet, register them as rules |
| **B7 · Depth as a signal.** Pulled quotes / sweeps / shelves from the 1-s book voting in the count | the 256 MB a day doing something | oi-lab's inverted finding on stacking; a new registration | the fills log (§3 #19), a forward test, n ≥ 20 per cell | display first; a vote only if the forward sheet earns it |
| **B8 · VPIN WITH at a stall as the exit sign** | her "it works and help" | §1m HOLD v2 untouched; a NEW registration; A198 retracted the first version | a clean since-entry window, a fixed yardstick, n ≥ 15 per side forward | shape seen, rule not earned; log it forward as a row before any chip reads it |
| **B9 · BANKNIFTY on the read; SENSEX futures flow** | two more markets | G14 (BANKNIFTY chain too small: biggest 3-min strike move 0.24–0.52L vs NIFTY's 8.8–18.1L); §1q (SENSEX futures too thin) | new data: BANKNIFTY monthly OI at scale, or a different bar; nothing fixes SENSEX futures | BANKNIFTY as a witness in ALL 3 only; SENSEX stays NIFTY's flow + its own OI |
| **B10 · Sizing from the count** | lots from `WITH n` | "counts, never odds; never a size" (25 Sep) | her risk rule in writing | hers alone; the tool names the stop distance in points and σ, never the lots |
| **B11 · Learning her hand.** The journal (marks, notes, the trades she took vs the word) read by the model in the evening: *"you folded three winners at the first WATCH this week"* | the father-trader's review (28 Sep) | none; display only | `/mark`, `/note`, the call log | the one place the model reads *her*, not the market. I would build this before any of B1–B10 |

---

## 10. Risks and the honest line

- **Thresholds are [I] from 2–10 days.** Every constant in `legs.py` and `jarvis.py` has a reason beside it and none has
  been judged out of sample. 19–30 Oct is in-sample. The 25-day atlas is descriptive and says so on every table.
- **The word flickers 52–79 times a day today** [M]. Until P0 lands, the ACTION word does not exist and the lean is the
  only thing to act on; the first-hour TREND call was right on 21 and 29 Oct and wrong on 5 and 19 Oct.
- **Data holes are real and recur**: 30 Oct lost 78 minutes to the internet; Dext's footprint stops when its tab hides
  (A168: a lag, not a stop — a read must say how many of the newest minutes are book); 13–15 Oct are missing; roll
  week's futures OI is raw until the next contract is recorded (A119); the chain stops at 15:30 while F&O trades to
  15:40; the cash index freezes at 15:15 (CAS). Health names each one; it cannot fill them.
- **The model can be confidently wrong.** My own 11:14 read on 30 Oct was ("range at the top"; +118 followed) and
  Jarvis's rule was right. The fence (§5) keeps numbers honest; it cannot make a narrative true. That is why the verdict
  stays with the engine and the narrator's lines are logged and reviewed like everything else.
- **Three faces, one mockup, and J3 unbuilt.** The Dext overlay works (A189) with readability owed; the Trade tab is a
  plan; `jarvis2.html` is a static page on 8787. The card (§3 #20) is what stops this from becoming four.
- **BANKNIFTY cannot be read and SENSEX reads NIFTY's flow.** Both are stated on screen, not papered over.
- **Nothing here is a promise.** *"Live from day one, scored every evening"* is the discipline: each capability ships
  with the count that would kill it, and the evening sheet is where it earns its place or goes.

---

## 11. What this document could not verify

- Nothing live: Saturday; the server was not started (agent-never-starts-live-server); no replay was re-run. Every
  replay number is quoted from the review, the atlas, JARVIS-DAY, DECODE-GAPS and the dream REPORT, with its source.
- Record sizes and row counts are for 29 Oct only [M, `ls` / `wc -l`]; other days differ (30 Oct has holes; 27 Oct lost
  Dext after ~12:00).
- The algo_ai line counts are the nine `.py` files (4,769); the take sheet's 6,288 includes the dashboard templates.
- The model cost is arithmetic on list prices and an FX guess [I]; the real number is the first month's bill.
- SENSEX and BANKNIFTY replays were not run here (G13 / G14 are quoted from DECODE-GAPS).
- The Dext 0.9.1 face and the War tab were read in code and in A189's probe, not seen on her chart.
