"""Unit sanity for chain_metrics (plain asserts, no framework).

Run:  python test_chain_metrics.py
Covers the four checks from the plan: max pain on a symmetric chain = ATM,
GEX flip on a constructed profile, writer-score signs on scripted
OI/premium paths, and squeeze quiet-then-fires on the synthetic fixture.
"""

import json
from pathlib import Path

from chain_metrics import (GEX_SPOT_STEPS, WALL_HOLD, ChainState, _iv_at,
                           _sane_iv, max_pain, pcr)

FIXTURE = Path(__file__).parent / "data" / "chain_sample.jsonl"


def _row(k, ce_oi, pe_oi, ce_ltp=50.0, pe_ltp=50.0, iv=0.12,
         ce_chg=0, pe_chg=0):
    def side(oi, ltp, chg):
        return {"ltp": ltp, "oi": oi, "oi_chg": chg, "iv": iv,
                "vol": 1000, "bid": ltp - 0.1, "ask": ltp + 0.1,
                "avg": None, "gamma": None, "delta": None}
    return {"k": k, "ce": side(ce_oi, ce_ltp, ce_chg),
            "pe": side(pe_oi, pe_ltp, pe_chg)}


def snap(sec, spot, strikes):
    return {"ts": f"{sec//3600:02d}:{sec%3600//60:02d}:{sec%60:02d}",
            "sec": sec, "spot": spot,
            "atm": min(strikes, key=lambda s: abs(s["k"] - spot))["k"],
            "strikes": strikes}


def test_max_pain_symmetric():
    # symmetric OI mountain centred on 24300 -> max pain must be 24300
    strikes = [_row(k, 1_000_000 - abs(k - 24300) * 800,
                    1_000_000 - abs(k - 24300) * 800)
               for k in range(24000, 24601, 100)]
    assert max_pain(strikes) == 24300, max_pain(strikes)
    p_oi, p_v = pcr(strikes)
    assert abs(p_oi - 1.0) < 1e-9
    print("PASS max_pain symmetric = ATM, PCR = 1")


def test_writer_score_signs():
    # strike A: OI rises while premium falls  -> writer-built, w > 0
    # strike B: OI rises while premium rises  -> buyer-built,  w < 0
    st = ChainState()
    prev = None
    for i in range(16):                      # 150s at 10s steps -> 2 buckets
        sec = 34000 + i * 10
        a_ltp = 60.0 - i * 0.6               # bleeding premium
        b_ltp = 60.0 + i * 0.6               # ripping premium
        strikes = [_row(24200, 500_000 + i * 20_000, 300_000, ce_ltp=a_ltp),
                   _row(24400, 500_000 + i * 20_000, 300_000, ce_ltp=b_ltp)]
        s = snap(sec, 24300.0, strikes)
        m = st.update(s, 0.004, prev)
        prev = s
    by_k = {r["k"]: r for r in m["per_strike"]}
    assert by_k[24200]["ce_w"] > 0.3, by_k[24200]
    assert by_k[24400]["ce_w"] < -0.3, by_k[24400]
    print(f"PASS writer signs: bleed->w={by_k[24200]['ce_w']}, "
          f"rip->w={by_k[24400]['ce_w']}")


def test_gex_flip_and_walls():
    # writer-built books both sides of spot (dealers long gamma at wings),
    # buyer-built ATM (dealers short) -> cumulative GEX must cross zero and
    # walls must sit on the heavy writer strikes.
    st = ChainState()
    prev = None
    for i in range(16):
        sec = 34000 + i * 10
        strikes = [
            _row(24100, 200_000, 900_000 + i * 30_000,
                 pe_ltp=40.0 - i * 0.5),                 # PE writers below
            _row(24300, 400_000 + i * 30_000, 400_000 + i * 30_000,
                 ce_ltp=80.0 + i * 0.7, pe_ltp=80.0 + i * 0.7),  # buyers ATM
            _row(24500, 900_000 + i * 30_000, 200_000,
                 ce_ltp=40.0 - i * 0.5),                 # CE writers above
        ]
        s = snap(sec, 24300.0, strikes)
        m = st.update(s, 0.004, prev)
        prev = s
    assert m["flip_px"] is not None, m
    assert m["wall_dn"] == 24100 and m["wall_up"] == 24500, m
    print(f"PASS gex flip={m['flip_px']:.0f} walls={m['wall_dn']}/{m['wall_up']}"
          f" regime={m['gex_regime']}")


