# tapemap/gate.py
"""gate.py -- the seller's GATE, ported from ui/toolb.js:826 gateState().

It may say only three things -- TRADE / HALF SIZE / NO NEW RISK -- and a
fourth that the old code could not: PATA NAHI. The P0 the port fixes: the
old gate initialised to TRADE and holes never downgraded it, so it showed GO
in green at 09:20 with IV/RV, VPIN and expiry all unknown. Here a hole WINS.
There is no event calendar anywhere in this backend; inventing one would be
the most dangerous number on the screen, so it stays a named hole, and the
level is PATA NAHI until a calendar exists -- `would_be` carries what the
gate would say with that hole filled. Pure, stdlib only."""
from __future__ import annotations

from typing import Optional

RANK = {"TRADE": 0, "HALF SIZE": 1, "NO NEW RISK": 2}


def state(ivrv: Optional[float], expiry_iso: Optional[str], today_iso: str,
          vpin_pct: Optional[float], squeeze: Optional[bool]) -> dict:
    holes = []
    level, lead = "TRADE", None

    def worse(l, why):
        nonlocal level, lead
        if RANK[l] > RANK[level]:
            level, lead = l, why

    if ivrv is None:
        holes.append("IV vs RV: not measured")
    elif ivrv < 1.0:
        worse("NO NEW RISK", "vol cheap")
    elif ivrv < 1.1:
        worse("HALF SIZE", "IV barely above RV")
    if not expiry_iso:
        holes.append("expiry date: chain did not give one")
    elif expiry_iso == today_iso:
        worse("HALF SIZE", "expiry day, gamma fast")
    if vpin_pct is None:
        holes.append("VPIN: not measured yet")
    elif vpin_pct >= 0.8:
        worse("NO NEW RISK", "VPIN burst")
    if squeeze is None:
        holes.append("day type: not measured yet")
    elif squeeze:
        worse("NO NEW RISK", "SQUEEZE day")
    holes.append("event calendar not wired")
    return {"level": "PATA NAHI", "reason": "; ".join(holes), "holes": holes,
            "would_be": level, "would_be_reason": lead or "no block seen"}
