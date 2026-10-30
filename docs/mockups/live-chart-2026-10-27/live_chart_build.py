"""Scratch: the LIVE CHART read of NIFTY fut 5m, bar by bar, for each day given, from move_facts_<day>.json (the record) --
what the server would decide; the mockup page only animates it. Prints a per-day summary, writes live-chart.html.
Usage: python live_chart_build.py <scratch dir> <out dir> <day> [<day> ...]"""
import json
import os
import sys
from datetime import date

S, OUT, DAYS = sys.argv[1], sys.argv[2], sys.argv[3:]
OI_MIN, PX_MIN, ABS_LOTS, ZOR_LOTS, ABS_PTS = 15000, 10, 400, 600, 3   # fut OI per bar, points, lots, points per 100 lots
FLIP, PB0, PB1, MINLEG, PBLEG, BOXLIFE = 0.618, 0.382, 0.618, 60, 120, 12
# Oct expiry 27 Oct: these sessions are its roll week, and the record holds only the Oct contract (NSE_FO|48704), so the
# fut OI reads carry the roll [I] -- the build must join the next month's OI
ROLL_WEEK = {"2026-10-21", "2026-10-22", "2026-10-23", "2026-10-26"}
PRI = ["STOP", "ENTRY", "ZONE", "PALTA", "BURN", "PHANSE", "ROKA", "THAKAN", "ABSORB", "LEVEL", "PB", "SL", "OI", "ZOR"]


def mins(s):
    return int(s[:2]) * 60 + int(s[3:5])


def f(p):
    return f"{p:,.0f}f"


