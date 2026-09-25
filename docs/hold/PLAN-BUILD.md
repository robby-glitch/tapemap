# THE PLAN (stop · next rung · room): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the signed PLAN (STOP · NEXT RUNG · ROOM, the rung's word at a touch, and the two exits side by side) inside the existing hold window. Log it forward, write-once.

**Architecture:**
- A new pure module `plan.py` reads the window's own rows (`hold.read`) and the same per-minute records. It never changes `hold.py`.
- `server.py` adds three things to what it already builds: the top-2 fronts per minute (`rec["fr"]`), the broker's greeks per minute (captured in the same pass that reads the running peak), and a `plan` key on `/api/hold` and on the log rows. Touches get their own write-once `rung_touch` rows.
- `HoldWindow.tsx` prints three more lines.

**Tech Stack:** Python 3.13 stdlib, pytest; React 19 / TypeScript (ui-v2, Vite).

## Global Constraints

- **The spec is `docs/hold/PLAN-PREREG.md` rev 2a,** sha256 `a0295c202697679f14fd59aa157813bdbf74cc0f8b1fbff6da17cea5a1e7158b`, anchored in `context/research-findings.md` §1f.
  - Check the hash first: `sha256sum docs/hold/PLAN-PREREG.md`.
  - If it differs, STOP. The spec changed after signing.
- **No rule of the window changes.** `hold.py` is not edited. `PREREG-merged.md` rev 4 still stands word for word.
- **Build only after 15:30 IST.**
  - Vite hot-reloads `ui-v2` into her live screen on save.
  - `server.py` edits are inert until a restart.
- **The agent never starts the live server** (memory: agent-never-starts-live-server). After the build, ask her to run `.\stop.bat; .\start-v2.bat`.
- **Never commit.** Commit only on her word. Never commit `data/trigger_log.jsonl`.
- **Her decisions, verbatim, "again depends on market leave the size to me":**
  - never a size;
  - never "book" or "exit" in any printed string;
  - the line and the window's word are shown side by side, never merged.
- **House rules:**
  - every number is tagged [M] or [I];
  - the three absences ("checked, none — " / "could not check — " / "not shown — ") never collapse into one;
  - a missing value is never 0;
  - no hit rate or probability;
  - LIGHT only, no chart, no order path.
- **Line endings:** `server.py` is CRLF, and edits must keep it CRLF. `hold_log.py`, `test_*.py` and `ui-v2/src/**` are LF.
- **The words and their favour clauses, verbatim from §2.2:**
  - DEFENDED: "the writers in your way are holding — against your move until they give";
  - GIVING WAY: "the writers in your way are leaving — in your favour";
  - STALLED: "the writers in your way stopped adding — neither yet".

---

### Task 1: `plan.py`, the pure read, with its tests

**Files:**
- Create: `tapemap/plan.py`
- Test: `tapemap/test_plan.py`

**Interfaces:**
- Consumes:
  - `hold.thesis(side, role) -> {d, buyer, Q, R}`;
  - `hold.SESSION`, `hold.mm`, `hold.hm`, `hold.FOLD_LIVE`, `hold.CC`, `hold.NONE`, `hold.NOT_SHOWN`;
  - the `hold.read` row fields `t`, `verdict`, `since`, `fold_rule`, `line{L, room, blind}` and `prem{c}`;
  - the per-minute record fields `t`, `ix [c, h, l]`, `blind`, `folds [{k, side, t, still}]` and (new, Task 2) `fr [{k, side, state, built}]`.
- Produces:
  - `plan.word(state, fold_t=None) -> str`;
  - `plan.risk(room, greek, role, prem_now, qty) -> (float|None, str|None)`;
  - `plan.rung(rec, d, close, ext) -> dict`;
  - `plan.read(trade, minutes, rows, greeks=None) -> {"rows": [...], "touches": [...]}`;
  - `plan.next15(minutes, i, d, last) -> dict|None`;
  - `plan.DRAFT`, `plan.WORDS`, `plan.NOT_SHOWN_LINES`.

- [ ] **Step 1: Check the spec hash**

Run: `cd tapemap && sha256sum docs/hold/PLAN-PREREG.md`
Expected: `a0295c202697679f14fd59aa157813bdbf74cc0f8b1fbff6da17cea5a1e7158b`. On anything else, STOP and tell her.

- [ ] **Step 2: Write the failing tests** (`tapemap/test_plan.py`)

