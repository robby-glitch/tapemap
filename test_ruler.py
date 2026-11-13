"""ruler.py (Jarvis decode v5, phase 1): her bands are the zone machine's own, the flow is Dext's only, a hole is BLIND."""
import contract_bars as cb
import ruler


def _ones(rows):
    return [{"t": t, "o": o, "h": h, "l": lo, "c": c, "v": v, "oi": 0} for t, o, h, lo, c, v in rows]


def _c(hhmm, delta, vol=100):
    return {"time": f"2026-11-11 {hhmm}:00", "total_volume": vol, "delta": delta}


def test_the_bands_are_the_zone_machines_own_recurrence_on_3_min_bars():
    ones = _ones([(f"09:{15 + k:02d}", 100 + k, 101 + k, 99 + k, 100.5 + k, 10 + k) for k in range(9)])
    b3 = cb.resample(ones, 3)
    assert ruler.bands(ones) == cb.with_bands(b3, cb.bands_on(b3)) and [b["t"] for b in ruler.bands(ones)] == ["09:15", "09:18", "09:21"]
    last = ruler.bands(ones)[-1]
    assert last["d2"] < last["d1"] < last["vwap"] < last["u1"] < last["u2"] < last["u3"]


def test_the_location_word_comes_from_z_and_says_when_it_cannot_read():
    band = {"vwap": 100.0, "u1": 102.0}                                  # σ = 2
    word = lambda px, m=600: ruler.where(px, band, m)["word"]            # noqa: E731
    assert [word(p) for p in (100.0, 101.9, 102.0, 96.5, 104.0, 105.9, 94.0, 106.0)] == \
        ["VALUE", "VALUE", "EDGE", "EDGE", "ZONE", "ZONE", "BEYOND", "BEYOND"]           # reaching 2σ IS her zone
    assert ruler.where(96.0, band, 600)["side"] == -1 and round(ruler.where(96.0, band, 600)["z"], 2) == -2.0
    assert ruler.where(104.0, band, 9 * 60 + 24)["word"] == "bands forming"
    assert ruler.where(104.0, {"vwap": 100.0, "u1": 100.0}, 600) is None and ruler.where(104.0, None, 600) is None


def test_flow_is_dexts_only_and_a_missing_minute_is_blind_never_a_number():
    cs = [_c(f"09:{15 + k:02d}", 65 * (k + 1)) for k in range(5)]        # 09:15 bar: +15 lots
    cs += [_c(f"09:{20 + k:02d}", -130) for k in (0, 1, 2, 4)]            # 09:23 never came: the 09:20 bar is BLIND
    cs += [_c(f"09:{25 + k:02d}", -65) for k in range(5)]                 # 09:25 bar: −5 lots, a new CVD stretch
    cs += [_c("09:30", 650)]                                              # still open: not a bar
    F = ruler.flow(cs, 65)
    assert [(b["t"], b["delta"], b["cvd"], b["since"], b["miss"]) for b in F] == \
        [("09:15", 15, 15, "09:15", 0), ("09:20", None, None, None, 1), ("09:25", -5, 10, "09:25", 0)]
    assert F[0]["q"] == 975 and F[2]["cq"] == 650                         # contracts, as her Dext bar statistics print
    assert [b["t"] for b in ruler.flow(cs, 65, upto=9 * 60 + 24)] == ["09:15"]      # 09:24: the 09:20 bar is still open
    assert ruler.flow([], 65) == [] and ruler.flow([_c("09:15", 5, vol=0)], 65) == []


def test_a_rewritten_minute_keeps_its_fullest_row():
    cs = [_c(f"09:{15 + k:02d}", 65) for k in range(5)] + [_c("09:19", 650, vol=900)]
    assert ruler.flow(cs, 65)[0]["delta"] == 14                           # 4 × 1 + 10


def test_push_bars_carry_dexts_delta_on_the_exchange_candle_and_a_blind_slot_is_no_bar():
    ones = _ones([(f"09:{15 + k:02d}", 100, 102, 99, 101, 650) for k in range(15)])
    cs = [_c(f"09:{15 + k:02d}", 130) for k in range(5)] + [_c(f"09:{20 + k:02d}", -65) for k in (0, 1, 3, 4)] \
        + [_c(f"09:{25 + k:02d}", -65) for k in range(5)]
    assert ruler.push_bars(ones, cs, 65) == [
        {"s": 555 * 60, "o": 100, "h": 102, "l": 99, "c": 101, "vol": 50.0, "delta": 10, "src": "dext"},
        {"s": 565 * 60, "o": 100, "h": 102, "l": 99, "c": 101, "vol": 50.0, "delta": -5, "src": "dext"}]


def test_D_is_the_median_of_the_earlier_readable_bars_only():
    bars = [{"delta": d} for d in (10, -30, None, 20, 5)]
    assert ruler.noise(bars) == [None, 10, 20.0, 20.0, 20]
