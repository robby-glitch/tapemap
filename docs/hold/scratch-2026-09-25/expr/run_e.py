# The rev e disclosure run. Rules as fingerprinted (rules_reve_before_run.md, sha256 fb583979...0cc9).
# Rev e moves only the writer's word (§B.2), so this re-reads the writer word at every 3-minute close, at her entries and at
# the grid units; every other table is rev d's (expr/revd/). Counts only; no word crossed with an outcome. Writes to expr/reve/.
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expr_e as EE       # noqa: E402
E = EE.E
X, hold = E.X, E.hold
th = X.th
mm = hold.mm
OUT = os.path.join(HERE, "reve")
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
DAYS = [(i, d) for d in ("2026-09-22", "2026-09-23", "2026-09-24") for i in ("NIFTY", "SENSEX", "BANKNIFTY")]
FRS = {k: X.oihist_fr(*k) for k in DAYS}
UNITS = set(i for i, t in enumerate(hold.SESSION) if hold.is_close(t) and t >= "09:44" and (mm(t) - mm("09:44")) % 30 == 0)
inc = lambda dct, k: dct.__setitem__(k, dct.get(k, 0) + 1)

closes = {"n": 0, "words": {}, "words_d": {}, "moved": {}, "go_beside_sell_refusal": 0, "go_beside_sell_refusal_d": 0}
grid = {"n": 0, "words": {}, "words_d": {}, "moved": {}, "stratum": {}, "stratum_beyond": {}, "beyond": 0,
        "resolved30": 0, "resolved1529": 0, "notscored": 0, "resolved30_stratum": 0}
for key in DAYS:
    D = th._day(*key)
    for d in (1, -1):
        for i in range(len(D["minutes"])):
            if not hold.is_close(hold.SESSION[i]):
                continue
            e = E.expression_d(D, i, d, FRS[key])
            if not e.get("word"):
                continue
            s = e["sell"]
            w = EE.writer_word_e(D, i, s["side"], s["k"], d, FRS[key])
            if not w.get("word"):
                continue
            closes["n"] += 1
            inc(closes["words"], w["word"]); inc(closes["words_d"], w["word_d"])
            if w["word"] != w["word_d"]:
                inc(closes["moved"], f"{w['word_d']} -> {w['word']}")
            closes["go_beside_sell_refusal"] += w["word"] == "GO" and bool(e["ref_s"])
            closes["go_beside_sell_refusal_d"] += w["word_d"] == "GO" and bool(e["ref_s"])
            if i in UNITS:
                g = grid
                g["n"] += 1
                inc(g["words"], w["word"]); inc(g["words_d"], w["word_d"])
                if w["word"] != w["word_d"]:
                    inc(g["moved"], f"{w['word_d']} -> {w['word']} ({key[0]} {key[1][5:]})")
                g["beyond"] += w["line_beyond_strike"]
                if w["stratum"]:
                    inc(g["stratum"], w["word"])
                    if w["line_beyond_strike"]:
                        inc(g["stratum_beyond"], w["word"])
                    g["resolved30_stratum"] += w["out30"] in ("target", "stop", "same minute")
                g["resolved30"] += w["out30"] in ("target", "stop", "same minute")
                g["resolved1529"] += w["out1529"] in ("target", "stop", "same minute")
                g["notscored"] += w["out30"] == "not scored"
    print(key, round(time.time() - t0), "s", flush=True)

ent = []
for x in json.load(open(os.path.join(HERE, "revd", "entries.json"), encoding="utf-8")):
    if "why" in x:
        ent.append({"id": x["id"], "why": x["why"]}); continue
    day, hhmm, idx, leg = x["id"].split(" ")
    key = (idx, "2026-" + day)
    D = th._day(*key)
    ir = mm(x["read"]) - mm("09:15")
    d = 1 if x["d"] == "UP" else -1
    s = x["sell"]
    w = EE.writer_word_e(D, ir, s["side"], s["k"], d, FRS[key])
    ent.append({"id": x["id"], "word": w.get("word"), "word_d": w.get("word_d"), "no_wall": w.get("no_wall"),
                "word_d_file": x["writer"]["word"]})
json.dump({"closes": closes, "grid": grid, "entries": ent}, open(os.path.join(OUT, "writer.json"), "w"), indent=1)
print(json.dumps({"closes": closes, "grid": grid}, indent=1))
print("entries moved", [(y["id"], y["word_d"], y["word"]) for y in ent if "why" not in y and y["word"] != y["word_d"]])
print("entries d reproduces file", all(y["word_d"] == y["word_d_file"] for y in ent if "why" not in y))
print("done", round(time.time() - t0), "s")
