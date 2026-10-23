"""THE DECODE block (decode.py): each sign, the call rule, live == replay (no look-ahead), the registered setups reused
(guard), fail-soft. Synthetic only: nothing here reads data/. Prices are futures; a 5-min bar is named by its opening
minute, a reading by its close."""
import ast
import os

import pytest

import confluence
import decode
import faded
import frame_v2
import ride

M = lambda hhmm: int(hhmm[:2]) * 60 + int(hhmm[3:])        # noqa: E731
KS = [22300.0 + 50 * j for j in range(9)]


def b5(hhmm, h, l, c, delta, vol=1000, o=None):
    return {"s": M(hhmm) * 60, "o": c if o is None else o, "h": h, "l": l, "c": c, "vol": vol, "delta": delta, "src": "gc"}


def top():
    """▲ leg 99 -> 115: 09:15 the biggest buying bar, new highs at 09:20 (50%) and 09:25 (20%: effort fading), then sells
    back under VWAP. Two later bars (09:45, 09:50) exist only for the no-look-ahead test."""
    return [b5("09:15", 110, 99, 108, 400, vol=5000), b5("09:20", 112, 105, 111, 200), b5("09:25", 115, 109, 114, 80),
            b5("09:30", 114, 108, 110, -50), b5("09:35", 111, 106, 109, -60), b5("09:40", 110, 104, 105, -90),
            b5("09:45", 106, 100, 101, -120), b5("09:50", 103, 98, 99, -40)]


def climb():
    """▲ leg 99 -> 116 on effort: every new high at >= 67% of the leg's biggest, the close far above VWAP."""
    return [b5("09:15", 105, 99, 104, 300), b5("09:20", 108, 103, 107, 200), b5("09:25", 112, 106, 111, 250),
            b5("09:30", 116, 110, 115, 350)]


def X_for(leads):
    """THE READ's chain arrays whose nine-strike PE lead at each 5-min close is `leads[close minute]` (one row 10 s
    before the close; CE writes 10 a strike, PE what the lead asks)."""
    t, spot, ce, pe = [], [], [], []
    for c in sorted(leads):
        L = leads[c]
        p = 10 * (100 + L) / (100 - L)
        t.append(c * 60 - 10)
        spot.append(22500.0)
        ce.append([1000 + 10] * 9)
        pe.append([1000 + p] * 9)
    return {"step": 50, "ks": KS, "t": t, "spot": spot, "ce_oi": ce, "pe_oi": pe, "ce_ltp": [[1] * 9 for _ in t],
            "pe_ltp": [[1] * 9 for _ in t], "base_ce": {k: 1000 for k in KS}, "base_pe": {k: 1000 for k in KS},
            "bars": [], "lot": 1}


TOP_LEAD = {M("09:20"): 20.0, M("09:25"): 30.0, M("09:30"): 35.0, M("09:35"): 33.0, M("09:40"): 22.0,
            M("09:45"): 18.0, M("09:50"): 15.0, M("09:55"): 12.0}
RISING = {M("09:20"): 10.0, M("09:25"): 20.0, M("09:30"): 28.0, M("09:35"): 40.0}


def g_top(T=M("09:45") * 60, **kw):
    return decode.facts("NIFTY", T, top(), X_for(TOP_LEAD), **kw)


def g_climb(**kw):
    return decode.facts("NIFTY", M("09:35") * 60, climb(), X_for(RISING), **kw)


@pytest.fixture(autouse=True)
def _session_leg(monkeypatch):
    """These fixtures are priced near 100, where A1's 50-pts-at-22,700 floor is 0.2 pts and every wiggle would be a
    swing: they test the signs on the session-extreme leg (the DECODE leg before the zigzag's first reversal). The
    swing leg has its own tests below, at NIFTY prices."""
    monkeypatch.setattr(decode, "ZZ_PCT", 1.0)


def peer(idx, d):
    return {"idx": idx, "leg": {"d": d}, "dleg": {"d": d}, "bars5": [b5("09:15", 1, 1, 1, 0)], "vwap": 2.0}


def keys(xs):
    return [k for k, _ in xs]


# ---- each sign --------------------------------------------------------------------------------------------------------

