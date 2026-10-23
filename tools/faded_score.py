"""tools/faded_score.py -- FADE-D's dry counts, its gated verdict and the in-sample description (FADE-D-PREREG.md, §1n).

    python tools/faded_score.py                     DRY, the default: the forward log's FADE-D rows from 2026-10-22 per
                                                    cell -- episodes, location bars (the control), the readings that
                                                    held, entries. No R, nothing written.
    python tools/faded_score.py --run               THE VERDICT (§1i §4, per cell), REFUSED until a cell has n >= 20
                                                    forward entries; a cell is judged once, when it first reaches 20
                                                    (data/confluence/faded_verdict.json), and never re-judged.
    python tools/faded_score.py --describe-in-sample [--day YYYY-MM-DD ...]
                                                    the recorded days before 2026-10-22 (21 Oct motivated the rule): every
                                                    episode's readings at each 5-min close, its entry, HOLD v2 and the
                                                    VWAP-target exit, and the control rows. Labelled IN-SAMPLE, NEVER
                                                    counted.

Every mode refuses unless FADE-D-PREREG.md still hashes to the sha256 anchored in research-findings §1n. The rows are
faded.py's, built by confluence_log.build_faded from confluence_log.faded_inputs -- the forward log's own loader. The
exits are faded.exits (hold2.exit_v2 and confluence.outcome) on hold2_score's memoised inputs. NO HIT RATE ANYWHERE.
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
for p in (HERE, os.path.join(HERE, "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import confluence as C   # noqa: E402
import confluence_log    # noqa: E402
import faded             # noqa: E402
import hold2_score       # noqa: E402

PREREG = os.path.join(HERE, "docs", "setup-review", "FADE-D-PREREG.md")
SHA = "3fd5e84ed3b7fb2a2972a3bb64a4ff719a1313f0909ee45b0f8b1316ea31f237"
FORWARD_FROM = "2026-10-22"                  # §Scope: forward only; every day before it is in-sample, never counted
OUT_JSON = os.path.join("data", "confluence", "faded_verdict.json")
INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
GROUPS = ("NIFTY+SENSEX", "BANKNIFTY")
CELLS = [f"{s} {g}" for s in ("SELL", "BUY") for g in GROUPS]
IN_SAMPLE = ("IN-SAMPLE -- these days were looked at (21 Oct motivated FADE-D): described so the rule's behaviour can be "
             "seen, NEVER counted toward the pass bar. No hit rate.")

# Where FADE-D-PREREG's text is not literal. Fixed before any forward row exists; a change is a new registration.
READINGS = [
    "Bars: confluence_log.push_bars -- the closed 5-min futures bars HOLD v2 reads (NIFTY GoCharting, the Upstox bar of a "
    "slot only where GoCharting lacks one; BANKNIFTY / SENSEX Upstox). A bar is named by its opening minute, a reading "
    "and an entry by the bar's close. Delta is the bar's own (lots).",
    "New session high (low): a bar whose high tops (low undercuts) every earlier bar's; the 09:15 bar never is one. A "
    "record that does not begin with the 09:15 bar cannot say 'new session high': no high / low is a location then and "
    "2a is 'could not check' (zone rows still locate).",
    "Zone location: trigger_log's zone ARM and ENTRY rows (non-outcome fields only), SELL = u2, BUY = d2. A 3-min row "
    "labelled t is known at its close t+3 and sits in the 5-min bar holding minute t+2.",
    "The evaluation window at a close c is the 30 min to c (bars closing at c-30 or later). An EPISODE is a run of same-"
    "side location bars each closing within 30 min of the one before; its window runs from the first location's close to "
    "the last's + 30, so condition 1 holds at every close of it. One row and at most one entry per episode.",
    "2a: some new-high bar N closing in the window has delta(N) / the largest positive delta of N's up-leg <= 0.25; the "
    "up-leg runs from the bar holding the session's lowest low before N (the latest on a tie; the open when N is first) "
    "through N itself. A delta at or below zero passes by arithmetic; a leg with no positive bar has no buying to fade "
    "(ratio None, passes). BUY mirrored (negative deltas, the down-leg from the last session high).",
    "2b: at the close, that bar's delta < 0 and CVD < its peak over the current up-leg (from the session low before the "
    "session-high bar as of the close, through the close). CVD = the running sum of the 5-min bars' delta from the first "
    "bar; the drawdown is logged in delta units. BUY mirrored.",
    "3: the PE lead = 100 x (PE - CE) / (|PE| + |CE|), PE / CE = aaj likha (OI - yesterday's close OI) summed over "
    "read.writers' nine strikes (ATM +/- 4 at that chain row, narrowed symmetrically at a window edge; m < 2 could not "
    "check). The prereg's '÷ (PE + CE)' is read as read.py's own |PE| + |CE| (its A: the lead is -100 A, bounded +/- 100). "
    "It is read at each 5-min close (the setup's clock) on the last chain row before the close's second; a row more than "
    "fronts.STALE_MIN minutes old is 'could not check'. The SESSION PEAK is the highest of those 5-min reads so far (the "
    "latest on a tie): a per-row or per-minute max would be a max of noise. '15 min ago' = the read at c-15. Pass: peak - "
    "now >= 10 AND (the peak at c-15 or later, OR the read at c-15 minus now >= 10). BUY: the CE lead (= -PE lead).",
    "Entry: the first close of the episode's window with 1, 2a, 2b and 3 true there, closing at or before 15:00. "
    "'Could not check' is never true. AMENDMENT 1 (§1n): the VWAP side is no condition, only a STAMP (each close's px "
    "and the entry's vwap): the close vs the session VWAP = market.js vwapSeries (hlc3, volume-weighted from the first "
    "bar) over the same 5-min bars (hold2.sigmas' recurrence).",
    "Stop: the session high (low) of the 5-min bars through the entry bar + (-) 0.25U, U = max(sigma, 0.1% of that "
    "extreme), sigma = hold2.sigma_at at the entry close (the 5-min vwapSeries sigma, HOLD v2's line unit); then risk at "
    "least 0.5 sigma from E.",
    "Exit: FADE-D uses HOLD v2 §exit only; the FADE->RIDE clause belongs to §1i entries (a reading, 2026-10-21). "
    "hold2.exit_v2 with target=False: line0 = the stop, the cached 1-min futures session (data/backtest), the push trail "
    "on the same 5-min source bars and references (SENSEX inactive: 'push ? ref nahi'), the lock at 2R, gave-up at the "
    "3-min closes (§1m Amendments 1 and 2), 15:20; no VWAP convert-or-exit decision. The REFERENCE exit is "
    "confluence.outcome: the stop, the first 1-min touch of its own session VWAP, else the 15:20 mark -- recorded "
    "'n/a (entry across VWAP)' for an entry stamped across VWAP (its target lies behind the entry). R on |stop - E|; "
    "exits named by the 1-min bar's END.",
    "Control: every location bar of the same index-days, entered at its own close with the same stop, the same exits "
    "and the 15:00 cutoff (a bar after it is listed, never entered); the VWAP side is stamped, never a filter "
    "(Amendment 1).",
    "Cells: SELL / BUY x NIFTY+SENSEX / BANKNIFTY. §1i §4 via confluence.verdict on HOLD v2's R (n >= 20, mean >= +0.25, "
    "drop-best > 0, beats the control by >= +0.20, no day > 40%); only the forward log's FADE-D rows from 2026-10-22 "
    "count; each cell is judged once, when it first has 20 entries.",
]


def sha_ok(path=PREREG):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest() == SHA


def cell(side, idx):
    return f"{side} {'BANKNIFTY' if idx == 'BANKNIFTY' else 'NIFTY+SENSEX'}"


def forward_rows(path=None):
    """The forward log's FADE-D rows from FORWARD_FROM, oldest first."""
    return [r for r in confluence_log._rows(path or confluence_log.PATH)
            if r.get("setup") == "FADE-D" and r.get("index") in INDICES and r.get("side") in ("SELL", "BUY")
            and isinstance(r.get("day"), str) and r["day"] >= FORWARD_FROM]


