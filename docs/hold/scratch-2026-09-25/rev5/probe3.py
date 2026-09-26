"""Scratch probe for PREREG rev 5 (a): the line breaks on the CLOSE of the 3-min index bar
(09:15-aligned grid), not on a 1-min close. Read-only: imports hold.py and the test harness,
monkeypatches hold.line in THIS process only. Never edits the repo."""
import json
import os
import sys

REPO = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # the as-built rev 4 hold.py (scratchpad/orig), not the file being edited tonight
os.chdir(REPO)
import hold          # noqa: E402
import test_hold as th  # noqa: E402

ORIG = hold.line
mm, hm, CC = hold.mm, hold.hm, hold.CC
T0 = mm("09:15")


def bar_close(t):
    """True when minute t is the LAST minute of its 3-min bar on the 09:15 grid."""
    return (mm(t) - T0) % 3 == 2


def line3(minutes, pivs, d, e):
    """hold.line verbatim except the break: a 3-min bar's close (its last minute's 1-min close)
    beyond L. Between bar closes the line's broken/not state is the last closed bar's."""
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
            if bar_close(m["t"]):
                carried = c > L if bear else c < L
                if carried and broken is None:
                    broken = m["t"]
            beyond = carried
        out[i] = {"L": L, "src": src, "room": round(L - c if bear else c - L), "px": c,
                  "beyond": beyond, "broken_at": broken, "by": round(abs(c - L), 1)}
        prev = c
    return out


def run(tr, which):
    hold.line = line3 if which == 3 else ORIG
    try:
        r, D = th._read(tr)
    finally:
        hold.line = ORIG
    return r, D


def main():
    rows = []
    for tr in th._trades():
        r4, D = run(tr, 1)
        if r4 is None:
            continue
        r5, _ = run(tr, 3)
        i0 = mm(hold.read_minute(tr["t0"])) - T0

        def desc(r):
            f = r["fold"]
            if not f:
                return None
            row = next(x for x in r["rows"] if x["t"] == f["t"])
            ln = row["line"]
            out = {"t": f["t"], "rule": f["rule"], "L": ln.get("L"), "px": ln.get("px")}
            if f["rule"] == 3:
                out["by"] = round(abs(ln["px"] - ln["L"]), 1)
            pc = (D["prem"].get(f"{int(tr['k'])}{tr['side']}") or {}).get("c") or []
            j = mm(f["t"]) - T0
            p = pc[j] if j < len(pc) else None
            if p is not None and tr.get("p0"):
                sg = 1 if tr["role"] == "long" else -1
                out["prem_pts"] = round(sg * (p - tr["p0"]), 1)
            return out
        a, b = desc(r4), desc(r5)
        if a == b or (a and b and (a["t"], a["rule"]) == (b["t"], b["rule"])):
            what = "same"
        elif b is None:
            what = "disappeared"
        else:
            what = "moved"
        rows.append({"id": tr["id"][:44].strip(), "entry4": r4["entry"]["verdict"], "entry5": r5["entry"]["verdict"],
                     "rev4": a, "rev5": b, "what": what,
                     "rev4_at_bar_close": bool(a and bar_close(a["t"]))})
    json.dump(rows, open(os.path.join(os.path.dirname(__file__), "probe3_out.json"), "w", encoding="utf-8"), indent=1)
    RN = {3: "line", 4: "flipped", 5: "quiet", 6: "two", None: "-"}
    for x in rows:
        a, b = x["rev4"] or {}, x["rev5"] or {}
        print(f"{x['id']:44s} {x['entry4']:5s}/{x['entry5']:5s} rev4 {a.get('t','none'):5s} {RN[a.get('rule')]:7s}"
              f" {('by '+str(a['by'])) if 'by' in a else '':8s} {('prem '+str(a.get('prem_pts'))) if a else '':12s}"
              f"| rev5 {b.get('t','none'):5s} {RN[b.get('rule')]:7s} {('by '+str(b['by'])) if 'by' in b else '':8s}"
              f" {('prem '+str(b.get('prem_pts'))) if b else '':12s} {x['what']}{' (rev4 fold minute was a bar close)' if x['rev4_at_bar_close'] and a.get('rule')==3 else ''}")
    from collections import Counter
    print(Counter(x["what"] for x in rows), "n =", len(rows))
    print("rev4 line folds:", sum(1 for x in rows if (x["rev4"] or {}).get("rule") == 3),
          "| rev5 line folds:", sum(1 for x in rows if (x["rev5"] or {}).get("rule") == 3))
    print("entry verdict changed:", [x["id"] for x in rows if x["entry4"] != x["entry5"]])


if __name__ == "__main__":
    main()
