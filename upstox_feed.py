"""The Upstox socket, held open, with the latest tick per instrument.

WHAT IT IS. A daemon thread that connects to the v3 market-data feed,
subscribes to a fixed set of instrument keys, decodes every frame and keeps
only the newest one per key. `snapshot()` hands that map to
`upstox_adapter.chain_payload`, which turns it into the shape
`chain_live.normalize` already eats.

WHY A SNAPSHOT AND NOT A STREAM. Everything downstream -- chain_metrics, the
GEX layer, the walls, ZONE READ -- is written against a periodic SNAPSHOT of
the chain, because that is what a REST poller produced. A socket delivers
deltas at whatever rate the exchange sends them. Rewriting the engine to be
event-driven would be a far larger change than this migration, and would throw
away the property that a snapshot is internally consistent: every strike read
at the same instant. So the socket fills a mailbox and the existing poll
cadence reads it. The engine never learns that its data source changed.

**CONNECTED IS NOT RECEIVING.** On 2026-07-27 this tool served a frozen tape
for most of a session while every health check said fine. A socket that is
open but silent looks identical to a quiet market, so `age()` reports seconds
since the last DECODED FRAME, not since connection, and `healthy()` requires
both. Anything that displays this feed must show staleness from `age()`; a
green dot sourced from `connected` alone would reproduce that outage exactly.

MODE. Options are subscribed `full`, not `option_greeks`: `full` is a superset
that adds `atp` (the chain's `avg`), and its 2000-key cap is far above the ~40
this tool uses. See `upstox_adapter`'s field map.

The subscribe frame MUST be sent as BINARY. Sent as text the socket stays open
and simply never delivers a feed -- a silent no-op indistinguishable from a
closed market.
"""

import json
import ssl
import threading
import time
import uuid

import websocket

import upstox_proto

WS_URL = "wss://api.upstox.com/v3/feed/market-data-feed"
TOKEN_FILE = ".upstox_token"

# Cloudflare answers Python's default User-Agent with Error 1010 -- a 403 that
# reads exactly like an auth failure and is not one (measured 2026-08-05).
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

RECV_TIMEOUT = 5          # so the loop can notice a stop request
STALE_AFTER = 30          # seconds without a frame before healthy() goes false
BACKOFF = (1, 2, 5, 10, 30)


def read_token(path=TOKEN_FILE):
    """The OAuth access token. Never logged, never returned in status."""
    with open(path, encoding="utf-8") as f:
        tok = f.read().strip()
    if not tok:
        raise RuntimeError(f"{path} is empty — run: python upstox_auth.py")
    return tok


def sub_frame(keys, mode="full", method="sub"):
    """The subscribe message. Callers must send the result as a BINARY frame."""
    return json.dumps({"guid": str(uuid.uuid4()), "method": method,
                       "data": {"mode": mode, "instrumentKeys": list(keys)}}
                      ).encode()


class UpstoxFeed(threading.Thread):
    """Owns one socket. `_latest` is the mailbox; `snapshot()` is the read."""

    def __init__(self, keys, mode="full", token=None, connect=None):
        super().__init__(daemon=True)
        self.keys = list(keys)
        self.mode = mode
        self._token = token
        # Injected so the reconnect logic and the decode loop can be tested
        # without a socket, a token or market hours.
        self._connect = connect or self._real_connect
        self._lock = threading.Lock()
        self._latest = {}
        self._stop = threading.Event()
        self.connected = False
        self.last_frame_at = None
        self.frames = 0
        self.last_error = None
        self.segments = {}
        self.reconnects = 0

    # ---- reading -------------------------------------------------------

    def snapshot(self):
        """A shallow copy of the newest feed per key, taken under the lock so
        a reader never sees a half-written map."""
        with self._lock:
            return dict(self._latest)

    def age(self):
        """Seconds since the last DECODED FRAME, or None if none ever came.

        Not since connection -- see the module docstring. This is the number
        that would have caught the 2026-07-27 frozen tape.
        """
        if self.last_frame_at is None:
            return None
        return time.monotonic() - self.last_frame_at

    def healthy(self):
        age = self.age()
        return bool(self.connected and age is not None and age < STALE_AFTER)

    def status(self):
        """Diagnosis, safe to log or serve: carries no token."""
        age = self.age()
        return {"connected": self.connected, "healthy": self.healthy(),
                "age_s": None if age is None else round(age, 1),
                "frames": self.frames, "instruments": len(self.snapshot()),
                "reconnects": self.reconnects, "segments": dict(self.segments),
                "error": self.last_error}

    def stop(self):
        self._stop.set()

    # ---- the socket ----------------------------------------------------

    def _real_connect(self):
        tok = self._token or read_token()
        return websocket.create_connection(
            WS_URL, timeout=RECV_TIMEOUT,
            sslopt={"cert_reqs": ssl.CERT_REQUIRED},
            header=[f"Authorization: Bearer {tok}", f"User-Agent: {UA}"])

    def run(self):
        attempt = 0
        while not self._stop.is_set():
            ws = None
            try:
                ws = self._connect()
                self.connected = True
                self.last_error = None
                attempt = 0
                ws.send_binary(sub_frame(self.keys, self.mode))
                self._pump(ws)
            except Exception as e:                # noqa: BLE001
                # A dead socket must not kill the thread: the tape would go
                # quiet with no way back short of a restart.
                self.last_error = f"{type(e).__name__}: {e}"
            finally:
                self.connected = False
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:             # noqa: BLE001
                        pass
            if self._stop.is_set():
                break
            self.reconnects += 1
            wait = BACKOFF[min(attempt, len(BACKOFF) - 1)]
            attempt += 1
            self._stop.wait(wait)

    def _pump(self, ws):
        """Read until stopped or the socket dies. Raises so `run` reconnects."""
        while not self._stop.is_set():
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue                         # a quiet market, not a fault
            if not raw:
                raise ConnectionError("socket closed by peer")
            if not isinstance(raw, (bytes, bytearray)):
                continue                         # text frames are not feeds
            self._absorb(raw)

    def _absorb(self, raw):
        """One frame -> the mailbox. A bad frame is counted, never fatal."""
        try:
            resp = upstox_proto.feed_response(raw)
        except Exception as e:                    # noqa: BLE001
            self.last_error = f"decode: {type(e).__name__}: {e}"
            return
        self.frames += 1
        self.last_frame_at = time.monotonic()
        segs = upstox_proto.segment_status(resp)
        if segs:
            self.segments.update(segs)
        feeds = resp.get("feeds") or {}
        if not feeds:
            return
        with self._lock:
            # Merge, never replace: one frame carries only the instruments
            # that ticked, and replacing would blank every quiet strike --
            # downstream that is a chain with holes in it.
            self._latest.update(feeds)
