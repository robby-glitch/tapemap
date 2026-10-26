"""confluence.py / confluence_log.py: one synthetic test per CONFLUENCE-PREREG.md rule, the no-look-ahead proof, the
outcome-field firewall, and the forward log's write-once timing. Nothing here reads data/."""
import datetime
import json
import os
import time

import confluence as C
import confluence_log as L
import fronts

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
DAY0 = int(datetime.datetime(2026, 10, 19, tzinfo=IST).timestamp() * 1000)      # IST midnight, epoch ms


def ms(hhmm, sec=0):
    h, m = map(int, hhmm.split(":"))
    return DAY0 + ((h * 60 + m) * 60 + sec) * 1000


def bar(t, h, l, c, vwap=100.0, sd=1.0, o=None):
    return {"t": t, "o": c if o is None else o, "h": h, "l": l, "c": c, "v": 1.0, "vwap": vwap,
            "u1": vwap + sd, "d1": vwap - sd, "u2": vwap + 2 * sd, "d2": vwap - 2 * sd,
            "u3": vwap + 3 * sd, "d3": vwap - 3 * sd}


def buy_series(arm_low=97.6, tail=(98.8, 98.7, 98.6)):
    """09:24 flat; 09:27 tags d2 (98) -- not beyond d3 (97) at 97.6; 09:30 closes above its high (98.8): the zone
    BUY entry. Then three bars still under d1 (99)."""
    bs = [bar("09:21", 100.4, 99.6, 100.0), bar("09:24", 100.3, 99.7, 100.0),
          bar("09:27", 98.8, arm_low, 98.0, o=98.6), bar("09:30", 98.95, 98.1, 98.9)]
    for k, c in enumerate(tail):
        bs.append(bar(f"09:{33 + 3 * k}", c + 0.05, c - 0.3, c))
    return bs


def test_pocket_and_exhaustion_split_on_d3_at_the_arm_bar():
    s = C.setups(buy_series())
    assert [(x["t"], x["side"], x["kind"]) for x in s] == [("09:30", "BUY", C.POCKET)]
    assert s[0]["extreme"] == 97.6 and s[0]["ref_t"] == "09:27" and s[0]["first_touch"] is True
    ex = C.setups(buy_series(arm_low=96.5))
    assert ex[0]["kind"] == C.EXHAUSTION and ex[0]["depth"] == 3.5


# ---- OI -----------------------------------------------------------------------------------------------------------

def grid(pe_path, ce_path, upto="10:30", spot=100.0):
    """A minute grid 09:15..upto: strike 100's CE / PE change since the open follows the two paths (f(n) of the
    minute's index)."""
    out, m, n = {}, 9 * 60 + 15, 0
    while m <= C.band_rotation._minute(upto):
        out[C.hm(m)] = {"spot": spot, "k": {100: (ce_path(n), pe_path(n))}}
        m, n = m + 1, n + 1
    return out


def test_oi_pocket_needs_the_defending_front_building():
    rising, flat = (lambda n: 1000.0 * n), (lambda n: 50000.0)
    ok = C.oi_read(C.POCKET, "BUY", grid(rising, flat), {}, "10:30")
    assert ok["ok"] is True and ok["front"]["side"] == "PE" and ok["front"]["state"] == fronts.BUILDING
    no = C.oi_read(C.POCKET, "BUY", grid(flat, rising), {}, "10:30")
    assert no["ok"] is False and no["front"]["state"] == fronts.STALLED
    sell = C.oi_read(C.POCKET, "SELL", grid(flat, rising), {}, "10:30")       # SELL's defender is the CE
    assert sell["ok"] is True and sell["front"]["side"] == "CE"


def test_oi_exhaustion_needs_the_attacking_front_stalled_or_unwinding():
    rising, flat = (lambda n: 1000.0 * n), (lambda n: 50000.0)
    unwind = lambda n: 1000.0 * n if n < 40 else 40000.0 - 2000.0 * (n - 40)       # noqa: E731
    assert C.oi_read(C.EXHAUSTION, "BUY", grid(rising, flat), {}, "10:30")["ok"] is True      # CE stalled
    assert C.oi_read(C.EXHAUSTION, "BUY", grid(rising, unwind), {}, "10:30")["ok"] is True    # CE unwinding
    assert C.oi_read(C.EXHAUSTION, "BUY", grid(flat, rising), {}, "10:30")["ok"] is False     # CE still adding
    assert C.oi_read(C.EXHAUSTION, "SELL", grid(flat, rising), {}, "10:30")["front"]["side"] == "PE"


