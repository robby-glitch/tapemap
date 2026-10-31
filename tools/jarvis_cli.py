"""tools/jarvis_cli.py -- THE TERMINAL JARVIS (Jarvis v3 Task 4): a `jarvis> ` prompt that prints the brain's card and sends
her commands to the server's one grammar (POST /api/jarvis/cmd, src "cli"). It decides nothing: the card is the server's,
the replies are the server's, printed verbatim. Display only; I read, I don't place.

    python tools/jarvis_cli.py [--base http://127.0.0.1:8765] [--idx NIFTY] [--frame saved_frame.json]

`now` GETs /api/jarvis/card and prints it as a block; `replay DAY HH:MM` GETs the replay frame once per day (cached in
memory) and prints that minute's call from its `calls`; `idx`, `help`, `quit` are local; everything else goes to the
grammar. `ask <text>`: the server answers "thinking", then the voice fills the card -- looked at every ASK_POLL_S until
it answers. `now` shows the card's VOICE and the day's BRIEF when it has them. `--frame` runs offline on a saved
/api/jarvis frame: `now` = its `call`, `replay` = its `calls[i]`; a command that needs the server says so. Any server failure prints `could not check — <reason>`. Stdlib only.
"""
import argparse
import datetime
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import readline  # noqa: F401  -- line editing + history where the platform has it (not on Windows: fine)
except ImportError:
    pass

CC = "could not check — "
ASK_POLL_S = 1.5                                # `ask`: the voice answers on the card, looked at every 1.5 s [I] ...
ASK_WAIT_MAX_S = 60                             # ... for up to 2 x the voice's 30 s model call [I]
IDXS = ("NIFTY", "SENSEX", "BANKNIFTY")
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
GRAMMAR = ("why", "why?", "next", "what", "status", "wrong", "if", "watch", "line", "zone", "remove", "clear", "list",
           "mark", "flat", "note", "ask")
ORDER = re.compile(r"\b(buy|sell|lots|order|place|square|exit now)\b")    # offline only: online the server refuses + logs
HELP = """now · why · next · status · wrong when · what if 22800
watch 22800s · line 22750f · zone 22680-22720f · remove 22750 · clear · list
mark NIFTY 23000 PE buy 325 · flat · note RBI 11:00 · ask <text>
replay 2026-10-21 10:30 · idx NIFTY|SENSEX|BANKNIFTY · help · quit
display only: I read, I don't place."""


def _txt(v):
    """One field as one line: a sentence verbatim; a dict by its `line`, else `key value · …`; a list joined. '' = absent."""
    if isinstance(v, dict):
        if "line" in v:
            return _txt(v["line"])
        v = " · ".join(f"{k} {x}" for k, x in v.items() if x not in (None, "", [], {}))
    elif isinstance(v, list):
        v = " · ".join(str(x) for x in v if x is not None)
    return "" if v is None else str(v)


def _frags(s):
    """An engine sentence cut at its own ' · ' separators, never inside brackets: one cell per line. Verbatim otherwise."""
    out = []
    for p in str(s).split(" · "):
        if out and out[-1].count("(") > out[-1].count(")"):
            out[-1] += " · " + p
        else:
            out.append(p)
    return out


def _block(prefix, text):
    """`prefix` + the first fragment, each further fragment on its own line under it (the ≤ 6-words-per-cell rule)."""
    f = _frags(text)
    return [prefix + f[0]] + [" " * len(prefix) + x for x in f[1:]]


