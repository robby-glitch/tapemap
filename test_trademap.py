"""THE TRADE MAP (trademap.py, spec docs/superpowers/specs/2026-10-24-trade-map-design.md): one check per rule -- the push
and the ulta push, the range used against the 09:20 EM, the wall-ahead port, survivor-only zone reads, fuel pinned at
entry, and the server's merge into the one voice."""
import copy
import json

import fold
import trademap as M

DAY = "2026-10-23"                                      # Fri; the weekly expires Tue 27 Oct: N = 3 (23, 26, 27)
KS = [22400 + 50 * i for i in range(9)]                 # 22400 .. 22800
T = lambda hms: fold.ms(DAY, hms)                       # noqa: E731


def snap(ts, spot, pe=None, ce=None, ltp=60.0):
    """A chain row: ATM 22600's straddle 120 at 09:20; pe / ce = {k: oi} override a flat 10L."""
    return {"ts": ts, "spot": spot, "atm": round(spot / 50) * 50, "expiry": "2026-10-27",
            "strikes": [{"k": k, "ce": {"oi": (ce or {}).get(k, 1e6), "ltp": ltp, "delta": 0.5, "iv": 0.12},
                         "pe": {"oi": (pe or {}).get(k, 1e6), "ltp": ltp, "delta": -0.5, "iv": 0.12}} for k in KS]}


def view(d=-1, now="11:00:00", E=22640.0, fut=22620.0):
    return {"d": d, "E": E, "fut": fut, "t": T(now), "units": {"basis_ix": 20.0}}


TR = {"id": "x", "idx": "NIFTY", "k": 22600, "side": "PE", "role": "long", "t0": "10:00:30"}
FLOW = {"size": {"q": [0.0] * 90 + [2.0] * 11}, "slot_absd": {str(i): 100.0 for i in range(30, 70)},
        "slot_range": {str(i): 20.0 for i in range(30, 70)}, "slot_vp10": {str(i): 10.0 for i in range(30, 70)}}


def bar(hm, o, c, delta):
    s = int(hm[:2]) * 3600 + int(hm[3:5]) * 60
    return {"s": s, "e": s + 300, "o": o, "h": max(o, c), "l": min(o, c), "c": c, "vol": 100.0, "delta": delta, "src": "gc"}


def test_push_and_ulta_push_her_direction_closed_after_entry_and_ref_nahi_is_not_none():
    b5 = [bar("09:50", 22660, 22640, -300),            # ▼ PUSH, closed 09:55: before her 10:00 entry, not hers
          bar("10:20", 22650, 22630, -300),            # ▼ PUSH closed 10:25
          bar("10:35", 22630, 22640, 300),             # ▲ PUSH (ulta) closed 10:40, origin 22,630
          bar("10:45", 22640, 22638, -300)]            # ▼ but R = 2 / 20 < 0.25: no push
    rows = [snap("09:20:10", 22600), snap("10:59:00", 22600)]
    l4, push, ulta, _, _ = M.l4_line(-1, 10 * 60 + 1, 11 * 60, b5, {"gc": FLOW}, rows, DAY)
    assert push["t"] == "10:20" and ulta["t"] == "10:35"
    assert l4.startswith("push ▼ 10:20 (35 min) · ulta push ▲ 10:35 @ 22,630f · ")
    l4, _, _, _, _ = M.l4_line(-1, 10 * 60 + 1, 10 * 60 + 39, b5, {"gc": FLOW}, rows, DAY)
    assert "ulta push: none" in l4                                     # by now: the 10:40 close has not happened
    l4, _, _, _, _ = M.l4_line(1, 10 * 60 + 41, 11 * 60, b5, {"gc": FLOW}, rows, DAY)
    assert l4.startswith("push ▲ abhi nahi · ulta push: none")        # checked: none since her entry
    l4, push, ulta, _, _ = M.l4_line(-1, 10 * 60 + 1, 11 * 60, b5, {}, rows, DAY)
    assert l4.startswith("push ? ref nahi · din range") and push is None and "none" not in l4   # could not check


