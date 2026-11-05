"""messages.py -- THE MESSAGE STREAM: what the tool already said, one line per CHANGE, for the floating window and
Telegram (spec docs/superpowers/specs/2026-10-25-message-window-telegram-design.md; NOTEPAD A101).

Mary, 25 Oct: "sometime i miss the signals it genrate and not able to decipher whats its telling, on these many screen".
NOTHING NEW IS READ: every message is a change in a read the server already logs, write-once.
  READ    THE READ's held word or arrow changes at a closed mark; a QUIT event                   data/read/read_<day>.jsonl
  LEG     DECODE's call turns JAARI <-> THAK or its leg flips; MILA / saaf nahi keep the last    data/decode/decode_<day>.jsonl
  SETUP   a FADE / RIDE / FADE-D / ZONE chip turns MATCH, or an entry's HOLD v2 state            the same DECODE rows
          ZONE (A116): her four pieces and n/4 on the line, then one line per piece that joins its episode (zone_ep);
          A131: the ZONE line ends with the §1o day type in her words (din); TOP / BOTTOM BAN SAKTA is palat.py's
  DIN     the one-sided meter's day type changes (TREND ▲ / ▼, CHOP, MIXED)                      the same DECODE rows
  JARVIS  Jarvis's ACTION word changes (keyed at its since), CAN'T SEE once per blind stretch, and   data/jarvis/call_<day>.jsonl
          her watch hits with the card's word, count and last answer (Jarvis v3)                  data/jarvis/cmd_<day>.jsonl
  TRADE   the one voice turns TIGHTEN / WARN / EXIT (server._in_trade -> `trade`)
  HEALTH  RECORDING NAHI starts / clears; the day's first look says "TapeMap live" (server._recording -> `health`)
SETUP reads DECODE's chips, not confluence_log: that log writes a row once the setup's window has CLOSED (23 Oct [M]:
FADE-D rows 30-36 min after the start) and 12 of its 14 rows that day never fired; the two that did (BANKNIFTY RIDE
10:45, FADE-D 13:15) are exactly DECODE's two chip turns, at the same close, logged a grace minute after it.
AGREE is DECODE's count at that close, never a %. DECODE's call.d / call.c are the decel / continuation COUNTS; the way is
the leg's d. JAARI reads the leg's way with c/7, THAK against it with d/7: "saath" when that way is the message's,
"khilaaf" when against; a message with no way shows DECODE's arrow and count. "mila d thak · c jaari" (checked, mixed), "saaf nahi"
(checked, no leg) and "?" (no DECODE row for that close) stay separate sentences.
PURE: no I/O, no clock -- the server hands in the day's rows, so a restart rebuilds the same stream (anytime-start).
DISPLAY ONLY: gates nothing; the faces and Telegram show `line` verbatim. [I]
"""
from __future__ import annotations

import re

ARROW = {1: "▲", -1: "▼", 0: ""}
KINDS = ("HEALTH", "READ", "SETUP", "LEG", "DIN", "JARVIS", "TRADE")    # the order of one close's lines
OFF = ("—", "ARMED")                                          # a setup chip that has not fired
TRADE_ON = ("TIGHTEN", "WARN", "EXIT")
JARVIS_TG_DAY = 20                                            # JARVIS word lines to Telegram a day per index, then quiet [I]
JARVIS_TG_ALWAYS = ("TREND", "PALAT?", "PALAT")              # her word 5 Nov (A255): never quiet, never counted in the 20
SKIPPED = {"n": 0}                                            # rows the LAST build skipped as malformed (a bad dir, text for a number)


def _n(x):
    return "?" if x is None else f"{x:,.0f}"


def px(x):
    """A price as the lines print it: 22,800 or 22,799.6; '?' when missing (never a zero)."""
    if not isinstance(x, (int, float)):
        return "?"
    x = round(float(x), 1)
    return f"{x:,.0f}" if x.is_integer() else f"{x:,.1f}"


