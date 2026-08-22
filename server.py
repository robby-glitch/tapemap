"""Local server for the tape-engine UI.

  python server.py [port] [data_dir] [strike] [--mock-chain]
  python server.py live [port] [--mock-chain]

Serves ui/ as static files, the analysis JSON at /api/data, and the live
option-chain analyser payload at /api/chain (chain_live.ChainPoller).

Multi-index: /api/data and /api/chain accept ?idx=NIFTY|BANKNIFTY|SENSEX
(default NIFTY). In live mode the server resolves + builds a payload per
enabled index and runs a single round-robin ChainPoller feeding one box per
index. --mock-chain replays the synthetic fixture into every index so the DATA
tab works with an expired token and outside market hours.
"""

import json
import logging
import sys
import threading
import time
from dataclasses import asdict
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import chainside as chain_mod
import desk as desk_mod
import desk_log
import direction as direction_mod
import drag as drag_mod
import fuse as fuse_mod
import instruments
import pools as pools_mod
import senses as senses_mod
import surface as surface_mod
import trigger_log
import upstox_adapter
from analyze import analyze

ROOT = Path(__file__).parent
log = logging.getLogger("tapemap")

# Process start, stamped at import. /api/health reports it so a caller can tell
# "the server I just started" from "a server that has been up since yesterday
# afternoon" -- which is exactly what held port 8765 on 2026-08-06.
_STARTED = time.time()

# The book detectors' output, newest last. A ring, not a list: this runs for a
# whole session and /api/senses only ever renders the tail. The forward RECORD
# is the file `senses_mod.Senses` appends to -- this is a window onto it, and
# losing the oldest entries here costs nothing.
_SENSES = {"rows": None, "obj": None, "err": None, "polls": 0, "started": None,
           "fuse": None, "pools": {}, "chain": {},
           # Kite order counts, POSTed by PaperDesk's bridge. token -> book.
           # The ONE field Upstox does not send, and the only thing that tells
           # a defended wall from a crowd on a round number.
           "orders": {}, "orders_at": None, "orders_n": 0,
           # THE BUYER'S TAX, one Board per index, session-anchored.
           # `drag.py` was written earlier, tested, and never called by
           # anything -- both handoffs say so. This is its first caller. It
           # answers the question the whole seller pivot rests on: even with
           # the direction exactly right, what fraction of the move did a
           # buyer actually collect?
           "drag": {}}

# ONE lock over _SENSES and every object it points at.
#
# The daemon loop ADDS a Fuse, a detector set and a pools entry the moment spot
# drifts to a fresh near-ATM strike, while the HTTP handler is iterating those
# same dicts to answer /api/senses. Unlocked, that collision raises
# "dictionary changed size during iteration" in the handler, which returns 500,
# which the console's .catch paints as CONSOLE CANNOT REACH THE SERVER -- in the
# red reserved solely for a DEAD FEED. A healthy feed must never wear a dead
# one's face. Spot crossing a strike is not a rare event; it is most of a
# trending morning.
#
# Lock ORDER is _SENSES_LOCK then feed._lock (taken inside snapshot()). Nothing
# anywhere takes them the other way round, so there is no cycle to deadlock on.
# Reentrant because the read side calls back into objects this module owns.
_SENSES_LOCK = threading.RLock()

# Most books a single POST may set. The bridge sends the newest book per
# subscribed token; Kite's own cap is far below this.
_MAX_BOOKS = 512


def _clean_books(books):
    """Keep only what `pools.orders_for` can actually walk. Never trust shape.

    THE POST IS UNAUTHENTICATED and its body is attacker-shaped: any script on
    the kite.zerodha.com origin passes CORS, and CORS advises browsers anyway.
    `orders_for` does `(book or {}).get("depth")`, so a single value that is not
    a dict -- POST {"books": {"1": 5}} -- raises AttributeError inside the senses
    loop every 0.5s, which the loop catches, logs and sleeps on. The book layer
    then stays dark until a valid bridge POST happens to overwrite the poisoned
    dict. One crafted request would deny the whole layer, so the shape is
    checked HERE, once, rather than trusted 45,000 times.

    Anything unrecognised is dropped silently: this is a best-effort side
    channel, and a partly-readable POST is worth more than a refused one.
    """
    if not isinstance(books, dict):
        return {}
    out = {}
    for tok, book in list(books.items())[:_MAX_BOOKS]:
        if not isinstance(book, dict):
            continue
        depth = book.get("depth")
        if not isinstance(depth, dict):
            continue
        side_out = {}
        for side in ("bid", "ask"):
            levels = depth.get(side)
            if not isinstance(levels, list):
                continue
            # 10 a side is the whole Kite packet; more is not a deeper book.
            # `price` must be a FINITE number: orders_for does arithmetic on it
            # (`abs(price - b0)`), so a string raises TypeError and a NaN
            # compares false against everything, which would read as "no book
            # matched" -- a wrong answer wearing the right one's clothes.
            clean = []
            for l in levels[:10]:
                if not isinstance(l, dict):
                    continue
                px = l.get("price")
                if not isinstance(px, (int, float)) or isinstance(px, bool):
                    continue
                if px != px or px in (float("inf"), float("-inf")):
                    continue
                clean.append(l)
            side_out[side] = clean
        if side_out.get("bid") and side_out.get("ask"):
            out[str(tok)] = {"depth": side_out}
    return out


# 5d -- LATENCY INSTRUMENTATION. Two ring buffers (last 500 samples each), one
# per `perf_counter` seam: a senses-loop PASS, and an HTTP handler's SERVICE
# TIME. `deque(maxlen=500)` drops the oldest sample on overflow by itself, so
# this never grows -- no log spam, no unbounded memory, just what /api/health
# needs to publish p50/p99.
from collections import deque as _deque

_LAT_LOCK = threading.Lock()
_LAT = {"senses_ms": _deque(maxlen=500), "http_ms": _deque(maxlen=500)}

# Below this many samples a percentile is noise, not a measurement -- constraint
# 9 says /api/health must publish ABSENT with a reason rather than a number
# computed off too little, and never a fabricated zero.
MIN_LAT_SAMPLES = 5


def _record_latency(bucket, ms):
    with _LAT_LOCK:
        _LAT[bucket].append(ms)


def _percentile(xs, p):
    s = sorted(xs)
    k = max(0, min(len(s) - 1, int(round(p / 100.0 * (len(s) - 1)))))
    return round(s[k], 2)


def _latency_summary():
    """{senses_ms: {...}, http_ms: {...}}, each either p50/p99/n or a reason."""
    with _LAT_LOCK:
        snaps = {k: list(v) for k, v in _LAT.items()}
    out = {}
    for k, xs in snaps.items():
        if len(xs) < MIN_LAT_SAMPLES:
            out[k] = {"p50": None, "p99": None, "n": len(xs),
                      "why": f"only {len(xs)} sample(s); need {MIN_LAT_SAMPLES}"}
        else:
            out[k] = {"p50": _percentile(xs, 50), "p99": _percentile(xs, 99),
                      "n": len(xs)}
    return out


# Strikes either side of spot the book detectors watch. The first live run
# watched every subscribed leg -- 101 instruments -- and the loudest were deep
# OTM SENSEX strikes 700+ points from spot, where the book is thin, the tick is
# wide and every flicker reads as a five-level sweep. That is noise with a
# timestamp. The cascade this stack is built to catch happens in the FUTURE and
# in the strikes near the money, so that is what is watched.
SENSES_EACH_SIDE = 3


def _chain_doc(poller, idx):
    """The poller's own published chain payload for one index, or None.

    One parse shared by the surface and the regime, so the two can never be
    fitted against different snapshots -- a skew read off one frame and a flip
    read off another would disagree for reasons no reader could see.
    """
    box = (getattr(poller, "boxes", None) or {}).get(idx) or {}
    try:
        return json.loads(box.get("payload") or "null")
    except (TypeError, ValueError):
        return None


