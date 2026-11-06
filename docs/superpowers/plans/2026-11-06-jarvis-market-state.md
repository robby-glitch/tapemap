# Jarvis Market State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis a per-index market state with memory (TREND ▲ / TREND ▼ / RANGE, EXPANDING / CONTRACTING) that leads the screen, a zone card that judges her §1b trigger by that state, and a cross-index read — the approved spec `docs/superpowers/specs/2026-11-06-jarvis-market-state-design.md` (commit 84f58ea), phases 1–3.

**Architecture:** One new pure module, `mstate.py`. It folds the frame causally from 09:15. Structure reuses `reader.py`'s leg engine: pivots are confirmed on closes, fed Jarvis's 3-min bars. The spec's trend rules sit on those pivots. `jarvis.py` gets thin wiring: `_build` stores `mstate` / `pivots` / `zone_cards`, and `call()` makes the state word THE word, with the old ACTION word as a chip. `jarvis_log.py` gains the state forward log. `server.py` adds the cross-index read and BANKNIFTY to the pass. The face is `docs/kahani/review/mockup/jarvis2.html`.

**Tech Stack:** Python 3.13, stdlib only (no new dependency), pytest; one static HTML page (vanilla JS).

## Global Constraints

- **The spec is the source of truth:** `docs/superpowers/specs/2026-11-06-jarvis-market-state-design.md` (84f58ea). The repo's rules are in `CLAUDE.md` ("The rules that survive").
- **Display only. No order path, ever** (CLAUDE.md rule 10). Nothing here gates, beeps or places.
- **Counts, never a %, win rate, hit rate, expectancy or confidence score** (CLAUDE.md rule 4, spec §8). Every new test asserts `"%" not in json.dumps(...)` where it prints text.
- **Rule 6, three sentences:** "checked, found nothing", "could not check — <reason>" and "not read — <why>" stay apart. A missing input is never a zero.
- **Rule 7:** every number is `[M]` measured or `[I]` inferred, and says which.
- **Every new [I] number** goes in `jarvis_thresholds.json` as `"mstate.<NAME>"`, with a `_why` and a NOTEPAD section-A row (A256 / A257 / A258) written in the same task. `test_thresholds.py` must stay green.
- **§1b–§1s are untouched.** Her §1d gate is shown verbatim and never changed. Phase 4 is BLOCKED: it is hers to sign.
- **Anytime-start:** the state is rebuilt causally from 09:15 on every build. State-log rows written after their minute are tagged `src: "backfill"` and are never pooled with `"live"` rows.
- **Causal:** row i reads minutes ≤ i only. A zone card is judged at its trigger's close (t+2), and is shown only from when its trigger_log row was written (`at`).
- **SENSEX (§1q):** NIFTY's order flow, its own OI. Its structure is read on spot (spec §3).
- **No backtests and no tuning** (CLAUDE.md rule 2, spec §11). The 28 Oct–5 Nov replay (Task 14) reports counts and observed words only. It never reads `mfe` / `mae` / `stop_hit`, and no threshold is moved on it.
- **Screens:** light mode only, terminal grammar (grids, numbers, pills, ≤6-word cells), and a Hinglish chip with its number for every symbol.
- **Never start, stop or restart the live server** (memory: an agent-started server died with the session). Mary restarts with `.\stop.bat; .\start-v2.bat`. Replays run only after 15:40 IST or at weekends.
- **Commits:** commit steps run only after Mary says commit. They are local only; never push.
  - Spec §10 asks for one commit per phase. Stage each task's files, then make ONE commit at the end of each phase with that phase's message (Tasks 6, 9 and 14). Commit per task only if Mary asks.
  - As of 6 Nov the working tree has someone else's uncommitted edits in `test_jarvis.py`, `docs/live/NOTEPAD.md` and `optflow/*`. Stage only this plan's hunks (`git add -p`), or ask Mary to commit hers first.
- **Tests:** `python -m pytest -q` from the repo root. 2081 tests are collected; one is known flaky (`test_v2feed` serve-cache, A49). Run the full suite before each phase commit.
- **Ponytail:** reuse before writing.
  - Reuse `reader.Engine` (pivots), `decode.ZZ_PCT` / `ZZ_SIG` (reversal size), `hold2.losing` (§1m gave up), `fronts.side_front`, `legs._chain_leg` / `legs._lad` / `legs.K_MIN` / `legs.K1_L`, `effort.lam_at` / `effort.HI`, `jarvis.wf_push` / `WF_L` / `UNWIND_AT` / `BLIND_MIN` / `MANAGE_WIN` / `_basis`, and `confluence_log.session`.
  - Write no fourth leg engine.

---

## File Structure

| File | Create / Modify | Responsibility |
|---|---|---|
| `mstate.py` | Create | Pure state layer. `fold` (trend memory, efficiency, volatility, 0 DTE, premium vs delta), `norm` (the bar-range yardstick from `data/backtest`), `gauges`, `chip`, `legal` / `signs` / `card` / `cards` / `card_line` (the zone card), `cross` (writers-sync, TREND DAY / ROTATION, COIL → ESCAPE). |
| `test_mstate.py` | Create | Synthetic-frame tests of every `mstate` function. |
| `jarvis.py` | Modify | `_atm_chain` (split out of `_legs`). `_build` stores `mstate` / `pivots` / `zone_cards` / `nf` and adds zone-row fields. `count` drops `setup`. `call()` makes the state word the word and adds `action` / `mstate` / `chips` / `zone`. `_grade` added. `calls()` carries the new keys. `reads()` fixes the `all3` N slot. `days()` adds BANKNIFTY. |
| `test_jarvis_state.py` | Create | Tests of the jarvis / jarvis_log / server wiring (kept out of `test_jarvis.py`, which holds uncommitted foreign edits). |
| `test_jarvis.py` | Modify | The record tests that assert the ACTION word read `c["action"]["said"]` (Task 4 only). |
| `jarvis_log.py` | Modify | `write` / `read` take `kind`. `row` logs `action` / `vol`. `self_line` counts PALAT? from `action`. `state_row` added. `card` passes `mstate` / `action` / `chips` / `zone` / `xstate`. |
| `test_jarvis_log.py` | Modify | The exact-row assertion gets `action` / `vol`. The pass test gets BANKNIFTY (Task 13). |
| `server.py` | Modify | `_jarvis_log` writes the state log. `_jarvis_cross` attaches `xstate`. `JARVIS_PASS_IDX` gets BANKNIFTY. |
| `jarvis_thresholds.json` | Modify | The `mstate.*` [I] numbers and their `_why`. |
| `test_thresholds.py` | Modify | Covers `mstate` beside `jarvis` / `legs`. |
| `docs/kahani/review/mockup/jarvis2.html` | Modify | The state line leads, the ACTION word becomes a chip, then the zone row, the ALERT row, and the BANKNIFTY option. |
| `tools/mstate_replay.py` | Create | Spec §9 behaviour check over 28 Oct–5 Nov: counts only, refused in market hours. |
| `test_mstate_replay.py` | Create | The replay tool's guard and table. |
| `trigger_log.py` | Modify | zone3 rows log their 3-min bar's vwap / u3 / d3 (§6a) |
| `test_zone3.py` | Modify | that logging |
| `docs/live/NOTEPAD.md` | Modify | Section A rows A256 / A257 / A258, and the replay's counts in section B. |

Ground truth these tasks are written against (6 Nov working tree):

- **`jarvis.py`**
  - `build` :291, `_build` :340, the ZONE rows :808-817, `bnf` / `sx` :856, `_legs(...)` call :902, ACTION words :903-907, `call(data)` :908.
  - `_legs` :934-959, `call()` :1078 (its return :1340-1352).
  - `PIECES` :1379, `days()` :1426 (loop :1437), `calls()` :1440 (keys :1448).
  - `count` :1482-1629 (the `setup` piece :1609-1620).
  - `said` :1632, `_box` :1639, `action_words` :1678-1774, `reads` :1837 (`sync_at` :1873-1879).
- **`legs.py`:** `read` :216-517, TREND quality :335, `_chain_leg` / `_lad`.
- **`reader.py`:** `Engine` :287 (`step` :347, `_cut` :411, `_confirm` :466), the auction :802-852.
- **`decode.py`:** `ZZ_PCT` / `ZZ_SIG` :58, `zz_thr` :129-140.
- **`hold2.py`:** `losing` :130.
- **`effort.py`:** `lam_at` :148, `HI` / `MIN_HIST` :32.
- **`jarvis_log.py`:** `_path` :31, `read` :35, `write` :40, `row` :69, `self_line` :106, `card` :145.
- **`server.py`:** `_jarvis_reply` :4743 (build :4774, log :4781), `JARVIS_PASS_IDX` :4794, `_jarvis_log` :4858.
- **`jarvis2.html`:** `renderCard` :588-650, the index picker :235.

---

## Phase 1 — the state layer (spec §10.1)

### Task 1: `mstate.py` — trend memory and efficiency

**Files:**
- Create: `mstate.py`
- Create: `test_mstate.py`
- Modify: `jarvis_thresholds.json` (keys before `"_why"`, reasons at the end of `"_why"`, `"_rule"` text)
- Modify: `test_thresholds.py:10-12,139-149`
- Modify: `docs/live/NOTEPAD.md` (section A, a row after A255)

**Interfaces:**
- Consumes:
  - `reader.Engine(idx, day, lot, unit)`, `.step(minute)`, `.legs[*]` with `dir`, `px0`, `px1`, `t0`, `t1`.
  - `reader.canonical(book_mins, candles)`, `reader.hm(ms)`, `reader.TH["K"]`.
  - `decode.ZZ_PCT`, `decode.ZZ_SIG`; `hold2.losing(d, spot, peak_spot, U)`; `fronts.side_front(fronts, side)`, `fronts.UNWINDING`.
  - `legs._fmt`; `fold.ms(day, "HH:MM")`; `sensex_flow.on(idx)`; `thresholds.stamp()` / `thresholds.get(name, default)`.
- Produces:
  - `mstate.fold(d) -> (rows, pivots)`.
    - Each row is `{"t", "word", "dir", "conf", "since", "why", "line", "eff", "vx", "price"}`.
    - `word` is one of `"OPENING"`, `"RANGE"`, `"TREND ▲"`, `"TREND ▼"`, `"TREND ▲ (leg, unconfirmed)"`, `"TREND ▼ (leg, unconfirmed)"`.
    - `pivots` is `[{"kind": "H"|"L", "lab": "H"|"L"|"HH"|"LH"|"HL"|"LL", "px", "t", "known"}]`.
  - `mstate.chip(row) -> str`.
  - `mstate._thresholds()`, `mstate._I`, `mstate._DEF`.

- [ ] **Step 1: Write the failing tests**

Create `test_mstate.py`:

```python
"""test_mstate.py -- the market state (plan docs/superpowers/plans/2026-11-06-jarvis-market-state.md). Synthetic frames
only: pure functions, no record, no clock."""
import json

import mstate


def _hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def _path(points):
    """[(minute index, price), ...] -> one price per minute, straight lines between the points."""
    out = []
    for (i0, p0), (i1, p1) in zip(points, points[1:]):
        out += [p0 + (p1 - p0) * (k - i0) / (i1 - i0) for k in range(i0, i1)]
    return out + [points[-1][1]]


def _frame(px, idx="NIFTY", rows=None):
    """A jarvis.build-shaped frame from 09:15, one futures price a minute (spot 40 below, VWAP flat at the open)."""
    n = len(px)
    mins = [_hm(555 + i) for i in range(n)]
    return {"ok": True, "day": "2026-11-05", "idx": idx, "mins": mins, "fut": list(px), "fo": list(px),
            "fhi": [p + 1 for p in px], "flo": [p - 1 for p in px], "spot": [p - 40 for p in px],
            "vwap": [px[0]] * n, "sd": [20.0] * n, "step": 50, "timeline": [{"fronts": []} for _ in range(n)],
            "legs": {"rows": rows or [{"t": m, "lean": 0, "word": "NO LEG", "leg": None} for m in mins]},
            "ctx": {"opt": {}}, "wf_ce": [None] * n, "wf_pe": [None] * n}


# 09:15 24,000 -> 10:00 24,200 (H) -> 10:15 24,120 (HL) -> 10:45 24,300 (HH) -> 11:00 24,220 (HL) -> 11:30 24,400
# -> 12:00 24,150 (through the HL line)
ZIG = _path([(0, 24000), (45, 24200), (60, 24120), (90, 24300), (105, 24220), (135, 24400), (165, 24150)])


def test_hh_then_hl_confirms_trend_up_and_the_line_is_the_hl():
    rows, piv = mstate.fold(_frame(ZIG))
    assert [p["lab"] for p in piv][:5] == ["L", "H", "HL", "HH", "HL"]
    first = next(r for r in rows if r["word"] == "TREND ▲")
    assert "11:00" < first["t"] < "11:30" and first["line"] == "line 24,219 (HL 11:00)"
    assert first["why"] == "TREND ▲: HH 24,301 (10:45) then HL 24,219 (11:00) held" and first["since"] == first["t"]
    assert all(r["word"] in ("OPENING", "RANGE") for r in rows if r["t"] < first["t"])   # one HL alone is not a trend


def test_a_close_through_the_hl_by_more_than_a_candle_ends_it_as_range():
    rows, _ = mstate.fold(_frame(ZIG))
    end = next(r for r in rows if r["t"] > "11:30" and r["word"] != "TREND ▲")
    assert end["word"] == "RANGE" and end["why"].startswith("structure: a 3-min close")
    assert "below the HL 24,219 (11:00)" in end["why"]
    assert all(r["word"] == "TREND ▲" for r in rows if "11:30" <= r["t"] < end["t"])   # no flicker before it


def test_writers_giving_up_ends_the_trend():
    d = _frame(ZIG)
    k = d["mins"].index("11:41")                              # 11:41 is a 3-min close; spot is 24,316 then
    for j in range(k, len(d["mins"])):
        d["timeline"][j] = {"fronts": [{"k": 24300.0, "side": "PE", "state": "UNWINDING", "peak_at": "11:30",
                                        "oi": 80.0, "chg": -9.0, "peak": 12.0}]}
    rows, _ = mstate.fold(d)
    assert rows[k - 1]["word"] == "TREND ▲" and rows[k]["word"] == "RANGE"
    assert rows[k]["why"].startswith("writers gave up: 24,300s PE UNWINDING")


def test_a_trend_leg_reads_unconfirmed_and_low_efficiency_reads_range():
    px = _path([(0, 24000), (40, 24150)])
    mins = [_hm(555 + i) for i in range(len(px))]
    leg = {"dir": 1, "quality": "TREND", "pts": 150, "origin": 24000.0, "origin_t": "09:15"}
    rows = [{"t": m, "lean": 1, "word": "OPENING", "leg": leg} for m in mins]
    out, _ = mstate.fold(_frame(px, rows=rows))
    assert out[-1]["word"] == "TREND ▲ (leg, unconfirmed)" and out[-1]["line"] == "line 24,000 (origin 09:15)"
    chop = _path([(0, 24000)] + [(5 * k, 24000 + (30 if k % 2 else -30)) for k in range(1, 12)] + [(60, 24010)])
    mins = [_hm(555 + i) for i in range(len(chop))]
    out, _ = mstate.fold(_frame(chop, rows=[{"t": m, "lean": 1, "word": "TREND", "leg": leg} for m in mins]))
    assert out[-1]["word"] == "RANGE" and out[-1]["why"].startswith("RANGE: a TREND leg, but efficiency")


def test_the_fold_is_causal():
    d = _frame(ZIG)
    full, _ = mstate.fold(d)
    k = 120
    cut = {key: (v[:k] if isinstance(v, list) and len(v) == len(d["mins"]) else v) for key, v in d.items()}
    cut["legs"] = {"rows": d["legs"]["rows"][:k]}
    part, _ = mstate.fold(cut)
    assert part == full[:k]


def test_no_rate_and_a_chip_with_its_number():
    rows, _ = mstate.fold(_frame(ZIG))
    assert "%" not in json.dumps(rows)
    up = next(r for r in rows if r["word"] == "TREND ▲")
    assert mstate.chip(up) == "upar ka trend · 24,219"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest -q test_mstate.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'mstate'`.

- [ ] **Step 3: Write `mstate.py`**

```python
"""mstate.py -- JARVIS MARKET STATE: the state word with memory per index (TREND ▲ / TREND ▼ / RANGE), the volatility
state, the zone card and the cross-index read. Spec docs/superpowers/specs/2026-11-06-jarvis-market-state-design.md
(approved 6 Nov 2026); plan docs/superpowers/plans/2026-11-06-jarvis-market-state.md.

STRUCTURE (spec §3) reuses reader.py's leg engine -- pivots confirmed on closes -- fed Jarvis's 3-minute bars (the
frame's futures; SENSEX's spot, §1q), its reversal decode.py's size at each close (max of 50 NIFTY-equivalent points,
0.5 x the IV-priced 30-min sigma). reader's own auction (`au`) is NOT the word: it breaks live on a minute's low and
flips straight to the opposite trend; the spec's trend ends only at her §1e close rule or her §1m "gave up".
  TREND ▲      a close confirmed a higher low after a higher high (or after the day's first high while a legs.py TREND ▲
               leg is live: the leg was the break). The line is the latest HL. TREND ▼ mirrors it.
  ends         the first of: a 3-min close past the line by more than one median 1-min candle (§1e), or the trend-side
               front UNWINDING with spot on its writers' losing side by 0.25U (hold2.losing, §1m) -> RANGE.
  unconfirmed  a legs.py TREND leg with no pullback held yet reads "TREND ▲ (leg, unconfirmed)" -- unless efficiency
               (net move / path over EFF_WIN min) < EFF_RANGE with >= VWAP_X VWAP returns: RANGE. A leg whose trend just
               ended never comes back as unconfirmed (it must be a new leg).
Pure: no I/O, no clock. Causal: row i reads minutes <= i only. Counts, never a %. DISPLAY ONLY: no gate, no order path;
her §1d gate is not touched (phase 4 is a registration she signs)."""
from __future__ import annotations

import statistics

import decode
import fold as _fold
import fronts
import hold2
import legs
import reader
import thresholds

START_M = 555                 # 09:15: her 3-min bars count from here (legs.START_M)
ARR = {1: "▲", -1: "▼"}
EFF_WIN = 45                  # [I] efficiency = |net move| / path of the 1-min closes over the last 45 min (spec §3)
EFF_RANGE = 0.3               # [I] an unconfirmed TREND leg reads RANGE at efficiency < 0.3 ...
VWAP_X = 2                    # [I] ... with >= 2 VWAP returns (fut crossing its VWAP) in those 45 min
HING = {"TREND ▲": "upar ka trend", "TREND ▼": "neeche ka trend", "RANGE": "range: dono taraf",
        "OPENING": "abhi swing nahi"}  # her Hinglish chips (symbols need Hinglish chips)

_I = ("EFF_WIN", "EFF_RANGE", "VWAP_X")
_DEF = {n: globals()[n] for n in _I}
_APPLIED = [None]
_fmt = legs._fmt


def _thresholds():
    """The [I] numbers from jarvis_thresholds.json ("mstate.<NAME>"), applied again only when the file changed."""
    st = thresholds.stamp()
    if st != _APPLIED[0]:
        globals().update({n: thresholds.get(f"mstate.{n}", v) for n, v in _DEF.items()})
        _APPLIED[0] = st


_thresholds()


def _m(t):
    return int(t[:2]) * 60 + int(t[3:5])


def _hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def _series(d):
    """The frame's price for structure -> (close, high, low, "fut" | "spot"): SENSEX on its spot (§1q), the rest on
    their futures' 1-min bars."""
    import sensex_flow
    if sensex_flow.on(d.get("idx")):
        return d["spot"], d["spot"], d["spot"], "spot"
    return d["fut"], d.get("fhi") or d["fut"], d.get("flo") or d["fut"], "fut"


def _opt(d, t, back=3):
    """The chain's ATM read (ctx.opt) at minute t, else the last within `back` min carrying an IV, else None."""
    o = (d.get("ctx") or {}).get("opt") or {}
    ks = [k for k in o if k <= t and _m(t) - _m(k) <= back and o[k].get("iv") is not None]
    return o[max(ks)] if ks else None


def _thr(d, i, c):
    """decode.zz_thr's reversal at minute i: max(50 pts NIFTY-equivalent, 0.5 x the IV-priced 30-min sigma) [I], the
    IV the chain's ATM IV at or just before i; none -> the floor alone (decode's own fallback)."""
    o = _opt(d, d["mins"][i])
    s30 = d["spot"][i] * o["iv"] / 100 / 365 ** 0.5 * (365 * 30 / (252 * 375)) ** 0.5 if o else 0.0
    return max(decode.ZZ_PCT * c, decode.ZZ_SIG * s30)


def _pivot(piv, kind, px, t, known):
    """Append a pivot labelled against the last one of its kind: HH / LH, HL / LL (the day's first: H or L)."""
    prev = next((p for p in reversed(piv) if p["kind"] == kind), None)
    lab = kind if prev is None else ({"H": "HH", "L": "HL"} if px > prev["px"] else {"H": "LH", "L": "LL"})[kind]
    p = {"kind": kind, "lab": lab, "px": round(px, 2), "t": t, "known": known}
    piv.append(p)
    return p


def _confirms(piv, live):
    """TREND from the pivots, read at a close that confirmed a new one -> 1 / -1 / None. ▲: the newest pivot is an HL
    and the one before it an HH -- or the day's first H while a legs.py TREND ▲ leg is live (`live`). ▼ mirrors."""
    if len(piv) < 2:
        return None
    p, q = piv[-1], piv[-2]
    for D, low, high, qk in ((1, "HL", "HH", "H"), (-1, "LH", "LL", "L")):
        if p["lab"] == low and q["kind"] == qk and (q["lab"] == high or (q["lab"] == qk and live == D)):
            return D
    return None


def _gave_up(d, i, D):
    """Her §1m "gave up" at the close ending minute i for a trend D -> the why, or None: the trend-side front (▲: PE,
    ▼: CE; fronts.side_front of the minute's fronts) UNWINDING with spot on its writers' losing side of the spot at the
    front's peak minute by more than 0.25U (hold2.losing; U = max(the frame's VWAP sigma, 0.1 % of spot), legs.U_at's)."""
    side = "PE" if D > 0 else "CE"
    f = fronts.side_front(((d.get("timeline") or [{}] * (i + 1))[i] or {}).get("fronts"), side)
    if not f or f.get("state") != fronts.UNWINDING or f.get("peak_at") not in d["mins"]:
        return None
    j, spot = d["mins"].index(f["peak_at"]), d["spot"][i]
    U = max(d["sd"][i] or 0.0, 0.001 * spot)
    if hold2.losing(D, spot, d["spot"][j], U) != "lose":
        return None
    return (f"writers gave up: {_fmt(f['k'])}s {side} UNWINDING, spot {_fmt(spot)} past their {f['peak_at']} spot "
            f"{_fmt(d['spot'][j])} by more than 0.25U")


def _eff(C, fut, vw, i):
    """(efficiency, VWAP returns) over the last EFF_WIN frame minutes: |net| / path of the closes, and how often the
    future crossed its VWAP; (None, 0) before EFF_WIN minutes or on a flat path."""
    j = i - EFF_WIN
    if j < 0:
        return None, 0
    path = sum(abs(C[k] - C[k - 1]) for k in range(j + 1, i + 1))
    sg = [1 if f >= w else -1 for f, w in zip(fut[j:i + 1], vw[j:i + 1]) if f is not None and w is not None]
    return (round(abs(C[i] - C[j]) / path, 2) if path else None), sum(1 for a, b in zip(sg, sg[1:]) if a != b)


def chip(row):
    """The state word's Hinglish chip with its number: "upar ka trend · 24,551" (rule: every symbol a chip)."""
    w = row["word"]
    base = ("upar ka leg, pakka nahi" if row["dir"] > 0 else "neeche ka leg, pakka nahi") \
        if w.endswith("(leg, unconfirmed)") else HING.get(w, w)
    return base + (f" · {row['line'].split()[1]}" if row.get("line") else "")


def fold(d):
    """The state per frame minute -> (rows, pivots). rows[i] = {"t", "word", "dir", "conf", "since", "why", "line",
    "eff", "vx", "price"}; pivots = the day's ordered swing list [{"kind", "lab", "px", "t", "known"}] (known = the close
    that confirmed it). Reads d["legs"]["rows"] for the unconfirmed leg; a frame without them has none."""
    mins = d["mins"]
    C, Hh, Ll, what = _series(d)
    LR = (d.get("legs") or {}).get("rows") or []
    eng, piv, nlegs = None, [], 0
    st = {"dir": 0, "conf": False, "line": None, "line_t": None, "why": "no swing confirmed yet", "ended": None}
    word = since = None
    cand, out = [], []
    for i, t in enumerate(mins):
        m = _m(t)
        cand.append(abs(C[i] - C[i - 1]) if what == "spot" and i else Hh[i] - Ll[i] if what == "fut" else None)
        row = LR[i] if i < len(LR) and LR[i].get("t") == t else {}
        lg = row.get("leg") or {}
        live = lg.get("dir") if lg.get("quality") == "TREND" and row.get("lean") == lg.get("dir") else 0
        if (m - START_M) % 3 == 2:                                 # her 3-min close: the bar m-2..m is complete
            js = [j for j in range(max(0, i - 2), i + 1) if _m(mins[j]) >= m - 2]
            o = (d.get("fo") or C)[js[0]] if what == "fut" else C[max(js[0] - 1, 0)]
            bar = {"t": _fold.ms(d["day"], _hm(m - 2)), "o": o, "h": max(Hh[j] for j in js),
                   "l": min(Ll[j] for j in js), "c": C[i], "vol": 0.0, "oi": None}
            thr = _thr(d, i, C[i])
            if eng is None:
                eng = reader.Engine(idx=d.get("idx") or "?", day=d["day"], lot=1, unit=thr / reader.TH["K"])
            eng.delta = thr            # decode's size at this close (reader freezes its ruler at the open; spec §3: per close)
            for x in reader.canonical([], [bar]):
                eng.step(x)
            new = []
            for leg in eng.legs[nlegs:]:
                if not piv:                                        # the day's first leg: its start is a pivot too
                    new.append(_pivot(piv, "L" if leg["dir"] > 0 else "H", leg["px0"], reader.hm(leg["t0"]), t))
                new.append(_pivot(piv, "H" if leg["dir"] > 0 else "L", leg["px1"], reader.hm(leg["t1"]), t))
            nlegs = len(eng.legs)
            one = statistics.median([x for x in cand if x is not None])      # one median 1-min candle (her §1e)
            if st["conf"]:
                D = st["dir"]
                for p in new:                                      # a new HL (LH) carries the line
                    if p["lab"] == ("HL" if D > 0 else "LH") and D * (p["px"] - st["line"]) > 0:
                        st.update(line=p["px"], line_t=p["t"])
                end = (f"structure: a 3-min close {_fmt(C[i])} {'below' if D > 0 else 'above'} the "
                       f"{'HL' if D > 0 else 'LH'} {_fmt(st['line'])} ({st['line_t']}) by more than one 1-min candle "
                       f"({one:.1f})") if D * (C[i] - st["line"]) < -one else _gave_up(d, i, D)
                if end:
                    st.update(dir=0, conf=False, line=None, line_t=None, why=end, ended=(D, lg.get("origin_t")))
            elif new:
                D = _confirms(piv, live)
                if D:
                    p, q = piv[-1], piv[-2]
                    st.update(dir=D, conf=True, line=p["px"], line_t=p["t"], ended=None,
                              why=f"TREND {ARR[D]}: {q['lab']} {_fmt(q['px'])} ({q['t']}) then {p['lab']} "
                                  f"{_fmt(p['px'])} ({p['t']}) held")
        eff, vx = _eff(C, d["fut"], d["vwap"], i)
        if st["conf"]:
            D = st["dir"]
            w, why = f"TREND {ARR[D]}", st["why"]
            line = f"line {_fmt(st['line'])} ({'HL' if D > 0 else 'LH'} {st['line_t']})"
        elif live and (live, lg.get("origin_t")) != st["ended"]:
            D, line = live, f"line {_fmt(lg['origin'])} (origin {lg.get('origin_t')})"
            if eff is not None and eff < EFF_RANGE and vx >= VWAP_X:
                w, D = "RANGE", 0
                why = f"RANGE: a TREND leg, but efficiency {eff:.2f} with {vx} VWAP returns in {EFF_WIN} min"
            else:
                w = f"TREND {ARR[live]} (leg, unconfirmed)"
                why = (f"a TREND leg {lg.get('pts')} pts from {_fmt(lg['origin'])} ({lg.get('origin_t')}): "
                       "no pullback has held yet")
        elif not piv and word in (None, "OPENING"):                # never back to OPENING once a word was said
            w, D, line, why = "OPENING", 0, None, "OPENING: no swing confirmed yet and no TREND leg"
        else:
            w, D, line = "RANGE", 0, None
            why = st["why"] if st["why"].startswith(("structure", "writers")) else \
                "RANGE: overlapping swings " + " ".join(p["lab"] for p in piv[-4:])
        if w != word:
            word, since = w, t
        out.append({"t": t, "word": w, "dir": D, "conf": st["conf"], "since": since, "why": why, "line": line,
                    "eff": eff, "vx": vx, "price": what})
    return out, piv
```

