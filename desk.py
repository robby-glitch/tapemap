"""desk.py -- which structure the market is actually paying for right now.

Reads two things and names a trade: the fitted surface (`surface.py`) and the
regime (`chain_metrics`' gamma flip, GEX and max pain, already computed and
until now never read by anything).

WHAT "DEPLOYABLE" MEANS HERE, AND WHAT IT DOES NOT. Every candidate carries a
STATUS, not a confidence score. The distinction is the whole point:

    DEPLOYABLE    the inputs this structure needs all exist and agree
    BLOCKED       a required input is missing, and `missing` names it
    STAND_ASIDE   the inputs exist and say don't

A confidence score would collapse three different claims -- confidence in the
FIT, confidence the MISPRICING IS REAL, and confidence the TRADE MAKES MONEY --
into one number a reader inevitably takes as the third. Only the first is
computable today; the third needs a track record that does not exist. So this
reports status plus the fit quality behind it, and `edge` as a description,
never a probability.

THE LEVEL IS UNKNOWABLE TODAY; THE RELATIVE VALUE IS NOT. Without multi-day
history nothing here can say "vol is rich" -- only "this point is rich against
its own curve". That decides which structures are honest on day one: a
RELATIVE-VALUE spread (sell the rich point, buy the cheap one) needs no level
view at all, while an outright strangle is a bet the level is high. The former
is deployable on the surface alone; the latter needs the regime to vouch.

THERE IS NO DIRECTION VIEW IN THIS STACK. Nothing computes bullish or bearish,
so every directional structure is BLOCKED rather than guessed. The gamma flip
is a REGIME read -- does hedging damp or amplify -- and max pain is a pin
target. Neither is a direction.

Pure computation, stdlib only, no I/O. Emits `[I]`: a structure choice is a
judgement built on measurements, and says so.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

import gamma

# A point must sit this far off the curve, in units of the fit's own rmse,
# before a structure is built around it. Self-calibrating: a noisy chain has a
# fat rmse and therefore a high bar.
Z_EDGE = 1.5

# AND IT MUST BE WORTH SOMETHING. A z-score is a statement about how UNUSUAL a
# residual is, not about how much it is WORTH -- and the two come apart badly
# when the fit is good. Measured live on 2026-08-21 at 09:42: NIFTY's rmse was
# 0.080 vol points, so z >= 1.5 needed only 0.12 vol points of residual, and
# the "best" trade the selector found was a deep-OTM put spread worth
# 23 paise a unit with a net edge of ZERO. Statistically significant,
# economically nothing.
#
# So a structure must also clear a floor in RUPEES PER UNIT of the underlying
# quantity. Deliberately absolute rather than ranked: what a rupee is worth
# does not rescale with how tidy today's curve happens to be.
MIN_EDGE_RS = 1.0

# ATM means within this fraction of the forward, in log-moneyness.
ATM_X = 0.004

# Spot must sit inside this many expected moves of max pain for the pin trade
# to be a pin trade rather than a hope.
PIN_MOVES = 0.5

# ── structure legality: shape first, richness second ─────────────────────
#
# A strangle's wings are a BET that the market stays inside a range -- which
# means they must actually sit outside the range the market itself is
# pricing (the ATM straddle), not merely be the two richest points on the
# curve. Live on 2026-08-20 the old selector named a PE twelve points from
# spot -- inside noise, not a wing -- a "strangle" leg because it ranked
# richest by z-score alone, with no concept of where a wing is allowed to be.
#
# So a candidate wing must clear BOTH bars: rich (z >= Z_EDGE, unchanged) AND
# at least this many expected moves from spot. 0.5 is deliberately loose --
# it is a floor against "the ATM point that happens to be noisy today", not a
# claim about where a desk actually likes to sell.
STRANGLE_MIN_MOVES = 0.5

# AND THE TWO WINGS MUST BE A PAIR, NOT TWO UNRELATED SHORTS. A strangle sold
# short a deep-OTM call against a near-money put is not "a strangle with a
# skewed view" -- it is a directional bet wearing a market-neutral structure's
# name, and this stack has no direction view (see the module docstring).
# Delta is the standard cross-strike ruler: two legs whose |delta| sit within
# this tolerance of each other are "the same distance from the money" in the
# market's own units, whatever the strike gap says. 0.15 admits the ordinary
# call/put skew asymmetry (a index's put wing sits closer in strike than its
# call wing for the same delta) without admitting a mismatched pair.
DELTA_BALANCE_TOL = 0.15

# ── risk, margin, sizing ──────────────────────────────────────────────────
#
# COSTS. She posts rather than crosses -- the spread is revenue, not cost --
# so the only real cost to sell is statutory: STT 0.1% + exchange 0.03503% +
# GST (18%) on the exchange leg, all on the option PREMIUM. Applied only to
# legs SOLD (buying to open carries no STT on options). This is a fixed
# statutory rate, not a judgement call, but it is not a live-fetched number
# either -- tagged [M] alongside everything else priced off the chain.
STATUTORY_PCT = 0.0014

# MARGIN IS OPAQUE; THIS IS A DOCUMENTED FLOOR, NEVER THE BROKER'S NUMBER.
# Defined-risk structures: the max loss IS a reasonable margin floor -- a
# spread cannot cost less to carry than it can lose, and most brokers
# recognise the hedge and charge close to exactly that.
#
# Naked index legs (a short strangle, the pin straddle, jade lizard's naked
# put) have no such floor -- only the exchange's own SPAN scan prices them,
# and this stack cannot run SPAN. Approximated here as a flat fraction of
# notional (forward x lot size) per naked leg, which is the crude SHAPE
# SPAN+exposure takes for a single short index option well before expiry:
# roughly 10-15% of contract value at typical index IV, tighter close to
# expiry, wider in a vol spike. NEVER presented as the broker's number --
# `margin_model` on every candidate says so in words.
NAKED_MARGIN_PCT = 0.11
# A second naked leg on the OTHER side of the book (the put in a strangle,
# against the call) cannot blow out at the same time the first one does --
# spot cannot be both far above and far below at once -- so it is not priced
# as a second full margin, only a fraction on top of the first.
NAKED_EXTRA_LEG_FRAC = 0.6

DEFAULT_CAPITAL = 5_00_00_000.0     # Rs 5 crore deployed margin, the desk's
                                     # own stated default -- capital is not the
                                     # constraint here, sizing discipline is
ONE_CRORE = 1_00_00_000.0

# FALLBACK ONLY -- `lot_size_from_chain` measures the real one off the wire.
# These were once hardcoded as 75/35/20 and were simply WRONG, scaling every
# sizing figure the desk produced by about 15%. Confirmed against both the
# live chain's own GCD and the operator on 2026-08-21. NSE/BSE revise the
# contract-value band periodically, so this table WILL rot -- the derivation
# is the number to trust and this is what stands in when a chain is too thin
# to derive from.
LOT_SIZE = {"NIFTY": 65, "BANKNIFTY": 30, "SENSEX": 20}
DEFAULT_LOT_SIZE = 65

# Smallest GCD worth believing. A chain that happens to share a small factor
# (every value even, say) would otherwise "derive" a lot size of 2 and size
# the whole book against it.
MIN_DERIVED_LOT = 5
# And an upper bound. Index-option lots sit in the tens; a "derived" value in
# the thousands means the sample shared a large coincidental factor rather
# than the real size -- which a synthetic fixture produced on the first run
# (every OI a multiple of 100,000, so the GCD was 100,000).
MAX_DERIVED_LOT = 500


def lot_size_from_chain(strikes) -> Optional[int]:
    """The lot size, MEASURED off the wire instead of assumed.

    Every open-interest and volume figure the exchange publishes is a whole
    number of LOTS expressed in units, so every one of them is a multiple of
    the lot size -- which makes the GCD across a whole chain the lot size
    itself, exactly, with no table to go stale.

    This started as a hardcoded guess (75/35/20) that was simply WRONG: the
    live chain on 2026-08-21 gives 65 / 30 / 20 across 68 values per index,
    and the operator confirmed those are the real sizes. Every sizing number
    the desk produced was scaled by roughly 15% as a result. The exchange
    revises these periodically and the payload carries no lot field, so
    deriving it is not merely tidier than a table -- it is the only version
    that cannot rot.

    Returns None when the chain is too thin or the GCD is implausibly small,
    in which case the caller falls back to LOT_SIZE and says it did.
    """
    vals = []
    for s in strikes or []:
        for side in ("ce", "pe"):
            leg = s.get(side) or {}
            for f in ("oi", "vol"):
                v = leg.get(f)
                if v and v > 0 and float(v).is_integer():
                    vals.append(int(v))
    if len(vals) < 8:
        return None
    g = 0
    for v in vals:
        g = math.gcd(g, v)
        if g == 1:
            return None
    return g if MIN_DERIVED_LOT <= g <= MAX_DERIVED_LOT else None

# SIZING IS CAPPED BY THE THINNEST LEG, NOT JUST BY CAPITAL. A crore-scale
# order in a leg carrying a few thousand contracts of OI cannot actually be
# built at the quoted price no matter how much margin is free. This caps lots
# at a fraction of the thinnest leg's own OI -- a floor against sizing a
# reading against a number nobody could fill, not a claim about market impact.
LIQUIDITY_OI_FRAC = 0.10

# AND A WIDE QUOTE CAN EAT THE EDGE BEFORE IT IS EVER POSTED. If one leg's own
# bid/ask spread is worth more than this many multiples of the WHOLE
# structure's per-unit edge, the "mispricing" is smaller than the noise in
# that leg's own quote -- posting inside it is a bet on the spread, not on the
# residual. Exempt when bid/ask is simply absent from the feed: silence is not
# evidence of a bad quote.
MAX_SPREAD_VS_EDGE = 2.0


@dataclass
class Regime:
    """What the dealers' book is forced to do -- not a direction."""
    spot: Optional[float] = None
    flip_px: Optional[float] = None
    above_flip: Optional[bool] = None
    gex: Optional[float] = None
    max_pain: Optional[float] = None
    expected_move: Optional[float] = None    # from the ATM straddle
    state: str = "UNKNOWN"                   # DAMPING | AMPLIFYING | UNKNOWN
    tag: str = "M"
    why: List[str] = field(default_factory=list)


