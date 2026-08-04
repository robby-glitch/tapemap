"""Score the operator's FULL d3-buy management: the band-to-band trailing stop.

THE RULE, in the operator's own words (2026-08-03, answered directly):
    "i buy the extream band lets the last line of -3 band than 20 point sl and
    than i trail band to band -- when it touch the upper line -2 std i move my
    stop to -3 std band, than if price moves from -2 to -1 std / vwap
    subsequently i just move my stop to 1 band lower, and at extreams bands
    like +2 or +3 bands i move in range so just 15 points -- market can
    reverse from +3 bands as per the rule."
Clarified the same day: the 15 points trail sits below the PRICE HIGH (not the
band), and every band reference is the band's LIVE per-bar value.

ENCODED, pessimistic where a choice existed:
  * Entries are the SAME first-of-run post-09:25 BUY records rotation_score
    scored with fixed horizons -- only the management differs. d3 primary,
    d2 beside it (noise under fixed exits; the ladder is measured, not assumed).
  * Ladder d3 d2 d1 vwap u1 u2 u3, live values off each 3-min bar.
  * Initial stop: entry band's value AT ENTRY minus 20 points.
  * Stop check FIRST on every later bar: low <= stop exits at the stop (at the
    open if the bar opened through it); a bar never rungs up after piercing.
  * Rung-up on the bar's HIGH touching the next band's live value; stop = live
    value of one band below the rung. From u2 the stop also trails 15 points
    under the highest high since. The stop only ever moves up.
  * No target: a trade ends at a trailed stop or the session's last bar close.

    python trail_score.py            # the scoreboard
    python trail_score.py 2026-06-16 # trace every d3/d2 trade of one day

Futures points, no costs, fill assumed AT the stop. First measurement of the
management, not a verdict on it.
"""

import statistics as st
import sys

from rotation_score import collect
from squeeze_score import load

INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
LADDER = ("d3", "d2", "d1", "vwap", "u1", "u2", "u3")
INIT_BUF = 20.0          # points below the entry band
TIGHT_BUF = 15.0         # points below the price high once u2 is touched
TIGHT_FROM = LADDER.index("u2")


VWAP_RUNG = LADDER.index("vwap")


def simulate(bars, i, band, trace=False, patient=False):
    """One BUY trade under the ladder. -> dict or None (band missing at entry).

    patient=False -- the ladder as first answered: trail one band below the
    rung from the first rung-up onward.
    patient=True -- the operator's clarified practice (2026-08-04): below VWAP,
    if the bands are NARROW, the stop moves to ENTRY (breakeven) and waits; the
    band-to-band trail only arms once price has crossed VWAP. NARROW is defined
    as sigma (the rung spacing, u1-vwap live) < INIT_BUF -- trailing to a band
    closer than the risk accepted at entry is the thing the operator refuses to
    do. No new constant is introduced.
    """
    entry_bar = bars[i]
    entry = entry_bar["c"]
    lvl = entry_bar.get(band)
    if lvl is None:
        return None
    entry_rung = LADDER.index(band)
    rung = entry_rung
    stop = lvl - INIT_BUF
    risk = entry - stop
    hh = None                     # highest high since u2 was first touched
    if trace:
        print(f"    {entry_bar['t']} ENTER {band} @ {entry:.1f} stop {stop:.1f}")
    for j in range(i + 1, len(bars)):
        b = bars[j]
        if b["l"] <= stop:
            px = b["o"] if b["o"] < stop else stop
            if trace:
                print(f"    {b['t']} STOP @ {px:.1f} (rung {LADDER[rung]})")
            return {"entry": entry, "exit": px, "risk": risk,
                    "rung": rung, "t": b["t"], "eod": False}
        while rung + 1 < len(LADDER):
            nxt = b.get(LADDER[rung + 1])
            if nxt is None or b["h"] < nxt:
                break
            rung += 1
            if trace:
                print(f"    {b['t']} rung up -> {LADDER[rung]} (high {b['h']:.1f})")
        new_stop = stop
        if rung > entry_rung:
            u1, vw = b.get("u1"), b.get("vwap")
            sigma = (u1 - vw) if (u1 is not None and vw is not None) else None
            narrow = sigma is not None and sigma < INIT_BUF
            if patient == "hold" and rung < VWAP_RUNG:
                # diagnostic third arm: below VWAP the initial stop is simply
                # LEFT ALONE -- no breakeven, no band trail. Isolates which
                # component of the clarified rule bleeds the edge.
                pass
            elif patient is True and rung < VWAP_RUNG and narrow:
                # narrow below VWAP: breakeven and wait, never trail the band
                new_stop = max(new_stop, entry)
            else:
                below = b.get(LADDER[rung - 1])
                if below is not None:
                    new_stop = max(new_stop, below)
        if rung >= TIGHT_FROM:
            hh = b["h"] if hh is None else max(hh, b["h"])
            new_stop = max(new_stop, hh - TIGHT_BUF)
        if trace and new_stop > stop:
            print(f"    {b['t']} stop -> {new_stop:.1f}")
        stop = new_stop
    last = bars[-1]
    if trace:
        print(f"    {last['t']} EOD exit @ {last['c']:.1f} (rung {LADDER[rung]})")
    return {"entry": entry, "exit": last["c"], "risk": risk,
            "rung": rung, "t": last["t"], "eod": True}


