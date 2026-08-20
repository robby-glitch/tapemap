"""fuse.py -- detector rows in, a regime verdict out.

WHAT IT IS FOR. `sweep`, `absorption` and `depth_pull` emit measurements with
magnitudes. `regime.decide()` wants booleans and ranks. Something has to turn
"a sweep took 3 levels and 975 lots" into "ignition", and that judgement is
neither the detector's job nor the gate's -- a detector that graded its own
output would be two modules in one, and a gate that parsed raw rows would be
impossible to replay. This is that seam, and it is the only place a magnitude
becomes a verdict.

**RANKING LIVES HERE, AND NOWHERE ELSE.** Every threshold is percentile-so-far
against THIS instrument's own session, never an absolute. That is the
discipline `engine.Rank` applies to bars, applied to the book, and it is why
one set of constants runs on NIFTY, BANKNIFTY and SENSEX without retuning: a
sweep of 975 lots is enormous on the future and unremarkable on a liquid ATM
call, and only the session can say which. `Rank` is duplicated from
`engine.Rank` rather than imported, deliberately -- importing it would couple
this module to a 1300-line file that owns the tape, and the whole operator
group is built to replay without one.

**IT DOES NOT INVENT DRAIN.** Drain is OI leaving the pressured side, and OI
does not appear in the book at all -- it arrives on the chain, at chain
cadence. So `drain` is an argument. Passing nothing leaves it False and the
gate simply never reaches CASCADE, which is the honest outcome: without the
third condition there is no confirmed forced flow, and manufacturing one from
book data alone is exactly the "2/3 plus impatience" failure the sequence rule
exists to prevent. `fuel_rank` is an argument for the same reason -- it comes
from `trapped_inventory`, which needs a chain snapshot.

WHAT ONE-SIDEDNESS MEANS HERE. Sweeps arriving overwhelmingly on one side of
the book within the window. It is a BOOK-FLOW reading, not the option-chain
one-sidedness the ledger measures, and the two can disagree; the caller picks
which it means. Defaulting silently to the ledger's would be the kind of quiet
conflation that makes a verdict impossible to argue with.

Pure computation, stdlib only, no I/O. The verdict inherits `regime`'s `[I]`
tag, because the cutoffs below rest on the same single afternoon.
"""

from __future__ import annotations

from bisect import bisect_right, insort
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import regime

# --- the [I] layer ---------------------------------------------------------
IGN_P = 0.90        # sweep-size percentile that counts as ignition
WINDOW = 12         # rows of book history a verdict looks back over
MIN_HIST = 10       # ranks below this much history are not trusted
ONE_SIDED = 0.75    # share of windowed sweeps on one side to call it lopsided


class Rank:
    """Percentile-so-far of a stream: rank(x) in [0,1] vs values seen earlier.

    Mirrors `engine.Rank` exactly. Copied, not imported -- see the module
    docstring on why this group stays free of the engine.
    """

    def __init__(self):
        self.sorted: List[float] = []

    def rank(self, x: float) -> float:
        n = len(self.sorted)
        r = bisect_right(self.sorted, x) / n if n else 0.5
        insort(self.sorted, x)
        return r

    def __len__(self):
        return len(self.sorted)


@dataclass
class Evidence:
    """What the verdict was built from, so it can be argued with."""
    ignition: bool = False
    ign_rank: Optional[float] = None
    ign_at: Optional[str] = None
    sweeps: int = 0
    buys: int = 0
    sells: int = 0
    one_sided_book: Optional[bool] = None
    pulls: int = 0
    absorptions: int = 0
    warm: bool = False
    notes: List[str] = field(default_factory=list)


