"""THE MESSAGE STREAM's builder (messages.py): one line per CHANGE in a read the server already logs, with DECODE's count
at that close. Fixture READ / DECODE / setup / DIN / voice / recording rows; pure, so no file and no clock."""
import messages


def mark(t, word, d=0, idx="NIFTY", **kw):
    return dict(kind="mark", idx=idx, t=t, word=word, dir=d, **kw)


def ev(t, event, d, text, idx="NIFTY", en="", **kw):
    return dict(kind="event", idx=idx, t=t, event=event, dir=d, text=text, en=en, **kw)


def dec(T, kind="JAARI", ld=-1, d=0, c=5, idx="NIFTY", setups=(), ty=None):
    return {"idx": idx, "T": T, "call": {"text": "x", "kind": kind, "d": d, "c": c, "of": 7,
                                         "signs": ["CVD leg low pe", "Δ leg ke saath"]},
            "leg": None if ld is None else {"d": ld, "ext": {"t": T, "fut": 22790.0, "spot": 22740.0}},
            "setups": list(setups), "onesided": {"type": ty}}


def lines(ms, kind):
    return [m["line"] for m in ms if m["kind"] == kind]


def test_read_word_changes_once_from_the_marks():
    """One line per change of THE READ's held word or arrow. BAN RAHA is never named, a repeat says nothing,
    and the line carries DECODE's count at that close and the READ's own level (spot)."""
    rr = [mark("09:40", "BAN RAHA"), mark("09:45", "WAIT"), mark("09:55", "LEAN", -1, flip=22800.0, since="09:55"),
          ev("09:55", "FORM", -1, "LEAN ▼ bana · FLIP 22,800", en="the read formed"),
          mark("10:00", "LEAN", -1, flip=22800.0), mark("10:05", "TREND", -1, src="flow+fuel", flip=22780.0),
          mark("10:10", "RANGE", 0, box={"top": {"k": 22900}, "bottom": {"k": 22700}}),
          ev("10:10", "BREAK", 1, "TREND ▼ · flow+fuel khatam · price ulta TREND")]
    dr = [dec("09:55", c=5), dec("10:05", "THAK", d=4, c=1), dec("10:10", "MILA", d=2, c=3)]
    ms = messages.build(rr, dr)
    assert lines(ms, "READ") == ["09:55  NIFTY  WAIT → LEAN ▼ · 5/7 saath · flip 22,800s",
                                 "10:05  NIFTY  LEAN ▼ → TREND ▼ · flow+fuel · 4/7 khilaaf · flip 22,780s",
                                 "10:10  NIFTY  TREND ▼ · flow+fuel → RANGE · mila 2 thak · 3 jaari · box 22,700–22,900s"]
    read = [m for m in ms if m["kind"] == "READ"]
    assert read[0]["why"] == "the read formed" and read[0]["dir"] == -1 and read[0]["ev"] == "WORD"
    assert read[0]["key"] == "NIFTY|READ|09:55|WAIT → LEAN ▼"
    assert read[-1]["why"] == "TREND ▼ · flow+fuel khatam · price ulta TREND"          # a BREAK's own words win


def test_read_line_means_the_word_or_the_arrow_changed():
    """flow+fuel arriving or leaving on the SAME word and arrow is churn, not a message; LEAN ▼ → TREND ▼ is one. The held
    state still follows the skipped mark, so the next line starts from what the READ was actually saying."""
    rr = [mark("09:55", "LEAN", -1, flip=22800.0), mark("10:00", "TREND", -1, src="flow+fuel", flip=22780.0),
          mark("10:05", "TREND", -1, flip=22760.0), mark("10:10", "TREND", -1, src="flow+fuel", flip=22750.0),
          mark("10:15", "RANGE", 0, box={"top": {"k": 22900}, "bottom": {"k": 22700}})]
    dr = [dec(t, c=5) for t in ("09:55", "10:00", "10:05", "10:10", "10:15")]
    assert lines(messages.build(rr, dr), "READ") == [
        "09:55  NIFTY  WAIT → LEAN ▼ · 5/7 saath · flip 22,800s",
        "10:00  NIFTY  LEAN ▼ → TREND ▼ · flow+fuel · 5/7 saath · flip 22,780s",
        "10:15  NIFTY  TREND ▼ · flow+fuel → RANGE · ▼5/7 · box 22,700–22,900s"]


