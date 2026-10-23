"""tools/ride_score.py -- RIDE's dry counts and its gated one-shot (RIDE-PREREG.md §6, research-findings §1j).

    python tools/ride_score.py              DRY, the default: counts only. No R, no premium, nothing written.
    python tools/ride_score.py --run        THE one-shot, REFUSED until some cell can reach n >= 20 RIDE entries with
                                            the forward rows included (§6); writes data/confluence/ride_first_look.json.
                                            Refuses if it has already run.
    python tools/ride_score.py --rerun WHY  a re-run, only to fix a bug that changes no definition (§6); WHY is logged
                                            in data/confluence/ride_reruns.jsonl and in the output.
    python tools/ride_score.py --look-amendment-2
                                            THE ONE LOOK of research-findings §1k (Amendment 2, Mary's request): the
                                            recorded days scored once with the gate shut, under the frozen rules and
                                            READINGS below, with §1k's descriptive extras; the output says so. Refuses
                                            if the one-shot (or this look) has already run. It loosens no definition.

Every mode refuses unless RIDE-PREREG.md still hashes to the sha256 anchored in research-findings §1j.

DAYS: every (index, day) on which the Upstox book record (data/book: v2feed's futures ticks, and FLOW's book) and the
chain record (data/chain: the OI fronts, the READ, the premiums) both exist; a day whose ticks give no closed 3-min bar
is listed with that reason. THE ROWS: every §E ENTRY on those days (ride.entries: frame_v2.plan called causally at each
bar close), each built exactly as the forward log builds it (confluence_log.build_ride). The forward rows
(data/confluence_log.jsonl, setup RIDE) count toward the gate only on days this scan does not hold, so no entry is
counted twice.

OUTPUT (--run only): per cell (DOWN / UP x NIFTY+SENSEX / BANKNIFTY) the RIDE trades, the §E-alone control on the same
days (entered at the §E bar's close, the identical hold), §4's fields and §5's paired expression rows. NO HIT RATE
ANYWHERE.
"""
import argparse
import collections
import glob
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # tapemap/
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import book_log          # noqa: E402
import chain_live        # noqa: E402
import confluence as C   # noqa: E402
import confluence_log    # noqa: E402
import frame_v2          # noqa: E402
import ride              # noqa: E402

PREREG = os.path.join(HERE, "docs", "setup-review", "RIDE-PREREG.md")
SHA = "dcb306a11ad662291a25094e7db3288aeacc3367be403d2364900302843aff7e"
OUT_JSON = os.path.join("data", "confluence", "ride_first_look.json")      # the one-shot, or §1k's one look
RERUNS = os.path.join("data", "confluence", "ride_reruns.jsonl")
INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
GROUPS = ("NIFTY+SENSEX", "BANKNIFTY")
CELLS = [f"{s} {g}" for s in ("DOWN", "UP") for g in GROUPS]
AMENDMENT = ("§1k (Amendment 2, 2026-10-21, Mary: 'can you tell me when these condition met what happened in the "
             "market afterwards'): the recorded days are scored once, before n >= 20, under the frozen rules and the "
             "READINGS below; any rule change after this look is a NEW registration judged only on later forward rows")

