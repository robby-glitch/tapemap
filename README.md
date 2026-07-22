# Tape Engine — FUT + CE + PE 3D replay

Reads three synchronized 1-minute CSVs (futures, call, put — Zerodha export
format: OHLC, VWAP, ±1/2/3σ bands, standard pivots, OI, Volume) and replays the
session as a state/event stream, the way a tape reader would narrate it.

## Run

```
python engine.py data 24200
```

- `data` — folder containing `FUT_3day.csv`, `CE_3day.csv`, `PE_3day.csv`
- `24200` — the option strike (instrument metadata; enables spring location-gating)

## Principles

- **No absolute thresholds.** Every feature is ranked against the session's own
  expanding distribution (percentile-so-far). Same engine works on NIFTY,
  BANKNIFTY, or stocks without retuning.
- **3D:** signals with lead time come from cross-book reads (OI rotation,
  mirror divergence, synchronized volume), not from any single chart.

## Event grammar

CAMPAIGN, BUYER-BUILD, TRAP, DIVERGENCE, PRESS, SPRING/ARMED, IGNITION,
CLIMAX, ABSORPTION, BREAK/FLIP-TEST, CARRY (end-of-day bias). States:
BALANCE, COILING, ARMED, TREND-UP/DOWN.

## Validation (ground truth: Jul 15–17, 2026)

- Jul 15: divergences on every FUT high (CE refusing to pay), bearish PRESS
  ~25 min before the 12:56 waterfall, IGNITION DOWN + PE covering CLIMAX
  marking the low, **BEARISH carry** → Jul 16 was indeed heavy.
- Jul 16: opening TRAP (CE round-tripped 136→66), **ARMED bearish 10:49**,
  11 min before the 24220 top → −165 pts. NEUTRAL carry.
- Jul 17: bullish divergences all morning, **ARMED bullish 13:50** — 25 min
  before the 14:15 ignition (flagged "FIRES A LIVE SPRING"), CE CLIMAX top
  marker at the 231 spike, R2 flip-test, **BULLISH carry** into Monday.

Known gaps: Jul 15's 09:28 opening trap is missed by the band test (the spike
itself inflates the newborn bands) — caught indirectly by DIVERGENCE; Thu
13:31 CLIMAX fired on a drift low (no sync-volume requirement yet).
