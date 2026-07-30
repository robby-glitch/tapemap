"""contract_pair.py -- the 09:20 premium-matched leg picker.

Fixtures use the real snapshot row shape (`chain_metrics.py`'s own documented
contract / `data/chain_sample.jsonl`): each row is
``{"k": strike, "ce": {"ltp": ...}, "pe": {"ltp": ...}}`` -- strike key is
`k`, not `strike`.

Families:
  1. Exact-premium match      -- a diff-0 cross-strike pair is picked when
                                  no ATM info narrows it further.
  2. Nearest-within-tolerance  -- smallest positive diff inside tol wins
                                  when no ATM info narrows it further.
  3. Nothing within tolerance  -- None + a reason naming the closest miss.
  4. Per-index tolerance       -- the same 40-pt-diff pair passes for SENSEX
                                  (tol 50) and fails for NIFTY (tol 30).
  5. Nearest-to-ATM beats a tighter-diff wing pair -- the actual fix: the
                                  objective is distance-to-ATM first, premium
                                  diff only as a tie-break.
  6. atm supplied vs. atm derived from the same-strike proxy.
  7. Missing / non-finite ltp is skipped, never substituted with 0.
  8. Empty input -- None + reason, never a crash.
  9. Unknown idx with no explicit tol is a hard error (no silent default).
"""

import math

import pytest

from contract_pair import pick_pair


def test_exact_premium_match_across_different_strikes():
    rows = [
        {"k": 100, "ce": {"ltp": 120.0}, "pe": {"ltp": 5.0}},
        {"k": 150, "ce": {"ltp": 80.0}, "pe": {"ltp": 45.0}},
        {"k": 200, "ce": {"ltp": 40.0}, "pe": {"ltp": 80.0}},
    ]
    # Cross diffs: CE100/PE150=75, CE100/PE200=40, CE150/PE100=75,
    # CE150/PE200=0 (exact, different strikes 150 vs 200), CE200/PE100=35,
    # CE200/PE150=5. Within NIFTY tol (30): CE150/PE200 (diff 0) and
    # CE200/PE150 (diff 5). No atm supplied, and the same-strike proxy (best
    # same-row CE~=PE match is row 150, diff 35) puts atm=150, at which both
    # admitted candidates sit equidistant (dist 50) -- so the diff tie-break
    # decides, and diff 0 wins.
    pair, why = pick_pair(rows, "NIFTY")
    assert pair == {"ce": {"strike": 150, "ltp": 80.0},
                     "pe": {"strike": 200, "ltp": 80.0}}
    assert "150" in why and "200" in why and "80" in why


def test_nearest_within_tolerance_when_no_exact_match_exists():
    rows = [
        {"k": 100, "ce": {"ltp": 50.0}, "pe": {"ltp": 12.0}},
        {"k": 200, "ce": {"ltp": 20.0}, "pe": {"ltp": 45.0}},
    ]
    # CE100/PE200 diff=5, CE200/PE100 diff=8. Both within NIFTY tol (30) and,
    # via the same-strike proxy (atm=200, row 200's own CE/PE are closest),
    # both sit at ATM-distance 100 -- so the diff tie-break decides and the
    # smaller (5) must win.
    pair, why = pick_pair(rows, "NIFTY")
    assert pair == {"ce": {"strike": 100, "ltp": 50.0},
                     "pe": {"strike": 200, "ltp": 45.0}}
    assert "5" in why


def test_nothing_within_tolerance_returns_none_and_reason():
    rows = [
        {"k": 100, "ce": {"ltp": 200.0}, "pe": {"ltp": None}},
        {"k": 200, "ce": {"ltp": None}, "pe": {"ltp": 10.0}},
    ]
    # Only cross pair possible is CE100(200)/PE200(10), diff=190, far past
    # any index's tolerance. Must return None, never widen tol to force it.
    pair, why = pick_pair(rows, "NIFTY")
    assert pair is None
    assert "190" in why
    assert "100" in why and "200" in why


