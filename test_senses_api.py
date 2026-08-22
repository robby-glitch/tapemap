"""The senses HTTP surface -- the part 707 tests never touched.

Both defects fixed here were found by review, not by a test, and the reason is
visible in `grep -l _SENSES *.py`: before this file, nothing tested the server's
book layer at all. The detectors had tests; the seam where their state meets a
concurrent HTTP handler did not.

Nothing here starts a server. `_clean_books` is a pure function, and the race is
reproduced by driving the two real code paths against each other directly, which
is faster and deterministic.
"""
import json
import threading

import pools
import server


# --------------------------------------------------------------------------
# the POST is unauthenticated and its body is attacker-shaped
# --------------------------------------------------------------------------

def test_a_book_that_is_not_a_dict_cannot_reach_orders_for():
    """POST {"books":{"1":5}} used to raise AttributeError inside the senses
    loop every 0.5s -- caught there, it left the book layer dark until a valid
    bridge POST happened to overwrite the poisoned dict."""
    assert server._clean_books({"1": 5}) == {}
    # and the real consumer survives what does get through
    assert pools.orders_for({"bid": [{"price": 1.0, "qty": 1}],
                             "ask": [{"price": 2.0, "qty": 1}]},
                            server._clean_books({"1": 5})) is None


def test_junk_shapes_are_dropped_rather_than_trusted():
    for junk in (None, [], "books", 5, {"1": None}, {"1": {"depth": 7}},
                 {"1": {"depth": {"bid": "no", "ask": "no"}}},
                 {"1": {"depth": {"bid": [], "ask": []}}}):
        assert server._clean_books(junk) == {}


def test_a_non_numeric_price_is_dropped_before_it_can_be_subtracted():
    """orders_for does abs(price - b0). A string raises TypeError; a NaN
    compares false against everything and reads as 'no book matched' -- a wrong
    answer wearing a right one's clothes."""
    for bad in ("24000", None, float("nan"), float("inf"), True):
        got = server._clean_books(
            {"1": {"depth": {"bid": [{"price": bad, "orders": 3}],
                             "ask": [{"price": 1.0, "orders": 3}]}}})
        assert got == {}, bad


def test_a_real_bridge_post_survives_intact():
    books = {"265": {"depth": {
        "bid": [{"price": 24000.0, "qty": 100, "orders": 3}],
        "ask": [{"price": 24000.05, "qty": 100, "orders": 8}]}}}
    got = server._clean_books(books)
    assert got["265"]["depth"]["bid"][0]["orders"] == 3
    assert got["265"]["depth"]["ask"][0]["orders"] == 8
    # and it still matches a ladder at the same touch
    lad = {"bid": [{"price": 24000.0, "qty": 50}],
           "ask": [{"price": 24000.05, "qty": 50}]}
    assert pools.orders_for(lad, got) == {"bid": [3], "ask": [8]}


def test_the_number_of_books_and_the_depth_per_side_are_both_capped():
    many = {str(i): {"depth": {"bid": [{"price": 1.0}], "ask": [{"price": 2.0}]}}
            for i in range(server._MAX_BOOKS + 50)}
    assert len(server._clean_books(many)) == server._MAX_BOOKS
    deep = {"1": {"depth": {"bid": [{"price": float(i)} for i in range(40)],
                            "ask": [{"price": 1.0}]}}}
    assert len(server._clean_books(deep)["1"]["depth"]["bid"]) == 10


# --------------------------------------------------------------------------
# the race the lock exists to prevent
# --------------------------------------------------------------------------

