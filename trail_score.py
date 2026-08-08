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

import band_rotation as br
from rotation_score import collect
from squeeze_score import load

INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
# The three management arms. "hold" was implemented in `simulate` from the
# start but never wired into main, so the operator's OWN chosen management --
# leave the stop alone until VWAP -- was the one arm never printed.
ARMS = (False, True, "hold")
ARM_TAG = {False: "ladder", True: "patient", "hold": "hold"}
LADDER = ("d3", "d2", "d1", "vwap", "u1", "u2", "u3")
# The SHORT mirror: the same rungs walked the other way. Written 2026-08-08 to
# measure the u3 SELL side under the management the operator ACTUALLY uses --
# the first sell run scored a fixed 30-minute exit, which section 1's own table
# lists as measured and NOT adopted (CHECKLIST C13).
LADDER_SELL = tuple(reversed(LADDER))
INIT_BUF = 20.0          # points below the entry band
TIGHT_BUF = 15.0         # points below the price high once u2 is touched
TIGHT_FROM = LADDER.index("u2")


VWAP_RUNG = LADDER.index("vwap")


def simulate(bars, i, band, trace=False, patient=False, side="BUY"):
    """One trade under the ladder. -> dict or None (band missing at entry).

    `side="SELL"` walks the SAME ladder downward: the stop sits ABOVE the entry
    band, a rung is taken when the LOW reaches the next rung down, and the
    tighten tracks the lowest low instead of the highest high. One function,
    two directions -- a second copy of a manager drifts, and this project has
    paid for that twice already (the 09:25 gate, and trigger_log reading a
    different rule from the one the chart draws).

    patient=False -- the ladder as first answered: trail one band below the
    rung from the first rung-up onward.
    patient=True -- the operator's clarified practice (2026-08-04): below VWAP,
    if the bands are NARROW, the stop moves to ENTRY (breakeven) and waits; the
    band-to-band trail only arms once price has crossed VWAP. NARROW is defined
    as sigma (the rung spacing, u1-vwap live) < INIT_BUF -- trailing to a band
    closer than the risk accepted at entry is the thing the operator refuses to
    do. No new constant is introduced.
    """
    sell = str(side).upper() == "SELL"
    ladder = LADDER_SELL if sell else LADDER
    tight_from = ladder.index("d2" if sell else "u2")
    vwap_rung = ladder.index("vwap")
    entry_bar = bars[i]
    entry = entry_bar["c"]
    lvl = entry_bar.get(band)
    if lvl is None:
        return None
    entry_rung = ladder.index(band)
    rung = entry_rung
    stop = (lvl + INIT_BUF) if sell else (lvl - INIT_BUF)
    risk = (stop - entry) if sell else (entry - stop)
    hh = None                     # extreme since the tighten rung was touched
    if trace:
        print(f"    {entry_bar['t']} ENTER {band} @ {entry:.1f} stop {stop:.1f}")
    for j in range(i + 1, len(bars)):
        b = bars[j]
        hit = (b["h"] >= stop) if sell else (b["l"] <= stop)
        if hit:
            px = b["o"] if ((b["o"] > stop) if sell else (b["o"] < stop)) else stop
            if trace:
                print(f"    {b['t']} STOP @ {px:.1f} (rung {ladder[rung]})")
            return {"entry": entry, "exit": px, "risk": risk,
                    "rung": rung, "t": b["t"], "eod": False}
        while rung + 1 < len(ladder):
            nxt = b.get(ladder[rung + 1])
            reached = False if nxt is None else (b["l"] <= nxt if sell else b["h"] >= nxt)
            if not reached:
                break
            rung += 1
            if trace:
                px_ = b["l"] if sell else b["h"]
                print(f"    {b['t']} rung up -> {ladder[rung]} ({px_:.1f})")
        new_stop = stop
        if rung > entry_rung:
            # Rung spacing on the side being traded: u1-vwap for a long,
            # vwap-d1 for a short. Same quantity, measured where the trade is.
            edge_, vw = b.get("d1" if sell else "u1"), b.get("vwap")
            sigma = (abs(vw - edge_) if (edge_ is not None and vw is not None)
                     else None)
            narrow = sigma is not None and sigma < INIT_BUF
            if patient == "hold" and rung < vwap_rung:
                # diagnostic third arm: below VWAP the initial stop is simply
                # LEFT ALONE -- no breakeven, no band trail. Isolates which
                # component of the clarified rule bleeds the edge.
                pass
            elif patient is True and rung < vwap_rung and narrow:
                # narrow before VWAP: breakeven and wait, never trail the band
                new_stop = min(new_stop, entry) if sell else max(new_stop, entry)
            else:
                back = b.get(ladder[rung - 1])
                if back is not None:
                    new_stop = min(new_stop, back) if sell else max(new_stop, back)
        if rung >= tight_from:
            if sell:
                hh = b["l"] if hh is None else min(hh, b["l"])
                new_stop = min(new_stop, hh + TIGHT_BUF)
            else:
                hh = b["h"] if hh is None else max(hh, b["h"])
                new_stop = max(new_stop, hh - TIGHT_BUF)
        if trace and ((new_stop < stop) if sell else (new_stop > stop)):
            print(f"    {b['t']} stop -> {new_stop:.1f}")
        stop = new_stop
    last = bars[-1]
    if trace:
        print(f"    {last['t']} EOD exit @ {last['c']:.1f} (rung {ladder[rung]})")
    return {"entry": entry, "exit": last["c"], "risk": risk,
            "rung": rung, "t": last["t"], "eod": True}


