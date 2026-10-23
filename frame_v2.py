"""frame_v2.py -- the extension v2's TapeMap half: frame.read / plan / writers / ux_flow, as pure functions.

Spec docs/superpowers/specs/2026-10-19-extension-v2-design.md §7; the wire is orderflow-desk/docs/V2-PLAN.md's
"Frame contract". No I/O, no clock: the caller hands in THE READ's arrays (read.from_v2, cut to `now` for a replay),
its timeline and card, the Upstox 5-min bars and `now`, so the server (server._frame_v2) and the replay tool
(tools/frame_v2_replay.py) give the same answer from the same files.

  read     read.card + the timeline's last row, re-shaped: KHEL, FLIP spot|fut, targets, the basis band;
           READ-2's src ("writers" | "flow+fuel" | null), JAGAH, and SIZE (ADHA on a LEAN, PURA on a TREND). [I]
  plan     READ-V2 §E (docs/read/READ-V2-PREREG.md) on 3-min futures bars built from the 1-s ticks, ported from
           docs/extension-v2/build_mockup.py run_entry_rule. Futures prices. RANGE -> her zone machine's pockets. [I]
  writers  ATM +/- 2 30-min OI change (thousands) ranked against rank_ref.writers30, and the READ's QUIT events.  [M]
  ux_flow  the last closed Upstox 5-min bars, for "GC+UX agree / GC only / sources disagree".                  [M]

DISPLAY ONLY: gates nothing; read.py's rules (REV), the zone machine, fold / validate / story are untouched.
"""
from __future__ import annotations

import bisect
import datetime
import math

import read
from contract_bars import vwap_sigma

OPEN_S, FORM_AT, LATE_S, CLOSE_S = read.OPEN_S, read.FORM_AT, read.LATE_S, read.CLOSE_S
BAR3 = 180
MAX_MISS = 1                 # 3-min slots with no futures tick allowed before the plan refuses (a restart's minute)
CARRY = 0.068                # the basis carry model: spot x 6.8% x DTE / 365
KHEL = {"TREND": "RIDE", "LEAN": "RIDE", "RANGE": "FADE", "WAIT": "BAITHO"}
CC = read.CC
hm = read.hm


def _r(x, n=1):
    return None if x is None else round(x, n)


def rank(tab, x):
    """The page's rank: the largest k with q[k] <= x; 0 below the reference's minimum; None when either is missing."""
    if not tab or not tab.get("q") or x is None:
        return None
    return max(0, bisect.bisect_right(tab["q"], x) - 1)


def dte(day, expiry):
    """Calendar days to the futures expiry, or None."""
    try:
        return (datetime.date.fromisoformat(str(expiry)[:10]) - datetime.date.fromisoformat(day)).days
    except (TypeError, ValueError):
        return None


