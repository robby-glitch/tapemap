"""holdshadow.py -- three HOLD v3 CANDIDATE lines beside HOLD v2 in the hold window (docs/live/NOTEPAD.md, "HOLD v3
candidates"). SHADOW: display and a forward log only, NOT rules. HOLD v2 (§1m), the engine's HOLD / FOLD and every locked
setup are untouched; a line becomes a rule only by beating HOLD v2 against the pass bar written in the NOTEPAD, and only
on her signature.

Each line is HOLD v2 PLUS ONE extra exit, so its exit pairs with HOLD v2's on the same trade (paired dR, R on HOLD v2's
own risk |line0 - E|):
  CHOP    on a CHOP / PIN-typed day (§1o, the DECODE log's meter at that minute) a FADE -- her entry on the far side of
          the 5-min futures VWAP from her direction -- takes its profit at VWAP: the first 1-min bar after entry that
          touches VWAP while the day reads CHOP / PIN exits at that VWAP. No RIDE convert (NOTEPAD A38).
  POP     a trade bought into covering (a payers' front UNWINDING at entry: CE for a long, PE for a short) folds at the
          first 3-min close where the covering has stopped (no payers' front UNWINDING) AND the tape is exhausted at a
          fresh extreme in her direction (VALIDATE rev 3 §1: FRESH, and EXHAUST / ABSORB / effort >= 2x at a high, each
          within 15 min). Exit at that close. SENSEX: could not check (its tape is patla).
  EFFORT  a long folds at the first DECODE close reading an expensive fresh HIGH (>= 2x); a short HOLDS past HOLD v2's
          exit while the latest fresh LOW is cheap (<= 0.5x, within 15 min) and exits at the first close where it no
          longer is (or 15:20). The two mirrors failed Fable's audit and are never used. NIFTY [I tested], BANKNIFTY [I,
          untested], SENSEX could not check.
A DECODE close c is read from minute c + 1 (the server's grace). Pure: no I/O, no clock; causal (minute m reads only
bars, chain minutes and closes available by then). A line that does not apply says so and pairs as `applies` False."""
from __future__ import annotations

import bisect

import confluence
import effort
import faded
import fronts
import hold2

REV = "holdshadow-1 (NOTEPAD HOLD v3 candidates, 2026-10-23)"
LINES = ("CHOP", "POP", "EFFORT")
CHIP = {"CHOP": "CHOP din: VWAP pe munafa", "POP": "covering ruki: pop khatam",
        "EFFORT+": "high mehenga: nikal lo", "EFFORT-": "low sasta: ruke raho"}
W15 = 15                        # minutes: every tape read is this fresh (VALIDATE rev 3 §1)
HI_X, LO_X = effort.HI, effort.LO
THIN = ("SENSEX",)
MARK, OPEN_M = hold2.MARK, hold2.OPEN_M
hm = hold2.hm


def _mm(t):
    return None if not t else int(t[:2]) * 60 + int(t[3:5])


def dec_rows(rows, idx):
    """{close minute: block} from data/decode/decode_<day>.jsonl rows for idx (each row is a block plus day / idx / T)."""
    return {_mm(r["T"]): r for r in rows or () if isinstance(r, dict) and r.get("idx") == idx and r.get("T")}


def _dec_at(dec, m):
    """The latest DECODE close readable at minute m (close + 1 <= m) -> (close, block) or (None, None)."""
    ks = sorted(k for k in dec if k + 1 <= m)
    return (ks[-1], dec[ks[-1]]) if ks else (None, None)


def _r(d, E, risk, px):
    return None if px is None or not risk else round(d * (px - E) / risk, 4)


def _close_at(ones, m):
    """The futures close of the 1-min bar ending at minute m (its start m - 1), else the last bar before."""
    c = None
    for b in ones:
        if b["s"] // 60 <= m - 1:
            c = b["c"]
    return c


def _payers(d, chain, m):
    """The payers' fronts (fronts.read's top-2 on CE for a long, PE for a short) at minute m's last closed minute."""
    at = hm(m - 1)
    cut = fronts.cut(chain[0], at)
    if not cut or fronts.stale(cut, at):
        return None
    side = "CE" if d > 0 else "PE"
    P = [f for f in fronts.read(cut, confluence._upto(chain[1], at)) if f.get("side") == side]
    return {"side": side, "k": [f["k"] for f in P], "states": [f["state"] for f in P]} if P else None