def test_oi_on_a_stale_grid_is_could_not_check_never_a_verdict():
    out = C.oi_read(C.POCKET, "BUY", grid(lambda n: 1000.0 * n, lambda n: 0.0, upto="10:00"), {}, "10:30")
    assert out["ok"] is None and "stale" in out["why"]


def test_chain_grid_keeps_each_minutes_last_snapshot_and_its_peak_as_at_then():
    def snap(ts, oi):
        return {"ts": ts, "spot": 100.0, "strikes": [{"k": 100, "ce": {"oi": oi, "oi_chg": oi - 10, "ltp": 5.0},
                                                      "pe": {"oi": 1, "oi_chg": 0, "ltp": 4.0}}]}
    minutes, peaks = C.chain_grid([snap("09:20:05", 50), snap("09:20:50", 40), snap("09:21:10", 90),
                                   snap("15:31:00", 999)], {"09:19": {"spot": 99.0, "k": {100: (0, 0)}, "px": {}}})
    assert minutes["09:20"]["k"][100] == (30, 0) and peaks["09:20"][(100, "ce")] == 50
    assert peaks["09:21"][(100, "ce")] == 90 and "15:31" not in minutes
    assert minutes["09:19"]["src"] == "backfill"


# ---- FLOW ---------------------------------------------------------------------------------------------------------

def book(rates, holes=()):
    """(flow, seen, bad) with every minute 09:00-15:30 seen; `rates` {"HH:MM": (buy, sell)} else (10, 10)."""
    flow = {m: [10, 10] for m in range(540, 931)}
    for k, v in rates.items():
        flow[C.band_rotation._minute(k)] = list(v)
    return flow, set(range(540, 931)), {C.band_rotation._minute(h) for h in holes}


def turned(close, buy=True, fast=(30, 10), slow=(10, 30)):
    """The 5 min before `close` led by one side, the 15 before those by the other."""
    c = C.band_rotation._minute(close)
    r = {C.hm(m): (fast if buy else fast[::-1]) for m in range(c - 5, c)}
    r.update({C.hm(m): (slow if buy else slow[::-1]) for m in range(c - 20, c - 5)})
    return r


def test_flow_buy_is_the_5_over_15_flip_and_sell_is_its_mirror():
    c = C.band_rotation._minute("10:00")
    out = C.flow_read("BUY", book(turned("10:00")), c)
    assert out["ok"] is True and out["t5"] == 0.5 and out["t15"] == -0.5
    assert C.flow_read("SELL", book(turned("10:00", buy=False)), c)["ok"] is True
    # the push into the zone was ALREADY buyer-led: no flip
    assert C.flow_read("BUY", book(turned("10:00", slow=(30, 10))), c)["ok"] is False
    # +0.10 is the line: 11 vs 9 is +0.10 exactly, 10.9 vs 9.1 is under it
    assert C.flow_read("BUY", book(turned("10:00", fast=(11, 9), slow=(10, 10))), c)["ok"] is True
    assert C.flow_read("BUY", book(turned("10:00", fast=(10.9, 9.1), slow=(10, 10))), c)["ok"] is False


def test_flow_nifty_gocharting_disagreeing_vetoes_but_absent_does_not():
    c = C.band_rotation._minute("10:00")
    b = book(turned("10:00"))
    against = [{"t": ms("09:55"), "buy": 40, "sell": 60, "partial": False}]
    assert C.flow_read("BUY", b, c, gc=against) == {"ok": False, "t5": 0.5, "t15": -0.5, "gc": -0.2,
                                                    "why": "sources disagree"}
    assert C.flow_read("BUY", b, c, gc=[])["ok"] is True                    # NIFTY, no bar on those 5 minutes
    off_grid = [{"t": ms("09:54"), "buy": 0, "sell": 99, "partial": False}]
    assert C.flow_read("BUY", b, c, gc=off_grid)["ok"] is True              # not the same 5 minutes
    partial = [{"t": ms("09:55"), "buy": 0, "sell": 99, "partial": True}]
    assert C.flow_read("BUY", b, c, gc=partial)["ok"] is True


