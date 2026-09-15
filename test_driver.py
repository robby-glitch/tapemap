"""driver.py -- the lean fires on a real extreme, never on a quiet tape,
and the NSE participant CSV parses into the split it exists for."""

import driver


def _strikes(oi):
    return [{"k": 25000, "ce": {"oi": oi}, "pe": {"oi": oi}}]


def test_quiet_windows_never_read_as_an_extreme():
    d = driver.Driver()
    for n in range(driver.MIN_HIST + 4):
        r = d.on_snapshot(1000.0 + n, _strikes(5000.0))   # vtt creeps, OI flat
    # a flat chain's d_oi is 0 every window; percentile-of-zero-in-zeros is
    # 1.00 and must NOT surface as a rank or a lean (the drain-rank trap)
    assert r["oi_rank"] is None
    assert r["lean"] in ("UNCLEAR", "FUTURES_LED")


def test_futures_led_fires_on_a_real_volume_burst():
    d = driver.Driver()
    # non-monotonic warm-up: small, varying futures volume, flat chain
    vtt = 0.0
    for n, dv in enumerate((10, 30, 20, 40, 15, 25, 35, 20, 30, 25)):
        vtt += dv
        r = d.on_snapshot(vtt, _strikes(5000.0))
    vtt += 100000.0                                        # the burst
    r = d.on_snapshot(vtt, _strikes(5000.0))
    assert r["lean"] == "FUTURES_LED"
    assert r["fut_rank"] is not None and r["fut_rank"] >= driver.LEAD_P
    assert r["tag"] == "I"


def test_option_led_fires_when_the_chain_turns_over_and_futures_sleep():
    d = driver.Driver()
    oi = 5000.0
    for n, doi in enumerate((5, 15, 10, 20, 8, 12, 18, 10, 15, 12)):
        oi += doi
        d.on_snapshot(None, _strikes(oi))                  # no futures volume
    r = d.on_snapshot(None, _strikes(oi + 50000.0))
    assert r["lean"] == "OPTION_LED"
    assert "no futures volume" in (r["fut_why"] or "")


CSV = """\
Participant wise Open Interest as on Aug 21 2026

Client Type,Future Index Long,Future Index Short,Future Stock Long,Future Stock Short,Option Index Call Long,Option Index Put Long,Option Index Call Short,Option Index Put Short,Total Long Contracts,Total Short Contracts
Client,100000,150000,1,1,"2,000,000",1800000,1500000,1900000,1,1
DII,5000,60000,1,1,10000,50000,20000,10000,1,1
FII,200000,120000,1,1,400000,500000,450000,400000,1,1
Pro,80000,90000,1,1,900000,800000,1200000,700000,1,1
TOTAL,385000,420000,4,4,3310000,3150000,3170000,3010000,4,4
"""


def test_participant_csv_parses_the_only_true_retail_split():
    got = driver._parse_participant(CSV)
    assert "TOTAL" not in got
    assert got["Client"]["call_long"] == 2000000     # quoted thousands comma
    assert got["Client"]["fut_short"] == 150000
    assert got["Pro"]["call_short"] == 1200000
    assert set(got) == {"Client", "DII", "FII", "Pro"}
