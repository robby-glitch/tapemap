"""tools/confluence_score.py -- THE ONE-SHOT FIRST LOOK at the confluence setup (CONFLUENCE-PREREG.md §6, §1i).

    python tools/confluence_score.py              DRY, the default: counts only. No R, no premium, nothing written.
    python tools/confluence_score.py --run        THE one-shot: writes docs/setup-review/FIRST-LOOK.md and
                                                  data/confluence/first_look.json. Refuses if it has already run.
    python tools/confluence_score.py --rerun WHY  a re-run, allowed only to fix a bug that changes no definition (§6);
                                                  WHY is logged in data/confluence/reruns.jsonl and in FIRST-LOOK.md.
    python tools/confluence_score.py --look-amendment-2
                                                  THE one-shot run once under research-findings §1k (Amendment 2, Mary's
                                                  request): first_look.json says so and carries §1k's descriptive
                                                  extras; the document is docs/setup-review/LOOK-2026-10-21.md
                                                  (tools/look_report.py). Refuses if the one-shot has run. Loosens nothing.

Every mode refuses unless CONFLUENCE-PREREG.md still hashes to the sha256 anchored in research-findings §1i.

DAYS (§6): every (index, day) on which zone ENTRY rows (data/trigger_log.jsonl), chain minutes (data/chain) and Upstox
1-s futures frames (data/book) all exist. Scoring also needs the zone machine's own series -- the cached 1-min session
(data/backtest) -- for E, the bands and the 1-min first passage; a qualifying day without it is listed with that reason
and enters NEITHER arm, so the control stays on the same days.

THE ROWS: each logged zone ENTRY is matched to the same entry replayed on the cached series (band_rotation.run_states
at d2 / u2, live.py's call). A row the replay does not reproduce, or whose cached close differs from its logged `px`,
is excluded and counted with its reason. trigger_log is read through confluence_log.logged, which keeps NON-outcome
fields only: mfe / mae / stop_hit / scored_* / triggered / f15 / ... are dropped at the parse and never read.

OUTPUT (--run only): per cell (kind x side x {NIFTY+SENSEX, BANKNIFTY}) the confluence entries, the zone-alone control
on the same days, §4's fields -- n, mean R, mean R without the best trade, the control's mean R, the largest day's
share, PASS / FAIL / INCONCLUSIVE -- and §5's paired expression rows. NO HIT RATE ANYWHERE.
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
import fronts            # noqa: E402
import ride              # noqa: E402   (§1k's descriptive extras only: ride.excursion)

PREREG = os.path.join("docs", "setup-review", "CONFLUENCE-PREREG.md")
SHA = "d5c4937fde3f20ffc772a22d22701200ed67f93bed990b4708841a5f2c31aa73"
OUT_JSON = os.path.join("data", "confluence", "first_look.json")
OUT_MD = os.path.join("docs", "setup-review", "FIRST-LOOK.md")
RERUNS = os.path.join("data", "confluence", "reruns.jsonl")
AMENDMENT = ("§1k (Amendment 2, 2026-10-21, Mary: 'can you tell me when these condition met what happened in the "
             "market afterwards'): the recorded days are scored once, before n >= 20, under the frozen rules and the "
             "READINGS below; any rule change after this look is a NEW registration judged only on later forward rows")
INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
GROUPS = ("NIFTY+SENSEX", "BANKNIFTY")
CELLS = [f"{k} {s} {g}" for k in (C.POCKET, C.EXHAUSTION) for s in ("BUY", "SELL") for g in GROUPS]
SIDE_RULE = ("ladder.attribute, stepped by ladder.Ladder.step: the Upstox side rule of the ux_log record rank.py "
             "ranks (quote rule, then mid, then the depth march)")

READINGS = [
    "Upstox 1-s futures bars = the book record data/book/book_<IDX>_<day> (~1 frame/s); data/tape/ux_<IDX>_<day> is "
    "its 5-min derivation and cannot give a 5-min window ending on a 3-min close. Sided by ladder.attribute "
    "(Ladder.step) at the tick that day's ux record used; fills binned by trade-time minute.",
    "A recorder hole is a book arrival gap >= 60 s. The minute of the first frame after it, and of the record's first "
    "frame, carry the gap's volume and are excluded; a minute with no frame at all is missing. A FLOW window that "
    "touches either is 'could not check', never a tilt over what is left.",
    "Bar close = the 3-min label + 3 min. OI is read on the chain minutes cut at the last minute inside the bar "
    "(fronts.bar_last_minute, the §1d stamp's minute); a grid more than fronts.STALE_MIN behind is 'could not check'.",
    "Session-peak OI (the front's rank) is the running peak AS AT the cut, rebuilt from the chain record; "
    "chain_backfill minutes fill only minutes the recorder never saw and carry no peak (ChainState's own rule).",
    "POCKET / EXHAUSTION: the setup's extreme is the reference bar's low (BUY) / high (SELL) at entry -- a re-arm moves "
    "the reference only on a new extreme -- judged against that same bar's d3 / u3. Equal to d3 is POCKET.",
    "FLOW windows: last 5 min = [close-5, close); the 15 min before = [close-20, close-5). The GoCharting check needs "
    "ONE whole GC 5-min bar opening at close-5, so it can bind only on closes on the 5-min grid (every 15 min).",
    "'Beyond the 1-sigma ring': close < d1 (BUY) / > u1 (SELL) on the confluence bar itself.",
    "No entry after 15:00: the confluence bar must CLOSE at or before 15:00 (the 14:57 bar is the last). The same "
    "cutoff is applied to the zone-alone control's trigger bar (her new-trade cutoff; a later entry is not a trade).",
    "'Within +3 bars' is the next three bars of the series AND within 9 minutes of the trigger close.",
    "One confluence entry per zone setup: each zone entry is one setup (the machine locks after an entry), so the "
    "first qualifying bar per zone entry is the only one taken.",
    "Stop 'd3 at entry' is d3 on the entry bar (confluence bar, or the trigger bar for the control); sigma there is "
    "VWAP - d1 on that bar, frozen. The 0.5-sigma floor moves the stop away from E when risk would be smaller.",
    "First passage on 1-min bars labelled from the entry close up to 15:19; the target is each bar's own session VWAP "
    "(vwap_bands at that bar), exit at that VWAP; a stop exit is the stop price; marked at the 15:19 bar's close, "
    "i.e. the price at 15:20:00 (the house rule that a 15:15 flat means bars labelled before 15:15).",
    "Premiums (§5): the strike nearest the chain spot in the entry bar's last minute; its CE and PE LTP there and at "
    "the exit minute (the 1-min bar that hit, or 15:19), from the RECORDED chain only (a backfilled minute is not "
    "used), within fronts.STALE_MIN. Points per unit, buy = exit - entry, sell = entry - exit. The both-legs stamp "
    "reads the recorded chain the same way.",
    "Stamps: DTE = the logged row's ctx.t_exp; first touch = no earlier zone arm (rearm false) that side that "
    "session; depth = (VWAP - extreme) / sigma at the reference bar; the READ word = the last READ mark at or before "
    "the close; both legs rising = §1h fact 5's straddle (strike ATM at t-15, CE and PE both up at t); reaction "
    "points = PDH / PDL (yesterday's cached futures session, same contract), a round 100, and today's session "
    "high / low BEFORE the setup's first arm (the reading of 'the prior session high/low'); gate and veto = the "
    "logged row's §1d gate and its ctx plays; R / T / P = v2.js FAM over the ofd marks and decoder events whose 5-min "
    "bar lies in [close-20, close]. The stamps are taken at the confluence bar (the trigger bar when there is none), "
    "and the reaction-point sigma is that bar's.",
    "A qualifying day without a cached 1-min session cannot be scored and enters neither arm; a logged row the "
    "cached replay does not reproduce (no entry on that bar, or a close more than 0.05 from its px) is excluded.",
]


def group(idx):
    return "BANKNIFTY" if idx == "BANKNIFTY" else "NIFTY+SENSEX"


def sha_ok():
    with open(PREREG, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest() == SHA


def _have(path):
    return os.path.exists(path) or os.path.exists(path + ".gz")


def days(logged):
    """Every (index, day) any of the three records holds, and whether it qualifies (§6)."""
    by = collections.defaultdict(list)
    for (day, idx, _t, _s), r in logged.items():
        by[(idx, day)].append(r)
    seen = set(by)
    for idx in INDICES:
        for p in glob.glob(os.path.join(book_log.DIR, f"book_{idx}_*.jsonl*")):
            seen.add((idx, os.path.basename(p)[len(f"book_{idx}_"):][:10]))
        for p in glob.glob(os.path.join(str(chain_live.CHAIN_DIR), f"chain_{idx}_*.jsonl*")):
            seen.add((idx, os.path.basename(p)[len(f"chain_{idx}_"):][:10]))
    out = []
    for idx, day in sorted(seen, key=lambda k: (k[1], INDICES.index(k[0]) if k[0] in INDICES else 9)):
        has = {"zone": len(by.get((idx, day), ())),
               "chain": _have(confluence_log._chain_path(idx, day)),
               "book": _have(book_log.day_path(day, idx))}
        miss = [k for k in ("zone", "chain", "book") if not has[k]]
        out.append({"index": idx, "day": day, **has, "qualifies": not miss,
                    "why": None if not miss else "no " + " / no ".join(
                        {"zone": "zone ENTRY rows", "chain": "chain minutes", "book": "Upstox book frames"}[k]
                        for k in miss),
                    "rows": sorted(by.get((idx, day), ()), key=lambda r: (r.get("t") or "", r.get("side") or ""))})
    return out


def collect(day_recs, run=False, lg=None):
    """The rows of every qualifying day; with run=True, also each one's outcomes. -> (entries, excluded)."""
    entries, excluded = [], []
    for d in day_recs:
        d["scoreable"] = False
        if not d["qualifies"]:
            continue
        idx, day = d["index"], d["day"]
        sess = confluence_log.session(idx, day)
        if sess is None:
            d["why"] = "no cached 1-min futures session in data/backtest (the zone machine's series)"
            excluded += [{"day": day, "index": idx, "t": r["t"], "side": r["side"], "why": d["why"]}
                         for r in d["rows"]]
            continue
        d["scoreable"] = True
        inp = confluence_log.inputs(idx, day, sess["expiry"], lg)
        d["chain_snaps"], d["book_minutes"] = inp["n_snaps"], inp["n_minutes"]
        sets = {(s["t"], s["side"]): s for s in C.setups(sess["bars"])}
        for r in d["rows"]:
            s = sets.get((r["t"], r["side"]))
            c = C.flat(sess["bars"][s["i"]]).get("c") if s else None
            why = ("the cached series replays no zone entry on this bar" if s is None
                   else f"cached close {c} is not the logged px {r['px']}"
                   if r.get("px") is not None and (c is None or abs(c - r["px"]) > 0.05)
                   else "the setup's kind could not be read" if s["kind"] is None else None)
            if why:
                excluded.append({"day": day, "index": idx, "t": r["t"], "side": r["side"], "why": why})
                continue
            row = confluence_log.build(idx, day, s, sess["bars"], inp)
            e = {"cell": f"{s['kind']} {s['side']} {group(idx)}", "row": row,
                 "late": C.close_of(s["t"]) > C.CUTOFF}
            if run:
                e.update(_outcomes(s, row, sess, inp))
            entries.append(e)
    return entries, excluded


