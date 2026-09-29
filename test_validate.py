"""validate.py against its registration (docs/hold/VALIDATE-PREREG.md rev 2): the four facts, the pick, the
word, the outcome, the unit and the stratum -- on checks whose answer is known by hand, and on the two saved
09-25 replies with that day's zone machine and candles frozen from §6's disclosure. In-sample by construction:
these pin the CODE to the TEXT, never the market."""
import json
import os

import hold
import validate

V = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "mockups", "validate-2026-09-25")
FX = json.load(open(os.path.join(V, "nifty_2026-09-25.json"), encoding="utf-8"))
IX = {c[1]: [c[5], c[3], c[4]] for c in FX["m1"]}
SETUP_FOR = {"fact": "for", "text": "zone SELL u2 triggered, 09:33 bar, gate legal — your setup, your direction",
             "absence": None, "side": "SELL", "band": "u2", "state": "TRIGGERED", "ref_t": "09:33"}
WALL = {"src": "wall", "side": "PE", "k": 23000.0, "word": "DEFENDED", "pts": 60.0}


def ck(setup=SETUP_FOR, entry="HOLD", line=40.0, noise=10.0, target=WALL, paid=True, role="long", fold_rule=None,
       B=None):
    """A buyer's long PE check at 10:00, every input a registered object as the server hands it over."""
    return {"trade": {"side": "PE", "role": role}, "thesis": hold.thesis("PE", role), "asof": "10:00",
            "setup": setup, "entry": {"verdict": entry, "fold_rule": fold_rule,
                                      "text": f"If you enter now, you enter into {entry} — the reason stands."},
            "now": {"payers": {"state": "for" if paid else "flat", "k": 23100.0,
                               "fact": "Put writers at 23,100 are covering — OI 20% off its peak, giving back since 09:50 [M] — fuel for your put"},
                    "holders": {"state": "for", "k": 23200.0, "fact": "Call writers at 23,200 still adding [M] — the ceiling above you holds"},
                    "flow": {"state": "blind"}, "trend": {"state": "for", "rows": "5m DOWN · 15m DOWN · 1h DOWN"},
                    "clock": {"paid_last": "10:00" if paid else "09:52"}},
            "room": {"t": "10:00", "close": 23100.0, "L": 23100.0 + line if line is not None else None, "line": line,
                     "noise": noise, "n": 15 if noise is not None else 9, "B": B, "level": 23145.0 if B else None,
                     "target": target, "why": None if line is not None else "could not check — no index candle at 10:00"}}


def saved(name):
    """A saved 09-25 reply with §1.1's pick and §1.3's geometry added as the server adds them."""
    c = json.load(open(os.path.join(V, name), encoding="utf-8"))
    fr = {"09:35": [{"k": 23100.0, "side": "PE", "state": "BUILDING", "built": True}],
          "09:43": [{"k": 23000.0, "side": "PE", "state": "UNWINDING", "built": True},    # §6: the top-2 PE fronts
                    {"k": 23100.0, "side": "PE", "state": "BUILDING", "built": True}]}[c["asof"]]
    mins = [{"t": t, "ix": IX.get(t), "fr": fr, "folds": [], "blind": None} for t in hold.SESSION if t <= c["asof"]]
    Z = FX["zone"]
    c["setup"] = validate.pick(Z["bars"], Z["buy"], Z["sell"], FX["zone_rows"], c["asof"], -1)
    c["room"] = validate.geometry(mins, len(mins) - 1, -1, c["now"]["line"])
    return c


# ---------------------------------------------------------------- §7: the seven tests that change
def test_her_0935_moment_reads_wait_as_disclosed():
    """§6: the facts become four; 09:35 reads [for, neither, against, neither], WAIT."""
    v = validate.word(saved("check_0935_WAIT_entry.json"))
    assert [f["state"] for f in v["facts"]] == ["for", "neither", "against", "neither"]
    assert (v["word"], v["n_for"], v["n_against"], v["n_neither"]) == ("WAIT", 1, 1, 2)
    assert (v["line"], v["noise"], v["target"]["k"], v["target"]["pts"]) == (17.65, 10.25, 23100.0, 3.95)
    assert v["sentence"] == "Your line is 17.65 pts away; the next wall (PE 23,100, DEFENDED) is only 3.95 [M]."
    assert v["needs"] == ["Room"]


