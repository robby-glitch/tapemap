"""The seam where a magnitude becomes a verdict.

The two that matter most: `test_a_pulled_row_never_counts_as_ignition` (a
cancellation reading as aggression would invert the very signal it is meant to
catch) and `test_drain_is_never_invented_from_book_data` (manufacturing the
third condition out of the two you can see is the exact 2/3-plus-impatience
failure the sequence rule exists to prevent).
"""
import fuse
import regime


def _sweep(qty, side="buy", t="10:00", kind="swept", inst="FUT"):
    return {"det": "sweep", "kind": kind, "qty": qty, "side": side,
            "t": t, "inst": inst, "levels": 3}


# Deliberately NOT monotonic. A rising series scores every new value at the
# 100th percentile, which is a property of percentile-so-far and not of the
# market; warming up with one would make ignition look permanently lit and
# hide exactly the staleness bug these tests exist to catch.
SPREAD = [90, 140, 70, 160, 110, 55, 175, 100, 130, 65, 150, 85]


def _warm(f, n=12, qty=100):
    """Enough varied small sweeps that percentiles mean something."""
    for i in range(n):
        f.on_rows([_sweep(SPREAD[i % len(SPREAD)], t=f"09:{i:02d}")])
    return f


# --------------------------------------------------------------------------
# ranking
# --------------------------------------------------------------------------

def test_a_big_sweep_against_a_quiet_session_is_ignition():
    f = _warm(fuse.Fuse())
    ev = f.on_rows([_sweep(100_000, t="10:30")])
    assert ev.ignition and ev.ign_rank >= fuse.IGN_P and ev.ign_at == "10:30"


def test_the_same_size_is_not_ignition_in_a_session_full_of_them():
    """975 lots is enormous on the future and unremarkable on an ATM call.
    Only the instrument's own session can say which, which is the whole reason
    nothing here uses an absolute."""
    f = fuse.Fuse()
    for i in range(20):
        f.on_rows([_sweep(100_000 + SPREAD[i % len(SPREAD)], t=f"09:{i:02d}")])
    assert not f.on_rows([_sweep(100_000, t="10:30")]).ignition


def test_ranks_are_not_trusted_before_there_is_a_session_to_rank_against():
    f = fuse.Fuse()
    ev = f.on_rows([_sweep(100_000)])
    assert not ev.warm and not ev.ignition
    assert any("not trusted" in n for n in ev.notes)


def test_a_pulled_row_never_counts_as_ignition():
    """A pull is liquidity LEAVING -- the opposite reading. Ranking it beside
    consumed sweeps would let cancellations masquerade as aggression."""
    f = _warm(fuse.Fuse())
    ev = f.on_rows([_sweep(100_000, t="10:30", kind="pulled")])
    assert not ev.ignition
    assert len(f._sweep_rank) == 12          # the pulled row was not ranked


# --------------------------------------------------------------------------
# what it refuses to make up
# --------------------------------------------------------------------------

def test_drain_is_never_invented_from_book_data():
    """OI is not in the book. Without drain the gate must not reach CASCADE,
    however loud the ignition."""
    f = _warm(fuse.Fuse())
    f.on_rows([_sweep(100_000, t="10:30")])
    assert f.ev.ignition
    assert f.verdict().gear != regime.CASCADE
    assert f.verdict(drain=True).gear == regime.CASCADE


def test_ignition_without_drain_still_says_fakes_die_here():
    f = _warm(fuse.Fuse())
    f.on_rows([_sweep(100_000, t="10:30")])
    v = f.verdict(vwap_flips_per_hr=12, walls_holding=True)
    assert any("fakes die here" in w for w in v.why)


# --------------------------------------------------------------------------
# one-sidedness is a book reading, and is overridable
# --------------------------------------------------------------------------

def test_lopsided_sweeps_read_as_one_sided_book_flow():
    f = fuse.Fuse()
    for i in range(10):
        f.on_rows([_sweep(100, side="buy", t=f"09:{i:02d}")])
    assert f.ev.one_sided_book is True


def test_a_balanced_book_is_not_one_sided():
    f = fuse.Fuse()
    for i in range(10):
        f.on_rows([_sweep(100, side="buy" if i % 2 else "sell", t=f"09:{i:02d}")])
    assert f.ev.one_sided_book is False


def test_the_caller_can_override_with_the_chains_own_one_sidedness():
    """Book flow and chain positioning can disagree; the caller picks which it
    means rather than this module conflating them."""
    f = fuse.Fuse()
    for i in range(10):
        f.on_rows([_sweep(100, side="buy", t=f"09:{i:02d}")])
    v = f.verdict(sigma_pctl=0.2, fuel_rank=0.9, one_sided=False)
    assert v.gear != regime.TRANSITION


