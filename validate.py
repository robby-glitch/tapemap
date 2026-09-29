"""validate.py -- THE VALIDATE WORD: GO · WAIT · NO, exactly as registered.

THE SPEC is docs/hold/VALIDATE-PREREG.md rev 2 (sha256 4a9b5963...4423), signed on her delegation
2026-09-25 19:40. Rev 1 (VALIDATE-PREREG-rev1.md) is retired unjudged; its press rows are its own record and
are never pooled with rev 2's, which carry `rev: "2"`. For a BUYER, four facts (§1), each WITH you /
AGAINST / NEITHER:

  Your setup  the zone machine's own state on the last closed 3-min bar, picked by §1.1's rule
  Right now   the window's entry check, read now (the one place trend counts)
  Room        the window's line L against one candle's noise, and the target (PLAN's rung, leaving walls out)
  Paying      the window's quiet-clock "paid" at the check minute

and one word by a fixed rule (§2). The outcome (§3) is a first passage to the STATIC target and the STATIC L
over the next 30 finished minutes; it reads no break rule. A writer gets no word (§1.6). A COUNT, never a
percentage (CLAUDE.md rule 4); never a size, never an order; it gates nothing.

Each fact says which absence a NEITHER is: "none" checked, none · "blind" could not check · "hidden" not
shown · None a read (CLAUDE.md rule 6). Display only: the states and the word never read it.

Pure: no I/O, no clock.
"""
from __future__ import annotations

import fronts
import hold
import plan

CC, NONE, NOT_SHOWN = hold.CC, hold.NONE, hold.NOT_SHOWN
REV = "2"
DRAFT = ("DRAFT — pre-registered 2026-09-25 (docs/hold/VALIDATE-PREREG.md rev 2, signed 19:40); its §4 decides, "
         "on your forward checks")
NAMES = ("Your setup", "Right now", "Room", "Paying")
HORIZON = 30          # §3 / §5: the outcome's window and the unit's spacing, finished minutes (rev 4 §7's horizon)
GATE = "09:25"        # §1.1: the zone machine's own gate (band_rotation.ANCHOR_MINUTE)
ACTIVE = ("ARMED", "TRIGGERED", "IN_TRADE")
STATE_WORD = {"ARMED": "armed", "TRIGGERED": "triggered", "IN_TRADE": "in trade"}
WRITER_NOTE = NOT_SHOWN + ("a GO / WAIT / NO for a writer: this word is judged on target against stop, and a "
                           "writer has no target; hers needs its own registration.")
FLOW_WORD = {"with": "with you", "against": "against you", "flat": "flat", "blind": "could not check"}
SIGMA = NOT_SHOWN + "σ against VWAP: the window's footer, never an input"          # §1.5, printed, not counted


