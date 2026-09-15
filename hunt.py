"""hunt.py -- war-map object C: the liquidity and runway map.

WHAT IT ANSWERS. The operator's morning question: WHICH SIDE PAYS MORE TO
RUN. For each direction, spot to the next reaction point, this itemizes who
goes underwater along the path and by how much -- the fuel. The runway with
more forced covering per point is where the dealer's money is. Two numbers,
one per direction, with the fuel itemized leg by leg.

THE MECHANISM, and why it is [I] end to end. `trapped_inventory` ledgers
carry a session-anchored writer basis per (strike, side) -- itself [I]
(writer-dominated assumption, invisible overnight basis; its own docstring
says so). The projection stacked on top here: an index move of D points moves
a leg's premium by ~delta x D, so a short CE book's pain at the up-target is
    max(0, ltp + delta*D - basis) - max(0, ltp - basis)
and fuel is that times the OI behind it. A leg with no delta on the wire
cannot be projected and is COUNTED OUT LOUD rather than silently skipped --
"we could not check" and "we checked and found nothing" are different
sentences (house rule).

STOP ZONES ARE INFERENCES, FOREVER. Stops are invisible until they trigger.
`stop_zone` on each runway names where fresh dwell-loaded positions would be
forced out (beyond the target, one band deep) and states its basis. It is
never rendered as an observed order.

KILL CONDITION (declared at birth, per the plan): if over ~30 scored
sessions runs measurably ignore the richer runway, the RANKING is wrong and
this module goes back to describing fuel without ranking it.

Pure computation, stdlib only, no I/O.
"""

from __future__ import annotations

from typing import List, Optional

# Levels a runway may target: the stable reaction points plus the walls --
# the places the thesis says a run is AIMED at. GAMMA_FLIP/MAX_PAIN drift
# with the chain and are pin physics, not destinations.
TARGET_KINDS = {"PDH", "PDL", "PDC", "PWH", "PWL", "OPEN", "ROUND",
                "CE_WALL", "PE_WALL"}
TOP_ITEMS = 5          # legs itemized per runway
MIN_DIST_BAND = 1.0    # a target closer than one band is where we ARE


def _target(spot: float, levels: List[dict], up: bool,
            band: float) -> Optional[dict]:
    """Nearest targetable level beyond `band` in the given direction."""
    cands = [l for l in levels or []
             if l.get("kind") in TARGET_KINDS
             and (l["px"] - spot > MIN_DIST_BAND * band if up
                  else spot - l["px"] > MIN_DIST_BAND * band)]
    if not cands:
        return None
    return min(cands, key=lambda l: abs(l["px"] - spot))


def _runway(spot: float, target: Optional[dict], legs: List[dict],
            up: bool, band: float) -> dict:
    """One direction's runway: fuel itemized, per-point, stop zone."""
    if target is None:
        return {"target": None, "fuel": None, "per_point": None, "items": [],
                "why": "no known level in this direction within the map"}
    dist = abs(target["px"] - spot)
    side = "ce" if up else "pe"          # the writers a move this way hurts
    items, skipped = [], 0
    for leg in legs or []:
        if leg.get("side") != side:
            continue
        oi, ltp, basis, delta = (leg.get("oi"), leg.get("ltp"),
                                 leg.get("basis"), leg.get("delta"))
        if not oi or ltp is None or basis is None:
            continue                     # cold ledger: nothing to project
        if delta is None:
            skipped += 1
            continue
        prem_at = ltp + abs(delta) * dist
        added = max(0.0, prem_at - basis) - max(0.0, ltp - basis)
        if added <= 0:
            continue
        items.append({"k": leg["k"], "side": side.upper(),
                      "oi": round(oi), "pain_added": round(added, 2),
                      "fuel": round(added * oi)})
    items.sort(key=lambda i: -i["fuel"])
    fuel = sum(i["fuel"] for i in items)
    why = (f"{len(items)} {side.upper()} writer leg(s) go deeper underwater "
           f"on the way to {target['kind']} {target['px']:,.0f}")
    if skipped:
        why += f" ({skipped} leg(s) had no delta on the wire and are NOT counted)"
    return {"target": {"kind": target["kind"], "px": target["px"]},
            "dist": round(dist, 1),
            "fuel": round(fuel), "per_point": round(fuel / dist) if dist else None,
            "items": items[:TOP_ITEMS],
            # The inference, with its basis stated -- never an observed order.
            "stop_zone": {
                "lo": round(target["px"] + (band if up else -2 * band), 1),
                "hi": round(target["px"] + (2 * band if up else -band), 1),
                "tag": "I",
                "basis": "fresh positions loaded at this level would be "
                         "forced out beyond it; inferred from entry premium "
                         "and pain, stops are invisible until they trigger"},
            "why": why, "tag": "I"}


def runways(spot: Optional[float], levels: List[dict], legs: List[dict],
            band: Optional[float]) -> dict:
    """Both runways plus the answer: which side pays more to run. All [I].

    `legs`: [{k, side ("ce"/"pe"), oi, ltp, basis, delta}] -- assembled by
    the caller from chainside's ledgers and the live chain, because this
    module must stay replayable against any fixture.
    """
    if spot is None:
        return {"ok": False, "why": "no spot; runways unknowable"}
    if band is None:
        return {"ok": False, "why": "band not calibrated yet (dwell.py owns it)"}
    up = _runway(spot, _target(spot, levels, True, band), legs, True, band)
    dn = _runway(spot, _target(spot, levels, False, band), legs, False, band)
    richer = None
    if up.get("per_point") is not None or dn.get("per_point") is not None:
        u, d = up.get("per_point") or 0, dn.get("per_point") or 0
        if u != d:
            richer = "UP" if u > d else "DOWN"
    return {"ok": True, "up": up, "down": dn, "richer": richer, "tag": "I",
            "note": "fuel = OI x premium-pain added over the path; the richer "
                    "runway is where forced covering pays the run [I]"}
