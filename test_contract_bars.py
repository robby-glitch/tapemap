"""contract_bars.py -- reshape, VWAP/sigma, and interval aggregation.

Written before the module (TDD). Families:

  1. Reshape      -- epoch -> IST "HH:MM", sorted, ragged arrays truncated to
                     the shortest with the drop RECORDED, non-finite values
                     making that bar None rather than 0.
  2. VWAP/sigma   -- a hand-computed 5-bar fixture, anchoring at the first bar,
                     and the anti-drift lock: contract_bars and live.py must
                     produce byte-identical bands from the same input, because
                     they are the SAME implementation.
  3. Causality    -- bands over bars[0..N] truncated at k equal bands over
                     bars[0..k]. Bar i uses bars 0..i only.
  4. Interval invariance -- 2/3/5/15-minute bands are the 1-minute bands
                     SAMPLED, never recomputed. Changing interval must not
                     move a band by a paisa.
  5. Emptiness    -- empty input returns empty and never throws; no bar is
                     ever invented.
"""

import math

import pytest

import contract_bars
import live

# 2026-07-30 09:15:00 IST. Derived by hand from a real cached session:
# data/backtest/fut_2026-07-17.json's first timestamp is 1784259900, which is
# 2026-07-17 03:45:00Z == 09:15 IST (03:45 + 05:30). Thirteen days later is
# 1784259900 + 13*86400 = 1785383100.
OPEN_EPOCH = 1785383100


def _ts(n):
    """Epoch seconds for the n-th minute after 09:15 IST."""
    return OPEN_EPOCH + 60 * n


def _payload(rows, oi=None, ts=None):
    """rows = [(o, h, l, c, v), ...] -> a rest_intraday-shaped response."""
    n = len(rows)
    d = {"open": [r[0] for r in rows], "high": [r[1] for r in rows],
         "low": [r[2] for r in rows], "close": [r[3] for r in rows],
         "volume": [r[4] for r in rows],
         "timestamp": list(ts) if ts is not None else [_ts(i) for i in range(n)]}
    if oi is not None:
        d["open_interest"] = list(oi)
    return d


# The hand-computed fixture. Each row's typical price (H+L+C)/3 is exactly
# 10, 20, 30, 40, 50 and every bar trades 100 lots, so the whole recurrence
# closes in decimal:
#
#   i cv    ctpv    vwap  (tp-vwap)  v*(tp-vwap)^2  cvar    var=cvar/cv
#   0 100   1000    10     0            0             0        0
#   1 200   3000    15     5         2500          2500      12.5
#   2 300   6000    20    10        10000         12500      125/3
#   3 400  10000    25    15        22500         35000      87.5
#   4 500  15000    30    20        40000         75000     150
#
# sigma is the square root of the last column.
FIXTURE = [(10, 11, 9, 10, 100), (20, 21, 19, 20, 100), (30, 31, 29, 30, 100),
           (40, 41, 39, 40, 100), (50, 51, 49, 50, 100)]
FIX_VWAP = [10.0, 15.0, 20.0, 25.0, 30.0]
FIX_SD = [0.0, math.sqrt(12.5), math.sqrt(125 / 3), math.sqrt(87.5),
          math.sqrt(150.0)]


# --------------------------------------------------------------- 1. reshape

def test_to_bars_reshapes_one_response():
    bars = contract_bars.to_bars(_payload(FIXTURE, oi=[7, 8, 9, 10, 11]))
    assert [b["t"] for b in bars] == ["09:15", "09:16", "09:17", "09:18",
                                      "09:19"]
    assert bars[0] == {"t": "09:15", "o": 10, "h": 11, "l": 9, "c": 10,
                       "v": 100, "oi": 7}
    assert bars[-1]["c"] == 50 and bars[-1]["oi"] == 11


def test_epoch_is_utc_and_ist_offset_is_applied():
    """The one real value checked on paper: 1784259900 is 2026-07-17
    03:45:00Z, and 03:45 + 05:30 = 09:15 IST -- the NSE open."""
    bars = contract_bars.to_bars(_payload([(1, 1, 1, 1, 1)],
                                          ts=[1784259900]))
    assert bars[0]["t"] == "09:15"