# ---------------------------------------------------------------- §1.1 Your setup
def pick(bars, buy, sell, zrows, asof, d):
    """§1.1: the zone machine (§1b, armed at d2 / u2) on bar b, the last 3-min bar whose last minute is at or
    before `asof`, picked by the registered rule -- never by any display's. `bars`: the day's 3-min future bars
    ({t, fut: {c, d3, d2, u2, u3}}); `buy` / `sell`: its per-bar zone_state / zone_state_sell; `zrows`: the
    day's rule-zone rows on this index with their §1d gates. -> the fact and the press row's `setup` keys."""
    out = {"machine": "zone", "side": None, "state": None, "band": None, "ref_t": None, "candles_left": None,
           "legal": None, "why": None, "bar": None, "context": None}

    def fact(state, text, absence=None):
        return {**out, "fact": state, "text": text, "absence": absence}
    if not bars or not isinstance(buy, list) or not isinstance(sell, list) or not len(buy) == len(sell) == len(bars):
        return fact("neither", CC + "the tape record could not be read", "blind")
    ib = max((i for i, b in enumerate(bars) if isinstance((b or {}).get("t"), str)
              and fronts.bar_last_minute(b["t"], 3) <= asof), default=None)
    if ib is None:
        return fact("neither", CC + "the zone machine is not live yet (no 3-min bar has closed)", "blind")
    t = out["bar"] = bars[ib]["t"]
    f = bars[ib].get("fut") or bars[ib]
    d3, d2, u2, u3, c = (f.get(k) for k in ("d3", "d2", "u2", "u3", "c"))
    if t < GATE:                                           # 1. not live yet -- which is also the both-pockets case
        return fact("neither", CC + f"the zone machine is not live yet (the {t} bar starts before its 09:25 gate)", "blind")
    if None in (d2, u2, c) or u2 <= d2:
        return fact("neither", CC + f"the zone machine is not live yet (the {t} bar's bands have not formed)", "blind")
    m = {"BUY": (buy[ib] or {}, buy), "SELL": (sell[ib] or {}, sell)}
    act = [s for s in ("BUY", "SELL") if m[s][0].get("state") in ACTIVE]
    pocket = ("BUY" if d3 is not None and d3 <= c <= d2 else "SELL" if u3 is not None and u2 <= c <= u3 else None)

    def event(s):                                          # an arm's reference bar; a trigger's own entry bar
        z, lst = m[s]
        j = z.get("ref_i") if z.get("state") == "ARMED" else next(
            (j for j in range(ib, -1, -1) if (lst[j] or {}).get("entry")), None)
        return bars[j]["t"] if isinstance(j, int) and 0 <= j < len(bars) else None

    def head(s):
        z, band, ev = m[s][0], "d2" if s == "BUY" else "u2", event(s)
        left = z.get("candles_left") if z.get("state") == "ARMED" else None
        return f"zone {s} {band} {STATE_WORD[z['state']]}, {ev} bar" + (f", {left} candles left" if left is not None else "")
    if not act:                                            # 2. neither active
        last = _last_event(bars, buy, sell, ib)
        return fact("neither", NONE + "the zone machine is waiting on both sides; "
                    + (f"its last event was {last}" if last else "no event yet today"), "none")
    if len(act) == 1:                                      # 3. one active wins, whatever the pocket
        s = act[0]
        if pocket and pocket != s:
            out["context"] = (f"price closed in the {pocket.lower()} pocket, but that machine is waiting — "
                              + _waiting(bars, m[pocket][1], ib))
    elif pocket:                                           # 4a. both active: the pocket at b's close
        s = pocket
    else:                                                  # 4b. the later event bar; 4c. a tie reads NEITHER
        ev = {s: event(s) for s in act}
        if None in ev.values() or ev["BUY"] == ev["SELL"]:
            return fact("neither", f"the zone machine points both ways on the {t} bar: {head('BUY')}; {head('SELL')}")
        s = max(act, key=lambda s: hold.mm(ev[s]))
    z, ev = m[s][0], event(s)
    out.update(side=s, state=z["state"], band="d2" if s == "BUY" else "u2", ref_t=ev,
               candles_left=z.get("candles_left") if z["state"] == "ARMED" else None)
    arm = z["state"] == "ARMED"
    row = next((r for r in zrows or [] if r.get("rule") == "zone" and r.get("t") == ev and r.get("side") == s
                and (r.get("kind") == "arm") == arm), None) if ev else None
    h = head(s)
    if row is None:
        return fact("neither", CC + f"{h} — its zone row is not in the record", "blind")
    g = row.get("gate") or {}
    out.update(legal=g.get("legal"), why=g.get("why"))
    if g.get("legal") is None:
        return fact("neither", CC + f"{h} — its gate was not read", "blind")
    mine = (1 if s == "BUY" else -1) == d
    if g["legal"] is False:
        return fact("neither", f"{h} — gate illegal ({g.get('why')}): "
                    + ("your direction, but the fade is refused" if mine else "the other side's fade is refused"))
    return (fact("for", f"{h}, gate legal — your setup, your direction") if mine else
            fact("against", f"{h}, gate legal — the other side's setup is live"))


def _events(lst, j, s):
    z = lst[j] or {}
    band = "d2" if s == "BUY" else "u2"
    ew = z.get("exit_why")
    return [x for x in (f"{s} {band} armed" if z.get("arm") else None,
                        f"{s} {band} triggered" if z.get("entry") else None,
                        f"{s} {band} lock cleared at {'VWAP' if ew == 'vwap' else 'its stop'}" if ew else None) if x]


def _last_event(bars, buy, sell, ib):
    for j in range(ib, -1, -1):
        e = _events(buy, j, "BUY") + _events(sell, j, "SELL")
        if e:
            return f"{' and '.join(e)}, {bars[j]['t']} bar"
    return None


def _waiting(bars, lst, ib):
    j = next((j for j in range(ib, -1, -1) if (lst[j] or {}).get("arm") or (lst[j] or {}).get("entry")
              or (lst[j] or {}).get("exit_why")), None)
    return f"lock open since {bars[j]['t']}" if j is not None and (lst[j] or {}).get("exit_why") else "no arm"


