"""tools/look_report.py -- §1k's ONE LOOK as one document: FADE + RIDE, row by row (research-findings §1k).

    python tools/look_report.py   reads data/confluence/first_look.json (tools/confluence_score.py --look-amendment-2)
                                  and data/confluence/ride_first_look.json (tools/ride_score.py --look-amendment-2),
                                  writes docs/setup-review/LOOK-2026-10-21.md and data/confluence/look_2026-10-21.json.

It computes nothing new: it joins the two scorers' rows, puts them in one table, adds §4's fields per cell and a
trader's sanity flags per row (flags(): what looks wrong is printed, never hidden). It refuses unless both inputs say
they ran under §1k. NO HIT RATE, WIN RATE OR "X OF Y" ANYWHERE: rows and §4's fields only. The control rows go in the
JSON only.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FADE_IN = os.path.join("data", "confluence", "first_look.json")
RIDE_IN = os.path.join("data", "confluence", "ride_first_look.json")
OUT_MD = os.path.join("docs", "setup-review", "LOOK-2026-10-21.md")
OUT_JSON = os.path.join("data", "confluence", "look_2026-10-21.json")
STEP = {"NIFTY": 50, "BANKNIFTY": 100, "SENSEX": 100}
HOW = {"stop": "stop", "target": "target VWAP", "mark": "15:20", "line": "line", "gave_up": "gave up"}
PREM = (0.0003, 0.03)          # an ATM premium outside 0.03%..3% of spot is not an ATM premium on these indices [I]
BASIS = (-0.003, 0.012)        # fut - spot outside -0.3%..+1.2% of spot is not a carry [I]


def _m(t):
    return int(t[:2]) * 60 + int(t[3:5])


def _hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def flags(r):
    """A trader's checks on one row -> [what looks wrong]."""
    out = []
    d, E, x = r["d"], r["E"], r["exit"]
    if r.get("range") and not r["range"][0] <= E <= r["range"][1]:
        out.append(f"E {E} outside the session range {r['range'][0]}-{r['range'][1]} before entry")
    if r.get("close_at_entry") is not None and abs(r["close_at_entry"] - E) > 0.5:
        out.append(f"E {E} is not the 1-min close at entry ({r['close_at_entry']})")
    if _m(r["exit_time"]) <= _m(r["time"]):
        out.append(f"exit not after entry ({r['exit_time']} vs {r['time']})")
    calc = d * (x - E) / r["risk0"]
    if abs(calc - r["R"]) > 0.001:
        out.append(f"R {r['R']} != (exit - E) / initial risk {calc:.4f}")
    if r.get("mfe") is not None and not -r["mae"] - 0.5 <= d * (x - E) <= r["mfe"] + 0.5:
        out.append(f"exit {x} outside the path's MFE {r['mfe']} / MAE {r['mae']}")
    if r.get("mfe") is not None and r["mfe"] < 0:
        out.append(f"never traded back to E after entry (MFE {r['mfe']}: the next 1-min bar opened away from it)")
    for n in (30, 60):
        if r.get(f"move{n}") is None and _m(r["time"]) + n <= 15 * 60 + 30:
            out.append(f"no 1-min bar at +{n}m (a hole in the futures record)")
    sp = r.get("spot")
    if sp:
        if not BASIS[0] * sp <= E - sp <= BASIS[1] * sp:
            out.append(f"basis E - spot {E - sp:+.1f} implausible for a future")
    o = r.get("opts")
    if not o:
        out.append("no option premiums recorded at entry / exit")
        return out
    if sp and abs(o["k"] - sp) > STEP.get(r["index"], 100):
        out.append(f"ATM strike {o['k']} is {o['k'] - sp:+.0f} from spot")
    for p in o["atm_in"]:
        if p is None or not (sp and PREM[0] * sp <= p <= PREM[1] * sp):
            out.append(f"ATM premium {p} implausible ({'no spot' if not sp else f'{(p or 0) / sp * 100:.2f}% of spot'})")
    if any(p is None for p in o["atm_out"]):
        out.append("no exit premium on an ATM leg")
    if o.get("itm_in") is not None and o["atm_in"][0] is not None and o["itm_in"] < o["atm_in"][0]:
        out.append(f"1-ITM premium {o['itm_in']} below the ATM's {o['atm_in'][0]}")
    if None not in o["atm_in"] and o.get("buy"):
        ce, pe = o["atm_in"] if o["buy"] == "CE" else o["atm_in"][::-1]
        f = o["k"] + ce - pe                     # put-call parity: the options' own forward at entry
        step = STEP.get(r["index"], 100)
        if abs(o["k"] - f) > 1.5 * step and abs(f - E) > 1.5 * step:
            out.append(f"the options price the underlying at {f:,.0f} (chain spot {sp:,.0f}, fut {E:,.0f}): strike "
                       f"{o['k']} is {o['k'] - f:+.0f} from the options' own forward, so 'ATM' here is not quite ATM")
    return out


