"""The second look: every Round-2 survivor counted the same way on each day, from days.json (her 3-min closes, causal).
Run from tapemap/:  python -I -X utf8 docs/optflow/fable/secondlook.py [2026-11-02] [2026-11-03]
Counts, never a rate; the two days are printed as two columns and never pooled. Ideas were formed on 3 Nov; 2 Nov is a
recorded day looked at afterwards, not the pre-registered forward test."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import hm, m_of, D
import load as _load

HERE = os.path.dirname(os.path.abspath(__file__))
HI = {"W": "WRITE", "B": "BUY", "C": "COVER", "D": "DUMP", "M": "MIXED", "Q": "QUIET", "?": "OI?", "F": "FLOW?"}


def closes(x):
    return [i for i, m in enumerate(x["mins"]) if (m - 555) % 3 == 2]


def fut_at(x, i, k):
    j = i + k
    return (x["fut"][j] - x["fut"][i]) if j < len(x["fut"]) and x["fut"][i] is not None and x["fut"][j] is not None else None


def f(v):
    return "?" if v is None else f"{v:+.0f}"


def pushes_vs_flow(x):
    out = []
    for p in x["pushes"]:
        am = m_of(p["am"]) if p["am"] else m_of(p["t"]) + 2
        j = x["mins"].index(am) if am in x["mins"] else (x["mins"].index(m_of(p["t"])) if m_of(p["t"]) in x["mins"] else None)
        if j is None:
            continue
        q = [n for n, k in enumerate(x["strikes"]) if k[0] == p["k"] and k[1] == p["side"]]
        who = HI[x["who"][j][q[0]]] if q and x["who"][j][q[0]] else "nofp"
        out.append((p["t"], p["dir"], p["ans"], who, p.get("p15"), p.get("p30")))
    return out


def study(day):
    _load.CUR["day"] = day
    days = json.load(open(os.path.join(HERE, "days.json"), encoding="utf-8"))
    x = days[day]["NIFTY"]
    C = closes(x)
    R = {}
    # 1. TOOT by COVER vs DUMP; NAHI + WRITE vs BUY (30-min continuation with the push, by count)
    pv = pushes_vs_flow(x)
    def grp(ans, who):
        rows = [r for r in pv if r[2] == ans and r[3] == who and r[5] is not None]
        withp = sum(1 for r in rows if r[1] * r[5] > 0)
        return f"{len(rows)} rows · {withp} went with the push at +30 · " + ", ".join(f"{r[0]} {'▲' if r[1] > 0 else '▼'} {f(r[5])}" for r in rows)
    R["TOOT+COVER"] = grp("TOOT", "COVER")
    R["TOOT+DUMP"] = grp("TOOT", "DUMP")
    R["NAHI+WRITE"] = grp("NAHI", "WRITE")
    R["NAHI+BUY"] = grp("NAHI", "BUY")
    R["pushes total"] = f"{len(pv)}; all (ans, who): " + ", ".join(f"{r[0]} {r[2]}+{r[3]}" for r in pv)
    # 2. fade alerts (SETUP lines, both indices, NIFTY's flow for both as §1q) with cap/floor WRITE at the last close <= alert
    M = _load.messages(day)
    rows = []
    seen = set()
    for r in M:
        if r["kind"] != "SETUP" or r["idx"] not in ("NIFTY", "SENSEX"):
            continue
        side = "SELL" if "SELL" in r["line"] else "BUY" if "BUY" in r["line"] else None
        if not side:
            continue
        key = (r["idx"], r["t"], side)
        if key in seen:
            continue
        seen.add(key)
        xx = days[day][r["idx"]]
        m = m_of(r["t"])
        if m not in xx["mins"]:
            continue
        i = xx["mins"].index(m)
        c = max((j for j in closes(xx) if j <= i), default=None)
        if c is None:
            continue
        g = xx["cap"][c] if side == "SELL" else xx["floor"][c]
        w = g["w"] if g else "?"
        f30 = fut_at(xx, i, 30)
        good = (f30 is not None) and ((f30 < 0) if side == "SELL" else (f30 > 0))
        rows.append((r["idx"], r["t"], side, w, f30, good))
    with_w = [r for r in rows if r[3] == "WRITE"]
    without = [r for r in rows if r[3] not in ("WRITE", "?")]
    R["fade alerts, wall WRITE at the alert"] = f"{len(with_w)} rows · {sum(1 for r in with_w if r[5])} went the fade's way at +30 · " + ", ".join(f"{r[0][:2]} {r[1]} {r[2]} {f(r[4])}" for r in with_w)
    R["fade alerts, wall not WRITE"] = f"{len(without)} rows · {sum(1 for r in without if r[5])} went the fade's way at +30 · " + ", ".join(f"{r[0][:2]} {r[1]} {r[2]} ({r[3]}) {f(r[4])}" for r in without)
    # 3. first-hour candidate: Jarvis's own leg row says TREND quality before 10:00 ('fuelled hh:mm' with hh:mm < 10:00)
    J = [r for r in _load.jarvis(day) if r["idx"] == "NIFTY"]
    cand = next((r for r in J if r["t"] < "10:00" and "fuelled" in (r.get("leg") or "")), None)
    if cand:
        i = x["mins"].index(m_of(cand["t"]))
        c = max(j for j in closes(x) if j <= i)
        pal = next((r for r in J if r["t"] > cand["t"] and r["word"].startswith("PALAT ")), None)
        end_i = x["mins"].index(m_of(pal["t"])) if pal else x["mins"].index(15 * 60 + 20)
        R["first-hour candidate"] = (f"leg qualified {cand['t']} ({(cand.get('leg') or '')[:40]}), count W{cand['count']['with']} A{cand['count']['against']}, "
                                     f"flow at the {hm(x['mins'][c])} close: {x['raw'][c]} (held {x['word'][c]}); fut {x['fut'][i]:.0f} → "
                                     f"{'PALAT ' + pal['t'] if pal else '15:20'} {x['fut'][end_i]:.0f} ({x['fut'][end_i] - x['fut'][i]:+.0f}); +30 {f(fut_at(x, i, 30))}")
    else:
        R["first-hour candidate"] = "no leg qualified before 10:00"
    # 4. PIN closes (both WRITE), with time
    pins = [hm(x["mins"][i]) for i in C if x["raw"][i] == "PIN"]
    R["PIN closes"] = f"{len(pins)} · " + ", ".join(pins)
    # 5. FLOOR / CAP COVER >= 10L at a close -> next close same side, fut +3 / +15
    for side in ("floor", "cap"):
        rr = []
        for n, i in enumerate(C):
            g = x[side][i]
            if g and g["w"] == "COVER" and g["doi"] <= -10e5:
                nx = x[side][C[n + 1]] if n + 1 < len(C) else None
                rr.append(f"{hm(x['mins'][i])} {g['doi'] / 1e5:+.0f}L → next {nx['w'] if nx else '?'} · +3 {f(fut_at(x, i, 3))} · +15 {f(fut_at(x, i, 15))}")
        R[f"{side.upper()} COVER ≥ 10L"] = f"{len(rr)} · " + "; ".join(rr)
    # 6. flow lean vs Jarvis lean at closes; lean sign flips
    agree = {}
    flips, prev = 0, None
    jl_by_min = {}
    for r in J:
        jl_by_min[m_of(r["t"])] = r["lean"]
    for i in C:
        fl = x["lean"][i]
        jl = x["jarvis"][i]["lean"] if x["jarvis"][i] else None
        agree[(fl, jl)] = agree.get((fl, jl), 0) + 1
        if prev is not None and fl and prev and fl != prev:
            flips += 1
        if fl:
            prev = fl
    jflips = sum(1 for a, b in zip(J, J[1:]) if a["lean"] and b["lean"] and a["lean"] != b["lean"])
    R["flow lean vs Jarvis lean (closes)"] = f"same ▲ {agree.get((1, 1), 0)} · same ▼ {agree.get((-1, -1), 0)} · flow ▲ vs J ▼ {agree.get((1, -1), 0)} · flow ▼ vs J ▲ {agree.get((-1, 1), 0)} · flow flat {sum(v for k, v in agree.items() if k[0] == 0)} · flow flips {flips} · Jarvis flips {jflips}"
    # 7. FIRM share at closes ATM+-3, and the held-word change count
    firm = tot = 0
    for i in C:
        if not x["firm"][i] or x["firm"][i][0] is None or x["spot"][i] is None:
            continue
        atm = round(x["spot"][i] / x["step"]) * x["step"]
        for q, k in enumerate(x["strikes"]):
            if abs(k[0] - atm) > 3 * x["step"] or x["who"][i][q] in ("Q", "?", "F", None):
                continue
            tot += 1
            firm += x["firm"][i][q]
    R["FIRM share (ATM±3, non-QUIET labels at closes)"] = f"{firm} of {tot}"
    R["held-word changes / lean flips"] = f"{sum(1 for a, b in zip(x['word'], x['word'][1:]) if a != b)} / {flips}"
    # 8. OI cadence from the chain
    rows = []
    for l in open(os.path.join(D, "chain", f"chain_NIFTY_{day}.jsonl"), encoding="utf-8"):
        if l.strip():
            try:
                rows.append(json.loads(l))
            except ValueError:
                pass
    import statistics as st
    secs = [r["sec"] for r in rows]
    gaps = [b - a for a, b in zip(secs, secs[1:])]
    atm = round(rows[len(rows) // 2]["spot"] / 50) * 50
    ser = [(r["sec"], s["ce"]["oi"]) for r in rows for s in r["strikes"] if s["k"] == atm and s.get("ce")]
    ch = [t2 for (t1, v1), (t2, v2) in zip(ser, ser[1:]) if v2 != v1]
    g2 = [b - a for a, b in zip(ch, ch[1:])]
    R["OI cadence"] = f"chain poll median {st.median(gaps):.0f} s · {atm} CE OI changes every {st.median(g2):.0f} s (median), p90 {sorted(g2)[int(.9 * len(g2))]} s, {len(ch)} changes in {len(ser)} snapshots"
    return R


if __name__ == "__main__":
    days = [a for a in sys.argv[1:] if a.startswith("2026")] or ["2026-11-02", "2026-11-03"]
    res = {d: study(d) for d in days}
    keys = list(res[days[0]].keys())
    for k in keys:
        print("=", k)
        for d in days:
            print(f"   {d}: {res[d].get(k)}")
