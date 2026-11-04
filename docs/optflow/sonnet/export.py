"""Option order-flow reader: export the real per-close data for the mockup (read-only on data/, writes only ./data_*.json
and ./mockup.html built from ./mockup.tpl.html). Run from anywhere:
    python -I -X utf8 export.py [2026-11-03 2026-11-04]
Reuses: brainstorm/strike_bands.py (bars3, who, load), prints.pct_rank, round7's own-normal + band signature rules
(the causal halves; 'next close' halves are resolved by the page, never here). NIFTY only (SENSEX: same engine, not exported).
Everything per close e (her grid, (e-555)%3==2) uses data up to e only."""
import json, os, sys, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
TM = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, TM)
import prints
from prints import pct_rank
BR = os.path.join(TM, "docs", "optflow", "brainstorm", "strike_bands.py")
ns = {"__name__": "sb"}
exec(open(BR, encoding="utf-8").read().split("\nfor day in")[0], ns)      # the file runs a study at import: head only
O, bars3, who, load = ns["O"], ns["bars3"], ns["who"], ns["load"]
REC = json.load(open(os.path.join(TM, "docs", "optflow", "fable", "scrip_recovered.json"), encoding="utf-8"))
LOT, STEP, READ_FROM, RANK_MIN = 75, 50, 584, 6
hm = lambda m: "%02d:%02d" % divmod(m, 60)


def patch_scrip(day):
    """03 NOV contracts left today's scrip master: add the recovered file -> (strike, side) rows (fable/load.recover_map)."""
    s = O.scrip()
    for fid, (k, sd) in REC.get(day, {}).items():
        if fid not in s:
            r = [""] * 15; r[0] = "NSE"; r[1] = "D"; r[6] = "NIFTY"; r[12] = EXP_HINT[0]; r[13] = str(k); r[14] = sd
            s[fid] = r


EXP_HINT = [""]


def rd(x, n=2):
    return None if x is None else round(x, n)