def render_card(card: dict) -> str:
    """The CARD as a fixed-width terminal block. Pure. The engine's sentences and levels verbatim, one ' · ' fragment
    per line; a key the card lacks (or null) is named once on the last line -- never a zero, never invented."""
    g, out, absent = card.get, [], []

    def row(label, v):
        t = _txt(v)
        if t:
            out.extend(_block(f"{label:<10}", t))
        else:
            absent.append(label.lower())

    out.append(" · ".join(str(x) for x in (g("idx"), g("day"), g("at"), {True: "live", False: "replay"}.get(g("live")),
                                            g("asof") and "asof " + g("asof")) if x))
    word = [x for x in (g("word"), g("state"), g("since") and "since " + g("since")) if x]
    absent += [k for k in ("word", "state", "since") if not g(k)]
    if word:
        out.append(f"{'WORD':<10}" + " · ".join(word))
    c = g("count") if isinstance(g("count"), dict) else {}
    n = " · ".join(f"{lab} {c[k]}" for k, lab in (("with", "WITH"), ("against", "AGAINST"), ("N", "N"), ("unread", "unread"))
                   if c.get(k) is not None)
    if n:
        out.append(f"{'COUNT':<10}{n}")          # the count's own one-word cells: one line
    else:
        absent.append("count")
    for p in c.get("pieces") or ():
        if p.get("text"):
            out.extend(_block(f"  {str(p.get('side') or '?'):<8}", p["text"]))
    row("LEG", g("leg"))
    row("PAUSE", g("pause"))
    row("HOW MUCH", g("how_much"))
    row("WHERE", g("where"))
    e = g("expression") if isinstance(g("expression"), dict) else {}
    row("BUYER", e.get("buyer"))
    row("SELLER", e.get("seller"))
    row("PICK", e.get("pick"))
    row("WRONG", g("wrong_line"))
    row("NO TRADE", g("no_trade"))
    row("SELF", g("self"))
    v = g("voice")
    if isinstance(v, dict):                     # Task 7: the model's narration, or why it fell back (optional: never "absent")
        said = [f"fell back — {v.get('why')}"] if v.get("fell_back") else [str(x) for x in v.get("lines") or () if x]
        for i, ln in enumerate(said):
            out.extend(_block(f"{'' if i else 'VOICE':<10}", ln))
    b = g("brief")
    if isinstance(b, dict) and b.get("lines"):  # Task 7: the day's pre-open brief, shown all day
        out.append(f"{'BRIEF':<10}" + (f"at {b['at']}" if b.get("at") else "today"))
        for ln in b["lines"]:
            out.extend(_block(" " * 10, str(ln)))
    h = g("health")
    if isinstance(h, dict):
        m = h.get("missing")
        out.append(f"{'HEALTH':<10}" + ("missing none" if m == [] else f"{len(m)} missing" if m else "missing not in the card"))
        for lab, xs in (("missing", m or ()), ("note", h.get("notes") or ())):
            for x in xs:
                out.extend(_block(f"  {lab:<8}", x))
    else:
        absent.append("health")
    if absent:
        out.append("NOT IN CARD  " + " · ".join(absent))
    return "\n".join(out)


def card_from_call(frame: dict, c: dict) -> dict:
    """A saved frame's `call` (or `calls[i]`) in the card's shape. Keys the call lacks stay None, never invented."""
    card = {k: c.get(k) for k in ("word", "state", "lean", "since", "count", "leg", "pause", "how_much", "where",
                                  "wrong_line", "up", "dn", "no_trade", "self")}
    card.update(idx=frame.get("idx"), day=frame.get("day"), at=c.get("at"), live=False,
                expression=c.get("expression") or {k: c.get(k) for k in ("buyer", "seller", "pick")},
                health=c.get("health") or ({"missing": c["missing"]} if "missing" in c else None))
    return card


def parse_cli(line: str):
    """One typed line -> (kind, arg). Local: noop / quit / help / now / idx / replay / bad (arg = the usage); all else cmd."""
    s = line.strip()
    low = s.lower()
    w = low.split()
    if not w:
        return "noop", None
    if low in ("quit", "q"):
        return "quit", None
    if low in ("help", "?"):
        return "help", None
    if low == "now":
        return "now", None
    if w[0] == "idx":
        return ("idx", w[1].upper()) if len(w) == 2 and w[1].upper() in IDXS else ("bad", "idx NIFTY|SENSEX|BANKNIFTY")
    if w[0] == "replay":
        m = re.fullmatch(r"replay\s+(\d{4}-\d\d-\d\d)\s+(\d\d:\d\d)", low)
        return ("replay", m.groups()) if m else ("bad", "replay YYYY-MM-DD HH:MM")
    return "cmd", s


def call_server(base, path, body=None, timeout=10):
    """THE one HTTP door: GET, or POST JSON when `body` is given -> (doc, None) or (None, 'could not check — <reason>')."""
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return None, f"{CC}the server answered {e.code} {e.reason}"
    except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
        return None, f"{CC}the server at {base} did not answer ({getattr(e, 'reason', e)})"
    except ValueError:
        return None, CC + "the server's reply was not JSON"
    return (doc, None) if isinstance(doc, dict) else (None, CC + "the server's reply was not an object")


def _not_ok(doc):
    why = str(doc.get("why") or "the server said not ok")
    return why if why.startswith(CC) else CC + why


