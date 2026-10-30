"""palat.py -- TOP / BOTTOM BAN SAKTA (NOTEPAD A130 / A131): her GoCharting footprint P at the swing extreme, counted
against four confirmations; at 3 of 4 one SETUP line for the message stream and Telegram.

Mary, 28 Oct: "send TOP/BOTTOM BAN SAKTA to Telegram when the P mark has 3 of 4 confirmations (zone armed, band stretch,
handshake exhaustion, fut OI flat)".

THE P: the extension's "trap" mark (tape_log.read_marks); side +1 = buyers trapped -> TOP (fade side SELL), -1 =
sellers trapped -> BOTTOM (BUY). At the extreme by the Trade tab's own test (ui-v2/src/trade/TradeTab.tsx:229-236): the
<= 12 GoCharting bars already closed at the P's t (at least 3), tol = max(2 x rowSize, 0.25 x their range); a TOP within
tol of their highest high, a BOTTOM of their lowest low. Anywhere else it is a "chhota trap" and never alerts.
THE CLOSE c = the P's bar close (its t + 5 min). Every read below uses only data at or before c (a minute m of the
chain grid, the Dext candles or the book is known at m + 1).
THE FOUR, each True / False / None (could not check: a missing input is never False):
  zone    DECODE's ZONE chip on the fade side ARMED / MATCH at c, or a zone-machine arm / entry row (trigger_log rule
          "zone") on that side whose 3-min bar closed in the 15 min to c
  band    the P at or beyond the session VWAP +/- 2 sigma on the extreme's side: faded.vwaps + hold2.sigmas (market.js
          vwapSeries, the recurrence the extension's rings use) on the GoCharting 5-min bars closed by c [M]; before
          30 min of bars (6) it cannot say (22 Sep 09:30 read -20 sigma off three bars)
  thakan  the latest same-direction PUSH in the 15 min to c whose answer is known by c got NO answer or a TIKI, after a
          same-direction push in the 30 min before it that WAS answered (TOOT / PHANS): A129's sequence, the force had
          been cutting walls and now gets nothing (a lone NAHI is the base rate at any extreme, Fable S4); or the
          other side's WRITERS at the EXTREME strike (nearest the P in spot: the P minus the 3-min basis) added
          >= max(3L, 4 % of its OI) in the 10 min to c, opened by writers (premium under what delta explains, Fable
          CRITIQUE M4), and the biggest 10-min add at that strike so far today (Fable's review 28 Oct: "the other side
          wrote >= 3L" alone was ordinary ATM writing, true on 102 of 127 rows)
  fut OI  no FRESH positions behind the move: the futures OI over the 15 min to c FLAT (|change| < onesided.OI_PCT,
          its fut_oi vote) or COVER (fell); FRESH (rose while spot moved into the extreme) is the one failure. The
          book record's "oi"
TREND-DAY GUARD: on a §1o TREND against the call (a TOP on TREND ▲, a BOTTOM on TREND ▼) it needs 4 of 4 and says
"trend din: khatra" (1 Oct 12:30 and 19 Oct 11:45, Fable's review). NIFTY only (no other index has P marks). A day
budget: the first BUDGET alerts of an index go to Telegram, the rest to the window only (`budget`).
PUSH / ANSWER are Fable's validated handshake, ONE copy in handshake.py (A132; export_v2.py, CRITIQUE.md M1-M5): the 1-min fut
delta in lots from the near-month Dext candles (the max total_volume row per minute; the contract is the book record's
own `ik`), else the Upstox 1-second book by the quote rule; a PUSH is a 2-min delta >= 2x the median |2-min delta| of
the 30 min before and >= MIN_PUSH lots, >= 4 min after the last push its way; the ANSWER is the attacked strike's OI
(the biggest ABSOLUTE OI in the push's band) 4 min later: TOOT (cut >= bar), PHANS (added, price through), TIKI (added,
price held), NAHI. SENSEX reads NIFTY's flow (§1q, sensex_flow.on) and its own chain and futures OI. OI moves are read
off the absolute `oi`, never `oi_chg` (A125: a leg with no 09:15 baseline stored oi_chg 0 all morning on 27 Oct).
DISPLAY ONLY: gates nothing, no order path; a COUNT n/4, never a %. Every threshold is [I]. Pure except `load`.
"""
from __future__ import annotations

