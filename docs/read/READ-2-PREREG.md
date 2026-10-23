# PRE-REGISTERED: READ-2, a trend led by flow and fuel, plus the JAGAH (placement) line (2026-10-21 ~13:15, UNTESTED)

## Why (Mary, 21 Oct, live, a trend-down day)
> "today is also a trend day and look if our tool is able to detect it or not because if we look at the cum delta it
> start decresing from the almost the top of the market and than delta of selling is almost always higher on each
> candle and some where there are delta positive is small"
> ... "we need to look at everything and decipher what most probably gonna happen how market is placed to move"

**What read-1.1 did that day:**
- It said LEAN ▼ from 10:05 and never TREND, because the writers were on both sides (A +0.17).
- In the same period:
  - **the order flow was one-sided.** From the 09:35 high: 27 sell-delta bars vs 13 buy-delta bars; sell bars averaged
    −229 lots against buy bars at +76; CVD went +3,140 → −2,132;
  - **the futures OI fell with price,** i.e. long liquidation, ranked p97 at 10:27.
- read-1.1 has no vote for either.

**Disclosure.** 21 Oct is the day that motivated this, so it is in-sample. The thresholds below are round numbers fixed
by judgement, not fitted to it. **21 Oct does not count as evidence for READ-2.**

## The two new votes (computed at every closed 5-min mark, as read-1.1's votes are)
**FUEL (futures OI × price), [M]**
- **Inputs:** the change in futures OI over the last 40 min, and the futures price change over the same 40 min.
- **Ranking:** |ΔOI| is ranked against prior days' 40-min |ΔOI| at the same clock (the `rank.foi` reference already
  built).
- **The vote:** if the rank is ≥ **p80**, the vote = the sign of the price change.
  - OI falling with price falling = long liquidation, ▼.
  - OI rising with price falling = fresh shorts, ▼.
  - Mirror for ▲: covering or fresh longs.
- **The chip names which one it is.**
- **Otherwise:** a rank below p80 is 0; no reference or no OI is `None` ("could not check").

**LEG FLOW (one-sidedness since the leg began), [M]**
- **The leg:** it starts at the session extreme opposite to d (for ▼, the session high) made before the mark.
- **The bars:** 5-min bars from v2feed's 1-s bars, the same quote rule as read-1.1's FLOW. Bars from GoCharting fill
  only minutes before the first tick, as read-1.1 does.
- **The measures,** written for ▼:
  - `S = Σ|Δ| of sell-delta bars ÷ (Σ|Δ| of sell-delta bars + Σ Δ of buy-delta bars)`;
  - `M = the mean |Δ| of sell-delta bars ÷ the mean Δ of buy-delta bars`.
- **The vote:** ▼ when the leg has ≥ **6** bars, S ≥ **0.70** and M ≥ **2.0**. Mirror for ▲. Otherwise 0. A leg under 6
  bars is `None`.

## The word
- **Unchanged:** read-1.1's TREND / LEAN / RANGE / WAIT and every HELD rule (FLIP, writers' vote, PRICE turn).
- **New:** **TREND d (flow + fuel)** = WRITERS = 0, PRICE = d, FLOW = d, **FUEL = d** and **LEG FLOW = d**.
  - It is shown as `TREND ▼ · flow+fuel`, never as a plain writers' TREND.
  - **KHEL = RIDE at full size.** A LEAN is "ADHA", half size.
- **Downgrade:** a flow+fuel TREND drops back to LEAN when FUEL or LEG FLOW stops voting d. That is not a break: the
  read stands.
- **Breaks:** the same as LEAN's.
- **Upgrade:** if the writers then join (WRITERS = d), it becomes read-1.1's TREND, as today's LEAN → TREND does.
- **Effect on other setups:** RIDE (§1j) is unaffected. Its LOCATION already accepts TREND and LEAN.

## JAGAH: where the market is placed (display only; never a vote, never a probability)
One line per index at each mark:
`JAGAH ▼ jagah 52 pts (0.9σ) to 22,700 PE wall · ▲ rukawat 38 pts to FLIP 22,800 · fuel ▼ long chhod rahe p97 · flow ▼ 74%`
- **Room in the read's direction:** the nearest of the read's T1 wall, the day's extreme, PDL/PDH, and the round 100.
  Points and σ.
- **The obstacle behind:** the nearest of FLIP, VWAP, and the extension's last-push origin when the frame has it.
  Points.
- **Which side has fuel and flow:** the FUEL and LEG FLOW readings in words, with their ranks.
- **RANGE:** the distance to each box wall. **WAIT:** "saaf nahi".

## Logging and judging
- **Logging:** `data/read/read_<day>.jsonl` rows carry both `word_r1` (read-1.1) and `word` (read-2), plus FUEL, LEG
  FLOW and JAGAH. Live equals replay.
- **The forward check** starts 2026-10-22. For every flow+fuel TREND upgrade (one per leg), record:
  - whether price reached the JAGAH room target before spot closed back past FLIP;
  - the points made in the read's direction at 30 and 60 min.
  These are described as rows, never printed as a rate.
- **Kill condition** (decided now; the result is not printed on any screen): after 20 upgrades, if price closed back
  past FLIP first on more than half of them, the upgrade reverts to LEAN (half size) and READ-2's word is retired.
  JAGAH stays.
- **Nothing here gates** the zone machine, the fade gate, RIDE, FADE, signals or trigger_log.
