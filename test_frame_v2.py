"""frame_v2.py (the extension v2's read / plan / writers / ux_flow) and its wiring into POST /api/frame."""
import json
import os
import threading
import types

import frame_v2 as F
import server
import tape_log
from test_frame_api import _Req, _tape

VW, SG = 22600.0, 20.0                          # SELL zone 22,580..22,600; -1.5 sigma 22,570; -2 sigma 22,560


def _bar(s, h=22595, l=22585, c=22590, delta=-1, vwap=VW, sig=SG):
    return {"s": s, "e": s + 180, "o": c, "h": h, "l": l, "c": c, "v": 100, "delta": delta, "vwap": vwap, "sig": sig}


def _rows(word="TREND", d=-1, upto=55800, targets=()):
    out = []
    for sec in range(33600, upto + 1, 300):
        w = word if sec >= 35100 else "BAN RAHA"
        out.append({"t": F.hm(sec), "word": w, "dir": d if w in ("TREND", "LEAN") else 0, "targets": list(targets),
                    "basis": 50.0})
    return out


def _day(special):
    """Neutral 3-min bars 09:15 .. 10:30 with `special` {start sec: bar} swapped in."""
    return [special.get(s) or _bar(s) for s in range(33300, 37800, 180)]


def _at(bars, rows, now, basis=None):
    return F.plan([b for b in bars if b["e"] <= now], [r for r in rows if F._sec(r["t"]) <= now], basis, now)


def test_plan_waits_until_0945():
    p, why = F.plan(_day({})[:10], _rows(), None, 35000)
    assert why is None and p["state"] == "WAIT_0945" and p["zone"] is None and "09:45" in p["why"]


def test_plan_arms_triggers_stops_and_rearms_at_one_and_a_half_sigma():
    S = 35100                                     # 09:45
    bars = _day({S + 180: _bar(S + 180, h=22590, l=22570, c=22575, delta=-50),         # 09:48 the §E bar -> ENTRY
                 S + 360: _bar(S + 360, h=22610, l=22590, c=22605, delta=30),          # 09:51 close > VWAP -> STOP
                 S + 540: _bar(S + 540),                                               # 09:54 nothing -> NOT_ARMED
                 S + 720: _bar(S + 720, h=22590, l=22569, c=22585),                    # 09:57 low <= -1.5 sigma -> re-arm
                 S + 900: _bar(S + 900, h=22590, l=22570, c=22575, delta=-40)})        # 10:00 -> ENTRY again
    rows = _rows()
    p, _ = _at(bars, rows, S + 180)
    assert p["state"] == "ARMED" and p["zone"] == {"lo": 22580.0, "hi": 22600.0, "name": "SELL −1σ…VWAP"}
    assert p["kill"]["fut"] == 22600.0 and p["t1"]["fut"] == 22560.0 and p["t2"] == {"fut": 22540.0, "name": "−3σ"}
    p, _ = _at(bars, rows, S + 360)
    assert p["state"] == "TRIGGERED" and p["trigger"] == {"t": "09:51", "px": 22575, "delta": -50}
    assert p["rows"][-1]["what"] == "ENTRY"
    p, _ = _at(bars, rows, S + 540)
    assert p["state"] == "STOPPED" and p["rows"][-1]["what"] == "STOP" and p["trigger"] is None
    p, _ = _at(bars, rows, S + 720)
    assert p["state"] == "NOT_ARMED"
    p, _ = _at(bars, rows, S + 900)
    assert p["state"] == "ARMED" and [r["what"] for r in p["rows"]] == ["ENTRY", "STOP"]    # the re-arm bar never triggers
    p, _ = _at(bars, rows, S + 1080)
    assert p["state"] == "TRIGGERED" and p["since"] == "10:03"


def test_a_bar_whose_delta_cannot_be_read_is_never_a_trigger():
    S = 35100
    bars = _day({S + 180: _bar(S + 180, h=22590, l=22570, c=22575, delta=None)})
    p, _ = _at(bars, _rows(), S + 360)
    assert p["state"] == "ARMED" and p["rows"][-1]["what"] == "?" and p["trigger"] is None


