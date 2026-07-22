"""Backtest harness for the TapeMap engine on unseen days.

Loads cached Dhan data (data/backtest/fut_*.json + opt_*.json), rebuilds the
indicator stack exactly as live.py does, applies OI-continuity correction
across rolling-ATM strike hops (a hop is NOT a real position change, so its
OI delta is zeroed), runs the UNMODIFIED engine, then scores each signal's
forward outcome in units of that day's own median range (self-calibrating).

  python backtest.py            # score all cached unseen days
  python backtest.py 2026-07-06 # one day, verbose

Honest by construction: every signal is scored against what price actually
did next; OI-derived signals firing within 2 bars of a strike hop are flagged
low-fidelity (rolling-ATM limitation, not present in clean TV-export data).
"""

import glob
import json
import math
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone

from engine import Session, session_json

IST = timezone(timedelta(hours=5, minutes=30))
BT = "data/backtest"
WIN = 45            # forward window (minutes) for directional/reversal scoring
SPENT_WIN = 30     # window to test whether a SPENT leg extended


def _fut_raw(day):
    d = json.load(open(f"{BT}/fut_{day}.json"))
    n = len(d["close"])
    oi = d.get("open_interest") or [0] * n
    out = []
    for i in range(n):
        t = datetime.fromtimestamp(d["timestamp"][i], IST).strftime("%H:%M")
        out.append({"T": t, "O": d["open"][i], "H": d["high"][i], "L": d["low"][i],
                    "C": d["close"][i], "V": d["volume"][i], "OI": oi[i]})
    return out


def _opt_raw(day, side):
    o = json.load(open(f"{BT}/opt_{day}.json"))[side]
    out = []
    adj = None
    prev_strike = prev_oi = None
    hops = 0
    for b in o:
        hop = prev_strike is not None and b["strike"] != prev_strike
        if adj is None:
            adj = b["oi"]
        elif not hop:
            adj += b["oi"] - prev_oi
        else:
            hops += 1                      # hop: carry adj (delta 0)
        prev_strike, prev_oi = b["strike"], b["oi"]
        out.append({"T": b["t"], "O": b["o"], "H": b["h"], "L": b["l"],
                    "C": b["c"], "V": b["v"], "OI": adj, "strike": b["strike"],
                    "hop": hop})
    return out, hops


def _pivots(prev_fut):
    H = max(b["H"] for b in prev_fut)
    L = min(b["L"] for b in prev_fut)
    C = prev_fut[-1]["C"]
    P = (H + L + C) / 3.0
    return {"P": P, "R1": 2 * P - L, "S1": 2 * P - H,
            "R2": P + (H - L), "S2": P - (H - L),
            "R3": H + 2 * (P - L), "S3": L - 2 * (H - P)}


def _bands(bars, piv):
    cv = ctpv = cvar = 0.0
    for b in bars:
        tp = (b["H"] + b["L"] + b["C"]) / 3.0
        cv += b["V"]
        ctpv += tp * b["V"]
        vwap = ctpv / cv if cv > 0 else b["C"]
        cvar += b["V"] * (tp - vwap) ** 2
        sd = math.sqrt(cvar / cv) if cv > 0 else 0.0
        b["VWAP"], b["U1"], b["D1"] = vwap, vwap + sd, vwap - sd
        b["U2"], b["D2"] = vwap + 2 * sd, vwap - 2 * sd
        b["U3"], b["D3"] = vwap + 3 * sd, vwap - 3 * sd
        b.update(piv)
    return bars


def _t_days(day):
    wd = datetime.strptime(day, "%Y-%m-%d").weekday()     # Mon=0
    to_tue = (1 - wd) % 7                                  # NIFTY weekly = Tue
    return (to_tue or 0.25) + 0.25


def load_day(day, prev_day):
    fut = _fut_raw(day)
    ce, ce_hops = _opt_raw(day, "ce")
    pe, pe_hops = _opt_raw(day, "pe")
    piv = _pivots(_fut_raw(prev_day))
    _bands(fut, piv)
    _bands(ce, piv)
    _bands(pe, piv)
    keep = ({b["T"] for b in ce} & {b["T"] for b in pe} & {b["T"] for b in fut})
    fut = [b for b in fut if b["T"] in keep]
    ce = [b for b in ce if b["T"] in keep]
    pe = [b for b in pe if b["T"] in keep]
    strike = round(fut[0]["O"] / 100.0) * 100.0
    hop_mins = {b["T"] for b in ce if b.get("hop")} | {b["T"] for b in pe if b.get("hop")}
    return fut, ce, pe, strike, hop_mins, ce_hops + pe_hops


