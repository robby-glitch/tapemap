"""jarvis_cmd.py -- THE COMMAND GRAMMAR every face sends text to (Jarvis v3 Task 2): the pure parser on every row of the
contract's table and the refusals, the day's state rebuilt from its file, the watches that fire once, and the server's
routes (GET /api/jarvis/card, GET / POST /api/jarvis/cmd) with `mark` / `flat` reaching her hold record through the SAME
handler the Float posts to. Every DIR is under tmp_path (conftest); the clock is held; no order path exists to test."""
import io
import json
import os
import time
from datetime import datetime

import pytest

import jarvis_cmd
import jarvis_log
import messages
import server
import telegram_out
from chain_live import IST
from test_jarvis_log import CALL, frame
from test_senses_api import _Cap

DAY = "2026-11-02"                                                       # a Monday
P = jarvis_cmd.parse
NO = "I read, I don't place."


def at(h, m, s=0):
    return datetime(2026, 11, 2, h, m, s, tzinfo=IST).timestamp()


# ---- the parser: pure, every grammar row ------------------------------------------------------------------------------

def test_parse_every_row_of_the_grammar():
    assert P("line 22750f") == {"kind": "line", "level": 22750.0, "frame": "f"}
    assert P("line 22,700s") == {"kind": "line", "level": 22700.0, "frame": "s"}
    assert P("zone 22680-22720f") == {"kind": "zone", "lo": 22680.0, "hi": 22720.0, "frame": "f"}
    assert P("zone 22,720 – 22,680s") == {"kind": "zone", "lo": 22680.0, "hi": 22720.0, "frame": "s"}
    assert P("watch 22800s") == {"kind": "watch", "level": 22800.0, "frame": "s"}
    assert P("Watch 22800F") == {"kind": "watch", "level": 22800.0, "frame": "f"}
    assert P("remove 22750") == {"kind": "remove", "level": 22750.0, "frame": None}
    assert P("clear") == {"kind": "clear"} and P("list") == {"kind": "list"}
    assert P("mark NIFTY 23000 PE buy 325") == {"kind": "mark", "idx": "NIFTY", "k": 23000.0, "side": "PE", "role": "buy",
                                                "p0": 325.0, "qty": None}
    assert P("mark SENSEX 74000 CE sell 98.85 qty 150") == {"kind": "mark", "idx": "SENSEX", "k": 74000.0, "side": "CE",
                                                            "role": "sell", "p0": 98.85, "qty": 150}
    assert P("flat") == {"kind": "flat", "idx": None} and P("flat NIFTY") == {"kind": "flat", "idx": "NIFTY"}
    assert P("note RBI 11:00 today") == {"kind": "note", "text": "RBI 11:00 today"}
    assert P("why") == P("why?") == {"kind": "why"}
    assert P("next") == P("what next") == {"kind": "next"}
    assert P("status") == P("now") == {"kind": "status"}
    assert P("wrong when") == P("wrong when?") == {"kind": "wrong"}
    assert P("what if 22800 breaks") == P("if 22800") == {"kind": "whatif", "level": 22800.0, "frame": None}
    assert P("what if 23,043f breaks?") == {"kind": "whatif", "level": 23043.0, "frame": "f"}
    assert P("ask is the floor holding") == {"kind": "ask", "text": "is the floor holding"}
    assert P("replay 2026-10-21 10:30") == {"kind": "replay", "day": "2026-10-21", "upto": "10:30"}


