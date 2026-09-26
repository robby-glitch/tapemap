# The rev c disclosure run. Rules as fingerprinted (rules_revc_before_run.md, sha256 64ad9d7f...2010).
# Counts and rows only, never a rate. Every output goes to an ABSOLUTE path inside expr/revc/.
import json, os, statistics, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expr_c as C        # noqa: E402
B, A, X, hold = C.B, C.A, C.X, C.hold
th = X.th
mm, hm = hold.mm, hold.hm
OUT = os.path.join(HERE, "revc")
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
DAYS = [(i, d) for d in ("2026-09-22", "2026-09-23", "2026-09-24") for i in ("NIFTY", "SENSEX", "BANKNIFTY")]
FRS = {k: X.oihist_fr(*k) for k in DAYS}
EXP_TODAY = {("NIFTY", "2026-09-22"), ("SENSEX", "2026-09-24")}
UNITS = [i for i, t in enumerate(hold.SESSION) if hold.is_close(t) and t >= "09:44" and (mm(t) - mm("09:44")) % 30 == 0]
BUYS, SELLS = ("BUY", "LEANS BUY"), ("SELL", "LEANS SELL")
I1500 = mm("15:00") - mm("09:15")

series = {}
for key in DAYS:
    D = th._day(*key)
    for d in (1, -1):
        series[(key, d)] = [C.expression_c(D, i, d, FRS[key]) for i in range(len(D["minutes"]))]
    print(key, round(time.time() - t0), "s", flush=True)


def label(e):
    return e["word"] or "could not check"


def cls(e):
    """(base word, named_by, sub) for the tables."""
    b = B.base(e["word"])
    w = e["word"] or ""
    sub = "both" if "both" in w else "led" if "led" in w else ("tie" if e.get("lead") == 0 and e.get("named_by") == "refusal" else "")
    return b, e.get("named_by"), sub


def stats(lst, mp):
    b = [B.base(e["word"]) for e in lst]
    changes = sum(1 for a, c in zip(b, b[1:]) if a != c)
    runs, cur = [], 1
    for a, c in zip(b, b[1:]):
        if a == c:
            cur += 1
        else:
            runs.append(cur); cur = 1
    runs.append(cur)
    strong = sum(1 for a, c in zip(b, b[1:]) if {a, c} == {"BUY", "SELL"})
    side = sum(1 for a, c in zip(b, b[1:]) if (a in BUYS and c in SELLS) or (a in SELLS and c in BUYS))
    tab = {}
    for e in lst:
        k = "·".join(str(x) for x in cls(e))
        tab[k] = tab.get(k, 0) + 1
    return {"n": len(b), "trans": len(b) - 1, "changes": changes, "runs": runs, "runs_of_one": sum(1 for r in runs if r == 1),
            "strong_flips": strong, "side_flips": side, "mp": mp, "words": {w: b.count(w) for w in sorted(set(b))}, "tab": tab,
            "labels": {w: sum(1 for e in lst if label(e) == w) for w in sorted({label(e) for e in lst})}}


rows, agg = [], {"1m": [], "3m": []}
for (key, d), es in series.items():
    closes = [e for i, e in enumerate(es) if hold.is_close(hold.SESSION[i])]
    for cad, lst, mp in (("1m", es, 1), ("3m", closes, 3)):
        s = stats(lst, mp)
        agg[cad].append(s)
        rows.append({"day": f"{key[0]} {key[1][5:]}", "d": "UP" if d > 0 else "DOWN", "cad": cad,
                     "median_run_min": statistics.median(s["runs"]) * mp, **{k: v for k, v in s.items() if k != "runs"}})