def test_t2_is_the_nearer_of_three_sigma_and_the_reads_wall_only_with_a_plausible_basis():
    ok = F.basis_band(22500, 50.0, 10)
    rows = _rows(targets=[{"k": 22500, "oi": 1, "side": "PE"}])       # 22,500 + 50 = 22,550: between -2 and -3 sigma
    p, _ = _at(_day({}), rows, 35280, ok)
    assert p["t2"] == {"fut": 22550.0, "spot": 22500, "name": "PE wall 22,500"}
    p, _ = _at(_day({}), rows, 35280, F.basis_band(22500, 4.0, 10))    # implausible basis: no wall, -3 sigma
    assert p["t2"]["name"] == "−3σ"


def test_range_fades_her_pockets_and_wait_has_no_plan():
    p, why = _at(_day({}), _rows("RANGE", 0), 36000)
    assert why is None and p["state"] == "FADE" and p["kill"] is None and p["t1"] == {"fut": 22600.0, "name": "VWAP"}
    assert p["zones"] == [{"side": "buy", "lo": 22540.0, "hi": 22560.0}, {"side": "sell", "lo": 22640.0, "hi": 22660.0}]
    p, why = _at(_day({}), _rows("WAIT", 0), 36000)
    assert p is None and "WAIT" in why


def test_the_plan_refuses_when_the_ticks_cannot_carry_her_vwap():
    bars = [b for b in _day({}) if b["s"] not in (33300, 33480)]          # a late start: 09:15 and 09:21 missing
    p, why = _at(bars, _rows(), 36000)
    assert p is None and "could not check" in why and "09:15" in why
    one = [b for b in _day({}) if b["s"] != 33300]                         # a single missing bar is tolerated
    assert _at(one, _rows(), 36000)[0] is not None


def test_basis_band_the_three_days():
    assert F.basis_band(22950, 6.0, 11)["ok"] is False                     # 16 Oct: +6 at 11 DTE is not carry
    assert F.basis_band(22500, 24.8, 8)["ok"] is True                      # 19 Oct
    assert F.basis_band(22400, 90.0, 14)["ok"] is True                     # 13 Oct
    b = F.basis_band(22950, 6.0, 11)
    assert b["expected"] == 47.0 and b["lo"] == 13.5 and b["hi"] == 95.3 and "implausible" in b["why"]
    assert F.basis_band(22500, 50.0, None)["lo"] == 20.0 and "fixed" in F.basis_band(22500, 50.0, None)["why"]
    nv = F.basis_band(22500, None, 8)
    assert nv["ok"] is False and nv["v"] is None and "could not check" in nv["why"]
    assert F.dte("2026-10-16", "2026-10-27") == 11 and F.dte("2026-10-16", None) is None


def _X(n=40):
    """A chain every 60 s from 09:15: CE adding 10k/row at 22,500, PE flat; spot 22,510."""
    ks = [22400.0, 22450.0, 22500.0, 22550.0, 22600.0]
    t = [33300 + 60 * i for i in range(n)]
    ce = [[1000, 1000, 1000 + 10 * i, 1000, 1000] for i in range(n)]
    pe = [[1000, 1000, 1000, None, 1000] for i in range(n)]
    return {"step": 50, "t": t, "spot": [22510.0] * n, "ks": ks, "ce_oi": ce, "pe_oi": pe, "ce_ltp": ce, "pe_ltp": pe,
            "base_ce": {}, "base_pe": {}, "bars": [[s, 225100, 65, 40] for s in range(33300, 33300 + 60 * n, 10)],
            "lot": 65, "bf": 0, "flow_from": 33300, "pre": [(33299, 10, 5), (33400, 1, 1)]}


