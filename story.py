# tapemap/story.py
"""story.py -- the decoder's one sentence, the day as chapters, the decoder's count beside her trade, and the out-of-the-
ordinary highlights, for the GoCharting panel, the Float and the DESK (Fable, docs/reader/FABLE-DECODER-DESIGN-2026-10-04.md
§2.6; orderflow-desk docs/PANEL-DESIGN-2026-10-04/DESIGN.md §2-§4, §7).

ONE DEFINITION. The events are the GoCharting extension's (orderflow-desk src/engine/decoder.js), posted with every tape
as `tape["decoder"]` (schema v1: id, kind, t, p, side, lots, trades, at, oi{state,doi,net,step}, quad, split, state,
state_t, chip, chips, en, tests, med_range; plus `per`, one OI word per closed bar). This module READS their fields and
never re-derives an event, a threshold or a state. The trap layer's state stamps (trap.py) and the sides-3 slots
(sides.py) are read the same way, as the server already publishes them. What this module adds is composition only:
where price is now against an open print, which events fall in which chapter, which of them are for or against her
trade's direction, and which of them happened in the last three minutes.

THE ENGINE'S WORD IS NOT TOUCHED. `trade_read` is the decoder's count of evidence for / against her side, labelled as the
decoder's read; HOLD / PAST GIVE-UP / FOLD stay fold.py's (P1-P7 are unsigned). Counts, never a percentage, never odds.

Pure, stdlib only, no I/O, no clock: `now_ms` is handed in. Every number is the event's own [M] (lots, price, trades, OI
on the bar) or [I] (direction words, chapter names, the count) and the objects say so in `tag`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

KINDS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7")
BAR_MS = 300000
HOLD_MS = 180000                    # a highlight stays 3 minutes (her ask, 2026-10-04) ...
FADE_MS = 20000                     # ... then fades out over 20 s (`fading`), never a blink
IST = timezone(timedelta(hours=5, minutes=30))
STATE_HI = {"REACHED": "PAHUNCHA", "DWELL": "RUKA", "INDUCED": "TOOTA", "FAILED": "FAILED", "RELEASED": "CHHOOTA",
            "TRAVELLING": "CHAL PADA"}
_EMPTY = {"sentence": None, "sentence_why": "no decoder event yet", "chips": [], "event": None, "asof": None,
          "open_prints": 0, "tag": {"M": ["lots", "p", "trades", "oi.doi", "fut"], "I": ["state", "quad", "split"]}}


def _px(p: float) -> str:
    return f"{round(p):,}"


def _hm(ms: Optional[int]) -> str:
    return "" if ms is None else datetime.fromtimestamp(ms / 1000, IST).strftime("%H:%M")


def day_ms(day: str, hhmm: str) -> Optional[int]:
    """'HH:MM[:SS]' on `day` (IST) -> epoch ms; None for anything unreadable."""
    try:
        y, m, d = map(int, day.split("-"))
        parts = [int(x) for x in str(hhmm).split(":")]
        return int(datetime(y, m, d, parts[0], parts[1], parts[2] if len(parts) > 2 else 0, tzinfo=IST).timestamp() * 1000)
    except (ValueError, TypeError, IndexError, AttributeError):
        return None


def _events(dec: Optional[dict]) -> List[dict]:
    if not isinstance(dec, dict) or dec.get("v") != 1:
        return []
    return [e for e in dec.get("events") or [] if isinstance(e, dict) and e.get("kind") in KINDS and e.get("t") is not None]


def compose(dec: Optional[dict], fut: Optional[float] = None) -> dict:
    """The sentence for the event that matters most now: the newest print still waiting for its exit (an open level),
    else the newest event the page drew (shown). None, with its reason, when the page sent no decoder or nothing yet."""
    out = dict(_EMPTY)
    if not isinstance(dec, dict):
        return {**out, "sentence_why": "the extension sent no decoder (it predates 0.4.0)"}
    if dec.get("v") != 1:
        return {**out, "sentence_why": f"decoder schema {dec.get('v')!r} is not the one this server reads (1)"}
    evs = [e for e in _events(dec) if e.get("en")]
    open_prints = [e for e in evs if e["kind"] == "E1" and e.get("state") == "BAAKI"]
    shown = [e for e in evs if e.get("shown")]
    top = (sorted(open_prints, key=lambda e: e.get("t") or 0) or sorted(shown, key=lambda e: e.get("t") or 0) or [None])[-1]
    if top is None:
        return {**out, "sentence_why": "no decoder event yet today" if not evs else "no event at her ring or a level yet"}
    s = top["en"]
    if top["kind"] == "E1" and top.get("state") == "BAAKI" and fut is not None and top.get("p") is not None:
        d = round(float(fut) - float(top["p"]), 1)
        s += f"; price now {abs(d):g} pts {'above' if d > 0 else 'below' if d < 0 else 'at'} his price"
    others = [e for e in open_prints if e is not top]
    if others:
        s += "; also open: " + ", ".join(f"{'buyer' if e.get('side', 0) > 0 else 'seller'} {_px(e['p'])}" for e in others[-2:])
    return {**out, "sentence": s, "sentence_why": None, "chips": list(top.get("chips") or [top.get("chip")])[:3],
            "event": {"id": top.get("id"), "kind": top["kind"], "state": top.get("state"), "t": top.get("t"), "p": top.get("p"), "side": top.get("side")},
            "asof": top.get("time"), "open_prints": len(open_prints)}


# ---- THE DAY AS CHAPTERS (DESIGN §3) ---------------------------------------------------------------------------------
def _trap_rows(trap: Optional[dict], day: str) -> List[dict]:
    """The trap layer's state stamps for this index as {t_ms, level, px, state, dir, src}, oldest first."""
    rows, last_dir = [], {}
    for e in sorted(((trap or {}).get("events") or []), key=lambda r: str(r.get("t"))):
        if e.get("kind") != "state" or e.get("state") not in STATE_HI:
            continue
        t = day_ms(day, str(e.get("t")))
        if t is None:
            continue
        key = (e.get("level"), e.get("px"))
        d = e.get("dir")
        d = 1 if d in ("UP", 1, "1") else -1 if d in ("DOWN", -1, "-1") else None
        if e["state"] == "INDUCED" and d is not None:
            last_dir[key] = d
        if e["state"] == "FAILED":
            d = last_dir.get(key)                    # a failed break traps the side that broke
        rows.append({"t_ms": t, "level": e.get("level"), "px": e.get("px"), "state": e["state"], "dir": d,
                     "src": e.get("src") or "live"})
    return rows