def run(idx, trace_day=None, patient=False):
    rows, _, _ = collect(idx)
    days = load(idx)
    out = {"d3": [], "d2": []}
    for r in rows:
        if not (r["anchored"] and r["first"] and r["side"] == "BUY"):
            continue
        if r["band"] not in out:
            continue
        tr = trace_day == r["day"]
        if tr:
            print(f"  {idx} {r['day']} {r['t']} BUY {r['band']}"
                  f" [{'patient' if patient else 'ladder'}]")
        sim = simulate(days[r["day"]]["bars"], r["i"], r["band"], trace=tr,
                       patient=patient)
        if sim is None or sim["risk"] <= 0:
            continue
        pnl = sim["exit"] - sim["entry"]
        out[r["band"]].append({**sim, "pnl": pnl, "R": pnl / sim["risk"],
                               "fixed30": r["+30m"], "day": r["day"]})
    return out


def _show(label, trades):
    if not trades:
        print(f"  {label:<10} n=0")
        return
    p = [t["pnl"] for t in trades]
    R = [t["R"] for t in trades]
    f30 = [t["fixed30"] for t in trades if t["fixed30"] is not None]
    eod = sum(1 for t in trades if t["eod"])
    scratch = sum(1 for x in p if abs(x) < 1e-9)
    rungs = sorted(t["rung"] for t in trades)
    base = (f"{st.mean(f30):+7.1f}" if f30 else "    n/a")
    print(f"  {label:<12} n={len(p):<4}"
          f"P&L {st.mean(p):+7.1f} med {st.median(p):+7.1f} "
          f"hit {sum(1 for x in p if x > 0) / len(p):4.0%}   "
          f"R {st.mean(R):+5.2f} med {st.median(R):+5.2f}   "
          f"risk~{st.mean([t['risk'] for t in trades]):4.0f}p   "
          f"med rung {LADDER[rungs[len(rungs) // 2]]:<4} "
          f"EOD {eod:<3}scr {scratch:<3}[fixed+30m: {base}]")


def main():
    trace_day = sys.argv[1] if len(sys.argv) > 1 else None
    pooled = {False: {"d3": [], "d2": []}, True: {"d3": [], "d2": []}}
    for idx in INDICES:
        print(f"\n{idx}")
        for patient in (False, True):
            tag = "patient" if patient else "ladder"
            out = run(idx, trace_day, patient=patient)
            _show(f"d3 {tag}", out["d3"])
            _show(f"d2 {tag}", out["d2"])
            for k in pooled[patient]:
                pooled[patient][k].extend(out[k])
    print("\nPOOLED -- co-moving indices; a pooled effect is a warning, not a result")
    for patient in (False, True):
        tag = "patient" if patient else "ladder"
        _show(f"d3 {tag}", pooled[patient]["d3"])
        _show(f"d2 {tag}", pooled[patient]["d2"])
    print("\nSame entries rotation_score scored; only the management differs. "
          "'patient' = the operator's clarified\nrule: narrow bands below VWAP "
          "-> stop to entry and wait; the trail arms past VWAP. Futures "
          "points,\nno costs, fills assumed at the stop. scr = breakeven "
          "scratches. First measurement, not a verdict.")


if __name__ == "__main__":
    main()
