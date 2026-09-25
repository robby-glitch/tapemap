"""scratch/page.html + verdict.js + the frozen facts -> ../hold-window.html (self-contained)."""
import glob
import gzip
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "hold-window.html")
S0 = 9 * 60 + 15


def mm(t):
    return int(t[:2]) * 60 + int(t[3:5])


days = {}
for p in sorted(glob.glob(os.path.join(HERE, "facts_*.json.gz"))):
    d = json.load(gzip.open(p, "rt", encoding="utf-8"))
    d.pop("folds_all", None)
    for m in d.get("minutes") or []:
        for s in ("CE", "PE"):
            if m.get(s):
                m[s].pop("words", None)
    days[f"{d['idx']}_{d['day']}"] = d
days["NIFTY_2026-09-21"] = {"idx": "NIFTY", "day": "2026-09-21",
                            "why": "could not check — there is no chain record for NIFTY on 2026-09-21 (the poller did not "
                                   "record that day), and the 09-22 weekly is no longer listed on Upstox REST, so its OI "
                                   "cannot be rebuilt. No verdict without the OI grid."}

T = json.load(open(os.path.join(HERE, "trades.json")))
for e in T["examples"]:
    d = days[f"{e['idx']}_{e['day']}"]
    i = mm(e["read"]) - S0
    k = round(d["minutes"][i]["spot"] / d["step"]) * d["step"]
    leg = d["prem"].get(f"{int(k)}{e['side']}")
    e.update(k=int(k), p0=leg["c"][i] if leg else None, qty=d["lot"] * e["lots"], t0=e["read"], read_from=e["read"],
             read_to="15:29", exits=[], mine=False, note=e["id"].split("·", 1)[-1].strip())

page = open(os.path.join(HERE, "page.html"), encoding="utf-8").read()
js = open(os.path.join(HERE, "..", "verdict.js"), encoding="utf-8").read()
bt = open(os.path.join(HERE, "..", "better.js"), encoding="utf-8").read()
data = ("const DAYS = " + json.dumps(days, separators=(",", ":")) + ";\nconst TRADES = " +
        json.dumps(T, separators=(",", ":")) + ";")
page = page.replace("<script>/*VERDICT*/</script>", "<script>\n" + js + "\n</script>")
page = page.replace("<script>/*BETTER*/</script>", "<script>\n" + bt + "\n</script>")
page = page.replace("<script>/*DATA*/</script>", "<script>\n" + data.replace("</", "<\\/") + "\n</script>")
open(OUT, "w", encoding="utf-8").write(page)
print(OUT, round(len(page) / 1e6, 2), "MB")
