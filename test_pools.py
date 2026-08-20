"""The terrain map, and the one thing it must keep refusing to say.

`test_wall_versus_cluster_is_never_guessed` is the important one. A shelf of
size is either one algorithm's wall or a crowd of small orders on a round
number -- opposite implications, and the difference is only visible in the
per-level ORDER COUNT, which this feed does not carry. Guessing it from size
would be an inference wearing a measurement's clothes, which is the specific
error the whole [M]/[I] discipline exists to prevent.
"""
import json
from pathlib import Path

import pools
import upstox_adapter as ua

FRAME = Path(__file__).parent / "data" / "feed_frame_2026-08-20.json"


def _real_fut():
    d = json.loads(FRAME.read_text(encoding="utf-8"))
    return ua.depth_ladder(d["frames"][d["fut_key"]])


def _ladder(bids, asks):
    """A book from (price, qty) pairs, best first."""
    b = [{"price": p, "qty": q} for p, q in bids]
    a = [{"price": p, "qty": q} for p, q in asks]
    return {"bid": b, "ask": a,
            "bid_qty": sum(x["qty"] for x in b),
            "ask_qty": sum(x["qty"] for x in a),
            "tbq": None, "tsq": None}


# --------------------------------------------------------------------------
# the refusal
# --------------------------------------------------------------------------

def test_wall_versus_cluster_is_never_guessed():
    """Upstox sends qty and price; Kite also sends `orders`. Without it the
    question is unanswerable, so it stays unanswered -- with the reason."""
    for p in pools.map_book(_real_fut()):
        assert p.kind is None
        assert "order counts" in p.why


def test_the_map_says_how_far_it_can_see():
    """Five levels a side is a keyhole. A panel that does not say so invites a
    reader to treat it as the whole book."""
    s = pools.summary(_real_fut())
    lo, hi = s["blind_past"]
    assert lo < hi                       # the deepest bid and ask observed


# --------------------------------------------------------------------------
# shelves
# --------------------------------------------------------------------------

def test_a_level_far_above_the_books_own_typical_size_is_a_shelf():
    lad = _ladder([(100.0, 10), (99.0, 10), (98.0, 500), (97.0, 10), (96.0, 10)],
                  [(101.0, 10), (102.0, 10), (103.0, 10)])
    shelves = [p for p in pools.map_book(lad) if p.kind_of == "shelf"]
    assert len(shelves) == 1
    assert shelves[0].price == 98.0 and shelves[0].qty == 500
    assert shelves[0].times == 50.0 and shelves[0].side == "bid"


def test_size_is_judged_against_the_same_book_never_an_absolute():
    """780 lots is a wall on the future and nothing on an ATM call. Identical
    shapes at wildly different scales must produce identical readings."""
    small = _ladder([(100.0, 1), (99.0, 1), (98.0, 10), (97.0, 1)],
                    [(101.0, 1), (102.0, 1), (103.0, 1)])
    big = _ladder([(100.0, 1000), (99.0, 1000), (98.0, 10000), (97.0, 1000)],
                  [(101.0, 1000), (102.0, 1000), (103.0, 1000)])
    a = [p.times for p in pools.map_book(small) if p.kind_of == "shelf"]
    b = [p.times for p in pools.map_book(big) if p.kind_of == "shelf"]
    assert a == b == [10.0]


def test_an_even_book_has_no_shelf():
    lad = _ladder([(100.0, 10), (99.0, 10), (98.0, 10), (97.0, 10)],
                  [(101.0, 10), (102.0, 10), (103.0, 10)])
    assert not [p for p in pools.map_book(lad) if p.kind_of == "shelf"]


# --------------------------------------------------------------------------
# vacuums
# --------------------------------------------------------------------------

def test_a_wide_gap_between_levels_is_a_vacuum():
    """Aug-19's retrace fell 40 points on almost no aggressive selling because
    nothing rested above 24,140. Gravity through a gap, not conviction."""
    lad = _ladder([(100.0, 10), (99.0, 10), (98.0, 10), (97.0, 10)],
                  [(101.0, 10), (102.0, 10), (140.0, 10), (141.0, 10)])
    vacs = [p for p in pools.map_book(lad) if p.kind_of == "vacuum"]
    assert len(vacs) == 1
    assert vacs[0].price == 102.0 and vacs[0].to_price == 140.0
    assert vacs[0].side == "ask" and vacs[0].qty is None


def test_an_evenly_spaced_book_has_no_vacuum():
    assert not [p for p in pools.map_book(_ladder(
        [(100.0, 10), (99.0, 10), (98.0, 10), (97.0, 10)],
        [(101.0, 10), (102.0, 10), (103.0, 10), (104.0, 10)]))
        if p.kind_of == "vacuum"]


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------

def test_a_book_too_short_for_typical_to_mean_anything_is_not_described():
    """Two levels have no median worth the name. Silence, not a guess."""
    assert pools.map_book(_ladder([(100.0, 10), (99.0, 900)],
                                  [(101.0, 10), (102.0, 10)])) == []