def _trap_name(r: dict) -> str:
    lvl = f"{r['level']} {_px(r['px'])}" if r.get("px") is not None else str(r.get("level"))
    if r["state"] == "FAILED":
        who = {1: " · buyers phanse", -1: " · sellers phanse"}.get(r.get("dir"), "")
        return f"FAIL · {lvl}{who}"
    if r["state"] in ("INDUCED", "RELEASED", "TRAVELLING") and r.get("dir"):
        return f"{STATE_HI[r['state']]} {'▲' if r['dir'] > 0 else '▼'} · {lvl}"
    return f"{STATE_HI[r['state']]} · {lvl}"


def _price_at(closed: List[dict], t_ms: int) -> Optional[float]:
    """The last close at or before t (a bar closes at t + 5 min); the first open before the first close."""
    px = None
    for b in closed:
        if b.get("t") is None or b.get("c") is None:
            continue
        if b["t"] + BAR_MS <= t_ms:
            px = b["c"]
        elif px is None and b.get("o") is not None:
            px = b["o"]
    return px


def chapters(dec: Optional[dict], closed: List[dict], day: str, trap: Optional[dict] = None, slots: Optional[list] = None,
             logged: Optional[List[dict]] = None, now_ms: Optional[int] = None) -> dict:
    """The WHOLE day from the first bar, as chapters, the current one last (DESIGN §3). A chapter opens on a trap state
    change at a level (FAILED / INDUCED / RELEASED strongest; DWELL; REACHED / TRAVELLING weakest), on a BADA PRINT (E1),
    or on a confirmed CVD ulta (E7); with no trap stamps, an event the page drew at her ring or a level stands in. It
    closes when the next opens. ANYTIME-START: events the page did not post this time but the decoder log kept are folded
    in, tagged src "log"; trap stamps rebuilt by a restart keep their own src "backfill"."""
    evs = {e["id"]: dict(e, src="live") for e in _events(dec) if e.get("id")}
    for e in logged or []:
        if isinstance(e, dict) and e.get("id") and e["id"] not in evs and e.get("kind") in KINDS:
            evs[e["id"]] = dict(e, src="log")
    ev = sorted(evs.values(), key=lambda e: e["t"])
    bars = sorted((b for b in closed or [] if b.get("t") is not None), key=lambda b: b["t"])
    trows = _trap_rows(trap, day)
    if not bars and not ev and not trows:
        return {"items": None, "items_why": "no bar and no event yet today", "n": 0}     # None, never [], beside a why
    start0 = bars[0]["t"] if bars else (day_ms(day, "09:15") or ev[0]["t"])
    pdc = next((q.get("p") for q in ((dec or {}).get("priors") or []) if q.get("kind") == "PDC"), None)
    roll = bool((dec or {}).get("roll"))           # yesterday's close is another contract: no gap to name
    gap = round(bars[0]["o"] - pdc) if bars and bars[0].get("o") is not None and pdc is not None and not roll else None
    op = [{"t": start0, "s": 3, "name": "SHURU" + (f" · gap {gap:+d}" if gap is not None else " · contract roll" if roll else ""), "chip": None, "side": 0,
           "en": None, "src": "live", "first": True}]
    for e in ev:
        close = e["t"] + BAR_MS
        if e["kind"] == "E1":
            k = (e.get("chips") or [e.get("chip")])[0]
            op.append({"t": close, "s": 4, "name": k, "chip": e.get("chip"), "side": e.get("side") or 0, "en": e.get("en"),
                       "src": e["src"], "id": e["id"]})
        elif e["kind"] == "E7" and e.get("state") == "CONFIRMED":
            op.append({"t": close, "s": 2, "name": e.get("chip"), "chip": e.get("chip"), "side": e.get("side") or 0,
                       "en": e.get("en"), "src": e["src"], "id": e["id"]})
    for r in trows:
        s = 3 if r["state"] in ("FAILED", "INDUCED", "RELEASED") else 2 if r["state"] == "DWELL" else 1
        side = (r["dir"] or 0) * (-1 if r["state"] == "FAILED" else 1)
        op.append({"t": r["t_ms"], "s": s, "name": _trap_name(r), "chip": f"{_trap_name(r)} {_hm(r['t_ms'])}", "side": side,
                   "en": f"{r['level']} {r['state'].lower()} at {_hm(r['t_ms'])}", "src": r["src"]})
    if True:                                        # the page's own drawn events at a level open a chapter too, weakest:
        for e in ev:                                # a 2-hour stretch with no trap stamp is still a story (1 Oct 10:00-12:10)
            if e["kind"] in ("E2", "E3", "E4") and e.get("shown") and e.get("at"):
                op.append({"t": e["t"] + BAR_MS, "s": 1, "name": e.get("chip"), "chip": e.get("chip"), "side": e.get("side") or 0,
                           "en": e.get("en"), "src": e["src"], "id": e["id"]})
    op.sort(key=lambda x: (x["t"], -x["s"]))
    gapms = {4: BAR_MS, 3: BAR_MS, 2: 3 * BAR_MS, 1: 6 * BAR_MS}     # a BADA PRINT names any chapter it lands in
    chs: List[dict] = []
    for x in op:
        cur = chs[-1] if chs else None
        if cur is None or (x["t"] - cur["start_ms"] >= gapms[x["s"]] and not x.get("first")):
            chs.append({"start_ms": x["t"], "name": x["name"], "s": x["s"], "side": x["side"], "chips": [x["chip"]] if x["chip"] else [],
                        "ens": [x["en"]] if x["en"] else [], "srcs": {x["src"]}, "ids": [x["id"]] if x.get("id") else []})
        else:
            if x["s"] > cur["s"] or (cur["name"].startswith("SHURU") and x["s"] >= 2):
                cur["name"] = (cur["name"] + " · " + x["name"]) if cur["name"].startswith("SHURU") else x["name"]
                cur["s"], cur["side"] = max(cur["s"], x["s"]), x["side"] or cur["side"]
            if x["chip"] and x["chip"] not in cur["chips"]:
                cur["chips"].append(x["chip"])
            if x["en"]:
                cur["ens"].append(x["en"])
            cur["srcs"].add(x["src"])
            if x.get("id"):
                cur["ids"].append(x["id"])
    # the events INSIDE each chapter (not only its openers) give the second clause and the remaining chips
    last_close = (bars[-1]["t"] + BAR_MS) if bars else (now_ms or start0)
    for i, c in enumerate(chs):
        end = chs[i + 1]["start_ms"] if i + 1 < len(chs) else None
        inside = [e for e in ev if c["start_ms"] <= e["t"] + BAR_MS < (end or 1 << 62) and e.get("shown") and e["id"] not in c["ids"]]
        for e in inside[-2:]:
            if e.get("chip") and e["chip"] not in c["chips"]:
                c["chips"].append(e["chip"])
            if e.get("en"):
                c["ens"].append(e["en"])
        for s_ in slots or []:
            t = day_ms(day, str(s_.get("t"))) if s_.get("t") else None
            if t is not None and c["start_ms"] <= t < (end or 1 << 62) and s_.get("power"):
                chip = f"POWER{' ▲' if s_.get('pdir') == 1 else ' ▼' if s_.get('pdir') == -1 else ''} {s_['t']}" + (
                    f" · forced {s_['fuel_top2_underwater']}/2" if s_.get("fuel_top2_underwater") is not None else "")
                if chip not in c["chips"]:
                    c["chips"].append(chip)
                break
        p0, p1 = _price_at(bars, c["start_ms"]), _price_at(bars, end if end is not None else last_close + 1)
        c["asar"] = None if p0 is None or p1 is None else round(p1 - p0)
    items = []
    for i, c in enumerate(chs):
        end = chs[i + 1]["start_ms"] if i + 1 < len(chs) else None
        ens = [x for x in c["ens"] if x][:2]
        sent = "; ".join(ens) if ens else ("the session opened" if c["name"].startswith("SHURU") else c["name"])
        items.append({"start": _hm(c["start_ms"]), "start_ms": c["start_ms"], "end": _hm(end) if end is not None else "abhi",
                      "current": end is None, "name": c["name"], "sentence": sent[:260], "chips": c["chips"][:3],
                      "side": c["side"], "asar": c["asar"], "asar_why": None if c["asar"] is not None else "no closed bar inside it",
                      "asar_label": "so far" if end is None else "", "src": sorted(c["srcs"]), "tag": "I"})
    return {"items": items, "items_why": None, "n": len(items),
            "trap_why": None if trows else "trap stamps check nahi — chapters from the decoder's own events"}