def test_an_order_word_is_refused_and_anything_else_gets_the_grammar():
    for t in ("buy 5 lots", "sell PE", "place order", "square off now", "exit now", "go long here", "1 lot more",
              "note sell above 23000", "mark NIFTY 23000 PE buy 325 5 lots", "note selling above 23000",
              "selling the CE now", "placing orders", "square my position", "squareoff", "go short", "short it",
              "long it", "buying here", "sells", "buys here", "note sells above 23000", "shorting here", "going long",
              "going short", "places an order"):
        assert P(t) == {"kind": "refused", "reply": NO}, t
    # her OI words are never orders: short covering, long unwinding (the review's ruling)
    assert P("note short covering at 23000") == {"kind": "note", "text": "short covering at 23000"}
    assert P("note long unwinding") == {"kind": "note", "text": "long unwinding"}
    assert P("note fresh shorts at 23000") == {"kind": "note", "text": "fresh shorts at 23000"}     # a noun, not a verb
    # a question is not an order, and "lot" is an order word only after a number (the coordinator's resolution)
    assert P("ask what happens if sellers get trapped") == {"kind": "ask", "text": "what happens if sellers get trapped"}
    assert P("note a lot of writing at 23000") == {"kind": "note", "text": "a lot of writing at 23000"}
    assert P("ask should I buy here")["kind"] == "ask" and P("why buy")["kind"] == "help"
    assert P("mark NIFTY 23000 PE long 325") == P("mark NIFTY 23000 PE buy 325")         # long / short name her side too
    for t in ("hello", "", "   "):
        assert P(t)["kind"] == "help"
    assert P("mark NIFTY 23000 PE 325")["kind"] == "mark" and "error" in P("mark NIFTY 23000 PE 325")   # buy or sell named
    assert "error" in P("line 22750") and "error" in P("watch 22800")                  # every level says s or f
    assert jarvis_cmd.for_telegram("/watch@tapemap_x_bot 22800s") == ("NIFTY", "watch 22800s")
    assert jarvis_cmd.for_telegram("SENSEX status") == ("SENSEX", "status")
    assert jarvis_cmd.for_telegram("flat NIFTY") == ("NIFTY", "flat NIFTY")


# ---- the day: persisted, rebuilt, read-only answers from the frame ----------------------------------------------------

FR = frame(timeline=[{"fronts": [{"k": k, "side": s, "state": "BUILDING", "oi": oi} for k, s, oi in
                                 ((22750, "PE", 60.0), (22850, "PE", 90.0), (22900, "PE", 186.0), (23000, "CE", 147.0),
                                  (23100, "CE", 80.0))]}])


def _disk():
    p = os.path.join(jarvis_cmd.DIR, f"cmd_{DAY}.jsonl")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(x) for x in f]


def test_the_drawing_commands_persist_and_a_restart_rebuilds_the_same_state():
    d = jarvis_cmd.Day(DAY)
    a = lambda t, idx="NIFTY", s=0: d.apply(idx, t, FR, "page", now=at(10, 12, s))   # noqa: E731
    assert a("line 22750f")["reply"] == "line 22,750f drawn"
    assert a("zone 22680-22720f")["reply"] == "zone 22,680–22,720f drawn"
    r = a("watch 22800s")
    assert (r["ok"], r["kind"], r["reply"]) == (True, "watch", "watching 22,800s (1 of 10 today)")
    assert r["state"]["watches"] == [{"id": 1, "level": 22800.0, "frame": "s", "set": "10:12", "hit": None}]
    dup = a("watch 22800s")
    assert dup["reply"] == "already watching 22,800s" and not dup["ok"]
    assert a("watch 74000s", "SENSEX")["reply"] == "watching 74,000s (2 of 10 today)"   # 10 a day, every index
    assert a("note RBI 11:00 today")["reply"] == "noted" and d.notes() == ["note 10:12 RBI 11:00 today"]
    assert a("remove 22750")["reply"] == "removed 22,750"
    gone = a("remove 22750")
    assert not gone["ok"] and gone["reply"] == "nothing at 22,750"
    assert a("buy 5 lots")["reply"] == NO
    st = d.state("NIFTY")
    assert st["lines"] == [] and st["zones"] == [{"id": 1, "lo": 22680.0, "hi": 22720.0, "frame": "f", "set": "10:12"}]
    assert a("line 22700s")["state"]["lines"] == [{"id": 2, "level": 22700.0, "frame": "s", "set": "10:12"}]   # ids per day
    assert a("remove 22700s")["ok"]
    rows = _disk()
    assert [r["kind"] for r in rows] == ["line", "zone", "watch", "watch", "watch", "note", "remove", "remove",
                                         "refused", "line", "remove"]                # a refused or failed one too
    assert set(rows[0]) >= {"at", "t", "idx", "kind", "text", "ok", "reply", "src"} and rows[0]["src"] == "page"
    assert rows[8] == dict(rows[8], kind="refused", text="buy 5 lots", ok=False, reply=NO)
    assert jarvis_cmd.Day(DAY).state("NIFTY") == st and jarvis_cmd.Day(DAY).notes() == d.notes()   # anytime-start
    ls = a("list")
    assert ls["lines"] == ["zone 22,680–22,720f · set 10:12", "watch 22,800s · set 10:12"] and len(_disk()) == 11  # not persisted
    assert a("clear")["reply"] == "cleared 2" and d.state("NIFTY") == {"watches": [], "lines": [], "zones": []}
    assert d.state("SENSEX")["watches"][0]["level"] == 74000.0                       # clear is one index's