def test_a_missing_book_is_declined_not_called_flat():
    assert pools.map_book(None) == []
    assert pools.map_book({}) == []
    assert pools.summary(None)["shelves"] == 0


def test_the_real_captured_book_is_describable():
    """The live NIFTY future, five a side: the map must actually run on it."""
    s = pools.summary(_real_fut())
    assert s["shelves"] + s["vacuums"] > 0
    assert all(p["tag"] == "M" for p in s["pools"])


# --------------------------------------------------------------------------
# wall vs cluster, once Kite's order counts arrive
# --------------------------------------------------------------------------

def _kite(bid_px, ask_px, bid_orders, ask_orders, qty=100):
    """A book as PaperDesk's bridge POSTs it."""
    return {"depth": {
        "bid": [{"qty": qty, "price": bid_px - i, "orders": n}
                for i, n in enumerate(bid_orders)],
        "ask": [{"qty": qty, "price": ask_px + i, "orders": n}
                for i, n in enumerate(ask_orders)]}}


def test_few_orders_holding_size_is_a_wall():
    lad = _ladder([(100.0, 10), (99.0, 10), (98.0, 500), (97.0, 10)],
                  [(101.0, 10), (102.0, 10), (103.0, 10)])
    shelf = [p for p in pools.map_book(lad, {"bid": [1, 1, 2, 1], "ask": []})
             if p.kind_of == "shelf"][0]
    assert shelf.kind == "wall" and shelf.orders == 2
    assert shelf.per_order == 250.0


def test_many_small_orders_on_one_level_is_a_crowd():
    """Eighty limits on a round number. Same size as a wall, opposite object:
    a crowd evaporates when touched."""
    lad = _ladder([(100.0, 10), (99.0, 10), (98.0, 500), (97.0, 10)],
                  [(101.0, 10), (102.0, 10), (103.0, 10)])
    shelf = [p for p in pools.map_book(lad, {"bid": [1, 1, 88, 1], "ask": []})
             if p.kind_of == "shelf"][0]
    assert shelf.kind == "cluster" and shelf.orders == 88


def test_the_middle_is_refused_rather_than_forced():
    """A classifier that put every level in one of two boxes would be most
    confident exactly where it has least reason to be."""
    lad = _ladder([(100.0, 10), (99.0, 10), (98.0, 500), (97.0, 10)],
                  [(101.0, 10), (102.0, 10), (103.0, 10)])
    shelf = [p for p in pools.map_book(lad, {"bid": [1, 1, 9, 1], "ask": []})
             if p.kind_of == "shelf"][0]
    assert shelf.kind is None and "neither clearly" in shelf.why


def test_without_counts_the_question_stays_open():
    lad = _ladder([(100.0, 10), (99.0, 10), (98.0, 500), (97.0, 10)],
                  [(101.0, 10), (102.0, 10), (103.0, 10)])
    shelf = [p for p in pools.map_book(lad) if p.kind_of == "shelf"][0]
    assert shelf.kind is None and "order counts absent" in shelf.why
    assert pools.summary(lad)["orders_known"] is False


# --------------------------------------------------------------------------
# matching Kite's book to Upstox's, without a symbol table
# --------------------------------------------------------------------------

def test_the_matching_book_is_found_by_its_top_of_book():
    """Both feeds watch the same exchange, so the same instrument has the same
    two prices at the touch. No symbol table, nothing to drift at expiry."""
    lad = _real_fut()
    b0, a0 = lad["bid"][0]["price"], lad["ask"][0]["price"]
    books = {"111": _kite(99999.0, 99999.5, [1], [1]),
             "222": _kite(b0, a0, [2, 3, 4, 5, 6], [7, 8, 9, 10, 11])}
    got = pools.orders_for(lad, books)
    assert got == {"bid": [2, 3, 4, 5, 6], "ask": [7, 8, 9, 10, 11]}


def test_no_matching_book_leaves_the_question_open():
    lad = _real_fut()
    assert pools.orders_for(lad, {"1": _kite(1.0, 2.0, [1], [1])}) is None
    assert pools.orders_for(lad, None) is None
    assert pools.orders_for(None, {"1": _kite(1.0, 2.0, [1], [1])}) is None


def test_an_ambiguous_match_is_refused_not_guessed():
    """Two books at the same touch. Attributing one instrument's order counts
    to another is worse than having none."""
    lad = _real_fut()
    b0, a0 = lad["bid"][0]["price"], lad["ask"][0]["price"]
    books = {"1": _kite(b0, a0, [1], [1]), "2": _kite(b0, a0, [99], [99])}
    assert pools.orders_for(lad, books) is None


def test_a_book_that_moved_a_tick_still_matches():
    lad = _real_fut()
    b0, a0 = lad["bid"][0]["price"], lad["ask"][0]["price"]
    got = pools.orders_for(lad, {"1": _kite(b0 + 0.05, a0 - 0.05, [5], [6])})
    assert got == {"bid": [5], "ask": [6]}