def test_go_needs_hold_none_against_and_at_most_one_neither():
    assert validate.word(ck())["word"] == "GO" and validate.word(ck())["sentence"] == "Nothing is against you; 4 of 4 line up."
    assert validate.word(ck(paid=False))["word"] == "GO"                                   # one NEITHER is allowed
    two = validate.word(ck(paid=False, setup={**SETUP_FOR, "fact": "neither", "absence": "none",
                                              "text": "checked, none — the zone machine is waiting on both sides"}))
    assert two["word"] == "WAIT" and two["sentence"] == ("Nothing is against you, but only 2 of 4 line up. "
                                                         "Not there yet: Your setup, Paying.")
    assert validate.word(ck(entry="WATCH"))["word"] == "WAIT"                              # GO needs HOLD
    assert validate.word(ck(entry="PATA NAHI"))["word"] == "WAIT"


def test_no_only_on_a_fold_at_entry():
    no = validate.word(ck(entry="FOLD", fold_rule=6))
    assert no["word"] == "NO" and no["facts"][1]["state"] == "against"
    against = {**SETUP_FOR, "fact": "against", "side": "BUY", "band": "d2", "state": "ARMED", "ref_t": "09:51"}
    two = validate.word(ck(setup=against, line=4.0, noise=10.0))           # two AGAINST is not NO: Room leads
    assert (two["word"], two["n_against"]) == ("WAIT", 2)
    assert two["sentence"] == ("Your line is 4.0 pts away — inside one candle's range (median 10 pts over the last "
                               "15 min [M]). BUY d2 armed, 09:51 bar, gate legal — the other side's setup is live.")


def test_plain_words_and_no_percentage_in_the_word():
    v = validate.word(ck())
    assert [f["name"] for f in v["facts"]] == ["Your setup", "Right now", "Room", "Paying"]
    assert v["count"] == "4 for · 0 against · 0 neither — of 4, a count, not odds" and v["rev"] == "2"   # one word with the states
    assert "%" not in v["sentence"] + v["count"] and v["draft"].startswith("DRAFT") and all(f["text"] for f in v["facts"])
    assert v["not_shown"] == [validate.NOT_SHOWN + "σ against VWAP: the window's footer, never an input"]   # §1.5


def test_every_neither_says_which_absence_it_is():
    """CLAUDE.md rule 6 over four facts: checked-none, could-not-check and not-shown never collapse; a NEITHER
    that is a read carries None."""
    ab = lambda v: [f["absence"] for f in v["facts"]]                                       # noqa: E731
    blind = validate.word(ck(setup={"fact": "neither", "absence": "blind", "text": validate.CC + "the zone machine is not live yet"},
                             entry="PATA NAHI", noise=None, paid=False))
    assert ab(blind) == ["blind", "blind", "blind", "none"] and blind["facts"][2]["text"] == validate.CC + "9 of 15 candles"
    reads = validate.word(ck(setup={**SETUP_FOR, "fact": "neither", "absence": None, "text": "zone BUY d2 armed — gate illegal"},
                             entry="WATCH"))
    assert ab(reads) == [None, None, None, None] and [f["state"] for f in reads["facts"]][:2] == ["neither", "neither"]
    walls = validate.word(ck(target={"blind": validate.CC + "the walls could not be read: fronts forming"}))
    assert walls["facts"][2]["absence"] == "blind"


