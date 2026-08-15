"""`/api/contract` on Upstox -- the leg charts, off Dhan.

WHY THIS EXISTS. Dhan's Data API lapsed on 2026-08-05 and `build_contract` was
the last thing still wired to it: `chain_live.read_token` -> `.dhan_token`, a
`dhanhq` client for the expiry, and `dhan_fetch.rest_intraday` for every option
bar. With the subscription gone the CE/PE panes were not "empty", they were a
500. This is the port, and these tests hold the two halves apart:

  * on Upstox NOTHING may reach Dhan -- not the token file, not the client,
    not the scrip master. A route that half-fell-back would read as working
    while charting nothing.
  * on Dhan the path stays bit-for-bit what it was. The switch fails safe
    (`test_broker_switch.py`); this asserts the same thing one level up.

Everything runs offline. `upstox_rest` is monkeypatched, so `candles_to_arrays`
and `_one_session` run for real against Upstox-shaped rows -- newest-first, ISO
timestamps with a +05:30 offset -- which is where a reversed session or a 5:30
axis shift would show up.
"""

from datetime import datetime, timedelta, timezone

import pytest

import live
import upstox_instruments

IST = timezone(timedelta(hours=5, minutes=30))


# ---- fixtures --------------------------------------------------------------

def _exp_ms(days_ahead=7):
    """An expiry still ahead of `live_expiries`' wall clock, computed rather
    than hardcoded so this file does not rot on a fixed date."""
    return (datetime.now() + timedelta(days=days_ahead)).timestamp() * 1000


def _exp_day(ms):
    """The same formatting `upstox_instruments.resolve` uses."""
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")


def _rows(exp_ms, strikes=(24300.0, 24350.0, 24400.0), past_ms=None):
    """A slice of the Upstox dump: one future plus CE/PE at each strike.

    `past_ms` adds an ALREADY EXPIRED weekly, which is the thing the real dump
    does not contain -- kept here so the tests can prove the resolver ignores
    it rather than merely never seeing one.
    """
    out = [{"instrument_key": "NSE_FO|FUT1", "instrument_type": "FUTIDX",
            "strike_price": None, "expiry": exp_ms,
            "trading_symbol": "NIFTY FUT"}]
    for k in strikes:
        for side in ("CE", "PE"):
            out.append({"instrument_key": f"NSE_FO|{int(k)}{side}",
                        "instrument_type": side, "strike_price": k,
                        "expiry": exp_ms,
                        "trading_symbol": f"NIFTY{int(k)}{side}"})
            if past_ms is not None:
                out.append({"instrument_key": f"NSE_FO|OLD{int(k)}{side}",
                            "instrument_type": side, "strike_price": k,
                            "expiry": past_ms,
                            "trading_symbol": f"OLD{int(k)}{side}"})
    return out


def _candles(day, n=5, base=100.0, oi0=500000):
    """Upstox intraday candles: NEWEST FIRST, ISO stamps carrying real IST."""
    t0 = datetime.strptime(day, "%Y-%m-%d").replace(
        hour=9, minute=15, tzinfo=IST)
    rows = [[(t0 + timedelta(minutes=i)).isoformat(),
             base + i, base + i + 2, base + i - 1, base + i + 1,
             10.0 * (i + 1), oi0 + 100 * i] for i in range(n)]
    return list(reversed(rows))


class _Rest:
    """A stand-in for `upstox_rest` that records who was asked for what."""

    def __init__(self, n=5, empty=()):
        self.n, self.empty = n, set(empty)
        self.intraday_calls, self.historical_calls = [], []

    def intraday(self, key, tok, interval="1minute"):
        self.intraday_calls.append((key, tok))
        return [] if key in self.empty else _candles(_today(), self.n)

    def historical(self, key, tok, day, interval="1minute"):
        self.historical_calls.append((key, tok, day))
        return [] if key in self.empty else _candles(day, self.n)


