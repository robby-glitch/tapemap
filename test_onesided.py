"""THE ONE-SIDED METER (onesided.py, §1o): the seven votes, a bar's state (? never ·), the day type at each boundary,
the fixed-strike lead (A24), the idempotent daily row, and the in-sample replay of 21 / 22 Oct (sanity, never
evidence). Synthetic except the replay, which skips when the day's files are absent."""
import json
import os

import pytest

import onesided
import tape_log

M = lambda hhmm: int(hhmm[:2]) * 60 + int(hhmm[3:])        # noqa: E731


def bar(hhmm, c, delta, vol=1000, oi=None, o=None, h=None, l=None):
    o = c if o is None else o
    return {"s": M(hhmm) * 60, "o": o, "h": max(o, c) + 5 if h is None else h, "l": min(o, c) - 5 if l is None else l,
            "c": c, "vol": vol, "delta": delta, "oi": oi, "src": "gc"}


def up4():
    return [bar("09:15", 22700, 0, oi=1_000_000, o=22700, h=22705, l=22695), bar("09:20", 22720, 100, o=22700),
            bar("09:25", 22740, 100, o=22720), bar("09:30", 22760, 100, oi=1_002_000, o=22740)]


# ---- the votes ----------------------------------------------------------------------------------------------------------

def test_all_seven_votes_up_make_a_one_sided_bar():
    bs = up4()
    s = bs[3]["s"]
    v = onesided.votes(bs, {M("09:35"): {"pe": 20.0}}, {M("09:35"): {"chg": 12.0, "shifted": False}},
                       [{s: 1}, {s: 1}])[3]
    assert v == {k: 1 for k in onesided.KEYS}                          # Δ/vol .10, CVD .10, VWAP, 20, +12, OI +.2% up, peers
    assert onesided.state(v) == 1


def test_each_vote_reads_its_own_threshold_and_missing_is_none():
    bs = up4()
    bs[3]["delta"] = 49                                                # 0.049 < 0.05
    s = bs[3]["s"]
    v = onesided.votes(bs, {M("09:35"): {"pe": -15.0}}, {M("09:35"): {"chg": -9.9, "shifted": True}},
                       [{s: 1}, {s: 0}])[3]
    assert (v["delta"], v["writers"], v["writers15"], v["peers"]) == (0, -1, 0, 0)
    first = onesided.votes(bs, {}, {}, [{}, {}])[0]
    assert first["cvd"] is None and first["fut_oi"] is None and first["writers"] is None and first["peers"] is None
    assert onesided.state(first) is None                              # 5 unread votes could still agree: "?"
    bs[3]["oi"] = 1_000_900                                            # +0.09% in 15 min: OI flat
    assert onesided.votes(bs, {}, {}, [{}, {}])[3]["fut_oi"] == 0
    assert onesided.votes(bs, {}, {}, [{s: 1}])[3]["peers"] is None   # one peer only: "both others" unread
    assert onesided.votes(bs, {}, {}, [{s: 1}, {}])[3]["peers"] is None
    assert onesided.votes(bs, {}, {}, [{s: 1}, {s: -1}])[3]["peers"] == 0


def test_a_short_falling_oi_with_price_down_votes_down():
    bs = up4()
    for b in bs[1:]:
        b["c"], b["delta"] = 22700 - 20 * (bs.index(b)), -100
    bs[3]["oi"] = 998_000                                              # long liquidation
    assert onesided.votes(bs, {}, {}, [{}, {}])[3]["fut_oi"] == -1


@pytest.mark.parametrize("v,want", [
    ([1, 1, 1, 1, 1, 0, -1], 1), ([-1] * 5 + [0, 0], -1), ([1, 1, 1, 1, 0, 0, 0], 0),
    ([1, 1, 1, 1, None, 0, 0], None), ([1, 1, 1, None, None, -1, -1], None), ([1, 1, 0, 0, None, -1, -1], 0)])