import math
import statistics

import faded
import handshake
import hold2
import messages
import onesided
# the handshake lives ONCE in handshake.py (A132, the §1d lesson): palat reads it from there
from handshake import (ANSWER, CUT_FRAC, CUT_L, MIN_PUSH, NORM, PUSH_X, QUIET, THROUGH, TICK, _l, _last, _leg,  # noqa: F401
                       _ks, _sg, _step, book_flow, chain_minutes, dext_flow, flow, hm, mod, pushes)

IV = 5                                    # GoCharting's bar, minutes
SWING_N, SWING_MIN, ROW_X, RANGE_X = 12, 3, 2, 0.25           # TradeTab.tsx:229-236
ZONE_WIN, ZONE_IV = 15, 3                 # arm rows in the 15 min to c; the zone machine's 3-min bar
SIGMA_X = 2.0
HS_WIN = 15                               # export_v2.py (NORM, PUSH_X, ANSWER, QUIET: handshake.py)
PRE_WIN = 30                              # the answered push before the unanswered one (A129's sequence)
WRITE_WIN = 10                            # (CUT_L, CUT_FRAC, THROUGH, TICK: handshake.py)
BAND_BARS = 6                             # 30 min of 5-min bars before a sigma is read
FUT_WIN = 15
BUDGET = 3                                # BAN SAKTA lines a day per index that go to Telegram
# The switch (28 Oct): the replay (docs/speed/alerts/REPLAY.md) still passes 1 Oct 12:30 (-100), 24 Sep 13:30 (-94) and 19 Oct
# 11:45 (-64), so BAN SAKTA starts on the SCREEN only (the message window) and is judged on forward days; True sends it to Telegram.
TELEGRAM_ON = False
IDXS = ("NIFTY",)                         # the indices with P marks (her GoCharting chart)
NEED = 4 - 1                              # 3 of 4
LATE = 15 * 60                            # her practice: no new trades after 15:00 (a reminder, never a gate)
NAME = {1: ("TOP", "▼", "SELL", -1), -1: ("BOTTOM", "▲", "BUY", 1)}   # P side -> (swing, arrow, fade side, message dir)
ORDER = ("zone", "band", "thakan", "fut")


# ---- the P and the swing test --------------------------------------------------------------------------------------

def traps(marks):
    """Her P marks (kind trap, a side, a price, a time), oldest first, ONE per bar and side: the extension re-posts a P a
    tick apart (30 Sep 10:05: 22,865 and 22,866), and that is one trap, kept at its most extreme price."""
    one = {}
    for m in marks or ():
        if (isinstance(m, dict) and m.get("kind") == "trap" and m.get("side") in (1, -1)
                and isinstance(m.get("p"), (int, float)) and isinstance(m.get("t"), (int, float))):
            k = (m["t"], m["side"])
            if k not in one or m["side"] * (m["p"] - one[k]["p"]) > 0:
                one[k] = m
    return sorted(one.values(), key=lambda m: (m["t"], m["p"]))


def close(P):
    return mod(P["t"]) + IV


def pid(P):
    """The P's identity for the write-once key: its bar and its side (traps keeps one per pair)."""
    return f"P{int(P['t'])}{'+' if P['side'] > 0 else '-'}"


def _prior(P, bars):
    t = mod(P["t"])
    return [b for b in bars if mod(b["t"]) + IV <= t][-SWING_N:]