def test_agree_reads_decodes_count_and_its_way():
    """JAARI reads its leg's way (c/7), THAK against it (d/7); saath / khilaaf against the message, DECODE's arrow when the
    message has no way. mila, saaf nahi and ? stay three different sentences (CLAUDE.md rule 6)."""
    up = dec("10:00", "JAARI", ld=1, c=5)
    assert messages.agree(up, 1) == "5/7 saath" and messages.agree(up, -1) == "5/7 khilaaf"
    assert messages.agree(up, 0) == "▲5/7"
    assert messages.agree(dec("10:00", "THAK", ld=1, d=4), -1) == "4/7 saath"
    assert messages.agree(dec("10:00", "MILA", d=2, c=3), 1) == "mila 2 thak · 3 jaari"
    assert messages.agree(dec("10:00", "SAAF_NAHI", ld=None), 1) == "saaf nahi"
    assert messages.agree(None, 1) == "?"
    assert messages.agree(dict(dec("10:00"), call={"text": "?", "kind": "SAAF_NAHI"}), 1) == "?"


def test_leg_moves_only_on_jaari_thak_or_a_flip():
    """MILA, saaf nahi and an unread close keep the last leg read: 23 Oct had 30-37 kind changes an index [M], 14-17 of
    them JAARI / THAK turns."""
    dr = [dec("09:35", "JAARI"), dec("09:40", "MILA", d=2, c=3), dec("09:45", "JAARI"), dec("09:50", "THAK", d=4, c=2),
          dec("09:55", "SAAF_NAHI", ld=None), dec("10:00", "JAARI", ld=1, c=6)]
    assert lines(messages.build([], dr), "LEG") == ["09:35  NIFTY  ▼ leg jaari · 5/7 saath",
                                                    "09:50  NIFTY  ▼ leg thak raha · 4/7 khilaaf",
                                                    "10:00  NIFTY  ▲ leg jaari · 6/7 saath"]


def test_setup_fires_on_match_and_again_only_after_it_clears():
    """A FADE / RIDE / FADE-D chip turning MATCH (or an entry's HOLD v2 state) is one SETUP line with the leg's extreme
    (fut). The chip staying live says nothing; it fires again only after it went back to ARMED or —."""
    def s(state, nm="FADE-D", side="BUY"):
        return [{"name": nm, "side": side, "checks": {}, "state": state}]
    dr = [dec("13:05", "THAK", d=4, setups=s("ARMED")), dec("13:10", "THAK", d=4, setups=s("MATCH")),
          dec("13:15", "THAK", d=4, setups=s("line 22,700 · +0.2R")), dec("13:20", "THAK", d=4, setups=s("—")),
          dec("13:25", "THAK", d=4, setups=s("MATCH")), dec("13:30", "THAK", d=4, setups=s("MATCH", "RIDE", "SELL"))]
    ms = messages.build([], dr)
    assert lines(ms, "SETUP") == ["13:10  NIFTY  FADE-D BUY · 4/7 saath · 22,790f",
                                  "13:25  NIFTY  FADE-D BUY · 4/7 saath · 22,790f",
                                  "13:30  NIFTY  RIDE SELL · 4/7 khilaaf · 22,790f"]
    assert [m["why"] for m in ms if m["kind"] == "SETUP"] == ["MATCH", "MATCH", "MATCH"]


def test_a_setup_line_shows_the_setups_own_entry_and_stop():
    """A108, 26 Oct 09:35: the FADE-D BUY's line showed 22,546f -- the DECODE leg's extreme, the bounce's high so far --
    for an entry at 22,500f with its stop at 22,434f. The chip's plan is the line's price; a chip without one (a row
    logged before it) keeps the leg's extreme."""
    s = [{"name": "FADE-D", "side": "BUY", "checks": {}, "state": "MATCH", "plan": "E 22,422s|22,500f · stop 22,356s|22,434f"}]
    ms = messages.build([], [dec("09:35", "JAARI", ld=1, c=4, setups=s)])
    assert lines(ms, "SETUP") == ["09:35  NIFTY  FADE-D BUY · 4/7 saath · E 22,422s|22,500f · stop 22,356s|22,434f"]


def test_din_changes_and_a_quit_is_its_own_read_line():
    """The day type speaks on a change only (an unread type keeps the last); a QUIT is a READ line of its own."""
    dr = [dec("09:20", "SAAF_NAHI", ld=None, ty="MIXED"), dec("09:25", ty="MIXED"), dec("11:00", c=7, ty="TREND ▼"),
          dec("11:05", ty=None), dec("11:10", ty="TREND ▼"), dec("14:40", ty="CHOP")]
    rr = [ev("10:10", "QUIT", -1, "22,600 PE likhne wale bhage · +37.2L → +15.1L · paar +78", k=22600.0, side="PE")]
    ms = messages.build(rr, dr)
    assert lines(ms, "DIN") == ["09:20  NIFTY  din MIXED · saaf nahi", "11:00  NIFTY  din TREND ▼ · 7/7 saath",
                                "14:40  NIFTY  din CHOP · ▼5/7"]
    q = [m for m in ms if m.get("ev") == "QUIT"]
    assert [m["line"] for m in q] == ["10:10  NIFTY  22,600 PE likhne wale bhage · ?"]
    assert q[0]["why"].startswith("22,600 PE likhne wale bhage · +37.2L")


