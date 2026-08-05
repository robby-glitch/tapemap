"""The broker must never change by accident.

Switching data source silently is the worst failure this wiring can have: the
tape would keep printing, the numbers would be real, and they would come from
somewhere nobody chose. So the default is asserted, and every spelling that is
not exactly "upstox" is asserted to stay on Dhan.
"""

import inspect
import os

import chain_live


def _with(value):
    """Run _broker() under a given TAPEMAP_BROKER, then restore."""
    had = "TAPEMAP_BROKER" in os.environ
    prev = os.environ.get("TAPEMAP_BROKER")
    try:
        if value is None:
            os.environ.pop("TAPEMAP_BROKER", None)
        else:
            os.environ["TAPEMAP_BROKER"] = value
        return chain_live._broker()
    finally:
        if had:
            os.environ["TAPEMAP_BROKER"] = prev
        else:
            os.environ.pop("TAPEMAP_BROKER", None)


def test_setting_nothing_keeps_dhan():
    """The behaviour that has been running stays the behaviour that runs."""
    assert _with(None) == "dhan"


def test_upstox_is_selected_explicitly():
    assert _with("upstox") == "upstox"
    assert _with("  UPSTOX  ") == "upstox"        # padded / shouted still counts


def test_a_misspelling_does_not_move_the_broker():
    """A typo must fail safe onto Dhan, never onto "some other source"."""
    for junk in ("upstoxx", "upstok", "", "  ", "kite", "dhan"):
        assert _with(junk) != "upstox", junk


def test_the_upstox_source_is_imported_only_when_chosen():
    """A Dhan-only run must not pay for -- or fail on -- the websocket
    dependency chain, so the import lives inside the helper, not at module
    scope."""
    assert "from upstox_chain import" in inspect.getsource(
        chain_live._upstox_source)
    assert "upstox" not in inspect.getsource(chain_live).split(
        "def _broker")[0], "chain_live must not import upstox at module scope"