def test_a_top_shows_every_decel_sign_with_its_number():
    g = g_top()
    assert g["leg"]["d"] == 1 and (g["leg"]["from"], g["leg"]["to"]) == (99, 115)
    dec, con = decode.signs(g, [peer("SENSEX", -1)])
    assert keys(dec) == ["effort", "delta", "cvd", "lead", "vwap", "peers"] and con == []
    chip = dict(dec)
    assert chip["effort"] == "nayi high 09:25 · 20% effort"            # 80 / 400: FADE-D 2a's reading
    assert chip["delta"] == "Δ −90 leg ke khilaf"
    assert chip["cvd"] == "CVD peak se −200"                            # 680 after the 09:25 bar -> 480
    assert chip["lead"] == "PE lead peak se −17"                        # 35 @09:30 -> 18 @09:45
    assert chip["vwap"].startswith("VWAP ke neeche −")
    assert chip["peers"] == "SNX ▼ ulta leg"


def test_a_climb_shows_every_continuation_mirror():
    g = g_climb(pushes=[{"s": M("09:25") * 60, "t": "09:25", "close": M("09:30"), "d": 1, "origin": 106}])
    dec, con = decode.signs(g, [peer("BANKNIFTY", 1)])
    assert dec == [] and keys(con) == ["effort", "delta", "cvd", "lead", "vwap", "push", "peers"]
    chip = dict(con)
    assert chip["effort"] == "nayi high 09:30 · 100% effort" and chip["delta"] == "Δ +350 leg ke saath"
    assert chip["cvd"] == "CVD leg peak pe" and chip["lead"] == "PE lead peak pe +40"
    assert chip["push"] == "▲ push 09:25 tika" and chip["peers"] == "BNF ▲ saath"


def test_the_lead_counts_only_at_10_off_its_peak_and_reads_faded_lead_pts(monkeypatch):
    g = decode.facts("NIFTY", M("09:40") * 60, top(), X_for({**TOP_LEAD, M("09:40"): 27.0}))   # 8 under 35
    assert "lead" not in keys(decode.signs(g, [])[0]) + keys(decode.signs(g, [])[1])
    monkeypatch.setattr(faded, "LEAD_PTS", 5.0)                          # the registered constant, not a copy
    assert "lead" in keys(decode.signs(g, [])[0])


def test_a_push_in_the_leg_fails_when_a_later_close_goes_back_through_its_origin():
    P = [{"s": M("09:20") * 60, "t": "09:20", "close": M("09:25"), "d": 1, "origin": 106}]
    dec, _ = decode.signs(g_top(pushes=P), [])
    assert dict(dec)["push"] == "▲ push 09:20 fail"                     # 09:40 closed 105 < 106
    held = [dict(P[0], origin=104)]
    assert dict(decode.signs(g_top(pushes=held), [])[1])["push"] == "▲ push 09:20 tika"
    against = [dict(P[0], d=-1)]
    assert "push" not in keys(sum(decode.signs(g_top(pushes=against), []), []))


def test_the_extensions_own_push_wins_when_it_sent_one_inside_the_leg():
    t_ms = ((M("09:30") * 60 - 19800) % 86400) * 1000                   # 09:30 IST as epoch ms (a day-0 epoch)
    ext = {"up": {"t": t_ms, "px": 113.0, "rank": 95, "failed": True}, "down": None}
    held = [{"s": M("09:20") * 60, "t": "09:20", "close": M("09:25"), "d": 1, "origin": 104}]
    dec, con = decode.signs(g_top(pushes=held, push=ext), [])
    assert dict(dec)["push"] == "▲ push 09:30 fail" and "push" not in keys(con)


def test_no_leg_no_signs_and_the_call_says_saaf_nahi():
    flat = [b5("09:15", 110, 100, 105, 10), b5("09:20", 109, 101, 104, -5)]       # no new extreme yet
    g = decode.facts("NIFTY", M("09:25") * 60, flat, X_for(TOP_LEAD))
    assert g["leg"] is None and decode.signs(g, []) == ([], [])
    out = decode.decode(g, [])
    assert out["call"] == {"text": "saaf nahi", "kind": "SAAF_NAHI", "d": 0, "c": 0, "of": 7, "signs": []}
    assert out["leg"] is None