def test_ten_watches_a_day_then_the_limit_says_so():
    d = jarvis_cmd.Day(DAY)
    for i in range(10):
        assert d.apply("NIFTY", f"watch {22000 + 50 * i}s", None, "cli", now=at(10, 0))["ok"]
    d.apply("NIFTY", "clear", None, "cli", now=at(10, 1))
    r = d.apply("NIFTY", "watch 23000s", None, "cli", now=at(10, 2))
    assert not r["ok"] and r["reply"] == "10 watches today already — the day's limit"


def test_notes_are_capped_at_200_characters_and_10_a_day():
    d = jarvis_cmd.Day(DAY)
    assert d.apply("NIFTY", "note " + "x" * 300, None, "telegram", now=at(10, 0))["ok"]
    assert d.notes()[0] == "note 10:00 " + "x" * 200
    for i in range(9):
        assert d.apply("NIFTY", f"note n{i}", None, "page", now=at(10, 1))["ok"]
    r = d.apply("NIFTY", "note one too many", None, "telegram", now=at(10, 2))
    assert not r["ok"] and r["reply"] == "10 notes today already — the day's limit" and len(d.notes()) == 10
    assert len(jarvis_cmd.Day(DAY).notes()) == 10


def test_the_read_only_commands_answer_from_the_frame_verbatim():
    d = jarvis_cmd.Day(DAY)
    a = lambda t, f=FR: d.apply("NIFTY", t, f, "page", now=at(10, 43))               # noqa: E731
    assert a("why")["lines"] == CALL["why"]
    assert a("next")["lines"] == [CALL["up"], CALL["dn"]]
    assert a("wrong when?")["reply"] == CALL["wrong_line"]
    assert a("status")["lines"] == ["TREND ▼ · HOLD · since 09:56", "WITH 4 · AGAINST 1 · N 6 · unread 2",
                                    "leg ▼ TREND 103 pts", "health: " + " · ".join(CALL["missing"])]
    assert a("what if 23000 breaks")["lines"] == [CALL["up"], "CE wall 23,000s (23,043f) 147L BUILDING"]
    assert a("if 22943f")["lines"] == [CALL["dn"], "PE wall 22,900s (22,943f) 186L BUILDING"]
    assert a("if 22800")["reply"] == "I don't have 22,800 in today's frame; nearest: 22,850s PE, 22,750s PE"
    assert a("if 23100")["lines"] == ["23,100s CE 80L BUILDING · not the first wall ahead: no scenario"]
    ask = a("ask is the floor holding")
    assert ask["reply"] == "voice not configured — the engine's lines:" and ask["lines"] == CALL["why"]
    assert not a("replay 2026-10-21 10:30")["ok"] and "terminal" in a("replay 2026-10-21 10:30")["reply"]
    h = a("hello")
    assert (h["ok"], h["kind"], h["reply"], h["lines"]) == (True, "help", "commands:", jarvis_cmd.HELP)
    bare = frame({"at": "10:42", "word": "HOLD ▼"})                                  # no count, no missing list
    assert a("status", bare)["lines"] == ["HOLD ▼", "could not check — count absent", "leg: none in this frame",
                                          "health: could not check — no missing list in this frame"]
    assert a("status", frame(dict(CALL, missing=[])))["lines"][3] == "health: every source live"   # only on []
    assert "None" not in json.dumps([a(t, bare) for t in ("status", "why", "next", "wrong when")], ensure_ascii=False)
    none = a("why", None)
    assert not none["ok"] and none["reply"] == "could not check — no frame built yet"
    assert _disk() == []                                                             # nothing read-only is persisted
    assert "%" not in json.dumps([a(t) for t in ("why", "next", "status", "wrong when", "if 22800")], ensure_ascii=False)


