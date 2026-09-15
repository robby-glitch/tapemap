"""A rebuilt morning must never be mistaken for one that was watched.

`vpin.from_bars` is pure, so the bucket arithmetic is pinned directly. What the
server does with it is pinned in `test_day_state.py`'s isolation cases and here
in the tagging ones -- and the rule that matters more than any of the numbers
is the LAST test in this file: nothing reconstructed may reach
`data/vpin_log.jsonl`, which is the promotion evidence for a shadow module on a
declared 30-session kill clock. A row written there is indistinguishable from
an observation the moment it lands.
"""

import json

import vpin


def _bars(rows):
    """`(stamp, close, volume)` oldest first, the shape
    `upstox_adapter.candles_to_arrays` already produces."""
    return [(t, c, v) for t, c, v in rows]


# ---- the bucket arithmetic --------------------------------------------------

def test_a_bucket_closes_at_bucket_v_and_not_before():
    """Volume time, not clock time: the boundary is BUCKET_V units, however
    many minutes that takes."""
    out = vpin.from_bars(_bars([("09:15", 100.0, 30_000),
                                ("09:16", 101.0, 20_000)]), bucket_v=60_000)
    assert out == []                       # 50k of a 60k bucket: not yet
    out = vpin.from_bars(_bars([("09:15", 100.0, 30_000),
                                ("09:16", 101.0, 20_000),
                                ("09:17", 102.0, 10_000)]), bucket_v=60_000)
    assert len(out) == 1 and out[0]["bucket"] == 1


def test_the_first_bars_volume_is_counted_not_swallowed_as_a_baseline():
    """`Gauge.on_frame` treats its first frame as the vtt baseline, so feeding
    cumulative volume straight in would silently discard 09:15 -- the heaviest
    minute of most sessions. from_bars primes at zero instead.

    60k of volume in the first bar alone must therefore close a 60k bucket."""
    out = vpin.from_bars(_bars([("09:15", 100.0, 60_000)]), bucket_v=60_000)
    assert len(out) == 1


def test_the_first_bar_is_neutral_because_it_has_no_previous_close():
    """BVC signs a bar by its close-to-close direction, and bar one has no
    previous close. Half/half is the same honest neutral the live path applies
    to volume with no sign yet -- NOT a direction invented from the bar body.
    imb is therefore 0."""
    out = vpin.from_bars(_bars([("09:15", 100.0, 60_000)]), bucket_v=60_000)
    assert out[0]["imb"] == 0.0
    assert out[0]["buy"] == out[0]["sell"] == 30_000.0


def test_a_rising_close_signs_the_whole_bar_buy():
    """The documented ceiling, asserted so nobody 'fixes' it into something
    subtler without noticing: one sign for the whole minute."""
    out = vpin.from_bars(_bars([("09:15", 100.0, 10_000),   # neutral, 10k
                                ("09:16", 101.0, 50_000)]),  # buy, 50k
                         bucket_v=60_000)
    assert out[0]["buy"] == 55_000.0 and out[0]["sell"] == 5_000.0
    assert out[0]["imb"] == round(50_000 / 60_000, 4)


def test_a_falling_close_signs_the_whole_bar_sell():
    out = vpin.from_bars(_bars([("09:15", 100.0, 10_000),
                                ("09:16", 99.0, 50_000)]), bucket_v=60_000)
    assert out[0]["sell"] == 55_000.0 and out[0]["buy"] == 5_000.0


def test_a_bar_with_no_close_or_no_volume_is_a_gap_not_a_zero():
    """A dropped candle is missing data. Counting it as zero volume would
    quietly stretch a bucket across a hole in the session."""
    out = vpin.from_bars(_bars([("09:15", None, 60_000),
                                ("09:16", 100.0, None),
                                ("09:17", 101.0, 60_000)]), bucket_v=60_000)
    assert len(out) == 1


def test_the_stamp_of_the_bar_that_closed_the_bucket_is_carried():
    out = vpin.from_bars(_bars([("09:15", 100.0, 30_000),
                                ("10:47", 101.0, 30_000)]), bucket_v=60_000)
    assert out[0]["at"] == "10:47"


# ---- the tag ----------------------------------------------------------------

def test_every_reconstructed_row_says_it_is_reconstructed():
    """The non-negotiable: backfilled data is distinguishable from
    live-observed data end to end. It starts here."""
    out = vpin.from_bars(_bars([("09:15", 100.0, 120_000)]), bucket_v=60_000)
    assert out and all(r["backfill"] is True for r in out)
    assert all(r["src"] == vpin.BACKFILL_SRC for r in out)


