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

def _kite(bid, ask, qty=100):
    """A book as PaperDesk's bridge POSTs it. `bid`/`ask` are each a list of
    (price, orders) pairs, one per depth level -- explicit prices, not an
    arithmetic offset from the touch, so a test can put a level exactly where
    it wants it (or deliberately NOT where the Upstox ladder has one)."""
    return {"depth": {
        "bid": [{"qty": qty, "price": p, "orders": n} for p, n in bid],
        "ask": [{"qty": qty, "price": p, "orders": n} for p, n in ask]}}


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
    """Both feeds watch the same exchange, so the same instrument has the
    same prices at MULTIPLE levels. Matched -- and aligned -- by PRICE,
    never by list position (see the 5e section below for why that carries a
    real cost)."""
    lad = _ladder([(100.00, 10), (99.95, 10), (99.90, 10)],
                  [(100.05, 10), (100.10, 10), (100.15, 10)])
    books = {"111": _kite([(50.0, 1)], [(50.5, 1)]),
             "222": _kite([(100.00, 2), (99.95, 3), (99.90, 4)],
                          [(100.05, 7), (100.10, 8), (100.15, 9)])}
    got = pools.orders_for(lad, books)
    assert got == {"bid": [2, 3, 4], "ask": [7, 8, 9]}


def test_no_matching_book_leaves_the_question_open():
    lad = _ladder([(100.0, 10)], [(101.0, 10)])
    assert pools.orders_for(lad, {"1": _kite([(1.0, 1)], [(2.0, 1)])}) is None
    assert pools.orders_for(lad, None) is None
    assert pools.orders_for(None, {"1": _kite([(1.0, 1)], [(2.0, 1)])}) is None


def test_an_ambiguous_match_is_refused_not_guessed():
    """Two books, BOTH genuinely confirmed across every level at the same
    prices. Attributing one instrument's order counts to another is worse
    than having none."""
    lad = _ladder([(100.00, 10), (99.00, 10)], [(101.00, 10), (102.00, 10)])
    books = {"1": _kite([(100.00, 1), (99.00, 1)], [(101.00, 1), (102.00, 1)]),
             "2": _kite([(100.00, 99), (99.00, 99)],
                       [(101.00, 99), (102.00, 99)])}
    assert pools.orders_for(lad, books) is None


def test_a_book_that_moved_a_tick_still_matches():
    """Two snapshots taken a moment apart can drift by a few paise; the
    tolerance applies per level, not only at the touch."""
    lad = _ladder([(100.00, 10), (99.00, 10)], [(101.00, 10), (102.00, 10)])
    got = pools.orders_for(lad, {"1": _kite([(100.03, 5), (99.02, 6)],
                                            [(101.04, 7), (102.03, 9)])})
    assert got == {"bid": [5, 6], "ask": [7, 9]}


# --------------------------------------------------------------------------
# 5e -- the two defects the Kite-bridge audit found. Both reproduced against
# the OLD `orders_for` first (see the note in each docstring), then fixed.
# --------------------------------------------------------------------------

def test_a_touch_only_coincidence_without_the_true_twin_is_refused():
    """Deep OTM options routinely sit at the exchange's minimum tick -- 0.05
    bid, 0.10 ask -- by coincidence, not because they are the same
    instrument. If the TRUE twin is not in the handed dict, one unrelated
    book quoting that same floor price must not be accepted just because it
    is the only book that happens to be there: being the sole candidate is
    not the same as being confirmed. Every deeper level here belongs to a
    completely different instrument -- proof, not just absence of proof.

    Against the OLD `orders_for` (touch-uniqueness only, no per-level
    confirmation) this returned {"bid": [40, ...], "ask": [41, ...]} -- a
    confident wrong match. A confident wrong wall is worse than an honest
    unknowable."""
    lad = _ladder([(0.05, 500), (1.05, 500), (2.05, 500)],
                  [(0.10, 500), (1.10, 500), (2.10, 500)])
    coincidence = {"999": _kite([(0.05, 40), (12.30, 1)],
                                [(0.10, 41), (18.75, 1)])}
    assert pools.orders_for(lad, coincidence) is None


def test_counts_are_aligned_by_price_not_by_list_position():
    """Kite's book is missing the level Upstox has at 99.00 (a stale quote
    that has not refreshed there yet). Zipping the two lists index-for-index
    -- the OLD behaviour -- would attribute Kite's SECOND entry (meant for
    98.00) to Upstox's 99.00 level instead, one level too high. Aligning by
    PRICE instead gives 99.00 None (honestly unmatched) and still hands
    98.00 its own, correct, count.

    Against the OLD `orders_for` this returned {"bid": [2, 4], "ask": [7, 8,
    9]} -- Kite's own list, unaligned to Upstox's ladder length or prices at
    all, let alone correctly."""
    lad = _ladder([(100.00, 10), (99.00, 10), (98.00, 10)],
                  [(101.00, 10), (102.00, 10), (103.00, 10)])
    books = {"1": _kite([(100.00, 2), (98.00, 4)],       # 99.00 missing
                        [(101.00, 7), (102.00, 8), (103.00, 9)])}
    got = pools.orders_for(lad, books)
    assert got == {"bid": [2, None, 4], "ask": [7, 8, 9]}