def _extras(side, tr, oc, t, sess, minutes):
    """§1k's descriptive extras, in no bar: the chain spot at the entry bar's last minute, MFE / MAE to the exit and
    the move 30 / 60 minutes on (ride.excursion over the cached 1-min series, the one R is scored on)."""
    m = C.band_rotation._minute
    ones = [{"s": m(b["t"]) * 60, "h": b["h"], "l": b["l"], "c": b["c"]} for b in sess["ones"] if m(b.get("t")) is not None]
    rec = C._at_minute(minutes, fronts.bar_last_minute(t, C.INTERVAL))
    return {"spot": rec.get("spot") if rec else None,
            "extras": ride.excursion(1 if side == "BUY" else -1, tr["E"], C.close_of(t), m(oc["exit_t"]) + 1, ones)}


def _outcomes(s, row, sess, inp):
    out = {"control": None, "confluence": None, "expression": None}
    if C.close_of(s["t"]) <= C.CUTOFF:
        tr = C.trade(s, C.flat(sess["bars"][s["i"]]))
        oc = C.outcome(s["side"], tr, C.close_of(s["t"]), sess["ones"]) if tr else None
        out["control"] = dict(tr, **oc, **_extras(s["side"], tr, oc, s["t"], sess, inp["chain"][0])) if oc else None
    en = row["entry"]
    if en:
        oc = C.outcome(s["side"], en, C.close_of(en["t"]), sess["ones"])
        if oc:
            out["confluence"] = dict(en, **oc, **_extras(s["side"], en, oc, en["t"], sess, inp["chain"][0]))
            out["expression"] = C.expression(s["side"], inp["chain"][0],
                                             fronts.bar_last_minute(en["t"], C.INTERVAL), oc["exit_t"])
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
        t["zone"] += 1
        t["late"] += e["late"]
        for part in ("oi", "flow"):
            v = _any(row, part)
            t[f"{part}_ok"] += v is True
            t[f"{part}_cnc"] += v is None
        t["both_same_bar"] += any(b["oi"]["ok"] and b["flow"]["ok"] and not b["late"] for b in row["bars"])
        t["confluence"] += row["entry"] is not None
    return tab


