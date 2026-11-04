"""The evening replay of the ladder: optflow/optladder.build for one day, embedded into optflow/ladder.html -> mockup.html
beside this file (standalone, REPLAY mode). Read-only on data/. Scratch, not repo code.

    python -I docs/optflow/brainstorm/mockup/export.py [YYYY-MM-DD] [NIFTY|SENSEX]     (default: the last full day, NIFTY)
"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
OPT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "optflow"))
sys.path.insert(0, OPT)
import optladder as ladder

DAY = next((a for a in sys.argv[1:] if a[:2] == "20"), time.strftime("%Y-%m-%d"))
IDX = next((a.upper() for a in sys.argv[1:] if a.upper() in ladder.IDX), "NIFTY")
d = ladder.build(DAY, IDX)
if not d["ok"]:
    sys.exit(d["why"])
tpl = open(os.path.join(OPT, "ladder.html"), encoding="utf-8").read()
out = os.path.join(HERE, "mockup.html")
open(out, "w", encoding="utf-8").write(tpl.replace("/*DATA*/", "const DATA = " + json.dumps(d, separators=(",", ":")) + ";"))
c = d["closes"]
ks = sorted(c, key=int)
print(f"{IDX} {DAY}: {len(d['series'])} minutes, {len(c)} closes from {c[ks[0]]['t'] if ks else '-'}, lot {d['lot']} "
      f"{'ok' if d['lot_check'] and d['lot_check']['ok'] else d['lot_check']}, open {d['open']['type']} -> {out}")
