# The rev a disclosure run (§D). Rules as fingerprinted (rules_reva_before_run.md, sha256 79d7daa6...162d).
# Counts and rows only, never a rate. Writes only into this scratch folder.
import json, os, statistics, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import expr_a as A        # noqa: E402
X, hold, th = A.X, A.hold, A.th
mm, hm = hold.mm, hold.hm
OUT = os.path.join(X.OUT, "reva")
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
DAYS = [(i, d) for d in ("2026-09-22", "2026-09-23", "2026-09-24") for i in ("NIFTY", "SENSEX", "BANKNIFTY")]
FRS = {k: X.oihist_fr(*k) for k in DAYS}
EXP_TODAY = {("NIFTY", "2026-09-22"), ("SENSEX", "2026-09-24")}
UNITS = [i for i, t in enumerate(hold.SESSION) if hold.is_close(t) and t >= "09:44" and (mm(t) - mm("09:44")) % 30 == 0]

series = {}
for key in DAYS:
    D = th._day(*key)
    for d in (1, -1):
        series[(key, d)] = [A.expression_a(D, i, d, FRS[key]) for i in range(len(D["minutes"]))]
    print(key, round(time.time() - t0), "s", flush=True)


def label(e):
    return e["word"] or "could not check"


def stats(words, es, minutes_per):
    b = [A.base(w) for w in words]
    changes = sum(1 for a, c in zip(b, b[1:]) if a != c)
    runs, cur = [], 1
    for a, c in zip(b, b[1:]):
        if a == c:
            cur += 1
        else:
            runs.append(cur); cur = 1
    runs.append(cur)
    direct = sum(1 for a, c in zip(b, b[1:]) if {a, c} == {"BUY", "SELL"})
    bs = [e for e in es if e.get("word") and A.base(e["word"]) in ("BUY", "SELL")]
    cnt = [e for e in bs if e["named_by"] == "count"]
    return {"n": len(b), "changes": changes, "runs": len(runs), "median_run_min": statistics.median(runs) * minutes_per,
            "runs_of_one": sum(1 for r in runs if r == 1), "direct_buy_sell": direct,
            "bs": len(bs), "bs_margin1": sum(1 for e in bs if abs(e["nb"] - e["ns"]) == 1),
            "bs_count": len(cnt), "bs_count_margin1": sum(1 for e in cnt if abs(e["nb"] - e["ns"]) == 1)}


def total(ss):
    keys = ("n", "changes", "runs", "runs_of_one", "direct_buy_sell", "bs", "bs_margin1", "bs_count", "bs_count_margin1")
    return {k: sum(s[k] for s in ss) for k in keys}


# ---- 1. words and stability, both cadences ----
words = {"1m": {}, "3m": {}}
st = {"1m": [], "3m": []}
rows = []
for (key, d), es in series.items():
    closes = [e for i, e in enumerate(es) if hold.is_close(hold.SESSION[i])]
    for cad, lst, mp in (("1m", es, 1), ("3m", closes, 3)):
        s = stats([label(e) for e in lst], lst, mp)
        st[cad].append(s)
        for e in lst:
            words[cad][label(e)] = words[cad].get(label(e), 0) + 1
        rows.append({"day": f"{key[0]} {key[1][5:]}", "d": "UP" if d > 0 else "DOWN", "cad": cad, **s,
                     "words": {w: sum(1 for e in lst if label(e) == w) for w in sorted({label(e) for e in lst})}})
json.dump({"per_index_day": rows, "totals": {c: total(st[c]) for c in st}, "words": words,
           "median_run_all": {c: None for c in st}}, open(os.path.join(OUT, "stability.json"), "w"), indent=1)
json.dump(rows, open(os.path.join(OUT, "silence_detail.json"), "w"), indent=1)
print("stability", {c: total(st[c]) for c in st}, flush=True)
print("words", words, flush=True)