def print_dry(day_recs, entries, excluded):
    print(f"CONFLUENCE first look -- DRY (counts only; no R, no premium, nothing written). {C.REV}")
    print(f"Upstox side rule: {SIDE_RULE}\n")
    print("DAYS (§6: zone ENTRY rows + chain minutes + Upstox book frames)")
    print(f"  {'day':<11}{'index':<10}{'zone':>5} {'chain':<6}{'book':<5} {'in':<4} why")
    for d in day_recs:
        ok = "yes" if d.get("scoreable") else "--"
        print(f"  {d['day']:<11}{d['index']:<10}{d['zone']:>5} {'y' if d['chain'] else '-':<6}"
              f"{'y' if d['book'] else '-':<5} {ok:<4} {d['why'] or ''}")
    q = [d for d in day_recs if d["qualifies"]]
    s = [d for d in day_recs if d.get("scoreable")]
    print(f"\n  {len(q)} index-days qualify under §6; {len(s)} can be scored (cached series present).")
    print("\nPER CELL (zone entries on scoreable days)")
    keys = ("zone", "oi_ok", "oi_cnc", "flow_ok", "flow_cnc", "both_same_bar", "confluence", "late")
    print(f"  {'cell':<28}" + "".join(f"{h:>11}" for h in ("zone", "OI ok", "OI cnc", "FLOW ok", "FLOW cnc",
                                                              "OI+FLOW", "CONFLUENCE", "trig>15:00")))
    tab = counts(entries)
    for c in CELLS + ["TOTAL"]:
        t = tab[c] if c != "TOTAL" else sum(tab.values(), collections.Counter())
        print(f"  {c:<28}" + "".join(f"{t[k]:>11}" for k in keys))
    print("  (ok = some bar of the window closing by 15:00 read ok; cnc = no such bar could be read, 'could not "
          "check'; OI+FLOW = both ok on one bar; CONFLUENCE adds the 1-sigma ring)")
    print(f"\nEXCLUDED ROWS: {len(excluded)}")
    for why, n in collections.Counter(x["why"] if not x["why"].startswith("cached close") else
                                      "cached close differs from the logged px" for x in excluded).most_common():
        print(f"  {n:>4}  {why}")


