# -*- coding: utf-8 -*-
"""EXECUTE THE EDGE — her zone, executed (spec docs/superpowers/specs/2026-11-13-execute-edge-design.md, approved 14 Nov 2026).

day_state() is pure: the day's exchange 1-min futures candles (+ Dext delta, yesterday's candles) -> the six-state line, the
trigger ticket and three plan lines over the same zone triggers:
  PLAN A  every trigger; any opposite trigger ends the trade and is taken (the edge walk, look_edge_walk FLIP)
  PLAN B  her rules: four checks (GAP, TREND, LEG PAID, FLOW); a weak opposite signal neither ends the trade nor is taken
  PLAN C  PLAN B + CAREFUL FLIP (a trade in profit is ended only by a valid opposite signal with room >= 1 sigma); logged only
for_frame() and append_log() are the two I/O adapters at the bottom. Display only; never an order (house rule 10).
"""
import datetime as dt
import json
import os

import band_rotation as br
import ruler

OPEN, LAST = 9 * 60 + 15, 15 * 60   # flat by 15:00 (her practice)
LOCK_R = 2.0                         # LEG PAID: a close at 2x its own stop (hold2.LOCK_R, §1m)
TREND_MIN = 120                      # TREND: VWAP untouched this many minutes (A313 / A320; alone it moves few trades: Fable A337)
LIVE_LAG = 5                         # a log row first written within 5 min of its own minute is "live", later "backfill" (one pass a minute)
ROOM_S = 1.0                         # PLAN C: room from VWAP in her sigma (her ROOM read, A315 / A329)
NEAR = 2                             # OI: the other side's writers at ATM +- 2 strikes (A332)


def M(t):
    return int(t[:2]) * 60 + int(t[3:5])