class Session:
    """One terminal: the server (or a saved frame), the index, and the replay frames fetched so far."""

    def __init__(self, base, idx="NIFTY", frame=None):
        self.base, self.idx, self.frame = base.rstrip("/"), idx, frame
        self._replays = {}   # ponytail: unbounded, ~15 MB a day held; a session replays a handful of days
        self.sleep = time.sleep

    def handle(self, line):
        """One line -> the text to print ('' = nothing); None = quit."""
        kind, arg = parse_cli(line)
        if kind == "quit":
            return None
        if kind == "noop":
            return ""
        if kind == "help":
            return HELP
        if kind == "bad":
            return "usage: " + arg
        if kind == "idx":
            if self.frame is not None:
                return f"offline — the saved frame is {self.frame.get('idx')}"
            self.idx = arg
            return f"idx {arg}"
        if kind == "now":
            return self.now()
        if kind == "replay":
            return self.replay(*arg)
        if self.frame is not None:
            first = arg.split()[0].lower()
            if first in GRAMMAR:
                return f"offline — {first} needs the server"
            return "I read, I don't place." if ORDER.search(arg.lower()) else HELP
        doc, why = call_server(self.base, "/api/jarvis/cmd", {"idx": self.idx, "text": arg, "src": "cli"})
        if why:
            return why
        reply = doc.get("reply")
        if doc.get("ok") is False and not reply:
            return _not_ok(doc)
        out = [reply] + [x for x in doc.get("lines") or () if x and x != reply]
        if doc.get("kind") == "ask" and str(reply).startswith("thinking"):
            out += self.voice(" ".join(arg.split()[1:]))       # the question as jarvis_cmd.parse keeps it
        return "\n".join(str(x) for x in out if x) or CC + "the server sent an empty reply"

    def voice(self, q):
        """Task 7: `ask` answers on the card's voice -- looked at every ASK_POLL_S until its `q` is hers (answered or fell
        back), up to ASK_WAIT_MAX_S; a server that does not answer ends the wait with its reason."""
        waited = 0.0
        while waited < ASK_WAIT_MAX_S:
            self.sleep(ASK_POLL_S)
            waited += ASK_POLL_S
            card, why = call_server(self.base, "/api/jarvis/card?" + urllib.parse.urlencode({"idx": self.idx}))
            if why:
                return [why]
            v = card.get("voice")
            if isinstance(v, dict) and v.get("q") == q:
                return ([str(x) for x in v.get("lines") or () if x]
                        + ([f"voice fell back — {v.get('why')}"] if v.get("fell_back") else []))
        return [f"the voice has not answered in {ASK_WAIT_MAX_S:g} s — `now` shows the card's voice when it does"]

    def now(self):
        if self.frame is not None:
            c = self.frame.get("call")
            return render_card(card_from_call(self.frame, c)) if c else CC + "the saved frame has no call"
        doc, why = call_server(self.base, "/api/jarvis/card?" + urllib.parse.urlencode({"idx": self.idx}))
        return why or (_not_ok(doc) if doc.get("ok") is False else render_card(doc))

    def replay(self, day, hm):
        f = self.frame
        if f is not None:
            if day != f.get("day"):
                return f"{CC}the saved frame is {f.get('day')}"
        else:
            today = datetime.datetime.now(IST).strftime("%Y-%m-%d")
            f = self._replays.get((self.idx, day))
            if f is None or (day == today and hm not in f["mins"]):   # today's record grows: refetch past its end
                q = {"idx": self.idx, "day": day, "fill": "1"}
                if day == today:                                      # no upto today = the live frame, which has no calls
                    m = int(hm[:2]) * 60 + int(hm[3:]) + 1
                    q["upto"] = f"{m // 60:02d}:{m % 60:02d}"
                doc, why = call_server(self.base, "/api/jarvis?" + urllib.parse.urlencode(q), timeout=300)
                if why:
                    return why
                if doc.get("ok") is False:
                    return _not_ok(doc)
                if not doc.get("calls") or not doc.get("mins"):
                    return CC + "the replay frame carries no calls"
                f = self._replays[(self.idx, day)] = doc
        mins, calls = f.get("mins") or [], f.get("calls") or []
        if len(calls) != len(mins):
            return f"{CC}the frame's calls ({len(calls)}) do not line up with its minutes ({len(mins)})"
        if hm not in mins:
            return f"{CC}{hm} is not on the {f.get('day')} record"
        return render_card(card_from_call(f, calls[mins.index(hm)]))


def main(argv=None):
    a = argparse.ArgumentParser(description="the terminal Jarvis: the card and her commands (display only)")
    a.add_argument("--base", default="http://127.0.0.1:8765")
    a.add_argument("--idx", default="NIFTY", type=str.upper, choices=IDXS)
    a.add_argument("--frame", help="a saved /api/jarvis frame (JSON): run offline on it")
    o = a.parse_args(argv)
    frame = None
    if o.frame:
        try:
            with open(o.frame, encoding="utf-8") as fh:
                frame = json.load(fh)
        except (OSError, ValueError) as e:
            print(f"{CC}the frame {o.frame} did not load ({e})")
            return 1
    if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:                                       # a pipe on Windows is cp1252: ▲ ▼ ± σ would not print
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    s = Session(o.base, o.idx, frame)
    print(f"jarvis · {'offline on ' + str(o.frame) if frame else o.base} · {o.idx} · help for the commands")
    while True:
        try:
            line = input("jarvis> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        try:
            r = s.handle(line)
        except Exception as e:                     # an odd reply shape must never kill the terminal
            r = f"{CC}{type(e).__name__}: {e}"
        if r is None:
            return 0
        if r:
            print(r)


if __name__ == "__main__":
    sys.exit(main())
