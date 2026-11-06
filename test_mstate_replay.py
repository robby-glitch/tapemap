"""tools/mstate_replay.py -- the market state's behaviour check (spec 2026-11-06 §9): refused in market hours, counts and
observed words only."""
import datetime
import os
import sys

import fold

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import mstate_replay  # noqa: E402


def test_the_replay_refuses_market_hours_and_counts_changes():
    ist = fold.IST
    assert mstate_replay.refused(datetime.datetime(2026, 11, 6, 10, 0, tzinfo=ist))        # a Friday, 10:00
    assert mstate_replay.refused(datetime.datetime(2026, 11, 6, 15, 39, tzinfo=ist))
    assert not mstate_replay.refused(datetime.datetime(2026, 11, 6, 15, 40, tzinfo=ist))
    assert not mstate_replay.refused(datetime.datetime(2026, 11, 6, 9, 14, tzinfo=ist))
    assert not mstate_replay.refused(datetime.datetime(2026, 11, 7, 10, 0, tzinfo=ist))    # a Saturday
    assert mstate_replay.changes(["A", "A", "B", "A"]) == 2
    assert mstate_replay.main(["2026-11-05", "2026-11-05"], now=datetime.datetime(2026, 11, 6, 11, 0, tzinfo=ist)) == 2


def _card(t, verdict, why, **k):
    return dict({"t": t, "close": t, "known": t, "late": False, "side": "SELL", "band": "u2", "verdict": verdict,
                 "why": why}, **k)


def test_one_touch_counts_once_and_a_close_beyond_the_record_is_named():
    zone = [{"t": "13:51", "side": "SELL", "band": "u2", "px": 1.0}, {"t": "13:52", "side": "SELL", "band": "u2", "px": 1.0},
            {"t": "14:09", "side": "SELL", "band": "u2", "px": 1.0}, {"t": "10:55", "side": "BUY", "band": "d2", "px": 1.0}]
    cards = [_card("13:51", "SKIP", "a"), _card("13:52", "SKIP", "a"),
             _card("10:55", "STRONG", "b", side="BUY", band="d2", late=True)]
    d = {"day": "2026-11-05", "mins": ["09:15", "09:16"], "zone": zone, "zone_cards": cards,
         "mstate": [{"t": "09:15", "word": "A"}, {"t": "09:16", "word": "B"}],
         "reads": {"action": [{"word": "X", "lean": 0}, {"word": "X", "lean": 0}]}, "health": {"notes": []}}
    r = mstate_replay.tally(d, "NIFTY")
    assert (r["zone_raw"], r["zone_dedup"], r["cards_raw"], r["cards_dedup"]) == (4, 3, 3, 2)
    assert r["not_carded"] == [("14:09", "SELL", "u2")]
    assert r["cards"]["SKIP"] == 1 and r["cards"]["STRONG"] == 1 and r["late_cards"] == 1
    assert (r["state_changes"], r["action_changes"]) == (1, 0)


def test_the_checks_say_what_the_engine_said_and_never_a_rate():
    why = "TREND ▲ + EXPANDING: a fade only if the band stopped expanding"
    fr = {"NIFTY": {"mins": ["12:32", "14:24"], "zone": [{"t": "13:51", "side": "SELL", "band": "u2", "px": 1.0}],
                    "mstate": [{"t": "09:40", "word": "TREND ▲ (leg, unconfirmed)"}, {"t": "12:32", "word": "RANGE"},
                               {"t": "14:24", "word": "RANGE"}],
                    "reads": {"action": [{"word": "HOLD", "lean": 1}, {"word": "WATCH", "lean": 1}]},
                    "zone_cards": [_card("12:30", "SKIP", why, close="12:32")]}}
    got = dict(mstate_replay.checks(fr))
    assert got["09:36–10:00 NIFTY word"] == "TREND ▲ (leg, unconfirmed)"
    assert got["12:30 NIFTY u2 sell"].startswith("SKIP — " + why) and got["12:30 NIFTY u2 sell"].endswith("state RANGE")
    assert got["09:36–10:00 SENSEX word"] == "not built"
    assert got["13:51 NIFTY sell"] == "not carded — close beyond the record"
    assert got["14:09 NIFTY sell"].startswith("no card")
    assert got["14:24 NIFTY words"] == "state RANGE · action WATCH ▲"
    assert "%" not in str(got)
