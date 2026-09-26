"""hold.py -- THE HOLD / FOLD WINDOW and THE SIDE READ, exactly as registered.

THE SPEC is docs/hold/PREREG-merged.md rev 4 (sha256 e7f50391...a7744709d0,
anchored in context/research-findings.md §1e), signed by the operator
2026-09-25 01:42. Nothing here is a result: every verdict carries DRAFT until
§7 passes, and a rule changed here is a new registration, never a fix.

PORTED, NOT REINVENTED. The §3 order is Opus's literal probe of the
registration (docs/hold/opus/scratch/xreview/prereg_probe.js, rev2 mode, its
table probe_rev3.txt); the line is docs/hold/fable/hold.js as ported into
docs/hold/opus/verdict.js; the side read is docs/hold/fable/scratch/
side_report.js. test_hold.py replays the registration's own stated examples on
the frozen facts those prototypes were probed with.

INPUT, one record per session minute 09:15..15:29, in the shape
docs/hold/opus/scratch/build_facts.py writes and server._hold_facts builds
from the same pure functions:
    {t, spot, blind?, CE, PE, folds, cvd, cvd_why, flow, flow_why, tr, tr_why, ix}
CE / PE are the NEARER of each side's §1d top 2 (board.nearer) by the running
session-peak OI; `folds` the fold events within 15 min of t, each with `still`
(board.still_folded); cvd / flow grounds' facts on ladder bars closed by t;
tr trendbox's 5m / 15m / 1h words; ix the index's own 1-min candle [c, h, l].

Pure: no I/O, no clock. It gates nothing -- not setup.gate, not the zone
machine, not trigger_log -- and there is no order path.
"""
from __future__ import annotations

import board
import trendbox

PERSIST = 3          # §6: an against-state holds 3 finished minutes
QUIET = 15           # §6: the buyer's clock, in readable minutes
FOLD_LIVE = 15       # §6: a fold is live within 15 min of its stamp AND still folded
ENTRY_SHOWN = 3      # §3 / S6: the entry check heads the window at least this long
CC, NONE, NOT_SHOWN = board.CC, board.NONE, board.NOT_SHOWN
DRAFT = ("DRAFT — pre-registered 2026-09-25 (docs/hold/PREREG-merged.md rev 4), untested; "
         "§7's forward rows decide it, not this screen")
SESSION = [f"{m // 60:02d}:{m % 60:02d}" for m in range(9 * 60 + 15, 15 * 60 + 30)]
UNW, BLD = "UNWINDING", "BUILDING"
ROWS = ("5m", "15m", "1h")

mm, hm = board.mm, board.hm


def read_minute(ts):
    """The last FINISHED minute before a fill (§2): a 13:41:38 fill reads 13:40."""
    return hm(max(mm(ts) - 1, mm("09:15")))


def thesis(side, role):
    """§1's table. d = the direction the thesis needs (a writer's: the danger absent)."""
    d = 1 if (side == "CE") == (role == "long") else -1
    return {"d": d, "buyer": role == "long", "Q": "CE" if d > 0 else "PE", "R": "PE" if d > 0 else "CE"}


def _strip(why):
    return (why or "").replace(CC, "") or None


def _k(k):
    return f"{float(k):,.0f}"


# ---------------------------------------------------------------- the three families
def flow(rec, d):
    """ORDER FLOW [I], board.aggression's strict rule: with / against only when CVD
    is strong AND the prints dominate the same way. -> (state, fact, why)."""
    c, f = rec.get("cvd"), rec.get("flow")
    dirn, _word, fact, why = board.aggression({
        "cvd": c and {"d": c["d"], "rank": c["rank"], "since": c["since"]},
        "flow": f and {"buy": f["b"], "sell": f["s"], "runs_why": f.get("rw")},
        "cvd_why": _strip(rec.get("cvd_why"))})
    if dirn:
        return ("with" if dirn == d else "against"), fact, None
    if fact is None or why == "prints could not be read" or (why or "").startswith("too thin"):
        return "blind", fact, why if (why or "").startswith(CC) else CC + why
    return "flat", fact, why


