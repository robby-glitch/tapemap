"""Prototype backtest of the BAND-REVERSAL setup on cached Dhan days.

Tests the operator's actual method in tiers, WITHOUT changing the engine:
  1. naked      - FUT tags -2s (or +2s), fade it, no confirmation
  2. +3D        - AND CE/PE at their opposing extremes (the yellow-arrow confluence)
  3. +confidence- AND the reverse-vs-break vote (gamma/OI/volume/trap) says reverse

Entry = close of the bar that first tags the band (one signal per excursion,
re-arms only after price returns inside +-1s). Scored forward 45m in R units
(R = median 15-min range): +1R target before -1R stop. Also reports the
operator's own management: target VWAP, stop just past the band.

  python band_backtest.py
"""

import glob
import os
import statistics

from backtest import load_day
from engine import Session, session_json

WIN = 45


def _forward(fut, k, d, R):
    entry = fut[k]["C"]
    mfe = mae = 0.0
    for j in range(k + 1, min(k + 1 + WIN, len(fut))):
        fav = d * (fut[j]["C"] - entry)
        mfe = max(mfe, fav)
        mae = min(mae, fav)
        if mfe >= R:
            return "win", mfe / R, mae / R
        if mae <= -R:
            return "loss", mfe / R, mae / R
    return "open", mfe / R, mae / R


def _vwap_target(fut, k, d, band_stop):
    """Operator's management: target VWAP, stop just past the entry band."""
    tgt = fut[k]["VWAP"]
    for j in range(k + 1, min(k + 1 + WIN, len(fut))):
        if d > 0:
            if fut[j]["L"] <= band_stop:
                return "loss"
            if fut[j]["H"] >= tgt:
                return "win"
        else:
            if fut[j]["H"] >= band_stop:
                return "loss"
            if fut[j]["L"] <= tgt:
                return "win"
    return "open"


def confidence(side, gmap_t, ev_win):
    """Reverse-vs-break vote from engine outputs. side +1 = long at -2s."""
    g = gmap_t
    reg = g.get("regime")
    wce, wpe = g.get("w_ce", 0), g.get("w_pe", 0)
    v = 0
    kinds = {(e["kind"], (e.get("data") or {}).get("side")) for e in ev_win}
    downrel = any(e["kind"] == "SQUEEZE-RELEASE" and "DOWNWARD" in e["msg"] for e in ev_win)
    uprel = any(e["kind"] == "SQUEEZE-RELEASE" and "UPWARD" in e["msg"] for e in ev_win)
    if side > 0:                                   # long, -2s reversal
        if reg in ("FLOOR", "PINNED"):
            v += 1
        if wpe > 0.25:
            v += 1                                 # put writers = floor
        if any(k0 in ("ABSORPTION", "CLIMAX") for k0, _ in kinds):
            v += 1
        if ("TRAP-SPRUNG", "BEAR") in kinds:
            v += 1                                 # bear trap sprung = bullish
        if reg == "AMPLIFIED-DOWN":
            v -= 1
        if wpe < -0.25:
            v -= 1                                 # put buyers press = fuel down
        if downrel:
            v -= 1
    else:                                          # short, +2s reversal
        if reg in ("CEILING", "PINNED"):
            v += 1
        if wce > 0.25:
            v += 1
        if any(k0 in ("ABSORPTION", "CLIMAX") for k0, _ in kinds):
            v += 1
        if ("TRAP-SPRUNG", "BULL") in kinds:
            v += 1
        if reg == "AMPLIFIED-UP":
            v -= 1
        if wce < -0.25:
            v -= 1
        if uprel:
            v -= 1
    return v


def scan_day(day, prev):
    fut, ce, pe, strike, hop_mins, nhops = load_day(day, prev)
    s = Session(day, fut, ce, pe, quiet=True, strike=strike, t_days=1.0)
    s.run()
    js = session_json(s)
    gmap = {b["t"]: (b.get("gamma") or {}) for b in js["bars"]}
    events = js["events"]
    cekey = {b["T"]: b for b in ce}
    pekey = {b["T"]: b for b in pe}
    R = statistics.median(
        max(x["H"] for x in fut[max(0, j - 14):j + 1])
        - min(x["L"] for x in fut[max(0, j - 14):j + 1]) for j in range(len(fut))) or 1.0

    sigs = []
    armed_lo = armed_hi = True
    for k in range(20, len(fut)):
        b = fut[k]
        z = (b["C"] - b["VWAP"]) / (b["U1"] - b["VWAP"]) if b["U1"] > b["VWAP"] else 0
        if abs(z) < 1:
            armed_lo = armed_hi = True
        if armed_lo and b["L"] <= b["D2"]:
            armed_lo = False
            t = b["T"]
            cb, pb = cekey.get(t), pekey.get(t)
            conf3d = bool(cb and pb and cb["L"] <= cb["D2"] and pb["H"] >= pb["U2"])
            ev_win = [e for e in events if e["t"] <= t][-8:]
            cv = confidence(+1, gmap.get(t, {}), ev_win)
            out, mfe, mae = _forward(fut, k, +1, R)
            cont = _forward(fut, k, -1, R)[0]        # continuation (keep falling)
            vout = _vwap_target(fut, k, +1, b["D2"] - 0.3 * R)
            g = gmap.get(t, {})
            sigs.append({"t": t, "side": "LONG", "deep3": b["L"] <= b["D3"],
                         "conf3d": conf3d, "vote": cv, "out": out, "cont": cont,
                         "mfe": mfe, "mae": mae, "vout": vout,
                         "reg": g.get("regime"), "netw": g.get("w_ce", 0) + g.get("w_pe", 0)})
        if armed_hi and b["H"] >= b["U2"]:
            armed_hi = False
            t = b["T"]
            cb, pb = cekey.get(t), pekey.get(t)
            conf3d = bool(cb and pb and cb["H"] >= cb["U2"] and pb["L"] <= pb["D2"])
            ev_win = [e for e in events if e["t"] <= t][-8:]
            cv = confidence(-1, gmap.get(t, {}), ev_win)
            out, mfe, mae = _forward(fut, k, -1, R)
            cont = _forward(fut, k, +1, R)[0]        # continuation (keep rising)
            vout = _vwap_target(fut, k, -1, b["U2"] + 0.3 * R)
            g = gmap.get(t, {})
            sigs.append({"t": t, "side": "SHORT", "deep3": b["H"] >= b["U3"],
                         "conf3d": conf3d, "vote": cv, "out": out, "cont": cont,
                         "mfe": mfe, "mae": mae, "vout": vout,
                         "reg": g.get("regime"), "netw": g.get("w_ce", 0) + g.get("w_pe", 0)})
    return sigs


