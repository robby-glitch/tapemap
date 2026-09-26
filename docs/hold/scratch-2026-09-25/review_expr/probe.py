# Reviewer's probe of EXPRESSION-PREREG-DRAFT rev 0a: construction properties only (flip rate, margins, words by
# refusal, fact co-occurrence, sell-strike distance in straddles, % elasticity of the two legs). No word is scored
# against an outcome. Reads the frozen fixtures through the drafter's expr.py; writes only into this folder.
import sys, os, json, statistics as st
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "expr"))
import expr as X  # noqa: E402  (chdirs into tapemap; reads docs/hold/opus/scratch only)
th, hold = X.th, X.hold
mm = hold.mm

DAYS = [(i, d) for d in ("2026-09-22", "2026-09-23", "2026-09-24") for i in ("NIFTY", "SENSEX", "BANKNIFTY")]
res = {}
for key in DAYS:
    D = th._day(*key)
    FR = X.oihist_fr(*key)
    for d in (1, -1):
        seq = []
        for i in range(len(D["minutes"])):
            e = X.expression(D, i, d, FR)
            w = e.get("word")
            wk = (w.split(" ")[0] if w and w.startswith(("BUY", "SELL")) else w) or "CNC"
            f = {k: v[0] for k, v in (e.get("facts") or {}).items()}
            sell = e.get("sell") or {}
            S_, atm = X.straddle(D, i)
            sq, _ = X.straddle15(D, i)
            ix = D["minutes"][i].get("ix")
            ix15 = D["minutes"][i - 15].get("ix") if i >= 15 else None
            seq.append({"i": i, "t": D["minutes"][i]["t"], "w": wk, "nb": e.get("nb"), "ns": e.get("ns"),
                        "rb": bool(e.get("ref_b")), "rs": bool(e.get("ref_s")),
                        "rs_codes": [r[:2] for r in e.get("ref_s", [])], "f": f,
                        "sk": sell.get("k"), "sside": sell.get("side"), "otm": sell.get("otm"),
                        "spx": sell.get("px"), "bk": (e.get("buy") or {}).get("k"),
                        "bpx": (e.get("buy") or {}).get("px"), "S": S_,
                        "mv15": (ix[0] - ix15[0]) if ix and ix15 else None,
                        "sq": sq and sq["state"]})
        res[f"{key[0]} {key[1]} {d}"] = seq
        print(key, d, flush=True)

json.dump(res, open(os.path.join(HERE, "per_minute.json"), "w"))
print("done")