def trend(rec, th):
    """TREND [I], trendbox's 5m / 15m / 1h. -> (state, rows text)."""
    tr = rec.get("tr")
    if not tr:
        return "blind", CC + (_strip(rec.get("tr_why")) or "no index candle yet")
    w = [tr.get(k) for k in ROWS]
    txt = " · ".join(f"{k} {x or 'forming'}" for k, x in zip(ROWS, w))
    mine, other = ("UP", "DOWN") if th["d"] > 0 else ("DOWN", "UP")
    n_m, n_o = w.count(mine), w.count(other)
    if th["buyer"]:
        st = "for" if n_m >= 2 and n_o == 0 else "against" if n_o >= 2 else "flat"
    else:           # a writer: against when >= 2 read the danger direction; with her when none does and none forms
        forming = any(x not in ("UP", "DOWN", "RANGE") for x in w)
        st = "against" if n_o >= 2 else "for" if n_o == 0 and not forming else "flat"
    return st, txt


def side_of(rec):
    """§10.1: CALLS / PUTS / no side off the same vote, or None = could not check. -> (side, why)."""
    tr = rec.get("tr")
    if not tr:
        return None, CC + (_strip(rec.get("tr_why")) or "no index candle yet")
    w = [tr.get(k) for k in ROWS]
    if any(x not in ("UP", "DOWN", "RANGE") for x in w):
        return None, CC + "a middle row is still forming"
    up, dn = w.count("UP"), w.count("DOWN")
    txt = " · ".join(f"{k} {x}" for k, x in zip(ROWS, w))
    if up >= 2 and dn == 0:
        return "CALLS", txt
    if dn >= 2 and up == 0:
        return "PUTS", txt
    return "no side", txt + " — no side"


# ---------------------------------------------------------------- THE LINE [M]
def pivots(m1, day, asof=None):
    """Confirmed 5-min swing highs / lows of TODAY (trendbox PIV = 2, 09:15-aligned
    closed bars, strict), `confirm` = the last minute of the second bar after the
    pivot. Ported from build_facts.pivots; cut to `asof` so a forming bar is never read."""
    rows = [r for r in trendbox.candles(m1) if r[0] == day and (asof is None or r[1] <= asof)]
    bars, P = trendbox.agg(rows, 5), trendbox.PIV
    out = []
    for i in range(P, len(bars) - P):
        hi = all(bars[i][4] > bars[x][4] for x in range(i - P, i)) and all(bars[i][4] > bars[x][4] for x in range(i + 1, i + 1 + P))
        lo = all(bars[i][5] < bars[x][5] for x in range(i - P, i)) and all(bars[i][5] < bars[x][5] for x in range(i + 1, i + 1 + P))
        conf = hm(trendbox.slot_end(bars[i + P][1], 5))
        if hi:
            out.append({"kind": "H", "price": bars[i][4], "bar": bars[i][1], "confirm": conf})
        if lo:
            out.append({"kind": "L", "price": bars[i][5], "bar": bars[i][1], "confirm": conf})
    return out


def line(minutes, pivs, d, e):
    """§2 THE LINE from entry index `e`: {i: {L, src, room, px, beyond, broken_at}}, or
    {blind} at a minute with no index candle; None when the entry minute has none (the
    line cannot be set, S4). A pivot confirmed at c is taken at the first candle
    minute after c -- verdict.js takes it at c + 1 exactly and so skipped it across a
    candle gap; on a whole record the two are the same. Break = a 1-min CLOSE beyond
    L, buffer 0."""
    bear = d < 0
    kind, word = ("H", "high") if bear else ("L", "low")
    m0 = minutes[e]
    if not m0.get("ix"):
        return None

    def far(p, c):
        return p > c if bear else p < c
    px0, t0 = m0["ix"][0], mm(m0["t"])
    mine = [p for p in pivs if p["kind"] == kind]
    known = sorted((p for p in mine if mm(p["confirm"]) <= t0 and far(p["price"], px0)),
                   key=lambda p: mm(p["bar"]), reverse=True)
    used = set()
    if known:
        L, src = known[0]["price"], f"5m swing {word} {known[0]['bar']}"
        used.add(known[0]["bar"])
    else:
        seen = [m["ix"] for m in minutes[:e + 1] if m.get("ix")]
        L = max(x[1] for x in seen) if bear else min(x[2] for x in seen)
        src = f"session {word} so far, no 5m swing {'above' if bear else 'below'} you yet"
    out, broken, prev = {}, None, px0
    for i in range(e, len(minutes)):
        m = minutes[i]
        if not m.get("ix"):
            out[i] = {"L": L, "src": src, "broken_at": broken, "blind": CC + f"no index candle at {m['t']}"}
            continue
        c, beyond = m["ix"][0], False
        if i > e:
            for p in sorted((p for p in mine if p["bar"] not in used and t0 <= mm(p["confirm"]) < mm(m["t"])),
                            key=lambda p: mm(p["confirm"])):
                used.add(p["bar"])
                if (p["price"] < L if bear else p["price"] > L) and far(p["price"], prev):
                    L, src = p["price"], f"5m swing {word} {p['bar']}"
            beyond = c > L if bear else c < L
            if beyond and broken is None:
                broken = m["t"]
        out[i] = {"L": L, "src": src, "room": round(L - c if bear else c - L), "px": c,
                  "beyond": beyond, "broken_at": broken}
        prev = c
    return out