def counts(rows):
    """{cell: Counter}: rows (episodes), locs (control bars), a / b / oi (some close of the window read ok), all (one
    close with 2a, 2b and 3), entries."""
    tab = {c: collections.Counter() for c in CELLS}
    for r in rows:
        t = tab[cell(r["side"], r["index"])]
        t["rows"] += 1
        t["locs"] += len(r.get("locs") or ())
        bs = r.get("bars") or ()
        for k in ("a", "b", "oi"):
            t[k] += any((b.get(k) or {}).get("ok") is True for b in bs)
        t["all"] += any(all((b.get(k) or {}).get("ok") is True for k in ("a", "b", "oi")) for b in bs)
        t["entries"] += r.get("entry") is not None
    return tab


def print_dry(rows):
    print(f"FADE-D -- DRY (counts only; no R, nothing written). {faded.REV}")
    print("\nREADINGS (where FADE-D-PREREG's text is not literal)")
    for k, r in enumerate(READINGS, 1):
        print(f"  {k}. {r}")
    print(f"\nFORWARD ROWS from {FORWARD_FROM} (data/confluence_log.jsonl, setup FADE-D), per cell:")
    keys, heads = ("rows", "locs", "a", "b", "oi", "all", "entries"), ("episodes", "loc bars", "2a ok", "2b ok", "3 ok",
                                                                       "2a+2b+3", "FADE-D")
    print(f"  {'cell':<20}" + "".join(f"{h:>10}" for h in heads) + "  gate")
    tab = counts(rows)
    for c in CELLS:
        t = tab[c]
        print(f"  {c:<20}" + "".join(f"{t[k]:>10}" for k in keys)
              + f"  {'due: --run judges it' if t['entries'] >= C.PASS_N else f'needs n >= {C.PASS_N}'}")
    print("  (ok = some 5-min close of the episode's window read ok; 2a+2b+3 = all three on one close; FADE-D = an entry: "
          "2a+2b+3 by 15:00, the VWAP side only stamped, Amendment 1)")
    print(f"\n{IN_SAMPLE.split(' -- ')[0]}: every day before {FORWARD_FROM} is never counted "
          "(python tools/faded_score.py --describe-in-sample).")


