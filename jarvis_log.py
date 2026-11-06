"""jarvis_log.py -- THE CALL LOG and THE CARD (Jarvis v3 Task 2; plan docs/superpowers/plans/2026-10-31-jarvis-v3-weekend.md,
the CALL LOG and CARD contracts).
  LOG    what the LIVE Jarvis frame said: one row per index per frame minute, write-once, data/jarvis/call_<day>.jsonl.
         The server writes it right after a live build whose last minute is new for that index (server._jarvis_log):
         never a replay, never a cache hit. `read` gives the rows in order; `self_line` the word's own record today.
  CARD   the small dict every face renders (GET /api/jarvis/card), built from the cached live frame ONLY -- no build.
         A key the frame lacks is null, never invented (Tasks 5 / 7 fill how_much, where, voice later).
Counts, never a %. Every level the engine printed keeps its s / f. Display only: nothing here gates, beeps or places."""
from __future__ import annotations

import json
import os
import re
import threading

import confluence_log

DIR = os.path.join("data", "jarvis")
TRUE_WIN_M = 45      # a PALAT? episode "came true" when a PALAT row follows within 45 min of its FIRST minute [I: the plan's
                     # number; tools/jarvis_review.py measures it the same way, so the card and the evening sheet agree]
PUSHES_N = 5         # the card's last pushes (the 10 KB bound) [I]
GAP_M = 2            # [I] call rows more than 2 min apart are a hole in the log (a restart, a build that kept failing); a
                     # skipped pass (lock held, slow) leaves one missing minute, never a hole
LOG_FROM = "09:16"   # a log whose first row is after 09:16 started late (the first frame minute is 09:15) [I]
GAPS_N = 3           # the self line names the last 3 holes and counts the rest (the 10 KB bound) [I]
PUSH_KEYS = ("t", "dir", "lots", "k", "side", "ans", "held_at", "via")
_SEEN = {}           # path -> {(idx, t)} already on disk: write-once across a restart
_LOCK = threading.Lock()


def _path(day, kind="call"):
    return os.path.join(DIR, f"{kind}_{day}.jsonl")


def read(day, idx=None, kind="call"):
    """The day's rows in file order, one index (or all); [] when there is no file. kind "call" (the call log) or
    "state" (the market state's forward log, spec 2026-11-06 §9)."""
    return [r for r in confluence_log._rows(_path(day, kind)) if idx is None or r.get("idx") == idx]


def write(day, idx, row, kind="call"):
    """Append `row` once per (idx, t) -> True when written, False for a minute already on disk. DIR is made on first write."""
    p = _path(day, kind)
    with _LOCK:
        seen = _SEEN.get(p)
        if seen is None:
            seen = _SEEN[p] = {(r.get("idx"), r.get("t")) for r in confluence_log._rows(p)}
        k = (idx, row.get("t"))
        if k in seen:
            return False
        os.makedirs(DIR, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(row, idx=idx), ensure_ascii=False, default=str) + "\n")
        seen.add(k)
        return True


def _last(xs):
    return (xs or [None])[-1]


def _cnt3(c):
    """The count as logged: with / against / N, flat / blind apart (rule 6, A230) and each piece's state by its key."""
    if not isinstance(c, dict):
        return None
    return {k: c.get(k) for k in ("with", "against", "N", "flat", "blind")} | {
        "pieces": {p.get("k"): p.get("state") or p.get("side") for p in c.get("pieces") or () if isinstance(p, dict)}}


def row(fr, now):
    """The CALL LOG row of a live frame (the contract's keys; absent ones null). `blind` = the call's BLIND line."""
    c = fr.get("call") or {}
    miss = list(c.get("missing") or [])
    return {"day": fr.get("day"), "idx": fr.get("idx"), "t": c.get("at") or _last(fr.get("mins")), "at": int(now),
            "shown": fr.get("asof"), "word": c.get("word"), "state": c.get("state"), "lean": c.get("lean"),
            "since": c.get("since"), "count": _cnt3(c.get("count")), "fut": _last(fr.get("fut")), "spot": _last(fr.get("spot")),
            "leg": c.get("leg"), "wrong_line": c.get("wrong_line"), "missing": miss,
            "action": (c.get("action") or {}).get("said"), "vol": ((c.get("mstate") or {}).get("vol") or {}).get("word"),
            "notes": list((fr.get("health") or {}).get("notes") or []), "blind": any(str(x).startswith("BLIND") for x in miss)}


def state_row(fr, j, now, src):
    """THE STATE LOG row for frame minute j (data/jarvis/state_<day>.jsonl, spec 2026-11-06 §9: the evening review,
    never a gate): the state word, since, line, why, efficiency, the volatility word and each gauge's vote. src "live" =
    the frame's newest minute, written as it happened; "backfill" = a minute rebuilt causally at a later start, never
    pooled with live rows."""
    s = fr["mstate"][j]
    v = s.get("vol") or {}
    return {"day": fr.get("day"), "t": s.get("t") or fr["mins"][j], "at": int(now), "src": src, "word": s["word"], "dir": s["dir"],
            "conf": s["conf"], "since": s["since"], "line": s["line"], "why": s["why"], "eff": s["eff"],
            "vol": v.get("word"), "votes": {g["k"]: g["vote"] for g in v.get("gauges") or ()}, "expiry": s.get("expiry"),
            "zone": [{k: z.get(k) for k in ("t", "side", "band", "verdict", "n", "N", "kind")}
                     for z in fr.get("zone_cards") or () if z["known"] <= fr["mins"][j]]}


def _m(t):
    return int(t[:2]) * 60 + int(t[3:5])