def cut(X, T):
    """read.from_v2's dict holding only rows and bars at or before T (sec of day): a replay sees nothing after T.
    New lists; the caller's arrays are not touched."""
    if T is None:
        return X
    n = bisect.bisect_right(X["t"], T)
    out = dict(X)
    for k in ("t", "spot", "ce_oi", "pe_oi", "ce_ltp", "pe_ltp"):
        out[k] = X[k][:n]
    bars = X.get("bars") or []
    out["bars"] = bars[:bisect.bisect_right([b[0] for b in bars], T)]
    out["pre"] = [p for p in X.get("pre") or () if p[0] <= T]
    hl = X.get("hl") or []
    out["hl"] = hl[:bisect.bisect_right(hl, [T, float("inf"), float("inf")])]
    sl = X.get("slow") or 1
    for k in ("ce_iv", "pe_iv"):                      # one IV row per `slow` chain rows: the rows at or before T only
        if X.get(k) is not None:
            out[k] = X[k][:(n - 1) // sl + 1] if n else []
    out["flow_from"] = out["bars"][0][0] if out["bars"] else None
    return out


PARITY_TOL = 0.001          # the options' forward agrees with the future within 0.1% of spot


def basis_band(spot, v, dte_, parity=None):
    """fut - spot against a carry model: expected = spot x 6.8% x DTE / 365, plausible within
    [0.5 x expected - 10, 1.6 x expected + 20]. DTE unknown -> a fixed 20..120. [I]
    `parity` (parity_basis(): the options' put-call-parity forward, carried to the future's expiry, minus spot [M]) is
    the second witness (decode-loop D6, 19 Oct): on 16 Oct NIFTY read +2..+12 at 11 DTE against a carry of ~47 and the
    band called it implausible, yet the options priced the same forward within 2 pts -- the market's basis, not a feed
    fault. Outside the carry band but within PARITY_TOL x spot of the options -> plausible, flagged `unusual`."""
    if dte_ is None or spot is None:
        exp, lo, hi, why = None, 20.0, 120.0, "expiry unknown -- fixed band 20..120"
    else:
        exp = spot * CARRY * dte_ / 365
        lo, hi, why = 0.5 * exp - 10, 1.6 * exp + 20, None
    out = {"v": _r(v), "expected": _r(exp), "lo": _r(lo), "hi": _r(hi), "dte": dte_, "parity": _r(parity),
           "unusual": False, "tag": "I"}
    if v is None:
        return dict(out, ok=False, why=CC + "no future/spot pair in the last 15 minutes")
    ok = lo <= v <= hi
    if not ok and parity is not None and spot and abs(v - parity) <= PARITY_TOL * spot:
        return dict(out, ok=True, unusual=True,
                    why=(f"basis {v:+.1f} carry se alag ({exp:.0f} at {dte_} DTE) · options bhi yahi kehte ({parity:+.1f}) [M]"
                         if exp is not None else f"basis {v:+.1f} · options bhi yahi kehte ({parity:+.1f}) [M]"))
    if not ok:
        why = (f"basis {v:+.1f} implausible: carry {exp:.0f} at {dte_} DTE, band {lo:.0f}..{hi:.0f}" if exp is not None
               else f"basis {v:+.1f} outside the fixed band 20..120 (expiry unknown)")
        if parity is not None:
            why += f"; options say {parity:+.1f}"
    return dict(out, ok=ok, why=why)


def parity_basis(X, now, day):
    """The options' basis [M]: at each of the last 15 one-minute marks up to `now`, the ATM +/- 1 synthetic forward
    (K + CE - PE, LTPs; median over the strikes), carried from the options' expiry to the future's at CARRY, minus
    spot; the median of those. None when the chain carries no expiry, no future expiry, or no strike with both LTPs."""
    ts = X.get("t") or []
    od, fd = dte(day, X.get("expiry")), dte(day, X.get("fut_expiry"))
    if not ts or od is None or fd is None or od < 0:
        return None
    now = ts[-1] if now is None else now
    step = X.get("step") or 1
    pos = {k: j for j, k in enumerate(X["ks"])}
    out = []
    for m in range(now - 14 * 60, now + 1, 60):
        i = bisect.bisect_right(ts, m) - 1
        if i < 0 or m - ts[i] > 60:
            continue
        spot = X["spot"][i]
        atm = math.floor(spot / step + 0.5) * step
        syn = []
        for k in (atm - step, atm, atm + step):
            j = pos.get(k)
            c = X["ce_ltp"][i][j] if j is not None else None
            p = X["pe_ltp"][i][j] if j is not None else None
            if c is not None and p is not None:
                syn.append(k + (c - p) / 20)                 # LTPs ride in 0.05 ticks
        if syn:
            out.append(sorted(syn)[len(syn) // 2] + spot * CARRY * (fd - od) / 365 - spot)
    return round(sorted(out)[len(out) // 2], 1) if out else None


def _fut(x, basis):
    return None if x is None or not (basis or {}).get("ok") else round(x + basis["v"], 1)


def read_part(card, tl, basis, bf_note=None, expr=None):
    """frame.read from read.card(...) and its timeline. fut = spot + basis only while the basis is plausible (else
    null: the page shows one banner)."""
    rows = tl.get("rows") or []
    r = rows[-1]
    word, d = card["word"], card["dir"]
    flip = ({"spot": r["flip"], "fut": _fut(r["flip"], basis)}
            if word in ("TREND", "LEAN") and r.get("flip") is not None else None)
    box = None
    if word == "RANGE" and r.get("box"):
        box = {k: (dict(b, fut=_fut(b["k"], basis)) if b else None) for k, b in r["box"].items()}
    w = r.get("writers") or {}
    blind = [f"{k}: {x.get('why')}" for k, x in (("WRITERS", r["writers"]), ("PRICE", r["price"]), ("FLOW", r["flow"]))
             if x.get("vote") is None]
    if bf_note:
        blind.append(bf_note)
    return {"ok": True, "t": card["t"], "word": word, "dir": d, "arrow": card["arrow"], "khel": KHEL.get(word, "?"),
            "since": card["since"], "agree": card["agree"], "spot": card["spot"], "spot_at": card["spot_at"],
            "flip": flip, "box": box,
            "targets": [{"k": x["k"], "fut": _fut(x["k"], basis), "side": x["side"], "oi": x["oi"]} for x in r.get("targets") or ()],
            "basis": basis,
            "writers": dict({k: w.get(k) for k in ("cls", "A", "ce", "pe", "ce30", "pe30", "vote")},
                            word=read.CLS_WORD.get(w.get("cls"))),
            "size": "ADHA" if word == "LEAN" else "PURA" if word == "TREND" else None, "expr": expr,
            "warn": card.get("warn") or [], "events": (tl.get("events") or [])[-12:], "blind": blind,
            "src": card.get("src"), "jagah": card.get("jagah"), "tag": "I"}    # READ-2: "writers" | "flow+fuel" | null


# ---- 3-min futures bars ------------------------------------------------------------------------------------------

def bars3(ticks, lot, now=None, width=BAR3):
    """Closed 3-min futures bars from v2feed's 1-s bars [sec, px x 10, vol, buy] (contracts), aligned to 09:15:
    {s, e, o, h, l, c, v (lots), delta (lots, None when the bar traded nothing), vwap, sig} with the session VWAP and
    sigma of contract_bars.vwap_sigma (the tape's recurrence). A bar still forming at `now` is never returned.
    `width` (sec) other than BAR3 gives the same bars at another width: RIDE's 1-min bars (ride.py, §1j)."""
    lot = lot or 1
    end = min(CLOSE_S, now if now is not None else CLOSE_S)
    out, cur = [], None
    for sec, px10, vol, buy in ticks or ():
        if sec < OPEN_S:
            continue
        s0 = OPEN_S + (sec - OPEN_S) // width * width
        if s0 + width > end:
            break
        px = px10 / 10
        if cur is None or cur["s"] != s0:
            cur = {"s": s0, "e": s0 + width, "o": px, "h": px, "l": px, "c": px, "vol": 0, "buy": 0}
            out.append(cur)
        cur["h"], cur["l"], cur["c"] = max(cur["h"], px), min(cur["l"], px), px
        cur["vol"] += vol
        cur["buy"] += buy
    bands = vwap_sigma([(b["h"], b["l"], b["c"], b["vol"]) for b in out])
    return [{"s": b["s"], "e": b["e"], "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": round(b["vol"] / lot),
             "delta": round((2 * b["buy"] - b["vol"]) / lot) if b["vol"] else None,
             "vwap": bd["vwap"], "sig": bd["u1"] - bd["vwap"]} for b, bd in zip(out, bands)]


def _holes(b3, now):
    """Why the bars cannot carry her chart's VWAP (more than MAX_MISS 3-min slots without a tick since 09:15), or None."""
    last_end = OPEN_S + (min(now, CLOSE_S) - OPEN_S) // BAR3 * BAR3
    have = {b["s"] for b in b3}
    miss = [s for s in range(OPEN_S, last_end, BAR3) if s not in have]
    if len(miss) <= MAX_MISS:
        return None
    return (CC + f"futures ticks missing for {len(miss)} of {(last_end - OPEN_S) // BAR3} 3-min bars "
            f"(first {hm(miss[0])}); VWAP / sigma would not be her chart's")


def _sec(t):
    h, m = t.split(":")[:2]
    return int(h) * 3600 + int(m) * 60


def _t2(vw, sg, d, wall):
    """The nearer of +/-3 sigma and the READ's first wall (strike, futures price); a wall nearer than T1 is no T2."""
    t3, t1 = vw + d * 3 * sg, vw + d * 2 * sg
    if wall is not None and (wall[1] < t1 if d < 0 else wall[1] > t1):
        t2 = max(t3, wall[1]) if d < 0 else min(t3, wall[1])
        if t2 != t3:
            return {"fut": round(t2, 1), "spot": wall[0], "name": ("PE" if d < 0 else "CE") + f" wall {wall[0]:,.0f}"}
    return {"fut": round(t3, 1), "name": "−3σ" if d < 0 else "+3σ"}


def _wall(row, basis):
    """(strike, futures price) of the READ row's first target, with the row's own basis -- only while the day's basis
    is plausible and the row's basis sits inside its band; else None."""
    k = ((row.get("targets") or [{}])[0]).get("k")
    bv = row.get("basis")
    if k is None or bv is None or not (basis or {}).get("ok") or not basis["lo"] <= bv <= basis["hi"]:
        return None
    return k, k + bv


def plan(b3, rows, basis, now):
    """READ-V2 §E on closed 3-min futures bars -> (plan dict, None) or (None, why). Ported from build_mockup
    run_entry_rule: from 09:45, TREND / LEAN d arms the zone (SELL -1 sigma..VWAP / BUY VWAP..+1 sigma); a closed bar
    with high >= -1 sigma, close < -1 sigma and delta < 0 (mirror) triggers; a 3-min close beyond VWAP stops; T1 +/-2
    sigma; T2 the nearer of +/-3 sigma and the READ's first wall (fixed at entry). After a stop or T2 the zone re-arms
    once price reaches 1.5 sigma beyond VWAP on the trend side. A bar whose delta cannot be read is "?", never a
    trigger. Levels come from the latest closed bar's VWAP / sigma."""
    now = CLOSE_S if now is None else now
    last = b3[-1] if b3 else None
    base = {"px": _r(last and last["c"]), "vwap": _r(last and last["vwap"]), "sigma": _r(last and last["sig"]),
            "bar_t": hm(last["e"]) if last else None, "late": now >= LATE_S, "tag": "I"}
    hole = _holes(b3, now)
    if now < FORM_AT:
        if hole:                                  # no band to show either
            base.update(px=None, vwap=None, sigma=None)
        return dict(base, ok=True, d=0, word="BAN RAHA", state="WAIT_0945", since=None, zone=None, trigger_rule=None,
                    kill=None, t1=None, t2=None, trigger=None, size=None, rows=[],
                    why="09:45 se pehle zone nahi · §E" + (" · " + hole if hole else "")), None
    if not rows:
        return None, CC + "no READ mark yet"
    if hole:
        return None, hole
    marks = [(_sec(r["t"]), r) for r in rows]
    msec = [m[0] for m in marks]

    def word_at(e):
        i = bisect.bisect_right(msec, e) - 1
        return marks[i][1] if i >= 0 else None

    E, pos, armed, label, since = [], None, True, None, None
    for b in b3:
        if b["s"] < FORM_AT:
            continue
        w = word_at(b["e"])
        d = w["dir"] if w and w["word"] in ("TREND", "LEAN") else 0
        vw, sg, t = b["vwap"], b["sig"], hm(b["e"])
        now_label = None
        if pos:
            pd = pos["d"]
            if (pd < 0 and b["c"] > vw) or (pd > 0 and b["c"] < vw):
                E.append({"t": t, "what": "STOP", "px": b["c"], "why": f"3m close {'>' if pd < 0 else '<'} VWAP {vw:,.1f}"})
                pos, armed, now_label = None, False, "STOPPED"
            else:
                if not pos["t1"] and ((pd < 0 and b["l"] <= vw - 2 * sg) or (pd > 0 and b["h"] >= vw + 2 * sg)):
                    pos["t1"] = t
                    E.append({"t": t, "what": "T1", "px": round(vw + pd * 2 * sg, 1)})
                if (pd < 0 and b["l"] <= pos["t2"]["fut"]) or (pd > 0 and b["h"] >= pos["t2"]["fut"]):
                    E.append({"t": t, "what": "T2", "px": pos["t2"]["fut"]})
                    pos, armed, now_label = None, False, "T2"
        elif not armed:
            if d and ((d < 0 and b["l"] <= vw - 1.5 * sg) or (d > 0 and b["h"] >= vw + 1.5 * sg)):
                armed = True
        elif d:
            hit = (d < 0 and b["h"] >= vw - sg and b["c"] < vw - sg) or (d > 0 and b["l"] <= vw + sg and b["c"] > vw + sg)
            if hit and b["delta"] is None:
                E.append({"t": t, "what": "?", "px": b["c"], "why": "zone touched, 3m delta ? (no traded volume read)"})
            elif hit and b["delta"] * d > 0:
                pos = {"d": d, "word": w["word"], "t": t, "px": b["c"], "delta": b["delta"], "t1": None,
                       "t2": _t2(vw, sg, d, _wall(w, basis))}
                E.append({"t": t, "what": "ENTRY", "px": b["c"], "why": (
                    f"{w['word']} {read.ARROW[d]}: high {b['h']:,.1f} >= −1σ {vw - sg:,.1f}, close < −1σ, 3m delta {b['delta']:+d}"
                    if d < 0 else
                    f"{w['word']} {read.ARROW[d]}: low {b['l']:,.1f} <= +1σ {vw + sg:,.1f}, close > +1σ, 3m delta {b['delta']:+d}")})
        if now_label is None:
            now_label = "TRIGGERED" if pos else ("ARMED" if armed else "NOT_ARMED") if d else ("FADE" if w and w["word"] == "RANGE" else "NONE")
        if now_label != label:
            label, since = now_label, t
    r = rows[-1]
    word_now, d_now = r["word"], (r["dir"] if r["word"] in ("TREND", "LEAN") else 0)
    vw, sg = last["vwap"], last["sig"]
    if not pos and not d_now:
        if word_now == "RANGE":
            return dict(base, ok=True, d=0, word="RANGE", state="FADE", since=since if label == "FADE" else None,
                        zones=[{"side": "buy", "lo": round(vw - 3 * sg, 1), "hi": round(vw - 2 * sg, 1)},
                               {"side": "sell", "lo": round(vw + 2 * sg, 1), "hi": round(vw + 3 * sg, 1)}],
                        t1={"fut": round(vw, 1), "name": "VWAP"}, kill=None, trigger=None, rows=E[-8:],
                        why="her zone machine's own stop"), None
        return None, f"READ {word_now} · zone nahi"
    d = pos["d"] if pos else d_now
    word = pos["word"] if pos else word_now
    # the bar that stopped / paid T2 shows it; the next bar is NOT_ARMED (or ARMED again at the 1.5 sigma re-arm)
    state = label if label in ("STOPPED", "T2") else "TRIGGERED" if pos else ("ARMED" if armed else "NOT_ARMED")
    sell = d < 0
    return dict(base, ok=True, d=d, word=word, side="SELL" if sell else "BUY", state=state,
                since=since if label == state else None,
                zone={"lo": round(vw - sg, 1), "hi": round(vw, 1), "name": "SELL −1σ…VWAP"} if sell
                else {"lo": round(vw, 1), "hi": round(vw + sg, 1), "name": "BUY VWAP…+1σ"},
                trigger_rule="3m high ≥ −1σ, close < −1σ, Δ < 0" if sell else "3m low ≤ +1σ, close > +1σ, Δ > 0",
                kill={"fut": round(vw, 1), "name": "VWAP", "rule": "3m close > VWAP" if sell else "3m close < VWAP"},
                t1={"fut": round(vw + d * 2 * sg, 1), "name": "−2σ" if sell else "+2σ"},
                t2=pos["t2"] if pos else _t2(vw, sg, d, _wall(r, basis)),
                trigger={"t": pos["t"], "px": pos["px"], "delta": pos["delta"]} if pos else None,
                size="chhota" if word == "LEAN" else None, rows=E[-8:],
                why="15:00 ke baad naya trade nahi" if now >= LATE_S else None), None


# ---- writers ------------------------------------------------------------------------------------------------------

def writers_part(X, now, ref30, tl):
    """ATM +/- 2 at the chain row at `now`: the 30-min CE / PE OI change (thousands), its rank against
    rank_ref.writers30 and `fresh` (an add ranked >= p90), with the READ's nine-strike writers and the QUIT events."""
    rows = tl.get("rows") or []
    w = rows[-1]["writers"] if rows else {}
    cls = w.get("cls")
    out = {"ok": True, "t": None, "atm": None, "step": X.get("step"), "unit": "k", "strikes": [],
           "n_ref": (ref30 or {}).get("n"), "A": w.get("A"), "cls": cls, "ce": w.get("ce"), "pe": w.get("pe"),
           "absent": "PE" if cls == "CALL" else "CE" if cls == "PUT" else None,
           "quits": [{"t": e["t"], "k": e["k"], "side": e["side"], "text": e["text"]}
                     for e in tl.get("events") or () if e.get("kind") == "QUIT"],
           "why": None, "tag": "M"}
    ts = X.get("t") or []
    t = now if now is not None else (ts[-1] if ts else None)
    if t is None or not ts:
        return dict(out, ok=False, why=CC + "no chain row recorded yet today")
    if t - 1800 < OPEN_S:
        return dict(out, t=hm(t), why="30-min window opens 09:45")
    i, j = bisect.bisect_right(ts, t) - 1, bisect.bisect_right(ts, t - 1800) - 1
    if i < 0 or j < 0 or t - ts[i] > 120 or t - 1800 - ts[j] > 120:
        return dict(out, ok=False, t=hm(t), why=CC + f"chain row missing near {hm(t)}")
    step = X.get("step") or 50
    atm = math.floor(X["spot"][i] / step + 0.5) * step
    pos = {k: n for n, k in enumerate(X["ks"])}
    strikes = []
    for k in (atm + step * n for n in range(-2, 3)):
        jj = pos.get(k)
        row = {"k": int(k)}
        for leg in ("ce", "pe"):
            a = X[leg + "_oi"][i][jj] if jj is not None else None
            b = X[leg + "_oi"][j][jj] if jj is not None else None
            ch = None if a is None or b is None else a - b
            rk = rank(ref30, ch)
            row[leg + "30"], row[leg + "_rank"] = ch, rk
            row[leg + "_fresh"] = None if ch is None or rk is None else (ch > 0 and rk >= 90)
        strikes.append(row)
    why = None if ref30 else "no writers30 reference: ranks ?"
    return dict(out, t=hm(t), atm=int(atm), step=step, strikes=strikes, why=why)


def ux_part(ux_bars, now_ms=None):
    """The last 6 Upstox 5-min bars closed by now_ms (None = the recorded day's end): {t (bar start, ms), delta, vol}."""
    bs = [b for b in ux_bars or () if isinstance(b, dict) and isinstance(b.get("t"), (int, float))
          and (now_ms is None or b["t"] + 300000 <= now_ms)]
    bs.sort(key=lambda b: b["t"])
    out = [{"t": int(b["t"]), "delta": b.get("delta"), "vol": b.get("vol")} for b in bs[-6:]]
    return {"bars": out, "why": None if out else CC + "no Upstox 5-min bar closed yet", "tag": "M"}


# ---- the whole v2 part --------------------------------------------------------------------------------------------

def compose(X, tl, card, ux_bars, ref, now, now_ms, dte_, bf_note=None, expr=None, day=None):
    """Everything the v2 frame adds, from one index's arrays at `now` (sec of day; None = the recorded day's end).
    `day` lets the basis band ask the options (parity_basis); without it the band is the carry model alone."""
    out = {}
    basis = (basis_band(card.get("spot"), card.get("basis"), dte_, parity_basis(X, now, day) if day else None)
             if card.get("ok") else None)
    if card.get("ok"):
        out["read"], out["read_why"] = read_part(card, tl, basis, bf_note, expr), None
        ts = X.get("t") or []
        if now is not None and ts and now - ts[-1] > 120:      # read.py holds the last row it has; say how old it is
            out["read"]["blind"].append(f"CHAIN: last row {hm(ts[-1])}, {(now - ts[-1]) // 60} min before {hm(now)} [M]")
    else:
        out["read"], out["read_why"] = None, card.get("why") or CC + "no READ yet"
    out["plan"], out["plan_why"] = plan(bars3(X.get("bars"), X.get("lot"), now), tl.get("rows") or [], basis, now)
    out["writers"] = writers_part(X, now, (ref or {}).get("writers30"), tl)
    out["ux_flow"] = ux_part(ux_bars, now_ms)
    return out
