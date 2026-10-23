"""test_v2feed.py -- the VALIDATE feed: incremental == one-shot, a gzipped day reads, delta + earlier payload == full."""
import gzip
import json
import os
import random

import v2feed

DAY = "2026-10-06"
IDX = ("NIFTY", "BANKNIFTY", "SENSEX")


def _chain_rows(idx, n, base, step, seed):
    rnd = random.Random(seed)
    rows, spot, t = [], base, 9 * 3600 + 17 * 60 + 9
    for i in range(n):
        spot += rnd.uniform(-8, 8)
        atm = round(spot / step) * step
        strikes = []
        for k in range(atm - 8 * step, atm + 9 * step, step):
            strikes.append({"k": k,
                            "ce": {"ltp": max(0.05, spot - k + 30 + rnd.uniform(0, 5)), "oi": int(1e6 + rnd.random() * 3e7), "oi_chg": 0,
                                   "iv": .3, "vol": 1, "bid": 1, "ask": 1.1, "avg": 40 + rnd.random(), "gamma": 0, "delta": rnd.random()},
                            "pe": {"ltp": max(0.05, k - spot + 30 + rnd.uniform(0, 5)), "oi": int(1e6 + rnd.random() * 3e7), "oi_chg": 0,
                                   "iv": .3, "vol": 1, "bid": 1, "ask": 1.1, "avg": 40 + rnd.random(), "gamma": 0, "delta": -rnd.random()}})
        rows.append({"ts": f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}", "sec": t, "spot": round(spot, 2), "atm": atm,
                     "strikes": strikes, "ik": "x", "expiry": DAY})
        t += 11
    return rows


def _book_rows(n, base, seed):
    rnd = random.Random(seed)
    rows, ltp, vtt, ms = [], base, 100, 1791225000000 + (9 * 3600 + 17 * 60) * 1000   # 2026-10-06 00:00 IST is epoch 1791225000; ticks from 09:17:00
    for i in range(n):
        ltp = round(ltp + rnd.choice((-0.2, 0, 0.2, 0.5, -0.5)), 1)
        vtt += rnd.randint(0, 300)
        rows.append({"t": ms, "cts": ms, "ltt": ms, "ltp": ltp, "ltq": 65, "vtt": vtt, "oi": 19000000 + i, "tbq": 1, "tsq": 1,
                     "b": [[ltp - 0.2, 65.0]], "a": [[ltp + 0.2, 65.0]], "ik": "x", "expiry": "2026-10-27"})
        ms += 1000 if i % 3 else 700
    return rows


def _vpin_rows(n):
    out, t = [], 9 * 3600 + 18 * 60
    for b in range(1, n + 1):
        out.append({"at": f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}", "bucket": b, "buy": 14000.0 + b, "sell": 6000.0,
                    "imb": .4, "vpin": .4, "pct": None if b < 10 else .5, "tag": "[I]", "shadow": True, "inst": "NIFTY-FUT:fast", "day": DAY})
        t += 100
    out.append({"at": "09:18:05", "bucket": 1, "buy": 1.0, "sell": 1.0, "imb": 0, "vpin": 0, "pct": None, "day": "2026-10-05"})   # another day: ignored
    return out


def _write(path, rows, upto=None, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding="utf-8") as fh:
        for r in rows[:upto]:
            fh.write(json.dumps(r) + "\n")


def _day(tmp, n_chain=40, n_book=300, split=None):
    """A synthetic day under tmp/data: the first `split` fraction only when split is given."""
    d = str(tmp / "data")
    files = {}
    for n, (idx, base, step) in enumerate((("NIFTY", 22600, 50), ("BANKNIFTY", 55000, 100), ("SENSEX", 72900, 100))):
        c, b = _chain_rows(idx, n_chain, base, step, n), _book_rows(n_book, base + 70, n)
        files[idx] = (c, b)
        _write(os.path.join(d, "chain", f"chain_{idx}_{DAY}.jsonl"), c, None if split is None else int(len(c) * split))
        _write(os.path.join(d, "book", f"book_{idx}_{DAY}.jsonl"), b, None if split is None else int(len(b) * split))
    v = _vpin_rows(14)
    _write(os.path.join(d, "vpin_fast.jsonl"), v, None if split is None else int(len(v) * split))
    return d, files, v


