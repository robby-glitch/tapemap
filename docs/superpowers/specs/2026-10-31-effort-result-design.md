# EFFORT / RESULT: VPIN rebuilt from first principles, and her support checklist (DRAFT for her signature, 2026-10-31)

> **DROPPED, 31 Oct, on Fable's review** (`docs/effort-result/fable/FABLE-REVIEW.md`). I checked the three main points
> myself and they hold [M]:
> - **§2 C (the stall split) is mechanics.** At AGAINST stalls a median 5 of the 10 buckets are from before the entry:
>   the push into the band. On since-signal buckets only, AGAINST went on 4 of 10, not 17 of 29.
>   - Bucket count alone (sign-blind) splits it: < 5 buckets since the signal went on 21 of 30; ≥ 10 went on 13 of 43.
>   - The 19 WITH stalls are about 8 market moments, and 8 of them are 27 Oct expiry.
> - **§2 D (the 77-touch table) is an artefact of the moving band.** With the band fixed at the touch: TURN 28, BREAK 42,
>   WALK 7 (not 55 / 11 / 11). 23 live "turns" had first gone past the touch-time 3σ.
> - **§2 A's quote rule already exists:** `handshake.book_flow` (handshake.py:121) feeds the frame's `flow`. Only
>   `vpin.py` uses the tick rule.
>
> Kept as the record. Nothing below is to be built.

## Origin (verbatim)
- **Mary, 31 Oct:** "first lets refine vpin completely and check from first principle and what metrics it uses and than
  we need to look at those metrics how they interact and what we can modify or change or tighten to make it and how we
  can redesign it calling as well so that we read it right what exactly is going on in the market and you also said we
  need to look at cause and effect effort vs result etc like lets say at support 5 things we can like for as a checklist
  that comes to my mind on top is absorption bif limit oder trapped traders aggressive traders and change in delta and
  maybe put in vwap bands and its expansion or contraction where is ib range and when it can go for price discovery .
  lets check this and brain strom on this"
- **The day before (atlas §10):** at a stall, the live VPIN chip WITH her trade meant the move was over. It went on
  0 of 21 times.

**Measured under §1k [M]:** a look at the past on her request, counts only, no rate, no rule. Thresholds were fixed
before the first run. Scripts: `docs/kahani/review/scripts/atlas/vpin_lab.py` and `vpin_turns.py`.

## 1. What VPIN measures today, from first principles

| Step | What `vpin.py` does | What it throws away |
|---|---|---|
| Volume | `vtt` change between ~1 s frames | nothing |
| Who was the aggressor | **tick rule**: uptick = buy, downtick = sell, flat = last sign | the quote: did the trade hit the bid or lift the ask? |
| Clock | volume buckets: 20,000 units (fast) / 60,000 (slow). Fast bucket median 87 s (p10 12 s, p90 237 s) | **time**: how fast the bucket filled (urgency) |
| Per bucket | \|buy − sell\| / V | **the sign** (who) and **the price move** (result) |
| Reading | mean of 50 buckets (fast: ~70 min), then a percentile against today so far | location: band, IB, VWAP, level |
| Hold chip (`fold.py`) | the last 10 buckets: one-sided (\|imb\| ≥ 0.5) count your way vs against, lead ≥ 2 | the price result in the same window |

**The flaw that matters for a trader:** one unsigned number cannot tell two opposite states apart:
- aggressors **winning**: one-sided flow, and price follows;
- aggressors **absorbed**: one-sided flow, and price stops.

The same VPIN number means "go on" in one and "it is over" in the other.

## 2. What the recorded days said

