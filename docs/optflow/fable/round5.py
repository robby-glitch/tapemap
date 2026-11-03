"""Round 5: the anatomy of short covering on five recorded days (28, 29, 30 Oct, 2, 3 Nov), NIFTY, her 3-min grid.
Every definition below was fixed before any outcome was looked at (see REPORT.md R5.0). Causal at every close.
Run from tapemap/:  python -I -X utf8 docs/optflow/fable/round5.py  (reads days.json, the chain, Dext's futures footprint)"""
import json, os, sys, statistics as st
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "brainstorm"))
from load import hm, m_of, D, IST
import load as _load
import strike_bands as SB
from round4 import chain_greeks, fut_footprint, implied_delta, vpin_at, closes, last_close, fut_after

DAYS = json.load(open(os.path.join(HERE, "days.json"), encoding="utf-8"))
ORDER = ["2026-10-28", "2026-10-29", "2026-10-30", "2026-11-02", "2026-11-03"]
LOT = {"2026-10-28": 65, "2026-10-29": 65, "2026-10-30": 65, "2026-11-02": 75, "2026-11-03": 75}   # the Nov future's lot per the tape
# [I] thresholds, fixed before counting (trader's reasons in REPORT R5.0)
OI_MOVE = 1.5e5            # a strike moved (qty / 3 min), as before
TRAP_X = 1.10              # the wall's writers are under water when ltp >= 1.10 x the day's avg price
TRAP_BUILT = 4 * OI_MOVE   # ... on OI built today of at least 6L
NEAR_STEPS = 2             # spot within 2 strike steps of the wall (jarvis.AHEAD_STEPS)
FUT_OI_LOTS = 300          # a futures-OI leg over 15 min: 300 lots (Jarvis's fuel run is 500 / 5 min; 15 min, modest)
LEG_PTS = 40               # a fast move that matters: 40 pts in 15 min (her leg minimum)
COVER_CLOSES = 2           # the option leg "covered" when writers bought back at >= 2 of the window's 5 closes


def bands(day, x):
    """strike_bands' premium bands without its fut1m dependency: the option bars only (the index band comes from x)."""
    import optflow as O
    from contract_bars import _Vwap
    ch = O.load_chain(day, "NIFTY")
    exp = ch[max(ch)]["expiry"]
    snap, cur = {}, {}
    for m in range(555, 931):
        r = ch.get(m)
        if r:
            for s in r.get("strikes") or []:
                for sd in ("ce", "pe"):
                    q = s.get(sd) or {}
                    if q.get("oi") is not None:
                        cur[(s["k"], sd)] = (q["oi"], q.get("ltp"))
        snap[m] = dict(cur)
    dx = _load.dext(day)["NIFTY"]
    out = {}
    for (k, sd), rows in dx.items():
        stv, bl, prev = _Vwap(), {}, None
        for e in range(557, 930, 3):
            ms = [m for m in (e - 2, e - 1, e) if m in rows]
            s = snap.get(e, {}).get((k, sd.lower()))
            if not ms or not s or s[1] is None:
                prev = s[0] if s else prev
                continue
            h = max(rows[m]["high"] for m in ms); l = min(rows[m]["low"] for m in ms)
            v = sum(rows[m]["total_volume"] for m in ms)
            bd = stv.push(h, l, s[1], v)
            bl[e] = dict(h=h, l=l, c=s[1], **bd)
        out[(k, sd.upper())] = bl
    return out


def wall(x, i, side):
    """The wall strike at close i: the CE with the largest OI at/above spot (side 'CE') or the PE at/below (side 'PE')."""
    sp = x["spot"][i]
    if sp is None:
        return None
    best = None
    for q, k in enumerate(x["strikes"]):
        if k[1] != side:
            continue
        if (side == "CE" and k[0] >= sp) or (side == "PE" and k[0] <= sp):
            oi = x["oi"][q][i]
            if oi is not None and (best is None or oi > best[1]):
                best = (q, oi)
    return best[0] if best else None


def first_oi(x, q):
    for v in x["oi"][q]:
        if v is not None:
            return v
    return None


