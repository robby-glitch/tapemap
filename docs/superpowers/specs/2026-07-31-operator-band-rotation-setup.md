# The operator's own setup — band rotation on option premium

**Date:** 2026-07-31 (dictated by the operator on the night of 2026-07-30, in
answer to six questions)
**Status:** specification, nothing built yet
**Relationship to the Tape Chart spec:** this is the *reason* to build Phase 5
(`/api/contract`). `2026-07-29-contract-tape-design.md` specifies Phase 5 as
"the option contract chart" in general terms; this document says what the
operator actually needs it to detect.

## Why this document exists

Every analytic in this tool so far encodes someone else's read — SPRING, ARMED,
the `loc` box grading, LuxAlgo's SMC vocabulary. This is the operator's own
edge, in their words, and it is the first thing the engine should be taught to
find. Quotes below are theirs, kept verbatim where the wording carries meaning.

---

## Setup A — the band extreme, confirmed by the other leg

> "i always look to buy ce or put at the very lower band or the last line of
> -2 std vwap while making sure the other side is also coming down from the
> +3 +2 upper line"

### The instrument — the part the tool cannot see today

The bands are on **the option's own premium**, with its own VWAP — not on the
index. TapeMap computes VWAP + σ bands on the FUT only, so **the series this
entire setup reads does not exist in our payload yet**. Building it is Phase 5:
the `ChainPoller` already sees every strike's `ltp` / `oi` / `vol` every ~10.5s,
so per-strike premium bars with a 09:15-anchored VWAP and ±1/2/3σ are
constructible from the feed we already run — no new data source.

### Leg selection — a premium-matched pair, chosen once at 09:20

> "i usually like to follow the strike price which has almost similar price at
> the open or after 9:20 differnece can be +- 30-50 if its nifty 30 is good and
> if its banknifty or sensex differnece can be +-50 can work"

Pick the CE and the PE whose **premiums are nearly equal** shortly after the
open — tolerance ±30 (NIFTY) / ±50 (BANKNIFTY, SENSEX) — then follow that pair
all day. This is a premium-parity ATM, not "nearest strike to spot".

**ANSWERED 2026-07-31: a premium-matched pair across DIFFERENT strikes.** Not
one strike where CE ≈ PE. The picker scans the chain for a CE at one strike and
a PE at another whose premiums are within tolerance of each other shortly after
the open, and follows that pair. The operator's own 2026-07-30 charts —
**SENSEX 77500 CE and 78000 PE** — are the reference case.

Consequences for the implementation: the pair is generally **not** delta-neutral
and not symmetric around spot, so nothing downstream may assume the two legs
share a strike or sit equidistant from the index.

**ANSWERED 2026-07-31 — the ATM straddle is the anchor, and the tolerance is
only an admission gate.** Implementing "minimise |CE − PE| within ±30/±50"
literally selects deep-OTM wings: both legs converge to ~₹0, so their difference
is ~₹0.05 and they beat the ATM straddle every time (measured: 520 of 668 cross
pairs sat inside tolerance, so the gate was selecting almost nothing). The
operator's answer — *"yeah straddle is about right because they almost forms
mirror charts"* — gives both the fix and the reason: near-the-money legs mirror
each other (delta ≈ ±0.5), which is the property the setup actually reads. Deep
wings do not mirror, they merely decay together.

So: **tolerance admits, distance-to-ATM selects, premium difference tie-breaks.**

**EXPIRY DAY IS OUT OF SCOPE, and this is the one trap to avoid.** The reference
charts (SENSEX 77500 CE / 78000 PE) differed by ₹173.25 at 09:20 and only
converged at 13:39 — which looks like it disproves the rule, and does not:
**2026-07-30 was SENSEX expiry**. Operator: *"since today was sensex expiry so
that why otherwise atm straddle is ideal"*. On expiry the ATM straddle is
decaying into settlement and the strikes that matter are the walls — a different
selection problem. **Do not tune the tolerance or the objective to make an
expiry session fit**; that fits the exception and breaks the ordinary case. The
expiry-day rule is **unspecified — ask before building it.** `engine.py`'s
`carry_verdict` already branches on `gamma.t <= 0.5`; reuse that test rather
than inventing a second definition of expiry day.

