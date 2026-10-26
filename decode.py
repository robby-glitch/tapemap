"""decode.py -- THE DECODE block: the TRAJECTORY of every input, then ONE combined call, per index at a 5-min close.

Mary, 22 Oct: "i want the app to do it for us. is in it why we are making this tool". What Claude did by hand on 21 Oct
(memory: read-changes-not-levels) -- delta per bar against the leg, CVD off its peak, the writers' lead now vs its peak,
FUEL, the zone / confluence / FADE-D state, the cross-index sync -- put together into one call. tools/decode_now.py
prints the same facts from the same functions (one source of truth).

PURE AND CAUSAL: no I/O, no clock. Every reading uses bars closed and chain rows recorded by the 5-min close it names
(`facts` cuts its bars at `now` whatever the caller passed; faded.leads reads the last chain row BEFORE each close).
The registered setups are CALLED, never re-implemented: faded.py (FADE-D 2a / 2b / 3), confluence.py (FADE: zone + OI +
flow), ride.py (RIDE: §E + OI + flow) -- test_decode's guard test fails if a threshold is copied here.

DISPLAY ONLY: gates nothing, writes nothing. The call is a COUNT of the signs present (n/7), never a %, a probability
or a hit rate. A missing input is "?" on its line and null on its check, never a zero and never a crash. [I]

THE CALL (display rule, fixed 2026-10-22). Decel signs for the current leg, each with its continuation mirror:
  effort   a new extreme at <= 25% of the leg's biggest same-side bar (FADE-D 2a)   | a new extreme on effort, 15 min
  delta    the last bar's delta against the leg                                      | with the leg
  cvd      CVD off its leg extreme (FADE-D 2b's leg CVD)                             | at its leg extreme
  lead     the winning side's lead >= 10 under its 5-min peak (FADE-D 3's reads)    | at its peak, or up 10 in 15 min
  vwap     the close back across VWAP                                                | on the leg's side
  push     the last push in the leg's direction failed                               | it held
  peers    a peer index on the opposite leg                                          | a peer on the same leg
  decel >= 4 and > continuation -> "leg thak raha · d/7"; continuation >= 4 and > decel -> "leg jaari · c/7";
  otherwise "mila-jula · d/c"; no leg -> "saaf nahi". The call's `signs`: its own side's chips, then the other side's,
  each prefixed "jaari · " / "thak · " (both prefixed on mila-jula).

THE DECODE LEG (gap A1, 2026-10-22): the call and the lines read the zigzag's open leg (swing_of: 5-min closes, the
panel research's max(50 pts NIFTY-equivalent, 0.5 x IV-priced 30-min sigma) reversal), so a turn in the middle of the
range is a leg; before the first reversal, the session-extreme leg (leg_of). FADE-D's status keeps §1n's own leg:
g["leg"] / g["fd"] are untouched, g["dleg"] / g["dfd"] are the call's. The lead's 15-min change is read on ONE strike
set (onesided.lead15, gap A24) and the block carries THE ONE-SIDED METER (onesided.py, §1o) as `onesided`.

THE EFFORT LINE (gap A44, 2026-10-23): effort per point (Kyle lambda) at the latest fresh extreme, Fable's surviving
read (effort.py, his definition ported), as the sixth LINE and `effort` -- never a sign: the 7-sign call is unchanged.
SENSEX (A25, display only): its futures-based lines carry "patla (med N lot/5m)", its FADE-D chip a `thin` field.
"""
from __future__ import annotations

import math

import confluence
import effort
import faded
import hold2
import onesided
import rank
import read
import ride

REV = ("decode-3 (2026-10-23: A44 EFFORT line + effort, A25 SENSEX patla stamps, A36 FUEL ref din, stops spot|fut; "
       "decode-2: A1 swing leg, A24 one strike set, A10/A12 words, N2 HOLD v2 state, N8 one sign a slot)")
THIN = ("SENSEX",)                # A25: futures too thin for a fut-based read (22 Oct: median 2 lots a minute)
NLINES = 6
OF = 7
ZZ_PCT, ZZ_SIG, ZZ_NEAR = 50 / 22700, 0.5, 15   # A1: 50 pts at NIFTY 22,700 (scaled by price) | 0.5 sigma30 | 15 min
FUEL_FROM = rank.OPEN_S + (rank.WIN + 1) * rank.MARK   # A12: READ-2's 40-min OI window first closes (10:00)
OPEN_S = faded.OPEN_M * 60
RECENT = 15                       # continuation's "new extreme on effort": closed in the last 15 min (display)
hm = faded.hm
ARROW = {1: "▲", -1: "▼", 0: "", None: ""}
SHORT = {"NIFTY": "NIFTY", "BANKNIFTY": "BNF", "SENSEX": "SNX"}
KINDS = ("THAK", "JAARI", "MILA", "SAAF_NAHI")


def _num(x, sign=True, comma=True, nd=0):
    """A number for a terminal line: the real minus sign, an integral float without its .0, "?" for None."""
    if x is None:
        return "?"
    x = round(x, nd) if nd else (int(round(x)) if abs(x - round(x)) < 1e-9 or abs(x) >= 100 else round(x, 1))
    s = f"{abs(x):,}" if comma else f"{abs(x)}"
    return ("−" if x < 0 else "+" if sign and x > 0 else "") + s


