# tapemap/breadth.py
"""breadth.py -- POSITIONING BREADTH. Pure, stdlib only, no I/O, no clock.

THREE THINGS WEAR THIS WORD AND ONLY ONE OF THEM IS HERE (spec §C).

  * DERIVATIVE BREADTH (engine.py:1004) sums four direction signs into STRONG
    BULL / LEAN BULL / MIXED / LEAN BEAR / STRONG BEAR. Three of those four are
    mechanically the same fact -- the index moved -- read through the index,
    its calls and its puts; collinear by construction, and only the regime lean
    is independent. It is one instrument's direction counted three times. THE
    VERDICT IS NOT PORTED and those words do not appear on this screen at any
    size; its own author's comment records it printing STRONG BEAR while price
    sat above VWAP on a 53M put wall. Two of its inputs ARE real and
    independent and land here as named facts: `regime` and `pinned`.

  * TRUE MARKET BREADTH (advances and declines) DOES NOT EXIST AND IS NOT
    BUILT (spec §C.3). Not bandwidth: index MEMBERSHIP is not in the Upstox
    dump, so the constituent list would be hardcoded and hand-maintained, and a
    stale list produces an advance/decline count that is quietly wrong in
    exactly the way nobody audits. Revisit after 30 sessions of forward rows,
    from free end-of-day constituent data, after the fact.

  * POSITIONING BREADTH -- this file. Her counterparty is the writer; this
    measures the writers, and every input is already in memory.

THERE IS NO DIRECTION FIELD IN THIS OBJECT (spec §C.4, §H.5). Not a word, not a
sign, not a net vote. Breadth is never a vote, never a gate, never a banner,
never a sound: the ballot's four votes are all local to the level in play and
the day's weather does not join them. Breadth may CAPTION a decision, never
make one -- and the enforcement is that you cannot render a banner from data
that does not contain one. `BANNED_WORDS` and the test that asserts on it are
how that stays true after somebody adds a field in six months.

WHAT THE COUNTS READ FROM. `ChainState.minutes[HH:MM]` is
`{"spot", "k": {strike: (ce_chg, pe_chg)}, "px": {strike: (ce_ltp, pe_ltp)},
"src"?}` -- `k` is CUMULATIVE change since the open, `px` is a LEVEL, and `src`
is "backfill" when chain_backfill rebuilt that mark from REST candles. The
window differences `k` across two marks and differences `px` across the same
two; backfilled marks are counted and flagged, never blended silently.
"""
from __future__ import annotations

from typing import List, Optional

# JUDGEMENT CALL (spec §F): three grid marks -- long enough that one poll
# cannot move it, short enough to turn inside a leg.
# KILL: if it flips more than twice an hour it is too short.
WINDOW_MIN = 15

# JUDGEMENT CALL (spec §F): a quarter given back is visible on the canvas.
# KILL: tune against the ghost outlines after 10 sessions.
RETREATING_FRAC = 0.25
ADVANCING_FRAC = 0.10

NOTE = ("counts of strikes, not a direction. calls written = a ceiling being "
        "built, or calls sold into strength before a roll.")

# The §C.1 verdict words, banned from this object at any size, in any field.
# `regime` is the exception that proves the rule: AMPLIFIED-UP / AMPLIFIED-DOWN
# are inherited STATE NAMES the engine already computes, published as named
# facts with tag "I" -- not a verdict this object reached. STRONG BULL is a
# verdict, and that ban is already paid for once.
BANNED_WORDS = ("BULL", "BEAR", "MIXED", "LEAN", "BIAS", "VERDICT")

_SIDES = ("ce", "pe")


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _ends(minutes, now_hhmm, window_min):
    """(t0, t1) -- both real marks, never an interpolation. t1 is the last
    mark at or before the clock; t0 is the last mark at or before
    t1 - window_min."""
    marks = [m for m in sorted(minutes or {}) if not now_hhmm or m <= now_hhmm]
    if not marks:
        return None, None
    t1 = marks[-1]
    want = _mins(t1) - window_min
    earlier = [m for m in marks if _mins(m) <= want]
    return (earlier[-1] if earlier else None), t1


def _pair(rec, k, side):
    p = (rec.get("k") or {}).get(k)
    if p is None:
        return None
    v = p[0] if side == "ce" else p[1]
    return None if v is None else float(v)


def _px(rec, k, side):
    p = (rec.get("px") or {}).get(k)
    if p is None:
        return None
    v = p[0] if side == "ce" else p[1]
    return None if v is None else float(v)


def _peak_chg(minutes, k, side, upto):
    best = None
    for m in sorted(minutes or {}):
        if upto is not None and m > upto:
            break
        v = _pair(minutes[m] or {}, k, side)
        if v is None:
            continue
        if best is None or abs(v) > abs(best):
            best = v
    return best


