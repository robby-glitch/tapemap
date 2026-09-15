# tapemap/test_frame.py
"""frame.py is composition only: every field carries src and tag, every
absence a reason, and a chain that did not answer yields PATA NAHI per block
with a distinct why -- never undefined, never a number."""
import copy
import json
import frame

TAPE = {"kind": "frame", "session": "NIFTY-I|5m|2026-09-11", "idx": "NIFTY", "interval": 5, "rowSize": 5, "futPx": 23350.0,
        "closed": [{"t": 1757563500000 + i * 300000, "o": 23300 + i, "h": 23310 + i, "l": 23290 + i, "c": 23305 + i,
                    "vol": 100, "delta": -10, "buy": 45, "sell": 55, "oi": 1000, "fromTicks": True} for i in range(14)],
        "forming": None,
        "bands": [{"t": 1757563500000 + i * 300000, "vwap": 23300.0, "sigma": 20.0, "u1": 23320.0, "d1": 23280.0,
                   "u2": 23340.0, "d2": 23260.0, "u3": 23360.0, "d3": 23240.0} for i in range(14)],
        "walls": [{"price": 23385.0, "side": -1, "size": 24000, "hits": 7, "since": "11:55", "wall": True}],
        "broke": [{"price": 23370.0, "side": 1, "brokenT": 1757567100000}],
        "events": [{"t": 1757563500000 + 3 * 300000, "kind": "absorption", "side": 1, "p": 23300.0, "size": 900}],
        "taps": [{"t": 1757563500000 + 6 * 300000, "i0": 6, "side": 1, "price": 23300.0, "z": -3.19, "ex": {"5": None, "15": None, "30": None}}]}

BOOK = {"warmap": {"ok": True, "spot": 23315.0, "band": 7.0,
                   "levels": [{"kind": "PDH", "px": 23448.1, "frame": "index", "tag": "M", "stable": True},
                              {"kind": "ROUND", "px": 23300.0, "frame": "index", "tag": "M", "stable": True}],
                   "sequence": {"PDH@23448.1": {"state": "IDLE", "tests": 2, "last_outcome": "REJECT"},
                                "ROUND@23300.0": {"state": "RUN", "tests": 3, "last_outcome": "REJECT"}},
                   "dwell": {"active": False, "why": "price is not at any known level"},
                   "heat": [{"k": 23300, "ce_oi": 18.5e6, "ce_chg": 15.7e6, "ce_pain": 0.0, "ce_conf": "session",
                             "pe_oi": 32.1e6, "pe_chg": 18.2e6, "pe_pain": 6.3, "pe_conf": "session"}],
                   "runways": {}, "driver": {"lean": "UNCLEAR"}},
        "minutes": {"09:16": {"spot": 23300.0, "k": {23300: (0.0, 0.0)}}, "09:31": {"spot": 23310.0, "k": {23300: (5e6, -2e6)}}},
        "spot": 23315.0, "expiry": "2026-09-15", "zone_state": None, "zone_state_sell": None,
        "vpin_pct": 0.56, "senses": None, "ivrv": None, "coverage": {"server_up": "09:41"}}

BLOCKS = ("header", "session", "paid", "failing", "ladder", "fuel", "zone", "watch", "footer")


def _every_item(fr):
    for name in BLOCKS:
        for it in fr[name]["items"]:
            yield name, it


# M13: every item must carry M or I -- a hole is the one legitimate exception,
# and only where THIS fixture actually produces one (verified against
# frame.build(TAPE, BOOK, ...) directly, not assumed): the footer block is
# wholesale exempt (its items are meta, never M/I by design), the header's
# "session" item is allowed None defensively (it is "M" today but is a raw
# tape passthrough with no measurement behind it), and three specific holes
# this fixture is known to produce -- FAILING has fewer than 4 chain minutes,
# FUEL's senses is None, and ZONE's chosen machine (sell, since futPx sits in
# the fixture's u2-u3 pocket) has no zone_state_sell to read.
ALLOWED_NONE_TAG = {("header", "session"), ("failing", "writing pace"), ("fuel", "gear"), ("zone", "setup (sell)")}


def test_every_item_is_tagged_and_sourced():
    fr = frame.build(TAPE, BOOK, "10:20")
    for name, it in _every_item(fr):
        if name == "footer" or (name, it["k"]) in ALLOWED_NONE_TAG:
            assert it["tag"] in ("M", "I", None), (name, it)
        else:
            assert it["tag"] in ("M", "I"), (name, it)
        assert fr[name]["src"], name
    assert fr["have_bars"] == 14 and "PATA NAHI" not in json.dumps(fr["paid"])


def test_chain_removed_yields_pata_nahi_per_block_with_distinct_reasons():
    fr = frame.build(TAPE, {"coverage": {}}, "10:20")
    whys = [it["why"] for name, it in _every_item(fr) if it["v"] == "PATA NAHI"]
    assert whys and len(set(whys)) == len(whys)
    assert "undefined" not in json.dumps(fr)
    assert all(it["v"] not in (None, "None") for _, it in _every_item(fr))
    # the tape half still reads
    assert any(it["k"].startswith("S ") for it in fr["ladder"]["items"])


def test_one_unjoined_bar_refuses_only_its_own_block():
    """I1: an unjoined first bar (o is None, as the adapter emits before the
    OHLC message has joined) must not take the whole frame down -- only
    SESSION should refuse, with its own reason, while ZONE (which never
    reads o/c) still ships its items."""
    tape = copy.deepcopy(TAPE)
    tape["closed"][0]["o"] = None
    fr = frame.build(tape, BOOK, "10:20")
    assert fr["ok"] is True
    assert any(it["v"] == "PATA NAHI" and it["why"] == "the first/last bar has no joined OHLC yet"
               for it in fr["session"]["items"])
    assert fr["zone"]["items"]


def test_window_change_is_a_difference_of_cumulative_marks():
    assert frame.window_change(BOOK["minutes"], "09:16", "09:31") == {23300: (5e6, -2e6)}
    assert frame.window_change(BOOK["minutes"], "09:16", "09:20") == {}


def test_a_strike_row_moves_with_the_basis_and_says_so():
    b35 = frame.ladder(TAPE, dict(BOOK, spot=23315.0))["rows"]
    b118 = frame.ladder(dict(TAPE, futPx=23433.0), dict(BOOK, spot=23315.0))["rows"]
    pe35 = next(r for r in b35 if r["kind"] == "PE"); pe118 = next(r for r in b118 if r["kind"] == "PE")
    assert pe35["p"] == 23335.0 and pe118["p"] == 23418.0
    assert pe35["why"] == frame.BASIS_WHY and pe118["why"] == frame.BASIS_WHY


def test_a_level_with_no_machine_state_is_not_a_row():
    book = dict(BOOK, warmap=dict(BOOK["warmap"], sequence={}))
    kinds = [r["kind"] for r in frame.ladder(TAPE, book)["rows"]]
    assert "PDH" not in kinds and "ROUND" not in kinds and "S" in kinds and "PE" in kinds


def test_rows_are_sorted_and_carry_distance():
    rows = frame.ladder(TAPE, BOOK)["rows"]
    assert [r["p"] for r in rows] == sorted((r["p"] for r in rows), reverse=True)
    assert all(r["d"] is not None for r in rows) and next(r for r in rows if r["kind"] == "PX")["d"] == 0.0