### Trigger — a tag, but it must REVERSE

> "tag or wick is enough but has to reverse from the last band because in option
> price can tap the extream bands but index often just poke the -3 std band and
> reverse so it depends"

- A wick into the band is enough; no close beyond it is required.
- **The reversal is the signal, not the touch.** A touch alone is not an entry.
- Asymmetry worth encoding: on the **index**, a −3σ poke usually reverses on its
  own. On **option premium**, price can sit on or ride the extreme band, so the
  reversal confirmation matters far more on the option series. Any detector must
  be tuned per series, not shared between index and premium.

### Confirmation — the other side rotating

The opposite leg must be **coming down from its +2/+3σ**. The pair rotates: one
leg washed out at its floor while the other unwinds from stretched. That is what
separates a genuine rotation from both legs decaying together, which is just
theta on a dead day.

### The OI condition — acceleration, not a peak

The operator's answer corrected the obvious reading. It is **not** "OI is at its
session peak":

> "the band peak oi is like cumlative delta and change in delta so it can be
> cumlative and mostly oi is lagging indicator so we need to prempt by the
> change on the both side means the rate of change of oi is declining now so it
> can give a sense if the oi is peaking or early unwinding has started"

So: **the rate of change of OI is decelerating, on both sides.** OI itself lags,
so a peak is only knowable after the fact; the decay in the *rate* of building
front-runs it. Implement as the second derivative — the slope of `oi_slope` —
evaluated on the CE and PE books together.

`oi_slope` and `oi_slope_r` are already published per book per bar, so this is a
derived quantity over existing fields, not new plumbing. `ce_pk`/`pe_pk`
(session-high OI per book) stay useful as context — "how far off peak" — but
they are not the trigger.

### Positioning does not veto it

> "so suppose book is put heavy but put prices are touching the last band so we
> can except a bounce from there"

A heavy book on the side being bought does **not** invalidate the setup. Premium
exhaustion at the band outranks what the book thinks. Any implementation that
filters on "the book is against you" would delete the operator's edge.

### Exit — band-to-band, modulated by regime and level

> "we like to chase as per bands to bands and as per the market condition if
> its pin day or moving day howmuch we are expecting and what oi is reflecting
> if the short covering trigged or market is breaking any major level or taking
> resistance like 100s or pdl pdh or pwh or pwl etc or premium or discount
> zones or pivots also are good support and resistance on index as wells as on
> option charts as wells so combination, 1:1 atleast"

- Default target is the **next band up** (band-to-band).
- Extended when the regime is a "moving day" and when OI says a **short-covering
  squeeze** has triggered; cut short on a pin day.
- Level context, on the **index and the option chart alike**: round hundreds,
  PDH/PDL, PWH/PWL, premium/discount, pivots. (PDH/PDL/PDC and premium/discount
  now exist in `structure.py`; PWH/PWL still need weekly history.)
- **Minimum 1:1** risk-reward, always.

---

## Setup B — the pin, and the SELL side

> "if price are just fiddling in and around +-1 std and the books are showing
> both die balance when can expect pinning coiling and as per gamma as well we
> can take those trades they become my buying and selling zones"

Conditions: price oscillating inside ±1σ · both books balanced · gamma agreeing
(PINNED) · a coiling / compressing state. The ±1σ edges then become the working
zones.

**Nearly buildable today** — every input already exists per bar: `inside1`
(share of the last 30 bars inside ±1σ), `bw_r` (bandwidth rank, i.e. the
compression), the BALANCE / COILING states, and `gamma.regime` PINNED.

### ANSWERED 2026-07-31 — selling is in scope, and it is the mirror image