def _spot(chain):
    return {_mm(t): r["spot"] for t, r in (chain[0] or {}).items() if isinstance(r, dict) and r.get("spot") is not None}


def fresh(d, spot, m, step):
    """VALIDATE rev 3's FRESH at minute m: spot within 1/4 step of the 30-min running extreme in direction d, set <= 5
    min ago (effort.running_extreme, Fable's fallback rule)."""
    if m not in spot or not step:
        return False
    H, mH, L, mL = effort.running_extreme(spot, m)
    tol = effort.TOL_STEPS * step
    if d > 0:
        return H is not None and spot[m] >= H - tol and m - mH <= effort.FRESH
    return L is not None and spot[m] <= L + tol and m - mL <= effort.FRESH


def exhausted(d, blk, m, absorbed):
    """The tape exhausted at minute m (VALIDATE rev 3 §2 #10): EXHAUST (decode.exhaust on a leg her way), ABSORB (her
    side's aggression absorbed, the fold engine's mark), or a long's expensive high (effort >= 2x) -- each within 15
    min. -> the names that fired ([] none)."""
    out = []
    ex = (blk or {}).get("exhaust")
    if ex and ex.get("d") == d and (_mm(ex.get("close")) or -999) >= m - W15:
        out.append(f"EXHAUST {ex.get('bar') or ex.get('close')}")
    if any(s == d and m - W15 < mm <= m for mm, s in absorbed or ()):
        out.append("ABSORB")
    e = (blk or {}).get("effort") or {}
    if d > 0 and e.get("at") == "HIGH" and (e.get("x") or 0) >= HI_X and (_mm(e.get("t")) or -999) >= m - W15:
        out.append(f"effort {e['x']:.1f}x")
    return out


