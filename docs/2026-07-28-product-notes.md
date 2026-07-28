# Product notes — live session 2026-07-28 (fix at day end)

> **TIER 1 SHIPPED** (items 13, 14, 18, 21, 22, 23, 29, 30, 31, 32 + the item-2
> wording fix). Measured on this session's own 375 bars: direction flips
> **60 -> 32**, times a side was named **41 -> 16**, median run **5 -> 10 bars**,
> bars admitting no edge **51 -> 183**. The browser reproduces the audit
> exactly (32 flips, LONG 132 / SHORT 60 / NONE 183) and the 15:29 SCAN now
> reads STAND ASIDE 0/100 instead of BULLISH-with-CE-buys. 54-day backtest:
> only SPRING and ARMED moved (conflicted springs reclassified); every other
> kind is byte-identical, aggregate -0.995 -> -1.020 pts/signal. 35 tests pass,
> including three new ones (roll-vs-rout, ITM books ignored, blown-up IV
> dropped). **The running server must be restarted to load the engine and
> chain_metrics changes — app.js is live already (v=20).**
> Still open from Tier 1's neighbours: item 24 (deep-ITM candidates) is Tier 3
> and still visible — with the read at STAND ASIDE the SCAN lists 24,100/
> 24,150/24,250 PE at 113-263 pts ITM, conf 13/100.

Running list from watching TapeMap work a real expiry day. Ordered by impact.

## Bugs / calc issues seen live

1. **Squeeze score fires hollow.** Score spiked to 0.65–0.88 with "0.0M writer
   OI trapped" at a single dead strike (10:15, 10:19). Score must be gated /
   weighted by trapped OI size (chain_metrics.py). My watcher now filters
   <1M trapped; the engine should do the same at the source.
2. **Squeeze verdict prints degenerate range** ("CE writers 23750–23750") when
   only one strike qualifies — collapse to single-strike wording.
3. **Flip/GEX whipsaw:** gamma flip printed 24,076 → 24,018 → 24,039 and GEX
   221k → 58k within ~40 min of book churn. Values are honest but jumpy —
   consider a short EMA/median smoothing for display, or show a mini flip
   trail so the drift is visible instead of confusing.

## Missing signal (the day's biggest lesson)

4. **No WALL-MIGRATION / ROLE-FLIP event.** Today's decisive structural move —
   24,000 flipping ceiling→floor (CE −24% off peak while PE +25M occupied the
   strike, CE army regrouping at 24,050/24,100) — produced NO narrative event.
   The engine watches books at one ATM strike; the chain analyser sees walls
   but only surfaces them as numbers. One event kind: "WALL MIGRATION: 24,000
   ceiling→floor, CE retreats to 24,050" would have been the headline of the
   morning.

## Productize today's ad-hoc watcher

5. **In-app ALERTS panel** replicating the scratchpad crack-watch: user-armed
   tripwires (level break, squeeze ≥ threshold with real trapped OI, wall-book
   drop % off session peak, feed-down watchdog), de-duplicated with re-arm
   logic, browser notification. This session proved the pattern works
   (caught the 10:08 PE evacuation and the CE rout in real time).

## Carried over from the 2026-07-27 audits (Phase 4 backlog)

6. Nightly self-scoring: cron `measure.py --live` per index after close;
   rolling per-kind stats accumulate in data/signal_stats.json.
7. UI badges: rolling hit-rate/CI next to each event kind in the feed;
   CARRY verdict rendered WITH its track record (11/30); BUYER-BUILD demoted
   to observation-only styling.
8. Engine emits explicit `dir` in event data (kill string-parsing of msgs —
   flagged in the independent review).
9. FOCUS feed: verify live-day reduction tonight (expiry day = worst case);
   tune LOUD set / cooldowns from real usage.

## Afternoon session additions (Kite cross-check, 12:57)