# ---- THE DECODER'S COUNT BESIDE HER TRADE (DESIGN §4) -------------------------------------------------------------------
def _in_trade(fold: Optional[dict], day: str = ""):
    """The open marked trade from /api/fold's reply: direction d (+1 = wants the future up), entry ms, id. The entry
    is the trade's own t0 (the view's events are its last 12, the seed can scroll out); the seed is the fallback."""
    if not isinstance(fold, dict) or not fold.get("ok"):
        return None
    v, tr = fold.get("view") or {}, fold.get("trade") or {}
    d = v.get("d")
    t0 = day_ms(day, str(tr.get("entry_t"))) if day and tr.get("entry_t") else None
    if t0 is None:
        t0 = next((e.get("t") for e in v.get("events") or [] if e.get("kind") == "seed"), None)
    if d not in (1, -1) or t0 is None or v.get("headline") is None or tr.get("exit_t") or v.get("frozen"):
        return None
    return {"d": d, "entry_ms": t0, "id": fold.get("id") or v.get("trade_id"), "E": v.get("E"), "fut": v.get("fut")}


def evidence(dec: Optional[dict], trap: Optional[dict], day: str, t0: int) -> List[dict]:
    """The decoder's evidence since t0, each piece with the side it favours (+1 up, -1 down), oldest first. Read off the
    posted events (a FAILED print or stack counts for the other side; absorbed counts against the aggressor; a failed
    divergence or initiative counts nothing), runs of confirmed new positions (one piece per run), and the trap layer's
    INDUCED / FAILED / RELEASED stamps. One definition for her trade's count and the flat lean."""
    items = []

    def add(side, chip, t, kind, at=False, n=1):
        items.append({"side": side, "chip": chip, "t": t, "time": _hm(t), "kind": kind, "at": bool(at), "n": n})
    for e in _events(dec):
        close = e["t"] + BAR_MS
        if close < t0:
            continue
        s, k, st, at = e.get("side") or 0, e["kind"], e.get("state"), bool(e.get("at") and (e["at"] or {}).get("kind") in ("band", "level"))
        if k == "E1":
            add(-s if st == "FAILED" else s, e.get("chip"), close, "E1", at)
        elif k == "E2" and st != "FAILED":
            add(s, e.get("chip"), close, "E2", at)
        elif k == "E3" and e.get("split") in ("positioning", "absorbed"):
            add(s if e["split"] == "positioning" else -s, e.get("chip"), close, "E3", at)
        elif k == "E4":
            add(-s if st == "FAILED" else s, e.get("chip"), close, "E4", at)
        elif k == "E6":
            add(-s, e.get("chip"), close, "E6", at)
        elif k == "E7" and st != "FAILED":
            add(s, e.get("chip"), close, "E7", at)
    # runs of confirmed new positions (E8 words without "?"), one item per run
    run = None
    for p in (dec or {}).get("per") or []:
        close = (p.get("t") or 0) + BAR_MS
        w = p.get("quad")
        sd = 1 if w == "naye long" else -1 if w == "naye short" else 0
        if close < t0 or not sd:
            if run:
                add(run["s"], run["chip"](), run["t"], "E8", False, run["n"]); run = None
            continue
        if run and run["s"] == sd:
            run["n"] += 1; run["end"] = close
        else:
            if run:
                add(run["s"], run["chip"](), run["t"], "E8", False, run["n"])
            run = {"s": sd, "n": 1, "t": close, "end": close, "w": w}
            run["chip"] = (lambda r=run: f"{r['w']} {_hm(r['t'])}" if r["n"] == 1 else f"{r['w']} ×{r['n']} bars {_hm(r['t'] - BAR_MS)}–{_hm(r['end'] - BAR_MS)}")
    if run:
        add(run["s"], run["chip"](), run["t"], "E8", False, run["n"])
    for r in _trap_rows(trap, day):
        if r["t_ms"] < t0 or r["state"] not in ("INDUCED", "FAILED", "RELEASED") or not r.get("dir"):
            continue
        add(-r["dir"] if r["state"] == "FAILED" else r["dir"], f"{_trap_name(r)} {_hm(r['t_ms'])}", r["t_ms"], "trap", True)
    items.sort(key=lambda x: x["t"])
    return items


