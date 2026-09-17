# tapemap/watch.py
"""watch.py -- WHERE THE FIGHT IS. Pure, stdlib only, no I/O, no clock.

THE SPLIT THAT MUST NEVER BLUR (spec §B.1). Hers to trade is two prices per
side and one line: d2/d3, u2/u3, VWAP. That is all of it, and `signals.py` owns
it. Every ladder row is something else -- a wall at 23,300 is not a trade, it
is where a maker will walk price, let it dwell and collect the stops. It
changes where she expects to be TAKEN and what the runway pays if it breaks.
It generates no entry.

THE HONEST RISK THIS FILE CARRIES (spec §H.1): four flags on a wall reads like
a setup. Three guardrails, all of them in code rather than in discipline:

  * watched rows carry no side, no direction and no target of their own --
    `_forbid` raises if one ever appears;
  * `signals.py`'s signature has no `walls_rows` parameter, so a watched level
    cannot originate a signal; it can vote through `oi_rows` and nothing more;
  * `NOTE` is a permanent header on the object, not decoration.

If the operator ever reports taking a trade off a watched level, the flags come
off the screen.

DANGER IS FLAGS, NEVER A SCORE (spec §B.3). Nothing is summed and no danger
number is printed. Six named conditions, printed when met. The list is ORDERED
by how many are met; the count orders and is never published. Ordering is not
a score, and the eye counts flags faster than it reads a number.

BROKEN IS REMEMBERED (spec §B.6). A level the sequence machine ran through
moves to `broken` and stays there for the rest of the session with its peak and
its break minute. It is never deleted mid-session and never silently
re-promoted: if price returns and the machine re-approaches, it comes back as
`role: "flipped"` with its break history attached. A level that failed as
resistance and is now tested as support is a different object and the screen
must not pretend otherwise. `prior` is the previous frame's own watch object --
this module stays pure and the caller carries the memory.
"""
from __future__ import annotations

from typing import List, Optional

# JUDGEMENT CALL (spec §F): sigma scales with the day and a fixed point count
# does not; 8 is a list and 9 is a table, and she rejected tables.
# KILL: if she scrolls the list, the cap is wrong.
CAP = 8
RADIUS_SIGMA = 1.5

# JUDGEMENT CALL (spec §F): each of the six is a fact the brain already holds.
# KILL: any flag that never varies across 30 sessions is deleted.
FLAGS = ("AGREE", "SIZE", "HELD", "DWELL", "FUEL", "CLOSING")

CLOSING_MARKS = 6          # the last 6 chain marks; points per minute over them
NOTE = "where the fight is \u2014 none of these is an entry"
_TAPE_KINDS = ("S", "B")
_OI_KINDS = ("CE", "PE")
_ENGAGING = ("PDH", "PDL", "PDC", "ROUND", "FLIP", "GAMMA_FLIP", "OPEN")
_FORBIDDEN = ("side", "direction", "dir", "target", "entry", "stop_px", "fire")


def _forbid(rows) -> None:
    """§H.1 in code. A watched row that grew a side, a direction or a target of
    its own is this layer's worst failure mode and raises here rather than
    reaching a screen."""
    for r in rows or []:
        for k in _FORBIDDEN:
            if k in r:
                raise ValueError(
                    f"a watched row may not carry {k!r} (spec §B.1, §H.1): "
                    "these rows say where the fight is, never what to do")


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _near(rows, spot, sigma) -> List[dict]:
    if spot is None or not sigma:
        return []
    r = RADIUS_SIGMA * float(sigma)
    return [w for w in rows or []
            if isinstance(w, dict) and w.get("p") is not None
            and abs(float(w["p"]) - float(spot)) <= r]


def _top3(rows, key, kinds) -> set:
    got = [(abs(float(w.get(key) or 0)), id(w)) for w in rows
           if w.get("kind") in kinds and w.get(key) is not None]
    got.sort(reverse=True)
    return {i for _v, i in got[:3]}


def _seq_of(sequence, w) -> dict:
    """The machine for this row. `sequence`'s keys are `kind@px` at one
    decimal (sequence.py:207); a row's own `state`/`tests` are the same
    machine's, copied in by frame._walls, so either source answers."""
    k = f"{w.get('kind')}@{float(w['p']):.1f}"
    return (sequence or {}).get(k) or {}


