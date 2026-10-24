"""tools/hold2_score.py -- HOLD v2 scored beside v1 on the registered FADE and RIDE entries (HOLD-V2-PREREG.md, §1m).

    python tools/hold2_score.py                       DRY, the default: the forward entries per group. No R, nothing written.
    python tools/hold2_score.py --run                 THE VERDICT, paired v2 vs v1, REFUSED until a group (FADE: §1i's 8
                                                      cells pooled; RIDE: §1j's 4) has n >= 20 forward entries from
                                                      2026-10-22 on. A group is judged once, when it first reaches 20
                                                      (data/confluence/hold2_verdict.json); a judged group is never re-judged.
    python tools/hold2_score.py --rerun WHY           re-judge the judged groups, only to fix a bug that changes no
                                                      definition; WHY is logged in data/confluence/hold2_reruns.jsonl.
    python tools/hold2_score.py --describe-in-sample [--trade ID]
                                                      the entries on or before 21 Oct (the §1k look's FADE and RIDE entries
                                                      and 21 Oct's forward rows) with their v1 and v2 rows, labelled
                                                      IN-SAMPLE and NEVER counted; --trade adds her marked trade's v2 line
                                                      through the day, the way her hold window would have shown it.

Every mode refuses unless HOLD-V2-PREREG.md still hashes to the sha256 anchored in research-findings §1m.

THE PAIRS: each registered entry exactly as logged (the forward log's `entry`; the §1k look's frozen trades), its v1 exit
recomputed by its own scorer's rule (confluence.outcome / ride.outcome) and its v2 exit by hold2.exit_v2, both on the
same 1-min bars (FADE: the cached 1-min futures session, data/backtest; RIDE: the futures ticks, v2feed). ΔR = R(v2) -
R(v1). §1m's bar per group: n >= 20, mean ΔR >= +0.20, mean ΔR without the best pair > 0, and if the total ΔR > 0 no day
supplies more than 40% of it -> PASS; n >= 20 and mean ΔR <= 0 -> FAIL; else INCONCLUSIVE. NO HIT RATE ANYWHERE.
"""
import argparse
import collections
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # tapemap/
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import book_log          # noqa: E402
import confluence as C   # noqa: E402
import confluence_log    # noqa: E402
import fold              # noqa: E402
import frame_v2          # noqa: E402
import fronts            # noqa: E402
import hold2             # noqa: E402
import ladder            # noqa: E402
import ride              # noqa: E402
import sensex_flow       # noqa: E402

PREREG = os.path.join(HERE, "docs", "setup-review", "HOLD-V2-PREREG.md")
SHA = "fca358a2b66337f4e51b38edec55281c87f9b16a62be895ad9a58f2548f5d9a6"
FORWARD_FROM = "2026-10-22"                  # §1m: forward only; every entry before it is in-sample, never counted
OUT_JSON = os.path.join("data", "confluence", "hold2_verdict.json")
RERUNS = os.path.join("data", "confluence", "hold2_reruns.jsonl")
LOOK = {"FADE": os.path.join("data", "confluence", "first_look.json"),            # §1k's frozen entries
        "RIDE": os.path.join("data", "confluence", "ride_first_look.json")}
INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
GROUPS = ("FADE", "RIDE")
PASS_N, PASS_MEAN, DAY_SHARE = 20, 0.20, 0.40                                     # §1m's pass bar
IN_SAMPLE = ("IN-SAMPLE -- these days were looked at under §1k (and 21 Oct motivated v2): described here so v2's "
             "behaviour can be seen, NEVER counted toward §1m's bar. No hit rate.")

