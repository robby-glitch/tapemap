"""Round 4: pullback anatomy, the signal x option-flow matrix, the option-implied delta vs the futures' delta, and the
writer-gamma profile. NIFTY, 2 and 3 Nov, her 3-min grid, causal at every close; "+15 / +30" are hindsight and say so.
Counts only. Run from tapemap/:  python -I -X utf8 docs/optflow/fable/round4.py [2026-11-02] [2026-11-03]
Reuses docs/optflow/brainstorm/strike_bands.py (A218) for the premium / index VWAP bands (contract_bars._Vwap)."""
import json, os, sys, statistics as st
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
TM = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(TM, "docs", "optflow", "brainstorm"))
from load import hm, m_of, D, IST
import load as _load
import strike_bands as SB

LOT = 75
DAYS = json.load(open(os.path.join(HERE, "days.json"), encoding="utf-8"))


def closes(x):
    return [i for i, m in enumerate(x["mins"]) if (m - 555) % 3 == 2]


def last_close(x, m):
    return max((i for i, mm in enumerate(x["mins"]) if mm <= m and (mm - 555) % 3 == 2), default=None)


def fut_after(x, i, k):
    j = i + k
    return (x["fut"][j] - x["fut"][i]) if j < len(x["fut"]) and x["fut"][i] is not None and x["fut"][j] is not None else None


def f(v, d=0):
    return "?" if v is None else f"{v:+.{d}f}"