def _fut(bars, t0_ms=None):
    """(d_oi, d_px) over the bars given. `oi` and `c`/`o` are the tape's own
    futures fields, the same two frame._trapped reads."""
    rows = [b for b in bars or [] if isinstance(b, dict)]
    if len(rows) < 2:
        return None, None
    a, b = rows[0], rows[-1]
    if a.get("oi") is None or b.get("oi") is None:
        return None, None
    if a.get("o") is None or b.get("c") is None:
        return None, None
    return int(b["oi"]) - int(a["oi"]), round(float(b["c"]) - float(a["o"]), 1)


def build(minutes, fut_bars, watched_strikes, regime, pinned, now_hhmm,
          window_min: int = WINDOW_MIN) -> dict:
    """The §D `breadth` object. `watched_strikes` is [(strike, "ce"|"pe")]."""
    t0, t1 = _ends(minutes, now_hhmm, window_min)
    out = {"window_min": window_min, "t0": t0, "t1": t1,
           "written_ce": None, "unwound_ce": None,
           "written_pe": None, "unwound_pe": None,
           "strikes_seen": 0, "counts_why": None,
           "concentration_top1": None, "concentration_top3": None,
           "concentration_why": None,
           "advancing": None, "retreating": None, "fronts_seen": 0,
           "fronts_why": None,
           "pressed": None, "bought": None, "premium_why": None,
           "fut_oi_day": None, "fut_px_day": None,
           "fut_oi_window": None, "fut_px_window": None, "fut_why": None,
           "regime": regime, "pinned": pinned, "regime_tag": "I",
           "regime_why": None if regime else "the engine has not published a regime",
           "backfill_minutes": 0, "tag": "M", "note": NOTE}

    if t0 is None or t1 is None or t0 == t1:
        out["counts_why"] = "fewer than two chain marks in the window"
        out["concentration_why"] = out["counts_why"]
        out["fronts_why"] = out["counts_why"]
        out["premium_why"] = out["counts_why"]
    else:
        a, b = minutes[t0] or {}, minutes[t1] or {}
        ks = sorted(set((a.get("k") or {})) & set((b.get("k") or {})))
        counts = {"written_ce": 0, "unwound_ce": 0, "written_pe": 0, "unwound_pe": 0}
        pressed = bought = 0
        for k in ks:
            for side in _SIDES:
                v0, v1 = _pair(a, k, side), _pair(b, k, side)
                if v0 is None or v1 is None:
                    continue
                d = v1 - v0
                if d > 0:
                    counts[f"written_{side}"] += 1
                    p0, p1 = _px(a, k, side), _px(b, k, side)
                    if p0 is not None and p1 is not None:
                        if p1 < p0:
                            pressed += 1      # writers pressing
                        elif p1 > p0:
                            bought += 1       # buyers building
                elif d < 0:
                    counts[f"unwound_{side}"] += 1
        out.update(counts)
        out["strikes_seen"] = len(ks)
        out["pressed"], out["bought"] = pressed, bought
        if not ks:
            out["counts_why"] = "no strike present at both ends of the window"
            out["premium_why"] = out["counts_why"]
            out["pressed"] = out["bought"] = None
            for key in counts:
                out[key] = None

        # concentration is the DAY's absolute change, not the window's: one
        # wall or a curtain is a session-shaped question.
        day = sorted((abs(_pair(b, k, s) or 0.0) for k in (b.get("k") or {})
                      for s in _SIDES), reverse=True)
        tot = sum(day)
        if tot:
            out["concentration_top1"] = round(day[0] / tot, 2)
            out["concentration_top3"] = round(sum(day[:3]) / tot, 2)
        else:
            out["concentration_why"] = "no absolute OI change on any strike yet"

        adv = ret = seen = 0
        for k, side in watched_strikes or []:
            pk = _peak_chg(minutes, k, side, t1)
            now = _pair(b, k, side)
            then = _pair(a, k, side)
            if not pk or now is None:
                continue
            seen += 1
            frac = 1.0 - (now / pk)
            if frac >= RETREATING_FRAC:
                ret += 1
            elif frac < ADVANCING_FRAC and then is not None and now > then:
                adv += 1
        out["fronts_seen"] = seen
        if seen:
            out["advancing"], out["retreating"] = adv, ret
        else:
            out["fronts_why"] = "no watched strike has a peak to measure from"

        out["backfill_minutes"] = sum(
            1 for m in sorted(minutes) if t0 <= m <= t1
            and (minutes[m] or {}).get("src") == "backfill")

    d_oi, d_px = _fut(fut_bars)
    out["fut_oi_day"], out["fut_px_day"] = d_oi, d_px
    span = max(1, window_min // 5)
    w_oi, w_px = _fut((fut_bars or [])[-(span + 1):])
    out["fut_oi_window"], out["fut_px_window"] = w_oi, w_px
    if d_oi is None:
        out["fut_why"] = "no futures OI on the joined bars"
    return out
