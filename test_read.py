"""test_read.py -- THE READ (read.py): held, OI first, never re-decided from scratch, and live == replay."""
import read

K = [22300.0, 22350.0, 22400.0, 22450.0, 22500.0, 22550.0, 22600.0, 22650.0, 22700.0]
BASE = 5000                                   # OI at yesterday's close, thousands, every strike and side


def day(spot_at, ce_add, pe_add, flow_sell=0.7, start=33300, end=55800):
    """A synthetic session, one chain row a minute. spot_at(sec) -> spot; ce_add(k, sec, spot) / pe_add(...) ->
    aaj likha in thousands; the future's 1-s bars carry `flow_sell` of the volume as sells."""
    t, spot, ce, pe, bars = [], [], [], [], []
    for sec in range(start, end + 1, 60):
        s = spot_at(sec)
        t.append(sec)
        spot.append(s)
        ce.append([BASE + ce_add(k, sec, s) for k in K])
        pe.append([BASE + pe_add(k, sec, s) for k in K])
        bars.append([sec, round((s + 50) * 10), 100, round(100 * (1 - flow_sell))])
    ltp = [[2000] * len(K) for _ in t]
    return {"step": 50, "t": t, "spot": spot, "ks": K, "ce_oi": ce, "pe_oi": pe, "ce_ltp": ltp, "pe_ltp": ltp,
            "base_ce": {k: BASE for k in K}, "base_pe": {k: BASE for k in K}, "bars": bars, "lot": 1}


def fall(sec):
    """22,520 at the open, a steady grind to 22,250, with a 40-pt bounce at 12:00-12:30."""
    s = 22520 - (sec - 33300) / (55800 - 33300) * 270
    return s + (40 if 43200 <= sec <= 45000 else 0)


def calls_above(k, sec, s):
    return int((sec - 33300) / 60 * 20) if k >= s else 0


def no_puts(k, sec, s):
    return 0


def words(tl):
    return [(r["t"], r["word"], r["dir"]) for r in tl["rows"] if r["word"] != "BAN RAHA"]


def test_call_writing_all_day_is_a_trend_down_held_through_the_bounce():
    D = day(fall, calls_above, no_puts)
    tl = read.timeline(D, [], None)
    w = words(tl)
    assert w[0] == ("09:45", "TREND", -1)                       # named at 09:45, not before
    assert all(x[1:] == ("TREND", -1) for x in w)               # held through the 12:00 bounce: one word all day
    assert all(r["word"] == "BAN RAHA" for r in tl["rows"] if r["t"] < "09:45")
    c = read.card(D, tl)
    assert c["changes"] == 0 and c["word"] == "TREND" and c["arrow"] == "▼"
    assert c["lines"][0]["k"] == "FLIP" and c["lines"][0]["spot"] > c["spot"]
    assert [x["act"] for x in c["trade"]] == ["BUY", "SELL"] and c["trade"][0]["side"] == "PE"
    assert "khilaaf" in c["against"]


def test_a_close_past_the_flip_breaks_the_read_and_it_is_reread_at_once():
    def rip(sec):                                               # the grind, then a squeeze far above every call wall
        return fall(sec) if sec < 46800 else 22800
    D = day(rip, calls_above, no_puts)
    tl = read.timeline(D, [], None)
    brk = [e for e in tl["events"] if e["kind"] == "BREAK"]
    assert brk and brk[0]["t"] == "13:00" and "FLIP" in brk[0]["text"]
    at13 = [r for r in tl["rows"] if r["t"] == "13:00"][0]
    assert (at13["word"], at13["dir"]) != ("TREND", -1)


def test_the_flip_trails_toward_price_never_away():
    D = day(fall, calls_above, no_puts)
    flips = [r["flip"] for r in read.timeline(D, [], None)["rows"] if r["flip"] is not None]
    assert flips == sorted(flips, reverse=True)                 # a down read's line only ever comes down


def test_both_sides_writing_with_flat_price_is_a_range_with_a_box(monkeypatch):
    monkeypatch.setattr(read, "_price", lambda *a: {"vote": 0, "word": "PIN/CHOP", "raw": "PIN", "dir": 0, "tag": "I"})
    both = lambda k, sec, s: int((sec - 33300) / 60 * 10)
    D = day(lambda sec: 22480.0, both, both, flow_sell=0.5)
    tl = read.timeline(D, [], None)
    assert {r["word"] for r in tl["rows"] if r["t"] >= "09:45"} == {"RANGE"}
    c = read.card(D, tl)
    assert [x["k"] for x in c["lines"][:2]] == ["TOP", "BOTTOM"]
    assert c["lines"][0]["spot"] > 22480 > c["lines"][1]["spot"]
    assert [x["act"] for x in c["trade"]] == ["SELL", "SELL"]