# ---- 2. facts, refusals, co-occurrence (3-min closes), Q3 placement ----
fx, refs, co, place, rs = {}, {}, {}, {}, []
N = 0
for (key, d), es in series.items():
    for i, e in enumerate(es):
        if not hold.is_close(hold.SESSION[i]) or not e.get("word"):
            continue
        N += 1
        f = {n: v[0] for n, v in e["facts"].items()}
        for n, v in f.items():
            fx[f"{n}:{v}"] = fx.get(f"{n}:{v}", 0) + 1
        for r in e["ref_b"] + e["ref_s"]:
            refs[r] = refs.get(r, 0) + 1
        pairs = {"SHIELD S · ROOM S": f["shield"] == "sell" and f["room"] == "sell",
                 "SPEED B · REGIME B": f["speed"] == "buy" and f["regime"] == "buy",
                 "REGIME B · PREMIUM B": f["regime"] == "buy" and f["premium"] == "buy",
                 "REGIME S · PREMIUM S": f["regime"] == "sell" and f["premium"] == "sell",
                 "SPEED B · ROOM B": f["speed"] == "buy" and f["room"] == "buy"}
        for p, v in pairs.items():
            co[p] = co.get(p, 0) + v
        if A.base(e["word"]) == "SELL":
            pl = e["sell"]["placement"]
            place[pl] = place.get(pl, 0) + 1
            if e["sell"]["r_over_S"] is not None:
                rs.append(e["sell"]["r_over_S"])
exp = {"SHIELD S · ROOM S": ("shield:sell", "room:sell"), "SPEED B · REGIME B": ("speed:buy", "regime:buy"),
       "REGIME B · PREMIUM B": ("regime:buy", "premium:buy"), "REGIME S · PREMIUM S": ("regime:sell", "premium:sell"),
       "SPEED B · ROOM B": ("speed:buy", "room:buy")}
coexp = {p: round(fx.get(a, 0) * fx.get(b, 0) / N) for p, (a, b) in exp.items()}
q = statistics.quantiles(rs, n=4) if len(rs) > 3 else None
json.dump({"N_closes": N, "facts": fx, "refusals": refs, "co": co, "co_if_independent": coexp,
           "sell_placement_at_SELL_words": place, "sell_wall_r_over_S_quartiles": q},
          open(os.path.join(OUT, "facts_3m.json"), "w"), indent=1)
print("facts", fx, refs, co, coexp, place, q, flush=True)

# ---- 3. her 29 entries ----
old = {r["id"]: r for r in json.load(open(os.path.join(X.OUT, "entries.json")))}
ent = []
for tr in th._trades():
    if not tr.get("mine"):
        continue
    D = th._day(tr["idx"], tr["day"])
    if not D.get("minutes"):
        ent.append({"id": tr["id"], "why": "could not check — never frozen"}); continue
    key = (tr["idx"], tr["day"])
    d = hold.thesis(tr["side"], tr["role"])["d"]
    ir = mm(tr["read_from"]) - mm("09:15")
    es = series[(key, d)]
    ic = max(i for i in range(ir + 1) if hold.is_close(hold.SESSION[i]))
    e = es[ic]
    # since / was on the close series
    cl = [i for i in range(ic + 1) if hold.is_close(hold.SESSION[i])]
    since, was, until = hold.SESSION[ic], None, None
    for a, b in zip(reversed(cl[:-1]), reversed(cl[1:])):
        if label(es[a]) == label(e):
            since = hold.SESSION[a]
        else:
            was, until = label(es[a]), hold.SESSION[b]
            break
    rm = A.r_mults(D, ir, d, {**e, "line": series[(key, d)][ir]["line"] or e["line"]}) if e.get("word") else {}
    sell = e["sell"] if e.get("word") else {}
    ww = A.writer_word_a(D, ir, sell.get("side"), sell.get("k"), d, FRS[key]) if sell.get("k") else {"word": None}
    other = {}
    if sell.get("k"):
        k, side = sell["k"], sell["side"]
        pk = D["prem"][f"{int(k)}{side}"]["c"]
        p0 = pk[ir]
        W = X.window_first_fold(D, {"side": side, "role": "short", "t0": hm(mm(tr["read_from"]) + 1), "k": k,
                                    "p0": p0, "qty": 1})
        f5 = W.get("fold") or {}
        yes = A.reach_a(D, W["rows"], k, side, d, pk, True, key in EXP_TODAY)
        no = A.reach_a(D, W["rows"], k, side, d, pk, False, key in EXP_TODAY)
        at = lambda t: pk[mm(t) - mm("09:15")] if t else None
        other = {"k": k, "side": side, "placement": sell["placement"], "p0": p0,
                 "rev5": (f5.get("t"), f5.get("rule"), round(p0 - at(f5["t"]), 2) if f5.get("t") else None),
                 "yes": (yes["fold"], yes["rule"], round(p0 - at(yes["fold"]), 2) if yes["fold"] else None, yes["events"],
                         yes.get("P_b"), yes.get("P_max")),
                 "no": (no["fold"], no["rule"], round(p0 - at(no["fold"]), 2) if no["fold"] else None),
                 "close": round(p0 - pk[374], 2)}
    ent.append({"id": tr["id"], "read": tr["read_from"], "close_read": hold.SESSION[ic], "d": "UP" if d > 0 else "DOWN",
                "word": label(e), "named_by": e.get("named_by"), "nb": e.get("nb"), "ns": e.get("ns"),
                "facts": {n: v[0] for n, v in (e.get("facts") or {}).items()}, "ref": e.get("ref_b", []) + e.get("ref_s", []),
                "since": since, "was": was, "until": until, "word4": e.get("word4"),
                "word_1m": label(es[ir]), "word_rev0a": (old.get(tr["id"]) or {}).get("word"),
                "buy": e.get("buy"), "sell": sell, "rmult": rm, "writer": ww, "other": other,
                "her_pts": round(tr["px"] - tr["p0"], 2)})