# The builder's readings where RIDE-PREREG's text is not literal (§1i Amendment 1's practice: printed in the dry header,
# stored in the one-shot's output). Frozen by §1k: a re-run may not change one.
READINGS = [
    "§E is frame_v2.plan, never re-implemented, called at every 3-min close with the bars closed by then, the READ rows "
    "marked by then and the frame's basis band AS AT that close (compose's own: the chain spot at or before the close, "
    "the last READ row's basis, parity_basis at the close). One later band would show entries the frame never showed: "
    "the band decides §E's T2 wall, so its re-arm (24 Sep NIFTY 11:51). (deviation 1)",
    "Bars: v2feed's 1-s futures ticks -> 3-min bars aligned to 09:15 with the tape's session VWAP / sigma "
    "(frame_v2.bars3), and 1-min bars from the same ticks (width=60). 3-min events are named by the bar's END; sigma "
    "for the line is the entry bar's (u1 - VWAP), frozen.",
    "OI is read at the bar's last minute (close - 1, the §1d stamp's minute) on the chain grid cut there, with the "
    "session-peak OI as at then; a grid more than fronts.STALE_MIN behind is 'could not check'. FLOW windows: last 5 min "
    "= [close-5, close), the 15 before = [close-20, close-5), §1i's book and holes; GC needs one whole 5-min bar "
    "opening at close-5.",
    "LOCATION's VWAP side: the RIDE bar's close against that bar's live session VWAP.",
    "No entry after 15:00: the RIDE bar must CLOSE at or before 15:00. The control (§E alone) is entered at the §E "
    "bar's close with trade(d, §E bar, §E bar) and the identical hold; a §E bar closing after 15:00 enters neither arm "
    "(FADE reading 8).",
    "HARD LINE: intrabar on 1-min bars; a touch exits at the line price. The TRAIL: at each 3-min close, the latest "
    "READ row as of it, only while that row reads TREND / LEAN in the ride's own direction (an opposite READ's FLIP is "
    "no line for this ride; deviation 7a). The line moves to FLIP -/+ 0.25 sigma only when nearer price than the "
    "current line, and never past that close (a line through price would be a close-triggered exit; deviation 7b).",
    "FLIP in fut = the READ row's FLIP + that row's own measured basis, even when the frame's plausibility band flags "
    "the basis (the Read tab's convention, her landing page; declared in §1k).",
    "SOMEBODY GAVE UP: the trend-side front (fronts.read at the close's last minute) reads UNWINDING at a 3-min close: "
    "exit at that bar's close. A close falling in a 1-min hole is read at the next bar's open, never skipped "
    "(deviation 7c). A stale grid cannot exit. STALLED is stamped, never an exit.",
    "15:20: the 15:19 bar's close, i.e. the 15:20:00 price, named '15:20' (every RIDE time is an END; deviation 6).",
    "R = (E - exit) / (line0 - E) for DOWN, mirrored for UP, on the initial line throughout.",
    "Expressions (§5): the strike nearest the chain spot at the entry's last chain minute; 1-ITM = the next strike in "
    "the trade's direction; the RECORDED chain LTPs only (a backfilled minute is not one), within fronts.STALE_MIN, read "
    "at the minute before each END time (FADE's §5 convention; deviation 9). Points per unit: buy = exit - entry, sell "
    "= entry - exit.",
    "Stamps: DTE to the OPTIONS expiry (deviation 8); leg age from the READ's `since`; pullback depth (RIDE-REVIEW "
    "MAJOR 1, replacing deviation 7d): DOWN pull = the §E bar's own high, ext = the lowest low of the leg's bars (from "
    "`since`) before it, start = the highest high of the leg's bars up to that low, depth = (pull - ext) / (start - "
    "ext), UP mirrored, the three raw prices stamped; flip_dist = FLIP fut minus the price it is measured from, both at "
    "the RIDE entry bar (else the §E bar and its close); peers = each other index's last READ row at or before the §E "
    "bar, sync = how many read TREND / LEAN the same way; pullback_no = the §E entries of that direction under the same "
    "`since`; the §1d gate is null, 'no §1d gate is logged for §E entries'.",
    "Days: the Upstox book record and the chain record both exist. §E itself refuses a whole day once more than one "
    "3-min slot since 09:15 has no futures tick (frame_v2.MAX_MISS): a late start logs no §E entry that day.",
    "The gate (§6) counts the forward log's RIDE entries only on index-days this scan does not hold (no double count). "
    "The dry table counts a trigger closing after 15:00 in its own column, never as 'could not check'.",
    "§1k's extras, in no bar: MFE / MAE in points over the 1-min bars from the entry close to the exit; the move 30 and "
    "60 minutes after entry in the trade's direction (the close of the 1-min bar ending then, whatever the exit); the "
    "chain spot at the entry's last chain minute.",
]


def group(idx):
    return "BANKNIFTY" if idx == "BANKNIFTY" else "NIFTY+SENSEX"


def cell(d, idx):
    return f"{'DOWN' if d < 0 else 'UP'} {group(idx)}"


def sha_ok(path=PREREG):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest() == SHA


def _have(path):
    return os.path.exists(path) or os.path.exists(path + ".gz")


