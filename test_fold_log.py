"""fold_log.py: rows per event and per bucket close, the three stamps on every row, outcome rows 20 minutes
after a falsifiable read, and the causal resume (6-amendment.md §5, §10): a mid-day restart on recorded
inputs writes zero `diverged` rows; a row that reads differently writes one, and the logged words win."""
import json

import pytest

import fold
import fold_log
from test_fold import DAY, PATH_A, PE, inputs

END = fold.ms(DAY, "09:48:00")


@pytest.fixture(autouse=True)
def _fold_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(fold_log, "DIR", str(tmp_path / "fold"))
    monkeypatch.setattr(fold_log, "_seen", {})


def _batches(inp, t_end, step=60000):
    keys = sorted([(r["t"], 1, r) for r in inp["book"]] + [(fold.ms(DAY, r["ts"]), 0, r) for r in inp["chain"]], key=lambda x: (x[0], x[1]))
    t, i, out = keys[0][0] // step * step, 0, []          # whole-minute batches, so a restart at :00 cuts between them
    while i < len(keys) and keys[i][0] <= t_end:
        b, c = [], []
        while i < len(keys) and keys[i][0] < t + step and keys[i][0] <= t_end:
            (b if keys[i][1] else c).append(keys[i][2])
            i += 1
        out.append((min(t + step, t_end), b, c))
        t += step
    return out


def _live(inp, t_end, trade=PE):
    """The server's day: a State fed a minute at a time, the log written after every step."""
    st = fold.State(trade, dict(inp, book=[], chain=[]))
    st.feed(vpin=inp["vpin"])
    for now, b, c in _batches(inp, t_end):
        fold.step(st, dict(book=b, chain=c), now=now)
        fold_log.write(st)
    return st


def test_one_row_per_event_and_per_bucket_close_with_the_three_stamps():
    inp = inputs(PATH_A)
    st = _live(inp, END)
    rows = fold_log.read("NIFTY", DAY)
    ev = [r for r in rows if r["event"] not in ("outcome", "diverged")]
    assert len(ev) == len(st.events) and [r["seq"] for r in ev] == [e["seq"] for e in st.events]
    assert sum(1 for r in ev if r["event"] == "bucket") == sum(1 for e in st.events if e["kind"] == "bucket") > 0
    for r in rows:
        assert r["rev"] == "6" and r["shadow"] is True and len(r["thresholds_sha"]) == 16 and len(r["code_sha"]) == 16
    r = next(r for r in ev if r["event"] == "fold")
    assert r["sound_id"] and r["headline"].startswith("FOLD ·") and r["chips"] and r["sentences"] and r["prem"]["now"]
    # nothing new -> nothing written; a call is never a row
    n = len(rows)
    for _ in range(50):
        assert fold_log.write(st) == 0
    assert len(fold_log.read("NIFTY", DAY)) == n


def test_outcome_rows_come_twenty_minutes_after_each_falsifiable_read_once():
    inp = inputs(PATH_A)
    st = _live(inp, END)
    rows = fold_log.read("NIFTY", DAY)
    f = next(r for r in rows if r["event"] == "fold")
    outs = [r for r in rows if r["event"] == "outcome"]
    early = [r for r in outs if r["ref_id"] == f"{f['trade_id']}:{f['seq']}"]
    assert not early or fold.ms(DAY, early[0]["ts"]) >= f["t"] + 20 * 60000
    # 20 more minutes of rows: the fold's outcome lands, once, with a verdict and its why
    more = inputs(PATH_A + [("09:48:00", 1500, 0, 0.0)])
    st2 = _live(more, fold.ms(DAY, "10:13:00"))
    outs = [r for r in fold_log.read("NIFTY", DAY) if r["event"] == "outcome" and r["ref_event"] == "fold"]
    assert len(outs) >= 1 and outs[0]["verdict"] in ("real", "noise") and outs[0]["why"] and outs[0]["read"].startswith("fold:")
    assert fold_log.write(st2) == 0
    assert len([r for r in fold_log.read("NIFTY", DAY) if r["event"] == "outcome" and r["ref_id"] == outs[0]["ref_id"]]) == 1


def test_a_mid_day_restart_on_recorded_inputs_writes_zero_diverged_rows():
    inp = inputs(PATH_A)
    t_restart = fold.ms(DAY, "09:30:00")
    live = _live(inp, t_restart)
    n_logged = len(fold_log.read("NIFTY", DAY))
    # the restart: recompute causally from the recorded rows, then carry on live
    again = fold.start(PE, dict(inp, book=[r for r in inp["book"] if r["t"] < t_restart],
                                chain=[r for r in inp["chain"] if fold.ms(DAY, r["ts"]) < t_restart]))
    res = fold_log.resume(again)
    assert res["diverged"] == 0 and res["last_seq"] == live.events[-1]["seq"]
    assert fold_log.write(again) == 0                          # logged rows are never re-emitted
    v = fold_log.words(again.view(t_restart), res)
    assert v["resumed"] is True and v["headline"] == res["words"]["headline"]
    for now, b, c in _batches(inp, END):
        if now <= t_restart:
            continue
        fold.step(again, dict(book=b, chain=c), now=now)
        fold_log.write(again)
    rows = fold_log.read("NIFTY", DAY)
    assert not any(r["event"] == "diverged" for r in rows)
    whole = fold.read(PE, inp, upto="09:48:00")
    ev = [r for r in rows if r["event"] not in ("outcome", "diverged")]
    assert [(r["seq"], r["event"], r["ts"], r["headline"]) for r in ev] == [(e["seq"], e["kind"], e["ts"], e["row"]["headline"]) for e in whole["events"]]
    assert len(ev) > n_logged


def test_a_row_that_reads_differently_writes_a_diverged_row_and_the_logged_words_win():
    inp = inputs(PATH_A)
    t_restart = fold.ms(DAY, "09:30:00")
    _live(inp, t_restart)
    p = fold_log.path("NIFTY", DAY)
    rows = [json.loads(l) for l in open(p, encoding="utf-8")]
    rows[-1]["headline"] = "HOLD · behind you: a word that was on the screen"
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    fold_log._seen.clear()
    again = fold.start(PE, dict(inp, book=[r for r in inp["book"] if r["t"] < t_restart],
                                chain=[r for r in inp["chain"] if fold.ms(DAY, r["ts"]) < t_restart]))
    res = fold_log.resume(again)
    assert res["diverged"] == 1
    d = [r for r in fold_log.read("NIFTY", DAY) if r["event"] == "diverged"]
    assert len(d) == 1 and d[0]["ref_seq"] == rows[-1]["seq"] and d[0]["logged"]["headline"] == rows[-1]["headline"]
    assert fold_log.resume(again)["diverged"] == 1 and len([r for r in fold_log.read("NIFTY", DAY) if r["event"] == "diverged"]) == 1
    v = fold_log.words(again.view(t_restart), res)
    assert v["headline"] == rows[-1]["headline"] and v["resumed"] is True