> "if we can build the setup b something in here where we can also decided if
> we want to sell option as well that also a good option because mostly markets
> are in sidways so we can sell premium and can sit with market maker view to
> eat premium the logic for selling is same always look to sell +3 bands
> reversing from there we can sell that"

**The trigger is one detector, not two.** Both sides are "premium at a band
extreme, then reversing":

| | leg's own premium | reversal | when preferred |
|---|---|---|---|
| **BUY** | at the lower band, −2σ / −3σ | turns back **up** off it | a moving day — the washed-out leg bounces |
| **SELL** | at the **+3σ** upper band | turns back **down** off it | a sideways / pinned day — eat premium beside the market maker |

So Setup A and Setup B share one primitive — *band extreme + reversal* — and the
**regime picks which side you want**. That is the whole design: build the
detector once, symmetric, and let PINNED/COILING versus a moving day select
between buying the cheap leg and selling the stretched one.

Note the asymmetry in the operator's own thresholds: they buy at −2σ *or* −3σ,
but sell only at **+3σ**. Selling is the more selective condition, which fits —
a stretched premium can stretch further.

### What kills a short — the engine already computes it

Selling is not the buy rule with the sign flipped, because the risk is not
symmetric: the buyer's worst case is the premium paid, the seller's is open-
ended. Two things the engine already produces map directly onto "get out":

- **`SQUEEZE-RISK`** — literally "writer book pressed on its pain side, unwind
  accelerating → upside/downside squeeze risk building". That is precisely the
  event that ends a premium seller's day, and it is already emitted per book
  with its own receipts. For a short it is a **kill condition**, not a
  directional read. (Worth noting: scored as a directional signal on 2026-07-30
  it was the worst performer, 2/10 — which is consistent with it being a
  warning rather than a call, and with it being useful for exactly this.)
- **`WALL-MIGRATION` / `role` flipping** — the wall you sold against moving is
  the structural version of the same thing.

`gamma.regime` also tells you which side is safer to sell: FLOOR means put
writers are defending below, CEILING means call writers are defending above.

**Still to decide with the operator:** position management for a short — band-to-
band on the way down is the buyer's exit rule, but a seller's exit is a stop
plus a decay target, and they have not specified either. Do not invent them.

---

## The trap filter — the most valuable part

This is what the operator asked the tool to protect them from, and no existing
analytic captures it.

> "trap are like the todays shrap move around 12:30 than no follow back it
> dipped to almost the days low… so suppose ce book is heavy and breaking the
> bands and volatitly expanding the bands so the whole vwap bands are expanding
> not narrowing or staying flat range is very small . and than the break so
> that side you know because smart money always make possition is narrow change
> once they load there position than the market start moving they put the
> distance there right the lLower lows Or HH"

The distinction is **what the band width was doing BEFORE the move**:

| | band width before the move | what the move is |
|---|---|---|
| **Real** | narrow / flat, range small — smart money loading inside compression | the break that follows is the move; bands expand, price makes HH or LL |
| **Trap** | already wide / expanding, no prior compression | a spike with nothing behind it — 2026-07-30 12:30 is the reference case: straight up, no follow-through, gave it back to near the day's low |

### REFINED 2026-07-31 — it is PRICE range and DWELL, not band width

The first implementation ranked **band width** and it does not work: measured
over 73 cached sessions it marked CLEAR on 26 of 747 signals, and CONFIRMED +
CLEAR happened twice in 73 sessions. Two separate reasons, both now understood:

1. **Band width grows monotonically through every session** (median
   `(u1-d1)/vwap` rises 0.117 → 0.388 across session deciles) because σ
   accumulates from the 09:15 anchor. Ranking a pre-move window against the
   session so far therefore measures **how late in the day it is**, not whether
   price coiled. No threshold fixes that; the comparison is the wrong shape.
2. **More important — band width is the wrong quantity.** The operator's own
   annotated chart (2026-07-31) shows a long coil where the ±1σ region is
   *wide* while price grinds in a thin strip just below VWAP: *"Price is in this
   narrow range just below vwap and -1std deviation"*, followed by a vertical
   break through the upper bands. Band width would call that period
   uncompressed and miss the setup entirely.

