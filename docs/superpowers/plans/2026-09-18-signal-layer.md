# The Signal Layer (brain side) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Four new pure stdlib modules — `visit.py`, `signals.py`, `watch.py`, `breadth.py` — plus one read-only route, so the frame publishes a latched, once-per-visit fade signal with a four-vote ballot, a watch list that is explicitly not an entry list, and a positioning-breadth object with no direction in it.

**Architecture:** Brain before face. `frame.py` stays composition-only — its own docstring says an object that quietly measured would be the one defect its composition test exists to catch, and the ballot measures — so every new computation lives in its own pure module with its own pytest, and `frame.py` only calls it, places the result, and states the absence. `band_rotation.run_states` is not touched: it already owns the two-candle rule, the 10-bar window and the re-arm rule, and a second copy of any of those in another file is the drift its own docstring warns about twice.

**Tech Stack:** Python 3.13, stdlib only (`json`, `typing`). pytest (`python -m pytest -q`). No new dependency, no new thread, no new file format, no new log.

## Global Constraints

- **Spec (binding):** `docs/superpowers/specs/2026-09-18-signal-layer-design.md`. Every §-reference below points into it. Where the spec names a field that does not exist under that name, this plan uses the real name and says so in the task — **the spec wins on intent, the real code wins on spelling.**
- **Scope is §G steps 1, 2, 3, 5 and 6 only.** §G steps 4 (`took`/`skipped`) and 7 (the Field marks) are **user-interface work and are NOT in this plan.** Do not write, modify or create any file under `ui/` or `chrome-ext/`, and no `.html`/`.css`/`.js`/`.mjs` anywhere. The last section of this plan is the handoff contract for whoever writes that UI plan.
- **Repo:** `C:\Users\kaam\Desktop\operator mode\tapemap`, branch `feature/operator-objects`. Every command below runs with that directory as cwd. The Python files sit directly in it (there is no `tapemap/tapemap/`).
- **THE SERVER IS LIVE ON PORT 8765.** Never start it, never stop it, never POST to it. `GET` against it is allowed and is how a route is smoke-tested. Python changes take effect only when the owner restarts after 15:30 IST, so a new route returns `404` against the live server and **that 404 is the expected result, not a failure.** `python -c "import server"` exiting 0 is the only import proof available before the restart.
- **Pre-existing test failures — DO NOT CHASE THEM.** `python -m pytest -q` reports `3 failed, 1115 passed` on this branch before any task here runs (measured 2026-09-18, 75 s). All three are in `test_desk_numbers.py`: `test_a_short_book_collects_theta_so_the_estimate_is_positive`, `test_a_long_book_pays_theta`, `test_a_leg_with_no_iv_is_named_not_silently_dropped`. Any task that says "only the 3 pre-existing failures" means exactly these three. They are not yours; do not open `desk.py`.
- **Absence grammar (house rule 6).** Three sentences, never one: checked and found nothing, could not check, not shown — they must never collapse into one rendering. Every published nullable field carries a sibling `*_why` of **at most 48 characters**, non-null exactly when the field is null. A missing value is never a zero, never a blank, never a default.
- **Tags.** Every published number is `"tag": "M"` measured or `"tag": "I"` inferred. Per-row tags (`pain_tag`, `fuel_tag`, `regime_tag`) follow the shape the existing objects already use.
- **NEVER print or compute** a hit rate, win rate, expectancy, probability, confidence score or payoff. **The 2026-09-16 study's numbers stay in the spec and never reach the code, a comment, a log line or a published field.** A comment may say "the six-day bucket table decided this" — it may not carry a percentage or an n.
- **No order path.** This stack is advisory and has never placed an order. Nothing here adds a side-effectful route; the only new route is a `GET`.
- **Judgement calls carry their kill in a comment.** Every threshold §F marks as a judgement call gets a module-level named constant with a comment saying it is a judgement call, naming its kill condition and its session count. No judgement threshold is inlined at a call site.
- **Route insertion point (Task 5):** insert the new `elif` **immediately above** the line
  `        elif self.path.startswith("/api/desk"):`
  — the only occurrence in `server.py` (line 1570 today; anchor on the string, never the number). The line directly above it is `            }).encode())`.
- **Route idioms, copy verbatim:** query = `q = parse_qs(urlsplit(self.path).query)`; index = `idx = self._idx()` (clamps to an enabled index); reply = `self._json(json.dumps({...}, default=str).encode())`.
- **Commit messages** end with the trailer:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- **Do not commit anything under `data/`.**

## File structure

| file | new? | owns |
|---|---|---|
| `visit.py` | **create** | one visit to a pocket: the latched reach, the key off `arm.first_t`, the ordinal, the window, the edge |
| `test_visit.py` | **create** | its pytest, pinned against the two real `.ofd.json` fixtures |
| `signals.py` | **create** | Task 2 the ballot; Task 3 the state machine, the frozen falsifier, blind candles, the two sounds |
| `test_signals.py` | **create** | its pytest |
| `watch.py` | **create** | the watch list: promotion, cap 8, six named flags, broken-and-remembered |
| `test_watch.py` | **create** | its pytest |
| `breadth.py` | **create** | positioning breadth, no direction field anywhere in the object |
| `test_breadth.py` | **create** | its pytest |
| `frame.py` | modify | Task 1 the visit block in `_setup`; Task 3 the `fire` chain-confirm term; Task 6 compose `setup.signal`, `setup.votes`, `walls.watch`, `breadth` |
| `frame_log.py` | modify | Task 3: `sig()` learns the signal state so a state transition forces a record append |
| `test_frame_log.py` | modify | Task 3: one new case |
| `server.py` | modify | Task 5 `GET /api/oihist`; Task 6 `_book_for` supplies sweeps, peaks, regime and the prior watch |
| `test_frame_zone.py` | modify | Task 1: one docstring. Task 3: the one test that pinned the confirm veto §A.5 deletes |

## Names the spec gets wrong, and the real ones

**Read this table before Task 1.** Every row was checked against the running code on 2026-09-18.

| §D / the spec says | the real thing | why |
|---|---|---|
| the module is called `signal.py` (§D) | it is called **`signals.py`** | **Measured, not theorised.** A file named `signal.py` at the repo root shadows Python's stdlib `signal` for everything launched from that directory, and **pytest itself will not start**: `anyio/abc/_eventloop.py` does `from signal import Signals`, which then resolves to the new file and raises `ImportError: cannot import name 'Signals'`. The whole suite dies at collection. One letter buys the name back; the published object stays `setup.signal`. |
| `signal.build(tape, bands_series, zone_states, walls_rows, sweeps, now_hhmm)` | `signals.build(tape, zone_states, side, oi_rows, sweeps, now_hhmm, oi_backfill=False)` | `bands_series` **is** `tape["bands"]`, already inside `tape`. `walls_rows` is forbidden by §H.1 — the parameter does not exist; `oi_rows` carries only the CE/PE rows the OI vote needs, and `signals.py` rejects anything else. `side` is `frame._pick_side`'s answer, passed in rather than re-derived. |
| `health.gaps` (§A.7) | a hole in `tape["closed"]`'s own timestamp series, plus a stale last close | `live.py`'s `gaps` is a list of missing **session days**, not minutes; no minute-gap field exists anywhere in this stack. The measurable equivalent is inside the tape itself. |
| "the forming bar's running low/high" (§A.2) | `tape["forming"]`, else `tape["futPx"]` | the tape doc carries a `forming` slot (`test_frame_zone.py:30` posts `"forming": None`). When it is null, `futPx` **is** that bar's last print. |
| `FLIP` (§B.2) | `GAMMA_FLIP` | `levels.py:120` emits `{"kind": "GAMMA_FLIP", ...}`. `frame._LEVEL_KINDS` spells it `FLIP`. Accept both. |
| `ChainState.peak` for `unwound_frac` (§C.2) | `ChainState.minutes` for `peak_chg`; `ChainState.peak` for `peak_oi` | `ChainState.peak[(k, side)]` is session-high **OI** with no minute attached (`chain_metrics.py:268`). `unwound_frac = 1 − chg_now / peak_chg` needs the **change** series and the minute it peaked on, and only `minutes` carries both. |
| `_book_for` should stop passing `senses: None` | `_book_for` gains `"sweeps"`; `"senses"` stays `None` | the `/api/senses` **reading** is assembled in the GET handler from `_SENSES["fuse"]` plus `_regime_engine_read`/`_walls_holding`, and `_book_for`'s own docstring forbids re-deriving it here. The DEPTH vote never needed that reading — only the raw sweep rows, which are `_SENSES["rows"]` filtered, no derivation at all. Two existing tests (`test_frame.py:126` and `:156`) pin `senses: None`'s honest absences; a new key keeps those true and still lets DEPTH be measured. |
| "a visit ends when a bar closes 0.5σ back inside" (§A.3) | that rule, **floored at the bar `run_states` let the setup go** | measured: applied bare against the real 2026-09-11 fixture it ends the 09:25 visit at 09:30 while the machine is still ARMED off that same reference through 09:55 — which would split one setup in two, the exact defect §A.9.4 exists to fix. The machine owns "is this setup still alive"; the 0.5σ rule only decides when a setup the machine has **already dropped** counts as a new visit on re-entry. |
| `zone_state[i]` and `tape.closed[i]` share an index | they do not | `zone_state` is built on the **server's** payload bars at `band_rotation.SCORED_INTERVAL = 3`; `tape.closed` is the GoCharting extension's own series (5-minute in every fixture). Join on the `"HH:MM"` label, never on `i`. |

---

## Task 1: `visit.py` — the latched reach, and the visit key off `arm.first_t`

**Goal:** one visit object per visit to a pocket, whose key is the setup's first arm so a re-arm can never split one setup into two record rows.

**Files:**
- Create: `visit.py`
- Create: `test_visit.py`
- Modify: `frame.py` (the visit block at the end of `_setup`, and one import)
- Modify: `test_frame_zone.py` (one docstring only — no assertion changes)

**Interfaces:**
- Produces: `visit.visits(tape: dict, zone_states: list, side: str) -> List[dict]` and `visit.current(tape: dict, zone_states: list, side: str) -> Optional[dict]`. A visit dict is
  `{"side", "reached_at", "reached_provisional", "reached_src", "visit_key", "visit_ordinal", "in_window", "is_edge", "window", "ended_at", "ended_why"}`.
  `visit.WINDOW == ("09:45", "13:15")`, `visit.END_SIGMA == 0.5`, `visit.SESSION_END == "15:30"`.
- Consumes: nothing from earlier tasks.

**Why this is first:** `frame._setup` keys the visit on `zone_state[i].ref_i`, the machine's **live** reference bar, which branch 3 of `run_states` moves on every new lower low — and §5c defines a run of falling lows as **one** setup. So the key changed mid-visit and the record got two rows for one setup. `run_states` publishes `arm.first_i` / `arm.first_t` precisely so that cannot happen.

- [ ] **Step 1: Write the failing test** — create `test_visit.py`:

