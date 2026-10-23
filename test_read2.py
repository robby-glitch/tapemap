"""test_read2.py -- READ-2 (docs/read/READ-2-PREREG.md, research-findings §1l): FUEL, LEG FLOW, the flow+fuel TREND,
JAGAH -- and read-1.1's word, unchanged, beside it (test_read.py is read-1.1's own and stays untouched)."""
import json

import frame_v2
import rank
import read
from test_read import day, fall, calls_above, no_puts

TAB = {"q": [round(-0.5 + k * 0.01, 4) for k in range(101)], "n": 101, "nd": 10}    # foi40: -0.5 % .. +0.5 % of OI
REF = {"foi40": [TAB] * 4}                                                           # one table per day-part


def ux(px_at, oi_at, start=33300, end=55800):
    """Upstox 5-min bar rows (ux_log): t ms whose IST second of day is the bar's start; close and OI at its last second."""
    return [{"t": (s - 19800) * 1000, "o": px_at(s), "h": px_at(s) + 5, "l": px_at(s + 299) - 5, "c": px_at(s + 299),
             "vol": 1000, "delta": -100, "oi": oi_at(s + 299)} for s in range(start, end, 300)]


def grind(sec):
    """22,520 at the open, a steady grind to 22,250 -- no bounce."""
    return 22520 - (sec - 33300) / (55800 - 33300) * 270


def slide(sec):
    """22,520 to 22,420: a gentle fall that keeps ATM +/- 2 inside the 22,300 .. 22,700 test chain all day."""
    return 22520 - (sec - 33300) / (55800 - 33300) * 100


def oi_falls_to_noon(s):
    return 1e6 * (1 - 0.0005 * (min(s, 43200) - 33300) / 60)        # -2 % every 40 minutes, flat from 12:00


def both(k, sec, s):
    return int((sec - 33300) / 60 * 10)


def down_price(monkeypatch):
    monkeypatch.setattr(read, "_price", lambda *a: {"vote": -1, "word": "TREND ▼", "raw": "TREND", "dir": -1, "tag": "I"})


def test_word_r1_is_read11_and_the_new_votes_absent_change_nothing(monkeypatch):
    """read-1.1's word sequence (no FUEL reference: the new votes absent) == READ-2's `word_r1` with them present, on
    every synthetic day here, held fields and events included; absent, `word` IS `word_r1`."""
    days = [day(fall, calls_above, no_puts), day(lambda s: fall(s) if s < 46800 else 22800, calls_above, no_puts),
            day(grind, both, both), day(fall, both, both), day(lambda s: 22480.0, both, both, flow_sell=0.5)]
    key = lambda r, w: (r["t"], r[w], r["dir"], r["since"], r["agree"], r["flip"], r["targets"], r["box"], r["warn"],
                        r["writers"], r["price"], r["flow"], r["basis"])
    fired = 0
    for patched in (False, True):
        if patched:
            down_price(monkeypatch)
        for D in days:
            b5 = ux(lambda s: D["spot"][read._at(D, s) or 0] + 50, oi_falls_to_noon)
            r1 = read.timeline(D, b5, None)                      # read-1.1: no reference, FUEL "could not check"
            r2 = read.timeline(D, b5, None, fuel_ref=REF)
            assert all(r["word"] == r["word_r1"] and r["src"] != "flow+fuel" for r in r1["rows"])
            assert all(r["fuel"]["vote"] is None for r in r1["rows"])
            assert [key(r, "word_r1") for r in r2["rows"]] == [key(r, "word") for r in r1["rows"]]
            base = [e for e in r2["events"] if e.get("src") != "flow+fuel"]
            assert [(e["t"], e["kind"], e["dir"]) for e in base] == [(e["t"], e["kind"], e["dir"]) for e in r1["events"]]
            fired += sum(r["src"] == "flow+fuel" for r in r2["rows"])
    assert fired                                                 # the overlay did fire on these days, and changed none of it


def ff_events(tl):
    return [(e["t"], e["kind"]) for e in tl["events"] if e.get("src") == "flow+fuel"]


