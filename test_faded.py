"""FADE-D (faded.py, FADE-D-PREREG.md, research-findings §1n): one synthetic test per rule, the ▲/▼ mirror, no look-ahead,
the forward log's write-once timing and the scorer's gate. Nothing here reads data/. Prices are futures; minutes are IST
minutes of the day; a bar is named by its opening minute, a reading by its close."""
import json
import os
import sys

import pytest

import faded as F
import hold2

M = lambda hhmm: int(hhmm[:2]) * 60 + int(hhmm[3:])        # noqa: E731


def b5(hhmm, h, l, c, delta, vol=1000, o=None):
    return {"s": M(hhmm) * 60, "o": c if o is None else o, "h": h, "l": l, "c": c, "vol": vol, "delta": delta,
            "src": "gc"}


def top():
    """09:15 the leg's biggest buying bar; new highs at 09:20 (half of it) and 09:25 (a fifth: 2a); 09:30 the first
    selling bar (2b); 09:35 sells again with the close still above VWAP."""
    return [b5("09:15", 110, 99, 108, 400, vol=5000), b5("09:20", 112, 105, 111, 200), b5("09:25", 115, 109, 114, 80),
            b5("09:30", 114, 108, 110, -50), b5("09:35", 111, 106, 109, -60), b5("09:40", 110, 104, 105, -90)]


LEAD = {M("09:20"): 20.0, M("09:25"): 30.0, M("09:30"): 35.0, M("09:35"): 33.0, M("09:40"): 22.0, M("09:45"): 18.0}


def lead(d=LEAD):
    return {k: {"pe": v, "why": None} for k, v in d.items()}


def ep_of(bars, zone=(), side="SELL", lead_=None):
    eps = [e for e in F.episodes(bars, list(zone)) if e["side"] == side]
    return eps, [F.evaluate(e, bars, lead_ or lead()) for e in eps]


# ---- 1. LOCATION ------------------------------------------------------------------------------------------------------

def test_location_is_a_new_session_high_or_a_zone_arm_or_entry_and_the_first_bar_never_is():
    bs = top()
    locs = F.locations(bs, [], "SELL")
    assert [(x["bar"], x["close"], x["why"]) for x in locs] == [("09:20", M("09:25"), ["high"]),
                                                               ("09:25", M("09:30"), ["high"])]
    # a 3-min row is known at its close (t + 3) and sits in the 5-min bar holding minute t + 2
    zone = [{"t": "09:33", "side": "SELL", "kind": "arm"}, {"t": "09:36", "side": "SELL", "kind": None},
            {"t": "09:27", "side": "SELL", "kind": "arm"}, {"t": "09:33", "side": "BUY", "kind": "arm"}]
    got = {x["bar"]: x["why"] for x in F.locations(bs, zone, "SELL")}
    assert got["09:35"] == ["zone arm 09:33", "zone entry 09:36"]
    assert got["09:25"] == ["high", "zone arm 09:27"]                      # the 09:27 bar closes 09:30: the 09:25 bar
    assert [x["bar"] for x in F.locations(bs, zone, "BUY")] == ["09:35"]   # its side's rows only (no new low here)


def test_a_session_that_does_not_begin_at_0915_cannot_say_new_high_but_zone_rows_still_locate():
    bs = top()[1:]                                                         # the 5-min record begins 09:20
    assert F.locations(bs, [], "SELL") == []
    assert [x["bar"] for x in F.locations(bs, [{"t": "09:27", "side": "SELL", "kind": "arm"}], "SELL")] == ["09:25"]
    eps, evs = ep_of(bs, [{"t": "09:27", "side": "SELL", "kind": "arm"}])
    assert evs[0]["bars"][0]["a"]["ok"] is None and "09:20" in evs[0]["bars"][0]["a"]["why"]


def test_an_episode_chains_location_bars_within_30_min_and_splits_beyond():
    bs = top() + [b5(f"{9 + (35 + 5 * k) // 60:02d}:{(35 + 5 * k) % 60:02d}", 104, 100, 102, -10)
                  for k in range(2, 12)]                                   # 09:45 .. 10:30, no new high
    bs.append(b5("10:35", 120, 102, 119, 300))                             # a new high 65 min after 09:25's close
    eps = [e for e in F.episodes(bs, []) if e["side"] == "SELL"]
    assert [(e["t"], e["end"], [x["bar"] for x in e["locs"]]) for e in eps] == [
        ("09:25", M("10:00"), ["09:20", "09:25"]), ("10:40", M("11:10"), ["10:35"])]


