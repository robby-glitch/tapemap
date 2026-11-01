"""legs.py on synthetic frames: leg qualification (the 10:00 split), PALAT at half the leg floored at 1U, the PALAT?
confirmation / latch / minimum display, k1 loading and emptying, the ATM premium vs delta, a missing input named, the
lagging note, the after-the-fact outcome; plus the record (read-only, skipped without data/): 30 Oct 11:00-12:10 and the
whole of 29 Oct have no lean change."""
import os
import pathlib

import pytest

import legs
from legs import hm, m2i

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def frame(path, start="10:00", sd=20.0, vwap=None, **kw):
    """A frame from a list of 1-min closes: bars +/-1 pt, VWAP flat at the first close (so sigma = pts / sd)."""
    N = len(path)
    m0 = m2i(start)
    d = {"mins": [hm(m0 + i) for i in range(N)], "fut": list(path), "fhi": [x + 1 for x in path], "flo": [x - 1 for x in path],
         "fo": [path[0]] + path[:-1], "spot": list(path), "vwap": [vwap if vwap is not None else path[0]] * N, "sd": [sd] * N,
         "flow": [0] * N, "oi": [1000] * N, "ladder": {}, "step": 50, "pushes": [], "wf_ce": [None] * N, "wf_pe": [None] * N,
         "sides": []}
    d.update(kw)
    return d


def ramp(a, b, n):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def low_z(d):
    """VWAP trails price 15 pts behind: the leg never reaches 1.5 sigma (0.8 at sd 20). Before Jarvis v3 these frames
    used sd 100, which now also raises the first leg's floor to 2U = 200 pts."""
    d["vwap"] = [x - 15 for x in d["fut"]]
    return d


def leans(rows):
    """Lean changes between consecutive rows that both have a leg."""
    return sum(1 for a, b in zip(rows, rows[1:]) if a["lean"] and b["lean"] and a["lean"] != b["lean"])


# ---- leg qualification --------------------------------------------------------------------------------------------------

def test_trend_after_10_needs_80_pts_and_sigma():
    rows = legs.read(frame(ramp(23000, 23090, 31)))["rows"]           # +90 pts, 4.5 sigma, after 10:00
    assert rows[-1]["leg"]["quality"] == "TREND" and rows[-1]["word"] in ("TREND", "HOLD") and rows[-1]["lean"] == 1
    rows = legs.read(low_z(frame(ramp(23000, 23090, 31))))["rows"]   # +90 pts but 0.8 sigma, no TOOT, not fuelled
    assert rows[-1]["leg"]["quality"] == "ROTATION" and rows[-1]["word"] == "ROTATION" and rows[-1]["lean"] == 1
    rows = legs.read(frame(ramp(23000, 23070, 31)))["rows"]           # +70 pts: under TREND_PTS
    assert rows[-1]["leg"]["quality"] == "ROTATION"


def test_trend_after_10_by_toot_alone():
    d = low_z(frame(ramp(23000, 23085, 31)))
    d["pushes"] = [{"t": "10:10", "dir": 1, "ans": "TOOT", "am": "10:12", "artifact": False}]
    rows = legs.read(d)["rows"]
    assert rows[-1]["leg"]["quality"] == "TREND" and rows[-1]["leg"]["toot"] == "10:10"


def test_opening_needs_100_pts_and_a_toot():
    d = frame(ramp(23000, 23110, 31), start="09:15")                   # +110 pts, 5.5 sigma, no TOOT, before 10:00
    rows = legs.read(d)["rows"]
    assert rows[-1]["leg"]["quality"] == "OPENING" and rows[-1]["word"] == "OPENING" and "no lean until 100 pts + TOOT" in rows[-1]["line"]
    d["pushes"] = [{"t": "09:25", "dir": 1, "ans": "TOOT", "am": "09:27", "artifact": False}]
    assert legs.read(d)["rows"][-1]["leg"]["quality"] == "TREND"
    d = frame(ramp(23000, 23090, 31), start="09:15", pushes=[{"t": "09:25", "dir": 1, "ans": "TOOT", "am": "09:27", "artifact": False}])
    assert legs.read(d)["rows"][-1]["leg"]["quality"] == "OPENING"    # 90 pts + TOOT: still the open


