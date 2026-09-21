"""ux_gate.py -- GoCharting's bars against the Upstox ladder, on one grid, by SHAPE.

WHAT IT RETURNS: numbers. POC distance in rows, delta sign agreement, value-
area overlap, node-set Jaccard, and one magnitude -- the volume ratio, [M]
against [M], a feed-integrity check, never a trading quantity. It returns no
verdict, no pass, no colour: the bar is the operator's (spec §K), stated after
five sessions. Every null carries its why (rule 6). Both records are re-binned
on GoCharting's grid (spec §J.4) -- the grid the operator's chart is on. Named ux_gate because gate.py is the seller's gate (frame.py imports it).

Pure, stdlib only, no I/O, no clock.
"""
from __future__ import annotations

from statistics import median
from typing import List, Optional

import prints


def _four(a: bool, b: bool) -> str:
    return "both" if a and b else "ofd" if a else "ux" if b else "neither"


def _sign(x) -> int:
    return 0 if not x else (1 if x > 0 else -1)


def per_bar(o: dict, u: dict, row_size: float, anchor: float = 0.0) -> dict:
    fo, fu = prints.bar_flags(o, row_size, anchor), prints.bar_flags(u, row_size, anchor)
    out: dict = {"t": o.get("t"), "tag": "M"}
    po, pu = (fo or {}).get("poc"), (fu or {}).get("poc")
    if po is None or pu is None:
        out["poc_rows"], out["poc_rows_why"] = None, "no POC on one side"
    else:
        out["poc_rows"], out["poc_rows_why"] = int(round(abs(pu - po) / row_size)), None
    so, su = _sign(o.get("delta")), _sign(u.get("delta"))
    if so == 0 or su == 0:
        out["delta_sign"], out["delta_sign_why"] = None, "a delta of 0 has no sign"
    else:
        out["delta_sign"], out["delta_sign_why"] = ("agree" if so == su else "disagree"), None
    vo = o.get("vol") or 0
    if not vo:
        out["vol_ratio"], out["vol_ratio_why"] = None, "GoCharting volume is 0"
    else:
        out["vol_ratio"], out["vol_ratio_why"] = (u.get("vol") or 0) / vo, None
    out["stacks"] = _four(bool((fo or {}).get("stacks")), bool((fu or {}).get("stacks")))
    out["unfinished"] = _four(bool((fo or {}).get("unfinished_high") or (fo or {}).get("unfinished_low")),
                              bool((fu or {}).get("unfinished_high") or (fu or {}).get("unfinished_low")))
    return out


def _jaccard(a: set, b: set) -> Optional[float]:
    return None if not a or not b else len(a & b) / len(a | b)


def _interval_overlap(x: Optional[dict], y: Optional[dict]) -> Optional[float]:
    if not x or not y:
        return None
    lo, hi = max(x["val"], y["val"]), min(x["vah"], y["vah"])
    union = max(x["vah"], y["vah"]) - min(x["val"], y["val"])
    return 1.0 if union <= 0 else max(0.0, hi - lo) / union


def rebinned(bars: List[dict], row_size: float, anchor: float) -> List[dict]:
    """Copies of `bars` with each ladder on the given grid -- the server's ux
    levels use this too, so profile and gate read one grid."""
    return [{**b, "ladder": prints.rebin(b.get("ladder") or [], row_size, anchor)} for b in bars]


def session(ofd: List[dict], ux: List[dict], row_size: float, anchor: float = 0.0) -> dict:
    by_o = {b["t"]: b for b in ofd if b.get("t") is not None}
    by_u = {b["t"]: b for b in ux if b.get("t") is not None}
    joined = sorted(set(by_o) & set(by_u))
    rows = [per_bar(by_o[t], by_u[t], row_size, anchor) for t in joined]
    out: dict = {"tag": "M", "bars_joined": len(joined),
                 "bars_ofd_only": len(set(by_o) - set(by_u)), "bars_ux_only": len(set(by_u) - set(by_o))}

    def med(key, name):
        v = [r[key] for r in rows if r.get(key) is not None]
        out[name] = median(v) if v else None
        out[name + "_why"] = None if v else ("no joined bars" if not rows else f"{key} null on every joined bar")

    med("poc_rows", "poc_rows_median")
    pr = [r["poc_rows"] for r in rows if r.get("poc_rows") is not None]
    out["poc_within_1"] = (sum(1 for x in pr if x <= 1) / len(pr)) if pr else None
    out["poc_within_1_why"] = None if pr else out["poc_rows_median_why"]
    ds = [r["delta_sign"] for r in rows if r.get("delta_sign") is not None]
    out["delta_sign_agree"] = (ds.count("agree") / len(ds)) if ds else None
    out["delta_sign_agree_why"] = None if ds else ("no joined bars" if not rows else "every joined bar has a 0 delta on one side")
    med("vol_ratio", "vol_ratio_median")

    po, pu = prints.profile(rebinned(ofd, row_size, anchor)), prints.profile(rebinned(ux, row_size, anchor))
    out["va_overlap"] = _interval_overlap(po, pu)
    out["va_overlap_why"] = None if out["va_overlap"] is not None else ("no ux profile" if not pu else "no GoCharting profile")
    no, nu = prints.nodes(po), prints.nodes(pu)
    for kind, key in (("HVN", "hvn_jaccard"), ("LVN", "lvn_jaccard")):
        a = {n["p"] for n in no if n["kind"] == kind}
        b = {n["p"] for n in nu if n["kind"] == kind}
        out[key] = _jaccard(a, b)
        out[key + "_why"] = None if out[key] is not None else f"no {kind} on one side"

    ex = sum(b.get("exact") or 0 for b in ux)
    rc = sum(b.get("reconstructed") or 0 for b in ux)
    vol = sum(b.get("vol") or 0 for b in ux)
    out["exact_frac"] = ex / (ex + rc) if (ex + rc) else None
    out["exact_frac_why"] = None if (ex + rc) else "no trading interval in the ux record"
    out["hidden_frac"] = (sum(b.get("hidden") or 0 for b in ux) / vol) if vol else None
    out["unknown_frac"] = (sum(b.get("unknown") or 0 for b in ux) / vol) if vol else None
    out["hidden_frac_why"] = out["unknown_frac_why"] = None if vol else "no ux volume"
    return out