```python
# tapemap/test_visit.py
"""visit.py: one visit to a pocket, latched (spec §A.2, §A.3).

Pinned against the same two recorded sessions test_frame_zone.py uses, plus
synthetic tapes for the pre-arm and intrabar paths. Nothing here is tuned:
every assertion follows from the rule as written, and the two fixture
numbers below were read off band_rotation.run_states itself.
"""
import json
import os

import band_rotation
import frame
import visit

FIX = r"C:\Users\kaam\Desktop\Go charting\orderflow-desk\test"


def _tape(day, upto_hhmm):
    """The same loader test_frame_zone.py uses: real bars, bands rebuilt from
    the running VWAP/sigma so the band under each bar is that bar's own."""
    j = json.load(open(os.path.join(FIX, f"session-{day}.ofd.json"), encoding="utf-8"))
    bars = sorted(j["bars"], key=lambda b: b["t"])
    bars = [b for b in bars if frame._hhmm(b["t"]) <= upto_hhmm]
    pv = pv2 = vv = 0.0
    bands = []
    for b in bars:
        tp = (b["h"] + b["l"] + b["c"]) / 3
        pv += tp * b["vol"]; pv2 += tp * tp * b["vol"]; vv += b["vol"]
        m = pv / vv; s = max(0.0, pv2 / vv - m * m) ** 0.5
        bands.append({"t": b["t"], "vwap": m, "sigma": s, "u1": m + s, "d1": m - s,
                      "u2": m + 2 * s, "d2": m - 2 * s, "u3": m + 3 * s, "d3": m - 3 * s})
    return {"kind": "frame", "session": f"NIFTY-I|5m|{day}", "idx": "NIFTY", "interval": 5,
            "rowSize": 5, "futPx": bars[-1]["c"], "closed": bars, "forming": None,
            "bands": bands, "walls": [], "broke": [], "events": [], "taps": []}


def _machine(tape, side="BUY", band="d2"):
    bars = [{"t": frame._hhmm(b["t"]), "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"],
             "vol": b["vol"], **{k: v for k, v in bd.items() if k != "t"}}
            for b, bd in zip(tape["closed"], tape["bands"])]
    return band_rotation.run_states(bars, stop_pts=band_rotation.OPERATOR_STOP_PTS,
                                    side=side, band=band)


def test_a_rearming_setup_is_one_visit_key_not_two():
    """THE DEFECT. On 2026-09-11 the buy machine arms at 09:25 and re-arms
    repeatedly down to the 09:55 trigger -- run_states' own re-arm rule, one
    setup. Keying on ref_i rewrote the key on every re-arm; keying on
    arm.first_t cannot."""
    t45, t50 = _tape("2026-09-11", "09:45"), _tape("2026-09-11", "09:50")
    v45 = visit.current(t45, _machine(t45), "buy")
    v50 = visit.current(t50, _machine(t50), "buy")
    assert v45["visit_key"] == v50["visit_key"] == "buy@09:25"
    assert v45["reached_at"] == "09:25" and v45["reached_src"] == "arm"
    assert len(visit.visits(t50, _machine(t50), "buy")) == 1


def test_the_reach_is_latched_and_does_not_go_false_when_price_leaves():
    """09:45 on 2026-09-11: the tap was at 09:25 and price is nowhere near
    d2 now. The visit is still the 09:25 one -- a printed low does not
    un-print. This is the 09:45 failure the verdict caught."""
    t = _tape("2026-09-11", "09:45")
    v = visit.current(t, _machine(t), "buy")
    bn = t["bands"][-1]
    assert not (bn["d3"] <= t["futPx"] <= bn["d2"]), "price is outside the pocket"
    assert v is not None and v["reached_at"] == "09:25"


def test_a_visit_the_machine_let_go_of_ends_and_the_next_touch_is_a_new_one():
    """2026-09-09 to 14:10: three separate buy setups (09:25, 09:45, 12:00),
    each dropped by the machine and then closed back inside; by 14:10 none is
    live, so there is no current visit at all."""
    t = _tape("2026-09-09", "14:10")
    vs = visit.visits(t, _machine(t), "buy")
    assert [v["visit_key"] for v in vs] == ["buy@09:25", "buy@09:45", "buy@12:00"]
    assert [v["visit_ordinal"] for v in vs] == [1, 2, 3]
    assert all(v["ended_at"] is not None for v in vs)
    assert visit.current(t, _machine(t), "buy") is None


def test_the_sell_side_is_the_same_machine_flipped():
    t = _tape("2026-09-11", "13:45")
    v = visit.current(t, _machine(t, "SELL", "u2"), "sell")
    assert v["visit_key"] == "sell@10:00" and v["side"] == "sell"


def test_window_and_edge_are_judged_on_reached_at():
    """09:25 is before the window opens, so the 2026-09-11 buy visit is not
    her edge however good it looks -- and 10:00 on the synthetic tape is."""
    t = _tape("2026-09-11", "09:45")
    v = visit.current(t, _machine(t), "buy")
    assert v["in_window"] is False and v["is_edge"] is False
    assert v["window"] == ["09:45", "13:15"]


def _synth(n=14):
    """A falling tape with a fixed band: bars 9..13 print lows at or under
    d2 = 23300, so the reach latches on bar 9 (10:00) and nothing after it
    closes 0.5 sigma back inside."""
    closed = [{"t": (1000 * 60 * 5 * i) + 1_780_026_340_000, "o": 23500 - 20 * i,
               "h": 23510 - 20 * i, "l": 23480 - 20 * i, "c": 23490 - 20 * i}
              for i in range(n)]
    bands = [{"vwap": 23400.0, "sigma": 50.0, "d2": 23300.0, "d3": 23250.0,
              "u2": 23500.0, "u3": 23550.0}] * n
    return {"session": "NIFTY-I|5m|2026-09-15", "idx": "NIFTY", "interval": 5,
            "rowSize": 5, "closed": closed, "bands": bands, "futPx": 23222.0,
            "forming": None}


def test_with_no_machine_the_reach_is_the_earliest_bar_of_the_touch_run():
    """No zone_state at all: the touch is still a printed fact, read off each
    bar's OWN band row, and it anchors on the FIRST bar of the run so the key
    does not drift bar to bar while the touch is still running."""
    v = visit.current(_synth(), [], "buy")
    assert v["visit_key"] == "buy@10:00" and v["reached_src"] == "touch"
    assert v["is_edge"] is True and v["reached_provisional"] is False


def test_the_intrabar_latch_is_provisional_until_the_bar_closes():
    """No closed bar has touched and no machine has armed, but the live price
    is inside the pocket -- so the reach latches NOW, stamped with the forming
    bar's own opening minute, and says it is provisional."""
    t = _synth(3)                      # 09:15, 09:20, 09:25; no low reaches 23300
    t["futPx"] = 23270.0               # inside [d3 23250, d2 23300]
    v = visit.current(t, [], "buy")
    assert v["reached_provisional"] is True and v["reached_src"] == "forming"
    assert v["reached_at"] == "09:30" and v["visit_key"] == "buy@09:30"


def test_a_forming_bars_running_low_beats_the_last_print_when_it_is_on_the_wire():
    t = _synth(3)
    t["futPx"] = 23400.0                          # back out of the pocket
    t["forming"] = {"o": 23400.0, "h": 23410.0, "l": 23280.0, "c": 23400.0}
    v = visit.current(t, [], "buy")
    assert v is not None and v["reached_provisional"] is True
    assert v["reached_at"] == "09:30"


def test_no_touch_no_machine_no_price_in_the_pocket_is_no_visit():
    t = _synth(3)
    t["futPx"] = 23450.0
    assert visit.current(t, [], "buy") is None
    assert visit.visits(t, [], "buy") == []
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_visit.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'visit'` (collection error, 0 tests run).

- [ ] **Step 3: Create `visit.py`**

```python
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
                    ended_at, ended_why = label, "closed 0.5\u03c3 back inside the edge"
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
```

- [ ] **Step 4: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_visit.py`
Expected: `9 passed`

- [ ] **Step 5: Point `frame._setup` at it**

In `frame.py`, find the import block:

```python
import gate as gate_mod
import structure   # prior_day_hlc: the payload's floor pivots inverted back to the prior session's H/L/C
```

and replace with:

```python
import gate as gate_mod
import structure   # prior_day_hlc: the payload's floor pivots inverted back to the prior session's H/L/C
import visit as visit_mod   # the latched reach and the visit key; frame.py composes, visit.py measures
```

Then find, at the end of `_setup`:

```python
    S["reached"], S["in_pocket"] = bool(in_buy or in_sell or machine in _ZONE_ACTIVE), bool(in_pocket)
    S["fire"] = S["reached"] and bool(flow) and confirm["value"] != "UNCONFIRMED"
    # visit is stable for the life of a visit: the machine's reference bar while it holds one, else the earliest bar
    # of the contiguous band-touch run, else today's last bar (frame.py stays stateless)
    if S["reached"] and closed:
        ref_i = last.get("ref_i") if last and machine in _ZONE_ACTIVE else None
        visit = None
        if ref_i is not None and 0 <= ref_i < len(closed):
            visit = f"{side}@{_hhmm(closed[ref_i]['t'])}"
        elif in_buy or in_sell:
            bands_list, key = tape.get("bands") or [], ("d2" if in_buy else "u2")

            def _touches(i):
                lvl = bands_list[i].get(key) if i < len(bands_list) else None
                return lvl is not None and (closed[i]["l"] <= lvl if in_buy else closed[i]["h"] >= lvl)
            i = len(closed) - 1
            if _touches(i):
                while i > 0 and _touches(i - 1):
                    i -= 1
                visit = f"{side}@{_hhmm(closed[i]['t'])}"
        S["visit"] = visit or f"{side}@{_hhmm(closed[-1]['t'])}"
    return S
```

and replace with:

```python
    # THE REACH IS LATCHED AND THE KEY IS `arm.first_t` (spec §A.2, §A.3, §A.9.4).
    # `reached` was a live-price test that went false the moment price left the pocket -- the
    # arm, not the reach -- and the key was `ref_i`, which branch 3 of run_states moves on
    # every new lower low, so one setup wrote two record rows. visit.py owns both rules now;
    # frame.py places the answer and measures nothing.
    zs = book.get("zone_state_sell") if use_sell else book.get("zone_state")
    v = visit_mod.current(tape, zs if isinstance(zs, list) else [], side)
    S["reached"], S["in_pocket"] = v is not None, bool(in_pocket)
    S["fire"] = S["reached"] and bool(flow) and confirm["value"] != "UNCONFIRMED"
    if v is not None:
        S["visit"] = v["visit_key"]
    elif closed:
        S["visit"] = None
    return S
```

- [ ] **Step 6: Update the one stale docstring in `test_frame_zone.py`**

No assertion changes — all five `S["reached"]` assertions and both `S["visit"]` assertions still hold (verified against the real fixtures on 2026-09-18). One docstring now describes a rule that is gone. Find:

```python
def test_0911_visit_is_the_earliest_bar_of_a_contiguous_d2_touch_run_before_arming():
    """Before the machine has armed a reference (state PATA NAHI / not yet
    active), a live d2 touch still needs a stable visit id: it anchors on the
    EARLIEST bar of the contiguous run of bars touching d2, not the latest,
    so the id does not drift bar to bar while the touch is still running.
    Built directly off the bands rather than the real machine, since this
    exercises the pre-arm fallback path specifically (no zone_state at all)."""
```

and replace with:

```python
def test_0911_visit_is_the_earliest_bar_of_a_contiguous_d2_touch_run_before_arming():
    """Before the machine has armed a reference (state PATA NAHI / not yet
    active), a live d2 touch still needs a stable visit id: it anchors on the
    EARLIEST bar of the contiguous run of bars touching d2, not the latest,
    so the id does not drift bar to bar while the touch is still running.
    Built directly off the bands rather than the real machine, since this
    exercises the pre-arm fallback path specifically (no zone_state at all).

    The rule lives in visit._touch_starts now (spec §A.2) rather than inline
    in frame._setup; the assertion is unchanged because the rule is."""
```

- [ ] **Step 7: Run the suite**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q 2>&1 | tail -6`
Expected: `3 failed, 1124 passed` — only the three pre-existing `test_desk_numbers.py` failures.

- [ ] **Step 8: Commit**

