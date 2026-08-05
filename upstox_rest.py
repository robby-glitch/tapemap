"""Upstox's candle REST, throttled. The only place this repo calls it.

Two callers, one endpoint:

  * the **09:15 OI baseline** per option leg, which is what makes `oi_chg`
    mean something (`upstox_adapter.session_open_oi`)
  * the **tape**, once the bar path moves off Dhan

Both want the same response, so both come through `intraday`.

THROTTLED ON PURPOSE. A chain of ~34 legs is ~34 calls at startup. Upstox's
data APIs are rate limited and a burst gets 429s that look, from the log, like
the token failing. `MIN_GAP` spaces them; ~9s for a full chain, paid once per
session. It is not a loop that runs per poll -- if you find yourself calling
this every cycle, that is the 2026-07-27 outage being rebuilt (a 37MB fetch
per cycle froze the tape for a session).

Read-only. Never logs the token.
"""

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.upstox.com/v2"
MIN_GAP = 0.25            # seconds between calls; data APIs are capped
TIMEOUT = 30

# Cloudflare answers Python's default User-Agent with Error 1010 -- a 403 that
# reads exactly like an auth failure and is not one (measured 2026-08-05).
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

_lock = threading.Lock()
_last = [0.0]


def _throttle():
    with _lock:
        gap = time.monotonic() - _last[0]
        if gap < MIN_GAP:
            time.sleep(MIN_GAP - gap)
        _last[0] = time.monotonic()


def _get(url, tok):
    _throttle()
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {tok}", "Accept": "application/json",
        "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def intraday(key, tok, interval="1minute"):
    """Today's candles for one instrument, NEWEST FIRST as Upstox sends them.

    Returns [] rather than raising when the instrument simply has no bars --
    a strike listed but not yet traded is normal, and must not take a chain
    poll down with it. A transport or auth failure still raises, because that
    is not the same thing and should not be silently read as "no data".
    """
    url = (f"{BASE}/historical-candle/intraday/"
           f"{urllib.parse.quote(key, safe='')}/{interval}")
    try:
        data = _get(url, tok)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    return (data.get("data") or {}).get("candles") or []


def baselines(meta, tok, on_error=None):
    """{(strike, side): 09:15 open interest} for every leg in `meta`.

    The baseline `oi_chg` is measured from. A leg whose candles cannot be
    fetched is OMITTED, not defaulted: a missing key leaves `oi_chg` at "not
    known", while a zero would report a change equal to the entire book.
    """
    import upstox_adapter                        # local: keeps this import-light

    out = {}
    for key, (strike, side) in meta.items():
        try:
            base = upstox_adapter.session_open_oi(intraday(key, tok))
        except Exception as e:                   # noqa: BLE001
            if on_error:
                on_error(key, e)
            continue
        if base:
            out[(strike, side)] = base
    return out
