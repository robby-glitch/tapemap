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
    # `rotation_run` since 2026-08-08. The logger deliberately no longer reads
    # `rotation` -- that is §1's one-candle rule, which marks the d3 TOUCH and
    # is VOID; see the test below that pins the refusal.
    return {"days": [{"bars": bars, "rotation_run": rot}]}


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
    new = dict(old, t="09:44", closed_bar=True, rule="5c")
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(old) + "\n" + json.dumps(new) + "\n")
    _changed, skipped = trigger_log.score(path)
    assert skipped == 1


def test_fail_soft_on_garbage(tmp_path):
    path = _fresh(tmp_path)
    assert trigger_log.log_new("NIFTY", b"not json at all", None, path=path) == 0
    assert trigger_log.log_new("NIFTY", {"days": []}, None, path=path) == 0
    assert trigger_log.log_new("NIFTY", None, None, path=path) == 0



# ── 2026-08-08: the logger follows the rule the CHART draws ────────────────

def test_the_old_one_candle_layer_is_not_logged(tmp_path):
    """`rotation` marks the d3 TOUCH, not the entry, and research-findings
    marks it VOID. Logging it produced rows describing a different BAR from
    the one the tool draws -- silently, 2026-08-04 to 2026-08-08. The refusal
    is pinned here so nobody "fixes" the logger back."""
    path = _fresh(tmp_path)
    full = _payload()
    old_only = {"days": [{"bars": full["days"][0]["bars"],
                          "rotation": full["days"][0]["rotation_run"]}]}
    assert trigger_log.log_new("NIFTY", old_only, None, path=path) == 0


def test_sell_records_are_logged_too(tmp_path):
    """Monday's forward score covers BOTH sides. A logger that silently
    captured only buys would have been found out weeks later."""
    path = _fresh(tmp_path)
    full = _payload()
    bars = full["days"][0]["bars"]
    sell = [None] * len(bars)
    sell[1] = dict(_rec("10:03", "24610.00"), side="SELL", band="u3")
    payload = {"days": [{"bars": bars, "rotation_run": [None] * len(bars),
                         "rotation_run_sell": sell}]}
    assert trigger_log.log_new("NIFTY", payload, None, path=path) == 1
    row = json.loads(open(path).read().strip())
    assert row["side"] == "SELL" and row["band"] == "u3"
    assert row["rule"] == "5c"


def test_a_buy_wins_the_slot_when_both_sides_land_on_one_bar(tmp_path):
    """The same tie-break the chart's draw uses, so the log and the screen can
    never disagree about which record existed on a bar."""
    path = _fresh(tmp_path)
    full = _payload()
    bars = full["days"][0]["bars"]
    buy = full["days"][0]["rotation_run"]
    sell = [None] * len(bars)
    sell[1] = dict(_rec("10:03", "24610.00"), side="SELL", band="u3")
    payload = {"days": [{"bars": bars, "rotation_run": buy,
                         "rotation_run_sell": sell}]}
    assert trigger_log.log_new("NIFTY", payload, None, path=path) == 1
    assert json.loads(open(path).read().strip())["side"] == "BUY"


def test_score_quarantines_rows_from_the_old_rule(tmp_path):
    """The rows already on disk predate the fix and describe the touch, not
    the entry. Skipped, not deleted -- their gamma/ctx context is still real,
    only the rule they belong to is not the one being scored."""
    path = _fresh(tmp_path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"day": "2026-08-04", "index": "NIFTY",
                            "t": "10:03", "side": "BUY", "band": "d3",
                            "px": 24610.0, "closed_bar": True}) + "\n")
    trigger_log.score(path=path)
    # The row must come back UNSCORED -- no outcome written onto it.
    row = json.loads(open(path).read().strip())
    assert row.get("f15") is None and row.get("f30") is None


# ── read(): the one parse /api/signals shares with the CLI ─────────────────

