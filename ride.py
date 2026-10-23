"""ride.py -- RIDE, her second setup: READ-V2 §E's trend pullback + OI + FLOW, and her hold (research-findings §1j).

THE BINDING TEXT is docs/setup-review/RIDE-PREREG.md (sha256 dcb306a1...aff7e). Every number is that file's, fixed
before any outcome existed; none is to be grid-searched. Pure: no I/O, no clock. Causal: every read at a bar uses data
at or before that bar's close. DESCRIPTIVE ONLY: no hit rate anywhere.

    LOCATION  a §E ENTRY (frame_v2.plan, never re-implemented: called causally, once per closed 3-min bar).
    OI        fronts.read (§1d's parameters) at the bar's last minute: the trend-side front (CE for ▼, PE for ▲)
              BUILDING and the defending front not BUILDING. A stale grid is "could not check", never a verdict.
    FLOW      §1i's book and side rule: ▼ tilt(last 5) <= -0.10 and tilt(the 15 before) <= +0.10; ▲ mirrored. NIFTY:
              a GoCharting tilt on the same 5 min >= +0.10 (▼) / <= -0.10 (▲) is "sources disagree". Absent GC is not.
    ENTRY     the first 3-min close from the §E bar through 3 bars after it (<= 9 min) with OI ok and FLOW ok, the
              close still on the trend side of VWAP, closing at or before 15:00. One per §E ENTRY.
    HOLD      the first of: the HARD LINE (intrabar on 1-min bars; trails to FLIP + 0.25 sigma only toward price),
              SOMEBODY GAVE UP (the trend-side front UNWINDING at a 3-min close: exit at that close), 15:20.
              No candle-close exit, no fixed target; STALLED and the READ word changing never exit. R on the initial
              risk throughout.

TIMES. 3-min events are named by the bar's END ("10:03" = the bar 10:00-10:03), as §E's own rows are. `hm` here is
minutes -> "HH:MM" (confluence.hm); frame_v2.hm is seconds -> "HH:MM". Both are used, deliberately.
"""
from __future__ import annotations

import confluence
import frame_v2
import fronts

REV = "ride-1 (RIDE-PREREG dcb306a1)"
TILT, FAST, SLOW = confluence.TILT, confluence.FAST, confluence.SLOW   # §0: the same FLOW numbers as §1i
WINDOW_BARS, WINDOW_MIN = 3, 9                                          # §1 ENTRY: the §E bar + 3 bars, <= 9 min
CUTOFF, MARK = 15 * 60, 15 * 60 + 20                                    # §1 no entry after 15:00; §2 marked at 15:20
LINE_BUF, MIN_RISK = 0.25, 0.5                                          # §2 sigma beyond the line; risk floor
IST_MS = confluence.IST_MS
hm = confluence.hm


def _upto(rows, e):
    """The READ rows marked at or before `e` (sec of day): read's rows are prefix-stable
    (test_read.test_live_equals_replay_no_look_ahead), so this is what the live frame saw then."""
    return [r for r in rows or () if isinstance(r.get("t"), str) and frame_v2._sec(r["t"]) <= e]


def entries(b3, rows, basis):
    """Every §E ENTRY, found causally: frame_v2.plan on the bars closed by each bar's end, the READ rows marked by
    then and the frame's basis band as of then -- exactly the live frame's call at that close. `basis` is a function of
    that close (sec of day; confluence_log.ride_inputs gives compose's own) or one fixed band: the band decides §E's
    T2 wall, hence when a position ends and the zone re-arms, so a later band would show entries the frame never
    showed. -> [{"i", "t" (bar END), "d", "word", "px"}]"""
    out = []
    for k in range(1, len(b3) + 1):
        now = b3[k - 1]["e"]
        p, _why = frame_v2.plan(b3[:k], _upto(rows, now), basis(now) if callable(basis) else basis, now)
        t = frame_v2.hm(now)
        for ev in (p or {}).get("rows") or ():
            if ev.get("what") == "ENTRY" and ev.get("t") == t:
                out.append({"i": k - 1, "t": t, "d": p["d"], "word": p.get("word"), "px": ev.get("px")})
    return out


