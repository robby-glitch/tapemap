"""tools/jarvis_cli.py: the terminal Jarvis -- the card as a fixed-width block, the command line, offline on a saved frame."""
import io
import json
import os
import sys
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import jarvis_cli  # noqa: E402

# the CARD contract's example (v3-common-brief.md), verbatim
CARD = json.loads("""
{"ok": true, "idx": "NIFTY", "day": "2026-11-02", "at": "10:42", "asof": "10:42:51", "live": true,
 "word": "TREND ▼", "state": "HOLD", "lean": -1, "since": "09:56",
 "count": {"with": 4, "against": 1, "N": 6, "unread": 2,
           "pieces": [{"k": "sides", "side": "with", "text": "Sides 10:40 REAL · put writers covering"},
                      {"k": "wf7", "side": "with", "text": "writers ±7 DOWN (CE +12.1L · PE −14.0L / 3 min)"},
                      {"k": "wall_ahead", "side": "against", "text": "wall ahead 22,900s PE 186L BUILDING"},
                      {"k": "answer", "side": "with", "text": "last answer 10:38 22,950s PE ±2 BROKEN"},
                      {"k": "trapped", "side": "?", "text": "could not check — Sides has no closed slot"},
                      {"k": "fut_oi", "side": "with", "text": "fut OI fresh shorts +612 lots / 30 min"},
                      {"k": "speed", "side": "against", "text": "speed ▲ ×2.3 FAST against"},
                      {"k": "all3", "side": "with", "text": "all 3 ▼ (N −14 · BN −31 · SX −52 / 5 min)"},
                      {"k": "setup", "side": "?", "text": "no trigger today"}]},
 "leg": "leg ▼ TREND 103 pts · 2.5σ · TOOT 09:51 · origin 23,135f 09:35 · extreme 23,002f 10:04",
 "pause": {"line": "PAUSE ▼ · hold · clean", "alive": ["…"], "risk": ["…"]},
 "how_much": {"line": "day TREND ▼ · range used 0.5 of EM · σ 26 · VIX could not check · CPR narrow", "rows": ["…"]},
 "where": {"stop": "23,136f (zone)", "pool": "PWH 23,155s", "t1": "pVAH 23,058f", "t2": "PE wall 23,008s (23,051f)", "room": "44 to MAX PAIN"},
 "expression": {"buyer": "buy the PE on a pullback to d1 22,990f, not chased · needs +62 pts today [I ×1.15] · EM left 40 → thin",
                "seller": "sell the CE at / above 23,000s (23,043f): call writers are writing it · IV 13.4 vs RV 9.8 → rich · fold = HOLD v2 line",
                "pick": "seller"},
 "wrong_line": "PALAT? if back past 22,938f (0.35 of the leg) · PALAT at 22,886f",
 "up": "▲ if 23,000s (23,043f) CE breaks (BROKEN) with writers ±7 ▲ → 23,100s", "dn": "▼ if …",
 "walls": {"ce": {"k": 23000, "f": 23043.0, "oi": 147.0, "state": "BUILDING"}, "pe": {"k": 22900, "f": 22943.0, "oi": 186.0, "state": "BUILDING"}},
 "lines": {"q35": 22938.0, "half": 22886.0},
 "no_trade": null,
 "health": {"missing": [], "notes": ["Dext footprint missing since 10:39 · newest 3 min from the book"]},
 "self": "TREND ▼ since 09:56 · −200 so far · PALAT? said 3× · came true 0× · blind 0 min",
 "pushes": [{"t": "10:38", "dir": -1, "lots": -612, "k": 22950, "side": "PE", "ans": "TOOT", "held_at": "10:41", "via": "band"}],
 "watches": [{"id": 3, "level": 22800.0, "frame": "s", "set": "10:12", "hit": null}],
 "voice": null}
""")


def test_render_card_on_the_contract_example():
    out = jarvis_cli.render_card(CARD)
    lines = out.splitlines()
    assert lines[0] == "NIFTY · 2026-11-02 · 10:42 · live · asof 10:42:51"
    assert "WORD      TREND ▼ · HOLD · since 09:56" in lines
    assert "COUNT     WITH 4 · AGAINST 1 · N 6 · unread 2" in lines
    assert "  against wall ahead 22,900s PE 186L BUILDING" in lines          # the pieces, verbatim, writers first
    assert "  ?       could not check — Sides has no closed slot" in lines
    assert "BUYER     buy the PE on a pullback to d1 22,990f, not chased · needs +62 pts today [I ×1.15] · EM left 40 → thin" in lines
    assert ("SELLER    sell the CE at / above 23,000s (23,043f): call writers are writing it · IV 13.4 vs RV 9.8 → rich"
            " · fold = HOLD v2 line") in lines
    assert "PICK      seller" in lines
    assert "WHERE     stop 23,136f (zone) · pool PWH 23,155s · t1 pVAH 23,058f · t2 PE wall 23,008s (23,051f) · room 44 to MAX PAIN" in lines
    assert "WRONG     PALAT? if back past 22,938f (0.35 of the leg) · PALAT at 22,886f" in lines
    assert "HEALTH    missing none" in lines                                   # checked and found nothing
    assert "  note    Dext footprint missing since 10:39 · newest 3 min from the book" in lines
    assert "NOT IN CARD  no trade" in lines                                    # the card's null, named -- never invented
    assert "%" not in out