def _surface_read(poller, idx):
    """Fit the live chain for one index. Returns a SurfaceRead, always.

    THE FORWARD, NOT SPOT. Options are priced off the FUTURE, and the basis
    between it and spot tilts every log-moneyness -- which the fitted skew
    would then report as a market view. The future's last price is used when
    the feed has it; spot is the declared fallback and `f_src` says so, so a
    reader can tell a measured surface from an approximated one.
    """
    doc = _chain_doc(poller, idx)
    if not doc or not doc.get("ok"):
        r = surface_mod.SurfaceRead(index=idx, expiry="")
        r.why.append("no chain payload yet -- outside market hours this is "
                     "simply a closed market, not a fault")
        return r

    expiry = doc.get("expiry") or ""
    spot = doc.get("spot")
    f, f_src = spot, "spot"
    src = getattr(poller, "src", None)
    feed = getattr(src, "feed", None)
    res = (getattr(src, "resolved", None) or {}).get(idx) or {}
    key = res.get("fut_key")
    if feed is not None and key:
        try:
            px = upstox_adapter.ltp_of((feed.snapshot() or {}).get(key))
            if px:
                f, f_src = px, "future"
        except Exception:               # a missing future is not a failure
            pass
    return surface_mod.read(idx, expiry, doc.get("strikes"), f,
                            surface_mod.years_to_expiry(expiry), f_src=f_src)


def _regime_engine_read(payloads, idx):
    """sigma_pctl, vwap_flips_per_hr for one index -- from the engine's OWN
    published session, not invented here. Returns (sigma_pctl,
    vwap_flips_per_hr, why); why is None on success, else a reason and both
    values are None.

    `fuse.verdict()`'s two chain-blind inputs sat dead since the gate was
    wired: nothing ever passed `sigma_pctl` or `vwap_flips_per_hr`, so
    `regime.decide` could only ever answer CASCADE or UNKNOWN. Both are
    already computed by the tape engine, per 1-minute bar:

      sigma_pctl -- `engine.Book.bw` (engine.py:118,130-131) ranks VWAP band
      WIDTH percentile-so-far against this session's own distribution. The
      latest bar's `bw_r` IS "how tight is sigma against this session" --
      exactly what `regime.decide`'s TRANSITION check reads.

      vwap_flips_per_hr -- not published directly, but `f["z"]`
      (engine.py:129, close position relative to the VWAP band) is, per bar.
      Counting z's sign changes across consecutive published bars and rating
      it per hour is the same VWAP-interaction reading `regime.py`'s PIN
      check wants, built from a quantity the engine already carries rather
      than a new one invented here.

    GATED ON THE ENGINE'S OWN MATURITY, not a threshold picked here:
    engine.py:918 (`if i >= MATURITY`) is where the tape's own state machine
    starts trusting `bw_r`; fewer bars than that and both values are None
    with a reason, per constraint 3 -- never a number from noise.
    """
    from engine import MATURITY
    box = (payloads or {}).get(idx)
    sess = box.get("session") if isinstance(box, dict) else None
    bars = ((sess or {}).get("day") or {}).get("bars") if sess else None
    if not bars:
        return None, None, f"no live engine session yet for {idx}"
    fut = [b["fut"] for b in bars if b.get("fut")]
    if len(fut) < MATURITY:
        return None, None, (f"only {len(fut)} bar(s) this session; the "
                            f"engine's own bands need {MATURITY} before "
                            "they carry statistical weight (engine.MATURITY)")
    sigma_pctl = fut[-1].get("bw_r")
    window = fut[-60:]                 # "last hour" -- engine.py:919's own look
    flips = sum(1 for a, b in zip(window, window[1:])
               if (a.get("z") or 0) * (b.get("z") or 0) < 0)
    span_hr = (len(window) - 1) / 60.0
    vwap_flips_per_hr = round(flips / span_hr, 1) if span_hr > 0 else None
    return sigma_pctl, vwap_flips_per_hr, None


def _walls_holding(pools_summary):
    """walls_holding for `regime.decide`, from `pools.summary()`'s own
    fields -- the third dead gear. Returns (walls_holding, why).

    A shelf becomes a WALL only when the order count says a few hands hold
    it (`pools.WALL_ORDERS`, pools.py:75,103-117); without Kite's order-count
    bridge `orders_known` is False and `walls` is always 0 by construction --
    reporting that as "no walls holding" would be exactly the invented zero
    constraint 3 forbids. None with pools.py's own reason in that case;
    otherwise walls_holding is simply whether this instrument's book has any
    shelf classified as a wall right now.
    """
    if not pools_summary:
        return None, "no book terrain mapped yet for this instrument"
    if not pools_summary.get("orders_known"):
        return None, ("order counts absent from this feed; wall vs cluster "
                      "unknowable (pools.py)")
    return pools_summary.get("walls", 0) > 0, None


def _log_chain_pace(poller, payloads, idx, doc, desk_state):
    """5a/5b: fit the surface and compute the desk view ONCE per new chain
    payload for `idx`, and forward-log a surface line plus any transition.

    WHY HERE, AND WHY THIS COSTS NOTHING EXTRA. This runs from inside the
    per-idx "new payload" block `_senses_loop` already has -- the same place
    that already re-parses the chain once per ~10s refresh, never per poll.
    `desk.decide` is real work (fits a whole candidate catalog); gating it on
    the same trigger, rather than the 0.5s loop tick, is what keeps it off
    the loop's own budget -- it already only runs at chain pace, which IS
    the requirement, not a separate throttle bolted on.

    NEVER NEEDS THE BOOK FEED. `_surface_read` falls back to spot when the
    future is unavailable, `desk_mod.regime_from_chain` reads the chain
    payload directly, and `_view_for` returns None gracefully when the book
    (fuse) or chain half is not ready -- exactly the same tolerance
    `/api/desk` already relies on. That is what lets this run under
    --mock-chain, where `poller.src` never exists at all.

    `desk_state` is the caller's idx -> {gear, conviction, deployable} cache;
    mutated in place so the next tick has something to diff against.
    """
    surf = _surface_read(poller, idx)
    if surf.fit.ok:
        skew_x = surface_mod.SKEW_X
        b = -(surf.fit.skew / (2.0 * skew_x)) if surf.fit.skew is not None else None
        desk_log.log_surface(idx, surf.fit.atm_iv, b, surf.fit.convexity,
                             surf.fit.rmse, surf.f_src, surf.expiry,
                             surf.fit.n)

    reg = desk_mod.regime_from_chain(doc)
    view = _view_for(idx, payloads)
    decision = desk_mod.decide(surf, reg, desk_mod.DEFAULT_CAPITAL,
                               strikes=doc.get("strikes"), view=view)

    new_state = {"gear": getattr(view, "gear", None),
                "conviction": getattr(view, "conviction", None),
                "deployable": decision.best}
    prev_state = desk_state.get(idx, {})
    for field, frm, to in desk_log.diff_transitions(prev_state, new_state):
        desk_log.log_transition(idx, field, frm, to,
                                detail=f"{idx} {field}: {frm} -> {to}")
    desk_state[idx] = new_state