def test_a_watch_fires_once_on_the_touch_and_writes_its_hit_with_the_card():
    d = jarvis_cmd.Day(DAY)
    d.apply("NIFTY", "watch 22800s", None, "page", now=at(10, 12))
    d.apply("NIFTY", "watch 22900f", None, "page", now=at(10, 12))
    assert d.armed()
    card = lambda: {"word": "TREND ▼", "count": {"with": 4, "against": 1, "N": 5}, "answer": "last answer 10:38 x"}  # noqa: E731
    assert d.check_watches("NIFTY", 22830.0, 22880.0, "11:40", card, now=at(11, 40)) == []   # the first look: no touch yet
    assert d.check_watches("NIFTY", None, None, "11:41", card) == []                  # a missing price is skipped, never a 0
    hits = d.check_watches("NIFTY", 22799.6, 22880.0, "11:42", card, now=at(11, 42))
    assert [(h["id"], h["frame"], h["px"], h["t"]) for h in hits] == [(1, "s", 22799.6, "11:42")]
    assert hits[0]["card"] == card() and hits[0]["kind"] == "watch_hit"
    assert d.check_watches("NIFTY", 22850.0, 22880.0, "11:43", card) == []           # fires once
    assert [h["id"] for h in d.check_watches("NIFTY", 22850.0, 22901.0, "11:44", card)] == [2]   # f: the future's price
    assert d.state("NIFTY")["watches"][0]["hit"] == "11:42" and not d.armed()
    assert [r["kind"] for r in _disk()][-2:] == ["watch_hit", "watch_hit"]
    assert jarvis_cmd.Day(DAY).state("NIFTY") == d.state("NIFTY")                    # a restart keeps the hits
    m = messages.jarvis([], [hits[0]])
    assert d.apply("NIFTY", "list", None, "page", now=at(11, 45))["lines"][0] == "watch 22,800s · hit 11:42 @22,799.6s"
    assert [x["line"] for x in m] == ["11:42  NIFTY  WATCH 22,800s hit @22,799.6s · TREND ▼ · WITH 4 · AGAINST 1 · "
                                      "last answer 10:38 x"]
    assert telegram_out.wants(m[0])                                                    # the hit reaches her phone


# ---- the server: the routes, the hold record, the senses hook, health -------------------------------------------------

class _Post(_Cap):
    def __init__(self, path, body):
        super().__init__(path)
        raw = json.dumps(body).encode()
        self.headers = {"Content-Length": str(len(raw))}
        self.rfile = io.BytesIO(raw)


@pytest.fixture
def srv(monkeypatch):
    clock = {"now": datetime(2026, 11, 2, 10, 42, 30, tzinfo=IST)}
    monkeypatch.setattr(server, "_ist", lambda now=None: clock["now"])
    monkeypatch.setattr(server, "_JARVIS", {})
    monkeypatch.setattr(server, "_JCMD", {})
    monkeypatch.setattr(server, "_MSG", server._msg_fresh())
    monkeypatch.setattr(server, "_HOLD", {"facts": {}, "locks": {}, "trades": [], "trades_day": None, "sigma": {}, "peaks": {}})
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "10:42"))
    return clock


def get(path):
    cap = _Cap(path)
    server.Handler.do_GET(cap)
    return cap.sent


def post(path, body):
    cap = _Post(path, body)
    server.Handler.do_POST(cap)
    return cap.sent


def test_the_card_route_serves_the_cached_live_frame_only(srv):
    assert get("/api/jarvis/card?idx=NIFTY") == {"ok": False, "why": "could not check — no frame built yet"}
    server._JARVIS["NIFTY"] = (("NIFTY", DAY, None, False), time.time(), FR)
    c = get("/api/jarvis/card?idx=nifty")
    assert c["ok"] and c["word"] == "TREND ▼" and c["count"]["with"] == 4 and c["watches"] == []
    want = json.loads(json.dumps(jarvis_log.card(FR, [], {"watches": [], "lines": [], "zones": []}, []), default=str))
    skip = ("voice", "brief")                                                       # the server's own (Task 7's voice)
    assert {k: v for k, v in c.items() if k not in skip} == {k: v for k, v in want.items() if k not in skip}
    assert all(k in c for k in skip)
    assert not get("/api/jarvis/card?idx=FINNIFTY")["ok"]


