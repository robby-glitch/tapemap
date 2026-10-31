"""jarvis_cmd.py -- THE COMMAND GRAMMAR every face sends text to: the Jarvis page, the terminal, Telegram, the Dext chart
(Jarvis v3 Task 2; plan docs/superpowers/plans/2026-10-31-jarvis-v3-weekend.md, the COMMAND contract).
  parse(text)   PURE, no I/O -> {"kind", ...}; a malformed command carries "error"; an order word is refused.
  Day(day)      the day's lines, zones, watches and notes, rebuilt from data/jarvis/cmd_<day>.jsonl (anytime-start: the file
                is the memory, append-only). apply() persists the drawing / record commands and every refusal, one row each,
                and answers the read-only ones from the cached frame verbatim; check_watches() fires a watch ONCE on a touch.
  mark / flat   call the server's OWN hold handler (server._hold_post, the Float's POST /api/hold/trades door), handed in as
                `hold`; nothing here copies it. A RECORD of a trade she already placed on her broker -- she trades on several,
                Upstox is only the data feed, and nothing here reads a broker position.
NO ORDER PATH: text with an order word (ORDER_RE) is refused with REFUSE and logged; `mark`'s buy / sell names what she did.
Counts, never a %. Every drawn level says s (spot) or f (futures)."""
from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime

import confluence_log
import messages
from chain_live import IST

DIR = os.path.join("data", "jarvis")
REFUSE = "I read, I don't place."
MAX_WATCH = 10                                   # watches a day, every index (the plan's number) [I]
IDXS = ("NIFTY", "SENSEX", "BANKNIFTY")
PERSIST = ("line", "zone", "watch", "remove", "clear", "note", "mark", "flat", "refused")
ORDER_RE = re.compile(r"\b(buy|sell|order|place|short|long)\b|\bsquare\s+off\b|\bexit\s+now\b|\b\d+\s*lots?\b")
ASKING = ("ask ", "why", "what if", "what next")             # a question is never an order: its order words are read, not refused
MARK = "mark NIFTY|SENSEX|BANKNIFTY <strike> CE|PE buy|sell <price> [qty N]"
HELP = ["line 22750f · zone 22680-22720f · watch 22800s (s spot, f futures)",
        "remove 22750 · clear · list",
        "mark NIFTY 23000 PE buy 325 [qty 150] · flat [NIFTY]",
        "note <text> · why · next · status · wrong when",
        "what if 22800 breaks · ask <question> · replay <day> <HH:MM> (terminal)"]
_N = r"(\d[\d,]*(?:\.\d+)?)"
_LV = _N + r"\s*([sf])?"
_RX = {k: re.compile(v) for k, v in {
    "line": rf"line\s+{_LV}", "watch": rf"watch\s+{_LV}", "remove": rf"remove\s+{_LV}",
    "zone": rf"zone\s+{_N}\s*([sf])?\s*[-–—]\s*{_LV}",
    "mark": rf"mark\s+(nifty|sensex|banknifty)\s+{_N}\s+(ce|pe)\s+(buy|sell|long|short)\s+@?{_N}(?:\s+qty\s+(\d+))?",
    "flat": r"flat(?:\s+(nifty|sensex|banknifty))?", "whatif": rf"(?:what\s+)?if\s+{_LV}(?:\s+breaks?)?",
    "replay": r"replay\s+(\d{4}-\d\d-\d\d)\s+(\d\d:\d\d)"}.items()}
_WORDS = {"clear": "clear", "list": "list", "why": "why", "next": "next", "what next": "next", "status": "status",
          "now": "status", "wrong when": "wrong"}
px = messages.px


def _f(s):
    return float(s.replace(",", ""))


