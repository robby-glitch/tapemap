"""Where tops and bottoms formed against VWAP and its sigma bands (her ask, 31 Oct). Counts only, never a rate.
Run after atlas_build.py + atlas.py (frames and atlas_legs.json in %TEMP%/jarvis_atlas)."""
import collections
import glob
import json
import os
import tempfile

A = os.path.join(tempfile.gettempdir(), "jarvis_atlas")
TREND = {"2026-09-28", "2026-10-06", "2026-10-08", "2026-10-12", "2026-10-13", "2026-10-21", "2026-10-23", "2026-10-26",
         "2026-10-29"}                                  # first TREND call before 10:00 (the atlas, §1)
ORDER = ["wrong side of VWAP", "VWAP-1", "1-2", "2-3", "beyond 3"]


def band(z):
    return "?" if z is None else ORDER[0] if z < 0 else ORDER[1] if z < 1 else ORDER[2] if z < 2 else ORDER[3] if z < 3 else ORDER[4]


def show(title, rs):
    c = collections.Counter(band(r["z"]) for r in rs)
    print(f"{title} (n {len(rs)}): " + " · ".join(f"{b} {c.get(b, 0)}" for b in ORDER) + (f" · ? {c['?']}" if c.get("?") else ""))


frames = {os.path.basename(f)[6:16]: json.load(open(f, encoding="utf-8")) for f in glob.glob(os.path.join(A, "frames", "NIFTY_*.json"))}
ext, minutes = [], []
for day, d in sorted(frames.items()):
    m, fhi, flo, vw, sd = d["mins"], d["fhi"], d["flo"], d["vwap"], d["sd"]
    if len(m) < 300:                                    # partial days: no day high / low
        continue
    hi = max(range(len(m)), key=lambda i: fhi[i])
    lo = min(range(len(m)), key=lambda i: flo[i])
    ext.append({"day": day, "kind": "top", "t": m[hi], "z": (fhi[hi] - vw[hi]) / sd[hi] if sd[hi] else None})
    ext.append({"day": day, "kind": "bottom", "t": m[lo], "z": (vw[lo] - flo[lo]) / sd[lo] if sd[lo] else None})
    z = [(c - v) / s if s else None for c, v, s in zip(d["fut"], vw, sd)]
    late = [x for x, t in zip(z, m) if t >= "09:45" and x is not None]
    minutes.append((day, sum(x >= 2 for x in late), sum(x >= 3 for x in late), sum(x <= -2 for x in late), sum(x <= -3 for x in late)))

swings = []
by = collections.defaultdict(list)
for L in json.load(open(os.path.join(A, "atlas_legs.json"), encoding="utf-8")):
    by[L["day"]].append(L)
for day, Ls in by.items():
    d = frames[day]
    Ls.sort(key=lambda L: L["birth"])
    for a, b in zip(Ls, Ls[1:]):                         # a leg (>= 40 pts) followed by one the other way: a swing turn
        if b["dir"] == a["dir"] or a["extreme_t"] not in d["mins"]:
            continue
        i = d["mins"].index(a["extreme_t"])
        z = None if not d["sd"][i] else (a["extreme"] - d["vwap"][i]) / d["sd"][i] * a["dir"]
        swings.append({"day": day, "kind": "top" if a["dir"] > 0 else "bottom", "t": a["extreme_t"], "z": z, "back": b["pts"]})

print("== the day's high and low (full days) ==")
show("all", ext)
show("  rotation days", [r for r in ext if r["day"] not in TREND])
show("  trend days", [r for r in ext if r["day"] in TREND])
print("== every swing turn (>= 40 pts into it and >= 40 back) ==")
show("all", swings)
for lbl, f in (("before 09:45", lambda r: r["t"] < "09:45"), ("09:45-12:00", lambda r: "09:45" <= r["t"] < "12:00"),
               ("12:00+", lambda r: r["t"] >= "12:00"), ("after 09:45, >= 80 back", lambda r: r["t"] >= "09:45" and r["back"] >= 80)):
    show("  " + lbl, [r for r in swings if f(r)])
print("== minutes beyond the bands after 09:45 (full days) ==")
for day, u2, u3, d2, d3 in minutes:
    print(f"  {day} {'TREND' if day in TREND else 'rot  '} beyond u2 {u2:>3} (u3 {u3:>2}) · beyond d2 {d2:>3} (d3 {d3:>2})")
print(f"  total beyond u3 or d3: {sum(x[2] + x[4] for x in minutes)} min over {len(minutes)} days")
