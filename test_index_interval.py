"""The index tape's BAR INTERVAL -- resampling, and what it must not move.

Until 2026-08-11 `live.build_payload` published 1-MINUTE bars and ran every
derived layer on them, while `context/research-findings.md` §5c's 68.4% (n=19)
was measured on 3-MINUTE bars with `RUN_WINDOW` = 10 candles = 30 minutes. Live
was therefore running a rule nobody had scored: the same constant meant ten
minutes instead of thirty, and the arm/trigger tests read 1-minute lows and
closes. Family 6 below demonstrates that difference on one fixture.

Fixtures use the COMPOSITE index shape `engine.session_json` emits -- a `t` on
the row and a fut/ce/pe leg under it -- because that is the shape
`contract_bars.resample_index` exists for; the flat shape has its own coverage
in `test_contract_bars.py`. VWAP is 100 and sigma is 5, so d3 is 85 and every
number below can be read at a glance.

Families:
  1. One bucketing  -- the flat and composite resamplers cannot disagree.
  2. Sampling       -- bands are COPIED off the bucket's last 1-minute bar.
  3. Honesty        -- no invented bucket, no invented leg, no invented bar.
  4. Alignment      -- every derived layer stays 1:1 with the published bars.
  5. Remapping      -- every carried index still points at the same real bar.
  6. The window     -- RUN_WINDOW = 10 PUBLISHED candles, which is the bug.
  7. Wiring         -- clamp, publish, and one build serving every interval.
"""

import pytest

import band_rotation
import contract_bars
import live
import server
import squeeze_score

VWAP = 100.0
SD = 5.0
D3 = VWAP - 3 * SD          # 85.0

BANDS = {"vwap": VWAP, "u1": VWAP + SD, "d1": VWAP - SD,
         "u2": VWAP + 2 * SD, "d2": VWAP - 2 * SD,
         "u3": VWAP + 3 * SD, "d3": D3}

OPEN = 9 * 60 + 15          # 09:15, the NSE open


def _hhmm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def _leg(low, high, close, i, **over):
    """One leg of one bar. `z` stands in for the engine's per-minute reads:
    like a band it is computed on the 1-minute series and can only be sampled,
    and it is made unique per bar so a copy can be told from a coincidence."""
    d = dict(BANDS)
    d.update({"o": close, "h": high, "l": low, "c": close,
              "v": 100 + i, "oi": 1000 + i, "z": round(i / 10.0, 2)})
    d.update(over)
    return d


def _row(i, low=88.0, high=94.0, close=91.0, minute=None, **over):
    """One composite index row, `i` minutes into the session."""
    m = OPEN + i if minute is None else minute
    row = {"t": _hhmm(m),
           "fut": _leg(low, high, close, i),
           # The legs are premiums, so they get their own (smaller) numbers --
           # a test that passed because every leg held the same values would
           # not notice the legs being folded into one another.
           "ce": _leg(low / 10, high / 10, close / 10, i),
           "pe": _leg(low / 10, high / 10, close / 10, i)}
    row.update(over)
    return row


def _session(rows, events=()):
    """The `days[0]` shape `engine.session_json` emits, at one minute."""
    return {"day": "Aug 07 LIVE", "strike": 24500.0,
            "bars": list(rows), "events": [dict(e) for e in events]}


def _inert(n):
    """`n` minutes that can do nothing: never reach d3 (85), never VWAP."""
    return [_row(i) for i in range(n)]


# --------------------------------------------------------- 1. one bucketing

@pytest.mark.parametrize("minutes", [1, 3, 5, 15])
def test_the_two_resamplers_agree_about_where_a_candle_starts(minutes):
    """`resample` (flat contract bars) and `resample_index` (the composite row)
    share `_buckets`. If either ever grew its own boundary rule they would
    disagree about which minutes are one candle -- silently, with the index
    tape and the option tape both looking right on their own."""
    rows = _inert(47)
    flat = [{"t": r["t"], "o": 1.0, "h": 1.0, "l": 1.0, "c": 1.0, "v": 1, "oi": 1}
            for r in rows]
    assert ([b["t"] for b in contract_bars.resample_index(rows, minutes)]
            == [b["t"] for b in contract_bars.resample(flat, minutes)])