def test_squeeze_on_fixture():
    snaps = [json.loads(x) for x in
             FIXTURE.read_text(encoding="utf-8").splitlines() if x.strip()]
    st = ChainState()
    prev = None
    calm_max, fire_max, fire_side = 0.0, 0.0, None
    for i, s in enumerate(snaps):
        m = st.update(s, s.get("T", 1e-3), prev)
        prev = s
        t_min = i * 5 / 60.0
        sc = m["squeeze"]["score"]
        if t_min < 25:
            calm_max = max(calm_max, sc)
        if 40 <= t_min <= 70 and sc > fire_max:
            fire_max, fire_side = sc, m["squeeze"]["side"]
    assert calm_max < 0.15, f"squeeze not quiet in calm phase: {calm_max}"
    assert fire_max >= 0.30, f"squeeze failed to fire in rally: {fire_max}"
    assert fire_side == "UP", fire_side
    print(f"PASS squeeze: calm max={calm_max:.2f}, "
          f"rally max={fire_max:.2f} side={fire_side}")


def _ce_walls(rout, strikes_at=(24050, 24100), spot=24000.0, sec0=34000,
              oi0=900_000, extra=()):
    """Two writer-built CE walls go underwater in a rally, then either the near
    one ROLLS its OI up to the far one, or BOTH are routed. Per-strike unwind
    is identical either way — only the side total differs.

    Timing matters: the build must finish before the 300s velocity window
    opens, or `oi_then` still sits mid-build and the unwind measures ~0.
    """
    st = ChainState()
    prev, m = None, None
    ka, kb = strikes_at
    oi_a = oi_b = oi0
    for i in range(70):
        sec = sec0 + i * 10
        if i < 40:                        # 400s build: OI up, premium bleeding
            oi_a += 50_000
            oi_b += 50_000
            ltp = 60.0 - i * 0.5
        else:                             # rally: premium rips past 1.3x build
            ltp = 40.0 + (i - 40) * 1.0
            if i >= 50:                   # ... and the walls come off
                oi_a -= 60_000
                oi_b += -60_000 if rout else 60_000
        s = snap(sec, spot, [_row(ka, oi_a, 200_000, ce_ltp=ltp),
                             _row(kb, oi_b, 200_000, ce_ltp=ltp)]
                 + [_row(*e) for e in extra])
        m = st.update(s, 0.004, prev)
        prev = s
    return m["squeeze"]


def test_roll_is_not_a_squeeze():
    """The 2026-07-28 lesson: identical strike-local unwind means opposite
    things depending on what the neighbouring strike did."""
    rout = _ce_walls(rout=True)
    roll = _ce_walls(rout=False)
    assert rout["score"] >= 0.35, rout
    assert rout["side"] == "UP", rout
    assert roll["score"] < 0.15, roll
    print(f"PASS roll vs rout: rout={rout['score']:.2f} "
          f"roll={roll['score']:.2f}")


def test_squeeze_ignores_itm_books():
    """A CE book far BELOW spot is losers closing out, not a ceiling failing —
    it must not be able to score (2026-07-28 13:53 and 15:20)."""
    # identical rout, but both walls sit 250-300 pts BELOW spot (deep ITM)
    itm = _ce_walls(rout=True, strikes_at=(23700, 23750), spot=24000.0)
    assert itm["score"] == 0.0, itm
    print(f"PASS ITM CE books ignored: score={itm['score']:.2f}")