**A. The input misreads the aggressor on some minutes.** Per minute, against Dext (Dhan's own footprint), 19 days, 5,481 minutes:

| Rule | Same sign on clear minutes (\|delta\| ≥ 20 % of volume) | Correlation of the minute imbalance |
|---|---|---|
| tick (live VPIN) | 3,098 of 3,671 | 0.71 |
| **quote** (at or above the previous best ask = buy, at or below the best bid = sell, inside the spread = tick) | **3,347 of 3,671** | **0.83** |

The book's volume matched Dext's (108 %).

**B. One bucket alone is noise.** Each bucket was classified by effort vs result:
- PUSH = one-sided and moved ≥ 0.25U the aggressor's way;
- ABSORB = one-sided and did not move their way;
- VACUUM = two-sided and moved ≥ 0.25U;
- BALANCE = two-sided and did not move.

What came next in 15 min (on = +0.5U the aggressor's way first, back = −0.5U first; quote rule, 4,252 buckets, 25 days):

| Bucket | on | back |
|---|---|---|
| PUSH | 109 | 126 |
| ABSORB | 110 | 118 |
| VACUUM | 171 | 170 |

- Under the tick rule, ABSORB read 81 on / 140 back. That lean was the classifier, not the market.

**C. The 10-bucket window at a stall carries the signal, and it survives the better input.** At the first stall (6 min
with no new extreme of 0.25U), on the 120 band-signal stalls from 21–30 Oct:

| One-sided lead at the stall | live log (tick) | rebuilt, quote rule |
|---|---|---|
| **your way** (your side's aggressors, no progress) | went on 0 of 21 | **went on 0 of 19** |
| **against you** (the other side hitting, price holding) | went on 17 of 25 | **went on 17 of 29** |
| quiet | 34 of 65 | 34 of 63 |

- It also held when controlled for how far the move had gone, for the time left and without BANKNIFTY (atlas §10).
- **At the band turn:** when the old side was still one-sided into the extreme, 7 of 11 turns (quote rule) went band to
  band; with a quiet lead, 2 of 11.

**D. Her checklist at the band.** Every first touch of 2σ after 09:45, NIFTY fut, 25 days: **77 touches** (22 days).
- **TURN** (back inside 1σ before 3σ): 55. **BREAK** (3σ first): 11. **WALK** (neither in 60 min): 11.
- These are her zone's own edges. A first try that called "0.5σ further" a break was wrong for a 2σ → 3σ zone.

| Item, read at the touch | present | absent |
|---|---|---|
| 1 absorption (≥ 1 outward ABSORB bucket of the last 5) | 12: turn 7 · fail 5 | 62: turn 45 · fail 17 |
| 2 aggressors winning (≥ 2 outward PUSH of the last 5) | 14: turn 7 · **fail 7** | 60: turn 45 · fail 15 |
| 2b urgency (buckets filling in < 0.5× the day's median time) | 8: turn 3 · **fail 5** | 66: turn 49 · fail 17 |
| 3 big resting limits (holding side's 5-level depth ≥ 1.5× the other side) | 26: **turn 21** · fail 5 | 48: turn 31 · fail 17 |
| 4 fut OI rose into the touch (the pre-set 0.5 % was never met; shown by sign) | 31: turn 23 · fail 8 | 43: turn 29 · fail 14 |
| 5 delta turned against the push at the touch | 4: turn 4 · fail 0 | 70: turn 48 · fail 22 |
| 6 bands expanding (σ ≥ 1.2× 30 min ago) | 20: **turn 16** · fail 4 | 46: turn 28 · fail 18 |
| 7 IB: touch before 10:15 (IB still forming) | 26: **turn 24** · fail 2 | — |
| 7 IB: after 10:15, outside the IB | 43: turn 27 · **fail 16** | — |
| 7 IB: after 10:15, inside the IB | 8: turn 4 · fail 4 | — |

- **Fail** means BREAK or WALK.
- **The items point both ways.** Limits, expanding bands and an early touch lean towards the turn. Aggressors still
  winning, urgency and range extension after the IB lean towards the break. **A summed checklist score is meaningless**
  (0–5 items present did not separate). It has to be two columns: holds vs breaks.
- **Delta change is a confirmation after the touch, not at it.** At the touch it was present 4 times in 77. CONFLUENCE's
  FLOW ✓ (§1i) is the registered after-the-touch version.
- **INCONCLUSIVE:** n ≤ 26 per cell, in-sample, one instrument. These are shapes to judge forward, not rules.

## 3. Three ways to go

| | What | For | Against |
|---|---|---|---|
| **A. Patch** | quote rule into `vpin.py`; relabel the chip at a stall | 2 small diffs | VPIN stays unsigned and blind to the result. Changing the input breaks the 30-session kill-clock record. The chip is registered |
| **B. EFFORT / RESULT read (recommended)** | a new signed read on the volume clock that does VPIN's job: effort, result and speed in one window, named by who is aggressive | answers her ask directly; reuses the part that measured (10 buckets); exact anytime start from the book file | a new module and log |
| **C. Everything now** | B + the support ledger + the discovery state in one build | one release | the level ledger is still unsigned. Too big to check in one replay |

**Recommendation: B now, then her checklist inside the LEVEL LEDGER (phase 2), then the discovery state (phase 3).**

## 4. The design (B): `effort_result.py`

**Input.**
- The 1-second futures book the server already records: `book_<IDX>_<day>`, with `ltp`, `vtt`, `b` / `a` (5 levels)
  and `oi`.
- Signed by the **quote rule** (§2 A).
- NIFTY and BANKNIFTY each read their own book. SENSEX reads NIFTY's (§1q; SENSEX futures are too thin, A25).

**Clock.** 20,000-unit buckets (`vpin.FAST_BUCKET_V`, kept).

**One read per closed bucket, over the last 10 buckets (≈ 15 min at the median):**

| Number | Definition |
|---|---|
| EFFORT | buy-sided buckets − sell-sided buckets (one-sided = \|imb\| ≥ 0.5). The aggressor is the side with a lead ≥ 2 |
| RESULT | did price make a new extreme ≥ 0.25U in the aggressor's direction in the last 6 min (legs.py's PAUSE_MIN / NEW_U)? Plus points moved over the window, in U |
| SPEED | the window's median bucket time ÷ the day's median so far |

**The words** (one per read; named by the aggressor, so they read the same for a buyer and a seller):

| Word | Rule | Chart chip | For a long | For a short |
|---|---|---|---|---|
| **BUYERS PUSHING** | buy lead ≥ 2 + a new high ≤ 6 min | `dhakka ▲` | with you | against you |
| **BUYERS ABSORBED** | buy lead ≥ 2 + no new high for 6 min | `kharidar thake` | **the exit sign** (§2 C: 0 of 19 went on) | the other side spent |
| **SELLERS PUSHING** | sell lead ≥ 2 + a new low ≤ 6 min | `dhakka ▼` | against you | with you |
| **SELLERS ABSORBED** | sell lead ≥ 2 + no new low for 6 min | `bechne wale thake` | **hold** (§2 C: 17 of 29 went on) | the exit sign |
| **VACUUM ▲ / ▼** | lead < 2 + moved ≥ 0.5U | `khaali ▲` | price moving on thin air: no one defending | — |
| **BALANCE** | lead < 2 + moved < 0.5U | `barabar` | nothing to read | — |

**Stamps** beside the word, never instead of it:
- **URGENT:** SPEED < 0.5.
- **HOT:** `vpin.py` percentile ≥ 0.90. VPIN is kept as a heat gauge, demoted to a stamp.

**One line on Jarvis and in the floating window** (English words, counts, never %):
`BUYERS ABSORBED · 7 of 10 bought · no new high 8 min · URGENT`

- **Display only.** It is not an input to the one voice (EXIT > WARN > TIGHTEN > HOLD, registered) or to any setup.

**Anytime start.** The book file is on disk from 09:15, so a restart rebuilds the day's buckets exactly. This is better
than VPIN, whose live log goes blind after a gap. Book holes show as "book hole HH:MM–HH:MM", never as BALANCE.

**Record.** `data/er/er_<day>.jsonl`: one row per closed bucket (t, buy, sell, imb, the window's numbers, the word). It is
the evening review's input, never a gate (standing rule, 26 Oct).

## 5. Her support checklist → the LEVEL LEDGER (phase 2, amends the unsigned 2026-10-26 spec)
The ledger already reads each test as families FOR / AGAINST. Her items become families or stamps. No new level
object, no second copy of anything:

| Her item | Read | Source | FOR (holds) | AGAINST (breaks) |
|---|---|---|---|---|
| absorption | the EFFORT / RESULT word at the test | §4 (new) | attackers ABSORBED | — |
| aggressive traders | the same word + URGENT | §4 (new) | — | attackers PUSHING; URGENT |
| big limit orders | **BOOK** (new family): the defending side's 5-level depth ≥ 1.5× the attacking side, as the median over the test's minutes; **PULLED** when it drops ≥ 50 % as price arrives | the recorded book (A: "recorded, not read") | stacked and holding | pulled |
| trapped traders | TRAPPED + FUT LEG (already in the spec) | fold `trapped`, AUDIT_OI | as the spec | as the spec |
| change in delta | after the test begins: FLOW ✓ (§1i's definition, unchanged) | confluence | turned | — |
| VWAP bands | stamp: σ expanding / flat | frame `sd` | — (stamp) | — |
| IB range | stamp: forming (< 10:15) / inside / outside | `daytype.py` IB | — (stamp) | — |

- The count stays as the spec has it: `FOR n · khilaaf m`, never a score, never summed across directions (§2 D).

## 6. Price discovery (phase 3)
**DISCOVERY ▲ / ▼** = after 10:15, price outside the IB, with attackers PUSHING (not ABSORBED) and the defending front
UNWINDING (§1d).
- It means: do not fade this band; the level is likely to break.
- It uses `daytype.py`'s IB and TREND as they are.
- The atlas (§1) found that the day's first-hour TREND call decides the day, and §2 D's failures sit after 10:15 outside
  the IB (16 of 43, against 2 of 26 before 10:15).

## 7. Judging (house rules 2 and 4, §1k)
- Every word, stamp and family is a display read, live from day one. Its forward log is the evening review.
- **An exit rule is a separate registration:** a HOLD v3 shadow line "ABSORBED" (exit at the first BUYERS ABSORBED in a
  long / SELLERS ABSORBED in a short).
  - It is judged by NOTEPAD §D's bar: ≥ 15 paired trades, ≥ 8 sessions, mean dR ≥ +0.20R, and so on.
  - Only on her signature.

## 8. Not changed
- `vpin.py`, `data/vpin_log.jsonl` and `vpin_fast.jsonl`: the live gauge and its 30-session kill-clock record.
- `fold.py`'s VPIN chip (registered).
- HOLD v2 (§1m), the one voice, CONFLUENCE (§1i), FADE-D (§1n), `effort.py`, `daytype.py`, `fronts.py`.

## 9. Decided as a trader (her standing rule: method questions are mine, with evidence)
- **Quote rule over tick:** §2 A.
- **10 buckets, not 50:** the 10-bucket window is the only VPIN read that measured (§2 C). The 50-bucket mean is ~70 min
  wide and blind to a stall.
- **Named by the aggressor, not by "your way":** one word reads both ways (buyer or seller, her rule of 25 Sep). The
  trade-relative meaning goes in the floating window's line.
- **5 levels of depth only:** Upstox `full`; 30 levels need Upstox Plus. A limit wall further out is not read, and the
  line says "5 levels".
- **Acceptance, before anything ships:** the build's replay of 21–30 Oct must reproduce §2 C's split from the words
  themselves (BUYERS ABSORBED at a long's stall: went on 0 of 19). If it does not, stop and report.