def test_compressed_sigma_plus_supplied_fuel_reaches_transition():
    f = fuse.Fuse()
    for i in range(10):
        f.on_rows([_sweep(100, side="buy", t=f"09:{i:02d}")])
    v = f.verdict(sigma_pctl=0.2, fuel_rank=0.9, setups=["S2", "S3", "S5"])
    assert v.gear == regime.TRANSITION and v.would_block == ["S2", "S3"]


# --------------------------------------------------------------------------
# per-instrument isolation
# --------------------------------------------------------------------------

def test_one_instruments_ranks_never_pollute_anothers():
    """A future's sweep sizes and an option's are different distributions.
    Sharing a Rank would make every option sweep look enormous."""
    b = fuse.Book()
    for i in range(12):
        b.on_rows([_sweep(1_000_000 + i, t=f"09:{i:02d}", inst="FUT")])
    ev = b.on_rows([_sweep(100, t="10:00", inst="24150CE")])["24150CE"]
    assert not ev.ignition and not ev.warm      # its own session is still empty
    assert len(b.for_inst("FUT")._sweep_rank) == 12
    assert len(b.for_inst("24150CE")._sweep_rank) == 1


def test_a_mixed_batch_is_routed_by_instrument():
    b = fuse.Book()
    out = b.on_rows([_sweep(100, inst="FUT"), _sweep(200, inst="24150PE")])
    assert set(out) == {"FUT", "24150PE"}


def test_the_window_forgets_old_rows():
    f = _warm(fuse.Fuse(), n=fuse.WINDOW * 3)
    assert f.ev.sweeps <= fuse.WINDOW


def test_the_verdict_stays_tagged_inferred():
    assert _warm(fuse.Fuse()).verdict().tag == "I"


def test_ignition_does_not_keep_re_firing_while_the_row_stays_in_view():
    """One big sweep must light ignition ONCE. Holding the flag up for every
    frame it lingers in the window would turn a moment into a state -- and the
    gate is what decides whether that moment is still armed, confirmed by
    drain, not this module by repetition."""
    f = _warm(fuse.Fuse())
    assert f.on_rows([_sweep(100_000, t="10:30")]).ignition
    assert not f.on_rows([_sweep(80, t="10:31")]).ignition
    assert not f.on_rows([_sweep(75, t="10:32")]).ignition


def test_a_percentile_so_far_scores_every_new_maximum_at_one():
    """Why the fixtures above are not monotonic: this is a property of the
    statistic, not of the market, and building a test on it would prove
    nothing about the detector."""
    r = fuse.Rank()
    for x in range(1, 30):
        last = r.rank(x * 10)
    assert last == 1.0


# --------------------------------------------------------------------------
# one-sidedness weighted by size, not by row count
# --------------------------------------------------------------------------

def test_a_row_that_contradicts_itself_no_longer_votes_at_full_strength():
    """`side` is [I]: it is whichever ladder lost MORE, so a two-sided collapse
    yields a row whose side is close to a coin flip. Counting rows let three
    such rows read as a decisively one-sided book. Weighting by the size that
    actually vanished -- including the losing side's `opp_qty` -- lets a
    self-contradicting row count for less."""
    b = fuse.Fuse()
    rows = [dict(_sweep(1000, "buy"), opp_qty=950.0) for _ in range(3)]
    ev = b.on_rows(rows)
    assert ev.sweeps == 3 and ev.buys == 3     # every row says "buy"
    # ... but half the size that vanished was on the other side
    assert ev.one_sided_qty is not None and ev.one_sided_qty < fuse.ONE_SIDED
    assert ev.one_sided_book is False


def test_a_genuinely_one_sided_book_still_reads_one_sided():
    b = fuse.Fuse()
    ev = b.on_rows([dict(_sweep(1000, "buy"), opp_qty=0.0) for _ in range(3)])
    assert ev.one_sided_qty == 1.0 and ev.one_sided_book is True


def test_rows_written_before_opp_qty_existed_keep_the_old_reading():
    """A forward log cannot be rewritten, so old rows must not change meaning.
    Absent `opp_qty` defaults to 0.0, which is exactly the old behaviour."""
    b = fuse.Fuse()
    ev = b.on_rows([_sweep(1000, "buy") for _ in range(3)])   # no opp_qty key
    assert ev.one_sided_book is True


def test_the_share_is_published_not_just_the_verdict():
    """0.51 and 0.99 both clear or fail one threshold; a reader must be able to
    tell a knife-edge from a landslide."""
    b = fuse.Fuse()
    ev = b.on_rows([dict(_sweep(1000, "buy"), opp_qty=0.0),
                    dict(_sweep(1000, "sell"), opp_qty=0.0)])
    assert ev.one_sided_qty == 0.5 and ev.one_sided_book is False
