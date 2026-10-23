"""effort.py (A44): Fable's effort-per-point read, ported -- equal to his harness's events on a recorded day, its edges,
and the DECODE line. Synthetic except the recorded-day test (skipped when the day's files are not on this machine)."""
import gzip
import json
import os

import pytest

import decode
import effort

HERE = os.path.dirname(os.path.abspath(__file__))
M = lambda hhmm: int(hhmm[:2]) * 60 + int(hhmm[3:])        # noqa: E731


def _rows(path):
    p = path if os.path.exists(path) else path + ".gz"
    op = gzip.open if p.endswith(".gz") else open
    with op(p, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def test_the_definition_is_fables_on_a_recorded_day():
    """22 Oct NIFTY: every lambda event (>= 2x / <= 0.5x the day median at a fresh high / low, mirrors too) and every
    fresh-extreme minute equal oi-lab/flow/proto/audit.py's cached run (test/fixtures/kyle_expected_NIFTY_2026-10-22)."""
    want = json.load(open(os.path.join(HERE, "test", "fixtures", "kyle_expected_NIFTY_2026-10-22.json"), encoding="utf-8"))
    book = os.path.join(HERE, "data", "book", "book_NIFTY_2026-10-22.jsonl")
    chain = os.path.join(HERE, "data", "chain", "chain_NIFTY_2026-10-22.jsonl")
    if not all(os.path.exists(p) or os.path.exists(p + ".gz") for p in (book, chain)):
        pytest.skip("22 Oct's book / chain records are not on this machine")
    fm = effort.minutes(_rows(book), 65)
    spot = {r["sec"] // 60: r["spot"] for r in _rows(chain) if isinstance(r, dict) and "sec" in r and r.get("spot") is not None}
    assert sorted(effort.events(fm, spot, 50)) == sorted(tuple(x) for x in want["kyle"])
    assert sorted((m, k) for m, k in effort.extremes(spot, 50).items() if k and m in fm) == sorted(tuple(x) for x in want["ext"])


def test_minutes_is_flowlabs_volume_and_range():
    t0 = (M("10:00") * 60 - 19800) * 1000
    lv = [[1, 1]]
    rows = [{"t": t0, "ltp": 100.0, "vtt": 650, "b": lv, "a": lv},              # first row: no volume of its own
            {"t": t0 + 1000, "ltp": 101.0, "vtt": 780, "b": lv, "a": lv},       # +130 = 2 lots
            {"t": t0 + 2000, "ltp": 99.0, "vtt": 780, "b": [], "a": lv},        # no bid level: skipped
            {"t": t0 + 60000, "ltp": 102.0, "vtt": 715, "b": lv, "a": lv},      # vtt fell: no volume, next minute
            {"t": t0 + 61000, "ltp": 103.0, "vtt": 845, "b": lv, "a": lv}]      # +130 since the previous kept row
    fm = effort.minutes(rows, 65)
    assert fm == {M("10:00"): {"vol": 2.0, "h": 101.0, "l": 100.0}, M("10:01"): {"vol": 2.0, "h": 103.0, "l": 102.0}}


def day(last=M("10:10"), vol=None, step=1.0, flat_from=None):
    """A clean rising tape from 09:15: 1 pt a minute, each minute's range 1 pt, 10 lots a minute -> 10 lots a point
    over any 5 minutes (5 pts), so the day median is 10. `vol` = {minute: lots}; `flat_from` stops the rise."""
    fm, spot = {}, {}
    for m in range(M("09:15"), last + 1):
        p = 22500 + step * (min(m, flat_from or m) - M("09:15"))
        fm[m] = {"vol": (vol or {}).get(m, 10.0), "h": p + 0.5, "l": p - 0.5}
        spot[m] = p - 80
    return fm, spot


def test_the_day_median_needs_six_blocks_so_the_first_read_is_0956():
    fm, spot = day()
    e = effort.read("NIFTY", fm, spot, M("09:55"))
    assert e["x"] is None and "has 5" in e["why"] and "09:56" in e["why"] and e["tag"] == "I"
    e = effort.read("NIFTY", fm, spot, M("09:56"))
    assert e["x"] == 1.0 and e["at"] == "HIGH" and e["word"] == "normal" and e["lpp"] == 10.0 and e["med"] == 10.0


def test_an_expensive_high_and_a_cheap_low_and_the_failed_mirrors():
    fm, spot = day(vol={m: 25.0 for m in range(M("10:06"), M("10:11"))})
    e = effort.read("NIFTY", fm, spot, M("10:10"))
    assert (e["at"], e["t"], e["x"], e["word"]) == ("HIGH", "10:10", 2.5, "mehenga (palat?)")
    g = {"idx": "NIFTY", "bars5": [], "effort": e}
    assert decode._effort_line(g) == "EFFORT 2.5× din ka · high 10:10 mehenga (palat?) [I]"
    fm, spot = day(vol={m: 2.0 for m in range(M("10:06"), M("10:11"))})
    assert effort.read("NIFTY", fm, spot, M("10:10"))["word"] == "sasta · read nahi"       # cheap high: the mirror failed
    fm, spot = day(step=-1.0, vol={m: 4.0 for m in range(M("10:06"), M("10:11"))})
    e = effort.read("BANKNIFTY", fm, spot, M("10:10"))
    assert (e["at"], e["word"]) == ("LOW", "sasta (aur girega?)") and e["x"] == 0.4
    assert decode._effort_line(dict(g, idx="BANKNIFTY", effort=e)).endswith("low 10:10 sasta (aur girega?) [I · BNF test nahi]")
    fm, spot = day(step=-1.0, vol={m: 30.0 for m in range(M("10:06"), M("10:11"))})
    assert effort.read("NIFTY", fm, spot, M("10:10"))["word"] == "mehenga · read nahi"     # expensive low: noise


def test_the_line_never_shows_a_threshold_it_has_not_crossed():
    assert decode._xs(1.99) == "1.9×" and decode._xs(2.0) == "2.0×" and decode._xs(0.51) == "0.6×" and decode._xs(0.5) == "0.5×"


def test_no_fresh_extreme_in_30_minutes_and_it_is_causal():
    fm, spot = day(last=M("10:40"), flat_from=M("10:00"))
    e = effort.read("NIFTY", fm, spot, M("10:40"))
    assert e["at"] is None and e["word"] == "taaza high/low nahi" and e["t"] == "10:40"
    fm2, spot2 = day(vol={m: 25.0 for m in range(M("10:06"), M("10:11"))})
    cut = effort.read("NIFTY", fm2, spot2, M("10:08"))
    later = range(M("10:09"), M("10:30"))
    more = {**fm2, **{m: {"vol": 999.0, "h": 1e5, "l": 0.0} for m in later}}
    assert effort.read("NIFTY", more, {**spot2, **{m: 0.0 for m in later}}, M("10:08")) == cut


def test_sensex_is_not_read_and_says_patla():
    e = effort.read("SENSEX", {}, {}, M("10:10"))
    assert e["x"] is None and e["word"] == "patla" and "too thin" in e["why"]
    g = {"idx": "SENSEX", "bars5": [{"vol": 3}, {"vol": 15}, {"vol": 40}], "effort": e}
    assert decode._effort_line(g) == "EFFORT nahi padha · patla (med 15 lot/5m) [I]"
    assert effort.read("NIFTY", {}, {M("10:00"): 1.0}, M("10:10"))["why"].startswith("could not check — no futures book")


def test_the_server_reads_it_from_the_book_record_and_the_chain_grid():
    """server._decode_effort: Fable's sources -- the book record (book_log, redirected by conftest) and the chain grid's
    spot per minute, REST-backfilled minutes left out; SENSEX not read; no chain grid is "could not check"."""
    import book_log
    import server
    fm, spot = day(vol={m: 25.0 for m in range(M("10:06"), M("10:11"))})
    t0, lv, vtt, rows = (M("09:15") * 60 - 19800) * 1000, [[1, 1]], 0, []
    for m in sorted(fm):                                  # two rows a minute: low then high, the minute's lots between
        f = fm[m]
        rows.append({"t": t0 + (m - M("09:15")) * 60000, "ltp": f["l"], "vtt": vtt, "b": lv, "a": lv})
        vtt += f["vol"] * 65
        rows.append({"t": t0 + (m - M("09:15")) * 60000 + 30000, "ltp": f["h"], "vtt": vtt, "b": lv, "a": lv})
    path = book_log.day_path("2026-01-02", "NIFTY")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in rows))
    grid = {effort.hm(m): {"spot": p} for m, p in spot.items()}
    grid["10:11"] = {"spot": 1.0, "src": "backfill"}
    e = server._decode_effort("NIFTY", "2026-01-02", M("10:15") * 60, {"chain": (grid, {})})
    assert (e["at"], e["t"], e["word"]) == ("HIGH", "10:10", "mehenga (palat?)") and e["x"] > 2
    assert server._decode_effort("SENSEX", "2026-01-02", M("10:15") * 60, None)["word"] == "patla"
    assert server._decode_effort("NIFTY", "2026-01-02", M("10:15") * 60, None)["why"].startswith("could not check")


def test_a_survivor_inside_the_closed_bar_wins_over_a_later_plain_extreme():
    """10:05 carries 60 lots: every window holding it is 2x the median; the 10:10 window is not. The 10:10 close's line
    reads the bar's last firing minute (10:09), not the plain 10:10 high."""
    fm, spot = day(vol={M("10:05"): 60.0})
    assert effort.lam_at(fm, M("10:10"))[0] == 10.0
    e = effort.read("NIFTY", fm, spot, M("10:10"))
    assert (e["at"], e["t"], e["x"], e["word"]) == ("HIGH", "10:09", 2.0, "mehenga (palat?)")
