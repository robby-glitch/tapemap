"""hedge.py -- paper delta-hedging, and the short-variance ledger. SHADOW.

WHY THIS EXISTS. The operator's broker arrangement is zero-cost: no brokerage,
statutory charges rebated on any position closing at least Rs 1 positive
(CLAUDE.md rule 8). Hedging is a HIGH-FREQUENCY, LOW-EDGE activity -- you trade
often and each trip earns nothing by itself -- so retail friction normally eats
it alive and a strangle stays what retail calls it: a range bet. At zero cost
the trip is free, and the same strangle becomes SHORT VARIANCE:

    P&L  ~=  IV sold  -  RV realized (paid out through hedge round-trips)

That is the identity HANDOFF-DESK section 1 already writes down
(1/2 x Gamma x (sigma^2_implied - sigma^2_realised)), with the hedge as the
mechanism that actually converts it into cash. This module builds the hands for
it, and -- more importantly -- the LEDGER that says whether it worked.

SHADOW, AND STRUCTURALLY SO. This reads the paper option book's net delta and
never mutates it. The hedge inventory is deliberately kept OUT of
`book.Book`: hedge positions there would move `book.risk()`, hence
`forced_ratio`, hence trader.py's FORCED_MIN entry gate -- a shadow module
silently steering the live paper desk. Nothing downstream reads anything here.

PAPER ONLY. House rule 10 is absolute: this stack has never placed an order and
must not learn how. Everything below is arithmetic over a paper book; there is
no broker call in this file, and there is no code path from it to one.

THE FILL ASSUMPTION, [I] AND OPTIMISTIC IN TWO NAMED WAYS. A hedge is assumed
filled at the index level this snapshot carries, with no spread paid:

  1. NO QUEUE, NO SLIPPAGE. Consistent with the desk's posting discipline (she
     posts rather than crosses, so the bid-ask is revenue) but still the
     front-of-queue optimism `quoting.py` already flags -- hedge cost here is a
     LOWER bound, so measured variance capture is an UPPER bound.
  2. THE INDEX STANDS IN FOR THE FUTURE. `book.mark_position` already marks FUT
     legs at spot with exactly this caveat. The future trades at a carry
     premium (59 points on 2026-08-04, more than a strike step), but a hedge is
     a ROUND TRIP: entry and exit both use the index, so the carry cancels and
     only the carry DRIFT over the hedge's life is unmodelled. Intraday carry is
     near-constant, so this is small -- and it is not zero.

# ponytail: index-as-future is the corner cut; the fix is plumbing the future's
# own ltp (the senses loop already has it via ladder_of) into on_chain, and is
# worth doing the moment the ledger shows carry drift mattering.

WHOLE LOTS ARE THE REASON THE BAND IS WHAT IT IS. The hedge instrument is a
futures lot, so a correction smaller than one lot cannot be expressed. A band
tighter than 1.0 lot-equivalent would fire on deltas the instrument cannot
answer and churn the ledger with round trips that do not reduce risk.

Pure computation plus row shaping; trader.py owns the disk, the same division
of labour `book.py` states.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional

# --- the [I] layer, every number declared and none of it forward-tested ------

BAND_LOTS = 1.0
"""Hedge when |net delta| reaches this many LOTS-equivalent.

Starting rationale, to be replaced by the operator's forward review: the paper
book runs at PAPER_LOTS = 2, and a 2-lot short strangle's delta wanders roughly
+/-0.5 lots on ordinary drift, reaching a full lot when one wing goes properly
in the money. So 1.0 is the level at which the position has stopped being
delta-neutral in a way a whole futures lot can actually correct. Below it the
instrument is too coarse to help; well above it (2-3) the book is running a
directional bet between hedges, which is the thing short variance is trying not
to do. [I]"""

MAX_HEDGES_DAY = 8
"""The BRAKE: hedges per index per day, after which hedging STOPS and says so.