def test_nothing_within_tolerance_even_with_atm_supplied():
    # The admission gate is on premium diff and is never bypassed just
    # because a real atm was supplied -- ATM only ranks pairs that already
    # cleared tolerance.
    rows = [
        {"k": 100, "ce": {"ltp": 200.0}, "pe": {"ltp": None}},
        {"k": 200, "ce": {"ltp": None}, "pe": {"ltp": 10.0}},
    ]
    pair, why = pick_pair(rows, "NIFTY", atm=150)
    assert pair is None
    assert "190" in why


def test_per_index_tolerance_40pt_diff_passes_sensex_fails_nifty():
    rows = [
        {"k": 77500, "ce": {"ltp": 140.0}, "pe": {"ltp": None}},
        {"k": 78000, "ce": {"ltp": None}, "pe": {"ltp": 100.0}},
    ]
    # diff = 40: outside NIFTY's +/-30, inside BANKNIFTY/SENSEX's +/-50.
    pair_n, why_n = pick_pair(rows, "NIFTY")
    assert pair_n is None
    assert "40" in why_n

    pair_s, why_s = pick_pair(rows, "SENSEX")
    assert pair_s == {"ce": {"strike": 77500, "ltp": 140.0},
                       "pe": {"strike": 78000, "ltp": 100.0}}

    pair_b, why_b = pick_pair(rows, "BANKNIFTY")
    assert pair_b is not None


def test_explicit_tol_overrides_the_per_index_default():
    rows = [
        {"k": 100, "ce": {"ltp": 140.0}, "pe": {"ltp": None}},
        {"k": 200, "ce": {"ltp": None}, "pe": {"ltp": 100.0}},
    ]
    # diff = 40, would fail NIFTY's default (30) -- but an explicit tol=45
    # must override the table regardless of idx.
    pair, why = pick_pair(rows, "NIFTY", tol=45)
    assert pair is not None
    assert "45" in why


def test_near_atm_pair_beats_a_tighter_diff_wing_pair():
    # THE FIX. Two candidates both clear tolerance: a deep-wing pair with a
    # near-zero premium diff (the old objective's winner) and a near-ATM
    # pair with a larger diff. The new objective must pick the near-ATM one.
    rows = [
        {"k": 23250, "ce": {"ltp": None}, "pe": {"ltp": 4.40}},   # far OTM PE
        {"k": 24300, "ce": {"ltp": 106.10}, "pe": {"ltp": 114.70}},  # near ATM
        {"k": 24800, "ce": {"ltp": 4.40}, "pe": {"ltp": None}},   # far OTM CE
    ]
    atm = 24300
    # Wing pair: CE24800/PE23250, diff=0.0, ATM-dist = |24800-24300| +
    # |23250-24300| = 500 + 1050 = 1550.
    # ATM pair: CE24300/PE24300 is same-strike (excluded) -- so the only
    # other admitted cross pair touching the ATM row is CE24300/PE23250 or
    # CE24800/PE24300; use the latter to keep it cross-strike and still far
    # closer to atm than the wing pair.
    # CE24800/PE24300: diff=|4.40-114.70|=110.30, ATM-dist=|24800-24300|+
    # |24300-24300|=500+0=500 -- closer to ATM than the wing pair's 1550,
    # so it must win despite a much larger diff, given a wide enough tol.
    pair, why = pick_pair(rows, "SENSEX", tol=200, atm=atm)
    assert pair == {"ce": {"strike": 24800, "ltp": 4.40},
                     "pe": {"strike": 24300, "ltp": 114.70}}
    assert "24300" in why  # names the atm used