def build(d):
    B, n = d["bars"], len(d["bars"])
    # the basis per bar: fut close - the chain's spot at that close; a bar with no spot borrows the nearest one [M]
    bas = [b["c"] - b["spot"] if b.get("spot") else None for b in B]
    known = [(i, v) for i, v in enumerate(bas) if v is not None]
    bas = [v if v is not None else (min(known, key=lambda kv: abs(kv[0] - i))[1] if known else None) for i, v in enumerate(bas)]

    def fs(p, i):
        return f"{p:,.0f}f|{p - bas[i]:,.0f}s" if bas[i] is not None else f(p)

    def bar_of(m):                                             # the 5-min bar holding minute m
        return max(0, min(n - 1, (m - (9 * 60 + 15)) // 5))

    ev, rows, leg = [], [], None
    # the extension's own marks: one row per mark (its last status), the kinds the face draws, and when each broke
    mk = {}
    for m in d["marks"]:
        mk[(m["t"], m["kind"], m["name"], m["p"])] = m
    marks = []
    for m in sorted(mk.values(), key=lambda x: x["t"]):
        lots = m["lots"] or 0
        if m["kind"] not in ("absorption", "exhaustion", "initiative") or lots < 100 or (m["kind"] == "initiative" and lots < ZOR_LOTS):
            continue
        i, w = bar_of(mins(m["t"])), m["winner"]
        brk = next((j for j in range(i + 1, n) if (B[j]["l"] < m["p"] - 5 if w > 0 else B[j]["h"] > m["p"] + 5)), None)
        marks.append(dict(m, i=i, broke=brk))
    for i, b in enumerate(B):
        pc = B[i - 1]["c"] if i else b["o"]
        dp, doi = b["c"] - pc, (b["oi"] - B[i - 1]["oi"]) if i and b["oi"] and B[i - 1]["oi"] else 0
        lead = (b.get("lead") or {}).get("pe")
        # the leg: a zigzag that turns only past 61.8 % of the leg
        if leg is None:
            leg = {"d": 1 if b["c"] >= b["o"] else -1, "H": b["h"], "L": b["l"], "i0": 0, "iL": 0, "iH": 0}
        if leg["d"] < 0:
            if b["l"] < leg["L"]:
                leg.update(L=b["l"], iL=i)
            size = leg["H"] - leg["L"]
            if size >= MINLEG and (b["c"] - leg["L"]) / size >= FLIP:
                leg = {"d": 1, "L": leg["L"], "H": b["h"], "i0": leg["iL"], "iL": leg["iL"], "iH": i}
                ev.append({"i": i, "k": "PALTA", "p": leg["L"], "side": 1, "w": "PALTA ▲", "s": f"low {f(leg['L'])} · leg upar"})
        else:
            if b["h"] > leg["H"]:
                leg.update(H=b["h"], iH=i)
            size = leg["H"] - leg["L"]
            if size >= MINLEG and (leg["H"] - b["c"]) / size >= FLIP:
                leg = {"d": -1, "H": leg["H"], "L": b["l"], "i0": leg["iH"], "iL": i, "iH": leg["iH"]}
                ev.append({"i": i, "k": "PALTA", "p": leg["H"], "side": -1, "w": "PALTA ▼", "s": f"high {f(leg['H'])} · leg neeche"})
        D = leg["d"]
        size = max(leg["H"] - leg["L"], 1)
        r = (leg["H"] - b["c"]) / size if D > 0 else (b["c"] - leg["L"]) / size
        phase = "PULLBACK" if r >= 0.236 and size >= MINLEG else "CHAL"
        # the OI x price read [I]
        oi = None
        if abs(doi) >= OI_MIN and abs(dp) >= PX_MIN:
            oi = ("SL KAT RAHE" if doi < 0 else "NAYE KHARIDAR") if dp > 0 else ("LONG NIKAL RAHE" if doi < 0 else "NAYE BECHNE WALE")
        oi_dir = {"SL KAT RAHE": 1, "NAYE KHARIDAR": 1, "LONG NIKAL RAHE": -1, "NAYE BECHNE WALE": -1}.get(oi, 0)
        # takat: how many of price / delta / OI / writers side with the leg (a COUNT, never a %)
        votes = {"price": dp * D > 0, "Δ": b["delta"] * D > 0, "OI": (oi_dir * D > 0) if oi else None,
                 "likh": (lead * D >= 10) if lead is not None else None}
        nv = sum(1 for v in votes.values() if v is True)
        # absorbed: a big push against the leg that bought little price (< ABS_PTS points per 100 lots) and no new extreme
        if D > 0 and b["delta"] <= -ABS_LOTS and b["l"] > leg["L"] + 10 and -dp <= ABS_PTS * abs(b["delta"]) / 100:
            ev.append({"i": i, "k": "ABSORB", "p": b["l"], "side": 1, "w": "BECHNE WALE ABSORB",
                       "s": f"{b['delta']:,.0f} lot · low {f(b['l'])} tika"})
        if D < 0 and b["delta"] >= ABS_LOTS and b["h"] < leg["H"] - 10 and dp <= ABS_PTS * abs(b["delta"]) / 100:
            ev.append({"i": i, "k": "ABSORB", "p": b["h"], "side": -1, "w": "KHARIDAR ABSORB",
                       "s": f"+{b['delta']:,.0f} lot · high {f(b['h'])} tika"})
        # whose stops / whose fresh positions: the leg's fuel, and a warning when fresh positions come against it
        if oi == "SL KAT RAHE" and D > 0:
            ev.append({"i": i, "k": "SL", "p": b["h"], "side": 1, "w": "SL KAT RAHE", "s": f"shorts · OI {doi / 1000:+.0f}k"})
        if oi == "LONG NIKAL RAHE" and D < 0:
            ev.append({"i": i, "k": "SL", "p": b["l"], "side": -1, "w": "SL KAT RAHE", "s": f"longs · OI {doi / 1000:+.0f}k"})
        if oi == "NAYE KHARIDAR":
            ev.append({"i": i, "k": "OI", "p": b["l"], "side": 1, "w": "NAYE KHARIDAR" + ("" if D > 0 else " · ulta"), "s": f"OI {doi / 1000:+.0f}k"})
        if oi == "NAYE BECHNE WALE":
            ev.append({"i": i, "k": "OI", "p": b["h"], "side": -1, "w": "NAYE BECHNE WALE" + ("" if D < 0 else " · ulta"), "s": f"OI {doi / 1000:+.0f}k"})
        for m in marks:
            if m["i"] == i:
                k = "PHANSE" if "PHANSE" in m["name"] else {"absorption": "ROKA", "exhaustion": "THAKAN", "initiative": "ZOR"}[m["kind"]]
                ev.append({"i": i, "k": k, "p": m["p"], "side": m["winner"], "w": m["name"][2:].replace(" · ", " "),
                           "s": f"{f(m['p'])} · {m['lots']:,} lot", "broke": m["broke"]})
        rows.append({"i": i, "t": b["t"], "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "delta": b["delta"],
                     "buy": b["buy"], "sell": b["sell"], "doi": doi, "oi_read": oi, "lead": lead, "bands": b["bands"],
                     "leg": {"d": D, "L": leg["L"], "H": leg["H"], "i0": leg["i0"]}, "phase": phase, "r": round(r, 3),
                     "votes": votes, "n": nv})

    # the zone machine's entries: touch, ENTRY (E = the entry bar's close, the machine's stop), STOP LAGA, the rotation band
    eps = []
    zs = sorted(d["zones"], key=lambda z: z["entry_t"])
    for k, z in enumerate(zs):
        dz = 1 if z["side"] == "BUY" else -1
        ti, ei = bar_of(mins(z["touch_t"])), bar_of(mins(z["entry_t"]) + 2)    # the entry bar closes 3 min after its start
        nxt = bar_of(mins(zs[k + 1]["entry_t"]) + 2) if k + 1 < len(zs) else n
        hit = next((j for j in range(ei + 1, n) if (B[j]["l"] <= z["stop"] if dz > 0 else B[j]["h"] >= z["stop"])), None)
        end = min(x for x in (hit, nxt, n) if x is not None)
        if not any(e["k"] == "ZONE" and e["i"] == ti and e["side"] == dz for e in ev):
            ev.append({"i": ti, "k": "ZONE", "p": z["touch_p"], "side": dz, "w": f"ZONE {z['band']} CHHUA", "s": fs(z["touch_p"], ti)})
        ev.append({"i": ei, "k": "ENTRY", "p": z["E"], "side": dz, "w": f"ZONE {z['side']} · ENTRY",
                   "s": f"E {fs(z['E'], ei)} · stop {fs(z['stop'], ei)}"})
        if hit is not None and hit == end:
            ev.append({"i": hit, "k": "STOP", "p": z["stop"], "side": -dz, "w": f"STOP LAGA · {z['side']}",
                       "s": f"{fs(z['stop'], hit)} · {abs(z['E'] - z['stop']):.0f} pts"})
        far = "u2" if dz > 0 else "d2"
        lv = next((j for j in range(ei + 1, end) if B[j]["bands"].get(far) and
                   (B[j]["h"] >= B[j]["bands"][far] if dz > 0 else B[j]["l"] <= B[j]["bands"][far])), None)
        if lv is not None:
            p = B[lv]["bands"][far]
            ev.append({"i": lv, "k": "LEVEL", "p": p, "side": dz, "w": f"{far} CHHUA", "s": f"{fs(p, lv)} · rotation"})
        eps.append({"ei": ei, "end": end, "side": dz, "E": z["E"], "stop": z["stop"], "stopped": hit is not None and hit == end,
                    "le": f"ENTRY {fs(z['E'], ei)}", "ls": f"STOP {fs(z['stop'], ei)}"})

    # boxes: trapped traders (PHANSE .. the bar's far end; their SL is the fuel) and one pullback jagah per leg
    boxes = []
    for e in [e for e in ev if e["k"] == "PHANSE"]:
        i, w = e["i"], e["side"]
        lo, hi = (e["p"], B[i]["h"]) if w > 0 else (B[i]["l"], e["p"])
        # burnt = price closes through the box (the trapped side's stops are there, whatever OI did); OI is a fact beside it
        burn = next((j for j in range(i + 1, min(n, i + BOXLIFE)) if (B[j]["c"] > hi + 5 if w > 0 else B[j]["c"] < lo - 5)), None)
        broke = next((j for j in range(i + 1, min(n, i + BOXLIFE)) if (B[j]["c"] < lo - 5 if w > 0 else B[j]["c"] > hi + 5)), None)
        end = min(x for x in (burn, broke, min(n - 1, i + BOXLIFE)) if x is not None)
        boxes.append({"k": "TRAP", "i": i, "lo": lo, "hi": hi, "end": end, "burn": burn == end and burn is not None,
                      "side": w, "w": f"PHANSE {'BECHNE WALE' if w > 0 else 'KHARIDAR'}"})
        if burn is not None and burn == end:
            q = rows[burn]
            sl = q["oi_read"] == ("SL KAT RAHE" if w > 0 else "LONG NIKAL RAHE")
            ev.append({"i": burn, "k": "BURN", "p": hi if w > 0 else lo, "side": w, "w": "FUEL JALA",
                       "s": f"phanse {'bechne walon' if w > 0 else 'kharidaron'} ka box toota · OI {q['doi'] / 1000:+.0f}k"
                            + (" · SL kate" if sl else " · naye bhi aaye" if q["doi"] > 0 else "")})
    seen = set()
    for r in rows:
        g = r["leg"]
        size = g["H"] - g["L"]
        key = (g["i0"], g["d"])
        if key in seen or size < PBLEG or r["r"] < PB0 - 0.03:
            continue
        seen.add(key)
        lo, hi = (g["H"] - PB1 * size, g["H"] - PB0 * size) if g["d"] > 0 else (g["L"] + PB0 * size, g["L"] + PB1 * size)
        end = next((q["i"] for q in rows[r["i"] + 1:] if (q["leg"]["i0"], q["leg"]["d"]) != key), n - 1)
        boxes.append({"k": "PB", "i": r["i"], "lo": lo, "hi": hi, "end": end, "burn": False, "side": g["d"], "w": "PULLBACK JAGAH"})
        ev.append({"i": r["i"], "k": "PB", "p": hi if g["d"] > 0 else lo, "side": g["d"], "w": "PULLBACK JAGAH MEIN",
                   "s": f"{f(hi)}–{f(lo)} · leg ka 38–62%"})

    # one headline per bar: the strongest thing that happened, else the state
    for r in rows:
        es = sorted([e for e in ev if e["i"] == r["i"]], key=lambda e: PRI.index(e["k"]))
        D = r["leg"]["d"]
        a, who = ("▲", "KHARIDAR") if D > 0 else ("▼", "BECHNE WALE")
        state = (f"{a} PULLBACK · {who} DEFEND" if r["phase"] == "PULLBACK" and r["n"] >= 3 else
                 f"{a} PULLBACK · DABAAV" if r["phase"] == "PULLBACK" and r["n"] <= 1 else
                 f"{a} PULLBACK" if r["phase"] == "PULLBACK" else
                 f"{a} {who} JEET RAHE" if r["n"] >= 3 else f"{a} RUK RAHA" if r["n"] <= 1 else f"{a} CHAL RAHA")
        r["head"] = es[0]["w"] if es else state
        r["head_k"], r["head_side"] = (es[0]["k"], es[0]["side"]) if es else (None, None)
        r["sub"] = (es[0]["s"] + (f" · {es[1]['w']}" if len(es) > 1 and es[0]["k"] != "BURN" else "")) if es else \
            f"Δ {r['delta']:+,.0f} · OI {r['doi'] / 1000:+.0f}k" + (f" · {r['oi_read'].lower()}" if r["oi_read"] else "")
    # the jumps: the moments worth a look
    want = ("ENTRY", "STOP", "BURN", "PHANSE", "ABSORB", "PALTA", "PB")
    jumps, last = [], -9
    for e in sorted(ev, key=lambda e: (e["i"], PRI.index(e["k"]))):
        if e["k"] in want and e["i"] - last >= 3:
            jumps.append([e["i"], f"{rows[e['i']]['t']} {e['w'].lower()}"])
            last = e["i"]
    cvd, cv = [], 0
    for r in rows:
        cv += r["delta"]
        cvd.append(cv)
    dt = date.fromisoformat(d["day"])
    return {"day": d["day"], "label": dt.strftime("%d %b · %a"), "roll": d["day"] in ROLL_WEEK,
            "rows": rows, "ev": ev, "boxes": boxes, "eps": eps,
            "jumps": jumps[:10], "cvd": [min(cvd + [0]), max(cvd + [0])]}


out = {}
for day in DAYS:
    d = json.load(open(os.path.join(S, f"move_facts_{day}.json"), encoding="utf-8"))
    x = build(d)
    out[day] = x
    from collections import Counter
    c = Counter(e["k"] for e in x["ev"])
    lo, hi = min(r["l"] for r in x["rows"]), max(r["h"] for r in x["rows"])
    print(day, f"range {lo:,.0f}-{hi:,.0f} ({hi - lo:.0f})", "events", len(x["ev"]), dict(c), "| eps",
          [(r["t"] if False else x["rows"][e["ei"]]["t"], "BUY" if e["side"] > 0 else "SELL", e["E"], round(e["stop"]), "STOP" if e["stopped"] else "-") for e in x["eps"]])
    print("   jumps", [j[1] for j in x["jumps"]])
tpl = open(os.path.join(S, "live-chart.tpl.html"), encoding="utf-8").read()
html = tpl.replace("/*DATA*/", json.dumps(out, ensure_ascii=False, separators=(",", ":")))
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "live-chart.html"), "w", encoding="utf-8", newline="\n").write(html)
print(len(html), "bytes")
