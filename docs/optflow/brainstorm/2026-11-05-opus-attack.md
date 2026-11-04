# Attack on "Option order flow for NIFTY: the trader's map and the quant's filters" (draft 1)

Written 2026-11-05 by Opus, adversarially, read-only on the repo. Tags: **[M]** measured by me today on `data/` (the
command is described inline), **[R]** from the repo's own measured docs, **[K-high / K-med / K-low]** my market knowledge
and my confidence in it, **[I]** my inference. Nothing here is registered. Nothing here places an order.

Four facts I measured before writing, because they change the document:

- **The open is not in the record.** The first chain row was 09:16:19 (2 Nov), 09:17:25 (3 Nov), 09:18:52 (4 Nov); the
  4 Nov futures book starts at 09:17:05 [M]. Section 5 has no data behind any row before 09:19.
- **The socket is not a tick feed.** On the 4 Nov NIFTY futures book, of 15,193 volume-changing frames, 7,077 (47 %)
  carry more volume than their `ltq`. Only **29 % of the day's volume** is the `ltq` of its frame. Arrival minus `ltt`
  is 1.6 s at the median and 6.6 s at p90 [M].
- **The chain snapshots are not synchronous.** `ltp` sits outside the same row's bid/ask on 41 % / 39 % / 52 % of
  strike-sides (2 / 3 / 4 Nov) [M]. Any quote rule run on `data/chain/` is classifying noise.
- **The lot is 65, not 75.** The GCD of all 16,354 non-zero Dext price cells for NSE-39961 on 4 Nov is 65 [M]. Every
  "delta-lots = qty × |delta| / 75" in this document, in C8, and in Fable decision 1 is 15 % too small. The 2,000
  delta-lot "wall move" was derived from 1.5 L / 75.

---

## A. The three worst problems

**A1. The tick layer, which carries the scalp and the open, rests on a per-trade feed that does not exist.**
The document assumes "per trade: signed qty = ltq × side, quote rule at ltt". On the measured futures feed, 71 % of
volume is never in any `ltq`. ATM weekly options trade more often per second than the future, so the merging there can
only be worse [I]. The 10-second BVC fallback runs on chain rows whose `ltp` is outside their own quote about 40 % of
the time. *At 09:18 with money on:* line 4 reads `CE lift 2,400 δ-lots / 60 s · p91`. Most of that number comes from
volume whose side was guessed, then scaled by a vendor delta computed off a stale `ltp`, then divided by the wrong
lot. It looks like a measurement and is a guess. *Instead:* record **frames**, not ticks. Per frame, take dV = Δvtt, and
sign it by the frame's `ltp` against the **previous frame's** touch: ≥ prior ask is +1, ≤ prior bid is −1, inside is
split by the BVC share using that contract's own 1-s σ. Call it "frame flow" on the screen. Publish the share of
volume decided at the touch every day; it is the honest error bar. Score it against Dext per minute, and report
the undecided share beside the agreement, never instead of it.

**A2. The opening read is a design for a window the recorders have never captured.**
Every opening type rests on "the first FIRM window" of OI × flow. FIRM needs OI at two closes plus a one-minute-shifted
flow window. With OI moving every ~63 s [R] and the first OI update after the cross landing around 09:16-09:17, the
earliest honest FIRM read is **09:20-09:21**, not 09:18. And on all three recorded days there is no 09:15-09:16 data at
all [M]. *At 09:18* the screen would show the opening type built from one OI print that is dominated by the 09:15
overnight cross (62 price levels, 70.85 to 111.45 on 4 Nov's 09:15 bar, which also opened the day's 813,800 volume [M]).
*Instead:* fix the start first (all recorders live by 09:14:30, with an alarm). Then build the opening read from things
that exist at 09:16-09:17 (section D), and let WHO arrive at 09:21 marked OPENING.