def test_render_card_names_what_is_absent_never_a_zero():
    out = jarvis_cli.render_card({"idx": "NIFTY", "day": "2026-10-30", "at": "11:14", "word": "HOLD ▲", "lean": 1})
    assert "WORD      HOLD ▲" in out.splitlines()
    assert "NOT IN CARD  state · since · count · leg · pause · how much · where · buyer · seller · pick · wrong · no trade" \
           " · self · health" in out.splitlines()
    assert "WITH 0" not in out and "None" not in out


def test_parse_cli():
    assert jarvis_cli.parse_cli("replay 2026-10-21 10:30") == ("replay", ("2026-10-21", "10:30"))
    assert jarvis_cli.parse_cli("replay 21 Oct")[0] == "bad"
    assert jarvis_cli.parse_cli("  idx sensex ") == ("idx", "SENSEX")
    assert jarvis_cli.parse_cli("idx FINNIFTY")[0] == "bad"
    assert jarvis_cli.parse_cli("now") == ("now", None)
    assert jarvis_cli.parse_cli("watch 22800s") == ("cmd", "watch 22800s")
    assert jarvis_cli.parse_cli("what if 22800 breaks") == ("cmd", "what if 22800 breaks")
    assert jarvis_cli.parse_cli("quit") == ("quit", None)
    assert jarvis_cli.parse_cli("") == ("noop", None)


def _toy_frame(tmp_path):
    def c(t, word):
        return {"at": t, "word": word, "lean": 1, "leg": f"leg ▲ TREND 40 pts · origin 22,990f 09:15 · extreme 23,030f {t}",
                "day": "day: legs flipped 0 times so far", "wrong_line": "PALAT? if back past 23,016f (0.35 of the leg)",
                "buyer": "buy the CE on the pullback, not chased", "seller": "sell the PE at / beyond 23,000s (23,042f)",
                "pause": None}
    fr = {"ok": True, "day": "2026-10-30", "idx": "NIFTY", "mins": ["09:15", "09:16", "09:17"],
          "call": dict(c("09:17", "WATCH ▲"), missing=["chain missing 09:17–09:17: walls and answers there not read"],
                       pause={"line": "PAUSE ▲ · watch · 1 risk"}),
          "calls": [c("09:15", "OPENING"), c("09:16", "HOLD ▲"), c("09:17", "WATCH ▲")]}
    p = tmp_path / "frame.json"
    p.write_text(json.dumps(fr, ensure_ascii=False), encoding="utf-8")
    return p


def test_offline_now_and_replay_from_a_saved_frame(tmp_path, monkeypatch, capsys):
    p = _toy_frame(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO(
        "now\nreplay 2026-10-30 09:16\nreplay 2026-10-29 09:15\nreplay 2026-10-30 09:40\nwatch 22800s\nsell 2 lots\nquit\n"))
    assert jarvis_cli.main(["--frame", str(p)]) == 0
    out = capsys.readouterr().out
    assert "WORD      WATCH ▲" in out                                           # now = the frame's call
    assert "PAUSE     PAUSE ▲ · watch · 1 risk" in out
    assert "  missing chain missing 09:17–09:17: walls and answers there not read" in out
    assert "NIFTY · 2026-10-30 · 09:16 · replay" in out and "WORD      HOLD ▲" in out   # replay = calls[i] for that minute
    assert "the saved frame is 2026-10-30, not 2026-10-29 — showing its 09:15" in out and "WORD      OPENING" in out
    assert "could not check — 09:40 is not on the 2026-10-30 record" in out
    assert "offline — watch needs the server" in out
    assert "I read, I don't place." in out                                   # an order word, even offline
    assert "%" not in out


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_commands_go_to_the_grammar_with_src_cli_and_the_reply_is_verbatim(monkeypatch):
    sent = []

    def fake(req, timeout=None):
        sent.append((req.full_url, json.loads(req.data.decode("utf-8")) if req.data else None))
        if req.full_url.endswith("/api/jarvis/cmd"):
            return _Resp(json.dumps({"ok": False, "kind": "refused", "reply": "I read, I don't place.", "lines": []}).encode())
        return _Resp(json.dumps(CARD, ensure_ascii=False).encode("utf-8"))
    monkeypatch.setattr(jarvis_cli.urllib.request, "urlopen", fake)
    s = jarvis_cli.Session("http://127.0.0.1:8765", "NIFTY")
    assert s.handle("exit now") == "I read, I don't place."
    assert sent[-1] == ("http://127.0.0.1:8765/api/jarvis/cmd", {"idx": "NIFTY", "text": "exit now", "src": "cli"})
    assert "WORD      TREND ▼ · HOLD · since 09:56" in s.handle("now")
    assert sent[-1][0] == "http://127.0.0.1:8765/api/jarvis/card?idx=NIFTY"

    def down(req, timeout=None):
        raise urllib.error.URLError(ConnectionRefusedError(10061, "refused"))
    monkeypatch.setattr(jarvis_cli.urllib.request, "urlopen", down)
    assert s.handle("why").startswith("could not check — the server at http://127.0.0.1:8765 did not answer")
    assert s.handle("now").startswith("could not check — ")
