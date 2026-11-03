# PRE-REGISTERED: OPTION-FLOW READS, four shadow stamps (2026-11-04 ~02:00, before 09:15, UNTESTED)

## Origin (verbatim)
- **Mary, 3 Nov:** "we have order flow of options as well … an orderflow reader for option order flow, ±3 to 5 strike".
- **Mary, 4 Nov:** "india is world biggest derivative market … using option oder flow with our different signals to make
  them stronger" · "see if we can figure something like short covering because they are fastest moves happens in the days".
- **Then "Yes, pre-register"** (4 Nov ~01:50) to the four reads below. Registered by Claude on that word.
- **In-sample:** 28, 29, 30 Oct, 2 and 3 Nov formed every idea here (NOTEPAD A215–A219,
  `docs/optflow/fable/REPORT.md` rounds 1–5, `docs/optflow/brainstorm/strike_bands.py`). They are described, never counted.

## What this is and is not
- **Shadow stamps.** Nothing here gates, suppresses, votes, alerts or changes a word. No Telegram, no screen, until she
  signs a build.
- **No existing registration is touched.** §1b, §1d, §1i–§1r and Jarvis's count are unchanged.
- **NIFTY only.** SENSEX's own option flow is not read (§1q is unchanged). The four reads are four populations, never pooled.
- **These are WHO reads, not timers.** On the in-sample days option flow moved in the same 3-min bar as the futures and
  never earlier (REPORT R4.C), and no squeeze forecast preceded any of 15 fast moves (R5.3). None is registered.

## Common definitions (fixed now)
- **C1 Contracts.** NIFTY, the nearest weekly expiry in that day's chain (`expiry`), strikes in 50-pt steps, as recorded:
  - the chain `data/chain/chain_NIFTY_<day>.jsonl`;
  - the Dext footprint `data/dext/dext_NSE-<id>_<day>.jsonl`, ids from `data/scrip_master.csv`;
  - the futures `data/tape/fut1m_NIFTY_<day>.json`.
- **C2 Grid.** Her 3-min grid: a close at minute m where (m − 555) mod 3 = 2 (09:17, 09:20, …). The bar is minutes
  m−2..m. Everything at a close uses data up to the end of minute m.
- **C3 Per strike per bar.**
  - **OI** = the chain's last snapshot at or before the bar's end. If that snapshot is more than 2 min old: OI?.
  - **delta** = Σ Dext `delta` over the bar's minutes. No footprint: FLOW?.
  - **Premium close** = the chain `ltp` at that snapshot.
- **C4 WHO.** dOI = OI at this close − OI at the previous close.
  - QUIET if |dOI| < 1.5L qty.
  - MIXED if |delta| < 0.2 × |dOI|.
  - Otherwise WRITE (dOI > 0, delta < 0), BUY (dOI > 0, delta > 0), COVER (dOI < 0, delta > 0), DUMP (dOI < 0, delta < 0).
  - **FIRM** = the same label with the delta window shifted one minute earlier. Exchange OI updates about every 63 s
    (R2.3).
- **C5 Groups at the close, spot = the chain's spot.**
  - CAP = CE strikes ≥ spot; FLOOR = PE strikes ≤ spot; ITM_CE = CE < spot; ITM_PE = PE > spot.
  - A group's WHO uses the C4 rule on its sums, with the QUIET floor at 3.0L.
  - **The cap** = the CE strike with the largest OI ≥ spot; **the floor** = the PE strike with the largest OI ≤ spot.
- **C6 Premium bands.** `contract_bars._Vwap` on the strike's own 3-min bars: h and l from Dext, c from C3, v = Dext
  `total_volume`, session from 09:15. Readable from the 09:44 close (10 bars) [I: the early σ is too thin, R4.B].
- **C7 Index bands.** `_Vwap` on the NIFTY futures 3-min bars: ZONE-3M's bands (§1r).
- **C8 Implied delta.** Σ over recorded strikes of Dext `delta` × that strike's chain `delta` (last snapshot), over the
  last three closes (9 min). Sign only.
- **C9 Outcomes (hindsight, evening only).** The futures close at +15 and +30 min after the stamp's close; the strike's
  premium likewise.

## The four reads

### R1 BAND TOUCH + WHO
- **Event.** At a close ≥ 09:44, an ATM or NEAR strike's premium bar touches its own u2 (high ≥ u2) or d2 (low ≤ d2).
  - ATM or NEAR = 0–2 OTM steps, by `round((k − spot)/50)` for a CE and `round((spot − k)/50)` for a PE.
  - Only the first touch per episode counts. An episode ends when the premium closes back through its VWAP.
- **Implied direction.** CE at u2 or PE at d2 = index UP. CE at d2 or PE at u2 = index DOWN.
- **Stamps.**
  - The strike's WHO and whether it is FIRM.
  - **INDEX AT BAND** if the futures bar's high ≥ u2 (UP) or low ≤ d2 (DOWN); else MID.
  - The paired leg (same strike, other side) against its own bands.
