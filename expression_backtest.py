"""Expression backtest: at each FUT ±2σ band tag, compare three ways to
express the fade with REAL option prices from the cached Dhan days:

  FUT   - fade in futures (baseline; +1R target / -1R stop, 45m)
  BUY   - buy the directional option (CE at -2σ low, PE at +2σ high)
  SELL  - sell the inflated opposite option (PE at -2σ, CE at +2σ)

BUY/SELL exit at the same moment FUT resolves (target/stop/timeout), priced
at that bar's option close. Tracks IV at entry (causal rank vs day so far)
and at exit -> measured IV crush. Splits by gamma sign (net writer score),
IV-rank tier, and days-to-expiry (NIFTY weekly = Tuesday).

Assumptions (stated, adjustable): lot = 75; seller margin ~= Rs 1.2L/lot;
buyer margin = premium paid. No slippage/costs (same for all expressions).

  python expression_backtest.py
"""

import glob
import json
import os
import statistics
from datetime import datetime

from backtest import load_day
from engine import Session, session_json

WIN = 45
LOT = 75
SELL_MARGIN = 120000.0


def _resolve(fut, k, d, R):
    """Return (outcome, exit_bar): first bar where dir move hits +R / -R,
    else timeout bar."""
    entry = fut[k]["C"]
    last = min(k + WIN, len(fut) - 1)
    for j in range(k + 1, last + 1):
        fav = d * (fut[j]["C"] - entry)
        if fav >= R:
            return "win", j
        if fav <= -R:
            return "loss", j
    return "open", last


def scan_day(day, prev):
    fut, ce, pe, strike, hop_mins, nhops = load_day(day, prev)
    s = Session(day, fut, ce, pe, quiet=True, strike=strike, t_days=1.0)
    s.run()
    js = session_json(s)
    gmap = {b["t"]: (b.get("gamma") or {}) for b in js["bars"]}
    raw = json.load(open(f"data/backtest/opt_{day}.json"))
    iv_ce = {b["t"]: b["iv"] for b in raw["ce"]}
    iv_pe = {b["t"]: b["iv"] for b in raw["pe"]}
    cekey = {b["T"]: i for i, b in enumerate(ce)}
    pekey = {b["T"]: i for i, b in enumerate(pe)}
    R = statistics.median(
        max(x["H"] for x in fut[max(0, j - 14):j + 1])
        - min(x["L"] for x in fut[max(0, j - 14):j + 1]) for j in range(len(fut))) or 1.0
    wd = datetime.strptime(day, "%Y-%m-%d").weekday()
    dte = (1 - wd) % 7                      # days to Tuesday weekly expiry

    out = []
    armed_lo = armed_hi = True
    for k in range(20, len(fut)):
        b = fut[k]
        z = (b["C"] - b["VWAP"]) / (b["U1"] - b["VWAP"]) if b["U1"] > b["VWAP"] else 0
        if abs(z) < 1:
            armed_lo = armed_hi = True
        for side, armed, tag in ((+1, armed_lo, b["L"] <= b["D2"]),
                                 (-1, armed_hi, b["H"] >= b["U2"])):
            if not (armed and tag):
                continue
            if side > 0:
                armed_lo = False
            else:
                armed_hi = False
            t = b["T"]
            outcome, j = _resolve(fut, k, side, R)
            tx = fut[j]["T"]
            ki, pi = cekey.get(t), pekey.get(t)
            kj, pj = cekey.get(tx), pekey.get(tx)
            if None in (ki, pi, kj, pj):
                continue
            # directional option = profits if fade works; opposite = the one to sell
            dbook, obook = (ce, pe) if side > 0 else (pe, ce)
            di, dj = (ki, kj) if side > 0 else (pi, pj)
            oi_, oj = (pi, pj) if side > 0 else (ki, kj)
            buy_pl = dbook[dj]["C"] - dbook[di]["C"]
            sell_entry = obook[oi_]["C"]
            sell_pl = sell_entry - obook[oj]["C"]
            ivmap = iv_pe if side > 0 else iv_ce      # IV of the SOLD option
            ivs = [ivmap[bb["T"]] for bb in fut[20:k + 1] if bb["T"] in ivmap]
            iv_e = ivmap.get(t)
            ivr = (sum(1 for x in ivs if x <= iv_e) / len(ivs)) if (ivs and iv_e) else None
            g = gmap.get(t, {})
            out.append({
                "day": day, "t": t, "side": "LONG" if side > 0 else "SHORT",
                "out": outcome, "hold": j - k,
                "fut_pts": side * (fut[j]["C"] - fut[k]["C"]),
                "buy_pl": buy_pl, "buy_prem": dbook[di]["C"],
                "sell_pl": sell_pl, "sell_prem": sell_entry,
                "iv_rank": ivr, "iv_e": iv_e, "iv_x": ivmap.get(tx),
                "netw": (g.get("w_ce", 0) or 0) + (g.get("w_pe", 0) or 0),
                "dte": dte, "R": R})
    return out