# ---------------------------------------------------------------- one minute's OI facts
def _front(rec, side):
    """The nearer front on `side`, carrying its side (the frozen fixtures' rows do not)."""
    f = rec.get(side)
    return f and {"side": side, **f}


def _last_fold(rec, side, now):
    live = [f for f in rec.get("folds") or []
            if f["side"] == side and f.get("still") and 0 <= mm(now) - mm(f["t"]) <= FOLD_LIVE]
    return live[-1] if live else None


def _raw(rec, th):
    """PAYERS / HOLDERS [M] for this thesis at one minute, before persistence."""
    c = rec.get("cvd")
    o = {"t": rec["t"], "oi_blind": rec.get("blind"), "dpx": c.get("dpx") if c else None}
    if o["oi_blind"]:
        return o
    q, r = _front(rec, th["Q"]), _front(rec, th["R"])
    both = bool(q and r and q["state"] == UNW and r["state"] == UNW)
    o.update(q=q, r=r, both=both,
             q_pays=bool(not both and q and q["state"] == UNW),
             q_fold=None if both else _last_fold(rec, th["Q"], rec["t"]),
             q_build=bool(q and q["state"] == BLD and q.get("built")),
             r_hold=bool(r and r["state"] == BLD and r.get("built")),
             r_unw=bool(not both and r and r["state"] == UNW),
             r_fold=None if both else _last_fold(rec, th["R"], rec["t"]))
    return o


def _held(rs, i, key):
    """Held PERSIST finished minutes, OI readable in each (§2)."""
    return i - PERSIST + 1 >= 0 and all(not rs[j]["oi_blind"] and rs[j].get(key)
                                        for j in range(i - PERSIST + 1, i + 1))


def _run(rs, i, key):
    n = 0
    while i - n >= 0 and not rs[i - n]["oi_blind"] and rs[i - n].get(key):
        n += 1
    return n


def _fw(f):
    return f"{f['side']} {_k(f['k'])} {f.get('words') or f['state'].lower()}"


