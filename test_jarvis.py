"""test_jarvis.py -- J2, the Jarvis brain (plan docs/superpowers/plans/2026-10-29-j2-jarvis-brain.md).

The record tests read the real day files READ-ONLY (conftest points every DIR at tmp; the `record` fixture points the
readers back at data/, and jarvis.build never writes) and are skipped when the day is absent. Their numbers are measured
(A155 / A157 / DAY-2026-10-29 §5); where the record and the plan differ, the test says so in its comment.
"""
import json
import os
import pathlib

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
    assert cover["khatam"] == "12:58" and cover["lots"] == -1726
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
    assert not s[0]["driving"] and s[0]["drive"] == []
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
    assert c["word"] != "UP" and "RISK" in " ".join(c["why"]).upper()               # 10:38 TOP RISK


@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_the_call_has_both_expressions_a_wrong_line_and_no_rate(record):
    d = build("2026-10-29", 11 * 60)
    c = d["call"]
    assert c["word"].rstrip(" ▲▼") in WORDS and c["v1"]["word"] in ("UP", "DOWN", "RANGE", "NO TRADE")
    assert c["buyer"] and c["seller"] and c["wrong_line"] and c["up"] and c["dn"]
    blob = json.dumps({k: d[k] for k in ("call", "health", "reads")}, ensure_ascii=False)
    assert not any(w in blob.lower() for w in ("%", "hit rate", "win rate", "odds")) and "order" not in c["buyer"] + c["seller"]
    assert d["health"]["not_read"]                                                   # GAPS §5: every "—" row named


@pytest.mark.skipif(not _has("2026-10-28"), reason="28 Oct record not present")
def test_the_reads_are_causal_too(record):
    full = build("2026-10-28", 13 * 60 + 41)["reads"]
    part = build("2026-10-28", 12 * 60 + 50)["reads"]
    n = len(part["speed"])
    for k in ("speed", "sync", "writers", "trade"):
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
    assert out["call"]["word"].rstrip(" ▲▼") in WORDS and out["health"]["dext"]["minutes"] == 0
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


@pytest.mark.skipif(not _has("2026-10-30"), reason="30 Oct record not present")
def test_a_blind_frame_says_cant_see_and_carries_nothing(record):
    """30 Oct 12:41-13:30 the book was empty (her internet): at 13:00 the newest minute is 12:41. The call said "NO TRADE
    -- writers and flow do not agree" off 12:41's data; it now says CAN'T SEE and names the blind span. After the close
    (15:40) a frame that ends at 15:39 is not blind."""
    c = build("2026-10-30", 13 * 60)["call"]
    assert c["word"] == "CAN'T SEE" and "blind since 12:41" in " ".join(c["why"])
    assert c["missing"][0].startswith("BLIND since 12:41") and c["buyer"].startswith("wait")
    assert build("2026-10-30", 15 * 60 + 41)["call"]["word"] != "CAN'T SEE"
