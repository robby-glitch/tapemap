"""test_jarvis.py -- J2, the Jarvis brain (plan docs/superpowers/plans/2026-10-29-j2-jarvis-brain.md).

The record tests read the real day files READ-ONLY (conftest points every DIR at tmp; the `record` fixture points the
readers back at data/, and jarvis.build never writes) and are skipped when the day is absent. Their numbers are measured
(A155 / A157 / DAY-2026-10-29 §5); where the record and the plan differ, the test says so in its comment.
"""
import json
import os
import pathlib
import re

import pytest

import jarvis

# the call's words: the leg's (legs.py, 30 Oct) with its lean arrow, the vote's (29 Oct) kept for old frames, and P0's blind
WORDS = ("NO LEG", "OPENING", "ROTATION", "TREND", "HOLD", "WATCH", "PALAT?", "PALAT", "CAN'T SEE",
         "UP", "DOWN", "RANGE", "NO TRADE")
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_BUILT = {}


def _has(day):
    return any(os.path.exists(os.path.join(DATA, "book", f"book_NIFTY_{day}.jsonl{z}")) for z in ("", ".gz"))


@pytest.fixture
def record(monkeypatch):
    """The real record, read-only."""
    import book_log
    import chain_backfill
    import chain_live
    import dext_log
    import trigger_log
    monkeypatch.setattr(book_log, "DIR", os.path.join(DATA, "book"))
    monkeypatch.setattr(dext_log, "DIR", os.path.join(DATA, "dext"))
    monkeypatch.setattr(chain_backfill, "DIR", os.path.join(DATA, "chain_backfill"))
    monkeypatch.setattr(chain_live, "CHAIN_DIR", pathlib.Path(DATA, "chain"))
    monkeypatch.setattr(trigger_log, "PATH", os.path.join(DATA, "trigger_log.jsonl"))
    monkeypatch.setattr(jarvis, "MSG_DIR", os.path.join(DATA, "messages"))
    import confluence_log                                   # Task 5's sources (tape_log.DIR stays tmp: the leg's marks
    import day_state                                        # are not read here, so the prior POC / VAH / VAL say so)
    import decoder_log
    import squeeze_score
    monkeypatch.setattr(confluence_log, "PATH", os.path.join(DATA, "confluence_log.jsonl"))
    monkeypatch.setattr(day_state, "DIR", os.path.join(DATA, "day_state"))
    monkeypatch.setattr(decoder_log, "DIR", os.path.join(DATA, "decoder"))
    monkeypatch.setattr(squeeze_score, "BT", os.path.join(DATA, "backtest"))
    monkeypatch.setattr(jarvis, "RANK_DIR", os.path.join(DATA, "rank"))
    monkeypatch.setattr(jarvis, "DECODE_DIR", os.path.join(DATA, "decode"))
    monkeypatch.setattr(jarvis, "VPIN_FAST", os.path.join(DATA, "vpin_fast.jsonl"))


def build(day, upto):
    """One build per (day, upto) for the whole module: the record does not change under the tests."""
    if (day, upto) not in _BUILT:
        _BUILT[(day, upto)] = jarvis.build(day, "NIFTY", upto)
    return _BUILT[(day, upto)]


# ---- Task 1: the exporter as a pure, causal module ---------------------------------------------------------------------

@pytest.mark.skipif(not _has("2026-10-28"), reason="28 Oct record not present")
def test_28oct_the_break_the_fuel_and_the_verdict(record):
    d = build("2026-10-28", 13 * 60 + 41)
    assert d["mins"][0] == "09:15" and d["mins"][-1] == "13:40"
    toot = [p for p in d["pushes"] if p["t"] == "12:43"][0]
    assert toot["ans"] == "TOOT" and toot["held_at"] == "12:47"        # Dext flow + handshake-2 (A155)
    cover = [r for r in d["runs"] if r["kind"] == "COVER" and r["start"] == "12:41"][0]
    # A240: was 12:58 / -1726, read on a 5m bar filed as the 12:55 minute (its OI was 12:59's); the true minutes say 13:03
    assert cover["khatam"] == "13:03" and cover["lots"] == -2146
    assert d["verdict"]["SELL"]["12:12"]["word"] == "CHALEGA"           # CONTINUE: fuel x (cover -775)


@pytest.mark.skipif(not _has("2026-10-28"), reason="28 Oct record not present")
def test_causal_prefix(record):
    full = build("2026-10-28", 13 * 60 + 41)
    part = build("2026-10-28", 12 * 60 + 50)
    assert part["mins"][-1] == "12:49"
    for p in part["pushes"]:
        if p.get("held_at") or p.get("am"):
            assert any(q["t"] == p["t"] and q["ans"] == p["ans"] for q in full["pushes"])
    # the prefix's own minutes read the same in both: a read never changes when later minutes arrive
    n = len(part["mins"])
    assert part["timeline"][:n] == full["timeline"][:n]
    assert {m: v for m, v in full["verdict"]["SELL"].items() if m <= "12:49"} == part["verdict"]["SELL"]


# ---- Task 2: the reads move from the face into the brain (one brain) ---------------------------------------------------

@pytest.mark.skipif(not _has("2026-10-28"), reason="28 Oct record not present")
def test_28oct_top_signs_at_the_high(record):
    r = build("2026-10-28", 13 * 60 + 41)["reads"]
    s = [x for x in r["signs"] if x["isHigh"] and x["n"] == 3]
    assert s and s[0]["at"] == "13:03"                                   # red on +374, absorption, exhaustion (A157)
    assert [i.split(":")[0].split(" +")[0] for i in s[0]["items"]] == ["red candle, green delta", "absorption", "exhaustion"]
    # A BROKEN read late through a chain hole counts from its push minute (A176, decided as the trader): the 12:51 push's
    # 22,700s CE TOOT was read at 13:00 only because the chain was blind 12:55-12:59, so at 13:03 it is 11 min old
    # A240: the TOOT stays out, but on the true minutes the fut cover runs to 13:03 (not 12:58, a 5m bar's early OI)
    assert s[0]["driving"] and s[0]["drive"] == ["fut shorts covering −2,146"]
    early = [x for x in r["signs"] if x["isHigh"] and x["at"] in ("12:45", "12:48", "12:57")]
    assert early and all(x["driving"] for x in early)                    # cover still running: not a top yet


@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_29oct_writer_flow_sequence(record):
    d = build("2026-10-29", 11 * 60)
    st = {m: w["state"] for m, w in zip(d["mins"], d["reads"]["writers"]) if w["state"]}
    near = lambda hm, want: any(st.get(x) == want for x in (hm, f"{hm[:3]}{int(hm[3:]) - 1:02d}", f"{hm[:3]}{int(hm[3:]) + 1:02d}"))  # noqa: E731
    assert near("09:41", "UP") and near("09:44", "PAUSED") and near("10:38", "RISK")   # DAY §5, +/- 1 min


@pytest.mark.skipif(not (_has("2026-10-28") and _has("2026-10-29")), reason="28 / 29 Oct records not present")
def test_risk_is_an_event_not_the_rest_of_the_day(record):
    """G2 (30 Oct, DECODE-GAPS): RISK sat 10:38-12:50 on 29 Oct, a day that closed +236 (149 of 386 minutes), and from
    13:19 to the close on 28 Oct (142). It now ends at a new extreme the leg's way, when the writers come back, or after
    RISK_HOLD minutes unless price went against the leg."""
    for day in ("2026-10-28", "2026-10-29"):
        d = build(day, 15 * 60 + 41)
        assert sum(w["state"] == "RISK" for w in d["reads"]["writers"]) < 40
        assert not any("RISK since" in x for x in d["call"]["why"])          # 28 Oct read "TOP RISK since 13:19" at 15:40
    st = {m: w["state"] for m, w in zip(d["mins"], d["reads"]["writers"])}
    assert st["10:38"] == "RISK" and st["10:44"] == "BACK" and st["12:30"] != "RISK"


@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_a_writer_leg_can_run_on_one_side(record):
    """G3 (30 Oct): the ±7 states read UP for 33 minutes on 29 Oct (+236), because a leg needed BOTH sides past 10L. A
    leg may now start or come back on one side alone (10:08: call writers -27.9L, puts +9.7L) and becomes two-sided when
    the other side joins (10:10: CE -47L, PE +27L)."""
    d = build("2026-10-29", 11 * 60)
    w = {m: (x["state"], x["legs"], x["ev"]) for m, x in zip(d["mins"], d["reads"]["writers"])}
    assert w["10:08"] == ("BACK", "calls", "BACK") and w["10:10"][:2] == ("UP", "both")


@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_manage_judges_the_trade_against_price(record):
    d = build("2026-10-29", 12 * 60)
    for m in d["reads"]["manage"]:
        assert not (m["st"] == "HOLD" and m["pts"] < 0)                  # the -120 pts HOLD bug (GAPS §1)
        assert m["pts"] > -15 or m["st"] == "AGAINST YOU"


def test_reads_on_a_toy_frame():
    """The ported rules on numbers small enough to check by hand: SPEED against its own median, ALL 3, and a missing
    minute named, never read as zero."""
    n = 30
    d = {"mins": [f"10:{i:02d}" for i in range(n)], "fut": [100.0 + i for i in range(n)], "fo": [99.5 + i for i in range(n)],
         "fhi": [101.0 + i for i in range(n)], "flo": [99.0 + i for i in range(n)], "delta": [10] * n, "fvol": [100] * n,
         "bnf": [200.0 + 6 * i for i in range(n)], "sx": [300.0 + 8 * i for i in range(n)], "vwap": [110.0] * n, "sd": [5.0] * n,
         "timeline": [{"fuel": None, "fuel_state": "-"}] * n, "runs": [], "pushes": [], "zone": [], "holes": [],
         "chain_missing": [], "sides": None, "wf_ce": [None] * n, "wf_pe": [None] * n, "bar": 500, "fights": []}
    d["delta"][20] = 70                                                  # a burst: 3-min |delta| 90 vs median 30 -> x3 FAST
    d["delta"][25] = None                                                # Dext missing that minute (and no book flow given)
    r = jarvis.reads(d)
    assert r["speed"][20]["word"] == "FAST" and r["speed"][20]["x"] == 3.0 and r["speed"][20]["dir"] == 1
    assert r["speed"][25]["word"] == "?" and r["speed"][25]["x"] is None   # a missing minute is not a zero
    assert r["sync"][10] == {"dir": 0, "ch": [5.0, 30.0, 40.0]}          # NIFTY +5 < 10: not in sync
    assert all(w["state"] is None for w in r["writers"])                 # no chain: no writer state, never a guess