def test_a_lean_without_the_writers_is_not_broken_by_them(monkeypatch):
    """The first replay's bug: every LEAN broke one mark after it formed (the TREND's give-back test applied to it)."""
    monkeypatch.setattr(read, "_price", lambda *a: {"vote": -1, "word": "TREND ▼", "raw": "TREND", "dir": -1, "tag": "I"})
    both = lambda k, sec, s: int((sec - 33300) / 60 * 10)
    D = day(fall, both, both)
    tl = read.timeline(D, [], None)
    w = words(tl)
    assert w and all(x[1:] == ("LEAN", -1) for x in w)
    assert not [e for e in tl["events"] if e["kind"] == "BREAK"]
    assert {r["since"] for r in tl["rows"] if r["word"] == "LEAN"} == {"09:45"}


def test_a_floor_quitting_near_spot_is_an_event_and_a_far_one_is_not():
    def pe(k, sec, s):
        if k == 22500.0:
            return 3000 if sec < 36000 else 1200                # +30L by 10:00, then 60 % covered, at the money
        if k == 22700.0:
            return 2500 if sec < 36000 else 900                 # the same, four strikes away: profit-taking
        return 0
    D = day(lambda sec: 22480.0, lambda k, sec, s: 500, pe, flow_sell=0.5)
    ev = [e for e in read.timeline(D, [], None)["events"] if e["kind"] == "QUIT"]
    assert [(e["k"], e["side"]) for e in ev] == [(22500.0, "PE")]
    assert "bhage" in ev[0]["text"]


def test_live_equals_replay_no_look_ahead():
    """What the face showed at 11:07 is exactly the replay's prefix to 11:05: a later row never changes an earlier mark."""
    D = day(fall, calls_above, no_puts)
    full = read.timeline(D, [], None)["rows"]
    cut = 11 * 3600 + 7 * 60
    n = read._at(D, cut) + 1
    part = {k: (v[:n] if k in ("t", "spot", "ce_oi", "pe_oi", "ce_ltp", "pe_ltp") else v) for k, v in D.items()}
    part["bars"] = [b for b in D["bars"] if b[0] <= cut]
    live = read.timeline(part, [], None, now=cut)["rows"]
    assert live and live[-1]["t"] == "11:05"
    assert live == full[: len(live)]


def test_a_late_start_takes_flow_from_gocharting_bars_closed_before_the_first_tick():
    """Server up at 10:11: FLOW reads GoCharting's 5-min bars from the open (tagged GC), each only once it has
    closed, and never as a price (basis stays on the live ticks)."""
    D = day(fall, calls_above, no_puts)
    D["bars"] = [b for b in D["bars"] if b[0] >= 36660]                  # the future's ticks begin 10:11
    D["pre"] = [(t0 + 299, 1000, 200) for t0 in range(33300, 36600, 300)]  # GC 09:15..10:05, 80% sells
    rows = {r["t"]: r for r in read.timeline(D, [], None)["rows"]}
    assert rows["09:20"]["flow"]["vol"] == 1000                           # the 09:15 bar, closed at 09:19:59
    assert rows["09:45"]["flow"]["vote"] == -1 and rows["09:45"]["flow"]["gc"] == "09:45"
    assert rows["09:45"]["basis"] is None                                 # a GC bar is never a price
    assert rows["10:20"]["flow"]["vol"] == 11 * 1000 + 9 * 100            # GC to 10:10 + live 10:11..10:19
    assert rows["10:20"]["flow"]["gc"] == "10:10"
    c = read.card(D, read.timeline(D, [], None))
    assert "GC" in next(x["v"] for x in c["chips"] if x["k"] == "FLOW")
    D.pop("pre")
    assert read.timeline(D, [], None)["rows"][4]["flow"]["vote"] is None  # without GC: blind before 10:11, as before


def test_no_close_oi_means_the_writers_are_blind_never_zero():
    D = day(fall, calls_above, no_puts)
    D["base_ce"], D["base_pe"] = {}, {}
    r = read.timeline(D, [], None)["rows"][-1]
    assert r["writers"]["vote"] is None and r["writers"]["why"].startswith(read.CC)
    assert r["word"] == "WAIT"                                   # flow alone never names a trend


def test_lakh_matches_the_apps_unit():
    assert read.lakh(4260) == "+42.6L" and read.lakh(-50) == "−0.5L" and read.lakh(43400) == "+434L"


# ---- decode-loop Phase 0 (2026-10-19) -------------------------------------------------------------------------------

