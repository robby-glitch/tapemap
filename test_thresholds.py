"""Jarvis v3 Task 6: jarvis_thresholds.json is the one place the [I] numbers of jarvis.py and legs.py live; it is re-read
when it changes (no restart), and a missing or malformed file leaves every module default standing, said once."""
import json
import logging
import os
import re

import pytest

import jarvis
import legs
import mstate
import thresholds

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def tfile(tmp_path, monkeypatch):
    """A thresholds file of the test's own; the modules re-read the real one afterwards (their defaults, as shipped)."""
    p = tmp_path / "jarvis_thresholds.json"
    monkeypatch.setattr(thresholds, "PATH", str(p))
    yield p
    monkeypatch.undo()
    jarvis._thresholds()
    legs._thresholds()


def _write(p, doc, bump=0):
    p.write_text(json.dumps(doc), encoding="utf-8")
    if bump:                                          # a second write inside the clock's tick: move the mtime on
        st = os.stat(p)
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + bump * 10 ** 9))


def test_an_override_is_read_and_the_rest_default(tfile):
    _write(tfile, {"jarvis.FAST": 3.0})
    assert thresholds.get("jarvis.FAST", 2.0) == 3.0
    assert thresholds.get("jarvis.SLOW", 0.5) == 0.5            # not in the file: the module's own default


def test_a_change_is_re_read_without_a_restart(tfile):
    _write(tfile, {"jarvis.FAST": 3.0})
    assert thresholds.get("jarvis.FAST", 2.0) == 3.0
    _write(tfile, {"jarvis.FAST": 4.0}, bump=1)
    assert thresholds.get("jarvis.FAST", 2.0) == 4.0