class Fuse:
    """One per instrument. Rows in, evidence and a regime verdict out."""

    def __init__(self):
        self._sweep_rank = Rank()
        self._pull_rank = Rank()
        self._recent: List[dict] = []
        self.ev = Evidence()

    def on_rows(self, rows: List[dict]) -> Evidence:
        """Ingest one frame's senses rows and re-rank. Returns the evidence.

        Ranking happens on INGEST, not at verdict time, so the distribution is
        the session's own regardless of how often anyone asks for a verdict. A
        rank that moved depending on when it was read would be unreplayable.
        """
        for r in rows or []:
            det = r.get("det")
            if det == "sweep":
                # Only a CONSUMED sweep counts toward ignition. A `pulled` row
                # is liquidity leaving, which is the opposite reading, and
                # ranking the two together would let cancellations masquerade
                # as aggression.
                if r.get("kind") == "swept":
                    r = dict(r, _rank=self._sweep_rank.rank(r.get("qty") or 0.0))
                else:
                    r = dict(r, _rank=None)
            elif det == "pull":
                r = dict(r, _rank=self._pull_rank.rank(r.get("gone") or 0.0))
            self._recent.append(r)
        if len(self._recent) > WINDOW:
            del self._recent[:-WINDOW]
        return self._evidence()

    def _evidence(self) -> Evidence:
        win = self._recent[-WINDOW:]
        sweeps = [r for r in win if r.get("det") == "sweep"
                  and r.get("kind") == "swept"]
        buys = sum(1 for r in sweeps if r.get("side") == "buy")
        sells = len(sweeps) - buys
        warm = len(self._sweep_rank) >= MIN_HIST

        # THE MOST RECENT SWEEP, NOT THE BIGGEST IN THE WINDOW. Taking the
        # window's maximum meant one large sweep kept re-firing ignition for
        # every frame it stayed in view -- and because a percentile-so-far
        # scores each new maximum at 1.00, a rising series read as continuous
        # ignition that never switched off. Ignition means "a big one just
        # arrived"; whether it is still ARMED afterwards is the gate's job,
        # confirmed by drain, not something to fake by holding the flag up.
        best = next((r for r in reversed(sweeps)
                     if r.get("_rank") is not None), None)
        ign = bool(warm and best and best["_rank"] >= IGN_P)

        ev = Evidence(
            ignition=ign,
            ign_rank=round(best["_rank"], 3) if best else None,
            ign_at=best.get("t") if (ign and best) else None,
            sweeps=len(sweeps), buys=buys, sells=sells,
            pulls=sum(1 for r in win if r.get("det") == "pull"),
            absorptions=sum(1 for r in win if r.get("det") == "absorption"),
            warm=warm)
        if sweeps:
            ev.one_sided_book = max(buys, sells) / len(sweeps) >= ONE_SIDED
        if not warm:
            ev.notes.append(f"only {len(self._sweep_rank)} sweeps ranked so far; "
                            f"percentiles are not trusted below {MIN_HIST}")
        if ign:
            ev.notes.append(f"sweep at {best['_rank']:.2f} pctl of this "
                            f"instrument's own session")
        self.ev = ev
        return ev

    def verdict(self, sigma_pctl: Optional[float] = None,
                fuel_rank: Optional[float] = None,
                one_sided: Optional[bool] = None,
                drain: bool = False,
                vwap_flips_per_hr: Optional[float] = None,
                walls_holding: Optional[bool] = None,
                setups: Optional[List[str]] = None) -> regime.Verdict:
        """The gate's verdict, with ignition supplied from the book.

        `drain` and `fuel_rank` stay arguments: both are chain quantities and
        this module sees only the book. Everything else passes straight
        through, so the gate's own ordering and reasons are unchanged.
        """
        return regime.decide(
            sigma_pctl=sigma_pctl, fuel_rank=fuel_rank,
            one_sided=self.ev.one_sided_book if one_sided is None else one_sided,
            ignition=self.ev.ignition, drain=drain,
            vwap_flips_per_hr=vwap_flips_per_hr, walls_holding=walls_holding,
            setups=setups)


class Book:
    """Fuses per instrument, so one tape's ranks never pollute another's."""

    def __init__(self):
        self._by: Dict[str, Fuse] = {}

    def for_inst(self, inst: str) -> Fuse:
        if inst not in self._by:
            self._by[inst] = Fuse()
        return self._by[inst]

    def on_rows(self, rows: List[dict]) -> Dict[str, Evidence]:
        """Route a mixed batch of rows to the right instrument's Fuse."""
        touched: Dict[str, List[dict]] = {}
        for r in rows or []:
            touched.setdefault(r.get("inst") or "?", []).append(r)
        return {i: self.for_inst(i).on_rows(rs) for i, rs in touched.items()}
