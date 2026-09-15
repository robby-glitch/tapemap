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