def test_the_live_path_carries_no_backfill_key_at_all():
    """Absence means observed. If the live event ever grew a `backfill` key
    the two populations would start to look alike, so pin it."""
    g = vpin.Gauge(bucket_v=1000)
    g.on_frame(100.0, 0.0, "09:15")
    evs = g.on_frame(101.0, 1000.0, "09:16")
    assert evs and "backfill" not in evs[0] and "src" not in evs[0]


def test_a_backfilled_reading_is_smoother_than_the_live_one_on_the_same_tape():
    """The ceiling, measured rather than asserted in prose. The same 60k of
    volume that arrived as a two-sided fight inside one minute reads imb 0 to
    the live path and imb 1.0 to BVC -- one sign for the whole bar. This is
    why the two populations are never pooled and why seeding the live gauge
    from them is an open decision rather than an obvious win."""
    bvc = vpin.from_bars(_bars([("09:15", 100.0, 10_000),
                                ("09:16", 101.0, 50_000)]), bucket_v=60_000)
    live = vpin.Gauge(bucket_v=60_000)
    live.on_frame(100.0, 0.0, "09:15")
    for ltp, cum in ((101.0, 10_000), (100.0, 30_000), (101.0, 60_000)):
        evs = live.on_frame(ltp, cum, "09:16")
    assert evs and evs[0]["imb"] < bvc[0]["imb"]


# ---- the forward record it must never touch ---------------------------------

def test_the_backfill_writer_and_the_forward_log_are_two_different_files():
    """`data/vpin_log.jsonl` is the 30-session promotion record. A
    reconstruction written into it could never be told apart from an
    observation afterwards, and the kill clock would be counting rows the
    socket never saw."""
    import server
    assert server.VPIN_LOG != server.VPIN_BACKFILL_LOG
    assert "vpin_log.jsonl" in server.VPIN_LOG
    assert "vpin_backfill.jsonl" in server.VPIN_BACKFILL_LOG


def test_the_gauge_seeding_decision_is_off_and_is_named(tmp_path):
    """An OPEN OPERATOR DECISION, parked OFF behind a constant she can find.
    The test pins the default, not the choice -- flipping it is hers, and this
    failing is the reminder to record that she made it."""
    import server
    assert server.SEED_LIVE_GAUGE_FROM_BACKFILL is False


def _bf(at):
    return {"at": at, "imb": 0.2, "vpin": 0.2, "pct": None,
            "backfill": True, "src": vpin.BACKFILL_SRC}


def _live(at):
    return {"at": at, "imb": 0.4, "vpin": 0.4, "pct": 0.7}


def test_the_backfilled_series_stops_where_the_live_record_starts():
    """An observation always beats a reconstruction, and volume-time buckets
    from the two paths do not align -- so they are concatenated at the
    boundary, never overlapped, summed or ranked together."""
    import server
    out = server._vpin_series([_live("11:07")],
                              [_bf("09:47"), _bf("10:30"), _bf("11:40")])
    assert [r["t"] for r in out] == ["09:47", "10:30", "11:07"]
    assert [r["backfill"] for r in out] == [True, True, False]


def test_with_no_live_buckets_the_whole_rebuilt_morning_is_served():
    import server
    out = server._vpin_series([], [_bf("09:47"), _bf("11:40")])
    assert [r["t"] for r in out] == ["09:47", "11:40"]
    assert all(r["backfill"] for r in out)


def test_a_live_row_names_its_own_source_too():
    """Not just "not backfilled" -- the row says what it IS, so a reader never
    has to infer a population from a missing key."""
    import server
    (row,) = server._vpin_series([_live("09:19")], [])
    assert row["backfill"] is False and row["src"] == "live_frames"


def test_an_unreadable_forward_log_is_not_an_empty_day(tmp_path, monkeypatch):
    """`series: null` (could not check) and `series: []` (checked, no buckets
    yet) are two different sentences and must not collapse -- house rule 6.
    The backfill file existing does not turn the first into the second."""
    import server
    assert server._read_jsonl(str(tmp_path / "nope.jsonl")) == []
    # the None case is produced by the endpoint, not the helper: the helper is
    # only ever handed a real list, and this pins that contract.
    assert server._vpin_series([], []) == []