json.dump(ent, open(os.path.join(OUT, "entries.json"), "w"), indent=1, default=str)

# ---- 4. the 09-24 seller case (her PE entries as CE sales at the same strike), both answers of §C.7 ----
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
    yes = A.reach_a(D, W["rows"], k, "CE", -1, pk, True, True)
    no = A.reach_a(D, W["rows"], k, "CE", -1, pk, False, True)
    sel.append({"trade": tr["id"], "k": k, "CE0": pk[i], "rev5": (f5.get("t"), f5.get("rule"), at(f5.get("t"))),
                "yes": {k2: yes.get(k2) for k2 in ("fold", "rule", "R", "S", "events", "P_b", "P_max")} | {"P_x": at(yes["fold"])},
                "no": {"fold": no["fold"], "rule": no["rule"], "P_x": at(no["fold"])}, "CE_1529": pk[374]})
json.dump(sel, open(os.path.join(OUT, "seller_0924.json"), "w"), indent=1, default=str)
for s in sel:
    print(s, flush=True)

# ---- 5. the grid: expression units, the writer population (ii), scoreability, held breaks ----
grid = {"units": 0, "words": {}, "scored_G": 0, "notscored": {}, "writer": {"30": {}, "1529": {}, "stratum": 0, "words": {}},
        "held_breaks": []}
for (key, d), es in series.items():
    D = th._day(*key)
    for i in UNITS:
        e = es[i]
        grid["units"] += 1
        grid["words"][label(e)] = grid["words"].get(label(e), 0) + 1
        if not e.get("word"):
            continue
        rm = A.r_mults(D, i, d, e)
        if "G" in rm:
            grid["scored_G"] += 1
        else:
            why = (rm.get("buy", {}).get("why") or rm.get("sell", {}).get("why"))
            grid["notscored"][why] = grid["notscored"].get(why, 0) + 1
        s = e["sell"]
        if s["k"]:
            w = A.writer_word_a(D, i, s["side"], s["k"], d, FRS[key])
            if w.get("word"):
                grid["writer"]["words"][w["word"]] = grid["writer"]["words"].get(w["word"], 0) + 1
                grid["writer"]["30"][w["out30"]] = grid["writer"]["30"].get(w["out30"], 0) + 1
                grid["writer"]["1529"][w["out1529"]] = grid["writer"]["1529"].get(w["out1529"], 0) + 1
                grid["writer"]["stratum"] += w["stratum"]
            pk = D["prem"][f"{int(s['k'])}{s['side']}"]["c"]
            W = X.window_first_fold(D, {"side": s["side"], "role": "short", "t0": hm(i + mm("09:15") + 1), "k": s["k"],
                                        "p0": pk[i], "qty": 1})
            if W.get("ok"):
                rc = A.reach_a(D, W["rows"], s["k"], s["side"], d, pk, True, key in EXP_TODAY)
                if rc["events"] and rc["events"][0][0] == "held":
                    at = lambda t: pk[mm(t) - mm("09:15")] if t else pk[374]
                    grid["held_breaks"].append({"day": key, "unit": hold.SESSION[i], "k": s["k"], "side": s["side"],
                                                "held": rc["events"][0], "fold": rc["fold"], "rule": rc["rule"],
                                                "P_b": rc["P_b"], "P_x": at(rc["fold"]), "P_max": rc["P_max"]})
json.dump(grid, open(os.path.join(OUT, "grid.json"), "w"), indent=1, default=str)
print("grid", {k: v for k, v in grid.items() if k != "held_breaks"}, len(grid["held_breaks"]), flush=True)
print("done", round(time.time() - t0), "s")
