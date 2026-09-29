"""plan.py -- THE PLAN: STOP · NEXT RUNG · ROOM, exactly as registered.

THE SPEC is docs/hold/PLAN-PREREG.md rev 3 (sha256 b3d2c63b...5327, anchored in
context/research-findings.md §1f): rev 2a signed by the operator 2026-09-25 09:31, rev 3's
band rung (§2.7) signed 13:20 and NOT BUILT here yet -- NOT_SHOWN_LINES says so. It sits
BESIDE the hold window (hold.py, PREREG-merged rev 4 amended by PREREG-rev5.md option B)
and changes none of its rules: it reads the window's own line off hold.read's rows and the
same per-minute records. Rev 5 moves only PLAN's copy and display (its §D item 12, §A.2's
break-level line, §B's STOP after a FOLD with NEXT WALL hidden); PLAN's change-log entry
for them is owed in docs/hold/PLAN-PREREG.md.

Her decisions, verbatim, "again depends on market leave the size to me": the plan
never sizes, never says "book" or "exit", and prints the line and the window's word
side by side, never merged.

Pure: no I/O, no clock. It gates nothing; there is no order path.
"""
from __future__ import annotations

import hold

CC, NONE, NOT_SHOWN = hold.CC, hold.NONE, hold.NOT_SHOWN
NEXT = 15                    # §5 (M1): a touch's window, finished minutes, rev 4 §7's extremum
LAST = len(hold.SESSION) - 1  # 15:29
DRAFT = "DRAFT — pre-registered 2026-09-25 (docs/hold/PLAN-PREREG.md rev 3), untested; its §6 decides"
WORDS = {
    "DEFENDED": "the writers in your way are holding — against your move until they give",
    "GIVING WAY": "the writers in your way are leaving — in your favour",
    "STALLED": "the writers in your way stopped adding — neither yet",
}
RULE = {3: "the line", 4: "positioning flipped", 5: "the reason is gone", 6: "two families"}
NOT_SHOWN_LINES = [NOT_SHOWN + "a size: the plan leaves the size to you",
                   NOT_SHOWN + "a single exit: the line and the window both stand; you choose",
                   NOT_SHOWN + "the band rung (PLAN rev 3, signed 13:20) — not built yet"]
mm, hm = hold.mm, hold.hm


def _strip(why):
    return (why or "").replace(CC, "") or None


def _pts(room):
    """A stop's room in words: after a close through the line, "64 pts past it", never "-64 pts"."""
    return f"{room} pts" if room >= 0 else f"{-room} pts past it"


def word(state, fold_t=None):
    """§2.2 / §2.4: the rung's word off its §1d state; a live fold reads GIVING WAY.
    board.still_folded never holds while a front reads BUILDING, so the order is exhaustive."""
    if state == "BUILDING":
        return "DEFENDED"
    if state == "UNWINDING" or fold_t:
        return "GIVING WAY"
    return "STALLED"


def _live_fold(rec, k, side):
    return next((f["t"] for f in reversed(rec.get("folds") or [])
                 if f["side"] == side and f["k"] == k and f.get("still")
                 and 0 <= mm(rec["t"]) - mm(f["t"]) <= hold.FOLD_LIVE), None)


def risk(room, greek, role, prem_now, qty):
    """§2.1: the premium at risk if the line broke now, × qty -- [I] on the broker's [M]
    delta and gamma. A buyer: |Δ|·R − ½Γ·R², clamped 0…premium; a writer: |Δ|·R + ½Γ·R²."""
    if room is None:
        return None, CC + "the line is blind this minute"
    if not greek or greek[0] is None or greek[1] is None:
        return None, CC + "no greeks for this strike in the chain record"
    dl, g, r = abs(greek[0]), greek[1], max(room, 0)
    if role == "long":
        per = max(0.0, dl * r - 0.5 * g * r * r)
        if prem_now is not None:
            per = min(per, prem_now)
    else:
        per = dl * r + 0.5 * g * r * r
    return round(per * (qty or 0), 2), None


def rung(rec, d, close, ext):
    """§2.2: the nearest SIZED payers'-side front strictly beyond the index in her
    direction; else the session extreme `ext` if it lies beyond; else price discovery."""
    side = "PE" if d < 0 else "CE"

    def beyond(k):
        return k < close if d < 0 else k > close
    word_side = "low" if d < 0 else "high"
    if not rec.get("blind"):
        walls = [f for f in rec.get("fr") or [] if f["side"] == side and f.get("built") and beyond(f["k"])]
        if walls:
            f = min(walls, key=lambda f: abs(f["k"] - close))
            fold = _live_fold(rec, f["k"], side)
            w = word(f["state"], fold)
            return {"src": "wall", "side": side, "k": f["k"], "room": round(abs(f["k"] - close)), "word": w,
                    "favour": WORDS[w], "state": f["state"], "fold_t": fold, "tag": "M"}
        label = f"session {word_side} — no sized wall inside the nine"
    else:
        label = f"session {word_side} — the walls could not be read: {_strip(rec['blind'])}"
    if ext is not None and beyond(ext):
        return {"src": "session", "side": side, "k": ext, "room": round(abs(ext - close)), "word": None,
                "label": label, "tag": "M"}
    return {"src": "none", "side": side, "k": None, "room": None, "word": None,
            "label": "no wall in the way — price discovery", "tag": "M"}


