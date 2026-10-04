# tapemap/validate_live.py
"""validate_live.py -- the live in-trade read for the Validate face (Mary's spec, C:/Users/kaam/Downloads/validate-tab-spec.md,
adapted to her house rules 2026-10-05): GET /api/validate?idx= and frame.story.trade_read.validate.

THE ENGINE'S WORD IS THE DECISION. `word` is fold.py's HOLD / PAST GIVE-UP / FOLD verbatim. Everything else here is a
read beside it: her four reads as lamps (the engine's own ZONE / FLOW / OI / VPIN rows: WITH -> G, QUIET / PULLBACK -> A,
AGAINST -> R, can't check -> X), the LEVEL line in futures points (the engine's space: G, the wall ahead and her entry
are futures prices), the reversal checklist (N/4, live -- no candle-close gate anywhere), the noise floor, the trail
lock, the timers, the expiry clock and the role prompt. The spec's lamp -> action table changes FOLD, so its words ride
in `shadow`, unsigned, logged beside the engine and never shown as the decision.

Pure: no I/O, no clock -- now_ms is handed in. Counts, never a rate; no rupee P&L anywhere."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from statistics import mean
from typing import List, Optional

import trade_record

IST = timezone(timedelta(hours=5, minutes=30))
BAR = 300000
LAMP = {"WITH": "G", "QUIET": "A", "PULLBACK": "A", "AGAINST": "R"}
CHIP = {"zone": "ZONE", "flow": "FLOW", "oi": "OI", "vpin": "VPIN"}
NAME = {"zone": "zone", "flow": "flow", "oi": "OI", "vpin": "VPIN"}      # the engine clause's own words
SEED_TYPICAL_S = 1200            # 20 min until her record has three target exits
REV_WINDOW = 3 * BAR             # the reversal conditions look at the last 3 bars
WRITE_WINDOW_MS = 10 * 60000     # fresh writing: her strike's OI over the last 10 minutes
CLOSE = "15:30:00"


def _hms(ms: Optional[int]) -> Optional[str]:
    return None if ms is None else datetime.fromtimestamp(ms / 1000, IST).strftime("%H:%M:%S")


def _ms(day: str, hms: str) -> Optional[int]:
    try:
        y, m, d = map(int, day.split("-"))
        p = [int(x) for x in str(hms).split(":")] + [0]
        return int(datetime(y, m, d, p[0], p[1], p[2], tzinfo=IST).timestamp() * 1000)
    except (ValueError, TypeError, AttributeError, IndexError):
        return None


def _r(x) -> Optional[float]:
    return None if x is None else round(x)


def typical_s(trades_by_day: List[List[dict]]) -> dict:
    """The median time from entry to a TARGET exit across her record (seeded at 20 min until there are three)."""
    secs = []
    for trades in trades_by_day:
        for t in trades:
            for r in trade_record.roles(t):
                if r.get("exit_reason") in ("TARGET_1", "TARGET_2") and r.get("exit_t") and r.get("entry_t"):
                    a = _ms("2000-01-01", r["entry_t"]); b = _ms("2000-01-01", r["exit_t"])
                    if a is not None and b is not None and b > a:
                        secs.append((b - a) / 1000)
    if len(secs) < 3:
        return {"s": SEED_TYPICAL_S, "n": len(secs), "src": "seed", "why": f"{len(secs)} target exit(s) in her record; 20 min seed until 3"}
    secs.sort()
    return {"s": int(secs[len(secs) // 2]), "n": len(secs), "src": "her record", "why": None}


def noise_floor(closed: List[dict]) -> Optional[float]:
    """1.5 x the mean high-low of the last 10 closed 5-min futures bars (spec §4.1)."""
    rs = [b["h"] - b["l"] for b in closed[-10:] if b.get("h") is not None and b.get("l") is not None]
    return round(1.5 * mean(rs), 1) if len(rs) >= 3 else None


def _lamps(view: dict, tr: dict, entry_hms: str) -> dict:
    chips, sents, evs = view.get("chips") or {}, view.get("sentences") or {}, view.get("events") or []
    rows = view.get("rows") or {}
    acks = tr.get("acks") or []
    out = {}
    for k, C in CHIP.items():
        raw = (chips.get(C[0]) or chips.get(C)) if chips else (rows.get(k) or {}).get("chip")      # the view keys Z / F / O / V
        st = LAMP.get(raw, "X")
        ch = [e for e in evs if e.get("kind") == "chip" and e.get("chip") == C]
        # the view carries its last 12 events: an older change is read back off the engine's clause ("OI since 10:35")
        m = None if ch else re.search(NAME[k] + r" since (\d\d:\d\d)", str(view.get("clause") or ""))
        since = ch[-1].get("ts") if ch else (m.group(1) + ":00") if m else entry_hms
        frm = LAMP.get(ch[-1].get("old"), "X") if ch else None
        acked = (not ch and not m) or any(a.get("lamp") == k and a.get("to") == st and str(a.get("t")) >= str(since) for a in acks)
        out[k] = {"state": st, "raw": raw, "text": sents.get(C[0]) or sents.get(C) or (rows.get(k) or {}).get("sentence") or ("can't check" if st == "X" else raw),
                  "since": since, "from": frm, "acked": acked}
    return out


def _excursion(closed: List[dict], entry_ms: int, fut: Optional[float], d: int):
    """(best, worst) futures price since her entry, from the closed bars that overlap the trade plus the price now."""
    hs = [b["h"] for b in closed if b.get("t") is not None and b["t"] + BAR > entry_ms and b.get("h") is not None]
    ls = [b["l"] for b in closed if b.get("t") is not None and b["t"] + BAR > entry_ms and b.get("l") is not None]
    if fut is not None:
        hs.append(fut); ls.append(fut)
    if not hs:
        return None, None
    return (max(hs), min(ls)) if d > 0 else (min(ls), max(hs))


def _writing(chain: List[dict], k: float, d: int, now_ms: int, day: str):
    """Fresh writing against her direction at her strike over the last 10 min [M]: the side that pays if the index goes
    against her has premium up with OI up (new buyers), or the side that pays her has OI up with premium down (new
    writers). -> (met, text) or (None, why)."""
    rows = [r for r in chain or [] if r.get("ts") and (_ms(day, r["ts"]) or 0) <= now_ms]
    if len(rows) < 2:
        return None, "could not check — no chain snapshots for her strike"
    now_r = rows[-1]
    then_r = next((r for r in rows if (_ms(day, r["ts"]) or 0) >= now_ms - WRITE_WINDOW_MS), rows[0])

    def leg(r, ty):
        x = next((s for s in r.get("strikes") or [] if float(s.get("k") or 0) == float(k)), None)
        v = (x or {}).get(ty.lower()) or {}
        return v.get("ltp"), v.get("oi")
    mine, other = ("CE", "PE") if d > 0 else ("PE", "CE")      # the leg that pays her; the mirror pays the other way
    (p1, o1), (p0, o0) = leg(now_r, mine), leg(then_r, mine)
    (q1, m1), (q0, m0) = leg(now_r, other), leg(then_r, other)
    if None in (p1, o1, p0, o0) or not o0:
        return None, f"could not check — no {k:g} {mine} OI in the chain"
    wrote = o1 > o0 * 1.02 and p1 < p0
    bought = None not in (q1, m1, q0, m0) and m0 and m1 > m0 * 1.02 and q1 > q0
    txt = (f"{k:g} {mine} OI {o0 / 1e5:.1f}L → {o1 / 1e5:.1f}L, premium {p0:g} → {p1:g} since {then_r['ts'][:5]}"
           + (f"; {k:g} {other} bought, OI {m0 / 1e5:.1f}L → {m1 / 1e5:.1f}L, premium {q0:g} → {q1:g}" if bought else ""))
    return bool(wrote or bought), ("fresh writing against you: " if wrote else "mirror leg initiation: " if bought else "no fresh writing against you: ") + txt


def _reversal(dec: Optional[dict], d: int, now_ms: int, fut, vwap, forming, chain, k, day) -> dict:
    evs = [e for e in ((dec or {}).get("events") or []) if isinstance(e, dict) and e.get("t") is not None]
    recent = [e for e in evs if now_ms - REV_WINDOW <= e["t"] + BAR <= now_ms and e.get("side") == -d and e.get("state") != "FAILED"]
    init = [e for e in recent if e.get("kind") == "E2"]
    cvd = [e for e in recent if e.get("kind") == "E7"]
    items = [{"key": "initiation", "met": bool(init),
              "text": (init[-1].get("chip") or "PEHAL against you") + f" · {init[-1].get('time')}" if init else "no opposing initiation in the last 3 bars"},
             {"key": "cvd", "met": bool(cvd),
              "text": (cvd[-1].get("chip") or "CVD ulta") + f" · {cvd[-1].get('time')}" if cvd else "CVD has not broken its swing against you"}]
    if vwap is None or fut is None:
        items.append({"key": "vwap", "met": None, "text": "could not check — no VWAP on the tape"})
    else:
        against = d * (fut - vwap) < 0
        held = forming is not None and forming.get("o") is not None and d * (forming["o"] - vwap) < 0
        items.append({"key": "vwap", "met": bool(against and held),
                      "text": (f"price {fut:,.0f} {'under' if d > 0 else 'over'} VWAP {vwap:,.0f} and this bar opened there — accepted, live"
                               if against and held else f"price {fut:,.0f} {'under' if d > 0 else 'over'} VWAP {vwap:,.0f}, not accepted yet (this bar opened on your side)"
                               if against else f"price {fut:,.0f} on your side of VWAP {vwap:,.0f}")})
    met, txt = _writing(chain, k, d, now_ms, day)
    items.append({"key": "writing", "met": met, "text": txt})
    return {"met": sum(1 for x in items if x["met"]), "of": 4, "items": items,
            "unknown": sum(1 for x in items if x["met"] is None)}


def read(tr: Optional[dict], fold: Optional[dict], day: str, now_ms: int, closed: Optional[List[dict]] = None,
         dec: Optional[dict] = None, vwap: Optional[float] = None, forming: Optional[dict] = None,
         chain: Optional[List[dict]] = None, walls: Optional[List[dict]] = None, trades: Optional[List[dict]] = None,
         typical: Optional[dict] = None, idx: str = "NIFTY") -> dict:
    """The live in-trade read for her open marked trade on idx; flat: the cooldown and flip timers only."""
    trades, closed = trades or [], [b for b in (closed or []) if b.get("t") is not None]
    cd, fl = trade_record.cooldown(trades, idx, now_ms / 1000)
    base = {"ok": True, "idx": idx, "asof": _hms(now_ms), "cooldown": cd, "cooldown_why": None if cd else "no STOPPED / RED exit in the last 10 min",
            "flip": fl, "flip_why": None if fl else "no exit in the last 60 s", "tag": "I",
            "note": "the engine's word is the decision; lamps, prompt and shadow are reads beside it (P1-P7 unsigned)"}
    v = (fold or {}).get("view") or {}
    if tr is None or tr.get("exit_t") or not (fold or {}).get("ok") or v.get("headline") is None:
        why = ("flat — no marked trade open" if tr is None or tr.get("exit_t") else
               (fold or {}).get("why") or v.get("why") or "the engine has no read of this trade yet")
        return {**base, "in_trade": tr is not None and not tr.get("exit_t"), "word": None, "word_why": why}
    d = v.get("d") or trade_record.direction(tr)
    E, fut = v.get("E"), v.get("fut")
    entry_hms = str(tr.get("t0"))
    entry_ms = _ms(day, entry_hms) or now_ms
    th = tr.get("thesis") or {}
    G, A = (v.get("G") or {}).get("px"), (v.get("A") or {}).get("px")
    t1 = th.get("t1") if th.get("t1") is not None else A
    if t1 is None and fut is not None:
        ahead = sorted((w["p"] for w in walls or [] if w.get("p") is not None and d * (w["p"] - fut) > 0), key=lambda p: d * (p - fut))
        t1 = ahead[0] if ahead else None
    t2 = th.get("t2")
    if t2 is None and t1 is not None:
        beyond = sorted((w["p"] for w in walls or [] if w.get("p") is not None and d * (w["p"] - t1) > 5), key=lambda p: d * (p - t1))
        t2 = beyond[0] if beyond else None
    inval = th.get("inval") if th.get("inval") is not None else G
    best, worst = _excursion(closed, entry_ms, fut, d)
    to = lambda lvl: None if lvl is None or fut is None else _r(d * (lvl - fut))      # noqa: E731
    hit = lambda lvl: lvl is not None and best is not None and d * (best - lvl) >= 0  # noqa: E731
    level = {"t1": t1, "t2": t2, "inval": inval, "to_t1": to(t1), "to_t2": to(t2),
             "to_inval": None if inval is None or fut is None else _r(d * (fut - inval)),
             "t1_hit": hit(t1), "t2_hit": hit(t2), "entry": E, "fut": fut, "units": "futures points",
             "src": {k: (th.get("src") or {}).get(k) or ("engine" if level_v is not None else None)
                     for k, level_v in (("t1", t1), ("t2", t2), ("inval", inval))}}
    for k in ("t1", "t2", "inval"):
        level[k + "_why"] = None if level[k] is not None else {"t1": "no wall ahead read and none set", "t2": "no level beyond T1 known; set it on the DESK",
                                                                "inval": "no give-up from the engine yet and none set"}[k]
    if fut is not None and inval is not None and d * (fut - inval) <= 0:
        level["state"] = "R"
    elif level["t2_hit"]:
        level["state"] = "T2"
    elif level["t1_hit"]:
        level["state"] = "T1"
    elif fut is not None and E is not None and d * (fut - E) < 0:
        level["state"] = "A"
    else:
        level["state"] = "G"
    lamps = _lamps(v, tr, entry_hms)
    rev = _reversal(dec, d, now_ms, fut, vwap, forming, chain, float(tr.get("k") or 0), day)
    nf = noise_floor(closed)
    # the trail: locked to the invalidation until T1 is touched or price has gone 1R her way (spec §4.2)
    R = abs(E - inval) if E is not None and inval is not None else None
    one_r = E + d * R if R else None
    unlocked = bool(level["t1_hit"] or (one_r is not None and best is not None and d * (best - one_r) >= 0))
    nxt = [x for x in (t1, one_r) if x is not None]
    at = (min(nxt, key=lambda x: d * (x - E)) if nxt and E is not None else None)
    prop = None
    if unlocked:                                          # structure only: the last pullback extreme since entry
        since = [b for b in closed if b["t"] + BAR > entry_ms]
        if since:
            prop = min(b["l"] for b in since[-3:]) if d > 0 else max(b["h"] for b in since[-3:])
    inside = prop is not None and nf is not None and fut is not None and abs(fut - prop) < nf
    trail = {"unlocked": unlocked, "at": None if unlocked else at, "one_r": one_r,
             "why": ("unlocked — " + ("T1 touched" if level["t1_hit"] else "1R reached")) if unlocked else
                    (f"locked until T1 {t1:,.0f} or 1R {one_r:,.0f}; the only stop is the invalidation {inval:,.0f}"
                     if t1 is not None and one_r is not None and inval is not None else "locked: the only stop is the invalidation"),
             "proposal": prop, "inside_noise": inside,
             "warn": (f"Trail at {prop:,.0f} is inside noise (5m range x1.5 = {nf:g} pts). This is a coin-flip exit." if inside else None)}
    # the timers (spec §5): her clock starts when the trade first goes her way by the noise floor
    typ = typical or {"s": SEED_TYPICAL_S, "src": "seed"}
    green_ms = None
    if nf is not None and E is not None:
        for b in closed:
            if b["t"] + BAR > entry_ms and d * ((b["h"] if d > 0 else b["l"]) - E) >= nf:
                green_ms = max(b["t"], entry_ms)
                break
        if green_ms is None and fut is not None and d * (fut - E) >= nf:
            green_ms = now_ms
    green_now = fut is not None and E is not None and d * (fut - E) > 0
    timer = {"in_trade_s": max(0, int((now_ms - entry_ms) / 1000)), "green_since": _hms(green_ms),
             "green_since_why": None if green_ms else "not yet her way by the noise floor",
             "typical_s": typ["s"], "typical_src": typ.get("src"),
             "fear_zone": bool(green_ms and green_now and (now_ms - green_ms) / 1000 < typ["s"] / 3)}
    # stall (spec §5.2): price under her entry AND flow amber, both for longer than her typical time
    stall = {"on": False, "since": None, "why": "not stalling"}
    if level["state"] == "A" and lamps["flow"]["state"] == "A":
        last_ok = max((b["t"] + BAR for b in closed if b["t"] + BAR > entry_ms and d * (b["c"] - E) >= 0), default=entry_ms)
        since_ms = max(last_ok, _ms(day, lamps["flow"]["since"]) or entry_ms)
        stall = {"on": (now_ms - since_ms) / 1000 > typ["s"], "since": _hms(since_ms),
                 "why": "stall — thesis not progressing (a legitimate cut, not fear)" if (now_ms - since_ms) / 1000 > typ["s"]
                 else f"price under entry and flow amber since {_hms(since_ms)[:5]}; stall after {typ['s'] // 60} min"}
    # the expiry clock (spec §5.4): DTE 0 only
    prem = v.get("prem") or {}
    theta = theta_why = None
    if prem.get("expiry_day"):
        left = max(0, int(((_ms(day, CLOSE) or now_ms) - now_ms) / 60000))
        tv = prem.get("time")
        theta = {"min_to_close": left, "time_value": tv,
                 "per_15m": round(tv / left * 15, 1) if tv is not None and left > 0 else None,
                 "per_15m_why": None if tv is not None and left > 0 else "no time value read from the chain",
                 "method": "time value spread evenly to 15:30 [I] — the chain carries no theta"}
    else:
        theta_why = "not expiry day (DTE > 0): no theta clock"
    # her lots, and whether an ADD may go on now (spec §6.3: FLOW just went AMBER -> GREEN, < 3 ADDs, 2 bars after an add)
    rs = trade_record.roles(tr)
    open_rs = [dict(r, stop_hit=bool(r.get("add_stop") is not None and fut is not None and d * (fut - r["add_stop"]) <= 0))
               for r in rs if not r.get("exit_t")]
    fl_ = lamps["flow"]
    flow_turn = fl_["state"] == "G" and fl_["from"] == "A" and (now_ms - (_ms(day, fl_["since"]) or 0)) <= BAR
    adds = [r for r in open_rs if r["role"] == "ADD"]
    last_add = max((_ms(day, r["entry_t"]) or 0 for r in rs if r["role"] == "ADD"), default=0)
    pull = [b for b in closed[-3:]]
    add_stop = (min(b["l"] for b in pull) if d > 0 else max(b["h"] for b in pull)) if pull else None
    add_why = (None if flow_turn and len(adds) < trade_record.MAX_ADDS and now_ms - last_add >= 2 * BAR else
               "only when FLOW has just gone AMBER → GREEN" if not flow_turn else
               f"{trade_record.MAX_ADDS} ADD lots already open" if len(adds) >= trade_record.MAX_ADDS else
               "locked for 2 bars after an add")
    add = {"ok": add_why is None, "why": add_why, "add_stop": add_stop}
    # the role prompt under the engine's word (spec §3.4, the role half): never on AMBER
    oi_g = lamps["oi"]["state"] == "G"
    banker = any(r["role"] == "BANKER" for r in open_rs)
    prompt = because = None
    if level["state"] == "R":
        prompt, because = "STOPPED", f"invalidation {inval:,.0f} crossed — exit all"
    elif level["t2_hit"] and not oi_g:
        prompt, because = "EXIT_ALL", "T2 touched and OI not green"
    elif rev["met"] >= 2 and adds:
        prompt, because = "CUT_ADDS", f"{rev['met']}/4 reversal conditions met — the ADD lots go first"
    elif level["t1_hit"] and banker:
        prompt, because = ("HOLD_BANKER", "T1 touched, OI green — writers covering, the move has fuel") if oi_g else \
                          ("BOOK_BANKER", "T1 touched, OI not green — book the BANKER")
    prompt_why = None if prompt else (
        "T2 touched, OI green: hold to the next level (re-plan the targets)" if level["t2_hit"] else
        f"{rev['met']}/4 reversal conditions met but no ADD lot open — the engine's word decides the rest" if rev["met"] >= 2 else
        "T1 touched; no BANKER lot open" if level["t1_hit"] else
        "no level event and fewer than 2 reversal conditions — nothing to do with the lots")
    # the spec's own lamp -> action words, beside the engine, unsigned (they would change FOLD)
    states = [x["state"] for x in lamps.values()]
    amber_no_exit = "A" in states and "R" not in states
    cut = rev["met"] >= 2
    sw = ("STOPPED" if level["state"] == "R" else ("EXIT ALL" if not oi_g else "HOLD to next level") if level["t2_hit"] else
          "CUT" if cut else ("HOLD BANKER" if oi_g else "BOOK BANKER") if level["t1_hit"] else
          "HOLD — pullback, not reversal" if level["state"] == "A" and fl_["state"] == "A" else "HOLD")
    return {**base, "in_trade": True, "trade_id": tr.get("id"), "word": v.get("headline"), "word_why": None, "clause": v.get("clause") or None,
            "prompt": prompt, "prompt_why": prompt_why, "prompt_because": because,
            "lamps": lamps, "level": level, "reversal": rev, "noise_floor": nf,
            "noise_floor_why": None if nf is not None else "fewer than 3 closed bars on the tape",
            "trail_unlock": trail, "timer": timer, "stall": stall, "theta": theta, "theta_why": theta_why,
            "roles": open_rs, "add": add, "thesis": th or None, "thesis_why": None if th else "no thesis written at the mark; the engine's levels stand in",
            "acks": tr.get("acks") or [], "tags": tr.get("tags") or [],
            "shadow": {"word": sw, "amber_no_exit": amber_no_exit, "cut_2of4": cut,
                       "why": "the spec's lamp → action words; they would change FOLD, so they are logged beside the engine, unsigned"}}
