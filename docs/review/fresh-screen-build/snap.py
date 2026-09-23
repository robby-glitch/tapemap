"""Read-only snapshot of the live TapeMap API for the fresh-screen mockup.
GET only. Writes snapshot.json next to this file."""
import json, time, urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8765/api/"
IDX = ["NIFTY", "BANKNIFTY", "SENSEX"]


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read())


def down(rows, n=90):
    step = max(1, len(rows) // n)
    out = rows[::step]
    if rows and out[-1] is not rows[-1]:
        out.append(rows[-1])
    return out


health = get("health")
desk = get("desk")
drag = get("drag")
surface = get("surface")
vpin = get("vpin")
paper = get("paperdesk")
warm_all = get("warmap")
sig_all = get("signals?rule=all&kind=all")
today = time.strftime("%Y-%m-%d")

snap = {"taken": time.strftime("%Y-%m-%d %H:%M:%S IST"), "health": {
    "broker": health["broker"], "feed": health.get("feed"), "feed_why": health.get("feed_why"),
    "coverage": health["coverage"], "latency": health.get("latency")},
    "participant": warm_all.get("participant"),
    "vpin": {"state": vpin["state"], "series": vpin["series"], "fast": vpin["fast_series"],
             "fast_why": vpin["fast_why"], "backfill": vpin["backfill"]},
    "record": {k: sig_all[k] for k in ("total", "five_c", "legacy", "arms", "no_rate_why")},
    "paper": {k: paper["desk"].get(k) for k in ("note", "capital", "lots", "realized_total", "day_pnl", "open", "marks",
                                               "risk", "closed_today", "by_index", "by_strategy", "day_refusals",
                                               "accounting_note", "hedge")},
    "idx": {}}
# populations kept apart (house rule 5): counted per (rule, kind, index), never pooled
from collections import Counter
cnt = Counter((r.get("rule") or "legacy", "arm" if r.get("kind") == "arm" else "entry", r.get("index")) for r in sig_all["rows"])
snap["record"]["by_pop"] = [{"rule": a, "kind": b, "idx": c, "n": n} for (a, b, c), n in sorted(cnt.items(), key=str)]
snap["record"]["scored_by_pop"] = [{"rule": a, "kind": b, "idx": c, "n": n} for (a, b, c), n in sorted(Counter(
    (r.get("rule") or "legacy", "arm" if r.get("kind") == "arm" else "entry", r.get("index"))
    for r in sig_all["rows"] if r.get("mfe") is not None).items(), key=str)]

for i in IDX:
    d = get(f"data?idx={i}")
    day = d["days"][0]
    bars = day["bars"]
    last = bars[-1]
    fut = last["fut"]
    ch = get(f"chain?idx={i}")
    oh = get(f"oihist?idx={i}")
    wm = warm_all["indices"].get(i) or {}
    fr = get(f"frame?idx={i}")
    fr = fr if fr.get("ok") else {"ok": False, "why": fr.get("why")}
    # the four fronts' OI-change series off the minute grid, plus spot
    mins = oh.get("minutes") or {}
    marks = sorted(mins)
    fronts = oh.get("fronts") or []
    fser = {}
    for f in fronts:
        col = 0 if f["side"] == "CE" else 1
        key = f"{int(f['k'])}{f['side']}"
        fser[key] = [[m, (mins[m]["k"].get(str(int(f["k"]))) or [None, None])[col]] for m in marks]
    spot_ser = [[m, mins[m].get("spot")] for m in marks]
    rows = [r for r in sig_all["rows"] if r.get("index") == i and r.get("day") == today]
    rows = [{k: r.get(k) for k in ("kind", "t", "first_t", "side", "band", "rule", "px", "level", "trigger", "rearm",
                                    "gate", "extreme", "ref_high", "ref_low")} | {"plays": (r.get("ctx") or {}).get("plays")}
            for r in reversed(rows)]  # chronological
    atm = ch.get("atm")
    heat = sorted([h for h in (wm.get("heat") or [])], key=lambda h: h["k"])
    dk = desk["indices"].get(i) or {}
    sf = surface["indices"].get(i) or {}
    dg = drag["indices"].get(i) or {}
    snap["idx"][i] = {
        "interval": d["interval"], "basis": d.get("basis"), "spot": d.get("spot"), "expiry": d.get("expiry"),
        "bars_n": len(bars), "last_t": last["t"],
        "bars": [{"t": b["t"], "o": b["fut"]["o"], "h": b["fut"]["h"], "l": b["fut"]["l"], "c": b["fut"]["c"],
                  "vwap": b["fut"]["vwap"], "u2": b["fut"]["u2"], "u3": b["fut"]["u3"], "d2": b["fut"]["d2"],
                  "d3": b["fut"]["d3"]} for b in bars],
        "fut": {k: fut[k] for k in ("o", "h", "l", "c", "vwap", "u1", "d1", "u2", "d2", "u3", "d3", "z", "bw_r")},
        "gamma": last.get("gamma"), "ctx": last.get("ctx"), "engine_events": day.get("events"),
        "zone_buy": (day.get("zone_state") or [None])[-1], "zone_sell": (day.get("zone_state_sell") or [None])[-1],
        "pivots": day.get("pivots"),
        "chain": {"ts": ch.get("ts"), "atm": atm, "expiry": ch.get("expiry"), "spot": ch.get("spot"),
                  "wall_log": (ch.get("metrics") or {}).get("wall_log", [])[-12:],
                  "strikes": [s for s in ch.get("strikes") or [] if atm and abs(s["k"] - atm) <= 8 * (50 if i == "NIFTY" else 100)]},
        "fronts": fronts, "fronts_why": oh.get("fronts_why"), "broke": oh.get("broke"),
        "front_series": fser, "spot_series": spot_ser, "backfill_marks": oh.get("backfill_marks"),
        "warmap": {k: wm.get(k) for k in ("ts", "spot", "band", "levels", "dwell", "runways", "driver", "flip_px",
                                           "max_pain", "sequence", "backfill")} | {"heat": heat},
        "desk": {k: dk.get(k) for k in ("regime", "view", "game", "directional", "lot_size", "why")} | {
            "candidates": [{k: c.get(k) for k in ("name", "status", "case", "why", "edge", "lots", "legs", "net_delta", "margin")}
                           for c in dk.get("candidates") or []], "best": dk.get("best")},
        "surface": {"fit": sf.get("fit"), "richest": sf.get("richest"), "cheapest": sf.get("cheapest"),
                    "day": ({**{k: v for k, v in (sf.get("day") or {}).items() if k != "series"},
                             "series": down((sf.get("day") or {}).get("series") or [])} if sf.get("day") else None)},
        "drag": ({**{k: v for k, v in dg.items() if k != "day"},
                  "day": ({**{k: v for k, v in (dg.get("day") or {}).items() if k != "series"},
                           "series": down((dg.get("day") or {}).get("series") or [])} if dg.get("day") else None)}
                 if dg else None),
        "record_today": rows,
        "frame": ({k: fr.get(k) for k in ("ts", "head", "where", "trapped", "tape", "breadth", "setup")} |
                  {"walls": [r for r in (fr.get("walls") or {}).get("rows", []) if r["kind"] in ("S", "B")],
                   "watch": (fr.get("walls") or {}).get("watch")} if fr.get("ok") else fr),
    }

out = Path(__file__).with_name("snapshot.json")
out.write_text(json.dumps(snap, default=str), encoding="utf-8")
print(out, out.stat().st_size, snap["taken"])
