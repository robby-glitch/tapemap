"""Upstox as a chain source, shaped like the Dhan one it stands in for.

`chain_live._run_live` needs exactly two things from a broker: the expiry per
index at startup, and a normalized snapshot per poll. This provides both with
the same signatures, so the poll loop -- warm start, round robin, persistence,
publishing, error isolation -- is untouched and the Dhan path stays byte for
byte what it was.

    src = UpstoxChainSource()
    expiries = src.start(configs, today)        # once, and again on a new day
    snap = src.poll(cfg, expiries[idx], now, window)   # every cycle

ONE SOCKET, ALL INDICES. Upstox allows two connections per user; opening one
per index would spend that budget for nothing, and a second connection is
worth keeping free for a manual probe while the tool runs. So every index's
keys go on a single feed and `poll` reads its own slice.

WHAT COSTS WHAT. `start()` is expensive and rare: it resolves instruments off
a cached dump, opens the socket, then fetches the 09:15 OI baseline for every
leg (one throttled REST call each). `poll()` is cheap and frequent: it copies
the feed's mailbox and translates it. Nothing in `poll` touches the network
but the once-a-day baseline of a start made before 09:16 (A18), which is the
property that keeps this off the 2026-07-27 failure mode where a per-cycle
fetch froze the tape for a session.

**A STALE SOCKET RAISES.** If the feed is connected but silent past
`upstox_feed.STALE_AFTER`, `poll` raises rather than returning the last good
snapshot forever. The poll loop already isolates and tags a failing index, so
the operator sees a stalled chain instead of a frozen one that looks alive --
which is precisely the distinction that outage turned on.
"""

import time
from datetime import datetime, timedelta

import chain_live
import upstox_adapter
# How long `start` waits for the websocket before returning. Generous because
# the cost of waiting is a slower startup and the cost of NOT waiting was a
# dead index every morning; `poll` still reports an unconnected feed with its
# own reason if the socket needs longer than this.
CONNECT_WAIT_S = 10.0
# A18 (the recorders began at ~09:17 every day): the socket waited for the first 1-min index bar (~09:16) to centre its
# strikes, then for ~200 per-leg REST baselines. From PREOPEN_FROM the prior close centres it, so it is up for 09:15;
# the 09:15 OI baselines need the 09:15 bar, so before BASELINE_FROM they wait for the first poll after it.
PREOPEN_FROM = 9 * 3600 + 14 * 60
BASELINE_FROM = 9 * 3600 + 16 * 60
import upstox_feed
import upstox_instruments
import upstox_rest


def near(meta, spot, each_side):
    """The subscribed legs of the 2 x each_side + 1 strikes nearest the LIVE spot (decode-loop D1): the window handed
    downstream is recentred on every poll, never the opening spot's. Strikes the socket does not carry stay absent --
    past the subscribed edge the window is honestly short on that side, and THE READ says "?" there."""
    ks = set(sorted({k for k, _ in meta.values()}, key=lambda k: (abs(k - spot), k))[:2 * each_side + 1])
    return {key: who for key, who in meta.items() if who[0] in ks}