def swing(P, bars, row):
    """'TOP' / 'BOTTOM' at the extreme of the <= 12 bars closed at the P's t, else None (TradeTab.tsx:229-236)."""
    prior = _prior(P, bars)
    if len(prior) < SWING_MIN:
        return None
    hi, lo = max(b["h"] for b in prior), min(b["l"] for b in prior)
    tol = max(ROW_X * row, RANGE_X * (hi - lo))
    if P["side"] > 0:
        return "TOP" if hi - P["p"] <= tol else None
    return "BOTTOM" if P["p"] - lo <= tol else None


# ---- the handshake's answer, as palat reads it (A131: the fixed 4-min minute) -----------------------------------

def answer(R, ms, p, upto):
    """handshake.answer read at the 4-min minute only (first=False), the shape palat's A131 replay was built on:
    {"ans", "k", "chg", "bar"} or None. The real-time first crossing (A129) is handshake's own default."""
    a = handshake.answer(R, ms, p, upto, first=False)
    return None if a is None else {x: a[x] for x in ("ans", "k", "chg", "bar")}


# ---- the four ---------------------------------------------------------------------------------------------------------

def zone(fade, c, row, zrows):
    """(ok, chip): DECODE's ZONE chip on the fade side ARMED / MATCH at c, or a zone row on that side whose 3-min bar
    closed in the ZONE_WIN min to c. False when DECODE's row at c or a zone row of the day says the machine was read."""
    hits = [z for z in zrows or () if z.get("side") == fade and isinstance(z.get("t"), str)
            and c - ZONE_WIN <= _hm2m(z["t"]) and _hm2m(z["t"]) + ZONE_IV <= c]
    chip = next((s for s in (row or {}).get("setups") or () if s.get("name") == "ZONE" and s.get("side") == fade), None)
    if hits:
        z = hits[-1]
        if z.get("kind") == "arm" and isinstance(z.get("level"), (int, float)):
            return True, f"zone {fade} armed {z['level']:,.0f}s"
        if isinstance(z.get("px"), (int, float)):
            return True, f"zone {fade} trigger {z['px']:,.0f}s"
        return True, f"zone {fade} {z['t']}"
    if chip and chip.get("state") in ("ARMED", "MATCH"):
        return True, f"zone {fade} {str(chip['state']).lower()}"
    if row is not None or any(_hm2m(z["t"]) + ZONE_IV <= c for z in zrows or () if isinstance(z.get("t"), str)):
        return False, f"zone {fade} nahi"
    return None, "zone"


def _hm2m(t):
    h, m = str(t).split(":")[:2]
    return int(h) * 60 + int(m)


def band(P, d, bars, c):
    """(ok, chip): the P against the session VWAP +/- 2 sigma of the GoCharting bars closed by c."""
    closed = [b for b in bars if mod(b["t"]) + IV <= c]
    if len(closed) < BAND_BARS or mod(closed[0]["t"]) != 555:  # VWAP is the session's, and needs 30 min to mean anything
        return None, "σ"
    vw, sg = faded.vwaps(closed)[-1], hold2.sigmas(closed)[-1]
    if vw is None or not sg:
        return None, "σ"
    z = (P["p"] - vw) / sg
    shown = math.trunc(z * 10) / 10                           # cut, never rounded up: a 1.96 must not read "+2σ ✗"
    return (z >= SIGMA_X if d > 0 else z <= -SIGMA_X), _sg(f"{shown:+g}σ")


who = handshake.who_opened                # export_v2.who, Fable CRITIQUE M4 (one copy)


def _add(R, ms, k, side, b):
    """(a, OI added at k over the WRITE_WIN min to chain minute b, in L); a or the add None when stale or missing."""
    a = _last(ms, b - WRITE_WIN)
    if a is None or a < b - WRITE_WIN - 5:
        return None, None
    o0, o1 = _leg(R[a], k, side).get("oi"), _leg(R[b], k, side).get("oi")
    return (a, None) if o0 is None or o1 is None else (a, (o1 - o0) / 1e5)