def test_a_bucket_is_labelled_by_its_opening_minute():
    out = contract_bars.resample_index(_inert(9), 3)
    assert [b["t"] for b in out] == ["09:15", "09:18", "09:21"]


@pytest.mark.parametrize("minutes", [0, -3, 2.5, "3", True])
def test_resample_index_rejects_a_nonsense_interval(minutes):
    with pytest.raises((ValueError, TypeError)):
        list(contract_bars.resample_index(_inert(6), minutes))


# ------------------------------------------------------------- 2. sampling

@pytest.mark.parametrize("minutes", [1, 3, 5, 15])
@pytest.mark.parametrize("leg", ["fut", "ce", "pe"])
def test_bands_are_copied_off_the_last_minute_never_recomputed(minutes, leg):
    """The interval invariance, structurally: `resample_index` reads a band, it
    does not derive one. Changing interval cannot move a band by a paisa."""
    rows = [_row(i, close=90.0 + i, **{}) for i in range(30)]
    # give each minute its own bands so "copied from the last one" is falsifiable
    for i, r in enumerate(rows):
        for k in contract_bars.BAND_KEYS:
            for lg in ("fut", "ce", "pe"):
                r[lg][k] = BANDS[k] + i / 100.0
    out = contract_bars.resample_index(rows, minutes)
    for j, bucket in enumerate(out):
        last = rows[min(minutes * (j + 1), len(rows)) - 1]
        for k in contract_bars.BAND_KEYS:
            assert bucket[leg][k] == last[leg][k], f"{k} moved at {minutes}m"
        # the engine's other per-minute reads take the same rule
        assert bucket[leg]["z"] == last[leg]["z"]


def test_recomputing_the_bands_on_aggregated_bars_would_have_moved_them():
    """The guard behind the test above -- it proves sampling does real work.
    Mirrors `test_contract_bars.py`'s guard on the flat path."""
    rows = _inert(30)
    for i, r in enumerate(rows):
        r["fut"]["d3"] = D3 + i          # a band that visibly walks
    out = contract_bars.resample_index(rows, 3)
    assert [b["fut"]["d3"] for b in out] == [D3 + i for i in (2, 5, 8, 11, 14,
                                                              17, 20, 23, 26, 29)]
    # the bucket's OWN low, if a band were re-derived from it, is a different
    # number entirely -- so a future "simplification" cannot pass by accident
    assert out[0]["fut"]["d3"] != out[0]["fut"]["l"]


def test_ohlcv_is_aggregated_and_oi_is_a_level():
    rows = [_row(0, low=88.0, high=94.0, close=91.0),
            _row(1, low=80.0, high=93.0, close=90.0),
            _row(2, low=89.0, high=99.0, close=97.0)]
    b = contract_bars.resample_index(rows, 3)[0]["fut"]
    assert (b["o"], b["h"], b["l"], b["c"]) == (91.0, 99.0, 80.0, 97.0)
    assert b["v"] == 100 + 101 + 102
    assert b["oi"] == 1002                       # a level: the bucket's last


# -------------------------------------------------------------- 3. honesty

def test_a_minute_the_feed_never_sent_leaves_a_hole_not_an_invented_bucket():
    """Buckets are anchored on the first bar's clock, so a gap must not shift
    every later boundary -- and a bucket with no real bar is not created."""
    rows = [_row(i) for i in range(9) if i not in (3, 4, 5)]   # 09:18-09:20 gone
    out = contract_bars.resample_index(rows, 3)
    assert [b["t"] for b in out] == ["09:15", "09:21"]
    assert len(out) == 2                          # no empty 09:18 bucket


