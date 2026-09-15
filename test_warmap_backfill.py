"""The war map on a late start: the minute grid -- REST-rebuilt rows AND rows
an earlier process observed -- is replayed through fresh machines before the
first live snapshot, to a separate log tagged backfill:true. The anytime-start
rule: a 13:18 start must know what 09:30 and 11:00 did."""

import json
import time

import chainside
import warmap
from test_warmap import IN_HOURS, _doc, _stub_fetch


def _grid(marks, observed_from=None):
    """chain_backfill.minute_grid rows (src=backfill) up to `observed_from`,
    then rows shaped the way ChainState.update writes them (no src)."""
    out = {}
    for m, spot in marks:
        rec = {"spot": spot, "px": {},
               "k": {k: (10.0, 20.0) for k in (24900, 24950, 25000, 25050, 25100)}}
        if observed_from is None or m < observed_from:
            rec["src"] = "backfill"
        out[m] = rec
    return out


def _board(tmp_path):
    wm = warmap.WarMap("NIFTY", seq_path=str(tmp_path / "w.jsonl"), fetch=_stub_fetch)
    wm._kick_daily()
    for _ in range(200):
        if wm.levels.daily:
            break
        time.sleep(0.01)
    assert wm.levels.daily, "the stub daily fetch did not land"
    return wm


def _live(sec, ts, spot=25000.0):
    d = _doc(sec, spot)
    d["ts"] = ts
    return d


# 09:16-09:24 calibrate the band on 1-point moves; 09:25-09:27 walk up to
# PDH 25150; 09:28-09:31 back down: one APPROACH -> REJECT on the PDH machine
MORNING = [(f"09:{16 + i:02d}", 25000.0 + (i % 2)) for i in range(9)] + [
    ("09:25", 25100.0), ("09:26", 25140.0), ("09:27", 25150.0),
    ("09:28", 25100.0), ("09:29", 25050.0), ("09:30", 25000.0), ("09:31", 25000.0)]
# ...and nine minutes an earlier process watched, restored without a src
LATER = [(f"09:{32 + i:02d}", 25000.0 + (i % 2)) for i in range(9)]


def test_a_late_start_replays_rest_rows_and_observed_rows_alike(tmp_path):
    live = tmp_path / "w.jsonl"
    wm = _board(tmp_path)
    grid = _grid(MORNING + LATER, observed_from="09:32")
    cs = chainside.ChainSide()
    wm.on_snapshot(_live(39600, "11:00:00"), cs, grid=grid,
                   now=IN_HOURS.replace(hour=11, minute=0))
    bf = wm.state()["backfill"]
    assert bf["done"] and bf["from"] == "09:16" and bf["to"] == "09:40", bf
    assert bf["backfilled"] == 16 and bf["observed"] == 9, bf
    assert bf["missing_before"] is None
    pdh = wm.state()["sequence"]["PDH@25150.0"]
    assert pdh["tests"] >= 1 and pdh["last_outcome"] == "REJECT", pdh
    rows = [json.loads(x) for x in open(bf["log"], encoding="utf-8")]
    assert rows and all(r["backfill"] is True for r in rows)
    assert {r["src"] for r in rows} <= {"rest_1m", "observed"}
    assert "rest_1m" in {r["src"] for r in rows}
    # the live log is observation-only
    if live.exists():
        assert all(not json.loads(x).get("backfill") for x in live.read_text().splitlines() if x.strip())
    # a second live snapshot does not replay again
    wm.on_snapshot(_live(39660, "11:01:00", 25001.0), cs, grid=grid,
                   now=IN_HOURS.replace(hour=11, minute=1))
    assert wm.state()["backfill"]["minutes"] == bf["minutes"]


def test_a_grid_that_starts_late_waits_then_replays_and_names_the_gap(tmp_path):
    """No REST rows and observed rows only from 09:42: the walk may still be
    running, so wait; after SEED_WAIT_S replay what is there and say the
    open is missing rather than pretending 09:42 was the open."""
    wm = _board(tmp_path)
    grid = _grid([(f"{9 + (42 + i) // 60:02d}:{(42 + i) % 60:02d}", 25000.0 + (i % 2))
                  for i in range(12)], observed_from="00:00")
    cs = chainside.ChainSide()
    wm.on_snapshot(_live(39600, "11:00:00"), cs, grid=grid, now=IN_HOURS.replace(hour=11))
    st = wm.state()["backfill"]
    assert st["done"] is False and "09:42" in st["why"], st
    wm.on_snapshot(_live(39600 + 601, "11:10:01"), cs, grid=grid, now=IN_HOURS.replace(hour=11, minute=10))
    st = wm.state()["backfill"]
    assert st["done"] and st["observed"] == 12 and st["backfilled"] == 0, st
    assert st["missing_before"] == "09:42" and "NOTHING before 09:42" in st["why"]


def test_a_start_at_the_open_has_nothing_to_rebuild(tmp_path):
    wm = warmap.WarMap("NIFTY", seq_path=str(tmp_path / "w.jsonl"), fetch=_stub_fetch)
    wm.on_snapshot(_live(33420, "09:17:00"), chainside.ChainSide(), grid={}, now=IN_HOURS)
    st = wm.state()["backfill"]
    assert st["done"] and "nothing to rebuild" in st["why"], st