def trade_read(dec: Optional[dict], fold: Optional[dict], trap: Optional[dict] = None, day: str = "") -> dict:
    """The decoder's evidence for / against her open trade's direction since her entry, as a COUNT with the chips that
    make it, and the PULLBACK / GAVE UP word when price is against her. Display only: fold.py's word is the decision."""
    tr = _in_trade(fold, day)
    if tr is None:
        return {"read": None, "read_why": "not in a marked trade"}
    d, t0 = tr["d"], tr["entry_ms"]
    items = evidence(dec, trap, day, t0)
    against = [x for x in items if x["side"] == -d]
    behind = [x for x in items if x["side"] == d]
    flip_t = grow_t = None
    a = b = 0
    for x in items:
        before = a > b
        if x["side"] == -d:
            a += 1
        elif x["side"] == d:
            b += 1
            grow_t = x["t"]
        if a > b and not before:
            flip_t = x["t"]
    word = word_t = because = None
    fut, E = tr.get("fut"), tr.get("E")
    word_why = ("no price or entry to compare yet" if fut is None or E is None else
                "price is with you or at your entry: no pullback / gave-up read")
    if fut is not None and E is not None and d * (fut - E) < 0:
        gave = [x for x in against if (x["kind"] in ("E1", "E3") and x["at"]) or x["kind"] == "trap" or (x["kind"] == "E8" and x["n"] >= 2)]
        if gave:
            g0 = gave[0]
            word, word_t = "GAVE UP", g0["t"] + (BAR_MS if g0["kind"] == "E8" else 0)   # a run counts from its 2nd bar
            because = f"{gave[0]['chip']} — new positions or a failure against you, not a pullback"
        else:
            word, because = "PULLBACK", "price against you on covering / rotation; no print or new positions against you"
        word_why = None
    return {"read": {"against": len(against), "behind": len(behind), "items": items, "d": d, "trade_id": tr["id"],
                     "word": word, "word_t": _hm(word_t) if word_t else None, "word_why": word_why, "word_because": because,
                     "flip_t": flip_t, "grow_t": grow_t, "since": _hm(t0), "tag": "I",
                     "note": "the decoder's read, beside the engine's word; it changes no HOLD / FOLD (P1-P7 unsigned)"},
            "read_why": None}