def test_fuel_pulses_once_and_one_sided_leg_flow_holds_trend_flow_fuel(monkeypatch):
    """Amendment 1: FUEL is the trigger, latched for the leg; its 40-min burst fading never downgrades."""
    down_price(monkeypatch)
    calls_late = lambda k, sec, s: both(k, sec, s) * (10 if sec >= 50400 else 1)       # the call writers join at 14:00
    pulse = lambda s: 1e6 * (1 - 0.0005 * (min(s, 36000) - 33300) / 60)              # OI falls 09:15 -> 10:00 only
    D = day(slide, calls_late, both)
    tl = read.timeline(D, ux(lambda s: slide(s) + 50, pulse), None, fuel_ref=REF)
    rows = {r["t"]: r for r in tl["rows"]}
    assert rows["09:45"]["word"] == "LEAN" and rows["09:45"]["fuel"]["vote"] is None       # 40 minutes not there yet
    r = rows["10:00"]
    assert (r["word"], r["dir"], r["src"], r["word_r1"]) == ("TREND", -1, "flow+fuel", "LEAN")
    assert r["fuel"]["kind"] == "long liquidation" and r["fuel"]["rank"] >= 80 and r["legflow"]["vote"] == -1
    assert r["legflow"]["from"] == "09:15" and r["legflow"]["S"] == 1.0
    late = rows["11:30"]
    assert late["fuel"]["vote"] == 0 and (late["word"], late["src"]) == ("TREND", "flow+fuel")      # faded, still held
    assert late["fuel_leg"] == {"vote": -1, "kind": "long liquidation", "word": "long chhod rahe", "rank": 100.0,
                                "t": "10:00"}
    assert "fuel ▼ long chhod rahe p100 @10:00 · abhi p" in late["jagah"]["text"]
    assert ff_events(tl) == [("10:00", "UP")]
    assert not [e for e in tl["events"] if e["kind"] == "BREAK"]
    assert {x["since"] for x in tl["rows"] if x["t"] >= "09:45"} == {"09:45"}               # the read stands
    assert (rows["14:00"]["word"], rows["14:00"]["src"]) == ("TREND", "writers")             # read-1.1's own TREND
    c = read.card(D, tl)
    assert c["src"] == "writers" and c["word_r1"] == "TREND"
    assert [s["word"] for s in c["day"]] == ["LEAN ▼", "TREND ▼ · flow+fuel", "TREND ▼"]


def test_one_mark_leg_flow_dip_holds_three_in_a_row_downgrade(monkeypatch):
    down_price(monkeypatch)
    real = read.legflow
    off = {"11:00": 0, "12:00": 0, "12:05": None, "12:10": 0}     # one dip; then three in a row (one could not check)
    monkeypatch.setattr(read, "legflow", lambda F, sec, d, ext: dict(real(F, sec, d, ext), vote=off[read.hm(sec)])
                        if read.hm(sec) in off else real(F, sec, d, ext))
    D = day(slide, both, both)
    tl = read.timeline(D, ux(lambda s: slide(s) + 50, oi_falls_to_noon), None, fuel_ref=REF)
    rows = {r["t"]: r for r in tl["rows"]}
    assert [rows[t]["src"] for t in ("10:55", "11:00", "11:05", "12:00", "12:05")] == ["flow+fuel"] * 5
    assert (rows["12:10"]["word"], rows["12:10"]["src"]) == ("LEAN", None)
    # the latch outlives the downgrade inside the leg: the next mark with LEG FLOW back on is TREND · flow+fuel again
    assert ff_events(tl) == [("10:00", "UP"), ("12:10", "DOWN"), ("12:15", "UP")]
    dn = [e for e in tl["events"] if e.get("src") == "flow+fuel" and e["kind"] == "DOWN"][0]
    assert "3 mark" in dn["text"] and "?" in dn["text"] and "read khada hai" in dn["text"]
    assert not [e for e in tl["events"] if e["kind"] == "BREAK"]


