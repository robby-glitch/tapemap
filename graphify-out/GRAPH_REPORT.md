# Graph Report - .  (2026-07-23)

## Corpus Check
- Large corpus: 202 files · ~1,390,923 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 411 nodes · 744 edges · 17 communities
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 43 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_UI App & Validator|UI App & Validator]]
- [[_COMMUNITY_Engine & Signal Logic|Engine & Signal Logic]]
- [[_COMMUNITY_Backtesting Harnesses|Backtesting Harnesses]]
- [[_COMMUNITY_Chain Metrics|Chain Metrics]]
- [[_COMMUNITY_Live Chain Poller|Live Chain Poller]]
- [[_COMMUNITY_Multi-Index Design & Project Context|Multi-Index Design & Project Context]]
- [[_COMMUNITY_Gamma & GEX Math|Gamma & GEX Math]]
- [[_COMMUNITY_Instrument Registry & Live Feed|Instrument Registry & Live Feed]]
- [[_COMMUNITY_Dhan Data Fetch|Dhan Data Fetch]]
- [[_COMMUNITY_UI Prototype MeridianRedesign|UI Prototype: Meridian/Redesign]]
- [[_COMMUNITY_Cross-Instrument Confluence|Cross-Instrument Confluence]]
- [[_COMMUNITY_Server HTTP Handler|Server HTTP Handler]]
- [[_COMMUNITY_Cross-Instrument Breakout|Cross-Instrument Breakout]]
- [[_COMMUNITY_UI Prototype Tape Scroll|UI Prototype: Tape Scroll]]
- [[_COMMUNITY_UI Prototype Variants|UI Prototype: Variants]]
- [[_COMMUNITY_Project Overview & GAN Harness|Project Overview & GAN Harness]]
- [[_COMMUNITY_Causal Features & Pivots|Causal Features & Pivots]]

## God Nodes (most connected - your core abstractions)
1. `$()` - 33 edges
2. `Session` - 29 edges
3. `ChainPoller` - 15 edges
4. `ChainState` - 14 edges
5. `session_json()` - 14 edges
6. `render()` - 14 edges
7. `renderMap()` - 13 edges
8. `build_payload()` - 12 edges
9. `renderData()` - 12 edges
10. `load_day()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Per-bar Features (Book: vol_r, rng_r, z, bw_r, oi_slope, prem_d)` --references--> `Book`  [EXTRACTED]
  context/logic-plain-english.md → engine.py
- `SQUEEZE-RISK / SQUEEZE-RELEASE` --references--> `GammaLayer`  [EXTRACTED]
  context/logic-plain-english.md → engine.py
- `GEX Profile (dealer-signed, flip level, put/call walls)` --references--> `gex_profile()`  [EXTRACTED]
  context/logic-plain-english.md → gamma.py
- `ChainPoller` --uses--> `ChainState`  [INFERRED]
  chain_live.py → chain_metrics.py
- `Option Chain Analyser (DATA tab)` --references--> `ChainPoller`  [EXTRACTED]
  context/progress-tracker.md → chain_live.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **TapeMap architecture invariants** — context_architecture_no_absolute_thresholds, context_architecture_causality_invariant, context_architecture_gamma_layer_separation, context_architecture_ui_renders_engine_decides, context_architecture_no_order_execution [EXTRACTED 1.00]
