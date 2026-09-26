# The rev b disclosure run. Rules as fingerprinted (rules_revb_before_run.md, sha256 d7d9ab38...e6cd).
# Counts and rows only, never a rate. Every output goes to an ABSOLUTE path inside expr/revb/.
import json, os, statistics, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expr_b as B        # noqa: E402
A, X, hold = B.A, B.X, B.hold
th = X.th
mm, hm = hold.mm, hold.hm
OUT = os.path.join(HERE, "revb")
os.makedirs(OUT, exist_ok=True)
assert os.getcwd() != X.TM or True
t0 = time.time()
DAYS = [(i, d) for d in ("2026-09-22", "2026-09-23", "2026-09-24") for i in ("NIFTY", "SENSEX", "BANKNIFTY")]
FRS = {k: X.oihist_fr(*k) for k in DAYS}
EXP_TODAY = {("NIFTY", "2026-09-22"), ("SENSEX", "2026-09-24")}
UNITS = [i for i, t in enumerate(hold.SESSION) if hold.is_close(t) and t >= "09:44" and (mm(t) - mm("09:44")) % 30 == 0]
BUYS, SELLS = ("BUY", "LEANS BUY"), ("SELL", "LEANS SELL")

series = {}
for key in DAYS:
    D = th._day(*key)
    for d in (1, -1):
        series[(key, d)] = [B.expression_b(D, i, d, FRS[key]) for i in range(len(D["minutes"]))]
    print(key, round(time.time() - t0), "s", flush=True)


def label(e):
    return e["word"] or "could not check"


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
    return {"n": len(b), "trans": len(b) - 1, "changes": changes, "runs": runs, "runs_of_one": sum(1 for r in runs if r == 1),
            "strong_flips": strong, "side_flips": side, "mp": mp,
            "words": {w: b.count(w) for w in sorted(set(b))},
            "labels": {w: sum(1 for e in lst if label(e) == w) for w in sorted({label(e) for e in lst})}}


rows, agg = [], {"1m": [], "3m": []}
for (key, d), es in series.items():
    closes = [e for i, e in enumerate(es) if hold.is_close(hold.SESSION[i])]
    for cad, lst, mp in (("1m", es, 1), ("3m", closes, 3)):
        s = stats(lst, mp)
        agg[cad].append(s)
        rows.append({"day": f"{key[0]} {key[1][5:]}", "d": "UP" if d > 0 else "DOWN", "cad": cad,
                     "median_run_min": statistics.median(s["runs"]) * mp,
                     **{k: v for k, v in s.items() if k not in ("runs",)}})
tot = {}
for cad, ss in agg.items():
    allruns = [r * ss[0]["mp"] for s in ss for r in s["runs"]]
    words, labels = {}, {}
    for s in ss:
        for w, n in s["words"].items():
            words[w] = words.get(w, 0) + n
        for w, n in s["labels"].items():
            labels[w] = labels.get(w, 0) + n
    tot[cad] = {"reads": sum(s["n"] for s in ss), "trans": sum(s["trans"] for s in ss),
                "changes": sum(s["changes"] for s in ss), "runs": len(allruns), "median_run_min": statistics.median(allruns),
                "runs_of_one": sum(s["runs_of_one"] for s in ss), "strong_flips": sum(s["strong_flips"] for s in ss),
                "side_flips": sum(s["side_flips"] for s in ss), "words": words, "labels": labels}
json.dump({"per_index_day": rows, "totals": tot}, open(os.path.join(OUT, "stability.json"), "w"), indent=1)
json.dump(rows, open(os.path.join(OUT, "silence_detail.json"), "w"), indent=1)
print(json.dumps(tot, indent=1), flush=True)

