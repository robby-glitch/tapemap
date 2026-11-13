# Execute the Edge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build her zone-execution plan (spec `docs/superpowers/specs/2026-11-13-execute-edge-design.md`, approved 14 Nov 2026) as one pure brain module, carried on the Jarvis card and drawn by the Dext extension.

**Architecture:** `execute.py` (tapemap root) computes, from the day's exchange 1-min futures candles, Dext delta and yesterday's candles, her zone triggers, the four checks, three plan lines (A / B / C) and the six-state line + ticket. Two small I/O adapters sit at its bottom (`for_frame`, `append_log`). The server attaches the compact block to every NIFTY Jarvis frame (`/api/jarvis`, `/api/jarvis/card`) and appends the live forward log `data/exec/<day>.jsonl`. The extension 0.9.3 renders the block verbatim.

**Tech Stack:** Python 3.13 stdlib + the repo's `ruler`, `band_rotation`, `jarvis_log`, `server`; plain JS (the extension's `lib/jarvis.js`, `lib/panel-render.js`), node test scripts.

## Global Constraints

- Display only; never an order path (house rule 10).
- Never start, stop or restart the TapeMap server; a server change goes live only when she restarts after a close.
- No change to the live tool in market hours (Mon–Fri 09:15–15:40 IST).
- **Commit only on her word**: every task ends with the files left uncommitted.
- `data/trigger_log.jsonl` is read-only.
- Every futures level carries `f`. Counts and points only, never a rate. Light mode only.
- A value that cannot be read says "could not check: …" and never counts as ✓ or ✗ (house rule 6).
- Constants, each with its origin: `LOCK_R = 2.0` (§1m), `TREND_MIN = 120` (A313/A320), `ROOM_S = 1.0` (A315/A329), `NEAR = 2` (A332), monthly expiry = the month's last Tuesday (A318).

---

### Task 1: execute.py — the pieces (triggers, checks, helpers)

**Files:** Create `execute.py`; Test `test_execute.py`.

**Interfaces — Produces:** `M(t)`, `HM(m)`, `prev_weekday(day)`, `last_tuesday(y, m)`, `contract_changed(day, prev_day) -> bool`, `gap(ones, prev_ones, changed) -> {ok: True|False|None, text, ...}`, `triggers(blist) -> (signals, armed)`, `vwap_untouched(blist, t0) -> int|None`, `flow_sum(delta, e) -> float|None`, `_signals(blist, T, delta, gp) -> [signal]`; a signal is `{t, side, px, level, ext, xb, first, narm, S, n, risk, z, fs, vw, chk: {GAP, TREND, FLOW}, bad}`.

- [ ] **Step 1: Write the failing tests** — `test_execute.py`:

```python
"""EXECUTE THE EDGE (execute.py): synthetic days only, no repo data. Spec docs/superpowers/specs/2026-11-13-execute-edge-design.md."""
import execute as X


def day_ones(path):
    """1-min candles 09:15..15:29 from {HH:MM: price} anchors, flat between them (h = l = c, so stops are exact)."""
    out, px = [], None
    for m in range(X.OPEN, 15 * 60 + 30):
        t = X.HM(m)
        px = path.get(t, px)
        out.append({"t": t, "o": px, "h": px, "l": px, "c": px, "v": 100})
    return out


def sig(t, side, px, ext, bad=False, z=1.5, **kw):
    S = -1 if side == "SELL" else 1
    e = {"t": t, "side": side, "px": px, "ext": ext, "S": S, "risk": abs(ext - px), "z": z, "bad": bad, "n": 1,
         "xb": X.M(t) - 3, "first": t, "level": px, "narm": 1, "fs": None, "vw": 30,
         "chk": {"GAP": False, "TREND": False, "FLOW": bad}}
    e.update(kw)
    return e


def test_contract_changed_on_the_day_after_a_monthly_expiry():
    assert X.contract_changed("2026-08-26", "2026-08-25")
    assert X.contract_changed("2026-09-30", "2026-09-29")
    assert X.contract_changed("2026-10-28", "2026-10-27")
    assert not X.contract_changed("2026-08-25", "2026-08-24")
    assert not X.contract_changed("2026-11-16", "2026-11-13")


def test_prev_weekday_skips_the_weekend():
    assert X.prev_weekday("2026-11-16") == "2026-11-13"
    assert X.prev_weekday("2026-11-13") == "2026-11-12"


def test_gap_reads_the_open_against_yesterday():
    prev = day_ones({"09:15": 95, "11:00": 99, "13:00": 90})
    assert X.gap(day_ones({"09:15": 100}), prev, False)["ok"] is False
    assert X.gap(day_ones({"09:15": 100}), prev, False)["text"] == "opened above yesterday's high 99f"
    assert X.gap(day_ones({"09:15": 85}), prev, False)["text"] == "opened below yesterday's low 90f"
    assert X.gap(day_ones({"09:15": 95}), prev, False)["ok"] is True
    assert X.gap(day_ones({"09:15": 95}), None, False)["ok"] is None
    assert X.gap(day_ones({"09:15": 95}), prev, True)["text"].startswith("could not check")


def test_flow_sum_from_the_bar_after_the_extreme_to_the_trigger_close():
    e = {"t": "10:03", "xb": X.M("10:00")}
    assert X.flow_sum({"10:03": -5, "10:04": 2, "10:05": None, "10:02": 99}, e) == -3
    assert X.flow_sum({}, e) is None


def test_vwap_untouched_counts_minutes_since_a_bar_held_vwap():
    bl = [{"t": X.HM(X.OPEN + 3 * k), "h": 101, "l": 99, "vwap": 100 if X.HM(X.OPEN + 3 * k) == "09:36" else 50}
          for k in range(12)]
    assert X.vwap_untouched(bl, "09:45") == 9
    assert X.vwap_untouched(bl[:4], "09:24") is None
```

- [ ] **Step 2: Run them to see them fail** — `python -m pytest -q test_execute.py` → FAIL, `ModuleNotFoundError: No module named 'execute'`.

- [ ] **Step 3: Write the module's first half** — `execute.py`:

```python
# -*- coding: utf-8 -*-
"""EXECUTE THE EDGE — her zone, executed (spec docs/superpowers/specs/2026-11-13-execute-edge-design.md, approved 14 Nov 2026).

day_state() is pure: the day's exchange 1-min futures candles (+ Dext delta, yesterday's candles) -> the six-state line, the
trigger ticket and three plan lines over the same zone triggers:
  PLAN A  every trigger; any opposite trigger ends the trade and is taken (the edge walk, look_edge_walk FLIP)
  PLAN B  her rules: four checks (GAP, TREND, LEG PAID, FLOW); a weak opposite signal neither ends the trade nor is taken
  PLAN C  PLAN B + CAREFUL FLIP (a trade in profit is ended only by a valid opposite signal with room >= 1 sigma); logged only
for_frame() and append_log() are the two I/O adapters at the bottom. Display only; never an order (house rule 10).
"""
import datetime as dt
import json
import os

import band_rotation as br
import ruler

OPEN, LAST = 9 * 60 + 15, 15 * 60   # flat by 15:00 (her practice)
LOCK_R = 2.0                         # LEG PAID: a close at 2x its own stop (hold2.LOCK_R, §1m)
TREND_MIN = 120                      # TREND: VWAP untouched this many minutes (A313; held on 37 unseen sessions, A320)
ROOM_S = 1.0                         # PLAN C: room from VWAP in her sigma (her ROOM read, A315 / A329)
NEAR = 2                             # OI: the other side's writers at ATM +- 2 strikes (A332)


def M(t):
    return int(t[:2]) * 60 + int(t[3:5])


def HM(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def prev_weekday(day):
    d = dt.date.fromisoformat(day) - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d.isoformat()


def last_tuesday(y, m):
    d = (dt.date(y, m, 28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    while d.weekday() != 1:
        d -= dt.timedelta(days=1)
    return d


def contract_changed(day, prev_day):
    """True when a monthly NIFTY futures expiry (the month's last Tuesday: 25 Aug, 29 Sep, 27 Oct 2026, A318) fell on prev_day
    or after it and before day: yesterday's candles are another contract."""
    p, d = dt.date.fromisoformat(prev_day), dt.date.fromisoformat(day)
    return p <= last_tuesday(p.year, p.month) < d


def gap(ones, prev_ones, changed):
    """GAP (A331): ok True = opened inside yesterday's futures high-low, False = outside (no fades), None = could not check."""
    if not prev_ones:
        return {"ok": None, "text": "could not check: no candles for the previous weekday"}
    if changed:
        return {"ok": None, "text": "could not check: a new futures contract since yesterday"}
    o = next((b["o"] for b in ones if b["t"] == "09:15"), None)
    if o is None:
        return {"ok": None, "text": "could not check: no 09:15 bar"}
    pv = [b for b in prev_ones if b["t"] <= "15:29"]
    hi, lo = max(b["h"] for b in pv), min(b["l"] for b in pv)
    base = {"open": o, "hi": hi, "lo": lo}
    if o > hi:
        return dict(base, ok=False, text=f"opened above yesterday's high {hi:,.0f}f")
    if o < lo:
        return dict(base, ok=False, text=f"opened below yesterday's low {lo:,.0f}f")
    return dict(base, ok=True, text="opened inside yesterday's range")


def triggers(blist):
    """Her zone on her 3-min bands by the machine's own loop (look_cause_effect.replay, lifted): (signals, armed).
    armed = {side: {first, ext, band}} for an arm still open at the last bar."""
    out, armed = [], {}
    for side, band in (("BUY", "d2"), ("SELL", "u2")):
        cur, rows = [], br.run_states(blist, stop_pts=br.OPERATOR_STOP_PTS, side=side, band=band, span=3)
        for s in rows:
            a = s.get("arm")
            if a:
                if not a["rearm"]:
                    cur = []
                cur.append((s["t"], a["extreme"], s["level"]))
            if s.get("entry") and cur:
                ref = cur[-1]                                   # the reference bar: the setup's last new extreme
                out.append({"t": s["t"], "side": side, "px": blist[s["i"]]["c"], "level": ref[2], "ext": ref[1],
                            "xb": M(ref[0]), "first": cur[0][0], "narm": len(cur)})
                cur = []
        if cur and rows and rows[-1].get("state") == "ARMED":
            armed[side] = {"first": cur[0][0], "ext": cur[-1][1], "band": band}
    return sorted(out, key=lambda r: r["t"]), armed


def vwap_untouched(blist, t0):
    """TREND: minutes since a 3-min bar from 09:30 on last held VWAP, up to the trigger bar (look_cause_effect.so_far 'vw')."""
    first = [b for b in blist if b["t"] < "09:30"]
    upto = [b for b in blist if "09:30" <= b["t"] <= t0]
    if len(first) < 5 or not upto:
        return None
    return next((3 * k for k, b in enumerate(reversed(upto)) if b.get("vwap") is not None and b["l"] <= b["vwap"] <= b["h"]),
                3 * len(upto))


def flow_sum(delta, e):
    """FLOW: Dext delta summed from the bar after the extreme to the trigger close; None = no minute readable."""
    mins = [HM(m) for m in range(e["xb"] + 3, M(e["t"]) + 3) if delta.get(HM(m)) is not None]
    return sum(delta[t] for t in mins) if mins else None


def _signals(blist, T, delta, gp):
    """Each trigger with what was known at its close: try number, risk, room (sigma), FLOW, TREND, GAP."""
    bars, n, out = {b["t"]: b for b in blist}, {"BUY": 0, "SELL": 0}, []
    for e in T:
        S = -1 if e["side"] == "SELL" else 1
        n[e["side"]] += 1
        tb = bars.get(e["t"]) or {}
        sg = (tb["u1"] - tb["vwap"]) if tb.get("u1") and tb.get("vwap") is not None else None
        fs = flow_sum(delta, e) if delta else None
        vw = vwap_untouched(blist, e["t"])
        chk = {"GAP": gp["ok"] is False, "TREND": vw is not None and vw >= TREND_MIN, "FLOW": fs is not None and S * fs <= 0}
        out.append(dict(e, S=S, n=n[e["side"]], risk=abs(e["ext"] - e["px"]), z=(S * (tb["vwap"] - e["px"]) / sg) if sg else None,
                        fs=fs, vw=vw, chk=chk, bad=any(chk.values())))
    return out
```

- [ ] **Step 4: Run the tests** — `python -m pytest -q test_execute.py` → 5 passed.
- [ ] **Step 5: Leave uncommitted** (commit only on her word).

---

### Task 2: execute.py — the three plan walks

**Files:** Modify `execute.py` (append); Test `test_execute.py` (append).

