"""A131: the ZONE line's day type (messages.din_line) and TOP / BOTTOM BAN SAKTA (palat.py) on synthetic days. Every file
is under tmp_path (conftest STR_PATHS); nothing here reads or writes data/."""
import json
import os
from datetime import datetime

import book_log
import chain_live
import messages
import palat
import tape_log
import trigger_log
from chain_live import IST

DAY = "2026-10-28"                                       # a Wednesday


def ms(m, s=0):
    y, mo, d = (int(x) for x in DAY.split("-"))
    return int(datetime(y, mo, d, m // 60, m % 60, s, tzinfo=IST).timestamp() * 1000)


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def scene(T=660, fut=None, chain=True, toot=True):
    """A TOP at minute T: flat 22,600 then a rip to 22,840f; spot to 22,824; a +300 buy push at T-10 that cuts the
    22,750 CE wall 10L (TOOT; not with toot=False), then a +300 buy push at T-1 the 22,850 CE wall never answers; put WRITERS (premium falling faster than delta explains) add 40L at 22,800, the day's biggest add there;
    the future 16 over spot; fut OI flat (or `fut` = the OI per minute); a SELL arm at T-3."""
    bars = [{"t": ms(m), "o": 22600, "h": 22610, "l": 22590, "c": 22600, "vol": 1000, "rowSize": 5} for m in range(555, T - 15, 5)]
    for m, (o, h, l, c) in zip((T - 15, T - 10, T - 5, T), ((22600, 22700, 22600, 22700), (22700, 22780, 22700, 22780),
                                                         (22780, 22840, 22780, 22835), (22835, 22840, 22800, 22805))):
        bars.append({"t": ms(m), "o": o, "h": h, "l": l, "c": c, "vol": 100, "rowSize": 5})
    R = {}
    for m in range(555, T + 5) if chain else ():
        sp = 22600 if m <= T - 20 else min(22824, 22600 + (m - (T - 20)) * 12.5) if m <= T - 2 else 22815
        R[m] = {"ts": hm(m) + ":59", "spot": sp, "strikes": [
            {"k": k, "ce": {"oi": 5e6 if k == 22850 else (6e6 if m < T - 8 or not toot else 5e6) if k == 22750 else 1e6},
             "pe": {"oi": 2e6 + (max(0, min(m, T + 4) - (T - 6)) * 4e5 if k == 22800 else 0),
                    "ltp": 300 - 3 * (m - 555), "delta": -0.5}}
            for k in range(22500, 23050, 50)]}
    F = {m: (10 if m % 2 else -10) for m in range(555, T + 5)}
    F[T - 2], F[T - 1] = 100, 200
    if toot:
        F[T - 11], F[T - 10] = 100, 200
    ms_ = sorted(R)
    oi = [(ms(m), (fut or (lambda m: 10_000_000))(m)) for m in range(555, T + 5)]
    return {"bars": bars, "row": 5.0, "R": R, "ms": ms_, "F": F, "src": {}, "pushes": palat.pushes(F, ms_, 150), "oi": oi,
            "px": {m: R[m]["spot"] + 16 for m in R},
            "lot": 65, "zone": [{"t": hm(T - 3), "side": "SELL", "kind": "arm", "level": 22820.07}],
            "marks": [{"t": ms(T), "kind": "trap", "side": 1, "p": 22840}], "flow_of": "NIFTY"}


ROW = {"idx": "NIFTY", "onesided": {"type": "PIN"}, "setups": []}


def test_the_day_type_in_her_words():
    assert messages.din_line("PIN", "SELL") == "din PIN: palat ki ummeed"
    assert messages.din_line("CHOP", "BUY") == "din CHOP: palat ki ummeed"
    assert messages.din_line("TREND ▲", "SELL") == "din TREND ▲: price discovery ho sakti hai · fade khatra"
    assert messages.din_line("TREND ▼", "BUY") == "din TREND ▼: price discovery ho sakti hai · fade khatra"
    assert messages.din_line("TREND ▼", "SELL") == "din TREND ▼: trend ke saath"
    assert messages.din_line("MIXED", "SELL") == "din MIXED: saaf nahi"
    assert messages.din_line(None, "SELL") == "din: padh nahi sake"


def test_the_zone_line_ends_with_the_day_type_and_fires_as_before():
    """It fires as before: on the chip turning MATCH (messages.OFF keeps ARMED silent), the day type on the line."""
    chip = {"name": "ZONE", "side": "SELL", "state": "MATCH", "n": 3, "pieces": ["✓ a", "✓ b", "✓ c", "✗ d"]}
    row = {"idx": "NIFTY", "T": "12:45", "call": {"text": "?"}, "leg": {}, "setups": [chip], "onesided": {"type": "TREND ▲"}}
    ms_ = [m for m in messages.build([], [dict(row, T="12:40", setups=[]), row]) if m["kind"] == "SETUP"]
    assert [m["line"] for m in ms_] == [
        "12:45  NIFTY  ZONE SELL · 3/4 · ✓ a · ✓ b · ✓ c · ✗ d · din TREND ▲: price discovery ho sakti hai · fade khatra"]
    assert ms_[0]["key"] == "NIFTY|SETUP|12:45|ZONE SELL" and messages.SKIPPED["n"] == 0


def test_the_p_must_sit_at_the_swing_extreme():
    inp = scene()
    assert palat.swing(inp["marks"][0], inp["bars"], 5.0) == "TOP"
    small = dict(inp["marks"][0], p=22700)                               # 140 under the high, tol 62.5: chhota trap
    assert palat.swing(small, inp["bars"], 5.0) is None
    j = palat.judge("NIFTY", small, inp, ROW)
    assert j["swing"] is None and j["msg"] is None and j["checks"] == {}
    assert palat.swing(dict(inp["marks"][0], side=-1, p=22590), inp["bars"], 5.0) == "BOTTOM"


def test_the_flow_keeps_the_fullest_dext_row_and_sides_the_book_by_the_quote_rule():
    rows = [{"time": "2026-10-28 11:00:00", "delta": 650, "total_volume": 900},
            {"time": "2026-10-28 11:00:00", "delta": 6500, "total_volume": 9000},     # the closed bar, re-written
            {"time": "2026-10-28 11:01:00", "delta": 0, "total_volume": 0}]           # blank: absent, not quiet
    assert palat.dext_flow(rows, 65) == {660: 100}
    book = [{"t": ms(661, 1), "ltp": 100.0, "b": [[99.5, 1]], "a": [[100.0, 1]], "vtt": 0},
            {"t": ms(661, 2), "ltp": 100.0, "b": [[99.5, 1]], "a": [[100.0, 1]], "vtt": 650},   # at the ask: +10
            {"t": ms(661, 3), "ltp": 99.5, "b": [[99.5, 1]], "a": [[100.0, 1]], "vtt": 975}]    # at the bid: -5
    d, v = palat.book_flow(book, 65)
    assert d == {661: 5} and v == {661: 15.0}
    assert palat.flow({660: 100}, d, v) == ({660: 100, 661: 5}, {660: "D", 661: "B"})


def test_the_push_and_its_answer_are_fables():
    inp = scene()
    assert [(x["m"], x["lots"]) for x in inp["pushes"] if x["dir"] > 0] == [(650, 300), (659, 300)]
    assert palat.answer(inp["R"], inp["ms"], inp["pushes"][0], 665)["ans"] == "TOOT"
    p = [x for x in inp["pushes"] if x["dir"] > 0][-1]
    assert palat.answer(inp["R"], inp["ms"], p, 665) == {"ans": "NAHI", "k": 22850, "chg": 0.0, "bar": 3.0}
    assert palat.answer(inp["R"], inp["ms"], p, 663) is None              # its 4-min minute is not known by that close


def test_a_top_with_all_four_says_each_with_its_number():
    j = palat.judge("NIFTY", scene()["marks"][0], scene(), ROW)
    assert (j["swing"], j["n"], j["unk"]) == ("TOP", 4, 0)
    assert j["msg"]["line"] == ("11:05  NIFTY  TOP BAN SAKTA ▼ 4/4 · P 22,840f · zone SELL armed 22,820s · +9.2σ · "
                                "push 10:50 toot −10.0L → 10:59 +300 jawab nahi + put writers 22,800 +40.0L · aaj ka max · "
                                "fut OI flat +0 lots · "
                                "din PIN: palat ki ummeed")
    assert j["msg"]["kind"] == "SETUP" and j["msg"]["dir"] == -1


def test_three_of_four_names_the_missing_one_and_the_key_is_the_p_not_the_count():
    four = palat.judge("NIFTY", scene()["marks"][0], scene(), ROW)["msg"]
    inp = scene(fut=lambda m: 10_000_000 + max(0, m - 640) * 2_000)       # +0.4 % in 15 min while spot rose: FRESH
    three = palat.judge("NIFTY", inp["marks"][0], inp, ROW)["msg"]
    assert three["word"] == "TOP BAN SAKTA ▼ 3/4" and "· ✗ fut OI fresh +462 lots ·" in three["line"]
    assert three["key"] == four["key"] == "NIFTY|SETUP|11:05|TOP BAN SAKTA ▼|P%d+" % ms(660)


def test_a_p_posted_twice_a_tick_apart_is_one_trap_at_its_extreme():
    a, b = {"t": ms(660), "kind": "trap", "side": 1, "p": 22865}, {"t": ms(660), "kind": "trap", "side": 1, "p": 22866}
    low = {"t": ms(665), "kind": "trap", "side": -1, "p": 22800}
    assert palat.traps([a, low, b, dict(low, p=22801), {"t": ms(670), "kind": "absorption", "side": 1, "p": 1}]) == [b, low]


def test_a_missing_input_is_could_not_check_never_false():
    inp = dict(scene(), oi=[], zone=[])
    j = palat.judge("NIFTY", inp["marks"][0], inp, None)                  # no DECODE row, no zone row, no book OI
    assert j["checks"]["fut"] == [None, "fut OI"] and j["checks"]["zone"] == [None, "zone"] and j["unk"] == 2
    assert j["n"] == 2 and j["msg"] is None
    inp = dict(scene(chain=False), F={})
    j = palat.judge("NIFTY", inp["marks"][0], inp, ROW)
    assert j["checks"]["thakan"] == [None, "push ? · put likhai ?"]
    assert j["n"] == 3 and "· ? push ? · put likhai ? ·" in j["msg"]["line"] and "din PIN" in j["msg"]["line"]


def test_after_15_00_the_line_says_so():
    inp = scene(T=900)
    line = palat.judge("NIFTY", inp["marks"][0], inp, None)["msg"]["line"]
    assert line.startswith("15:05  NIFTY  TOP BAN SAKTA ▼ ") and line.endswith("· din: padh nahi sake · 3 baje ke baad")


def _put(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))


def test_load_reads_the_record_the_books_own_contract_and_niftys_flow_for_sensex():
    import dext_log
    _put(tape_log.marks_path(DAY, "NIFTY"), [{"t": ms(660), "kind": "trap", "side": 1, "p": 22840},
                                             {"t": ms(665), "kind": "absorption", "side": -1, "p": 22840}])
    _put(tape_log.day_path(DAY, "NIFTY"), [{"t": ms(655), "o": 1, "h": 2, "l": 1, "c": 2, "vol": 5, "rowSize": 5}])
    _put(os.path.join(str(chain_live.CHAIN_DIR), f"chain_SENSEX_{DAY}.jsonl"), [{"ts": "11:00:30", "spot": 73000, "strikes": []}])
    book = [{"t": ms(660, s), "ltp": 100.0, "b": [[99.5, 1]], "a": [[100.0, 1]], "vtt": 65 * s, "oi": 8e6,
             "ik": "NSE_FO|51345"} for s in range(3)]
    _put(book_log.day_path(DAY, "NIFTY"), book)
    _put(book_log.day_path(DAY, "SENSEX"), [{"t": ms(660), "ltp": 1.0, "b": [[1, 1]], "a": [[1, 1]], "vtt": 0, "oi": 9e4}])
    _put(dext_log.candles_path("NSE-51345", DAY), [{"time": f"{DAY} 10:59:00", "delta": 1300, "total_volume": 5000}])
    _put(dext_log.candles_path("NSE-48704", DAY), [{"time": f"{DAY} 10:58:00", "delta": 9e9, "total_volume": 9e9}])
    _put(trigger_log.PATH, [{"rule": "zone", "kind": "arm", "day": DAY, "index": "NIFTY", "t": "10:57", "side": "SELL",
                             "level": 22820.07}])
    n = palat.load(DAY, "NIFTY")
    assert [m["kind"] for m in n["marks"]] == ["trap"] and len(n["bars"]) == 1 and n["row"] == 5.0
    assert n["F"] == {659: 20, 660: 2} and n["src"] == {659: "D", 660: "B"}            # 48704 is not the book's contract
    assert n["oi"][0] == (ms(660), 8e6) and n["zone"][0]["level"] == 22820.07
    s = palat.load(DAY, "SENSEX")                                                         # §1q: NIFTY's flow, its own OI
    assert s["flow_of"] == "NIFTY" and s["F"] == n["F"] and s["oi"] == [(ms(660), 9e4)] and list(s["R"]) == [660]


def test_the_server_says_each_p_once_from_its_close_and_never_again_after_a_restart(monkeypatch):
    import server
    inp = scene()
    _put(tape_log.marks_path(DAY, "NIFTY"), inp["marks"])
    monkeypatch.setattr(palat, "load", lambda day, idx: inp)
    monkeypatch.setattr(server, "_PALAT", {"day": None, "done": {}})
    monkeypatch.setattr(server, "_MSG", server._msg_fresh())
    rows = [dict(ROW, T="11:05")]
    c = 665 * 60
    assert server._palat_pass(DAY, c + server.PALAT_WAIT_S - 1, rows) == []
    got = server._palat_pass(DAY, c + server.PALAT_WAIT_S, rows)
    assert [m["word"] for m in got] == ["TOP BAN SAKTA ▼ 4/4"]
    now = datetime(2026, 10, 28, 11, 7, 10, tzinfo=IST).timestamp()
    assert len(server._msg_write(DAY, got, now)) == 1
    assert server._msg_write(DAY, server._palat_pass(DAY, c + 200, rows), now) == []     # the next pass: nothing new
    monkeypatch.setattr(server, "_PALAT", {"day": None, "done": {}})                       # a restart
    monkeypatch.setattr(server, "_MSG", server._msg_fresh())
    assert server._msg_write(DAY, server._palat_pass(DAY, c + 300, rows), now) == []


def test_sensex_says_the_push_is_niftys():
    inp = dict(scene(), flow_of="NIFTY")                                  # §1q: SENSEX reads NIFTY's flow, labelled
    line = palat.judge("SENSEX", inp["marks"][0], inp, ROW)["msg"]["line"]
    assert line.startswith("11:05  SENSEX  TOP BAN SAKTA ▼ 4/4") and "· NIFTY push 10:50 toot −10.0L → 10:59 +300 jawab nahi + put" in line


def test_fut_oi_cover_passes_fresh_into_the_move_fails():
    cover = scene(fut=lambda m: 10_000_000 - max(0, m - 640) * 2_000)
    assert palat.judge("NIFTY", cover["marks"][0], cover, ROW)["checks"]["fut"] == [True, "fut OI cover −462 lots"]
    assert palat.fut_oi([(ms(m), 1e7 + (m - 640) * 2e3) for m in range(640, 665)], 665, 65, -1, scene()["R"],
                        scene()["ms"]) == (True, "fut OI fresh ulta +462 lots")   # risen against a BOTTOM's fall: not behind it


def test_the_writers_must_be_writers_at_the_extreme_and_the_days_biggest_add():
    inp = scene()
    for r in inp["R"].values():                                            # premium now rises: buyers opened it
        for s_ in r["strikes"]:
            s_["pe"]["ltp"] = 100 + 3 * (palat._hm2m(r["ts"]) - 555)
    assert palat.writers(1, 665, 22824, inp["R"], inp["ms"]) == (False, "put 22,800 +40.0L · kharidar")
    inp = scene()
    for m, r in inp["R"].items():                                          # a bigger add at 10:00 the same strike
        if 590 <= m:
            for s_ in r["strikes"]:
                if s_["k"] == 22800:
                    s_["pe"]["oi"] += 9e6
    assert palat.writers(1, 665, 22824, inp["R"], inp["ms"]) == (False, "put 22,800 +40.0L · aaj ka max nahi")
    assert palat.writers(1, 665, None, inp["R"], inp["ms"]) == (None, "put likhai ?")    # no basis: the P has no spot


def test_sigma_waits_30_minutes_of_bars():
    inp = scene()
    assert palat.band(inp["marks"][0], 1, inp["bars"][:5], 9999) == (None, "σ")
    six = inp["bars"][:5] + [dict(inp["bars"][-2], t=ms(580))]          # 09:15-09:45 with one rip bar
    assert palat.band(inp["marks"][0], 1, six, 9999)[0] is True


def test_a_trend_against_the_call_needs_4_of_4_and_says_khatra():
    up = dict(ROW, onesided={"type": "TREND ▲"})
    four = palat.judge("NIFTY", scene()["marks"][0], scene(), up)
    assert four["need"] == 4 and four["msg"]["line"].endswith(
        "· din TREND ▲: price discovery ho sakti hai · fade khatra · trend din: khatra")
    inp = scene(fut=lambda m: 10_000_000 + max(0, m - 640) * 2_000)
    j = palat.judge("NIFTY", inp["marks"][0], inp, up)
    assert j["n"] == 3 and j["msg"] is None                                # 3/4 on a trend against it: not sent
    assert palat.judge("NIFTY", inp["marks"][0], inp, dict(ROW, onesided={"type": "TREND ▼"}))["msg"] is not None


def test_the_day_budget_sends_three_and_keeps_the_rest_in_the_window(monkeypatch):
    import telegram_out
    ms_ = []
    for T in (660, 700, 740, 780):
        inp = scene(T=T)
        ms_.append(palat.judge("NIFTY", inp["marks"][0], inp, ROW)["msg"])
    monkeypatch.setattr(palat, "TELEGRAM_ON", True)
    out = palat.budget(list(reversed(ms_)))
    assert [m["t"] for m in out] == ["11:05", "11:45", "12:25", "13:05"]
    assert [telegram_out.wants(m) for m in out] == [True, True, True, False]
    assert out[3]["line"].endswith("· Telegram nahi: aaj ke 3 ho gaye") and out[3]["key"] == ms_[3]["key"]
    # the switch off (28 Oct's start): every line stays on the screen, none goes to Telegram, and each says why
    monkeypatch.setattr(palat, "TELEGRAM_ON", False)
    off = palat.budget(list(ms_))
    assert not any(telegram_out.wants(m) for m in off)
    assert all(m["line"].endswith("· screen par · Telegram band (parakh rahe)") for m in off)


def test_an_unanswered_push_counts_only_after_an_answered_one():
    """A129's sequence: the force had been cutting walls (TOOT / PHANS) and now gets nothing. A lone NAHI is the base
    rate at any extreme (Fable S4: 16-28 of 26-39 pushes a day), so it does not count alone."""
    inp = scene(toot=False)
    ok, chip = palat.thakan(1, 665, None, inp["R"], inp["ms"], inp["F"], inp["pushes"])
    assert (ok, chip) == (None, "push 10:59 +300 jawab nahi · pehle koi toot nahi · put likhai ?")
    inp = scene()
    assert palat.thakan(1, 665, None, inp["R"], inp["ms"], inp["F"], inp["pushes"]) == (
        True, "push 10:50 toot −10.0L → 10:59 +300 jawab nahi")