```python
"""plan.py against its registration (docs/hold/PLAN-PREREG.md rev 2a, §1f), on synthetic
minutes whose answer is known by hand. In-sample by construction: these pin the CODE to
the TEXT, never the market."""
import hold
import plan


def rec(t, close, lo, hi, fr=(), folds=(), blind=None):
    return {"t": t, "spot": close, "ix": [close, hi, lo], "fr": [dict(f) for f in fr],
            "folds": list(folds), "blind": blind}


def F(k, side, state, built=True):
    return {"k": k, "side": side, "state": state, "built": built}


def row(t, L, room, c=None, verdict="HOLD"):
    return {"t": t, "verdict": verdict, "since": t, "fold_rule": None,
            "line": {"L": L, "room": room, "blind": None}, "prem": {"c": c}}


def day(n=375, close=100.0):
    """A whole session of flat synthetic minutes, 09:15 onward, session-aligned."""
    return [rec(hold.SESSION[i], close, close - 1, close + 1) for i in range(n)]


def test_the_rung_is_the_nearest_sized_payers_wall_beyond_the_index():
    m = rec("12:31", 74013.5, 74010, 74030, fr=[F(74000, "PE", "UNWINDING"), F(73900, "PE", "BUILDING"),
                                               F(74100, "PE", "BUILDING"), F(73800, "PE", "BUILDING", built=False),
                                               F(73900, "CE", "BUILDING")])
    r = plan.rung(m, -1, 74013.5, 74010.0)
    assert (r["src"], r["k"], r["room"], r["word"], r["state"]) == ("wall", 74000, 14, "GIVING WAY", "UNWINDING")
    assert r["favour"] == plan.WORDS["GIVING WAY"] and r["tag"] == "M"
    up = plan.rung(m, 1, 74013.5, 74030.5)              # a long CE's wall is a CE above: none here
    assert up["src"] == "session" and up["k"] == 74030.5 and up["room"] == 17


def test_no_wall_falls_back_to_the_session_extreme_then_to_price_discovery():
    m = rec("13:57", 73659.3, 73640, 73670)
    s = plan.rung(m, -1, 73659.3, 73633.7)
    assert s["src"] == "session" and s["room"] == 26 and s["label"] == "session low — no sized wall inside the nine"
    n = plan.rung(m, -1, 73659.3, 73659.3)
    assert n["src"] == "none" and n["label"] == "no wall in the way — price discovery" and n["room"] is None
    b = plan.rung({**m, "blind": "could not check — fronts forming: 9 of 15"}, -1, 73659.3, 73633.7)
    assert b["src"] == "session" and b["label"].startswith("session low — the walls could not be read")


def test_the_three_words_and_a_live_fold():
    assert plan.word("BUILDING") == "DEFENDED" and plan.word("STALLED") == "STALLED"
    assert plan.word("UNWINDING") == "GIVING WAY" and plan.word("STALLED", "12:27") == "GIVING WAY"
    m = rec("12:31", 74013.5, 74010, 74030, fr=[F(74000, "PE", "STALLED")],
            folds=[{"k": 74000, "side": "PE", "t": "12:27", "still": True}])
    r = plan.rung(m, -1, 74013.5, 74010.0)
    assert r["word"] == "GIVING WAY" and r["fold_t"] == "12:27"
    stale = {**m, "folds": [{"k": 74000, "side": "PE", "t": "12:10", "still": True}]}   # 21 min old: not live
    assert plan.rung(stale, -1, 74013.5, 74010.0)["word"] == "STALLED"


def test_the_premium_at_risk_by_role():
    # a buyer: |Δ|·R − ½Γ·R², clamped 0…premium; a PE's negative delta is read as |Δ|
    assert plan.risk(100, (-0.5, 0.002), "long", 200.0, 20) == (800.0, None)       # (50 − 10) × 20
    assert plan.risk(100, (-0.5, 0.002), "long", 30.0, 20) == (600.0, None)        # capped at the premium
    assert plan.risk(600, (0.3, 0.002), "long", 500.0, 1) == (0.0, None)           # never below 0
    assert plan.risk(100, (0.5, 0.002), "short", 200.0, 20) == (1200.0, None)      # (50 + 10) × 20
    assert plan.risk(100, None, "long", 200.0, 20) == (None, plan.CC + "no greeks for this strike in the chain record")
    assert plan.risk(None, (0.5, 0.002), "long", 200.0, 20) == (None, plan.CC + "the line is blind this minute")


def test_one_touch_per_strike_a_retest_is_not_a_touch_a_new_strike_is():
    mins = day()
    i0 = hold.SESSION.index("12:30")
    mins[i0] = rec("12:30", 74020, 74015, 74030, fr=[F(74000, "PE", "BUILDING")])
    mins[i0 + 1] = rec("12:31", 74005, 73995, 74020, fr=[F(74000, "PE", "BUILDING")])          # touch 74,000
    mins[i0 + 2] = rec("12:32", 74008, 73990, 74015, fr=[F(74000, "PE", "BUILDING")])          # retest: no
    mins[i0 + 3] = rec("12:33", 73980, 73975, 74010, fr=[F(74000, "PE", "UNWINDING"), F(73900, "PE", "BUILDING")])
    mins[i0 + 4] = rec("12:34", 73910, 73895, 73985, fr=[F(73900, "PE", "UNWINDING")])         # touch 73,900
    rows = [row(hold.SESSION[i0 + j], 74100.0, 80 - j) for j in range(5)]
    tr = {"side": "PE", "role": "long", "qty": 20}
    out = plan.read(tr, mins, rows)
    assert [(t["t"], t["k"], t["word"]) for t in out["touches"]] == [("12:31", 74000, "DEFENDED"),
                                                                      ("12:34", 73900, "GIVING WAY")]
    assert out["rows"][0]["touch"] is None and out["rows"][2]["touch"] is None
    assert out["rows"][3]["rung"]["k"] == 73900                                   # the hand-over


def test_room_and_its_sentences():
    mins = day()
    i0 = hold.SESSION.index("12:30")
    mins[i0] = rec("12:30", 74020, 74015, 74030, fr=[F(74000, "PE", "BUILDING")])
    tr = {"side": "PE", "role": "long", "qty": 20}
    near = plan.read(tr, mins, [row("12:30", 74100.0, 80)])["rows"][0]
    assert near["room"] == {"rung": 20, "stop": 80, "text": "rung 20 pts · stop 80 pts",
                            "note": "you risk more points to the line than the next rung is away"}
    flat = day(close=74025.0)                                                     # every earlier low is 74,024
    flat[i0] = rec("12:30", 74020, 74020, 74030)                                  # the close IS the session low; no wall
    open_ = plan.read(tr, flat[:i0 + 1], [row("12:30", 74100.0, 80)])["rows"][0]
    assert open_["rung"]["src"] == "none" and open_["room"]["note"] == "no wall in the way — the stop is 80 pts behind you"


def test_the_two_exits_are_printed_side_by_side_never_merged():
    mins = day()
    out = plan.read({"side": "CE", "role": "long", "qty": 65}, mins, [row("10:00", 95.0, 5, verdict="FOLD")])
    ex = out["rows"][0]["exits"]
    assert ex["line"] == "the line: 95.0, 5 pts" and ex["window"].startswith("the window: FOLD")
    text = repr(out)
    assert "exit" not in text.replace("exits", "") and "book" not in text          # her decision: never an instruction


def test_next15_is_the_best_point_reached_not_the_last_and_waits_for_its_window():
    mins = day()
    i = hold.SESSION.index("12:00")
    mins[i] = rec("12:00", 100.0, 99.5, 100.5)
    mins[i + 2] = rec("12:02", 90.0, 80.0, 99.0)                                  # the best point: 20 pts
    mins[i + 15] = rec("12:15", 99.0, 98.5, 99.5)                                 # the last point: 1 pt
    assert plan.next15(mins, i, -1, i + 14) is None                               # the window has not finished
    got = plan.next15(mins, i, -1, i + 15)
    assert got == {"pts": 20.0, "to": "12:15", "short": False, "tag": "M"}
    late = hold.SESSION.index("15:20")
    assert plan.next15(mins, late, -1, 374) == {"pts": 1.0, "to": "15:29", "short": True, "tag": "M"}
    assert plan.next15(mins, i, 1, i + 15)["pts"] == 1.0                         # a long CE's side: the highest high, 101


def test_a_writer_gets_the_stop_only():
    mins = day()
    out = plan.read({"side": "CE", "role": "short", "qty": 20}, mins, [row("10:00", 105.0, 5, c=50.0)],
                    greeks=[(0.4, 0.001)] * 375)
    r = out["rows"][0]
    assert r["rung"] is None and r["room"] is None and out["touches"] == []
    assert r["stop"]["risk"] == round((0.4 * 5 + 0.5 * 0.001 * 25) * 20, 2) and r["stop"]["risk_tag"] == "I"


def test_a_plan_cut_at_a_minute_is_the_first_part_of_the_close_plan():
    mins = day()
    rows = [row(hold.SESSION[i], 110.0, 10) for i in range(100, 200)]
    tr = {"side": "CE", "role": "long", "qty": 1}
    full, cut = plan.read(tr, mins, rows), plan.read(tr, mins, rows[:50])
    assert cut["rows"] == full["rows"][:50]
```