def test_writers_rank_fresh_and_the_absent_side():
    ref = {"q": [x * 10 for x in range(101)], "n": 500}                   # 0, 10, ..., 1000
    tl = {"rows": [{"writers": {"cls": "CALL", "A": 0.6, "ce": 900, "pe": 10}}],
          "events": [{"t": "10:00", "kind": "QUIT", "k": 22450, "side": "PE", "text": "22,450 PE likhne wale bhage"},
                     {"t": "10:00", "kind": "FORM", "text": "x"}]}
    w = F.writers_part(_X(), 33300 + 60 * 39, ref, tl)                    # 09:54: row 39 against row 9
    assert w["ok"] and w["atm"] == 22500 and [s["k"] for s in w["strikes"]] == [22400, 22450, 22500, 22550, 22600]
    s = {x["k"]: x for x in w["strikes"]}
    assert s[22500]["ce30"] == 300 and s[22500]["ce_rank"] == 30 and s[22500]["ce_fresh"] is False
    assert s[22550]["pe30"] is None and s[22550]["pe_rank"] is None and s[22550]["pe_fresh"] is None   # missing, not 0
    assert w["absent"] == "PE" and w["n_ref"] == 500 and w["quits"] == [{"t": "10:00", "k": 22450, "side": "PE", "text": "22,450 PE likhne wale bhage"}]
    hot = F.writers_part(_X(), 33300 + 60 * 39, {"q": [x for x in range(101)], "n": 101}, tl)
    assert {x["k"]: x for x in hot["strikes"]}[22500]["ce_fresh"] is True                         # p100 add
    early = F.writers_part(_X(), 34000, ref, tl)
    assert early["strikes"] == [] and "09:45" in early["why"]


def test_cut_leaves_nothing_after_t():
    X = _X()
    T = 33300 + 60 * 20 + 30
    c = F.cut(X, T)
    assert max(c["t"]) <= T and all(b[0] <= T for b in c["bars"]) and all(p[0] <= T for p in c["pre"])
    assert len(c["t"]) == len(c["spot"]) == len(c["ce_oi"]) == len(c["pe_ltp"]) == 21
    assert len(X["t"]) == 40                                              # the caller's arrays are untouched


def test_bars3_aligned_closed_and_in_lots():
    ticks = [[33300 + i, 225000 + (i % 7), 130, 100] for i in range(0, 400)]      # 400 s of 2-lot ticks, 100 of 130 bought
    b = F.bars3(ticks, 65, now=33300 + 400)
    assert [x["s"] for x in b] == [33300, 33480]                          # the 09:21 bar is still forming
    assert b[0]["v"] == 360 and b[0]["delta"] == round((2 * 100 - 130) * 180 / 65)
    assert b[0]["h"] == 22500.6 and b[0]["l"] == 22500.0 and b[0]["sig"] >= 0


def test_ux_flow_only_closed_bars_last_six():
    bars = [{"t": 1000 + i * 300000, "delta": i, "vol": 10} for i in range(10)]
    u = F.ux_part(bars, 1000 + 8 * 300000)
    assert [x["delta"] for x in u["bars"]] == [2, 3, 4, 5, 6, 7] and u["why"] is None
    assert F.ux_part([], 5)["why"].startswith("could not check")


# ---- the wire ----------------------------------------------------------------------------------------------------

DAY = "2026-09-11"


def _v2_fixture(monkeypatch, tmp_path):
    for k in ("parts", "busy", "ref", "building"):
        server._V2[k].clear()
    monkeypatch.setattr(server, "_board_clock", lambda: (DAY, "10:00"))
    monkeypatch.setattr(server.frame_log, "day_path", lambda day: str(tmp_path / f"frame_{day}.jsonl"))
    import v2feed
    monkeypatch.setattr(v2feed, "with_day", lambda day, fn, data_dir=None: fn(types.SimpleNamespace(idx={"NIFTY": None})))
    parts = {"read": {"ok": True, "word": "TREND"}, "read_why": None, "plan": None, "plan_why": "READ WAIT · zone nahi",
             "writers": {"ok": True, "strikes": []}, "ux_flow": {"bars": [], "why": "x"}}
    monkeypatch.setattr(server, "_v2_parts", lambda *a, **k: parts)
    os.makedirs(server.RANK_DIR, exist_ok=True)
    ref = {"v": 1, "id": "rank-NIFTY-2026-09-11-abcdef12", "before": DAY, "idx": "NIFTY", "writers30": None}
    with open(os.path.join(server.RANK_DIR, f"rank_ref_NIFTY_{DAY}.json"), "w") as f:
        json.dump(ref, f)
    return ref