def key(m):
    """The write-once key within a day: idx | kind | t | word, and the trade id for TRADE."""
    return "|".join(str(x) for x in (m["idx"], m["kind"], m["t"], m["word"]) + ((m["id"],) if m.get("id") else ()))


def line(m):
    """The one line every face and Telegram show: HH:MM  IDX  what · agree · level. TRADE / HEALTH: the kind, and the why's
    first clause."""
    lbl = m["kind"] if m["kind"] in ("TRADE", "HEALTH") else m["idx"]
    head = m["word"]
    if m["kind"] in ("TRADE", "HEALTH") and m.get("why"):
        head += " · " + re.sub(r"\s*\([^)]*\)\s*$", "", str(m["why"]).split(" · ")[0])
    return f"{m['t']}  {lbl}  " + " · ".join(x for x in (head, m.get("agree"), m.get("level")) if x)


def _msg(t, idx, kind, d, word, agree_, level, why, **extra):
    if d not in ARROW:
        raise ValueError(f"dir {d!r}")
    m = dict(t=t, idx=idx, kind=kind, dir=d, word=word, agree=agree_, level=level, why=why, **extra)
    m["key"], m["line"] = key(m), line(m)
    return m


def name(word, d=0, ff=False):
    """THE READ's held word as the faces say it (read._name): "TREND ▼ · flow+fuel", "LEAN ▲", "RANGE"."""
    return f"{word}{' ' + ARROW[d] if d else ''}{' · flow+fuel' if ff else ''}"


def agree(row, d):
    """DECODE's count at this close against direction d (module docstring). Never blank, never a 0."""
    c = (row or {}).get("call") or {}
    k, ld = c.get("kind"), ((row or {}).get("leg") or {}).get("d")
    if not row or c.get("text") in (None, "?"):
        return "?"
    if k == "SAAF_NAHI":
        return "saaf nahi"
    if k == "MILA":
        return f"mila {c.get('d')} thak · {c.get('c')} jaari"      # A126: "mila 3/1" read as 3 of 1
    if k not in ("JAARI", "THAK") or ld not in (1, -1):
        return "?"
    way, n = (ld, c.get("c")) if k == "JAARI" else (-ld, c.get("d"))
    of = c.get("of") or 7
    return f"{ARROW[way]}{n}/{of}" if not d else f"{n}/{of} {'saath' if way == d else 'khilaaf'}"


def din_line(ty, side):
    """A131: the §1o day type said on a zone / palat line against its fade side ("BUY" / "SELL"), in her words: on a pin
    or chop day expect the reversal, on a trend against the zone side the price may go on discovering. None: not read."""
    if not ty:
        return "din: padh nahi sake"
    if ty in ("PIN", "CHOP"):
        return f"din {ty}: palat ki ummeed"
    if ty.startswith("TREND"):
        return (f"din {ty}: price discovery ho sakti hai · fade khatra" if ("▲" in ty) == (side == "SELL")
                else f"din {ty}: trend ke saath")
    return f"din {ty}: saaf nahi"


def _level(r):
    """THE READ's level: a TREND / LEAN's FLIP, a RANGE's box walls -- spot, as the READ reads them."""
    if r.get("flip") is not None:
        return f"flip {_n(r['flip'])}s"
    bx = r.get("box") or {}
    lo, hi = (bx.get("bottom") or {}).get("k"), (bx.get("top") or {}).get("k")
    return f"box {_n(lo)}–{_n(hi)}s" if lo is not None and hi is not None else None


def _ok(r, k):
    """A log row with a text index and a text close `k` (they are sort keys and key parts); anything else is not a row."""
    return isinstance(r.get("idx"), str) and r["idx"] != "" and isinstance(r.get(k), str) and r[k] != ""