# ---------------------------------------------------------------- §1.3 Room
def target(rec, d, close, ext):
    """§1.3: THE PLAN's rung (§2.2) re-read with every GIVING WAY wall removed -- a wall that is leaving caps
    nothing, so it cannot be the target: the nearest sized payers'-side front beyond the index that is
    DEFENDED or STALLED; else the session extreme beyond; else none."""
    if rec.get("blind"):
        return {"blind": CC + f"the walls could not be read: {hold._strip(rec['blind'])}"}
    fr = [f for f in rec.get("fr") or [] if plan.word(f["state"], plan._live_fold(rec, f["k"], f["side"])) != "GIVING WAY"]
    rg = plan.rung({**rec, "fr": fr}, d, close, ext)
    return {"src": rg["src"], "side": rg["side"], "k": rg["k"], "word": rg.get("word"),
            "pts": None if rg["k"] is None else round(abs(rg["k"] - close), 2)}


def geometry(minutes, i, d, ln, late=None):
    """§1.3's three quantities at check minute i, unrounded (exact on the 0.05 price grid): the line distance
    |close − L| -- L itself under rev 5 B, its break level printed, never used -- the noise (hold.noise, the one
    measure the window's B reads) and the target. ONE function for the check's Room and the outcome (§3)."""
    t, x = minutes[i]["t"], minutes[i].get("ix")
    close = x[0] if x else None
    ext = None
    for m in minutes[:i + 1]:
        y = m.get("ix")
        if y:
            v = y[2] if d < 0 else y[1]
            ext = v if ext is None else (min(ext, v) if d < 0 else max(ext, v))
    nz, n = hold.noise(minutes, i, late)
    L = None if not ln or ln.get("blind") else ln.get("L")
    why = (ln or {}).get("blind") or (None if close is not None else CC + f"no index candle at {t}")
    return {"t": t, "close": close, "L": L, "line": None if L is None or close is None else round(abs(close - L), 2),
            "noise": nz, "n": n, "B": (ln or {}).get("B"), "level": (ln or {}).get("level"),
            "target": target(minutes[i], d, close, ext) if close is not None else {"blind": why}, "why": why}


def room(g, buyer=True):
    """§1.3's order: the line blind or the noise unreadable -- could not check; line <= noise AGAINST (a tie is
    AGAINST); the walls unreadable -- could not check; target < line AGAINST (a tie is WITH); else WITH.
    A writer gets the line-against-noise half, printed (§1.6)."""
    if g["line"] is None:
        return ("neither", CC + f"the line could not be set at {g['t']}: {hold._strip(g['why'])}", "blind")
    if g["noise"] is None:
        return ("neither", CC + f"{g['n']} of {hold.QUIET} candles", "blind")
    s, m = g["line"], hold._pts(g["noise"])
    if s <= g["noise"]:
        return ("against", f"your line is {s} pts away — inside one candle's range (median {m} pts over the last "
                           f"15 min [M])" + _further(g), None)
    if not buyer:
        return ("for", f"your line is {s} pts away — outside one candle's range (median {m} pts [M])", None)
    tg = g["target"]
    if tg.get("blind"):
        return ("neither", tg["blind"], "blind")
    if tg["src"] == "none":
        return ("for", f"your line is {s} pts away, outside one candle ({m} pts [M]); no wall in the way — price discovery", None)
    at = _target_name(tg)
    if tg["pts"] < s:
        return ("against", f"{at} is only {tg['pts']} pts away, nearer than your line at {s} [M]", None)
    return ("for", f"your line is {s} pts away, outside one candle ({m} pts [M]); {at} is {tg['pts']} pts away", None)


def _further(g):
    return f" (the window breaks one candle further, at {g['level']:,.1f})" if g.get("B") is not None else ""


def _target_name(tg):
    if tg["src"] == "wall":
        return f"the next wall ({tg['side']} {tg['k']:,.0f}, {tg['word']})"
    return f"the session {'low' if tg['side'] == 'PE' else 'high'} ({tg['k']:,.1f})"


# ---------------------------------------------------------------- §1.2 Right now, §1.4 Paying
def _right_now(ck):
    ent = ck.get("entry") or {}
    ev, why = ent.get("verdict"), (ent.get("text") or "").split(" — ", 1)[-1].rstrip(".")
    return (("for", "you would enter into HOLD — " + why, None) if ev == "HOLD" else
            ("against", "you would enter a broken setup — " + why, None) if ev == "FOLD" else
            ("neither", f"you would enter into {ev or 'PATA NAHI'} — {why}", None if ev == "WATCH" else "blind"))