def test_ist_conversion_ignores_the_machine_timezone(monkeypatch):
    """A fixed offset, not localtime: the label must not follow the host."""
    monkeypatch.setenv("TZ", "America/New_York")
    bars = contract_bars.to_bars(_payload([(1, 1, 1, 1, 1)], ts=[_ts(374)]))
    assert bars[0]["t"] == "15:29"          # the last minute of the session


def test_to_bars_sorts_by_time():
    shuffled = [_ts(2), _ts(0), _ts(1)]
    bars = contract_bars.to_bars(_payload(FIXTURE[:3], ts=shuffled))
    assert [b["t"] for b in bars] == ["09:15", "09:16", "09:17"]
    assert [b["c"] for b in bars] == [20, 30, 10]


def test_ragged_arrays_truncate_to_shortest_and_record_the_drop():
    d = _payload(FIXTURE, oi=[7, 8, 9, 10, 11])
    d["volume"] = d["volume"][:3]           # the feed short-changed one array
    bars = contract_bars.to_bars(d)
    assert len(bars) == 3
    assert bars.dropped == 2                # recorded, not swallowed
    assert bars.lengths["volume"] == 3 and bars.lengths["close"] == 5


def test_ragged_arrays_are_never_zip_padded():
    """A short array must shorten the series, never contribute a zero bar."""
    d = _payload(FIXTURE)
    d["high"] = d["high"][:2]
    bars = contract_bars.to_bars(d)
    assert len(bars) == 2
    assert all(b is not None and b["h"] not in (0, None) for b in bars)


def test_clean_arrays_record_no_drop():
    bars = contract_bars.to_bars(_payload(FIXTURE))
    assert bars.dropped == 0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_value_makes_that_bar_none(bad):
    d = _payload(FIXTURE)
    d["close"][2] = bad
    bars = contract_bars.to_bars(d)
    assert bars[2] is None                  # None, never 0
    assert len(bars) == 5
    assert bars[1]["c"] == 20 and bars[3]["c"] == 40


def test_non_finite_open_interest_also_voids_the_bar():
    d = _payload(FIXTURE, oi=[7, float("nan"), 9, 10, 11])
    bars = contract_bars.to_bars(d)
    assert bars[1] is None


def test_absent_open_interest_is_none_not_zero():
    """No OI array at all is a missing INPUT, not a non-finite value: the
    price bar survives and oi reads unknown. 0 would be a lie."""
    bars = contract_bars.to_bars(_payload(FIXTURE))
    assert all(b["oi"] is None for b in bars)


def test_unparseable_timestamp_voids_the_bar():
    d = _payload(FIXTURE[:2], ts=[_ts(0), float("nan")])
    bars = contract_bars.to_bars(d)
    assert bars[0]["t"] == "09:15" and bars[1] is None


def test_to_bars_does_not_mutate_the_payload():
    d = _payload(FIXTURE, oi=[7, 8, 9, 10, 11])
    before = {k: list(v) for k, v in d.items()}
    contract_bars.to_bars(d)
    assert d == before


# ------------------------------------------------------------ 2. VWAP/sigma

def test_vwap_bands_match_the_hand_computed_fixture():
    banded = contract_bars.vwap_bands(contract_bars.to_bars(_payload(FIXTURE)))
    for i, b in enumerate(banded):
        assert b["vwap"] == pytest.approx(FIX_VWAP[i])
        assert b["u1"] == pytest.approx(FIX_VWAP[i] + FIX_SD[i])
        assert b["d1"] == pytest.approx(FIX_VWAP[i] - FIX_SD[i])
        assert b["u2"] == pytest.approx(FIX_VWAP[i] + 2 * FIX_SD[i])
        assert b["d2"] == pytest.approx(FIX_VWAP[i] - 2 * FIX_SD[i])
        assert b["u3"] == pytest.approx(FIX_VWAP[i] + 3 * FIX_SD[i])
        assert b["d3"] == pytest.approx(FIX_VWAP[i] - 3 * FIX_SD[i])