def test_a_bar_is_one_sided_at_five_and_question_only_when_the_missing_could_tip_it(v, want):
    assert onesided.state(dict(zip(onesided.KEYS, v))) == want


# ---- the day type, each boundary -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("up,down,flips,crosses,rng,want", [
    (0, 10, 1, 2, 1.0, "TREND ▼"), (10, 0, 0, 0, 1.0, "TREND ▲"),
    (0, 9, 0, 0, 1.0, "MIXED"),                    # 9 one-sided bars: not yet
    (2, 8, 1, 2, 1.0, "TREND ▼"), (21, 79, 1, 2, 1.0, "MIXED"),          # 80% vs 79%
    (0, 10, 2, 2, 1.0, "MIXED"), (0, 10, 1, 3, 1.0, "MIXED"),            # flips 2 / crosses 3
    (3, 3, 0, 4, 0.49, "PIN"), (3, 3, 0, 4, 0.5, "CHOP"), (3, 3, 0, 3, 0.3, "MIXED"),
    (3, 3, 0, 4, 1.0, "CHOP"), (3, 3, 3, 0, 1.0, "CHOP"), (3, 3, 2, 3, 1.0, "MIXED"),
    (0, 12, 1, 4, 0.4, "PIN")])                    # crosses >= 4 cannot be a TREND
def test_the_day_type_boundaries(up, down, flips, crosses, rng, want):
    assert onesided.kind(up, down, flips, crosses, rng) == want


def test_a_cross_through_a_flat_bar_counts_once():
    assert onesided._crosses([1, 0, -1, 0, -1, None, 1]) == 2 and onesided._crosses([0, 1, 1, 0, 1]) == 0


def test_the_meter_says_why_when_it_cannot_read_and_counts_when_it_can():
    late = onesided.meter(up4()[1:], {}, {})
    assert late["type"] is None and "09:20" in late["why"] and late["strip"] is None
    m = onesided.meter(up4(), {}, {}, upto=M("09:35") * 60)
    assert m["why"] is None and m["last"] == "09:35" and len(m["strip"]) == 4
    assert m["up"] + m["down"] + m["mix"] + m["unk"] == 4 and m["type"] == "MIXED"
    assert onesided.meter(up4(), {}, {}, upto=M("09:30") * 60)["last"] == "09:30"     # the 09:30 bar is not closed
    assert (m["thin"], m["lots_med"]) == (0, 1000)


def test_thin_bars_are_flagged_and_change_no_vote():
    thin = up4()
    for b in thin:
        b["vol"], b["delta"] = b["vol"] / 100, b["delta"] / 100           # 10 lots a bar: SENSEX-thin, same shares
    m, fat = onesided.meter(thin, {}, {}), onesided.meter(up4(), {}, {})
    assert (m["thin"], m["lots_med"]) == (4, 10) and m["strip"] == fat["strip"] and m["type"] == fat["type"]


# ---- A24: one strike set -------------------------------------------------------------------------------------------

KS = [22300.0 + 50 * j for j in range(13)]


def X_shift():
    """Two rows: 09:44:50 at spot 22,500 (the nine = 22,300..22,700), 09:59:50 at 22,550 (22,350..22,750). Every strike
    writes CE 10, PE 20, except a fresh CE 100 at 22,750 -- inside the new nine only."""
    ce1 = [1010] * 13
    ce1[9] = 1100
    return {"step": 50, "ks": KS, "t": [M("09:45") * 60 - 10, M("10:00") * 60 - 10], "spot": [22500.0, 22550.0],
            "ce_oi": [[1010] * 13, ce1], "pe_oi": [[1020] * 13, [1020] * 13], "base_ce": {k: 1000 for k in KS},
            "base_pe": {k: 1000 for k in KS}, "bars": [], "lot": 1}


def test_the_lead_change_is_read_on_the_strikes_it_started_with():
    f = onesided.lead15(X_shift(), M("10:00"))
    assert f["shifted"] is True and round(f["a15"], 1) == 33.3
    assert round(f["chg"], 1) == 0.0                 # the old nine wrote nothing new; re-centred it would read -33.3
    assert onesided.lead15(X_shift(), M("10:30")) is None                  # the last row is stale: never a number
    assert onesided.lead15(None, M("10:00")) is None