def test_flow_excludes_the_minute_after_a_book_hole():
    c = C.band_rotation._minute("10:00")
    out = C.flow_read("BUY", book(turned("10:00"), holes=("09:57",)), c)
    assert out["ok"] is None and "09:57" in out["why"]


def frame(t, vtt, ltp, q):
    return {"t": t, "ltt": t, "ltp": ltp, "ltq": q, "vtt": vtt, "b": [[99.9, 1000]], "a": [[100.0, 1000]]}


def frames(trades, start="09:17"):
    """One frame a minute from `start`, `trades` {"HH:MM": +q buy / -q sell} (else a quiet frame); a value of None
    is a minute with no frame at all."""
    out, vtt = [], 0
    for m in range(C.band_rotation._minute(start), C.band_rotation._minute("10:30")):
        q = trades.get(C.hm(m), 0)
        if q is None:
            continue
        out.append(frame(ms(C.hm(m), 5), vtt, 100.0, None))            # a depth change: frames every ~30 s
        vtt += abs(q)
        out.append(frame(ms(C.hm(m), 30), vtt, 100.0 if q > 0 else 99.9, abs(q) or None))
    return out


def test_book_flow_sides_by_the_ladder_rule_and_marks_holes():
    rows = frames({"09:20": 65, "09:21": -130, "09:30": None, "09:31": None, "09:32": 65})
    flow, seen, bad = C.book_flow(rows, tick=0.1)
    assert flow[C.band_rotation._minute("09:20")] == [65, 0]
    assert flow[C.band_rotation._minute("09:21")] == [0, 130]
    assert C.band_rotation._minute("09:30") not in seen                  # no frame: a hole, not a quiet minute
    assert C.band_rotation._minute("09:32") in bad                       # carries the hole's volume
    assert C.band_rotation._minute("09:17") in bad                       # the record's first frame


# ---- the entry -----------------------------------------------------------------------------------------------------

def test_entry_is_the_first_bar_of_the_window_with_zone_oi_and_flow():
    bs = buy_series()
    s = C.setups(bs)[0]
    chain = (grid(lambda n: 1000.0 * n, lambda n: 0.0), {})
    late_flow = book(turned("09:39"))                                     # FLOW turns only at the 09:36 bar's close
    ev = C.evaluate(s, bs, chain, late_flow)
    assert [b["t"] for b in ev["bars"]] == ["09:30", "09:33", "09:36", "09:39"]
    assert ev["entry"]["t"] == "09:36" and ev["entry"]["bar"] == 2
    # the 1-sigma ring: a close back above d1 is not an entry
    bs2 = buy_series(tail=(98.8, 99.2, 99.3))
    ev2 = C.evaluate(C.setups(bs2)[0], bs2, chain, late_flow)
    assert ev2["entry"] is None and ev2["bars"][2]["zone"]["ok"] is False
    # beyond 3 bars it is not this setup's any more
    assert C.evaluate(s, bs, chain, book(turned("09:45")))["entry"] is None


def test_no_entry_after_15_00():
    bs = [bar(f"14:{m:02d}", 100.2, 99.8, 100.0) for m in (45, 48)]
    bs += [bar("14:51", 98.8, 97.6, 98.0, o=98.6), bar("14:54", 98.95, 98.1, 98.9), bar("14:57", 98.85, 98.5, 98.8),
           bar("15:00", 98.85, 98.5, 98.8)]
    s = C.setups(bs)[0]
    chain = (grid(lambda n: 1000.0 * n * n, lambda n: 0.0, upto="15:10"), {})     # still building at 15:00
    ok = C.evaluate(s, bs, chain, book(turned("15:00")))                   # the 14:57 bar closes AT 15:00
    assert ok["entry"]["t"] == "14:57"
    late = C.evaluate(s, bs, chain, book(turned("15:03")))                 # the 15:00 bar closes at 15:03
    assert late["entry"] is None and late["bars"][-1]["late"] is True


# ---- the outcome --------------------------------------------------------------------------------------------------

def setup_of(kind, side="BUY", extreme=97.6):
    return {"kind": kind, "side": side, "extreme": extreme}