LEAN_MS = 30 * 60000                 # with no chapter yet, the lean reads the last 30 minutes


def lean(dec: Optional[dict], trap: Optional[dict], day: str, chapters_: Optional[dict], now_ms: int) -> dict:
    """The decoder's lean with no trade open (for IF YOU WERE IN on the DESK): the same evidence as her trade's count,
    since the current chapter opened (else the last 30 minutes), as up / down COUNTS. A buy-CE or sell-PE leg reads
    `up` as behind it and `down` as against; a buy-PE or sell-CE leg the other way round. Never a %."""
    if not _events(dec) and not ((dec or {}).get("per")) and not _trap_rows(trap, day):
        return {"lean": None, "lean_why": "no decoder event and no trap stamp yet today"}
    items = ((chapters_ or {}).get("items") or [])
    t0 = items[-1]["start_ms"] if items else now_ms - LEAN_MS
    ev = [x for x in evidence(dec, trap, day, t0) if x["t"] <= now_ms]
    return {"lean": {"up": sum(1 for x in ev if x["side"] > 0), "down": sum(1 for x in ev if x["side"] < 0),
                     "since": _hm(t0), "items": ev[-6:], "tag": "I",
                     "why": (f"the decoder's evidence since the current chapter opened ({_hm(t0)})" if items else
                             f"the decoder's evidence in the last 30 minutes (since {_hm(t0)})") + "; counts, never a %"},
            "lean_why": None}


