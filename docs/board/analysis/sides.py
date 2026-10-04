"""Round 3: the OI flow split by side against the index move. Definitions FIXED 2026-10-03 23:38 IST in
tapemap/docs/board/real-vs-fake-2026-10-03.md §2 -- do not change a number here without changing that note
and saying so. Read-only on data/.  Usage: python sides.py DAY [--table out.txt]"""
import json, os, statistics, sys
sys.path.insert(0, os.path.dirname(__file__))
from replay import load, ROOT  # noqa
import chain_metrics, fronts  # noqa

IDX = ("NIFTY", "BANKNIFTY", "SENSEX")
WARM, FLAT_K, BROAD, POWER_R, GAP, FREEZE = 6, 0.5, 6, 3.0, 15, 15 * 60 + 15
mm = lambda t: int(t[:2]) * 60 + int(t[3:5])
hm = lambda m: f"{m // 60:02d}:{m % 60:02d}"
sgn = lambda x: (x > 0) - (x < 0)


def state_of(idx, day):
    st = chain_metrics.ChainState()
    bf = os.path.join(ROOT, "data", "chain_backfill", f"backfill_{idx}_{day}.jsonl")
    if os.path.exists(bf):
        for line in open(bf):
            r = json.loads(line)
            st.minutes[r["t"]] = {"spot": r["spot"], "k": {float(k): tuple(v) for k, v in r["k"].items()}}
    for s in load(idx, day):
        st.minutes[(s.get("ts") or "00:00:00")[:5]] = {
            "spot": s["spot"], "k": {float(r["k"]): ((r["ce"].get("oi_chg") or 0.0), (r["pe"].get("oi_chg") or 0.0)) for r in s["strikes"]}}
    return st


def side(d, hist, same):
    """(state, ratio, power) for one side in one slot, against that side's earlier slots today."""
    if len(hist) < WARM:
        return None, None, False
    M = statistics.median(hist)
    r = abs(d) / M if M > 0 else (float("inf") if d else 0.0)
    if abs(d) <= FLAT_K * M:
        return "FLAT", r, False
    st = "ADD" if d > 0 else "COV"
    return st, r, (r >= POWER_R and same >= BROAD)


def word(I, c, p, cpow, ppow):
    if I is None or c is None or p is None:
        return None
    if I == "FLAT":
        cov = [n for n, s, pw in (("▲", c, cpow), ("▼", p, ppow)) if pw and s == "COV"]
        if cov:
            return "PRESSURE " + "".join(cov)
        if (cpow and c == "ADD") or (ppow and p == "ADD"):
            return "WALL"
        return "FLAT"
    # the move's own side: UP -> (fuel = CE covering, floor = PE adding); DOWN mirrors
    fuel, back = (c, p) if I == "UP" else (p, c)
    if fuel == "COV" and back == "ADD":
        return "REAL"
    if fuel == "COV":
        return "SQUEEZE"
    if fuel == "ADD" and back in ("ADD", "FLAT"):
        return "CAPPED"
    if fuel == "ADD" and back == "COV":
        return "FAKE"
    if back == "ADD":
        return "BACKED"
    if back == "COV":
        return "HOLLOW"
    return "QUIET"