def test_range_used_is_the_session_spot_range_over_the_0920_straddle_em():
    rows = [snap("09:17:00", 22650), snap("09:20:10", 22600), snap("10:00:00", 22700), snap("10:59:00", 22650)]
    l4, _, _, rg, _ = M.l4_line(-1, 601, 11 * 60, [], {"gc": FLOW}, rows, DAY)
    assert rg["em"] == 86.6 and rg["used"] == round(100 / (120 / 0.8 / 3 ** 0.5), 2) == 1.15
    assert l4.endswith("din range 1.15 EM")
    _, _, _, rg, _ = M.l4_line(-1, 601, 11 * 60, [], {"gc": FLOW}, [snap("09:31:00", 22600)], DAY)
    assert "used" not in rg and rg["why"] == "no chain row 09:20–09:30"
    assert M.l4_line(-1, 601, 11 * 60, [], {}, [snap("09:31:00", 22600)], DAY)[0].endswith("din range ? — no 09:20 straddle")


def test_the_wall_ahead_is_the_nearest_strike_with_half_the_largest_oi():
    r = snap("11:00:00", 22610, pe={22550: 4e6, 22500: 10e6, 22450: 6e6, 22400: 2e6}, ce={22650: 9e6, 22700: 3e6})
    assert M.wall_nearest(r, "pe", -1, 22610)["k"] == 22500           # 22550 holds 40 % of the largest: not a wall
    assert M.wall_nearest(r, "ce", 1, 22610)["k"] == 22650
    m = M.read(TR, view(), [snap("09:20:10", 22600), r], [], {}, {}, None, 11 * 60)
    assert m["l5"] == "pullback zone 22,520f / 22,500s (110 pts) · 22500 PE 100.0L"   # fut = K + basis, pts = spot to the strike
    flat = snap("11:00:00", 22610, pe={k: None for k in KS})
    assert M.read(TR, view(), [flat], [], {}, {}, None, 11 * 60)["l5"] == "pullback zone: koi deewar nahi (checked ±8)"


def test_zone_reads_print_survivors_only_and_mirrors_print_nothing():
    r = snap("11:00:00", 22540, pe={22500: 10e6})                       # spot 40 above the wall: at the zone
    dec = lambda at, x: {655: {"effort": {"at": at, "x": x, "t": "10:58"}}}   # noqa: E731
    l5 = lambda d, dc, rr=r: M.read(dict(TR, side="CE" if d > 0 else "PE"), view(d), [rr], [], {}, dc, None, 11 * 60,  # noqa: E731
                                    [], T("10:55:00"))["l5"]           # the GoCharting tab alive, no print: nothing added
    assert l5(-1, dec("LOW", 0.44)).endswith("· 22500 PE 100.0L · EFFORT 0.44× sasta @ naya low")
    assert "EFFORT" not in l5(-1, dec("LOW", 2.3)) and "EFFORT" not in l5(-1, dec("HIGH", 0.4))   # the failed mirrors
    assert "EFFORT" not in l5(-1, {})                                                         # read nahi: no default
    up = snap("11:00:00", 22660, ce={22700: 10e6})
    assert l5(1, dec("HIGH", 2.3), up).endswith("· 22700 CE 100.0L · EFFORT 2.3× mehenga @ naya high")
    assert "EFFORT" not in l5(1, dec("LOW", 0.44), up)
    far = snap("11:00:00", 22610, pe={22500: 10e6})
    assert "EFFORT" not in l5(-1, dec("LOW", 0.44), far)                                      # not at the zone
    assert "EFFORT" not in l5(-1, {655: {"effort": {"at": "LOW", "x": 0.44, "t": "10:30"}}})  # a stale extreme


