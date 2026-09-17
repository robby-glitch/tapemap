# tapemap/signals.py
"""signals.py -- THE BALLOT, AND THE ONE VERB. Pure, stdlib only, no I/O, no clock.

WHY THIS IS NOT IN frame.py (spec §A.9.1). frame.py's own docstring says an
object that quietly measured would be the one defect its composition test
exists to catch. The ballot measures, so it lives here and frame.py composes
the answer.

THIS MODULE NEVER RECEIVES `walls.rows` (spec §B.1, §H.1). The most likely way
this whole layer makes the operator worse is the watch list turning into an
entry list: four flags on a wall reads like a setup. The guardrail is in the
SIGNATURE, not in discipline -- there is no `walls_rows` parameter. `oi_rows`
accepts CE and PE rows only, and `_only_oi` raises on anything else, so a
prior-day level or a tape wall cannot originate a signal. It can vote; it can
never be the reason.

THE THRESHOLD IS ONE MEASURED VOTE, AND IT MAY NOT BE OI (spec §A.4). Some gate
beat no gate on the only sample that exists; a second stacked gate bought
nothing. OI is excluded from counting alone because it is true on most visits
where it is measurable -- background, not a filter -- and it is the only
inferred vote on the ballot.

THREE ANSWERS, NEVER TWO. `ok: True` met, `ok: False` checked and not met,
`ok: None` COULD NOT CHECK with `why` printed. A null vote never counts for or
against, and the card reads "2 of 3 measurable - depth not answered".

BACKFILLED EVIDENCE IS SHOWN AND NEVER COUNTED. The anytime-start rule applied
to the ballot: a reconstructed morning may be drawn, but only what the brain
watched happen rings a bell.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import visit as visit_mod

# JUDGEMENT CALL (spec §F): chosen off the six-day bucket table, not off taste.
# KILL: at n = 30 fired signals -- sides reported separately, never merged --
# if the +6-bar excursion of fired visits does not exceed the bare-reach
# control by one standard deviation of the control's own +6-bar distribution,
# the ballot is deleted, the signal fires on the reach alone, and the card
# says so.
THRESHOLD = 1

# OI never alone. JUDGEMENT CALL (spec §F), folded into the per-vote kill
# clock: at n = 30, any vote whose present-population +6-bar excursion does not
# exceed its absent-population by one sd is dropped from the ballot and demoted
# to a printed fact. DEPTH ships with that clock already running and is the
# first candidate to go.
MEASURED_KEYS = ("wall", "event", "depth")

# JUDGEMENT CALL (spec §F, the DEPTH vote): the two thresholds the sweep read
# is gated on. KILL: the per-vote clock above, n = 30.
DEPTH_RATIO = 1.5
DEPTH_MIN_SWEEPS = 5

EDGE_ROWS = 3                    # the existing CONFIRMS grammar: 3 x tape.rowSize
CONFIRMS = ("absorption", "exhaustion", "trap")
INITIATIVE = ("initiative",)
_OI_KINDS = ("CE", "PE")


def _hhmm(t_ms: int) -> str:
    s = (t_ms // 1000 + 19800) % 86400
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"


def _only_oi(oi_rows) -> List[dict]:
    """§H.1 in code. A row that is not a CE or PE strike has no business on
    this ballot and raises rather than quietly becoming a vote."""
    out = []
    for r in oi_rows or []:
        if not isinstance(r, dict):
            continue
        if r.get("kind") not in _OI_KINDS:
            raise ValueError(
                f"signal.votes takes OI rows only; got kind={r.get('kind')!r}. "
                "walls.rows never enters this module (spec §B.1, §H.1).")
        out.append(r)
    return out


def _item(key, ok, t=None, p=None, src=None, why=None, tag="M", label=None) -> dict:
    return {"key": key, "ok": ok, "t": t, "p": p, "src": src, "why": why,
            "tag": tag, "label": label}


def _within(v: dict, t: str) -> bool:
    """Is this clock label inside the visit? At or after the reach, and at or
    before the end when the visit has one."""
    if t is None or t < v["reached_at"]:
        return False
    return v["ended_at"] is None or t <= v["ended_at"]


def _pocket(side: str, bn: dict):
    """(lo, hi, edge) of the pocket: [d3, d2] buy, [u2, u3] sell."""
    if side == "sell":
        return bn.get("u2"), bn.get("u3"), bn.get("u2")
    return bn.get("d3"), bn.get("d2"), bn.get("d2")


def _wall_vote(tape, side, v, bn, row) -> dict:
    """A tape wall of the setup's side, still standing, priced inside the
    pocket or within 3 rows of the edge, built during this visit.

    `snapshot` is the tape's own word for a wall that was already there when
    the extension started looking -- not watched being built -- so it is
    `src: "backfill"` and does not count."""
    lo, hi, e = _pocket(side, bn)
    if lo is None or hi is None or e is None:
        return _item("wall", None, why="no bands; the pocket has no edges")
    want = -1 if side == "sell" else 1
    best = None
    for w in tape.get("walls") or []:
        if not isinstance(w, dict) or w.get("price") is None:
            continue
        if (w.get("side") or 0) * want <= 0:
            continue
        p = float(w["price"])
        if not (lo <= p <= hi or abs(p - e) <= EDGE_ROWS * row):
            continue
        since = w.get("since")
        if not isinstance(since, str) or not _within(v, since):
            continue
        if best is None or since < best.get("since"):
            best = w
    if best is None:
        return _item("wall", False,
                     why="no wall of this side at the edge this visit")
    return _item("wall", True, t=best["since"], p=float(best["price"]),
                 src="backfill" if best.get("snapshot") else "observed",
                 label=f"{'sell' if side == 'sell' else 'buy'} wall "
                       f"{float(best['price']):,.0f} built during this visit")


def _event_vote(tape, side, v, bn, row) -> dict:
    """An initiative bar of the setup's side inside the pocket +/- 3 rows, or
    absorption / exhaustion / trap within 3 rows of the edge. A tape event
    carries a `side` only sometimes; where it does it must match, and where it
    does not the kind alone decides and `label` says which."""
    lo, hi, e = _pocket(side, bn)
    if lo is None or hi is None or e is None:
        return _item("event", None, why="no bands; the pocket has no edges")
    want = -1 if side == "sell" else 1
    hit = None
    for ev in sorted((e2 for e2 in (tape.get("events") or [])
                      if isinstance(e2, dict) and e2.get("p") is not None
                      and e2.get("t") is not None),
                     key=lambda e2: e2["t"]):
        t = _hhmm(int(ev["t"]))
        if not _within(v, t):
            continue
        p, kind = float(ev["p"]), ev.get("kind")
        sd = ev.get("side")
        if kind in INITIATIVE:
            if sd is not None and sd * want <= 0:
                continue
            ok = (lo - EDGE_ROWS * row) <= p <= (hi + EDGE_ROWS * row)
        elif kind in CONFIRMS:
            ok = abs(p - e) <= EDGE_ROWS * row
        else:
            continue
        if ok:
            hit = (t, p, kind, sd)
            break
    if hit is None:
        return _item("event", False,
                     why="no initiative or absorption at the edge")
    t, p, kind, sd = hit
    sided = "" if sd is not None else " (the tape sent no side)"
    return _item("event", True, t=t, p=p, src="observed",
                 label=f"{kind} at {p:,.0f}{sided}")


def _depth_vote(sweeps, side, v) -> dict:
    """Futures depth sweeps over the visit's minutes, summed by side.

    A `senses` row is `{det, kind, side, qty, t, inst}` -- `det` is which
    detector spoke and `kind` is the Sweep's own word, so the rows wanted are
    `det == "sweep"` AND `kind == "swept"`. `t` is "HH:MM:SS"; the visit is
    keyed in minutes. A sweep's `side` is the [I] half of an otherwise [M] row
    (sweep.Sweep's docstring), which is why the COUNT gates it as well as the
    ratio -- one mis-sided interval cannot carry the vote."""
    rows = [r for r in sweeps or []
            if isinstance(r, dict) and r.get("det") == "sweep"
            and r.get("kind") == "swept" and isinstance(r.get("t"), str)
            and _within(v, r["t"][:5])]
    if not rows:
        end = v["ended_at"] or "now"
        return _item("depth", None,
                     why=f"no sweep rows for {v['reached_at']}-{end}")
    want = "sell" if side == "sell" else "buy"
    mine = [r for r in rows if r.get("side") == want]
    theirs = [r for r in rows if r.get("side") and r.get("side") != want]
    q_mine = sum(float(r.get("qty") or 0) for r in mine)
    q_theirs = sum(float(r.get("qty") or 0) for r in theirs)
    ok = len(mine) >= DEPTH_MIN_SWEEPS and q_mine >= DEPTH_RATIO * q_theirs
    if not ok:
        return _item("depth", False,
                     why=f"{len(mine)} {want} sweep(s); under the floor")
    return _item("depth", True, t=rows[-1]["t"][:5], src="observed",
                 label=f"{len(mine)} {want} sweeps against {len(theirs)}")


def _oi_vote(oi_rows, side, v, bn, backfill) -> dict:
    """Fresh writing on the side that pays for the fade, at or beyond the
    edge, with writers on the other side of it under water.

    Buy: fresh PUT writing at strikes at or under the edge (chg > 0, at least
    one of them with conf == "session" -- the ledger watched at least half of
    it build) AND put writers above the edge under water (pain > 0). Sell is
    the mirror on calls. Inherits trapped_inventory's [I] through `pain`."""
    _lo, _hi, e = _pocket(side, bn)
    if e is None:
        return _item("oi", None, tag="I", why="no bands; the edge has no price")
    rows = _only_oi(oi_rows)
    if not rows:
        return _item("oi", None, tag="I", why="the chain has not answered")
    want = "CE" if side == "sell" else "PE"
    legs = [r for r in rows if r.get("kind") == want and r.get("p") is not None]
    if not legs:
        return _item("oi", None, tag="I", why=f"no {want} strike on the ladder")
    beyond = [r for r in legs
              if (float(r["p"]) >= e if side == "sell" else float(r["p"]) <= e)]
    inside = [r for r in legs
              if (float(r["p"]) < e if side == "sell" else float(r["p"]) > e)]
    fresh = [r for r in beyond if (r.get("chg") or 0) > 0]
    watched = [r for r in fresh if r.get("conf") == "session"]
    hurt = [r for r in inside if (r.get("pain") or 0) > 0]
    if not (fresh and watched and hurt):
        return _item("oi", False, tag="I",
                     why="no fresh watched writing with trapped writers")
    top = max(watched, key=lambda r: float(r.get("chg") or 0))
    src = "backfill" if backfill else "observed"
    return _item("oi", True, t=v["reached_at"], p=float(top["p"]), src=src, tag="I",
                 label=f"fresh {want} writing beyond the edge; "
                       f"{want} writers inside it under water")


def votes(tape: dict, oi_rows, sweeps, side: str, v: dict,
          oi_backfill: bool = False) -> dict:
    """The §D `votes` object. `v` is a `visit.current(...)` dict.

    NOTE THE SIGNATURE. There is no `walls_rows` parameter and there will not
    be one (spec §H.1). The tape's own walls arrive inside `tape`; the OI
    strikes arrive pre-filtered as `oi_rows`; nothing else about the ladder
    reaches this module."""
    bands = tape.get("bands") or []
    bn = bands[-1] if bands else {}
    row = float(tape.get("rowSize") or 5)
    items = [_wall_vote(tape, side, v, bn, row),
             _event_vote(tape, side, v, bn, row),
             _depth_vote(sweeps, side, v),
             _oi_vote(oi_rows, side, v, bn, oi_backfill)]
    counted = [i for i in items if i["ok"] is True and i["src"] != "backfill"]
    measured = [i for i in counted if i["key"] in MEASURED_KEYS]
    n = len(counted)
    passed = n >= THRESHOLD and bool(measured)
    why = None
    if not passed:
        why = ("one vote, and it is OI" if n and not measured
               else "no measured vote at the edge this visit")
    return {"n": n, "of": len(items),
            "measurable": sum(1 for i in items if i["ok"] is not None),
            "threshold": THRESHOLD, "passed": passed, "passed_why": why,
            "items": items}


# JUDGEMENT CALL (spec §F, inherited from the operator's own rule): the number
# of consecutive closes past the frozen price that count as falsified. KILL:
# it is her rule, not this module's, and it goes when she says so.
FALSIFIER_BARS = 3

# JUDGEMENT CALL (spec §A.6): how far the live band may walk from the frozen
# one before the card must print both numbers. KILL: if the card never prints
# two numbers across 30 sessions, the drift test is doing nothing and goes.
DRIFT_SIGMA = 0.25

_ACTIVE = ("ARMED", "TRIGGERED", "IN_TRADE")

EMPTY_VOTES = {"n": 0, "of": 4, "measurable": 0, "threshold": THRESHOLD,
               "passed": False, "passed_why": "the ballot did not build",
               "items": []}

EMPTY_SIGNAL = {
    "state": "PATA NAHI", "state_why": "the signal did not build",
    "side": "buy", "intent": "fade to VWAP", "not_a": None,
    "reached_at": None, "reached_at_why": "no visit to this pocket",
    "reached_provisional": False,
    "visit_key": None, "visit_ordinal": None, "in_window": False, "is_edge": False,
    "window": list(visit_mod.WINDOW),
    "armed_at": None, "ref_px": None, "candles_left": None,
    "candles_blind": False, "blind_since": None,
    "fired_at": None, "seen_at": None, "trigger_px": None,
    "target": None, "target_why": "no VWAP on the tape",
    "falsifier": None, "falsifier_why": "nothing to falsify before σ exists",
    "sound": None, "mute_why": "no visit to sound for",
    "out_of_method": True, "tag": "M"}


def _labels(tape) -> List[str]:
    return [lbl for lbl, _b, _bn in visit_mod._bars(tape)]


def _bar_at(tape, label) -> Optional[tuple]:
    """The tape bar carrying `label`, else the last one before it -- the two
    series do not share an axis, so this joins on the clock (see the module
    docstring of visit.py)."""
    hit = None
    for r in visit_mod._bars(tape):
        if r[0] <= label:
            hit = r
        else:
            break
    return hit


def _blind(tape, since_label, now_hhmm):
    """(blind, first_missing_minute). A hole in the tape's OWN timestamp
    series between `since_label` and the last closed bar means the close of a
    bar was never seen; a last close more than one interval behind the clock
    means the current bar is overdue. Spec §A.7 names `health.gaps` for this;
    no such field exists -- live.py's `gaps` is a list of missing session DAYS
    -- so the measurable equivalent is the tape itself."""
    closed = [b for b in (tape.get("closed") or [])
              if isinstance(b, dict) and b.get("t") is not None]
    if len(closed) < 2:
        return False, None
    iv = int(tape.get("interval") or 5) * 60000
    for a, b in zip(closed, closed[1:]):
        if visit_mod._hhmm(int(a["t"])) < since_label:
            continue
        if int(b["t"]) - int(a["t"]) > iv:
            return True, visit_mod._hhmm(int(a["t"]) + iv)
    last_close = visit_mod._hhmm(int(closed[-1]["t"]) + iv)
    if now_hhmm and now_hhmm > last_close:
        h1, m1 = (int(x) for x in last_close.split(":"))
        h2, m2 = (int(x) for x in now_hhmm.split(":"))
        if (h2 * 60 + m2) - (h1 * 60 + m1) > iv // 60000:
            return True, last_close
    return False, None


def _rows_in(zone_states, v) -> List[dict]:
    """The machine's rows belonging to this visit, joined on the clock."""
    out = []
    for zs in zone_states or []:
        if not isinstance(zs, dict):
            continue
        t = zs.get("t")
        if isinstance(t, str) and _within(v, t):
            out.append(zs)
    return out


def _falsifier(tape, side, v, interval):
    """FROZEN AT THE ARM BAR (spec §A.6). `setup.falsifies` was a string
    rebuilt from the CURRENT band every frame, so the number she was shown at
    the arm was not the number being checked an hour later -- the band moves
    with VWAP all session. This freezes the arm bar's own d3 / u3 and prints
    when the live band has walked more than DRIFT_SIGMA away from it."""
    hit = _bar_at(tape, v["reached_at"])
    if hit is None or not hit[2]:
        return None, "no band under the arm bar"
    bn0 = hit[2]
    px = bn0.get("u3") if side == "sell" else bn0.get("d3")
    if px is None:
        return None, "the arm bar's band has no 3σ edge"
    bands = tape.get("bands") or []
    live = bands[-1] if bands else {}
    now = live.get("u3") if side == "sell" else live.get("d3")
    s = live.get("sigma") or bn0.get("sigma")
    drifted = bool(now is not None and s and abs(float(now) - float(px)) > DRIFT_SIGMA * float(s))
    mins = interval // 60000
    return {"px": round(float(px), 1),
            "rule": f"a {mins}-minute close past {float(px):,.0f} held for "
                    f"{FALSIFIER_BARS} bars",
            "frozen_at": v["reached_at"], "drifted": drifted,
            "live_px": None if now is None else round(float(now), 1)}, None


def _state(tape, zone_states, side, v, passed):
    """WATCHING -> REACHED -> ARMED -> LIVE -> SPENT | STOPPED, with VOID off
    ARMED. Every transition is read off run_states or off a printed bar; none
    is invented here. BLIND holds the state rather than advancing it."""
    rows = _rows_in(zone_states, v)
    armed = [r for r in rows if r.get("ref_i") is not None or r.get("arm")]
    fired = next((r for r in rows if r.get("entry")), None)
    if fired is not None and passed:
        return "LIVE", fired, armed
    if armed:
        last = rows[-1] if rows else None
        if last is not None and last.get("state") == "WAITING" and fired is None:
            return "VOID", None, armed
        return "ARMED", fired, armed
    return "REACHED", None, armed


def _after_fire(tape, side, fired_label, vwap, fpx):
    """SPENT when a bar touches VWAP; STOPPED when the frozen falsifier is hit
    on FALSIFIER_BARS consecutive closes. Both read off printed bars."""
    run = 0
    for label, bar, _bn in visit_mod._bars(tape):
        if label <= fired_label:
            continue
        if vwap is not None and bar.get("h") is not None and bar.get("l") is not None:
            if float(bar["l"]) <= float(vwap) <= float(bar["h"]):
                return "SPENT", label
        c = bar.get("c")
        if fpx is not None and c is not None:
            past = float(c) > float(fpx) if side == "sell" else float(c) < float(fpx)
            run = run + 1 if past else 0
            if run >= FALSIFIER_BARS:
                return "STOPPED", label
    return None, None


def build(tape: dict, zone_states, side: str, oi_rows, sweeps, now_hhmm: str,
          oi_backfill: bool = False) -> Tuple[dict, dict]:
    """(signal, votes) for the visit in play. Pure; `now_hhmm` is passed in.

    THE `fire` CHAIN-CONFIRM TERM IS GONE (spec §A.5). `_book_for` passes
    `senses: None` on every request, so `confirm` was permanently "not wired"
    and the term was a no-op wearing a gate's clothes. On a single index series
    the pair-rotation confirm is structurally UNKNOWN
    (band_rotation.SINGLE_SERIES_CONFIRM_WHY) and always will be. It stays on
    the frame as a printed field with its reason; it stops pretending to gate.
    """
    bands = tape.get("bands") or []
    bn = bands[-1] if bands else None
    v = visit_mod.current(tape, zone_states if isinstance(zone_states, list) else [], side)
    if v is None or not bn or not bn.get("sigma"):
        why = ("no bands on the tape yet" if not bn or not bn.get("sigma")
               else "no visit to this pocket")
        return dict(EMPTY_SIGNAL, side=side, state_why=why[:48],
                    not_a="outright short" if side == "sell" else None), dict(EMPTY_VOTES)

    o = votes(tape, oi_rows, sweeps, side, v, oi_backfill)
    state, fired, armed = _state(tape, zone_states, side, v, o["passed"])
    interval = int(tape.get("interval") or 5) * 60000
    fal, fal_why = _falsifier(tape, side, v, interval)

    fired_at = fired.get("t") if fired else None
    trigger_px = None
    if fired is not None:
        hit = _bar_at(tape, fired_at) if isinstance(fired_at, str) else None
        trigger_px = None if hit is None else hit[1].get("c")
    if state == "LIVE" and fired_at:
        after, _at = _after_fire(tape, side, fired_at, bn.get("vwap"),
                                 None if fal is None else fal["px"])
        state = after or state

    blind, blind_since = _blind(tape, v["reached_at"], now_hhmm)
    left = None
    for r in _rows_in(zone_states, v):
        if r.get("candles_left") is not None:
            if blind and blind_since is not None and isinstance(r.get("t"), str) \
                    and r["t"] >= blind_since:
                break          # candles are not counted blind (spec §A.7)
            left = r["candles_left"]

    # `seen_at` is `fired_at` unless the trigger bar sat inside a hole, in
    # which case the brain first saw it on the next bar that actually printed.
    seen_at = fired_at
    if fired_at and blind and blind_since is not None and blind_since <= fired_at:
        later = [l for l in _labels(tape) if l > fired_at]
        seen_at = later[0] if later else now_hhmm

    sound, mute = _sound(v, o, state, fired_at, seen_at)
    armed_at = armed[0].get("t") if armed else None
    ref_px = next((r.get("ref_low" if side == "sell" else "ref_high")
                   for r in armed if r.get("ref_low" if side == "sell" else "ref_high")
                   is not None), None)
    vwap = bn.get("vwap")
    s = {"state": state, "state_why": None,
         "side": side, "intent": "fade to VWAP",
         "not_a": "outright short" if side == "sell" else None,
         "reached_at": v["reached_at"], "reached_at_why": None,
         "reached_provisional": v["reached_provisional"],
         "visit_key": v["visit_key"], "visit_ordinal": v["visit_ordinal"],
         "in_window": v["in_window"], "is_edge": v["is_edge"],
         "window": v["window"],
         "armed_at": armed_at, "ref_px": ref_px,
         "candles_left": left, "candles_blind": blind, "blind_since": blind_since,
         "fired_at": fired_at, "seen_at": seen_at, "trigger_px": trigger_px,
         "target": None if vwap is None else round(float(vwap), 1),
         "target_why": None if vwap is not None else "no VWAP on the tape",
         "falsifier": fal, "falsifier_why": fal_why,
         "sound": sound, "mute_why": mute,
         "out_of_method": not v["is_edge"], "tag": "M"}
    return s, o


def _sound(v, o, state, fired_at, seen_at):
    """TWO SOUNDS, AND NOTHING ELSE (spec §A.8). The mute is on `is_edge`, not
    on the ballot -- which is what actually bounds frequency: at most two
    signals per index per session can sound, by construction, whatever the
    threshold is. The threshold controls what is DRAWN; the window controls
    what is HEARD."""
    if not v["in_window"]:
        return None, f"{v['reached_at']} - outside "\
                     f"{visit_mod.WINDOW[0]}-{visit_mod.WINDOW[1]}"
    if not v["is_edge"]:
        return None, f"visit {v['visit_ordinal']} - not your edge"
    if state == "LIVE":
        if not o["passed"]:
            return None, o["passed_why"]
        if fired_at and seen_at and seen_at != fired_at:
            return "soft", None      # rebuilt from REST; the brain did not see it
        return "firm", None
    if state in ("REACHED", "ARMED"):
        return "soft", None
    return None, f"{state.lower()} - nothing left to ring"
