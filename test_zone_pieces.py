"""A116: the ZONE alert carries her four pieces -- zone · thakan/roka · PE likh rahe · delta flip -- each with its number,
n/4, and one line when a piece joins. Mary, 26 Oct: "vwap band rotation is for to look for lows and if there are sellers
is getting exhausted and absorbed and in oi also there was clear bias on put side delta was reducing or i should say goes
from - to + ... there was nothing on the app thats was telling all that". The candles are 26 Oct's (test_zone3)."""
import inspect

import decode
import faded
import messages
import server
import telegram_out
import tape_log
from test_zone3 import M, _b3, _g

T0915 = 1792986300000                      # 26 Oct 09:15 IST, the extension's mark clock (epoch ms of the 5-min bar)


def _ms(hhmm):
    return T0915 + (M(hhmm) - M("09:15")) * 60000


def _mark(hhmm, kind, name, p, winner=1):
    return {"id": f"{kind}@{_ms(hhmm)}@{p}", "t": _ms(hhmm), "kind": kind, "name": name, "p": p, "winner": winner}


MARKS = [_mark("09:15", "absorption", "▲ KHAREEDAR NE ROKA", 22500),
         _mark("09:20", "exhaustion", "▲ THAKAN · bechne wale", 22454),
         _mark("09:35", "initiative", "▼ ZOR · bechne wale", 22500.1, -1)]


def _b5(*rows):
    """5-min flow bars {s, delta} from (HH:MM, delta)."""
    return [{"s": M(t) * 60, "delta": dl, "c": 22500.0} for t, dl in rows]


FLOW = _b5(("09:15", -1007), ("09:20", -286), ("09:25", 33), ("09:30", 372), ("09:35", -880))


def _gz(at, l5=None, bars5=FLOW, **kw):
    g = _g(at, **kw)
    g["bars5"] = [b for b in bars5 if b["s"] + 300 <= g["now"]]
    g["l5"] = l5 if l5 is not None else {M("09:30"): {"pe": -20.5, "why": None}, M("09:35"): {"pe": 3.9, "why": None},
                                         M("09:40"): {"pe": 15.6, "why": None}}
    return g


def _fin(at, marks=MARKS, **kw):
    return dict({"bars3": _b3(M(at)), "marks": marks}, **kw)


def test_the_match_chip_carries_her_four_pieces_with_their_numbers():
    s = decode._zone3(_gz("09:30"), _fin("09:30"))
    assert s["state"] == "MATCH" and s["plan"] == "E 22,534f · stop 22,425f" and s["ep"] == "09:27"
    assert s["pieces"] == ["✓ d2 22,445f chhua 09:24",
                           "✓ KHAREEDAR NE ROKA 22,500f 09:15, THAKAN bechne wale 22,454f 09:20",
                           "✗ PE likh rahe · lead −20.5",
                           "✓ Δ −1,007 → −286 → +33"]
    assert s["checks"] == {"zone": True, "thakan": True, "PE": False, "Δ": True} and s["n"] == 3
    sp = decode._zone3(_gz("09:30", basis=65.95), _fin("09:30"))
    assert sp["pieces"][0] == "✓ d2 22,379s|22,445f chhua 09:24"              # every level says spot and fut


def test_a_mark_counts_only_on_her_side_after_its_bar_closed_and_inside_the_window():
    late = [_mark("09:30", "absorption", "▲ KHAREEDAR NE ROKA", 22497)]        # its bar closes 09:35
    s = decode._zone3(_gz("09:30"), _fin("09:30", marks=late + MARKS[2:]))
    assert s["checks"]["thakan"] is False and s["pieces"][1] == "✗ thakan/roka nahi"
    early = [_mark("09:05", "absorption", "▲ KHAREEDAR NE ROKA", 22600)]       # before 15 min ahead of the 09:24 arm
    assert decode._zone3(_gz("09:30"), _fin("09:30", marks=early))["checks"]["thakan"] is False


def test_put_writers_join_at_the_first_close_ten_points_ahead():
    assert faded.LEAD_PTS == 10.0
    p = {x["k"]: x for x in decode._zone_read(_gz("09:40"), _fin("09:40"))[1]["pieces"]}
    assert p["PE"]["ok"] is True and p["PE"]["chip"] == "✓ PE likh rahe · lead +15.6 09:40" and p["PE"]["t"] == "09:40"


def test_writers_and_the_flip_count_only_from_the_touch():
    """26 Oct replay: a 09:30 CE lead and a 09:35 flip had made the 09:45 u2 arm read 4/4 under a 250-pt rally."""
    l5 = {M("09:20"): {"pe": 40.0, "why": None}, M("09:30"): {"pe": -20.5, "why": None}}
    flow = _b5(("09:15", -100), ("09:20", 50), ("09:25", -30))                 # flipped at 09:20, before the 09:24 touch
    s = decode._zone3(_gz("09:30", l5=l5, bars5=flow), _fin("09:30"))
    assert s["checks"]["PE"] is False and s["pieces"][2] == "✗ PE likh rahe · lead −20.5"
    assert s["checks"]["Δ"] is False and s["pieces"][3] == "✗ Δ − → + nahi · abhi −30"


