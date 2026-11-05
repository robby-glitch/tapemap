"""5 Nov: once PALAT? is said, the word goes back to HOLD only on a new extreme -- the card's own wrong-line ("back to HOLD
on a real new high past X"). Before, the leg's PALAT? latch lapsing in the same pause brought HOLD back with no new
extreme, and the buyer line offered a new CE / PE (5 Nov NIFTY / SENSEX 14:44, SENSEX 10:29 / 10:38)."""
import jarvis
from test_jarvis import _toy


def _frame(after):
    """A ▼ TREND leg to 10:19 (extreme 23,043f), PALAT? 10:20-10:28 (0.40 of the leg back), then `after(i)` -> (word,
    extreme) for the leg rows from 10:29."""
    d = _toy()
    d["reads"] = jarvis.reads(d)
    rows = []
    for i, m in enumerate(d["mins"]):
        word, ext = ("TREND", 23043.0) if i < 20 else ("PALAT?", 23043.0) if i < 29 else after(i)
        rows.append({"t": m, "lean": -1, "word": word, "risk": [],
                     "leg": {"dir": -1, "quality": "TREND", "extreme": ext, "retrace": 0.4 if word == "PALAT?" else 0.1}})
    d["legs"] = {"rows": rows, "day": {"flips": [0] * 40, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    return d


def test_palatq_holds_through_the_pause_without_a_new_extreme():
    a = jarvis.action_words(_frame(lambda i: ("HOLD", 23043.0)))      # the latch lapses, price never makes a new low
    assert a[20]["word"] == "PALAT?"
    assert all(x["word"] == "PALAT?" for x in a[20:])                 # before: HOLD at the 10:32 close


def test_a_new_extreme_releases_it():
    a = jarvis.action_words(_frame(lambda i: ("TREND", 23043.0 - 3 * (i - 28))))   # a real new low from 10:29
    assert a[20]["word"] == "PALAT?" and a[-1]["word"] in ("TREND", "HOLD")


def test_a_new_extreme_then_a_new_pause_is_not_held():
    # a new low at 10:29 (the leg's extreme moves), then a pause again: the old PALAT? does not hold the new pause
    a = jarvis.action_words(_frame(lambda i: ("TREND" if i == 29 else "HOLD", 23040.0)))
    assert a[-1]["word"] == "HOLD"


def test_watch_offers_no_new_sale_either():
    """WATCH (the count turned against): the buyer line already said "no new one"; the seller line offered a new sale."""
    d = _toy()
    g = {"dir": -1, "quality": "TREND", "pts": 117, "sigma_max": 2.1, "toot": None, "fuelled": None, "origin": 23102.0,
         "origin_t": "10:00", "extreme": 22985.0, "extreme_t": "10:30", "retrace": 0.1}
    d["legs"] = {"rows": [{"t": m, "lean": -1, "word": "WATCH", "risk": [], "leg": g, "line": "WATCH", "alive": [],
                           "notes": [], "missing": []} for m in d["mins"]],
                 "day": {"flips": [0] * 40, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    d["reads"] = jarvis.reads(d)
    d["verdict"] = {"BUY": {}, "SELL": {}}
    d["health"] = jarvis.health(d, None)
    d["reads"]["action"] = [dict(x, word="WATCH") for x in jarvis.action_words(d)]
    c = jarvis.call(d)
    assert "no new one while WATCH" in c["buyer"] and "no new one while WATCH" in c["seller"]