```bash
git add visit.py test_visit.py frame.py test_frame_zone.py
git commit -m "visit: latch the reach, key the visit on arm.first_t so a re-arm stops splitting one setup in two

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: `signals.py` — the ballot, threshold one measured vote, OI never alone

**Goal:** four votes with honest `null` semantics, a threshold of one measured vote that may not be OI, and backfilled evidence that is shown and never counted.

**Files:**
- Create: `signals.py`
- Create: `test_signals.py`

**Interfaces:**
- Consumes: `visit.current(...)` from Task 1 (a visit dict).
- Produces: `signals.votes(tape: dict, oi_rows: list, sweeps: list, side: str, v: dict, oi_backfill: bool = False) -> dict` returning the §D `votes` object. Constants `signals.THRESHOLD == 1`, `signals.MEASURED_KEYS == ("wall", "event", "depth")`, `signals.DEPTH_RATIO == 1.5`, `signals.DEPTH_MIN_SWEEPS == 5`, `signals.EDGE_ROWS == 3`.
- Task 3 adds `signals.build(...)` to this same file and calls `signal.votes` from it.

**The guardrail this task enforces (§H.1):** there is no parameter named `walls_rows` and there never will be. `oi_rows` takes CE/PE rows only and the function raises on anything else, so a ladder row cannot originate a signal — it can only vote, and its vote can never be the reason a bell rings.

- [ ] **Step 1: Write the failing test** — create `test_signals.py`:

```python
# tapemap/test_signals.py
"""signals.py: the ballot (spec §A.4), and the state machine (spec §A.2, §A.5-A.8).

Synthetic tape and book throughout: no recorded day is a target, and no
number from the 2026-09-16 study appears here or in the module.
"""
import pytest

import signals as sig
import visit


def _tape(n=14, fut=23270.0):
    closed = [{"t": (1000 * 60 * 5 * i) + 1_780_026_340_000, "o": 23500 - 20 * i,
               "h": 23510 - 20 * i, "l": 23480 - 20 * i, "c": 23490 - 20 * i}
              for i in range(n)]
    bands = [{"vwap": 23400.0, "sigma": 50.0, "d2": 23300.0, "d3": 23250.0,
              "u2": 23500.0, "u3": 23550.0}] * n
    return {"session": "NIFTY-I|5m|2026-09-15", "idx": "NIFTY", "interval": 5,
            "rowSize": 5, "closed": closed, "bands": bands, "futPx": fut,
            "forming": None, "walls": [], "broke": [], "events": [], "taps": []}


def _v(t):
    """The visit these votes are cast inside: buy@10:00, bar 9 of the tape."""
    v = visit.current(t, [], "buy")
    assert v is not None and v["visit_key"] == "buy@10:00"
    return v


def _wall(px=23290.0, since="10:05", snapshot=False):
    return {"price": px, "side": 1, "size": 400, "hits": 2, "since": since,
            "snapshot": snapshot}


def _sweeps(n_buy=6, n_sell=1, qty=100.0, t="10:05:10"):
    return ([{"det": "sweep", "kind": "swept", "side": "buy", "qty": qty, "t": t,
              "inst": "NIFTY-FUT"}] * n_buy
            + [{"det": "sweep", "kind": "swept", "side": "sell", "qty": qty, "t": t,
                "inst": "NIFTY-FUT"}] * n_sell)


def _oi(chg=1.0e6, pain=6.2, conf="session"):
    """One PE strike under the edge (fresh writing) and one above it (under
    water). Prices are in the futures frame, as frame._walls emits them."""
    return [{"kind": "PE", "p": 23280.0, "strike": 23250.0, "oi": 2.2e7, "chg": chg,
             "pain": 0.0, "pain_tag": "I", "conf": conf},
            {"kind": "PE", "p": 23360.0, "strike": 23330.0, "oi": 1.1e7, "chg": -1.0e5,
             "pain": pain, "pain_tag": "I", "conf": "low"}]


def test_a_single_measured_vote_passes_and_names_which():
    t = _tape(); t["walls"] = [_wall()]
    o = sig.votes(t, [], [], "buy", _v(t))
    assert o["n"] == 1 and o["threshold"] == 1 and o["passed"] is True
    assert o["passed_why"] is None and o["of"] == 4
    w = next(i for i in o["items"] if i["key"] == "wall")
    assert w["ok"] is True and w["src"] == "observed" and w["tag"] == "M"
    assert w["why"] is None and w["label"] and w["t"] == "10:05"


def test_no_votes_does_not_pass_and_says_so_in_one_clause():
    t = _tape()
    o = sig.votes(t, [], [], "buy", _v(t))
    assert o["n"] == 0 and o["passed"] is False
    assert o["passed_why"] and len(o["passed_why"]) <= 48


def test_oi_is_never_the_reason_on_its_own():
    """True on most visits where it is measurable -- background, not a filter,
    and the only inferred vote on the ballot. It adds weight and can never be
    the reason a sound happened (spec §A.4)."""
    t = _tape()
    o = sig.votes(t, _oi(), [], "buy", _v(t))
    oi = next(i for i in o["items"] if i["key"] == "oi")
    assert oi["ok"] is True and oi["tag"] == "I"
    assert o["n"] == 1 and o["passed"] is False
    assert o["passed_why"] == "one vote, and it is OI"


def test_oi_plus_one_measured_vote_passes():
    t = _tape(); t["walls"] = [_wall()]
    o = sig.votes(t, _oi(), [], "buy", _v(t))
    assert o["n"] == 2 and o["passed"] is True and o["passed_why"] is None


def test_a_null_vote_never_moves_n_and_prints_why_it_could_not_be_checked():
    t = _tape()
    o = sig.votes(t, [], [], "buy", _v(t))
    for key in ("depth", "oi"):
        it = next(i for i in o["items"] if i["key"] == key)
        assert it["ok"] is None and it["src"] is None
        assert it["why"] and len(it["why"]) <= 48
    assert o["measurable"] == 2 and o["n"] == 0


def test_a_checked_and_not_met_vote_is_false_not_null():
    """Three sentences, never one: found nothing is not could not check."""
    t = _tape()
    o = sig.votes(t, _oi(), _sweeps(n_buy=1, n_sell=9), "buy", _v(t))
    d = next(i for i in o["items"] if i["key"] == "depth")
    assert d["ok"] is False and d["why"] and o["measurable"] == 4


def test_the_depth_vote_needs_both_the_ratio_and_the_count():
    t = _tape()
    assert next(i for i in sig.votes(t, [], _sweeps(6, 1), "buy", _v(t))["items"]
                if i["key"] == "depth")["ok"] is True
    assert next(i for i in sig.votes(t, [], _sweeps(4, 0), "buy", _v(t))["items"]
                if i["key"] == "depth")["ok"] is False, "4 sweeps is under the floor"
    assert next(i for i in sig.votes(t, [], _sweeps(6, 5), "buy", _v(t))["items"]
                if i["key"] == "depth")["ok"] is False, "ratio under 1.5"


def test_a_backfilled_vote_is_shown_and_does_not_count():
    """The anytime-start rule applied to the ballot: a reconstructed morning
    may be drawn, but only what the brain WATCHED happen rings a bell."""
    t = _tape(); t["walls"] = [_wall(snapshot=True)]
    o = sig.votes(t, [], [], "buy", _v(t))
    w = next(i for i in o["items"] if i["key"] == "wall")
    assert w["ok"] is True and w["src"] == "backfill"
    assert o["n"] == 0 and o["passed"] is False


def test_evidence_from_before_the_reach_is_not_this_visits_evidence():
    t = _tape(); t["walls"] = [_wall(since="09:20")]
    o = sig.votes(t, [], [], "buy", _v(t))
    assert next(i for i in o["items"] if i["key"] == "wall")["ok"] is False


def test_a_wall_of_the_wrong_side_is_not_a_vote():
    t = _tape()
    t["walls"] = [dict(_wall(), side=-1)]
    o = sig.votes(t, [], [], "buy", _v(t))
    assert next(i for i in o["items"] if i["key"] == "wall")["ok"] is False


def test_an_event_four_rows_off_the_edge_is_not_a_vote():
    t = _tape()
    far = t["closed"][-1]["t"]
    t["events"] = [{"t": far, "kind": "absorption", "p": 23300.0 + 4 * 5}]
    assert next(i for i in sig.votes(t, [], [], "buy", _v(t))["items"]
                if i["key"] == "event")["ok"] is False
    t["events"] = [{"t": far, "kind": "absorption", "p": 23300.0 + 2 * 5}]
    assert next(i for i in sig.votes(t, [], [], "buy", _v(t))["items"]
                if i["key"] == "event")["ok"] is True


def test_the_ballot_refuses_anything_that_is_not_an_oi_row():
    """§H.1 enforced by the signature, not by discipline: a tape wall or a
    prior-day level handed in as an OI row is a bug, and it raises here rather
    than quietly becoming a vote."""
    t = _tape()
    with pytest.raises(ValueError):
        sig.votes(t, [{"kind": "PDH", "p": 23500.0}], [], "buy", _v(t))


def test_every_why_fits_on_the_card():
    t = _tape()
    o = sig.votes(t, [], [], "buy", _v(t))
    for it in o["items"]:
        assert it["why"] is None or len(it["why"]) <= 48
        assert (it["why"] is None) == (it["ok"] is True)
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_signals.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'signals'` (collection error, 0 tests run).

**Do not `touch signal.py` to "fix" this.** The plural is deliberate and the naming table at the top of this plan says why: a `signal.py` at the repo root stops `pytest` starting at all.

- [ ] **Step 3: Create `signals.py`**

```python
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
```

- [ ] **Step 4: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_signals.py`
Expected: `13 passed`

- [ ] **Step 5: Run the suite**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q 2>&1 | tail -6`
Expected: `3 failed, 1137 passed` — only the three pre-existing `test_desk_numbers.py` failures. If the run instead dies at collection with `ImportError: cannot import name 'Signals' from 'signal'`, a file called `signal.py` has appeared at the repo root: delete it, keep `signals.py`.

- [ ] **Step 6: Commit**

```bash
git add signals.py test_signals.py
git commit -m "signal: the four-vote ballot, threshold one measured vote, OI never alone, backfill shown and never counted

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: the state machine, the frozen falsifier, blind-safe candles, the two sounds

**Goal:** one `signal` object per visit that says which state it is in, what would falsify it (frozen at the arm bar), whether the candles are being counted blind, and which of the two sounds it deserves — and a record row a scorer can read the transition back out of.

**Files:**
- Modify: `signals.py` (append; no existing function changes)
- Modify: `test_signals.py` (append)
- Modify: `frame.py` (the `fire` term, one line)
- Modify: `frame_log.py` (`sig()`, one expression)
- Modify: `test_frame_log.py` (append one case)

**Interfaces:**
- Consumes: `signals.votes(...)` from Task 2, `visit.current(...)` from Task 1.
- Produces: `signals.build(tape, zone_states, side, oi_rows, sweeps, now_hhmm, oi_backfill=False) -> Tuple[dict, dict]` returning `(signal_obj, votes_obj)` matching §D. Constants `signals.FALSIFIER_BARS == 3`, `signals.DRIFT_SIGMA == 0.25`. Also `signals.EMPTY_SIGNAL` and `signals.EMPTY_VOTES`, the module-level empty shapes Task 6's `frame._safe` merges a `why` over.

- [ ] **Step 1: Write the failing tests** — append to `test_signals.py`:

```python
def _zs(rows):
    """A zone_state list at the payload's own 3-minute labels. `arm` is
    non-None only on arming bars, exactly as run_states emits it."""
    return rows


def _armed(first_t="10:00", state="ARMED", entry=None, left=3):
    return {"i": 0, "t": first_t, "state": state, "ref_i": 0, "ref_high": 23310.0,
            "level": 23300.0, "stop": None, "candles_left": left,
            "arm": {"rearm": False, "band": "d2", "extreme": 23290.0,
                    "first_i": 0, "first_t": first_t},
            "entry": entry, "exit_why": None, "readable": True}


def _after(t, state="ARMED", entry=None, left=2):
    return {"i": 1, "t": t, "state": state, "ref_i": 0, "ref_high": 23310.0,
            "level": 23300.0, "stop": None, "candles_left": left, "arm": None,
            "entry": entry, "exit_why": None, "readable": True}


def _entry(t="10:15"):
    return {"i": 1, "t": t, "side": "BUY", "leg": "index", "band": "d2",
            "trigger": "index low touched d2 23300 at 10:00, then closed 23320 "
                       "above that candle's high 23310 3 bars later",
            "also": None, "confirm": "UNKNOWN", "confirm_why": "single series",
            "trap": "UNKNOWN", "trap_why": "no index series", "trap_dwell": None,
            "ref_i": 0, "ref_high": 23310.0, "level": 23300.0, "waited": 3,
            "stop": None}


def test_a_reached_but_unarmed_visit_names_the_intent_and_the_target():
    t = _tape()
    s, o = sig.build(t, [], "buy", [], [], "10:10")
    assert s["state"] == "REACHED" and s["state_why"] is None
    assert s["visit_key"] == "buy@10:00" and s["is_edge"] is True
    assert s["side"] == "buy" and s["intent"] == "fade to VWAP" and s["not_a"] is None
    assert s["target"] == 23400.0 and s["target_why"] is None


def test_the_sell_side_says_what_it_is_not():
    t = _tape(fut=23520.0)
    for i, b in enumerate(t["closed"]):
        t["closed"][i] = dict(b, h=23520.0)           # every bar tags u2
    s, _o = sig.build(t, [], "sell", [], [], "10:10")
    assert s["side"] == "sell" and s["not_a"] == "outright short"
    assert s["intent"] == "fade to VWAP" and s["target"] == 23400.0


def test_armed_then_live_only_when_the_ballot_passes():
    t = _tape(); t["walls"] = [_wall()]
    zs = _zs([_armed(), _after("10:15", state="TRIGGERED", entry=_entry())])
    s, o = sig.build(t, zs, "buy", [], [], "10:20")
    assert o["passed"] is True and s["state"] == "LIVE"
    assert s["fired_at"] == "10:15" and s["trigger_px"] is not None
    t2 = _tape()                                       # no wall: no measured vote
    s2, o2 = sig.build(t2, zs, "buy", [], [], "10:20")
    assert o2["passed"] is False and s2["state"] == "ARMED"


def test_a_reference_that_expired_without_an_entry_is_void():
    t = _tape()
    zs = _zs([_armed(), _after("10:45", state="WAITING", left=None)])
    s, _o = sig.build(t, zs, "buy", [], [], "10:50")
    assert s["state"] == "VOID" and s["state_why"] is None


def test_the_falsifier_is_frozen_at_the_arm_bar_and_says_when():
    t = _tape()
    zs = _zs([_armed()])
    s, _o = sig.build(t, zs, "buy", [], [], "10:10")
    f = s["falsifier"]
    assert f["px"] == 23250.0 and f["frozen_at"] == "10:00" and f["drifted"] is False
    assert "5-minute close past 23,250" in f["rule"] and "3 bars" in f["rule"]


def test_the_falsifier_says_so_when_the_live_band_has_walked_away_from_it():
    t = _tape()
    t["bands"] = [dict(b) for b in t["bands"]]
    t["bands"][-1] = dict(t["bands"][-1], d3=23250.0 - 0.3 * 50.0)
    zs = _zs([_armed()])
    s, _o = sig.build(t, zs, "buy", [], [], "10:10")
    assert s["falsifier"]["drifted"] is True and s["falsifier"]["px"] == 23250.0


def test_candles_are_not_counted_blind():
    """A hole in the tape's own timestamp series between the arm bar and now
    means the close of a bar was never seen. candles_left HOLDS at its last
    seen value, candles_blind is true, and blind_since names the minute. The
    bars here are 5 minutes apart from 09:15, so dropping index 10 and 11
    removes 10:05 and 10:10 and the hole opens at 10:05."""
    t = _tape()
    t["closed"] = t["closed"][:10] + t["closed"][12:]
    zs = _zs([_armed(), _after("10:05", left=2)])
    s, _o = sig.build(t, zs, "buy", [], [], "10:30")
    assert s["candles_blind"] is True and s["blind_since"] == "10:05"
    assert s["candles_left"] == 3, "the 10:05 row's count was never seen"


def test_a_seen_signal_sounds_firm_and_an_unseen_one_sounds_soft():
    t = _tape(); t["walls"] = [_wall()]
    zs = _zs([_armed(), _after("10:15", state="TRIGGERED", entry=_entry())])
    s, _o = sig.build(t, zs, "buy", [], [], "10:20")
    assert s["state"] == "LIVE" and s["sound"] == "firm" and s["mute_why"] is None
    assert s["seen_at"] == s["fired_at"] == "10:15"
    # drop 10:10 and 10:15: the reach at 10:00 survives, the trigger bar does
    # not, so the brain did not watch it happen
    t2 = _tape(); t2["walls"] = [_wall()]
    t2["closed"] = t2["closed"][:11] + t2["closed"][13:]
    s2, _o2 = sig.build(t2, zs, "buy", [], [], "10:30")
    assert s2["state"] == "LIVE" and s2["candles_blind"] is True
    assert s2["sound"] == "soft" and s2["seen_at"] == "10:20" != s2["fired_at"]


def test_visit_two_draws_and_never_sounds():
    """The screen makes visit two attractive because it still draws
    beautifully (spec §H.7). It is grey, silent, tagged out_of_method so its
    rows can never pool with the edge population."""
    closed, bands = [], []
    # bars run 09:45 .. 10:20. The pocket is touched at 09:55, abandoned by the
    # 10:00 close (0.5 sigma back inside), and touched again at 10:15.
    lows = [23480, 23480, 23290, 23480, 23480, 23480, 23290, 23290]
    closes = [23470, 23470, 23300, 23340, 23470, 23470, 23300, 23300]
    for i, (lo, c) in enumerate(zip(lows, closes)):
        closed.append({"t": (1000 * 60 * 5 * i) + 1_780_026_340_000 + 1800000,
                       "o": 23470, "h": 23500, "l": lo, "c": c})
        bands.append({"vwap": 23400.0, "sigma": 50.0, "d2": 23300.0,
                      "d3": 23250.0, "u2": 23500.0, "u3": 23550.0})
    t = {"session": "NIFTY-I|5m|2026-09-15", "idx": "NIFTY", "interval": 5,
         "rowSize": 5, "closed": closed, "bands": bands, "futPx": 23290.0,
         "forming": None, "walls": [], "events": []}
    s, _o = sig.build(t, [], "buy", [], [], "10:30")
    assert s["visit_ordinal"] == 2 and s["is_edge"] is False
    assert s["sound"] is None and s["mute_why"] == "visit 2 - not your edge"
    assert s["out_of_method"] is True


def test_nothing_outside_the_window_ever_sounds():
    t = _tape(n=3, fut=23270.0)          # the provisional latch at 09:30
    s, _o = sig.build(t, [], "buy", [], [], "09:30")
    assert s["reached_at"] == "09:30" and s["in_window"] is False
    assert s["is_edge"] is False and s["sound"] is None
    assert s["mute_why"] == "09:30 - outside 09:45-13:15"
    assert s["out_of_method"] is True


def test_a_visit_with_no_bands_says_it_does_not_know():
    t = _tape(); t["bands"] = []
    s, o = sig.build(t, [], "buy", [], [], "10:10")
    assert s["state"] == "PATA NAHI" and s["state_why"] and len(s["state_why"]) <= 48
    assert o["n"] == 0


def test_every_nullable_field_has_its_why_and_no_why_exceeds_the_card():
    t = _tape()
    s, _o = sig.build(t, [], "buy", [], [], "10:10")
    for f, w in (("reached_at", "reached_at_why"), ("target", "target_why"),
                 ("falsifier", "falsifier_why")):
        assert (s[w] is not None) == (s[f] is None), f
        assert s[w] is None or len(s[w]) <= 48
    # state_why is the one exception the contract names: non-null exactly when
    # state is "PATA NAHI", not when state is null (it never is).
    assert (s["state_why"] is not None) == (s["state"] == "PATA NAHI")
    assert (s["mute_why"] is not None) == (s["sound"] is None)


def test_no_probability_word_reaches_the_object():
    import json as _json
    t = _tape(); t["walls"] = [_wall()]
    zs = _zs([_armed(), _after("10:15", state="TRIGGERED", entry=_entry())])
    s, o = sig.build(t, zs, "buy", [], [], "10:20")
    blob = _json.dumps([s, o]).lower()
    for banned in ("hit rate", "win rate", "expectancy", "probability",
                   "confidence", "%"):
        assert banned not in blob
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_signals.py`
Expected: FAIL — `AttributeError: module 'signals' has no attribute 'build'`, the 13 earlier cases still passing.

- [ ] **Step 3: Append to `signals.py`**

Add these imports at the top of `signals.py`, replacing:

```python
from typing import List, Optional
```

with:

```python
from typing import List, Optional, Tuple

import visit as visit_mod
```

Then append to the end of `signals.py`:

```python
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
    "falsifier": None, "falsifier_why": "nothing to falsify before \u03c3 exists",
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
        return None, "the arm bar's band has no 3\u03c3 edge"
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
```

- [ ] **Step 4: Delete the `fire` chain-confirm term in `frame.py`**

Find:

```python
    S["reached"], S["in_pocket"] = v is not None, bool(in_pocket)
    S["fire"] = S["reached"] and bool(flow) and confirm["value"] != "UNCONFIRMED"
```

and replace with:

```python
    S["reached"], S["in_pocket"] = v is not None, bool(in_pocket)
    # THE CHAIN-CONFIRM TERM IS DELETED, NOT REPAIRED (spec §A.5). `_book_for`
    # passes `senses: None` on every request, so `confirm` is permanently
    # "not wired" and this term was a no-op wearing a gate's clothes. The
    # pair-rotation confirm belongs on the contract chart where both legs
    # exist; on a single index series it is structurally UNKNOWN
    # (band_rotation.SINGLE_SERIES_CONFIRM_WHY) and always will be. `confirm`
    # stays on the frame as a printed field with its reason; it stops
    # pretending to gate.
    S["fire"] = S["reached"] and bool(flow)
```

- [ ] **Step 5: Update the one test that pinned the gate that could not gate**

`test_frame_zone.py::test_0911_0945_fires_only_when_flow_is_supplied_at_the_zone` asserts the old veto. It is the only test in the suite that does, and it fails after Step 4 with `assert True is False`. **That failure is the change landing, not a regression.** Find:

```python
def test_0911_0945_fires_only_when_flow_is_supplied_at_the_zone():
    tape = _with_absorption(_tape("2026-09-11", "09:45"))
    S = frame.build(tape, {"zone_state": _machine(tape), "senses": {"confirm": "UNKNOWN"}}, "09:45")["setup"]
    assert S["reached"] and any(f["kind"] == "absorption" for f in S["flow"]) and S["fire"] is True and S["visit"]
    S2 = frame.build(tape, {"zone_state": _machine(tape), "senses": {"confirm": "UNCONFIRMED"}}, "09:45")["setup"]
    assert S2["fire"] is False, "a chain UNCONFIRMED vetoes the beep even with tape flow present"
```

and replace with:

```python
def test_0911_0945_fires_only_when_flow_is_supplied_at_the_zone():
    tape = _with_absorption(_tape("2026-09-11", "09:45"))
    S = frame.build(tape, {"zone_state": _machine(tape), "senses": {"confirm": "UNKNOWN"}}, "09:45")["setup"]
    assert S["reached"] and any(f["kind"] == "absorption" for f in S["flow"]) and S["fire"] is True and S["visit"]
    # THE CONFIRM TERM IS GONE FROM `fire` (spec §A.5, 2026-09-18). It read as
    # a veto and vetoed nothing: `_book_for` passes `senses: None` on every
    # request, so `confirm` was permanently "not wired", and on a single index
    # series the pair-rotation confirm is structurally UNKNOWN
    # (band_rotation.SINGLE_SERIES_CONFIRM_WHY). It is still PRINTED on the
    # frame with its reason; it no longer gates, and this asserts both halves.
    S2 = frame.build(tape, {"zone_state": _machine(tape), "senses": {"confirm": "UNCONFIRMED"}}, "09:45")["setup"]
    assert S2["confirm"]["value"] == "UNCONFIRMED", "still printed"
    assert S2["fire"] is True, "and no longer a gate"
```

- [ ] **Step 6: Teach the record the signal transitioned**

In `frame_log.py` find:

```python
def sig(fr: dict) -> str:
    rows = [(r.get("p"), r.get("kind"), r.get("state")) for r in (fr.get("walls") or {}).get("rows") or []]
    s = fr.get("setup") or {}
    tells = [(t.get("name"), t.get("target")) for t in s.get("tells") or []]
    return json.dumps([fr.get("idx"), rows, s.get("state"), s.get("fire"), tells, sorted(fr.get("missing") or [])], default=str)
```

and replace with:

```python
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
```

- [ ] **Step 7: Add the record test** — append to `test_frame_log.py`:

```python
def test_a_signal_transition_is_its_own_record_row(tmp_path):
    """A visit going ARMED -> LIVE with the ladder unchanged used to write no
    row at all, so the scorer had nothing to fill forward cells against."""
    a = _fr()
    a["setup"]["signal"] = {"state": "ARMED", "visit_key": "buy@09:45", "sound": "soft"}
    a["setup"]["votes"] = {"n": 0, "passed": False}
    b = _fr()
    b["setup"]["signal"] = {"state": "LIVE", "visit_key": "buy@09:45", "sound": "firm"}
    b["setup"]["votes"] = {"n": 1, "passed": True}
    assert frame_log.sig(a) != frame_log.sig(b)
    p = str(tmp_path / "frame_2026-09-18.jsonl")
    frame_log._last_sig.clear()
    assert frame_log.append_if_changed(a, "2026-09-18", path=p) is True
    assert frame_log.append_if_changed(b, "2026-09-18", path=p) is True
    assert frame_log.append_if_changed(b, "2026-09-18", path=p) is False
    assert sum(1 for _ in open(p, encoding="utf-8")) == 2
```

- [ ] **Step 8: Run the tests**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_signals.py test_frame_log.py test_frame.py test_frame_zone.py`
Expected: all pass — `test_signals.py` at `26 passed` for that file alone.

- [ ] **Step 9: Run the suite**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q 2>&1 | tail -6`
Expected: `3 failed, 1151 passed` — only the three pre-existing `test_desk_numbers.py` failures.

- [ ] **Step 10: Commit**

```bash
git add signals.py test_signals.py frame.py frame_log.py test_frame_log.py test_frame_zone.py
git commit -m "signal: states, the falsifier frozen at the arm bar, blind-safe candles, two sounds; fire's dead confirm term deleted

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: `watch.py` — where the fight is, and none of it is an entry

**Goal:** at most eight ladder rows near spot, each naming why it was promoted and which of six flags it meets, plus every level that broke today kept on screen with its peak and its break minute.

**Files:**
- Create: `watch.py`
- Create: `test_watch.py`

**Interfaces:**
- Consumes: nothing from earlier tasks. Independent of `signals.py` **on purpose** — see the guardrail below.
- Produces: `watch.build(walls_rows, spot, sigma, basis, dwell, sequence, seq_fired, runways, minutes, peaks, prior=None) -> dict` returning the §D `walls.watch` object. Constants `watch.CAP == 8`, `watch.RADIUS_SIGMA == 1.5`, `watch.FLAGS == ("AGREE", "SIZE", "HELD", "DWELL", "FUEL", "CLOSING")`, `watch.NOTE`.

**The guardrail (§H.1)**, all three parts in code rather than in discipline: `_forbid` raises if a watched row ever grows a side, a direction or a target; `signals.py` has no `walls_rows` parameter, so a watched level can never originate a signal; and `NOTE` is a permanent header saying *where the fight is — none of these is an entry*.

- [ ] **Step 1: Write the failing test** — create `test_watch.py`:

```python
# tapemap/test_watch.py
"""watch.py: the watch list (spec §B). Synthetic ladder and machines.

Nothing here is an entry, and the tests assert that as hard as they assert
the promotion rules -- a row that grew a `side` or a `target` would be the
failure mode §H.1 names.
"""
import pytest

import watch


def _row(kind, p, **kw):
    r = {"kind": kind, "p": float(p), "d": None, "size": None, "since": None,
         "leaned": None, "snapshot": False, "oi": None, "chg": None, "pain": None,
         "pain_tag": None, "conf": None, "state": None, "tests": None,
         "last_outcome": None, "strike": None, "agree": None}
    r.update(kw)
    return r


def _ladder():
    return [
        _row("CE", 23300.0, strike=23270.0, oi=2.21e7, chg=4.3e6, pain=6.2,
             pain_tag="I", conf="session", agree="B 23300", state="held"),
        _row("B", 23300.0, size=600, leaned=3, since="10:02", agree="CE 23270",
             state="held"),
        _row("PE", 23250.0, strike=23220.0, oi=1.84e7, chg=-2.0e6, pain=0.0,
             pain_tag="I", conf="session", state="held"),
        _row("PDH", 23400.0, state="APPROACH", tests=2, last_outcome="REJECT"),
        _row("ROUND", 23450.0, state="IDLE"),
        _row("S", 26000.0, size=100, leaned=1, since="09:30", state="held"),
    ]


def _dwell(px=23300.0, held_s=240):
    return {"active": False, "holding": True, "level": {"kind": "CE", "px": px},
            "held_s": held_s, "band": 12.5, "tag": "I"}


def _sequence():
    return {"PDH@23400.0": {"state": "APPROACH", "kind": "PDH", "px": 23400.0,
                            "tests": 2, "last_outcome": "REJECT", "target": None},
            "ROUND@23450.0": {"state": "IDLE", "kind": "ROUND", "px": 23450.0,
                              "tests": 0, "last_outcome": None, "target": None}}


def _runways():
    return {"ok": True, "tag": "I", "richer": "UP",
            "up": {"target": {"kind": "PDH", "px": 23400.0}, "dist": 100.0,
                   "fuel": 41200000, "per_point": 412000, "items": [],
                   "stop_zone": {"lo": 23412.5, "hi": 23425.0, "tag": "I",
                                 "basis": "inferred"}, "why": "x"},
            "down": {"target": None, "fuel": None, "per_point": None, "items": [],
                     "why": "no known level in this direction within the map"}}


def _minutes():
    return {"12:45": {"spot": 23200.0, "k": {23270: (1.0e6, 0.0), 23220: (0.0, 2.0e6)},
                      "px": {23270: (80.0, 40.0), 23220: (30.0, 90.0)}},
            "12:52": {"spot": 23240.0, "k": {23270: (3.0e6, 0.0), 23220: (0.0, 1.0e6)},
                      "px": {23270: (70.0, 45.0), 23220: (28.0, 95.0)}},
            "13:00": {"spot": 23270.0, "k": {23270: (4.3e6, 0.0), 23220: (0.0, 0.8e6)},
                      "px": {23270: (65.0, 50.0), 23220: (25.0, 99.0)}}}


def _peaks():
    return {(23270, "ce"): 2.4e7, (23220, "pe"): 1.9e7}


def _build(**kw):
    # sigma 150 -> a radius of 225 points, which reaches the PDH at 23400 and
    # the ROUND at 23450 and does not reach the 26000 wall.
    a = dict(walls_rows=_ladder(), spot=23240.0, sigma=150.0, basis=30.0,
             dwell=_dwell(), sequence=_sequence(), seq_fired=[],
             runways=_runways(), minutes=_minutes(), peaks=_peaks(), prior=None)
    a.update(kw)
    return watch.build(**a)


def test_the_header_is_permanent_and_says_it_is_not_an_entry():
    w = _build()
    assert w["note"] == watch.NOTE
    assert "none of these is an entry" in watch.NOTE


def test_no_row_carries_a_side_a_direction_or_a_target():
    w = _build()
    for r in w["rows"] + w["broken"]:
        for banned in ("side", "direction", "dir", "target", "entry", "stop_px"):
            assert banned not in r, f"{banned} on a watched row is §H.1 broken"


def test_a_row_outside_one_and_a_half_sigma_is_not_watched():
    """The radius scales with the day: sigma, never a fixed point count."""
    w = _build()
    assert all(abs(r["p"] - 23240.0) <= watch.RADIUS_SIGMA * 150.0 for r in w["rows"])
    assert 26000.0 not in [r["p"] for r in w["rows"]]


def test_every_row_names_what_promoted_it():
    w = _build()
    assert w["rows"], "the ladder has promotable rows"
    for r in w["rows"]:
        assert r["promoted_by"] in ("agree", "sequence", "leaned", "oi_top3")


def test_agree_is_always_watched_and_flagged():
    w = _build()
    r = next(r for r in w["rows"] if r["kind"] == "CE" and r["p"] == 23300.0)
    assert r["promoted_by"] == "agree" and "AGREE" in r["flags"]


def test_a_level_the_machine_is_engaging_is_watched_and_an_idle_one_is_not():
    """Both are inside the radius; APPROACH means price is engaging the PDH
    and IDLE means the ROUND is just a number on a chart."""
    w = _build()
    ps = [r["p"] for r in w["rows"]]
    assert 23400.0 in ps and 23450.0 not in ps


def test_held_dwell_fuel_and_closing_are_flags_and_no_number_is_summed():
    w = _build()
    pdh = next(r for r in w["rows"] if r["p"] == 23400.0)
    assert "HELD" in pdh["flags"] and pdh["tests"] == 2
    assert pdh["fuel"] == 41200000 and pdh["fuel_tag"] == "I" and "FUEL" in pdh["flags"]
    assert pdh["stop_zone"] == 23412.5
    ce = next(r for r in w["rows"] if r["kind"] == "CE")
    assert "DWELL" in ce["flags"] and ce["dwell_min"] == 4
    assert "CLOSING" in ce["flags"] and ce["closing_pts_min"] is not None
    for r in w["rows"]:
        assert "danger" not in r and "score" not in r


def test_the_list_is_ordered_by_how_many_flags_are_met_and_the_count_is_not_printed():
    w = _build()
    counts = [len(r["flags"]) for r in w["rows"]]
    assert counts == sorted(counts, reverse=True)
    for r in w["rows"]:
        assert "flag_count" not in r and "n_flags" not in r


def test_the_cap_is_eight_and_shown_says_how_many_got_through():
    rows = _ladder() + [_row("B", 23240.0 + i, size=500, leaned=3, since="10:00",
                             state="held") for i in range(12)]
    w = _build(walls_rows=rows)
    assert w["cap"] == 8 and len(w["rows"]) == 8 and w["shown"] == 8


def test_an_empty_list_says_which_of_the_two_silences_it_is():
    w = _build(walls_rows=[])
    assert w["rows"] == [] and w["why"] == "the war map did not answer"
    w2 = _build(walls_rows=[_row("S", 26000.0, size=100, leaned=1, state="held")])
    assert w2["rows"] == [] and w2["why"] == "no ladder row within 1.5\u03c3 of spot"
    assert w["why"] != w2["why"], "two silences, never one sentence"