def build(read_rows, decode_rows):
    """The day's market messages (READ, LEG, SETUP, DIN) from its READ and DECODE log rows, oldest first: each a change
    from the close before it. A row without an index or a close is skipped. So is a MALFORMED row (a dir that is not -1 / 0
    / 1, text for a number): skipped and counted in SKIPPED, never raised -- one bad row must not freeze the stream, and the
    state the next row is compared with moves only after a row's message is made."""
    bad = 0
    dec = sorted((r for r in decode_rows if _ok(r, "T")), key=lambda r: (r["T"], r["idx"]))
    at = {(r["idx"], r["T"]): r for r in dec}
    evs = [e for e in read_rows if e.get("kind") == "event" and _ok(e, "t")]
    out, held = [], {}
    for r in sorted((r for r in read_rows if r.get("kind") == "mark" and _ok(r, "t")), key=lambda r: (r["t"], r["idx"])):
        if r.get("word") in (None, "BAN RAHA"):              # the first 30 minutes are read, never named
            continue
        try:
            i, t, s = r["idx"], r["t"], (r["word"], r.get("dir") or 0, r.get("src") == "flow+fuel")
            was = held.get(i, ("WAIT", 0, False))
            if s[:2] != was[:2]:                             # same word, same arrow: flow+fuel coming or going is churn
                here = [e for e in evs if (e["idx"], e["t"]) == (i, t)]
                why = (next((e.get("text") for e in here if e.get("event") == "BREAK"), None)
                       or next((e.get("en") for e in here if e.get("event") in ("FORM", "UP", "DOWN")), None))
                out.append(_msg(t, i, "READ", s[1], f"{name(*was)} → {name(*s)}", agree(at.get((i, t)), s[1]), _level(r), why,
                                ev="WORD"))
            held[i] = s
        except Exception:                                    # noqa: BLE001 -- a malformed row is skipped, never raised
            bad += 1
    for e in evs:
        if e.get("event") == "QUIT":                         # a big writer wall near spot gave back half its build
            try:
                d = e.get("dir") or 0
                out.append(_msg(e["t"], e["idx"], "READ", d, f"{_n(e.get('k'))} {e.get('side')} likhne wale bhage",
                                agree(at.get((e["idx"], e["t"])), d), None, e.get("text"), ev="QUIT"))
            except Exception:                                # noqa: BLE001
                bad += 1
    leg, live, din = {}, {}, {}
    zep = {}                                                 # A116: idx -> [side, ep, the pieces already said] of a ZONE alert
    for r in dec:
        try:
            i, t, c, lg = r["idx"], r["T"], r.get("call") or {}, r.get("leg") or {}
            ld = lg.get("d")
            if c.get("kind") in ("JAARI", "THAK") and ld in (1, -1) and leg.get(i) != (c["kind"], ld):
                out.append(_msg(t, i, "LEG", ld, f"{ARROW[ld]} leg {'jaari' if c['kind'] == 'JAARI' else 'thak raha'}",
                                agree(r, ld), None, " · ".join((c.get("signs") or [])[:2]) or None))
                leg[i] = (c["kind"], ld)                     # MILA / saaf nahi / ? keep the last leg read
            on = {(s.get("name"), s.get("side")): str(s.get("state")) for s in r.get("setups") or ()
                  if s.get("name") and s.get("side") in ("BUY", "SELL") and str(s.get("state") or "—") not in OFF}
            ext = lg.get("ext") or {}
            plan = {(s.get("name"), s.get("side")): s.get("plan") for s in r.get("setups") or ()}   # A108: its own E / stop
            chip = {(s.get("name"), s.get("side")): s for s in r.get("setups") or ()}
            for (nm, side), state in on.items():
                if (nm, side) not in live.get(i, {}):
                    d, z = 1 if side == "BUY" else -1, chip[(nm, side)]
                    if nm == "ZONE" and z.get("pieces"):     # A116: her four pieces, n/4, instead of DECODE's 7-sign count
                        out.append(_msg(t, i, "SETUP", d, f"{nm} {side}", f"{z.get('n')}/4",    # A131: + the day type
                                        " · ".join(list(z["pieces"]) + ([z["plan"]] if z.get("plan") else [])
                                                   + [din_line((r.get("onesided") or {}).get("type"), side)]), state))
                        zep[i] = [side, z.get("ep"), {k for k, v in (z.get("checks") or {}).items() if v is True}]
                        continue
                    out.append(_msg(t, i, "SETUP", d, f"{nm} {side}", agree(r, d), plan.get((nm, side))
                                    or (None if ext.get("fut") is None else f"{_n(ext['fut'])}f"), state))
            live[i] = on
            ze, z0 = r.get("zone_ep") or {}, zep.get(i)
            if z0 and [ze.get("side"), ze.get("ep")] == z0[:2]:      # one line when a piece joins the alerted setup
                new = [p for p in ze.get("pieces") or () if p.get("ok") is True and p.get("k") not in z0[2]]
                if new:
                    out.append(_msg(t, i, "SETUP", 1 if z0[0] == "BUY" else -1,
                                    f"ZONE {z0[0]} + " + " + ".join(p["lbl"] for p in new), f"{ze.get('n')}/4",
                                    " · ".join([p["chip"] for p in new] + ([ze["plan"]] if ze.get("plan") else [])),
                                    "piece joined"))
                    z0[2].update(p["k"] for p in new)
            ty = (r.get("onesided") or {}).get("type")
            if ty and din.get(i) != ty:                      # None (could not check) keeps the last type
                d = 1 if "▲" in ty else -1 if "▼" in ty else 0
                out.append(_msg(t, i, "DIN", d, f"din {ty}", agree(r, d), None, None if din.get(i) is None else f"pehle {din[i]}"))
                din[i] = ty
        except Exception:                                    # noqa: BLE001
            bad += 1
    SKIPPED["n"] = bad
    return sorted(out, key=lambda m: (m["t"], KINDS.index(m["kind"]), m["idx"], m["word"]))