def test_vwap_is_anchored_at_the_first_bar():
    banded = contract_bars.vwap_bands(contract_bars.to_bars(_payload(FIXTURE)))
    assert banded[0]["vwap"] == pytest.approx(10.0)      # == bar 0's own TP
    assert banded[0]["u1"] == banded[0]["d1"] == banded[0]["vwap"]


def test_vwap_bands_keep_the_bar_fields():
    banded = contract_bars.vwap_bands(
        contract_bars.to_bars(_payload(FIXTURE, oi=[7, 8, 9, 10, 11])))
    assert banded[2]["t"] == "09:17" and banded[2]["c"] == 30
    assert banded[2]["oi"] == 9


def test_vwap_bands_do_not_mutate_the_input_bars():
    bars = contract_bars.to_bars(_payload(FIXTURE))
    contract_bars.vwap_bands(bars)
    assert set(bars[0]) == {"t", "o", "h", "l", "c", "v", "oi"}


def test_zero_volume_falls_back_to_close():
    """cv == 0 means there is no volume-weighted price yet; live.py's rule is
    vwap = close, sigma = 0. Reused verbatim."""
    bars = contract_bars.to_bars(_payload([(9, 11, 9, 10, 0)]))
    banded = contract_bars.vwap_bands(bars)
    assert banded[0]["vwap"] == 10 and banded[0]["u3"] == 10


def test_none_bars_produce_none_bands_and_contribute_nothing():
    d = _payload(FIXTURE)
    d["close"][1] = float("nan")            # bar 1 is unusable
    banded = contract_bars.vwap_bands(contract_bars.to_bars(d))
    assert banded[1] is None
    # bars 0, 2, 3, 4 must read exactly as if bar 1 had never been sent
    kept = contract_bars.vwap_bands(
        contract_bars.to_bars(_payload([FIXTURE[0]] + FIXTURE[2:])))
    live_bands = [b for b in banded if b is not None]
    for got, want in zip(live_bands, kept):
        assert got["vwap"] == pytest.approx(want["vwap"])
        assert got["u2"] == pytest.approx(want["u2"])


def test_vwap_bands_carry_the_drop_receipt_forward():
    d = _payload(FIXTURE)
    d["low"] = d["low"][:4]
    banded = contract_bars.vwap_bands(contract_bars.to_bars(d))
    assert banded.dropped == 1


def test_contract_bars_and_live_agree_to_the_last_bit():
    """The anti-drift lock (spec section 2). v1 and v2 must never disagree
    about the same band on the same data -- so there is ONE implementation.
    Re-inlining a second derivation in live.py fails here."""
    d = _payload([(24000, 24040, 23990, 24030, 1200),
                  (24030, 24075, 24025, 24060, 3400),
                  (24060, 24065, 23980, 23995, 5100),
                  (23995, 24010, 23940, 23950, 2750),
                  (23950, 24020, 23945, 24015, 6300)],
                 oi=[1796860.0, 1770145.0, 1734525.0, 1720000.0, 1705000.0])
    ours = contract_bars.vwap_bands(contract_bars.to_bars(d))
    theirs = live._bars(d, {})
    assert len(ours) == len(theirs)
    for a, b in zip(ours, theirs):
        assert a["t"] == b["T"]
        for lo, up in (("vwap", "VWAP"), ("u1", "U1"), ("d1", "D1"),
                       ("u2", "U2"), ("d2", "D2"), ("u3", "U3"), ("d3", "D3")):
            assert a[lo] == b[up], f"{lo} drifted from live.py at {a['t']}"