# ---------------------------------------------------------------- THE WINDOW (§3, §4)
def read(trade, minutes, pivs, upto=None, prem=None, idx=None):
    """Every finished minute of one trade from its entry read to `upto` (HH:MM,
    default the last record). `trade`: {side CE|PE, role long|short, t0
    HH:MM[:SS], p0, qty}. `prem`: {"c": [...], "o": [...], "src"} aligned to
    `minutes`, or None. -> {ok, rows, entry, fold, th}; rows[-1] is what shows now."""
    th = thesis(trade["side"], trade["role"])
    d, buyer, Q, R = th["d"], th["buyer"], th["Q"], th["R"]
    idx = idx or trade.get("idx") or "the index"
    at = {m["t"]: i for i, m in enumerate(minutes)}
    et = read_minute(trade["t0"])
    if et not in at:
        return {"ok": False, "why": CC + f"no record of {et}, the minute finished before your fill", "th": th}
    e = at[et]
    to = len(minutes) - 1 if upto is None else at.get(upto)
    if to is None or to < e:
        return {"ok": False, "why": CC + f"{upto} is not a finished minute at or after your entry read {et}", "th": th}
    LN = line(minutes, pivs, d, e) or {}
    rs = [_raw(m, th) for m in minutes[:to + 1]]
    p0, qty = trade.get("p0"), trade.get("qty") or 0
    sg = 1 if buyer else -1
    floor = "floor" if R == "PE" else "ceiling"
    rows, latch, heal, readable, paid_at, run = [], None, None, [], {}, None
    for i in range(e, to + 1):
        m, x, ln = minutes[i], rs[i], LN.get(i)
        t = m["t"]
        line_blind = ((ln or {}).get("blind") if ln else
                      CC + f"no index candle at the entry minute {et} — the line cannot be set")
        oi_blind = x["oi_blind"]
        fl_state, fl_fact, fl_why = flow(m, d)
        tr_state, tr_txt = trend(m, th)
        # PAYERS / HOLDERS with persistence, and the writer's own-side clause (§4)
        qA = not oi_blind and _held(rs, i, "q_build")
        rA_raw = not oi_blind and _held(rs, i, "r_unw")
        dpx = x["dpx"]
        squeeze = None if dpx is None else ((dpx > 0) - (dpx < 0)) == -d
        rA = rA_raw if buyer else bool(rA_raw and squeeze)
        rF = None if oi_blind else x.get("r_fold")
        rF_against = bool(rF) and (buyer or bool(squeeze))
        fAg, fWith, tAg = fl_state == "against", fl_state == "with", tr_state == "against"
        if not oi_blind:
            readable.append(i)
            paid_at[i] = bool(x["q_pays"] or x["q_fold"]) or fWith
        last_paid = next((minutes[j]["t"] for j in reversed(readable) if paid_at[j]), None)
        quiet_n = sum(1 for j in readable if not last_paid or mm(minutes[j]["t"]) > mm(last_paid))
        quiet = buyer and len(readable) >= QUIET and not any(paid_at[j] for j in readable[-QUIET:])
        P = _payers(x, oi_blind, qA, rs, i, Q)
        H = _holders(x, oi_blind, rA, rF, squeeze, dpx, buyer, R, floor, rs, i)
        F = {"state": fl_state, "fact": fl_fact, "why": fl_why, "tag": "I"}
        T = {"state": tr_state, "rows": tr_txt, "tag": "I"}
        fam = [f for f in (("OI", P["fact"]) if qA else None, ("FLOW", fl_fact) if fAg else None,
                           ("TREND", tr_txt) if tAg else None) if f]
        # §3 in order, the latch removed (the unlatched state, §7)
        rule, why = None, None
        if line_blind:
            u = "PATA NAHI"
        elif ln["beyond"]:
            u, rule = "FOLD", 3
            why = (f"the line is broken: {idx} closed {ln['px']:,.1f} {'above' if d < 0 else 'below'} "
                   f"your line {ln['L']:,.1f} ({ln['src']})")
        elif qA and rA:
            u, rule, why = "FOLD", 4, f"positioning flipped: {P['fact']}; and {H['fact']}"
        elif quiet:
            u, rule = "FOLD", 5
            why = (f"the reason is gone: nothing has paid in the last {QUIET} readable minutes "
                   f"(paid last {last_paid or 'never since entry'})")
        elif len(fam) >= 2:
            u, rule, why = "FOLD", 6, "two families against: " + " — ".join(f"{k}: {v}" for k, v in fam)
        else:
            w = [f for f in (P["fact"] if buyer and qA else None, H["fact"] if rA else None,
                             H["fold"] if rF_against else None,
                             f"flow against you: {fl_fact}" if fAg else None,
                             f"trend against you: {tr_txt}" if tAg else None) if f]
            u, why = ("WATCH", "; ".join(w)) if w else ("HOLD", None)
        fors = [f for f in (P["fact"] if P["state"] == "for" else None,
                            H["fact"] if H["state"] == "for" else None,
                            H["fold"] if H.get("fold_for") else None,
                            f"flow with you: {fl_fact}" if fWith else None,
                            f"trend with you: {tr_txt}" if tr_state == "for" else None) if f]
        pr = _prem(prem, i, p0, qty, sg)       # never an input to the verdict (§1): noise tag, P&L, footer
        tag = None
        if latch:
            word = "FOLD"
            heal = (heal or t) if u in ("HOLD", "WATCH") else None
            sentence = f"FOLD since {latch['t']} — {latch['why']}" + (
                f" · the break has healed since {heal} — a re-entry is a new trade" if heal else "")
        elif u == "PATA NAHI":
            word, sentence = u, f"PATA NAHI — {line_blind}"
        else:
            word = u
            if u == "FOLD":
                latch = {"t": t, "i": i, "rule": rule, "why": why}
                sentence = f"FOLD — {why}"
            elif u == "WATCH":
                sentence = f"WATCH — {why}"
            elif oi_blind:
                tag, sentence = "structure only", f"HOLD · structure only — OI could not check: {_strip(oi_blind)}"
            elif not fors:
                tag = "nothing paying"
                sentence = (f"HOLD · nothing paying ({quiet_n} min)" if buyer else
                            "HOLD — nothing against you; time is paying the writer")
            elif pr.get("adverse"):
                tag, sentence = "noise", "HOLD · noise — what holds this trade has not changed: " + "; ".join(fors[:2])
            else:
                sentence = "HOLD — the reason stands: " + "; ".join(fors[:2])
            if oi_blind and u in ("WATCH", "FOLD"):
                sentence += f" (structure only — OI could not check: {_strip(oi_blind)})"
        if run is None or run[0] != word:
            run = (word, t)
        blind = [b for b in (line_blind, oi_blind, F["why"] if fl_state == "blind" else None,
                             tr_txt if tr_state == "blind" else None) if b]
        rows.append({
            "t": t, "verdict": word, "tag": tag, "sentence": sentence,
            "since": latch["t"] if latch else run[1],
            "fold_rule": latch["rule"] if latch else None, "unlatched": u, "healed_since": heal,
            "line": ({"L": round(ln["L"], 2), "src": ln["src"], "room": ln.get("room"), "px": ln.get("px"),
                      "broken_at": ln.get("broken_at"), "blind": ln.get("blind"), "tag": "M"} if ln else
                     {"blind": line_blind, "tag": "M"}),
            "payers": P, "holders": H, "flow": F, "trend": T, "both_leaving": bool(x.get("both")),
            "count": (f"{sum(1 for r in (P, H, F, T) if r['state'] == 'for')} for · "
                      f"{sum(1 for r in (P, H, F, T) if r['state'] == 'against')} against — a count, not odds"),
            "clock": ({"paid_last": last_paid, "quiet": min(quiet_n, QUIET), "readable": len(readable), "of": QUIET,
                       "text": f"paid last {last_paid or '—'} · quiet {min(quiet_n, QUIET)} of {QUIET}"}
                      if buyer else {"text": NOT_SHOWN + "a writer has no quiet clock (§4); time pays her"}),
            "watch": _hint(qA, rA, fAg, tAg, buyer, Q, R, ln) if word == "WATCH" else None,
            "prem": pr, "blind": blind,
        })
    return {"ok": True, "th": th, "entry": _entry(rows[0], et), "rows": rows,
            "fold": ({"t": latch["t"], "rule": latch["rule"], "why": latch["why"]} if latch else None)}


