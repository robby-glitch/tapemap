"""Round 6: TapeMap's own footprint reads (prints.py, absorption/climax/exhaustion by tm_marks, stacked imbalances,
CVD, volume profile) run on the OPTION strikes' Dext ladders, NIFTY, 28-30 Oct + 2-3 Nov, her 3-min grid, causal.
The reads are REUSED, not changed; only the scale is chosen here (NOTES.md "Round 6 scale"). Counts only.
Run from tapemap/:  python -I -X utf8 docs/optflow/fable/round6.py"""
import json, os, sys, statistics as st
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
TM = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE); sys.path.insert(0, TM); sys.path.insert(0, os.path.join(HERE, "..", "brainstorm"))
from load import hm, m_of, D
import load as _load
import prints, strike_bands as SB
from round4 import chain_greeks, closes, last_close, fut_after
from round5 import wall, ORDER, bands

DAYS = json.load(open(os.path.join(HERE, "days.json"), encoding="utf-8"))
# ---- the scale, fixed before counting (NOTES.md): -------------------------------------------------------------------
ROW_PCT = 0.01          # option row = 1 % of the bar's close premium, rounded to the 0.05 tick, floor 0.05
UNIT = 7_500            # one "lot" fed to prints.imbalances = 7,500 qty, so IMB_MIN_LOTS 5 = 37,500 qty (500 lots) at one row
BIG_QTY = 5e5           # qty-big: 5L in one price cell in one minute (as before)
BIG_RS = 2e7            # rupee-big: qty x premium >= Rs 2 crore of premium at one cell
BIG_DLOTS = 2_000       # delta-big: qty x |chain delta| / 75 >= 2,000 lots-equivalent (the size of a wall move)
LOT = 75


def row_size(c):
    return max(0.05, round(round(c * ROW_PCT / 0.05) * 0.05, 2))


def opt_bars(rows, snap, k, side):
    """3-min option bars on her grid from the 1-min Dext candles: h, l, o/c = chain ltp at the previous / this close,
    vol, delta, ladder (merged per-price cells, b/s in UNITs for prints.imbalances, raw qty kept in bq/sq)."""
    out, prev_c = [], None
    for e in range(557, 930, 3):
        ms = [m for m in (e - 2, e - 1, e) if m in rows]
        s = snap.get(e, {}).get((k, side.lower()))
        if not ms or not s or s[1] is None:
            continue
        lad = defaultdict(lambda: [0, 0])
        for m in ms:
            for lv in rows[m]["levels"]:
                lad[lv["price"]][0] += lv["buy_volume"]; lad[lv["price"]][1] += lv["sell_volume"]
        c = s[1]
        out.append({"t": e, "o": prev_c if prev_c is not None else c, "h": max(rows[m]["high"] for m in ms), "l": min(rows[m]["low"] for m in ms),
                    "c": c, "vol": sum(rows[m]["total_volume"] for m in ms) / UNIT, "delta": sum(rows[m]["delta"] for m in ms) / UNIT,
                    "ladder": [{"p": p, "b": b / UNIT, "s": sv / UNIT, "u": 0, "bt": 0, "st": 0} for p, (b, sv) in sorted(lad.items())],
                    "cells": [(p, b, sv) for p, (b, sv) in lad.items()]})
        prev_c = c
    return out


def snapshot(day):
    import optflow as O
    ch = O.load_chain(day, "NIFTY")
    snap, cur = {}, {}
    for m in range(555, 931):
        r = ch.get(m)
        if r:
            for s in r.get("strikes") or []:
                for sd in ("ce", "pe"):
                    q = s.get(sd) or {}
                    if q.get("oi") is not None:
                        cur[(s["k"], sd)] = (q["oi"], q.get("ltp"))
        snap[m] = dict(cur)
    return snap