# ---- 2a / 2b / 3 ------------------------------------------------------------------------------------------------------

def test_2a_a_new_high_on_at_most_a_quarter_of_the_up_legs_biggest_buying_bar():
    bs = top()
    r = F.ratio(bs, 2, "SELL")                                             # the 09:25 bar: 80 / 400
    assert (r["bar"], r["big_bar"], r["big"], r["ratio"], r["ok"]) == ("09:25", "09:15", 400, 0.2, True)
    assert F.ratio(bs, 1, "SELL")["ratio"] == 0.5 and F.ratio(bs, 1, "SELL")["ok"] is False
    # the leg starts at the last session low before the bar: a deeper low resets the leg's biggest bar
    bs2 = bs[:4] + [b5("09:35", 109, 90, 92, -500), b5("09:40", 100, 92, 99, 120), b5("09:45", 116, 99, 115, 100)]
    r = F.ratio(bs2, 6, "SELL")
    assert (r["leg_from"], r["big_bar"], r["ratio"], r["ok"]) == ("09:35", "09:40", round(100 / 120, 3), False)
    # a new high on selling is fading buying by arithmetic
    bs3 = bs[:2] + [b5("09:25", 115, 109, 114, -20)]
    assert F.ratio(bs3, 2, "SELL")["ok"] is True


def test_2b_the_last_bar_sells_and_cvd_sits_below_its_up_leg_peak():
    bs = top()
    b = F.cvd_turn(bs, 3, "SELL")                                          # at the 09:35 close (the 09:30 bar)
    assert (b["delta"], b["cvd"], b["peak"], b["dd"], b["ok"]) == (-50, 630, 680, 50, True)
    assert F.cvd_turn(bs, 2, "SELL")["ok"] is False                        # the 09:25 bar still bought
    bs[3] = b5("09:30", 114, 108, 110, 0)
    assert F.cvd_turn(bs, 3, "SELL")["ok"] is False                        # a flat bar is not < 0


def test_3_the_pe_lead_10_points_off_its_session_peak_with_the_peak_in_15_min_or_a_10_point_fall():
    r = F.lead_read(lead(), M("09:35"), "SELL")
    assert (r["now"], r["peak"], r["peak_t"], r["off"], r["ok"]) == (33.0, 35.0, "09:30", 2.0, False)
    r = F.lead_read(lead(), M("09:40"), "SELL")
    assert (r["now"], r["peak"], r["off"], r["chg15"], r["ok"]) == (22.0, 35.0, 13.0, -8.0, True)
    # the peak 25 min old: only a 10-point fall over 15 min passes
    old = {M("09:20"): 50.0, M("09:25"): 41.0, M("09:30"): 40.0, M("09:35"): 35.0, M("09:40"): 30.0, M("09:45"): 31.0}
    assert F.lead_read(lead(old), M("09:45"), "SELL")["ok"] is False      # 15 min ago 40 -> 31: a 9-point fall
    assert F.lead_read(lead(old), M("09:40"), "SELL")["ok"] is True       # 41 (09:25) -> 30: an 11-point fall
    # unread now is could not check, never a verdict
    gap = lead({**LEAD, M("09:40"): None})
    assert F.lead_read(gap, M("09:40"), "SELL")["ok"] is None
    # BUY reads the CE lead: the PE lead's negative
    neg = lead({k: -v for k, v in LEAD.items()})
    assert F.lead_read(neg, M("09:40"), "BUY")["ok"] is True and F.lead_read(neg, M("09:40"), "BUY")["side"] == "CE"


def test_leads_are_read_writers_nine_strikes_at_each_close_and_stale_rows_are_unread():
    ks = [22300.0 + 50 * j for j in range(9)]
    X = {"step": 50, "ks": ks, "t": [33300, 33590, 33890], "spot": [22500.0, 22510.0, 22505.0],
         "ce_oi": [[1000] * 9, [1010] * 9, [1020] * 9], "pe_oi": [[1000] * 9, [1030] * 9, [1060] * 9],
         "base_ce": {k: 1000 for k in ks}, "base_pe": {k: 1000 for k in ks}}
    L = F.leads(X, [M("09:20"), M("09:25"), M("09:35")])
    assert L[M("09:20")]["pe"] == pytest.approx(100 * (270 - 90) / 360)        # the 09:19:50 row: PE +30 x 9, CE +10 x 9
    assert L[M("09:25")]["pe"] == pytest.approx(100 * (540 - 180) / 720)       # the 09:24:50 row, nothing after it
    assert L[M("09:35")]["pe"] is None and "09:24" in L[M("09:35")]["why"]       # 10 min old: stale


