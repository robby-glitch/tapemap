# Progress Tracker

Update this file after every meaningful implementation change.

## Current Phase

- In progress — Gamma layer (MM perspective), Stage 1.

## Current Goal

- Implement `GammaLayer` in engine.py per the approved plan
  (`~/.claude/plans/before-you-run-any-hashed-bubble.md`): PIN/AMPLIFIED
  regime + GAMMA-PIN / SQUEEZE-RISK / SQUEEZE-RELEASE events, exported in
  session JSON, with the base event stream byte-identical (regression gate).

## Completed

- Tape engine (engine.py): self-calibrating features, states, 13 event
  types; validated against 3 labeled days (Jul 15–17, 2026) — see README
  scorecard.
- UI V2 "Replay Dashboard" (ui/): trap radar, momentum windows, annotated
  ladder with LIVE row, narrative log, replay scrubber; verified in browser
  at 14:11/14:15 Jul 17.
- JSON pipeline (analyze.py, server.py) at `/api/data`, localhost:8765.
- Dhan connectivity (dhan_fetch.py): token validated; instrument resolution
  (FUT 61093, 24200CE 57348, 24200PE 57349); 1-min OHLCV bar-perfect vs
  TradingView; OI via direct REST `oi:true` exact-match (PE peak 24,435,645
  @13:01 Jul 17).
- Multi-strike proof: 33/33 series (3 days × FUT + 5 strikes × CE/PE), full
  375 bars + OI each. GEX-lite table produced for the 3 days (walls, floor
  dissolution, squeeze paths) — matched trade moments.
- context/ spec files filled (this unit).
- Gamma Stage 2 (2026-07-20): gamma.py (BS price/vega/gamma, IV Newton+
  bisection, dealer-signed gex_profile — pure math, stdlib); dhan_fetch.py
  `chain` command (direct REST oi:true, 5 strikes x CE/PE + FUT ->
  data/chain_2026-07-17.json, 375 bars each, 24200 PE peak 24,435,645
  @13:01 = exact match vs prior validation); gex_run.py (Stage-1
  session-cumulative writer rule per strike/side, IV solved per 5 min +
  interpolation -> data/gex_2026-07-17.json); server.py /api/gex route
  (needs restart to serve); ui/app.js WALL/FLIP cyan ladder rungs (Jul 17
  only). Gates: BS round-trip 0.0000% err, gamma peaks ATM; engine replay
  byte-identical to replay_gamma3.txt; analyze() OK. Jul 17 GEX read:
  IVs 0.046-0.152; PE walls 24000-24200 writer-built (w +0.9..1.0, dealer
  long gamma, +GEX) = the 24200 defense; CE 24300/24400 BUYER-built
  (w -0.9..-1.0, dealer short gamma, -GEX) = squeeze fuel above — the
  14:15 squeeze ran through 24300 to 24365 with no dealer-long call wall
  to stop it; cumulative GEX never crossed zero (net +30-50k all day) so
  flip_px None — pin-regime day at the index level, amplification only
  above 24200. By 14:30 24300 flipped +GEX (put writers migrated up) =
  the late pin near 24300.

## In Progress

- (none — gamma layer COMPLETE + regime banner COMPLETE. Next: backtesting.)

## Regime banner / context brain (2026-07-20)

- engine.Session.context(): per-bar `ctx` JSON block (additive; zero new
  printed lines; base events 0 lost) — verdict (GO/READY/WAIT/STAND
  ASIDE/CAUTION + why), breadth (cross-book votes: z, CE prem, PE prem
  inverted, MM regime lean → STRONG/LEAN BULL/BEAR/MIXED), narration line
  (state age, 30m range pts + percentile, vol % of day avg, % inside ±1σ,
  MM regime + age), delta radar `flips[]` (15-min changes: writer scores
  ±0.15, OI flow sign flips, bandwidth ±20 pctile, VWAP side cross).
- ui: #ctxBar at top (verdict chip / breadth / mono line / Δ chips).
- Verified Fri 13:45: "WAIT · LEAN BEAR · COILING 3m · 30m range 34 pts
  (p22) · vol 30% · 100% inside ±1σ · MM FLOOR 195m · Δ bands compressing
  46→23". Fri 11:30 reads "STAND ASIDE · STRONG BULL" (chop + floor = the
  don't-trade-but-don't-short answer).

## Code-review pass (2026-07-20) — 4 findings, all fixed

1. CRITICAL — gex_run iv_track interpolated toward FUTURE solves (causality
   violation). Fixed: forward-hold only; None before first solve. Effect:
   IV band tightened to 0.104–0.148 (lookahead had produced 0.046 lows).
2. HIGH — GammaLayer oi0/px0 captured at bar 15 (WARMUP gate), not the true
   open; diverged from gex_run's rule. Fixed: gamma.update runs from bar 0
   (events still maturity-gated). Regression: base events still 0 lost.
3. HIGH — gex_run writer_scores crashed on strikes with no quote at open.
   Fixed: first non-None seed, 0.0 scores before it.
4. MEDIUM — gamma.py used equity-style BS drift while claiming futures
   pricing. Fixed: proper Black-76 (no drift in d1, both legs discounted).
   Round-trip 0.00000%, gamma peaks ATM.
Post-fix GEX story unchanged in substance: put floor walls 24100/24200,
gex_total +29k..+50k all day (net-pinned, amplification above), squeeze ran
to 24365 with no dealer-long call wall in its path.

## Trap + momentum lifecycle rebuild (2026-07-20, live day)

