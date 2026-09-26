# The rev d disclosure run. Rules as fingerprinted (rules_revd_before_run.md, sha256 78b5f86c...d260).
# Counts and rows only, never a rate; no word is crossed with an outcome. Every output goes to an ABSOLUTE path in expr/revd/.
import json, os, statistics, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expr_d as E        # noqa: E402
C, B, A, X, hold = E.C, E.B, E.A, E.X, E.hold
th = X.th
mm, hm = hold.mm, hold.hm
OUT = os.path.join(HERE, "revd")
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
        series[(key, d)] = [E.expression_d(D, i, d, FRS[key]) for i in range(len(D["minutes"]))]
    print(key, round(time.time() - t0), "s", flush=True)


def label(e):
    return e["word"] or "could not check"


def cls(e):
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
            "strong_flips": strong, "side_flips": side, "mp": mp, "words": {w: b.count(w) for w in sorted(set(b))}, "tab": tab}


# ---- 1. words and stability, both cadences ----
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
    words, tab = {}, {}
    for s in ss:
        for src, dst in ((s["words"], words), (s["tab"], tab)):
            for w, n in src.items():
                dst[w] = dst.get(w, 0) + n
    tot[cad] = {"reads": sum(s["n"] for s in ss), "trans": sum(s["trans"] for s in ss),
                "changes": sum(s["changes"] for s in ss), "runs": len(allruns), "median_run_min": statistics.median(allruns),
                "runs_of_one": sum(s["runs_of_one"] for s in ss), "strong_flips": sum(s["strong_flips"] for s in ss),
                "side_flips": sum(s["side_flips"] for s in ss), "words": words, "tab": tab}
json.dump({"per_index_day": rows, "totals": tot}, open(os.path.join(OUT, "stability.json"), "w"), indent=1)
print(json.dumps(tot, indent=1), flush=True)

# ---- 2. refusals at the closes; what stands behind the refusal words (A-T5, A-T6) ----
refs, behind, N = {}, {}, 0
for (key, d), es in series.items():
    for i, e in enumerate(es):
        if not hold.is_close(hold.SESSION[i]) or not e.get("word"):
            continue
        N += 1
        for r in e["ref_b"] + e["ref_s"]:
            refs[r] = refs.get(r, 0) + 1
        if e["named_by"] == "refusal":
            k_ = "·".join(str(x) for x in cls(e))
            bb = behind.setdefault(k_, {"n": 0, "with_R6": 0, "only_R6": 0})
            bb["n"] += 1
            bb["with_R6"] += "R6" in e["ref_s"]
            bb["only_R6"] += e["ref_s"] == ["R6"]
json.dump({"N_closes": N, "refusals": refs, "behind_refusal_words": behind}, open(os.path.join(OUT, "refusals.json"), "w"), indent=1)
print("refusals", refs, behind, flush=True)

# rev c's words at the same closes, from rev c's own code, to say which words rev d moved
mv = {}
for (key, d), es in series.items():
    D = th._day(*key)
    for i, e in enumerate(es):
        if not hold.is_close(hold.SESSION[i]):
            continue
        ec = C.expression_c(D, i, d, FRS[key])
        if label(ec) != label(e):
            k_ = f"{B.base(ec['word'])} -> {B.base(e['word'])}"
            mv[k_] = mv.get(k_, 0) + 1
json.dump(mv, open(os.path.join(OUT, "moved_from_revc.json"), "w"), indent=1)
print("moved from rev c", sum(mv.values()), mv, flush=True)

# ---- 3. her entries: the rev d word; the ATM sold leg under rev 5 B (the window, unchanged); R-multiples; writer word ----
oldc = {r["id"]: r for r in json.load(open(os.path.join(HERE, "revc", "entries.json")))}
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
    rm, ww, other = {}, {"word": None}, {}
    if e.get("word"):
        rm = A.r_mults(D, ir, d, {**e, "line": es[ir].get("line") or e["line"]})
        s = e["sell"]
        ww = E.writer_word_d(D, ir, s["side"], s["k"], d, FRS[key])
        pk = D["prem"][f"{int(s['k'])}{s['side']}"]["c"]
        W = X.window_first_fold(D, {"side": s["side"], "role": "short", "t0": hm(mm(tr["read_from"]) + 1), "k": s["k"],
                                    "p0": pk[ir], "qty": 1})
        f5 = W.get("fold") or {}
        at = lambda t: pk[mm(t) - mm("09:15")] if t else None
        other = {"k": s["k"], "side": s["side"], "p0": pk[ir],
                 "rev5": (f5.get("t"), f5.get("rule"), round(pk[ir] - at(f5["t"]), 2) if f5.get("t") else None),
                 "at_1459": round(pk[ir] - pk[I1500 - 1], 2), "close": round(pk[ir] - pk[374], 2)}
    oc = oldc.get(tr["id"]) or {}
    ent.append({"id": tr["id"], "read": tr["read_from"], "close_read": hold.SESSION[ic], "d": "UP" if d > 0 else "DOWN",
                "word": label(e), "named_by": e.get("named_by"), "lead": e.get("lead"), "nb": e.get("nb"), "ns": e.get("ns"),
                "ref": e.get("ref_b", []) + e.get("ref_s", []), "since": since, "was": was,
                "word_c": oc.get("word"), "sell_c": (oc.get("sell") or {}).get("k"), "word_1m": label(es[ir]),
                "buy": e.get("buy"), "sell": e.get("sell"), "rmult": rm,
                "writer": {k: ww.get(k) for k in ("word", "word_no_cnc_clause", "facts", "cnc", "X", "c0", "line_beyond_strike", "stratum", "out30", "out1529")},
                "other": other})