**Interfaces — Consumes:** Task 1 signals (`S`, `px`, `ext`, `bad`, `z`, `t`, `side`). **Produces:** `_walk(ones, sig, plan, upto_m=None) -> {"trades": [{t, side, px, x, why, pts, risk}], "pos": {t, side, S, px, stop, risk}|None, "won": "BUY"|"SELL"|None, "acts": {(t, side): (word, won)}}`, `plan` in `"A"|"B"|"C"`, word in `TAKEN|SKIP|HOLD|IN TRADE`.

- [ ] **Step 1: Write the failing tests** (append):

```python
def test_plan_a_flips_plan_b_holds_through_a_weak_signal():
    ones = day_ones({"09:15": 100, "10:20": 95, "10:40": 108, "11:00": 111})
    s = [sig("10:00", "SELL", 100, 110), sig("10:30", "BUY", 95, 90, bad=True)]
    a = X._walk(ones, s, "A")
    assert [(x["side"], x["why"], round(x["pts"])) for x in a["trades"]] == [("SELL", "FLIP", 5), ("BUY", "15:00", 16)]
    b = X._walk(ones, s, "B")
    assert [(x["side"], x["why"], round(x["pts"])) for x in b["trades"]] == [("SELL", "STOP", -10)]
    assert b["acts"][("10:30", "BUY")][0] == "HOLD"


def test_leg_paid_is_read_after_the_flip_for_the_entry():
    ones = day_ones({"09:15": 100, "10:20": 80, "11:30": 85, "12:30": 90})
    s = [sig("10:00", "SELL", 100, 105), sig("11:00", "BUY", 80, 75), sig("12:00", "BUY", 85, 79)]
    b = X._walk(ones, s, "B")
    assert [(x["side"], x["why"], round(x["pts"])) for x in b["trades"]] == [("SELL", "FLIP", 20)]
    assert b["won"] == "SELL"
    assert b["acts"][("11:00", "BUY")] == ("SKIP", "SELL") and b["acts"][("12:00", "BUY")][0] == "SKIP"
    assert [x["side"] for x in X._walk(ones, s, "A")["trades"]] == ["SELL", "BUY"]


def test_plan_c_keeps_a_working_trade_through_a_signal_without_room():
    ones = day_ones({"09:15": 100, "10:20": 90, "11:00": 70})
    s = [sig("10:00", "SELL", 100, 110), sig("10:30", "BUY", 90, 85, z=0.5)]
    assert [round(x["pts"]) for x in X._walk(ones, s, "C")["trades"]] == [30]
    assert [round(x["pts"]) for x in X._walk(ones, s, "B")["trades"]] == [10, -5]


def test_upto_keeps_the_trade_open():
    ones = day_ones({"09:15": 100, "10:20": 95, "10:40": 108, "11:00": 111})
    b = X._walk(ones, [sig("10:00", "SELL", 100, 110)], "B", X.M("10:45"))
    assert b["trades"] == [] and b["pos"]["side"] == "SELL" and b["pos"]["stop"] == 110
```

- [ ] **Step 2: Run them to see them fail** — 4 failed, `AttributeError: module 'execute' has no attribute '_walk'`.

- [ ] **Step 3: Append the walk** to `execute.py`:

```python
def _walk(ones, sig, plan, upto_m=None):
    """One plan over the day's signals on the 1-min candles up to upto_m (None = the whole day, flat at 15:00).
    A: any opposite signal ends the trade and is taken. B: a weak signal (any check, or LEG PAID read before the flip) neither
    ends the trade nor is taken; LEG PAID is read again after the flip for the entry. C: B, and a trade in profit is ended
    only by a signal with room >= ROOM_S. acts[(t, side)] = (TAKEN | SKIP | HOLD | IN TRADE, the LEG state it was read on)."""
    ix = {b["t"]: i for i, b in enumerate(ones)}
    ent = {}
    for e in sig:
        ie = ix.get(HM(M(e["t"]) + 2))
        if ie is not None and M(e["t"]) + 2 < LAST:
            ent.setdefault(ie, []).append(e)
    st, lastj = {"pos": None, "won": None, "trades": [], "acts": {}}, None

    def close(j, px, why):
        p = st["pos"]
        x = {"t": p["t"], "side": p["side"], "px": p["px"], "x": ones[j]["t"], "why": why, "pts": p["S"] * (px - p["px"]),
             "risk": p["risk"]}
        st["trades"].append(x)
        if plan != "A" and st["won"] is None and x["pts"] >= LOCK_R * p["risk"]:
            st["won"] = p["side"]
        st["pos"] = None

    for j, b in enumerate(ones):
        m = M(b["t"])
        if m > LAST or (upto_m is not None and m > upto_m):
            break
        hi, lo, c = b.get("h"), b.get("l"), b.get("c")
        if c is not None:
            lastj = j
        p = st["pos"]
        if p and hi is not None and lo is not None:
            if (p["S"] < 0 and hi > p["stop"]) or (p["S"] > 0 and lo < p["stop"]):
                close(j, p["stop"], "STOP")
            elif m >= LAST and c is not None:
                close(j, c, "15:00")
        for e in ent.get(j, []):
            S, key, p = e["S"], (e["t"], e["side"]), st["pos"]
            weak = plan != "A" and (e["bad"] or (st["won"] is not None and e["side"] != st["won"]))
            if p and p["S"] == -S and c is not None:
                careful = plan == "C" and p["S"] * (c - p["px"]) > 0 and e["z"] is not None and e["z"] < ROOM_S
                if weak or careful:
                    st["acts"][key] = ("HOLD", st["won"])
                    continue
                close(j, c, "FLIP")
            leg = plan != "A" and st["won"] is not None and e["side"] != st["won"]
            if st["pos"] is None and not weak and not leg:
                st["pos"] = {"t": e["t"], "side": e["side"], "S": S, "px": e["px"], "stop": e["ext"], "risk": abs(e["ext"] - e["px"])}
                st["acts"][key] = ("TAKEN", st["won"])
            elif st["pos"] is None:
                st["acts"][key] = ("SKIP", st["won"])
            else:
                st["acts"].setdefault(key, ("IN TRADE", st["won"]))
    if st["pos"] and lastj is not None and (upto_m is None or upto_m >= LAST):
        close(lastj, ones[lastj]["c"], "15:00")
    return st
```

- [ ] **Step 4: Run the tests** — 9 passed.
- [ ] **Step 5: Leave uncommitted.**

---

### Task 3: execute.py — the screen, day_state, card, log, adapters; the card carries it