@dataclass
class Leg:
    side: str          # SELL | BUY
    strike: float
    right: str         # CE | PE
    iv: Optional[float] = None
    resid: Optional[float] = None
    z: Optional[float] = None
    oi: Optional[float] = None
    ltp: Optional[float] = None
    delta: Optional[float] = None
    vol: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None


@dataclass
class Candidate:
    name: str
    status: str                      # DEPLOYABLE | BLOCKED | STAND_ASIDE
    legs: List[Leg] = field(default_factory=list)
    edge: Optional[float] = None     # vol-points x vega captured, Rs/unit
    thinnest_oi: Optional[float] = None
    why: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    tag: str = "I"
    # ── risk ──
    risk: str = ""                   # DEFINED | UNDEFINED | "" (not priced)
    max_loss: Optional[float] = None # Rs/unit; None when risk is UNDEFINED --
                                      # a naked structure has no fake ceiling
    breakevens: List[float] = field(default_factory=list)   # Rs, underlying
    # ── margin [I] -- a documented floor, never the broker's SPAN number ──
    margin_per_lot: Optional[float] = None
    margin_model: str = ""
    # ── score: edge per rupee at risk, not raw edge ──
    edge_per_margin: Optional[float] = None      # Rs earned / Rs of margin
    edge_per_max_loss: Optional[float] = None    # only when risk is DEFINED
    # ── sizing -- follows from stated capital, capped by liquidity ──
    lots: int = 0
    lots_per_cr: int = 0
    liquidity_note: str = ""
    # ── DIRECTION, WHICH EVERY VOL TRADE CARRIES WHETHER IT MEANS TO OR NOT ──
    # A vertical between two strikes is neutral in VOL and emphatically not
    # neutral in SPOT. Live on 2026-08-21 the "level-neutral" vertical carried
    # +0.359 delta a unit -- at 1,880 lots of 75 that is the exposure of about
    # 50,000 NIFTY units, several crore of direction nobody asked for, emitted
    # by a module that BLOCKS directional structures for want of a direction
    # view. A position whose largest risk goes unnamed is not a recommendation.
    net_delta: Optional[float] = None      # per unit of the underlying
    hedge_units: Optional[float] = None    # futures units that flatten it
    hedge_note: str = ""


