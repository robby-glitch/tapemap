"""tools/mark_grade.py (A46): the final state per mark id, its known minute, signed spot excursions, the groups --
counts and medians only. Synthetic files in tmp_path."""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import mark_grade as G  # noqa: E402

DAY = "2026-10-22"
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
ms = lambda hhmm: int(datetime.datetime(2026, 10, 22, int(hhmm[:2]), int(hhmm[3:]), tzinfo=IST).timestamp() * 1000)  # noqa: E731


def _write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))


def test_a_day_is_graded_from_the_last_row_of_each_mark(tmp_path):
    data = str(tmp_path)
    spot = [{"sec": m * 60 + 30, "spot": 100.0 + min(m - 600, 20) - 2 * max(0, m - 620)} for m in range(570, 931)]  # up to 10:20, then down
    _write(os.path.join(data, "chain", f"chain_NIFTY_{DAY}.jsonl"), spot)
    _write(os.path.join(data, "tape", "ux_NIFTY_2026-10-21.jsonl"),
           [{"t": ms("15:10") - 86400000, "o": 1, "h": 300.0, "l": 90.0, "c": 150.0}])
    m = {"kind": "initiative", "winner": 1, "rank": 95, "tier": "solid", "ring": "VWAP", "p": 152.0, "build": "v2.7"}
    _write(os.path.join(data, "tape", f"ofd_marks2_NIFTY_{DAY}.jsonl"), [
        dict(m, id="a", t=ms("10:00"), status="TIKA", status_t=None),
        dict(m, id="a", t=ms("10:00"), status="TOOTA", status_t=ms("10:30")),          # the last row of "a" wins
        dict(m, id="b", kind="trap", winner=-1, rank=40, ring=None, t=ms("10:00"), status="TIKA", status_t=None),
        dict(m, id="c", kind="climax", winner=0, rank=None, t=ms("15:20"), status="TIKA", status_t=None)])
    g = G.build("NIFTY", DAY, data)
    a, b, c = g["rows"]
    assert (a["id"], a["ref"], a["status"], a["broke_after"], a["pd"]) == ("a", "10:05", "TOOTA", 30, "PDC")
    assert (a["spot0"], a["mfe15"], a["mae15"], a["mfe30"], a["mae30"], a["mae60"]) == (104.0, 15.0, 0.0, 16.0, -12.0, -72.0)
    assert (b["ref"], b["mfe15"], b["mae15"]) == ("10:10", 0.0, -11.0)          # a trap is known one bar later (bar B)
    assert c["mfe15"] is None and c["band"] == "none" and c["part"] == "15:15-15:30"          # unsided: no excursion
    assert g["groups"]["kind"]["initiative"] == {"n": 1, "tika": 0, "toota": 1, "toota15": 0, "toota30": 1, "toota60": 1,
                                                 "med_mfe15": 15.0, "med_mae15": 0.0, "med_mfe30": 16.0, "med_mae30": -12.0,
                                                 "med_mfe60": 16.0, "med_mae60": -72.0}
    assert set(g["groups"]) == {"kind", "band", "tier", "ring", "pd", "part"}
    assert not any(w in k for d in g["groups"].values() for x in d.values() for k in x for w in ("rate", "pct", "%"))
    G.main(["--day", DAY, "--data", data])
    s = json.load(open(os.path.join(data, "grade", "marks_summary.json"), encoding="utf-8"))
    assert s["days"] == [f"NIFTY {DAY}"] and s["by_build"]["NIFTY · v2.7"]["n"] == 3