def test_backtest_bands_and_contract_bars_agree_to_the_last_bit():
    """The other half of the anti-drift lock.

    `backtest._bands` is a THIRD copy of the same VWAP/sigma recurrence, and
    the operator's whole validation story -- encode, then score, over the
    cached sessions -- runs through it. If it drifts from `vwap_sigma`, the
    tool scores signals against bands it no longer draws and nothing else in
    the suite would notice. This does not merge the copy (backtest.py is left
    alone deliberately); it locks the two together so an edit to one has to
    be an edit to both.
    """
    import backtest

    rows = [(24000, 24040, 23990, 24030, 1200),
            (24030, 24075, 24025, 24060, 3400),
            (24060, 24065, 23980, 23995, 5100),
            (23995, 24010, 23940, 23950, 2750),
            (23950, 24020, 23945, 24015, 6300)]
    ours = contract_bars.vwap_sigma([(h, l, c, v) for _o, h, l, c, v in rows])
    theirs = backtest._bands(
        [{"H": h, "L": l, "C": c, "V": v} for _o, h, l, c, v in rows], {})

    assert len(ours) == len(theirs) == len(rows)
    for i, (a, b) in enumerate(zip(ours, theirs)):
        for lo, up in (("vwap", "VWAP"), ("u1", "U1"), ("d1", "D1"),
                       ("u2", "U2"), ("d2", "D2"), ("u3", "U3"), ("d3", "D3")):
            assert a[lo] == b[up], f"{lo} drifted from backtest.py at bar {i}"


def test_backtest_shares_the_zero_volume_fallback_too():
    """With no volume there is no volume-weighted price, so VWAP falls back to
    the close and sigma is 0. It is a quirk, not a definition, which is exactly
    the kind of thing a re-implementation gets wrong."""
    import backtest

    rows = [(100, 102, 99, 101, 0), (101, 103, 100, 102, 0),
            (102, 105, 101, 104, 500)]
    ours = contract_bars.vwap_sigma([(h, l, c, v) for _o, h, l, c, v in rows])
    theirs = backtest._bands(
        [{"H": h, "L": l, "C": c, "V": v} for _o, h, l, c, v in rows], {})

    assert ours[0]["vwap"] == theirs[0]["VWAP"] == 101      # the close
    assert ours[0]["u3"] == theirs[0]["U3"] == 101          # sigma is 0
    for a, b in zip(ours, theirs):
        for lo, up in (("vwap", "VWAP"), ("u1", "U1"), ("d1", "D1"),
                       ("u2", "U2"), ("d2", "D2"), ("u3", "U3"), ("d3", "D3")):
            assert a[lo] == b[up]


# -------------------------------------------------------------- 3. causality

def test_bands_are_causal_under_truncation():
    """Bar i uses bars 0..i only, so replay is truncation, not recomputation."""
    rows = [(100 + i, 105 + i, 95 + i, 100 + (i % 7) - 3, 100 + 13 * i)
            for i in range(40)]
    bars = contract_bars.to_bars(_payload(rows))
    full = contract_bars.vwap_bands(bars)
    for k in (0, 1, 7, 23, 39):
        part = contract_bars.vwap_bands(bars[:k + 1])
        assert len(part) == k + 1
        for i in range(k + 1):
            for key in ("vwap", "u1", "d1", "u2", "d2", "u3", "d3"):
                assert full[i][key] == part[i][key]


def test_a_later_bar_cannot_move_an_earlier_band():
    rows = [(10, 11, 9, 10, 100), (20, 21, 19, 20, 100)]
    one = contract_bars.vwap_bands(contract_bars.to_bars(_payload(rows[:1])))
    two = contract_bars.vwap_bands(contract_bars.to_bars(_payload(rows)))
    assert one[0] == two[0]


# ----------------------------------------------------- 4. interval invariance

RAMP = [(100 + i, 100 + i + 4, 100 + i - 4, 100 + i + 1, 100 + 7 * i)
        for i in range(30)]


def _banded_ramp():
    return contract_bars.vwap_bands(contract_bars.to_bars(_payload(RAMP)))


def test_resample_aggregates_ohlcv():
    bars = contract_bars.to_bars(_payload(RAMP, oi=list(range(500, 530))))
    out = contract_bars.resample(bars, 3)
    assert len(out) == 10
    assert out[0]["t"] == "09:15"           # labelled by the bucket's open
    assert out[0]["o"] == bars[0]["o"]
    assert out[0]["c"] == bars[2]["c"]
    assert out[0]["h"] == max(b["h"] for b in bars[:3])
    assert out[0]["l"] == min(b["l"] for b in bars[:3])
    assert out[0]["v"] == sum(b["v"] for b in bars[:3])
    assert out[0]["oi"] == bars[2]["oi"]    # OI is a level: take the last
    assert out[1]["t"] == "09:18"