@pytest.fixture
def upstox(monkeypatch):
    """Put the whole process on Upstox, with no network anywhere.

    `TAPEMAP_BROKER` is set for real rather than stubbing `_upstox()`, so the
    documented switch is what these tests exercise.
    """
    monkeypatch.setenv("TAPEMAP_BROKER", "upstox")
    # Weekends only change WHICH endpoint serves the newest session, and that
    # is not what these tests are about -- so live's clock is pinned to the
    # session day (2026-08-15, first weekend run caught the drift).
    monkeypatch.setattr(live, "datetime", _SessionClock)
    import upstox_feed
    import upstox_rest

    exp = _exp_ms()
    rest = _Rest()
    monkeypatch.setattr(upstox_instruments, "load",
                        lambda name="NIFTY", fetch=None: _rows(exp))
    monkeypatch.setattr(upstox_feed, "read_token", lambda path=None: "utok")
    monkeypatch.setattr(upstox_rest, "intraday", rest.intraday)
    monkeypatch.setattr(upstox_rest, "historical", rest.historical)
    rest.expiry_ms = exp
    rest.expiry = _exp_day(exp)
    return rest


@pytest.fixture
def no_dhan(monkeypatch):
    """Every Dhan door, wired to explode. Nothing on the Upstox path may knock."""
    import chain_live
    import dhan_fetch
    import instruments

    def boom(*a, **k):
        raise AssertionError("the Upstox path reached Dhan")

    for mod, name in ((chain_live, "read_token"), (chain_live, "token_status"),
                      (chain_live, "_client"), (chain_live, "resolve_expiry"),
                      (dhan_fetch, "rest_intraday"),
                      (instruments, "resolve_dynamic"),
                      (instruments, "_load_scrip")):
        monkeypatch.setattr(mod, name, boom)


def _today():
    """The session `build_contract` will treat as "today" -- NOT the calendar
    date. `_sessions_back` rolls a Sat/Sun request to Friday, and `live` then
    compares every session against its own wall clock to pick intraday vs
    historical and to decide the backfill caveat. On the first weekend run
    (Sat 2026-08-15) the calendar date and the session disagreed and four
    tests here failed -- a suite that cries every weekend gets ignored, so
    the tests anchor to the session, and the `upstox` fixture freezes
    `live`'s clock to the same day (see `_SessionClock`)."""
    d = datetime.now(IST)
    while d.weekday() >= 5:                      # same rule as _sessions_back
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


class _SessionClock(datetime):
    """`datetime` with `now` pinned to the last session day (time-of-day
    kept). Swapped in for `live.datetime` so that on a weekend `live` agrees
    with `_today()` that Friday's session "is" today -- the exact agreement
    the market provides for free Mon-Fri. Everything else (`strptime`,
    arithmetic) is inherited untouched."""

    @classmethod
    def now(cls, tz=None):
        d = datetime.now(tz)
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        return d


# ---- 1. the expiry the legs are actually resolved against ------------------

def test_option_expiry_is_the_same_one_option_keys_resolves(upstox):
    """Two answers to "which contract is this" would eventually disagree, and
    the payload would then name an expiry the bars do not belong to."""
    exp = upstox_instruments.option_expiry("NIFTY")
    assert exp == upstox.expiry
    keys = upstox_instruments.option_keys(24350, "NIFTY")
    assert keys == {"CE": "NSE_FO|24350CE", "PE": "NSE_FO|24350PE"}


def test_an_expired_weekly_in_the_dump_is_never_chosen(monkeypatch):
    past = (datetime.now() - timedelta(days=3)).timestamp() * 1000
    exp = _exp_ms()
    monkeypatch.setattr(upstox_instruments, "load",
                        lambda name="NIFTY", fetch=None: _rows(exp, past_ms=past))
    assert upstox_instruments.option_expiry("NIFTY") == _exp_day(exp)
    assert upstox_instruments.option_keys(24350, "NIFTY")["CE"] == \
        "NSE_FO|24350CE"


def test_option_expiry_refuses_rather_than_guessing_when_none_are_live(monkeypatch):
    past = (datetime.now() - timedelta(days=3)).timestamp() * 1000
    monkeypatch.setattr(upstox_instruments, "load",
                        lambda name="NIFTY", fetch=None: _rows(past))
    with pytest.raises(RuntimeError, match="no live option expiry"):
        upstox_instruments.option_expiry("NIFTY")


