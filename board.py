"""board.py -- BOARD rev 3's read of one index at one finished minute.

THE SPEC is `docs/mockups/board-chess-rev3-2026-09-24-notes.md` §6 (the exact
definitions) and §8 steps 2-6. The mockup's generator (g3.py, in that session's
scratchpad) is the reference implementation; this is its port, rule for rule,
with the words kept. Its rules were fixed before either reference day
(2026-09-23 range, 2026-09-24 trend) was read through them.

WHAT IT ANSWERS, in the order the eye reads the board:
  * the headline -- who is pressing (rev 2's P2 floor), the latest fold still
    folded near spot, and the next wall on that side (0j.2);
  * the fronts with what was carried in vs built today, the nearer of each
    side's two, and the §1d gate's defender described honestly (0j.4);
  * the day's folds and FIRST FOLD;
  * agreement over five evidence families -- a COUNT, never a probability;
  * PCR, as text; the trend box's STRONG / REGIME (`trendbox.py`);
  * the mirror read of the option premium (`mirror`).

EVERYTHING HERE IS DISPLAY [I] on top of [M] facts. Nothing feeds
`fronts.fade_gate`, `setup.gate`, the zone machine or trigger_log; §1d is
called, never changed. LEVEL UNDER ATTACK and the FLUSH candle are not here
on purpose: both wait for her pre-registration (notes §7).

Pure: stdlib plus the repo's pure `fronts` / `grounds` / `trendbox`, no I/O,
no clock. The caller hands in a grid already cut to a FINISHED minute, so the
same inputs give the same board whenever it is read.
"""
from __future__ import annotations

import fronts
import grounds
import trendbox

TAPE_MIN = 15                     # grounds' own window (3 closed 5-min bars)
TAPE_KINDS = ("initiative", "absorption", "exhaustion")
FAMILIES = 5                      # OI, CVD, FLOW, TAPE, TREND

# The three absences (house rule 6), never one rendering.
CC = "could not check — "
NONE = "checked, none — "
NOT_SHOWN = "not shown — "


def mm(hhmm):
    h, m = str(hhmm)[:5].split(":")
    return int(h) * 60 + int(m)


