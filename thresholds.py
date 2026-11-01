"""thresholds.py -- THE ONE PLACE the [I] numbers of jarvis.py and legs.py live (Jarvis v3 Task 6).

`get("jarvis.FAST", 2.0)` -> the value in jarvis_thresholds.json ({"jarvis.FAST": 2.0, "legs.DEEP": 0.35, ...}), else the
caller's default (the module's own constant). The file is re-read when its mtime or size changes, cached otherwise, so a
change takes effect at the next jarvis.build without a restart (jarvis._thresholds / legs._thresholds). A missing or
malformed file, or a value of the wrong type, -> the default, with one warning in the log per file state; a missing or
unreadable file is also one line on her screen (problem() -> jarvis.health's method). Every change needs a NOTEPAD line
(the file's "_rule"); keys starting "_" are its notes. Stdlib only, nothing written.
"""
from __future__ import annotations

import json
import logging
import os
import threading

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_thresholds.json")
log = logging.getLogger("thresholds")
_LOCK = threading.Lock()
_S = {"key": None, "vals": {}, "bad": set(), "why": None}   # the file state, its values, the names warned of, the
                                                             # file's own problem (problem())


def stamp():
    """The file's state (path, mtime_ns, size), or (path, None) when it is missing: what the cache is keyed on."""
    try:
        st = os.stat(PATH)
    except OSError:
        return PATH, None
    return PATH, st.st_mtime_ns, st.st_size


def _vals():
    key = stamp()
    with _LOCK:
        if key != _S["key"]:
            (_S["vals"], _S["why"]), _S["key"], _S["bad"] = _read(key), key, set()
        return _S["vals"]


def problem():
    """The file's own state when every number is the module's default -> "thresholds file missing / unreadable: module
    defaults in use", else None (the file read; a single bad value is the log's, its default standing)."""
    _vals()
    return _S["why"]


def _read(key):
    """-> (the file's values, None) or ({}, the line problem() says)."""
    if key[1] is None:
        log.warning("thresholds: %s missing: every [I] number is the module's own default", key[0])
        return {}, "thresholds file missing: module defaults in use"
    try:
        with open(key[0], encoding="utf-8") as f:
            v = json.load(f)
    except (OSError, ValueError) as e:
        log.warning("thresholds: %s unreadable (%s): every [I] number is the module's own default", key[0], e)
        return {}, "thresholds file unreadable: module defaults in use"
    if not isinstance(v, dict):
        log.warning("thresholds: %s is not a JSON object: every [I] number is the module's own default", key[0])
        return {}, "thresholds file unreadable: module defaults in use"
    return v, None


def _fits(v, default):
    """Is `v` a value the code can use where `default` stands? (The file is hand-edited and re-read in market hours: a
    value that passed here and broke a build would stop the card, the log and the voice.) An int default takes an int
    only, a float one an int or a float, never a bool for either; a tuple a list of its length (JSON has no tuple), each
    element fitting the default's; a dict the default's keys, each value fitting the default's (an extra key, the first
    default value's kind); else the default's own type."""
    if isinstance(default, bool) or isinstance(v, bool):
        return type(v) is type(default)
    if isinstance(default, int):
        return isinstance(v, int)
    if isinstance(default, float):
        return isinstance(v, (int, float))
    if isinstance(default, tuple):
        return isinstance(v, list) and len(v) == len(default) and all(map(_fits, v, default))
    if isinstance(default, dict):
        d0 = next(iter(default.values()), None)
        return isinstance(v, dict) and all(k in v for k in default) and             all(_fits(x, default.get(k, d0)) for k, x in v.items())
    return isinstance(v, type(default))


def get(name: str, default):
    """The [I] number `name` ("jarvis.FAST"), from the file when it holds one of the default's kind, else `default`."""
    vals = _vals()
    if name not in vals:
        return default
    v = vals[name]
    if default is not None and not _fits(v, default):
        if name not in _S["bad"]:                     # once per file state, never once per build
            _S["bad"].add(name)
            log.warning("thresholds: %s = %r is not a %s: the default %r stands", name, v, type(default).__name__, default)
        return default
    return tuple(v) if isinstance(default, tuple) else v