# ---- the trades -----------------------------------------------------------------------------------------------------------

def _scored(idx, day, entry, D):
    """faded.exits for one entry -> {"v2", "vwap_ref"} or {"why"}."""
    S = D.fade(idx, day)
    if S is None:
        return {"why": "no cached 1-min futures session in data/backtest"}
    P, pwhy, _refs, b5 = D.pushes(idx, day)
    return faded.exits(entry, S["sess"], S["chain"], P, b5, pwhy)


def controls(row, bars5):
    """The control entries of one row: each location bar entered at its close (§ Control), or the reason it is not."""
    by = {faded.hm(faded.close(b)): j for j, b in enumerate(bars5)}
    vw = faded.vwaps(bars5)
    out = []
    for L in row.get("locs") or ():
        j = by.get(L["close"])
        if j is None:
            out.append({"loc": L, "why": "its bar is not in the 5-min record now"})
        elif faded.close(bars5[j]) > faded.CUTOFF:
            out.append({"loc": L, "why": "closes after 15:00"})
        else:
            out.append({"loc": L, "entry": dict(faded.trade(row["side"], bars5, j),
                                                vwap=faded.stamp(row["side"], bars5[j], vw[j]))})
    return out


def verdict_cell(c, rows, D):
    trades, control, skipped = [], [], []
    bars = {}
    for r in rows:
        key = (r["index"], r["day"])
        if key not in bars:
            bars[key] = confluence_log.faded_inputs(r["index"], r["day"], lead=False)["bars5"]
        for x in controls(r, bars[key]):
            s = _scored(r["index"], r["day"], x["entry"], D) if x.get("entry") else {}
            if (s.get("v2") or {}).get("R") is not None:
                control.append({"day": r["day"], "R": s["v2"]["R"]})
        if r.get("entry"):
            s = _scored(r["index"], r["day"], r["entry"], D)
            if (s.get("v2") or {}).get("R") is None:
                skipped.append({"day": r["day"], "index": r["index"], "t": r["entry"]["t"], "why": s.get("why")})
            else:
                trades.append({"day": r["day"], "index": r["index"], "t": r["entry"]["t"], "R": s["v2"]["R"],
                               "vwap_ref_R": (s.get("vwap_ref") or {}).get("R")})
    return {"verdict": C.verdict(trades, control), "trades": trades, "skipped": skipped,
            "run_at": time.strftime("%Y-%m-%d %H:%M:%S")}


# ---- the in-sample description --------------------------------------------------------------------------------------------

def _f(v, sign=True):
    return "?" if v is None else f"{v:+,.1f}" if sign else f"{v:,.1f}"