def parse(text):
    """One line of her text -> the command (the contract's table). Pure."""
    raw = " ".join(str(text or "").split())
    t = raw.lower().rstrip("?").strip()
    m = _RX["mark"].fullmatch(t)
    if m:
        return {"kind": "mark", "idx": m[1].upper(), "k": _f(m[2]), "side": m[3].upper(),
                "role": {"long": "buy", "short": "sell"}.get(m[4], m[4]), "p0": _f(m[5]), "qty": int(m[6]) if m[6] else None}
    if t.startswith("mark ") and not ORDER_RE.search(re.sub(r"\b(buy|sell|long|short)\b", "", t)):
        return {"kind": "mark", "error": MARK}                   # her record, mistyped: the form, not a refusal
    if ORDER_RE.search(t) and not t.startswith(ASKING):
        return {"kind": "refused", "reply": REFUSE}
    if t in _WORDS:
        return {"kind": _WORDS[t]}
    for k in ("line", "watch", "remove"):
        m = _RX[k].fullmatch(t)
        if m:
            if m[2] is None and k != "remove":
                return {"kind": k, "error": f"say s (spot) or f (futures): {k} {px(_f(m[1]))}s or {k} {px(_f(m[1]))}f"}
            return {"kind": k, "level": _f(m[1]), "frame": m[2]}
    m = _RX["zone"].fullmatch(t)
    if m:
        lo, hi = sorted((_f(m[1]), _f(m[3])))
        if not (m[4] or m[2]):
            return {"kind": "zone", "error": f"say s (spot) or f (futures): zone {px(lo)}-{px(hi)}s or …f"}
        return {"kind": "zone", "lo": lo, "hi": hi, "frame": m[4] or m[2]}
    m = _RX["flat"].fullmatch(t)
    if m:
        return {"kind": "flat", "idx": m[1].upper() if m[1] else None}
    m = _RX["whatif"].fullmatch(t)
    if m:
        return {"kind": "whatif", "level": _f(m[1]), "frame": m[2]}
    m = _RX["replay"].fullmatch(t)
    if m:
        return {"kind": "replay", "day": m[1], "upto": m[2]}
    for k in ("note", "ask"):
        if t.startswith(k + " "):
            return {"kind": k, "text": raw[len(k):].strip()}
    return {"kind": "help"}


def for_telegram(text):
    """Her chat's text -> (idx, command): a leading / and an @botname off; the index is NIFTY unless the first word names one."""
    w = str(text or "").strip().lstrip("/").split(None, 1)
    if not w:
        return "NIFTY", ""
    head, rest = w[0].split("@")[0], (w[1] if len(w) > 1 else "")
    return (head.upper(), rest) if head.upper() in IDXS else ("NIFTY", f"{head} {rest}".strip())


def rows(day):
    """The day's command rows, oldest first ([] when none)."""
    return list(confluence_log._rows(os.path.join(DIR, f"cmd_{day}.jsonl")))


def _oi(x):
    return f"{x:.0f}L" if isinstance(x, (int, float)) else "OI ?"


