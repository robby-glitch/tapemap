"""The best-trade atlas (31 Oct, her ask): every LEG on every cached day, the state of every read at the minute the move
became visible (born: 40 pts) and at the minute Jarvis called it TREND, and what happened after. DESCRIPTIVE ONLY
(research-findings §1k terms): rows and counts, never a rate; no rule comes out of this without forward rows."""
import tempfile
import glob
import json
import os
import sys

HERE = os.path.join(tempfile.gettempdir(), "jarvis_atlas")
FILES = sorted(glob.glob(os.path.join(HERE, "frames", f"{sys.argv[1] if len(sys.argv) > 1 else 'NIFTY'}_*.json")))


def m2i(s):
    return int(s[:2]) * 60 + int(s[3:5])


def snap(d, i, dr):
    """Every read at minute i, oriented to the leg's direction dr (+1 up / -1 down). Causal: the frame's per-minute series
    are as known at that minute; pushes count only once their answer minute has passed."""
    mins, r, tl = d["mins"], d["reads"], d["timeline"][i]
    t = mins[i]
    w, sp, sy = r["writers"][i], r["speed"][i], r["sync"][i]
    sd, vw, fut, spot = d["sd"][i], d["vwap"][i], d["fut"][i], d["spot"][i]
    s = None
    for x in d.get("sides") or ():
        if x.get("t") and x["t"] <= t:
            s = x
    fu, fst = tl.get("fuel"), tl.get("fuel_state")
    P = [p for p in d["pushes"] if not p.get("artifact") and m2i(t) - 15 < m2i(p["t"]) <= m2i(t)]
    pw = [p for p in P if p["dir"] == dr]
    pa = [p for p in P if p["dir"] == -dr]
    ans = lambda ps: [p["ans"] for p in ps if p.get("am") and p["am"] <= t and p.get("ans") not in (None, "?")]
    fr = tl.get("fronts") or []
    up_side, dn_side = ("CE", "PE") if dr > 0 else ("PE", "CE")
    ahead = sorted((f for f in fr if f["side"] == up_side and dr * (f["k"] - spot) > -5), key=lambda f: dr * f["k"])
    behind = sorted((f for f in fr if f["side"] == dn_side and dr * (spot - f["k"]) > -5), key=lambda f: -dr * f["k"])
    fo = (d["legs"].get("day") or {}).get("fut_oi") or []
    fo = fo[i] if i < len(fo) else None
    row = d["legs"]["rows"][i]
    eff = [p["effort"]["x"] for p in pw if (p.get("effort") or {}).get("x") is not None]
    hi, lo = max(d["fhi"][:i + 1]), min(d["flo"][:i + 1])
    return {
        "t": t,
        "z": None if not sd else round(dr * (fut - vw) / sd, 1),            # + = away from VWAP in the leg's direction
        "day_pos": round((fut - lo) / (hi - lo), 2) if hi > lo else None,   # 0 = day low, 1 = day high (so far)
        "writers": w["state"] or "quiet",
        "w_with": bool(w["state"] in ("UP", "DOWN", "BACK") and w["dir"] == dr),
        "w_against": bool(w["state"] in ("UP", "DOWN", "BACK") and w["dir"] == -dr),
        "w_legs": w.get("legs"),
        "sides": None if s is None else s.get("word"),
        "sides_with": None if s is None else (s.get("fuel") == dr if s.get("fuel") else False),
        "fuel": None if not fu else f"{fu['meaning']} {fu['dir']} {fst}",
        "fuel_with": bool(fu and fst == "LIVE" and (fu["dir"] == "▲") == (dr > 0)),
        "fuel_against": bool(fu and fst == "LIVE" and (fu["dir"] == "▲") != (dr > 0)),
        "speed": sp["word"] if sp.get("x") is not None else "?",
        "fast_with": sp.get("word") == "FAST" and sp.get("dir") == dr,
        "fast_against": sp.get("word") == "FAST" and sp.get("dir") == -dr,
        "all3_with": bool(sy and sy.get("dir") == dr),
        "push_with": len(pw), "ans_with": ans(pw), "push_against": len(pa), "ans_against": ans(pa),
        "effort_with": max(eff) if eff else None,
        "ahead": None if not ahead else f"{ahead[0]['state']} {ahead[0].get('chg')}",
        "ahead_state": None if not ahead else ahead[0]["state"],
        "behind": None if not behind else f"{behind[0]['state']} {behind[0].get('chg')}",
        "behind_state": None if not behind else behind[0]["state"],
        "fut_oi": None if not fo else f"{fo.get('word')} {fo.get('lots')}",
        "fut_oi_word": None if not fo else fo.get("word"),
        "alive": [x["k"] for x in row.get("alive") or ()],
        "risk": [x["k"] for x in row.get("risk") or ()],
        "word": row.get("word"),
    }


out = []
for f in FILES:
    d = json.load(open(f, encoding="utf-8"))
    mins, fut, fhi, flo, rows = d["mins"], d["fut"], d["fhi"], d["flo"], d["legs"]["rows"]
    N = len(mins)
    legs = {}
    for i, row in enumerate(rows):
        g = row.get("leg")
        if not g:
            continue
        L = legs.setdefault((g["dir"], g["origin_t"]), {"day": d["day"], "dir": g["dir"], "origin_t": g["origin_t"],
                                                         "origin": g["origin"], "birth": i, "trend": None, "last": i,
                                                         "pts": 0, "toot": None, "fuelled": None, "sigma": 0})
        L["last"] = i
        if g.get("quality") == "TREND" and L["trend"] is None:
            L["trend"] = i
        if g["pts"] >= L["pts"]:
            L["pts"], L["extreme"], L["extreme_t"] = g["pts"], g["extreme"], g["extreme_t"]
        L["toot"] = L["toot"] or g.get("toot")
        L["fuelled"] = L["fuelled"] or g.get("fuelled")
        L["sigma"] = max(L["sigma"], g.get("sigma_max") or 0)
    for L in legs.values():
        dr, e = L["dir"], min(L["last"] + 1, N - 1)
        L["end"] = rows[e]["word"] if L["last"] + 1 < N else "EOD"
        L["exit_t"], L["exit"] = mins[e], fut[e]
        for tag in ("birth", "trend"):
            i = L[tag]
            if i is None:
                continue
            s = snap(d, i, dr)
            s["entry"] = fut[i]
            s["captured"] = round(dr * (fut[e] - fut[i]), 1)                 # in at this minute, out where the leg ended
            s["mfe"] = round(dr * (L["extreme"] - fut[i]), 1)
            s["mae"] = round(max(0, max(dr * (fut[i] - (flo[j] if dr > 0 else fhi[j])) for j in range(i, e + 1))), 1)
            L[tag + "_snap"] = s
        L["birth"], L["trend"], L["last"] = mins[L["birth"]], L["trend"] and mins[L["trend"]], mins[L["last"]]
        out.append(L)

json.dump(out, open(os.path.join(HERE, "atlas_legs.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(FILES), "days,", len(out), "legs,", sum(1 for L in out if L["trend"]), "became TREND")