def test_bada_print_at_the_zone_is_hers_since_entry_and_a_closed_tab_is_could_not_check():
    r = snap("11:00:00", 22540, pe={22500: 10e6})                       # zone 22500 PE = 22,520f, at it (spot 40 above)
    E1 = lambda t, p, side=-1, shown=True: {"kind": "E1", "name": "BADA PRINT", "t": T(t), "time": t[:5], "side": side,  # noqa: E731
                                            "lots": 607, "p": p, "shown": shown}
    l5 = lambda pr, gc=T("10:55:00"): M.read(TR, view(), [r], [], {}, {}, None, 11 * 60, pr, gc)["l5"]  # noqa: E731
    assert l5([E1("10:40:00", 22530.0), E1("10:50:00", 22510.0, side=1)]).endswith("· BADA BUYER 607 lots @22,510f 10:50")
    assert "BADA" not in l5([E1("09:50:00", 22520.0)])                 # before her entry
    assert "BADA" not in l5([E1("11:00:00", 22520.0)])                 # its 5-min bar (11:00-11:05) has not closed yet
    assert "BADA" not in l5([E1("10:40:00", 22600.0)])                 # 80 pts from the zone: not at it
    assert "BADA" not in l5([E1("10:40:00", 22520.0, shown=False)])    # her decoder did not print it
    assert l5([], gc=None).endswith("· BADA ? GoCharting tab nahi")    # never posted: could not check, never "none"
    assert l5([], gc=T("10:40:00")).endswith("· BADA ? GoCharting tab nahi")   # 20 min silent
    vc = {"ok": True, "r_now": 0.5, "gauge": "W-BLEED 22700 CE −12.0% off 100.0L peak · 20 upd [M] · gauge, not a give-up alone"}
    det = M.into(vc, M.read(TR, view(), [r], [], {}, {}, None, 11 * 60, [], T("10:55:00")))["detail"]
    assert det[0]["text"].startswith("W-BLEED 22700 CE")                # A61: the bleed is a number in detail, never a WARN


def test_fuel_is_pinned_at_entry_and_a_missing_strike_is_could_not_check_never_zero():
    e = snap("10:00:10", 22610, pe={22600: 20e6, 22650: 30e6, 22700: 25e6, 22750: 5e6, 22800: 1e6})
    pk = snap("10:30:00", 22580, pe={22600: 22e6, 22650: 32e6, 22700: 26e6})
    now = snap("10:59:00", 22520, pe={22600: 10e6, 22650: 15e6, 22700: 12e6, 22750: 40e6})   # 22750 grew: not in the set
    f, fd = M.fuel(-1, [e, pk, now], "10:00:30")
    assert fd["ks"] == [22600, 22650, 22700] and fd["t0"] == "10:00"
    assert f["text"] == "fuel 22600/22650/22700 PE · entry 750L → now 370L · peak 800L 10:30"
    gone = copy.deepcopy(now)
    next(s for s in gone["strikes"] if s["k"] == 22650)["pe"]["oi"] = None
    f, fd = M.fuel(-1, [e, pk, gone], "10:00:30")
    assert f["text"] == "fuel: could not check — 22650 PE not in the snapshot" and fd["now"] is None


def test_levels_say_pd_not_fetched_and_a_sale_reads_its_premium_path():
    rows = [snap("09:20:10", 22640), snap("10:10:00", 22560), snap("10:59:00", 22620, pe={22600: 10e6})]
    m = M.read(dict(TR, side="CE", role="short"), view(-1), rows, [], {}, {}, None, 11 * 60)
    lv, pr = m["detail"][1]["text"], m["detail"][2]["text"]
    assert lv == "levels IB lo/LOD 22,560s/22,580f · PD ? — not fetched"
    assert pr.startswith("premium 60 = 20 intrinsic + 40 TV · theta ~₹") and "/hr [I] · at zone ≈ ₹50 [I]" in pr
    assert m["prem"]["theta_hr"] > 0 and m["prem"]["d10_prem"] is None
    m = M.read(TR, view(-1), rows, [], {}, {}, {"PDH": 22700, "PDL": 22500}, 11 * 60)
    assert m["detail"][1]["text"] == "levels IB lo/LOD 22,560s/22,580f · PDL 22,500s/22,520f" and len(m["detail"]) == 2