def _payers(x, oi_blind, qA, rs, i, Q):
    q = x.get("q")
    if oi_blind or not q:
        return {"state": "blind", "fact": CC + (_strip(oi_blind) or f"no {Q} front read"), "k": None, "tag": "M"}
    k = q["k"]
    if x["both"]:
        return {"state": "flat", "k": k, "tag": "M",
                "fact": f"both sides' writers leaving — OI cannot say which way ({_fw(q)})"}
    if x["q_pays"]:
        return {"state": "for", "k": k, "tag": "M", "fact": f"{_fw(q)} — the writers your move forces are leaving"}
    if x["q_fold"]:
        f = x["q_fold"]
        return {"state": "for", "k": k, "fold_t": f["t"], "tag": "M",
                "fact": f"{Q} {_k(f['k'])} folded {f['t']}, {f['off']:.0%} off its {f['high_at']} high"}
    if qA:
        return {"state": "against", "k": k, "tag": "M", "fact": f"{_fw(q)} — writers adding in its way (held {PERSIST} min)"}
    if x["q_build"]:
        return {"state": "flat", "k": k, "tag": "M",
                "fact": f"{_fw(q)} — adding, {_run(rs, i, 'q_build')} of {PERSIST} min before it counts"}
    return {"state": "flat", "k": k, "tag": "M", "fact": _fw(q)}


