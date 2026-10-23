# PRE-REGISTERED: THE CONFLUENCE SETUP (zone + OI + order flow) and its pass bar

**Written 2026-10-21 00:45 IST, before any confluence outcome exists. Nothing here is a result.**

## Delegation (verbatim)
- Mary, 2026-10-21: "you decide the pass bar as a trader and the reason i am using oder flow and oi is to not to look at
  the zone standalone they become the signals but when everything matches thats when those become buy or sell zones".
- Then, on the plan to write this, stamp it live and run a one-shot first look: "yes". With these corrections, which
  bind:
  - "there is no rules that i follow like 1:30 or 1:45";
  - "the cut off time for new trade is 3:00 pm and if i m in trade i can hold it till 03:20";
  - "no rules for expirary";
  - "i can buy or sell options to make sure you give importance to both side".
- **Signed by Claude on that delegation.** Same standing as rev 5 B (§1e).

## Disclosure
- **Neither review agent read an outcome field.** That covers EVIDENCE-AUDIT.md and MECHANICS-ATTACK.md.
- **While checking the log schema, I saw the outcome fields of one row:** NIFTY 18 Aug 09:30 zone arm, `stop_hit: true`.
- **This session also read several days live or in replay:** 9, 12, 13, 16 and 19 Oct.
- **No threshold below was chosen from those days.** Every number is a round value fixed by trader judgement, and none
  is to be grid-searched (§5c's rule).

## 1. The setup: all three must match
**ZONE.** A zone ENTRY row in `data/trigger_log.jsonl` (`rule: "zone"`): the zone machine's reversal trigger after a
d2→d3 (BUY) or u2→u3 (SELL) arm.
- **POCKET:** the setup's extreme did not go beyond d3 (BUY) or u3 (SELL), at the arm bar's σ.
- **EXHAUSTION:** the extreme went beyond it.

**OI**, from `fronts.read` on the chain minutes cut at the bar close, with §1d's fixed parameters:
- **POCKET:** the *defending* front (PE for BUY, CE for SELL; the largest session-peak OI among the nine strikes
  nearest spot) is **BUILDING**. The writers who must hold the band are still adding.
- **EXHAUSTION:** the *attacking* front (CE for BUY, PE for SELL) is **STALLED or UNWINDING**. "Somebody gave up".
- **The engine's NO FADE veto is not part of OI ✓.** It cannot be reconstructed on older days. It is recorded as a stamp
  where it exists.

**ORDER FLOW**, from the futures 1-s bars recorded from Upstox for that index. The buy/sell side uses the single
Upstox side rule in `rank.py`; the run report names the function before the run.
- `tilt(W) = (buys − sells) ÷ (buys + sells)` over the window W ending at the bar close.
- **FLOW ✓ (BUY)** = `tilt(last 5 min) ≥ +0.10` **and** `tilt(the 15 min before those 5) ≤ 0`. The push into the zone
  was not buyer-led, and aggression has now turned to the buyers.
- **SELL** is mirrored: `≤ −0.10` and `≥ 0`.
- **NIFTY only:** if GoCharting bars cover the same 5 minutes and their tilt is ≤ −0.10 (BUY) / ≥ +0.10 (SELL), it
  reads **FLOW ✗, sources disagree**. Absent GoCharting is not disagreement.
- **Absorption and exhaustion marks are recorded as stamps.** These are the decoder's R / T / P within the window. They
  are not part of FLOW ✓. That simplification is deliberate: the flip is the measurable core of "aggression turns your
  way".

**THE CONFLUENCE ENTRY**
- It is the first 3-min bar close, from the zone trigger bar through 3 bars after it (≤ 9 min), at which OI ✓ and
  FLOW ✓ both hold.
- Price must still be beyond the 1σ ring on the zone's side.
- No entry after **15:00**.
- One confluence entry per zone setup: re-arms collapse, as in the zone machine.

**There is no time-of-day rule before 15:00 and no expiry rule.** These are recorded as stamps only:
- time;
- DTE;
- first touch;
- depth in σ;
- the READ / day-card word;
- both legs rising;
- a reaction point within 0.25σ of the extreme (PDH/PDL, a round 100, the prior session high/low);
- the §1d `gate` where logged.

## 2. Outcome, in index points and R (direction only)
- **Entry:** E = the confluence bar's close, on the zone machine's own series.
- **σ:** the band σ at the entry bar, frozen.
- **Stop:**
  - POCKET BUY: d3 at entry. EXHAUSTION BUY: the setup's extreme − 0.25σ.
  - Floor: risk is at least 0.5σ.
  - SELL is mirrored.
- **Target:** session VWAP, live. It is touched when a later 1-min bar's high ≥ VWAP (BUY) / low ≤ VWAP (SELL).
- **First passage** is on 1-min bars after entry. A bar touching both counts as **stop first**.
- **No target or stop by 15:20:** marked at the 15:20 close.
- **R** = (exit − E) ÷ (E − stop) for BUY, mirrored for SELL.
- **The control (zone-alone):** every zone entry in the same cell on the same days, scored identically from its own
  trigger bar.
- **Outcome fields already in `trigger_log` are not used** (`mfe`, `mae`, `stop_hit`, …). Everything is recomputed
  from bars.

## 3. Cells
There are 8 cells, each judged alone:
- kind: POCKET / EXHAUSTION;
- side: BUY / SELL;
- group: NIFTY + SENSEX / BANKNIFTY.

## 4. The pass bar (per cell)
**PASS** requires all of:
1. n ≥ 20 confluence entries;
2. mean R ≥ **+0.25**;
3. mean R with the single best trade removed is **> 0**;
4. mean R(confluence) − mean R(zone-alone, same cell, same days) ≥ **+0.20**;
5. if total R > 0, **no single session supplies more than 40%** of it.

**FAIL:** n ≥ 20 **and** (mean R ≤ 0 **or** the difference vs zone-alone < 0).

**INCONCLUSIVE:** anything else. Logging continues.

**Reporting.** A verdict reports n, mean R, mean R without the best trade, the control's mean R and the largest day's
share. No hit rate is printed, here or on any screen.

## 5. Both sides of the option (recorded; not part of the bar)
- **For every confluence entry, record ATM option premiums** at entry and at exit, from the recorded chain:
  - BUY: **buy ATM CE** and **sell ATM PE**;
  - SELL: **buy ATM PE** and **sell ATM CE**.
- **At n ≥ 20 per cell they are described as paired rows on the same entries,** with the drop-the-best check. The
  description then feeds a separate expression registration.
- **Buying and selling carry equal weight.** Neither is the default.

## 6. The one-shot first look, and the forward log
- **The one-shot covers recorded days on which** zone rows, chain minutes and Upstox 1-s futures bars all exist.
- **It runs ONCE,** after this file's sha256 is anchored in `context/research-findings.md` §1i.
- **A re-run is allowed only to fix a bug that does not change a definition.** Each re-run is logged with its reason.
- **The scorer must prove no look-ahead:** values at a bar use data at or before that bar's close.
- **Forward:**
  - **What:** every zone entry gets a write-once row in `data/confluence_log.jsonl`.
  - **Content:** ZONE / OI / FLOW at the trigger bar and the next 3 bars, the stamps, and the confluence entry if any.
  - **Where it shows:** on the panel as `ZONE ✓ · OI ✓ · FLOW ✗` (a count, never a percentage).
  - **When it is judged:** under §4, once each cell reaches n ≥ 20.

## 7. Falsifier, restated
For a cell with n ≥ 20, the confluence idea is falsified if it fails §4.1–§4.2 **or** fails to beat zone-alone (§4.4).
Fewer signals is never, by itself, evidence of anything.
