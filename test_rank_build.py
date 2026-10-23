"""tools/rank_build.py: the reference never reads a day >= before; the quantile / rank rule both sides use; board.js's
Math.round binning; the wall_bin coverage rule; legs() as board.js has it."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import rank_build as R  # noqa: E402

def _t0(day):
    import datetime
    d = datetime.datetime.fromisoformat(day).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    return int((d + datetime.timedelta(hours=9, minutes=15)).timestamp() * 1000)


def _gc_day(day, scale=1, n=75, skip=()):
    """n 5-min bars from 09:15 with a three-row ladder, a gentle down drift and OI."""
    out = []
    for i in range(n):
        if i in skip:
            continue
        px = 22600 - i * 2 * scale
        lad = [{"p": px - 5, "b": 10 * scale, "s": 2}, {"p": px, "b": 3, "s": 12 * scale}, {"p": px + 5, "b": 4, "s": 4},
               {"p": px + 10, "b": 1, "s": 1}]
        out.append({"t": _t0(day) + i * 300000, "o": px + 1, "h": px + 6 * scale, "l": px - 6 * scale, "c": px - 1,
                    "vol": 100 * scale + i, "buy": 50, "sell": 50, "delta": (-1) ** i * 7 * scale, "oi": 1000000 + i * 1000 * scale,
                    "fromTicks": True, "ladder": lad})
    return out


def _write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))


def _chain(day, scale=1):
    rows = []
    for sec in range(33300, 55800, 60):
        oi = (sec - 33300) * 10 * scale
        rows.append({"ts": "x", "sec": sec, "spot": 22500.0, "atm": 22500,
                     "strikes": [{"k": k, "ce": {"oi": 5000000 + oi, "ltp": 1}, "pe": {"oi": 4000000 - oi, "ltp": 1}}
                                 for k in range(22350, 22700, 50)]})
    return rows


def _fixture(data, days, late):
    """Recorded days plus LATE days (>= before) whose numbers would change every table."""
    for d in days + late:
        s = 50 if d in late else 1
        _write(os.path.join(data, "tape", f"tape_NIFTY_{d}.jsonl"), _gc_day(d, s))
        _write(os.path.join(data, "chain", f"chain_NIFTY_{d}.jsonl"), _chain(d, s))
        _write(os.path.join(data, "tape", f"ofd_marks_NIFTY_{d}.jsonl"),
               [{"t": _t0(d), "kind": "trap", "side": 1, "p": 22500.0, "size": 100 * s},
                {"t": _t0(d), "kind": "absorption", "side": -1, "p": 22510.0, "size": 200 * s}])
        _write(os.path.join(data, "decoder", f"decoder_{d}.jsonl"),
               [{"row": "event", "kind": "E1", "idx": "NIFTY", "id": f"E1@{d}", "event": {"lots": 300 * s}}])


def test_build_never_reads_a_day_on_or_after_before(tmp_path):
    data = str(tmp_path / "data")
    days, late = ["2026-10-05", "2026-10-06", "2026-10-07"], ["2026-10-08", "2026-10-09"]
    _fixture(data, days, late)
    with_late = R.build("NIFTY", "2026-10-08", data)
    for d in late:                                   # remove the late days: the reference must not move
        for p in (f"tape/tape_NIFTY_{d}.jsonl", f"chain/chain_NIFTY_{d}.jsonl", f"tape/ofd_marks_NIFTY_{d}.jsonl",
                  f"decoder/decoder_{d}.jsonl"):
            os.remove(os.path.join(data, p))
    without = R.build("NIFTY", "2026-10-08", data)
    assert with_late["id"] == without["id"] and with_late["days"] == days
    assert with_late["marks"]["trap"]["q"][100] == 100 and with_late["marks"]["E1"]["n"] == 3
    assert with_late["writers30"]["days"] == days
    # and a later `before` does see them (the fixture is not inert)
    _fixture(data, [], late)
    assert R.build("NIFTY", "2026-10-10", data)["marks"]["trap"]["q"][100] == 5000


def test_quantile_table_and_the_page_rank_rule():
    tab = R.quant(range(1, 11))                       # 1..10
    assert tab["n"] == 10 and len(tab["q"]) == 101
    assert tab["q"][0] == 1 and tab["q"][100] == 10 and tab["q"][50] == 5   # sorted[floor(50 * 9 / 100)] = sorted[4]
    assert R.rank(tab, 5) == 55                       # the largest k with q[k] <= 5: floor(55 * 9 / 100) = 4
    assert R.rank(tab, 10) == 100 and R.rank(tab, 0.5) == 0 and R.rank(tab, None) is None and R.rank(None, 3) is None
    assert R.quant([]) is None and R.quant([None]) is None


def test_bins_round_half_up_like_javascript():
    assert R.bin5(22502.5) == 22505 and round(22502.5 / 5) * 5 == 22500    # Python's round() would split the bin
    assert R.bin5(22502.4) == 22500 and R.bin5(22507.5) == 22510
    bars = [{"t": i, "m": 560 + 5 * i, "ladder": [{"p": 22502.5, "b": 10, "s": 0}, {"p": 22505.0, "b": 0, "s": 4},
                                                  {"p": 22520, "b": 1, "s": 1}, {"p": 22530, "b": 1, "s": 1},
                                                  {"p": 22540, "b": 1, "s": 1}]} for i in range(2)]
    vals = R.wall_values(bars, 600)
    assert 12 in vals                                 # 22502.5 and 22505 are ONE bin: |(10 - 4) x 2 bars|


def test_wall_bin_coverage_needs_80_percent_of_the_bars(tmp_path):
    data = str(tmp_path / "data")
    _write(os.path.join(data, "tape", "tape_NIFTY_2026-10-05.jsonl"), _gc_day("2026-10-05"))
    # 09:20 -> 09:45 expects 5 bars (09:20..09:40); drop two of them (60%) on the second day
    _write(os.path.join(data, "tape", "tape_NIFTY_2026-10-06.jsonl"), _gc_day("2026-10-06", skip=(2, 3)))
    ref = R.build("NIFTY", "2026-10-07", data)
    assert ref["wall_bin"]["585"]["n_days"] == 1
    assert ref["wall_bin"]["915"]["n_days"] == 2       # by 15:15 the two missing bars are under 20%
    assert ref["crosses"]["585"]["n_days"] == 1


def test_legs_is_board_js():
    b = lambda o, h, l, c: {"o": o, "h": h, "l": l, "c": c}   # noqa: E731
    bars = [b(99, 101, 99, 100), b(100, 131, 100, 130), b(130, 131, 100, 101), b(101, 102, 70, 72)]
    L = R.legs(bars, 25)
    assert [(x["i0"], x["i1"], x["dir"], x["open"]) for x in L] == [(0, 1, 1, False), (1, 3, -1, True)]
    assert L[0]["to"] == 131 and L[1]["from"] == 131 and L[1]["to"] == 70


def test_the_whole_reference_is_well_formed(tmp_path):
    data = str(tmp_path / "data")
    _fixture(data, ["2026-10-05", "2026-10-06"], [])
    ref = R.build("NIFTY", "2026-10-07", data)
    assert ref["v"] == 1 and ref["id"].startswith("rank-NIFTY-2026-10-07-") and len(ref["id"].rsplit("-", 1)[1]) == 8
    assert set(ref["wall_bin"]) == {str(c) for c in R.CHECKPOINTS} == set(ref["crosses"])
    assert ref["flow"]["size"] is not None and ref["flow"]["res_min"] == 0.25 and "37" in ref["flow"]["slot_absd"]
    assert ref["open_flow"]["n"] == 2 and ref["fuel"] is not None
    p = R.write(ref, str(tmp_path / "rank"))
    assert os.path.basename(p) == "rank_ref_NIFTY_2026-10-07.json" and json.load(open(p))["id"] == ref["id"]
    empty = R.build("NIFTY", "2026-10-01", data)
    assert empty["writers30"] is None and "writers30" in empty["why"] and empty["wall_bin"]["585"] is None


def test_v21_the_restored_kinds_rank_against_their_own_kind(tmp_path):
    """v2.1: exhaustion / initiative / vacuum / climax (board) and E2 / E3 (decoder lots) get their own era-B pools, so a
    restored or SAB MARKS mark ranks against its own kind, never against traps."""
    data = str(tmp_path / "data")
    for d in ("2026-10-05", "2026-10-06"):
        _write(os.path.join(data, "tape", f"tape_NIFTY_{d}.jsonl"), _gc_day(d, 1))
        _write(os.path.join(data, "tape", f"ofd_marks_NIFTY_{d}.jsonl"),
               [{"t": _t0(d), "kind": k, "side": 1, "p": 22500.0 + i, "size": 10 * (i + 1)}
                for i, k in enumerate(("exhaustion", "initiative", "vacuum", "climax"))])
        _write(os.path.join(data, "decoder", f"decoder_{d}.jsonl"),
               [{"row": "event", "kind": k, "idx": "NIFTY", "id": f"{k}@{d}", "event": {"lots": 70 + i}} for i, k in enumerate(("E2", "E3"))])
    m = R.build("NIFTY", "2026-10-07", data)["marks"]
    assert [m[k]["n"] for k in ("exhaustion", "initiative", "vacuum", "climax", "E2", "E3")] == [2] * 6
    assert m["vacuum"]["q"][100] == 30 and m["E3"]["q"][0] == 71



# ---- decode-loop Phase 1: THE READ's ranks ride the same reference (rank.py's definitions) ------------------------

def _ux_day(day, scale=1, n=75, expiry="2026-10-27"):
    rows = _gc_day(day, scale, n)
    for r in rows:
        r.pop("ladder", None)
        r.update(ik="NSE_FO|1", expiry=expiry)
    rows[0]["partial"] = True                                       # the 09:15 bar: the recorder starts ~09:17, always
    return rows


def test_the_read_section_is_one_reference_and_never_reads_a_day_on_or_after_before(tmp_path):
    data = str(tmp_path / "data")
    days, late = ["2026-10-05", "2026-10-06", "2026-10-07"], ["2026-10-08"]
    _fixture(data, days, late)
    for d in days + late:
        _write(os.path.join(data, "tape", f"ux_NIFTY_{d}.jsonl"), _ux_day(d, 50 if d in late else 1))
    _write(os.path.join(data, "surface", "surface_2026-10-06.jsonl"),
           [{"idx": "BANKNIFTY", "expiry": "2026-10-27"}, {"idx": "NIFTY", "expiry": "2026-10-06"}])
    ref = R.build("NIFTY", "2026-10-08", data)
    rd = ref["read"]
    assert rd["marks"]["ux"]["days"] == days and rd["marks"]["gc"]["days"] == days
    assert rd["kinds"]["2026-10-06"] == "EXPIRY"          # chain rows without `expiry`: the surface log's, never a weekday
    assert rd["kinds"]["2026-10-05"] == "NORMAL"
    cvd = rd["marks"]["ux"]["cvd"]["36000"]               # 09:15 .. 09:55 of +7/-7: the partial 09:15 bar counts
    assert cvd == [7, 7, 7] and len(rd["pool"]["NORMAL"]["ux"]["size"]) == 4
    for d in late:
        os.remove(os.path.join(data, "tape", f"ux_NIFTY_{d}.jsonl"))
    assert R.build("NIFTY", "2026-10-08", data)["read"] == rd   # a later day never moves it
    for k in ("wall_bin", "crosses", "open_flow", "fuel", "flow", "marks", "writers30"):   # the extension's, untouched
        assert k in ref



def test_a9_the_purest_exhaustion_ranks_highest_in_its_own_pool():
    """A9 (MARKS-EXPLAINED 12.3): ranked by eff, a new high made on NO buying (eff 0) ranks p0. Its own strength is the
    fade of effort at the extreme, 1 - eff / the leg's peak: the pure one is 1.0, a tired-but-still-pushing one 0.8."""
    def bar(i, c, d):
        return {"t": i * 300000, "o": c - 1, "h": c + 1, "l": c - 2, "c": c, "delta": d}
    up = lambda pushes: [bar(i, 100 + 10 * i, d) for i, d in enumerate(pushes)]      # noqa: E731 -- one up-leg, new highs
    assert R.exhaustion_fades(up([50, 500, 0])) == [1.0]                               # the new high on no buying
    assert R.exhaustion_fades(up([50, 500, 100])) == [0.8]
    assert R.exhaustion_fades(up([50, 500, 400])) == []                                # 80 % of the peak: not tired
    assert R.exhaustion_fades(up([50, 90, 0])) == []                                   # peak under board.js's 100 lots
    tab = R.quant([0.8, 0.9, 1.0, 0.5, 0.6])
    assert R.rank(tab, 1.0) > R.rank(tab, 0.8)                                         # purest ranks highest