Deliberately NOT the manual-discipline "4". That number is a human's limit --
attention, decision fatigue, the cost of watching. A systematic hedger has none
of those, so its brake exists for a different reason: to cap the damage of a
hedger that is malfunctioning or being whipsawed by a chopping tape. 8 is
one rebalance roughly every 45 minutes across a 375-minute session, which is
loose enough not to bind on a normally trending day and tight enough that a
runaway loop is stopped inside an hour. [I]"""

GAP_MOVE_EM = 1.0
"""Overnight gap sized at this many expected-moves, for the daily row's
UNHEDGED exposure. Same shape and the same constant value as
`book.STRESS_MOVE_EM`, reused so the two readings cannot drift apart. [I]"""

LEDGER_DIR = os.path.join("data", "paper_desk")
"""Read at CALL time so `server._isolate_mock_writers` can redirect it -- the
2026-08-24 replay-leak rule: a fixture run must never share a path with the
record it exists to rehearse for."""


def ledger_path(day: str) -> str:
    return os.path.join(LEDGER_DIR, f"hedge_{day}.jsonl")


# --- the plan ---------------------------------------------------------------

def _round_half_up(x: float) -> int:
    """Python's round() is BANKER'S rounding: round(0.5) == 0, round(1.5) == 2.
    A hedge of 0 lots at exactly the band would be a no-op that still burned a
    brake slot, so half-up is the correct rule here."""
    return int(math.floor(abs(x) + 0.5)) * (1 if x >= 0 else -1)


def plan(option_delta_lots: Optional[float], hedge_lots: float,
         band: float = BAND_LOTS) -> Optional[dict]:
    """What hedge, if any, this delta calls for. Pure.

    `option_delta_lots` is the OPTION book's net delta in lots-equivalent
    (delta-units / lot_size); `hedge_lots` is the futures inventory already on,
    signed (+ long). A future's delta is 1.0 per unit, so the two simply add.

    Returns None when inside the band or when delta is unknown -- and "unknown"
    must reach here as None, never as 0.0. A book whose greeks did not arrive
    has an UNKNOWN delta, and hedging it as though it were flat is the one
    failure mode that turns a hedger into a random position generator.
    """
    if option_delta_lots is None:
        return None
    residual = option_delta_lots + hedge_lots
    if abs(residual) < band:
        return None
    lots = abs(_round_half_up(residual))
    if lots <= 0:
        return None
    side = "SELL" if residual > 0 else "BUY"      # trade AGAINST the exposure
    signed = -lots if residual > 0 else lots
    return {"side": side, "lots": lots,
            "residual_before": round(residual, 3),
            "residual_after": round(residual + signed, 3),
            "band": band}


# --- the paper futures inventory --------------------------------------------

@dataclass
class HedgeFill:
    ts: str
    idx: str
    side: str          # BUY | SELL
    lots: int
    qty: int           # units (lots x lot_size)
    px: float
    trigger_delta_lots: float
    residual_after: float
    mode: str = "maker-assumed"
    realized: float = 0.0      # rupees released by THIS fill, if it reduced


@dataclass
class _Leg:
    """One index's running futures inventory, average-cost."""
    lots: float = 0.0
    qty: float = 0.0
    vwap: Optional[float] = None
    realized: float = 0.0


