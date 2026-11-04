"""optflow/structures.py (the read's trade) and optflow/optladder.py: the pure pricing check, and the ladder's three states on
an empty record (conftest points every DIR at tmp, so a build here sees no chain and must say so, never a zero)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "optflow"))
import structures   # noqa: E402


def test_structures_price_the_reads_trade_and_gate_it():
    structures.demo()


def test_every_mapped_read_names_a_structure_the_catalog_explains():
    for said, (sel, buy, why) in structures.MAP.items():
        for name in (sel, buy):
            assert name is None or name in structures.EXPLAIN, (said, name)
        assert why


def test_ladder_without_a_chain_says_so(monkeypatch, tmp_path):
    import optladder as ladder
    monkeypatch.setattr(ladder, "D", str(tmp_path))
    d = ladder.build("2026-01-05", "NIFTY")
    assert d["ok"] is False and "dekh nahi paaye" in d["why"]
