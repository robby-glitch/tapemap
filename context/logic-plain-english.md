# TapeMap — Every Rule in Plain English

All logic lives in engine.py. This file says what each rule watches, when
it speaks, and why it means what it means. No thresholds below are absolute
prices/sizes — everything is ranked against the session's own history so
the same code reads NIFTY, BANKNIFTY, or a stock.

## Philosophy

Every raw number (volume, range, OI change, bandwidth) is converted to
"where does this sit vs everything seen so far today" (0–1 rank). Events
fire on extreme ranks agreeing across books — never on fixed numbers.

## Per-bar features (class Book)

- vol_r / rng_r — this bar's volume / range ranked vs the day so far.
- z — closes distance from VWAP in units of the 1σ band.
- bw_r — band width rank (low = compressed = energy storing).
- oi_slope — OI change over the last 10 minutes; oi_slope_r ranks |slope|.
- prem_d — option premium change over the same 10 minutes. OI direction
  + premium direction = who is acting: OI↑+prem↓ writers selling;
  OI↑+prem↑ buyers paying; OI↓+prem↑ shorts covering; OI↓+prem↓ longs bailing.

## Base events (the grammar)

- TRAP (opening only, first 20m): option pokes beyond 2σ while BOTH books
  add OI — two-sided writers selling the spike; fade risk.
- CAMPAIGN: one book's OI building at top-decile speed into falling
  premium — writers pressing; PE campaign is bullish, CE campaign bearish.
- BUYER-BUILD: same speed but premium firming — protection being bought;
  opposite bias of a campaign.
- DIVERGENCE: FUT makes a new session extreme but the option that should
  profit can't better its own peak — the move is not being paid for.
