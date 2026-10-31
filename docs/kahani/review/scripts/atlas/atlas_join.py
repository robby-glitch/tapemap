"""At the TREND call: the winners (>= +40 to the lean flip) vs the losers (< 0), every read; counts only."""
import tempfile
import json, os, collections, glob
HERE = os.path.join(tempfile.gettempdir(), "jarvis_atlas")
legs = {(x["day"], x["dir"], x["origin_t"]): x for x in json.load(open(os.path.join(HERE, "atlas_legs.json"), encoding="utf-8"))}
T = json.load(open(os.path.join(HERE, "atlas_trades.json"), encoding="utf-8"))
fr = {}
for t in T:
    L = legs.get((t["day"], t["dir"], t["origin_t"]))
    t["s"] = L and L.get("trend_snap")
    if t["day"] not in fr:
        d = json.load(open(os.path.join(HERE, "frames", f"NIFTY_{t['day']}.json"), encoding="utf-8"))
        fr[t["day"]] = d
    d = fr[t["day"]]; i = d["mins"].index(t["call"]["in_t"])
    fl = d["legs"]["day"]["flips"]; t["flips"] = fl[i] if i < len(fl) else None
    t["leg"] = L
first = {}
for t in T:
    first.setdefault(t["day"], t)
W = [t for t in T if t["call"]["pts"] >= 40]; X = [t for t in T if t["call"]["pts"] < 0]
def row(lbl, f):
    print(lbl.ljust(34) + f"{sum(1 for t in W if f(t))} of {len(W)}".ljust(12) + f"{sum(1 for t in X if f(t))} of {len(X)}")
print("at the TREND call".ljust(34) + "WIN>=40".ljust(12) + "LOSE<0")
row("first call of the day", lambda t: first[t["day"]] is t)
row("called before 10:00", lambda t: t["call"]["in_t"] < "10:00")
row("called 10:00-12:59", lambda t: "10:00" <= t["call"]["in_t"] < "13:00")
row("called 13:00+", lambda t: t["call"]["in_t"] >= "13:00")
row("lean flips so far today = 0", lambda t: t["flips"] == 0)
row("lean flips so far today >= 2", lambda t: (t["flips"] or 0) >= 2)
row("leg >= 120 pts at the call", lambda t: t["leg_pts_at_call"] >= 120)
row("leg had a TOOT (a wall broke)", lambda t: t["leg"] and t["leg"]["toot"])
row("leg fuelled (fut OI run)", lambda t: t["leg"] and t["leg"]["fuelled"])
for b in ("w_with", "w_against", "sides_with", "fuel_with", "fuel_against", "fast_with", "all3_with"):
    row(b, lambda t, b=b: t["s"] and t["s"].get(b))
row("push against in 15 min", lambda t: t["s"] and t["s"]["push_against"] >= 1)
row("TOOT/PHANS with in 15 min", lambda t: t["s"] and any(a in ("TOOT", "PHANS") for a in t["s"]["ans_with"]))
row("z >= 1.5 (stretched off VWAP)", lambda t: t["s"] and (t["s"]["z"] or 0) >= 1.5)
row("z < 1", lambda t: t["s"] and (t["s"]["z"] or 0) < 1)
row("day_pos at the extreme (>=.9 / <=.1)", lambda t: t["s"] and t["s"]["day_pos"] is not None and (t["s"]["day_pos"] >= .9 if t["dir"] > 0 else t["s"]["day_pos"] <= .1))
row("wall ahead UNWINDING", lambda t: t["s"] and t["s"]["ahead_state"] == "UNWINDING")
row("wall ahead BUILDING", lambda t: t["s"] and t["s"]["ahead_state"] == "BUILDING")
row("wall behind BUILDING", lambda t: t["s"] and t["s"]["behind_state"] == "BUILDING")
row("wall behind UNWINDING", lambda t: t["s"] and t["s"]["behind_state"] == "UNWINDING")
row("Sides REAL/BACKED", lambda t: t["s"] and t["s"]["sides"] in ("REAL", "BACKED"))
row("Sides SQUEEZE", lambda t: t["s"] and t["s"]["sides"] == "SQUEEZE")
row("Sides CAPPED", lambda t: t["s"] and t["s"]["sides"] == "CAPPED")
print("\nfirst call of each day:")
for d_, t in first.items():
    s = t["s"] or {}
    print(f"  {d_} {'▲' if t['dir'] > 0 else '▼'} {t['call']['in_t']} leg {t['leg_pts_at_call']} → {t['call']['pts']:+.0f} (mfe {t['call']['mfe']:+.0f}) out {t['call']['out_t']} · writers {s.get('writers')} · ahead {s.get('ahead')} · behind {s.get('behind')} · Sides {s.get('sides')} · z {s.get('z')} · fut OI {s.get('fut_oi')}")
print("\ncalls at or after 11:00:")
for t in sorted([t for t in T if t["call"]["in_t"] >= "11:00"], key=lambda t: -t["call"]["pts"]):
    s = t["s"] or {}
    print(f"  {t['day']} {'▲' if t['dir'] > 0 else '▼'} {t['call']['in_t']} {t['call']['pts']:+5.0f} (mfe {t['call']['mfe']:+.0f}) flips {t['flips']} leg {t['leg_pts_at_call']} z {s.get('z')} pos {s.get('day_pos')} wr {s.get('writers')} ahead {s.get('ahead_state')} behind {s.get('behind_state')} Sides {s.get('sides')} vs-push {s.get('push_against')} ans {s.get('ans_with')} fast {s.get('fast_with')}")
