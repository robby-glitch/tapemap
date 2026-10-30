"""coil_scan.py -- what OI, the ATM straddle and the price range did in the 30 min BEFORE each real NIFTY leg started, and
in the first minutes of it. Descriptive rows for the coil / push / lean brainstorm (Mary 27 Oct: "is it able to detect
squeeze and big push candle where running started ... which side is leaning"). Read-only on data/chain. Rows, not rates.

    python coil_scan.py
"""
import gzip
import json
import os
import statistics as st

CHAIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "chain")
DAYS = ["2026-09-23", "2026-09-25", "2026-09-29", "2026-09-30", "2026-10-06", "2026-10-08", "2026-10-21", "2026-10-22",
        "2026-10-23", "2026-10-26", "2026-10-27"]
LEG = 0.0035      # a leg = a 0.35 % zigzag swing (~80 NIFTY pts)
PRE = 30          # minutes looked at before the leg starts


def minutes(day):
    """{minute-of-day: last row of that minute}"""
    p = os.path.join(CHAIN, f"chain_NIFTY_{day}.jsonl")
    f = open(p, encoding="utf-8") if os.path.exists(p) else gzip.open(p + ".gz", "rt", encoding="utf-8")
    out = {}
    with f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("spot") and r.get("ts"):
                h, m = int(r["ts"][:2]), int(r["ts"][3:5])
                out[h * 60 + m] = r
    return out


def legs(ms, sp):
    """a zigzag over the whole day (a description of what happened, not a signal): [(start_m, end_m, dir)]"""
    thr = LEG * sp[ms[0]]
    out, piv, pm, d = [], sp[ms[0]], ms[0], 0
    ext, em = piv, pm
    for m in ms[1:]:
        x = sp[m]
        if d >= 0 and x > ext:
            ext, em = x, m
        if d <= 0 and x < ext:
            ext, em = x, m
        if d == 0 and abs(x - piv) >= thr:
            d = 1 if x > piv else -1
            ext, em = x, m
        elif d == 1 and ext - x >= thr:
            out.append((pm, em, 1)); piv, pm, d, ext, em = ext, em, -1, x, m
        elif d == -1 and x - ext >= thr:
            out.append((pm, em, -1)); piv, pm, d, ext, em = ext, em, 1, x, m
    if d and abs(ext - piv) >= thr:
        out.append((pm, em, d))
    return out


def leg_of(r, k, side):
    for s in r.get("strikes") or []:
        if s.get("k") == k:
            return s.get(side) or {}
    return {}


def window(r, n=2):
    """the ATM ± n strikes of this row, PINNED by the caller so a moving price does not slide the window"""
    atm = r.get("atm")
    ks = sorted({s["k"] for s in r.get("strikes") or []})
    if atm not in ks:
        return None
    i = ks.index(atm)
    return ks[max(0, i - n): i + n + 1]


def near(r, side, ks):
    """OI change since the open summed over the pinned strikes ks"""
    if not ks:
        return None
    tot = 0
    for k in ks:
        g = leg_of(r, k, side)
        if g.get("oi_chg") is None:
            return None
        tot += g["oi_chg"]
    return tot


def straddle(r):
    ce, pe = leg_of(r, r.get("atm"), "ce"), leg_of(r, r.get("atm"), "pe")
    return (ce.get("ltp") or 0) + (pe.get("ltp") or 0) if ce.get("ltp") and pe.get("ltp") else None


def iv(r):
    ce, pe = leg_of(r, r.get("atm"), "ce"), leg_of(r, r.get("atm"), "pe")
    xs = [x for x in (ce.get("iv"), pe.get("iv")) if x]
    v = sum(xs) / len(xs) if xs else None
    return None if v is None else v * 100 if v < 3 else v       # vol points


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def main():
    print("day        start  dir  size | 30 min before: range30 vs day-typical  straddle  IV   CALL near  PUT near  | push: first 3-min bar >= 2x the coil's | first 5 min: CALL near  PUT near")
    for day in DAYS:
        R = minutes(day)
        if not R:
            continue
        ms = sorted(R)
        sp = {m: R[m]["spot"] for m in ms}
        for a, b, d in legs(ms, sp):
            size = sp[b] - sp[a]
            pre = [m for m in ms if a - PRE <= m <= a]
            if len(pre) < 20:
                print(f"{day} {hm(a)}  {'▲' if d > 0 else '▼'}  {size:+5.0f} | (record too short before it)")
                continue
            rng30 = max(sp[m] for m in pre) - min(sp[m] for m in pre)
            earlier = [m for m in ms if ms[0] + PRE <= m <= a - PRE]
            rolls = [max(sp[x] for x in ms if m - PRE <= x <= m) - min(sp[x] for x in ms if m - PRE <= x <= m) for m in earlier]
            typ = st.median(rolls) if len(rolls) >= 5 else None
            s0, s1 = straddle(R[pre[0]]), straddle(R[a])
            v0, v1 = iv(R[pre[0]]), iv(R[a])
            ks = window(R[a])                                      # the strikes at the leg's start, held for before AND after
            c0, c1, p0, p1 = near(R[pre[0]], "ce", ks), near(R[a], "ce", ks), near(R[pre[0]], "pe", ks), near(R[a], "pe", ks)
            def bars(lo, hi):
                out = []
                for m in range(lo, hi, 3):
                    xs = [sp[x] for x in ms if m <= x < m + 3]
                    if xs:
                        out.append((m, max(xs) - min(xs)))
                return out
            coil = [r for _, r in bars(a - PRE, a)]
            base = st.median(coil) if coil else None
            push = next(((m, r) for m, r in bars(a, min(b, a + 30)) if base is not None and r >= 2 * max(base, 1)), None)
            a5 = min((m for m in ms if m >= a + 5), default=None)
            n5c, n5p = (near(R[a5], "ce", ks), near(R[a5], "pe", ks)) if a5 else (None, None)
            cc = n5c - c1 if None not in (n5c, c1) else None
            pc = n5p - p1 if None not in (n5p, p1) else None
            L = lambda x: "   ?   " if x is None else f"{x / 1e5:+6.1f}L"
            print(f"{day} {hm(a)}  {'▲' if d > 0 else '▼'}  {size:+5.0f} | "
                  f"{rng30:5.0f} vs {('%5.0f' % typ) if typ else '  ?  '} pts   "
                  f"{('%+6.1f' % (s1 - s0)) if s0 and s1 else '   ?  '}   {('%+4.1f' % (v1 - v0)) if v0 and v1 else '  ? '}  "
                  f"{L(None if None in (c0, c1) else c1 - c0)}  {L(None if None in (p0, p1) else p1 - p0)} | "
                  f"{(hm(push[0]) + ' ' + ('%3.0f' % push[1]) + ' pts vs ' + ('%2.0f' % base)) if push else 'none in 30 min':>24} | {L(cc)}  {L(pc)}")


if __name__ == "__main__":
    main()
