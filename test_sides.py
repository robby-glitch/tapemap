"""sides.py / sides_log.py -- the OI flow split by side against the index move (Board round 4, rev sides-2).

Pinned on Thu 2026-10-01 from one frozen fixture of the saved chain
(`test/fixtures/sides_2026-10-01.json.gz`: data/chain_backfill + data/chain, the grid at
every minute, the open OI, the snapshot at each 5-minute mark, and 30 Sep's scale). The
definitions were fixed 2026-10-03 23:38 IST and amended 2026-10-04 00:25 IST and 01:25 IST
(docs/board/real-vs-fake-2026-10-03.md §2, §2a, §2b); a failing test here means a rule moved.

Nothing here tests that a read is RIGHT about the market -- only that the rules say what
they said, and that the log can never write a row twice or outside its session. A passing
suite is not evidence (CLAUDE.md rule 9).
"""
import gzip
import json
import os
from datetime import datetime

import chain_metrics
import sides
import sides_log

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test", "fixtures", "sides_2026-10-01.json.gz")
_D = {}


def _load(idx):
    if not _D:
        with gzip.open(FIX, "rt", encoding="utf-8") as f:
            _D.update(json.load(f)["idx"])
    d = _D[idx]
    opens = {(float(k.split("|")[0]), k.split("|")[1]): v for k, v in d["opens"].items()}
    book = {t: {float(k): {"ce": tuple(l["ce"]), "pe": tuple(l["pe"])} for k, l in legs.items()}
            for t, legs in d["book"].items()}
    return d["minutes"], opens, book, d["kal"]


def _read(idx, **kw):
    minutes, opens, book, kal = _load(idx)
    st = chain_metrics.ChainState()
    st.minutes = minutes
    args = dict(opens=opens, book=book, kal=kal)
    args.update(kw)
    return sides.read(st.oi_flow(interval=sides.INTERVAL), minutes, **args)


def _at(slots, t):
    return {x["t"]: x for x in slots}[t]


def test_1oct_1210_nifty_is_the_pushti_down_forced():
    s = _at(_read("NIFTY"), "12:10")
    assert (s["power"], s["pdir"], s["first"], s["word"], s["dir"]) == (True, -1, True, "REAL", -1)
    assert s["p_state"] == "COV" and s["p_power"] and s["top2_pe_agree"] == 2 and s["p_ratio"] >= sides.POWER_R
    assert s["fuel_side"] == "pe" and s["fuel_top2_underwater"] == 2       # her two put fronts' writers underwater
    assert s["M_basis"] == "today" and s["src"] == "live"


def test_1oct_1400_nifty_is_not_a_power_real_down():
    """Fable: on the 17-strike window it read a POWER REAL ▼ at the day's low. On the nine with her
    top-2 breadth it is no POWER slot; the nine's calls still add while her two CE fronts cover."""
    s = _at(_read("NIFTY"), "14:00")
    assert not (s["power"] and s["word"] == "REAL" and s["dir"] == -1)
    assert not s["power"]
    assert s["dce_top2"] < 0 < s["dce"] and s["top2_ce_agree"] == 0


def test_first_sign_rearms_only_after_the_opposite_power():
    s = _read("NIFTY")
    down_leg = [x["t"] for x in s if x["first"] and x["pdir"] == -1 and "12:10" <= x["t"] <= "13:45"]
    assert down_leg == ["12:10"]                                            # one sign in the 12:10-13:45 leg
    assert [x["t"] for x in s if x["power"] and x["pdir"] == -1 and "12:10" < x["t"] <= "13:45"]   # continuation there
    assert _at(s, "14:35")["first"] and _at(s, "14:35")["pdir"] == 1        # an up POWER slot re-armed nothing below