def days():
    """Every (index, day) either record holds, and whether it qualifies."""
    seen = set()
    for idx in INDICES:
        for p in glob.glob(os.path.join(book_log.DIR, f"book_{idx}_*.jsonl*")):
            seen.add((idx, os.path.basename(p)[len(f"book_{idx}_"):][:10]))
        for p in glob.glob(os.path.join(str(chain_live.CHAIN_DIR), f"chain_{idx}_*.jsonl*")):
            seen.add((idx, os.path.basename(p)[len(f"chain_{idx}_"):][:10]))
    out = []
    for idx, day in sorted(seen, key=lambda k: (k[1], INDICES.index(k[0]))):
        has = {"chain": _have(confluence_log._chain_path(idx, day)), "book": _have(book_log.day_path(day, idx))}
        miss = [k for k in ("chain", "book") if not has[k]]
        out.append({"index": idx, "day": day, **has, "qualifies": not miss, "scanned": False, "e": None,
                    "why": None if not miss else "no " + " / no ".join(
                        {"chain": "chain record", "book": "Upstox book record"}[k] for k in miss)})
    return out


def collect(day_recs, run=False):
    """Every §E ENTRY's row on the qualifying days; with run=True, also its outcomes."""
    entries = []
    for d in day_recs:
        if not d["qualifies"]:
            continue
        idx, day = d["index"], d["day"]
        inp = confluence_log.ride_inputs(idx, day, None, light=True)
        d["scanned"] = True
        if not inp["b3"]:
            d["why"] = "no closed 3-min futures bar from the ticks"
            continue
        ents = ride.entries(inp["b3"], inp["rows"], inp["basis"])
        d["e"] = len(ents)
        if not ents:
            continue
        inp = dict(confluence_log.ride_inputs(idx, day, None), entries=ents)
        for ent in ents:
            e = {"cell": cell(ent["d"], idx), "row": confluence_log.build_ride(idx, day, ent, inp),
                 "late": inp["b3"][ent["i"]]["e"] // 60 > ride.CUTOFF}
            if run:
                e.update(_outcomes(ent, e["row"], inp))
            entries.append(e)
    return entries


def _outcomes(ent, row, inp):
    """THE SCORER ONLY (§6): the control entered at the §E close and the RIDE entry, both with §2's identical hold."""
    d, b3, rows, chain, ones = ent["d"], inp["b3"], inp["rows"], inp["chain"], inp["ones"]
    out = {"control": None, "ride": None, "expressions": None}

    def scored(tr, start, t):
        oc = ride.outcome(d, tr, start, ones, ride.closes_after(d, start, b3, rows, chain))
        if not oc:
            return None
        spot = C._at_minute(chain[0], ride._chain_min(t))
        return dict(tr, **oc, t=t, spot=spot.get("spot") if spot else None,
                    extras=ride.excursion(d, tr["E"], start, frame_v2._sec(oc["exit_t"]) // 60, ones))
    c0 = b3[ent["i"]]["e"] // 60
    if c0 <= ride.CUTOFF:
        out["control"] = scored(ride.trade(d, b3[ent["i"]], b3[ent["i"]]), c0, ent["t"])
    en = row["entry"]
    if en:
        out["ride"] = scored(en, frame_v2._sec(en["t"]) // 60, en["t"])
        if out["ride"]:
            out["expressions"] = ride.expressions(d, chain[0], en["t"], out["ride"]["exit_t"])
    return out


# ---- DRY: counts only -------------------------------------------------------------------------------------------------

def _any(row, part):
    """True if some bar of the window (closing by 15:00) read ok, None if none could be read, else False."""
    vals = [b[part]["ok"] for b in row["bars"] if not b["late"]]
    return True if True in vals else False if False in vals else None


def counts(entries):
    tab = {c: collections.Counter() for c in CELLS}
    for e in entries:
        t, row = tab[e["cell"]], e["row"]
        t["e"] += 1
        t["late"] += e["late"]
        if e["late"]:
            continue                             # a trigger closing after 15:00: its own column, never "could not check"
        t["loc_ok"] += _any(row, "loc") is True
        for part in ("oi", "flow"):
            v = _any(row, part)
            t[f"{part}_ok"] += v is True
            t[f"{part}_cnc"] += v is None
        t["both_same_bar"] += any(b["oi"]["ok"] and b["flow"]["ok"] and not b["late"] for b in row["bars"])
        t["ride"] += row["entry"] is not None
    return tab


def forward(scanned, path=None):
    """{cell: forward RIDE rows with a RIDE entry} from the forward log, on (index, day)s the scan does not hold."""
    out = collections.Counter()
    for r in confluence_log._rows(path or confluence_log.PATH):
        if (r.get("setup") == "RIDE" and r.get("entry") and r.get("index") in INDICES
                and (r["index"], r.get("day")) not in scanned and isinstance(r.get("d"), int)):
            out[cell(r["d"], r["index"])] += 1
    return dict(out)


def can_run(counts_, fwd):
    """§6: an outcome may be computed once ANY cell can reach n >= 20 RIDE entries, the forward rows included."""
    return any(counts_.get(c, 0) + fwd.get(c, 0) >= C.PASS_N for c in CELLS)


def print_dry(day_recs, entries, fwd):
    print(f"RIDE -- DRY (counts only; no R, no premium, nothing written). {ride.REV}\n")
    print("READINGS (where RIDE-PREREG's text is not literal; frozen by §1k)")
    for k, r in enumerate(READINGS, 1):
        print(f"  {k}. {r}")
    print()
    print("DAYS (§6: the Upstox book record + the chain record)")
    print(f"  {'day':<11}{'index':<10} {'chain':<6}{'book':<5} {'in':<4}{'§E':>4}  why")
    for d in day_recs:
        print(f"  {d['day']:<11}{d['index']:<10} {'y' if d['chain'] else '-':<6}{'y' if d['book'] else '-':<5} "
              f"{'yes' if d['scanned'] and d['e'] is not None else '--':<4}{'' if d['e'] is None else d['e']:>4}  "
              f"{d['why'] or ''}")
    q = [d for d in day_recs if d["qualifies"]]
    s = [d for d in day_recs if d["e"] is not None]
    print(f"\n  {len(q)} index-days qualify; {len(s)} have closed 3-min bars and were scanned.")
    print("\nPER CELL (§E entries on the scanned days)")
    keys = ("e", "loc_ok", "oi_ok", "oi_cnc", "flow_ok", "flow_cnc", "both_same_bar", "ride", "late")
    heads = ("§E", "LOC ok", "OI ok", "OI cnc", "FLOW ok", "FLOW cnc", "OI+FLOW", "RIDE", "trig>15:00")
    print(f"  {'cell':<20}" + "".join(f"{h:>11}" for h in heads) + f"{'forward':>11}")
    tab = counts(entries)
    for c in CELLS + ["TOTAL"]:
        t = tab[c] if c != "TOTAL" else sum(tab.values(), collections.Counter())
        fw = fwd.get(c, 0) if c != "TOTAL" else sum(fwd.values())
        print(f"  {c:<20}" + "".join(f"{t[k]:>11}" for k in keys) + f"{fw:>11}")
    print("  (ok = some bar of the window closing by 15:00 read ok; cnc = no such bar could be read, 'could not "
          "check'; OI+FLOW = both ok on one bar; RIDE adds the VWAP side; forward = the forward log's RIDE entries on "
          "days not scanned here)")
    gate = can_run({c: tab[c]["ride"] for c in CELLS}, fwd)
    print(f"\nGATE (§6): {'OPEN -- a cell can reach n >= 20' if gate else 'SHUT -- no cell can reach n >= 20'}; "
          f"--run {'may run once' if gate else 'refuses'}.")


# ---- RUN: the one-shot (refused until the gate opens) ------------------------------------------------------------------

def result(day_recs, entries, reruns, amendment=None):
    cells = {}
    for c in CELLS:
        es = [e for e in entries if e["cell"] == c]
        key = lambda e: dict(day=e["row"]["day"], index=e["row"]["index"], trigger_t=e["row"]["t"])   # noqa: E731
        rd = [dict(e["ride"], **key(e), expressions=e["expressions"]) for e in es if e.get("ride")]
        ctl = [dict(e["control"], **key(e)) for e in es if e.get("control")]
        xr = [dict(key(e), **e["expressions"]) for e in es if e.get("ride") and e.get("expressions")
              and all(e["expressions"].get(x) for x in ("buy_atm", "buy_itm", "sell_atm"))]
        summ = None
        if len(xr) >= C.PASS_N:
            summ = {"n": len(xr)}
            for x in ("buy_atm", "buy_itm", "sell_atm"):
                pts = [r[x]["pts"] for r in xr]
                summ[x] = {"mean_pts": round(C._mean(pts), 2), "mean_pts_ex_best": round(C.drop_best(pts), 2)}
        cells[c] = {"verdict": C.verdict(rd, ctl), "ride": rd, "control": ctl,
                    "expressions": {"rows": xr, "summary": summ,
                                    "why": None if summ else f"{len(xr)} paired rows, under {C.PASS_N}: recorded, "
                                                              f"not described (§5)"}}
    return {"prereg": os.path.relpath(PREREG, HERE), "sha256": SHA, "rev": ride.REV, "amendment": amendment,
            "readings": READINGS, "run_at": time.strftime("%Y-%m-%d %H:%M:%S"), "reruns": reruns, "days": day_recs,
            "cells": cells, "rows": [e["row"] for e in entries]}


def _f(v):
    return "-" if v is None else f"{v:+.2f}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry", action="store_true", help="counts only (the default)")
    g.add_argument("--run", action="store_true", help="THE one-shot, gated by §6")
    g.add_argument("--rerun", metavar="WHY", help="a logged re-run to fix a bug that changes no definition")
    g.add_argument("--look-amendment-2", action="store_true", dest="look",
                   help="§1k's one look: the recorded days scored once, gate shut, frozen rules")
    a = ap.parse_args(argv)
    os.chdir(HERE)
    if not sha_ok():
        print(f"REFUSED: {PREREG} no longer hashes to the anchored {SHA[:8]}...; it must never be edited.")
        return 2
    run = a.run or bool(a.rerun) or a.look
    if (a.run or a.look) and os.path.exists(OUT_JSON):
        print(f"REFUSED: the one-shot / §1k look already ran ({OUT_JSON}). A re-run needs --rerun WHY (§6).")
        return 2
    day_recs = days()
    entries = collect(day_recs, run=False)
    fwd = forward({(d["index"], d["day"]) for d in day_recs if d["scanned"]})
    if not run:
        print_dry(day_recs, entries, fwd)
        return 0
    tab = counts(entries)
    if not a.look and not can_run({c: tab[c]["ride"] for c in CELLS}, fwd):
        print("REFUSED (§6): no RIDE cell can reach n >= 20 with the forward rows included -- "
              + ", ".join(f"{c} {tab[c]['ride']}+{fwd.get(c, 0)}" for c in CELLS)
              + ". No R or premium outcome is computed on recorded days until then.")
        return 2
    entries = collect(day_recs, run=True)
    reruns = list(confluence_log._rows(RERUNS))
    if a.rerun:
        reruns.append({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "why": a.rerun})
    res = result(day_recs, entries, reruns, AMENDMENT if a.look else None)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    if a.rerun:
        with open(RERUNS, "a", encoding="utf-8") as f:
            f.write(json.dumps(reruns[-1]) + "\n")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(f"RIDE first look ({ride.REV}) -> {OUT_JSON}. No hit rate is printed, here or anywhere (§4).")
    if a.look:
        print(f"  RAN UNDER {AMENDMENT}.")
    print(f"  {'cell':<20}{'n':>4}{'mean R':>9}{'w/o best':>10}{'ctl n':>7}{'ctl R':>8}{'diff':>8}{'day share':>11}  verdict")
    for c in CELLS:
        v = res["cells"][c]["verdict"]
        share = "-" if v["largest_day_share"] is None else f"{v['largest_day_share'] * 100:.0f}%"
        print(f"  {c:<20}{v['n']:>4}{_f(v['mean_R']):>9}{_f(v['mean_R_ex_best']):>10}{v['control_n']:>7}"
              f"{_f(v['control_mean_R']):>8}{_f(v['diff']):>8}{share:>11}  {v['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