- [ ] **Step 4: Put the [I] numbers in the thresholds file and make `test_thresholds.py` cover `mstate`**

In `jarvis_thresholds.json`, replace the line ` "legs.HORIZON": 45,` with:

```json
 "legs.HORIZON": 45,
 "mstate.EFF_WIN": 45,
 "mstate.EFF_RANGE": 0.3,
 "mstate.VWAP_X": 2,
```

Replace `  "legs.HORIZON": "the after-the-fact outcome window of the forward log, 45 min"` with:

```json
  "legs.HORIZON": "the after-the-fact outcome window of the forward log, 45 min",
  "mstate.EFF_WIN": "the state's efficiency: |net move| / path of the 1-min closes over the last 45 min (spec 2026-11-06 §3, A256)",
  "mstate.EFF_RANGE": "an unconfirmed TREND leg reads RANGE below efficiency 0.3 ...",
  "mstate.VWAP_X": "... with >= 2 VWAP returns in those 45 min"
```

In `"_rule"`, replace `the [I] numbers of jarvis.py and legs.py live` with `the [I] numbers of jarvis.py, legs.py and mstate.py live`.

In `test_thresholds.py`, change `import legs` to:

```python
import legs
import mstate
```

Then change `for mod, path in ((jarvis, "jarvis.py"), (legs, "legs.py")):` to `for mod, path in ((jarvis, "jarvis.py"), (legs, "legs.py"), (mstate, "mstate.py")):`, and change `assert keys == {f"{m.__name__}.{n}" for m in (jarvis, legs) for n in m._I}` to `assert keys == {f"{m.__name__}.{n}" for m in (jarvis, legs, mstate) for n in m._I}`.

- [ ] **Step 5: Write the NOTEPAD row**

In `docs/live/NOTEPAD.md`, insert this row directly after the `| A255 |` row (section A):

```markdown
| A256 | 6 Nov (her approved spec `docs/superpowers/specs/2026-11-06-jarvis-market-state-design.md`, 84f58ea; plan `docs/superpowers/plans/2026-11-06-jarvis-market-state.md` phase 1) | **Jarvis re-voted 9 pieces a minute and remembered one leg: one quiet minute flipped the word, and her zone trigger voted against a trend the writers backed.** | 5 Nov call log [M]: SENSEX's word changed 23×; the `setup` piece voted the 12:30 NIFTY sell against the trend (NOTEPAD B, 5 Nov) | `mstate.py`: the state word with memory (reader.py's pivots on Jarvis's 3-min bars, decode's reversal size; a trend ends only at her §1e close rule or §1m gave up), efficiency and the volatility state; the state word leads; the trigger leaves the count. [I] in `jarvis_thresholds.json`: `mstate.EFF_WIN` 45 min, `EFF_RANGE` 0.3, `VWAP_X` 2; Task 2 adds `NORM_N` 10 sessions, `NORM_MIN` 5, `RANGE_HI` 1.5×, `RANGE_LO` 0.67×, `GAUGE_WIN` 15 min, `VIX_PTS` 0.3, `IV_PTS` 0.5, `VOL_N` 2 gauges, `VOL_CLOSES` 2 closes | BUILDING (phase 1) |
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest -q test_mstate.py test_thresholds.py`
Expected: PASS (6 in `test_mstate.py`, all of `test_thresholds.py`).

- [ ] **Step 7: Stage (the commit is made at the phase end, on Mary's word)**

```bash
git add mstate.py test_mstate.py jarvis_thresholds.json test_thresholds.py
git add -p docs/live/NOTEPAD.md      # only the A256 hunk
```

---

### Task 2: `mstate.py` — the volatility state

**Files:**
- Modify: `mstate.py` (constants, `_I`, imports; add `norm`, `_norm`, `gauges`; replace `fold`)
- Test: `test_mstate.py` (append)
- Modify: `jarvis_thresholds.json`

**Interfaces:**
- Consumes:
  - `confluence_log.session(idx, day)["bars"]` (3-min bars `{"t", "h", "l", ...}`), `squeeze_score._paths(idx)`, `squeeze_score.BT`.
  - `legs._chain_leg(chain, t, side, k) -> (leg, spot)`.
  - `jarvis.wf_push(ce, pe)`, `jarvis.WF_L`; the frame's `ctx.vix` (`[[ts, vix, src], ...]`), `ctx.opt`, `wf_ce`, `wf_pe`, `fhi`, `flo`.
- Produces:
  - `mstate.norm(idx, day) -> ({slot: median range}, days_used_tuple)`.
  - `mstate.gauges(d, i, chain=None, nm=None) -> [{"k": "range"|"straddle"|"vix"|"iv"|"raftaar", "vote": 1|-1|0|None, "text"}]`.
  - `mstate.fold(d, chain=None, nm=None) -> (rows, pivots)`: rows gain `"vol": {"word": "EXPANDING"|"CONTRACTING"|"NORMAL"|"?"|None, "since", "up", "down", "read", "gauges"}`.

- [ ] **Step 1: Write the failing tests** (append to `test_mstate.py`)

```python
# ---- Task 2: the volatility state ---------------------------------------------------------------------------------------

def _flat(n=60, idx="NIFTY"):
    return _frame([24000.0] * n, idx=idx)


def test_each_gauge_votes_or_says_why_it_could_not_check():
    d = _flat()
    i = d["mins"].index("10:02")                                  # a 3-min close (09:15 + 3k + 2)
    G = {g["k"]: g for g in mstate.gauges(d, i)}
    assert list(G) == ["range", "straddle", "vix", "iv", "raftaar"]
    assert all(g["vote"] is None and "could not check" in g["text"] for g in G.values())
    d["fhi"][i] += 30                                             # a 32-pt bar against a 10-pt slot median: EXPANDING
    nm = ({(mstate._m("10:00") - 555) // 3: 10.0}, ("a", "b", "c", "d", "e"))
    chain = {"09:47": {"spot": 23995.0, "ce": {24000: {"ltp": 100.0, "delta": 0.5}},
                       "pe": {24000: {"ltp": 110.0, "delta": -0.5}}},
             "10:02": {"spot": 23997.0, "ce": {24000: {"ltp": 108.0, "delta": 0.5}},
                       "pe": {24000: {"ltp": 109.0, "delta": -0.5}}}}
    d["ctx"] = {"vix": [["09:47", 14.0, None], ["10:02", 14.5, None]],
                "opt": {"09:47": {"iv": 14.0}, "10:02": {"iv": 15.0}}}
    d["wf_ce"][i], d["wf_pe"][i] = -12.0, 0.0                     # call writers covering, puts not against: running
    G = {g["k"]: g for g in mstate.gauges(d, i, chain, nm)}
    assert {k: g["vote"] for k, g in G.items()} == {"range": 1, "straddle": 1, "vix": 1, "iv": 1, "raftaar": 1}
    assert G["straddle"]["text"].startswith("24,000s straddle 210.0 → 217.0") and "%" not in json.dumps(G)


def test_the_volatility_word_needs_two_closes(monkeypatch):
    d = _flat(90)
    votes = {t: ([1, 1, 0, None, 0] if t >= "10:05" else [-1, -1, 0, 0, None])
             for t in d["mins"] if (mstate._m(t) - 555) % 3 == 2}
    monkeypatch.setattr(mstate, "gauges", lambda d, i, chain=None, nm=None: [
        {"k": str(n), "vote": v, "text": ""} for n, v in enumerate(votes[d["mins"][i]])])
    rows, _ = mstate.fold(d)
    at = {r["t"]: r["vol"]["word"] for r in rows}
    assert at["09:17"] == "CONTRACTING"                           # the day's first close says it at once
    assert at["10:05"] == "CONTRACTING" and at["10:08"] == "EXPANDING"   # one close is not enough; two are
    assert rows[-1]["vol"]["since"] == "10:08" and rows[-1]["vol"]["up"] == 2


def test_the_bar_range_yardstick_reads_prior_sessions_only(tmp_path, monkeypatch):
    import squeeze_score
    monkeypatch.setattr(squeeze_score, "BT", str(tmp_path))
    assert mstate.norm("NIFTY", "2026-11-05") == ({}, ())          # nothing on the record: could not check, never zero
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest -q test_mstate.py`
Expected: FAIL with `AttributeError: module 'mstate' has no attribute 'gauges'`.

- [ ] **Step 3: Add the gauges and replace `fold`**

In `mstate.py`, replace `import statistics` with:

```python
import functools
import os
import statistics
```

After the `VWAP_X = 2 ...` line, add:

```python
NORM_N = 10                   # [I] the bar-range yardstick: the same 3-min slot's median range over the last 10 sessions
NORM_MIN = 5                  # [I] ... read only with >= 5 of them on the record (fewer: could not check)
RANGE_HI, RANGE_LO = 1.5, 0.67  # [I] a bar >= 1.5x its slot's median votes EXPANDING, <= 0.67x CONTRACTING
GAUGE_WIN = 15                # [I] the straddle / VIX / IV gauges read their change over the last 15 min
VIX_PTS = 0.3                 # [I] India VIX up >= 0.3 in 15 min votes EXPANDING, down >= 0.3 CONTRACTING
IV_PTS = 0.5                  # [I] ATM IV up >= 0.5 vol points in 15 min votes EXPANDING, down >= 0.5 CONTRACTING
VOL_N = 2                     # [I] EXPANDING / CONTRACTING needs 2 gauges that way (and more than the other way) ...
VOL_CLOSES = 2                # [I] ... at 2 consecutive 3-min closes (spec §4); the day's first close says it at once
```

Replace the `_I = (...)` line with:

```python
_I = ("EFF_WIN", "EFF_RANGE", "VWAP_X", "NORM_N", "NORM_MIN", "RANGE_HI", "RANGE_LO", "GAUGE_WIN", "VIX_PTS", "IV_PTS",
      "VOL_N", "VOL_CLOSES")
```

In the module docstring, replace `Pure: no I/O, no clock.` with `Pure: no I/O but norm() (the prior sessions' bars, read only), no clock.`

Insert before `def chip(row):`:

```python
def norm(idx, day):
    """The bar-range yardstick -> ({3-min slot: the median high - low of that slot's futures bar over the last NORM_N
    sessions before `day`}, the days used): the futures' 1-min sessions on the record (data/backtest via
    confluence_log.session, the zone machine's own series). Read only; cached per (idx, day, the backtest dir)."""
    import squeeze_score
    return _norm(idx, day, squeeze_score.BT, NORM_N)


@functools.lru_cache(maxsize=16)
def _norm(idx, day, bt, n):
    import confluence_log
    import squeeze_score
    prev = sorted(x for x in (os.path.basename(p)[4:14] for p in squeeze_score._paths(idx)) if x < day)[-n:]
    by, used = {}, []
    for x in prev:
        s = confluence_log.session(idx, x)
        if not s:
            continue
        used.append(x)
        for b in s["bars"]:
            by.setdefault((_m(b["t"]) - START_M) // 3, []).append(b["h"] - b["l"])
    return {k: statistics.median(v) for k, v in by.items()}, tuple(used)


def gauges(d, i, chain=None, nm=None):
    """The five volatility gauges at the 3-min close ending at minute i (spec §4) -> [{"k", "vote", "text"}]; vote +1
    EXPANDING, -1 CONTRACTING, 0 neither, None could not check (its text says why). `chain` = jarvis._atm_chain's
    {HH:MM: {"spot", "ce": {k: {"ltp", "delta"}}, "pe": ...}}; `nm` = norm()'s pair."""
    import jarvis
    mins, t = d["mins"], d["mins"][i]
    m, step, G = _m(t), d.get("step") or 50, []
    t0 = _hm(m - GAUGE_WIN)
    js = [j for j in range(max(0, i - 2), i + 1) if _m(mins[j]) >= m - 2]
    hi, lo = max(d["fhi"][j] for j in js), min(d["flo"][j] for j in js)
    slots, used = nm or ({}, ())
    med = slots.get((m - START_M) // 3)
    if len(used) < NORM_MIN or not med:
        G.append({"k": "range", "vote": None, "text": f"bar range: could not check — {len(used)} prior sessions on the "
                                                       f"record (needs {NORM_MIN})"})
    else:
        x = (hi - lo) / med
        G.append({"k": "range", "vote": 1 if x >= RANGE_HI else -1 if x <= RANGE_LO else 0,
                  "text": f"3-min range {hi - lo:.0f} pts = {x:.1f}× its {_hm(m - 2)} median ({len(used)} sessions)"
                          + (" · SENSEX fut: patla" if d.get("idx") == "SENSEX" else "")})
    a, b = (chain or {}).get(t0), (chain or {}).get(t)
    k0 = None if not a else round(a["spot"] / step) * step
    ls = [legs._chain_leg(chain, x, s, k0)[0] for x in (t0, t) for s in ("ce", "pe")] if a and b else []
    if not ls or any(not g or g.get("ltp") is None for g in ls):
        G.append({"k": "straddle", "vote": None, "text": f"straddle: could not check — no ATM premium at {t0} and {t}"})
    else:
        s0, s1, mv = ls[0]["ltp"] + ls[1]["ltp"], ls[2]["ltp"] + ls[3]["ltp"], abs(b["spot"] - a["spot"])
        G.append({"k": "straddle", "vote": 1 if s1 > s0 else -1 if mv < step / 2 else 0,
                  "text": f"{_fmt(k0)}s straddle {s0:.1f} → {s1:.1f} in {GAUGE_WIN} min, spot moved {mv:.0f} (no theta on "
                          "the record: a rise is net of decay; a fall counts only with spot inside half a step)"})
    vx = [x for x in (d.get("ctx") or {}).get("vix") or () if x[0] <= t]
    v0 = next((x for x in reversed(vx) if x[0] <= t0), None)
    if not vx or not v0:
        G.append({"k": "vix", "vote": None, "text": f"VIX: could not check — no row at or before {t0}"})
    else:
        ch = vx[-1][1] - v0[1]
        G.append({"k": "vix", "vote": 1 if ch >= VIX_PTS else -1 if ch <= -VIX_PTS else 0,
                  "text": f"VIX {v0[1]:.2f} → {vx[-1][1]:.2f} ({ch:+.2f}) in {GAUGE_WIN} min"
                          + (" (backfilled)" if vx[-1][2] == "backfill" else "")})
    o1, o0 = _opt(d, t), _opt(d, t0)
    if not o1 or not o0:
        G.append({"k": "iv", "vote": None, "text": f"ATM IV: could not check — no chain IV at {t0} and {t}"})
    else:
        ch = o1["iv"] - o0["iv"]
        G.append({"k": "iv", "vote": 1 if ch >= IV_PTS else -1 if ch <= -IV_PTS else 0,
                  "text": f"ATM IV {o0['iv']:.1f} → {o1['iv']:.1f} ({ch:+.1f}) in {GAUGE_WIN} min"})
    ce, pe = (d.get("wf_ce") or [None] * (i + 1))[i], (d.get("wf_pe") or [None] * (i + 1))[i]
    if ce is None or pe is None:
        G.append({"k": "raftaar", "vote": None, "text": "writers ±7: could not check — chain not read this minute"})
    else:
        p = jarvis.wf_push(ce, pe)
        both = ce >= jarvis.WF_L and pe >= jarvis.WF_L
        G.append({"k": "raftaar", "vote": 1 if p else -1 if both else 0,
                  "text": (f"writers ±7: {'call' if p > 0 else 'put'} writers running" if p else
                           "writers ±7: both sides adding" if both else "writers ±7: neither running")
                          + f" (CE {ce:+.1f}L · PE {pe:+.1f}L / 3 min)"})
    return G
```

Replace the whole `def fold(d):` function with:

```python
def fold(d, chain=None, nm=None):
    """The state per frame minute -> (rows, pivots). rows[i] = {"t", "word", "dir", "conf", "since", "why", "line",
    "eff", "vx", "price", "vol"}; pivots = the day's ordered swing list [{"kind", "lab", "px", "t", "known"}] (known =
    the close that confirmed it). Reads d["legs"]["rows"] for the unconfirmed leg (a frame without them has none),
    `chain` / `nm` for the volatility gauges (absent: those gauges could not check)."""
    mins = d["mins"]
    C, Hh, Ll, what = _series(d)
    LR = (d.get("legs") or {}).get("rows") or []
    eng, piv, nlegs = None, [], 0
    st = {"dir": 0, "conf": False, "line": None, "line_t": None, "why": "no swing confirmed yet", "ended": None}
    vol = {"word": None, "since": None, "up": 0, "down": 0, "read": 0, "gauges": []}
    word = since = vpend = None
    cand, out = [], []
    for i, t in enumerate(mins):
        m = _m(t)
        cand.append(abs(C[i] - C[i - 1]) if what == "spot" and i else Hh[i] - Ll[i] if what == "fut" else None)
        row = LR[i] if i < len(LR) and LR[i].get("t") == t else {}
        lg = row.get("leg") or {}
        live = lg.get("dir") if lg.get("quality") == "TREND" and row.get("lean") == lg.get("dir") else 0
        if (m - START_M) % 3 == 2:                                 # her 3-min close: the bar m-2..m is complete
            js = [j for j in range(max(0, i - 2), i + 1) if _m(mins[j]) >= m - 2]
            o = (d.get("fo") or C)[js[0]] if what == "fut" else C[max(js[0] - 1, 0)]
            bar = {"t": _fold.ms(d["day"], _hm(m - 2)), "o": o, "h": max(Hh[j] for j in js),
                   "l": min(Ll[j] for j in js), "c": C[i], "vol": 0.0, "oi": None}
            thr = _thr(d, i, C[i])
            if eng is None:
                eng = reader.Engine(idx=d.get("idx") or "?", day=d["day"], lot=1, unit=thr / reader.TH["K"])
            eng.delta = thr            # decode's size at this close (reader freezes its ruler at the open; spec §3: per close)
            for x in reader.canonical([], [bar]):
                eng.step(x)
            new = []
            for leg in eng.legs[nlegs:]:
                if not piv:                                        # the day's first leg: its start is a pivot too
                    new.append(_pivot(piv, "L" if leg["dir"] > 0 else "H", leg["px0"], reader.hm(leg["t0"]), t))
                new.append(_pivot(piv, "H" if leg["dir"] > 0 else "L", leg["px1"], reader.hm(leg["t1"]), t))
            nlegs = len(eng.legs)
            one = statistics.median([x for x in cand if x is not None])      # one median 1-min candle (her §1e)
            if st["conf"]:
                D = st["dir"]
                for p in new:                                      # a new HL (LH) carries the line
                    if p["lab"] == ("HL" if D > 0 else "LH") and D * (p["px"] - st["line"]) > 0:
                        st.update(line=p["px"], line_t=p["t"])
                end = (f"structure: a 3-min close {_fmt(C[i])} {'below' if D > 0 else 'above'} the "
                       f"{'HL' if D > 0 else 'LH'} {_fmt(st['line'])} ({st['line_t']}) by more than one 1-min candle "
                       f"({one:.1f})") if D * (C[i] - st["line"]) < -one else _gave_up(d, i, D)
                if end:
                    st.update(dir=0, conf=False, line=None, line_t=None, why=end, ended=(D, lg.get("origin_t")))
            elif new:
                D = _confirms(piv, live)
                if D:
                    p, q = piv[-1], piv[-2]
                    st.update(dir=D, conf=True, line=p["px"], line_t=p["t"], ended=None,
                              why=f"TREND {ARR[D]}: {q['lab']} {_fmt(q['px'])} ({q['t']}) then {p['lab']} "
                                  f"{_fmt(p['px'])} ({p['t']}) held")
            G = gauges(d, i, chain, nm)
            up, dn = sum(g["vote"] == 1 for g in G), sum(g["vote"] == -1 for g in G)
            rd = sum(g["vote"] is not None for g in G)
            cv = "?" if rd < VOL_N else "EXPANDING" if up >= VOL_N and up > dn else \
                "CONTRACTING" if dn >= VOL_N and dn > up else "NORMAL"
            vpend = None if cv == vol["word"] else [cv, vpend[1] + 1 if vpend and vpend[0] == cv else 1]
            if vpend and (vol["word"] is None or vpend[1] >= VOL_CLOSES):
                vol, vpend = dict(vol, word=cv, since=t), None
            vol = dict(vol, up=up, down=dn, read=rd, gauges=G)
        eff, vx = _eff(C, d["fut"], d["vwap"], i)
        if st["conf"]:
            D = st["dir"]
            w, why = f"TREND {ARR[D]}", st["why"]
            line = f"line {_fmt(st['line'])} ({'HL' if D > 0 else 'LH'} {st['line_t']})"
        elif live and (live, lg.get("origin_t")) != st["ended"]:
            D, line = live, f"line {_fmt(lg['origin'])} (origin {lg.get('origin_t')})"
            if eff is not None and eff < EFF_RANGE and vx >= VWAP_X:
                w, D = "RANGE", 0
                why = f"RANGE: a TREND leg, but efficiency {eff:.2f} with {vx} VWAP returns in {EFF_WIN} min"
            else:
                w = f"TREND {ARR[live]} (leg, unconfirmed)"
                why = (f"a TREND leg {lg.get('pts')} pts from {_fmt(lg['origin'])} ({lg.get('origin_t')}): "
                       "no pullback has held yet")
        elif not piv and word in (None, "OPENING"):                # never back to OPENING once a word was said
            w, D, line, why = "OPENING", 0, None, "OPENING: no swing confirmed yet and no TREND leg"
        else:
            w, D, line = "RANGE", 0, None
            why = st["why"] if st["why"].startswith(("structure", "writers")) else \
                "RANGE: overlapping swings " + " ".join(p["lab"] for p in piv[-4:])
        if w != word:
            word, since = w, t
        out.append({"t": t, "word": w, "dir": D, "conf": st["conf"], "since": since, "why": why, "line": line,
                    "eff": eff, "vx": vx, "price": what, "vol": vol})
    return out, piv
```

- [ ] **Step 4: Add the thresholds**

In `jarvis_thresholds.json`, replace ` "mstate.VWAP_X": 2,` with:

```json
 "mstate.VWAP_X": 2,
 "mstate.NORM_N": 10,
 "mstate.NORM_MIN": 5,
 "mstate.RANGE_HI": 1.5,
 "mstate.RANGE_LO": 0.67,
 "mstate.GAUGE_WIN": 15,
 "mstate.VIX_PTS": 0.3,
 "mstate.IV_PTS": 0.5,
 "mstate.VOL_N": 2,
 "mstate.VOL_CLOSES": 2,
```

Replace `  "mstate.VWAP_X": "... with >= 2 VWAP returns in those 45 min"` with:

```json
  "mstate.VWAP_X": "... with >= 2 VWAP returns in those 45 min",
  "mstate.NORM_N": "the bar-range yardstick: the same 3-min slot's median high-low over the last 10 futures sessions (data/backtest)",
  "mstate.NORM_MIN": "... read only with >= 5 sessions on the record; fewer: could not check",
  "mstate.RANGE_HI": "a 3-min bar >= 1.5x its slot's median votes EXPANDING",
  "mstate.RANGE_LO": "a 3-min bar <= 0.67x its slot's median votes CONTRACTING",
  "mstate.GAUGE_WIN": "the straddle / VIX / ATM IV gauges read their change over 15 min",
  "mstate.VIX_PTS": "India VIX +/- 0.3 in 15 min votes EXPANDING / CONTRACTING",
  "mstate.IV_PTS": "ATM IV +/- 0.5 vol points in 15 min votes EXPANDING / CONTRACTING",
  "mstate.VOL_N": "EXPANDING / CONTRACTING needs 2 gauges that way, more than the other way",
  "mstate.VOL_CLOSES": "... at 2 consecutive 3-min closes (spec §4)"
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest -q test_mstate.py test_thresholds.py`
Expected: PASS (9 in `test_mstate.py`).

- [ ] **Step 6: Stage**

```bash
git add mstate.py test_mstate.py jarvis_thresholds.json
```

---

### Task 3: her zone trigger stops voting in the count

**Files:**
- Modify: `jarvis.py:1379` (PIECES), `jarvis.py:1482-1488` (count docstring), `jarvis.py:1609-1620` (delete the `setup` piece)
- Create: `test_jarvis_state.py`

**Interfaces:**
- Consumes: `jarvis.count(d, i)`, `test_jarvis._toy()`.
- Produces: `jarvis.PIECES == ("sides", "wf7", "wall_ahead", "answer", "trapped", "fut_oi", "speed", "all3")`. The count has 8 pieces. Her zone trigger is the zone card's (Task 9).

- [ ] **Step 1: Write the failing test**

Create `test_jarvis_state.py`:

```python
"""test_jarvis_state.py -- the market state wired into Jarvis (plan docs/superpowers/plans/2026-11-06-jarvis-market-state.md):
jarvis.py, jarvis_log.py and server.py. Toy frames, plus record checks skipped when the day is absent. Kept apart from
test_jarvis.py so its own edits never mix with these."""
import json

import pytest

import jarvis
from test_jarvis import _call_toy, _has, _toy, record  # noqa: F401  (record is a fixture)


def test_her_zone_trigger_no_longer_votes_in_the_count():
    """Spec 2026-11-06 §2: zone triggers never vote in the trend count again (5 Nov: the 12:30 NIFTY sell voted against
    a trend the writers backed). The trigger is the zone card's."""
    d = _toy()
    d["zone"] = [{"t": "10:30", "side": "SELL", "px": 23010.0}]
    d["reads"] = jarvis.reads(d)
    d["legs"] = {"rows": [{"t": m, "lean": -1, "word": "TREND", "leg": {"dir": -1}} for m in d["mins"]],
                 "day": {"flips": [0] * 40, "fut_oi": [None] * 40}, "pauses": [], "missing": []}
    c = jarvis.count(d, 39)
    assert "setup" not in jarvis.PIECES and [p["k"] for p in c["pieces"]] == list(jarvis.PIECES)
    assert not any("trigger" in p["text"] for p in c["pieces"]) and c["N"] == c["with"] + c["against"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest -q test_jarvis_state.py::test_her_zone_trigger_no_longer_votes_in_the_count`
Expected: FAIL on `assert "setup" not in jarvis.PIECES`.

- [ ] **Step 3: Remove the piece**

In `jarvis.py:1379`, replace:

```python
PIECES = ("sides", "wf7", "wall_ahead", "answer", "trapped", "fut_oi", "speed", "all3", "setup")   # GAPS §4, writers first
```

with:

```python
PIECES = ("sides", "wf7", "wall_ahead", "answer", "trapped", "fut_oi", "speed", "all3")   # GAPS §4, writers first; her
                                                       # zone trigger left the count 6 Nov: it is the zone card's (spec §2)
```

In `count`'s docstring, replace `-> fut OI -> flow and speed -> cross-index -> her setup.` with `-> fut OI -> flow and speed -> cross-index (her zone trigger is the zone card's, never a vote: spec 2026-11-06 §2).`

Delete these lines from `count` (`jarvis.py:1609-1620`):

```python
    # her setup: her latest zone3 trigger, inside its 45-min window (MANAGE's)
    zs = [z for z in d.get("zone") or () if not z.get("kind") and z.get("px") is not None and str(z.get("t", ""))[:5] <= t]
    if not zs:
        put("setup", "?", "no trigger today")
    else:
        z = zs[-1]
        age = m - _m(z["t"][:5])
        if age >= MANAGE_WIN:
            put("setup", "?", f"last trigger {z['t'][:5]} {z['side']} {age} min ago (outside its 45 min)")
        else:
            put("setup", by(-1 if z["side"] == "SELL" else 1),
                f"her trigger {z['t'][:5]} {z['side']} {_fmt(z['px'])}f · {age} min")
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest -q test_jarvis_state.py test_jarvis.py test_jarvis_log.py test_jarvis_cli.py`
Expected: PASS. `test_jarvis.py`'s `len(jarvis.PIECES)` assertions follow the tuple. `test_jarvis_cli.py:25`'s fake `setup` piece is display text only.

Then confirm nothing else names the piece:
Run: `git grep -n "\"setup\", \"?\"\|put(\"setup\"" -- "*.py"`
Expected: no output.

- [ ] **Step 5: Stage**

```bash
git add jarvis.py test_jarvis_state.py
```

---

### Task 4: the state word leads in `jarvis.call()`

**Files:**
- Modify: `jarvis.py:934-959` (split `_atm_chain` out of `_legs`), `:902` (the `_legs` call), `:907-908` (the state fold before `call`), `:1340-1352` (`call()`'s return), `:1448` (`calls()` keys); add `_grade` after `said` (:1632)
- Modify: `test_jarvis.py` (the record tests that assert the ACTION word)
- Test: `test_jarvis_state.py` (append)

**Interfaces:**
- Consumes: `mstate.fold(d, chain, nm)`, `mstate.norm(idx, day)`, `mstate.chip(row)`, `mstate._thresholds()`.
- Produces:
  - `jarvis._atm_chain(R, step) -> {"HH:MM": {"spot", "ce": {k: {"ltp", "delta"}}, "pe": {...}}}`.
  - `jarvis._legs(d, chain, day, idx)`.
  - `jarvis._grade(cnt, D, lean) -> "healthy"|"tired"|"fuel blind"|None`.
  - Frame keys `d["mstate"]` (rows, len == len(mins)) and `d["pivots"]`.
  - `call()` adds:
    - `"word"`: the state word when the frame has a state;
    - `"since"`: the state's;
    - `"action"`: `{"said", "word", "lean", "since", "why"}`;
    - `"mstate"`: `{"word", "dir", "conf", "since", "why", "line", "eff", "expiry", "vol": {...}, "grade", "chip"}`, or None;
    - `"chips"`: `[action said, "fuel <grade>"]`.
  - `calls()` rows add `"action"`, `"mstate"` and `"chips"`.

- [ ] **Step 1: Write the failing tests** (append to `test_jarvis_state.py`)

```python
def _state_rows(d, word="TREND ▼", D=-1):
    return [{"t": m, "word": word, "dir": D, "conf": True, "since": "10:12",
             "why": "TREND ▼: LL 22,990 (10:06) then LH 23,040 (10:09) held", "line": "line 23,040 (LH 10:09)",
             "eff": 0.61, "vx": 0, "price": "fut", "expiry": None,
             "vol": {"word": "EXPANDING", "since": "10:20", "up": 2, "down": 0, "read": 4, "gauges": []}}
            for m in d["mins"]]