def test_a_broken_level_stays_on_screen_with_its_peak_and_its_break_minute():
    fired = [{"level": "PE", "px": 23250.0, "from": "DWELL", "to": "BREAK",
              "spot": 23241.0, "band": 12.5, "direction": "DOWN",
              "ts": "2026-09-18T11:03:07"},
             {"level": "PE", "px": 23250.0, "from": "BREAK", "to": "RUN",
              "spot": 23241.0, "band": 12.5,
              "target": {"kind": "ROUND", "px": 23150.0},
              "ts": "2026-09-18T11:03:07"}]
    w = _build(seq_fired=fired)
    b = next(b for b in w["broken"] if b["p"] == 23250.0)
    assert b["broke_at"] == "11:03" and b["broke_spot"] == 23241.0
    assert b["target_named"] == 23150.0 and b["role"] is None
    assert b["peak_oi"] == 1.9e7 and b["peak_at"] == "12:45" and b["peak_spot"] == 23200.0
    assert 0.5 < b["unwound_frac"] < 0.7


def test_a_broken_level_is_never_deleted_mid_session_and_re_enters_as_flipped():
    fired = [{"level": "PE", "px": 23250.0, "from": "DWELL", "to": "BREAK",
              "spot": 23241.0, "band": 12.5, "direction": "DOWN",
              "ts": "2026-09-18T11:03:07"}]
    w1 = _build(seq_fired=fired)
    w2 = _build(seq_fired=[], prior=w1)           # the break is not re-fired
    assert [b["p"] for b in w2["broken"]] == [23250.0]
    seq = dict(_sequence(), **{"PE@23250.0": {"state": "APPROACH", "kind": "PE",
                                              "px": 23250.0, "tests": 3,
                                              "last_outcome": "REJECT",
                                              "target": None}})
    w3 = _build(seq_fired=[], prior=w2, sequence=seq)
    assert next(b for b in w3["broken"] if b["p"] == 23250.0)["role"] == "flipped"


def test_a_row_that_grows_a_side_raises_rather_than_reaching_the_screen():
    with pytest.raises(ValueError):
        watch._forbid([{"p": 1.0, "side": "buy"}])
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_watch.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'watch'` (collection error, 0 tests run).

- [ ] **Step 3: Create `watch.py`**

```python
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
```

- [ ] **Step 4: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_watch.py`
Expected: `13 passed`

- [ ] **Step 5: Run the suite**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q 2>&1 | tail -6`
Expected: `3 failed, 1164 passed` — only the three pre-existing `test_desk_numbers.py` failures.

- [ ] **Step 6: Commit**

```bash
git add watch.py test_watch.py
git commit -m "watch: eight ladder rows near spot with six named flags, broken levels remembered; no side, no target, no entry

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: `breadth.py` and `GET /api/oihist` — positioning, with no direction in it

**Goal:** counts of what the writers did over a trailing 15 minutes, published with no direction field anywhere in the object, plus the per-strike minute grid served read-only so the counts can be reproduced from outside memory.

**Files:**
- Create: `breadth.py`
- Create: `test_breadth.py`
- Modify: `server.py` (one import, one `elif`)

**Interfaces:**
- Produces: `breadth.build(minutes, fut_bars, watched_strikes, regime, pinned, now_hhmm, window_min=15) -> dict` returning the §D `breadth` object. Constants `breadth.WINDOW_MIN == 15`, `breadth.ADVANCING_FRAC == 0.10`, `breadth.RETREATING_FRAC == 0.25`, `breadth.NOTE`, `breadth.BANNED_WORDS`.
- Route: `GET /api/oihist?idx=NIFTY` returning `{"ok", "idx", "minutes", "peak", "backfill_marks", "why"}`.

**Two things this deliberately does not do**, both argued in full in the module docstring below: `engine.py`'s STRONG BULL / STRONG BEAR verdict is **not ported** (§C.1 — three of its four inputs are the same fact counted three times), and true advance/decline breadth is **not built** (§C.3 — index membership is not in the Upstox dump, so the constituent list would be hand-maintained and quietly wrong). Two of the verdict's inputs *are* real and independent and do land here as named facts: `regime` and `pinned`.

- [ ] **Step 1: Write the failing test** — create `test_breadth.py`:

```python
# tapemap/test_breadth.py
"""breadth.py: positioning breadth (spec §C.2). Counts of strikes, never a
direction -- the object is built with no direction field IN it, which is the
enforcement, and the last test here is what enforces the enforcement."""
import json

import breadth


def _minutes():
    """Three marks, 15 minutes apart at the ends. `k` is cumulative OI change
    since the open (ChainState.minutes' own meaning); `px` is a LEVEL."""
    return {
        "12:45": {"spot": 23200.0,
                  "k": {23200: (1.0e6, 2.0e6), 23300: (1.2e6, 1.0e6),
                        23100: (0.0, 3.0e6)},
                  "px": {23200: (120.0, 90.0), 23300: (60.0, 180.0),
                         23100: (210.0, 40.0)}},
        "12:52": {"spot": 23230.0,
                  "k": {23200: (1.4e6, 2.4e6), 23300: (1.5e6, 9.0e5),
                        23100: (0.0, 3.4e6)},
                  "px": {23200: (110.0, 95.0), 23300: (55.0, 190.0),
                         23100: (220.0, 38.0)},
                  "src": "backfill"},
        "13:00": {"spot": 23270.0,
                  "k": {23200: (2.0e6, 3.0e6), 23300: (1.0e6, 8.0e5),
                        23100: (0.0, 4.0e6)},
                  "px": {23200: (100.0, 99.0), 23300: (50.0, 200.0),
                         23100: (230.0, 35.0)}},
    }


def _fut():
    return [{"t": 1_780_026_340_000, "o": 23195.0, "h": 23210.0, "l": 23190.0,
             "c": 23200.0, "oi": 1_000_000},
            {"t": 1_780_026_340_000 + 300000 * 3, "o": 23200.0, "h": 23240.0,
             "l": 23195.0, "c": 23230.0, "oi": 940_000},
            {"t": 1_780_026_340_000 + 300000 * 6, "o": 23230.0, "h": 23280.0,
             "l": 23225.0, "c": 23270.0, "oi": 588_000}]


def _b(**kw):
    a = dict(minutes=_minutes(), fut_bars=_fut(),
             watched_strikes=[(23200, "pe"), (23300, "ce"), (23100, "pe")],
             regime="PINNED", pinned=True, now_hhmm="13:00")
    a.update(kw)
    return breadth.build(**a)


def test_the_window_is_named_and_both_ends_are_real_marks():
    b = _b()
    assert b["window_min"] == 15 and b["t0"] == "12:45" and b["t1"] == "13:00"


def test_four_counts_never_a_ratio_and_never_a_word():
    """23200 adds on both legs, 23300 sheds CE and PE, 23100 adds PE and does
    not move CE -- a strike that did not move is neither, not a zero."""
    b = _b()
    assert b["written_ce"] == 1 and b["unwound_ce"] == 1
    assert b["written_pe"] == 2 and b["unwound_pe"] == 1
    assert b["strikes_seen"] == 3 and b["counts_why"] is None


def test_concentration_says_one_wall_or_a_curtain():
    b = _b()
    assert 0.0 < b["concentration_top1"] <= 1.0
    assert b["concentration_top1"] <= b["concentration_top3"] <= 1.0
    assert b["concentration_why"] is None


def test_advancing_and_retreating_are_measured_off_each_front_s_own_peak():
    """23300 CE peaked at 1.5M mid-window and sits at 1.0M: a third given
    back, past the retreating threshold. The two PE fronts are still at their
    own peaks and still rising."""
    b = _b()
    assert b["fronts_seen"] == 3 and b["fronts_why"] is None
    assert b["advancing"] == 2 and b["retreating"] == 1


def test_pressed_and_bought_read_the_axis_minutes_px_was_stored_for():
    """Of the strikes that ADDED OI this window, how many saw premium fall
    (writers pressing) against rise (buyers building) -- the axis
    ChainState.minutes["px"] was stored for and nothing has ever read."""
    b = _b()
    assert b["pressed"] == 2 and b["bought"] == 1 and b["premium_why"] is None


def test_the_futures_lane_is_oi_against_price_session_and_window():
    b = _b()
    assert b["fut_oi_day"] == -412000 and b["fut_px_day"] == 75.0
    assert b["fut_oi_window"] is not None and b["fut_why"] is None


def test_regime_is_a_ported_fact_and_carries_its_tag():
    b = _b()
    assert b["regime"] == "PINNED" and b["pinned"] is True
    assert b["regime_tag"] == "I" and b["regime_why"] is None
    b2 = _b(regime=None, pinned=None)
    assert b2["regime"] is None and b2["regime_why"] and len(b2["regime_why"]) <= 48


def test_backfilled_minutes_are_counted_and_flagged_never_blended_silently():
    b = _b()
    assert b["backfill_minutes"] == 1


def test_a_window_with_one_mark_says_it_could_not_check():
    b = _b(minutes={"13:00": _minutes()["13:00"]})
    assert b["written_ce"] is None and b["counts_why"] and len(b["counts_why"]) <= 48
    assert b["t0"] is None and b["t1"] == "13:00"


def test_there_is_no_direction_field_anywhere_in_the_object():
    """§C.4's enforcement, and §H.5's guardrail: you cannot render a BULL/BEAR
    banner from data that does not contain one. This is the test that keeps it
    true after someone adds a field in six months."""
    b = _b()
    blob = json.dumps(b).upper()
    for banned in breadth.BANNED_WORDS:
        assert banned not in blob, f"{banned} reached the breadth object"
    for k in b:
        assert k not in ("direction", "bias", "lean", "verdict", "sentiment", "net")


def test_the_caption_is_permanent_and_names_both_readings():
    b = _b()
    assert b["note"] == breadth.NOTE
    assert "ceiling" in breadth.NOTE and "or" in breadth.NOTE
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_breadth.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'breadth'` (collection error, 0 tests run).

- [ ] **Step 3: Create `breadth.py`**

```python
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
```

- [ ] **Step 4: Run the test**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_breadth.py`
Expected: `11 passed`

- [ ] **Step 5: Add `GET /api/oihist`**

In `server.py` find the import line:

```python
import frame
import frame_log
```

and replace with:

```python
import breadth as breadth_mod
import frame
import frame_log
```

(The import is added now so the module is loaded once with the rest; Task 6 uses it.)

Then find the insertion anchor (the only occurrence in the file):

```python
        elif self.path.startswith("/api/desk"):
```

and insert **directly above it**:

```python
        elif self.path.startswith("/api/oihist"):
            # THE PER-STRIKE MINUTE GRID AS IT SITS IN MEMORY. GET only.
            # `ChainState.minutes` has had exactly one reader (/api/oiflow,
            # which aggregates it away) and `ChainState.peak` has had none
            # over HTTP, so the breadth counts and the Field's fronts could
            # not be checked against the same numbers the brain used. Without
            # this the fronts are drawn from one ~10-second snapshot and the
            # ghost outlines cannot exist at all.
            #
            # `peak` is keyed by a (strike, side) TUPLE in memory, which JSON
            # has no key for, so it goes out as a LIST of rows rather than
            # being silently string-joined into something a reader has to
            # parse back apart.
            idx = self._idx()
            st = (getattr(self.poller, "states", None) or {}).get(idx) if self.poller else None
            mins = getattr(st, "minutes", None)
            peak = getattr(st, "peak", None)
            self._json(json.dumps({
                "ok": mins is not None,
                "idx": idx,
                "why": None if mins is not None else
                       "the chain poller has no state for this index yet",
                "minutes": mins or {},
                "peak": [{"k": k, "side": s, "oi": v}
                         for (k, s), v in sorted((peak or {}).items())],
                # Which marks were REBUILT from REST candles rather than seen
                # by the socket (chain_backfill stamps `src` on the mark
                # itself). A reconstructed morning is worth having and is not
                # the same evidence as an observation.
                "backfill_marks": sorted(m for m, rec in (mins or {}).items()
                                         if (rec or {}).get("src") == "backfill"),
            }, default=str).encode())