def pieces(day, x, i, dirn, gk, B, imp, fut, med3):
    """The lead-in pieces at close i for a move in direction dirn (+1 up: the cap; -1 down: the floor). Causal."""
    side = "CE" if dirn > 0 else "PE"
    q = wall(x, i, side)
    out = {}
    if q is None:
        return out
    k = tuple(x["strikes"][q])
    out["wall"] = k
    lp = x["ltp"][q][i]
    oi, oi0 = x["oi"][q][i], first_oi(x, q)
    out["trapped"] = bool(lp and lp[1] and oi is not None and oi0 is not None and lp[0] >= TRAP_X * lp[1] and oi - oi0 >= TRAP_BUILT)
    C = closes(x)
    ci = C.index(i) if i in C else None
    if ci is not None and ci >= 6:
        d_now = [x["doi"][C[ci - j]][q] for j in (0, 1)]
        d_prev = [x["doi"][C[ci - j]][q] for j in range(2, 7)]
        out["stalled"] = all(v is not None and abs(v) < OI_MOVE for v in d_now) and any(v is not None and v >= OI_MOVE for v in d_prev)
    sp = x["spot"][i]
    out["near"] = abs(k[0] - sp) <= NEAR_STEPS * x["step"]
    g_now = (gk.get(x["mins"][i], {}).get(k) or (None, None))[1]
    g_prev = (gk.get(x["mins"][i] - 3, {}).get(k) or (None, None))[1]
    out["gamma_up"] = (g_now is not None and g_prev is not None and g_now > g_prev)
    out["cover"] = x["who"][i][q] == "C" if x["who"][i] else False
    fo = x["futoi"][i]; fo30 = x["futoi"][i - 30] if i >= 30 else None
    out["fut_oi_30"] = ((fo - fo30) / LOT[day]) if fo is not None and fo30 is not None else None
    b = (B.get((k[0], side)) or {}).get(x["mins"][i])
    out["prem_band"] = SB.pos(b) if b else None
    s9 = lambda ser: sum(ser.get(x["mins"][j]) or 0 for j in range(max(0, i - 8), i + 1))
    out["imp9"], out["fut9"] = s9(imp), s9(fut)
    f3 = fut_after(x, i - 3, 3) if i >= 3 else None
    out["fast"] = f3 is not None and med3 and abs(f3) >= 2 * med3
    vp = vpin_at(day, x["mins"][i])
    out["vpin"] = vp["pct"] if vp else None
    j = x["jarvis"][i]
    out["jarvis"] = j["w"] if j else None
    return out


