"""telegram_out.py -- THE MESSAGE STREAM's outbound Telegram alerts (spec docs/superpowers/specs/
2026-10-25-message-window-telegram-design.md §4; NOTEPAD A101).

OUTBOUND ONLY: sendMessage to her one chat. Nothing here reads a command (telegram_in.py answers /now and /last, read-only);
nothing here places an order. The text is the window's own line (messages.line), the day's first one prefixed with the date.
  WHAT    `wants`: SETUP; READ to LEAN / TREND; TRADE WARN / EXIT; every HEALTH line. QUIT, LEG, DIN and RANGE / WAIT churn
          stay in the window (a READ QUIT fires late, and was 23 of the 32 Telegram lines on 23 Oct).
  GATE    `gate`: weekdays 09:15-15:40 IST, and the message's own close within FRESH_S of now -- a restart rebuilds the
          morning into the window, never into her phone. `offer` queues each (day, key) once.
  CAP     `plan`: at most CAP sends a minute; past that, the rest of the minute go as ONE batch message.
  SENDER  one daemon thread (`start`, from server.main, never under --mock-chain), stdlib urllib, TIMEOUT_S, RETRIES more
          tries; a failure is logged at most once an hour and never raised into the server.
CONFIG (hers, git-ignored telegr/): bot.txt holds the token (the token-shaped line; a "key: " prefix is fine), chat.txt the
chat id (tools/telegram_setup.py writes it). No chat.txt: OFF, and the window still works. THE TOKEN lives only in the
request URL: never in a log line, a message, or any text this module writes (`scrub`).
"""
from __future__ import annotations

import json
import logging
import os
import queue
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime

from chain_live import IST

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegr")
API = "https://api.telegram.org/bot{}/{}"
TOKEN_RE = re.compile(r"\d+:[A-Za-z0-9_-]{30,}")
CAP, TIMEOUT_S, RETRIES = 6, 8, 2
FRESH_S, QUIET_S, TICK_S = 600, 3600, 2       # a line older than 10 min is not sent; a failure logged once an hour
OPEN_HM, CLOSE_HM = "09:15", "15:40"
log = logging.getLogger("tapemap")
_open = urllib.request.urlopen                # the one network seam: tests replace it, so no test reaches Telegram
_ON = False
_Q = queue.SimpleQueue()                      # messages offered, for the sender thread (the gate runs again at send)
_SENT = set()                                 # (day, key) already queued
_HELD = []                                    # over this minute's cap: the next minute's first send
_USED = {"minute": None, "n": 0, "day": None}
_FAIL = {"at": 0.0}


def scrub(s):
    """Any token-shaped text out of a string bound for a log or a screen."""
    return TOKEN_RE.sub("<token>", str(s))


def token():
    """Her bot token from telegr/bot.txt (its token-shaped line), or None."""
    try:
        with open(os.path.join(DIR, "bot.txt"), encoding="utf-8") as f:
            m = TOKEN_RE.search(f.read())
    except OSError:
        return None
    return m.group(0) if m else None


def chat():
    """Her chat id from telegr/chat.txt, or None (Telegram is OFF)."""
    try:
        with open(os.path.join(DIR, "chat.txt"), encoding="utf-8") as f:
            c = f.read().strip()
    except OSError:
        return None
    return c if re.fullmatch(r"-?\d+", c) else None


def config():
    """(token, chat id) when both are there, else None: OFF."""
    t, c = token(), chat()
    return (t, c) if t and c else None


def wants(m):
    """The alert subset (spec §4). A READ QUIT is not in it: it fires late, and was 23 of 32 lines on 23 Oct. A line marked
    `quiet` (A131: a BAN SAKTA past the day's budget, palat.budget) stays in the window only."""
    k, w = m.get("kind"), str(m.get("word") or "")
    if m.get("quiet"):
        return False
    if k in ("SETUP", "HEALTH"):
        return True
    if k == "TRADE":
        return w in ("WARN", "EXIT")
    return k == "READ" and w.split(" → ")[-1].startswith(("LEAN", "TREND"))


