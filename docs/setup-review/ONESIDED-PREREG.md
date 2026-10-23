# PRE-REGISTERED: THE ONE-SIDED METER, the day type from vote consistency (2026-10-22 ~15:45, UNTESTED)

## Origin (verbatim)
- **Mary, 22 Oct:**
  > "dashboard … where we seprate thing like if market is one side in terms of data like how many says one side how
  > many says mix … than we make decipher if it a trend day or chop day or pin day … in chop days the data is often
  > mixed … and keep getting our stoplosses trigged"
- **Then "fix everything"** on the gap list, which includes A23 (this meter).
- **Signed by Claude on that delegation.**
- **Mockup:** `https://claude.ai/artifact/GZzeADmMVPzUnZwo7ujpRL`; script `scratchpad/oneside.py`.
- **In-sample:** 21 and 22 Oct, both looked at while choosing the day-type rule.

## Votes, per closed 5-min bar (display only; gates nothing)
Each vote is ▲, ▼ or · (mixed), or `?` when the data is missing:
1. **Delta:** the bar's Δ ÷ volume, ≥ +0.05 / ≤ −0.05.
2. **CVD 15m:** CVD now minus 3 bars ago, ÷ those 3 bars' volume, ≥ +0.05 / ≤ −0.05.
3. **VWAP side:** close beyond ±0.02% of the session VWAP.
4. **Writers:** PE lead (nine strikes, aaj likha) ≥ +15 / ≤ −15.
5. **Writers 15m:** the PE lead changed ≥ +10 / ≤ −10 over 3 bars, **measured on the same strike set** (gap A24).
6. **Futures OI × price, 15m:** |ΔOI| ≥ 0.10%. Fresh longs or covering = ▲; fresh shorts or long liquidation = ▼.
7. **Peers:** both other indices on the same side of VWAP.

**A bar is one-sided** when ≥ 5 votes agree.

## Day type (computed live at every close; a count, never a probability)
- **TREND d:** one-sided bars ≥ 10, ≥ 80% of them d, flips ≤ 1, VWAP crosses ≤ 2.
- **PIN:** range < 0.5% of the open, and VWAP crosses ≥ 4.
- **CHOP:** VWAP crosses ≥ 4, or flips ≥ 3.
- **MIXED:** anything else.

**Shown as:** the type plus its numbers: `▲n ▼n · mila-jula n · disha x% · palte n · VWAP cross n`.

## Sources
- **Flow:** NIFTY from GoCharting bars; BANKNIFTY and SENSEX from Upstox.
- **OI:** the recorded chain and futures OI.

## Judging (forward from 2026-10-23)
- **What's logged:** at 15:30 each day, the final type per index, beside the day's realised shape: range in σ, VWAP crosses, and whether the close was within 0.5σ of VWAP.
- **The test:** after 20 sessions, describe the rows. **Does TREND by 11:30 match days whose afternoon kept the morning's direction? Does CHOP by 11:30 match days that crossed VWAP ≥ 4 more times?**
- **No hit rate is printed.**
- **Kill condition:** if the 11:30 type matches the afternoon no better than the 11:30 READ word does, the meter is retired.
