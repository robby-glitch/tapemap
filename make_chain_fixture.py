"""Generate data/chain_sample.jsonl — a deterministic synthetic option-chain
session for developing/demoing the chain analyser with no Dhan token.

Scenario (90 minutes, one snapshot per 5s, seeded RNG):
  A 09:15-09:45  calm: spot oscillates ~24250; writers grind OI into
                 CE 24400/24500 and PE 24100/24200 while premiums decay.
                 Squeeze must stay quiet here (calm half of the unit test).
  B 09:45-10:15  rally to ~24460: CE 24400 goes ITM, its premium rips,
                 writer OI unwinds fast -> UP-squeeze must fire.
  C 10:15-10:45  plateau just under 24450: unwind decelerates.

Premiums are Black-76 prices (gamma.bs_price) from a skewed IV surface, so
IV solving, GEX and writer classification all see internally consistent
numbers. Run:  python make_chain_fixture.py
"""

import json
import math
import random
from pathlib import Path

from gamma import bs_price

OUT = Path(__file__).parent / "data" / "chain_sample.jsonl"
STEP = 100
STRIKES = list(range(23900, 24701, STEP))
T0 = 1.5 / 365.0            # 1.5 days to expiry at open
DAY_YEARS = 1.0 / 365.0
START_SEC = 9 * 3600 + 15 * 60
SNAP_S = 5
N = (90 * 60) // SNAP_S      # 90 minutes


def spot_path(i):
    """Deterministic spot: calm -> rally -> plateau, with small wiggle."""
    t = i * SNAP_S / 60.0                     # minutes since open
    wig = 0.8 * math.sin(i / 7.0) + 0.5 * math.sin(i / 2.3)
    if t < 30:
        base = 24252.0 - t * 0.2              # gentle bleed: writers in charge
    elif t < 60:
        base = 24246.0 + (t - 30) / 30.0 * 214.0      # ramp to 24460
    else:
        base = 24458.0
    return base + wig


def iv_for(k, spot, i):
    """Skewed smile, drifting softly down in phase A, popping in the rally."""
    t = i * SNAP_S / 60.0
    money = (k - spot) / spot
    smile = 0.115 + 0.35 * money * money * 100     # gentle parabola
    skew = -0.25 * money                           # puts richer
    drift = -0.012 * min(t, 30) / 30.0             # A: sellers pressing IV
    pop = 0.020 * max(0.0, min((t - 30) / 15.0, 1.0)) if t >= 30 else 0.0
    return max(0.07, smile + skew + drift + pop)


def main():
    rng = random.Random(7)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    oi = {}                    # (k, side) -> running OI
    oi0 = {}                   # day-open OI baseline for oi_chg
    for k in STRIKES:
        for side in ("ce", "pe"):
            dist = abs(k - 24250) / STEP
            base = int(2.2e6 * math.exp(-0.35 * dist)) + 250_000
            oi[(k, side)] = base
            oi0[(k, side)] = base

    with OUT.open("w", encoding="utf-8") as f:
        for i in range(N):
            sec = START_SEC + i * SNAP_S
            spot = spot_path(i)
            t_min = i * SNAP_S / 60.0
            T = max(T0 - (t_min / (6.25 * 60)) * DAY_YEARS * 0.26, 1e-4)
            atm = int(round(spot / STEP) * STEP)

            for k in STRIKES:
                # phase A: writers build the wings, small random jitter
                if t_min < 30:
                    if k in (24400, 24500):
                        oi[(k, "ce")] += rng.randint(1200, 2600)
                    if k in (24100, 24200):
                        oi[(k, "pe")] += rng.randint(1200, 2600)
                # phase B: trapped CE 24400 (and some 24500) writers run
                elif t_min < 60:
                    if k == 24400:
                        oi[(k, "ce")] -= rng.randint(2500, 5200)
                    if k == 24500:
                        oi[(k, "ce")] -= rng.randint(800, 1800)
                    if k == 24300:
                        oi[(k, "pe")] += rng.randint(800, 1800)
                # phase C: unwind decelerates
                else:
                    if k == 24400:
                        oi[(k, "ce")] -= rng.randint(200, 700)
                for side in ("ce", "pe"):
                    oi[(k, side)] = max(oi[(k, side)], 50_000)

            rows = []
            for k in STRIKES:
                iv = iv_for(k, spot, i)
                row = {"k": k}
                for side, kind in (("ce", "C"), ("pe", "P")):
                    px = bs_price(spot, k, iv, T, kind)
                    px = max(round(px + rng.uniform(-0.05, 0.05), 2), 0.05)
                    row[side] = {
                        "ltp": px,
                        "oi": oi[(k, side)],
                        "oi_chg": oi[(k, side)] - oi0[(k, side)],
                        "iv": round(iv, 4),
                        "vol": int(abs(oi[(k, side)] - oi0[(k, side)]) * 1.6)
                               + 40_000,
                        "bid": round(px - 0.1, 2), "ask": round(px + 0.1, 2),
                        "avg": round(px * 1.04, 2),
                        "gamma": None, "delta": None,
                    }
                rows.append(row)

            h, rem = divmod(sec, 3600)
            m, s = divmod(rem, 60)
            f.write(json.dumps({
                "ts": f"{h:02d}:{m:02d}:{s:02d}", "sec": sec, "T": round(T, 6),
                "spot": round(spot, 1), "atm": atm, "strikes": rows,
            }) + "\n")

    print(f"wrote {N} snapshots -> {OUT}")


if __name__ == "__main__":
    main()