def main():
    res = {}
    allS = {"up": [], "dn": []}
    for day in ORDER:
        _load.CUR["day"] = day
        x = DAYS[day]["NIFTY"]
        C = closes(x)
        gk = chain_greeks(day)
        B = bands(day, x)
        imp, fut = implied_delta(day, x)
        print(f"\n################ {day} · futures: {_load.FUT_SRC.get(day, 'fut1m')} · chain from {hm(min(m for m in x['mins'] if x['spot'][x['mins'].index(m)] is not None))}")
        # 1. events: 15-min moves ending at closes, the 3 largest non-overlapping
        cands = []
        for i in C:
            if i >= 15 and x["fut"][i] is not None and x["fut"][i - 15] is not None:
                cands.append((abs(x["fut"][i] - x["fut"][i - 15]), i))
        cands.sort(reverse=True)
        picked = []
        for mv, i in cands:
            if all(abs(i - j) > 15 for _, j in picked):
                picked.append((mv, i))
            if len(picked) == 3:
                break
        # the day's median |3-min move| for FAST (running, causal) -- computed per close below
        for mv, e in sorted(picked, key=lambda z: z[1]):
            s = e - 15
            dirn = 1 if x["fut"][e] > x["fut"][s] else -1
            pts = x["fut"][e] - x["fut"][s]
            fo = ((x["futoi"][e] - x["futoi"][s]) / LOT[day]) if x["futoi"][e] is not None and x["futoi"][s] is not None else None
            win = [i for i in C if s < i <= e]
            cap = Counter(x["cap"][i]["w"] for i in win if x["cap"][i]); fl = Counter(x["floor"][i]["w"] for i in win if x["floor"][i])
            if dirn > 0:
                opt = "CAP COVER" if cap["COVER"] >= COVER_CLOSES else "CAP BUYERS" if cap["BUY"] >= COVER_CLOSES else "FLOOR WRITERS" if fl["WRITE"] >= 3 else "MIXED"
                mech = "SHORT COVERING" if (opt == "CAP COVER" or (fo is not None and fo <= -FUT_OI_LOTS)) else "FRESH LONGS" if (fo is not None and fo >= FUT_OI_LOTS) else "MIXED"
            else:
                opt = "FLOOR COVER" if fl["COVER"] >= COVER_CLOSES else "FLOOR BUYERS" if fl["BUY"] >= COVER_CLOSES else "CAP WRITERS" if cap["WRITE"] >= 3 else "MIXED"
                mech = "PUT-WRITER COVERING" if opt == "FLOOR COVER" else "LONG UNWIND" if (fo is not None and fo <= -FUT_OI_LOTS) else "FRESH SHORTS" if (fo is not None and fo >= FUT_OI_LOTS) else "MIXED"
            quad = "?" if fo is None else ("short covering" if (dirn > 0 and fo < 0) else "fresh longs" if (dirn > 0) else "long unwinding" if fo < 0 else "fresh shorts")
            print(f"\n== EVENT {hm(x['mins'][s])}→{hm(x['mins'][e])} {'▲' if dirn > 0 else '▼'} {pts:+.0f} pts · fut OI {f'{fo:+.0f} lots ({quad})' if fo is not None else 'unknown'} · option leg {opt} (cap {dict(cap)} · floor {dict(fl)}) → {mech}")
            # 2. lead-in: the first close in the 30 min before the start at which each piece was true
            lead = defaultdict(lambda: None)
            med = []
            for i in C:
                if i > s:
                    break
                f3 = fut_after(x, i - 3, 3) if i >= 3 else None
                if f3 is not None:
                    med.append(abs(f3))
            med3 = st.median(med) if med else None
            rows = []
            for i in C:
                if s - 30 <= i <= s:
                    P = pieces(day, x, i, dirn, gk, B, imp, fut, med3)
                    rows.append((i, P))
                    for key in ("trapped", "stalled", "near", "gamma_up", "cover", "fast"):
                        if P.get(key) and lead[key] is None:
                            lead[key] = x["mins"][s] - x["mins"][i]
                    if P.get("prem_band") in ("≥u2", "≥u3") and lead["prem_u2"] is None:
                        lead["prem_u2"] = x["mins"][s] - x["mins"][i]
                    if P.get("fut_oi_30") is not None and P["fut_oi_30"] * dirn < -FUT_OI_LOTS and lead["fut_oi_trend"] is None:
                        lead["fut_oi_trend"] = x["mins"][s] - x["mins"][i]
                    if P.get("imp9") is not None and P["imp9"] * dirn > 0 and P["fut9"] * dirn > 0 and lead["both_delta"] is None:
                        lead["both_delta"] = x["mins"][s] - x["mins"][i]
                    if P.get("vpin") is not None and P["vpin"] >= 0.7 and lead["vpin70"] is None:
                        lead["vpin70"] = x["mins"][s] - x["mins"][i]
            P0 = rows[-1][1] if rows else {}
            print("   lead-in (minutes before the start that the piece first held, within 30 min; '—' = not before the start): "
                  + " · ".join(f"{k} {lead[k]}" if lead[k] is not None else f"{k} —" for k in ("trapped", "stalled", "near", "gamma_up", "cover", "prem_u2", "fut_oi_trend", "both_delta", "fast", "vpin70")))
            print(f"   at the start close: wall {P0.get('wall')} · trapped {P0.get('trapped')} · stalled {P0.get('stalled')} · near {P0.get('near')} · prem {P0.get('prem_band')} · fut OI 30 {P0.get('fut_oi_30') and round(P0['fut_oi_30'])} · implied 9 {P0.get('imp9') and round(P0['imp9'])} · fut Δ 9 {P0.get('fut9') and round(P0['fut9'])} · VPIN p{P0.get('vpin')} · Jarvis {P0.get('jarvis')}")
            # 3. inside: who covered first, the cascade, the wall's migration, the premium burst
            side = "CE" if dirn > 0 else "PE"
            firsts, migr, burst = {}, [], None
            for i in win:
                sp = x["spot"][i]
                if sp is None or not x["who"][i]:
                    continue
                for q, k in enumerate(x["strikes"]):
                    if k[1] == side and ((dirn > 0 and k[0] >= sp - x["step"]) or (dirn < 0 and k[0] <= sp + x["step"])) and x["who"][i][q] == "C" and k[0] not in firsts:
                        firsts[k[0]] = (hm(x["mins"][i]), x["doi"][i][q])
                w = wall(x, i, side)
                if w is not None:
                    kk = x["strikes"][w][0]
                    if not migr or migr[-1][1] != kk:
                        migr.append((hm(x["mins"][i]), kk))
                    b = (B.get((kk, side)) or {}).get(x["mins"][i])
                    if b and SB.pos(b) == "≥u3" and burst is None:
                        burst = hm(x["mins"][i])
            print("   inside: first covers " + (", ".join(f"{k} {t} {d / 1e5:+.0f}L" for k, (t, d) in sorted(firsts.items(), key=lambda z: z[1][0])) or "none")
                  + f" · wall path {migr} · wall premium ≥u3 at {burst}")
        # 4. false alarms: the signature at every close, both directions
        for dirn, key in ((1, "up"), (-1, "dn")):
            med = []
            for i in C:
                f3 = fut_after(x, i - 3, 3) if i >= 3 else None
                if f3 is not None:
                    med.append(abs(f3))
                P = pieces(day, x, i, dirn, gk, B, imp, fut, st.median(med) if med else None)
                S = bool(P.get("trapped") and P.get("stalled") and P.get("near"))
                S4 = S and P.get("cover")
                nxt = fut_after(x, i, 15)
                allS[key].append((day, hm(x["mins"][i]), S, S4, nxt, {kk: bool(P.get(kk)) for kk in ("trapped", "stalled", "near", "cover", "fast")} | {"prem_u2": P.get("prem_band") in ("≥u2", "≥u3"), "vpin70": (P.get("vpin") or 0) >= 0.7, "imp_against": (P.get("imp9") or 0) * dirn < -20000}))
    # false-alarm table
    print("\n################ FALSE ALARMS · signature S = trapped AND stalled AND near (the wall); S4 = S AND the first cover; next = fut 15 min after the close")
    for key, dirn in (("up", 1), ("dn", -1)):
        print(f"\n-- {key.upper()} ({'the cap' if dirn > 0 else 'the floor'})")
        for day in ORDER:
            rows = [r for r in allS[key] if r[0] == day]
            nS = [r for r in rows if r[2]]; nS4 = [r for r in rows if r[3]]
            def split(rs):
                w = sum(1 for r in rs if r[4] is not None and r[4] * dirn >= LEG_PTS)
                a = sum(1 for r in rs if r[4] is not None and r[4] * dirn <= -LEG_PTS)
                return f"{len(rs)} closes · ≥{LEG_PTS} with {w} · ≥{LEG_PTS} against {a} · flat {len(rs) - w - a}"
            print(f"   {day}: closes {len(rows)} · S: {split(nS)} · S4: {split(nS4)}" + (f" · S at: {', '.join(r[1] for r in nS)[:160]}" if nS else ""))
            for pc in ("trapped", "stalled", "near", "cover", "prem_u2", "vpin70", "imp_against", "fast"):
                rs = [r for r in rows if r[5].get(pc)]
                print(f"        {pc:12} {split(rs)}")
            pairs = {"trapped+cover": lambda d: d["trapped"] and d["cover"], "stalled+cover": lambda d: d["stalled"] and d["cover"], "near+cover": lambda d: d["near"] and d["cover"], "trapped+near": lambda d: d["trapped"] and d["near"], "imp_against+near": lambda d: d["imp_against"] and d["near"]}
            for nm, fn in pairs.items():
                rs = [r for r in rows if fn(r[5])]
                print(f"        {nm:16} {split(rs)}")


if __name__ == "__main__":
    main()