class UpstoxChainSource:
    def __init__(self, token=None, each_side=upstox_instruments.STRIKES_EACH_SIDE,
                 sub_each_side=upstox_instruments.SUBSCRIBE_EACH_SIDE):
        self.token = token
        self.each_side = each_side              # what every poll hands downstream, around the live spot
        self.sub_each_side = max(sub_each_side, each_side)   # what the socket subscribes once, around the opening spot
        self.feed = None
        self.resolved = {}          # under_sym -> upstox_instruments.resolve()
        self.prev_oi = {}           # under_sym -> {(strike, side): 09:15 OI}

    # ---- startup -------------------------------------------------------

    def start(self, configs, today=None):
        """Resolve, baseline and connect. Returns {under_sym: 'YYYY-MM-DD'}.

        Safe to call again -- a new trading day re-runs it, so the old socket
        is closed first rather than left running with yesterday's strikes.
        """
        tok = self.token or upstox_feed.read_token()
        self.close()
        self.resolved, self.prev_oi, keys = {}, {}, []
        for c in configs:
            idx = c["under_sym"]
            # Looked up in the index's own dump rather than hardcoded, and
            # per index: NIFTY/BANKNIFTY are NSE, SENSEX is BSE.
            idx_key = upstox_instruments.index_key(idx)
            spot = self._spot(idx_key, tok)
            r = upstox_instruments.resolve(spot, name=idx, each_side=self.sub_each_side)
            self.resolved[idx] = r
            keys += r["keys"]

        self.feed = upstox_feed.UpstoxFeed(keys, token=tok)
        self.feed.start()
        # WAIT FOR THE SOCKET rather than handing back a feed still dialling.
        # `UpstoxFeed.start()` only spawns the reader thread, so without this
        # the caller's first poll lands on `connected == False` and raises --
        # and the chain poller is a ROUND-ROBIN, so that cost fell on the same
        # index every single morning (NIFTY, first in the list). Returning
        # early is what made a transient warm-up look like a per-index outage.
        #
        # ponytail: polled, not an Event -- `connected` is a plain bool the
        # reader thread flips, and a condition variable is more surface than
        # this needs. A real failure breaks out immediately instead of burning
        # the whole deadline.
        deadline = time.time() + CONNECT_WAIT_S
        while not self.feed.connected and time.time() < deadline:
            if self.feed.last_error:
                break
            time.sleep(0.1)
        # Deliberately NOT raising on timeout: `poll` already reports an
        # unconnected feed with its own reason, and a socket that connects a
        # second late must not take the session down with it.
        self._deferred = set(self.resolved)          # A18: the socket first, then the baselines
        if chain_live._sec_of_day(datetime.now(chain_live.IST)) >= BASELINE_FROM:
            for idx in self.resolved:
                self._baseline(idx, tok)
        return {idx: r["expiry"] for idx, r in self.resolved.items()}

    _deferred = frozenset()                          # indices whose 09:15 OI baselines wait for the 09:15 bar

    def _baseline(self, idx, tok):
        r = self.resolved[idx]
        self.prev_oi[idx] = upstox_rest.baselines(
            r["meta"], tok,
            on_error=lambda k, e: print(f"upstox baseline {k}: {e}"))
        self._deferred.discard(idx)
        print(f"upstox chain {idx}: expiry {r['expiry']}, "
              f"{len(r['meta'])} legs, "
              f"{len(self.prev_oi[idx])} OI baselines from 09:15")

    def _spot(self, idx_key, tok):
        """The index last price, needed BEFORE the socket to centre strikes.

        Read from candles rather than the feed because the strike window has
        to be decided in order to know what to subscribe to -- the socket
        cannot tell us where to point it.
        """
        candles = upstox_rest.intraday(idx_key, tok)
        closes = upstox_adapter.candles_to_arrays(candles)["close"]
        now = datetime.now(chain_live.IST)
        if not closes and now.weekday() < 5 and chain_live._sec_of_day(now) >= PREOPEN_FROM:
            # A18: no 1-min bar before ~09:16; the prior close centres the +/- SUBSCRIBE_EACH_SIDE window and `near`
            # recentres every poll. ponytail: a gap past ~8 strikes leaves the far side short, as the window says.
            days = upstox_rest.daily_range(idx_key, tok, (now - timedelta(days=10)).strftime("%Y-%m-%d"),
                                           now.strftime("%Y-%m-%d"))
            closes = [days[0][4]] if days else []
        if not closes:
            raise RuntimeError(
                f"{idx_key}: no intraday candles, so no spot to centre the "
                f"strike window on. Before 09:15 this is expected.")
        return closes[-1]

    # ---- per poll ------------------------------------------------------

    def poll(self, cfg, expiry, now, window=chain_live.WINDOW_PTS):
        """The same normalized snapshot the Dhan path produces."""
        idx = cfg["under_sym"]
        r = self.resolved.get(idx)
        if not r or self.feed is None:
            raise RuntimeError(f"{idx}: upstox source polled before start()")
        if not self.feed.connected:
            # `last_error` is None both before the first connect attempt and
            # after a clean close, so printing it raw yields "upstox feed down:
            # None" -- an absence with no reason, which is exactly what rule A2
            # forbids. On 2026-08-06 NIFTY reported that None while BANKNIFTY
            # and SENSEX carried the real WebSocket 401, so the one index the
            # operator happened to be watching was the one hiding the cause.
            why = self.feed.last_error or (
                "no error recorded -- the socket has not finished a connect "
                "attempt yet. If this does not clear, check the token first: "
                "python upstox_auth.py")
            raise RuntimeError(f"upstox feed down: {why}")
        age = self.feed.age()
        if age is None:
            raise RuntimeError("upstox feed connected but has sent nothing yet")
        if age > upstox_feed.STALE_AFTER:
            raise RuntimeError(
                f"upstox feed stale: {age:.0f}s since the last frame "
                f"(connected, but not receiving)")

        feeds = self.feed.snapshot()
        spot = upstox_adapter.ltp_of(feeds.get(r["idx_key"]))
        if not spot:
            raise RuntimeError(f"{idx}: no index tick yet, so no spot")
        if idx in self._deferred:
            if chain_live._sec_of_day(now) < BASELINE_FROM:
                raise RuntimeError(f"{idx}: the 09:15 OI baselines wait for the 09:15 bar (from 09:16); "
                                   "the socket is already recording")
            self._baseline(idx, self.token or upstox_feed.read_token())
        payload = upstox_adapter.chain_payload(
            feeds, near(r["meta"], spot, getattr(self, "each_side", upstox_instruments.STRIKES_EACH_SIDE)),
            spot, self.prev_oi.get(idx))
        return chain_live.normalize(payload, now, window)

    # ---- housekeeping --------------------------------------------------

    def status(self):
        return {} if self.feed is None else self.feed.status()

    def close(self):
        if self.feed is not None:
            self.feed.stop()
            self.feed = None
