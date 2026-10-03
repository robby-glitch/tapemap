import io, contextlib
import analyze7 as A
with contextlib.redirect_stdout(io.StringIO()):
    import analyze10 as G
ends = {}
tot = 0
rows = []
for r in A.R:
    ss = [s for s in r["snaps"] if s["t"] <= "15:00"]
    gv = G.ivg(r)
    gv_t = A.hm(r["day"], gv["t"] + 60000) if gv else None
    on, start = False, None
    for i, s in enumerate(ss):
        p = s["head"].startswith("HOLD") and s["dE"] is not None and s["w"] and s["dE"] <= -s["w"] and s["Wst"] in ("building", "stopped")
        if p and not on:
            on, start = True, s
        elif on and not p:
            if s["head"].startswith("FOLD"):
                why = "rev 6 FOLD"
            elif gv_t and s["t"] >= gv_t and s["Wst"] == "off":
                why = "GAVE UP (iv-g)"
            elif s["Wst"] == "off":
                why = "W off (no fold: flow/VPIN with her or price no longer against)"
            elif s["dE"] is not None and s["dE"] > -s["w"]:
                why = "price back within w of entry"
            else:
                why = "other: " + s["head"][:12]
            ends[why] = ends.get(why, 0) + 1
            rows.append((r["name"], start["t"], s["t"], start["pct"], s["pct"], why))
            on = False
    if on:
        ends["15:00"] = ends.get("15:00", 0) + 1
        rows.append((r["name"], start["t"], "15:00", start["pct"], ss[-1]["pct"], "15:00"))
for x in rows:
    print(f"   {x[0]:28} {x[1]}-{x[2]} {x[3]:+.0f} -> {x[4]:+.0f} % | {x[5]}")
print(len(rows), "spells", ends)
