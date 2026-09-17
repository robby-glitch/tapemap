# tapemap/visit.py
"""visit.py -- ONE VISIT TO A POCKET, LATCHED. Pure, stdlib only, no I/O, no clock.

THE DEFECT THIS FIXES (spec §A.9.4). `frame._setup` keyed the visit on
`zone_state[i].ref_i`, the machine's LIVE reference bar. `run_states` branch 3
MOVES that reference every time a new lower low prints, and §5c defines a run
of falling lows as ONE setup -- so the key was rewritten mid-visit and the
decision record got two rows for one setup. `run_states` publishes
`arm.first_i` / `arm.first_t` for exactly this reason; this module reads those.

REACHED IS LATCHED (spec §A.2). `setup.reached` was `in_buy or in_sell or
machine active` -- a LIVE-PRICE test that goes false the moment price leaves
the pocket. That reads the ARM, not the REACH, and it is the 09:45 failure the
verdict caught. Once a bar of this visit has touched the near edge the reach is
a printed fact and never moves again for the life of that visit.

THE ZONE RULE IS THE REACH. `live.py` runs the machine with `band="d2"` (buy) /
`"u2"` (sell) -- the §1b zone rule, reaching the near edge IS the event -- so
`run_states` branch 4's touch test IS the reach test, already measured, once.
When the machine has answered this module does not re-test the touch: a second
copy of that comparison in another file is precisely the drift
`band_rotation`'s own docstring warns about twice. The bare touch scan below is
the FALLBACK for when no machine answered at all, and it is the same rule read
off each bar's own band row.

WHEN A VISIT ENDS. Spec §A.3 says "a bar closes on the VWAP side of the near
edge by more than 0.5 sigma, or 15:30". Measured against the real 2026-09-11
session, applying that bare ends the 09:25 visit at 09:30 while the machine is
still ARMED off that same reference through 09:55 -- which would split one
setup in two, the very defect above. So the rule is FLOORED at the bar the
machine let the setup go (its first WAITING row after the arm: no reference,
no lock). The machine owns "is this setup still alive"; the 0.5 sigma rule only
decides when a setup the machine has ALREADY dropped counts as a new visit on
re-entry.

TWO SERIES, JOINED BY THE CLOCK AND NEVER BY THE INDEX. `zone_states` is built
on the SERVER's payload bars (`band_rotation.SCORED_INTERVAL` = 3) and
`tape["closed"]` is the GoCharting extension's own series (5-minute in every
fixture). `arm.first_i` indexes the first, `closed[i]` the second; they are not
the same axis. Everything here joins on the "HH:MM" label.
"""
from __future__ import annotations

from typing import List, Optional

# JUDGEMENT CALL (spec §F): her stated edge, not a measured one.
# KILL: at n = 30 signals, if `is_edge` visits do not exceed non-edge visits by
# one standard deviation at +6 bars, the mute rule is wrong, the window goes,
# and every visit sounds.
WINDOW = ("09:45", "13:15")

# JUDGEMENT CALL (spec §F): a re-entry rule was needed and no evidence exists
# either way. KILL: if the ordinals this produces disagree with the operator's
# own count of visits on 10 sessions, the rule goes.
END_SIGMA = 0.5

SESSION_END = "15:30"