def test_a45_slot_range_is_the_reference_days_median_bar_range_per_5_min_slot(tmp_path):
    data = str(tmp_path / "data")
    _fixture(data, ["2026-10-05", "2026-10-06"], ["2026-10-07"])            # the late day's bars are 50x as wide
    ref = R.build("NIFTY", "2026-10-07", data)
    assert ref["slot_range_src"] == "gc" and len(ref["slot_range"]) == 75 and "slot_range" not in ref["why"]
    assert ref["slot_range"]["0915"] == 12.0 and ref["slot_range"]["1525"] == 12.0    # never the day it serves
    part = _gc_day("2026-10-05")
    part[1]["partial"] = True
    assert R.slot_range({"d": [dict(b, s=int(b["t"] / 1000 + 19800) % 86400) for b in part[:2]]}) == {"0915": 12.0}
    for d in ("2026-10-05", "2026-10-06"):                                  # an index GoCharting never recorded: Upstox
        _write(os.path.join(data, "tape", f"ux_SENSEX_{d}.jsonl"), [dict(b, h=b["h"] + 1) for b in _gc_day(d)])
    sx = R.build("SENSEX", "2026-10-07", data)
    assert sx["slot_range_src"] == "ux" and sx["slot_range"]["0920"] == 13.0
    assert R.build("BANKNIFTY", "2026-10-07", data)["why"]["slot_range"].startswith("no ux 5-min bar")


def test_a45_the_frame_serves_the_current_slots_median_range():
    import server
    ref = {"slot_range": {"0915": 66.1, "0920": 31.4}, "slot_range_src": "gc"}
    assert server._slot_range_now(ref, 9 * 3600 + 22 * 60) == ({"0915": 66.1, "0920": 31.4}, None)   # this slot + the last
    assert server._slot_range_now(ref, 9 * 3600 + 16 * 60) == ({"0915": 66.1}, None)                 # nothing before 09:15
    assert server._slot_range_now(ref, 9 * 3600 + 26 * 60) == ({"0920": 31.4}, None)
    assert server._slot_range_now(ref, 9 * 3600 + 31 * 60)[1].startswith("could not check — no reference bar in the 09:30")
    assert server._slot_range_now({}, 9 * 3600 + 22 * 60)[1].startswith("could not check — this rank_ref has no slot_range")
    assert server._slot_range_now(ref, 15 * 3600 + 31 * 60) == (None, "not shown — outside today's 09:15-15:30 session")
    assert server._slot_range_now(ref, None)[0] is None