- [ ] **Step 3: Run it to see it fail**

Run: `cd tapemap && python -m pytest -q test_plan.py`
Expected: `ModuleNotFoundError: No module named 'plan'`.

- [ ] **Step 4: Write `tapemap/plan.py`**

```python
"""plan.py -- THE PLAN: STOP · NEXT RUNG · ROOM, exactly as registered.

THE SPEC is docs/hold/PLAN-PREREG.md rev 2a (sha256 a0295c20...158b, anchored in
context/research-findings.md §1f), signed by the operator 2026-09-25 09:31. It sits
BESIDE the hold window (hold.py, PREREG-merged rev 4) and changes none of its rules:
it reads the window's own line off hold.read's rows and the same per-minute records.

Her decisions, verbatim, "again depends on market leave the size to me": the plan
never sizes, never says "book" or "exit", and prints the line and the window's word
side by side, never merged.

Pure: no I/O, no clock. It gates nothing; there is no order path.
"""
from __future__ import annotations

import hold

CC, NONE, NOT_SHOWN = hold.CC, hold.NONE, hold.NOT_SHOWN
NEXT = 15                    # §5 (M1): a touch's window, finished minutes, rev 4 §7's extremum
LAST = len(hold.SESSION) - 1  # 15:29
DRAFT = "DRAFT — pre-registered 2026-09-25 (docs/hold/PLAN-PREREG.md rev 2a), untested; its §6 decides"
WORDS = {
    "DEFENDED": "the writers in your way are holding — against your move until they give",
    "GIVING WAY": "the writers in your way are leaving — in your favour",
    "STALLED": "the writers in your way stopped adding — neither yet",
}
RULE = {3: "the line", 4: "positioning flipped", 5: "the reason is gone", 6: "two families"}
NOT_SHOWN_LINES = [NOT_SHOWN + "a size: the plan leaves the size to you",
                   NOT_SHOWN + "a single exit: the line and the window both stand; you choose"]
mm, hm = hold.mm, hold.hm


def _strip(why):
    return (why or "").replace(CC, "") or None


def word(state, fold_t=None):
    """§2.2 / §2.4: the rung's word off its §1d state; a live fold reads GIVING WAY.
    board.still_folded never holds while a front reads BUILDING, so the order is exhaustive."""
    if state == "BUILDING":
        return "DEFENDED"
    if state == "UNWINDING" or fold_t:
        return "GIVING WAY"
    return "STALLED"


def _live_fold(rec, k, side):
    return next((f["t"] for f in reversed(rec.get("folds") or [])
                 if f["side"] == side and f["k"] == k and f.get("still")
                 and 0 <= mm(rec["t"]) - mm(f["t"]) <= hold.FOLD_LIVE), None)


def risk(room, greek, role, prem_now, qty):
    """§2.1: the premium at risk if the line broke now, × qty -- [I] on the broker's [M]
    delta and gamma. A buyer: |Δ|·R − ½Γ·R², clamped 0…premium; a writer: |Δ|·R + ½Γ·R²."""
    if room is None:
        return None, CC + "the line is blind this minute"
    if not greek or greek[0] is None or greek[1] is None:
        return None, CC + "no greeks for this strike in the chain record"
    dl, g, r = abs(greek[0]), greek[1], max(room, 0)
    if role == "long":
        per = max(0.0, dl * r - 0.5 * g * r * r)
        if prem_now is not None:
            per = min(per, prem_now)
    else:
        per = dl * r + 0.5 * g * r * r
    return round(per * (qty or 0), 2), None


def rung(rec, d, close, ext):
    """§2.2: the nearest SIZED payers'-side front strictly beyond the index in her
    direction; else the session extreme `ext` if it lies beyond; else price discovery."""
    side = "PE" if d < 0 else "CE"

    def beyond(k):
        return k < close if d < 0 else k > close
    word_side = "low" if d < 0 else "high"
    if not rec.get("blind"):
        walls = [f for f in rec.get("fr") or [] if f["side"] == side and f.get("built") and beyond(f["k"])]
        if walls:
            f = min(walls, key=lambda f: abs(f["k"] - close))
            fold = _live_fold(rec, f["k"], side)
            w = word(f["state"], fold)
            return {"src": "wall", "side": side, "k": f["k"], "room": round(abs(f["k"] - close)), "word": w,
                    "favour": WORDS[w], "state": f["state"], "fold_t": fold, "tag": "M"}
        label = f"session {word_side} — no sized wall inside the nine"
    else:
        label = f"session {word_side} — the walls could not be read: {_strip(rec['blind'])}"
    if ext is not None and beyond(ext):
        return {"src": "session", "side": side, "k": ext, "room": round(abs(ext - close)), "word": None,
                "label": label, "tag": "M"}
    return {"src": "none", "side": side, "k": None, "room": None, "word": None,
            "label": "no wall in the way — price discovery", "tag": "M"}


def next15(minutes, i, d, last):
    """§5 (M1): the MAXIMUM favourable index excursion over the 15 finished minutes after
    the touch minute i, from its 1-min close; to 15:29 and flagged short. None until that
    window has finished (`last` = index of the latest finished minute)."""
    end = min(i + NEXT, LAST)
    if last < end or not minutes[i].get("ix"):
        return None
    c = minutes[i]["ix"][0]
    xs = [m["ix"] for m in minutes[i + 1:end + 1] if m.get("ix")]
    if not xs:
        return {"pts": None, "to": hold.SESSION[end], "short": i + NEXT > LAST, "tag": "M",
                "why": CC + "no index candle in the window"}
    pts = (c - min(x[2] for x in xs)) if d < 0 else (max(x[1] for x in xs) - c)
    return {"pts": round(max(pts, 0.0), 2), "to": hold.SESSION[end], "short": i + NEXT > LAST, "tag": "M"}


def read(trade, minutes, rows, greeks=None):
    """THE PLAN beside each of hold.read's `rows` (same trade, same session-aligned
    `minutes`). `greeks`: [(delta, gamma) | None] aligned to `minutes`.
    -> {"rows": [...one per hold row...], "touches": [{t, i, k, side, word, close}]}."""
    th = hold.thesis(trade["side"], trade["role"])
    d, buyer = th["d"], th["buyer"]
    at = {m["t"]: i for i, m in enumerate(minutes)}
    ext, run = [], None                          # the session extreme in her direction, 09:15 .. each minute
    for m in minutes:
        x = m.get("ix")
        if x:
            v = x[2] if d < 0 else x[1]
            run = v if run is None else (min(run, v) if d < 0 else max(run, v))
        ext.append(run)
    out, touches, touched, prev = [], [], set(), None
    for r in rows:
        i = at[r["t"]]
        m, ln = minutes[i], r["line"]
        room = None if ln.get("blind") else ln.get("room")
        g = greeks[i] if greeks and i < len(greeks) else None
        rk, why = risk(room, g, trade["role"], (r.get("prem") or {}).get("c"), trade.get("qty"))
        stop = {"L": ln.get("L"), "room": room, "risk": rk, "risk_why": why, "tag": "M", "risk_tag": "I"}
        win = f"the window: {r['verdict']}" + (f" · {RULE[r['fold_rule']]}" if r.get("fold_rule") else "") + \
              f" · since {r['since']}"
        exits = {"line": f"the line: {ln.get('L')}, {room} pts" if room is not None else "the line: could not check",
                 "window": win}
        if not buyer:
            out.append({"t": r["t"], "stop": stop, "rung": None, "room": None, "touch": None, "exits": exits})
            continue
        ix = m.get("ix")
        rg = rung(m, d, ix[0], ext[i]) if ix else {"src": "none", "side": "PE" if d < 0 else "CE", "k": None,
                                                    "room": None, "word": None, "tag": "M",
                                                    "label": CC + f"no index candle at {r['t']}"}
        touch = None
        if prev and prev["src"] in ("wall", "session") and ix and prev["k"] is not None:
            reached = ix[2] <= prev["k"] if d < 0 else ix[1] >= prev["k"]
            key = (prev["k"], prev["side"] if prev["src"] == "wall" else "session")
            if reached and key not in touched:
                touched.add(key)
                if prev["src"] == "wall":
                    f = next((f for f in m.get("fr") or [] if f["k"] == prev["k"] and f["side"] == prev["side"]), None)
                    w = word(f["state"], _live_fold(m, prev["k"], prev["side"])) if f else prev["word"]
                    touch = {"k": prev["k"], "side": prev["side"], "word": w, "favour": WORDS[w],
                             "read": "at the touch minute" if f else "as last read — not in the top 2 this minute"}
                    touches.append({"t": r["t"], "i": i, "close": ix[0], **touch})
                else:                            # §2.4: printed, never counted
                    touch = {"session": True, "text": f"session {'low' if d < 0 else 'high'} touched — no wall read there"}
        rr = rg.get("room")
        note = (f"no wall in the way — the stop is {room} pts behind you" if rg["src"] == "none" and room is not None else
                "you risk more points to the line than the next rung is away" if rr is not None and room is not None
                and rr < room else None)
        out.append({"t": r["t"], "stop": stop, "rung": rg, "touch": touch, "exits": exits,
                    "room": {"rung": rr, "stop": room, "text": f"rung {rr if rr is not None else '—'} pts · stop "
                                                              f"{room if room is not None else '—'} pts", "note": note}})
        prev = rg
    return {"rows": out, "touches": touches}
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `cd tapemap && python -m pytest -q test_plan.py`
Expected: `10 passed`.
- If `test_room_and_its_sentences` fails on the dict order, compare the keys. The assertion is dict equality, so order does not matter.
- If `test_the_two_exits…` fails on "exit", the printed strings contain an instruction. Fix the string, never the test.

- [ ] **Step 6: No commit.** Commit only on her word.

---

### Task 2: the facts the plan reads (fronts per minute, broker greeks per minute)

**Files:**
- Modify: `tapemap/server.py`:
  - `_hold_rec`: add `rec["fr"]`;
  - `_hold_peaks`: also capture greeks;
  - a new `_hold_greeks`.
- Modify: `tapemap/test_hold_route.py`: add the greeks test.

**Interfaces:**
- Produces:
  - `rec["fr"] = [{"k": float, "side": "CE"|"PE", "state": str, "built": bool}]` (fronts.read's top 2 per side at t), present whenever fronts were read;
  - `_hold_greeks(idx, day, k, side, n) -> [(delta, gamma) | None] * n`, carried forward from the latest snapshot at or before each minute.

- [ ] **Step 1: Write the failing test.** Append to `test_hold_route.py`, after `test_the_running_peak_is_read_off_the_chain_record_as_it_stood`:

```python
def test_the_greeks_are_read_off_the_chain_record_and_carried_forward(monkeypatch, tmp_path):
    """PLAN §2.1: the broker's delta and gamma for her strike-side at the latest snapshot
    at or before each minute [M]; a strike the record never carried reads None."""
    import chain_live
    monkeypatch.setattr(chain_live, "CHAIN_DIR", tmp_path)
    monkeypatch.setattr(server, "_HOLD", _fresh())
    p = tmp_path / "chain_NIFTY_2026-09-24.jsonl"
    leg = lambda oi, dl, g: {"oi": oi, "delta": dl, "gamma": g}                       # noqa: E731
    p.write_text(json.dumps({"ts": "09:15:05", "spot": 23200.0, "strikes": [
        {"k": 23200, "ce": leg(100, 0.52, 0.0014), "pe": leg(90, -0.48, 0.0013)}]}) + "\n"
                 + json.dumps({"ts": "09:17:30", "spot": 23210.0, "strikes": [
        {"k": 23200, "ce": leg(110, 0.55, 0.0015), "pe": leg(95, -0.45, 0.0012)}]}) + "\n")
    server._hold_peaks("NIFTY", DAY)
    assert server._hold_greeks("NIFTY", DAY, 23200, "PE", 4) == [(-0.48, 0.0013), (-0.48, 0.0013),
                                                                (-0.45, 0.0012), (-0.45, 0.0012)]
    assert server._hold_greeks("NIFTY", DAY, 23250, "CE", 2) == [None, None]
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd tapemap && python -m pytest -q test_hold_route.py -k greeks`
Expected: `AttributeError: module 'server' has no attribute '_hold_greeks'`.

- [ ] **Step 3: Implement it** in `server.py`, keeping CRLF. Use the Edit tool; verify with the byte check in Step 5.

In `_hold_peaks`, the two state resets gain `greeks`:

```python
        st = _HOLD["peaks"][idx] = {"day": day, "off": 0, "run": {}, "by_t": {}, "greeks": {}}
