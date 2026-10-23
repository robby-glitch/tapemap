"""fold.py (rev 6, 6-blueprint.md §4) on synthetic recorded rows: the P2-01 proofs.

The rows are shaped exactly as the recorders write them (book: arrival t, ltt, ltp, ltq, vtt, b, a; chain:
ts + strikes with ltp / oi / delta; vpin_fast rows), one lot a second, every print an EXACT fill on the touch
it hit, so every fight is a known one. The §4.9 reproduction on the recorded days is tools/fold_replay.py
(read-only on data/), not a test: the day files are gzipped after a week."""
import math

import fold

DAY = "2026-09-30"
LOT = 65
PRIOR = [dict(bars=[dict(t=0, h=23005.0, l=23000.0, c=23002.0, vol=10)] * 375,
              fills=[dict(p=23000 + (i % 10), q=LOT) for i in range(50)])]     # BK = 30 lots, prior B = 5


def gen(segs, chain_every=10, oi=None, book_gap=(), chain_gap=()):
    """segs: [(start 'HH:MM:SS', seconds, side, dp)], contiguous. side +1 lifts the offer every second, -1 hits
    the bid, 0 alternates (two-sided). Returns the day's (book, chain, vpin) rows."""
    P, p = [], 23000.0
    for start, n, side, dp in segs:
        t0 = fold.ms(DAY, start)
        for i in range(n):
            p = round(p + dp, 1)
            P.append((t0 + i * 1000 + 500, p, side if side else (1 if i % 2 == 0 else -1)))
    book, vtt = [], 100000
    for i, (t, p, s) in enumerate(P):
        nxt = P[i + 1] if i + 1 < len(P) else None
        bid = nxt[1] if nxt and nxt[2] < 0 else round(p - 0.1, 1)
        ask = nxt[1] if nxt and nxt[2] > 0 else round(p + 0.1, 1)
        if ask <= bid:
            ask = round(bid + 0.1, 1)
        if any(a <= t < b for a, b in book_gap):
            continue
        vtt += LOT
        book.append(dict(t=t, ltt=t - 300, ltp=p, ltq=LOT, vtt=vtt, oi=1000000,
                         b=[[round(bid - 0.1 * j, 1), 65.0] for j in range(5)], a=[[round(ask + 0.1 * j, 1), 65.0] for j in range(5)]))
    chain, ts = [], [x[0] for x in P]
    for t in range((P[0][0] // 1000 + 1) * 1000, P[-1][0], chain_every * 1000):
        if any(a <= t < b for a, b in chain_gap):
            continue
        import bisect
        F = P[max(0, bisect.bisect_right(ts, t) - 1)][1]
        atm = round(F / 50) * 50
        strikes = []
        for k in range(atm - 500, atm + 501, 50):
            tv = 20 * math.exp(-abs(k - F) / 100) + 1
            dce = min(0.98, max(0.02, 0.5 + (F - k) / 400))
            g = (lambda ty: oi(k, ty, t) if oi else 100000 + 200 * ((t // 10000) % 7))
            strikes.append(dict(k=k, ce=dict(ltp=round(max(F - k, 0) + tv, 2), oi=g("CE"), delta=round(dce, 4)),
                                pe=dict(ltp=round(max(k - F, 0) + tv, 2), oi=g("PE"), delta=round(dce - 1, 4))))
        chain.append(dict(ts=fold.hms(t), spot=F, strikes=strikes))
    vpin = []
    for t in range(fold.ms(DAY, "09:15:00"), P[-1][0], 60000):
        sides = [s for tt, _, s in P if t <= tt < t + 60000]
        if not sides:
            continue
        b = sum(1 for s in sides if s > 0) / len(sides)
        vpin.append(dict(at=fold.hms(t + 60000), buy=round(20000 * b), sell=round(20000 * (1 - b)), inst="NIFTY-FUT:fast", day=DAY))
    return book, chain, vpin


def inputs(segs, **kw):
    expiry = kw.pop("expiry", None)
    book, chain, vpin = gen(segs, **kw)
    return dict(day=DAY, idx="NIFTY", lot=LOT, book=book, chain=chain, vpin=vpin, prior=PRIOR, expiry=expiry)


# path A (long PE, d = -1): sellers win at ~22985 (G 23003 with the 23000 CE wall), a pullback to 22999, sellers win
# again HIGHER (~22993: the give-up would loosen to 23005 -- refused), then lower (~22969: G 22981, trailed under the
# 22997 entry), then a rally through the give-up that is accepted and held. Two-sided minutes fix each fight.
PATH_A = [("09:15:00", 300, -1, -0.1), ("09:20:00", 60, 0, 0.0), ("09:21:00", 290, 1, 0.1), ("09:25:50", 70, 0, 0.0),
          ("09:27:00", 120, -1, -0.1), ("09:29:00", 60, 0, 0.0), ("09:30:00", 350, -1, -0.1), ("09:35:50", 70, 0, 0.0),
          ("09:37:00", 480, 1, 0.1), ("09:45:00", 180, 0, 0.0)]
PE = dict(k=23000, ty="PE", side="BUY", p0=100.0, entry_t="09:15:30", trade_id="T1")


def _g_path(v):
    return [e["row"]["G"]["px"] for e in v["events"] if e["row"]["G"]["px"] is not None]


def test_g_never_loosens_a_refused_loosening_is_logged():
    v = fold.read(PE, inputs(PATH_A), upto="09:48:00")
    kinds = [e["kind"] for e in v["events"]]
    assert "reset" in kinds and "refused_loosen" in kinds
    g = _g_path(v)
    assert all(b <= a for a, b in zip(g, g[1:])), g          # long PE: G above; it only ever comes down
    r = next(e for e in v["events"] if e["kind"] == "refused_loosen")
    assert r["refused"] > r["row"]["G"]["px"]


def test_no_fold_on_arrival_nothing_before_the_mark_can_fold():
    late = dict(PE, entry_t="09:43:00")            # marked mid-rally, price (22988) already beyond the 22981 give-up
    v = fold.read(late, inputs(PATH_A), upto="09:43:01")
    assert v["headline"] == "HOLD" and v["G"]["px"] > 22988          # the fight's give-up was not used: seeded beyond price
    assert all(e["t"] >= fold.ms(DAY, "09:43:00") for e in v["events"])
    v = fold.read(late, inputs(PATH_A), upto="09:48:00")
    for f in (e for e in v["events"] if e["kind"] == "fold"):
        t0 = next(e for e in v["events"] if e["kind"] == "tally")
        assert t0["t"] >= fold.ms(DAY, "09:43:00") and f["t"] > t0["t"]


def test_cant_check_over_a_hole_and_never_hold_inside_one():
    gap = (fold.ms(DAY, "09:31:00"), fold.ms(DAY, "09:32:30"))
    inp = inputs(PATH_A, book_gap=[gap], chain_gap=[gap])
    inside = fold.read(PE, inp, upto="09:31:45")
    assert inside["headline"].startswith("CAN'T CHECK since 09:30") and "silent" in inside["clause"]
    after = fold.read(PE, inp, upto="09:40:00")
    holes = [e for e in after["events"] if e["kind"] == "hole"]
    assert len(holes) == 1 and "TapeMap was down" in holes[0]["text"]
    assert after["holes"][0]["t0"] == "09:30:59" and after["holes"][0]["t1"] == "09:32:30"
    assert not any(gap[0] < e["t"] < gap[1] and e["row"]["headline"] == "HOLD" for e in after["events"])
    first = next(e for e in after["events"] if e["t"] >= gap[1])
    assert first["row"]["tally"]["t0"] is None or first["row"]["tally"]["t0"] >= "09:32:30"   # no tally spans it
    # the feed silent with the chain alive is named as such
    g2 = (fold.ms(DAY, "09:37:00"), fold.ms(DAY, "09:37:45"))
    v = fold.read(PE, inputs(PATH_A, book_gap=[g2]), upto="09:40:00")
    assert any(e["kind"] == "hole" and "order-flow feed silent 4" in e["text"] for e in v["events"])


FORM = {"WITH": "behind you: ", "AGAINST": "at ", "QUIET": "no level born or broken since ", "CAN'T CHECK": "could not check"}


def test_the_zone_sentence_agrees_with_its_chip_on_every_row():
    v = fold.read(PE, inputs(PATH_A), upto="09:48:00")
    rows = [e["row"] for e in v["events"] if e["kind"] == "bucket"]
    assert rows
    for r in rows:
        assert r["sentences"]["Z"].startswith(FORM[r["chips"]["Z"]]), (r["chips"]["Z"], r["sentences"]["Z"])
    assert v["rows"]["zone"]["sentence"].startswith(FORM[v["rows"]["zone"]["chip"]])


def test_one_fold_sound_per_event_and_a_reread_is_silent():
    inp = inputs(PATH_A)
    v = fold.read(PE, inp, upto="09:48:00")
    folds = [e for e in v["events"] if e["kind"] == "fold"]
    assert folds, "the rally through the give-up must fold"
    ids = [e["sound_id"] for e in folds]
    assert len(ids) == len(set(ids)) and all(i for i in ids)
    assert len({e["epoch"] for e in folds}) == len(folds)          # at most one per epoch
    assert v["headline"].startswith("FOLD ·") and v["line2"].startswith("still marked · now: ")
    again = fold.read(PE, inp, upto="09:48:00")
    assert [e["sound_id"] for e in again["events"] if e["kind"] == "fold"] == ids
    st = fold.start(PE, dict(inp, book=[r for r in inp["book"] if r["t"] <= fold.ms(DAY, "09:48:00")]))
    n = len(st.events)
    st.view(fold.ms(DAY, "09:48:00"))
    assert len(fold.step(st, {}, now=fold.ms(DAY, "09:48:00"))["events"]) == n and st.view()["new_events"] == []


def test_mode_line2_and_the_clause_forms():
    early = fold.read(PE, inputs(PATH_A), upto="09:23:00")        # G 23003 is above the 22997 entry: at entry
    assert early["mode"] == "at entry" and early["line2"].startswith("out if ") and early["line2"].endswith(" is accepted")
    v = fold.read(PE, inputs(PATH_A), upto="09:37:30")            # trailed by then: G 22988 came under the 22997 entry
    assert v["mode"] == "trailed" and "never back through" in v["line2"] and "held 2 buckets" in v["line2"]
    assert v["headline"] == "HOLD"
    assert v["clause"] == "nothing behind you now, nothing against you" or v["clause"].startswith(("behind you: ", "against you: "))
    for k in ("now", "peak", "at_G", "at_A", "intrinsic", "time"):
        assert k in v["prem"]
    assert v["prem"]["at_G_why"] in ("[I]",) or v["prem"]["at_G_why"].startswith("could not check")


PATH_X = [("13:20:00", 300, -1, -0.1), ("13:25:00", 60, 0, 0.0), ("13:26:00", 300, -1, -0.1), ("13:31:00", 60, 0, 0.0),
          ("13:32:00", 120, -1, -0.1), ("13:34:00", 60, 0, 0.0), ("13:35:00", 400, 1, 0.1), ("13:41:40", 120, 0, 0.0)]


def test_expiry_afternoon_the_give_up_follows_the_best_and_plain_acceptance_folds():
    tr = dict(PE, entry_t="13:20:30", trade_id="X1")
    v = fold.read(tr, inputs(PATH_X, expiry=DAY), upto="13:43:00")
    trails = [e for e in v["events"] if e["kind"] == "expiry_trail"]
    assert trails and all(e["ts"] >= "13:30:00" for e in trails)
    g = [e["row"]["G"]["px"] for e in v["events"] if e["row"]["G"]["px"] is not None]
    assert all(b <= a for a, b in zip(g, g[1:]))                    # only ever tighter
    assert v["events"][-1]["row"]["expiry_pm"] is True
    f = next(e for e in v["events"] if e["kind"] == "fold")
    assert f["why"] == "expiry" and "expiry afternoon" in f["text"]
    acc = next(e for e in v["events"] if e["kind"] == "accepted" and e["epoch"] == f["epoch"])
    assert acc["t"] == f["t"]                                       # no OI wait, no held wait
    # the same path on a non-expiry day: trailed, so plain acceptance does NOT fold by itself
    w = fold.read(tr, inputs(PATH_X), upto="13:43:00")
    assert not any(e["kind"] == "fold" and e["why"] == "expiry" for e in w["events"])
    assert not any(e["kind"] == "expiry_trail" for e in w["events"])


def test_the_oi_event_needs_three_updates_and_three_percent_on_top_of_three_sigma():
    def watch(path):
        u = [(i * 60000, oi) for i, oi in enumerate(path)]
        w = fold._OIWatch(("K", "CE"), 0)
        return [k for k, _, _ in w.update({("K", "CE"): u}, 65)]
    noise = [100000 + 200 * (i % 3) for i in range(16)]           # peak 100400; sigma = 1.4826 x 200 -> ~300
    assert watch(noise + [98000, 97800]) == []                     # -2.6 %, n = 2: z would pass (8.7), the floor does not
    assert watch(noise + [99000, 98500, 98000, 97700]) == []       # n >= 3 but never 3 % of the peak (-2.7 %)
    assert watch(noise + [99000, 98000, 96000]) == ["EVENT"]       # n = 3 and -4.4 %
    assert watch(noise + [99000, 98000, 96000, 101000]) == ["EVENT", "WITHDRAWN"]


def test_the_seller_reads_the_same_engine_with_her_own_sentences():
    ce = dict(k=23000, ty="CE", side="SELL", p0=60.0, entry_t="09:15:30", trade_id="S1")   # d = -1 like the long PE
    v = fold.read(ce, inputs(PATH_A), upto="09:21:00")
    assert v["d"] == -1 and v["mode"] == "at entry"
    assert "behind you: the move away from your strike" in v["rows"]["flow"]["sentence"]
    long_ = fold.read(PE, inputs(PATH_A), upto="09:21:00")
    assert long_["G"] == v["G"] and long_["prem"]["pct"] is not None and v["prem"]["pct"] is not None


def test_a_read_before_the_mark_and_the_numbers_carry_their_tags():
    v = fold.read(PE, inputs(PATH_A), upto="09:15:10")
    assert v["headline"] is None and v["why"] == "before the mark"
    v = fold.read(PE, inputs(PATH_A), upto="09:30:00")
    assert v["tag"]["M"] and v["tag"]["I"] and v["prem"]["tag"]["I"] == ["at_G", "at_A", "intrinsic", "time"]
    assert v["units"]["bucket"] == 30 and v["units"]["pooled_sessions"] == 1


CANDLE = ("candle", "close", "bar close")


def test_flat_next_fight_is_on_both_sides_of_the_forward_in_her_four_terms():
    inp = inputs(PATH_A)
    f = fold.flat(inp, upto="09:37:00")
    nf = f["next_fight"]
    assert nf["above"]["px"] > f["F"] > nf["below"]["px"]
    for side in ("above", "below"):
        x = nf[side]
        assert x["what"] and x["confirm"] and "followed by price" in x["confirm"] and "VPIN" in x["confirm"]
        assert not any(c in x["confirm"].lower() for c in CANDLE)
    assert nf["above"]["confirm"].endswith(": calls") and nf["below"]["confirm"].endswith(": puts")
    assert set(f["rows"]) == {"zone", "flow", "oi", "vpin"}
    assert all(r["chip"] in ("BUYERS", "SELLERS", "QUIET", "CAN'T CHECK") and r["sentence"] for r in f["rows"].values())
    assert {"BUYERS", "SELLERS"} & {r["chip"] for r in f["rows"].values()}          # flat names the side, never "you"
    for s in [r["sentence"] for r in f["rows"].values()] + [nf["above"]["what"], nf["below"]["what"], f["day"]]:
        assert "you" not in s.lower().replace("yourself", ""), s
    assert "day" in f["day"] and ("boxed" in f["day"] or "trending" in f["day"]) and "[M]" in f["day"]
    assert f["asof"] == "09:37:00" and f["gave_up"] is None
    # before the first chain snapshot: three sentences, never a zero
    early = fold.flat(inp, upto="09:15:05")
    assert early["next_fight"] is None and early["why"].startswith("could not check") and early["rows"]["oi"]["chip"] == "CAN'T CHECK"
    # the re-entry read after a FOLD is printed as unproven, never as a verdict
    fd = dict(G=22988, d=-1, k=23000, ty="PE", t="09:42:00", exit_prem=70.0)
    r = fold.flat(dict(inp, fold=fd), upto="09:48:00")["reentry"]
    assert r and r["unproven"] and ("unproven" in r["text"] or r["text"].startswith("no re-entry read"))
    assert not any(w in r["text"] for w in ("GO", "NO ", "odds"))


def test_if_you_were_in_equals_read_for_the_same_trade_marked_now():
    inp = inputs(PATH_A)
    v = fold.ifin(inp, 23000, "PE", "BUY", upto="09:37:00")
    assert v["ifin"] is True and v["headline"] == "HOLD" and v["p0"] > 0 and v["mode"] in ("at entry", "trailed")
    assert v["line2"].startswith("out if ") and "GO" not in v["headline"] and v["G"]["px"] and v["prem"]["at_G"]
    last = max((r for r in inp["book"] if r["t"] <= fold.ms(DAY, "09:37:00")), key=lambda r: r["t"])
    man = fold.read(dict(k=23000, ty="PE", side="BUY", p0=v["p0"], entry_t=last["ltt"], trade_id="M"), inp, upto=last["t"])
    for key in ("headline", "clause", "line2", "G", "A", "W", "mode", "E", "rows"):
        assert man[key] == v[key], key
    assert man["prem"] == v["prem"] and len(man["events"]) == len(v["events"])
    assert fold.ifin(dict(inp, chain=[]), 23000, "PE", "BUY", upto="09:37:00")["why"].startswith("could not check")


def test_after_her_exit_the_view_is_frozen_at_the_exit_and_the_log_goes_on():
    inp = inputs(PATH_A)
    live = fold.read(PE, inp, upto="09:48:00")
    at_exit = fold.read(PE, inp, upto="09:40:00")
    x = fold.read(PE, inp, upto="09:48:00", exit_t="09:40:00")
    assert x["frozen"] is True and x["exit_t"] == "09:40:00" and at_exit["frozen"] is False
    for key in ("headline", "clause", "line2", "G", "rows", "chips"):
        assert x[key] == at_exit[key], key
    assert x["prem"]["now"] == at_exit["prem"]["now"] and x["prem"]["pct"] == at_exit["prem"]["pct"]
    assert x["prem"]["now"] != live["prem"]["now"]                    # never 15:29's premium after a 10:20 exit
    assert len(x["events"]) == len(live["events"]) > len(at_exit["events"])
    assert any(e["after_exit"] for e in x["events"]) and not any(e["after_exit"] for e in at_exit["events"])
    assert fold.read(dict(PE, exit_t="09:40:00"), inp, upto="09:48:00")["prem"] == x["prem"]
    st = fold.start(dict(PE, exit_t="09:40:00"), dict(inp, book=[r for r in inp["book"] if r["t"] <= fold.ms(DAY, "09:39:00")]))
    assert fold.step(st, dict(book=[r for r in inp["book"] if fold.ms(DAY, "09:39:00") < r["t"] <= fold.ms(DAY, "09:48:00")]))["frozen"] is True


FIGHT_KINDS = ("won", "absorbed", "disputed", "trapped", "released", "failed")


def test_fight_events_are_placed_once_with_a_price_and_never_revised():
    inp = inputs(PATH_A)
    v = fold.read(PE, inp, upto="09:48:00")
    ev = [e for e in v["events"] if e["kind"] in FIGHT_KINDS]
    assert sum(1 for e in ev if e["kind"] == "won") >= 2 and any(e["kind"] == "trapped" for e in ev)
    for e in ev:
        assert isinstance(e["px"], float) and e["side"] in (1, -1) and e["by"] in ("price", "book") and e["text"]
        assert e["kind"] != "failed" or e["by"] == "price"
    keys = [(e["kind"], e["t"], e["px"], e["side"]) for e in ev]
    assert len(keys) == len(set(keys))
    assert all(e["px"] is not None for e in v["events"])              # every mark has a (t, px)
    f = next(e for e in v["events"] if e["kind"] == "fold")
    assert f["px"] and f["bucket_px"] and f["bucket_t"] <= f["t"]
    again = fold.read(PE, inp, upto="09:48:00")
    assert [(e["kind"], e["t"], e["px"], e["side"]) for e in again["events"] if e["kind"] in FIGHT_KINDS] == keys
    st = fold.start(PE, dict(inp, book=[r for r in inp["book"] if r["t"] <= fold.ms(DAY, "09:48:00")]))
    n = len(st.events)
    assert len(fold.step(st, {}, now=fold.ms(DAY, "09:48:00"))["events"]) == n
    assert v["d"] == -1 and fold.read(PE, inp, upto="09:15:10")["d"] == -1
    assert v["units"]["basis"] is not None and "forward" in v["units"]["basis_of"]
    fl = fold.flat(inp, upto="09:48:00")
    assert fl["basis"] == v["units"]["basis"] and any(m["kind"] == "won" for m in fl["marks"]) and any(m["kind"] == "wall" for m in fl["marks"])
    assert all(m["t"] <= fold.ms(DAY, "09:48:00") and m["px"] for m in fl["marks"])


def test_the_view_carries_the_give_up_staircase_the_wall_behind_px_and_the_wall_ahead_state():
    """Output fields only (the Trade tab's D.14): G_steps is the give-up's staircase, W sits at K + basis like A,
    and A carries W's state vocabulary. None of them changes a word, a level or a fold."""
    v = fold.read(PE, inputs(PATH_A), upto="09:48:00")
    steps = v["G_steps"]
    assert steps and all(set(s) == {"t", "px", "why"} for s in steps)
    path = [g for i, g in enumerate(_g_path(v)) if i == 0 or g != _g_path(v)[i - 1]]
    assert [s["px"] for s in steps] == path                                  # the same staircase the events carry
    assert all(b["px"] <= a["px"] for a, b in zip(steps, steps[1:]))         # long PE: it only ever comes down
    assert steps[-1]["px"] == v["G"]["px"]
    if v["W"] is not None:
        assert abs(v["W"]["px"] - (v["W"]["k"] + v["units"]["basis"])) <= 1
    if v["A"] is not None:
        assert "state" in v["A"] and v["A"]["state"] in (None, "building", "stopped", "off")
    before = fold.read(PE, inputs(PATH_A), upto="09:15:10")
    assert before["headline"] is None and "G_steps" not in before           # nothing before the mark


def test_premium_at_a_futures_price_is_priced_through_the_basis():
    """G and A are futures-chart prices; F is the options' forward (future minus basis). The premium at the
    future's own price is today's premium. 2026-10-03: the shift missed the basis, so on 30 Sep (basis 77)
    "at your give-up" read 152 when the call there was worth ~113, and 178 at the FOLD while it traded 127.55."""
    inp = inputs(PATH_A)
    upto = fold.ms(DAY, "09:37:30")
    st = fold.start(PE, dict(inp, book=[r for r in inp["book"] if r["t"] <= upto], chain=[c for c in inp["chain"] if fold.ms(DAY, c["ts"]) <= upto]))
    st.bas = 77.0                                         # the fixture's basis is 0, which hid the bug
    own = next(x["pe"]["ltp"] for x in st.rc["strikes"] if x["k"] == st.k)
    assert abs(st._prem_at(st.F + st.bas, st.rc_t)[0] - own) < 0.1


def _index_under(inp, d):
    """The chain's index sits d under the future the options are priced off (the live gap: index 117, forward 94)."""
    return dict(inp, chain=[dict(c, spot=c["spot"] - d) for c in inp["chain"]])


def test_her_basis_draws_and_prints_a_strike_but_decides_nothing():
    """2026-10-05, ONE BASIS (her word): a strike is drawn and printed at K + (future - index); the engine's words,
    give-up, events and chips stay on the forward basis -- the signed rule does not move."""
    a = fold.read(PE, inputs(PATH_A), upto="09:48:00")
    b = fold.read(PE, _index_under(inputs(PATH_A), 40), upto="09:48:00")
    same = lambda v: (v["headline"], v["clause"], v["G"], v["G_steps"], v["chips"],    # noqa: E731
                      [(e["kind"], e["t"], e.get("px"), e.get("side")) for e in v["events"]])
    assert same(a) == same(b)
    assert b["units"]["basis"] == a["units"]["basis"] and b["units"]["basis_ix"] == round(a["units"]["basis_ix"] + 40, 1)
    for w in ("W", "A"):
        if b[w] is not None:
            assert abs(b[w]["px"] - (b[w]["k"] + b["units"]["basis_ix"])) <= 1
    assert b["W"] is not None or b["A"] is not None


def test_the_flat_read_sorts_its_futures_levels_against_the_future():
    """2026-10-05 live: every flat level is a futures-chart price, but they were sorted against F, the forward ~94
    under the future, so 22,565 read "upar" with the future at 22,640. Above means above the future now."""
    inp = inputs(PATH_A)
    upto = fold.ms(DAY, "09:48:00")
    st = fold.start(PE, dict(inp, book=[r for r in inp["book"] if r["t"] <= upto],
                             chain=[c for c in inp["chain"] if fold.ms(DAY, c["ts"]) <= upto]))
    st.bas, st.F = 94.0, st.last_p - 94.0
    nf = st.flat_view(upto)["next_fight"]
    assert nf and nf["below"]["px"] is not None and nf["below"]["px"] < st.last_p
    assert nf["above"]["px"] is None or nf["above"]["px"] > st.last_p
