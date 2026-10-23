# PRE-REGISTERED: FADE-D, the deceleration fade at an extreme (2026-10-21 ~20:00, UNTESTED)

## Origin (verbatim)
- **Mary, 21 Oct:**
  > "both delta cvd my zone and oi all gave a sign from 09:30 to 10:00 … at the top oi difference which was +47% at
  > 09:50 but at 09:55 is changes +37% … even though the market is going up the strength declined … cvd and delta as
  > well in that zone started decline right at high"
- **Then "offcourse"** to registering it.
- **Her own zone rule (§1b, profile):** "front-runs the OI peak using build-rate deceleration (second derivative),
  because velocity lags". The FADE check of §1i never encoded this.
- **Signed by Claude on her delegation.**
- **21 Oct is in-sample:** it motivated the rule. The thresholds are round numbers fixed now.

## The setup (top = SELL; a bottom = BUY is the mirror)
**1. LOCATION.** Within the evaluation window, at least one of these happened:
- a zone-machine SELL arm or entry (u2→u3);
- **or** a 5-min bar made a new session high.

The **location bar** is the latest such bar.

**2. FLOW SPEED (the effort fades at the extreme), both of:**
- **(a) Fading buying:** a bar that made a new session high within the window has delta **≤ 25%** of the largest
  positive-delta bar of the up-leg. The up-leg runs from the last session low before it, or the open.
- **(b) CVD has turned:** at the bar close, the latest closed bar's delta is **< 0** **and** CVD is below its up-leg
  peak.

**3. OI SPEED (the winning side's lead breaks).**
- **The lead:** PE lead = (PE aaj likha − CE aaj likha) ÷ (PE + CE), over the nine strikes (read.py's window).
- **The test:** the lead is now **≥ 10 points** below its session peak, **and** that peak was within the last
  **15 min**, or the lead fell ≥ 10 points in the last 15 min.
- **For a bottom,** the CE lead mirrors it.

**4. THE ENTRY.**
- **When:** the first 5-min bar close at which 1, 2a, 2b and 3 all hold, with every condition true **within 30 min** of
  the location bar.
- **Price:** the close is still above VWAP (SELL), so there is room to the target.
- **Cutoff:** no entry after 15:00.
- **Count:** one per location episode.
- **Flow source:** GoCharting 5-min bars for NIFTY, with Upstox filling only missing bars. Upstox for BANKNIFTY and
  SENSEX.

**5. STOP:** the session high + 0.25U, with risk at least 0.5σ.

**6. EXIT:** HOLD v2 (§1m, as amended).
- The trend side for a SELL is CE (call writers). Its line starts at the stop.
- For reference, the VWAP-target exit is also recorded.

## Control and pass bar
- **Control:** every location bar (step 1) on the same days, entered at its close, with the same stop and exit. This
  is "the zone or extreme alone".
- **Cells:** SELL / BUY × NIFTY + SENSEX / BANKNIFTY.
- **Pass bar:** §1i §4, per cell:
  - n ≥ 20;
  - mean R ≥ +0.25;
  - drop-best > 0;
  - beats the control by ≥ +0.20R;
  - day share ≤ 40%.
- **No hit rate is printed.**
- **Forward only, from 2026-10-22.** Earlier days may be described IN-SAMPLE and are never counted.

## Logging
Every location episode gets a write-once row in `data/confluence_log.jsonl` (`setup: "FADE-D"`), carrying:
- the 2a / 2b / 3 readings at each 5-min close of its window: the delta ratio, the CVD drawdown, and the lead now /
  peak / 15-min change;
- the entry, if any.
