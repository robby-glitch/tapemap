"""Run the tape engine over a data folder and produce the UI timeline JSON.

Used by server.py (import) or standalone: python analyze.py [data_dir] [strike]
"""

import json
import sys

import band_rotation
import structure
from engine import Session, days_to_expiry, load, session_json


def analyze(base="data", strike=24200.0, expiry="2026-07-21"):
    fut, years = load(f"{base}/FUT_3day.csv")
    ce, _ = load(f"{base}/CE_3day.csv")
    pe, _ = load(f"{base}/PE_3day.csv")
    days = []
    for day in sorted(fut, key=lambda d: (d.split()[0], int(d.split()[1]))):
        if day in ce and day in pe:
            t_days = days_to_expiry(day, years[day], expiry)
            s = Session(day, fut[day], ce[day], pe[day], quiet=True,
                        strike=strike, t_days=t_days)
            s.run()
            js = session_json(s)
            # same additive Phase 3.5 key as live.py: replay must carry the
            # structure layer too, or the two paths disagree about the tape --
            # including the pivots block, which is where PDH/PDL/PDC come from
            js["structures"] = structure.compute(js["bars"],
                                                 pivots=js.get("pivots"))
            # same additive key as live.py, for the same reason: replay must
            # carry the index-side band-rotation signals too, or the live tape
            # and the replayed one disagree about the operator's own setup
            js["rotation"] = band_rotation.detect_index(js["bars"])
            js["rotation_rule"] = band_rotation.INDEX_ROTATION_RULE
            days.append(js)
    return {"strike": strike, "days": days}


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "data"
    strike = float(sys.argv[2]) if len(sys.argv) > 2 else 24200.0
    print(json.dumps(analyze(base, strike)))