def test_fuelled_counts_only_after_10():
    """Jarvis's own UP at a minute of the leg qualifies it after 10:00 (reads + timeline in the frame), never before."""
    def with_reads(d):
        N = len(d["mins"])
        d["reads"] = {"writers": [{"state": "UP", "dir": 1, "push": None}] * N,
                      "speed": [{"word": "FAST", "dir": 1}] * N, "sync": [None] * N}
        d["timeline"] = [{"fuel": None, "fuel_state": None}] * N
        return d
    rows = legs.read(with_reads(low_z(frame(ramp(23000, 23085, 31)))))["rows"]
    assert rows[-1]["leg"]["fuelled"] and rows[-1]["leg"]["quality"] == "TREND"
    rows = legs.read(with_reads(low_z(frame(ramp(23000, 23085, 31), start="09:15"))))["rows"]
    assert rows[-1]["leg"]["quality"] == "OPENING"


# ---- PALAT: half the leg, floored at 1U; the lean flips there and only there ---------------------------------------------

def test_palat_at_half_the_leg():
    up = ramp(23000, 23100, 21)                                        # bars +/-1: the leg is 22,999 -> 23,101 = 102, half = 51; U = 23.1
    rows = legs.read(frame(up + [23060, 23051]))["rows"]
    assert rows[-1]["word"] != "PALAT" and rows[-1]["lean"] == 1       # 50 back: not yet
    out = legs.read(frame(up + [23060, 23051, 23050]))
    rows = out["rows"]
    assert rows[-1]["word"] == "PALAT" and rows[-1]["lean"] == -1 and "gave back 51 (0.50)" in rows[-1]["line"]
    assert out["day"]["flips"][-1] == 1 and out["day"]["flips"][-2] == 0
    assert leans(rows) == 1


def test_palat_floor_is_1U_on_a_small_leg():
    """Only the day's first leg needs 2U (LEG_MIN_U); a leg born at a PALAT may be 40 pts, and its own PALAT waits for 1U."""
    down = ramp(23086, 23000, 9)                                       # the first leg 23,087 -> 22,999 = 88 pts, half 44
    up = down + [23020, 23043]                                         # 44 back: PALAT, the new leg 22,999 -> 23,044 = 45 pts
    rows = legs.read(frame(up))["rows"]
    assert rows[-1]["word"] == "PALAT" and rows[-1]["lean"] == 1
    assert legs.read(frame(up + [23021]))["rows"][-1]["word"] != "PALAT"           # 23 back: half 22.5 < U 23.02
    assert legs.read(frame(up + [23021, 23019]))["rows"][-1]["word"] == "PALAT"


# ---- PALAT?: confirmed at a 3-min close or after 6 min, latched, shown >= 6 min, never carried stale -------------------

def test_palat_question_confirmation_latch_and_min_show():
    up = ramp(23000, 23100, 20)                                        # 10:00-10:19, TREND (100 pts, 5 sigma)
    path = up + [23090, 23064, 23064, 23064, 23095, 23095, 23095, 23095, 23095, 23095, 23095]
    rows = legs.read(frame(path))["rows"]
    w = {r["t"]: r["word"] for r in rows}
    assert w["10:20"] == "HOLD"                                        # the pause begins (0.25U back)
    assert w["10:21"] == "HOLD" and w["10:22"] == "HOLD"               # 0.36 back, but 10:21 / 10:22 are not 3-min closes
    assert w["10:23"] == "PALAT?"                                      # confirmed at the close (10:23 = 09:15 + 3k + 2)
    assert w["10:24"] == "PALAT?" and w["10:28"] == "PALAT?"           # price back to 0.05: latched for MIN_SHOW
    assert w["10:29"] == "HOLD"                                        # not carried past 6 min once the condition is gone
    assert "retrace 0.36 of the leg" in {r["t"]: r["line"] for r in rows}["10:23"]


def test_palat_question_by_three_risk_items_needs_a_close_too():
    """Three risk items (band emptying, delta against, inside 1 sigma) at a non-close minute wait for the close."""
    up = ramp(23000, 23100, 20)
    path = up + [23090, 23080, 23080, 23080]
    N = len(path)
    d = frame(path, vwap=23070.0)                                      # z at 23080 = 0.5: inside 1 sigma after a 1.5 sigma leg
    d["flow"] = [0] * 20 + [-100, -100, -100, -100]                    # 3-min delta against -300 from 10:22
    d["ladder"] = {hm(600 + i): {"ce": {"23100": 100.0 - 0.5 * i, "23150": 50.0, "23200": 50.0}, "pe": {}} for i in range(N)}
    w = {r["t"]: r for r in legs.read(d)["rows"]}
    assert len(w["10:22"]["risk"]) >= 3 and w["10:22"]["word"] == "WATCH"
    assert w["10:23"]["word"] == "PALAT?"


# ---- the items --------------------------------------------------------------------------------------------------------