@dataclass
class Decision:
    index: str
    expiry: str
    capital: float = DEFAULT_CAPITAL   # [I] stated capital sizing is built on
    lot_size: int = DEFAULT_LOT_SIZE   # units per lot
    lot_size_src: str = ""             # measured | assumed -- an [M]
                                       # when derived off the wire, an
                                       # [I] only when falling back
    regime: Regime = field(default_factory=Regime)
    fit_ok: bool = False
    fit_rmse: Optional[float] = None
    fit_n: int = 0
    parity_gap: Optional[float] = None
    candidates: List[Candidate] = field(default_factory=list)
    best: Optional[str] = None
    why: List[str] = field(default_factory=list)
    tag: str = "I"


# ── the regime ────────────────────────────────────────────────────────────

def _atm_straddle(strikes, spot):
    """ATM straddle price -- the market's own forecast of the day's range."""
    if not strikes or not spot:
        return None
    best = px = None
    for s in strikes or []:
        k = s.get("k")
        if not k:
            continue
        d = abs(float(k) - spot)
        if best is not None and d >= best:
            continue
        ce = (s.get("ce") or {}).get("ltp")
        pe = (s.get("pe") or {}).get("ltp")
        if ce and pe:
            best, px = d, float(ce) + float(pe)
    return px


def regime_from_chain(doc: Optional[dict]) -> Regime:
    """The dealers' gear, from what `chain_metrics` already publishes."""
    r = Regime()
    if not doc or not doc.get("ok"):
        r.why.append("no chain payload -- regime UNKNOWN, which is not the "
                     "same as neutral")
        return r
    # THE METRICS ARE NESTED, AND READING THEM FLAT COSTS EVERYTHING. The chain
    # payload puts spot and strikes at the top level but flip_px, gex_total and
    # max_pain under `metrics`. Read flat, all three come back None, the regime
    # is UNKNOWN, and every premium structure in the catalog is BLOCKED -- a
    # total silence caused by one nesting level, wearing the face of an honest
    # "no regime yet". Found on the first live chain, not by a test. The
    # top-level fallback keeps an older or flattened payload working.
    m = doc.get("metrics") or {}
    r.spot = doc.get("spot")
    r.flip_px = m.get("flip_px", doc.get("flip_px"))
    r.gex = m.get("gex_total", doc.get("gex"))
    r.max_pain = m.get("max_pain", doc.get("max_pain"))
    r.expected_move = _atm_straddle(doc.get("strikes"), r.spot)

    # NO FLIP IS NOT NO INFORMATION. `flip_status: NO_CROSSING` means dealer
    # GEX never changes sign anywhere in the visible chain -- which is a
    # STRONGER statement than a flip, not a weaker one: the whole strike range
    # sits on one side of the gear. Positive throughout is damping everywhere;
    # negative throughout is amplifying everywhere. Treating that as UNKNOWN
    # blocked the entire catalog on the first live open, on three indices at
    # once, in exactly the condition selling premium wants.
    status = m.get("flip_status")
    if r.spot is not None and r.flip_px is not None:
        r.above_flip = r.spot > r.flip_px
    elif status == "NO_CROSSING" and r.gex is not None and r.gex != 0:
        r.above_flip = r.gex > 0
        r.why.append(
            f"no crossing in range: dealer GEX is "
            f"{'POSITIVE' if r.gex > 0 else 'NEGATIVE'} across every visible "
            f"strike, so the whole chain is on one side of the gear")
    if r.spot is None or r.above_flip is None:
        r.why.append("no gamma flip and no signed GEX -- cannot tell damping "
                     "from amplifying")
        return r
    r.state = "DAMPING" if r.above_flip else "AMPLIFYING"
    if r.flip_px is None:
        r.why.append("DAMPING everywhere in range" if r.above_flip
                     else "AMPLIFYING everywhere in range")
        return r
    r.why.append(
        f"spot {r.spot:,.0f} {'above' if r.above_flip else 'below'} flip "
        f"{r.flip_px:,.0f}: dealer hedging "
        + ("DAMPS range -- the condition selling premium wants"
           if r.above_flip else
           "AMPLIFIES the move -- selling here is short gamma into an "
           "amplifier"))
    if r.expected_move:
        r.why.append(f"ATM straddle {r.expected_move:,.0f} -- the market's own "
                     f"forecast of the day's range")
    return r


# ── structure helpers ─────────────────────────────────────────────────────

def _leg(p, side, f=None, t=None):
    d = (gamma.delta(f, p.k, p.iv, t, "C" if p.right == "CE" else "P")
         if f and t and p.iv else None)
    return Leg(side=side, strike=p.k, right=p.right, iv=p.iv,
               resid=p.resid, z=p.z, oi=p.oi, ltp=p.ltp, delta=d,
               vol=p.vol, bid=p.bid, ask=p.ask)


def _edge(legs: List[Leg], points) -> Optional[float]:
    """Vol-points of mispricing captured, weighted by each leg's vega.

    Selling a rich option captures its residual; buying a cheap one captures
    the negative of its negative residual. Both add. A DESCRIPTION of what is
    being harvested, not a forecast of what it pays.
    """
    by = {(p.k, p.right): p for p in points}
    tot = 0.0
    for l in legs:
        p = by.get((l.strike, l.right))
        if p is None or p.resid is None:
            return None
        tot += (p.vega * p.resid) * (1.0 if l.side == "SELL" else -1.0)
    return tot