13. **The CE "squeeze" was a ROLL, not a rout — engine called it backwards.**
    SQUEEZE-RISK fired 11:55 (CE 31.0M, +0.57) and 12:15 (33.1M, +0.64) reading
    the 24,000 CE unwind as writers capitulating → "upside squeeze risk". Kite
    `oi_day_high` proves otherwise: 24,000 CE is −21% off its 44.0M peak while
    **24,050 CE sits at 34.8M = its day high, i.e. exactly at peak strength**,
    and 24,100 CE is 36.8M. The call writers rolled up 50 points; they did not
    cover. Reading strike-local unwind without checking the neighbouring
    strikes' build produces a directionally WRONG signal. Fix: squeeze must net
    the unwind against OI added within ±2 strikes over the same window.
14. **`oi_day_high` / `oi_day_low` per strike is the missing input.** It gives
    "% off peak" for free and is what makes item 13 detectable. The chain
    poller should track per-strike session peak/trough itself (it already polls
    the full chain — just retain the extremes).
15. **The narrative box is tighter than the structural box.** Engine caps the
    day at 24,026 (a trap bar) while the real ceiling is the 34.7M 24,050 wall;
    price printed 24,040 after that trap. Trap-bar highs should not become the
    displayed `cap` when a bigger OI wall sits above — "mid-box, worst location"
    is misleading when price is actually mid-cage of a wider structure.
16. **`breadth: STRONG BEAR` contradicts the rest of the panel** on a pinned day
    (price above VWAP, above prior close, sitting on a 53M put wall, MM PINNED
    64m). Bar-internals breadth is low information in a positive-GEX regime —
    suppress it or weight it by gamma regime.
17. **Gamma flip still whipsawing:** 24,076 → 24,018 → 24,039 → **24,111** while
    GEX ran 221k → 58k → 320k → 626k. Reinforces item 3; needs smoothing.

## 13:16 breakdown — one bug, one win

18. **State machine printed `ARMED — spring live (bullish)` into a breakdown.**
    At 13:13 the state flipped ARMED/bullish while the engine's OWN events two
    minutes later read `CAMPAIGN … → BEARISH`, `GAMMA-PIN CEILING at 24000` and
    `SQUEEZE-RELEASE DOWNWARD … hedging amplifies the move`. Price went 24,009 →
    23,968 across the same window. The ARMED direction is derived from coil
    geometry alone and is not reconciled against the book/flow events. Either
    sign it from the same evidence the events use, or emit it directionless
    ("ARMED — spring live, direction unresolved").
19. **WIN — the squeeze logic called this one correctly and early.** 13:13
    SQUEEZE-RISK (PE book 47.6M, score +0.84, −4327k/10m) then 13:15
    SQUEEZE-RELEASE DOWNWARD (rank 0.97, prem velocity 0.99) landed ~3 min
    BEFORE the watcher's second book-crack alert. Worth preserving when fixing
    item 13.
20. **Item 13's proposed fix is validated by the contrast.** Morning CE case:
    unwind at one strike, neighbours BUILDING (24,050 at day peak) = roll, and
    the signal was wrong. Afternoon PE case: every put strike shedding at once
    (24,000 −31% off peak, 23,950 −18% having been AT peak 4 min earlier,
    23,800 −13%) = genuine rout, and the signal was right. Netting local unwind
    against neighbouring builds separates these two cleanly — implement exactly
    that.

## SCAN / validator direction (audited 13:38, replicated app.js:904-921 over 264 bars)

21. **The SCAN direction is not stuck — it flip-flops. 42 direction changes in
    one session** (LONG 130 bars / SHORT 112 / NONE 22), i.e. one flip every ~6
    minutes, and sometimes bar-to-bar: 13:32 NONE → 13:33 LONG → 13:34 NONE →
    13:35 LONG. A tradeable read cannot change sides four times in four minutes.