def test_a_writer_gets_no_word_and_is_told_why():
    """§1.6: the window's entry verdict heads; Your setup, Right now and the noise half of Room are printed."""
    v = validate.word(ck(role="short"))
    assert v["word"] is None and v["writer_note"] == validate.NOT_SHOWN + (
        "a GO / WAIT / NO for a writer: this word is judged on target against stop, and a writer has no target; "
        "hers needs its own registration.")
    assert v["facts"][3] == {"name": "Paying", "state": "neither", "absence": "hidden",
                             "text": validate.NOT_SHOWN + "Paying: a writer has no quiet clock; time pays her"}
    assert v["not_shown"] == [validate.SIGMA, validate.NOT_SHOWN + "a writer has no next wall; time is her target"]
    assert v["sentence"] == "If you enter now, you enter into HOLD — the reason stands."
    assert validate.word(ck(role="short", line=4.0))["facts"][2]["state"] == "against"      # the noise half


def test_fact_one_is_the_zone_machines_state_on_the_closed_bar():
    """§1.1 / P0-3: at 14:12 the zone SELL machine is ARMED on the 14:03 re-arm, 8 left on the CLOSED 14:09 bar
    (the forming 14:12 bar would say 7); its gate is read illegal. The day's 13:00 BUY trigger plays no part."""
    assert any(r["t"] == "13:00" and r["side"] == "BUY" and r.get("kind") != "arm" for r in FX["zone_rows"])
    Z = FX["zone"]
    s = validate.pick(Z["bars"], Z["buy"], Z["sell"], FX["zone_rows"], "14:12", -1)
    assert (s["bar"], s["side"], s["state"], s["ref_t"], s["candles_left"], s["legal"]) == ("14:09", "SELL", "ARMED", "14:03", 8, False)
    assert s["fact"] == "neither" and s["absence"] is None
    assert s["text"] == ("zone SELL u2 armed, 14:03 bar, 8 candles left — gate illegal (CE 23100 gave up its build at "
                         "13:46): your direction, but the fade is refused")


# ---------------------------------------------------------------- §7: the new tests owed
def test_the_0943_saved_reply_reads_wait_on_a_leaving_wall():
    """§6: 09:43 -- the BUY arm is illegal, HOLD, the leaving PE 23,000 is removed so the target is the session
    low 23,030.0 at 18.8 against a 72.8 line, paid this minute: WAIT, 2 for · 1 against · 1 neither."""
    c = saved("check_0943.json")
    v = validate.word(c)
    assert [f["state"] for f in v["facts"]] == ["neither", "for", "against", "for"]
    assert (v["word"], v["n_for"], v["n_against"], v["n_neither"]) == ("WAIT", 2, 1, 1)
    assert v["target"] == {"src": "session", "side": "PE", "k": 23030.0, "word": None, "pts": 18.8}
    assert (v["line"], v["noise"]) == (72.8, 11.05)


def test_a_line_inside_the_noise_is_against_whatever_the_target():
    for tg in (WALL, {**WALL, "pts": 999.0}, {"src": "none", "side": "PE", "k": None, "word": None, "pts": None}):
        assert validate.room(ck(line=4.0, noise=4.9, target=tg)["room"])[0] == "against"
    tie = validate.room(ck(line=4.9, noise=4.9, B=4.9)["room"])                             # a tie is AGAINST
    assert tie[0] == "against" and tie[1].endswith("(the window breaks one candle further, at 23,145.0)")
    assert validate.room(ck(line=40.0, target={**WALL, "pts": 40.0})["room"])[0] == "for"   # a target tie is WITH


def test_a_leaving_wall_is_removed_from_the_target():
    rec = {"t": "10:00", "blind": None, "folds": [{"k": 23050.0, "side": "PE", "t": "09:55", "still": True}],
           "fr": [{"k": 23080.0, "side": "PE", "state": "UNWINDING", "built": True},
                  {"k": 23050.0, "side": "PE", "state": "STALLED", "built": True},      # STALLED, but a live fold: leaving
                  {"k": 23000.0, "side": "PE", "state": "BUILDING", "built": True}]}
    assert validate.target(rec, -1, 23100.0, 22990.0) == {"src": "wall", "side": "PE", "k": 23000.0, "word": "DEFENDED", "pts": 100.0}
    gone = {**rec, "fr": rec["fr"][:2]}
    assert validate.target(gone, -1, 23100.0, 22990.0)["src"] == "session"                   # every wall leaving
    assert validate.target({**rec, "blind": "could not check — fronts forming"}, -1, 23100.0, 22990.0) == \
        {"blind": validate.CC + "the walls could not be read: fronts forming"}


