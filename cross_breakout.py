"""Coil -> breakout confluence test (the June-15 archetype).

Detects expansion THRUSTS out of compression on Nifty (bands were coiled,
then a volume-backed directional break), and asks: when BankNifty + Sensex
break the SAME way with volume at that moment, does the move RUN (continue)?
This is the momentum/continuation context where 'real moves move together'
should pay — unlike the mean-reverting band tags tested before.

Thrust @ bar k: prior compression (mean bandwidth rank over [k-20,k-5] < 0.45)
+ range expanding now (5-min range rank > 0.8) + volume (vol rank > 0.7)
+ directional break (|z| > 1.1), 30-bar cooldown. Forward 60m: 'run' if
price extends +1.5R in the break direction before -1R stop, else 'fail'/flat.
Split by how many of BankNifty/Sensex thrust the same way with volume.

Standalone CLI; nothing imports it; no project imports. Reads
data/backtest/fut_YYYY-MM-DD.json (Nifty Dhan arrays: high/low/close/volume/
timestamp). Fetches BankNifty 61088 (NSE_FNO) + Sensex 1144507 (BSE_FNO) FUT
from the Dhan API. Writes nothing.

  python cross_breakout.py
"""

import glob
import json
import math
import os
import statistics
import time
import urllib.request
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
URL = "https://api.dhan.co/v2/charts/intraday"
_tok = open(".dhan_token").read().strip()
W2 = 60      # forward window (minutes) for continuation


def fut(sec, seg, day):
    body = json.dumps({"securityId": str(sec), "exchangeSegment": seg,
                       "instrument": "FUTIDX", "interval": "1", "oi": False,
                       "fromDate": day, "toDate": day}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "access-token": _tok})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
    except Exception:
        return None
    n = len(d.get("close", []) or [])
    if n < 250:
        return None
    ts = [datetime.fromtimestamp(d["timestamp"][i], IST).strftime("%H:%M") for i in range(n)]
    cl = {ts[i]: d["close"][i] for i in range(n)}
    seen = []
    vr = {}
    for i in range(n):
        seen.append(d["volume"][i])
        vr[ts[i]] = sum(1 for x in seen if x <= d["volume"][i]) / len(seen)
    return cl, vr, ts


def nifty_bars(day):
    d = json.load(open(f"data/backtest/fut_{day}.json"))
    n = len(d["close"])
    out = []
    cv = ctpv = cvar = 0.0
    bw_seen = []
    vol_seen = []
    for i in range(n):
        h, l, c, v = d["high"][i], d["low"][i], d["close"][i], d["volume"][i]
        tp = (h + l + c) / 3
        cv += v
        ctpv += tp * v
        vw = ctpv / cv if cv > 0 else c
        cvar += v * (tp - vw) ** 2
        sd = math.sqrt(cvar / cv) if cv > 0 else 0
        bw = 4 * sd
        bw_seen.append(bw)
        bwr = sum(1 for x in bw_seen if x <= bw) / len(bw_seen)
        vol_seen.append(v)
        volr = sum(1 for x in vol_seen if x <= v) / len(vol_seen)
        out.append({"T": datetime.fromtimestamp(d["timestamp"][i], IST).strftime("%H:%M"),
                    "H": h, "L": l, "C": c, "V": v, "VWAP": vw,
                    "z": (c - vw) / sd if sd > 0 else 0, "bwr": bwr, "volr": volr})
    rr_seen = []
    for i in range(n):
        rng5 = (max(x["H"] for x in out[max(0, i - 4):i + 1])
                - min(x["L"] for x in out[max(0, i - 4):i + 1]))
        rr_seen.append(rng5)
        out[i]["rngr"] = sum(1 for x in rr_seen if x <= rng5) / len(rr_seen)
    return out


def run():
    days = sorted(os.path.basename(p)[4:14] for p in glob.glob("data/backtest/fut_*.json"))
    days = [d for d in days if "2026-06-08" <= d <= "2026-07-14"]
    recs = []
    jun15 = None
    used = 0
    for day in days:
        b = fut(61088, "NSE_FNO", day)
        time.sleep(0.15)
        s = fut(1144507, "BSE_FNO", day)
        time.sleep(0.15)
        if not b or not s:
            continue
        bnf_cl, bnf_vr, bnf_o = b
        sx_cl, sx_vr, sx_o = s
        nf = nifty_bars(day)
        used += 1
        R = statistics.median(max(x["H"] for x in nf[max(0, j - 14):j + 1])
                              - min(x["L"] for x in nf[max(0, j - 14):j + 1])
                              for j in range(len(nf))) or 1
        last = -99
        day_recs = []
        for k in range(25, len(nf) - 5):
            bar = nf[k]
            coiled = statistics.mean(x["bwr"] for x in nf[k - 20:k - 5]) < 0.45
            thrust = bar["rngr"] > 0.8 and bar["volr"] > 0.7 and abs(bar["z"]) > 1.1
            if not (coiled and thrust and k - last >= 30):
                continue
            last = k
            dirn = 1 if bar["z"] > 0 else -1
            t = bar["T"]

            def al(cl, vr, order):
                if t not in cl:
                    return False
                i = order.index(t)
                if i < 10:
                    return False
                ret = cl[t] - cl[order[i - 10]]
                return ((ret > 0) == (dirn > 0)) and ret != 0 and vr.get(t, 0) > 0.6

            nalign = int(al(bnf_cl, bnf_vr, bnf_o)) + int(al(sx_cl, sx_vr, sx_o))
            entry = bar["C"]
            out = "flat"
            for j in range(k + 1, min(k + 1 + W2, len(nf))):
                fav = dirn * (nf[j]["C"] - entry)
                if fav >= 1.5 * R:
                    out = "run"
                    break
                if fav <= -1.0 * R:
                    out = "fail"
                    break
            rec = {"day": day, "t": t, "dir": dirn, "nalign": nalign, "out": out}
            recs.append(rec)
            day_recs.append(rec)
        if day == "2026-06-15":
            jun15 = day_recs
    return used, recs, jun15


def rate(rows):
    d = [r for r in rows if r["out"] in ("run", "fail")]
    return (sum(1 for r in d if r["out"] == "run") / len(d) if d else 0), len(d), len(rows)


def main():
    used, recs, jun15 = run()
    print(f"\n{'='*72}\nCOIL->BREAKOUT CONFLUENCE — {used} days, {len(recs)} thrust events\n{'='*72}")
    print("Thrust out of compression; does it RUN (+1.5R before -1R, 60m)?\n")
    for na in (0, 1, 2):
        rows = [r for r in recs if r["nalign"] == na]
        rr, dec, tot = rate(rows)
        lbl = {0: "Nifty alone (no index follows)",
               1: "1 other index aligned + vol",
               2: "ALL 3 break together + vol"}[na]
        print(f"  {lbl:34} events={tot:3} decided={dec:3}  RUN rate {rr:.0%}")
    rr, dec, tot = rate(recs)
    print(f"\n  baseline (all thrusts): RUN rate {rr:.0%} (decided {dec})")
    if jun15 is not None:
        print(f"\n  JUN 15 (the archetype): {len(jun15)} thrust(s)")
        for r in jun15:
            print(f"    {r['t']} dir{r['dir']:+d} aligned={r['nalign']}/2 -> {r['out']}")


if __name__ == "__main__":
    main()
