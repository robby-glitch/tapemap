# Fresh screen: design notes

Mockup: [fresh-screen.html](fresh-screen.html). Double-click it. It is one file with a read-only
snapshot of the live API embedded, taken 2026-09-23 around 10:52 IST. To refresh it with the
server running, run `python snap.py` and then `python build.py` in
[fresh-screen-build/](fresh-screen-build/). Both are GET only. The page can't poll the server
itself: the server's CORS allows only `kite.zerodha.com`, so a `file://` page can't read it.

## What I read, and what I didn't

I read CLAUDE.md, START-HERE, research-findings §1–§5 (including §1b and the new §1d),
logic-plain-english, mental-map, frame.py, server.py's routes, and the docstrings of about 30
modules. I pulled every GET route for all three indices.

I didn't open ui/, ui-v2/, docs/mockups/, chrome-ext/, any .png, the three ui-* context files,
or any existing .html/.tsx/.css. Two files, `opus5-review.md` and `opus5-screen.html`, appeared
in this folder during my session. I didn't open them either.

A few passages I read before realising they described old screens:
- the "UI composition" tail of logic-plain-english
- the `ui/` and `ui-v2/` rows of mental-map
- about ten lines of HANDOFF-DESK §2 describing the old desk.html
- HANDOFF's "BOARD tab" heading

I stopped at each. The only visual idea I carried over on purpose is §1b's azure zone colour,
because that is your Kite chart, not this tool.

---

## 1. Your questions, and the order I'd put them in

Your list: worth trading → what kind of market → who is trapped → is there a trade → am I safe.

1. **"Is there a trade now, and what kills it?" goes first.** It's the only one that changes
   minute to minute, and it's the one you act on.
2. **"Am I still safe?" isn't a separate panel. It replaces #1 while you hold something.** The
   tool can't see your book (HANDOFF-DESK §1: that's yours and private), so this needs one input
   from you: "I'm in this". The mockup fakes that with a Flat/Holding switch and uses the tool's
   own 09:57 entry as the example.
3. **"Who is trapped" should be asked as "who stopped adding first".** Pain is a stock: it says a
   tank is full, not when it goes off. Your 09-22 rule is about flow ("which side stops first
   increasing, then unwinding"), and timing lives in flow. The engine already has this as
   `fronts.py`, and it's the only one of its three "trapped" answers that follows your rule (see
   §4).
4. **"What kind of market" collapses to one mechanical fact: does dealer hedging damp or amplify
   here, and where is the flip.** The engine has at least six regime words. Only this one is
   mechanism, and it's the one that decides whether a fade is sane.
5. **"Is today worth trading" can't be answered honestly today.** The seller gate is permanently
   PATA NAHI (§4d). What the engine *can* say in the morning is who today is paying:
   - the buyer's tax on each index
   - IV vs realized
   - how much of the straddle's range is already used

   That's a morning glance, not a headline, so it sits lower down.

## 2. The design

**Two surfaces.** No more.

- **Beside the chart:** one 470px column, light background so it doesn't glare next to Kite's
  white.
- **After the bell:** full width. This is for the record, the paper desk, the structures, the
  surface, and the day's series. Nothing on it is needed while a bar is forming.

**The column, top to bottom:**