def _forward(fut, k, dir_, R):
    entry = fut[k]["C"]
    mfe = mae = 0.0
    for j in range(k + 1, min(k + 1 + WIN, len(fut))):
        fav = dir_ * (fut[j]["C"] - entry)
        mfe = max(mfe, fav)
        mae = min(mae, fav)
        if mfe >= R:
            return "win", mfe / R, mae / R
        if mae <= -R:
            return "loss", mfe / R, mae / R
    return "open", mfe / R, mae / R


def _lean(regime):
    return {"FLOOR": 1, "AMPLIFIED-UP": 1,
            "CEILING": -1, "AMPLIFIED-DOWN": -1}.get(regime, 0)


def score_day(day, prev_day, verbose=False):
    fut, ce, pe, strike, hop_mins, nhops = load_day(day, prev_day)
    s = Session(f"{day}", fut, ce, pe, quiet=True, strike=strike,
                t_days=_t_days(day))
    s.run()
    js = session_json(s)
    bars = js["bars"]
    idx = {b["t"]: i for i, b in enumerate(bars)}
    fkey = {b["T"]: i for i, b in enumerate(fut)}
    # R = a typical short-term swing (median 15-min rolling range), so +1R is
    # a real move a trader could hold, not per-bar noise.
    rolls = [max(x["H"] for x in fut[max(0, j - 14):j + 1])
             - min(x["L"] for x in fut[max(0, j - 14):j + 1])
             for j in range(len(fut))]
    R = statistics.median(rolls) or 1.0

    recs = []
    for e in js["events"]:
        t, kind, data = e["t"], e["kind"], e.get("data") or {}
        k = fkey.get(t)
        if k is None:
            continue
        near_hop = t in hop_mins or any(bb["T"] in hop_mins for bb in fut[max(0, k - 2):k + 1])
        gam = (bars[idx[t]].get("gamma") or {}).get("regime") if t in idx else None
        dir_ = None
        cat = None
        if kind in ("ARMED", "SPRING"):
            dir_ = 1 if data.get("side") == "UP" else -1 if data.get("side") == "DN" else None
            cat = kind
        elif kind == "TRAP-SPRUNG":
            dir_ = -1 if data.get("side") == "BULL" else 1 if data.get("side") == "BEAR" else None
            cat = "TRAP-FADE"
        if dir_ is None:
            continue
        outcome, mfe, mae = _forward(fut, k, dir_, R)
        recs.append({"t": t, "cat": cat, "dir": dir_, "outcome": outcome,
                     "mfe": round(mfe, 2), "mae": round(mae, 2),
                     "lean": _lean(gam), "near_hop": near_hop})

    spent = []
    for b in bars:
        ep = (b.get("ctx") or {}).get("episode", "")
        if ep.startswith("MOVE SPENT"):
            k = fkey.get(b["t"])
            if k is None or k + 1 >= len(fut):
                continue
            legdir = 1 if " UP leg" in ep else -1
            entry = fut[k]["C"]
            ext = max(legdir * (fut[j]["C"] - entry)
                      for j in range(k + 1, min(k + 1 + SPENT_WIN, len(fut))))
            spent.append(ext < 0.5 * R)     # True = "don't chase" was correct

    carry = next((e for e in js["events"] if e["kind"] == "CARRY"), None)
    return recs, spent, carry, R, nhops, len(fut)