# Where HOLD-V2-PREREG's text is not literal. Fixed before any forward pair exists; a change is a new registration.
READINGS = [
    "PUSH = v2.js flowState's PUSH (orderflow-desk src/engine/v2.js, v2.5) ported line for line (hold2.state): SIZE = "
    "|delta| / the same 15-min slot's median |delta|, at or above the table's p90 (q[90]), the bar not thin (volume at or "
    "under the slot's p10), R = sign(delta)(close - open) / the slot's median range >= the table's res_min (0.25). The "
    "table is rank_build.flow_ref over the source's own record strictly before the day; for GoCharting it equals the "
    "day's rank_ref `flow` section, the one the extension ranks with (checked 9-21 Oct). The port was run against the "
    "extension's own code through node on 9, 12, 13, 16, 19 and 21 Oct: the same state on every bar.",
    "Sources: NIFTY's GoCharting bar where it has a candle, delta and volume, else the Upstox (ux) bar of the same slot, "
    "ranked against the Upstox table; BANKNIFTY Upstox. The Upstox table is rank_build.flow_ref over the ux record's "
    "days before the day -- the read section's slot reference carries no median range, which R needs. SENSEX has no "
    "usable 5-min reference (rank.BAR_MIN 15: its 5-min bars are not rankable, FLOW-STATE §5): before 2026-10-25 its "
    "push trail is inactive ('push ? ref nahi', push_src SENSEX-ux); from 2026-10-25 (§1q, HOLD v2 Amendment 3) a "
    "SENSEX line moves on NIFTY's pushes, at SENSEX's own same-slot 5-min open + 0.25U (push_src NIFTY).",
    "U = max(sigma, 0.1% of the origin), sigma = market.js vwapSeries (hlc3, volume-weighted from the first bar) over the "
    "same 5-min source bars at the push bar: the extension's push-line unit, so the v2 line sits where her chart's PUSH "
    "line fails.",
    "'After entry' = a push bar CLOSING after the entry close. 'Between the line and price' = strictly between the line "
    "and the trade's last 1-min close at the push bar's close; the move must also bring the line nearer price. A push "
    "acts from its bar's close on.",
    "The lock: once a 1-min bar takes MFE to >= 2R (initial risk), the line is never worse than the entry from the next "
    "1-min bar on (the order of prices inside a bar is unknown).",
    "SOMEBODY GAVE UP: the trend-side front (DOWN: CE, UP: PE) read at each 3-min close's last minute as RIDE's v1 reads "
    "it (fronts.read on the grid cut there; RIDE's FLIP trail is not v2's); FADE uses its cached 3-min series' closes. "
    "AMENDMENT 1 (§1m): it exits only when the front reads UNWINDING AND the chain spot at that close's last minute is "
    "on its writers' losing side of the chain spot at the front's peak minute (fronts.read's peak_at on the same cut): "
    "CE above, PE below (strictly). Unwinding with price level or still in their favour is stamped 'munafa booking', "
    "never an exit; a spot that cannot be read is stamped too, never a verdict. AMENDMENT 2: 'losing' means beyond the "
    "peak-minute spot by more than 0.25U, U = max(sigma, 0.1% of the spot at the close), sigma = the 5-min vwapSeries "
    "sigma of the push source bars closed by then (the line's own U; on SENSEX its own bars' sigma); "
    "inside the buffer is stamped 'munafa / chop (within 0.25U)', never an exit. RIDE v1 is unchanged (the frozen "
    "baseline). A close in a 1-min hole is read at the next bar's open, never skipped. At one minute: the FADE -> RIDE "
    "restart, then gave-up, then pushes.",
    "FADE -> RIDE: the VWAP touch is §1i's first passage (each 1-min bar's own session VWAP; a bar touching the line and "
    "VWAP is the line first). It is decided at the touch bar's 3-min close by ride.oi_read / ride.flow_read in the FADE's "
    "direction; 'both hold' = both True (could not check is no hold). Not converting = v1's exit at that VWAP. "
    "Converting: held, the line live from the touch on; at the close the line restarts at that 3-min bar's own VWAP "
    "+/- 0.5 x its sigma, never worse than it was. R stays on the FADE's initial risk.",
    "15:20: the 15:19 bar's close, named '15:20'. v2 times are 1-min bar ENDs; the FADE v1 rows print their exit as an "
    "END too (v1's own record names the bar by its label).",
    "MFE / MAE: points over the 1-min bars from the entry close through the exit bar.",
    "Expressions at the v2 exit (descriptive): FADE confluence.expression (the ATM pair at the entry bar's last chain "
    "minute and at the minute before the v2 exit); RIDE ride.expressions.",
    "The gate: the forward log's FADE / RIDE rows with an entry, on days from 2026-10-22. A group is judged once, when it "
    "first has >= 20 such rows; a pair whose v1 or v2 cannot be scored is listed with its reason and not counted.",
    "Her hold window (display only): the line starts at her thesis invalidation, else the engine's give-up G (the "
    "window's own `inval`, validate_live's rule); E = the engine's entry future; the trail and the lock run from the "
    "first whole minute after her entry. It never changes the window's HOLD / FOLD word.",
]