def run(idx, day):
    st = state_of(idx, day)
    rows = st.oi_flow(interval=5)
    mins = sorted(st.minutes)
    rec = lambda t: st.minutes[max(m for m in mins if m <= t)]
    spot = {r["time"]: r["ltp"] for r in rows}
    H = {"ce": [], "pe": [], "I": []}
    out, last_pow = [], {1: None, -1: None}
    for a, b in zip(rows, rows[1:]):
        t = b["time"]
        A, B = rec(a["time"]), rec(t)
        ks = [k for k in B["k"] if k in A["k"]]
        dk = {k: (B["k"][k][0] - A["k"][k][0], B["k"][k][1] - A["k"][k][1]) for k in ks}
        dce, dpe = sum(v[0] for v in dk.values()), sum(v[1] for v in dk.values())
        nine = fronts.nine(ks, b["ltp"]) if b["ltp"] is not None else []
        same_ce = sum(1 for k in nine if dk[k][0] and sgn(dk[k][0]) == sgn(dce))
        same_pe = sum(1 for k in nine if dk[k][1] and sgn(dk[k][1]) == sgn(dpe))
        dI = None if (mm(t) > FREEZE or b["ltp"] is None or a["ltp"] is None) else b["ltp"] - a["ltp"]
        c, cr, cp = side(dce, H["ce"], same_ce)
        p, pr, pp = side(dpe, H["pe"], same_pe)
        if dI is None or len(H["I"]) < WARM:
            I = None
        else:
            MI = statistics.median(H["I"])
            I = "FLAT" if abs(dI) <= FLAT_K * MI else ("UP" if dI > 0 else "DOWN")
        w = word(I, c, p, cp, pp)
        dirs = set()
        if cp:
            dirs.add(1 if c == "COV" else -1)
        if pp:
            dirs.add(1 if p == "ADD" else -1)
        pdir = (dirs.pop() if len(dirs) == 1 else 0) if dirs else None
        first = False
        if pdir in (1, -1):
            lp = last_pow[pdir]
            first = lp is None or mm(t) - lp > GAP
            last_pow[pdir] = mm(t)
        fut = {}
        for h in (15, 30):
            tt = hm(mm(t) + h)
            fut[h] = (None if mm(tt) > FREEZE or tt not in spot or spot[tt] is None or b["ltp"] is None
                      else spot[tt] - b["ltp"])
        out.append({"t": t, "idx": idx, "dce": dce, "dpe": dpe, "c": c, "cr": cr, "cs": same_ce, "cp": cp,
                    "p": p, "pr": pr, "ps": same_pe, "pp": pp, "dI": dI, "I": I, "w": w,
                    "power": cp or pp, "pdir": pdir, "first": first, "f15": fut[15], "f30": fut[30], "n9": len(nine)})
        H["ce"].append(abs(dce)); H["pe"].append(abs(dpe))
        if dI is not None:
            H["I"].append(abs(dI))
    return out


def fmt_side(name, s, r, same, pw):
    if s is None:
        return f"{name} warm"
    rr = "∞" if r == float("inf") else f"{r:.1f}"
    return f"{name} {s:4} ×{rr:>4} {same}/9{'*' if pw else ' '}"


def main(day, table=None):
    R = {k: {x["t"]: x for x in run(k, day)} for k in IDX}
    times = sorted(set().union(*R.values()))
    ARW = {1: "▲", -1: "▼", 0: "both", None: ""}
    print(f"=== {day}  POWER slots (* = POWER side, ! = first sign)")
    for t in times:
        xs = [R[k].get(t) for k in IDX]
        pw = [x for x in xs if x and x["power"]]
        if not pw:
            continue
        same_read = all(x and x["w"] for x in xs) and len({x["w"] for x in xs}) == 1
        tag = f"[{len(pw)}/3 power{' · 3/3 same read ' + xs[0]['w'] if same_read else ''}]"
        for x in pw:
            f15 = "·" if x["f15"] is None else f"{x['f15']:+.0f}"
            f30 = "·" if x["f30"] is None else f"{x['f30']:+.0f}"
            dI = "frozen" if x["dI"] is None else f"{x['dI']:+.0f}"
            print(f"{t} {x['idx']:9} {'!' if x['first'] else ' '} {ARW[x['pdir']]:4} | {fmt_side('CE', x['c'], x['cr'], x['cs'], x['cp'])} | "
                  f"{fmt_side('PE', x['p'], x['pr'], x['ps'], x['pp'])} | idx {dI:>6} {x['I'] or '-':5} | {x['w'] or '-':12} | +15 {f15:>5} +30 {f30:>5} {tag}")
    if table:
        with open(table, "w", encoding="utf-8") as f:
            f.write(f"{day} · every 5-min slot · per index: READ word, CE side, PE side, index move. "
                    f"'*' POWER side, '!' first sign. Sides: ADD/COV/FLAT ×(size vs that side's day median) "
                    f"(strikes of the nine moving the same way). Definitions: real-vs-fake-2026-10-03.md §2.\n\n")
            for t in times:
                cells = []
                for k in IDX:
                    x = R[k].get(t)
                    if not x:
                        cells.append(f"{'—':44}")
                        continue
                    def s(st, r, n, p):
                        if st is None:
                            return "warm"
                        return f"{st}{'*' if p else ''}{'' if r is None else ('×∞' if r == float('inf') else f'×{r:.1f}')}({n})"
                    dI = "frz" if x["dI"] is None else f"{x['dI']:+.0f}"
                    cells.append(f"{('!' if x['first'] else ' ')}{(x['w'] or '-'):11} CE {s(x['c'], x['cr'], x['cs'], x['cp']):13} PE {s(x['p'], x['pr'], x['ps'], x['pp']):13} {dI:>5}"[:58].ljust(58))
                f.write(f"{t} | " + " | ".join(cells) + "\n")
    return R


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[a.index("--table") + 1] if "--table" in a else None)
