# TapeMap — Mental Map

One screen that reads the tape in words. The trader has charts elsewhere;
this tool says what the FUT + ATM CE + ATM PE books are DOING — traps,
momentum windows, market-maker positioning — with every claim data-backed.
It never places orders (permanent rule).

## The chess board (files → responsibility)

| File | Owns |
|---|---|
| engine.py | ALL intelligence. `Book` (per-instrument features/ranks), `Session` (event grammar, states, trap+setup lifecycles, episode brain, ctx banner, structure map), `GammaLayer` (MM regimes, writer scores, squeeze events, live IV). Pure stdlib + gamma.py. |
| gamma.py | Black-76 math: price/vega/gamma, IV solver, dealer-signed GEX profile. Pure math, no state. |
| analyze.py | Replay: 3-day CSVs → list of finished Sessions → JSON. |
| live.py | Live: Dhan REST (FUT + sticky 100-grid ATM CE/PE), self-computed VWAP/σ/pivots, SAME Session class, CARRY suppressed mid-session. `REFRESH_S=60`. |
| server.py | Serves ui/ + `/api/data` (+`/api/gex` for Jul 17). `python server.py` = replay; `python server.py live` = live with 60s refresh thread. Port 8765. |
| dhan_fetch.py | Instrument resolution (scrip master), validated REST intraday with `oi:true`, `chain` command for multi-strike days. |
| gex_run.py | Stage-2 GEX for a chain day → data/gex_*.json (causal IV forward-hold). |
| ui/index.html + style.css + app.js | Render-only. TAPE view (READ panel, trap radar, momentum, ladder, log, ctx banner, TODAY SO FAR) + DATA view (widget grid + IV/gamma/MM top bar). No logic that isn't display composition; consumes structured JSON fields, no prose parsing in the hero cards. |
| data/ | IMMUTABLE ground truth: FUT/CE/PE_3day.csv (Jul 15–17), chain/gex JSON. Parse CSVs by column INDEX (headers are mojibake). FUT exports order pivots BEFORE vwap; options the reverse. |
| context/ | This constitution. progress-tracker.md = full history; logic-plain-english.md = every rule in words. |
| replay_*.txt | Regression baselines (latest = replay_band2.txt). |
| backtest.py | Offline: runs the UNCHANGED engine over data/backtest/ caches, scores ARMED/SPRING/TRAP/episode/CARRY forward outcomes in R units. `load_day(day,prev)` reused by the others. |
| band_backtest.py | Offline: prototypes the BAND-REVERSAL fade in tiers (naked / 3D-confluence / confidence-vote / gamma-sign split). |
| expression_backtest.py | Offline: at each ±2σ tag prices FUT-fade vs BUY-option vs SELL-option with real option closes + IV; splits by gamma sign / IV-rank / dte. |
| cross_instrument.py | Fetches BankNifty (61088,NSE_FNO) + Sensex (1144507,BSE_FNO), runs the engine + band scoring to validate self-calibration across instruments. In-memory (not cached). |
| cross_confluence.py / cross_breakout.py | Cross-index research: at Nifty band tags / coil-breakouts, does BankNifty+Sensex alignment+volume change the outcome. Fetch BNF+Sensex FUT live. |
| data/backtest/ | Cached Dhan history: fut_YYYY-MM-DD.json (Dhan arrays) + opt_YYYY-MM-DD.json (fixed-strike CE/PE + per-minute IV), ~55 Nifty days (Apr–Jul). Token-independent. |
| .dhan_token | Operator-refreshed daily (web.dhan.co). Never hardcode. Read at runtime. |

## Data flow

CSV / Dhan bars → `Session.run()` → per minute: Book features →
events + state + gamma + setup + ctx (episode/box/playbook/verdict) →
`session_json()` → `/api/data` → app.js render(i) → both views.
Replay and live run the IDENTICAL Session — that is invariant #2.

## The seven invariants (never break)

1. No absolute market thresholds — percentile-so-far ranks only (`Rank`).
   Relative geometry constants (strike-step fractions, leg fractions) OK
   with a justification comment.
2. Causal: bar i uses only bars ≤ i. Replay engine == live engine.
3. Gamma layer NEVER modifies base signals (clean backtest comparison).
4. No order execution, ever.
5. Flat files only, no DB.
6. UI is render-only; engine emits "HEAD — evidence" strings + structured
   `data`/`ctx`/`setup` fields.
7. Regression gate before calling any unit done:
   `python engine.py data 24200 > replay_new.txt`, multiset-diff vs the
   latest baseline; BASE grammar lines lost must be 0 (unit's own new
   kinds may re-time; say so in the tracker).

## Operating notes

- Live: `python server.py live` → localhost:8765, brand shows ●LIVE,
  UI repolls 60s, pins to newest bar. Restart server after ANY engine edit
  (payload built in-process).
- Sticky ATM: 100-grid, migrates only after price holds >0.6 grid-steps
  away for 5 refreshes (see live.py `_pick_strike`).
- GateGuard hook denies the first Write/Edit/Bash per file/session —
  state facts in the message text, retry the identical call. Watch for
  PARTIAL batch application; re-send only the denied edits.
- Known ground truth for sanity: Fri ARMED 13:50 → FIRED 14:15 squeeze;
  Wed 12:56 waterfall; Thu pin day; Jul 20 three-act day; Jul 15 second-half
  down move (BAND-BREAK + IGNITION-DOWN case study, see tracker).

## Known data caveats (important before trusting any backtest)

1. FUTURES CONTRACT: data/backtest uses 61093 = the JULY future for ALL
   dates. For dates before ~late-Jun it was the BACK month (June was front)
   → early-Jun FUT is the wrong contract (Jun 15 reads FLAT vs the operator's
   front-month breakout chart). Fix: resolve front-month future per date
   (needs Dhan EXPIRED-futures feed) before trusting pre-late-Jun FUT / any
   breakout test. Mean-reversion band results ~intact (structure is relative)
   but volume/levels for June are back-month.
2. OPTION OI: Dhan's expired feed is ROLLING-ATM (serves a strike only while
   near ATM). Reconstructed to FIXED-STRIKE by pulling ATM-offset band
   (ATM-7..+7) and stitching one 100-grid strike per day → clean OI, 0 hops.
   Bug history: toDate is EXCLUSIVE; data nests at data.data.ce/pe.
3. dte metric assumes Tuesday weekly expiry (Nifty). WRONG for Sensex (BSE,
   different expiry day) → its near/far-expiry splits are mislabeled. The
   confidence TIER (bakes in Nifty dte+IV) must NOT be applied to
   BankNifty/Sensex without per-instrument recalibration.
4. BankNifty/Sensex data is fetched in-memory (cross_*.py), not cached.

## Current frontier

BAND-REVERSAL/BAND-BREAK live-verify (next Nifty session, expiry-day 0dte
= ideal HIGH-tier test). Open research: cross-index confluence as a MOMENTUM
confirmer (front-month contract + multi-day coil detector); per-instrument
tier calibration; more unseen days for thin buckets (neg-gamma, deep-3σ).