def chain_greeks(day):
    """{minute: {(k, 'CE'|'PE'): (delta, gamma)}} from the chain's last snapshot in the minute, forward-filled."""
    out, cur = {}, {}
    for l in open(os.path.join(D, "chain", f"chain_NIFTY_{day}.jsonl"), encoding="utf-8"):
        if not l.strip():
            continue
        try:
            r = json.loads(l)
        except ValueError:
            continue
        for s in r["strikes"]:
            for sd in ("ce", "pe"):
                q = s.get(sd)
                if q and q.get("delta") is not None:
                    cur[(s["k"], sd.upper())] = (q["delta"], q.get("gamma"))
        out[r["sec"] // 60] = dict(cur)
    ff, last = {}, {}
    for m in range(555, 931):
        if m in out:
            last = out[m]
        ff[m] = last
    return ff


def fut_footprint(day):
    rows = {}
    p = os.path.join(D, "dext", f"dext_NSE-61471_{day}.jsonl")
    for l in open(p, encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            rows[(r["t"] + IST) % 86400 // 60] = r
    return rows


def implied_delta(day, x):
    """Per minute: sum over strikes of (lifted - hit) x the chain's delta, in futures-lot equivalents; and the futures'
    own Dext delta in lots. Causal: minute m uses minute m's closed footprint and the chain delta known at m."""
    gk = chain_greeks(day)
    dx = _load.dext(day)["NIFTY"]
    ff = fut_footprint(day)
    imp, fut = {}, {}
    for m in x["mins"]:
        s = 0.0
        g = gk.get(m, {})
        for k, rows in dx.items():
            r = rows.get(m)
            d = g.get(k)
            if r and d:
                s += r["delta"] * d[0]
        imp[m] = s / LOT
        fut[m] = (ff[m]["delta"] / LOT) if m in ff else None
    return imp, fut


# ------------------------------------------------------------------------------------------------ A. pullbacks
def pullbacks(day, x):
    """2 Nov: Jarvis's pause log. 3 Nov: runs of the leg's state HOLD / WATCH / PALAT? after a TREND state in the call log
    (the same rule legs.py logs; no pause file exists for 3 Nov)."""
    out = []
    p = os.path.join(D, "jarvis", f"pause_{day}.jsonl")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            r = json.loads(l)
            g = r["leg"]
            out.append({"t": r["t"], "dir": g["dir"], "origin": g["origin"], "ext": g["extreme"], "pts": g["pts"], "src": "pause log",
                        "word": r["word"], "jarvis_outcome": (r.get("after") or {}).get("outcome")})
    else:
        J = [r for r in _load.jarvis(day) if r["idx"] == "NIFTY"]
        prev, run = None, None
        for r in J:
            stt = r.get("state")
            if stt in ("HOLD", "WATCH", "PALAT?") and prev == "TREND":
                import re
                g = r.get("leg") or ""
                m1 = re.search(r"origin ([\d,]+)f", g); m2 = re.search(r"extreme ([\d,]+)f", g); m3 = re.search(r"(\d+) pts", g)
                run = {"t": r["t"], "dir": r["lean"], "origin": float(m1.group(1).replace(",", "")) if m1 else None,
                       "ext": float(m2.group(1).replace(",", "")) if m2 else None, "pts": int(m3.group(1)) if m3 else None,
                       "src": "call log state", "word": stt, "jarvis_outcome": None}
                out.append(run)
            if stt not in ("HOLD", "WATCH", "PALAT?") or prev != "TREND":
                pass
            prev = stt if stt in ("TREND", "HOLD", "WATCH", "PALAT?", "PALAT") else prev
    # depth, duration, outcome from the futures path (1-min closes), the leg's lean flip from the call log
    J = [r for r in _load.jarvis(day) if r["idx"] == "NIFTY"]
    flips = [m_of(r["t"]) for a, r in zip(J, J[1:]) if a["lean"] and r["lean"] and a["lean"] != r["lean"]]
    res = []
    for pb in out:
        i0 = x["mins"].index(m_of(pb["t"]))
        d = pb["dir"]
        ext = pb["ext"] if pb["ext"] else x["fut"][i0]
        deep, end, outcome = x["fut"][i0], None, "UNRESOLVED"
        for j in range(i0, min(i0 + 60, len(x["mins"]))):
            v = x["fut"][j]
            if v is None:
                continue
            deep = min(deep, v) if d > 0 else max(deep, v)
            if (v > ext if d > 0 else v < ext):
                end, outcome = j, "CONT"
                break
            if any(m_of(pb["t"]) < fl <= x["mins"][j] for fl in flips):
                end, outcome = j, "FAIL (PALAT)"
                break
        end = end if end is not None else min(i0 + 60, len(x["mins"]) - 1)
        depth = (ext - deep) if d > 0 else (deep - ext)
        pb.update({"depth": depth, "share": depth / pb["pts"] if pb["pts"] else None, "dur": x["mins"][end] - x["mins"][i0], "outcome": outcome,
                   "i0": i0, "i1": end})
        res.append(pb)
    return res


def pb_flow(day, x, pb, B, fb):
    """What the option flow did at the closes inside the pullback: the defending floor (up-leg) / cap (down-leg), the
    attacked side, the ITM writers, option buyers lifting; the ATM premium's band position (the leg's own option)."""
    d = pb["dir"]
    C = [i for i in closes(x) if pb["i0"] <= i <= pb["i1"]]
    if not C:
        C = [last_close(x, x["mins"][pb["i0"]])]
    defend = "floor" if d > 0 else "cap"
    attack = "cap" if d > 0 else "floor"
    dw = Counter(x[defend][i]["w"] for i in C if x[defend][i])
    aw = Counter(x[attack][i]["w"] for i in C if x[attack][i])
    # ITM writers of the leg's direction: for an up-leg the ITM CE (below spot), for a down-leg the ITM PE
    itm = Counter()
    for i in C:
        sp = x["spot"][i]
        if sp is None or not x["who"][i]:
            continue
        for q, k in enumerate(x["strikes"]):
            if (d > 0 and k[1] == "CE" and k[0] < sp) or (d < 0 and k[1] == "PE" and k[0] > sp):
                w = x["who"][i][q]
                if w in ("W", "B", "C", "D"):
                    itm[w] += 1
    # option buyers lifting on the attacked side's option (puts in an up-leg): the defending group's BUY
    buyers = dw.get("BUY", 0)
    # the ATM option of the leg's direction: its premium band position at each close
    prem = Counter()
    for i in C:
        sp = x["spot"][i]
        if sp is None:
            continue
        k = round(sp / 50) * 50
        sd = "ce" if d > 0 else "pe"
        bl = B.get((k, sd)) or []
        b = next((bb for bb in bl if bb["e"] == x["mins"][i]), None)
        if b:
            prem[SB.pos(b)] += 1
    ib = Counter(SB.pos(fb.get(x["mins"][i])) for i in C)
    return {"defend": defend, "dw": dict(dw), "attack": attack, "aw": dict(aw), "itm": dict(itm), "buyers": buyers, "prem": dict(prem),
            "index": dict(ib), "n": len(C), "words": [x["raw"][i] for i in C]}


# ------------------------------------------------------------------------------------------------ B. the matrix
def band_rows(day):
    rows = []
    for l in open(os.path.join(D, "trigger_log.jsonl"), encoding="utf-8"):
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("day") == day and r.get("index") == "NIFTY" and r.get("rule") == "zone3" and r.get("kind") in ("arm", "trigger", "entry"):
            rows.append(r)
    return rows


def speed_at(x, i):
    """fut points per minute over the last 3 min, and the defending side's dOI deceleration (this close vs the previous)."""
    f3 = fut_after(x, i - 3, 3) if i >= 3 else None
    return (f3 / 3) if f3 is not None else None


def effort_at(x, ffp, i):
    """lots per point over the last 3 min (Dext futures footprint volume / the 3-min range), against the day's median so far."""
    ms = [x["mins"][j] for j in range(max(0, i - 2), i + 1)]
    v = sum(ffp[m]["total_volume"] for m in ms if m in ffp) / LOT
    hi = max((ffp[m]["high"] for m in ms if m in ffp), default=None); lo = min((ffp[m]["low"] for m in ms if m in ffp), default=None)
    if hi is None or hi == lo:
        return None
    return v / (hi - lo)


def vpin_at(day, m):
    best = None
    for l in open(os.path.join(D, "vpin_fast.jsonl"), encoding="utf-8"):
        if day not in l:
            continue
        r = json.loads(l)
        if r.get("day") == day and m_of(r["at"]) <= m:
            best = r
    return best


def main(day):
    _load.CUR["day"] = day
    x = DAYS[day]["NIFTY"]
    exp, spot, B, fb = SB.bars3(day)
    ffp = fut_footprint(day)
    imp, fut = implied_delta(day, x)
    print(f"\n################ {day}")
    # ---------------- A
    print("\n== A. pullbacks (source: %s)" % ("pause log" if os.path.exists(os.path.join(D, "jarvis", f"pause_{day}.jsonl")) else "call-log states"))
    pbs = pullbacks(day, x)
    effs = []
    for pb in pbs:
        fl = pb_flow(day, x, pb, B, fb)
        i = last_close(x, x["mins"][pb["i0"]])
        e = effort_at(x, ffp, i)
        sp = speed_at(x, i)
        vp = vpin_at(day, x["mins"][i])
        d9 = sum(fut.get(x["mins"][j]) or 0 for j in range(max(0, i - 8), i + 1))
        o9 = sum(imp.get(x["mins"][j]) or 0 for j in range(max(0, i - 8), i + 1))
        print(f"{pb['t']} {'▲' if pb['dir'] > 0 else '▼'} leg {pb['pts']} pts · depth {pb['depth']:.0f} ({(pb['share'] or 0):.2f} of the leg) · {pb['dur']} min · {pb['outcome']}"
              f" (Jarvis {pb['jarvis_outcome']}) · closes {fl['n']}: words {fl['words']}")
        print(f"      {fl['defend']} {fl['dw']} · {fl['attack']} {fl['aw']} · ITM writers {fl['itm']} · buyers on the {fl['defend']} {fl['buyers']}"
              f" · ATM premium {fl['prem']} · index band {fl['index']}")
        print(f"      at the first close: speed {f(sp, 1)} pts/min · effort {f(e, 0)} lots/pt · VPIN {vp['vpin'] if vp else '?'} (p{vp['pct'] if vp else '?'})"
              f" · fut delta 9 min {f(d9)} lots · option-implied 9 min {f(o9)} lots")
    # ---------------- B1 band rotation (trigger_log zone3) with flow / band position
    print("\n== B1. band rotation rows (trigger_log zone3, NIFTY): flow at the last close <= t, index band, premium band; mfe / mae as logged")
    rows = band_rows(day)
    agg = defaultdict(list)
    for r in rows:
        m = m_of(r["t"]); i = last_close(x, m)
        if i is None:
            continue
        side = r["side"]
        g = x["cap"][i] if side == "SELL" else x["floor"][i]
        w = g["w"] if g else "?"
        ib = SB.pos(fb.get(x["mins"][i]))
        sp = x["spot"][i]
        k = round(sp / 50) * 50 if sp else None
        b = next((bb for bb in (B.get((k, "ce" if side == "SELL" else "pe")) or []) if bb["e"] == x["mins"][i]), None)
        pbp = SB.pos(b) if b else "?"
        legal = (r.get("gate") or {}).get("legal")
        agg[(side, r["kind"], w)].append((r["t"], legal, ib, pbp, r.get("mfe"), r.get("mae")))
    for key in sorted(agg):
        v = agg[key]
        stopped = sum(1 for z in v if z[5] is not None and z[5] <= -30)
        ran = sum(1 for z in v if z[4] is not None and z[4] >= 40)
        print(f"  {key[0]} {key[1]:7} wall {key[2]:6}: {len(v)} rows · mfe≥40 {ran} · mae≤−30 {stopped} · " + ", ".join(f"{z[0]} {'L' if z[1] else 'I'} idx{z[2]} prem{z[3]} {f(z[4])}/{f(z[5])}" for z in v[:8]))
    # ---------------- B3 handshake with answer speed
    print("\n== B3. pushes: answer speed (am − t), who, +30")
    for p in x["pushes"]:
        am = m_of(p["am"]) if p["am"] else m_of(p["t"]) + 2
        j = x["mins"].index(am) if am in x["mins"] else None
        q = [n for n, k in enumerate(x["strikes"]) if k[0] == p["k"] and k[1] == p["side"]]
        who = {"W": "WRITE", "B": "BUY", "C": "COVER", "D": "DUMP", "M": "MIXED", "Q": "QUIET", "?": "OI?", "F": "FLOW?"}.get(x["who"][j][q[0]], "?") if (j is not None and q) else "?"
        print(f"  {p['t']} {'▲' if p['dir'] > 0 else '▼'} {p['lots']:>5} lots · answer in {am - m_of(p['t'])} min: {p['ans']} · flow {who} · +30 {f(p['p30'])}")
    # ---------------- B6 sides x flow word x f15
    print("\n== B6. Sides slot word × flow group word at the same close × f15 (sides' own outcome rows)")
    srows = [json.loads(l) for l in open(os.path.join(D, "sides", f"sides_{day}.jsonl"), encoding="utf-8") if l.strip()]
    oc = {r["t"]: r for r in srows if r.get("kind") == "outcome" and r["idx"] == "NIFTY"}
    cnt = defaultdict(lambda: [0, 0, 0])
    for r in srows:
        if r.get("kind") == "outcome" or r["idx"] != "NIFTY" or not r.get("word"):
            continue
        i = last_close(x, m_of(r["t"]))
        if i is None:
            continue
        o = oc.get(r["t"])
        if not o or o.get("f15") is None:
            continue
        key = (r["word"], x["word"][i])
        c = cnt[key]; c[0] += 1; c[1] += o["f15"] > 0; c[2] += o["f15"] < 0
    for key in sorted(cnt, key=lambda k: -cnt[k][0])[:14]:
        c = cnt[key]; print(f"  Sides {key[0]:9} + flow {key[1]:14}: {c[0]} slots · f15 up {c[1]} · down {c[2]}")
    # ---------------- C option-implied delta vs futures delta
    print("\n== C. option-implied directional flow (Σ (lifted−hit) × chain delta, in fut-lot equivalents) vs the futures' Dext delta")
    C = closes(x)
    s9 = lambda ser, i: sum(ser.get(x["mins"][j]) or 0 for j in range(max(0, i - 8), i + 1))
    I9 = {i: s9(imp, i) for i in C}; F9 = {i: s9(fut, i) for i in C}
    tot_i = sum(abs(v) for v in imp.values() if v); tot_f = sum(abs(v) for v in fut.values() if v)
    print(f"  size: Σ|implied| {tot_i:,.0f} lots · Σ|fut delta| {tot_f:,.0f} lots over the day")
    agree = sum(1 for i in C if I9[i] * F9[i] > 0); dis = sum(1 for i in C if I9[i] * F9[i] < 0)
    print(f"  9-min sums at closes: same sign {agree} · opposite {dis}")
    # lead: correlation of the 3-min sums at lags (closes)
    s3 = lambda ser, i: sum(ser.get(x["mins"][j]) or 0 for j in range(max(0, i - 2), i + 1))
    I3 = [s3(imp, i) for i in C]; F3 = [s3(fut, i) for i in C]
    def corr(a, b):
        n = len(a); ma, mb = sum(a) / n, sum(b) / n
        sa = sum((u - ma) ** 2 for u in a) ** .5; sb = sum((u - mb) ** 2 for u in b) ** .5
        return sum((u - ma) * (v - mb) for u, v in zip(a, b)) / (sa * sb) if sa and sb else 0
    lags = {}
    for L in (-2, -1, 0, 1, 2):
        a = I3[max(0, L):len(I3) + min(0, L)]; b = F3[max(0, -L):len(F3) + min(0, -L)]
        lags[L] = corr(a, b)
    print("  corr(implied_3min at close c, fut_3min at close c+L): " + ", ".join(f"L={L:+d} {v:+.2f}" for L, v in lags.items()) + "  (L>0: options first)")
    # divergence: opposite 9-min signs -> fut +15, by the implied sign
    dv = defaultdict(lambda: [0, 0, 0])
    for i in C:
        if I9[i] * F9[i] < 0 and abs(I9[i]) >= 200 and abs(F9[i]) >= 200:
            k = "implied ▲ / fut ▼" if I9[i] > 0 else "implied ▼ / fut ▲"
            a = fut_after(x, i, 15); c = dv[k]; c[0] += 1
            if a is not None: c[1] += a > 0; c[2] += a < 0
    for k, c in dv.items():
        print(f"  divergence {k} (both ≥ 200 lots in 9 min): {c[0]} closes · fut +15 up {c[1]} · down {c[2]}")
    # at the leg turns: which 9-min sum crossed zero first
    J = [r for r in _load.jarvis(day) if r["idx"] == "NIFTY"]
    flips = [(r["t"], r["lean"]) for a, r in zip(J, J[1:]) if a["lean"] and r["lean"] and a["lean"] != r["lean"]]
    for t, ln in flips:
        i = last_close(x, m_of(t))
        ci = next((j for j in reversed([c for c in C if c <= i]) if I9[j] * ln <= 0), None)
        cf = next((j for j in reversed([c for c in C if c <= i]) if F9[j] * ln <= 0), None)
        fi = next((j for j in C if j <= i and all(I9[k] * ln > 0 for k in C if j <= k <= i)), None)
        ff_ = next((j for j in C if j <= i and all(F9[k] * ln > 0 for k in C if j <= k <= i)), None)
        print(f"  lean flip {t} {'▲' if ln > 0 else '▼'}: implied 9-min turned {'▲' if ln > 0 else '▼'} and stayed from {hm(x['mins'][fi]) if fi is not None else '?'} · fut delta from {hm(x['mins'][ff_]) if ff_ is not None else '?'}")
    # ---------------- D writer gamma
    print("\n== D. writer short-gamma profile: Σ_today dOI in WRITE windows − in BUY windows, × the chain's gamma (writers short where positive)")
    gk = chain_greeks(day)
    W = defaultdict(float)
    marks = {"2026-11-02": (12 * 60 + 47, 13 * 60 + 17, 14 * 60 + 29), "2026-11-03": (12 * 60 + 59, 13 * 60 + 29, 14 * 60 + 23)}[day]
    for i in C:
        for q, k in enumerate(x["strikes"]):
            k = tuple(k)
            w, doi = x["who"][i][q] if x["who"][i] else None, x["doi"][i][q] if x["doi"][i] else None
            if doi is None:
                continue
            if w == "W":
                W[k] += doi
            elif w == "B":
                W[k] -= doi
        if x["mins"][i] in marks:
            g = gk.get(x["mins"][i], {})
            prof = sorted(((k, W[k] * (g.get(k) or (0, 0))[1] if (g.get(k) or (0, None))[1] else 0) for k in W), key=lambda z: -abs(z[1]))[:4]
            print(f"  {hm(x['mins'][i])} spot {x['spot'][i]:.0f} fut {x['fut'][i]:.0f}: " + ", ".join(f"{k[0]} {k[1]} {v / 1e3:+.0f}k" for k, v in prof) + "  (gamma × qty; + = writers short gamma there)")


if __name__ == "__main__":
    for day in [a for a in sys.argv[1:] if a.startswith("2026")] or ("2026-11-02", "2026-11-03"):
        main(day)
