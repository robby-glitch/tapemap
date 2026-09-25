"""board-chess-2026-09-24-gen.py -- builds the data behind board-chess-2026-09-24.html.

MOCKUP GENERATOR, NOT PRODUCTION. It is here as the reference for the three [I] layers the
board needs from the server and that do not exist yet: `position()` (the answer line),
`squares()` (what can happen) and the MOVES composition in `build()` -- see the notes file,
section 4. The rules it reads are NOT re-implemented: fronts.read / fronts._state /
fronts.fade_gate / fronts.broke, grounds.facts / grounds.ground and runs.Runs are imported.

READ-ONLY against the repo. Inputs:
  - GET captures taken 2026-09-24 00:25 IST while the server still held 2026-09-23:
    /api/oihist?idx=, /api/tape?idx=&day=2026-09-23, /api/warmap?idx=,
    /api/signals?rule=all&kind=all&day=2026-09-23 -> BOARD_RAW (default: the session
    scratchpad's raw/ folder, which may be gone; re-capture the same routes to rerun)
  - data/chain, data/book (via book_log.read_rows), data/frame, data/warmap, data/tape,
    data/vpin_log.jsonl, data/day_state -- all read, never written.
Writes ONLY <BOARD_RAW>/../board_data.json. The page template lives with the output HTML.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from collections import defaultdict

RAW = os.environ.get("BOARD_RAW", 'C:\\Users\\kaam\\AppData\\Local\\Temp\\claude\\C--Users-kaam-Desktop-operator-mode\\f1b3e1c1-1ed6-48af-adf8-96866d72f980\\scratchpad\\raw')
HERE = os.path.dirname(RAW)
TM = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, TM)
os.chdir(TM)                       # book_log / daylog resolve data/ relative to the repo

import book_log                    # noqa: E402  (read_rows only)
import fronts                      # noqa: E402
import grounds                     # noqa: E402
import ladder                      # noqa: E402
import runs as runs_mod            # noqa: E402

DAY = "2026-09-23"
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
IST = 19800
DEBOUNCE = 3                       # [I] display rule: a front's new state must hold 3 minutes to be a MOVE


def jload(name):
    with open(os.path.join(RAW, name), encoding="utf-8") as f:
        return json.load(f)


def mm(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def hm(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def ms_hm(t_ms):
    s = (int(t_ms) // 1000 + IST) % 86400
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"


def day_ms(hhmm, sec=59):
    """epoch ms of HH:MM:sec IST on DAY (first bar t gives the day's base)."""
    return None  # filled per index from a known bar


def L(x):
    """OI in lakh (1e5 units), one decimal, signed -- the house's own unit (+234.2L)."""
    return f"{x / 1e5:+.1f}L"


def Lu(x):
    return f"{abs(x) / 1e5:.1f}L"


# ---------------------------------------------------------------- inputs
def peak_asof(idx, times):
    """{minute: {(k, side): session-high absolute OI up to that minute}} from the chain record.
    The same running max chain_metrics keeps in ChainState.peak."""
    path = os.path.join(TM, "data", "chain", f"chain_{idx}_{DAY}.jsonl")
    run, by_min = {}, {}
    last_min = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                s = json.loads(line)
            except ValueError:
                continue
            m = (s.get("ts") or "")[:5]
            if not m:
                continue
            if last_min is not None and m != last_min:
                by_min[last_min] = dict(run)
            last_min = m
            for r in s.get("strikes") or []:
                for side in ("ce", "pe"):
                    oi = (r.get(side) or {}).get("oi")
                    if isinstance(oi, (int, float)):
                        key = (r["k"], side)
                        run[key] = max(run.get(key, 0), oi)
            by_min["_last_abs"] = {(r["k"], sd): (r.get(sd) or {}).get("oi") for r in s.get("strikes") or [] for sd in ("ce", "pe")}
    if last_min is not None:
        by_min[last_min] = dict(run)
    out, cur = {}, None
    for t in times:
        if t in by_min:
            cur = by_min[t]
        out[t] = cur
    return out


def abs_oi_asof(idx, times):
    """{minute: {(k, side): absolute OI at the last snapshot of that minute}} [M]."""
    path = os.path.join(TM, "data", "chain", f"chain_{idx}_{DAY}.jsonl")
    by_min = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                s = json.loads(line)
            except ValueError:
                continue
            m = (s.get("ts") or "")[:5]
            by_min[m] = {(r["k"], sd): (r.get(sd) or {}).get("oi") for r in s.get("strikes") or [] for sd in ("ce", "pe")}
    out, cur = {}, None
    for t in times:
        if t in by_min:
            cur = by_min[t]
        out[t] = cur
    return out


def replay_runs(idx, lot, tick):
    """Fill runs for the day, replayed from the book record exactly as the server's
    restart rebuild feeds them (ladder.step -> runs.on_fill). Also the detector's own
    `why` at each minute, so "could not rank" is never read as "none"."""
    lad = ladder.Ladder(lot=lot, tick=tick, idx=idx, day=DAY, lot_src="dump")
    R = runs_mod.Runs(lot=lot)
    why_at = {}
    for row in book_log.read_rows(DAY, idx):
        _closed, fills = lad.step(row)
        for f in fills:
            R.on_fill(f)
            why_at[ms_hm(f["ltt"])] = R.why()
    return R.events, why_at


# ---------------------------------------------------------------- per-index build
def build(idx):
    oh = jload(f"oihist_idx_{idx}.json")
    minutes = oh["minutes"]
    times = sorted(t for t in minutes if isinstance(t, str) and t < "15:30")
    backfill = set(oh.get("backfill_marks") or [])
    spot = [minutes[t]["spot"] for t in times]
    ks = sorted({float(k) for t in times for k in (minutes[t].get("k") or {})})
    step = min(b - a for a, b in zip(ks, ks[1:]) if b > a)

    pk = peak_asof(idx, times)
    absoi = abs_oi_asof(idx, times)

    tape = jload(f"tape0923_{idx}.json")
    ux = [b for b in (tape.get("ux") or {}).get("bars") or [] if b.get("cvd") is not None]
    lot = tape["ux"].get("lot")
    with open(os.path.join(TM, "data", "tape", f"ux_{idx}_{DAY}.jsonl"), encoding="utf-8") as f:
        tick = json.loads(f.readline()).get("tick")
    run_events, runs_why_at = replay_runs(idx, lot, tick)
    base_ms = ux[0]["t"] - (mm(ms_hm(ux[0]["t"])) * 60 - 0) * 1000 - 0   # epoch ms of 00:00 IST... approx
    base_ms = ux[0]["t"] - mm(ms_hm(ux[0]["t"])) * 60000             # 00:00 IST on DAY, in epoch ms

    def m_end(t):
        return base_ms + (mm(t) * 60 + 59) * 1000 + 999

    # ---- ribbons: every strike that was among the 9 nearest at any minute
    near = set()
    for t in times:
        s = minutes[t]["spot"]
        near.update(sorted(ks, key=lambda k: abs(k - s))[:fronts.NEAR])
    ribbons = []
    rib_index = {}
    for k in sorted(near):
        for i, side in enumerate(("CE", "PE")):
            vals = [fronts._pair(fronts._at(minutes[t].get("k"), k))[i] for t in times]
            st, run_max = [], float("-inf")
            for j, v in enumerate(vals):
                run_max = max(run_max, v)
                back = vals[max(0, j - fronts.SLOPE_MARKS)]
                st.append(fronts._state(v, run_max, v - back)[0])
            rib_index[(k, side)] = len(ribbons)
            ribbons.append({"k": k, "side": side, "chg": [round(v) for v in vals], "st": "".join(st)})

    # ---- fronts as-of every minute (the server's function on the cut grid)
    fr_by = []
    for t in times:
        p = pk.get(t)
        fr_by.append(fronts.read(fronts.cut(minutes, t), p) if True else [])

    # ---- frame (NIFTY only): last row per minute, forward-filled
    frame_by = {}
    taps, tape_ev = {}, {}
    if idx == "NIFTY":
        rows = {}
        with open(os.path.join(TM, "data", "frame", f"frame_{DAY}.jsonl"), encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                ts = r.get("ts") or ""
                if r.get("idx") != idx or not ts or ts >= "15:30":
                    continue
                rows[ts] = r
                for tp in r.get("taps") or []:
                    taps[tp["t"]] = tp
                for e in (r.get("tape") or {}).get("events") or []:
                    if e.get("at"):
                        tape_ev[(e["t"], e["kind"], e["p"])] = {**e, "basis": (r.get("walls") or {}).get("basis")}
        cur = None
        for t in times:
            if t in rows:
                cur = rows[t]
            frame_by[t] = cur

    # ---- basis (fut - spot), smoothed; only to draw HER zone (a futures object) on the index board
    basis_raw = {}
    for t in times:
        fr_ = frame_by.get(t)
        if fr_ and fr_.get("ts") == t and (fr_.get("where") or {}).get("px"):
            basis_raw[t] = fr_["where"]["px"] - minutes[t]["spot"]
    basis_s = {}
    for j, t in enumerate(times):
        win = [basis_raw[x] for x in times[max(0, j - 14): j + 1] if x in basis_raw]
        basis_s[t] = statistics.median(win) if win else None

    zone = []
    for t in times:
        fr_ = frame_by.get(t)
        w = (fr_ or {}).get("where") or {}
        b = basis_s.get(t)
        if not fr_ or b is None or not w.get("buy_zone") or not w.get("sell_zone") or not w.get("warm"):
            zone.append(None)
            continue
        zone.append({"d3": round(w["buy_zone"][0] - b, 1), "d2": round(w["buy_zone"][1] - b, 1),
                     "u2": round(w["sell_zone"][0] - b, 1), "u3": round(w["sell_zone"][1] - b, 1),
                     "vw": round(w["vwap"] - b, 1), "b": round(b, 1),
                     "fd2": round(w["buy_zone"][1], 1), "fd3": round(w["buy_zone"][0], 1),
                     "fu2": round(w["sell_zone"][0], 1), "fu3": round(w["sell_zone"][1], 1),
                     "fvw": round(w["vwap"], 1), "fpx": w.get("px")})

    # ---- levels (index frame, war map) -- fixed for the day
    wm = jload(f"warmap_idx_{idx}.json")["indices"][idx]
    levels = [{"kind": l["kind"], "px": l["px"], "label": l.get("label"), "major": l.get("major")}
              for l in wm.get("levels") or [] if l.get("kind") in ("PDH", "PDL", "PDC", "PWH", "PWL", "OPEN")]
    # MAX_PAIN and the war map's CE_WALL/PE_WALL are whole-chain aggregates: excluded by her
    # rule (near ATM, top two per side) -- the fronts ARE the walls on this board.

    # ---- signals (trigger_log) for this index, de-duplicated (first write wins)
    sig = jload("signals_0923.json")["rows"]
    seen, arms = set(), []
    for r in reversed(sig):                       # file order
        if r.get("index") != idx:
            continue
        key = (r["t"], r.get("kind") or "entry", r["side"])
        if key in seen:
            continue
        seen.add(key)
        arms.append(r)

    # engine ctx by minute: recorded only at arm/entry rows, plus the one the live screen showed at 13:36
    ctx_at = {}
    for r in arms:
        for d in range(3):
            ctx_at[hm(mm(r["t"]) + d)] = (r.get("ctx"), f"trigger_log {r.get('kind') or 'entry'} row {r['t']}")
    if idx == "NIFTY":
        for t in ("13:36", "13:37", "13:38"):
            ctx_at[t] = ({"verdict": "CAUTION", "vwhy": "no edge defined right now"},
                         "HANDOFF 2026-09-23 night: what the live header said at 13:36")

    # ---- VPIN (NIFTY-FUT only) and drag (per index) as-of
    vp = []
    if idx == "NIFTY":
        with open(os.path.join(TM, "data", "vpin_log.jsonl"), encoding="utf-8") as f:
            vp = [json.loads(l) for l in f if f'"{DAY}"' in l]
        vp = [r for r in vp if r.get("inst") == "NIFTY-FUT"]
    with open(os.path.join(TM, "data", "day_state", f"day_{DAY}.json"), encoding="utf-8") as f:
        drag = sorted((r for r in json.load(f)["drag_day"].get(idx) or [] if r.get("t", "99") < "15:30"),
                      key=lambda r: r["t"])

    # ---------------------------------------------------------------- per-minute reads
    reads, prev_div = [], {"top": None, "bottom": None}
    div_moves = []
    for j, t in enumerate(times):
        e_ms = m_end(t)
        bars = [b for b in ux if mm(ms_hm(b["t"])) + 5 <= mm(t)]
        rs = [{**e, "t": min(e["t"], e_ms)} for e in run_events if e["from_t"] <= e_ms]
        rwhy = None
        for tt in sorted(runs_why_at):
            if tt <= t:
                rwhy = runs_why_at[tt]
        fr = fr_by[j]
        F = grounds.facts(bars, rs, fr, runs_why=rwhy)
        s = spot[j]

        # divergence moves (first minute each new divergence text appears)
        cv = F.get("cvd") or {}
        for kk in ("top", "bottom"):
            dv = cv.get("div_" + kk)
            if dv and dv != prev_div[kk]:
                div_moves.append({"t": t, "kind": "div", "side": "sell" if kk == "top" else "buy",
                                  "text": "divergence: " + dv, "tag": "I"})
            prev_div[kk] = dv

        # the engine's call, if one was recorded for this minute
        call = None
        cx = ctx_at.get(t)
        if cx and cx[0]:
            px = bars[-1]["c"] if bars else None
            g = grounds.ground(cx[0], px, bars, rs, fr, runs_why=rwhy)
            head = next((c for c in g["calls"] if c["source"] == "verdict"), g["calls"][0] if g["calls"] else None)
            if head:
                call = {"text": head["text"], "status": head["status"], "src": cx[1],
                        "fam": {k: {"state": head[k]["state"], "fact": head[k]["fact"], "tag": head[k]["tag"]}
                                for k in ("oi", "cvd", "flow")},
                        "others": [{"text": c["text"], "status": c["status"]} for c in g["calls"] if c is not head][:3]}

        gb = fronts.fade_gate(fr, "buy", None, fronts.stale(minutes, t))
        gs = fronts.fade_gate(fr, "sell", None, fronts.stale(minutes, t))
        z = zone[j]
        vpr = [r for r in vp if r["at"][:5] <= t]
        dr = [r for r in drag if r["t"] <= t]
        reads.append({
            "fr": [{"k": f["k"], "side": f["side"], "oi": f["oi"], "chg": f["chg"], "peak": f["peak"],
                    "peak_at": f["peak_at"], "from_peak": f["from_peak"], "slope": f["slope"],
                    "state": f["state"],
                    "now_oi": (absoi.get(t) or {}).get((int(f["k"]), f["side"].lower()))} for f in fr],
            "broke": (lambda b: {"k": b["k"], "side": b["side"], "peak_at": b["peak_at"], "state": b["state"]} if b else None)(fronts.broke(fr)),
            "cvd": cv or None, "cvd_why": F.get("cvd_why"),
            "flow": F.get("flow"), "flow_why": F.get("flow_why"),
            "fut": F.get("fut_oi"),
            "call": call,
            "gate": {"buy": {"legal": gb["legal"], "why": gb["why"]}, "sell": {"legal": gs["legal"], "why": gs["why"]}},
            "vpin": ({"v": vpr[-1]["vpin"], "pct": vpr[-1]["pct"], "at": vpr[-1]["at"][:5]} if vpr else None),
            "drag": ({"frac": dr[-1]["frac"], "side": dr[-1]["side"], "at": dr[-1]["t"]} if dr else None),
            "sig": ((frame_by.get(t) or {}).get("setup") or {}).get("signal", {}).get("state") if frame_by.get(t) else None,
        })

    # ---------------------------------------------------------------- moves (the scoresheet)
    moves = []
    # 1. opening position, 5 minutes in
    j0 = next((j for j, t in enumerate(times) if t >= "09:20" and fr_by[j]), None)
    if j0 is not None:
        fr = fr_by[j0]
        ce = [f"{f['k']:.0f}" for f in fr if f["side"] == "CE"]
        pe = [f"{f['k']:.0f}" for f in fr if f["side"] == "PE"]
        moves.append({"t": times[j0], "kind": "open", "side": None,
                      "text": f"opening fronts: CE {' / '.join(ce)} · PE {' / '.join(pe)} · spot {spot[j0]:,.1f}", "tag": "M"})

    # 2. the SEQUENCE per front (her rule), one move per LEG: a leg is the rule's BUILDING held
    #    DEBOUNCE minutes; it ends in ONE "stopped adding" (the rule's state out of BUILDING for
    #    DEBOUNCE minutes), then "giving back" (UNWINDING held DEBOUNCE minutes) and "half its
    #    build gone". Creeping highs inside a stall are the rule's STALLED, not a new leg, and building
    #    again without a new high is not one either.
    #    Only while the strike-side is a current top-2 front, and only for fronts of size.
    #    [I] display rules, declared: DEBOUNCE = 3 min; size = peak >= 15 % of the biggest front.
    for (k, side), ri in rib_index.items():
        st, chg = ribbons[ri]["st"], ribbons[ri]["chg"]
        run_peak, peak_j, in_leg, stalled, gave, last = float("-inf"), None, False, False, set(), float("-inf")
        for j in range(len(times)):
            if chg[j] > run_peak:
                run_peak, peak_j = chg[j], j
            win = st[max(0, j - DEBOUNCE + 1): j + 1] if j >= DEBOUNCE - 1 else ""
            if win == "B" * DEBOUNCE and not in_leg and run_peak > last:   # a leg needs a NEW high
                in_leg, stalled, gave = True, False, set()
            if not any(f["k"] == k and f["side"] == side for f in fr_by[j]):
                continue
            big = max(abs(f["peak"]) for f in fr_by[j]) or 1
            if run_peak <= 0 or run_peak < 0.15 * big:
                continue
            if in_leg and win and "B" not in win:
                moves.append({"t": times[j], "kind": "front", "side": side, "k": k, "state": "S",
                              "text": f"{side} {k:.0f} stopped adding — peak {L(run_peak)} at {times[peak_j]}", "tag": "M"})
                in_leg, stalled, last = False, True, run_peak
            if not stalled:
                continue
            off = (run_peak - chg[j]) / abs(run_peak)
            if "U" not in gave and win == "U" * DEBOUNCE:
                moves.append({"t": times[j], "kind": "front", "side": side, "k": k, "state": "U",
                              "text": f"{side} {k:.0f} giving back — {off:.0%} off its {times[peak_j]} peak ({L(chg[j])} left)", "tag": "M"})
                gave.add("U")
            if "H" not in gave and off >= 0.5 and st[j] == "U":
                moves.append({"t": times[j], "kind": "front", "side": side, "k": k, "state": "U",
                              "text": f"{side} {k:.0f} half its build gone — {off:.0%} off its {times[peak_j]} peak ({L(chg[j])} left)", "tag": "M"})
                gave.add("H")

    # 3. level moves from the war map's forward log (observed live, not the backfill replay)
    wl = []
    with open(os.path.join(TM, "data", "warmap", f"warmap_{DAY}.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("idx") == idx and r.get("to") != "APPROACH":
                wl.append(r)
    rej = {}
    for r in wl:
        t = r["ts"][11:16]
        if t >= "15:30":
            continue
        name = f"{'round ' if r['level'] == 'ROUND' else r['level'] + ' '}{r['px']:,.0f}"
        if r["to"] == "REJECT":
            g = rej.get(r["px"])
            if g and mm(t) - mm(g["times"][-1]) <= 30:
                g["times"].append(t)
            else:
                g = rej[r["px"]] = {"t": t, "kind": "reject", "side": None, "px": r["px"], "name": name, "times": [t], "tag": "M"}
                moves.append(g)
        elif r["to"] == "DWELL":
            moves.append({"t": t, "kind": "dwell", "px": r["px"], "text": f"dwell at {name} — price parked, positions loading", "tag": "M"})
        elif r["to"] == "BREAK":
            d = r.get("direction")
            moves.append({"t": t, "kind": "break", "side": "buy" if d == "UP" else "sell", "px": r["px"],
                          "text": f"{name} broken {'up' if d == 'UP' else 'down'}", "tag": "M"})
        elif r["to"] == "RUN":
            tg = r.get("target") or {}
            if moves and moves[-1]["kind"] == "break" and moves[-1]["px"] == r["px"]:
                moves[-1]["text"] += f" → next {tg.get('kind', '')} {tg.get('px', 0):,.0f}"
        elif r["to"] in ("HIT", "FAILED"):
            tg = r.get("target") or {}
            moves.append({"t": t, "kind": r["to"].lower(), "px": r["px"],
                          "text": (f"run {r['px']:,.0f} → {tg.get('kind', '')} {tg.get('px', 0):,.0f} arrived" if r["to"] == "HIT"
                                   else f"run {r['px']:,.0f} → {tg.get('kind', '')} {tg.get('px', 0):,.0f} failed, back through {r['px']:,.0f}"),
                          "tag": "M"})

    # 4. zone taps (frame, NIFTY) and 5. zone arms/entries (trigger_log), gate stamped at the row's own bar
    visit = {}
    for tp in sorted(taps.values(), key=lambda x: x.get("tx") or x["t"]):
        t = ms_hm(tp.get("tx") or tp["t"])
        side = "buy" if tp["side"] == 1 else "sell"
        v = visit.get(side)
        if v and mm(t) - mm(v["times"][-1]) <= 20:          # one visit = taps of one side, <= 20 min apart
            if t not in v["times"]:
                v["times"].append(t)
            continue
        v = visit[side] = {"t": t, "kind": "tap", "side": side, "times": [t], "count": "taps",
                           "text": f"{side} pocket reached — {tp['price']:,.1f} fut (z {tp['z']:+.1f})", "tag": "M"}
        moves.append(v)
    last_arm = {}
    for r in arms:
        kind = r.get("kind") or "entry"
        g = r.get("gate") or {}
        gl = {True: "LEGAL", False: "ILLEGAL", None: "PATA NAHI"}[g.get("legal")]
        side = r["side"].lower()
        if kind == "arm" and r.get("rearm") and last_arm.get(side):
            last_arm[side]["n"] = last_arm[side].get("n", 1) + 1
            last_arm[side]["times"].append(r["t"])
            continue
        c = r.get("ctx") or {}
        eng = f" · engine then: {c.get('verdict')}" if c.get("verdict") else ""
        mv = {"t": r["t"], "kind": "arm" if kind == "arm" else "fire", "side": side, "times": [r["t"]], "count": "arms" if kind == "arm" else None,
              "text": (f"zone {r['side']} {'armed' if kind == 'arm' else 'TRIGGER'} {r.get('band')} {r.get('level'):,.0f} fut"
                       f" · fade {gl}: {g.get('why')}{eng}"), "tag": "M", "gate": gl}
        moves.append(mv)
        if kind == "arm":
            last_arm[side] = mv

    # 6. fill-run clusters per 15 minutes [I]
    for w0 in range(mm("09:15"), mm("15:30"), 15):
        inw = [e for e in run_events if w0 <= mm(ms_hm(e["from_t"])) < w0 + 15]
        b = [e for e in inw if e["side"] > 0]
        s_ = [e for e in inw if e["side"] < 0]
        for mine, other, word, side in ((b, s_, "buy", "buy"), (s_, b, "sell", "sell")):
            if len(mine) >= 3 and len(mine) >= 2 * len(other):
                q = sum(e.get("qty") or 0 for e in mine)
                moves.append({"t": hm(min(w0 + 15, mm("15:29"))), "kind": "runs", "side": side,
                              "text": f"{len(mine)} {word} runs {hm(w0)}–{hm(w0 + 15)} vs {len(other)} {'sell' if side == 'buy' else 'buy'} (≈{q:,.0f} lots)",
                              "tag": "I"})
    # 7. divergences [I] -- one move per run of the same kind (new highs without CVD, 10:35 -> 12:10 ...)
    dv_last = {}
    for mv in div_moves:
        g = dv_last.get(mv["side"])
        if g and mm(mv["t"]) - mm(g["times"][-1]) <= 20:
            g["times"].append(mv["t"])
            continue
        mv["times"], mv["count"] = [mv["t"]], "new extremes"
        dv_last[mv["side"]] = mv
        moves.append(mv)
    # 8. tape events AT one of her levels (an OI wall or a prior-day level) -- the trader rule:
    #    absorption/exhaustion count only at levels. Tape-book walls (S/B) stay on the strip.
    tev = {}
    for e in sorted(tape_ev.values(), key=lambda x: x["t"]):
        if e["kind"] not in ("absorption", "exhaustion", "trap"):
            continue
        parts = ((e.get("at") or {}).get("label") or "").replace("at ", "").split()
        if len(parts) != 2 or parts[0] not in ("CE", "PE", "PDH", "PDL", "PDC"):
            continue
        where = f"{parts[0]} {parts[1]}"
        if parts[0] in ("CE", "PE") and e.get("basis") is not None:
            try:
                where = f"the {parts[0]} {round((float(parts[1]) - e['basis']) / step) * step:.0f} wall"
            except ValueError:
                pass
        t = hm(mm(e["t"]) + 5)
        key = (e["kind"], where)
        g = tev.get(key)
        if g and mm(t) - mm(g["times"][-1]) <= 30:
            if t not in g["times"]:
                g["times"].append(t)
            continue
        side = "buy" if (e.get("side") or 0) > 0 else "sell"
        g = tev[key] = {"t": t, "kind": "tape", "side": side, "times": [t], "count": "bars",
                        "text": f"{e['kind']} at {where} ({e['p']:,.0f} fut)", "tag": "M"}
        moves.append(g)

    for mv in moves:
        if mv["kind"] == "reject":
            mv["text"] = f"{mv['name']} rejected"
            mv["count"] = "tests"
    moves.sort(key=lambda m: (m["t"], {"open": 0, "front": 1}.get(m["kind"], 2)))

    # ---------------------------------------------------------------- squares (what can happen) per minute
    for j, t in enumerate(times):
        reads[j]["sq"] = squares(idx, t, spot[j], reads[j], levels, zone[j], spot[: j + 1], times[: j + 1], step)
        reads[j]["pos"] = position(reads[j], spot[j], step)
        if j < fronts.SLOPE_MARKS:
            # fronts.read has no "forming" state: with fewer than SLOPE_MARKS marks every front's
            # slope is ~0 and it reads STALLED, so broke() names one "stopped first" at 09:15. The
            # board says forming instead (dashed-geometry sentence) -- see the notes, server addition.
            reads[j]["forming"] = True
            reads[j]["pos"] = {"head": f"Fronts forming — the build → stall → unwind sequence needs {fronts.SLOPE_MARKS} one-minute marks, {j + 1} so far",
                               "sub": reads[j]["pos"]["sub"].split(" · CVD")[0] + " · states before 09:30 are not a read yet", "tag": "M"}

    # day range for a stable board
    # the board's price range: the day's spot range +/- 1.5 strikes, fixed for the day (live: it only
    # ever widens, at a new extreme) -- a front beyond it is named at the edge, never allowed to
    # stretch the board (BANKNIFTY's CE/PE 57000 sat 400+ pts away for 202 minutes on 09-23)
    lo = min(spot) - 1.5 * step
    hi = max(spot) + 1.5 * step
    # how often the exchange OI actually steps in this grid [M] -- a peak stamp is only as fine as that
    tot = same = 0
    for rb in ribbons:
        for a, b in zip(rb["chg"], rb["chg"][1:]):
            tot += 1
            same += a == b
    return {"idx": idx, "step": step, "lot": lot, "t": times, "spot": spot,
            "oi_same": round(same / tot, 2) if tot else None,
            # the SECOND tape (GoCharting, NIFTY only): same bars, its own side attribution
            "ofd": [{"t": ms_hm(b["t"]), "cvd": b["cvd"]} for b in tape.get("bars") or [] if b.get("cvd") is not None],
            "agree": ((tape.get("ux") or {}).get("agree") or {}).get("delta_sign_agree"),
            "bf": [j for j, t in enumerate(times) if t in backfill],
            "ribbons": ribbons, "levels": levels, "zone": zone, "range": [lo, hi],
            "ux": [{"t": ms_hm(b["t"]), "c": b["c"], "cvd": b["cvd"], "d": b.get("delta"), "oi": b.get("oi"),
                    "partial": b.get("partial")} for b in ux],
            "runs": [{"t": ms_hm(e["from_t"]), "side": e["side"], "qty": e.get("qty"), "n": e.get("n"), "p": e.get("p")}
                     for e in run_events],
            "taps": [{"t": ms_hm(tp.get("tx") or tp["t"]), "side": tp["side"], "p": tp["price"], "z": tp["z"]} for tp in taps.values()],
            "arms": [{"t": r["t"], "side": r["side"], "kind": r.get("kind") or "entry",
                      "legal": (r.get("gate") or {}).get("legal")} for r in arms],
            "moves": moves, "reads": reads,
            "frame": idx == "NIFTY", "n_runs": len(run_events)}


# ---------------------------------------------------------------- the two [I] layers this mockup stands in for
def _fr(rd, side, i=0):
    rows = [f for f in rd["fr"] if f["side"] == side]
    return rows[i] if len(rows) > i else None


def _press(rd):
    """(+1 buyers / -1 sellers / 0, strength word, fact) off grounds' CVD + FLOW facts."""
    c, fl = rd.get("cvd"), rd.get("flow")
    if not c:
        return 0, None, rd.get("cvd_why")
    d = (c["d"] > 0) - (c["d"] < 0)
    word = "pressing" if c["rank"] >= grounds.ONE_SIDED else "leaning" if c["rank"] >= grounds.STRONG else None
    fact = f"CVD {c['d']:+,.0f} since {c['since']} (rank {c['rank']:.2f})"
    if fl:
        fact += f" · {fl['sell']} sell / {fl['buy']} buy prints of size"
    return (d if word else 0), word, fact


def position(rd, s, step):
    """THE ANSWER LINE: positioning -> aggression -> response, in her read model's order.
    Direction only ever inside a mechanism sentence."""
    ce, pe = _fr(rd, "CE"), _fr(rd, "PE")
    if not ce or not pe:
        return {"head": "Fronts could not be read", "sub": "near-ATM fronts not read — could not check", "tag": "M"}

    def st(f):
        if f["state"] == "BUILDING":
            return f"still adding ({L(f['chg'])})"
        if f["state"] == "STALLED":
            return f"stopped adding at {f['peak_at']}"
        return f"giving back since its {f['peak_at']} peak ({(f['peak'] - f['chg']) / max(abs(f['peak']), 1):.0%} off)"

    sub = f"Call writers at {ce['k']:.0f} {st(ce)} · put writers at {pe['k']:.0f} {st(pe)}"
    d, word, fact = _press(rd)
    if d == 0:
        if ce["state"] == pe["state"] == "BUILDING":
            head = (f"Nobody pressing, and both sides are writing — " +
                    (f"a straddle wall at {ce['k']:.0f} is being defended" if ce["k"] == pe["k"]
                     else f"the range {min(pe['k'], ce['k']):.0f}–{max(pe['k'], ce['k']):.0f} is being defended"))
        elif ce["state"] == pe["state"] == "UNWINDING":
            head = ("Nobody pressing, and writers are leaving both sides — " +
                    (f"nobody is defending {ce['k']:.0f} from either side" if ce["k"] == pe["k"]
                     else f"nobody is defending {pe['k']:.0f} or {ce['k']:.0f}"))
        else:
            b = rd.get("broke")
            head = ("Nobody pressing — " + (f"{b['side']} {b['k']:.0f} writers stopped first ({b['peak_at']}), the fuel is on that side"
                                           if b else "fronts quiet"))
        return {"head": head, "sub": sub + " · " + (fact or ""), "tag": "I"}
    who = "Buyers" if d > 0 else "Sellers"
    dfn = ce if d > 0 else pe            # the writers who PAY if the aggressors win
    k = dfn["k"]
    if dfn["state"] == "BUILDING":
        resp = f"into {dfn['side']} {k:.0f} writers still adding — a defender is absorbing it"
    elif dfn["state"] == "STALLED":
        resp = f"into {dfn['side']} {k:.0f} writers who stopped adding at {dfn['peak_at']} — no defender building at {k:.0f}"
    else:
        resp = f"while {dfn['side']} {k:.0f} writers give back — the writers are paying the move"
    return {"head": f"{who} {word} {resp}", "sub": sub + " · " + fact, "tag": "I"}


def squares(idx, t, s, rd, levels, z, path, ptimes, step):
    """WHAT CAN HAPPEN: the nearest reaction points each way, and what would have to be
    true to reach / to be refused there. Conditions only -- never a probability."""
    cand = []
    for l in levels:
        cand.append((l["px"], l["label"] or l["kind"], "level"))
    for f in rd["fr"]:
        cand.append((f["k"], f"{f['side']} {f['k']:.0f} wall", "wall_" + f["side"]))
    for r in range(int((s - 3 * step) // step), int((s + 3 * step) // step) + 1):
        cand.append((r * step, f"round {r * step:,.0f}", "round"))
    hi_j = max(range(len(path)), key=lambda i: path[i])
    lo_j = min(range(len(path)), key=lambda i: path[i])
    cand.append((path[hi_j], f"day high ({ptimes[hi_j]})", "hod"))
    cand.append((path[lo_j], f"day low ({ptimes[lo_j]})", "lod"))
    if z:
        cand += [(z["d2"], f"buy pocket top d2 ({z['fd2']:,.0f} fut)", "zone_b"), (z["d3"], f"buy pocket floor d3 ({z['fd3']:,.0f} fut)", "zone_b"),
                 (z["u2"], f"sell pocket u2 ({z['fu2']:,.0f} fut)", "zone_s"), (z["u3"], f"sell pocket u3 ({z['fu3']:,.0f} fut)", "zone_s")]
    # merge within 4 pts into one square
    cand.sort()
    merged = []
    for px, lab, kind in cand:
        if merged and abs(px - merged[-1]["px"]) <= 4:
            if lab not in merged[-1]["labels"]:
                merged[-1]["labels"].append(lab)
                merged[-1]["kinds"].append(kind)
        else:
            merged.append({"px": px, "labels": [lab], "kinds": [kind]})
    up = [m for m in merged if m["px"] > s + 3][:2]
    dn = [m for m in reversed(merged) if m["px"] < s - 3][:2]

    d, word, fact = _press(rd)
    ce, pe = _fr(rd, "CE"), _fr(rd, "PE")

    def fuel_cond(f, dirn):
        who = "call" if dirn > 0 else "put"
        if not f:
            return {"ok": None, "mode": "blind", "text": f"{who} writers giving back", "fact": "fronts not read — could not check"}
        ok = True if f["state"] == "UNWINDING" else False if f["state"] == "BUILDING" else None
        mode = {"UNWINDING": "met", "BUILDING": "against", "STALLED": "notyet"}[f["state"]]
        fact = {"UNWINDING": f"{f['side']} {f['k']:.0f} giving back, {(f['peak'] - f['chg']) / max(abs(f['peak']), 1):.0%} off its {f['peak_at']} peak",
                "STALLED": f"{f['side']} {f['k']:.0f} stopped adding at {f['peak_at']} — not giving back yet",
                "BUILDING": f"{f['side']} {f['k']:.0f} still adding ({L(f['chg'])}) — defending"}[f["state"]]
        return {"ok": ok, "mode": mode, "text": f"{f['side']} {f['k']:.0f} gives back", "fact": fact}

    def press_cond(dirn):
        who = "buyers" if dirn > 0 else "sellers"
        if not rd.get("cvd"):
            return {"ok": None, "mode": "blind", "text": f"{who} press", "fact": "could not check — " + (rd.get("cvd_why") or "no ladder bars")}
        ok = True if d == dirn else False if d == -dirn else None
        mode = "met" if d == dirn else "against" if d == -dirn else "notyet"
        return {"ok": ok, "mode": mode, "text": f"{who} press", "fact": fact}

    def gate(side):
        g = rd["gate"][side]
        return {"legal": g["legal"], "why": g["why"]}

    out = {}
    for name, sq, dirn, f_fuel, f_hold, pocket in (("up", up, 1, ce, ce, "sell"), ("dn", dn, -1, pe, pe, "buy")):
        if not sq:
            out[name] = None
            continue
        conds = [fuel_cond(f_fuel, dirn), press_cond(dirn)]
        hold = (f"{f_hold['side']} {f_hold['k']:.0f} writers add again, or absorption prints at {sq[0]['px']:,.0f}"
                if f_hold else "writers at the square add again")
        out[name] = {"sq": [{"px": round(m["px"], 1), "labels": m["labels"], "kinds": m["kinds"], "dist": round(m["px"] - s, 1)} for m in sq],
                     "conds": conds, "hold": hold, "pocket": pocket, "gate": gate(pocket)}
    both_build = bool(ce and pe and ce["state"] == pe["state"] == "BUILDING")
    out["pin"] = {"ok": both_build,
                  "fact": (f"CE {ce['k']:.0f} {ce['state'].lower()} · PE {pe['k']:.0f} {pe['state'].lower()}" if ce and pe else "fronts not read")}
    return out


if __name__ == "__main__":
    data = {"day": DAY, "made": "2026-09-24 00:40 IST", "idx": {}}
    for idx in IDXS:
        b = build(idx)
        data["idx"][idx] = b
        print(idx, "minutes", len(b["t"]), "ribbons", len(b["ribbons"]), "moves", len(b["moves"]), "runs", b["n_runs"])
    with open(os.path.join(HERE, "board_data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), default=str)
    print("bytes", os.path.getsize(os.path.join(HERE, "board_data.json")))
