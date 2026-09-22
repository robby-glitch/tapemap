"""The VPIN gauge, checked on synthetic tapes where the answer is arithmetic.

The cases that matter: a perfectly one-sided bucket reads 1.0 and a perfectly
alternating one reads ~0, the tick rule carries its sign through flat prints,
a vtt reset contributes NOTHING (never negative volume), and one big delta
spilling across bucket boundaries closes every bucket it fills.
"""
import vpin


def _gauge(v=100, window=50):
    return vpin.Gauge(bucket_v=v, window=window)


def test_one_sided_bucket_is_max_toxic():
    g = _gauge(v=100)
    g.on_frame(100.0, 0)              # baseline frame
    g.on_frame(101.0, 0)              # uptick -> sign = buy
    evs = g.on_frame(101.0, 100)      # 100 units, all buy -> bucket closes
    assert len(evs) == 1
    assert evs[0]["imb"] == 1.0 and evs[0]["vpin"] == 1.0
    assert evs[0]["buy"] == 100.0 and evs[0]["sell"] == 0.0


def test_balanced_flow_is_near_zero():
    g = _gauge(v=100)
    g.on_frame(100.0, 0)
    evs = []
    for i in range(1, 5):             # up 25, down 25, up 25, down 25
        px = 100.0 + (1 if i % 2 else -1)
        evs = g.on_frame(px, i * 25)
    assert len(evs) == 1
    assert evs[0]["imb"] == 0.0


def test_tick_rule_carries_sign_through_flat_prints():
    g = _gauge(v=100)
    g.on_frame(100.0, 0)
    g.on_frame(100.5, 50)             # uptick: 50 buy
    evs = g.on_frame(100.5, 100)      # flat: carries buy -> closes one-sided
    assert evs and evs[0]["imb"] == 1.0


def test_unsigned_volume_splits_neutral():
    g = _gauge(v=100)
    g.on_frame(100.0, 0)              # baseline; no price change ever
    evs = g.on_frame(100.0, 100)      # sign unknown -> 50/50
    assert evs and evs[0]["imb"] == 0.0
    assert evs[0]["buy"] == 50.0 and evs[0]["sell"] == 50.0


def test_vtt_reset_contributes_nothing():
    g = _gauge(v=100)
    g.on_frame(100.0, 0)
    g.on_frame(101.0, 60)             # 60 in
    assert g.on_frame(101.0, 10) == []   # reset: re-arm, no volume
    assert g.resets == 1
    evs = g.on_frame(101.0, 50)       # 40 more -> bucket closes at 100
    assert evs and g.buckets == 1


def test_big_delta_spills_across_buckets():
    g = _gauge(v=100)
    g.on_frame(100.0, 0)
    g.on_frame(101.0, 0)
    evs = g.on_frame(101.0, 250)      # 2.5 buckets in one delta
    assert len(evs) == 2 and g.buckets == 2
    assert g.state()["fill"] == 0.5   # half a bucket left in progress


def test_vpin_is_rolling_mean_and_state_reports_it():
    g = _gauge(v=100, window=2)
    g.on_frame(100.0, 0)
    g.on_frame(101.0, 100)            # bucket 1: imb 1.0
    g.on_frame(101.0, 150)            # 50 buy...
    g.on_frame(100.0, 200)            # ...50 sell -> bucket 2: imb 0.0
    g.on_frame(101.0, 300)            # bucket 3: imb 1.0; window 2 -> (0+1)/2
    s = g.state()
    assert s["vpin"] == 0.5 and s["buckets"] == 3
    assert s["shadow"] is True and s["tag"] == "[I]"


def test_no_reading_before_first_bucket():
    g = _gauge()
    s = g.state()
    assert s["vpin"] is None and s["pct"] is None and s["buckets"] == 0


def test_pct_withheld_below_min_hist():
    g = _gauge(v=100)
    g.on_frame(100.0, 0)
    g.on_frame(101.0, 0)
    evs = g.on_frame(101.0, 100 * vpin.MIN_HIST)      # MIN_HIST buckets at once
    assert all(e["pct"] is None for e in evs[:-1])
    assert evs[-1]["pct"] is not None                 # trusted from MIN_HIST on


def test_seed_replays_today_after_a_restart():
    """Today's own rows rebuild the window and bucket count."""
    g = vpin.Gauge(bucket_v=100)
    rows = [{"day": "2026-08-25", "at": "09:20", "imb": 0.2, "vpin": 0.2},
            {"day": "2026-08-25", "at": "09:25", "imb": 0.4, "vpin": 0.3}]
    r = g.seed(rows, today="2026-08-25")
    assert r == {"today_buckets": 2}
    assert g.buckets == 2
    assert g.state()["vpin"] == 0.3   # mean of the replayed window