def hm(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def sgn(x):
    return (x > 0) - (x < 0)


def L(x):
    """OI in lakh, signed, one decimal -- the house unit (+23.4L)."""
    return f"{x / 1e5:+.1f}L"


def Lx(x):
    return f"{abs(x) / 1e5:.1f}L"


def dom(a, b):
    """grounds' flow rule: at least 2, and twice the other side."""
    return a >= 2 and a >= 2 * b


def itm(k, side, s):
    """("ITM"|"OTM", points) of a strike-side against spot."""
    d = (s - k) if side == "CE" else (k - s)
    return ("ITM", round(d)) if d > 0 else ("OTM", round(-d))


def nearer(fr, side, s):
    """The nearer to spot of `side`'s fronts (a tie to the larger OI)."""
    rows = [f for f in fr if f["side"] == side]
    return min(rows, key=lambda x: (abs(x["k"] - s), -(x.get("oi") or 0))) if rows else None


# ---------------------------------------------------------------- the wording floors (rev 2)
def paying(f):
    """The front's state in §1d's words, never 'building' for a front >= 15 %
    under its own high (Fable P1). -> (yes|no|not yet, text)."""
    off = f["peak"] - f["chg"]
    frac = off / max(abs(f["peak"]), 1)
    if f["state"] == fronts.BUILDING:
        # BUILDING is the 15-mark slope, not the last few marks: once the front is off its high it says so.
        # "adding again" / "still adding" were printed while 22,900 PE fell every minute from its 09:33
        # peak (2026-09-28 trader audit, bug 5).
        if off >= fronts.STALL_FRAC * max(abs(f["peak"]), 1):
            return "no", f"up on the 15-min slope ({L(f['chg'])}) but {Lx(off)} under its {f['peak_at']} peak"
        return "no", f"still adding ({L(f['chg'])})"
    if f["state"] == fronts.STALLED:
        return "not yet", f"stopped building at {f['peak_at']}" + (f", {frac:.0%} off" if frac >= 0.005 else "")
    ua = f.get("unwind_at")
    return "yes", (f"unwinding since {ua}" if ua else "gave up its build") + f", {frac:.0%} off its {f['peak_at']} high"


def aggression(facts):
    """(dir, word, fact, why_none). An aggression word needs BOTH grounds' CVD
    strength AND its flow rule the same way (Fable P2)."""
    facts = facts or {}
    c, fl = facts.get("cvd"), facts.get("flow")
    if not c:
        return 0, None, None, CC + (facts.get("cvd_why") or "no ladder bars")
    if c.get("rank") is None:           # too few earlier changes to size it: could not check, never "small"
        return 0, None, None, CC + (c.get("rank_why") or f"sizing the CVD change needs {grounds.MIN_PRIOR} "
                                                            "earlier 15-min changes today")
    d = sgn(c["d"])
    fact = f"CVD {c['d']:+,.0f} since {c['since']} (rank {c['rank']:.2f})"
    if not fl:
        return 0, None, fact, "prints could not be read"
    nb, ns = fl["buy"], fl["sell"]
    pf = f"{ns} sell / {nb} buy prints of size"
    if fl.get("runs_why") and not (nb or ns):
        return 0, None, fact + " · " + pf, "too thin to read (fill runs could not rank)"
    if not (nb or ns):
        return 0, None, fact + " · " + pf, "no prints of size"
    mine, other = (nb, ns) if d > 0 else (ns, nb)
    if c["rank"] >= grounds.STRONG and d and dom(mine, other):
        return d, ("pressing" if c["rank"] >= grounds.ONE_SIDED else "leaning"), fact + " · " + pf, None
    if c["rank"] < grounds.STRONG or not d:
        return 0, None, fact + " · " + pf, f"CVD {c['d']:+,.0f}, small for today (rank {c['rank']:.2f})"
    return 0, None, fact + " · " + pf, f"CVD leans {'buyers' if d > 0 else 'sellers'}, prints {ns} sell / {nb} buy"


def state_words(f):
    off = (f["peak"] - f["chg"]) / max(abs(f["peak"]), 1)
    if f["peak"] <= 0:
        return "never built today (" + ("flat" if abs(f["chg"]) < 5000 else L(f["chg"])) + " from the open)"
    if f["state"] == fronts.BUILDING:
        return paying(f)[1]
    if f["state"] == fronts.STALLED:
        return f"stopped building at {f['peak_at']}"
    return f"giving back since {f.get('unwind_at') or f['peak_at']} ({off:.0%} off)"


# ---------------------------------------------------------------- fronts: carried in vs built today
def _fronts(fr, s, opens, times, spots, S, RP):
    """§1d's rows plus [M] extras: the open (carried in), the share of the high
    built today and its label, now = open + change, the nearer of the side's
    two, the spot at the high and the first §1d UNWINDING read after it."""
    jx = {t: j for j, t in enumerate(times)}
    out = []
    for f in fr:
        k, side = f["k"], f["side"]
        opn = (opens or {}).get((k, side.lower()))
        hi_abs = (opn + f["peak"]) if opn is not None else None
        share = (f["peak"] / hi_abs) if (hi_abs and f["peak"] > 0) else 0.0
        pj = jx.get(f["peak_at"])
        v = S.get((k, side)) or []
        ua = None
        if pj is not None:
            for j in range(max(pj + 1, fronts.SLOPE_MARKS), len(v)):
                if fronts._state(v[j], RP[(k, side)][j], v[j] - v[j - fronts.SLOPE_MARKS]) == fronts.UNWINDING:
                    ua = times[j]
                    break
        m, dd = itm(k, side, s)
        out.append({**f, "open": opn, "now_oi": (opn + f["chg"]) if opn is not None else None,
                    "share": round(share, 3) if opn is not None else None,
                    "built": ("never" if f["peak"] <= 0 else None if opn is None else
                              "today" if share >= 0.5 else "carried"),
                    "dist": round(abs(k - s)), "itm": [m, dd],
                    "peak_spot": spots[pj] if pj is not None else None, "unwind_at": ua})
    for f in out:
        f["nearer"] = nearer(out, f["side"], s) is f
        f["rank"] = next(n for n, x in enumerate((x for x in out if x["side"] == f["side"]), 1) if x is f)
        f["words"] = state_words(f)
        f["built_label"] = {"never": "NEVER BUILT", "today": f"TODAY {f['share']:.0%}" if f["share"] is not None else None,
                            "carried": f"CARRIED {1 - f['share']:.0%}" if f["share"] is not None else None,
                            None: None}[f["built"]]
    return out


def gate_flag(fr, side, s):
    """The §1d gate's defender -- the #1 by session-peak OI, unchanged -- said
    honestly (0j.4): never built today, or the farther of the side's two."""
    rows = [f for f in fr if f["side"] == side]
    if not rows:
        return None
    d, near_f = rows[0], nearer(fr, side, s)
    bits = []
    if d["peak"] <= 0:
        bits.append("never built today")
    if near_f is not d:
        bits.append(f"the farther wall, {abs(d['k'] - s):,.0f} pts; the nearer is {near_f['side']} "
                    f"{near_f['k']:,.0f} (#2, {near_f['state'].lower()})")
    return {"k": d["k"], "side": side, "flags": bits, "tag": "I",
            "fades": "d2 BUY" if side == "PE" else "u2 SELL"}


# ---------------------------------------------------------------- folds and FIRST
def still_folded(e, j, S, RP, jx):
    """No new high since the fold, and §1d not reading it BUILDING at mark j."""
    key, ej = (e["k"], e["side"]), jx[e["t"]]
    if j < ej or RP[key][j] != e["high"]:
        return False
    v = S[key]
    return fronts._state(v[j], e["high"], v[j] - v[max(0, j - fronts.SLOPE_MARKS)]) != fronts.BUILDING


def first_fold(minutes, evs, opens=None, peak=None, g=None):
    """The day's FIRST FOLD: the first fold of a §1d top-2 front AT ITS OWN
    MARK (notes §6.1). [M]

    Top 2 is ranked the way §1d ranks it, by session-high absolute OI, as it
    stood at that mark: the open plus the running high change on the grid's
    minute marks (an intra-minute spike the grid never held is not seen). A
    strike with no known open falls back to the live session high. None when
    no top-2 front has folded yet.
    """
    times, spots, ks, S, RP = g or fronts.grid(minutes)
    jx = {t: j for j, t in enumerate(times)}
    for e in evs:
        j = jx.get(e["t"])
        if j is None:
            continue
        pk = {}
        for (k, side), rp in RP.items():
            o = (opens or {}).get((k, side.lower()))
            v = (o + rp[j]) if o is not None else (peak or {}).get((k, side.lower()))
            if v is not None:
                pk[(k, side.lower())] = v
        rows = fronts.read(fronts.cut(minutes, e["t"]), pk)
        if any(f["k"] == e["k"] and f["side"] == e["side"] for f in rows):
            return {k: e[k] for k in ("k", "side", "t", "high", "high_at", "spot_high", "tag")}
    return None


def coverage(times):
    """Is the grid whole from the open? A hole is a gap between marks wider
    than §1d's own staleness bound (a restart's backfill still landing, or a
    dead feed). FIRST is stamped only off a whole grid."""
    holes = [f"{a}–{b}" for a, b in zip(times, times[1:]) if mm(b) - mm(a) > fronts.STALE_MIN]
    late = bool(times) and mm(times[0]) - mm("09:15") > fronts.STALE_MIN
    return {"from": times[0] if times else None, "to": times[-1] if times else None,
            "marks": len(times), "holes": holes, "late": late,
            "whole": bool(times) and not holes and not late, "tag": "M"}


# ---------------------------------------------------------------- the headline (0j.2)
def headline(j, fr, facts, s, step, evs, S, RP, near, jx):
    if j < fronts.SLOPE_MARKS:
        return {"text": f"Fronts forming — the build → stall → unwind sequence needs {fronts.SLOPE_MARKS} "
                        f"one-minute marks, {j + 1} so far", "fold": None, "next": None, "tag": "M"}
    d, word, _fact, why = aggression(facts)
    lead = (f"{'Buyers' if d > 0 else 'Sellers'} {word}" if d else
            "Nobody pressing — too thin to read" if (why or "").startswith("too thin") else
            "Pressure " + why if (why or "").startswith(CC) else "Nobody pressing")

    def near_spot(e):
        # [I, display]: within one strike of spot, or spot through the strike on
        # the writers' losing side (ITM). An OTM fold far from price is not headlined.
        return abs(e["k"] - s) <= step or itm(e["k"], e["side"], s)[0] == "ITM"
    live = [e for e in evs if jx[e["t"]] <= j and still_folded(e, j, S, RP, jx)
            and e["k"] in near[j] and near_spot(e)]
    if live:
        e = max(live, key=lambda e: (jx[e["t"]], e["high"]))
        m, dd = itm(e["k"], e["side"], s)
        off = (e["high"] - S[(e["k"], e["side"])][j]) / e["high"]
        fold_txt = f"{e['side']} {e['k']:,.0f} ({m} {dd}) folded {e['t']}, {off:.0%} off its {e['high_at']} high"
        # who defends next on that side: the nearest sized, unfolded build within a strike or beyond spot
        big = max([RP[(k, e["side"])][j] for k in near[j]] + [0.0])
        beyond = [k for k in near[j] if (k <= s + step if e["side"] == "PE" else k >= s - step) and k != e["k"]]
        nxt = None
        for k in sorted(beyond, key=lambda k: (abs(k - s), k)):
            kk = (k, e["side"])
            if RP[kk][j] > 0 and RP[kk][j] >= fronts.FOLD_SIZE * big and not any(
                    x["k"] == k and x["side"] == e["side"] and still_folded(x, j, S, RP, jx)
                    for x in evs if jx[x["t"]] <= j):
                v = S[kk]
                st = fronts._state(v[j], RP[kk][j], v[j] - v[max(0, j - fronts.SLOPE_MARKS)])
                nxt = {"k": k, "side": e["side"], "state": st,
                       "rel": "at spot" if abs(k - s) < step / 2 else f"{abs(k - s):,.0f} {'below' if k < s else 'above'}"}
                break
        who = "put" if e["side"] == "PE" else "call"
        if nxt:
            w2 = {fronts.BUILDING: "still adding", fronts.STALLED: "stopped adding", fronts.UNWINDING: "giving back"}[nxt["state"]]
            ntxt = f"next {who} wall {e['side']} {nxt['k']:,.0f} ({nxt['rel']}) {w2}"
        else:
            ntxt = f"no sized {who} build {'below' if e['side'] == 'PE' else 'above'} spot inside the nine"
        return {"text": f"{lead} · {fold_txt} · {ntxt}", "tag": "I",
                "fold": {"k": e["k"], "side": e["side"], "t": e["t"], "high_at": e["high_at"],
                         "off": round(off, 3), "itm": [m, dd], "tag": "M"},
                "next": nxt}
    # No fold near spot: the nearer of each side's top 2 -- and never one that
    # never built today (0j.2; the brief's "never a never-built front").
    if not fr:
        return {"text": f"{lead} · near-ATM fronts could not be read", "fold": None, "next": None, "tag": "I"}

    def pick(side):
        return nearer([f for f in fr if f["side"] == side and f["peak"] > 0], side, s)

    def who(f):
        m, dd = itm(f["k"], f["side"], s)
        return f"{f['side']} {f['k']:,.0f} ({m} {dd})"

    def clause(f, side):
        if f is None:
            return f"no {'call' if side == 'CE' else 'put'} front of the top 2 built today"
        return f"{who(f)} {state_words(f)}"
    ce, pe = pick("CE"), pick("PE")
    if d:
        pay, other, ps, os_ = (ce, pe, "CE", "PE") if d > 0 else (pe, ce, "PE", "CE")
        into = f"into {who(pay)}, which is {state_words(pay)}" if pay else "· " + clause(None, ps)
        return {"text": f"{lead} {into} · {clause(other, os_)} · no fold near spot yet",
                "fold": None, "next": None, "tag": "I"}
    return {"text": f"{lead} · {clause(ce, 'CE')} · {clause(pe, 'PE')} · no fold near spot yet",
            "fold": None, "next": None, "tag": "I"}


# ---------------------------------------------------------------- agreement: five families, counted
def tape_events(marks):
    """Footprint events (initiative / absorption / exhaustion, GoCharting + the
    TapeMap ladder), each visible at its 5-min bar's close. [I] side
    attribution. The same mark served twice (the extension replays the
    footprint) is kept once; two marks in one bar at nearby prices are two."""
    seen, out = set(), []
    for src in ("ofd", "tm"):
        for m in (marks or {}).get(src) or []:
            if not isinstance(m, dict) or m.get("kind") not in TAPE_KINDS or not m.get("side") or m.get("t") is None:
                continue
            e = {"vis": mm(grounds._hh(m["t"])) + 4, "kind": m["kind"], "side": m["side"],   # its bar closed by then (= _closed)
                 "src": "GoCharting" if src == "ofd" else "TapeMap ladder"}
            key = (m["t"], e["kind"], e["side"], m.get("p"), m.get("size"), src)
            if key not in seen:
                seen.add(key)
                out.append(e)
    return sorted(out, key=lambda e: e["vis"])


def oi_read(fr, s):
    """(word, why) for the trend box's REGIME: the nearer of each side's §1d top 2."""
    ce, pe = nearer(fr, "CE", s), nearer(fr, "PE", s)
    if not ce or not pe:
        return "NOT READ", "fronts not read"
    b_ce = ce["state"] == fronts.BUILDING and ce["peak"] > 0
    b_pe = pe["state"] == fronts.BUILDING and pe["peak"] > 0

    def w(f, b):
        return "writing" if b else ("never built" if f["peak"] <= 0 else
                                    {"STALLED": "stopped", "UNWINDING": "giving back"}.get(f["state"], "stopped"))
    tag = f"CE {ce['k']:,.0f} {w(ce, b_ce)} · PE {pe['k']:,.0f} {w(pe, b_pe)}"
    if b_ce and b_pe:
        return "PIN", "both sides writing: " + tag
    if b_ce:
        return "TREND DOWN", "put side stopped, call side writing: " + tag
    if b_pe:
        return "TREND UP", "call side stopped, put side writing: " + tag
    return "BOTH LEAVING", "neither side writing: " + tag


def agreement(fr, s, facts, events, have, asof, stg, idx):
    """Five evidence families, each ▲ (+1) ▼ (-1) · (0) or ? (None, could not
    check), counted. NEVER a probability: 'n of 5 agree' overstates their
    independence (FLOW counts stacks, TREND is price), and says so."""
    facts = facts or {}
    fam = []
    ce, pe = nearer(fr, "CE", s), nearer(fr, "PE", s)
    if not ce or not pe:
        fam.append(("OI", None, CC + "fronts not read", "M", None))
    else:
        b_ce = ce["state"] == fronts.BUILDING and ce["peak"] > 0
        b_pe = pe["state"] == fronts.BUILDING and pe["peak"] > 0
        v = -1 if (b_ce and not b_pe) else 1 if (b_pe and not b_ce) else 0
        fam.append(("OI", v, f"PE {pe['k']:,.0f} {state_words(pe)} · CE {ce['k']:,.0f} {state_words(ce)}", "M",
                    "the nearer of each side's top 2 by §1d" if v else
                    ("both sides writing" if b_ce and b_pe else "neither side writing")))
    cv = facts.get("cvd")
    if not cv or cv["rank"] is None:
        fam.append(("CVD", None, CC + aggression(facts)[3].replace(CC, ""), "I", None))
    else:
        v = sgn(cv["d"]) if cv["rank"] >= grounds.STRONG else 0
        fam.append(("CVD", v, f"{cv['d']:+,.0f} / 15 min · rank {cv['rank']:.2f} · price {cv['dpx']:+.1f}", "I",
                    "Upstox ladder, side inferred" if v else "small for today (rank under 0.50)"))
    fl = facts.get("flow")
    if not fl:
        fam.append(("FLOW", None, CC + (facts.get("flow_why") or "no prints"), "I", None))
    else:
        v = 1 if dom(fl["buy"], fl["sell"]) else -1 if dom(fl["sell"], fl["buy"]) else 0
        fam.append(("FLOW", v, f"{fl['sell']} sell / {fl['buy']} buy prints of size", "I",
                    "fill runs could not rank" if fl.get("runs_why") else "print side inferred"))
    if not (have.get("ofd") or have.get("tm")):
        fam.append(("TAPE", None, CC + f"no footprint events for {idx}", "I", None))
    else:
        now = mm(asof)
        w = [e for e in events if now - TAPE_MIN < e["vis"] <= now]
        nb, ns = sum(1 for e in w if e["side"] > 0), sum(1 for e in w if e["side"] < 0)
        v = 1 if dom(nb, ns) else -1 if dom(ns, nb) else 0
        last = w[-1] if w else None
        fam.append(("TAPE", v, f"{ns} bearish / {nb} bullish footprint events" +
                    (f" · last {last['kind']} {hm(last['vis'] - 4)}" if last else ""), "I",
                    "GoCharting + TapeMap marks, 15 min" if w else "checked, none in 15 min"))
    if stg.get("word") is None:
        fam.append(("TREND", None, CC + (stg.get("why") or "trend box not read"), "I", None))
    else:
        v = 1 if stg["word"] == "BULLS" else -1 if stg["word"] == "BEARS" else 0
        u, dn, r, f = stg["n"]
        fam.append(("TREND", v, f"{stg['word'].lower()} · {dn} down / {u} up / {r} range" +
                    (f" / {f} forming" if f else ""), "I", "the trend box's 7 rows"))
    ups = sum(1 for x in fam if x[1] == 1)
    dns = sum(1 for x in fam if x[1] == -1)
    read_ = sum(1 for x in fam if x[1] is not None)
    dirn = 0 if ups == dns else (1 if ups > dns else -1)
    n, against = max(ups, dns), min(ups, dns)
    lead = "▲ UP" if dirn > 0 else "▼ DOWN" if dirn < 0 else "· NO SIDE"
    return {"head": {"dir": dirn, "n": n, "of": FAMILIES, "against": against, "read": read_,
                     "text": f"{lead} · {n} of {FAMILIES} agree · {against} against · {FAMILIES - read_} not read"
                             " · a count, not odds"},
            "fam": [{"k": a, "v": b, "fact": c, "tag": t, "doubt": e} for a, b, c, t, e in fam],
            "tag": "I", "note": "a count of families, never a probability or a confidence"}


def pcr(last_k, opens):
    """ΣPE / ΣCE absolute OI over the grid's strikes (open + change), text only. [M]"""
    ce = pe = 0.0
    n = 0
    for key, cell in (last_k or {}).items():
        k = fronts._num(key)
        oc, op = (opens or {}).get((k, "ce")), (opens or {}).get((k, "pe"))
        if k is None or oc is None or op is None:
            continue
        c, p = fronts._pair(cell)
        ce, pe, n = ce + oc + c, pe + op + p, n + 1
    if not n or ce <= 0:
        return {"v": None, "text": CC + "no chain snapshot to read the open from", "tag": "M"}
    v = round(pe / ce, 2)
    return {"v": v, "n": n, "tag": "M",
            "text": f"PCR {v:.2f} · ΣPE / ΣCE open interest over the {n} grid strikes · drifts, no timing"}


# ---------------------------------------------------------------- what can happen (rev 2's squares, rev 3's words)
SQ_MERGE = 4          # candidates within this many points are one square (the mockup's rule)
SQ_CLEAR = 3          # a square must sit more than this far from spot
SQ_ROUNDS = 3         # round strikes within this many steps of spot


def squares(fr, s, step, facts, levels, spots, times, hilo=None):
    """WHAT CAN HAPPEN: the next square up and down, who pays there, are they
    paying now, is anyone pressing, and what would refuse the move. Conditions
    only, never odds. [I] on [M] facts.

    The squares are the prior-session / week / open levels (`levels`,
    levels.static_levels rows), the §1d fronts' strikes, round strikes near
    spot and the day's high / low on the grid's minute marks, merged within
    SQ_MERGE points. WHO PAYS is the nearer §1d front on the side the move
    hurts (calls up, puts down) -- NOT the draft level-under-attack defender,
    which waits for her pre-registration (notes §7.1), so AT THE LEVEL is not
    here at all."""
    cand = [(l["px"], _short(l.get("label") or l["kind"])) for l in levels or [] if l.get("px") is not None]
    cand += [(f["k"], f"{f['side']} {f['k']:,.0f} wall") for f in fr or []]
    if step:
        cand += [(r * step, f"round {r * step:,.0f}")
                 for r in range(int((s - SQ_ROUNDS * step) // step), int((s + SQ_ROUNDS * step) // step) + 1)]
    if hilo and hilo.get("hi") is not None and hilo.get("lo") is not None:
        # decode-loop D6: the day's high / low from every chain row (read.day_hl), never the minute grid's marks --
        # a high printed between two marks was invisible to the grid
        cand += [(hilo["hi"], f"day high {hilo['hi_t']}"), (hilo["lo"], f"day low {hilo['lo_t']}")]
    elif spots:
        hj = max(range(len(spots)), key=lambda i: spots[i])
        lj = min(range(len(spots)), key=lambda i: spots[i])
        cand += [(spots[hj], f"day high {times[hj]}"), (spots[lj], f"day low {times[lj]}")]
    merged = []
    for px, lab in sorted(cand):
        if merged and abs(px - merged[-1]["px"]) <= SQ_MERGE:
            if lab not in merged[-1]["labels"]:
                merged[-1]["labels"].append(lab)
        else:
            merged.append({"px": px, "labels": [lab]})
    d, word, fact, why = aggression(facts)
    fl = (facts or {}).get("flow") or {}
    out = {"tag": "I", "note": "conditions, never odds",
           "levels_why": None if levels else CC + "no prior-session / week / open levels in hand, so the squares "
                                              "are the fronts, round strikes and the day's high / low only"}
    for name, dirn, side in (("up", 1, "CE"), ("dn", -1, "PE")):
        sq = ([m for m in merged if m["px"] > s + SQ_CLEAR][:2] if dirn > 0 else
              [m for m in reversed(merged) if m["px"] < s - SQ_CLEAR][:2])
        if not sq:
            out[name], out[name + "_why"] = None, NONE + f"no square {'above' if dirn > 0 else 'below'} spot on this board"
            continue
        row = {"sq": [{"px": round(m["px"], 1), "labels": m["labels"], "dist": round(m["px"] - s, 1)} for m in sq]}
        f = nearer(fr or [], side, s)
        who = "call" if dirn > 0 else "put"
        if f:
            m_, dd = itm(f["k"], side, s)
            bt = {"never": "never built today",
                  "today": f"built today ({f.get('share') or 0:.0%} of its high)",
                  "carried": f"carried in ({1 - (f.get('share') or 0):.0%} of its high was there at the open)",
                  None: "carried in vs built today could not be checked (no open)"}[f.get("built")]
            row["who"] = {"text": f"{who} writers at {side} {f['k']:,.0f} — {m_} {dd} · {bt}", "k": f["k"],
                          "side": side, "tag": "M"}
            yn, p = ("no", "never built today — nothing here to pay") if f["peak"] <= 0 else paying(f)
            row["paying"] = {"yn": yn, "text": p, "tag": "M"}
            row["refused"] = f"{side} {f['k']:,.0f} adds again, or absorption prints at {f['k']:,.0f}"
        else:
            row["who"] = {"text": CC + "fronts not read", "k": None, "side": side, "tag": "M"}
            row["paying"] = {"yn": "could not check", "text": "fronts not read", "tag": "M"}
            row["refused"] = CC + "fronts not read"
        if d:
            txt = f"{'buyers' if d > 0 else 'sellers'} {word}: {fact.split(' since ')[0]}, " \
                  f"{fl.get('sell')} sell / {fl.get('buy')} buy"
            row["press"] = {"yn": "yes" if d == dirn else "no", "text": txt if d == dirn else "the other side — " + txt}
        else:
            blind = (why or "").startswith((CC, "too thin")) or "could not" in (why or "")
            row["press"] = {"yn": "could not check" if blind else "no",
                            "text": (why or "nobody pressing").replace(CC, "")}
        row["press"]["tag"] = "I"
        out[name] = row
    return out


def _short(label):
    """'PDH 23,466.9 (2026-09-23)' -> 'PDH 23,466.9': the square names the level, not its date."""
    i = label.find(" (")
    return label[:i] if i > 0 else label


# ---------------------------------------------------------------- the whole read
def read(minutes, peak=None, opens=None, facts=None, marks=None, trend=None, first=None,
         idx=None, g=None, evs=None, trend_why=None, levels=None, hilo=None):
    """The board at the grid's last mark (a FINISHED minute).

    minutes  the chain grid cut to that minute (`fronts.cut`)
    peak     ChainState.peak -- §1d's ranking, exactly what /api/oihist uses
    opens    {(strike, "ce"|"pe"): OI at the open}, i.e. oi - oi_chg
    facts    `grounds.facts` at this minute, or None
    marks    {"ofd": [...], "tm": [...]} footprint marks, or None (no record)
    trend    `trendbox.rows(...)`, or None with `trend_why`
    first    the day's FIRST FOLD as stamped (once a day, by the caller, off
             `first_fold` on a whole grid -- day_state keeps it), or None
    g, evs   `fronts.grid` / `fronts.folds` of `minutes`, when already in hand
    levels   levels.static_levels rows (PDH/PDL/PDC/PWH/PWL/OPEN) for the squares, or None
    hilo     read.day_hl(...)["spot"] -- the day's high / low off every chain row -- or None (the grid's marks then)
    """
    g = g or fronts.grid(minutes)
    times, spots, ks, S, RP = g
    if not times:
        return {"ok": False, "why": CC + "no minute with a spot and a strike grid yet", "tag": "M"}
    evs = fronts.folds(minutes, g) if evs is None else evs
    jx = {t: j for j, t in enumerate(times)}
    j, s, asof = len(times) - 1, spots[-1], times[-1]
    step = min((b - a for a, b in zip(ks, ks[1:]) if b > a), default=None)
    near = [set(fronts.nine(ks, x)) for x in spots]
    fr = _fronts(fronts.read(minutes, peak), s, opens, times, spots, S, RP)
    cov = coverage(times)
    stg = trendbox.strong(trend)
    if trend is None:
        stg["why"] = trend_why or "trend box not read"
    rg = trendbox.regime(trend, oi_read(fr, s)) if trend else {
        "word": None, "why": CC + (trend_why or "no index candle yet")}
    have = {"ofd": bool((marks or {}).get("ofd")), "tm": bool((marks or {}).get("tm"))}
    hd = headline(j, fr, facts, s, step, evs, S, RP, near, jx) if step else {
        "text": CC + "one strike on the grid, no step", "fold": None, "next": None, "tag": "I"}
    last_k = (minutes.get(asof) or {}).get("k")
    return {
        "ok": True, "asof": asof, "spot": s, "step": step, "tag": "I",
        "headline": hd,
        "fronts": fr or None,
        "fronts_why": None if fr else CC + "no minute carries a spot and a strike grid yet",
        "defender": {"buy": gate_flag(fr, "PE", s), "sell": gate_flag(fr, "CE", s),
                     "note": "§1d's defender is unchanged (the #1 by session-peak OI); this only describes it"},
        "folds": evs,
        "folds_why": None if evs else NONE + "no sized front inside the nine has folded yet today",
        "first": first,
        "first_why": (None if first else
                      NONE + "no §1d top-2 front has folded yet today" if cov["whole"] else
                      CC + "not stamped: the grid is not whole from the open"
                      + (f" (holes {', '.join(cov['holes'])})" if cov["holes"] else f" (it starts {cov['from']})")
                      + " -- a restart's backfill may still be landing"),
        "agreement": agreement(fr, s, facts, tape_events(marks), have, asof, stg, idx),
        "trend": {**({"px": trend["px"], "rows": trend["rows"], "at": trend.get("at")} if trend else
                     {"px": None, "rows": None, "why": CC + (trend_why or "no index candle yet")}),
                  "strong": stg, "regime": rg, "tag": "I", "src": "the index's own Upstox candles"},
        "pcr": pcr(last_k, opens),
        "squares": squares(fr, s, step, facts, levels, spots, times, hilo),
        "grid": cov,
    }


# ---------------------------------------------------------------- the mirror read (notes §6.7)
def band(z):
    return ("above +3σ" if z >= 3 else "+2σ…+3σ" if z >= 2 else "+1σ…+2σ" if z >= 1 else
            "VWAP…+1σ" if z >= 0 else "−1σ…VWAP" if z > -1 else "−2σ…−1σ" if z > -2 else
            "−3σ…−2σ" if z > -3 else "below −3σ")


def _closed(bars, asof):
    """The last 5-min bar CLOSED by `asof` (a finished minute), or -1."""
    i = -1
    for q, b in enumerate(bars):
        if b and mm(b["t"]) + 4 <= mm(asof):
            i = q
    return i


PIVOT_KEYS = ("P", "R1", "R2", "R3", "S1", "S2", "S3")


def mirror_leg(leg, asof):
    """One /api/contract leg (5-min, axis-aligned): z of the last closed close
    against its own session VWAP, the band it sits in, and the nearest
    prior-session floor pivot above and at-or-below it. [M]"""
    if not leg or not any(leg.get("bars") or []):
        return {"strike": (leg or {}).get("strike"), "why": CC + "no candles for this contract today", "tag": "M"}
    bars, vw = leg["bars"], leg.get("vwap") or []
    i = _closed(bars, asof)
    if i < 0:
        return {"strike": leg.get("strike"), "why": NONE + "the first 5-min bar has not closed yet", "tag": "M"}
    b, v = bars[i], (vw[i] if i < len(vw) else None) or {}
    c, vwap, u1 = b["c"], v.get("vwap"), v.get("u1")
    sg = (u1 - vwap) if (u1 is not None and vwap is not None) else None
    out = {"strike": leg.get("strike"), "t": b["t"], "c": c, "vwap": vwap, "sigma": sg, "tag": "M"}
    if sg:
        z = (c - vwap) / sg
        out.update(z=round(z, 2), band=band(z))
    else:
        out.update(z=None, band=None, why=CC + "the band has no width yet (σ = 0)")
    piv = leg.get("pivots")
    if not piv:
        out["pivots"], out["pivots_why"] = None, leg.get("pivots_why") or CC + "no prior-session pivots"
    else:
        lv = [(k, piv[k]) for k in PIVOT_KEYS if piv.get(k) is not None]
        up = min((x for x in lv if x[1] > c), key=lambda x: x[1], default=None)
        dn = max((x for x in lv if x[1] <= c), key=lambda x: x[1], default=None)
        out["pivots"] = {
            "above": {"name": up[0], "px": round(up[1], 2), "dist": round(up[1] - c, 2)} if up else None,
            "above_why": None if up else NONE + "above R3",
            "below": {"name": dn[0], "px": round(dn[1], 2), "dist": round(c - dn[1], 2)} if dn else None,
            "below_why": None if dn else NONE + "under S3",
            "day": leg.get("pivots_day")}
    return out


def vs_futures(ce, pe, fut, asof):
    """VS FUTURES [I], her reading, DRAFTED, not registered: at the future's
    latest new session low (high), did the PE print a new session high and the
    CE a new session low in the same 5-min bar (mirrored)? Both CONFIRMS, both
    no DIVERGES, one of each SPLIT."""
    fb = [b for b in (fut or []) if b]
    fi = _closed(fb, asof)
    if fi < 1:
        return {"word": None, "why": NONE + "no new futures extreme since the first bar", "tag": "I", "draft": True}
    e, kind = -1, None
    for q in range(1, fi + 1):
        hi, lo = max(b["h"] for b in fb[:q]), min(b["l"] for b in fb[:q])
        if fb[q]["l"] < lo:
            e, kind = q, "low"
        elif fb[q]["h"] > hi:
            e, kind = q, "high"
    if e < 1:
        return {"word": None, "why": NONE + "no new futures extreme since the first bar", "tag": "I", "draft": True}
    t = fb[e]["t"]

    def new(leg, hi):
        lb = [b for b in (leg or {}).get("bars") or [] if b]
        q = next((i for i, b in enumerate(lb) if b["t"] == t), None)
        if q is None or q < 1:
            return None
        return (lb[q]["h"] > max(b["h"] for b in lb[:q])) if hi else (lb[q]["l"] < min(b["l"] for b in lb[:q]))
    if kind == "low":
        a, b = new(pe, True), new(ce, False)
        ta = {True: "PE new high ✓", False: "PE no new high ✗ put buyers not paying up", None: "PE: no bar at " + t}[a]
        tb = {True: "CE new low ✓", False: "CE above its low ✗", None: "CE: no bar at " + t}[b]
    else:
        a, b = new(ce, True), new(pe, False)
        ta = {True: "CE new high ✓", False: "CE no new high ✗ call buyers not paying up", None: "CE: no bar at " + t}[a]
        tb = {True: "PE new low ✓", False: "PE above its low ✗", None: "PE: no bar at " + t}[b]
    if a is None or b is None:
        word = None
    else:
        word = "CONFIRMS" if a and b else "DIVERGES" if not (a or b) else "SPLIT"
    return {"word": word, "fut": {"kind": kind, "t": t}, "legs": [ta, tb], "tag": "I", "draft": True,
            "why": None if word else CC + f"a leg has no 5-min bar labelled {t}",
            "text": f"fut new {kind} {t} bar → {word or 'could not check'} · {ta} · {tb}"}


def mirror(legs, fut, asof, expiry=None):
    """The mirror read: the chosen CE and PE premium against its own session
    VWAP ±σ exactly as /api/contract serves it, their nearest prior-session
    pivots, and the draft VS FUTURES read."""
    ce, pe = (legs or {}).get("CE"), (legs or {}).get("PE")
    return {"ok": True, "expiry": expiry, "asof": asof, "tag": "M",
            "legs": {"CE": mirror_leg(ce, asof), "PE": mirror_leg(pe, asof)},
            "vs_futures": vs_futures(ce, pe, fut, asof)}
