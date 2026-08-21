"""surface.py -- the volatility surface, and which points on it are rich.

WHAT IT ANSWERS. An option chain is not a list of prices; it is one curve
sampled at strikes. Fit the curve and every point has a residual: trading above
the curve is rich, below is cheap. That residual is the edge a vol desk sells,
and it is what turns "which strategy" from a menu into a search -- calendars,
skew trades, flies and condors are all just different ways of being short the
rich points and long the cheap ones.

TWO KINDS OF RICH, AND ONLY ONE IS AVAILABLE ON DAY ONE.

  CROSS-SECTIONAL   this point vs the rest of TODAY's surface. Needs one
                    snapshot. Available immediately -- it is `resid` / `z`.
  TIME-SERIES       this point vs its OWN history. Needs days of forward log.
                    Absent until the log fills, and says so rather than
                    pretending.

Shipping only the second would mean a tool that does nothing for a month. The
first is genuinely useful alone: it says WHERE on the surface to trade even
when it cannot yet say whether the whole surface is rich.

THE FIT'S COEFFICIENTS ARE THE SURFACE DESCRIPTORS. Fitting
`iv = a + b*x + c*x^2` in log-moneyness `x = ln(K/F)` gives them directly:

    a   ATM vol (the curve at x=0)
    b   SKEW -- a downward-sloping curve means puts bid over calls
    c   CONVEXITY -- how fast the wings lift; the smile itself

So skew and smile are not separate calculations bolted on. They fall out of one
fit, which is why term structure and skew stop being separate playbooks.

OTM ONLY, AND VEGA-WEIGHTED. An ITM option trades near intrinsic, leaving the
solver almost no time value to fit, so its IV is noise -- the same failure
`chain_metrics._sane_iv` exists to gate. Using OTM calls above the forward and
OTM puts below avoids it by construction. The fit is then weighted by vega,
because a far wing with negligible vega must not drag a curve that ATM size
actually trades on.

THE FORWARD, NOT SPOT. `gamma.py` is Black-76 on a forward. Passing spot where
a forward belongs biases every log-moneyness and tilts the whole fitted skew,
which would then be read as a market view. When the future's price is not
available the caller may pass spot, and `f_src` records that it did.

Pure computation, stdlib only, no I/O. Emits `[M]` for measured IVs and
residuals; the fit itself is `[I]` -- a quadratic is a choice about the world.

KILL CONDITION. If, after ~20 forward sessions, points ranked rich do not decay
more than points ranked cheap, this module is deleted rather than tuned. A
surface that cannot separate the two is an expensive way to redraw the chain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import gamma

# Indian markets settle at 15:30 IST. Declared here rather than imported so
# this module stays stdlib-only and I/O-free like its siblings.
IST = timezone(timedelta(hours=5, minutes=30))
CLOSE_H, CLOSE_M = 15, 30

# A YEAR OF WHAT. Time to expiry is quoted in CALENDAR years because that is
# what Black-76 wants and what the feed's own IV is quoted against; using
# trading days here would silently reprice every option relative to the number
# the exchange publishes.
YEAR = 365.0

# A fit needs enough points that a quadratic is not merely interpolating noise.
MIN_POINTS = 6

# An IV we believe. Mirrors chain_metrics._sane_iv's intent: a solve outside
# this bracket, or on an option with no time value left, is garbage that used
# to propagate into gamma and the flip.
IV_MAX = 3.0
MIN_TV = 0.05          # minimum time value (price - intrinsic) to trust an IV

# How far the feed's IV may sit from our own inversion before we stop believing
# it. A broker-derived number we cannot reproduce is not a measurement, it is
# someone else's opinion.
IV_TOL = 0.02          # 2 vol points

# Where skew is quoted from the fitted curve: +/- this in log-moneyness. A
# fixed MONEYNESS, not a fixed strike offset, so NIFTY and BANKNIFTY stay
# comparable despite different strike spacing.
SKEW_X = 0.03

# How far out the curve is fitted, in EXPECTED MOVES either side of the
# forward.
#
# VEGA WEIGHTING ALONE IS NOT ENOUGH, which a test proved rather than a theory
# predicted: one junk print 1,500 points out moved the fitted convexity from
# 4.0 to 139 and ATM vol by 1.2 vol points, despite carrying almost no vega. In
# a quadratic a point at large |x| has enormous leverage on the x^2 term, and
# down-weighting it does not remove that leverage.
#
# So the curve is fitted only where it is actually traded. The width is
# self-calibrating -- expected move is `iv * sqrt(T)`, seeded from the measured
# IV nearest the money -- so a quiet day fits a narrow curve and a wild one a
# wide curve, with no absolute constant to tune per index.
FIT_MOVES = 3.0


@dataclass
class Point:
    """One OTM option, and how far off the fitted curve it trades."""
    k: float
    right: str                      # CE | PE
    x: float                        # log-moneyness ln(K/F)
    iv: float                       # the IV we believe  [M]
    iv_src: str                     # agreed | derived
    ltp: float
    oi: float
    vega: float
    vol: Optional[float] = None     # today's traded volume, for liquidity  [M]
    bid: Optional[float] = None     # top-of-book bid                      [M]
    ask: Optional[float] = None     # top-of-book ask                      [M]
    fit_iv: Optional[float] = None  # the curve at this x   [I]
    resid: Optional[float] = None   # iv - fit_iv, vol points -- RICH if > 0
    z: Optional[float] = None       # resid / rmse
    tag: str = "M"


@dataclass
class Fit:
    """The curve, whose coefficients are the surface's own descriptors."""
    atm_iv: Optional[float] = None      # a
    skew: Optional[float] = None        # fit(-SKEW_X) - fit(+SKEW_X)
    convexity: Optional[float] = None   # c
    rmse: Optional[float] = None
    n: int = 0
    excluded: int = 0                   # points outside the fitted window
    window_x: Optional[float] = None    # half-width in log-moneyness
    ok: bool = False
    why: str = ""
    tag: str = "I"