def block(rows, label):
    if not rows:
        print(f"  {label:24} (none)")
        return
    n = len(rows)

    def stats(key):
        pl = [r[key] for r in rows]
        return (sum(1 for x in pl if x > 0) / n, statistics.mean(pl))

    fw, fa = stats("fut_pts")
    bw, ba = stats("buy_pl")
    sw, sa = stats("sell_pl")
    b_rom = statistics.mean(r["buy_pl"] / r["buy_prem"] for r in rows if r["buy_prem"] > 0) * 100
    s_rom = statistics.mean(r["sell_pl"] * LOT / SELL_MARGIN for r in rows) * 100
    print(f"  {label:24} n={n:3}")
    print(f"     FUT  scalp : WR {fw:4.0%}  avg {fa:+6.1f} pts")
    print(f"     BUY  option: WR {bw:4.0%}  avg {ba:+6.2f} pts ({b_rom:+5.1f}% of premium)")
    print(f"     SELL option: WR {sw:4.0%}  avg {sa:+6.2f} pts ({s_rom:+5.2f}% on 1.2L margin)")
    crush = [r["iv_x"] - r["iv_e"] for r in rows
             if r["iv_e"] is not None and r["iv_x"] is not None]
    if crush:
        print(f"     IV of sold option entry->exit: {statistics.mean(crush):+.2f} vol pts avg")


def main():
    days = sorted(os.path.basename(p)[4:14] for p in glob.glob("data/backtest/fut_*.json"))
    opt = {os.path.basename(p)[4:14] for p in glob.glob("data/backtest/opt_*.json")}
    days = [d for d in days if d in opt]
    rows = []
    for i in range(1, len(days)):
        try:
            rows += scan_day(days[i], days[i - 1])
        except Exception as ex:
            print(f"  {days[i]}: ERR {ex}")

    print(f"\n{'='*78}\nEXPRESSION BACKTEST — {len(days)-1} days, {len(rows)} band tags"
          f"  (lot {LOT}, sell margin 1.2L)\n{'='*78}")
    print("\nALL TAGS:")
    block(rows, "all")
    print("\nBY IV RANK OF THE SOLD OPTION (is high IV the seller's entry?):")
    block([r for r in rows if r["iv_rank"] is not None and r["iv_rank"] >= 0.7], "IV rank >=0.7 (pumped)")
    block([r for r in rows if r["iv_rank"] is not None and r["iv_rank"] < 0.7], "IV rank <0.7")
    print("\nBY GAMMA SIGN (net writer score):")
    block([r for r in rows if r["netw"] > 0.3], "+writer (pos gamma)")
    block([r for r in rows if -0.3 <= r["netw"] <= 0.3], "mid")
    block([r for r in rows if r["netw"] < -0.3], "-writer (NEG gamma)")
    print("\nBY DAYS TO EXPIRY (Tue weekly):")
    block([r for r in rows if r["dte"] <= 1], "expiry Mon/Tue (0-1d)")
    block([r for r in rows if r["dte"] >= 4], "far (4-6d)")
    print("\nWHEN THE FADE WINS vs LOSES (what each expression pays):")
    block([r for r in rows if r["out"] == "win"], "FUT resolved WIN")
    block([r for r in rows if r["out"] == "loss"], "FUT resolved LOSS")
    block([r for r in rows if r["out"] == "open"], "timeout (chop)")


if __name__ == "__main__":
    main()
