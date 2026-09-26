# The disclosure run (§D). Rules as fingerprinted in rules_before_run.md (sha256 eca1afe0...2b6c). Writes only here.
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import expr as X          # noqa: E402
hold, th = X.hold, X.th
mm, hm = hold.mm, hold.hm
OUT = X.OUT
t_start = time.time()

DAYS = [(i, d) for d in ("2026-09-22", "2026-09-23", "2026-09-24") for i in ("NIFTY", "SENSEX", "BANKNIFTY")]
FRS = {k: X.oihist_fr(*k) for k in DAYS}

# ---- 1. silence: every finished minute, both directions ----
count, per_min = {}, {}
for key in DAYS:
    D = th._day(*key)
    c = {}
    for i in range(len(D["minutes"])):
        for d in (1, -1):
            e = X.expression(D, i, d, FRS[key])
            w = e["word"] or "could not check"
            w = w.split(" ")[0] if w.startswith(("BUY", "SELL")) else w
            c[(d, w)] = c.get((d, w), 0) + 1
            per_min[(key, i, d)] = e
    count[key] = c
    print(key, {f"{'UP' if d > 0 else 'DN'} {w}": n for (d, w), n in sorted(c.items())}, round(time.time() - t_start), "s")
json.dump({f"{k[0]} {k[1]}": {f"{'UP' if d > 0 else 'DOWN'} {w}": n for (d, w), n in v.items()} for k, v in count.items()},
          open(os.path.join(OUT, "silence.json"), "w"), indent=1)

# ---- refusal and fact tallies (what drives the words) ----
tally = {}
for (key, i, d), e in per_min.items():
    if not e.get("word"):
        continue
    for r in e["ref_b"] + e["ref_s"]:
        tally[r[:2]] = tally.get(r[:2], 0) + 1
    for n, (s, _) in e["facts"].items():
        tally[f"{n}:{s}"] = tally.get(f"{n}:{s}", 0) + 1
json.dump(tally, open(os.path.join(OUT, "tally.json"), "w"), indent=1, sort_keys=True)

# ---- 2. her 29 entries ----
rows = []
for tr in th._trades():
    if not tr.get("mine"):
        continue
    D = th._day(tr["idx"], tr["day"])
    if not D.get("minutes"):
        rows.append({"id": tr["id"], "why": "could not check — the day was never frozen (no chain record)"}); continue
    i = mm(tr["read_from"]) - mm("09:15")
    d = hold.thesis(tr["side"], tr["role"])["d"]
    e = X.expression(D, i, d, FRS.get((tr["idx"], tr["day"])))
    sell = e["sell"]
    k_other = sell["k"] or e["buy"]["k"]          # the named sell strike; ATM for description if not shown
    oside = sell["side"]
    ww = X.writer_word(D, i, oside, k_other, d, FRS.get((tr["idx"], tr["day"])))
    p = lambda j: X.prem(D, k_other, oside, j)
    p0 = p(i)

    def at(n):
        j = min(i + n, len(D["minutes"]) - 1)
        v = p(j)
        return None if v is None or p0 is None else round(p0 - v, 2)
    win = [p(j) for j in range(i + 1, min(i + 31, len(D["minutes"])))]
    win = [v for v in win if v is not None]
    # the other leg read by the window: rev 5 B as built, then with §C's reach
    W = X.window_first_fold(D, {"side": oside, "role": "short", "t0": hm(mm(tr["read_from"]) + 1), "k": k_other,
                                "p0": p0, "qty": 1})
    f5 = W.get("fold") or {}
    rc = X.reach_read(D, W["rows"], k_other, d) if W.get("ok") else {}
    pf = (lambda t: X.prem(D, k_other, oside, mm(t) - mm("09:15")) if t else None)
    # her own leg at +30 (hindsight), for the row
    own = D["prem"].get(f"{int(tr['k'])}{tr['side']}")
    own30 = own["c"][min(i + 30, 374)] if own else None
    rows.append({
        "id": tr["id"], "read": tr["read_from"], "d": "UP" if d > 0 else "DOWN", "word": e["word"],
        "nb": e["nb"], "ns": e["ns"], "facts": {k: v[0] for k, v in e["facts"].items()},
        "fact_text": {k: v[1] for k, v in e["facts"].items()},
        "refused": e["ref_b"] + e["ref_s"], "buy": e["buy"], "sell": sell, "frsrc": e["frsrc"],
        "her": {"p0": tr["p0"], "exit": tr["exit_read"], "pts": round(tr["px"] - tr["p0"], 2), "p30": own30,
                "pts30": round(own30 - tr["p0"], 2) if own30 is not None else None},
        "other": {"k": k_other, "side": oside, "shown": sell["k"] is not None, "p0": p0,
                  "sold_pts_15": at(15), "sold_pts_30": at(30), "sold_pts_close": at(374 - i),
                  "worst_30": round(p0 - max(win), 2) if win and p0 is not None else None,
                  "rev5_fold": (f5.get("t"), f5.get("rule"), round(p0 - pf(f5["t"]), 2) if f5.get("t") and p0 else None),
                  "reach_fold": (rc.get("fold"), rc.get("rule"),
                                 round(p0 - pf(rc["fold"]), 2) if rc.get("fold") and p0 else None, rc.get("events"))},
        "writer_word": ww,
    })
json.dump(rows, open(os.path.join(OUT, "entries.json"), "w"), indent=1, default=str)

# ---- 3. the 09-24 seller case: her PE entries as CE sales at the same strike (the handoff's replay) ----
sel = []
for tr in th._trades():
    if tr.get("day") != "2026-09-24" or not tr.get("mine"):
        continue
    D = th._day(tr["idx"], tr["day"])
    k = tr["k"]
    i = mm(tr["read_from"]) - mm("09:15")
    c = D["prem"][f"{int(k)}CE"]["c"]
    w = {"side": "CE", "role": "short", "t0": hm(mm(tr["read_from"]) + 1), "k": k, "p0": c[i], "qty": 1}
    W = X.window_first_fold(D, w)
    f5 = W["fold"] or {}
    rc = X.reach_read(D, W["rows"], k, -1)
    # the straddle and reach at 14:38 for the record
    j = mm("14:38") - mm("09:15")
    S38, atm38 = X.straddle(D, j)
    px38 = D["minutes"][j]["ix"][0]
    pc = lambda t: c[mm(t) - mm("09:15")] if t else None
    sel.append({"trade": tr["id"].replace("PE", "CE sold"), "in": tr["read_from"], "CE0": c[i],
                "rev5": (f5.get("t"), f5.get("rule"), pc(f5.get("t")), round(c[i] - pc(f5["t"]), 2) if f5.get("t") else None),
                "reach": (rc.get("fold"), rc.get("rule"), pc(rc.get("fold")),
                          round(c[i] - pc(rc["fold"]), 2) if rc.get("fold") else None, rc.get("R"), rc.get("S"),
                          rc.get("events")),
                "at_1438": {"R": round(abs(k - px38), 1), "S": S38, "atm": atm38, "close": px38},
                "CE_1529": c[374], "to_close": round(c[i] - c[374], 2)})
json.dump(sel, open(os.path.join(OUT, "seller_0924.json"), "w"), indent=1, default=str)
for s in sel:
    print(s)
print("done", round(time.time() - t_start), "s")