def test_read_returns_rows_and_counts_the_lines_it_could_not_parse(tmp_path):
    """A truncated tail must not hide the rows above it -- nor vanish."""
    path = _fresh(tmp_path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"day": "2026-08-10", "rule": "5c"}) + "\n")
        f.write("\n")                      # blank lines are not rows
        f.write('{"day": "2026-08-10", "rul')   # a write cut off by a kill
    rows, bad = trigger_log.read(path)
    assert [r["rule"] for r in rows] == ["5c"]
    assert bad == 1


def test_read_raises_rather_than_reporting_a_missing_log_as_an_empty_one(tmp_path):
    """"The log is missing" and "the log is empty" are opposite facts. A
    reader that cannot tell them apart renders one as the other."""
    import pytest
    with pytest.raises(OSError):
        trigger_log.read(tmp_path / "not-a-log.jsonl")


# ── 2026-08-12, Phase 0: the setup ARMING, at the scored interval ──────────
#
# An arm is not a trade. These pin the four ways an arm row could quietly stop
# being true: written twice, collapsing a re-arm, guessing a minute, or being
# mistaken for an entry.

import band_rotation                                       # noqa: E402
from contract_bars import IST                              # noqa: E402,F401

D3 = 24595.0


def _one(t, low, high=None, close=None):
    """One 1-MINUTE composite index bar in /api/data's shape."""
    high = high if high is not None else low + 10.0
    close = close if close is not None else low + 5.0
    return {"t": t, "fut": {"o": low + 2.0, "h": high, "l": low, "c": close,
                            "v": 100.0, "vwap": 24700.0, "d3": D3,
                            "u3": 24800.0}}


def _three(t, low, high=None, close=None, **extra):
    """One 3-MINUTE bar, same shape, plus any row-level reads."""
    bar = _one(t, low, high, close)
    bar.update(extra)
    return bar


def _arm_payload(bars3, ones=None, interval=3):
    """A payload carrying run_state exactly as live.derive_payload builds it.

    The state list comes from `band_rotation.run_states` itself rather than
    being hand-written: a fixture that invents its own state rows tests the
    fixture. The last bar is the FORMING one, as on a live refresh.
    """
    states = band_rotation.run_states(
        bars3, stop_pts=band_rotation.OPERATOR_STOP_PTS)
    sell = band_rotation.run_states(
        bars3, stop_pts=band_rotation.OPERATOR_STOP_PTS, side="SELL")
    return {"interval": interval,
            "days": [{"bars": bars3,
                      "run_state": states, "run_state_sell": sell,
                      "rotation_run": [s["entry"] for s in states],
                      "rotation_run_sell": [s["entry"] for s in sell]}]}, ones


# 09:27 touches d3; 09:30 and 09:33 sit above it; 09:36 is the forming bar.
def _armed_session():
    return [_three("09:24", 24700.0),                     # before the gate
            _three("09:27", D3, high=24620.0,
                   gamma={"regime": "BALANCE"}, ctx={"verdict": "GO"}),
            _three("09:30", 24610.0),
            _three("09:33", 24612.0),
            _three("09:36", 24614.0)]                     # forming


def _armed_minutes():
    """The nine minutes behind those three-minute bars.

    09:28 is the minute that actually made the low — NOT the bucket's first
    minute, so a t_1m that merely echoed the bucket label would fail here.
    """
    return [_one("09:24", 24702.0), _one("09:25", 24701.0), _one("09:26", 24700.0),
            _one("09:27", 24600.0), _one("09:28", D3), _one("09:29", 24598.0),
            _one("09:30", 24612.0), _one("09:31", 24610.0), _one("09:32", 24611.0),
            _one("09:33", 24614.0), _one("09:34", 24612.0), _one("09:35", 24613.0)]


def _arms(path):
    return [r for r in (json.loads(x) for x in open(path, encoding="utf-8"))
            if r.get("kind") == "arm"]