def test_what_could_not_be_read_says_why_and_never_counts():
    s = decode._zone3(_gz("09:30", l5={}, bars5=[]), _fin("09:30", marks=[]))
    assert s["pieces"][1:] == ["? thakan/roka — chart marks nahi", "? PE likh rahe — chain nahi", "? Δ — koi 5m bar nahi"]
    assert s["checks"] == {"zone": True, "thakan": None, "PE": None, "Δ": None} and s["n"] == 1
    p = {x["k"]: x for x in decode._zone_read(_gz("09:40", bars5=_b5(("09:30", 372), ("09:35", -880))),
                                                _fin("09:40", marks=None))[1]["pieces"]}
    assert p["Δ"]["ok"] is None and p["Δ"]["chip"] == "? Δ — flow 09:30 se"     # the selling into the band was never seen
    assert p["thakan"]["ok"] is None


def test_the_armed_chip_shows_the_pieces_forming():
    s = decode._zone3(_gz("09:27"), _fin("09:27"))                         # the 09:25 bar (+33) closes at 09:30
    assert s["state"] == "ARMED" and s["n"] == 2 and "ep" not in s
    assert s["checks"] == {"zone": True, "thakan": True, "PE": None, "Δ": False} and s["pieces"][3] == "✗ Δ − → + nahi · abhi −286"


def test_the_episode_lives_30_min_from_the_location_bar_and_ends_on_its_stop():
    assert faded.WINDOW == 30
    ep = decode._zone_read(_gz("09:50"), _fin("09:50"))[1]
    assert ep["side"] == "BUY" and ep["ep"] == "09:27" and ep["n"] == 4 and ep["plan"] == "E 22,534f · stop 22,425f"
    assert decode._zone_read(_gz("09:55"), _fin("09:55"))[1] is None             # 09:24 + 30 min is over
    b3 = _b3(M("09:33"))
    b3[-1] = dict(b3[-1], fut=dict(b3[-1]["fut"], l=22400.0))                  # the 09:30 bar trades the 22,425 stop
    assert decode._zone_read(_gz("09:35"), {"bars3": b3, "marks": MARKS})[1] is None


def test_decode_carries_the_episode_and_empty_says_none():
    assert decode.empty("x")["zone_ep"] is None
    assert "zone_ep" in inspect.getsource(decode.decode)


def _row(at, g):
    fin = _fin(at)
    return {"idx": "NIFTY", "T": at, "call": {"text": "x", "kind": "JAARI", "d": 0, "c": 4, "of": 7, "signs": []},
            "leg": {"d": 1, "ext": {"t": at, "fut": 22549.0, "spot": None}}, "onesided": {"type": None},
            "setups": [s for s in [decode._zone3(g, fin)] if s], "zone_ep": decode._zone_read(g, fin)[1]}


def test_the_setup_line_says_n_of_4_and_each_piece_then_one_line_when_a_piece_joins():
    rows = [_row(t, _gz(t)) for t in ("09:30", "09:35", "09:40", "09:45")]
    ms = [m for m in messages.build([], rows) if m["kind"] == "SETUP"]
    assert [m["line"] for m in ms] == [
        "09:30  NIFTY  ZONE BUY · 3/4 · ✓ d2 22,445f chhua 09:24 · "
        "✓ KHAREEDAR NE ROKA 22,500f 09:15, THAKAN bechne wale 22,454f 09:20 · ✗ PE likh rahe · lead −20.5 · "
        "✓ Δ −1,007 → −286 → +33 · E 22,534f · stop 22,425f · din: padh nahi sake",              # A131: + the day type
        "09:40  NIFTY  ZONE BUY + PE likh rahe · 4/4 · ✓ PE likh rahe · lead +15.6 09:40 · E 22,534f · stop 22,425f"]
    assert all(telegram_out.wants(m) for m in ms)
    assert len({m["key"] for m in ms}) == 2


def test_no_update_without_the_alert_or_for_another_episode():
    r = _row("09:40", _gz("09:40"))
    assert not [m for m in messages.build([], [dict(r, setups=[])]) if m["kind"] == "SETUP"]   # no MATCH was alerted
    other = dict(r, zone_ep=dict(r["zone_ep"], ep="10:12"))
    assert len([m for m in messages.build([], [_row("09:30", _gz("09:30")), other]) if m["kind"] == "SETUP"]) == 1


def test_sensex_reads_niftys_flow_and_marks_and_its_own_writers(tmp_path, monkeypatch):
    """§1q: SENSEX's delta and chart marks are NIFTY's, tagged; its PE lead is its own chain's."""
    s = decode._zone3(dict(_gz("09:30", bars5=[]), idx="SENSEX"), _fin("09:30", flow={"of": "NIFTY", "bars5": FLOW}))
    assert s["pieces"][1].endswith("(NIFTY)") and s["pieces"][3] == "✓ Δ −1,007 → −286 → +33 (NIFTY)"
    assert s["pieces"][2] == "✗ PE likh rahe · lead −20.5"
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path))
    tape_log._write_lines(tape_log.marks2_path("2026-10-28", "NIFTY"), MARKS)
    G = {"NIFTY": {"bars5": FLOW}, "SENSEX": {"bars5": []}}
    zi = server._decode_zone_in("SENSEX", "2026-10-28", G)
    assert zi["flow"] == {"of": "NIFTY", "bars5": FLOW} and [m["id"] for m in zi["marks"]] == [m["id"] for m in MARKS]
    assert server._decode_zone_in("BANKNIFTY", "2026-10-28", G) == {"marks": []}
    assert "_decode_zone_in(i, day, G)" in inspect.getsource(server._decode_all)