json.dump(ent, open(os.path.join(OUT, "entries.json"), "w"), indent=1, default=str)
print("entries", len(ent), flush=True)

# ---- 4. the 09-24 seller case: her strikes as CE sales, under rev 5 B (the window, unchanged) ----
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
    sel.append({"trade": tr["id"], "k": k, "CE0": pk[i], "rev5": (f5.get("t"), f5.get("rule"), at(f5.get("t"))),
                "CE_1459": pk[I1500 - 1], "CE_1529": pk[374]})
json.dump(sel, open(os.path.join(OUT, "seller_0924.json"), "w"), indent=1, default=str)
for s in sel:
    print(s, flush=True)

# ---- 5. the grid: words at units; G scoreability; the writer population (ii); the ATM sold legs under rev 5 B ----
grid = {"units": 0, "words": {}, "tab": {}, "scored_G": 0, "notscored": {}, "tab_scored": {},
        "writer": {"n": 0, "words": {}, "words_no_cnc_clause": {}, "cnc_moved": 0, "stratum": {}, "stratum_beyond": {},
                   "beyond": 0, "resolved30": 0, "resolved1529": 0, "notscored": 0, "resolved30_stratum": 0},
        "legs": {"n": 0, "first_fold": {}, "exp_today": 0, "after_1500_start": 0}}
for (key, d), es in series.items():
    D = th._day(*key)
    for i in UNITS:
        e = es[i]
        grid["units"] += 1
        grid["words"][label(e)] = grid["words"].get(label(e), 0) + 1
        k_ = "·".join(str(x) for x in cls(e))
        grid["tab"][k_] = grid["tab"].get(k_, 0) + 1
        if not e.get("word"):
            continue
        rm = A.r_mults(D, i, d, e)
        if "G" in rm:
            grid["scored_G"] += 1
            grid["tab_scored"][k_] = grid["tab_scored"].get(k_, 0) + 1
        else:
            why = (rm.get("buy", {}).get("why") or rm.get("sell", {}).get("why"))
            grid["notscored"][why] = grid["notscored"].get(why, 0) + 1
        s = e["sell"]
        w = E.writer_word_d(D, i, s["side"], s["k"], d, FRS[key])
        g = grid["writer"]
        if w.get("word"):
            g["n"] += 1
            g["words"][w["word"]] = g["words"].get(w["word"], 0) + 1
            g["words_no_cnc_clause"][w["word_no_cnc_clause"]] = g["words_no_cnc_clause"].get(w["word_no_cnc_clause"], 0) + 1
            g["cnc_moved"] += w["word"] != w["word_no_cnc_clause"]
            g["beyond"] += w["line_beyond_strike"]
            if w["stratum"]:
                g["stratum"][w["word"]] = g["stratum"].get(w["word"], 0) + 1
                if w["line_beyond_strike"]:
                    g["stratum_beyond"][w["word"]] = g["stratum_beyond"].get(w["word"], 0) + 1
                g["resolved30_stratum"] += w["out30"] in ("target", "stop", "same minute")
            g["resolved30"] += w["out30"] in ("target", "stop", "same minute")
            g["resolved1529"] += w["out1529"] in ("target", "stop", "same minute")
            g["notscored"] += w["out30"] == "not scored"
        pk = D["prem"][f"{int(s['k'])}{s['side']}"]["c"]
        W = X.window_first_fold(D, {"side": s["side"], "role": "short", "t0": hm(mm(hold.SESSION[i]) + 1), "k": s["k"],
                                    "p0": pk[i], "qty": 1})
        if W.get("ok"):
            L = grid["legs"]
            L["n"] += 1
            f5 = W.get("fold") or {}
            r_ = str(f5.get("rule")) if f5.get("t") else "none"
            L["first_fold"][r_] = L["first_fold"].get(r_, 0) + 1
            L["exp_today"] += key in EXP_TODAY
            L["after_1500_start"] += i >= I1500
json.dump(grid, open(os.path.join(OUT, "grid.json"), "w"), indent=1, default=str)
print("grid", json.dumps(grid, indent=1), flush=True)
print("done", round(time.time() - t0), "s")
