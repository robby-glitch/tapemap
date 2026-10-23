# Mary's setup: combined review (21 Oct 2026)

**Sources:**
- `MECHANICS-ATTACK.md` (Opus, as a prop-desk options trader).
- `EVIDENCE-AUDIT.md` (Opus, records only, with no outcome read).
- My own read.

**Method:** no backtests, no outcome statistics. Her records are quoted with their status.

## 1. Verdict in one paragraph
Her central idea is sound and rare: **an intraday stretch caused by flow reverts, a stretch caused by information does
not**, and her records found that boundary four independent ways. What stops it from working as a *system* is not the
idea. Three things do:
1. **Two different trades are glued into one zone.**
2. **Her own 5-year refusals are missing from the tool that arms her trades.**
3. **Nothing has ever been settled, because the pass bar was never set.**

The forward record is now large enough to settle most open questions **as soon as she states the bar.**

## 2. What is strong (keep as is)
- **The regime map:** NIFTY/SENSEX intraday stretches revert; BANKNIFTY, gaps and single stocks do not (§3).
- **Reading the defenders before fading** (the §1d idea): near ATM, top two by OI, building → stalled → unwinding.
- **Management lessons:** no breakeven (it cost about 13 pts a trade on the measured line); "touch nothing until VWAP";
  trail only above VWAP.
- **The discipline:** pre-registration, forward logging, falsifiers written first, and the three absences kept apart.

## 3. The attacks (agreed by all three reviewers unless marked)
| # | Attack | Evidence / mechanism | Severity |
|---|---|---|---|
| A1 | **The zone glues a POCKET fade (2.0–2.4σ, first touch, liquidity noise) to an EXHAUSTION reversal (d3+, forced flow that has spent itself).** One trigger, stop, gate and hold serves neither. | The 5-yr claim refuses fades past 2.4σ; §5c's d3 two-candle trigger was "not falsified"; the d2 "coin flip" used the VOID one-candle trigger. | High |
| A2 | **The 5-yr refusals are missing from the zone machine.** | PaperDesk enforces first touch, ≤ 2.4σ, before 13:15 and DTE ≥ 2; the zone has none of these. Only 188 of 415 zone entries fall inside the 5-yr clock and DTE windows. **Her two tools give opposite instructions on the same chart.** | High, and the cheapest fix |
| A3 | **On trend days, d2 sits in the trend's 1σ–2σ lane**, where trend sellers add. | 10 BUY arms on 22 Sep; armed BUY all day on 8 Oct. | High |
| A4 | **The §1d gate is right for the pocket, wrong for the exhaustion trade.** At a real d3 low the put writers are being run over, so the PE front stalls exactly at the best reversal. | §4: "put-heaviness arrives after the turn". The gate marks zone BUY entries **78 illegal / 13 legal**, against its own prediction of "a large minority". | High (for d3) |
| A5 | **The SELL side is not a mirror.** Rallies here are mostly short covering (O3); covering is forced and runs. | Selling upper bands failed on 5 datasets (one-candle trigger). The u3 two-candle test FAILED. **u2 has never been measured.** | Medium–high |
| A6 | **Bought CE is often the wrong vehicle for a lower-band fade.** IV is high at the low and falls on the rally. | Delta drag, theta and IV crush versus a small VWAP target. | Medium–high |
| A7 | **One hold rule serves two trades.** A fade has a target (VWAP); a ride has none. Fade instincts applied to a ride produce her "exit too early". | Her own diagnosis (24 Sep). | Medium–high |
| A8 | **S2 (cascade) is a chase in a market where NIFTY breakouts fade.** S1 (sweep and reclaim) is really the exhaustion trade at a level. | ORB rejected. S1/S2 exist only in a memory note, with no logs. | Low–medium |
| A9 | **Untested or unsigned rules drive her screen while their due checks go unread.** | §1d drives beeps since 23 Sep (falsifier due: 15 of 10 sessions). Rev 6 is unsigned and folds trades. VPIN (32/30) and `direction.py` (34/30) kill clocks are past due. **Her trade marking stopped after 6 Oct.** | Medium |
| A10 | **The 5-yr record spans a different market.** | One weekly index per exchange from Nov 2024; BANKNIFTY monthly-only; NIFTY expiry Thu → Tue (Sept 2025); lot-size changes. The mechanism (depth, clock, DTE) transfers; weekday effects and lot-counted thresholds don't. | Medium |
| A11 | **"VPIN behind me" doesn't work:** VPIN has no direction by design. | It measures toxicity and expansion risk, not side. | Low–medium |

## 4. Where the reviewers disagree, and my call
- **BANKNIFTY.** Mechanics says ride-only. The audit says "inverts" rests on n = 5–8, under the repo's own n < 15 line.
  - **My call:** don't decide it by opinion. The forward record holds 60 BUY / 63 SELL BANKNIFTY zone entries, so her
    pass bar settles it. Until then, no BANKNIFTY fades on her screen.
- **The d2 contradiction.** I first called d2 "dead". Both agents show that test used the VOID trigger.
  - **My call:** d2 is unmeasured, not dead. The pocket (2.0–2.4σ, first touch) is the version that carries her 5-yr
    claim.
- **The gate.** Mechanics wants a depth split added to §1d. The audit notes §1d is already acting as an entry veto
  that CHECKLIST C11 forbids.
  - **My call:** read §1d's own pre-registered falsifier first (it is due). Change nothing before that.

## 5. Refinements, in the order I'd do them
| # | Refinement | Kind | Needs her |
|---|---|---|---|
| 1 | **State the pass bar and the horizon,** per side, before any outcome is read. The record can then settle the zone, u2 SELL, the stop and BANKNIFTY in **zero more sessions**. | Decision | **Yes, only her** |
| 2 | **Stamp her 5-yr refusals on every zone arm** (first touch, depth ≤ 2.4σ, before 13:15, DTE per index), shown on the face. Never suppress a row. | Pre-register, then log | Sign |
| 3 | **Split the zone into POCKET and EXHAUSTION,** each with its own trigger, stop, gate and target. | Pre-register | Sign |
| 4 | **The day card switches pocket fades off on TREND days.** At most one exhaustion per side, to VWAP. | Pre-register | Sign |
| 5 | **Two hold modes.** FADE: only the hard line until VWAP. RIDE: only the break rule. A fade converts to a ride at VWAP only if fronts, flow and the leg all agree. | Pre-register | Sign |
| 6 | **The vehicle by side and kind** (lower-band fade → sell the PE; upper-band exhaustion → buy the PE; ride at 0–1 DTE → ITM). Display first. | Display → pre-register | Later |
| 7 | **Read the due checks:** §1d falsifier, VPIN, `direction.py`. Clean the 375 midnight copies out of `trigger_log`. | Housekeeping | Her OK to touch data |
| 8 | **One rule set on the screen, signed.** Retire or sign rev 6; remove the candle-close rule she rejected. | Governance | Sign |

## 6. What this means for the panel (the brainstorm we paused)
The panel should be built on **these** setups, not on new rules:
- the phase / day card;
- POCKET vs EXHAUSTION, with her refusals stamped;
- fronts (§1d);
- the hold mode;
- the next reaction point.

The research numbers (pace × tempo, leg, fuel chips) stay as the evidence layer under those words.