**A3. Line 4 rebuilds, on options, the futures reads that the audit killed, and points a poster at crossing.**
`asks thinning 1:3` is depth imbalance: whole-book tbq/tsq was **inverted** on futures and 5-level depth imbalance was
zero [R, AUDIT 3.2/3.4]. `accel +` is a delta surge: noise, inverted in-sample. A 60-s lift count is OFI, worth +2 to +3
points: real but below the bar. Sign persistence was inverted. Nothing in the document says why these primitives should
work on a contract whose flow moves in the **same** 3-min bar as the futures. *At 09:18:* she sees "lift, p91, accel +,
asks thinning", the textbook momentum-chase entry. She is a **poster**: her edge is spread capture minus adverse
selection, and this line tells her to pay the spread exactly when the flow is most toxic. *Instead:* line 4 should
answer the poster's question: "is resting here about to get picked off?" (section E).

---

## B. The nine questions

**1. Conflated or every trade?** Conflated [M on futures; K-high that options behave the same: Upstox v3 is a
snapshot stream, about 1 s, last-value-wins per key]. `ltq`/`ltt` are the last trade in the frame only. `ltt` has
millisecond resolution (0.2 % of values are whole seconds [M]). BVC per 10 s on the chain is **not** honest enough, for
two reasons. The chain snapshot is non-synchronous. And an ATM option's 10-s premium change is mostly Δ·dF, so BVC on
it re-labels the **futures'** direction as option aggression, which makes "options agree with futures" true by
construction. If BVC is used at all, run it on the **residual** premium change (mid change − Δ·dF) per 1-s frame. Use
it only for undecided frames, and only in minute aggregates (Chakrabarty et al.: BVC is worse than the tick rule
trade-by-trade and fine in bulk) [K-med].

**2. OI in the first five minutes.** NSE's intraday OI is a periodic dissemination, about every 63 s here [R], and is
not tied to the trades it counts. Until the first update the field carries the prior session's closing OI [K-med].
The first post-open value therefore lumps the whole 09:15 cross into one dOI. Usable read: **first-update OI minus the
prior close**, per strike. The chain carries `oi_chg`, so the prior close is `oi − oi_chg`. That gives "how many
overnight positions changed in the cross", a valid opening number, at about 09:16:30. Not usable: any 1-min WHO before
09:20.

**3. Own-day rank enough?** No. It is undefined for the first six bars, which is the whole open. It saturates on trend
days, when every bar is p90. And it cannot separate a one-strike event from a whole-ladder move. Add two filters.
(a) Cross-sectional: each strike's minute delta-lots as a z-score against the median and MAD across ATM ±3 on the
same side, at the same minute (not the same second; the frames are not aligned). (b) Futures residual: regress
per-strike signed delta-lots on the futures' signed lots over the day so far, and rank the residual. What is left is
the option-specific event; the rest is the futures' move seen through the options.

**4. The decomposition on 0-1 DTE at 1 min.** Not stable [K-high]. The chain greeks are the vendor's, computed from an
`ltp` that is outside the quote about 40 % of the time [M]. On 0 DTE, Θ is non-linear through the day, ½Γ dF² is the
same size as Δ dF on a 20-point move, and a 10-s IV change is mostly bid-ask bounce. Replace it with a **model-free**
label. ATM straddle mid = CE mid + PE mid. Over the window: |Δstraddle| large with |dF| small is VOL; |Δ(CE mid − PE
mid)| ≈ dF with a flat straddle is DIRECTIONAL; else MIXED. Readable at 1 min on 3+ DTE; on 0-1 DTE only at 3 min.