def _post(body):
    req = _Req("/api/frame", body)
    server.Handler.do_POST(req)
    return req.out[-1][1]


def test_a_v2_post_gets_the_new_keys_and_the_table_once(tmp_path, monkeypatch):
    ref = _v2_fixture(monkeypatch, tmp_path)
    old = _post(_tape())                                                  # today's page: nothing new, nothing missing
    assert old["ok"] and not {"read", "plan", "writers", "ux_flow", "rank_ref_id", "rank_ref"} & set(old)
    first = _post({**_tape(), "build": "v2-test", "rank_have": None})
    assert set(old) <= set(first)                                         # every old key still rides
    for k in ("read", "read_why", "plan", "plan_why", "writers", "ux_flow", "rank_ref_id", "rank_ref_why"):
        assert k in first, k
    assert first["read"]["word"] == "TREND" and first["rank_ref_id"] == ref["id"] and first["rank_ref"]["id"] == ref["id"]
    again = _post({**_tape(), "build": "v2-test", "rank_have": ref["id"]})
    assert "rank_ref" not in again and again["rank_ref_id"] == ref["id"]
    assert "rank_ref" not in _post({**_tape(), "build": "v2-test"})       # no rank_have: never the big table
    assert "rank_ref" not in server._SENSES["frame"]["NIFTY"]             # GET /api/frame never carries it


def test_a_missing_reference_serves_the_older_one_as_stale_then_the_built_one(tmp_path, monkeypatch):
    _v2_fixture(monkeypatch, tmp_path)
    os.remove(os.path.join(server.RANK_DIR, f"rank_ref_NIFTY_{DAY}.json"))
    with open(os.path.join(server.RANK_DIR, "rank_ref_NIFTY_2026-09-10.json"), "w") as f:
        json.dump({"id": "rank-NIFTY-2026-09-10-00000000", "before": "2026-09-10"}, f)
    gate = threading.Event()
    calls = []

    def build(idx, day, data_dir=None):
        gate.wait(5)
        calls.append(day)
        return {"id": f"rank-{idx}-{day}-11111111", "idx": idx, "before": day}
    fake = types.SimpleNamespace(build=build, write=lambda ref, d: os.path.join(d, "x"))
    monkeypatch.setattr(server, "_rank_mod", lambda: fake)
    j = _post({**_tape(), "rank_have": None})
    assert j["rank_ref_id"] == "rank-NIFTY-2026-09-10-00000000" and j["rank_ref"]["stale_from"] == "2026-09-10"
    assert "stale" in j["rank_ref_why"]
    gate.set()
    for t in threading.enumerate():
        if t.name == f"rank-NIFTY-{DAY}":
            t.join(5)
    j = _post({**_tape(), "rank_have": "rank-NIFTY-2026-09-10-00000000"})
    assert j["rank_ref_id"] == f"rank-NIFTY-{DAY}-11111111" and j["rank_ref"]["before"] == DAY and calls == [DAY]


def test_marks2_rows_are_written_once_per_id_status_tier(tmp_path, monkeypatch):
    _v2_fixture(monkeypatch, tmp_path)
    m = {"id": "trap@1", "t": 1757563500000, "kind": "trap", "p": 22500.0, "lots": 300, "trapped": -1, "winner": 1,
         "rank": 93, "n": 41, "tier": "solid", "status": "TIKA", "junk": "dropped"}
    _post({**_tape(), "build": "v2-test", "marks2": [m, dict(m)]})
    _post({**_tape(), "build": "v2-test", "marks2": [m]})                   # the every-second re-post
    _post({**_tape(), "build": "v2-test", "marks2": [m, dict(m, status="TOOTA", status_t=1757563800000, break_px=22480)]})
    rows = tape_log._read(tape_log.marks2_path(DAY, "NIFTY"))
    assert [r["status"] for r in rows] == ["TIKA", "TOOTA"]
    assert rows[0]["day"] == DAY and rows[0]["idx"] == "NIFTY" and "junk" not in rows[0] and rows[1]["break_px"] == 22480
    tape_log._seen_marks2.clear()                                          # a restart re-seeds from the file
    assert tape_log.append_marks2({"marks2": [m]}, DAY, "NIFTY") == 0
    assert str(tmp_path) in os.path.abspath(tape_log.marks2_path(DAY, "NIFTY"))