class Day:
    """One day's drawn state. `hold(doc) -> reply` and `trades() -> [trade]` are the server's own hold door and record;
    without them mark / flat say they could not check."""

    def __init__(self, day, hold=None, trades=None):
        self.day, self.hold, self.trades = day, hold, trades
        self._lock = threading.RLock()
        self._st, self._notes, self._prev, self._px0 = {}, [], {}, {}   # _prev: watch id -> the last price seen (memory)
        self._ids = {"line": 0, "zone": 0, "watch": 0}      # the day's ids per kind; `watch` is also the day's 10
        for r in rows(day):
            if r.get("ok"):
                try:
                    self._step(r)
                except Exception:                           # noqa: BLE001 -- a malformed row costs itself, never the day
                    continue
        self._old = {w["id"] for v in self._st.values() for w in v["watches"]}   # set before this process: a gap is possible

    def _s(self, idx):
        return self._st.setdefault(idx, {"watches": [], "lines": [], "zones": []})

    def state(self, idx):
        with self._lock:
            return {k: [dict(x) for x in v] for k, v in self._s(idx).items()}

    def notes(self):
        with self._lock:
            return list(self._notes)

    def armed(self):
        """Any watch today not yet hit (the senses pass looks only then)."""
        with self._lock:
            return any(not w["hit"] and not w.get("gap") for s in self._st.values() for w in s["watches"])

    @staticmethod
    def _matches(s, p):
        L, fr = p["level"], p.get("frame")
        same = lambda x: fr is None or x["frame"] == fr     # noqa: E731
        return ([("lines", x) for x in s["lines"] if x["level"] == L and same(x)]
                + [("zones", x) for x in s["zones"] if L in (x["lo"], x["hi"]) and same(x)]
                + [("watches", x) for x in s["watches"] if x["level"] == L and same(x)])

    def _step(self, r):
        """A persisted row (ok) into the state: the one transition both apply() and the rebuild use."""
        k, s = r["kind"], self._s(r.get("idx"))
        if k in ("watch_hit", "watch_gap"):
            for w in s["watches"]:
                if w["id"] == r["id"]:
                    w.update(hit=r["t"][:5], px=r.get("px")) if k == "watch_hit" else w.update(gap=r["gap"])
            return
        if k == "note":
            self._notes.append(f"note {r['t'][:5]} {parse(r['text'])['text']}")
            return
        if k not in ("line", "zone", "watch", "remove", "clear"):
            return
        p, hm = parse(r["text"]), r["t"][:5]
        if k in self._ids:
            self._ids[k] = max(self._ids[k], r["id"])
        if k == "line":
            s["lines"].append({"id": r["id"], "level": p["level"], "frame": p["frame"], "set": hm})
        elif k == "zone":
            s["zones"].append({"id": r["id"], "lo": p["lo"], "hi": p["hi"], "frame": p["frame"], "set": hm})
        elif k == "watch":
            s["watches"].append({"id": r["id"], "level": p["level"], "frame": p["frame"], "set": hm, "hit": None})
            self._px0[r["id"]] = r.get("px0")
        elif k == "remove":
            for key, x in self._matches(s, p):
                s[key].remove(x)
        else:
            s.update(watches=[], lines=[], zones=[])

    def _write(self, r):
        os.makedirs(DIR, exist_ok=True)
        with open(os.path.join(DIR, f"cmd_{self.day}.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

    def apply(self, idx, text, frame=None, src="page", now=None):
        """One command -> {ok, kind, reply, lines, state} (+ why when not ok). The persisted kinds write one row each (a
        refusal and a failure too); the read-only ones read `frame` (the cached live frame) verbatim and write nothing."""
        now = time.time() if now is None else now
        hms = datetime.fromtimestamp(now, IST).strftime("%H:%M:%S")
        p = parse(text)
        with self._lock:
            ok, reply, lines, extra = self._answer(idx, p, frame, hms)
            if p["kind"] in PERSIST:
                r = dict({"at": int(now), "t": hms, "idx": idx, "kind": p["kind"], "text": " ".join(str(text or "").split()),
                          "ok": ok, "reply": reply, "src": src}, **extra)
                self._write(r)
                if ok:
                    self._step(r)
            return dict({"ok": ok, "kind": p["kind"], "reply": reply, "lines": lines, "state": self.state(idx)},
                        **({} if ok else {"why": reply}))          # every ok: false says why (the faces print `reply`)

    def _answer(self, idx, p, frame, hms):
        """-> (ok, reply, lines, extra fields for the row)."""
        k, s = p["kind"], self._s(idx)
        if p.get("error"):
            return False, p["error"], [], {}
        if k == "refused":
            return False, REFUSE, [], {}
        if k == "help":
            return False, "commands:", list(HELP), {}
        if k in ("line", "watch"):
            lv = f"{px(p['level'])}{p['frame']}"
            have = s["lines"] if k == "line" else [w for w in s["watches"] if not w["hit"]]
            if any(x["level"] == p["level"] and x["frame"] == p["frame"] for x in have):
                return False, (f"line {lv} already drawn" if k == "line" else f"already watching {lv}"), [], {}
            if k == "line":
                return True, f"line {lv} drawn", [], {"id": self._ids["line"] + 1}
            if self._ids["watch"] >= MAX_WATCH:
                return False, f"{MAX_WATCH} watches today already — the day's limit", [], {}
            n, fr = self._ids["watch"] + 1, frame if (frame or {}).get("ok") else {}
            px0 = (fr.get("spot" if p["frame"] == "s" else "fut") or [None])[-1]     # the price when set: a restart's gap check
            return True, f"watching {lv} ({n} of {MAX_WATCH} today)", [], {"id": n, "px0": px0}
        if k == "zone":
            z = f"zone {px(p['lo'])}–{px(p['hi'])}{p['frame']}"
            if any((x["lo"], x["hi"], x["frame"]) == (p["lo"], p["hi"], p["frame"]) for x in s["zones"]):
                return False, f"{z} already drawn", [], {}
            return True, f"{z} drawn", [], {"id": self._ids["zone"] + 1}
        if k == "remove":
            lv = f"{px(p['level'])}{p['frame'] or ''}"
            return (True, f"removed {lv}", [], {}) if self._matches(s, p) else (False, f"nothing at {lv}", [], {})
        if k == "clear":
            return True, f"cleared {sum(len(v) for v in s.values())}", [], {}
        if k == "list":
            ls = ([f"line {px(x['level'])}{x['frame']} · set {x['set']}" for x in s["lines"]]
                  + [f"zone {px(x['lo'])}–{px(x['hi'])}{x['frame']} · set {x['set']}" for x in s["zones"]]
                  + [f"watch {px(x['level'])}{x['frame']} · " + (f"hit {x['hit']} @{px(x.get('px'))}" if x["hit"]
                                                                  else f"set {x['set']}") for x in s["watches"]])
            return True, (f"{len(ls)} on {idx}" if ls else f"nothing drawn on {idx}"), ls, {}
        if k == "note":
            return True, "noted", [], {}
        if k == "mark":
            return self._mark(p, hms)
        if k == "flat":
            return self._flat(p, hms)
        if k == "replay":
            return False, "replay runs in the terminal: python tools/jarvis_cli.py, then replay DAY HH:MM", [], {}
        c = (frame or {}).get("call") if (frame or {}).get("ok") else None
        if not c:                                                   # a frame that could not build says why
            return False, (frame or {}).get("why") or "could not check — no frame built yet", [], {}
        if k == "why":
            return True, f"why {c.get('word')} ({c.get('at')})", list(c.get("why") or []), {}
        if k == "next":
            return True, "next", [x or "could not check — no scenario in this frame" for x in (c.get("up"), c.get("dn"))], {}
        if k == "wrong":
            return True, c.get("wrong_line") or "could not check — no wrong-line in this frame", [], {}
        if k == "status":
            cn = c.get("count")
            return True, f"{idx} {c.get('at')}", [
                " · ".join(x for x in (c.get("word"), c.get("state"), c.get("since") and f"since {c['since']}") if x),
                (f"WITH {cn.get('with')} · AGAINST {cn.get('against')} · N {cn.get('N')} · unread {cn.get('unread')}"
                 if isinstance(cn, dict) else "count: could not check — this frame has no count yet"),
                c.get("leg") or "leg: none in this frame",
                "health: " + (" · ".join(c["missing"]) if c.get("missing") else "every source live")], {}
        if k == "whatif":
            return self._whatif(p, frame, c)
        return True, "voice not configured — the engine's lines:", list(c.get("why") or []), {}     # ask (Task 7's seam)

    def _whatif(self, p, frame, c):
        L, fr = p["level"], p.get("frame") or "s"
        said, step = f"{px(L)}{p.get('frame') or ''}", frame.get("step") or 50
        for side, scen in (("ce", "up"), ("pe", "dn")):
            w = (c.get("walls") or {}).get(side) or {}
            at = w.get("f") if fr == "f" else w.get("k")
            if isinstance(at, (int, float)) and abs(at - L) < step / 2:
                return True, f"what if {said} breaks", [c.get(scen) or "could not check — no scenario in this frame",
                                                        f"{side.upper()} wall {px(w['k'])}s ({px(w.get('f'))}f) {_oi(w.get('oi'))} "
                                                        f"{w.get('state')}"], {}
        fronts = [f for f in ((frame.get("timeline") or [{}])[-1] or {}).get("fronts") or () if isinstance(f.get("k"), (int, float))]
        fut, spot = (frame.get("fut") or [None])[-1], (frame.get("spot") or [None])[-1]
        if fr == "f" and (fut is None or spot is None):
            return False, f"could not check — no spot and fut to place {said} among the walls", [], {}
        Ls = L - (fut - spot) if fr == "f" else L                   # only to find the nearest strikes, never printed
        on = next((f for f in fronts if abs(f["k"] - Ls) < step / 2), None)
        if on:
            return True, f"what if {said} breaks", [f"{px(on['k'])}s {on.get('side')} {_oi(on.get('oi'))} {on.get('state')} · "
                                                   "not the first wall ahead: no scenario"], {}
        near = sorted(fronts, key=lambda f: (abs(f["k"] - Ls), -f["k"]))[:2]
        return True, (f"I don't have {said} in today's frame; nearest: " + ", ".join(f"{px(f['k'])}s {f.get('side')}" for f in near)
                      if near else f"I don't have {said} in today's frame; no walls read"), [], {}

    def _mark(self, p, hms):
        if self.hold is None or self.trades is None:
            return False, "could not check — no hold record in this process", [], {}
        role = {"buy": "long", "sell": "short"}[p["role"]]
        key = (p["idx"], p["k"], p["side"], role)
        mine = next((t for t in self.trades() if not t.get("exit_t")
                     and (t.get("idx"), t.get("k"), t.get("side"), t.get("role")) == key), None)
        if mine:                                                     # her Float mark (or an earlier one) wins
            return False, f"already marked — {mine['id']} in at {mine['t0']} is open (her mark stands)", [], {}
        out = self.hold({"op": "mark", "idx": p["idx"], "k": p["k"], "side": p["side"], "role": role, "t0": hms,
                         "p0": p["p0"], "qty": p["qty"] or 0, "via": "cmd"})
        if not out.get("ok"):
            return False, out.get("why") or "could not check — the hold record said no", [], {}
        tid = ((out.get("trades") or [{}])[-1]).get("id")
        return (True, f"marked {p['idx']} {p['k']:g} {p['side']} {p['role']} @{p['p0']:g} · the voice is on · id {tid}", [],
                {"id": tid})

    def _flat(self, p, hms):
        if self.hold is None or self.trades is None:
            return False, "could not check — no hold record in this process", [], {}
        want = p.get("idx")
        live = [t for t in self.trades() if not t.get("exit_t") and (want is None or t.get("idx") == want)]
        if not live:
            return False, "nothing open to flat" + (f" on {want}" if want else ""), [], {}
        done, why = [], []
        for t in live:
            out = self.hold({"op": "exit", "id": t["id"], "exit_t": hms})
            (done.append(t["id"]) if out.get("ok") else why.append(f"{t['id']}: {out.get('why')}"))
        if not done:
            return False, why[0], why, {}
        return True, f"flat · receipt {hms[:5]}", [f"out {i} at {hms}" for i in done] + why, {"ids": done}

    def check_watches(self, idx, spot, fut, hm, card=None, now=None):
        """The senses pass: each live watch of `idx` against spot (an s level) or fut (f). A touch = the price on or across
        the level since the last look. A hit fires ONCE: its row (with card(): the word, count and last answer) is written
        and returned. The first look only remembers the price -- except for a watch set before this process whose price at
        set is on the other side now: it was crossed unseen, so it says `could not check — gap <set>–<now>` once (a
        watch_gap row), never a hit. A missing price is skipped."""
        out = []
        with self._lock:
            for w in self._s(idx)["watches"]:
                x = spot if w["frame"] == "s" else fut
                if w["hit"] or w.get("gap") or not isinstance(x, (int, float)) or x <= 0:
                    continue
                was, self._prev[w["id"]] = self._prev.get(w["id"]), x
                p0 = self._px0.get(w["id"])
                if (was is None and w["id"] in self._old and isinstance(p0, (int, float))
                        and (p0 - w["level"]) * (x - w["level"]) <= 0):
                    r = {"at": int(time.time() if now is None else now), "t": hm, "idx": idx, "kind": "watch_gap", "ok": True,
                         "id": w["id"], "level": w["level"], "frame": w["frame"], "px": x, "gap": f"{w['set']}–{hm}"}
                    self._write(r)
                    self._step(r)
                    out.append(r)
                    continue
                if was is None or (was - w["level"]) * (x - w["level"]) > 0:
                    continue
                c = card() if card else {}
                r = {"at": int(time.time() if now is None else now), "t": hm, "idx": idx, "kind": "watch_hit", "ok": True,
                     "id": w["id"], "level": w["level"], "frame": w["frame"], "px": x,
                     "card": {k: (c or {}).get(k) for k in ("word", "count", "answer")}}
                self._write(r)
                self._step(r)
                out.append(r)
        return out