- engine.py: emit() gains structured `data` payloads (events JSON additive);
  TRAP lifecycle all-session — TRAP-SETTING (>=2 distinct tells within 25m at
  the extreme: divergence / absorption / writers / opposite-spring) and
  TRAP-SPRUNG (close back through the extreme-maker bar); momentum setup
  lifecycle (LOADING/ARMED -> FIRED on matching ignition, INVALIDATED on
  close through spring-time session extreme -> SPRING-FAIL event, EXPIRED
  at 45m) exported per-bar as `setup`. armed_until untouched (base STATE
  machine cannot shift). live.py suppresses CARRY before 15:25.
- ui/app.js: trap radar + momentum card render purely from event.data /
  bar.setup — ALL regex parsing removed from both heroes; STORED ENERGY
  (was a mislabeled OI rank) replaced by honest COMPRESSION + SPRING
  INTENSITY meters; MM regime shown on trap card (display-only fusion).
- Gate: 0 base lines lost, 16 added (all new kinds). Validation: Fri ARMED
  13:50 R1 -> FIRED 14:15; Fri BEAR TRAP SPRUNG 13:54 (21m before squeeze);
  Thu BULL TRAP SPRUNG 10:33 (16m before -165pt ARMED move); Wed SPRUNG
  11:06/11:22 pre-waterfall. LIVE Jul 20: 10:19 bearish spring correctly
  SPRING-FAILed 10:31 (the stale-card bug caught on screen), BULL TRAP
  SETTING 10:17 -> SPRUNG 10:20; browser-verified at 10:20/10:25/10:33.

## Episode brain + THE READ (2026-07-20 afternoon, live day)

- engine.py: note_detonation() leg tracker (anchored at recent swing — a
  release fires AT the extreme, so anchoring there measured zero legs);
  episode phases RUNNING/STALLING/SPENT with hysteresis (0.2/0.3 up,
  0.55 to SPENT, SPENT terminal per leg); TRAP UNWINDING + FIGHT AT <lvl>
  episodes; event-born structure marks (absorptions, sprung traps, flipped
  pivots, gamma walls) -> floor/cap box + location quality; playbook
  (if-then trigger strings); verdict SPENT override. All ctx-JSON only —
  gate 0 lost / 0 added, twice.
- ui: #readPanel "THE READ" (episode headline / box+location / play chips),
  TODAY SO FAR briefing (open vs P, beats, range, day character), sticky
  100-grid ATM in live.py (0.6-step + 5-refresh hysteresis), book tiles
  show actual contract + expiry.
- Live validation Jul 20: 12:48 release -> 12:52 "MOVE SPENT 88% retraced
  — don't chase" (the exact read the operator had to get from chat before);
  13:14 UP leg to 24250 tracked RUNNING with trap-sprung floor at 24235.

## OI-PEAK-LAG + DATA tab (2026-07-20 evening)

- OI-PEAK-LAG event: losing-side book sets session OI peak AFTER a price
  extreme then starts a sustained unwind (2 consecutive negative slopes,
  ≤45m window, one-shot per extreme) → "reversal fuel"; feeds trap voter.
  Gate: base grammar 0 lost; unit's own TRAP-* lines re-timed EARLIER
  (Wed bear-trap call 10:41→09:55). Fired 3x live Jul 20 (10:08/11:06/
  14:19); the textbook 12:57 case is masked by Dhan OI lag (TV-export
  data catches it ~13:06) → backtest question: OI truth source.
- GammaLayer solves IV (Black-76, every 5m, forward-held) → gamma.iv_ce/
  iv_pe in JSON. Gate 0/0.
- DATA view (ui): TAPE/DATA header toggle; top bar IV/GAMMA/MM THINKING/
  EXPECTED VIEW; 8 clickable widgets with PE↔CE lean + confidence and
  evidence tables (OI episode ledger classified writer/buyer, build map
  avg prices, volume, vwap/bands, box, setup, traps). Scrub-aware, pure
  client-side composition.
- Docs: context/mental-map.md (takeover map) + context/
  logic-plain-english.md (every rule in words) created; keep both
  current — update them with every unit, same discipline as this file.
- Sticky strike migrated 24200→24300 after the close (FUT settled 24269)
  — tool already on tomorrow's likely expiry battlefield.
- Latest regression baseline: replay_iv.txt.

## Backtest phase — first pass (2026-07-20 night)

- Data access SOLVED: Dhan `expired_options_data` (/charts/rollingoption)
  gives 5yr of 1-min ATM option history w/ OI+IV+spot. Earlier "can't fetch"
  was two bugs: toDate is EXCLUSIVE (I sent from==to = empty range) and data
  nests at data.data.ce/pe. Cached 24 FUT days (Jun10-Jul14) + 27 opt days
  (Jun10-Jul17) in data/backtest/. Token-independent from here.
- LIMITATION SOLVED (Dhan-only, no TV needed): rolling-ATM fragmentation
  fixed by pulling a BAND of ATM-relative offsets (ATM-7..ATM+7) and
  stitching ONE fixed strike (100-grid ATM@open) across whichever offset
  holds it each minute → clean fixed-contract OI, 375/375 coverage, 0
  strike-hops. Re-cached all 27 days this way. (Operator has NO TV/Kite
  historical exports — weekly options expire; Dhan is the only source.)
- backtest.py: rebuilds indicators like live.py, runs UNMODIFIED engine,
  scores forward outcome in R = median 15-min rolling range, +1R target vs
  -1R stop, 45m window.