- **Tape-reading base engine (states + events + lifecycles)** — context_logic_plain_english_engine_states, context_logic_plain_english_event_grammar, context_logic_plain_english_trap_lifecycle, context_logic_plain_english_momentum_setup, context_logic_plain_english_episode_brain [INFERRED 0.85]
- **Gamma / MM-perspective layer** — context_logic_plain_english_gamma_regimes, context_logic_plain_english_writer_score, context_logic_plain_english_squeeze_events, context_logic_plain_english_gex_profile [INFERRED 0.85]
- **Replay Scrubber + State-Ribbon Playback Pattern** — ui_meridian_prototype, ui_redesign_prototype, ui_tapemap_session_stage, ui_tapescroll_vertical_tape [INFERRED 0.75]
- **Quick Style Studies (Terminal / Story / Cockpit)** — ui_variant_a_terminal, ui_variant_b_story, ui_variant_c_cockpit [INFERRED 0.75]
- **Multi-Index Feed & Serving Pipeline** — docs_superpowers_specs_2026_07_23_multi_index_tapemap_design_instrument_registry, docs_superpowers_specs_2026_07_23_multi_index_tapemap_design_build_payload, docs_superpowers_specs_2026_07_23_multi_index_tapemap_design_chain_poller, docs_superpowers_specs_2026_07_23_multi_index_tapemap_design_per_index_serving, ui_index_idxtabs [EXTRACTED 0.85]
- **Seven Invariants Constraint Set** — context_mental_map_causal_features, context_mental_map_percentile_ranks, context_mental_map_render_only_ui, context_mental_map_regression_gate, context_code_standards_head_evidence_contract [INFERRED 0.85]

## Communities (17 total, 0 thin omitted)

### Community 0 - "UI App & Validator"
Cohesion: 0.07
Nodes (72): $(), _armVal(), BAND_TIER, boot(), bootData(), chainStart(), chainStop(), chSpk() (+64 more)

### Community 1 - "Engine & Signal Logic"
Cohesion: 0.06
Nodes (38): analyze(), Run the tape engine over a data folder and produce the UI timeline JSON.  Used b, Regression Gate (replay multiset-diff), Gamma Layer Separation Invariant, BAND-REVERSAL / BAND-BREAK Setup, BAND Confidence Tier (HIGH/MED/LOW), Engine States (OPENING/BALANCE/COILING/ARMED/TREND-UP/TREND-DOWN), Episode Brain (leg RUNNING/STALLING/SPENT) (+30 more)

### Community 2 - "Backtesting Harnesses"
Cohesion: 0.09
Nodes (35): _bands(), _forward(), _fut_raw(), _lean(), load_day(), main(), _opt_raw(), _pivots() (+27 more)

### Community 3 - "Chain Metrics"
Cohesion: 0.09
Nodes (25): ChainState, _clamp01(), _clamp1(), _iv_at(), iv_surface(), max_pain(), pcr(), Full option-chain analytics: writer scores, dealer GEX, max pain, PCR, IV surfac (+17 more)

### Community 4 - "Live Chain Poller"
Cohesion: 0.09
Nodes (26): ChainPoller, _client(), _inner(), normalize(), _num(), Option-chain poller: Dhan REST option_chain -> normalized snapshots -> chain_met, Raw Dhan chain payload -> the chain_metrics snapshot contract., Daemon thread owning per-index chain state; publishes JSON bytes into     self.b (+18 more)

### Community 5 - "Multi-Index Design & Project Context"
Cohesion: 0.08
Nodes (33): /api/data Additive-Only Response Contract, HEAD — evidence Message Contract, No Fabricated Data, Causal Features (bar i uses bars <= i), dhan_fetch.py Data Access, engine.py (Book / Session / GammaLayer), gamma.py Black-76 Math, live.py Live Dhan Feed (+25 more)

### Community 6 - "Gamma & GEX Math"
Cohesion: 0.11
Nodes (28): bs_price(), _cdf(), _d1(), gamma(), gex_profile(), implied_vol(), _pdf(), Black-Scholes pricing, implied volatility and dealer GEX profile.  TapeMap gamma (+20 more)

### Community 7 - "Instrument Registry & Live Feed"
Cohesion: 0.11
Nodes (27): get(), _load_scrip(), _prev_trading_day(), Instrument registry: one config per tradable index. Static fields live here; vol, Shallow copy of the static config for `idx` (raises KeyError if unknown)., Nearest non-expired monthly future for `under_sym`.      `rows` are parsed scrip, Prior weekday (Sat/Sun skipped; holidays not modelled — YAGNI)., Augment `cfg` in place with fut_id, expiry, prev_day and return it.      `tok` i (+19 more)