def test_the_state_word_leads_and_the_action_word_becomes_a_chip():
    d = _call_toy()
    d["reads"]["action"] = jarvis.action_words(d)
    old = jarvis.call(d)                                          # a frame with no state: the ACTION word, as before
    assert old["word"] == old["action"]["said"] and old["mstate"] is None and old["chips"] == []
    d["mstate"] = _state_rows(d)
    c = jarvis.call(d)
    assert c["word"] == "TREND ▼" and c["since"] == "10:12" and c["action"]["said"] == old["word"]
    assert c["chips"][0] == old["word"] and c["mstate"]["vol"]["word"] == "EXPANDING"
    assert c["mstate"]["chip"] == "neeche ka trend · 23,040" and c["mstate"]["grade"] in ("healthy", "tired", "fuel blind")
    assert c["why"][0].startswith("state: TREND ▼ · EXPANDING since 10:12 — TREND ▼: LL")
    assert c["buyer"] == old["buyer"] and c["wrong_line"] == old["wrong_line"]   # the expressions follow the ACTION word
    rows = jarvis.calls(d)
    assert rows[-1]["word"] == "TREND ▼" and rows[-1]["action"]["said"] == old["word"]
    assert "%" not in json.dumps(c, default=str)


def test_the_grade_reads_the_count_for_the_trend_and_never_flips_it():
    assert jarvis._grade({"with": 3, "against": 1}, 1, 1) == "healthy"
    assert jarvis._grade({"with": 3, "against": 1}, 1, -1) == "tired"        # the count is for the other lean: mirrored
    assert jarvis._grade({"with": 0, "against": 0}, -1, -1) == "fuel blind"  # HOLD with nothing voting is not allowed
    assert jarvis._grade({"with": 2, "against": 0}, 0, 1) is None           # no trend: no grade


@pytest.mark.skipif(not _has("2026-11-05"), reason="5 Nov record not present")
def test_5nov_every_minute_has_a_state_and_the_open_drive_is_spoken(record):
    """Spec §9 row 1, observed on the record: SENSEX's leg qualified at 09:43, so the word reads TREND ▲ (unconfirmed)
    before 10:00 instead of a silent OPENING."""
    d = jarvis.build("2026-11-05", "SENSEX", None)
    assert len(d["mstate"]) == len(d["mins"]) and not any("market state failed" in x for x in d["health"]["notes"])
    assert any(r["word"].startswith("TREND ▲") for r in d["mstate"] if "09:36" <= r["t"] <= "10:00")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest -q test_jarvis_state.py`
Expected: FAIL with `KeyError: 'action'` (and `AttributeError: ... '_grade'`).

- [ ] **Step 3: Split the ATM chain out of `_legs` and fold the state in `_build`**

Replace the whole `def _legs(d, R, day, idx):` function (`jarvis.py:934-959`) with:

```python
def _atm_chain(R, step):
    """The ATM premium + delta per chain minute, near ATM (+/- 5 steps) -> {"HH:MM": {"spot", "ce": {k: {"ltp",
    "delta"}}, "pe": {...}}}: the leg's premium read (legs.read) and the market state's straddle / premium gauges
    (mstate.gauges, mstate._prem). A minute without spot is absent."""
    chain = {}
    for m, r in R.items():
        sp = r.get("spot")
        if not sp:
            continue
        row = {"spot": sp, "ce": {}, "pe": {}}
        for s in r.get("strikes") or ():
            if isinstance(s.get("k"), (int, float)) and abs(s["k"] - sp) <= 5 * step:
                for side in ("ce", "pe"):
                    leg = s.get(side) or {}
                    if leg.get("ltp") is not None and leg.get("delta") is not None:
                        row[side][s["k"]] = {"ltp": leg["ltp"], "delta": leg["delta"]}
        chain[hm(m)] = row
    return chain


def _legs(d, chain, day, idx):
    """THE LEG (legs.py, NOISE-DECODER-BRAINSTORM.md, merged decision 30 Oct) on this frame, with its two extras: the ATM
    premium + delta per chain minute (`chain`, _atm_chain's; None: its read says could not check) and her footprint
    marks (NIFTY's chart only: SENSEX reads NIFTY's flow, §1q, but a NIFTY mark's price means nothing on SENSEX).
    Fail-soft: a decoder error leaves the frame and the old call standing, and says so."""
    import legs
    import tape_log
    try:
        marks = list(_rows(os.path.join(tape_log.DIR, f"ofd_marks2_{idx}_{day}.jsonl"))) if idx == "NIFTY" else None
        return legs.read(d, chain=chain, marks=marks)
    except Exception as e:                                    # display only: never take the frame down
        return {"error": f"{type(e).__name__}: {e}", "rows": [], "pauses": [], "day": {}, "missing": ["the leg read failed"]}
```

In `_build`, replace `    data["legs"] = _legs(data, R, day, idx)` (`:902`) with:

```python
    try:
        ach = _atm_chain(R, STEP)
    except Exception:                                # display only: the premium reads say could not check
        ach = None
    data["legs"] = _legs(data, ach, day, idx)
```

In `_build`, replace `    data["call"] = call(data)` (`:908`) with:

```python
    try:                                             # THE MARKET STATE (mstate.py, spec 2026-11-06): display only
        import mstate
        mstate._thresholds()
        data["mstate"], data["pivots"] = mstate.fold(data, ach, mstate.norm(idx, day))
    except Exception as e:                           # never the frame: the ACTION word stays the word
        data["mstate"], data["pivots"] = [], []
        data["health"]["notes"].append(f"the market state failed: {type(e).__name__}: {e} — the ACTION word shown")
    data["call"] = call(data)
```

- [ ] **Step 4: Make the state word the word in `call()`**

In `call()`, insert directly before `    return T5 | {"at": mins[i], "word": word, ...` (`:1340`):

```python
    ms = d.get("mstate") or []
    srow = ms[i] if len(ms) == len(mins) and not blind else None      # THE MARKET STATE leads (spec 2026-11-06 §7)
    said_act, grade = word, None                                     # the ACTION word: now a chip under the state
    if srow:
        import mstate
        grade = _grade(cnt, srow["dir"], lean)
        word = srow["word"]
        vw_ = (srow.get("vol") or {}).get("word")
        why.insert(0, f"state: {word}" + (f" · {vw_}" if vw_ else "") + f" since {srow['since']} — {srow['why']}"
                   + (f" · {srow['line']}" if srow.get("line") else "")
                   + (f" · eff {srow['eff']:.2f}" if srow.get("eff") is not None else "")
                   + (f" · fuel {grade}" if grade else "") + f" · action {said_act}")
```

In the return dict, replace:

```python
            "state": (row or {}).get("word"), "since": act["since"] if act else mins[i] if blind else None,
```

with:

```python
            "state": (row or {}).get("word"),
            "since": srow["since"] if srow else act["since"] if act else mins[i] if blind else None,
```

Replace `             "missing": row.get("missing")}, "v1": v1, "lines": lines,` with:

```python
             "missing": row.get("missing")}, "v1": v1, "lines": lines,
            "action": {"said": said_act, "word": act["word"] if act else None, "lean": lean,
                       "since": act["since"] if act else None, "why": act["why"] if act else reason},
            "mstate": None if srow is None else
            {k: srow.get(k) for k in ("word", "dir", "conf", "since", "why", "line", "eff", "expiry")}
            | {"vol": {k: (srow.get("vol") or {}).get(k) for k in ("word", "since", "up", "down", "read", "gauges")},
               "grade": grade, "chip": mstate.chip(srow)},
            "chips": [x for x in (said_act, grade and f"fuel {grade}") if x] if srow else [],
```

After `def said(word, lean): ...` (`:1632-1636`), add:

```python
def _grade(cnt, D, lean):
    """The trend's fuel from the count (spec 2026-11-06 §3: the pieces GRADE a trend, never flip it) -> "healthy" /
    "tired" / "fuel blind", None outside a trend. The count is for the leg's lean: a trend the other way reads it
    mirrored. HOLD with nothing voting is not allowed: no WITH and no AGAINST reads "fuel blind" (spec §7)."""
    if not D:
        return None
    w, a = (cnt or {}).get("with") or 0, (cnt or {}).get("against") or 0
    if lean and lean != D:
        w, a = a, w
    return "fuel blind" if not w and not a else "healthy" if w >= a else "tired"