22. **Cause: `breadth` alone decides it, because everything else cancels.**
    In that 13:32-13:35 window every other term was identical (setup +1.9, PE
    writer +1.0, CE writer −1.0); only breadth toggled LEAN BEAR (−1) vs STRONG
    BEAR (−2), and that ±1 swings B across the ±0.5 threshold. The bias sum is
    a knife-edge on the single noisiest input (see also item 16). Fix: hysteresis
    on the direction (require |B| > 1.5 to flip, and hold for N bars), and cut
    breadth's weight or gate it by gamma regime.
23. **The mis-signed ARMED setup is a permanent thumb on the bull scale — this
    is why the user sees only CE.** `setup ARMED dir=UP` contributes
    `+1 * (1 + intensity)` ≈ **+1.8 to +2.0**, the single largest term in B, and
    it has been pinned UP since 13:13 *through a 40-point decline*. Right now
    B = +0.85 → LONG while the CE writer score is 0.99 (maximum bearish) and
    breadth is bearish. **Drop that one term and B = −1.05 → SHORT.** The CE
    recommendation is an artifact of item 18, not a read of the tape.
24. **No sanity filter on candidates.** `BUY 22950 CE` — 1032 pts ITM, Δ0.98,
    premium ₹1074.8 (~₹80k/lot) — ranked #3. Confidence buckets (`round(conf/5)`)
    tie at 9 for 43/44/44, so the nearest-the-money tie-break is all that
    separates a real ATM trade from a synthetic future. Needs a hard filter on
    moneyness / premium / delta before ranking.
25. **Identical R:R across every row is misleading.** All three rows show
    ENTRY 23980 · T1 23996 · T2 24027 · T3 24041 · STOP 23965 · R:R 1.02,
    because entry/stop/targets are UNDERLYING levels applied to every candidate.
    A 15-pt underlying stop is a ~40% premium loss on the Δ0.38 OTM call and
    ~1.5% on the Δ0.98 ITM one. R:R must be expressed in premium terms per
    candidate, or labelled clearly as an underlying-level R:R.
26. **Scrubbing back in time uses the LIVE chain snapshot.** `S.mapChain` is
    always current, so the pcr/squeeze/skew terms contaminate historical bars
    with future information — replay reads are not causal. Store the chain
    snapshot per bar, or drop the chain terms when the scrub is off the last bar.

## Third failure mode: theta-contaminated "% off peak" (13:53)

27. **On expiry afternoon, `% off peak` is contaminated by worthless-option
    housekeeping.** The 13:53 alert fired on 23,950 CE −9.5% off peak, and the
    neighbours were shedding too (23,900 CE −11.5%, 24,100 CE **−20%**), which
    by the item-13 roll-vs-rout test looks like a broad call rout = bullish.
    It isn't. 24,100 CE trades at **₹2.10** with ~95 min to expiry — that book
    is decaying to zero and writers are closing it to free margin, not covering
    in fear. Meanwhile the books that actually cap price, 24,000 (55.0M, −5%)
    and 24,050 (38.1M, −0.5%), are intact. Fix: weight unwind by premium —
    ignore or heavily discount strikes under ~₹5, and prefer *notional* OI
    change (OI x premium) over raw contract count when ranking a crack. Cheap
    far-OTM strikes should not be able to trigger a squeeze read at all.
28. **Corollary for the roll-vs-rout test:** "neighbours also shedding" is
    necessary but not sufficient. The neighbours must be *live* strikes (real
    premium, near the money) for a broad unwind to mean anything directional.

## Squeeze rows ignore which side of spot the strike is on (14:34)

29. **The engine's squeeze rows include books that cannot do what the verdict
    claims.** 14:33 fired 0.44/0.49 DOWN — "PE writers 24,000-24,200 underwater,
    12.4M trapped, fuel BELOW" — with spot at 23,973. Every one of those strikes
    is ABOVE spot, i.e. **in-the-money puts**. Their writers are losers closing
    out near expiry; that is not a floor giving way. The actual floor, 23,950 PE,
    **grew from 29.1M (13:16) to 43.5M** over the same stretch — put writers were
    piling IN one strike below spot while the engine called put support failing.
    Apply the same side-of-spot rule the watcher now uses: a PE book only
    supports price at/below spot, a CE book only caps it at/above.