def test_a_leg_absent_for_the_whole_bucket_stays_none():
    rows = _inert(3)
    for r in rows:
        r["ce"] = None
    b = contract_bars.resample_index(rows, 3)[0]
    assert b["ce"] is None
    assert b["fut"] is not None and b["pe"] is not None


def test_a_leg_that_printed_for_part_of_the_bucket_folds_from_what_it_printed():
    """`session_json` emits every FUT bar and nulls a leg that did not print.
    The bucket is then folded from the minutes that ARE there -- real bars --
    rather than being voided or padded with a made-up one."""
    rows = _inert(3)
    rows[1]["ce"] = None                          # 09:16 did not print
    b = contract_bars.resample_index(rows, 3)[0]["ce"]
    assert b["o"] == rows[0]["ce"]["c"]           # opened on the minute it did print
    assert b["c"] == rows[2]["ce"]["c"]
    assert b["v"] == rows[0]["ce"]["v"] + rows[2]["ce"]["v"]


def test_a_row_level_block_takes_the_last_real_read_in_the_bucket():
    rows = _inert(3)
    rows[0]["ctx"] = {"verdict": "WAIT"}
    rows[1]["ctx"] = {"verdict": "GO"}            # 09:17 carried none
    b = contract_bars.resample_index(rows, 3)[0]
    assert b["ctx"] == {"verdict": "GO"}


def test_empty_or_unusable_input_returns_empty_and_never_throws():
    assert list(contract_bars.resample_index([], 3)) == []
    assert list(contract_bars.resample_index([None, 3, "x"], 3)) == []
    assert list(contract_bars.resample_index([{"fut": {}}], 3)) == []   # no clock


# ------------------------------------------------------------ 4. alignment

_PER_BAR = ("rotation", "run_state", "rotation_run",
            "run_state_sell", "rotation_run_sell")


@pytest.mark.parametrize("minutes", live.INTERVALS)
def test_every_derived_layer_stays_one_to_one_with_the_published_bars(minutes):
    """The whole reason the layers moved into `_at_interval`: a layer computed
    on the 1-minute series and then aggregated would leave every marker on a
    bar index that no longer exists."""
    out = live._at_interval(_session(_inert(60)), minutes)
    n = len(out["bars"])
    assert n == len(contract_bars.resample_index(_inert(60), minutes))
    for k in _PER_BAR:
        assert len(out[k]) == n, k


@pytest.mark.parametrize("minutes", live.INTERVALS)
def test_the_published_bars_are_the_resampled_ones(minutes):
    out = live._at_interval(_session(_inert(60)), minutes)
    expected = 60 // minutes + (1 if 60 % minutes else 0)
    assert len(out["bars"]) == expected


def test_at_interval_does_not_mutate_the_session_it_was_given():
    """One build serves every interval, so the 1-minute session is shared."""
    day = _session(_inert(30))
    before = len(day["bars"])
    live._at_interval(day, 3)
    live._at_interval(day, 15)
    assert len(day["bars"]) == before
    assert "run_state" not in day and "structures" not in day


# ------------------------------------------------------------ 5. remapping

@pytest.mark.parametrize("minutes", live.INTERVALS)
def test_a_structure_is_born_on_a_bar_that_exists(minutes):
    out = live._at_interval(_session(_ramp(60)), minutes)
    n = len(out["bars"])
    for s in out["structures"]:
        assert 0 <= s["i0"] < n and 0 <= s["i1"] < n and 0 <= s["born"] < n


@pytest.mark.parametrize("minutes", live.INTERVALS)
def test_every_carried_index_addresses_its_own_bar(minutes):
    """A record's `i` and its `t` must name the SAME bar. This is what would
    have broken had the layers been computed before the resample."""
    out = live._at_interval(_session(_ramp(60)), minutes)
    bars = out["bars"]
    for k in ("rotation", "run_state", "run_state_sell"):
        for i, rec in enumerate(out[k]):
            if rec is None:
                continue
            assert rec["i"] == i, k
            assert rec["t"] == bars[i]["t"], k
    for st in out["run_state"]:
        if st["ref_i"] is not None:
            assert 0 <= st["ref_i"] < len(bars)