def test_stops_pocket_at_d3_exhaustion_beyond_the_extreme_and_the_half_sigma_floor():
    b = bar("09:30", 99, 98, 98.9)                                         # sigma 1, d3 97
    assert C.trade(setup_of(C.POCKET), b) == {"E": 98.9, "sigma": 1.0, "stop": 97.0}
    assert C.trade(setup_of(C.EXHAUSTION, extreme=96.5), b)["stop"] == 96.25
    assert C.trade(setup_of(C.EXHAUSTION, extreme=98.7), b)["stop"] == 98.4     # 98.45 floored to E - 0.5
    assert C.trade(setup_of(C.POCKET, "SELL"), bar("09:30", 102, 101, 101.1))["stop"] == 103.0


def one(t, h, l, c, vwap):
    return {"t": t, "h": h, "l": l, "c": c, "vwap": vwap}


def test_outcome_vwap_first_passage_stop_first_on_a_double_touch_and_the_15_20_mark():
    tr = {"E": 98.9, "stop": 97.0}
    start = C.band_rotation._minute("09:33")
    ones = [one("09:32", 120, 90, 99, 100), one("09:33", 99.2, 98.5, 99, 100), one("09:34", 100.1, 98.9, 100, 100)]
    assert C.outcome("BUY", tr, start, ones) == {"exit": 100, "how": "target", "exit_t": "09:34", "R": 0.5789}
    both = [one("09:33", 100.5, 96.9, 99, 100)]
    assert C.outcome("BUY", tr, start, both)["how"] == "stop" and C.outcome("BUY", tr, start, both)["R"] == -1.0
    drift = [one("15:18", 99.2, 98.5, 99.0, 100), one("15:19", 99.2, 98.5, 99.3, 100),
             one("15:20", 101, 98.5, 100.9, 100)]
    out = C.outcome("BUY", tr, start, drift)
    assert out["how"] == "mark" and out["exit_t"] == "15:19" and out["exit"] == 99.3
    sell = C.outcome("SELL", {"E": 101.1, "stop": 103.0}, start, [one("09:33", 101.5, 99.9, 100, 100)])
    assert sell["how"] == "target" and sell["R"] == 0.5789


def test_both_expressions_ride_every_entry_with_equal_weight():
    mins = {"09:32": {"spot": 100.4, "px": {100: (5.0, 4.0), 105: (2.0, 9.0)}},
            "09:50": {"spot": 102.0, "px": {100: (6.5, 2.5), 105: (3.0, 7.0)}}}
    x = C.expression("BUY", mins, "09:32", "09:50")
    assert (x["k"], x["buy"], x["sell"]) == (100, "CE", "PE")
    assert (x["buy_pts"], x["sell_pts"]) == (1.5, 1.5)
    y = C.expression("SELL", mins, "09:32", "09:50")
    assert (y["buy"], y["buy_pts"], y["sell"], y["sell_pts"]) == ("PE", -1.5, "CE", -1.5)
    mins["09:50"]["src"] = "backfill"                                     # premiums come from the recorded chain only
    assert C.expression("BUY", mins, "09:32", "09:50") is None


def test_verdict_pass_fail_inconclusive_and_no_rate():
    days = [f"2026-10-{d:02d}" for d in range(1, 21)]
    good = [{"day": d, "R": 0.5} for d in days]
    ctl = [{"day": d, "R": 0.1} for d in days]
    v = C.verdict(good, ctl)
    assert v["verdict"] == "PASS" and v["largest_day_share"] == 0.05
    assert C.verdict(good[:19], ctl)["verdict"] == "INCONCLUSIVE"                       # n < 20
    assert C.verdict(good, [{"day": "x", "R": 0.4}])["verdict"] == "INCONCLUSIVE"        # beats control by < 0.20
    assert C.verdict(good, [{"day": "x", "R": 0.6}])["verdict"] == "FAIL"                # worse than zone-alone
    one_day = [{"day": days[0], "R": 9.0}] + [{"day": d, "R": 0.01} for d in days[1:]]
    assert C.verdict(one_day, ctl)["verdict"] == "INCONCLUSIVE"                          # one session > 40%
    assert not any("rate" in k or "hit" in k or "win" in k for k in v)


def test_stamps_both_legs_and_reaction_points():
    mins = {"09:17": {"spot": 100.0, "px": {100: (5.0, 4.0)}}, "09:32": {"spot": 98.0, "px": {100: (5.5, 4.5)}}}
    assert C.both_legs(mins, "09:32") is True
    mins["09:32"]["px"][100] = (4.0, 6.0)
    assert C.both_legs(mins, "09:32") is False
    s = {"extreme": 100.2, "session_hl": (104.0, 97.9)}
    assert C.reaction(s, 1.0, {"h": 110.0, "l": 100.1}) == ["PDL", "round100"]


