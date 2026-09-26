# §D.3: her three 09-25 NIFTY entries, on what the frozen record holds for that day (index candles, the zone rows,
# the OI grid read by GET at 16:25, the live /api/hold rows of her two marked trades, the saved 09:35 check).
# No premium record was frozen for 09-25: fact 5 and every premium figure are "could not check". Writes nothing to the repo.
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import expr as X          # noqa: E402
hold, fronts, board, validate = X.hold, X.fronts, X.board, X.validate
mm = hold.mm
SP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(X.TM, "docs", "mockups", "validate-2026-09-25")
O = json.load(open(os.path.join(SP, "rev5", "oihist_NIFTY_1625.json"), encoding="utf-8"))
F = json.load(open(os.path.join(V, "nifty_2026-09-25.json"), encoding="utf-8"))
ix = {c[1]: [c[5], c[3], c[4]] for c in F["m1"]}
minutes = O["minutes"]
opens = {(float(o["k"]), o["side"]): o["oi"] for o in O["open"]}
g = fronts.grid(minutes)
times, _sp, _ks, S_, RP = g
jx = {t: j for j, t in enumerate(times)}
evs = fronts.folds(minutes, g)


def rec_at(t):
    cut = fronts.cut(minutes, t)
    j = jx.get(max(cut))
    pk = {(k, sd.lower()): opens[(k, sd.lower())] + rp[j] for (k, sd), rp in RP.items() if (k, sd.lower()) in opens}
    fr = fronts.read(cut, pk)
    folds = [{"k": e["k"], "side": e["side"], "t": e["t"], "still": board.still_folded(e, j, S_, RP, jx)}
             for e in evs if jx[e["t"]] <= j and mm(t) - mm(e["t"]) <= hold.FOLD_LIVE]
    return {"t": t, "spot": cut[max(cut)]["spot"], "ix": ix.get(t), "blind": None, "folds": folds,
            "fr": [{"k": f["k"], "side": f["side"], "state": f["state"], "built": f["peak"] > 0} for f in fr]}


mins = [{"t": t, "ix": ix.get(t)} for t in hold.SESSION]
rows = {"12:00": json.load(open(os.path.join(SP, "rev5", "rows_NIFTY-23100CE-long-120121.json"), encoding="utf-8"))["rows"][0],
        "12:04": json.load(open(os.path.join(SP, "rev5", "rows_NIFTY-23200PE-long-120528.json"), encoding="utf-8"))["rows"][0],
        "09:35": json.load(open(os.path.join(V, "check_0935_WAIT_entry.json"), encoding="utf-8"))["now"]}
ENT = [("09:35", -1, "NIFTY 23200PE (09:36, her words; the saved 09:35 check)"),
       ("12:00", 1, "NIFTY 23100CE 12:01:21 (marked)"), ("12:04", -1, "NIFTY 23200PE 12:05:28 (marked)")]
for t, d, name in ENT:
    r = rows[t]
    i = hold.SESSION.index(t)
    rc = rec_at(t)
    M = [dict(m) for m in mins]
    M[i] = {**M[i], **rc}
    g2 = validate.geometry(M, i, d, r["line"])
    tg = g2["target"]
    ss = "PE" if d > 0 else "CE"
    spot = ix[t][0]
    step = 50.0
    beyond = (lambda k: k <= spot + step / 2) if ss == "PE" else (lambda k: k >= spot - step / 2)
    cands = [f for f in rc["fr"] if f["side"] == ss and beyond(f["k"])]
    wall = min(cands, key=lambda f: abs(f["k"] - spot)) if cands else None
    sd = hold.side_of({"tr": dict(zip(hold.ROWS, [w.split(" ")[1] for w in r["trend"]["rows"].split(" · ")]))})
    facts = {
        "speed": "buy" if (r["clock"] or {}).get("paid_last") == t else "neither",
        "room": ("buy" if tg["src"] == "none" or tg["pts"] >= g2["line"] else "sell"),
        "shield": ("sell" if wall and wall["state"] == hold.BLD and wall["built"] else "neither"),
        "regime": ("buy" if sd[0] == ("CALLS" if d > 0 else "PUTS") else "sell" if sd[0] == "no side" else "neither"),
        "premium": "neither — could not check: no 09-25 premium record frozen"}
    nb = sum(v == "buy" for v in facts.values())
    ns = sum(v == "sell" for v in facts.values())
    print(json.dumps({"entry": name, "read": t, "d": d, "spot": spot, "line": g2["line"], "L": g2["L"], "noise": g2["noise"],
                      "target": tg, "wall_behind_sale": wall, "fr": rc["fr"], "side_read": sd,
                      "long_entry": r.get("unlatched") or r.get("verdict"), "payers": r["payers"]["state"],
                      "holders": r["holders"]["state"], "flow": r["flow"]["state"], "trend": r["trend"]["rows"],
                      "facts": facts, "nb": nb, "ns": ns}, default=str))