def gate(m, d):
    """Weekdays 09:15-15:40 IST (d: an aware IST datetime), and the message's own close within FRESH_S of d. A TRADE line's `t`
    is its voice trigger's time, which can be long past when the line was said: TRADE reads its write time `at` instead."""
    if d.weekday() >= 5 or not OPEN_HM <= d.strftime("%H:%M") < CLOSE_HM:
        return False
    if m.get("kind") == "TRADE" and isinstance(m.get("at"), (int, float)):
        return -60 <= d.timestamp() - m["at"] <= FRESH_S
    try:
        h, mi = (int(x) for x in str(m.get("t"))[:5].split(":"))
    except ValueError:
        return False
    return -60 <= d.hour * 3600 + d.minute * 60 + d.second - (h * 3600 + mi * 60) <= FRESH_S


def offer(msgs, now=None):
    """server._msg_write hands every newly written message here. The subset that passes the gate is queued once per (day,
    key); a no-op until start() (the suite, a --mock-chain run). -> how many were queued."""
    if not _ON:
        return 0
    d = datetime.fromtimestamp(time.time() if now is None else now, IST)
    n = 0
    for m in msgs:
        k = (d.strftime("%Y-%m-%d"), m.get("key"))
        if wants(m) and gate(m, d) and k not in _SENT:
            _SENT.add(k)
            _Q.put(m)
            n += 1
    return n


def plan(lines, used):
    """(texts, sends) for one tick: every line alone while this minute has room under CAP; past it, the rest go as ONE batch
    message; with no room left, nothing until the next minute."""
    free = CAP - used
    if not lines or free <= 0:
        return [], 0
    if len(lines) <= free:
        return list(lines), len(lines)
    rest = lines[free - 1:]
    return list(lines[:free - 1]) + [f"+{len(rest)} ek saath:\n" + "\n".join(rest)], free


def send(tok, chat_id, text):
    """One sendMessage, RETRIES more tries on failure -> True when Telegram said ok. Never raises."""
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}).encode()
    err = "no reply"
    for _ in range(1 + RETRIES):
        try:
            with _open(urllib.request.Request(API.format(tok, "sendMessage"), data=body), timeout=TIMEOUT_S) as r:
                rep = json.loads(r.read().decode("utf-8") or "{}")
            if rep.get("ok"):
                return True
            err = f"Telegram said: {rep.get('description') or 'not ok'}"
        except Exception as e:  # noqa: BLE001 -- a send never raises into the server
            err = f"{type(e).__name__}: {e}"
    _failed(err)
    return False


def _failed(err, now=None):
    t = time.time() if now is None else now
    if t - _FAIL["at"] >= QUIET_S:
        _FAIL["at"] = t
        log.warning("telegram: a send failed (%s); the window still has every message", scrub(err))


def _drain(now=None):
    """One sender tick: the queued lines, sent within the cap (the day's first with the date). -> the texts sent."""
    d = datetime.fromtimestamp(time.time() if now is None else now, IST)
    minute, day = d.strftime("%Y-%m-%d %H:%M"), d.strftime("%Y-%m-%d")
    if _USED["minute"] != minute:
        _USED.update(minute=minute, n=0)
    while True:
        try:
            _HELD.append(_Q.get_nowait())
        except queue.Empty:
            break
    _HELD[:] = [m for m in _HELD if gate(m, d)]   # a line that went stale while queued or held is dropped, never sent late
    texts, n = plan([m["line"] for m in _HELD], _USED["n"])
    if not texts:
        return []
    _HELD.clear()
    _USED["n"] += n
    cfg = config()
    if cfg is None:                               # chat.txt missing: OFF -- the lines stay in the window only
        return []
    if _USED["day"] != day:
        _USED["day"] = day
        texts[0] = f"{d.strftime('%a %d %b')}\n{texts[0]}"
    for x in texts:
        send(cfg[0], cfg[1], x)
    return texts


def _run():
    while True:
        time.sleep(TICK_S)
        try:
            _drain()
        except Exception as e:  # noqa: BLE001 -- the sender never dies and never raises into the server
            _failed(f"sender tick: {type(e).__name__}: {e}")


def start():
    """server.main calls this once, live only (never under --mock-chain): the sender thread. While chat.txt is missing
    Telegram stays OFF; tools/telegram_setup.py can write it at any time, with no restart. Logs ON / OFF, never the token."""
    global _ON
    if _ON:
        return
    _ON = True
    threading.Thread(target=_run, name="telegram", daemon=True).start()
    log.info("telegram: %s", "ON -- alerts go to her chat" if config()
             else "OFF -- no telegr/chat.txt yet (python tools/telegram_setup.py)")