def _hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def self_line(rows, fut_now):
    """`TREND ▼ since 09:56 · −200 so far · PALAT? said 3× · came true 0× · blind 0 min`, or None with no rows. since = the
    first row of the current unbroken word; so far = the RAW signed move, fut now − fut at since (the arrow says which way
    is good); said = PALAT? episodes (consecutive rows); came true = episodes with a PALAT row within TRUE_WIN_M of the
    episode's first minute; blind = rows marked blind (one a minute).
    I4 (anytime-start): the word is never joined across a hole of more than GAP_M min (since / so far start after it), a
    log that starts after LOG_FROM says `· log from HH:MM`, and each hole is named `· log gap a–b` (the minutes missing; the
    last GAPS_N, the rest counted): the counts cover only the rows on disk."""
    rows = [r for r in rows if isinstance(r.get("t"), str) and re.match(r"\d\d:\d\d", r["t"])]   # a bad t costs its row
    if not rows:
        return None
    ms = [_m(r["t"]) for r in rows]
    w, i = rows[-1].get("word"), len(rows) - 1
    while i and rows[i - 1].get("word") == w and ms[i] - ms[i - 1] <= GAP_M:
        i -= 1
    f0 = rows[i].get("fut")
    far = ("so far could not check — no fut price" if fut_now is None or f0 is None
           else f"{fut_now - f0:+,.0f} so far".replace("-", "−"))
    word = [str(r.get("action") or r.get("word") or "") for r in rows]   # PALAT? / PALAT live in the ACTION word (6 Nov)
    eps = [_m(r["t"]) for j, r in enumerate(rows) if word[j].startswith("PALAT?") and not (j and word[j - 1].startswith("PALAT?"))]
    flips = [_m(r["t"]) for j, r in enumerate(rows) if word[j].startswith("PALAT") and not word[j].startswith("PALAT?")]
    true = sum(1 for a in eps if any(a < m <= a + TRUE_WIN_M for m in flips))
    blind = sum(1 for r in rows if r.get("blind"))
    holes = [f" · log gap {_hm(a + 1)}–{_hm(b - 1)}" for a, b in zip(ms, ms[1:]) if b - a > GAP_M]
    tail = ((f" · log from {rows[0]['t'][:5]}" if rows[0]["t"][:5] > LOG_FROM else "")
            + (f" · +{len(holes) - GAPS_N} earlier log gaps" if len(holes) > GAPS_N else "") + "".join(holes[-GAPS_N:]))
    return f"{w} since {rows[i]['t']} · {far} · PALAT? said {len(eps)}× · came true {true}× · blind {blind} min{tail}"


def answer(fr):
    """The last answer as the engine said it: the count's `answer` piece, else the `last answer …` clause of the call's why
    (verbatim), else None."""
    c = (fr or {}).get("call") or {}
    for p in (c.get("count") or {}).get("pieces") or ():
        if p.get("k") == "answer":
            return p.get("text")
    for ln in c.get("why") or ():
        m = re.search(r"last answer .*?(?= · |$)", str(ln))
        if m:
            return m.group(0)
    return None


def brief(fr):
    """The card's word, count and last answer -- what a watch hit carries to the stream and Telegram."""
    c = (fr or {}).get("call") or {}
    return {"word": c.get("word"), "count": _cnt3(c.get("count")), "answer": answer(fr)}


def card(fr, rows=(), state=None, notes=()):
    """THE CARD (the contract) from a cached live frame, today's call-log rows (the self line), the day's drawn state and
    her notes. A frame that could not build passes its why on."""
    if not (fr or {}).get("ok"):
        return {"ok": False, "why": (fr or {}).get("why") or "could not check — no frame built yet"}
    c = fr.get("call") or {}
    hn = list((fr.get("health") or {}).get("notes") or [])
    pz, st = c.get("pause"), state or {}
    return {"ok": True, "idx": fr.get("idx"), "day": fr.get("day"), "at": c.get("at"), "asof": fr.get("asof"),
            "live": bool(fr.get("live")), "word": c.get("word"), "state": c.get("state"), "lean": c.get("lean"),
            "since": c.get("since"), "count": c.get("count"), "leg": c.get("leg"),
            "pause": {k: pz.get(k) for k in ("line", "alive", "risk")} if isinstance(pz, dict) else None,
            "how_much": c.get("how_much"), "where": c.get("where"), "cross": c.get("cross"),   # Task 5's reads
            "her_setup": c.get("her_setup"), "expiry": c.get("expiry"), "bada": c.get("bada"),
            "expression": c.get("expression") or {"buyer": c.get("buyer"), "seller": c.get("seller"), "pick": c.get("pick")},
            "wrong_line": c.get("wrong_line"), "up": c.get("up"), "dn": c.get("dn"), "walls": c.get("walls"),
            "lines": c.get("lines"), "no_trade": c.get("no_trade"),
            "health": {"missing": [x for x in c.get("missing") or () if x not in hn], "notes": hn + list(notes),
                       "method": list((fr.get("health") or {}).get("method") or [])},   # how a number was made (Task 6), not a gap
            "self": self_line(rows, _last(fr.get("fut"))),
            "pushes": [{k: p.get(k) for k in PUSH_KEYS} for p in (fr.get("pushes") or [])[-PUSHES_N:]],
            "watches": list(st.get("watches") or []), "voice": None, "brief": None,   # Task 7: server._JVOICE fills both
            "mstate": c.get("mstate"), "action": c.get("action"), "chips": c.get("chips"), "zone": c.get("zone")}   # the state leads (6 Nov)
