"""Local server for the tape-engine UI.

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
import re
import logging
import math
import os
import sys
import threading
import time
from dataclasses import asdict
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import band_rotation
import chainside as chain_mod
import day_state
import desk_log
import direction as direction_mod
import drag as drag_mod
import warmap as warmap_mod
import fuse as fuse_mod
import breadth as breadth_mod
import frame
import frame_log
import fronts                    # research-findings §1d: the near-ATM fronts
import grounds                   # every engine call held against OI, CVD and order flow
import board                     # BOARD rev 3's read, one index at one finished minute (display only)
import trendbox                  # ...and its trend box, on the index's own candles
import calls_log                 # ...and kept, one row per engine bar, in session only
import daytype                   # AAJ KA DIN: trend or pin/chop, on /api/calls for the answer band (display only)
import read                      # THE READ: one held read per index, OI first (GET /api/read; display only)
import hold                      # the hold / fold window, as registered (PREREG-merged.md rev 4 + PREREG-rev5.md option B)
import hold_log                  # ...and its forward logs, write-once
import fold_live                 # the rev 6 engine (fold.py) run live: /api/fold*, the frame's fold / flat (API-v3)
import receipts                  # her trades' receipts + the KPI (validate-tab-spec §7): GET /api/receipts, POST /api/receipts/import
import trade_record              # her trade's thesis / roles / acks / re-plans / tags on /api/hold/trades (Validate spec §2, §7)
import validate_live             # the live in-trade read: /api/validate, frame.validate (Validate spec, adapted 2026-10-05)
import feed_health               # is the GoCharting tape alive? from the data (P3): /api/feed/gc, and `feed` on the faces' replies
import reader_live               # the SHADOW leg engine (reader.py) on its own thread: GET /api/reader, data/reader/
import xindex_live               # the SHADOW cross-index read (xindex.py) on the reader's pass: GET /api/xindex, data/xindex/
import chain_metrics             # ChainState.oi_flow: the OI Flow tab's marks, re-used by /api/sides
import sides                     # the OI flow split by side against the index move (Board round 4): GET /api/sides
import sides_log                 # ...and its forward log, once per closed slot, market hours only: data/sides/
import trap                      # the trap layer, SHADOW (docs/board/TRAP-PREREG-2026-10-04.md): GET /api/trap
import trap_log                  # ...its forward log (data/trap/) and its incremental readers of the recorders' files
import decoder_log               # the decoder's forward log (data/decoder/), from the events the extension posts (Fable §6.1)
import effort                    # A44: effort per point (Kyle lambda) at a fresh extreme, DECODE's EFFORT line (display only)
import dext_log                  # GATE 3: the Dext extension's 1m candles + getData rows, recorded only (data/dext/)
import dext_parity               # ...and the three-way parity (Dext / Upstox / GoCharting): GET /api/dext/parity
import plan                      # THE PLAN beside the window (docs/hold/PLAN-PREREG.md rev 2a, §1f)
import validate                  # ...and the Validate tab's GO / WAIT / NO (docs/hold/VALIDATE-PREREG.md rev 2)
import expression                # ...and THE EXPRESSION, buy or sell, and the writer's word (EXPRESSION-PREREG.md rev e)
import daylog                    # week-old daily records kept as .jsonl.gz
import tape_log
import book_log
import ux_log
import ux_gate as gate_mod      # amended at Task 9: gate.py is the seller's gate
import runs as runs_mod
import impact as impact_mod
import upstox_instruments
import prints
import instruments
import oi_dwell
import pools as pools_mod
import record_read
import score_frame

# idx -> the closed-bar count the record was last scored against.
_SCORED_BARS = {}
import senses as senses_mod
import surface as surface_mod
import trigger_log
import confluence_log            # research-findings §1i: the confluence setup's forward log, beside trigger_log
import hold2                     # research-findings §1m: HOLD v2's line beside the hold window's word (display only)
import holdshadow                # three HOLD v3 candidate lines beside HOLD v2 (NOTEPAD), shadow + forward log only
import sensex_flow               # SENSEX reads NIFTY's order flow (SENSEX-NIFTY-FLOW-PREREG §1q, signed 25 Oct)
import voice                     # THE ONE VOICE in a trade (A52): one state ladder over the word + HOLD v2, display only
import trademap                  # THE TRADE MAP (A53-A59): the voice's l4 / l5 / [detail], display only
import voice_path                # the voice replayed over a past marked trade (A56), GET /api/voice_path
import upstox_adapter
import vpin as vpin_mod

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
           # THE OI WAR MAP, one board per index (warmap.Boards). Fed at
           # chain pace in the senses loop, served at /api/warmap. Shadow
           # end to end: it describes the battlefield and gates nothing.
           "warmap": None,
           # THE BUYER'S TAX, one Board per index, session-anchored.
           # `drag.py` was written earlier, tested, and never called by
           # anything -- both handoffs say so. This is its first caller. It
           # answers the question the whole seller pivot rests on: even with
           # the direction exactly right, what fraction of the move did a
           # buyer actually collect?
           "drag": {},
           # THE TAX'S DAY TRACE, idx -> deque of {t, frac, side} sampled at
           # chain pace. In-memory like the boards themselves (resets with
           # the server, honestly "since start"), so /api/drag can say what
           # the day DID and not only where the meter stands.
           "drag_day": {},
           # How many drag samples `_load_day_state` put back from
           # data/day_state/ at startup -- 0 on a cold day. Published so a
           # reading can say "restored" rather than let a reader assume this
           # process watched the whole session. NOT a backfill flag: those
           # rows were observed, by an earlier process on the same day.
           "day_restored": 0,
           # ORDER-FLOW TOXICITY (vpin.Gauge), NIFTY future only, SHADOW end
           # to end: nothing downstream reads it. Fed in the senses loop from
           # the same frame the ladder comes from; completed buckets go to
           # VPIN_LOG, the reading to /api/senses. inst -> Gauge.
           "vpin": {},
           # THE TAPE, POSTed whole-day by the Chrome extension at
           # /api/frame -- idx -> {"doc": <the tape>, "at": time.time()}.
           # frame.py (Task 2) reads this; frame.py does not exist yet, so
           # today's handler only stores it and answers have_bars.
           "tape": {},
           # THE BOOK RECORD (spec 2026-09-20-upstox-tape §B): the deque the
           # feed thread fills and the loop drains. `book_rows` is what the
           # last drain wrote, for ux_log to consume on the same pass.
           "book": book_log.Book(), "book_rows": [],
           # THE WATCHED CONTRACT per index (pro-tool P1-02..P1-05): idx -> {"ik", "expiry",
           # "expired"} off upstox_instruments.resolve, re-set every senses pass beside Book.watch.
           # `expiry` blinds the futures-OI read in its expiry week, `expired` cuts the Trade tab's
           # prior days at the roll, `ik` stamps the book and ux rows.
           "contract": {},
           # per-index lot/tick and the two book-derived detectors (spec §G);
           # keyed by idx, reset on a day roll in the loop
           "ux": {},
           # the shared flush/step half of `_ux_drain` names its own failure
           # here -- process-wide, not per index (`ux` state's `rebuild_why`
           # is per index, for the rebuild half only). Sticky: the FIRST
           # failure's reason is kept (a clean pass does not clear it, so a
           # reader never sees "no problem" for a wire that is still short
           # bars), `ux_drain_failed` counts every failure since, and a day
           # roll resets both.
           "ux_drain_why": None,
           "ux_drain_failed": 0,
           # THE FRAME the tape most recently produced, idx -> the dict also
           # appended to frame_log when its signature changes. Placeholder
           # until frame.py lands.
           "frame": {}}

# The toxicity forward record. Reassigned by _isolate_mock_writers so a
# fixture replay can never write into the live record (the 2026-08-24 leak).
VPIN_LOG = str(ROOT / "data" / "vpin_log.jsonl")
# FEED HEALTH transitions (feed_health.py): one row per state change of the GoCharting tape, the record the hidden-tab
# measurement of N is read from. Runtime only; tests leave feed_health.LOG None.
feed_health.LOG = str(ROOT / "data" / "feed_log.jsonl")

# THE MORNING NOBODY WATCHED, and why it is a DIFFERENT FILE.
#
# `VPIN_LOG` is the promotion evidence for a shadow module on a declared
# 30-session kill clock (vpin.py's docstring: "pct >= 0.90 must precede range
# expansion at better than base rate, or this module dies"). Rows rebuilt from
# 1-minute bars are a coarser measurement of the same tape -- BVC, one sign per
# minute instead of per frame -- and a row is only evidence if you can still
# tell, months later, whether the socket saw it. Written into the same file
# they would be indistinguishable the moment they landed, and the clock would
# be counting minutes the tool was not running for. Separate file, every row
# additionally tagged `backfill: true`, and /api/vpin republishes the tag.
VPIN_BACKFILL_LOG = str(ROOT / "data" / "vpin_backfill.jsonl")
# THE FAST LINE'S OWN FILE (vpin.FAST_BUCKET_V). A SEPARATE POPULATION, kept
# in a separate file for the same reason the backfill log is: `VPIN_LOG` is the
# promotion evidence for a shadow module on a declared 30-session kill clock,
# and two bucket sizes in one file would be one record of two different
# measurements. Nothing ranks, averages or counts across the two.
VPIN_FAST_LOG = str(ROOT / "data" / "vpin_fast.jsonl")
# The gauge dict's key for it. `_book_for` and the frame read `f"{idx}-FUT"`
# exactly, so the suffix keeps the fast line out of everything downstream --
# it is displayed and logged, and read by nothing, exactly like the slow one.
VPIN_FAST_INST = "NIFTY-FUT:fast"

# OPEN OPERATOR DECISION, parked OFF until she rules on it.
#
# The live gauge's percentile is percentile-of-THIS-SESSION (the cross-day
# reference was built and rejected on 2026-08-25 -- see vpin.Gauge.seed). So a
# server started at 11:00 is mute until MIN_HIST live buckets complete, around
# lunch, and the morning's backfilled buckets are sitting right there and could
# fill that window instead.
#
# THE ARGUMENT AGAINST, which is why the default is False: a percentile is only
# honest over ONE population, and backfilled buckets are a different
# measurement of the same tape, not more of the same measurement. BVC's
# one-sign-per-minute is smoother than the live frame path, so seeding would
# push the reference distribution DOWN and make the first live burst rank
# higher than it deserves -- alarming on exactly the mornings this is turned on
# for. The mute morning is the honest price, the same price the module already
# pays every day.
#
# THE ARGUMENT FOR: a mute gauge on a late start is the failure the operator
# named, and a slightly-wrong percentile may beat no percentile at all.
#
# Flip to True and `_seed_vpin` feeds the backfilled rows in ahead of the live
# ones. /api/vpin publishes this flag either way, so a reading never hides
# which population it was ranked against.
SEED_LIVE_GAUGE_FROM_BACKFILL = False

# What `_backfill_vpin` found, for /api/vpin to explain itself with. `why` is
# never None and never empty: "we could not check", "we checked and found
# nothing" and "there was no gap to fill" are three different sentences.
_VPIN_BF = {"n": 0, "why": "not attempted yet"}

# How often the day's RAM-only series is written down. A crash costs at most
# this much of the trace, and the whole ring is rewritten each time (~500KB for
# three indices at full length), so a minute is the balance between losing work
# and rewriting a file for nothing.
DAY_STATE_EVERY_S = 60

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

# Hysteresis for the desk's published state (oi_dwell.py). Module-level so it
# shares `desk_state`'s lifetime exactly: both reset on process start, so a
# bounce re-confirms every field from scratch rather than resuming a gate
# whose evidence is gone. Held across indices -- one Gate per (idx, field).
_DESK_GATE = oi_dwell.StateGate()


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


# (idx, day, file size) -> the parsed day. The log only ever APPENDS, so an
# unchanged size means an unchanged answer and the file is not re-read on
# every desk poll.
_SURF_DAY_CACHE = {}


RV_SESSIONS = 6      # closes read -> up to 5 close-to-close returns
RV_MIN_RETURNS = 4   # below this the stdev is noise, and says so
RV_ANNUALIZE = 252.0


def _rv5(idx):
    """Realized vol over the last cached sessions. [M] -- measured from bars.

    `(rv5, why)`, exactly one of them not None. The closes come from
    `data/backtest/fut_*.json`, which `eod_capture` writes and
    `recover_tape.py` can refill -- so this is the tool's own captured record,
    not a live fetch, and it is only as complete as that cache. NIFTY sits at
    the top level; the other indices under their own subdirectory.

    METHOD, stated because an unlabelled vol number is unusable: the LAST
    close of each session, close-to-close LOG returns, SAMPLE standard
    deviation (n-1), annualized by sqrt(252).

    THE 252-vs-365 BASIS, named rather than buried. Variance accumulates only
    on days the market trades, so sqrt(252) is the right annualizer for a
    realized number. But `gamma.DAYS_PER_YEAR` and `surface.years_to_expiry`
    put IV's T on a 365 CALENDAR basis. The two are therefore not directly
    subtractable without care -- comparing RV to IV is the whole point of
    having this, so the convention travels with the number instead of a reader
    assuming they match.
    """
    base = ROOT / "data" / "backtest"
    d = base if idx == "NIFTY" else base / idx
    try:
        files = sorted(p for p in d.glob("fut_*.json"))[-RV_SESSIONS:]
    except OSError:
        return None, f"could not read {d}"
    closes = []
    for p in files:
        try:
            with open(p, encoding="utf-8") as fh:
                c = (json.load(fh) or {}).get("close") or []
            if c and c[-1]:
                closes.append(float(c[-1]))
        except (OSError, ValueError, TypeError):
            continue          # a corrupt capture is skipped, never zero-filled
    rets = [math.log(b / a) for a, b in zip(closes, closes[1:])
            if a > 0 and b > 0]
    if len(rets) < RV_MIN_RETURNS:
        return None, (f"only {len(closes)} usable cached session(s) for {idx} "
                      f"({len(rets)} return(s)); need at least "
                      f"{RV_MIN_RETURNS + 1} sessions. eod_capture fills this "
                      f"daily and recover_tape.py can backfill a missing one")
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return {"rv": round(math.sqrt(var) * math.sqrt(RV_ANNUALIZE), 4),
            "sessions": len(closes), "n_returns": len(rets),
            "method": ("close-to-close log returns on the last close of each "
                       "cached session, sample stdev (n-1), annualized "
                       "sqrt(252)"),
            "basis_note": ("annualized on 252 TRADING days; IV's T in this "
                           "repo is 365 CALENDAR (gamma.DAYS_PER_YEAR) -- do "
                           "not subtract them without accounting for that"),
            "tag": "M"}, None


def _surface_day(idx):
    """Today's a/b/c story for one index, read back from the forward log.

    Returns None when today has no file or no fits for this index -- a
    stated absence the panel renders as such, never a fabricated flat day.
    `desk_log.surface_path()` is called at request time so --mock-chain's
    writer isolation carries over automatically.
    """
    path = desk_log.surface_path()
    try:
        size = os.path.getsize(path)
    except OSError:
        return None
    key = (idx, path, size)
    hit = _SURF_DAY_CACHE.get(key)
    if hit is not None:
        return hit
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("idx") == idx and r.get("a") is not None:
                rows.append(r)
    if not rows:
        return None
    hi = max(rows, key=lambda r: r["a"])
    lo = min(rows, key=lambda r: r["a"])
    step = max(1, len(rows) // 60)      # ~60 points is plenty for a sparkline
    out = {
        "n": len(rows),
        "open": {"t": rows[0]["ts"][11:16], "a": rows[0]["a"], "b": rows[0]["b"]},
        "now": {"t": rows[-1]["ts"][11:16], "a": rows[-1]["a"], "b": rows[-1]["b"]},
        "hi": {"t": hi["ts"][11:16], "a": hi["a"]},
        "lo": {"t": lo["ts"][11:16], "a": lo["a"]},
        "series": [{"t": r["ts"][11:16], "a": round(r["a"], 5)}
                   for r in rows[::step]],
    }
    for k in [k for k in _SURF_DAY_CACHE if k[0] == idx]:
        del _SURF_DAY_CACHE[k]          # one live key per index is enough
    _SURF_DAY_CACHE[key] = out
    return out


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
    starts trusting `bw_r` -- `i` is a 0-indexed bar count, so that first
    fires on the (MATURITY+1)-th bar, and `len(fut) > MATURITY` mirrors it
    exactly rather than one bar early. Fewer bars than that and both values
    are None with a reason, per constraint 3 -- never a number from noise.
    """
    from engine import MATURITY
    box = (payloads or {}).get(idx)
    sess = box.get("session") if isinstance(box, dict) else None
    bars = ((sess or {}).get("day") or {}).get("bars") if sess else None
    if not bars:
        return None, None, f"no live engine session yet for {idx}"
    fut = [b["fut"] for b in bars if b.get("fut")]
    if len(fut) <= MATURITY:
        return None, None, (f"only {len(fut)} bar(s) this session; the "
                            f"engine's own bands need {MATURITY + 1} before "
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

    WHY HERE, AND WHY THIS COSTS NOTHING EXTRA. This is called once per new
    chain payload for `idx` -- the same trigger `_senses_loop` already uses
    to re-parse the chain, which happens once per ~10s refresh, never per
    poll. The surface fit is real work; gating it on the same trigger, rather
    than the 0.5s loop tick, is what keeps it off the loop's own budget -- it
    already only runs at chain pace, which IS the requirement, not a separate
    throttle bolted on.

    CALLED WITHOUT `_SENSES_LOCK` HELD. `_senses_loop` queues `(idx, doc)`
    pairs while it holds the lock and calls this function only after
    releasing it, so the fit never blocks `/api/senses` or `/api/drag`, both
    of which also take `_SENSES_LOCK`. `_view_for` still needs a couple of
    `_SENSES` fields and re-acquires the lock itself, briefly, for that read
    alone.

    NEVER NEEDS THE BOOK FEED. `_surface_read` falls back to spot when the
    future is unavailable, and `_view_for` returns None gracefully when the
    book (fuse) or chain half is not ready. That is what lets this run under
    --mock-chain, where `poller.src` never exists at all.

    `desk_state` is the caller's idx -> {gear, conviction, oi_dir} cache;
    mutated in place so the next tick has something to diff against. It
    resets to empty on every process start (the server is bounced routinely),
    so the FIRST reading for an index in a process diffs against `{}` and
    every field reports "changed from None" -- a restart pseudo-transition,
    not an observed one, but with the identical row shape unless marked.
    That first-reading call is logged with `baseline=True` (desk_log.py); any
    later call for the same index, including one where a field moves from
    None to a real value for the first time mid-session, is a plain
    transition with no marker -- see desk_log.py's module docstring.
    """
    surf = _surface_read(poller, idx)
    if surf.fit.ok:
        skew_x = surface_mod.SKEW_X
        b = -(surf.fit.skew / (2.0 * skew_x)) if surf.fit.skew is not None else None
        desk_log.log_surface(idx, surf.fit.atm_iv, b, surf.fit.convexity,
                             surf.fit.rmse, surf.f_src, surf.expiry,
                             surf.fit.n)

    view = _view_for(idx, payloads)

    # The RAW per-snapshot reading -- correct, and by itself unreadable.
    # Measured 2026-08-24: published straight through, the desk's fields
    # produced 1,807 transitions in one session at a median life of ELEVEN
    # SECONDS (one chain snapshot). Nothing downstream -- not the screen, not
    # the operator -- can act on a reading that is gone before it can be read.
    #
    # `oi_dir` was the field missing entirely: chain_metrics.oi_flow has
    # computed this divergence all along, but its only consumers were a
    # display table and a passive stamp on trigger rows, so on 2026-08-24 the
    # desk watched CE/PE OI diverge one way for four hours (+1.7M -> +88.7M
    # while spot fell 24299 -> 24150) and never once let it change a decision.
    raw_state = {"gear": getattr(view, "gear", None),
                "conviction": getattr(view, "conviction", None),
                "oi_dir": oi_dwell.direction(doc.get("strikes") or [])[0]}
    # `_DESK_GATE` can only hold a field at a value the desk itself published
    # earlier -- it never invents one -- so the worst case is a reading stale
    # by CONFIRM snapshots, never a fabricated state. What gets logged and
    # published from here on is the GATED state; the raw read is not kept,
    # because two versions of "what the desk thinks" is how the screen and
    # the log start disagreeing.
    new_state = _DESK_GATE.filter(idx, raw_state)
    prev_state = desk_state.get(idx, {})
    is_baseline = not prev_state          # {} only on this index's first
                                           # reading since process start
    for field, frm, to in desk_log.diff_transitions(prev_state, new_state):
        desk_log.log_transition(idx, field, frm, to,
                                detail=f"{idx} {field}: {frm} -> {to}",
                                baseline=is_baseline)
    # `desk_state[idx]` advances to `new_state` even when `log_transition`
    # just refused the write (outside 09:15-15:30 IST, desk_log.py's
    # `market_hours` gate) -- an off-hours change is consumed, not deferred
    # to the next in-hours call. Left as is: the routine daily bounce means
    # the first in-hours reading is a `baseline=True` row anyway (desk_state
    # resets to {} on restart), so there is no accumulated backlog of unlogged
    # transitions to lose, only the (rare) off-hours flip itself.
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
    ring = _SENSES["rows"] = deque(maxlen=2000)
    # THE RING PICKS UP WHERE TODAY LEFT OFF. `senses_mod.Senses` has been
    # writing every one of these rows to data/senses/senses_<day>.jsonl since
    # day one and nothing ever read them back, so a 13:00 start scored every
    # morning visit's DEPTH vote `ok: None` with the answer already on disk --
    # and the ring covers only ~15 minutes of a busy tape even mid-session.
    # Restored rows carry `src: "restored"` and _depth_vote counts them like
    # any other; the seeder streams the file, which at 94-220 MB a day is not
    # optional. Measured on a 100 MB synthetic log: 2.6 MB peak, ~10 s, so the
    # cost of a late start is ten seconds of THIS thread -- it runs after the
    # port is bound and blocks nothing else -- against the whole morning. On a
    # 09:15 start there is no file yet and it costs nothing. Published empty
    # FIRST, so a reader mid-seed sees an empty ring rather than a missing key.
    restored = senses_mod.restore_sweeps(limit=ring.maxlen)
    if restored:
        with _SENSES_LOCK:
            ring.extend(restored)
        log.info("senses: restored %s sweep row(s) from today's log",
                 len(restored))
    _SENSES["started"] = time.time()
    obj = _SENSES["obj"] = senses_mod.Senses()
    book = _SENSES["fuse"] = fuse_mod.Book()
    chains = chain_mod.Chains()
    wboards = _SENSES["warmap"] = warmap_mod.Boards()
    seen_payload = {}          # idx -> id() of the last payload already read
    desk_state = {}            # idx -> {gear, conviction, oi_dir}, 5b's diff base
    last_day_save = 0.0        # the RAM-only day series' last write to disk
    from chain_live import IST, in_session
    from datetime import datetime
    while True:
        t0 = time.perf_counter()
        try:
            src = getattr(poller, "src", None)
            feed = getattr(src, "feed", None)
            feed_ok = feed is not None and feed.connected
            snap = feed.snapshot() if feed_ok else {}
            stamp = time.strftime("%H:%M:%S")
            boxes = getattr(poller, "boxes", None) or {}
            # (idx, doc) pairs due for 5a/5b, queued under the lock below and
            # run AFTER it is released -- see the note past the `with` block.
            chain_pace_due = []
            # Completed VPIN buckets, queued the same way for the same
            # reason: their append touches disk, and disk never runs under
            # _SENSES_LOCK.
            vpin_due = []
            vpin_fast_due = []
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
                        # The backfilled minute grid rides along so a late
                        # start anchors on 09:15's premiums, not this one's
                        # (drag.Board._anchor_from_grid); the war map below
                        # replays the same grid. None until the poller has
                        # a state for this index.
                        _cst = (getattr(poller, "states", None) or {}).get(idx)
                        _grid = getattr(_cst, "minutes", None)
                        board.on_snapshot(doc.get("spot"),
                                          doc.get("strikes"), stamp, grid=_grid)
                        # The day trace, one sample per snapshot. `frac` is
                        # usually None (drag.py refuses to invent a rate) and
                        # None is KEPT -- a gap in the trace is a fact.
                        try:
                            dr = board.read()
                            ring = _SENSES["drag_day"].setdefault(
                                idx, deque(maxlen=3000))
                            ring.append({"t": stamp[:5],
                                         "frac": dr.get("frac"),
                                         "side": dr.get("right_side")})
                        except Exception:
                            pass        # the trace must never stall the tape
                        # THE WAR MAP, same snapshot, same lock. All its
                        # sub-modules are O(strikes + levels) per call --
                        # comparable to chains.on_snapshot above -- and the
                        # ChainSide whose ledgers hunt.py projects from is
                        # mutated only by THIS thread, so feeding here keeps
                        # /api/warmap's read (which takes this same lock)
                        # from ever iterating a half-updated machine dict.
                        try:
                            _wb = wboards.for_index(idx)
                            _wb.on_snapshot(doc, chains.for_index(idx),
                                            grid=_grid)
                            # A restored publish repeats on the poller's 30s
                            # closed-market tick, because _try_seed is a
                            # one-shot that needs the daily levels and the REST
                            # grid first. This is its stop signal: the board
                            # has actually seeded.
                            if (doc.get("mode") == "restored"
                                    and _wb.backfill.get("done")):
                                getattr(poller, "restored_acked", set()).add(idx)
                        except Exception:   # the map must never stall the tape
                            log.exception("warmap at chain pace (%s)", idx)
                        # 5a/5b is queued, NOT run here -- the surface fit is
                        # real work and must not run while this lock is held:
                        # /api/senses and /api/drag both block on the same
                        # `_SENSES_LOCK`, and one slow fit would stall both.
                        # `doc` is a local dict already parsed from this
                        # snapshot, so queuing it costs nothing the lock needs
                        # to protect.
                        chain_pace_due.append((idx, doc))
                        fold_live.push_chain(idx, doc)      # the rev 6 engine's chain row (fold_live.py)

                if feed_ok:
                    # NOTHING IS RECORDED OUTSIDE THE SESSION (operator,
                    # 2026-09-23). The feed runs on to ~15:40 and every recorder
                    # below wrote it down -- ~6 MB of a closed book a day.
                    # A40 (2026-10-23): F&O's session now IS 15:40 -- NIFTY
                    # futures' 1-min candles for 22 Oct run to 15:39 (385 bars,
                    # 36-326 lots a minute after 15:30), so the FEED's recorders
                    # (book, senses legs, VPIN, pools) stop at 15:40. The chain
                    # poller keeps chain_live.in_session's 15:30 (options and
                    # the index spot after 15:30 are not verified).
                    live = _feed_session(datetime.now(IST))
                    # The record's hook: on inside the session, off outside it,
                    # re-set every pass so a reconnect that rebuilds the feed re-hooks.
                    _hook_book(feed, live)
                    for idx, r in (getattr(src, "resolved", None) or {}).items():
                        # The future's key is watched for the book record; a
                        # contract roll changes fut_key and this re-watches it.
                        # Watched even after the close: a restart then rebuilds
                        # the day's ladder and runs from this watched set.
                        _SENSES["book"].watch(idx, r.get("fut_key"), r.get("fut_expiry"))
                        _SENSES["contract"][idx] = {"ik": r.get("fut_key"), "expiry": r.get("fut_expiry"),
                                                    "expired": r.get("fut_expired")}
                        if not live:
                            continue
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
                                # TOXICITY, NIFTY future only -- the one
                                # instrument the bucket size was measured on
                                # (vpin.py docstring). SHADOW: fed, logged,
                                # displayed, read by nothing. ltp and vtt come
                                # from the SAME frame as the ladder, the
                                # discipline ladder_of states.
                                if name == "NIFTY-FUT":
                                    gv = _SENSES["vpin"].get(name)
                                    if gv is None:
                                        gv = _SENSES["vpin"][name] = vpin_mod.Gauge()
                                    for ev in gv.on_frame(
                                            upstox_adapter.ltp_of(frame),
                                            _v, stamp, t_ms=upstox_adapter.ltt_of(frame)):
                                        vpin_due.append(
                                            dict(ev, inst=name,
                                                 day=time.strftime("%Y-%m-%d")))
                                    # THE FAST LINE, same frame, smaller
                                    # bucket. Its own gauge and its own log:
                                    # the two are different populations and
                                    # must never be ranked against each other
                                    # (vpin.FAST_BUCKET_V says why).
                                    gf = _SENSES["vpin"].get(VPIN_FAST_INST)
                                    if gf is None:
                                        gf = _SENSES["vpin"][VPIN_FAST_INST] = \
                                            vpin_mod.Gauge(vpin_mod.FAST_BUCKET_V)
                                    for ev in gf.on_frame(
                                            upstox_adapter.ltp_of(frame),
                                            _v, stamp, t_ms=upstox_adapter.ltt_of(frame)):
                                        vpin_fast_due.append(
                                            dict(ev, inst=VPIN_FAST_INST,
                                                 day=time.strftime("%Y-%m-%d")))
                                if lad:
                                    # No order counts: Upstox does not send them,
                                    # so wall-vs-cluster stays open (pools.py).
                                    _SENSES["pools"][name] = pools_mod.summary(lad, None)
                    _SENSES["polls"] += 1
                    _SENSES["err"] = None
                else:
                    _SENSES["err"] = "feed not connected"

            # 5a/5b, OUTSIDE _SENSES_LOCK. `_view_for` (called inside
            # `_log_chain_pace`) re-acquires the lock itself for its own
            # short read of `_SENSES["fuse"]`/`["chain"]`/`["pools"]`, which
            # is safe -- `_SENSES_LOCK` is an RLock and this thread does not
            # hold it here -- and it never touches `feed._lock`, so the
            # documented order (`_SENSES_LOCK` -> `feed._lock`, never
            # inverted) cannot be crossed from this path. `desk_state`
            # belongs only to this thread (no other thread reads or writes
            # it), so updating it needs no lock either. Own try/except per
            # index so a bad fit on ONE index cannot cost the others their
            # chain-pace log.
            # THE BOOK RECORD'S DRAIN AND THE LADDER, outside the lock with the
            # other writers (spec 2 §B, §E).
            _SENSES["book_rows"] = _ux_drain(time.strftime("%Y-%m-%d"))
            fold_live.push_book(_SENSES["book_rows"])      # the rev 6 engine's book rows, the ones just written

            # The toxicity record, outside the lock with the other writers.
            # Fail-soft: a full disk costs the row, never the tape.
            if vpin_due:
                try:
                    with open(VPIN_LOG, "a", encoding="utf-8") as fh:
                        for ev in vpin_due:
                            fh.write(json.dumps(ev) + "\n")
                except OSError:
                    log.exception("vpin log append")
            # The fast line's record, its own file, its own try: a failure on
            # the display line must never cost the promotion record a row.
            if vpin_fast_due:
                try:
                    with open(VPIN_FAST_LOG, "a", encoding="utf-8") as fh:
                        for ev in vpin_fast_due:
                            fh.write(json.dumps(ev) + "\n")
                except OSError:
                    log.exception("vpin fast log append")
                fold_live.push("NIFTY", "vpin", vpin_fast_due)      # the rev 6 engine's VPIN row (NIFTY-FUT:fast)
            # THE DAY'S RAM-ONLY SERIES, written down so a post-close restart
            # does not blank the screen ("abhi to ui he khali ho jaata"). Out
            # here with the other disk writers, never under _SENSES_LOCK.
            # Unconditional on market hours ON PURPOSE, unlike desk_log and
            # sequence: those are forward RECORDS and a row outside the session
            # would corrupt one, while this is a snapshot of state that is
            # already what it is -- and 15:35 is exactly when it most needs to
            # be on disk.
            if time.time() - last_day_save >= DAY_STATE_EVERY_S:
                last_day_save = time.time()
                _save_day_state()
            for idx, doc in chain_pace_due:
                try:
                    _log_chain_pace(poller, payloads, idx, doc, desk_state)
                except Exception:
                    log.exception("desk_log at chain pace (%s)", idx)
        except Exception as e:            # never take the tape down
            _SENSES["err"] = f"{type(e).__name__}: {e}"
            log.exception("senses loop")
            # Recorded BEFORE the backoff sleep, not in a shared `finally` --
            # otherwise the 2s fault-recovery sleep below bleeds into
            # senses_ms and a faulting loop reads as merely a slow one.
            _record_latency("senses_ms", (time.perf_counter() - t0) * 1000.0)
            time.sleep(2)                 # extra backoff on a sustained fault
        else:
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


def _session_payload(box, interval):
    """/api/data's bytes: `payload_at`'s, minus everything stamped at or after
    the close (DEFERRED 0j.8 follow-up 3 -- it served 15:30/15:35 FUT bars to
    every tab). The session's 1-minute bars and events are cut at
    SESSION_END_HHMM and the payload is DERIVED again from what is left, so
    every layer that is 1:1 with the bars (rotation, run_state, zone_state,
    structures) is computed on the session alone -- the rule `_session_only`
    applies to the extension's POST, here applied where /api/data is served.

    SERVED ONLY. `payload_at` itself is untouched, so trigger_log, the frame's
    book and /api/calls read exactly what they read before. Cached per build
    per interval like `payload_at`; a session with nothing past the close
    serves `payload_at`'s own bytes, with no second derive.
    """
    base = box.get("session") if isinstance(box, dict) else None
    day = (base or {}).get("day") or {}
    ones = day.get("bars") or []
    if not ones or str((ones[-1] or {}).get("t")) < SESSION_END_HHMM:
        return payload_at(box, interval)
    cache = box.setdefault("served", {})
    hit = cache.get(interval)
    if hit is not None and hit[0] == box.get("stamp"):
        return hit[1]
    from live import derive_payload
    cut = dict(base, day=dict(day, bars=[b for b in ones if str(b.get("t")) < SESSION_END_HHMM],
                              events=[e for e in day.get("events") or []
                                      if str(e.get("t")) < SESSION_END_HHMM]))
    out = derive_payload(cut, interval)
    cache[interval] = (box.get("stamp"), out)
    return out


def _book_for(handler, idx):
    """Everything the frame composes from, gathered under the lock. Each
    field is None when its module has not answered; frame.py turns None into
    that block's own PATA NAHI. Nothing is computed here.

    `vpin_pct` reads the gauge through `Gauge.state()["pct"]` -- vpin.py has
    no bare `.pct` attribute, only that reading method (server.py's own
    /api/vpin and /api/senses handlers read it the same way). `senses` is
    passed as None: the per-instrument reading a `Senses` object could offer
    is not an attribute of it either -- it is assembled in the GET
    /api/senses handler from `_SENSES["fuse"]` plus `_regime_engine_read`/
    `_walls_holding`, which this composer must not re-derive.

    zone_state/zone_state_sell live under the payload's days[0], not at top
    level (live.derive_payload).
    """
    with _SENSES_LOCK:
        wb = _SENSES.get("warmap")
        wm = wb.for_index(idx).state() if wb else None
        ct = dict((_SENSES.get("contract") or {}).get(idx) or {})
        g = (_SENSES.get("vpin") or {}).get(f"{idx}-FUT")
        vpin_pct = g.state().get("pct") if g else None
        senses = None
        # THE DEPTH VOTE'S ONLY INPUT (spec §A.4). `senses` stays None above
        # for the reason this function's docstring gives -- the /api/senses
        # READING is assembled in that handler and must not be re-derived
        # here. The vote never wanted the reading; it wants the raw sweep
        # rows, which are the ring filtered by instrument and nothing more.
        # Until this key existed the DEPTH vote was structurally unmeasurable.
        sweeps = [r for r in (_SENSES.get("rows") or ())
                  if r.get("inst") == f"{idx}-FUT" and r.get("det") == "sweep"]
        # The previous frame's watch list, so a level that broke this morning
        # is still on screen this afternoon. watch.py is pure; the memory
        # lives here, in the object this process already keeps.
        watch_prior = (((_SENSES.get("frame") or {}).get(idx) or {})
                       .get("walls") or {}).get("watch")
        # ...and the previous frame's signal, so the fade gate read AT the tap and
        # AT the trigger is FROZEN for the visit (frame.build). Recomputed each
        # frame, a past bar's gate re-read with later plays/peaks could turn a
        # vetoed trigger legal twenty minutes on and ring a late firm beep.
        signal_prior = ((((_SENSES.get("frame") or {}).get(idx) or {})
                         .get("setup") or {}).get("signal"))
    st = (getattr(handler.poller, "states", None) or {}).get(idx) if handler.poller else None
    box = handler.chains.get(idx) if handler.chains else None
    pj = {}
    try:
        pl = payload_at(handler.payloads.get(idx), band_rotation.SCORED_INTERVAL) if handler.payloads else None
        pj = json.loads(pl) if isinstance(pl, (bytes, str)) else (pl or {})
    except Exception:
        pj = {}
    _day0 = (pj.get("days") or [{}])[0] if isinstance(pj, dict) else {}
    # The engine's OWN regime, off the last published bar's ctx (engine.py:1200
    # writes `pin.regime`; contract_bars.resample_index carries `ctx` through
    # the 3-minute fold). Two named facts, not the STRONG BULL / STRONG BEAR
    # verdict beside them -- that verdict is not ported at any size (spec §C.1).
    regime = None
    plays = None
    plays_at = {}
    try:
        _bars = _day0.get("bars") or []
        _ctx = _bars[-1].get("ctx") or {}
        regime = (_ctx.get("pin") or {}).get("regime")
        # THE ENGINE'S OWN VETO, carried so the fade gate can obey it
        # (research-findings §1d). On 2026-09-22 the engine printed "NO FADE at
        # 23360 -- negative gamma; continuation only" at 11:45 and 13:51 while
        # the zone machine armed a BUY fade in the same minute, verdict GO. The
        # sentence already existed; nothing read it. Strings only -- `fronts`
        # matches on the prefix and never parses a price back out of them.
        # An EMPTY list is the engine read and printing no play -- no veto. Only a
        # missing ctx is "not read" (None), and fronts.fade_gate treats those two
        # differently: the first can be legal, the second is PATA NAHI.
        _pl = _ctx.get("plays")
        plays = [p for p in _pl if isinstance(p, str)] if isinstance(_pl, list) else None
        # EVERY BAR'S OWN PLAYS, by its 3-min label -- the same ctx trigger_log
        # stamps each row's gate from. frame.build reads a tap's/trigger's gate
        # with THAT bar's veto, so the answer is a function of the bar alone: it
        # survives a restart and cannot turn a vetoed trigger legal once the
        # veto has aged out of the latest bar.
        plays_at = {}
        for _b in _bars:
            _bp = ((_b or {}).get("ctx") or {}).get("plays")
            if isinstance((_b or {}).get("t"), str) and isinstance(_bp, list):
                plays_at[_b["t"]] = [p for p in _bp if isinstance(p, str)]
    except (AttributeError, IndexError, TypeError):
        regime, plays, plays_at = None, None, {}
    return {"warmap": wm, "minutes": getattr(st, "minutes", None),
            "peaks": getattr(st, "peak", None), "plays": plays,
            "spot": box.get("spot") if box else None,
            "expiry": (box or {}).get("expiry") or (pj.get("expiry") if isinstance(pj, dict) else None),
            "zone_state": _day0.get("zone_state"), "zone_state_sell": _day0.get("zone_state_sell"),
            # ONE BASIS: the fold engine's display basis (future minus the index, 3-min median of paired samples (A60), her
            # word 2026-10-05), so a strike's OI row and her W / A lines sit at one height; None until the engine has one.
            "basis": fold_live.basis(idx),
            "pivots": _day0.get("pivots"),      # the prior session's floor pivots; frame._walls inverts them to PDH/PDL/PDC
            "vpin_pct": vpin_pct, "senses": senses, "sweeps": sweeps,
            "watch_prior": watch_prior, "signal_prior": signal_prior, "plays_at": plays_at,
            "regime": regime, "pinned": None if regime is None else regime == "PINNED",
            "ivrv": None, "coverage": _coverage(),
            # the watched future's expiry (P1-02) and the last UX_OI_N Upstox ladder bars' {t, oi}
            # (P1-05): the extension's contract match needs an OI that is not GoCharting's own
            "fut_expiry": ct.get("expiry"),
            "ux_oi": [{"t": b["t"], "oi": b.get("oi")} for b in _ux_bars(idx, time.strftime("%Y-%m-%d"))[-UX_OI_N:]
                      if tape_log.bar_t(b) is not None]}


TAPE_LIVE_S = 15      # the extension's own FRAME_STALE_MS boundary (orderflow-desk main.js:53)
UX_OI_N = 24          # Upstox ladder bars {t, oi} carried on the frame for the contract match (P1-05)
_FRAME_DOOR = {"seen": 0}   # first frame POSTs logged with their headers (P1-07)
_LADDER_WHY = "extension predates ladders (orderflow-desk < 0.3.1)"
_NO_FLAGS = {"stacks": None, "unfinished_high": None, "unfinished_low": None, "poc": None}


def _ofd_lot(idx, day):
    """GoCharting's lot for `idx` on `day` -- the spec's second fallback, before
    gcd (dump first, §B/§J.12): the live extension doc's `lot` while it is
    posting, else the record's first bar's `lot`, else None."""
    doc = (_SENSES["tape"].get(idx) or {}).get("doc") or {}
    lot = doc.get("lot")
    if lot:
        return lot
    bars = tape_log.read_bars(day, idx)
    return bars[0].get("lot") if bars else None


# F&O trades 09:15-15:30 IST; nothing after the close is session (operator,
# 2026-09-23: "the app should show the last snapshot and not build anything
# after that"). The same clock the chain poller stops on.
SESSION_END_HHMM = "15:30"


def _session_only(doc: dict) -> dict:
    """The extension's POST without anything stamped at or after the close.

    GoCharting keeps drawing bars after 15:30, and each one reached the frame
    build, the frame record, the ladder file and the scorer -- 81 frame rows
    and 2.5 MB after the close on 2026-09-23. Trimmed here, the frame after the
    close IS the last session snapshot. An item with no `t` is kept."""
    def session(x):
        t = x.get("t") if isinstance(x, dict) else None
        return t is None or frame._hhmm(int(t)) < SESSION_END_HHMM
    fm = doc.get("forming")
    return {**doc, "closed": [b for b in doc.get("closed") or [] if session(b)],
            "events": [e for e in doc.get("events") or [] if session(e)],
            "forming": fm if isinstance(fm, dict) and session(fm) else None}


FEED_CLOSE_S = 15 * 3600 + 40 * 60   # A40: the futures feed's recorders run to 15:40 (F&O's session since 3 Aug 2026)


def _feed_session(now) -> bool:
    """chain_live.in_session's weekday 09:15 open, with the F&O close of 15:40 (A40) instead of 15:30."""
    import chain_live
    return now.weekday() < 5 and chain_live.SESS_OPEN <= now.hour * 3600 + now.minute * 60 + now.second <= FEED_CLOSE_S


def _hook_book(feed, live: bool) -> None:
    """The book record's feed hook: on inside the session, off outside it.
    Re-set every pass, so a reconnect that rebuilds the feed re-hooks."""
    if not live:
        feed.on_frame = None
    elif getattr(feed, "on_frame", None) is None:
        feed.on_frame = _SENSES["book"].on_frame


def _ux_meta(idx):
    """lot/tick for the index once per process, and its runs/impact machines.
    (None, None) when the cached slice predates the fields or cannot be read --
    ladder.py then infers and the row says `lot_src: "gcd"`."""
    st = _SENSES["ux"].get(idx)
    if st is None:
        try:
            lot, tick = upstox_instruments.lot_tick(idx)
        except Exception:                      # noqa: BLE001 -- no dump is not a reason to stop recording
            lot, tick = None, None
        st = _SENSES["ux"][idx] = {"lot": lot, "tick": tick, "day": None, "rebuild_why": None,
                                    "runs": runs_mod.Runs(lot=lot),
                                    "impact": impact_mod.Impact(lot=lot, tick=tick)}
    return st


def _ux_observe(idx, row, fills):
    """ux_log's per-row observer: every fill to the run detector, every frame to the gauge."""
    st = _ux_meta(idx)
    for f in fills:
        st["runs"].on_fill(f)
    st["impact"].on_frame(row, fills)


def _ux_drain(day: str) -> list:
    """The book record's drain and the ladder step, once a pass (spec 2 §B,
    §E). Order matters: on the first pass of a day (or a late start) the
    ladder is REBUILT from the book file BEFORE this pass's rows are written,
    so nothing is stepped twice. Returns the rows flushed -- [] on a disk
    fault too, which costs the rows, never the tape."""
    try:
        for idx in _SENSES["book"].watched():
            st = _ux_meta(idx)
            if st["day"] != day:
                # a failed rebuild must not be retried every 0.5 s (a 60 MB
                # re-read twice a second), so st["day"] is set in `finally`
                # either way -- but a failure NAMES itself on `rebuild_why`
                # instead of silently looking like a fresh, empty day. `runs`/
                # `impact` are reset BEFORE the rebuild feeds them, and again in
                # `except`, so a raise inside `_ofd_lot` cannot leave yesterday's
                # machines in place for today. (Until 2026-09-23 the reset sat in
                # `finally`, AFTER the rebuild, and threw every rebuilt run away.)
                # `ux_drain_why`/`ux_drain_failed` are process-wide, not
                # per-index, but a day roll is the one event that legitimately
                # retires yesterday's sticky failure -- a new day gets a clean
                # wire to complain about.
                _SENSES["ux_drain_why"] = None
                _SENSES["ux_drain_failed"] = 0
                lot = None
                try:
                    # dump (upstox_instruments, resolved in _ux_meta) first,
                    # GoCharting's own lot for the same index/day second, the
                    # gcd last (ladder infers when `lot` is still None) --
                    # spec §B/§J.12, and the row says which.
                    lot = st["lot"] if st["lot"] else _ofd_lot(idx, day)
                    lot_src = "dump" if st["lot"] else ("ofd" if lot else None)
                    # fresh machines BEFORE the rebuild feeds them through _ux_observe --
                    # a reset after it threw every rebuilt run away (2026-09-23)
                    st["runs"] = runs_mod.Runs(lot=lot)
                    st["impact"] = impact_mod.Impact(lot=lot, tick=st["tick"])
                    ux_log.state(idx, day, lot, st["tick"], lot_src=lot_src)
                    n_re = ux_log.rebuild(day, idx, lot, st["tick"], lot_src=lot_src, observer=_ux_observe,
                                          close_last=False)
                    if n_re:
                        log.info("ux: rebuilt %s bar(s) for %s from today's book record", n_re, idx)
                    st["rebuild_why"] = None
                except Exception as e:
                    st["rebuild_why"] = f"rebuild failed: {type(e).__name__}: {e}"
                    st["runs"] = runs_mod.Runs(lot=lot)      # never yesterday's, never half-fed
                    st["impact"] = impact_mod.Impact(lot=lot, tick=st["tick"])
                    log.exception("ux rebuild for %s", idx)
                finally:
                    st["day"] = day
    except Exception:                   # a disk fault costs the rows, never the tape
        log.exception("ux drain")
        return []
    try:
        rows = _SENSES["book"].flush(day)
        if rows:
            ux_log.on_frames(rows, day, observer=_ux_observe)
        return rows
    except Exception as e:               # named on ux_drain_why, never raised past here
        if _SENSES["ux_drain_why"] is None:            # sticky: the FIRST failure is kept
            _SENSES["ux_drain_why"] = f"drain failed at {time.strftime('%H:%M:%S')}: {type(e).__name__}: {e}"
        _SENSES["ux_drain_failed"] += 1
        log.exception("ux drain")
        return []


def _ux_bars(idx, day):
    st = ux_log._STATE.get(idx)
    if st is not None and st["day"] == day:
        return list(st["bars"])
    return ux_log.read_bars(day, idx)


def _feed_read(idx, day):
    """The GoCharting tape's health (feed_health.py) with Upstox lots per closed bin for the volume check.
    Fail-soft: a failure anywhere here is a why on the wire, never a 500 and never at the frame's expense."""
    try:
        ux = {int(b["t"]): b.get("vol") for b in _ux_bars(idx, day)
              if isinstance(b, dict) and isinstance(b.get("t"), (int, float))}
    except Exception:
        ux = None
    return feed_health.read(idx, ux_vols=ux or None)


_UX_KEEP = ("t", "o", "h", "l", "c", "vol", "buy", "sell", "unknown", "unpriced", "delta", "cvd", "oi",
            "exact", "reconstructed", "hidden", "late_frames", "partial", "partial_why", "feed_gaps", "gap_vol")


def _ux_reply(idx, day, row, anchor, ofd_raw):
    """The ux object (spec §E): bars, levels, runs, impact, agreement -- three sentences each."""
    bars_raw = [b for b in _ux_bars(idx, day) if tape_log.bar_t(b) is not None]
    book = _SENSES["book"]
    book_from = book.book_from.get(idx)
    st = _SENSES["ux"].get(idx) or {}
    rebuild_why = st.get("rebuild_why")
    out = {"src": "ux", "tag": "I", "bars": [], "forming": None,
           "levels": {"session": None, "nodes": [], "why": None},
           "marks": {"runs": [], "runs_why": None}, "impact": None,
           "agree": None, "agree_why": None, "book_from": book_from, "frames_per_s": None,
           "lot": st.get("lot"), "lot_src": None, "lot_why": None, "rebuild_why": rebuild_why, "why": None}
    if not bars_raw:
        if book_from is None and not daylog.exists(book_log.day_path(day, idx)):
            why = (f"no book record for {idx} on {day} — the server was not recording "
                   f"(book_log predates it, or the feed never connected)")
        elif rebuild_why:
            why = f"book record from {book_from or 'file'}, {rebuild_why}"
        else:
            why = f"book record from {book_from or 'file'}, no bar closed yet"
        out["why"] = out["levels"]["why"] = out["agree_why"] = out["marks"]["runs_why"] = why
        return out
    for b in prints.with_cvd(bars_raw):
        f = prints.bar_flags(b, row, anchor)
        out["bars"].append({**{k: b.get(k) for k in _UX_KEEP}, **(f or _NO_FLAGS)})
    fm = ux_log.forming(idx, day)
    if fm is not None:
        out["forming"] = {**{k: fm.get(k) for k in _UX_KEEP}, **(prints.bar_flags(fm, row, anchor) or _NO_FLAGS)}
    prof = prints.profile(gate_mod.rebinned(bars_raw, row, anchor))
    out["levels"] = {"session": ({"poc": prof["poc"], "vah": prof["vah"], "val": prof["val"]} if prof else None),
                     "nodes": prints.nodes(prof), "why": None if prof else "no ux bar with a ladder yet"}
    out["lot"], out["lot_src"] = bars_raw[-1].get("lot"), bars_raw[-1].get("lot_src")
    if out["lot_src"] == "gcd":
        out["lot_why"] = "lot inferred by gcd -- vol_ratio is not yet a measurement of the feed"
    elif out["lot"] is None:
        # the bar's own reason (ladder._resolve's "no traded volume yet to
        # infer a lot from") -- a lotless day is not the gcd day, and must
        # not borrow its sentence.
        out["lot_why"] = bars_raw[-1].get("lot_why")
    else:
        out["lot_why"] = None
    # a day can cross a dump outage, a GoCharting-only stretch and a rebuild
    # all in one file: the LAST bar's lot_src (served above) hides that the
    # earlier bars were resolved a different way -- and different sources can
    # disagree, so the bars are not provably one unit. This is worse than the
    # gcd sentence (a known, consistent fallback), so it overrides it.
    srcs = {b.get("lot_src") for b in bars_raw}
    if len(srcs) > 1:
        out["lot_why"] = ("mixed lot provenance across the day's bars: " + ", ".join(sorted(str(s) for s in srcs))
                          + " — the bars are not in one unit")
    frames = sum(b.get("frames") or 0 for b in bars_raw)
    out["frames_per_s"] = round(frames / (300.0 * len(bars_raw)), 2)
    r = st.get("runs")
    out["marks"] = {"runs": [dict(e) for e in r.events] if r else [],
                    "runs_why": r.why() if r else "no fill has reached the run detector yet this process"}
    im = st.get("impact")
    out["impact"] = im.read() if im else {"lambda": None, "lots_per_tick": None, "pct": None, "n": 0,
                                          "why": "no frame has reached the impact gauge yet this process", "tag": "I"}
    if not ofd_raw:
        out["agree_why"] = "GoCharting record absent for this day — ux stands alone, flags on the default grid"
    else:
        ag = gate_mod.session(ofd_raw, bars_raw, row, anchor)
        if ag["bars_joined"] == 0:
            out["agree_why"] = "no GoCharting bar shares a t with any ux bar — nothing to compare"
        else:
            out["agree"] = ag
    return out


def _tape_reply(idx: str, day: str) -> dict:
    """GET /api/tape: bars + levels + two mark families, three sentences (spec §D)."""
    with _SENSES_LOCK:
        held = _SENSES["tape"].get(idx)
    doc = (held or {}).get("doc") or {}
    live = bool(held) and str(doc.get("session", "")).endswith(day) and (time.time() - held["at"]) < TAPE_LIVE_S
    if live:
        raw, forming = list(doc.get("closed") or []), doc.get("forming")
        # the extension's marks as posted, in the SAME shape tape_log writes them, so the
        # two sources are one population on the wire (src is stamped here for the live path)
        ofd = [{"t": m.get("t"), "kind": m.get("kind"), "side": m.get("side"), "p": m.get("p"),
                "size": m.get("size"), "src": "ofd", "idx": idx, "day": day}
               for m in (doc.get("events") or [])
               if tape_log.keep_mark(m)]
        meta = {"rowSize": doc.get("rowSize"), "rowAnchor": doc.get("rowAnchor", 0), "lot": doc.get("lot")}
        forming_why = None
    else:
        raw = tape_log.read_bars(day, idx)
        if not raw and not _ux_bars(idx, day) and not daylog.exists(book_log.day_path(day, idx)) \
                and idx not in _SENSES["book"].book_from:
            return {"ok": False, "idx": idx, "day": day, "src": None,
                    "why": f"no prints record for {idx} on {day} — GoCharting was on another index, or the extension never posted"}
        forming, ofd = None, tape_log.read_marks(day, idx)
        # no GoCharting record but a ux one: the extension's defaults (rowSize 5,
        # anchor 0), and levels.why says the grid was assumed (spec 2 §E)
        meta = ({"rowSize": raw[0].get("rowSize"), "rowAnchor": raw[0].get("rowAnchor", 0), "lot": raw[0].get("lot")}
                if raw else {"rowSize": 5, "rowAnchor": 0, "lot": None})
        forming_why = (f"extension not posting for {int(time.time() - held['at'])}s — showing the record" if held
                       else "extension not posting since server start — showing the record")
    row, anchor = float(meta["rowSize"] or 5), float(meta["rowAnchor"] or 0)
    # the SAME filter the writer applies (tape_log.bar_t): a non-dict entry or a
    # `t` that is not a number is skipped here too, so a corrupt POST or a
    # corrupt record row costs one bar and not the whole reply.
    raw = [b for b in raw if tape_log.bar_t(b) is not None]
    bars = []
    for b in prints.with_cvd(raw):
        f = prints.bar_flags(b, row, anchor)
        # the ladder is NOT served (spec §D, amended at the final review): it was
        # 81 % of the reply's bytes and nothing on the wire read it. It stays in
        # the record, which is its point.
        bars.append({**{k: b.get(k) for k in ("t", "o", "h", "l", "c", "vol", "buy", "sell", "delta", "cvd", "oi", "fromTicks")},
                     **(f or _NO_FLAGS)})
    # falsy, not `is None`: extension 0.3.1 posts `[]` for a bar it has no ladder for
    ladder_why = _LADDER_WHY if any(not b.get("ladder") for b in raw) else None
    if forming is not None:
        forming = {**{k: v for k, v in forming.items() if k != "ladder"},
                   **(prints.bar_flags(forming, row, anchor) or _NO_FLAGS)}
    prof = prints.profile(raw)
    # THE ROLL (P1-03): a prior day on or before the expired front future's expiry is another
    # contract's prices, off by the calendar spread; a day whose ux record names another
    # contract, or none, is dropped the same way. `cut_why` says so when nothing is left.
    ct = (_SENSES.get("contract") or {}).get(idx) or {}
    pool, cut_why = tape_log.prior_pool(day, idx, 5, after=ct.get("expired"), ik=ct.get("ik"))
    prior_days = [(d, tape_log.read_bars(d, idx)) for d in pool]
    prior = prints.prior_levels(prior_days)
    tm, tm_why = prints.tm_marks(raw)
    # rule 6: three facts, three sentences. Live has no marks file to check --
    # the extension just hasn't detected anything yet today. File-branch keeps
    # "no file" (seeded from an export, which carries none) apart from
    # "file exists but the extension found nothing on this day".
    if ofd:
        ofd_why = None
    elif live:
        ofd_why = "the extension has detected nothing yet today"
    elif not os.path.exists(tape_log.marks_path(day, idx)):
        ofd_why = f"no marks file for {idx} on {day} — the record was seeded from an export, which carries none"
    else:
        ofd_why = "the extension detected nothing on this day"
    return {
        "ok": True, "idx": idx, "day": day, "interval": 5, "src": "live" if live else "file", "tag": "M", **meta,
        "bars": bars, "forming": forming, "forming_why": forming_why, "ladder_why": ladder_why,
        "levels": {"session": ({"poc": prof["poc"], "vah": prof["vah"], "val": prof["val"]} if prof else None),
                   "prior": prior, "prior_why": None if prior else cut_why or "no earlier day in the record yet",
                   "naked": prints.naked(prior_days, raw), "nodes": prints.nodes(prof), "tag": "M",
                   "why": (f"no GoCharting record for {idx} on {day} — ux stands alone" if not raw
                           else None if prof else "no bar with a ladder yet")},
        "marks": {"ofd": ofd, "ofd_why": ofd_why, "tm": tm, "tm_why": tm_why},
        "ux": _ux_reply(idx, day, row, anchor, raw),
        "why": None,
    }


def _roll_why(idx, day):
    """P1-02: the sentence that blinds the near future's OI read in its expiry week, or None
    -- grounds.roll_why on the watched contract's own expiry."""
    return grounds.roll_why(day, ((_SENSES.get("contract") or {}).get(idx) or {}).get("expiry"))


def _calls_for(payloads, poller, idx: str) -> dict:
    """/api/calls's reply, shared with calls_log so the row kept is what the
    face was served. May raise; the route turns that into its own reply."""
    box = (payloads or {}).get(idx)
    pl = payload_at(box, band_rotation.SCORED_INTERVAL) if box else None
    pj = json.loads(pl) if isinstance(pl, (bytes, str)) else (pl or {})
    bars = ((pj.get("days") or [{}])[0] or {}).get("bars") or []
    last = bars[-1] if bars else {}
    ux = (_tape_reply(idx, time.strftime("%Y-%m-%d")) or {}).get("ux") or {}
    st = (getattr(poller, "states", None) or {}).get(idx) if poller else None
    fr = fronts.read(getattr(st, "minutes", None) or {}, getattr(st, "peak", None))
    return {"ok": bool(last), "idx": idx, "t": last.get("t"),
            "why": None if last else "no engine bar for this index yet",
            **grounds.ground(last.get("ctx") or {}, (last.get("fut") or {}).get("c"),
                             ux.get("bars"), (ux.get("marks") or {}).get("runs"), fr,
                             runs_why=(ux.get("marks") or {}).get("runs_why"),
                             roll=_roll_why(idx, time.strftime("%Y-%m-%d")), idx=idx)}


_DAYTYPE = {}       # idx -> (key, reply): one read per index per closed 5-min bar
_IBREF = {}         # (idx, day) -> the prior 5 sessions' median initial balance: daytype's SIZE yardstick, once a day


def _ib_ref(idx, day):
    if (idx, day) not in _IBREF:
        pre = f"ux_{idx}_"
        try:
            days = sorted({n[len(pre):len(pre) + 10] for n in os.listdir(tape_log.DIR) if n.startswith(pre)})
        except OSError:
            days = []
        v = [daytype.ib_of(daytype._bars(ux_log.read_bars(d, idx))) for d in [d for d in days if d < day][-5:]]
        v = sorted(x for x in v if x)
        _IBREF[(idx, day)] = (v[len(v) // 2] + v[(len(v) - 1) // 2]) / 2 if v else None
    return _IBREF[(idx, day)]


def _trap_logged(idx, day):
    """The trap layer's state stamps for idx as they were written live (data/trap/trap_<day>.jsonl), oldest first; []
    when there is no log."""
    out = []
    try:
        with daylog.open_text(os.path.join(trap_log.DIR, f"trap_{day}.jsonl")) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("idx") == idx and r.get("kind") == "state":
                    out.append(r)
    except OSError:
        return []
    return sorted(out, key=lambda r: str(r.get("t") or ""))


def _daytype_reply(poller, idx):
    """AAJ KA DIN (daytype.py) for the answer band, riding on /api/calls. Rebuilt whole from today's ux bars, the
    chain grid and the sides slots each time a 5-min bar closes (so it is the same whenever the server started),
    a dict lookup in between. Display only."""
    day, hm = _board_clock()
    now = board.mm(hm)
    bars = _ux_bars(idx, day)
    n = sum(1 for b in bars if isinstance(b.get("t"), (int, float)) and board.mm(grounds._hh(b["t"])) + 5 <= now)
    st = (getattr(poller, "states", None) or {}).get(idx) if poller else None
    mins = dict(getattr(st, "minutes", None) or {})
    tr = ((_TRAP.get("reply") or {}).get("indices") or {}).get(idx) or {}     # the trap layer's stamps (its FAILs end a trend)
    rev = [e for e in tr.get("events") or () if e.get("kind") == "state"] if tr.get("ok") and tr.get("day") == day else []
    # What the trap layer SAID live is its forward log; a restart's backfill re-derives the morning from the minute grid and
    # can miss a fail it called on ticks (5 Oct: 12:18 "FAIL · PDC" gone after the 17:01 restart). Log first, then only
    # the live stamps since; the backfill alone only when nothing was logged (a late start).
    logged = _trap_logged(idx, day)
    tev = (logged + [e for e in rev if e.get("src") == "live" and e.get("t", "") > (logged[-1].get("t") or "")]
           if logged else rev or None)
    key = (day, n, len(mins) > 0, None if tev is None else len(tev))   # a warming grid / trap read is not kept
    hit = _DAYTYPE.get(idx)
    if hit and hit[0] == key:
        return hit[1]
    sd = _sides_reply(poller, getattr(poller, "boxes", None), idx)["indices"].get(idx) or {}
    out = daytype.read(idx, day, bars, now, mins, _board_opens(poller, idx),
                       sd.get("dte"), sd.get("slots") if sd.get("ok") else None,
                       {k: _ux_bars(k, day) for k in instruments.ENABLED if k != idx}, tev, _ib_ref(idx, day))
    _DAYTYPE[idx] = (key, out)
    return out


# ---- THE READ (read.py; docs/review/DAY-TEST-2026-10-08.md) ----
#
# One HELD read per index: the word, the FLIP line, the targets, what would make it wrong, and the trade. Computed
# whole from the day files v2feed already tails (so a restart at any hour gives the same marks), cached per change of
# those files and of the 5-min mark. Every closed mark is kept once in data/read/read_<day>.jsonl, market hours only
# (the one gate, _market_hours). DISPLAY ONLY: nothing here feeds the engine, the zone machine, the fade gate or
# trigger_log.
_READ = {"cache": {}, "seen": {}}
_READ_LOCK = threading.Lock()
READ_DIR = os.path.join("data", "read")
_READ_LOG_GRACE = 60      # A16: a mark is logged a minute after its close, once its 5-min bar has landed (decode's grace)
# READ-2's JAGAH (docs/read/READ-2-PREREG.md): the extension's last-push origins, from POST /api/frame's optional `push`,
# the latest per index, memory only -- an obstacle candidate on the live card alone (read.card), never in a row.
_PUSH = {}


def _push_clean(p):
    """The frame's `push` -> {"down", "up"}, each {t: epoch ms, px: futures price, rank: int, failed: bool} or None;
    None when it is not that shape (one malformed side refuses the whole push). Never raises."""
    if not isinstance(p, dict):
        return None

    def num(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
    out = {}
    for k in ("down", "up"):
        x = p.get(k)
        if x is None:
            out[k] = None
        elif (isinstance(x, dict) and num(x.get("t")) and x["t"] > 0 and num(x.get("px")) and x["px"] > 0
              and num(x.get("rank")) and isinstance(x.get("failed"), bool)):
            out[k] = {"t": int(x["t"]), "px": float(x["px"]), "rank": int(round(x["rank"])), "failed": x["failed"]}
        else:
            return None
    return out


def _push_for(idx, day):
    """The latest push the extension sent for (idx, day), or None."""
    hit = _PUSH.get(idx)
    return hit["push"] if hit and hit.get("day") == day else None


def _read_levels(idx):
    """PDH / PDL / PDC (index prices) off the war map's daily candles, memory only; None until they land."""
    lv = _board_levels(idx) or []
    return {x["kind"]: x["px"] for x in lv if x.get("kind") in ("PDH", "PDL", "PDC")} or None


def _read_expr(idx, day, d):
    """expression.py's latest word for direction d -- the hold window's own read, never recomputed here."""
    C = (_HOLD.get("expr") or {}).get(idx)
    if not d or not C or C.get("day") != day:
        return None
    ks = [k for k, e in C["reads"].items() if k[1] == d and (e or {}).get("word")]
    if not ks:
        return None
    k = max(ks)
    return {"word": C["reads"][k]["word"], "t": k[0], "d": d, "tag": "I"}


def _read_log(day, idx, tl, now=None):
    """Each closed mark once per (day, idx, t), and each event once: the forward record the read is judged on.
    `now` (live, sec of day): a mark or event at T waits until T + _READ_LOG_GRACE, when T's 5-min bar has landed --
    A16, 21 Oct NIFTY 10:05 was logged RANGE before the 10:00 bar closed, and the day replays LEAN. None = no wait."""
    os.makedirs(READ_DIR, exist_ok=True)
    path = os.path.join(READ_DIR, f"read_{day}.jsonl")
    seen = _READ["seen"].get(day)
    if seen is None:
        seen = set()
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    seen.add((r.get("idx"), r.get("kind"), r.get("t"), r.get("text")))
        except FileNotFoundError:
            pass
        _READ["seen"] = {day: seen}
    out = []
    early = lambda t: now is not None and int(t[:2]) * 3600 + int(t[3:5]) * 60 + _READ_LOG_GRACE > now  # noqa: E731
    for r in tl["rows"]:
        key = (idx, "mark", r["t"], None)
        if key not in seen and not early(r["t"]):
            seen.add(key)
            out.append({"day": day, "idx": idx, "kind": "mark", "t": r["t"], "word": r["word"], "dir": r["dir"],
                        "since": r["since"], "agree": r["agree"], "spot": r["spot"], "flip": r["flip"],
                        "targets": [x["k"] for x in r["targets"]], "box": r["box"], "warn": r["warn"],
                        "writers": r["writers"], "price": r["price"].get("word"), "flow": r["flow"].get("cvd"),
                        # READ-2: read-1.1's word beside READ-2's, and the two new votes and JAGAH as the row had them
                        "word_r1": r.get("word_r1"), "src": r.get("src"), "fuel": r.get("fuel"),
                        "fuel_leg": r.get("fuel_leg"), "legflow": r.get("legflow"), "jagah": r.get("jagah"),
                        "rev": read.REV, "tag": "I"})
    for e in tl["events"]:
        key = (idx, "event", e["t"], e["text"])
        if key not in seen and not early(e["t"]):
            seen.add(key)
            out.append(dict(e, day=day, idx=idx, kind="event", event=e["kind"], rev=read.REV))
    if out:
        with open(path, "a", encoding="utf-8") as f:
            for r in out:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def _read_gc_pre(idx, day, s, lot, rows=None):
    """GoCharting's bars (tape_log: lots, the extension's own delta) that CLOSED before this process's first future
    tick -> [(sec, vol, buy vol)] in units at each bar's last second: THE READ's flow on a late start. Bar width from
    the session tag ("NIFTY-I|5m|day"); a bar of unknown width is skipped, never guessed. `rows`: the day's tape rows
    when the caller already read them."""
    first = s.bars[0][0] if s.bars else 86400
    out = []
    for b in tape_log.read_bars(day, idx) if rows is None else rows:
        t, m = tape_log.bar_t(b), re.search(r"\|(\d+)m\|", str(b.get("session") or ""))
        if t is None or m is None or not isinstance(b.get("vol"), (int, float)) or not isinstance(b.get("buy"), (int, float)):
            continue
        t0, w = int(t // 1000 + 19800) % 86400, int(m.group(1)) * 60
        if t0 + w <= first:
            out.append((t0 + w - 1, round(b["vol"] * lot), round(b["buy"] * lot)))
    return sorted(set(out))


def _closed_by(rows, now):
    """5-min bar rows (t ms) closed by `now` (sec of day); all of them when now is None."""
    if now is None:
        return list(rows or ())
    return [b for b in rows or () if isinstance(b, dict) and isinstance(b.get("t"), (int, float))
            and int(b["t"] // 1000 + 19800) % 86400 + 300 <= now]


def _read_decode(idx, day, s, X, tl, c, ux, gc, now, live, levels):
    """Decode-loop Phases 0-1 on one READ card (display only, nothing here reaches read.timeline): the basis with its
    carry band and the options' witness (D6), the ranks beside every number (rank.py, Phase 1), COVERAGE (§5.1)."""
    import frame_v2
    import rank
    import coverage
    c["basis_band"] = frame_v2.basis_band(c.get("spot"), c.get("basis"), frame_v2.dte(day, s.fut_expiry),
                                          frame_v2.parity_basis(X, now, day))
    ref, _ref_id, ref_why = _rank_ref(idx, day, need_read=True)
    ik = next((b.get("ik") for b in reversed(ux or []) if b.get("ik")), None)
    try:
        c["ranks"] = rank.card_ranks(ref, idx, day, X, c, tl["rows"], ux, gc, ik)
    except Exception as e:                       # a rank failure is a why on the card, never the card's failure
        log.exception("read ranks")
        c["ranks"] = {"why": f"could not check — the rank read failed: {type(e).__name__}: {e}"}
    kind = (c["ranks"] or {}).get("kind")
    kinds = ((ref or {}).get("read") or {}).get("kinds") or {}
    c["coverage"] = coverage.build(idx, X, c, ux, gc, now, live, ref, ref_why, c["basis_band"], levels, kind,
                                   sum(1 for k in kinds.values() if k == kind) if kind else None)


def _read_reply(day, want=None, at=None):
    """GET /api/read: the card per index (read.card) and the day's events. A past ?day= replays through the same
    door (no levels, no log); ?at=HH:MM cuts a past day to that time (nothing after it is read)."""
    import v2feed
    import frame_v2
    import rank
    today = time.strftime("%Y-%m-%d")
    live = day == today
    lt = time.localtime()
    now = lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec if live else None
    if not live and at:
        now = int(at[:2]) * 3600 + int(at[3:5]) * 60
    hm_now = time.strftime("%H:%M")
    idxs = [want] if want else [i for i in v2feed.IDXS if i in instruments.ENABLED]

    def go(D):
        res = {}
        for idx in idxs:
            s = D.idx[idx]
            ux = _closed_by(_ux_bars(idx, day) if live else ux_log.read_bars(day, idx), None if live else now)
            levels = _read_levels(idx) if live else None
            gc = _closed_by(tape_log.read_bars(day, idx), None if live else now) if idx == "NIFTY" else None
            pre = _read_gc_pre(idx, day, s, v2feed.LOTS.get(idx) or 1, gc or [])
            rr = _rank_ref(idx, day, need_read=True)
            ref_id = rr[1:]
            push = _push_for(idx, day) if live else None
            key = (day, idx, s.chain.signature(), s.book.signature(), len(ux), None if now is None else now // read.MARK,
                   None if levels is None else tuple(sorted(levels.items())), len(pre), len(gc or ()), ref_id,
                   json.dumps(push, sort_keys=True),
                   None if now is None else (now - _READ_LOG_GRACE) // read.MARK)    # A16: the log's own tick, 15:31 too
            hit = _READ["cache"].get((day, idx))
            if hit and hit[0] == key:
                res[idx] = hit[1]
                continue
            X = read.from_v2(s, v2feed.LOTS.get(idx), pre)
            if not live and now is not None:
                X = frame_v2.cut(X, now)
            tl = read.timeline(X, ux, levels, now, rank.fuel_ref(rr[0], day, X, ux))
            c = read.card(X, tl, levels, now, push)
            if c.get("ok"):
                c["expr"] = _read_expr(idx, day, c["dir"]) if live else None
                c["events"] = tl["events"][-12:]
                last = tl["rows"][-1]
                c["blind"] = [f"{k}: {r.get('why')}" for k, r in (("WRITERS", last["writers"]), ("PRICE", last["price"]),
                                                                    ("FLOW", last["flow"])) if r.get("vote") is None]
                if s.bf:
                    c["blind"].append(f"CHAIN: the first {s.bf} minutes ({s.bf_from}-{s.bf_to}) are REST-rebuilt [I]")
                try:
                    _read_decode(idx, day, s, X, tl, c, ux, gc, now, live, levels)
                except Exception as e:           # never at the READ's expense
                    log.exception("read decode")
                    c["coverage"] = [{"src": "DECODE", "kind": "cnc", "text": f"could not check — {type(e).__name__}: {e}",
                                      "tag": "M"}]
            res[idx] = c
            _READ["cache"][(day, idx)] = (key, c)
            if live and c.get("ok") and _market_hours(day, today, hm_now):
                try:
                    _read_log(day, idx, tl, now)
                except OSError:
                    log.exception("read log")
        return res

    with _READ_LOCK:
        cards = v2feed.with_day(day, go)
        try:                                     # THE DECODE block (decode.py): additive, never at the card's expense
            dec = _decode_for(day, now, live)
        except Exception as e:
            log.exception("decode")
            dec = {"why": f"could not check — the decode read failed: {type(e).__name__}: {e}"}
        for idx, c in cards.items():
            c["decode"] = _decode_aged((dec or {}).get(idx), now)
            c["decode_why"] = None if c["decode"] else ((dec or {}).get("why")
                                                        or "could not check — the decode block is reading the day")
    return {"ok": True, "rev": read.REV, "day": day, "live": live, "asof": hm_now if live else (at or None),
            "indices": cards, "tag": "I"}


# ---- THE DECODE block (decode.py; memory read-changes-not-levels): the trajectories, then one combined call ------------
#
# ONE compute per 5-min close for all indices together (the peers read each other), never per request: live, a daemon
# thread fills the cache a GRACE minute after the close (GoCharting's bar and the chain's last row land seconds after
# it) and the previous close's block is served meanwhile; a replay (?day= / ?at=) computes in the caller's thread.
# DISPLAY ONLY: nothing here reaches a gate, a beep, a log row or trigger_log.
_DECODE = {"out": {}, "last": {}, "busy": set(), "replay": {}}
_DECODE_LOCK = threading.Lock()
_DECODE_GRACE = 60
DECODE_DIR = os.path.join("data", "decode")     # N7: the DECODE block's forward log, decode_<day>.jsonl (_decode_log)
_DECODE_SEEN = {}                  # path -> {(idx, close)} already on disk
_PAYLOADS = {}                     # main()'s payload boxes: FADE's live 3-min band bars (the zone machine's own)


def _decode_bars3(idx, day, T, live):
    """The zone machine's closed 3-min band bars at T: live, the refresh loop's payload (confluence_log.log_new's own
    bars); a past day, the cached 1-min session (the scorer's). [] when neither exists."""
    import confluence
    if live:
        box = _PAYLOADS.get(idx)
        raw = payload_at(box, confluence.INTERVAL) if box else None
        js = json.loads(raw) if raw else {}
        d = (js.get("days") or [None])[-1] or {}
        if not str(d.get("day") or "").startswith(time.strftime("%b %d")):
            return []
        bars = d.get("bars") or []
    else:
        bars = (confluence_log.session(idx, day) or {}).get("bars") or []
    return [b for b in bars if (confluence.close_of(confluence.flat(b).get("t")) or 10 ** 9) * 60 <= T]


def _decode_files(idx, day, T, live):
    """The recorders' side of one index's facts at T, read OUTSIDE v2feed's lock: the 5-min push bars, the Upstox bars,
    the rank reference, the push tables (cached per index-day), the zone rows whose 3-min bar had closed."""
    import decode
    ux = _closed_by(_ux_bars(idx, day) if live else ux_log.read_bars(day, idx), T)
    bars5 = [b for b in confluence_log.push_bars(idx, day, ux_rows=_ux_bars(idx, day) if live else None)
             if b["s"] + 300 <= T]
    if live:
        ref = _rank_ref(idx, day, need_read=True)[0]
    else:
        try:
            with open(os.path.join(RANK_DIR, f"rank_ref_{idx}_{day}.json"), encoding="utf-8") as f:
                ref = json.load(f)
        except (OSError, ValueError):
            ref = None
    if (idx, day) not in _HOLD2["refs"]:
        _HOLD2["refs"][(idx, day)] = confluence_log.push_refs(idx, day)
    refs, pwhy = _HOLD2["refs"][(idx, day)]
    zone = [z for z in confluence_log.zone_rows(idx, day) if (decode._min(z["t"]) + 3) * 60 <= T]
    return {"ux": ux, "bars5": bars5, "ref": ref, "pushes": hold2.pushes(bars5, refs) if refs else None, "pwhy": pwhy,
            "zone": zone}


def _decode_facts(idx, day, T, live, D, F, keep=False):
    """decode.facts for one index at the close T (sec of day), under v2feed's lock (D): THE READ's arrays, READ-2's
    FUEL and the card's basis at T, beside `F` (_decode_files). `keep` adds what tools/decode_now.py prints beside the
    block (the card, its rows)."""
    import decode
    import frame_v2
    import rank
    import v2feed
    s, lot = D.idx[idx], v2feed.LOTS.get(idx) or 1
    X = frame_v2.cut(read.from_v2(s, lot, _read_gc_pre(idx, day, s, lot)), T)
    fref = rank.fuel_ref(F["ref"], day, X, F["ux"]) if F["ref"] else None
    tl = read.timeline(X, F["ux"], None, T, fref)
    card = read.card(X, tl, None, T, None)
    fuel = read.fuel(rank.bars_of(F["ux"], 5), T, fref, lot) if fref else {"vote": None, "why": f"no rank_ref for {day}"}
    g = decode.facts(idx, T, F["bars5"], read.from_v2(s, lot), F["zone"], card.get("basis") if card.get("ok") else None,
                     fuel, F["pushes"], F["pwhy"], _push_for(idx, day) if live else None)
    if keep:
        g.update(card=card, rows=tl.get("rows") or [])
    return g


def _decode_all(day, now, live, keep=False):
    """{idx: the decode block} at `now`'s 5-min close (decode.at_close), every enabled index, the peers read together.
    With keep, also {"_facts": {idx: facts}} for the tool. One index's failure is its own block's "?"."""
    import decode
    import v2feed
    T = decode.at_close(min(now if now is not None else read.CLOSE_S, read.CLOSE_S))
    idxs = [i for i in v2feed.IDXS if i in instruments.ENABLED]
    if T <= decode.OPEN_S:
        return {i: decode.empty("the session has not opened (09:15)") for i in idxs}

    files = {}
    for i in idxs:
        try:
            files[i] = _decode_files(i, day, T, live)
        except Exception as e:
            log.exception("decode files %s", i)
            files[i] = e

    def go(D):
        out = {}
        for i in idxs:
            try:
                if isinstance(files[i], Exception):
                    raise files[i]
                out[i] = _decode_facts(i, day, T, live, D, files[i], keep)
            except Exception as e:
                log.exception("decode facts %s", i)
                out[i] = e
        return out
    G = v2feed.with_day(day, go)
    res = {}
    for i in idxs:
        g = G[i]
        if isinstance(g, Exception):
            res[i] = decode.empty(f"could not check — {type(g).__name__}: {g}")
            continue
        peers = [G[k] for k in idxs if k != i and not isinstance(G[k], Exception)]
        fin = rin = f = None
        # ponytail: the chain + book records are re-read whole once per close per index (~2 s each by 15:00, off the
        # request thread); an incremental reader (trap_log's byte offsets) if that ever shows on the tape
        try:                                     # the setups' heavy inputs: §1i's own loaders, cut at T by their readers
            f = confluence_log.inputs(i, day, lg={})
            fin = {"bars3": _decode_bars3(i, day, T, live), "chain": f["chain"], "book": f["book"], "gc": f["gc"]}
        except Exception:
            log.exception("decode FADE inputs %s", i)
        try:
            if f is not None:
                rin = dict(confluence_log.ride_inputs(i, day, T, light=True), chain=f["chain"], book=f["book"], gc=f["gc"])
        except Exception:
            log.exception("decode RIDE inputs %s", i)
        try:                                     # A44: the EFFORT line's read, its own "?" on failure
            g["effort"] = _decode_effort(i, day, T, f)
        except Exception as e:
            log.exception("decode effort %s", i)
            g["effort"] = effort.blank(f"could not check — {type(e).__name__}: {e}")
        try:
            res[i] = decode.decode(g, peers, fin, rin)
        except Exception as e:
            log.exception("decode %s", i)
            res[i] = decode.empty(f"could not check — {type(e).__name__}: {e}")
    if keep:
        res["_facts"] = G
    return res


def _decode_effort(idx, day, T, f):
    """A44: effort.read at the close T, on Fable's sources -- the futures book record (book_log) and the chain
    recorder's spot per minute (`f` = confluence_log.inputs: its chain grid, REST-backfilled minutes left out as his
    harness never saw them). SENSEX is not read (A25) and says so."""
    import v2feed
    if idx not in effort.STEP:
        return effort.read(idx, {}, {}, 0)
    if f is None:
        return effort.blank("could not check — the chain record could not be read")
    # ponytail: the whole book record is re-read once per close per index (~0.4 s by 15:00, in the decode thread);
    # an incremental (byte-offset) reader if it ever shows on the tape
    fm = effort.minutes(book_log.read_rows(day, idx), v2feed.LOTS.get(idx) or 1)
    spot = {int(m[:2]) * 60 + int(m[3:5]): r["spot"] for m, r in f["chain"][0].items() if r.get("src") != "backfill"}
    return effort.read(idx, fm, spot, T // 60 - 1)


def _decode_for(day, now, live):
    """The blocks for /api/read and the frame: live from the cache (filled once per close by a daemon thread; the last
    close's blocks meanwhile, None before the first), a replay computed here."""
    import decode
    if not live:                                 # a past day's files no longer change: computed once per close
        key = (day, decode.at_close(min(now if now is not None else read.CLOSE_S, read.CLOSE_S)))
        with _DECODE_LOCK:
            hit = _DECODE["replay"].get(key)
        if hit is None:
            hit = _decode_all(day, key[1], False)
            with _DECODE_LOCK:
                if len(_DECODE["replay"]) >= 64:
                    _DECODE["replay"].clear()
                _DECODE["replay"][key] = hit
        return hit
    T = decode.at_close(min(max(now - _DECODE_GRACE, 0), read.CLOSE_S))
    key = (day, T)
    th = None
    with _DECODE_LOCK:
        hit = _DECODE["out"].get(key)
        if hit is None and key not in _DECODE["busy"]:
            _DECODE["busy"].add(key)
            th = threading.Thread(target=_decode_run, args=(day, T, key), name="decode", daemon=True)
        last = hit or _DECODE["last"].get(day)
    if th is not None:
        th.start()
    return last


def _decode_run(day, T, key):
    try:
        out = _decode_all(day, T, True, keep=T >= read.CLOSE_S)
    except Exception as e:
        log.exception("decode run")
        out = {"why": f"could not check — the decode read failed: {type(e).__name__}: {e}"}
    G = out.pop("_facts", None)
    if G:
        _onesided_log(day, G)
    _decode_log(day, T, out)
    with _DECODE_LOCK:
        _DECODE["out"] = {k: v for k, v in _DECODE["out"].items() if k[0] == day and k[1] >= T - 900}
        _DECODE["out"][key] = out
        _DECODE["last"] = {day: out}
        _DECODE["busy"].discard(key)


def _decode_aged(blk, now):
    """A13: a copy of the block with age_s = now (sec of day) minus the close it reads, set when it is SERVED (the block
    is cached per close); None when either is unknown. The extension reads it too."""
    if not isinstance(blk, dict):
        return blk
    t = blk.get("t")
    return dict(blk, age_s=None if now is None or not t else now - (int(t[:2]) * 3600 + int(t[3:5]) * 60))


def _decode_log(day, T, out):
    """N7: each index's DECODE block once per 5-min close, to DECODE_DIR/decode_<day>.jsonl -- the block AS SERVED, from
    the one live compute a grace minute after the close (A16's read-log timing: the bar and the chain row have landed),
    never rewritten by a later compute. A close the server was not up for stays absent (a replay is not what the app
    said); a row computed late says so by its `at`. Fail-soft."""
    import decode
    import onesided
    if T <= decode.OPEN_S:                       # before the first close: the blocks are "?", nothing to record
        return
    try:
        path = os.path.join(DECODE_DIR, f"decode_{day}.jsonl")
        seen = _DECODE_SEEN.get(path)
        if seen is None:
            seen = _DECODE_SEEN[path] = {(r.get("idx"), r.get("T")) for r in confluence_log._rows(path)}
        t = decode.hm(T // 60)
        rows = [dict(b, day=day, idx=i, T=t, rev=decode.REV, rev_onesided=onesided.REV, at=time.time())
                for i, b in out.items() if isinstance(b, dict) and "call" in b and (i, t) not in seen]
        if rows:
            os.makedirs(DECODE_DIR, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in rows))
            seen.update((r["idx"], t) for r in rows)
    except Exception:
        log.exception("decode log")


def _onesided_log(day, G):
    """§1o's daily row per index (onesided.log: once per day + index, fail-soft), from the facts of the first live
    compute at or after the 15:30 close -- so a server started after the close writes it on its first read (the
    anytime-start rule). An index whose facts failed writes nothing; a later start that day can still write it."""
    import onesided
    try:
        ok = {i: g for i, g in G.items() if isinstance(g, dict)}
        onesided.log([onesided.row(day, i, g["bars5"], g["l5"], g["l15"], [p["bars5"] for k, p in ok.items() if k != i])
                      for i, g in ok.items()])
    except Exception:
        log.exception("onesided log")


# ---- EXTENSION V2 (docs/superpowers/specs/2026-10-19-extension-v2-design.md §7; orderflow-desk V2-PLAN "Frame contract")
#
# read / plan / writers / ux_flow / rank_ref_id ride the frame of a v2 page -- one that sends `rank_have` or `build`;
# today's page sends neither and gets none of it, so her live extension costs nothing new. NEVER PER POST (the
# 2026-09-18 wedge was per-POST work): one compute per (day, idx) at most every V2_EVERY s, in a daemon thread; a
# POST reads the cache (only the very first one waits, at most V2_WAIT s). rank_ref = RANK_DIR/rank_ref_<idx>_<day>.json
# (tools/rank_build.py, days < day), loaded once per (idx, day); when it is missing it is built ONCE in a daemon thread
# and the newest earlier file is served meanwhile, flagged stale_from (still days < day: no look-ahead). Nothing here
# enters the frame record (it runs after frame_log), and DISPLAY ONLY: frame_v2.py gates nothing.
_V2 = {"parts": {}, "busy": set(), "ref": {}, "building": set()}
_V2_LOCK = threading.Lock()
V2_EVERY, V2_WAIT = 20, 2.0
RANK_DIR = os.path.join("data", "rank")
_V2_NONE = ("read", "plan", "writers", "ux_flow", "decode")


def _rank_mod():
    """tools/rank_build.py, loaded by path (tools/ is not a package)."""
    m = sys.modules.get("rank_build")
    if m is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("rank_build", str(ROOT / "tools" / "rank_build.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        sys.modules["rank_build"] = m
    return m


def _rank_build_bg(idx, day):
    """Build day's reference once per process, in a daemon thread, into the RANK_DIR of the moment it was asked."""
    key, out_dir = (idx, day), RANK_DIR
    with _V2_LOCK:
        if key in _V2["building"]:
            return
        _V2["building"].add(key)

    def run():
        try:
            m = _rank_mod()
            ref = m.build(idx, day)
            m.write(ref, out_dir)
            hit = (ref, ref["id"], None)
        except Exception as e:
            log.exception("rank_ref build")
            old = _V2["ref"].get(key) or (None, None, None)
            hit = (old[0], old[1], f"could not check — the rank_ref build failed: {e}")
        with _V2_LOCK:
            _V2["ref"][key] = hit
    threading.Thread(target=run, name=f"rank-{idx}-{day}", daemon=True).start()


def _rank_ref(idx, day, need_read=False):
    """(ref, id, why) for (idx, day): the day's file, else the newest earlier one (stale_from) while it builds.
    need_read (THE READ's ranks, decode-loop Phase 1): a reference built before its `read` section existed is rebuilt
    once in the background and served meanwhile -- its tables are the extension's, unchanged."""
    hit = _rank_ref_load(idx, day)
    ref = hit[0]
    if need_read and ref is not None and "read" not in ref and not ref.get("stale_from"):
        _rank_build_bg(idx, day)
        return ref, hit[1], "stale — this reference predates THE READ's ranks; rebuilding it"
    return hit


def _rank_ref_load(idx, day):
    key = (idx, day)
    with _V2_LOCK:
        hit = _V2["ref"].get(key)
    if hit is not None:
        return hit
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        return None, None, f"could not check — no session day ({day!r})"

    def load(p):
        try:
            with open(p, encoding="utf-8") as f:
                r = json.load(f)
            return r if isinstance(r, dict) and r.get("id") else None
        except (OSError, ValueError):
            return None
    ref = load(os.path.join(RANK_DIR, f"rank_ref_{idx}_{day}.json"))
    if ref is not None:
        hit = (ref, ref["id"], None)
    else:
        _rank_build_bg(idx, day)
        try:
            names = sorted(n for n in os.listdir(RANK_DIR) if re.match(rf"^rank_ref_{re.escape(idx)}_\d{{4}}-\d{{2}}-\d{{2}}\.json$", n)
                           and n[-15:-5] < day)
        except OSError:
            names = []
        old = load(os.path.join(RANK_DIR, names[-1])) if names else None
        hit = ((dict(old, stale_from=old.get("before")), old["id"], f"stale — the {old.get('before')} reference while {day}'s builds")
               if old else (None, None, f"building — no reference for {day} yet"))
    with _V2_LOCK:
        return _V2["ref"].setdefault(key, hit)


def _v2_parts(idx, day, s, now, now_ms, ux, ref, live=False):
    """frame_v2.compose for one index at `now` (sec of day; None = the recorded day's end), from v2feed's IdxState `s`.
    Call under v2feed's lock (read.from_v2 references its arrays). tools/frame_v2_replay.py calls this too."""
    import v2feed
    import frame_v2
    import rank
    lot = v2feed.LOTS.get(idx) or 1
    X = frame_v2.cut(read.from_v2(s, lot, _read_gc_pre(idx, day, s, lot)), now)
    # READ-2: FUEL's reference, and live, JAGAH's PDL / PDH and the extension's last push (the card's alone)
    tl = read.timeline(X, ux, _read_levels(idx) if live else None, now, rank.fuel_ref(ref, day, X, ux))
    c = read.card(X, tl, None, now, _push_for(idx, day) if live else None)
    bf = f"CHAIN: the first {s.bf} minutes ({s.bf_from}-{s.bf_to}) are REST-rebuilt [I]" if s.bf else None
    expr = _read_expr(idx, day, c.get("dir")) if live and c.get("ok") else None
    return frame_v2.compose(X, tl, c, ux, ref, now, now_ms, frame_v2.dte(day, s.fut_expiry), bf, expr, day=day)


def _v2_refresh(idx, day, ref, ref_id):
    try:
        import v2feed
        live = day == time.strftime("%Y-%m-%d")
        lt = time.localtime()
        now = lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec if live else None
        ux = _ux_bars(idx, day) if live else ux_log.read_bars(day, idx)
        parts = v2feed.with_day(day, lambda D: _v2_parts(idx, day, D.idx[idx], now, int(time.time() * 1000) if live else None,
                                                         ux, ref, live))
    except Exception as e:
        log.exception("frame v2")
        parts = {}
        for k in _V2_NONE:
            parts[k], parts[k + "_why"] = None, f"could not check — the v2 read failed: {type(e).__name__}: {e}"
    try:                                         # THE DECODE block, outside v2feed's lock (a replay takes it itself)
        dec = _decode_for(day, now, live) or {}
        parts["decode"] = dec.get(idx)
        parts["decode_why"] = None if parts["decode"] else (dec.get("why") or "could not check — the decode block is "
                                                                                "reading the day")
    except Exception as e:
        log.exception("frame decode")
        parts["decode"], parts["decode_why"] = None, f"could not check — the decode read failed: {type(e).__name__}: {e}"
    with _V2_LOCK:
        _V2["parts"][(day, idx)] = (time.time(), parts, ref_id)
        _V2["busy"].discard((day, idx))


def _frame_v2(idx, day):
    """(the v2 frame keys, rank_ref) for one POST: a cache read; the compute runs at most every V2_EVERY s."""
    ref, ref_id, ref_why = _rank_ref(idx, day)
    key, th = (day, idx), None
    with _V2_LOCK:
        hit = _V2["parts"].get(key)
        if (hit is None or time.time() - hit[0] >= V2_EVERY or hit[2] != ref_id) and key not in _V2["busy"]:
            _V2["busy"].add(key)
            th = threading.Thread(target=_v2_refresh, args=(idx, day, ref, ref_id), name=f"v2-{idx}", daemon=True)
    if th is not None:
        th.start()
        if hit is None:
            th.join(V2_WAIT)
    with _V2_LOCK:
        hit = _V2["parts"].get(key)
    if hit is None:
        parts = {}
        for k in _V2_NONE:
            parts[k], parts[k + "_why"] = None, "could not check — the first v2 read of this day is still loading"
    else:
        parts = hit[1]
    lt = time.localtime()                        # A13: the decode block's age at THIS post (the parts are cached)
    now = lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec if day == time.strftime("%Y-%m-%d") else None
    srn, srw = _slot_range_now(ref, now)
    return dict(parts, decode=_decode_aged(parts.get("decode"), now), rank_ref_id=ref_id, rank_ref_why=ref_why,
                slot_range_now=srn, slot_range_why=srw), ref


def _slot_range_now(ref, now):
    """A45: ({"HHMM": pts, ...}, None) -- the reference days' median high - low (rank_build.slot_range) of the 5-min
    slot `now` (sec of day) is in and of the one before it (the bar that just closed), the map shape the extension's
    slotNR reads (orderflow-desk v2.js), for its bars judged before its NR has 5 bars; else (None, why)."""
    if now is None or not read.OPEN_S <= now < read.CLOSE_S:
        return None, "not shown — outside today's 09:15-15:30 session"
    tab = (ref or {}).get("slot_range")
    if not tab:
        return None, "could not check — this rank_ref has no slot_range (built before 2026-10-23)"
    s = now // 300 * 300
    keys = [f"{x // 3600:02d}{x // 60 % 60:02d}" for x in (s - 300, s) if x >= read.OPEN_S]
    out = {k: tab[k] for k in keys if k in tab}
    return (out, None) if out else (None, f"could not check — no reference bar in the {keys[-1][:2]}:{keys[-1][2:]} slot")


# ---- BOARD rev 3 (docs/mockups/board-chess-rev3-2026-09-24-notes.md §8) ----
#
# /api/board composes board.py and trendbox.py for the LATEST FINISHED MINUTE
# of one index, CACHED per index per minute: the UI polls every ~15 s, and a
# per-request rebuild is how this server wedged on 2026-09-18 (a 55 MB rewrite
# per POST). One computation per index per minute -- plus one mirror per strike
# pair asked for -- and every other request is a dict lookup. After the close
# the minute stops moving (15:29), so the last session snapshot is computed
# once and served. DISPLAY ONLY: nothing here feeds setup.gate, the zone
# machine or trigger_log, and §1d is only called.
BOARD_MIRROR_SPAN = 5     # the mirror follows strikes within ATM +- this many steps (bounds REST per request)


def _board_fresh():
    return {"core": {}, "base": {}, "reply": {}, "locks": {}, "first": {}, "first_day": None,
            "trend_day": {}, "trend_1m": {}}


_BOARD = _board_fresh()


def _board_clock():
    """(day, HH:MM) now. One seam, so a test can hold the clock."""
    return time.strftime("%Y-%m-%d"), time.strftime("%H:%M")


def _market_hours(day, now_day, now_hm):
    """THE ONE GATE for every forward record a tape post reaches: the frame log, the scorer, the marks writer
    (tape_log) and the decoder log. True only for TODAY's session: the posted day is today, a weekday, and
    09:15 <= now < 15:35 (the 15:25 bar closes at 15:30 and is written by the post right after it; _session_only has
    already stripped anything stamped 15:30 or later). On 3-4 Oct a GoCharting tab left open on 1 Oct wrote 144 marks
    into 1 Oct's record on a Sunday and BANKNIFTY-priced marks into NIFTY's on a Saturday: the marks writer had no gate."""
    from datetime import date as _date
    try:
        weekday = _date.fromisoformat(now_day).weekday()
    except (TypeError, ValueError):
        return False
    return day == now_day and weekday < 5 and "09:15" <= now_hm < "15:35"


_STORY_MEM = {}      # idx -> the two things with no time of their own: VPIN crossing 0.8, a flat read going to CAN'T CHECK


def _own_fold(fold, idx):
    """The frame's fold when it is THIS index's trade (or names none), else None. Since 25 Oct (F6) the frame can carry her
    open trade on another index for the panel's voice; the story's count and the HOLD-vs-DECODER log read this index's
    decoder, so a SENSEX trade riding NIFTY's POST never enters them."""
    return fold if ((fold or {}).get("trade") or {}).get("idx") in (None, idx) else None


def _story_for(idx, day, doc, fr, now_ms):
    """THE PANEL'S STORY (story.compose_all) for this post: the decoder's sentence, the day as chapters, the decoder's
    count beside her trade, and the out-of-the-ordinary highlights. Reads what the server already publishes -- the
    posted decoder, the frame's fold / flat / feed, the trap reply (/api/trap, its sides-3 `three`), the VPIN gauge --
    and the decoder log for the events a restarted page did not post again (anytime-start). Re-derives nothing."""
    import story as story_mod
    m = _STORY_MEM.get(idx)
    if m is None or m["day"] != day:
        m = _STORY_MEM[idx] = {"day": day, "vpin": None, "vpin_since": None, "flat": None, "cant": []}
    rep = _TRAP.get("reply") or {}
    trap = (rep.get("indices") or {}).get(idx)
    three = rep.get("three")
    if not (trap or {}).get("ok") or trap.get("day") != day:
        trap = {"why": (trap or {}).get("why") or "trap-1 abhi nahi (the trap read has not run for this day)"}
        three = None
    with _SENSES_LOCK:
        g = (_SENSES.get("vpin") or {}).get(f"{idx}-FUT")
        pct = g.state().get("pct") if g else None
    hi = None if pct is None else pct >= 0.8
    if hi and m["vpin"] is False:               # a crossing this process SAW; a restart already above 0.8 is no change
        m["vpin_since"] = now_ms
    m["vpin"] = hi
    vp = None if pct is None else {"pct": pct, "since_ms": m["vpin_since"] if hi else None, "shadow": True, "tag": "I"}
    flat = fr.get("flat") if isinstance(fr.get("flat"), dict) else {}
    chips = {k: (v or {}).get("chip") for k, v in (flat.get("rows") or {}).items()}
    for k, c in chips.items():
        o = (m["flat"] or {}).get(k)
        if c == "CAN'T CHECK" and o not in (None, "CAN'T CHECK"):
            m["cant"].append({"what": k.upper(), "t_ms": now_ms, "block": "flat"})
    m["flat"] = chips or m["flat"]
    m["cant"] = [c for c in m["cant"] if now_ms - c["t_ms"] <= story_mod.HOLD_MS]
    try:
        logged = decoder_log.read_events(day, idx)
    except Exception:
        logged = []
    return story_mod.compose_all(doc.get("decoder"), doc.get("futPx"), day, now_ms, doc.get("closed") or [],
                                 _own_fold(fr.get("fold"), idx), trap, three, fr.get("feed"), vp, logged, m["cant"])


_VAL_LAST = {}       # trade id -> its last live read: tags her exits (FEAR_EXIT / AMBER_EXIT), never blocks them
_TYPICAL = {"at": 0.0, "v": None}


def _record_days(today_trades):
    """Her trades by day for the typical time-to-target: the saved days, today's from memory (not its file)."""
    import glob
    today = _board_clock()[0]
    out = [list(today_trades)]
    for p in sorted(glob.glob(os.path.join(str(day_state.DIR), "day_*.json")))[-60:]:
        if today in os.path.basename(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                out.append(json.load(f).get("hold_trades") or [])
        except (OSError, ValueError):
            continue
    return out


def _validate_for(idx, day, doc, fr, now_ms):
    """THE LIVE IN-TRADE READ (validate_live.read) for this post: her open trade on idx with the frame's fold, the posted
    bars / VWAP / decoder, the engine's chain snapshots and the frame's walls. Fills her thesis once from the engine's
    levels where she left them blank (src engine), then locks them."""
    with HOLD_TRADES_LOCK:
        trades = [dict(t) for t in _hold_trades()]
    tr = next((t for t in trades if t.get("idx") == idx and not t.get("exit_t")), None)
    if time.time() - _TYPICAL["at"] > 60:
        _TYPICAL.update(at=time.time(), v=validate_live.typical_s(_record_days(trades)))
    eng = fold_live._ENG.get(idx)
    chain = list((eng.rows.get("chain") if eng and eng.day == day else None) or [])[-80:]
    bands = doc.get("bands") or []
    v = validate_live.read(tr, fr.get("fold"), day, now_ms, doc.get("closed") or [], doc.get("decoder"),
                           (bands[-1] or {}).get("vwap") if bands else None, doc.get("forming"), chain,
                           (fr.get("walls") or {}).get("rows"), trades, _TYPICAL["v"], idx)
    if tr is not None and v.get("level"):
        _VAL_LAST[tr["id"]] = v
        lv, th = v["level"], tr.get("thesis") or {}
        fill = {k: lv[k] for k in ("t1", "t2", "inval") if th.get(k) is None and lv.get(k) is not None}
        if fill:
            with HOLD_TRADES_LOCK:
                live = next((t for t in _hold_trades() if t["id"] == tr["id"]), None)
                if live is not None:
                    t_ = live.setdefault("thesis", {"why": None, "t1": None, "t2": None, "inval": None, "src": {},
                                                    "locked_at": time.strftime("%H:%M:%S")})
                    for k, x in fill.items():
                        if t_.get(k) is None:
                            t_[k] = x
                            t_.setdefault("src", {})[k] = "engine"
            _save_day_state()
    return v


def _story_past(idx, day):
    """GET /api/story?day=: a day's chapters from the SAVED logs only -- the decoder's forward log (its events, tagged
    "log"), the trap log's state stamps and the ladder record's bars (for asar). For RECORD on the DESK. Never the live
    page's events, never re-derived; a day without those logs says so."""
    import story as story_mod
    logged = decoder_log.read_events(day, idx)
    trap, slots = {"events": []}, []
    try:
        with daylog.open_text(os.path.join(trap_log.DIR, f"trap_{day}.jsonl")) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("idx") == idx and r.get("kind") == "state":
                    trap["events"].append(r)
                elif r.get("idx") == idx and r.get("kind") == "slot":
                    slots.append(r)
    except OSError:
        trap = None
    bars = [b for b in tape_log.read_bars(day, idx) if b.get("t") is not None]
    ch = story_mod.chapters(None, bars, day, trap, slots, logged)
    if not logged and not (trap or {}).get("events"):
        ch = {**ch, "items_why": f"no decoder log and no trap log for {idx} on {day} (both forward logs start with the "
                                  f"server that has them; nothing is rebuilt from a re-cut cache)" if not ch["items"] else ch["items_why"]}
    return {"ok": bool(ch["items"]), "idx": idx, "day": day, "past": True, "chapters": ch, "src": "log",
            "events_logged": len(logged), "trap_stamps": len((trap or {}).get("events") or []),
            "trap_why": None if trap is not None else f"no trap log for {day}"}

def _board_asof(minutes, now):
    """The latest FINISHED minute on the grid -- never the one in progress
    (`now`), never 15:30 or later -- or None before the day's first mark."""
    cutoff = min(now, SESSION_END_HHMM)
    ts = [t for t in list(minutes or {}) if isinstance(t, str) and t < cutoff]
    return max(ts) if ts else None


def _board_opens(poller, idx):
    """{(strike, "ce"|"pe"): OI at the open} off the chain's latest snapshot:
    oi - oi_chg, one subtraction (Upstox's oi_chg is since today's open)."""
    snap = (getattr(poller, "prevs", None) or {}).get(idx) if poller else None
    out = {}
    for row in (snap or {}).get("strikes") or []:
        for side in ("ce", "pe"):
            leg = row.get(side) or {}
            if isinstance(leg.get("oi"), (int, float)):
                out[(float(row["k"]), side)] = float(leg["oi"]) - float(leg.get("oi_chg") or 0)
    return out


def _board_core(poller, idx):
    """The grid cut to the latest finished minute, its folds, and the day's
    FIRST FOLD -- the part /api/oihist shares with /api/board. Memory only, no
    REST; cached per (index, day, minute).

    FIRST is stamped ONCE per day, off a grid that is whole from the open (a
    restart's backfill lands on its own thread, and a FIRST read off half a
    morning would be kept all day), into _BOARD["first"]; _save_day_state
    writes it down and _load_day_state reads it back, so a restart re-reads the
    same FIRST (the anytime-start rule)."""
    st = (getattr(poller, "states", None) or {}).get(idx) if poller else None
    if st is None:
        return None
    snap = dict(getattr(st, "minutes", None) or {})     # one copy: the poller keeps writing
    day, now = _board_clock()
    asof = _board_asof(snap, now)
    minutes = fronts.cut(snap, asof) if asof else {}
    # the mark count is in the key: a restart's backfill lands on its own
    # thread, and after the close `asof` stops moving -- without it a board
    # read off half a morning would be served all evening
    key = (day, asof, len(minutes))
    hit = _BOARD["core"].get(idx)
    if hit is not None and hit["key"] == key:
        return hit
    if _BOARD["first_day"] != day:
        _BOARD["first"], _BOARD["first_day"] = {}, day
    g = fronts.grid(minutes)
    evs = fronts.folds(minutes, g)
    opens = _board_opens(poller, idx)
    peak = dict(getattr(st, "peak", None) or {})
    cov = board.coverage(g[0])
    first = _BOARD["first"].get(idx)
    if first is None and cov["whole"]:
        got = board.first_fold(minutes, evs, opens, peak, g)
        if got:
            first = _BOARD["first"][idx] = dict(got, src="stamped by this process at " + asof)
    core = {"key": key, "idx": idx, "day": day, "asof": asof, "minutes": minutes, "g": g, "evs": evs,
            "opens": opens, "peak": peak, "first": first, "cov": cov}
    _BOARD["core"][idx] = core
    return core


def _board_facts(idx, day, asof, fr):
    """grounds' CVD / FLOW facts and the footprint marks, as of `asof`: only
    ladder bars CLOSED by then and fill runs begun by then (the mockup's
    replay rule), so a restart reads a past minute exactly as it read live."""
    try:
        tape = _tape_reply(idx, day)
    except Exception as e:                  # a disk fault costs the facts, never the board
        why = f"tape record unreadable: {type(e).__name__}: {e}"
        return {"cvd": None, "flow": None, "cvd_why": why, "flow_why": why}, None
    if not tape.get("ok"):
        why = tape.get("why") or "no prints record"
        return {"cvd": None, "flow": None, "cvd_why": why, "flow_why": why}, None
    ux = tape.get("ux") or {}
    now = board.mm(asof)
    bars = [b for b in ux.get("bars") or []
            if b.get("t") is not None and board.mm(grounds._hh(b["t"])) + 4 <= now]  # a bar starting at m has closed by the END of finished minute m + 4 (2026-09-28 audit, bug 9; = board._closed)
    runs = [r for r in (ux.get("marks") or {}).get("runs") or []
            if r.get("from_t") is None or grounds._hh(r["from_t"]) <= asof]
    facts = grounds.facts(bars, runs, fr, runs_why=(ux.get("marks") or {}).get("runs_why"),
                          roll=_roll_why(idx, day), idx=idx)
    if not bars and ux.get("why"):
        facts["cvd_why"] = facts["flow_why"] = ux["why"]
    return facts, tape.get("marks")


def _board_trend(idx, day, asof):
    """trendbox.rows off REST, cached like levels.py: the prior session's 1-min,
    the 30-min and the daily candles once a day (a failure is retried at most
    once a minute), today's 1-min at most once a minute. -> (rows|None, why)."""
    import upstox_feed
    import upstox_rest
    td = _BOARD["trend_day"].get(idx)
    if td is None or td["day"] != day or (td["data"] is None and td["tried"] != asof):
        try:
            td = {"day": day, "data": trendbox.fetch_daily(idx, day), "why": None, "tried": asof}
        except Exception as e:
            td = {"day": day, "data": None, "why": f"{type(e).__name__}: {e}", "tried": asof}
        _BOARD["trend_day"][idx] = td
    t1 = _BOARD["trend_1m"].get(idx)
    if t1 is None or t1["key"] != (day, asof):
        try:
            t1 = {"key": (day, asof), "c": upstox_rest.intraday(upstox_instruments.index_key(idx),
                                                                upstox_feed.read_token()), "why": None}
        except Exception as e:
            t1 = {"key": (day, asof), "c": None, "why": f"{type(e).__name__}: {e}"}
        _BOARD["trend_1m"][idx] = t1
    if td["data"] is None:
        return None, "the prior sessions' index candles did not load: " + td["why"]
    if t1["c"] is None:
        return None, "today's index candles did not load: " + t1["why"]
    d = td["data"]
    tr = trendbox.rows(d["m1_prior"], t1["c"], d["m30"], d["d1"], day, asof)
    return tr, (None if tr else f"no index candle at or before {asof} today")


def _board_mirror(idx, asof, kce, kpe):
    """The mirror read off /api/contract's own assembly (5-min legs, their
    session VWAP bands and prior-session pivots, the near future)."""
    import live
    try:
        if kce == kpe:
            b = live.leg_pivots(live.build_contract(idx, strike=kce, side="BOTH", interval=5))
            legs, fut, exp = b.get("legs") or {}, (b.get("index_series") or {}).get("bars"), b.get("expiry")
        else:
            bc = live.leg_pivots(live.build_contract(idx, strike=kce, side="CE", interval=5))
            bp = live.leg_pivots(live.build_contract(idx, strike=kpe, side="PE", interval=5))
            legs = {"CE": (bc.get("legs") or {}).get("CE"), "PE": (bp.get("legs") or {}).get("PE")}
            fut, exp = (bc.get("index_series") or {}).get("bars"), bc.get("expiry")
    except Exception as e:                  # one index's option REST failing costs its mirror only
        log.exception("board mirror %s", idx)
        return {"ok": False, "why": board.CC + f"{type(e).__name__}: {e}", "tag": "M"}
    return board.mirror(legs, fut, asof, expiry=exp)


def _board_levels(idx):
    """levels.static_levels (PDH/PDL/PDC/PWH/PWL/OPEN) off the war map's own
    daily candles, for the board's squares -- memory only, no REST here; None
    until the war map's daily fetch has landed. No lock: `daily` is replaced
    whole by Levels.set_daily, so one attribute read sees all of it or none."""
    wm = getattr(_SENSES.get("warmap"), "_by", None) or {}
    daily = getattr(getattr(wm.get(idx), "levels", None), "daily", None)
    return warmap_mod.levels_mod.static_levels(daily) if daily else None


def _board_strikes(q, atm, step):
    """(CE strike, PE strike, why): ATM by default; ?strike=K sets both legs,
    ?ce=K / ?pe=K each one. A strike beyond ATM +- BOARD_MIRROR_SPAN steps is
    not fetched, and says so."""
    def num(name):
        try:
            v = float((q.get(name) or [""])[0])
            return v if v == v and abs(v) != float("inf") else None
        except ValueError:
            return None
    both = num("strike")
    kce, kpe = num("ce") or both or atm, num("pe") or both or atm
    far = [f"{side} {k:,.0f}" for side, k in (("CE", kce), ("PE", kpe))
           if abs(k - atm) > BOARD_MIRROR_SPAN * step]
    return kce, kpe, (board.NOT_SHOWN + f"{' and '.join(far)} is beyond ATM {atm:,.0f} ± {BOARD_MIRROR_SPAN} strikes"
                      if far else None)


_BOARD_NOT_SHOWN = {
    "level_under_attack": board.NOT_SHOWN + "a draft read; it waits for her pre-registration (notes §7.1)",
    "flush": board.NOT_SHOWN + "her proposed flush-candle rule waits for pre-registration (notes §7.2)",
    "deep_otm": board.NOT_SHOWN + "the deep-OTM strip is a later batch (notes §8 step 7)",
    "forced": board.NOT_SHOWN + "forced / released waits for her §1d addendum, which she held (notes §7.4)",
    "engine": board.NOT_SHOWN + "the engine's own words and their grounding are /api/calls",
}


def _board_hilo(idx, day, asof):
    """The day's spot high / low to `asof`'s minute off every recorded chain row (read.day_hl, decode-loop D6), or
    None -- the squares then fall back to the grid's marks. Fail-soft: never at the board's expense."""
    try:
        import v2feed
        end = int(asof[:2]) * 3600 + int(asof[3:5]) * 60 + 59
        return v2feed.with_day(day, lambda D: read.day_hl(read.from_v2(D.idx[idx]), end).get("spot"))
    except Exception:                          # noqa: BLE001
        log.exception("board hilo")
        return None


def _board_reply(poller, idx, q):
    """GET /api/board's bytes for one index at its latest finished minute."""
    core = _board_core(poller, idx)
    if core is None or not core["g"][0]:
        why = ("the chain poller has no state for this index yet" if core is None else
               "no finished minute of today's session on the grid yet")
        return json.dumps({"ok": False, "idx": idx, "day": _board_clock()[0], "asof": None,
                           "why": board.CC + why, "not_shown": _BOARD_NOT_SHOWN}).encode()
    key, day, asof = core["key"], core["day"], core["asof"]
    # the war map's daily levels can land AFTER the close, when the minute key
    # has stopped moving -- their arrival is part of the key, or the squares
    # would stay level-blind all evening
    lv = _board_levels(idx)
    key = (key, lv is not None)
    times, spots, ks, _S, _RP = core["g"]
    step = min((b - a for a, b in zip(ks, ks[1:]) if b > a), default=None) or 1.0
    atm = round(spots[-1] / step) * step
    kce, kpe, far = _board_strikes(q, atm, step)
    hit = (_BOARD["reply"].get(idx) or {})
    if hit.get("key") == key and (kce, kpe) in hit:
        return hit[(kce, kpe)]
    with _BOARD["locks"].setdefault(idx, threading.Lock()):
        hit = (_BOARD["reply"].get(idx) or {})
        if hit.get("key") == key and (kce, kpe) in hit:
            return hit[(kce, kpe)]
        base = _BOARD["base"].get(idx)
        if base is None or base["key"] != key:
            fr = fronts.read(core["minutes"], core["peak"])
            facts, marks = _board_facts(idx, day, asof, fr)
            tr, tr_why = _board_trend(idx, day, asof)
            doc = board.read(core["minutes"], core["peak"], core["opens"], facts, marks, tr,
                             first=core["first"], idx=idx, g=core["g"], evs=core["evs"], trend_why=tr_why,
                             levels=lv, hilo=_board_hilo(idx, day, asof))
            base = _BOARD["base"][idx] = {"key": key, "doc": doc}
        mir = ({"ok": False, "why": far, "tag": "M"} if far else _board_mirror(idx, asof, kce, kpe))
        mir.update(strikes={"CE": kce, "PE": kpe}, atm=atm, span=BOARD_MIRROR_SPAN)
        out = json.dumps({**base["doc"], "idx": idx, "day": day, "built_at": time.time(),
                          "mirror": mir, "not_shown": _BOARD_NOT_SHOWN,
                          "note": "display only [I] on [M] facts; nothing here gates anything"},
                         default=str).encode()
        if hit.get("key") != key:
            hit = {"key": key}
        hit[(kce, kpe)] = out
        _BOARD["reply"][idx] = hit
        return out


# ---- THE SIDES READ (sides.py rev sides-2; docs/board/real-vs-fake-2026-10-03.md §2a) ----
#
# Per index, per CLOSED 5-minute slot: the call side and the put side on her nine
# strikes, read separately against the index move, off the SAME grid and marks the
# OI Flow tab reads (ChainState.minutes and its oi_flow). The forced chip reads the
# saved chain snapshot at each mark (BookTail on today's data/chain file); the morning
# is sized against the previous session's saved chain ("kal ka scale"). DISPLAY ONLY:
# nothing here feeds a gate, the zone machine or trigger_log.
#
# ANYTIME START. A restart's warm start replays today's saved chain into the same grid
# and chain_backfill rebuilds any hole from REST, so a server started at 11:00 reads
# every slot since 09:15 again, exactly; slots that opened before this process started
# (or touch a REST-rebuilt minute) say src "backfill", never "live".
_SIDES_CACHE, _SIDES_TAIL, _SIDES_KAL = {}, {}, {}
_SIDES_KAL_LOCK = threading.Lock()


def _sides_kal(idx, day):
    """The previous session's scale for `idx` (sides.day_scale on its saved chain), once per day."""
    from chain_live import CHAIN_DIR
    with _SIDES_KAL_LOCK:
        if (idx, day) in _SIDES_KAL:
            return _SIDES_KAL[(idx, day)]
        got = None
        try:
            prev = sides_log.prev_session_path(CHAIN_DIR, idx, day)
            if prev:
                info = {}
                m, o, _bk = sides_log.load_session(prev[1], info)
                import chain_backfill   # the REST walk's marks (09:15-09:16) the poller never saw, as the frozen runs read them
                for t, rec in chain_backfill.read_grid(prev[0], idx).items():
                    m.setdefault(t, rec)
                g = chain_metrics.ChainState()
                g.minutes = m
                sc = sides.day_scale(sides.read(g.oi_flow(interval=sides.INTERVAL), m, opens=o))
                # rev sides-3 (B3): a previous session that was this index's expiry day is not a like
                # for a fresh-series morning; its own saved snapshots say which expiry they were on
                exp = info.get("expiry")
                got = dict(sc, day=prev[0], expiry=exp, expiry_day=(exp == prev[0]) if exp else None)
        except Exception:
            log.exception("sides previous-session scale %s", idx)
        _SIDES_KAL[(idx, day)] = got
        return got


def _sides_book(idx, day):
    """The saved chain snapshot at each 5-minute mark today, followed incrementally."""
    from chain_live import CHAIN_DIR
    tail = _SIDES_TAIL.get(idx)
    if tail is None or tail.day != day:
        tail = sides_log.BookTail(str(CHAIN_DIR / f"chain_{idx}_{day}.jsonl"))
        tail.day = day
        _SIDES_TAIL[idx] = tail
    return tail.read()


def _sides_state(poller, chains, idx, today, hhmm, live_from):
    """(public reply for one index, the grid and opens it was read from)."""
    st = (getattr(poller, "states", None) or {}).get(idx) if poller else None
    if st is None:
        return {"ok": False, "why": sides.CC + "the chain poller has no state for this index yet"}, None, None
    chain_ok, chain_why, expiry, grid_day = True, None, None, None
    box = (chains or {}).get(idx)
    try:
        pl = json.loads(box["payload"]) if box and box.get("payload") else None
    except (ValueError, TypeError):
        pl = None
    if pl is None:
        chain_ok, chain_why = False, "chain poller warming up"
    else:
        expiry = pl.get("expiry")
        if pl.get("ok", True):
            if isinstance(pl.get("built_at"), (int, float)):
                grid_day = time.strftime("%Y-%m-%d", time.localtime(pl["built_at"]))
        else:
            chain_ok, chain_why = False, pl.get("error") or "the chain is unavailable"
    mins = dict(getattr(st, "minutes", None) or {})      # one copy: the poller keeps writing
    day = grid_day or today
    now = hhmm if day == today else None                 # a past session: every mark is closed
    lf = live_from if day == today else None
    opens = _board_opens(poller, idx)
    book = _sides_book(idx, day)
    kal = _sides_kal(idx, day)
    key = (idx, day, len(mins), max(mins) if mins else None, now, lf, len(book), bool(kal), len(opens))
    hit = _SIDES_CACHE.get(idx)
    if hit is None or hit["key"] != key:
        g = chain_metrics.ChainState()
        g.minutes = mins
        slots = sides.read(g.oi_flow(interval=sides.INTERVAL), mins, now=now, live_from=lf,
                           opens=opens, book=book, kal=kal)
        hit = _SIDES_CACHE[idx] = {"key": key, "slots": slots}
    slots = hit["slots"]
    dte = None
    try:
        if expiry:
            from datetime import date
            dte = (date.fromisoformat(expiry) - date.fromisoformat(day)).days
    except ValueError:
        dte = None
    pub = {"ok": True, "day": day, "grid_day": grid_day, "expiry": expiry, "dte": dte,
           "expiry_day": bool(expiry) and expiry == day, "chain_ok": chain_ok, "chain_why": chain_why,
           "live_from": lf, "kal": kal, "kal_why": None if kal else sides.NO_KAL, "slots": slots,
           "why": None if slots else (sides.CC + (chain_why or "no minute on the grid yet") if not chain_ok
                                      else "checked, none yet — the first slot closes at 09:20")}
    return pub, mins, opens


def _sides_reply(poller, chains, want=None, _internal=None):
    """GET /api/sides: every closed slot today per index, and the three indices' two lines."""
    today, hhmm = _board_clock()
    up = time.localtime(_STARTED)
    live_from = time.strftime("%H:%M", up) if time.strftime("%Y-%m-%d", up) == today else None
    out = {}
    for i in instruments.ENABLED:
        if want in (None, i):
            pub, mins, opens = _sides_state(poller, chains, i, today, hhmm, live_from)
            out[i] = pub
            if _internal is not None:
                _internal[i] = (mins, opens)
    reads = {i: x["slots"] for i, x in out.items() if x.get("ok")}
    meta = {i: {"dte": x.get("dte"), "expiry_day": x.get("expiry_day")} for i, x in out.items() if x.get("ok")}
    return {"ok": True, "rev": sides.REV, "defs": sides.DEFS, "now": hhmm, "indices": out,
            "three": sides.three(reads, meta) if want is None else None,
            "note": "display [I] on [M] OI, premiums and prints; counts, never odds; gates nothing"}


_SIDES_DROP = ("ce", "pe", "move")       # the face's nested copies; the log keeps the flat fields


def _sides_loop(poller, chains):
    """The forward log (Fable §5's spec): every 10 s in market hours, each index's newly CLOSED slots
    as kind "slot" rows (every slot, with the three indices' counts and §1d's leader at that mark),
    and each slot's outcome as a kind "outcome" row once t+30 has closed. Once each; the guard
    (market hours, weekdays, today's own session) lives in sides_log.append."""
    from chain_live import IST
    from datetime import datetime
    while True:
        time.sleep(10)
        now = datetime.now(IST)
        if not sides_log.may_write(now, now.strftime("%Y-%m-%d"))[0]:
            continue
        grids = {}
        try:
            rep_ = _sides_reply(poller, chains, None, grids)
        except Exception:
            log.exception("sides read failed")
            continue
        reads = {i: x["slots"] for i, x in rep_["indices"].items() if x.get("ok")}
        hm = now.strftime("%H:%M")
        for idx, x in rep_["indices"].items():
            if not (x.get("ok") and x.get("grid_day")):      # only a grid the chain built TODAY is written
                continue
            try:
                mins, opens = grids.get(idx) or ({}, {})
                day = x["grid_day"]
                new = sides_log.unwritten(day, idx, "slot", [s["t"] for s in x["slots"]])
                rows = []
                for s in x["slots"]:
                    if s["t"] in new:
                        rows.append({**{k: v for k, v in s.items() if k not in _SIDES_DROP},
                                     "expiry": x.get("expiry"), "dte": x.get("dte"), "expiry_day": x.get("expiry_day"),
                                     **sides.cross_at(reads, s["t"]), **sides.board_at(mins, opens, s["t"])})
                closed = [s for s in x["slots"] if sides._hm(sides._mm(s["t"]) + 30) < hm]
                todo = sides_log.unwritten(day, idx, "outcome", [s["t"] for s in closed])
                rows += [sides.outcome(mins, s["t"], s.get("pdir"), x.get("live_from"))
                         for s in closed if s["t"] in todo]
                sides_log.append(day, idx, rows, now)
            except Exception:
                log.exception("sides log failed %s", idx)


# ---- THE TRAP LAYER (trap.py rev trap-1; docs/board/TRAP-PREREG-2026-10-04.md) ----
#
# SHADOW, [I]: display and log only; it changes no verdict, word or count. One thread reads every
# index every TRAP_EVERY_S from the sides slots above (cached) and the recorders' own files --
# warmap's stamps, the reader's legs, xindex, the NIFTY tape, senses, yesterday's saved chain --
# followed incrementally by trap_log.Day, so a restart rebuilds the day exactly from disk (the
# anytime-start rule). The endpoint is a dict lookup. In market hours the same pass writes
# data/trap/: state rows once per key, slot rows once per closed slot, outcome rows after t+30,
# under sides_log's guard; an index's rows wait until the war map has rebuilt its morning.
_TRAP = {"D": None, "reply": None}
TRAP_EVERY_S = 15


def _trap_day(day):
    """The day's incremental readers, at the recorders' own folders (a mock run's are followed)."""
    import sequence as sequence_mod
    from chain_live import CHAIN_DIR
    D = _TRAP["D"]
    if D is None or D.day != day:
        D = _TRAP["D"] = trap_log.Day(day, chain_dir=str(CHAIN_DIR), vpin_path=VPIN_FAST_LOG, dirs={
            "warmap": sequence_mod.DIR, "reader": reader_live.DIR, "xindex": xindex_live.DIR,
            "tape": tape_log.DIR, "senses": senses_mod.DIR})
    return D


def _trap_compute(poller, chains):
    """Every index's trap read now -> (the public reply, {idx: (sides reply, grid minutes, read, war map rebuilt)})."""
    today, hhmm = _board_clock()
    grids = {}
    rep_ = _sides_reply(poller, chains, None, grids)
    wm = getattr(_SENSES.get("warmap"), "_by", None) or {}
    out, raw = {}, {}
    for idx, x in rep_["indices"].items():
        if not x.get("ok"):
            out[idx] = {"ok": False, "why": x.get("why") or trap.CC + "the sides read is not ready"}
            continue
        day = x["day"]
        D = _trap_day(day)
        mins = (grids.get(idx) or ({}, {}))[0] or {}
        fp = next((mins[t]["spot"] for t in sorted(mins) if (mins[t] or {}).get("spot") is not None), None)
        lv = _board_levels(idx) if day == today else None
        prev, legs, xin, tape = D.oi_prev(idx), D.legs(idx), D.xin(), D.tape(idx)
        stamps = D.stamps()
        r = trap.read(idx, stamps, x["slots"], now=hhmm if day == today else None,
                      static={L["kind"]: L["px"] for L in lv} if lv else None, first_print=fp,
                      legs=legs, xin=xin, tape=tape, pulled=D.pulled(idx), oi_prev=(prev or {}).get("k"),
                      book=_sides_book(idx, day), live_from=x.get("live_from"))
        bf = getattr(wm.get(idx), "backfill", None) or {}
        rebuilt = bool(bf.get("done")) or day != today
        raw[idx] = (x, mins, r, rebuilt)
        out[idx] = {
            "ok": True, "day": day, "live_from": x.get("live_from"), "lines": r["lines"], "events": r["events"],
            "releases": r["releases"], "slots": r["slots"], "traps": list(r["traps"].values()),
            "levels": "the war map's static levels" if lv else "from the stamps (the war map's daily levels are not in)",
            "stamps_why": (None if r["events"] or r["traps"] else trap.CC + "the war map has stamped no level today")
            if rebuilt else trap.CC + "the war map is still rebuilding the morning (" + str(bf.get("why")) + ")",
            "who_why": None if legs is not None else "check nahi (reader log nahi)",
            "xindex_why": None if xin is not None else "check nahi (xindex log nahi)",
            "tape_why": (trap.TAPE_THIN if idx not in trap.WEEKLY_TAPE else
                         None if tape else trap.CC + "no NIFTY tape file today"),
            "oi_prev_day": (prev or {}).get("day"),
            "oi_prev_why": None if prev else trap.CC + "no saved chain for the previous session",
        }
    return {"ok": True, "rev": trap.REV, "fixed_at": trap.FIXED_AT, "now": hhmm, "at": time.strftime("%H:%M:%S"),
            "indices": out, "three": rep_.get("three"), "tag": "I", "shadow": True,
            "note": "SHADOW [I] — display and log only; changes no verdict, word or count; f15/f30 are logged, never shown"}, raw


def _trap_write(raw, now):
    """The forward log (prereg §4), once per key, for a grid the chain built TODAY only."""
    hm = now.strftime("%H:%M")
    for idx, (x, mins, r, rebuilt) in raw.items():
        if not (x.get("grid_day") and rebuilt):
            continue
        day = x["grid_day"]
        try:
            rows = [dict(e, key=f"{e['t']}|{trap.level_key(e['level'], e['px']) if e.get('px') is not None else '-'}"
                                f"|{e['state']}") for e in r["events"]]
            rows += r["slots"]
            closed = [q for q in r["releases"] if sides._hm(sides._mm(q["t"]) + 30) < hm]
            todo = trap_log.unwritten(day, idx, "outcome", [q["t"] for q in closed])
            rows += [dict(sides.outcome(mins, q["t"], q["dir"], x.get("live_from")), level=q["level"], px=q["px"],
                          dir=q["dir"], tag="M") for q in closed if q["t"] in todo]
            trap_log.append(day, idx, rows, now)
        except Exception:
            log.exception("trap log failed %s", idx)


def _trap_loop(poller, chains):
    from chain_live import IST
    from datetime import datetime
    while True:
        try:
            rep_, raw = _trap_compute(poller, chains)
            _TRAP["reply"] = rep_
            now = datetime.now(IST)
            if sides_log.may_write(now, now.strftime("%Y-%m-%d"))[0]:
                _trap_write(raw, now)
        except Exception:
            log.exception("trap read failed")
        time.sleep(TRAP_EVERY_S)


# ---- THE HOLD / FOLD WINDOW (docs/hold/PREREG-merged.md rev 4; hold.py) ----
#
# Per-minute facts per index, CACHED and extended a minute at a time: one
# record per finished minute from the same pure functions /api/board calls
# (fronts, board, grounds, trendbox), in the shape hold.py reads -- the loop
# body of docs/hold/opus/scratch/build_facts.py, which matched /api/oihist on
# 373 of 373 minutes. A request is a dict lookup plus hold.read over <= 375
# small records; nothing re-parses a day file (a 55 MB per-POST parse once
# wedged this server). The running session-peak OI at a past minute is the
# open plus the running high change on the grid's marks -- board.first_fold's
# own ranking -- so a restart re-reads any past minute identically. DISPLAY
# ONLY: nothing here feeds setup.gate, the zone machine or trigger_log.
_HOLD = {"facts": {}, "locks": {}, "trades": [], "trades_day": None, "sigma": {}, "peaks": {}}
HOLD_TRACK = 30          # §8: a side stamp's strike, tracked for its next 30 finished minutes
HOLD_TRADES_LOCK = threading.Lock()


def _hold_front(f):
    if not f:
        return None
    return {"side": f["side"], "k": f["k"], "state": f["state"], "built": f["peak"] > 0,
            "chg": round(f["chg"]), "peak": round(f["peak"]), "peak_at": f["peak_at"],
            "words": board.state_words(f)}


def _hold_rec(t, core, jx, ux, trd, c1, ix, peaks):
    """One finished minute's facts, every input cut to `t`."""
    minutes, g, evs = core["minutes"], core["g"], core["evs"]
    rec, fr, j = {"t": t}, [], None
    cut = fronts.cut(minutes, t)
    marks = sorted(cut)
    if not marks:
        rec["blind"] = board.CC + "no chain mark yet today"
    else:
        # A mark the poller wrote without a spot: fronts.read cannot judge nearness there (fronts.grid
        # skips it), so the minute reads blind. Live 2026-09-25 its float() raised, and every hold read
        # and log row of SENSEX and BANKNIFTY that day was lost with it.
        s = cut[marks[-1]].get("spot")
        if s is not None:
            s = float(s)
            rec["spot"] = round(s, 2)
        sw = fronts.stale(cut, t)
        if sw:
            rec["blind"] = board.CC + sw
        elif s is None:
            rec["blind"] = board.CC + f"no spot on the {marks[-1]} chain mark"
        elif len(marks) < fronts.SLOPE_MARKS:
            rec["blind"] = (board.CC + "fronts forming: the build → stall → unwind sequence needs "
                            f"{fronts.SLOPE_MARKS} one-minute marks, {len(marks)} so far")
        j = jx.get(marks[-1])
        if peaks:                            # the running session high as it stood at this mark, exactly
            pk = peaks.get(marks[-1], {})    # a backfilled mark the record never saw ranks by its own build, as build_facts did
        else:                                # no chain record: board.first_fold's open + running high on the marks
            pk = dict(core["peak"])
            for (k, side), rp in (g[4].items() if j is not None else ()):
                o = core["opens"].get((k, side.lower()))
                if o is not None:
                    pk[(k, side.lower())] = o + rp[j]
        fr = fronts.read(cut, pk)
        rec["fr"] = [{"k": f["k"], "side": f["side"], "state": f["state"], "built": f["peak"] > 0}
                     for f in fr]                # PLAN §2.2: the top 2 per side, for the rung
        if fr:
            rec["CE"], rec["PE"] = _hold_front(board.nearer(fr, "CE", s)), _hold_front(board.nearer(fr, "PE", s))
        else:
            rec.setdefault("blind", board.CC + "near-ATM fronts not read")
        rec["folds"] = [{"k": e["k"], "side": e["side"], "t": e["t"], "off": e["off"], "high_at": e["high_at"],
                         "still": board.still_folded(e, j, g[3], g[4], jx)}
                        for e in evs if j is not None and jx[e["t"]] <= j
                        and board.mm(t) - board.mm(e["t"]) <= hold.FOLD_LIVE]
    now = board.mm(t)
    bt = [b for b in ux["bars"] if b.get("t") is not None and board.mm(grounds._hh(b["t"])) + 4 <= now]  # a bar starting at m has closed by the END of finished minute m + 4 (2026-09-28 audit, bug 9; = board._closed)
    rt = [r for r in ux["runs"] if r.get("from_t") is None or grounds._hh(r["from_t"]) <= t]
    F = grounds.facts(bt, rt, fr, runs_why=ux["runs_why"], roll=_roll_why(core.get("idx"), core["day"]), idx=core.get("idx"))
    if not bt and ux["why"]:
        F["cvd_why"] = F["flow_why"] = ux["why"]
    c, fl = F.get("cvd"), F.get("flow")
    rec["cvd"] = c and {"d": round(c["d"]), "rank": c["rank"], "rank_why": c.get("rank_why"),
                        "dpx": c["dpx"], "since": c["since"],
                        "dt": c["div_top"], "db": c["div_bottom"]}
    rec["cvd_why"] = None if c else board.CC + (F.get("cvd_why") or "no ladder bars")
    rec["flow"] = fl and {"b": fl["buy"], "s": fl["sell"], "rw": fl.get("runs_why")}
    rec["flow_why"] = None if fl else board.CC + (F.get("flow_why") or "no prints")
    trr = trendbox.rows(trd["m1_prior"], c1, trd["m30"], trd["d1"], core["day"], t) if trd and c1 else None
    rec["tr"] = {k: trr["rows"][k]["word"] for k in hold.ROWS} if trr else None
    rec["tr_why"] = None if trr else board.CC + (ux["tr_why"] or f"no index candle at or before {t} today")
    x = ix.get(t)
    rec["ix"] = [x[3], x[1], x[2]] if x else None
    return rec


def _hold_peaks(idx, day):
    """{HH:MM: {(k, "ce"|"pe"): session-high OI as of that minute's last snapshot}} off
    the day's own chain record -- ChainState.peak as it stood at each minute, exactly
    ("the peak as of t, never the day's end", §2; build_facts.read_chain's reading,
    which matched /api/oihist). The grid's minute marks cannot give it: they miss an
    intra-minute high, and a strike that has left the chain window has no open. Read
    once, then only the lines appended since -- a few KB a minute, never a whole-file
    parse per request. {} when there is no record."""
    from chain_live import CHAIN_DIR
    st = _HOLD["peaks"].get(idx)
    if st is None or st["day"] != day:
        st = _HOLD["peaks"][idx] = {"day": day, "off": 0, "run": {}, "by_t": {}, "greeks": {}}
    try:
        with open(CHAIN_DIR / f"chain_{idx}_{day}.jsonl", "rb") as f:
            f.seek(0, 2)
            if f.tell() < st["off"]:                 # the record was rewritten: read it again
                st.update(off=0, run={}, by_t={}, greeks={})
            f.seek(st["off"])
            data = f.read()
    except OSError:
        return st["by_t"]
    end = data.rfind(b"\n") + 1                     # a line the poller is still writing waits for the next read
    run = st["run"]
    for line in data[:end].splitlines():
        try:
            s = json.loads(line)
        except ValueError:
            continue
        m = (s.get("ts") or "")[:5]
        if not ("09:15" <= m < "15:30") or s.get("spot") is None:
            continue
        gk = st["greeks"].setdefault(m, {})          # PLAN §2.1: the broker's greeks, last snapshot of the minute
        for row in s.get("strikes") or []:
            ce, pe = row.get("ce") or {}, row.get("pe") or {}
            gk[float(row["k"])] = (ce.get("delta"), ce.get("gamma"), pe.get("delta"), pe.get("gamma"))
            for side in ("ce", "pe"):
                oi = (row.get(side) or {}).get("oi")
                if isinstance(oi, (int, float)):
                    key = (float(row["k"]), side)
                    run[key] = max(run.get(key, 0.0), float(oi))
        st["by_t"][m] = dict(run)
    st["off"] += end
    return st["by_t"]


def _hold_greeks(idx, day, k, side, n):
    """[(delta, gamma) | None] for the first n session minutes: the broker's greeks for
    her strike-side at the latest chain snapshot at or before each minute [M] (the
    record _hold_peaks reads). None before the strike first appears -- never a zero."""
    st = _HOLD["peaks"].get(idx) or {}
    by = (st.get("greeks") or {}) if st.get("day") == day else {}
    j, out, last = (0 if side == "CE" else 2), [], None
    for t in hold.SESSION[:n]:
        g = (by.get(t) or {}).get(float(k))
        if g and g[j] is not None and g[j + 1] is not None:
            last = (g[j], g[j + 1])
        out.append(last)
    return out


def _hold_expiry(poller, idx):
    """§10.3: the chain poller's resolved expiry for `idx` (the frame head's expiry is
    this same value, handed on), or None -- never the live instrument dump."""
    r = (getattr(poller, "resolved", None) or {}).get(idx)
    if isinstance(r, dict) and r.get("expiry"):
        return r["expiry"]
    box = (getattr(poller, "boxes", None) or {}).get(idx) or {}
    try:
        pl = box.get("payload")
        return json.loads(pl).get("expiry") if isinstance(pl, (bytes, str)) else None
    except (ValueError, AttributeError):
        return None


HOLD_REFETCH_S = 15      # a late index candle is asked for again at most this often


def _hold_candles(idx, day, asof):
    """(prior sessions' candles, today's index 1-min, why) -- the trend box's REST,
    off /api/board's own cache (fetched once per grid minute). Upstox serves a minute's
    candle a minute or more late (live 2026-09-25), and the board's one fetch per minute
    usually lands before it; so while the newest minute's candle is missing, today's
    1-min is asked again at most every HOLD_REFETCH_S, into the hold's own cache (the
    board's is not touched). One seam for tests."""
    _tr, why = _board_trend(idx, day, asof)
    trd, c1 = (_BOARD["trend_day"].get(idx) or {}).get("data"), (_BOARD["trend_1m"].get(idx) or {}).get("c")

    def newest(c):
        return max((r[1] for r in trendbox.candles(c or []) if r[0] == day), default="")
    mine = _HOLD.setdefault("c1", {})
    h = mine.get(idx) if (mine.get(idx) or {}).get("day") == day else None
    if h and newest(h["c"]) > newest(c1):
        c1 = h["c"]
    if c1 is not None and newest(c1) < asof and (h is None or time.time() - h["at"] >= HOLD_REFETCH_S):
        mine[idx] = {"day": day, "at": time.time(), "c": c1}     # claimed first: a read meanwhile does not ask too
        import upstox_feed
        import upstox_rest
        try:
            fresh = upstox_rest.intraday(upstox_instruments.index_key(idx), upstox_feed.read_token())
        except Exception:                    # a failed re-ask costs nothing: the board's candles stand
            fresh = None
        if fresh and newest(fresh) > newest(c1):
            c1 = fresh
        mine[idx] = {"day": day, "at": time.time(), "c": c1}
    return trd, c1, why


def _hold_land(idx, day):
    """rev 5 §A.0.4, per index, kept in day state so a restart re-reads what was read live (the record alone
    would read every late close as if on time): `late` {HH:MM: {read_at}} -- a candle first read after its own
    minute, at the first finished minute whose facts carried it -- or {read_at: None, backfill: HH:MM} -- a
    close no live read ever carried, first read from a restart's backfill; `blind` the minutes read without
    their candle and still waiting; `live_to` the latest minute read live. `boot`, this process's first read
    of the day, is not kept: a restart is a new boot."""
    land = _HOLD.setdefault("land", {})
    lnd = land.get(idx)
    if lnd is None or lnd.get("day") != day:
        lnd = land[idx] = {"day": day, "late": {}, "blind": [], "live_to": None, "boot": None}
    return lnd


def _hold_late(idx, day):
    return _hold_land(idx, day)["late"]


def _hold_frozen(tr):
    """rev 5 §A.0.4 / §G: a marked trade's B reads from day state (None for a query, a check or an import)."""
    return _HOLD.setdefault("frozen_b", {}).get(tr["id"]) if tr.get("src") == "marked" else None


def _hold_freeze(tr, reads):
    """Each B read of a marked trade (L, its set / trail minute, B, B_at, the level in force, clamped) is
    written ONCE into day state and read back on a restart (rev 5 §A.0.4, §G)."""
    if tr.get("src") != "marked" or not reads:
        return
    have = _HOLD.setdefault("frozen_b", {}).setdefault(tr["id"], [])
    keys = {(round(b["L"], 2), b["L_at"]) for b in have}
    new = [dict(b) for b in reads if (round(b["L"], 2), b["L_at"]) not in keys]
    if new:
        have.extend(new)
        _HOLD["dirty"] = _HOLD["land_new"] = True


def _hold_facts(poller, idx):
    """The day's per-minute records for `idx`, 09:15 .. the latest finished minute,
    built once and extended a minute at a time. None before the grid has a mark."""
    core = _board_core(poller, idx)
    if core is None or not core["g"][0]:
        return None
    day, asof = core["day"], core["asof"]
    # The candles OUTSIDE the lock (REVIEW P1-18): a late candle's REST re-ask (30 s timeout) must not
    # queue every /api/hold and /api/hold/check on this index behind it. The lock guards the cache.
    trd, c1, tr_why = _hold_candles(idx, day, asof)
    with _HOLD["locks"].setdefault(idx, threading.Lock()):
        # A MINUTE IS FINISHED WHEN ITS INDEX CANDLE HAS LANDED. Live 2026-09-25 11:58: Upstox had
        # served candles to 11:56 while the grid held 11:57, so reading 11:57 blinded the line (PATA
        # NAHI) and would have written that blindness into the write-once logs. The read waits for
        # the candle -- at most fronts.STALE_MIN minutes; a candle feed further behind is stale, and
        # the minute reads blind and says so.
        newest = max((r[1] for r in trendbox.candles(c1 or []) if r[0] == day and r[1] <= asof), default=None)
        if newest and newest < asof and hold.mm(asof) - hold.mm(newest) <= fronts.STALE_MIN:
            asof = newest
        n_at = sum(1 for t in core["minutes"] if t <= asof)
        key = (day, asof, n_at, trd is not None, c1 is not None)
        hit = _HOLD["facts"].get(idx)
        if hit is not None and hit["key"] == key:
            return hit
        prev = hit if hit is not None and hit["day"] == day else None
        recs = dict(prev["recs"]) if prev else {}
        if prev and sum(1 for t in core["minutes"] if t <= prev["asof"]) != prev["n"]:
            recs = {}                    # a backfill landed under minutes already read: read them again
        try:
            tape = _tape_reply(idx, day)
        except Exception as e:           # a disk fault costs the facts, never the window
            tape = {"ok": False, "why": f"tape record unreadable: {type(e).__name__}: {e}"}
        u = (tape.get("ux") or {}) if tape.get("ok") else {}
        mk = u.get("marks") or {}
        ux = {"bars": u.get("bars") or [], "runs": mk.get("runs") or [], "runs_why": mk.get("runs_why"),
              "why": u.get("why") if tape.get("ok") else (tape.get("why") or "no prints record"),
              "tr_why": tr_why}
        jx = {t: j for j, t in enumerate(core["g"][0])}
        ix = {r[1]: r[2:] for r in trendbox.candles(c1 or []) if r[0] == day}
        peaks = _hold_peaks(idx, day)
        # A ladder bar or fill run that lands after a minute was first read (a drain a moment late, the
        # run detector re-fed after a restart) must reach that minute, as a restart would read it: each
        # minute keeps the counts it was read with -- bars closed by t, runs begun by t, _hold_rec's own
        # cuts -- and is read again when they move. Rows already logged stay as written (write-once).
        from bisect import bisect_right
        ends = sorted(board.mm(grounds._hh(b["t"])) + 4 for b in ux["bars"] if b.get("t") is not None)   # = _hold_rec's cut
        starts = sorted(grounds._hh(r["from_t"]) for r in ux["runs"] if r.get("from_t") is not None)
        seen = dict(prev.get("seen") or {}) if prev else {}
        land = _hold_land(idx, day)
        boot = land["boot"] is None
        if boot:                         # rev 5 §A.0.4: this process's first read of today. A close that no live read
            land["boot"] = asof          # ever carried (the server was down across it) is read from backfill: at its
            for t in hold.SESSION:       # own bar, and tagged so, never blended with a close read live.
                if t >= asof:
                    break
                if (hold.is_close(t) and t in ix and t not in land["late"]
                        and (land["live_to"] is None or t > land["live_to"] or t in land["blind"])):
                    land["late"][t] = {"read_at": None, "backfill": asof}
                    _HOLD["dirty"] = _HOLD["land_new"] = True
        for t in hold.SESSION:
            if t > asof:
                break
            n = (bisect_right(ends, hold.mm(t)), bisect_right(starts, t) + len(ux["runs"]) - len(starts))
            r = recs.get(t)
            if r is None or (r["tr"] is None and trd and c1) or (r["ix"] is None and t in ix) or seen.get(t) != n:
                recs[t] = _hold_rec(t, core, jx, ux, trd, c1, ix, peaks)
                seen[t] = n
            if recs[t]["ix"] is None:    # read without its candle: when it lands it is read late, never back-dated
                if t not in land["blind"]:
                    land["blind"].append(t)
            elif t in land["blind"]:
                land["blind"].remove(t)
                if not boot and t not in land["late"]:
                    land["late"][t] = {"read_at": asof}      # the first finished minute whose facts carry it
                    _HOLD["dirty"] = _HOLD["land_new"] = True
        land["live_to"] = max(land["live_to"] or asof, asof)
        exp = _hold_expiry(poller, idx)
        out = {"key": key, "day": day, "asof": asof, "n": n_at, "recs": recs, "seen": seen, "core": core,
               "pivots": hold.pivots(c1 or [], day, asof),
               "expiry": hold.expiry_line(idx, day, exp, "the chain poller's resolved expiry"),
               "src": {"grid": f"chain poller grid, {len(core['g'][0])} marks to {asof}",
                       "ladder": (f"{len(ux['bars'])} ladder bars, {len(ux['runs'])} fill runs"
                                  + (f" ({ux['runs_why']})" if ux["runs_why"] else "") if ux["bars"]
                                  else board.CC + str(ux["why"] or "no ladder bars")),
                       "trend": "Upstox index candles (REST)" if c1 and trd else board.CC + str(tr_why)}}
        _HOLD["facts"][idx] = out
        return out


def _hold_minutes(F):
    return [F["recs"][t] for t in hold.SESSION if t <= F["asof"]]


def _hold_prem(F, k, side):
    """The held contract's premium per minute [I]: the chain poller's last LTP of each
    minute (a restart's backfill fills the same key); open = the previous close."""
    mins, c = F["core"]["minutes"], []
    for t in hold.SESSION:
        if t > F["asof"]:
            break
        cell = fronts._at((mins.get(t) or {}).get("px"), k)
        v = cell[0 if side == "CE" else 1] if isinstance(cell, (list, tuple)) and len(cell) == 2 else None
        c.append(float(v) if isinstance(v, (int, float)) and v > 0 else None)
    return {"c": c, "o": [None] + c[:-1], "src": "I"} if any(v is not None for v in c) else None


def _hold_sigma(idx, k, side, asof):
    """The premium against its own session VWAP, in σ [M] -- /api/contract's assembly
    on REST 1-min candles, once per contract per minute. Footer only; never an input."""
    hit = _HOLD["sigma"].get((idx, k, side))
    if hit and hit["asof"] == asof:
        return hit["out"]
    import live
    try:
        b = live.build_contract(idx, strike=k, side=side, interval=1)
        bars, vw = b.get("bars") or [], b.get("vwap") or []
        i = next((i for i in range(len(bars) - 1, -1, -1) if (bars[i] or {}).get("t") == asof), None)
        if i is None or not vw[i] or vw[i].get("vwap") is None or not vw[i].get("u1"):
            out = {"why": board.CC + f"no {asof} candle for this contract from REST yet", "tag": "M"}
        else:
            sd = vw[i]["u1"] - vw[i]["vwap"]
            out = {"vwap": round(vw[i]["vwap"], 2), "z": round((bars[i]["c"] - vw[i]["vwap"]) / sd, 1) if sd else None,
                   "c": bars[i]["c"], "tag": "M"}
    except Exception as e:                   # the footer's σ failing costs the σ, never the window
        out = {"why": board.CC + f"premium candles: {type(e).__name__}: {e}", "tag": "M"}
    _HOLD["sigma"][(idx, k, side)] = {"asof": asof, "out": out}
    return out


def _hold_trades():
    """Today's marked trades; restored from data/day_state/ on a restart."""
    day = _board_clock()[0]
    if _HOLD["trades_day"] != day:
        _HOLD["trades"], _HOLD["trades_day"] = [], day
    return _HOLD["trades"]


_HOLD2 = {"refs": {}, "closes": {}, "out": {}, "busy": set(), "shadow": {}}
SHADOW_DIR = os.path.join("data", "hold")        # holdshadow's forward log, shadow_<day>.jsonl (_shadow_log)
_SHADOW_SEEN = {}                                # path -> {(trade id, line)} already on disk
_HOLD2_LOCK = threading.Lock()


def _hold2(rep, trades):
    """HOLD v2 (hold2.py, research-findings §1m) for her open marked trade on /api/fold?id=: DISPLAY ONLY -- a block
    beside the reply, which never reads or changes the window's HOLD / FOLD word. Computed off the request thread at most
    once a minute per trade, from memory (the fold engine's 1-min bars and chain rows, the ux / GoCharting 5-min bars) and
    the push references (the prior days' tape files, read once per index-day); a request gets the last block, or why
    there is none yet."""
    tr = next((t for t in trades if t["id"] == rep.get("id")), None)
    if tr is not None and tr.get("exit_t"):          # her exit: the shadow lines still undecided are logged as they stood
        with _HOLD2_LOCK:
            hit = _HOLD2["out"].get(tr["id"])
        if hit and (hit[1] or {}).get("shadow"):
            _shadow_log(_board_clock()[0], tr, hit[1]["shadow"], at_exit=True)
    if tr is None or tr.get("exit_t") or not rep.get("ok") or (rep.get("view") or {}).get("frozen"):
        return None
    lt = time.localtime()
    m, key = lt.tm_hour * 60 + lt.tm_min, tr["id"]
    with _HOLD2_LOCK:
        hit = _HOLD2["out"].get(key)
        if (hit is None or hit[0] != m) and key not in _HOLD2["busy"]:
            _HOLD2["busy"].add(key)
            threading.Thread(target=_hold2_run, args=(tr, rep["view"], m), name=f"hold2-{key}", daemon=True).start()
    return hit[1] if hit else {"ok": False, "tag": "I", "text": None,
                               "why": "could not check — HOLD v2 is reading the day (first look)"}


def _hold2_run(tr, view, m):
    key, idx = tr["id"], tr["idx"]
    try:
        got = fold_live.hold2_rows(idx)
        if got is None:
            out = {"ok": False, "tag": "I", "text": None, "why": "could not check — the fold engine has no market read yet"}
        else:
            day, bars1, chain_rows, tape = got
            if (idx, day) not in _HOLD2["refs"]:
                _HOLD2["refs"][(idx, day)] = confluence_log.push_refs(idx, day)
            refs, rwhy = _HOLD2["refs"][(idx, day)]
            bars5 = confluence_log.push_bars(idx, day, gc_rows=tape, ux_rows=_ux_bars(idx, day))
            fl = sensex_flow.on(idx)             # SENSEX-NIFTY-FLOW §1.2 (signed 25 Oct): NIFTY's pushes move the SENSEX line
            if fl:
                P, pwhy, skip = sensex_flow.line(*_nifty_pushes(day), bars5)
            out = hold2.live(tr, view, m, bars1, chain_rows, bars5, None if fl else refs, pwhy if fl else rwhy,
                             _HOLD2["closes"].setdefault((day, key), {}), pushes_=P if fl else None)
            if fl:
                sensex_flow.stamp(out, skip, tr["t0"], m)
            if out.get("text"):                  # A25, display only: SENSEX futures are too thin (the line is spot|fut)
                import decode
                out["text"] += decode.patla_of(idx, bars5)
            try:
                dec = holdshadow.dec_rows(confluence_log._rows(os.path.join(DECODE_DIR, f"decode_{day}.jsonl")), idx)
            except Exception:                    # a torn DECODE log costs the effort reads, never HOLD v2
                log.exception("decode rows")
                dec = {}
            try:                                 # THE TRADE MAP (trademap.py): l4 / l5 / detail for the one voice, display only
                gc_t = max((b["t"] for b in tape or () if isinstance(b.get("t"), (int, float))), default=None)   # the GoCharting tab alive?
                out["map"] = trademap.read(tr, view, chain_rows, bars5, refs, dec, _read_levels(idx), m,
                                           decoder_log.read_events(day, idx), gc_t,     # A61: her BADA PRINTs at the zone
                                           flow={"P": P, "why": pwhy} if fl else None)   # §1.4: l4's pushes NIFTY's
                _map_log(day, tr, view, out["map"])
            except Exception as e:
                log.exception("trade map")
                out["map"] = {"ok": False, "why": f"could not check — the map failed: {type(e).__name__}: {e}"}
            if out.get("ok"):                    # the HOLD v3 candidates (holdshadow.py): shadow, never the word or v2
                try:
                    out["shadow"] = holdshadow.live(tr, view, out, m, bars1, chain_rows, bars5, dec,
                                                    _HOLD2["shadow"].setdefault((day, key), {}))
                    _shadow_log(day, tr, out["shadow"])
                except Exception as e:
                    log.exception("hold shadow")
                    out["shadow"], out["shadow_why"] = None, f"could not check — the shadow lines failed: {type(e).__name__}: {e}"
    except Exception as e:
        log.exception("hold2")
        out = {"ok": False, "tag": "I", "text": None, "why": f"could not check — HOLD v2 failed: {type(e).__name__}: {e}"}
    with _HOLD2_LOCK:
        _HOLD2["out"][key] = (m, out)
        _HOLD2["busy"].discard(key)


def _nifty_pushes(day):
    """NIFTY's pushes for a SENSEX line (sensex_flow.ON only): NIFTY's own 5-min bars (GoCharting from the NIFTY engine's
    memory, else Upstox) ranked on NIFTY's own history -> (pushes, None) or (None, why)."""
    if ("NIFTY", day) not in _HOLD2["refs"]:
        _HOLD2["refs"][("NIFTY", day)] = confluence_log.push_refs("NIFTY", day)
    nrefs, nwhy = _HOLD2["refs"][("NIFTY", day)]
    if not nrefs:
        return None, nwhy
    got = fold_live.hold2_rows("NIFTY")
    nb5 = confluence_log.push_bars("NIFTY", day, gc_rows=got[3] if got and got[0] == day else None,
                                   ux_rows=_ux_bars("NIFTY", day))
    return hold2.pushes(nb5, nrefs), None


def _shadow_log(day, tr, lines, at_exit=False):
    """holdshadow's forward log, data/hold/shadow_<day>.jsonl: one row per trade per line, WRITE-ONCE, when both its exit
    and HOLD v2's are decided (`final`), or at her exit as the lines stood (final False). Anytime-start: the rows already
    on disk are read before the first write, so a restart never writes a line twice. Fail-soft."""
    try:
        path = os.path.join(SHADOW_DIR, f"shadow_{day}.jsonl")
        seen = _SHADOW_SEEN.get(path)
        if seen is None:
            seen = _SHADOW_SEEN[path] = {(r.get("id"), r.get("line")) for r in confluence_log._rows(path)}
        rows = [holdshadow.row(day, tr, L, time.time()) for L in lines or ()
                if (tr["id"], L["line"]) not in seen and (L.get("final") or at_exit)]
        if rows:
            os.makedirs(SHADOW_DIR, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in rows))
            seen.update((r["id"], r["line"]) for r in rows)
    except Exception:
        log.exception("shadow log")


MAP_DIR = os.path.join("data", "hold")           # trademap's forward log, map_<day>.jsonl (_map_log)
_MAP_SEEN = {}                                   # path -> {(trade id, event, key)} already on disk


def _map_log(day, tr, view, m):
    """trademap's forward log, data/hold/map_<day>.jsonl: one row per (trade, event, key), WRITE-ONCE -- each ulta push
    (t, origin, fut) and the first minute within one step of each wall ahead (k, leg, fut, OI, the effort read or null,
    her pts). No outcome is written; scoring is later and separate. Anytime-start: the rows on disk are read before the
    first write, and the events are rebuilt from the record, so a restart backfills them. Fail-soft."""
    try:
        path = os.path.join(MAP_DIR, f"map_{day}.jsonl")
        seen = _MAP_SEEN.get(path)
        if seen is None:
            seen = _MAP_SEEN[path] = {(r.get("id"), r.get("event"), r.get("key")) for r in confluence_log._rows(path)}
        rows = [dict(e, day=day, id=tr["id"], idx=tr["idx"], d=view.get("d"), E=view.get("E"), rev=trademap.REV, at=time.time())
                for e in (m or {}).get("events") or () if (tr["id"], e["event"], e["key"]) not in seen]
        if rows:
            os.makedirs(MAP_DIR, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in rows))
            seen.update((r["id"], r["event"], r["key"]) for r in rows)
    except Exception:
        log.exception("map log")


_VOICE, _VOICE_LOCK = {}, threading.Lock()      # trade id -> voice.ladder's memory (state, seq, first sights)
_FLOWMEM = {}                                    # trade id -> sensex_flow.flow_view's chip_since (SENSEX-NIFTY-FLOW, OFF)


def _in_trade(rep, trades):
    """The in-trade reply's companions, on a COPY of the engine's cached reply (A52): HOLD v2 beside the word (§1m) with
    the shadow lines kept OFF it while the trade is open (their log, _shadow_log, is unchanged), and THE ONE VOICE
    (voice.py) computed once here, with the TRADE MAP's lines (trademap.py, read in _hold2_run, kept off hold2), so the
    panel, the hold window and Validate render the same block; after her exit, the receipt instead. Display only,
    fail-soft: a failure is a why, never the reply's."""
    tr = next((t for t in trades if t["id"] == rep.get("id")), None)
    if tr is not None and sensex_flow.on(tr["idx"]):    # SENSEX-NIFTY-FLOW §1.3 (signed 25 Oct): the FLOW shown is NIFTY's, on a copy
        try:
            nflat = fold_live.reply("/api/fold/flat", {"idx": ["NIFTY"]}, trades)
        except Exception as e:                   # never SENSEX's own flow: an unread NIFTY is CAN'T CHECK with why
            nflat = {"ok": False, "why": f"{type(e).__name__}: {e}"}
        with _VOICE_LOCK:
            rep = sensex_flow.flow_view(rep, nflat, _FLOWMEM.setdefault(tr["id"], {}))
    try:
        h2 = _hold2(rep, trades)
    except Exception as e:
        h2 = {"ok": False, "tag": "I", "text": None, "why": f"could not check — HOLD v2 failed: {type(e).__name__}: {e}"}
    out = dict(rep, hold2={k: x for k, x in h2.items() if k not in ("shadow", "shadow_why", "map")} if isinstance(h2, dict) else h2)
    try:
        if tr is not None and tr.get("exit_t"):
            p = ((rep.get("view") or {}).get("prem") or {}).get("now")
            path = os.path.join(SHADOW_DIR, f"shadow_{_board_clock()[0]}.jsonl")
            out["receipt"] = voice.receipt(tr, p, confluence_log._rows(path))
        elif tr is not None:
            with _VOICE_LOCK:
                out["voice"] = voice.ladder(rep, h2, int(time.time() * 1000), _VOICE.setdefault(tr["id"], {}),
                                            lambda px: fold_live.prem_at(tr["idx"], tr["id"], px))
            trademap.into(out["voice"], (h2 or {}).get("map") if isinstance(h2, dict) else None)   # l4 / l5 / detail
            if rep.get("flow_src"):
                sensex_flow.relabel(out["voice"])
    except Exception as e:
        log.exception("voice")
        out["voice"] = {"ok": False, "why": f"could not check — the voice failed: {type(e).__name__}: {e}"}
    return out


VOICE_DIR = os.path.join("data", "voice")        # the voice replayed per marked trade, path_<day>_<id>.json (_voice_path)
VPATH_FROM = "15:40"                             # F&O closes: today's trade replays after it; never in market hours
_VPATH = {"busy": set(), "why": {}}


def _voice_path(day, tid):
    """GET /api/voice_path?id=&day= (A56): the one voice and its map, minute by minute, over her marked trade of a PAST
    day, or today's after 15:40 -- voice_path.run, computed once off the request thread and kept at
    data/voice/path_<day>_<id>.json; a request meanwhile gets why. Never computed in market hours."""
    path = os.path.join(VOICE_DIR, f"path_{day}_{re.sub(r'[^A-Za-z0-9_.-]', '_', tid)}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            hit = json.load(f)
        if hit.get("rev") == trademap.REV:
            return hit
    lt = time.localtime()
    now, today = time.strftime("%H:%M", lt), time.strftime("%Y-%m-%d", lt)
    if day == today and now < VPATH_FROM:
        return {"ok": False, "why": "could not check — replay of today's trade after 15:40"}
    if day > today or (lt.tm_wday < 5 and "09:15" <= now < VPATH_FROM):
        return {"ok": False, "why": "could not check — " + ("that day has not happened" if day > today
                                                            else "a replay is computed after 15:40, never in market hours")}
    trs = list(_hold_trades()) if day == today else (day_state.load(day) or {}).get("hold_trades") or []
    tr = next((t for t in trs if t.get("id") == tid), None)
    if tr is None:
        return {"ok": False, "why": f"could not check — no marked trade {tid} on {day}"}
    with _HOLD2_LOCK:
        if path in _VPATH["why"]:
            return {"ok": False, "why": _VPATH["why"][path]}
        if path in _VPATH["busy"]:
            return {"ok": False, "busy": True, "why": "could not check — the replay is being computed"}
        _VPATH["busy"].add(path)
    threading.Thread(target=_voice_path_run, args=(day, tr, path), name="voice-path", daemon=True).start()
    return {"ok": False, "busy": True, "why": "could not check — the replay is being computed (first ask)"}


def _voice_path_run(day, tr, path):
    try:
        ex = tr.get("exit_t")
        end = min(hold2.MARK, int(ex[:2]) * 60 + int(ex[3:5]) + 1) if ex else hold2.MARK    # her exit, then the recap
        c = {"day": day, "tr": tr, "end": hold2.hm(end) + ":00"}
        p = voice_path.run(c)
        out = {"ok": True, "day": day, "id": tr["id"], "rev": trademap.REV, "dec_src": c.get("dec_src"),
               "receipt": c.get("receipt"), "path": [{"t": x["t"], "at": x["at"], "voice": x["voice"]} for x in p], "at": time.time()}
        os.makedirs(VOICE_DIR, exist_ok=True)
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, default=str)
        os.replace(path + ".tmp", path)
    except Exception as e:
        log.exception("voice path")
        with _HOLD2_LOCK:                        # said once, not retried until a restart
            _VPATH["why"][path] = f"could not check — the replay failed: {type(e).__name__}: {e}"
    finally:
        with _HOLD2_LOCK:
            _VPATH["busy"].discard(path)


def _receipt_for(idx, trades):
    """The panel's post-trade receipt: her last exited trade on idx today (the frame has no `fold` once she is out)."""
    done = sorted((t for t in trades if t["idx"] == idx and t.get("exit_t")), key=lambda t: t["exit_t"])
    if not done:
        return None
    rep = fold_live.reply("/api/fold", {"id": [done[-1]["id"]]}, trades)
    return dict(_in_trade(rep, trades).get("receipt") or {}, id=done[-1]["id"]) if rep.get("ok") else None


_HOLD_T = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")      # a real clock time: "09:99" is refused


def _hold_sec(t):
    """HH:MM[:SS] -> seconds since midnight."""
    return hold.mm(t) * 60 + int(t[6:8] or 0)


def _hold_trade(doc, src="marked"):
    """A trade from the form, the query or the tradebook, checked at the door. -> (trade, why)."""
    try:
        idx = str(doc.get("idx") or "").upper()
        side, role = str(doc.get("side") or "").upper(), str(doc.get("role") or "").lower()
        k = float(doc.get("k"))
        p0 = float(doc["p0"]) if doc.get("p0") not in (None, "") else None
        qty = int(float(doc.get("qty") or 0))
    except (TypeError, ValueError, KeyError):
        return None, "strike, entry price and qty must be numbers"
    t0, ex = str(doc.get("t0") or ""), doc.get("exit_t") or None
    if idx not in instruments.ENABLED:
        return None, f"index must be one of {', '.join(instruments.ENABLED)}"
    if side not in ("CE", "PE") or role not in ("long", "short"):
        return None, "side must be CE or PE, and role long or short"
    if not (k > 0 and k != float("inf")) or (p0 is not None and not 0 < p0 < 1e6) or qty < 0:
        return None, "strike and entry price must be positive, qty not negative"
    if not _HOLD_T.match(t0) or not "09:15" <= t0[:5] <= "15:29":
        return None, "entry time must be HH:MM or HH:MM:SS inside 09:15-15:29"
    if ex is not None and (not _HOLD_T.match(str(ex)) or str(ex) < t0):
        return None, "exit time must be HH:MM or HH:MM:SS, not before the entry"
    va = doc.get("validate") if isinstance(doc.get("validate"), dict) else None     # VALIDATE rev 3 §3: the entry stamp
    va = None if va is None else {k: (str(va[k])[:80] if k in ("rev", "word") else int(va[k]) if isinstance(va[k], (int, float)) else None)
                                  for k in ("rev", "word", "w", "a", "n", "c", "of") if k in va}
    return {"id": f"{idx}-{k:g}{side}-{role}-{t0.replace(':', '')}", "idx": idx, "k": k, "side": side,
            "role": role, "t0": t0, "p0": p0, "qty": qty, "exit_t": ex, "src": src,
            "expiry": doc.get("expiry"), "validate": va}, None


def _hold_reply(poller, q):
    """GET /api/hold's reply: the verdict, the four rows, the entry check and the side read."""
    def one(n):
        return (q.get(n) or [None])[0]
    if one("id"):
        tr = next((t for t in list(_hold_trades()) if t["id"] == one("id")), None)
        if tr is None:
            return {"ok": False, "why": board.CC + f"no marked trade {one('id')} today"}
    else:
        tr, why = _hold_trade({n: one(n) for n in ("idx", "k", "side", "role", "t0", "p0", "qty", "exit_t")}, "query")
        if tr is None:
            return {"ok": False, "why": board.CC + why}
    F = _hold_facts(poller, tr["idx"])
    if F is None:
        return {"ok": False, "trade": tr, "draft": hold.DRAFT,
                "why": board.CC + "no finished minute of today's session on the chain grid yet"}
    asof = one("asof") or F["asof"]
    if asof not in hold.SESSION or asof > F["asof"]:
        return {"ok": False, "trade": tr, "draft": hold.DRAFT,
                "why": board.CC + f"{asof} is not a finished session minute yet (latest {F['asof']})"}
    mins = _hold_minutes(F)
    res = hold.read(tr, mins, F["pivots"], upto=asof, prem=_hold_prem(F, tr["k"], tr["side"]), idx=tr["idx"],
                    late=_hold_late(tr["idx"], F["day"]), frozen=_hold_frozen(tr))
    if not res["ok"]:
        return {"ok": False, "trade": tr, "asof": asof, "draft": hold.DRAFT, "why": res["why"]}
    pl = plan.read(tr, mins, res["rows"], greeks=_hold_greeks(tr["idx"], F["day"], tr["k"], tr["side"], len(mins)))
    i = hold.SESSION.index(asof)
    sd = hold.sides(mins, upto=i)[-1]
    now, ent = res["rows"][-1], res["entry"]
    ex = tr.get("exit_t")
    return {
        "ok": True, "draft": hold.DRAFT, "idx": tr["idx"], "day": F["day"], "asof": asof, "trade": tr,
        "thesis": res["th"], "now": now, "fold": res["fold"],
        "plan": {**pl["rows"][-1], "entry": pl["rows"][0], "draft": plan.DRAFT, "not_shown": plan.NOT_SHOWN_LINES},
        "entry": {**ent, "head": asof < ent["head_until"]},
        "side": {**hold.side_line(mins[i], sd, F["expiry"]), "agrees": hold.agrees(tr["side"], tr["role"], sd["side"])},
        "after_exit": bool(ex) and hold.mm(asof) > hold.mm(hold.read_minute(ex)),
        "sigma": _hold_sigma(tr["idx"], tr["k"], tr["side"], asof) if one("sigma") != "0" else None,
        "rows": res["rows"] if one("rows") == "1" else None,
        "runs": _hold_runs(res["rows"]) if one("rows") == "brief" else None,
        "absent": {
            # under a latch a FOLD rule HAS matched: no "checked, none" sentence, and the latch rule goes on
            # its own field (a rule statement, printed plain -- never dressed as an absence)
            "checked_none": None if res["fold"] else board.NONE + "no FOLD rule has matched since your entry",
            "rule_note": "nothing un-latches a FOLD; a re-entry is a new trade" if res["fold"] else None,
            "could_not_check": now["blind"],
            "not_shown": [board.NOT_SHOWN + "the engine's own headline word — it read CONTRADICTED on 09-24",
                          board.NOT_SHOWN + "an order, a size, a target, a stop price or a probability — never",
                          board.NOT_SHOWN + "P&L on the collapsed line — the window reads the reason, not the money"]},
        "src_data": F["src"], "note": "display only; the window gates nothing and has no order path",
    }


def _hold_runs(rows):
    """The trade's record since entry as runs of the WORD: [{from, to, verdict, tag, sentence}],
    one per change of HOLD / WATCH / FOLD / PATA NAHI (a noise tag flickering minute to minute is
    not a change of the word) -- each with the sentence that opened it. What the Validate tab
    prints instead of 300 minute rows."""
    out = []
    for x in rows:
        if out and out[-1]["verdict"] == x["verdict"]:
            out[-1]["to"] = x["t"]
        else:
            out.append({"from": x["t"], "to": x["t"], "verdict": x["verdict"], "tag": x["tag"], "sentence": x["sentence"]})
    return out


def _hold_zone_rows():
    """The zone machine's rows (data/trigger_log.jsonl, read-only), re-read only when the
    file changes -- so a check polled every 15 s costs a stat, not a parse."""
    try:
        st = os.stat(trigger_log.PATH)
    except OSError:
        return None
    c = _HOLD.get("zone_cache")
    if not c or c["key"] != (st.st_size, st.st_mtime):
        rows, _bad = trigger_log.read(trigger_log.PATH)
        c = _HOLD["zone_cache"] = {"key": (st.st_size, st.st_mtime), "rows": [r for r in rows if r.get("rule") == "zone"]}
    return c["rows"]


def _hold_lot(idx):
    try:
        return upstox_instruments.lot_tick(idx)[0]
    except Exception:                        # the dump not loaded: the check says "per unit"
        return None


def _hold_zone(idx, day, asof, d):
    """Her setup, as the zone machine logged it forward: its latest TRIGGER and latest ARM on
    `idx` today, each seen once its 3-min bar has closed by `asof`, with its own §1d gate [M]
    and whether it agrees with a trade of direction `d`. Display only; it gates nothing."""
    rows = _hold_zone_rows()
    if rows is None:
        return {"trigger": None, "arm": None, "why": board.CC + "the zone record could not be read"}
    mine = [r for r in rows if r.get("rule") == "zone" and r.get("day") == day and r.get("index") == idx
            and isinstance(r.get("t"), str) and fronts.bar_last_minute(r["t"], 3) <= asof]     # never pooled with 5c

    def ev(r):
        g, zd = r.get("gate") or {}, {"SELL": -1, "BUY": 1}.get(r.get("side"), 0)
        seen = fronts.bar_last_minute(r["t"], 3)
        return {"t": r["t"], "seen": seen, "ago": hold.mm(asof) - hold.mm(seen),
                "kind": "armed" if r.get("kind") == "arm" else "triggered", "side": r.get("side"),
                "band": r.get("band"), "px": r.get("px"), "legal": g.get("legal"), "why": g.get("why"),
                "agrees": "agrees" if zd == d else "against" if zd == -d else "no side", "tag": "M"}
    trig = [r for r in mine if r.get("kind") != "arm"]
    arms = [r for r in mine if r.get("kind") == "arm"]
    return {"trigger": ev(trig[-1]) if trig else None, "arm": ev(arms[-1]) if arms else None,
            "why": None if mine else board.NONE + f"the zone machine has not armed on {idx} today"}


def _hold_machine(payloads, idx):
    """The zone machine's own per-bar states on the day's 3-min future bars -- what /api/data publishes at
    band_rotation.SCORED_INTERVAL as zone_state / zone_state_sell -- as (bars, buy, sell); (None, None, None)
    when the tape has no payload. One seam for tests."""
    try:
        pl = payload_at((payloads or {}).get(idx), band_rotation.SCORED_INTERVAL)
        pj = json.loads(pl) if isinstance(pl, (bytes, str)) else (pl or {})
        d0 = (pj.get("days") or [{}])[0] if isinstance(pj, dict) else {}
        return d0.get("bars"), d0.get("zone_state"), d0.get("zone_state_sell")
    except Exception:                        # an unreadable tape costs the setup fact, never the check
        return None, None, None


def _xindex_zone(payloads, idx):
    """xindex's zone seam: the zone machine's per-bar states on /api/data's 3-min payload, with the payload's session
    label so a stale session is never read as today. None when unreadable. SHADOW; read-only."""
    try:
        pl = payload_at((payloads or {}).get(idx), band_rotation.SCORED_INTERVAL)
        pj = json.loads(pl) if isinstance(pl, (bytes, str)) else (pl or {})
        d0 = (pj.get("days") or [{}])[0] if isinstance(pj, dict) else {}
        return {"label": d0.get("day"), "buy": d0.get("zone_state"), "sell": d0.get("zone_state_sell")}
    except Exception:
        return None


def _hold_setup(payloads, idx, day, asof, d):
    """VALIDATE rev 2 §1.1: Your setup, the zone machine's own state on the last closed 3-min bar, by the
    registered pick, with the §1d gate of its event's logged zone row. Display only; it gates nothing."""
    bars, buy, sell = _hold_machine(payloads, idx)
    rows = _hold_zone_rows()
    mine = [r for r in rows or [] if r.get("day") == day and r.get("index") == idx]
    return validate.pick(bars if rows is not None else None, buy, sell, mine, asof, d)


def _hold_geom(F, idx, t, d):
    """VALIDATE rev 2 §1.3 at check minute t for direction d, ONE function for the check's Room and the outcome
    writer (§3): the window's line from the trade the check makes (t0 = t + 1; CE for d = +1, PE for d = -1;
    long -- a writer's danger-side line for the same d is the same line), the noise and the target, off the
    same day facts. Exact after a restart."""
    mins, late = _hold_minutes(F), _hold_late(idx, F["day"])
    tr = {"side": "CE" if d > 0 else "PE", "role": "long", "t0": hold.hm(hold.mm(t) + 1), "k": 0, "p0": None, "qty": 0}
    res = hold.read(tr, mins, F["pivots"], upto=t, idx=idx, late=late)
    ln = res["rows"][0]["line"] if res.get("ok") else {"blind": res.get("why")}
    return validate.geometry(mins, hold.SESSION.index(t), d, ln, late)


def _hold_check(poller, q, payloads=None):
    """GET /api/hold/check -- the Validate tab's "if I enter now": THE SAME READ the window makes
    at a fill (the entry check, the four rows, the plan, the side read), made at the latest
    finished minute for a trade not yet taken, plus her setup from the zone machine. Nothing is
    marked, nothing is logged; no new rule is involved."""
    def one(n):
        return (q.get(n) or [None])[0]
    idx = str(one("idx") or "").upper()
    if idx not in instruments.ENABLED:
        return {"ok": False, "why": board.CC + f"index must be one of {', '.join(instruments.ENABLED)}"}
    F = _hold_facts(poller, idx)
    if F is None:
        if _board_clock()[1] < "09:16":      # nothing is missing before the first minute has finished
            return {"ok": False, "idx": idx, "why": board.NOT_SHOWN + "the first check reads the 09:15 minute, from 09:16"}
        return {"ok": False, "idx": idx, "why": board.CC + "no finished minute of today's session on the chain grid yet"}
    asof = F["asof"]
    if hold.mm(asof) + 1 > hold.mm("15:29"):
        return {"ok": False, "idx": idx, "asof": asof,
                "why": board.NOT_SHOWN + "the session has closed — a pre-trade check reads a live minute"}
    lot = _hold_lot(idx)
    qty = one("qty") or lot or 1
    try:
        k, side = float(one("k")), str(one("side") or "").upper()
        cell = fronts._at((F["core"]["minutes"].get(asof) or {}).get("px"), k)
    except (TypeError, ValueError):
        return {"ok": False, "idx": idx, "why": board.CC + "strike must be a number"}
    live = cell[0 if side == "CE" else 1] if isinstance(cell, (list, tuple)) and len(cell) == 2 else None
    p0 = one("p0") or live
    tr, why = _hold_trade({"idx": idx, "k": k, "side": side, "role": one("role"), "qty": qty, "p0": p0,
                           "t0": hold.hm(hold.mm(asof) + 1)}, "check")
    if tr is None:
        return {"ok": False, "idx": idx, "why": board.CC + why}
    mins = _hold_minutes(F)
    res = hold.read(tr, mins, F["pivots"], prem=_hold_prem(F, k, side), idx=idx, late=_hold_late(idx, F["day"]))
    if not res["ok"]:
        return {"ok": False, "idx": idx, "asof": asof, "why": res["why"]}
    gk = _hold_greeks(idx, F["day"], k, side, len(mins))
    pl = plan.read(tr, mins, res["rows"], greeks=gk)
    i = hold.SESSION.index(asof)
    sd = hold.sides(mins, upto=i)[-1]
    ent = res["entry"]
    text = ent["text"].replace("You entered into", "If you enter now, you enter into", 1) \
                      .replace("the reason was already gone (read", "the reason is already gone (read", 1)
    out = {
        "ok": True, "draft": hold.DRAFT, "idx": idx, "day": F["day"], "asof": asof, "trade": tr, "lot": lot,
        "qty_src": "you" if one("qty") else f"1 lot ({lot})" if lot else "per unit — the lot size is not loaded",
        "p0_src": "you" if one("p0") else f"the chain's last trade at {asof} [I]" if live else None,
        "thesis": res["th"], "now": res["rows"][-1], "entry": {**ent, "text": text},
        "plan": {**pl["rows"][-1], "draft": plan.DRAFT, "not_shown": plan.NOT_SHOWN_LINES},
        "side": {**hold.side_line(mins[i], sd, F["expiry"]), "agrees": hold.agrees(side, tr["role"], sd["side"])},
        "zone": _hold_zone(idx, F["day"], asof, res["th"]["d"]),
        "greeks": ({"delta": gk[-1][0], "gamma": gk[-1][1], "tag": "M"} if gk and gk[-1] else
                   {"why": board.CC + "no greeks for this strike in the chain record"}),
        "absent": {"checked_none": board.NOT_SHOWN + "an order, a size or a confidence number — never computed here",
                   "could_not_check": res["rows"][-1]["blind"],
                   "not_shown": [board.NOT_SHOWN + "the engine's own headline word — it read CONTRADICTED on 09-24"]
                   + plan.NOT_SHOWN_LINES},
        "note": "a check marks no trade; a VALIDATE press is logged",       # VALIDATE-PREREG.md §3
    }
    d = res["th"]["d"]
    out["setup"] = su = _hold_setup(payloads, idx, F["day"], asof, d)          # VALIDATE rev 2 §1.1
    out["room"] = g = _hold_geom(F, idx, asof, d)                               # §1.3
    out["validate"] = v = validate.word(out)
    try:                                     # EXPRESSION-PREREG §A.2 / §F.1; its failing never costs the buyer's word
        out["expr"] = ex = _expr_press(F, idx, asof, d, tr, out, res)
    except Exception as e:
        log.exception("expression read failed %s %s", idx, asof)
        why = board.CC + f"the expression could not be read: {type(e).__name__}: {e}"
        out["expr"] = ex = {"ok": False, "why": why, "d": d, "dir": "UP" if d > 0 else "DOWN", "draft": expression.DRAFT,
                            "not_shown": expression.NOT_SHOWN_LINES, "mine": None, "log": {"word": None, "why": why}}
    if tr["role"] == "short" and ex.get("mine"):     # §B: a writer's GO / WAIT / NO (amends VALIDATE rev 2 §1.6, writers only)
        out["validate"] = v = ex["mine"]
    if one("log") == "1":                    # VALIDATE-PREREG rev 2 §3: every press, write-once per minute and contract
        tg, paid = g["target"], v["facts"][3] if tr["role"] == "long" else {}
        hold_log.append("check", F["day"], [{
            "day": F["day"], "at": round(time.time(), 1), "t": asof, "idx": idx, "k": k, "side": side,
            "role": tr["role"], "p0": tr["p0"], "word": v["word"], "n_for": v["n_for"], "n_against": v["n_against"],
            "facts": [[f["name"], f["state"], f["absence"], f["text"]] for f in v["facts"]], "entry_verdict": ent["verdict"],
            "zone_t": (out["zone"].get("trigger") or {}).get("t"),
            "stop": {k2: out["plan"]["stop"].get(k2) for k2 in ("L", "room")},
            "rung": out["plan"]["rung"] and {k2: out["plan"]["rung"].get(k2) for k2 in ("src", "side", "k", "room", "word")},
            "tag": "I", "rev": v["rev"], "d": d,
            "setup": {k2: su.get(k2) for k2 in ("machine", "state", "band", "ref_t", "candles_left", "legal", "why")},
            "room": {"line": g["line"], "noise": g["noise"], "n": g["n"],
                     "target": {k2: tg.get(k2) for k2 in ("src", "side", "k", "pts", "word")}},
            "paid": True if paid.get("state") == "for" else False if paid.get("absence") == "none" else None,
            **({"writer": {k2: v.get(k2) for k2 in ("X", "P", "L", "line", "noise", "beyond_strike", "stratum")}}
               if tr["role"] == "short" else {}),
            "expr": ex["log"], "after_1500": expression.after_1500(asof)}])      # EXPRESSION-PREREG §E.3, additive
    return out


def _hold_row(F, tr, x, ent, sd, pr, fold=None):
    """One §8 trade-log row, with THE PLAN's minute (PLAN §5) as one additive key, and rev 5 §G's additive
    keys: the line's close read, its B and level; the latch once set; the option the row was written under."""
    rec = F["recs"][x["t"]]
    c, fl, ex = rec.get("cvd") or {}, rec.get("flow") or {}, tr.get("exit_t")
    return {"day": F["day"], "t": x["t"], "idx": tr["idx"], "trade_id": tr["id"], "src": tr["src"],
            "after_exit": bool(ex) and hold.mm(x["t"]) > hold.mm(hold.read_minute(ex)),
            "strike": tr["k"], "side": tr["side"], "role": tr["role"], "qty": tr["qty"],
            "entry_t": tr["t0"], "entry_px": tr["p0"], "exit_t": ex,
            "verdict": x["verdict"], "word_tag": x["tag"], "since": x["since"], "fold_rule": x["fold_rule"],
            "entry_verdict": ent["verdict"], "unlatched": x["unlatched"],
            "line": {k: x["line"].get(k) for k in ("L", "src", "room", "broken_at", "blind", "px", "bar_close", "bar",
                                                   "read_at", "backfill", "B", "B_at", "level", "clamped")},
            "latch": {k: fold.get(k) for k in ("t", "rule", "bar", "L", "src", "px", "by", "read_at", "backfill", "B",
                                               "B_at", "level", "by_level", "clamped")}
                     if fold and hold.mm(x["t"]) >= hold.mm(fold["t"]) else None,
            "prereg": hold.PREREG,
            "payers": {k: x["payers"].get(k) for k in ("k", "state", "fold_t")},
            "holders": {k: x["holders"].get(k) for k in ("k", "state", "fold_t")},
            "both_leaving": x["both_leaving"],
            "flow": {"cvd_d": c.get("d"), "rank": c.get("rank"), "buy": fl.get("b"), "sell": fl.get("s"),
                     "word": x["flow"]["state"], "why": x["flow"]["why"]},
            "trend": {**(rec.get("tr") or {}), "word": x["trend"]["state"]},
            "clock": {k: x["clock"].get(k) for k in ("paid_last", "quiet", "readable")},
            "prem": x["prem"].get("c"), "prem_pct_of_entry": x["prem"].get("pct"), "pnl": x["prem"].get("pnl"),
            "blind": x["blind"],
            "side_read": {"side": sd["side"], "since": sd["since"],
                          "agrees": hold.agrees(tr["side"], tr["role"], sd["side"])},
            "plan": {"stop": {k: pr["stop"].get(k) for k in ("L", "room", "risk", "risk_why")},
                     "rung": pr["rung"] and {k: pr["rung"].get(k) for k in ("src", "side", "k", "room", "word", "state", "fold_t")},
                     "touch": pr["touch"] and {k: pr["touch"].get(k) for k in ("k", "side", "word", "session")}},
            "tag": "I", "src_data": F["src"], "at": round(time.time(), 1)}


def _hold_tick(poller, idx, extra=(), expr=True):
    """The forward logs for one index up to its latest finished minute (§8): every
    minute's side row not yet written, each side stamp's strike track once its 30
    finished minutes are in (to 15:29 and flagged short after 14:59), and the rows of
    every marked trade (+ `extra`, the import's). Exact after a restart. -> rows written.
    `expr`: THE EXPRESSION's log too (EXPRESSION-PREREG §E.3; its rows are not in the count) --
    False from the import's request, which leaves it to the hold loop's thread."""
    F = _hold_facts(poller, idx)
    if F is None:
        return 0
    day, asof, mins = F["day"], F["asof"], _hold_minutes(F)
    sds = hold.sides(mins)
    grid = F["core"]["minutes"]
    ks = F["core"]["g"][2]
    step = min((b - a for a, b in zip(ks, ks[1:]) if b > a), default=None) or 1.0

    def px(t, k):
        cell = fronts._at((grid.get(t) or {}).get("px"), k)
        return list(cell) if isinstance(cell, (list, tuple)) and len(cell) == 2 else [None, None]

    def atm(m):
        return round(m["spot"] / step) * step if m.get("spot") is not None else None
    side_rows = []
    for m, sd in zip(mins, sds):
        if hold_log.has("side", day, (idx, m["t"], "minute")):
            continue
        k = atm(m)
        sl = hold.side_line(m, sd, F["expiry"])
        side_rows.append({
            "day": day, "t": m["t"], "idx": idx, "kind": "minute", "rows": m.get("tr"), "side": sd["side"],
            "since": sd["since"], "stamp": sd["stamp"], "facts": {f["k"]: f["state"] for f in sl["facts"]},
            "oi_half": sl["oi_half"], "blind": [b for b in (m.get("blind"), m.get("tr_why")) if b],
            "expiry": F["expiry"]["text"], "atm": {"k": k, **dict(zip(("ce_px", "pe_px"), px(m["t"], k) if k else [None, None]))},
            "tag": "I", "src_data": F["src"], "at": round(time.time(), 1)})
    for i, sd in enumerate(sds):
        if not sd["stamp"]:
            continue
        end = min(hold.mm(sd["t"]) + HOLD_TRACK, hold.mm("15:29"))
        if hold.mm(asof) < end or hold_log.has("side", day, (idx, sd["t"], "stamp_track")):
            continue
        k, ts = atm(mins[i]), [hold.hm(n) for n in range(hold.mm(sd["t"]), end + 1)]
        side_rows.append({"day": day, "t": sd["t"], "idx": idx, "kind": "stamp_track", "side": sd["side"],
                          "stamp_track": {"k": k, "from": sd["t"], "to": hold.hm(end),
                                          "short": hold.mm(sd["t"]) + HOLD_TRACK > hold.mm("15:29"),
                                          # no spot at the stamp (30 Sep BANKNIFTY): no strike, the track says so -- it
                                          # raised here every minute and took the whole index's hold log down with it
                                          "ce": [{"t": t, "px": px(t, k)[0] if k else None} for t in ts],
                                          "pe": [{"t": t, "px": px(t, k)[1] if k else None} for t in ts]},
                          "tag": "I", "src_data": F["src"], "at": round(time.time(), 1)})
    n = hold_log.append("side", day, side_rows)
    with HOLD_TRADES_LOCK:
        trades = [t for t in _hold_trades() if t["idx"] == idx] + list(extra)
    by_t = {s["t"]: s for s in sds}
    for tr in trades:
        # rev 5 §A.0.4: a live or marked trade reads each close when it was read; the close-time import reads
        # every close at its own bar (src: import, shown apart)
        res = hold.read(tr, mins, F["pivots"], prem=_hold_prem(F, tr["k"], tr["side"]), idx=idx,
                        late=None if tr.get("src") == "import" else _hold_late(idx, day), frozen=_hold_frozen(tr))
        if not res["ok"]:
            continue
        _hold_freeze(tr, res["b_reads"])
        pl = plan.read(tr, mins, res["rows"], greeks=_hold_greeks(idx, day, tr["k"], tr["side"], len(mins)))
        pr = {p["t"]: p for p in pl["rows"]}
        n += hold_log.append("hold", day, [_hold_row(F, tr, x, res["entry"], by_t[x["t"]], pr[x["t"]], res["fold"])
                                           for x in res["rows"]
                                           if not hold_log.has("hold", day, (tr["id"], x["t"], "minute"))])
        d = res["th"]["d"]
        touch_rows = []
        for tc in pl["touches"]:                     # PLAN §5: each touch its own write-once row, once its 15 minutes finish
            nx = plan.next15(mins, tc["i"], d, len(mins) - 1)
            if nx is None or hold_log.has("hold", day, (tr["id"], tc["t"], "rung_touch")):
                continue
            touch_rows.append({"day": day, "kind": "rung_touch", "t": tc["t"], "touch_t": tc["t"], "trade_id": tr["id"],
                               "idx": idx, "src": tr["src"], "k": tc["k"], "side": tc["side"], "word": tc["word"],
                               "close_at_touch": tc["close"], "next15": nx, "tag": "M", "at": round(time.time(), 1)})
        n += hold_log.append("hold", day, touch_rows)
    n += _hold_outcomes(F, idx)
    if expr:
        try:
            _expr_tick(F, idx)
        except Exception:                    # the expression's log failing costs its rows, never the window's
            log.exception("expression log failed %s", idx)
    if _HOLD.pop("land_new", False):         # a late read or a B read: on disk before the next restart can need it
        _save_day_state()
    return n


def _hold_outcomes(F, idx):
    """VALIDATE rev 2 §3, the stamp_track discipline: for every (idx, read minute t, d) with a rev 2 buyer press
    and no outcome row yet, once its window has finished (asof >= min(t + 30, 15:29)), ONE outcome row -- the
    trade re-created from the press row as the check made it, L and the target read by the check's own
    function. Keyed (idx, t, d, role, "outcome") so a long CE and a long PE at one minute are two rows, and a
    long CE and a short PE (EXPRESSION-PREREG §B.3) are two rows. A rev "2W" writer press gets its own row,
    role "short": P − X before the static L, 30 minutes judged and to 15:29 shown, written once both are known."""
    day, asof = F["day"], F["asof"]
    allp = [r for r in hold_log.read("check", day) if r.get("kind") != "check_outcome" and r.get("t") in hold.SESSION]
    press = [r for r in allp if r.get("rev") == validate.REV and r.get("role") == "long"]
    rows, mins = [], None
    for key in sorted({(r["t"], r["d"]) for r in press if r.get("idx") == idx}):
        t, d = key
        if hold.mm(asof) < min(hold.mm(t) + validate.HORIZON, hold.mm(hold.SESSION[-1])) \
                or hold_log.has("check", day, (idx, t, d, "long", "outcome")):
            continue
        mins = mins or _hold_minutes(F)
        o = validate.outcome(mins, hold.SESSION.index(t), d, _hold_geom(F, idx, t, d))
        if o is None:
            continue
        rows.append({"kind": "check_outcome", "day": day, "t": t, "idx": idx, "d": d,
                     "word": next(r["word"] for r in press if (r["idx"], r["t"], r["d"]) == (idx, t, d)),
                     "co_timed": sorted({r["idx"] for r in press if r["idx"] != idx and (r["t"], r["d"]) == key}),
                     "opposite_same_minute": any((r["idx"], r["t"], r["d"]) == (idx, t, -d) for r in press),
                     **o, "after_1500": expression.after_1500(t), "tag": "M"})
    wpress = [r for r in allp if r.get("rev") == expression.REV_W and r.get("role") == "short"]
    D = None
    for key in sorted({(r["t"], r["d"]) for r in wpress if r.get("idx") == idx}):
        t, d = key
        end = hold.hm(min(hold.mm(t) + validate.HORIZON, hold.mm(hold.SESSION[-1])))
        if hold.mm(asof) < hold.mm(end) or hold_log.has("check", day, (idx, t, d, "short", "outcome")):
            continue
        p = next(r for r in wpress if (r["idx"], r["t"], r["d"]) == (idx, t, d))
        w, D = p.get("writer") or {}, D or _expr_day(F, idx)
        i = hold.SESSION.index(t)
        f30 = expression.writer_outcome(D, i, d, p["k"], p["side"], w, end)
        f1529 = expression.writer_outcome(D, i, d, p["k"], p["side"], w, hold.SESSION[-1])
        if f30 is None or f1529 is None:             # to 15:29 not known yet: the row waits, whole (write-once)
            continue
        rows.append({"kind": "check_outcome", "day": day, "t": t, "idx": idx, "d": d, "role": "short", "word": p["word"],
                     "k": p["k"], "side": p["side"],
                     "target": {"P": w.get("P"), "X": w.get("X"),
                                "level": None if None in (w.get("P"), w.get("X")) else round(w["P"] - w["X"], 2)},
                     "stop": {"L": w.get("L"), "pts": w.get("line")}, "first_30": f30, "first_1529": f1529, "to": end,
                     "beyond_strike": w.get("beyond_strike"), "stratum": w.get("stratum"),
                     "co_timed": sorted({r["idx"] for r in wpress if r["idx"] != idx and (r["t"], r["d"]) == key}),
                     "short": hold.mm(t) + validate.HORIZON > hold.mm(hold.SESSION[-1]),
                     "after_1500": expression.after_1500(t), "tag": "M"})
    return hold_log.append("check", day, rows)


# ---- THE EXPRESSION (docs/hold/EXPRESSION-PREREG.md rev e, signed 2026-09-26 20:48; expression.py) ----
#
# §A's read at each 3-minute close, per index and direction, off the same per-minute facts the window reads;
# §B's writer word on a SELL press. Its forward log (§E.3) is written by the hold loop's thread and completed at
# the close by the same thread when the import asks: a day's backfill is ~750 reads, and a server once wedged on
# heavy work inside a request (2026-09-18). A request reads at most ONE close. It gates nothing; no order path.
def _expr_day(F, idx, late=None):
    """expression.py's input off the hold facts: the minutes, pivots, each strike's minute close off the chain
    grid [I] (as _hold_prem) and the broker's greeks [M] (as _hold_greeks). `late` (rev 5 §A.0.4) for a press, as
    VALIDATE reads it; None for the closes, each read at its own bar as the close-time import reads them."""
    mins, grid = _hold_minutes(F), F["core"]["minutes"]
    ks = F["core"]["g"][2]
    step = min((b - a for a, b in zip(ks, ks[1:]) if b > a), default=None) or 1.0
    gks = {}

    def px(k, side, i):
        if k is None or i >= len(mins):
            return None
        cell = fronts._at((grid.get(hold.SESSION[i]) or {}).get("px"), k)
        v = cell[0 if side == "CE" else 1] if isinstance(cell, (list, tuple)) and len(cell) == 2 else None
        return float(v) if isinstance(v, (int, float)) and v > 0 else None

    def gk(k, side, i):
        if k is None:
            return None
        if (k, side) not in gks:
            gks[(k, side)] = _hold_greeks(idx, F["day"], k, side, len(mins))
        g = gks[(k, side)]
        return g[i] if i < len(g) else None
    return {"idx": idx, "step": step, "minutes": mins, "pivots": F["pivots"], "px": px, "gk": gk, "late": late}


def _expr_cache(idx, day):
    c = _HOLD.setdefault("expr", {}).get(idx)
    if c is None or c["day"] != day:
        c = _HOLD["expr"][idx] = {"day": day, "reads": {}, "writers": {}}
    return c


def _expr_get(D, C, i, d):
    """The read at close i for direction d, kept for the day; a close read before its candle landed is read
    again once it has (§A.2: a late close is read when its candle lands)."""
    t = hold.SESSION[i]
    e = C["reads"].get((t, d))
    if e is None or (e["word"] is None and D["minutes"][i].get("ix")):
        e = C["reads"][(t, d)] = expression.read(D, i, d)
        C["writers"].pop((t, d), None)
    return e


def _expr_drag(idx):
    """§A.7: the drag number, printed, never counted -- read live; drag.py keeps no per-minute past."""
    with _SENSES_LOCK:
        b = (_SENSES.get("drag") or {}).get(idx)
    r = b.read() if b is not None else None
    if not r or r.get("paid") is None or r.get("owed") is None:
        return {"why": board.CC + ((r or {}).get("anchor_why") or "no drag number yet today"), "tag": "M"}
    return {"text": f"today a correct buyer was paid {r['paid']:.1f} of {r['owed']:.1f} owed since "
                    f"{r.get('anchored_at')} [M]", "paid": r["paid"], "owed": r["owed"], "tag": "M"}


def _expr_tick(F, idx):
    """§E.3's log for one index to its latest finished minute: one row per 3-min close per direction not yet
    written, in order (a due close whose candle has not landed holds the rest until it lands, or the day is
    complete), and one `expr_outcome` row per unit once complete. Exact after a restart. -> rows written."""
    day, asof = F["day"], F["asof"]
    with _HOLD.setdefault("expr_locks", {}).setdefault(idx, threading.Lock()):
        D, C = _expr_day(F, idx), _expr_cache(idx, day)
        closes = [i for i, t in enumerate(hold.SESSION) if hold.is_close(t) and t <= asof]
        final = asof == hold.SESSION[-1]
        rows = []
        for d in (1, -1):
            ser = [_expr_get(D, C, i, d) for i in closes]
            for j, i in enumerate(closes):
                e = ser[j]
                if not D["minutes"][i].get("ix") and not final:
                    break
                if hold_log.has("expr", day, (idx, e["t"], d, "expr")):
                    continue
                live = hold.mm(asof) - hold.mm(e["t"]) < hold.BAR
                rows.append(expression.row(D, e, day, idx, (ser, j), expiry_line=F["expiry"], drag=(
                    _expr_drag(idx) if live else
                    {"why": board.NOT_SHOWN + f"the drag number is read live, not kept per minute (row written at {asof})",
                     "tag": "M"})))
        n = hold_log.append("expr", day, rows)
        outs = []
        for d in (1, -1):
            for i in closes:
                t = hold.SESSION[i]
                if (not expression.is_unit(t) or not hold_log.has("expr", day, (idx, t, d, "expr"))
                        or hold_log.has("expr", day, (idx, t, d, "expr_outcome"))):
                    continue
                e = _expr_get(D, C, i, d)
                if e["word"] and (t, d) not in C["writers"]:
                    C["writers"][(t, d)] = expression.writer(D, i, d, e["sell"]["side"], e["sell"]["k"], Sr=e["_short"])
                co = [x for x in instruments.ENABLED if x != idx and hold_log.has("expr", day, (x, t, d, "expr"))]
                o = expression.outcome_row(D, e, C["writers"].get((t, d)), day, idx, co)
                if o is not None:
                    outs.append(o)
        return n + hold_log.append("expr", day, outs)


def _expr_complete(poller):
    """The close-time import's half of §E.3, on the hold loop's thread (never the import's request)."""
    for idx in instruments.ENABLED:
        try:
            F = _hold_facts(poller, idx)
            if F is not None:
                _expr_tick(F, idx)
        except Exception:
            log.exception("expression log failed %s", idx)


def _expr_verdict(w, su=None, expiry=None):
    """§B's writer word in VALIDATE's reply shape, so the tab renders a writer's four facts as a buyer's."""
    base_ = {"rev": expression.REV_W, "draft": expression.DRAFT, "tag": "I", "writer_note": None,
             "not_shown": [validate.SIGMA, board.NOT_SHOWN + "a writer has no next wall; time is her target"]}
    if not w.get("word"):
        return {**base_, "word": None, "count": "", "n_for": 0, "n_against": 0, "n_neither": 0, "needs": [],
                "sentence": w.get("why"), "facts": []}
    printed = [x for x in (su and su.get("text") and f"Your setup — {su['text']} (printed, not counted)",
                           expiry and expiry.get("text"),
                           w["X"] is not None and f"X = {w['X']:,.2f} of premium at your line [I]") if x]
    return {**base_, "word": w["word"], "count": w["count"], "n_for": w["n_for"], "n_against": w["n_against"],
            "n_neither": w["n_neither"], "sentence": w["sentence"], "needs": w["needs"], "printed": printed,
            "line": w["line"], "noise": w["noise"], "X": w["X"], "P": w["P"], "L": w["L"], "wall": w["wall"],
            "beyond_strike": w["beyond_strike"], "stratum": w["stratum"], "entry": w["entry"],
            "facts": [{"name": n, "state": s, "text": t, "absence": a} for n, s, a, t in w["facts"]]}


def _expr_setup_line(su):
    """§F.1: when her zone setup names a direction on its closed bar -- display only, it pre-fills nothing."""
    if not su or su.get("side") not in ("BUY", "SELL") or not su.get("state"):
        return None
    return (f"setup: {su['side']} {su['band']} {validate.STATE_WORD[su['state']]}, {su['ref_t']} bar — "
            f"the expression for {'UP' if su['side'] == 'BUY' else 'DOWN'} is ready")


def _expr_refused(e, codes):
    out = []
    for c in codes:
        why = (e.get("why_ref") or {}).get(c) or expression.R_TEXT[c]
        out.append(f"R4 — could not check: {hold._strip(why)}" if c == "R4cnc" else f"{c} — {why}")
    return out


def _expr_press(F, idx, asof, d, tr, out, res):
    """§A.2 / §A.6 / §F.1 on a VALIDATE press: the last 3-min close's word for the direction of the pressed leg,
    its since / was, the five facts, and the two legs at that close's ATM strike -- premiums, Δ, entry checks and
    each leg's own VALIDATE word read at the press minute -- with the prints. A SELL press also gets §B's word at
    her own strike (`mine`). At most ONE close is read here; the day's closes are the hold loop's."""
    day, ip, late = F["day"], hold.SESSION.index(asof), _hold_late(idx, F["day"])
    Dl = _expr_day(F, idx, late)
    bs, ss = ("CE", "PE") if d > 0 else ("PE", "CE")
    mine = (_expr_verdict(expression.writer(Dl, ip, d, tr["side"], tr["k"], Sr=res), out.get("setup"), F["expiry"])
            if tr["role"] == "short" else None)
    closes = [i for i, t in enumerate(hold.SESSION) if hold.is_close(t) and t <= asof]
    base_ = {"ok": False, "d": d, "dir": "UP" if d > 0 else "DOWN", "draft": expression.DRAFT, "mine": mine,
             "prereg": expression.PREREG, "not_shown": expression.NOT_SHOWN_LINES,
             "setup_line": _expr_setup_line(out.get("setup"))}
    if not closes:
        why = board.CC + "the 09:15–09:17 close has not landed"
        return {**base_, "why": why, "log": {"word": None, "why": why}}
    D, C = _expr_day(F, idx), _expr_cache(idx, day)
    ic = closes[-1]
    tc = hold.SESSION[ic]
    e = _expr_get(D, C, ic, d)
    if e["word"] is None:
        why = (board.CC + f"the {hold.bar_name(tc)} close has not landed" if not D["minutes"][ic].get("ix")
               else e.get("why") or board.CC + "the line can't be set")
        return {**base_, "read_at": tc, "why": why, "log": {"word": None, "read_at": tc, "why": why}}
    lab = lambda x: x["word"] or "could not check"
    since, was, gap = tc, None, None
    for i in reversed(closes[:-1]):
        x = C["reads"].get((hold.SESSION[i], d))
        if x is None:                               # the loop has not read it yet: say so, never read it here
            gap = board.CC + f"the closes before {since} are still being read — the since-clock starts there"
            break
        if lab(x) == lab(e):
            since = hold.SESSION[i]
        else:
            was = {"word": lab(x), "until": since}
            break
    k, t1 = e["buy"]["k"], hold.hm(hold.mm(asof) + 1)
    same_l = tr["role"] == "long" and tr["side"] == bs
    Lr = res if same_l else hold.read({"side": bs, "role": "long", "t0": t1, "k": k, "p0": None, "qty": tr["qty"]},
                                      Dl["minutes"], F["pivots"], idx=idx, late=late)
    vb = out["validate"] if same_l else validate.word({**out, "trade": {**tr, "side": bs, "role": "long", "k": k},
                                                       "thesis": Lr["th"], "entry": Lr["entry"], "now": Lr["rows"][-1]}) \
        if Lr.get("ok") else None
    same_s = tr["role"] == "short" and tr["side"] == ss and float(tr["k"]) == float(k)
    Sr = res if same_s else hold.read({"side": ss, "role": "short", "t0": t1, "k": k, "p0": None, "qty": tr["qty"]},
                                      Dl["minutes"], F["pivots"], idx=idx, late=late)
    ws = expression.writer(Dl, ip, d, ss, k, Sr=Sr)
    vs = mine if same_s else _expr_verdict(ws, out.get("setup"), F["expiry"])
    b = expression.base(e["word"])
    named = "buy" if b in ("BUY", "LEANS BUY") else "sell" if b in ("SELL", "LEANS SELL") else None
    zero = bool(F["expiry"].get("zero_dte"))

    def card(lg, role, rd, v, codes):
        g_ = Dl["gk"](k, lg, ip)
        return {"side": lg, "role": role, "k": k, "atm": f"ATM {k:,.0f}; one strike ITM reads the same facts",
                "expiry": F["expiry"].get("text"), "px": Dl["px"](k, lg, ip), "px_t": asof, "px_tag": "I",
                "delta": g_[0] if g_ else None, "gamma": g_[1] if g_ else None, "greeks_tag": "M",
                "greeks_why": None if g_ else board.CC + "no greeks for this strike in the chain record",
                "entry": rd["entry"]["verdict"] if rd.get("ok") else None, "validate": v,
                "named": named == ("buy" if role == "long" else "sell"),
                "refused": _expr_refused(e, codes)}      # σ: /api/hold/sigma, after the answer (a REST fetch)
    buy = card(bs, "long", Lr, vb, e["ref_b"])
    sell = card(ss, "short", Sr, vs, e["ref_s"])
    L = ws.get("L")
    sell.update(wall=ws.get("wall"), s4=expression.S4_ROW if zero else None,
                line_vs_strike=None if L is None else
                f"your line {L:,.1f} sits {abs(k - L):,.1f} pts {'below' if L < k else 'above'} your strike [M]")
    exp_txt = (F["expiry"].get("text") or "") + (" Theta is fastest and gamma largest today: the first pays a writer, "
                                                "the second hunts her; §B's Cushion reads both." if zero else "")
    words = {"word": e["word"], "base": b, "leg": e["word"].split(" · ")[0].split(" ")[-1] if named else None,
             "leans": b.startswith("LEANS"), "named_by": e["named_by"], "strength": e["strength"], "lead": e["lead"],
             "refusal": e["refusal"], "refused": _expr_refused(e, e["refusal"]), "since": since, "was": was,
             "since_gap": gap, "read_at": tc, "nb": e["nb"], "ns": e["ns"], "nn": e["nn"], "count": e["count"]}
    facts = [{"name": n, "state": s, "absence": a, "text": t, "tag": expression.TAG[n]} for n, s, a, t in e["facts"]]
    return {**base_, "ok": True, **words, "facts": facts, "buy": buy, "sell": sell, "zero_dte": zero,
            "printed": {"drag": _expr_drag(idx), "expiry": exp_txt, "regime": expression.regime_board(D["minutes"][ic])},
            "log": {**{x: words[x] for x in ("word", "named_by", "refusal", "since", "nb", "ns", "read_at")},
                    "facts": e["facts"],
                    "legs": {lg: {"side": c["side"], "k": k, "px": c["px"], "delta": c["delta"], "entry": c["entry"],
                                  "word": (c["validate"] or {}).get("word")} for lg, c in (("buy", buy), ("sell", sell))}}}


def _expr_reply(poller, payloads, idx):
    """GET /api/hold/expr: the slip's quiet line (§F.1) -- her zone setup's direction on its closed bar. Cheap:
    no close is read here."""
    F = _hold_facts(poller, idx)
    if F is None:
        return {"ok": False, "idx": idx, "why": board.CC + "no finished minute of today's session on the chain grid yet"}
    su = _hold_setup(payloads, idx, F["day"], F["asof"], 1)
    return {"ok": True, "idx": idx, "asof": F["asof"], "setup_line": _expr_setup_line(su)}


def _hold_loop(poller):
    """The forward logs, once a minute per index, for session minutes only -- on its own
    thread, so a slow REST candle fetch can never cost the tape a build. The 15:29
    minute finishes at 15:30:00, so the gate reads the clock 90 s back; the close-time
    import completes anything a dead minute missed."""
    from chain_live import IST, in_session
    from datetime import datetime, timedelta
    last = {}
    while True:
        time.sleep(10)
        if _HOLD.pop("expr_complete", False):         # the close-time import's ask (EXPRESSION-PREREG §E.3)
            _expr_complete(poller)
        now = datetime.now(IST)
        if not in_session(now - timedelta(seconds=90)):
            continue
        for idx in instruments.ENABLED:
            m = now.strftime("%H:%M")
            if last.get(idx) == m:
                continue
            last[idx] = m
            try:
                _hold_tick(poller, idx)
            except Exception:
                log.exception("hold log failed %s", idx)


_HOLD_SYM = re.compile(r"^(NIFTY|SENSEX|BANKNIFTY)\d{2}[0-9A-Z]{3}(\d+)(CE|PE)$")


def _hold_trips(text, day):
    """Her Zerodha tradebook CSV -> flat-to-flat round trips of `day`, long when the
    first fill buys, short when it sells. -> (trades, skipped)."""
    import csv
    import io
    fills, skipped = [], []
    for r in csv.DictReader(io.StringIO(text)):
        if (r.get("trade_date") or "") != day:
            continue
        m = _HOLD_SYM.match(r.get("symbol") or "")
        try:
            q, p = int(float(r["quantity"])), float(r["price"])
            t = (r.get("order_execution_time") or "")[11:19]
            bs = (r.get("trade_type") or "").lower()
        except (KeyError, TypeError, ValueError):
            m = None
        if not m or bs not in ("buy", "sell") or not _HOLD_T.match(t):
            skipped.append(r.get("symbol") or "?")
            continue
        fills.append((t, r["symbol"], m.group(1), float(m.group(2)), m.group(3), bs, q, p, r.get("expiry_date")))
    trips, book = [], {}
    for t, sym, idx, k, side, bs, q, p, exp in sorted(fills):
        st = book.get(sym)
        if st is None or st["pos"] == 0:
            st = book[sym] = {"idx": idx, "k": k, "side": side, "role": "long" if bs == "buy" else "short",
                              "t0": t, "pos": 0, "in": [], "exit_t": None, "expiry": exp}
        sg = 1 if bs == "buy" else -1
        if (st["role"] == "long") == (sg > 0):
            st["in"].append((q, p))
        else:
            st["exit_t"] = t
        st["pos"] += sg * q
        if st["pos"] == 0:
            trips.append(st)
    trips += [st for st in book.values() if st["pos"] != 0]          # still open at the import
    out = []
    for st in trips:
        qin = sum(q for q, _ in st["in"])
        tr, why = _hold_trade({**st, "p0": round(sum(q * p for q, p in st["in"]) / qin, 2) if qin else None,
                               "qty": qin, "exit_t": st["exit_t"] if st["pos"] == 0 else None}, "import")
        (out.append(tr) if tr else skipped.append(f"{st['idx']} {st['k']:g}{st['side']} {st['t0']}: {why}"))
    return out, skipped


def _hold_import(poller, text):
    """POST /api/hold/import -- the close-time import (§8, S5). Every trade of TODAY in
    her tradebook that she did not mark is replayed causally from the day record and
    logged `src: import`; the side log and the marked trades are completed to the
    latest finished minute. An empty body only completes."""
    day = _board_clock()[0]
    trips, skipped = _hold_trips(text, day) if text.strip() else ([], [])

    def same(m, t):
        return (m["idx"] == t["idx"] and m["k"] == t["k"] and m["side"] == t["side"] and m["role"] == t["role"]
                and abs(hold.mm(m["t0"]) - hold.mm(t["t0"])) <= 2)
    n_broker = 0
    with HOLD_TRADES_LOCK:
        marked = list(_hold_trades())
        for t in trips:
            for m in marked:
                if t["exit_t"] and same(m, t):
                    # the tradebook's exit BESIDE the one she clicked: additive, it never changes exit_t
                    # or a logged row; which of the two §7 reads is her call (REVIEW P1-9)
                    m["exit_t_broker"] = t["exit_t"]
                    n_broker += 1
    if n_broker:
        _save_day_state()
    new = [t for t in trips if not any(same(m, t) for m in marked)]
    written = {idx: _hold_tick(poller, idx, extra=[t for t in new if t["idx"] == idx], expr=False)
               for idx in instruments.ENABLED}
    _HOLD["expr_complete"] = True            # THE EXPRESSION's log: the hold loop's thread, never this request
    return {"ok": True, "day": day, "trips": len(trips), "imported": [t["id"] for t in new],
            "matched_marked": len(trips) - len(new), "skipped": skipped, "rows_written": written,
            "expr": "the expression log completes on the hold thread within about 10 s",
            "files": [hold_log.path("hold", day), hold_log.path("side", day), hold_log.path("expr", day)]}


def _receipts_words(day):
    """The engine's words per trade for a day (fold_live's RECORD: today from the engines, a past day off the files) --
    RECEIPTS reads the word at her exit for amber exits. Additive: no words, no amber read."""
    r = fold_live.reply("/api/fold/record", {"day": [day]}, [])
    return {t["id"]: t.get("words") or [] for t in r.get("trades") or []} if isinstance(r, dict) and r.get("ok") else {}


def _receipts_get():
    """GET /api/receipts: every closed trade's receipt and the scoreboard (today / this week / all time). Read-only."""
    from chain_live import CHAIN_DIR
    day = _board_clock()[0]
    with HOLD_TRADES_LOCK:
        live = [dict(t) for t in _hold_trades()]
    return receipts.build(day_state.DIR, str(CHAIN_DIR), day, words_fn=_receipts_words, extra_today=live)


def _receipts_import(text, confirm):
    """POST /api/receipts/import {csv, confirm}: her Zerodha tradebook -> round trips (src import), checked at the mark's
    door (_hold_trade). Without confirm: the preview. With it: each touched day file is backed up, past days written,
    today's trips appended to the live list (and saved). Idempotent on the trip id and every fill's trade_id. Never an order."""
    day = _board_clock()[0]
    plan = receipts.import_plan(text, day_state.DIR, door=_hold_trade)
    slim = {d: {"new": [{k: t.get(k) for k in ("id", "t0", "exit_t", "qty", "p0", "exit_px")} for t in x["new"]],
                "have": x["have"], "refused": x["refused"]} for d, x in plan["days"].items()}
    out = {"ok": True, "confirm": bool(confirm), "fills": plan["fills"], "skipped": plan["skipped"], "days": slim}
    if not confirm:
        return out
    with HOLD_TRADES_LOCK:
        w = receipts.import_write(plan, day_state.DIR, day)
        trades = _hold_trades()
        have = {t["id"] for t in trades}
        add = [t for t in w["for_today"] if t["id"] not in have]
        trades += add
        if add:
            _HOLD["dirty"] = True
    if add:
        _save_day_state()
    try:                                    # F13a (25 Oct review, A76): the CSV's days are on record (an empty CSV: today), so that day's nudge stops
        os.makedirs(IMPORT_DIR, exist_ok=True)
        for d in (plan["days"] or {day: 0}):
            with open(os.path.join(IMPORT_DIR, f"import_{d}.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({"day": d, "t": time.strftime("%H:%M:%S"), "fills": plan["fills"], "wrote": w["wrote"],
                                    "today": [t["id"] for t in add]}) + "\n")
    except OSError:
        log.exception("tradebook import mark")
    return {**out, "wrote": {**w["wrote"], **({day: [t["id"] for t in add]} if add else {})}, "backups": w["backups"]}


VALIDATE_DIR = os.path.join("data", "validate")    # F12 (25 Oct review, A75): her VALIDATE presses, press_<day>.jsonl
_VALIDATE_LOCK = threading.Lock()
_PRESS_KEY = ("t", "idx", "K", "ty", "side")


def _validate_press(doc):
    """POST /api/validate/log (F12, A75): one VALIDATE press as Validate's engine.js computed it (rev 3 / 3.1, §1p / §1q) --
    the word, its counts, its checks and `stale` (the face read CAN'T CHECK) -- kept once per (t, idx, K, ty, side) in data/validate/press_<day>.jsonl, on the
    server's own day, market hours only (_market_hours, the one gate). A LOG ONLY: nothing reads it back, nothing is
    recomputed here, and no rule changes on it."""
    day, hm = _board_clock()
    row = {k: doc.get(k) for k in _PRESS_KEY + ("px", "rev", "word", "counts", "checks", "stale")}
    if not (isinstance(row["t"], str) and _HOLD_T.match(row["t"]) and row["idx"] in instruments.ENABLED
            and isinstance(row["K"], (int, float)) and row["ty"] in ("CE", "PE") and row["side"] in ("BUY", "SELL")
            and isinstance(row["word"], str) and isinstance(row["rev"], str)
            and (row["stale"] is None or isinstance(row["stale"], bool))):
        return {"ok": False, "why": "not logged — a press needs t, idx, K, ty, side, rev and word (stale, if sent, a bool)"}
    if not _market_hours(day, day, hm):
        return {"ok": False, "why": "not logged — outside market hours"}
    key, path = tuple(row[k] for k in _PRESS_KEY), os.path.join(VALIDATE_DIR, f"press_{day}.jsonl")
    with _VALIDATE_LOCK:
        try:
            with open(path, encoding="utf-8") as f:   # ponytail: a scan per press (tens a day); a seen-set if they run to thousands
                for line in f:
                    try:
                        if tuple(json.loads(line).get(k) for k in _PRESS_KEY) == key:
                            return {"ok": True, "new": False}
                    except (ValueError, AttributeError):
                        continue
        except FileNotFoundError:
            pass
        os.makedirs(VALIDATE_DIR, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(row, day=day, at=time.strftime("%H:%M:%S")), ensure_ascii=False, default=str) + "\n")
    return {"ok": True, "new": True}


# F13 (25 Oct review, A76; TRADER F07): intake had stalled -- 4 of her last 10 sessions recorded in full, no tradebook import
# since 3 Oct -- and nothing said so. Two display-only checks ride /api/health for 5173, the Float and Validate.
REC_DUE = (("book", "09:20"), ("chain", "09:20"), ("calls", "09:20"), ("read", "09:25"), ("GoCharting", "09:20"))   # read: its 09:20 mark lands after its grace
REC_END = "15:30"
FRAME_QUIET_S = 120                                # no frame POST for 2 min: the panel's record is not being written
IMPORT_DIR = os.path.join("data", "receipts")      # one row per confirmed tradebook import, import_<day>.jsonl (_receipts_import)
_REC = {"day": None, "text": None}                 # the last recording state logged to data/feed_log.jsonl
_REC_LOCK = threading.Lock()


def _ist(now=None):
    from datetime import datetime
    from chain_live import IST
    return datetime.fromtimestamp(time.time() if now is None else now, IST)


def _recording(now=None):
    """F13b: which of today's logs is not being written, 09:20-15:30 IST on a weekday; None outside it. {ok, missing, text}:
    `missing` names each log with no row today (book, chain, calls; read from 09:25) and GoCharting when no frame POST came in
    FRAME_QUIET_S. Each change of `text` within a day is ONE row in data/feed_log.jsonl through feed_health's writer (the
    day's first look only when something is missing). Display only: nothing reads it but the faces."""
    from chain_live import CHAIN_DIR
    d = _ist(now)
    day, hm = d.strftime("%Y-%m-%d"), d.strftime("%H:%M")
    if d.weekday() >= 5 or not "09:20" <= hm < REC_END:
        return None

    def wrote(paths):
        for p in paths:
            try:
                if os.path.getsize(p) > 0:
                    return True
            except OSError:
                continue
        return False
    files = {"book": [book_log.day_path(day, i) for i in instruments.ENABLED],
             "chain": [str(CHAIN_DIR / f"chain_{i}_{day}.jsonl") for i in instruments.ENABLED],
             "calls": [calls_log.path(day)], "read": [os.path.join(READ_DIR, f"read_{day}.jsonl")]}
    last = feed_health.last_post(day)
    missing = [k for k, due in REC_DUE if hm >= due and (
        (last is None or d.timestamp() - last > FRAME_QUIET_S) if k == "GoCharting" else not wrote(files[k]))]
    text = "RECORDING NAHI: " + ", ".join(missing) if missing else None
    with _REC_LOCK:
        if (_REC["day"], _REC["text"]) != (day, text) and (_REC["day"] == day or text):
            feed_health._log({"t": d.strftime("%H:%M:%S"), "day": day, "idx": "RECORD",
                              "from": _REC["text"] if _REC["day"] == day else None, "to": text or "RECORDING OK",
                              "since": d.strftime("%H:%M:%S"), "why": "the recording check (25 Oct review F13b)"})
        _REC.update(day=day, text=text)
    return {"ok": not missing, "missing": missing, "text": text}


def _tradebook_due(now=None):
    """F13a: after 15:30 on a weekday whose book recorded today, no confirmed tradebook import today -> {"due": True}. The faces
    say "tradebook aaj import nahi" and link pro.html's RECORD, the existing import door; she exports the CSV from Kite
    herself and nothing here logs in for her. Display only."""
    d = _ist(now)
    day = d.strftime("%Y-%m-%d")
    ran = d.weekday() < 5 and d.strftime("%H:%M") >= REC_END and any(os.path.isfile(book_log.day_path(day, i)) for i in instruments.ENABLED)
    return {"due": bool(ran) and not os.path.isfile(os.path.join(IMPORT_DIR, f"import_{day}.jsonl"))}


def _health_safe(fn):
    """/api/health is how 5173 decides the backend is alive: a display-only check that raises gives None, logged, never raised."""
    try:
        return fn()
    except Exception:
        log.exception("/api/health: %s", fn.__name__)
        return None


def _frame_chain(poller, idx):
    """frame.chain (API-v3, the panel's mark slip): the latest option-chain snapshot as {atm, step, ts,
    strikes: [{k, ce, pe}]} with ce / pe the LTPs. `atm` sits on the options' own forward -- F* = k + CE - PE at
    the strike nearest the spot [I] -- never on the chain's spot print (the future trades 30-90 points off the
    index, HANDOFF §6b). Older than 3 minutes (or rebuilt from the day file): `stale: true`, with the age."""
    from datetime import datetime
    from chain_live import IST, _sec_of_day
    snap = (getattr(poller, "prevs", None) or {}).get(idx) if poller else None
    rows = sorted((r for r in (snap or {}).get("strikes") or [] if isinstance(r.get("k"), (int, float))), key=lambda r: r["k"])
    if not rows or not snap.get("ts"):
        return {"ok": False, "why": board.CC + "no chain snapshot yet"}
    ks = [r["k"] for r in rows]
    step = min((b - a for a, b in zip(ks, ks[1:]) if b > a), default=None)
    spot = snap.get("spot")
    near = min(rows, key=lambda r: abs(r["k"] - spot)) if isinstance(spot, (int, float)) else rows[len(rows) // 2]
    ce, pe = (near.get("ce") or {}).get("ltp"), (near.get("pe") or {}).get("ltp")
    F = near["k"] + ce - pe if isinstance(ce, (int, float)) and isinstance(pe, (int, float)) else None
    mode = ((getattr(poller, "boxes", None) or {}).get(idx) or {}).get("mode")
    age = (_sec_of_day(datetime.now(IST)) - snap["sec"]) % 86400 if isinstance(snap.get("sec"), (int, float)) else None
    out = {"ok": True, "ts": snap["ts"], "step": step, "F": None if F is None else round(F, 1),
           "atm": min(ks, key=lambda k: abs(k - F)) if F is not None else None,
           "atm_why": None if F is not None else board.CC + f"no CE and PE price at {near['k']} to set the forward",
           "strikes": [{"k": r["k"], "ce": (r.get("ce") or {}).get("ltp"), "pe": (r.get("pe") or {}).get("ltp")} for r in rows],
           "age_s": age, "tag": {"M": ["strikes", "ts"], "I": ["F", "atm"]}}
    if mode == "restored" or (age is not None and age > 180):
        out["stale"] = True
        out["stale_why"] = ("rebuilt from the day file, not a live snapshot" if mode == "restored"
                            else f"chain snapshot {age // 60} min old")
    return out


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, payloads=None, late=None, **kw):
        self.payloads = payloads or {}     # idx -> {"payload": bytes, "session": ...}
        # Resolved per REQUEST rather than when the factory was built: the
        # socket is now bound BEFORE the chain poller exists, so the poller is
        # handed over through `late` once it does. See main() for why the bind
        # has to come first.
        late = late or {}
        self.chains = late.get("chains")
        self.poller = late.get("poller")
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
        if self.path.startswith("/api/receipts/import"):
            # RECEIPTS' tradebook import (receipts.py): {csv, confirm}; a preview unless confirm, and every touched day
            # file backed up before a write. Same-origin only, as the hold doors; CAPPED; never an order.
            site, origin = self.headers.get("Sec-Fetch-Site"), self.headers.get("Origin") or ""
            if site is not None and site not in ("same-origin", "same-site", "none") and not origin.startswith("chrome-extension://"):
                self._json(json.dumps({"ok": False, "why": "refused — a POST from another site"}).encode(), 403)
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if not 0 < n < 2097152:
                    self._json(b'{"ok":false,"why":"bad request"}', 400)
                    return
                doc = json.loads(self.rfile.read(n) or b"{}")
                out = _receipts_import(str(doc.get("csv") or ""), bool(doc.get("confirm")))
            except Exception as e:           # never 500 the RECORD
                log.exception("receipts import")
                out = {"ok": False, "why": board.CC + f"{type(e).__name__}: {e}"}
            self._json(json.dumps(out, default=str).encode())
            return
        if self.path.startswith("/api/validate/log"):
            # F12 (25 Oct review, A75): Validate's press log, the word engine.js computed, kept once (_validate_press).
            # Same-origin only, the hold doors' rule; CAPPED; a log -- never an order, never a rule.
            site, origin = self.headers.get("Sec-Fetch-Site"), self.headers.get("Origin") or ""
            if site is not None and site not in ("same-origin", "same-site", "none") and not origin.startswith("chrome-extension://"):
                self._json(json.dumps({"ok": False, "why": "refused — a POST from another site"}).encode(), 403)
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if not 0 < n < 65536:
                    self._json(b'{"ok":false,"why":"bad request"}', 400)
                    return
                out = _validate_press(json.loads(self.rfile.read(n) or b"{}"))
            except Exception as e:           # never 500 a log
                log.exception("validate press")
                out = {"ok": False, "why": board.CC + f"{type(e).__name__}: {e}"}
            self._json(json.dumps(out, default=str).encode())
            return
        # PaperDesk's paper fills, tagged with the tape context they were
        # taken in. A SEPARATE file from trigger_log.jsonl on purpose:
        # trigger_log counts rule populations under a quarantine discipline,
        # and operator-taken fills mixed into it would corrupt every count the
        # server publishes. The two join on (index, day, t) when §5e asks
        # "of the zone arms, which did I actually take". Fire-and-forget on
        # the extension side — a failure here must never block a fill.
        if self.path.startswith("/api/hold/"):
            # THE HOLD WINDOW's two doors. /api/hold/trades {op: mark|exit|reopen|unmark}:
            # the trades she marks, kept in data/day_state/ so a restart keeps
            # them. /api/hold/import (text/csv, may be empty): the close-time
            # tradebook import. CAPPED like every POST here; never an order.
            # A POST another site's page made is refused (REVIEW §P2): a no-cors
            # text/plain POST needs no preflight and could mark or unmark trades
            # in her forward record. The UI posts through the Vite proxy
            # (same-origin); a client that sends no Sec-Fetch-Site (curl) passes.
            # ...and the one legitimately cross-site sender, the extension's service worker (orderflow-desk
            # sw.js -> /api/hold/trades, 2026-09-29), let in by its chrome-extension:// Origin, exactly as
            # the frame door does (P1-07). A web page's Origin is still refused.
            site, origin = self.headers.get("Sec-Fetch-Site"), self.headers.get("Origin") or ""
            if site is not None and site not in ("same-origin", "same-site", "none") and not origin.startswith("chrome-extension://"):
                self._json(json.dumps({"ok": False, "why": "refused — a POST from another site"}).encode(), 403)
                return
            try:
                try:
                    n = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    n = -1
                cap = 1048576 if self.path.startswith("/api/hold/import") else 8192
                if not 0 <= n < cap:
                    self._json(b'{"ok":false,"why":"bad request"}', 400)
                    return
                body = self.rfile.read(n) if n else b""
                if self.path.startswith("/api/hold/import"):
                    out = _hold_import(self.poller, body.decode("utf-8-sig", "replace"))
                else:
                    doc = json.loads(body or b"{}")
                    op = doc.get("op")
                    with HOLD_TRADES_LOCK:
                        trades = _hold_trades()
                        if op == "mark":
                            tr, why = _hold_trade(doc)
                            out = {"ok": False, "why": board.CC + why} if tr is None else None
                            # a double-click, not a second trade (REVIEW P1-8): the same contract, still
                            # open, marked within 60 s of this one
                            dup = tr and next((t for t in trades if not t.get("exit_t")
                                               and all(t[f] == tr[f] for f in ("idx", "k", "side", "role"))
                                               and abs(_hold_sec(t["t0"]) - _hold_sec(tr["t0"])) <= 60), None)
                            if dup:
                                out = {"ok": False, "why": f"already marked — {dup['idx']} {dup['k']:g} {dup['side']} "
                                                           f"{dup['role']} in at {dup['t0']} is open"}
                            elif tr is not None:
                                th, why1 = trade_record.thesis_from(doc, time.strftime("%H:%M:%S"))
                                rs, why2 = trade_record.roles_from(doc, tr)
                                if why1 or why2:
                                    out = {"ok": False, "why": board.CC + (why1 or why2)}
                                else:
                                    tr = dict(tr, at=time.time(), **({"thesis": th} if th else {}), **({"roles": rs} if rs else {}))
                                    tags = trade_record.entry_tags(tr, trades, time.time())   # FLIP / COOLDOWN: warned, never refused
                                    if tags:
                                        tr["tags"] = tags
                                    trades[:] = [t for t in trades if t["id"] != tr["id"]] + [tr]
                        elif op in ("exit", "unmark", "reopen"):
                            tr = next((t for t in trades if t["id"] == doc.get("id")), None)
                            ex = str(doc.get("exit_t") or time.strftime("%H:%M:%S"))      # none given: now
                            out = None
                            if tr is None:
                                out = {"ok": False, "why": board.CC + f"no marked trade {doc.get('id')} today"}
                            elif op == "unmark":
                                trades.remove(tr)
                            elif op == "reopen":
                                # the UI's 10 s "undo I'm out", for an exit clicked in the last 120 s. Minute
                                # rows the log wrote meanwhile keep their after_exit (write-once, hold_log.py).
                                if not tr.get("exit_t") or time.time() - (tr.get("exit_at") or 0) > 120:
                                    out = {"ok": False, "why": "nothing to undo — no exit in the last 120 s"}
                                else:
                                    tr["exit_t"] = None
                                    tr.pop("exit_t_broker", None)
                                    tr.pop("exit_at", None)
                            elif (op == "exit" and tr.get("exit_t") and time.time() - (tr.get("exit_at") or 0) < 60
                                  and (not doc.get("exit_t") or ex >= tr["exit_t"])):
                                # her second click on a slow answer (the client gives up in 8 s): the first exit stands, untouched (25 Oct F10).
                                # Every face: Validate sends no exit_t, the panel / Float / Mark send the click time -- a later one is the same
                                # click; an EARLIER exit_t is a correction, and any exit 60 s or more after the first passes
                                out = {"ok": True, "why": f"already out at {tr['exit_t']}", "trades": list(trades)}
                            elif not _HOLD_T.match(ex) or ex < tr["t0"]:
                                out = {"ok": False, "why": board.CC + "exit time must be HH:MM[:SS], not before the entry"}
                            else:
                                tr["exit_t"], tr["exit_at"] = ex, time.time()
                                rd = _VAL_LAST.get(tr["id"])          # the whole trade out at once: its lamps, its tags
                                trade_record.snap_exit(tr, rd)
                                for tag in trade_record.exit_tags("MANUAL", rd):
                                    if tag not in tr.setdefault("tags", []):
                                        tr["tags"].append(tag)
                        elif op in trade_record.OPS:
                            # her record (Validate spec): thesis, role_add, role_exit, ack, replan, peek. A RECORD of
                            # what she did on her broker -- never an order. More lots out than a role holds is refused.
                            tr = next((t for t in trades if t["id"] == doc.get("id")), None)
                            why = (board.CC + f"no marked trade {doc.get('id')} today" if tr is None else
                                   trade_record.apply(tr, op, doc, time.strftime("%H:%M:%S"), time.time(), _VAL_LAST.get(tr["id"])))
                            out = {"ok": False, "why": why} if why else None
                        else:
                            out = {"ok": False, "why": board.CC + "op must be mark, exit, reopen, unmark or " + ", ".join(trade_record.OPS)}
                        out = out or {"ok": True, "trades": list(trades)}
                    if out["ok"]:
                        _HOLD["dirty"] = True
                        _save_day_state()
                self._json(json.dumps(out, default=str).encode())
            except Exception as e:      # never 500 at the window
                log.exception("hold post %s", self.path)
                self._json(json.dumps({"ok": False, "why": f"{type(e).__name__}: {e}"}).encode())
            return

        if self.path.startswith("/api/dext/candles"):
            # GATE 3 (dext_log.py; docs/dext/README.md): the Dext extension's closed 1m candles + getData rows, RECORDED and
            # nothing else -- no frame build, no engine, append only (the 2026-09-18 wedge was a whole-file rewrite per
            # POST). The hold doors' rule: a web page's Origin is refused, the extension's service worker is let in.
            site, origin = self.headers.get("Sec-Fetch-Site"), self.headers.get("Origin") or ""
            if site not in (None, "same-origin", "same-site", "none") and not origin.startswith("chrome-extension://"):
                self._json(json.dumps({"ok": False, "why": "refused — a POST from another site"}).encode(), 403)
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if not 0 < n < 4194304:              # the extension sends <= 1,500 candles and <= 3 MB a batch
                self._json(b'{"ok":false,"why":"bad request"}', 400)
                return
            try:
                out, code = dext_log.store(json.loads(self.rfile.read(n))), 200
            except ValueError as e:              # dext_log.Refused, or a malformed body: nothing stored
                out, code = {"ok": False, "why": f"refused — {e}"}, 400
            except Exception as e:               # a disk failure: said, never a 500
                log.exception("dext candles")
                out, code = {"ok": False, "why": f"could not store — {type(e).__name__}: {e}"}, 200
            self._json(json.dumps(out).encode(), code)
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
        if self.path.startswith("/api/frame"):
            # THE FRAME DOOR (pro-tool P1-07): the hold doors' rule, with the one sender that is
            # legitimately cross-site let in. A no-cors text/plain POST from any page she visits
            # needs no preflight, and tape_log writes each bar once by `t`, so a forged bar that
            # lands first locks the real one out. The extension posts from its SERVICE WORKER
            # (orderflow-desk sw.js), whose Origin is its own chrome-extension:// id; curl and the
            # tests send no header at all. The first senders are logged so the first live session
            # shows what sw.js actually sends. Revert: delete the `if site not in` block.
            site, origin = self.headers.get("Sec-Fetch-Site"), self.headers.get("Origin") or ""
            if _FRAME_DOOR["seen"] < 3:
                _FRAME_DOOR["seen"] += 1
                log.info("frame door: Sec-Fetch-Site=%r Origin=%r Sec-Fetch-Mode=%r", site, origin,
                         self.headers.get("Sec-Fetch-Mode"))
            if site not in (None, "same-origin", "same-site", "none") and not origin.startswith("chrome-extension://"):
                self._json(json.dumps({"ok": False, "why": "refused — a POST from another site"}).encode(), 403)
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if not 0 < n < 4194304:              # a whole 5m day with ladders is ~1 MB
                self._json(b'{"ok":false,"why":"bad request"}', 400)
                return
            try:
                doc = json.loads(self.rfile.read(n) or b"{}")
                idx = str(doc.get("idx") or "NIFTY")
                if int(doc.get("interval") or 0) != 5:
                    self._json(json.dumps({"ok": False, "why": "interval must be 5 minutes; got "
                                           f"{doc.get('interval')!r}. The band machine's windows are "
                                           "counted in bars, so another interval is a different tool "
                                           "(band_rotation.py:850-861)."}).encode())
                    return
                day = str(doc.get("session") or "").split("|")[-1] or time.strftime("%Y-%m-%d")
                # after the close the frame is the last session snapshot: bars
                # and marks stamped 15:30 or later never reach the build, the
                # record, the ladder file or the scorer (_session_only)
                doc = _session_only(doc)
                # FEED HEALTH (P3): every accepted post is a data point (arrival time, heartbeat, newest bar). Never raises.
                feed_health.on_post(idx, day, doc)
                if "push" in doc:                        # READ-2's JAGAH: optional; absent or malformed keeps the last
                    pc = _push_clean(doc.get("push"))
                    if pc is not None:
                        _PUSH[idx] = {"day": day, "push": pc}
                # `fr` is fully built -- including the log-write decision --
                # BEFORE the lock is taken, and never mutated again once
                # published: GET /api/frame json.dumps()s this same object
                # under the lock, and mutating it outside the lock (the
                # earlier placeholder set log_row_written after publishing)
                # is a race with that serialization.
                fr = frame.build(doc, _book_for(self, idx), time.strftime("%H:%M"))
                fr["day"] = day
                try:                                        # the panel draws the same band as every other face
                    fr["feed"] = _feed_read(idx, day)
                except Exception as e:                      # never at the frame's expense
                    fr["feed"] = {"idx": idx, "state": None, "why": f"could not check — feed health failed: {e}", "alarm": False, "sound": False}
                # A post outside its own session adds nothing to that session's record: GoCharting shows the last
                # session before 09:15, all weekend and after the close, stamped with that day. On 3 Oct such posts
                # rewrote 1 Oct's 244 MB record every minute and tore a line into it; 30 Sep's pre-open landed in 29 Sep's.
                now_day, now_hm = _board_clock()
                in_session = _market_hours(day, now_day, now_hm)
                fr["record"] = {"written": frame_log.append_if_changed(fr, day, idx) if in_session else False}
                # THE LADDER RECORD (tape_log.py): each new closed bar and each
                # new extension mark, once. Fail-soft inside; nothing here can
                # change `ok`. Before the lock, like the frame write above.
                if in_session:                           # the marks writer behind the same gate (nothing on a weekend, another day, or off hours)
                    tape_log.append(doc, day, idx)
                    try:                                 # the v2 page's own mark log (doc.marks2), behind the same gate
                        tape_log.append_marks2(doc, day, idx)
                    except Exception:
                        log.exception("tape_log marks2")
                    try:                                 # the decoder's forward log: once per event, state and outcome
                        decoder_log.append(doc.get("decoder"), doc.get("closed") or [], day, idx)
                    except Exception:
                        log.exception("decoder_log append")
                # THE REV 6 ENGINE (fold_live.py, API-v3): the panel's `fold` (her open marked trade) and
                # `flat` reads ride on the frame, from the engine's cache. Isolated twice: a failure is a why.
                try:
                    fold_live.push(idx, "tape", doc.get("closed") or [])
                    trs = list(_hold_trades())
                    fr["fold"], fr["flat"] = fold_live.frame(idx, trs, any_idx=bool(doc.get("away")) and idx in instruments.ENABLED)
                    if isinstance(fr["fold"], dict) and fr["fold"].get("ok"):    # the panel's one voice (A52)
                        fr["fold"] = _in_trade(fr["fold"], trs)
                    elif fr["fold"] is None:
                        fr["receipt"] = _receipt_for(idx, trs)
                except Exception as e:                   # never at the frame's expense
                    fr["fold"], fr["flat"] = {"ok": False, "why": f"could not check — the engine failed: {e}"}, None
                try:
                    fr["chain"] = _frame_chain(self.poller, idx)
                except Exception as e:
                    fr["chain"] = {"ok": False, "why": f"could not check — the chain slip failed: {e}"}
                try:                                     # the panel's story; frame.build's sentence stays if this fails
                    fr["story"] = _story_for(idx, day, doc, fr, int(time.time() * 1000))
                except Exception:
                    log.exception("story compose")
                try:                                     # the live in-trade read (Validate): lamps, level, N/4, prompt
                    fr["validate"] = _validate_for(idx, day, doc, fr, int(time.time() * 1000))
                    if isinstance((fr.get("story") or {}).get("trade_read"), dict):
                        fr["story"]["trade_read"]["validate"] = fr["validate"]
                except Exception as e:
                    log.exception("validate read")
                    fr["validate"] = {"ok": False, "why": f"could not check — the validate read failed: {e}"}
                v2_ref = None                            # EXTENSION V2 (_frame_v2): a v2 page only; after the record
                if "rank_have" in doc or "build" in doc:
                    try:
                        v2, v2_ref = _frame_v2(idx, day)
                        fr.update(v2)
                    except Exception as e:               # never at the frame's expense
                        log.exception("frame v2")
                        for k in _V2_NONE + ("rank_ref_id",):
                            fr[k] = None
                        for k in ("read_why", "plan_why", "rank_ref_why"):
                            fr[k] = f"could not check — the v2 read failed: {e}"
                if in_session and isinstance(_own_fold(fr.get("fold"), idx), dict) and fr["fold"].get("ok"):
                    try:                                 # HOLD vs DECODER, once a minute while she is marked
                        decoder_log.minute(day, idx, now_hm, fr["fold"], (fr.get("story") or {}).get("trade_read"), fr.get("validate"))
                    except Exception:
                        log.exception("decoder_log minute")
                with _SENSES_LOCK:
                    _SENSES["tape"][idx] = {"doc": doc, "at": time.time()}
                    _SENSES["frame"][idx] = fr
                reply = {"ok": True, **fr}
                if v2_ref is not None and "rank_have" in doc and doc.get("rank_have") != fr.get("rank_ref_id"):
                    # once per session: the page sends back the id it holds. `read` is TapeMap's own (the READ's
                    # ranks, ~200 KB) -- the page never reads it, so it does not travel
                    reply["rank_ref"] = {k: v for k, v in v2_ref.items() if k != "read"}
                self._json(json.dumps(reply, default=str).encode())
                # forward-fills the day's log rows (taps, tells, control) so
                # the §8 kill conditions have something to execute against;
                # its own try/except -- a scoring failure must never touch
                # a reply that has already gone out
                # ONCE PER CLOSED BAR, NOT ONCE PER POST. `score_frame.write`
                # reads the WHOLE day file, parses every row, rescores and
                # writes it all back. On 2026-09-18 that file was 55 MB across
                # 2,026 rows and the extension posts every few seconds, so each
                # request held a 55 MB parse; ThreadingHTTPServer gave each one
                # a thread, the process reached 2.2 GB with ~70 sockets in
                # CLOSE_WAIT, and it stopped accepting connections without ever
                # raising -- twice today, which is exactly where the chain log
                # goes silent (10:59 and 13:34). Nothing the scorer fills can
                # change until a BAR CLOSES: every horizon it writes is measured
                # in bars or in minutes off a bar's close. So it runs when the
                # bar count moves, which is once per five minutes per index.
                # ponytail: a whole-file rewrite, now rare enough to survive.
                # Make it incremental if the record ever outgrows one bar's
                # worth of time.
                nbars = len(doc.get("closed") or [])
                if in_session and nbars != _SCORED_BARS.get(idx):
                    _SCORED_BARS[idx] = nbars
                    try:
                        score_frame.write(day, doc.get("closed") or [], idx=idx)
                    except Exception:
                        log.exception("score_frame write")
            except Exception as e:               # never 500 at a browser extension
                self._json(json.dumps({"ok": False, "why": str(e)}).encode(), 200)
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
            # The live UI is TapeMap v2 on Vite (5173, started by
            # start-v2.bat); a bookmark to this server's root lands there.
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:5173/")
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
                            "Dhan broker or --mock-chain")
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
                # WHAT THIS PROCESS COULD AND COULD NOT KNOW ABOUT TODAY. A
                # server started at 11:02 has a reconstructed morning for some
                # panels and no morning at all for others, and the difference
                # has to be readable from one place rather than inferred from
                # an empty chart. Names both lists and, when the start was
                # late, the sentence that says so.
                "coverage": _coverage(),
                # The RAM-only day series, restored from data/day_state/ so a
                # 19:30 cold open still shows the finished session. Observed
                # rows, not reconstructed ones -- see day_state.py.
                "day_restored": _SENSES.get("day_restored") or 0,
                # F13 (25 Oct review, A76): is today's record being written, and is today's tradebook imported (display only)
                "recording": _health_safe(_recording),
                "tradebook": _health_safe(_tradebook_due),
            }).encode())
            return
        if self.path.startswith("/api/data"):
            idx = self._idx()
            box = self.payloads.get(idx)
            if box is None:
                # Never serve one index's tape under another's name. The old
                # fallback chain quietly answered /api/data?idx=BANKNIFTY with
                # NIFTY's session — three identical panels that looked live
                # and were mislabelled.
                self._json(json.dumps({
                    "index": idx, "strike": None, "days": [],
                    "built_at": time.time(),
                    "live_error": f"no {idx} tape in this server mode — "
                                  f"start with: python server.py live"}).encode())
                return
            from live import clamp_interval
            q = parse_qs(urlsplit(self.path).query)
            interval = clamp_interval((q.get("interval") or [None])[0])
            pl = _session_payload(box, interval)
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
            # How much of this grid was REBUILT rather than seen. Every row
            # already carries its own `backfill` flag; this is the one-line
            # version a header can render without walking the rows.
            bf_marks = sum(1 for m in st.minutes.values()
                           if m.get("src") == "backfill")
            self._json(json.dumps({"ok": True, "index": idx,
                                   "interval": interval, "strikes": avail,
                                   "selected": strikes, "rows": rows,
                                   "chain_ok": chain_ok,
                                   "chain_why": chain_why,
                                   "backfill_marks": bf_marks,
                                   "marks": len(st.minutes),
                                   # Per-strike premium rides on each row under
                                   # `px`, for the SELECTED strikes only. An
                                   # empty `px` with no reason would read as
                                   # "no premium moved" -- house rule 6.
                                   "px_why": (None if strikes else
                                              "px is served for a named "
                                              "selection only -- add "
                                              "&strikes=<k,...>. A premium "
                                              "sum across strikes is not a "
                                              "quantity, and the whole chain "
                                              "would be ~180KB per poll"),
                                   "coverage": _coverage()}).encode())
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
                live.leg_pivots(body)            # fail-soft, per leg
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
            # ZONE (§1b) is her rule, its own population -- not the void one-candle
            # legacy. `legacy` was `rule != "5c"` and so counted every zone entry
            # as quarantined (591 = 335 zone + 256 untagged on 2026-09-23).
            zone = [r for r in entries if r.get("rule") == "zone"]
            legacy = [r for r in entries if r.get("rule") not in ("5c", "zone")]
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
            # ?day=YYYY-MM-DD | today -- a VIEW filter like ?idx=, for a chart that
            # only draws today's marks (PaperDesk's fade-gate join). The counts
            # below stay whole-file, exactly as they were.
            vday = ((q.get("day") or [""])[0] or "").strip()
            if vday == "today":
                vday = time.strftime("%Y-%m-%d")
            if vday:
                sel = [r for r in sel if r.get("day") == vday]
            self._json(json.dumps({
                "ok": True, "path": str(src), "rule": rule,
                "idx": want or None, "kind": kind, "day": vday or None,
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
                "zone": {"n": len(zone)},     # counted apart, never summed into five_c or legacy
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
        elif self.path.startswith("/api/oihist"):
            # THE PER-STRIKE MINUTE GRID AS IT SITS IN MEMORY. GET only.
            # `ChainState.minutes` has had exactly one reader (/api/oiflow,
            # which aggregates it away) and `ChainState.peak` has had none
            # over HTTP, so the breadth counts and the Field's fronts could
            # not be checked against the same numbers the brain used. Without
            # this the fronts are drawn from one ~10-second snapshot and the
            # ghost outlines cannot exist at all.
            #
            # `peak` is keyed by a (strike, side) TUPLE in memory, which JSON
            # has no key for, so it goes out as a LIST of rows rather than
            # being silently string-joined into something a reader has to
            # parse back apart.
            idx = self._idx()
            st = (getattr(self.poller, "states", None) or {}).get(idx) if self.poller else None
            mins = getattr(st, "minutes", None)
            peak = getattr(st, "peak", None)
            # THE NEAR-ATM FRONTS (research-findings §1d) RIDE HERE, not only
            # on the frame: this route is served straight out of the chain
            # poller's state and does not touch the extension at all, so "who
            # stopped building first" survives a dead GoCharting tab -- which
            # is exactly the morning of 2026-09-22, when the extension posted
            # once at 09:17 and stopped. `frame.py` calls the same function on
            # the same grid, so the rule exists once, in one language.
            rows = fronts.read(mins or {}, peak)
            # BOARD rev 3, ADDITIVE: the open per strike and side (carried in),
            # and the day's folds and FIRST FOLD off the same grid, cut to the
            # latest finished minute and cached per minute (_board_core).
            opens = _board_opens(self.poller, idx)
            try:
                core, core_why = _board_core(self.poller, idx), None
            except Exception as e:           # the new keys must never cost the old ones
                log.exception("oihist folds %s", idx)
                core, core_why = None, f"{type(e).__name__}: {e}"
            self._json(json.dumps({
                "ok": mins is not None,
                "idx": idx,
                "why": None if mins is not None else
                       "the chain poller has no state for this index yet",
                # null, not [], for the reason frame.py gives at its own
                # `fronts` key: an empty list reads as "checked, none found".
                "fronts": rows or None,
                "fronts_why": None if rows else
                              ("the chain poller has no state for this index yet"
                               if mins is None else
                               "no minute carries a spot and a strike grid yet"),
                "broke": fronts.broke(rows),
                "minutes": mins or {},
                "peak": [{"k": k, "side": s, "oi": v}
                         for (k, s), v in sorted((peak or {}).items())],
                # Which marks were REBUILT from REST candles rather than seen
                # by the socket (chain_backfill stamps `src` on the mark
                # itself). A reconstructed morning is worth having and is not
                # the same evidence as an observation.
                "backfill_marks": sorted(m for m, rec in (mins or {}).items()
                                         if (rec or {}).get("src") == "backfill"),
                "open": [{"k": k, "side": s, "oi": v} for (k, s), v in sorted(opens.items())],
                "open_why": None if opens else "no chain snapshot yet -- the open is oi - oi_chg off it",
                "folds": core["evs"] if core else None,
                "folds_asof": core["asof"] if core else None,
                "folds_why": (board.CC + (core_why or "the chain poller has no state for this index yet")
                              if core is None else None if core["evs"] else
                              board.NONE + "no sized front inside the nine has folded yet today"),
                "first": core["first"] if core else None,
                "first_why": None if core and core["first"] else (
                    board.NONE + "no §1d top-2 front has folded yet today" if core and core["cov"]["whole"]
                    else board.CC + "the grid is not whole from the open yet"),
            }, default=str).encode())
        elif self.path.startswith("/api/sides"):
            # THE SIDES READ (sides.py): ?idx= for one index, none for all three plus their count.
            want = (parse_qs(urlsplit(self.path).query).get("idx") or [None])[0]
            want = want.upper() if want and want.upper() in instruments.ENABLED else None
            try:
                out = _sides_reply(self.poller, self.chains, want)
            except Exception as e:           # a bad read must not 500 the face
                log.exception("sides")
                out = {"ok": False, "why": sides.CC + f"{type(e).__name__}: {e}"}
            self._json(json.dumps(out, default=str).encode())
        elif self.path.startswith("/api/trap"):
            # THE TRAP LAYER, SHADOW (trap.py): the trap thread's last read; ?idx= for one index.
            want = (parse_qs(urlsplit(self.path).query).get("idx") or [None])[0]
            want = want.upper() if want and want.upper() in instruments.ENABLED else None
            out = _TRAP["reply"]
            if out is None:
                out = {"ok": False, "rev": trap.REV, "why": trap.CC + "the trap read has not run yet"}
            elif want:
                out = dict(out, indices={want: out["indices"].get(want) or {"ok": False, "why": trap.CC + "no read for " + want}})
            self._json(json.dumps(out, default=str).encode())
        elif self.path.startswith("/api/board"):
            # BOARD rev 3's server half (notes §8 steps 2-6): headline, fronts
            # with carried/built, folds and FIRST, agreement, the trend box,
            # the mirror read and PCR -- for the latest FINISHED minute, cached
            # per index per minute. ?idx= and optional ?strike= / ?ce= / ?pe=.
            idx = self._idx()
            try:
                out = _board_reply(self.poller, idx, parse_qs(urlsplit(self.path).query))
            except Exception as e:           # a bad read must not 500 the face
                log.exception("board %s", idx)
                out = json.dumps({"ok": False, "idx": idx,
                                  "why": board.CC + f"{type(e).__name__}: {e}"}).encode()
            self._json(out)
        elif self.path.startswith("/api/day/record"):
            # The record has never had a reader. The day's ORDER FLOW lives in
            # it — the extension replays GoCharting's loaded footprint, so a
            # file whose first frame landed at 09:50 still carries events
            # stamped 09:15 (measured 2026-09-18). Streamed, never loaded.
            q = parse_qs(urlsplit(self.path).query)
            day = (q.get("day") or [time.strftime("%Y-%m-%d")])[0]
            idx = self._idx()
            rows, events = record_read.read(day, idx)
            self._json(json.dumps({
                "ok": True, "day": day, "idx": idx,
                "rows": rows, "events": events,
                "rows_why": None if rows else "no record for that day",
                "events_why": None if events else (
                    "no tape events recorded" if rows else "no record for that day"),
            }, default=str).encode())
        elif self.path.startswith("/api/surface"):
            # THE DAY, not just the snapshot (2026-08-25). The a/b/c story --
            # "vol aayi ya nikli, skew kab unwind hua" -- lived only in the
            # forward log, readable by grep and nobody else. `day` below is
            # that file read back at request time, so the panel can say what
            # the session DID and not only where it stands.
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
                try:
                    # REALIZED vol beside the IMPLIED one. The desk sells IV
                    # and pays RV, so a fitted smile with no realized number
                    # next to it is half the trade. [M], from captured bars.
                    rv, rv_why = _rv5(idx)
                    fit = out[idx].get("fit")
                    if isinstance(fit, dict):
                        fit["rv5"], fit["rv5_why"] = rv, rv_why
                except Exception as e:      # never 500 the panel over history
                    fit = out[idx].get("fit")
                    if isinstance(fit, dict):
                        fit["rv5"] = None
                        fit["rv5_why"] = f"{type(e).__name__}: {e}"
                try:
                    out[idx]["day"] = _surface_day(idx)
                except Exception:        # the day story is additive, never fatal
                    out[idx]["day"] = None
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
                traces = {i: list(r) for i, r in
                          (_SENSES["drag_day"] or {}).items()}
            out = {i: b.read() for i, b in boards.items()
                   if not only or i == only}
            # The day trace rides along, downsampled to ~60 points. `hi` is
            # the worst tax the day showed with its clock; None when no
            # readable frac ever appeared (an index that never moved).
            for i in out:
                rows = traces.get(i) or []
                fr = [r for r in rows if r["frac"] is not None]
                step = max(1, len(rows) // 60)
                out[i]["day"] = {
                    "n": len(rows),
                    "hi": (max(fr, key=lambda r: r["frac"]) if fr else None),
                    "series": rows[::step],
                    # Part of this trace may have been read back from
                    # data/day_state/ rather than gathered by this process --
                    # which is why 19:30 shows the day at all. It is NOT
                    # backfilled: every row was observed, just by an earlier
                    # process on the same day. A reader needs this only so
                    # "since start" means the SESSION's start, not this
                    # process's.
                    "restored": bool(_SENSES.get("day_restored")),
                } if rows else None
                # An empty trace with no reason reads as "the tax was zero".
                # WIRED 2026-09-15: the ANCHOR now comes from the backfilled
                # grid on a late start (drag.Board._anchor_from_grid, see
                # `anchor_src` above). The TRACE before this start still
                # cannot be rebuilt: the grid has no delta and drag.between
                # refuses an assumed one.
                out[i]["day_why"] = None if rows else (
                    "no samples: the trace fills at chain pace (~10s per "
                    "index). On a late start the anchor is rebuilt from the "
                    "backfilled grid (anchor_src says which), but the trace "
                    "between 09:15 and this start is not -- the grid carries "
                    "no delta and no rate is invented without one. If an "
                    "earlier process today wrote a trace, it is restored from "
                    "data/day_state/ instead.")
            self._json(json.dumps({
                "ok": bool(out),
                "indices": out,
                "coverage": _coverage(),
                "note": ("owed = delta x the underlying's move; paid = what "
                         "the premium actually did; drag = owed - paid, and "
                         "frac is that as a RATE. Deltas are real, off the "
                         "chain -- there is no assumed 0.5 here, and that "
                         "assumption is why this module exists."),
            }).encode())
        elif self.path.startswith("/api/warmap"):
            # THE OI WAR MAP, per index: levels + dwell + runways + sequence,
            # assembled at chain pace by warmap.py and served from its last
            # reading. SHADOW: nothing here gates a setup, and no field is
            # ever a hit rate.
            q = parse_qs(urlsplit(self.path).query)
            only = (q.get("idx") or [None])[0]
            with _SENSES_LOCK:
                boards = _SENSES.get("warmap")
                out = boards.states() if boards is not None else {}
            if only:
                out = {k: v for k, v in out.items() if k == only}
            self._json(json.dumps({
                "ok": bool(out),
                "why": None if out else ("no war map yet -- the senses loop "
                                         "builds one per index at chain pace"),
                "indices": out,
                "note": ("stop zones and retail attribution are [I] forever; "
                         "the forward log is data/warmap/ and is never "
                         "pooled with any other record"),
            }).encode())
        elif self.path.startswith("/api/vpin"):
            # THE DAY'S TOXICITY SERIES, straight from the forward log -- the
            # log IS the record, this is today's slice of it plus the live
            # state. Reads the file per request (~70 rows a session; the
            # size-keyed caching _surface_day needs would buy nothing here).
            # series null = log unreadable, [] = no completed buckets yet --
            # two different sentences, never collapsed.
            today = time.strftime("%Y-%m-%d")
            idx = self._idx()
            if idx != "NIFTY":
                # P1-02: the gauge is on the NIFTY future only (vpin.py's bucket was measured there);
                # SENSEX's future prints a median 7-10 lots a 5-min bar [M]. The count is the reason.
                bars = _ux_bars(idx, today)
                lots = bars[-1].get("vol") if bars else None
                self._json(json.dumps({"ok": True, "day": today, "idx": idx, "inst": f"{idx}-FUT", "series": None,
                                       "state": {}, "fast_series": None, "tag": "[I]", "shadow": True,
                                       "why": board.CC + (f"{idx} future, {lots:g} lots this bucket"
                                                          if isinstance(lots, (int, float)) and not isinstance(lots, bool)
                                                          else f"{idx} future: no closed ladder bar yet")}).encode())
                return
            # `series` stays None when the LIVE log is unreadable: "we could
            # not check" and "there are no buckets yet" are two sentences and
            # an empty list would say the wrong one.
            live = None
            try:
                with open(VPIN_LOG, encoding="utf-8"):
                    pass
            except OSError:
                pass
            else:
                live = [r for r in _read_jsonl(VPIN_LOG)
                        if r.get("day") == today and r.get("inst") == "NIFTY-FUT"]
            bf = [r for r in _read_jsonl(VPIN_BACKFILL_LOG)
                  if r.get("day") == today and r.get("inst") == "NIFTY-FUT"]
            series = None if live is None else _vpin_series(live, bf)
            # THE FAST LINE, read the same way and kept apart the same way:
            # null = its log could not be read, [] = read and no bucket yet.
            fast = _vpin_fast_rows(VPIN_FAST_LOG, today, VPIN_FAST_INST)
            with _SENSES_LOCK:
                st = {i: g.state()
                      for i, g in sorted(_SENSES["vpin"].items())}
            self._json(json.dumps(
                {"ok": True, "day": today, "inst": "NIFTY-FUT",
                 "series": series, "state": st, "tag": "[I]",
                 "shadow": True,
                 # The fast line rides beside the slow one, never inside it.
                 # Two bucket sizes are two populations: their percentiles are
                 # comparable as SHAPES and not as numbers, and nothing here
                 # ranks, averages or counts across the pair.
                 "fast_inst": VPIN_FAST_INST,
                 "fast_bucket_v": vpin_mod.FAST_BUCKET_V,
                 "fast_series": fast,
                 "fast_why": (None if fast else
                              ("the fast line's log could not be read"
                               if fast is None else
                               "no completed fast bucket yet today")),
                 # The live gauge's percentile is ranked against ONE
                 # population. This says which, so a reading is never read
                 # against a distribution it was not measured in.
                 "seeded_from_backfill": SEED_LIVE_GAUGE_FROM_BACKFILL,
                 "backfill": {"n": _VPIN_BF["n"], "why": _VPIN_BF["why"],
                              "method": "BVC on 1-minute FUT bars",
                              "note": ("coarser than the live frame path and "
                                       "generally lower; a separate file, "
                                       "never written into data/vpin_log."
                                       "jsonl, which is the promotion record")},
                 "coverage": _coverage()}).encode())
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
                    "read": read,
                    "pools": _SENSES["pools"],
                    # SHADOW, [I]: percentile-so-far of flow toxicity on the
                    # NIFTY future. A panel renders it; nothing acts on it.
                    "vpin": {i: g.state()
                             for i, g in sorted(_SENSES["vpin"].items())},
                    "rows": rows[-n:],
                }).encode())
        elif self.path.startswith("/api/reader"):
            # THE SHADOW LEG ENGINE (reader_live.py; docs/reader/8-shadow-build.md): GET /api/reader?idx= -- the reader
            # thread's cached reply, O(1). Read-only; shadow and unsigned; nothing decides on it.
            idx = (parse_qs(urlsplit(self.path).query).get("idx") or ["NIFTY"])[0]
            self._json(json.dumps(reader_live.read(idx), default=str).encode())
        elif self.path.startswith("/api/xindex"):
            # THE SHADOW CROSS-INDEX READ (xindex_live.py; docs/reader/10-xindex-build.md): the latest 3-min read and the
            # day's LOOK HERE changes. Read-only; shadow and unsigned; the glance bar's LOOK HERE chip is untouched.
            self._json(json.dumps(xindex_live.read(), default=str).encode())
        elif self.path.startswith("/api/feed"):
            # FEED HEALTH (P3): GET /api/feed/gc?idx= -- is the GoCharting tape alive, from the data. The DESK, the float and
            # the Trade tab also get it as `feed` on /api/fold* and /api/tape, which they poll already.
            q = parse_qs(urlsplit(self.path).query)
            idx = (q.get("idx") or ["NIFTY"])[0]
            self._json(json.dumps({"ok": True, **_feed_read(idx, time.strftime("%Y-%m-%d"))}, default=str).encode())
        elif self.path.startswith("/api/receipts"):
            # RECEIPTS (receipts.py; validate-tab-spec §7): her closed trades' receipts and the scoreboard. Read-only.
            try:
                out = _receipts_get()
            except Exception as e:           # never 500 the RECORD
                log.exception("receipts")
                out = {"ok": False, "why": board.CC + f"{type(e).__name__}: {e}"}
            self._json(json.dumps(out, default=str).encode())
        elif self.path.startswith("/api/fold"):
            # THE REV 6 ENGINE'S READS (fold_live.py; docs/pro-tool/API-v3.md): /api/fold?id=, /api/fold/flat?idx=,
            # /api/fold/ifin?idx=&k=&ty=&side=, /api/fold/record?day=. Every reply is the engine loop's cache --
            # no request reads a day file -- and a failure inside the engine is a why, never a 500.
            u = urlsplit(self.path)
            with HOLD_TRADES_LOCK:
                trades = list(_hold_trades())
            out = fold_live.reply(u.path, parse_qs(u.query), trades)
            if isinstance(out, dict) and u.path != "/api/fold/record":      # the feed band rides the reads the faces poll
                out["feed"] = _feed_read((parse_qs(u.query).get("idx") or ["NIFTY"])[0], time.strftime("%Y-%m-%d"))
            if isinstance(out, dict) and u.path == "/api/fold" and out.get("ok"):
                out = _in_trade(out, trades)                          # HOLD v2 + the one voice, on a copy (A52)
            self._json(json.dumps(out, default=str).encode())
        elif self.path.startswith("/api/hold"):
            # THE HOLD / FOLD WINDOW (hold.py; docs/hold/PREREG-merged.md rev 4):
            # /api/hold?id= a marked trade, or ?idx=&k=&side=&role=&t0=&p0=&qty=
            # [&asof=HH:MM][&rows=1]; /api/hold/trades today's marked trades.
            # GET only here.
            q = parse_qs(urlsplit(self.path).query)
            path = urlsplit(self.path).path
            try:
                if path == "/api/hold/trades":
                    with HOLD_TRADES_LOCK:
                        out = {"ok": True, "trades": list(_hold_trades()), "draft": hold.DRAFT}
                    out["lots"] = {i: _hold_lot(i) for i in instruments.ENABLED}     # before any answer (REVIEW P1-7)
                elif path == "/api/hold/check":
                    out = _hold_check(self.poller, q, self.payloads)
                elif path == "/api/hold/expr":
                    out = _expr_reply(self.poller, self.payloads, self._idx())
                elif path == "/api/hold/sigma":      # a leg's σ vs its VWAP (§F.1, printed): off the press's path
                    F = _hold_facts(self.poller, self._idx())
                    out = (_hold_sigma(self._idx(), float((q.get("k") or ["0"])[0]), (q.get("side") or ["CE"])[0].upper(),
                                       F["asof"]) if F else {"why": board.CC + "no finished minute yet", "tag": "M"})
                else:
                    out = _hold_reply(self.poller, q)
                    tid = (q.get("id") or [None])[0]
                    if tid and isinstance(out, dict):            # the hold window's one voice (A52), the same block
                        with HOLD_TRADES_LOCK:
                            trs = list(_hold_trades())
                        rep = fold_live.reply("/api/fold", {"id": [tid]}, trs)
                        fv = _in_trade(rep, trs) if isinstance(rep, dict) and rep.get("ok") else {}
                        out["voice"] = fv.get("voice") or {"ok": False, "why": (rep or {}).get("why") or "could not check — no engine read"}
                        if fv.get("receipt"):
                            out["receipt"] = fv["receipt"]
                        if fv.get("flow_src"):           # SENSEX-NIFTY-FLOW §3 (signed 25 Oct): the hold reply names its flow
                            out["flow_src"] = fv["flow_src"]
            except Exception as e:           # a bad read must not 500 the window
                log.exception("hold %s", self.path)
                out = {"ok": False, "why": board.CC + f"{type(e).__name__}: {e}"}
            self._json(json.dumps(out, default=str).encode())
        elif urlsplit(self.path).path == "/api/voice_path":
            # A56: the one voice + its map replayed over a marked trade of a past day (or today's after 15:40), once
            q = parse_qs(urlsplit(self.path).query)
            day, tid = (q.get("day") or [time.strftime("%Y-%m-%d")])[0], (q.get("id") or [""])[0]
            try:
                out = (_voice_path(day, tid) if re.match(r"^\d{4}-\d{2}-\d{2}$", day) and tid
                       else {"ok": False, "why": "could not check — voice_path needs id and day YYYY-MM-DD"})
            except Exception as e:               # never 500
                log.exception("voice path %s", self.path)
                out = {"ok": False, "why": board.CC + f"{type(e).__name__}: {e}"}
            self._json(json.dumps(out, ensure_ascii=False, default=str).encode())
        elif urlsplit(self.path).path == "/api/read":
            # THE READ (read.py): one held read per index -- word, FLIP, targets, wrong-if, the trade. ?idx= one
            # index, ?day= a past day through the same door. Display only; a failure is a why, never a 500.
            q = parse_qs(urlsplit(self.path).query)
            day = (q.get("day") or [time.strftime("%Y-%m-%d")])[0]
            want = (q.get("idx") or [None])[0]
            want = want.upper() if want and want.upper() in instruments.ENABLED else None
            at = (q.get("at") or [None])[0]               # a past day as of HH:MM (decode-loop replays)
            try:
                out = (_read_reply(day, want, at if at and re.match(r"^\d{2}:\d{2}$", at) else None)
                       if re.match(r"^\d{4}-\d{2}-\d{2}$", day) else {"ok": False, "why": "day must be YYYY-MM-DD"})
            except Exception as e:               # never 500
                log.exception("read %s", self.path)
                out = {"ok": False, "why": board.CC + f"{type(e).__name__}: {e}"}
            self._json(json.dumps(out, ensure_ascii=False, default=str).encode())
        elif urlsplit(self.path).path == "/api/decode":
            # VALIDATE rev 3's DECODE inputs (docs/hold/VALIDATE-PREREG-rev3.md §1): the DECODE block per index -- live,
            # the loop's cache (never computed on the request); a past ?day=&at=HH:MM, once per close (_decode_for).
            q = parse_qs(urlsplit(self.path).query)
            day = (q.get("day") or [time.strftime("%Y-%m-%d")])[0]
            at = (q.get("at") or [None])[0]
            try:
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", day) or (at and not re.match(r"^\d{2}:\d{2}$", at)):
                    out = {"ok": False, "why": "day must be YYYY-MM-DD, at HH:MM"}
                else:
                    live = day == time.strftime("%Y-%m-%d")
                    lt = time.localtime()
                    now = (int(at[:2]) * 3600 + int(at[3:5]) * 60 if at
                           else lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec if live else None)
                    if live and at:                  # today, a scrubbed close: what the app said then (the write-once log)
                        dec = {r["idx"]: r for r in confluence_log._rows(os.path.join(DECODE_DIR, f"decode_{day}.jsonl"))
                               if r.get("T") == at and r.get("idx")}
                    else:
                        dec = _decode_for(day, now, live) or {}
                    out = {"ok": True, "day": day, "live": live, "why": dec.get("why"),
                           "indices": {i: _decode_aged(dec.get(i), now) for i in instruments.ENABLED if isinstance(dec.get(i), dict)}}
            except Exception as e:               # never 500
                log.exception("decode door")
                out = {"ok": False, "why": board.CC + f"{type(e).__name__}: {e}"}
            self._json(json.dumps(out, ensure_ascii=False, default=str).encode())
        elif self.path.startswith("/api/calls"):
            # EVERY ENGINE CALL, GROUNDED (grounds.py). The engine's verdict,
            # episode, breadth and plays on its latest 3-min bar, each held
            # against the near-ATM fronts (OI), the Upstox ladder's CVD and its
            # order flow -- three families the engine never sees. A face shows a
            # call WITH its status and facts, never bare. GET only, per request.
            idx = self._idx()
            try:
                out = _calls_for(self.payloads, self.poller, idx)
            except Exception as e:           # a bad read must not 500 the face
                out = {"ok": False, "idx": idx, "why": f"{type(e).__name__}: {e}", "calls": []}
            try:                             # AAJ KA DIN rides here, so the band needs no new poll
                out["daytype"] = _daytype_reply(self.poller, idx)
            except Exception as e:
                log.exception("daytype %s", idx)
                out["daytype"] = {"ok": False, "idx": idx, "why": board.CC + f"{type(e).__name__}: {e}"}
            self._json(json.dumps(out, default=str).encode())
        elif self.path.startswith("/api/tape"):
            # the ladder record and what prints.py reads off it (spec §D) --
            # live from the extension's last post, else from data/tape/, else
            # the third sentence. Streamed readers only; never a whole-file
            # json.load on this thread (record_read.py:1-15).
            q = parse_qs(urlsplit(self.path).query)
            day = (q.get("day") or [time.strftime("%Y-%m-%d")])[0]
            out = _tape_reply(self._idx(), day)
            out["feed"] = _feed_read(self._idx(), day)     # the Trade tab's band, on the poll it already makes
            self._json(json.dumps(out, default=str).encode())
        elif self.path.startswith("/api/frame"):
            q = parse_qs(urlsplit(self.path).query)
            idx = (q.get("idx") or ["NIFTY"])[0]
            with _SENSES_LOCK:
                fr = _SENSES["frame"].get(idx)
            self._json(json.dumps(fr or {"ok": False, "why": "no frame yet: the extension has not posted"},
                                  default=str).encode())
        elif self.path.startswith("/api/story"):
            # THE STORY for the panel, the Float and the DESK (story.compose_all over the events the extension posted, the
            # fold / trap / sides-3 / VPIN reads): sentence, chapters, trade_read, lean, highlights, now_ms -- the last
            # frame's, never recomputed here. ?day= a past day: its chapters off the saved logs (_story_past).
            q = parse_qs(urlsplit(self.path).query)
            idx = (q.get("idx") or ["NIFTY"])[0]
            want = (q.get("day") or [None])[0]
            with _SENSES_LOCK:
                fr = _SENSES["frame"].get(idx)
            st = (fr or {}).get("story") if isinstance(fr, dict) else None
            if want and not re.match(r"^\d{4}-\d{2}-\d{2}$", want):
                body = {"ok": False, "idx": idx, "why": "day must be YYYY-MM-DD"}
            elif want and want != (fr or {}).get("day"):      # a past day (RECORD): its chapters off the saved logs
                try:
                    body = _story_past(idx, want)
                except Exception as e:
                    body = {"ok": False, "idx": idx, "day": want, "why": f"could not check — {e}"}
            else:
                body = ({"ok": st.get("sentence") is not None, "idx": idx, "day": fr.get("day"), "ts": fr.get("ts"), **st} if st
                        else {"ok": False, "idx": idx, "sentence": None, "sentence_why": "no frame yet: the extension has not posted"})
            self._json(json.dumps(body, default=str).encode())
        elif self.path.startswith("/api/v2/data"):
            # THE VALIDATE FACE'S FEED (v2feed.py; ui-v2/public/validate2): the day files tailed by byte offset, one
            # payload cached per (day, file sizes) -- full on the first call, a delta with since=<sec of day> after.
            # Read-only; a past day (?day=) replays through the same door; a failure inside is a why, never a 500.
            import v2feed
            q = parse_qs(urlsplit(self.path).query)
            day = (q.get("day") or [time.strftime("%Y-%m-%d")])[0]
            try:
                out = (v2feed.serve(day, (q.get("since") or [None])[0]) if re.match(r"^\d{4}-\d{2}-\d{2}$", day)
                       else {"ok": False, "why": "day must be YYYY-MM-DD"})
            except Exception as e:               # never 500
                log.exception("v2feed %s", self.path)
                out = {"ok": False, "why": board.CC + f"{type(e).__name__}: {e}"}
            self._json(out if isinstance(out, bytes) else json.dumps(out, default=str).encode())
        elif self.path.startswith("/api/validate"):
            # THE LIVE IN-TRADE READ (validate_live.py): the last frame's, never recomputed here. No frame yet: the
            # cooldown / flip timers still answer, and the trade says why it has no lamps.
            q = parse_qs(urlsplit(self.path).query)
            idx = (q.get("idx") or ["NIFTY"])[0]
            with _SENSES_LOCK:
                fr = _SENSES["frame"].get(idx)
            body = (fr or {}).get("validate") if isinstance(fr, dict) else None
            if body is None:
                with HOLD_TRADES_LOCK:
                    trades = [dict(t) for t in _hold_trades()]
                tr = next((t for t in trades if t.get("idx") == idx and not t.get("exit_t")), None)
                body = validate_live.read(tr, {"ok": False, "why": "no frame yet: the extension has not posted"}, _board_clock()[0],
                                          int(time.time() * 1000), trades=trades, idx=idx)
            self._json(json.dumps(body, default=str).encode())
        elif self.path.startswith("/api/dext/parity"):
            # GATE 3's three-way check (dext_parity.py), computed on request: counts and ratios only, never a verdict
            day = (parse_qs(urlsplit(self.path).query).get("day") or [time.strftime("%Y-%m-%d")])[0]
            try:
                out = dext_parity.report(day) if re.match(r"^\d{4}-\d{2}-\d{2}$", day) else {"ok": False, "why": "day must be YYYY-MM-DD"}
            except Exception as e:               # never 500
                log.exception("dext parity")
                out = {"ok": False, "day": day, "why": f"could not check — {type(e).__name__}: {e}"}
            self._json(json.dumps(out, default=str).encode())
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

    NONE IS A RESULT, NOT A FAILURE. A cold server, a market that is shut, or
    a chain that has not warmed gives None, and the desk log's gear and
    conviction read None rather than an error.

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


def _isolate_mock_writers():
    """Point every forward-log writer under data/mock/ for a --mock-chain run.

    THE REPLAY LEAK (2026-08-24): a --mock-chain server left running after a
    build night looped the fixture for 33 hours and wrote fixture trades,
    fixture levels and fixture fits into the LIVE forward record --
    data/paper_desk/, data/warmap/, data/surface/, data/desk_log.jsonl --
    costing the paper desk and the war map their clean day 1. A replay must
    never share a path with the record it exists to rehearse for. The
    writers read these constants at call time.
    """
    import os
    import sequence as sequence_mod
    mock = os.path.join("data", "mock")
    sequence_mod.DIR = os.path.join(mock, "warmap")
    desk_log.SURF_DIR = os.path.join(mock, "surface")
    desk_log.DESK_LOG_PATH = os.path.join(mock, "desk_log.jsonl")
    day_state.DIR = os.path.join(mock, "day_state")
    hold_log.DIR = os.path.join(mock, "hold")
    global VPIN_LOG, VPIN_BACKFILL_LOG, VPIN_FAST_LOG, RANK_DIR
    RANK_DIR = os.path.join(mock, "rank")                           # the extension v2's rank_ref files (_rank_ref)
    VPIN_LOG = os.path.join(mock, "vpin_log.jsonl")
    VPIN_BACKFILL_LOG = os.path.join(mock, "vpin_backfill.jsonl")
    VPIN_FAST_LOG = os.path.join(mock, "vpin_fast.jsonl")
    tape_log.DIR = os.path.join(mock, "tape")
    book_log.DIR = os.path.join(mock, "book")
    reader_live.DIR = os.path.join(mock, "reader")                  # the shadow leg engine's log (docs/reader/8-shadow-build.md)
    xindex_live.DIR = os.path.join(mock, "xindex")                  # the shadow cross-index log (docs/reader/10-xindex-build.md)
    sides_log.DIR = os.path.join(mock, "sides")                     # the sides read's forward log (sides_log.py)
    trap_log.DIR = os.path.join(mock, "trap")                       # the trap layer's forward log (trap_log.py)
    decoder_log.DIR = os.path.join(mock, "decoder")                 # the decoder's forward log (decoder_log.py)
    dext_log.DIR = os.path.join(mock, "dext")                       # the Dext record (dext_log.py)
    # 2026-09-28 (the correctness pass): the writers this list had missed. Each reads
    # its constant at call time; trigger_log.log_new is handed PATH at its call site.
    import chain_live
    import live
    frame_log.DIR = os.path.join(mock, "frame")
    calls_log.DIR = os.path.join(mock, "calls")
    senses_mod.DIR = os.path.join(mock, "senses")
    trigger_log.PATH = os.path.join(mock, "trigger_log.jsonl")
    confluence_log.PATH = os.path.join(mock, "confluence_log.jsonl")
    import onesided
    onesided.PATH = os.path.join(mock, "onesided_log.jsonl")         # §1o's daily row (onesided.py)
    global DECODE_DIR, MAP_DIR, VOICE_DIR, SHADOW_DIR
    DECODE_DIR = os.path.join(mock, "decode")                       # N7: the DECODE block's forward log (_decode_log)
    MAP_DIR = SHADOW_DIR = os.path.join(mock, "hold")               # the TRADE MAP's and holdshadow's forward logs
    VOICE_DIR = os.path.join(mock, "voice")                         # the voice replayed per marked trade (_voice_path)
    global VALIDATE_DIR, IMPORT_DIR
    VALIDATE_DIR = os.path.join(mock, "validate")                   # F12: Validate's press log (_validate_press)
    IMPORT_DIR = os.path.join(mock, "receipts")                     # F13a: the tradebook import marks (_receipts_import)
    chain_live.CHAIN_DIR = ROOT / mock / "chain"
    live.STICK_F = ROOT / mock / "stick_state.json"
    feed_health.LOG = os.path.join(mock, "feed_log.jsonl")           # the GoCharting feed's transitions (A17)
    # 2026-09-28 (pro-tool P1-01): the rev 6 event log (P2-02), guarded until it lands.
    # conftest.py keeps the same list for pytest; test_leak_guard.py checks both.
    import chain_backfill
    chain_backfill.DIR = os.path.join(mock, "chain_backfill")      # the 09:15 REST backfill on disk (P2-06)
    try:
        import fold_log
        fold_log.DIR = os.path.join(mock, "fold")
    except ImportError:
        pass


def _session_bars(index="NIFTY"):
    """Today's 1-minute FUTURE bars as `(stamp, close, volume)`, oldest first.

    ONE REST call. Deliberately not routed through `live._upstox_bars`: that
    path carries the Dhan branch and the whole `live` import graph for a
    three-field read, and it returns Dhan's chart-array shape which this would
    only have to unpack again.
    """
    import upstox_adapter as ua
    import upstox_feed
    import upstox_instruments
    import upstox_rest
    arr = ua.candles_to_arrays(
        upstox_rest.intraday(upstox_instruments.fut_key(index),
                             upstox_feed.read_token()))
    ts = arr.get("timestamp") or []
    close = arr.get("close") or []
    vol = arr.get("volume") or []
    return [(time.strftime("%H:%M", time.localtime(t)), c, v)
            for t, c, v in zip(ts, close, vol)]


def _backfill_vpin():
    """Rebuild the toxicity buckets for the part of today the socket missed.

    THE GAP THIS CLOSES, in the operator's words: *"i open my laptop at 11 to
    pta chle morning ki koi info nhi h phir to reliable he nhi hoga"*. The
    frames are gone but the BARS are not, so the morning's volume is
    recoverable -- coarsely, and `vpin.from_bars` documents exactly how
    coarsely.

    ONLY WHEN THE GAP IS REAL. If the live log already starts at the open there
    is nothing to rebuild and this does nothing but say so. The reconstruction
    is cut off at the first LIVE bucket's clock, because an observation always
    beats a reconstruction -- the same rule `chain_backfill` states -- and
    because volume-time buckets from the two paths do not align and must never
    be stitched into one running series.

    The file is REWRITTEN, not appended. It is derived, regenerable from the
    same bars any time, and appending would duplicate the morning on every
    restart. Nothing about a forward record applies to it: that is `VPIN_LOG`,
    which this function never opens for writing.
    """
    _VPIN_BF["n"], _VPIN_BF["rows"] = 0, []
    today = time.strftime("%Y-%m-%d")
    if os.environ.get("TAPEMAP_BROKER", "dhan").strip().lower() != "upstox":
        _VPIN_BF["why"] = ("not attempted: bars come from Upstox and this "
                           "server is not on the Upstox path")
        return
    if time.localtime().tm_wday >= 5:
        _VPIN_BF["why"] = "not attempted: not a weekday session"
        return
    first_live = None
    for r in _read_jsonl(VPIN_LOG):
        if r.get("day") == today and r.get("inst") == "NIFTY-FUT" and r.get("at"):
            first_live = min(first_live or r["at"], r["at"])
    if first_live is not None and first_live[:5] <= "09:20":
        _VPIN_BF["why"] = (f"no gap to fill: the live record already starts at "
                           f"{first_live}, which is the open")
        return
    try:
        bars = _session_bars("NIFTY")
    except Exception as e:                            # noqa: BLE001
        _VPIN_BF["why"] = (f"could not check: the 1-minute bars did not load "
                           f"({type(e).__name__}: {e})")
        log.exception("vpin backfill: bars")
        return
    if first_live is not None:
        bars = [b for b in bars if b[0] < first_live[:5]]
    if not bars:
        _VPIN_BF["why"] = ("checked and found nothing: no bars before the "
                           "first live bucket -- there was no unwatched "
                           "morning to rebuild")
        return
    rows = [dict(r, inst="NIFTY-FUT", day=today)
            for r in vpin_mod.from_bars(bars)]
    try:
        os.makedirs(os.path.dirname(VPIN_BACKFILL_LOG) or ".", exist_ok=True)
        with open(VPIN_BACKFILL_LOG, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
    except OSError as e:                              # noqa: BLE001
        log.exception("vpin backfill write")
        _VPIN_BF["why"] = f"rebuilt but could not be written ({e})"
    _VPIN_BF["n"], _VPIN_BF["rows"] = len(rows), rows
    _VPIN_BF["why"] = (
        f"{len(rows)} bucket(s) rebuilt from {len(bars)} 1-minute bars "
        f"[I-backfill, BVC], covering "
        + (f"the open to {first_live}" if first_live else "the session so far")
        + "; coarser than the live path and never pooled with it")
    log.info("vpin backfill: %s", _VPIN_BF["why"])


def _vpin_fast_rows(path, day, inst):
    """The fast line's buckets for `day`, in the shape `_vpin_series` returns.

    THREE ABSENCES, THREE ANSWERS, and the middle one is the whole reason this
    is a function. `None` means the log could not be READ -- a real failure.
    `[]` means read and empty, OR never written at all: on the fast line's
    first day `vpin_fast.jsonl` does not exist yet because no bucket has
    completed, and "nothing yet" must not reach the face as "could not check".
    The slow path never met this only because its log has existed for weeks.
    """
    try:
        with open(path, encoding="utf-8"):
            pass
    except FileNotFoundError:
        return []
    except OSError:
        return None
    return [{"t": r.get("at"), "imb": r.get("imb"), "vpin": r.get("vpin"),
             "pct": r.get("pct"), "backfill": False, "src": "live_frames"}
            for r in _read_jsonl(path)
            if r.get("day") == day and r.get("inst") == inst]


def _vpin_series(live, backfill):
    """One day's toxicity series, every row saying which population it is from.

    THE REBUILT MORNING GOES IN FRONT, and is CUT OFF at the first live bucket.
    An observation always beats a reconstruction -- `chain_backfill` states the
    same rule for the OI grid -- and here there is a second reason the two must
    not overlap: these are VOLUME-time buckets, and buckets counted off
    1-minute bars do not align with buckets counted off 0.5s frames. Stitching
    them would produce a series whose boundaries mean two different things.

    Nothing is summed, averaged or ranked ACROSS the join. The join is a
    concatenation and the tag on each row is what makes it readable as one.
    """
    def row(r, is_bf):
        return {"t": r.get("at"), "imb": r.get("imb"), "vpin": r.get("vpin"),
                "pct": r.get("pct"), "backfill": is_bf,
                "src": r.get("src") if is_bf else "live_frames"}

    first_live = min((r.get("at") for r in live if r.get("at")), default=None)
    kept = [r for r in backfill
            if first_live is None or (r.get("at") or "") < first_live]
    return [row(r, True) for r in kept] + [row(r, False) for r in live]


def _read_jsonl(path):
    """Every parseable object in `path`; `[]` when the file will not open.

    A line that will not parse is skipped rather than ending the read: these
    files are appended to by a running process, so the last line can be a
    partial write, and one torn line must not cost the whole day.
    """
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return out


def _load_day_state():
    """Put back the day's RAM-only series, so 19:30 can see 09:15.

    The operator, verbatim: *"7:30pm ko bhi kholu to dekh paaoun kya hua"*.
    Everything else this stack learns is already on disk in a forward log; the
    drag day trace was the one series that died with the process.

    TODAY'S FILE ONLY -- `day_state.load` enforces that, so tomorrow starts
    cold rather than opening on yesterday's tax. Runs before any thread starts,
    so no lock is needed, and BEFORE the senses loop can save over it.
    """
    from collections import deque
    doc = day_state.load(time.strftime("%Y-%m-%d"))
    n = 0
    for idx, rows in (doc.get("drag_day") or {}).items():
        if not isinstance(rows, list):
            continue
        _SENSES["drag_day"][idx] = deque(rows, maxlen=3000)
        n += len(rows)
    # Not a `backfill` tag: every one of these rows was OBSERVED, by an earlier
    # process on the same day. This says only that the running process did not
    # gather them itself, so "since start" is read correctly.
    _SENSES["day_restored"] = n
    if n:
        log.info("day state: restored %s drag sample(s) across %s index(es)",
                 n, len(doc.get("drag_day") or {}))
    # BOARD rev 3's FIRST FOLD, stamped once per day: a restart re-reads it
    # rather than re-deciding it (the anytime-start rule).
    _BOARD["first"] = {i: dict(f, src="restored from data/day_state/") for i, f in
                       (doc.get("board_first") or {}).items() if isinstance(f, dict)}
    _BOARD["first_day"] = time.strftime("%Y-%m-%d")
    # THE HOLD WINDOW's marked trades: a restart re-reads each one (its entry
    # minute, line, latch and clock are re-derived from the day record) and its
    # log continues the same rows (hold_log.py appends only what is missing).
    _HOLD["trades"] = [t for t in doc.get("hold_trades") or [] if isinstance(t, dict) and t.get("id")]
    _HOLD["trades_day"] = _board_clock()[0]
    # rev 5 §A.0.4: when each late close was first read, which closes were backfilled, and each marked
    # trade's B reads -- written once, read back, so a restart re-reads what was read live.
    _HOLD["land"] = {i: {"day": v["day"], "late": dict(v.get("late") or {}), "blind": list(v.get("blind") or []),
                         "live_to": v.get("live_to"), "boot": None}
                     for i, v in (doc.get("hold_land") or {}).items()
                     if isinstance(v, dict) and v.get("day") == _HOLD["trades_day"]}
    _HOLD["frozen_b"] = {k: v for k, v in (doc.get("hold_b") or {}).items() if isinstance(v, list)}


def _save_day_state():
    """Write the day's RAM-only series down. Fail-soft: a full disk costs the
    save, never the tape."""
    try:
        with _SENSES_LOCK:
            snap = {i: list(r) for i, r in (_SENSES["drag_day"] or {}).items()}
        day = time.strftime("%Y-%m-%d")
        first = dict(_BOARD["first"]) if _BOARD["first_day"] == day else {}
        with HOLD_TRADES_LOCK:
            trades = [dict(t) for t in _hold_trades()]
        land = {}
        for i, v in list((_HOLD.get("land") or {}).items()):     # copied under the index lock that writes it
            with _HOLD["locks"].setdefault(i, threading.Lock()):
                land[i] = {"day": v["day"], "late": dict(v["late"]), "blind": list(v["blind"]), "live_to": v["live_to"]}
        frozen = {k: list(v) for k, v in list((_HOLD.get("frozen_b") or {}).items())}
        if snap or first or trades or land or _HOLD.pop("dirty", False):   # dirty: an unmark must reach the disk too
            day_state.save(day, {"drag_day": snap, "board_first": first, "hold_trades": trades,
                                 "hold_land": land, "hold_b": frozen})
    except OSError:
        log.exception("day state save")


def _book_coverage():
    lost = book_log.failed + ux_log.failed
    if _SENSES.get("book") is None:
        return {"from": {}, "dropped": 0, "written": 0, "rebuild_why": {}, "failed": book_log.failed,
                "ux_failed": ux_log.failed, "drain_why": _SENSES.get("ux_drain_why"),
                "drain_failed": _SENSES.get("ux_drain_failed", 0),
                "why": "no book writer in this process"}
    b = _SENSES["book"]
    frm = dict(b.book_from)
    ux_state = _SENSES.get("ux") or {}
    rebuild_why = {idx: st["rebuild_why"] for idx, st in ux_state.items() if st.get("rebuild_why")}
    why = None if frm else "no frame recorded yet this process -- feed not connected, or before the first drain"
    if lost:
        note = f"{lost} row(s) lost to a write failure this process"
        why = f"{why} — {note}" if why else note
    return {"from": frm, "dropped": b.dropped, "written": b.written, "rebuild_why": rebuild_why,
            "failed": book_log.failed, "ux_failed": ux_log.failed,
            "drain_why": _SENSES.get("ux_drain_why"), "drain_failed": _SENSES.get("ux_drain_failed", 0),
            "why": why}


def _coverage():
    """What this process could and could not know about today.

    A late start is not a failure to hide, it is a fact to publish. Rule 6 of
    the house rules: "we checked and found nothing", "we could not check" and
    "we are not showing you" must never collapse into one rendering -- so a
    screen opened at 11:02 gets a sentence naming which panels have a
    reconstructed morning, which have none and never will, and why.

    The machine clock IS IST here (HANDOFF-DESK section 7: `TZ=Asia/Kolkata`
    silently returns UTC in this Git Bash, and local time is already IST), so
    `localtime` is the right read and an explicit offset would double-count.
    """
    up = time.localtime(_STARTED)
    started = time.strftime("%H:%M", up)
    late = (up.tm_hour * 60 + up.tm_min) - (9 * 60 + 15)
    gap = None if (up.tm_wday >= 5 or late <= 0) else min(late, 375)
    return {
        "server_up": started,
        "session_open": "09:15",
        "late_min": gap,
        # THE BOOK RECORD (spec 2026-09-20 §B): where the socket record starts
        # today, per index, and what the deque dropped. Rule 6: an empty map
        # gets its sentence.
        "book": _book_coverage(),
        "reconstructed": [
            "the tape's 1-minute FUT bars (live.build_session re-fetches the "
            "whole session from REST every cycle -- never lost)",
            # CORRECTED 2026-08-25: this used to claim the war map's time
            # dimension was reconstructed too. It is not, and the payload
            # said so four lines below -- `chain_backfill` fills
            # `ChainState.minutes`, which only /api/oiflow reads. warmap.py
            # builds its boards from chain snapshots at chain pace and never
            # touches that grid, so its history starts at process start.
            "the per-strike OI and premium minute grid behind /api/oiflow "
            "(chain_backfill, rows tagged backfill:true)",
            "the toxicity buckets, coarsely, from those same bars "
            "(/api/vpin, rows tagged backfill:true) [I]",
            "the buyer's-tax day trace, if an earlier process today wrote it "
            "down (data/day_state/, observed not reconstructed)",
            # WIRED 2026-09-15: warmap.py replays that same grid through fresh
            # dwell / sequence machines on the first chain snapshot
            # after the grid and the daily levels land. Its rows go to
            # warmap_<day>_backfill.jsonl, never the observed log.
            "the drag meter's anchor -- on a late start drag.Board anchors on "
            "the grid's earliest backfilled mark (09:15's strike and premiums), "
            "not on the first live snapshot; /api/drag.<idx>.anchor_src says "
            "which, and the rate then uses the live delta alone",
            "the war map's boards -- levels, dwell and the sequence machines "
            "-- replayed at 1-minute pace from the same "
            "minute grid (data/warmap/warmap_<day>_backfill.jsonl, rows tagged "
            "backfill:true; /api/warmap.<idx>.backfill says what landed)",
        ],
        "not_reconstructable": [
            "IV, greeks, GEX, the gamma flip and the fitted surface before "
            "this start -- REST candles carry no IV and no greeks",
            # CORRECTED 2026-08-25: this used to say no REST endpoint serves
            # the drag anchor. That was false -- `chain_backfill` already
            # fetches per-strike OI AND (since tonight) premium from 09:15,
            # which is exactly what anchoring needs. Nothing feeds drag.Board
            # from that grid, so this is a WIRING gap, not an impossibility,
            # and it must not be filed under "never will".
            "the drag meter's day TRACE before this start -- the grid carries "
            "no delta, and drag.between refuses an assumed one, so the samples "
            "between 09:15 and this start cannot be rebuilt (the ANCHOR can, "
            "and is: see `reconstructed`)",
            "the war map's dwell crossing evidence and hunt fuel before this "
            "start -- the minute grid carries no bid/ask and no ledger basis",
        ],
        "why": (None if gap is None else
                f"could not check — server started {started}, {gap} min after "
                f"the open. The fields under not_reconstructable have no "
                f"morning and never will; the ones under reconstructed do, "
                f"and say so row by row."),
    }


def _seed_vpin():
    """Rebuild the NIFTY-FUT toxicity gauge from its forward log, at startup.

    Runs BEFORE any thread starts (so no lock is needed) and AFTER
    `_isolate_mock_writers` (so a --mock-chain run seeds from its own
    isolated log, never the live record -- the 2026-08-24 replay-leak rule).
    TODAY's rows only -- prior sessions are deliberately ignored, see the
    operator's rejection recorded in vpin.Gauge.seed. A missing or empty
    log just starts the gauge cold, which is day one."""
    today = time.strftime("%Y-%m-%d")
    rows = _read_jsonl(VPIN_LOG)
    g = vpin_mod.Gauge()
    # The OPEN DECISION, exercised here and nowhere else. Backfilled buckets go
    # in FIRST when it is on -- they are the earlier part of the session, and
    # a percentile built out of chronological order is not a percentile-so-far.
    # See SEED_LIVE_GAUGE_FROM_BACKFILL for both sides of the argument.
    seeded_bf = 0
    if SEED_LIVE_GAUGE_FROM_BACKFILL and _VPIN_BF.get("rows"):
        seeded_bf = g.seed(_VPIN_BF["rows"], today=today)["today_buckets"]
    r = g.seed([x for x in rows if x.get("inst") == "NIFTY-FUT"], today=today)
    _SENSES["vpin"]["NIFTY-FUT"] = g
    log.info("vpin seeded: %s (of which %s backfilled, seeding %s)",
             r, seeded_bf, "ON" if SEED_LIVE_GAUGE_FROM_BACKFILL else "OFF")


def main():
    _setup_logging()
    argv = [a for a in sys.argv[1:] if a != "--mock-chain"]
    mock_chain = "--mock-chain" in sys.argv[1:]
    if mock_chain:
        _isolate_mock_writers()
    # ORDER MATTERS, all three before any thread starts. Isolation first (a
    # replay must not read OR write the live record), then the morning is
    # rebuilt so `_seed_vpin` can decide whether to rank against it, then the
    # day state is restored BEFORE the senses loop exists to save over it.
    _backfill_vpin()
    _seed_vpin()
    _load_day_state()
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
        globals()["_PAYLOADS"] = payloads        # THE DECODE block's FADE reads the same boxes (display only)
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
        from chain_live import IST, in_session
        from datetime import datetime
        _calls_min = {}             # idx -> the minute calls were last read

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
                              if isinstance(_sess, dict) else None),
                        path=trigger_log.PATH)   # read at call time, so a mock run is isolated
                    # §1i's forward log: one row per zone entry once its window has closed. Fail-soft, its own
                    # file only -- it changes no row, gate or beep above.
                    confluence_log.log_new(x, payload_at(payloads[x], DEFAULT_INTERVAL), path=confluence_log.PATH)
                    try:
                        confluence_log.log_ride(x, path=confluence_log.PATH)   # §1j RIDE forward log: fail-soft, its own rows only
                    except Exception:
                        pass
                    try:
                        confluence_log.log_faded(x, path=confluence_log.PATH)  # §1n FADE-D forward log: fail-soft, its own rows only
                    except Exception:
                        pass
                    # The grounded calls, kept (calls_log.py): in session only,
                    # read at most once a minute per index, a row only when the
                    # engine's bar is new. Its own try: the log must never cost
                    # the tape a build.
                    if _calls_min.get(x) != _t.strftime("%H:%M") and in_session(datetime.now(IST)):
                        _calls_min[x] = _t.strftime("%H:%M")
                        try:
                            calls_log.append(_t.strftime("%Y-%m-%d"), x,
                                             _calls_for(payloads, poller, x), _t.time())
                        except Exception:
                            log.exception("calls log failed %s", x)
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
        #
        # WEEK-OLD DAYS, COMPRESSED (daylog.py; operator 2026-09-23, "my
        # personal laptop with like 120 gb left"). Once per start, in the
        # background so a start is never slowed; today and the last week are
        # never touched. The folders are the recorders' own, so a redirect
        # (mock isolation) is followed rather than second-guessed.
        from chain_live import CHAIN_DIR
        threading.Thread(target=daylog.compress_old, args=(time.strftime("%Y-%m-%d"),),
                         kwargs={"dirs": (senses_mod.DIR, frame_log.DIR, book_log.DIR, str(CHAIN_DIR),
                                          calls_log.DIR, hold_log.DIR, sides_log.DIR, trap_log.DIR),
                                 "log": log.info},
                         daemon=True, name="daylog").start()
        if poller is not None:
            threading.Thread(target=_senses_loop, args=(poller, payloads),
                             daemon=True, name="senses").start()
            log.info("senses thread started -> %s", senses_mod.day_path())
            # THE HOLD WINDOW's forward logs (hold_log.py), on their own thread.
            threading.Thread(target=_hold_loop, args=(poller,), daemon=True, name="hold").start()
            # THE SIDES forward log (sides_log.py): its own thread, market hours only, once per closed slot.
            threading.Thread(target=_sides_loop, args=(poller, chains), daemon=True, name="sides").start()
            # THE TRAP LAYER (trap.py, SHADOW): its own thread, read every 15 s, logged in market hours only.
            threading.Thread(target=_trap_loop, args=(poller, chains), daemon=True, name="trap").start()
            # THE REV 6 ENGINE, live and incremental (fold_live.py, pro-tool P2-03): one thread, the day's
            # rows in memory, every read cached. Its seams are read at call time (mock isolation, day roll).
            threading.Thread(target=fold_live.run, kwargs=dict(
                day_fn=lambda: _board_clock()[0], trades_fn=lambda: list(_hold_trades()), lot_fn=_hold_lot,
                contract_fn=lambda i: (_SENSES.get("contract") or {}).get(i), chain_dir_fn=lambda: CHAIN_DIR,
                vpin_path_fn=lambda: VPIN_FAST_LOG, mock=mock_chain), daemon=True, name="fold").start()
            # THE SHADOW LEG ENGINE (reader_live.py): its own thread, tails the book and tape files, never raises.
            xindex_live._CFG.update(zone=lambda i: _xindex_zone(payloads, i),            # the zone machine's own states
                                    chain_dir=lambda: str(__import__("chain_live").CHAIN_DIR))
            threading.Thread(target=reader_live.run, kwargs=dict(day_fn=lambda: _board_clock()[0]),
                             daemon=True, name="reader").start()
        httpd.serve_forever()          # bound above, before anything was taken
        return
    log.error("usage: python server.py live [port] [--mock-chain]")
    sys.exit(2)


if __name__ == "__main__":
    main()
