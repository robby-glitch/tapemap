"""analyze8.py -- candidates (i)..(v) side by side + the four diagnoses, from replays_*.json. Pure."""
import json
import os
import sys

import analyze7 as A

OUT = sys.argv[1] if len(sys.argv) > 1 else "."


def evs_of(r):
    out = []
    for e in r["events"]:
        if e["ts"] > "15:00:00":
            break
        out.append(dict(e, d=r["d"]))
    return out


def cand_ivb(r, confirm=False):
    """(iv): an OI event on W born while she is under water by >= w, at entry (pre-trail) -> FOLD 'gave up'.
    confirm=True: also FLOW or VPIN AGAINST while that event is live and price still against."""
    evs = evs_of(r)
    f6 = A.first(evs, lambda e: e["kind"] == "fold")
    ok = False
    for e in evs:
        if f6 and e["t"] > f6["t"]:
            break
        if e["kind"] == "oi_event":
            ok = e["mode"] == "at entry" and A.against_px(e) and e["chips"].get("O") != "CAN'T CHECK"
        elif not e["oi_ev"]:
            ok = False
        if ok and e["oi_ev"] and e["mode"] == "at entry" and A.against_px(e):
            if not confirm or "AGAINST" in (e["chips"].get("F"), e["chips"].get("V")):
                return e
    return None


def story(r, e, path=None, p0=None, own=None):
    return A.after(r, e["t"], path, p0, own) if e else None


def exit_pct(r, e, path=None, p0=None, own=None):
    """the exit a rule gives: its first speak, else rev 6's FOLD, else 15:00"""
    path = r["path"] if path is None else path
    if e is None:
        return A.pct(r, path[-1][1], p0, own), "15:00"
    return A.pct(r, A.at(path, e["t"]), p0, own), e["ts"][:5]


def rule_exit(r, key, c):
    """earliest of the rule's speak and rev 6's FOLD (the rule is added to rev 6, not instead of it)"""
    e6 = c["rev6"]
    e = c.get(key)
    if key == "rev6":
        return e6
    if key in ("capG", "nostep"):
        return e                        # a re-run engine: its own first FOLD (rev 6's rules included)
    if e is None:
        return e6
    if e6 is None or e["t"] < e6["t"]:
        return e
    return e6


if __name__ == "__main__":
    rows = []
    for r in A.R:
        c = A.candidates(r)
        c["ivb"] = cand_ivb(r)
        c["ivc"] = cand_ivb(r, confirm=True)
        rows.append((r, c))
    keys = ["rev6", "i", "iv", "ivb", "ivc", "capG", "nostep"]
    names = dict(rev6="rev 6", i="(i) OI event + price against", iv="(iv-a) (i) + flow/VPIN against",
                 ivb="(iv) gave up under pressure", ivc="(iv-c) (iv) + flow/VPIN", capG="(iii) G cap -25 %", nostep="(v) no G step while losing")
    # ---- per-rule exits, every replay
    print("| replay | rev 6 | " + " | ".join(names[k] for k in keys[1:]) + " | 15:00 |")
    tab = {}
    for r, c in rows:
        cells = []
        for k in keys:
            e = rule_exit(r, k, c)
            p, t = exit_pct(r, e)
            cells.append(f"{p:+d} {t}" if p is not None else "-")
            tab.setdefault(k, []).append((r, e, p, t))
        print(f"| {r['name']} | " + " | ".join(cells) + f" | {A.pct(r, r['path'][-1][1]):+d} |")
    # ---- changed rows per rule
    for k in keys[1:]:
        ch = []
        for (r, e6, p6, t6), (_, e, p, t) in zip(tab["rev6"], tab[k]):
            if t != t6:
                ch.append((r["name"], p6, t6, p, t, story(r, e)))
        better = sum(1 for x in ch if x[3] > x[1])
        worse = sum(1 for x in ch if x[3] < x[1])
        print(f"\n### {names[k]}: changes {len(ch)} rows (premium at exit higher than rev 6 on {better}, lower on {worse})")
        for x in ch:
            print(f"   {x[0]:28} rev6 {x[1]:+d} {x[2]} -> {x[3]:+d} {x[4]} | after: {x[5]}")
    # ---- mirrors (zone: short the other side, same d, same speak)
    print("\n### zone mirrors (sell the other side at the same second): rev 6 v (iv)")
    for r, c in rows:
        m = r.get("mirror")
        if not m or not m["path"]:
            continue
        e6, e4 = rule_exit(r, "rev6", c), rule_exit(r, "ivb", c)
        p6, t6 = exit_pct(r, e6, m["path"], m["p0"], -1)
        p4, t4 = exit_pct(r, e4, m["path"], m["p0"], -1)
        if t4 != t6:
            print(f"   {r['name']:28} short {m['ty']} @ {m['p0']}: rev6 {p6:+d} {t6} -> (iv) {p4:+d} {t4} | 15:00 {A.pct(r, m['path'][-1][1], m['p0'], -1):+d}")
    json.dump({k: [(r["name"], p, t) for r, e, p, t in v] for k, v in tab.items()}, open(os.path.join(OUT, "rule_exits.json"), "w"))