def test_incremental_equals_one_shot(tmp_path):
    d, files, v = _day(tmp_path, split=0.5)
    inc = v2feed.Day(DAY, d)
    inc.refresh()                                                   # the first half
    half = inc.full(now=0, live=False)
    assert half["idx"]["NIFTY"]["t"] and len(half["idx"]["NIFTY"]["t"]) < 40
    for idx, (c, b) in files.items():                               # the second half lands later, appended
        _write(os.path.join(d, "chain", f"chain_{idx}_{DAY}.jsonl"), c[20:], mode="a")
        _write(os.path.join(d, "book", f"book_{idx}_{DAY}.jsonl"), b[150:], mode="a")
    _write(os.path.join(d, "vpin_fast.jsonl"), v[7:], mode="a")
    inc.refresh()
    one = v2feed.Day(DAY, d)
    one.refresh()
    assert inc.full(now=0, live=False) == one.full(now=0, live=False)
    x = one.full()["idx"]["NIFTY"]
    assert len(x["t"]) == 40 and len(x["ks"]) >= 17 and len(x["ce"]["d"]) == 7 and x["bars"] and x["futoi"]
    assert sum(b[2] for b in x["bars"]) == files["NIFTY"][1][-1]["vtt"] - files["NIFTY"][1][0]["vtt"]   # volume conserved
    assert len(one.full()["vpin"]) == 14                            # the other day's row is not ours


def test_partial_last_line_waits(tmp_path):
    d, files, v = _day(tmp_path)
    p = os.path.join(d, "chain", f"chain_NIFTY_{DAY}.jsonl")
    with open(p, "a", encoding="utf-8") as fh:
        fh.write('{"ts": "15:00:00", "sec": 54000, "spot": 22600, "atm": 22600, "strikes": [{"k": 22550, "ce": {"oi": 1, "ltp": 1}, "pe": {"oi": 1, "ltp": 1}}, {"k": 22600, "ce": {"oi": 1, "ltp": 1}')   # torn
    D = v2feed.Day(DAY, d)
    D.refresh()
    assert len(D.idx["NIFTY"].t) == 40                              # the torn row is not a row yet
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(', "pe": {"oi": 1, "ltp": 1}}]}\n')
    D.refresh()
    assert len(D.idx["NIFTY"].t) == 41 and D.idx["NIFTY"].t[-1] == 54000


def test_gz_day_reads(tmp_path):
    d, files, v = _day(tmp_path)
    plain = v2feed.Day(DAY, d)
    plain.refresh()
    want = plain.full(now=0, live=False)
    for idx in IDX:
        for kind in ("chain", "book"):
            p = os.path.join(d, kind, f"{kind}_{idx}_{DAY}.jsonl")
            with open(p, "rb") as src, gzip.open(p + ".gz", "wb") as dst:
                dst.write(src.read())
            os.remove(p)
    gz = v2feed.Day(DAY, d)
    gz.refresh()
    assert gz.full(now=0, live=False) == want
    gz.refresh()                                                    # a second refresh adds nothing twice
    assert gz.full(now=0, live=False) == want