def _wa(c):
    c = c or {}
    return None if c.get("with") is None or c.get("against") is None else f"WITH {c['with']} · AGAINST {c['against']}"


def jarvis(call_rows, cmd_rows=()):
    """Jarvis v3's lines (kind JARVIS) from the call log (jarvis_log rows, every index) and the command log (jarvis_cmd
    rows): one line per ACTION word change, at its `since` (the minute the word was set); CAN'T SEE once per blind stretch;
    the word said again at its own minute once she can see; one line per watch hit with the card's word, count and last
    answer, and `could not check — gap` for a watch crossed while the server was down. Other command rows say nothing.
    Past JARVIS_TG_DAY word lines for an index, the rest are `quiet` (the window only), with one line saying so; CAN'T
    SEE, the watches and the JARVIS_TG_ALWAYS words (TREND / PALAT? / PALAT) are never capped and never counted. A malformed row is skipped, never raised. Pure: a restart rebuilds the same."""
    out, held, dark, said = [], {}, {}, {}
    for r in sorted((r for r in call_rows if _ok(r, "t")), key=lambda r: (r["idx"], r["t"])):
        try:
            i, t = r["idx"], r["t"]
            if r.get("blind"):
                if not dark.get(i):
                    out.append(_msg(t, i, "JARVIS", 0, "CAN'T SEE", None, f"blind since {t}", None))
                dark[i] = True
                continue
            w, s = r.get("word"), r.get("since")
            if not w or (w == held.get(i) and not dark.get(i)):
                continue
            m = _msg(t if dark.get(i) or not s else s, i, "JARVIS", r.get("lean") or 0, w, _wa(r.get("count")),
                     f"since {s or t}", None)
            if w.split(" ")[0] not in JARVIS_TG_ALWAYS:      # 5 Nov: the 20 muted her 14:44 / 15:00 calls (A251, A255)
                said[i] = said.get(i, 0) + 1
                if said[i] == JARVIS_TG_DAY + 1:             # the review's ruling: past 20 a day, the window only, said once
                    out.append(_msg(m["t"], i, "JARVIS", 0, f"JARVIS quiet on Telegram: {JARVIS_TG_DAY} today "
                                    "(TREND / PALAT still sent)", None, None, None))
                if said[i] > JARVIS_TG_DAY:
                    m["quiet"] = True
            out.append(m)
            held[i], dark[i] = w, False
        except Exception:                                    # noqa: BLE001
            continue
    for h in cmd_rows:
        if h.get("kind") not in ("watch_hit", "watch_gap") or not _ok(h, "t"):
            continue
        try:
            if h["kind"] == "watch_gap":                     # crossed while the server was down: never called a hit
                out.append(_msg(h["t"][:5], h["idx"], "JARVIS", 0, f"WATCH {px(h['level'])}{h['frame']}",
                                f"could not check — gap {h['gap']}", None, None, id=f"g{h['id']}"))
                continue
            c = h.get("card") or {}
            out.append(_msg(h["t"][:5], h["idx"], "JARVIS", 0, f"WATCH {px(h['level'])}{h['frame']} hit @{px(h['px'])}{h['frame']}",
                            " · ".join(x for x in (c.get("word"), _wa(c.get("count"))) if x) or None, c.get("answer"), None,
                            id=f"w{h['id']}"))
        except Exception:                                    # noqa: BLE001
            continue
    return sorted(out, key=lambda m: (m["t"], m["idx"], m["word"]))