**Files:** Modify `execute.py` (append), `jarvis_log.py` (`card()`'s returned dict: one key); Test `test_execute.py` (append).

**Interfaces — Produces:** `day_state(day, ones, delta=None, prev_ones=None, changed=False, upto=None, ladder=None, spot=None, step=50) -> {ok, day, upto, state, line, ticket, signals, plan_a, plan_b, plan_c, gap, why}`; `_screen(ones, sig, walks, gp, armed, upto_m, ladder, spot, step) -> (state, line, ticket|None)`; `_other_side(ladder, spot, pos, now_t, step)`; `card(ex) -> {ok, day, upto, state, line, ticket}` or `{ok: False, why}`; `log_rows(ex) -> [row with key]`; `append_log(path, rows) -> int`; `for_frame(fr) -> day_state(...)`; `jarvis_log.card(fr)["exec"] == fr.get("exec")`.

- [ ] **Step 1: Write the failing tests** (append):

```python
def test_day_state_waits_and_names_a_gap_day():
    ones = day_ones({"09:15": 100})
    assert X.day_state("2026-11-13", ones)["state"] == "DAY END"
    ex = X.day_state("2026-11-13", ones, upto="10:00")
    assert ex["ok"] and ex["state"] == "WAIT" and ex["line"] == "WAIT · no zone armed"
    ex = X.day_state("2026-11-13", ones, prev_ones=day_ones({"09:15": 95, "11:00": 99}), upto="10:00")
    assert ex["line"] == "GAP DAY · opened above yesterday's high 99f · no fades"
    assert X.day_state("2026-11-13", [])["ok"] is False


def test_screen_trigger_ticket_and_in_trade_line():
    ones = day_ones({"09:15": 100, "10:20": 95, "10:40": 108, "11:00": 111})
    s = [sig("10:00", "SELL", 100, 110, fs=-50),
         sig("10:30", "BUY", 95, 90, bad=True, fs=-40, chk={"GAP": False, "TREND": False, "FLOW": True})]
    gp = {"ok": True, "text": "opened inside yesterday's range"}
    w = {k: X._walk(ones, s, k, X.M("10:32")) for k in "ABC"}
    st, line, tk = X._screen(ones, s, w, gp, {}, X.M("10:32"), None, None, 50)
    assert st == "TRIGGER" and line == "SKIP (FLOW ✗) · HOLD SELL" and tk[-1] == line
    assert tk[0].startswith("BUY 10:30 · try 1 · entry 95f · stop 90f (5)") and "FLOW   no buyers since the bottom -40 ✗" in tk
    w = {k: X._walk(ones, s, k, X.M("10:45")) for k in "ABC"}
    st, line, tk = X._screen(ones, s, w, gp, {}, X.M("10:45"), None, None, 50)
    assert st == "IN TRADE" and line == "HOLD SELL 100f · wrong only at 110f · out on a valid BUY or 15:00" and tk is None


def test_screen_day_end_and_the_card():
    ones = day_ones({"09:15": 100, "10:20": 95})
    s = [sig("10:00", "SELL", 100, 110)]
    w = {k: X._walk(ones, s, k) for k in "ABC"}
    st, line, _ = X._screen(ones, s, w, {"ok": True, "text": ""}, {}, X.M("15:10"), None, None, 50)
    assert st == "DAY END" and line == "PLAN B +5 (1) · PLAN A +5 (1) · PLAN C +5 (1)"
    c = X.card({"ok": True, "day": "d", "upto": "15:10", "state": st, "line": line, "ticket": None, "signals": [1]})
    assert c == {"ok": True, "day": "d", "upto": "15:10", "state": st, "line": line, "ticket": None}
    assert X.card({"ok": False, "why": "x"}) == {"ok": False, "why": "x"}


def test_other_side_oi_reads_writers_near_the_money():
    lad = {"10:02": {"pe": {"24900.0": 10.0, "25000.0": 20.0, "25300.0": 5.0}},
           "10:30": {"pe": {"24900.0": 12.0, "25000.0": 25.0, "25300.0": 1.0}}}
    pos = {"t": "10:00", "S": -1}
    assert X._other_side(lad, {"10:02": 25010.0}, pos, "10:30", 50) == 7.0
    assert X._other_side(None, {}, pos, "10:30", 50) is None


def test_log_rows_and_append_log_never_write_twice(tmp_path):
    ex = {"signals": [{"t": "10:00", "side": "SELL", "b": "TAKEN"}],
          "plan_b": {"trades": [{"t": "10:00", "side": "SELL", "x": "11:00", "why": "STOP", "pts": -10.0}]}}
    rows = X.log_rows(ex)
    assert [r["key"] for r in rows] == ["S|10:00|SELL", "C|B|10:00|SELL"]
    p = str(tmp_path / "exec" / "2026-11-13.jsonl")
    assert X.append_log(p, rows) == 2 and X.append_log(p, rows) == 0


def test_for_frame_reads_the_tape_and_the_frame(monkeypatch):
    monkeypatch.setattr(X.ruler, "ones_of", lambda day, idx="NIFTY": day_ones({"09:15": 100}) if day == "2026-11-13" else [])
    ex = X.for_frame({"day": "2026-11-13", "mins": ["09:15", "10:00"], "delta": [None, 5]})
    assert ex["ok"] and ex["upto"] == "10:00" and ex["state"] == "WAIT"
    assert X.for_frame({"day": "2026-11-13", "mins": []})["ok"] is False


def test_the_jarvis_card_carries_the_block():
    import jarvis_log
    c = jarvis_log.card({"ok": True, "call": {}, "fut": [100.0], "exec": {"ok": True, "line": "WAIT · no zone armed"}})
    assert c["exec"] == {"ok": True, "line": "WAIT · no zone armed"}
```

- [ ] **Step 2: Run them to see them fail** — the 7 new tests fail (functions missing; the card has no `exec`).

- [ ] **Step 3: Append to `execute.py`:**

```python
def _live_leg(ones, ix, sig, e):
    """LIVE LEG (A328, information only): earlier opposite signals whose stop is not hit by e's entry minute, points then."""
    ie, out = ix.get(HM(M(e["t"]) + 2)), []
    if ie is None:
        return out
    for o in sig:
        if M(o["t"]) >= M(e["t"]):
            break
        io = ix.get(HM(M(o["t"]) + 2))
        if o["side"] == e["side"] or io is None:
            continue
        hit = any((o["S"] < 0 and ones[j]["h"] > o["ext"]) or (o["S"] > 0 and ones[j]["l"] < o["ext"]) for j in range(io + 1, ie + 1))
        if not hit:
            out.append(f"{o['side']} {o['t']} alive {o['S'] * (ones[ie]['c'] - o['px']):+.0f}")
    return out


def _other_side(ladder, spot, pos, now_t, step=50):
    """OI in a trade (A332, information only): the other side's writers at ATM +- NEAR strikes, entry minute -> now."""
    if not ladder or not spot:
        return None
    t0 = HM(M(pos["t"]) + 2)
    sp, A, B = spot.get(t0), ladder.get(t0), ladder.get(now_t)
    if sp is None or not A or not B:
        return None
    side, atm = ("pe" if pos["S"] < 0 else "ce"), round(sp / step) * step
    ks, a_, b_ = {atm + k * step for k in range(-NEAR, NEAR + 1)}, A.get(side) or {}, B.get(side) or {}
    ch = [b_[k] - a for k, a in a_.items() if a is not None and b_.get(k) is not None and int(float(k)) in ks]
    return sum(ch) if ch else None


def _ticket(e, gp, act, live, held):
    """The trigger ticket: the head, the four checks in the order they become known, LIVE LEG, then one word line."""
    S, opp = e["S"], ("BUY" if e["S"] < 0 else "SELL")
    who, ex = ("sellers", "top") if S < 0 else ("buyers", "bottom")
    word, won = act or ("?", None)
    mark = lambda ok: " ✓" if ok else " ✗"                                  # noqa: E731
    legbad = won is not None and e["side"] != won
    lines = [f"{e['side']} {e['t']} · try {e['n']} · entry {e['px']:,.0f}f · stop {e['ext']:,.0f}f ({e['risk']:.0f})"
             + (f" · room {e['z']:.1f}σ" if e["z"] is not None else ""),
             "GAP    " + gp["text"] + ("" if gp["ok"] is None else mark(gp["ok"])),
             "TREND  could not check: bands forming" if e["vw"] is None else
             f"TREND  VWAP untouched {e['vw']} min ✗" if e["chk"]["TREND"] else f"TREND  VWAP touched {e['vw']} min ago ✓",
             "LEG    no 2R win today ✓" if won is None else f"LEG    2R win today was a {won}" + mark(not legbad),
             "FLOW   could not check: no Dext delta" if e["fs"] is None else
             f"FLOW   {'no ' if e['chk']['FLOW'] else ''}{who} since the {ex} {e['fs']:+,.0f}" + mark(not e["chk"]["FLOW"]),
             "LIVE LEG  " + ("; ".join(live) if live else "none")]
    why = " ".join(f"{k} ✗" for k in [k for k, v in e["chk"].items() if v] + (["LEG"] if legbad else []))
    lines.append({"TAKEN": f"TAKE · hold till a valid {opp}, the stop or 15:00",
                  "HOLD": (f"SKIP ({why}) · HOLD {held}" if why else f"NOT AT THE BAND · HOLD {held}"),
                  "SKIP": f"SKIP ({why}) · wait",
                  "IN TRADE": f"IN A {e['side']} ALREADY · HOLD"}.get(word, word))
    return lines


def _screen(ones, sig, walks, gp, armed, upto_m, ladder, spot, step):
    """PLAN B speaks: DAY END > TRIGGER (a signal on the last closed 3-min bar) > IN TRADE > ARMED > OUT > WAIT."""
    ix = {b["t"]: i for i, b in enumerate(ones)}
    B, pos = walks["B"], walks["B"]["pos"]
    if upto_m >= LAST:
        pts = {k: (sum(x["pts"] for x in w["trades"]), len(w["trades"])) for k, w in walks.items()}
        return "DAY END", " · ".join(f"PLAN {k} {pts[k][0]:+.0f} ({pts[k][1]})" for k in "BAC"), None
    bar_end, last = OPEN + ((upto_m - OPEN + 1) // 3) * 3 - 1, (sig[-1] if sig else None)
    if last and M(last["t"]) + 2 == bar_end:
        tk = _ticket(last, gp, B["acts"].get((last["t"], last["side"])), _live_leg(ones, ix, sig, last), pos and pos["side"])
        return "TRIGGER", tk[-1], tk
    if pos:
        oi = _other_side(ladder, spot, pos, HM(upto_m), step)
        tail = "" if oi is None else f" · OTHER SIDE {'adding (fuel)' if oi > 0 else 'cutting (being paid)'}"
        return "IN TRADE", (f"HOLD {pos['side']} {pos['px']:,.0f}f · wrong only at {pos['stop']:,.0f}f · out on a valid "
                            f"{'BUY' if pos['S'] < 0 else 'SELL'} or 15:00{tail}"), None
    pre = f"GAP DAY · {gp['text']} · no fades" if gp["ok"] is False else ""
    if armed:
        arm = " · ".join(f"ARMED {s} · {a['band']} touched {a['first']} · extreme {a['ext']:,.0f}f" for s, a in sorted(armed.items()))
        return "ARMED", (pre + " · " if pre else "") + arm, None
    if B["trades"] and B["trades"][-1]["why"] == "STOP":
        return "OUT", (pre + " · " if pre else "") + f"STOPPED {B['trades'][-1]['pts']:+.0f} · look again", None
    return "WAIT", pre or "WAIT · no zone armed", None


def _summary(w):
    tr = w["trades"]
    return {"pts": round(sum(x["pts"] for x in tr), 1), "n": len(tr), "won": sum(1 for x in tr if x["pts"] > 0),
            "open": None if not w["pos"] else {k: w["pos"][k] for k in ("t", "side", "px", "stop")},
            "trades": [dict({k: x[k] for k in ("t", "side", "px", "x", "why")}, pts=round(x["pts"], 1)) for x in tr]}


def day_state(day, ones, delta=None, prev_ones=None, changed=False, upto=None, ladder=None, spot=None, step=50):
    """THE BRAIN, pure. ones = the day's exchange 1-min futures candles; delta = Dext delta {HH:MM: lots}; prev_ones = the
    previous weekday's candles or None; changed = a new contract since then; upto = the last minute to use (None = all)."""
    ones = [b for b in ones or () if b.get("c") is not None and b["t"] >= "09:15"]
    if not ones:
        return {"ok": False, "day": day, "why": f"could not check — no futures candles for {day}"}
    upto_m = M(upto) if upto else M(ones[-1]["t"])
    bar_end = OPEN + ((upto_m - OPEN + 1) // 3) * 3 - 1
    now = [b for b in ones if M(b["t"]) <= upto_m]
    blist = ruler.bands([b for b in ones if M(b["t"]) <= bar_end], 3)
    T, armed = triggers(blist)
    gp = gap(ones, prev_ones, changed)
    sig = _signals(blist, [e for e in T if M(e["t"]) + 2 < LAST], delta or {}, gp)
    walks = {k: _walk(now, sig, k, None if upto is None else upto_m) for k in "ABC"}
    state, line, ticket = _screen(now, sig, walks, gp, armed, upto_m, ladder, spot, step)
    ix = {b["t"]: i for i, b in enumerate(now)}
    rows = [{"t": e["t"], "side": e["side"], "px": e["px"], "ext": e["ext"], "risk": round(e["risk"], 1),
             "z": None if e["z"] is None else round(e["z"], 2), "vw": e["vw"], "fs": e["fs"], "chk": e["chk"],
             "live": _live_leg(now, ix, sig, e),
             **{k.lower(): (walks[k]["acts"].get((e["t"], e["side"])) or ("—", None))[0] for k in "ABC"}} for e in sig]
    return {"ok": True, "day": day, "upto": HM(upto_m), "state": state, "line": line, "ticket": ticket, "signals": rows,
            "plan_a": _summary(walks["A"]), "plan_b": _summary(walks["B"]), "plan_c": _summary(walks["C"]), "gap": gp, "why": []}


def card(ex):
    """The card's compact block (the ≤10 KB contract): the line and, at a trigger, the ticket."""
    if not ex.get("ok"):
        return {"ok": False, "why": ex.get("why")}
    return {k: ex.get(k) for k in ("ok", "day", "upto", "state", "line", "ticket")}


def log_rows(ex):
    """The forward log's rows: one per signal, one per closed plan trade, each with a key that never repeats."""
    rows = [dict(s, kind="signal", key=f"S|{s['t']}|{s['side']}") for s in ex.get("signals") or ()]
    for p in "abc":
        rows += [dict(x, kind="close", plan=p.upper(), key=f"C|{p.upper()}|{x['t']}|{x['side']}")
                 for x in (ex.get("plan_" + p) or {}).get("trades") or ()]
    return rows


# ---------------------------------------------------------------- the two I/O adapters

def append_log(path, rows):
    """Append the rows whose key is not in the file yet (a restart re-reads it: never twice). Returns how many were written."""
    seen = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    seen.add(json.loads(line).get("key"))
                except ValueError:
                    continue
    new = [r for r in rows if r["key"] not in seen]
    if new:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in new)
    return len(new)


def for_frame(fr):
    """A Jarvis frame (live or replay) -> day_state: the saved exchange tape (ruler.ones_of) up to the frame's last minute,
    the frame's Dext delta (no fallback: all order flow from Dext), its ladder and spot for the OI line."""
    day, mins = fr.get("day"), fr.get("mins") or []
    if not day or not mins:
        return {"ok": False, "why": "could not check — the frame has no minutes"}
    pday = prev_weekday(day)
    prev = [b for b in ruler.ones_of(pday) if b.get("c") is not None]
    return day_state(day, ruler.ones_of(day), {t: v for t, v in zip(mins, fr.get("delta") or ()) if v is not None},
                     prev if len(prev) >= 300 else None, contract_changed(day, pday), upto=mins[-1], ladder=fr.get("ladder"),
                     spot={t: v for t, v in zip(mins, fr.get("spot") or ()) if v is not None}, step=fr.get("step") or 50)
```

In `jarvis_log.py`, `card()`'s returned dict, change its last line to:

```python
            "mstate": c.get("mstate"), "action": c.get("action"), "chips": c.get("chips"), "zone": c.get("zone"), "xstate": c.get("xstate"),
            "exec": fr.get("exec")}   # EXECUTE THE EDGE (spec 2026-11-13): her plan's line + ticket, compact, verbatim
```

- [ ] **Step 4: Run the tests** — `python -m pytest -q test_execute.py` → 16 passed; then `python -m pytest -q -k jarvis_log` → pass.
- [ ] **Step 5: Leave uncommitted.**

---

### Task 4: the 60-session parity script and her replays

**Files:** Create `docs/setup-review/check_execute_parity.py`.

**Interfaces — Consumes:** `execute.day_state`, `look_cause_effect.replay / logged / load / SCRATCH / FOUND_FROM`, `look_edge_walk.walk`, `ruler.ones_of`, `docs/setup-review/candles/`.

- [ ] **Step 1: Write the script** (it is the test; it prints PASS or FAIL):

```python
# -*- coding: utf-8 -*-
"""EXECUTE THE EDGE parity (spec §6): execute.py against the record, every NIFTY session with candles. Read-only.

    python -X utf8 docs/setup-review/check_execute_parity.py                    # PASS / FAIL
    python -X utf8 docs/setup-review/check_execute_parity.py --show 2026-11-13  # her replay: the screen at every signal
"""
import functools
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import execute as X  # noqa: E402
import look_cause_effect as L  # noqa: E402
import look_edge_walk as W  # noqa: E402
import ruler  # noqa: E402


@functools.lru_cache(maxsize=None)
def candles(day):
    ex = [b for b in ruler.ones_of(day) if b.get("c") is not None]
    cf = os.path.join(HERE, "candles", f"fut_NIFTY_{day}.json")
    if len(ex) < 300 and os.path.exists(cf):
        ex = json.load(open(cf, encoding="utf-8"))["bars"]
    return tuple(ex) if len(ex) >= 300 and sum(1 for b in ex if b.get("v")) >= 300 else None


def dext():
    out = {}
    for p in sorted(glob.glob(os.path.join(L.SCRATCH, "frame_NIFTY_*.json"))):
        f = L.load(p)
        if f and f["exch"] and f["dext"] >= 0.9:
            out[f["day"]] = {t: v for t, v in zip(f["mins"], f["delta"]) if v is not None}
        del f
    return out


def state(day, delta=None, upto=None):
    pday = X.prev_weekday(day)
    prev = candles(pday)
    return X.day_state(day, list(candles(day)), delta or {}, list(prev) if prev else None, X.contract_changed(day, pday), upto=upto)


def frame(day):
    ones = list(candles(day))
    bl = ruler.bands(ones, 3)
    d = {"day": day, "mins": [b["t"] for b in ones], "fhi": [b["h"] for b in ones], "flo": [b["l"] for b in ones],
         "fut": [b["c"] for b in ones], "blist": bl, "bars": {b["t"]: b for b in bl}}
    d["ix"] = {t: i for i, t in enumerate(d["mins"])}
    return d


def show(day):
    dl = dext().get(day)
    full = state(day, dl)
    for s in full["signals"]:
        ex = state(day, dl, upto=X.HM(X.M(s["t"]) + 2))
        print(f"\n{ex['state']} at {ex['upto']}\n" + "\n".join(ex["ticket"] or [ex["line"]]))
    print(f"\n{full['line']}")


def main(argv):
    if "--show" in argv:
        show(argv[argv.index("--show") + 1])
        return 0
    days = sorted({json.loads(l).get("day") for l in open(os.path.join(ROOT, "data", "trigger_log.jsonl"), encoding="utf-8")
                   if '"NIFTY"' in l} - {None})
    days = [d for d in days if candles(d)]
    DL, bad, A, B60, BF = dext(), 0, [], [], []
    for day in days:
        ex, d = state(day), frame(day)
        mine = [(s["t"], s["side"], s["px"], s["ext"]) for s in ex["signals"]]
        ref = [(e["t"], e["side"], e["px"], e["ext"]) for e in L.replay(d) if L.M(e["t"]) + 2 < L.LAST]
        if mine != ref:
            bad += 1
            print(f"TRIGGERS differ {day}")
        a, w = [round(x["pts"], 6) for x in ex["plan_a"]["trades"]], [round(x["pts"], 6) for x in W.walk(d, "FLIP")]
        if a != w:
            bad += 1
            print(f"PLAN A differs {day}")
        A += a
        B60 += ex["plan_b"]["trades"]
        if day in DL:
            BF += state(day, DL[day])["plan_b"]["trades"]
        for s in ex["signals"]:                                     # no look-ahead: read at its own close = read at day end
            cut = state(day, upto=X.HM(X.M(s["t"]) + 2))
            c = next((y for y in cut["signals"] if (y["t"], y["side"]) == (s["t"], s["side"])), None)
            if not c or any(c[k] != s[k] for k in ("px", "ext", "z", "vw", "chk", "b")):
                bad += 1
                print(f"LOOK-AHEAD {day} {s['t']} {s['side']}")
    late = [d for d in days if d >= L.FOUND_FROM]
    logged = {x for x in L.logged(set(late)) if L.M(x[1]) + 2 < L.LAST}
    ours = {(d, s["t"], s["side"]) for d in late for s in state(d)["signals"]}
    P = lambda xs: sum(x["pts"] for x in xs)                         # noqa: E731
    print(f"{len(days)} sessions · trigger log from {L.FOUND_FROM}: logged {len(logged)}, matched {len(logged & ours)}, "
          f"ours not logged {len(ours - logged)}")
    print(f"PLAN A: {len(A)} trades {sum(A):+.0f} (expected 257, +1,028)")
    print(f"PLAN B, every day without Dext: {len(B60)} trades {P(B60):+.0f} (expected 119, +1,650)")
    print(f"PLAN B, the order-flow days with Dext: {len(BF)} trades {P(BF):+.0f} (expected 24, +1,260)")
    ok = (bad == 0 and logged <= ours and len(A) == 257 and abs(sum(A) - 1028) < 1 and len(B60) == 119
          and abs(P(B60) - 1650) < 1 and len(BF) == 24 and abs(P(BF) - 1260) < 1)
    print("PASS" if ok else f"FAIL ({bad} differences)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 2: Run it** — `python -X utf8 docs/setup-review/check_execute_parity.py` → the three expected lines and `PASS`. A difference names the day: fix `execute.py`, never the expected numbers.
- [ ] **Step 3: Her replays** — `--show 2026-11-13`, then 11-12 and 11-11: one TRIGGER block per signal, then the DAY END line.
- [ ] **Step 4: Leave uncommitted.**

---

### Task 5: the server carries the block and writes the forward log

**Files:** Modify `server.py` (one new function above `def _jarvis_reply(q):`, one call inside it).

**Interfaces — Consumes:** `execute.for_frame / card / log_rows / append_log`, `_hold_list()`. **Produces:** every NIFTY Jarvis frame has `exec`; `/api/jarvis/card` passes it (Task 3); live frames append `data/exec/<day>.jsonl`.

- [ ] **Step 1: Add above `def _jarvis_reply(q):`**

```python
EXEC_DIR = os.path.join("data", "exec")       # EXECUTE THE EDGE's forward log, <day>.jsonl (spec 2026-11-13 §5)


def _exec_attach(fr, live):
    """EXECUTE THE EDGE (spec 2026-11-13, approved 14 Nov): her plan on this NIFTY frame -> the card's compact block; when live,
    the forward log data/exec/<day>.jsonl. Fail-soft: the frame and the card never wait on it or fall with it."""
    import execute
    try:
        ex = execute.for_frame(fr)
    except Exception as e:                          # one bad build: said on the card, retried next pass
        log.exception("execute")
        return {"ok": False, "why": f"could not check — the plan failed ({type(e).__name__})"}
    if live and ex.get("ok"):
        try:
            execute.append_log(os.path.join(EXEC_DIR, f"{fr['day']}.jsonl"), execute.log_rows(ex))
        except Exception:
            log.exception("execute log")
    c = execute.card(ex)
    if live and c.get("state") == "DAY END":       # her marked trades are options (strike, side, role): a count, not points
        c["line"] += f" · YOU {sum(1 for t in _hold_list() if t.get('idx') == 'NIFTY')} marked"
    return c
```

- [ ] **Step 2: Call it** in `_jarvis_reply`, right after the build line:

```python
        out = dict(jarvis.build(day, idx, upto, fill), live=live, asof=d.strftime("%H:%M:%S"))
        if idx == "NIFTY" and out.get("ok") and out.get("mins"):
            out["exec"] = _exec_attach(out, live)      # EXECUTE THE EDGE: her plan beside Jarvis's word, never the word
```

- [ ] **Step 3: Check in-process on a past day** (no server started; outside market hours):

```bash
python -X utf8 -c "import server, json; r = server._jarvis_reply({'idx': ['NIFTY'], 'day': ['2026-11-13'], 'upto': ['10:57']}); print(json.dumps(r.get('exec'), ensure_ascii=False, indent=1))"
```
Expected: `{"ok": true, "day": "2026-11-13", "upto": "10:56", "state": "TRIGGER", ...}` with the 10:54 SELL ticket; nothing written under `data/exec/` (a replay is not live).

- [ ] **Step 4: Run the suite** — `python -m pytest -q` → all pass except the known flaky `test_v2feed` serve-cache (NOTEPAD A49).
- [ ] **Step 5: Leave uncommitted.** Live only after her restart after a close.

---

### Task 6: the Dext extension draws the block (0.9.3)

**Files (in `C:\Users\kaam\Desktop\dext extension\dext-decoder\dext-decoder`):** Modify `lib/jarvis.js` (`cardFace`, `face`, `panel`), `lib/panel-render.js` (`jarvis`), `sidepanel.css`, `manifest.json`; Create `test/exec.test.js`.

**Interfaces — Consumes:** the card's `exec`. **Produces:** `face.exec = {state, line, ticket[]} | {why} | null`; `panel(...).exec`; the renderer's `<div class="jx">` before the word.

- [ ] **Step 1: Write the failing test** — `test/exec.test.js`:

```js
// node test/exec.test.js -- EXECUTE THE EDGE on the Dext panel (0.9.3): the card's exec block -> face -> panel -> html, verbatim.
const J = require('../lib/jarvis.js'), R = require('../lib/panel-render.js'), V = require('./fixtures/views.js');
const CARD = require('./fixtures/jarvis-card-contract.json');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.log('  FAIL', m); } };
const clone = o => JSON.parse(JSON.stringify(o));
const IST = 19800000, NOW = Date.parse('2026-11-02T10:43:05Z') - IST;
const panelOf = f => J.panel({ idx: 'NIFTY', face: f, at: NOW, err: null }, NOW);
const htmlOf = p => { const v = clone(V.live); v.jarvis = p; return R.html([v], { tab: 'dext' }); };
{
  const cd = clone(CARD);
  cd.exec = { ok: true, day: cd.day, upto: '10:56', state: 'TRIGGER', line: 'TAKE · hold till a valid BUY, the stop or 15:00',
    ticket: ['SELL 10:54 · try 2 · entry 25,250f · stop 25,285f (35) · room 1.3σ', "GAP    opened inside yesterday's range ✓",
      'TAKE · hold till a valid BUY, the stop or 15:00'] };
  const f = J.face(cd, 'card');
  ok(f.ok && f.exec && f.exec.state === 'TRIGGER' && f.exec.ticket.length === 3, 'face carries exec verbatim');
  const p = panelOf(f);
  ok(p.exec && p.exec.line === cd.exec.line, 'panel carries the line');
  const h = htmlOf(p);
  ok(h.includes('class="jx"') && h.includes('room 1.3σ') && h.indexOf('class="jx"') < h.indexOf('class="jw"'), 'the plan block first, the ticket verbatim');
  ok((h.match(/TAKE · hold till a valid BUY/g) || []).length === 1, 'the word line once, not twice');
}
{
  const f = J.face(clone(CARD), 'card');
  ok(f.ok && f.exec === null, 'an older card without exec: no block in the face');
  ok(!htmlOf(panelOf(f)).includes('class="jx"'), 'no exec, no block drawn');
}
{
  const cd = clone(CARD); cd.exec = { ok: false, why: 'could not check — the plan failed (KeyError)' };
  const f = J.face(cd, 'card');
  ok(f.exec && f.exec.why === cd.exec.why && htmlOf(panelOf(f)).includes('the plan failed'), 'a failed plan says why, verbatim');
}
console.log(`exec: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
```

- [ ] **Step 2: Run it to see it fail** — `node test/exec.test.js` → FAIL lines, exit 1.

- [ ] **Step 3: Implement.** In `lib/jarvis.js`, above `function cardFace(cd) {`:

```js
  // EXECUTE THE EDGE (0.9.3): TapeMap's plan block, verbatim — {state, line, ticket[]}; {why} when it could not run; null on an older card
  const execOf = x => (!x || typeof x !== 'object' ? null : x.ok ? { state: str(x.state), line: str(x.line), ticket: strs(x.ticket) }
    : { why: str(x.why) || 'could not check — the plan gave no reason' });
```
In `cardFace`'s returned object change `fut: null, spot: null, vwap: null, sd: null, step: null };` to `fut: null, spot: null, vwap: null, sd: null, step: null, exec: execOf(cd.exec) };`. In `face`'s frame return (`return { ok: true, src: 'frame', idx: str(fr.idx), …`) insert `exec: execOf(fr.exec),` after `src: 'frame',`. In `panel`: add `exec: null,` after `brief: null,` in the `out` defaults, and `exec: f.exec || null,` after `pushes,` in the final `Object.assign`.

In `lib/panel-render.js` `jarvis(j, key, ui)`, right after `let out = \`<div class="jv${j.grey ? ' grey' : ''}">\` + hl(j.health);` add:

```js
    const x = j.exec;   // EXECUTE THE EDGE (0.9.3): the plan's line, then at a trigger its ticket, verbatim, before the word
    if (x) out += '<div class="jx">' + (has(x.line) ? `<div class="jxl">${t(x.line)}</div>` : '')
      + (x.ticket || []).filter(s => s !== x.line).map(s => `<div class="jxt">${t(s)}</div>`).join('')
      + (has(x.why) ? `<div class="jxt mute">${t(x.why)}</div>` : '') + '</div>';
```
In `sidepanel.css`, after the `.jnote` rule:

```css
.jx { margin: 2px 0 6px; padding: 5px 7px; border-left: 3px solid var(--fg); background: var(--bg); }
.jxl { font-weight: 700; font-size: 12.5px; line-height: 1.35; }
.jxt { font-family: ui-monospace, Consolas, monospace; font-size: 11px; line-height: 1.35; white-space: pre-wrap; overflow-wrap: anywhere; }
```
In `manifest.json`: `"version": "0.9.2"` → `"version": "0.9.3"`.

- [ ] **Step 4: Run the extension's tests** — `node test/exec.test.js` → `exec: 7 passed, 0 failed`; `node test/jarvis.test.js` and the README's other test files → unchanged, all pass.
- [ ] **Step 5: Leave uncommitted.** She reloads the extension after the server restart.

---

### Task 7: verify and hand over

- [ ] **Step 1:** `python -m pytest -q test_execute.py` → 16 passed; the parity script → PASS; the extension tests → pass.
- [ ] **Step 2:** The replays of 11, 12, 13 Nov (`--show`) go to her as text.
- [ ] **Step 3:** NOTEPAD row and memory: what was built, the parity numbers, what goes live on her restart, nothing committed.
- [ ] **Step 4:** Her actions: restart after a close, reload the extension; her word on the commit.
