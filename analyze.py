"""Run the tape engine over a data folder and produce the UI timeline JSON.

Used by server.py (import) or standalone: python analyze.py [data_dir] [strike]
"""

import json
import sys

from engine import Session, load, session_json


def analyze(base="data", strike=24200.0, expiry_dom=21):
    fut = load(f"{base}/FUT_3day.csv")
    ce = load(f"{base}/CE_3day.csv")
    pe = load(f"{base}/PE_3day.csv")
    days = []
    for day in sorted(fut, key=lambda d: (d.split()[0], int(d.split()[1]))):
        if day in ce and day in pe:
            t_days = max(expiry_dom - int(day.split()[1]), 0) + 0.25
            s = Session(day, fut[day], ce[day], pe[day], quiet=True,
                        strike=strike, t_days=t_days)
            s.run()
            days.append(session_json(s))
    return {"strike": strike, "days": days}


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "data"
    strike = float(sys.argv[2]) if len(sys.argv) > 2 else 24200.0
    print(json.dumps(analyze(base, strike)))