def main():
    days = sorted(os.path.basename(p)[4:14]
                  for p in glob.glob(f"{BT}/fut_*.json"))
    opt_days = {os.path.basename(p)[4:14]
                for p in glob.glob(f"{BT}/opt_*.json")}
    days = [d for d in days if d in opt_days]

    if len(sys.argv) > 1:
        day = sys.argv[1]
        prev = days[days.index(day) - 1]
        recs, spent, carry, R, nhops, n = score_day(day, prev, verbose=True)
        print(f"{day}: R={R:.0f}pts, {nhops} strike-hops, {n} bars")
        for r in recs:
            print(f"  {r['t']} {r['cat']:9} dir{r['dir']:+d} -> {r['outcome']:4} "
                  f"MFE{r['mfe']:+.1f}R MAE{r['mae']:+.1f}R lean{r['lean']:+d}"
                  f"{'  [near-hop]' if r['near_hop'] else ''}")
        print(f"  SPENT calls: {sum(spent)}/{len(spent)} correct")
        if carry:
            print(f"  {carry['msg'][-40:]}")
        return

    allrecs, allspent, carries, daystats = [], [], [], []
    for i in range(1, len(days)):
        day, prev = days[i], days[i - 1]
        try:
            recs, spent, carry, R, nhops, n = score_day(day, prev)
        except Exception as ex:
            print(f"  {day}: ERROR {ex}")
            continue
        for r in recs:
            r["day"] = day
        allrecs += recs
        allspent += spent
        nxt = days[i + 1] if i + 1 < len(days) else None
        carries.append((day, carry, nxt))
        daystats.append((day, len(recs), nhops))

    def tally(rows, label):
        if not rows:
            print(f"  {label:16} (none)")
            return
        w = sum(1 for r in rows if r["outcome"] == "win")
        l = sum(1 for r in rows if r["outcome"] == "loss")
        o = sum(1 for r in rows if r["outcome"] == "open")
        dec = w + l
        wr = f"{w/dec:.0%}" if dec else "n/a"
        avg_mfe = statistics.mean(r["mfe"] for r in rows)
        avg_mae = statistics.mean(r["mae"] for r in rows)
        print(f"  {label:16} n={len(rows):3}  win {w:3} loss {l:3} open {o:3}  "
              f"winrate(decided) {wr:>4}  MFE {avg_mfe:+.2f}R  MAE {avg_mae:+.2f}R")

    print(f"\n{'='*76}\nBACKTEST — {len(daystats)} unseen days "
          f"({days[1]}..{days[-1]})\n{'='*76}")
    print(f"total signals: {len(allrecs)}  |  strike-hops/day median: "
          f"{statistics.median(h for _,_,h in daystats):.0f}")

    print("\nDirectional & reversal (target +1R before -1R stop, 45m window):")
    tally([r for r in allrecs if r["cat"] == "ARMED"], "ARMED")
    tally([r for r in allrecs if r["cat"] == "SPRING"], "SPRING")
    tally([r for r in allrecs if r["cat"] == "TRAP-FADE"], "TRAP-FADE")
    tally(allrecs, "ALL signals")

    clean = [r for r in allrecs if not r["near_hop"]]
    print("\nOI-fidelity control (signals NOT within 2 bars of a strike hop):")
    tally(clean, "clean-only")
    tally([r for r in allrecs if r["near_hop"]], "near-hop")

    print("\nGamma layer (does agreeing with MM regime help? directional only):")
    dirrec = [r for r in allrecs if r["cat"] in ("ARMED", "SPRING") and r["lean"]]
    tally([r for r in dirrec if r["lean"] == r["dir"]], "signal AGREES")
    tally([r for r in dirrec if r["lean"] == -r["dir"]], "signal FIGHTS")

    if allspent:
        print(f"\nEpisode SPENT ('don't chase' correct?): {sum(allspent)}/"
              f"{len(allspent)} = {sum(allspent)/len(allspent):.0%}")

    cok = ctot = 0
    for day, carry, nxt in carries:
        if not carry or not nxt:
            continue
        bias = ("BULLISH" if "BULLISH" in carry["msg"] else
                "BEARISH" if "BEARISH" in carry["msg"] else "NEUTRAL")
        if bias == "NEUTRAL":
            continue
        nf = _fut_raw(nxt)
        moved = nf[-1]["C"] - nf[0]["O"]
        ctot += 1
        cok += (moved > 0) == (bias == "BULLISH")
    if ctot:
        print(f"CARRY next-day direction: {cok}/{ctot} correct")

    json.dump({"records": allrecs, "spent_acc":
               (sum(allspent) / len(allspent)) if allspent else None},
              open(f"{BT}/scores.json", "w"))
    print(f"\nwrote {BT}/scores.json")


if __name__ == "__main__":
    main()
