# RIDE Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to carry out this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** implement `docs/setup-review/RIDE-PREREG.md` (sha256 `dcb306a1…aff7e`, research-findings §1j). Mary's second
setup is RIDE: READ-V2 §E's trend-pullback entry plus the same OI and FLOW checks, and her hold (a hard line trailing to
FLIP, "somebody gave up", 15:20). The pieces are:
- a pure module;
- tests;
- a dry-count scorer;
- a fail-soft live forward log.

**Architecture:**
- `ride.py` is pure (no I/O, no clock), beside the already-built FADE `confluence.py`. It reuses FADE's FLOW plumbing
  and chain grid and `fronts`. §E is never re-implemented: `ride.entries` calls the registered `frame_v2.plan` causally,
  once per closed bar.
- `confluence_log.py` gains the RIDE inputs loader and a fail-soft `log_ride`.
- `tools/ride_score.py` prints dry counts only. Its `--run` refuses until some cell can reach n ≥ 20 with forward rows,
  per §6.

**Tech stack:** Python 3.13 stdlib, pytest. The existing modules used are:
- `frame_v2` (`bars3`, `plan`, `cut`, `compose`'s basis), `read` (`from_v2`, `timeline`);
- `fronts`, `confluence`, `confluence_log`, `v2feed`, `ux_log`, `server._read_gc_pre`.

## Global Constraints
- **The spec is never edited.** `docs/setup-review/RIDE-PREREG.md` must keep sha256
  `dcb306a11ad662291a25094e7db3288aeacc3367be403d2364900302843aff7e`. Every tool checks it before running.
- **Numbers are fixed and never tuned:**
  - `TILT = 0.10`, `FAST = 5`, `SLOW = 15` (min);
  - `WINDOW_BARS = 3`, `WINDOW_MIN = 9`;
  - `CUTOFF = 15:00` (entry bar close), `MARK = 15:20`;
  - `LINE_BUF = 0.25` σ, `MIN_RISK = 0.5` σ;
  - pass bar `20 / +0.25 / >0 / +0.20 / 40%`.
- **OI ✓ (▼)** = CE front BUILDING **and** PE front not BUILDING. ▲ is mirrored.
- **FLOW ✓ (▼)** = `tilt(last 5) ≤ −0.10` **and** `tilt(previous 15) ≤ +0.10`. ▲ is mirrored.
  - NIFTY GC disagreement: a GC tilt ≥ +0.10 (▼) makes it FLOW ✗. An absent GC is not disagreement.
- **No candle-close exit anywhere.** No fixed target. STALLED never exits. The READ word changing never exits.
- **R uses the initial risk,** even after the trail.
- **No hit rate is printed anywhere.**
- **No R or premium outcome is computed on real recorded days** until §6's gate opens. Synthetic tests only.
- **Changes are surgical.**
  - No change to any existing row, gate, beep, frame key or log.
  - `frame_v2.plan`'s behaviour is unchanged; `frame_v2.bars3` keeps its default output.
- **No commits** (Mary commits on her word).
- **No server start or stop, and no localhost calls.**
- **No writes to `data/trigger_log.jsonl`.**
- **The live log is fail-soft:** an exception returns 0 and never reaches the caller.

## File structure
- Create `ride.py`: the pure RIDE rules (entries, OI, FLOW, entry, line, outcome, expressions, stamps, row).
- Create `test_ride.py`: one test per rule, no-look-ahead, trail-only-toward-price, STALLED-holds,
  UNWINDING-exits.
- Modify `frame_v2.py`: `bars3(ticks, lot, now=None, width=BAR3)`, generalising the bucket width so RIDE gets 1-min
  bars from the same ticks. The default is unchanged.
- Modify `confluence_log.py`:
  - `ride_inputs(index, day)`;
  - `build_ride(...)`;
  - `log_ride(index, now=None, path=PATH)`;
  - FADE rows gain `"setup": "FADE"` (the file does not exist yet; her restart starts it).
- Create `tools/ride_score.py`: dry counts per cell; `--run` gated by §6.
- Modify `server.py`: one fail-soft `confluence_log.log_ride(x)` call beside the existing `confluence_log.log_new(...)`
  (around line 5793).
- Modify `context/research-findings.md` §1j: append "BUILT" with the file list, after tests pass.

---

### Task 1: `frame_v2.bars3` width parameter

**Files:**
- Modify: `frame_v2.py`, `def bars3` (lines about 170–193).
- Test: `test_frame_v2.py` (append).

**Interfaces:**
- Produces: `frame_v2.bars3(ticks, lot, now=None, width=180) -> [{s, e, o, h, l, c, v, delta, vwap, sig}]`. With
  `width=60`, it gives 1-min bars from the same 1-s ticks.

- [ ] **Step 1: Write the failing test**
```python
def test_bars3_width_60_gives_one_minute_bars_and_default_is_unchanged():
    import frame_v2
    t0 = frame_v2.OPEN_S
    ticks = [[t0 + s, 225000 + s, 10, 6] for s in range(0, 360)]          # 6 minutes of 1-s bars
    b3 = frame_v2.bars3(ticks, 1, now=t0 + 360)
    b1 = frame_v2.bars3(ticks, 1, now=t0 + 360, width=60)
    assert [b["s"] - t0 for b in b3] == [0, 180]
    assert [b["s"] - t0 for b in b1] == [0, 60, 120, 180, 240, 300]
    assert b1[0]["h"] == 22505.9 and b1[0]["l"] == 22500.0
```
- [ ] **Step 2:** run `python -m pytest -q test_frame_v2.py -k width`. Expected: FAIL, unexpected keyword `width`.
- [ ] **Step 3: Implement.** Change the signature to `def bars3(ticks, lot, now=None, width=BAR3):`. Replace the two
  uses of `BAR3` inside the loop with `width`:
```python
        s0 = OPEN_S + (sec - OPEN_S) // width * width
        if s0 + width > end:
            break
        ...
            cur = {"s": s0, "e": s0 + width, "o": px, "h": px, "l": px, "c": px, "vol": 0, "buy": 0}
```
- [ ] **Step 4:** run `python -m pytest -q test_frame_v2.py`. Expected: all PASS (the default output is unchanged).

### Task 2: `ride.py` — entries, OI, FLOW, the RIDE entry

**Files:**
- Create: `ride.py`
- Test: `test_ride.py`

**Interfaces:**
- **Consumes:**
  - `frame_v2.plan(b3, rows, basis, now) -> (dict|None, why)`: an ENTRY event is `{"t": "HH:MM" (bar END), "what":
    "ENTRY", "px"}` in `plan["rows"]`, with `plan["d"]`.
  - `confluence.tilt(book, a, b)`, `confluence.gc_tilt(gc, close)`, `confluence._upto(peaks, at)`.
  - `fronts.cut / stale / read / side_front`; `fronts.BUILDING / STALLED / UNWINDING`.
- **Produces:**
  - `ride.entries(b3, rows, basis) -> [{"i", "t", "d", "word", "px"}]`;
  - `ride.oi_read(d, minutes, peaks, at) -> {"ok", "why", "trend", "defend"}`;
  - `ride.flow_read(d, book, close_min, gc=None) -> {"ok", "t5", "t15", "gc", "why"}`;
  - `ride.trade(d, trig_bar, bar) -> {"E", "sigma", "line0"}`;
  - `ride.evaluate(ent, b3, chain, book, gc=None) -> {"bars": [...], "entry": dict|None}`.

- [ ] **Step 1: Write the failing tests** (`test_ride.py`)
```python
import fronts
import ride

def front(side, state, k=22500.0):
    return {"side": side, "k": k, "state": state, "peak_at": "10:00"}

def test_oi_ok_down_needs_ce_building_and_pe_not_building(monkeypatch):
    monkeypatch.setattr(fronts, "stale", lambda cut, at: None)
    monkeypatch.setattr(fronts, "cut", lambda m, at: m)
    cases = [((fronts.BUILDING, fronts.STALLED), True), ((fronts.BUILDING, fronts.UNWINDING), True),
             ((fronts.BUILDING, fronts.BUILDING), False), ((fronts.STALLED, fronts.UNWINDING), False)]
    for (ce, pe), want in cases:
        monkeypatch.setattr(fronts, "read", lambda cut, peaks, ce=ce, pe=pe: [front("CE", ce), front("PE", pe)])
        assert ride.oi_read(-1, {"10:00": {}}, {}, "10:00")["ok"] is want
    # up is the mirror: PE building, CE not building
    monkeypatch.setattr(fronts, "read", lambda cut, peaks: [front("CE", fronts.STALLED), front("PE", fronts.BUILDING)])
    assert ride.oi_read(+1, {"10:00": {}}, {}, "10:00")["ok"] is True

def test_oi_stale_grid_is_could_not_check(monkeypatch):
    monkeypatch.setattr(fronts, "cut", lambda m, at: m)
    monkeypatch.setattr(fronts, "stale", lambda cut, at: "grid 5 min stale")
    r = ride.oi_read(-1, {}, {}, "10:00")
    assert r["ok"] is None and r["why"] == "grid 5 min stale"

def book(mins):
    """mins: {minute: (buy, sell)} -> confluence's (flow, seen, bad)."""
    return ({m: list(v) for m, v in mins.items()}, set(mins), set())

def test_flow_down_needs_sellers_back_and_no_strong_counter_buying():
    close = 600                                                        # 10:00
    prev = {m: (55, 45) for m in range(close - 20, close - 5)}        # +0.10 counter tilt: allowed (<= +0.10)
    last = {m: (40, 60) for m in range(close - 5, close)}             # -0.20: sellers back
    assert ride.flow_read(-1, book({**prev, **last}), close)["ok"] is True
    strong = {m: (60, 40) for m in range(close - 20, close - 5)}      # +0.20 counter buying: not a weak pullback
    assert ride.flow_read(-1, book({**strong, **last}), close)["ok"] is False

def test_flow_nifty_gc_disagreement_and_absent_gc():
    close = 600
    b = book({**{m: (50, 50) for m in range(close - 20, close - 5)}, **{m: (40, 60) for m in range(close - 5, close)}})
    gc_up = [{"t": (close - 5) * 60000 - ride.IST_MS, "buy": 60, "sell": 40}]          # +0.20 on the same 5 min
    assert ride.flow_read(-1, b, close, gc_up)["why"] == "sources disagree"
    assert ride.flow_read(-1, b, close, [])["ok"] is True                              # absent GC is not disagreement

def bar(s, h, l, c, vw, sg):
    return {"s": s, "e": s + 180, "o": c, "h": h, "l": l, "c": c, "v": 10, "delta": -5, "vwap": vw, "sig": sg}

def test_trade_line_is_higher_of_trigger_high_and_vwap_plus_quarter_sigma_with_half_sigma_floor():
    trig = bar(36000, 22510, 22480, 22490, 22500, 20)
    tr = ride.trade(-1, trig, bar(36180, 22495, 22470, 22475, 22500, 20))
    assert tr["line0"] == 22510 + 5 and tr["E"] == 22475
    tight = ride.trade(-1, bar(36000, 22471, 22468, 22469, 22470, 20), bar(36180, 22472, 22468, 22470, 22470, 20))
    assert tight["line0"] == 22470 + 10                                # 22471+5 < E+0.5σ: the floor wins
```
- [ ] **Step 2:** run `python -m pytest -q test_ride.py`. Expected: FAIL, no module `ride`.
- [ ] **Step 3: Implement** `ride.py` (head and these functions):
```python
"""ride.py -- RIDE, her second setup: READ-V2 §E's trend pullback + OI + FLOW, and her hold (research-findings §1j).

THE BINDING TEXT is docs/setup-review/RIDE-PREREG.md (sha256 dcb306a1...aff7e). Every number is that file's, fixed
before any outcome existed; none is to be grid-searched. Pure: no I/O, no clock. Causal: every read at a bar uses data
at or before that bar's close. DESCRIPTIVE ONLY: no hit rate anywhere.
"""
from __future__ import annotations

import confluence
import frame_v2
import fronts

REV = "ride-1 (RIDE-PREREG dcb306a1)"
TILT, FAST, SLOW = confluence.TILT, confluence.FAST, confluence.SLOW   # §0: the same FLOW numbers as §1i
WINDOW_BARS, WINDOW_MIN = 3, 9
CUTOFF, MARK = 15 * 60, 15 * 60 + 20
LINE_BUF, MIN_RISK = 0.25, 0.5
IST_MS = confluence.IST_MS
hm = confluence.hm


def entries(b3, rows, basis):
    """Every §E ENTRY, found causally: frame_v2.plan on the bars closed by each bar's end and the READ rows marked by
    then (read's rows are prefix-stable: test_read.test_live_equals_replay_no_look_ahead)."""
    out = []
    for k in range(1, len(b3) + 1):
        now = b3[k - 1]["e"]
        rk = [r for r in rows or () if isinstance(r.get("t"), str) and frame_v2._sec(r["t"]) <= now]
        p, _why = frame_v2.plan(b3[:k], rk, basis, now)
        t = frame_v2.hm(now)
        for ev in (p or {}).get("rows") or ():
            if ev.get("what") == "ENTRY" and ev.get("t") == t:
                out.append({"i": k - 1, "t": t, "d": p["d"], "word": p.get("word"), "px": ev.get("px")})
    return out


def oi_read(d, minutes, peaks, at):
    """§1 OI: the trend-side front BUILDING and the defending front not BUILDING. Stale -> could not check."""
    cut = fronts.cut(minutes, at)
    stale = fronts.stale(cut, at)
    out = {"ok": None, "why": stale, "trend": None, "defend": None}
    if stale:
        return out
    rows = fronts.read(cut, confluence._upto(peaks, at))
    tside, dside = ("CE", "PE") if d < 0 else ("PE", "CE")
    t, f = fronts.side_front(rows, tside), fronts.side_front(rows, dside)
    if t is None or f is None:
        out["why"] = f"no {tside if t is None else dside} front read at {at}"
        return out
    out["trend"] = {"k": t["k"], "side": tside, "state": t["state"]}
    out["defend"] = {"k": f["k"], "side": dside, "state": f["state"]}
    out["ok"] = t["state"] == fronts.BUILDING and f["state"] != fronts.BUILDING
    out["why"] = f"{tside} {t['k']:.0f} {t['state']} · {dside} {f['k']:.0f} {f['state']}"
    return out


def flow_read(d, book, close, gc=None):
    """§1 FLOW at a bar closing at IST minute `close`."""
    t5, w5 = confluence.tilt(book, close - FAST, close)
    t15, w15 = confluence.tilt(book, close - FAST - SLOW, close - FAST)
    g = confluence.gc_tilt(gc, close) if gc is not None else None
    out = {"ok": None, "t5": t5, "t15": t15, "gc": g, "why": w5 or w15}
    if t5 is None or t15 is None:
        return out
    out["ok"] = (t5 <= -TILT and t15 <= TILT) if d < 0 else (t5 >= TILT and t15 >= -TILT)
    out["why"] = "trend aggression back" if out["ok"] else "no return"
    if out["ok"] and g is not None and (g >= TILT if d < 0 else g <= -TILT):
        out.update(ok=False, why="sources disagree")
    return out


def trade(d, trig, b):
    """§2 initial HARD LINE: beyond the higher (lower) of the §E trigger bar's extreme and VWAP at entry by 0.25 sigma;
    risk at least 0.5 sigma; sigma frozen at entry."""
    E, vw, sg = b["c"], b["vwap"], b["sig"]
    if d < 0:
        line = max(max(trig["h"], vw) + LINE_BUF * sg, E + MIN_RISK * sg)
    else:
        line = min(min(trig["l"], vw) - LINE_BUF * sg, E - MIN_RISK * sg)
    return {"E": E, "sigma": round(sg, 4), "line0": round(line, 4)}


def evaluate(ent, b3, chain, book, gc=None):
    """LOCATION / OI / FLOW at the §E ENTRY bar and the next 3 bars (<= 9 min); the RIDE entry or None."""
    i, d = ent["i"], ent["d"]
    c0 = b3[i]["e"] // 60
    bars, entry = [], None
    for j in range(i, min(i + WINDOW_BARS + 1, len(b3))):
        b = b3[j]
        close = b["e"] // 60
        if close - c0 > WINDOW_MIN:
            break
        side_ok = b["c"] < b["vwap"] if d < 0 else b["c"] > b["vwap"]
        ev = {"t": frame_v2.hm(b["e"]), "loc": {"ok": side_ok, "c": b["c"], "vwap": round(b["vwap"], 2)},
              "oi": oi_read(d, chain[0], chain[1], hm(close - 1)),
              "flow": flow_read(d, book, close, gc), "late": close > CUTOFF}
        bars.append(ev)
        if entry is None and not ev["late"] and side_ok and ev["oi"]["ok"] and ev["flow"]["ok"]:
            entry = dict(trade(d, b3[i], b), t=ev["t"], bar=j - i)
    return {"bars": bars, "entry": entry}
```
- [ ] **Step 4:** run `python -m pytest -q test_ride.py`. Expected: PASS.

### Task 3: `ride.py` — the hold and exit (her rules), expressions, stamps, row

**Files:**
- Modify: `ride.py` (append).
- Test: `test_ride.py` (append).

**Interfaces:**
- **Produces:**
  - `ride.closes_after(d, entry_close, b3, rows, chain) -> {close_min: {"c", "flip_fut", "trend_state"}}`;
  - `ride.outcome(d, tr, start_min, ones, closes) -> {"exit", "how" in {"line", "gave_up", "mark"}, "exit_t", "R",
    "stalled": [...]}`;
  - `ride.expressions(d, minutes, entry_at, exit_at) -> dict|None`;
  - `ride.stamps(ent, b3, rows, tr, peers=None, dte=None) -> dict`;
  - `ride.row(ent, b3, rows, chain, book, gc=None, peers=None, dte=None) -> dict` (no outcome).

- [ ] **Step 1: Write the failing tests**
```python
def one(m, h, l, c):
    return {"s": m * 60, "e": m * 60 + 60, "h": h, "l": l, "c": c}

TR = {"E": 22475.0, "sigma": 20.0, "line0": 22515.0}

def test_line_exit_is_intrabar_never_a_close():
    ones = [one(601, 22480, 22470, 22472), one(602, 22516, 22470, 22471)]    # high pokes the line, closes back below
    r = ride.outcome(-1, TR, 601, ones, {})
    assert r["how"] == "line" and r["exit"] == 22515.0 and r["R"] == -1.0

def test_trail_moves_only_toward_price():
    closes = {603: {"c": 22440, "flip_fut": 22480, "trend_state": fronts.BUILDING},   # line -> 22485
              606: {"c": 22430, "flip_fut": 22500, "trend_state": fronts.BUILDING}}   # farther: ignored
    ones = [one(m, 22450, 22420, 22440) for m in range(601, 607)] + [one(607, 22486, 22430, 22480)]
    r = ride.outcome(-1, TR, 601, ones, closes)
    assert r["how"] == "line" and r["exit"] == 22485.0
    assert round(r["R"], 4) == round((22475 - 22485) / 40, 4)              # initial risk throughout

def test_stalled_holds_and_unwinding_exits_at_that_close():
    closes = {603: {"c": 22440, "flip_fut": None, "trend_state": fronts.STALLED},
              606: {"c": 22420, "flip_fut": None, "trend_state": fronts.UNWINDING}}
    ones = [one(m, 22450, 22410, 22440 if m < 605 else 22420) for m in range(601, 610)]
    r = ride.outcome(-1, TR, 601, ones, closes)
    assert r["how"] == "gave_up" and r["exit"] == 22420 and r["exit_t"] == "10:06"
    assert r["stalled"] == ["10:03"]

def test_marked_at_1520_when_nothing_fires():
    ones = [one(m, 22450, 22440, 22445) for m in range(601, 925)]
    r = ride.outcome(-1, TR, 601, ones, {})
    assert r["how"] == "mark" and r["exit_t"] == "15:19"

def test_no_look_ahead_entry_is_identical_when_inputs_are_cut_at_the_bar(monkeypatch):
    """evaluate() at a §E entry gives the same answer whether book/chain hold the whole day or only data to the
    window's last close."""
    import random
    random.seed(7)
    close0 = 603                                       # the §E bar (b3[1], 10:00-10:03) closes at minute 603
    full = {m: (random.randint(30, 70), random.randint(30, 70)) for m in range(560, 700)}
    cut = {m: v for m, v in full.items() if m < close0 + 9}            # the window's last close is 612
    monkeypatch.setattr(fronts, "cut", lambda m, at: {k: v for k, v in m.items() if k <= at})
    monkeypatch.setattr(fronts, "stale", lambda c, at: None)
    monkeypatch.setattr(fronts, "read", lambda c, p: [front("CE", fronts.BUILDING if len(c) % 2 else fronts.STALLED),
                                                      front("PE", fronts.STALLED)])
    grid = {hm: {} for hm in (f"{h:02d}:{m:02d}" for h in range(9, 12) for m in range(60))}
    b3 = [bar(36000 - 180 + 180 * j, 22510, 22470, 22480, 22500, 20) for j in range(6)]
    ent = {"i": 1, "d": -1}
    a = ride.evaluate(ent, b3, (grid, {}), book(full))
    b = ride.evaluate(ent, b3, ({k: v for k, v in grid.items() if k <= "10:11"}, {}), book(cut))  # last OI read 10:11
    assert a == b
```
- [ ] **Step 2:** run `python -m pytest -q test_ride.py`. Expected: the new tests FAIL (no `outcome` / `closes_after`).
- [ ] **Step 3: Implement** (append to `ride.py`):
```python
def flip_fut(row):
    """The READ row's FLIP in futures (its own basis), or None."""
    f, bv = row.get("flip"), row.get("basis")
    return None if f is None or bv is None else f + bv


def closes_after(d, entry_close, b3, rows, chain):
    """For every 3-min close after entry: its close, the READ's FLIP in fut as of it, and the trend-side front's
    state at its last minute (fronts, §1d's parameters). Data at or before each close only."""
    out = {}
    tside = "CE" if d < 0 else "PE"
    for b in b3:
        close = b["e"] // 60
        if close <= entry_close or close > MARK:
            continue
        rk = [r for r in rows or () if isinstance(r.get("t"), str) and frame_v2._sec(r["t"]) <= b["e"]]
        at = hm(close - 1)
        cut = fronts.cut(chain[0], at)
        st = None
        if not fronts.stale(cut, at):
            f = fronts.side_front(fronts.read(cut, confluence._upto(chain[1], at)), tside)
            st = f["state"] if f else None
        out[close] = {"c": b["c"], "flip_fut": flip_fut(rk[-1]) if rk else None, "trend_state": st}
    return out


def outcome(d, tr, start, ones, closes):
    """§2: the first of the HARD LINE (intrabar, 1-min), SOMEBODY GAVE UP (the trend-side front UNWINDING at a 3-min
    close, exit at that close), or 15:20 (the last 1-min close before it). The line trails to FLIP + 0.25 sigma only
    toward price. R on the initial risk. STALLED is stamped, never an exit. SCORER ONLY."""
    E, sg, line = tr["E"], tr["sigma"], tr["line0"]
    risk = abs(tr["line0"] - E)
    stalled, ex, last = [], None, None
    for b in ones or ():
        m = b["s"] // 60
        if m < start or m >= MARK:
            continue
        last = b
        if (b["h"] >= line) if d < 0 else (b["l"] <= line):
            ex = (line, "line", hm(m + 1))
            break
        ev = closes.get(m + 1)
        if ev:
            if ev["trend_state"] == fronts.UNWINDING:
                ex = (ev["c"], "gave_up", hm(m + 1))
                break
            if ev["trend_state"] == fronts.STALLED:
                stalled.append(hm(m + 1))
            f = ev["flip_fut"]
            if f is not None:
                cand = f + LINE_BUF * sg if d < 0 else f - LINE_BUF * sg
                if (cand < line and cand > ev["c"]) if d < 0 else (cand > line and cand < ev["c"]):
                    line = cand
    if ex is None:
        if last is None:
            return None
        ex = (last["c"], "mark", hm(last["s"] // 60))
    R = (E - ex[0]) / risk if d < 0 else (ex[0] - E) / risk
    return {"exit": round(ex[0], 4), "how": ex[1], "exit_t": ex[2], "R": round(R, 4), "stalled": stalled}


def expressions(d, minutes, entry_at, exit_at):
    """§5, equal weight: buy the with-trend ATM, buy the with-trend 1-strike ITM, sell the against-trend ATM -- the
    same strikes' recorded LTPs at entry and exit, premium points."""
    a, b = confluence._at_minute(minutes, entry_at), confluence._at_minute(minutes, exit_at)
    if a is None or b is None:
        return None
    k = confluence._atm_k(a)
    ks = sorted(a.get("px") or {})
    if k is None or k not in ks:
        return None
    j = ks.index(k)
    itm = ks[j + 1] if d < 0 and j + 1 < len(ks) else ks[j - 1] if d > 0 and j > 0 else None
    leg = 1 if d < 0 else 0                        # px[k] = (ce, pe): buy PE on a down ride, CE on an up ride
    opp = 1 - leg

    def px(rec, kk, i):
        v = (rec.get("px") or {}).get(kk)
        return None if v is None else v[i]
    out = {"k": k, "itm_k": itm, "buy": "PE" if d < 0 else "CE", "sell": "CE" if d < 0 else "PE"}
    for name, kk, i, sign in (("buy_atm", k, leg, 1), ("buy_itm", itm, leg, 1), ("sell_atm", k, opp, -1)):
        p0, p1 = (None, None) if kk is None else (px(a, kk, i), px(b, kk, i))
        out[name] = None if p0 is None or p1 is None else {"in": p0, "out": p1, "pts": round(sign * (p1 - p0), 2)}
    return out


def stamps(ent, b3, rows, tr, peers=None, dte=None):
    """§1 stamps at the RIDE entry (or the §E bar): never gating."""
    i = ent["i"]
    e = b3[i]["e"]
    rk = [r for r in rows or () if isinstance(r.get("t"), str) and frame_v2._sec(r["t"]) <= e]
    last = rk[-1] if rk else {}
    since = last.get("since")
    s0 = frame_v2._sec(since) if isinstance(since, str) else None
    leg = [b for b in b3[: i + 1] if s0 is not None and b["s"] >= s0]
    d = ent["d"]
    start = leg[0]["o"] if leg else None
    ext = (min(b["l"] for b in leg) if d < 0 else max(b["h"] for b in leg)) if leg else None
    pull = b3[i]["h"] if d < 0 else b3[i]["l"]
    depth = (None if start is None or ext is None or start == ext
             else round(abs(pull - ext) / abs(start - ext) * 100, 1))
    ff = flip_fut(last) if last else None
    return {"time": ent["t"], "word": ent.get("word"), "since": since, "dte": dte,
            "leg_age_min": None if s0 is None else (e - s0) // 60,
            "pullback_depth_pct": depth, "flip_dist": None if ff is None or tr is None else round(ff - tr["E"], 1),
            "peers": peers}


def row(ent, b3, rows, chain, book, gc=None, peers=None, dte=None, pullback_no=None):
    """The forward log's row (and the scorer's): everything known by the window's last close. No outcome."""
    ev = evaluate(ent, b3, chain, book, gc)
    return {"setup": "RIDE", "t": ent["t"], "d": ent["d"], "word": ent.get("word"), "bars": ev["bars"],
            "entry": ev["entry"],
            "stamps": dict(stamps(ent, b3, rows, ev["entry"], peers, dte), pullback_no=pullback_no), "rev": REV}
```
- [ ] **Step 4:** run `python -m pytest -q test_ride.py`. Expected: PASS. Then add one test for `expressions` (a
  synthetic two-minute chain with `px`: ATM, ITM and opposite legs give the right `pts` signs) and one for
  `entries()` (monkeypatch `frame_v2.plan` to return an ENTRY on the 3rd bar only; assert one entry with `i == 2`).
  Run again; expected PASS.

### Task 4: `confluence_log.py` — RIDE inputs, the RIDE row and the fail-soft live log

**Files:**
- Modify: `confluence_log.py`.
- Test: `test_confluence.py` (append).

**Interfaces:**
- **Consumes:** `ride.*`; `server._read_gc_pre`; `v2feed.Day`; `read.from_v2`, `read.timeline`; `frame_v2.cut`,
  `bars3`, `basis_band` / `parity_basis` exactly as `frame_v2.compose` computes `basis`; `ux_log.read_bars`;
  `confluence_log.inputs`.
- **Produces:**
  - `confluence_log.ride_inputs(index, day, now=None) -> {"b3", "ones", "rows", "basis", "chain", "book", "gc",
    "dte", "peers_rows"}`;
  - `confluence_log.build_ride(index, day, ent, inp) -> row`;
  - `confluence_log.log_ride(index, now=None, path=PATH) -> int`.
  - FADE's `build()` rows gain `"setup": "FADE"`.

- [ ] **Step 1: Write the failing test** (append to `test_confluence.py`)
```python
def test_log_ride_is_fail_soft_and_write_once(tmp_path, monkeypatch):
    import confluence_log, ride
    p = tmp_path / "c.jsonl"
    monkeypatch.setattr(confluence_log, "ride_inputs", lambda idx, day, now=None: (_ for _ in ()).throw(OSError("x")))
    assert confluence_log.log_ride("NIFTY", now="11:00", path=str(p)) == 0        # an error never escapes
    inp = {"b3": [], "ones": [], "rows": [], "basis": None, "chain": ({}, {}), "book": ({}, set(), set()),
           "gc": None, "dte": 3, "peers_rows": {}}
    monkeypatch.setattr(confluence_log, "ride_inputs", lambda idx, day, now=None: inp)
    monkeypatch.setattr(ride, "entries", lambda b3, rows, basis: [{"i": 0, "t": "10:00", "d": -1, "word": "TREND", "px": 1}])
    monkeypatch.setattr(confluence_log, "build_ride", lambda idx, day, ent, inp: {"setup": "RIDE", "day": day, "index": idx,
                                                                               "t": ent["t"], "d": ent["d"]})
    monkeypatch.setattr(confluence_log, "_ride_due", lambda ent, b3, nowm: True)
    assert confluence_log.log_ride("NIFTY", now="11:00", path=str(p)) == 1
    assert confluence_log.log_ride("NIFTY", now="11:03", path=str(p)) == 0        # write-once
    assert '"setup": "RIDE"' in p.read_text()
```
- [ ] **Step 2:** run `python -m pytest -q test_confluence.py -k log_ride`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - **`ride_inputs`** mirrors `server._v2_parts` up to `compose`: `v2feed.Day(day, v2feed.DATA)`, `.refresh()`,
    `s = D.idx[index]`, `X = frame_v2.cut(read.from_v2(s, lot, server._read_gc_pre(index, day, s, lot)), now_sec)`,
    `tl = read.timeline(X, ux, None, now_sec)`.
    - `b3 = frame_v2.bars3(X["bars"], lot, now_sec)` and `ones = frame_v2.bars3(X["bars"], lot, now_sec, width=60)`.
    - `basis` is computed the way `compose` computes it. Read `compose` and copy its two lines.
    - FADE's `inputs(index, day)` supplies `chain`, `book` and `gc`.
    - `peers_rows` = each other index's `tl["rows"]` built the same way.
    - `dte = frame_v2.dte(day, s.fut_expiry)`.
    - Put the `v2feed` / `server` imports inside the function so that importing `confluence_log` stays light.
  - **`build_ride(index, day, ent, inp)`** returns `{"day", "index", **ride.row(...)}`.
    - `peers` = `{idx: last row word/dir at ent["t"]}`.
    - `pullback_no` = the 1-based count of `ride.entries` with the same `since` up to this one.
  - **`_ride_due(ent, b3, nowm)`** is True when the window's last bar (i+3, or the last bar) has closed and
    `nowm ≥ close + GRACE`, or `nowm ≥ CLOSE`.
  - **`log_ride(index, now=None, path=PATH)`:**
    - try/except-all returning 0;
    - throttle: at most once per 3-min bar per index (a module dict `{index: last_bar_minute}`);
    - `_seen` keys are `("RIDE", day, index, t)`;
    - appends rows the same way `log_new` does.
  - In `build()` (FADE), add `"setup": "FADE"` to the returned dict.
- [ ] **Step 4:** run `python -m pytest -q test_confluence.py test_ride.py`. Expected: PASS.

### Task 5: `tools/ride_score.py` — dry counts; `--run` gated by §6

**Files:**
- Create: `tools/ride_score.py`.
- Test: `test_ride.py` (append: `sha_ok()` False on a changed file; `--run` refuses while no cell can reach 20).

**Interfaces:**
- Consumes: `confluence_log.ride_inputs`, `confluence_log.build_ride`, `ride.entries`, `confluence.verdict`.
- Produces: the CLI `python tools/ride_score.py [--dry] [--run] [--rerun WHY]`.
  - **Dry, the default:** per cell (▼/▲ × NIFTY+SENSEX / BANKNIFTY), the §E entries, LOCATION ok, OI ok, OI could-not,
    FLOW ok, FLOW could-not, OI+FLOW on one bar, RIDE entries, triggers after 15:00. Plus the qualifying days and why
    others don't. **Counts only.**
  - **`--run`:**
    - refuses unless, for some cell, the dry RIDE entries plus the forward RIDE rows in `data/confluence_log.jsonl`
      reach ≥ 20;
    - prints that and exits 2 otherwise;
    - refuses if `data/confluence/ride_first_look.json` exists (one run) unless `--rerun WHY` is given;
    - every mode refuses if the prereg sha256 differs.
- [ ] **Step 1:** write the two tests. `sha_ok` takes a path. `can_run(counts, forward)` returns False for
  `{cell: 2}` and `{}`.
- [ ] **Step 2:** run them. Expected: FAIL.
- [ ] **Step 3:** implement, following the structure of `tools/confluence_score.py` (`group`, `sha_ok`, `days`,
  `collect`, `counts`, `print_dry`, `main`). The days are those on which the book, chain and v2feed ticks all exist.
- [ ] **Step 4:** run the tests. Expected: PASS. Then run `python tools/ride_score.py` (dry). Expected: a counts table
  and **no R or premium anywhere** in the output.

### Task 6: the server hook, the full suite, the anchor note

**Files:**
- Modify: `server.py`, right after the existing `confluence_log.log_new(...)` line (around 5793).
- Modify: `context/research-findings.md` §1j (append a "BUILT" line).

- [ ] **Step 1:** add the call. `log_ride` swallows its own errors; the hook also wraps it so the tape build never
  pays:
```python
                    try:
                        confluence_log.log_ride(x)      # §1j RIDE forward log: fail-soft, its own rows only
                    except Exception:
                        pass
```
- [ ] **Step 2:** run `python -m pytest -q`. Capture pytest's own exit code (not tail's). Expected: exit 0, with the
  count = the previous 1707 + the new tests.
