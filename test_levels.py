"""levels.py -- the reaction-point map states facts, in the right frame."""

from datetime import date, timedelta

import levels


def test_round_levels_carry_minor_and_major_and_stay_near_spot():
    lv = levels.round_levels("NIFTY", 25000.0)
    pxs = {l["px"]: l for l in lv}
    assert 25000.0 in pxs and pxs[25000.0]["major"] is True
    assert 24950.0 in pxs and pxs[24950.0]["major"] is False
    lo, hi = 25000 * (1 - levels.ROUND_WINDOW), 25000 * (1 + levels.ROUND_WINDOW)
    assert all(lo <= p <= hi for p in pxs)
    assert all(l["stable"] and l["frame"] == "index" for l in lv)


def test_static_levels_absent_until_the_fetch_lands():
    assert levels.static_levels(None) == []
    daily = {"pd": {"date": "2026-08-21", "h": 25100.0, "l": 24900.0,
                    "c": 25050.0},
             "pw": {"h": 25200.0, "l": 24800.0, "start": "2026-08-11"},
             "open": {"px": 25010.0, "tag": "M"}}
    got = {l["kind"]: l for l in levels.static_levels(daily)}
    assert got["PDH"]["px"] == 25100.0 and got["PDH"]["stable"]
    assert got["PWL"]["px"] == 24800.0
    assert got["OPEN"]["px"] == 25010.0
    assert all(l["frame"] == "index" for l in got.values())


def test_chain_levels_drift_and_the_flip_is_inferred():
    strikes = [{"k": 24900, "ce": {"oi": 1e6}, "pe": {"oi": 9e6}},
               {"k": 25100, "ce": {"oi": 8e6}, "pe": {"oi": 2e6}}]
    metrics = {"max_pain": 25000, "flip_px": 24950.0}
    got = {l["kind"]: l for l in levels.chain_levels(metrics, strikes)}
    assert got["CE_WALL"]["px"] == 25100.0
    assert got["PE_WALL"]["px"] == 24900.0
    assert got["GAMMA_FLIP"]["tag"] == "I"
    # drifting levels must never be handed to a sequence machine
    assert all(not l["stable"] for l in got.values())


def test_the_book_reads_sorted_and_carries_the_absence_reason():
    b = levels.Levels("NIFTY")
    r = b.read(25000.0, {}, [])
    assert r["daily_why"]                      # not fetched yet, said aloud
    assert r["n_static"] == 0
    pxs = [l["px"] for l in r["levels"]]
    assert pxs == sorted(pxs, reverse=True)
    b.set_daily({"pd": {"date": "d", "h": 25150.0, "l": 24850.0, "c": 25000.0},
                 "pw": None, "open": None})
    r2 = b.read(25000.0, {}, [])
    assert r2["daily_why"] is None
    assert any(l["kind"] == "PDH" for l in r2["levels"])


def test_fetch_daily_aggregates_prior_day_week_and_open(monkeypatch):
    import upstox_feed
    import upstox_instruments
    import upstox_rest
    today = date.today()
    d1 = today - timedelta(days=1)
    old = [today - timedelta(days=n) for n in (8, 9, 10)]

    def daily_range(key, tok, frm, to, interval="day"):
        mk = lambda d, h, l, c: [f"{d}T00:00:00", c - 5, h, l, c, 0, 0]
        return ([mk(d1, 25100, 24900, 25050)]
                + [mk(d, 25300 + i, 24700 - i, 25000) for i, d in enumerate(old)])

    monkeypatch.setattr(upstox_rest, "daily_range", daily_range)
    monkeypatch.setattr(upstox_rest, "intraday",
                        lambda key, tok, interval="1minute":
                        [["t2", 25020, 0, 0, 0, 0, 0],
                         ["t1", 25010, 0, 0, 0, 0, 0]])
    monkeypatch.setattr(upstox_feed, "read_token", lambda path=None: "tok")
    monkeypatch.setattr(upstox_instruments, "index_key", lambda idx: "K")

    out = levels.fetch_daily("NIFTY")
    assert out["pd"]["h"] == 25100 and out["pd"]["date"] == str(d1)
    assert out["open"]["px"] == 25010          # the OLDEST bar's open
    # the prior-week aggregate covers exactly the newest week strictly before
    # this one -- recomputed here with the same calendar the module uses
    this_week = today.isocalendar()[:2]
    wk = {}
    for i, d in enumerate([d1] + old):
        h = 25100 if i == 0 else 25300 + (i - 1)
        l = 24900 if i == 0 else 24700 - (i - 1)
        if d.isocalendar()[:2] < this_week:
            wk.setdefault(d.isocalendar()[:2], []).append((h, l))
    want = wk[max(wk)]
    assert out["pw"]["h"] == max(h for h, _ in want)
    assert out["pw"]["l"] == min(l for _, l in want)