# ---- RUN: the one-shot ------------------------------------------------------------------------------------------------

def _trade_rows(entries, key):
    return [dict(e[key], day=e["row"]["day"], index=e["row"]["index"], trigger_t=e["row"]["t"])
            for e in entries if e.get(key)]


def result(day_recs, entries, excluded, reruns):
    cells = {}
    for c in CELLS:
        es = [e for e in entries if e["cell"] == c]
        conf, ctl = _trade_rows(es, "confluence"), _trade_rows(es, "control")
        xr = [dict(day=e["row"]["day"], index=e["row"]["index"], t=e["row"]["t"], entry_t=e["confluence"]["t"],
                   **e["expression"]) for e in es if e.get("confluence") and e.get("expression")]
        summ = None
        if len(xr) >= C.PASS_N:
            b, s = [x["buy_pts"] for x in xr], [x["sell_pts"] for x in xr]
            summ = {"n": len(xr), "buy_mean_pts": round(C._mean(b), 2), "buy_mean_pts_ex_best": round(C.drop_best(b), 2),
                    "sell_mean_pts": round(C._mean(s), 2), "sell_mean_pts_ex_best": round(C.drop_best(s), 2)}
        cells[c] = {"verdict": C.verdict(conf, ctl), "confluence": conf, "control": ctl,
                    "expression": {"rows": xr, "summary": summ,
                                   "why": None if summ else f"{len(xr)} paired rows, under {C.PASS_N}: recorded, "
                                                             f"not described (§5)"}}
    return {"prereg": PREREG, "sha256": SHA, "rev": C.REV, "run_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "side_rule": SIDE_RULE, "readings": READINGS, "reruns": reruns,
            "days": [{k: v for k, v in d.items() if k != "rows"} for d in day_recs],
            "excluded": excluded, "cells": cells, "rows": [e["row"] for e in entries]}