So compression is measured on **price**, not on the envelope:

- **Range** — the high/low range over a trailing window, normalised (by VWAP,
  or by the band width so it reads as "how much of the available room is price
  actually using"), ranked against a **trailing** window rather than the
  session so far, so "narrow" means narrow relative to recently.
- **Dwell** — *"is its a good thing to notice or keep in mind for how long the
  price are in this range"*: yes. How many consecutive bars price has held that
  narrow range is a separate signal from how narrow it is. A thin range held for
  90 minutes has far more loaded inside it than the same range held for ten.
- **Direction of change** — the operator's words are *"expanding or narrowing"*
  and *"not narrowing or staying flat"*. Judge the **trend** of the measure
  across the run-up, not only its level.

**Anchor at 09:25.** *"by 9:25 we have the values for vwap standard deviation
and from there we judge wheather they are expanding or narrowing."* Before that
there is too little session to rank anything — which matches the measured
finding that 23% of triggers land in the first 10 bars, where every gate is
`UNKNOWN` by construction. Do not report a compression verdict before the
anchor; report `UNKNOWN`.

### The ±1σ interior is the NO-TRADE zone

*"mostly +1 -1 is like the zone of no trading becuase during whole day the price
almost spent of the their time in their."* This is the counterpart to Setup B
and must not be confused with it: the **interior** of ±1σ is where price idles
and where the operator does not trade; Setup B's *"buying and selling zones"*
are the **edges** of that box during a pin, not its middle.

**OPEN — confirm before relying on it:** that reading (interior = stand aside,
edges = the zones) reconciles two statements that otherwise conflict, but the
operator has not confirmed it in those words.

And the second half — **who is being trapped**:

> "market like to either trap sellers or buyers and we need to figure out their
> direction who they are targetting today or who can be trapped where retails
> have made the maximum position"

Maximum retail position = the heaviest OI strikes, already tracked as the walls
(`ChainState.role`, `wall_log`, per-strike `oi`). The engine should name the
side with the most to lose, not merely the level.

---

## What exists vs what must be built

**Already in the payload:** FUT VWAP + ±1/2/3σ · `bw_r` · `oi_slope` /
`oi_slope_r` per book · per-strike `oi`, `oi_chg`, `ce_pk`/`pe_pk`,
`ce_w`/`pe_w`, `gex`, `role` · gamma regime PINNED/FLOOR/CEILING · BALANCE /
COILING states · `inside1` · pivots · PDH/PDL/PDC and premium/discount
(`structure.py`, 2026-07-30).

**To build, in dependency order:**

1. **Per-strike premium bars + option-side VWAP σ bands** — Phase 5
   (`/api/contract`). Everything in Setup A depends on it. Source is the
   existing `ChainPoller` tick stream; no new feed.
2. **The 09:20 premium-matched leg picker** — a CE and a PE at *different*
   strikes whose premiums are within ±30 (NIFTY) / ±50 (BANKNIFTY, SENSEX).
3. **Band-extreme + reversal detection — ONE symmetric detector**, tuned per
   series (premium vs index): lower band → buy side, +3σ → sell side.
4. **OI acceleration** — the slope of `oi_slope`, per book, both sides.
5. **The compression→expansion trap filter** over `bw_r`, plus naming the
   trapped side from wall OI.
6. **The regime selector** — PINNED/COILING favours the sell side, a moving day
   favours the buy side. Inputs all exist (`inside1`, `bw_r`, `gamma.regime`,
   BALANCE/COILING).
7. **Short kill conditions** — wire `SQUEEZE-RISK` and `WALL-MIGRATION`/`role`
   flips as exits for a sold leg, not as directional reads.

## How this gets validated

`signal_review.py` scores a rule against a session with the unconditional move
as the control, and `data/backtest/` holds ~55 cached days. Encode, then score —
in that order, and score before trusting. The operator declined a backtest on
2026-07-30; ask before running one.