- **Outcome at +30.** RUN = the futures went more than 15 pts further in the implied direction. Otherwise STALL/TURN.
  [I: a quarter of a typical fast 15-min move.]
- **Prediction.**
  - Cell COVER × AT BAND is STALL/TURN more often than RUN.
  - It is also STALL/TURN more often than cell COVER × MID.
  - In-sample: 3 of 4 at band; the mid-band "continue" held only 1 of 4. The other cells are logged as controls.

### R2 PULLBACK CARD
- **Event.** A pullback inside a leg: a row of Jarvis's pause log (`data/jarvis/pause_<day>.jsonl`). When that file is
  absent, the first HOLD / WATCH / PALAT? minute after a TREND minute in the call log. The source is named on each row.
- **Read at the pause's second close.** For a ▲ leg (mirror for ▼):
  - **D:** the FLOOR group reads WRITE or BUY at one or more of the two closes and COVER at none → DEFENDING.
  - **I:** ITM_CE reads WRITE at both closes → AGAINST; COVER or DUMP at either → FUEL; else NEUTRAL.
  - **Δ:** the C8 sign → WITH or AGAINST the leg.
  - **P:** the ATM CE's close against its own VWAP → ABOVE or BELOW.
- **Card.**
  - HEALTHY = D DEFENDING, Δ WITH and P ABOVE.
  - REVERSAL-START = I AGAINST, Δ AGAINST and P BELOW.
  - Otherwise MIXED.
- **Outcome.** CONT = a new leg extreme on the 1-min futures closes within 60 min. FAIL = Jarvis's lean flips first.
  Otherwise UNRESOLVED.
- **Prediction.** HEALTHY cards end CONT more often than FAIL. REVERSAL-START cards end FAIL more often than CONT.
  In-sample: 9 of 12 CONT looked healthy; 1 clean FAIL.

### R3 SQUEEZE ON (a state stamp, never a forecast)
- **Stamp ▲.** At a close where **the cap** reads COVER and either:
  - at least two other CE strikes ≥ spot read COVER at the same close; or
  - the cap read COVER at the previous close too.
- **Stamp ▼.** The mirror on the floor and the PE strikes ≤ spot.
- **Outcome at +15.** WITH = the futures move ≥ 20 pts the stamp's way; AGAINST = ≥ 20 pts the other way; else FLAT.
- **Predictions.**
  - (1) It is stamped 1–3 times a day.
  - (2) WITH exceeds AGAINST by count.
  - (3) On each day it lands at or before the second close of the day's covering fast moves: the 3 largest 15-min
    futures moves on the C2 grid, non-overlapping, classed as covering when futures OI fell or the cap/floor read COVER.

### R4 PIN (expiry day only)
- **Stamp.** Only when the chain's expiry is that day, at a close ≥ 13:00. A CE strike and a PE strike at the same strike
  or adjacent strikes both read WRITE (FIRM) at two consecutive closes. The pin is PIN k₁–k₂.
- **Outcome.** HELD = spot stays within [min k − 50, max k + 50] at every close until 15:15. Otherwise LEFT.
- **Prediction.** HELD more often than LEFT. In-sample: 1 expiry (3 Nov 13:30–15:15), described only.

## Logging, window and pass bar
- **The log.** An evening replay over that day's recorded files, causal (each close uses data up to its end), writes one
  write-once row per event to `data/optflow/reads_<day>.jsonl`. Each row carries every C-reading named above, its source,
  and the outcome.
  - The replay script is not built yet. These definitions bind it; where code and this text disagree, this text wins.
  - A missing input is a reason ("FLOW?", "OI?", "no pause file"), never a zero.
  - A day the bridge missed can be fetched after the close (`node optflow/dext_bridge.mjs --now <day>`) and logged then,
    tagged `backfill`.
- **Window.** Forward only, **from 2026-11-04 09:15**, for 20 sessions per read. Expiry days only for R4: 10 expiries.
- **Pass bar: OWED BY THE OPERATOR.**
  - Mary states it before any evaluation is read. Until then the evening log describes rows only.
  - No hit rate, win rate or expectancy is printed.
  - Under 15 rows per cell is INCONCLUSIVE.
- **Kills (any one retires that read to a plain chip):**
  - R1: the AT BAND and MID cells do not differ at n ≥ 15 each.
  - R2: HEALTHY and REVERSAL-START end the same at n ≥ 15 each.
  - R3: WITH does not exceed AGAINST by at least 2 : 1 at n ≥ 15 per direction, or more than 4 stamps a day on 5 of 20
    days (the cascade bar then rises to 3 strikes).
  - R4: over 10 expiries, LEFT as often as HELD.
  - All reads: a result that collapses when its best day is removed.