# ---- no look-ahead ------------------------------------------------------------------------------------------------

def test_a_bar_reads_the_same_whether_the_inputs_end_at_its_close_or_run_on():
    """Every input runs on past bar T and turns AGAINST the setup afterwards; the read at T must not move."""
    bs = buy_series()
    snaps, n = [], 0
    for m in range(C.band_rotation._minute("09:15"), C.band_rotation._minute("10:00")):
        pe = 1000.0 * n if m < C.band_rotation._minute("09:36") else 1000.0 * n - 30000.0 * (n - 21)
        big = 5e7 if m >= C.band_rotation._minute("09:36") else 5e5      # a later peak that would steal the front
        snaps.append({"ts": C.hm(m) + ":40", "spot": 98.5, "strikes": [
            {"k": 100, "ce": {"oi": 9e6, "oi_chg": 0.0, "ltp": 1.0}, "pe": {"oi": 1e6 + pe, "oi_chg": pe, "ltp": 2.0}},
            {"k": 105, "ce": {"oi": 1e5, "oi_chg": 0.0, "ltp": 0.5}, "pe": {"oi": big, "oi_chg": 0.0, "ltp": 7.0}}]})
        n += 1
    trades = {C.hm(m): (-65 if m < C.band_rotation._minute("09:32") else 130)
              for m in range(C.band_rotation._minute("09:17"), C.band_rotation._minute("09:36"))}
    trades.update({C.hm(m): -650 for m in range(C.band_rotation._minute("09:36"), C.band_rotation._minute("10:00"))})
    rows = frames(trades, start="09:05")
    gc = [{"t": ms(f"09:{m:02d}"), "buy": 10, "sell": 10, "partial": False} for m in range(15, 60, 5)]
    s = C.setups(bs)[0]
    T = 1                                                              # the 09:33 bar, closing 09:36
    assert C.setups(bs[:s["i"] + T + 1])[0] == s                       # the setup itself is causal
    close = C.close_of(bs[s["i"] + T]["t"])
    full = C.evaluate(s, bs, C.chain_grid(snaps), C.book_flow(rows, 0.1), gc)
    cut = C.evaluate(s, bs[:s["i"] + T + 1],
                     C.chain_grid([x for x in snaps if C.band_rotation._minute(x["ts"]) < close]),
                     C.book_flow([r for r in rows if C.mod(r["t"]) < close], 0.1),
                     [g for g in gc if C.mod(g["t"]) + 5 <= close])
    assert full["bars"][:T + 1] == cut["bars"] and cut["entry"] == full["entry"]
    assert full["entry"] is not None and full["entry"]["t"] == "09:33"   # the read the later data would have killed
    assert full["bars"][T + 1]["oi"]["ok"] is False or full["bars"][T + 1]["flow"]["ok"] is False


# ---- the firewall and the forward log -------------------------------------------------------------------------------

OUTCOME = ("mfe", "mae", "mfe_t", "mae_t", "stop_hit", "stop_t", "stop_px", "scored_at", "scored_from",
           "triggered", "f15", "f30", "bands", "anchor_px", "unscored")


def test_logged_rows_never_carry_an_outcome_field(tmp_path):
    p = tmp_path / "tl.jsonl"
    row = {"day": "2026-10-19", "index": "NIFTY", "t": "09:30", "side": "BUY", "band": "d2", "rule": "zone",
           "px": 98.9, "ctx": {"t_exp": 2.1}, "gate": {"legal": True}, **{k: 1 for k in OUTCOME}}
    p.write_text(json.dumps(row) + "\n" + json.dumps(dict(row, kind="arm")) + "\n\n{torn", encoding="utf-8")
    got = L.logged(str(p))
    assert list(got) == [("2026-10-19", "NIFTY", "09:30", "BUY")]
    assert not set(got[("2026-10-19", "NIFTY", "09:30", "BUY")]) & set(OUTCOME)