def pause_frame(ladder_slope=0.0):
    up = ramp(23000, 23100, 20)
    path = up + [23090, 23088, 23090, 23089]                           # a shallow pause from 10:20
    N = len(path)
    d = frame(path)
    d["ladder"] = {hm(600 + i): {"ce": {"23100": 100.0 + ladder_slope * i, "23150": 60.0, "23200": 40.0}, "pe": {}} for i in range(N)}
    return d


def test_k1_loading_and_emptying():
    r = legs.read(pause_frame(+0.5))["rows"][-1]                       # 23100 CE +4.5L over 9 min
    assert any(x["k"] == "k1_loading" and "23,100s CE loading +4.5L" in x["text"] for x in r["alive"])
    assert r["word"] == "HOLD" and "clean" in r["line"] and r["leg"]["k1"] == 23100
    r = legs.read(pause_frame(-0.5))["rows"][-1]                       # 23100 CE -4.5L: the band ahead emptying
    assert any(x["k"] == "band_emptying" for x in r["risk"]) and "clean" not in r["line"]


def test_premium_holding_and_bleeding():
    d = pause_frame()
    chain = {t: {"spot": s, "ce": {"23100": {"ltp": 100.0, "delta": 0.5}}, "pe": {}} for t, s in zip(d["mins"], d["spot"])}
    chain["10:23"]["ce"]["23100"]["ltp"] = 100.0 + 0.5 * (23089 - 23100) + 1.2   # from the extreme (10:19, spot 23,100): delta explains -5.5; bid +1.2 beyond
    r = legs.read(d, chain=chain)["rows"][-1]
    assert any(x["k"] == "premium_holding" and "+1.2" in x["text"] and "since 10:19" in x["text"] for x in r["alive"])
    chain["10:23"]["ce"]["23100"]["ltp"] = 100.0 + 0.5 * (23089 - 23100) - 1.2
    r = legs.read(d, chain=chain)["rows"][-1]
    assert any(x["k"] == "premium_bleeding" and "−1.2" in x["text"] for x in r["risk"])


def test_her_mark_against_known_at_bar_close_plus_one():
    d = pause_frame()
    bar = (m2i("10:15") * 60 - 19800) * 1000                           # the 10:15-10:19 bar, IST -> epoch ms
    marks = [{"id": "absorption@x", "t": bar, "kind": "absorption", "name": "▼ BECHNE WALE NE ROKA", "winner": -1, "p": 23100.0, "prov": False}]
    w = {r["t"]: r for r in legs.read(d, marks=marks)["rows"]}
    assert not any(x["k"] == "mark_against" for x in w["10:20"]["risk"])      # known at 10:21 (bar close 10:20 + 1)
    assert any(x["k"] == "mark_against" and "bar 10:15" in x["text"] for x in w["10:21"]["risk"])


def test_missing_inputs_are_named_never_zero():
    r = legs.read(pause_frame())["rows"][-1]
    assert any("ATM premium" in s and "could not check" in s for s in r["missing"])
    assert any("footprint marks" in s for s in r["missing"]) and any("fuelled" in s for s in r["missing"])
    d = pause_frame()
    d["ladder"] = {}
    r = legs.read(d, chain={}, marks=[])["rows"][-1]
    assert any("k1 OI" in s for s in r["missing"]) and not any("footprint" in s for s in r["missing"])
    assert any("ATM premium" in s and "not in the chain" in s for s in r["missing"])


def test_lagging_writers_and_sides_are_notes_not_items():
    d = pause_frame()
    N = len(d["mins"])
    d["wf_ce"], d["wf_pe"] = [-8.0] * N, [6.0] * N                     # +14L with the leg
    d["sides"] = [{"t": "10:15", "word": "REAL", "fuel_side": "ce", "c": "COV", "p": "ADD"}]
    r = legs.read(d)["rows"][-1]
    assert any(x["k"] == "writers7" and "(lagging)" in x["text"] and "with" in x["text"] for x in r["notes"])
    assert any(x["k"] == "sides" and "(lagging)" in x["text"] for x in r["notes"])
    assert not any(x["k"] in ("writers7", "sides") for x in r["alive"] + r["risk"])