# ---- 4. ENTRY, 5. STOP ------------------------------------------------------------------------------------------------

def test_entry_is_the_first_close_with_1_2a_2b_3_above_vwap_and_one_per_episode():
    eps, evs = ep_of(top())
    ev = evs[0]
    by = {r["close"]: r for r in ev["bars"]}
    assert [by["09:35"][k]["ok"] for k in ("a", "b", "oi")] == [True, True, False]
    assert [by["09:40"][k]["ok"] for k in ("a", "b", "oi", "px")] == [True, True, True, True]
    assert ev["entry"]["t"] == "09:40" and ev["entry"]["E"] == 109
    assert by["09:45"]["oi"]["ok"] is True and ev["entry"]["t"] == "09:40"   # 09:45 holds too: one entry only
    assert ev["entry"]["vwap"]["side"] == "far" and ev["entry"]["vwap"]["c"] == 109


def test_amendment_1_the_close_across_vwap_still_enters_and_the_side_is_only_stamped():
    bs = top()
    bs[4] = b5("09:35", 111, 100, 101, -60)                                # 09:40 close back under VWAP
    ev = ep_of(bs)[1][0]
    row = next(r for r in ev["bars"] if r["close"] == "09:40")
    assert row["px"]["ok"] is False                                         # the reading is still on the row
    e = ev["entry"]
    assert (e["t"], e["E"], e["vwap"]["side"]) == ("09:40", 101, "across")
    assert e["vwap"]["vwap"] == round(F.vwaps(bs)[4], 2) and e["vwap"]["pts"] < 0
    # the bottom mirror: a close back above VWAP still enters the BUY, stamped "across"
    ev = ep_of(mirror(bs), side="BUY", lead_=lead({k: -v for k, v in LEAD.items()}))[1][0]
    e = ev["entry"]
    assert (e["t"], e["E"], e["d"], e["vwap"]["side"]) == ("09:40", 99, 1, "across") and e["vwap"]["pts"] > 0


def test_no_entry_after_1500():
    flat = [b5(f"{m // 60:02d}:{m % 60:02d}", 100, 99, 99.5, 1) for m in range(M("09:15"), M("14:45"), 5)]
    tail = [b5("14:45", 110, 99, 108, 400, vol=60000), b5("14:50", 112, 105, 111, 200), b5("14:55", 115, 109, 114, 80),
            b5("15:00", 114, 108, 110, -50), b5("15:05", 111, 106, 109, -60)]
    ld = lead({M("14:50"): 20.0, M("14:55"): 30.0, M("15:00"): 35.0, M("15:05"): 33.0, M("15:10"): 22.0})
    eps, evs = ep_of(flat + tail, lead_=ld)
    rows = {r["close"]: r for r in evs[-1]["bars"]}
    assert rows["15:10"]["late"] is True and [rows["15:10"][k]["ok"] for k in ("a", "b", "oi")] == [True, True, True]
    assert evs[-1]["entry"] is None


def test_stop_is_the_session_high_plus_a_quarter_u_with_half_a_sigma_of_risk_at_least():
    bs = top()
    tr = F.trade("SELL", bs, 4)
    sg = hold2.sigma_at(bs, M("09:40"))
    U = max(sg, 0.001 * 115)
    assert tr["extreme"] == 115 and tr["stop"] == pytest.approx(round(max(115 + 0.25 * U, 109 + 0.5 * sg), 2))
    # the floor binds when the high is within half a sigma of the entry
    bs2 = bs[:4] + [b5("09:35", 115, 106, 114.9, -60)]
    tr2 = F.trade("SELL", bs2, 4)
    sg2 = hold2.sigma_at(bs2, M("09:40"))
    assert tr2["stop"] == pytest.approx(round(max(115 + 0.25 * max(sg2, 0.115), 114.9 + 0.5 * sg2), 2))


# ---- ▲ / ▼ mirror, no look-ahead ---------------------------------------------------------------------------------------

def mirror(bars):
    return [dict(b, o=200 - b["o"], h=200 - b["l"], l=200 - b["h"], c=200 - b["c"], delta=-b["delta"]) for b in bars]