def sha_ok(path=PREREG):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest() == SHA


# ---- the entries ---------------------------------------------------------------------------------------------------

def forward_entries(path=None):
    """The forward log's FADE and RIDE rows that have an entry, oldest first."""
    out = []
    for r in confluence_log._rows(path or confluence_log.PATH):
        en, g = r.get("entry"), r.get("setup")
        if not en or g not in GROUPS or r.get("index") not in INDICES or not isinstance(r.get("day"), str):
            continue
        d = r.get("d") if g == "RIDE" else (1 if r.get("side") == "BUY" else -1 if r.get("side") == "SELL" else None)
        if d in (1, -1):
            out.append({"setup": g, "day": r["day"], "index": r["index"], "d": d, "trig": r.get("t"), "en": en,
                        "src": "forward log"})
    return out


def look_entries():
    """§1k's frozen entries (the look's own trades, v1 as it scored them), oldest first."""
    out = []
    for g, key in (("FADE", "confluence"), ("RIDE", "ride")):
        try:
            with open(LOOK[g], encoding="utf-8") as f:
                res = json.load(f)
        except (OSError, ValueError):
            continue
        for c, cell in (res.get("cells") or {}).items():
            d = (1 if " BUY " in f" {c} " else -1) if g == "FADE" else (-1 if c.startswith("DOWN") else 1)
            for t in cell.get(key) or ():
                en = {k: t[k] for k in ("E", "sigma", "stop", "line0", "t", "close", "bar") if k in t}
                out.append({"setup": g, "day": t["day"], "index": t["index"], "d": d, "trig": t.get("trigger_t"),
                            "en": en, "src": "§1k look", "look_v1": {k: t.get(k) for k in ("how", "exit_t", "R")}})
    return sorted(out, key=lambda e: (e["day"], e["en"]["t"], e["index"]))


def in_sample():
    """Every entry on or before the day before FORWARD_FROM: the §1k look's, then the forward log's own (21 Oct)."""
    have = {(e["setup"], e["day"], e["index"], e["trig"]) for e in look_entries()}
    fw = [e for e in forward_entries() if e["day"] < FORWARD_FROM and (e["setup"], e["day"], e["index"], e["trig"]) not in have]
    return look_entries() + fw


# ---- the inputs, once per index-day ----------------------------------------------------------------------------------

class Days:
    """The heavy loads, memoised per (index, day)."""

    def __init__(self):
        self.m = {}

    def _get(self, key, fn):
        if key not in self.m:
            self.m[key] = fn()
        return self.m[key]

    def pushes(self, idx, day):
        """(pushes or None, why the trail is inactive, {src: reference days}, the 5-min source bars -- their sigma is U
        for the line and, Amendment 2, for gave-up's buffer, on every index, SENSEX too)."""
        def go():
            refs, why = confluence_log.push_refs(idx, day)
            bars5 = confluence_log.push_bars(idx, day)
            if not refs:
                return None, why, {}, bars5
            return hold2.pushes(bars5, refs), None, {k: len(v["days"]) for k, v in refs.items()}, bars5
        return self._get(("push", idx, day), go)

    def fade(self, idx, day):
        def go():
            sess = confluence_log.session(idx, day)
            if sess is None:
                return None
            inp = confluence_log.inputs(idx, day, sess["expiry"], lg={})
            return dict(sess=sess, chain=inp["chain"], book=inp["book"], gc=inp["gc"])
        return self._get(("fade", idx, day), go)

    def ride(self, idx, day):
        return self._get(("ride", idx, day), lambda: confluence_log.ride_inputs(idx, day, None))