def test_an_arm_is_written_once_and_never_re_appended(tmp_path):
    """The refresh thread runs repeatedly over a GROWING session. Without the
    de-dup every arm the day ever produced would land again each cycle."""
    path = _fresh(tmp_path)
    pl, ones = _arm_payload(_armed_session(), _armed_minutes())
    assert trigger_log.log_new("NIFTY", pl, None, ones=ones, path=path) == 1
    for _ in range(3):                      # three more refresh cycles
        assert trigger_log.log_new("NIFTY", pl, None, ones=ones, path=path) == 0
    arms = _arms(path)
    assert len(arms) == 1
    a = arms[0]
    assert a["side"] == "BUY" and a["band"] == "d3" and a["interval"] == 3
    assert a["t"] == "09:27" and a["rearm"] is False
    assert a["level"] == D3 and a["extreme"] == D3
    # The line to beat, under its TRUE name. A low must never arrive as a high.
    assert a["ref_high"] == 24620.0 and "ref_low" not in a
    assert a["gamma"]["regime"] == "BALANCE" and a["ctx"]["verdict"] == "GO"
    assert "px" not in a and "f15" not in a and "f30" not in a


def test_an_arm_survives_a_restart_without_being_re_appended(tmp_path):
    path = _fresh(tmp_path)
    pl, ones = _arm_payload(_armed_session(), _armed_minutes())
    trigger_log.log_new("NIFTY", pl, None, ones=ones, path=path)
    trigger_log._seen = None                # simulate a server restart
    assert trigger_log.log_new("NIFTY", pl, None, ones=ones, path=path) == 0


def test_t_1m_lands_on_the_minute_that_made_the_low(tmp_path):
    """09:28 holds the low inside the 09:27 bucket — not 09:27, its label."""
    path = _fresh(tmp_path)
    pl, ones = _arm_payload(_armed_session(), _armed_minutes())
    trigger_log.log_new("NIFTY", pl, None, ones=ones, path=path)
    a = _arms(path)[0]
    assert a["t_1m"] == "09:28" and a["extreme_1m"] == D3
    assert a["t_1m_why"] is None


def test_no_1m_series_yields_a_null_minute_and_a_reason_not_a_guess(tmp_path):
    path = _fresh(tmp_path)
    pl, _ = _arm_payload(_armed_session(), None)
    trigger_log.log_new("NIFTY", pl, None, ones=None, path=path)
    a = _arms(path)[0]
    assert a["t_1m"] is None and a["extreme_1m"] is None
    assert "no 1-minute series" in a["t_1m_why"]
    # The arm itself is untouched: 1-minute supplies timing and nothing else.
    assert a["t"] == "09:27" and a["extreme"] == D3


def test_a_1m_series_that_disagrees_is_refused_rather_than_published(tmp_path):
    """The 3-minute bar IS an aggregation of those minutes. If the minute's
    low does not match it, they are not the same session — so no minute."""
    path = _fresh(tmp_path)
    ones = _armed_minutes()
    for b in ones:                          # a different session entirely
        b["fut"]["l"] += 40.0
    pl, _ = _arm_payload(_armed_session(), ones)
    trigger_log.log_new("NIFTY", pl, None, ones=ones, path=path)
    a = _arms(path)[0]
    assert a["t_1m"] is None and "do not match" not in (a["t_1m_why"] or "")
    assert "does not match" in a["t_1m_why"]


def test_a_re_arm_is_its_own_row_flagged_and_pointed_at_the_first_arm(tmp_path):
    """§5c: a later candle printing a new lower low BECOMES the reference.
    Falling lows are ONE setup — lossless rows, counted by `rearm: false`."""
    path = _fresh(tmp_path)
    bars = [_three("09:24", 24700.0),
            _three("09:27", D3, high=24620.0),          # arm
            _three("09:30", 24580.0, high=24600.0),     # new lower low: RE-ARM
            _three("09:33", 24585.0),
            _three("09:36", 24590.0)]                   # forming
    pl, _ = _arm_payload(bars, None)
    assert trigger_log.log_new("NIFTY", pl, None, path=path) == 2
    a, b = _arms(path)
    assert (a["t"], a["rearm"], a["first_t"]) == ("09:27", False, "09:27")
    assert (b["t"], b["rearm"], b["first_t"]) == ("09:30", True, "09:27")
    assert b["extreme"] == 24580.0 and b["ref_high"] == 24600.0
    # ONE setup, two rows.
    assert sum(1 for r in (a, b) if not r["rearm"]) == 1


