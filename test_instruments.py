from instruments import resolve_futures_id, get, DEFAULT


def test_resolve_futures_id_picks_nearest_unexpired():
    rows = [
        {"SECURITY_ID": "111", "UNDERLYING_SYMBOL": "BANKNIFTY", "INSTRUMENT": "FUTIDX", "SM_EXPIRY_DATE": "2026-07-29"},
        {"SECURITY_ID": "222", "UNDERLYING_SYMBOL": "BANKNIFTY", "INSTRUMENT": "FUTIDX", "SM_EXPIRY_DATE": "2026-08-26"},
        {"SECURITY_ID": "333", "UNDERLYING_SYMBOL": "NIFTY",     "INSTRUMENT": "FUTIDX", "SM_EXPIRY_DATE": "2026-07-29"},
    ]
    sid, exp = resolve_futures_id(rows, "BANKNIFTY", "2026-07-23")
    assert sid == "111" and exp == "2026-07-29"


def test_resolve_futures_id_skips_expired():
    rows = [
        {"SECURITY_ID": "111", "UNDERLYING_SYMBOL": "SENSEX", "INSTRUMENT": "FUTIDX", "SM_EXPIRY_DATE": "2026-07-20"},
        {"SECURITY_ID": "222", "UNDERLYING_SYMBOL": "SENSEX", "INSTRUMENT": "FUTIDX", "SM_EXPIRY_DATE": "2026-08-28"},
    ]
    sid, exp = resolve_futures_id(rows, "SENSEX", "2026-07-23")
    assert sid == "222"


def test_resolve_futures_id_excludes_options():
    # an OPTIDX row for the same underlying must never be chosen as the future
    rows = [
        {"SECURITY_ID": "999", "UNDERLYING_SYMBOL": "NIFTY", "INSTRUMENT": "OPTIDX", "SM_EXPIRY_DATE": "2026-07-24"},
        {"SECURITY_ID": "111", "UNDERLYING_SYMBOL": "NIFTY", "INSTRUMENT": "FUTIDX", "SM_EXPIRY_DATE": "2026-07-28"},
    ]
    sid, exp = resolve_futures_id(rows, "NIFTY", "2026-07-23")
    assert sid == "111" and exp == "2026-07-28"


def test_get_returns_copy_with_defaults():
    cfg = get(DEFAULT)
    assert cfg["under_id"] == 13 and cfg["step"] == 100
    cfg["step"] = 999
    assert get(DEFAULT)["step"] == 100     # get() must return a copy