def _thin(legs: List[Leg]) -> Optional[float]:
    ois = [l.oi for l in legs if l.oi is not None]
    return min(ois) if ois else None


def _liquidity_block(legs: List[Leg], edge_per_unit: Optional[float]
                     ) -> Optional[str]:
    """A leg whose OWN bid/ask spread outweighs the edge makes that edge
    unrecoverable even resting inside the spread -- posting there is a bet on
    the quote, not on the residual. `edge_per_unit=None` (the pin straddle,
    whose case is the regime rather than a residual) exempts the check rather
    than blocking on any positive spread against a near-zero edge. Silence --
    no bid/ask on the feed -- is not evidence of a bad quote and never blocks.
    """
    if edge_per_unit is None:
        return None
    for l in legs:
        if l.bid is None or l.ask is None or l.ask <= l.bid:
            continue
        spread = l.ask - l.bid
        if spread > MAX_SPREAD_VS_EDGE * abs(edge_per_unit):
            return (f"{l.strike:,.0f}{l.right} quotes {l.bid:g}/{l.ask:g} "
                    f"(spread Rs {spread:.2f}) against Rs {edge_per_unit:.2f}"
                    f"/unit edge -- the quote can swallow the edge before it "
                    f"is ever posted")
    return None


def _finish(c: Candidate, points) -> Candidate:
    """Price the structure, then apply the economic floor to it.

    The pin straddle is exempt: its case is the REGIME, not a residual, so it
    is allowed an edge near zero -- it says so in its own `why`. Everything
    else is a mispricing trade, and a mispricing worth less than a rupee a unit
    is not a trade however unusual the z-score says it is.
    """
    if c.status != "DEPLOYABLE" or not c.legs:
        return c
    c.edge = _edge(c.legs, points)
    c.thinnest_oi = _thin(c.legs)
    if c.name == "short_straddle_pin":
        # EXEMPT FROM THE FLOOR IS NOT LICENCE TO BE NEGATIVE. The pin's case
        # is the REGIME, so it may earn nothing from the surface and still
        # stand. But a NEGATIVE edge is the surface saying both legs trade
        # CHEAP to the curve -- the market is not paying for this straddle, it
        # is offering it. Selling below fair value on a pin hypothesis is an
        # argument for BUYING the straddle, not selling it.
        #
        # Shipped without this guard, the pin ranked BEST on two of three
        # indices at 11:11 IST on 2026-08-21, at Rs -0.90 and Rs -4.62 a unit.
        if c.edge is not None and c.edge < 0:
            c.status = "STAND_ASIDE"
            c.why = [f"both legs trade cheap to the curve "
                     f"(Rs {c.edge:.2f}/unit): the market is offering this "
                     f"straddle, not paying for it -- a pin hypothesis does "
                     f"not justify selling under fair value"]
            # LEGS KEPT ON PURPOSE. Showing what it would have sold, beside
            # the reason it is not being sold, is more use to a reader than an
            # empty row -- and it lets the risk classifier still label the
            # structure honestly as UNDEFINED.
        return c
    if c.edge is None or c.edge < MIN_EDGE_RS:
        got = "unpriceable" if c.edge is None else f"Rs {c.edge:.2f}/unit"
        c.status = "BLOCKED"
        c.missing = [f"captures {got}, under the Rs {MIN_EDGE_RS:.2f} floor"]
        c.legs, c.why = [], []
    return c


def _rich(points, right=None, atm=False):
    xs = [p for p in points
          if p.z is not None and p.z >= Z_EDGE
          and (right is None or p.right == right)
          and (not atm or abs(p.x) <= ATM_X)]
    return max(xs, key=lambda p: p.z) if xs else None


def _cheap(points, right=None):
    xs = [p for p in points
          if p.z is not None and p.z <= -Z_EDGE
          and (right is None or p.right == right)]
    return min(xs, key=lambda p: p.z) if xs else None


# ── the catalog ───────────────────────────────────────────────────────────

def _relative_value(surf, reg, points):
    """Sell the rich point, buy the cheap one on the SAME side.

    THE ONLY STRUCTURE HERE THAT NEEDS NO LEVEL VIEW. It is long and short the
    same wing, so whether vol overall is rich never enters -- which is exactly
    why it is honest on day one and an outright strangle is not.
    """
    c = Candidate("vertical_relative_value", "BLOCKED")
    # THE BEST PAIR, NOT THE FIRST ONE FOUND. Checking CE then PE and taking
    # whichever hit first picked a deep-OTM put spread over a near-money call
    # spread worth eight times as much, purely because "CE" sorted first.
    best = None
    for right in ("CE", "PE"):
        r, ch = _rich(points, right), _cheap(points, right)
        if r and ch and r.k != ch.k:
            legs = [_leg(r, "SELL", surf.f, surf.t),
                    _leg(ch, "BUY", surf.f, surf.t)]
            e = _edge(legs, points)
            if e is not None and (best is None or e > best[0]):
                best = (e, right, r, ch, legs)
    if best is None:
        c.missing = [f"no pair on one side with |z| >= {Z_EDGE} to trade "
                     f"against each other"]
        return c
    e, right, r, ch, legs = best
    if e < MIN_EDGE_RS:
        c.missing = [f"best pair captures only Rs {e:.2f}/unit, under the "
                     f"Rs {MIN_EDGE_RS:.2f} floor -- statistically off the "
                     f"curve, economically nothing"]
        return c
    c.status = "DEPLOYABLE"
    c.legs = legs
    c.why = [f"{right}: {r.k:,.0f} rich {r.resid * 100:+.2f} vol "
             f"(z {r.z:+.1f}), {ch.k:,.0f} cheap {ch.resid * 100:+.2f} "
             f"(z {ch.z:+.1f})",
             "VOL-neutral: needs no view on whether vol is rich, which is the "
             "view this stack cannot yet form. NOT spot-neutral -- see the "
             "net delta below and hedge it, or you are holding a direction "
             "this stack never formed a view on"]
    return c