def test_a_sell_arm_is_logged_with_its_own_band_and_true_field_name(tmp_path):
    """Operator decision: log BOTH sides' arms. A sell's line to beat is a
    LOW, and it must arrive under `ref_low`."""
    path = _fresh(tmp_path)
    bars = [_three("09:24", 24700.0),
            _three("09:27", 24790.0, high=24800.0, close=24795.0),   # tags u3
            _three("09:30", 24700.0),
            _three("09:33", 24705.0)]                                # forming
    pl, _ = _arm_payload(bars, None)
    trigger_log.log_new("NIFTY", pl, None, path=path)
    sells = [r for r in _arms(path) if r["side"] == "SELL"]
    assert len(sells) == 1
    s = sells[0]
    assert s["band"] == "u3" and s["ref_low"] == 24790.0 and "ref_high" not in s
    assert s["extreme"] == 24800.0 and s["level"] == 24800.0


def test_the_forming_bar_never_arms_the_log(tmp_path):
    """The reference's HIGH is the line the entry must beat, and it is not
    final until the bar closes — nor is d3, which still moves with volume."""
    path = _fresh(tmp_path)
    bars = [_three("09:24", 24700.0), _three("09:27", D3, high=24620.0)]
    pl, _ = _arm_payload(bars, None)
    assert trigger_log.log_new("NIFTY", pl, None, path=path) == 0


def test_an_arm_is_refused_at_any_interval_but_the_scored_one(tmp_path):
    """Operator decision, binding: 3-minute is canonical. A 1-minute arm is a
    different setup carrying no measured number, so it is not logged at all."""
    path = _fresh(tmp_path)
    pl, ones = _arm_payload(_armed_session(), _armed_minutes(), interval=1)
    assert trigger_log.log_new("NIFTY", pl, None, ones=ones, path=path) == 0
    # And a payload that does not NAME its interval cannot be taken to be 3.
    pl.pop("interval")
    assert trigger_log.log_new("NIFTY", pl, None, ones=ones, path=path) == 0


def test_an_arm_bug_can_never_cost_an_entry_row(tmp_path):
    """The entries are the scored population; the arms are measurement being
    started. A state list of garbage must lose the arm, not the entry."""
    path = _fresh(tmp_path)
    full = _payload()
    full["interval"] = 3
    full["days"][0]["run_state"] = "not a list of states"
    assert trigger_log.log_new("NIFTY", full, None, path=path) == 1
    assert _arms(path) == []


def test_an_absent_kind_still_reads_as_an_entry(tmp_path):
    """Every row written before 2026-08-12 has no `kind`. Absent means entry,
    and no historical row is rewritten to say so."""
    path = _fresh(tmp_path)
    trigger_log.log_new("NIFTY", _payload(), None, path=path)
    row = json.loads(open(path, encoding="utf-8").read().strip())
    assert "kind" not in row
    assert row["px"] == 24610.0                   # an entry, with its price
    rows, _bad = trigger_log.read(path)
    assert [r for r in rows if r.get("kind") != "arm"] == rows


def test_an_arm_never_gets_an_entry_price_or_a_forward_move(tmp_path):
    """`f15`/`f30` are the move FROM AN ENTRY, and an arm entered nothing.

    `score` DOES now give an arm an outcome -- the operator asked for one,
    measured from the arm candle's own close -- but it must never hand it the
    two fields that only mean something for a trade that was taken, and
    `backfill` must never report it as damaged.
    """
    path = _fresh(tmp_path)
    pl, ones = _arm_payload(_armed_session(), _armed_minutes())
    trigger_log.log_new("NIFTY", pl, None, ones=ones, path=path)
    _, skipped = trigger_log.score(path)
    assert skipped == 0
    assert trigger_log.backfill(path) == 0
    a = _arms(path)[0]
    assert "f15" not in a and "f30" not in a and "px" not in a


