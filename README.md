# Tape Engine — FUT + CE + PE 3D replay

Reads three synchronized 1-minute CSVs (futures, call, put — Zerodha export
format: OHLC, VWAP, ±1/2/3σ bands, standard pivots, OI, Volume) and replays the
session as a state/event stream, the way a tape reader would narrate it.

## Run

```
python engine.py data 24200 2026-07-21     # replay: folder, strike, weekly expiry
python server.py 8765 data 24200 --mock-chain   # UI at http://127.0.0.1:8765 (offline demo)
python server.py live                       # live mode (needs a Dhan token)
python band_backtest.py [--cost 1.5]        # BAND-REVERSAL backtest on cached days
python test_chain_metrics.py                # chain-layer unit checks
python -m pytest test_instruments.py        # instrument-resolver unit checks
```

- `data` — folder containing `FUT_3day.csv`, `CE_3day.csv`, `PE_3day.csv`
- `24200` — the option strike (instrument metadata; enables spring location-gating)
- `2026-07-21` — weekly expiry the day is priced against (optional; the CSV year
  is read so expiry math is month/year-boundary safe)

### Secrets (all gitignored)

- Dhan **access token**: env `DHAN_TOKEN` or a `.dhan_token` file. It expires
  daily — copy the fresh token from the Dhan portal and click **⟳ TOKEN** in the
  TapeMap header: it captures from the clipboard, validates, saves `.dhan_token`,
  and hot-reloads the pollers (a `type=password` paste field appears if the
  browser blocks clipboard access). The token is never logged or displayed.
- Dhan **client id**: env `DHAN_CLIENT_ID` or a `.dhan_client` file (never in
  source).

## Principles

- **No absolute price/size thresholds.** Features are ranked against the
  session's own expanding distribution (percentile-so-far), so the same engine
  works on NIFTY, BANKNIFTY, or stocks without retuning. Percentile cutoffs
  (0.9, 0.97) and time windows are still tuned constants.
- **3D:** signals with lead time come from cross-book reads (OI rotation,
  mirror divergence, synchronized volume), not from any single chart.

## Event grammar

CAMPAIGN, BUYER-BUILD, TRAP, DIVERGENCE, PRESS, SPRING/ARMED, IGNITION,
CLIMAX, ABSORPTION, BREAK/FLIP-TEST, CARRY (end-of-day bias). States:
BALANCE, COILING, ARMED, TREND-UP/DOWN.

## Validation (in-sample: Jul 15–17, 2026)

**These three days shaped development — they are demonstrations, not
out-of-sample proof.** The engine was tuned while reading them, so a clean read
here is expected, not evidence of forward edge.

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

## Backtest evidence & limits

`band_backtest.py` on 54 cached days (219 ±2σ tags), with causal R (no full-day
lookahead) and stop-first scoring:

- **Naked fade** ≈ 59% WR, but the 95% CI is **50–67%** — the lower bound sits at
  a coin flip. Net ≈ **+0.14R/trade** after a 1.5-pt round-trip cost assumption
  (`COST_PTS`, override with `--cost`).
- **Negative-gamma veto** (fade dies, continuation wins) points the right way —
  fade ~33% vs continuation ~67% — but rests on **n≈9 decided trades** [CI 12–65].
- The confidence tiers (deep-3σ, vote≥2, full-setup) are all **n<30** cells and
  are flagged with a leading `!` in the output.

**Honest status:** the tier and veto rules were tuned on the *same* 54 days they
report on, so those numbers are in-sample. Treat the tiers as **hypotheses, not
proof.** The rules are frozen as of this commit; `chain_live.py` records every
live day to `data/chain/`. Re-run the backtest on **30–50 fresh** days before
trusting any tier — that is the real out-of-sample test.

## Operational notes (2026-07-27 outage postmortem)

The bar builder froze for ~1 h while the UI kept rendering the last payload as
live. Root cause: `live._atm_ids()` re-downloaded the 37 MB detailed scrip
master **every refresh cycle per index**; when CDN throughput dropped to
~80 KB/s the single serial refresh thread hung (urllib `timeout=` bounds socket
ops, not a slow trickle). Fixes now in place:

- **Scrip master cached three deep** (memory / `data/scrip_master.csv` / download,
  per IST day) — `instruments._load_scrip()`; ATM ids + pivots memoized in `live.py`.
- **Wall-clock deadlines** on every download (`instruments.fetch_bytes`).
- **Heartbeat**: `/api/data` carries `built_at`; the UI shows a **TAPE STALE**
  banner when the payload is >90 s old. A frozen tape can no longer look live.
- **`tapemap.log`**: all server diagnostics (with tracebacks) persist here,
  not just in the console window.
- **One refresh thread per index** — one bad index can't stall the others.
- `/api/gex` serves the newest `data/gex_*.json` (adds `as_of`).

**Known external quirk — Zerodha Kite MCP:** `get_positions` returns every
position row **duplicated**. Never ingest it raw; dedupe on
`(instrument_token, product)` and cross-check `option_premium` in `get_margins`.