def export(day):
    ch = O.load_chain(day, "NIFTY")
    EXP_HINT[0] = ch[max(ch)]["expiry"]
    patch_scrip(day)
    exp, snap, spot, flow, fut = load(day)
    _, _, B, fb = bars3(day)
    last_ch = max(ch)
    closes = [e for e in range(557, 930, 3) if e <= last_ch and spot.get(e)]
    hist = {}          # key -> {vol, adel, rng lists}; prev bar
    prevb = {}
    cum = {}           # key -> [cumdelta, cumvol] over closes so far
    out = {"day": day, "exp": exp, "src": f"chain to {hm(last_ch)}", "closes": []}
    bymin = lambda m: ch.get(m)
    for e in closes:
        sp = spot[e]; atm = round(sp / STEP) * STEP
        cs = ch.get(e) or ch[max(m for m in ch if m <= e)]
        cd = {(s["k"], sd): (s.get(sd) or {}) for s in cs["strikes"] for sd in ("ce", "pe")}
        rec = {"e": e, "t": hm(e), "sp": rd(sp, 1), "atm": atm}
        f = fb.get(e)
        if f:
            rec["fut"] = {k: rd(f[k], 1) for k in ("c", "h", "l", "vwap", "u2", "d2", "u3", "d3")}
        # chain OI of the nine nearest strikes + walls over the whole chain
        rec["oi"] = [[k, (cd.get((k, "ce")) or {}).get("oi"), (cd.get((k, "pe")) or {}).get("oi")] for k in range(atm - 250, atm + 251, STEP)]
        ce = [(v.get("oi") or 0, k) for (k, sd), v in cd.items() if sd == "ce" and k > sp]
        pe = [(v.get("oi") or 0, k) for (k, sd), v in cd.items() if sd == "pe" and k < sp]
        rec["wall"] = {"ce": max(ce)[::-1] if ce else None, "pe": max(pe)[::-1] if pe else None}
        rows = []
        for k in range(atm - 250, atm + 251, STEP):
            for sd in ("ce", "pe"):
                key = (k, sd)
                b = next((x for x in B.get(key, []) if x["e"] == e), None)
                if not b:
                    rows.append({"k": k, "s": sd, "na": 1})
                    continue
                h = hist.setdefault(key, {"vol": [], "adel": [], "rng": []})
                rng = b["h"] - b["l"]; adel = abs(b["d"])
                r = {"k": k, "s": sd, "c": rd(b["c"]), "vw": rd(b["vwap"]), "u2": rd(b["u2"]), "u3": rd(b["u3"]), "d2": rd(b["d2"]), "d3": rd(b["d3"]),
                     "h": rd(b["h"]), "l": rd(b["l"]), "v": b["v"], "d": b["d"], "oi": b["oi"], "doi": b["doi"], "who": who(b["doi"], b["d"])}
                # FIRM: the label survives a 1-min window shift (delta e-3..e-1, dOI = oi(e-1) - oi(e-4))
                rows_f = flow[key]
                try:
                    ds = sum(rows_f[m]["delta"] or 0 for m in (e - 3, e - 2, e - 1))
                    ois = snap[e - 1][key][0] - snap[e - 4][key][0]
                    r["firm"] = int(who(ois, ds) == r["who"])
                except (KeyError, TypeError):
                    r["firm"] = None
                # own day-normal ranks (strictly below, nothing before 6 closes: prints.pct_rank)
                r["pv"], r["pa"], r["pr"] = (rd(pct_rank(h[m], x), 2) for m, x in (("vol", b["v"]), ("adel", adel), ("rng", rng)))
                med = st.median(h["rng"]) if len(h["rng"]) >= RANK_MIN else None
                # chain delta -> implied index delta in lots; biggest single-price print in delta-lots
                dl = (cd.get(key) or {}).get("delta")
                r["cdl"] = rd(dl, 3)
                r["imp"] = rd(b["d"] * dl / LOT, 1) if dl is not None else None
                bg = (0, None, None)
                if dl is not None:
                    for m in (e - 2, e - 1, e):
                        for lv in (rows_f.get(m) or {}).get("levels", []):
                            for side, q in (("B", lv.get("buy_volume") or 0), ("S", lv.get("sell_volume") or 0)):
                                if q * abs(dl) / LOT > bg[0]:
                                    bg = (q * abs(dl) / LOT, side, lv["price"])
                r["big"] = [round(bg[0]), bg[1], bg[2]] if bg[1] else None
                # location against its OWN premium bands
                loc = "BU" if b["h"] >= b["u3"] else "AU" if b["h"] >= b["u2"] else "BD" if b["l"] <= b["d3"] else "AD" if b["l"] <= b["d2"] else "IN"
                r["loc"] = loc
                # causal signature candidates (round7 rules minus the 'next close' halves)
                p = prevb.get(key)
                sg = []
                if e >= READ_FROM and r["pv"] is not None and loc != "IN":
                    up = loc in ("AU", "BU")
                    abn = (r["pv"] >= .9) or (r["pa"] is not None and r["pa"] >= .9)
                    abn95 = (r["pv"] >= .95) or (r["pa"] is not None and r["pa"] >= .95)
                    small = (med is not None and rng <= med) or (up and b["c"] < b["u2"]) or ((not up) and b["c"] > b["d2"])
                    if abn and small: sg.append("A")
                    if abn95 and loc in ("BU", "BD"): sg.append("C")
                    if abn and up and b["c"] >= b["u2"] and r["who"] == "COVER": sg.append("I")
                    if p:
                        hi6 = max([q["h"] for q in prevb_hist.get(key, [])[-6:]], default=None)
                        lo6 = min([q["l"] for q in prevb_hist.get(key, [])[-6:]], default=None)
                        fall = b["v"] < p["v"] and adel < abs(p["d"]) and (b["doi"] is None or p["doi"] is None or b["doi"] < p["doi"])
                        if fall and ((up and hi6 is not None and b["h"] > hi6) or ((not up) and lo6 is not None and b["l"] < lo6)):
                            sg.append("E")
                r["sg"] = "".join(sg)
                cc = cum.setdefault(key, [0, 0]); cc[0] += b["d"]; cc[1] += b["v"]
                r["cd"], r["cv"] = cc
                for m, x in (("vol", b["v"]), ("adel", adel), ("rng", rng)):
                    h[m].append(x)
                prevb[key] = {"v": b["v"], "d": b["d"], "doi": b["doi"]}
                prevb_hist.setdefault(key, []).append({"h": b["h"], "l": b["l"]})
                rows.append(r)
        rec["rows"] = rows
        out["closes"].append(rec)
    return out