def test_v21_marks2_logs_every_mark_with_its_tag_direction(tmp_path, monkeypatch):
    """v2.1: the page logs EVERY mark the board and decoder produce (drawn or not), so a day's log runs past 200 rows; the
    flow tag keeps its own direction (flow_dir: whose push) apart from the mark's winner."""
    _v2_fixture(monkeypatch, tmp_path)
    rows = [{"id": f"E5@{i}", "t": 1757563500000 + i, "kind": "E5", "p": 22500.0 + i, "winner": 1, "tier": "count",
             "status": "TIKA", "flow": "PUSH", "flow_dir": -1} for i in range(260)]
    _post({**_tape(), "build": "v2-test", "marks2": rows})
    got = tape_log._read(tape_log.marks2_path(DAY, "NIFTY"))
    assert len(got) == 260 and got[0]["flow_dir"] == -1 and got[0]["winner"] == 1


def test_v23_marks2_keeps_the_forward_record_and_writes_each_resolution_once(tmp_path, monkeypatch):
    """v2.3: each row carries the KHEL it was born under, its 60-minute hold (TIKA / TOOTA / open) and which side traded
    0.5U first; the row is written again only when that record moves on, and the every-second re-post writes nothing."""
    _v2_fixture(monkeypatch, tmp_path)
    m = {"id": "absorption@1", "t": 1757563500000, "kind": "absorption", "p": 22500.0, "winner": 1, "tier": "solid",
         "status": "TIKA", "khel": "FADE", "hold": "open", "first": "open"}
    _post({**_tape(), "build": "v2-test", "marks2": [m]})
    _post({**_tape(), "build": "v2-test", "marks2": [m]})
    _post({**_tape(), "build": "v2-test", "marks2": [dict(m, first="WITH")]})
    _post({**_tape(), "build": "v2-test", "marks2": [dict(m, first="WITH", hold="TIKA")]})
    _post({**_tape(), "build": "v2-test", "marks2": [dict(m, first="WITH", hold="TIKA")]})
    rows = tape_log._read(tape_log.marks2_path(DAY, "NIFTY"))
    assert [(r["hold"], r["first"], r["khel"]) for r in rows] == [("open", "open", "FADE"), ("open", "WITH", "FADE"), ("TIKA", "WITH", "FADE")]



# ---- decode-loop D6: the basis's second witness -------------------------------------------------------------------

def test_d6_the_options_confirm_a_basis_the_carry_model_calls_implausible():
    """16 Oct: NIFTY +2..+12 at 11 DTE against a carry of ~47. The options' parity forward said the same; the carry
    band alone hid every fut level. With the options agreeing within 0.1% of spot it is plausible, flagged."""
    ok = F.basis_band(22950, 6.0, 11, parity=14.5)
    assert ok["ok"] is True and ok["unusual"] is True and "options" in ok["why"]
    no = F.basis_band(22950, 6.0, 11, parity=60.0)
    assert no["ok"] is False and "options say +60.0" in no["why"]
    assert F.basis_band(22950, 6.0, 11)["ok"] is False                           # no witness: the old answer


def test_d6_parity_basis_is_the_atm_synthetic_carried_to_the_future():
    ks = [22400.0, 22450.0, 22500.0, 22550.0, 22600.0]
    t = list(range(40000, 41000, 60))
    spot = 22500.0
    ce = [[round((max(spot - k, 0) + 60) * 20) for k in ks] for _ in t]
    pe = [[round((max(k - spot, 0) + 60 - 10) * 20) for k in ks] for _ in t]       # C - P = spot - K + 10
    X = {"t": t, "spot": [spot] * len(t), "ks": ks, "step": 50, "ce_ltp": ce, "pe_ltp": pe,
         "expiry": "2026-10-27", "fut_expiry": "2026-10-27"}
    assert F.parity_basis(X, t[-1], "2026-10-20") == 10.0
    assert F.parity_basis({**X, "expiry": None}, t[-1], "2026-10-20") is None



