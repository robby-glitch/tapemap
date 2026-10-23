# PRE-REGISTERED: HOLD v2, the push trail, the profit lock and FADE → RIDE (2026-10-21 ~16:00, UNTESTED)

## Delegation and origin (verbatim)
- **Mary, 2026-10-21:** "yes write and lock hold version 2 and build it".
- **Her standing words:**
  - "identifying direction is never my problem but holding a trade" (24 Sep);
  - "if these are behind me i will hold and not i will fold" (28 Sep);
  - "a fixed target would repeat the first leak";
  - no candle close, ever.
- **Signed by Claude on that delegation.**
- **What motivated it (in-sample, disclosed; never evidence):**
  - 22 Sep: SENSEX RIDE ▼ had an MFE of +278 pts and ended at −0.14R; BANKNIFTY RIDE ▼ had an MFE of +170 and ended at
    −0.35R;
  - 12 Oct: a BANKNIFTY RIDE ▼ exited at +1.16R, then price ran 242 more;
  - 21 Oct: a SENSEX FADE SELL took its VWAP target at 09:57, then price ran 500+ more;
  - all from the §1k look and the 21 Oct session.

## What it applies to
- **Entries:** the entries of §1i (FADE) and §1j (RIDE), exactly as registered. Nothing about *entry* changes.
- **Exits:** HOLD v2 is a second exit rule scored **beside** each setup's registered exit (v1) on the **same entries**.
  v1 keeps running unchanged.
- **Live:** her hold window shows the v2 line beside its own word. It is display only and never changes that word.

## The push (the same definition live and in scoring)
- **A PUSH bar:**
  - a closed 5-min futures bar whose |Δ| ranks ≥ **p90** against prior days' same 15-min slot;
  - **and** its signed price result `R = sign(Δ) × (close − open) ÷ the slot's median range` is ≥ **0.25**.
  - This is the extension's existing flow state PUSH (`v2.js`). The TapeMap port must give the same answers on the same
    bars.
- **Its origin:** the bar's **open**.
- **Source:**
  - NIFTY uses GoCharting bars (her chart's footprint) and falls back to the Upstox 5-min bars only for a bar GC lacks;
  - BANKNIFTY and SENSEX use Upstox.
  - Each source is ranked only against its own history.

## The v2 exit, for a position in direction d (▼ = short the index / long PE / short CE), first of:
1. **THE LINE** (a price level, touched intrabar on 1-min bars; never a close):
   - **Start:** the setup's registered initial stop (FADE: §1i §2's stop; RIDE: §1j §2's initial line).
   - **Push trail:** after entry, every new PUSH in direction d whose origin lies between the current line and price moves
     the line to **origin + 0.25U** (▼; mirror for ▲). U = max(σ at that bar, 0.1% of price). It only moves toward
     price.
   - **Profit lock:** once MFE ≥ **2R** (on the initial risk), the line is never worse than the entry price
     (breakeven).
2. **SOMEBODY GAVE UP:** the trend-side front (▼: CE; ▲: PE; `fronts.read`, §1d's parameters) reads **UNWINDING** at a
   3-min close. Exit at that close. STALLED is stamped, never an exit.
3. **15:20:** marked at the 15:20 price, by §1i's convention.

## FADE → RIDE at VWAP
- **Where:** a FADE entry reaches its VWAP target (§1i §2's first-passage touch).
- **The check:** at the **3-min close of that bar**, apply §1j's RIDE OI ✓ and FLOW ✓ for the direction the move is
  going. That is the FADE's own direction (a FADE BUY moving up through VWAP is checked as RIDE ▲).
- **If both hold:** it does **not** exit. From that close on, the v2 exit applies.
  - Its line restarts at **VWAP − 0.5σ** (▲) / **VWAP + 0.5σ** (▼), never worse than the line it had.
  - R stays on the FADE's initial risk.
- **Otherwise:** it exits at VWAP, as v1 does.

## Scoring and the pass bar (paired: v2 against v1 on the same entries)
- **Groups:** FADE (all 8 cells pooled) and RIDE (all 4 cells pooled), judged separately. A hold rule is about the exit,
  so pooling across the setup's cells is the registered unit.
- **ΔR** = R(v2) − R(v1) per entry.
- **PASS:**
  - n ≥ **20** pairs;
  - mean ΔR ≥ **+0.20**;
  - mean ΔR with the single best pair removed **> 0**;
  - if the total ΔR > 0, no single day supplies more than **40%** of it.
- **FAIL:** n ≥ 20 and mean ΔR ≤ 0.
- **INCONCLUSIVE:** anything else.
- **Reporting:** n, mean ΔR, mean ΔR without the best pair, the largest day's share, and both groups' mean R(v1) and
  R(v2). **No hit rate anywhere.**
- **Forward only, from 2026-10-22.** Entries on or before 21 Oct are in-sample. They may be described, labelled
  IN-SAMPLE, but **never** counted.
- **Also recorded (descriptive):**
  - per entry, v2's exit reason (line by push / line by lock / initial line / gave up / 15:20 / converted);
  - the number of push moves;
  - MFE and MAE;
  - the option expressions at the v2 exit.
