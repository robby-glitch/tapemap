"""test_coverage.py -- COVERAGE (coverage.py, decode-loop §5.1): the 9 Oct gaps by name (D4: the GoCharting 11:15 bar
the page never posted), the REST-rebuilt morning, single-source indices, and the three absences kept apart."""
import datetime

import coverage

DAY = "2026-10-09"
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
T0 = int(datetime.datetime.fromisoformat(DAY).replace(tzinfo=IST).timestamp() * 1000)


def _gc(skip=(), noprice=()):
    """5-min GoCharting rows 09:15 .. 13:55 (57 bars) with the named slots dropped / footprint-only."""
    out = []
    for i in range(57):
        s = 33300 + i * 300
        hm = "%02d:%02d" % (s // 3600, s % 3600 // 60)
        if hm in skip:
            continue
        price = None if hm in noprice else 22500.0
        out.append({"t": T0 + s * 1000, "o": price, "c": price, "h": 22510.0, "l": 22490.0, "vol": 300, "delta": 10})
    return out


def _x(bf=0, first=36660):
    """THE READ's arrays: chain rows a minute apart from 09:16 (REST-rebuilt to 10:10 when bf), ticks from `first`."""
    t = list(range(33360, 50400, 60))
    return {"t": t, "bf": bf, "bars": [[s, 225000, 10, 5] for s in range(first, 50400, 1)]}


def test_the_9_oct_gaps_are_named_d4():
    gc = _gc(skip=("11:15", "12:35", "13:20"), noprice=("09:15", "09:20"))
    rows = coverage.build("NIFTY", _x(bf=55), {"w": {}, "f": {"gc": "10:10"}}, [], gc, now=50400, live=False)
    text = " | ".join(f"{r['kind']}:{r['src']}:{r['text']}" for r in rows)
    assert "cnc:GC:could not check -- GC 11:15 · 12:35 · 13:20 bar nahi aaya" in text
    assert "GC 09:15–09:20 open/close nahi" in text
    assert "ok:CHAIN:OI 09:16–10:10 REST-rebuilt" in text                      # what WAS seen, and how [I]
    assert "fut ticks begin 10:11; FLOW to 10:10 from GoCharting bars" in text
    assert "hidden:LEVELS" in text                                             # a replay shows no levels: on purpose


def test_three_absences_never_merge():
    full = coverage.build("NIFTY", _x(first=33320), {"w": {}, "f": {}, "events": []}, [], _gc(), now=50400,
                          live=False)
    kinds = {(r["src"], r["kind"]) for r in full}
    assert ("GC", "none") in kinds and ("QUIT", "none") in kinds                # checked, nothing
    assert ("LEVELS", "hidden") in kinds                                        # not shown
    assert ("UX", "cnc") in kinds                                               # could not check
    for r in full:
        if r["kind"] == "none":
            assert "could not check" not in r["text"] and "not shown" not in r["text"]
        if r["kind"] == "cnc":
            assert r["text"].startswith("could not check")


def test_banknifty_and_sensex_say_their_flow_is_one_source_d5():
    rows = coverage.build("SENSEX", _x(first=33320), {"w": {}, "f": {}}, [], None, now=50400, live=False)
    gc = [r for r in rows if r["src"] == "GC"]
    assert gc and gc[0]["kind"] == "cnc" and "one source" in gc[0]["text"]


def test_window_edge_and_an_implausible_basis_are_said():
    rows = coverage.build("NIFTY", _x(first=33320), {"w": {"edge": 1}, "f": {}}, [], _gc(), now=50400, live=False,
                          basis={"ok": False, "why": "basis +1.0 implausible: carry 47 at 11 DTE, band 13..95"})
    text = " | ".join(r["text"] for r in rows)
    assert "strike window edge: the nine read ATM ±1 only" in text and "fut levels ?" in text
