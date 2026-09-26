# Her 09-24 trades through the window as it is NOW (rev 5 option B, built), beside rev 4 and her real exits.
# Descriptive only: counts and rows, never a rate (CLAUDE.md rule 4). Reads the frozen fixtures; writes nothing.
import json, os, sys
TM = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, TM); os.chdir(TM)
import hold, test_hold as th

P = {r["id"]: r for r in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rev5", "probeB_out.json"), encoding="utf-8"))}
out = []
for tr in th._trades():
    if tr.get("day") != "2026-09-24" or not tr.get("mine"):
        continue
    r, D = th._read(tr)
    if r is None:
        continue
    prem = D["prem"][f"{int(tr['k'])}{tr['side']}"]["c"]
    at = lambda t: prem[hold.mm(t) - hold.mm("09:15")] if t and 0 <= hold.mm(t) - hold.mm("09:15") < len(prem) else None
    rows = {x["t"]: x for x in r["rows"]}
    ex = rows.get(tr.get("exit_read")) or {}
    f = r["fold"] or {}
    old = (P.get(tr["id"]) or {}).get("rev4") or {}
    out.append({"trade": tr["id"], "in": tr["t0"][:5], "p0": tr["p0"], "out": tr["tx"][:5], "px": tr["px"],
                "her_pts": round(tr["px"] - tr["p0"], 2), "word_at_her_exit": (ex.get("verdict"), ex.get("tag")),
                "rev4_fold": (old.get("t"), old.get("rule")), "B_fold": (f.get("t"), f.get("rule")),
                "B_fold_prem_pts": round(at(f["t"]) - tr["p0"], 2) if f.get("t") and at(f["t"]) is not None else None,
                "entry": r["entry"]["verdict"]})
for o in out:
    print(json.dumps(o, ensure_ascii=False))
print("n", len(out))
