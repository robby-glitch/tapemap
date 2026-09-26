# Her 09-24 entries read as a SELLER: the same bearish view, but SHORT the call at the same strike instead of long the put.
# The window as built now (rev 5 option B; the writer clauses of rev 4 §4). Descriptive, hindsight, frozen facts; writes nothing.
import json, os, sys
TM = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, TM); os.chdir(TM)
import hold, test_hold as th

for tr in th._trades():
    if tr.get("day") != "2026-09-24" or not tr.get("mine"):
        continue
    D = th._day(tr["idx"], tr["day"])
    key = f"{int(tr['k'])}CE"
    if key not in D["prem"]:
        print(tr["id"], "no CE record"); continue
    c = D["prem"][key]["c"]
    i0 = hold.mm(tr["read_from"]) - hold.mm("09:15")
    w = {**tr, "side": "CE", "role": "short", "p0": c[i0]}
    r = hold.read(w, D["minutes"], D["pivots"], prem=D["prem"][key], idx=tr["idx"])
    if not r.get("ok"):
        print(tr["id"], r.get("why")); continue
    rows = {x["t"]: x for x in r["rows"]}
    at = lambda t: c[hold.mm(t) - hold.mm("09:15")] if t else None
    f = r["fold"] or {}
    her_exit = rows.get(tr.get("exit_read")) or {}
    last = r["rows"][-1]
    print(json.dumps({"trade": tr["id"].replace("PE", "CE sold"), "in": tr["read_from"], "CE_at_entry": w["p0"],
                      "entry_word": r["entry"]["verdict"],
                      "word_at_her_put_exit": (tr.get("exit_read"), her_exit.get("verdict"), her_exit.get("tag")),
                      "fold": (f.get("t"), f.get("rule")), "CE_at_fold": at(f.get("t")),
                      "seller_pts_at_fold": round(w["p0"] - at(f["t"]), 2) if f.get("t") else None,
                      "CE_last": c[hold.mm(last["t"]) - hold.mm("09:15")], "last_t": last["t"],
                      "seller_pts_to_last": round(w["p0"] - c[hold.mm(last["t"]) - hold.mm("09:15")], 2)}, ensure_ascii=False))