def _fade(e, S, P, pwhy, b5):
    d, en = e["d"], e["en"]
    side = "BUY" if d > 0 else "SELL"
    m = C.band_rotation._minute
    start = C.close_of(en["t"])
    v1 = C.outcome(side, en, start, S["sess"]["ones"])
    if v1:
        v1 = dict(v1, exit_t=C.hm(m(v1["exit_t"]) + 1))                     # its bar's END, as v2 names exits
    ones = [{"s": m(b["t"]) * 60, "h": b["h"], "l": b["l"], "c": b["c"], "vwap": C._num(b.get("vwap"))}
            for b in S["sess"]["ones"] if m(b.get("t")) is not None]
    flat = [C.flat(b) for b in S["sess"]["bars"]]
    by3 = {C.close_of(b["t"]): b for b in flat if C.close_of(b.get("t")) is not None}
    b3 = [{"e": k * 60, "c": b["c"]} for k, b in sorted(by3.items())]
    closes = hold2.closes(d, start, b3, S["chain"], b5)

    def convert(k):
        b = by3.get(k) or {}
        return hold2.fade_convert(d, k, C._num(b.get("vwap")), C.sigma(b) if b else None, S["chain"], S["book"], S["gc"])
    v2 = hold2.exit_v2(d, {"E": en["E"], "line0": en["stop"]}, start, ones, P, closes, target=True, convert=convert,
                       trail_why=pwhy)
    x = (C.expression(side, S["chain"][0], fronts.bar_last_minute(en["t"], C.INTERVAL), ride._chain_min(v2["exit_t"]))
         if v2 and v2["exit_t"] else None)
    return v1, v2, x


def _ride(e, S, P, pwhy, b5):
    d, en = e["d"], e["en"]
    start = frame_v2._sec(en["t"]) // 60
    v1 = ride.outcome(d, en, start, S["ones"], ride.closes_after(d, start, S["b3"], S["rows"], S["chain"]))
    v2 = hold2.exit_v2(d, {"E": en["E"], "line0": en["line0"]}, start, S["ones"], P,
                       hold2.closes(d, start, S["b3"], S["chain"], b5), trail_why=pwhy)
    x = ride.expressions(d, S["chain"][0], en["t"], v2["exit_t"]) if v2 and v2["exit_t"] else None
    return v1, v2, x


def score(e, D):
    """One pair: {"v1", "v2", "dR", "expr", "refs", "why"} -- why is set when either side cannot be scored."""
    P, pwhy, refs, b5 = D.pushes(e["index"], e["day"])
    src = sensex_flow.push_src(e["index"], e["day"])        # SENSEX-NIFTY-FLOW §1.2 (signed 25 Oct; None only if OFF)
    if src == sensex_flow.SRC:                              # from her signing day: the line moves on NIFTY's pushes
        nP, nwhy, _nrefs, _nb5 = D.pushes("NIFTY", e["day"])
        P, pwhy, _skip = sensex_flow.line(nP, nwhy, b5)
    if e["setup"] == "FADE":
        S = D.fade(e["index"], e["day"])
        if S is None:
            return {"why": "no cached 1-min futures session in data/backtest", "refs": refs}
        v1, v2, x = _fade(e, S, P, pwhy, b5)
    else:
        S = D.ride(e["index"], e["day"])
        if not S.get("ones"):
            return {"why": "no 1-min futures bar from the ticks", "refs": refs}
        v1, v2, x = _ride(e, S, P, pwhy, b5)
    ok = v1 and v2 and v1.get("R") is not None and v2.get("R") is not None
    out = {"v1": v1, "v2": v2, "expr": x, "refs": refs, "dR": round(v2["R"] - v1["R"], 4) if ok else None,
           "why": None if ok else "v1 or v2 could not be scored (no 1-min bar after the entry)"}
    return dict(out, push_src=src) if src else out


# ---- §1m's bar -------------------------------------------------------------------------------------------------------