def _wing_candidates(points, right, reg):
    """Points on `right` LEGAL to be a strangle/condor wing: rich AND far
    enough from spot to sit outside the expected move -- not merely the
    richest point on the curve, which is how a 12-point-from-spot PE got
    named a strangle wing on 2026-08-20."""
    if reg.spot is None or not reg.expected_move:
        return []
    return [p for p in points
            if p.right == right and p.z is not None and p.z >= Z_EDGE
            and abs(p.k - reg.spot) >= STRANGLE_MIN_MOVES * reg.expected_move]


def _short_strangle(surf, reg, points):
    c = Candidate("short_strangle", "BLOCKED")
    if reg.above_flip is None:
        c.missing = ["gamma flip unknown"]
        return c
    if not reg.above_flip:
        c.status = "STAND_ASIDE"
        c.why = ["below the flip, hedging amplifies -- this is the regime "
                 "that ends short-gamma books"]
        return c
    if reg.spot is None or not reg.expected_move:
        c.missing = ["expected move unavailable -- cannot judge whether a "
                     "wing sits outside it"]
        return c
    ces, pes = (_wing_candidates(points, "CE", reg),
                _wing_candidates(points, "PE", reg))
    if not (ces and pes):
        have = ", ".join(s for s, ok in (("CE", ces), ("PE", pes)) if ok)
        c.missing = [f"needs a rich point (z >= {Z_EDGE}) beyond "
                     f"{STRANGLE_MIN_MOVES:g} expected moves on BOTH sides; "
                     f"have {have or 'neither'}"]
        return c
    r_ce = max(ces, key=lambda p: p.z)
    r_pe = max(pes, key=lambda p: p.z)
    # A PAIR, NOT TWO UNRELATED SHORTS. Delta is the cross-strike ruler: two
    # legs the market itself prices at roughly the same "distance from the
    # money" are a strangle; two mismatched ones are a directional bet in a
    # market-neutral structure's clothes, and this stack has no direction view.
    d_ce = gamma.delta(surf.f, r_ce.k, r_ce.iv, surf.t, "C")
    d_pe = gamma.delta(surf.f, r_pe.k, r_pe.iv, surf.t, "P")
    if abs(abs(d_ce) - abs(d_pe)) > DELTA_BALANCE_TOL:
        c.missing = [f"wings not delta-balanced: {r_ce.k:,.0f}CE delta "
                     f"{d_ce:+.2f} vs {r_pe.k:,.0f}PE delta {d_pe:+.2f}, "
                     f"tolerance {DELTA_BALANCE_TOL:.2f}"]
        return c
    c.status = "DEPLOYABLE"
    c.legs = [_leg(r_ce, "SELL", surf.f, surf.t),
              _leg(r_pe, "SELL", surf.f, surf.t)]
    c.why = ["above the flip: hedging damps range",
             f"both wings rich and beyond {STRANGLE_MIN_MOVES:g} expected "
             f"moves: {r_ce.k:,.0f}CE z {r_ce.z:+.1f} delta {d_ce:+.2f}, "
             f"{r_pe.k:,.0f}PE z {r_pe.z:+.1f} delta {d_pe:+.2f}"]
    return c


def _iron_condor(surf, reg, points):
    c = Candidate("iron_condor", "BLOCKED")
    st = _short_strangle(surf, reg, points)
    if st.status != "DEPLOYABLE":
        c.status = st.status
        c.why = st.why
        c.missing = st.missing or ["the short strangle body"]
        return c
    body_ce, body_pe = st.legs[0], st.legs[1]
    w_ce = _cheap([p for p in points
                   if p.right == "CE" and p.k > body_ce.strike])
    w_pe = _cheap([p for p in points
                   if p.right == "PE" and p.k < body_pe.strike])
    if not (w_ce and w_pe):
        c.missing = ["no cheap wing beyond the body on both sides -- a wing "
                     "bought at fair value is insurance, not edge"]
        return c
    c.status = "DEPLOYABLE"
    c.legs = [body_ce, body_pe, _leg(w_ce, "BUY", surf.f, surf.t),
              _leg(w_pe, "BUY", surf.f, surf.t)]
    c.why = st.why + [f"wings cheap: {w_ce.k:,.0f}CE z {w_ce.z:+.1f}, "
                      f"{w_pe.k:,.0f}PE z {w_pe.z:+.1f} -- defined risk that "
                      f"is paid for rather than bought"]
    return c


