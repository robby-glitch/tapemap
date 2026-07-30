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

**OPEN QUESTION (blocking):** must both legs be the *same* strike, or may they
be different strikes whose premiums match? The operator's own two charts on
2026-07-30 were **SENSEX 77500 CE and 78000 PE** — different strikes — which
suggests a premium-matched *pair* across strikes. Confirm before implementing;
it changes the picker completely.

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

## Setup B — the pin

> "if price are just fiddling in and around +-1 std and the books are showing
> both die balance when can expect pinning coiling and as per gamma as well we
> can take those trades they become my buying and selling zones"

Conditions: price oscillating inside ±1σ · both books balanced · gamma agreeing
(PINNED) · a coiling / compressing state. The ±1σ edges then become the working
zones.

**Nearly buildable today** — every input already exists per bar: `inside1`
(share of the last 30 bars inside ±1σ), `bw_r` (bandwidth rank, i.e. the
compression), the BALANCE / COILING states, and `gamma.regime` PINNED.

**OPEN QUESTION:** the expression. "buying and selling zones" reads as fading
both edges, but whether that means buying the cheap leg at each edge or selling
premium into the pin is **undecided by the operator** ("not decided on that
one"). Do not guess — the two have opposite risk profiles.

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

`bw_r` (bandwidth rank) is exactly this measurement and already exists per bar.
The rule to encode is roughly: *a break is trustworthy when it emerges from a
low-`bw_r` regime; a spike while `bw_r` is already high is suspect.* The COILING
state (`bw_r < 0.3`) already marks the loading phase.

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
2. **The 09:20 premium-matched leg picker** (±30 NIFTY / ±50 BANKNIFTY, SENSEX)
   — blocked on the same-strike-vs-pair question above.
3. **OI acceleration** — the slope of `oi_slope`, per book, both sides.
4. **Reversal-from-band detection**, tuned separately for premium and index.
5. **The compression→expansion trap filter** over `bw_r`, plus naming the
   trapped side from wall OI.
6. **Setup B**, once the operator decides the expression.

## How this gets validated

`signal_review.py` scores a rule against a session with the unconditional move
as the control, and `data/backtest/` holds ~55 cached days. Encode, then score —
in that order, and score before trusting. The operator declined a backtest on
2026-07-30; ask before running one.
