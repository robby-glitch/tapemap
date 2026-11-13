"""ruler.py -- JARVIS DECODE v5, phase 1: ONE RULER, ONE FLOW. NIFTY futures.
Spec: docs/superpowers/specs/2026-11-11-jarvis-decode-v5-design.md §4 and §5A.1 (signed 11 Nov 2026).
SHADOW: nothing live imports this yet. Pure functions over the recorders' rows, and one check to run by hand:

    python ruler.py [YYYY-MM-DD] [HH:MM]     her bands at each 3-min close and Dext's 5-min delta / CVD up to HH:MM,
                                             to hold against her chart and her Dext footprint (phase 1's "done when")

  bands   her VWAP and ±1 / 2 / 3σ: contract_bars.bands_on over the 3-min bars of the exchange's 1-min futures
          candles -- the very recurrence ZONE-3M's zone machine runs (§1r), not a second one                      [M]
  where   the location word from z = (price − VWAP) ÷ σ: VALUE (inside 1σ) · EDGE (1–2σ) · ZONE (2–3σ, her zone:
          reaching 2σ IS the event, §1b) · BEYOND (past 3σ); "bands forming" before her 09:25 anchor
  flow    Dext's footprint ONLY (handshake.dext_flow's minutes) on the 09:15 grid: delta and CVD per closed bar. A bar
          with a minute Dext has not sent is BLIND -- never our book's delta, which carried the other sign on 15 of 45
          bars on 11 Nov (NOTEPAD A269). CVD is read by its shape inside one unbroken stretch (`since`)             [M]
  noise   D, the flow noise unit: per bar, the median |delta| of today's EARLIER readable bars (U's twin, spec §4)   [M]
No threshold lives in this file: every number v5 may use is in spec §12."""
import json
import statistics
import sys
import time

import contract_bars as cb
import dext_log
import handshake

OPEN = 9 * 60 + 15
ANCHOR = 9 * 60 + 25                    # her zone anchors at 09:25 (spec §4): before it the bands are still forming
WORDS = ("VALUE", "EDGE", "ZONE")       # |z| < 1 · < 2 · < 3, else BEYOND


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def bands(ones, minutes=3):
    """`ones` = the exchange's 1-min futures candles [{t: "HH:MM", o, h, l, c, v}] -> the `minutes`-bars, each with
    vwap, u1..u3, d1..d3 as they stood at its close (causal). Exactly decode._zone_read's two calls."""
    b = cb.resample([x for x in ones or () if x], minutes)
    return cb.with_bands(b, cb.bands_on(b))


def where(px, band, minute=None):
    """{"z", "word", "side"} for a price against one bar's bands; `minute` = the clock minute of the read. None = could
    not read (no band yet, or no σ): never a word."""
    if minute is not None and minute < ANCHOR:
        return {"z": None, "word": "bands forming", "side": 0}
    vw, u1 = (band or {}).get("vwap"), (band or {}).get("u1")
    if px is None or vw is None or u1 is None or u1 <= vw:
        return None
    z = (px - vw) / (u1 - vw)
    return {"z": z, "word": next((w for k, w in enumerate(WORDS, 1) if abs(z) < k), "BEYOND"), "side": (z > 0) - (z < 0)}


def flow(candles, lot, minutes=5, upto=None):
    """Dext's 1-min candles of one contract -> its closed `minutes`-bars from 09:15, oldest first: {s (open minute), t,
    q / cq (delta and CVD in contracts, as her Dext bar statistics print them), delta / cvd (lots), since (the open of
    the unbroken stretch this CVD is readable in), miss (minutes Dext has not sent)}. A bar with a missing minute is
    BLIND: every number None; the CVD after it starts a new stretch (its level is off by the hole, its shape is not).
    `upto` = the clock minute now (a bar still open is not returned); None = up to the last minute Dext sent."""
    q = {m: v for m, v in handshake.dext_flow(candles, 1).items() if m >= OPEN}
    if not q:
        return []
    end = max(q) + 1 if upto is None else upto
    out, cq, since = [], 0, None
    for s in range(OPEN, end - minutes + 1, minutes):
        got = [q[m] for m in range(s, s + minutes) if m in q]
        if len(got) < minutes:
            since = None
            out.append({"s": s, "t": hm(s), "q": None, "cq": None, "delta": None, "cvd": None, "since": None,
                        "miss": minutes - len(got)})
            continue
        since = since or hm(s)
        cq += sum(got)
        out.append({"s": s, "t": hm(s), "q": sum(got), "cq": cq, "delta": round(sum(got) / lot),
                    "cvd": round(cq / lot), "since": since, "miss": 0})
    return out