def now_rows(read_rows, decode_rows, idxs):
    """NOW, one line per index: THE READ's latest logged mark, DECODE's count at that close, since when."""
    dec = {(r.get("idx"), r.get("T")): r for r in decode_rows}
    last = {}
    for r in read_rows:
        if r.get("kind") == "mark" and r.get("idx") and r.get("t") and r["t"] >= (last.get(r["idx"]) or {}).get("t", ""):
            last[r["idx"]] = r
    out = []
    for i in idxs:
        r = last.get(i)
        if r is None:
            out.append({"idx": i, "dir": 0, "word": None, "line": f"{i}  read abhi nahi",
                        "why": "could not check — no READ mark logged yet today"})
            continue
        d = r.get("dir") or 0
        parts = [name(r.get("word") or "?", d, r.get("src") == "flow+fuel"), agree(dec.get((i, r["t"])), d)]
        if r.get("since"):
            parts.append(f"since {r['since']}")
        out.append({"idx": i, "dir": d, "word": r.get("word"), "line": f"{i}  " + " · ".join(parts), "why": f"mark {r['t']}"})
    return out


def trade(tr, v, was, row, hm):
    """THE ONE VOICE's turn into TIGHTEN / WARN / EXIT as a message (`was`: its last state for this trade; `row`: the
    trade index's latest DECODE row), else None -- the same state, HOLD, or no voice."""
    st = (v or {}).get("state")
    if not (v or {}).get("ok") or st == was or st not in TRADE_ON:
        return None
    d = v.get("d") or 0
    return _msg(v.get("trig_t") or hm, tr["idx"], "TRADE", d, st, agree(row, d),
                None if v.get("stop_f") is None else f"stop {_n(v['stop_f'])}f", v.get("reason"), id=tr["id"])


def health(rec, was, hm):
    """server._recording ({ok, missing, text}; None outside 09:20-15:30) as a message, else None: the day's first look
    says "TapeMap live", then RECORDING NAHI once when it starts and RECORDING OK once when it clears."""
    if rec is None:
        return None
    if not rec.get("ok"):
        return None if was == "RECORDING NAHI" else _msg(hm, "ALL", "HEALTH", 0, "RECORDING NAHI", None, None,
                                                           ", ".join(rec.get("missing") or ()) or None)
    if was is None:
        return _msg(hm, "ALL", "HEALTH", 0, "TapeMap live", None, None, "recording ok")
    return _msg(hm, "ALL", "HEALTH", 0, "RECORDING OK", None, None, None) if was == "RECORDING NAHI" else None
