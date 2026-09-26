"""THE EXPRESSION's server half (EXPRESSION-PREREG.md rev e §A.2, §B, §E.3, §F.1) on the board's frozen NIFTY 09-24
grid, with the clock held and every REST / disk feeder replaced (test_hold_route's fixtures). Plumbing only: what the
rules say is test_expression.py's job. Nothing here reaches the live server or data/."""
import os

import expression
import hold
import hold_log
import server
from test_board import fx  # noqa: F401  (the module fixture)
from test_hold_route import DAY, _check_rows, _get, _lines, _post, pre, srv  # noqa: F401

Q = "/api/hold/check?idx=NIFTY&k={k}&side={s}&role={r}&p0=100"


def test_a_writer_press_gets_the_writers_word_and_a_2W_row(pre):
    a = _get(Q.format(k=23150, s="PE", r="short") + "&log=1", pre)
    v = a["validate"]
    assert v["rev"] == "2W" and v["word"] in ("GO", "WAIT", "NO")
    assert [f["name"] for f in v["facts"]] == list(expression.W_NAMES)
    assert v["count"].endswith("— of 4, a count, not odds") and v["draft"] == expression.DRAFT
    p = _check_rows()[0]
    assert (p["rev"], p["role"], p["word"], p["d"]) == ("2W", "short", v["word"], 1)
    assert [x[0] for x in p["facts"]] == list(expression.W_NAMES) and p["paid"] is None
    assert set(p["writer"]) == {"X", "P", "L", "line", "noise", "beyond_strike", "stratum"}
    assert isinstance(p["writer"]["beyond_strike"], bool) and p["after_1500"] is False
    assert p["expr"]["read_at"] == "13:02" and set(p["expr"]) >= {"word", "named_by", "refusal", "since", "nb", "ns",
                                                                  "facts", "legs"}


def test_a_buyer_press_keeps_rev_2_and_gains_only_additive_keys(pre):
    a = _get(Q.format(k=23200, s="PE", r="long") + "&log=1", pre)
    assert a["validate"]["rev"] == "2" and len(a["validate"]["facts"]) == 4
    p = _check_rows()[0]
    assert p["rev"] == "2" and p["facts"][0][0] == "Your setup" and "writer" not in p
    assert p["expr"]["word"] == a["expr"]["word"] and p["after_1500"] is False


def test_the_press_shows_the_last_closes_word_and_both_legs_at_its_ATM(pre):
    """§A.2: a press between closes shows the last close's word, labelled; §F.1: BUY left, SELL right, one strike."""
    x = _get(Q.format(k=23200, s="PE", r="long"), pre)["expr"]
    assert x["ok"] and x["read_at"] == "13:02" and x["dir"] == "DOWN" and x["prereg"] == "expr-e"
    assert x["buy"]["side"] == "PE" and x["sell"]["side"] == "CE" and x["buy"]["k"] == x["sell"]["k"]
    assert x["buy"]["px_t"] == "13:04" and x["buy"]["validate"]["rev"] == "2" and x["sell"]["validate"]["rev"] == "2W"
    assert [f["name"] for f in x["facts"]] == list(expression.NAMES) and x["count"].endswith("a count, not odds")
    assert x["nb"] + x["ns"] + x["nn"] == 5 and x["since"] <= "13:02"
    assert x["not_shown"] == expression.NOT_SHOWN_LINES and set(x["printed"]) == {"drag", "expiry", "regime"}
    assert x["buy"]["named"] == (x["base"] in ("BUY", "LEANS BUY")) and x["sell"]["named"] == (x["base"] in ("SELL", "LEANS SELL"))
    up = _get(Q.format(k=23200, s="PE", r="short"), pre)["expr"]              # a short PE is UP: BUY CE vs SELL PE
    assert up["dir"] == "UP" and up["buy"]["side"] == "CE" and up["sell"]["side"] == "PE"