### Community 8 - "Dhan Data Fetch"
Cohesion: 0.18
Nodes (14): chain(), client(), fetch_day(), Fetch 1-min OHLCV+OI from Dhan for NIFTY FUT / CE / PE and validate vs CSVs.  Us, Scrip-master lookup (same source as resolve()) -> {strike: {CE,PE} ids}., Dhan chart arrays -> compact {t(HH:MM IST), o,h,l,c,v[,oi]} lists., Fetch FUT + 5-strike CE/PE 1-min OHLCV+OI -> data/chain_<day>.json., Find NIFTY current FUT + 24200 CE/PE (21 Jul 2026 expiry) in security master. (+6 more)

### Community 9 - "UI Prototype: Meridian/Redesign"
Cohesion: 0.20
Nodes (10): Arc Session Timeline, Board Rail, Event Tape Scroll, MERIDIAN Prototype, Ribbon Stage, Chart Stage, Hero Header, Level Ladder (+2 more)

### Community 10 - "Cross-Instrument Confluence"
Cohesion: 0.43
Nodes (7): fut(), main(), nifty_fut(), Cross-index confluence test: do Nifty band-fade outcomes depend on whether BankN, run(), vol_ranks(), wr()

### Community 11 - "Server HTTP Handler"
Cohesion: 0.32
Nodes (3): Handler, ?idx= clamped to an enabled index; unknown/absent -> DEFAULT., SimpleHTTPRequestHandler

### Community 12 - "Cross-Instrument Breakout"
Cohesion: 0.48
Nodes (6): fut(), main(), nifty_bars(), rate(), Coil -> breakout confluence test (the June-15 archetype).  Detects expansion THR, run()

### Community 13 - "UI Prototype: Tape Scroll"
Cohesion: 0.29
Nodes (7): Read Rail (Verdict/Books/MM), TapeMap Session Stage (V3), Session Stage Canvas, Transport Scrubber, NOW Rail, Vertical Tape Canvas, TapeMap Vertical Tape (V4)

### Community 14 - "UI Prototype: Variants"
Cohesion: 0.40
Nodes (6): Terminal Chart & Tape Log, Variant A — Terminal, Variant B — Story, Story Chapters & Event Cards, Variant C — Cockpit, Cockpit Gauges & Heartbeat

### Community 15 - "Project Overview & GAN Harness"
Cohesion: 0.40
Nodes (5): No Absolute Thresholds (Percentile Self-Calibration), No Order Execution (Signal-only, permanent), TapeMap, Design Eval Rubric (Design/Originality/Craft/Functionality), TapeMap Redesign Brief (GAN spec)

### Community 16 - "Causal Features & Pivots"
Cohesion: 0.50
Nodes (4): Causality Invariant (no future bars; replay==live), Per-bar Features (Book: vol_r, rng_r, z, bw_r, oi_slope, prem_d), VWAP σ Bands (z-score, ±1/2/3σ, band width), Standard Pivots (P/R1-R3/S1-S3)

## Knowledge Gaps
- **34 isolated node(s):** `COL`, `LOUD`, `GAMMA_COL`, `GAMMA_TXT`, `EVC` (+29 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Session` connect `Engine & Signal Logic` to `Backtesting Harnesses`, `Instrument Registry & Live Feed`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `ChainPoller` connect `Live Chain Poller` to `Server HTTP Handler`, `Engine & Signal Logic`, `Chain Metrics`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `ChainState` connect `Chain Metrics` to `Live Chain Poller`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ChainPoller` (e.g. with `ChainState` and `Handler`) actually correct?**
  _`ChainPoller` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Run the tape engine over a data folder and produce the UI timeline JSON.  Used b`, `Backtest harness for the TapeMap engine on unseen days.  Loads cached Dhan data`, `Prototype backtest of the BAND-REVERSAL setup on cached Dhan days.  Tests the op` to the rest of the system?**
  _119 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `UI App & Validator` be split into smaller, more focused modules?**
  _Cohesion score 0.06666666666666667 - nodes in this community are weakly interconnected._
- **Should `Engine & Signal Logic` be split into smaller, more focused modules?**
  _Cohesion score 0.05902980713033314 - nodes in this community are weakly interconnected._