def test_forward_log_writes_one_row_per_zone_entry_once_its_window_has_closed(tmp_path, monkeypatch):
    import squeeze_score
    import trigger_log
    monkeypatch.setattr(L, "READ_DIR", str(tmp_path / "read"))
    monkeypatch.setattr(squeeze_score, "BT", str(tmp_path / "backtest"))      # yesterday's bars: none here
    path = str(tmp_path / "confluence_log.jsonl")
    monkeypatch.setattr(L, "_seen", None)
    bs = buy_series() + [bar("09:42", 99, 98.4, 98.6)]                     # 09:42 is the forming bar
    payload = {"interval": 3, "days": [{"day": time.strftime("%b %d") + " LIVE", "bars": bs}]}
    assert L.log_new("NIFTY", payload, path=path, now="09:42") == 0      # 09:39 closed at 09:42: grace minute
    assert L.log_new("NIFTY", payload, path=path, now="09:43") == 1
    assert L.log_new("NIFTY", json.dumps(payload), path=path, now="09:50") == 0     # write-once
    monkeypatch.setattr(L, "_seen", None)                                # a restart re-reads the file
    assert L.log_new("NIFTY", payload, path=path, now="09:50") == 0
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert len(rows) == 1 and rows[0]["t"] == "09:30" and rows[0]["kind"] == C.POCKET
    assert [b["t"] for b in rows[0]["bars"]] == ["09:30", "09:33", "09:36", "09:39"]
    assert rows[0]["entry"] is None and rows[0]["bars"][0]["flow"]["ok"] is None     # no book recorded here
    assert not any(k in rows[0] for k in ("R", "exit", "outcome"))
    assert rows[0]["setup"] == "FADE"                                    # §1j: the two setups share the file
    assert not os.path.exists(trigger_log.PATH)                          # it writes nothing anywhere else


# ---- §1j RIDE: the same file, its own rows ----------------------------------------------------------------------------

def test_log_ride_is_fail_soft_and_write_once(tmp_path, monkeypatch):
    import confluence_log, ride
    p = tmp_path / "c.jsonl"
    monkeypatch.setattr(confluence_log, "_seen", None)
    monkeypatch.setattr(confluence_log, "_ride_slot", {})
    monkeypatch.setattr(confluence_log, "ride_inputs",
                        lambda idx, day, now=None, light=False: (_ for _ in ()).throw(OSError("x")))
    assert confluence_log.log_ride("NIFTY", now="11:00", path=str(p)) == 0        # an error never escapes
    inp = {"b3": [{"s": 35820, "e": 36000}], "ones": [], "rows": [], "basis": None, "chain": ({}, {}),
           "book": ({}, set(), set()), "gc": None, "dte": 3, "peers_rows": {}}
    monkeypatch.setattr(confluence_log, "ride_inputs", lambda idx, day, now=None, light=False: inp)
    monkeypatch.setattr(ride, "entries", lambda b3, rows, basis: [{"i": 0, "t": "10:00", "d": -1, "word": "TREND", "px": 1}])
    monkeypatch.setattr(confluence_log, "build_ride", lambda idx, day, ent, inp: {"setup": "RIDE", "day": day, "index": idx,
                                                                               "t": ent["t"], "d": ent["d"]})
    monkeypatch.setattr(confluence_log, "_ride_due", lambda ent, b3, nowm: True)
    assert confluence_log.log_ride("NIFTY", now="11:00", path=str(p)) == 0        # the failed bar is used: no retry loop
    assert confluence_log.log_ride("NIFTY", now="11:03", path=str(p)) == 1        # the next bar retries
    assert confluence_log.log_ride("NIFTY", now="11:06", path=str(p)) == 0        # write-once
    monkeypatch.setattr(confluence_log, "_seen", None)                            # a restart re-reads the RIDE keys
    assert confluence_log.log_ride("NIFTY", now="11:09", path=str(p)) == 0
    assert '"setup": "RIDE"' in p.read_text()
    assert len(p.read_text().splitlines()) == 1