def test_iv_dropped_when_no_time_value():
    """Near expiry an option trades at intrinsic and the IV solver diverges;
    that must not reach `skew`, which votes on direction downstream."""
    st = ChainState()
    # ATM put worth 19.55 against 19.0 of intrinsic -> 0.55 of time value, and
    # an upper skew leg trading at 5 paise -> both solves are meaningless.
    strikes = [_row(23700, 400_000, 400_000, iv=0.10),
               _row(24000, 400_000, 400_000, ce_ltp=8.0, pe_ltp=19.55, iv=1.33),
               _row(24300, 400_000, 400_000, ce_ltp=0.05, iv=1.90)]
    m = st.update(snap(34000, 23981.0, strikes), 0.004, None)
    assert m["iv"]["atm_pe"] is None, m["iv"]        # no time value left
    assert m["iv"]["atm_ce"] == 1.33, m["iv"]        # 8.0 of tv: still a fit
    assert m["iv"]["skew"] is None, m["iv"]          # dead leg kills the skew
    print(f"PASS blown-up IV dropped: {m['iv']}")


def test_the_iv_gate_is_one_definition_not_two():
    """D3's root cause. The gate used to live INSIDE `_iv_at`, so it guarded
    the display path and nothing else. It is a standalone `_sane_iv` now and
    both callers share it."""
    good = _row(24000, 1, 1, ce_ltp=80.0, pe_ltp=80.0, iv=0.12)
    assert _sane_iv(good, "ce", 24000.0) == 0.12
    assert _iv_at([good], 24000, "ce", 24000.0) == _sane_iv(good, "ce", 24000.0)

    blown = _row(24000, 1, 1, iv=5.0)                 # 500% vol
    assert _sane_iv(blown, "ce", 24000.0) is None
    # The old GEX filter was `if v` — this is what it let through.
    assert bool(blown["ce"]["iv"]) is True


def test_a_blown_up_iv_cannot_reach_gex():
    """D3, the companion to test_iv_dropped_when_no_time_value above.

    That test pins the DISPLAY path. This one pins the computation: the GEX
    block read `s[side]["iv"]` raw, filtered by nothing but truthiness, so a
    500% solve priced gamma and flowed into the per-strike bars, gex_total,
    the flip and both walls. With every IV unusable there is nothing to price,
    and the honest answer is None — not a number derived from garbage."""
    st = ChainState()
    prev = None
    for i in range(4):
        strikes = [_row(k, 400_000, 400_000, iv=5.0)   # every solve blown up
                   for k in (24100, 24300, 24500)]
        s = snap(34000 + i * 10, 24300.0, strikes)
        m = st.update(s, 0.004, prev)
        prev = s
    assert m["gex_total"] is None, m
    assert m["flip_px"] is None, m
    assert m["wall_up"] is None and m["wall_dn"] is None, m
    print("PASS blown-up IV kept out of GEX entirely")


def test_gex_spot_reaches_past_one_strike_and_says_how_far():
    """D5. The near-money window was +/-1 strike step, which admitted two
    strikes -- three when spot sat exactly on a strike, so even the COUNT
    moved -- and one strike's OI blip could swing the sign of the number the
    regime label is read from."""
    st = ChainState()
    prev = None
    ks = (24200, 24300, 24400, 24500, 24600)          # 100-point steps
    for i in range(4):
        strikes = [_row(k, 400_000, 400_000, ce_ltp=80.0, pe_ltp=80.0)
                   for k in ks]
        s = snap(34000 + i * 10, 24400.0, strikes)
        m = st.update(s, 0.004, prev)
        prev = s
    assert m["gex_spot_band"] == 100.0 * GEX_SPOT_STEPS
    assert m["gex_spot_band"] > 100.0, "one strike step was the bug"
    # A book two strikes out must now be inside the window.
    assert abs(24600 - 24400) <= m["gex_spot_band"]
    print(f"PASS gex_spot band +/-{m['gex_spot_band']:.0f} pts")