def _dwell_min(dwell, w) -> Optional[int]:
    d = dwell or {}
    lv = d.get("level") or {}
    if not d.get("holding") or lv.get("px") is None or d.get("held_s") is None:
        return None
    if abs(float(lv["px"]) - float(w["p"])) > float(d.get("band") or 0) + 1e-6:
        return None
    return int(round(float(d["held_s"]) / 60.0))


def _fuel_of(runways, w):
    """(fuel, stop_zone_lo) when this row IS the named target of a runway --
    the [I] figure hunt.py already published, never a re-derivation."""
    for leg in ("up", "down"):
        r = (runways or {}).get(leg) or {}
        t = r.get("target") or {}
        if t.get("px") is None or abs(float(t["px"]) - float(w["p"])) > 1e-6:
            continue
        sz = r.get("stop_zone") or {}
        return r.get("fuel"), sz.get("lo")
    return None, None


def _closing(minutes, basis, w, spot):
    """Points per minute the distance is shrinking over the last
    CLOSING_MARKS chain marks. `minutes` spots are INDEX prices and a ladder
    row is in the futures frame, so the basis has to come off or the sign
    itself can be wrong."""
    if basis is None or spot is None or not minutes:
        return None
    marks = sorted(minutes)[-CLOSING_MARKS:]
    if len(marks) < 2:
        return None
    s0 = (minutes.get(marks[0]) or {}).get("spot")
    if s0 is None:
        return None
    d0 = abs(float(w["p"]) - (float(s0) + float(basis)))
    d1 = abs(float(w["p"]) - float(spot))
    span = _mins(marks[-1]) - _mins(marks[0])
    if span <= 0:
        return None
    pts = (d0 - d1) / span
    return round(pts, 1) if pts > 0 else None


def _peak_chg(minutes, k, side, upto=None):
    """(peak_chg, minute, spot) off ChainState.minutes. Spec §C.2 names
    `ChainState.peak` for this; that structure is session-high OI with no
    minute attached, and `unwound_frac` needs the CHANGE series and the minute
    it peaked on -- only `minutes` carries both."""
    best = None
    for m in sorted(minutes or {}):
        if upto is not None and m > upto:
            break
        rec = minutes[m] or {}
        pair = (rec.get("k") or {}).get(k)
        if pair is None:
            continue
        v = pair[0] if side == "ce" else pair[1]
        if v is None:
            continue
        if best is None or abs(float(v)) > abs(best[0]):
            best = (float(v), m, (rec.get("spot")))
    return best or (None, None, None)


def _chg_now(minutes, k, side):
    for m in sorted(minutes or {}, reverse=True):
        pair = ((minutes[m] or {}).get("k") or {}).get(k)
        if pair is None:
            continue
        v = pair[0] if side == "ce" else pair[1]
        if v is not None:
            return float(v)
    return None


def _broken_row(ev, target, minutes, peaks) -> dict:
    ts = ev.get("ts") or ""
    kind = ev.get("level")
    k = side = None
    if kind in _OI_KINDS:
        side = kind.lower()
    peak_oi = peak_at = peak_spot = unwound = None
    peak_why = "this level is not an OI strike"
    if side is not None:
        cands = [kk for (kk, sd) in (peaks or {}) if sd == side]
        if cands:
            k = min(cands, key=lambda kk: abs(float(kk) - float(ev["px"])))
            peak_oi = (peaks or {}).get((k, side))
            pk, at, sp = _peak_chg(minutes, k, side)
            now = _chg_now(minutes, k, side)
            peak_at, peak_spot = at, sp
            if pk and now is not None:
                unwound = round(1.0 - (now / pk), 2)
            peak_why = None if peak_oi is not None else "no peak for that strike"
    return {"p": float(ev["px"]), "kind": kind,
            "broke_at": ts[11:16] if len(ts) >= 16 else None,
            "broke_at_why": None if len(ts) >= 16 else "the break carried no stamp",
            "broke_spot": ev.get("spot"),
            "peak_oi": peak_oi, "peak_at": peak_at, "peak_spot": peak_spot,
            "peak_why": peak_why,
            "unwound_frac": unwound,
            "unwound_why": None if unwound is not None else "no peak change to measure against",
            "target_named": (target or {}).get("px"),
            "target_named_why": None if (target or {}).get("px") is not None
                                else "the run was unaimed; no level ahead",
            "role": None, "tag": "M"}