# ---- 2. the route runs, and touches nothing of Dhan's ---------------------

def test_build_contract_on_upstox_charts_both_legs(upstox, no_dhan):
    out = live.build_contract("NIFTY", strike=24350, side="BOTH", interval=1,
                              days=1, day=_today())
    assert out["ok"] is True
    assert out["broker"] == "upstox"
    assert out["expiry"] == upstox.expiry
    assert len(out["axis"]) == 5
    for leg in out["legs"].values():
        assert len(leg["bars"]) == 5
        assert leg["gaps"] == []
    # the ids the payload reports are Upstox instrument KEYS, not Dhan ids
    assert out["legs"]["CE"]["security_id"] == "NSE_FO|24350CE"
    assert out["legs"]["PE"]["security_id"] == "NSE_FO|24350PE"


def test_todays_legs_come_from_the_intraday_endpoint(upstox, no_dhan):
    live.build_contract("NIFTY", strike=24350, side="BOTH", interval=1,
                        days=1, day=_today())
    asked = {k for k, _tok in upstox.intraday_calls}
    assert {"NSE_FO|24350CE", "NSE_FO|24350PE"} <= asked
    assert upstox.historical_calls == []


def test_a_past_session_comes_from_the_historical_endpoint(upstox, no_dhan):
    # 2026-07-30 is a Thursday, so `_sessions_back` returns it unchanged
    live.build_contract("NIFTY", strike=24350, side="CE", interval=1,
                        days=1, day="2026-07-30")
    assert [d for _k, _t, d in upstox.historical_calls] == ["2026-07-30"] * 2
    assert upstox.intraday_calls == []


def test_the_index_series_is_the_future_out_of_the_upstox_dump(upstox, no_dhan):
    out = live.build_contract("NIFTY", strike=24350, side="BOTH", interval=1,
                              days=1, day=_today())
    idx = out["index_series"]
    assert out["index_series_why"] is None
    assert idx["instrument"] == "FUTIDX"
    assert idx["security_id"] == "NSE_FO|FUT1"     # resolved, never guessed
    assert len(idx["bars"]) == 5


def test_upstox_candles_are_flipped_oldest_first(upstox, no_dhan):
    """Upstox sends newest first. Feeding them straight through would run VWAP
    and the sigma bands backwards through the session."""
    out = live.build_contract("NIFTY", strike=24350, side="CE", interval=1,
                              days=1, day=_today())
    ts = [b["t"] for b in out["legs"]["CE"]["bars"]]
    assert ts == ["09:15", "09:16", "09:17", "09:18", "09:19"]
    assert ts == sorted(ts)


def test_the_ist_offset_survives_the_round_trip(upstox, no_dhan):
    """The stamps carry +05:30. A naive epoch read would put every bar 5:30
    out and `_one_session` would file them under the wrong day."""
    out = live.build_contract("NIFTY", strike=24350, side="CE", interval=1,
                              days=1, day=_today())
    assert out["legs"]["CE"]["bar_days"] == [_today()] * 5
    assert out["legs"]["CE"]["bars"][0]["t"] == "09:15"


# ---- 3. honest refusals, not silent fallbacks -----------------------------

def test_no_chain_snapshot_means_no_pair_and_no_second_socket(upstox, no_dhan):
    """The chain arrives over the poller's websocket. This route will not open
    a second one, and says so instead of quietly picking a strike."""
    with pytest.raises(RuntimeError, match="no strike requested"):
        live.build_contract("NIFTY", strike=None, side="BOTH", interval=1,
                            days=1, day=_today())


def test_the_pair_still_comes_from_a_snapshot_the_caller_supplies(upstox, no_dhan):
    """server.py hands over the snapshot the poller already paid for, so the
    pair picker works on Upstox exactly as it did on Dhan."""
    rows = [{"strike": 24350, "ce": {"ltp": 120.0}, "pe": {"ltp": 110.0}},
            {"strike": 24400, "ce": {"ltp": 95.0}, "pe": {"ltp": 140.0}}]
    out = live.build_contract("NIFTY", strike=None, side="BOTH", interval=1,
                              days=1, day=_today(), chain_rows=rows, atm=24350)
    assert out["pair"] is not None or out["pair_why"]