def jarvis(day):
    """Jarvis's NIFTY call per minute, from data/jarvis/call_<day>.jsonl (files only, never /api/jarvis). The `missing` lists repeat, so
    they go in one table. Pieces (each read's text and side) exist only for the five 3 Nov moments in jarvis-panel-sonnet/calls_3nov.json."""
    out = {"rows": {}, "ms": [], "moments": {}}
    tab = {}
    p = os.path.join(TM, "data", "jarvis", f"call_{day}.jsonl")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            if not l.strip():
                continue
            r = json.loads(l)
            if r.get("idx") != "NIFTY":
                continue
            ids = []
            for m in r.get("missing") or []:
                ids.append(tab.setdefault(m, len(tab)))
            c = r.get("count") or {}
            out["rows"][r["t"]] = {"w": r.get("word"), "st": r.get("state"), "l": r.get("lean"), "s": r.get("since"), "c": [c.get("with"), c.get("against"), c.get("N")],
                                   "leg": r.get("leg"), "wl": r.get("wrong_line"), "ms": ids, "bl": r.get("blind"), "sh": r.get("shown")}
    out["ms"] = [k for k, _ in sorted(tab.items(), key=lambda kv: kv[1])]
    cj = os.path.join(TM, "docs", "kahani", "review", "jarvis-panel-sonnet", "calls_3nov.json")
    if day == "2026-11-03" and os.path.exists(cj):
        for k, m in json.load(open(cj, encoding="utf-8"))["moments"].items():
            c = m["call"]
            out["moments"][k] = {"pieces": c["count"].get("pieces"), "unread": c["count"].get("unread"), "buyer": c.get("buyer"), "seller": c.get("seller"),
                                 "pause": (c.get("pause") or {}).get("line"), "day": c.get("day")}
    return out

prevb_hist = {}

if __name__ == "__main__":
    days = sys.argv[1:] or ["2026-11-03", "2026-11-04"]
    allv = {}
    for d in days:
        prevb_hist.clear()
        x = export(d)
        allv[d] = x
        json.dump(x, open(os.path.join(HERE, f"data_{d}.json"), "w", encoding="utf-8"), separators=(",", ":"))
        print(d, x["exp"], x["src"], len(x["closes"]), "closes")
    tpl = os.path.join(HERE, "mockup.tpl.html")
    if os.path.exists(tpl):
        html = open(tpl, encoding="utf-8").read().replace("/*DATA*/", "window.__DATA=" + json.dumps(allv, separators=(",", ":")) + ";")
        open(os.path.join(HERE, "mockup.html"), "w", encoding="utf-8").write(html)
        print("mockup.html", len(html) // 1024, "KB")
    tpl2 = os.path.join(HERE, "mockup-v2.tpl.html")
    if os.path.exists(tpl2):                      # round 2: Jarvis's calls (files only) beside the option flow
        for d in allv:
            allv[d]["jar"] = jarvis(d)
        html = open(tpl2, encoding="utf-8").read().replace("/*DATA*/", "window.__DATA=" + json.dumps(allv, separators=(",", ":")) + ";")
        open(os.path.join(HERE, "mockup-v2.html"), "w", encoding="utf-8").write(html)
        print("mockup-v2.html", len(html) // 1024, "KB")
