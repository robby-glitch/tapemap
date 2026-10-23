# tapemap/dext_parity.py
"""dext_parity.py -- GATE 3: Dext vs GoCharting vs Upstox, one NIFTY futures day, counts and ratios only.

    python dext_parity.py [YYYY-MM-DD]      (default today) -> data/dext/parity_<day>.json + one summary line
    GET /api/dext/parity?day=               the same report, computed on request (server.py)

D = the Dext extension's 1m candles (dext_log.py) folded into 5m bars anchored at 09:15 IST, in LOTS (contracts / lot).
U = Upstox's ladder bars (data/tape/ux_NIFTY_<day>.jsonl). G = GoCharting's (data/tape/tape_NIFTY_<day>.jsonl).

RULES, each one measured on the trader's export before it was written here:
  * Same contract or no comparison. Dext's NSE SEC_ID is the Upstox exchange token (NSE_FO|<SEC_ID>). GoCharting's
    NIFTY-I is the continuous near month, so it is compared only on days whose Upstox record is on Dext's contract.
  * The 09:15 bar is excluded: Dext and GoCharting fold the pre-open auction into it, Upstox does not. Its three
    volumes are reported on their own.
  * Dext's 15:30-15:39 minutes (NSE's closing auction session; Dext only) are excluded; their volume is reported.
  * Every pairwise number is over the bars all compared sources have; a bar one source lacks is named, not filled.
  * Cells: 5-point rows centred on multiples of 5 (round(p / 5) * 5), all volume at the price (Dext's neutral and
    Upstox's unknown-side included). POC = the heaviest such row. Move = the bar's own close - open (Dext's from getData).
Never a winner, never an accuracy verdict: the trader reads the rows.

READS ONLY: nothing TapeMap decides on reads this file or its output.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
import time
from typing import Dict, List, Optional

import dext_log
import tape_log

CC = "could not check — "
NIFTY_FUT = re.compile(r"^NIFTY [A-Z]{3} FUT$")
OPEN, CLOSE = 9 * 60 + 15, 15 * 60 + 30
PAIRS = (("D", "U"), ("D", "G"), ("U", "G"))


def _mod(t_s: int) -> int:
    """minute of the IST day"""
    return ((t_s + 19800) // 60) % 1440


def _hm(t_ms: int) -> str:
    return time.strftime("%H:%M", time.gmtime(t_ms / 1000 + 19800))


def _row5(p: float) -> float:
    return round(p / 5) * 5


def _dext_bars(candles: List[dict], ohlc: List[dict], lot: float) -> tuple:
    """1m candles -> {t_ms: bar} 5m bars 09:15..15:25, plus the 15:30+ closing-auction volume (lots, minutes)."""
    bars: Dict[int, dict] = {}
    auction, auction_n = 0.0, 0
    for c in candles:
        m = _mod(c["t"])
        if m >= CLOSE:
            auction += (c.get("total_volume") or 0) / lot
            auction_n += 1
            continue
        if m < OPEN:
            continue
        t = (c["t"] - (m - OPEN) % 5 * 60) * 1000
        b = bars.setdefault(t, {"t": t, "vol": 0.0, "buy": 0.0, "sell": 0.0, "cells": {}})
        b["vol"] += (c.get("total_volume") or 0) / lot
        b["buy"] += (c.get("buy_volume") or 0) / lot
        b["sell"] += (c.get("sell_volume") or 0) / lot
        for lv in c.get("levels") or ():
            if (lv.get("price") or 0) > 0:
                q = b["cells"].setdefault(lv["price"], [0.0, 0.0, 0.0])
                q[0] += (lv.get("total_volume") or 0) / lot
                q[1] += (lv.get("buy_volume") or 0) / lot
                q[2] += (lv.get("sell_volume") or 0) / lot
    oh = {r["t"] * 1000: r for r in ohlc}
    for b in bars.values():
        b["delta"] = b["buy"] - b["sell"]
        r = oh.get(b["t"])
        b["oi"] = r.get("oi") if r else None
        b["move"] = r["c"] - r["o"] if r and r.get("c") is not None and r.get("o") is not None else None
    return bars, auction, auction_n


def _tape_bars(rows: List[dict], with_u: bool) -> Dict[int, dict]:
    """ux / tape rows (LOTS) -> {t_ms: bar}; duplicated t: the last row wins."""
    out = {}
    for r in rows:
        if not isinstance(r.get("t"), (int, float)) or isinstance(r.get("t"), bool):
            continue
        cells = {}
        for x in r.get("ladder") or ():
            q = cells.setdefault(x["p"], [0.0, 0.0, 0.0])
            b, s = x.get("b") or 0, x.get("s") or 0
            q[0] += b + s + ((x.get("u") or 0) if with_u else 0)
            q[1] += b
            q[2] += s
        o, c = r.get("o"), r.get("c")
        out[int(r["t"])] = {"t": int(r["t"]), "vol": r.get("vol") or 0, "delta": r.get("delta") or 0, "oi": r.get("oi"),
                            "move": c - o if o is not None and c is not None else None, "cells": cells}
    return out


def _rows(cells: dict) -> Dict[float, float]:
    out: Dict[float, float] = {}
    for p, q in cells.items():
        out[_row5(p)] = out.get(_row5(p), 0.0) + q[0]
    return out


def _overlap(a: dict, b: dict) -> Optional[float]:
    ra, rb = _rows(a), _rows(b)
    ks = set(ra) | set(rb)
    mx = sum(max(ra.get(k, 0), rb.get(k, 0)) for k in ks)
    return sum(min(ra.get(k, 0), rb.get(k, 0)) for k in ks) / mx if mx else None


def _poc(cells: dict) -> Optional[float]:
    r = _rows(cells)
    return max(sorted(r), key=lambda k: r[k]) if r else None


def _corr(x: List[float], y: List[float]) -> Optional[float]:
    try:
        return round(statistics.correlation(x, y), 3)
    except (statistics.StatisticsError, ValueError, ZeroDivisionError):
        return None


def _sign(v: float) -> int:
    return (v > 0) - (v < 0)


def _pick_inst(day: str, ux_ik: Optional[str]) -> Optional[dict]:
    """The NIFTY future Dext sent candles for on `day`; the one on Upstox's contract first."""
    have = [dict(v, key=k) for k, v in dext_log.instruments().items()
            if NIFTY_FUT.match(str(v.get("name") or "")) and os.path.exists(dext_log.candles_path(k, day))]
    return next((v for v in have if f"NSE_FO|{v['SEC_ID']}" == ux_ik and v.get("SEG") == "D"), have[0] if have else None)