def writers(d, c, pspot, R, ms):
    """(ok, chip): the other side's writers at the extreme strike in the WRITE_WIN min to c -- the add >= max(3L, 4 % of
    the strike's OI), opened by WRITERS (`who`), and the biggest 10-min add at that strike so far today."""
    other, nm = ("pe", "put") if d > 0 else ("ce", "call")
    b = _last(ms, c - 1)
    ks = _ks(R[b]) if b is not None else []
    if b is None or b < c - 3 or pspot is None or not ks:
        return None, f"{nm} likhai ?"
    k = min(ks, key=lambda k: abs(k - pspot))
    a, add = _add(R, ms, k, other, b)
    if add is None:
        return None, f"{nm} likhai ?"
    head = f"{nm} {k:,.0f} {_l(add)}"
    if add < max(CUT_L, CUT_FRAC * (_leg(R[a], k, other).get("oi") or 0) / 1e5):
        return False, head
    earlier = [x for x in (_add(R, ms, k, other, j)[1] for j in ms if j <= a) if x is not None]   # windows before this one
    if earlier and add < max(earlier):
        return False, head + " · aaj ka max nahi"
    w = who(R[a], R[b], k, other)
    if w is None:
        return None, head + " · kaun ?"
    if w != "WRITERS":
        return False, head + (" · kharidar" if w == "KHAREEDAR" else " · kaun saaf nahi")
    return True, f"{nm} writers {k:,.0f} {_l(add)} · aaj ka max"


def basis(px, R, ms, c):
    """fut minus spot: the median over the last 3 chain minutes to c with a fut price (A60's 3-min median), or None."""
    xs = [px[m] - R[m]["spot"] for m in ms if c - 3 <= m <= c - 1 and m in px]
    return statistics.median(xs) if xs else None


def thakan(d, c, pspot, R, ms, F, pushes_, of=""):
    """(ok, chip): the latest same-direction push in HS_WIN min to c with its answer known by c got NAHI / TIKI, or the
    other side's writers at the extreme strike (`writers`; pspot = the P in spot).
    `of`: "NIFTY " when the flow is NIFTY's (SENSEX, §1q), so the push says whose it is."""
    parts, oks = [], []
    ps = [p for p in pushes_ if p["dir"] == d and c - HS_WIN <= p["m"]]
    known = [(p, a) for p, a in ((p, answer(R, ms, p, c)) for p in ps) if a is not None]
    seen = sum(1 for m in range(c - HS_WIN, c) if m in F)
    warm = sum(1 for m in range(c - HS_WIN - NORM, c - HS_WIN) if m in F)
    if seen < HS_WIN // 2 or warm < 10 or _last(ms, c - 1) is None or _last(ms, c - 1) < c - 3:
        oks.append(None)                                      # no flow, or too little before the window to see a push
        parts.append(f"{of}push ?")
    elif not known:
        oks.append(False)
        parts.append(f"{of}push nahi")
    else:
        p, a = known[-1]
        w = {"NAHI": "jawab nahi", "TIKI": f"deewar tiki {_l(a['chg'])}", "TOOT": f"toot {_l(a['chg'] or 0)}",
             "PHANS": f"phans {_l(a['chg'] or 0)}", None: "jawab ?"}[a["ans"]]
        lots = _sg(f"{p['lots']:+,}")
        chip = f"{of}push {hm(p['m'])} {lots} {w}"
        ok = None if a["ans"] is None else a["ans"] in ("NAHI", "TIKI")
        if ok:                    # A129's sequence: the force had been cutting walls (TOOT / PHANS), now it gets nothing
            before = [(q, answer(R, ms, q, c)) for q in pushes_ if q["dir"] == d and p["m"] - PRE_WIN <= q["m"] < p["m"]]
            hit = next(((q, qa) for q, qa in reversed(before) if qa and qa["ans"] in ("TOOT", "PHANS")), None)
            if hit is None:
                ok, chip = False, chip + " · pehle koi toot nahi"
            else:
                q, qa = hit
                chip = f"{of}push {hm(q['m'])} {qa['ans'].lower()} {_l(qa['chg'])} → {chip[len(of) + 5:]}"
        oks.append(ok)
        parts.append(chip)
    w_ok, w_chip = writers(d, c, pspot, R, ms)
    oks.append(w_ok)
    parts.append(w_chip)
    if True in oks:
        return True, " + ".join(x for x, o in zip(parts, oks) if o)
    return (None if None in oks else False), " · ".join(parts)