def _senses_loop(poller, payloads, period=0.5):
    """Drive the book detectors off the chain poller's ALREADY-OPEN socket,
    and forward-log the surface fit + desk verdict transitions (5a/5b) at the
    same chain-payload cadence.

    WHY A SEPARATE THREAD. The refresh loop runs at bar cadence, which is the
    right rate for the tape and far too slow for a book: a sweep lives for one
    frame. This reads the feed's mailbox directly at `period`, which costs no
    network -- `snapshot()` is a dict copy -- and no second Upstox connection,
    which matters because there are only two and one is a manual probe.

    THE FEED GATE ONLY GUARDS THE BOOK HALF, NOT THE CHAIN HALF. Until
    2026-08-22 a missing/disconnected feed skipped the WHOLE tick, including
    the "new chain payload" block that feeds `chains.on_snapshot`, the drag
    board and (now) the surface/desk forward log -- none of which need the
    book feed at all. That made the chain half stall on a dead book socket
    for no reason, and made --mock-chain (which never opens a feed) unable to
    exercise 5a/5b even though nothing it does depends on one. The feed check
    now only gates the near-ATM book-detector pass below it.

    EVERYTHING HERE IS FAIL-SOFT AND NOTHING HERE CAN STOP THE TAPE. The
    poller may not have a source yet, may be restarting for a new day, or may
    have a dead socket; all of those are "no rows this tick", never an
    exception that ends the thread. The last error is published on
    /api/senses so a silent stall cannot masquerade as a quiet market -- the
    2026-07-27 lesson, applied to this loop too.
    """
    from collections import deque
    _SENSES["rows"] = deque(maxlen=2000)
    _SENSES["started"] = time.time()
    obj = _SENSES["obj"] = senses_mod.Senses()
    book = _SENSES["fuse"] = fuse_mod.Book()
    chains = chain_mod.Chains()
    seen_payload = {}          # idx -> id() of the last payload already read
    desk_state = {}            # idx -> {gear, conviction, deployable}, 5b's diff base
    while True:
        t0 = time.perf_counter()
        try:
            src = getattr(poller, "src", None)
            feed = getattr(src, "feed", None)
            feed_ok = feed is not None and feed.connected
            snap = feed.snapshot() if feed_ok else {}
            stamp = time.strftime("%H:%M:%S")
            boxes = getattr(poller, "boxes", None) or {}
            with _SENSES_LOCK:
                # FUEL AND DRAIN, from the chain -- the half the book cannot see,
                # and needs no feed either. Parsed only when the poller has
                # actually published something new: the chain refreshes about
                # every ten seconds per index and this loop runs twice a second,
                # so re-parsing every pass would be twenty wasted json.loads for
                # one new snapshot.
                for idx, box in boxes.items():
                    pl = (box or {}).get("payload")
                    if not pl or seen_payload.get(idx) == id(pl):
                        continue
                    seen_payload[idx] = id(pl)
                    try:
                        doc = json.loads(pl)
                    except (TypeError, ValueError):
                        continue
                    if doc.get("ok"):
                        stamp = time.strftime("%H:%M:%S")
                        rd = chains.on_snapshot(idx, stamp,
                                                doc.get("strikes"))
                        _SENSES["chain"][idx] = rd.__dict__
                        # Same snapshot, same lock, one more reading. The
                        # Board anchors itself on its first call and only
                        # watches after that, so there is nothing to
                        # initialise and nothing to reset at the open.
                        board = _SENSES["drag"].get(idx)
                        if board is None:
                            board = _SENSES["drag"][idx] = drag_mod.Board()
                        board.on_snapshot(doc.get("spot"),
                                          doc.get("strikes"), stamp)
                        # 5a/5b -- own try/except so a bad fit or a desk
                        # exception on ONE index cannot cost the others their
                        # chain/drag processing this same tick.
                        try:
                            _log_chain_pace(poller, payloads, idx, doc,
                                            desk_state)
                        except Exception:
                            log.exception("desk_log at chain pace (%s)", idx)

                if feed_ok:
                    for idx, r in (getattr(src, "resolved", None) or {}).items():
                        # Near-ATM legs only, chosen against the poller's own spot. If
                        # spot is not known yet the FUTURE is watched alone rather than
                        # everything -- "which strikes are near" is unanswerable
                        # without it, and guessing would reinstate the noise.
                        spot = (boxes.get(idx) or {}).get("spot")
                        meta = list((r.get("meta") or {}).items())
                        if spot:
                            near = sorted({k_[0] for _, k_ in meta},
                                          key=lambda x: abs(x - spot))[:SENSES_EACH_SIDE * 2 + 1]
                            meta = [(k, v) for k, v in meta if v[0] in set(near)]
                        else:
                            meta = []
                        # The FUTURE first: it is the instrument the zone rule is
                        # measured on, and its book is the one a cascade runs through.
                        # Option legs follow, named by strike so a row says which.
                        for name, key in ([(f"{idx}-FUT", r.get("fut_key"))]
                                          + [(f"{idx}-{s}{sd.upper()}", k)
                                             for k, (s, sd) in meta]):
                            if not key:
                                continue
                            frame = snap.get(key)
                            rows = obj.observe(name, stamp, frame, key)
                            if rows:
                                _SENSES["rows"].extend(rows)
                                book.on_rows(rows)
                            # Terrain for the FUTURE only. Mapping every leg would
                            # triple the work to describe books nobody trades through,
                            # and the cascade this stack watches for runs through the
                            # future's ladder.
                            if name.endswith("-FUT"):
                                lad, _v = senses_mod.ladder_of(frame)
                                if lad:
                                    # Kite's order counts, if PaperDesk's bridge is
                                    # running. Matched on the touch rather than by
                                    # symbol table -- both feeds watch the same
                                    # exchange, so the same instrument has the same two
                                    # prices. Absent -> wall-vs-cluster stays open.
                                    oc = pools_mod.orders_for(lad, _SENSES["orders"])
                                    _SENSES["pools"][name] = pools_mod.summary(lad, oc)
                    _SENSES["polls"] += 1
                    _SENSES["err"] = None
                else:
                    _SENSES["err"] = "feed not connected"
        except Exception as e:            # never take the tape down
            _SENSES["err"] = f"{type(e).__name__}: {e}"
            log.exception("senses loop")
        finally:
            _record_latency("senses_ms", (time.perf_counter() - t0) * 1000.0)
        time.sleep(period)


def _setup_logging():
    """Console AND tapemap.log — the 2026-07-27 freeze left its only evidence
    in a closed console window; the log file survives.

    ROTATING, not a plain FileHandler: this server runs for a whole session
    (or many, across days, if never stopped) and an unbounded log is a slow
    leak that only shows up as "disk is full" months later. 5 MB x 3 backups
    keeps a session or two of history without growing forever.
    """
    from logging.handlers import RotatingFileHandler
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[RotatingFileHandler(ROOT / "tapemap.log", maxBytes=5 * 1024 * 1024,
                                      backupCount=3, encoding="utf-8"),
                  logging.StreamHandler()])


class _Server(ThreadingHTTPServer):
    """One TapeMap per port, enforced at the socket.

    Python's HTTPServer sets `allow_reuse_address = 1`. On Linux that only
    shortens TIME_WAIT, but on WINDOWS SO_REUSEADDR lets a second process bind
    a port another process is already listening on and take it over. That is
    how two servers came up 2s apart on 2026-08-06: the second stole 8765, and
    the first stayed alive holding an Upstox websocket slot while serving
    nothing -- invisible to stop.bat, which kills by port. One token only gets
    so many sockets, so the survivor's chain poller took 401 after 401.
    """

    allow_reuse_address = False