def test_now_rows_one_per_index_with_a_reason_when_missing():
    rr = [mark("10:00", "LEAN", -1, since="09:55"), mark("10:05", "TREND", -1, src="flow+fuel", since="09:55"),
          mark("10:05", "RANGE", idx="SENSEX", since="10:05")]
    dr = [dec("10:05", c=6), dec("10:05", "THAK", d=4, idx="SENSEX")]
    assert [r["line"] for r in messages.now_rows(rr, dr, ["NIFTY", "BANKNIFTY", "SENSEX"])] == [
        "NIFTY  TREND ▼ · flow+fuel · 6/7 saath · since 09:55", "BANKNIFTY  read abhi nahi",
        "SENSEX  RANGE · ▲4/7 · since 10:05"]


def test_trade_and_health_are_changes_only():
    tr = {"id": "t1", "idx": "NIFTY"}
    v = {"ok": True, "state": "WARN", "d": -1, "trig_t": "11:07", "stop_f": 22780.0,
         "reason": "CE front gave up @ 22,780f · line 22,780f (HOLD v2)"}
    m = messages.trade(tr, v, "HOLD", dec("11:05", "THAK", d=4), "11:08")
    assert m["line"] == "11:07  TRADE  WARN · CE front gave up @ 22,780f · 4/7 khilaaf · stop 22,780f"
    assert m["key"] == "NIFTY|TRADE|11:07|WARN|t1" and m["id"] == "t1"
    assert messages.trade(tr, v, "WARN", None, "11:08") is None                        # the same state: said already
    assert messages.trade(tr, dict(v, state="HOLD"), "WARN", None, "11:08") is None     # HOLD is the quiet state
    assert messages.trade(tr, {"ok": False, "why": "x"}, None, None, "11:08") is None
    ok = {"ok": True, "missing": [], "text": None}
    nahi = {"ok": False, "missing": ["book", "GoCharting"], "text": "RECORDING NAHI: book, GoCharting"}
    assert messages.health(None, None, "09:16") is None
    assert messages.health(ok, None, "09:20")["line"] == "09:20  HEALTH  TapeMap live · recording ok"
    assert messages.health(ok, "TapeMap live", "09:21") is None
    assert messages.health(nahi, "TapeMap live", "11:02")["line"] == "11:02  HEALTH  RECORDING NAHI · book, GoCharting"
    assert messages.health(nahi, "RECORDING NAHI", "11:03") is None
    assert messages.health(ok, "RECORDING NAHI", "11:09")["line"] == "11:09  HEALTH  RECORDING OK"


def test_build_is_the_same_whatever_the_row_order():
    """Anytime-start: the same rows give the same stream, however the logs were appended."""
    rr = [mark("09:55", "LEAN", -1, flip=22800.0), ev("10:10", "QUIT", -1, "a", k=22600.0, side="PE"),
          ev("10:10", "QUIT", -1, "b", k=22550.0, side="PE"), mark("10:10", "WAIT")]
    dr = [dec("09:55"), dec("10:10", "THAK", d=4, ty="MIXED")]
    assert messages.build(rr, dr) == messages.build(rr[::-1], dr[::-1])


def test_one_malformed_row_is_skipped_and_counted_never_raised():
    """A bad dir, a text number or a non-text close in ONE row must not freeze the stream (the pass would raise on every
    pass): the row is skipped, counted in messages.SKIPPED, and the held state is not poisoned by it."""
    rr = [mark("09:55", "LEAN", -1, flip=22800.0),
          mark("10:00", "TREND", "up"),                                   # dir that is not -1 / 0 / 1
          mark("10:05", "TREND", -1, flip="22780"),                       # a number as text
          mark(1007, "RANGE", 0),                                         # a close that is not text: not a row at all
          mark("10:10", "TREND", -1, flip=22780.0),
          ev("10:12", "QUIT", -1, "gave back", k="abc", side="PE")]       # a strike as text
    bad = dec("10:15", "JAARI", ld=-1, c=5)
    bad["call"]["signs"] = 5                                              # not a list
    dr = [bad, dec("10:20", "JAARI", ld=-1, c=5)]
    ms = messages.build(rr, dr)
    assert lines(ms, "READ") == ["09:55  NIFTY  WAIT → LEAN ▼ · ? · flip 22,800s",
                                 "10:10  NIFTY  LEAN ▼ → TREND ▼ · ? · flip 22,780s"]
    assert lines(ms, "LEG") == ["10:20  NIFTY  ▼ leg jaari · 5/7 saath"]
    assert messages.SKIPPED["n"] == 4
    assert messages.build([], []) == [] and messages.SKIPPED["n"] == 0