# ---- Task 3: health and the ONE CALL (GAPS §4) --------------------------------------------------------------------------

@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_29oct_health_names_dext_missing(record, tmp_path, monkeypatch):
    """DAY §7: at 15:11 the Dext footprint was missing since 14:45. THE RECORD NO LONGER SHOWS IT: the Dext tab re-sent
    14:45-15:39 after the close (the candle file was last written 18:27), so this replays the record as it stood live --
    the candle rows before 14:45, in tmp -- which the live handshake log corroborates (its 14:53 and 15:06 pushes read the
    book, src B)."""
    import json
    import dext_log
    os.makedirs(tmp_path / "dext")
    with open(os.path.join(DATA, "dext", "dext_NSE-61471_2026-10-29.jsonl"), encoding="utf-8") as f, \
            open(tmp_path / "dext" / "dext_NSE-61471_2026-10-29.jsonl", "w", encoding="utf-8") as g:
        g.writelines(ln for ln in f if json.loads(ln)["time"][11:16] < "14:45")
    monkeypatch.setattr(dext_log, "DIR", str(tmp_path / "dext"))
    d = jarvis.build("2026-10-29", "NIFTY", 15 * 60 + 11)
    h = d["health"]
    assert any(a <= "14:46" and b >= "15:10" for a, b in h["dext"]["missing"])      # DAY §7: missing since 14:45
    assert h["dext"]["book_only_tail"] == 26                                         # 14:45-15:10, read from the book
    assert any("Dext footprint missing since 14:45" in x for x in d["call"]["missing"])
    assert d["reads"]["speed"][-1]["word"] != "?"                                   # the reads go on, from the book's flow


@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_29oct_call_at_1040_names_the_risk(record):
    c = build("2026-10-29", 10 * 60 + 40)["call"]
    assert c["action"]["said"] != "UP" and "RISK" in " ".join(c["why"]).upper()               # 10:38 TOP RISK


@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_the_call_has_both_expressions_a_wrong_line_and_no_rate(record):
    d = build("2026-10-29", 11 * 60)
    c = d["call"]
    assert c["action"]["said"].rstrip(" ▲▼") in WORDS and c["word"].startswith(("TREND", "RANGE", "OPENING")) and c["v1"]["word"] in ("UP", "DOWN", "RANGE", "NO TRADE")
    assert c["buyer"] and c["seller"] and c["wrong_line"] and c["up"] and c["dn"]
    blob = json.dumps({k: d[k] for k in ("call", "health", "reads")}, ensure_ascii=False)
    assert not any(w in blob.lower() for w in ("%", "hit rate", "win rate", "odds")) and "order" not in c["buyer"] + c["seller"]
    assert d["health"]["not_read"]                                                   # GAPS §5: every "—" row named


@pytest.mark.skipif(not _has("2026-10-28"), reason="28 Oct record not present")
def test_the_reads_are_causal_too(record):
    for upto in (13 * 60 + 41, 12 * 60 + 50):                         # the fail-soft fallback cannot pass this trivially
        assert not any("the ACTION word failed" in x for x in build("2026-10-28", upto)["health"]["notes"])
    full = build("2026-10-28", 13 * 60 + 41)["reads"]
    part = build("2026-10-28", 12 * 60 + 50)["reads"]
    n = len(part["speed"])
    assert len(part["action"]) == n and len(full["action"]) == len(full["speed"])
    for k in ("speed", "sync", "writers", "trade", "action"):
        assert part[k] == full[k][:n], k
    assert part["signs"] == [s for s in full["signs"] if s["b"] < n]
    assert part["manage"] == [m for m in full["manage"] if m["b"] + 1 < n]


# ---- Task 4: the server serves it; the incremental reader ---------------------------------------------------------------

