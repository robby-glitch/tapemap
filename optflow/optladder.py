"""optladder.py -- the option order-flow LADDER for one index and one day, from the record (spec
docs/superpowers/specs/2026-11-05-option-orderflow-design.md §5, §7, §8; SHADOW until Phase 2's options_flow.py replaces
the compute behind the same shape). Read-only on tapemap/data; no clock, no network, nothing written.

    build(day, idx, upto=None) -> DATA   the dashboard's dict: per-minute series, the close layer at her 3-min closes
                                        (WHO per strike ATM ±3, groups, word, said lean, walls, cover alarm, R3 stamp,
                                        the read's trade from structures.py), the ATM footprint per minute, the lens,
                                        the opening read, the frame layer's reason. Minutes > upto are not read.

Every number at a minute uses data at or before it; the footprint's "ruka / nikla" mark resolves one minute later and
is labelled. Thresholds are [I] (§1s C4 with lot 65 and the first WHO window at 09:23); the lot is v2feed.LOTS checked
against the day's Dext cell GCD [M]. Named optladder because tapemap/ladder.py already exists. Served by optflow.py (/ladder, /ladder.json); embedded by the mockup export.
"""
from __future__ import annotations

import datetime
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.normpath(os.path.join(HERE, ".."))):     # python -I drops the script's own dir from sys.path
    if p not in sys.path:
        sys.path.insert(0, p)
import v2feed                       # stdlib-only module: LOTS, the one place the lot lives
import structures
from optflow import D, IST, scrip  # the Battlefield's data dir and scrip lookup (NSE-<id> / BSE-<id> -> scrip row)

IDX = {"NIFTY": {"exch": "NSE", "step": 50, "oi_move": 150_000}, "SENSEX": {"exch": "BSE", "step": 100, "oi_move": 2_500}}
AGG_X, COVER_N, NEAR = 0.2, 3, 3                     # [I] §1s C4; the cover alarm; ATM ±3
T0, T1, OPEN_END, FIRST_WHO = 555, 930, 585, 563     # 09:15..15:30; OPENING to 09:45; the first close at/after 09:21 = 09:23
QUAD = {(1, -1): "WRITE", (1, 1): "BUY", (-1, 1): "COVER", (-1, -1): "DUMP"}
HI = {"WRITE": "likh rahe", "BUY": "kharid rahe", "COVER": "bhaag rahe", "DUMP": "nikal rahe", "QUIET": "shaant",
      "MIXED": "mila-jula", "OI?": "OI nahi", "FLOW?": "flow nahi"}
UP = {"CAP": {"COVER": 2, "BUY": 1, "DUMP": -1, "WRITE": -2}, "FLOOR": {"WRITE": 2, "DUMP": 1, "BUY": -1, "COVER": -2}}
FRAME_CANT = ("optframe recorder not built (Phase 1): no option frames on the record. Would show: quote lag vs futures "
              "(ticks) · touch size vs yours · 30-s markout · undecided share · fut λ")


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def m_of(s):
    return int(s[:2]) * 60 + int(s[3:5])


def L(x):
    return None if x is None else round(x / 1e5, 1)


def sgn(x, t):
    return 1 if x >= t else -1 if x <= -t else 0


