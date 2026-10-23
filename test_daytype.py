"""AAJ KA DIN on 2026-10-05, the check day (thresholds were tuned on 2026-09-22 .. 2026-10-01 only).

The truth that day (Upstox NIFTY-I 5m): a 09:50-12:10 trend leg down (-194, 27/28 bars under VWAP), a failed
break of yesterday's close at 12:18 (the trap layer: FAIL · PDC 22,422 · sellers phanse) and a short-covering V,
then 13:45-15:30 pin/chop between 22500 PE and 22600 CE with expiry the next day (its last 35 min drift -17,
under the SIZE floor). Read the way the band reads
it -- daytype.read at every minute of the session, each seeing only the bars closed by then.
"""
import gzip
import json
import os

import board
import daytype

FX = os.path.join(os.path.dirname(__file__), "test", "fixtures", "daytype_NIFTY_2026-10-05.json.gz")


def test_daytype_2026_10_05_names_the_leg_ends_it_at_the_fail_and_names_the_pin():
    with gzip.open(FX, "rt", encoding="utf-8") as f:
        fx = json.load(f)
    opens = {(float(k.split("|")[0]), k.split("|")[1]): v for k, v in fx["opens"].items()}
    shown = []                                   # (clock HH:MM, word) each time the band's word changed
    for now in range(9 * 60 + 15, 15 * 60 + 31):
        r = daytype.read("NIFTY", fx["day"], fx["bars"], now, fx["minutes"], opens, fx["dte"], trap_events=fx["trap"],
                         ib_ref=fx["ib_ref"])
        if r["ok"] and (not shown or shown[-1][1] != r["word"]):
            shown.append((board.hm(now), r["word"]))
    k = next(j for j, (t, w) in enumerate(shown) if w == "TREND ▼")
    assert "09:55" <= shown[k][0] <= "10:20", shown
    assert k + 1 < len(shown) and shown[k + 1][0] <= "12:25", shown          # ended by the 12:18 PDC fail
    assert any(w == "PIN/CHOP" and t <= "14:15" for t, w in shown), shown
    assert len(shown) - 1 <= 8, shown
    assert shown[-1][1] != "TREND ▼", shown          # the 14:55-15:30 drift (-17) is under the SIZE floor