- PRESS: both books rotating the same direction ahead of price (one side
  writers adding while the other side's shorts evacuate).
- SPRING: an extreme being disbelieved — the winning side dumps OI at
  top-quartile speed while the losing side adds, price stretched from
  VWAP. Location-gated by the defended strike.
- ARMED: a SPRING landing at a pivot level — trigger defined; window ~45m.
- IGNITION: all three books' volume ranks ≥0.97 with FUT range rank ≥0.9 —
  synchronized detonation. "FIRES A LIVE SPRING" when it matches an armed
  direction.
- CLIMAX: option beyond 3σ + losing-side OI cliff + extreme volume —
  covering climax; usually marks the turn.
- ABSORPTION: extreme volume, no range — someone is swallowing the flow
  at that price ("sellers/buyers hitting a wall").
- BREAK / FLIP-TEST: pivot crossed on a close; retested from the other
  side within 3–45m and holding = level flipped.
- CARRY (close only; suppressed live until 15:25): which book KEPT its
  intraday build overnight → next-day bias. Both books evacuating = no
  conviction carried.

## Trap lifecycle (all session)

- Evidence per side, each kind counted once: divergence, absorption,
  winning-side writers adding at the extreme, opposite-side spring,
  OI-PEAK-LAG. Tells must corroborate within 25 minutes.
- TRAP-SETTING: ≥2 distinct tells while price still near the extreme.
- TRAP-SPRUNG: price closes back through the bar that made the extreme —
  the failed break; late entrants are now trapped (fade their exits).

## OI-PEAK-LAG (late conviction)

The losing side's book sets its session OI PEAK *after* the price extreme,
then starts a sustained unwind (two consecutive negative slopes, within
45m of the extreme). Maximum conviction arriving after the move stopped =
that book is reversal fuel. (Jul 20 ground truth: CE peaked 26.5M nine
minutes after the 24121 low; its forced unwind was the +78pt squeeze.)
Feeds the trap voter as a tell.

## BAND-REVERSAL / BAND-BREAK (the operator's core setup, backtest-validated)

When FUT tags its ±2σ band (re-arms only after closing back inside ±1σ):
- Positive/neutral gamma (net writer score ≥ −0.3): **BAND-REVERSAL** — fade
  armed as a ~1R scalp. Deep ±3σ = high conviction. Message carries the
  seller expression ("sell PE/CE", its IV percentile) and expiry context.
- Negative gamma (net writer < −0.3): **BAND-BREAK** — do NOT fade; dealer
  hedging chases, continuation favored.
Why (54 days / 219 tags): naked fade 55–58% WR; buyer expression of the same
fade is a coin flip (theta+IV bleed in chop, 32% WR / −8% premium in
timeouts); SELLING the inflated opposite side wins 58–65%, collects measured
IV crush, and is paid in chop. Edge concentrates near expiry (0–1 dte: seller
65% WR) and vanishes 4–6 dte; in negative gamma everything dies (fade 25%).
CONFIDENCE TIER (advisory, no suppression — every tag still fires): a
HIGH/MED/LOW grade from the three edge-concentrators the expression backtest
found, scored: +2 if ≤1.5 days to expiry (dominant factor — edge vanishes
4-6 dte), −2 if ≥4 dte; +1 if sold-side IV rank ≥0.7 (pumped); +1 if deep 3σ.
HIGH ≥3, MED ≥1, LOW ≤0. So HIGH needs the near-expiry window; mid-week tags
(and all 3 replay days, which are Wed-Fri = 4-6 dte) read LOW even at high IV.
Shown as a coloured badge on the READ playbook chip (green/amber/slate).

The playbook shows the active band chip for 20 minutes after a tag. Caveat:
the veto reads dealer positioning, not writer squeezes — a trapped-writer
squeeze (positive netw, like Fri 14:15) still fires REVERSAL; check the
SQUEEZE-RISK/RELEASE lamps beside it.

## Momentum setup lifecycle (per-bar `setup` JSON)

LOADING (spring seen) / ARMED (spring at a level) → FIRED (ignition in its
direction within 45m) / INVALIDATED (close through the session extreme it
sprang from → SPRING-FAIL event; card dies on screen) / EXPIRED (45m).
Honest meters: compression = 1 − bandwidth rank; intensity = the dump's
oi_slope rank at spring time.

## States (background regime)

ARMED (spring window live) / TREND-UP/DOWN (≥80% of last hour one side of
VWAP riding outer bands) / COILING (bandwidth rank <0.3) / BALANCE (else).
First 20m = OPENING (bands statistically immature).

## Gamma layer (MM perspective — separate, never touches base signals)

- Writer score per book, session-cumulative: net new OI since open,
  classified by premium direction since open (2% relative floor),
  magnitude vs the session's own largest build → [-1,+1]. +1 = fully
  writer-built, −1 = buyer-built.
- Regimes (bell-weighted by distance to strike, book size vs session peak):
  PINNED (both walls, both dampen), FLOOR (put wall — dips absorbed,
  upside NOT capped), CEILING (call wall — rallies sold, downside NOT
  supported), AMPLIFIED-UP/DOWN (buyer-built book or unwinding writers →
  dealer hedging CHASES price), NEUTRAL.
- SQUEEZE-RISK: big writer book pressed on its pain side with unwind
  accelerating. SQUEEZE-RELEASE: violent unwind + violent premium move —
  trapped-writer covering or short-gamma hedge chase; hedging amplifies.
- IV: Black-76 inversion of each option every 5 minutes, forward-held
  (causal). Stage-2 GEX (gamma.py + gex_run.py): dealer-signed by the
  writer score, NOT the naive always-short convention — validated Jul 17
  where buyer-built 24300 was fuel, not a wall.

## Episode brain (the story between events)

A detonation (IGNITION or SQUEEZE-RELEASE) opens a "leg", anchored at the
recent swing (a release fires AT the extreme). While the leg is <40m old
and ≥3× median bar range: retracement of the leg decides the phase with
hysteresis — RUNNING (<~0.25 given back), STALLING (~half), SPENT (>~0.55,
terminal until a fresh detonation; verdict becomes SPENT "don't chase").
No leg → TRAP UNWINDING (recent sprung trap) → FIGHT AT <level> (≥3
crossings in 35m) → fall back to state.

## Structure map, box, playbook (ctx JSON)

Event-born levels only: absorption prices, sprung-trap refs, flipped
pivots, gamma walls, session extremes. Nearest below = floor, nearest
above = cap → the box + where price sits in it ("mid-box — worst
location"). Playbook = ≤3 if-then strings: fade the cap (invalid on CE
squeeze-risk if it's a wall), break of floor needs vol rank >0.9, ride
hedge flow when AMPLIFIED, don't chase when SPENT.

## Banner (ctx)

- Verdict: GO / READY / WAIT / STAND ASIDE / CAUTION / SPENT + why.
- Breadth: four direction votes (FUT z, CE premium, PE premium inverted,
  MM regime lean) → STRONG/LEAN BULL/BEAR or MIXED.
- Narration line: state age, 30m range pts + its percentile, volume % of
  day, % inside ±1σ, MM regime + age.
- Flips radar (vs 15m ago): writer score ±0.15, OI flow sign flip,
  bandwidth ±20pctile, VWAP side cross — what's changing while price isn't.

## UI composition (render-only)

- TAPE view: THE READ (episode/box/playbook) → trap radar → momentum card
  → ladder (pivots + event notes + strike + WALL/FLIP rungs when GEX
  present) → narrative log; TODAY SO FAR digest (open vs P, key beats,
  range, day character from traps-vs-ignitions counts); ctx banner on top.
- DATA view: top bar (IV CE/PE + 1h drift, gamma regime + strike pull,
  MM thinking in words, expected view) + 8 widgets, each with a
  PE/BEAR↔CE/BULL lean bar and confidence = |lean|:
  OI per book (lean = writer score, sign-flipped for CE), BUILD MAP
  (OI-weighted avg build price; price above a book's build avg = its
  writers underwater = fuel), VOLUME (vol-weighted 30m direction),
  VWAP & BANDS (z/2), LEVELS & BOX (position in box), MOMENTUM SETUP
  (direction × status weight), TRAPS (recent trap side, inverted).
  Click a widget → its evidence table (largest OI episodes classified,
  biggest volume bars, band touches, etc.). All computed client-side
  from bars ≤ current scrub position.

## Live mode specifics

Same Session code. VWAP/σ self-computed cumulatively; pivots from prior
session FUT H/L/C; sticky ATM on the 100-grid; CARRY hidden before 15:25;
payload refreshed every 60s server-side, repolled every 60s by the page.
Dhan OI lags a few minutes — squeeze/peak-lag timing is blunter live than
on clean TV-export data (open backtest question).