# ── The OUTCOME scorer (2026-08-12) ────────────────────────────────────────
#
# The operator's own spec, verbatim: *"check that after it generates any
# signals what the max market moves from price and did it touch the other side
# +-2 std +-3 std and beyond. because i try to hold the trade if oi is heavy on
# that side."*
#
# The fixtures below are FLAT banded bars -- the shape `squeeze_score.load`
# returns, which is what `score` reads -- and are handed to the scorer through
# `_load_sessions`, the one seam between this module and data/backtest/. No
# test here writes into that cache, and none of them cuts a new hypothesis out
# of it: research-findings §5 closed it to that, and filling a pre-registered
# row's outcome is the other route it names.

DAY, IDX = "2026-08-10", "NIFTY"


def _banded(t, o, h, l, c, vwap, sig):
    """One 3-minute bar with the six band keys, as the cache carries them."""
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "v": 1000.0, "oi": None,
            "vwap": vwap,
            "u1": vwap + sig, "u2": vwap + 2 * sig, "u3": vwap + 3 * sig,
            "d1": vwap - sig, "d2": vwap - 2 * sig, "d3": vwap - 3 * sig}


def _cached(monkeypatch, bars, index=IDX, day=DAY):
    monkeypatch.setattr(trigger_log, "_load_sessions",
                        lambda idx: {day: {"bars": bars}} if idx == index else {})


def _entry(t="09:30", side="BUY", band="d3", px=100.0, level=70.0, **extra):
    row = {"at": 1.0, "day": DAY, "index": IDX, "t": t, "side": side,
           "band": band, "rule": "5c", "px": px, "level": level,
           "closed_bar": True}
    row.update(extra)
    return row


