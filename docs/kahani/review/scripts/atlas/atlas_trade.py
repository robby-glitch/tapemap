"""The trade a trader would take off Jarvis's leg: in at the TREND call (or at the first HOLD pullback after it), out when
the lean flips (PALAT) or at 15:20. Rows only, counts, never a rate."""
import tempfile
import glob, json, os
HERE = os.path.join(tempfile.gettempdir(), "jarvis_atlas")
ARR = {1: "▲", -1: "▼"}
out = []
for f in sorted(glob.glob(os.path.join(HERE, "frames", "NIFTY_*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    mins, fut, fhi, flo, rows = d["mins"], d["fut"], d["fhi"], d["flo"], d["legs"]["rows"]
    N = len(mins)
    seen = set()
    for i, r in enumerate(rows):
        g = r.get("leg")
        if not g or g.get("quality") != "TREND" or (g["dir"], g["origin_t"]) in seen or mins[i] >= "15:00":
            continue
        seen.add((g["dir"], g["origin_t"]))
        dr = g["dir"]
        if r.get("lean") != dr:
            continue
        def trade(a):
            e = next((j for j in range(a + 1, N) if rows[j].get("lean") != dr or mins[j] >= "15:20"), N - 1)
            mfe = max(dr * ((fhi[j] if dr > 0 else flo[j]) - fut[a]) for j in range(a, e + 1))
            mae = max(0, max(dr * (fut[a] - (flo[j] if dr > 0 else fhi[j])) for j in range(a, e + 1)))
            why = "15:20" if mins[e] >= "15:20" else ("EOD" if e == N - 1 else rows[e]["word"])
            return {"in_t": mins[a], "in": fut[a], "out_t": mins[e], "why": why, "pts": round(dr * (fut[e] - fut[a]), 1),
                    "mfe": round(mfe, 1), "mae": round(mae, 1)}
        t1 = trade(i)
        h = next((j for j in range(i + 1, N) if rows[j].get("lean") == dr and rows[j].get("word") == "HOLD"
                  and mins[j] < "15:00"), None)
        h = h if h is not None and all(rows[k].get("lean") == dr for k in range(i, h + 1)) else None
        out.append({"day": d["day"], "dir": dr, "origin_t": g["origin_t"], "leg_pts_at_call": g["pts"],
                    "call": t1, "pullback": trade(h) if h is not None else None})
json.dump(out, open(os.path.join(HERE, "atlas_trades.json"), "w", encoding="utf-8"), ensure_ascii=False)
for x in out:
    c, p = x["call"], x["pullback"]
    print(f"{x['day']} {ARR[x['dir']]} leg {x['leg_pts_at_call']:>3} at call | CALL {c['in_t']} {c['pts']:+6.0f} (mfe {c['mfe']:+.0f} mae {c['mae']:.0f}) out {c['out_t']} {c['why']:<8}"
          + (f" | HOLD {p['in_t']} {p['pts']:+6.0f} (mfe {p['mfe']:+.0f} mae {p['mae']:.0f})" if p else " | no HOLD"))
c = [x["call"]["pts"] for x in out]; p = [x["pullback"]["pts"] for x in out if x["pullback"]]
print(f"\nCALL entries {len(c)}: sum {sum(c):+.0f} pts · >= +40: {sum(1 for v in c if v >= 40)} · < 0: {sum(1 for v in c if v < 0)} · best {max(c):+.0f} · sum without best {sum(c) - max(c):+.0f}")
print(f"HOLD entries {len(p)}: sum {sum(p):+.0f} pts · >= +40: {sum(1 for v in p if v >= 40)} · < 0: {sum(1 for v in p if v < 0)} · best {max(p):+.0f} · sum without best {sum(p) - max(p):+.0f}")
mfe = [x["call"]["mfe"] for x in out]
print(f"CALL mfe: >= +60 in {sum(1 for v in mfe if v >= 60)} of {len(mfe)}; the exit (lean flip) gave back: " +
      f"{sum(x['call']['mfe'] - x['call']['pts'] for x in out):.0f} pts in all")