def test_reading_the_reading_while_new_strikes_arrive_does_not_raise():
    """The daemon adds a Fuse the moment spot drifts to a fresh near-ATM strike,
    while the handler iterates `book._by` to answer /api/senses. Unlocked this
    raises 'dictionary changed size during iteration', the handler 500s, and the
    console paints CONSOLE CANNOT REACH THE SERVER in the red kept for a dead
    feed. Without server._SENSES_LOCK this fails within a few hundred
    iterations; with it, never.
    """
    import fuse
    book = fuse.Book()
    stop, errors = threading.Event(), []

    def add():                      # the senses loop, discovering new strikes
        i = 0
        while not stop.is_set():
            with server._SENSES_LOCK:
                book.for_inst(f"NIFTY-{24000 + i * 50}CE")
            i += 1

    def read():                     # the HTTP handler, answering /api/senses
        try:
            for _ in range(3000):
                with server._SENSES_LOCK:
                    for _i, f in sorted(book._by.items()):
                        f.verdict(fuel_rank=None, drain=False, one_sided=None)
        except Exception as e:      # noqa: BLE001 -- the point is to catch any
            errors.append(e)

    w = threading.Thread(target=add, daemon=True)
    w.start()
    read()
    stop.set()
    w.join(timeout=5)
    assert not errors, errors


def test_the_lock_is_reentrant_because_the_read_side_nests():
    with server._SENSES_LOCK:
        with server._SENSES_LOCK:
            assert True


# --------------------------------------------------------------------------
# the cap the other two POSTs already had
# --------------------------------------------------------------------------

def test_the_orderbook_post_declares_the_same_kind_of_cap_as_its_siblings():
    """/api/paper_fill caps at 16384 and /api/token at 8192. /api/orderbook
    shipped with no cap at all, so a declared Content-Length of 5e9 blocked the
    handler thread forever -- there is no socket timeout -- and repeated
    connections piled up hung threads."""
    src = (server.ROOT / "server.py").read_text(encoding="utf-8")
    # Split on the NEXT handler's dispatch line, not on its name: the orderbook
    # handler's own comment cites "/api/paper_fill 16K" as the precedent it
    # follows, and slicing on the bare name cuts the body off before the cap.
    body = (src.split('startswith("/api/orderbook")')[1]
               .split('startswith("/api/paper_fill")')[0])
    assert "0 < n < " in body, "the orderbook POST must bound its body"
    assert "except ValueError" in body, "a junk Content-Length must not raise"


def test_clean_books_output_is_json_serialisable():
    """It is handed straight to a live dict the senses loop reads."""
    json.dumps(server._clean_books(
        {"1": {"depth": {"bid": [{"price": 1.0, "orders": 2}],
                         "ask": [{"price": 2.0, "orders": 3}]}}}))


# --------------------------------------------------------------------------
# the three dead gears -- fuse.verdict() never received sigma_pctl,
# vwap_flips_per_hr or walls_holding, so regime.decide() could only ever
# answer CASCADE or UNKNOWN (see regime.LEGAL) and direction.GAME could
# never surface SELL_PREMIUM (PIN) or STAND_ASIDE (TRANSITION). 12 unit
# tests on regime.decide() in isolation passed the whole time; nothing drove
# the COMPOSED path -- _view_for, the function server.py actually calls --
# with inputs able to reach either gear. This does.
# --------------------------------------------------------------------------

def _fut_bars(n, z_of, bw_r_last):
    """Synthetic `payloads[idx]["session"]["day"]["bars"]`, engine-shaped."""
    return [{"t": f"{9 + i // 60:02d}:{(15 + i) % 60:02d}",
             "fut": {"z": z_of(i), "bw_r": (bw_r_last if i == n - 1 else 0.5)}}
            for i in range(n)]


def test_composed_path_reaches_pin_and_transition():
    import fuse
    import regime

    saved = {k: server._SENSES.get(k) for k in ("fuse", "chain", "pools")}
    try:
        # --- PIN: VWAP magnetism (flips/hr >= regime.MAGNET_FLIPS) with
        # walls holding, no ignition/drain (else CASCADE would win) and no
        # TRANSITION reading (fuel_rank is None, so that branch cannot fire).
        server._SENSES["fuse"] = fuse.Book()
        server._SENSES["fuse"].for_inst("NIFTY-FUT")
        server._SENSES["chain"] = {"NIFTY": {"fuel_rank": None, "drain": False,
                                             "one_sided": None}}
        server._SENSES["pools"] = {"NIFTY-FUT": {"orders_known": True, "walls": 1}}
        payloads = {"NIFTY": {"session": {"day": {"bars":
            _fut_bars(20, lambda i: 1.0 if i % 2 == 0 else -1.0, 0.5)}}}}
        v = server._view_for("NIFTY", payloads)
        assert v is not None and v.gear == regime.PIN, v

        # --- TRANSITION: tight sigma + one-sided loaded fuel, no ignition/
        # drain (else CASCADE would win) and no VWAP flips (z held at 0, so
        # PIN cannot fire either).
        server._SENSES["fuse"] = fuse.Book()
        server._SENSES["fuse"].for_inst("NIFTY-FUT")
        server._SENSES["chain"] = {"NIFTY": {"fuel_rank": 0.9, "drain": False,
                                             "one_sided": True}}
        server._SENSES["pools"] = {"NIFTY-FUT": {"orders_known": True, "walls": 0}}
        payloads = {"NIFTY": {"session": {"day": {"bars":
            _fut_bars(20, lambda i: 0.0, 0.1)}}}}
        v = server._view_for("NIFTY", payloads)
        assert v is not None and v.gear == regime.TRANSITION, v
    finally:
        server._SENSES.update(saved)