def test_atm_supplied_vs_derived_from_same_strike_proxy():
    # Same chain, two admitted candidates tied at the same premium diff (10):
    # one near the strike 500 straddle, one far from it. With NO atm passed,
    # the same-strike proxy at k=500 (ce/pe 0.5 apart) is derived and the
    # near-500 candidate wins. With an EXPLICIT atm far on the other side,
    # the far candidate must win instead -- proving the supplied atm, not
    # the proxy, drives the ranking when both are available.
    rows = [
        {"k": 100, "ce": {"ltp": 200.0}, "pe": {"ltp": None}},
        {"k": 450, "ce": {"ltp": 60.0}, "pe": {"ltp": None}},
        {"k": 500, "ce": {"ltp": 1000.0}, "pe": {"ltp": 1000.5}},
        {"k": 550, "ce": {"ltp": None}, "pe": {"ltp": 70.0}},
        {"k": 900, "ce": {"ltp": None}, "pe": {"ltp": 210.0}},
    ]
    # Candidates tied at diff=10: CE100/PE900 (near 100/900) and CE450/PE550
    # (near 450/550).
    pair_derived, why_derived = pick_pair(rows, "NIFTY")
    assert pair_derived == {"ce": {"strike": 450, "ltp": 60.0},
                             "pe": {"strike": 550, "ltp": 70.0}}
    assert "500" in why_derived        # names the derived (proxy) ATM
    assert "proxy" in why_derived.lower()

    pair_supplied, why_supplied = pick_pair(rows, "NIFTY", atm=100)
    assert pair_supplied == {"ce": {"strike": 100, "ltp": 200.0},
                              "pe": {"strike": 900, "ltp": 210.0}}
    assert "100" in why_supplied
    assert "supplied" in why_supplied.lower()
    assert "proxy" not in why_supplied.lower()


def test_no_atm_available_falls_back_to_smallest_diff_deterministically():
    # No atm supplied, and no same-strike row carries both a valid CE and PE
    # ltp, so no proxy can be derived either -- ranking must fall back to
    # smallest premium diff, and why must say plainly that no ATM existed.
    rows = [
        {"k": 100, "ce": {"ltp": 200.0}, "pe": {"ltp": None}},
        {"k": 450, "ce": {"ltp": 60.0}, "pe": {"ltp": None}},
        {"k": 550, "ce": {"ltp": None}, "pe": {"ltp": 70.0}},
        {"k": 900, "ce": {"ltp": None}, "pe": {"ltp": 210.0}},
    ]
    # Same tie as above (diff=10 for both CE100/PE900 and CE450/PE550) but
    # with no k=500 straddle row this time, so no proxy exists.
    pair, why = pick_pair(rows, "NIFTY")
    assert pair == {"ce": {"strike": 100, "ltp": 200.0},
                     "pe": {"strike": 900, "ltp": 210.0}}
    assert "no ATM available" in why


def test_missing_or_non_finite_ltp_is_skipped_never_zero():
    rows = [
        {"k": 100, "pe": {"ltp": 0.05}},                          # no "ce" key at all
        {"k": 600, "ce": {"ltp": 0.1}, "pe": {"ltp": float("nan")}},
        {"k": 700, "ce": {"ltp": float("nan")}, "pe": {"ltp": 0.02}},
    ]
    # If a missing/non-finite ltp were substituted with 0, bogus diff-0
    # pairs would appear (e.g. "ce@100=0" vs "pe@600=0" from the nan-filled
    # pe, or "ce@100=0" vs "pe@700=0.02"). The only LEGITIMATE valid legs are
    # CE@600=0.1 and PE@{100:0.05, 700:0.02}, whose real minimum is
    # CE600/PE100 (diff 0.05); no same-strike proxy exists (no row has both
    # a valid ce and pe), so this exercises the no-ATM fallback too.
    pair, why = pick_pair(rows, "NIFTY")
    assert pair == {"ce": {"strike": 600, "ltp": 0.1},
                     "pe": {"strike": 100, "ltp": 0.05}}


def test_empty_input_returns_none_and_reason():
    pair, why = pick_pair([], "NIFTY")
    assert pair is None
    assert why and isinstance(why, str)

    pair2, why2 = pick_pair(None, "NIFTY")
    assert pair2 is None
    assert why2 and isinstance(why2, str)


def test_unknown_index_without_explicit_tol_is_a_hard_error():
    rows = [{"k": 100, "ce": {"ltp": 50.0}, "pe": {"ltp": 50.0}}]
    with pytest.raises(ValueError):
        pick_pair(rows, "MIDCPNIFTY")


def test_same_strike_ce_pe_is_never_paired_even_if_it_would_match():
    # A single straddle row where CE == PE at ONE strike must never be
    # returned as "the pair" -- the spec is explicit this is not the setup.
    rows = [{"k": 500, "ce": {"ltp": 50.0}, "pe": {"ltp": 50.0}}]
    pair, why = pick_pair(rows, "NIFTY")
    assert pair is None
    assert "different strikes" in why.lower() or "same strike" in why.lower()