def _paying(ck):
    """§1.4: the window's own "paid" at the check minute, off now.clock.paid_last == asof. OI blind: could not
    check; nothing paying: checked, none. No AGAINST state."""
    now, asof = ck.get("now") or {}, ck.get("asof")
    P, H, F = now.get("payers") or {}, now.get("holders") or {}, now.get("flow") or {}
    if P.get("state") == "blind" and H.get("state") == "blind":
        return ("neither", CC + "OI " + (hold._strip(P.get("fact")) or "not read"), "blind")
    if (now.get("clock") or {}).get("paid_last") == asof:
        what = (hold._lc(P["fact"]) if P.get("state") == "for" else           # name what actually paid (audit bug 6)
                f"the payers' fold of {P['fold_t']}" if P.get("fold_t") else
                "flow with you" if F.get("state") == "with" else hold._lc(P.get("fact") or ""))
        return ("for", f"paid at {asof}: {what}", None)
    return ("neither", NONE + f"nothing paying at {asof}: {hold._lc(P.get('fact') or '')}; "
                              f"flow {FLOW_WORD.get(F.get('state'), 'could not check')}", "none")


# ---------------------------------------------------------------- §2 the word
def word(ck):
    """The four facts, the word, its count and one sentence. `ck` is /api/hold/check's reply with the
    server's `setup` (pick) and `room` (geometry) added."""
    tr = ck.get("trade") or {}
    buyer = tr.get("role") != "short"
    d = (ck.get("thesis") or {}).get("d") or (1 if tr.get("side") == "CE" else -1)
    su, g = ck.get("setup") or {}, ck.get("room")
    facts = [(su.get("fact") or "neither", su.get("text") or CC + "the zone machine", su.get("absence", "blind") if su else "blind"),
             _right_now(ck),
             room(g, buyer) if g else ("neither", CC + "the room could not be read", "blind"),
             _paying(ck) if buyer else ("neither", NOT_SHOWN + "Paying: a writer has no quiet clock; time pays her", "hidden")]
    n = {s: sum(1 for f in facts if f[0] == s) for s in ("for", "against", "neither")}
    if not buyer:
        w = None                                           # §1.6
    elif facts[1][0] == "against":
        w = "NO"
    elif facts[1][0] == "for" and n["against"] == 0 and n["neither"] <= 1:
        w = "GO"
    else:
        w = "WAIT"
    sentence, needs = _say(w, facts, ck, g, su, d)
    return {"word": w, "rev": REV,
            "count": f"{n['for']} for · {n['against']} against · {n['neither']} neither — of 4, a count, not odds",
            "n_for": n["for"], "n_against": n["against"], "n_neither": n["neither"], "sentence": sentence,
            "needs": needs, "draft": DRAFT, "tag": "I",
            "writer_note": None if buyer else WRITER_NOTE,
            "not_shown": [SIGMA] + ([] if buyer else [NOT_SHOWN + "a writer has no next wall; time is her target"]),
            "line": g and g["line"], "noise": g and g["noise"], "target": g and g["target"],
            "facts": [{"name": nm, "state": s, "text": t, "absence": a} for nm, (s, t, a) in zip(NAMES, facts)]}