def test_the_lagging_writers_bar_is_jarvis_own_key(monkeypatch):
    """T6 review: legs kept its own copy of jarvis.WF_L, so a change to jarvis.WF_L never reached the (lagging) note."""
    import jarvis
    d = pause_frame()
    N = len(d["mins"])
    d["wf_ce"], d["wf_pe"] = [-8.0] * N, [6.0] * N                     # 14L with the leg
    assert not hasattr(legs, "WF_L") and not hasattr(legs, "WF_STOP")  # no copy left
    monkeypatch.setattr(jarvis, "WF_L", 15.0)
    assert not any(x["k"] == "writers7" for x in legs.read(d)["rows"][-1]["notes"])
    monkeypatch.setattr(jarvis, "WF_L", 14.0)
    assert any(x["k"] == "writers7" for x in legs.read(d)["rows"][-1]["notes"])


def test_pause_outcome_is_read_after_the_fact():
    up = ramp(23000, 23100, 20)
    out = legs.read(frame(up + [23090, 23088, 23095, 23108]))          # a new extreme 0.25U past the pause's
    ev = out["pauses"][0]
    assert ev["t"] == "10:20" and ev["word"] == "HOLD" and ev["after"]["outcome"] == "CONT" and ev["after"]["t"] == "10:23"
    out = legs.read(frame(up + [23090, 23088, 23070, 23050]))          # half given back: PALAT
    assert out["pauses"][0]["after"]["outcome"] == "REV"
    out = legs.read(frame(up + [23090, 23088]))
    assert out["pauses"][0]["after"]["outcome"] is None and "window open" in out["pauses"][0]["after"]["why"]


def test_day_fut_oi_quadrant():
    path = ramp(23000, 23040, 40)
    d = frame(path, oi=[1000 - 20 * i for i in range(40)])             # -600 lots over 30 min on +30 pts
    q = legs.read(d)["day"]["fut_oi"]
    assert q[29] is None and q[-1]["word"] == "short covering" and q[-1]["lots"] == -600


# ---- the record, read-only ------------------------------------------------------------------------------------------------

def _has(day):
    return any(os.path.exists(os.path.join(DATA, "book", f"book_NIFTY_{day}.jsonl{z}")) for z in ("", ".gz"))


@pytest.fixture
def record(monkeypatch):
    import book_log
    import chain_backfill
    import chain_live
    import dext_log
    import jarvis
    import trigger_log
    monkeypatch.setattr(book_log, "DIR", os.path.join(DATA, "book"))
    monkeypatch.setattr(dext_log, "DIR", os.path.join(DATA, "dext"))
    monkeypatch.setattr(chain_backfill, "DIR", os.path.join(DATA, "chain_backfill"))
    monkeypatch.setattr(chain_live, "CHAIN_DIR", pathlib.Path(DATA, "chain"))
    monkeypatch.setattr(trigger_log, "PATH", os.path.join(DATA, "trigger_log.jsonl"))
    monkeypatch.setattr(jarvis, "MSG_DIR", os.path.join(DATA, "messages"))
    return jarvis


@pytest.mark.skipif(not _has("2026-10-30"), reason="30 Oct record not present")
def test_30oct_up_leg_has_no_lean_change(record):
    out = legs.read(record.build("2026-10-30", "NIFTY", None))
    rows = [r for r in out["rows"] if "11:00" <= r["t"] <= "12:10"]
    assert rows and leans(rows) == 0 and all(r["lean"] == 1 for r in rows)
    assert any(r["word"] == "PALAT" and r["t"] == "13:42" for r in out["rows"])


@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_29oct_has_no_lean_change_all_day(record):
    out = legs.read(record.build("2026-10-29", "NIFTY", None))
    assert leans(out["rows"]) == 0 and out["day"]["flips"][-1] == 0
    assert all(r["lean"] == 1 for r in out["rows"] if r["t"] >= "10:00")


# ---- freshness: evidence must be fresh (a 3-hour shallow consolidation is HOLD) ----------------------------------------

