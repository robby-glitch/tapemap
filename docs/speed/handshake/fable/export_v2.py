"""export_v2.py -- the HANDSHAKE v2 data: per minute NIFTY spot, the RAFTAAR picture (engine, lockstep), the strike OI, the
flow from the near-month Dext (last row per minute) with the 1-second book as the fallback, GoCharting + Upstox 5-min bars,
and the pushes with their answers: the attacked strike by ABSOLUTE OI, who opened the OI behind (premium vs delta), the
futures OI leg, effort per point, and what the 5-min bars said. Causal: a PUSH exists at its minute; its ANSWER and the
sources' 5-min verdict only at +4. Read-only on data/. Rows, not rates.

    python export_v2.py            -> data_v2.js + RAFTAAR-handshake-v2.html (self-contained)
"""
import glob
import gzip
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.normpath(os.path.join(HERE, "..", "..", "final")), os.path.normpath(os.path.join(HERE, "..", "..", "live")),
                os.path.normpath(os.path.join(HERE, "..", "..", "coil"))]
import coil_scan as C          # noqa: E402
from export import lockstep    # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "data"))
LOT = 65
DAYS = [("2026-10-26", "trend ▲ · 09:52 wall break"), ("2026-10-22", "chop · her stop-loss day"), ("2026-10-23", "▼ then +204"),
        ("2026-10-27", "Oct expiry · Dext blank pm (book)"), ("2026-10-21", "top 09:58 → −470"), ("2026-10-08", "clean trend ▼"),
        ("2026-10-06", "expiry grind · pin"), ("2026-09-29", "Sep expiry · round trip")]
NORM, PUSH_X, MIN_PUSH, ANSWER, QUIET = 30, 2.0, 150, 4, 4       # [I] as the mockup
CUT_L, CUT_FRAC, PRINT_X = 3.0, 0.04, 10                          # [I] the answer bar is 4 % of the strike's ABSOLUTE OI (min 3L)
TICK = 0.05


def near(day):
    return "NSE-2885" if day <= "2026-09-30" else "NSE-48704"


def dext(day):
    """{minute: lots} from the near-month contract, the LAST row per minute (rows are re-written as the bar fills)."""
    p = os.path.join(DATA, "dext", f"dext_{near(day)}_{day}.jsonl")
    last = {}
    for line in open(p, encoding="utf-8") if os.path.exists(p) else ():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        m = int(r["time"][11:13]) * 60 + int(r["time"][14:16])
        if m not in last or (r.get("total_volume") or 0) >= (last[m].get("total_volume") or 0):
            last[m] = r
    return {m: round(r["delta"] / LOT) for m, r in last.items() if r.get("total_volume")}


def book(day):
    """{minute: [delta lots, vol lots, high, low, fut oi]} from the 1-second book by the quote rule (the Dext fallback)."""
    p = os.path.join(DATA, "book", f"book_NIFTY_{day}.jsonl")
    f = open(p, encoding="utf-8") if os.path.exists(p) else gzip.open(p + ".gz", "rt", encoding="utf-8") if os.path.exists(p + ".gz") else None
    if f is None:
        return {}
    out, prev = {}, None
    with f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("ltp") is None or not r.get("b") or not r.get("a") or not isinstance(r.get("t"), (int, float)):
                continue
            m = int(r["t"] / 1000 + 19800) % 86400 // 60
            c = out.setdefault(m, [0.0, 0.0, r["ltp"], r["ltp"], None])
            c[2], c[3], c[4] = max(c[2], r["ltp"]), min(c[3], r["ltp"]), r.get("oi") or c[4]
            if prev is not None:
                v = (r.get("vtt") or 0) - (prev.get("vtt") or 0)
                if v > 0:
                    bid, ask = prev["b"][0][0], prev["a"][0][0]
                    sgn = 1 if r["ltp"] >= ask else -1 if r["ltp"] <= bid else (1 if r["ltp"] > prev["ltp"] else -1 if r["ltp"] < prev["ltp"] else 0)
                    c[0] += sgn * v / LOT
                    c[1] += v / LOT
            prev = r
    return {m: [round(v[0]), round(v[1]), v[2], v[3], v[4]] for m, v in out.items()}


