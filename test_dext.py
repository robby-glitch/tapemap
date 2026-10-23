"""Gate 3: the Dext record (dext_log.py) and the three-way parity (dext_parity.py), on the trader's own export.

The fixture is her Dext NIFTY OCT FUT export (30 Sep, 1 Oct, 5 Oct candles + getData rows) and the matching
Upstox (ux_) and GoCharting (tape_) rows from data/tape, trimmed. It goes in exactly as the extension sends it --
batches of <= 1,500 candles through dext_log.store -- and the parity must reproduce her manual run."""
import gzip
import json
import os

import pytest

import dext_log
import dext_parity
import tape_log

FX = os.path.join(os.path.dirname(__file__), "test", "fixtures", "dext_parity_NIFTY_2026-10-05.json.gz")


@pytest.fixture
def fx(tmp_path, monkeypatch):
    monkeypatch.setattr(dext_log, "DIR", str(tmp_path / "dext"))
    dext_log._SEEN.clear()
    with gzip.open(FX, "rt", encoding="utf-8") as f:
        x = json.load(f)
    for i in range(0, len(x["candles"]), 1500):
        r = dext_log.store({"inst": x["inst"], "name": x["name"], "candles": x["candles"][i:i + 1500],
                            "ohlc": x["ohlc"] if i == 0 else []})
        assert r["ok"]
    os.makedirs(tape_log.DIR, exist_ok=True)
    for day in x["ux"]:
        for name, rows in (("ux", x["ux"][day]), ("tape", x["gc"][day])):
            with open(os.path.join(tape_log.DIR, f"{name}_NIFTY_{day}.jsonl"), "w", encoding="utf-8") as f:
                f.write("".join(json.dumps(r) + "\n" for r in rows))
    return x


# her manual run, same contract, first bar excluded
REF = {"2026-09-30": dict(of=70, vol=(53067, 53067, 53076), dsum=(-6343, -8188, -7390), ss=(66, 49), cells=True),
       "2026-10-01": dict(of=74, vol=(83694, 83689, 83674), dsum=(-1570, -5998, 14), ss=None, cells=False),
       "2026-10-05": dict(of=74, vol=(49242, 49234, 49233), dsum=(-1544, -2372, -1509), ss=(60, 62), cells=True)}


@pytest.mark.parametrize("day", sorted(REF))
def test_parity_reproduces_the_manual_run(fx, day):
    ref, r = REF[day], dext_parity.report(day)
    assert r["ok"] and r["contract"]["same"] and r["lot"] == 65, r
    assert r["of"] == ref["of"]
    assert tuple(round(r["vol"][s]) for s in "DUG") == ref["vol"]
    assert tuple(round(r["delta_sum"][s]) for s in "DUG") == ref["dsum"]
    if ref["ss"]:
        assert (r["same_sign_delta"]["DU"], r["same_sign_delta"]["DG"]) == ref["ss"]
    if ref["cells"]:
        assert round(r["cell_overlap_median"]["DU"], 2) == 0.90 and round(r["cell_overlap_median"]["DG"], 2) == 0.90
    assert r["first_bar"]["time"] == "09:15" and r["first_bar"]["vol"]["D"] > r["first_bar"]["vol"]["U"]   # the pre-open, folded in
    assert r["closing_auction"]["minutes"] == 10 and r["closing_auction"]["vol_D"] > 0
    assert all(len(r["top_cells"][s]) == 5 for s in "DUG")
    assert "winner" not in json.dumps(r).lower()


