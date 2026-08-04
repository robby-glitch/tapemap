"""trigger_log: append-once semantics, context capture, fail-soft contract."""

import json

import trigger_log


class FakeChain:
    def oi_flow(self, interval=15):
        return [{"call": 1_000_000, "put": 2_000_000, "strength": 0.5}]


class BrokenChain:
    def oi_flow(self, interval=15):
        raise RuntimeError("chain poller down")


def _payload(rot_t="10:03"):
    """The shape /api/data actually serves.

    The index OHLC is NESTED under `fut`; gamma/ctx sit beside it at the top
    level and are dicts, not strings. This fixture's first version invented a
    flat {"c": ...} bar, so the logger shipped reading bar["c"] and wrote 18
    live rows with px=null on 2026-08-04 — every one of them unscorable,
    because score() skips a row without a px. A fixture that invents its own
    schema tests the fixture, not the caller.

    The LAST bar is the one still FORMING on a live refresh, so the fixture
    carries one — and gives it its own rotation record, so the tests can prove
    a forming trigger is never written.
    """
    forming_t = "10:04"
    bars = [{"t": "10:00", "fut": {"c": 24600.0}},
            {"t": rot_t, "fut": {"c": 24610.0},
             "gamma": {"regime": "BALANCE"}, "ctx": {"verdict": "GO"}},
            {"t": forming_t, "fut": {"c": 24618.0}}]
    rot = [None, _rec(rot_t, "24610.00"), _rec(forming_t, "24618.00")]
    return {"days": [{"bars": bars, "rotation": rot}]}


def _rec(t, close):
    return {"t": t, "side": "BUY", "band": "d3",
            "trigger": f"index low 24590.00 <= d3 24595.00 and the same bar "
                       f"closed {close} back above it"}


def _fresh(tmp_path):
    trigger_log._seen = None            # new process, new file
    return str(tmp_path / "log.jsonl")


def test_logs_once_with_context(tmp_path):
    path = _fresh(tmp_path)
    assert trigger_log.log_new("NIFTY", _payload(), FakeChain(), path=path) == 1
    # the same payload again — the record is already on disk
    assert trigger_log.log_new("NIFTY", _payload(), FakeChain(), path=path) == 0
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert len(rows) == 1
    r = rows[0]
    assert r["side"] == "BUY" and r["band"] == "d3" and r["px"] == 24610.0
    assert r["gamma"]["regime"] == "BALANCE" and r["oi_strength"] == 0.5
    assert r["oi_call"] == 1_000_000 and r["oi_put"] == 2_000_000
    assert "f30" not in r               # outcomes are score()'s job, later


def test_dedupe_survives_restart(tmp_path):
    path = _fresh(tmp_path)
    trigger_log.log_new("NIFTY", _payload(), None, path=path)
    trigger_log._seen = None            # simulate a server restart
    assert trigger_log.log_new("NIFTY", _payload(), None, path=path) == 0


def test_broken_chain_still_logs(tmp_path):
    path = _fresh(tmp_path)
    assert trigger_log.log_new("NIFTY", _payload(), BrokenChain(), path=path) == 1
    row = json.loads(open(path, encoding="utf-8").read())
    assert row["oi_strength"] is None   # absent, never invented


def test_px_from_flat_bars(tmp_path):
    """The cached backtest bars are flat — both shapes must yield a px."""
    path = _fresh(tmp_path)
    p = _payload()
    for b in p["days"][0]["bars"]:          # collapse to the cache's shape
        b["c"] = b.pop("fut")["c"]
    assert trigger_log.log_new("NIFTY", p, None, path=path) == 1
    with open(path, encoding="utf-8") as f:
        assert json.loads(f.read())["px"] == 24610.0


def test_backfill_recovers_px_from_the_receipt(tmp_path):
    """A row logged without a px is repairable from its trigger sentence."""
    path = _fresh(tmp_path)
    trigger_log.log_new("NIFTY", _payload(), None, path=path)
    with open(path, encoding="utf-8") as f:
        row = json.loads(f.read())
    row["px"] = None                        # the 2026-08-04 rows as written
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")

    assert trigger_log.backfill(path) == 1
    with open(path, encoding="utf-8") as f:
        assert json.loads(f.read())["px"] == 24610.0
    assert trigger_log.backfill(path) == 0   # idempotent


def test_backfill_leaves_an_unparsable_receipt_alone(tmp_path):
    """No sentence to read -> px stays null. Never guess an entry price."""
    path = _fresh(tmp_path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"day": "2026-08-04", "index": "NIFTY", "t": "09:33",
                            "side": "BUY", "band": "d3", "px": None,
                            "trigger": "chain down, no receipt"}) + "\n")
    assert trigger_log.backfill(path) == 0
    with open(path, encoding="utf-8") as f:
        assert json.loads(f.read())["px"] is None


def test_forming_bar_is_never_logged(tmp_path):
    """The last bar is still open — its trigger can un-fire when it closes."""
    path = _fresh(tmp_path)
    assert trigger_log.log_new("NIFTY", _payload(), None, path=path) == 1
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert [r["t"] for r in rows] == ["10:03"]      # 10:04 was still forming
    assert rows[0]["closed_bar"] is True


def test_score_quarantines_forming_bar_rows(tmp_path):
    """Rows from before the fix carry no closed_bar key and are never scored."""
    path = _fresh(tmp_path)
    old = {"day": "2026-08-04", "index": "NIFTY", "t": "09:33", "side": "BUY",
           "band": "d3", "px": 24643.0, "trigger": "…closed 24643.00 back above it"}
    new = dict(old, t="09:44", closed_bar=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(old) + "\n" + json.dumps(new) + "\n")
    _changed, skipped = trigger_log.score(path)
    assert skipped == 1


def test_fail_soft_on_garbage(tmp_path):
    path = _fresh(tmp_path)
    assert trigger_log.log_new("NIFTY", b"not json at all", None, path=path) == 0
    assert trigger_log.log_new("NIFTY", {"days": []}, None, path=path) == 0
    assert trigger_log.log_new("NIFTY", None, None, path=path) == 0
