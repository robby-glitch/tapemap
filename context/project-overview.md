# TapeMap

## Overview

TapeMap is a second-screen trading intelligence instrument for an intraday
Indian index-options trader. It ingests three synchronized 1-minute books —
index futures (FUT), one or more call options (CE) and put options (PE) — and
narrates the session in plain words backed by data receipts: where traps are
forming, where momentum is loading, what market makers' hedging will do to the
next move, and what bias carries into tomorrow. It does not draw candlestick
charts (the trader already has those on another monitor); it reads the tape
the way an expert tape-reader would, continuously, without fatigue.

## Goals

1. Detect **traps** (extremes not confirmed by the option books) and
   **momentum windows** (springs: disbelieved dips/rallies with trapped
   fuel) minutes before they resolve — measured by replaying labeled days.
2. Expose the **market-maker perspective** (gamma layer): PIN vs AMPLIFIED
   regimes, squeeze risk/release, and the multi-strike GEX profile (flip
   level, put/call walls) — kept strictly separate from base signals.
3. Self-calibrate to any instrument (NIFTY, BANKNIFTY, stocks) — **no
   absolute thresholds anywhere**; every feature ranks against the session's
   own expanding distribution.
4. Pass out-of-sample validation on 15–20 unseen days before any live use.

## Core User Flow

1. Trader starts the local server (`python server.py`) and opens
   `localhost:8765`.
2. Picks a session day (or, later, LIVE mode) — the state header, trap radar,
   momentum windows, level ladder and narrative log populate instantly.
3. During the session (or replay), glances 2 seconds for state + active
   calls; leans in 10 seconds to read the OI/volume/level evidence.
4. Uses the MM/gamma strip to judge whether dealer hedging dampens
   (pin — fade extremes) or amplifies (squeeze — ride) the next move.
5. At close, reads the CARRY verdict (residual OI) for next-day bias.

## Features

### Analysis engine (engine.py)

- Self-calibrating per-minute features: VWAP z-score, band width, OI slopes,
  volume/range percentile ranks (expanding, causal — no lookahead).
- Cross-book reads: writer/buyer disambiguation, mirror divergence,
  synchronized volume detonation, defended-strike detection.
- States: OPENING, BALANCE, COILING, ARMED, TREND-UP, TREND-DOWN.
- Events: TRAP, DIVERGENCE, CAMPAIGN, BUYER-BUILD, PRESS, SPRING, ARMED,
  IGNITION, CLIMAX, ABSORPTION, BREAK, FLIP-TEST, CARRY.
- Gamma layer (separate): PIN/AMPLIFIED regime, GAMMA-PIN, SQUEEZE-RISK,
  SQUEEZE-RELEASE events; Stage 2 adds GEX profile (flip level, walls).

### Data (dhan_fetch.py + data/)

- TradingView CSV ingestion (legacy, 3 labeled ground-truth days).
- Dhan REST fetching: any day, any strike, 1-min OHLCV + OI (validated
  bar-perfect vs TradingView), multi-strike chain for GEX.
- Self-computed VWAP/σ bands + standard pivots for API-sourced data.

### UI (ui/ — "Replay Dashboard" V2)

- State header, three book tiles, TRAP RADAR + MOMENTUM WINDOWS hero cards,
  annotated level ladder with loud LIVE row, narrative log with event
  hierarchy, replay scrubber (1×–25×), CARRY strip, MM/gamma strip.

## Scope

### In Scope

- Replay + (later) live signal generation and narration; alerting.
- NIFTY first; design must generalize to BANKNIFTY/stocks without retuning.
- Backtesting harness over Dhan-fetched historical days.

### Out of Scope

- Order placement / auto-trading — permanently. Signal-only.
- Candlestick charting (trader has charts elsewhere).
- Light theme, mobile layout.
- Personalized financial advice — the tool reports mechanics, not
  recommendations.

## Success Criteria

1. Replaying the 3 labeled days reproduces the documented calls (Fri ARMED
   13:50 → IGNITION 14:15; Thu ARMED bearish 10:49; Wed PRESS → 12:56
   CLIMAX; carries BEARISH/NEUTRAL/BULLISH) with zero regressions when new
   layers are added.
2. Gamma layer flags Fri 14:15 and Wed 12:56 as SQUEEZE-RELEASE and Thu as
   predominantly PINNED, without altering any base event.
3. Stage-2 GEX on Jul 17 puts the flip/walls consistent with the observed
   defense of 24200 and exhaustion above 24300.
4. Out-of-sample: on ≥15 unseen days, documented hit/miss scorecard exists
   for ARMED→move and TRAP→reversal, with honest failure analysis.