def test_an_event_is_moved_onto_the_candle_that_now_contains_its_minute():
    """Events carry a CLOCK, not an index, and the UI keys them by `bar.t`
    (`buildNarration`). At 3 minutes only every third minute is a bar label, so
    an unremapped event would silently vanish from two bars in three."""
    day = _session(_inert(9), events=[{"t": "09:16", "kind": "SQUEEZE", "msg": "x"},
                                      {"t": "09:21", "kind": "GAP", "msg": "y"}])
    out = live._at_interval(day, 3)
    labels = {b["t"] for b in out["bars"]}
    assert [e["t"] for e in out["events"]] == ["09:15", "09:21"]
    assert all(e["t"] in labels for e in out["events"])
    # the minute the engine actually observed is kept, never destroyed
    assert out["events"][0]["t_min"] == "09:16"
    assert "t_min" not in out["events"][1]        # it did not move


def test_an_event_whose_minute_has_no_bar_is_left_exactly_as_it_is():
    day = _session(_inert(6), events=[{"t": "15:29", "kind": "CARRY", "msg": "z"}])
    out = live._at_interval(day, 3)
    assert out["events"] == [{"t": "15:29", "kind": "CARRY", "msg": "z"}]


def test_one_minute_leaves_every_event_alone():
    evs = [{"t": "09:16", "kind": "SQUEEZE", "msg": "x"}]
    out = live._at_interval(_session(_inert(9), events=evs), 1)
    assert out["events"] == evs


# ----------------------------------------------------------- 6. the window

def _ramp(n):
    """`n` inert minutes with a slow drift, so structure.py has pivots to find
    and the rotation layers have something other than a flat line to read."""
    out = []
    for i in range(n):
        d = (i % 7) - 3
        out.append(_row(i, low=88.0 + d, high=94.0 + d, close=91.0 + d))
    return out


def _touch_then_break(gap_buckets):
    """A d3 touch in the 3-minute bucket at 09:30, then a close above that
    bucket's high `gap_buckets` 3-minute candles later. Everything else is
    inert: no lower low (so no re-arm) and no earlier close above 94."""
    rows = _inert(60)
    rows[15] = _row(15, low=84.5, high=94.0, close=91.0)      # 09:30, bucket 5
    brk = 3 * (5 + gap_buckets) + 2                           # the bucket's CLOSE
    rows[brk] = _row(brk, low=88.0, high=96.0, close=95.0)
    return rows


def test_run_window_counts_ten_PUBLISHED_candles():
    """§5c's window is 10 candles. At the scored 3 minutes that is 30 minutes,
    and the bar exactly on the edge still counts."""
    out = live._at_interval(_session(_touch_then_break(10)), 3)
    fired = [s["entry"] for s in out["run_state"] if s["entry"]]
    assert len(fired) == 1
    assert fired[0]["t"] == "10:00"                # 09:30 + 10 candles


def test_one_candle_past_the_window_expires():
    out = live._at_interval(_session(_touch_then_break(11)), 3)
    assert [s["entry"] for s in out["run_state"] if s["entry"]] == []


def test_the_same_session_scores_differently_at_one_minute_than_at_three():
    """THE BUG, on one fixture. `RUN_WINDOW` = 10 is counted in BARS, so on the
    1-minute tape live published it meant ten MINUTES: the reference expired
    long before the break that §5c's 30-minute window catches. Live was not
    running the rule that was scored."""
    day = _session(_touch_then_break(10))
    at3 = [s["entry"] for s in live._at_interval(day, 3)["run_state"] if s["entry"]]
    at1 = [s["entry"] for s in live._at_interval(day, 1)["run_state"] if s["entry"]]
    assert len(at3) == 1 and at1 == []


def test_the_scored_interval_is_one_number_not_two():
    """The backtest that produced 68.4% and the tape the operator reads must be
    the same candles, or the number describes something nobody is looking at."""
    assert squeeze_score.INTERVAL == band_rotation.SCORED_INTERVAL == 3
    assert live.DEFAULT_INTERVAL == band_rotation.SCORED_INTERVAL