@dataclass
class HedgeBook:
    """Paper futures inventory per index, plus the day's counters.

    Average-cost accounting: adding in the same direction re-averages the
    basis; reducing or reversing RELEASES P&L on the closed portion. That
    released number is the realized-vol bill -- it is normally NEGATIVE, and
    that is not a malfunction, it is what buying high and selling low to stay
    neutral costs. The whole module exists to weigh it against theta.
    """
    legs: Dict[str, _Leg] = field(default_factory=dict)
    fills: List[dict] = field(default_factory=list)
    hedges_today: Dict[str, int] = field(default_factory=dict)
    brake_logged: Dict[str, bool] = field(default_factory=dict)
    day: Optional[str] = None

    def leg(self, idx: str) -> _Leg:
        l = self.legs.get(idx)
        if l is None:
            l = self.legs[idx] = _Leg()
        return l

    def roll_day(self, day: str) -> bool:
        """New session: counters reset, INVENTORY DOES NOT. Anything still on
        at the close was carried overnight and its basis is still the basis."""
        if self.day == day:
            return False
        self.day, self.hedges_today, self.brake_logged = day, {}, {}
        self.fills = []
        return True

    def used(self, idx: str) -> int:
        return self.hedges_today.get(idx, 0)

    def braked(self, idx: str, cap: int = MAX_HEDGES_DAY) -> bool:
        return self.used(idx) >= cap

    def apply(self, idx: str, side: str, lots: int, lot_size: int, px: float,
              ts: str, trigger: float, residual_after: float) -> HedgeFill:
        """Book one paper futures fill. Returns it, with realized filled in."""
        l = self.leg(idx)
        sgn = 1 if side == "BUY" else -1
        add_lots, add_qty = sgn * lots, sgn * lots * lot_size
        realized = 0.0
        if l.vwap is None or l.qty == 0:
            l.vwap = px
        elif (l.qty > 0) == (add_qty > 0):
            # same direction: re-average
            l.vwap = ((l.vwap * abs(l.qty) + px * abs(add_qty))
                      / (abs(l.qty) + abs(add_qty)))
        else:
            # reducing or reversing: release P&L on the overlap
            closed = min(abs(l.qty), abs(add_qty))
            realized = (px - l.vwap) * closed * (1 if l.qty > 0 else -1)
            l.realized += realized
            if abs(add_qty) > abs(l.qty):
                l.vwap = px                    # flipped: new basis is this fill
        l.lots += add_lots
        l.qty += add_qty
        if l.qty == 0:
            l.vwap = None
        self.hedges_today[idx] = self.used(idx) + 1
        f = HedgeFill(ts=ts, idx=idx, side=side, lots=lots,
                      qty=lots * lot_size, px=round(px, 2),
                      trigger_delta_lots=round(trigger, 3),
                      residual_after=round(residual_after, 3),
                      realized=round(realized, 2))
        self.fills.append(asdict(f))
        return f

    def realized_total(self, idx: Optional[str] = None) -> float:
        if idx is not None:
            return self.leg(idx).realized
        return sum(l.realized for l in self.legs.values())

    # -- (de)hydration for trader.py's state.json ----------------------------
    def to_dict(self) -> dict:
        return {"legs": {k: asdict(v) for k, v in self.legs.items()},
                "fills": self.fills, "hedges_today": self.hedges_today,
                "brake_logged": self.brake_logged, "day": self.day}

    @classmethod
    def from_dict(cls, d: dict) -> "HedgeBook":
        b = cls()
        for k, v in (d.get("legs") or {}).items():
            b.legs[k] = _Leg(**v)
        b.fills = d.get("fills") or []
        b.hedges_today = d.get("hedges_today") or {}
        b.brake_logged = d.get("brake_logged") or {}
        b.day = d.get("day")
        return b


# --- the ledger rows --------------------------------------------------------

def fill_row(f: HedgeFill, day: str, spot: Optional[float],
             why: str) -> dict:
    """One hedge, with the snapshot that triggered it. [I], shadow."""
    return {"day": day, "kind": "hedge", "ts": f.ts, "idx": f.idx,
            "side": f.side, "lots": f.lots, "qty": f.qty, "px": f.px,
            "spot": spot,
            "trigger_delta_lots": f.trigger_delta_lots,
            "residual_after": f.residual_after,
            "hedge_realized": f.realized,
            "mode": f.mode, "why": why,
            "tag": "I", "shadow": True, "paper": True}


def refusal_row(day: str, ts: str, idx: str, why: str,
                delta_lots: Optional[float], used: int,
                cap: int = MAX_HEDGES_DAY) -> dict:
    """A hedge NOT taken, and why. The brake must never be silent: an
    unhedged book that looks like a hedged one is the worst reading this
    module could produce."""
    return {"day": day, "kind": "refusal", "ts": ts, "idx": idx,
            "why": why, "delta_lots": delta_lots,
            "hedges_used": used, "hedges_max": cap,
            "tag": "I", "shadow": True, "paper": True}


