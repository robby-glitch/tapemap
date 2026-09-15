"""book.py -- the risk core: the position book the desk never had.

WHY IT EXISTS. Every module before this one was eyes. A desk is hands first:
what am I holding, what are its greeks, how much margin is it eating, how far
am I from being FORCED, and -- after the day -- WHICH of theta/gamma/vega/
direction made or lost the money. Signals decide when to press; this decides
whether pressing is survivable and what pressing actually earned. Built for
the PAPER desk (trader.py): no real capital, no order path, ever.

DISTANCE-TO-FORCED IS THE FIRST-CLASS NUMBER. The hunt kills through margin,
not through opinion (the crowd doctrine, rule 5): SPAN rises exactly when the
loss mounts. So the book's headline is not P&L -- it is "what multiple of
stress can this book absorb before ANY action is forced". Computed against a
declared stress (margin doubling + an adverse expected-move on the net
delta/gamma), all [I] and labeled: a real SPAN engine would disagree in
detail and agree in shape.

ATTRIBUTION IS [I] AND SAYS SO. Per leg the book stores entry spot, IV and
delta/vega; a mark decomposes P&L into delta x dS, vega x dIV, and a residual
that is theta+gamma+higher-order together. Crude, first-order, and exactly
enough to answer the only daily question that compounds: did the money come
from where the thesis said it would?

MARKS ARE MID WHEN TWO-SIDED, LTP OTHERWISE, AND THE MARK SAYS WHICH. A
one-sided book cannot produce an honest mid; pretending otherwise marks the
book at a price nobody is showing.

THE MARGIN MODEL IS desk.py's, reused not re-invented: 11% of notional per
naked leg, +60% per extra leg, premium for long-only books -- a documented
shape, not SPAN, and every reading carries that caveat.

Pure computation, stdlib only, no I/O. trader.py owns the disk.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

import desk as desk_mod

# --- the [I] layer ----------------------------------------------------------
STRESS_MARGIN_X = 2.0   # stress: margin doubles (an IV spike's SPAN shape)
STRESS_MOVE_EM = 1.0    # ...while spot moves one expected-move against us


@dataclass
class PaperLeg:
    strike: Optional[float]      # None for FUT
    right: str                   # CE | PE | FUT
    side: str                    # BUY | SELL
    qty: int                     # units (lots x lot_size), always positive
    entry_px: float
    entry_ts: str
    mode: str = "maker"          # maker (posted) | taker (crossed)
    # entry-time context for attribution, [I]
    iv0: Optional[float] = None
    delta0: Optional[float] = None
    vega0: Optional[float] = None
    exit_px: Optional[float] = None
    exit_ts: Optional[str] = None
    exit_mode: Optional[str] = None


@dataclass
class Position:
    pid: str
    idx: str
    strategy: str
    lots: int
    legs: List[PaperLeg] = field(default_factory=list)
    opened_ts: str = ""
    state: str = "OPEN"          # OPEN | CLOSED
    closed_ts: Optional[str] = None
    spot0: Optional[float] = None
    # rule 9, filled at birth: who is forced, and why
    forced_who: str = ""
    forced_why: str = ""
    gear_at_entry: str = ""
    realized: Optional[float] = None   # rupees, set on close
    # exit policy the trader manages against (fractions of entry premium)
    policy: Dict[str, float] = field(default_factory=dict)
    # the session the position belongs to (YYYY-MM-DD); the chain's own ts
    # is clock-of-day only, so "closed today" is unanswerable without this
    day: Optional[str] = None


def _sgn(side: str) -> int:
    return 1 if side == "BUY" else -1


def mark_px(leg_quote: Optional[dict]) -> Tuple[Optional[float], str]:
    """(mark, src). Mid when two-sided, ltp otherwise, None with why never
    a zero."""
    q = leg_quote or {}
    bid, ask, ltp = q.get("bid"), q.get("ask"), q.get("ltp")
    if bid and ask and ask > bid:
        return (bid + ask) / 2.0, "mid"
    if ltp:
        return ltp, "ltp"
    return None, "no quote"


class Book:
    """The paper book: open/close positions, mark, aggregate risk."""

    def __init__(self, capital: float):
        self.capital = capital
        self.positions: List[Position] = []
        self.realized_total = 0.0
        self._next = 1

    # -- lifecycle -----------------------------------------------------------
    def open(self, idx: str, strategy: str, lots: int, legs: List[PaperLeg],
             ts: str, spot0: Optional[float], forced_who: str,
             forced_why: str, gear: str,
             policy: Optional[Dict[str, float]] = None) -> Position:
        p = Position(pid=f"P{self._next}", idx=idx, strategy=strategy,
                     lots=lots, legs=legs, opened_ts=ts, spot0=spot0,
                     forced_who=forced_who, forced_why=forced_why,
                     gear_at_entry=gear, policy=policy or {})
        self._next += 1
        self.positions.append(p)
        return p

    def close(self, p: Position, fills: Dict[int, Tuple[float, str]],
              ts: str) -> float:
        """fills: leg-index -> (exit_px, mode). Returns realized rupees."""
        total = 0.0
        for i, leg in enumerate(p.legs):
            px, mode = fills[i]
            leg.exit_px, leg.exit_ts, leg.exit_mode = px, ts, mode
            total += _sgn(leg.side) * (px - leg.entry_px) * leg.qty
        p.state, p.closed_ts, p.realized = "CLOSED", ts, round(total, 2)
        self.realized_total += total
        return total

    def open_positions(self) -> List[Position]:
        return [p for p in self.positions if p.state == "OPEN"]

    # -- marking -------------------------------------------------------------
    def mark_position(self, p: Position, by_k: Dict[tuple, dict],
                      spot: Optional[float]) -> dict:
        """One position's mark: unrealized, greeks, attribution. Every
        absent input is a stated absence."""
        unreal, why = 0.0, []
        net_delta = net_gamma = 0.0
        d_pnl = v_pnl = 0.0
        attributable = True
        # A leg whose delta did not arrive used to be skipped SILENTLY, so
        # `net_delta` came back a smaller number with no hint it was partial.
        # Harmless while nothing acted on it; not harmless once hedge.py sizes
        # a futures trade from it -- hedging an understated delta is how a
        # hedger becomes a random position generator. Named legs here, and the
        # hedger refuses rather than guessing.
        delta_why: List[str] = []
        for leg in p.legs:
            q = by_k.get((leg.strike, leg.right)) if leg.right != "FUT" else None
            if leg.right == "FUT":
                px, src = spot, "index [I: future not marked separately]"
            else:
                px, src = mark_px(q)
            if px is None:
                why.append(f"{leg.strike} {leg.right}: no quote to mark")
                attributable = False
                continue
            s = _sgn(leg.side)
            unreal += s * (px - leg.entry_px) * leg.qty
            d = (q or {}).get("delta") if leg.right != "FUT" else 1.0
            g = (q or {}).get("gamma") if leg.right != "FUT" else 0.0
            if d is not None:
                net_delta += s * d * leg.qty
            else:
                delta_why.append(f"{leg.strike} {leg.right}: no delta")
            if g is not None:
                net_gamma += s * g * leg.qty
            # attribution vs entry context, [I]
            iv = (q or {}).get("iv")
            if (leg.delta0 is not None and p.spot0 is not None
                    and spot is not None):
                d_pnl += s * leg.delta0 * (spot - p.spot0) * leg.qty
            else:
                attributable = False
            if leg.vega0 is not None and leg.iv0 is not None and iv is not None:
                v_pnl += s * leg.vega0 * (iv - leg.iv0) * leg.qty
            elif leg.right != "FUT":
                attributable = False
        out = {"pid": p.pid, "idx": p.idx, "strategy": p.strategy,
               "unrealized": round(unreal, 2),
               "net_delta": round(net_delta, 1),
               # Empty list = every leg contributed. Non-empty = `net_delta` is
               # a PARTIAL sum and must not be sized against.
               "delta_why": delta_why,
               "net_gamma": round(net_gamma, 4),
               "why": why}
        if attributable:
            out["attribution"] = {
                "delta": round(d_pnl, 2), "vega": round(v_pnl, 2),
                "theta_gamma_resid": round(unreal - d_pnl - v_pnl, 2),
                "tag": "I",
                "note": "first-order decomposition off entry greeks; the "
                        "residual bundles theta, gamma and everything higher"}
        else:
            out["attribution"] = None
            out["attribution_why"] = ("entry context or a live quote is "
                                      "missing; refusing a partial "
                                      "decomposition")
        return out

    # -- margin & the forced distance ---------------------------------------
    def margin_position(self, p: Position, spot: Optional[float],
                        lot_size: int) -> Tuple[Optional[float], str]:
        """Rupees of margin this position eats. desk.py's documented shape:
        naked shorts 11% notional (+60% per extra), long-only books their
        premium. [I], and the note says so."""
        if spot is None:
            return None, "no spot; notional unknowable"
        shorts = [l for l in p.legs if l.side == "SELL"]
        longs = [l for l in p.legs if l.side == "BUY"]
        if shorts:
            n = len(shorts)
            per_lot = desk_mod._naked_margin(spot, lot_size, n)
            return per_lot * p.lots, desk_mod._NAKED_MODEL_NOTE
        prem = sum(l.entry_px * l.qty for l in longs)
        return prem, "long-only: margin is the premium paid [M]"

    def risk(self, marks_by_idx: Dict[str, dict]) -> dict:
        """The book-level headline: margin used, headroom, and
        distance-to-forced under the declared stress. All [I].

        marks_by_idx: idx -> {"spot", "expected_move", "lot_size",
        "mark": {net_delta, net_gamma}}.
        """
        margin_used, m_why = 0.0, []
        stressed_loss = 0.0
        for p in self.open_positions():
            ctx = marks_by_idx.get(p.idx) or {}
            m, note = self.margin_position(p, ctx.get("spot"),
                                           ctx.get("lot_size") or
                                           desk_mod.LOT_SIZE.get(p.idx,
                                           desk_mod.DEFAULT_LOT_SIZE))
            if m is None:
                m_why.append(f"{p.pid}: {note}")
                continue
            margin_used += m
            em = ctx.get("expected_move")
            mk = ctx.get("mark") or {}
            nd, ng = mk.get("net_delta"), mk.get("net_gamma")
            if em and nd is not None:
                # adverse EM move against the net delta, plus the gamma bill
                stressed_loss += abs(nd) * em * STRESS_MOVE_EM
                if ng is not None:
                    stressed_loss += 0.5 * abs(ng) * (em * STRESS_MOVE_EM) ** 2
        headroom = self.capital - margin_used
        stress_need = margin_used * STRESS_MARGIN_X + stressed_loss
        forced_ratio = (self.capital / stress_need) if stress_need > 0 else None
        return {
            "capital": self.capital,
            "margin_used": round(margin_used, 0),
            "headroom": round(headroom, 0),
            "stress_margin_x": STRESS_MARGIN_X,
            "stressed_need": round(stress_need, 0),
            # >1: the stress leaves room. <1: the stress FORCES us -- the
            # book is crowd-shaped and the trader must refuse new risk.
            "forced_ratio": (round(forced_ratio, 2)
                             if forced_ratio is not None else None),
            "forced_why": None if forced_ratio is not None else
                          "no open risk to stress",
            "margin_why": m_why,
            "tag": "I",
            "note": ("stress = margin x%.1f + one adverse expected-move on "
                     "net delta/gamma; a real SPAN engine would differ in "
                     "detail, agree in shape" % STRESS_MARGIN_X),
        }

    # -- (de)hydration for trader.py's persistence ---------------------------
    def to_dict(self) -> dict:
        return {"capital": self.capital, "next": self._next,
                "realized_total": round(self.realized_total, 2),
                "positions": [asdict(p) for p in self.positions]}

    @classmethod
    def from_dict(cls, d: dict) -> "Book":
        b = cls(d.get("capital", 0.0))
        b._next = d.get("next", 1)
        b.realized_total = d.get("realized_total", 0.0)
        for pd in d.get("positions", []):
            legs = [PaperLeg(**ld) for ld in pd.pop("legs", [])]
            b.positions.append(Position(legs=legs, **pd))
        return b
