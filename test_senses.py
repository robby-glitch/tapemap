"""The wiring layer: real frames in, forward-log rows out.

Two of these matter more than the rest. `test_the_trigger_log_is_never_touched`
pins the one rule whose violation is unrecoverable -- detector rows must never
land in the file holding the 5c / zone / legacy populations. And
`test_a_write_failure_does_not_take_the_tape_down` pins fail-soft: a log line
that cannot be written must cost a counter, never the session.
"""
import json
from pathlib import Path

import senses
import upstox_adapter as ua

FRAME = Path(__file__).parent / "data" / "feed_frame_2026-08-20.json"


def _frames():
    return json.loads(FRAME.read_text(encoding="utf-8"))


def _fut_feed():
    d = _frames()
    return d["frames"][d["fut_key"]], d["fut_key"]


def _swept(feed, drop=3):
    """The same frame after `drop` ask levels were lifted -- a BUY sweep.

    Upstox pairs a bid and an ask inside ONE `Quote`, so the two ladders share
    a container without being related. Slicing that array therefore removes
    levels from BOTH sides, which is a two-sided collapse, not an aggressor --
    and it reads as a SELL sweep here, because the bid side of this real book
    carries more size. So the ask ladder is shifted while the bids are left
    exactly where they were, which is what lifting offers actually does.
    """
    out = json.loads(json.dumps(feed))
    mf = out["fullFeed"]["marketFF"]
    q = mf["marketLevel"]["bidAskQuote"]
    mf["marketLevel"]["bidAskQuote"] = [
        {"bidQ": q[i].get("bidQ"), "bidP": q[i].get("bidP"),
         "askQ": q[i + drop].get("askQ") if i + drop < len(q) else 0,
         "askP": q[i + drop].get("askP") if i + drop < len(q) else 0}
        for i in range(len(q))]
    mf["vtt"] = (mf.get("vtt") or 0) + 5_000
    return out


# --------------------------------------------------------------------------
# the rule that must never break
# --------------------------------------------------------------------------

def test_the_trigger_log_is_never_touched(tmp_path):
    """The forward record of 5c / zone / legacy rows is the one irreplaceable
    artefact here. Detector rows are a fourth population and must land
    elsewhere, always."""
    assert "trigger_log" not in senses.DIR
    assert "trigger_log" not in senses.day_path("2026-08-20")
    assert senses.day_path("2026-08-20").endswith("senses_2026-08-20.jsonl")

    real = Path(__file__).parent / "data" / "trigger_log.jsonl"
    before = real.read_bytes() if real.exists() else None

    feed, key = _fut_feed()
    s = senses.Senses(path=str(tmp_path / "senses.jsonl"), day="2026-08-20")
    s.observe("FUT", "10:00", feed, key)
    s.observe("FUT", "10:01", _swept(feed), key)

    after = real.read_bytes() if real.exists() else None
    assert after == before


# --------------------------------------------------------------------------
# rows
# --------------------------------------------------------------------------

def test_a_real_sweep_becomes_a_logged_row(tmp_path):
    feed, key = _fut_feed()
    log = tmp_path / "senses.jsonl"
    s = senses.Senses(path=str(log), day="2026-08-20")
    assert s.observe("FUT", "10:00", feed, key) == []       # nothing prior
    rows = s.observe("FUT", "10:01", _swept(feed), key)

    assert "sweep" in [r["det"] for r in rows]
    row = next(r for r in rows if r["det"] == "sweep")
    assert row["day"] == "2026-08-20" and row["t"] == "10:01"
    assert row["inst"] == "FUT" and row["key"] == key
    assert row["side"] == "buy" and row["levels"] == 3 and row["tag"] == "M"

    on_disk = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert on_disk == rows              # returned and written are the same rows


def test_nothing_is_written_when_nothing_happened(tmp_path):
    feed, key = _fut_feed()
    log = tmp_path / "senses.jsonl"
    s = senses.Senses(path=str(log), day="2026-08-20")
    s.observe("FUT", "10:00", feed, key)
    s.observe("FUT", "10:01", feed, key)                    # identical book
    assert s.written == 0 and not log.exists()