def build(walls_rows, spot, sigma, basis, dwell, sequence, seq_fired, runways,
          minutes, peaks, prior=None) -> dict:
    """The §D `walls.watch` object.

    `prior` is the previous frame's own `walls.watch`; the caller carries the
    memory so this module stays pure. `walls_rows` IS the ladder and belongs
    here -- §H.1's rule is about `signals.py`, which never sees it."""
    near = _near(walls_rows, spot, sigma)
    big_oi = _top3(near, "oi", _OI_KINDS)
    big_sz = _top3(near, "size", _TAPE_KINDS)
    top_chg = _top3([w for w in near if w.get("conf") == "session"], "chg", _OI_KINDS)

    rows = []
    for w in near:
        st = _seq_of(sequence, w)
        state = st.get("state") or w.get("state")
        promoted = None
        if w.get("agree"):
            promoted = "agree"
        elif w.get("kind") in _ENGAGING and state not in (None, "IDLE", "held"):
            promoted = "sequence"
        elif w.get("kind") in _TAPE_KINDS and (w.get("leaned") or 0) >= 2:
            promoted = "leaned"
        elif id(w) in top_chg:
            promoted = "oi_top3"
        if promoted is None:
            continue

        tests = st.get("tests") if st.get("tests") is not None else w.get("tests")
        outcome = st.get("last_outcome") or w.get("last_outcome")
        dmin = _dwell_min(dwell, w)
        fuel, stop_lo = _fuel_of(runways, w)
        closing = _closing(minutes, basis, w, spot)

        flags = []
        if w.get("agree"):
            flags.append("AGREE")
        if id(w) in big_oi or id(w) in big_sz:
            flags.append("SIZE")
        if (tests or 0) >= 2 and outcome == "REJECT":
            flags.append("HELD")
        if dmin is not None:
            flags.append("DWELL")
        if fuel:
            flags.append("FUEL")
        if closing is not None:
            flags.append("CLOSING")

        rows.append({
            "p": float(w["p"]), "kind": w.get("kind"), "agree": w.get("agree"),
            "d": w.get("d"), "live": bool(state in ("APPROACH", "DWELL")),
            "flags": flags, "tests": tests, "last_outcome": outcome,
            "oi": w.get("oi"), "chg": w.get("chg"),
            "pain": w.get("pain"), "pain_tag": w.get("pain_tag"),
            "conf": w.get("conf"),
            "dwell_min": dmin, "closing_pts_min": closing,
            "fuel": fuel, "fuel_tag": "I" if fuel else None,
            "stop_zone": stop_lo, "stop_zone_tag": "I" if stop_lo else None,
            "promoted_by": promoted, "tag": "M"})

    # nearest first decides WHO is on the list (spec §B.2); flag count decides
    # the ORDER once they are (spec §B.3). The count itself is never published.
    rows.sort(key=lambda r: abs(float(r["p"]) - float(spot)))
    rows = rows[:CAP]
    rows.sort(key=lambda r: -len(r["flags"]))
    _forbid(rows)

    broken = [dict(b) for b in ((prior or {}).get("broken") or [])]
    have = {b["p"] for b in broken}
    fired = list(seq_fired or [])
    for i, ev in enumerate(fired):
        if ev.get("to") != "BREAK" or ev.get("px") is None:
            continue
        if float(ev["px"]) in have:
            continue
        run = next((f for f in fired[i + 1:]
                    if f.get("to") == "RUN" and f.get("px") == ev.get("px")), None)
        broken.append(_broken_row(ev, (run or {}).get("target"), minutes, peaks))
        have.add(float(ev["px"]))
    for b in broken:
        st = _seq_of(sequence, b)
        if st.get("state") in ("APPROACH", "DWELL"):
            b["role"] = "flipped"
    _forbid(broken)

    why = None
    if not rows:
        why = ("the war map did not answer" if not (walls_rows or [])
               else f"no ladder row within {RADIUS_SIGMA}\u03c3 of spot")
    return {"rows": rows, "broken": broken, "cap": CAP, "shown": len(rows),
            "why": why, "note": NOTE}