def chop_line(d, E, start, end, ones, bars5, dec):
    """CHOP's own exit (or why it does not apply / is still open)."""
    vw = faded.vwaps(bars5 or [])
    cl = [b["s"] // 60 + 5 for b in bars5 or []]

    def vat(m):
        j = bisect.bisect_right(cl, m) - 1
        return vw[j] if j >= 0 else None
    v0 = vat(start)
    if v0 is None:
        return {"applies": None, "how": "cnc", "why": "no 5-min VWAP at her entry yet"}
    if d * (v0 - E) <= 0:
        return {"applies": False, "how": "n/a", "why": f"fade nahi · entry VWAP ke {'upar' if E > v0 else 'neeche'}",
                "vwap": round(v0, 1)}
    unread = []
    for b in ones:
        mm = b["s"] // 60
        if mm < start or mm + 1 > end or mm >= MARK:
            continue
        v = vat(mm)
        if v is None or not (b["h"] >= v if d > 0 else b["l"] <= v):
            continue
        typ = ((_dec_at(dec, mm)[1] or {}).get("onesided") or {}).get("type")
        if typ is None:
            unread.append(hm(mm))
        elif typ in ("CHOP", "PIN"):
            return {"applies": True, "how": "vwap", "t": hm(mm + 1), "px": round(v, 2), "typ": typ}
    _, blk = _dec_at(dec, end)
    return {"applies": True, "how": "open", "vwap": None if vat(end) is None else round(vat(end), 1),
            "typ": ((blk or {}).get("onesided") or {}).get("type"), "unread": unread}


def pop_line(d, start, end, ones, chain, dec, absorbed, idx, step, cache):
    """POP's own exit. `cache` keeps each 3-min close's read once, a minute after it (hold2.live's rule)."""
    if idx in THIN:
        return {"applies": None, "how": "cnc", "why": f"{idx} tape patla — check nahi"}
    p0 = _payers(d, chain, start)
    if p0 is None:
        return {"applies": None, "how": "cnc", "why": "no payers' front read at her entry"}
    if fronts.UNWINDING not in p0["states"]:
        return {"applies": False, "how": "n/a", "why": f"covering me nahi khareeda · {p0['side']} {'/'.join(p0['states']).lower()}"}
    spot = _spot(chain)
    k = OPEN_M + ((start - OPEN_M) // 3 + 1) * 3
    while k <= min(end - 1, MARK):
        if k not in cache:
            pay = _payers(d, chain, k)
            stopped = bool(pay) and fronts.UNWINDING not in pay["states"]
            ex = exhausted(d, _dec_at(dec, k)[1], k, absorbed)
            cache[k] = {"stopped": stopped, "fresh": fresh(d, spot, k - 1, step), "ex": ex,
                        "pay": None if pay is None else dict(zip(pay["k"], pay["states"]))}
        r = cache[k]
        if r["stopped"] and r["fresh"] and r["ex"]:
            return {"applies": True, "how": "pop", "t": hm(k), "px": _close_at(ones, k), "ex": r["ex"]}
        k += 3
    last = cache[max(cache)] if cache else None
    return {"applies": True, "how": "open", "pay0": dict(zip(p0["k"], p0["states"])), "last": last}


def _cheap(dec, m):
    e = (_dec_at(dec, m)[1] or {}).get("effort") or {}
    return e.get("at") == "LOW" and e.get("x") is not None and e["x"] <= LO_X and (_mm(e.get("t")) or -999) >= m - W15


def effort_line(d, start, end, ones, dec, v2, idx):
    """EFFORT's own exit: a long's first expensive fresh high; a short's HOLD v2 exit deferred while the low is cheap."""
    if idx not in effort.STEP:
        return {"applies": None, "how": "cnc", "why": f"{idx} fut patla — check nahi"}
    if d > 0:
        for c in sorted(dec):
            if c < start or c + 1 > end - 1 or c + 1 > MARK:
                continue
            e = dec[c].get("effort") or {}
            if e.get("at") == "HIGH" and (e.get("x") or 0) >= HI_X and (_mm(e.get("t")) or -999) >= c - W15:
                return {"applies": True, "how": "effort", "t": hm(c + 1), "px": _close_at(ones, c + 1), "x": e["x"]}
        e = (_dec_at(dec, end)[1] or {}).get("effort") or {}
        return {"applies": True, "how": "open", "x": e.get("x"), "at": e.get("at")}
    if not v2 or v2.get("how") in (None, "open"):
        return {"applies": True, "how": "open", "cheap": _cheap(dec, end)}
    t2 = _mm(v2["t"])
    if not _cheap(dec, t2):
        return {"applies": True, "how": "v2", "cheap": False}
    for m in range(t2 + 1, min(end - 1, MARK) + 1):
        if m - 1 in dec and not _cheap(dec, m):               # a new close became readable and the low is not cheap
            return {"applies": True, "how": "effort", "t": hm(m), "px": _close_at(ones, m), "deferred_from": v2["t"]}
    if end - 1 >= MARK:
        return {"applies": True, "how": "mark", "t": hm(MARK), "px": _close_at(ones, MARK), "deferred_from": v2["t"]}
    return {"applies": True, "how": "open", "cheap": True, "deferred_from": v2["t"]}


def _pair(name, own, d, E, risk, v2):
    """One line's exit beside HOLD v2's: its own when it fires first (EFFORT's short: after), else HOLD v2's."""
    v2f = bool(v2) and v2.get("how") not in (None, "open")
    chip = CHIP.get(name) or CHIP[name + ("+" if d > 0 else "-")]
    out = {"line": name, "d": d, "chip": chip, "applies": own.get("applies"), "why": own.get("why"), "v2": v2, "own": own}
    if own["how"] in ("vwap", "pop", "effort", "mark"):
        later = name != "EFFORT" or d > 0
        if v2f and later and _mm(v2["t"]) < _mm(own["t"]):
            out.update(how="v2", t=v2["t"], px=v2.get("px"), R=v2.get("R"))
        else:
            out.update(how=own["how"], t=own["t"], px=own["px"], R=_r(d, E, risk, own["px"]))
    elif v2f and own["how"] != "open":                       # n/a, cnc, v2: the line is HOLD v2's exit
        out.update(how="v2", t=v2["t"], px=v2.get("px"), R=v2.get("R"))
    elif v2f and not (name == "EFFORT" and d < 0):           # open, but HOLD v2 already out: the line can no longer fire
        out.update(how="v2", t=v2["t"], px=v2.get("px"), R=v2.get("R"))
    else:
        out.update(how="open", t=None, px=None, R=None)
    out["final"] = out["how"] != "open" and v2f
    out["dR"] = (None if not out["final"] or out["R"] is None or v2.get("R") is None
                 else round(out["R"] - v2["R"], 4))
    return out


def text(L, basis=None):
    """The line in the window's words: '<name> · <state or exit> · <chip>' -- terse, every level fut|spot."""
    own, name = L["own"], L["line"]

    def lvl(x):
        return f"{x:,.0f}f" + ("" if basis is None else f"|{x - basis:,.0f}s")
    if L["how"] not in ("open", "v2"):
        R = "" if L["R"] is None else f" · {L['R']:+.2f}R"
        return f"{name} · out {L['t']} @{'?' if L['px'] is None else lvl(L['px'])}{R} · {L['chip']}"
    if L["applies"] is False or own["how"] == "cnc":
        return f"{name} · {own.get('why') or 'lagu nahi'}" + (f" · = HOLD v2 {L['t']}" if L["how"] == "v2" else "")
    if L["how"] == "v2":
        return f"{name} · nahi chala · = HOLD v2 out {L['t']}"
    if name == "CHOP":
        v = own.get("vwap")
        return f"{name} · VWAP {'?' if v is None else lvl(v)} · din {own.get('typ') or '?'} · {L['chip']}"
    if name == "POP":
        last = own.get("last") or {}
        return (f"{name} · covering {'ruki' if last.get('stopped') else 'jaari'} · tape "
                f"{'thaka' if last.get('ex') else 'thaka nahi'} · {L['chip']}")
    if L["d"] > 0:
        x = own.get("x")
        return f"{name} · high {'?' if x is None else f'{x:.1f}×'} din ka · 2× pe nikal"
    if own.get("deferred_from"):
        return f"{name} · low sasta · v2 {own['deferred_from']} ke baad bhi ruke"
    return f"{name} · low {'sasta' if own.get('cheap') else 'sasta nahi'} · {L['chip']}"


def lines(d, E, line0, start, end, ones, bars5, chain, dec, absorbed, v2, idx, step, cache, basis=None):
    """The three lines for her open trade: [{line, chip, applies, how, t, px, R, v2, dR, final, own, text}]."""
    risk = abs(line0 - E) if line0 is not None and E is not None else None
    own = {"CHOP": chop_line(d, E, start, end, ones, bars5, dec),
           "POP": pop_line(d, start, end, ones, chain, dec, absorbed, idx, step, cache.setdefault("pop", {})),
           "EFFORT": effort_line(d, start, end, ones, dec, v2, idx)}
    out = []
    for n in LINES:
        L = _pair(n, own[n], d, E, risk, v2)
        L["text"] = text(L, basis)
        out.append(L)
    return out


def _step(chain):
    """The chain's strike step, from its last minute's strikes (NIFTY 50, BANKNIFTY / SENSEX 100)."""
    ms = sorted(chain[0] or {})
    ks = sorted(float(k) for k in ((chain[0][ms[-1]] or {}).get("k") or {})) if ms else []
    gaps = [b - a for a, b in zip(ks, ks[1:]) if b > a]
    return min(gaps) if gaps else None


def live(tr, view, h2, now_m, bars1, chain_rows, bars5, dec, cache):
    """The three lines from the live server's memory (server._hold2_run: the same inputs HOLD v2 reads) plus the DECODE
    log's blocks for the index (`dec` = dec_rows(...)) and the fold view's "absorbed" events. None until HOLD v2 has a
    line (the lines pair with its exit)."""
    d, E = view.get("d"), view.get("E")
    if not h2 or not h2.get("ok") or d not in (1, -1) or E is None:
        return None
    h, mi = (int(x) for x in str(tr["t0"]).split(":")[:2])
    ones = [{"s": (int(b["t"]) // 1000 + 19800) % 86400, "h": b["h"], "l": b["l"], "c": b["c"]}
            for b in bars1 or () if b.get("h") is not None and b.get("t") is not None]
    chain = confluence.chain_grid(chain_rows)
    absorbed = [(_mm(e["ts"]), e.get("side")) for e in view.get("events") or ()
                if e.get("kind") == "absorbed" and isinstance(e.get("ts"), str)]
    return lines(d, E, h2.get("line0"), h * 60 + mi + 1, now_m, ones, bars5, chain, dec, absorbed, h2.get("v2_exit"),
                 tr["idx"], _step(chain), cache, (view.get("units") or {}).get("basis_ix"))


def row(day, tr, L, now):
    """The forward log's row for one line (write-once per trade and line): its exit beside HOLD v2's, paired."""
    v2 = L.get("v2") or {}
    return {"day": day, "id": tr["id"], "idx": tr["idx"], "line": L["line"], "rev": REV, "d": L["d"],
            "applies": L["applies"], "how": L["how"], "sh": {"t": L["t"], "px": L["px"], "R": L["R"]},
            "v2": {"how": v2.get("how"), "t": v2.get("t"), "px": v2.get("px"), "R": v2.get("R")}, "dR": L["dR"],
            "final": L["final"], "why": L.get("why"), "validate": tr.get("validate"), "at": now}