def test_a_bottom_is_the_mirror_buy():
    eps, evs = ep_of(mirror(top()), side="BUY", lead_=lead({k: -v for k, v in LEAD.items()}))
    sell = ep_of(top())[1][0]
    assert eps[0]["t"] == "09:25" and evs[0]["entry"]["t"] == sell["entry"]["t"] == "09:40"
    e, s = evs[0]["entry"], sell["entry"]
    assert (e["E"], e["extreme"], e["d"]) == (200 - s["E"], 200 - s["extreme"], 1)
    assert e["stop"] == pytest.approx(200 - s["stop"], abs=0.02)
    for a, b in zip(evs[0]["bars"], sell["bars"]):
        assert [a[k]["ok"] for k in ("a", "b", "oi", "px")] == [b[k]["ok"] for k in ("a", "b", "oi", "px")]


def test_no_look_ahead_every_close_reads_the_same_with_the_inputs_cut_there():
    bs = top() + [b5("09:45", 118, 104, 117, 500), b5("09:50", 117, 110, 111, -40)]
    zone = [{"t": "09:33", "side": "SELL", "kind": "arm"}, {"t": "09:45", "side": "SELL", "kind": None}]
    ld = {**LEAD, M("09:50"): 25.0, M("09:55"): 12.0}
    full = ep_of(bs, zone, lead_=lead(ld))[1][0]
    for r in full["bars"]:
        c = M(r["close"])
        cb = [b for b in bs if b["s"] // 60 + 5 <= c]
        cz = [z for z in zone if M(z["t"]) + 3 <= c]
        cut = ep_of(cb, cz, lead_=lead({k: v for k, v in ld.items() if k <= c}))[1][0]
        assert next(x for x in cut["bars"] if x["close"] == r["close"]) == r
    assert full["entry"]["t"] == "09:40"


# ---- 6. EXIT: HOLD v2 and the VWAP reference ---------------------------------------------------------------------------

def test_exits_are_hold_v2_from_the_stop_and_the_vwap_target_reference():
    entry = {"t": "09:40", "E": 109.0, "stop": 116.0, "d": -1, "extreme": 115}
    ones = [{"t": f"09:{m:02d}", "h": 109.5, "l": 108.5, "c": 109.0, "vwap": 106.0} for m in range(40, 45)]
    ones += [{"t": "09:45", "h": 108.0, "l": 105.5, "c": 106.0, "vwap": 106.0}]      # touches VWAP
    sess = {"ones": ones, "bars": []}
    x = F.exits(entry, sess, ({}, {}), None, [], "push ? ref nahi")
    assert (x["vwap_ref"]["how"], x["vwap_ref"]["exit_t"], x["vwap_ref"]["R"]) == ("target", "09:46", round(3 / 7, 4))
    assert (x["v2"]["how"], x["v2"]["converted"]) == ("mark", None)        # HOLD v2 §exit only: no VWAP decision
    ones[-1] = {"t": "09:45", "h": 117.0, "l": 108.0, "c": 116.5, "vwap": 106.0}
    x = F.exits(entry, sess, ({}, {}), None, [], None)
    assert (x["v2"]["how"], x["v2"]["exit"], x["vwap_ref"]["how"]) == ("line_init", 116.0, "stop")


def test_an_entry_across_vwap_never_exits_at_vwap_and_its_vwap_reference_is_na():
    entry = {"t": "09:40", "E": 104.0, "stop": 116.0, "d": -1, "extreme": 115,
             "vwap": {"c": 104.0, "vwap": 106.0, "side": "across", "pts": -2.0}}
    ones = [{"t": f"09:{m:02d}", "h": 106.5, "l": 103.5, "c": 104.0, "vwap": 106.0} for m in range(40, 60)]  # VWAP every bar
    x = F.exits(entry, {"ones": ones, "bars": []}, ({}, {}), None, [], None)
    assert (x["v2"]["how"], x["v2"]["exit_t"], x["v2"]["converted"]) == ("mark", "10:00", None)
    assert (x["vwap_ref"]["how"], x["vwap_ref"]["R"]) == ("n/a (entry across VWAP)", None)
    # the bottom mirror
    up = dict(entry, E=96.0, stop=84.0, d=1, vwap={"c": 96.0, "vwap": 94.0, "side": "across", "pts": 2.0})
    mo = [{"t": b["t"], "h": 200 - b["l"], "l": 200 - b["h"], "c": 200 - b["c"], "vwap": 94.0} for b in ones]
    x = F.exits(up, {"ones": mo, "bars": []}, ({}, {}), None, [], None)
    assert (x["v2"]["how"], x["v2"]["exit_t"], x["vwap_ref"]["R"]) == ("mark", "10:00", None)


# ---- the forward log (confluence_log.log_faded) ------------------------------------------------------------------------

def _inp(bars, zone=(), ld=None):
    return {"bars5": bars, "zone": list(zone), "lead": lead(ld or LEAD), "why": None}


def test_log_faded_writes_one_row_per_episode_once_its_30_min_window_has_closed(tmp_path, monkeypatch):
    import confluence_log as L
    import trigger_log
    p = tmp_path / "c.jsonl"
    monkeypatch.setattr(L, "_seen", None)
    monkeypatch.setattr(L, "_faded_slot", {})
    bs = top() + [b5(f"{m // 60:02d}:{m % 60:02d}", 104, 101, 102, -5) for m in range(M("09:45"), M("10:05"), 5)]
    monkeypatch.setattr(L, "faded_inputs", lambda idx, day, now=None, lead=True: _inp(
        [b for b in bs if b["s"] + 300 <= now], (), LEAD))
    assert L.log_faded("NIFTY", now="10:00", path=str(p)) == 0         # the window (to 10:00) is still open
    assert L.log_faded("NIFTY", now="10:01", path=str(p)) == 1         # closed + the grace minute
    assert L.log_faded("NIFTY", now="10:02", path=str(p)) == 0         # the same 5-min slot: not checked again
    assert L.log_faded("NIFTY", now="10:06", path=str(p)) == 0         # write-once
    monkeypatch.setattr(L, "_seen", None)                              # a restart re-reads the keys
    monkeypatch.setattr(L, "_faded_slot", {})
    assert L.log_faded("NIFTY", now="10:11", path=str(p)) == 0
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    r = rows[0]
    assert (r["setup"], r["index"], r["side"], r["t"], r["entry"]["t"]) == ("FADE-D", "NIFTY", "SELL", "09:25", "09:40")
    b = next(x for x in r["bars"] if x["close"] == "09:40")
    assert (b["a"]["bars"][-1]["ratio"], b["b"]["dd"], b["oi"]["now"], b["oi"]["peak"], b["oi"]["chg15"]) == (
        0.2, 110, 22.0, 35.0, -8.0)
    assert not any(k in r for k in ("R", "exit", "outcome", "v2"))
    assert not os.path.exists(trigger_log.PATH)                         # it writes nothing anywhere else


def test_log_faded_is_fail_soft_and_retries_at_the_next_bar(tmp_path, monkeypatch):
    import confluence_log as L
    p = tmp_path / "c.jsonl"
    monkeypatch.setattr(L, "_seen", None)
    monkeypatch.setattr(L, "_faded_slot", {})
    monkeypatch.setattr(L, "faded_inputs", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    assert L.log_faded("NIFTY", now="11:00", path=str(p)) == 0
    monkeypatch.setattr(L, "faded_inputs", lambda idx, day, now=None, lead=True: _inp(top()))
    assert L.log_faded("NIFTY", now="11:00", path=str(p)) == 0         # the failed slot is used: no retry loop
    assert L.log_faded("NIFTY", now="11:05", path=str(p)) == 1
    assert '"setup": "FADE-D"' in p.read_text(encoding="utf-8")


def test_zone_rows_are_one_index_days_arms_and_entries_without_an_outcome_field(tmp_path):
    import confluence_log as L
    p = tmp_path / "tl.jsonl"
    base = {"day": "2026-10-22", "index": "NIFTY", "t": "09:33", "side": "SELL", "band": "u2", "rule": "zone",
            "kind": "arm", "mfe": 9, "stop_hit": True, "gate": {"legal": False}}
    rows = [base, base, dict(base, kind=None, t="09:45"), dict(base, index="SENSEX"), dict(base, day="2026-10-21"),
            dict(base, kind="outcome"), dict(base, rule="5c")]
    p.write_text("".join(json.dumps(r) + "\n" for r in rows) + "{torn", encoding="utf-8")
    got = L.zone_rows("NIFTY", "2026-10-22", str(p))
    assert [(z["t"], z["kind"]) for z in got] == [("09:33", "arm"), ("09:45", None)]
    assert not {"mfe", "stop_hit"} & set(got[0])


# ---- tools/faded_score.py ----------------------------------------------------------------------------------------------

def _score():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import faded_score
    return faded_score


def test_the_prereg_sha_is_checked(tmp_path):
    fs = _score()
    p = tmp_path / "x.md"
    p.write_text("changed", encoding="utf-8")
    assert fs.sha_ok(p) is False


def test_dry_counts_only_forward_rows_from_1022_and_run_refuses_below_20(tmp_path, monkeypatch, capsys):
    fs = _score()
    import confluence_log as L
    p = tmp_path / "c.jsonl"
    ent = {"t": "09:40", "E": 109, "stop": 116, "d": -1}
    rows = [{"setup": "FADE-D", "day": "2026-10-21", "index": "NIFTY", "side": "SELL", "t": "09:25", "locs": [{}],
             "bars": [], "entry": ent},
            {"setup": "FADE-D", "day": "2026-10-22", "index": "BANKNIFTY", "side": "BUY", "t": "10:25", "locs": [{}, {}],
             "bars": [], "entry": dict(ent, d=1)},
            {"setup": "FADE", "day": "2026-10-22", "index": "NIFTY", "side": "SELL", "t": "09:30", "entry": ent}]
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    monkeypatch.setattr(L, "PATH", str(p))
    monkeypatch.setattr(fs, "OUT_JSON", str(tmp_path / "v.json"))
    assert fs.main([]) == 0
    out = capsys.readouterr().out
    assert "BUY BANKNIFTY" in out and "IN-SAMPLE" in out
    n = fs.counts(fs.forward_rows())
    assert n["BUY BANKNIFTY"]["entries"] == 1 and n["BUY BANKNIFTY"]["locs"] == 2 and n["SELL NIFTY+SENSEX"]["rows"] == 0
    assert fs.main(["--run"]) == 2
    out = capsys.readouterr().out
    assert "REFUSED" in out and not os.path.exists(tmp_path / "v.json")
    assert "hit" not in out.lower() and "win rate" not in out.lower()


def test_describe_in_sample_is_labelled_and_never_counted(monkeypatch, capsys):
    fs = _score()
    monkeypatch.setattr(fs, "describe_day", lambda idx, day, D, out: out(f"  {idx} {day} (described)") or [])
    assert fs.main(["--describe-in-sample", "--day", "2026-10-21"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("FADE-D -- IN-SAMPLE") and "NEVER counted" in out and "NIFTY 2026-10-21 (described)" in out
    assert fs.main(["--describe-in-sample", "--day", "2026-10-22"]) == 2     # a forward day is never in-sample


# ---- tools/decode_now.py: facts, never a verdict ---------------------------------------------------------------------------

def test_decode_now_lists_the_signs_present_as_facts_without_a_verdict():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import decode_now as dn
    bs = top()[:5]                                                          # closed by 09:40
    leg = dn.leg_of(bs)
    assert (leg["d"], leg["from_bar"], leg["to_bar"], leg["to"]) == (1, "09:15", "09:25", 115)
    rows = dn.delta_rows(bs)
    assert [(r["bar"], r["pct"], r["ext"], bool(r["fading"])) for r in rows][1:3] == [("09:20", 50, "H", False),
                                                                                    ("09:25", 20, "H", True)]
    # 2026-10-22: decode_now's signs are decode.py's (the app's DECODE block), one source of truth
    g = {"idx": "NIFTY", "now": M("09:40") * 60, "leg": leg, "fd": dn.fade_now(bs, lead(), leg), "bars5": bs,
         "vwap": F.vwaps(bs)[-1], "pushes": None, "push": None}
    g.update(dleg=g["leg"], dfd=g["fd"])          # A1: the call reads the DECODE leg (here the session leg, no swing)
    dec, con = dn.decode.signs(g, [{"idx": "SENSEX", "leg": {"d": 1}, "dleg": {"d": 1}}])
    dec, con = [x for _, x in dec], [x for _, x in con]
    text = " ".join(dec + con).lower()
    assert "nayi high 09:25 · 20% effort" in dec and "Δ −60 leg ke khilaf" in dec
    assert "PE lead peak se −13" in dec                                     # 35 @09:30 -> 22 @09:40
    assert "SNX ▲ saath" in con and any(x.startswith("VWAP ke upar") for x in con)
    for w in ("sell now", "buy now", "probab", "likely", "chance", "confidence", "hit rate", "win rate"):
        assert w not in text