# ---- her entries: the rev b word at the last close; the sold leg under rev 5 B, rev a's 3s and rev b's 3s ----
olda = {r["id"]: r for r in json.load(open(os.path.join(HERE, "reva", "entries.json")))}
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
        ra = A.reach_a(D, W["rows"], k, side, d, pk, True, key in EXP_TODAY)
        rb = B.reach_b(D, W["rows"], k, side, d, pk, True, key in EXP_TODAY)
        rbn = B.reach_b(D, W["rows"], k, side, d, pk, False, key in EXP_TODAY)
        at = lambda t: pk[mm(t) - mm("09:15")] if t else None
        f = lambda r: (r["fold"], r["rule"], round(pk[ir] - at(r["fold"]), 2) if r["fold"] else None)
        other = {"k": k, "side": side, "p0": pk[ir], "rev5": (f5.get("t"), f5.get("rule"), round(pk[ir] - at(f5["t"]), 2) if f5.get("t") else None),
                 "a": f(ra), "b_yes": f(rb), "b_no": f(rbn), "B_k": rb["B_k"], "B_at": rb["B_at"], "close": round(pk[ir] - pk[374], 2)}
    ent.append({"id": tr["id"], "read": tr["read_from"], "close_read": hold.SESSION[ic], "d": "UP" if d > 0 else "DOWN",
                "word": label(e), "lead": e.get("lead"), "nb": e.get("nb"), "ns": e.get("ns"),
                "ref": e.get("ref_b", []) + e.get("ref_s", []), "since": since, "was": was,
                "word_a": (olda.get(tr["id"]) or {}).get("word"), "word_1m": label(es[ir]), "sell": sell, "other": other})
json.dump(ent, open(os.path.join(OUT, "entries.json"), "w"), indent=1, default=str)

# ---- the 09-24 seller case under rev b ----
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
    ra = A.reach_a(D, W["rows"], k, "CE", -1, pk, True, True)
    yes = B.reach_b(D, W["rows"], k, "CE", -1, pk, True, True)
    no = B.reach_b(D, W["rows"], k, "CE", -1, pk, False, True)
    sel.append({"trade": tr["id"], "k": k, "CE0": pk[i], "rev5": (f5.get("t"), f5.get("rule"), at(f5.get("t"))),
                "rev_a": (ra["fold"], ra["rule"], at(ra["fold"])),
                "yes": (yes["fold"], yes["rule"], at(yes["fold"]), yes["events"], yes["P_b"], yes["P_max"]),
                "no": (no["fold"], no["rule"], at(no["fold"])), "B_k": yes["B_k"], "B_at": yes["B_at"], "CE_1529": pk[374]})
json.dump(sel, open(os.path.join(OUT, "seller_0924.json"), "w"), indent=1, default=str)
for s in sel:
    print(s, flush=True)

# ---- the grid: words at units, and the 165 sold legs under rev a's 3s and rev b's 3s ----
grid = {"words": {}, "legs": []}
for (key, d), es in series.items():
    D = th._day(*key)
    for i in UNITS:
        e = es[i]
        grid["words"][label(e)] = grid["words"].get(label(e), 0) + 1
        s = e.get("sell") or {}
        if not e.get("word") or not s.get("k"):
            continue
        pk = D["prem"][f"{int(s['k'])}{s['side']}"]["c"]
        W = X.window_first_fold(D, {"side": s["side"], "role": "short", "t0": hm(mm(hold.SESSION[i]) + 1), "k": s["k"], "p0": pk[i], "qty": 1})
        if not W.get("ok"):
            continue
        f5 = W.get("fold") or {}
        ra = A.reach_a(D, W["rows"], s["k"], s["side"], d, pk, True, key in EXP_TODAY)
        rb = B.reach_b(D, W["rows"], s["k"], s["side"], d, pk, True, key in EXP_TODAY)
        at = lambda t: pk[mm(t) - mm("09:15")] if t else pk[374]
        grid["legs"].append({"day": f"{key[0]} {key[1][5:]}", "d": "UP" if d > 0 else "DOWN", "unit": hold.SESSION[i],
                             "word": e["word"], "k": s["k"], "side": s["side"], "p0": pk[i],
                             "rev5": (f5.get("t"), f5.get("rule"), at(f5.get("t"))),
                             "a": (ra["fold"], ra["rule"], at(ra["fold"])), "b": (rb["fold"], rb["rule"], at(rb["fold"])),
                             "B_k": rb["B_k"], "b_held": rb["events"][:1], "b_Pb": rb.get("P_b"), "b_Pmax": rb.get("P_max"),
                             "P_1529": pk[374]})
json.dump(grid, open(os.path.join(OUT, "grid.json"), "w"), indent=1, default=str)
print("grid words", grid["words"], len(grid["legs"]), flush=True)
print("done", round(time.time() - t0), "s")