def test_the_tick_writes_the_expression_log_once_and_its_outcomes(srv):
    n = server._hold_tick(srv, "NIFTY")
    rows = [r for r in _lines("expr") if r["kind"] == "expr"]
    assert len(rows) == 125 * 2 and {r["prereg"] for r in rows} == {"expr-e"}
    assert [r["t"] for r in rows if r["d"] == 1] == [t for t in hold.SESSION if hold.is_close(t)]
    assert all(r["after_1500"] == (r["t"] >= "15:00") and r["unit"] == expression.is_unit(r["t"]) for r in rows)
    assert all(set(r) >= {"word", "strength", "lead", "named_by", "refusal", "since", "was", "nb", "ns", "facts", "buy",
                          "sell", "S", "line", "noise", "regime_board", "drag", "expiry_line", "blind", "word_1m"}
               for r in rows)
    out = [r for r in _lines("expr") if r["kind"] == "expr_outcome"]
    assert len(out) == 12 * 2 and all(r["writer"] is None or isinstance(r["writer"]["beyond_strike"], bool) for r in out)
    assert {r["t"] for r in out} == {t for t in hold.SESSION if expression.is_unit(t)}
    assert n == len(_lines("side"))                  # the window's own count: no expression row in it (no trade marked)
    before = len(_lines("expr"))
    server._hold_tick(srv, "NIFTY")
    assert len(_lines("expr")) == before                                        # write-once


def test_the_import_leaves_the_expression_to_the_hold_thread(srv):
    got = _post("/api/hold/import", b"", srv)
    assert got["ok"] and not os.path.exists(hold_log.path("expr", DAY))         # nothing heavy on the request
    assert server._HOLD.pop("expr_complete") is True
    server._expr_complete(srv)                                                   # what the loop's thread runs
    assert len([r for r in _lines("expr") if r["kind"] == "expr"]) == 250


def test_a_long_CE_and_a_short_PE_at_one_minute_get_two_outcome_rows(pre, monkeypatch):
    """§B.3: they share d (UP), so the outcome key gains role; the writer's row waits until both horizons are known."""
    _get(Q.format(k=23150, s="CE", r="long") + "&log=1", pre)
    _get(Q.format(k=23150, s="PE", r="short") + "&log=1", pre)
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "15:45"))
    server._hold_tick(pre, "NIFTY")
    out = [r for r in _check_rows() if r.get("kind") == "check_outcome"]
    assert sorted(r.get("role", "long") for r in out) == ["long", "short"] and {r["d"] for r in out} == {1}
    w = next(r for r in out if r.get("role") == "short")
    assert w["first_30"] and w["first_1529"] and set(w["target"]) == {"P", "X", "level"} and w["after_1500"] is False
    assert "role" not in next(r for r in out if r.get("role") is None)          # the buyer's row does not move
    server._hold_tick(pre, "NIFTY")
    assert len([r for r in _check_rows() if r.get("kind") == "check_outcome"]) == 2


def test_the_setup_line_route_reads_no_close(pre):
    a = _get("/api/hold/expr?idx=NIFTY", pre)
    assert a["ok"] and a["asof"] == "13:04" and "setup_line" in a
    assert not server._HOLD.get("expr")                                          # no close was read for it


def test_an_expression_failure_never_costs_the_buyers_word(pre, monkeypatch):
    """A fault in the expression costs its block only: the buyer's VALIDATE answers as signed, and a writer press
    falls back to VALIDATE rev 2 §1.6's writer screen (§A.7) -- never a failed check."""
    def boom(*a):
        raise RuntimeError("test")
    monkeypatch.setattr(server, "_expr_press", boom)
    a = _get(Q.format(k=23200, s="PE", r="long"), pre)
    assert a["ok"] and a["validate"]["rev"] == "2" and a["validate"]["word"] in ("GO", "WAIT", "NO")
    assert a["expr"]["ok"] is False and a["expr"]["why"].startswith("could not check — the expression could not be read")
    w = _get(Q.format(k=23150, s="PE", r="short"), pre)
    assert w["ok"] and w["validate"]["word"] is None and w["validate"]["writer_note"]