tot = {}
for cad, ss in agg.items():
    allruns = [r * ss[0]["mp"] for s in ss for r in s["runs"]]
    words, labels, tab = {}, {}, {}
    for s in ss:
        for src, dst in ((s["words"], words), (s["labels"], labels), (s["tab"], tab)):
            for w, n in src.items():
                dst[w] = dst.get(w, 0) + n
    tot[cad] = {"reads": sum(s["n"] for s in ss), "trans": sum(s["trans"] for s in ss),
                "changes": sum(s["changes"] for s in ss), "runs": len(allruns), "median_run_min": statistics.median(allruns),
                "runs_of_one": sum(s["runs_of_one"] for s in ss), "strong_flips": sum(s["strong_flips"] for s in ss),
                "side_flips": sum(s["side_flips"] for s in ss), "words": words, "labels": labels, "tab": tab}
json.dump({"per_index_day": rows, "totals": tot}, open(os.path.join(OUT, "stability.json"), "w"), indent=1)
json.dump(rows, open(os.path.join(OUT, "silence_detail.json"), "w"), indent=1)
print(json.dumps({c: {k: v for k, v in t.items() if k != "labels"} for c, t in tot.items()}, indent=1), flush=True)

# ---- her entries: the rev c word at the last close; the sold leg under rev 5 B, rev b (YES) and rev c (NO) ----
oldb = {r["id"]: r for r in json.load(open(os.path.join(HERE, "revb", "entries.json")))}
ent = []
for tr in th._trades():
    if not tr.get("mine"):
        continue
    D = th._day(tr["idx"], tr["day"])
    if not D.get("minutes"):
        ent.append({"id": tr["id"], "why": "never frozen"}); continue
    key = (tr["idx"], tr["day"])
    d = hold.thesis(tr["side"], tr["role"])["d"]
    ir = mm(tr["read_from"]) - mm("09:15")
    es = series[(key, d)]
    ic = max(i for i in range(ir + 1) if hold.is_close(hold.SESSION[i]))
    e = es[ic]
    cl = [i for i in range(ic + 1) if hold.is_close(hold.SESSION[i])]
    since, was = hold.SESSION[ic], None
    for a, b2 in zip(reversed(cl[:-1]), reversed(cl[1:])):
        if label(es[a]) == label(e):
            since = hold.SESSION[a]
        else:
            was = label(es[a]); break
    sell = e["sell"]
    other = {}
    if sell.get("k"):
        k, side = sell["k"], sell["side"]
        pk = D["prem"][f"{int(k)}{side}"]["c"]
        W = X.window_first_fold(D, {"side": side, "role": "short", "t0": hm(mm(tr["read_from"]) + 1), "k": k, "p0": pk[ir], "qty": 1})
        f5 = W.get("fold") or {}
        ry = B.reach_b(D, W["rows"], k, side, d, pk, True, key in EXP_TODAY)
        rc = C.reach_c(D, W["rows"], k, side, d, pk, key in EXP_TODAY)
        at = lambda t: pk[mm(t) - mm("09:15")] if t else None
        f = lambda r: (r["fold"], r["rule"], round(pk[ir] - at(r["fold"]), 2) if r["fold"] else None)
        other = {"k": k, "side": side, "p0": pk[ir], "rev5": (f5.get("t"), f5.get("rule"), round(pk[ir] - at(f5["t"]), 2) if f5.get("t") else None),
                 "b_yes": f(ry), "c": f(rc), "B_k": rc["B_k"], "B_at": rc["B_at"], "held_c": rc["held"], "close": round(pk[ir] - pk[374], 2),
                 "at_1459": round(pk[ir] - pk[I1500 - 1], 2)}
    ent.append({"id": tr["id"], "read": tr["read_from"], "close_read": hold.SESSION[ic], "d": "UP" if d > 0 else "DOWN",
                "word": label(e), "named_by": e.get("named_by"), "lead": e.get("lead"), "nb": e.get("nb"), "ns": e.get("ns"),
                "ref": e.get("ref_b", []) + e.get("ref_s", []), "since": since, "was": was,
                "word_b": (oldb.get(tr["id"]) or {}).get("word"), "word_1m": label(es[ir]), "sell": sell, "other": other})