def _fade_rows(res):
    rows = []
    for cell, c in res["cells"].items():
        kind, side, _g = cell.split(" ", 2)
        xs = {(x["day"], x["index"], x["t"]): x for x in c["expression"]["rows"]}
        for t in c["confluence"]:
            x = xs.get((t["day"], t["index"], t["trigger_t"]))
            ex = t.get("extras") or {}
            rows.append({"setup": f"FADE {kind}", "side": side, "cell": cell, "day": t["day"], "index": t["index"],
                         "d": 1 if side == "BUY" else -1, "time": t["close"], "E": t["E"], "spot": t.get("spot"),
                         "exit": t["exit"], "exit_time": _hm(_m(t["exit_t"]) + 1), "how": HOW[t["how"]], "R": t["R"],
                         "risk0": abs(t["stop"] - t["E"]), "mfe": ex.get("mfe"), "mae": ex.get("mae"),
                         "move30": ex.get("move30"), "move60": ex.get("move60"), "range": ex.get("range"),
                         "close_at_entry": ex.get("close_at_entry"),
                         "opts": None if not x else {"k": x["k"], "buy": x["buy"], "sell": x["sell"],
                                                     "atm_in": [x["buy_px"], x["sell_px"]],
                                                     "atm_out": [x["buy_exit"], x["sell_exit"]], "itm_in": None,
                                                     "pts": {f"buy {x['buy']}": x["buy_pts"],
                                                             f"sell {x['sell']}": x["sell_pts"]}}})
    return rows


def _ride_rows(res):
    rows = []
    for cell, c in res["cells"].items():
        for t in c["ride"]:
            d = -1 if cell.startswith("DOWN") else 1
            ex, x = t.get("extras") or {}, t.get("expressions")
            leg = (lambda n: (x.get(n) or {}))
            rows.append({"setup": f"RIDE {'▼' if d < 0 else '▲'}", "side": "SELL" if d < 0 else "BUY", "cell": cell,
                         "day": t["day"], "index": t["index"], "d": d, "time": t["t"], "E": t["E"],
                         "spot": t.get("spot"), "exit": t["exit"], "exit_time": t["exit_t"], "how": HOW[t["how"]],
                         "R": t["R"], "risk0": abs(t["line0"] - t["E"]), "mfe": ex.get("mfe"), "mae": ex.get("mae"),
                         "move30": ex.get("move30"), "move60": ex.get("move60"), "range": ex.get("range"),
                         "close_at_entry": ex.get("close_at_entry"), "stalled": t.get("stalled"),
                         "opts": None if not x else {
                             "k": x["k"], "itm_k": x["itm_k"], "buy": x["buy"], "sell": x["sell"],
                             "atm_in": [leg("buy_atm").get("in"), leg("sell_atm").get("in")],
                             "atm_out": [leg("buy_atm").get("out"), leg("sell_atm").get("out")],
                             "itm_in": leg("buy_itm").get("in"),
                             "pts": {f"buy {x['buy']}": leg("buy_atm").get("pts"),
                                     f"buy 1-ITM {x['buy']}": leg("buy_itm").get("pts"),
                                     f"sell {x['sell']}": leg("sell_atm").get("pts")}}})
    return rows


def _f(v, nd=1, sign=True):
    return "—" if v is None else (f"{v:+,.{nd}f}" if sign else f"{v:,.{nd}f}")


def _opts(o):
    if not o:
        return "—"
    return f"{o['k']:.0f}: " + " · ".join(f"{n} {_f(p, 1)}" for n, p in o["pts"].items())