@dataclass
class SurfaceRead:
    index: str
    expiry: str
    f: Optional[float] = None
    f_src: str = "none"                  # future | spot
    t: Optional[float] = None            # years to expiry
    fit: Fit = field(default_factory=Fit)
    points: List[Point] = field(default_factory=list)
    richest: List[Point] = field(default_factory=list)
    cheapest: List[Point] = field(default_factory=list)
    parity_gap: Optional[float] = None   # |CE IV - PE IV| nearest the forward
    disagreed: int = 0                   # legs whose feed IV we could not match
    why: List[str] = field(default_factory=list)
    tag: str = "M"


# ── the clock ─────────────────────────────────────────────────────────────

def years_to_expiry(expiry: str, now: Optional[datetime] = None
                    ) -> Optional[float]:
    """Calendar years from now to 15:30 IST on the expiry date.

    ALWAYS IST, NEVER THE LOCAL CLOCK. This machine runs 5.5 hours ahead of
    IST, so a naive `datetime.now()` would place the desk in tomorrow from
    18:30 IST onward and misprice every option by a day. `chain_live` and
    `instruments` already take this care; so does this.

    Returns None on an unparseable date, and 0.0 once expiry has passed --
    never a negative, which would put an imaginary number inside the solver.
    """
    if not expiry:
        return None
    try:
        d = datetime.strptime(str(expiry)[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return None
    settle = datetime(d.year, d.month, d.day, CLOSE_H, CLOSE_M, tzinfo=IST)
    now = now or datetime.now(IST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    return max((settle - now).total_seconds() / 86400.0 / YEAR, 0.0)


# ── linear algebra, 3x3, stdlib only ──────────────────────────────────────

def _solve3(a: List[List[float]], b: List[float]) -> Optional[List[float]]:
    """Gaussian elimination with partial pivoting. None if singular."""
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(3):
        p = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[p][col]) < 1e-12:
            return None
        m[col], m[p] = m[p], m[col]
        for r in range(3):
            if r == col:
                continue
            f = m[r][col] / m[col][col]
            for cc in range(col, 4):
                m[r][cc] -= f * m[col][cc]
    return [m[i][3] / m[i][i] for i in range(3)]


def _wls_quad(xs, ys, ws) -> Optional[Tuple[float, float, float, float]]:
    """Weighted least squares for y = a + b*x + c*x^2. -> (a, b, c, rmse)."""
    s = [0.0] * 5
    t = [0.0] * 3
    for x, y, w in zip(xs, ys, ws):
        xp = 1.0
        for i in range(5):
            s[i] += w * xp
            xp *= x
        t[0] += w * y
        t[1] += w * x * y
        t[2] += w * x * x * y
    coef = _solve3([[s[0], s[1], s[2]],
                    [s[1], s[2], s[3]],
                    [s[2], s[3], s[4]]], t)
    if coef is None:
        return None
    a, b, c = coef
    den = sum(ws)
    if den <= 0:
        return None
    num = sum(w * (y - (a + b * x + c * x * x)) ** 2
              for x, y, w in zip(xs, ys, ws))
    return a, b, c, math.sqrt(num / den)


# ── the IV we believe ─────────────────────────────────────────────────────

def believable_iv(leg: dict, k: float, f: float, t: float,
                  right: str) -> Tuple[Optional[float], str]:
    """The feed's IV, our own inversion, or None with the reason.

    The feed's `iv` is a number we did not derive. It is accepted only when our
    own Black-76 inversion of the same price agrees; otherwise the inversion
    wins, and if that fails too the point is dropped. A surface built on IVs we
    cannot reproduce is a surface built on someone else's model.
    """
    ltp = leg.get("ltp")
    if not ltp or ltp <= 0 or t <= 0 or f <= 0 or k <= 0:
        return None, "no price"
    intrinsic = max(f - k, 0.0) if right == "CE" else max(k - f, 0.0)
    if ltp - intrinsic < MIN_TV:
        return None, "no time value left to fit"

    ours = gamma.implied_vol(ltp, f, k, t, "C" if right == "CE" else "P")
    feed = leg.get("iv")
    if feed is not None and 0 < feed <= IV_MAX:
        if ours is not None and abs(ours - feed) <= IV_TOL:
            return feed, "agreed"
        if ours is not None:
            return ours, "derived"        # reproducible beats authoritative
        return None, "feed iv unreproducible"
    if ours is not None and 0 < ours <= IV_MAX:
        return ours, "derived"
    return None, "unsolvable"


# ── the surface ───────────────────────────────────────────────────────────

def points_from_chain(strikes, f: float, t: float) -> Tuple[List[Point], int]:
    """OTM legs only -> believable points. Returns (points, n_unreproducible)."""
    out: List[Point] = []
    bad = 0
    for s in strikes or []:
        k = s.get("k")
        if not k or float(k) <= 0:
            continue
        k = float(k)
        # OTM by construction: calls above the forward, puts below. ITM legs
        # trade near intrinsic and their IVs are noise.
        right = "CE" if k > f else "PE"
        leg = s.get(right.lower()) or {}
        iv, src = believable_iv(leg, k, f, t, right)
        if iv is None:
            if src == "feed iv unreproducible":
                bad += 1
            continue
        out.append(Point(k=k, right=right, x=math.log(k / f), iv=iv,
                         iv_src=src, ltp=float(leg.get("ltp") or 0.0),
                         oi=float(leg.get("oi") or 0.0),
                         vega=gamma.vega(f, k, iv, t),
                         vol=leg.get("vol"), bid=leg.get("bid"),
                         ask=leg.get("ask")))
    return out, bad


def fit_window(points: List[Point], t: float) -> Optional[float]:
    """Half-width of the fitted moneyness window, in expected moves.

    Seeded from the MEASURED IV nearest the money rather than from a fit, so
    there is no circularity -- the window does not need the curve it defines.
    """
    if not points or t <= 0:
        return None
    atm = min(points, key=lambda p: abs(p.x))
    return FIT_MOVES * atm.iv * math.sqrt(t)


def fit_smile(points: List[Point], t: float) -> Fit:
    """Vega-weighted quadratic in log-moneyness, over the traded window."""
    live = [p for p in points if p.vega > 0]
    win = fit_window(live, t)
    usable = [p for p in live if win is None or abs(p.x) <= win]
    excluded = len(live) - len(usable)
    if len(usable) < MIN_POINTS:
        return Fit(n=len(usable), excluded=excluded, window_x=win,
                   why=f"{len(usable)} points inside the {FIT_MOVES:g}-move "
                       f"window, need {MIN_POINTS}")
    got = _wls_quad([p.x for p in usable], [p.iv for p in usable],
                    [p.vega for p in usable])
    if got is None:
        return Fit(n=len(usable), excluded=excluded, window_x=win,
                   why="fit is singular -- strikes degenerate")
    a, b, c, rmse = got
    lo = a + b * -SKEW_X + c * SKEW_X ** 2
    hi = a + b * SKEW_X + c * SKEW_X ** 2
    return Fit(atm_iv=a, skew=lo - hi, convexity=c, rmse=rmse,
               n=len(usable), excluded=excluded, window_x=win, ok=True,
               why=f"vega-weighted quadratic over {len(usable)} OTM points "
                   f"within {FIT_MOVES:g} expected moves")


def _parity_gap(strikes, f: float, t: float) -> Optional[float]:
    """|CE IV - PE IV| at the strike nearest the forward.

    Both should price the same vol. A wide gap means one leg is stale or
    mismarked, and any surface built on it is suspect -- so it is reported
    rather than silently averaged away.
    """
    best = None
    gap = None
    for s in strikes or []:
        k = s.get("k")
        if not k:
            continue
        k = float(k)
        d = abs(k - f)
        if best is not None and d >= best:
            continue
        ce, _ = believable_iv(s.get("ce") or {}, k, f, t, "CE")
        pe, _ = believable_iv(s.get("pe") or {}, k, f, t, "PE")
        if ce is not None and pe is not None:
            best, gap = d, abs(ce - pe)
    return gap


def read(index: str, expiry: str, strikes, f: Optional[float],
         t: Optional[float], f_src: str = "future",
         top: int = 3) -> SurfaceRead:
    """One chain snapshot -> the fitted surface and its rich/cheap points.

    `t` is years to expiry. `f` is the FORWARD (the future's price); pass spot
    only with f_src="spot", which records that the moneyness is approximate.
    """
    r = SurfaceRead(index=index, expiry=expiry, f=f, t=t, f_src=f_src)
    if not f or not t or t <= 0 or not strikes:
        r.why.append("no forward or no time to expiry -- nothing to fit")
        return r
    if f_src != "future":
        r.why.append("moneyness measured off SPOT, not the forward: the "
                     "fitted skew is tilted by the basis")

    r.points, r.disagreed = points_from_chain(strikes, f, t)
    r.parity_gap = _parity_gap(strikes, f, t)
    r.fit = fit_smile(r.points, t)
    if not r.fit.ok:
        r.why.append(r.fit.why)
        return r
    if r.fit.excluded:
        r.why.append(f"{r.fit.excluded} points sat outside the "
                     f"{FIT_MOVES:g}-expected-move window and did not steer "
                     f"the curve; their residuals are extrapolated")

    a, c = r.fit.atm_iv, r.fit.convexity
    b = -(r.fit.skew / (2.0 * SKEW_X))
    for p in r.points:
        p.fit_iv = a + b * p.x + c * p.x * p.x
        p.resid = p.iv - p.fit_iv
        p.z = (p.resid / r.fit.rmse) if r.fit.rmse else None

    ranked = sorted([p for p in r.points if p.z is not None], key=lambda p: p.z)
    r.cheapest = ranked[:top]
    r.richest = list(reversed(ranked[-top:]))

    if r.disagreed:
        r.why.append(f"{r.disagreed} legs had a feed IV we could not "
                     f"reproduce; they were dropped")
    if r.parity_gap is not None and r.parity_gap > IV_TOL * 2:
        r.why.append(f"put-call parity gap {r.parity_gap:.3f} at the touch -- "
                     f"one leg may be stale")
    # THE HALF THIS CANNOT ANSWER YET. Everything above is cross-sectional:
    # rich RELATIVE TO TODAY'S OWN CURVE. Whether the whole curve is rich needs
    # days of forward log, which does not exist yet.
    r.why.append("cross-sectional only: whether the WHOLE surface is rich "
                 "needs multi-day history the forward log has not accumulated")
    return r