def test_delta_plus_earlier_equals_full(tmp_path):
    d, files, v = _day(tmp_path, split=0.5)
    D = v2feed.Day(DAY, d)
    D.refresh()
    half = D.full(now=0, live=False)
    since = half["idx"]["NIFTY"]["t"][-1]                           # the face asks from its newest chain second
    for idx, (c, b) in files.items():
        _write(os.path.join(d, "chain", f"chain_{idx}_{DAY}.jsonl"), c[20:], mode="a")
        _write(os.path.join(d, "book", f"book_{idx}_{DAY}.jsonl"), b[150:], mode="a")
    _write(os.path.join(d, "vpin_fast.jsonl"), v[7:], mode="a")
    D.refresh()
    full = D.full(now=0, live=False)
    delta = D.delta(since, now=0, live=False)
    assert delta["idx"]["NIFTY"]["i0"] == 20 and delta["idx"]["NIFTY"]["d0"] == 4
    assert v2feed.merge(half, delta) == full
    assert v2feed.merge(full, D.delta(full["idx"]["NIFTY"]["t"][-1], now=0, live=False)) == full   # nothing new: unchanged


def test_serve_caches_full_and_answers_delta(tmp_path):
    d, files, v = _day(tmp_path)
    b1 = v2feed.serve(DAY, None, d)
    b2 = v2feed.serve(DAY, None, d)
    assert isinstance(b1, bytes) and b1 is b2                       # same file sizes: the same bytes, not re-serialised
    doc = json.loads(b1)
    assert doc["ok"] and doc["day"] == DAY and set(doc["idx"]) == set(IDX) and "now" in doc and doc["live"] == (DAY == v2feed.today())
    dl = v2feed.serve(DAY, doc["idx"]["NIFTY"]["t"][-1], d)
    assert dl["delta"] and dl["idx"]["NIFTY"]["t"] == []
    empty = json.loads(v2feed.serve("2019-01-01", None, d))        # a day with no files is an empty, honest payload
    assert empty["ok"] and empty["idx"]["NIFTY"]["t"] == [] and empty["vpin"] == []


# ---------------- LATE START: the rebuilt morning (chain_backfill.py) prepended, tagged, recorded wins ----------------
def _backfill_rows(idx, first_chain_row, n_min, spot0):
    """REST minutes 09:15.. : oi_chg since the open, px; the first recorded row's OI/oi_chg anchor the absolute OI."""
    out, t = [], 9 * 3600 + 15 * 60
    ks = [str(s["k"]) for s in first_chain_row["strikes"]]
    for i in range(n_min):
        out.append({"day": DAY, "index": idx, "t": f"{t // 3600:02d}:{t % 3600 // 60:02d}", "spot": spot0 + i * 0.5,
                    "k": {k: [100.0 * i, 50.0 * i] for k in ks}, "px": {k: [10.0 + i, 20.0 + i] for k in ks}, "src": "backfill", "backfilled": True})
        t += 60
    out.append({"day": DAY, "index": idx, "t": "15:35", "spot": None, "k": {}, "px": {}, "backfilled": True})       # a spot-less post-close mark: dropped
    return out