def test_log_ride_checks_once_per_bar_and_skips_a_row_whose_bar_moved(tmp_path, monkeypatch):
    import confluence_log, ride
    p = tmp_path / "c.jsonl"
    monkeypatch.setattr(confluence_log, "_seen", None)
    monkeypatch.setattr(confluence_log, "_ride_slot", {})
    calls = []
    lite = {"b3": [{"s": 35820, "e": 36000}], "rows": [], "basis": None}
    heavy = dict(lite, b3=[{"s": 35640, "e": 35820}])                  # the heavy load's bar 0 is not the 10:00 bar
    monkeypatch.setattr(confluence_log, "ride_inputs",
                        lambda idx, day, now=None, light=False: (calls.append(light), lite if light else heavy)[1])
    monkeypatch.setattr(ride, "entries", lambda b3, rows, basis: [{"i": 0, "t": "10:00", "d": -1}])
    monkeypatch.setattr(confluence_log, "_ride_due", lambda ent, b3, nowm: True)
    monkeypatch.setattr(confluence_log, "build_ride", lambda idx, day, ent, inp: {"setup": "RIDE", "t": ent["t"]})
    assert confluence_log.log_ride("NIFTY", now="10:13", path=str(p)) == 0        # the index guard: no row
    assert confluence_log.log_ride("NIFTY", now="10:15", path=str(p)) == 0        # same slot (10:13..10:15): skipped
    assert calls == [True, False] and not p.exists()


def test_ride_due_waits_for_the_window_and_the_grace_minute():
    b3 = [{"s": 36000 + 180 * j, "e": 36180 + 180 * j} for j in range(5)]           # closes 10:03 .. 10:15
    ent = {"i": 1}                                                                  # window 10:06 .. 10:15
    assert L._ride_due(ent, b3[:4], 10 * 60 + 13) is False                          # 10:13: bar i+3 not closed
    assert L._ride_due(ent, b3, 10 * 60 + 15) is False                              # 10:15: the grace minute
    assert L._ride_due(ent, b3, 10 * 60 + 16) is True
    assert L._ride_due(ent, b3[:4], L.CLOSE) is True                                # after 15:30 every window is closed


def test_build_ride_stamps_the_peers_sync_and_which_pullback_this_is():
    def b(j):
        return {"s": 36000 + 180 * j, "e": 36180 + 180 * j, "o": 22500, "h": 22510, "l": 22470, "c": 22480,
                "vwap": 22500, "sig": 20, "delta": -5}
    rows = [{"t": "10:00", "word": "TREND", "dir": -1, "since": "10:00", "flip": 22550, "basis": 40}]
    peer = [{"t": "10:00", "word": "TREND", "dir": -1}, {"t": "10:20", "word": "TREND", "dir": 1}]
    ents = [{"i": 1, "t": "10:06", "d": -1, "word": "TREND", "px": 22480},
            {"i": 4, "t": "10:15", "d": -1, "word": "TREND", "px": 22480}]
    inp = {"b3": [b(j) for j in range(8)], "rows": rows, "basis": None, "chain": ({}, {}), "book": ({}, set(), set()),
           "gc": None, "dte": 3, "peers_rows": {"SENSEX": peer, "BANKNIFTY": []}, "entries": ents}
    r = L.build_ride("NIFTY", "2026-10-19", ents[1], inp)
    assert (r["day"], r["index"], r["setup"], r["t"]) == ("2026-10-19", "NIFTY", "RIDE", "10:15")
    assert r["stamps"]["pullback_no"] == 2 and r["stamps"]["dte"] == 3
    assert r["stamps"]["peers"] == {"words": {"SENSEX": "TREND ▼", "BANKNIFTY": None}, "sync": 1}
    assert r["entry"] is None and r["bars"][0]["oi"]["ok"] is None                  # nothing recorded: could not check
    assert not any(k in r for k in ("R", "exit", "outcome", "expressions"))


def test_fade_look_amendment_2_scores_once_marks_1k_and_refuses_a_second_time(tmp_path, monkeypatch):
    import sys
    monkeypatch.chdir(os.getcwd())                                       # main() chdirs; give the cwd back after
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    import confluence_score as cs
    out, md = tmp_path / "first_look.json", tmp_path / "FIRST-LOOK.md"
    monkeypatch.setattr(cs, "OUT_JSON", str(out))
    monkeypatch.setattr(cs, "OUT_MD", str(md))
    runs = []
    monkeypatch.setattr(cs, "days", lambda lg: [])
    monkeypatch.setattr(cs, "collect", lambda recs, run=False, lg=None: (runs.append(run), ([], []))[1])
    assert cs.main(["--look-amendment-2"]) == 0 and runs == [True]
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["amendment"].startswith("§1k") and res["readings"] == cs.READINGS
    assert not md.exists()                                               # the look's document is LOOK-2026-10-21.md
    assert cs.main(["--look-amendment-2"]) == 2 and cs.main(["--run"]) == 2 and runs == [True]   # once