def test_another_contract_is_not_compared(fx, tmp_path):
    rows = fx["ux"]["2026-10-05"]
    with open(tape_log.ux_path("2026-10-05", "NIFTY"), "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(dict(r, ik="NSE_FO|35000")) + "\n" for r in rows))
    with open(os.path.join(dext_log.DIR, "instruments.json"), encoding="utf-8") as f:
        reg = json.load(f)
    reg["NSE-48704"]["lot"] = 65                  # the lot can no longer come from Upstox's dump: the config says it
    with open(os.path.join(dext_log.DIR, "instruments.json"), "w", encoding="utf-8") as f:
        json.dump(reg, f)
    r = dext_parity.report("2026-10-05")
    assert r["ok"] and not r["contract"]["same"] and set(r["vol"]) == {"D"}
    assert "another contract" in r["contract"]["why"] and "NSE_FO|35000" in r["contract"]["why"]


def test_no_candles_and_the_evening_run(fx, capsys):
    assert dext_parity.main(["dext_parity.py", "2026-10-02"]) == 0
    assert "could not check — no Dext candles for 2026-10-02" in capsys.readouterr().out
    assert dext_parity.main(["dext_parity.py", "2026-10-05"]) == 0
    out = capsys.readouterr().out
    assert "49,242 / 49,234 / 49,233" in out and "DU 60/74 DG 62/74" in out
    assert json.load(open(os.path.join(dext_log.DIR, "parity_2026-10-05.json"), encoding="utf-8"))["of"] == 74


def test_store_is_idempotent_and_last_wins(fx):
    day, k = "2026-10-05", "NSE-48704"
    p = dext_log.candles_path(k, day)
    size = os.path.getsize(p)
    c = next(c for c in fx["candles"] if c["time"].startswith(day + " 15:39"))
    assert dext_log.store({"inst": fx["inst"], "candles": [c] * 3})["stored"] == {day: 3}
    assert os.path.getsize(p) == size                           # an identical re-send writes nothing
    dext_log._SEEN.clear()                                      # a restart reads the file once and still writes nothing
    dext_log.store({"inst": fx["inst"], "candles": [c]})
    assert os.path.getsize(p) == size
    dext_log.store({"inst": fx["inst"], "candles": [dict(c, total_volume=c["total_volume"] + 65)]})   # Dext filled it late
    rows = dext_log.read_candles(k, day)
    assert len(rows) == 385 and len({r["t"] for r in rows}) == 385
    assert rows[-1]["total_volume"] == c["total_volume"] + 65


def test_only_allowed_fields_are_kept():
    c = {"t": 1791171900, "time": "2026-10-05 09:15:00", "high": 1, "low": 1, "buy_volume": 1, "sell_volume": 0,
         "neutral_volume": 0, "total_volume": 1, "delta": 1, "cumulative_delta": 1, "client_id": 1100012345,
         "levels": [{"price": 1, "buy_volume": 1, "sell_volume": 0, "neutral_volume": 0, "total_volume": 1, "delta": 1, "token": "x"}]}
    out = dext_log.clean_candle(c)
    assert "client_id" not in out and "token" not in out["levels"][0]
    assert set(dext_log.clean_ohlc({"t": 1791171900, "o": 1, "h": 1, "l": 1, "c": 1, "v": 1, "oi": 2, "uid": 7})) == {"t", "o", "h", "l", "c", "v", "oi"}


@pytest.mark.parametrize("bad", [
    {"inst": {"EXCH": "NSE", "SEG": "D", "SEC_ID": "48704;rm"}},
    {"inst": {"EXCH": "NSE", "SEG": "D", "SEC_ID": "48704"}, "name": "user 1100012345"},
    {"inst": {"EXCH": "NSE", "SEG": "D", "SEC_ID": "48704"}, "candles": [{"t": 1791171930}]},              # not a whole minute
    {"inst": {"EXCH": "NSE", "SEG": "D", "SEC_ID": "48704"}, "candles": [{"t": 1791171900, "high": float("inf")}]},
    {"inst": {"EXCH": "NSE", "SEG": "D", "SEC_ID": "48704"}, "candles": [{"t": 1791171900, "total_volume": -5}]},
    {"inst": {"EXCH": "NSE", "SEG": "D", "SEC_ID": "48704"}, "candles": [{"t": 1791171900, "time": "<script>"}]},
    {"inst": {"EXCH": "NSE", "SEG": "D", "SEC_ID": "48704"}, "candles": [{"t": 1791171900}] * 2001},
    {"inst": {"EXCH": "NSE", "SEG": "D", "SEC_ID": "48704"}, "ohlc": [{"t": 1791171900, "o": "22600"}]},
])
def test_absurd_payloads_are_refused_whole(bad, tmp_path, monkeypatch):
    monkeypatch.setattr(dext_log, "DIR", str(tmp_path / "dext"))
    with pytest.raises(dext_log.Refused):
        dext_log.store(bad)
    assert not os.path.exists(tmp_path / "dext")


def test_the_door(monkeypatch, tmp_path):
    """POST /api/dext/candles: the extension's Origin in, a web page's out; a refusal is a 400, never a 500."""
    import io
    import server
    monkeypatch.setattr(dext_log, "DIR", str(tmp_path / "dext"))
    dext_log._SEEN.clear()

    def post(body, headers):
        h = server.Handler.__new__(server.Handler)
        raw = json.dumps(body).encode()
        h.path, h.rfile, h.wfile = "/api/dext/candles", io.BytesIO(raw), io.BytesIO()
        h.headers = {"Content-Length": str(len(raw)), **headers}
        sent = {}
        h.send_response = lambda code, *a: sent.setdefault("code", code)
        h.send_header = lambda *a: None
        h.end_headers = lambda: None
        h.do_POST()
        return sent["code"], json.loads(h.wfile.getvalue())

    body = {"inst": {"EXCH": "NSE", "SEG": "D", "SEC_ID": "48704"}, "name": "NIFTY OCT FUT",
            "candles": [{"t": 1791171900, "time": "2026-10-05 09:15:00", "high": 2, "low": 1, "total_volume": 65, "levels": []}]}
    code, out = post(body, {"Sec-Fetch-Site": "cross-site", "Origin": "https://evil.example"})
    assert code == 403 and not out["ok"]
    code, out = post(body, {"Sec-Fetch-Site": "none", "Origin": "chrome-extension://abcdef"})
    assert code == 200 and out == {"ok": True, "stored": {"2026-10-05": 1}, "last_t": 1791171900}
    code, out = post({**body, "candles": [{"t": 5}]}, {"Origin": "chrome-extension://abcdef"})
    assert code == 400 and not out["ok"] and "t must be" in out["why"]