def _day(close=100.0, lo=99.0, hi=101.0):
    return [{"t": t, "ix": [close, hi, lo]} for t in hold.SESSION]


def _g(L, T, line=10.0, noise=2.0):
    return {"t": "?", "L": L, "line": line, "noise": noise, "why": None,
            "target": {"src": "wall", "side": "PE", "k": T, "pts": 10.0, "word": "STALLED"}}


def test_the_outcome_is_a_first_passage_to_static_levels():
    """§3, a long PE checked at 12:00: target reached on a 1-min LOW, stop on a 1-min HIGH, 30 finished minutes;
    `same minute`, `neither`, not scored, `short` after 14:59, and a minute with no candle is a gap."""
    i = hold.SESSION.index("12:00")
    m = _day()
    m[i + 3]["ix"] = [95.0, 100.0, 89.0]
    o = validate.outcome(m, i, -1, _g(110.0, 90.0))
    assert (o["first"], o["at"], o["to"], o["short"], o["gaps"]) == ("target", "12:03", "12:30", False, 0)
    m[i + 2]["ix"] = [105.0, 111.0, 100.0]
    assert validate.outcome(m, i, -1, _g(110.0, 90.0))["first"] == "stop"                  # the stop came first
    both = _day()
    both[i + 1]["ix"] = [100.0, 111.0, 89.0]
    assert validate.outcome(both, i, -1, _g(110.0, 90.0))["first"] == "same minute"
    quiet = _day()
    quiet[i + 5]["ix"] = None
    o = validate.outcome(quiet, i, -1, _g(110.0, 90.0))
    assert (o["first"], o["gaps"]) == ("neither", 1)
    assert validate.outcome(quiet[:i + 20], i, -1, _g(110.0, 90.0)) is None                  # the window has not finished
    late = validate.outcome(_day(), hold.SESSION.index("15:10"), -1, _g(110.0, 90.0))
    assert (late["to"], late["short"], late["first"]) == ("15:29", True, "neither")
    none = validate.outcome(_day(), i, -1, {**_g(110.0, 90.0), "target": {"src": "none", "side": "PE", "k": None, "pts": None}})
    assert (none["first"], none["why"]) == ("not scored", validate.NONE + "no target (price discovery)")
    blind = validate.outcome(_day(), i, -1, {**_g(None, 90.0), "line": None, "why": "could not check — no NIFTY candle for 12:00"})
    assert blind["why"] == validate.CC + "the line could not be set at 12:00: no NIFTY candle for 12:00"


def test_the_unit_is_the_first_press_per_index_and_direction_per_30_minutes():
    """§3: strike-shopping one minute buys one unit; the next unit is 30 minutes after the last; another index
    or direction is its own; rev 1 rows are never units."""
    def p(t, idx="NIFTY", d=-1, k=23100.0, rev="2"):
        return {"rev": rev, "t": t, "idx": idx, "d": d, "k": k, "role": "long", "at": 0}
    rows = [p("10:00", k=23100.0), p("10:00", k=23200.0), p("10:00", k=23300.0), p("10:10"), p("10:29"),
            p("10:30"), p("10:00", idx="SENSEX"), p("10:05", d=1), p("09:50", rev=None),
            {**p("10:31"), "role": "short"}, {"kind": "check_outcome", "t": "10:00", "idx": "NIFTY", "d": -1}]
    got = [(u["t"], u["idx"], u["d"]) for u in validate.units(rows)]
    assert got == [("10:00", "NIFTY", -1), ("10:00", "SENSEX", -1), ("10:05", "NIFTY", 1), ("10:30", "NIFTY", -1)]