# ---- decode-loop Phases 0-1 on the wire ---------------------------------------------------------------------------

def test_the_page_never_receives_the_reads_ranks(tmp_path, monkeypatch):
    """One reference serves both: the extension gets its tables, never TapeMap's `read` section (~200 KB)."""
    ref = _v2_fixture(monkeypatch, tmp_path)
    with open(os.path.join(server.RANK_DIR, f"rank_ref_NIFTY_{DAY}.json"), "w") as f:
        json.dump(dict(ref, read={"marks": {}, "pool": {}, "kinds": {}}), f)
    server._V2["ref"].clear()
    j = _post({**_tape(), "build": "v2-test", "rank_have": None})
    assert j["rank_ref"]["id"] == ref["id"] and "read" not in j["rank_ref"] and "writers30" in j["rank_ref"]


def test_api_read_carries_ranks_coverage_and_the_basis_band_and_at_cuts_a_replay(tmp_path, monkeypatch):
    import v2feed
    import test_v2feed as V
    d, _files, _v = V._day(tmp_path, n_chain=60, n_book=600)
    D = v2feed.Day(V.DAY, d)
    monkeypatch.setattr(v2feed, "with_day", lambda day, fn, data_dir=None: (D.refresh(), fn(D))[1])
    server._READ["cache"].clear()
    for k in ("ref", "building"):
        server._V2[k].clear()
    os.makedirs(server.RANK_DIR, exist_ok=True)
    for idx in ("NIFTY", "BANKNIFTY", "SENSEX"):                       # a reference with a read section: no build
        with open(os.path.join(server.RANK_DIR, f"rank_ref_{idx}_{V.DAY}.json"), "w") as f:
            json.dump({"id": f"rank-{idx}-test", "before": V.DAY, "read": {"marks": {}, "pool": {}, "kinds": {}}}, f)
    out = server._read_reply(V.DAY, "NIFTY", "09:20")
    c = out["indices"]["NIFTY"]
    assert out["asof"] == "09:20" and c["ok"] and c["t"] == "09:20"
    assert {"ranks", "coverage", "basis_band", "hl", "wb"} <= set(c)
    assert c["ranks"]["ce"]["tag"] == "?" and c["ranks"]["ce"]["why"]   # no reference day: "?", never a rank of zero
    kinds = {r["kind"] for r in c["coverage"]}
    assert kinds <= {"ok", "none", "cnc", "hidden"} and "hidden" in kinds  # a replay hides levels, and says so


def test_v22_a_late_joined_bar_keeps_its_partial_flag(tmp_path, monkeypatch):
    """v2.2 / D4: the page now posts a bar it joined late (flagged) instead of never posting it; the record keeps the flag, so
    an undercounted bar is never read as a whole one."""
    monkeypatch.setattr(tape_log, "DIR", str(tmp_path / "tape"))
    bar = {"t": 1757563500000, "o": 1, "h": 2, "l": 0, "c": 1, "vol": 10, "delta": 1, "buy": 5, "sell": 4, "oi": 1, "fromTicks": True, "partial": True, "ladder": []}
    tape_log.append({"session": f"NIFTY-I|5m|{DAY}", "closed": [bar]}, DAY, "NIFTY")
    assert tape_log._read(tape_log.day_path(DAY, "NIFTY"))[0]["partial"] is True


def test_bars3_width_60_gives_one_minute_bars_and_default_is_unchanged():
    import frame_v2
    t0 = frame_v2.OPEN_S
    ticks = [[t0 + s, 225000 + s, 10, 6] for s in range(0, 360)]          # 6 minutes of 1-s bars
    b3 = frame_v2.bars3(ticks, 1, now=t0 + 360)
    b1 = frame_v2.bars3(ticks, 1, now=t0 + 360, width=60)
    assert [b["s"] - t0 for b in b3] == [0, 180]
    assert [b["s"] - t0 for b in b1] == [0, 60, 120, 180, 240, 300]
    assert b1[0]["h"] == 22505.9 and b1[0]["l"] == 22500.0