# ---- the reads, per index (moved from tools/decode_now.py, unchanged) ------------------------------------------------

def delta_rows(bars5, n_last=8):
    """The last n closed bars: delta as a share of the leg's biggest bar in the same direction (faded.ratio's leg: an
    up-bar against the up-leg from the session low before it, a down-bar against the down-leg from the session high), and
    which made a new session extreme -- with 2a's 25% test on that extreme's own side ("effort fading")."""
    ext = faded.extremes(bars5)
    opened = faded.opened(bars5) is None
    out = []
    for n in range(max(0, len(bars5) - n_last), len(bars5)):
        d = bars5[n]["delta"]
        r = faded.ratio(bars5, n, "SELL" if d >= 0 else "BUY")
        nh, nl = (ext[n] if opened else (False, False))
        fade = None
        if nh or nl:
            fr = faded.ratio(bars5, n, "SELL" if nh else "BUY")
            fade = fr if fr["ok"] else None
        out.append({"bar": hm(bars5[n]["s"] // 60), "c": bars5[n]["c"], "delta": d, "src": bars5[n].get("src"),
                    "pct": None if r["ratio"] is None else round(r["ratio"] * 100), "big": r["big"],
                    "big_bar": r["big_bar"], "ext": "H" if nh else "L" if nl else "", "fading": fade})
    return out


def cvd_read(bars5):
    run, cvd = 0, []
    for b in bars5:
        run += b["delta"]
        cvd.append((run, faded.close(b)))
    if not cvd:
        return None
    pk, tr = max(cvd, key=lambda x: (x[0], x[1])), min(cvd, key=lambda x: (x[0], -x[1]))
    return {"now": cvd[-1][0], "peak": pk[0], "peak_t": hm(pk[1]), "trough": tr[0], "trough_t": hm(tr[1]),
            "dd": pk[0] - cvd[-1][0], "up": cvd[-1][0] - tr[0]}


def leg_of(bars5):
    """The current leg: the latest new session extreme decides it (a high: ▲ from the low before it), or None."""
    if faded.opened(bars5):
        return None
    ext = faded.extremes(bars5)
    n = next((k for k in range(len(bars5) - 1, 0, -1) if any(ext[k])), None)
    if n is None:
        return None
    up = ext[n][0]
    side = "SELL" if up else "BUY"
    k0 = faded._arg(bars5, 0, n, side)
    x0, x1 = bars5[k0]["l" if up else "h"], bars5[n]["h" if up else "l"]
    return {"d": 1 if up else -1, "side": side, "from_bar": hm(bars5[k0]["s"] // 60), "from": x0,
            "to_bar": hm(bars5[n]["s"] // 60), "to": x1, "k0": k0, "n": n}


def zz_thr(bars5, X, c):
    """A1's reversal: max(50 pts NIFTY-equivalent (ZZ_PCT of the price), 0.5 x today's IV-priced 30-min sigma) -- the
    panel research's rule (PANEL-DESIGN-V2 §B5, mockup NOTES D5: sigma30 = spot x ATM IV x sqrt(30 / (252 x 375))),
    the IV from rank.scale at close c; no IV -> the floor alone."""
    try:
        sd = (rank.scale(X, {"t": hm(c)}) if X and c is not None else {}).get("sigma_d")
    except Exception:                         # the IV is a refinement: its failure leaves the floor, never the block
        sd = None
    s30 = sd * math.sqrt(365 * 30 / (252 * 375)) if sd else 0      # rank.scale's sigma_d is spot x IV / sqrt(365)
    return max(ZZ_PCT * bars5[-1]["c"], ZZ_SIG * s30)


def swing_of(bars5, thr):
    """A1, THE DECODE LEG: the open leg of a zigzag on the 5-min closes reversing >= thr (board.js legs(), the panel
    mockup's port), from the true high / low within 15 min before its close pivot to its extreme since. None before the
    zigzag's first reversal (until then the open leg's direction is only a seed) or when the record does not begin at
    09:15: the caller then reads the session-extreme leg (leg_of)."""
    if faded.opened(bars5) or len(bars5) < 2 or not thr:
        return None
    c = [b["c"] for b in bars5]
    d = 1 if c[0] > bars5[0]["o"] else -1
    ext, ei, i0, turned = c[0], 0, 0, False
    for i in range(1, len(bars5)):
        if (c[i] >= ext) if d > 0 else (c[i] <= ext):
            ext, ei = c[i], i
        if ((ext - c[i]) if d > 0 else (c[i] - ext)) >= thr:
            d, i0, ext, ei, turned = -d, ei, c[i], i, True
    if not turned:
        return None

    def px(k, key):
        return bars5[k][key] if bars5[k].get(key) is not None else c[k]
    near = [k for k in range(i0 + 1) if bars5[k]["s"] >= bars5[i0]["s"] - ZZ_NEAR * 60]
    k0 = min(near, key=lambda k: px(k, "l")) if d > 0 else max(near, key=lambda k: px(k, "h"))
    side = "SELL" if d > 0 else "BUY"
    n = faded._arg(bars5, k0, len(bars5), side, own=True)
    return {"d": d, "side": side, "from_bar": hm(bars5[k0]["s"] // 60), "from": px(k0, "l" if d > 0 else "h"),
            "to_bar": hm(bars5[n]["s"] // 60), "to": px(n, "h" if d > 0 else "l"), "k0": k0, "n": n, "how": "swing",
            "thr": round(thr, 1)}


def lead_minutes(X, now):
    """The PE lead at every minute 09:16 .. now (faded.leads: the last chain row before each minute)."""
    return faded.leads(X, list(range(OPEN_S // 60 + 1, now // 60 + 1)))


def lead_read(lm, l5, now):
    m = now // 60
    v = lambda k: (lm.get(k) or {}).get("pe")                              # noqa: E731
    seen = [(x["pe"], k) for k, x in lm.items() if x["pe"] is not None]
    s5 = [(x["pe"], k) for k, x in l5.items() if x["pe"] is not None]
    pk, pk5 = (max(seen) if seen else None), (max(s5) if s5 else None)
    now_v, a15, a30 = v(m), v(m - 15), v(m - 30)
    return {"now": now_v, "t": hm(m), "a15": a15, "a30": a30,
            "chg15": None if None in (now_v, a15) else now_v - a15, "chg30": None if None in (now_v, a30) else now_v - a30,
            "peak": pk and pk[0], "peak_t": pk and hm(pk[1]), "peak5": pk5 and pk5[0], "peak5_t": pk5 and hm(pk5[1]),
            "why": None if now_v is not None else (lm.get(m) or {}).get("why")}


def fade_now(bars5, l5, leg):
    """FADE-D's 2a / 2b / 3 and the VWAP side at the last close, on the current leg's side (a ▲ leg: the SELL side)."""
    if not leg or not bars5:
        return None
    j, side = len(bars5) - 1, leg["side"]
    c, top = faded.close(bars5[j]), side == "SELL"
    ext, vw = faded.extremes(bars5), faded.vwaps(bars5)
    a = [faded.ratio(bars5, n, side) for n in range(1, j + 1)
         if (ext[n][0] if top else ext[n][1]) and faded.close(bars5[n]) >= c - faded.WINDOW]
    return {"side": side, "close": hm(c), "a": a, "a_ok": any(r["ok"] for r in a), "b": faded.cvd_turn(bars5, j, side),
            "oi": faded.lead_read(l5, c, side),
            "px_ok": None if vw[-1] is None else (bars5[-1]["c"] > vw[-1] if top else bars5[-1]["c"] < vw[-1])}


def leg_now(bars5, l5, leg, session=None):
    """fade_now's readings on the DECODE leg. A swing leg (A1) reads its own bars from its start -- its new extremes,
    its biggest bar, its CVD peak, the winning lead's peak since the start -- beside the session's VWAP (off `session`,
    the exchange's candles, when the flow record began late: A107) and CVD level; the session-extreme leg reads exactly
    fade_now (FADE-D's own)."""
    if not leg or leg.get("how") != "swing":
        return fade_now(bars5, l5, leg)
    k0, c = leg["k0"], bars5[-1]["c"]
    fd = fade_now(bars5[k0:], {k: v for k, v in l5.items() if k >= bars5[k0]["s"] // 60}, leg)
    off, vw = sum(b["delta"] for b in bars5[:k0]), faded.vwaps(session or bars5)[-1]
    return dict(fd, b=dict(fd["b"], cvd=fd["b"]["cvd"] + off, peak=fd["b"]["peak"] + off),
                px_ok=None if vw is None else (c > vw if leg["d"] > 0 else c < vw))


def _fixed15(fd, l15, c):
    """A24 on the call and the LEAD line: the winning lead's 15-min change on ONE strike set (onesided.lead15), signed
    to the side read, and whether the nine re-centred meanwhile. FADE-D's own reads (g["fd"]) are never touched."""
    if not fd:
        return fd
    f = l15.get(c)
    sg = 1 if fd["side"] == "SELL" else -1
    return dict(fd, oi=dict(fd["oi"], chg15=None if f is None else round(sg * f["chg"], 1),
                            shifted=bool(f and f["shifted"])))


def _pin(v):
    """A10: a lead at +/-100 means one side's aaj likha is <= 0 -- one-sided and thin, not huge writing (display)."""
    return " (ek-tarfa, patla)" if v is not None and abs(v) >= 99.95 else ""


def patla_of(idx, bars5):
    """A25 (display only, nothing reads it): " · patla (med N lot/5m)" for an index in THIN -- the median lots of its
    closed 5-min bars -- else ""."""
    if idx not in THIN:
        return ""
    v = sorted(b["vol"] for b in bars5 or () if isinstance(b.get("vol"), (int, float)))
    return f" · patla (med {_num(v[len(v) // 2], sign=False)} lot/5m)" if v else " · patla"


def _px(x, basis):
    """A25 / levels rule: a futures price with its spot (fut - the READ's basis) when the basis is known."""
    return f"{x:,.0f}f" if basis is None else f"{x - basis:,.0f}s|{x:,.0f}f"


def _min(t):
    h, m = str(t).split(":")[:2]
    return int(h) * 60 + int(m)


# ---- one index's facts at a 5-min close -----------------------------------------------------------------------------

def _rebase(pleg, p5, bars5):
    """A107: the leg read off the exchange's candles, on the recorded flow bars: k0 = its start's slot (or the first
    recorded after it), n = its extreme on those bars since -- a swing, so every flow sign reads only the leg's own
    recorded bars. None when the leg began before the record: the flow of its start was never seen."""
    s0 = p5[pleg["k0"]]["s"] if pleg else None
    k0 = next((k for k, b in enumerate(bars5) if b["s"] >= s0), None) if pleg and s0 >= bars5[0]["s"] else None
    if k0 is None:
        return None
    return dict(pleg, k0=k0, n=faded._arg(bars5, k0, len(bars5), pleg["side"], own=True), how="swing")


def facts(idx, now, bars5, X=None, zone=(), basis=None, fuel=None, pushes=None, push_why=None, push=None, price5=None):
    """Everything the block reads for one index at `now` (sec of day): the 5-min push / flow bars closed by then
    (confluence_log.push_bars' rows), THE READ's chain arrays `X` (read.from_v2, for the writers' lead), the zone rows
    whose 3-min bar had closed (confluence_log.zone_rows), the READ card's basis (fut - spot), READ-2's FUEL (read.fuel),
    the stack's push bars (hold2.pushes, or None with `push_why`) and the extension's last push (server._push_for: live
    only, {"up", "down"}: {t ms, px, rank, failed}). Any of them None -> its line reads "?".
    A107, a late start: when the flow bars do not begin at 09:15, `price5` (the exchange's 5-min candles from 09:15,
    confluence_log.price_bars) gives the DECODE leg and the session VWAP; the leg is rebased onto the recorded bars
    (_rebase) -- `pleg` keeps it as read, `flow_from` says where the record begins. FADE-D's leg (§1n) is untouched."""
    bars5 = [b for b in bars5 or () if b["s"] + faded.BAR * 60 <= now]
    p5 = [b for b in price5 or () if b["s"] + faded.BAR * 60 <= now]
    closes = list(range(OPEN_S // 60 + faded.BAR, now // 60 + 1, faded.BAR))
    l5 = faded.leads(X, closes) if X else {}
    l15 = {c: onesided.lead15(X, c) for c in closes} if X else {}
    leg = leg_of(bars5)
    vw = faded.vwaps(bars5)
    c_last = faded.close(bars5[-1]) if bars5 else None
    zz = zz_thr(bars5, X, c_last) if bars5 else None
    late = bool(bars5) and bool(faded.opened(bars5)) and bool(p5) and not faded.opened(p5)
    pleg = (swing_of(p5, zz) or (dict(leg_of(p5), how="session") if leg_of(p5) else None)) if late else None
    if late:
        vw, dleg = faded.vwaps(p5), _rebase(pleg, p5, bars5)
    else:
        dleg = swing_of(bars5, zz) or (dict(leg, how="session") if leg else None)
    return {"idx": idx, "now": now, "bars5": bars5, "c_last": c_last,
            "deltas": delta_rows(bars5), "cvd": cvd_read(bars5), "l5": l5, "zone": list(zone or ()), "basis": basis,
            "fuel": fuel, "pushes": pushes, "push_why": push_why, "push": push, "vwap": vw[-1] if vw else None,
            "leg": leg, "fd": fade_now(bars5, l5, leg), "l15": l15, "zz": zz, "dleg": dleg, "pleg": pleg,
            "flow_from": hm(bars5[0]["s"] // 60) if late else None,
            "dfd": _fixed15(leg_now(bars5, l5, dleg, p5 if late else None), l15, c_last)}


# ---- the seven signs --------------------------------------------------------------------------------------------------

def _push_sign(g):
    """(failed, chip) for the last push in the leg's direction since the leg began, or None. The extension's own push
    (live) when it sent one in the leg; else the stack's (hold2.pushes): failed = a later 5-min close back through its
    origin [I]."""
    leg, bars5 = g["dleg"], g["bars5"]
    d, s0 = leg["d"], bars5[leg["k0"]]["s"]
    a = ARROW[d]
    p = (g.get("push") or {}).get("up" if d > 0 else "down")
    if p:
        t = int(p["t"] // 1000 + 19800) % 86400
        if s0 <= t <= g["now"]:
            return p["failed"], f"{a} push {hm(t // 60)} {'fail' if p['failed'] else 'tika'}"
    P = [x for x in g.get("pushes") or () if x["d"] == d and x["s"] >= s0 and x["close"] * 60 <= g["now"]]
    if not P:
        return None
    x = P[-1]
    later = [b["c"] for b in bars5 if b["s"] > x["s"] and b.get("c") is not None]
    failed = any((c < x["origin"]) if d > 0 else (c > x["origin"]) for c in later)
    return failed, f"{a} push {x['t']} {'fail' if failed else 'tika'}"


def signs(g, peers):
    """(decel, continuation): [(key, chip)] of the signs present for this index's current leg -- each a short Hinglish
    chip with its number. `peers` = the other indices' facts. A sign whose input is missing is in neither list. The
    DECODE leg's own reads (g["dleg"] / g["dfd"], A1), never FADE-D's."""
    leg, fd = g["dleg"], g["dfd"]
    if not leg or not fd:
        return [], []
    d = leg["d"]
    hi = "high" if d > 0 else "low"
    dec, con = [], []
    r = fd["a"][-1] if fd["a"] else None                # N8: ONE effort sign, the latest new extreme's (7 slots, never 8)
    if r and r["ok"]:
        if r["ratio"] is not None and r["ratio"] < 0:              # the extreme printed on the other side's delta
            dec.append(("effort", f"nayi {hi} {r['bar']} · Δ ulta {_num(r['delta'], comma=False)}"))
        else:
            pct = "?" if r["ratio"] is None else _num(round(r["ratio"] * 100), sign=False, comma=False)
            dec.append(("effort", f"nayi {hi} {r['bar']} · {pct}% effort"))
    elif r and _min(r["close"]) >= _min(fd["close"]) - RECENT:
        con.append(("effort", f"nayi {hi} {r['bar']} · {round(r['ratio'] * 100)}% effort"))
    last = fd["b"]["delta"]
    if last * d < 0:
        dec.append(("delta", f"Δ {_num(last, comma=False)} leg ke khilaf"))
    elif last * d > 0:
        con.append(("delta", f"Δ {_num(last, comma=False)} leg ke saath"))
    b = fd["b"]
    if b["dd"] > 0:
        dec.append(("cvd", f"CVD {'peak' if d > 0 else 'low'} se {_num(b['cvd'] - b['peak'])}"))
    else:
        con.append(("cvd", f"CVD leg {'peak' if d > 0 else 'low'} pe"))
    oi = fd["oi"]
    if oi["now"] is not None:
        if oi["off"] is not None and oi["off"] >= faded.LEAD_PTS:
            dec.append(("lead", f"{oi['side']} lead peak se {_num(-oi['off'])}"))
        elif oi["off"] == 0 or (oi["chg15"] is not None and oi["chg15"] >= faded.LEAD_PTS):
            con.append(("lead", f"{oi['side']} lead peak pe {_num(oi['now'])}{_pin(oi['now'])}" if oi["off"] == 0
                        else f"{oi['side']} lead {_num(oi['chg15'])} in 15m"))
    if fd["px_ok"] is not None and g["vwap"] is not None:
        c = g["bars5"][-1]["c"]
        chip = f"VWAP ke {'upar' if c > g['vwap'] else 'neeche'} {_num(c - g['vwap'])}"
        (con if fd["px_ok"] else dec).append(("vwap", chip))
    ps = _push_sign(g)
    if ps:
        (dec if ps[0] else con).append(("push", ps[1]))
    # A107: a late-started peer's leg is its candles' (pleg) -- a direction, read exactly off price
    pd = [(SHORT.get(p["idx"], p["idx"]), (p.get("dleg") or p.get("pleg") or {}).get("d")) for p in peers]
    other, same = [s for s, x in pd if x == -d], [s for s, x in pd if x == d]
    if other and not same:                    # N8: one peers sign; split peers are neither side's
        dec.append(("peers", f"{'+'.join(other)} {ARROW[-d]} ulta leg"))
    elif same and not other:
        con.append(("peers", f"{'+'.join(same)} {ARROW[d]} saath"))
    return dec, con


def call(leg, dec, con):
    """The display rule (module docstring): a COUNT of the signs present, never a %."""
    if not leg:
        return {"text": "saaf nahi", "kind": "SAAF_NAHI", "d": 0, "c": 0, "of": OF, "signs": []}
    d, c, a = len(dec), len(con), ARROW[leg["d"]]
    D, C = [x[1] if isinstance(x, tuple) else x for x in dec], [x[1] if isinstance(x, tuple) else x for x in con]
    # the call's own signs first, then the other side's, each of those prefixed with its side ("jaari · " / "thak · ")
    if d >= 4 and d > c:
        return {"text": f"{a} leg thak raha · {d}/{OF}", "kind": "THAK", "d": d, "c": c, "of": OF,
                "signs": D + [f"jaari · {x}" for x in C]}
    if c >= 4 and c > d:
        return {"text": f"{a} leg jaari · {c}/{OF}", "kind": "JAARI", "d": d, "c": c, "of": OF,
                "signs": C + [f"thak · {x}" for x in D]}
    return {"text": f"{a} mila-jula · {d}/{c}", "kind": "MILA", "d": d, "c": c, "of": OF,
            "signs": [f"thak · {x}" for x in D] + [f"jaari · {x}" for x in C]}


# ---- the five lines ---------------------------------------------------------------------------------------------------

def _ratio(bars5, leg, k):
    """faded.ratio on the DECODE leg: a swing leg's own bars from its start (A1); the session leg reads the session."""
    k0 = leg["k0"] if leg.get("how") == "swing" else 0
    return None if k < k0 else faded.ratio(bars5[k0:], k - k0, leg["side"])


def _delta_line(g):
    bars5, leg = g["bars5"], g["dleg"]
    if not bars5:
        return "Δ ? — no closed 5-min bar yet"
    parts, anchor = [], ""
    big = _ratio(bars5, leg, leg["n"]) if leg else None
    for k in range(max(0, len(bars5) - 6), len(bars5)):
        dl = bars5[k]["delta"]
        mark = ("H" if leg["d"] > 0 else "L") if leg and k == leg["n"] else ""
        r = _ratio(bars5, leg, k) if leg and dl * leg["d"] > 0 else None
        if r is None or r["ratio"] is None or r["big_bar"] == hm(bars5[k]["s"] // 60):
            parts.append(_num(dl, comma=False) + mark)
        else:
            parts.append(f"{round(r['ratio'] * 100)}%{mark}")
    if big and big["big"] is not None and _min(big["big_bar"]) * 60 < bars5[max(0, len(bars5) - 6)]["s"]:
        anchor = f"big {_num(big['big'], comma=False)} {big['big_bar']} | "
    return "Δ " + anchor + " · ".join(parts) + patla_of(g["idx"], bars5)


def _cvd_line(g):
    fd = g["dfd"]
    th = patla_of(g["idx"], g["bars5"]) + (f" · {g['flow_from']} se" if g.get("flow_from") else "")   # A107: from the record
    if fd:
        b, d = fd["b"], g["dleg"]["d"]
        return (f"CVD {_num(b['peak'], sign=False)} {'peak' if d > 0 else 'low'} {b['peak_close']} → "
                f"{_num(b['cvd'], sign=False)} ({_num(b['cvd'] - b['peak'])})" + th)
    c = g["cvd"]
    if not c:
        return "CVD ? — no closed 5-min bar yet"
    return f"CVD {_num(c['now'], sign=False)} · peak {_num(c['peak'], sign=False)} {c['peak_t']} ({_num(-c['dd'])})" + th


def _lead_line(g):
    """The DECODE leg's lead read (its peak since a swing start, A1); Δ15 on one strike set, stamped "window shifted"
    when the nine re-centred in those 15 min (A24); a pinned +/-100 says so (A10)."""
    c = g["c_last"]
    fd = g.get("dfd")
    side = (fd or {}).get("side") or "SELL"
    if c is None:
        return "PE lead ? — no closed 5-min bar yet"
    oi = (fd or _fixed15({"side": side, "oi": faded.lead_read(g["l5"], c, side)}, g.get("l15") or {}, c))["oi"]
    if oi["now"] is None:
        return f"{oi['side']} lead ? — {str(oi['why'] or 'no chain').replace(faded.CC, '')}"
    p5 = faded.lead_read({k: v for k, v in g["l5"].items() if k <= c - faded.BAR}, c - faded.BAR, side)["now"]
    ch = "" if p5 is None else f"{_num(p5, sign=False)} → "
    mv = "" if p5 is None else f" ({_num(oi['now'] - p5)} in 5m)"
    return (f"{oi['side']} lead {ch}{_num(oi['now'], sign=False)}{_pin(oi['now'])}{mv} · Δ15 {_num(oi['chg15'])}"
            f"{' · window shifted' if oi.get('shifted') else ''} · "
            f"peak {_num(oi['peak'], sign=False)}{_pin(oi['peak'])} {oi['peak_t']}")


def _fuel_line(g):
    fu = g["fuel"]
    if g["now"] < FUEL_FROM:                  # A12: READ-2's 40-min futures OI window has not closed yet (§1l, locked)
        return f"FUEL ? · 40 min OI chahiye · {hm(FUEL_FROM // 60)} se"
    if not fu:
        return "FUEL ? — no rank reference"
    ref = "" if fu.get("n") is None else f" · ref {fu['n']} din"      # A36: the reference's depth (days in this part)
    if fu.get("why"):
        return "FUEL ?" + ref + " — " + str(fu["why"]).replace(read.CC, "").replace(faded.CC, "")
    return (f"FUEL {fu.get('kind') or 'p80 se kam'} · p{fu.get('rank'):.0f} · OI {_num(fu.get('oi_pct'), nd=2)}% · "
            f"px {_num(fu.get('px'))} {ARROW.get(fu.get('vote')) or '·'}").rstrip(" ·") + ref


def _xs(x):
    """The multiple for the line, rounded TOWARD 1 so it never shows a threshold (2x / 0.5x) it has not crossed."""
    return f"{(math.floor(x * 10) if x >= 1 else math.ceil(x * 10)) / 10:.1f}×"


def _effort_line(g):
    """A44: "EFFORT 2.3× din ka · high 10:42 mehenga (palat?) [I]" -- effort.read's dict in words; "?" with its why."""
    e = g.get("effort")
    if not e:
        return "EFFORT ? — not read"
    if e["word"] == "patla":
        return "EFFORT nahi padha" + (patla_of(g["idx"], g["bars5"]) or " · patla") + " [I]"
    if e["x"] is None:
        return "EFFORT ? — " + str(e["why"] or "not read").replace("could not check — ", "")
    at = f"{e['at'].lower()} {e['t']} " if e["at"] else ""
    tag = "[I]" if g["idx"] == "NIFTY" else f"[I · {SHORT.get(g['idx'], g['idx'])} test nahi]"   # Fable: NIFTY only
    return f"EFFORT {_xs(e['x'])} din ka · {at}{e['word']} {tag}"


def _vw_side(g):
    if not g.get("bars5") or g.get("vwap") is None:
        return "?"
    return "▲" if g["bars5"][-1]["c"] > g["vwap"] else "▼"


def _sync_line(g, peers):
    return "SYNC " + " · ".join([f"{SHORT.get(g['idx'], g['idx'])} {_vw_side(g)}VWAP"]
                                + [f"{SHORT.get(p['idx'], p['idx'])} {_vw_side(p)}" for p in peers])


def lines(g, peers):
    return [_delta_line(g), _cvd_line(g), _lead_line(g), _fuel_line(g), _sync_line(g, peers), _effort_line(g)]


# ---- the setups, live at the current close: the registered functions, called ------------------------------------------

def _plan(en, basis):
    """A108: an entry's own price and stop for the SETUP alert, "E 22,422s|22,500f · stop 22,356s|22,434f" (RIDE's stop
    is its line0) -- {} when the entry carries no price. Display only: nothing reads it but messages.build."""
    E, st = (en or {}).get("E"), (en or {}).get("stop", (en or {}).get("line0"))
    return {"plan": f"E {_px(E, basis)} · stop {_px(st, basis)}"} if E is not None and st is not None else {}


def _held(en, g, rin):
    """N2: an entry's HOLD v2 state at the current close -- hold2.exit_v2 (§1m as frozen, its exit section, as
    faded.exits calls it) with `end` = the close, on RIDE's live inputs (`rin`: the 1-min and 3-min futures bars and the
    chain grid, cut at the close). Open: "line 73,612 · +0.4R" / "lock ..."; out: "gave up @10:57 −0.1R" / "out @10:34
    −1R". None when those bars are not there (the chip keeps MATCH)."""
    if not (rin or {}).get("ones") or not rin.get("b3") or rin.get("chain") is None or g["c_last"] is None:
        return None
    d, start = en["d"], _min(en["t"])
    v2 = hold2.exit_v2(d, {"E": en["E"], "line0": en["stop"]}, start, rin["ones"], g.get("pushes"),
                       hold2.closes(d, start, rin["b3"], rin["chain"], g["bars5"]), end=g["c_last"],
                       trail_why=g.get("push_why"))
    if not v2:
        return None
    if v2["how"] == "open":
        risk = abs(en["stop"] - en["E"])
        R = None if not risk else d * (g["bars5"][-1]["c"] - en["E"]) / risk
        return f"{'lock' if v2['line_src'] == 'lock' else 'line'} {_px(v2['line'], g.get('basis'))} · {_num(R, nd=1)}R"
    return f"{'gave up' if v2['how'] == 'gave_up' else 'out'} @{v2['exit_t']} {_num(v2['R'], nd=1)}R"


def _fade_d(g, rin=None):
    """FADE-D: the episode whose 30-min window holds the last close (faded.episodes / faded.evaluate), its readings
    at that close; else the leg's side read now (fade_now) with state "—". Once the episode has an entry, the state is
    its HOLD v2 state (N2, _held) instead of MATCH -- the field and the checks are unchanged."""
    bars5, c = g["bars5"], g["c_last"]
    if c is None:
        return None
    leg = g["leg"]
    live = [e for e in faded.episodes(bars5, g["zone"]) if e["locs"][0]["close"] <= c <= e["end"]]
    if live:
        ep = sorted(live, key=lambda e: (bool(leg) and e["side"] == leg["side"], e["locs"][-1]["close"]))[-1]
        ev = faded.evaluate(ep, bars5, g["l5"])
        r = ev["bars"][-1]
        return {"name": "FADE-D", "side": ep["side"], "checks": {"2a": r["a"]["ok"], "2b": r["b"]["ok"], "3": r["oi"]["ok"]},
                "state": (_held(ev["entry"], g, rin) or "MATCH") if ev["entry"] else "ARMED", **_plan(ev["entry"], g["basis"])}
    fd = g["fd"]
    if not fd:
        return None
    return {"name": "FADE-D", "side": fd["side"], "checks": {"2a": fd["a_ok"] if fd["a"] else False, "2b": fd["b"]["ok"],
                                                           "3": fd["oi"]["ok"]}, "state": "—"}


def _fade(g, fin):
    """FADE (§1i zone + OI + flow): the zone entry whose window (its bar + 3, <= 9 min) holds the last closed 3-min bar,
    confluence.evaluate's readings there. `fin` = {"bars3": the closed 3-min band bars, "chain", "book", "gc"}."""
    leg = g["leg"]
    dflt = {"name": "FADE", "side": ("SELL" if leg["d"] > 0 else "BUY") if leg else None, "checks": {}, "state": "—"}
    b3 = (fin or {}).get("bars3")
    if not b3:
        return dflt if leg else None
    last = confluence.close_of(confluence.flat(b3[-1]).get("t"))
    for s in reversed(confluence.setups(b3)):
        c0 = confluence.close_of(s["t"])
        if c0 is None or last is None or not 0 <= last - c0 <= confluence.WINDOW_MIN or len(b3) - 1 - s["i"] > confluence.WINDOW_BARS:
            continue
        ev = confluence.evaluate(s, b3, fin["chain"], fin["book"], fin.get("gc"))
        if not ev["bars"]:
            continue
        r = ev["bars"][-1]
        return {"name": "FADE", "side": s["side"], "checks": {"zone": r["zone"]["ok"], "oi": r["oi"]["ok"],
                                                              "flow": r["flow"]["ok"]},
                "state": "MATCH" if ev["entry"] else "ARMED", **_plan(ev["entry"], g["basis"])}
    return dflt if leg else None


def _ride(g, rin):
    """RIDE (§1j §E + OI + flow): the §E entry whose window (its bar + 3, <= 9 min) holds the last closed 3-min bar,
    ride.evaluate's readings there. `rin` = {"b3", "rows", "basis", "chain", "book", "gc"} (confluence_log.ride_inputs)."""
    leg = g["leg"]
    dflt = {"name": "RIDE", "side": ("BUY" if leg["d"] > 0 else "SELL") if leg else None, "checks": {}, "state": "—"}
    b3 = (rin or {}).get("b3")
    if not b3:
        return dflt if leg else None
    for e in reversed(ride.entries(b3, rin["rows"], rin["basis"])):
        if len(b3) - 1 - e["i"] > ride.WINDOW_BARS or (b3[-1]["e"] - b3[e["i"]]["e"]) // 60 > ride.WINDOW_MIN:
            continue
        ev = ride.evaluate(e, b3, rin["chain"], rin["book"], rin.get("gc"))
        if not ev["bars"]:
            continue
        r = ev["bars"][-1]
        return {"name": "RIDE", "side": "BUY" if e["d"] > 0 else "SELL",
                "checks": {"loc": r["loc"]["ok"], "oi": r["oi"]["ok"], "flow": r["flow"]["ok"]},
                "state": "MATCH" if ev["entry"] else "ARMED", **_plan(ev["entry"], g["basis"])}
    return dflt if leg else None


def setups(g, fade_in=None, ride_in=None):
    """FADE, RIDE, FADE-D in that order, each live at the current close or "—"; one that cannot be read is dropped
    (no side to show). Each part fails soft on its own."""
    out = []
    for fn in (lambda: _fade(g, fade_in), lambda: _ride(g, ride_in), lambda: _fade_d(g, ride_in)):
        try:
            s = fn()
        except Exception:                     # one setup's failure is that chip's absence, never the block's
            s = None
        if s and s.get("side"):
            out.append(s)
    th = patla_of(g["idx"], g["bars5"])
    for s in out:                             # A25: display only -- the chip's state and checks are unchanged
        if th and s["name"] == "FADE-D":
            s["thin"] = th[3:]
    return out


# ---- the block ------------------------------------------------------------------------------------------------------

def leg_out(g):
    leg, bs = g["dleg"] or g.get("pleg"), g["basis"]
    if not leg:
        return None

    def pt(t, x):
        return {"t": t, "fut": x, "spot": None if bs is None or x is None else round(x - bs, 1)}
    return {"d": leg["d"], "start": pt(leg["from_bar"], leg["from"]), "ext": pt(leg["to_bar"], leg["to"])}


def _onesided(g, peers):
    try:                                      # the meter's failure is its own "?", never the block's
        return onesided.meter(g["bars5"], g["l5"], g.get("l15"), [p["bars5"] for p in peers])
    except Exception as e:
        return onesided.blank(f"could not check — {type(e).__name__}: {e}")


def exhaust_of(g):
    """VALIDATE rev 3's EXHAUST (docs/hold/VALIDATE-PREREG-rev3.md §1): FADE-D 2a's fading-effort test on the DECODE
    leg's latest new extreme -- the very reading `signs` turns into its effort decel sign -- as {d, bar, close, ratio},
    else None (no leg, no new extreme in the window, or the effort did not fade). Display only."""
    leg, fd = g.get("dleg"), g.get("dfd")
    a = (fd or {}).get("a") or ()
    r = a[-1] if a else None
    if not leg or not r or not r.get("ok"):
        return None
    return {"d": leg["d"], "bar": r.get("bar"), "close": r.get("close"), "ratio": r.get("ratio")}


def decode(g, peers, fade_in=None, ride_in=None):
    """The contract (shared with the extension): {call, lines (<= 6, EFFORT last), setups, leg, t, tag, onesided,
    effort, exhaust}. `g` = facts(...) for this index plus g["effort"] (effort.read, set by the server), `peers` = the
    other indices' facts. The server adds `age_s` when it serves the block (A13)."""
    dec, con = signs(g, peers)
    c = call(g["dleg"], dec, con)
    bs, pl = g["bars5"], g.get("pleg")
    # A104, rule 6: a record not from 09:15 could not be read -- "?" with its why, never "saaf nahi"; unless (A107) the
    # exchange's candles from 09:15 were read and show no leg, which IS saaf nahi
    if not g["dleg"] and faded.opened(bs) and (pl or not g.get("flow_from")):
        why = (f"leg {ARROW[pl['d']]} {pl['from_bar']} se · flow {g['flow_from']} se" if pl
               else f"5m bars {hm(bs[0]['s'] // 60)} se · 09:15 nahi" if bs else "koi 5m bar nahi")
        c = dict(c, text="?", signs=[why])
    return {"call": c, "lines": lines(g, peers)[:NLINES], "setups": setups(g, fade_in, ride_in),
            "leg": leg_out(g), "t": hm(g["c_last"]) if g["c_last"] is not None else None, "tag": "I",
            "onesided": _onesided(g, peers), "effort": g.get("effort") or effort.blank("could not check — not read"),
            "exhaust": exhaust_of(g)}


def empty(why):
    """The block when an index cannot be read at all: every field present, the call "?"."""
    return {"call": {"text": "?", "kind": "SAAF_NAHI", "d": 0, "c": 0, "of": OF, "signs": []},
            "lines": [f"? — {why}"], "setups": [], "leg": None, "t": None, "tag": "I", "onesided": onesided.blank(why),
            "effort": effort.blank(why), "exhaust": None}


def at_close(now):
    """The 5-min close a reading at `now` (sec of day) belongs to: live and replay read the same instant."""
    return now // 300 * 300