def next15(minutes, i, d, last):
    """§5 (M1): the MAXIMUM favourable index excursion over the 15 finished minutes after
    the touch minute i, from its 1-min close; to 15:29 and flagged short. None until that
    window has finished (`last` = index of the latest finished minute)."""
    end = min(i + NEXT, LAST)
    if last < end or not minutes[i].get("ix"):
        return None
    c = minutes[i]["ix"][0]
    xs = [m["ix"] for m in minutes[i + 1:end + 1] if m.get("ix")]
    if not xs:
        return {"pts": None, "to": hold.SESSION[end], "short": i + NEXT > LAST, "tag": "M",
                "why": CC + "no index candle in the window"}
    pts = (c - min(x[2] for x in xs)) if d < 0 else (max(x[1] for x in xs) - c)
    return {"pts": round(max(pts, 0.0), 2), "to": hold.SESSION[end], "short": i + NEXT > LAST, "tag": "M"}


def read(trade, minutes, rows, greeks=None):
    """THE PLAN beside each of hold.read's `rows` (same trade, same session-aligned
    `minutes`). `greeks`: [(delta, gamma) | None] aligned to `minutes`.
    -> {"rows": [...one per hold row...], "touches": [{t, i, k, side, word, close}]}."""
    th = hold.thesis(trade["side"], trade["role"])
    d, buyer = th["d"], th["buyer"]
    at = {m["t"]: i for i, m in enumerate(minutes)}
    ext, run = [], None                          # the session extreme in her direction, 09:15 .. each minute
    for m in minutes:
        x = m.get("ix")
        if x:
            v = x[2] if d < 0 else x[1]
            run = v if run is None else (min(run, v) if d < 0 else max(run, v))
        ext.append(run)
    out, touches, touched, prev = [], [], set(), None
    for r in rows:
        i = at[r["t"]]
        m, ln = minutes[i], r["line"]
        room = None if ln.get("blind") else ln.get("room")
        g = greeks[i] if greeks and i < len(greeks) else None
        rk, why = risk(room, g, trade["role"], (r.get("prem") or {}).get("c"), trade.get("qty"))
        if room is None and not ln.get("blind") and ln.get("note"):
            why = ln["note"]                         # rev 5 §A.0.4: a mid-bar gap -- the line reads, its room could not
        af = r.get("after_fold")
        stop = {"L": ln.get("L"), "room": room, "risk": rk, "risk_why": why, "tag": "M", "risk_tag": "I",
                # rev 5 §D item 12 (PLAN §3's sentence): measured to L, never an exit, no break rule named
                "text": f"≈ ₹{rk:,.0f} [I] of premium between here and the line" if rk is not None else why,
                "level": ln.get("level"), "level_text": ln.get("print"),      # rev 5 §A.2: the break level, its own line
                # rev 5 §B: after a FOLD the STOP shows the line that broke; plan.stop.L above keeps the trailed L
                "after_fold": af and {"L": af["L"], "text": af["text"], "detail": af["detail"]}}
        win = f"the window: {r['verdict']}" + (f" · {RULE[r['fold_rule']]}" if r.get("fold_rule") else "") + \
              f" · since {r['since']}"
        exits = {"line": f"the line: {ln['L']:,.1f}, {_pts(room)}" if room is not None else "the line: could not check",
                 "window": win}
        if not buyer:
            out.append({"t": r["t"], "stop": stop, "rung": None, "room": None, "touch": None, "exits": exits})
            continue
        ix = m.get("ix")
        rg = rung(m, d, ix[0], ext[i]) if ix else {"src": "none", "side": "PE" if d < 0 else "CE", "k": None,
                                                    "room": None, "word": None, "tag": "M",
                                                    "label": CC + f"no index candle at {r['t']}"}
        touch = None
        if prev and prev["src"] in ("wall", "session") and ix and prev["k"] is not None:
            reached = ix[2] <= prev["k"] if d < 0 else ix[1] >= prev["k"]
            key = (prev["k"], prev["side"] if prev["src"] == "wall" else "session")
            if reached and key not in touched:
                touched.add(key)
                if prev["src"] == "wall":
                    f = next((f for f in m.get("fr") or [] if f["k"] == prev["k"] and f["side"] == prev["side"]), None)
                    w = word(f["state"], _live_fold(m, prev["k"], prev["side"])) if f else prev["word"]
                    touch = {"k": prev["k"], "side": prev["side"], "word": w, "favour": WORDS[w],
                             "read": "at the touch minute" if f else "as last read — not in the top 2 this minute"}
                    touches.append({"t": r["t"], "i": i, "close": ix[0], **touch})
                else:                            # §2.4: printed, never counted
                    touch = {"session": True, "text": f"session {'low' if d < 0 else 'high'} touched — no wall read there"}
        rr = rg.get("room")
        note = ((f"no wall in the way — the stop is {room} pts behind you" if room >= 0 else
                 f"no wall in the way — the index is {-room} pts past the line") if rg["src"] == "none" and room is not None else
                "you risk more points to the line than the next rung is away" if rr is not None and room is not None
                and rr < room else None)
        out.append({"t": r["t"], "stop": stop, "rung": rg, "touch": touch, "exits": exits,
                    # §B: only once she is out; while the trade is open the rung above IS the next wall
                    "next_wall": NOT_SHOWN + "the next wall — the plan ended at the FOLD" if af and trade.get("exit_t") else None,
                    "room": {"rung": rr, "stop": room, "text": f"rung {rr if rr is not None else '—'} pts · stop "
                                                              f"{_pts(room) if room is not None else '— pts'}", "note": note}})
        prev = rg
    return {"rows": out, "touches": touches}