def tally(rows, label):
    if not rows:
        print(f"  {label:22} (none)")
        return
    w = sum(r["out"] == "win" for r in rows)
    l = sum(r["out"] == "loss" for r in rows)
    o = sum(r["out"] == "open" for r in rows)
    dec = w + l
    vw = sum(r["vout"] == "win" for r in rows)
    vl = sum(r["vout"] == "loss" for r in rows)
    vdec = vw + vl
    print(f"  {label:22} n={len(rows):3}  +1R/-1R WR {(w/dec if dec else 0):.0%} "
          f"(w{w} l{l} o{o}) | VWAP-tgt WR {(vw/vdec if vdec else 0):.0%} (n{vdec}) | "
          f"MFE {statistics.mean(r['mfe'] for r in rows):+.2f} "
          f"MAE {statistics.mean(r['mae'] for r in rows):+.2f}")


def main():
    days = sorted(os.path.basename(p)[4:14] for p in glob.glob("data/backtest/fut_*.json"))
    opt = {os.path.basename(p)[4:14] for p in glob.glob("data/backtest/opt_*.json")}
    days = [d for d in days if d in opt]
    allsig = []
    for i in range(1, len(days)):
        try:
            allsig += scan_day(days[i], days[i - 1])
        except Exception as ex:
            print(f"  {days[i]}: ERR {ex}")

    print(f"\n{'='*84}\nBAND-REVERSAL prototype — {len(days)-1} unseen days, "
          f"{len(allsig)} band tags\n{'='*84}")
    print("\nTIER 1 - naked band tag (fade every touch):")
    tally(allsig, "all -2s/+2s")
    tally([r for r in allsig if r["deep3"]], "deep 3s only")

    print("\nTIER 2 - + 3D confluence (CE & PE at opposing extremes):")
    tally([r for r in allsig if r["conf3d"]], "with 3D confluence")
    tally([r for r in allsig if not r["conf3d"]], "without confluence")

    print("\nTIER 3 - + confidence vote (gamma/OI/volume/trap):")
    tally([r for r in allsig if r["vote"] >= 2], "vote >=2 (high)")
    tally([r for r in allsig if r["vote"] == 1], "vote =1 (medium)")
    tally([r for r in allsig if r["vote"] <= 0], "vote <=0 (skip)")

    print("\nBEST STACK - 3D confluence AND vote>=2:")
    tally([r for r in allsig if r["conf3d"] and r["vote"] >= 2], "full setup")

    def wr(rows, key):
        d = [r for r in rows if r[key] in ("win", "loss")]
        return (sum(r[key] == "win" for r in d) / len(d)) if d else 0, len(d)

    def split(rows, label):
        fw, fn = wr(rows, "out")       # fade / mean-reversion
        cw, cn = wr(rows, "cont")      # continuation
        print(f"  {label:26} n={len(rows):3}  FADE WR {fw:.0%} (n{fn})  |  "
              f"CONTINUATION WR {cw:.0%} (n{cn})")

    print("\nGAMMA SIGN — does fade win in +gamma and continuation in -gamma?")
    print(" by regime:")
    split([r for r in allsig if r["reg"] in ("PINNED", "FLOOR", "CEILING")],
          "+gamma (PIN/FLOOR/CEIL)")
    split([r for r in allsig if r["reg"] in ("AMPLIFIED-UP", "AMPLIFIED-DOWN")],
          "-gamma (AMPLIFIED)")
    split([r for r in allsig if r["reg"] in (None, "NEUTRAL")], "neutral")
    print(" by net writer score (w_ce+w_pe):")
    split([r for r in allsig if r["netw"] > 0.3], "+writer (>0.3, damp)")
    split([r for r in allsig if r["netw"] < -0.3], "-writer (<-0.3, amp)")
    split([r for r in allsig if -0.3 <= r["netw"] <= 0.3], "mid (-0.3..0.3)")


if __name__ == "__main__":
    main()
