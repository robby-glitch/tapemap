# Graph Report - .  (2026-07-23)

## Corpus Check
- 18 files · ~1,393,620 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 448 nodes · 812 edges · 26 communities (24 shown, 2 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 15 edges (avg confidence: 0.82)
- Token cost: 0 input · 134,129 output

## Community Hubs (Navigation)
- [[_COMMUNITY_UI  app.js (render, token, chain)|UI / app.js (render, token, chain)]]
- [[_COMMUNITY_Live chain poller (chain_live)|Live chain poller (chain_live)]]
- [[_COMMUNITY_Chain analytics (chain_metrics)|Chain analytics (chain_metrics)]]
- [[_COMMUNITY_Event grammar (concepts)|Event grammar (concepts)]]
- [[_COMMUNITY_Gamma  Black-76 math|Gamma / Black-76 math]]
- [[_COMMUNITY_Instrument registry|Instrument registry]]
- [[_COMMUNITY_Cross-index & data sources|Cross-index & data sources]]
- [[_COMMUNITY_Session replay engine|Session replay engine]]
- [[_COMMUNITY_Dhan fetch & validate|Dhan fetch & validate]]
- [[_COMMUNITY_Per-book features & ranks|Per-book features & ranks]]
- [[_COMMUNITY_Replay pipeline (analyzeengine)|Replay pipeline (analyze/engine)]]
- [[_COMMUNITY_Backtest harness|Backtest harness]]
- [[_COMMUNITY_Band-reversal backtest|Band-reversal backtest]]
- [[_COMMUNITY_Gamma layer & carry (concepts)|Gamma layer & carry (concepts)]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]

## God Nodes (most connected - your core abstractions)
1. `$()` - 37 edges
2. `Session` - 26 edges
3. `Session class (event grammar, states, lifecycles)` - 22 edges
4. `render()` - 15 edges
5. `session_json()` - 14 edges
6. `ChainPoller` - 13 edges
7. `renderMap()` - 13 edges
8. `renderData()` - 12 edges
9. `ChainState` - 10 edges
10. `build_payload()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `tally()`  [INFERRED]
  backtest.py → band_backtest.py
- `Per-Index Serving (?idx= in server.py)` --references--> `server.py (serving + API routes)`  [INFERRED]
  docs/superpowers/specs/2026-07-23-multi-index-tapemap-design.md → context/mental-map.md
- `Index-Agnostic Engine Reuse` --references--> `engine.py (Session/Book/GammaLayer)`  [INFERRED]
  docs/superpowers/specs/2026-07-23-multi-index-tapemap-design.md → context/mental-map.md
- `Index-Agnostic Engine Reuse` --references--> `gamma.py (Black-76 math, GEX profile)`  [INFERRED]
  docs/superpowers/specs/2026-07-23-multi-index-tapemap-design.md → context/mental-map.md
- `scan_day()` --calls--> `load_day()`  [EXTRACTED]
  expression_backtest.py → backtest.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **TapeMap base event grammar** — context_logic_plain_english_trap, context_logic_plain_english_divergence, context_logic_plain_english_spring, context_logic_plain_english_armed, context_logic_plain_english_ignition, context_logic_plain_english_climax, context_logic_plain_english_carry [EXTRACTED 1.00]
- **Gamma / MM layer** — context_logic_plain_english_writer_score, context_logic_plain_english_gamma_regimes, context_logic_plain_english_squeeze, context_logic_plain_english_gex_profile, context_project_overview_gamma_pin [EXTRACTED 0.90]
- **The seven invariants** — context_architecture_no_absolute_thresholds, context_architecture_causality, context_architecture_gamma_layer_separate, context_architecture_no_order_execution, context_architecture_ui_renders_engine_decides, context_architecture_signal_receipt, context_architecture_immutable_ground_truth [EXTRACTED 1.00]

## Communities (26 total, 2 thin omitted)

### Community 0 - "UI / app.js (render, token, chain)"
Cohesion: 0.06
Nodes (82): $(), _armVal(), BAND_TIER, boot(), bootData(), captureToken(), chainStart(), chainStop() (+74 more)

### Community 1 - "Live chain poller (chain_live)"
Cohesion: 0.08
Nodes (26): ChainPoller, _client(), _inner(), normalize(), _num(), Option-chain poller: Dhan REST option_chain -> normalized snapshots -> chain_met, Raw Dhan chain payload -> the chain_metrics snapshot contract., Daemon thread owning per-index chain state; publishes JSON bytes into     self.b (+18 more)

### Community 2 - "Chain analytics (chain_metrics)"
Cohesion: 0.09
Nodes (27): ChainState, _clamp01(), _clamp1(), _iv_at(), iv_surface(), max_pain(), pcr(), Full option-chain analytics: writer scores, dealer GEX, max pain, PCR, IV surfac (+19 more)

### Community 3 - "Event grammar (concepts)"
Cohesion: 0.08
Nodes (31): CHOP (chop-suppressed pivot re-cross), ABSORPTION event, ARMED event/state, BREAK / FLIP-TEST event, BUYER-BUILD event, CAMPAIGN event, CLIMAX event, ctx banner (verdict/breadth/narration/flips) (+23 more)

### Community 4 - "Gamma / Black-76 math"
Cohesion: 0.11
Nodes (28): bs_price(), _cdf(), _d1(), gamma(), gex_profile(), implied_vol(), _pdf(), Black-Scholes pricing, implied volatility and dealer GEX profile.  TapeMap gamma (+20 more)

### Community 5 - "Instrument registry"
Cohesion: 0.11
Nodes (27): get(), _load_scrip(), _prev_trading_day(), Instrument registry: one config per tradable index. Static fields live here; vol, Shallow copy of the static config for `idx` (raises KeyError if unknown)., Nearest non-expired monthly future for `under_sym`.      `rows` are parsed scrip, Prior weekday (Sat/Sun skipped; holidays not modelled — YAGNI)., Augment `cfg` in place with fut_id, expiry, prev_day and return it.      `tok` i (+19 more)

### Community 6 - "Cross-index & data sources"
Cohesion: 0.12
Nodes (20): Causality invariant (no future bars), Dhan REST v2 data source, cross_breakout.py (coil-breakout confluence), cross_confluence.py (cross-index confluence), dhan_fetch.py (Dhan API access), instruments.py (per-index registry), live.py (live Dhan mode), _atm_ids Nearest-Strike Generalization (BSXOPT) (+12 more)

### Community 7 - "Session replay engine"
Cohesion: 0.19
Nodes (8): median(), Replays one day across the three books and emits the event stream., Record an event with a per-kind cooldown (minutes). `data` is an         optiona, A pivot cross. First two crossings of a level in a 30m window emit         BREAK, Track the current expansion leg for the episode brain. Consecutive         deton, (Re)arm the momentum-card lifecycle; the newest spring supersedes.         `ref`, Regime banner data: time-quantified window stats, breadth votes,         tradeab, Session

### Community 8 - "Dhan fetch & validate"
Cohesion: 0.18
Nodes (14): chain(), client(), fetch_day(), Fetch 1-min OHLCV+OI from Dhan for NIFTY FUT / CE / PE and validate vs CSVs.  Us, Direct REST 1-min chart call (the SDK lacks the oi flag; validated     pattern:, Scrip-master lookup (same source as resolve()) -> {strike: {CE,PE} ids}., Dhan chart arrays -> compact {t(HH:MM IST), o,h,l,c,v[,oi]} lists., Fetch FUT + 5-strike CE/PE 1-min OHLCV+OI -> data/chain_<day>.json. (+6 more)

### Community 9 - "Per-book features & ranks"
Cohesion: 0.19
Nodes (6): Book, GammaLayer, Rank, Per-instrument session state: ranks, slopes, swing extremes., MM-perspective layer (architecture invariant 3: strictly separate).      Reads t, Percentile-so-far of a stream: rank(x) in [0,1] vs values seen earlier.

### Community 10 - "Replay pipeline (analyze/engine)"
Cohesion: 0.29
Nodes (10): analyze(), Run the tape engine over a data folder and produce the UI timeline JSON.  Used b, days_to_expiry(), load(), main(), Tape-reading replay engine for FUT + CE + PE 1-minute data.  Reads three synchro, Compact per-minute timeline of a finished Session for the UI., Parse a Zerodha CSV export -> (days, years) keeping full sessions only.      day (+2 more)

### Community 11 - "Backtest harness"
Cohesion: 0.32
Nodes (11): _bands(), _forward(), _fut_raw(), _lean(), load_day(), main(), _opt_raw(), _pivots() (+3 more)

### Community 12 - "Band-reversal backtest"
Cohesion: 0.26
Nodes (11): confidence(), _forward(), main(), Prototype backtest of the BAND-REVERSAL setup on cached Dhan days.  Tests the op, Wilson score 95% CI for a win rate (w wins of n decided)., Operator's management: target VWAP, stop just past the entry band., Reverse-vs-break vote from engine outputs. side +1 = long at -2s., scan_day() (+3 more)

### Community 13 - "Gamma layer & carry (concepts)"
Cohesion: 0.24
Nodes (12): CARRY (writer-aware end-of-day bias), Gamma layer (MM perspective), GEX profile (dealer-signed, flip level, walls), Writer score (per book, session-cumulative), backtest.py (forward-outcome scorer), engine.py (Session/Book/GammaLayer), flip_px (true GEX flip via spot revaluation), gamma.py (Black-76 math, GEX profile) (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.25
Nodes (9): Gamma layer separate invariant, Immutable ground-truth CSVs invariant, Every signal carries its receipt invariant, TradingView CSV ground-truth days, UI renders, engine decides invariant, HEAD — evidence message contract, Regression gate (multiset-diff replay baseline), The seven invariants (+1 more)

### Community 15 - "Community 15"
Cohesion: 0.36
Nodes (7): bands(), fut_day(), main(), piv_of(), Cross-instrument validation: run the UNCHANGED engine + band-fade scoring on Ban, rep(), run()

### Community 16 - "Community 16"
Cohesion: 0.32
Nodes (8): /api/data JSON contract, chain_live.py (ChainPoller daemon), Dhan access token (.dhan_token, POST /api/token), analyze.py (replay adapter), server.py (serving + API routes), DATA view / chain analyser, Token capture (⟳ TOKEN button), ui/ (render-only dashboard)

### Community 17 - "Community 17"
Cohesion: 0.29
Nodes (8): BAND-BREAK (negative-gamma continuation), BAND-REVERSAL setup, BAND-REVERSAL confidence tier (HIGH/MED/LOW), band_backtest.py (BAND-REVERSAL backtest), expression_backtest.py (buyer vs seller), Seller vs buyer expression edge, Naked fade edge (~59% WR), Negative-gamma veto

### Community 18 - "Community 18"
Cohesion: 0.43
Nodes (7): fut(), main(), nifty_fut(), Cross-index confluence test: do Nifty band-fade outcomes depend on whether BankN, run(), vol_ranks(), wr()

### Community 19 - "Community 19"
Cohesion: 0.48
Nodes (6): fut(), main(), nifty_bars(), rate(), Coil -> breakout confluence test (the June-15 archetype).  Detects expansion THR, run()

### Community 20 - "Community 20"
Cohesion: 0.43
Nodes (6): block(), main(), Expression backtest: at each FUT ±2σ band tag, compare three ways to express the, Return (outcome, exit_bar): first bar where dir move hits +R / -R,     else time, _resolve(), scan_day()

### Community 21 - "Community 21"
Cohesion: 0.33
Nodes (6): chain_metrics.py (option-chain analytics), Chain squeeze score, IV skew, Max pain, PCR (put-call ratio), SQUEEZE-RISK / SQUEEZE-RELEASE events

### Community 22 - "Community 22"
Cohesion: 0.33
Nodes (6): No absolute thresholds invariant, Per-bar features (vol_r/rng_r/z/bw_r/oi_slope/prem_d), Book class (per-instrument features/ranks), cross_instrument.py (BNF/Sensex validation), Rank (percentile-so-far self-calibration), Self-calibration across instruments

### Community 23 - "Community 23"
Cohesion: 0.50
Nodes (4): No order execution invariant, TapeMap, Design Eval Rubric (Design/Originality/Craft/Functionality), TapeMap Redesign Brief (GAN spec)

## Knowledge Gaps
- **36 isolated node(s):** `Design Eval Rubric (Design/Originality/Craft/Functionality)`, `resolve_futures_id pure resolver`, `Per-Index Sticky ATM (_pick_strike)`, `COL`, `LOUD` (+31 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Session` connect `Session replay engine` to `Instrument registry`, `Per-book features & ranks`, `Replay pipeline (analyze/engine)`, `Backtest harness`, `Band-reversal backtest`, `Community 15`, `Community 20`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `_client_id()` connect `Live chain poller (chain_live)` to `Dhan fetch & validate`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **What connects `Backtest harness for the TapeMap engine on unseen days.  Loads cached Dhan data`, `Full option-chain analytics: writer scores, dealer GEX, max pain, PCR, IV surfac`, `Strike minimizing total intrinsic payout to option holders.` to the rest of the system?**
  _118 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `UI / app.js (render, token, chain)` be split into smaller, more focused modules?**
  _Cohesion score 0.059644322845417236 - nodes in this community are weakly interconnected._
- **Should `Live chain poller (chain_live)` be split into smaller, more focused modules?**
  _Cohesion score 0.08246225319396051 - nodes in this community are weakly interconnected._
- **Should `Chain analytics (chain_metrics)` be split into smaller, more focused modules?**
  _Cohesion score 0.08636977058029689 - nodes in this community are weakly interconnected._
- **Should `Event grammar (concepts)` be split into smaller, more focused modules?**
  _Cohesion score 0.07956989247311828 - nodes in this community are weakly interconnected._