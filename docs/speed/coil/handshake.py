"""handshake.py -- order flow (NIFTY fut, Dext 1-min delta / CVD) lined up minute by minute with OI at the CALL wall and the
PUT floor, around real moves. The question (Mary 27 Oct): when flow pushes there, what moves in OI here, and the other way
round; do walls break and floors form. Read-only on data/. Rows, not rates.

    python handshake.py
"""
import json
import os

import coil_scan as C

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data")
LOT = 65                                   # NIFTY lot: Dext volumes are contracts -> lots
EVENTS = [("2026-10-26", "09:44", "10:14", "the 09:50 burst up (calls burned 207L)"),
          ("2026-10-26", "10:02", "10:30", "the 10:08 top and the turn down"),
          ("2026-10-23", "12:41", "13:11", "the 12:51 +204 leg"),
          ("2026-10-27", "14:06", "14:34", "expiry 14:16 push"),
          ("2026-10-22", "12:09", "12:51", "her chop day: the 12:21 push down that gave back 98")]


def flow(day):
    """{minute: (delta lots, cvd lots)} from Dext's 1-min NIFTY fut bars"""
    p = os.path.join(DATA, "dext", f"dext_NSE-48704_{day}.jsonl")
    out = {}
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            h, m = int(r["time"][11:13]), int(r["time"][14:16])
            out[h * 60 + m] = (r["delta"] / LOT, r["cumulative_delta"] / LOT)
    return out


def oi(r, k, side):
    g = C.leg_of(r, k, side)
    return g.get("oi_chg")


def main():
    for day, a, b, what in EVENTS:
        R, F = C.minutes(day), flow(day)
        m0, m1 = int(a[:2]) * 60 + int(a[3:]), int(b[:2]) * 60 + int(b[3:])
        ms = [m for m in sorted(R) if m0 <= m <= m1]
        r0 = R[ms[0]]
        ks = sorted({s["k"] for s in r0["strikes"]})
        s0 = r0["spot"]
        above = [k for k in ks if k >= s0][:5]
        below = [k for k in ks if k <= s0][-5:]
        wall = max(above, key=lambda k: oi(r0, k, "ce") or 0)          # the biggest CALL build above price at the start
        floor = max(below, key=lambda k: oi(r0, k, "pe") or 0)         # the biggest PUT build below price at the start
        print(f"\n== {day} {a}-{b} · {what} · start spot {s0:.0f}s · CALL wall {wall:.0f} · PUT floor {floor:.0f}")
        print("time   spot   fut Δ(2m) CVD(win) | wall CE(L) 2m   | CE biggest 2m add/cut     | floor PE(L) 2m  | PE biggest 2m add/cut")
        cvd0 = F.get(ms[0], (0, 0))[1]
        prev = None
        for m in ms[::2]:
            r = R[m]
            d2 = sum(F.get(x, (0, 0))[0] for x in (m - 1, m)) if F else None
            cvd = F.get(m, (0, cvd0))[1] - cvd0 if F else None
            def chg(side, k):
                now, was = oi(r, k, side), oi(prev, k, side) if prev else None
                return now, (now - was if None not in (now, was) else None)
            wn, wd = chg("ce", wall)
            fn, fd = chg("pe", floor)
            def biggest(side):
                if not prev:
                    return ""
                best = None
                for k in ks:
                    n, w = oi(r, k, side), oi(prev, k, side)
                    if None in (n, w):
                        continue
                    if best is None or abs(n - w) > abs(best[1]):
                        best = (k, n - w)
                return f"{best[0]:.0f} {best[1] / 1e5:+6.1f}L" if best else ""
            L = lambda x: "   ?  " if x is None else f"{x / 1e5:+6.1f}"
            print(f"{C.hm(m)} {r['spot']:7.0f}  {('%+6.0f' % d2) if d2 is not None else '   ?  '} {('%+7.0f' % cvd) if cvd is not None else '    ?  '} | "
                  f"{L(wn)} {L(wd)}   | {biggest('ce'):>16}          | {L(fn)} {L(fd)}  | {biggest('pe'):>16}")
            prev = r


if __name__ == "__main__":
    main()