def fut_oi(oi, c, lot, d=1, R=None, ms=()):
    """(ok, chip): no FRESH positions behind the move over FUT_WIN min to c; oi = [(t ms, oi)] in time order. FLAT
    (|change| < onesided.OI_PCT) and COVER (fell) pass; FRESH (rose while spot moved the move's way d, into the extreme)
    fails; risen while spot went the other way is fresh AGAINST the move and passes ("fresh ulta")."""
    def at(m):
        x = [(mod(t), v) for t, v in oi if mod(t) <= m]
        return x[-1] if x else (None, None)
    (m0, o0), (m1, o1) = at(c - 1 - FUT_WIN), at(c - 1)
    if not o0 or not o1 or m0 < c - 1 - FUT_WIN - 5 or m1 < c - 3:
        return None, "fut OI"
    lots = _sg(f"{round((o1 - o0) / lot):+,} lots")
    if abs(o1 - o0) / o0 * 100 < onesided.OI_PCT:
        return True, f"fut OI flat {lots}"
    if o1 < o0:
        return True, f"fut OI cover {lots}"
    s0, s1 = spot_at(R, ms, c - 1 - FUT_WIN), spot_at(R, ms, c - 1)
    if s0 is not None and s1 is not None and d * (s1 - s0) < 0:
        return True, f"fut OI fresh ulta {lots}"
    return False, f"fut OI fresh {lots}"


def spot_at(R, ms, m):
    j = _last(ms, m) if R else None
    return None if j is None else R[j]["spot"]


# ---- the judgement and its line ---------------------------------------------------------------------------------------

def judge(idx, P, inp, row):
    """One P against the four at its close. `inp` = load(); `row` = DECODE's row at the close (its "T" = hm(c)) or None.
    -> {"P", "c", "swing", "checks": {name: [ok, chip]}, "n", "unk", "msg" (the SETUP message at n >= NEED, else None)}"""
    c = close(P)
    sw = swing(P, inp["bars"], inp["row"])
    out = {"P": P, "c": c, "swing": sw, "checks": {}, "n": 0, "unk": 0, "msg": None}
    if sw is None:
        return out
    d, fade = P["side"], NAME[P["side"]][2]
    R, ms = inp["R"], inp["ms"]
    bs = basis(inp.get("px") or {}, R, ms, c)
    pspot = None if bs is None else P["p"] - bs                # the P in spot: its extreme strike is the nearest one
    ck = {"zone": zone(fade, c, row, inp["zone"]), "band": band(P, d, inp["bars"], c),
          "thakan": thakan(d, c, pspot, R, ms, inp["F"], inp["pushes"],
                           "NIFTY " if inp.get("flow_of", idx) != idx else ""),
          "fut": fut_oi(inp["oi"], c, inp["lot"], d, R, ms)}
    ty = ((row or {}).get("onesided") or {}).get("type")
    against = isinstance(ty, str) and ty.startswith("TREND") and ("▲" in ty) == (d > 0)   # TOP on TREND ▲, BOTTOM on ▼
    out["checks"] = {k: list(v) for k, v in ck.items()}
    out["n"] = sum(ck[k][0] is True for k in ORDER)
    out["unk"] = sum(ck[k][0] is None for k in ORDER)
    out["need"] = 4 if against else NEED
    if out["n"] >= out["need"]:
        out["msg"] = message(idx, P, c, sw, ck, out["n"], ty, against)
    return out