# ---- the daily row: once per day + index, fail-soft -------------------------------------------------------------------

def test_the_daily_log_writes_each_day_and_index_once(tmp_path):
    p = str(tmp_path / "os" / "log.jsonl")
    rows = [onesided.row("2026-10-23", i, up4(), {}, {}) for i in ("NIFTY", "BANKNIFTY")]
    assert onesided.log(rows, p) == 2 and onesided.log(rows, p) == 0
    onesided._seen.clear()                                             # a restart re-reads the keys
    assert onesided.log(rows, p) == 0
    got = [json.loads(x) for x in open(p, encoding="utf-8")]
    assert [r["index"] for r in got] == ["NIFTY", "BANKNIFTY"]
    r = got[0]
    assert {"type", "up", "down", "mix", "dom", "flips", "crosses", "strip", "at_1130", "shape", "rev"} <= set(r)
    assert set(r["shape"]) >= {"range_sd", "crosses", "near_vwap", "sigma"}
    assert onesided.log([{"no": "day"}], p) == 0                       # fail-soft: an error is 0, never a raise


def test_the_server_writes_the_row_at_the_1530_close_only(monkeypatch):
    import read
    import server
    g = {"bars5": up4(), "l5": {}, "l15": {}}

    def all_(day, T, live, keep=False):
        return dict({"NIFTY": {"t": "15:30"}}, **({"_facts": {"NIFTY": g, "SENSEX": OSError("x")}} if keep else {}))
    monkeypatch.setattr(server, "_decode_all", all_)
    monkeypatch.setattr(server, "_DECODE", {"out": {}, "last": {}, "busy": set(), "replay": {}})
    server._decode_run("2026-10-23", read.CLOSE_S - 300, ("2026-10-23", read.CLOSE_S - 300))
    assert not os.path.exists(onesided.PATH)
    server._decode_run("2026-10-23", read.CLOSE_S, ("2026-10-23", read.CLOSE_S))
    got = [json.loads(x) for x in open(onesided.PATH, encoding="utf-8")]
    assert [(r["day"], r["index"]) for r in got] == [("2026-10-23", "NIFTY")]       # a failed index writes nothing
    assert "_facts" not in server._DECODE["out"][("2026-10-23", read.CLOSE_S)]


# ---- in-sample replay (21 and 22 Oct chose the rule: sanity, never evidence) ------------------------------------------

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


@pytest.mark.parametrize("day,want", [("2026-10-21", "TREND ▼"), ("2026-10-22", "CHOP")])
def test_in_sample_nifty_matches_the_mockup(day, want, monkeypatch):
    import confluence_log
    import faded
    import read
    import v2feed
    if not all(os.path.exists(os.path.join(DATA, sub, f"{pre}_{day}.jsonl")) for sub, pre in
               (("tape", "tape_NIFTY"), ("tape", "ux_BANKNIFTY"), ("tape", "ux_SENSEX"), ("chain", "chain_NIFTY"))):
        pytest.skip(f"{day}'s recorded files are not here")
    monkeypatch.setattr(tape_log, "DIR", os.path.join(DATA, "tape"))   # read-only: the real record
    bars = {i: confluence_log.push_bars(i, day) for i in ("NIFTY", "BANKNIFTY", "SENSEX")}
    closes = list(range(M("09:20"), M("15:30") + 1, 5))

    def go(D):
        X = read.from_v2(D.idx["NIFTY"], v2feed.LOTS["NIFTY"])
        return faded.leads(X, closes), {c: onesided.lead15(X, c) for c in closes}
    l5, l15 = v2feed.with_day(day, go)
    assert onesided.meter(bars["NIFTY"], l5, l15, [bars["BANKNIFTY"], bars["SENSEX"]])["type"] == want
