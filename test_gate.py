# tapemap/test_gate.py
"""The seller's gate, ported from ui/toolb.js:826 with the P0 fixed: a hole
WINS. The old gate initialised to TRADE and holes never downgraded it, so it
said GO in green at 09:20 with IV/RV, VPIN and expiry all unknown."""
import gate


def test_a_hole_wins_and_reads_grey():
    g = gate.state(ivrv=None, expiry_iso="2026-09-15", today_iso="2026-09-15", vpin_pct=0.2, squeeze=False)
    assert g["level"] == "PATA NAHI" and any("IV vs RV" in h for h in g["holes"])


def test_the_calendar_hole_is_permanent_and_named():
    g = gate.state(ivrv=1.3, expiry_iso="2026-09-15", today_iso="2026-09-15", vpin_pct=0.2, squeeze=False)
    assert g["level"] == "PATA NAHI" and g["holes"] == ["event calendar not wired"]
    assert g["would_be"] == "HALF SIZE" and "expiry" in g["would_be_reason"]


def test_worst_reason_leads():
    g = gate.state(ivrv=0.9, expiry_iso="2026-09-15", today_iso="2026-09-15", vpin_pct=0.9, squeeze=False)
    assert g["would_be"] == "NO NEW RISK" and g["would_be_reason"] in ("vol cheap", "VPIN burst")