# ---- the call rule ----------------------------------------------------------------------------------------------------

LEG = {"d": 1}


@pytest.mark.parametrize("d,c,kind,text", [
    (5, 1, "THAK", "▲ leg thak raha · 5/7"), (4, 3, "THAK", "▲ leg thak raha · 4/7"),
    (1, 4, "JAARI", "▲ leg jaari · 4/7"), (0, 7, "JAARI", "▲ leg jaari · 7/7"),
    (4, 4, "MILA", "▲ mila-jula · 4/4"), (3, 0, "MILA", "▲ mila-jula · 3/0"), (5, 5, "MILA", "▲ mila-jula · 5/5"),
])
def test_the_call_is_a_count_never_a_percent(d, c, kind, text):
    dec = [("k%d" % i, f"dec {i}") for i in range(d)]
    con = [("k%d" % i, f"con {i}") for i in range(c)]
    out = decode.call(LEG, dec, con)
    assert (out["kind"], out["text"], out["d"], out["c"], out["of"]) == (kind, text, d, c, 7)
    assert "%" not in out["text"]
    own = {"THAK": [x for _, x in dec], "JAARI": [x for _, x in con]}.get(kind)
    if own is not None:                                   # its own chips first, the other side's prefixed after them
        assert out["signs"][:len(own)] == own and all(s.startswith(("jaari · ", "thak · ")) for s in out["signs"][len(own):])
    else:
        assert out["signs"] == [f"thak · {x}" for _, x in dec] + [f"jaari · {x}" for _, x in con]


def test_a_down_leg_carries_its_arrow():
    assert decode.call({"d": -1}, [("a", "x")] * 4, [])["text"] == "▼ leg thak raha · 4/7"


def test_the_block_keeps_the_shared_contract():
    out = decode.decode(g_top(basis=12.0), [peer("SENSEX", -1)])
    assert set(out) == {"call", "lines", "setups", "leg", "t", "tag", "onesided", "effort"} and out["tag"] == "I" and out["t"] == "09:45"
    assert set(out["onesided"]) == set(decode.onesided.blank("x"))
    assert set(out["call"]) == {"text", "kind", "d", "c", "of", "signs"} and out["call"]["kind"] in decode.KINDS
    assert out["call"]["text"] == "▲ leg thak raha · 6/7"
    assert len(out["lines"]) <= 6 and all(isinstance(x, str) for x in out["lines"])
    assert out["lines"][5] == "EFFORT ? — not read" and out["effort"]["x"] is None and out["effort"]["tag"] == "I"
    assert out["lines"][0] == "Δ +400 · 50% · 20%H · −50 · −60 · −90"
    assert out["lines"][1] == "CVD 680 peak 09:30 → 480 (−200)"
    assert out["lines"][2] == "PE lead 22 → 18 (−4 in 5m) · Δ15 −17 · peak 35 09:30"
    assert out["lines"][4] == "SYNC NIFTY ▼VWAP · SNX ▼"
    assert out["leg"] == {"d": 1, "start": {"t": "09:15", "fut": 99, "spot": 87.0},
                          "ext": {"t": "09:25", "fut": 115, "spot": 103.0}}
    for s in out["setups"]:
        assert set(s) == {"name", "side", "checks", "state"} and s["name"] in ("FADE", "RIDE", "FADE-D")
        assert s["side"] in ("BUY", "SELL") and s["state"] in ("ARMED", "MATCH", "—")
        assert all(v in (True, False, None) for v in s["checks"].values())


# ---- live == replay -----------------------------------------------------------------------------------------------------

def test_live_equals_replay_no_look_ahead():
    """The block at every close is the same from the whole day's arrays and from arrays cut at that close: nothing
    recorded after a close changes it."""
    full_bars, full_X = top(), X_for(TOP_LEAD)
    for T in range(M("09:25") * 60, M("09:55") * 60 + 1, 300):
        live = decode.decode(decode.facts("NIFTY", T, [b for b in full_bars if b["s"] + 300 <= T], frame_v2.cut(full_X, T)),
                             [peer("SENSEX", -1)])
        replay = decode.decode(decode.facts("NIFTY", T, full_bars, full_X), [peer("SENSEX", -1)])
        assert live == replay, T