def _wall_migrations(heavies, spot=24300.0):
    """Drive ChainState with a per-reading choice of which CE strike above spot
    carries the heavy writer book, and return only the WALL-MIGRATION events.

    Premium bleeds on every reading so a writer score actually builds; the OI
    is assigned rather than accumulated so the wall follows `heavies` at once.
    """
    st, prev, m = ChainState(), None, None
    ltp = {24100: 60.0, 24400: 60.0, 24500: 60.0}
    for i, heavy in enumerate(heavies):
        for k in ltp:
            ltp[k] = max(5.0, ltp[k] - 0.4)
        strikes = [_row(k,
                        900_000 if k == heavy else 200_000,
                        900_000 if k == 24100 else 200_000,
                        ce_ltp=ltp[k], pe_ltp=ltp[k],
                        ce_chg=60_000 if k == heavy else 0,
                        pe_chg=60_000 if k == 24100 else 0)
                   for k in (24100, 24400, 24500)]
        s = snap(34000 + i * 10, spot, strikes)
        m = st.update(s, 0.004, prev)
        prev = s
    return [e for e in m["wall_log"] if e["kind"] == "WALL-MIGRATION"]


def test_a_flickering_wall_announces_nothing():
    """P2. `self.walls[tag]` was overwritten every reading and ANY change
    printed a headline, so a wall oscillating between two strikes announced on
    every leg — twelve "migrations" in one hour on 2026-08-04. An oscillation
    returns to the announced wall on every other reading, which resets the
    candidate, so it can never accumulate WALL_HOLD."""
    flicker = [24400, 24500, 24400, 24500, 24400, 24500, 24400, 24500]
    assert _wall_migrations(flicker) == []


def test_a_wall_that_holds_announces_once():
    """The other half: hysteresis must not swallow a real migration, and must
    not repeat it once announced."""
    held = [24400] * 4 + [24500] * 6
    evts = _wall_migrations(held)
    assert len(evts) == 1, evts
    assert evts[0]["k"] == 24500
    assert "held" in evts[0]["msg"]
    print(f"PASS one migration after {WALL_HOLD} readings: {evts[0]['msg'][:60]}")


def test_hollow_squeeze_killed():
    """A tiny trapped book beside a huge one must not score: the raw ratio
    flatters it (2026-07-28 10:15 read 0.65-0.88 on 0.0M trapped)."""
    # same rout, but an 80M book elsewhere dwarfs the ~1.3M actually trapped
    hollow = _ce_walls(rout=True, oi0=20_000,
                       extra=[(23900, 1_000, 80_000_000)])
    assert hollow["score"] == 0.0, hollow
    print(f"PASS hollow squeeze killed: score={hollow['score']:.2f}")


def test_squaring_window_suppresses_direction():
    """After 15:05 the whole chain decays; no unwind carries direction."""
    late = _ce_walls(rout=True, sec0=54_000)     # 15:00 -> runs past 15:05
    assert late["score"] == 0.0 and late["side"] is None, late
    assert "squaring" in late["verdict"], late
    print(f"PASS squaring window: {late['verdict'][:56]}...")


def test_role_flip_and_book_zone():
    """24,000 going ceiling->floor was the headline of 2026-07-28 morning and
    produced no narrative at all. It must now emit an event."""
    st = ChainState()
    prev, ev = None, []
    for i in range(6):
        ce, pe = (40_000_000, 10_000_000) if i < 3 else (10_000_000, 40_000_000)
        s = snap(34000 + i * 60, 24000.0,
                 [_row(24000, ce, pe, ce_ltp=40.0, pe_ltp=40.0)])
        m = st.update(s, 0.004, prev)
        prev = s
        ev += m["wall_events"]
    flips = [e for e in ev if e["kind"] == "ROLE-FLIP"]
    assert len(flips) == 1, ev
    assert flips[0]["k"] == 24000 and flips[0]["side"] == "UP", flips
    assert "ceiling→floor" in flips[0]["msg"], flips[0]["msg"]
    assert m["in_book_zone"] is True, m["in_book_zone"]
    print(f"PASS role flip: {flips[0]['msg'][:70]}...")