def _pin_straddle(surf, reg, points):
    c = Candidate("short_straddle_pin", "BLOCKED")
    if reg.above_flip is None:
        c.missing = ["gamma flip unknown"]
        return c
    if not reg.above_flip:
        c.status = "STAND_ASIDE"
        c.why = ["below the flip -- nothing pins when hedging amplifies"]
        return c
    if reg.max_pain is None or reg.spot is None or not reg.expected_move:
        c.missing = ["max pain or expected move unavailable"]
        return c
    off = abs(reg.spot - reg.max_pain)
    if off > PIN_MOVES * reg.expected_move:
        c.status = "STAND_ASIDE"
        c.why = [f"spot is {off:,.0f} from max pain {reg.max_pain:,.0f}, more "
                 f"than {PIN_MOVES:g} expected moves -- too far to call a pin"]
        return c
    # BOTH LEGS, ALWAYS, OR IT IS NOT A STRADDLE. Selecting legs by richness
    # emitted a ONE-LEGGED "straddle" whenever only one side cleared the bar --
    # a naked short option wearing a straddle's name, which is the kind of
    # mislabel that gets someone hurt. The pin trade is justified by the
    # REGIME, not by richness; richness is supporting evidence. So the strike
    # is chosen by the pin and both legs are always sold.
    near = min((p for p in points), key=lambda p: abs(p.k - reg.max_pain),
               default=None)
    if near is None:
        c.missing = ["no usable strike near max pain"]
        return c
    k = near.k
    ce = next((p for p in points if p.k == k and p.right == "CE"), None)
    pe = next((p for p in points if p.k == k and p.right == "PE"), None)
    if not (ce and pe):
        # points_from_chain keeps only the OTM side of each strike, so the pin
        # strike yields one right. Take the nearest usable strike each side.
        ce = min((p for p in points if p.right == "CE"),
                 key=lambda p: abs(p.k - k), default=None)
        pe = min((p for p in points if p.right == "PE"),
                 key=lambda p: abs(p.k - k), default=None)
    if not (ce and pe):
        c.missing = ["no usable CE and PE either side of the pin"]
        return c
    c.status = "DEPLOYABLE"
    c.legs = [_leg(ce, "SELL", surf.f, surf.t), _leg(pe, "SELL", surf.f, surf.t)]
    c.why = [f"spot {reg.spot:,.0f} within {PIN_MOVES:g} expected moves of max "
             f"pain {reg.max_pain:,.0f}", "above the flip: hedging pins"]
    hot = [p for p in (ce, pe) if p.z is not None and p.z >= Z_EDGE]
    c.why.append(f"{len(hot)} of 2 legs also rich (z >= {Z_EDGE})"
                 if hot else "neither leg is rich -- the pin is the whole "
                             "case, and it is an [I]")
    return c


def _jade_lizard(surf, reg, points):
    """Short put + short call spread: no upside risk, when put skew pays."""
    c = Candidate("jade_lizard", "BLOCKED")
    # IT CAPS THE UPSIDE, NOT THE DOWNSIDE. The call spread removes the tail
    # above; the short put below is naked. An amplifying regime punishes
    # exactly that side, so this obeys the flip like every other premium
    # seller here -- "no upside risk" is not "no risk", and reading it that way
    # would put the one uncapped leg into the one regime built to run it over.
    if reg.above_flip is None:
        c.missing = ["gamma flip unknown"]
        return c
    if not reg.above_flip:
        c.status = "STAND_ASIDE"
        c.why = ["below the flip: the call spread caps the upside, but the "
                 "short put is naked into an amplifying regime"]
        return c
    if surf.fit.skew is None:
        c.missing = ["skew unavailable"]
        return c
    if surf.fit.skew <= 0:
        c.status = "STAND_ASIDE"
        c.why = [f"skew {surf.fit.skew * 100:+.2f} vol -- puts are not bid "
                 f"over calls, so there is no crowded side to sell"]
        return c
    pe, ce = _rich(points, "PE"), _rich(points, "CE")
    if not pe:
        c.missing = [f"no rich put (z >= {Z_EDGE}) to sell into the skew"]
        return c
    if not ce:
        c.missing = ["no rich call to build the financing spread"]
        return c
    above = [p for p in points if p.right == "CE" and p.k > ce.k]
    wing = _cheap(above) or (min(above, key=lambda p: p.k) if above else None)
    if not wing:
        c.missing = ["no call strike above the short call to cap the upside"]
        return c
    c.status = "DEPLOYABLE"
    c.legs = [_leg(pe, "SELL", surf.f, surf.t), _leg(ce, "SELL", surf.f, surf.t),
              _leg(wing, "BUY", surf.f, surf.t)]
    c.why = [f"put skew {surf.fit.skew * 100:+.2f} vol -- puts are the "
             f"crowded side",
             "capped upside: the call spread removes the tail the naked "
             "version carries"]
    return c


# Structures whose inputs this stack does not produce. Named explicitly rather
# than omitted: a missing row reads as "not considered", while a BLOCKED row
# with a reason reads as "considered, and here is the gap".
_UNSUPPORTED = [
    ("calendar", ["a second expiry: surface.read fits ONE expiry at a time"]),
    ("diagonal", ["a second expiry"]),
    ("bull_put_spread", ["a direction view -- nothing in this stack computes "
                         "bullish or bearish"]),
    ("bear_call_spread", ["a direction view"]),
    ("risk_reversal", ["a direction view"]),
    ("strip_strap", ["a direction view"]),
    ("ratio_backspread", ["a margin model for undefined-risk leg ratios"]),
    ("box", ["execution certainty across four legs; parity_gap exists but "
             "nothing prices the trade"]),
]

_ORDER = {"DEPLOYABLE": 0, "STAND_ASIDE": 1, "BLOCKED": 2}


# ── risk, per structure shape ──────────────────────────────────────────────
#
# Each function prices ONE known leg layout (the catalog above builds exactly
# these shapes, in exactly this leg order) into (max_loss, risk, breakevens,
# margin_per_lot, margin_model). `max_loss` and `margin_per_lot` are Rs per
# LOT; everything upstream of here is Rs per unit.

def _costs(legs: List[Leg]) -> float:
    """Statutory-only cost of the legs SOLD, Rs/unit. She posts rather than
    crosses, so there is no spread cost to model -- only STT + exchange +
    GST on the exchange leg, which apply to premium sold, not premium paid."""
    return sum((l.ltp or 0.0) * STATUTORY_PCT for l in legs if l.side == "SELL")


def _naked_margin(f: float, lot_size: int, n_naked_legs: int) -> float:
    """A documented FLOOR for `n_naked_legs` naked index legs -- see
    NAKED_MARGIN_PCT above for the model and why it is not SPAN."""
    if n_naked_legs <= 0 or not f:
        return 0.0
    notional = f * lot_size
    return (NAKED_MARGIN_PCT * notional
            * (1.0 + (n_naked_legs - 1) * NAKED_EXTRA_LEG_FRAC))


_NAKED_MODEL_NOTE = (
    f"[I] naked-leg floor: {NAKED_MARGIN_PCT:.0%} of notional (forward x lot "
    f"size) per naked leg, +{NAKED_EXTRA_LEG_FRAC:.0%} more for each "
    f"additional naked leg on the book -- NOT the broker's SPAN number, which "
    f"this stack cannot compute")