def test_morning_is_sized_on_kal_ki_subah_and_says_why_when_it_cannot():
    s = _read("NIFTY")
    assert _at(s, "09:20")["M_basis"] == "kal_morning" and _at(s, "09:20")["word"] is not None   # shown from 09:20
    assert _at(s, "10:30")["M_basis"] == "kal_morning" and _at(s, "10:35")["M_basis"] == "today"
    for f in ("c_ratio_kal_morning", "c_ratio_kal_midday", "c_ratio_today", "p_ratio_kal_morning", "I_ratio_kal_midday"):
        assert _at(s, "10:35")[f] is not None, f                                # every basis logged on every row
    kal = _load("NIFTY")[3]
    was_expiry = _read("NIFTY", kal=dict(kal, expiry_day=True))
    for x in was_expiry:
        if x["t"] <= "10:30":
            assert x["word"] is None and sides.KAL_EXPIRY in x["why"] and x["shown_why"] == "no_kal", x["t"]
    assert sides.KAL_EXPIRY == "could not check — subah ka scale — kal expiry din tha"
    blind = _read("NIFTY", kal=None)
    for x in blind:
        if x["t"] <= "10:30":
            assert x["word"] is None and x["shown_why"] == "no_kal" and sides.NO_KAL in x["why"], x["t"]
    assert sides.NO_KAL == "could not check — subah ka scale — kal ka data nahi"
    assert _at(blind, "10:35")["word"] is not None                          # from 10:30 on, today's own scale


def test_1oct_0935_is_a_morning_witness_not_a_counted_2of2_fake_and_1210_stays_the_pushti():
    by = {i: _read(i) for i in sides.IDXS}
    cx = sides.cross_at(by, "09:35")
    assert cx["n_weekly_power"] == 0 and cx["n_power"] == 0 and cx["morning_witness"]   # never a vote
    assert cx["n_weekly_power_witness"] == 1 and not _at(by["NIFTY"], "09:35")["power"]
    t = sides.three({i: _read(i, now="09:36") for i in sides.IDXS})
    assert t["dir_weekly"] is None and t["morning"] and sides.MORNING_TAG in t["tags"]
    assert "witness, gina nahi" in t["line1_weekly"]
    noon = sides.cross_at(by, "12:10")
    assert noon["n_weekly_power"] == 2 and noon["weekly_dir"] == -1
    assert _at(by["NIFTY"], "12:10")["first"] and _at(by["SENSEX"], "12:10")["first"]   # a witness never used it up


def test_the_read_word_table_and_its_mirror():
    w = sides.word
    assert w("UP", "COV", "ADD") == ("REAL", 1)
    assert w("UP", "COV", "FLAT") == ("SQUEEZE", 1)
    assert w("UP", "ADD", "ADD") == ("CAPPED", 1)
    assert w("UP", "ADD", "COV") == ("FAKE", 1)
    assert w("UP", "FLAT", "ADD") == ("BACKED", 1)
    assert w("UP", "FLAT", "COV") == ("HOLLOW", 1)
    assert w("UP", "FLAT", "FLAT") == ("QUIET", 1)
    assert w("DOWN", "ADD", "COV") == ("REAL", -1)
    assert w("DOWN", "COV", "ADD") == ("FAKE", -1)
    assert w("FLAT", "FLAT", "COV", False, True) == ("PRESSURE", -1)
    assert w("FLAT", "ADD", "FLAT", True, False) == ("WALL", 0)
    assert w(None, "ADD", "ADD") == (None, None)


def test_the_1515_freeze_says_why_and_an_open_slot_is_never_read():
    s = _read("NIFTY")
    late = _at(s, "15:20")
    assert late["word"] is None and sides.FROZEN in late["why"] and late["shown_why"] == "frozen"
    assert _read("NIFTY", now="12:10")[-1]["t"] == "12:05"                 # the 12:10 slot is still open at 12:10