# ---- OUT OF THE ORDINARY (her ask, 2026-10-04; DESIGN §7) ---------------------------------------------------------------
TIERS = ("red", "amber", "blue")


def highlights(dec: Optional[dict], fold: Optional[dict], tread: Optional[dict], day: str, now_ms: int,
               trap: Optional[dict] = None, slots: Optional[list] = None, three: Optional[dict] = None,
               feed: Optional[dict] = None, chapters_: Optional[dict] = None, vpin: Optional[dict] = None,
               cant: Optional[List[dict]] = None) -> List[dict]:
    """Every change in the last HOLD_MS that the colour grammar names, as {tier, kind, what, t_ms, time, id, block}.
    Stateless from each thing's own time (anytime-start: a restart never floods old changes); the two that have no time
    of their own (VPIN crossing 0.8, a read going to CAN'T CHECK) are handed in with the time the server first saw them."""
    out: List[dict] = []
    tr = _in_trade(fold, day)
    d = tr["d"] if tr else None

    def hit(tier, kind, what, t, block, id_=""):
        if t is not None and 0 <= now_ms - t <= HOLD_MS + FADE_MS:
            out.append({"tier": tier, "kind": kind, "what": what, "t_ms": t, "time": _hm(t), "id": id_ or "", "block": block,
                        "fading": now_ms - t > HOLD_MS})
    # RED · act now
    for e in ((fold or {}).get("view") or {}).get("events") or []:
        if e.get("kind") == "fold":
            hit("red", "FOLD", e.get("text") or "FOLD", e.get("t"), "trade")
        elif e.get("kind") in ("touch", "past_give_up"):
            hit("red", "PAST GIVE-UP", e.get("text") or "give-up touched", e.get("t"), "trade")
        elif e.get("kind") == "chip" and e.get("new") == "CAN'T CHECK" and e.get("old") not in (None, "CAN'T CHECK"):
            hit("amber", "CANT CHECK", f"{e.get('chip')} ab CAN'T CHECK (pehle {e.get('old')})", e.get("t"), "trade")
    red_ids = set()
    for e in _events(dec):
        if e["kind"] != "E1":
            continue
        close, at = e["t"] + BAR_MS, (e.get("at") or {}).get("kind") in ("band", "level")
        if d and e.get("side") == -d and at and tr and close >= tr["entry_ms"]:
            hit("red", "PRINT AGAINST", f"{(e.get('chips') or [e.get('chip')])[0]} tumhare khilaaf · {(e.get('at') or {}).get('name')}", close, "trade", e["id"])
            red_ids.add(e["id"])
    r = (tread or {}).get("read") or {}
    if r.get("flip_t"):
        hit("red", "DECODER FLIP", f"decoder palta: {r['against']} khilaaf · {r['behind']} saath", r["flip_t"], "trade")
    if tr and (feed or {}).get("state") in ("DEAD", "STALLED"):
        hit("red", "FEED", f"feed {feed['state']} — trade ka read ruka", day_ms(day, str(feed.get("since") or "")) or now_ms, "feed")
    # AMBER · out of the ordinary, look now
    for e in _events(dec):
        close = e["t"] + BAR_MS
        if e["kind"] == "E1" and e["id"] not in red_ids:
            hit("amber", "BADA PRINT", "naya " + (e.get("chips") or [e.get("chip")])[0], close, "abhi", e["id"])
    for p in (dec or {}).get("per") or []:
        if p.get("step") and p.get("t") is not None:
            hit("amber", "OI STEP", f"OI publication step {_hm(p['t'])} · OI check nahi", p["t"] + BAR_MS, "book")
    for x in _trap_rows(trap, day):
        if x["state"] in ("INDUCED", "FAILED", "RELEASED"):
            hit("amber", "TRAP", _trap_name(x), x["t_ms"], "book")
    for s_ in slots or []:
        t = day_ms(day, str(s_.get("t"))) if s_.get("t") else None
        if t is None:
            continue
        if s_.get("episode_t0") and s_.get("episode_t0") == s_.get("t"):
            hit("amber", "PUSHTI", f"PUSHTI {'▲' if s_.get('pdir') == 1 else '▼'} {s_['t']}", t, "book")
        elif s_.get("power"):
            hit("amber", "POWER", f"POWER slot {'▲' if s_.get('pdir') == 1 else '▼'} {s_['t']}" + (
                f" · forced {s_['fuel_top2_underwater']}/2" if s_.get("fuel_top2_underwater") is not None else ""), t, "book")
    if (three or {}).get("n_weekly_power") == 2 and three.get("t"):
        hit("amber", "WEEKLY 2/2", f"weekly books 2/2 {'▲' if three.get('dir_weekly') == 1 else '▼'} · NIFTY+SENSEX", day_ms(day, str(three["t"])), "book")
    if vpin and vpin.get("pct") is not None and vpin["pct"] >= 0.8:
        hit("amber", "VPIN", f"VPIN {vpin['pct']:.2f} pct (shadow)", vpin.get("since_ms"), "book")
    seen_t = {h["t_ms"] for h in out}
    for c in ((chapters_ or {}).get("items") or [])[1:]:
        if c["start_ms"] not in seen_t:             # the print / trap that opened it already says so: one line, not two
            hit("amber", "CHAPTER", f"naya chapter · {c['name']}", c["start_ms"], "kahani")
    for c in cant or []:
        hit("amber", "CANT CHECK", f"{c.get('what')} ab CAN'T CHECK", c.get("t_ms"), c.get("block") or "trade")
    # BLUE · in your favour
    if r.get("grow_t"):
        hit("blue", "BEHIND GROWS", f"saath wale saboot badhe: {r['behind']} saath · {r['against']} khilaaf", r["grow_t"], "trade")
    for e in _events(dec):
        if d and e["kind"] == "E1" and e.get("side") == d and e.get("state") != "FAILED" and e.get("tests"):
            hit("blue", "LEVEL HOLDS", f"tumhare saath wala print {_px(e['p'])} ka test hold", e["tests"][-1] + BAR_MS, "ledger", e["id"])
    rank = {t: i for i, t in enumerate(TIERS)}
    out.sort(key=lambda h: (rank[h["tier"]], -h["t_ms"]))
    return out