def test_seed_ignores_prior_sessions():
    """The operator's rejection, 2026-08-25: expiry character and the vol
    regime reshape the distribution daily, so yesterday's buckets must not
    rank today's. An expiry day's log full of imb-1.0 buckets contributes
    NOTHING -- the percentile stays mute until today earns MIN_HIST."""
    g = vpin.Gauge(bucket_v=100)
    rows = [{"day": "2026-08-24", "imb": 1.0, "vpin": 1.0}
            for _ in range(30)]
    assert g.seed(rows, today="2026-08-25") == {"today_buckets": 0}
    g.on_frame(100.0, 0.0)
    g.on_frame(101.0, 100.0)
    ev = g.on_frame(101.0, 200.0)[0]
    assert ev["pct"] is None          # yesterday bought it no voice


# ── THE FAST LINE (operator, 2026-09-23) ────────────────────────────────────
# "we need a fast line and a slow line ... 60k is why it is slow and takes
# time". The separation is the load-bearing part: two bucket sizes are two
# populations, and the slow log is the promotion evidence for a shadow module
# on a declared 30-session kill clock.

def test_the_fast_bucket_reaches_a_rank_on_less_volume():
    """Same tape, smaller bucket -> MIN_HIST arrives sooner. That IS the point."""
    assert vpin.FAST_BUCKET_V < vpin.BUCKET_V
    need_fast = vpin.FAST_BUCKET_V * vpin.MIN_HIST
    need_slow = vpin.BUCKET_V * vpin.MIN_HIST
    assert need_fast < need_slow
    # measured on the cache the constants came from: a median day is ~2.96M
    # units, and the slow line's first rank needs ~20% of it
    assert need_slow / 2_963_090 > 0.15
    assert need_fast / 2_963_090 < 0.10


def test_the_two_gauges_rank_against_their_own_populations():
    """A fast bucket and a slow bucket fed the identical tape do not share a
    percentile — each ranks inside its own series, which is why the face must
    compare their shapes and never their numbers."""
    fast, slow = vpin.Gauge(bucket_v=100), vpin.Gauge(bucket_v=400)
    fast.on_frame(100.0, 0); slow.on_frame(100.0, 0)
    for i in range(40):
        px = 100.0 + (1 if i % 2 else -1)          # alternating, then one push
        fast.on_frame(px, 100); slow.on_frame(px, 100)
    for _ in range(12):
        fast.on_frame(200.0, 100); slow.on_frame(200.0, 100)
    assert fast.state()["buckets"] > slow.state()["buckets"]
    # both have a reading; they are not required to agree, and the test does
    # not assert they do -- it asserts they are counted apart
    assert fast.state()["bucket_v"] != slow.state()["bucket_v"]


def test_the_fast_log_is_a_different_file_from_the_promotion_record():
    import server
    assert server.VPIN_FAST_LOG != server.VPIN_LOG
    assert server.VPIN_FAST_LOG != server.VPIN_BACKFILL_LOG
    assert server.VPIN_FAST_INST != "NIFTY-FUT"
    # the frame and the board read the bare instrument key, so the suffix is
    # what keeps the fast line out of everything downstream
    assert server.VPIN_FAST_INST.startswith("NIFTY-FUT")


def test_a_fast_log_that_was_never_written_is_nothing_yet_not_a_failure(tmp_path):
    """On day one the file does not exist because no bucket has completed.
    That is `[]` ("checked, nothing yet"), never None ("could not check")."""
    import server
    missing = str(tmp_path / "never_written.jsonl")
    assert server._vpin_fast_rows(missing, "2026-09-23", "NIFTY-FUT:fast") == []


def test_a_fast_log_that_exists_is_filtered_to_the_day_and_the_instrument(tmp_path):
    import json as _json
    import server
    p = tmp_path / "vpin_fast.jsonl"
    p.write_text("\n".join(_json.dumps(r) for r in [
        {"at": "09:24", "imb": 0.3, "vpin": 0.1, "pct": 0.4,
         "day": "2026-09-23", "inst": "NIFTY-FUT:fast"},
        {"at": "09:25", "imb": 0.4, "vpin": 0.2, "pct": 0.6,
         "day": "2026-09-23", "inst": "NIFTY-FUT"},          # the SLOW line
        {"at": "15:20", "imb": 0.9, "vpin": 0.9, "pct": 0.9,
         "day": "2026-09-22", "inst": "NIFTY-FUT:fast"},     # yesterday
    ]) + "\n", encoding="utf-8")
    rows = server._vpin_fast_rows(str(p), "2026-09-23", "NIFTY-FUT:fast")
    assert [r["t"] for r in rows] == ["09:24"]
    assert rows[0]["backfill"] is False and rows[0]["src"] == "live_frames"
