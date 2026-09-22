"""An unset session extreme must never reach the screen as a price.

MEASURED 2026-09-22, live, NIFTY 09:27 — before the session had an extreme,
`engine.Session.context` put `fut_lo`/`fut_hi` straight into its level
candidates while both were still the `__init__` sentinels, and the operator's
playbook printed:

    FADE a test of 1000000000000000000 (session low)
    BREAK of -1000000000000000000 (session high) needs vol rank >0.9

Two failures in one line. The sentinels are unbounded, so -1e18 was the only
candidate below spot and +1e18 the only one above: each won `floor`/`cap`
outright rather than losing to a real level. And the labels came out
backwards, the "session low" sentinel sitting ABOVE price, because the low's
sentinel is the POSITIVE one.
"""

import engine


def test_unset_extremes_are_not_levels():
    """Both sentinels present, the opening state: no candidate at all."""
    assert engine.session_extremes(1e18, -1e18) == []


def test_real_extremes_survive_with_their_labels():
    assert engine.session_extremes(23436.5, 23475.0) == [
        ("session low", 23436.5), ("session high", 23475.0)]


def test_one_sided_warmup_keeps_only_the_real_one():
    """A low can be set while the high is not; the half that exists is a level."""
    assert engine.session_extremes(23436.5, -1e18) == [("session low", 23436.5)]
    assert engine.session_extremes(1e18, 23475.0) == [("session high", 23475.0)]


def test_no_index_price_is_near_the_sentinel_bound():
    """The guard must not be able to eat a real price.

    SENSEX is the largest index this tool follows; the bound sits well above
    it, and the sentinels ten orders of magnitude above the bound.
    """
    assert engine.UNSET_EXTREME > 1_000_000        # far above any index
    assert engine.UNSET_EXTREME < 1e18             # far below the sentinels
    assert engine.session_extremes(75_000.0, 90_000.0) != []


def test_none_is_dropped_like_a_sentinel():
    """An extreme that was never written is absent, not zero."""
    assert engine.session_extremes(None, None) == []
    assert engine.session_extremes(None, 23475.0) == [("session high", 23475.0)]


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_"):
            _fn(); print("ok", _name)