30. **"Hedging amplifies the move" is printed regardless of GEX sign.** The
    13:15 SQUEEZE-RELEASE said "dealer short-gamma hedge chase, hedging
    amplifies the move" while `gex_regime` was **POSITIVE** (+393k) — long-gamma
    dealers dampen, they don't chase. The amplification wording must be gated on
    negative GEX; in positive GEX the same flow argues for fade-and-pin.
    (Mechanically it's also backwards here: a hedged short put is short futures,
    so buying the put back means buying futures — mildly supportive, not
    downside fuel.)

## Expiry-afternoon IV solver blows up, and it votes on direction (14:52)

31. **`iv.atm_pe` returned 1.3313 (133% vol) at 14:52** with `atm_ce` at 0.0663
    — it was 0.0977 at 12:57. The ATM put was ₹19.55 against ~₹19 of intrinsic,
    so the solver is fitting ~₹0.5 of time value with 37 minutes left and
    diverging. This is not cosmetic: `iv.skew` (−0.0161) feeds the SCAN's
    direction term as **+0.5 bullish** (app.js:918-919), so a blown-up solver is
    casting a vote on which side to trade. Clamp IV to a sane band, and drop the
    skew term when time-to-expiry is under ~2h or when either leg's time value
    is below a few rupees.
32. **Two events one minute apart read the SAME two numbers oppositely.** 14:51
    PRESS: "BEARISH rotation: CE writers add (+3399k) while PE shorts evacuate
    (-4120k) — books lean down before price." 14:51 ARMED: "BULLISH SPRING at
    P 23996 — dip disbelieved: PE OI -4120k/10m while FUT z=-2.0; CE writers
    adding +3399k." Identical inputs, opposite conclusions, same minute, both in
    the feed. Whatever reconciliation item 18 gets must cover this pair — one of
    these two interpretations has to win, or both must be suppressed as
    unresolved.

## The 15:01 "breakdown" was the pin loading, not breaking (15:20)

33. **A falling GEX total during a wall break is ambiguous, and I read it wrong
    live.** At 15:01 GEX had collapsed 967k -> 120k and I called the 23,950
    break real (new day low, 4-6x volume, BANKNIFTY confirming, every put book
    shedding). Price reversed 52 points and closed the move back above 24,000,
    and **GEX went to 1,561,573** — 13x the 15:01 reading. The total fell only
    because spot had walked AWAY from the strikes holding the gamma; the
    restoring force was building, not dying. Fix: never show `gex_total` alone
    as a regime strength. Pair it with distance-to-max-pain and the gamma at
    the CURRENT spot, and on expiry day flag when price is outside the big-book
    zone — that is precisely when the total understates the snap-back risk.
34. **Late-session unwind is squaring, not conviction.** The 15:20 squeeze fired
    0.46 UP on 12,671k unwound at 24,000 CE — with the option at Rs 1.75 and
    nine minutes to expiry. Those writers were closing to avoid settlement, not
    being run over. The premium filter (item 27) needs a time-of-day companion:
    after ~15:05, weight unwind by premium AND suppress direction claims
    entirely, because OI decay is mechanical everywhere.

## Smaller polish

10. Show `built_at` as a small "bars HH:MM:SS" stamp on the TAPE view so bar
    lag vs chain is visible at a glance (banner only fires at >90s).
11. Surface rate-limit backoff in the UI (server logs it now; a quiet chip
    "throttled, retrying" beats silence when builds skip a beat).
12. crack-watch thresholds per index if productized (35pt/40pt equivalents).