def test_the_server_keeps_the_map_off_hold2_merges_it_into_the_voice_and_logs_events_once(monkeypatch, tmp_path):
    import server
    import test_voice as TV
    tr = {"id": "x", "idx": "NIFTY", "t0": "10:07:30", "k": 23000, "side": "PE", "role": "long", "p0": 174.85}
    mp = {"ok": True, "l4": "push ▼ abhi nahi · ulta push: none · din range 0.77 EM", "l5": "pullback zone: koi deewar nahi (checked ±8)",
          "detail": [{"text": "fuel …", "tip": None}, {"text": "levels …", "tip": None}], "zone": None, "tag": "I"}
    monkeypatch.setattr(server, "_hold2", lambda rep, trades: dict(TV.h2(), map=mp))
    monkeypatch.setattr(server, "_VOICE", {})
    out = server._in_trade(TV.rep(), [tr])
    vc = out["voice"]
    assert "map" not in out["hold2"] and vc["state"] == "HOLD" and vc["l4"] == mp["l4"] and vc["l5"] == mp["l5"]
    assert [x["text"] for x in vc["detail"]] == ["fuel …", "levels …", "R +0.3 · BE lock at 2R"] and vc["map"]["tag"] == "I"
    monkeypatch.setattr(server, "_hold2", lambda rep, trades: TV.h2())
    vc = server._in_trade(TV.rep(), [tr])["voice"]                     # no map: the three lines alone, and why
    assert vc["ok"] and vc["l3"] and "l4" not in vc and vc["map_why"].startswith("could not check")
    monkeypatch.setattr(server, "MAP_DIR", str(tmp_path))
    monkeypatch.setattr(server, "_MAP_SEEN", {})
    ev = {"events": [{"event": "zone", "key": 22900, "t": "11:18", "k": 22900, "leg": "PE", "fut": 22926.0, "oi": 7.45e6,
                      "effort": None, "pts": 35.0}, {"event": "ulta_push", "key": "12:40", "t": "12:40", "origin": 22780.0, "fut": 22800.0}]}
    server._map_log(DAY, tr, {"d": -1, "E": 23003.2}, ev)
    server._map_log(DAY, tr, {"d": -1, "E": 23003.2}, ev)              # write-once per (trade, event, key)
    monkeypatch.setattr(server, "_MAP_SEEN", {})                       # a restart reads the disk first
    server._map_log(DAY, tr, {"d": -1, "E": 23003.2}, ev)
    got = [json.loads(x) for x in (tmp_path / f"map_{DAY}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(g["event"], g["key"]) for g in got] == [("zone", 22900), ("ulta_push", "12:40")]
    assert got[0]["effort"] is None and got[0]["E"] == 23003.2 and "outcome" not in got[0]


def test_voice_path_answers_today_only_after_1540_and_a_cached_path_as_is(monkeypatch, tmp_path):
    import time
    import server
    monkeypatch.setattr(server, "VOICE_DIR", str(tmp_path))
    today = time.strftime("%Y-%m-%d")
    lt = time.localtime()
    if time.strftime("%H:%M", lt) < server.VPATH_FROM:
        assert server._voice_path(today, "x")["why"] == "could not check — replay of today's trade after 15:40"
    (tmp_path / "path_2026-10-21_x.json").write_text(json.dumps({"ok": True, "rev": M.REV, "path": [{"t": "10:08", "voice": {"ok": True}}]}))
    assert server._voice_path("2026-10-21", "x")["path"][0]["t"] == "10:08"
