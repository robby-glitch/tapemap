"""analyze10.py -- (ii-F) her literal rule as a FOLD; (iv-g) gave-up under pressure unless FLOW or VPIN is WITH; (iv) falsifier verdicts."""
import analyze7 as A
import analyze8 as B


def lit(r):
    """(ii-F): at entry, HOLD, >= 2 of the four reads AGAINST and the future >= w against her entry -> FOLD."""
    evs = B.evs_of(r)
    return A.first(evs, lambda e: e["mode"] == "at entry" and (e["head"] or "").startswith("HOLD") and A.nag(e["chips"]) >= 2 and A.against_px(e))


def ivg(r):
    evs = B.evs_of(r)
    f6 = A.first(evs, lambda e: e["kind"] == "fold")
    ok = False
    for e in evs:
        if f6 and e["t"] > f6["t"]:
            break
        if e["kind"] == "oi_event":
            ok = e["mode"] == "at entry" and A.against_px(e) and e["chips"].get("O") != "CAN'T CHECK"
        elif not e["oi_ev"]:
            ok = False
        if ok and e["oi_ev"] and e["mode"] == "at entry" and A.against_px(e) and "WITH" not in (e["chips"].get("F"), e["chips"].get("V")):
            return e
    return None


def verdict(r, e):
    """(iv)'s falsifier, 20 min: W rebuilt above the event's peak, or the future back >= w her side of her entry."""
    t1 = e["t"] + 20 * 60000
    rb = next((x for x in r["events"] if e["t"] < x["t"] <= t1 and x["kind"] == "oi_withdrawn" and "rebuilt" in x["text"]), None)
    back = next((s for s in r["snaps"] if A.hm(r["day"], e["t"]) < s["t"] <= A.hm(r["day"], t1) and s["dE"] is not None and s["w"] and s["dE"] >= s["w"]), None)
    v = []
    if rb:
        v.append(f"W rebuilt {rb['ts'][:5]}")
    if back:
        v.append(f"back her side of entry {back['t']}")
    return ("noise: " + "; ".join(v)) if v else "real: W not rebuilt, never back to entry in 20 min"


for name, fn in (("(ii-F) literal 2-of-4 FOLD", lit), ("(iv-g) gave up under pressure, unless flow or VPIN WITH", ivg)):
    ch = []
    for r in A.R:
        c = A.candidates(r)
        e6 = c["rev6"]
        e = fn(r)
        ex = e if (e and (e6 is None or e["t"] < e6["t"])) else e6
        p6, t6 = B.exit_pct(r, e6)
        p, t = B.exit_pct(r, ex)
        if ex is not e6 and (e6 is None or e6["t"] - e["t"] >= 120000):
            ch.append((r["name"], p6, t6, p, t, A.after(r, e["t"]), "".join(k[0] for k in ("ZONE", "FLOW", "OI", "VPIN") if e["chips"].get(k[0]) == "AGAINST")))
    print(f"\n### {name}: {len(ch)} rows >= 2 min earlier than rev 6 (higher premium at exit on {sum(1 for x in ch if x[3] > x[1])}, lower on {sum(1 for x in ch if x[3] < x[1])})")
    for x in ch:
        print(f"   {x[0]:28} rev6 {x[1]:+d} {x[2]} -> {x[3]:+d} {x[4]} [against: {x[6]}] | after: {x[5]}")

print("\n### chips at each (iv) speak, and its falsifier verdict")
for r in A.R:
    e = B.cand_ivb(r)
    if not e:
        continue
    e6 = A.candidates(r)["rev6"]
    print(f"   {r['name']:28} {e['ts'][:8]} Z {e['chips']['Z']} F {e['chips']['F']} O {e['chips']['O']} V {e['chips']['V']} | {'same minute as rev 6' if e6 and e6['t'] - e['t'] < 120000 else verdict(r, e)}")
