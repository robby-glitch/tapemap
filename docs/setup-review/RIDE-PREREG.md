# PRE-REGISTERED: RIDE, her second setup (trend pullback + the same three checks) and its pass bar

**Written 2026-10-21 ~02:30 IST, before any RIDE outcome exists. Nothing here is a result.**

## Delegation (verbatim)
- **Mary, 2026-10-21:** "yes register RIDE as second setup with same three checks and that sum up everything so make
  sure built it carefully . think about plan and than built it".
- **Standing words that bind this file:**
  - "identifying direction is never my problem but holding a trade it closing too early" (24 Sep);
  - "i dont care about candle close or anything i have zone oderflow oi and vpin and if these are behind me i will hold
    and not i will fold" (28 Sep);
  - "a fixed target would repeat the first leak" (hold review, 25 Sep);
  - "the cut off time for new trade is 3:00 pm and if i m in trade i can hold it till 03:20", "no rules for expirary",
    "i can buy or sell options to make sure you give importance to both side" (21 Oct).
- **Signed by Claude on that delegation.** It is the sister of `CONFLUENCE-PREREG.md` (§1i), which is FADE.

## Disclosure
- **This session read 9, 12, 13, 16 and 19 Oct live or in replay.** That includes her 19 Oct PE ride (178 → about
  348).
- **No RIDE outcome has been computed.** No threshold below was chosen from any day.
- **Every number is round and fixed by trader judgement.** None is to be grid-searched.

## 0. What RIDE reuses (nothing is invented where a registered rule exists)
- **LOCATION + TRIGGER = READ-V2 §E, unchanged** (`docs/read/READ-V2-PREREG.md` §4.E; `frame_v2.plan`):
  - READ word TREND or LEAN with direction d;
  - from 09:45, the zone is −1σ…VWAP (▼) / VWAP…+1σ (▲);
  - a closed 3-min bar with high ≥ −1σ, close < −1σ and bar delta < 0 (mirror) is the §E ENTRY;
  - §E's own re-arm and state machine are kept as they are; it only generates the trigger.
- **OI:** `fronts.read` with §1d's fixed parameters (nine nearest strikes; front = the largest session-peak OI on its
  side; BUILDING / STALLED / UNWINDING).
- **FLOW:** the futures 1-s book bars and the side rule (`ladder.attribute`), the same as §1i. The GoCharting
  disagreement rule is also §1i's.

## 1. The setup: all three must match
**LOCATION.** A §E ENTRY event with d = −1 (RIDE ▼) or +1 (RIDE ▲).

**OI.** Written for ▼; ▲ is mirrored.
- **OI ✓ (RIDE ▼)** = the trend-side front (the **CE** front) is **BUILDING**, **and** the defending front (the **PE**
  front) is **not BUILDING** (STALLED or UNWINDING).
- In her words: the writers on her side are still adding, and the other side has stopped defending.

**FLOW.** Written for ▼; ▲ is mirrored.
- **FLOW ✓ (RIDE ▼)** = `tilt(last 5 min) ≤ −0.10` **and** `tilt(the 15 min before those 5) ≤ +0.10`.
- In words: the pullback was not led by strong counter-trend buying, and the trend side's aggression is back.
- **NIFTY only:** GoCharting disagreement, i.e. a GC tilt on the same 5 min of ≥ +0.10 (▼), reads FLOW ✗. Absent GC
  is not disagreement.

**THE RIDE ENTRY.**
- **When:** the first 3-min bar close, from the §E ENTRY bar through 3 bars after it (≤ 9 min), at which OI ✓ and
  FLOW ✓ both hold.
- **Price:** the close must still be on the trend side of VWAP (▼: close < VWAP).
- **Cutoff:** no entry after **15:00**.
- **Count:** one RIDE entry per §E ENTRY.

**Stamps** (recorded, never gating):
- time, DTE, and leg age (minutes since the READ word began);
- **which pullback of the leg this is** (1st / 2nd / 3rd …);
- pullback depth as a % of the leg;
- the distance to the READ's FLIP;
- the peers' READ words (BANKNIFTY / SENSEX / NIFTY): the sync count;
- STALLED events of the trend-side front during the hold;
- the §1d gate, where logged.