```

In `calls()` (`:1448`), replace:

```python
        out.append({k: c[k] for k in ("at", "word", "lean", "leg", "day", "wrong_line", "buyer", "seller", "state", "since",
                                      "count", "action_why")}
```

with:

```python
        out.append({k: c[k] for k in ("at", "word", "lean", "leg", "day", "wrong_line", "buyer", "seller", "state", "since",
                                      "count", "action_why", "action", "mstate", "chips")}
```

- [ ] **Step 5: Point the record tests that assert the ACTION word at `action`**

The word they assert has not changed. It moved to `c["action"]["said"]`. In `test_jarvis.py`, make these replacements (search by content; the line numbers are from the 6 Nov working tree):

- `test_the_call_has_both_expressions_a_wrong_line_and_no_rate` (~:195): `assert c["word"].rstrip(" ▲▼") in WORDS and` → `assert c["action"]["said"].rstrip(" ▲▼") in WORDS and c["word"].startswith(("TREND", "RANGE", "OPENING")) and`
- The server mock-day test (~:283): `assert out["call"]["word"].rstrip(" ▲▼") in WORDS and` → `assert out["call"]["action"]["said"].rstrip(" ▲▼") in WORDS and`
- `test_a_blind_frame_says_cant_see_and_a_backfill_is_read` (~:350): `c["word"] == "WATCH ▲", c["word"]` → `c["action"]["said"] == "WATCH ▲", c["action"]`
- `test_21oct_the_word_holds_in_a_one_way_leg` (~:523) and `test_21oct_one_trend_call_and_at_most_two_palatq` (~:536): `words = [c["word"] for c in jarvis.calls(d)]` → `words = [c["action"]["said"] for c in jarvis.calls(d)]`
- `test_30oct_the_opening_is_not_announced` (~:545): `early = [c["word"] for c in jarvis.calls(d) if c["at"] < "10:00"]` → `early = [c["action"]["said"] for c in jarvis.calls(d) if c["at"] < "10:00"]`
- `test_the_1530_chain_stop_is_never_a_hole_on_the_record` (~:950): `assert mins[-1] > "15:35" and c["word"] == w, (day, c["word"])` → `assert mins[-1] > "15:35" and c["action"]["said"] == w, (day, c["action"])`

Leave the toy tests (`_call_toy`, `_expr_toy`, the PALAT toy) alone. Their frames carry no `mstate`, so `c["word"]` is still the ACTION word. CAN'T SEE is never swapped (`srow` is None when blind).

- [ ] **Step 6: Run the tests**

Run: `python -m pytest -q test_jarvis_state.py test_jarvis.py test_mstate.py`
Expected: PASS (the record tests skip where the day is absent; the existing xfail stays xfail).

- [ ] **Step 7: Stage**

```bash
git add jarvis.py test_jarvis_state.py
git add -p test_jarvis.py            # only the hunks of Step 5
```

---

### Task 5: the call log carries the action word, the state forward log, the card

**Files:**
- Modify: `jarvis_log.py:31-50` (`_path`, `read`, `write` take `kind`), `:69-77` (`row`), `:106` (`self_line`), `:145-158` (`card`); add `state_row`
- Modify: `server.py:4858-4868` (`_jarvis_log` writes the state log)
- Modify: `test_jarvis_log.py:99-104` (the exact row gains `action` / `vol`)
- Test: `test_jarvis_state.py` (append)

**Interfaces:**
- Consumes: `call()`'s `action` / `mstate` / `chips`; the frame's `mstate` rows.
- Produces:
  - `jarvis_log.write(day, idx, row, kind="call")` and `jarvis_log.read(day, idx=None, kind="call")`, with `kind="state"` -> `data/jarvis/state_<day>.jsonl`.
  - `jarvis_log.state_row(fr, j, now, src) -> {"day", "t", "at", "src", "word", "dir", "conf", "since", "line", "why", "eff", "vol", "votes", "expiry"}`.
  - Call-log rows gain `"action"` and `"vol"`. The card gains `"mstate"`, `"action"` and `"chips"`.

- [ ] **Step 1: Write the failing tests** (append to `test_jarvis_state.py`)

```python
import jarvis_log  # noqa: E402

DAY = "2026-11-02"


def _srow(t, word="TREND ▲"):
    return {"t": t, "word": word, "dir": 1, "conf": True, "since": "10:40", "why": "TREND ▲: HH then HL held",
            "line": "line 23,000 (HL 10:30)", "eff": 0.5, "vx": 1, "price": "fut", "expiry": None,
            "vol": {"word": "NORMAL", "since": "10:30", "up": 1, "down": 0, "read": 4,
                    "gauges": [{"k": "vix", "vote": 0, "text": "VIX +0.10"}]}}


def test_the_call_row_carries_the_action_and_the_self_line_counts_palatq_from_it():
    fr = {"day": DAY, "idx": "NIFTY", "mins": ["10:42"], "fut": [1.0], "spot": [1.0],
          "call": {"at": "10:42", "word": "TREND ▲", "action": {"said": "PALAT? ▲"}, "mstate": {"vol": {"word": "EXPANDING"}}}}
    r = jarvis_log.row(fr, 1793596371)
    assert r["word"] == "TREND ▲" and r["action"] == "PALAT? ▲" and r["vol"] == "EXPANDING"
    rows = [dict(r, t="10:40", action="HOLD ▲"), dict(r, t="10:41", action="PALAT? ▲"), dict(r, t="10:42", action="PALAT ▼")]
    s = jarvis_log.self_line(rows, 1.0)
    assert s.startswith("TREND ▲ since 10:40") and "PALAT? said 1× · came true 1×" in s


def test_the_state_log_is_write_once_and_tags_a_late_minute_backfill():
    fr = {"ok": True, "day": DAY, "idx": "NIFTY", "mins": ["10:40", "10:41"], "call": {},
          "mstate": [_srow("10:40"), _srow("10:41")]}
    for j in (0, 1):
        assert jarvis_log.write(DAY, "NIFTY", jarvis_log.state_row(fr, j, 1793596371, "live" if j else "backfill"),
                                kind="state") is True
    assert jarvis_log.write(DAY, "NIFTY", jarvis_log.state_row(fr, 1, 1793596400, "live"), kind="state") is False
    rows = jarvis_log.read(DAY, "NIFTY", kind="state")
    assert [(x["t"], x["src"]) for x in rows] == [("10:40", "backfill"), ("10:41", "live")]
    assert rows[0]["votes"] == {"vix": 0} and rows[0]["vol"] == "NORMAL" and jarvis_log.read(DAY, "NIFTY") == []


def test_the_server_writes_every_minute_of_a_late_start_once(monkeypatch):
    """Anytime-start: a first live build at 10:42 writes 10:40 as backfill and 10:41 live; the next minute adds one row."""
    import time
    from datetime import datetime
    from chain_live import IST
    from test_jarvis_log import CALL, _srv, frame
    server, clock = _srv(monkeypatch, (2026, 11, 2, 10, 42, 25))

    def fake(day, idx, upto, fill=False):
        ms = [f"{m // 60:02d}:{m % 60:02d}" for m in range(640, upto)]
        return dict(frame(), day=day, idx=idx, mins=ms, call=dict(CALL, at=ms[-1]), mstate=[_srow(m) for m in ms])
    monkeypatch.setattr(jarvis, "build", fake)
    server._jarvis_reply({"idx": ["NIFTY"]})
    assert [(r["t"], r["src"]) for r in jarvis_log.read(DAY, "NIFTY", kind="state")] == [("10:40", "backfill"),
                                                                                         ("10:41", "live")]
    clock["now"] = datetime(2026, 11, 2, 10, 43, 25, tzinfo=IST)
    monkeypatch.setattr(server, "JARVIS_TTL_S", 0)
    server._jarvis_reply({"idx": ["NIFTY"]})
    assert [(r["t"], r["src"]) for r in jarvis_log.read(DAY, "NIFTY", kind="state")][-1] == ("10:42", "live")
    assert len(jarvis_log.read(DAY, "NIFTY", kind="state")) == 3 and time.time()


def test_the_card_passes_the_state_the_action_and_the_chips():
    fr = {"ok": True, "day": DAY, "idx": "NIFTY", "mins": ["10:41"], "fut": [1.0], "health": {"notes": []},
          "call": {"word": "TREND ▲", "mstate": {"word": "TREND ▲", "chip": "upar ka trend · 23,000"},
                   "action": {"said": "WATCH ▲"}, "chips": ["WATCH ▲", "fuel tired"]}}
    c = jarvis_log.card(fr)
    assert c["mstate"]["chip"] == "upar ka trend · 23,000" and c["action"]["said"] == "WATCH ▲"
    assert c["chips"] == ["WATCH ▲", "fuel tired"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest -q test_jarvis_state.py -k "call_row or state_log or late_start or card_passes"`
Expected: FAIL (`KeyError: 'action'`, `TypeError: write() got an unexpected keyword argument 'kind'`).

- [ ] **Step 3: Extend `jarvis_log.py`**

Replace `_path`, `read` and `write` (`:31-50`) with:

```python
def _path(day, kind="call"):
    return os.path.join(DIR, f"{kind}_{day}.jsonl")


def read(day, idx=None, kind="call"):
    """The day's rows in file order, one index (or all); [] when there is no file. kind "call" (the call log) or
    "state" (the market state's forward log, spec 2026-11-06 §9)."""
    return [r for r in confluence_log._rows(_path(day, kind)) if idx is None or r.get("idx") == idx]


def write(day, idx, row, kind="call"):
    """Append `row` once per (idx, t) -> True when written, False for a minute already on disk. DIR is made on first write."""
    p = _path(day, kind)
    with _LOCK:
        seen = _SEEN.get(p)
        if seen is None:
            seen = _SEEN[p] = {(r.get("idx"), r.get("t")) for r in confluence_log._rows(p)}
        k = (idx, row.get("t"))
        if k in seen:
            return False
        os.makedirs(DIR, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(row, idx=idx), ensure_ascii=False, default=str) + "\n")
        seen.add(k)
        return True
```

In `row`, replace `"leg": c.get("leg"), "wrong_line": c.get("wrong_line"), "missing": miss,` with:

```python
            "leg": c.get("leg"), "wrong_line": c.get("wrong_line"), "missing": miss,
            "action": (c.get("action") or {}).get("said"), "vol": ((c.get("mstate") or {}).get("vol") or {}).get("word"),
```

After `row`, add:

```python
def state_row(fr, j, now, src):
    """THE STATE LOG row for frame minute j (data/jarvis/state_<day>.jsonl, spec 2026-11-06 §9: the evening review,
    never a gate): the state word, since, line, why, efficiency, the volatility word and each gauge's vote. src "live" =
    the frame's newest minute, written as it happened; "backfill" = a minute rebuilt causally at a later start, never
    pooled with live rows."""
    s = fr["mstate"][j]
    v = s.get("vol") or {}
    return {"day": fr.get("day"), "t": fr["mins"][j], "at": int(now), "src": src, "word": s["word"], "dir": s["dir"],
            "conf": s["conf"], "since": s["since"], "line": s["line"], "why": s["why"], "eff": s["eff"],
            "vol": v.get("word"), "votes": {g["k"]: g["vote"] for g in v.get("gauges") or ()}, "expiry": s.get("expiry")}
```

In `self_line`, replace `    word = [str(r.get("word") or "") for r in rows]` with:

```python
    word = [str(r.get("action") or r.get("word") or "") for r in rows]   # PALAT? / PALAT live in the ACTION word (6 Nov)
```

In `card`, replace `            "watches": list(st.get("watches") or []), "voice": None, "brief": None}` with:

```python
            "watches": list(st.get("watches") or []), "voice": None, "brief": None,
            "mstate": c.get("mstate"), "action": c.get("action"), "chips": c.get("chips")}   # the state leads (6 Nov)
```

- [ ] **Step 4: Write the state log from the server**

In `server._jarvis_log`, replace:

```python
            jarvis_log.write(out["day"], out["idx"], jarvis_log.row(out, time.time()))
            _LAST_LOGGED[out["idx"]] = t
```

with:

```python
            now = time.time()
            jarvis_log.write(out["day"], out["idx"], jarvis_log.row(out, now))
            ms = out.get("mstate") or []
            for j in range(len(ms)):                 # THE STATE LOG: every minute once; the newest is live, a minute this
                jarvis_log.write(out["day"], out["idx"],            # process never saw live is backfill (anytime-start)
                                 jarvis_log.state_row(out, j, now, "live" if j == len(ms) - 1 else "backfill"),
                                 kind="state")
            _LAST_LOGGED[out["idx"]] = t
```

- [ ] **Step 5: Update the exact-row assertion**

In `test_jarvis_log.py`, `test_the_row_carries_the_contract_and_marks_a_blind_minute` (~:100-104), replace:

```python
                 "missing": CALL["missing"], "notes": ["Dext footprint missing since 10:39"], "blind": True}
```

with:

```python
                 "missing": CALL["missing"], "notes": ["Dext footprint missing since 10:39"], "blind": True,
                 "action": None, "vol": None}
```

- [ ] **Step 6: Run the tests**

Run: `python -m pytest -q test_jarvis_state.py test_jarvis_log.py test_jarvis_voice.py test_messages.py`
Expected: PASS.

- [ ] **Step 7: Stage**

```bash
git add jarvis_log.py server.py test_jarvis_state.py test_jarvis_log.py
```

---

### Task 6: the face — the state line leads, WATCH / PALAT? become chips (phase 1 ends)

**Files:**
- Modify: `docs/kahani/review/mockup/jarvis2.html:594-605` (`renderCard`)
- Modify: `docs/live/NOTEPAD.md` (A256 status)

**Interfaces:**
- Consumes: the card / call keys `mstate` (`word`, `dir`, `line`, `eff`, `expiry`, `why`, `chip`, `vol.word`, `vol.gauges`), `chips` and `since`.
- Produces: the big word is the state word, with `VOL · since` under it. Then one line (line · eff · expiry). Then a chips row (the ACTION word, the fuel grade, the Hinglish chip with its number). The gauges sit in that row's tooltip.

- [ ] **Step 1: Edit `renderCard`**

Replace:

```js
  const NC = "could not check — no card", blind = c.word === "CAN'T SEE", lean = /^RANGE/.test(c.word || "") ? 0   // A229: RANGE names no side
    : c.lean || (c.word === "UP" ? 1 : c.word === "DOWN" ? -1 : 0);
  const sub = [c.state, c.since && "since " + c.since].filter(Boolean).join(" · ");
```

with:

```js
  const S = c.mstate, V = (S && S.vol) || {};        // THE MARKET STATE leads (spec 2026-11-06 §7): word · volatility · since
  const NC = "could not check — no card", blind = c.word === "CAN'T SEE", lean = S ? S.dir : /^RANGE/.test(c.word || "") ? 0   // A229: RANGE names no side
    : c.lean || (c.word === "UP" ? 1 : c.word === "DOWN" ? -1 : 0);
  const sub = (S ? [V.word, c.since && "since " + c.since] : [c.state, c.since && "since " + c.since]).filter(Boolean).join(" · ");
```

Directly after the line `  const line = (txt, cls) => { if (txt) row("s " + (cls || "clip"), txt); };`, insert:

```js
  if (S) {                                            // the state's line, then the chips under the word: the ACTION word
    row("s clip", [S.line, S.eff != null && "eff " + S.eff.toFixed(2), S.expiry].filter(Boolean).join(" · ") || S.why, S.why);
    const ch = row("rc", "", (V.gauges || []).map(g => (g.vote === 1 ? "▲ " : g.vote === -1 ? "▼ " : g.vote === 0 ? "· " : "? ") + g.text).join("\n"));
    for (const t of (c.chips || []).concat([S.chip])) {   // (WATCH / PALAT? live here now), the fuel grade, the Hinglish chip
      const el = document.createElement("span"); el.className = "chip q"; el.textContent = t; ch.appendChild(el);
    }
  }
```

- [ ] **Step 2: Check it on 5 Nov (after 15:40 or at a weekend; never start the live server)**

Run (it writes one JSON file beside the page):

```bash
python -c "import json, jarvis; d = jarvis.build('2026-11-05', 'SENSEX', None); d['calls'] = jarvis.calls(d); json.dump(d, open('docs/kahani/review/mockup/data_2026-11-05_state.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)"
```

Open `http://localhost:8787/jarvis2.html?api=data_2026-11-05_state.json`. That is her page server, started by `start-v2.bat`; if it is not up, ask Mary and do not start it.

Expected:
- The big word reads `TREND ▲ (leg, unconfirmed)` at 09:43–10:00, with `NORMAL · since 09:43` under it.
- The chips row shows the ACTION word (for example `OPENING`) and `abhi swing nahi` / `upar ka leg, pakka nahi · 78,616`.
- It renders in light mode with no console error.

Delete the JSON file afterwards (it is a check, not an artifact).

- [ ] **Step 3: Mark A256 built**

In the A256 row, replace `| BUILDING (phase 1) |` with `| BUILT, uncommitted — phase 1 commit on her word |`.

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: the 6 Nov baseline plus the new tests pass. The only accepted failure is `test_v2feed` serve-cache (A49, flaky).

- [ ] **Step 5: Commit phase 1 (only after Mary says commit; never push)**

```bash
git add docs/kahani/review/mockup/jarvis2.html
git add -p docs/live/NOTEPAD.md
git commit -m "Jarvis market state, phase 1: the state word with memory leads; volatility state; zone triggers stop voting (spec 2026-11-06, A256)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Phase 2 — the zone card (spec §10.2)

### Task 7: zone rows carry when they were written, her gate, and the effort read; NIFTY's spot on every frame

**Files:**
- Modify: `jarvis.py:808-817` (the ZONE rows), `:856` (`nf`)
- Test: `test_jarvis_state.py` (append)

**Interfaces:**
- Consumes: `trigger_log` zone3 rows (`at`, `gate`, `stop_px`; never `mfe` / `mae` / `stop_hit` / `f15` / `f30`), `inp["fm"]` (effort minutes: the flow index's book; SENSEX → NIFTY's, §1q), `effort.lam_at(fm, m)`, `effort.MIN_HIST`.
- Produces:
  - `d["zone"][*]` gains `"stop_px"`, `"gate"` and `"at"`. Each trigger (not an arm) gains `"effort": {"x": float|None, "why": str|None}`, read at the trigger bar's close (t+2).
  - `d["nf"]`: NIFTY spot per frame minute, carried.

- [ ] **Step 1: Write the failing test** (append to `test_jarvis_state.py`)

```python
@pytest.mark.skipif(not _has("2026-11-05"), reason="5 Nov record not present")
def test_5nov_zone_rows_carry_when_they_were_written_and_never_a_score(record):
    d = jarvis.build("2026-11-05", "SENSEX", None)
    z = [x for x in d["zone"] if not x.get("kind")]
    assert z and all({"at", "gate", "effort"} <= set(x) for x in z)
    assert not any(k in x for x in d["zone"] for k in ("mfe", "mae", "stop_hit", "f15", "f30", "scored_at"))
    assert len(d["nf"]) == len(d["mins"]) and d["nf"][-1] is not None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest -q test_jarvis_state.py::test_5nov_zone_rows_carry_when_they_were_written_and_never_a_score`
Expected: FAIL on the `{"at", "gate", "effort"}` assertion (or SKIP where the record is absent; run it where it is).

- [ ] **Step 3: Implement**

Replace the ZONE loop (`jarvis.py:810-814`):

```python
    for r in _rows(trigger_log.PATH):
        if r.get("day") == day and r.get("index") == idx and r.get("rule") == "zone3" and START <= str(r.get("t", ""))[:5] \
                and _m(str(r["t"])) < upto:
            ZONE.append({k: r.get(k) for k in ("t", "kind", "side", "px", "level", "stop", "entry", "band", "u2", "d2", "bands_on")
                         if r.get(k) is not None})
```

with:

```python
    import effort
    for r in _rows(trigger_log.PATH):
        if r.get("day") == day and r.get("index") == idx and r.get("rule") == "zone3" and START <= str(r.get("t", ""))[:5] \
                and _m(str(r["t"])) < upto:
            z = {k: r.get(k) for k in ("t", "kind", "side", "px", "level", "stop", "entry", "band", "u2", "d2", "bands_on",
                                       "stop_px", "gate", "at") if r.get(k) is not None}   # never a scored field (mfe, ...)
            if not z.get("kind") and z.get("px") is not None:   # the zone card's sign 3 at the trigger's close (effort.py;
                lam, med, nb = effort.lam_at(inp.get("fm") or {}, _m(str(r["t"])[:5]) + 2)   # SENSEX: NIFTY's flow, §1q)
                z["effort"] = ({"x": round(lam / med, 2), "why": None} if lam and med else
                               {"x": None, "why": f"the day median needs {effort.MIN_HIST} five-minute blocks (has {nb})"
                                if med is None else "no price range or volume in the last 5 min"})
            ZONE.append(z)
```

Replace `    data["bnf"], data["sx"] = other_spot("BANKNIFTY"), other_spot("SENSEX")` with:

```python
    data["bnf"], data["sx"] = other_spot("BANKNIFTY"), other_spot("SENSEX")
    data["nf"] = other_spot("NIFTY")                 # NIFTY's spot on every frame: the card's sync sign and ALL 3's N slot
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest -q test_jarvis_state.py test_jarvis.py`
Expected: PASS.

- [ ] **Step 5: Stage**

```bash
git add jarvis.py test_jarvis_state.py
```

---

### Task 8: `mstate` — legality, the five signs, the card

**Files:**
- Modify: `mstate.py` (imports, constants, `_I`; append the zone-card section)
- Test: `test_mstate.py` (append)
- Modify: `jarvis_thresholds.json`, `docs/live/NOTEPAD.md` (A257)

**Interfaces:**
- Consumes:
  - `jarvis._basis(d, i)`; `legs._lad(d, t, side, k)`, `legs.K_MIN` (9), `legs.K1_L` (2.0L); `effort.HI` (2.0); `fold.IST`.
  - The frame's `vwap`, `sd`, `fhi`, `flo`, `nf`, `bnf`, `sx`, `ladder`; the zone rows (Task 7).
- Produces:
  - `mstate.legal(row, vword, side, t, dte=None) -> (kind: "with"|"fade"|"range"|None, why)`.
  - `mstate.signs(d, i, z, piv) -> [{"k": "band"|"wall"|"effort"|"sync"|"mature", "ok": bool|None, "text"}]`.
  - `mstate.card(d, z, rows, piv, dte=None) -> {"t", "close", "known", "late", "side", "band", "px", "state", "vol", "kind", "verdict", "why", "signs", "n", "N", "stop", "targets", "gate"}` or None.
  - `mstate.cards(d, rows, piv) -> [card]` and `mstate.card_line(card) -> str`.

- [ ] **Step 1: Write the failing tests** (append to `test_mstate.py`)

```python
# ---- Task 8: the zone card --------------------------------------------------------------------------------------------

def test_the_legality_table():
    up = {"word": "TREND ▲", "dir": 1}
    rng = {"word": "RANGE", "dir": 0}
    assert mstate.legal(up, "EXPANDING", "BUY", "10:30")[0] == "with"
    assert mstate.legal(up, "EXPANDING", "SELL", "12:30") == (
        "fade", "TREND ▲ + EXPANDING: a fade only if the band stopped expanding and the writers at it hold")
    assert mstate.legal(up, "CONTRACTING", "SELL", "13:51")[0] == "fade"
    assert mstate.legal(up, "NORMAL", "SELL", "13:51")[0] == "fade"            # EXPANDING adds the band + wall need
    assert mstate.legal(rng, "CONTRACTING", "SELL", "11:00")[0] == "range"
    assert mstate.legal(rng, "EXPANDING", "BUY", "11:00") == (None, "RANGE + EXPANDING: stand aside")
    assert mstate.legal(up, "CONTRACTING", "BUY", "09:40")[0] is None          # before 09:45
    assert mstate.legal(up, "CONTRACTING", "BUY", "15:03", dte=0)[0] is None   # 0 DTE after 15:00


def _zone_frame():
    """A climb into u2 by 11:00 (NIFTY fut), BANKNIFTY / SENSEX flat (no new highs), the CE strike at the band adding
    5L in 9 min, VWAP 24,050 with sigma 30 (u2 24,110, d1 24,020)."""
    px = _path([(0, 24000), (60, 24030), (105, 24110), (120, 24090)])
    d = _frame(px)
    n = len(px)
    d.update(vwap=[24050.0] * n, sd=[30.0] * n, bnf=[54000.0] * n, sx=[79000.0] * n)
    d["ladder"] = {"11:02": {"ce": {24100: 60.0}, "pe": {}}, "10:53": {"ce": {24100: 55.0}, "pe": {}}}
    return d


def test_the_signs_at_the_band_are_a_count_with_reasons():
    d = _zone_frame()
    i = d["mins"].index("11:02")
    piv = [{"kind": "H", "lab": "H", "px": 24000, "t": "10:00", "known": "10:10"},
           {"kind": "H", "lab": "HH", "px": 24060, "t": "10:30", "known": "10:40"}]
    S = {s["k"]: s for s in mstate.signs(d, i, {"side": "SELL", "effort": {"x": 2.4}}, piv)}
    assert S["band"]["ok"] is True and S["band"]["text"].startswith("u2 24,110f vs 24,110f")
    assert S["wall"]["ok"] is True and S["wall"]["text"].startswith("24,100s CE at the band +5.0L / 9 min")
    assert S["effort"]["ok"] is True
    assert S["sync"]["ok"] is True and "BANKNIFTY did not" in S["sync"]["text"]
    assert S["mature"]["ok"] is True and S["mature"]["text"].startswith("push no. 3 up")
    B = {s["k"]: s for s in mstate.signs(d, i, {"side": "BUY"}, piv)}
    assert B["effort"]["ok"] is None and B["effort"]["text"].startswith("effort: not read at a low")


def test_a_card_judges_at_the_close_with_stop_and_targets():
    d = _zone_frame()
    rows = [{"t": t, "word": "TREND ▲", "dir": 1, "vol": {"word": "EXPANDING"}} for t in d["mins"]]
    z = {"t": "11:00", "side": "SELL", "band": "u2", "px": 24095.0, "gate": {"legal": False, "why": "CE 24500 gave up"}}
    c = mstate.card(d, z, rows, [])
    assert c["verdict"] == "TAKE · smaller target" and c["known"] == "11:03"       # band stopped, CE at it adding
    assert c["why"].startswith("TREND ▲ + EXPANDING: a fade only if the band stopped expanding")
    d2 = _zone_frame()
    d2["ladder"]["11:02"]["ce"][24100] = 40.0                                     # the CE at the band LEAVING (-15L)
    c2 = mstate.card(d2, z, rows, [])
    assert c2["verdict"] == "SKIP" and "writers at it leaving" in c2["why"]
    assert c["gate"]["why"] == "CE 24500 gave up"                                # her gate shown, unchanged
    rows = [dict(r, vol={"word": "CONTRACTING"}) for r in rows]
    c = mstate.card(d, dict(z, effort={"x": 2.5}), rows, [])
    assert c["verdict"] == "TAKE · smaller target" and c["targets"] == [["VWAP", 24050.0]]
    assert c["stop"] == max(d["fhi"][d["mins"].index(m)] for m in ("11:00", "11:01", "11:02"))
    assert mstate.card(d, dict(z, side="BUY", band="d2"), [dict(r, word="TREND ▼", dir=-1) for r in rows],
                       [])["kind"] == "fade"                                     # a BUY in TREND ▼ is a fade
    s = mstate.card(d, dict(z, side="BUY", band="d2"), rows, [])
    assert s["kind"] == "with" and s["targets"][1][0] == "u1"
    assert mstate.card_line(c).startswith("ZONE u2 24,095f · TAKE · smaller target (")
    assert "%" not in json.dumps(c)


def test_a_late_row_is_shown_from_when_it_was_written():
    import datetime
    import fold
    d = _zone_frame()
    rows = [{"t": t, "word": "RANGE", "dir": 0, "vol": {"word": "NORMAL"}} for t in d["mins"]]
    at = datetime.datetime(2026, 11, 5, 13, 48, 40, tzinfo=fold.IST).timestamp()
    c = mstate.card(d, {"t": "11:00", "side": "SELL", "band": "u2", "px": 24095.0, "at": at}, rows, [])
    assert c["known"] == "13:48" and c["late"] and c["close"] == "11:02" and c["verdict"] == "TAKE"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest -q test_mstate.py`
Expected: FAIL with `AttributeError: module 'mstate' has no attribute 'legal'`.

- [ ] **Step 3: Implement**

In `mstate.py`, replace `import functools` with:

```python
import datetime
import functools
import math
```

and replace `import decode` with:

```python
import decode
import effort
```

After the `VOL_CLOSES = 2 ...` line, add:

```python
OPEN_LEGAL = "09:45"          # [I] spec §5: no zone trade before 09:45 (the opening's touches stay out)
NO_HOLD_AT = "15:00"          # her practice (no new trades after 15:00): on 0 DTE the card reads "no hold for the close"
FADE_SIGNS = 2                # [I] a fade against a trend that is not expanding is TAKE at >= 2 of the 5 signs
MATURE_PUSHES = 3             # [I] sign 5, a mature leg: the 3rd or later push of the move into the band
SYNC_WIN = 30                 # [I] sign 4: a fresh 30-min extreme (the reads' TOP / BOTTOM signs' window)
```

Replace the `_I = (...)` lines with:

```python
_I = ("EFF_WIN", "EFF_RANGE", "VWAP_X", "NORM_N", "NORM_MIN", "RANGE_HI", "RANGE_LO", "GAUGE_WIN", "VIX_PTS", "IV_PTS",
      "VOL_N", "VOL_CLOSES", "OPEN_LEGAL", "FADE_SIGNS", "MATURE_PUSHES", "SYNC_WIN")
```

Append to the end of `mstate.py`:

```python
# ---- the zone card (spec §5-6) -------------------------------------------------------------------------------------

