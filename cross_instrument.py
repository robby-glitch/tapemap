"""Cross-instrument validation: run the UNCHANGED engine + band-fade scoring
on BankNifty and Sensex to test the self-calibration invariant and whether
the band-fade edge / gamma split / seller expression generalize.

Fetches ~20 recent days per instrument from Dhan (fixed-strike ATM CE/PE via
offset-band reconstruction, same as the Nifty cache), runs Session, scores
every ±2σ tag: FUT fade (+1R/-1R, 45m), BUY vs SELL option P&L, gamma-sign
split, sold-side IV rank, days-to-expiry. Prints one block per instrument.

  python cross_instrument.py

Standalone CLI; nothing imports it. Imports engine (Session, session_json).
Fetches from the Dhan API; reads no local data files (writes none).
"""

import json
import math
import statistics
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from dhanhq import DhanContext, dhanhq

from engine import Session, session_json

IST = timezone(timedelta(hours=5, minutes=30))
URL = "https://api.dhan.co/v2/charts/intraday"
F = ["open", "high", "low", "close", "iv", "oi", "volume", "strike", "spot"]
_tok = open(".dhan_token").read().strip()
_dh = dhanhq(DhanContext("1111966509", _tok))


def fut_day(sec, seg, day):
    body = json.dumps({"securityId": str(sec), "exchangeSegment": seg,
                       "instrument": "FUTIDX", "interval": "1", "oi": True,
                       "fromDate": day, "toDate": day}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "access-token": _tok})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def band(und, seg, side, off, fro, to):
    s = "ATM" if off == 0 else (f"ATM+{off}" if off > 0 else f"ATM{off}")
    for _ in range(2):
        r = _dh.expired_options_data(
            security_id=str(und), exchange_segment=seg, instrument_type="OPTIDX",
            expiry_flag="WEEK", expiry_code=1, strike=s, drv_option_type=side,
            required_data=F, from_date=fro, to_date=to, interval=1)
        if r.get("status") == "success":
            key = "ce" if side == "CALL" else "pe"
            return (r.get("data") or {}).get("data", {}).get(key, {})
        time.sleep(1)
    return {}


def bands(bars, piv):
    cv = ctpv = cvar = 0.0
    for b in bars:
        tp = (b["H"] + b["L"] + b["C"]) / 3
        cv += b["V"]
        ctpv += tp * b["V"]
        vw = ctpv / cv if cv > 0 else b["C"]
        cvar += b["V"] * (tp - vw) ** 2
        sd = math.sqrt(cvar / cv) if cv > 0 else 0
        b["VWAP"], b["U1"], b["D1"] = vw, vw + sd, vw - sd
        b["U2"], b["D2"] = vw + 2 * sd, vw - 2 * sd
        b["U3"], b["D3"] = vw + 3 * sd, vw - 3 * sd
        b.update(piv)


def piv_of(fb):
    H = max(b["H"] for b in fb)
    L = min(b["L"] for b in fb)
    C = fb[-1]["C"]
    P = (H + L + C) / 3
    return {"P": P, "R1": 2 * P - L, "S1": 2 * P - H, "R2": P + (H - L),
            "S2": P - (H - L), "R3": H + 2 * (P - L), "S3": L - 2 * (H - P)}