def _jsonl(path):
    try:
        with open(path, encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    try:
                        yield json.loads(l)
                    except ValueError:
                        continue
    except OSError:
        return


# ---- the record -------------------------------------------------------------------------------------------------------
def load_chain(day, idx):
    """{minute: the last snapshot in it}; empty when the day has no chain."""
    ch = {}
    for r in _jsonl(os.path.join(D, "chain", f"chain_{idx}_{day}.jsonl")):
        if "sec" in r:
            ch[r["sec"] // 60] = r
    return ch


def load_dext(day, idx, expiry):
    """{(k, 'CE'|'PE'): {minute: candle}} for the index's contracts of `expiry`."""
    cfg, out = IDX[idx], {}
    for p in glob.glob(os.path.join(D, "dext", f"dext_{cfg['exch']}-*_{day}.jsonl")):
        r = scrip().get(os.path.basename(p).split("_")[1])
        if not r or r[6] != idx or r[12] != expiry or r[14] not in ("CE", "PE"):
            continue
        rows = {}
        for c in _jsonl(p):
            if "t" in c:
                rows[(c["t"] + IST) % 86400 // 60] = c
        out[(int(float(r[13])), r[14])] = rows
    return out


def load_backfill(day, idx):
    return {m_of(r["t"]): r for r in _jsonl(os.path.join(D, "chain_backfill", f"backfill_{idx}_{day}.jsonl")) if "t" in r}


def load_fut1m(day, idx):
    try:
        with open(os.path.join(D, "tape", f"fut1m_{idx}_{day}.json"), encoding="utf-8") as f:
            return {m_of(k): v for k, v in json.load(f).items()}
    except (OSError, ValueError):
        return {}


def load_vix(day):
    return {m_of(r["ts"]): r["vix"] for r in _jsonl(os.path.join(D, "vix", f"vix_{day}.jsonl")) if "ts" in r}


def load_jarvis(day, idx):
    return {m_of(r["t"]): r for r in _jsonl(os.path.join(D, "jarvis", f"call_{day}.jsonl")) if r.get("idx") == idx and "t" in r}


def prior_day(day, idx):
    """The last day before `day` with a futures tape, up to 7 days back."""
    d = datetime.date.fromisoformat(day)
    for i in range(1, 8):
        p = (d - datetime.timedelta(days=i)).isoformat()
        if os.path.exists(os.path.join(D, "tape", f"fut1m_{idx}_{p}.json")):
            return p
    return None


def lot_check(dext, lot):
    """The day's Dext cell GCD against the feed's lot [M]; None when there are no cells."""
    g = 0
    for rows in dext.values():
        for c in rows.values():
            for lv in c.get("levels") or ():
                for k in ("buy_volume", "sell_volume"):
                    v = int(lv.get(k) or 0)
                    if v:
                        g = math.gcd(g, v)
    return None if not g else {"gcd": g, "lot": lot, "ok": g == lot}


# ---- the build ---------------------------------------------------------------------------------------------------------
def build(day, idx="NIFTY", upto=None):
    cfg = IDX[idx]
    STEP, OI_MOVE = cfg["step"], cfg["oi_move"]
    LOT = v2feed.LOTS.get(idx) or 1
    CH = load_chain(day, idx)
    if not CH:
        return {"ok": False, "day": day, "idx": idx, "why": f"no chain for {idx} on {day}: dekh nahi paaye"}
    expiry = CH[max(CH)].get("expiry")
    DX = load_dext(day, idx, expiry)
    BF, FT, JV = load_backfill(day, idx), load_fut1m(day, idx), load_jarvis(day, idx)
    VX = load_vix(day) if idx == "NIFTY" else {}
    last = min(T1, max(max(CH), max(FT) if FT else 0))
    if upto is not None:
        last = min(last, upto)
    MINS = list(range(T0, last + 1))
    OI, SPOT = {}, {}
    for m, r in CH.items():
        SPOT[m] = r.get("spot")
        OI[m] = {(s["k"], sd.upper()): s[sd]["oi"] for s in r.get("strikes") or [] for sd in ("ce", "pe") if s.get(sd) and s[sd].get("oi") is not None}
    dte = (datetime.date.fromisoformat(expiry) - datetime.date.fromisoformat(day)).days if expiry else None

    def chain_m(m):
        return max((mm for mm in CH if mm <= m), default=None)

    def spot_at(m):
        for mm in range(m, T0 - 1, -1):
            if SPOT.get(mm):
                return SPOT[mm], "chain"
            if mm in BF and BF[mm].get("spot"):
                return BF[mm]["spot"], "backfill"
        return None, None

    def leg(m, k, sd):
        mm = chain_m(m)
        s = next((x for x in (CH.get(mm) or {}).get("strikes") or [] if x["k"] == k), None) if mm is not None else None
        return (s or {}).get(sd.lower()) or {}

    def last_oi(k, sd, m):
        for mm in range(m, T0 - 1, -1):
            v = OI.get(mm, {}).get((k, sd))
            if v is not None:
                return v, mm
        return None, None

    def window(k, sd, m0, m1):
        o1, t1 = last_oi(k, sd, m1)
        o0, _ = last_oi(k, sd, m0)
        doi = (o1 - o0) if (o0 is not None and o1 is not None) else None
        rows = [DX[(k, sd)][m] for m in range(m0 + 1, m1 + 1) if (k, sd) in DX and m in DX[(k, sd)]]
        delta = sum(r["delta"] or 0 for r in rows) if rows else None
        vol = sum(r["total_volume"] or 0 for r in rows) if rows else None
        stale = t1 is not None and m1 - t1 > 2
        if doi is None or stale:
            who = "OI?"
        elif delta is None:
            who = "FLOW?"
        elif abs(doi) < OI_MOVE:
            who = "QUIET"
        else:
            who = QUAD.get((1 if doi > 0 else -1, sgn(delta, AGG_X * abs(doi))), "MIXED")
        firm = None
        if who in QUAD.values():
            lag = [DX[(k, sd)][m] for m in range(m0, m1) if (k, sd) in DX and m in DX[(k, sd)]]
            if lag:
                d2 = sum(r["delta"] or 0 for r in lag)
                firm = QUAD.get((1 if doi > 0 else -1, sgn(d2, AGG_X * abs(doi))), "MIXED") == who
        return {"who": who, "firm": firm, "doi": doi, "delta": delta, "vol": vol, "oi": o1, "stale": stale}

    def word_of(cap, fl):
        if cap == "OI?" or fl == "OI?":
            return "OI?", 0
        s = UP["CAP"].get(cap, 0) + UP["FLOOR"].get(fl, 0)
        if s >= 3:
            return "UP FUEL", 1
        if s <= -3:
            return "DOWN FUEL", -1
        if s == 2:
            return ("LID BREAKING", 1) if cap == "COVER" else ("FLOOR UP", 1) if fl == "WRITE" else ("UP BUYERS", 1)
        if s == -2:
            return ("LID", -1) if cap == "WRITE" else ("FLOOR BREAKING", -1) if fl == "COVER" else ("DOWN BUYERS", -1)
        if s == 1:
            return "UP BUYERS", 1
        if s == -1:
            return "DOWN BUYERS", -1
        return {("WRITE", "WRITE"): "PIN", ("COVER", "COVER"): "SQUEEZE", ("DUMP", "DUMP"): "BUYERS OUT"}.get((cap, fl), "QUIET"), 0

    def walls(m, sp):
        out, have = {}, [mm for mm in OI if mm <= m]
        for sd, cond in (("CE", lambda k: k >= sp), ("PE", lambda k: k <= sp)):
            best = None
            for (k, s), v in (OI[max(have)].items() if have else ()):
                if s == sd and cond(k) and (best is None or v > best[1]):
                    best = (k, v)
            if not best:
                out[sd.lower()] = None
                continue
            o6, _ = last_oi(best[0], sd, m - 6)
            ch6 = None if o6 is None else best[1] - o6
            state = "?" if ch6 is None else "building" if ch6 >= OI_MOVE else "leaving" if ch6 <= -OI_MOVE else "holding"
            out[sd.lower()] = {"k": best[0], "oi": L(best[1]), "state": state, "ch6": L(ch6)}
        return out

    # ---- the close layer ----
    closes, said, lean_said, pend, prev = {}, None, None, None, None
    for m in [m for m in MINS if (m - T0) % 3 == 2 and m >= FIRST_WHO]:
        sp, _ = spot_at(m)
        if sp is None:
            continue
        atm = int(round(sp / STEP) * STEP)
        ks = [atm + i * STEP for i in range(-NEAR, NEAR + 1)]
        st = {f"{k}{sd}": window(k, sd, m - 3, m) for k in ks for sd in ("CE", "PE")}
        groups = {}
        for g, pick in (("CAP", lambda k, sd: sd == "CE" and k >= sp), ("FLOOR", lambda k, sd: sd == "PE" and k <= sp),
                        ("ITM_CE", lambda k, sd: sd == "CE" and k < sp), ("ITM_PE", lambda k, sd: sd == "PE" and k > sp)):
            ws = [st[f"{k}{sd}"] for k in ks for sd in ("CE", "PE") if pick(k, sd)]
            known = [w for w in ws if w["doi"] is not None and not w["stale"]]
            doi = sum(w["doi"] for w in known)
            dl = sum(w["delta"] for w in known if w["delta"] is not None)
            word = "OI?" if not known else "QUIET" if abs(doi) < 2 * OI_MOVE else QUAD.get((1 if doi > 0 else -1, sgn(dl, AGG_X * abs(doi))), "MIXED")
            groups[g] = {"word": word, "doi": L(doi) if known else None, "delta": L(dl) if known else None, "n": len(ws), "known": len(known)}
        word, lean = word_of(groups["CAP"]["word"], groups["FLOOR"]["word"])
        if word == "OI?":
            said, lean_said, pend = "OI?", 0, None
        elif said is None or said == "OI?":
            said, lean_said, pend = word, lean, None
        elif lean == lean_said:
            said, pend = word, None
        else:
            pend = [lean, (pend[1] + 1) if pend and pend[0] == lean else 1]
            if pend[1] >= 2:
                said, lean_said, pend = word, lean, None
        cover = None
        for sd in ("CE", "PE"):
            cs = [k for k in ks if st[f"{k}{sd}"]["who"] == "COVER"]
            if len(cs) >= COVER_N:
                cover = {"side": sd, "n": len(cs), "doi": L(sum(st[f"{k}{sd}"]["doi"] for k in cs))}
        wl = walls(m, sp)
        for sd in ("ce", "pe"):
            if wl[sd]:
                wl[sd]["who"] = st.get(f"{wl[sd]['k']}{sd.upper()}", {}).get("who", "flow nahi")
        stamps = []
        for sd, side, key in (("CE", 1, "ce"), ("PE", -1, "pe")):
            w = wl[key]
            if w and w.get("who") == "COVER":
                others = [k for k in ks if (k >= sp if sd == "CE" else k <= sp) and k != w["k"] and st[f"{k}{sd}"]["who"] == "COVER"]
                pw = prev and prev["walls"][key] and prev["walls"][key].get("who") == "COVER"
                if len(others) >= 2 or pw:
                    stamps.append({"read": "R3", "dir": side, "k": w["k"]})
        read = sum(1 for w in st.values() if w["who"] not in ("OI?", "FLOW?"))
        cap_t = f"cap {HI[groups['CAP']['word']]} {groups['CAP']['doi']:+}L" if groups["CAP"]["doi"] is not None else "cap OI nahi"
        flo_t = f"floor {HI[groups['FLOOR']['word']]} {groups['FLOOR']['doi']:+}L" if groups["FLOOR"]["doi"] is not None else "floor OI nahi"
        cov_t = f"{cover['side']} bhaag rahe ×{cover['n']} {cover['doi']:+}L" if cover else "cover nahi dekha"
        cap = wl["ce"]
        cm = chain_m(m)
        row = {"t": hm(m), "word": word, "lean": lean, "said": said, "lean_said": lean_said, "groups": groups,
               "strikes": {kk: dict(w, doi=L(w["doi"]), delta=L(w["delta"]), vol=L(w["vol"]), oi=L(w["oi"])) for kk, w in st.items()},
               "cover": cover, "walls": wl, "stamps": stamps, "atm": atm, "ks": ks, "step": STEP,
               "caption": f"{said} · {cap_t} · {flo_t} · {cov_t} · " + (f"wall {cap['k']} CE {cap['state']}" if cap else "no CE wall above"),
               "why": [f"flow: {read} of {len(st)} strikes read", f"oi: chain {CH[cm]['ts']}" if cm is not None else "oi: no chain yet"]}
        ce, pe = leg(m, atm, "CE"), leg(m, atm, "PE")
        em = round(ce["ltp"] + pe["ltp"], 2) if ce.get("ltp") and pe.get("ltp") else None
        row["em"] = em
        row["trade"] = structures.pick(row, CH.get(cm) if cm is not None else None, LOT, dte, m, em)
        closes[m] = row
        prev = row

    # ---- the minute layer: the ATM CE / PE footprint ----
    minute, cells = {}, []
    for m in MINS:
        sp, _ = spot_at(m)
        if sp is None:
            continue
        atm = int(round(sp / STEP) * STEP)
        row = {}
        for sd in ("CE", "PE"):
            c = DX.get((atm, sd), {}).get(m)
            if not c:
                row[sd] = {"k": atm, "cant": "no Dext minute"}
                continue
            lv = c.get("levels") or []
            poc = max(lv, key=lambda x: x["total_volume"]) if lv else None
            big = max(lv, key=lambda x: max(x["buy_volume"], x["sell_volume"])) if lv else None
            bq, bside = (max(big["buy_volume"], big["sell_volume"]), "B" if big["buy_volume"] >= big["sell_volume"] else "S") if big else (0, None)
            dl = leg(m, atm, sd).get("delta")
            dlots = round(bq * abs(dl) / LOT) if dl else None
            p90 = sorted(cells)[int(len(cells) * 0.9)] if len(cells) >= 6 else None
            cells.append(bq)
            bin_ = max(0.05, round(0.01 * (c["high"] + c["low"]) / 2 / 0.05) * 0.05)
            nxt = DX.get((atm, sd), {}).get(m + 1) if (upto is None or m + 1 <= upto) else None   # HINDSIGHT, one minute
            absorb = None
            if p90 is not None and bq >= p90 and big:
                if nxt is None:
                    absorb = "agla minute?"
                else:
                    prog = (nxt["high"] - big["price"]) if bside == "B" else (big["price"] - nxt["low"])
                    absorb = "ruka (absorbed)" if prog <= bin_ else "nikla (went through)"
            row[sd] = {"k": atm, "vol": L(c["total_volume"]), "delta": L(c["delta"]), "hi": c["high"], "lo": c["low"],
                       "poc": poc and [poc["price"], L(poc["total_volume"])], "big": big and [big["price"], bside, L(bq), dlots],
                       "p90": L(p90), "absorb": absorb, "bin": round(bin_, 2), "n": len(lv)}
        minute[m] = row

    # ---- the opening read (§7.1) ----
    pday = prior_day(day, idx)
    PF = load_fut1m(pday, idx) if pday else {}
    pc = PF[max(PF)][3] if PF else None
    o15 = FT.get(T0)
    gap = None if not (o15 and pc) else round(o15[0] - pc, 1)
    prange = (max(v[1] for v in PF.values()) - min(v[2] for v in PF.values())) if PF else None
    strad = {}
    for m in range(T0, T0 + 6):
        b = BF.get(m)
        if not b or not b.get("spot"):
            continue
        a = int(round(b["spot"] / STEP) * STEP)
        px = (b.get("px") or {}).get(str(a))
        if px and px[0] and px[1]:
            strad[hm(m)] = {"atm": a, "ce": px[0], "pe": px[1], "sum": round(px[0] + px[1], 2)}
    b17 = BF.get(T0 + 2) or {}
    cross = {"CE": 0.0, "PE": 0.0, "n": 0}
    if b17.get("spot"):
        a17 = int(round(b17["spot"] / STEP) * STEP)
        for k in range(a17 - NEAR * STEP, a17 + NEAR * STEP + 1, STEP):
            chg = (b17.get("k") or {}).get(str(k))
            if chg:
                cross["CE"] += chg[0]
                cross["PE"] += chg[1]
                cross["n"] += 1
    sl = list(strad.values())
    s_dir = None if len(sl) < 2 else ("BID" if sl[-1]["sum"] > sl[0]["sum"] else "OFFERED")
    vs_prior, vs_cant = None, None
    PCH = load_chain(pday, idx) if pday else {}
    if not PCH:
        vs_cant = "no prior day's chain: dekh nahi paaye"
    elif not sl:
        vs_cant = "no 09:15 straddle in the backfill: dekh nahi paaye"
    else:
        ps = PCH[max(PCH)]
        if ps.get("expiry") != expiry:
            vs_cant = f"prior day's chain holds the {ps.get('expiry')} expiry, not {expiry}: dekh nahi paaye"
        else:
            s = next((x for x in ps.get("strikes") or [] if x["k"] == sl[0]["atm"]), None)
            if s and s.get("ce", {}).get("ltp") and s.get("pe", {}).get("ltp"):
                vs_prior = round(sl[-1]["sum"] - (s["ce"]["ltp"] + s["pe"]["ltp"]), 2)
            else:
                vs_cant = "the prior close has no quote at today's ATM: dekh nahi paaye"
    otype = "UNREADABLE" if vs_prior is None else ("GO-leaning" if vs_prior > 0 else "FADE-leaning")
    OPEN = {"prior_day": pday, "prior_close": pc, "prior_range": None if prange is None else round(prange, 1),
            "fut_0915": o15 and {"o": o15[0], "h": o15[1], "l": o15[2], "c": o15[3]},
            "gap": gap, "gap_pct": None if gap is None else round(100 * gap / pc, 2),
            "gap_sigma": None if gap is None or not prange else round(gap / (prange / 4), 2),
            "straddle": strad, "straddle_dir_proxy": s_dir, "straddle_vs_prior": vs_prior, "straddle_vs_prior_cant": vs_cant,
            "cross": {"CE": L(cross["CE"]), "PE": L(cross["PE"]), "n": cross["n"], "prior": "rest (09:15 REST baseline, A125)"},
            "type": otype, "type_why": ("the straddle has no prior-close reference on this day; the intraday direction is a proxy only"
                                        if vs_prior is None else "straddle vs prior close, θ not adjusted [I]"),
            "first_who": hm(FIRST_WHO), "chain_from": CH[min(CH)].get("ts"), "src": "chain_backfill (REST, tagged backfill)"}

    # ---- the lens ----
    def iv_atm(m):
        sp, _ = spot_at(m)
        if sp is None:
            return None
        v = leg(m, int(round(sp / STEP) * STEP), "CE").get("iv")
        return None if v is None else round(100 * v, 2)
    iv_ref = next((iv_atm(m) for m in range(T0 + 5, T0 + 45) if iv_atm(m) is not None), None)
    vix_open = VX[min(VX)] if VX else None
    lens = {}
    for m in MINS:
        part = "09:15-10:00" if m < 600 else "10:00-12:00" if m < 720 else "12:00-13:30" if m < 810 else "13:30-15:15"
        iv = iv_atm(m)
        oi5 = (FT[m][5] - FT[m - 5][5]) / LOT if m in FT and m - 5 in FT and FT[m][5] and FT[m - 5][5] else None
        px5 = FT[m][3] - FT[m - 5][3] if m in FT and m - 5 in FT else None
        run = None
        if oi5 is not None and abs(oi5) >= 500:
            run = {"kind": "FRESH" if oi5 > 0 else "COVER", "lots": round(oi5), "dir": None if px5 is None else (1 if px5 >= 5 else -1 if px5 <= -5 else 0)}
        vx = VX.get(m)
        lens[m] = {"dte": dte, "part": part, "opening": m < OPEN_END, "iv": iv,
                   "iv_vs_ref": None if iv is None or iv_ref is None else round(iv - iv_ref, 2),
                   "vix": vx, "vix_vs_open": None if vx is None or vix_open is None else round(vx - vix_open, 2), "run": run, "profile": None}

    series = []
    for m in MINS:
        sp, src = spot_at(m)
        j = JV.get(m)
        series.append({"m": m, "t": hm(m), "spot": sp, "spot_src": src, "fut": FT[m][3] if m in FT else None,
                       "jarvis": j and {"word": j.get("word"), "lean": j.get("lean"), "count": j.get("count")}})
    return {"ok": True, "day": day, "idx": idx, "expiry": expiry, "lot": LOT, "lot_check": lot_check(DX, LOT), "t0": T0,
            "upto": None if upto is None else hm(upto), "series": series,
            "closes": {str(k): v for k, v in closes.items()}, "minute": {str(k): v for k, v in minute.items()},
            "lens": {str(k): v for k, v in lens.items()}, "open": OPEN, "frame": {"cant": FRAME_CANT},
            "thresholds": {"OI_MOVE": OI_MOVE, "AGG_X": AGG_X, "COVER_N": COVER_N, "NEAR": NEAR, "first_who": hm(FIRST_WHO)},
            "shadow": "SHADOW: thresholds [I], not a registered read, no order path"}


if __name__ == "__main__":
    import time
    day = next((a for a in sys.argv[1:] if a[:2] == "20"), time.strftime("%Y-%m-%d"))
    for idx in IDX:
        d = build(day, idx)
        if not d["ok"]:
            print(idx, d["why"])
            continue
        c = d["closes"]
        ks = sorted(c, key=int)
        print(f"{idx} {day}: {len(d['series'])} min · {len(c)} closes from {c[ks[0]]['t'] if ks else '-'} · lot {d['lot']} {d['lot_check']} · "
              f"open {d['open']['type']} gap {d['open']['gap']} · last: {c[ks[-1]]['caption'] if ks else '-'}")