def _f(v, nd=2):
    return "—" if v is None else f"{v:+.{nd}f}"


def markdown(res):
    L = [f"# FIRST LOOK: the confluence setup (one-shot, CONFLUENCE-PREREG.md §6)", "",
         f"- **Run** {res['run_at']} against `{PREREG}`, sha256 `{SHA}` (research-findings §1i).",
         f"- **Upstox side rule** [I]: {SIDE_RULE}.",
         "- **R** [M from bars] per §2. **No hit rate is printed, here or anywhere** (§4).",
         "- The full rows, every stamp and every excluded row are in `data/confluence/first_look.json`.", "",
         "## §4 verdicts, per cell", "",
         "| cell | n | mean R | mean R w/o best | zone-alone n | zone-alone mean R | difference | largest day's share | verdict |",
         "|---|---|---|---|---|---|---|---|---|"]
    for c in CELLS:
        v = res["cells"][c]["verdict"]
        share = "—" if v["largest_day_share"] is None else f"{v['largest_day_share'] * 100:.0f}%"
        L.append(f"| {c} | {v['n']} | {_f(v['mean_R'])} | {_f(v['mean_R_ex_best'])} | {v['control_n']} | "
                 f"{_f(v['control_mean_R'])} | {_f(v['diff'])} | {share} | **{v['verdict']}** |")
    L += ["", "## §5 both sides of the option (recorded; not part of the bar)", "",
          "Premium points per unit [M], the same entries, buy = the with-side ATM option, sell = the opposite ATM. "
          "Equal weight; neither is the default.", ""]
    for c in CELLS:
        x = res["cells"][c]["expression"]
        if not x["rows"]:
            continue
        L.append(f"**{c}** -- " + (x["why"] if x["summary"] is None else
                 f"n {x['summary']['n']}: buy {x['summary']['buy_mean_pts']:+.2f} "
                 f"(w/o best {x['summary']['buy_mean_pts_ex_best']:+.2f}) · sell {x['summary']['sell_mean_pts']:+.2f} "
                 f"(w/o best {x['summary']['sell_mean_pts_ex_best']:+.2f}) pts"))
        L += ["", "| day | index | entry | strike | buy | entry → exit | pts | sell | entry → exit | pts |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        L += [f"| {r['day']} | {r['index']} | {r['entry_t']} | {r['k']:.0f} | {r['buy']} | {r['buy_px']} → "
              f"{r['buy_exit']} | {r['buy_pts']:+.2f} | {r['sell']} | {r['sell_px']} → {r['sell_exit']} | "
              f"{r['sell_pts']:+.2f} |" for r in x["rows"]]
        L.append("")
    L += ["## Days (§6)", "", "| day | index | zone rows | chain | book | scored | why not |", "|---|---|---|---|---|---|---|"]
    L += [f"| {d['day']} | {d['index']} | {d['zone']} | {'yes' if d['chain'] else '—'} | {'yes' if d['book'] else '—'} "
          f"| {'yes' if d.get('scoreable') else '—'} | {d['why'] or ''} |" for d in res["days"]]
    L += ["", "## Excluded rows", ""]
    L += [f"- {n} · {w}" for w, n in collections.Counter(
        x["why"] if not x["why"].startswith("cached close") else "cached close differs from the logged px"
        for x in res["excluded"]).most_common()] or ["- none"]
    L += ["", "## Readings chosen where the text was not literal", ""] + [f"{k}. {r}" for k, r in
                                                                           enumerate(res["readings"], 1)]
    L += ["", "## Re-runs (§6: only to fix a bug that changes no definition)", ""]
    L += [f"- {r['at']}: {r['why']}" for r in res["reruns"]] or ["- none: this is the first and only run."]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--run", action="store_true", help="THE one-shot (writes FIRST-LOOK.md + first_look.json)")
    g.add_argument("--rerun", metavar="WHY", help="a logged re-run to fix a bug that changes no definition")
    g.add_argument("--look-amendment-2", action="store_true", dest="look",
                   help="§1k's one look: the one-shot, run on Mary's request, with §1k's descriptive extras")
    a = ap.parse_args(argv)
    os.chdir(HERE)
    if not sha_ok():
        print(f"REFUSED: {PREREG} no longer hashes to the anchored {SHA[:8]}…; it must never be edited.")
        return 2
    run = a.run or bool(a.rerun) or a.look
    if (a.run or a.look) and os.path.exists(OUT_JSON):
        print(f"REFUSED: the one-shot / §1k look already ran ({OUT_JSON}). A re-run needs --rerun WHY (§6).")
        return 2
    lg = confluence_log.logged()
    day_recs = days(lg)
    entries, excluded = collect(day_recs, run=run, lg=lg)
    if not run:
        print_dry(day_recs, entries, excluded)
        return 0
    reruns = list(confluence_log._rows(RERUNS))
    if a.rerun:
        reruns.append({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "why": a.rerun})
    res = result(day_recs, entries, excluded, reruns)
    res["amendment"] = AMENDMENT if a.look else None
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    if a.rerun:
        with open(RERUNS, "a", encoding="utf-8") as f:
            f.write(json.dumps(reruns[-1]) + "\n")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    if a.look:                                   # the look's document is docs/setup-review/LOOK-2026-10-21.md
        print(f"FADE one look -> {OUT_JSON}. RAN UNDER {AMENDMENT}.")
        return 0
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(markdown(res))
    print(markdown(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