def noise(bars):
    """D for each bar of `flow`: the median |delta| (lots) of the earlier readable bars; None while there is none."""
    out, seen = [], []
    for b in bars:
        out.append(statistics.median(seen) if seen else None)
        if b["delta"] is not None:
            seen.append(abs(b["delta"]))
    return out


def push_bars(ones, candles, lot, upto=None):
    """v5's 5-min bars for hold2.pushes -- §1m's PUSH exactly as signed, on Dext's delta: the exchange's candle (o, h, l,
    c, vol in lots) with Dext's delta, src "dext". A slot Dext is BLIND on is not a bar: no push is born from the book."""
    px = {int(b["t"][:2]) * 60 + int(b["t"][3:]): b for b in cb.resample([x for x in ones or () if x], 5)}
    return [{"s": f["s"] * 60, "o": px[f["s"]]["o"], "h": px[f["s"]]["h"], "l": px[f["s"]]["l"], "c": px[f["s"]]["c"],
             "vol": (px[f["s"]]["v"] or 0) / lot, "delta": f["delta"], "src": "dext"}
            for f in flow(candles, lot, 5, upto) if f["delta"] is not None and f["s"] in px]


def push_ref(days):
    """{"dext": §1m's push table} over `days` = {day: push_bars}, the days strictly before the one being read: Dext's
    bars ranked against Dext's own history (tools/rank_build.flow_ref, the table hold2.state reads, unchanged)."""
    import importlib.util
    import os
    m = sys.modules.get("rank_build")
    if m is None:                                   # tools/ is not a package (server._rank_mod's way)
        spec = importlib.util.spec_from_file_location(
            "rank_build", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "rank_build.py"))
        m = sys.modules["rank_build"] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    F = m.flow_ref(days)
    return {"dext": F} if F.get("size") and F.get("slot_absd") else {}


# ---- the record's side (the hand check; phase 2 passes live rows instead) ------------------------------------------------

def ones_of(day, idx="NIFTY"):
    """The exchange's 1-min futures candles as contract_bars rows: the server's saved tape (jarvis.save_tape, from 30
    Oct), else the zone machine's cached session (confluence_log.session); [] when neither holds the day."""
    import jarvis
    try:
        with open(jarvis.tape_path(day, idx), encoding="utf-8") as f:
            tape = json.load(f)
    except (OSError, ValueError):
        import confluence_log
        return [b for b in (confluence_log.session(idx, day) or {}).get("ones") or [] if b.get("t", "") >= "09:15"]
    return [{"t": k, "o": b[0], "h": b[1], "l": b[2], "c": b[3], "v": b[4], "oi": b[5]}
            for k, b in sorted(tape.items()) if k >= "09:15"]


def dext_tag(day, idx="NIFTY"):
    """Dext's name for the contract our own record traded that day (dext_parity's rule: the book's own `ik`)."""
    import ux_log
    ik = next((b.get("ik") for b in ux_log.read_bars(day, idx) if isinstance(b, dict) and b.get("ik")), None)
    return f"NSE-{ik.split('|')[1]}" if isinstance(ik, str) and ik.startswith("NSE_FO|") else None