def test_out_of_book_zone_flagged():
    """gex_total falls when price leaves the books — that is snap-back setup,
    not the end of dampening (the 15:01 misread)."""
    st = ChainState()
    strikes = [_row(24000, 40_000_000, 40_000_000),
               _row(24050, 30_000_000, 30_000_000)]
    m = st.update(snap(34000, 23400.0, strikes), 0.004, None)
    assert m["in_book_zone"] is False, m
    assert m["book_zone"] == [24000, 24050], m["book_zone"]
    assert m["mp_dist"] is not None
    print(f"PASS out-of-zone flagged: zone={m['book_zone']} "
          f"mp_dist={m['mp_dist']}")


def test_oi_flow_samples_at_the_mark():
    """Each row is the chain AS AT its clock mark, not an average over the
    interval that follows. Labelling it the other way shifts every row by one
    bucket — exactly how the first attempt disagreed with the reference tool
    on real 2026-07-28 data."""
    st = ChainState()
    for i in range(30):                    # 09:15..09:44
        st.minutes["09:%02d" % (15 + i)] = {
            "spot": 100.0 + i, "k": {24000: (100.0, 10.0 * (i + 1))}}
    rows = st.oi_flow(interval=15, strikes=[24000])
    at = {r["time"]: r for r in rows}
    # data runs to 09:44, so 09:45 has no mark and must not be invented
    assert list(at) == ["09:15", "09:30"], list(at)
    # 09:30 must read the 09:30 snapshot (put = 10*16 = 160), not 09:44's
    assert at["09:30"]["put"] == 160, at["09:30"]
    assert at["09:30"]["call"] == 100
    assert at["09:30"]["diff"] == 60
    assert at["09:30"]["pcr"] == 1.6
    assert abs(at["09:30"]["strength"] - 60 / 160) < 1e-9, at["09:30"]
    assert at["09:30"]["sentiment"] == "BULLISH"
    assert at["09:30"]["chg_dir"] == at["09:30"]["diff"] - at["09:15"]["diff"]
    assert rows[0]["chg_dir"] is None, rows[0]
    print(f"PASS oi_flow samples at the mark: 09:30 put={at['09:30']['put']} "
          f"pcr={at['09:30']['pcr']} str={at['09:30']['strength']:.2f}")


def test_oi_flow_breaks_and_selection():
    """Day high/low breaks fire only on a NEW extreme, and strike selection
    actually restricts the sum."""
    st = ChainState()
    for i, sp in enumerate([100, 101, 99, 104, 98]):
        for j in range(15):
            tot = i * 15 + j
            st.minutes["%02d:%02d" % (9 + tot // 60, tot % 60)] = {
                "spot": float(sp), "k": {24000: (10.0, 20.0), 24100: (5.0, 5.0)}}
    rows = st.oi_flow(interval=15, strikes=[24000])
    assert all(r["call"] == 10 and r["put"] == 20 for r in rows), rows[0]
    both = st.oi_flow(interval=15, strikes=[24000, 24100])
    assert both[0]["call"] == 15 and both[0]["put"] == 25, both[0]
    brks = [r["brk"] for r in rows if r["brk"]]
    assert "DHB" in brks and "DLB" in brks, brks
    assert rows[0]["brk"] is None, "the first mark cannot break anything"
    print(f"PASS oi_flow breaks + selection: {brks}")


if __name__ == "__main__":
    test_max_pain_symmetric()
    test_writer_score_signs()
    test_gex_flip_and_walls()
    test_squeeze_on_fixture()
    test_roll_is_not_a_squeeze()
    test_squeeze_ignores_itm_books()
    test_iv_dropped_when_no_time_value()
    test_hollow_squeeze_killed()
    test_squaring_window_suppresses_direction()
    test_role_flip_and_book_zone()
    test_out_of_book_zone_flagged()
    test_oi_flow_samples_at_the_mark()
    test_oi_flow_breaks_and_selection()
    print("ALL PASS")