def test_backfill_precedes_recorded_and_recorded_wins(tmp_path):
    d, files, v = _day(tmp_path)
    c = files["NIFTY"][0]
    first_sec = c[0]["sec"]                                                   # 09:17:09 -> minutes 09:15 and 09:16 qualify, 09:17 does not
    bf = _backfill_rows("NIFTY", c[0], 4, 22590.0)                             # 09:15, 09:16, 09:17, 09:18 (+ the dropped one)
    _write(os.path.join(d, "chain_backfill", f"backfill_NIFTY_{DAY}.jsonl"), bf)
    D = v2feed.Day(DAY, d)
    D.refresh()
    x = D.idx["NIFTY"]
    assert x.bf == 2 and x.bf_from == "09:15" and x.bf_to == "09:16" and x.chain_from == c[0]["ts"]
    assert x.t[:2] == [9 * 3600 + 15 * 60, 9 * 3600 + 16 * 60] and x.t[2] == first_sec and len(x.t) == 42
    assert all(a < b for a, b in zip(x.t, x.t[1:])) and x.t[1] + 60 <= x.t[2]  # never at or after the first recorded row
    k = x.pos[float(c[0]["strikes"][3]["k"])]
    g = c[0]["strikes"][3]["ce"]
    assert x.ce["oi"][0][k] == round((g["oi"] - g["oi_chg"] + 0.0) / 1000)       # OI_first - oi_chg_first + oi_chg(09:15)
    assert x.ce["oi"][1][k] == round((g["oi"] - g["oi_chg"] + 100.0) / 1000)
    assert x.ce["oi"][2][k] == round(g["oi"] / 1000)                              # the recorded row, untouched
    assert x.ce["ltp"][0][k] == round(10.0 * 20) and x.pe["ltp"][1][k] == round(21.0 * 20)
    assert x.spot[0] == 22590.0 and x.spot[2] == round(c[0]["spot"], 1)
    assert x.ce["d"][0][k] is None and x.ce["avg"][0][k] is None                 # a REST candle has no delta / day-avg
    full = D.full(now=0, live=False)["idx"]["NIFTY"]
    assert full["bf"] == 2 and full["bfFrom"] == "09:15" and full["bfTo"] == "09:16" and full["flowFrom"] == "09:17:00" and full["bfWhy"]
    assert D.idx["BANKNIFTY"].bf == 0 and D.full(now=0, live=False)["idx"]["BANKNIFTY"]["bfWhy"] is None   # no file: exactly as before
    plain = v2feed.Day(DAY, d); plain.refresh()
    assert plain.full(now=0, live=False)["idx"]["BANKNIFTY"] == full_no_bf(tmp_path, d)["idx"]["BANKNIFTY"]


def full_no_bf(tmp_path, d):
    D = v2feed.Day(DAY, d); D.refresh(); return D.full(now=0, live=False)


def test_backfill_landing_late_rebuilds_once_and_bumps_gen(tmp_path):
    d, files, v = _day(tmp_path)
    D = v2feed.Day(DAY, d)
    D.refresh()
    x = D.idx["NIFTY"]
    assert x.bf == 0 and x.gen == 0 and len(x.t) == 40
    _write(os.path.join(d, "chain_backfill", f"backfill_NIFTY_{DAY}.jsonl"), _backfill_rows("NIFTY", files["NIFTY"][0][0], 3, 22590.0))
    D.refresh()                                                                 # the file appeared after rows were out
    x = D.idx["NIFTY"]
    assert x.bf == 2 and x.gen == 1 and len(x.t) == 42 and x.t[2] == files["NIFTY"][0][0]["sec"]
    half = D.full(now=0, live=False)
    with_old_gen = dict(half, idx={i: dict(v, gen=0) for i, v in half["idx"].items()})
    try:
        v2feed.merge(with_old_gen, D.delta(x.t[-1], now=0, live=False))
        assert False, "a client on the old layout must be told to reload"
    except ValueError:
        pass
    D.refresh()
    assert D.idx["NIFTY"].gen == 1                                              # rebuilt once, not every refresh



def test_d6_tick_extremes_and_iv_kept_off_the_wire(tmp_path):
    """Every tick's high / low per second (the day's fut high / low from ticks) and the chain's IV (D2's residual) are
    held in memory; the VALIDATE face's payload is byte-for-byte the old shape."""
    d, files, _ = _day(tmp_path)
    D = v2feed.Day(DAY, d)
    D.refresh()
    s = D.idx["NIFTY"]
    ticks = files["NIFTY"][1]
    assert max(h[1] for h in s.hl) == round(max(r["ltp"] for r in ticks) * 10)
    assert min(h[2] for h in s.hl) == round(min(r["ltp"] for r in ticks) * 10)
    assert {v for v in s.ce["iv"][0] if v is not None} == {3000}            # IV 0.30 -> 3000 (x 10^4)
    full = D.full(0, False)["idx"]["NIFTY"]
    assert set(full["ce"]) == {"oi", "ltp", "d", "avg"} and "hl" not in full