def test_missing_or_malformed_means_defaults_said_once(tfile, caplog):
    with caplog.at_level(logging.WARNING, logger="thresholds"):
        assert thresholds.get("jarvis.FAST", 2.0) == 2.0       # no file at all
        assert thresholds.get("legs.DEEP", 0.35) == 0.35
    assert len(caplog.records) == 1 and "missing" in caplog.records[0].getMessage()
    caplog.clear()
    tfile.write_text("{not json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="thresholds"):
        assert thresholds.get("jarvis.FAST", 2.0) == 2.0
        assert thresholds.get("jarvis.FAST", 2.0) == 2.0
    assert len(caplog.records) == 1 and "unreadable" in caplog.records[0].getMessage()


def test_a_value_of_the_wrong_kind_keeps_the_default(tfile, caplog):
    _write(tfile, {"jarvis.FAST": "fast", "jarvis.SYNC_PTS": [11, 25, 35], "jarvis.BLIND_MIN": True})
    with caplog.at_level(logging.WARNING, logger="thresholds"):
        assert thresholds.get("jarvis.FAST", 2.0) == 2.0
        assert thresholds.get("jarvis.FAST", 2.0) == 2.0
        assert thresholds.get("jarvis.BLIND_MIN", 2) == 2           # a bool is not a number here
    assert len(caplog.records) == 2                                  # once per name, not once per build
    assert thresholds.get("jarvis.SYNC_PTS", (10, 25, 35)) == (11, 25, 35)   # JSON has no tuple: the default's kind


def test_a_value_that_would_take_the_frame_down_keeps_the_default(tfile, caplog):
    """T6 review: a wrong-kind value that passed the check took every frame down (LAD_NEAR 7.0 -> range() TypeError; a
    P5_MIN dict without BANKNIFTY -> KeyError). An int default takes an int only, a float one an int or a float, a dict
    the default's keys each of its kind, a tuple each element of its kind; else the default, one warning."""
    _write(tfile, {"jarvis.LAD_NEAR": 7.0, "jarvis.P5_MIN": {"NIFTY": 5}, "jarvis.SYNC_PTS": [10, "25", 35],
                   "jarvis.FAST": 3, "legs.LEG_MIN": True, "jarvis.ACT_LEAD": 3})
    with caplog.at_level(logging.WARNING, logger="thresholds"):
        assert thresholds.get("jarvis.LAD_NEAR", 7) == 7 and type(thresholds.get("jarvis.LAD_NEAR", 7)) is int
        assert thresholds.get("jarvis.P5_MIN", {"NIFTY": 5, "BANKNIFTY": 15}) == {"NIFTY": 5, "BANKNIFTY": 15}
        assert thresholds.get("jarvis.SYNC_PTS", (10, 25, 35)) == (10, 25, 35)
        assert thresholds.get("legs.LEG_MIN", 40) == 40
    assert len(caplog.records) == 4
    assert thresholds.get("jarvis.FAST", 2.0) == 3                     # an int for a float is a number
    assert thresholds.get("jarvis.ACT_LEAD", 2) == 3
    _write(tfile, {"jarvis.P5_MIN": {"NIFTY": 6, "BANKNIFTY": 15.5, "SENSEX": "x"}}, bump=1)
    assert thresholds.get("jarvis.P5_MIN", {"NIFTY": 5, "BANKNIFTY": 15}) == {"NIFTY": 5, "BANKNIFTY": 15}   # 15.5, "x"
    _write(tfile, {"jarvis.P5_MIN": {"NIFTY": 6, "BANKNIFTY": 15, "SENSEX": 12}}, bump=2)
    assert thresholds.get("jarvis.P5_MIN", {"NIFTY": 5, "BANKNIFTY": 15}) == {"NIFTY": 6, "BANKNIFTY": 15, "SENSEX": 12}
    _write(tfile, {"jarvis.LAD_NEAR": 7.0, "jarvis.P5_MIN": {"NIFTY": 5}}, bump=3)
    out = jarvis.build("2020-01-01", "NIFTY", 600)                    # applied: the build stops early, it never raises
    assert out["ok"] is False and jarvis.LAD_NEAR == 7 and jarvis.P5_MIN == {"NIFTY": 5, "BANKNIFTY": 15}


def test_an_unreadable_file_is_one_line_in_health_method(tfile):
    """T6 review: a malformed file left every default standing, said only in the log; her screen must say it."""
    _write(tfile, {"jarvis.FAST": 2.0})
    assert thresholds.problem() is None
    tfile.write_text("{not json", encoding="utf-8")
    assert thresholds.problem() == "thresholds file unreadable: module defaults in use"
    tfile.write_text("[1, 2]", encoding="utf-8")
    assert thresholds.problem() == "thresholds file unreadable: module defaults in use"
    tfile.unlink()
    assert thresholds.problem() == "thresholds file missing: module defaults in use"
    tfile.write_text("{not json", encoding="utf-8")
    d = {"mins": ["09:15"], "delta": [1], "flow": [1], "flow_src": ["D"], "f_src": ["dext"], "holes": [],
         "chain_missing": [], "sides": [], "idx": "NIFTY", "ctx": {"method": ["RV x"]}}
    assert jarvis.health(d, True)["method"] == ["RV x", "thresholds file unreadable: module defaults in use"]
    assert not any("thresholds" in x for x in jarvis.health(d, True)["notes"])       # how a number was made, not a gap


def test_a_change_takes_effect_at_the_next_build(tfile):
    _write(tfile, {"jarvis.FAST": 3.0, "legs.DEEP": 0.4, "jarvis.SYNC_PTS": [11, 26, 36]})
    out = jarvis.build("2020-01-01", "NIFTY", 600)                    # no record here: the build stops early
    assert out["ok"] is False
    assert jarvis.FAST == 3.0 and legs.DEEP == 0.4 and jarvis.SYNC_PTS == (11, 26, 36)
    _write(tfile, {"jarvis.FAST": 2.5}, bump=1)
    jarvis.build("2020-01-01", "NIFTY", 600)
    assert jarvis.FAST == 2.5 and legs.DEEP == 0.35 and jarvis.SYNC_PTS == (10, 25, 35)   # gone from the file: default


def _tagged(path):
    """Every module constant whose definition (or its comment's continuation lines) carries [I], from the source."""
    names, cur = set(), None
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"^([A-Z][A-Z0-9_]*(?:\s*,\s*[A-Z][A-Z0-9_]*)*)\s*=", ln)
        if m:
            cur = [x.strip() for x in m.group(1).split(",")]
        elif not re.match(r"^\s+#", ln):
            cur = None
        if cur and "[I]" in ln:
            names.update(cur)
    return names


def test_the_shipped_file_holds_every_I_number_at_its_default():
    with open(os.path.join(HERE, "jarvis_thresholds.json"), encoding="utf-8") as f:
        doc = json.load(f)
    assert "NOTEPAD" in doc["_rule"]
    for mod, path in ((jarvis, "jarvis.py"), (legs, "legs.py"), (mstate, "mstate.py")):
        tagged = _tagged(os.path.join(HERE, path))
        assert tagged <= set(mod._I), (path, sorted(tagged - set(mod._I)))          # every [I] constant is looked up
        for n in mod._I:
            key = f"{mod.__name__}.{n}"
            assert key in doc and doc["_why"].get(key), key                         # with a reason
            v = doc[key]
            assert (tuple(v) if isinstance(mod._DEF[n], tuple) else v) == mod._DEF[n], key   # shipping it changes nothing
    keys = {k for k in doc if not k.startswith("_")}
    assert keys == {f"{m.__name__}.{n}" for m in (jarvis, legs, mstate) for n in m._I}
    assert set(doc["_why"]) == keys