def _say(w, facts, ck, g, su, d):
    """§2's sentences. -> (sentence, needs)."""
    if w is None:                                          # a writer: the window's entry verdict is the headline
        return (ck.get("entry") or {}).get("text"), []
    t, opt = ck.get("asof"), "call" if d > 0 else "put"
    if w == "GO":
        return f"Nothing is against you; {sum(f[0] == 'for' for f in facts)} of 4 line up.", []
    if w == "NO":
        now, rule = ck.get("now") or {}, (ck.get("entry") or {}).get("fold_rule")
        P, H, Fl, T = (now.get(k) or {} for k in ("payers", "holders", "flow", "trend"))
        th = hold.thesis("CE" if d > 0 else "PE", "long")
        if rule == 4:
            return (f"Positioning has flipped against your {opt} (read {t}): {hold._lc(hold._w(th['Q']))} at "
                    f"{hold._k(P.get('k') or 0)} are adding in your way, and the {hold._lc(hold._w(th['R']))} "
                    f"{'below' if th['R'] == 'PE' else 'above'} are covering."), []
        fams = [f for f in (hold._lc(P.get("fact") or "") if P.get("state") == "against" else None,
                            f"flow against you: {Fl.get('fact')} [I]" if Fl.get("state") == "against" else None,
                            f"trend against you: {T.get('rows')} [I]" if T.get("state") == "against" else None) if f]
        return f"Two families are against your {opt} (read {t}): {'; '.join(fams)}.", []
    against = [i for i, f in enumerate(facts) if f[0] == "against"]
    if not against:
        names = [NAMES[i] for i, f in enumerate(facts) if f[0] == "neither"]
        return (f"Nothing is against you, but only {sum(f[0] == 'for' for f in facts)} of 4 line up. "
                f"Not there yet: {', '.join(names)}."), names
    parts = []
    if 2 in against:                                       # two AGAINST: Room's sentence leads
        s, tg = g["line"], g["target"]
        if s <= (g["noise"] or 0):
            parts.append(f"Your line is {s} pts away — inside one candle's range (median {hold._pts(g['noise'])} pts "
                         f"over the last 15 min [M]){_further(g)}.")
        elif tg["src"] == "wall":
            parts.append(f"Your line is {s} pts away; the next wall ({tg['side']} {tg['k']:,.0f}, {tg['word']}) "
                         f"is only {tg['pts']} [M].")
        else:
            parts.append(f"Your line is {s} pts away; the session {'low' if tg['side'] == 'PE' else 'high'} "
                         f"({tg['k']:,.1f}) is only {tg['pts']} — no sized wall inside the nine that is holding [M].")
    if 0 in against:
        parts.append(f"{su['side']} {su['band']} {STATE_WORD[su['state']]}, {su['ref_t']} bar, gate legal — "
                     "the other side's setup is live.")
    return " ".join(parts), [NAMES[i] for i in against]


# ---------------------------------------------------------------- §3 the outcome, the unit, §4 the stratum
def outcome(minutes, i, d, g):
    """§3: the geometry the word read, frozen at check minute i -- a first passage on 1-min highs / lows to the
    static target and the static L over the HORIZON finished minutes after it (to 15:29, `short`, after
    14:59). A minute with no candle cannot touch; it is counted in `gaps`. None until the window has finished."""
    t = minutes[i]["t"]
    end = min(hold.mm(t) + HORIZON, hold.mm(hold.SESSION[-1]))
    if hold.mm(minutes[-1]["t"]) < end:
        return None
    win = [m for m in minutes[i + 1:] if hold.mm(m["t"]) <= end]
    tg = g["target"]
    out = {"target": {k: tg.get(k) for k in ("src", "side", "k", "pts")}, "stop": {"L": g["L"], "pts": g["line"]},
           "noise": g["noise"], "first": "not scored", "why": None, "at": None, "to": hold.hm(end),
           "short": hold.mm(t) + HORIZON > hold.mm(hold.SESSION[-1]), "gaps": sum(1 for m in win if not m.get("ix"))}
    if g["line"] is None:
        return {**out, "why": CC + f"the line could not be set at {t}: {hold._strip(g['why'])}"}
    if tg.get("blind"):
        return {**out, "why": CC + f"the walls could not be read at {t}"}
    if tg["src"] == "none":
        return {**out, "why": NONE + "no target (price discovery)"}
    L, T = g["L"], tg["k"]
    for m in win:
        x = m.get("ix")
        if not x:
            continue
        hit_t = x[2] <= T if d < 0 else x[1] >= T
        hit_s = x[1] >= L if d < 0 else x[2] <= L
        if hit_t or hit_s:
            return {**out, "first": "same minute" if hit_t and hit_s else "target" if hit_t else "stop", "at": m["t"]}
    return {**out, "first": "neither"}


def units(rows):
    """§3's unit, computed at judging time: the FIRST rev 2 buyer press per (index, direction) per HORIZON
    minutes, whatever its word -- the next unit is the first press at least HORIZON minutes after the last."""
    out, last = [], {}
    presses = [r for r in rows if r.get("rev") == REV and r.get("kind") != "check_outcome" and r.get("role") == "long"]
    for r in sorted(presses, key=lambda r: (r["t"], r.get("at") or 0)):
        key = (r["idx"], r["d"])
        if key not in last or hold.mm(r["t"]) - hold.mm(last[key]) >= HORIZON:
            last[key] = r["t"]
            out.append(r)
    return out


def in_stratum(o):
    """§4: the judged geometry, Room's whole WITH -- line > noise AND target >= line, both at the check. Units
    outside it are shown, not judged."""
    s, n, tg = (o.get("stop") or {}).get("pts"), o.get("noise"), (o.get("target") or {}).get("pts")
    return None not in (s, n, tg) and s > n and tg >= s