def test_the_cmd_route_draws_a_watch_and_mark_and_flat_reach_her_hold_record(srv):
    r = post("/api/jarvis/cmd", {"idx": "NIFTY", "text": "watch 22800s"})
    assert r["ok"] and r["reply"] == "watching 22,800s (1 of 10 today)"
    assert get("/api/jarvis/cmd?idx=NIFTY")["state"]["watches"][0]["level"] == 22800.0
    assert _disk()[0]["src"] == "page"
    m = post("/api/jarvis/cmd", {"idx": "NIFTY", "text": "mark NIFTY 23000 PE buy 325 qty 150", "src": "cli"})
    tr = server._hold_trades()
    assert len(tr) == 1 and (tr[0]["idx"], tr[0]["k"], tr[0]["side"], tr[0]["role"], tr[0]["p0"], tr[0]["qty"]) == \
        ("NIFTY", 23000.0, "PE", "long", 325.0, 150)
    assert tr[0]["t0"] == "10:42:30" and tr[0]["src"] == "marked" and tr[0]["via"] == "cmd"   # a live marked trade, by the cmd
    assert m["ok"] and m["reply"] == f"marked NIFTY 23000 PE buy @325 · the voice is on · id {tr[0]['id']}"
    again = post("/api/jarvis/cmd", {"idx": "NIFTY", "text": "mark NIFTY 23000 PE buy 330"})
    assert not again["ok"] and tr[0]["id"] in again["reply"] and len(server._hold_trades()) == 1   # her open mark stands
    empty = {"watches": [], "lines": [], "zones": []}
    unk = post("/api/jarvis/cmd", {"idx": "FINNIFTY", "text": "watch 22800s"})
    assert not unk["ok"] and unk["state"] == empty and unk["why"] == unk["reply"]           # the contract's shape, empty
    assert get("/api/jarvis/cmd?idx=FINNIFTY")["state"] == empty
    bad = post("/api/jarvis/cmd", {"idx": "NIFTY", "text": "mark FINNIFTY 23000 PE buy 330"})
    assert bad["kind"] == "mark" and not bad["ok"] and bad["reply"].startswith("mark NIFTY|SENSEX|BANKNIFTY")
    srv["now"] = datetime(2026, 11, 2, 11, 42, 5, tzinfo=IST)
    f = post("/api/jarvis/cmd", {"idx": "NIFTY", "text": "flat NIFTY"})
    assert f["ok"] and f["reply"] == "flat · receipt 11:42" and server._hold_trades()[0]["exit_t"] == "11:42:05"
    assert not post("/api/jarvis/cmd", {"idx": "NIFTY", "text": "flat"})["ok"]          # nothing open
    assert [r["kind"] for r in _disk()] == ["watch", "mark", "mark", "mark", "flat", "flat"]
    assert _disk()[1]["src"] == "cli" and _disk()[1]["id"] == tr[0]["id"]
    assert post("/api/jarvis/cmd", {"idx": "NIFTY", "text": "buy 5 lots"})["reply"] == NO
    assert len(server._hold_trades()) == 1                                               # an order word touches nothing


def test_the_hold_door_still_marks_through_the_one_handler(srv):
    """The Float's own POST /api/hold/trades runs the handler jarvis_cmd now calls (moved, not copied)."""
    doc = {"op": "mark", "idx": "NIFTY", "k": 23000, "side": "PE", "role": "long", "t0": "10:40:00", "p0": 300, "qty": 75}
    out = post("/api/hold/trades", doc)
    assert out["ok"] and len(out["trades"]) == 1 and "via" not in out["trades"][0]
    r = post("/api/jarvis/cmd", {"idx": "NIFTY", "text": "mark NIFTY 23000 PE buy 325"})
    assert not r["ok"] and "already marked" in r["reply"] and len(server._hold_trades()) == 1   # her Float mark wins