```

- [ ] **Step 6: Prove the module imports and the route is syntactically live**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -c "import server; print('ok')"`
Expected: `ok`

Run: `curl -s -o NUL -w "%{http_code}\n" "http://127.0.0.1:8765/api/oihist?idx=NIFTY"`
Expected: `404` — **correct and expected.** The live server is running the old Python and will not serve this route until the owner restarts after 15:30 IST. Record the 404 and move on. Do not restart the server.

- [ ] **Step 7: Run the suite**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q 2>&1 | tail -6`
Expected: `3 failed, 1175 passed` — only the three pre-existing `test_desk_numbers.py` failures.

- [ ] **Step 8: Commit**

```bash
git add breadth.py test_breadth.py server.py
git commit -m "breadth: writer counts over a trailing 15 minutes with no direction field in the object; GET /api/oihist serves the minute grid

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: wire the four objects onto the frame, and give `_book_for` the sweeps

**Goal:** `setup.signal`, `setup.votes`, `walls.watch` and a top-level `breadth` on every frame, each isolated so a raising object becomes its own `why` and the other objects still print — and the DEPTH vote measurable for the first time.

**Files:**
- Modify: `frame.py` (empty shapes, `_setup`, `_walls`, `build`)
- Modify: `server.py` (`_book_for`)
- Modify: `test_frame.py` (append composition cases)

**Interfaces:**
- Consumes: `signal.build`, `signals.EMPTY_SIGNAL`, `signals.EMPTY_VOTES` (Task 3); `watch.build`, `watch.NOTE` (Task 4); `breadth.build`, `breadth.NOTE` (Task 5).
- Produces: the frame keys `setup.signal`, `setup.votes`, `walls.watch`, `breadth`.

**The `_book_for` fix, precisely.** `_book_for` passes `senses: None` on every request, which is why the DEPTH vote could never be measured. It keeps passing `senses: None` — the `/api/senses` **reading** is assembled in the GET handler from `_SENSES["fuse"]` plus `_regime_engine_read`/`_walls_holding`, and `_book_for`'s own docstring forbids re-deriving it here; two tests (`test_frame.py:126` and `:156`) pin the honest absences that produces. What the DEPTH vote actually needs is the raw sweep rows, which are `_SENSES["rows"]` filtered by instrument — no derivation at all — so they arrive under their own key and the composer's rule is not broken to get them.

- [ ] **Step 1: Write the failing tests** — append to `test_frame.py`:

```python
def test_the_signal_and_the_ballot_ride_on_the_setup():
    f = frame.build(_tape(), _book(), "15:30")
    S = f["setup"]
    assert "signal" in S and "votes" in S
    assert S["signal"]["visit_key"] == S["visit"], "one visit key, not two"
    assert S["signal"]["intent"] == "fade to VWAP"
    assert S["votes"]["of"] == 4 and S["votes"]["threshold"] == 1
    assert len(S["votes"]["items"]) == 4


def test_breadth_says_it_could_not_check_when_the_chain_has_no_two_marks():
    b = _book(); b["minutes"] = {}
    B = frame.build(_tape(), b, "15:30")["breadth"]
    assert B["t0"] is None and B["written_ce"] is None
    assert B["counts_why"] and len(B["counts_why"]) <= 48
    assert B["strikes_seen"] == 0, "a count of nothing, not a missing count"


def test_the_watch_list_rides_under_walls_and_carries_its_permanent_header():
    import watch
    f = frame.build(_tape(), _book(), "15:30")
    W = f["walls"]["watch"]
    assert W["cap"] == 8 and W["note"] == watch.NOTE
    assert (W["why"] is not None) == (W["rows"] == [])


def test_breadth_is_a_top_level_object_with_no_direction_in_it():
    import breadth as br
    import json as _json
    f = frame.build(_tape(), _book(), "15:30")
    B = f["breadth"]
    assert B["window_min"] == 15 and B["note"] == br.NOTE
    blob = _json.dumps(B).upper()
    for banned in br.BANNED_WORDS:
        assert banned not in blob


def test_the_depth_vote_is_measurable_once_sweeps_are_on_the_book():
    b = _book()
    b["sweeps"] = [{"det": "sweep", "kind": "swept", "side": "buy", "qty": 100.0,
                    "t": "10:05:10", "inst": "NIFTY-FUT"}] * 6
    f = frame.build(_tape(), b, "15:30")
    d = next(i for i in f["setup"]["votes"]["items"] if i["key"] == "depth")
    assert d["ok"] is not None, "with rows on the book DEPTH is no longer unknowable"


def test_the_ballot_never_sees_a_level_row():
    """§H.1 by construction: only CE/PE rows are handed over, so a PDH or a
    tape wall cannot originate anything. If the composer ever hands the whole
    ladder across, signals._only_oi raises, _safe turns the whole setup into
    its own `why`, and this assertion is what catches it."""
    f = frame.build(_tape(), _book(), "15:30")
    assert "why" not in f["setup"], f["setup"].get("why")
    assert "why" not in f["walls"], f["walls"].get("why")
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_frame.py -k "signal or watch or breadth or ballot or depth_vote"`
Expected: FAIL — `KeyError: 'signal'` on the first case.

- [ ] **Step 3: Extend the empty shapes in `frame.py`**

Find:

```python
import gate as gate_mod
import structure   # prior_day_hlc: the payload's floor pivots inverted back to the prior session's H/L/C
import visit as visit_mod   # the latched reach and the visit key; frame.py composes, visit.py measures
```

and replace with:

```python
import breadth as breadth_mod   # positioning breadth; no direction field exists in that object by construction
import gate as gate_mod
import signals as signal_mod     # the ballot and the state machine; frame.py never measures a vote
import structure   # prior_day_hlc: the payload's floor pivots inverted back to the prior session's H/L/C
import visit as visit_mod   # the latched reach and the visit key; frame.py composes, visit.py measures
import watch as watch_mod       # the ladder rows worth watching; none of them is an entry
```

Then find:

```python
_EMPTY_WALLS = {"rows": [], "cap": WALL_CAP, "floors_taken": 0, "oi_why": None, "prior_why": None, "basis": None}
```

and replace with:

```python
_EMPTY_WALLS = {"rows": [], "cap": WALL_CAP, "floors_taken": 0, "oi_why": None, "prior_why": None, "basis": None,
                "watch": {"rows": [], "broken": [], "cap": watch_mod.CAP, "shown": 0,
                          "why": "the watch list did not build", "note": watch_mod.NOTE}}
_EMPTY_BREADTH = {"window_min": breadth_mod.WINDOW_MIN, "t0": None, "t1": None,
                  "written_ce": None, "unwound_ce": None, "written_pe": None, "unwound_pe": None,
                  "strikes_seen": 0, "counts_why": "breadth did not build",
                  "concentration_top1": None, "concentration_top3": None, "concentration_why": "breadth did not build",
                  "advancing": None, "retreating": None, "fronts_seen": 0, "fronts_why": "breadth did not build",
                  "pressed": None, "bought": None, "premium_why": "breadth did not build",
                  "fut_oi_day": None, "fut_px_day": None, "fut_oi_window": None, "fut_px_window": None,
                  "fut_why": "breadth did not build", "regime": None, "pinned": None, "regime_tag": "I",
                  "regime_why": "breadth did not build", "backfill_minutes": 0, "tag": "M",
                  "note": breadth_mod.NOTE}
```

Then find:

```python
_EMPTY_SETUP = {"side": "buy", "state": "PATA NAHI", "state_why": None, "ref": None, "candles_left": None, "level": None,
                 "reached": False, "in_pocket": False, "flow": [], "fire": False, "visit": None, "tells": [],
                 "confirm": {"value": "UNKNOWN", "why": "setup did not build", "why_full": None, "tag": "I"}, "falsifies": None}
```

and replace with:

```python
_EMPTY_SETUP = {"side": "buy", "state": "PATA NAHI", "state_why": None, "ref": None, "candles_left": None, "level": None,
                 "reached": False, "in_pocket": False, "flow": [], "fire": False, "visit": None, "tells": [],
                 "confirm": {"value": "UNKNOWN", "why": "setup did not build", "why_full": None, "tag": "I"}, "falsifies": None,
                 "signal": dict(signal_mod.EMPTY_SIGNAL), "votes": dict(signal_mod.EMPTY_VOTES)}
```

- [ ] **Step 4: Compose the signal and the ballot in `_setup`**

Find, at the end of `_setup`:

```python
    zs = book.get("zone_state_sell") if use_sell else book.get("zone_state")
    v = visit_mod.current(tape, zs if isinstance(zs, list) else [], side)
```

and replace with:

```python
    zs = book.get("zone_state_sell") if use_sell else book.get("zone_state")
    zs = zs if isinstance(zs, list) else []
    # THE BALLOT AND THE STATE MACHINE (spec §A). Composed, never measured
    # here: signals.py owns every comparison. Only the CE/PE rows are handed
    # over -- `walls.rows` never enters signals.py (spec §B.1, §H.1) -- and the
    # OI vote's `src` is "backfill" when the war map replayed a rebuilt grid.
    oi_rows = [r for r in (walls.get("rows") or []) if r.get("kind") in ("CE", "PE")]
    S["signal"], S["votes"] = signal_mod.build(
        tape, zs, side, oi_rows, book.get("sweeps") or [], now_hhmm,
        oi_backfill=bool((book.get("warmap") or {}).get("backfill")))
    v = visit_mod.current(tape, zs, side)
```

- [ ] **Step 5: Compose the watch list in `_walls`**

Find, at the end of `_walls`:

```python
    for r in rows:
        r["d"] = round(float(r["p"] - fut), 1) if fut is not None else None
    rows.sort(key=lambda r: -r["p"])
    return {"rows": rows, "cap": WALL_CAP, "floors_taken": sum(1 for x in broke if x.get("side") == 1),
            "oi_why": oi_why, "prior_why": prior_why, "basis": b}
```

and replace with:

```python
    for r in rows:
        r["d"] = round(float(r["p"] - fut), 1) if fut is not None else None
    rows.sort(key=lambda r: -r["p"])
    bn = _bands_now(tape)
    # THE WATCH LIST (spec §B). `prior` is the previous frame's own watch
    # object, handed over by the server so a broken level is remembered for
    # the rest of the session while this module stays pure and stateless.
    wt = watch_mod.build(
        rows, fut, (bn or {}).get("sigma"), b,
        wm.get("dwell"), wm.get("sequence"), wm.get("seq_fired"), wm.get("runways"),
        book.get("minutes") or {}, book.get("peaks") or {}, book.get("watch_prior"))
    return {"rows": rows, "cap": WALL_CAP, "floors_taken": sum(1 for x in broke if x.get("side") == 1),
            "oi_why": oi_why, "prior_why": prior_why, "basis": b, "watch": wt}
```

- [ ] **Step 6: Compose breadth in `build`**

Find:

```python
    events, events_why = _safe_list(_events_and_armed)
    return {"ok": True, "idx": tape.get("idx") or "NIFTY", "ts": now_hhmm, "day": day, "interval": sess[1] if len(sess) >= 3 else None,
            "have_bars": len(closed), "lot": tape.get("lot"), "missing": missing, "coverage": book.get("coverage") or {},
            "events": events, "events_why": events_why, "taps": tape.get("taps") or [], "head": head, "record": {"written": False},
            "where": where, "trapped": trapped, "walls": walls, "tape": tape_o, "setup": setup}
```