def _risk_vertical(legs, f, lot_size):
    """SELL near / BUY far, same right: defined risk between the two strikes."""
    sell, buy = legs
    width = abs(sell.strike - buy.strike)
    credit = (sell.ltp or 0.0) - (buy.ltp or 0.0) - _costs(legs)
    max_loss = max(width - credit, 0.0)
    be = [sell.strike + credit if sell.right == "CE" else sell.strike - credit]
    return (max_loss, "DEFINED", be, max_loss * lot_size,
            "[I] defined-risk floor: max loss x lot size")


def _risk_naked_pair(legs, f, lot_size):
    """Both legs sold naked (strangle, pin straddle): unbounded risk."""
    credit = sum(l.ltp or 0.0 for l in legs) - _costs(legs)
    ce = next((l for l in legs if l.right == "CE"), None)
    pe = next((l for l in legs if l.right == "PE"), None)
    be = sorted(x for x in (
        (ce.strike + credit) if ce is not None else None,
        (pe.strike - credit) if pe is not None else None) if x is not None)
    return None, "UNDEFINED", be, _naked_margin(f, lot_size, 2), _NAKED_MODEL_NOTE


def _risk_condor(legs, f, lot_size):
    """SELL body (CE, PE) / BUY wings beyond it: defined risk both sides."""
    body_ce, body_pe, wing_ce, wing_pe = legs
    call_w = wing_ce.strike - body_ce.strike
    put_w = body_pe.strike - wing_pe.strike
    credit = ((body_ce.ltp or 0.0) - (wing_ce.ltp or 0.0)
              + (body_pe.ltp or 0.0) - (wing_pe.ltp or 0.0) - _costs(legs))
    max_loss = max(call_w - credit, put_w - credit, 0.0)
    be = sorted([body_ce.strike + credit, body_pe.strike - credit])
    return (max_loss, "DEFINED", be, max_loss * lot_size,
            "[I] defined-risk floor: max loss x lot size")


def _risk_jade_lizard(legs, f, lot_size):
    """SELL put (naked) + SELL call / BUY wing above it (defined).

    IT CAPS THE UPSIDE, NOT THE DOWNSIDE. The naked put makes the STRUCTURE's
    own risk UNDEFINED even though the call side is priced -- reporting a max
    loss here would read as the whole position's ceiling when it is only the
    capped upside's. Margin still adds the call spread's own defined loss on
    top of the naked put's floor, because that loss is real capital at risk
    even though it is bounded.
    """
    pe, ce, wing = legs
    call_w = wing.strike - ce.strike
    credit = (pe.ltp or 0.0) + (ce.ltp or 0.0) - (wing.ltp or 0.0) - _costs(legs)
    upside_loss = max(call_w - credit, 0.0)
    be = [pe.strike - credit]
    if upside_loss > 0:
        be.append(ce.strike + credit)
    margin = _naked_margin(f, lot_size, 1) + upside_loss * lot_size
    model = ("[I] naked put floor (see above) + the call spread's own "
             "defined loss x lot size -- NOT SPAN")
    return None, "UNDEFINED", sorted(be), margin, model


_RISK_MODEL = {
    "vertical_relative_value": _risk_vertical,
    "short_strangle": _risk_naked_pair,
    "iron_condor": _risk_condor,
    "short_straddle_pin": _risk_naked_pair,
    "jade_lizard": _risk_jade_lizard,
}


def _delta_book(c: Candidate, f: float, t: float, lot_size: int) -> None:
    """Net delta of the structure, and the futures that would flatten it.

    NEUTRAL IN VOL IS NOT NEUTRAL IN SPOT. A desk running a vol book hedges the
    delta out with futures and keeps only the vega it wanted; a reader handed
    the legs without this number is handed a directional bet by omission.
    `hedge_units` is what to trade in the future to reach flat -- negative means
    SELL futures. It is stated, never executed: this stack has no order path.
    """
    if not c.legs or not f or not t or t <= 0:
        return
    net = 0.0
    for l in c.legs:
        if l.iv is None:
            return                      # one unpriceable leg makes the sum a lie
        d = gamma.delta(f, l.strike, l.iv, t, "C" if l.right == "CE" else "P")
        net += d * (-1.0 if l.side == "SELL" else 1.0)
    c.net_delta = round(net, 4)
    units = net * max(c.lots, 0) * lot_size
    c.hedge_units = round(-units, 1)
    if abs(net) < 0.05:
        c.hedge_note = (f"net delta {net:+.3f}/unit -- already close to flat, "
                        f"no futures hedge worth paying for")
    else:
        c.hedge_note = (
            f"net delta {net:+.3f}/unit. At {c.lots} lots this is "
            f"{units:+,.0f} units of underlying exposure -- "
            f"{'SELL' if units > 0 else 'BUY'} {abs(units):,.0f} units "
            f"({abs(units) / lot_size:,.0f} lots) of the future to hold the "
            f"vol and drop the direction.")


def _score(c: Candidate, lot_size: int) -> None:
    """Edge per rupee AT RISK, not raw edge -- the real score. `edge` is
    Rs/unit; margin and max loss are Rs/lot, so edge is scaled by lot size to
    match before dividing."""
    if c.margin_per_lot:
        c.edge_per_margin = ((c.edge or 0.0) * lot_size) / c.margin_per_lot
    if c.risk == "DEFINED" and c.max_loss:
        c.edge_per_max_loss = (c.edge or 0.0) / c.max_loss


