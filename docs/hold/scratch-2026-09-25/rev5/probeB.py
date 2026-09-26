"""Scratch, read-only: PREREG rev 5a OPTION B -- the line breaks on a 3-min bar close beyond L by
more than B, B = the median high-low of the index's last 15 finished 1-min candles at the minute L
was set or last trailed, FROZEN with L (buffer 0 until 15 candles exist, then read once and frozen).
Frozen trades: hold.read with hold.line replaced in this process (the as-built rev 4 copy beside
this file). Also re-runs option A (probe3.line3) so both columns come from one run."""
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
os.chdir(REPO)
import hold          # noqa: E402  (the as-built rev 4 copy in this folder)
import probe3        # noqa: E402
import test_hold as th  # noqa: E402

mm, CC = hold.mm, hold.CC
bar_close = probe3.bar_close
N = 15


def noise(minutes, i):
    if i - N + 1 < 0:
        return None
    xs = [minutes[j].get("ix") for j in range(i - N + 1, i + 1)]
    if any(x is None for x in xs):
        return None
    return round(statistics.median(x[1] - x[2] for x in xs), 2)


def lineB(minutes, pivs, d, e):
    bear = d < 0
    kind, word = ("H", "high") if bear else ("L", "low")
    m0 = minutes[e]
    if not m0.get("ix"):
        return None

    def far(p, c):
        return p > c if bear else p < c
    px0, t0 = m0["ix"][0], mm(m0["t"])
    mine = [p for p in pivs if p["kind"] == kind]
    known = sorted((p for p in mine if mm(p["confirm"]) <= t0 and far(p["price"], px0)),
                   key=lambda p: mm(p["bar"]), reverse=True)
    used = set()
    if known:
        L, src = known[0]["price"], f"5m swing {word} {known[0]['bar']}"
        used.add(known[0]["bar"])
    else:
        seen = [m["ix"] for m in minutes[:e + 1] if m.get("ix")]
        L = max(x[1] for x in seen) if bear else min(x[2] for x in seen)
        src = f"session {word} so far, no 5m swing {'above' if bear else 'below'} you yet"
    B = noise(minutes, e)
    B_at = minutes[e]["t"] if B is not None else None
    out, broken, prev, carried = {}, None, px0, False
    for i in range(e, len(minutes)):
        m = minutes[i]
        if not m.get("ix"):
            out[i] = {"L": L, "src": src, "broken_at": broken, "blind": CC + f"no index candle at {m['t']}"}
            continue
        c, beyond = m["ix"][0], False
        if i > e:
            for p in sorted((p for p in mine if p["bar"] not in used and t0 <= mm(p["confirm"]) < mm(m["t"])),
                            key=lambda p: mm(p["confirm"])):
                used.add(p["bar"])
                if (p["price"] < L if bear else p["price"] > L) and far(p["price"], prev):
                    L, src = p["price"], f"5m swing {word} {p['bar']}"
                    B = noise(minutes, i)
                    B_at = m["t"] if B is not None else None
            if B is None:
                B = noise(minutes, i)
                B_at = m["t"] if B is not None else None
            if bar_close(m["t"]):
                lvl = L + (B or 0) if bear else L - (B or 0)
                carried = c > lvl if bear else c < lvl
                if carried and broken is None:
                    broken = m["t"]
            beyond = carried
        lvl = L + (B or 0) if bear else L - (B or 0)
        out[i] = {"L": L, "src": src, "room": round(L - c if bear else c - L), "px": c,
                  "beyond": beyond, "broken_at": broken, "B": B, "B_at": B_at, "level": round(lvl, 2)}
        prev = c
    return out


def run(tr, fn):
    hold.line = fn
    try:
        return th._read(tr)
    finally:
        hold.line = probe3.ORIG


def desc(r, D, tr, fn):
    f = r["fold"]
    if not f:
        return None
    out = {"t": f["t"], "rule": f["rule"]}
    if f["rule"] == 3:
        LN = fn(D["minutes"], D["pivots"], r["th"]["d"], hold.mm(hold.read_minute(tr["t0"])) - hold.mm("09:15"))
        i = hold.mm(f["t"]) - hold.mm("09:15")
        ln = LN[i]
        out.update(L=ln["L"], px=ln["px"], by_L=round(abs(ln["px"] - ln["L"]), 1))
        if "B" in ln:
            out.update(B=ln["B"], B_at=ln["B_at"], level=ln["level"], by_level=round(abs(ln["px"] - ln["level"]), 1))
    pc = (D["prem"].get(f"{int(tr['k'])}{tr['side']}") or {}).get("c") or []
    j = hold.mm(f["t"]) - hold.mm("09:15")
    p = pc[j] if j < len(pc) else None
    if p is not None and tr.get("p0"):
        out["prem_pts"] = round((1 if tr["role"] == "long" else -1) * (p - tr["p0"]), 1)
    return out


def main():
    rows = []
    for tr in th._trades():
        r4, D = run(tr, probe3.ORIG)
        if r4 is None:
            continue
        rA, _ = run(tr, probe3.line3)
        rB, _ = run(tr, lineB)
        a, A, B = desc(r4, D, tr, probe3.ORIG), desc(rA, D, tr, probe3.line3), desc(rB, D, tr, lineB)

        def what(x):
            if x is None and a is None:
                return "none both"
            if x is None:
                return "disappeared"
            if a and (x["t"], x["rule"]) == (a["t"], a["rule"]):
                return "same"
            return "moved"
        rows.append({"id": tr["id"][:44].strip(), "entry": [r4["entry"]["verdict"], rA["entry"]["verdict"], rB["entry"]["verdict"]],
                     "rev4": a, "A": A, "B": B, "whatA": what(A), "whatB": what(B)})
    json.dump(rows, open(os.path.join(HERE, "probeB_out.json"), "w", encoding="utf-8"), indent=1)
    RN = {3: "line", 4: "flipped", 5: "quiet", 6: "two"}

    def f(x):
        if not x:
            return "none"
        s = f"{x['t']} {RN[x['rule']]}"
        if x["rule"] == 3:
            s += f" by {x['by_L']}" + (f" (B {x['B']} @{x['B_at']}, past level {x['by_level']})" if "B" in x else "")
        return s + f" prem {x.get('prem_pts')}"
    for x in rows:
        print(f"{x['id']:44s} {'/'.join(x['entry'])} | rev4 {f(x['rev4'])} | A {f(x['A'])} [{x['whatA']}] | B {f(x['B'])} [{x['whatB']}]")
    from collections import Counter
    print("A:", Counter(x["whatA"] for x in rows), "B:", Counter(x["whatB"] for x in rows), "n", len(rows))


if __name__ == "__main__":
    main()