def _ok(v):
    return "✓" if v is True else "✗" if v is False else "?"


def _pct(r):
    return "-" if r is None else f"{r * 100:.0f}%"


def line(ev):
    """One close's readings, in one line."""
    a, b, oi, px = ev["a"], ev["b"], ev["oi"], ev["px"]
    best = min((x for x in a["bars"] if x["ratio"] is not None), key=lambda x: x["ratio"], default=None)
    sa = (f"{a['why']}" if not a["bars"] else
          f"{len(a['bars'])} new-ext bar(s), lowest {best['bar']} {best['delta']:+,} = {_pct(best['ratio'])} of "
          f"{best['big']:+,} ({best['big_bar']})" if best else f"{a['bars'][-1]['bar']} no same-direction bar in its leg")
    chg = "?" if oi["chg15"] is None else f"{oi['chg15']:+.1f}"
    so = (oi["why"] if oi["now"] is None else
          f"{oi['side']} lead {oi['now']:+.1f}, peak {oi['peak']:+.1f} @{oi['peak_t']} (off {oi['off']:.1f}), Δ15 {chg}")
    vw = "?" if px["vwap"] is None else f"{px['vwap']:,.1f}"
    return (f"    {ev['close']} [{ev['bar']} bar]{' LATE' if ev['late'] else ''}  2a {_ok(a['ok'])} {sa} | 2b {_ok(b['ok'])} "
            f"δ {b['delta']:+,}, CVD {b['cvd']:+,} vs leg {'peak' if ev['oi']['side'] == 'PE' else 'low'} {b['peak']:+,} "
            f"after {b['peak_close']} (dd {b['dd']:,}) | "
            f"3 {_ok(oi['ok'])} {so} | VWAP stamp {'far' if px['ok'] else 'across' if px['ok'] is False else '?'} "
            f"{px['c']:,.1f} vs {vw}")


def _exit_text(s):
    if s.get("why"):
        return f"could not score -- {s['why']}"
    v2, ref = s.get("v2") or {}, s.get("vwap_ref") or {}
    rtxt = (ref.get("how") if ref.get("R") is None else
            f"{ref.get('how')} {ref.get('exit_t')} @ {ref.get('exit') or 0:,.1f} R {ref['R']:+.2f}")
    moves = "; push moves " + ", ".join(f"{m['t']} -> {m['to']:,.1f}" for m in v2["moves"]) if v2.get("moves") else ""
    mun = ("; unwinding, no exit: " + ", ".join(f"{x['t']} {x['read']}" for x in v2["munafa"])) if v2.get("munafa") else ""
    return (f"HOLD v2 {v2.get('how')} {v2.get('exit_t')} @ {v2.get('exit') or 0:,.1f} R {v2.get('R') or 0:+.2f} "
            f"(MFE {v2.get('mfe')}, MAE {v2.get('mae')}{moves}{mun}{'; ' + v2['trail'] if v2.get('trail') else ''}) "
            f"· VWAP-target ref {rtxt}")


def describe_day(idx, day, D, out=print):
    """Every episode of (idx, day): the readings at each close, the entry with both exits, and the control rows."""
    inp = confluence_log.faded_inputs(idx, day)
    rows = [confluence_log.build_faded(idx, day, e, inp) for e in faded.episodes(inp["bars5"], inp["zone"])]
    src = collections.Counter(b.get("src") for b in inp["bars5"])
    out(f"\n== {day} {idx}: {len(inp['bars5'])} closed 5-min bars ({', '.join(f'{k} {n}' for k, n in src.items())}), "
        f"{len(inp['zone'])} zone rows, {len(rows)} episodes{' -- ' + inp['why'] if inp['why'] else ''}")
    for r in rows:
        locs = "; ".join(f"{L['bar']} bar ({' + '.join(L['why'])})" for L in r["locs"])
        out(f"  {r['side']} episode {r['t']}-{r['end']}: location bars {locs}")
        for ev in r["bars"]:
            out(line(ev))
        e = r["entry"]
        if e:
            vs = e.get("vwap") or {}
            out(f"    ENTRY {r['side']} {e['t']} close [{e['bar']} bar] E {e['E']:,.1f} · extreme {e['extreme']:,.1f} · "
                f"sigma {e['sigma']} U {e['U']} · stop {e['stop']:,.1f} (risk {abs(e['stop'] - e['E']):,.1f}) · VWAP stamp "
                f"{vs.get('side')} ({_f(vs.get('pts'))} vs {_f(vs.get('vwap'), sign=False)})")
            out(f"      {_exit_text(_scored(idx, day, e, D))}")
        else:
            out("    no FADE-D entry in this episode")
        for x in controls(r, inp["bars5"]):
            L = x["loc"]
            if x.get("entry"):
                ce = x["entry"]
                out(f"    control {L['bar']} bar @ {ce['E']:,.1f} stop {ce['stop']:,.1f}: {_exit_text(_scored(idx, day, ce, D))}")
            else:
                out(f"    control {L['bar']} bar: not entered -- {x['why']}")
    return rows