def test_a_reading_mid_bar_belongs_to_the_last_close():
    assert decode.at_close(M("10:02") * 60 + 30) == M("10:00") * 60 and decode.at_close(M("10:05") * 60) == M("10:05") * 60
    mid = decode.facts("NIFTY", M("09:47") * 60, top(), X_for(TOP_LEAD))
    assert decode.decode(mid, []) == decode.decode(g_top(T=M("09:45") * 60), [])


# ---- the registered setups are CALLED, never re-implemented -------------------------------------------------------------

def test_guard_decode_copies_no_registered_threshold():
    tree = ast.parse(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "decode.py"), encoding="utf-8").read())
    consts = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)}
    assert not consts & {faded.RATIO, confluence.TILT, faded.LEAD_PTS}         # 0.25, 0.10, 10.0
    names = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    assert not names & {"RATIO", "TILT", "LEAD_PTS", "LEAD_MIN", "WINDOW", "WINDOW_BARS", "WINDOW_MIN", "CUTOFF"}


def test_guard_the_setups_come_from_their_own_modules(monkeypatch):
    seen = []

    def fake_fd(ep, bars5, lead):
        seen.append("faded.evaluate")
        return {"bars": [{"a": {"ok": True}, "b": {"ok": None}, "oi": {"ok": False}}], "entry": {"t": "09:40"}}

    def fake_cs(b3):
        seen.append("confluence.setups")
        return [{"i": 0, "t": "09:42", "side": "SELL", "kind": "POCKET"}]

    def fake_ce(s, b3, chain, book, gc=None):
        seen.append("confluence.evaluate")
        return {"bars": [{"zone": {"ok": False}, "oi": {"ok": True}, "flow": {"ok": None}}], "entry": None}

    def fake_re(b3, rows, basis):
        seen.append("ride.entries")
        return [{"i": 0, "t": "09:45", "d": -1}]

    def fake_rv(e, b3, chain, book, gc=None):
        seen.append("ride.evaluate")
        return {"bars": [{"loc": {"ok": True}, "oi": {"ok": True}, "flow": {"ok": True}}], "entry": {"t": "09:45"}}
    monkeypatch.setattr(faded, "evaluate", fake_fd)
    monkeypatch.setattr(confluence, "setups", fake_cs)
    monkeypatch.setattr(confluence, "evaluate", fake_ce)
    monkeypatch.setattr(ride, "entries", fake_re)
    monkeypatch.setattr(ride, "evaluate", fake_rv)
    fin = {"bars3": [{"t": "09:42"}], "chain": ({}, {}), "book": ({}, set(), set()), "gc": None}
    rin = {"b3": [{"e": M("09:45") * 60}], "rows": [], "basis": None, "chain": fin["chain"], "book": fin["book"]}
    out = {s["name"]: s for s in decode.setups(g_top(), fin, rin)}
    assert set(seen) == {"faded.evaluate", "confluence.setups", "confluence.evaluate", "ride.entries", "ride.evaluate"}
    assert out["FADE"] == {"name": "FADE", "side": "SELL", "checks": {"zone": False, "oi": True, "flow": None},
                           "state": "ARMED"}
    assert out["RIDE"] == {"name": "RIDE", "side": "SELL", "checks": {"loc": True, "oi": True, "flow": True},
                           "state": "MATCH"}
    assert out["FADE-D"] == {"name": "FADE-D", "side": "SELL", "checks": {"2a": True, "2b": None, "3": False},
                             "state": "MATCH"}


def test_fade_d_reads_the_live_episode_at_the_current_close():
    """top()'s new highs open a SELL episode; at 09:45 its window is live: FADE-D's own readings there."""
    s = next(x for x in decode.setups(g_top()) if x["name"] == "FADE-D")
    ev = faded.evaluate(next(e for e in faded.episodes(top()[:6], []) if e["side"] == "SELL"), top()[:6],
                        g_top()["l5"])
    r = ev["bars"][-1]
    assert s == {"name": "FADE-D", "side": "SELL", "state": "MATCH" if ev["entry"] else "ARMED",
                 "checks": {"2a": r["a"]["ok"], "2b": r["b"]["ok"], "3": r["oi"]["ok"]}}
    assert r["close"] == "09:45"