**5. Are four opening types enough; separable by minute 5?** They are the wrong set. Missing:
- **NO GAP** (the open inside yesterday's range), probably the commonest day and not covered at all;
- **GAP AND FILL**: the overnight counter-auction went against the gap on 7 of 17 days [R, AUDIT 3.5].

GO versus CAP are not separable by OI at 09:20. By 09:21-09:24 they partly are, if the straddle and the futures' λ
agree; by 09:30, more. Counting rules this out too: 20 sessions split four or five ways gives about 4 per type, so
no cell reaches the n ≥ 15 the prereg demands within the window. Pre-register **two** directional types plus
UNREADABLE, or the open will "fit anything" as the document itself warns.

**6. Who else is forced?** See C1. The most important omission: **the passive side of "BUY" is mostly HFT/prop
market-makers, not writers with a view.** They hedge in futures within seconds [K-med]. WRITE/BUY tells you who
crossed, not who has conviction.

**7. Under-weighted / naive.** Under-weighted: #6, aggressor classification. The whole stack inherits it. 1,112 agree
against 885 disagree, with 1,261 undecided excluded, is barely above a coin [R], and nothing is built until frames are
scored. Naive: #3 (greeks on stale `ltp`), #4 (PAIRED at 30 % within a minute will fire nearly every ATM minute), #2
(the wrong lot), #12 (her posted size is the "wall" she would read).

**8. What a scalper needs on line 4.** Section E.

**9. Most dangerous.** Section G.

---

## C. What is missing

**C1. Participants.**
- **Short-premium sellers' stops.** Indian prop and HNI writers mostly run premium-multiple stops (SL-limit buys at
  1.3-2× the sell price) and roll strikes, rather than hedging delta continuously [K-med]. The covering cascade's fuel
  sits at **premium levels** (1.5× and 2× the strike's 09:20-09:30 VWAP, or the day low), not only at strikes.
  Concrete read: the premium's distance to 1.5× and 2× its early VWAP, with dOI at the strike as it crosses.
- **Options market-makers / HFT,** passive on most retail lifts; the hedge goes into futures, so their footprint is
  futures flow lagging option flow by seconds.
- **Parity arbitrageurs** (conversions/reversals, synthetic futures). They create opposite-side CE/PE prints at one
  strike, and #4's PAIRED will call them spreads.
- **Delta-limit-forced desks.** FutEq OI limits and random intraday snapshots [R, review 1.5] force delta trims at
  unknown times; the trims land in futures.
- **Broker auto square-off** of intraday (MIS) option longs, about 15:10-15:25 [K-high]. It is forced selling in the
  last half-hour, mis-read as DUMP/"conviction".
- **Next-expiry rollers** on expiry day. Flow migrates to the next weekly, which the bridge does not ask for.

**C2. Noise sources not in the twelve.** Late recorder starts (every day so far) [M]. Non-synchronous chain fields
[M]. The lot unit [M]. ATM drift: "CVD(strike) since 09:15" changes moneyness under the strike as spot moves, so it
must be per moneyness slot, not per contract. Price discreteness: the 0.05 tick on sub-₹5 premiums, where the quote
rule and BVC degenerate. Dext forces a side (its `neutral_volume` is 0 on every row I read [M]), so midpoint trades are
hidden inside the buy/sell split. Clock skew between Dext minute stamps, `ltt` and the arrival time `t`.

**C3. Reads a real options desk uses, computable from these fields.**
- **Parity-implied future:** F* = K + C_mid − P_mid at ATM, minus the real futures mid, in points, over 1-s frames. A
  dislocation says which market is moving first, and it is the clean test of "options never lead".
- **Straddle mid versus futures** (B4): vol-versus-direction without a model.
- **Markout / realised spread:** for each frame, signed dV × (mid at t+30 s − trade price), summed per strike per
  minute. This is toxicity in rupees. For a poster it is the number.
- **Option Kyle λ:** Δpremium mid per signed delta-lot over 5 min, against the strike's own-day median. It is the audit's
  one surviving family, moved to the instrument she trades; check it alongside the futures λ, never instead of it.
- **VPIN** on equal-volume buckets of ATM ±2 option volume (Easley, López de Prado, O'Hara). A toxicity regime flag,
  not a direction.
- **Risk reversal:** the IV of the CE nearest delta 0.25 minus the PE nearest −0.25, and its 15-min change; directional
  demand for protection. Use IV from mids, not vendor greeks.

**C4. Literature that changes the design.**
- **Muravyev (2016)**: option order imbalance moves the **option's** price, through market-maker inventory risk, more
  than it predicts the underlying [K-med]. She trades premium, so every R5/R6 outcome should add the option's excess
  return (Δmid − Δ·dF), not only futures points at +15/+30.
- **Easley-O'Hara-Srinivas (1998), Hu (2014)**: informativeness is in **delta-signed** option imbalance and is strongest
  where leverage is high. Keep C8, but net it against futures flow (C3 residual).
- **Hasbrouck information share** at 1 s between F* and the futures. The "options never earlier" conclusion came from
  lag-0 correlation on a 3-min grid, which cannot see a 20-second lead. It is untested, not refuted.
- **Ni-Pearson-Poteshman (2005)**: pinning comes from long-gamma hedgers rebalancing. In India the writers are short
  gamma, so their hedging pushes away from the strike, and any pin must come from defence, not hedging [I]. R4's
  mechanism needs restating before its outcome means anything.
- **Lee-Ready**: the prior-quote rule (quote before the trade), never the same snapshot's quote.

---

## D. The opening read (section 5)

The table has an anachronism: the 09:15 row "reads" the 09:16 POC, and Dext's 09:16 minute does not arrive until
09:17-09:18. The 09:16-09:17 row ranks against "the same-slot reference of prior days", but no prior day has that slot
recorded [M]. Even with the slots fixed, only post-7-Sep-2026 sessions (R3 regime) may enter the reference, so n is
under 45 even in a perfect world.

The four types: GAP AND CAP / GO depend on ITM-CE COVER. Inside ATM ±3 on a 0.5 % gap, "ITM" strikes are one to three
steps in the money, with thin, hedged, spread-leg flow; the deep ITM inventory that actually moved overnight is outside
the recorded strikes. TWO-SIDED at the first FIRM window confuses market-makers' passive inventory with writers' intent.

**Is anything readable before 09:18?** Yes, if recorded:

1. The futures auction price against the prior close, and against GIFT at 09:08: the gap in σ of the prior day's range.
2. At about 09:16:30, the first OI update minus the prior close (`oi − oi_chg`) per strike: the overnight cross.
3. From 09:15:30, the ATM straddle mid, once the CE and PE spreads are each ≤ 2 % of premium (skip frames before that).

**The single best opening read [I, to pre-register]:** the ATM straddle mid at 09:17 against the prior close's straddle
(θ-adjusted by one session's decay), read beside the gap's sign.
- Gap with the straddle **bid** (paying for movement): participants fear continuation; GO-leaning.
- Gap with the straddle **offered**: writers are selling the gap; FADE-leaning.

It is model-free and two contracts deep, it needs no OI and no aggressor sign, and it is available at 09:16-09:17.
Confirm it at 09:21 with the first FIRM WHO, never before.

---

## E. The scalp ladder (section 6)

**Line 4, for someone who posts (each one computable from frames):**
- **Stale-quote gap:** option mid minus (mid at the last frame + Δ·dF since), in ticks. The futures move first; option
  quotes lag by sub-second to seconds. A positive gap at her resting offer means she is about to be lifted by an arb.
- **Touch:** spread in ticks, best size against her size, and size at level 2. Whether her post is first in line or
  behind a wall.
- **Toxicity:** 30-s markout of the last 60 s of aggressor flow on this strike, in ticks: "aggressors won +1.5". Post
  when markout is ≤ 0; stand aside when it is positive.
- **Futures λ at the extreme,** the one proven timer, with its own clock stamp.

**Line 5 for a scalp:** a time stop on screen (the clock counting to 5:00); premium mid back through the entry-minute
VWAP; futures λ absorption against her side; markout turning against her. "Strike WHO → WRITE" is a 3-min clock and
belongs to the 5-30 min book.

**Noise on line 4:** `asks thinning 1:3` (inverted on futures), `accel +` (noise), CVD(strike) since 09:15 (moneyness
drift), `IV flat` (vendor greek off a stale `ltp`), a lift count without the futures residual.

---

## F. The twelve filters

1. **FIX:** own-day rank → same-slot prior days (R3 regime only) until bar 6, plus a cross-sectional z and a futures
   residual.
2. **FIX:** lot 65 [M]; delta from mids against the futures, not vendor greeks; keep the three-way sizing.
3. **FIX:** greek decomposition → straddle-versus-futures label; 3-min only on 0-1 DTE.
4. **FIX:** PAIRED only for same-frame, opposite-sign, 1:1 ±10 % in lots; otherwise drop it; keep ladder netting.
5. **KEEP;** add first-update-versus-prior-close OI; no WHO from the 09:15-09:17 OI.
6. **FIX:** prior-frame quote rule on Δvtt; publish the undecided share; never classify from chain rows.
7. **KEEP the ban, FIX the timing:** no read from minute-0 prints, the 09:15 POC included; recorders live by 09:14:30.
8. **KEEP;** add next-expiry flow and a tick-floor caveat for premiums under ₹5.
9. **KEEP.**
10. **KEEP, escalate:** late starts are a daily event today [M]; make health a blocking line.
11. **FIX:** collapse to 0 DTE / not-0 × two day-parts until n allows; 3 × 4 cells × 20 days are empty.
12. **FIX:** her orders stamped live, and her strike-minute greyed on screen; her resting size excluded from "walls".

---

## G. The most dangerous way it fools her, and the guard

**It turns her winning population into her losing one.** Her edge is passive scalps of 5 minutes or less; the leak was
holds of 5-30 minutes [R, A78]. The ladder puts a thesis (line 2: `UP FUEL · cap bhaag rahe ×3`) directly above an
entry (line 4). A scalp that goes 6 ticks against her at minute 4 now has a story to hold for: "writers are still
running". The tool hands her a reason to hold through exactly the horizon where she loses. Its WHO words are
mis-signed often enough (R2 aggressor agreement; 26 % of 1-min labels move with a one-minute shift [R]) that the story
is wrong a material share of the time.

**Guard:**
- In scalp mode the close and context layers may only **veto** an entry (grey line 4); they never appear after a fill.
- After a fill the card shows only the 5:00 clock, the markout, and line 5.
- Every hold past 5:00 is logged with the ladder as it stood at entry, and the evening sheet counts them first.
- Runner-up danger: line 4 trains a poster to cross. The guard is the same: line 4 speaks in toxicity, not in "lift".

---

## H. Ten changes, most valuable first

1. Start the chain, book and option-frame recorders by 09:14:30 with a blocking health alarm, because no recorded day
   has 09:15 data.
2. Record option frames and sign Δvtt with the prior-frame quote rule, calling it frame flow, because `ltq` carries
   only 29 % of volume.
3. Change the lot from 75 to 65 everywhere (delta-lots, the 2,000 threshold, C8, Fable decision 1) and re-derive the
   thresholds.
4. Re-target line 4 for a poster: stale-quote gap against the futures, the touch against her size, 30-s markout
   toxicity, and futures λ; drop "asks thinning" and "accel".
5. In scalp mode, let the close and context layers only veto entries, show a hard 5:00 clock after a fill, and log
   every hold past it with the entry ladder.
6. Rebuild the opening read on the futures gap, the ATM straddle mid against the prior close, and first-update OI
   against the prior close (`oi − oi_chg`); start WHO at 09:21; pre-register two types plus UNREADABLE.
7. Replace the greek decomposition with a model-free straddle-versus-futures VOL/DIRECTIONAL label, using deltas from
   mids, not vendor greeks.
8. Add the option's own excess return (Δmid − Δ·dF) as an outcome beside futures points in R5/R6 (Muravyev).
9. Test lead-lag at 1 s with the parity-implied future against the real future before re-asserting "options never
   lead".
10. Add the cross-sectional z and the futures-residual filter for one-strike events, and collapse the reference cells
    to 0-DTE / other until n allows.