def _write(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def _scored(tmp_path, monkeypatch, bars, rows):
    path = _fresh(tmp_path)
    _cached(monkeypatch, bars)
    trigger_log.score(_write(path, rows))
    return [json.loads(x) for x in open(path, encoding="utf-8")]


def test_mfe_and_mae_are_the_extremes_after_the_anchor_bar(tmp_path, monkeypatch):
    """The furthest favourable and adverse moves, with the clock of each.

    The ANCHOR BAR'S OWN high and low are excluded: the anchor is that bar's
    CLOSE, so its wicks were printed before the position existed and crediting
    them would report a move the row could not have been in. Anything at or
    after 15:15 is excluded too -- the operator is flat by then.
    """
    bars = [_banded("09:30", 100, 200, 0, 100, 100, 10),      # the anchor bar
            _banded("09:33", 100, 110, 95, 105, 100, 10),
            _banded("09:36", 105, 130, 90, 120, 100, 10),
            _banded("15:15", 120, 999, 120, 999, 100, 10)]    # after the flat
    r = _scored(tmp_path, monkeypatch, bars, [_entry()])[0]
    assert (r["mfe"], r["mfe_t"]) == (30.0, "09:36")
    assert (r["mae"], r["mae_t"]) == (-10.0, "09:36")
    assert r["anchor"] == "entry_close" and r["anchor_px"] == 100.0
    assert r["scored_from"] == "09:33" and r["scored_to"] == "15:15"
    assert "unscored" not in r


def test_the_sell_side_signs_mirror_the_buy_side(tmp_path, monkeypatch):
    """Signs are side-aware, exactly as f15/f30 already are: positive is a move
    in the row's own favour on a SELL as much as on a BUY."""
    bars = [_banded("09:30", 100, 100, 100, 100, 100, 10),
            _banded("09:33", 100, 105, 80, 85, 100, 10),
            _banded("09:36", 85, 160, 85, 150, 100, 10)]
    r = _scored(tmp_path, monkeypatch, bars,
                [_entry(side="SELL", band="u3", level=130.0)])[0]
    assert (r["mfe"], r["mfe_t"]) == (20.0, "09:33")     # DOWN is favourable
    assert (r["mae"], r["mae_t"]) == (-60.0, "09:36")
    assert r["bands"]["side"] == "d"                    # the mirror side


def test_a_stop_is_recorded_and_does_not_end_the_measurement(tmp_path, monkeypatch):
    """*"i try to hold the trade if oi is heavy on that side."*

    "Stopped out" and "would have worked" are two separate facts and the
    operator wants both. A scorer that stopped measuring at the stop could not
    tell a trade that was wrong from one that was early.
    """
    bars = [_banded("09:30", 100, 100, 100, 100, 100, 10),
            _banded("09:33", 100, 100, 40, 60, 100, 10),      # through the stop
            _banded("09:36", 60, 200, 60, 190, 100, 10)]      # then it runs
    r = _scored(tmp_path, monkeypatch, bars, [_entry()])[0]
    assert r["stop_hit"] is True and r["stop_t"] == "09:33"
    assert r["stop_px"] == band_rotation._stop_px(
        70.0, band_rotation.OPERATOR_STOP_PTS, False)
    assert (r["mfe"], r["mfe_t"]) == (100.0, "09:36")         # kept measuring


def test_a_row_with_no_placeable_stop_says_so_rather_than_holding(tmp_path, monkeypatch):
    """No level and no receipt to recover one from: whether the stop broke is
    UNKNOWN, which is not the same claim as "it held"."""
    bars = [_banded("09:30", 100, 100, 100, 100, 100, 10),
            _banded("09:33", 100, 110, 90, 105, 100, 10)]
    row = _entry()
    del row["level"]
    r = _scored(tmp_path, monkeypatch, bars, [row])[0]
    assert r["stop_hit"] is None and r["stop_px"] is None
    assert "unknown whether it broke" in r["stop_why"]


def test_a_missing_level_is_recovered_from_the_receipt_and_said_so(tmp_path, monkeypatch):
    """Rows logged before 2026-08-12 carry no `level`. The detector's own
    receipt does, exactly -- and the row records WHICH of the two placed its
    stop, because they are not the same provenance."""
    bars = [_banded("09:30", 100, 100, 100, 100, 100, 10),
            _banded("09:33", 100, 110, 45, 105, 100, 10)]
    row = _entry(trigger="index low touched d3 70.00 at 09:27, then closed "
                         "100.00 above that candle's high 99.00 1 bar later")
    del row["level"]
    r = _scored(tmp_path, monkeypatch, bars, [row])[0]
    assert r["stop_from"] == "trigger receipt" and r["stop_px"] == 50.0
    assert r["stop_hit"] is True


def test_a_receipt_naming_another_band_is_refused_rather_than_read(tmp_path, monkeypatch):
    """A number lifted out of a sentence about a DIFFERENT band would place the
    stop somewhere the setup never armed. No number is better."""
    bars = [_banded("09:30", 100, 100, 100, 100, 100, 10),
            _banded("09:33", 100, 110, 90, 105, 100, 10)]
    row = _entry(trigger="index high touched u3 130.00 at 09:27, then closed "
                         "100.00 below that candle's low 101.00 1 bar later")
    del row["level"]
    r = _scored(tmp_path, monkeypatch, bars, [row])[0]
    assert r["stop_px"] is None and r["stop_from"] is None


def test_the_opposite_bands_are_read_live_not_frozen_at_the_anchor(tmp_path, monkeypatch):
    """THE point of the band read. The operator trails band to band and the
    session VWAP drifts all day, so u2 at 09:30 is not u2 at 09:36. Here the
    ANCHOR's u2 is 120 and is never reached; the LIVE u2 on the arriving bar is
    110 and is. A frozen read would report "not reached" for a level the chart
    printed price through."""
    bars = [_banded("09:30", 100, 100, 100, 100, 100, 10),   # anchor: u2 = 120
            _banded("09:33", 100, 115, 100, 112, 90, 10)]    # live u2 = 110
    r = _scored(tmp_path, monkeypatch, bars, [_entry()])[0]
    b = r["bands"]
    assert b["u1"] == "09:33" and b["u2"] == "09:33" and b["u3"] is None
    assert b["furthest"] == "u2" and b["beyond"] is False
    assert b["sigma"] == 2.5                              # (115-90)/10


def test_beyond_u3_is_distinguished_from_merely_touching_it(tmp_path, monkeypatch):
    """*"+-2 std +-3 std and beyond"*. Touching u3 IS +3 sigma, so the level
    test alone cannot tell a tag from a run through it; the distance does."""
    at3 = [_banded("09:30", 100, 100, 100, 100, 100, 10),
           _banded("09:33", 100, 130, 100, 125, 100, 10)]    # exactly +3
    past = [_banded("09:30", 100, 100, 100, 100, 100, 10),
            _banded("09:33", 100, 145, 100, 140, 100, 10)]   # +4.5
    a = _scored(tmp_path, monkeypatch, at3, [_entry()])[0]["bands"]
    b = _scored(tmp_path, monkeypatch, past, [_entry()])[0]["bands"]
    assert a["u3"] == "09:33" and a["sigma"] == 3.0 and a["beyond"] is False
    assert b["u3"] == "09:33" and b["sigma"] == 4.5 and b["beyond"] is True


def test_a_missing_session_gets_a_reason_never_a_zero(tmp_path, monkeypatch):
    """"Could not score" and "scored, moved nothing" are opposite facts. A row
    the cache cannot reach carries the sentence and NO numbers at all."""
    monkeypatch.setattr(trigger_log, "_load_sessions", lambda idx: {})
    path = _write(_fresh(tmp_path), [_entry()])
    trigger_log.score(path)
    r = json.loads(open(path, encoding="utf-8").read().strip())
    assert "no cached NIFTY session for 2026-08-10" in r["unscored"]
    assert "UNMEASURED, not flat" in r["unscored"]
    for k in ("mfe", "mae", "stop_hit", "bands", "anchor_px"):
        assert k not in r


def test_a_session_that_ends_before_the_row_is_unmeasured_not_flat(tmp_path, monkeypatch):
    """A cache that holds the day but no bar after this row is still an absence
    of measurement, and must not read as a trade that went nowhere."""
    bars = [_banded("09:30", 100, 100, 100, 100, 100, 10)]
    r = _scored(tmp_path, monkeypatch, bars, [_entry()])[0]
    assert "no forward window" in r["unscored"] and "mfe" not in r


def test_an_arm_is_anchored_on_its_own_candle_close_under_that_name(tmp_path, monkeypatch):
    """An arm entered nothing, so there is no entry price to measure from. It
    is measured from the ARM CANDLE'S CLOSE and the row says so, so a reader
    can never mistake which price a number is in points from."""
    bars = [_banded("09:24", 100, 100, 100, 100, 100, 10),
            _banded("09:30", 100, 105, 70, 100, 100, 10),     # touches d3 = 70
            _banded("09:33", 100, 112, 100, 110, 100, 10)]    # closes > 105
    arm = {"kind": "arm", "at": 1.0, "day": DAY, "index": IDX, "interval": 3,
           "t": "09:30", "side": "BUY", "band": "d3", "rule": "5c",
           "level": 70.0, "ref_high": 105.0, "extreme": 70.0,
           "rearm": False, "first_t": "09:30", "closed_bar": True}
    r = _scored(tmp_path, monkeypatch, bars, [arm])[0]
    assert r["anchor"] == "arm_close" and r["anchor_px"] == 100.0
    assert (r["mfe"], r["mfe_t"]) == (12.0, "09:33")
    # The question arms exist to answer: did the trigger earn its keep?
    assert r["triggered"] is True and r["trigger_t"] == "09:33"


def test_an_arm_the_cached_session_does_not_show_is_not_called_unfired(tmp_path, monkeypatch):
    """"Did not trigger" and "was not re-derived" look identical on a screen
    and mean opposite things. The scorer refuses to say the first."""
    bars = [_banded("09:30", 100, 100, 100, 100, 100, 10),
            _banded("09:33", 100, 110, 95, 105, 100, 10)]     # nothing arms
    arm = {"kind": "arm", "at": 1.0, "day": DAY, "index": IDX, "interval": 3,
           "t": "09:30", "side": "BUY", "band": "d3", "rule": "5c",
           "level": 70.0, "rearm": False, "first_t": "09:30",
           "closed_bar": True}
    r = _scored(tmp_path, monkeypatch, bars, [arm])[0]
    assert r["triggered"] is None
    assert "NOT re-derived" in r["trigger_why"]
    assert r["mfe"] is not None            # the move is still measured


def test_scoring_is_idempotent_to_the_byte_and_keeps_unknown_keys(tmp_path, monkeypatch):
    """Re-running must not duplicate a row, rewrite a log-time field, or drop a
    key this module has never heard of."""
    bars = [_banded("09:30", 100, 100, 100, 100, 100, 10),
            _banded("09:33", 100, 130, 90, 120, 100, 10)]
    path = _fresh(tmp_path)
    _cached(monkeypatch, bars)
    _write(path, [_entry(some_future_key={"kept": [1, 2]})])
    trigger_log.score(path)
    first = open(path, "rb").read()
    trigger_log.score(path)
    assert open(path, "rb").read() == first
    rows = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert len(rows) == 1
    assert rows[0]["some_future_key"] == {"kept": [1, 2]}
    assert rows[0]["at"] == 1.0 and rows[0]["px"] == 100.0
    assert rows[0]["t"] == "09:30" and rows[0]["level"] == 70.0


def test_a_row_unscored_today_is_scored_once_its_session_arrives(tmp_path, monkeypatch):
    """The reason is a state, not a verdict: it is cleared, not left beside the
    numbers, the run the cache can finally reach the day."""
    path = _write(_fresh(tmp_path), [_entry()])
    monkeypatch.setattr(trigger_log, "_load_sessions", lambda idx: {})
    trigger_log.score(path)
    assert json.loads(open(path, encoding="utf-8").read())["unscored"]
    _cached(monkeypatch, [_banded("09:30", 100, 100, 100, 100, 100, 10),
                          _banded("09:33", 100, 130, 90, 120, 100, 10)])
    trigger_log.score(path)
    r = json.loads(open(path, encoding="utf-8").read())
    assert "unscored" not in r and r["mfe"] == 30.0


def test_quarantined_rows_are_not_given_an_outcome_or_a_reason(tmp_path, monkeypatch):
    """A forming-bar capture and a void one-candle row are excluded by RULE,
    not by a gap in the cache. Writing "could not be scored" onto them would
    imply a fuller cache would fix something."""
    bars = [_banded("09:30", 100, 100, 100, 100, 100, 10),
            _banded("09:33", 100, 130, 90, 120, 100, 10)]
    rows = _scored(tmp_path, monkeypatch, bars,
                   [_entry(closed_bar=False), _entry(rule=None)])
    for r in rows:
        assert "mfe" not in r and "unscored" not in r


def test_no_rate_is_ever_printed_and_the_refusal_says_why():
    """Rule 2 of this screen and of this CLI. Below the target the sample is
    noise; at or above it, §5e records the pass criterion as OWED BY THE
    OPERATOR and not to be invented. Neither branch prints a percentage."""
    for n in (0, 3, trigger_log.TARGET_N, trigger_log.TARGET_N + 40):
        s = trigger_log.rate_refusal(n)
        assert "%" not in s
        assert "hit rate, win rate or expectancy" in s
        assert "LIVE forward rows, not a backtest" in s
    assert "INCONCLUSIVE" in trigger_log.rate_refusal(3)
    assert "OWED BY THE OPERATOR" in trigger_log.rate_refusal(trigger_log.TARGET_N)