def test_backfill_a_restart_at_1100_reads_every_slot_exactly_and_tags_the_rebuilt_ones():
    """ANYTIME START: the warm start replays the saved chain into the same grid, so a process up at
    11:00 reads 09:15-11:00 exactly as one that watched them -- and says so. No repaint either."""
    whole, restarted = _read("NIFTY"), _read("NIFTY", live_from="11:00")

    def key(x):
        return (x["t"], x["word"], x["dir"], x["power"], x["first"], x.get("c_ratio"), x.get("p_ratio"),
                x.get("fuel_top2_underwater"), x.get("fuel_gone_pct"))
    assert [key(x) for x in whole] == [key(x) for x in restarted]
    for x in restarted:
        assert x["src"] == ("backfill" if x["from"] <= "11:00" else "live"), x["t"]
    assert _at(whole, "09:20")["src"] == "backfill" and _at(whole, "09:20")["grid_src"] == "mixed"   # the 09:15 REST mark
    assert _at(restarted, "11:05")["grid_src"] == "mixed" and _at(restarted, "11:10")["src"] == "live"
    early = _read("NIFTY", now="11:00")
    assert [key(x) for x in early] == [key(x) for x in whole if x["t"] < "11:00"]


def test_three_counts_her_model_and_logs_the_weekly_one_a_missing_index_never_agrees():
    meta = {"NIFTY": {"dte": 5}, "BANKNIFTY": {"dte": 26}, "SENSEX": {"dte": 0, "expiry_day": True}}
    t = sides.three({i: _read(i, now="12:31") for i in sides.IDXS}, meta)
    assert t["t"] == "12:30" and t["dir"] == -1 and t["n_power"] == 3 and t["n_weekly_power"] == 2
    assert t["line1"].startswith("▼ PUT WRITERS KAAT RAHE · 3 of 3") and "BANKNIFTY (monthly · 26 DTE)" in t["line1"]
    assert "expiry din · SENSEX" in t["tags"]
    # Mary's count (2026-10-04, the default): the weekly books, BANKNIFTY a witness shown and never counted
    assert t["line1_weekly"].startswith("▼ PUT WRITERS KAAT RAHE · NIFTY+SENSEX 2/2") and t["dir_weekly"] == -1
    assert "BN saath ×4 · monthly · 26 DTE · gina nahi" in t["line1_weekly"] and t["dir"] == t["dir_weekly"]
    alone = sides.three({"NIFTY": _read("NIFTY", now="12:26"), "BANKNIFTY": _read("BANKNIFTY", now="12:26"),
                         "SENSEX": _read("SENSEX", now="12:26")}, meta)
    assert alone["dir_weekly"] == -1 and "BANKNIFTY" not in alone["line1_weekly"].split("·")[1]
    gone = sides.three({"NIFTY": _read("NIFTY", now="12:31"), "BANKNIFTY": [], "SENSEX": _read("SENSEX", now="12:16")})
    assert set(gone["missing"]) == {"BANKNIFTY", "SENSEX"} and gone["n_power"] <= 1


def test_outcome_and_the_previous_session_scale():
    minutes = _load("NIFTY")[0]
    o = sides.outcome(minutes, "12:10", -1)
    assert o["kind"] == "outcome" and o["f15"] is not None and o["f30"] is not None
    assert o["mfe30"] >= 0 >= o["mae30"]                                    # excursions signed in the sign's direction
    assert sides.outcome(minutes, "15:00", -1)["f30"] is None               # crosses the 15:15 freeze
    sc = sides.day_scale(_read("NIFTY"))
    for w in ("morning", "midday"):
        assert sc[w]["n"] > 0 and sc[w]["ce"] > 0 and sc[w]["pe"] > 0 and sc[w]["ix"] > 0, w


