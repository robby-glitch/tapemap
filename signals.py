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

from typing import List, Optional

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