```
```python
                st.update(off=0, run={}, by_t={}, greeks={})
```

and the per-snapshot loop becomes:

```python
        gk = st["greeks"].setdefault(m, {})          # PLAN §2.1: the broker's greeks, last snapshot of the minute
        for row in s.get("strikes") or []:
            ce, pe = row.get("ce") or {}, row.get("pe") or {}
            gk[float(row["k"])] = (ce.get("delta"), ce.get("gamma"), pe.get("delta"), pe.get("gamma"))
            for side in ("ce", "pe"):
                oi = (row.get(side) or {}).get("oi")
                if isinstance(oi, (int, float)):
                    key = (float(row["k"]), side)
                    run[key] = max(run.get(key, 0.0), float(oi))
        st["by_t"][m] = dict(run)
```

A new function, directly after `_hold_peaks`:

```python
def _hold_greeks(idx, day, k, side, n):
    """[(delta, gamma) | None] for the first n session minutes: the broker's greeks for
    her strike-side at the latest chain snapshot at or before each minute [M] (the
    record _hold_peaks reads). None before the strike first appears -- never a zero."""
    st = _HOLD["peaks"].get(idx) or {}
    by = (st.get("greeks") or {}) if st.get("day") == day else {}
    j, out, last = (0 if side == "CE" else 2), [], None
    for t in hold.SESSION[:n]:
        g = (by.get(t) or {}).get(float(k))
        if g and g[j] is not None and g[j + 1] is not None:
            last = (g[j], g[j + 1])
        out.append(last)
    return out