def bars5(path):
    out = []
    for line in open(path, encoding="utf-8") if os.path.exists(path) else ():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        m = int((r["t"] / 1000 + 19800) % 86400 // 60)
        if 555 <= m <= 930 and r.get("delta") is not None:
            out.append([m, round(r["delta"]), None if r.get("oi") is None else int(r["oi"])])
    return out


def leg(r, k, side):
    return C.leg_of(r, k, side)


def who(r0, r4, k, side, s0, s4):
    """Who opened the OI added at k between r0 and r4: the premium move minus what delta explains.
    > +2 ticks: buyers paying up (IV up) · < -2 ticks: writers selling into it · else unclear."""
    a, b = leg(r0, k, side), leg(r4, k, side)
    if a.get("ltp") is None or b.get("ltp") is None or a.get("delta") is None:
        return None
    expl = a["delta"] * (s4 - s0)
    x = (b["ltp"] - a["ltp"]) - expl
    return ["KHAREEDAR" if x > 2 * TICK else "WRITERS" if x < -2 * TICK else "?", round(x, 2)]


def day_data(day, label):
    R = C.minutes(day)
    ms = sorted(m for m in R if 555 <= m <= 930)
    sp = {m: R[m]["spot"] for m in ms}
    ks = sorted({s["k"] for s in R[ms[-1]]["strikes"]})
    step = min(b - a for a, b in zip(ks, ks[1:]))
    lo, hi = min(sp.values()) - 3 * step, max(sp.values()) + 3 * step
    keep = [k for k in ks if lo <= k <= hi]
    D, B = dext(day), book(day)
    G = bars5(os.path.join(DATA, "tape", f"tape_NIFTY_{day}.jsonl"))
    U = bars5(os.path.join(DATA, "tape", f"ux_NIFTY_{day}.jsonl"))
    # the flow used per minute: Dext, else the book (tagged), else None
    F, src = {}, {}
    for m in ms:
        if m in D:
            F[m], src[m] = D[m], "D"
        elif m in B and B[m][1] > 0:
            F[m], src[m] = B[m][0], "B"
    outs, _, _ = lockstep(day)
    pic = {}
    for t, o in outs["NIFTY"]:
        p = o.get("picture") or {}
        g = p.get("grade") or {}
        pic[int(t[:2]) * 60 + int(t[3:])] = [p.get("word"), p.get("dir"), g.get("n"), g.get("N"), p.get("story"), g.get("word")]
    # effort per point (effort.py's rule on the flow used): lots per point over 5 min vs the day's median of 5-min blocks so far
    eff, blocks = {}, []
    for m in ms:
        w = [j for j in range(m - 4, m + 1) if j in F and j in B]
        if len(w) == 5:
            vol = sum(B[j][1] for j in w)
            rng = max(B[j][2] for j in w) - min(B[j][3] for j in w)
            if rng > 0:
                lam = vol / rng
                if (m - 555) % 5 == 4:
                    blocks.append(lam)
                med = st.median(blocks[:-1]) if len(blocks) > 6 else None
                eff[m] = [round(lam), None if med is None else round(lam / med, 1)]
    futoi = {m: B[m][4] for m in ms if m in B and B[m][4]}

    def d2(m):
        a, b = F.get(m - 1), F.get(m)
        return None if a is None or b is None else a + b

    events, last = [], {1: -99, -1: -99}
    for m in ms:
        x = d2(m)
        hist = [abs(d2(j)) for j in range(m - NORM, m) if d2(j) is not None]
        if x is None or len(hist) < 10:
            continue
        norm = st.median(hist)
        sgn = 1 if x > 0 else -1
        if abs(x) < max(MIN_PUSH, PUSH_X * norm) or m - last[sgn] < QUIET:
            continue
        last[sgn] = m
        r0, s0 = R[m], sp[m]
        side = "ce" if sgn > 0 else "pe"
        band = [k for k in keep if (s0 - step / 2 <= k <= s0 + 2 * step if sgn > 0 else s0 - 2 * step <= k <= s0 + step / 2)]
        att = max(band, key=lambda k: leg(r0, k, side).get("oi") or 0) if band else None
        ev = {"m": m, "dir": sgn, "lots": x, "norm": round(norm), "spot": s0, "k": att, "side": side.upper(), "src": src.get(m),
              "print": abs(x) >= PRINT_X * norm}
        m4 = next((j for j in ms if j >= m + ANSWER), None)
        if att is not None and m4 is not None:
            o0, o4 = leg(r0, att, side).get("oi_chg"), leg(R[m4], att, side).get("oi_chg")
            base = leg(r0, att, side).get("oi")
            moved = sgn * (sp[m4] - s0)
            if None not in (o0, o4, base):
                chg = (o4 - o0) / 1e5
                bar = max(CUT_L, CUT_FRAC * max(base, 0) / 1e5)
                through = moved >= 0.3 * step
                ev.update(chg=round(chg, 1), bar=round(bar, 1), oi_k=round(base / 1e5, 1), am=m4, moved=round(moved),
                          ans="TOOT" if chg <= -bar else "PHANS" if chg >= bar and through else "TIKI" if chg >= bar else "NAHI")
                if ev["ans"] in ("PHANS", "TIKI"):
                    ev["who"] = who(r0, R[m4], att, side, s0, sp[m4])
                # behind price at the answer: the other side's biggest add within 2 steps behind price, and who opened it
                s4, other = sp[m4], ("pe" if sgn > 0 else "ce")
                zone = [k for k in keep if (s4 - 2 * step <= k <= s4 if sgn > 0 else s4 <= k <= s4 + 2 * step)]
                adds = [(k, ((leg(R[m4], k, other).get("oi_chg") or 0) - (leg(r0, k, other).get("oi_chg") or 0)) / 1e5) for k in zone]
                best = max(adds, key=lambda a: a[1]) if adds else None
                if best and best[1] >= CUT_L:
                    ev["behind"] = [best[0], round(best[1], 1), who(r0, R[m4], best[0], other, s0, s4)]
                # the futures leg over the same 4 min: fut OI with price = fresh positions, against = covering (oi-lab's surviving read)
                f0, f4 = futoi.get(m), futoi.get(m4)
                if f0 and f4:
                    d_oi = (f4 - f0) / LOT
                    ev["fut"] = [round(d_oi), "FRESH" if d_oi * sgn > 0 and abs(d_oi) >= 500 else "COVER" if d_oi * sgn < 0 and abs(d_oi) >= 500 else "FLAT"]
                if m4 in eff:
                    ev["eff"] = eff[m4]
                # the three sources on the 5-min bar holding the push, known once that bar has closed (<= m4)
                slot = m - ((m - 555) % 5)
                if slot + 5 <= m4 + 1:
                    dv = sum(F[j] for j in range(slot, slot + 5)) if all(j in F for j in range(slot, slot + 5)) else None
                    gv = next((b[1] for b in G if b[0] == slot), None)
                    uv = next((b[1] for b in U if b[0] == slot), None)
                    ev["srcs"] = [dv, gv, uv]
                    ev["agree"] = sum(1 for v in (dv, gv, uv) if v is not None and (v > 0) == (sgn > 0))
                for w in (15, 30):
                    mw = next((j for j in ms if j >= m + w), None)
                    ev[f"p{w}"] = None if mw is None else round(sgn * (sp[mw] - s0))
        events.append(ev)
    rows = []
    for m in ms:
        r = R[m]
        rows.append({"m": m, "s": round(sp[m], 1), "d": F.get(m), "src": src.get(m), "p": pic.get(m), "e": eff.get(m),
                     "fo": None if m not in futoi else round(futoi[m] / LOT),
                     "oi": [None if leg(r, k, sd).get("oi_chg") is None else round(leg(r, k, sd)["oi_chg"] / 1e5, 1) for k in keep for sd in ("ce", "pe")]})
    # the basis as a 3-min median of fut (book ltp) minus spot, per minute
    basis = {}
    for m in ms:
        xs = [B[j][2] - sp[j] for j in (m - 2, m - 1, m) if j in B and j in sp]
        if xs:
            basis[m] = round(st.median(xs))
    return {"day": day, "label": label, "step": step, "strikes": keep, "rows": rows, "events": events, "G": G, "U": U, "basis": basis,
            "near": near(day), "dext_minutes": len(D), "book_minutes": len([m for m in B if B[m][1] > 0])}


if __name__ == "__main__":
    data = [day_data(d, l) for d, l in DAYS]
    js = "window.HS2 = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    open(os.path.join(HERE, "data_v2.js"), "w", encoding="utf-8").write(js)
    tpl = os.path.join(HERE, "handshake-v2.html")
    if os.path.exists(tpl):
        page = open(tpl, encoding="utf-8").read().replace('<script src="data_v2.js"></script>', "<script>" + js + "</script>")
        open(os.path.join(HERE, "RAFTAAR-handshake-v2.html"), "w", encoding="utf-8").write(page)
    for x in data:
        ans = {}
        for e in x["events"]:
            ans[e.get("ans", "?")] = ans.get(e.get("ans", "?"), 0) + 1
        print(x["day"], x["near"], "Dext", x["dext_minutes"], "book", x["book_minutes"], "·", len(x["events"]), "pushes", ans)