def test_without_their_inputs_fade_and_ride_say_dash_never_a_guess():
    out = {s["name"]: s for s in decode.setups(g_top())}
    assert out["FADE"] == {"name": "FADE", "side": "SELL", "checks": {}, "state": "—"}
    assert out["RIDE"] == {"name": "RIDE", "side": "BUY", "checks": {}, "state": "—"}


# ---- A1: the DECODE leg is the zigzag's open leg; FADE-D keeps §1n's ----------------------------------------------------

def nifty_turn():
    """09:15 low 22,600 -> the 09:55 high 22,800 (each bar a new session high), then down 105 pts to 10:20 with no new
    session low: the 22 Oct 12:25 case (a mid-range turn the session-extreme leg cannot see)."""
    up = [22620, 22640, 22660, 22690, 22720, 22740, 22760, 22780, 22795]
    out = [b5(decode.hm(9 * 60 + 15 + 5 * k), c + 5, c - 20 if k else 22600, c, 300, o=c - 15)
           for k, c in enumerate(up)]
    out[-1]["h"] = 22800
    for k, c in enumerate([22770, 22740, 22720, 22700, 22690]):
        out.append(b5(decode.hm(10 * 60 + 5 * k), c + 25, c - 5, c, -300, o=c + 20))
    return out


def test_a_mid_range_turn_is_the_decode_leg_and_fade_d_keeps_its_own(monkeypatch):
    monkeypatch.setattr(decode, "ZZ_PCT", 50 / 22700)                  # the real floor: 50 pts at 22,700
    bars = nifty_turn()
    g = decode.facts("NIFTY", M("10:25") * 60, bars, None)
    assert (g["leg"]["d"], g["leg"]["from_bar"]) == (1, "09:15")           # §1n's session-extreme leg: unchanged
    assert g["fd"] == decode.fade_now(bars, g["l5"], decode.leg_of(bars)) and g["fd"]["side"] == "SELL"
    assert g["dleg"]["how"] == "swing" and (g["dleg"]["d"], g["dleg"]["from_bar"], g["dleg"]["from"]) == (-1, "09:55", 22800)
    out = decode.decode(g, [])
    assert out["call"]["text"].startswith("▼") and out["leg"]["start"] == {"t": "09:55", "fut": 22800, "spot": None}
    assert {s["name"]: s["side"] for s in out["setups"]}["FADE-D"] == "SELL"       # FADE-D's status: its own leg
    early = decode.facts("NIFTY", M("10:05") * 60, bars, None)            # 22,795 -> 22,770: 25 pts, no reversal yet
    assert early["dleg"]["how"] == "session" and early["dleg"]["d"] == 1


def test_the_reversal_is_the_panel_rule_floor_or_half_the_iv_priced_30_min_sigma(monkeypatch):
    monkeypatch.setattr(decode, "ZZ_PCT", 50 / 22700)
    bars = nifty_turn()
    assert round(decode.zz_thr(bars, None, M("10:25")), 1) == round(50 / 22700 * 22690, 1)
    monkeypatch.setattr(decode.rank, "scale", lambda X, card: {"sigma_d": 800.0})     # an expiry-afternoon IV
    thr = decode.zz_thr(bars, {"t": [1]}, M("10:25"))
    assert round(thr, 1) == round(0.5 * 800 * (365 * 30 / (252 * 375)) ** 0.5, 1)
    assert decode.swing_of(bars, thr) is None                         # 105 pts is under that reversal


# ---- N8: one sign a slot, never 8 on a 7 scale ---------------------------------------------------------------------------