def HM(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def prev_weekday(day):
    d = dt.date.fromisoformat(day) - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d.isoformat()


def last_tuesday(y, m):
    d = (dt.date(y, m, 28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    while d.weekday() != 1:
        d -= dt.timedelta(days=1)
    return d


def contract_changed(day, prev_day):
    """True when a monthly NIFTY futures expiry (the month's last Tuesday: 25 Aug, 29 Sep, 27 Oct 2026, A318) fell on prev_day
    or after it and before day: yesterday's candles are another contract."""
    p, d = dt.date.fromisoformat(prev_day), dt.date.fromisoformat(day)
    return p <= last_tuesday(p.year, p.month) < d


def gap(ones, prev_ones, changed):
    """GAP (A331): ok True = opened inside yesterday's futures high-low, False = outside (no fades), None = could not check."""
    if not prev_ones:
        return {"ok": None, "text": "could not check: no candles for the previous weekday"}
    if changed:
        return {"ok": None, "text": "could not check: a new futures contract since yesterday"}
    o = next((b["o"] for b in ones if b["t"] == "09:15"), None)
    if o is None:
        return {"ok": None, "text": "could not check: no 09:15 bar"}
    pv = [b for b in prev_ones if b["t"] <= "15:29"]
    hi, lo = max(b["h"] for b in pv), min(b["l"] for b in pv)
    base = {"open": o, "hi": hi, "lo": lo}
    if o > hi:
        return dict(base, ok=False, text=f"opened above yesterday's high {hi:,.0f}f")
    if o < lo:
        return dict(base, ok=False, text=f"opened below yesterday's low {lo:,.0f}f")
    return dict(base, ok=True, text="opened inside yesterday's range")


def triggers(blist):
    """Her zone on her 3-min bands by the machine's own loop (look_cause_effect.replay, lifted): (signals, armed).
    armed = {side: {first, ext, band}} for an arm still open at the last bar."""
    out, armed = [], {}
    for side, band in (("BUY", "d2"), ("SELL", "u2")):
        cur, rows = [], br.run_states(blist, stop_pts=br.OPERATOR_STOP_PTS, side=side, band=band, span=3)
        for s in rows:
            a = s.get("arm")
            if a:
                if not a["rearm"]:
                    cur = []
                cur.append((s["t"], a["extreme"], s["level"]))
            if s.get("entry") and cur:
                ref = cur[-1]                                   # the reference bar: the setup's last new extreme
                out.append({"t": s["t"], "side": side, "px": blist[s["i"]]["c"], "level": ref[2], "ext": ref[1],
                            "xb": M(ref[0]), "first": cur[0][0], "narm": len(cur)})
                cur = []
        if cur and rows and rows[-1].get("state") == "ARMED":
            armed[side] = {"first": cur[0][0], "ext": cur[-1][1], "band": band}
    return sorted(out, key=lambda r: r["t"]), armed


def vwap_untouched(blist, t0):
    """TREND: minutes since a 3-min bar from 09:30 on last held VWAP, up to the trigger bar (look_cause_effect.so_far 'vw')."""
    first = [b for b in blist if b["t"] < "09:30"]
    upto = [b for b in blist if "09:30" <= b["t"] <= t0]
    if len(first) < 5 or not upto:
        return None
    return next((3 * k for k, b in enumerate(reversed(upto)) if b.get("vwap") is not None and b["l"] <= b["vwap"] <= b["h"]),
                3 * len(upto))


def flow_sum(delta, e):
    """FLOW: Dext delta summed from the bar after the extreme to the trigger close; None = no minute readable."""
    mins = [HM(m) for m in range(e["xb"] + 3, M(e["t"]) + 3) if delta.get(HM(m)) is not None]
    return sum(delta[t] for t in mins) if mins else None


def _signals(blist, T, delta, gp):
    """Each trigger with what was known at its close: try number, risk, room (sigma), FLOW, TREND, GAP."""
    bars, n, out = {b["t"]: b for b in blist}, {"BUY": 0, "SELL": 0}, []
    for e in T:
        S = -1 if e["side"] == "SELL" else 1
        n[e["side"]] += 1
        tb = bars.get(e["t"]) or {}
        sg = (tb["u1"] - tb["vwap"]) if tb.get("u1") and tb.get("vwap") is not None else None
        fs = flow_sum(delta, e) if delta else None
        vw = vwap_untouched(blist, e["t"])
        chk = {"GAP": gp["ok"] is False, "TREND": vw is not None and vw >= TREND_MIN, "FLOW": fs is not None and S * fs <= 0}
        out.append(dict(e, S=S, n=n[e["side"]], risk=abs(e["ext"] - e["px"]), z=(S * (tb["vwap"] - e["px"]) / sg) if sg else None,
                        fs=fs, vw=vw, chk=chk, bad=any(chk.values())))
    return out


def _walk(ones, sig, plan, upto_m=None):
    """One plan over the day's signals on the 1-min candles up to upto_m (None = the whole day, flat at 15:00).
    A: any opposite signal ends the trade and is taken. B: a weak signal (any check, or LEG PAID read before the flip) neither
    ends the trade nor is taken; LEG PAID is read again after the flip for the entry. C: B, and a trade in profit is ended
    only by a signal with room >= ROOM_S. acts[(t, side)] = (TAKEN | SKIP | HOLD | IN TRADE, the LEG state it was read on)."""
    ix = {b["t"]: i for i, b in enumerate(ones)}
    ent = {}
    for e in sig:
        ie = ix.get(HM(M(e["t"]) + 2))
        if ie is not None and M(e["t"]) + 2 < LAST:
            ent.setdefault(ie, []).append(e)
    st, lastj = {"pos": None, "won": None, "trades": [], "acts": {}}, None

    def close(j, px, why):
        p = st["pos"]
        x = {"t": p["t"], "side": p["side"], "px": p["px"], "x": ones[j]["t"], "why": why, "pts": p["S"] * (px - p["px"]),
             "risk": p["risk"]}
        st["trades"].append(x)
        if plan != "A" and st["won"] is None and x["pts"] >= LOCK_R * p["risk"]:
            st["won"] = p["side"]
        st["pos"] = None

    for j, b in enumerate(ones):
        m = M(b["t"])
        if m > LAST or (upto_m is not None and m > upto_m):
            break
        hi, lo, c = b.get("h"), b.get("l"), b.get("c")
        if c is not None:
            lastj = j
        p = st["pos"]
        if p and hi is not None and lo is not None:
            if (p["S"] < 0 and hi > p["stop"]) or (p["S"] > 0 and lo < p["stop"]):
                close(j, p["stop"], "STOP")
            elif m >= LAST and c is not None:
                close(j, c, "15:00")
        for e in ent.get(j, []):
            S, key, p = e["S"], (e["t"], e["side"]), st["pos"]
            weak = plan != "A" and (e["bad"] or (st["won"] is not None and e["side"] != st["won"]))
            if p and p["S"] == -S and c is not None:
                careful = plan == "C" and p["S"] * (c - p["px"]) > 0 and e["z"] is not None and e["z"] < ROOM_S
                if weak or careful:
                    st["acts"][key] = ("HOLD", st["won"])
                    continue
                close(j, c, "FLIP")
            leg = plan != "A" and st["won"] is not None and e["side"] != st["won"]
            if st["pos"] is None and not weak and not leg:
                st["pos"] = {"t": e["t"], "side": e["side"], "S": S, "px": e["px"], "stop": e["ext"], "risk": abs(e["ext"] - e["px"])}
                st["acts"][key] = ("TAKEN", st["won"])
            elif st["pos"] is None:
                st["acts"][key] = ("SKIP", st["won"])
            else:
                st["acts"].setdefault(key, ("IN TRADE", st["won"]))
    if st["pos"] and lastj is not None and (upto_m is None or upto_m >= LAST):
        close(lastj, ones[lastj]["c"], "15:00")
    return st


def _live_leg(ones, ix, sig, e):
    """LIVE LEG (A328, information only): earlier opposite signals whose stop is not hit by e's entry minute, points then."""
    ie, out = ix.get(HM(M(e["t"]) + 2)), []
    if ie is None:
        return out
    for o in sig:
        if M(o["t"]) >= M(e["t"]):
            break
        io = ix.get(HM(M(o["t"]) + 2))
        if o["side"] == e["side"] or io is None:
            continue
        hit = any((o["S"] < 0 and ones[j]["h"] > o["ext"]) or (o["S"] > 0 and ones[j]["l"] < o["ext"]) for j in range(io + 1, ie + 1))
        if not hit:
            out.append(f"{o['side']} {o['t']} alive {o['S'] * (ones[ie]['c'] - o['px']):+.0f}")
    return out


def _other_side(ladder, spot, pos, now_t, step=50):
    """OI in a trade (A332, information only): the other side's writers at ATM +- NEAR strikes, entry minute -> now."""
    if not ladder or not spot:
        return None
    t0 = HM(M(pos["t"]) + 2)
    sp, A, B = spot.get(t0), ladder.get(t0), ladder.get(now_t)
    if sp is None or not A or not B:
        return None
    side, atm = ("pe" if pos["S"] < 0 else "ce"), round(sp / step) * step
    ks, a_, b_ = {atm + k * step for k in range(-NEAR, NEAR + 1)}, A.get(side) or {}, B.get(side) or {}
    ch = [b_[k] - a for k, a in a_.items() if a is not None and b_.get(k) is not None and int(float(k)) in ks]
    return sum(ch) if ch else None


def _sync(peers, pos, upto_m):
    """SYNC (A334, information only, a hold reason): from 30 min after the entry, have BANKNIFTY and SENSEX futures moved her
    way since the entry? None before 30 minutes."""
    t0 = M(pos["t"]) + 2
    if peers is None or upto_m < t0 + 30:
        return None
    with_ = 0
    for name in ("BANKNIFTY", "SENSEX"):
        c = [(b["t"], b["c"]) for b in peers.get(name) or () if b.get("c") is not None]
        a = next((px for t, px in reversed(c) if M(t) <= t0), None)
        b = next((px for t, px in reversed(c) if M(t) <= upto_m), None)
        if a is None or b is None:
            return f"SYNC could not check: no {name} candles"
        with_ += pos["S"] * (b - a) > 0
    return {2: "ALL 3 WITH YOU · hold", 1: "1 of 2 with you"}.get(with_, "NIFTY alone")


def _ticket(e, gp, act, live, held, closed=None):
    """The trigger ticket: the head, the four checks in the order they become known, LIVE LEG, then one word line (led by
    EXIT <side> <pts> when this signal ended the open trade)."""
    S, opp = e["S"], ("BUY" if e["S"] < 0 else "SELL")
    who, ex = ("sellers", "top") if S < 0 else ("buyers", "bottom")
    word, won = act or ("?", None)
    mark = lambda ok: " ✓" if ok else " ✗"                                  # noqa: E731
    legbad = won is not None and e["side"] != won
    lines = [f"{e['side']} {e['t']} · try {e['n']} · entry {e['px']:,.0f}f · stop {e['ext']:,.0f}f ({e['risk']:.0f})"
             + (f" · room {e['z']:.1f}σ" if e["z"] is not None else ""),
             "GAP    " + gp["text"] + ("" if gp["ok"] is None else mark(gp["ok"])),
             "TREND  could not check: bands forming" if e["vw"] is None else
             f"TREND  VWAP untouched {e['vw']} min ✗" if e["chk"]["TREND"] else f"TREND  VWAP touched {e['vw']} min ago ✓",
             "LEG    no 2R win today ✓" if won is None else f"LEG    2R win today was a {won}" + mark(not legbad),
             "FLOW   could not check: no Dext delta" if e["fs"] is None else
             f"FLOW   {'no ' if e['chk']['FLOW'] else ''}{who} since the {ex} {e['fs']:+,.0f}" + mark(not e["chk"]["FLOW"]),
             "LIVE LEG  " + ("; ".join(live) if live else "none")]
    why = " ".join(f"{k} ✗" for k in [k for k, v in e["chk"].items() if v] + (["LEG"] if legbad else []))
    lines.append((f"EXIT {closed['side']} {closed['pts']:+.0f} · " if closed else "")
                 + {"TAKEN": f"TAKE · hold till a valid {opp}, the stop or 15:00",
                    "HOLD": (f"SKIP ({why}) · HOLD {held}" if why else f"NOT AT THE BAND · HOLD {held}"),
                    "SKIP": f"SKIP ({why}) · wait",
                    "IN TRADE": f"IN A {e['side']} ALREADY · HOLD"}.get(word, word))
    return lines


def _mark(e, gp, act, closed):
    """The plan's word on one signal, for the Jarvis page's zone mark (her one voice, 14 Nov): word, a short label, the
    ticket's word line, the four checks (✓ / ✗ / ? when it could not be read)."""
    word, won = act or ("—", None)
    legbad = won is not None and e["side"] != won
    q = lambda v, bad: "?" if v is None else ("✗" if bad else "✓")                                   # noqa: E731
    checks = [f"GAP {q(gp['ok'], gp['ok'] is False)}", f"TREND {q(e['vw'], e['chk']['TREND'])}",
              f"LEG {'✗' if legbad else '✓'}", f"FLOW {q(e['fs'], e['chk']['FLOW'])}"]
    why, held = " ".join(c for c in checks if c.endswith("✗")), ("SELL" if e["side"] == "BUY" else "BUY")
    w = {"TAKEN": "TAKE", "SKIP": "SKIP", "HOLD": "HOLD", "IN TRADE": "IN TRADE"}.get(word, "PLAN ?")
    label = {"TAKE": "TAKE", "SKIP": f"SKIP · {why}", "HOLD": f"HOLD {held} · {why}", "IN TRADE": f"IN A {e['side']} ALREADY"}.get(w, w)
    if closed:
        label = f"EXIT {closed['side']} {closed['pts']:+.0f} · {label}"
    return {"t": e["t"], "side": e["side"], "word": w, "label": label, "line": _ticket(e, gp, act, [], held, closed)[-1], "checks": checks}


def _screen(ones, sig, walks, gp, armed, upto_m, ladder, spot, step, peers=None):
    """PLAN B speaks: DAY END > TRIGGER (a signal on the last closed 3-min bar) > IN TRADE > ARMED > OUT > WAIT."""
    ix = {b["t"]: i for i, b in enumerate(ones)}
    B, pos = walks["B"], walks["B"]["pos"]
    if upto_m >= LAST:
        pts = {k: (sum(x["pts"] for x in w["trades"]), len(w["trades"])) for k, w in walks.items()}
        return "DAY END", " · ".join(f"PLAN {k} {pts[k][0]:+.0f} ({pts[k][1]})" for k in "BAC"), None
    bar_end, last = OPEN + ((upto_m - OPEN + 1) // 3) * 3 - 1, (sig[-1] if sig else None)
    if last and M(last["t"]) + 2 == bar_end:
        closed = next((x for x in B["trades"] if x["why"] == "FLIP" and x["x"] == HM(bar_end)), None)
        tk = _ticket(last, gp, B["acts"].get((last["t"], last["side"])), _live_leg(ones, ix, sig, last), pos and pos["side"], closed)
        return "TRIGGER", tk[-1], tk
    if pos:
        oi = _other_side(ladder, spot, pos, HM(upto_m), step)
        tail = "" if oi is None else f" · OTHER SIDE {'adding (fuel)' if oi > 0 else 'cutting (being paid)'}"
        sync = _sync(peers, pos, upto_m)
        tail += f" · {sync}" if sync else ""
        return "IN TRADE", (f"HOLD {pos['side']} {pos['px']:,.0f}f · wrong only at {pos['stop']:,.0f}f · out on a valid "
                            f"{'BUY' if pos['S'] < 0 else 'SELL'} or 15:00{tail}"), None
    pre = f"GAP DAY · {gp['text']} · no fades" if gp["ok"] is False else ""
    if armed:
        arm = " · ".join(f"ARMED {s} · {a['band']} touched {a['first']} · extreme {a['ext']:,.0f}f" for s, a in sorted(armed.items()))
        return "ARMED", (pre + " · " if pre else "") + arm, None
    if B["trades"] and B["trades"][-1]["why"] == "STOP":
        return "OUT", (pre + " · " if pre else "") + f"STOPPED {B['trades'][-1]['pts']:+.0f} · look again", None
    return "WAIT", pre or "WAIT · no zone armed", None


def _summary(w):
    tr = w["trades"]
    return {"pts": round(sum(x["pts"] for x in tr), 1), "n": len(tr), "won": sum(1 for x in tr if x["pts"] > 0),
            "open": None if not w["pos"] else {k: w["pos"][k] for k in ("t", "side", "px", "stop")},
            "trades": [dict({k: x[k] for k in ("t", "side", "px", "x", "why")}, pts=round(x["pts"], 1)) for x in tr]}


def day_state(day, ones, delta=None, prev_ones=None, changed=False, upto=None, ladder=None, spot=None, step=50, peers=None):
    """THE BRAIN, pure. ones = the day's exchange 1-min futures candles; delta = Dext delta {HH:MM: lots}; prev_ones = the
    previous weekday's candles or None; changed = a new contract since then; upto = the last minute to use (None = all);
    peers = {"BANKNIFTY": candles, "SENSEX": candles} for the SYNC line (None = not shown)."""
    ones = [b for b in ones or () if b.get("c") is not None and b["t"] >= "09:15"]
    if not ones:
        return {"ok": False, "day": day, "why": f"could not check — no futures candles for {day}"}
    upto_m = M(upto) if upto else M(ones[-1]["t"])
    bar_end = OPEN + ((upto_m - OPEN + 1) // 3) * 3 - 1
    now = [b for b in ones if M(b["t"]) <= upto_m]
    blist = ruler.bands([b for b in ones if M(b["t"]) <= bar_end], 3)
    T, armed = triggers(blist)
    gp = gap(ones, prev_ones, changed)
    sig = _signals(blist, [e for e in T if M(e["t"]) + 2 < LAST], delta or {}, gp)
    walks = {k: _walk(now, sig, k, None if upto is None else upto_m) for k in "ABC"}
    state, line, ticket = _screen(now, sig, walks, gp, armed, upto_m, ladder, spot, step, peers)
    ix = {b["t"]: i for i, b in enumerate(now)}
    rows = [{"t": e["t"], "side": e["side"], "px": e["px"], "ext": e["ext"], "risk": round(e["risk"], 1),
             "z": None if e["z"] is None else round(e["z"], 2), "vw": e["vw"], "fs": e["fs"], "chk": e["chk"],
             "live": _live_leg(now, ix, sig, e),
             **{k.lower(): (walks[k]["acts"].get((e["t"], e["side"])) or ("—", None))[0] for k in "ABC"}} for e in sig]
    B = walks["B"]
    closed = lambda e: next((x for x in B["trades"] if x["why"] == "FLIP" and x["x"] == HM(M(e["t"]) + 2)), None)   # noqa: E731
    marks = [_mark(e, gp, B["acts"].get((e["t"], e["side"])), closed(e)) for e in sig]
    out = {"ok": True, "day": day, "upto": HM(upto_m), "state": state, "line": line, "ticket": ticket, "signals": rows,
           "marks": marks, "plan_a": _summary(walks["A"]), "plan_b": _summary(B), "plan_c": _summary(walks["C"]), "gap": gp, "why": []}
    if sig and state != "TRIGGER":                   # Fable A337 #9: the last ticket stays on screen (the faces grey it) until the next one
        e = sig[-1]
        out["last"] = _ticket(e, gp, B["acts"].get((e["t"], e["side"])), _live_leg(now, ix, sig, e),
                              "SELL" if e["side"] == "BUY" else "BUY", closed(e))
    if upto_m >= LAST:                               # Fable A337 #3: after the close, every signal scored alone (a SKIP too)
        out["results"] = [dict({"t": e["t"], "side": e["side"], "b": (B["acts"].get((e["t"], e["side"])) or ("—",))[0]}, **_alone(now, e))
                          for e in sig]
    return out


def _alone(ones, e):
    """One signal taken alone with her stop, held to 15:00: its points, its best move her way, the minute it was stopped (None = held)."""
    ie = next((i for i, b in enumerate(ones) if b["t"] == HM(M(e["t"]) + 2)), None)
    if ie is None:
        return {"pts": None, "best": None, "stop": None}
    S, best, last = e["S"], 0.0, None
    for b in ones[ie + 1:]:
        if M(b["t"]) > LAST:
            break
        if (S < 0 and b["h"] > e["ext"]) or (S > 0 and b["l"] < e["ext"]):
            return {"pts": round(-abs(e["ext"] - e["px"]), 1), "best": round(best, 1), "stop": b["t"]}
        best, last = max(best, (e["px"] - b["l"]) if S < 0 else (b["h"] - e["px"])), b["c"]
    return {"pts": None if last is None else round(S * (last - e["px"]), 1), "best": round(best, 1), "stop": None}


def her_dirs(trades, idx="NIFTY"):
    """Her open marked trades on idx -> their directions: a CE bought or a PE sold is a BUY view; a PE bought or a CE sold a SELL view."""
    return ["BUY" if (str(t.get("side")).upper() == "CE") == (str(t.get("role")).lower() in ("buy", "long")) else "SELL"
            for t in trades or () if t.get("idx") == idx and not t.get("exit_t")]


def card(ex, her=None):
    """The card's compact block (the ≤10 KB contract): the line, at a trigger the ticket, after it the last ticket (the faces grey
    it). her = the directions of her open marked trades (None = not known, as in a replay): a plan trade she is not in says PAPER."""
    if not ex.get("ok"):
        return {"ok": False, "why": ex.get("why")}
    c = {k: ex.get(k) for k in ("ok", "day", "upto", "state", "line", "ticket", "last")}
    op = (ex.get("plan_b") or {}).get("open")
    if her is not None and ex.get("state") == "IN TRADE" and op and op.get("side") not in her:   # Fable A337 #5
        c["line"] = "PAPER · " + (c["line"] or "")
    return c


def log_rows(ex, at=None):
    """The forward log's rows: one per signal, one per closed plan trade, and after the close one result per signal (her stop or
    15:00, taken alone); each with a key that never repeats, the clock time it was first written (`at`) and live / backfill."""
    src = lambda minute: None if at is None else ("live" if M(at) - minute <= LIVE_LAG else "backfill")   # noqa: E731
    rows = [dict(s, kind="signal", key=f"S|{s['t']}|{s['side']}", at=at, src=src(M(s["t"]) + 2)) for s in ex.get("signals") or ()]
    for p in "abc":
        rows += [dict(x, kind="close", plan=p.upper(), key=f"C|{p.upper()}|{x['t']}|{x['side']}", at=at, src=src(M(x["x"])))
                 for x in (ex.get("plan_" + p) or {}).get("trades") or ()]
    rows += [dict(r, kind="result", key=f"R|{r['t']}|{r['side']}", at=at, src="final") for r in ex.get("results") or ()]
    return rows


# ---------------------------------------------------------------- the two I/O adapters

def append_log(path, rows):
    """Append the rows whose key is not in the file yet (a restart re-reads it: never twice). Returns how many were written."""
    seen = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    seen.add(json.loads(line).get("key"))
                except ValueError:
                    continue
    new = [r for r in rows if r["key"] not in seen]
    if new:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in new)
    return len(new)


def last_session(day, back=10):
    """GAP's yesterday (Fable A337 #6): the last weekday before `day` with candles, at most `back` weekdays back (a holiday has
    none) -> (that day, its candles); (the previous weekday, None) when none is found."""
    d = day
    for _ in range(back):
        d = prev_weekday(d)
        c = [b for b in ruler.ones_of(d) if b.get("c") is not None]
        if len(c) >= 300:
            return d, c
    return prev_weekday(day), None


def for_frame(fr):
    """A Jarvis frame (live or replay) -> day_state: the saved exchange tape (ruler.ones_of) up to the frame's last minute,
    the frame's Dext delta (no fallback: all order flow from Dext), its ladder and spot for the OI line."""
    day, mins = fr.get("day"), fr.get("mins") or []
    if not day or not mins:
        return {"ok": False, "why": "could not check — the frame has no minutes"}
    pday, prev = last_session(day)
    return day_state(day, ruler.ones_of(day), {t: v for t, v in zip(mins, fr.get("delta") or ()) if v is not None},
                     prev, contract_changed(day, pday), upto=mins[-1], ladder=fr.get("ladder"),
                     spot={t: v for t, v in zip(mins, fr.get("spot") or ()) if v is not None}, step=fr.get("step") or 50,
                     peers={i: ruler.ones_of(day, i) for i in ("BANKNIFTY", "SENSEX")})
