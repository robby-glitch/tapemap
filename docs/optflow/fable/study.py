"""3 Nov option flow x OI, minute-true. Builds the per-strike table and the window states, prints the read, and writes
day.json for mockup.html. Causal: window w reads minutes <= w's last minute only. Run from tapemap/:
    python -I -X utf8 docs/optflow/fable/study.py            # prints the 3-min read for NIFTY
    python -I -X utf8 docs/optflow/fable/study.py SENSEX 15  # SENSEX at 15-min
    python -I -X utf8 docs/optflow/fable/study.py --json     # writes day.json
Units: OI and volume in quantity (Dext's volume matched the chain's cumulative vol within 1.2 % on 3 Nov). L = lakh qty.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
import load as _load
if "--day" in sys.argv:
    _load.CUR["day"] = sys.argv[sys.argv.index("--day") + 1]

# [I] thresholds, stated once. A strike "moved" in a window when |dOI| >= OI_MOVE and the aggressor side is clear
# (|delta| >= AGG_FRAC x the window's volume). NIFTY 1.5L qty / 3 min = 2,000 lots at one strike, the smallest change a
# trader would call a wall moving (Jarvis's own readability bar is 3L / 3 min for a strike near ATM). SENSEX scaled by
# the measured volume ratio (~1/65 on 3 Nov), rounded to a number she can say.
OI_MOVE = {"NIFTY": 150_000, "SENSEX": 2_500}
AGG_X = 0.2               # [I] |delta| >= 0.2 x |dOI|: at least one in five of the contracts that opened or closed was
                          # crossed by that side. Below it the window was posted both ways: MIXED (no one was in a hurry).
                          # Measured 3 Nov: ATM option |delta| is ~11 % of volume at the median, so a volume-based cut
                          # called everything MIXED; the OI change is the right yardstick for "who was in a hurry".
WIN = 3                   # her canonical 3-min bar
BIG = {"NIFTY": 500_000, "SENSEX": 8_000}   # [I] one price cell, one minute: BADA. NIFTY 5L = 6,667 lots (the decoder's
                                            # BADA floor is single-print based; this is one price level in one minute)
QUAD = {(1, -1): "WRITE", (1, 1): "BUY", (-1, 1): "COVER", (-1, -1): "DUMP"}
HINGLISH = {"WRITE": "likh rahe", "BUY": "kharid rahe", "COVER": "bhaag rahe", "DUMP": "nikal rahe", "QUIET": "shaant",
            "MIXED": "mila-jula"}


def sgn(x, t):
    return 1 if x >= t else -1 if x <= -t else 0


def table(idx):
    """Per strike per minute: oi, buy, sell, delta, premium, big cell. Minutes with no chain row carry oi=None."""
    dx = dext()[idx]
    ch = chain(idx)
    oi, spot = oi_table(ch)
    ft = fut(idx)
    mins = sorted(set(ft) | set(oi))
    mins = [m for m in mins if 555 <= m <= 930]
    strikes = sorted(dx)
    out = {}
    for k in strikes:
        rows = dx[k]
        per = {}
        for m in mins:
            r = rows.get(m)
            o = oi.get(m, {}).get(k)
            cell = None
            if r:
                lv = max(r["levels"], key=lambda x: x["total_volume"], default=None)
                if lv:
                    cell = (lv["price"], lv["buy_volume"], lv["sell_volume"])
            per[m] = {"oi": o, "buy": r["buy_volume"] if r else None, "sell": r["sell_volume"] if r else None,
                      "delta": r["delta"] if r else None, "vol": r["total_volume"] if r else None,
                      "hi": r["high"] if r else None, "lo": r["low"] if r else None, "cell": cell}
        out[k] = per
    return mins, strikes, out, spot, ft, ch


def last_oi(per, m):
    """The last OI known at or before minute m (the chain's last snapshot), with its minute."""
    while m >= 555:
        o = per.get(m, {}).get("oi")
        if o is not None:
            return o, m
        m -= 1
    return None, None


def window(idx, per, m0, m1):
    """One strike over minutes (m0, m1]: dOI from the last known OI at m0 to the one at m1, summed flow, the WHO word."""
    o1, t1 = last_oi(per, m1)
    o0, t0 = last_oi(per, m0)
    doi = (o1 - o0) if (o0 is not None and o1 is not None) else None
    rs = [per[m] for m in range(m0 + 1, m1 + 1) if per.get(m) and per[m]["vol"] is not None]
    vol = sum(r["vol"] for r in rs) if rs else None
    delta = sum(r["delta"] for r in rs) if rs else None
    stale = (t1 is not None and m1 - t1 > 2)          # OI older than 2 min at the window's end: say so
    if doi is None or stale:
        who = "OI?"
    elif vol is None:
        who = "FLOW?"
    elif abs(doi) < OI_MOVE[idx]:
        who = "QUIET"
    else:
        s = sgn(delta, AGG_X * abs(doi))
        who = QUAD.get((1 if doi > 0 else -1, s), "MIXED")
    big = None
    for m in range(m0 + 1, m1 + 1):
        c = per.get(m, {}).get("cell")
        if c and c[1] + c[2] >= BIG[idx] and (big is None or c[1] + c[2] > big[2] + big[3]):
            big = (m, c[0], c[1], c[2])
    return {"doi": doi, "vol": vol, "delta": delta, "who": who, "stale": stale, "big": big, "oi": o1}


def window_lag(idx, per, m0, m1):
    """The same strike with the DELTA window one minute earlier ((m0-1, m1-1]) against the OI window (m0, m1]: the
    exchange publishes OI about once a minute (median 63 s between changes on 3 Nov), so a window's OI change can belong
    to the trades of the minute before. Both windows are knowable at m1. A label is FIRM when window() and window_lag()
    agree."""
    w = window(idx, per, m0, m1)
    rs = [per[m] for m in range(m0, m1) if per.get(m) and per[m]["vol"] is not None]
    if w["doi"] is None or w["who"] in ("OI?", "FLOW?", "QUIET") or not rs:
        return w["who"]
    delta = sum(r["delta"] for r in rs)
    s = sgn(delta, AGG_X * abs(w["doi"]))
    return QUAD.get((1 if w["doi"] > 0 else -1, s), "MIXED")


def sides(idx, strikes, tab, spot_at, m0, m1, dOI_sum=None):
    """The four groups at the window's end: CAP (CE >= spot), FLOOR (PE <= spot), ITM CE (< spot), ITM PE (> spot).
    Each: summed dOI, summed delta, the strikes' words, and the group's own word by the sum."""
    sp = spot_at
    groups = {"CAP": [], "FLOOR": [], "ITM_CE": [], "ITM_PE": []}
    for k in strikes:
        strike, side = k
        g = ("CAP" if strike >= sp else "ITM_CE") if side == "CE" else ("FLOOR" if strike <= sp else "ITM_PE")
        groups[g].append(k)
    out = {}
    for g, ks in groups.items():
        ws = {k: window(idx, tab[k], m0, m1) for k in ks}
        doi = sum(w["doi"] for w in ws.values() if w["doi"] is not None)
        delta = sum(w["delta"] for w in ws.values() if w["delta"] is not None)
        vol = sum(w["vol"] for w in ws.values() if w["vol"] is not None)
        known = sum(1 for w in ws.values() if w["doi"] is not None and not w["stale"])
        if not known:
            word = "OI?"
        elif abs(doi) < OI_MOVE[idx] * 2:
            word = "QUIET"
        else:
            s = sgn(delta, AGG_X * abs(doi))
            word = QUAD.get((1 if doi > 0 else -1, s), "MIXED")
        out[g] = {"doi": doi, "delta": delta, "vol": vol, "word": word, "strikes": ws, "n": len(ks), "known": known}
    return out


def L(x):
    return f"{x / 1e5:+.1f}L" if x is not None else "?"


def main():
    idx = next((a for a in sys.argv[1:] if a in ("NIFTY", "SENSEX")), "NIFTY")
    step = next((int(a) for a in sys.argv[1:] if a.isdigit()), WIN)
    mins, strikes, tab, spot, ft, ch = table(idx)
    print(idx, len(strikes), "contracts", hm(mins[0]), "->", hm(mins[-1]), "OI_MOVE", OI_MOVE[idx], "BIG", BIG[idx])
    m = 554      # her grid: the first bar is 09:15-09:17 (minutes 555..557), closing at the end of 09:17
    hdr = " ".join(f"{k[0] % 1000:>4}{k[1][0]}" for k in strikes)
    print(f"{'time':11} {'fut':>6} {'spot':>7} | CAP(CE>=s)        FLOOR(PE<=s)       ITMce      ITMpe     | per strike dOI(L) who")
    while m + step <= 930:
        m0, m1 = m, m + step
        sp = None
        for mm in range(m1, 554, -1):
            if mm in spot:
                sp = spot[mm]; break
        f = ft.get(m1, ft.get(m1 - 1))
        if sp is None or f is None:
            m += step; continue
        S = sides(idx, strikes, tab, sp, m0, m1)
        def grp(g):
            x = S[g]
            return f"{x['word']:6} {L(x['doi']):>7} d{x['delta'] / 1e5:+5.1f}"
        allw = {}
        for g in S.values():
            allw.update(g["strikes"])
        top = sorted((k for k in allw if allw[k]["doi"] is not None and allw[k]["who"] not in ("QUIET", "OI?")),
                     key=lambda k: -abs(allw[k]["doi"]))[:4]
        cells = [f"{k[0]}{k[1][0]} {allw[k]['who']} {allw[k]['doi'] / 1e5:+.1f}L" + (" BADA" if allw[k]["big"] else "") for k in top]
        print(f"{hm(m0 + 1)}-{hm(m1)} {f[3]:6.0f} {sp:7.1f} | {grp('CAP')} | {grp('FLOOR')} | {S['ITM_CE']['word']:6} | {S['ITM_PE']['word']:6} | " + " · ".join(cells))
        m += step


if __name__ == "__main__" and "--json" not in sys.argv:
    main()


# ---------------------------------------------------------------- the export for mockup.html (rolling 3-min, per minute)
UP = {"CAP": {"COVER": 2, "BUY": 1, "DUMP": -1, "WRITE": -2}, "FLOOR": {"WRITE": 2, "DUMP": 1, "BUY": -1, "COVER": -2}}
CODE = {"WRITE": "W", "BUY": "B", "COVER": "C", "DUMP": "D", "MIXED": "M", "QUIET": "Q", "OI?": "?", "FLOW?": "F"}


def word_of(cap, fl):
    """The one word from the cap's and the floor's state, and its lean. A display word, not a rule.
    Score (UP): cap COVER +2 / BUY +1 / DUMP -1 / WRITE -2; floor WRITE +2 / DUMP +1 / BUY -1 / COVER -2.
    |S| >= 3 is FUEL (writers on one side running or pressing, the other side agreeing); |S| == 2 from one side alone is
    named by that side (a LID is not a drop, a FLOOR is not a rally); |S| == 1 is buyers chasing; 0 names the pair."""
    if cap == "OI?" or fl == "OI?":
        return "OI?", 0
    c, f = UP["CAP"].get(cap, 0), UP["FLOOR"].get(fl, 0)
    s = c + f
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
    if cap == "WRITE" and fl == "WRITE":
        return "PIN", 0
    if cap == "COVER" and fl == "COVER":
        return "SQUEEZE", 0
    if cap == "DUMP" and fl == "DUMP":
        return "BUYERS OUT", 0
    return "QUIET", 0


def held(words, leans, mins):
    """The said lean: changes only at her 3-min closes, on the same lean at 2 consecutive closes (Jarvis's ACT_CLOSES);
    the first close says it at once; OI? at once (a clock, not a read). The said WORD is the latest close's word of that
    lean, so a FUEL word is never said off one window alone (a break taken back in the next window is a SHAKE)."""
    out, w, ln, pend = [], None, None, None
    for m, cand, cl in zip(mins, words, leans):
        if cand == "OI?":
            w, ln, pend = "OI?", 0, None
        elif (w is None or w == "OI?") and (m - 555) % 3 == 2:   # the first word is said at a close, never mid-bar (R3)
            w, ln, pend = cand, cl, None
        elif w is None or w == "OI?":
            pass
        elif (m - 555) % 3 == 2:
            if cl == ln:
                w, pend = cand, None
            else:
                pend = [cl, (pend[1] + 1) if pend and pend[0] == cl else 1]
                if pend[1] >= 2:
                    w, ln, pend = cand, cl, None
        out.append(w)
    return out


def export(idx):
    mins, strikes, tab, spot, ft, ch = table(idx)
    mins = [m for m in mins if 555 <= m <= 930]
    vx = vix()
    J = [r for r in jarvis() if r["idx"] == idx]
    jw = {}
    for r in J:
        jw[m_of(r["t"])] = {"w": r["word"], "lean": r["lean"], "with": r["count"]["with"], "against": r["count"]["against"],
                            "shown": r.get("shown")}
    # pushes (NIFTY's handshake log; SENSEX reads NIFTY's pushes by §1q, so the same rows with SENSEX's own strike)
    pushes = []
    p = os.path.join(D, "raftaar", f"handshake_{_load.CUR['day']}.jsonl")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                if r.get("idx") == idx and r.get("final"):
                    pushes.append({"t": r["t"], "dir": r["dir"], "lots": r["lots"], "k": r["k"], "side": r["side"],
                                   "ans": r["ans"], "who": r.get("who"), "am": r.get("am"), "p15": r.get("p15"), "p30": r.get("p30")})
    alerts = [{"t": r["t"], "kind": r["kind"], "line": r["line"]} for r in messages()
              if r["idx"] == idx and r["kind"] in ("SETUP", "FLOW", "READ")]
    sp_ff, last = {}, None
    for m in mins:
        if m in spot:
            last = spot[m]
        sp_ff[m] = last
    out = {"idx": idx, "day": _load.CUR["day"], "lot": LOT[idx], "step": STEP[idx], "oi_move": OI_MOVE[idx], "big": BIG[idx],
           "mins": mins, "spot": [], "fut": [], "futoi": [], "vix": [], "jarvis": [], "strikes": [list(k) for k in strikes],
           "oi": [], "ltp": [], "doi": [], "dl": [], "who": [], "bigc": [], "firm": [], "cap": [], "floor": [], "word": [], "lean": [],
           "pushes": pushes, "alerts": alerts, "chain_end": hm(max(ch))}
    # chain ltp / avg per strike per minute (the trapped gauge)
    ltp = {k: {} for k in strikes}
    for m, r in ch.items():
        for s in r["strikes"]:
            for side in ("ce", "pe"):
                k = (s["k"], side.upper())
                if k in ltp and s.get(side):
                    ltp[k][m] = (s[side]["ltp"], s[side]["avg"])
    for k in strikes:
        per = tab[k]
        out["oi"].append([per[m]["oi"] for m in mins])
        row = []
        lastv = None
        for m in mins:
            if m in ltp[k]:
                lastv = ltp[k][m]
            row.append(lastv)
        out["ltp"].append(row)
    jlast = None
    words = []
    for m in mins:
        sp = sp_ff[m]
        f = ft.get(m)
        out["spot"].append(sp)
        out["fut"].append(f[3] if f else None)
        out["futoi"].append(f[5] if f else None)
        out["vix"].append(vx.get(m))
        if m in jw:
            jlast = jw[m]
        out["jarvis"].append(jlast)
        if sp is None:
            S = None
        else:
            S = sides(idx, strikes, tab, sp, m - WIN, m)
        if S is None:
            for key in ("doi", "dl", "who", "bigc", "firm"):
                out[key].append([None] * len(strikes))
            out["cap"].append(None); out["floor"].append(None); words.append("OI?")
            continue
        allw = {}
        for g in S.values():
            allw.update(g["strikes"])
        out["doi"].append([allw[k]["doi"] for k in strikes])
        out["dl"].append([allw[k]["delta"] for k in strikes])
        out["who"].append([CODE[allw[k]["who"]] for k in strikes])
        out["firm"].append([1 if window_lag(idx, tab[k], m - WIN, m) == allw[k]["who"] else 0 for k in strikes])
        out["bigc"].append([(allw[k]["big"][2] + allw[k]["big"][3]) if allw[k]["big"] else 0 for k in strikes])
        for g in ("CAP", "FLOOR"):
            x = S[g]
            top = sorted((k for k in x["strikes"] if x["strikes"][k]["doi"] is not None), key=lambda k: -abs(x["strikes"][k]["doi"]))[:1]
            out[g.lower()].append({"w": x["word"], "doi": x["doi"], "dl": x["delta"], "top": list(top[0]) if top else None})
        words.append(word_of(S["CAP"]["word"], S["FLOOR"]["word"])[0])
        if "--trace" in sys.argv and (m - 555) % 3 == 2:
            print(hm(m), S["CAP"]["word"], S["FLOOR"]["word"], words[-1])
    leans = [LEAN.get(w, 0) for w in words]
    out["word"] = held(words, leans, mins)
    out["raw"] = words
    out["lean"] = [LEAN.get(w, 0) for w in out["word"]]
    out["next15"] = [(out["fut"][i + 15] - out["fut"][i]) if i + 15 < len(mins) and out["fut"][i] and out["fut"][i + 15] else None
                     for i in range(len(mins))]
    return out


LEAN = {"UP FUEL": 1, "LID BREAKING": 1, "FLOOR UP": 1, "UP BUYERS": 1, "DOWN FUEL": -1, "LID": -1, "FLOOR BREAKING": -1,
        "DOWN BUYERS": -1}


if "--json" in sys.argv:
    from collections import Counter
    days = {}
    for day in ("2026-11-03", "2026-11-02", "2026-10-30", "2026-10-29", "2026-10-28"):
        _load.CUR["day"] = day
        days[day] = {idx: export(idx) for idx in (("NIFTY", "SENSEX") if day >= "2026-11-02" else ("NIFTY",))}
        for idx, d in days[day].items():
            print(day, idx, "held words", Counter(d["word"]).most_common(6), "changes", sum(1 for a, b in zip(d["word"], d["word"][1:]) if a != b))
    for name, data in (("day.json", days["2026-11-03"]), ("days.json", days)):
        p = os.path.join(HERE, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        print("wrote", p, os.path.getsize(p) // 1024, "KB")