- CLEAN-OI results (23 days, 110 signals, 0 hops) — the trustworthy run:
    ARMED 75% winrate(decided) 6W/2L/12open, n=20 — KEEPER. Held identical
      across fragmented AND clean runs → robust real edge (still n=20,
      wants more days for significance).
    CARRY 6/13 = 46% — MIRAGE. Prior 8/9=89% was small-sample luck on
      FRAGMENTED OI; clean fixed-strike OI + more samples → coin flip.
      NOT an edge. (Lesson: never trust a 9-sample result.)
    TRAP-FADE 47% (20W/23L, n=69) — improved from 40% w/ clean OI but STILL
      sub-50 → part data, part LOGIC. Mechanical 45m fade ≈ coin flip.
      Needs rework, not just better data.
    SPRING 45%, SPENT 53% — coin flips as standalone mechanical entries.
    Gamma agree/fight n=27 (3 agree / 24 fight) — inconclusive; note most
      directional signals FIGHT the MM regime (they're counter-trend fades)
      → agree/fight framing may be wrong test for these signals.
    48/110 signals resolve "open" (neither +1R nor -1R in 45m) = they
      precede CHOP as often as moves. Blind-entry scoring is a harsh test
      for what are CONTEXT signals.
- KEY INSIGHT: as blind mechanical entries most signals are coin-flips; the
  tool's value is telling you WHEN NOT to trade. Next backtest should score
  CONDITIONALLY — only signals where verdict=GO/READY, or filtered by
  episode/box — to test the filtering, not the raw trigger.
- Next: (a) conditional scoring (verdict/regime-filtered), (b) more unseen
  days for ARMED significance (Dhan 5yr available), (c) rework TRAP-FADE,
  (d) tier signals by measured edge + surface as UI confidence.

## BAND-REVERSAL prototype + gamma-sign split (2026-07-20 night)

- band_backtest.py (standalone, no engine change): fades FUT ±2σ tags on the
  23 unseen days, scores +1R/-1R 45m. Findings:
    Naked ±2σ fade: 58% WR, n=90 — BEST base signal found (biggest sample,
      >coin-flip). Location edge is real.
    3D confluence (CE-2σ & PE+2σ): HURT it (47% vs 62% without) — simultaneous
      extremes flag strong TREND, not exhaustion.
    Confidence vote (my ad-hoc gamma/OI/vol/trap): did NOT discriminate
      (57% high vs 58% skip). Wrong operationalization.
    Management: VWAP-target w/ tight band-stop only 30% — band tag is a ~1R
      SCALP, not a ride-to-VWAP.
- Gamma-sign split (operator's key insight: +gamma→fade, -gamma→continuation):
    by net writer score: -writer (<-0.3, neg gamma) → FADE 33% / CONTINUATION
      67% — EXACTLY the hypothesis. BUT n=4 (3 decided) — cannot confirm.
    +writer/mid → fade wins (55%/64%). 
    by regime label: fade won in BOTH pos & AMPLIFIED (59%/59%) — the engine's
      AMPLIFIED regime is NOT a clean neg-gamma proxy; net-writer-score is
      cleaner. Possible engine refinement: lean regime on net writer sign.
  ROOT ISSUE: these 23 days (June, rangebound) are mostly POSITIVE gamma —
  only 4 band-tags in clear negative gamma. Sample too pos-gamma-heavy to
  validate the fade-vs-continuation switch. NEED more days, esp. trend/
  expansion/neg-gamma days (the Jun-15-style rip). That's the unlock.
- EXPANDED to 55 days / 219 tags (cached Apr-Jul; FUT 61093 only liquid back
  to ~late Apr so early-Apr opt has no FUT match). Re-run findings:
    Naked ±2σ fade: 56% WR n=219 — ROBUST core edge (was 58%@90). Build it.
    3D confluence: robustly HURTS (52% vs 58% without, n=74) — drop it;
      simultaneous extremes = strong move, not exhaustion.
    Ad-hoc confidence vote: doesn't discriminate (57% vs 56%) — drop/rethink.
    GAMMA SIGN (operator's Q): net writer < -0.3 (neg gamma) → FADE 25% /
      CONTINUATION 75% — EXACTLY the hypothesis, and strengthened from n=4
      to n=7. BUT neg-gamma-at-extreme is RARE (7/219 = 3%): can't prove
      statistically, functions as a high-value VETO ("don't fade into neg
      gamma") not a frequent signal. +writer/mid → fade 55-59%.
    Regime LABEL (AMPLIFIED) is NOT a gamma-sign proxy (fade won 58% in it,
      n=158) — net-writer-score is the clean measure. ENGINE REFINEMENT:
      lean regime classification on net writer sign, not the current rule.
    Deep 3σ tags: 6W/0L (n=7) — hint at stronger fade; watch as data grows.
    VWAP-target mgmt: 26% — confirmed the tag is a ~1R SCALP not a VWAP ride.
- Design the data supports for BAND-REVERSAL: fade ±2σ (scalp ~1R) + VETO
  when net writer strongly negative + (tentative) deep-3σ higher conviction;
  NO 3D-confluence gate, NO ad-hoc vote.

## Expression backtest — buyer vs seller (2026-07-20 late night)

- expression_backtest.py: at each of the 219 ±2σ tags (54 days), priced all
  three expressions with REAL option closes + per-minute IV from cache.
- OPERATOR'S THESIS PROVEN — same fade, different P&L by expression:
    FUT scalp:  55% WR, +2.0 pts avg
    BUY option: 49% WR, ~0% of premium — the fade's edge DISAPPEARS for the
      buyer; in the 63 timeout/chop tags buyer is 32% WR, -8.1% of premium
      (theta+IV bleed). Buying the extreme is one-sided-skewed, as operator
      said.
    SELL opposite option: 58% WR, +1.51 pts; wins the chop bucket 63% WR
      (+2.0 pts) — seller is PAID to wait; measured IV crush -0.67 vol pts
      avg (sold at fear, exits calmer).
- Edge concentrators (multiplicative):
    IV rank of sold option >=0.7 → seller +3.00 pts (crush -1.11) vs +0.41
      below; pumped IV at the extreme IS the seller's entry.
    Days-to-expiry 0-1 (Mon/Tue, weekly Tue): seller 65% WR +4.71 pts,
      crush -1.35. FAR days (4-6 dte): ALL expressions ~flat/negative —
      the band-fade edge is a NEAR-EXPIRY phenomenon. Major filter.
    Neg gamma (netw<-0.3): everything dies (FUT -16.8 avg, buyer -6.6%/prem)
      — veto reconfirmed across expressions.
- Seller asymmetry noted honestly: avg win +24.7 vs avg loss -28.1 pts
  (short gamma cuts both ways); higher WR + chop income still nets better.
- BEST STACK (design target): ±2σ tag + 0-1 dte + netw>-0.3 + sold-side IV
  rank high → SELL the inflated side, ~45m scalp horizon.
- Plan file (approved direction, build pending): BAND-REVERSAL/BAND-BREAK
  engine events w/ netw veto + expression line; AMPLIFIED regime fix (lean
  on netw sign); UI cards; see
  ~/.claude/plans/i-want-you-to-melodic-eclipse.md

## BAND-REVERSAL build (2026-07-20, end of session)

- engine.py: BAND-REVERSAL / BAND-BREAK events per plan (±2σ tag, re-arm
  inside ±1σ, deep-3σ conviction, netw<-0.3 veto → BREAK, seller expression
  + IV rank + expiry note in msg/data); GammaLayer IV percentile ranks
  (iv_r); AMPLIFIED now requires netw<0 (55-day finding); playbook band chip
  (20m). Gate vs replay_iv.txt: BASE 0 LOST; 7 GAMMA-PIN re-timed (expected
  from AMPLIFIED fix); 8 BAND-REVERSAL lines added. New baseline:
  replay_band.txt. Smoke: analyze() JSON carries data payloads + playbook
  chip ("FADE the 24336 band tag — scalp ~1R down; seller: sell CE").
- ui/app.js: BAND-* in EVC/LOUD/STORY_KINDS.
- NOT yet verified live (market closed; token expires ~05:45 IST) — next
  session: regenerate token at web.dhan.co, `python server.py live`, confirm
  BAND cards render; watch first live band tag vs the backtest expectations.
- Known nuance (documented in logic file): netw veto reads dealer sign, not
  writer squeezes — Fri 14:15 fired REVERSAL (netw +0.79) during the
  trapped-writer squeeze; SQUEEZE-RISK/RELEASE remain the companion check.

## BAND-REVERSAL confidence tier (2026-07-20, end)

- engine.py band block: HIGH/MED/LOW tier from expression-backtest edge
  concentrators — score = (+2 if t_d<=1.5 else -2 if t_d>=4 else 0) +
  (1 if IV rank>=0.7) + (1 if deep 3σ); HIGH>=3/MED>=1/LOW<=0. Advisory,
  no suppression (operator choice). tier in message "[HIGH] …" + data
  payload + playbook chip. band_last tuple now 5-wide (…, tier).
- ui/app.js: playChip() parses "[TIER]" prefix → coloured badge (BAND_TIER
  green/amber/slate); style.css .plays .tier. Verified in browser: Jul 17
  14:16 chip shows slate LOW badge + "FADE the 24336 …".
- CLARIFICATION: all 3 replay days are Wed-Fri = 4-6 dte from Jul 21 expiry
  → correctly read LOW (backtest: far-from-expiry edge is flat). HIGH needs
  the Mon/Tue final-days, which only appear LIVE. Plan's "Fri=HIGH" note was
  my miscalc; implementation is correct & consistent with data.
- Gate: base grammar 0 lost; 8 BAND-REVERSAL lines re-texted (tier prefix
  only). Baseline now replay_band2.txt.
- Live-verify pending next session (token expired): Mon/Tue tags should show
  MED/HIGH badges — tomorrow (expiry, 0 dte) is the ideal first test.

## Cross-instrument validation — BankNifty + Sensex (2026-07-21)

- SELF-CALIBRATION INVARIANT CONFIRMED: engine ran UNCHANGED on BankNifty
  (fut 61088, ~54k, NSE_FNO) and Sensex (fut 1144507, ~80k, BSE_FNO) — no
  crashes, sensible band tags / gamma / writer scores at price levels 2-3×
  Nifty. Dhan expired_options_data works for both (BNF WEEK NSE_FNO, Sensex
  WEEK BSE_FNO); fixed-strike offset-band reconstruction reused, 100-grid.
- Band-fade edge (9 days each, PRELIMINARY small n):
    SENSEX  61% WR (n23) — edge generalizes, strong
    NIFTY   56% (55-day baseline)
    BANKNIFTY 50% (n20) — coin flip; plausibly its higher trendiness (bands
      break more = continuation) weakens mean-reversion. Needs more days.
  Neg-gamma buckets ~empty (BNF 0, Sensex 1) — rare as always at 9 days.
- READ: the SETUP detection generalizes (percentile self-calibration adapts);
  whether the fade PAYS is an instrument-character property that varies
  (Sensex mean-reverts well, BankNifty less so) — argues for per-instrument
  edge/tier calibration once enough days per instrument exist. Not cached to
  disk (ran in-memory); expand to 30+ days/instrument to firm up magnitude.

## Cross-instrument FULL backtest — 19 days each (cross_instrument.py)

- BANKNIFTY (19d, 71 tags): naked fade WR 64% (n47; earlier 50% was 9-day
  noise) | +gamma 64%, neg-gamma n0 | SELL 69% +13.4 pts vs BUY 61% +6.1 |
  dte near(0-1) SELL +20.3 vs far +8.6 (near-expiry edge HOLDS) | IV-rank
  filter neutral (+12.7 vs +13.4).
- SENSEX (19d, 62 tags): naked fade 58% (n50) | +gamma 60% / NEG gamma 40%
  (n5) — GAMMA SWITCH CONFIRMED on a new instrument | SELL 60% +9.7 vs BUY
  48% -4.9 (buyer LOSES) | dte near +6.5 vs far +11.2 (INVERTED) | IV-rank
  >=0.7 SELL -11.0 vs all +9.7 (INVERTED).
- CONCLUSIONS:
  1. Core band-fade edge GENERALIZES: all three win (Nifty 56 / BNF 64 /
     Sensex 58). Self-calibration invariant fully validated at scale.
  2. SELLER > BUYER expression HOLDS on all three (buyer even loses on
     Sensex). The operator's one-sidedness point is universal.
  3. Gamma-sign switch CONFIRMED on Sensex (neg-gamma fade 40% vs 60%).
  4. SECONDARY FILTERS (near-expiry, IV-rank) are NIFTY-SPECIFIC — Sensex
     inverts both. Partly an artifact: dte metric assumes Tue expiry (Nifty);
     Sensex is BSE with a different expiry day, so its dte buckets are
     mislabeled. => the confidence TIER (bakes in Nifty dte+IV) must NOT be
     applied to BankNifty/Sensex without per-instrument recalibration + a
     correct per-instrument expiry-day. Live tool is Nifty-only today; safe.
- Caveats: BankNifty weeklies exist in this dataset; Sensex options thinner
  (IV noisier); 19 days each still modest; Sensex dte needs its real expiry
  weekday before trusting near/far splits.

## Cross-index confluence test (cross_confluence.py, 2026-07-21)

- Q: at a Nifty ±2σ tag, does BankNifty+Sensex moving the same way with
  volume predict continuation (don't fade) vs idiosyncratic (fade)?
- 26 days, 103 tags (73 decided). Fade WR by # of other indices aligned:
    0 aligned (Nifty ALONE): 67% fade  ← idiosyncratic extreme reverts best
    1 aligned:               48% fade  (worst; likely noise, n23)
    2 aligned (ALL 3 + vol): 58% fade  = baseline, NOT worse
    baseline: 58%
- VERDICT: half the hypothesis holds. Nifty-ALONE extreme = stronger fade
  (67% vs 58%) → usable positive filter ("divergence confirms the fade").
  But ALL-3-ALIGNED does NOT predict continuation at the band (58% = base)
  — at the 45m scalp horizon mean-reversion dominates regardless of breadth.
- The operator's "real move = all 3 + volume" intuition is about MOMENTUM/
  breakout, a different context than mean-reverting band extremes. Natural
  next test: does all-3-aligned+volume predict SUSTAINED directional moves
  (level breaks / VWAP thrusts), and at a longer horizon than 45m.
- Caveats: 73 decided, ~24/bucket, non-monotonic (noise); longer-horizon
  and momentum-context tests not yet run.

## Coil→breakout confluence + CONTRACT MISMATCH (cross_breakout.py, 2026-07-21)

- Tested "coil all day then all 3 break together" (June-15 archetype) as a
  MOMENTUM confirmer: thrust out of compression, does it RUN (+1.5R/-1R, 60m)?
  26 days, 16 thrust events (TINY): Nifty-alone 0% run (n1), 1-aligned 25%
  (n4), ALL-3+vol 50% (n6), baseline 36%. Monotonic → supports the intuition
  but far underpowered.
- CRITICAL FINDING — WRONG FUTURES CONTRACT: Jun 15 detector found 0 thrusts
  because data/backtest uses 61093 (JULY future) for ALL dates; on Jun 15 the
  front month the operator charts was the JUNE future. July (back-month) sat
  FLAT (+17pts) while June front-month broke out. So: (a) breakout/June tests
  invalid on this cache; (b) caveat on June-heavy band results (structure ok,
  volume/levels back-month). FIX before more breakout work: resolve
  front-month future per date via Dhan expired-futures feed + a MULTI-DAY
  compression detector (the coil is often the PRIOR day → next-day gap/run,
  which the intraday detector can't see). Logged in mental-map caveats.

## Jul 15 second-half down move — case study (2026-07-21, clean: July=front)

- Move: 24189 (12:00) → 24012 low (~13:02, -0.7%), then reverted to pivot
  P 24064 and CHOPPED there to close. "Second-half down move" = fast drop to
  1pm, then dead consolidation.
- CROSS-INDEX CONFLUENCE CONFIRMED: all 3 down together near-identically
  (13:00: NIFTY -0.52% / BNF -0.43% / SENSEX -0.52%) — a real market move,
  not idiosyncratic. Engine's IGNITION 12:56 (FUT/CE/PE vol 1.00/0.98/1.00)
  independently flagged the same instant.
- BAND-BREAK VETO WORKED LIVE: 12:55 "-2σ tag at 24099 in NEGATIVE gamma
  (netw -0.38) — do NOT fade; hedging chases" → price continued down to the
  12:56 CLIMAX low. The neg-gamma continuation call was correct; a fade would
  have been run over. Then TRAP-SPRUNG + FLIP-TEST P marked exhaustion → chop.
- Honest: base layer fired premature bullish springs 12:35-39, invalidated by
  SPRING-FAIL 12:53; the gamma-aware BAND-BREAK was the right read. Validates
  both the cross-index confluence idea AND the BAND-BREAK veto on a real move.

## DATA tab → full option-chain analyser (2026-07-21)

- OPERATOR DIRECTION: rebuild the DATA tab on Dhan's whole option chain
  (option_chain REST: all strikes w/ OI, oi_change, IV, greeks, top bid/ask)
  — fixes the one-strike gamma/squeeze blind spot properly.
- chain_metrics.py (pure, stdlib, mirrors gamma.py; engine untouched):
  per-strike writer scores ce_w/pe_w (1-min classification buckets — 5s
  deltas are noise; same dOI-vs-premium grammar as GammaLayer), full-chain
  dealer GEX per strike + gamma.gex_profile flip/walls/total, max pain, PCR
  (OI+vol), ATM IV + fixed-offset skew, CHAIN SQUEEZE score (writer-dominant
  books underwater × unwind velocity × premium velocity, receipts per
  strike), session series.
- chain_live.py: ChainPoller daemon thread — expiry auto-resolved via
  expiry_list (no hardcoded expiry), token from env DHAN_TOKEN → .dhan_token
  w/ JWT exp check surfaced as UI error (no crash), polls option_chain every
  5s (limit 1/3s), normalizes ATM±1500, persists every live snapshot to
  data/chain/chain_<date>.jsonl (each live day becomes replayable chain
  history), --mock mode replays data/chain_sample.jsonl (make_chain_fixture:
  deterministic Black-76-priced 90-min calm→rally→squeeze scenario).
- server.py: /api/chain endpoint (poller box; 404 when no poller → UI
  legacy fallback); --mock-chain flag works in live AND replay modes;
  /api/gex kept (Jul-17 replay ladder rungs unaffected).
- ui: DATA tab rebuilt as chain analyser — top strip (SPOT/PCR/MAX PAIN/GEX
  regime/FLIP/ATM IV+skew/SQUEEZE), CE|strike|PE ladder w/ OI bars tinted by
  writer score, ΔOI chips, per-strike dealer-GEX diverging bars, SPOT+FLIP
  overlay lines, MP/WALL strike chips, PAIN MAP receipts panel, 4 session
  sparklines (PCR/GEX/spot·flip·maxpain/squeeze). 5s poll only while DATA
  tab active; keyed per-strike row patching (no innerHTML teardown); legacy
  widgets remain as fallback for replay days without chain data. All
  analytics server-side ("UI renders, engine decides" restored for chain).
- GATES: unit sanity (test_chain_metrics.py) — max pain=ATM symmetric, GEX
  flip+walls on constructed profile, writer signs ±, squeeze calm 0.00 →
  rally 1.00 UP on fixture, ALL PASS; engine replay BYTE-IDENTICAL vs
  replay_band2.txt (engine untouched); analyze JSON valid; mock end-to-end
  in browser (tapemap-mock, port 8766): ladder/top/pain/sparklines render,
  squeeze fired 100% ▲ "CE writers 24400–24500 underwater 0.7M trapped,
  315k unwound/5m" w/ WALL chip + cyan writer tint verified in DOM.
- LIVE-VERIFIED (2026-07-21 10:49 IST, expiry day, fresh token): expiry
  auto-resolved to 2026-07-21 (0DTE); 60 strikes; spot 24178. FIELD FIX:
  live chain API ships `previous_oi`, NOT `oi_change` — normalize computes
  oi_chg = oi − previous_oi (first run had all-zero seeds/walls; obvious
  once seen). Post-fix read is textbook expiry pin: max pain 24200 = ATM,
  PCR 0.75, CE books writer-built (w +1.0, premiums below day avg) / PE
  books buyer-built, walls 24150/24250 bracketing spot, flip 23931 (−245
  pts), per-strike GEX negative below 24150 (amplification zone) positive
  above (pin zone), squeeze honest 2% (11.9M ITM CE-writer OI flagged but
  not unwinding). Browser DOM verified: MP/WALL chips, SPOT@24176 + FLIP
  lines, pain receipts, sparklines. Snapshots accumulating in
  data/chain/chain_2026-07-21.jsonl. Server: `tapemap-live` launch config,
  port 8767 (8765 held by a stale pre-change process).

## TAPE-view critique refinements (2026-07-21, expiry-day live session)

Operator asked for a 20yr-trader critique of how the TAPE view read the live
0DTE session, then to implement the fixes. All engine changes are ctx-JSON /
display-only or scoped away from BAND events — **band_backtest stayed 219 tags
/ 56% WR (w87 l69 o63) through every change**; replay baseline replay_band2.txt
unchanged. Each item verified on the 54-day cache and live on port 8767.

- **Volatility strip** (engine ctx + `#volStrip`): added ctx fields `z`,
  `bw_r`, `iv_ce/iv_pe`, `ivr_ce/ivr_pe` (all already computed in GammaLayer).
  New UI strip under MM strip: realized σ, 30m range+pctile, band-width pctile
  (compress/expand), % inside ±1σ, ATM IV+rank, fused COILED/EXPANDED/NORMAL
  tag. NOTE: the context "vol N% of day" is VOLUME, not volatility.
- **P0 — verdict gated on range + pin chip.** context() verdict: a trend
  label is no longer auto-GO. `compressed = rng_r<0.30`; GO requires
  `not compressed and regime!=PINNED`; compressed trend → `WAIT "trend
  stalled — range pNN, compression not continuation"`. Verified 54 days /
  20,225 ctx bars: **GO-during-compression = 0** (was the 14:21 bug),
  WAIT-stalled fires 3,308×. Added ctx `pin` {k,dist,regime} (from
  `self.gamma.k`) → `#pinChip` on #ctxBar ("◎ PIN 24200 · px −20"; hidden
  when no pin). Puts the pin magnet on TAPE, not just DATA.
- **Chop-aware BREAK suppression.** engine `_cross_ev()`: first 2 crossings of
  a pivot in 30m emit BREAK; beyond → single `CHOP "<lvl> chopping — N
  crossings in Mm, breaks unreliable"` (reuses level_hits). Verified: **>2
  BREAKs/level/30m = 0**, 120 CHOP across 42 days. `CHOP:#c9a24a` in EVC.
  Intentionally changes the BREAK stream (not a regression); BAND tags 219 held.
- **Expiry master-regime.** ctx `t_exp` = `self.gamma.t` (real DTE from
  live.py's expiry timestamp — a Monday reads ~4, banner stays hidden).
  `#expiryBar` magenta top banner shows ONLY when `t_exp<=1.0` (0DTE badge
  `<=0.5`): pin + ATM IV + "crushed" (IVr≤25) + "SELL PREMIUM · fade to pin ·
  trend labels unreliable — theta rules". Live: "◉ 0DTE · PIN 24200 · px −15 ·
  ATM IV 3.1% · p5 crushed".
- **Event-spam cooldown.** emit() merges recurring TRAP/DIVERGENCE with the
  same template (digits→'#') within 20m into a `×N` counter on the prior line.
  Scoped to those 2 kinds (BAND/gamma untouched). Verified: 516 dup rows
  absorbed / 54 days (~62% fewer TRAP/DIV rows). ×N refreshes on feed
  re-render; live never shows dup ROWS regardless.
- **CARRY expiry bug (operator-caught).** carry_verdict() projected option-OI
  retention as "→ BEARISH carry into next session" — invalid on expiry (weekly
  CE/PE SETTLE 15:30). Now when `self.gamma.t<=0.5`: "EXPIRY SETTLEMENT —
  <strike> CE/PE expire at close [pinned / closed ±N vs strike]; no option OI
  carries overnight. Book resets next session on a fresh weekly." Non-expiry
  path unchanged. Downstream degrade cleanly (backtest scorer skips; footer
  has no `→`). AUDIT: CARRY was the ONLY overnight read; all others intraday.
  Cosmetic-stale legend comment left at engine.py:24.
- **UI infra fixes.** (1) Narrative-log scroll bug: `main` grid row auto-sized
  to content so no column scrolled — fixed `main{grid-template-rows:minmax(0,
  1fr)}` + `min-height:0` on #railLog/#feed; feed scrolls + auto-pins to
  latest (data was never missing). (2) "TODAY SO FAR" beats clipped (CSS
  nowrap + JS `head.slice(0,64)`) — now wrap w/ hanging indent, full head.
  (3) Cache-busting: `style.css?v=6`, `app.js?v=7` — bump on EVERY ui edit
  (browser was serving stale files).
- Verification scripts in scratchpad (p0_verify / chop_verify / merge_verify)
  if numbers need re-confirming. Live server: tapemap-live, port 8767.

## Next Up

1. ~~Stage 1 GammaLayer + regression diff~~ DONE — 0 base lines lost; 36
   gamma lines added. Regime vocabulary evolved during validation:
   PINNED / FLOOR / CEILING / AMPLIFIED-UP / AMPLIFIED-DOWN / NEUTRAL
   (one-sided walls only dampen moves INTO them — Wed 12:37 CEILING with
   "downside NOT supported" 19 min before the waterfall validated this).
   Writer score = session-cumulative (doi vs open, premium direction vs
   open, magnitude / session's own peak build) after the 10-min EWMA
   failed validation (Fri wPE read −0.02 during a 21M writer campaign).
2. ~~UI MM strip~~ DONE — FLOOR verified on screen Fri 13:52; hero cards
   unchanged; SQUEEZE-RELEASE added to LOUD; cyan = gamma layer.
3. ~~Stage 2: gamma.py (BS IV + gamma + GEX), chain fetcher, FLIP/WALL
   ladder rungs; validate on Jul 17~~ DONE (see Completed; restart
   server.py to activate /api/gex).
4. Code-review agent pass over engine.py + gamma.py. DONE.
5. Backtesting phase. DONE (band-fade validated; see later sections).

## CURRENT NEXT UP (2026-07-21) — supersedes the list above

1. LIVE-VERIFY BAND-REVERSAL/BAND-BREAK + confidence tier on the next Nifty
   session. Token expired ~05:45 — regenerate at web.dhan.co, `python
   server.py live`. Tomorrow/today is expiry (0 dte) = ideal HIGH-tier test.
2. FIX FUTURES CONTRACT (blocks breakout + June work): resolve front-month
   future per date via Dhan expired-futures feed; re-cache pre-late-Jun FUT.
3. Cross-index confluence as a MOMENTUM confirmer — redo after #2 with a
   MULTI-DAY coil detector (June-15 archetype). Directionally promising
   (all-3 breakouts run 50% vs 36%) but underpowered + wrong contract so far.
4. Per-instrument tier/edge calibration for BankNifty + Sensex (core edge +
   seller expression generalize; the Nifty-calibrated tier does NOT — Sensex
   inverts dte/IV). Needs each instrument's real expiry weekday.
5. More unseen days to fatten thin buckets (neg-gamma band tags, deep-3σ).
6. Known debt: UI still regex-parses some engine prose (non-hero); trap
   confidence heuristics; live OI lag vs clean history.

## Stage-1 validation record (2026-07-20)

- Fri: FLOOR 09:58 (PE 18.6M, FUT 1pt from strike) = day bias 43 min in;
  SQUEEZE-RISK 13:52 (PE 20.9M, unwind accel 13 min); RELEASE UP 14:15.
- Wed: CEILING 12:37 (wPE −0.88, "downside NOT supported") → waterfall;
  RELEASE DOWN 12:56. Thu: FLOOR/CEILING alternation (pin day), RISK
  cluster 11:23–12:41 before the 13:40 low.
- Known imperfection: Thu 10:49/10:59 RELEASE UP fired on the 11:00 pop
  that immediately topped — releases mark thrusts, not continuation; base
  layer (ARMED bearish 10:49) judged continuation correctly. Layers agree
  to disagree by design.

## Open Questions

- Jul 17 24200 CE final close: Dhan ~204 vs TradingView 205.75 (PE matched
  exactly). Investigate last-bar semantics before backtesting.
- ~~Dealer-sign heuristic for GEX~~ validated on Jul 17: writer-signed GEX
  put the pin below 24200 and the squeeze fuel above it (the naive
  always-short convention would have called 24300 a resistance wall — it
  wasn't; price ran through it at 14:15). Note: cumulative flip_px was
  None all day (book net long gamma); consider whether a per-strike
  sign-boundary "local flip" (24200/24300 boundary) is the more useful
  display before backtesting.
- Strike auto-discovery (OI concentration) — scheduled with backtest phase;
  currently strike is a CLI parameter.
- Dhan token expires ~daily — operator regenerates; automate the reminder?

## Pine Script port (2026-07-20 night)

- tapemap_bandreversal.pine — TradingView v5 indicator = the VALIDATED
  price-structure core only: session VWAP + ±1/2/3σ bands, ±2σ/3σ fade
  markers (re-arm after returning inside ±1σ), pin-zone shading, ±1R scalp
  lines, prior-day pivots, alertconditions. Deliberately EXCLUDES the OI/
  gamma half (writer scores, gamma veto, squeeze) — Pine cannot get NSE
  option OI, let alone multi-strike chains. Split architecture: Pine on the
  chart = WHERE (extreme printed); TapeMap app = WHETHER (gamma veto).
  Not live-compiled (TV Desktop/CDP absent on this machine — browser TV);
  written to v5 spec, paste into Pine editor. If option OI turns out
  accessible on the user's TV plan, a lightweight OI read could be added.

## Architecture Decisions

- No absolute thresholds; percentile self-calibration (generalizes across
  instruments; the same code must read NIFTY/BANKNIFTY/stocks).
- Causal/expanding features so replay engine == live engine.
- Gamma layer strictly separate from base signals (operator decision,
  2026-07-20) — enables honest with/without comparison in backtesting.
- UI is render-only; engine emits "HEAD — evidence" strings + structured
  fields (known debt: some UI regex-parsing of prose remains; migrate to
  structured payloads during gamma work).
- Flat-file storage only; no DB.

## Session Notes

- Server: `python server.py` → localhost:8765. Dev preview runs via
  `.claude/launch.json` ("tapemap").
- Regression command: `python engine.py data 24200 > replay_new.txt`, diff
  vs prior output; only intentional new lines allowed.
- `.dhan_token` valid ~24h from 2026-07-20; client id 1111966509.
- GateGuard hook denies first Write/Bash per session/path — state facts,
  retry once.
- Known-good ground truth: Fri ARMED 13:50 → IGNITION 14:15 "FIRES A LIVE
  SPRING" → CLIMAX 14:15–17 → carry BULLISH; Thu ARMED bearish 10:49, carry
  NEUTRAL; Wed PRESS 11:47/12:43 → IGNITION DOWN + PE CLIMAX 12:56, carry
  BEARISH.

## 2026-07-23 — post-review remediation (pushed: robby-glitch/tapemap)

Repo initialized + pushed to private GitHub as a rollback point (ba3c152), then
six phase commits. `.dhan_token` / `.dhan_client` / `data/chain/` gitignored.
Replay console output stayed byte-identical except the intended CARRY lines
(ground truth Jul 15 BEARISH / 16 NEUTRAL / 17 BULLISH preserved). Both test
files green throughout.

- **A Hygiene**: 18 replay_*.txt + 7 orphan UI prototypes → archive/; dead no-op
  loop removed; client id → lazy `_client_id()` (env/.dhan_client).
- **B Engine**: month/year-safe expiry — `load()` returns `(days, years)`,
  `days_to_expiry()`, CLI `engine.py data 24200 2026-07-21` (analyze.py fixed
  too); CARRY writer-aware (retention signed by holder, clamped at 0); true GEX
  flip (spot-revaluation; gex_total/walls unchanged to 1e-9).
- **C Backtest honesty**: causal expanding-median R, stop-first scoring,
  `COST_PTS`/`--cost` net-R, Wilson CI + `!` n<30 flags. Headline: naked fade
  59% WR [CI 50–67], net +0.14R; neg-gamma veto n≈9. IN-SAMPLE hypotheses.
- **D UI**: rAF throttle, keyboard shortcuts, feed+ribbon click-to-seek, status
  banner, localStorage persistence, price ribbon, contrast (--dim #8090a8), ×N
  tooltip. (style v14 / app v18.)
- **D9 Token capture**: POST /api/token (validate→save→hot-reload poller;
  ChainPoller.reload flag), ⟳ TOKEN clipboard button + password paste fallback,
  token never logged/rendered.
- **E Docs**: README honest stats framing + run/secrets; architecture.md.
- **Post**: crash-proof live startup (binds instantly, resolves+builds in the
  background so a stale token can't stop boot; scrip downloaded once for all
  indices); `pollUntilLive` after token capture; start.bat/stop.bat + Desktop
  shortcuts (TapeMap / Stop TapeMap) with ui/tapemap.ico + ui/stop.ico.

Corrections to notes above: replay baselines now live in archive/ (not the
root); REFRESH_S is 15 (not 60); client id is no longer hardcoded (was
1111966509 in source — now env/.dhan_client).
