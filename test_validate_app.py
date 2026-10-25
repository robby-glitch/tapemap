"""Validate's app.js (ui-v2/public/validate2) in node, through test/validate_app_harness.cjs (25 Oct review F9 / F10): the
one stop and the pollers. The face's engine.js keeps its own harness (test_validate3.py). Skipped when node is not installed."""
import json
import os
import shutil
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(HERE, "test", "validate_app_harness.cjs")
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def run(scenario):
    r = subprocess.run(["node", HARNESS, scenario], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert "err" not in out, out.get("err")
    return out


def test_the_stop_is_the_voices_or_could_not_check_never_engine_js_g():
    """F9 / A73 (DEV-FACES F03): with the voice refused, Validate drew engine.js's own give-up G as the STOP line and the
    to-stop cells -- a third stop beside the panel's and the Float's. Now it is the voice's stop, or "could not check — why"."""
    o = run("voice_stop")
    assert o["refused"] == {"why": "could not check — the engine is catching up (12 of 40 rows)"}
    assert o["mute"] == {"why": "could not check — HOLD v2 has no line yet"}
    assert o["none"] == {"why": "could not check — TapeMap ki voice nahi aayi"}
    assert o["spoke"] == {"f": 23050, "s": 23010, "src": "HOLD v2"}


def test_a_voice_with_a_fut_stop_and_no_spot_one_shows_the_fut_stop_and_spot_unknown():
    """F9 round 1: the voice spoke (fold engine's fallback with basis_ix None: stop_f set, stop_s None). The face said "TapeMap
    ki voice nahi aayi" -- false. It shows the fut stop and `spot ?`, and never invents a spot value."""
    o = run("fut_only")
    assert o["f"] == 22640 and o["s"] is None
    assert "22640f · spot ?" in o["txt"] and "nahi aayi" not in json.dumps(o)


def test_off_the_clock_the_stop_why_is_the_replayed_voices_own_why():
    """F9 round 1: the replayed path's entry at T carries the voice's why; voiceStop read only the path's."""
    o = run("path_why")
    assert o["entry"] == {"why": "could not check — second"}
    assert o["first"] == {"why": "could not check — first"}
    assert o["refused"] == {"why": "could not check — replay refused"}
    assert o["bare"] == {"why": "could not check — TapeMap ki voice nahi aayi"}


def test_the_prototype_row_prints_no_out_if_stop_without_a_voice_stop():
    """F9 round 1 (DEV-FACES F12): with /api/fold refused (or the voice mute, or no stop on it) the prototype row's
    "out if G fut accepted" is a fallback stop on the face. The word stays; the clause goes -- and it goes beside the
    voice's own stop too, which is the one stop (controller, 25 Oct)."""
    o = run("proto_row")
    for k in ("refused", "mute", "nostop"):
        assert o[k]["sub"] == "" and o[k]["ewSub"] == "" and "out if" not in json.dumps(o[k]), k
        assert o[k]["src"] == "prototype" or k != "refused"
    assert o["refused"]["headline"] == "HOLD"
    assert o["spoke"]["sub"] == "" and "out if" not in json.dumps(o["spoke"])


def test_each_poller_has_one_request_in_flight_and_gives_up_in_8_s():
    """F10 (DEV-FACES F20, F05): pollFold / pollTrades / pollFlat had no in-flight guard and no timeout, so about 5 requests a
    second stacked on a wedged server and a late reply could overwrite a newer voice; /api/v2/data's poll hung for good and
    FEED DEAD never came. Now each keeps one request in flight, bounded at 8 s (ui-v2 hold/store.ts j()'s bound)."""
    o = run("pollers")
    assert o["inFlight"] == {"fold": 1, "flat": 1, "trades": 2, "data": 1}
    assert o["after"] == {"fold": 2, "flat": 2, "trades": 3}
    assert o["bounded"] and set(o["bounded"]) == {8000}
    assert o["feed"] == "dead" and o["fold"] == {"ok": False, "why": "not answering"}


def test_a_mark_and_an_exit_refresh_the_trade_list_even_with_the_5_s_poll_in_flight():
    """F10 round 1: markTrade / exitTrade awaited pollTrades(), which returns at once while the 5 s poll is out -- the new trade
    was not selected, and after an exit the trade still showed open (a second exit click). Now a call made while the poll is
    in flight waits for it, then reads once more: a read that began after the write. Still one read in flight."""
    o = run("refresh_after_write")
    for k in ("mark", "exit"):
        assert o[k]["during"] == 2, k          # the boot read and the slow poll; no read beside the slow one
        assert o[k]["gets"] == 3, k            # then one read that began after the write
    assert o["mark"]["sel"] == "NIFTY-22600CE-long-100000" and o["mark"]["exitTs"] == [None]
    assert o["exit"]["exitTs"] == [36300]


def test_a_hung_full_reload_gives_up_in_its_bound_and_frees_the_poller():
    """F10 round 1: poll() falls back to loadFull() when the engine says reload; that fetch had no signal, so one hang kept
    `polling` true for good -- FEED DEAD never showed and nothing polled again. Now it is bounded (20 s: the whole day)."""
    o = run("full_reload")
    assert o["ms"] == [20000]
    assert o["dead"] == "dead" and o["again"] == 1 and o["feed"] == "ok"


def test_the_decode_poll_is_bounded_at_8_s_and_frees_its_flag():
    """F10 round 1: pollDecode's read had no signal, so one hang kept decBusy true for good and no chart's decode loaded."""
    o = run("decode")
    assert o["inFlight"] == 1                  # the second chart waits for the first
    assert o["ms"] == [8000, 8000]             # and the first gave up, so the third could ask
    assert "timed out" in o["why"]
