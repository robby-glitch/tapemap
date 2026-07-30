"""contract_pair.py -- the 09:20 premium-matched leg picker.

Fixtures use the real snapshot row shape (`chain_metrics.py`'s own documented
contract / `data/chain_sample.jsonl`): each row is
``{"k": strike, "ce": {"ltp": ...}, "pe": {"ltp": ...}}`` -- strike key is
`k`, not `strike`.

Families:
  1. Exact-premium match     -- a diff-0 cross-strike pair is picked.
  2. Nearest-within-tolerance -- smallest positive diff inside tol wins.
  3. Nothing within tolerance -- None + a reason naming the closest miss.
  4. Per-index tolerance      -- the same 40-pt-diff pair passes for SENSEX
                                 (tol 50) and fails for NIFTY (tol 30).
  5. Tie resolved by the documented (unconfirmed) nearest-to-ATM rule.
  6. Missing / non-finite ltp is skipped, never substituted with 0.
  7. Empty input -- None + reason, never a crash.
  8. Unknown idx with no explicit tol is a hard error (no silent default).
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
    # CE200/PE150=5. Minimum is the exact 0 match, uniquely.
    pair, why = pick_pair(rows, "NIFTY")
    assert pair == {"ce": {"strike": 150, "ltp": 80.0},
                     "pe": {"strike": 200, "ltp": 80.0}}
    assert "150" in why and "200" in why and "80" in why


def test_nearest_within_tolerance_when_no_exact_match_exists():
    rows = [
        {"k": 100, "ce": {"ltp": 50.0}, "pe": {"ltp": 12.0}},
        {"k": 200, "ce": {"ltp": 20.0}, "pe": {"ltp": 45.0}},
    ]
    # CE100/PE200 diff=5, CE200/PE100 diff=8. Both within NIFTY tol (30);
    # the smaller (5) must win.
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


def test_tie_resolved_by_documented_nearest_to_atm_rule():
    rows = [
        {"k": 100, "ce": {"ltp": 200.0}, "pe": {"ltp": None}},
        {"k": 450, "ce": {"ltp": 60.0}, "pe": {"ltp": None}},
        # the ATM proxy: same-strike CE/PE closest to each other (0.5 apart),
        # far in absolute premium from every other leg so it cannot quietly
        # become part of a smaller-diff candidate itself.
        {"k": 500, "ce": {"ltp": 1000.0}, "pe": {"ltp": 1000.5}},
        {"k": 550, "ce": {"ltp": None}, "pe": {"ltp": 70.0}},
        {"k": 900, "ce": {"ltp": None}, "pe": {"ltp": 210.0}},
    ]
    # Two candidates tie at diff=10: CE100/PE900 (dist to atm 500 = 800) and
    # CE450/PE550 (dist to atm 500 = 100). Nearest-to-ATM must pick the
    # second.
    pair, why = pick_pair(rows, "NIFTY")
    assert pair == {"ce": {"strike": 450, "ltp": 60.0},
                     "pe": {"strike": 550, "ltp": 70.0}}
    assert "500" in why           # names the ATM proxy it used
    assert "UNCONFIRMED" in why or "unconfirmed" in why.lower()


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
    # CE600/PE100 (diff 0.05).
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
