# tapemap/frame_log.py
"""frame_log.py -- THE ONE DECISION RECORD. `data/frame/frame_<day>.jsonl`.

Appended when the frame's SIGNATURE changes -- walls rows and their state,
setup state, tells, the missing list -- never on a raw counter or a tick of
OI. The categorical-signature idea is receive.mjs's `sig()` (the extension's
retired sink), moved into the process that survives the browser, so a
morning like 2026-09-11 (tool right all day, record empty) cannot recur.

Forward cells (`ex`, `resolved`) are written ONCE by score_frame.py and never
edited here. Raw sense logs (senses/, warmap/, chain/) stay as inputs; this
file is the only decision record. Fail-soft append, same as sequence.py.
"""
from __future__ import annotations

import json
import os
from typing import Optional

DIR = os.path.join("data", "frame")
_last_sig: dict = {}      # (day, idx) -> last signature written


def day_path(day: str) -> str:
    return os.path.join(DIR, f"frame_{day}.jsonl")


def sig(fr: dict) -> str:
    rows = [(r.get("p"), r.get("kind"), r.get("state")) for r in (fr.get("walls") or {}).get("rows") or []]
    s = fr.get("setup") or {}
    tells = [(t.get("name"), t.get("target")) for t in s.get("tells") or []]
    # THE SIGNAL IS PART OF THE SIGNATURE (spec §A.10). Without this a visit
    # could go REACHED -> ARMED -> LIVE with the ladder unchanged and the
    # record would hold one row for the whole thing -- the scorer fills
    # forward cells per row, so a transition nobody appended is a transition
    # nobody can score. No new file and no new scorer: `signal{}` and
    # `votes{}` ride inside the frame this function already writes whole.
    sg = s.get("signal") or {}
    vo = s.get("votes") or {}
    return json.dumps([fr.get("idx"), rows, s.get("state"), s.get("fire"), tells,
                       sg.get("state"), sg.get("visit_key"), sg.get("sound"),
                       vo.get("n"), vo.get("passed"),
                       sorted(fr.get("missing") or [])], default=str)


def append_if_changed(fr: dict, day: str, idx: str = "NIFTY", path: Optional[str] = None) -> bool:
    s = sig(fr)
    key = (day, idx)
    if _last_sig.get(key) == s:
        return False
    p = path or day_path(day)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps({"day": day, **fr}, default=str) + "\n")
    except OSError:
        return False          # never drop the feed for a disk error
    _last_sig[key] = s
    return True