@pytest.mark.parametrize("minutes", [2, 3, 5, 15])
def test_interval_invariance_bands_are_sampled_not_recomputed(minutes):
    """Spec section 2: VWAP is computed on the 1-minute series and then
    SAMPLED. Changing interval must not move a band by a paisa."""
    one = _banded_ramp()
    agg = contract_bars.resample(one, minutes)
    for j, bucket in enumerate(agg):
        last = one[min(minutes * (j + 1), len(one)) - 1]
        for key in ("vwap", "u1", "d1", "u2", "d2", "u3", "d3"):
            assert bucket[key] == last[key], f"{key} moved at {minutes}m"


def test_one_minute_resample_is_the_identity_on_bands():
    one = _banded_ramp()
    same = contract_bars.resample(one, 1)
    assert [b["vwap"] for b in same] == [b["vwap"] for b in one]
    assert [b["c"] for b in same] == [b["c"] for b in one]


def test_recomputing_on_aggregated_bars_would_have_moved_the_bands():
    """The guard behind the invariance test: proves sampling is doing real
    work. Recomputing the VWAP on 3-minute bars gives DIFFERENT numbers, so a
    future 'simplification' to recompute cannot pass by coincidence."""
    one = _banded_ramp()
    sampled = contract_bars.resample(one, 3)
    recomputed = contract_bars.vwap_bands(
        contract_bars.resample(contract_bars.to_bars(_payload(RAMP)), 3))
    assert sampled[-1]["u2"] != pytest.approx(recomputed[-1]["u2"])


def test_resample_buckets_are_time_anchored_across_a_gap():
    """A minute the feed never sent must not shift the bucket boundaries."""
    ts = [_ts(i) for i in range(6) if i != 3]       # 09:18 missing
    rows = [RAMP[i] for i in range(6) if i != 3]
    out = contract_bars.resample(contract_bars.to_bars(_payload(rows, ts=ts)),
                                 3)
    assert [b["t"] for b in out] == ["09:15", "09:19"]
    assert out[1]["v"] == RAMP[4][4] + RAMP[5][4]   # 09:18 contributed nothing


def test_resample_skips_none_bars_without_inventing_one():
    d = _payload(RAMP[:6])
    d["close"][1] = float("nan")
    out = contract_bars.resample(contract_bars.to_bars(d), 3)
    assert len(out) == 2
    assert out[0]["v"] == RAMP[0][4] + RAMP[2][4]


def test_resample_carries_the_drop_receipt_forward():
    d = _payload(RAMP)
    d["open"] = d["open"][:27]
    out = contract_bars.resample(contract_bars.to_bars(d), 3)
    assert out.dropped == 3


@pytest.mark.parametrize("minutes", [0, -3, 2.5, "3"])
def test_resample_rejects_a_nonsense_interval(minutes):
    with pytest.raises((ValueError, TypeError)):
        contract_bars.resample(_banded_ramp(), minutes)


# --------------------------------------------------------------- 5. emptiness

@pytest.mark.parametrize("payload", [
    {}, {"close": []}, {"close": [], "open": [], "high": [], "low": [],
                        "volume": [], "timestamp": []},
    {"close": [1.0]},                       # every other array missing
])
def test_empty_or_unusable_payload_returns_empty_never_throws(payload):
    bars = contract_bars.to_bars(payload)
    assert list(bars) == []
    assert contract_bars.vwap_bands(bars) == []
    assert contract_bars.resample(bars, 3) == []


def test_a_wholly_void_series_yields_no_bars_but_records_them():
    d = _payload(FIXTURE[:2])
    d["close"] = [float("nan"), float("nan")]
    bars = contract_bars.to_bars(d)
    assert bars == [None, None]             # positions kept, values not faked
    assert contract_bars.vwap_bands(bars) == [None, None]
    assert list(contract_bars.resample(bars, 3)) == []