## 2. The hold and the exit: her rules, with no candle close anywhere and no fixed target
Exit at the **first** of:
1. **HARD LINE (a price level, intrabar on 1-min bars).**
   - Initial: ▼ = the higher of the trigger bar's high and VWAP at entry, **+ 0.25σ** ("a poke doesn't fold you").
     Risk is at least 0.5σ. σ is frozen at entry.
   - **Trail:** the line moves to **FLIP (in fut) + 0.25σ** whenever the READ's FLIP, as of the latest closed bar, is
     nearer to price than the current line. It only moves toward price, never away.
2. **SOMEBODY GAVE UP.**
   - Trigger: the trend-side front (▼: CE) reads **UNWINDING** at a 3-min bar close.
   - Exit at that bar's close.
   - STALLED alone is a pullback in the writers and **does not exit**; it is stamped.
3. **15:20.** Marked at the 15:20 price, using the same convention as §1i reading 9.

**Not exits:** the READ's word changing, a single bar, a CVD divergence, VPIN. These are stamped only.

**R** = (E − exit) ÷ (initial line − E) for ▼, mirrored for ▲. The initial risk is used throughout, even after the
trail.

**Outcome fields already in any log are not used.** Everything is recomputed from bars.

## 3. The control (RIDE without the checks)
- **What:** every §E ENTRY in the same cell on the same days, entered at the §E ENTRY bar's close.
- **How it's scored:** with the identical hold and exit (§2).
- **What it isolates:** whether the OI and FLOW checks add anything over "trend + pullback".

## 4. Cells and the pass bar
**Cells (4):** side ▼ / ▲ × group NIFTY + SENSEX / BANKNIFTY.

**PASS** requires all of these, per cell (the same bar as §1i):
1. n ≥ 20 RIDE entries;
2. mean R ≥ **+0.25**;
3. mean R with the single best trade removed is **> 0**;
4. mean R(RIDE) − mean R(control, same cell, same days) ≥ **+0.20**;
5. if total R > 0, no single session supplies more than **40%** of it.

**FAIL:** n ≥ 20 and (mean R ≤ 0 or the difference vs the control < 0).

**INCONCLUSIVE:** anything else.

**Reporting:** n, mean R, mean R without the best trade, the control's mean R and the largest day's share. **No hit rate
is printed anywhere.**

Note: rides are fat-tailed, so check 3 is deliberately hard for them. It guards against one big day carrying the
verdict.

## 5. Both sides of the option (recorded; not part of the bar)
- **For every RIDE entry, three expressions are recorded** at entry and at exit, from the recorded chain LTPs:
  - **buy the with-trend ATM option**;
  - **buy the with-trend option one strike ITM**;
  - **sell the against-trend ATM option**.
- **When they're described:** at n ≥ 20 per cell, as paired rows with the drop-the-best check.
- **Buying and selling carry equal weight.**

## 6. Run policy (the same as §1i Amendment 1)
- **Dry counts** (entries, OI ✓, FLOW ✓, RIDE entries per cell) may be printed now.
- **No R or premium outcome** is computed on recorded days until any RIDE cell reaches n ≥ 20 with the forward rows
  included.
- **Then the past and forward rows are scored ONCE, pooled.**
- **A re-run** is only for a bug that doesn't change a definition, and is logged with its reason.
- **Forward:** every §E ENTRY gets a write-once row in `data/confluence_log.jsonl` (`setup: "RIDE"`), with LOCATION /
  OI / FLOW at the trigger bar and the next 3 bars, the stamps, and the RIDE entry if any.

## 7. Relation to READ-V2 §5
- READ-V2 §5 judges §E's own stop/T1/T2 rows **with her bar owed**. This file supersedes that for the RIDE trade.
- §E's rows keep being written unchanged and serve as this file's control.
- §E's own 3-min-close stop and fixed targets are **not** her hold. They stay on §E's rows as a record, not as RIDE's
  exit.