json.dump(ent, open(os.path.join(OUT, "entries.json"), "w"), indent=1, default=str)

# ---- the 09-24 seller case: rev c (NO, registered) and YES (not registered), plus the 14:59 premium ----
sel = []
for tr in th._trades():
    if tr.get("day") != "2026-09-24" or not tr.get("mine"):
        continue
    D = th._day(tr["idx"], tr["day"])
    k, i = tr["k"], mm(tr["read_from"]) - mm("09:15")
    pk = D["prem"][f"{int(k)}CE"]["c"]
    W = X.window_first_fold(D, {"side": "CE", "role": "short", "t0": hm(mm(tr["read_from"]) + 1), "k": k, "p0": pk[i], "qty": 1})
    f5 = W["fold"] or {}
    at = lambda t: pk[mm(t) - mm("09:15")] if t else None
    yes = B.reach_b(D, W["rows"], k, "CE", -1, pk, True, True)
    no = C.reach_c(D, W["rows"], k, "CE", -1, pk, True)
    sel.append({"trade": tr["id"], "k": k, "CE0": pk[i], "rev5": (f5.get("t"), f5.get("rule"), at(f5.get("t"))),
                "no": (no["fold"], no["rule"], at(no["fold"]), no["held"]), "yes": (yes["fold"], yes["rule"], at(yes["fold"]), yes["P_max"]),
                "B_k": no["B_k"], "CE_1459": pk[I1500 - 1], "CE_1529": pk[374]})
json.dump(sel, open(os.path.join(OUT, "seller_0924.json"), "w"), indent=1, default=str)
for s in sel:
    print(s, flush=True)

# ---- the grid: words at units; the 165 sold legs under rev b (YES) and rev c (NO) ----
grid = {"words": {}, "tab": {}, "legs": []}
for (key, d), es in series.items():
    D = th._day(*key)
    for i in UNITS:
        e = es[i]
        grid["words"][label(e)] = grid["words"].get(label(e), 0) + 1
        k_ = "·".join(str(x) for x in cls(e))
        grid["tab"][k_] = grid["tab"].get(k_, 0) + 1
        s = e.get("sell") or {}
        if not e.get("word") or not s.get("k"):
            continue
        pk = D["prem"][f"{int(s['k'])}{s['side']}"]["c"]
        W = X.window_first_fold(D, {"side": s["side"], "role": "short", "t0": hm(mm(hold.SESSION[i]) + 1), "k": s["k"], "p0": pk[i], "qty": 1})
        if not W.get("ok"):
            continue
        f5 = W.get("fold") or {}
        rb = B.reach_b(D, W["rows"], s["k"], s["side"], d, pk, True, key in EXP_TODAY)
        rc = C.reach_c(D, W["rows"], s["k"], s["side"], d, pk, key in EXP_TODAY)
        at = lambda t: pk[mm(t) - mm("09:15")] if t else pk[374]
        grid["legs"].append({"day": f"{key[0]} {key[1][5:]}", "exp_today": key in EXP_TODAY, "d": "UP" if d > 0 else "DOWN",
                             "unit": hold.SESSION[i], "word": e["word"], "k": s["k"], "side": s["side"], "p0": pk[i],
                             "rev5": (f5.get("t"), f5.get("rule"), at(f5.get("t"))),
                             "b": (rb["fold"], rb["rule"], at(rb["fold"])), "c": (rc["fold"], rc["rule"], at(rc["fold"])),
                             "b_held": rb["events"][:1], "c_held": rc["events"][:1], "B_k": rc["B_k"], "P_1459": pk[I1500 - 1], "P_1529": pk[374]})
json.dump(grid, open(os.path.join(OUT, "grid.json"), "w"), indent=1, default=str)
print("grid tab", grid["tab"], len(grid["legs"]), flush=True)
print("done", round(time.time() - t0), "s")