def _new_rows(idx):
    """Entries from the operator's ACTUAL two-candle rule (§5c), in the shape
    `run` already consumes.

    The detector has already applied the 09:25 gate, the reference walk, the
    window and the re-fire lock, so `anchored`/`first` are True BY
    CONSTRUCTION here rather than filtered afterwards -- unlike the one-candle
    path, where both are measurement choices made in rotation_score."""
    days = load(idx)
    rows = []
    for day, D in sorted(days.items()):
        bars = D["bars"]
        if not bars:
            continue
        close = [b["c"] for b in bars]
        for rec in br.detect_index_run(bars, stop_pts=INIT_BUF):
            if rec is None:
                continue
            i = rec["i"]
            j = i + 10                       # +30m on 3-minute bars
            rows.append({"day": day, "t": rec["t"], "i": i, "side": "BUY",
                         "band": rec["band"], "anchored": True, "first": True,
                         "+30m": None if j >= len(close) else close[j] - close[i]})
    return rows


def run(idx, trace_day=None, patient=False, rule="old"):
    rows = collect(idx)[0] if rule == "old" else _new_rows(idx)
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
                  f" [{ARM_TAG[patient]}]")
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
    for rule in ("old", "new"):
        head = ("OLD one-candle entries (research-findings §1, VOID)"
                if rule == "old"
                else "NEW two-candle entries -- the operator's rule (§5c)")
        print(f"\n{'=' * 72}\n{head}")
        # The new rule is d3 BUY only by construction, so its d2 bucket is
        # always empty and printing it would read as a measured zero.
        bands = ("d3", "d2") if rule == "old" else ("d3",)
        pooled = {a: {b: [] for b in bands} for a in ARMS}
        for idx in INDICES:
            print(f"\n{idx}")
            for patient in ARMS:
                out = run(idx, trace_day, patient=patient, rule=rule)
                for b in bands:
                    _show(f"{b} {ARM_TAG[patient]}", out[b])
                    pooled[patient][b].extend(out[b])
        print("\nPOOLED -- co-moving indices; a pooled effect is a warning, "
              "not a result")
        for patient in ARMS:
            for b in bands:
                _show(f"{b} {ARM_TAG[patient]}", pooled[patient][b])
    print("\nOnly the management differs within each block; the entries are "
          "fixed.\n"
          "  ladder  = trail band-to-band from the first rung up\n"
          "  patient = narrow bands below VWAP -> stop to entry and wait\n"
          "  hold    = the operator's own rule: leave the initial stop ALONE "
          "until VWAP,\n            then trail. Implemented from the start but "
          "never printed until now.\n"
          "Futures points, no costs, fills assumed AT the stop. scr = "
          "breakeven scratches.")


if __name__ == "__main__":
    main()