def recorded_days():
    """Every day with a chain record, before FORWARD_FROM."""
    ds = {os.path.basename(p).split("_")[2][:10] for p in glob.glob(os.path.join("data", "chain", "chain_*_*.jsonl*"))}
    return sorted(d for d in ds if d < FORWARD_FROM)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--run", action="store_true", help="the verdict, gated: a cell with n >= 20 forward entries")
    g.add_argument("--describe-in-sample", action="store_true", dest="describe",
                   help="the days before 2026-10-22, IN-SAMPLE, never counted")
    ap.add_argument("--day", action="append", help="with --describe-in-sample: only this day (repeatable)")
    a = ap.parse_args(argv)
    os.chdir(HERE)
    if not sha_ok():
        print(f"REFUSED: {PREREG} no longer hashes to the anchored {SHA[:8]}...; it must never be edited.")
        return 2
    if a.describe:
        days = a.day or recorded_days()
        if any(d >= FORWARD_FROM for d in days):
            print(f"REFUSED: {FORWARD_FROM} onward is forward data, never described as in-sample.")
            return 2
        print(f"FADE-D -- {IN_SAMPLE}\n{faded.REV}\n")
        print("READINGS (where FADE-D-PREREG's text is not literal)")
        for k, r in enumerate(READINGS, 1):
            print(f"  {k}. {r}")
        D = hold2_score.Days()
        for day in days:
            for idx in INDICES:
                describe_day(idx, day, D, print)
        print(f"\n  IN-SAMPLE, NEVER counted (§1n: forward only, from {FORWARD_FROM}).")
        return 0
    rows = forward_rows()
    if not a.run:
        print_dry(rows)
        return 0
    try:
        with open(OUT_JSON, encoding="utf-8") as f:
            judged = json.load(f).get("cells") or {}
    except (OSError, ValueError):
        judged = {}
    tab = counts(rows)
    todo = [c for c in CELLS if tab[c]["entries"] >= C.PASS_N and c not in judged]
    if not todo:
        print(f"REFUSED (§1n): no cell is due -- forward FADE-D entries from {FORWARD_FROM}: "
              + ", ".join(f"{c} {tab[c]['entries']}" for c in CELLS)
              + f"; a cell is judged once, at n >= {C.PASS_N}. No R is computed.")
        return 2
    D = hold2_score.Days()
    for c in todo:
        judged[c] = verdict_cell(c, [r for r in rows if cell(r["side"], r["index"]) == c], D)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"prereg": os.path.relpath(PREREG, HERE), "sha256": SHA, "rev": faded.REV, "readings": READINGS,
                   "forward_from": FORWARD_FROM, "cells": judged}, f, indent=1, default=str)
    print(f"FADE-D verdict ({faded.REV}) -> {OUT_JSON}. No hit rate is printed, here or anywhere.")
    print(f"  {'cell':<20}{'n':>4}{'mean R':>9}{'w/o best':>10}{'ctl n':>7}{'ctl R':>8}{'diff':>8}{'day share':>11}  verdict")
    f2 = lambda v: "-" if v is None else f"{v:+.2f}"          # noqa: E731
    for c in todo:
        v = judged[c]["verdict"]
        share = "-" if v["largest_day_share"] is None else f"{v['largest_day_share'] * 100:.0f}%"
        print(f"  {c:<20}{v['n']:>4}{f2(v['mean_R']):>9}{f2(v['mean_R_ex_best']):>10}{v['control_n']:>7}"
              f"{f2(v['control_mean_R']):>8}{f2(v['diff']):>8}{share:>11}  {v['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