def main():
    for day in ORDER:
        _load.CUR["day"] = day
        x = DAYS[day]["NIFTY"]; C = closes(x)
        dx = _load.dext(day)["NIFTY"]; snap = snapshot(day); gk = chain_greeks(day); B = bands(day, x)
        print(f"\n################ {day}")
        # ---------------- 1. big prints three ways (1-min cells, every strike, the whole day)
        cnt = Counter(); byzone = defaultdict(Counter)
        for (k, side), rows in dx.items():
            for m, r in rows.items():
                d = (gk.get(m, {}).get((k, side)) or (None, None))[0]
                i = x["mins"].index(m) if m in x["mins"] else None
                sp = x["spot"][i] if i is not None else None
                z = SB.zone(k, side.lower(), sp) if sp else "?"
                for lv in r["levels"]:
                    q = lv["total_volume"]
                    qb, rb, db = q >= BIG_QTY, q * lv["price"] >= BIG_RS, (d is not None and q * abs(d) / LOT >= BIG_DLOTS)
                    if qb or rb or db:
                        key = ("Q" if qb else "") + ("R" if rb else "") + ("D" if db else "")
                        cnt[key] += 1; byzone[z][key] += 1
        print("== 1. big cells by class (Q qty>=5L · R >=Rs2cr · D >=2,000 delta-lots):", dict(cnt))
        print("   by zone:", {z: dict(v) for z, v in byzone.items()})
        # per-strike bars for the strikes we read: cap / floor / ATM±1 at each close -> build bars for all strikes once
        bars = {key: opt_bars(rows, snap, key[0], key[1]) for key, rows in dx.items()}
        marks = {key: prints.tm_marks(bl)[0] for key, bl in bars.items()}
        flags = {key: {b["t"]: prints.bar_flags(b, row_size(b["c"])) for b in bl} for key, bl in bars.items()}
        # ---------------- 2. absorption (tm_marks kind 'absorption') at the wall strikes and ATM±1
        abs_at = defaultdict(list)
        for i in C:
            sp = x["spot"][i]
            if sp is None: continue
            atm = round(sp / 50) * 50
            for key in [tuple(x["strikes"][wall(x, i, "CE")]) if wall(x, i, "CE") is not None else None,
                        tuple(x["strikes"][wall(x, i, "PE")]) if wall(x, i, "PE") is not None else None,
                        (atm, "CE"), (atm, "PE"), (atm + 50, "CE"), (atm - 50, "PE")]:
                if not key or key not in marks: continue
                for mk in marks[key]:
                    if mk["t"] == x["mins"][i] and mk["kind"] == "absorption":
                        abs_at[key].append((hm(x["mins"][i]), mk.get("side"), fut_after(x, i, 15)))
        n_abs = sum(len(v) for v in abs_at.values())
        up = sum(1 for v in abs_at.values() for r in v if r[2] is not None and r[2] >= 20); dn = sum(1 for v in abs_at.values() for r in v if r[2] is not None and r[2] <= -20)
        print(f"== 2. absorption marks at wall / ATM±1 strikes: {n_abs} (fut +15 ≥ +20: {up} · ≤ −20: {dn}) · " + "; ".join(f"{k[0]}{k[1]} " + ",".join(r[0] for r in v) for k, v in list(abs_at.items())[:8]))
        if day == "2026-11-03" and (23600, "CE") in marks:
            print("   3 Nov 23,600 CE 09:47–10:17 bars:", [(hm(b["t"]), round(b["c"], 1), round(b["delta"] * UNIT / 1e5, 1), [m["kind"] for m in marks[(23600, "CE")] if m["t"] == b["t"]]) for b in bars[(23600, "CE")] if 587 <= b["t"] <= 617])
        # ---------------- 3. stacked buy imbalances at the cap vs the first COVER close; false alarms
        stack_closes = []
        for i in C:
            w = wall(x, i, "CE")
            if w is None: continue
            key = tuple(x["strikes"][w]); f = flags.get(key, {}).get(x["mins"][i])
            if f and any(s["side"] == "buy" for s in f["stacks"]):
                stack_closes.append(i)
        sc = {hm(x["mins"][i]) for i in stack_closes}
        nxt = [fut_after(x, i, 15) for i in stack_closes]
        print(f"== 3. stacked BUY imbalance at the cap: {len(stack_closes)} closes · next 15 ≥ +40: {sum(1 for v in nxt if v is not None and v >= 40)} · ≤ −40: {sum(1 for v in nxt if v is not None and v <= -40)} · at: {', '.join(sorted(sc))[:200]}")
        # the 8 covering events (R5): first COVER close at the cap and the last stacked-buy close before it
        EV = {"2026-10-28": [("12:44", 1)], "2026-10-29": [("10:17", 1), ("14:11", 1)], "2026-10-30": [("11:05", 1), ("11:44", 1)], "2026-11-02": [("09:32", 1), ("12:59", -1), ("14:29", 1)], "2026-11-03": []}
        for t0, dirn in EV.get(day, []):
            s = x["mins"].index(m_of(t0)); e = s + 15
            side = "CE" if dirn > 0 else "PE"
            first_cov = next((i for i in C if s - 30 <= i <= e and wall(x, i, side) is not None and x["who"][i][wall(x, i, side)] == "C"), None)
            stk = [i for i in C if s - 30 <= i <= (first_cov if first_cov is not None else e) and wall(x, i, side) is not None
                   and (flags.get(tuple(x["strikes"][wall(x, i, side)]), {}).get(x["mins"][i]) or {"stacks": []})["stacks"]
                   and any(z["side"] == ("buy" if dirn > 0 else "sell") for z in flags[tuple(x["strikes"][wall(x, i, side)])][x["mins"][i]]["stacks"])]
            print(f"   event {t0} {'▲' if dirn > 0 else '▼'}: first COVER close at the wall {hm(x['mins'][first_cov]) if first_cov is not None else 'none in window'} · stacked {'buy' if dirn > 0 else 'sell'} at the wall before it: {[hm(x['mins'][i]) for i in stk] or 'none'}"
                  + (f" → {x['mins'][first_cov] - x['mins'][stk[0]]} min ahead" if stk and first_cov is not None else ""))
        # ---------------- 4. climax / exhaustion at the cap and ATM strikes: next 15 fut with the premium's side
        cx = Counter()
        for i in C:
            sp = x["spot"][i]
            if sp is None: continue
            atm = round(sp / 50) * 50
            for key in {(atm, "CE"), (atm, "PE"), tuple(x["strikes"][wall(x, i, "CE")]) if wall(x, i, "CE") is not None else (atm, "CE")}:
                for mk in marks.get(key, []):
                    if mk["t"] != x["mins"][i] or mk["kind"] not in ("climax", "exhaustion"): continue
                    b = (B.get(key) or {}).get(x["mins"][i]); pos = SB.pos(b) if b else "?"
                    up_side = (key[1] == "CE") == (mk.get("side") == "buy")   # a call bought / a put sold = index up
                    n15 = fut_after(x, i, 15)
                    res = "?" if n15 is None else ("RUN" if (n15 if up_side else -n15) >= 20 else "TURN" if (n15 if up_side else -n15) <= -20 else "flat")
                    cx[(mk["kind"], "band" if pos in ("≥u2", "≥u3", "≤d2", "≤d3") else "mid", res)] += 1
        print("== 4. climax / exhaustion marks (cap + ATM) by premium band and what fut did next:", dict(sorted(cx.items())))
        if day == "2026-11-03":
            print("   3 Nov 10:32–10:38 marks on 23,600/23,650 CE:", [(k, hm(m["t"]), m["kind"], m.get("side")) for k in ((23600, "CE"), (23650, "CE")) for m in marks.get(k, []) if 630 <= m["t"] <= 641])
        # ---------------- 5. per-strike CVD divergence at the cap: premium 30-min high, CVD not
        dv = Counter()
        for key in [tuple(x["strikes"][wall(x, i, "CE")]) for i in C[::10] if wall(x, i, "CE") is not None]:
            bl = prints.with_cvd(bars.get(key, []))
            for j in range(10, len(bl)):
                win = bl[j - 10:j]
                if bl[j]["c"] > max(b["c"] for b in win) and bl[j]["cvd"] < max(b["cvd"] for b in win):
                    i = x["mins"].index(bl[j]["t"]) if bl[j]["t"] in x["mins"] else None
                    n15 = fut_after(x, i, 15) if i is not None else None
                    dv["div_high" + ("_up" if n15 is not None and n15 >= 20 else "_dn" if n15 is not None and n15 <= -20 else "_flat")] += 1
        print("== 5. cap-strike CVD divergence at a 30-min premium high (dedup by strike):", dict(dv))
        # ---------------- 6. premium POC reaction vs a shifted placebo (cap strike, day so far)
        react = Counter()
        for key in {tuple(x["strikes"][wall(x, i, "CE")]) for i in C[::15] if wall(x, i, "CE") is not None}:
            bl = bars.get(key, [])
            for j in range(12, len(bl) - 3):
                prof = prints.profile(bl[:j])
                if not prof: continue
                rs = row_size(bl[j]["c"])
                for name, lvl in (("poc", prof["poc"]), ("placebo", prof["poc"] + 3 * rs)):
                    if abs(bl[j]["c"] - lvl) <= rs:
                        back = bl[j + 3]["c"] - bl[j]["c"]
                        react[(name, "rev" if (bl[j]["c"] - bl[j - 3]["c"]) * back < 0 and abs(back) >= rs else "cont/flat")] += 1
        print("== 6. premium at the strike's own POC vs a 3-row placebo: next-3-bar reversal counts:", dict(react))


if __name__ == "__main__":
    main()