def payload_at(box, interval):
    """One index's box -> the /api/data bytes at `interval`.

    THE EXPENSIVE HALF HAPPENS ONCE. A refresh cycle costs a token, three
    intraday downloads and an engine run (`live.build_session`); rebuilding all
    of that per interval would triple the network load of a tape the operator
    switches between 1m and 3m on a whim, and would put three different
    `built_at` stamps on what is one observation of one session. So the poller
    stores the SESSION and this derives a payload from it per interval, on
    first ask, cached until the next build.

    The cache is keyed by interval and each entry carries the build stamp it
    came from, so a payload derived a moment before a refresh landed can never
    be served as if it belonged to the new build. Two threads can derive the
    same interval at once -- that wastes a little CPU and cannot produce a
    wrong answer, which is the right way round.

    A box with no session (starting up, or a build that failed) serves its own
    error bytes verbatim: an interval cannot make a tape exist.
    """
    if not isinstance(box, dict):
        return box                       # legacy/replay mode: raw bytes
    base = box.get("session")
    if base is None:
        return box.get("payload")
    stamp = box.get("stamp")
    cache = box.setdefault("by_interval", {})
    hit = cache.get(interval)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    from live import derive_payload
    out = derive_payload(base, interval)
    cache[interval] = (stamp, out)
    return out


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, payloads=None, chains=None, poller=None, late=None,
                 **kw):
        self.payloads = payloads or {}     # idx -> {"payload": bytes} (or bytes)
        # Resolved per REQUEST rather than when the factory was built: the
        # socket is now bound BEFORE the chain poller exists, so the poller is
        # handed over through `late` once it does. See main() for why the bind
        # has to come first.
        self.chains = late["chains"] if late is not None else chains
        self.poller = late["poller"] if late is not None else poller
        super().__init__(*a, directory=str(ROOT / "ui"), **kw)

    def _idx(self):
        """?idx= clamped to an enabled index; unknown/absent -> DEFAULT."""
        q = parse_qs(urlsplit(self.path).query)
        idx = (q.get("idx") or [instruments.DEFAULT])[0]
        return idx if idx in instruments.ENABLED else instruments.DEFAULT

    # PaperDesk's bridge posts from a CONTENT SCRIPT, so the request carries
    # kite.zerodha.com as its origin and CORS applies -- the extension's
    # host_permissions do not exempt it, which is the trap: the manifest looks
    # correct and every POST still fails. Measured 2026-08-20, a wall of
    # "blocked by CORS policy" in the Kite console.
    #
    # Exactly one origin is allowed. A wildcard would let ANY page the browser
    # visits POST into this server, and this one accepts market data that
    # feeds a reading -- an open door for a page to hand it fabricated depth.
    # Localhost-only binding is not protection from that; the browser is the
    # one making the request.
    ALLOW_ORIGIN = "https://kite.zerodha.com"

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin == self.ALLOW_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def do_OPTIONS(self):
        """Preflight. A JSON content-type makes the browser ask first."""
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _json(self, body, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # PaperDesk's paper fills, tagged with the tape context they were
        # taken in. A SEPARATE file from trigger_log.jsonl on purpose:
        # trigger_log counts rule populations under a quarantine discipline,
        # and operator-taken fills mixed into it would corrupt every count the
        # server publishes. The two join on (index, day, t) when §5e asks
        # "of the zone arms, which did I actually take". Fire-and-forget on
        # the extension side — a failure here must never block a fill.
        if self.path.startswith("/api/orderbook"):
            # PaperDesk's Kite tap, shipping per-level ORDER COUNTS. Read-only
            # and additive: nothing in the tape or the chain depends on it, so
            # a bridge that is not running costs exactly the wall-vs-cluster
            # answer and nothing else.
            try:
                # A CAP, like every other POST here (/api/paper_fill 16K,
                # /api/token 8K). Without one, `rfile.read(n)` on a declared
                # Content-Length of 5,000,000,000 blocks this handler thread
                # forever -- there is no socket timeout -- and repeated
                # connections pile up hung threads on ThreadingHTTPServer.
                # CORS does not help: it only advises BROWSERS, and the server
                # processes the request either way. 10 depth levels across a
                # few hundred tokens is tens of KB; 512K is generous.
                try:
                    n = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    n = 0
                if not 0 < n < 524288:
                    self._json(b'{"ok":false,"msg":"bad request"}', 400)
                    return
                doc = json.loads(self.rfile.read(n) or b"{}")
                books = _clean_books(doc.get("books"))
                with _SENSES_LOCK:
                    _SENSES["orders"] = books
                    _SENSES["orders_at"] = time.time()
                    _SENSES["orders_n"] = len(books)
                self._json(json.dumps({"ok": True, "books": len(books)}).encode())
            except Exception as e:      # never 500 at a browser extension
                self._json(json.dumps({"ok": False,
                                       "error": str(e)}).encode(), 200)
            return

        if self.path.startswith("/api/paper_fill"):
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if not 0 < n < 16384:
                self._json(b'{"ok":false,"msg":"bad request"}', 400)
                return
            try:
                row = json.loads(self.rfile.read(n))
                if not isinstance(row, dict):
                    raise ValueError("not an object")
            except ValueError:
                self._json(b'{"ok":false,"msg":"malformed request body"}', 400)
                return
            row["received_at"] = time.time()
            dst = ROOT / "data" / "paper_fills.jsonl"
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(dst, "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            self._json(b'{"ok":true}')
            return
        # One-click token capture: validate a pasted/clipboard Dhan token, save
        # it to .dhan_token, and kick the poller. The token is never logged or
        # echoed — only the validity message from token_status goes back.
        if not self.path.startswith("/api/token"):
            self.send_error(404)
            return
        from chain_live import _broker, token_status
        # On Upstox this button cannot do what it says. The running tape and
        # chain both read `.upstox_token`; an Upstox token is an opaque OAuth
        # string, not a Dhan JWT, so token_status would reject it as malformed
        # even if the operator pasted the right one. Writing `.dhan_token` and
        # reporting success would be the third sentence in HANDOFF §9 -- "we
        # are not showing you" dressed up as "accepted". Refuse, and name the
        # thing that actually refreshes it.
        if _broker() == "upstox":
            self._json(json.dumps({
                "ok": False,
                "msg": ("running on Upstox — this button only writes the Dhan "
                        "token, which nothing on this path reads. Re-auth "
                        "with: python upstox_auth.py"),
            }).encode())
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if not 0 < n < 8192:
            self._json(b'{"ok":false,"msg":"bad request"}', 400)
            return
        try:
            tok = json.loads(self.rfile.read(n)).get("token", "").strip()
        except (ValueError, AttributeError):
            self._json(b'{"ok":false,"msg":"malformed request body"}', 400)
            return
        st = token_status(tok)
        if not st["ok"]:
            self._json(json.dumps({"ok": False, "msg": st["msg"]}).encode())
            return
        (ROOT / ".dhan_token").write_text(tok, encoding="utf-8")
        if self.poller is not None:
            self.poller.reload = True          # hot-reload the chain poller
        self._json(json.dumps({"ok": True, "msg": st["msg"]}).encode())

    def do_GET(self):
        # Answers whatever the tape is doing, and before any other route, so
        # "is a TapeMap server there, and on which broker" is always askable.
        # Every other route conflates two different failures: /api/data returns
        # a live_error body BOTH when the broker is dead and when the market
        # simply has not opened, which is how a screen at 02:50 came to read
        # "the backend is unreachable" while the backend was up and correct.
        # Two callers need the distinction:
        #   * start-v2.bat, to refuse to reuse a server on the wrong broker --
        #     a Dhan server left running from the previous afternoon held 8765
        #     on 2026-08-06 and the launcher reused it.
        #   * the UI's NOT LIVE banner, which named an expired Dhan token as
        #     the usual cause while the tool was running on Upstox.
        if urlsplit(self.path).path == "/":
            # The site root IS the desk now -- start-v2.bat opens it directly
            # and a bookmark to "/" should land there too. /index.html (the
            # legacy landing page) stays reachable by its own name; only the
            # bare root redirects.
            self.send_response(302)
            self.send_header("Location", "/desk.html")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path.startswith("/api/health"):
            from chain_live import _broker
            # UpstoxFeed.status() / UpstoxChainSource.status() (upstox_feed.py:
            # 116-123) existed with zero callers -- a dead socket had nowhere
            # to say so except the senses loop's own /api/senses error, which
            # only runs live. `feed` is None with a reason on the Dhan/mock
            # path or before the chain source has connected, per constraint 3
            # -- never a fabricated "healthy".
            feed, feed_why = None, None
            src = getattr(self.poller, "src", None) if self.poller else None
            status_fn = getattr(src, "status", None)
            if callable(status_fn):
                feed = status_fn() or None
                if feed is None:
                    feed_why = "chain source has no feed yet (starting up)"
            else:
                feed_why = ("no Upstox chain source in this server mode -- "
                            "Dhan broker, --mock-chain, or replay mode")
            self._json(json.dumps({
                "ok": True,
                "broker": _broker(),
                "started_at": _STARTED,
                "indices": sorted(self.payloads),
                "feed": feed,
                "feed_why": feed_why,
                # 5d -- p50/p99 off the last <=500 samples of each seam.
                # Absent (with a reason) rather than zero until there are
                # enough samples to mean anything -- constraint 9.
                "latency": _latency_summary(),
            }).encode())
            return
        if self.path.startswith("/api/data"):
            idx = self._idx()
            box = self.payloads.get(idx)
            if box is None:
                # Never serve one index's tape under another's name. Replay
                # mode only builds DEFAULT, and the old fallback chain quietly
                # answered /api/data?idx=BANKNIFTY with NIFTY's session — three
                # identical panels that looked live and were mislabelled.
                self._json(json.dumps({
                    "index": idx, "strike": None, "days": [],
                    "built_at": time.time(),
                    "live_error": f"no {idx} tape in this server mode — "
                                  f"start with: python server.py live"}).encode())
                return
            from live import clamp_interval
            q = parse_qs(urlsplit(self.path).query)
            interval = clamp_interval((q.get("interval") or [None])[0])
            pl = payload_at(box, interval)
            self._json(pl if pl is not None else b"{}")
        elif self.path.startswith("/api/chain"):
            idx = self._idx()
            if not self.chains:
                self.send_error(404)     # no poller: UI falls back to legacy
                return
            box = self.chains.get(idx) or self.chains.get(instruments.DEFAULT)
            if not box or box["payload"] is None:
                self._json(b'{"ok":false,"error":"chain poller warming up"}')
            else:
                self._json(box["payload"])
        elif self.path.startswith("/api/oiflow"):
            # Trending-OI table. Aggregated server-side on purpose: the minute
            # grid it reads is a few hundred KB while the raw chain is ~180 MB
            # a day, so the browser must never see the latter.
            idx = self._idx()
            if not self.poller:
                self._json(b'{"ok":false,"error":"no chain poller"}')
                return
            st = self.poller.states.get(idx)
            if st is None:
                self._json(json.dumps({"ok": False,
                                       "error": f"no chain state for {idx}"}).encode())
                return
            q = parse_qs(urlsplit(self.path).query)
            try:
                interval = max(1, min(60, int((q.get("interval") or ["15"])[0])))
            except ValueError:
                interval = 15
            raw = (q.get("strikes") or [""])[0]
            strikes = None
            if raw:
                try:
                    strikes = [float(x) for x in raw.split(",") if x.strip()]
                except ValueError:
                    strikes = None
            rows = st.oi_flow(interval=interval, strikes=strikes)
            avail = sorted({k for m in st.minutes.values() for k in m["k"]})
            # The CHAIN's own health travels with the rows. Without it an empty
            # `rows` says only "nothing here", and a reader cannot tell "the
            # boundary has not arrived yet" from "the feed is down, so no mark
            # is coming" -- which are A1's first and second sentences and must
            # never render as one. On 2026-08-12 NIFTY's socket was dead from
            # the open while this endpoint answered ok:true with an empty list,
            # so the tab told the operator to wait for a 09:20 row that was
            # never going to exist. `ok` still describes THIS endpoint; the
            # chain's state is reported under its own name.
            chain_ok, chain_why = True, None
            cbox = self.chains.get(idx) if self.chains else None
            if cbox is None or cbox.get("payload") is None:
                chain_ok, chain_why = False, "chain poller warming up"
            else:
                try:
                    cp = json.loads(cbox["payload"])
                    if not cp.get("ok", True):
                        chain_ok = False
                        chain_why = cp.get("error") or "the chain is unavailable"
                except (ValueError, TypeError):
                    pass          # unparseable box: say nothing rather than guess
            self._json(json.dumps({"ok": True, "index": idx,
                                   "interval": interval, "strikes": avail,
                                   "selected": strikes, "rows": rows,
                                   "chain_ok": chain_ok,
                                   "chain_why": chain_why}).encode())
        elif self.path.startswith("/api/contract"):
            # Option-premium tape: 1-min bars + their own session VWAP bands,
            # per leg. The heavy lifting is live.build_contract (fetch + the
            # pure contract_bars/contract_pair layers); this handler only
            # parses params and keeps one index's failure off the others.
            idx = self._idx()
            q = parse_qs(urlsplit(self.path).query)

            def _int(name, dflt, lo, hi):
                try:
                    return max(lo, min(hi, int((q.get(name) or [str(dflt)])[0])))
                except ValueError:
                    return dflt

            interval = _int("interval", 3, 1, 60)
            days = _int("days", 1, 1, 10)
            side = ((q.get("side") or ["both"])[0] or "both").upper()
            if side not in ("CE", "PE", "BOTH"):
                side = "BOTH"
            raw = (q.get("strike") or [""])[0].strip()
            strike = None
            if raw:
                try:
                    strike = float(raw)
                except ValueError:
                    strike = None      # unparseable -> let the pair picker choose
            # Reuse the chain snapshot the poller already paid for rather than
            # spending another request against Dhan's 1-per-3s chain limit.
            # `atm` rides along with it so contract_pair.pick_pair ranks
            # candidates against the real ATM instead of its own proxy.
            rows, atm = None, None
            box = (self.chains or {}).get(idx)
            if box and box.get("payload"):
                try:
                    pl = json.loads(box["payload"])
                    if pl.get("ok"):
                        rows = pl.get("strikes")
                        atm = pl.get("atm")
                except ValueError:
                    rows = None
            import live                          # local: same style as do_POST
            from chain_live import _broker       # for the failure body below
            try:
                body = live.build_contract(idx, strike=strike, side=side,
                                           interval=interval, days=days,
                                           chain_rows=rows, atm=atm)
            except Exception as e:
                # Same isolation as /api/data: this index reports its own
                # failure, the others are untouched, and the traceback lands
                # in tapemap.log rather than a closed console.
                log.exception("contract build failed %s", idx)
                body = {"ok": False, "index": idx, "strike": strike,
                        "side": side, "interval": interval, "days": days,
                        # Same "empty, never absent" rule as `rotation` below:
                        # the broker is knowable even when the build failed,
                        # and a reader must not have to tell "no field" from
                        # "no value" to find out which source went down.
                        "broker": _broker(), "expiry_why": None,
                        "expiry": None, "sessions": [],
                        "pair": None, "pair_why": None,
                        "legs": {}, "bars": None, "vwap": None, "oi": None,
                        "bar_days": None, "gaps": [], "gap_reasons": {},
                        # empty, never absent: a consumer that reads `rotation`
                        # must not have to tell "no signals" from "no field".
                        "rotation": [], "rotation_rule": live.ROTATION_RULE,
                        "forming": None, "forming_why": live.FORMING_WHY,
                        "built_at": time.time(),
                        "live_error": f"{type(e).__name__}: {e}"}
            self._json(json.dumps(body).encode())
        elif self.path.startswith("/api/signals"):
            # The live trigger record (trigger_log.py) for the SIGNALS tab.
            #
            # Read from disk PER REQUEST, never cached: the per-index refresh
            # threads append to this file while the operator is looking at it,
            # and a cached copy would show a signal that has already fired as
            # absent. It is a few hundred KB — the read costs nothing worth
            # trading a stale answer for.
            #
            # ?rule=5c (default) | all, ?idx=NIFTY|BANKNIFTY|SENSEX.
            # 5c is the DEFAULT because the file holds two different rules:
            # rows without a `rule` came from §1's one-candle TOUCH, which
            # research-findings marks VOID, and pooling them into a §5c number
            # is the exact mistake `score` already refuses to make. So the
            # counts below are computed per rule and never summed.
            q = parse_qs(urlsplit(self.path).query)
            rule = ((q.get("rule") or ["5c"])[0] or "5c").lower()
            if rule not in ("5c", "all"):
                rule = "5c"
            # NOT self._idx(): that clamps an absent/unknown index to NIFTY,
            # which here would silently filter a log the caller asked to see
            # whole. Absent means every index; unknown means every index.
            want = ((q.get("idx") or [""])[0]).upper()
            if want not in instruments.ENABLED:
                want = ""
            # ?kind=all (default) | entry | arm. A THIRD population, not a
            # third rule: an arm is the setup ARMING (a bar touching d3/u3),
            # and the entry may never come. It is filterable and counted on
            # its own and is never summed into an entry total anywhere below —
            # presenting an arm as a trade signal would inflate what this
            # strategy has produced by every setup that expired unfired.
            kind = ((q.get("kind") or ["all"])[0] or "all").lower()
            if kind not in ("all", "entry", "arm"):
                kind = "all"
            src = ROOT / trigger_log.PATH
            try:
                rows, unparsed = trigger_log.read(src)
            except OSError as e:
                # Explicit, never an empty list. "No signals have fired" and
                # "the log could not be read" produce the same empty table and
                # are opposite facts; the caller gets the reason in the OS's
                # own words so it can say which one this is.
                self._json(json.dumps({
                    "ok": False, "path": str(src),
                    "error": f"{type(e).__name__}: {e.strerror or e}",
                }).encode())
                return
            # Absent `kind` IS "entry" — every row written before 2026-08-12
            # is one, and none of them was rewritten to say so.
            entries = [r for r in rows if r.get("kind") != "arm"]
            arms = [r for r in rows if r.get("kind") == "arm"]
            five = [r for r in entries if r.get("rule") == "5c"]
            legacy = [r for r in entries if r.get("rule") != "5c"]
            sel = rows
            if kind == "arm":
                sel = [r for r in sel if r.get("kind") == "arm"]
            elif kind == "entry":
                sel = [r for r in sel if r.get("kind") != "arm"]
            if rule == "5c":
                # §5c ONLY hides the void one-candle legacy rows. Every arm is
                # §5c by construction, so this cannot filter one out.
                sel = [r for r in sel if r.get("rule") == "5c"]
            if want:
                sel = [r for r in sel if r.get("index") == want]
            self._json(json.dumps({
                "ok": True, "path": str(src), "rule": rule,
                "idx": want or None, "kind": kind,
                "total": len(rows), "unparsed": unparsed,
                # Whole-file counts, per rule, deliberately unaffected by
                # ?idx= — the screen's headline is "what has this strategy
                # produced", and a count that moved with a view filter would
                # answer a different question each time it was read.
                "five_c": {
                    "n": len(five),
                    "buy": sum(1 for r in five if r.get("side") == "BUY"),
                    "sell": sum(1 for r in five if r.get("side") == "SELL"),
                    # An outcome exists only where `python trigger_log.py
                    # score` has filled it. Published as a COUNT, not as any
                    # kind of average: nothing here has been scored, so any
                    # aggregate would be a number about zero measurements.
                    "scored": sum(1 for r in five
                                  if r.get("f15") is not None
                                  or r.get("f30") is not None),
                    # The OPERATOR'S outcome measures (MFE/MAE/stop/bands),
                    # counted apart from f15/f30: they answer a different
                    # question, from a named anchor, and a row can carry
                    # either without the other. Still only a COUNT.
                    "outcome": sum(1 for r in five if r.get("mfe") is not None),
                    # How many were CHECKED and could not be measured. "Could
                    # not score" and "scored, moved nothing" are opposite
                    # facts; a screen that showed one number for both would
                    # render a hole in the cache as a flat trade.
                    "unscored": sum(1 for r in five if r.get("unscored")),
                },
                "legacy": {"n": len(legacy)},
                # The arm population, counted APART from `five_c` and never
                # added to it. `setups` counts distinct setups (§5c: a run of
                # falling lows collapses into ONE, so the re-arms are the
                # remainder), while `n` stays the lossless row count — both
                # published, so a reader never has to guess which one a single
                # number meant. No `scored` here: an arm has no entry price,
                # so it has no outcome to fill, ever.
                "arms": {
                    "n": len(arms),
                    "buy": sum(1 for r in arms if r.get("side") == "BUY"),
                    "sell": sum(1 for r in arms if r.get("side") == "SELL"),
                    "setups": sum(1 for r in arms if not r.get("rearm")),
                    "rearms": sum(1 for r in arms if r.get("rearm")),
                    # The interval every arm was recorded at, published rather
                    # than assumed — a screen that has to guess which candles
                    # it is showing cannot say whether the scored number
                    # applies. None only if the log holds no arm yet.
                    "interval": sorted({r.get("interval") for r in arms
                                        if r.get("interval") is not None}),
                    # How many arms could NOT be given their minute. The field
                    # is timing only, so this is not a defect count — it is
                    # how much of the timing is missing, said out loud instead
                    # of shown as a blank column.
                    "no_minute": sum(1 for r in arms
                                     if r.get("t_1m") is None),
                    # An arm still has no entry price and never gets f15/f30.
                    # It CAN carry the outcome measures, anchored on its own
                    # candle's close and saying so on the row -- that is what
                    # the arms were started for. Counted here, never added to
                    # `five_c` above.
                    "outcome": sum(1 for r in arms if r.get("mfe") is not None),
                    "unscored": sum(1 for r in arms if r.get("unscored")),
                    # Did the setup go on to fire? Three states, never two:
                    # fired, did not, and NOT RE-DERIVED (the cached session
                    # shows no arm on that bar). The third is not a "no".
                    "triggered": sum(1 for r in arms if r.get("triggered")),
                    "not_rederived": sum(1 for r in arms
                                         if r.get("mfe") is not None
                                         and r.get("triggered") is None),
                },
                # The refusal to print a rate, in trigger_log's own words
                # rather than restated in TypeScript -- putting one rule in two
                # languages is exactly how the 09:25 gate drifted for weeks.
                "no_rate_why": trigger_log.rate_refusal(
                    sum(1 for r in five if r.get("mfe") is not None)),
                # Newest first by REVERSAL, not by sorting on `at`: the file is
                # append-only in the order the tape produced the rows, so its
                # own order is the record. A sort would quietly re-rank rows
                # whose `at` collides (three indices log within the same
                # second — 2026-08-10 has two at 09:38).
                "rows": list(reversed(sel)),
                "matched": len(sel),
            }).encode())
        elif self.path.startswith("/api/desk"):
            # Every structure, with a STATUS each -- deployable, stand aside,
            # or blocked with the missing input named. Never a confidence
            # score: nothing here has a track record, and a number a reader
            # takes for a probability would be the one lie this stack cannot
            # afford. `?capital=` (rupees, default Rs 5cr) is the margin
            # capital sizing is built against; it is what makes `lots` per
            # candidate a real number instead of a label on the reading.
            q = parse_qs(urlsplit(self.path).query)
            only = (q.get("idx") or [None])[0]
            try:
                capital = max(1.0, min(
                    float((q.get("capital") or [str(desk_mod.DEFAULT_CAPITAL)])[0]),
                    1000 * desk_mod.ONE_CRORE))
            except ValueError:
                capital = desk_mod.DEFAULT_CAPITAL
            out = {}
            for idx in (instruments.ENABLED if not only else [only]):
                try:
                    surf = _surface_read(self.poller, idx)
                    reg = desk_mod.regime_from_chain(_chain_doc(self.poller, idx))
                    # The raw strikes go through so the lot size is MEASURED
                    # off the chain's own oi/vol GCD rather than read from a
                    # table that rots the next time the exchange revises the
                    # contract-value band.
                    out[idx] = asdict(desk_mod.decide(
                        surf, reg, capital,
                        strikes=(_chain_doc(self.poller, idx) or {}).get("strikes"),
                        view=_view_for(idx, self.payloads)))
                except Exception as e:
                    out[idx] = {"index": idx, "fit_ok": False, "best": None,
                                "candidates": [],
                                "why": [f"{type(e).__name__}: {e}"]}
            self._json(json.dumps({
                "ok": any(v.get("best") for v in out.values()),
                "capital": capital,
                "indices": out,
            }).encode())
        elif self.path.startswith("/api/surface"):
            # The fitted vol surface per index, and which points sit off the
            # curve. All three by default, because "which instrument is paying
            # best" is a first-class question and cannot be answered one index
            # at a time.
            q = parse_qs(urlsplit(self.path).query)
            only = (q.get("idx") or [None])[0]
            out = {}
            for idx in (instruments.ENABLED if not only else [only]):
                try:
                    out[idx] = asdict(_surface_read(self.poller, idx))
                except Exception as e:   # a bad chain must not 500 the panel
                    out[idx] = {"index": idx, "fit": {"ok": False},
                                "why": [f"{type(e).__name__}: {e}"]}
            # Ranked by ATM vol only when a fit succeeded. This is NOT yet the
            # richness ranking the selector needs -- that wants multi-day
            # history the forward log has not accumulated -- and says so.
            fitted = [(i, d) for i, d in out.items()
                      if (d.get("fit") or {}).get("ok")]
            self._json(json.dumps({
                "ok": bool(fitted),
                "indices": out,
                "ranked": [i for i, _ in sorted(
                    fitted, key=lambda kv: -(kv[1]["fit"]["atm_iv"] or 0))],
                "note": ("ranked by ATM vol, which is a LEVEL not a richness. "
                         "Ranking by richness needs multi-day history that "
                         "does not exist yet."),
            }).encode())
        elif self.path.startswith("/api/drag"):
            # THE BUYER'S TAX, PER INDEX. Not a signal and not a gate: a
            # meter. It says whether being right is even payable today, which
            # is the question that turned this stack from a buyer's alarm into
            # a seller's desk.
            #
            # EVERY FIELD IS ALLOWED TO BE None AND USUALLY IS. Before the
            # anchor exists, on an index that has not moved, and on the leg
            # the move went AGAINST, there is no honest number -- `drag.py`
            # refuses rather than reporting an enormous meaningless percentage
            # on a trade that simply lost. A reader that renders those as zero
            # is reading it wrong.
            q = parse_qs(urlsplit(self.path).query)
            only = (q.get("idx") or [None])[0]
            with _SENSES_LOCK:
                boards = dict(_SENSES["drag"] or {})
            out = {i: b.read() for i, b in boards.items()
                   if not only or i == only}
            self._json(json.dumps({
                "ok": bool(out),
                "indices": out,
                "note": ("owed = delta x the underlying's move; paid = what "
                         "the premium actually did; drag = owed - paid, and "
                         "frac is that as a RATE. Deltas are real, off the "
                         "chain -- there is no assumed 0.5 here, and that "
                         "assumption is why this module exists."),
            }).encode())
        elif self.path.startswith("/api/senses"):
            # A WINDOW, NOT THE RECORD. The forward record is
            # data/senses_log.jsonl; this renders the tail of the ring so a
            # panel can show what the book just did. `err` and `polls` are
            # here for the same reason /api/health names the broker: a thread
            # that has quietly stopped must not look like a quiet market.
            q = parse_qs(urlsplit(self.path).query)
            n = min(int((q.get("n") or ["100"])[0] or 100), 2000)
            inst = (q.get("inst") or [None])[0]
            with _SENSES_LOCK:
                rows = list(_SENSES["rows"] or ())
                if inst:
                    rows = [r for r in rows if r.get("inst") == inst]
                obj = _SENSES["obj"]
                # The READING, kept separate from the rows. `gear` is [I] and
                # SHADOW -- `would_block` is what it WOULD refuse, and nothing in
                # this stack enforces it. A panel that renders this as a block is
                # reading it wrong.
                book = _SENSES["fuse"]
                read = {}
                if book is not None:
                    for i, f in sorted(book._by.items()):
                        if inst and i != inst:
                            continue
                        idx_i = i.split("-")[0]
                        # The chain half, matched to this instrument's index. All
                        # three conditions finally meet here: fuel and drain from
                        # the chain, ignition from the book. Absent chain -> the
                        # gate simply cannot reach CASCADE, which is correct.
                        c = _SENSES["chain"].get(idx_i) or {}
                        # The other two dead gears -- see _regime_engine_read
                        # and _walls_holding for why these were None until
                        # 2026-08-22 and where each value actually comes from.
                        sigma_pctl, vwap_flips_per_hr, eng_why = \
                            _regime_engine_read(self.payloads, idx_i)
                        walls_holding, walls_why = _walls_holding(
                            _SENSES["pools"].get(i))
                        v = f.verdict(fuel_rank=c.get("fuel_rank"),
                                      drain=bool(c.get("drain")),
                                      one_sided=c.get("one_sided"),
                                      sigma_pctl=sigma_pctl,
                                      vwap_flips_per_hr=vwap_flips_per_hr,
                                      walls_holding=walls_holding)
                        read[i] = {"gear": v.gear, "why": v.why, "chain": c,
                                   "would_block": v.would_block, "shadow": v.shadow,
                                   "tag": v.tag, "evidence": f.ev.__dict__,
                                   "regime_inputs": {
                                       "sigma_pctl": sigma_pctl,
                                       "vwap_flips_per_hr": vwap_flips_per_hr,
                                       "walls_holding": walls_holding,
                                       "why": [w for w in (eng_why, walls_why) if w],
                                   }}
                self._json(json.dumps({
                    "ok": _SENSES["err"] is None,
                    "error": _SENSES["err"],
                    "polls": _SENSES["polls"],
                    "up_s": (round(time.time() - _SENSES["started"], 1)
                             if _SENSES["started"] else None),
                    "written": getattr(obj, "written", 0),
                    "failed": getattr(obj, "failed", 0),
                    "log": getattr(obj, "path", None) or senses_mod.day_path(),
                    "pending": obj.pending() if obj else {},
                    # Is the Kite bridge alive? A dead bridge costs exactly the
                    # wall-vs-cluster answer, and must say so rather than letting
                    # every shelf read as "unknowable" for a silent reason.
                    "orders_bridge": {
                        "books": _SENSES["orders_n"],
                        "age_s": (round(time.time() - _SENSES["orders_at"], 1)
                                  if _SENSES["orders_at"] else None),
                    },
                    "read": read,
                    "pools": _SENSES["pools"],
                    "rows": rows[-n:],
                }).encode())
        else:
            super().do_GET()

    def handle_one_request(self):
        """5d -- the ONE seam every GET/POST/OPTIONS passes through, timed
        into `http_ms` without touching `do_GET`/`do_POST` themselves.

        Overriding here rather than decorating `do_GET`/`do_POST` directly
        was deliberate: `test_upstox_only.py` introspects
        `inspect.getsource(server.Handler.do_POST)` to verify an ordering
        invariant, and a decorator without the original method's own source
        would have broken that test for a reason having nothing to do with
        what it checks. `BaseHTTPRequestHandler.handle_one_request` is the one
        place `http.server` already routes every method through, so timing it
        here catches all three without touching either handler's body.
        """
        t0 = time.perf_counter()
        try:
            super().handle_one_request()
        finally:
            _record_latency("http_ms", (time.perf_counter() - t0) * 1000.0)

    def log_message(self, *a):
        pass


def _view_for(idx, payloads):
    """The direction view for one index, or None if the tape cannot form one.

    NONE IS A RESULT, NOT A FAILURE. `desk.decide` blocks the flow half of the
    catalog with its reason named when this returns None, exactly as it did
    before a direction view existed at all -- so a cold server, a market that
    is shut, or a chain that has not warmed produces a readable screen rather
    than an error.

    It assembles the same two halves `/api/senses` already assembles, and for
    the same reason: ignition is a BOOK quantity and fuel/drain are CHAIN
    quantities, so neither source can answer alone. `fuse` supplies the gear
    with ignition folded in; `chainside` supplies the trapped side.
    """
    with _SENSES_LOCK:
        book = _SENSES["fuse"]
        chain = (_SENSES["chain"] or {}).get(idx)
        if book is None or not chain:
            return None
        # One index can carry several instruments (the future plus the strikes
        # around it). The FUTURE is the tape that matters for ignition -- a
        # single deep-OTM leg's book is thin enough that every flicker reads
        # extreme, which is the volume-scoping trap from HANDOFF-OPERATOR §2.6.
        #
        # MATCH THE SUFFIX, NOT THE HYPHEN COUNT. This read
        # `p[0].count("-") <= 1` until 2026-08-22, on the belief that a strike
        # leg carried an extra hyphen. It does not: keys are minted as
        # f"{idx}-FUT" and f"{idx}-{strike}{CE|PE}" (see the senses thread
        # below), so BOTH have exactly one hyphen, the filter matched
        # everything, and `next` returned the first item of a sorted list --
        # in which "NIFTY-24450CE" precedes "NIFTY-FUT" because digits sort
        # before letters. Ignition was therefore read off whichever near
        # strike happened to sort first, never the future: the exact trap the
        # paragraph above warns about, two lines under the warning.
        fuses = [(i, f) for i, f in sorted(book._by.items())
                 if i.split("-")[0] == idx]
        if not fuses:
            return None
        inst, f = next((p for p in fuses if p[0].endswith("-FUT")), fuses[0])
        sigma_pctl, vwap_flips_per_hr, _eng_why = _regime_engine_read(payloads, idx)
        walls_holding, _walls_why = _walls_holding(_SENSES["pools"].get(inst))
        v = f.verdict(fuel_rank=chain.get("fuel_rank"),
                      drain=bool(chain.get("drain")),
                      one_sided=chain.get("one_sided"),
                      sigma_pctl=sigma_pctl,
                      vwap_flips_per_hr=vwap_flips_per_hr,
                      walls_holding=walls_holding)
    return direction_mod.read(chain, v.gear)


def _build_why(e):
    """Turn a live-build failure into a sentence that names the ACTUAL cause.

    Every exception used to print "waiting for a valid Dhan token", which is
    the one thing the operator can act on and therefore the one thing they
    tried. On 2026-08-05 that cost an hour: the token was perfect -- it
    authenticated against /v2/fundlimit with HTTP 200 -- but the DATA API
    subscription had lapsed, so every intraday call came back 401 / DH-902.
    The screen said "click TOKEN", and clicking it could never have helped.

    A wrong diagnosis is worse than none, so anything unrecognised now says so
    and points at the log instead of blaming the token.
    """
    body = ""
    try:                                   # HTTPError carries Dhan's JSON body
        body = e.read().decode(errors="replace")[:400]
    except Exception:                      # noqa: BLE001 - not an HTTPError
        pass
    code = getattr(e, "code", None)
    if "DH-902" in body or "not subscribed to Data APIs" in body:
        return ("Dhan DATA API subscription is not active (DH-902). The token "
                "is fine — the historical/intraday plan needs renewing at "
                "dhan.co. Clicking ⟳ TOKEN will not fix this.")
    if code == 429:
        return "Dhan rate-limited the tape (HTTP 429) — backing off, no action needed"
    if code == 401:
        return ("Dhan refused the request (HTTP 401). Check the token first, "
                "then the Data API subscription."
                + (f" Dhan said: {body}" if body else ""))
    if code:
        return f"Dhan returned HTTP {code}" + (f": {body}" if body else "")
    return f"live build failed ({type(e).__name__}) — see tapemap.log"


def _start_chain(mock, configs):
    from chain_live import ChainPoller
    poller = ChainPoller(configs, mock=mock)
    poller.start()
    log.info("chain poller started%s for %s",
             " (MOCK fixture)" if mock else "",
             ", ".join(c["under_sym"] for c in configs))
    return poller


def main():
    _setup_logging()
    argv = [a for a in sys.argv[1:] if a != "--mock-chain"]
    mock_chain = "--mock-chain" in sys.argv[1:]
    if argv and argv[0] == "live":
        import threading
        import time as _t
        from live import DEFAULT_INTERVAL, REFRESH_S, build_session
        port = int(argv[1]) if len(argv) > 1 else 8765

        def _waiting(sym, why):
            return json.dumps({"index": sym, "strike": None, "days": [],
                               "built_at": time.time(),
                               "live_error": why}).encode()

        # Crash-proof deferred startup: bind the server immediately with
        # "starting up" payloads, then resolve instruments + build the tape in
        # the background loop. A stale or missing .dhan_token can no longer stop
        # the server from coming up — start it, open the UI, click the TOKEN
        # button, and the next refresh (<= REFRESH_S) brings the tape live. The
        # chain poller only needs the static under_id/seg, so it starts on its
        # own. (resolve_dynamic uses the public scrip master, no token needed.)
        cfgs = {x: instruments.get(x) for x in instruments.ENABLED}
        payloads = {x: {"payload": _waiting(x, "starting up — resolving…")}
                    for x in instruments.ENABLED}
        have = {x: False for x in instruments.ENABLED}
        # BIND FIRST -- before the chain poller opens a websocket. The poller
        # used to start here, so a second server that went on to lose the port
        # had already taken an Upstox socket, and kept it. Claiming the port is
        # the cheapest thing that can fail, so it goes first: a duplicate now
        # dies below having taken nothing.
        late = {"chains": None, "poller": None}
        try:
            httpd = _Server(("127.0.0.1", port),
                            partial(Handler, payloads=payloads, late=late))
        except OSError as e:
            log.error("cannot bind 127.0.0.1:%s (%s). Another TapeMap server "
                      "is already running -- stop it first with stop.bat, "
                      "then start again.", port, e)
            sys.exit(1)
        poller = _start_chain(mock_chain, list(cfgs.values()))
        chains = poller.boxes
        late["chains"], late["poller"] = chains, poller
        log.info("LIVE server up on http://127.0.0.1:%s for %s (refresh %ss). "
                 "Need a token? Click TOKEN in the UI.", port, list(cfgs), REFRESH_S)

        # One refresh thread PER INDEX: a slow download or bad instrument on
        # one index can no longer stall the other two (2026-07-27: a single
        # serial loop froze all three tapes at once). The scrip master behind
        # resolve_dynamic is lock-guarded and day-cached in instruments, so
        # three threads still cost one download.
        def refresh_one(x, c, stagger):
            _t.sleep(stagger)       # de-phase the per-index cycles
            first = True
            while True:
                if not first:
                    _t.sleep(REFRESH_S)
                first = False
                try:
                    if "fut_id" not in c:
                        instruments.resolve_dynamic(
                            c, "", _t.strftime("%Y-%m-%d"))
                    # The chain poller already knows the live INDEX price.
                    # Hand it over: the tape is the monthly future, the legs
                    # are the nearest weekly, and pricing one off the other
                    # put a 59-point carry into the option maths on
                    # 2026-08-04 (every CE unsolvable, PE IV 2.3x the
                    # chain's). Absent chain -> None -> old behaviour.
                    # The poller publishes it beside the bytes; one dict read
                    # replaces a full-payload json.loads per cycle.
                    box = chains.get(x)
                    spot = box.get("spot") if box else None
                    # The engine still runs on 1-minute data; what gets
                    # published is derived per interval by payload_at above.
                    base = build_session(c, spot=spot)
                    box = payloads[x]
                    if base.get("error") is not None:
                        box["session"] = None
                        box["payload"] = base["error"]
                    else:
                        box["payload"] = None
                        box["stamp"] = base["built_at"]
                        # A NEW dict, not a clear(): a reader holding the old
                        # one keeps serving a coherent older build rather than
                        # racing an empty cache. Bounds memory at one payload
                        # per supported interval per index.
                        box["by_interval"] = {}
                        box["session"] = base      # last: it is what arms the rest
                    have[x] = True
                    # Log any NEW band-rotation trigger with the gamma/OI
                    # context the operator watches (trigger_log.py). log_new
                    # is fail-soft by contract — the tape must never stall
                    # for the logger's sake (2026-07-27 post-mortem).
                    #
                    # Logged at the SCORED interval, not at whatever a browser
                    # last asked for. The forward test only means something
                    # against the bars §5c was measured on, and until
                    # 2026-08-11 this logged 1-minute records — a different
                    # rule, silently.
                    #
                    # The ONE-MINUTE bars go along for TIMING ONLY: each arm
                    # is a 3-minute record, and `ones` only names which minute
                    # inside that candle made the extreme. Taken from the
                    # session the payload was derived from -- the same bars
                    # `_at_interval` resampled -- so it costs nothing and
                    # cannot be a different session.
                    _sess = payloads[x].get("session")
                    trigger_log.log_new(
                        x, payload_at(payloads[x], DEFAULT_INTERVAL),
                        poller.states.get(x) if poller else None,
                        ones=((_sess.get("day") or {}).get("bars")
                              if isinstance(_sess, dict) else None))
                except Exception as e:  # keep last good data; else say why
                    log.exception("live build failed %s", x)
                    if not have[x]:
                        payloads[x]["payload"] = _waiting(x, _build_why(e))
                    if "429" in str(e):     # rate-limited: back off, don't hammer
                        log.warning("%s rate-limited, backing off 20s", x)
                        _t.sleep(20)

        for n, (x, c) in enumerate(cfgs.items()):
            threading.Thread(target=refresh_one, args=(x, c, n * 5),
                             daemon=True, name=f"refresh-{x}").start()
        # The book detectors, on their own clock. Daemon like the rest: it
        # must not hold the process open, and it must not be waited on.
        #
        # RUNS UNDER --mock-chain TOO, as of 2026-08-22. The near-ATM book
        # detectors still need a real feed and stay silent without one (see
        # `_senses_loop`'s `feed_ok` gate), but 5a/5b's chain-payload trigger
        # -- the surface forward log and the desk transition log -- needs
        # only `poller.boxes`, which the mock poller publishes into just like
        # the live one. Skipping this thread under mock used to mean
        # --mock-chain could not exercise 5a/5b at all; it now can, which is
        # the acceptance criterion this task was built against.
        if poller is not None:
            threading.Thread(target=_senses_loop, args=(poller, payloads),
                             daemon=True, name="senses").start()
            log.info("senses thread started -> %s", senses_mod.day_path())
        httpd.serve_forever()          # bound above, before anything was taken
        return
    port = int(argv[0]) if argv else 8765
    base = argv[1] if len(argv) > 1 else "data"
    strike = float(argv[2]) if len(argv) > 2 else 24200.0
    poller = (_start_chain(True, [instruments.get(x) for x in instruments.ENABLED])
              if mock_chain else None)
    chains = poller.boxes if poller else None
    payload = json.dumps(analyze(base, strike)).encode()
    payloads = {instruments.DEFAULT: {"payload": payload}}
    log.info("analysis ready (%s KB), serving on http://127.0.0.1:%s",
             len(payload) // 1024, port)
    ThreadingHTTPServer(("127.0.0.1", port),
                        partial(Handler, payloads=payloads,
                                chains=chains, poller=poller)).serve_forever()


if __name__ == "__main__":
    main()