def test_stale_items_expire():
    """A mark older than MARK_FRESH_MIN is a note; premium is read over the last PREM_FRESH min once the pause is old;
    inside 1 sigma needs the price to have come back, not VWAP to have walked up."""
    up = ramp(23000, 23100, 20)                                        # 10:00-10:19
    flat = [23092] * 40                                                # 10:20-10:59: a 0.08 pullback that just sits there
    N = 20 + len(flat)
    d = frame(up + flat)
    d["vwap"] = [23000.0] * 20 + [23000.0 + 3.0 * i for i in range(len(flat))]   # VWAP walks up to price: z falls under 1
    bar = (m2i("10:15") * 60 - 19800) * 1000
    marks = [{"id": "trap@x", "t": bar, "kind": "trap", "name": "▼ KHARIDNE WALE PHANSE", "winner": -1, "p": 23100.0, "prov": False}]
    chain = {}
    for i, (t, s) in enumerate(zip(d["mins"], d["spot"])):
        ltp = 100.0 if i < 20 else 100.0 + 0.5 * (s - 23100) - 6.0    # a 6 Rs bleed at the extreme, then flat for 40 min
        chain[t] = {"spot": s, "ce": {"23100": {"ltp": ltp, "delta": 0.5}}, "pe": {}}
    w = {r["t"]: r for r in legs.read(d, chain=chain, marks=marks)["rows"]}
    assert any(x["k"] == "mark_against" for x in w["10:25"]["risk"])            # known 10:21, fresh
    assert not any(x["k"] == "mark_against" for x in w["10:40"]["risk"])        # 19 min old: a note
    assert any(x["k"] == "mark_old" and "old" in x["text"] for x in w["10:40"]["notes"])
    assert any(x["k"] == "premium_bleeding" for x in w["10:22"]["risk"])        # young pause: read from the extreme
    assert not any(x["k"] == "premium_bleeding" for x in w["10:45"]["risk"])    # old pause: the last 15 min were flat
    assert not any(x["k"] == "inside_1sigma" for x in w["10:50"]["risk"])       # VWAP came to price; retrace 0.08 < 0.20
    assert w["10:50"]["word"] == "HOLD" and w["10:59"]["word"] == "HOLD"
    d2 = frame(up + [23092, 23078, 23078, 23078, 23078], vwap=23060.0)          # z 0.9 and 0.22 of the leg given back
    assert any(x["k"] == "inside_1sigma" for x in legs.read(d2)["rows"][-1]["risk"])


# ---- Jarvis v3 Task 1: the day's first leg scales with the day; the open is not announced -------------------------------

def test_the_first_leg_needs_2U():
    """LEG_MIN_U: U = max(sigma, 0.1 % of price) = 23 at 23,000 with sigma 10, so the first leg needs 46 pts, not 40."""
    assert legs.LEG_MIN_U == 2.0
    rows = legs.read(frame(ramp(23000, 23042, 15), sd=10.0))["rows"]   # bars +/-1: a 44-pt swing
    assert rows[-1]["word"] == "NO LEG" and "no 46-pt swing yet" in rows[-1]["line"]
    rows = legs.read(frame(ramp(23000, 23046, 15), sd=10.0))["rows"]   # 48 pts
    assert rows[-1]["leg"] and rows[-1]["lean"] == 1


def test_before_10_every_leg_row_reads_opening_with_its_lean():
    d = frame(ramp(23000, 23110, 31), start="09:15", pushes=[{"t": "09:25", "dir": 1, "ans": "TOOT", "am": "09:27", "artifact": False}])
    rows = legs.read(d)["rows"]
    assert rows[-1]["leg"]["quality"] == "TREND" and rows[-1]["word"] == "OPENING" and rows[-1]["lean"] == 1
    down = ramp(23000, 22900, 21)                                      # 09:15-09:35 down 100, then half back: a PALAT at 09:4x
    rows = legs.read(frame(down + ramp(22905, 22960, 12), start="09:15"))["rows"]
    flip = [r for r in rows if r["leg"] and r["leg"]["quality"] == "PALAT"]
    assert flip and all(r["word"] == "OPENING" and r["lean"] == 1 for r in flip)
    assert all(r["word"] in ("NO LEG", "OPENING") for r in rows)


def test_the_wall_behind_and_push_with_chips_are_known_the_minute_after_their_read():
    """legs.wall_behind_broke (one rule with Jarvis's EXIT-class WATCH) and push_with: an answer read at 10:21 is known at
    10:22, not at 10:21; a PHANS against the leg counts as the wall behind broken; an artifact push is never read."""
    def chips(pushes):
        d = pause_frame()
        d["pushes"] = pushes
        return {r["t"]: [x["k"] for x in r["risk"] + r["alive"]] for r in legs.read(d)["rows"]}
    against = {"t": "10:20", "dir": -1, "ans": "PHANS", "am": "10:21", "artifact": False}
    w = chips([against])
    assert "wall_behind_broke" not in w["10:21"] and "wall_behind_broke" in w["10:22"]
    w = chips([dict(against, artifact=True)])
    assert not any("wall_behind_broke" in v for v in w.values())
    w = chips([{"t": "10:20", "dir": 1, "ans": "TOOT", "am": "10:21", "artifact": False}])
    assert "push_with" not in w["10:21"] and "push_with" in w["10:22"]
    assert legs.wall_behind_broke([against], 1, m2i("10:22")) is against and legs.wall_behind_broke([against], 1, m2i("10:21")) is None