| layer | what | why it's there |
|---|---|---|
| index strip | NIFTY / BANKNIFTY / SENSEX, each with a one-line state ("SELL armed at u2", "sell zone 42 pts up") and a dot when something is armed | You trade all three. "Which index has something" is the first glance, and it costs one line. |
| **the answer** | the zone machine's state as a sentence; how it goes in (close past the arming bar's extreme, candles left); fade gate with its reason; the defender front now; stop; target (VWAP); falsifier; tape events at the edge; method caveats | This is the only big type on the screen. Everything below it is evidence for it. |
| **the rail** | a vertical price axis in the futures frame, so it lines up with your chart: both zones in Kite azure, VWAP, OI per strike (CE indigo / PE ochre, dark part = added today) with the four fronts outlined and named, levels (PDH/PDL/PDC/OPEN/max pain/flip/PWH) with the war map's test counts, tape walls, and the machine's armed/trigger/stop lines. Below it: dwell, runways, and what's off the edges. | Every price-located fact in one place, on your chart's axis. It shows what the chart can't: where the OI is, and in which state. |
| **who is trapped** | a headline ("CE 23,400 stopped first · peaked 10:15"), a small chart of the four fronts' OI-change since the open with a peak marker, spot drawn above it, one row per front, and a one-line strike-breadth count | This is your 09-22 rule drawn as a picture. The peak dots are exactly "who stopped first". |
| the day | worth trading? (honest CAN'T SAY); dealer hedging + flip, with a DISAGREE flag when the engine's own gamma read contradicts it; range used vs the straddle; ATM IV vs 5-session RV; VPIN; buyer's tax on all three indices side by side | One glance, mostly for the morning and for picking an index. |
| today so far | a 09:15–15:30 strip with arms (hollow) and entries (filled), amber when the gate said not legal, ticks where a front stopped, and tape event dots; then the rows as a list | What already happened, without scrolling a log. |
| drawers | engine narrative, the desk's structures, the desk's direction view, coverage, participant OI, legend | Kept, labelled, one tap away, and never on the face. |

**Colour and grammar.**
- **Red and green don't appear anywhere.** Your chart already uses them for price, and a green
  "legal" next to a red candle would be two languages on one desk.
- **The zone is the one colour I brought in: Kite's azure,** so "blue" means the same thing on
  both screens.
- **Calls are indigo and puts are ochre.**
- **Amber means "look here"** and never means up or down.
- **The house rules on screen:**
  - [M] is plain type and [I] is italic with a dotted underline, with the reason on hover. A
    `[I]` tag on every number would drown the numbers.
  - "Could not check" is a hatched chip that always prints its reason.
  - "Checked, nothing" is plain grey "none".
  - "Not showing you" is a drawer with a count on it.

  Those are three visibly different things, never one blank.
- **No rates anywhere,** including the after-the-bell record (counts per population only).
- **The two method caveats are printed every time they apply,** not buried:
  - selling the upper zone is the unproven half (5 datasets rejected it; u2 SELL is still your
    call)
  - BANKNIFTY trends

**Built only on sources all three indices have** (`/api/data` 3-min zone machine,
`/api/oihist` fronts, `/api/warmap`, `/api/chain`, `/api/drag`, `/api/surface`, `/api/signals`).
The GoCharting frame adds tape walls, tape events, strike breadth and the live gate, and it
exists only for NIFTY. On the other two indices every frame-only item shows as "can't see", with
the reason.

**Invented** (marked MOCK on screen):
- the Flat/Holding switch
- "you hold it"
- the "your stop" box

**Page arithmetic:**
- The sentences are composed by the page from engine fields.
- Distances in points and the "range used" percentage are simple arithmetic.
- In production the engine should emit the answer object itself (§5); the face shouldn't be
  deciding wording.

## 3. The map, and where each piece lives

Face = on the column. Glance = the day strip or today strip. Drawer = one tap. Review = after
the bell. Cut = not on screen.

| # | piece, in plain language | lives | why |
|---|---|---|---|
| 1 | VWAP and σ bands on the 3-min future (u/d 1–3) | face (rail, answer) | They define your zones. |
| 2 | Zone machine per side: WAITING/ARMED/TRIGGERED/IN_TRADE, reference bar, candles left, stop | face (headline, rail lines) | This is the trade. |
| 3 | Forward record: every arm and entry, with its population and gate stamp | glance (today) + review (counts) | Shows what happened, with populations kept apart. |
| 4 | Fade gate: is a fade legal (defender front building, no engine veto) | face | Your "if market condition is right". |
| 5 | Near-ATM fronts: top-2 strikes per side, build/stall/unwind, peak time | face (panel + rail) | Your rule. |
| 6 | "broke": the first front to stop | face (fronts headline) | The single most useful sentence the chain produces. |
| 7 | Strike breadth: strikes written/unwound in the last 15 min | face, one line (NIFTY only) | Tells you whether a front's move is broad or lone. |
| 8 | Breadth concentration/advancing/retreating/pressed/bought | cut | Counts that change no decision. |
| 9 | OI per strike (chain): OI, today's change, IV, greeks | face (rail bars) | Where the inventory sits, on your axis. |
| 10 | Max pain | face (rail) | A level. |
| 11 | Gamma flip / GEX / damping vs amplifying | face (rail) + glance (day) | The one mechanical regime fact. |
| 12 | Expected move (ATM straddle) | glance (range used) | Tells you how much day is left. |
| 13 | Levels map: PDH/PDL/PDC/PWH/PWL/OPEN/ROUND | face (rail); rounds shown only as strike ticks | Where retail reacts. |
| 14 | Sequence machine per level: tests, last outcome, RUN target | face (rail labels, e.g. "OPEN tested 11×, last reject") | Tells you which levels are live. |
| 15 | Dwell: price parked at a level, which side is loading | face (under rail) | The trap being set. |
| 16 | Runways: target each way, trapped premium per point | face (under rail), [I] | Which way pays the dealer to run. |
| 17 | Tape walls (resting offer/bid size, times leaned on) | face (rail), NIFTY only | Where you'll be absorbed. |
| 18 | Tape events: absorption/exhaustion/trap/vacuum/initiative | face ("tape at the edge") + glance (dots) | Flow at the zone edge. |
| 19 | 5-min frame falsifier ("close past X held 3 bars") | face ("wrong if") | Tells you what kills it. |
| 20 | Seller gate: TRADE / HALF / NO NEW RISK / PATA NAHI | glance, shown as CAN'T SAY plus its would-be | Honest about its holes. |
| 21 | Buyer's tax (drag) per index | glance, all three side by side | Tells you who today pays, and on which index. |
| 22 | ATM IV and the day's IV path; 5-session RV | glance; IV path in review | Vol sold vs vol paid. |
| 23 | VPIN toxicity, slow and fast, NIFTY future | glance (NIFTY) + review series | An expansion-risk gauge. |
| 24 | Coverage: late start, what was rebuilt, what can't be | top strip ("up since") + drawer | Anytime-start rule. |
| 25 | Feed health (connected, age, reconnects) | top strip | A dead token looks like a quiet market. |
| 26 | Engine event narrative (CAMPAIGN, DIVERGENCE, TRAP-SPRUNG, BAND-REVERSAL…) | drawer | Scored below do-nothing (§2); readable, not actionable. |
| 27 | Engine verdict GO/WAIT/CAUTION/STAND ASIDE/SPENT | cut (mentioned in drawer) | A second opinion with no record that contradicts the gate (§4e). |
| 28 | Engine "derivative breadth" STRONG BULL etc. | cut | breadth.py's own docstring: one direction counted three times. |
| 29 | Engine episode / box / playbook strings | cut (plays are an input to the gate) | Same stream as #26. |
| 30 | Engine narration line, flips radar, per-bar ranks (vol_r, rng_r, bw_r, oi_slope, prem_d) | cut | Inputs, not answers. |
| 31 | Engine gamma regime (PINNED/FLOOR/CEILING/AMPLIFIED) + writer scores | glance, as "the engine's own read" with a DISAGREE flag | Kept only as a cross-check on #11. |
| 32 | One-candle `rotation` layer | cut | VOID (§1). |
| 33 | SMC/ICT structures | cut | Default OFF, over-fires 4×. |
| 34 | Option-premium pivots, ATM CE/PE legs' own bands | cut | Not your method. |
| 35 | /api/contract pair stack | cut | No consumer; already flagged "ship or delete". |
| 36 | frame `trapped.writers` (max pain over every leg) | cut | Contradicts #5; points at far strikes (§4b). |
| 37 | frame `trapped.window` / `pace` (3-min OI window, pace ranks) | cut | #5 answers it better. |
| 38 | frame `tells` (DOWN/PIN predicates) | cut | Untested [I] re-statements of what the fronts show. |
| 39 | frame `where` extras (hour net/travel, off-extreme, z) | cut | Your chart shows these. |
| 40 | frame 5-min signal ballot (votes, visit, FIRE, sound) | face, one line only when it disagrees | A second setup machine (§4a). |
| 41 | frame aggressor (sign of session delta) | cut | The footprint on your chart. |
| 42 | Watch-list flags (AGREE/SIZE/CLOSING) | folded into the rail | Not a separate list. |
| 43 | Wall-migration log | cut | Flickers (§4k). |
| 44 | Trending OI table (/api/oiflow: call/put sums, PCR, BULLISH/BEARISH) | cut | A direction label from sums; the fronts do this properly. |
| 45 | Heat map pain per strike | cut | Feeds #36. |
| 46 | Driver lean (futures-led / option-led) | cut | UNCLEAR most of the day; no decision hangs on it. |
| 47 | Participant OI (NSE EOD, a day old) | drawer | Morning context. |
| 48 | Senses rows: sweeps, absorption, depth pulls | cut from the column | An adverse-selection layer for a quoting desk; the paper desk uses it. |
| 49 | Pools (shelves, vacuums) | cut | Order bridge dead (`books: 0`); wall vs cluster unknowable. |
| 50 | Fuse gear PIN/TRANSITION/CASCADE/UNKNOWN | cut | Shadow; UNKNOWN on all 55 instruments at the snapshot (§4c). |
| 51 | Chainside fuel / drain / trapped side | cut | Feeds #50 and #52. |
| 52 | Desk direction view (BULL/BEAR, FORCED/LEANING) | drawer, with a caveat | Built on #36's leg (§4b). |
| 53 | Desk structure catalog with statuses | drawer + review | Seller structures are a between-trades question. |
| 54 | Surface fit (ATM IV, skew, convexity, residuals, richest/cheapest) | glance (ATM IV) + review | Cross-sectional only. |
| 55 | oi_dwell hysteresis OI direction | cut | Another direction label. |
| 56 | Paper desk: book, marks, forced ratio, decisions, refusals, P&L by strategy | review | The tool's paper trading, not yours; a distraction mid-bar. |
| 57 | Short-variance hedger ledger, theta estimate, margin shift | review (not in the mockup) | End-of-day accounting. |
| 58 | Kyle lambda (impact), runs, Upstox ladder (ux), prints/POC/stacks | cut | Research instruments on kill clocks; the chart owns the footprint. |
| 59 | Records: frame log, tape log, book log, senses log, desk log | cut | Records, not readings (#3 is the one you need). |
| 60 | Latency p50/p99 | cut | Engineering. |

---

## 4. What made designing hard, worst first

**a. Two setup machines, two intervals, two sets of bands.** The forward record and the zone
machine run on 3-min Upstox bars (CLAUDE.md rule 3: "3-minute is canonical"). The frame's ballot
and visit machine runs on 5-min GoCharting bars, and `POST /api/frame` rejects any other
interval. At 10:48 both armed SELL at 10:36, but:
- the zones differ by about 4 pts (u2 23,442.8 vs 23,438.8)
- the stops differ (23,462.8 vs "a 5-min close past 23,453 held 3 bars")
- **the 5-min ballot said FIRE while the fade gate said NOT LEGAL**

A face can only show one trade. I picked the 3-min machine because it's the record, and
demoted the other to one line. The engine should pick one.

**b. "Who is trapped" has three answers, and two use the leg your rule excludes.**
- `frame.trapped.writers` takes max pain over every leg.
- `chainside` / the desk's `view` take the worst leg.

At 10:33 both named **CE 23,000**, 400 points in the money. That's the "hedging strike" you
called irrelevant on 09-22. The desk's direction view (BULL · LEANING) is built on it. `fronts`
follows your rule and named CE 23,400 / PE 23,400. frame.py knows this and publishes both
"because they are different questions". On a screen they read as one question with two answers.

**c. "What kind of market" has at least six answers, and they disagree right now.**
- fuse gear: UNKNOWN on all 55 instruments
- desk regime: AMPLIFYING (below the flip)
- engine gamma: FLOOR
- engine state: BALANCE
- engine verdict: CAUTION
- engine breadth: STRONG BULL

The flip itself moved 23,509 → 23,562 → 23,645 (index) between 10:33 and 10:52. I show the flip
and the engine's gamma read side by side, with DISAGREE when they conflict. That's honest, but
the engine should say which one it believes.

**d. "Worth trading today" can never be answered.** `gate.state` adds "event calendar not wired"
unconditionally, so the level is always PATA NAHI. On top of that, `_book_for` hard-codes
`ivrv: None` and `senses: None`, even though `/api/surface` has ATM IV and rv5 and VPIN exists.
The gate is blind to inputs the engine already has. Also:
- IV is on a 365-day basis and RV on 252, so they can't be ratioed naively.
- VPIN's slow percentile is null for the first hour, which is exactly when this question gets
  asked.

**e. The engine stream is dead as a signal but still speaks.** At 10:48 its play read "[LOW]
FADE the 23450 band tag, scalp ~1R down; seller: sell CE" while the gate said NOT LEGAL. HANDOFF
2026-09-23 records the verdict's "gate something or leave the headline" fix as not done. I cut
it from the face.

**f. Half the richest data exists for one index only.** The GoCharting frame (tape walls,
events, breadth, live gate, falsifier) is NIFTY only, because the extension sits on one chart.
Anything built around `/api/frame` is blind on BANKNIFTY and SENSEX. BANKNIFTY is also where the
fade has no validated edge.

**g. `/api/signals` pools populations in its headline counts.** `legacy = entries where rule !=
"5c"`, which lumps 112 NIFTY `zone` entries in with the 161 quarantined rows. `zone` has no count
of its own. That's rule 5 broken in the one place a screen would read counts from. The review
view counts populations itself and says so.

**h. The zone machine already answers an "open" question.** §1b(b) asks whether the stop is
d3−20 or d2−20 ("owed by the operator"). The machine publishes `stop = level ± 20` on the
arming edge (23,442.79 → 23,462.79), so the code has quietly chosen d2/u2 ± 20. I show it as
"the zone machine's stop"; you should know it's there. In Holding mode I show no stop for the
same reason.

**i. The buyer's-tax "worst of the day" is an artefact.** `drag.day.hi` read **1,786%** at
10:25: a tiny move near the anchor divides by almost nothing. The mockup flags it (TINY-MOVE
ARTEFACT) and leaves |tax| > 150% out of the review series. The meter needs a minimum-move floor
before `hi` is taken.

**j. Three price frames, and every consumer shifts them itself.**
- index: war map levels, strikes, flip
- futures: bands, frame, tape walls
- chain: flip, max pain

The basis moved 20.5–26.7 during the session. Your chart is the future, so the engine should
publish everything in the futures frame with the strike as a label.

**k. The wall-migration log flickers.** "floor moved 23350 → 23100", then "23100 → 23350", then
back, within 60 seconds, each "held 3 readings". It isn't readable as information.

**l. The desk says two things at once.** `/api/desk` reports `ok:false, best:null` (the gate
holds it) while a candidate is `DEPLOYABLE`. A face has to pick.

**m. Kill clocks everywhere, and no ledger of them.** gear, direction, ballot, per-vote depth,
taps, tells, pain column, lambda, VPIN, the war map sequence, the fade gate, SIGMA_FLOOR: each
module carries its own 30-session clock in its docstring. There's no one place that says which
modules are alive, on the clock (and at which session count), or killed. That list is what a
screen most needs in order to know what it's allowed to show big.

## 5. What would make this real

Smallest first:
1. **An `/api/answer?idx=` object** carrying the side, the state, the gate, the defender, the
   stop, the target, the falsifier and the caveats, with `[M]/[I]` and `*_why`. Then the face
   formats and composes nothing, which is frame.py's own rule.
2. **One setup machine on one interval.**
3. **"Trapped" = fronts, everywhere,** including the desk's direction view.
4. **Wire IV/RV and VPIN into the gate, and name the calendar hole** as the only permanent one.
5. **Everything in futures coordinates.**
6. **A per-population count in `/api/signals`.**
7. **Serve the page from the server** so it can poll. As a double-clicked file it can only carry
   a snapshot.