```

In `_hold_rec`, directly after `fr = fronts.read(cut, pk)`:

```python
        rec["fr"] = [{"k": f["k"], "side": f["side"], "state": f["state"], "built": f["peak"] > 0}
                     for f in fr]                # PLAN §2.2: the top 2 per side, for the rung
```

- [ ] **Step 4: Run it to see it pass, then the hold suites**

Run: `cd tapemap && python -m pytest -q test_hold_route.py test_hold.py test_plan.py`
Expected: all pass.

- [ ] **Step 5: Check the line endings**

Run: `cd tapemap && python -c "b=open('server.py','rb').read(); print(sum(1 for l in b.split(b'\n')[:-1] if not l.endswith(b'\r')))"`
Expected: `0`.

- [ ] **Step 6: No commit.**

---

### Task 3: `/api/hold` gains `plan`; the log gains `plan` and `rung_touch` rows

**Files:**
- Modify: `tapemap/hold_log.py`: `key()` includes `kind` for hold rows.
- Modify: `tapemap/server.py`:
  - `import plan` beside `import hold`;
  - `_hold_reply`: the `plan` key;
  - `_hold_row`: the `plan` key;
  - `_hold_tick`: plan rows, and `rung_touch` rows.
- Modify: `tapemap/test_hold_route.py`: new assertions; update the log-count assertion.

**Interfaces:**
- Consumes: `plan.read`, `plan.next15`, `plan.DRAFT`, `plan.NOT_SHOWN_LINES` (Task 1); `_hold_greeks` (Task 2).
- Produces:
  - `/api/hold` → `"plan": {...the latest plan row..., "entry": {...the entry minute's plan row...}, "draft": plan.DRAFT, "not_shown": [...]}`;
  - hold-log rows carry `"plan": {"stop", "rung", "touch"}`;
  - `{"kind": "rung_touch", "trade_id", "t", "touch_t", "idx", "k", "side", "word", "close_at_touch", "next15", "src", "tag": "M", "at"}` rows.

- [ ] **Step 1: Write the failing tests.** Add `import plan` to `test_hold_route.py`'s imports, then add:

```python
def test_the_reply_carries_the_plan_beside_the_window(srv):
    _post("/api/hold/trades", MARK, srv)
    a = _get("/api/hold?id=NIFTY-23200PE-long-122030", srv)
    p = a["plan"]
    assert p["draft"] == plan.DRAFT and p["not_shown"] == plan.NOT_SHOWN_LINES
    assert p["t"] == a["now"]["t"] and p["entry"]["t"] == a["entry"]["t"]
    assert p["stop"]["L"] == a["now"]["line"]["L"] and p["stop"]["risk"] is None       # the test poller has no greeks
    assert p["stop"]["risk_why"] == board.CC + "no greeks for this strike in the chain record"
    assert p["rung"]["src"] in ("wall", "session", "none") and p["exits"]["window"].startswith("the window: ")


def test_rung_touches_are_their_own_write_once_rows(srv):
    _post("/api/hold/trades", MARK, srv)
    server._hold_tick(srv, "NIFTY")
    rows = _lines("hold")
    minute = [r for r in rows if r.get("kind", "minute") == "minute"]
    touch = [r for r in rows if r.get("kind") == "rung_touch"]
    assert all("plan" in r and set(r["plan"]) == {"stop", "rung", "touch"} for r in minute)
    assert [r["t"] for r in touch] == [r["t"] for r in minute if (r["plan"]["touch"] or {}).get("word")]
    assert all(r["next15"]["tag"] == "M" and r["word"] in plan.WORDS for r in touch)
    assert server._hold_tick(srv, "NIFTY") == 0                                         # write-once
```

In `test_the_logs_are_written_once_from_entry_to_the_close`, `trade = _lines("hold")` becomes:

```python
    trade = [r for r in _lines("hold") if r.get("kind", "minute") == "minute"]
    touches = [r for r in _lines("hold") if r.get("kind") == "rung_touch"]
```

and its count line becomes:

```python
    assert n == len(side) + len(trade) + len(tracks) + len(touches)
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd tapemap && python -m pytest -q test_hold_route.py -k "plan or touch"`
Expected: `KeyError: 'plan'`.

- [ ] **Step 3: Implement it**

`hold_log.py`, the `key()` function:

```python
def key(kind: str, r: dict):
    if kind == "hold":                       # a minute row and a rung_touch row at the same t are two rows
        return r.get("trade_id"), r.get("t"), r.get("kind") or "minute"
    return r.get("idx"), r.get("t"), r.get("kind") or "minute"
```

`server.py`, beside `import hold`:

```python
import plan                      # THE PLAN beside the window (docs/hold/PLAN-PREREG.md rev 2a, §1f)
```

`_hold_reply`, directly after the `if not res["ok"]: return {...}` block:

```python
    pl = plan.read(tr, mins, res["rows"], greeks=_hold_greeks(tr["idx"], F["day"], tr["k"], tr["side"], len(mins)))
```

and in the returned dict, after `"fold": res["fold"],`:

```python
        "plan": {**pl["rows"][-1], "entry": pl["rows"][0], "draft": plan.DRAFT, "not_shown": plan.NOT_SHOWN_LINES},
```

`_hold_row(F, tr, x, ent, sd)` becomes `_hold_row(F, tr, x, ent, sd, pr)` and adds, before `"tag": "I"`:

```python
            "plan": {"stop": {k: pr["stop"].get(k) for k in ("L", "room", "risk", "risk_why")},
                     "rung": pr["rung"] and {k: pr["rung"].get(k) for k in ("src", "side", "k", "room", "word", "state", "fold_t")},
                     "touch": pr["touch"] and {k: pr["touch"].get(k) for k in ("k", "side", "word", "session")}},
```

In `_hold_tick`, the per-trade loop becomes:

```python
    for tr in trades:
        res = hold.read(tr, mins, F["pivots"], prem=_hold_prem(F, tr["k"], tr["side"]), idx=idx)
        if not res["ok"]:
            continue
        pl = plan.read(tr, mins, res["rows"], greeks=_hold_greeks(idx, day, tr["k"], tr["side"], len(mins)))
        pr = {p["t"]: p for p in pl["rows"]}
        n += hold_log.append("hold", day, [_hold_row(F, tr, x, res["entry"], by_t[x["t"]], pr[x["t"]])
                                           for x in res["rows"]
                                           if not hold_log.has("hold", day, (tr["id"], x["t"], "minute"))])
        d = res["th"]["d"]
        touch_rows = []
        for tc in pl["touches"]:
            nx = plan.next15(mins, tc["i"], d, len(mins) - 1)
            if nx is None or hold_log.has("hold", day, (tr["id"], tc["t"], "rung_touch")):
                continue
            touch_rows.append({"day": day, "kind": "rung_touch", "t": tc["t"], "touch_t": tc["t"], "trade_id": tr["id"],
                               "idx": idx, "src": tr["src"], "k": tc["k"], "side": tc["side"], "word": tc["word"],
                               "close_at_touch": tc["close"], "next15": nx, "tag": "M", "at": round(time.time(), 1)})
        n += hold_log.append("hold", day, touch_rows)
```

- [ ] **Step 4: Run it to see it pass, then all the hold suites**

Run: `cd tapemap && python -m pytest -q test_hold_route.py test_hold.py test_plan.py`
Expected: all pass.

- [ ] **Step 5: CRLF check,** as in Task 2 Step 5. Expected: `0`.

- [ ] **Step 6: No commit.**

---

### Task 4: the three lines on the window (after 15:30 only: Vite hot-reloads her screen)

**Files:**
- Modify: `tapemap/ui-v2/src/hold/HoldWindow.tsx`

**Interfaces:**
- Consumes: `/api/hold` → `plan` (Task 3).

- [ ] **Step 1: Types.** Add the `PlanRow` type after the `Reading` type:

```ts
type PlanRow = {
  t: string
  stop: { L?: number; room?: number | null; risk?: number | null; risk_why?: string | null }
  rung: null | { src: 'wall' | 'session' | 'none'; side: string; k: number | null; room: number | null; word: string | null
                 favour?: string; state?: string; fold_t?: string | null; label?: string }
  room: null | { rung: number | null; stop: number | null; text: string; note: string | null }
  touch: null | { k?: number; side?: string; word?: string; favour?: string; session?: boolean; text?: string }
  exits: { line: string; window: string }
}
```

and on `Reading`, add:

```ts
  plan?: PlanRow & { entry: PlanRow; draft: string; not_shown: string[] }
```

- [ ] **Step 2: The block.** Insert it directly before `{sideRead && <SideBlock ...}`:

```tsx
      {current && now && rd?.plan && <PlanBlock p={rd.plan} />}
```

and add the component at the end of the file:

```tsx
function PlanBlock({ p }: { p: PlanRow & { not_shown: string[] } }) {
  // THE PLAN (docs/hold/PLAN-PREREG.md rev 2a): distances and a word, never a size, never an instruction
  const rg = p.rung
  const rungText = !rg ? null
    : rg.src === 'wall' ? `${rg.side} ${rg.k?.toLocaleString('en-IN')} · ${rg.room} pts · ${rg.word} — ${rg.favour} · ${rg.state}${rg.fold_t ? `, folded ${rg.fold_t}` : ''}`
    : rg.src === 'session' ? `${rg.label} · ${rg.k?.toLocaleString('en-IN', { maximumFractionDigits: 1 })} · ${rg.room} pts`
    : rg.label
  return (
    <div style={{ padding: '6px 10px', borderBottom: `1px solid ${C.line}`, fontSize: 11.5, color: C.pn, display: 'flex', flexDirection: 'column', gap: 3 }}>
      <div><b style={{ color: C.ink }}>STOP</b> {p.stop.L != null ? `${n1(p.stop.L)} · ${p.stop.room} pts` : 'could not check'} [M]
        {' · '}{p.stop.risk != null ? `≈ ₹${n0(p.stop.risk)} at risk if it broke now [I]` : p.stop.risk_why}</div>
      {rungText && <div><b style={{ color: C.ink }}>RUNG</b> {rungText} [M]</div>}
      {p.room && <div><b style={{ color: C.ink }}>ROOM</b> {p.room.text}{p.room.note && <span style={{ color: C.watch }}> — {p.room.note}</span>}</div>}
      {p.touch && <div style={{ color: C.ink }}>touched {p.t}: {p.touch.session ? p.touch.text : `${p.touch.word} — ${p.touch.favour}`}</div>}
      <div style={{ color: C.mute }}>{p.exits.line} · {p.exits.window} — both stand; you choose</div>
    </div>
  )
}
```

- [ ] **Step 3: The collapsed line** gains the rung. It is never P&L. `collapsed(t, n)` becomes `collapsed(t, n, pl?: PlanRow)`, and its last line becomes:

```ts
  const rung = pl?.rung?.src === 'wall' ? ` · rung ${pl.rung.room} pts ${pl.rung.word}` : ''
  return `${t.idx} ${t.k} ${t.side} ${t.role} · ${ln} · ${a}${rung}`
```

The call site `collapsed(current, now)` becomes `collapsed(current, now, rd?.plan)`.

- [ ] **Step 4: The absences.** Inside the existing `<details>` block, after the `not_shown` map:

```tsx
            {(rd?.plan?.not_shown || []).map((b, i) => <div key={`p${i}`}>{b}</div>)}
```

- [ ] **Step 5: Type-check**

Run: `cd tapemap/ui-v2 && npx tsc --noEmit`
Expected: no output, exit 0.

- [ ] **Step 6: No commit.**

---

### Task 5: verify, and hand the restart to her

**Files:**
- Modify: `tapemap/CLAUDE.md`, `tapemap/START-HERE.md`, `tapemap/context/DEFERRED.md`: the stated test count, which `test_docs_claims.py` pins.

- [ ] **Step 1: The full suite**

Run: `cd tapemap && python -m pytest -q -p no:cacheprovider`
Expected: the 3 known `test_desk_numbers` failures, and `test_docs_claims::test_stated_test_count_matches_reality` failing with the new count, before Step 2.

- [ ] **Step 2: Update the count** in all three places:
  - CLAUDE.md line 58 and START-HERE.md line 235: `NNNN collected, MMMM passing …, as of 2026-09-25`.
  - DEFERRED.md: a new leading `- **Test count is now NNNN** (…THE PLAN, signed 09:31 §1f: plan.py + tests, the fronts and greeks per minute, /api/hold.plan, rung_touch rows… (1474+N=NNNN); before that 1474, …` entry, byte-safe as before.

  Re-run the suite. Expected: only the 3 known failures.

- [ ] **Step 3: Replay on the raw record** with the scratch harness (`<scratchpad>/e2e.py` and `replay_srv.py` from 2026-09-25; rebuild them if the scratchpad is gone).
  - Read her 09-24 12:32 SENSEX 74100PE at `asof=12:31`: `plan.rung` should be `PE 74,000 · 14 pts · GIVING WAY`, as described in PLAN-PREREG §3.
  - At 13:57 SENSEX 73800PE (`asof=13:56`): `rung.src` should be `session` or `none`, and the room note should be present. This is the chase case.
  - Screens at 1536×695: the open window with the three lines, and the collapsed line with the rung and no P&L.

- [ ] **Step 4: Hand over the restart.** Do not start the server. Tell her the build is verified and ask her to run:

```bash
.\stop.bat; .\start-v2.bat
```

After her restart, check `curl -s "http://127.0.0.1:8765/api/hold/trades"` answers. Check that `data/trigger_log.jsonl`'s line count equals its count before the build.

- [ ] **Step 5: Record it.**
  - Append a "THE PLAN built" section to `docs/hold/BUILD-REPORT.md`.
  - Update the memory file `hold-fold-window-2026-09-24.md`.
  - No commit without her word.