def test_one_effort_and_one_peers_sign_so_thak_plus_jaari_never_passes_7():
    g = g_top(T=M("09:30") * 60)          # new highs 09:20 at 50% (strong, inside 15 min) and 09:25 at 20% (fading)
    dec, con = decode.signs(g, [])
    assert dict(dec)["effort"] == "nayi high 09:25 · 20% effort" and "effort" not in keys(con)     # the latest's, once
    split = [peer("SENSEX", -1), peer("BANKNIFTY", 1)]
    assert "peers" not in keys(sum(decode.signs(g_top(), split), []))       # split peers: neither side's sign
    P = [{"s": M("09:20") * 60, "t": "09:20", "close": M("09:25"), "d": 1, "origin": 104}]
    for T in range(M("09:25") * 60, M("09:55") * 60 + 1, 300):
        for ps in (split, [peer("SENSEX", 1)], [peer("SENSEX", -1)]):
            out = decode.decode(decode.facts("NIFTY", T, top(), X_for(TOP_LEAD), pushes=P), ps)
            assert out["call"]["d"] + out["call"]["c"] <= decode.OF, (T, out["call"])


# ---- N2: after an entry, FADE-D's chip reads HOLD v2, never a stale MATCH ----------------------------------------------

def test_an_entry_shows_its_hold_v2_state_instead_of_match():
    import confluence
    g = g_top(T=M("10:00") * 60)                                     # the last close 09:55, the 09:50 bar at 99
    en = {"d": -1, "t": "09:45", "E": 105.0, "stop": 116.0}
    rin = {"b3": [{"e": M("09:48") * 60, "c": 110.0}], "chain": confluence.chain_grid([]),
           "ones": [{"s": M("09:46") * 60, "h": 106.0, "l": 104.0, "c": 105.0}]}
    assert decode._held(en, g, rin) == "line 116f · +0.5R"           # still held: the line, R marked at the 09:50 close
    assert decode._held(en, dict(g, basis=12.0), rin) == "line 104s|116f · +0.5R"     # A25: the stop in spot too
    rin["ones"].append({"s": M("09:47") * 60, "h": 117.0, "l": 105.0, "c": 112.0})
    assert decode._held(en, g, rin) == "out @09:48 −1.0R"            # the line was hit at 09:47: out, never MATCH
    assert decode._held(en, g, {"b3": [], "chain": None}) is None     # nothing to read: the chip keeps MATCH


# ---- N7: the DECODE block's forward log ---------------------------------------------------------------------------------

def test_the_live_block_is_logged_once_per_close_with_its_rev(monkeypatch):
    import json
    import server
    blk = decode.decode(g_top(), [])

    def all_(day, T, live, keep=False):
        return {"NIFTY": blk, "SENSEX": decode.empty("x")}
    monkeypatch.setattr(server, "_decode_all", all_)
    monkeypatch.setattr(server, "_DECODE", {"out": {}, "last": {}, "busy": set(), "replay": {}})
    server._decode_run("2026-10-23", M("09:10") * 60, ("2026-10-23", M("09:10") * 60))         # before the open
    path = os.path.join(server.DECODE_DIR, "decode_2026-10-23.jsonl")
    assert not os.path.exists(path)
    for _ in range(2):                                                # the same close twice: written once
        server._decode_run("2026-10-23", M("09:45") * 60, ("2026-10-23", M("09:45") * 60))
    server._DECODE_SEEN.clear()                                       # a restart re-reads the keys
    server._decode_run("2026-10-23", M("09:45") * 60, ("2026-10-23", M("09:45") * 60))
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert [(r["idx"], r["T"]) for r in rows] == [("NIFTY", "09:45"), ("SENSEX", "09:45")]
    assert rows[0]["call"] == blk["call"] and rows[0]["rev"] == decode.REV and rows[0]["onesided"] == blk["onesided"]


# ---- A10 / A24 / A12: the lines ----------------------------------------------------------------------------------------

def test_a_lead_pinned_at_100_says_one_sided_thin():
    X = X_for(TOP_LEAD)
    X["ce_oi"] = [[990] * 9 for _ in X["t"]]                            # CE aaj likha -10 a strike: PE lead +100
    g = decode.facts("NIFTY", M("09:45") * 60, top(), X)
    assert "100 (ek-tarfa, patla)" in decode.lines(g, [])[2]
    assert "PE lead peak pe +100 (ek-tarfa, patla)" in dict(decode.signs(g, [])[1]).values()