def oi_read(d, minutes, peaks, at):
    """§1 OI at minute `at` (the last minute inside the bar). Stale or unreadable -> ok None with the reason."""
    cut = fronts.cut(minutes, at)
    stale = fronts.stale(cut, at)
    out = {"ok": None, "why": stale, "trend": None, "defend": None}
    if stale:
        return out
    rows = fronts.read(cut, confluence._upto(peaks, at))
    tside, dside = ("CE", "PE") if d < 0 else ("PE", "CE")
    t, f = fronts.side_front(rows, tside), fronts.side_front(rows, dside)
    if t is None or f is None:
        out["why"] = f"no {tside if t is None else dside} front read at {at}"
        return out
    out["trend"] = {"k": t["k"], "side": tside, "state": t["state"]}
    out["defend"] = {"k": f["k"], "side": dside, "state": f["state"]}
    out["ok"] = t["state"] == fronts.BUILDING and f["state"] != fronts.BUILDING
    out["why"] = f"{tside} {t['k']:.0f} {t['state']} · {dside} {f['k']:.0f} {f['state']}"
    return out


def flow_read(d, book, close, gc=None):
    """§1 FLOW at a bar closing at IST minute `close`. `gc` is NIFTY's GoCharting bars, None for the others."""
    t5, w5 = confluence.tilt(book, close - FAST, close)
    t15, w15 = confluence.tilt(book, close - FAST - SLOW, close - FAST)
    g = confluence.gc_tilt(gc, close) if gc is not None else None
    out = {"ok": None, "t5": t5, "t15": t15, "gc": g, "why": w5 or w15}
    if t5 is None or t15 is None:
        return out
    out["ok"] = (t5 <= -TILT and t15 <= TILT) if d < 0 else (t5 >= TILT and t15 >= -TILT)
    out["why"] = "trend aggression back" if out["ok"] else "no return"
    if out["ok"] and g is not None and (g >= TILT if d < 0 else g <= -TILT):
        out.update(ok=False, why="sources disagree")
    return out


def trade(d, trig, b):
    """§2 initial HARD LINE: beyond the higher (▼) / lower (▲) of the §E trigger bar's extreme and VWAP at entry by
    0.25 sigma; risk at least 0.5 sigma; sigma frozen at entry (the entry bar's)."""
    E, vw, sg = b["c"], b["vwap"], b["sig"]
    if d < 0:
        line = max(max(trig["h"], vw) + LINE_BUF * sg, E + MIN_RISK * sg)
    else:
        line = min(min(trig["l"], vw) - LINE_BUF * sg, E - MIN_RISK * sg)
    return {"E": E, "sigma": round(sg, 4), "line0": round(line, 4)}


def evaluate(ent, b3, chain, book, gc=None):
    """LOCATION / OI / FLOW at the §E ENTRY bar and the next 3 bars (<= 9 min); the RIDE entry or None.
    `chain` = confluence.chain_grid(...), `book` = confluence.book_flow(...)."""
    i, d = ent["i"], ent["d"]
    c0 = b3[i]["e"] // 60
    bars, entry = [], None
    for j in range(i, min(i + WINDOW_BARS + 1, len(b3))):
        b = b3[j]
        close = b["e"] // 60
        if close - c0 > WINDOW_MIN:
            break
        side_ok = b["c"] < b["vwap"] if d < 0 else b["c"] > b["vwap"]
        ev = {"t": frame_v2.hm(b["e"]), "loc": {"ok": side_ok, "c": b["c"], "vwap": round(b["vwap"], 2)},
              "oi": oi_read(d, chain[0], chain[1], hm(close - 1)),
              "flow": flow_read(d, book, close, gc), "late": close > CUTOFF}
        bars.append(ev)
        if entry is None and not ev["late"] and side_ok and ev["oi"]["ok"] and ev["flow"]["ok"]:
            entry = dict(trade(d, b3[i], b), t=ev["t"], bar=j - i)
    return {"bars": bars, "entry": entry}


# ---- the hold and the exit (§2): the scorer's only; never on a forward row ------------------------------------------

def flip_fut(row):
    """The READ row's FLIP in futures (with the row's own basis), or None."""
    f, bv = row.get("flip"), row.get("basis")
    return None if f is None or bv is None else f + bv


def closes_after(d, entry_close, b3, rows, chain):
    """{close minute: {"c", "flip_fut", "trend_state"}} for every 3-min close after entry up to 15:20: its close, the
    READ's FLIP in fut as of it, and the trend-side front's state at its last minute. Data at or before each close only.
    The FLIP is taken only from a READ row that still reads the trade's own direction (TREND / LEAN d): a ▲ READ's
    FLIP sits below price and is no line for a ▼ ride."""
    out = {}
    tside = "CE" if d < 0 else "PE"
    for b in b3:
        close = b["e"] // 60
        if close <= entry_close or close > MARK:
            continue
        rk = _upto(rows, b["e"])
        last = rk[-1] if rk else {}
        at = hm(close - 1)
        cut = fronts.cut(chain[0], at)
        st = None
        if not fronts.stale(cut, at):
            f = fronts.side_front(fronts.read(cut, confluence._upto(chain[1], at)), tside)
            st = f["state"] if f else None
        mine = last.get("word") in ("TREND", "LEAN") and last.get("dir") == d
        out[close] = {"c": b["c"], "flip_fut": flip_fut(last) if mine else None, "trend_state": st}
    return out