def test_regime_engine_read_refuses_before_maturity():
    """Fewer bars than engine.MATURITY -> None with a reason, never a number
    computed off noise (constraint: absence gets a reason, never a fabricated
    value)."""
    from engine import MATURITY
    payloads = {"NIFTY": {"session": {"day": {"bars":
        _fut_bars(MATURITY - 1, lambda i: 1.0, 0.1)}}}}
    sigma_pctl, vwap_flips_per_hr, why = server._regime_engine_read(payloads, "NIFTY")
    assert sigma_pctl is None and vwap_flips_per_hr is None and why


def test_walls_holding_is_none_not_false_without_order_counts():
    """`walls` is always 0 when `orders_known` is False (pools.py cannot
    classify wall vs cluster without Kite's order counts) -- reporting that
    as walls_holding=False would be the invented zero constraint 3
    forbids."""
    holding, why = server._walls_holding(
        {"orders_known": False, "walls": 0, "shelves": 2})
    assert holding is None and why


# --------------------------------------------------------------------------
# root redirect + /api/health's feed dict -- routing exercised the same way
# test_upstox_only.py drives do_GET: no socket, no real request.
# --------------------------------------------------------------------------

class _Cap:
    """A Handler with the socket machinery removed."""

    def __init__(self, path, payloads=None, poller=None):
        self.path = path
        self.payloads = payloads or {}
        self.chains = None
        self.poller = poller
        self.sent = None
        self.status = None
        self.headers = []

    def _json(self, body, code=200):
        self.sent = json.loads(body.decode())

    def send_response(self, code):
        self.status = code

    def send_header(self, k, v):
        self.headers.append((k, v))

    def end_headers(self):
        pass


def test_root_redirects_to_the_desk():
    """start-v2.bat now opens `/`; the site root must land on the desk, not
    a directory listing or the legacy index."""
    cap = _Cap("/")
    server.Handler.do_GET(cap)
    assert cap.status == 302
    assert ("Location", "/desk.html") in cap.headers


def test_health_feed_is_none_with_a_reason_off_the_upstox_path():
    """Dhan, --mock-chain and replay mode all leave poller.src unset (or
    poller itself None) -- feed must be null with a reason, never a
    fabricated 'healthy', per constraint 3."""
    cap = _Cap("/api/health", payloads={"NIFTY": {}})
    server.Handler.do_GET(cap)
    assert cap.sent["feed"] is None
    assert cap.sent["feed_why"]


def test_health_publishes_the_wired_feed_status_verbatim():
    """upstox_feed.UpstoxFeed.status() / UpstoxChainSource.status()
    (upstox_feed.py:116-123) had zero callers; this is the first one."""
    class _Src:
        def status(self):
            return {"connected": True, "healthy": True, "age_s": 1.2,
                    "frames": 900, "reconnects": 0, "error": None}

    class _Poller:
        src = _Src()

    cap = _Cap("/api/health", payloads={"NIFTY": {}}, poller=_Poller())
    server.Handler.do_GET(cap)
    assert cap.sent["feed"] == {"connected": True, "healthy": True,
                                "age_s": 1.2, "frames": 900,
                                "reconnects": 0, "error": None}
    assert cap.sent["feed_why"] is None