def test_the_incremental_reader_equals_a_full_read_and_rereads_after_a_truncation(tmp_path):
    import confluence_log
    import tailread
    p = str(tmp_path / "day.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.write('{"t": 1}\n{"t": 2}\n')
    assert tailread.rows(p) == [{"t": 1}, {"t": 2}]
    with open(p, "a", encoding="utf-8") as f:
        f.write('{"t": 3}\nnot json\n{"t": 4')                          # a bad line, and a torn last line
    assert tailread.rows(p) == list(confluence_log._rows(p)) == [{"t": 1}, {"t": 2}, {"t": 3}]
    with open(p, "a", encoding="utf-8") as f:
        f.write('}\n')                                                    # the torn line completes
    assert tailread.rows(p) == list(confluence_log._rows(p)) == [{"t": 1}, {"t": 2}, {"t": 3}, {"t": 4}]
    got = tailread.rows(p)
    got.append({"t": 99})                                                 # a caller's list is its own
    assert tailread.rows(p)[-1] == {"t": 4}
    with open(p, "w", encoding="utf-8") as f:                             # shrank: read again from the start
        f.write('{"t": 7}\n')
    assert tailread.rows(p) == [{"t": 7}]
    assert tailread.rows(str(tmp_path / "missing.jsonl")) == []


MOCK = "2026-01-05"                                                      # a Monday, long past


def _mock_day():
    """A synthetic NIFTY morning, 09:10-10:00, in the conftest tmp dirs: the 1-second book every 10 s (ltp rising 1 pt a
    minute, OI flat, volume), and one chain snapshot a minute (spot = fut - 60, nine strikes, OI flat)."""
    import json as _j
    from datetime import datetime
    import book_log
    import chain_live
    from chain_live import IST
    os.makedirs(book_log.DIR, exist_ok=True)
    os.makedirs(str(chain_live.CHAIN_DIR), exist_ok=True)
    t0 = datetime(2026, 1, 5, 9, 10, tzinfo=IST).timestamp() * 1000
    with open(book_log.day_path(MOCK, "NIFTY"), "w", encoding="utf-8") as f:
        for s in range(0, 50 * 60, 10):
            p = 22700 + s / 60
            f.write(_j.dumps({"t": t0 + s * 1000, "ltp": p, "vtt": 1000 + 65 * s, "oi": 1.6e7, "b": [[p - 0.5, 65]],
                              "a": [[p, 65]], "ik": "NSE_FO|1"}) + "\n")
    with open(os.path.join(str(chain_live.CHAIN_DIR), f"chain_NIFTY_{MOCK}.jsonl"), "w", encoding="utf-8") as f:
        for m in range(9 * 60 + 15, 10 * 60):
            spot = 22700 + (m - 550) - 60
            f.write(_j.dumps({"ts": f"{m // 60:02d}:{m % 60:02d}:30", "spot": spot, "strikes": [
                {"k": k, "ce": {"oi": 5e6, "oi_chg": 0.0, "ltp": 50.0}, "pe": {"oi": 5e6, "oi_chg": 0.0, "ltp": 50.0}}
                for k in range(22450, 22900, 50)]}) + "\n")


def test_the_jarvis_route_serves_a_frame_and_refuses_a_past_day_in_market_hours(monkeypatch):
    from datetime import datetime
    import server
    from chain_live import IST
    from test_senses_api import _Cap
    _mock_day()
    monkeypatch.setattr(server, "_JARVIS", {})
    clock = {"now": datetime(2026, 1, 7, 18, 0, tzinfo=IST)}             # a Wednesday evening
    monkeypatch.setattr(server, "_ist", lambda now=None: clock["now"])

    def get(path):
        cap = _Cap(path)
        server.Handler.do_GET(cap)
        return cap.sent
    out = get(f"/api/jarvis?idx=NIFTY&day={MOCK}&upto=09:50")
    assert out["ok"] and out["mins"][0] == "09:15" and out["mins"][-1] == "09:49" and out["idx"] == "NIFTY"
    assert out["call"]["action"]["said"].rstrip(" ▲▼") in WORDS and out["health"]["dext"]["minutes"] == 0
    assert any("Dext footprint missing" in x for x in out["call"]["missing"])  # no Dext on this day: named, never a zero
    clock["now"] = datetime(2026, 1, 7, 11, 0, tzinfo=IST)               # in market hours: a past day is not replayed
    out = get(f"/api/jarvis?idx=NIFTY&day={MOCK}&upto=09:50")
    assert not out["ok"] and "15:40" in out["why"]
    assert not get("/api/jarvis?idx=NIFTY&day=yesterday")["ok"]


def test_writers_fuel_counts_a_squeeze_and_a_covering_side_alone():
    """A176 (decided as the trader): Sides SQUEEZE with the other side FLAT is writers' fuel its way; WRITER FLOW ±7 counts
    a covering side alone <= -10L / 3 min while the other side is not covering against it (>= -2L). Both covering, or the
    other side covering, is not fuel. The ±7 STATES (UP / PAUSED / BACK / RISK) keep DAY §5's two-leg rule."""
    assert jarvis.sides_fuel({"word": "SQUEEZE", "fuel_side": "ce", "c": "COV", "p": "FLAT"}) == 1
    assert jarvis.sides_fuel({"word": "SQUEEZE", "fuel_side": "pe", "c": "FLAT", "p": "COV"}) == -1
    assert jarvis.sides_fuel({"word": "SQUEEZE", "fuel_side": "ce", "c": "COV", "p": "COV"}) is None
    assert jarvis.sides_fuel({"word": "REAL", "fuel_side": "ce", "c": "COV", "p": "ADD"}) == 1
    assert jarvis.sides_fuel({"word": "CAPPED", "fuel_side": "ce", "c": "ADD", "p": "ADD"}) is None
    assert jarvis.wf_push(-39.5, 2.6) == 1 and jarvis.wf_push(-16.0, 7.8) == 1 and jarvis.wf_push(-11.0, -1.5) == 1
    assert jarvis.wf_push(-16.0, -3.0) is None and jarvis.wf_push(-9.9, 0.0) is None
    assert jarvis.wf_push(1.0, -12.0) == -1 and jarvis.wf_push(-2.5, -12.0) is None


# ---- P0 (30 Oct, JARVIS-DAY-2026-10-30): the saved tape rebuilds a book hole; a blind frame says so ----------------------

def _ms(day, hhmm):
    """Epoch ms of HH:MM IST on `day`."""
    import datetime as dt
    t = dt.datetime.strptime(f"{day} {hhmm}", "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30)))
    return int(t.timestamp() * 1000)


def test_the_tape_rebuilds_a_hole_only_from_when_it_was_seen():
    """A bar keeps the time it was FIRST saved; a replay at minute m uses only the bars live Jarvis had by then, so an
    outage stays blind in the replay and is rebuilt from the reconnect on (30 Oct lost 78 minutes for good)."""
    day = "2026-10-30"
    bar = lambda c: {"t": "12:45", "fut": {"o": c, "h": c + 2, "l": c - 2, "c": c, "v": 10, "oi": 15_800_000}}
    assert jarvis.save_tape("NIFTY", {"day": {"date": day, "bars": [bar(23_100.0)]}}, now_ms=_ms(day, "13:31")) == 1
    jarvis.save_tape("NIFTY", {"day": {"date": day, "bars": [bar(23_105.0)]}}, now_ms=_ms(day, "13:40"))   # revised later
    tape = json.load(open(jarvis.tape_path(day, "NIFTY"), encoding="utf-8"))
    assert tape["12:45"][3] == 23_105.0 and tape["12:45"][6] == _ms(day, "13:31")   # the value moves, first-seen does not
    F, src = jarvis._fut_bars(None, day, [], 13 * 60 + 40, "NIFTY")
    assert src.get("12:45") == "tape" and F["12:45"][4] == 23_105.0
    F, src = jarvis._fut_bars(None, day, [], 13 * 60, "NIFTY")            # at 13:00 it had not been seen: still a hole
    assert "12:45" not in F
    F, src = jarvis._fut_bars(None, day, [], 13 * 60, "NIFTY", fill=True)  # her backtest (31 Oct): fill ignores first-seen
    assert src.get("12:45") == "tape" and F["12:45"][4] == 23_105.0


@pytest.mark.skipif(not _has("2026-10-30"), reason="30 Oct record not present")
def test_a_blind_frame_says_cant_see_and_carries_nothing(record):
    """30 Oct 12:41-13:30 the book was empty (her internet): at 13:00 the newest minute is 12:41. The call said "NO TRADE
    -- writers and flow do not agree" off 12:41's data; it now says CAN'T SEE and names the blind span. After the close
    (15:40) a frame that ends at 15:39 is not blind."""
    c = build("2026-10-30", 13 * 60)["call"]
    assert c["word"] == "CAN'T SEE" and "blind since 12:41" in " ".join(c["why"])
    assert c["missing"][0].startswith("BLIND since 12:41") and c["buyer"].startswith("wait")
    assert build("2026-10-30", 15 * 60 + 41)["call"]["word"] != "CAN'T SEE"


# ---- Jarvis v3 Task 1: the word that holds, decided by the writers ------------------------------------------------------

def _toy(n=40, lean=-1):
    """A 40-minute down-leg from 10:00 with every count piece settable."""
    fut = [23100.0 - 3 * i for i in range(n)]
    d = {"mins": [f"{10 + i // 60:02d}:{i % 60:02d}" for i in range(n)], "fut": fut, "fo": [x + 1 for x in fut],
         "fhi": [x + 2 for x in fut], "flo": [x - 2 for x in fut], "spot": [x - 50 for x in fut], "delta": [-40] * n,
         "fvol": [120] * n, "bnf": [54000.0 - 8 * i for i in range(n)], "sx": [74000.0 - 12 * i for i in range(n)],
         "vwap": [23080.0] * n, "sd": [20.0] * n, "oi": [16000.0] * n, "step": 50, "bar": 500,
         "timeline": [{"fuel": None, "fuel_state": "-", "fronts": [{"k": 22900.0, "side": "PE", "state": "UNWINDING", "oi": 90.0, "chg": -4.0, "peak": 94.0}]}] * n,
         "runs": [], "pushes": [], "zone": [], "holes": [], "chain_missing": [], "fights": [],
         "sides": [{"t": "10:05", "c": "ADD", "p": "COV", "word": "REAL", "fuel_side": "pe", "uw": 2}],
         "wf_ce": [12.0] * n, "wf_pe": [-14.0] * n, "upto": "10:40", "live_from": "09:15"}
    return d


def test_count_reads_writers_first_and_never_counts_a_question_mark():
    d = _toy()
    d["reads"] = jarvis.reads(d)
    d["legs"] = {"rows": [{"t": m, "lean": -1, "word": "TREND", "leg": {"dir": -1}} for m in d["mins"]],
                 "day": {"flips": [0] * len(d["mins"]), "fut_oi": [None] * len(d["mins"])}, "pauses": [], "missing": []}
    c = jarvis.count(d, len(d["mins"]) - 1)
    assert [p["k"] for p in c["pieces"]][:5] == ["sides", "wf7", "wall_ahead", "answer", "trapped"]
    assert c["pieces"][0]["side"] == "with" and c["pieces"][2]["side"] == "with"      # Sides REAL pe-fuel, wall ahead UNWINDING
    assert c["pieces"][5]["side"] == "?"                                             # no 30-min story: could not check
    assert c["N"] == c["with"] + c["against"] and c["unread"] >= 1
    assert "%" not in json.dumps(c)
    assert c["pieces"][5]["text"] == "no 30-min story"                               # OI now and 30 min ago: checked
    assert jarvis.count(d, 10)["pieces"][5]["text"] == "could not check — fut OI needs 30 min of OI"   # rule 6


def test_action_word_needs_two_closes_and_palat_at_once():
    d = _toy()
    d["reads"] = jarvis.reads(d)
    rows = [{"t": m, "lean": -1, "word": "TREND" if i < 20 else "WATCH", "leg": {"dir": -1}} for i, m in enumerate(d["mins"])]
    rows[30] = dict(rows[30], word="PALAT", lean=1)
    d["legs"] = {"rows": rows, "day": {"flips": [0] * 30 + [1] * 10, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    a = jarvis.action_words(d)                                   # the per-minute ACTION series reads() stores
    assert a[0]["word"] == "HOLD"                                # the first word, at once, but by the count (WITH 1)
    assert a[7]["word"] == "HOLD" and a[8]["word"] == "TREND"    # TREND needs two closes (10:05, 10:08)
    assert a[21]["word"] == "TREND"                              # one close of the pause does not flip it
    assert a[26]["word"] == "HOLD"                               # two consecutive closes do (10:20 and 10:23); the leg's
                                                                 # WATCH is HOLD while the count is with the lean (ruling 2)
    assert a[30]["word"] == "PALAT" and a[30]["since"] == "10:30"   # the lean flip speaks at once
    assert all("%" not in x["why"] for x in a)


def test_on_a_trend_leg_watch_needs_the_count_to_turn():
    """Ruling 2 (1 Nov): in a pause the leg's HOLD and WATCH are both HOLD, the leg's risk items a chip in `why`; WATCH only
    when the count has turned against the lean (AGAINST > WITH) at two consecutive closes. Ruling 1: OPENING has no arrow."""
    d = _toy()
    leg = {"dir": -1, "quality": "TREND", "retrace": 0.1}
    risk = [{"k": "premium_bleeding"}, {"k": "mark_against"}]
    rows = [{"t": m, "lean": -1, "word": "TREND" if i < 20 else "WATCH", "risk": [] if i < 20 else risk, "leg": leg}
            for i, m in enumerate(d["mins"])]
    d["legs"] = {"rows": rows, "day": {"flips": [0] * 40, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    d["reads"] = jarvis.reads(d)
    a = jarvis.action_words(d)
    assert a[23]["word"] == "HOLD" and " · 2 risk · " in a[23]["why"]           # the leg says WATCH, the count says with
    # from 10:20 the count turns: call writers cover (±7 UP), Sides call-fuel, the PE wall below builds
    d["wf_ce"], d["wf_pe"] = [12.0] * 20 + [-14.0] * 20, [-14.0] * 20 + [12.0] * 20
    d["sides"] = d["sides"] + [{"t": "10:20", "c": "COV", "p": "ADD", "word": "REAL", "fuel_side": "ce", "uw": 1}]
    d["timeline"] = d["timeline"][:20] + [{"fuel": None, "fuel_state": "-", "fronts": [
        {"k": 22900.0, "side": "PE", "state": "BUILDING", "oi": 99.0, "chg": 4.0, "peak": 99.0}]}] * 20
    d["reads"] = jarvis.reads(d)
    a = jarvis.action_words(d)
    assert a[20]["count"]["against"] > a[20]["count"]["with"]
    assert a[22]["word"] == "TREND" and a[23]["word"] == "WATCH" and a[23]["since"] == "10:23"   # closes 10:20 and 10:23
    assert "the count turned" in a[23]["why"]
    assert jarvis.said("OPENING", -1) == "OPENING" and jarvis.said("HOLD", -1) == "HOLD ▼"


def _pause_toy(word, risk, retrace):
    """The toy leg TREND to 10:19, then `word` with `risk` items and `retrace` from 10:20."""
    d = _toy()
    d["reads"] = jarvis.reads(d)
    rows = [{"t": m, "lean": -1, "word": "TREND" if i < 20 else word, "risk": [] if i < 20 else risk,
             "leg": {"dir": -1, "quality": "TREND", "retrace": 0.05 if i < 20 else retrace}} for i, m in enumerate(d["mins"])]
    d["legs"] = {"rows": rows, "day": {"flips": [0] * 40, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    return d


def test_palatq_by_two_closes_or_at_one_close_on_a_deep_retrace():
    """PALAT? with its condition (>= 3 risk items) needs two consecutive closes (10:20, 10:23); 0.35 of the leg back
    (geometry, not an opinion) speaks at its first close (10:20)."""
    a = jarvis.action_words(_pause_toy("PALAT?", [{"k": "band_emptying"}, {"k": "delta_against"}, {"k": "mark_against"}], 0.2))
    assert a[22]["word"] == "TREND" and a[23]["word"] == "PALAT?" and "2 closes" in a[23]["why"]
    a = jarvis.action_words(_pause_toy("PALAT?", [], 0.4))
    assert a[19]["word"] == "TREND" and a[20]["word"] == "PALAT?" and "retrace 0.40" in a[20]["why"]


def test_the_answer_piece_reads_who_won_the_push():
    """The lean's own push BROKEN -> with; a push against it DEFENDED by writers -> with (the floor / cap behind held);
    TIKI by buyers (GHUSE) -> "?", never a defence."""
    d = _pause_toy("HOLD", [], 0.1)

    def answer(**p):
        d["pushes"] = [dict({"t": "10:30", "m": 630, "am": "10:33", "k": 22950.0, "side": "PE", "who": "WRITERS",
                             "artifact": False}, **p)]
        return jarvis.count(d, 36)["pieces"][3]
    assert answer(dir=-1, ans="TOOT") == {"k": "answer", "side": "with", "text": "last answer 10:30 push ▼ 22,950s PE BROKEN",
                                          "state": "with"}
    assert answer(dir=1, ans="TIKI", side="CE")["side"] == "with"
    assert answer(dir=1, ans="TOOT", side="CE")["side"] == "against"
    got = answer(dir=1, ans="TIKI", side="CE", who="KHAREEDAR")
    assert got["side"] == "?" and got["text"].endswith("buyers in at the wall")
    assert answer(dir=-1, ans="TOOT", am="10:36")["side"] == "?"          # read at 10:36: known from 10:37, not at 10:36


def test_the_entry_guidance_keys_on_the_legs_own_word():
    """The ACTION word is the holder's; a new entry keys on the leg's word: the leg's WATCH (ACTION HOLD) says hold, no new
    one; the leg's HOLD says buy the pullback; an ACTION PALAT? outlasting the leg's (the leg back to HOLD) says no new."""
    def frame(raw, palat_tail=False):
        d = _pause_toy(raw, [{"k": "premium_bleeding"}, {"k": "mark_against"}] if raw == "WATCH" else [], 0.1)
        if palat_tail:                                           # the leg's PALAT? 10:20-10:24 (0.40 back), then HOLD
            for r in d["legs"]["rows"][20:25]:
                r.update(word="PALAT?", leg=dict(r["leg"], retrace=0.4))
        g = {"dir": -1, "quality": "TREND", "pts": 117, "sigma_max": 2.1, "toot": None, "fuelled": None, "origin": 23102.0,
             "origin_t": "10:00", "extreme": 22985.0, "extreme_t": "10:30"}
        for r in d["legs"]["rows"]:
            r.update(leg=dict(g, retrace=r["leg"]["retrace"]), line=r["word"], alive=[], notes=[], missing=[])
        d["verdict"] = {"BUY": {}, "SELL": {}}
        d["health"] = jarvis.health(d, None)
        d["reads"]["action"] = jarvis.action_words(d)
        return d
    c = jarvis.call(frame("WATCH"))
    assert c["word"] == "HOLD ▼" and c["state"] == "WATCH" and "no new one while WATCH" in c["buyer"]
    c = jarvis.call(frame("HOLD"))
    assert c["word"] == "HOLD ▼" and "on the pullback" in c["buyer"]
    c = jarvis.calls(frame("HOLD", palat_tail=True))[27]                # 10:27: two closes of HOLD not yet (10:26, 10:29)
    assert c["word"] == "PALAT? ▼" and c["state"] == "HOLD" and c["buyer"].startswith("no new PE")


def test_the_wall_behind_broken_speaks_at_once_and_a_latched_palatq_waits():
    """EXIT-class: a push against the lean that BROKE the wall behind turns TREND / HOLD into WATCH at once, its why names
    the break. A PALAT? the leg only latched (its condition gone at the close) is a WATCH candidate, never PALAT?."""
    d = _toy()
    d["reads"] = jarvis.reads(d)
    rows = [{"t": m, "lean": -1, "word": "TREND", "risk": [], "leg": {"dir": -1, "quality": "TREND", "retrace": 0.1}}
            for m in d["mins"]]
    d["pushes"] = [{"t": "10:12", "m": 612, "dir": 1, "ans": "TOOT", "am": "10:13", "k": 23000.0, "side": "CE",
                    "who": "WRITERS", "artifact": False}]
    d["legs"] = {"rows": rows, "day": {"flips": [0] * 40, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    a = jarvis.action_words(d)
    assert a[13]["word"] == "TREND"                              # read at 10:13: known the minute after (final_ans)
    assert a[14]["word"] == "WATCH" and a[14]["since"] == "10:14"   # at once, not at a close (10:14 is not one)
    assert "BROKEN" in a[14]["why"] and "10:12" in a[14]["why"]
    for r in rows[20:]:
        r.update(word="PALAT?", risk=[{"k": "delta_against"}])     # latched by the leg, one risk item, 0.10 back
    a = jarvis.action_words(d)
    assert not any(x["word"] == "PALAT?" for x in a)


def test_banknifty_says_its_oi_cannot_answer_once():
    """G14: a BANKNIFTY frame whose chain OI never moves 3L in 3 min names it once; other frames keep the cross-index line."""
    d = _toy()
    d["idx"] = "BANKNIFTY"
    notes = jarvis.health(d, False)["notes"]
    assert notes.count("BANKNIFTY chain OI too small to answer pushes (G14)") == 1
    d["idx"] = "NIFTY"
    assert not any("G14" in x for x in jarvis.health(d, False)["notes"])


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="the plan's bar (<= 15 changes net of lean flips) is not met: 19 on 21 Oct, on this "
                                       "test record and the full record alike; .superpowers/sdd/task-1-report.md, Fix report")
@pytest.mark.skipif(not _has("2026-10-21"), reason="21 Oct record not present")
def test_21oct_the_word_holds_in_a_one_way_leg(record):
    d = jarvis.build("2026-10-21", "NIFTY", None, fill=True)
    words = [c["action"]["said"] for c in jarvis.calls(d)]
    net = sum(1 for a, b in zip(words, words[1:]) if a != b and "PALAT" not in (a.split()[0], b.split()[0]))
    assert net <= 15, net                                         # was 78; net of lean flips (ruling 3), 0 here after 10:00
    palatq = sum(1 for a, b in zip(words, words[1:]) if b.startswith("PALAT?") and not a.startswith("PALAT?"))
    assert palatq <= 2, palatq                                    # was 9 in a 473-pt down leg that reversed 0 times
    assert any(w.startswith("TREND ▼") for w in words[35:50])     # the first-hour trend call survives (09:50-10:05)


@pytest.mark.skipif(not _has("2026-10-21"), reason="21 Oct record not present")
def test_21oct_one_trend_call_and_at_most_two_palatq(record):
    """The parts of 21 Oct's bar the rules meet (the xfail above stops at its first assert): PALAT? at most twice in a
    473-pt down leg that reversed 0 times after 10:00 (was 9), and the first-hour TREND ▼ said by 10:05."""
    d = jarvis.build("2026-10-21", "NIFTY", None, fill=True)
    words = [c["action"]["said"] for c in jarvis.calls(d)]
    assert sum(1 for a, b in zip(words, words[1:]) if b.startswith("PALAT?") and not a.startswith("PALAT?")) <= 2
    assert any(w.startswith("TREND ▼") for w in words[35:50])


@pytest.mark.skipif(not _has("2026-10-30"), reason="30 Oct record not present")
def test_30oct_the_opening_is_not_announced(record):
    d = jarvis.build("2026-10-30", "NIFTY", None, fill=True)
    assert len(d["reads"]["action"]) == len(d["mins"]) and not any("the ACTION word failed" in x for x in d["health"]["notes"])
    early = [c["action"]["said"] for c in jarvis.calls(d) if c["at"] < "10:00"]
    assert all(w.startswith("OPENING") or w in ("NO LEG",) for w in early), set(early)


@pytest.mark.skipif(not (_has("2026-10-29") and any(os.path.exists(os.path.join(DATA, "book", f"book_SENSEX_2026-10-29.jsonl{z}"))
                                                     for z in ("", ".gz"))), reason="29 Oct SENSEX record not present")
def test_29oct_sensex_reads_niftys_flow(record):
    """G13 (§1q): SENSEX has no footprint of its own; its frame reads NIFTY's flow (29 Oct: 384 minutes of speed "?")."""
    d = jarvis.build("2026-10-29", "SENSEX", 11 * 60, fill=True)
    assert "N" in d["flow_src"] and "flow from NIFTY (§1q)" in d["health"]["method"]   # A231: method, not a gap
    assert sum(s["word"] == "?" for s in d["reads"]["speed"]) <= 15                  # the 10-bar warm-up and the first 2 min
    assert d["call"]["count"]["pieces"][6]["k"] == "speed"


# ---- Jarvis v3 Task 5: what the tool already measures (HOW MUCH, WHERE, EXPRESSION, her trade, the reads) ----------------

LEVEL = re.compile(r"\d[sf]\b")                                          # every level says spot (s) or futures (f)


@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_29oct_the_reads_jarvis_never_consumed(record):
    """29 Oct 10:59 (measured on the record): DECODE's 10:55 close logged §1o MIXED (8 one-sided bars, all ▲, under its 10),
    THE READ said TREND ▲ at 10:55, the futures range (22,712-22,965f) had used 1.20 of the 09:20 straddle's EM 211, and
    the leg's PALAT? kept the buyer out with the move already spent (needs +176, EM left 34)."""
    d = build("2026-10-29", 11 * 60)
    c = d["call"]
    assert "range used" in c["how_much"]["line"] and "σ" in c["how_much"]["line"]
    assert c["how_much"]["line"].startswith("day MIXED · range used 1.20 of EM")
    assert LEVEL.search(c["where"]["t1"]) and LEVEL.search(c["where"]["stop"])
    assert c["where"]["stop"].endswith("f (PALAT line)") and c["where"]["t1"].startswith("CE wall 23,000s (")
    e = c["expression"]
    assert e["pick"] in ("seller", "buyer", None) and "needs +" in e["buyer"] and "EM left" in e["buyer"]
    assert c["buyer"] == e["buyer"] and " vs RV " in e["seller"] and e["buyer"].endswith("EM left 34 → thin")
    assert c["cross"]["read"] is None or isinstance(c["cross"]["read"], str)
    assert c["cross"] == {"read": "THE READ ▲ TREND 10:55", "decode": "DECODE ▲ mila-jula · 2 thak 3 jaari 10:55",
                          "board": None}
    assert len(d["health"]["not_read"]) <= 5 and d["health"]["not_shown"]
    assert "%" not in json.dumps(c, ensure_ascii=False)
    assert [s["src"] for s in d["reads"]["speed"][2:10]] == ["rank"] * 8       # 09:17 on, not "?" for 10 bars


@pytest.mark.skipif(not _has("2026-10-28"), reason="28 Oct record not present")
def test_the_priced_lines_are_causal(record):
    """The buyer's needs / EM left and the seller's IV vs RV at 12:49 read the same from the 12:50 build and from the 13:41
    build cut at 12:49 (calls(), her replay): ctx is keyed by minute, never the frame's end."""
    full, part = build("2026-10-28", 13 * 60 + 41), build("2026-10-28", 12 * 60 + 50)
    c = jarvis.calls(full)[len(part["mins"]) - 1]
    assert (c["buyer"], c["seller"]) == (part["call"]["buyer"], part["call"]["seller"]) and " vs RV " in c["seller"]


T5_KEYS = ("how_much", "where", "expression", "cross", "her_setup", "expiry", "bada", "buyer", "seller")


@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_every_task5_key_is_causal(record):
    """Every Task 5 key of the call at a minute reads the same from a build cut there and from the full day's frame cut
    there (cut_at, her replay's): 29 Oct at 10:59 and 14:50 -- the DECODE / READ logs, the confluence rows (written when
    their window closed), a BADA PRINT at the CE wall (14:35), the ATM read, her levels."""
    full = build("2026-10-29", 15 * 60 + 41)
    for up in (11 * 60, 14 * 60 + 51):
        part = build("2026-10-29", up)
        a, b = part["call"], jarvis.call(jarvis.cut_at(full, len(part["mins"]) - 1))
        for k in T5_KEYS:
            assert json.dumps(a[k], ensure_ascii=False) == json.dumps(b[k], ensure_ascii=False), (up, k)
    assert a["her_setup"] and a["cross"]["decode"] and a["where"]["t1"]


def test_the_logs_are_read_when_they_were_written():
    """A DECODE row from its written `at` (29 Oct's 09:20 close landed 09:21:07: not at the 09:20 minute, yes at 09:21), a
    READ mark at close + 1 (holdshadow._dec_at's rule)."""
    at = jarvis.fold.ms("2026-10-29", "09:21:07") / 1000
    d = {"day": "2026-10-29", "mins": ["09:20", "09:21", "10:55", "10:56"],
         "ctx": {"read": [{"t": "10:55", "word": "TREND", "dir": 1}], "decode": [{"T": "09:20", "at": at}]}}
    assert [len(x) for x in jarvis._logged(d, 0)] == [0, 0] and [len(x) for x in jarvis._logged(d, 1)] == [0, 1]
    assert [len(x) for x in jarvis._logged(d, 2)] == [0, 1] and [len(x) for x in jarvis._logged(d, 3)] == [1, 1]


def test_cpr_and_rv_by_hand():
    """CPR: pivot (H+L+C)/3, bc (H+L)/2, tc 2·pivot − bc, width |tc − bc|, narrow at <= 0.1 of the range [I]. RV: server._rv5's
    formula (close-to-close log returns, sample sd, √252), None under 4 returns."""
    c = jarvis.cpr(23000.0, 22800.0, 22950.0)                           # pivot 22,916.7 · bc 22,900 · tc 22,933.3
    assert c["w"] == pytest.approx(33.33, abs=0.01) and c["kind"] == "wide"   # 33.3 > 0.1 x 200
    assert jarvis.cpr(23000.0, 22800.0, 22900.0)["kind"] == "narrow"      # C at the mid: width 0
    assert jarvis.rv([100, 101, 100, 101, 100, 101]) == pytest.approx(0.1730, abs=1e-4)
    assert jarvis.rv([100, 101, 100, 101]) is None                        # 3 returns: noise, said so


def test_the_speed_warms_up_on_the_rank_reference():
    """rank_build's same-slot median |5-min delta| (data/rank) is the yardstick for the first 10 bars, at √(3/5) for a
    3-min sum [I], tagged src rank; without the reference the "?" stays and says why."""
    n = 30
    d = {"mins": [f"10:{i:02d}" for i in range(n)], "fut": [100.0 + i for i in range(n)], "fo": [99.5 + i for i in range(n)],
         "fhi": [101.0 + i for i in range(n)], "flo": [99.0 + i for i in range(n)], "delta": [10] * n, "fvol": [100] * n,
         "bnf": [200.0] * n, "sx": [300.0] * n, "vwap": [110.0] * n, "sd": [5.0] * n,
         "timeline": [{"fuel": None, "fuel_state": "-"}] * n, "runs": [], "pushes": [], "zone": [], "holes": [],
         "chain_missing": [], "sides": None, "wf_ce": [None] * n, "wf_pe": [None] * n, "bar": 500, "fights": []}
    sp = jarvis.reads(d)["speed"]
    assert sp[2]["word"] == "?" and "no rank reference" in sp[2]["why"]
    d["ctx"] = {"absd": {40: 50.0}}                                       # 10:00-10:14, slot 40: |5-min delta| 50 lots
    sp = jarvis.reads(d)["speed"]
    assert sp[2]["src"] == "rank" and sp[2]["x"] == round(30 / (50 * (3 / 5) ** 0.5), 2) and sp[2]["word"] == "NORMAL"
    assert "src" not in sp[12] and sp[12]["x"] == 1.0                     # 10 bars of its own: its own median


def test_on_expiry_afternoon_writers_covering_is_not_with():
    """0 DTE from 14:00: the Sides and ±7 covering is the expiry unwind, never WITH (labelled); before 14:00, or with DTE 1,
    it counts; an AGAINST is left as it reads."""
    def frame(ce, pe):
        d = _toy()
        d["mins"] = [f"{13 + (40 + i) // 60:02d}:{(40 + i) % 60:02d}" for i in range(40)]     # 13:40-14:19
        d["wf_ce"], d["wf_pe"] = [ce] * 40, [pe] * 40
        d["reads"] = jarvis.reads(d)
        d["legs"] = {"rows": [{"t": m, "lean": -1, "word": "TREND", "leg": {"dir": -1}} for m in d["mins"]],
                     "day": {"flips": [0] * 40, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
        return d
    d = frame(12.0, -14.0)                                               # ±7 DOWN: with the ▼ lean
    d["ctx"] = {"dte": 1}
    assert [p["side"] for p in jarvis.count(d, 39)["pieces"][:2]] == ["with", "with"]
    d["ctx"] = {"dte": 0}
    assert [p["side"] for p in jarvis.count(d, 15)["pieces"][:2]] == ["with", "with"]     # 13:55: before 14:00
    p = jarvis.count(d, 39)["pieces"]                                    # 14:19
    assert [x["side"] for x in p[:2]] == ["?", "?"] and all(x["text"].endswith("· expiry unwind") for x in p[:2])
    d = frame(-14.0, 12.0)                                               # ±7 UP: against the ▼ lean
    d["ctx"] = {"dte": 0}
    p = jarvis.count(d, 39)["pieces"]
    assert p[0]["side"] == "?" and p[1]["side"] == "against" and "expiry unwind" not in p[1]["text"]


def test_her_marked_trade_is_manages_subject():
    """Her open marked trade is MANAGE's subject (entry minute's fut, her side and role); the zone trigger is the labelled
    fallback, and after her exit the subject goes back to it."""
    d = _toy()
    d["zone"] = [{"t": "10:02", "side": "SELL", "px": 23094.0}]
    d["ctx"] = {"marked": [{"id": "NIFTY-23000PE-long-100510", "idx": "NIFTY", "k": 23000.0, "side": "PE", "role": "long",
                            "t0": "10:05:10", "p0": 120.0, "exit_t": "10:30:00"}]}
    r = jarvis.reads(d)
    assert r["trade"][3]["subject"] == "zone trigger"                     # before her mark
    t = r["trade"][20]
    assert t["subject"] == "her trade" and t["opt"] == "PE" and t["role"] == "long" and t["pts"] == 45.0   # 23,085 -> 23,040
    assert r["trade"][35]["subject"] == "zone trigger"                    # flat at 10:30
    assert any(m["subject"] == "her trade" for m in r["manage"]) and all(m["b"] < 30 for m in r["manage"]
                                                                          if m["subject"] == "her trade")


def _expr_toy(iv=14.0, rv=0.10, em=120.0, broke=False):
    """The toy down-leg (TREND ▼, Sides REAL put writers covering) with the Task 5 context: the ATM read, RV, EM, levels."""
    d = _toy()
    g = {"dir": -1, "quality": "TREND", "pts": 117, "sigma_max": 2.1, "toot": None, "fuelled": None, "origin": 23102.0,
         "origin_t": "10:00", "extreme": 22985.0, "extreme_t": "10:39", "retrace": 0.05}
    d["legs"] = {"rows": [{"t": m, "lean": -1, "word": "TREND", "risk": [], "leg": g, "line": "TREND", "alive": [],
                           "notes": [], "missing": []} for m in d["mins"]],
                 "day": {"flips": [0] * 40, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    if broke:                                                            # the lean's own push BROKE its wall at 10:34
        d["pushes"] = [{"t": "10:34", "m": 634, "dir": -1, "ans": "TOOT", "am": "10:36", "k": 22950.0, "side": "PE",
                        "who": "WRITERS", "artifact": False}]
    d["ctx"] = {"opt": {m: {"k": 22950, "ce": 60.0, "pe": 70.0, "iv": iv, "mp": 23000} for m in d["mins"]}, "rv": rv,
                "em": {"em": em, "t": "09:20", "K": 23000, "straddle": 150.0, "N": 5}, "dte": 3, "notes": [],
                "levels": {"PDH": 23060.0, "PDL": 22900.0, "PWH": 23200.0, "PWL": 22800.0},
                "vp": {"day": "2026-10-29", "poc": 22960.0, "vah": 23050.0, "val": 22940.0},
                "marked": [{"id": "T1", "idx": "NIFTY", "k": 23000.0, "side": "PE", "role": "long", "t0": "10:05:00",
                            "p0": 120.0, "exit_t": None}]}
    d["verdict"] = {"BUY": {}, "SELL": {}}
    d["reads"] = jarvis.reads(d)
    d["health"] = jarvis.health(d, None)
    d["reads"]["action"] = jarvis.action_words(d)
    return jarvis.call(d)


def test_the_expression_pick_where_and_how_much_on_a_toy():
    c = _expr_toy()
    assert c["word"] == "TREND ▼"
    e = c["expression"]
    assert e["pick"] == "seller" and "IV 14.0 vs RV 12.0 (cal) → rich" in e["seller"]    # RV 10 x √(365/252) = 12.0
    assert e["seller"].endswith("fold: could not check — the HOLD v2 line is not logged")
    assert "IV 14.0 vs RV 13.2 (cal) → fair" in _expr_toy(rv=0.11)["expression"]["seller"]   # raw 11 x 1.15 = 12.65 would
    assert _expr_toy(rv=0.11)["expression"]["pick"] is None                                # read rich: the day count only
    assert "needs +80 pts today [I ×1.15] · EM left 2 → thin" in e["buyer"]            # PE 70 x 1.15; 120 − |22,983 − 23,101|
    assert e["in_trade"] == {"id": "T1", "side": "PE", "role": "long", "pts": 102.0, "word_at_entry": "HOLD ▼"}
    w = c["where"]
    assert w["stop"] == f"{jarvis._fmt(c['lines']['half'])}f (PALAT line)" and w["pool"] == "PDH 23,060f"
    assert w["t1"] == "pPOC 22,960f" and w["t2"] == "PE wall 22,900s (22,950f)" and w["room"] == "23 to pPOC"
    assert c["how_much"]["line"].startswith("day ? · range used 1.01 of EM") and "CPR could not check" in c["how_much"]["line"]
    # the bars' 23,102 - 22,981 over EM 120
    assert c["expiry"] == {"dte": 3, "mode": None}
    assert _expr_toy(rv=0.13)["expression"]["pick"] is None                              # 14 / 13: fair, no BROKEN
    assert _expr_toy(rv=0.13)["expression"]["pick_why"] == "no edge named"
    assert _expr_toy(rv=0.13, broke=True)["expression"]["pick"] is None                  # BROKEN, but EM left 2 < 80
    assert _expr_toy(rv=0.13, em=250.0, broke=True)["expression"]["pick"] == "buyer"     # EM left 132 >= 80


# ---- Task 6: the incremental frame IS the cold frame --------------------------------------------------------------------

LIVE_STEPS = [10 * 60 + i for i in range(21)] + [13 * 60, 13 * 60 + 1] + [10 * 60 + 10, 10 * 60 + 11, 13 * 60 + 2]
# 10:00, 10:01 ... 10:20, then 13:00, 13:01, then back (a replay, a reconnect): 10:10, 10:11, and on to 13:02
T6_KEYS = ("call", "pushes", "verdict", "fights")


def _cold(day, idx, upto):
    """A cold build at `upto`: jarvis's cache emptied for it, the warm entries put back after (the live day goes on)."""
    warm = dict(jarvis._CACHE)
    jarvis._CACHE.clear()
    try:
        return jarvis.build(day, idx, upto)
    finally:
        jarvis._CACHE.clear()
        jarvis._CACHE.update(warm)


def _same(warm, cold, where):
    """The brief's keys one by one (a readable failure), then the whole frame."""
    for k in ("word", "state", "since", "count"):                    # the word she reads, its since and its count first
        assert warm["call"][k] == cold["call"][k], (where, "call", k)
    assert warm["reads"]["action"][-1] == cold["reads"]["action"][-1], (where, "reads.action[-1]")
    for k in T6_KEYS:
        assert warm[k] == cold[k], (where, k)
    for k in ("action", "writers", "signs"):
        assert warm["reads"][k] == cold["reads"][k], (where, "reads", k)
    assert warm["timeline"][-1] == cold["timeline"][-1], (where, "timeline[-1]")
    assert warm["legs"]["rows"][-1] == cold["legs"]["rows"][-1], (where, "legs.rows[-1]")
    for k in ("how_much", "where", "expression", "cross", "her_setup", "expiry", "bada"):   # Task 5's, inside the call
        assert warm["call"][k] == cold["call"][k], (where, "call", k)
    assert warm == cold, (where, sorted(k for k in warm if warm[k] != cold.get(k)))


@pytest.mark.parametrize("day,idx,steps", [("2026-10-21", "NIFTY", LIVE_STEPS), ("2026-10-29", "NIFTY", LIVE_STEPS),
                                           ("2026-10-30", "NIFTY", LIVE_STEPS),
                                           ("2026-10-29", "SENSEX", [600, 601, 780, 781])])
def test_the_incremental_frame_equals_a_cold_build(record, day, idx, steps):
    """The live day simulated (10:00, then +1 min to 10:20, then 13:00, 13:01): every warm build from the cache equals a
    cold build at the same upto -- the call's word / state / since / count, the last ACTION row, the call, the ACTION /
    writers / signs series, the last timeline row, the pushes, the verdict, the fights, the leg's last row, Task 5's keys,
    and the whole frame."""
    if not _has(day):
        pytest.skip(f"{day} record not present")
    jarvis._CACHE.clear()
    for upto in steps:
        warm = jarvis.build(day, idx, upto)
        assert any(k[:3] == (day, idx, False) for k in jarvis._CACHE)   # the build left its entry for the next minute
        _same(warm, _cold(day, idx, upto), (day, idx, jarvis.hm(upto)))


def _grow(day, cut, src, dst):
    """Append to `dst` the lines of the record file `src` stamped before `cut` (book: epoch ms; chain: "HH:MM:SS") that
    are not there yet -- the live recorder, a minute at a time."""
    have = dst.read_text(encoding="utf-8").count("\n") if dst.exists() else 0
    keep = [ln for ln, k in src if k < cut]
    with open(dst, "a", encoding="utf-8") as f:
        f.writelines(keep[have:])


def _lines(path, key):
    out = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            try:
                out.append((ln, key(json.loads(ln))))
            except ValueError:
                continue
    return out


@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_the_incremental_frame_follows_growing_files(record, tmp_path, monkeypatch):
    """The record as the live recorders write it: the book and the three chains grow minute by minute (each cut 20 s into
    the minute, the server's grace) and every warm build equals a cold one. A chain row landing late for an earlier minute
    and a chain file rewritten shorter are said ('re-read from HH:MM: ...', health.method) and the rest of the frame, the
    call included, still equals cold."""
    import book_log
    import chain_live
    day = "2026-10-29"
    ist = 19800 * 1000
    monkeypatch.setattr(book_log, "DIR", str(tmp_path / "book"))
    monkeypatch.setattr(chain_live, "CHAIN_DIR", pathlib.Path(tmp_path / "chain"))
    (tmp_path / "book").mkdir()
    (tmp_path / "chain").mkdir()
    src = {"book": _lines(os.path.join(DATA, "book", f"book_NIFTY_{day}.jsonl"),
                          lambda r: (int(r["t"]) + ist) // 1000 % 86400 if isinstance(r.get("t"), (int, float)) else -1)}
    for i in ("NIFTY", "BANKNIFTY", "SENSEX"):
        src[i] = _lines(os.path.join(DATA, "chain", f"chain_{i}_{day}.jsonl"), lambda r: r.get("ts") or "")
    dst = {"book": tmp_path / "book" / f"book_NIFTY_{day}.jsonl"}
    dst |= {i: tmp_path / "chain" / f"chain_{i}_{day}.jsonl" for i in ("NIFTY", "BANKNIFTY", "SENSEX")}

    def grow(upto):
        _grow(day, upto * 60 + 20, src["book"], dst["book"])
        for i in ("NIFTY", "BANKNIFTY", "SENSEX"):
            _grow(day, jarvis.hm(upto) + ":20", src[i], dst[i])

    jarvis._CACHE.clear()
    for upto in range(10 * 60, 10 * 60 + 6):
        grow(upto)
        warm = jarvis.build(day, "NIFTY", upto)
        assert not any(x.startswith("re-read from") for x in warm["health"]["method"])
        _same(warm, _cold(day, "NIFTY", upto), ("growing", jarvis.hm(upto)))

    def same_but_the_note(warm, cold, why):
        """T6 review: the re-read is how the frame was made (health.method), never a gap: the call -- its missing, the
        call log's row -- equals the cold replay's."""
        assert any(x.startswith("re-read from " + why) for x in warm["health"]["method"]), warm["health"]["method"]
        assert not any("re-read" in x for x in warm["health"]["notes"] + warm["call"]["missing"])
        assert warm["call"] == cold["call"]
        assert {k: v for k, v in warm.items() if k != "health"} == {k: v for k, v in cold.items() if k != "health"}
        assert dict(warm["health"], method=[x for x in warm["health"]["method"] if not x.startswith("re-read from")]) \
            == cold["health"]

    late = next(ln for ln, k in src["NIFTY"] if k.startswith("10:02:"))  # 10:02's first snapshot written again, late:
    with open(dst["NIFTY"], "a", encoding="utf-8") as f:                 # now the minute's last
        f.write(late)
    warm = jarvis.build(day, "NIFTY", 10 * 60 + 6)
    same_but_the_note(warm, _cold(day, "NIFTY", 10 * 60 + 6), "10:02: the chain minutes changed")
    lines = dst["NIFTY"].read_text(encoding="utf-8").splitlines(keepends=True)
    dst["NIFTY"].write_text("".join(lines[:-3]), encoding="utf-8")       # rewritten shorter: tailread reads it again
    warm = jarvis.build(day, "NIFTY", 10 * 60 + 6)
    same_but_the_note(warm, _cold(day, "NIFTY", 10 * 60 + 6), "09:15: the chain record (it shrank or was rewritten)")
    assert not any(x.startswith("re-read from") for x in jarvis.build(day, "NIFTY", 10 * 60 + 6)["health"]["method"])
    import tailread                                                      # the reader drops and re-parses unchanged files
    with tailread._LOCK:                                                 # (its LRU): every row a new object, not news
        for k in [k for k in tailread._FILES if os.path.basename(k).startswith(("book_NIFTY", "chain_NIFTY"))]:
            tailread._FILES.pop(k)
    warm = jarvis.build(day, "NIFTY", 10 * 60 + 6)
    assert not any(x.startswith("re-read from") for x in warm["health"]["method"])
    _same(warm, _cold(day, "NIFTY", 10 * 60 + 6), ("re-parsed", "10:06"))


# ---- final fixes B (the whole-branch review's I2 / I1 / M1 / PALAT lines; Task 6's review) -----------------------------

def _call_toy(raw="HOLD"):
    """_pause_toy with the leg's lines and a verdict: a frame call() can read."""
    d = _pause_toy(raw, [], 0.1)
    g = {"dir": -1, "quality": "TREND", "pts": 117, "sigma_max": 2.1, "toot": None, "fuelled": None, "origin": 23102.0,
         "origin_t": "10:00", "extreme": 22985.0, "extreme_t": "10:30"}
    for r in d["legs"]["rows"]:
        r.update(leg=dict(g, retrace=r["leg"]["retrace"]), line=r["word"], alive=[], notes=[], missing=[])
    d["verdict"] = {"BUY": {}, "SELL": {}}
    d["health"] = jarvis.health(d, None)
    return d


def test_a_bad_count_piece_is_could_not_check_never_the_build():
    """I1: with action_words failed (the build keeps the frame, reads.action = []), call() re-ran count() unguarded, so one
    bad piece took the whole build down. A Sides slot whose under-water count is not a number now costs the count only."""
    d = _call_toy()
    d["sides"] = [dict(d["sides"][0], uw="two")]                 # a malformed Sides entry: count's trapped piece raises
    with pytest.raises(TypeError):
        jarvis.action_words(d)
    d["reads"]["action"] = []                                    # as _build leaves it when action_words raised
    c = jarvis.call(d)
    assert c["word"] == "HOLD ▼"                                 # the leg's word stands
    assert c["count"]["N"] == 0 and c["count"]["unread"] == len(jarvis.PIECES)
    assert {p["text"] for p in c["count"]["pieces"]} == {"could not check — TypeError"}


def _close_toy():
    """The toy TREND ▼ leg on 15:00-15:39: the count WITH 5 to 15:30, its chain reads turned against it after (as a chain
    read carried past its end would)."""
    d = _toy()
    d["mins"] = [f"15:{i:02d}" for i in range(40)]
    d["upto"] = "15:40"
    d["ladder"] = {m: {} for m in d["mins"][:31]}                # the chain's minutes: 15:00-15:30
    d["sides"] = [dict(d["sides"][0], t="15:05"), {"t": "15:35", "c": "COV", "p": "ADD", "word": "REAL", "fuel_side": "ce", "uw": 2}]
    d["wf_ce"], d["wf_pe"] = [12.0] * 31 + [-14.0] * 9, [-14.0] * 31 + [12.0] * 9
    d["timeline"] = d["timeline"][:31] + [{"fuel": None, "fuel_state": "-", "fronts": [
        {"k": 22900.0, "side": "PE", "state": "BUILDING", "oi": 99.0, "chg": 4.0, "peak": 99.0}]}] * 9
    d["reads"] = jarvis.reads(d)
    rows = [{"t": m, "lean": -1, "word": "TREND", "risk": [], "leg": {"dir": -1, "quality": "TREND", "retrace": 0.05}}
            for m in d["mins"]]
    d["legs"] = {"rows": rows, "day": {"flips": [0] * 40, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    return d


def test_after_the_chains_scheduled_end_the_word_holds_and_its_reads_say_so():
    """I2: the chain stops at 15:30 by schedule (the futures trade to 15:40). After it, a piece read off the chain says
    could not check — chain ends 15:30 (excluded, never carried), no 3-min close changes the word, and only the at-once
    events (PALAT, the wall behind) still do. Health says it once, as method -- never a gap."""
    d = _close_toy()
    a = jarvis.action_words(d)
    assert a[30]["word"] == "TREND" and a[30]["count"]["with"] == 5
    assert all(x["word"] == "TREND" for x in a[31:]), [x["word"] for x in a[31:]]
    assert "chain ends 15:30: only PALAT / the wall behind change it" in a[35]["why"] and "chain ends" not in a[30]["why"]
    c = {p["k"]: p for p in a[35]["count"]["pieces"]}
    for k in jarvis.CHAIN_PIECES + ("answer",):
        assert c[k] == {"k": k, "side": "?", "text": "could not check — chain ends 15:30", "state": "blind"}, k
    assert a[35]["count"]["N"] == 0
    assert {p["k"]: p for p in a[30]["count"]["pieces"]}["sides"]["side"] == "with"     # 15:30 has its snapshot: read
    d["legs"]["rows"][36] = dict(d["legs"]["rows"][36], word="PALAT", lean=1)        # the lean flips at 15:36: at once
    for r in d["legs"]["rows"][37:]:
        r["lean"] = 1
    a = jarvis.action_words(d)
    assert a[35]["word"] == "TREND" and a[36]["word"] == "PALAT" and a[39]["word"] == "PALAT"
    h = d["health"] = jarvis.health(d, None)
    assert "chain ends 15:30 (scheduled)" in h["method"] and not any("15:3" in x for x in h["notes"])
    assert "chain ends 15:30 (scheduled)" not in jarvis.health(jarvis.cut_at(d, 29), None)["method"]   # 15:29: not yet


@pytest.mark.skipif(not (_has("2026-10-29") and _has("2026-10-30")), reason="29 / 30 Oct records not present")
def test_the_1530_chain_stop_is_never_a_hole_on_the_record(record):
    """I2, measured at dd9b09c: 29 Oct HOLD ▲ -> WATCH ▲ at 15:35 (the count turned on the chain's absence), 30 Oct
    ROTATION ▲ -> NO TRADE 'can't see 15:30-15:40' -- each a word line to her phone every day. Now the word after 15:30 is
    the 15:30 word (neither day has a PALAT or a wall behind after it), nothing from 15:30 reads can't see, and the card's
    gaps never name the close."""
    for day, w in (("2026-10-29", "HOLD ▲"), ("2026-10-30", "ROTATION ▲")):
        d = build(day, 15 * 60 + 45)
        c, mins = d["call"], d["mins"]
        assert mins[-1] > "15:35" and c["action"]["said"] == w, (day, c["action"])
        j = max(i for i, m in enumerate(mins) if m <= "15:30")
        assert {jarvis.said(x["word"], x["lean"]) for x in d["reads"]["action"][j:]} == {w}, day
        assert "chain ends 15:30 (scheduled)" in d["health"]["method"]
        assert not any("chain missing" in x and "15:3" in x for x in d["health"]["notes"] + c["missing"]), day
        assert not any(x["why"] == "can't see" and x["to"] >= "15:30" for x in d["reads"]["notrade"]), day
        assert {p["text"] for p in c["count"]["pieces"] if p["k"] in jarvis.CHAIN_PIECES} == \
            {"could not check — chain ends 15:30"}


def test_palat_says_the_old_leg_ended_and_the_new_one_both_ways():
    """The PALAT buyer / seller lines said 'no lean: buy only at her bands' while the card carried lean ±1 and the new
    leg. Now: which leg ended, what is not new yet, both ways; the wrong-line names the old leg's extreme (f)."""
    d = _call_toy()
    rows = d["legs"]["rows"]
    rows[36] = dict(rows[36], word="PALAT", lean=1)              # the ▼ leg (extreme 22,985f) gave back half: lean ▲
    for r in rows[37:]:
        r.update(lean=1, word="ROTATION", leg=dict(r["leg"], dir=1, origin=22985.0, extreme=23040.0, quality="ROTATION"))
    d["health"] = jarvis.health(d, None)
    d["reads"]["action"] = jarvis.action_words(d)
    for i in (36, 39):                                           # the flip minute (its row holds the old leg) and after
        c = jarvis.call(jarvis.cut_at(d, i))
        assert c["word"] == "PALAT ▲", (i, c["word"])
        assert c["buyer"].startswith("PALAT: the ▼ leg ended · no new CE until the ▲ leg holds 2 closes"), c["buyer"]
        assert c["seller"].startswith("PALAT: the ▼ leg ended · no new PE sale until the ▲ leg holds 2 closes"), c["seller"]
        assert c["wrong_line"] == "back to ▼ on a new low past 22,985f"
        assert "no lean" not in c["buyer"] + c["seller"]


# ---- JARVIS-FIX-2026-11-04 (A229-A232) ----------------------------------------------------------------------------------

def test_a_question_mark_is_flat_or_blind_never_one():
    """A230 (rule 6, A223): a "?" piece is flat (checked, takes no side) or blind (could not check), said apart."""
    d = _toy()
    d["reads"] = jarvis.reads(d)
    d["legs"] = {"rows": [{"t": m, "lean": -1, "word": "TREND", "leg": {"dir": -1}} for m in d["mins"]],
                 "day": {"flips": [0] * 40, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    c, early = jarvis.count(d, 39), jarvis.count(d, 10)
    assert c["pieces"][5]["state"] == "flat" and early["pieces"][5]["state"] == "blind"    # no 30-min story / needs 30 min
    assert c["pieces"][0]["state"] == "with" and c["flat"] + c["blind"] == c["unread"]
    assert {p["state"] for p in c["pieces"]} <= {"with", "against", "flat", "blind"}


def _box_toy(ce_state="BUILDING", os_type=None):
    """A range: fut 23,100f (spot 23,050s, basis 50) between the writers' 22,950s PE and 23,150s CE walls; the leg's lean
    flips inside the box at 10:12, 10:20 and 10:28; from 10:32 a ▲ leg runs to 23,300f, past the CE wall."""
    d = _toy()
    n = len(d["mins"])
    d.update(fut=[23100.0] * n, fo=[23100.0] * n, fhi=[23102.0] * n, flo=[23098.0] * n, spot=[23050.0] * n,
             day="2026-11-04", sides=[], wf_ce=[1.0] * n, wf_pe=[1.0] * n)
    d["timeline"] = [{"fuel": None, "fuel_state": "-", "fronts": [
        {"k": 23150.0, "side": "CE", "state": ce_state, "oi": 120.0}, {"k": 22950.0, "side": "PE", "state": "BUILDING", "oi": 110.0}]}] * n
    if os_type:
        d["ctx"] = {"decode": [{"T": "09:50", "at": None, "call": None, "lines": [], "os": {"type": os_type}}]}
    rows = []
    for i, m in enumerate(d["mins"]):
        lean = -1 if i < 12 or 20 <= i < 28 else 1
        if i >= 32:
            rows.append({"t": m, "lean": 1, "word": "TREND", "leg": {"dir": 1, "quality": "TREND", "extreme": 23300.0}})
        elif i in (12, 20, 28):                       # the flip row holds the old leg, its extreme inside the box
            rows.append({"t": m, "lean": lean, "word": "PALAT", "leg": {"dir": -lean, "quality": "PALAT",
                                                                        "extreme": 23010.0 if lean > 0 else 23180.0}})
        else:
            rows.append({"t": m, "lean": lean, "word": "ROTATION", "leg": {"dir": lean, "quality": "ROTATION",
                                                                           "extreme": 23180.0 if lean > 0 else 23010.0}})
    d["legs"] = {"rows": rows, "day": {"flips": [0] * n, "fut_oi": [None] * n}, "pauses": [], "missing": []}
    d["reads"] = jarvis.reads(d)
    return d


def test_the_range_guard_holds_range_inside_the_writers_box():
    """A229: a lean flip inside the writers' box (both walls there, neither UNWINDING, the leg turned inside them, §1o not
    TREND) is RANGE at once, no arrow, and the next flips inside it change nothing; a leg past a wall leaves RANGE at two
    closes. Before: PALAT at once on every flip."""
    a = jarvis.action_words(_box_toy())
    said = [jarvis.said(x["word"], x["lean"]) for x in a]
    assert said[12] == "RANGE" and a[12]["since"] == "10:12" and "writers' box 22,950s PE" in a[12]["why"]
    assert all(s == "RANGE" for s in said[12:34]) and a[33]["since"] == "10:12"   # 10:20 / 10:28 flips: no change
    assert said[35] != "RANGE" and said[35].endswith("▲")                           # closes 10:32 and 10:35, past the wall
    assert sum(x != y for x, y in zip(said, said[1:])) <= 3
    for kw in ({"ce_state": "UNWINDING"}, {"os_type": "TREND ▲"}):                # a wall covering, or §1o TREND: no box
        a = jarvis.action_words(_box_toy(**kw))
        assert [jarvis.said(x["word"], x["lean"]) for x in a][12] == "PALAT ▲", kw


def test_the_leg_line_says_how_much_of_em_it_used():
    """A232 (display only, the word unchanged): the leg line carries its points over trademap.em's EM once EM is known."""
    d = _call_toy()
    d["reads"]["action"] = jarvis.action_words(d)
    word = jarvis.call(d)["word"]
    d["ctx"] = {"em": {"t": "09:30", "em": 100.0, "K": 23050, "straddle": 150.0, "N": 2}}
    c = jarvis.call(d)
    assert "leg ▼ TREND 117 pts · 1.17 of EM · 2.1σ" in c["leg"] and c["word"] == word
    d["ctx"]["em"]["t"] = "10:45"                                # EM read after this minute: not known yet
    assert "of EM" not in jarvis.call(d)["leg"]


def test_niftys_flow_on_sensex_is_method_not_a_gap():
    """A231 (§1q): "flow from NIFTY" says how SENSEX's flow is made; it is never in notes (the call's missing)."""
    d = _toy()
    d["flow"], d["flow_src"] = list(d["delta"]), ["N"] * len(d["mins"])
    h = jarvis.health(d, None)
    assert "flow from NIFTY (§1q)" in h["method"] and "flow from NIFTY (§1q)" not in h["notes"]


def test_an_index_whose_answers_are_not_said_never_counts_them():
    """A231 (handshake.SPEAK): SENSEX's OI cannot cross the 3L answer bar, so every answer reads HELD (3 Nov: 19 of 19)
    and the count read AGAINST on 116 of 332 minutes; it is not counted (flat, never blind: the data is there), with the
    reason. NIFTY's answer is counted as before."""
    d = _pause_toy("HOLD", [], 0.1)
    d["pushes"] = [{"t": "10:30", "m": 630, "am": "10:33", "k": 22950.0, "side": "PE", "who": "WRITERS", "artifact": False,
                    "dir": -1, "ans": "NAHI"}]
    d["idx"] = "NIFTY"
    assert jarvis.count(d, 36)["pieces"][3]["side"] == "against"                 # the lean's own push HELD
    d["idx"] = "SENSEX"
    p = jarvis.count(d, 36)["pieces"][3]
    assert p["state"] == "flat" and p["text"].startswith("not counted") and "handshake.SPEAK" in p["text"]


@pytest.mark.skipif(not _has("2026-10-30"), reason="30 Oct record not present")
def test_30oct_1345_palat_lines_match_the_card(record):
    """The controller's card read: 30 Oct 13:45, word PALAT ▼, lean −1."""
    c = build("2026-10-30", 13 * 60 + 46)["call"]
    assert c["action"]["said"] == "PALAT ▼" and c["lean"] == -1, (c["action"], c["lean"])
    assert c["buyer"].startswith("PALAT: the ▲ leg ended · no new PE until the ▼ leg holds 2 closes"), c["buyer"]
    assert c["seller"].startswith("PALAT: the ▲ leg ended · no new CE sale until the ▼ leg holds 2 closes"), c["seller"]
    assert re.fullmatch(r"back to ▲ on a new high past \d{2},\d{3}f", c["wrong_line"]), c["wrong_line"]


def test_how_much_never_reads_a_missing_sigma_as_zero():
    """M1: with no 1-min futures volume yet the build's σ is 0.0, and HOW MUCH read 'σ 0' at 09:15. It is could not
    check; the range-used row names its source (trademap.em at HH:MM); before 09:20 the EM is not yet, never missing."""
    d = _toy()
    d["ctx"] = {"em": {"t": "09:20", "em": 120.0, "K": 23050, "straddle": 150.0, "N": 2}}
    d["sd"] = [0.0] * len(d["mins"])
    h = jarvis.how_much(d, 5, lambda k: f"{jarvis._fmt(k)}s")
    assert "σ could not check — no σ yet (needs 1-min futures volume)" in h["line"] and "σ 0" not in h["line"]
    assert "σ could not check — no σ yet (needs 1-min futures volume)" in h["rows"]
    ru = next(x for x in h["rows"] if x.startswith("range used"))
    assert "trademap.em at 09:20" in ru and "day range" in ru
    d["sd"] = [20.0] * len(d["mins"])
    assert " · σ 20 · " in jarvis.how_much(d, 5, lambda k: f"{jarvis._fmt(k)}s")["line"]
    d["mins"] = ["09:15"] + d["mins"][1:]
    d["ctx"] = {"em": None, "em_why": "no chain row 09:20–09:30"}
    assert "range used could not check — before the 09:20 straddle" in jarvis.how_much(d, 0, str)["line"]


def test_how_much_vix_says_its_three_sentences_and_never_reads_a_later_row():
    """T2: VIX from vix_log's rows up to the frame's minute -- the change since the open, a late start's own first row, or
    could not check with the reason (never a 0)."""
    d = _toy()                                                   # minutes 10:00 .. 10:39
    d["ctx"] = {"vix": [["09:15", 12.8, "backfill"], ["10:05", 13.4, None], ["10:30", 14.9, None]]}
    h = jarvis.how_much(d, 20, str)                              # 10:20: the 10:30 row is not known yet
    assert " · VIX 13.4 · +0.6 since open · " in h["line"]
    assert any(r.startswith("VIX 13.4 · +0.6 since open: 13.40 at 10:05, +0.6 on 12.80 at 09:15 (backfilled)")
               for r in h["rows"])
    d["ctx"] = {"vix": [["10:07", 13.3, None], ["10:20", 13.4, None]]}
    assert " · VIX 13.4 · since 10:07 (started late) · " in jarvis.how_much(d, 25, str)["line"]
    d["ctx"] = {"vix": [["10:07", 13.3, None]]}
    h = jarvis.how_much(d, 5, str)                               # 10:05, before the first row
    assert " · VIX could not check — no VIX row before 10:06 · " in h["line"] and "VIX 0" not in h["line"]
    d["ctx"] = {"vix": [], "vix_why": "no row in vix_2026-10-30.jsonl"}
    assert "VIX: could not check — no VIX row before 10:06 (no row in vix_2026-10-30.jsonl)" in \
        jarvis.how_much(d, 5, str)["rows"]


def test_the_build_cuts_the_vix_rows_at_upto():
    """Causality: jarvis.build(day, idx, upto) reads minutes < upto only -- a row written for a later minute is not read."""
    import vix_log
    os.makedirs(vix_log.DIR)
    with open(vix_log.path_for("2026-11-02"), "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in ({"ts": "09:15", "vix": 12.8}, {"ts": "10:00", "vix": 13.4},
                                                       {"ts": "10:01", "vix": 13.6})))
    assert jarvis._vix_rows("2026-11-02", 10 * 60 + 1) == ([["09:15", 12.8, None], ["10:00", 13.4, None]], None)
    assert jarvis._vix_rows("2026-10-30", 600) == (
        [], "no row in vix_2026-10-30.jsonl (India VIX is recorded by the server's 1-min read)")


def test_rv_on_ivs_calendar_counts_today():
    """T6 review: today's session was left out of both day counts (RV read low, the grade tilted to rich)."""
    f, tr = jarvis._rv_cal("2026-10-30", 4)                     # Fri -> Tue: today + Mon + Tue trading, 5 calendar days
    assert tr == 3 and abs(f - jarvis.RV_CAL * (3 / 5) ** 0.5) < 1e-12
    assert jarvis._rv_cal("2026-10-27", 0) == (jarvis.RV_CAL, None)


def test_a_live_build_drops_another_days_cache_entries(monkeypatch):
    """T6 review: a server left on overnight kept yesterday's live entries (and every chain snapshot in them)."""
    monkeypatch.setattr(jarvis, "_today", lambda: "2026-11-02")
    jarvis._CACHE.clear()
    old = ("2026-10-30", "NIFTY", False, "x", "y")
    same = ("2026-11-02", "SENSEX", False, "x", "y")
    jarvis._CACHE.update({old: {}, same: {}})
    jarvis.build("2026-10-29", "NIFTY", 600)                     # a replay keeps them all
    assert old in jarvis._CACHE and same in jarvis._CACHE
    jarvis.build("2026-11-02", "NIFTY", 600)                     # a live build: today's only
    assert old not in jarvis._CACHE and same in jarvis._CACHE
    assert all(k[0] == "2026-11-02" for k in jarvis._CACHE)
    jarvis._CACHE.clear()


@pytest.mark.skipif(not _has("2026-09-29"), reason="29 Sep record not present")
def test_no_buyer_pick_while_the_word_says_no_new_one(record):
    """Final re-review (1 Nov): on 29 Sep 11:12 the pick said `buyer` (a fresh BROKEN that fit EM) while the ACTION word was
    PALAT and the buyer line said no new CE until the leg holds 2 closes. A pick is named only while the word holds."""
    d = jarvis.build("2026-09-29", "NIFTY", upto=jarvis._m("11:12") + 1, fill=True)
    c = d["call"]
    assert c["action"]["said"].startswith(("PALAT", "RANGE")), c["action"]["said"]   # A229: the 11:10 flip sat inside the writers' box
    assert c["expression"]["pick"] is None and c["expression"]["pick_why"] == "no edge named"      # 22,600-22,700s: RANGE
