"""xindex_live.py -- the cross-index read on the reader's pass: logs each bar once, a restart repaints nothing, a stale
zone payload is CAN'T CHECK, and a failure costs the reader nothing. Everything under tmp_path."""
import json
import os

import reader_live
import xindex
import xindex_live
from test_reader_live import DAY, ms, setup


def fresh(monkeypatch, tmp_path, zone=None):
    setup(monkeypatch, tmp_path)
    xindex_live._S.clear()
    xindex_live._READ.clear()
    monkeypatch.setitem(xindex_live._CFG, "zone", zone)
    monkeypatch.setitem(xindex_live._CFG, "chain_dir", lambda: str(tmp_path / "chain"))


def rows():
    with open(xindex_live.log_path(DAY), encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_each_bar_is_logged_once_and_served_shadow(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path)
    reader_live.tick(ms(DAY, 9, 46), DAY)
    out = xindex_live.read()
    assert out["ok"] and out["shadow"] and out["signed"] is False and "sheet" in out
    got = rows()
    assert [r["t"] for r in got] == [xindex.hm(c) for c in xindex_live.bar_closes(DAY) if c + 5000 <= ms(DAY, 9, 46)]
    assert len({r["asof"] for r in got}) == len(got)
    n = got[-1]["out"]["idx"]["NIFTY"]
    assert n["lines"]["zone"]["vote"] is None and "zone" in n["lines"]["zone"]["why"]      # no seam: said, not zero
    assert out["out"]["look"]["line"].startswith("LOOK HERE")


def test_a_restart_repaints_nothing(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path)
    reader_live.tick(ms(DAY, 9, 46), DAY)
    before = rows()
    reader_live._DAYS.clear()
    xindex_live._S.clear()
    xindex_live._READ.clear()
    reader_live.tick(ms(DAY, 9, 46), DAY)
    after = rows()
    assert after == before
    assert json.dumps(xindex_live.read()["out"], sort_keys=True, default=str) == \
        json.dumps(before[-1]["out"], sort_keys=True, default=str)


def test_a_stale_zone_payload_is_cant_check(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path, zone=lambda idx: {"label": "Sep 28 LIVE", "buy": [], "sell": []})
    reader_live.tick(ms(DAY, 9, 46), DAY)
    z = rows()[-1]["out"]["idx"]["NIFTY"]["lines"]["zone"]
    assert z["vote"] is None and "another session" in z["why"]


def test_a_failure_costs_the_reader_nothing(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path)

    def boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(xindex, "step", boom)
    reader_live.tick(ms(DAY, 9, 46), DAY)
    assert reader_live.read("NIFTY")["ok"]
    x = xindex_live.read()
    assert not x["ok"] and "xindex failed" in x["why"]
    assert not os.path.exists(xindex_live.log_path(DAY))
