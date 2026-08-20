"""Fuel and drain out of the chain -- the half the order book cannot see.

The shape being reproduced is Aug-19's: CE writers build a wall, the premium
rises against them, they end up underwater, and eventually they cover. Fuel
must appear while they are trapped; drain must appear when they leave; and
neither may be claimed before there is enough session to rank against.
"""
import chainside


def _snap(strikes):
    """[(strike, ce_oi, ce_ltp, pe_strike_oi, pe_ltp), ...] -> a snapshot."""
    return [{"k": k, "ce": {"oi": co, "ltp": cl}, "pe": {"oi": po, "ltp": pl}}
            for k, co, cl, po, pl in strikes]


def _build(cs, n=10, oi=1_000_000, ltp=100.0, step=100_000):
    """Writers piling into 24100CE while the premium sits still."""
    for i in range(n):
        cs.on_snapshot(f"09:{i:02d}",
                       _snap([(24100, oi + i * step, ltp, 500_000, 80.0)]))
    return cs


# --------------------------------------------------------------------------
# fuel
# --------------------------------------------------------------------------

def test_writers_underwater_show_up_as_pain():
    """OI built around 100, premium now 130: the short side is ~30 points
    underwater and that is the fuel."""
    cs = chainside.ChainSide()
    _build(cs)
    r = cs.on_snapshot("10:00", _snap([(24100, 2_000_000, 130.0, 500_000, 80.0)]))
    assert r.worst_pain and r.worst_pain > 20
    assert r.worst_leg == "24100CE" and r.trapped_side == "ce"


def test_pain_on_one_side_reads_as_a_lopsided_chain():
    cs = chainside.ChainSide()
    _build(cs)
    r = cs.on_snapshot("10:00", _snap([(24100, 2_000_000, 130.0, 500_000, 80.0)]))
    assert r.one_sided is True and r.trapped_side == "ce"


def test_fuel_is_ranked_against_this_sessions_own_pain():
    """'30 points underwater' means nothing until you know whether the session
    has seen 2 or 200."""
    cs = chainside.ChainSide()
    _build(cs)
    r = cs.on_snapshot("10:00", _snap([(24100, 2_000_000, 300.0, 500_000, 80.0)]))
    assert r.warm and r.fuel_rank is not None and r.fuel_rank >= 0.9


def test_nothing_is_claimed_before_there_is_a_session_to_rank_against():
    cs = chainside.ChainSide()
    r = cs.on_snapshot("09:16", _snap([(24100, 1_000_000, 100.0, 500_000, 80.0)]))
    assert not r.warm and r.fuel_rank is None and not r.drain
    assert any("not trusted" in n for n in r.notes)


# --------------------------------------------------------------------------
# drain
# --------------------------------------------------------------------------

def test_covering_while_underwater_registers_as_forced_exit_flow():
    """OI collapsing on a leg whose writers are in pain is forced exit -- the
    third condition, and the one the book alone can never supply."""
    cs = chainside.ChainSide()
    _build(cs, n=12)
    r = None
    for i, oi in enumerate((1_900_000, 1_500_000, 900_000, 400_000)):
        r = cs.on_snapshot(f"10:{i:02d}",
                           _snap([(24100, oi, 130.0, 500_000, 80.0)]))
    assert r.drain_rank is not None and r.drain_rank > 0


def test_a_quiet_chain_does_not_drain():
    cs = chainside.ChainSide()
    _build(cs, n=12)
    r = cs.on_snapshot("10:00", _snap([(24100, 2_100_000, 100.0, 500_000, 80.0)]))
    assert not r.drain


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------

def test_a_missing_chain_is_unknown_not_calm():
    """A chain that stopped arriving must not look like a chain reporting
    calm -- the rule upstox_feed.age() enforces one layer down."""
    cs = chainside.ChainSide()
    _build(cs, n=12)
    r = cs.on_snapshot("10:00", None)
    assert r.fuel_rank is None and not r.drain
    assert any("unknown" in n for n in r.notes)
    assert cs.on_snapshot("10:01", []).fuel_rank is None


def test_legs_with_no_price_or_no_oi_are_skipped_not_zeroed():
    cs = chainside.ChainSide()
    r = cs.on_snapshot("09:16", [{"k": 24100, "ce": {"oi": None, "ltp": 100.0},
                                  "pe": {"oi": 500_000, "ltp": None}}])
    assert r.worst_pain is None


def test_the_reading_stays_tagged_inferred():
    """The ledger assumes writer-dominated builds. Passing that through one
    more function does not turn it into a measurement."""
    cs = chainside.ChainSide()
    r = _build(cs, n=9).on_snapshot(
        "10:00", _snap([(24100, 2_000_000, 130.0, 500_000, 80.0)]))
    assert r.tag == "I"
    assert any("[I:" in n for n in r.notes)


# --------------------------------------------------------------------------
# per-index isolation
# --------------------------------------------------------------------------

def test_one_indexs_pain_never_ranks_against_anothers():
    c = chainside.Chains()
    for i in range(12):
        c.on_snapshot("NIFTY", f"09:{i:02d}",
                      _snap([(24100, 1_000_000 + i * 100_000, 100.0,
                              500_000, 80.0)]))
    r = c.on_snapshot("SENSEX", "10:00",
                      _snap([(77400, 100_000, 200.0, 90_000, 150.0)]))
    assert not r.warm                      # its own session is still empty
    assert c.for_index("NIFTY").read.warm