def test_the_live_kal_reads_yesterdays_rest_backfilled_minutes_like_the_frozen_runs(tmp_path):
    """Yesterday's chain file starts at the poller's first snapshot (09:17 on 1 Oct); the REST walk's
    09:15-09:16 marks live in data/chain_backfill/. The live scale must read both, as every frozen run
    does, or a morning slot reads differently live (1 Oct SENSEX 10:10, found 2026-10-04)."""
    import chain_backfill
    import chain_live
    import server
    minutes = _load("SENSEX")[0]
    rows, bf = [], []
    for t in sorted(minutes):
        x = minutes[t]
        if x.get("src") == "backfill":
            bf.append({"day": "2026-10-01", "index": "SENSEX", "t": t, "spot": x["spot"], "k": x["k"], "backfilled": True})
        else:
            rows.append({"ts": t + ":30", "spot": x["spot"], "expiry": "2026-10-01",
                         "strikes": [{"k": float(k), "ce": {"oi_chg": v[0]}, "pe": {"oi_chg": v[1]}} for k, v in x["k"].items()]})
    assert bf, "the fixture carries a REST-backfilled mark"
    os.makedirs(str(chain_live.CHAIN_DIR), exist_ok=True)
    with open(os.path.join(str(chain_live.CHAIN_DIR), "chain_SENSEX_2026-10-01.jsonl"), "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))
    os.makedirs(chain_backfill.DIR, exist_ok=True)
    with open(chain_backfill.path("2026-10-01", "SENSEX"), "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in bf))
    whole = {t: {"spot": x["spot"], "k": {float(k): tuple(v) for k, v in x["k"].items()}} for t, x in minutes.items()}
    st = chain_metrics.ChainState()
    st.minutes = whole
    want = sides.day_scale(sides.read(st.oi_flow(interval=sides.INTERVAL), whole, opens={}))
    server._SIDES_KAL.clear()
    got = server._sides_kal("SENSEX", "2026-10-05")
    server._SIDES_KAL.clear()
    assert got["day"] == "2026-10-01" and got["morning"] == want["morning"] and got["midday"] == want["midday"]


def test_the_log_writes_only_in_market_hours_once_per_row_and_only_todays_session(tmp_path):
    d, day = str(tmp_path), "2026-10-01"                      # a Thursday
    rows = [{"t": "12:05", "src": "live", "word": "REAL"}, {"t": "12:10", "src": "backfill", "word": "REAL"},
            {"t": "12:05", "kind": "outcome", "f30": -12.0}]

    def at(hm, dd=1):
        return datetime(2026, 10, dd, int(hm[:2]), int(hm[3:]), 30)
    assert sides_log.append(day, "NIFTY", rows, at("09:14"), d) == 0          # before the open
    assert sides_log.append(day, "NIFTY", rows, at("15:31"), d) == 0          # after the close
    assert sides_log.append(day, "NIFTY", rows, at("00:00", 2), d) == 0       # midnight: the 1 Oct trigger_log bug
    assert sides_log.append("2026-09-30", "NIFTY", rows, at("12:30"), d) == 0 # yesterday's grid, today's clock
    assert sides_log.append("2026-10-03", "NIFTY", rows, at("12:30", 3), d) == 0   # a Saturday
    assert not os.path.exists(sides_log.path_for(day, d))
    assert sides_log.append(day, "NIFTY", rows, at("12:10"), d) == 2          # 12:10 is still open at 12:10
    assert sides_log.append(day, "NIFTY", rows, at("12:11"), d) == 1
    assert sides_log.append(day, "NIFTY", rows, at("12:12"), d) == 0          # once
    sides_log._SEEN.clear()                                                   # a restarted process re-reads the file
    assert sides_log.append(day, "NIFTY", rows, at("12:20"), d) == 0
    with open(sides_log.path_for(day, d), encoding="utf-8") as f:
        got = [json.loads(x) for x in f]
    assert sorted((r["kind"], r["t"], r["src"] if r["kind"] == "slot" else None) for r in got) == [
        ("outcome", "12:05", None), ("slot", "12:05", "live"), ("slot", "12:10", "backfill")]
