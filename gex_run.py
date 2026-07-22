"""GEX post-processor: chain_<date>.json -> gex_<date>.json (per-minute).

Reads the Dhan-fetched multi-strike chain, reproduces the Stage-1
session-cumulative writer score per strike per side (the SAME rule as
engine.GammaLayer: net OI since open, classified by premium direction since
open with a 2% relative floor, magnitude scaled by the session's own peak
build), solves BS implied vol per strike every 5 minutes (interpolated in
between, last value reused on solve failure) and emits the dealer-signed
GEX profile (gex_total, flip, walls) per minute via gamma.gex_profile.

Separate-layer rule: this never touches engine.py or base signals.

Usage: python gex_run.py [date]      (default 2026-07-17)
"""

import json
import sys
from datetime import datetime, timedelta, timezone

from gamma import gex_profile, implied_vol

IST = timezone(timedelta(hours=5, minutes=30))
IV_SOLVE_EVERY = 5          # minutes between IV solves (plan: 5-min + interp)


def t_years(date_str, hhmm, expiry_str):
    """ACT/365 year fraction from date hhmm IST to expiry 15:30 IST."""
    now = datetime.strptime(f"{date_str} {hhmm}", "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    exp = datetime.strptime(f"{expiry_str} 15:30", "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    return max((exp - now).total_seconds(), 0.0) / (365.0 * 86400.0)


def writer_scores(series):
    """Per-minute writer score for one option series (engine.GammaLayer rule).

    Robust to illiquid strikes: the session-open reference is the first
    non-None (oi, close) pair; minutes before it score 0.0."""
    pairs = list(zip(series["oi"], series["c"]))
    out = [0.0] * len(pairs)
    first = next((j for j, (oi, c) in enumerate(pairs)
                  if oi is not None and c is not None), None)
    if first is None or pairs[first][1] in (None, 0):
        return out
    oi0, px0 = pairs[first]
    build_peak = 0.0
    for j in range(first, len(pairs)):
        oi, c = pairs[j]
        if oi is None or c is None:
            out[j] = out[j - 1] if j > first else 0.0
            continue
        doi = oi - oi0
        build_peak = max(build_peak, doi)
        dpx = c - px0
        # 2% relative premium floor before calling a direction (same
        # justification as GammaLayer: avoids noise-flips near open)
        direction = 1.0 if dpx < -0.02 * px0 else \
            (-1.0 if dpx > 0.02 * px0 else 0.0)
        mag = max(doi, 0.0) / build_peak if build_peak > 0 else 0.0
        out[j] = direction * min(1.0, mag)
    return out


def iv_track(series, fut_c, k, kind, date_str, expiry, times):
    """Per-minute IV, strictly causal (architecture invariant 2): solved every
    IV_SOLVE_EVERY min, FORWARD-HELD between solves (no interpolation toward a
    future solve), None before the first successful solve."""
    n = len(times)
    track = [None] * n
    last = None
    for i in range(n):
        if i % IV_SOLVE_EVERY == 0:
            T = t_years(date_str, times[i], expiry)
            iv = implied_vol(series["c"][i], fut_c[i], k, T, kind)
            if iv is not None:
                last = iv
        track[i] = last
    return track


def run(date_str):
    chain = json.load(open(f"data/chain_{date_str}.json"))
    expiry = chain["expiry"]
    fut = chain["fut"]
    times = fut["t"]
    n = len(times)

    # align every option series onto the FUT clock (defensive: series were
    # fetched bar-perfect, but a missing minute must not shift the arrays)
    per_strike = {}
    iv_stats = []
    for ks, sides in chain["strikes"].items():
        k = float(ks)
        entry = {}
        for side in ("ce", "pe"):
            s = sides[side]
            idx = {t: j for j, t in enumerate(s["t"])}
            aligned = {key: [s[key][idx[t]] if t in idx else None for t in times]
                       for key in ("c", "oi")}
            # fill the rare missing minute by carrying the previous bar
            for key in ("c", "oi"):
                prev = None
                col = aligned[key]
                for j in range(n):
                    if col[j] is None:
                        col[j] = prev
                    prev = col[j]
            entry[side] = {
                "oi": aligned["oi"], "c": aligned["c"],
                "w": writer_scores(aligned),
                "iv": iv_track(aligned, fut["c"], k, side[0].upper(),
                               date_str, expiry, times),
            }
        per_strike[k] = entry
        for side in ("ce", "pe"):
            iv_stats.extend(v for v in entry[side]["iv"] if v is not None)

    out = {"t": list(times), "flip": [], "wall_up": [], "wall_dn": [],
           "gex_total": []}
    profiles = {}
    for i, t in enumerate(times):
        T = t_years(date_str, t, expiry)
        F = fut["c"][i]
        strikes_data = [{
            "k": k,
            "ce_oi": e["ce"]["oi"][i], "pe_oi": e["pe"]["oi"][i],
            "ce_iv": e["ce"]["iv"][i], "pe_iv": e["pe"]["iv"][i],
            "ce_w": e["ce"]["w"][i], "pe_w": e["pe"]["w"][i],
        } for k, e in sorted(per_strike.items())]
        p = gex_profile(strikes_data, F, T)
        out["flip"].append(p["flip_px"])
        out["wall_up"].append(p["wall_up"])
        out["wall_dn"].append(p["wall_dn"])
        out["gex_total"].append(p["gex_total"])
        profiles[t] = (p, F)

    path = f"data/gex_{date_str}.json"
    with open(path, "w") as f:
        json.dump(out, f)
    print(f"wrote {path} ({n} minutes)")

    # ---- validation report ----------------------------------------------
    print(f"\nIV sanity: {len(iv_stats)} minute-IVs, "
          f"min {min(iv_stats):.4f} max {max(iv_stats):.4f} "
          f"mean {sum(iv_stats)/len(iv_stats):.4f}")
    for t in ("10:00", "11:30", "13:50", "14:15", "14:30", "15:15"):
        if t not in profiles:
            continue
        p, F = profiles[t]
        fl = f"{p['flip_px']:.0f}" if p["flip_px"] is not None else "None"
        gt = f"{p['gex_total']/1e3:+.1f}k" if p["gex_total"] is not None else "None"
        print(f"{t}  F {F:7.1f}  flip {fl:>6}  wall_dn {p['wall_dn']}  "
              f"wall_up {p['wall_up']}  gex_total {gt}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "2026-07-17")