def _row(hhmm, o, h, l, c, delta, vol=1000):
    s = int(hhmm[:2]) * 3600 + int(hhmm[3:]) * 60
    return {"t": (s - 19800) * 1000, "o": o, "h": h, "l": l, "c": c, "vol": vol, "delta": delta}


def _ones(hhmm, rows):
    m0 = int(hhmm[:2]) * 60 + int(hhmm[3:])
    return [{"t": f"{(m0 + k) // 60:02d}:{(m0 + k) % 60:02d}", "o": o, "h": h, "l": l, "c": c}
            for k, (o, h, l, c) in enumerate(rows)]


# 26 Oct 09:15, as recorded: GoCharting's history bar (no open / close) and the exchange's five 1-min candles
GC_0915 = _row("09:15", None, 22579.3, 22500.0, None, -1007, vol=2233)
ONES_0915 = _ones("09:15", [(22560.0, 22570.0, 22530.0, 22535.0), (22531.0, 22575.0, 22525.6, 22575.0),
                            (22575.0, 22579.3, 22540.0, 22545.0), (22545.0, 22550.0, 22505.0, 22510.0),
                            (22510.0, 22520.0, 22500.0, 22500.0)])


def test_a_late_start_completes_gochartings_history_bar_from_the_exchanges_1min_candles():
    """A106, 26 Oct 09:32 start: the extension's history bars 09:15-09:25 came with h, l, vol and delta but no open /
    close (its candle join has failed since 3 Oct) and Upstox's flow bars began at the start, so NIFTY's 5-min bars
    began 09:30 and DECODE read nothing all day. Where no Upstox bar holds the slot, the open / close are the exchange's
    1-min candles' (first open, last close), tagged; GoCharting's own h / l / vol / delta are untouched."""
    ux = [_row("09:30", 22506.0, 22529.9, 22499.5, 22503.5, 12)]
    got = L.push_bars("NIFTY", "2026-10-26", gc_rows=[GC_0915], ux_rows=ux, ones=ONES_0915)
    b = got[0]
    assert [(x["s"] // 60, x["src"]) for x in got] == [(555, "gc"), (570, "ux")]
    assert (b["o"], b["h"], b["l"], b["c"], b["vol"], b["delta"], b["oc"]) == (22560.0, 22579.3, 22500.0, 22500.0,
                                                                                2233, -1007, "ux1m")


def test_price_bars_are_the_exchanges_5min_candles_on_the_0915_grid():
    """A107: DECODE's leg on a late start -- the 1-min candles folded to 5-min bars shaped as the flow bars (s, o, h, l,
    c, vol), tagged ux1m, with no delta: price and volume only."""
    ones = [dict(o, v=100 * (k + 1)) for k, o in enumerate(ONES_0915)] + _ones("09:20", [(22500.0, 22501.8, 22454.0, 22470.0)])
    got = L.price_bars("BANKNIFTY", "2026-10-26", ones=ones)
    assert got == [{"s": 555 * 60, "o": 22560.0, "h": 22579.3, "l": 22500.0, "c": 22500.0, "vol": 1500, "src": "ux1m"},
                   {"s": 560 * 60, "o": 22500.0, "h": 22501.8, "l": 22454.0, "c": 22470.0, "vol": 0, "src": "ux1m"}]


def test_the_candle_fill_never_touches_a_slot_upstox_holds_or_a_candle_it_cannot_trust():
    ux = [_row("09:15", 22561.0, 22579.0, 22501.0, 22502.0, -900)]
    held = L.push_bars("NIFTY", "2026-10-26", gc_rows=[GC_0915], ux_rows=ux, ones=ONES_0915)
    assert [(b["src"], b["delta"], "oc" in b) for b in held] == [("ux", -900, False)]      # an observed bar wins: untouched
    for ones in (ONES_0915[:4],                                                             # a minute short
                 [dict(o, h=o["h"] + 120, l=o["l"] + 120) for o in ONES_0915]):              # another contract's range
        assert L.push_bars("NIFTY", "2026-10-26", gc_rows=[GC_0915], ux_rows=[], ones=ones) == []
