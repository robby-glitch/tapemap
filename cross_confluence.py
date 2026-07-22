"""Cross-index confluence test: do Nifty band-fade outcomes depend on whether
BankNifty and Sensex are moving the SAME direction WITH volume?

Hypothesis (operator): a REAL move shows as all 3 indices aligned + volume;
a single-index extreme is idiosyncratic noise that reverts. So at a Nifty
±2σ tag, if the other two indices are ALSO stretched the same way with
volume (broad move) → continuation, don't fade. If Nifty is alone → fade.

Standalone CLI; nothing imports it; imports no project modules. Reads Nifty
FUT from data/backtest/fut_YYYY-MM-DD.json (Dhan arrays: high/low/close/
volume/timestamp); fetches BankNifty (61088, NSE_FNO) + Sensex (1144507,
BSE_FNO) FUT from the Dhan API (FUT only). Writes nothing.

  python cross_confluence.py
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
        return {}
    n = len(d.get("close", []) or [])
    if n < 250:
        return {}
    return {datetime.fromtimestamp(d["timestamp"][i], IST).strftime("%H:%M"):
            (d["close"][i], d["volume"][i]) for i in range(n)}


def nifty_fut(day):
    d = json.load(open(f"data/backtest/fut_{day}.json"))
    n = len(d["close"])
    out = []
    cv = ctpv = cvar = 0.0
    for i in range(n):
        h, l, c, v = d["high"][i], d["low"][i], d["close"][i], d["volume"][i]
        tp = (h + l + c) / 3
        cv += v
        ctpv += tp * v
        vw = ctpv / cv if cv > 0 else c
        cvar += v * (tp - vw) ** 2
        sd = math.sqrt(cvar / cv) if cv > 0 else 0
        out.append({"T": datetime.fromtimestamp(d["timestamp"][i], IST).strftime("%H:%M"),
                    "H": h, "L": l, "C": c, "V": v, "VWAP": vw,
                    "U1": vw + sd, "D2": vw - 2 * sd, "U2": vw + 2 * sd})
    return out


def vol_ranks(series_ct):
    ts = sorted(series_ct)
    seen = []
    out = {}
    for t in ts:
        v = series_ct[t][1]
        seen.append(v)
        out[t] = sum(1 for x in seen if x <= v) / len(seen)
    return out


def run():
    days = sorted(os.path.basename(p)[4:14] for p in glob.glob("data/backtest/fut_*.json"))
    days = [d for d in days if "2026-06-08" <= d <= "2026-07-14"]
    recs = []
    used = 0
    for day in days:
        bnf = fut(61088, "NSE_FNO", day)
        time.sleep(0.15)
        sx = fut(1144507, "BSE_FNO", day)
        time.sleep(0.15)
        if not bnf or not sx:
            continue
        nf = nifty_fut(day)
        used += 1
        bnf_vr = vol_ranks(bnf)
        sx_vr = vol_ranks(sx)
        R = statistics.median(max(x["H"] for x in nf[max(0, j - 14):j + 1])
                              - min(x["L"] for x in nf[max(0, j - 14):j + 1])
                              for j in range(len(nf))) or 1
        armed_lo = armed_hi = True
        for k in range(20, len(nf)):
            b = nf[k]
            z = (b["C"] - b["VWAP"]) / (b["U1"] - b["VWAP"]) if b["U1"] > b["VWAP"] else 0
            if abs(z) < 1:
                armed_lo = armed_hi = True
            for sgn, tag in ((+1, b["L"] <= b["D2"]), (-1, b["H"] >= b["U2"])):
                if not tag:
                    continue
                if sgn > 0 and not armed_lo:
                    continue
                if sgn < 0 and not armed_hi:
                    continue
                if sgn > 0:
                    armed_lo = False
                else:
                    armed_hi = False
                movedir = -sgn                    # move that made the extreme
                t = b["T"]

                def al(other, vr):
                    ts = sorted(other)
                    if t not in other:
                        return False
                    i = ts.index(t)
                    if i < 10:
                        return False
                    ret = other[t][0] - other[ts[i - 10]][0]
                    samedir = (ret < 0) == (movedir < 0) and ret != 0
                    return samedir and vr.get(t, 0) > 0.55

                nalign = int(al(bnf, bnf_vr)) + int(al(sx, sx_vr))
                entry = b["C"]
                out = "open"
                for j in range(k + 1, min(k + 46, len(nf))):
                    fav = sgn * (nf[j]["C"] - entry)
                    if fav >= R:
                        out = "win"
                        break
                    if fav <= -R:
                        out = "loss"
                        break
                recs.append({"nalign": nalign, "out": out})
    return used, recs


def wr(rows):
    d = [r for r in rows if r["out"] in ("win", "loss")]
    return (sum(1 for r in d if r["out"] == "win") / len(d) if d else 0), len(d)


def main():
    used, recs = run()
    print(f"\n{'='*70}\nCROSS-INDEX CONFLUENCE — {used} days, {len(recs)} Nifty band tags\n{'='*70}")
    print("At each Nifty ±2σ tag: how many of BankNifty/Sensex moved the SAME")
    print("way (into the extreme) WITH volume, and did the Nifty fade work?\n")
    for na in (0, 1, 2):
        rows = [r for r in recs if r["nalign"] == na]
        fwr, n = wr(rows)
        cwr = 1 - fwr
        lbl = {0: "0 aligned (Nifty ALONE - idiosyncratic)",
               1: "1 aligned (partial)",
               2: "2 aligned (ALL 3 + volume - broad move)"}[na]
        print(f"  {lbl:44} n={n:3}  FADE WR {fwr:.0%} | continuation {cwr:.0%}")
    allwr, alln = wr(recs)
    print(f"\n  baseline (all tags): FADE WR {allwr:.0%} (n{alln})")


if __name__ == "__main__":
    main()
