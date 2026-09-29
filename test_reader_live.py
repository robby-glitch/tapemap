"""reader_live.py -- the shadow hook: tails the book file, appends its log once, survives a restart without
repainting, and fails soft. Everything under tmp_path (conftest redirects book_log, tape_log and reader_live)."""
import json
import os
from datetime import datetime

import book_log
import reader
import reader_live

DAY = "2026-09-29"
PRIOR = "2026-09-28"


def ms(day, hh, mm, ss=0):
    return int(datetime.fromisoformat(f"{day}T{hh:02d}:{mm:02d}:{ss:02d}+05:30").timestamp() * 1000)


def book_rows(day, points, minutes, oi_step=0):
    """One row every 2 s: ltp walked through (minute, price) points, bought at the ask, OI stepping per minute."""
    rows, vtt, prev = [], 0, None
    for k in range(minutes * 30):
        m = k / 30
        seg = next(((a, b) for a, b in zip(points, points[1:]) if a[0] <= m <= b[0]), (points[-2], points[-1]))
        (m0, p0), (m1, p1) = seg
        p = round(p0 + (p1 - p0) * (m - m0) / (m1 - m0), 1)
        up = prev is None or p >= prev
        vtt += 65 * 3
        t = ms(day, 9, 15) + k * 2000
        rows.append({"t": t, "ltt": t, "ltp": p, "ltq": 195, "vtt": vtt, "oi": 6_500_000 + 65 * oi_step * int(m),
                     "b": [[round(p - 0.1, 1) if up else p, 650]], "a": [[p if up else round(p + 0.1, 1), 650]],
                     "ik": "NSE_FO|68407", "expiry": "2026-09-29"})
        prev = p
    return rows


def write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def setup(monkeypatch, tmp_path):
    monkeypatch.setattr(reader_live, "IDXS", ("NIFTY",))
    monkeypatch.setitem(reader_live._CFG, "lot_tick", lambda idx: (65, 10.0))
    reader_live._DAYS.clear()
    reader_live._READ.clear()
    zig = [(0, 100), (4, 102), (8, 99), (12, 101), (16, 100)]       # a calm prior day: 1-min unit ~1 pt
    write(book_log.day_path(PRIOR, "NIFTY"), book_rows(PRIOR, zig, 16))
    today = [(0, 100), (10, 160), (15, 130), (25, 190), (30, 170)]
    write(book_log.day_path(DAY, "NIFTY"), book_rows(DAY, today, 30, oi_step=100))


def test_the_hook_reads_the_book_logs_once_and_serves_shadow(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    reader_live.tick(ms(DAY, 9, 46), DAY)
    out = reader_live.read("NIFTY")
    assert out["ok"] and out["shadow"] and out["signed"] is False
    assert out["legs"] and all(L["idx"] == "NIFTY" and "x" in L for L in out["legs"])
    path = reader_live.log_path("NIFTY", DAY)
    n = len(open(path, encoding="utf-8").read().splitlines())
    assert n >= len(out["legs"])
    reader_live.tick(ms(DAY, 9, 47), DAY)                             # nothing new: nothing appended
    assert len(open(path, encoding="utf-8").read().splitlines()) == n


def test_a_restart_repaints_nothing(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    reader_live.tick(ms(DAY, 9, 46), DAY)
    before = reader_live.read("NIFTY")
    path = reader_live.log_path("NIFTY", DAY)
    lines = open(path, encoding="utf-8").read().splitlines()
    reader_live._DAYS.clear()                                         # the server restarts
    reader_live.tick(ms(DAY, 9, 46), DAY)
    after = reader_live.read("NIFTY")
    assert open(path, encoding="utf-8").read().splitlines() == lines   # no row written twice
    assert [L["en"] for L in after["legs"]] == [L["en"] for L in before["legs"]]


def test_the_hook_fails_soft(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)

    def boom(self, m):
        raise RuntimeError("synthetic")
    monkeypatch.setattr(reader.Engine, "step", boom)
    reader_live.tick(ms(DAY, 9, 46), DAY)                             # never raises
    out = reader_live.read("NIFTY")
    assert out["ok"] is False and "could not check" in out["why"] and "synthetic" in out["why"]


def test_no_book_yet_is_said_not_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(reader_live, "IDXS", ("SENSEX",))
    monkeypatch.setitem(reader_live._CFG, "lot_tick", lambda idx: (20, 5.0))
    reader_live._DAYS.clear()
    reader_live.tick(ms(DAY, 9, 20), DAY)
    out = reader_live.read("SENSEX")
    assert out["ok"] is False and "no Upstox book rows" in out["why"]
    assert reader_live.read("BANKNIFTY")["why"].startswith("could not check")