def test_the_lead_lines_delta15_is_on_one_strike_set_and_says_when_the_window_moved():
    import test_onesided
    bars = [b5(decode.hm(9 * 60 + 15 + 5 * k), 22510 + k, 22490, 22500 + k, 10) for k in range(9)]
    line = decode.lines(decode.facts("NIFTY", M("10:00") * 60, bars, test_onesided.X_shift()), [])[2]
    assert "Δ15 0 · window shifted" in line and "peak 33.3 09:45" in line   # re-centred, it would read Δ15 −33.3


def test_fuel_before_its_40_minutes_says_why_and_when():
    assert decode.lines(g_top(), [])[3] == "FUEL ? · 40 min OI chahiye · 10:00 se"
    g = decode.facts("NIFTY", M("10:00") * 60, top(), X_for(TOP_LEAD), fuel={"vote": None, "why": "x"})
    assert decode.lines(g, [])[3] == "FUEL ? — x"
    g = decode.facts("SENSEX", M("10:00") * 60, top(), X_for(TOP_LEAD),        # A36: the reference's depth, always
                     fuel={"vote": None, "n": 3, "why": "could not check -- only 3 UX day(s) in this part of the day"})
    assert decode.lines(g, [])[3] == "FUEL ? · ref 3 din — only 3 UX day(s) in this part of the day"
    g = decode.facts("NIFTY", M("10:00") * 60, top(), X_for(TOP_LEAD),
                     fuel={"vote": -1, "n": 12, "rank": 91.0, "oi_pct": -0.84, "px": -20.0, "kind": "long chhod rahe"})
    assert decode.lines(g, [])[3] == "FUEL long chhod rahe · p91 · OI −0.84% · px −20 ▼ · ref 12 din"


def test_sensex_futures_reads_say_patla_and_nothing_else_changes():
    """A25, display only: SENSEX's Δ / CVD lines and its FADE-D chip carry the stamp with the median lots per 5-min
    bar; the call, the signs and every check are exactly NIFTY's on the same bars."""
    n = decode.decode(decode.facts("NIFTY", M("09:45") * 60, top(), X_for(TOP_LEAD)), [])
    s = decode.decode(decode.facts("SENSEX", M("09:45") * 60, top(), X_for(TOP_LEAD)), [])
    assert s["call"] == n["call"] and [(x["name"], x["checks"], x["state"]) for x in s["setups"]] == \
        [(x["name"], x["checks"], x["state"]) for x in n["setups"]]
    assert s["lines"][0] == n["lines"][0] + " · patla (med 1,000 lot/5m)"
    assert s["lines"][1] == n["lines"][1] + " · patla (med 1,000 lot/5m)"
    assert next(x for x in s["setups"] if x["name"] == "FADE-D")["thin"] == "patla (med 1,000 lot/5m)"
    assert all("thin" not in x for x in n["setups"]) and decode.patla_of("NIFTY", top()) == ""


def test_the_served_block_carries_its_age():
    import server
    blk = {"t": "10:05", "call": {}}
    assert server._decode_aged(blk, 10 * 3600 + 12 * 60)["age_s"] == 420 and "age_s" not in blk
    assert server._decode_aged(blk, None)["age_s"] is None and server._decode_aged(None, 1) is None
    assert server._decode_aged(decode.empty("x"), 40000)["age_s"] is None


# ---- fail-soft ----------------------------------------------------------------------------------------------------------

def test_missing_inputs_read_question_marks_never_a_crash():
    g = decode.facts("NIFTY", M("09:45") * 60, top(), None)                  # no chain, no fuel, no pushes, no basis
    out = decode.decode(g, [])
    assert out["lines"][2].startswith("PE lead ? —") and out["lines"][3] == "FUEL ? · 40 min OI chahiye · 10:00 se"
    assert out["leg"]["start"]["spot"] is None
    assert "lead" not in out["call"]["signs"] and out["call"]["kind"] in decode.KINDS
    fd = next(s for s in out["setups"] if s["name"] == "FADE-D")
    assert fd["checks"]["3"] is None                                        # unread lead: null, never False
    empty = decode.decode(decode.facts("NIFTY", M("09:15") * 60, [], None), [])
    assert empty["t"] is None and empty["lines"][0].startswith("Δ ?") and empty["setups"] == []