def test_the_senses_hook_fires_a_watch_into_the_stream_and_never_raises(srv, monkeypatch):
    post("/api/jarvis/cmd", {"idx": "NIFTY", "text": "watch 22800s"})
    server._JARVIS["NIFTY"] = (("NIFTY", DAY, None, False), time.time(), FR)
    boxes = {"NIFTY": {"spot": 22830.0}}
    server._jarvis_watch(boxes, {}, {})
    boxes["NIFTY"]["spot"] = 22799.0
    server._jarvis_watch(boxes, {}, {})
    hit = [m for m in server._MSG["items"] if m["kind"] == "JARVIS"]
    assert [m["line"] for m in hit] == ["10:42  NIFTY  WATCH 22,800s hit @22,799s · TREND ▼ · WITH 4 · AGAINST 1 · "
                                        "last answer 10:38 22,950s PE ±2 BROKEN"]
    monkeypatch.setattr(jarvis_cmd.Day, "armed", lambda self: 1 / 0)
    server._jarvis_watch(boxes, {}, {})                                                  # a broken watch never stops the pass


def test_health_names_the_code_changed_since_this_process_started(monkeypatch):
    monkeypatch.setattr(server, "_STARTED", time.time() + 10 ** 9)
    assert get("/api/health")["code_changed_since_start"] == {"n": 0, "files": []}
    monkeypatch.setattr(server, "_STARTED", 0.0)
    got = get("/api/health")["code_changed_since_start"]
    assert "server.py" in got["files"] and got["n"] == len(got["files"])
    assert not any(f.startswith("test_") or f == "conftest.py" for f in got["files"])


class _Hdr(_Cap):
    """A handler whose REQUEST headers are a dict and whose sent headers are kept apart (the CORS reads both)."""
    _cors, ALLOW_ORIGIN = server.Handler._cors, server.Handler.ALLOW_ORIGIN

    def __init__(self, path, origin, site=None, body=None):
        super().__init__(path)
        raw = json.dumps(body or {}).encode()
        self.headers = {"Origin": origin, "Content-Length": str(len(raw)), **({"Sec-Fetch-Site": site} if site else {})}
        self.rfile, self.wfile, self.out = io.BytesIO(raw), io.BytesIO(), []

    def send_header(self, k, v):
        self.out.append((k, v))


def test_her_page_and_the_extension_may_call_the_jarvis_routes_across_origins(srv):
    """The page is served from 8787 (localhost or 127.0.0.1) and polls through Vite on 5173; the Dext extension posts from
    its chrome-extension:// origin. Those origins get the CORS answer on the two Jarvis routes (the preflight too); any
    other site gets none, and its cross-site POST is refused. The hold doors keep their own rule."""
    def opt(path, origin):
        cap = _Hdr(path, origin)
        server.Handler.do_OPTIONS(cap)
        return dict(cap.out).get("Access-Control-Allow-Origin")
    for o in ("http://localhost:8787", "http://127.0.0.1:8787", "http://localhost:5173", "chrome-extension://abcdef"):
        assert opt("/api/jarvis/cmd", o) == o and opt("/api/jarvis/card?idx=NIFTY", o) == o
    assert opt("/api/jarvis/cmd", "https://evil.example") is None and opt("/api/hold/trades", "http://localhost:8787") is None
    cap = _Hdr("/api/jarvis/card?idx=NIFTY", "http://127.0.0.1:8787")
    server.Handler._json(cap, b"{}")                                                  # the GET's own reply carries it
    assert ("Access-Control-Allow-Origin", "http://127.0.0.1:8787") in cap.out

    def send(origin):
        cap = _Hdr("/api/jarvis/cmd", origin, "cross-site", {"idx": "NIFTY", "text": "watch 22800s"})
        server.Handler.do_POST(cap)
        return cap.sent
    assert send("https://evil.example") == {"ok": False, "why": "refused — a POST from another site"}
    assert send("http://localhost:8787")["reply"] == "watching 22,800s (1 of 10 today)"   # localhost page -> 127.0.0.1 server
    no = _Hdr("/api/jarvis/cmd", "", None, {"idx": "NIFTY", "text": "sell PE"})
    server.Handler.do_POST(no)
    assert no.sent == dict(no.sent, ok=False, kind="refused", reply=NO, why=NO)          # a refusal is a 200 answer, said