def test_d1_the_nine_are_symmetric_around_atm_and_say_the_edge():
    """8 Oct's window kept 17 strikes round the OPENING atm; spot walked to its edge and "the nine nearest" became
    lopsided. Now: ATM +/- 4 on the grid, narrowed on both sides at an edge, and said."""
    D = day(lambda sec: 22600.0, lambda k, sec, s: 100, lambda k, sec, s: 100)       # strikes 22,300 .. 22,700
    w = read.writers(D, 5)
    assert w["ks"] == [22500.0, 22550.0, 22600.0, 22650.0, 22700.0] and w["edge"] == 2
    D2 = day(lambda sec: 22500.0, lambda k, sec, s: 100, lambda k, sec, s: 100)
    assert read.writers(D2, 5)["edge"] is None and len(read.writers(D2, 5)["ks"]) == 9
    D3 = day(lambda sec: 22690.0, lambda k, sec, s: 100, lambda k, sec, s: 100)       # ATM 22,700: nothing above
    w3 = read.writers(D3, 5)
    assert w3["vote"] is None and "edge" in w3["why"] and w3["why"].startswith(read.CC)


def test_d2_writing_vs_buying_is_an_iv_residual_and_never_moves_the_read():
    D = day(lambda sec: 22500.0, lambda k, sec, s: (40 if k == 22600.0 and sec >= 40000 else 0),
            lambda k, sec, s: (40 if k == 22400.0 and sec >= 40000 else 0))
    n = len(D["t"])
    ce_iv = [[1500] * len(K) for _ in range(n)]
    pe_iv = [[1500] * len(K) for _ in range(n)]
    for i, sec in enumerate(D["t"]):
        if sec >= 40000:
            ce_iv[i][K.index(22600.0)] = 1450          # CE OI up, its IV down against a flat ATM: sold into
            pe_iv[i][K.index(22400.0)] = 1560          # PE OI up, its IV up: bought
    i, i30 = read._at(D, 41000), read._at(D, 41000 - 1800)
    bare = read.timeline(D, [], None)
    D.update(ce_iv=ce_iv, pe_iv=pe_iv, slow=1)
    wb = read.writing_vs_buying(D, i, i30)
    assert wb["ce"]["word"] == "bech ke likha" and wb["pe"]["word"] == "khareed ke" and wb["tag"] == "I"
    assert read.timeline(D, [], None) == bare                                   # display only: the READ is unchanged
    assert read.writing_vs_buying({**D, "ce_iv": None}, i, i30)["why"].startswith(read.CC)


def test_d6_the_days_high_and_low_are_the_ticks_not_a_grid():
    D = day(fall, calls_above, no_puts)
    D["hl"] = [[b[0], b[1], b[1]] for b in D["bars"]]
    D["hl"][100] = [D["hl"][100][0], 230000, D["hl"][100][2]]                   # a 23,000 print inside one second
    hl = read.day_hl(D)
    assert hl["fut"]["hi"] == 23000.0 and hl["fut"]["hi_t"] == read.hm(D["hl"][100][0])
    assert hl["spot"]["hi"] == max(D["spot"]) and hl["spot"]["lo"] == min(D["spot"])
    early = read.day_hl(D, now=D["hl"][99][0])                                  # as of before the print: not seen
    assert early["fut"]["hi"] < 23000.0


def test_quit_on_a_strike_price_is_already_through_stamps_how_far():
    """N4 (display only): a QUIT on a strike already ITM says "paar +N"; an OTM one says nothing. The logic is unchanged."""
    ks = [22300.0 + 50 * j for j in range(13)]
    ce = lambda add: [1000 + (add if k == 22600 else 0) for k in ks]           # noqa: E731
    D = {"ks": ks, "step": 50, "spot": [22550.0, 22683.0], "ce_oi": [ce(100), ce(10)], "pe_oi": [[1000] * 13] * 2,
         "base_ce": {k: 1000 for k in ks}, "base_pe": {k: 1000 for k in ks}}
    peaks, done, ev = {}, set(), []
    read._quits(D, 0, "11:40", peaks, done, ev)
    read._quits(D, 1, "11:45", peaks, done, ev)
    assert [e["text"] for e in ev] == ["22,600 CE likhne wale bhage · +1.0L → +0.1L · paar +83"]
    assert ev[0]["en"] == "22,600 CE ceiling gone · paar +83"
    D["spot"][1] = 22560.0                                                       # OTM by 40: no stamp
    ev2, peaks2, done2 = [], {}, set()
    read._quits(D, 0, "11:40", peaks2, done2, ev2)
    read._quits(D, 1, "11:45", peaks2, done2, ev2)
    assert [e["text"] for e in ev2] == ["22,600 CE likhne wale bhage · +1.0L → +0.1L"]