# -------------------------------------------------------------- 7. wiring

@pytest.mark.parametrize("raw,want", [
    ("1", 1), ("3", 3), ("5", 5), ("15", 15), (5, 5),
    (None, 3), ("", 3), ("abc", 3), ("2", 3), ("0", 3), ("-3", 3),
    ("999", 3), (2.7, 3), ([], 3),
])
def test_clamp_interval_never_raises_and_never_invents_an_interval(raw, want):
    assert live.clamp_interval(raw) == want


def test_the_payload_states_which_interval_it_is():
    """A screen that has to guess which candles it is drawing cannot honestly
    say whether the scored number applies to them."""
    base = {"error": None, "built_at": 1.0, "day": _session(_inert(30)),
            "head": {"index": "NIFTY", "strike": 24500.0}}
    import json
    for n in live.INTERVALS:
        d = json.loads(live.derive_payload(base, n))
        assert d["interval"] == n
        assert len(d["days"][0]["bars"]) == len(
            contract_bars.resample_index(base["day"]["bars"], n))


def test_one_build_serves_every_interval_without_being_consumed():
    base = {"error": None, "built_at": 1.0, "day": _session(_ramp(45)),
            "head": {"index": "NIFTY"}}
    import json
    first = json.loads(live.derive_payload(base, 3))
    json.loads(live.derive_payload(base, 15))
    again = json.loads(live.derive_payload(base, 3))
    assert first == again                          # deriving is not destructive


def test_a_failed_build_serves_its_own_error_at_every_interval():
    base = {"error": b'{"live_error":"no bars yet"}'}
    for n in live.INTERVALS:
        assert live.derive_payload(base, n) == base["error"]


# ------------------------------------------------- 8. the per-interval cache

def _counting(monkeypatch):
    calls = []

    def fake(base, interval):
        calls.append(interval)
        return f'{{"interval":{interval}}}'.encode()

    monkeypatch.setattr(live, "derive_payload", fake)
    return calls


def test_a_refresh_is_paid_for_once_and_derived_per_interval(monkeypatch):
    """A cycle costs a token, three downloads and an engine run. Rebuilding all
    of that per interval would triple the network load of a tape the operator
    flicks between 1m and 3m."""
    calls = _counting(monkeypatch)
    box = {"session": {"day": None}, "stamp": 1.0, "by_interval": {}}
    assert server.payload_at(box, 3) == b'{"interval":3}'
    assert server.payload_at(box, 3) == b'{"interval":3}'      # cached
    assert server.payload_at(box, 15) == b'{"interval":15}'
    assert calls == [3, 15]


def test_a_new_build_invalidates_every_interval_it_replaces(monkeypatch):
    calls = _counting(monkeypatch)
    box = {"session": {"day": None}, "stamp": 1.0, "by_interval": {}}
    server.payload_at(box, 3)
    box["stamp"] = 2.0                       # the poller landed a fresh build
    server.payload_at(box, 3)
    assert calls == [3, 3]


def test_the_cache_holds_at_most_one_payload_per_supported_interval(monkeypatch):
    _counting(monkeypatch)
    box = {"session": {"day": None}, "stamp": 1.0, "by_interval": {}}
    for _ in range(3):
        for n in live.INTERVALS:
            server.payload_at(box, n)
        box["stamp"] += 1
    assert len(box["by_interval"]) == len(live.INTERVALS)


def test_a_box_with_no_session_serves_its_own_bytes():
    """Starting up, or a build that failed. An interval cannot make a tape
    exist, so the box's own sentence goes out unchanged."""
    box = {"payload": b'{"live_error":"starting up"}', "session": None}
    for n in live.INTERVALS:
        assert server.payload_at(box, n) == box["payload"]
    assert server.payload_at(b"raw replay bytes", 3) == b"raw replay bytes"