def markdown(rows, cells, srcs):
    L = ["# LOOK 2026-10-21 · FADE + RIDE on the recorded days (§1k, one look)", "",
         "- **Ran under** research-findings §1k (Amendment 2): Mary asked what the market did after these conditions "
         "met. The rules are frozen as registered; a rule changed after this look is a new registration.",
         f"- **Sources:** `{srcs[0]}` and `{srcs[1]}` (each scorer's `--look-amendment-2`, run once). Readings: in each.",
         "- **Prices** are futures points [M from bars]; spot = the chain's at the entry's last minute. Times are clock "
         "ENDs: entry = the bar close, exit = the minute by which it happened. MFE / MAE = entry to exit; +30m / +60m = "
         "the move after entry in the trade's direction, whatever the exit. Options = premium points per unit at the "
         "same strike, entry to exit [M].",
         "- **No hit rate is printed, here or anywhere.** n < 20 in every cell: every verdict is INCONCLUSIVE.", "",
         "## Every entry", "",
         "| day | time | index | setup | side | E fut | spot | exit | exit time | exit why | R | MFE | MAE | +30m | +60m | options (pts) | flags |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['day']} | {r['time']} | {r['index']} | {r['setup']} | {r['side']} | {_f(r['E'], 1, False)} | "
                 f"{_f(r['spot'], 1, False)} | {_f(r['exit'], 1, False)} | {r['exit_time']} | {r['how']} | "
                 f"{_f(r['R'], 2)} | {_f(r['mfe'])} | {_f(r['mae'])} | {_f(r['move30'])} | {_f(r['move60'])} | "
                 f"{_opts(r['opts'])} | {len(r['flags']) or ''} |")
    for name, cs in cells.items():
        L += ["", f"## {name}: §4 per cell", "",
              "| cell | n | mean R | mean R w/o best | control n | control mean R | largest day's share | verdict |",
              "|---|---|---|---|---|---|---|---|"]
        for c, v in cs.items():
            share = "—" if v["largest_day_share"] is None else f"{v['largest_day_share'] * 100:.0f}%"
            L.append(f"| {c} | {v['n']} | {_f(v['mean_R'], 2)} | {_f(v['mean_R_ex_best'], 2)} | {v['control_n']} | "
                     f"{_f(v['control_mean_R'], 2)} | {share} | {v['verdict']} |")
    L += ["", "## The futures basis behind these rows (E fut − chain spot, at entry)", ""]
    for idx in sorted({r["index"] for r in rows}):
        bs = [(r["E"] - r["spot"], r["day"]) for r in rows if r["index"] == idx and r.get("spot")]
        if bs:
            lo, hi = min(bs), max(bs)
            L.append(f"- {idx}: {lo[0]:+,.0f} ({lo[1]}) … {hi[0]:+,.0f} ({hi[1]}), {len(bs)} rows")
    L.append("- R, MFE and MAE are futures points on futures bars; the basis moves only the spot column and the "
             "trail's FLIP→fut (the READ row's own basis, §1k).")
    flagged = [r for r in rows if r["flags"]]
    L += ["", "## Sanity flags (a trader's checks; printed, never hidden)", ""]
    L += [f"- {r['day']} {r['time']} {r['index']} {r['setup']}: " + "; ".join(r["flags"]) for r in flagged] or \
         ["- none: every entry sits inside its day's range at its time, every exit is after its entry, every R is "
          "(exit - E) / initial risk, and every ATM premium is a plausible ATM premium."]
    return "\n".join(L) + "\n"


def main(argv=None):
    os.chdir(HERE)
    res = {}
    for name, p in (("FADE", FADE_IN), ("RIDE", RIDE_IN)):
        if not os.path.exists(p):
            print(f"REFUSED: {p} is missing; run the scorer's --look-amendment-2 first.")
            return 2
        with open(p, encoding="utf-8") as f:
            res[name] = json.load(f)
        if not str(res[name].get("amendment") or "").startswith("§1k"):
            print(f"REFUSED: {p} did not run under §1k.")
            return 2
    rows = sorted(_fade_rows(res["FADE"]) + _ride_rows(res["RIDE"]), key=lambda r: (r["day"], r["time"], r["index"]))
    for r in rows:
        r["flags"] = flags(r)
    cells = {n: {c: v["verdict"] for c, v in res[n]["cells"].items()} for n in ("FADE", "RIDE")}
    doc = {"amendment": res["RIDE"]["amendment"], "run_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "sources": {"FADE": FADE_IN, "RIDE": RIDE_IN}, "rows": rows, "cells": cells,
           "controls": {"FADE": [t for c in res["FADE"]["cells"].values() for t in c["control"]],
                        "RIDE": [t for c in res["RIDE"]["cells"].values() for t in c["control"]]},
           "readings": {n: res[n]["readings"] for n in ("FADE", "RIDE")}}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    text = markdown(rows, cells, (FADE_IN, RIDE_IN))
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(text)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