- [ ] **Step 3:** measure one `log_ride("NIFTY", now="12:00")` against a recorded day's files with a mock path
  (`data/mock/`), as wall time. It must be ≤ 2 s per call. If it is slower, cache the per-day `v2feed.Day` in the
  module, refreshed only when its file signature changes (`D.signature()`), and re-measure.
- [ ] **Step 4:** append to research-findings §1j: "BUILT 2026-10-21: ride.py, test_ride.py, tools/ride_score.py,
  confluence_log.log_ride, server hook (fail-soft). pytest N passed. Live at her restart. Dry counts: …"
- [ ] **Step 5: No commit.** Mary commits on her word.

---

## Self-review (done while writing)
- **Spec coverage:**
  - §0 → Tasks 2 and 4 (§E via `frame_v2.plan`; `fronts`; FLOW reuse).
  - §1 → Task 2 (OI, FLOW, entry window, VWAP side, 15:00) and Task 3 (stamps).
  - §2 → Task 3 (line, trail, gave up, 15:20, initial-risk R, STALLED stamped).
  - §3 control → Task 5: the dry run counts §E entries; at `--run`, §E entries are scored with the same `outcome`
    from the §E bar's close using `trade(d, b3[i], b3[i])`.
  - §4 → `confluence.verdict` (identical bar).
  - §5 → `ride.expressions`.
  - §6 → Task 5's gate and Task 4's forward log.
  - §7 → no change to §E's rows.
- **Type consistency:**
  - `closes` is keyed by IST minute; `outcome` reads `closes.get(m + 1)` for the 1-min bar labelled `m` (its close).
  - `b3[i]["e"] // 60` is the close minute everywhere.
  - `hm()` is `confluence.hm` (minutes) and `frame_v2.hm` is seconds. **Both are used deliberately, and named.**
- **Placeholders:** none. Task 4's `basis` points at `compose`'s two lines to copy, because a pasted copy here could
  drift from the source.