def verdict(pairs):
    """§1m for one group. `pairs` = [{"day", "r1", "r2"}]. Never a hit rate."""
    dr = [p["r2"] - p["r1"] for p in pairs]
    n, mean, ex = len(dr), C._mean(dr), C.drop_best(dr)
    tot = sum(dr)
    days = collections.defaultdict(float)
    for p, x in zip(pairs, dr):
        days[p["day"]] += x
    share = max(days.values()) / tot if tot > 0 else None
    ok = (n >= PASS_N and mean >= PASS_MEAN and ex is not None and ex > 0 and (share is None or share <= DAY_SHARE))
    bad = n >= PASS_N and mean <= 0
    r4 = lambda v: None if v is None else round(v, 4)          # noqa: E731
    return {"n": n, "mean_dR": r4(mean), "mean_dR_ex_best": r4(ex), "largest_day_share": r4(share),
            "mean_R_v1": r4(C._mean([p["r1"] for p in pairs])), "mean_R_v2": r4(C._mean([p["r2"] for p in pairs])),
            "verdict": "PASS" if ok else "FAIL" if bad else "INCONCLUSIVE"}


def due(fw, judged):
    """The groups a --run may judge: >= 20 forward entries and not judged before."""
    n = collections.Counter(e["setup"] for e in fw)
    return [g for g in GROUPS if n[g] >= PASS_N and g not in judged], dict(n)


# ---- printing --------------------------------------------------------------------------------------------------------

def _f(v):
    return "-" if v is None else f"{v:+.2f}"


def _x(e):
    return f"{e['day']} {e['index']:<9} {e['setup']:<4} {'▲' if e['d'] > 0 else '▼'} {e['en']['t']}"


def _moves(v2):
    return "; ".join(f"{m['t']} o {m['origin']:,.1f} -> {m['to']:,.1f} (from {m['from']:,.1f}) at {m['at']}"
                     for m in v2["moves"])


def describe(entries, D, out=print):
    out(f"HOLD v2 -- {IN_SAMPLE}\n{hold2.REV}\n")
    out("READINGS (where HOLD-V2-PREREG's text is not literal)")
    for k, r in enumerate(READINGS, 1):
        out(f"  {k}. {r}")
    out("")
    head = (f"  {'entry':<34}{'E':>10}  {'v1 how':<9}{'exit':>6}{'R':>7}  {'v2 how':<10}{'exit':>6}{'R':>7}{'ΔR':>7}"
            f"{'moves':>6}{'MFE':>8}{'MAE':>8}  refs / note")
    out(head)
    rows = []
    for e in entries:
        s = score(e, D)
        rows.append((e, s))
        v1, v2 = s.get("v1") or {}, s.get("v2") or {}
        refs = " ".join(f"{k}:{n}d" for k, n in (s.get("refs") or {}).items()) or "no ref"
        conv = v2.get("converted")
        note = s.get("why") or ""
        if conv:
            note += (f"VWAP {conv['touch_t']}: {'CONVERTED' if conv.get('ok') else 'not converted'} "
                     f"(OI {conv.get('oi', {}).get('ok')}, FLOW {conv.get('flow', {}).get('ok')}) ")
        if v2.get("trail"):
            note += v2["trail"]
        out(f"  {_x(e):<34}{e['en']['E']:>10,.1f}  {v1.get('how', '-'):<9}{v1.get('exit_t') or '-':>6}{_f(v1.get('R')):>7}"
            f"  {v2.get('how', '-'):<10}{v2.get('exit_t') or '-':>6}{_f(v2.get('R')):>7}{_f(s.get('dR')):>7}"
            f"{v2.get('n_moves', '-'):>6}{v2.get('mfe') if v2.get('mfe') is not None else '-':>8}"
            f"{v2.get('mae') if v2.get('mae') is not None else '-':>8}  {refs} {note}")
        if v2.get("moves"):
            out(f"      push moves: {_moves(v2)}")
        if v2.get("munafa") or v2.get("unwind_cnc"):
            out("      unwinding, no exit -- munafa booking (price in the writers' favour) / chop (within 0.25U): "
                + ", ".join(f"{x['t']} {x['k']:.0f} {x['read']}" for x in v2.get("munafa") or ())
                + (f"; unwinding, price side ? {', '.join(v2['unwind_cnc'])}" if v2.get("unwind_cnc") else ""))
        if v2.get("lock_t"):
            out(f"      lock: MFE >= 2R at {v2['lock_t']} (line never worse than E {e['en']['E']:,.1f} from then)")
        lk = e.get("look_v1")
        if lk and v1 and lk.get("R") is not None and abs(lk["R"] - v1["R"]) > 1e-6:
            out(f"      CHECK: v1 here {v1['R']:+.4f} != the §1k look's {lk['R']:+.4f}")
    out(f"\n  {len(rows)} in-sample entries described; none is counted (§1m: forward only, from {FORWARD_FROM}).")
    return rows


