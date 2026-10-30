"""export_mockup.py -- READ-ONLY: one day of NIFTY with the real recorded numbers -> ../mockup/data_28oct.json.

J2 (29 Oct): a thin wrapper. The rules live in tapemap/jarvis.py (`jarvis.build`, the one brain the server's /api/jarvis
also serves); this writes its frame as the mockup's JSON. Writes ONE file and nothing under tapemap/data/. No network,
no token: the futures minutes come from Dext 0.8.1 / the book, the spot from the chain record, Sides from the saved chain.

    python docs/kahani/review/scripts/export_mockup.py                                    # 28 Oct 09:15-13:40
    KAHANI_DAY=2026-10-29 KAHANI_END=15:30 KAHANI_OUT=.../mockup/data_today.json python ...   # another day, to the close
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import handshake as H  # noqa: E402
import jarvis  # noqa: E402

DAY, IDX = os.environ.get("KAHANI_DAY", "2026-10-28"), "NIFTY"           # KAHANI_* : a live day (29 Oct)
END = os.environ.get("KAHANI_END", "13:40")
OUT = os.environ.get("KAHANI_OUT") or os.path.join(HERE, "..", "mockup", "data_28oct.json")

data = jarvis.build(DAY, IDX, int(END[:2]) * 60 + int(END[3:5]) + 1)   # minutes <= END
if not data.get("ok"):
    sys.exit(f"{DAY}: {data.get('why')}")
data["made"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False)

mins, RUNS, PUSH = data["mins"], data["runs"], data["pushes"]
print(f"wrote {os.path.normpath(OUT)}: {len(mins)} minutes {mins[0]}-{mins[-1]}, chain missing {data['chain_missing']}, holes {data['holes']}")
print("runs:", *(f"\n  {r['kind']} {r['start']}(base {r['base']})-{r['last_ext']} K{r['khatam']} {r['lots']:+,} {r['dir']} {r['meaning']} dirs {r['dirs']}" for r in RUNS))
print("pushes:")
for p in PUSH:
    print(f"  {p['t']} {H.ARROW[p['dir']]} {p['lots']:+} {p['side']} {p['k']} ans {p['ans']} {p['chg']}L@{p['am']} m4 {p['ans4']} "
          f"held {p['held']}@{p['held_at']} who {p['who']} behind {p['behind']} fut {p['fut']} shown {p['shown']} "
          f"{'ARTIFACT' if p['artifact'] else ''}")
print("fights:")
for f in data["fights"]:
    print(f"  #{f['id']} {f['k']} {f['side']} born {f['born']} ending {f['ending']}: " + " | ".join(f"{a} {b} {c}" for a, b, c in f["stamps"]))
print("chapters (on change):")
last = None
for x in data["timeline"]:
    if x["chapter"] != last:
        print(f"  {x['t']} {x['chapter']}  wall {x['wall']} {x['wall_state']} {x['wall_chg']}L  fuel {x['fuel']}")
        last = x["chapter"]
print("verdict SELL (on change):")
last = None
for mm in mins:
    v = data["verdict"]["SELL"].get(mm)
    if v and (v["word"], v["ctx"], v["n"], v["N"]) != last:
        print(f"  {mm} ({v['ctx']}) {v['word']} {v['n']}/{v['N']} ?{v['q']} " + " · ".join(f"{k} {a} {b}" for k, (a, b) in v["pieces"].items()))
        last = (v["word"], v["ctx"], v["n"], v["N"])
print("zone rows:", data["zone"])
if data.get("reads"):
    print("reads:", {k: len(v) for k, v in data["reads"].items()})
print("health:", data.get("health"))
print("call:", data.get("call"))