def main(argv):
    import rank
    import tape_log
    import v2feed
    day = next((a for a in argv[1:] if len(a) == 10 and a[4] == "-"), time.strftime("%Y-%m-%d"))
    at = next((a for a in argv[1:] if len(a) == 5 and a[2] == ":"), None)
    upto = int(at[:2]) * 60 + int(at[3:]) if at else None
    if upto is None and day == time.strftime("%Y-%m-%d"):          # live: a bar still open is never printed
        upto = int(time.strftime("%H")) * 60 + int(time.strftime("%M"))
    lot, tag = v2feed.LOTS["NIFTY"], dext_tag(day)
    print(f"RULER · NIFTY fut · {day}{' · up to ' + at if at else ''} · lot {lot} · Dext contract {tag or '?'}")
    B = [b for b in bands(ones_of(day)) if upto is None or int(b["t"][:2]) * 60 + int(b["t"][3:]) + 3 <= upto]
    print("\nHER BANDS at the 3-min close (futures) [M]" if B else "\nHER BANDS: no saved 1-min futures tape for this day")
    if B:
        print("  bar     close      VWAP        ±1σ                  ±2σ (her zone)        ±3σ                where")
    for b in B[-6:]:
        m = int(b["t"][:2]) * 60 + int(b["t"][3:]) + 3
        w = where(b["c"], b, m)
        f = lambda k: f"{b[k]:,.1f}"                                                                # noqa: E731
        print(f"  {b['t']}  {b['c']:>9,.1f}  {f('vwap'):>9}  {f('d1')} / {f('u1')}  {f('d2')} / {f('u2')}  "
              f"{f('d3')} / {f('u3')}  " + ("?" if not w else w["word"] + ("" if w["z"] is None else f" z {w['z']:+.2f}")))
    F = flow(dext_log.read_candles(tag, day), lot, 5, upto) if tag else []
    print("\nDEXT FLOW, 5-min closed bars [M]" if F else "\nDEXT FLOW: BLIND — no Dext candles for this contract and day")
    if F:
        print("  bar     delta (contracts / lots)     CVD (contracts / lots)     D (lots)   stretch from")
    for b, d in list(zip(F, noise(F)))[-12:]:
        print(f"  {b['t']}  BLIND — Dext is missing {b['miss']} of its 5 minutes" if b["delta"] is None else
              f"  {b['t']}  {b['q']:>+10,} / {b['delta']:>+6,}       {b['cq']:>+11,} / {b['cvd']:>+7,}   "
              f"{'—' if d is None else format(d, ',.0f'):>8}   {b['since']}")
    if F:                              # the fold against the bars Dext's own face posted (the decoder's 5-min bars)
        face = {b["s"] // 60: b["delta"] for b in rank.bars_of(tape_log.read_bars(day, "NIFTY"), 5)
                if isinstance(b.get("delta"), (int, float))}
        both = [(b, face[b["s"]]) for b in F if b["delta"] is not None and b["s"] in face]
        off = [(b, x) for b, x in both if abs(b["delta"] - x) > 1]
        print(f"\nCHECK against the tape Dext's face posted: {len(both)} bars on both, {len(both) - len(off)} equal, "
              f"{len(off)} differ" + "".join(f"\n  {b['t']}  ruler {b['delta']:+,}  face {x:+,.0f}" for b, x in off[:8]))
        print(f"BLIND bars: {sum(b['delta'] is None for b in F)} of {len(F)}")
    if "push" in argv[1:] and tag:     # §1m's PUSH on Dext's delta, ranked against Dext's own earlier days
        import glob
        import os
        import hold2
        prior = sorted({os.path.basename(p)[-16:-6] for p in glob.glob(os.path.join(dext_log.DIR, "dext_NSE-*_*.jsonl"))
                        if "ohlc" not in os.path.basename(p)} - {day})
        ref = push_ref({d: push_bars(ones_of(d), dext_log.read_candles(dext_tag(d), d), lot)
                        for d in prior if d < day and dext_tag(d)})
        P = hold2.pushes(push_bars(ones_of(day), dext_log.read_candles(tag, day), lot, upto), ref)
        print(f"\nPUSH (§1m, unchanged) on Dext's delta · table from {len((ref.get('dext') or {}).get('days') or [])} "
              f"earlier Dext days [M]" + ("" if ref else " — no table: fewer than one full earlier day"))
        for p in P:
            line = p["origin"] - p["d"] * hold2.TRAIL_U * p["U"]
            print(f"  {p['t']}  {'▲' if p['d'] > 0 else '▼'}  origin {p['origin']:,.1f}f  size {p['size']:.2f}  R {p['R']:.2f}  "
                  f"U {p['U']:.1f}  line {line:,.1f}f")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