def her_trade(tid, D, out=print):
    """Her marked trade's v2 line through the day, as the hold window would have shown it, IN-SAMPLE."""
    rec = None
    for p in sorted(os.listdir(os.path.join("data", "day_state"))):
        try:
            with open(os.path.join("data", "day_state", p), encoding="utf-8") as f:
                st = json.load(f)
        except (OSError, ValueError):
            continue
        rec = next((t for t in st.get("hold_trades") or () if t.get("id") == tid), None)
        if rec:
            day = st.get("day") or p[4:14]
            break
    if rec is None:
        out(f"no marked trade {tid} in data/day_state")
        return None
    idx = rec["idx"]
    flog = [r for r in confluence_log._rows(os.path.join("data", "fold", f"fold_{idx}_{day}.jsonl"))
            if r.get("trade_id") == tid and r.get("E") is not None]
    if not flog:
        out(f"{tid}: the fold log holds no read of it (E unknown)")
        return None
    seed = flog[0]
    d, E = seed["d"], seed["E"]
    line0 = (rec.get("thesis") or {}).get("inval")
    line0 = line0 if line0 is not None else (seed.get("G") or {}).get("px")
    lad = ladder.Ladder(lot=None, tick=fold.LADDER_TICK, interval_s=60, idx=idx, day=day)   # the engine's own bars
    ones = []
    for r in book_log.read_rows(day, idx):
        b, _f2 = lad.step(r)
        if b and b.get("h") is not None:
            ones.append({"s": (b["t"] // 1000 + 19800) % 86400, "h": b["h"], "l": b["l"], "c": b["c"]})
    snaps = list(confluence_log._rows(confluence_log._chain_path(idx, day)))
    chain = C.chain_grid(snaps)
    h, mi, *_ = map(int, rec["t0"].split(":"))
    start = h * 60 + mi + 1                                     # the first whole minute after her entry
    P, pwhy, refs, b5 = D.pushes(idx, day)
    b3 = hold2.bars3(ones)
    closes = hold2.closes(d, start, b3, chain, b5)
    basis = {r["ts"][:5]: (r.get("units") or {}).get("basis_ix") for r in flog}
    out(f"\nHER TRADE {tid} -- {IN_SAMPLE}")
    out(f"  {idx} {rec['k']:.0f} {rec['side']} {rec['role']}, in {rec['t0']} at {rec['p0']} (E {E:,.1f}f), "
        f"out {rec.get('exit_t') or 'open'}; line0 = the window's invalidation {line0:,.0f}f; refs "
        f"{' '.join(f'{k}:{n}d' for k, n in refs.items()) or pwhy}")
    out(f"  {'time':<6} {'fut':>9}  HOLD v2 (what her window's line would have read)")
    last, res = None, []
    bym = {b["s"] // 60: b for b in ones}
    for M in range(start + 1, hold2.MARK + 1):
        if M - 1 not in bym:
            continue
        fut = bym[M - 1]["c"]
        bx = next((basis[k] for k in sorted(basis, reverse=True) if k <= hold2.hm(M) and basis[k] is not None), None)
        w = hold2.window_line(d, E, line0, start, ones, P, closes, M, fut, bx,
                              hold2.front_now(d, chain, M, hold2.sigma_at(b5, M)), pwhy, rec["t0"][:5])
        fr = w.get("front") or {}
        key = (w.get("line_fut"), w.get("how"), fr.get("state"), fr.get("price") if fr.get("state") == "UNWINDING" else None,
               w.get("gave_up_t"))
        her = " · (her exit)" if rec.get("exit_t") and hold2.hm(M - 1) < rec["exit_t"][:5] <= hold2.hm(M) else ""
        if key != last or her:
            out(f"  {hold2.hm(M):<6} {fut:>9,.1f}  {w.get('text') or w.get('why')}{her}")
            res.append((hold2.hm(M), fut, w))
            last = key
        if w.get("how") not in ("open", None):
            break                                                   # the line was touched (or 15:20): it moves no more
    if res:
        out(f"  {res[0][2]['note']}")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--run", action="store_true", help="the verdict, gated: a group with n >= 20 forward entries")
    g.add_argument("--rerun", metavar="WHY", help="re-judge the judged groups to fix a bug that changes no definition")
    g.add_argument("--describe-in-sample", action="store_true", dest="describe",
                   help="the <= 21 Oct entries' v1 and v2 rows, IN-SAMPLE, never counted")
    ap.add_argument("--trade", metavar="ID", help="with --describe-in-sample: her marked trade's v2 line through the day")
    a = ap.parse_args(argv)
    os.chdir(HERE)
    if not sha_ok():
        print(f"REFUSED: {PREREG} no longer hashes to the anchored {SHA[:8]}...; it must never be edited.")
        return 2
    D = Days()
    if a.describe:
        describe(in_sample(), D)
        if a.trade:
            her_trade(a.trade, D)
        return 0
    fw = [e for e in forward_entries() if e["day"] >= FORWARD_FROM]
    try:
        with open(OUT_JSON, encoding="utf-8") as f:
            done = json.load(f)
    except (OSError, ValueError):
        done = {"groups": {}}
    judged = done.get("groups") or {}
    todo, n = due(fw, judged)
    if not (a.run or a.rerun):
        print(f"HOLD v2 -- DRY (counts only; no R, nothing written). {hold2.REV}")
        print("\nREADINGS (where HOLD-V2-PREREG's text is not literal)")
        for k, r in enumerate(READINGS, 1):
            print(f"  {k}. {r}")
        print(f"\nFORWARD ENTRIES from {FORWARD_FROM} (data/confluence_log.jsonl), per group:")
        for gname in GROUPS:
            st = "judged " + judged[gname]["verdict"]["verdict"] if gname in judged else (
                "due: --run judges it" if gname in todo else f"needs n >= {PASS_N}")
            print(f"  {gname:<5} n {n.get(gname, 0):>3}   {st}")
        return 0
    if a.rerun:
        todo = list(judged)
    if not todo:
        print(f"REFUSED (§1m): no group is due -- forward entries from {FORWARD_FROM}: "
              + ", ".join(f"{g_} {n.get(g_, 0)}" for g_ in GROUPS)
              + f"; a group is judged once, at n >= {PASS_N}. No R is computed.")
        return 2
    reruns = list(confluence_log._rows(RERUNS))
    if a.rerun:
        reruns.append({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "why": a.rerun})
    for gname in todo:
        rows, pairs, skipped = [], [], []
        for e in (x for x in fw if x["setup"] == gname):
            s = score(e, D)
            rows.append({"entry": e, **s})
            if s["dR"] is None:
                skipped.append({"day": e["day"], "index": e["index"], "t": e["en"]["t"], "why": s["why"]})
            else:
                pairs.append({"day": e["day"], "r1": s["v1"]["R"], "r2": s["v2"]["R"]})
        judged[gname] = {"verdict": verdict(pairs), "rows": rows, "skipped": skipped,
                         "run_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    res = {"prereg": os.path.relpath(PREREG, HERE), "sha256": SHA, "rev": hold2.REV, "readings": READINGS,
           "forward_from": FORWARD_FROM, "reruns": reruns, "groups": judged}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    if a.rerun:
        with open(RERUNS, "a", encoding="utf-8") as f:
            f.write(json.dumps(reruns[-1]) + "\n")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"HOLD v2 verdict ({hold2.REV}) -> {OUT_JSON}. No hit rate is printed, here or anywhere.")
    print(f"  {'group':<6}{'n':>4}{'mean ΔR':>9}{'w/o best':>10}{'day share':>11}{'R v1':>8}{'R v2':>8}  verdict")
    for gname in todo:
        v = judged[gname]["verdict"]
        share = "-" if v["largest_day_share"] is None else f"{v['largest_day_share'] * 100:.0f}%"
        print(f"  {gname:<6}{v['n']:>4}{_f(v['mean_dR']):>9}{_f(v['mean_dR_ex_best']):>10}{share:>11}"
              f"{_f(v['mean_R_v1']):>8}{_f(v['mean_R_v2']):>8}  {v['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
