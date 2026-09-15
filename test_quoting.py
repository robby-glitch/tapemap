"""quoting.py -- fills only on a real cross, at OUR price, mode recorded;
one-sided books refuse with a reason; stale intent dies counted."""

import quoting


def test_a_resting_sell_fills_only_when_the_bid_reaches_it():
    q = quoting.Quoter()
    q.post("NIFTY", 25200.0, "CE", "SELL", 105.0, 130, "SELL_PIN", "10:00")
    # bid below our offer: no fill
    assert q.on_quotes("NIFTY", {(25200.0, "CE"): {"bid": 104.0,
                                                   "ask": 106.0}},
                       "10:01") == []
    fills = q.on_quotes("NIFTY", {(25200.0, "CE"): {"bid": 105.0,
                                                    "ask": 107.0}}, "10:02")
    assert len(fills) == 1
    f = fills[0]
    assert f.px == 105.0 and f.mode == "maker" and f.side == "SELL"
    assert q.resting == []                       # filled quotes leave the book


def test_a_resting_buy_fills_when_the_ask_falls_to_it():
    q = quoting.Quoter()
    q.post("NIFTY", 25000.0, "PE", "BUY", 90.0, 130, "X", "10:00")
    assert q.on_quotes("NIFTY", {(25000.0, "PE"): {"bid": 91.0,
                                                   "ask": 92.0}},
                       "10:01") == []
    fills = q.on_quotes("NIFTY", {(25000.0, "PE"): {"bid": 88.0,
                                                    "ask": 89.5}}, "10:02")
    assert len(fills) == 1 and fills[0].px == 90.0


def test_ttl_expires_stale_intent_and_counts_it():
    q = quoting.Quoter()
    q.post("NIFTY", 25200.0, "CE", "SELL", 105.0, 130, "S", "10:00", ttl=2)
    quiet = {(25200.0, "CE"): {"bid": 100.0, "ask": 101.0}}
    q.on_quotes("NIFTY", quiet, "10:01")
    q.on_quotes("NIFTY", quiet, "10:02")
    assert q.resting == [] and q.expired == 1


def test_take_crosses_at_the_touch_and_refuses_one_sided_books():
    q = quoting.Quoter()
    by_k = {(25000.0, "CE"): {"bid": 99.0, "ask": 101.0}}
    f, why = q.take("NIFTY", 25000.0, "CE", "BUY", 130, "SCALP", by_k, "t")
    assert f.px == 101.0 and f.mode == "taker" and why is None
    f2, why2 = q.take("NIFTY", 25000.0, "CE", "SELL", 130, "S",
                      {(25000.0, "CE"): {"ask": 101.0}}, "t")
    assert f2 is None and "no bid" in why2


def test_cancel_by_predicate_and_other_index_untouched():
    q = quoting.Quoter()
    q.post("NIFTY", 25200.0, "CE", "SELL", 105.0, 130, "S", "t")
    q.post("SENSEX", 81500.0, "CE", "SELL", 205.0, 40, "S", "t")
    assert q.cancel(lambda x: x.idx == "NIFTY") == 1
    assert len(q.resting) == 1 and q.resting[0].idx == "SENSEX"
    # a NIFTY snapshot must not age or fill the SENSEX quote
    q.on_quotes("NIFTY", {}, "t")
    assert q.resting[0].age == 0