def _size(c: Candidate, capital: float, lot_size: int) -> None:
    """Lots that follow from stated capital, capped by the thinnest leg's own
    liquidity -- never just a label on the reading."""
    if not c.margin_per_lot or c.margin_per_lot <= 0:
        return
    c.lots_per_cr = int(ONE_CRORE // c.margin_per_lot)
    by_capital = int(capital // c.margin_per_lot)
    by_liquidity = (int((LIQUIDITY_OI_FRAC * c.thinnest_oi) // lot_size)
                    if c.thinnest_oi else 0)
    c.lots = max(0, min(by_capital, by_liquidity))
    if c.lots == 0:
        binding = "capital" if by_capital <= by_liquidity else \
                  "the thinnest leg's own liquidity"
        c.liquidity_note = (f"sized to 0 lots -- {binding} is the binding "
                             f"constraint (capital allows {by_capital}, "
                             f"liquidity allows {by_liquidity})")
    elif by_liquidity < by_capital:
        c.liquidity_note = (f"capped by the thinnest leg's liquidity: "
                             f"{LIQUIDITY_OI_FRAC:.0%} of {c.thinnest_oi:,.0f} "
                             f"OI allows {by_liquidity} lots vs {by_capital} "
                             f"lots by capital")


def _price(c: Candidate, f: float, t: float, lot_size: int,
           capital: float) -> Candidate:
    """After `_finish` has priced the edge and cleared the economic floor:
    liquidity, risk, margin, score, size. Runs only on a still-DEPLOYABLE
    candidate this stack has a risk model for."""
    if not c.legs:
        return c
    model = _RISK_MODEL.get(c.name)
    if model is None:
        return c
    # RISK IS A PROPERTY OF THE STRUCTURE, NOT OF OUR OPINION OF IT. A
    # stand-aside straddle is still naked both sides, and a reader looking at
    # why we declined it should see that -- so the risk classification runs on
    # anything with legs. Only the liquidity check, the score and the sizing
    # are gated on still wanting to trade it.
    c.max_loss, c.risk, c.breakevens, c.margin_per_lot, c.margin_model = \
        model(c.legs, f, lot_size)
    if c.status != "DEPLOYABLE":
        return c
    # PIN STRADDLE IS EXEMPT HERE TOO: its edge is allowed near zero (its case
    # is the regime), so the liquidity check is exempted the same way the
    # economic floor is -- checking a near-zero edge against ANY spread would
    # block it on noise, not on a real problem.
    note = _liquidity_block(
        c.legs, None if c.name == "short_straddle_pin" else c.edge)
    if note:
        c.status, c.missing = "BLOCKED", [note]
        c.legs, c.why = [], []
        return c
    _score(c, lot_size)
    _size(c, capital, lot_size)
    # LAST, because the hedge is quoted at the size actually recommended.
    _delta_book(c, f, t, lot_size)
    return c


def decide(surf, reg: Regime, capital: float = DEFAULT_CAPITAL,
           lot_size: Optional[int] = None, strikes=None) -> Decision:
    """One surface + one regime -> every structure, with a status each.

    `capital` is the Rs of margin capital the sizing is built against
    (default Rs 5cr). `lot_size` defaults from LOT_SIZE by index -- see its
    caveat above; pass it explicitly once the live contract note is checked.
    """
    # MEASURE IT, DO NOT ASSUME IT. The GCD of the chain's own oi/vol is
    # the lot size exactly; the table is only a fallback for a chain too
    # thin to derive from.
    src = "given"
    if lot_size is None:
        # ONLY from a real chain. Deriving off the fitted points would use
        # OI alone from one side of each strike -- too thin a sample, and a
        # wrong answer there would carry a "measured" label.
        lot_size = lot_size_from_chain(strikes)
        src = "measured"
    if not lot_size:
        lot_size = LOT_SIZE.get(surf.index, DEFAULT_LOT_SIZE)
        src = "assumed"
    d = Decision(index=surf.index, expiry=surf.expiry, capital=capital,
                 lot_size=lot_size, lot_size_src=src, regime=reg,
                 fit_ok=surf.fit.ok, fit_rmse=surf.fit.rmse,
                 fit_n=surf.fit.n, parity_gap=surf.parity_gap)
    if src == "assumed":
        d.why.append(f"lot size {lot_size} is ASSUMED [I] -- the chain was too "
                     f"thin to measure it from. Every sizing figure below "
                     f"rides on it; confirm before acting.")
    if not surf.fit.ok:
        d.why.append("no fitted surface -- " + (surf.fit.why or "unknown"))
        d.candidates = [Candidate(n, "BLOCKED", missing=["a fitted surface"])
                        for n, _ in _UNSUPPORTED]
        return d

    pts = [p for p in surf.points if p.z is not None]
    built = [_relative_value(surf, reg, pts), _short_strangle(surf, reg, pts),
             _iron_condor(surf, reg, pts), _pin_straddle(surf, reg, pts),
             _jade_lizard(surf, reg, pts)]
    d.candidates = [_price(_finish(c, surf.points), surf.f, surf.t,
                           lot_size, capital)
                    for c in built]
    d.candidates += [Candidate(n, "BLOCKED", missing=m)
                     for n, m in _UNSUPPORTED]

    live = [c for c in d.candidates
            if c.status == "DEPLOYABLE" and c.edge is not None]
    live.sort(key=lambda c: -(c.edge_per_margin
                              if c.edge_per_margin is not None else
                              float("-inf")))
    # A BELT AGAINST THE BRACES. `best` is the one field a reader acts on, so
    # it never names a structure that earns nothing: even if some future
    # candidate slips past its own floor, a non-positive edge cannot be "best".
    d.best = next((c.name for c in live
                   if (c.edge_per_margin or 0.0) > 0), None)
    d.candidates.sort(key=lambda c: (_ORDER[c.status],
                                     -(c.edge_per_margin or 0.0)))
    if not live:
        d.why.append("nothing deployable: the surface and the regime do not "
                     "currently agree on any structure this stack can build")
    d.why.append("status, NOT confidence. `edge` describes the mispricing "
                 "being harvested; it does not forecast what it pays, and "
                 "nothing here has a track record. Ranked by edge per rupee "
                 "of margin -- an [I] model, never the broker's SPAN.")
    d.why += surf.why
    return d