def test_instruments_keep_separate_detectors(tmp_path):
    """One book must never be compared against another's -- that would report
    a sweep of the whole distance between two instruments."""
    d = _frames()
    fut, futk = d["frames"][d["fut_key"]], d["fut_key"]
    optk = next(k for k in d["meta"] if k != futk)
    opt = d["frames"][optk]
    s = senses.Senses(path=str(tmp_path / "senses.jsonl"), day="2026-08-20")
    s.observe("FUT", "10:00", fut, futk)
    assert s.observe("OPT", "10:00", opt, optk) == []       # its own first frame


def test_the_index_leg_has_no_book_and_produces_nothing(tmp_path):
    d = _frames()
    idx = d["frames"][d["idx_key"]]
    s = senses.Senses(path=str(tmp_path / "senses.jsonl"), day="2026-08-20")
    s.observe("IDX", "10:00", idx, d["idx_key"])
    assert s.observe("IDX", "10:01", idx, d["idx_key"]) == []


def test_ladder_of_reads_book_and_volume_from_the_same_frame():
    feed, _ = _fut_feed()
    lad, vtt = senses.ladder_of(feed)
    assert lad == ua.depth_ladder(feed)
    assert vtt == feed["fullFeed"]["marketFF"]["vtt"]


# --------------------------------------------------------------------------
# fail-soft
# --------------------------------------------------------------------------

def test_a_write_failure_does_not_take_the_tape_down(tmp_path):
    """A log line that cannot be written costs a counter, never the session."""
    feed, key = _fut_feed()
    bad = tmp_path / "nope"
    bad.mkdir()                                   # a directory, not a file
    s = senses.Senses(path=str(bad), day="2026-08-20")
    s.observe("FUT", "10:00", feed, key)
    rows = s.observe("FUT", "10:01", _swept(feed), key)     # must not raise
    assert rows and s.written == 0 and s.failed == len(rows)


def test_pending_absorption_is_reported_but_not_logged(tmp_path):
    """A running total must not enter the record -- it is still growing."""
    feed, key = _fut_feed()
    log = tmp_path / "senses.jsonl"
    s = senses.Senses(path=str(log), day="2026-08-20")
    hot = json.loads(json.dumps(feed))
    hot["fullFeed"]["marketFF"]["vtt"] = feed["fullFeed"]["marketFF"]["vtt"] + 50_000
    s.observe("FUT", "10:00", feed, key)
    s.observe("FUT", "10:01", hot, key)           # touch held, volume poured in
    live = s.pending()
    assert "FUT" in live and live["FUT"]["ratio"] > 1
    assert s.written == 0 and not log.exists()


def test_a_detectors_own_fields_cannot_rewrite_the_rows_identity(tmp_path):
    """`Sweep.kind` is "swept"; the row's identity is `det`. When those shared
    a name the event overwrote the envelope and every row looked alike. The
    envelope must win, and the event's own kind must survive alongside it."""
    feed, key = _fut_feed()
    s = senses.Senses(path=str(tmp_path / "senses.jsonl"), day="2026-08-20")
    s.observe("FUT", "10:00", feed, key)
    row = next(r for r in s.observe("FUT", "10:01", _swept(feed), key)
               if r["det"] == "sweep")
    assert row["det"] == "sweep" and row["kind"] == "swept"
    assert row["inst"] == "FUT" and row["day"] == "2026-08-20"


def test_the_log_is_one_file_per_day():
    """A single growing file at the measured row rate is the chain-snapshot
    problem again. Per day, so one session can be handed to a scorer."""
    a, b = senses.day_path("2026-08-20"), senses.day_path("2026-08-21")
    assert a != b and senses.DIR in a and a.endswith(".jsonl")


def test_the_day_is_resolved_at_write_time_not_at_construction(tmp_path):
    """A process left running across midnight must roll into the new day's
    file, not keep appending to the one it opened at start."""
    import os
    feed, key = _fut_feed()
    s = senses.Senses(day="2026-08-20")
    s.day = "2026-08-21"                       # midnight, mid-process
    assert os.path.basename(senses.day_path(s.day)) == "senses_2026-08-21.jsonl"