def test_the_stratum_is_rooms_whole_with_geometry():
    """§4: a WAIT unit with its line inside the noise is shown, not judged; line > noise and target >= line is."""
    row = {"first": "stop", "noise": 14.8, "stop": {"L": 23121.6, "pts": 2.65}, "target": {"pts": 18.95}}
    assert validate.in_stratum(row) is False
    assert validate.in_stratum({**row, "stop": {"pts": 24.95}, "noise": 5.3, "target": {"pts": 36.65}}) is True
    assert validate.in_stratum({**row, "stop": {"pts": 24.95}, "noise": 5.3, "target": {"pts": 18.8}}) is False


# ---------------------------------------------------------------- §1.1 the pick, one test per rule
def _bars(c=100.0, n=12, crossed=False, start="09:30"):
    return [{"t": hold.hm(hold.mm(start) + 3 * i),
             "fut": {"c": c, "d3": 90.0, "d2": 95.0, "u2": 94.0 if crossed else 105.0, "u3": 110.0}} for i in range(n)]


W = {"state": "WAITING", "ref_i": None, "candles_left": None, "exit_why": None}


def _armed(ref, left):
    return {"state": "ARMED", "ref_i": ref, "candles_left": left, "exit_why": None}


ROWS = [{"rule": "zone", "t": "09:45", "kind": "arm", "side": "BUY", "gate": {"legal": True, "why": "PE 23000 still building"}},
        {"rule": "zone", "t": "09:54", "kind": "arm", "side": "SELL", "gate": {"legal": True, "why": "CE 23300 still building"}},
        {"rule": "zone", "t": "09:45", "kind": "arm", "side": "SELL", "gate": {"legal": True, "why": "CE 23300 still building"}}]


def _pick(buy_last, sell_last, c=100.0, rows=ROWS, **kw):
    b = _bars(c, **kw)
    buy, sell = [dict(W) for _ in b], [dict(W) for _ in b]
    buy[-1], sell[-1] = buy_last, sell_last
    return validate.pick(b, buy, sell, rows, "10:05", -1)


def test_pick_one_active_machine_wins_over_a_pocket_whose_machine_is_waiting():
    s = _pick(W, _armed(8, 7), c=93.0)                     # the close is in the BUY pocket; BUY is waiting
    assert (s["side"], s["ref_t"], s["fact"]) == ("SELL", "09:54", "for")
    assert s["context"] == "price closed in the buy pocket, but that machine is waiting — no arm"


def test_pick_both_active_the_pocket_at_the_close_wins():
    s = _pick(_armed(5, 4), _armed(8, 7), c=93.0)
    assert (s["side"], s["ref_t"], s["fact"]) == ("BUY", "09:45", "against")


def test_pick_both_active_no_pocket_the_later_event_bar_wins():
    s = _pick(_armed(5, 4), _armed(8, 7), c=100.0)
    assert (s["side"], s["ref_t"]) == ("SELL", "09:54")


def test_pick_an_exact_tie_reads_neither():
    s = _pick(_armed(5, 4), _armed(5, 4), c=100.0)
    assert (s["fact"], s["absence"], s["side"]) == ("neither", None, None)
    assert s["text"].startswith("the zone machine points both ways on the 10:03 bar: zone BUY d2 armed, 09:45 bar")


def test_pick_crossed_bands_or_a_bar_before_0925_could_not_check():
    s = _pick(_armed(5, 4), W, crossed=True)
    assert (s["fact"], s["absence"]) == ("neither", "blind") and "bands have not formed" in s["text"]
    b = _bars(start="09:15", n=4)
    early = validate.pick(b, [dict(W)] * 4, [dict(W)] * 4, ROWS, "09:23", -1)
    assert early["absence"] == "blind" and "before its 09:25 gate" in early["text"]


def test_pick_a_lock_that_has_just_opened_is_not_active():
    s = _pick({**W, "exit_why": "vwap"}, W)
    assert (s["fact"], s["absence"]) == ("neither", "none")
    assert s["text"] == (validate.NONE + "the zone machine is waiting on both sides; its last event was "
                         "BUY d2 lock cleared at VWAP, 10:03 bar")