def _hhmm(t_ms: int) -> str:
    """Epoch ms -> IST "HH:MM". A two-line copy of `frame._hhmm`; importing
    frame here would be a cycle, since frame imports this module."""
    s = (t_ms // 1000 + 19800) % 86400
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"


def _bars(tape: dict) -> List[tuple]:
    """[(label, bar, band)] over the tape's own closed series, in order. The
    band row is the one printed UNDER that bar, never the current one."""
    closed, bands = tape.get("closed") or [], tape.get("bands") or []
    out = []
    for i, b in enumerate(closed):
        if not isinstance(b, dict) or b.get("t") is None:
            continue
        out.append((_hhmm(int(b["t"])), b, bands[i] if i < len(bands) else None))
    return out


def _edge(side: str, bn: Optional[dict]) -> Optional[float]:
    """The NEAR edge: d2 on a buy, u2 on a sell. Reaching it is the event."""
    if not bn:
        return None
    v = bn.get("u2") if side == "sell" else bn.get("d2")
    return float(v) if v is not None else None


def _touched(side: str, bar: dict, bn: Optional[dict]) -> bool:
    e = _edge(side, bn)
    if e is None:
        return False
    x = bar.get("h") if side == "sell" else bar.get("l")
    if x is None:
        return False
    return float(x) >= e if side == "sell" else float(x) <= e


def _left(side: str, bar: dict, bn: Optional[dict]) -> bool:
    """A close on the VWAP side of the near edge by more than END_SIGMA."""
    e, s, c = _edge(side, bn), (bn or {}).get("sigma"), bar.get("c")
    if e is None or not s or c is None:
        return False
    c, s = float(c), float(s)
    return c < e - END_SIGMA * s if side == "sell" else c > e + END_SIGMA * s


def _fresh_arms(zone_states, side: str) -> List[str]:
    """Every SETUP this machine opened, by its first arm's clock.

    Deduplicating on `first_t` is the whole fix: a re-arm (branch 3) carries
    the first arm's `first_t`, so it lands on a label already seen and adds
    nothing. `side` is not read -- the caller passes the machine for the side
    it wants -- and is in the signature so a reader cannot mistake which list
    this walked."""
    seen, out = set(), []
    for zs in zone_states or []:
        if not isinstance(zs, dict):
            continue
        a = zs.get("arm")
        if not isinstance(a, dict):
            continue
        ft = a.get("first_t")
        if not isinstance(ft, str) or ft in seen:
            continue
        seen.add(ft)
        out.append(ft)
    return sorted(out)


def _let_go(zone_states, ft: str) -> Optional[str]:
    """The label at which run_states dropped the setup that armed at `ft`:
    its first WAITING row afterwards -- no reference, no lock. None while the
    machine still holds it, and this module does not get to call a visit over
    while the machine that owns the rule disagrees."""
    i0 = None
    for i, zs in enumerate(zone_states or []):
        a = zs.get("arm") if isinstance(zs, dict) else None
        if isinstance(a, dict) and a.get("first_t") == ft:
            i0 = i
            break
    if i0 is None:
        return ft
    for zs in (zone_states or [])[i0 + 1:]:
        if isinstance(zs, dict) and zs.get("state") == "WAITING":
            t = zs.get("t")
            return t if isinstance(t, str) else ft
    return None


def _touch_starts(tape: dict, side: str) -> List[str]:
    """The FALLBACK reach scan, used only when no machine answered: the first
    bar of each contiguous run of bars that touched the near edge, read off
    each bar's own band row (spec §A.2)."""
    starts, prev = [], False
    for label, bar, bn in _bars(tape):
        hit = _touched(side, bar, bn)
        if hit and not prev:
            starts.append(label)
        prev = hit
    return starts


def _visit(side, at, ordinal, ended_at, ended_why, src, provisional=False) -> dict:
    in_window = WINDOW[0] <= at <= WINDOW[1]
    return {"side": side, "reached_at": at, "reached_provisional": provisional,
            "reached_src": src, "visit_key": f"{side}@{at}", "visit_ordinal": ordinal,
            "in_window": in_window, "is_edge": ordinal == 1 and in_window,
            "window": list(WINDOW), "ended_at": ended_at, "ended_why": ended_why}


def _assemble(tape, side, starts, src, zone_states=None) -> List[dict]:
    rows, out = _bars(tape), []
    for at in starts:
        if out and (out[-1]["ended_at"] is None or out[-1]["ended_at"] > at):
            continue                 # price never left: §A.3, still one visit
        floor = at if zone_states is None else _let_go(zone_states, at)
        ended_at = ended_why = None
        if floor is not None:
            for label, bar, bn in [r for r in rows if r[0] >= floor and r[0] > at]:
                if _left(side, bar, bn):
                    ended_at, ended_why = label, "closed 0.5σ back inside the edge"
                    break
            if ended_at is None and rows and rows[-1][0] >= SESSION_END:
                ended_at, ended_why = SESSION_END, "session closed"
        out.append(_visit(side, at, len(out) + 1, ended_at, ended_why, src))
    return out


def visits(tape: dict, zone_states, side: str) -> List[dict]:
    """Every visit of `side` this session, in order, ordinals assigned."""
    arms = _fresh_arms(zone_states, side)
    if arms:
        return _assemble(tape, side, arms, "arm", zone_states)
    return _assemble(tape, side, _touch_starts(tape, side), "touch")


def _provisional(tape: dict, side: str, ordinal: int) -> Optional[dict]:
    """THE INTRABAR LATCH (spec §A.2). The tape posts CLOSED bars; the forming
    bar rides under `forming` and is often null, in which case `futPx` IS that
    bar's last print. A live price inside the pocket has already printed the
    touch, and a printed low does not un-print -- so it latches now, stamped
    with the forming bar's own opening minute, and says it is provisional
    until that bar closes and the machine arms on it."""
    bands = tape.get("bands") or []
    bn = bands[-1] if bands else None
    if not bn or not bn.get("sigma"):
        return None
    lo, hi = bn.get("d3"), bn.get("d2")
    if side == "sell":
        lo, hi = bn.get("u2"), bn.get("u3")
    fm = tape.get("forming") if isinstance(tape.get("forming"), dict) else None
    x = (fm or {}).get("h" if side == "sell" else "l")
    if x is None:
        x = tape.get("futPx")
    if x is None or lo is None or hi is None:
        return None
    if not (float(lo) <= float(x) <= float(hi)):
        return None
    closed = tape.get("closed") or []
    if not closed or closed[-1].get("t") is None:
        return None
    iv = int(tape.get("interval") or 5) * 60000
    return _visit(side, _hhmm(int(closed[-1]["t"]) + iv), ordinal, None, None,
                  "forming", provisional=True)


def current(tape: dict, zone_states, side: str) -> Optional[dict]:
    """The visit in play, or None. An ENDED visit is never returned: the latch
    holds for the life of ONE visit, and that life is over."""
    vs = visits(tape, zone_states, side)
    live = [v for v in vs if v["ended_at"] is None]
    if live:
        return live[-1]
    return _provisional(tape, side, len(vs) + 1)