def legal(row, vword, side, t, dte=None):
    """Spec §5's table -> (kind, why). kind: "with" (the with-trend pullback band), "fade" (against a trend; EXPANDING
    also needs the band stopped + writers holding: TAKE only with the tired signs, target VWAP only, the trend word unchanged), "range" (band to band) or
    None (not legal: the why says which row). An unconfirmed trend is a trend here; NORMAL and ? read as not expanding
    (the table names only EXPANDING and CONTRACTING; EXPANDING adds the band-stopped + writers-holding need, her 6 Nov rule)."""
    if t < OPEN_LEGAL:
        return None, f"before {OPEN_LEGAL}: no zone trade (the opening's touches stay out)"
    if dte == 0 and t >= NO_HOLD_AT:
        return None, f"0 DTE after {NO_HOLD_AT}: premium beats trend, no hold for the close"
    D, trade = row.get("dir") or 0, 1 if side == "BUY" else -1
    if D and trade == D:
        return "with", f"{row['word']}: the with-trend pullback band"
    if D and vword == "EXPANDING":     # her 6 Nov rule: expanding = not a trigger, unless it visibly reverses there
        return "fade", f"{row['word']} + EXPANDING: a fade only if the band stopped expanding and the writers at it hold"
    if D:
        return "fade", f"{row['word']} + {vword or '?'}: a fade only with the tired signs, target VWAP only"
    if vword == "EXPANDING":
        return None, f"{row['word']} + EXPANDING: stand aside"
    return "range", f"{row['word']} + {vword or '?'}: band to band"


def _fresh(xs, i, hi):
    """Did xs make a fresh SYNC_WIN-min extreme (strictly past it) in the 3 minutes to i? None when the window holds a
    gap or < 10 minutes."""
    w, now = xs[max(0, i - SYNC_WIN):max(0, i - 2)], xs[max(0, i - 2):i + 1]
    if len(w) < 10 or None in w or None in now:
        return None
    return max(now) > max(w) if hi else min(now) < min(w)


def signs(d, i, z, piv):
    """The five signs at the band on the trigger's 3-min close, minute i (spec §6) -> [{"k", "ok", "text"}]; ok True /
    False, or None (could not check / not read: the text says which). A count, never a %."""
    import jarvis
    t, top = d["mins"][i], z["side"] == "SELL"
    D, band, S = (1 if top else -1), ("u2" if top else "d2"), []
    bn = d["vwap"][i] + 2 * D * d["sd"][i]
    if i < 3:                                                      # 1. the band stopped expanding (the rejection is the
        S.append({"k": "band", "ok": None, "text": "band: could not check — no 3-min close before it"})   # trigger itself)
    else:
        b0 = d["vwap"][i - 3] + 2 * D * d["sd"][i - 3]
        S.append({"k": "band", "ok": D * (bn - b0) <= 0, "text": f"{band} {_fmt(bn)}f vs {_fmt(b0)}f 3 min before: "
                  + ("stopped expanding" if D * (bn - b0) <= 0 else "still expanding")})
    step = d.get("step") or 50                                     # 2. writers AT the band's strike (the wall defended)
    px = bn - jarvis._basis(d, i)
    k = (math.ceil(px / step) if top else math.floor(px / step)) * step
    sd_, SD, t9 = ("ce", "CE", _hm(_m(t) - legs.K_MIN)) if top else ("pe", "PE", _hm(_m(t) - legs.K_MIN))
    a, b = legs._lad(d, t, sd_, k), legs._lad(d, t9, sd_, k)
    if a is None or b is None:
        S.append({"k": "wall", "ok": None, "text": f"writers at the band: could not check — {_fmt(k)}s {SD} not on "
                                                    f"the ladder at {t if a is None else t9}"})
    else:
        S.append({"k": "wall", "ok": a - b >= -legs.K1_L, "text": f"{_fmt(k)}s {SD} at the band {a - b:+.1f}L / "
                  f"{legs.K_MIN} min (" + ("holding / adding" if a - b >= -legs.K1_L else "leaving") + ")"})
    e = z.get("effort") or {}                                      # 3. effort without result (effort.py, the survivor)
    if not top:
        S.append({"k": "effort", "ok": None, "text": "effort: not read at a low — the 2× mirror failed there "
                                                      "(effort.py; its survivor at a low says continuation)"})
    elif e.get("x") is None:
        S.append({"k": "effort", "ok": None, "text": f"effort: could not check — {e.get('why') or 'no read'}"})
    else:
        S.append({"k": "effort", "ok": e["x"] >= effort.HI, "text": f"effort {e['x']:.1f}× the day's lots per point"
                  + (" (NIFTY's flow, §1q)" if d.get("idx") == "SENSEX" else "")})
    _, Hh, Ll, _ = _series(d)                                      # 4. sync broke: a fresh extreme here, none in peers
    peers = {n: s for n, s in (("NIFTY", d.get("nf")), ("BANKNIFTY", d.get("bnf")), ("SENSEX", d.get("sx")))
             if n != d.get("idx")}
    mine = _fresh(Hh if top else Ll, i, top)
    pf = {n: (_fresh(s, i, top) if s else None) for n, s in peers.items()}
    if mine is None or None in pf.values():
        S.append({"k": "sync", "ok": None, "text": "sync: could not check — " + ", ".join(
            n for n, v in [(d.get("idx"), mine)] + list(pf.items()) if v is None) + f" lacks {SYNC_WIN} min"})
    else:
        S.append({"k": "sync", "ok": mine and not any(pf.values()),
                  "text": f"{d.get('idx')} {'made' if mine else 'no'} new {SYNC_WIN}-min {'high' if top else 'low'} · "
                          + " · ".join(f"{n} {'made it' if v else 'did not'}" for n, v in pf.items())})
    kind, lab = ("H", "HH") if top else ("L", "LL")                # 5. a mature leg: a later push of the day
    run = 0
    for p in reversed([p for p in piv if p["kind"] == kind and p["known"] <= t]):
        if p["lab"] not in (lab, kind):
            break
        run += 1
    S.append({"k": "mature", "ok": run + 1 >= MATURE_PUSHES,
              "text": f"push no. {run + 1} {'up' if top else 'down'} into the band (≥ {MATURE_PUSHES} is mature), "
                      f"{band} is 2σ from VWAP"})
    return S


def card(d, z, rows, piv, dte=None):
    """THE ZONE CARD of one zone3 trigger row z (trigger_log; t = its 3-min bar's start), judged at that bar's close
    (minute t+2, the state and signs as of then) -> dict, or None when the close is not in the frame yet. known = the
    minute it could first be shown: the close's next minute, or later when the row was written later (`at`, IST): a late
    row says so. stop: beyond the trigger candle (SELL its high, BUY its low; fut); targets: VWAP, then the next band
    (SELL d1, BUY u1) -- a smaller target is VWAP only. `gate` is her §1d gate as logged, shown beside the at-band read
    (sign 2), never changed (phase 4 is hers)."""
    t0 = str(z["t"])[:5]
    tc = _hm(_m(t0) + 2)
    if tc not in d["mins"]:
        return None
    i, top = d["mins"].index(tc), z["side"] == "SELL"
    row = rows[i]
    vword = (row.get("vol") or {}).get("word")
    kind, why = legal(row, vword, z["side"], tc, dte)
    S = signs(d, i, z, piv)
    n, N = sum(s["ok"] is True for s in S), sum(s["ok"] is not None for s in S)
    wall = next(s for s in S if s["k"] == "wall")
    if kind is None:
        verdict = "SKIP"
    elif kind == "with":
        verdict = "STRONG" if wall["ok"] else "TAKE"
        why += " · writers behind" if wall["ok"] else " · writers at the band not holding"
    elif kind == "fade":
        band = next(s for s in S if s["k"] == "band")
        need = vword == "EXPANDING" and not (band["ok"] is True and wall["ok"] is True)
        verdict = "TAKE · smaller target" if n >= FADE_SIGNS and not need else "SKIP"
        why += (f" · {n} of 5 signs" + ("" if n >= FADE_SIGNS else f" (needs {FADE_SIGNS})")
                + (" · band still expanding or writers at it leaving" if need else ""))
    else:
        verdict = "TAKE"
    js = range(max(0, i - 2), i + 1)
    stop = max(d["fhi"][j] for j in js) if top else min(d["flo"][j] for j in js)
    vw, sd = d["vwap"][i], d["sd"][i]
    tg = [["VWAP", round(vw, 2)]] + ([] if verdict == "TAKE · smaller target" else
                                     [["d1" if top else "u1", round(vw - sd if top else vw + sd, 2)]])
    known = _m(t0) + 3
    if isinstance(z.get("at"), (int, float)):
        a = datetime.datetime.fromtimestamp(z["at"], _fold.IST)
        if a.strftime("%Y-%m-%d") == d["day"]:
            known = max(known, a.hour * 60 + a.minute)
    return {"t": t0, "close": tc, "known": _hm(known), "late": known - (_m(t0) + 3) > 2, "side": z["side"],
            "band": z.get("band"), "px": z.get("px"), "state": row["word"], "vol": vword, "kind": kind,
            "verdict": verdict, "why": why, "signs": S, "n": n, "N": N, "stop": round(stop, 2), "targets": tg,
            "gate": z.get("gate")}


def cards(d, rows, piv):
    """card() for every zone3 trigger of the frame (d["zone"], arms excluded), in the record's order."""
    dte = (d.get("ctx") or {}).get("dte")
    out = [card(d, z, rows, piv, dte) for z in d.get("zone") or () if not z.get("kind") and z.get("px") is not None]
    return [c for c in out if c]


def card_line(c):
    """The card in one terminal line: "ZONE d2 79,250f · STRONG · stop 79,190f · VWAP 79,330f → u1 79,410f"."""
    return (f"ZONE {c['band'] or c['side']} {_fmt(c['px'])}f · {c['verdict']}"
            + (f" ({c['n']} of 5 signs)" if c["kind"] in ("fade", "range") else "")
            + f" · stop {_fmt(c['stop'])}f · " + " → ".join(f"{k} {_fmt(v)}f" for k, v in c["targets"])
            + (f" · logged late {c['known']}" if c["late"] else ""))
```

- [ ] **Step 4: Thresholds and NOTEPAD**

In `jarvis_thresholds.json`, replace ` "mstate.VOL_CLOSES": 2,` with:

```json
 "mstate.VOL_CLOSES": 2,
 "mstate.OPEN_LEGAL": "09:45",
 "mstate.FADE_SIGNS": 2,
 "mstate.MATURE_PUSHES": 3,
 "mstate.SYNC_WIN": 30,
```

Replace `  "mstate.VOL_CLOSES": "... at 2 consecutive 3-min closes (spec §4)"` with:

```json
  "mstate.VOL_CLOSES": "... at 2 consecutive 3-min closes (spec §4)",
  "mstate.OPEN_LEGAL": "the zone card: no zone trade before 09:45, the opening's touches stay out (spec §5, A257)",
  "mstate.FADE_SIGNS": "a fade against a trend that is not expanding is TAKE · smaller target at >= 2 of the 5 signs",
  "mstate.MATURE_PUSHES": "sign 5, a mature leg: the 3rd or later push of the move into the band",
  "mstate.SYNC_WIN": "sign 4, sync broke: a fresh 30-min extreme here and none in the two peers"
```

In `docs/live/NOTEPAD.md`, insert after the A256 row:

```markdown
| A257 | 6 Nov (spec 2026-11-06 §5-6, plan phase 2) | **Her zone is a location the market's state makes legal or not; Jarvis had no card for it.** On 5 Nov her §1d gate cited a stale strike ("CE 24500 gave up 11:17") all afternoon. | 5 Nov trigger_log [M]: the five top-band sells read NOT legal on the 11:17 strike | `mstate.card`: legality by state × volatility (spec §5), five signs counted at the trigger's close (band stopped, writers AT the band's strike, effort at a fresh high, sync broke, a mature push), stop beyond the trigger candle, VWAP then the next band; her gate shown verbatim beside the at-band read (phase 4, the gate reading the band, is hers to sign). [I]: `mstate.OPEN_LEGAL` 09:45, `FADE_SIGNS` 2 of 5, `MATURE_PUSHES` 3, `SYNC_WIN` 30 min. NORMAL volatility reads as not expanding (the table names two states; decided as the trader). Sign 3 is read at highs only (effort's ≥2× mirror failed at lows; CVD divergence at highs is inverted, oi-lab) | BUILDING (phase 2) |
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest -q test_mstate.py test_thresholds.py`
Expected: PASS (13 in `test_mstate.py`).

- [ ] **Step 6: Stage**

```bash
git add mstate.py test_mstate.py jarvis_thresholds.json
git add -p docs/live/NOTEPAD.md
```

---

### Task 9: the zone card on the frame, the call, the log and the face (phase 2 ends)

**Files:**
- Modify: `jarvis.py` (`_build`'s market-state block; `call()` zone; `calls()` keys)
- Modify: `jarvis_log.py` (`card`, `state_row`)
- Modify: `docs/kahani/review/mockup/jarvis2.html` (`renderCard`)
- Test: `test_jarvis_state.py` (append)

**Interfaces:**
- Consumes: `mstate.cards(d, rows, piv)`, `mstate.card_line(c)`, `jarvis.MANAGE_WIN`.
- Produces:
  - `d["zone_cards"]`.
  - `call()["zone"]`: the latest card known by the minute and younger than `MANAGE_WIN`, plus `"line"`; or None.
  - The card's `"zone"`; the state row's `"zone"` (`[{t, side, band, verdict, n, N, kind}]` known by then).

- [ ] **Step 1: Write the failing test** (append to `test_jarvis_state.py`)

```python
def test_the_zone_card_shows_from_when_it_was_known_for_45_minutes():
    d = _call_toy()
    d["reads"]["action"] = jarvis.action_words(d)
    d["mstate"] = _state_rows(d)
    card = {"t": "10:05", "close": "10:07", "known": "10:09", "late": False, "side": "BUY", "band": "d2", "px": 23010.0,
            "state": "TREND ▼", "vol": "EXPANDING", "kind": None, "verdict": "SKIP",
            "why": "TREND ▼ + EXPANDING: no bottom fades", "signs": [], "n": 0, "N": 0, "stop": 23000.0,
            "targets": [["VWAP", 23080.0], ["u1", 23100.0]], "gate": {"legal": True, "why": "PE 22900 still building"}}
    d["zone_cards"] = [card]
    assert jarvis.call(jarvis.cut_at(d, 8))["zone"] is None                      # 10:08: not known yet
    c = jarvis.call(jarvis.cut_at(d, 9))
    assert c["zone"]["verdict"] == "SKIP" and c["zone"]["line"].startswith("ZONE d2 23,010f · SKIP · stop 23,000f")
    assert any(x.startswith("zone: ZONE d2") for x in c["why"])
    assert jarvis_log.card(dict(ok=True, day=DAY, idx="NIFTY", mins=["10:09"], fut=[1.0], health={"notes": []},
                                call=c))["zone"]["verdict"] == "SKIP"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest -q test_jarvis_state.py::test_the_zone_card_shows_from_when_it_was_known_for_45_minutes`
Expected: FAIL with `KeyError: 'zone'`.

- [ ] **Step 3: Implement**

In `_build`, in the market-state block of Task 4, replace:

```python
        data["mstate"], data["pivots"] = mstate.fold(data, ach, mstate.norm(idx, day))
    except Exception as e:                           # never the frame: the ACTION word stays the word
        data["mstate"], data["pivots"] = [], []
```

with:

```python
        data["mstate"], data["pivots"] = mstate.fold(data, ach, mstate.norm(idx, day))
        data["zone_cards"] = mstate.cards(data, data["mstate"], data["pivots"])     # spec §6: one card per trigger
    except Exception as e:                           # never the frame: the ACTION word stays the word
        data["mstate"], data["pivots"], data["zone_cards"] = [], [], []
```

In `call()`, inside the `if srow:` block of Task 4, after the `why.insert(0, ...)` statement, add:

```python
        zc = [z for z in d.get("zone_cards") or () if z["known"] <= mins[i] and _m(mins[i]) - _m(z["known"]) < MANAGE_WIN]
        zone = dict(zc[-1], line=mstate.card_line(zc[-1])) if zc else None
        if zone:
            why.insert(1, "zone: " + zone["line"] + f" — {zone['why']}"
                       + (f" · her gate (§1d): {'legal' if zone['gate'].get('legal') else 'NOT legal'} — "
                          f"{zone['gate'].get('why')}" if zone.get("gate") else ""))
```

Before the `if srow:` line, add `    zone = None`. In the return dict, after the `"chips": ...` line, add:

```python
            "zone": zone,
```

In `calls()`'s key tuple, append `"zone"` after `"chips"`.

In `jarvis_log.card`, replace `"mstate": c.get("mstate"), "action": c.get("action"), "chips": c.get("chips")}` with `"mstate": c.get("mstate"), "action": c.get("action"), "chips": c.get("chips"), "zone": c.get("zone")}`.

In `jarvis_log.state_row`, replace `"expiry": s.get("expiry")}` with:

```python
            "expiry": s.get("expiry"),
            "zone": [{k: z.get(k) for k in ("t", "side", "band", "verdict", "n", "N", "kind")}
                     for z in fr.get("zone_cards") or () if z["known"] <= fr["mins"][j]]}
```

In `jarvis2.html`'s `renderCard`, directly after the `if (S) { ... }` block of Task 6, insert:

```js
  const Z = c.zone;                                   // THE ZONE CARD under the state (spec §6): verdict, stop, targets;
  if (Z) {                                            // her §1d gate beside the at-band read (phase 4 is hers to sign)
    row("s clip " + (Z.verdict === "SKIP" ? "q" : "pk"), Z.line,
        [Z.line, Z.why].concat((Z.signs || []).map(s => (s.ok === true ? "✓ " : s.ok === false ? "✗ " : "? ") + s.text)).join("\n"));
    const atb = ((Z.signs || []).find(s => s.k === "wall") || {}).text;
    row("s clip", `gate §1d: ${Z.gate ? (Z.gate.legal ? "legal" : "NOT legal") + " — " + Z.gate.why : "not logged"} · at band: ${atb || "?"}`);
  }
```

- [ ] **Step 4: Run the tests and the full suite**

Run: `python -m pytest -q test_jarvis_state.py test_jarvis_log.py test_mstate.py`, then `python -m pytest -q`
Expected: PASS (the known flaky A49 aside).

- [ ] **Step 5: Mark A257 built, then commit phase 2 (only after Mary says commit; never push)**

In the A257 row, replace `| BUILDING (phase 2) |` with `| BUILT, uncommitted — phase 2 commit on her word |`.

```bash
git add jarvis.py jarvis_log.py docs/kahani/review/mockup/jarvis2.html test_jarvis_state.py
git add -p docs/live/NOTEPAD.md
git commit -m "Jarvis market state, phase 2: the zone card (legality by state, five signs counted, stop / target), her gate beside the at-band read (A257)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9a: §6a — managing an open zone trade (after phase 2)

> Added 6 Nov from her spec amendment §6a ("yes add it"). It is built after phase 2 and committed only on her word. The open questions at the end were decided by the controller as the trader-side owner (her standing rule): every proposed answer was taken.