def gap_exposure(net_delta: Optional[float], net_gamma: Optional[float],
                 expected_move: Optional[float]) -> dict:
    """What an overnight gap would cost, UNHEDGED. [I].

    THE HEDGER DOES NOT COVER THIS AND THE RECORD MUST SAY SO. Delta-hedging
    rebalances during the session; a gap happens while the book sits still, and
    the whole point of the short-variance identity is that it holds for
    CONTINUOUS rehedging. Overnight is the discontinuity -- HANDOFF's own
    research finding is that gaps are informed repricing, not noise, and carry
    no mean-reversion edge to lean on.

    Same shape as `book.risk`'s stressed_loss so the two cannot disagree:
    one expected-move against the net delta, plus the gamma bill on that move.
    """
    if net_delta is None or not expected_move:
        return {"rupees": None,
                "why": ("could not size the gap: "
                        + ("net delta is unknown" if net_delta is None
                           else "no expected move published this snapshot")),
                "tag": "I"}
    move = expected_move * GAP_MOVE_EM
    rs = abs(net_delta) * move
    if net_gamma is not None:
        rs += 0.5 * abs(net_gamma) * move ** 2
    return {"rupees": round(rs, 0), "move": round(move, 1),
            "em_x": GAP_MOVE_EM,
            "why": None,
            "note": ("UNHEDGED by construction -- the hedger rebalances "
                     "intraday and a gap is the discontinuity the short-"
                     "variance identity does not cover"),
            "tag": "I"}


def daily_row(day: str, idx: str, theta: Optional[float],
              hedge_cost: float, used: int, gap: dict,
              net_delta_lots: Optional[float],
              cap: int = MAX_HEDGES_DAY) -> dict:
    """The session's summary for one index -- the row the module is FOR.

    THETA, AND HOW IT IS MEASURED. `theta` is the sum of
    `book.mark_position`'s `attribution.theta_gamma_resid` over this index's
    open option positions: a first-order decomposition against entry greeks,
    where the residual is everything delta x dS and vega x dIV did not explain.
    It therefore BUNDLES theta with gamma and higher-order terms, and the name
    of the field says so rather than claiming a clean theta.

    That bundling is not a compromise here, it is the right quantity: for a
    hedged short-variance book the gamma effect on the OPTION legs and the
    hedge round-trips on the FUTURES are two halves of one bill, and
    `net_variance` adds them. What this row cannot do is separate pure time
    decay from gamma within the options -- that needs a per-snapshot greek
    path, not entry greeks, and is not built.

    NO RATE, NO WIN COUNT, EVER (house rule 4). This row describes one
    session's rupees. Whether the strategy works is a question for the
    operator, over sessions, against a bar she states first.
    """
    net = None if theta is None else round(theta + hedge_cost, 2)
    return {"day": day, "kind": "daily", "idx": idx,
            "theta_collected": None if theta is None else round(theta, 2),
            "theta_method": ("sum of attribution.theta_gamma_resid over open "
                             "option positions; bundles theta + gamma + "
                             "higher-order, does not isolate decay"),
            "theta_why": None if theta is not None else
                         ("no attributable mark: entry greeks or a live quote "
                          "were missing, and a partial decomposition is "
                          "refused"),
            "hedge_cost": round(hedge_cost, 2),
            "hedge_cost_note": ("realized futures round-trip P&L; NEGATIVE is "
                                "normal and is the realized-vol bill"),
            "net_variance": net,
            "hedges_used": used, "hedges_max": cap,
            "net_delta_lots_at_close": (None if net_delta_lots is None
                                        else round(net_delta_lots, 3)),
            "gap_exposure": gap,
            "fill_model": ("filled at the index level, no spread paid; "
                           "index stands in for the future so carry cancels "
                           "on the round trip and only carry DRIFT is "
                           "unmodelled"),
            "tag": "I", "shadow": True, "paper": True}
