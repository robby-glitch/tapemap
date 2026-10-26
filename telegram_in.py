"""telegram_in.py -- READ-ONLY Telegram replies: /now and /last, from her one private chat only (her word, 26 Oct: "add
read-only Telegram replies: /now and /last, only from my chat"; follows telegram_out.py, NOTEPAD A101).
  RECEIVER  one daemon thread (`start`, from server.main beside telegram_out.start, live only): a getUpdates long-poll
            (POLL_S), a back-off of 5 s up to 60 s on any error; it never raises out of the thread and never blocks the
            server. At start the queued backlog is acknowledged and not answered, so a restart never replays old commands.
  WHO       only message.chat.id == telegr/chat.txt AND a private chat. Any other chat is ignored: no reply, and its text is
            never logged (one "ignored" line an hour, with no content). No chat.txt (or token): the receiver does not start.
  WHAT      /now  -> "NOW HH:MM" and the NOW rows exactly as GET /api/messages gives them
            /last -> the last LAST_N message lines, newest first (the window's order), each with its time
            else  -> HELP. At most CAP replies a minute.
  READ-ONLY the provider (server._msg_reply) is the stream's memory: nothing here computes, writes, or places an order.
Reuses telegram_out's config reader, scrub and HTTP seam (`_open`, `send`); THE TOKEN lives only in a request URL and every
logged error goes through `scrub`.
tools/telegram_setup.py also calls getUpdates, once: Telegram allows ONE long-poller at a time (the other gets a 409, which
backs off here) and this receiver acknowledges what it reads. Run the setup before chat.txt exists, or with the server stopped.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime

import telegram_out as out
from chain_live import IST

POLL_S, CAP, LAST_N = 25, 10, 10
BACKOFF_S, MAX_BACKOFF_S, QUIET_S, STALE_S = 5, 60, 3600, 120
HELP = "/now · /last"
log = logging.getLogger("tapemap")
_sleep = time.sleep                           # the back-off wait: a test seam, as telegram_out._open is for the network
_ON = False
_SENT = []                                    # epoch s of the last minute's replies (the cap)
_QUIET = {}                                   # log key -> when it last logged: each line at most once an hour


def _once(key, msg, *a, now=None):
    t = time.time() if now is None else now
    if key not in _QUIET or t - _QUIET[key] >= QUIET_S:
        _QUIET[key] = t
        log.warning(msg, *a)


def _get(tok, offset, wait):
    """One getUpdates (waiting up to `wait` s) -> its updates. Telegram's own 'not ok' (a 409: another poller) raises."""
    q = urllib.parse.urlencode({"timeout": wait, "offset": offset})
    with out._open(urllib.request.Request(out.API.format(tok, "getUpdates") + "?" + q), timeout=wait + out.TIMEOUT_S) as r:
        rep = json.loads(r.read().decode("utf-8") or "{}")
    if not rep.get("ok"):
        raise RuntimeError(f"Telegram said: {rep.get('description') or 'not ok'}")
    return rep.get("result") or []


def backlog(tok):
    """Acknowledge everything already queued and answer none of it -> the first offset to poll from."""
    off = 0
    while True:
        top = max((int(u["update_id"]) + 1 for u in _get(tok, off, 0)), default=0)
        if top <= off:
            return off
        off = top


def answer(cmd, provider, d):
    """The reply text for a command (d: the IST time now). Read-only, never blank: a could-not-check says why."""
    if cmd not in ("/now", "/last"):
        return HELP
    try:
        rep = provider()
    except Exception as e:  # noqa: BLE001 -- a stream that raises is still an answer
        rep = {"ok": False, "why": f"could not check — {type(e).__name__}"}
    why, hm = rep.get("why") or "could not check", d.strftime("%H:%M")
    if cmd == "/last":
        if not rep.get("ok"):
            return why
        ms = sorted(rep.get("msgs") or (), key=lambda m: (m.get("t") or "", m.get("at") or 0), reverse=True)[:LAST_N]
        return "\n".join(m["line"] for m in ms) or "koi message nahi"
    if not rep.get("ok"):
        return f"NOW {hm} · {why}"
    if d.weekday() >= 5 or hm < out.OPEN_HM:
        return f"NOW {hm} · market abhi khula nahi"
    rows, hm = [r["line"] for r in rep.get("now") or ()], hm + _late(rep.get("asof"), d)
    return f"NOW {hm}\n" + "\n".join(rows) if rows else f"NOW {hm} · koi read nahi"


def _late(asof, d):
    """' · purana — stream HH:MM se ruka' when the stream's last pass ("HH:MM:SS"; it runs every 20 s) is over STALE_S old."""
    try:
        h, m, s = (int(x) for x in str(asof).split(":"))
    except ValueError:
        return ""
    late = d.hour * 3600 + d.minute * 60 + d.second - (h * 3600 + m * 60 + s) > STALE_S
    return f" · purana — stream {h:02d}:{m:02d} se ruka" if late else ""


def handle(u, cfg, provider, now=None):
    """One update: from her private chat, within the cap -> the reply sent; anything else is ignored."""
    m = u.get("message")
    if not m:
        return
    ch = m.get("chat") or {}
    if ch.get("type") != "private" or str(ch.get("id")) != cfg[1]:
        _once("ignored", "telegram: ignored update from another chat", now=now)
        return
    t = time.time() if now is None else now
    _SENT[:] = [x for x in _SENT if t - x < 60]
    if len(_SENT) >= CAP:
        return
    _SENT.append(t)
    cmd = ((m.get("text") or "").split() or [""])[0].split("@")[0].lower()      # "/now@tapemap_x_bot" is /now
    out.send(cfg[0], cfg[1], answer(cmd, provider, datetime.fromtimestamp(t, IST)))


def poll(cfg, off, provider, now=None):
    """One long-poll -> the next offset. The offset moves before an update is handled: a poison update is never fetched twice."""
    for u in _get(cfg[0], off, POLL_S):
        off = max(off, int(u["update_id"]) + 1)
        try:
            handle(u, cfg, provider, now)
        except Exception as e:  # noqa: BLE001 -- one update never stops the receiver
            _once("reply", "telegram: a reply failed (%s)", out.scrub(f"{type(e).__name__}: {e}"))
    return off


def _run(provider):
    off, wait = None, 0
    while True:
        try:
            cfg = out.config()
            if cfg is None:
                raise RuntimeError("telegr/ has no token or chat id")
            off = backlog(cfg[0]) if off is None else poll(cfg, off, provider)
            wait = 0
        except Exception as e:  # noqa: BLE001 -- the receiver never dies and never raises into the server
            wait = min(MAX_BACKOFF_S, wait * 2 or BACKOFF_S)
            _once("poll", "telegram: the receiver could not poll (%s); retrying", out.scrub(f"{type(e).__name__}: {e}"))
            _sleep(wait)


def start(provider):
    """server.main calls this once, live only, after telegram_out.start(). No chat.txt (or token): no receiver. -> started."""
    global _ON
    if _ON or out.config() is None:
        return False
    _ON = True
    threading.Thread(target=_run, args=(provider,), name="telegram_in", daemon=True).start()
    log.info("telegram: /now and /last ON -- her chat only, read-only")
    return True