def test_a_new_leg_or_a_reread_resets_the_fuel_latch():
    f = lambda v, r: {"vote": v, "rank": r, "kind": "long liquidation", "word": "long chhod rahe"}     # noqa: E731
    fuels = [(36000, f(-1, 97)), (36300, f(-1, 99)), (36600, f(0, 40)), (36900, f(None, None))]
    L = read._latch(fuels, -1, 35000, 33300)
    assert (L["vote"], L["rank"], L["t"], L["kind"]) == (-1, 99, "10:05", "long liquidation")       # max rank, its time
    assert read._latch(fuels, -1, 36400, 33300)["vote"] == 0        # a new session high at 10:06: a new leg, no fuel yet
    assert read._latch(fuels, -1, 35000, 36600)["vote"] == 0        # the read re-formed at 10:10: the latch starts there
    assert read._latch(fuels, -1, 36700, 33300)["vote"] is None     # the leg's only mark could not check
    assert read._latch(fuels, 1, 35000, 33300)["vote"] == 0         # no up-fuel in the leg
    assert read._latch([(36000, f(-1, 97)), (36300, f(-1, 97))], -1, 35000, 33300)["t"] == "10:00"   # tie: the first


def test_leg_flow_is_one_sidedness_since_the_extreme_and_a_short_leg_is_none():
    def F_of(deltas):                       # one 5-min bar per delta from 10:00, each one 1-s bar of 1,000 contracts
        return read.Flow([[36000 + 300 * n + 10, 225000, 1000, (1000 + dl) // 2] for n, dl in enumerate(deltas)])
    ext = {-1: 36000, 1: 36000}
    at = lambda n: 36000 + 300 * n
    F = F_of([-300, -200, 100, -400, -250, -300])          # sells 1,450 in 5 bars vs buys 100 in 1: S 0.94, M 2.9
    lf = read.legflow(F, at(6), -1, ext)
    assert (lf["vote"], lf["n"], lf["S"], lf["M"], lf["from"]) == (-1, 6, 0.94, 2.9, "10:00")
    assert read.legflow(F, at(5), -1, ext)["vote"] is None                                  # five bars: under six
    assert read.legflow(F_of([-200, -200, 150, -200, -200, 150]), at(6), -1, ext)["vote"] == 0   # S 0.73, M 1.33
    assert read.legflow(F_of([-300] * 6), at(6), -1, ext)["vote"] == -1                     # no buy bar: M passes
    assert read.legflow(F, at(6), 1, ext)["vote"] == 0                                      # the up leg: not one-sided
    late = read.legflow(F, at(6), -1, {-1: 35000})                                          # the leg began 09:55
    assert late["vote"] is None and late["why"].startswith(read.CC)
    assert read.legflow(F, at(6), 0, ext)["vote"] is None


def test_fuel_names_who_the_oi_says_is_acting_and_says_when_it_cannot_check():
    bars = lambda px, oi: rank.bars_of(ux(px, oi, 33300, 36600))         # 09:15 .. 10:05, eleven bars
    M = 36600                                                             # 10:10: the 40 minutes 09:25 -> 10:05
    up_oi, dn_oi = (lambda s: 1e6 * (1 + 0.0005 * (s - 33300) / 60)), (lambda s: 1e6 * (1 - 0.0005 * (s - 33300) / 60))
    up_px, dn_px = (lambda s: 22500 + (s - 33300) / 60), (lambda s: 22500 - (s - 33300) / 60)
    for px, oi, vote, kind, word in ((dn_px, dn_oi, -1, "long liquidation", "long chhod rahe"),
                                     (dn_px, up_oi, -1, "fresh shorts", "naye short"),
                                     (up_px, dn_oi, 1, "covering", "covering"), (up_px, up_oi, 1, "fresh longs", "naye long")):
        f = read.fuel(bars(px, oi), M, REF, 1)
        assert (f["vote"], f["kind"], f["word"]) == (vote, kind, word) and f["rank"] >= 80 and f["tag"] == "M"
    assert read.fuel(bars(dn_px, lambda s: 1e6), M, REF, 1)["vote"] == 0                   # OI flat: under p80
    for f in (read.fuel(bars(dn_px, dn_oi), M, None, 1), read.fuel(bars(dn_px, lambda s: None), M, REF, 1)):
        assert f["vote"] is None and f["why"].startswith(read.CC)                          # no reference / no OI


def test_live_equals_replay_on_the_new_fields(monkeypatch):
    """test_read's no-look-ahead check, with FUEL, LEG FLOW, the flow+fuel word and JAGAH all live at the cut."""
    down_price(monkeypatch)
    D = day(grind, both, both)
    b5 = ux(lambda s: grind(s) + 50, oi_falls_to_noon)
    lv = {"PDH": 22600.0, "PDL": 22300.0, "PDC": 22550.0}
    full = read.timeline(D, b5, lv, fuel_ref=REF)["rows"]
    cut = 11 * 3600 + 7 * 60
    n = read._at(D, cut) + 1
    part = {k: (v[:n] if k in ("t", "spot", "ce_oi", "pe_oi", "ce_ltp", "pe_ltp") else v) for k, v in D.items()}
    part["bars"] = [b for b in D["bars"] if b[0] <= cut]
    b5c = [b for b in b5 if (b["t"] // 1000 + 19800) % 86400 + 300 <= cut]
    live = read.timeline(part, b5c, lv, now=cut, fuel_ref=REF)["rows"]
    assert live and live[-1]["t"] == "11:05" and live[-1]["src"] == "flow+fuel" and live[-1]["jagah"]["room"]
    assert live == full[: len(live)]


def test_jagah_room_ahead_obstacle_behind_in_points_and_sigma_never_a_probability(monkeypatch):
    down_price(monkeypatch)
    D = day(grind, both, both)
    b5 = ux(lambda s: grind(s) + 50, oi_falls_to_noon)
    lv = {"PDH": 22600.0, "PDL": 22300.0, "PDC": 22550.0}
    tl = read.timeline(D, b5, lv, now=39660, fuel_ref=REF)              # to 11:00
    r = tl["rows"][-1]
    j, spot = r["jagah"], r["spot"]
    assert r["t"] == "11:00" and r["word"] == "TREND" and r["src"] == "flow+fuel"
    # room below: T1 22,400 (44 pts) beats the round 22,400 (a tie, T1 first) and PDL 22,300; the day low is spot itself
    assert j["room"]["name"] == "22,400 PE wall" and j["room"]["pts"] == round(spot - 22400)
    assert j["room"]["fut"] == round(22400 + r["basis"], 1) and isinstance(j["room"]["sig"], float)
    assert j["obstacle"]["name"] == f"FLIP {r['flip']:,.0f}" and j["obstacle"]["pts"] == round(r["flip"] - spot)
    assert j["fuel"] == {"vote": -1, "kind": "long liquidation", "rank": r["fuel"]["rank"], "word": "long chhod rahe"}
    assert j["fuel_leg"] == r["fuel_leg"] and j["fuel_leg"]["t"] == "10:00"          # the leg's latched fuel
    assert j["legflow"] == {"vote": -1, "S": 1.0, "M": None, "n": r["legflow"]["n"]}
    assert j["text"].startswith("▼ jagah ") and " to 22,400 PE wall · ▲ rukawat " in j["text"]
    assert j["text"].endswith(f"fuel ▼ long chhod rahe p100 @10:00 · abhi ▼ p{r['fuel']['rank']:.0f} · flow ▼ 100%")
    assert "\n" not in j["text"]
    # the card adds the extension's last push origin when it is behind price and nearer than FLIP; one in front is no
    # obstacle behind
    near = {"t": 1, "px": spot + r["basis"] + 3, "rank": 90, "failed": False}
    c = read.card(D, tl, lv, now=39660, push={"down": near, "up": None})
    assert c["jagah"]["obstacle"]["name"] == f"push {spot + 3:,.0f}" and c["jagah"]["obstacle"]["pts"] == 3
    assert "rukawat 3 pts to push" in c["jagah"]["text"] and c["jagah"]["room"] == j["room"]
    front = dict(near, px=spot + r["basis"] - 20)
    assert read.card(D, tl, lv, now=39660, push={"down": front, "up": None})["jagah"] == j
    assert read.card(D, tl, lv, now=39660)["jagah"] == j
    W = day(fall, calls_above, no_puts)                                  # WAIT: saaf nahi
    W["base_ce"], W["base_pe"] = {}, {}
    wait = read.timeline(W, [], None)["rows"][-1]
    assert wait["word"] == "WAIT" and wait["jagah"]["text"] == "saaf nahi" and wait["jagah"]["room"] is None


def test_range_jagah_is_the_box_walls(monkeypatch):
    monkeypatch.setattr(read, "_price", lambda *a: {"vote": 0, "word": "PIN/CHOP", "raw": "PIN", "dir": 0, "tag": "I"})
    r = read.timeline(day(lambda s: 22480.0, both, both, flow_sell=0.5), [], None)["rows"][-1]
    assert r["word"] == "RANGE"
    t = r["jagah"]["text"]
    assert f"▲ {round(r['box']['top']['k'] - 22480)} pts to TOP {r['box']['top']['k']:,.0f}" in t
    assert f"▼ {round(22480 - r['box']['bottom']['k'])} pts to BOTTOM {r['box']['bottom']['k']:,.0f}" in t


def test_frame_read_carries_src_jagah_and_the_size_word(monkeypatch):
    down_price(monkeypatch)
    D = day(grind, both, both)
    tl = read.timeline(D, ux(lambda s: grind(s) + 50, oi_falls_to_noon), None, now=39660, fuel_ref=REF)
    c = read.card(D, tl, None, now=39660)
    fr = frame_v2.read_part(c, tl, None)
    assert (fr["word"], fr["src"], fr["size"]) == ("TREND", "flow+fuel", "PURA") and fr["jagah"] == c["jagah"]
    assert set(fr["jagah"]) >= {"text", "room", "obstacle", "fuel", "legflow"}
    lean = read.timeline(D, [], None, now=39660)                       # no FUEL: read-1.1's LEAN, half size
    assert frame_v2.read_part(read.card(D, lean, None, now=39660), lean, None)["size"] == "ADHA"
    assert frame_v2.read_part(read.card(D, lean, None, now=39660), lean, None)["src"] is None


def test_the_read_log_carries_word_r1_beside_word_and_the_new_fields(tmp_path, monkeypatch):
    import server
    down_price(monkeypatch)
    monkeypatch.setattr(server, "READ_DIR", str(tmp_path))
    monkeypatch.setitem(server._READ, "seen", {})
    D = day(grind, both, both)
    tl = read.timeline(D, ux(lambda s: grind(s) + 50, oi_falls_to_noon), None, now=39660, fuel_ref=REF)
    server._read_log("2026-10-21", "NIFTY", tl)
    rows = [json.loads(x) for x in open(tmp_path / "read_2026-10-21.jsonl", encoding="utf-8")]
    m = [x for x in rows if x["kind"] == "mark" and x["t"] == "11:00"][0]
    assert (m["word"], m["word_r1"], m["src"], m["rev"]) == ("TREND", "LEAN", "flow+fuel", read.REV)
    assert m["fuel"]["vote"] == -1 and m["legflow"]["vote"] == -1 and m["jagah"]["text"].startswith("▼ jagah")
    assert m["fuel_leg"]["vote"] == -1 and m["fuel_leg"]["t"] == "10:00"
    assert [x["text"] for x in rows if x["kind"] == "event" and x.get("src") == "flow+fuel"][0].startswith("LEAN ▼ → TREND ▼")


def test_the_frame_push_is_validated_and_never_crashes_the_post():
    import server
    good = {"down": {"t": 1792554300000, "px": 23050.5, "rank": 92, "failed": False}, "up": None}
    assert server._push_clean(good) == good
    assert server._push_clean({"down": {"t": 1792554300000, "px": 23050.5, "rank": 92.0, "failed": True}})["down"]["rank"] == 92
    for bad in (None, 5, "x", [], {"down": "x"}, {"down": {"t": "1", "px": 1, "rank": 1, "failed": False}},
                {"up": {"t": 1, "px": float("nan"), "rank": 1, "failed": False}},
                {"up": {"t": 1, "px": 1.0, "rank": True, "failed": False}}, {"up": {"t": 1, "px": 1.0, "rank": 1, "failed": 0}},
                {"down": good["down"], "up": {"t": 1, "px": -5, "rank": 1, "failed": False}}):
        assert server._push_clean(bad) is None                    # one malformed side: the whole push is refused
    assert server._push_clean({"down": None, "up": None}) == {"down": None, "up": None}    # nothing known: a real answer


def test_post_frame_stores_the_latest_push_per_index_and_absent_or_bad_is_fine(tmp_path, monkeypatch):
    import server
    from test_frame_api import _Req, _tape
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    monkeypatch.setattr(server, "_PUSH", {})
    push = {"down": {"t": 1757563500000, "px": 25010.0, "rank": 88, "failed": False}, "up": None}
    for body in ({**_tape(), "push": push}, _tape(), {**_tape(), "push": {"down": {"px": "x"}}}, {**_tape(), "push": 7}):
        req = _Req("/api/frame", body)
        server.Handler.do_POST(req)
        assert req.out[-1][0] == 200 and req.out[-1][1]["ok"] is True
    assert server._PUSH["NIFTY"] == {"day": "2026-09-11", "push": push}       # absent and bad posts left the last good one
    assert server._push_for("NIFTY", "2026-09-11") == push and server._push_for("NIFTY", "2026-09-12") is None


def test_fades_read_stamp_stays_read11s_word():
    """confluence's §1 `read` stamp is read-1.1's word (FADE's registration predates READ-2): word_r1 when the log row
    has it, `word` on a pre-READ-2 row."""
    import confluence as C
    from test_confluence import bar
    s = {"i": 0, "t": "10:00", "first_touch": True, "depth": 1, "extreme": 98.0, "session_hl": (104.0, 97.0),
         "side": "BUY", "kind": C.POCKET}
    b = [bar("10:00", 99, 98, 98.9)]
    assert C.stamps(s, b, {}, "10:00", read=[{"t": "09:55", "word": "TREND", "word_r1": "LEAN"}])["read"] == "LEAN"
    assert C.stamps(s, b, {}, "10:00", read=[{"t": "09:55", "word": "LEAN"}])["read"] == "LEAN"



def test_the_read_log_waits_for_a_marks_bar_to_land(tmp_path, monkeypatch):
    """A16 (21 Oct NIFTY 10:05): the log wrote RANGE before the 10:00 bar closed and the day replays LEAN. Live, a mark
    or event at T is written only from T + _READ_LOG_GRACE; the next call writes it from the data that landed."""
    import server
    down_price(monkeypatch)
    monkeypatch.setattr(server, "READ_DIR", str(tmp_path))
    monkeypatch.setitem(server._READ, "seen", {})
    D = day(grind, both, both)
    tl = read.timeline(D, ux(lambda s: grind(s) + 50, oi_falls_to_noon), None, now=39600, fuel_ref=REF)
    assert tl["rows"][-1]["t"] == "11:00"
    path = tmp_path / "read_2026-10-21.jsonl"
    server._read_log("2026-10-21", "NIFTY", tl, now=39600 + server._READ_LOG_GRACE - 1)
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert max(x["t"] for x in rows if x["kind"] == "mark") == "10:55"            # 11:00 waits
    assert all(x["t"] < "11:00" for x in rows)                                    # and so do its events
    server._read_log("2026-10-21", "NIFTY", tl, now=39600 + server._READ_LOG_GRACE)
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert [x["t"] for x in rows if x["kind"] == "mark"].count("11:00") == 1