def compose_all(dec: Optional[dict], fut: Optional[float], day: str, now_ms: int, closed: Optional[list] = None,
                fold: Optional[dict] = None, trap: Optional[dict] = None, three: Optional[dict] = None,
                feed: Optional[dict] = None, vpin: Optional[dict] = None, logged: Optional[List[dict]] = None,
                cant: Optional[List[dict]] = None) -> dict:
    """Everything the panel, the Float and the DESK read: compose() plus the chapters, the decoder's count beside her
    trade, the highlights, and the BOOK·TRAP lines as the server publishes them."""
    base = compose(dec, fut)
    slots = (trap or {}).get("slots") or []
    ch = chapters(dec, closed or [], day, trap, slots, logged, now_ms)
    tr = trade_read(dec, fold, trap, day)
    ln = lean(dec, trap, day, ch, now_ms)
    hl = highlights(dec, fold, tr, day, now_ms, trap, slots, three, feed, ch, vpin, cant)
    lines = (trap or {}).get("lines")
    return {**base, "chapters": ch, "trade_read": tr["read"], "trade_read_why": tr["read_why"], "highlights": hl, **ln,
            "now_ms": now_ms, "hold_ms": HOLD_MS, "fade_ms": FADE_MS,
            "book": three or None, "book_why": None if three else "sides-3 abhi nahi (the server's sides read has not run)",
            "trap": lines or None, "trap_why": None if lines else ((trap or {}).get("why") or "trap-1 abhi nahi (the trap read has not run)"),
            "vpin": vpin or None, "vpin_why": None if vpin else "VPIN check nahi"}