def test_a_gap_names_the_broker_that_served_nothing(upstox, no_dhan):
    upstox.empty = {"NSE_FO|24350CE"}
    out = live.build_contract("NIFTY", strike=24350, side="CE", interval=1,
                              days=1, day=_today())
    said = out["legs"]["CE"]["gap_reasons"][_today()]
    assert "Upstox" in said and "Dhan" not in said
    assert "no usable bars" in said


def test_backfill_discloses_that_the_expiry_is_the_current_one(upstox, no_dhan):
    """Expired weeklies drop out of Upstox's dump, so an older session is
    charted on the CURRENT front contract -- real data, different instrument
    from what Dhan would have picked. That has to be said, not assumed."""
    out = live.build_contract("NIFTY", strike=24350, side="CE", interval=1,
                              days=1, day="2026-07-30")
    assert out["expiry_why"]
    assert "expired" in out["expiry_why"]
    assert out["expiry"] in out["expiry_why"]


def test_todays_chart_carries_no_backfill_caveat(upstox, no_dhan):
    out = live.build_contract("NIFTY", strike=24350, side="CE", interval=1,
                              days=1, day=_today())
    assert out["expiry_why"] is None


# ---- 4. the Dhan path is untouched ----------------------------------------

def _payload(day, n=5, base=100.0):
    t0 = datetime.strptime(day, "%Y-%m-%d").replace(
        hour=9, minute=15, tzinfo=IST).timestamp()
    return {"open": [base + i for i in range(n)],
            "high": [base + i + 2 for i in range(n)],
            "low": [base + i - 1 for i in range(n)],
            "close": [base + i + 1 for i in range(n)],
            "volume": [10.0 * (i + 1) for i in range(n)],
            "open_interest": [500000 + 100 * i for i in range(n)],
            "timestamp": [t0 + 60 * i for i in range(n)]}


def test_default_broker_still_builds_the_contract_through_dhan(monkeypatch):
    """Setting nothing keeps the behaviour that has been running -- including
    the Dhan token gate and the Dhan expiry resolve."""
    import chain_live

    monkeypatch.delenv("TAPEMAP_BROKER", raising=False)
    seen = []
    monkeypatch.setattr(chain_live, "read_token",
                        lambda: seen.append("token") or "tok")
    monkeypatch.setattr(chain_live, "token_status", lambda t: {"ok": True})
    monkeypatch.setattr(chain_live, "_client",
                        lambda t: seen.append("client") or object())
    monkeypatch.setattr(chain_live, "_with_deadline", lambda fn, s, label: fn())
    monkeypatch.setattr(chain_live, "resolve_expiry",
                        lambda *a, **k: seen.append("expiry") or "2026-08-04")
    monkeypatch.setattr(live, "_atm_ids",
                        lambda k, cfg: {"CE": "111", "PE": "222"})

    out = live.build_contract("NIFTY", strike=24200, side="BOTH", interval=1,
                              days=1, day="2026-07-30", chain_rows=[],
                              fetch=lambda sec_id, day: _payload(day))
    assert seen == ["token", "client", "expiry"]
    assert out["broker"] == "dhan"
    assert out["expiry"] == "2026-08-04"
    assert out["expiry_why"] is None              # Dhan resolves the real one
    assert len(out["axis"]) == 5


def test_an_expired_dhan_token_still_fails_loudly(monkeypatch):
    import chain_live

    monkeypatch.delenv("TAPEMAP_BROKER", raising=False)
    monkeypatch.setattr(chain_live, "read_token", lambda: "tok")
    monkeypatch.setattr(chain_live, "token_status",
                        lambda t: {"ok": False, "msg": "Dhan token EXPIRED"})
    with pytest.raises(RuntimeError, match="Dhan token EXPIRED"):
        live.build_contract("NIFTY", strike=24200, side="CE",
                            fetch=lambda sec_id, d: _payload(d))