def _holders(x, oi_blind, rA, rF, squeeze, dpx, buyer, R, floor, rs, i):
    r = x.get("r")
    out = {"label": "HOLDERS" if buyer else "YOUR SIDE", "tag": "M", "fold": None, "fold_for": False}
    own = None
    if not buyer:
        own = (CC + "no ladder window yet" if dpx is None else
               f"spot moving toward your strike (index {dpx:+,.1f} over the ladder's 15 min) — a squeeze" if squeeze else
               f"winners cashing in — spot moving away (index {dpx:+,.1f} over the ladder's 15 min)")
    if rF:
        out["fold"] = f"{R} {_k(rF['k'])} folded {rF['t']} — the {floor} stepped" + (f" · {own}" if own else "")
        out["fold_t"], out["fold_for"] = rF["t"], squeeze is False and not buyer
    if oi_blind or not r:
        return {**out, "state": "blind", "fact": CC + (_strip(oi_blind) or f"no {R} front read"), "k": None}
    out["k"] = r["k"]
    left = f", {_run(rs, i, 'r_unw')} of {PERSIST} min before it counts"
    if x["both"]:
        return {**out, "state": "flat", "fact": f"both sides' writers leaving — OI cannot say which way ({_fw(r)})"}
    if x["r_hold"]:
        return {**out, "state": "for", "fact": f"{_fw(r)} — holding"}
    if not x["r_unw"]:
        return {**out, "state": "flat", "fact": _fw(r)}
    if buyer:
        return {**out, "state": "against" if rA else "flat",
                "fact": f"{_fw(r)} — the side holding your trade is leaving" + ("" if rA else left)}
    if dpx is None:
        return {**out, "state": "blind", "fact": f"{_fw(r)} — {own}"}
    if squeeze:
        return {**out, "state": "against" if rA else "flat", "fact": f"{_fw(r)} — your side leaving, {own}" + ("" if rA else left)}
    return {**out, "state": "for", "fact": f"{_fw(r)} — {own}; your strike is farther from spot than at entry"}


def _prem(prem, i, p0, qty, sg):
    if not prem:
        return {"why": CC + "no premium record for this contract"}
    c = (prem.get("c") or [])[i] if i < len(prem.get("c") or []) else None
    if c is None:
        return {"why": CC + "no print for this contract in this minute", "tag": prem.get("src", "I")}
    o = (prem.get("o") or [])[i] if i < len(prem.get("o") or []) else None
    out = {"c": c, "tag": prem.get("src", "I")}
    if p0:
        out.update(pnl=round((c - p0) * qty * sg, 2), pct=round((c / p0 - 1) * 100, 1),
                   adverse=sg * (c - p0) < 0 or (o is not None and sg * (c - o) < 0))
    return out


def _hint(qA, rA, fAg, tAg, buyer, Q, R, ln):
    """What would turn this WATCH into FOLD (§3.7), from the rules themselves."""
    fams = [(f"{Q} writers adding in its way for {PERSIST} min", qA),
            ("flow against you (CVD strong and prints dominant)", fAg),
            ("the trend rows against you (2 of 5m / 15m / 1h)", tAg)]
    missing = [n for n, v in fams if not v]
    bits = []
    if qA and not rA:
        bits.append(f"the {R} writers leave for {PERSIST} min")
    bits.append(("one more of: " if any(v for _, v in fams) else "two of: ") + "; ".join(missing))
    if ln and not ln.get("blind") and ln.get("L") is not None:
        bits.append(f"a 1-min index close beyond {ln['L']:,.1f}")
    if buyer:
        bits.append(f"nothing pays for {QUIET} readable min")
    return "FOLD if " + ", or ".join(bits)


def _entry(head, et):
    """§3's entry check, from the reading at the entry minute with the latch removed."""
    u, why = head["unlatched"], head["sentence"].split(" — ", 1)[-1]
    if u == "FOLD":
        txt = f"You entered into a broken setup — the reason was already gone at {et}, because {why}."
    elif u == "WATCH":
        txt = f"You entered into WATCH — {why}; it becomes {head['watch']}."
    elif u == "HOLD":
        ln = head["line"]
        paying = "nothing paying yet" if head["tag"] == "nothing paying" else why.split(": ", 1)[-1]
        txt = f"You entered into HOLD — line {ln['L']:,.1f}, {ln['room']:,} pts of room; {paying}."
    else:
        txt = f"You entered into PATA NAHI — {why}."
    start = mm("09:15") + (mm(et) - mm("09:15")) // 5 * 5
    return {"t": et, "verdict": u, "text": txt, "head_until": hm(max(start + 5, mm(et) + ENTRY_SHOWN)),
            "fold_rule": head["fold_rule"] if u == "FOLD" else None}


# ---------------------------------------------------------------- THE SIDE READ (§10)
def oi_half(rec):
    """board.oi_read on the two nearer fronts: printed, never counted (N4)."""
    if rec.get("blind") or not rec.get("CE") or not rec.get("PE"):
        return ["NOT READ", CC + (_strip(rec.get("blind")) or "fronts not read")]
    return list(board.oi_read([_front(rec, "CE"), _front(rec, "PE")], rec.get("spot") or rec["CE"]["k"]))