**Files:**
- Modify: `trigger_log.py` (`log_new`: the zone3 arm `out.extend(...)` and the entry loop's `if rule_tag == "zone3":` block)
- Test: `test_zone3.py` (append)
- Modify: `jarvis.py` (the ZONE loop's key tuple; `data["eff_x"]` after the `data = {...}` dict; `call()`'s zone block from Task 9)
- Modify: `mstate.py` (constants, `_I`; the wall dicts in `signs` gain `"strike"`; `card` gains `u3` / `d3` / `u3_why`; `cards` calls `trades`; append the §6a section)
- Test: `test_mstate.py` (append), `test_jarvis_state.py` (append)
- Modify: `docs/kahani/review/mockup/jarvis2.html` (`renderCard`, under the zone rows of Task 9)
- Modify: `jarvis_thresholds.json`, `docs/live/NOTEPAD.md` (A259)
- Add two rows to the File Structure table:
  - `trigger_log.py | Modify | zone3 rows log their 3-min bar's vwap / u3 / d3 (§6a)`
  - `test_zone3.py | Modify | that logging`

**Interfaces:**
- Consumes:
  - `day_js["bands3"]`: one `{vwap, u1..u3, d1..d3}` or None per 3-min bar, from `live._at_interval` → `contract_bars.bands_on(out["bars"])`.
  - `legs._lad`, `legs.K_MIN`, `legs.K1_L`; `effort.lam_at`, `effort.HI`; `jarvis.MANAGE_WIN`.
  - `mstate._ix` / `_fmt` / `_m` / `_hm` / `START_M`.
  - The frame's `fut` / `fhi` / `flo` / `vwap` / `sd` / `ladder`, the `mstate.fold` rows, and the Task 8 cards.
- Produces:
  - Every NEW zone3 row (arm and entry) gains `"vwap"`, `"u3"` and `"d3"` (rounded to 2), or `"bands3_why"` when its band could not be read. This is additive: no row on disk is rewritten, and `mfe` / `mae` / `stop_hit` / `bands` are never touched.
  - `d["zone"][*]` carries `vwap` / `u3` / `d3` / `bands3_why`.
  - `d["eff_x"]` is present when the frame has a zone trigger: effort ÷ the day median per minute, or None.
  - The wall dict from `signs()` gains `"strike"`. `card()` gains `"u3"`, `"d3"` and `"u3_why"`.
  - Cards from `cards()` gain `"trade"` (a list) and `"in_trade"` (the trigger `t` of the trade they were folded into, else None).
  - `mstate.trade(d, c, rows, later=()) -> [{"t", "open", "chips", "why", "risk"}] | None`; `mstate.trades(d, cs, rows) -> cs`; `mstate._holds`; `mstate._open_at`.
  - `call()["zone"]["open"]`: `{"of", "t", "open", "chips", "why", "risk"}` or None. `call()["zone"]` never carries `"trade"`, so no later minute leaks into it.

- [ ] **Step 1: Write the failing test for the logger** (append to `test_zone3.py`)

```python
# ---- Task 9a: every zone3 row logs its own 3-min bar's VWAP / u3 / d3 (spec 2026-11-06 §6a) ----------------------------

def test_zone3_rows_carry_their_bars_vwap_u3_d3_and_old_rows_stay_byte_identical(tmp_path, monkeypatch):
    import trigger_log
    path = _fresh(tmp_path)
    old = ('{"day": "2026-10-28", "index": "NIFTY", "t": "10:00", "side": "BUY", "band": "d2", "rule": "zone3", '
           '"px": 1.0, "mfe": 5.0, "mae": -2.0, "stop_hit": false}\n')
    with open(path, "w", encoding="utf-8") as f:                                 # a row already on disk (tmp only)
        f.write(old)
    monkeypatch.setattr(band_rotation, "ZONE3_FROM", "2000-01-01")
    out = _out()
    assert trigger_log.log_new("NIFTY", _payload(), None, ones=_ones(), path=path) == 2
    lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
    assert lines[0] == old                                                      # never rewritten, scores untouched
    arm, entry = [json.loads(x) for x in lines[1:]]
    b3 = {b["t"]: x for b, x in zip(out["bars"], out["bands3"])}
    for r in (arm, entry):
        assert {k: r[k] for k in ("vwap", "u3", "d3")} == {k: round(b3[r["t"]][k], 2) for k in ("vwap", "u3", "d3")}
        assert not {"mfe", "mae", "stop_hit", "bands"} & set(r)                  # a write never carries a score
```

(`_fresh`, `_out`, `_payload`, `_ones` and `band_rotation` are the helpers and imports already in `test_zone3.py`. If a name differs, use the real one and report it.)

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest -q test_zone3.py::test_zone3_rows_carry_their_bars_vwap_u3_d3_and_old_rows_stay_byte_identical`
Expected: FAIL with `KeyError: 'vwap'`.

- [ ] **Step 3: Implement the logger**

In `trigger_log.log_new`, directly after `z3on = day >= band_rotation.ZONE3_FROM`, add:

```python
        # §6a (spec 2026-11-06, plan Task 9a): every zone3 row carries its own 3-min bar's VWAP / u3 / d3 -- bands3,
        # the bands it armed and entered on -- so the open-trade card reads the u3 line as logged, never recomputed.
        # Additive keys on NEW rows only: a row on disk is never rewritten. An unreadable band says so, never a zero.
        b3 = {b.get("t"): x for b, x in zip(bars, day_js.get("bands3") or ()) if isinstance(b, dict)}

        def _b3(t):
            x = b3.get(t)
            return ({k: round(x[k], 2) for k in ("vwap", "u3", "d3")} if x
                    else {"bands3_why": "the 3-min band could not be read on this bar"})
```

In the zone3 arm block, replace `out.extend(json.dumps(dict(r, bands_on="3m")) for r in` with:

```python
                out.extend(json.dumps(dict(r, bands_on="3m", **_b3(r.get("t")))) for r in
```

In the entry loop, replace:

```python
            if rule_tag == "zone3":     # ZONE-3M: bands on its own 3-min bars
                row["bands_on"] = "3m"  # (absent on every other row)
```

with:

```python
            if rule_tag == "zone3":     # ZONE-3M: bands on its own 3-min bars
                row["bands_on"] = "3m"  # (absent on every other row)
                row.update(_b3(bar.get("t")))   # §6a: its bar's VWAP / u3 / d3 (Task 9a)
```

Run: `python -m pytest -q test_zone3.py test_trigger_log.py`
Expected: PASS. The live server picks this up only at Mary's next `.\stop.bat; .\start-v2.bat`. Never restart it.

- [ ] **Step 4: Write the failing tests for the open trade** (append to `test_mstate.py`)

```python
# ---- Task 9a: §6a, managing an open zone trade (display only; she decides) --------------------------------------------

def _trade_frame(pts, lad=lambda T: 60.0):
    """A SELL at u2 11:00 (close 11:02, 24,095): VWAP 24,050 sigma 30, the median 1-min candle 2 pts, the CE at the
    band (24,100) on the ladder every minute at lad(clock minute)."""
    d = _frame(_path(pts))
    n = len(d["mins"])
    d.update(vwap=[24050.0] * n, sd=[30.0] * n)
    d["ladder"] = {t: {"ce": {24100: lad(555 + j)}, "pe": {}} for j, t in enumerate(d["mins"])}
    return d


def _tc(d, **kw):
    """A card as mstate.card makes it (Task 8) plus the logged u3 / d3: SELL 11:00, stop = the trigger candle's high."""
    js = [d["mins"].index(m) for m in ("11:00", "11:01", "11:02")]
    return dict({"t": "11:00", "close": "11:02", "known": "11:03", "side": "SELL", "px": 24095.0,
                 "stop": max(d["fhi"][j] for j in js), "u3": 24150.0, "d3": 23950.0, "u3_why": None,
                 "verdict": "TAKE · smaller target", "targets": [["VWAP", 24050.0]],
                 "signs": [{"k": "wall", "ok": True, "text": "24,100s CE at the band +0.0L / 9 min", "strike": 24100}]},
                **kw)


# into u2, the trigger, then a slow creep to 0.5 pt under the 24,111 stop from 11:05, held 15 min, then down to VWAP
CREEP = [(0, 24000), (105, 24110), (107, 24095), (110, 24109.5), (125, 24109.5), (140, 24040)]
FAST = [(0, 24000), (105, 24110), (107, 24095), (110, 24130), (140, 24130)]
BREAK = [(0, 24000), (105, 24110), (107, 24095), (110, 24109.5), (125, 24109.5), (128, 24125), (140, 24125)]
ADDUP = [(0, 24000), (105, 24110), (107, 24095), (110, 24109.5), (125, 24109.5), (128, 24160), (140, 24160)]


def test_widen_shows_after_six_slow_minutes_near_the_stop_and_the_target_ends_it():
    d = _trade_frame(CREEP)
    E = {e["t"]: e for e in mstate.trade(d, _tc(d), _rows(d, vol="CONTRACTING"))}
    assert min(E) == "11:03" and not any(c.startswith("WIDEN") for c in E["11:10"]["chips"])   # 5 min near: hidden
    assert E["11:11"]["chips"][:2] == ["WIDEN · stop → beyond u3 24,150f", "risk to u3: 55 pts"]
    assert E["11:11"]["risk"] == 55.0 and E["11:11"]["why"][0].startswith("WIDEN 11:11: writers tike: 24,100s CE")
    assert E["11:33"]["open"] is False and E["11:33"]["chips"][-1] == "target VWAP 24,050f ✓ — trade poora"
    assert max(E) == "11:33"
    x = {e["t"]: e for e in mstate.trade(d, _tc(d), _rows(d, vol="EXPANDING"))}     # TREND ▲ + EXPANDING vs a SELL
    assert not any(c.startswith("WIDEN") for e in x.values() for c in e["chips"])
    assert "no WIDEN: TREND ▲ + EXPANDING against the trade" in x["11:11"]["why"]
    assert "%" not in json.dumps([E, x])


def test_a_fast_stop_says_it_was_not_the_trade():
    d = _trade_frame(FAST)
    tr = mstate.trade(d, _tc(d), _rows(d, vol="CONTRACTING"))
    assert [e["t"] for e in tr] == ["11:03", "11:04"] and tr[-1]["open"] is False
    assert tr[-1]["chips"][-1] == "stop hua — yeh trade nahi tha · 24,111f · fast — straight through (WIDEN needs 6 min)"
    assert "%" not in json.dumps(tr)


def test_writers_leaving_the_band_hide_widen_and_the_stop_says_why():
    d = _trade_frame(BREAK, lad=lambda T: 60.0 if T < 660 else 60.0 - (T - 660))     # the CE at the band -1L a minute
    E = {e["t"]: e for e in mstate.trade(d, _tc(d), _rows(d, vol="CONTRACTING"))}
    assert not any(c.startswith("WIDEN") for e in E.values() for c in e["chips"])
    assert E["11:21"]["open"] is False and E["11:21"]["chips"][-1] == (
        "stop hua — yeh trade nahi tha · 24,111f · writers at 24,100s CE leaving -9.0L / 9 min · effort: could not check")


def test_add_once_while_the_widen_stands_and_the_hard_line_ends_both_lots():
    d = _trade_frame(ADDUP)
    c1, c2 = _tc(d), _tc(d, t="11:12", close="11:14", known="11:15", px=24105.0)
    mstate.trades(d, [c1, c2], _rows(d, vol="CONTRACTING"))
    E = {e["t"]: e for e in c1["trade"]}
    assert c2["trade"] is None and c2["in_trade"] == "11:00"                     # folded: the ADD, never a 2nd trade
    assert not any(c.startswith("ADD") for c in E["11:14"]["chips"])
    assert E["11:15"]["chips"] == ["WIDEN · stop → beyond u3 24,150f", "ADD 1 · avg 24,100f · stop beyond u3 24,150f",
                                   "risk to u3: 55 + 45 = 100 pts (dono lot)"] and E["11:15"]["risk"] == 100.0
    assert E["11:21"]["open"] is True                                            # past the old stop: widened, still open
    assert E["11:23"]["open"] is False and E["11:23"]["chips"][-1] == "u3 ke paar 3-min close 24,160f — dono lot band"
    assert max(E) == "11:23" and "%" not in json.dumps(c1["trade"])


def test_no_add_after_a_broken_widen_and_no_third_adjustment():
    d = _trade_frame(ADDUP, lad=lambda T: 60.0 if T <= 672 else 60.0 - 3 * (T - 672))   # writers leave from 11:13
    c1, c2 = _tc(d), _tc(d, t="11:12", close="11:14", known="11:15", px=24105.0)
    mstate.trades(d, [c1, c2], _rows(d, vol="CONTRACTING"))
    E = {e["t"]: e for e in c1["trade"]}
    assert E["11:15"]["chips"] == ["WIDEN · stop → beyond u3 24,150f", "WIDEN toota — ADD nahi", "risk to u3: 55 pts"]
    assert not any(c.startswith("ADD") for e in E.values() for c in e["chips"])
    assert any(w.startswith("WIDEN broken 11:13: writers at 24,100s CE leaving -3.0L") for w in E["11:15"]["why"])
    assert E["11:23"]["chips"][-1] == "u3 ke paar 3-min close 24,160f — trade band"


def test_a_row_without_u3_could_not_check_never_a_zero():
    d = _trade_frame(CREEP)
    tr = mstate.trade(d, _tc(d, u3=None, d3=None), _rows(d, vol="CONTRACTING"))
    assert all(e["chips"][0] == "u3: could not check — u3 not logged (row before 6 Nov)" for e in tr)
    assert all(e["risk"] is None for e in tr)
    assert not any(c.startswith(("WIDEN", "ADD", "risk")) for e in tr for c in e["chips"])
    assert tr[-1]["chips"][-1] == "target VWAP 24,050f ✓ — trade poora"            # the stop and target still read
    zc = mstate.card(_zone_frame(), Z, _rows(_zone_frame()), [])                  # Z has no u3: the card says None
    assert zc["u3"] is None and zc["signs"][1]["strike"] == 24100
    assert "%" not in json.dumps(tr)


def test_the_trade_is_causal():
    d = _trade_frame(ADDUP)
    rows, c2 = _rows(d, vol="CONTRACTING"), _tc(d, t="11:12", close="11:14", known="11:15", px=24105.0)
    full, N = mstate.trade(d, _tc(d), rows, [c2]), len(d["mins"])
    for e in full:                                                               # minute j reads minutes <= j only
        j = d["mins"].index(e["t"])
        cut = {k: (v[:j + 1] if isinstance(v, list) and len(v) == N else v) for k, v in d.items()}
        assert mstate.trade(cut, _tc(d), rows[:j + 1], [c2])[-1] == e
```

(`_frame`, `_path`, `_rows`, `_zone_frame` and `Z` are the existing helpers in `test_mstate.py`. Check their real signatures. Note: `_frame`'s day is before 6 Nov, so "(row before 6 Nov)" is expected. The exact chip strings and minute stamps were derived by hand from the code below. If a number differs because a helper's real path or candle size differs, fix the TEST FIXTURE, never the rule, and report the difference.)

- [ ] **Step 5: Run them to verify they fail**

Run: `python -m pytest -q test_mstate.py`
Expected: FAIL with `AttributeError: module 'mstate' has no attribute 'trade'`.

- [ ] **Step 6: Implement `mstate`**

After the `SYNC_WIN = 30 ...` line (or the last zone-card constant), add:

```python
WIDEN_MIN = 6                 # [I] §6a WIDEN: >= 6 consecutive min near the trigger-candle stop without crossing it
NEAR_X = 1.0                  # [I] §6a "near the stop": a minute's high (SELL; BUY its low) within 1.0 x the day's median
                              #     1-min candle so far (her §1e yardstick): scales across NIFTY / BANKNIFTY / SENSEX
```

Add `"WIDEN_MIN", "NEAR_X"` to the end of the `_I = (...)` tuple.

In `signs()`, sign 2: add `"strike": k` to each wall dict that sign appends (both the `ok: None` one and the read one). `k` is the strike the sign reads, which after Task 8's fix comes from `level` when it was logged.

In `card()`, add to the card dict:

```python
         "u3": z.get("u3"), "d3": z.get("d3"), "u3_why": z.get("bands3_why"),       # §6a: as logged (Task 9a)
```

In `cards()`, replace the final `return [c for c in out if c]` (or its equivalent) with `return trades(d, [c for c in out if c], rows)     # §6a`.

Append to the end of `mstate.py`:

```python
# ---- §6a: managing an open zone trade (spec 2026-11-06 §6a; display only, she decides) --------------------------------

def _holds(d, j, top, k, row):
    """WIDEN's reasons at minute j -> (True, why) when the state is not EXPANDING against the trade and sign 2 (the
    writers at the band's strike k not leaving over legs.K_MIN min) or sign 3 (effort without result, >= effort.HI; read
    at a high only, as signs()) holds; else (False, why). Unread is never a yes (rule 6)."""
    D, vol = (1 if top else -1), (row.get("vol") or {}).get("word")
    if row.get("dir") == D and vol == "EXPANDING":
        return False, f"{row['word']} + EXPANDING against the trade"
    if vol in (None, "?"):
        return False, "vol: could not check"
    t, (sd_, SD) = d["mins"][j], (("ce", "CE") if top else ("pe", "PE"))
    a, b = legs._lad(d, t, sd_, k), legs._lad(d, _hm(_m(t) - legs.K_MIN), sd_, k)
    x = (d.get("eff_x") or [None] * (j + 1))[j] if top else None
    if a is not None and b is not None and a - b >= -legs.K1_L:
        return True, f"writers tike: {_fmt(k)}s {SD} {a - b:+.1f}L / {legs.K_MIN} min"
    if x is not None and x >= effort.HI:
        return True, f"effort {x:.1f}× bina result"
    w = (f"writers at the band: could not check — {_fmt(k)}s {SD} not on the ladder" if a is None or b is None
         else f"writers at {_fmt(k)}s {SD} leaving {a - b:+.1f}L / {legs.K_MIN} min")
    e = ("effort: not read at a low" if not top else "effort: could not check" if x is None
         else f"effort {x:.1f}× (needs {effort.HI:.0f}×)")
    return False, f"{w} · {e}"


def trade(d, c, rows, later=()):
    """§6a, ONE open zone trade, display only (she decides; nothing gates, nothing places) -> [{"t", "open", "chips",
    "why", "risk"}], one per frame minute from the card's `known` to its end; None for a card with no stop. Walked from
    the trigger's close (a late row's earlier minutes count; shown from `known`); minute j reads minutes <= j only.
    Open until the first of: the trigger-candle stop crossed with no WIDEN standing ("stop hua — yeh trade nahi tha":
    fast, or why WIDEN could not stand); the hard line, a 3-min close beyond u3 (SELL; d3 BUY), ending both lots; the
    last target (live VWAP, then the next band; VWAP only on a smaller target); jarvis.MANAGE_WIN after `known`.
    WIDEN (once): WIDEN_MIN consecutive minutes with the high (BUY: low) within NEAR_X median 1-min candles of the stop,
    not crossed, _holds true, before VWAP is touched, on a card that is not SKIP, with u3 logged beyond the stop. Then
    the stop is beyond u3 (as logged at the trigger bar: a stop is a price). If _holds later fails the WIDEN is shown
    broken: no ADD, and the stop stays (no third adjustment). ADD 1 (once): the first `later` same-side card, not SKIP,
    known while the WIDEN stands; avg = the two trigger closes. Risk = points from each lot's entry to u3, summed; never
    a %. u3 not logged -> could not check, never a zero (rule 6)."""
    import jarvis
    i = _ix(d, c["close"])
    if c.get("stop") is None or not c.get("signs") or i is None:
        return None
    mins, top, S = d["mins"], c["side"] == "SELL", c["stop"]
    D, nm, bn = (1, "u3", "d1") if top else (-1, "d3", "u1")
    L, k = c.get(nm), next((s for s in c["signs"] if s["k"] == "wall"), {}).get("strike")
    no3 = None if L is not None else f"{nm}: could not check — " + (c.get("u3_why") or f"{nm} not logged " + (
        "(row before 6 Nov)" if d["day"] < "2026-11-06" else "on this row"))
    bar = ("the card said SKIP — no WIDEN" if c["verdict"] == "SKIP" else no3 if no3 else
           None if D * (L - S) > 0 else f"{nm} {_fmt(L)}f is not beyond the stop {_fmt(S)}f")
    K0, lots, out = _m(c["known"]), [c["px"]], []
    near0 = widen = broke = paid = why_not = None
    for j in range(i + 1, len(mins)):
        t, T = mins[j], _m(mins[j])
        if T - K0 >= jarvis.MANAGE_WIN:
            break
        ax, fx = (d["fhi"][j], d["flo"][j]) if top else (d["flo"][j], d["fhi"][j])
        vw, b1, end = d["vwap"][j], d["vwap"][j] - D * d["sd"][j], None
        if not widen and D * (ax - S) > 0:                            # the trigger-candle stop, no WIDEN standing
            end = f"stop hua — yeh trade nahi tha · {_fmt(S)}f · " + (
                (f"fast — {T - near0} min near it" if near0 else "fast — straight through") + f" (WIDEN needs {WIDEN_MIN} min)"
                if not near0 or T - near0 <= WIDEN_MIN else why_not)
        elif L is not None and (T - START_M) % 3 == 2 and D * (d["fut"][j] - L) > 0:     # the hard line, her 3-min close
            end = f"{nm} ke paar 3-min close {_fmt(d['fut'][j])}f — " + ("dono lot band" if len(lots) > 1 else "trade band")
        else:
            paid = paid or ((t, vw) if D * (vw - fx) >= 0 else None)   # VWAP touched (live: she trails band to band)
            if paid and (len(c["targets"]) == 1 or D * (b1 - fx) >= 0):
                end = (f"target VWAP {_fmt(paid[1])}f ✓ — trade poora" if len(c["targets"]) == 1
                       else f"target {bn} {_fmt(b1)}f ✓ — trade poora")
        if not end:
            one = statistics.median(d["fhi"][x] - d["flo"][x] for x in range(j + 1))    # her §1e candle, minutes <= j
            near0 = (near0 or T) if not widen and D * (S - ax) <= NEAR_X * one else None
            if near0 and not widen and T - near0 >= WIDEN_MIN:
                ok, w = (False, bar or "VWAP touched — no WIDEN after it") if bar or paid else _holds(d, j, top, k, rows[j])
                widen, why_not = ((t, w), None) if ok else (None, w)
            elif widen and not broke:
                ok, w = _holds(d, j, top, k, rows[j])
                broke = None if ok else (t, w)
            if widen and not broke and len(lots) == 1:
                c2 = next((x for x in later if widen[0] <= x["known"] <= t and x["verdict"] != "SKIP"), None)
                if c2:
                    lots.append(c2["px"])
        chips, why, risk = ([no3] if no3 else []), [], None
        if widen:
            rs = [D * (L - p) for p in lots]
            risk = round(sum(rs), 1)
            chips.append(f"WIDEN · stop → beyond {nm} {_fmt(L)}f")
            why.append(f"WIDEN {widen[0]}: {widen[1]}")
            if broke:
                chips.append("WIDEN toota — ADD nahi")
                why.append(f"WIDEN broken {broke[0]}: {broke[1]} · the stop stays beyond {nm} (no third adjustment)")
            if len(lots) > 1:
                chips.append(f"ADD 1 · avg {_fmt(sum(lots) / 2)}f · stop beyond {nm} {_fmt(L)}f")
            chips.append(f"risk to {nm}: " + (f"{rs[0]:.0f} pts" if len(rs) == 1 else
                                             f"{rs[0]:.0f} + {rs[1]:.0f} = {sum(rs):.0f} pts (dono lot)"))
        elif why_not:
            why.append(f"no WIDEN: {why_not}")
        if paid and not end:
            chips.append(f"VWAP {_fmt(paid[1])}f ✓ → {bn}")
        if end:
            chips.append(end)
        out.append({"t": t, "open": not end, "chips": chips, "why": why, "risk": risk})
        if end:
            break
    shown = [e for e in out if e["t"] >= c["known"]]
    return shown or ([dict(out[-1], t=c["known"])] if out and not out[-1]["open"] else [])


def _open_at(c, t):
    """Was card c's trade open at clock minute t? (A trade whose window ran out is open through its last minute.)"""
    tr = c.get("trade") or []
    return bool(tr) and tr[0]["t"] <= t and (t < tr[-1]["t"] or (t == tr[-1]["t"] and tr[-1]["open"]))


def trades(d, cs, rows):
    """§6a over the frame's cards, in the record's order: a card known while an earlier same-side trade is open is
    folded into it (`in_trade`: the ADD candidate, never a second trade); every other card gets its own `trade`.
    ponytail: record order, not `known` order -- a late row is judged against the trades before it in the file."""
    for n, c in enumerate(cs):
        p = next((p for p in reversed(cs[:n]) if p["side"] == c["side"] and _open_at(p, c["known"])), None)
        c["trade"], c["in_trade"] = ((None, p["t"]) if p else
                                     (trade(d, c, rows, [x for x in cs[n + 1:] if x["side"] == c["side"]]), None))
    return cs
```

Make sure `statistics`, `effort` and `legs` are imported at the top of `mstate.py`; add any that are missing. Mind the frame's holes (Task 8's fix): `d["mins"]` skips absent minutes. The walk above steps frame rows, and its 3-min-close test uses the clock minute `T`, so that is consistent. Report any place where a hole could make a chip lie.

Run: `python -m pytest -q test_mstate.py`
Expected: PASS.

- [ ] **Step 7: Write the failing test for the call** (append to `test_jarvis_state.py`)

```python
def test_the_open_trade_rides_on_the_zone_card_and_never_shows_a_later_minute():
    d = _call_toy()
    d["reads"]["action"] = jarvis.action_words(d)
    d["mstate"] = _state_rows(d)
    tr = [{"t": "10:09", "open": True, "chips": ["WIDEN · stop → beyond d3 22,950f", "risk to d3: 60 pts"],
           "why": ["WIDEN 10:09: writers tike: 22,900s PE +1.0L / 9 min"], "risk": 60.0},
          {"t": "10:12", "open": False, "chips": ["d3 ke paar 3-min close 22,940f — trade band"], "why": [], "risk": 60.0}]
    card = {"t": "10:05", "close": "10:07", "known": "10:09", "late": False, "side": "BUY", "band": "d2", "px": 23010.0,
            "level": None, "state": "TREND ▼", "vol": "EXPANDING", "kind": "fade", "verdict": "TAKE · smaller target",
            "why": "TREND ▼ + EXPANDING: a fade only if the band stopped", "signs": [], "n": 2, "N": 4, "stop": 23000.0,
            "stop_why": None, "targets": [["VWAP", 23080.0]], "gate": None, "u3": None, "d3": 22950.0, "u3_why": None,
            "trade": tr, "in_trade": None}
    d["zone_cards"] = [card]
    c = jarvis.call(jarvis.cut_at(d, 10))                                        # 10:10
    assert "trade" not in c["zone"] and c["zone"]["open"]["of"] == "10:05" and c["zone"]["open"]["t"] == "10:09"
    assert c["zone"]["open"]["chips"][0] == "WIDEN · stop → beyond d3 22,950f"
    assert any("open 10:05: WIDEN · stop → beyond d3 22,950f" in x for x in c["why"])
    e = jarvis.call(jarvis.cut_at(d, 12))["zone"]["open"]                        # 10:12: the hard line
    assert e["open"] is False and e["chips"] == ["d3 ke paar 3-min close 22,940f — trade band"]
    assert "%" not in json.dumps(c["zone"])
```

(Check that `_call_toy`'s minutes at indexes 10 and 12 are 10:10 and 10:12, and adjust the indexes if they aren't. The empty `signs` here makes `card_line` print its why; that is fine for this test.)

- [ ] **Step 8: Run it to verify it fails**

Run: `python -m pytest -q test_jarvis_state.py::test_the_open_trade_rides_on_the_zone_card_and_never_shows_a_later_minute`
Expected: FAIL with an `AssertionError` on `"trade" not in c["zone"]`.

- [ ] **Step 9: Implement the wiring**

In `_build`'s ZONE loop, add `"vwap", "u3", "d3", "bands3_why"` to the key tuple that copies the trigger_log row (comment: `vwap / u3 / d3: §6a (Task 9a)`). Never copy a scored field (`mfe`, `mae`, `stop_hit`, `bands`, `f15`, `f30`, `scored_at`).

Directly after the `data = {...}` dict, add:

```python
    if any(not z.get("kind") for z in ZONE):         # §6a: effort per minute for an open zone trade's WIDEN (sign 3 at
        data["eff_x"] = [(lambda a: round(a[0] / a[1], 2) if a[0] and a[1] else None)(   # minute m: effort.lam_at's
            effort.lam_at(inp.get("fm") or {}, _m(m))) for m in mins]                   # m-4..m; SENSEX: NIFTY's, §1q)
```

(`eff_x` is a list with the frame's length, so `cut_at` slices it per minute. That is correct here; keep it OUT of `cut_at`'s exclusion list.)

In `call()`, find Task 9's zone block. It computes `zc` (cards known by this minute and within `MANAGE_WIN`) and `zone` = the latest card plus `line`, then inserts the zone why line; Task 9's fix guards the gate with `isinstance(gate, dict)`. Change it so that:
- `tc = [z for z in zc if z.get("trade")]`, and `op = [e for e in tc[-1]["trade"] if e["t"] <= mins[i]] if tc else []`;
- `zone` is the latest card WITHOUT its `"trade"` key, plus `"line"`, plus `"open": dict(op[-1], of=tc[-1]["t"]) if op else None`;
- the zone why line gains `f" · open {O['of']}: " + " · ".join(O["chips"])` when `O` and `O["chips"]`;
- the existing gate guard stays.

In `jarvis2.html`'s `renderCard`, inside Task 9's zone block, after the gate row, insert:

```js
    const O = Z.open;                                 // §6a: the open trade's chips, verbatim (display only; she decides)
    if (O && O.chips && O.chips.length) {
      const oc = row("rc", "", [`trade of ${O.of}`].concat(O.why || []).join("\n"));
      for (const t of O.chips) {
        const el = document.createElement("span");
        el.className = "chip " + (/^stop hua|ke paar|toota/.test(t) ? "bad" : /^(WIDEN|ADD) ·/.test(t) ? "you" : /✓/.test(t) ? "ok" : "q");
        el.textContent = t; oc.appendChild(el);
      }
    }
```

(Check that the CSS classes `chip bad`, `chip you`, `chip ok` and `chip q` exist on the page; use the nearest existing light-mode classes if not, and report it.)

- [ ] **Step 10: Thresholds and NOTEPAD**

In `jarvis_thresholds.json`, add `"mstate.WIDEN_MIN": 6` and `"mstate.NEAR_X": 1.0` beside the other `mstate.*` keys, and add to `_why`:

```json
  "mstate.WIDEN_MIN": "§6a WIDEN: >= 6 consecutive min near the trigger-candle stop without crossing it (spec 2026-11-06 §6a, A259)",
  "mstate.NEAR_X": "§6a near the stop: a minute's high (BUY: low) within 1.0 x the day's median 1-min candle so far (her §1e yardstick: one ordinary minute away; less needs a near-touch, more counts a normal pullback as approaching)"
```

In `docs/live/NOTEPAD.md`, insert after the A258 row (or after A257 if A258 is not written yet):

```markdown
| A259 | 6 Nov (spec 2026-11-06 §6a, from her 09:57 → 10:33 NIFTY sells; plan Task 9a) | **Her open zone trade had no management read: when to widen, when to add, where it ends. And no zone3 row logged the u3 line or the VWAP it needs.** | 6 Nov trigger_log [M]: NIFTY zone3 SELL u2 09:57 (24,637.8f, level 24,648.5) and 10:33 (24,680.0f, level 24,705.2), the leg's second same-side trigger; neither row carries u3 or VWAP (a row's `level` is the u2 it armed on; the scorer's `bands` is which bands were reached later, not their prices) | `trigger_log.log_new`: every NEW zone3 row (arm and entry) carries its own 3-min bar's `vwap` / `u3` / `d3` from `bands3` (rounded 2; an unreadable band writes `bands3_why`). Additive: no row rewritten, no scored field touched. `mstate.trade` / `trades` (display only, she decides): WIDEN "stop → beyond u3" after `WIDEN_MIN` consecutive minutes with the high (a BUY: the low) within `NEAR_X` median 1-min candles of the trigger-candle stop and not crossed, with the writers at the band's strike not leaving (sign 2) or effort ≥ 2× (sign 3, highs only), and the state not EXPANDING against the trade; never on a SKIP card or after VWAP is touched. "stop hua — yeh trade nahi tha" when the stop is crossed fast or with WIDEN's reason failing. ADD 1 once, on the next same-side non-SKIP card known while the WIDEN stands (avg of the two trigger closes; that card is folded into the trade, never a second one). The hard line, a 3-min close beyond u3 as logged, ends both lots. A WIDEN whose reason fails is shown broken: no ADD, and the stop stays (no third adjustment). Target: live VWAP, then the next band (VWAP only on a smaller target). Open until those or `jarvis.MANAGE_WIN`. Risk = points from each lot's entry to u3, summed, never a %. Rows without u3 read "u3: could not check — u3 not logged (row before 6 Nov)" (6 Nov rows: "… on this row"). [I]: `mstate.WIDEN_MIN` 6 (spec), `NEAR_X` 1.0 (her §1e yardstick, scales across the three indices). Open questions decided by the controller (trader side, 6 Nov): u3 is the logged price (a stop is a price), the targets read live; a broken WIDEN keeps the stop beyond u3, no exit chip; no WIDEN / ADD on a SKIP card; "same leg" = the first trade still open; "near" must be consecutive; no WIDEN after VWAP is touched; a late row is walked from its close and shown from `known`. Her §1d gate is shown verbatim, unchanged (phase 4 is hers) | BUILT, uncommitted — commit on her word |
```

- [ ] **Step 11: Run the focused tests** (the full suite runs after 15:40, by the controller)

Run: `python -m pytest -q test_zone3.py test_trigger_log.py test_mstate.py test_jarvis_state.py test_jarvis_log.py test_thresholds.py test_jarvis.py`
Expected: PASS, apart from the 2 known pre-existing `test_jarvis.py` failures (A241 record drift).

- [ ] **Step 12: Stage** (no commit: commits happen on Mary's word; never push)

```bash
git add trigger_log.py test_zone3.py mstate.py test_mstate.py jarvis.py test_jarvis_state.py jarvis_thresholds.json docs/kahani/review/mockup/jarvis2.html
# NOTEPAD: only the A259 hunk (patch method; foreign edits stay unstaged)
```

The logger change reaches the live record only after Mary restarts the server. Never restart it, and never write to `data/trigger_log.jsonl`.

#### Open questions: decided (controller, trader side, 6 Nov)

1. **u3: logged price or moving band?** The logged price at the trigger bar is the WIDEN stop and the hard line, because a stop is a price. The targets (VWAP, then the next band) read live, since she trails them.
2. **The stop after a broken WIDEN.** It stays beyond u3, and the card shows "WIDEN toota — ADD nahi" with the reason. There is no exit chip: an exit chip would be a new rule.
3. **SKIP cards.** They get no WIDEN and no ADD, because both add risk. The stop, hard line and target lines still show.
4. **"Same leg" for ADD.** It means the first trade is still open. `legs.py`'s leg is not used, because its origin can reset mid-trade.
5. **"Near the stop".** It must hold for 6 minutes in a row. One minute away from the stop restarts the count.
6. **After VWAP is touched.** There is no WIDEN.
7. **Late rows.** They are walked from the close and shown from `known`, so a stop hit before the row was written shows as already ended.

---

## Phase 3 — cross-index (spec §10.3)

### Task 10: the ALL 3 read's N slot reads NIFTY on every frame

**Files:**
- Modify: `jarvis.py:1873-1879` (`reads()`'s `sync_at`)
- Test: `test_jarvis_state.py` (append)

**Interfaces:**
- Consumes: `d["nf"]` (Task 7).
- Produces: `reads(d)["sync"][i]["ch"] == [N, BN, SX]`. N is NIFTY's future on a NIFTY frame and NIFTY's spot on a SENSEX or BANKNIFTY frame. Before this fix, a SENSEX frame's N slot was SENSEX's own future, and a BANKNIFTY frame's N slot was BANKNIFTY's.

- [ ] **Step 1: Write the failing test** (append to `test_jarvis_state.py`)

```python
def test_all3_reads_nifty_in_its_n_slot_on_a_sensex_frame():
    d = _toy()
    n = len(d["mins"])
    d["idx"] = "SENSEX"
    d["fut"] = [74000.0 - 12 * i for i in range(n)]               # SENSEX's own future falls 60 in 5 min ...
    d["nf"] = [23000.0] * n                                       # ... NIFTY does not move
    s = jarvis.reads(d)["sync"][10]
    assert s["ch"][0] == 0.0 and s["dir"] == 0                    # not "all 3 ▼": NIFTY did not move
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest -q test_jarvis_state.py::test_all3_reads_nifty_in_its_n_slot_on_a_sensex_frame`
Expected: FAIL (`ch[0] == -60.0`, `dir == -1`).

- [ ] **Step 3: Implement**

In `reads()`, replace:

```python
        ch = [None if a[i] is None or a[i - 5] is None else round(a[i] - a[i - 5], 2) for a in (fut, d["bnf"], d["sx"])]
```

with:

```python
        nf = fut if d.get("idx") in (None, "NIFTY") else (d.get("nf") or [None] * N)   # N is NIFTY on every frame (spec
        ch = [None if a[i] is None or a[i - 5] is None else round(a[i] - a[i - 5], 2)   # §4: it read the frame's own future)
              for a in (nf, d["bnf"], d["sx"])]
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest -q test_jarvis_state.py test_jarvis.py`
Expected: PASS.

- [ ] **Step 5: Stage**

```bash
git add jarvis.py test_jarvis_state.py
```

---

### Task 11: 0 DTE mode on the state

**Files:**
- Modify: `mstate.py` (`fold`: the `dte` line and the row's `expiry`)
- Test: `test_mstate.py` (append)

**Interfaces:**
- Consumes: `d["ctx"]["dte"]`, `jarvis.UNWIND_AT` ("14:00"), `NO_HOLD_AT` ("15:00").
- Produces: `rows[i]["expiry"]`:
  - `"EXPIRY: gamma both ways"` on 0 DTE from 14:00;
  - `"EXPIRY: gamma both ways · no hold for the close"` from 15:00;
  - otherwise None.
  - `call()["mstate"]["expiry"]` already carries it (Task 4), and the face already joins it (Task 6). The card's 15:00 rule is in `legal` (Task 8).

- [ ] **Step 1: Write the failing test** (append to `test_mstate.py`)

```python
def test_zero_dte_says_gamma_both_ways_from_14_and_no_hold_from_15():
    d = _frame([24000.0] * 351)                                   # 09:15 .. 15:05
    d["ctx"]["dte"] = 0
    rows, _ = mstate.fold(d)
    at = {r["t"]: r["expiry"] for r in rows}
    assert at["13:59"] is None and at["14:00"] == "EXPIRY: gamma both ways"
    assert at["15:00"] == "EXPIRY: gamma both ways · no hold for the close"
    d["ctx"]["dte"] = 1
    assert all(r["expiry"] is None for r in mstate.fold(d)[0])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest -q test_mstate.py::test_zero_dte_says_gamma_both_ways_from_14_and_no_hold_from_15`
Expected: FAIL with `KeyError: 'expiry'`.

- [ ] **Step 3: Implement**

In `fold`, replace `    LR = (d.get("legs") or {}).get("rows") or []` with:

```python
    import jarvis
    LR = (d.get("legs") or {}).get("rows") or []
    dte = (d.get("ctx") or {}).get("dte")
```

Replace the last statement of the loop:

```python
        out.append({"t": t, "word": w, "dir": D, "conf": st["conf"], "since": since, "why": why, "line": line,
                    "eff": eff, "vx": vx, "price": what, "vol": vol})
```

with:

```python
        exp = None
        if dte == 0 and t >= jarvis.UNWIND_AT:                     # 0 DTE (spec §4): gamma both ways from 14:00
            exp = "EXPIRY: gamma both ways" + (" · no hold for the close" if t >= NO_HOLD_AT else "")
        out.append({"t": t, "word": w, "dir": D, "conf": st["conf"], "since": since, "why": why, "line": line,
                    "eff": eff, "vx": vx, "price": what, "vol": vol, "expiry": exp})
```

Add `"expiry"` to `fold`'s docstring list of row keys.

- [ ] **Step 4: Run the tests**

Run: `python -m pytest -q test_mstate.py`
Expected: PASS.

- [ ] **Step 5: Stage**

```bash
git add mstate.py test_mstate.py
```

---

### Task 12: writers-sync, TREND DAY / ROTATION, COIL → ESCAPE

**Files:**
- Modify: `mstate.py` (imports, constants, `_I`, `IDXS`, `_prem`, the `prem` row key; append `_at` and `cross`)
- Modify: `server.py` (`_jarvis_reply` attaches `xstate`; add `_jarvis_cross`)
- Modify: `jarvis_log.py` (`card` passes `xstate`)
- Modify: `docs/kahani/review/mockup/jarvis2.html` (the ALERT / cross row)
- Test: `test_mstate.py`, `test_jarvis_state.py` (append)
- Modify: `jarvis_thresholds.json`, `docs/live/NOTEPAD.md` (A258)

**Interfaces:**
- Consumes:
  - Each frame's `mstate` (`dir`, `vol.word`, `prem`), `timeline[*].fronts`, `wf_ce`, `wf_pe`, `mins`, `day`, `ok`.
  - `jarvis.wf_push`, `jarvis.WF_L`, `jarvis.BLIND_MIN`, `handshake.TICK`.
  - `server._JARVIS[idx] = (key, built_at, frame)`.
- Produces:
  - `mstate.IDXS = ("NIFTY", "SENSEX", "BANKNIFTY")`.
  - `mstate._prem(d, i, chain) -> {"ce": float|None, "pe": float|None}`; rows gain `"prem"`.
  - `mstate.cross(frames, t, day=None) -> {"t", "sync": {"dir", "n", "of", "text"}|None, "day": str|None, "alert": str|None, "why": [str]}`.
  - `server._jarvis_cross(idx, out) -> dict`; `call()["xstate"]` on live frames; the card's `"xstate"`.
  - The cross read is a chip and a line beside the word, never the word (see the self-review).

- [ ] **Step 1: Write the failing tests**

Append to `test_mstate.py`:

```python
# ---- Task 12: the cross-index read -------------------------------------------------------------------------------------

def test_prem_reads_the_premium_beyond_delta():
    d = _frame([24000.0] * 10)
    chain = {"09:16": {"spot": 23990.0, "ce": {24000: {"ltp": 100.0, "delta": 0.5}}, "pe": {24000: {"ltp": 110.0, "delta": -0.5}}},
             "09:19": {"spot": 24010.0, "ce": {24000: {"ltp": 112.0, "delta": 0.55}}, "pe": {24000: {"ltp": 99.0, "delta": -0.45}}}}
    assert mstate._prem(d, d["mins"].index("09:19"), chain) == {"ce": 2.0, "pe": -1.0}
    assert mstate._prem(d, d["mins"].index("09:18"), chain) == {"ce": None, "pe": None}


def _xf(idx, d=1, unwind=None, wf=(None, None), vol="NORMAL", prem=None):
    mins = [_hm(600 + i) for i in range(10)]
    fr = [{"k": 24000.0, "side": unwind, "state": "UNWINDING"}] if unwind else []
    return {"ok": True, "idx": idx, "mins": mins, "timeline": [{"fronts": fr} for _ in mins],
            "wf_ce": [wf[0]] * 10, "wf_pe": [wf[1]] * 10,
            "mstate": [{"t": m, "word": "TREND ▲" if d > 0 else "RANGE", "dir": d, "vol": {"word": vol},
                        "prem": prem or {"ce": None, "pe": None}} for m in mins]}


def test_trend_day_rotation_and_could_not_check():
    x = mstate.cross({n: _xf(n, unwind="CE") for n in mstate.IDXS}, "10:09")
    assert x["sync"]["dir"] == 1 and x["sync"]["n"] == 3 and x["day"].startswith("TREND DAY ▲")
    x = mstate.cross({"NIFTY": _xf("NIFTY"), "SENSEX": _xf("SENSEX", 0), "BANKNIFTY": _xf("BANKNIFTY", 0)}, "10:09")
    assert x["day"].startswith("ROTATION: NIFTY ▲ alone") and x["sync"] is None
    x = mstate.cross({"NIFTY": _xf("NIFTY")}, "10:09")
    assert x["day"] is None and x["why"] == ["SENSEX: could not check — no frame at 10:09",
                                             "BANKNIFTY: could not check — no frame at 10:09"]
    assert mstate.cross({n: dict(_xf(n), day="2026-11-04") for n in mstate.IDXS}, "10:09", "2026-11-05")["why"][0] \
        == "NIFTY: could not check — no frame at 10:09"                           # another day's frame is never a peer


def test_coil_then_escape_is_a_display_only_warning():
    coil = {n: _xf(n, 0, wf=(12.0, 11.0), vol="CONTRACTING") for n in mstate.IDXS}
    assert mstate.cross(coil, "10:09")["alert"] is None                         # a coil alone says nothing
    esc = dict(coil, NIFTY=_xf("NIFTY", 0, wf=(-12.0, 0.0), vol="CONTRACTING", prem={"ce": 0.4, "pe": None}),
               SENSEX=_xf("SENSEX", 0, wf=(-15.0, 1.0), vol="CONTRACTING"))
    for n in ("NIFTY", "SENSEX"):                                               # the coil was 8-10 min ago
        esc[n]["wf_ce"][:3], esc[n]["wf_pe"][:3] = [12.0] * 3, [11.0] * 3
    a = mstate.cross(esc, "10:09")["alert"]
    assert a.startswith("box ban gaya, writers bhaag rahe — bada move ho sakta hai ▲")
    assert "premium bid beyond delta: NIFTY" in a and "never a prediction" in a and "%" not in a
```

Append to `test_jarvis_state.py`:

```python
def test_a_live_frame_carries_the_cross_read_of_its_cached_peers(monkeypatch):
    from test_jarvis_log import CALL, _srv, frame
    server, clock = _srv(monkeypatch, (2026, 11, 2, 10, 42, 25))

    def fake(day, idx, upto, fill=False):
        ms = [f"{m // 60:02d}:{m % 60:02d}" for m in range(640, upto)]
        return dict(frame(), day=day, idx=idx, mins=ms, call=dict(CALL, at=ms[-1]), mstate=[_srow(m) for m in ms],
                    timeline=[{"fronts": []} for _ in ms], wf_ce=[None] * len(ms), wf_pe=[None] * len(ms))
    monkeypatch.setattr(jarvis, "build", fake)
    out = server._jarvis_reply({"idx": ["NIFTY"]})
    assert out["call"]["xstate"]["why"] == ["SENSEX: could not check — no frame at 10:41",
                                            "BANKNIFTY: could not check — no frame at 10:41"]
    server._jarvis_reply({"idx": ["SENSEX"]})
    out = server._jarvis_reply({"idx": ["BANKNIFTY"]})
    assert out["call"]["xstate"]["why"] == [] and out["call"]["xstate"]["day"] is None   # all ▲, no front covering
    assert server._jarvis_card("BANKNIFTY")["xstate"]["t"] == "10:41"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest -q test_mstate.py test_jarvis_state.py -k "prem or trend_day or coil or cross_read"`
Expected: FAIL with `AttributeError: module 'mstate' has no attribute '_prem'` and `KeyError: 'xstate'`.

- [ ] **Step 3: Implement in `mstate.py`**

Replace `import datetime` with:

```python
import bisect
import datetime
```

After `ARR = {1: "▲", -1: "▼"}`, add:

```python
IDXS = ("NIFTY", "SENSEX", "BANKNIFTY")
```

After the `SYNC_WIN = 30 ...` line, add:

```python
SYNC_MIN = 5                  # [I] writers-sync / running: within the last 5 min (spec §4)
SYNC_N = 2                    # [I] ... in >= 2 of the 3 indices (spec §4)
COIL_MIN = 30                 # [I] COIL -> ESCAPE: a coil (CONTRACTING with both sides adding) within the last 30 min
```

Replace the `_I = (...)` lines with:

```python
_I = ("EFF_WIN", "EFF_RANGE", "VWAP_X", "NORM_N", "NORM_MIN", "RANGE_HI", "RANGE_LO", "GAUGE_WIN", "VIX_PTS", "IV_PTS",
      "VOL_N", "VOL_CLOSES", "OPEN_LEGAL", "FADE_SIGNS", "MATURE_PUSHES", "SYNC_WIN", "SYNC_MIN", "SYNC_N", "COIL_MIN")
```

Insert before `def chip(row):`:

```python
def _prem(d, i, chain):
    """The ATM premium vs delta over the last 3 min per side -> {"ce", "pe"}: rupees beyond what delta explains
    (handshake.who_opened's read, M4), None when a minute's ATM leg is missing. COIL -> ESCAPE's who (spec §4 guard:
    who opened the move is read on premium vs delta, never on "OI up = writers")."""
    t = d["mins"][i]
    t3, step, out = _hm(_m(t) - 3), d.get("step") or 50, {"ce": None, "pe": None}
    a, b = (chain or {}).get(t3), (chain or {}).get(t)
    if not a or not b:
        return out
    k = round(a["spot"] / step) * step
    for s in out:
        x, y = legs._chain_leg(chain, t3, s, k)[0], legs._chain_leg(chain, t, s, k)[0]
        if x and y and x.get("delta") is not None and y.get("ltp") is not None:
            out[s] = round((y["ltp"] - x["ltp"]) - x["delta"] * (b["spot"] - a["spot"]), 2)
    return out
```

In `fold`, replace `"eff": eff, "vx": vx, "price": what, "vol": vol, "expiry": exp})` with `"eff": eff, "vx": vx, "price": what, "vol": vol, "expiry": exp, "prem": _prem(d, i, chain)})`.

Append to the end of `mstate.py`:

```python
# ---- the cross-index read (spec §3 tiebreak, §4 writers-sync and COIL -> ESCAPE) ---------------------------------------

def _at(fr, t, stale):
    ms = fr.get("mins") or []
    j = bisect.bisect_right(ms, t) - 1
    return None if j < 0 or _m(t) - _m(ms[j]) > stale else j


def cross(frames, t, day=None):
    """The cross-index read at minute t from the three indices' frames ({idx: a jarvis.build frame with `mstate`}) ->
    {"t", "sync", "day", "alert", "why"}. sync: a side's top front UNWINDING (§1d) in >= SYNC_N indices within SYNC_MIN
    min (call writers covering = ▲). day: TREND DAY (all three in one trend, that side covering in all three) or
    ROTATION (one index trending, the other two not). alert: COIL -> ESCAPE (spec §4) -- a coil (CONTRACTING with both
    sides adding) within COIL_MIN min in any index, then one side's writers running (jarvis.wf_push) in >= SYNC_N within
    SYNC_MIN min; who opened it is read on premium vs delta (_prem). Display only: a chip and a line beside each index's
    own word, never its word, never a gate. A peer missing, of another day or stale (jarvis.BLIND_MIN) -> could not
    check, named."""
    import handshake
    import jarvis
    at, why = {}, []
    for n in IDXS:
        fr = frames.get(n) or {}
        ok = fr.get("ok") and fr.get("mstate") and (day is None or fr.get("day") == day)
        j = _at(fr, t, jarvis.BLIND_MIN) if ok else None
        if j is None:
            why.append(f"{n}: could not check — no frame at {t}")
        else:
            at[n] = (fr, j)

    def back(fr, j, win):
        return [x for x in range(j, -1, -1) if _m(t) - _m(fr["mins"][x]) < win]

    cover = {"CE": [], "PE": []}
    for n, (fr, j) in at.items():
        for side in cover:
            hit = next((fr["mins"][x] for x in back(fr, j, SYNC_MIN) if (fronts.side_front(
                (fr["timeline"][x] or {}).get("fronts"), side) or {}).get("state") == fronts.UNWINDING), None)
            if hit:
                cover[side].append((n, hit))
    sync = None
    for side, D, other in (("CE", 1, "PE"), ("PE", -1, "CE")):
        if len(cover[side]) >= SYNC_N and len(cover[side]) > len(cover[other]):
            sync = {"dir": D, "n": len(cover[side]), "of": len(at),
                    "text": f"{'call' if D > 0 else 'put'} writers covering in {len(cover[side])} of {len(at)}: "
                            + ", ".join(f"{n} {m}" for n, m in cover[side])}
    dirs = {n: fr["mstate"][j]["dir"] for n, (fr, j) in at.items()}
    dayw = None
    if len(at) == 3 and len(set(dirs.values())) == 1 and 0 not in dirs.values() and sync and sync["n"] == 3 \
            and sync["dir"] == next(iter(dirs.values())):
        D = sync["dir"]
        dayw = f"TREND DAY {ARR[D]}: all 3 trending, {'call' if D > 0 else 'put'} writers covering in all 3"
    elif len(at) == 3 and sum(1 for v in dirs.values() if v) == 1:
        n = next(n for n, v in dirs.items() if v)
        dayw = f"ROTATION: {n} {ARR[dirs[n]]} alone, the other two don't follow — fade the extremes"

    def both_add(fr, x):
        ce, pe = fr["wf_ce"][x], fr["wf_pe"][x]
        return ce is not None and pe is not None and ce >= jarvis.WF_L and pe >= jarvis.WF_L
    coiled = [n for n, (fr, j) in at.items() if any(((fr["mstate"][x].get("vol") or {}).get("word") == "CONTRACTING"
                                                      and both_add(fr, x)) for x in back(fr, j, COIL_MIN))]
    run = {1: [], -1: []}
    for n, (fr, j) in at.items():
        for x in back(fr, j, SYNC_MIN):
            ce, pe = fr["wf_ce"][x], fr["wf_pe"][x]
            p = jarvis.wf_push(ce, pe) if ce is not None and pe is not None else None
            if p:
                run[p].append((n, x))
                break
    alert = None
    for D in (1, -1):
        if coiled and len(run[D]) >= SYNC_N:
            s = "ce" if D > 0 else "pe"
            bid = [n for n, x in run[D] if ((at[n][0]["mstate"][x].get("prem") or {}).get(s) or 0) > 2 * handshake.TICK]
            alert = (f"box ban gaya, writers bhaag rahe — bada move ho sakta hai {ARR[D]} (coil: {', '.join(coiled)} · "
                     f"{'call' if D > 0 else 'put'} writers running: {', '.join(n for n, _ in run[D])} · premium bid "
                     f"beyond delta: {', '.join(bid) or 'none'}) · display only, never a prediction: a coil blasted in "
                     "6 of 24 legs (27 Oct coil study)")
    return {"t": t, "sync": sync, "day": dayw, "alert": alert, "why": why}
```

- [ ] **Step 4: Attach it to live frames in `server.py`; pass it on the card; show it on the face**

In `_jarvis_reply`, replace:

```python
        if not live and out.get("ok"):
            out["calls"] = jarvis.calls(out)
```

with:

```python
        if not live and out.get("ok"):
            out["calls"] = jarvis.calls(out)
        if live and out.get("ok") and out.get("mins"):
            out["call"]["xstate"] = _jarvis_cross(idx, out)   # spec §3-4: beside the word, never the word
```

After `_jarvis_reply`, add:

```python
def _jarvis_cross(idx, out):
    """THE CROSS-INDEX READ (mstate.cross) on this live frame and the other indices' cached live frames: writers-sync,
    TREND DAY / ROTATION, COIL -> ESCAPE. A replay builds one index, so it has none (its card says nothing of it).
    Fail-soft: a failure is its own could-not-check line."""
    import mstate
    try:
        peers = {i: (_JARVIS.get(i) or (None, 0.0, None))[2] for i in mstate.IDXS if i != idx}
        return mstate.cross(dict(peers, **{idx: out}), out["mins"][-1], out.get("day"))
    except Exception as e:
        log.exception("jarvis cross")
        return {"t": out["mins"][-1], "sync": None, "day": None, "alert": None,
                "why": [f"could not check — the cross-index read failed: {type(e).__name__}"]}
```

In `jarvis_log.card`, replace `"zone": c.get("zone")}` with `"zone": c.get("zone"), "xstate": c.get("xstate")}`.

In `jarvis2.html`'s `renderCard`, directly after the `if (Z) { ... }` block of Task 9, insert:

```js
  const X = c.xstate;                                 // THE CROSS-INDEX read (spec §3-4): a line beside the word, never it
  if (X && (X.day || X.alert || X.sync)) row("s clip" + (X.alert ? " bad" : ""),
    [X.alert && "ALERT " + X.alert, X.day, X.sync && X.sync.text].filter(Boolean).join(" · "), (X.why || []).join("\n"));
```

- [ ] **Step 5: Thresholds and NOTEPAD**

In `jarvis_thresholds.json`, replace ` "mstate.SYNC_WIN": 30,` with:

```json
 "mstate.SYNC_WIN": 30,
 "mstate.SYNC_MIN": 5,
 "mstate.SYNC_N": 2,
 "mstate.COIL_MIN": 30,
```

Replace `  "mstate.SYNC_WIN": "sign 4, sync broke: a fresh 30-min extreme here and none in the two peers"` with:

```json
  "mstate.SYNC_WIN": "sign 4, sync broke: a fresh 30-min extreme here and none in the two peers",
  "mstate.SYNC_MIN": "writers-sync and writers running: within the last 5 min (spec §4, A258)",
  "mstate.SYNC_N": "... in >= 2 of the 3 indices",
  "mstate.COIL_MIN": "COIL -> ESCAPE: a coil (CONTRACTING with both sides adding) within the last 30 min"
```

In `docs/live/NOTEPAD.md`, insert after the A257 row:

```markdown
| A258 | 6 Nov (spec 2026-11-06 §3-4 / §7, plan phase 3) | **Cross-index was price only: `all3`'s N slot read the frame's own future (SENSEX's on a SENSEX frame), no writers-sync, no coil warning, no 0 DTE state, and BANKNIFTY had no rows.** | 5 Nov call log [M]: NIFTY 344 rows, SENSEX 336, BANKNIFTY 0 (`server.JARVIS_PASS_IDX` held NIFTY and SENSEX only) | `mstate.cross` per live frame from the cached peers: writers-sync (a side's front UNWINDING in ≥2 of 3 within 5 min), TREND DAY / ROTATION as a chip beside the word (never the word: a replay builds one index), COIL → ESCAPE as a display-only line (who opened it read on premium vs delta); ALL 3's N slot reads NIFTY on every frame; 0 DTE says "EXPIRY: gamma both ways" from 14:00; BANKNIFTY joins the pass. [I]: `mstate.SYNC_MIN` 5 min, `SYNC_N` 2 of 3, `COIL_MIN` 30 min | BUILDING (phase 3) |
```

- [ ] **Step 6: Run the tests**

Run: `python -m pytest -q test_mstate.py test_jarvis_state.py test_jarvis_log.py test_thresholds.py`
Expected: PASS.

- [ ] **Step 7: Stage**

```bash
git add mstate.py server.py jarvis_log.py docs/kahani/review/mockup/jarvis2.html test_mstate.py test_jarvis_state.py jarvis_thresholds.json
git add -p docs/live/NOTEPAD.md
```

---

### Task 13: BANKNIFTY gets rows

**Root cause:**
- `server.JARVIS_PASS_IDX = ("NIFTY", "SENSEX")` (`server.py:4794`, "BANKNIFTY builds on a face's demand"). The Jarvis page's picker (`jarvis2.html:235`) offers only NIFTY and SENSEX, so no face ever demanded BANKNIFTY, and its call log stayed empty.
- `jarvis.days()` (`:1437`) also lists only NIFTY and SENSEX.
- `jarvis.CACHE_KEEP = 4` is already sized for three live indices plus one replay.

**Files:**
- Modify: `server.py:4794`, `jarvis.py:1437`, `docs/kahani/review/mockup/jarvis2.html:235`
- Modify: `test_jarvis_log.py:210-285` (the pass test)
- Test: `test_jarvis_state.py` (append)

**Interfaces:**
- Produces:
  - `server.JARVIS_PASS_IDX == ("NIFTY", "SENSEX", "BANKNIFTY")`.
  - `jarvis.days()` keys NIFTY, SENSEX and BANKNIFTY.
  - The face's picker offers BANKNIFTY.

- [ ] **Step 1: Write the failing test** (append to `test_jarvis_state.py`)

```python
def test_banknifty_is_kept_live_and_on_the_replay_calendar(tmp_path, monkeypatch):
    import pathlib
    import book_log
    import chain_live
    import server
    assert "BANKNIFTY" in server.JARVIS_PASS_IDX
    monkeypatch.setattr(book_log, "DIR", str(tmp_path))
    monkeypatch.setattr(chain_live, "CHAIN_DIR", pathlib.Path(tmp_path))
    for f in ("book_BANKNIFTY_2026-11-05.jsonl", "chain_BANKNIFTY_2026-11-05.jsonl"):
        (tmp_path / f).write_text("{}\n", encoding="utf-8")
    assert jarvis.days()["BANKNIFTY"] == ["2026-11-05"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest -q test_jarvis_state.py::test_banknifty_is_kept_live_and_on_the_replay_calendar`
Expected: FAIL on `assert "BANKNIFTY" in server.JARVIS_PASS_IDX`.

- [ ] **Step 3: Implement**

In `server.py:4794`, replace:

```python
JARVIS_PASS_IDX = ("NIFTY", "SENSEX")            # the pass keeps these live; BANKNIFTY builds on a face's demand
```

with:

```python
JARVIS_PASS_IDX = ("NIFTY", "SENSEX", "BANKNIFTY")   # the pass keeps all three live (spec 2026-11-06 §7: BANKNIFTY gets
                                                     # rows; on 5 Nov it had none, no face asked for it); a pass over
                                                     # JARVIS_SLOW_S still says so on the card
```

In `jarvis.days()`, replace `for i in ("NIFTY", "SENSEX")}` with `for i in ("NIFTY", "SENSEX", "BANKNIFTY")}`.

In `jarvis2.html:235`, replace `<select id="pIdx"><option>NIFTY</option><option>SENSEX</option></select>` with `<select id="pIdx"><option>NIFTY</option><option>SENSEX</option><option>BANKNIFTY</option></select>`.

In `test_jarvis_log.py`, `test_the_jarvis_pass_keeps_nifty_and_sensex_live_without_any_face`:

- rename it `test_the_jarvis_pass_keeps_all_three_live_without_any_face`;
- in its docstring, replace `for NIFTY and SENSEX (BANKNIFTY on demand)` with `for NIFTY, SENSEX and BANKNIFTY`;
- `assert built == [("NIFTY", 642), ("SENSEX", 642)]                                     # never BANKNIFTY` → `assert built == [("NIFTY", 642), ("SENSEX", 642), ("BANKNIFTY", 642)]`
- `assert len(built) == 2` → `assert len(built) == 3`
- `assert built[2:] == [("SENSEX", 644)]` → `assert built[3:] == [("SENSEX", 644), ("BANKNIFTY", 644)]`
- `assert len(built) == 3                                                                # never stacked behind a build` → `assert len(built) == 5                                                                # never stacked behind a build`
- `assert built[3:] == [("NIFTY", 645), ("SENSEX", 645)]` → `assert built[5:] == [("NIFTY", 645), ("SENSEX", 645), ("BANKNIFTY", 645)]`
- `assert len(built) == 5` (after the close) → `assert len(built) == 8`

- [ ] **Step 4: Run the tests**

Run: `python -m pytest -q test_jarvis_state.py test_jarvis_log.py`
Expected: PASS.

- [ ] **Step 5: Stage**

```bash
git add server.py jarvis.py docs/kahani/review/mockup/jarvis2.html test_jarvis_state.py
git add -p test_jarvis_log.py
```

---

### Task 14: the replay behaviour check, 28 Oct–5 Nov (phase 3 ends)

**Files:**
- Create: `tools/mstate_replay.py`
- Create: `test_mstate_replay.py`
- Modify: `docs/live/NOTEPAD.md` (A258 status; section B, the counts)

**Interfaces:**
- Consumes: `jarvis.build(day, idx)` (fill off: what live saw), `jarvis.days()`, `jarvis.said`, `mstate.cross`, `mstate.IDXS`, `fold.IST`.
- Produces:
  - `mstate_replay.refused(now=None) -> bool` and `mstate_replay.changes(xs) -> int`.
  - `mstate_replay.measure(day) -> (rows, frames, cross_row)`.
  - `mstate_replay.checks(frames) -> [(check, observed)]`.
  - `mstate_replay.main(argv) -> int`.

- [ ] **Step 1: Write the failing tests**

Create `test_mstate_replay.py`:

```python
"""tools/mstate_replay.py -- the market state's behaviour check (spec 2026-11-06 §9): refused in market hours, counts and
observed words only."""
import datetime
import os
import sys

import fold

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import mstate_replay  # noqa: E402


def test_the_replay_refuses_market_hours_and_counts_changes():
    assert mstate_replay.refused(datetime.datetime(2026, 11, 6, 10, 0, tzinfo=fold.IST))        # a Friday, 10:00
    assert not mstate_replay.refused(datetime.datetime(2026, 11, 6, 15, 45, tzinfo=fold.IST))
    assert not mstate_replay.refused(datetime.datetime(2026, 11, 7, 10, 0, tzinfo=fold.IST))    # a Saturday
    assert mstate_replay.changes(["A", "A", "B", "A"]) == 2


def test_the_checks_say_what_the_engine_said_and_never_a_rate():
    fr = {"NIFTY": {"mstate": [{"t": "09:40", "word": "TREND ▲ (leg, unconfirmed)"}],
                    "zone_cards": [{"t": "12:30", "verdict": "SKIP", "why": "TREND ▲ + EXPANDING: a fade only if the band stopped expanding and the writers at it hold · band still expanding or writers at it leaving"}]}}
    got = dict(mstate_replay.checks(fr))
    assert got["09:36–10:00 NIFTY word"] == "TREND ▲ (leg, unconfirmed)"
    assert got["12:30 NIFTY u2 sell"] == ("SKIP — TREND ▲ + EXPANDING: a fade only if the band stopped expanding and the writers at it hold"
                                            " · band still expanding or writers at it leaving")
    assert got["09:36–10:00 SENSEX word"] == "not built" and got["13:51 NIFTY sell"].startswith("no card")
    assert "%" not in str(got)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest -q test_mstate_replay.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'mstate_replay'`.

- [ ] **Step 3: Write `tools/mstate_replay.py`**

```python
"""tools/mstate_replay.py -- the market state's behaviour check (spec 2026-11-06 §9), on the record, never in market hours.

    python tools/mstate_replay.py 2026-10-28 2026-11-05                     # every recorded day between, all 3 indices
    python tools/mstate_replay.py 2026-11-05 2026-11-05 --json C:\\tmp\\x.json # the rows as JSON too (its own path)

Per day and index: jarvis.build(day, idx) as live saw it (fill off), then COUNTS -- the state word's changes, the
ACTION word's changes (the old word, beside it), the zone cards by verdict and how many were logged late -- and per day,
when all three indices built, the cross-index read at every NIFTY minute (TREND DAY / ROTATION minutes, COIL -> ESCAPE
onsets). For 5 Nov it prints spec §9's table as OBSERVED: no row is asserted, no target is set, no threshold is tuned on
it (spec §11). Never a rate, never an outcome: no mfe / mae / stop_hit is read. Refused 09:15-15:40 IST on a weekday.
Read-only: nothing under data/ is written (only --json's own path)."""
import argparse
import datetime
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

VERDICTS = ("STRONG", "TAKE", "TAKE · smaller target", "SKIP")


def refused(now=None):
    """True in market hours (weekday 09:15-15:40 IST): a replay never runs beside the live server's builds."""
    import fold
    now = now or datetime.datetime.now(fold.IST)
    return now.weekday() < 5 and "09:15" <= now.strftime("%H:%M") < "15:40"


def changes(xs):
    return sum(1 for a, b in zip(xs, xs[1:]) if a != b)


def measure(day):
    """-> (one row per index, the frames built, the day's cross row)."""
    import jarvis
    import mstate
    rows, fr = [], {}
    for idx in mstate.IDXS:
        d = jarvis.build(day, idx)
        if not d.get("ok"):
            rows.append({"day": day, "idx": idx, "why": d.get("why")})
            continue
        fr[idx] = d
        acts = [jarvis.said(a["word"], a["lean"]) for a in (d.get("reads") or {}).get("action") or ()]
        cards = d.get("zone_cards") or []
        rows.append({"day": day, "idx": idx, "minutes": len(d["mins"]),
                     "state_changes": changes([r["word"] for r in d.get("mstate") or ()]),
                     "action_changes": changes(acts),
                     "cards": {v: sum(c["verdict"] == v for c in cards) for v in VERDICTS},
                     "late_cards": sum(bool(c["late"]) for c in cards),
                     "failed": [x for x in d["health"]["notes"] if "market state failed" in x]})
    x = {"day": day, "trend_day_min": None, "rotation_min": None, "alerts": None}
    if len(fr) == 3:
        xs = [mstate.cross(fr, t, day) for t in fr["NIFTY"]["mins"]]
        x.update(trend_day_min=sum(bool(a["day"] and a["day"].startswith("TREND DAY")) for a in xs),
                 rotation_min=sum(bool(a["day"] and a["day"].startswith("ROTATION")) for a in xs),
                 alerts=sum(1 for a, b in zip([None] + xs, xs) if b["alert"] and not (a and a["alert"])))
    return rows, fr, x


def checks(fr):
    """Spec §9's 5 Nov table as observed -> [(check, what the engine said)]."""
    def words(idx, a, b):
        d = fr.get(idx)
        return " / ".join(sorted({r["word"] for r in d.get("mstate") or () if a <= r["t"] <= b})) if d else "not built"

    def card(idx, t):
        c = next((c for c in (fr.get(idx) or {}).get("zone_cards") or () if c["t"] == t), None)
        return f"{c['verdict']} — {c['why']}" if c else "no card (no trigger at that time on the record)"
    return [("09:36–10:00 NIFTY word", words("NIFTY", "09:36", "10:00")),
            ("09:36–10:00 SENSEX word", words("SENSEX", "09:36", "10:00")),
            ("12:30 NIFTY u2 sell", card("NIFTY", "12:30")),
            ("13:51 NIFTY sell", card("NIFTY", "13:51")),
            ("14:09 NIFTY sell", card("NIFTY", "14:09")),
            ("10:55 SENSEX d2", card("SENSEX", "10:55")),
            ("14:24 SENSEX word", words("SENSEX", "14:24", "14:24"))]


def main(argv=None):
    ap = argparse.ArgumentParser(description="the market state's behaviour check (spec §9)")
    ap.add_argument("start")
    ap.add_argument("end")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    if refused():
        print("refused: a replay never runs 09:15-15:40 IST on a weekday (spec §9)")
        return 2
    os.chdir(ROOT)
    import jarvis
    out = []
    for day in [x for x in jarvis.days()["NIFTY"] if a.start <= x <= a.end]:
        rows, fr, x = measure(day)
        out.append({"rows": rows, "cross": x, "checks": checks(fr) if day == "2026-11-05" else None})
        for r in rows:
            print(r["day"], r["idx"], r["why"] if "why" in r else
                  f"{r['minutes']} min · state changes {r['state_changes']} · ACTION changes {r['action_changes']} · "
                  "cards " + " / ".join(f"{k} {v}" for k, v in r["cards"].items()) + f" · late {r['late_cards']}"
                  + (f" · FAILED {r['failed']}" if r["failed"] else ""))
        print(day, "cross:", "could not check — fewer than 3 indices built" if x["trend_day_min"] is None else
              f"TREND DAY {x['trend_day_min']} min · ROTATION {x['rotation_min']} min · COIL → ESCAPE {x['alerts']}×")
        for k, v in out[-1]["checks"] or ():
            print("   ", k, "→", v)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest -q test_mstate_replay.py`
Expected: PASS.

- [ ] **Step 5: Run the replay (after 15:40 IST or at a weekend; it refuses otherwise)**

Run: `python tools/mstate_replay.py 2026-10-28 2026-11-05`
Expected:
- One line per recorded day and index with counts.
- One cross line per day.
- The 5 Nov table (seven rows).
- No `FAILED`.
- No `%` anywhere.

The 6 Nov scratch prototype read 5 Nov as follows (the replay's numbers are the ones to record):
- the state word changed NIFTY 4×, SENSEX 7× and BANKNIFTY 9×, against ACTION 19× and 17× for NIFTY and SENSEX;
- the open drive was spoken at 09:46 (NIFTY) and 09:43 (SENSEX);
- the 12:30 NIFTY sell read SKIP;
- the 10:55 SENSEX d2 read TAKE (RANGE), not STRONG.

Do not change any threshold on these.

- [ ] **Step 6: Record the counts and mark A258 built**

In `docs/live/NOTEPAD.md`, section B, add a heading `### 2026-11-06 (Friday): the market state replayed on 28 Oct–5 Nov (behaviour check, spec §9)`. Under it:
- one bullet per day with each index's `state changes N · ACTION changes M`, as printed;
- one bullet with the seven 5 Nov rows, verbatim as printed;
- the line: "Counts only; no target was set in advance; no threshold moved on them (spec §11). Her read, in the evening."

In the A258 row, replace `| BUILDING (phase 3) |` with `| BUILT, uncommitted — phase 3 commit on her word; replay counts in section B, 6 Nov |`.

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS, with the known flaky A49 aside.

- [ ] **Step 8: Commit phase 3 (only after Mary says commit; never push)**

```bash
git add tools/mstate_replay.py test_mstate_replay.py
git add -p docs/live/NOTEPAD.md
git commit -m "Jarvis market state, phase 3: writers-sync, TREND DAY / ROTATION, COIL -> ESCAPE, the ALL 3 N-slot fix, 0 DTE, BANKNIFTY rows; the 28 Oct-5 Nov replay counts (A258)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Mary restarts the server herself (`.\stop.bat; .\start-v2.bat`) to make it live. The new state log starts at `data/jarvis/state_<day>.jsonl`.

---

## Phase 4 — the gate reads the wall at the band (spec §6, §10.4)

> **BLOCKED — needs Mary's signature as a new registration; do not build.**

- **What it would change:**
  - Her §1d fade gate (`trigger_log` zone3 `gate {legal, why}`, written by the zone machine) cites the trend-side front for the rest of the day.
  - On 5 Nov that was "CE 24500 gave up 11:17", and it blocked all five top-band sells (+64 to +185 pts to the pullback [M]).
  - Phase 4 would make the gate read the writers AT the band's strike: the zone card's sign 2, `mstate.signs(...)["wall"]`.
- **Why it is blocked:** this changes how a registered rule is applied (§1b–§1s are never changed; a change is a new registration, CLAUDE.md). Spec §6 says so in its own words.
- **What already ships (phase 2):** the card shows both reads side by side. One is the gate as logged (`gate §1d: NOT legal — CE 24500 gave up ...`); the other is the at-band read (`at band: 24,600s CE +3.1L / 9 min (holding / adding)`).
- **To unblock:**
  1. Mary writes and signs the amendment text in `context/research-findings.md` (a new §, with its sha256 anchor).
  2. A separate plan names the exact gate function in the zone machine and its forward log.
  3. Nothing in this plan touches the gate.

---

## Self-Review

**1. Spec coverage**

| Spec | Task |
|---|---|
| §2 four layers; the state word leads; zone triggers never vote | 1, 2, 3, 4, 6 |
| §3 swings on 3-min closes, decode sizing, reuse reader.py; TREND start / end rules; nothing else ends a trend | 1 |
| §3 pieces only grade healthy / tired / blind | 4 (`_grade`) |
| §3 efficiency beside the state; RANGE assist | 1 |
| §3 cross-index tiebreak (TREND DAY / ROTATION) | 12 (as a chip — see the deviation below) |
| §3 unconfirmed trend | 1 |
| §4 five gauges, 2 of them at 2 closes | 2 |
| §4 writers-sync + `all3` fix | 12, 10 |
| §4 COIL → ESCAPE with the guard | 12 |
| §4 0 DTE mode | 11 (+ 8's 15:00 legality) |
| §5 legality table | 8 |
| §6 signs count, STRONG / TAKE · smaller target / SKIP, stop and target | 8, 9 |
| §6 gate and at-band read side by side | 9 |
| §7 the screen (light, terminal, Hinglish chips, WATCH / PALAT? as chips, "fuel blind") | 6, 9, 12 |
| §7 BANKNIFTY rows | 13 |
| §8 rules kept | Global Constraints |
| §8 anytime-start, backfill tags | 4 (fold from 09:15 every build), 5 (state log `src`) |
| §9 replay + the forward log `state_<day>.jsonl` | 14, 5 |
| §10.4 gate | Phase 4 stub (BLOCKED) |

Deliberate deviations, each named where it is built:

- **Cross-index tiebreak.** TREND DAY / ROTATION is a chip and a line beside the word, not a rewrite of it. A replay builds one index, so a word moved by its peers would read differently live and replayed. If Mary wants it to decide the word, that is a follow-up.
- **Sign 3 at the d-band.** It is "not read": effort's ≥2× mirror failed at lows. "CVD stalled" is not used (CVD divergence at highs is inverted, oi-lab).
- **The straddle gauge.** It has no theta: the chain record carries ltp / oi / iv / delta / gamma, no theta [M]. A rise counts as expansion (decay only lowers it); a fall counts as contraction only while spot sat within half a step.
- **NORMAL volatility.** The legality table names only EXPANDING and CONTRACTING, so NORMAL reads as not expanding (a trader's call, noted in A257).

**2. Placeholder scan.** Every step that changes code shows the code, and every run step names its command and expected result. NOTEPAD row texts are given in full. The replay's section-B bullets are filled from the tool's own printed output; that is a transcription, not an invention.

**3. Type consistency**

- `fold(d, chain=None, nm=None) -> (rows, pivots)` everywhere after Task 2 (Task 1 introduces `fold(d)`; Task 2 replaces it).
- `gauges(d, i, chain=None, nm=None)`, `legal(row, vword, side, t, dte=None)`, `signs(d, i, z, piv)`, `card(d, z, rows, piv, dte=None)`, `cards(d, rows, piv)`, `card_line(c)`, `_prem(d, i, chain)` and `cross(frames, t, day=None)` match their tests and their callers (`_build`, `_jarvis_cross`, `mstate_replay`).
- Row keys:
  - `vol` from Task 2, `expiry` from Task 11, `prem` from Task 12;
  - `call()["mstate"]` copies `expiry` with `.get` (None before Task 11);
  - `cross` reads `prem` with `.get` (absent before Task 12 is impossible, since cross ships in Task 12).
- `jarvis_log.write(..., kind=)`, `read(..., kind=)` and `state_row(fr, j, now, src)` match Task 5's tests and `server._jarvis_log`.
- `call()` keys `action` / `mstate` / `chips` / `zone` match `jarvis_log.card` and `jarvis2.html`.
- `xstate` is set by the server and passed by `card`.