def test_a_broken_setup_is_that_chips_absence_only(monkeypatch):
    monkeypatch.setattr(faded, "episodes", lambda *a: 1 / 0)
    out = decode.decode(g_top(), [])
    assert [s["name"] for s in out["setups"]] == ["FADE", "RIDE"] and out["call"]["kind"] == "THAK"


def test_the_empty_block_has_every_field():
    e = decode.empty("x")
    assert set(e) == {"call", "lines", "setups", "leg", "t", "tag", "onesided", "effort"} and e["call"]["of"] == 7 and e["lines"] == ["? — x"]
    assert e["effort"]["why"] == "x" and e["effort"]["x"] is None
    assert e["onesided"]["type"] is None and e["onesided"]["why"] == "x"


def test_api_read_survives_a_decode_failure(monkeypatch):
    import server
    import v2feed
    monkeypatch.setattr(v2feed, "with_day", lambda day, fn: {"NIFTY": {"ok": False, "why": "no mark"}})
    monkeypatch.setattr(server, "_decode_for", lambda *a: 1 / 0)
    out = server._read_reply("2026-01-02", "NIFTY")
    c = out["indices"]["NIFTY"]
    assert out["ok"] and c["decode"] is None and c["decode_why"].startswith("could not check — the decode read failed")


def test_decode_all_one_index_failing_is_its_own_question_mark(monkeypatch):
    import confluence_log
    import server
    import v2feed
    monkeypatch.setattr(server.instruments, "ENABLED", ("NIFTY", "BANKNIFTY", "SENSEX"))

    def files(i, day, T, live):
        if i == "BANKNIFTY":
            raise OSError("no ux file")
        return {}
    monkeypatch.setattr(server, "_decode_files", files)
    monkeypatch.setattr(server, "_decode_facts", lambda i, day, T, live, D, F, keep=False: dict(g_top(T=T), idx=i))
    monkeypatch.setattr(v2feed, "with_day", lambda day, fn: fn(None))
    monkeypatch.setattr(confluence_log, "inputs", lambda *a, **k: 1 / 0)
    res = server._decode_all("2026-01-02", M("09:46") * 60, False)
    assert res["BANKNIFTY"]["call"]["text"] == "?" and "no ux file" in res["BANKNIFTY"]["lines"][0]
    assert res["NIFTY"]["t"] == "09:45" and res["NIFTY"]["lines"][4] == "SYNC NIFTY ▼VWAP · SNX ▼"
    assert {s["name"]: s["state"] for s in res["NIFTY"]["setups"]}["FADE"] == "—"      # its inputs failed: "—"
    assert server._decode_all("2026-01-02", M("09:10") * 60, False)["NIFTY"]["call"]["text"] == "?"


def test_live_blocks_are_computed_once_per_close_off_the_request_thread(monkeypatch):
    import server
    calls = []

    def all_(day, T, live, keep=False):
        calls.append((day, T, live))
        return {"NIFTY": {"t": decode.hm(T // 60)}}
    monkeypatch.setattr(server, "_decode_all", all_)
    monkeypatch.setattr(server, "_DECODE", {"out": {}, "last": {}, "busy": set(), "replay": {}})
    now = M("10:00") * 60 + 40                                  # inside the grace minute: still the 09:55 close
    assert server._decode_for("2026-01-02", now, True) is None  # nothing yet: "reading the day", never a block of zeros
    for th in [t for t in __import__("threading").enumerate() if t.name == "decode"]:
        th.join(5)
    assert server._decode_for("2026-01-02", now, True) == {"NIFTY": {"t": "09:55"}}
    assert calls == [("2026-01-02", M("09:55") * 60, True)]
    first = server._decode_for("2026-01-02", M("10:06") * 60 + 5, True)     # the next close: the last block meanwhile
    assert first == {"NIFTY": {"t": "09:55"}}
    for th in [t for t in __import__("threading").enumerate() if t.name == "decode"]:
        th.join(5)
    assert server._decode_for("2026-01-02", M("10:06") * 60 + 5, True) == {"NIFTY": {"t": "10:05"}}
    assert server._decode_for("2026-01-02", M("12:00") * 60, False) == {"NIFTY": {"t": "12:00"}}
    server._decode_for("2026-01-02", M("12:00") * 60, False)
    assert len(calls) == 3                                      # a replay close is computed once too