def test_a_watch_crossed_while_the_server_was_down_says_could_not_check_once():
    """A restart cannot know a touch it did not see. A watch set before this process (rebuilt from the file) whose price
    is on the other side of its level at the first look says `could not check — gap <set>–<now>` once, never a hit; a
    watch set in this process compares its first look with its set-time price (I6): crossed = a hit, never a gap."""
    d = jarvis_cmd.Day(DAY)
    d.apply("NIFTY", "watch 22800s", FR, "page", now=at(10, 12))                     # spot 22,967.3 when set: above
    d.apply("NIFTY", "watch 23100f", FR, "page", now=at(10, 12))                     # fut 23,010.5 when set: below
    d2 = jarvis_cmd.Day(DAY)                                                          # a restart
    rows = d2.check_watches("NIFTY", 22750.0, 23050.0, "11:40", now=at(11, 40))
    assert [(r["kind"], r["id"], r["gap"]) for r in rows] == [("watch_gap", 1, "10:12–11:40")]   # 23,100f never crossed
    assert d2.check_watches("NIFTY", 22700.0, 23050.0, "11:41") == []               # said once
    st = jarvis_cmd.Day(DAY).state("NIFTY")["watches"]
    assert st[0]["gap"] == "10:12–11:40" and st[0]["hit"] is None and "gap" not in st[1]
    assert [m["line"] for m in messages.jarvis([], rows)] == ["11:40  NIFTY  WATCH 22,800s · could not check — gap 10:12–11:40"]
    d2.apply("NIFTY", "watch 22600s", FR, "page", now=at(11, 42))                   # set in THIS process, spot 22,967.3
    assert [r["kind"] for r in d2.check_watches("NIFTY", 22550.0, None, "11:43")] == ["watch_hit"]   # crossed: a touch


def test_a_watch_set_near_price_fires_on_a_cross_before_its_first_look():
    """I6 (final review): watch 22800s set at spot 22,798 (2 pts below the level); price is 22,803 by the first senses
    pass. The crossing between the set-time price and the first look is a touch: it fires once, never silently missed."""
    d = jarvis_cmd.Day(DAY)
    d.apply("NIFTY", "watch 22800s", dict(FR, spot=[22797.0, 22798.0]), "page", now=at(10, 12))
    card = lambda: {"word": "TREND ▲", "count": None, "answer": None}               # noqa: E731
    hits = d.check_watches("NIFTY", 22803.0, None, "10:13", card, now=at(10, 13))
    assert [(h["kind"], h["id"], h["px"]) for h in hits] == [("watch_hit", 1, 22803.0)]
    assert d.check_watches("NIFTY", 22805.0, None, "10:14", card) == []              # fires once
    d.apply("NIFTY", "watch 22900s", dict(FR, spot=[22798.0]), "page", now=at(10, 15))
    assert d.check_watches("NIFTY", 22810.0, None, "10:16", card) == []              # not crossed: nothing


def test_a_watch_set_with_no_frame_takes_its_first_price_and_a_failed_write_is_looked_at_again():
    d = jarvis_cmd.Day(DAY)
    d.apply("NIFTY", "watch 22800s", None, "page", now=at(10, 12))                   # no frame yet: no set-time price
    assert d.check_watches("NIFTY", 22850.0, None, "10:13", now=at(10, 13)) == []    # the first price seen is kept
    assert _disk()[-1] == dict(_disk()[-1], kind="watch_px0", id=1, px0=22850.0)
    gone = jarvis_cmd.Day(DAY)                                                        # a restart, the price now below
    assert [r["kind"] for r in gone.check_watches("NIFTY", 22790.0, None, "11:00", now=at(11, 0))] == ["watch_gap"]

    d = jarvis_cmd.Day("2026-11-03")
    d.apply("NIFTY", "watch 23000s", FR, "page", now=at(10, 12))
    assert d.check_watches("NIFTY", 22980.0, None, "10:13") == []                    # set at 22,967.3s: still below
    real = d._write

    def full(r):
        raise OSError("disk full")
    d._write = full
    with pytest.raises(OSError):
        d.check_watches("NIFTY", 23010.0, None, "10:14")                              # the touch could not be written
    d._write = real
    assert [h["id"] for h in d.check_watches("NIFTY", 23010.0, None, "10:15")] == [1]   # so the next pass sees it again