and replace with:

```python
    events, events_why = _safe_list(_events_and_armed)
    # POSITIONING BREADTH (spec §C.2), a TOP-LEVEL object because it is a
    # property of the session and not of the setup in play. The watched
    # strikes are the ladder's own OI rows, so breadth and the war map are
    # always describing the same fronts.
    watched = [(int(r["strike"]), r["kind"].lower())
               for r in (walls.get("rows") or [])
               if r.get("kind") in ("CE", "PE") and r.get("strike") is not None]
    breadth_o = _safe(lambda: breadth_mod.build(
        mins, closed, watched, book.get("regime"), book.get("pinned"), clock),
        _EMPTY_BREADTH)
    return {"ok": True, "idx": tape.get("idx") or "NIFTY", "ts": now_hhmm, "day": day, "interval": sess[1] if len(sess) >= 3 else None,
            "have_bars": len(closed), "lot": tape.get("lot"), "missing": missing, "coverage": book.get("coverage") or {},
            "events": events, "events_why": events_why, "taps": tape.get("taps") or [], "head": head, "record": {"written": False},
            "where": where, "trapped": trapped, "walls": walls, "tape": tape_o, "setup": setup, "breadth": breadth_o}
```

- [ ] **Step 7: Give `_book_for` the sweeps, the peaks, the regime and the prior watch**

In `server.py`, find:

```python
    with _SENSES_LOCK:
        wb = _SENSES.get("warmap")
        wm = wb.for_index(idx).state() if wb else None
        g = (_SENSES.get("vpin") or {}).get(f"{idx}-FUT")
        vpin_pct = g.state().get("pct") if g else None
        senses = None
    st = (getattr(handler.poller, "states", None) or {}).get(idx) if handler.poller else None
    box = handler.chains.get(idx) if handler.chains else None
```

and replace with:

```python
    with _SENSES_LOCK:
        wb = _SENSES.get("warmap")
        wm = wb.for_index(idx).state() if wb else None
        g = (_SENSES.get("vpin") or {}).get(f"{idx}-FUT")
        vpin_pct = g.state().get("pct") if g else None
        senses = None
        # THE DEPTH VOTE'S ONLY INPUT (spec §A.4). `senses` stays None above
        # for the reason this function's docstring gives -- the /api/senses
        # READING is assembled in that handler and must not be re-derived
        # here. The vote never wanted the reading; it wants the raw sweep
        # rows, which are the ring filtered by instrument and nothing more.
        # Until this key existed the DEPTH vote was structurally unmeasurable.
        sweeps = [r for r in (_SENSES.get("rows") or ())
                  if r.get("inst") == f"{idx}-FUT" and r.get("det") == "sweep"]
        # The previous frame's watch list, so a level that broke this morning
        # is still on screen this afternoon. watch.py is pure; the memory
        # lives here, in the object this process already keeps.
        watch_prior = (((_SENSES.get("frame") or {}).get(idx) or {})
                       .get("walls") or {}).get("watch")
    st = (getattr(handler.poller, "states", None) or {}).get(idx) if handler.poller else None
    box = handler.chains.get(idx) if handler.chains else None
```

Then find:

```python
    _day0 = (pj.get("days") or [{}])[0] if isinstance(pj, dict) else {}
    return {"warmap": wm, "minutes": getattr(st, "minutes", None),
            "spot": box.get("spot") if box else None,
            "expiry": (box or {}).get("expiry") or (pj.get("expiry") if isinstance(pj, dict) else None),
            "zone_state": _day0.get("zone_state"), "zone_state_sell": _day0.get("zone_state_sell"),
            "pivots": _day0.get("pivots"),      # the prior session's floor pivots; frame._walls inverts them to PDH/PDL/PDC
            "vpin_pct": vpin_pct, "senses": senses, "ivrv": None,
            "coverage": _coverage()}
```

and replace with:

```python
    _day0 = (pj.get("days") or [{}])[0] if isinstance(pj, dict) else {}
    # The engine's OWN regime, off the last published bar's ctx (engine.py:1200
    # writes `pin.regime`; contract_bars.resample_index carries `ctx` through
    # the 3-minute fold). Two named facts, not the STRONG BULL / STRONG BEAR
    # verdict beside them -- that verdict is not ported at any size (spec §C.1).
    regime = None
    try:
        _bars = _day0.get("bars") or []
        regime = ((_bars[-1].get("ctx") or {}).get("pin") or {}).get("regime")
    except (AttributeError, IndexError, TypeError):
        regime = None
    return {"warmap": wm, "minutes": getattr(st, "minutes", None),
            "peaks": getattr(st, "peak", None),
            "spot": box.get("spot") if box else None,
            "expiry": (box or {}).get("expiry") or (pj.get("expiry") if isinstance(pj, dict) else None),
            "zone_state": _day0.get("zone_state"), "zone_state_sell": _day0.get("zone_state_sell"),
            "pivots": _day0.get("pivots"),      # the prior session's floor pivots; frame._walls inverts them to PDH/PDL/PDC
            "vpin_pct": vpin_pct, "senses": senses, "sweeps": sweeps,
            "watch_prior": watch_prior,
            "regime": regime, "pinned": None if regime is None else regime == "PINNED",
            "ivrv": None, "coverage": _coverage()}
```

- [ ] **Step 8: Run the frame tests**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q test_frame.py test_frame_zone.py test_frame_api.py test_operator_objects.py`
Expected: all pass.

- [ ] **Step 9: Prove the server still imports**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -c "import server; print('ok')"`
Expected: `ok`

- [ ] **Step 10: Run the suite**

Run: `cd "C:/Users/kaam/Desktop/operator mode/tapemap" && python -m pytest -q 2>&1 | tail -6`
Expected: `3 failed, 1181 passed` — only the three pre-existing `test_desk_numbers.py` failures.

- [ ] **Step 11: Commit**

```bash
git add frame.py server.py test_frame.py
git commit -m "frame: compose signal, votes, walls.watch and breadth; _book_for hands over the sweeps so the DEPTH vote can finally be measured

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: Handoff to the UI plan — the contract §G steps 4 and 7 must be written against

**This task writes no code and makes no commit.** §G step 4 (the `took` / `skipped` column) and §G step 7 (the Field marks) are user-interface work for a desk build that does not exist yet. The brain now ships every field that work needs. This section is what the UI plan's author reads instead of re-deriving it.

**Where everything lives on the wire.** One `POST /api/frame` response, and one new `GET`:

| what the face needs | where it is |
|---|---|
| the signal | `setup.signal` |
| the ballot | `setup.votes` |
| the watch list and the broken levels | `walls.watch` |
| positioning breadth | `breadth` (top level) |
| the per-strike minute grid and peaks | `GET /api/oihist?idx=NIFTY` → `{ok, idx, minutes, peak, backfill_marks, why}` |

### For §G step 4 — the `took` / `skipped` column

The column is one keystroke per visit, written to `localStorage`, exported with the record. **No POST, no server write, no order path — it is a note, and notes are not orders.**

- **The key to store against is `setup.signal.visit_key`** (`"buy@09:45"`). It is stable for the life of a visit by construction: `visit.py` derives it from `run_states`' `arm.first_t`, so a re-arm cannot change it mid-visit, which is the defect Task 1 fixed. Do **not** key on `setup.visit` — it is the same string today and may not stay that way; `signal.visit_key` is the contract.
- **A row is out of method when `setup.signal.out_of_method` is true.** Those rows must never pool with the edge population. Render them grey and silent; `setup.signal.mute_why` is the sentence to print (`"visit two - not your edge"` or `"09:30 - outside 09:45-13:15"`).
- **Unanswered renders `—` and is counted in the record header.** Not blank, not a zero. §H.6: a half-kept promise on a record is worse than no column.
- **Its kill condition, set before the first row:** if after 20 sessions more than half the rows are unanswered, the column is deleted rather than left on screen.
- The record itself needs no change: `frame_log.append_if_changed` writes the whole frame, so `signal{}` and `votes{}` are already in every row, and `frame_log.sig` was taught the signal state in Task 3 so a REACHED → ARMED → LIVE transition writes its own row.

### For §G step 7 — the Field marks

Every mark below is drawn from a field that ships today. Nothing on this list needs a new route or a new computation.

| mark (spec §E) | fields |
|---|---|
| reach ring, dashed while provisional | `signal.reached_at`, `signal.reached_provisional`; the price is the near edge from `where.buy_zone[1]` / `where.sell_zone[0]` |
| vote ticks `W` `E` `D` on the edge line | `votes.items[].key`, `.t`, `.p`, `.ok`, `.src` — draw `ok: true` filled, `ok: false` as nothing, `ok: null` as the reason text; a `src: "backfill"` tick is drawn hollow because it did not count |
| the OI chip at the right of the edge | the `votes.items[]` entry with `key == "oi"`; its `label` is the chip text and its `tag` is always `"I"` |
| heavy edge segment, reach bar → trigger bar | `signal.reached_at` → `signal.fired_at`, drawn only when `signal.state == "LIVE"`; grey when `signal.out_of_method` |
| falsifier hairline, and the second faint one | `signal.falsifier.px`, `.frozen_at`, `.drifted`, `.live_px` — print both numbers when `drifted` |
| candles-left pips that stop moving when blind | `signal.candles_left`, `signal.candles_blind`, `signal.blind_since` |
| `seen at` provenance | `signal.fired_at` beside `signal.seen_at`; they differ only when the brain did not watch the trigger bar |
| the state word at 15 px | `signal.state`, and `signal.state_why` whenever the state is `"PATA NAHI"` |
| the ordinal in words on the first line | `signal.visit_ordinal`, printed whenever it is not 1 |
| the two sounds | `signal.sound` (`"soft"` / `"firm"` / `null`) and `signal.mute_why`. **That is the complete list of sounds.** Nothing else on this screen ever makes one — not arming, not a vote landing, not a level going live or breaking, not a dead feed, not breadth, not the gate |
| watched-level gutter rules | `walls.watch.rows[]`: `p`, `kind`, `agree`, `d`, `live`, `flags`, `tests`, `last_outcome`, `dwell_min`, `closing_pts_min`, `fuel` + `fuel_tag`, `stop_zone`, `promoted_by` |
| the permanent watch header | `walls.watch.note` — render it verbatim, always, never collapsed |
| ghost outlines at peak thickness | `walls.watch.broken[]`: `p`, `kind`, `broke_at`, `broke_spot`, `peak_oi`, `peak_at`, `peak_spot`, `unwound_frac`, `target_named`, `role` |
| the 28 px breadth strip on the Field's x axis | `breadth` for the current counts; `GET /api/oihist` for the per-minute ticks and the `backfill_marks` to draw differently |
| the breadth caption | `breadth.note` — permanent, verbatim |

**Three rules the UI plan inherits and may not relax:**

1. **Loudness, in order, never violated:** distance-to-zone chip 34 px › the Field › signal state word 15 px › watched-level labels 12 px › breadth strip 10 px. Breadth is the quietest visible thing on the screen. Nothing animates; rows never re-sort while a signal is LIVE.
2. **No watched level may be rendered with a verb, a side, a direction or a target of its own.** The brain refuses to publish them (`watch._forbid` raises), and the face must not invent them. If the operator ever reports taking a trade off a watched level, the flags come off the screen.
3. **Breadth may caption a decision, never make one.** No BULL/BEAR banner exists to render — the object contains no direction field, and `breadth.BANNED_WORDS` plus its test keep it that way. Under a LIVE signal one caption may print naming what the fronts are doing on the side of the trade, built only from the §C.2 counts.

**Check the 960 px width first.** Both prior desk designs deleted the battlefield at 960 by different bugs. Check the narrow layout before the wide one.