def message(idx, P, c, sw, ck, n, ty, against=False):
    """The SETUP line: "{idx} TOP BAN SAKTA ▼ 3/4 · P 22,840f · <the four> · din ... [· trend din: khatra] [· 3 baje ke
    baad]". A check not true says so: "✗ ..." checked and not met, "? ..." could not check. Keyed per P (its bar and
    side), never per count, so a later pass or a restart never says it twice."""
    name, arrow, fade, d = NAME[P["side"]]
    chips = [ck[k][1] if ck[k][0] is True else ("✗ " if ck[k][0] is False else "? ") + ck[k][1] for k in ORDER]
    level = " · ".join([f"P {P['p']:,.0f}f"] + chips + [messages.din_line(ty, fade)]
                       + (["trend din: khatra"] if against else []) + (["3 baje ke baad"] if c >= LATE else []))
    m = messages._msg(hm(c), idx, "SETUP", d, f"{name} BAN SAKTA {arrow} {n}/4", None, level,
                      f"footprint P {hm(mod(P['t']))} at {P['p']:,.0f}f, read to the {hm(c)} close", ev="PALAT", n=n)
    m["key"] = messages.key(dict(m, word=f"{name} BAN SAKTA {arrow}", id=pid(P)))
    return m


def budget(msgs):
    """The day's BAN SAKTA lines, in time order: per index the first BUDGET go to Telegram, the rest are written to the
    window only (`quiet`, which telegram_out.wants honours) and say so. Deterministic from the P's, so a restart quiets the
    same ones."""
    seen, out = {}, []
    for m in sorted(msgs, key=lambda m: (m["t"], m["key"])):
        seen[m["idx"]] = seen.get(m["idx"], 0) + 1
        if not TELEGRAM_ON:
            m = dict(m, quiet=True, level=f"{m['level']} · screen par · Telegram band (parakh rahe)")
            m["line"] = messages.line(m)
        elif seen[m["idx"]] > BUDGET:
            m = dict(m, quiet=True, level=f"{m['level']} · Telegram nahi: aaj ke {BUDGET} ho gaye")
            m["line"] = messages.line(m)
        out.append(m)
    return out


# ---- I/O: the record files, the same live and in a replay (anytime-start) -------------------------------------------

def load(day, idx):
    """Everything `judge` reads for (day, idx) from the record: GoCharting bars, the chain grid, the flow (Dext of the
    book's own contract, else the book; SENSEX: NIFTY's, §1q), the pushes, the futures OI (the index's own book), the
    zone rows. Read whole, once per pass with a P to judge."""
    import book_log
    import confluence_log
    import tape_log
    import v2feed
    bars = sorted((b for b in tape_log.read_bars(day, idx) if tape_log.bar_t(b) is not None
                   and isinstance(b.get("h"), (int, float)) and isinstance(b.get("l"), (int, float))), key=lambda b: b["t"])
    R = chain_minutes(confluence_log._rows(confluence_log._chain_path(idx, day)))
    ms = sorted(m for m in R if 555 <= m <= 930)
    fi, flot, brows, F, src = handshake.load_flow(day, idx)     # the book's own contract's Dext, else the book (one copy)
    own = brows if fi == idx else list(book_log.read_rows(day, idx))
    oi = sorted((r["t"], r["oi"]) for r in own if isinstance(r.get("oi"), (int, float)) and r["oi"] > 0)
    px = {mod(t): x for t, x in sorted((r["t"], r["ltp"]) for r in own if isinstance(r.get("ltp"), (int, float)))}
    return {"bars": bars, "row": float((bars[0].get("rowSize") if bars else None) or 5), "R": R, "ms": ms, "F": F,
            "src": src, "pushes": pushes(F, ms, MIN_PUSH.get(fi, MIN_PUSH["NIFTY"])), "oi": oi, "px": px,
            "lot": v2feed.LOTS.get(idx) or 1, "zone": confluence_log.zone_rows(idx, day),
            "marks": traps(tape_log.read_marks(day, idx)), "flow_of": fi}