def report(day: str) -> dict:
    ux_rows = tape_log._read(tape_log.ux_path(day, "NIFTY"))
    ux_ik = next((r.get("ik") for r in ux_rows if r.get("ik")), None)
    inst = _pick_inst(day, ux_ik)
    if inst is None:
        return {"ok": False, "day": day, "why": CC + "no Dext candles today" if day == time.strftime("%Y-%m-%d")
                else CC + f"no Dext candles for {day}"}
    key = inst["key"]
    candles, ohlc = dext_log.read_candles(key, day), dext_log.read_ohlc(key, day)
    dext_ik = f"NSE_FO|{inst['SEC_ID']}" if inst.get("EXCH") == "NSE" and inst.get("SEG") == "D" else None
    out = {"ok": True, "day": day, "tag": "M", "inst": {"key": key, "name": inst.get("name"), "SEC_ID": inst["SEC_ID"]},
           "notes": []}

    same = bool(dext_ik) and dext_ik == ux_ik
    out["contract"] = {"dext": dext_ik, "upstox": ux_ik, "gocharting": "NIFTY-I (continuous near month)", "same": same}
    if not same:
        out["contract"]["why"] = (CC + f"Upstox and GoCharting: no Upstox record for {day}, so the contract is unproven" if not ux_ik else
                                  CC + f"Upstox and GoCharting: Upstox recorded {ux_ik} on {day}, Dext's chart is {dext_ik or key} "
                                  "(another contract); GoCharting's NIFTY-I is the near month, so it is another contract too")

    # the lot: instruments.json first, else the lot Upstox's dump gave the SAME exchange token; never assumed
    lot, lot_src = inst.get("lot"), "data/dext/instruments.json"
    if not lot and same:
        lot = next((r.get("lot") for r in ux_rows if r.get("lot")), None)
        lot_src = f"Upstox record's lot for {ux_ik}"
    if not lot:
        return {**out, "ok": False, "why": CC + f"the lot of {inst.get('name') or key} is unknown (put it in data/dext/instruments.json)"
                + ("" if same else "; " + out["contract"]["why"])}
    out["lot"], out["lot_src"] = lot, lot_src

    D, auction, auction_n = _dext_bars(candles, ohlc, lot)
    out["closing_auction"] = {"minutes": auction_n, "vol_D": round(auction, 2), "why": "Dext's 15:30-15:39 minutes, excluded"}
    srcs = {"D": D}
    if same:
        srcs["U"] = _tape_bars(ux_rows, True)
        srcs["G"] = _tape_bars(tape_log._read(tape_log.day_path(day, "NIFTY")), False)
        if not srcs["G"]:
            del srcs["G"]
            out["notes"].append(CC + f"GoCharting: no tape_NIFTY_{day}.jsonl")

    allt = set().union(*(set(B) for B in srcs.values()))
    first = next((t for t in allt if _mod(t // 1000) == OPEN), None)
    out["first_bar"] = {"time": "09:15", "why": "excluded: Dext and GoCharting fold the pre-open auction into it, Upstox does not",
                        "vol": {s: round(B[first]["vol"], 2) if first in B else None for s, B in srcs.items()}}
    grid = sorted(allt - {first})
    ts = [t for t in grid if all(t in B for B in srcs.values())]
    out["bars"] = {"compared": len(ts), "missing": {s: [_hm(t) for t in grid if t not in B] for s, B in srcs.items()}}
    if not ts:
        return {**out, "ok": False, "why": CC + "no bar after 09:15 that every compared source has"}
    S = [k for k in "DUG" if k in srcs]
    pairs = [(a, b) for a, b in PAIRS if a in srcs and b in srcs]
    v = {s: [srcs[s][t] for t in ts] for s in S}
    n = len(ts)
    out["vol"] = {s: round(sum(b["vol"] for b in v[s]), 2) for s in S}
    out["delta_sum"] = {s: round(sum(b["delta"] for b in v[s]), 2) for s in S}
    out["vol_within_half_lot"] = {a + b: sum(abs(x["vol"] - y["vol"]) <= 0.5 for x, y in zip(v[a], v[b])) for a, b in pairs}
    out["same_sign_delta"] = {a + b: sum(_sign(x["delta"]) == _sign(y["delta"]) for x, y in zip(v[a], v[b])) for a, b in pairs}
    out["of"] = n
    out["delta_corr"] = {a + b: _corr([x["delta"] for x in v[a]], [y["delta"] for y in v[b]]) for a, b in pairs}
    out["oi_equal"] = {a + b: {"n": sum(x["oi"] == y["oi"] for x, y in zip(v[a], v[b]) if x["oi"] is not None and y["oi"] is not None),
                               "of": sum(x["oi"] is not None and y["oi"] is not None for x, y in zip(v[a], v[b]))} for a, b in pairs}
    out["delta_move_corr"] = {s: _corr([b["delta"] for b in v[s] if b["move"] is not None], [b["move"] for b in v[s] if b["move"] is not None])
                              for s in S}
    steps = sorted({b["t"] - a["t"] for a, b in zip(ohlc, ohlc[1:])})
    if steps and steps[0] != 300:
        out["oi_equal"] = {k: {"n": None, "of": 0} for k in out["oi_equal"]}
        out["delta_move_corr"]["D"] = None
        out["notes"].append(CC + f"Dext OI and move: its getData rows for {day} are {steps[0] // 60}m, not 5m")
    elif not ohlc:
        out["notes"].append(CC + f"Dext OI and move: no getData rows for {day}")
    out["cell_overlap_median"] = {}
    for a, b in pairs:
        if a == "D":
            ov = [o for o in (_overlap(x["cells"], y["cells"]) for x, y in zip(v[a], v[b])) if o is not None]
            out["cell_overlap_median"][a + b] = round(statistics.median(ov), 3) if ov else None
    out["poc_agree"] = {a + b: sum(_poc(x["cells"]) == _poc(y["cells"]) for x, y in zip(v[a], v[b])) for a, b in pairs}
    out["top_cells"] = {s: [{"time": _hm(b["t"]), "p": p, "vol": round(q[0], 2), "buy": round(q[1], 2), "sell": round(q[2], 2)}
                            for b, p, q in sorted(((b, p, q) for b in v[s] for p, q in b["cells"].items()), key=lambda z: -z[2][0])[:5]]
                        for s in S}
    return out


def _f(x) -> str:
    return "-" if x is None else f"{x:,.0f}" if isinstance(x, (int, float)) and abs(x) >= 100 else f"{x}"


def summary(r: dict) -> str:
    if not r.get("ok"):
        return f"dext parity {r['day']} · {r.get('why')}"
    S, n = list(r["vol"]), r["of"]
    ss = " ".join(f"{k} {c}/{n}" for k, c in r["same_sign_delta"].items())
    cells = " ".join(f"{k} {x}" for k, x in r["cell_overlap_median"].items())
    line = (f"dext parity {r['day']} · {r['inst']['name']} ({r['inst']['key']}) · {n} bars, 09:15 excluded · "
            f"vol {'/'.join(S)} {' / '.join(_f(r['vol'][s]) for s in S)} · "
            f"sum delta {' / '.join(_f(r['delta_sum'][s]) for s in S)} · same-sign {ss} · cells {cells} [M]")
    return line + ("" if r["contract"]["same"] else " · " + r["contract"]["why"])


def run(day: str) -> dict:
    r = report(day)
    os.makedirs(dext_log.DIR, exist_ok=True)
    p = os.path.join(dext_log.DIR, f"parity_{day}.json")
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(r, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)
    return r


def main(argv: List[str]) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")        # a cp1252 console or log never kills the evening run
    except (AttributeError, ValueError):
        pass
    day = argv[1] if len(argv) > 1 else time.strftime("%Y-%m-%d")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        print("usage: python dext_parity.py [YYYY-MM-DD]")
        return 2
    print(summary(run(day)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