def outcome(d, tr, start, ones, closes):
    """§2: the first of the HARD LINE (intrabar, 1-min bars), SOMEBODY GAVE UP (the trend-side front UNWINDING at a
    3-min close: exit at that close), or 15:20 (the 15:19 bar's close). The line trails to FLIP + 0.25 sigma only toward
    price and never past it (a line moved through price would be a close-triggered exit). R on the initial risk.
    STALLED is stamped, never an exit. `start` = the entry close (IST minute); `closes` = closes_after(...).
    A 3-min close that falls in a 1-min hole is read at the next bar's open, never skipped. -> dict or None."""
    E, sg, line = tr["E"], tr["sigma"], tr["line0"]
    risk = abs(tr["line0"] - E)
    keys = sorted(k for k in closes if k > start)
    stalled, ex, last, q = [], None, None, 0

    def at_close(k):
        nonlocal line
        ev = closes[k]
        if ev["trend_state"] == fronts.UNWINDING:
            return ev["c"], "gave_up", hm(k)
        if ev["trend_state"] == fronts.STALLED:
            stalled.append(hm(k))
        f = ev["flip_fut"]
        if f is not None:
            cand = f + LINE_BUF * sg if d < 0 else f - LINE_BUF * sg
            if (ev["c"] < cand < line) if d < 0 else (line < cand < ev["c"]):
                line = cand
        return None

    for b in ones or ():
        m = b["s"] // 60
        if m < start or m >= MARK:
            continue
        while ex is None and q < len(keys) and keys[q] <= m:
            ex, q = at_close(keys[q]), q + 1
        if ex:
            break
        last = b
        if (b["h"] >= line) if d < 0 else (b["l"] <= line):
            ex = (line, "line", hm(m + 1))
            break
        if q < len(keys) and keys[q] == m + 1:
            ex, q = at_close(keys[q]), q + 1
            if ex:
                break
    if ex is None:
        if last is None:
            return None
        ex = (last["c"], "mark", hm(last["s"] // 60 + 1))
    R = (E - ex[0]) / risk if d < 0 else (ex[0] - E) / risk
    return {"exit": round(ex[0], 4), "how": ex[1], "exit_t": ex[2], "R": round(R, 4), "stalled": stalled}


def _chain_min(t):
    """An END time "HH:MM" -> the last chain minute inside it (the §1d stamp's minute; FADE's §5 convention)."""
    return hm(frame_v2._sec(t) // 60 - 1)


def expressions(d, minutes, entry_at, exit_at):
    """§5, equal weight: buy the with-trend ATM, buy the with-trend 1-strike ITM, sell the against-trend ATM -- the
    same strikes' RECORDED LTPs at entry and at exit (END times; read at the minute before), premium points per unit.
    Buy = exit - entry, sell = entry - exit. The scorer's only."""
    a = confluence._at_minute(minutes, _chain_min(entry_at))
    b = confluence._at_minute(minutes, _chain_min(exit_at))
    if a is None or b is None:
        return None
    k = confluence._atm_k(a)
    ks = sorted(a.get("px") or {})
    if k is None or k not in ks:
        return None
    j = ks.index(k)
    itm = ks[j + 1] if d < 0 and j + 1 < len(ks) else ks[j - 1] if d > 0 and j > 0 else None
    leg = 1 if d < 0 else 0                        # px[k] = (ce, pe): buy PE on a ▼ ride, CE on a ▲ ride
    opp = 1 - leg

    def px(rec, kk, i):
        v = (rec.get("px") or {}).get(kk)
        return None if v is None else v[i]
    out = {"k": k, "itm_k": itm, "buy": "PE" if d < 0 else "CE", "sell": "CE" if d < 0 else "PE"}
    for name, kk, i, sign in (("buy_atm", k, leg, 1), ("buy_itm", itm, leg, 1), ("sell_atm", k, opp, -1)):
        p0, p1 = (None, None) if kk is None else (px(a, kk, i), px(b, kk, i))
        out[name] = None if p0 is None or p1 is None else {"in": p0, "out": p1, "pts": round(sign * (p1 - p0), 2)}
    return out


# ---- the stamps (§1: recorded, never gating) and the forward row ------------------------------------------------------

def stamps(ent, b3, rows, tr, peers=None, dte=None):
    """§1's stamps at the §E bar (never gating): time, DTE, leg age (minutes since the READ word began), pullback depth,
    the distance to the READ's FLIP, the peers' READ words and the §1d gate (none is logged for a §E entry).

    PULLBACK DEPTH (RIDE-REVIEW MAJOR 1). ▼: pull = the §E bar's own high (the poke that made the trigger); ext = the
    lowest low of the leg's bars (from the READ's `since`) before the §E bar; start = the highest high of the leg's
    bars up to that low; depth = (pull - ext) / (start - ext) in %. ▲ mirrored. The three raw prices are stamped too,
    so any later definition can be applied without touching a write-once row.
    FLIP DISTANCE (MINOR 6): FLIP in fut minus the price it is measured from, both at the same bar -- the RIDE entry bar
    (E) when there is one, else the §E bar (its close)."""
    i, d = ent["i"], ent["d"]
    e = b3[i]["e"]
    rk = _upto(rows, e)
    last = rk[-1] if rk else {}
    since = last.get("since")
    s0 = frame_v2._sec(since) if isinstance(since, str) else None
    leg = [b for b in b3[:i] if s0 is not None and b["s"] >= s0]          # the leg's bars before the §E bar
    depth = raw = None
    if leg:
        x = min(range(len(leg)), key=lambda j: leg[j]["l"]) if d < 0 else max(range(len(leg)), key=lambda j: leg[j]["h"])
        ext = leg[x]["l"] if d < 0 else leg[x]["h"]
        start = max(b["h"] for b in leg[:x + 1]) if d < 0 else min(b["l"] for b in leg[:x + 1])
        pull = b3[i]["h"] if d < 0 else b3[i]["l"]
        raw = {"start": start, "ext": ext, "pull": pull}
        depth = None if start == ext else round((pull - ext) / (start - ext) * 100, 1)
    at, E = (frame_v2._sec(tr["t"]), tr["E"]) if tr else (e, b3[i]["c"])
    fr = _upto(rows, at)
    ff = flip_fut(fr[-1]) if fr else None
    return {"time": ent["t"], "word": ent.get("word"), "since": since, "dte": dte,
            "leg_age_min": None if s0 is None else (e - s0) // 60,
            "pullback_depth_pct": depth, "pullback": raw, "flip_dist": None if ff is None else round(ff - E, 1),
            "peers": peers, "gate": None, "gate_why": "no §1d gate is logged for §E entries"}


def row(ent, b3, rows, chain, book, gc=None, peers=None, dte=None, pullback_no=None):
    """The forward log's row (and the scorer's): everything known by the window's last close. NO OUTCOME."""
    ev = evaluate(ent, b3, chain, book, gc)
    return {"setup": "RIDE", "t": ent["t"], "d": ent["d"], "word": ent.get("word"), "px": ent.get("px"),
            "bars": ev["bars"], "entry": ev["entry"],
            "stamps": dict(stamps(ent, b3, rows, ev["entry"], peers, dte), pullback_no=pullback_no), "rev": REV}


# ---- §1k: the one look's descriptive extras -- in no rule and no bar; the scorers' look only -----------------------

def excursion(d, E, start, end, ones):
    """MFE and MAE in points from the entry close `start` to the exit `end` (IST minutes: the 1-min bars labelled
    start .. end-1), the move 30 and 60 minutes after entry in the trade's direction (the close of the 1-min bar ending
    then, whatever the exit; None without that bar, never a zero), and two sanity reads: the session's range before the
    entry and the close of the 1-min bar ending at the entry."""
    by = {b["s"] // 60: b for b in ones or ()}
    path = [by[m] for m in range(start, end) if m in by]
    pre = [b for m, b in by.items() if m < start]

    def move(n):
        b = by.get(start + n - 1)
        return None if b is None else round((E - b["c"]) if d < 0 else (b["c"] - E), 2)
    fav = [(E - b["l"]) if d < 0 else (b["h"] - E) for b in path]
    adv = [(b["h"] - E) if d < 0 else (E - b["l"]) for b in path]
    return {"mfe": round(max(fav), 2) if fav else None, "mae": round(max(adv), 2) if adv else None,
            "move30": move(30), "move60": move(60),
            "range": [min(b["l"] for b in pre), max(b["h"] for b in pre)] if pre else None,
            "close_at_entry": by[start - 1]["c"] if start - 1 in by else None}