def run(name, fut_id, und, seg, step, alldays, prior):
    futs = {}
    for day in [prior] + alldays:
        try:
            d = fut_day(fut_id, seg, day)
            n = len(d.get("close", []) or [])
            if n >= 250:
                futs[day] = [{"T": datetime.fromtimestamp(d["timestamp"][i], IST).strftime("%H:%M"),
                              "O": d["open"][i], "H": d["high"][i], "L": d["low"][i],
                              "C": d["close"][i], "V": d["volume"][i],
                              "OI": (d.get("open_interest") or [0] * n)[i]} for i in range(n)]
        except Exception:
            pass
        time.sleep(0.18)
    to = (datetime.strptime(alldays[-1], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    def gather(sidenm):
        st = defaultdict(lambda: defaultdict(dict))
        for off in range(-8, 9):
            dd = band(und, seg, sidenm, off, prior, to)
            ts = dd.get("timestamp", [])
            for i in range(len(ts)):
                dt = datetime.fromtimestamp(ts[i], IST)
                dy, m = dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
                st[dy][dd["strike"][i]][m] = {"T": m, "O": dd["open"][i], "H": dd["high"][i],
                                              "L": dd["low"][i], "C": dd["close"][i],
                                              "V": dd["volume"][i], "OI": dd["oi"][i],
                                              "iv": dd["iv"][i]}
            time.sleep(0.18)
        return st

    ce, pe = gather("CALL"), gather("PUT")

    def pick(book, K):
        cand = sorted(book, key=lambda k: (-len(book[k]), abs(k - K)))
        p = K if K in book and len(book[K]) >= 300 else (cand[0] if cand else None)
        return [book[p][m] for m in sorted(book[p])] if p else None

    rows = []
    ran = 0
    seq = [prior] + alldays
    for day in alldays:
        pi = seq[seq.index(day) - 1]
        if day not in futs or pi not in futs:
            continue
        fut = [dict(b) for b in futs[day]]
        piv = piv_of(futs[pi])
        bands(fut, piv)
        K = round(fut[0]["O"] / step) * step
        cser, pser = pick(ce.get(day, {}), K), pick(pe.get(day, {}), K)
        if not cser or not pser:
            continue
        bands(cser, piv)
        bands(pser, piv)
        keep = ({b["T"] for b in cser} & {b["T"] for b in pser} & {b["T"] for b in fut})
        fut = [b for b in fut if b["T"] in keep]
        cser = [b for b in cser if b["T"] in keep]
        pser = [b for b in pser if b["T"] in keep]
        if len(fut) < 250:
            continue
        s = Session(day, fut, cser, pser, quiet=True, strike=float(K), t_days=1.0)
        s.run()
        js = session_json(s)
        ran += 1
        gmap = {b["t"]: (b.get("gamma") or {}) for b in js["bars"]}
        ceI = {b["T"]: i for i, b in enumerate(cser)}
        peI = {b["T"]: i for i, b in enumerate(pser)}
        R = statistics.median(
            max(x["H"] for x in fut[max(0, j - 14):j + 1])
            - min(x["L"] for x in fut[max(0, j - 14):j + 1]) for j in range(len(fut))) or 1
        wd = datetime.strptime(day, "%Y-%m-%d").weekday()
        dte = (1 - wd) % 7
        armed_lo = armed_hi = True
        for k in range(20, len(fut)):
            b = fut[k]
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
                entry = b["C"]
                out, jx = "open", min(k + 45, len(fut) - 1)
                for j in range(k + 1, min(k + 46, len(fut))):
                    fav = sgn * (fut[j]["C"] - entry)
                    if fav >= R:
                        out, jx = "win", j
                        break
                    if fav <= -R:
                        out, jx = "loss", j
                        break
                t, tx = b["T"], fut[jx]["T"]
                dbook, obook = (cser, pser) if sgn > 0 else (pser, cser)
                dI, oI = (ceI, peI) if sgn > 0 else (peI, ceI)
                if t not in dI or tx not in dI or t not in oI or tx not in oI:
                    continue
                buy = dbook[dI[tx]]["C"] - dbook[dI[t]]["C"]
                sell = obook[oI[t]]["C"] - obook[oI[tx]]["C"]
                ivI = peI if sgn > 0 else ceI
                ivm = pser if sgn > 0 else cser
                ivs = [ivm[ivI[bb["T"]]]["iv"] for bb in fut[20:k + 1] if bb["T"] in ivI]
                ive = obook[oI[t]].get("iv")
                ivr = (sum(1 for x in ivs if x <= ive) / len(ivs)) if (ivs and ive) else None
                g = gmap.get(t, {})
                netw = (g.get("w_ce", 0) or 0) + (g.get("w_pe", 0) or 0)
                rows.append({"out": out, "netw": netw, "buy": buy,
                             "sell": sell, "ivr": ivr, "dte": dte})
    return name, ran, rows


def rep(name, ran, rows):
    dec = [r for r in rows if r["out"] in ("win", "loss")]
    fwr = sum(1 for r in dec if r["out"] == "win") / len(dec) if dec else 0
    pos = [r for r in dec if r["netw"] >= -0.3]
    neg = [r for r in dec if r["netw"] < -0.3]
    pwr = sum(1 for r in pos if r["out"] == "win") / len(pos) if pos else 0
    nwr = sum(1 for r in neg if r["out"] == "win") / len(neg) if neg else 0

    def avg(rs, k):
        return statistics.mean(r[k] for r in rs) if rs else 0

    def w(rs, k):
        return sum(1 for r in rs if r[k] > 0) / len(rs) if rs else 0

    print(f"\n=== {name}: {ran} days, {len(rows)} band tags ===")
    print(f"  naked fade WR {fwr:.0%} (n{len(dec)}) | +gamma {pwr:.0%} (n{len(pos)}) "
          f"| NEG gamma {nwr:.0%} (n{len(neg)})")
    print(f"  expression: BUY opt WR {w(rows,'buy'):.0%} avg {avg(rows,'buy'):+.1f} | "
          f"SELL opt WR {w(rows,'sell'):.0%} avg {avg(rows,'sell'):+.1f}")
    hi = [r for r in rows if r["ivr"] is not None and r["ivr"] >= 0.7]
    print(f"  SELL when sold-side IV rank>=0.7: avg {avg(hi,'sell'):+.1f} (n{len(hi)}) "
          f"vs all {avg(rows,'sell'):+.1f}")
    ne = [r for r in rows if r["dte"] <= 1]
    fr = [r for r in rows if r["dte"] >= 4]
    print(f"  by dte: near(0-1) SELL avg {avg(ne,'sell'):+.1f} (n{len(ne)}) | "
          f"far(4-6) SELL avg {avg(fr,'sell'):+.1f} (n{len(fr)})")


def main():
    alldays = []
    d = datetime(2026, 6, 12, tzinfo=IST)
    end = datetime(2026, 7, 10, tzinfo=IST)
    while d <= end:
        if d.weekday() < 5:
            alldays.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    for name, fid, und, seg, step in (("BANKNIFTY", 61088, 25, "NSE_FNO", 100),
                                      ("SENSEX", 1144507, 51, "BSE_FNO", 100)):
        try:
            rep(*run(name, fid, und, seg, step, alldays, "2026-06-11"))
        except Exception as e:
            print(f"\n{name}: ERR {str(e)[:140]}")


if __name__ == "__main__":
    main()