def side_facts(rec, s):
    """§10.2: payers, holders and aggression for / against the named side, counted."""
    if s not in ("CALLS", "PUTS"):
        return []
    d = 1 if s == "CALLS" else -1
    P, Hs = ("CE", "PE") if d > 0 else ("PE", "CE")
    out = []
    if rec.get("blind") or not rec.get(P) or not rec.get(Hs):
        why = CC + (_strip(rec.get("blind")) or "fronts not read")
        out += [{"k": "payers", "state": "blind", "fact": why, "tag": "M"},
                {"k": "holders", "state": "blind", "fact": why, "tag": "M"}]
    else:
        p, h, pf = _front(rec, P), _front(rec, Hs), _last_fold(rec, P, rec["t"])
        out.append({"k": "payers", "tag": "M", **(
            {"state": "for", "fact": _fw(p) + (f" · {P} {_k(pf['k'])} folded {pf['t']}" if pf else "")}
            if p["state"] == UNW or pf else
            {"state": "against", "fact": f"{_fw(p)} — writers adding in its way"} if p["state"] == BLD else
            {"state": "flat", "fact": _fw(p)})})
        out.append({"k": "holders", "tag": "M", **(
            {"state": "for", "fact": _fw(h)} if h["state"] == BLD else
            {"state": "against", "fact": f"{_fw(h)} — the {'floor' if Hs == 'PE' else 'ceiling'} is leaving"}
            if h["state"] == UNW else {"state": "flat", "fact": _fw(h)})})
    st, fact, why = flow(rec, d)
    out.append({"k": "aggression", "tag": "I", "state": {"with": "for"}.get(st, st),
                "fact": fact if st in ("with", "against") else (why or fact)})
    return out


def sides(minutes, upto=None):
    """§10 at every minute 09:15..upto (an index): [{t, side, why, since, stamp}] --
    `stamp` on the first minute a side is named after no side or the other side."""
    out, last, since, named = [], None, None, None
    for m in minutes[:None if upto is None else upto + 1]:
        s, why = side_of(m)
        key = s or "could not check"
        if key != last:
            since, last = m["t"], key
        stamp = s in ("CALLS", "PUTS") and s != named
        if s in ("CALLS", "PUTS") or s == "no side":
            named = s
        out.append({"t": m["t"], "side": key, "why": why, "since": since, "stamp": stamp})
    return out


def side_line(rec, sd, expiry):
    """The side read at one minute, printed: word, since, the counted facts, the OI half, expiry."""
    facts = side_facts(rec, sd["side"])
    n = {s: sum(1 for f in facts if f["state"] == s) for s in ("for", "against", "blind")}
    oi = oi_half(rec)
    head = (f"{sd['side']} side since {sd['since']} · {n['for']} for · {n['against']} against · "
            f"{n['blind']} could not check · OI: {oi[0]}" if sd["side"] in ("CALLS", "PUTS") else
            f"no side since {sd['since']} — {sd['why']}" if sd["side"] == "no side" else sd["why"])
    return {"side": sd["side"], "since": sd["since"], "stamp": sd["stamp"], "text": head, "rows": sd["why"],
            "facts": facts, "oi_half": oi, "expiry": expiry, "note": "a count, never odds", "tag": "I"}


def agrees(side, role, s):
    """§10.4: your side vs the read."""
    if s not in ("CALLS", "PUTS"):
        return "no side — the rows do not agree" if s == "no side" else "could not check"
    return "agrees" if (s == ("CALLS" if side == "CE" else "PUTS")) == (role == "long") else "against"


def expiry_line(idx, day, expiry, src):
    """§10.3, from the day's own record only (never the live instrument dump)."""
    if not expiry:
        return {"text": CC + "expiry not in the day's record", "tag": "M"}
    if expiry == day:
        return {"text": (f"0DTE today for {idx}: the ATM strike's theta is at its fastest and its gamma at its "
                         "largest — a side is not a hold; the window's clock and line decide when to leave."),
                "zero_dte": True, "src": src, "tag": "M"}
    from datetime import date
    n = (date.fromisoformat(expiry) - date.fromisoformat(day)).days
    return {"text": f"expiry {expiry}, {n} days", "zero_dte": False, "src": src, "tag": "M"}
