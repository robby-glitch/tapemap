"""Live trigger logger for the operator's band-rotation setup.

WHY (2026-08-04). The d3 setup is validated on 18 backtest trades; the two
conditions the operator actually watches at the screen — the gamma regime and
the morning OI build on BOTH sides — cannot be backtested from the cache
(no per-trigger chain history). This module records them AT the moment each
live trigger fires, so in ~20-25 live signals checklist items #17 and #18
stop being hypotheses. Every row is written the instant the tape shows the
record; outcomes are filled in later by `score`, never at log time — a row
can therefore never peek forward.

WIRING. server.py's per-index refresh thread calls `log_new` right after a
successful build_payload. Everything here is fail-soft by construction: a
logger exception must never stall the tape (the 2026-07-27 frozen-tape
post-mortem is why), so `log_new` catches everything and returns 0.

THE LOG. data/trigger_log.jsonl, one JSON object per line:
    at          epoch seconds when logged
    day         ISO date (live tape == today)
    index, t, side, band, px      the record + its bar's close
    trigger     the detector's own receipt sentence
    gamma, ctx  the SAME bar's engine reads (absent -> null, never invented)
    oi_call, oi_put, oi_strength  the chain's cumulative day OI change at the
                latest oi_flow mark (chain_metrics semantics: change, not
                outstanding), and diff/max(call,put) signed
    f15, f30    filled by `score` only: forward move in points, signed by
                side, by CLOCK label (+15/+30 minutes), so 1-min live bars
                and 3-min cached bars score identically
    level       the band price the setup armed on, as the detector emitted it.
                Rows written before 2026-08-12 carry none; `_level_of` recovers
                it from the receipt sentence for those, and says which it used.

OUTCOME FIELDS (2026-08-12). Also filled by `score` only, never at log time,
and under names of their own -- `f15`/`f30` keep exactly the meaning they had.
See "SCORING THE OUTCOME" below for what each one measures and why.

    anchor, anchor_px, anchor_t     WHICH PRICE every number below is measured
                from, named rather than implied
    mfe, mfe_t / mae, mae_t         furthest favourable / adverse move in
                points, signed by side like f15, and the clock it was reached
    stop_px, stop_hit, stop_t       the operator's own 20-point stop. Recording
                it does NOT end the measurement
    bands       how far the OPPOSITE side of the band was reached, read LIVE
    triggered, trigger_t            ARM ROWS ONLY: did the setup go on to fire
    unscored    the reason there are no numbers on this row. Never a zero.

ARM ROWS (Phase 0, 2026-08-12). The file now also holds the moment each setup
ARMS -- a bar touching d3 (BUY) or u3 (SELL) -- so the setup can eventually be
scored on forward live data rather than on more backtest slicing. They are
told apart by `kind`:

    kind        "arm" on an arming row. ABSENT on an entry row, which is what
                every row written before today is -- absent means "entry", and
                no historical row is rewritten to say so.

An arm is NOT a trade signal. It is the setup arming; the entry may never
come, and nothing anywhere may fold an arm into an entry count. Arm rows carry
no `px` and no outcome, and `score` / `backfill` skip them by name.

    kind, interval, t, side, band, level     3 is the ONLY interval an arm is
                logged at (band_rotation.SCORED_INTERVAL) -- the interval
                §5c's 68.4% (n=19) was measured on. A payload that does not
                NAME its interval as that one logs no arm at all.
    ref_high / ref_low   the reference bar's line to beat, under its TRUE name
                -- a low is never carried as `ref_high`
    extreme     that bar's own low (BUY) / high (SELL): the touch itself
    t_1m, extreme_1m     TIMING ONLY: which 1-minute bar inside the 3-minute
                bucket actually made that extreme. 1-minute never creates a
                signal 3-minute did not have. Unidentifiable -> `t_1m: null`
                plus `t_1m_why`, never a guessed minute.
    rearm, first_t       each distinct reference is its own row (lossless). A
                run of falling lows is ONE setup, so counting SETUPS means
                counting `rearm: false` rows; `first_t` points a re-arm at the
                arm that started it.

    python trigger_log.py           # print the log as a table
    python trigger_log.py score     # fill f15/f30 AND the outcome measures
                                    # where the session allows; every row it
                                    # cannot score says why, on the row
    python trigger_log.py backfill  # recover a missing px from its receipt
"""

import json
import os
import re
import time

import band_rotation
import contract_bars

PATH = os.path.join("data", "trigger_log.jsonl")

_seen = None            # {(day, index, t, side, band, rule, kind)} on disk


def _key(row):
    # `rule` is part of the identity: a §1 touch and a §5c entry can land on
    # the same (day, index, t, side, band) and are not the same event.
    #
    # `kind` likewise: the bar that ARMS a setup and the bar that ENTERS it are
    # different events, and while §5c's branches make them different BARS
    # today, a key that cannot tell them apart would silently suppress one of
    # them if that ever stopped being true. An entry row carries no `kind` at
    # all -- absent IS "entry" -- so this reads None for every row already on
    # disk and the 259 keys there do not shift under a restart.
    return (row.get("day"), row.get("index"), row.get("t"),
            row.get("side"), row.get("band"), row.get("rule"),
            row.get("kind"))


def _dedupe(rows):
    """The rows whose identity is not already on disk, marked as seen.

    The same discipline the entry loop applies inline, over the same `_seen`
    set, because the refresh thread runs repeatedly over a GROWING session:
    without it every arm the session has ever produced would be re-appended
    once per cycle. `_load_seen` rebuilds `_seen` from the file, so a restart
    does not re-append the morning's arms either.
    """
    out = []
    for row in rows:
        k = _key(row)
        if k in _seen:
            continue
        _seen.add(k)
        out.append(row)
    return out


def _close(bar):
    """The bar's close, whichever shape the caller's bars are in.

    /api/data nests the index OHLC one level down -- a bar is
    {"t", "fut": {"o","h","l","c",...}, "ce", "pe", "gamma", "ctx"} -- while
    the cached backtest bars are flat ("c"). Reading only the flat key logged
    18 live rows with px=null on 2026-08-04, and `score` skips any row whose
    px is None, so the logger was collecting context that could never be
    given an outcome. Read both shapes rather than pick a side.
    """
    if not isinstance(bar, dict):
        return None
    fut = bar.get("fut")
    if isinstance(fut, dict) and fut.get("c") is not None:
        return fut["c"]
    return bar.get("c")


def _load_seen(path):
    global _seen
    _seen = set()
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    _seen.add(_key(json.loads(line)))
                except (ValueError, KeyError):
                    continue
    except OSError:
        pass


# ── arms: the setup ARMING, at the scored interval, timed by the minute ────

def _minute_extreme(ones, t, sell, interval, extreme):
    """Which 1-MINUTE bar inside bucket `t` made the extreme. Timing only.

    Returns ``(t_1m, extreme_1m, why)``. On any doubt it returns
    ``(None, None, <sentence>)`` -- a guessed minute would be worse than no
    minute, because the whole point of the field is to say when inside the
    candle the touch happened.

    The 1-minute bars are mapped onto their bucket by
    `contract_bars.bucket_labels`, which is built from `_buckets` -- the ONLY
    bucketing rule in this codebase, and the same one `resample_index` used to
    build the 3-minute bar this arm was detected on. A second bucketing here
    would drift silently: the logger and the tape would disagree about which
    minutes are one candle while both looked right alone.

    Two minutes printing the identical extreme leave the EARLIEST one, which
    is the one that reached the band first.

    The last guard is the load-bearing one: the minute's extreme must EQUAL
    the 3-minute bar's, because the 3-minute bar is an aggregation of exactly
    these minutes. If it does not, the two series are not the same session and
    the minute is not identified -- rather than published as though it were.
    """
    want = "high" if sell else "low"
    if not isinstance(ones, (list, tuple)) or not ones:
        return None, None, ("no 1-minute series reached the logger on this "
                            "refresh, so the minute that made the "
                            f"{want} is not identified")
    labels = contract_bars.bucket_labels(ones, interval)
    best_t = best_v = None
    for row in ones:
        if not isinstance(row, dict) or not isinstance(row.get("t"), str):
            continue
        if labels.get(row["t"]) != t:
            continue
        one = band_rotation._index_bar(row)
        v = band_rotation._num((one or {}).get("h" if sell else "l"))
        if v is None:
            continue
        if best_v is None or (v > best_v if sell else v < best_v):
            best_t, best_v = row["t"], v
    if best_v is None:
        return None, None, (f"the {interval}-minute bucket {t} holds no "
                            f"1-minute bar with a readable {want}")
    if extreme is not None and abs(best_v - extreme) > 1e-6:
        return None, None, (f"the 1-minute {want} {best_v} in bucket {t} does "
                            f"not match the {interval}-minute bar's "
                            f"{extreme} — the two series disagree, so the "
                            f"minute is not identified")
    return best_t, best_v, None


def _arm_rows(index, day_js, bars, last, day, oi, ones, interval, now):
    """Every ARM on this session's state lists, as rows ready to append.

    BOTH sides, on the operator's decision: BUY off d3 (`run_state`) and SELL
    off u3 (`run_state_sell`). Unlike the ENTRY loop above, a bar that arms on
    both sides yields TWO rows -- there is no slot to win here. An entry is one
    pill the chart draws; an arm is a setup arming, and two setups arming on
    one candle is two facts.

    The arming itself is `band_rotation.run_states`' own `arm` field, not a
    re-reading of `ref_i`: telling a fresh arm from a re-arm means knowing
    whether the previous reference expired or was moved, and that window rule
    lives in the state machine. See `run_states` for why it is stated there.
    """
    out = []
    for key, sell in (("run_state", False), ("run_state_sell", True)):
        for st in day_js.get(key) or []:
            if not isinstance(st, dict):
                continue
            arm = st.get("arm")
            if not isinstance(arm, dict):
                continue
            i = st.get("i")
            # NEVER the forming bar, for the same reason the entry loop
            # refuses it: the reference's HIGH -- the line the entry has to
            # beat -- is not final until the bar closes, and d3 itself still
            # moves as the bar's volume folds into the session VWAP. An arm
            # read mid-candle can describe a level that never existed.
            if not isinstance(i, int) or i >= last or i < 0 or i >= len(bars):
                continue
            bar = bars[i] if isinstance(bars[i], dict) else {}
            t = st.get("t")
            t1m, x1m, why = _minute_extreme(ones, t, sell, interval,
                                            arm.get("extreme"))
            row = {"kind": "arm", "at": now, "day": day, "index": index,
                   # The interval is part of the record, not context: an arm
                   # logged at any other interval would be a different setup
                   # carrying no measured number.
                   "interval": interval, "t": t,
                   "side": "SELL" if sell else "BUY", "band": arm.get("band"),
                   "rule": "5c",
                   "level": st.get("level"),
                   # The reference bar's line to beat, under its TRUE name.
                   # `run_states` emits `ref_low` on a sell and `ref_high` on a
                   # buy; copying whichever it emitted is what stops a low
                   # being carried in a field called `ref_high`.
                   ("ref_low" if sell else "ref_high"):
                       st.get("ref_low" if sell else "ref_high"),
                   # The touch itself: this bar's own low (BUY) / high (SELL).
                   "extreme": arm.get("extreme"),
                   # TIMING ONLY -- 1-minute never creates a signal 3-minute
                   # did not have. Null plus a reason, never a guessed minute.
                   "t_1m": t1m, "extreme_1m": x1m, "t_1m_why": why,
                   # Lossless: each distinct reference is its own row. Counting
                   # SETUPS means counting `rearm: false`.
                   "rearm": bool(arm.get("rearm")),
                   "first_t": arm.get("first_t"),
                   # The same context capture the entry rows have, off the same
                   # bar. Absent is null, never invented.
                   "gamma": bar.get("gamma"), "ctx": bar.get("ctx"),
                   "oi_call": oi[0], "oi_put": oi[1], "oi_strength": oi[2],
                   "closed_bar": True}
            out.append(row)
    return out


def log_new(index, payload, chain_state=None, ones=None, path=PATH):
    """Append every rotation record not yet on disk. Returns rows written.

    `payload` is build_payload's output — bytes, str or dict. Fail-soft:
    any exception is swallowed and 0 returned; the tape must never notice.

    `ones` is the session's ONE-MINUTE bars (`build_session`'s `day["bars"]`),
    used for nothing but naming the minute inside each 3-minute arm bucket
    that made the extreme. Absent -> `t_1m: null` with a reason on every arm
    row; it can never add, remove or move an arm.
    """
    try:
        if isinstance(payload, (bytes, str)):
            payload = json.loads(payload)
        day_js = (payload.get("days") or [None])[-1]
        if not day_js:
            return 0
        bars = day_js.get("bars") or []
        # BOTH sides of §5c's TWO-CANDLE rule -- the entries the chart marks.
        #
        # This read `rotation` until 2026-08-08, which is §1's ONE-CANDLE rule:
        # it marks the d3 TOUCH, not the entry, and research-findings marks it
        # VOID. So every row this logger wrote described a different bar from
        # the one the tool draws, and a forward score built on it would have
        # measured the wrong rule -- silently, and for weeks. The logger was
        # written 2026-08-04; `rotation_run` arrived 08-07 and nobody moved it.
        #
        # `rotation` is deliberately NOT logged any more. It is still published
        # for v1, and mixing two rules in one file is exactly how a forward
        # test ends up unreadable.
        rot = list(day_js.get("rotation_run") or [])
        sell = list(day_js.get("rotation_run_sell") or [])
        if len(sell) == len(rot):
            # One slot per bar on both, so a bar can carry at most one record.
            # A buy wins the slot if both ever land together -- the same
            # tie-break the chart's draw uses, so the log and the screen can
            # never disagree about which record existed.
            rot = [b if b is not None else s_ for b, s_ in zip(rot, sell)]
        elif sell and not rot:
            rot = sell
        if _seen is None:
            _load_seen(path)
        day = time.strftime("%Y-%m-%d")

        oi_call = oi_put = oi_strength = None
        if chain_state is not None:
            try:
                rows = chain_state.oi_flow(interval=15)
                if rows:
                    last = rows[-1]
                    oi_call = last.get("call")
                    oi_put = last.get("put")
                    oi_strength = last.get("strength")
            except Exception:
                pass                      # chain down != no trigger log

        # NEVER log the last bar: during a live refresh it is still FORMING,
        # and a trigger read off a forming bar can UN-FIRE when the minute
        # closes. The rule needs "the same bar CLOSES back above the band";
        # mid-minute that close is only the latest tick. Measured 2026-08-04:
        # of 12 NIFTY rows logged that morning, 5 did not exist at all once
        # their bar closed (09:19, 09:21, 09:32, 09:34, 09:35), and every
        # survivor's px was wrong -- 09:20 was logged at 24654.50 against an
        # actual close of 24672.10, a 17.6-point error on a setup whose whole
        # edge is ~21 points. Costs at most one refresh of delay.
        last = len(bars) - 1

        wrote = 0
        out = []

        # ARMS first in the batch: an arm always precedes the entry it leads
        # to, so a cycle that flushes both keeps them in that order. Across a
        # batch the file's order is APPEND order, not a claim about time —
        # `t` is the clock of record, as it always was.
        #
        # In its own try: an arming bug must never cost an ENTRY row. The
        # entries are the scored population; the arms are Phase 0 measurement
        # being started, and the newer thing yields to the older one.
        try:
            interval = payload.get("interval")
            # Operator decision, 2026-08-12: 3-minute is canonical. An arm is
            # logged at band_rotation.SCORED_INTERVAL or not at all — and the
            # payload has to NAME its interval, because a payload that does
            # not say which candles it drew cannot be taken to have drawn
            # those. `derive_payload` has published it since 2026-08-11.
            if interval == band_rotation.SCORED_INTERVAL:
                out.extend(json.dumps(r) for r in
                           _dedupe(_arm_rows(index, day_js, bars, last, day,
                                             (oi_call, oi_put, oi_strength),
                                             ones, interval, time.time())))
                wrote = len(out)
        except Exception:
            pass

        for i, rec in enumerate(rot):
            if rec is None or i >= last or bars[i] is None:
                continue
            bar = bars[i]
            row = {"at": time.time(), "day": day, "index": index,
                   "t": rec.get("t") or bar.get("t"),
                   "side": rec.get("side"), "band": rec.get("band"),
                   # Which RULE produced this row. Rows written before
                   # 2026-08-08 carry no `rule` and describe §1's one-candle
                   # TOUCH; `score` quarantines them rather than pooling two
                   # different rules into one number.
                   "rule": "5c",
                   "px": _close(bar), "trigger": rec.get("trigger"),
                   # The band price the setup armed on. The scorer needs it to
                   # place the operator's stop (`band_rotation._stop_px`), and
                   # until today the only copy of it on an entry row was inside
                   # the receipt SENTENCE. Logged as a number so the scorer
                   # reads a field instead of parsing prose; the three rows
                   # already on disk predate this and are recovered from the
                   # receipt, which `_level_of` marks as such.
                   "level": rec.get("level"),
                   "gamma": bar.get("gamma"), "ctx": bar.get("ctx"),
                   "oi_call": oi_call, "oi_put": oi_put,
                   "oi_strength": oi_strength,
                   # Provenance, not decoration: rows written before the
                   # forming-bar fix lack this key, and `score` refuses them.
                   # That quarantines the 2026-08-04 morning batch without
                   # deleting it -- the context in those rows is still real,
                   # only the trigger and the price are not trustworthy.
                   "closed_bar": True}
            k = _key(row)
            if k in _seen:
                continue
            _seen.add(k)
            out.append(json.dumps(row))
            wrote += 1
        if out:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n".join(out) + "\n")
        return wrote
    except Exception:
        return 0


# ── reading: one parse, so a second reader cannot invent a second row shape ─

def read(path=PATH):
    """(rows oldest-first, count of lines that would not parse).

    `show`, `score` and `backfill` each spell `[json.loads(x) for x in f]`
    inline, which was fine while every reader lived in this file. /api/signals
    is a reader in ANOTHER module, and a row shape re-implemented there is a
    row shape that can drift from the one `log_new` writes — so the parse
    lives here, once, and the server calls it.

    OSError is deliberately NOT swallowed. A caller that cannot tell "the log
    is missing" from "the log is empty" will render one as the other, and on a
    screen whose entire job is the record those are opposite facts. Unparsable
    LINES are counted rather than raised: one truncated tail (a write cut off
    by a kill) must not hide the 258 rows above it, but it must not vanish
    silently either.
    """
    rows, bad = [], 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                bad += 1
    return rows, bad


# ── repair: recover a missing px from the detector's own receipt ───────────

_CLOSED_RE = re.compile(r"closed\s+(\d+(?:\.\d+)?)\s+back\s+(?:above|below)\b")


def backfill(path=PATH):
    """Fill px on rows logged without one, from their `trigger` sentence.

    band_rotation's receipt ends "... and the same bar closed 24643.00 back
    above it" -- that number IS the close the row should have carried, so
    this recovers it exactly rather than approximating from a neighbouring
    bar. Verified against the live tape on 2026-08-04: the 09:36 record's
    sentence read 24650.90 and the same bar's fut.c was 24650.9.

    Idempotent -- rows that already have a px are left untouched. Needed
    once because of the schema bug in `_close`; kept because a future bar
    could go missing for other reasons and the sentence always survives.
    """
    try:
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(x) for x in f if x.strip()]
    except OSError:
        print(f"no log at {path}")
        return 0
    fixed = unrecoverable = 0
    for r in rows:
        if r.get("kind") == "arm":
            # An arm has no entry price to recover and no receipt sentence to
            # recover one from: nothing was entered. Counting it as
            # "unrecoverable" would report a repair that was never owed.
            continue
        if r.get("px") is not None:
            continue
        m = _CLOSED_RE.search(r.get("trigger") or "")
        if m:
            r["px"] = float(m.group(1))
            fixed += 1
        else:
            unrecoverable += 1
    if fixed:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(json.dumps(r) for r in rows) + "\n")
        os.replace(tmp, path)
    print(f"{len(rows)} rows, {fixed} px recovered"
          + (f", {unrecoverable} with no parsable receipt" if unrecoverable
             else ""))
    return fixed


# ── scoring: fill f15/f30 by clock label, never at log time ────────────────

def _mins(t):
    try:
        hh, mm = t.split(":")
        return int(hh) * 60 + int(mm)
    except (AttributeError, ValueError):
        return None


# ── the session tape a row is scored against ──────────────────────────────

def _load_sessions(index):
    """Every cached session for one index, `{day: {"bars": [...]}}`.

    The one seam between this module and the cache on disk, so a test can hand
    the scorer a session without writing files into data/backtest/ -- and so
    there is exactly one line to change if the cache ever moves.
    """
    from squeeze_score import load
    return load(index)


def _session_bars(index, day, cache):
    """`([bars at SCORED_INTERVAL, banded], None)` or `(None, why)`.

    ONE loading path, `squeeze_score.load` -- the same one `score` has always
    used for f15/f30 -- so the candles an outcome is measured on are the
    candles §5c was measured on (`vwap_bands` THEN `resample`, at
    `band_rotation.SCORED_INTERVAL`). Deriving a second series here would let
    the scorer and the tape disagree about which minutes are one bar.

    READING THIS CACHE IS NOT SLICING IT. research-findings §5 closed
    `data/backtest/` to further re-cutting: no NEW hypothesis may be searched
    out of it, because seven consecutive searches already manufactured two
    findings that evaporated. Filling the outcome of a row that was written
    FORWARD -- logged the instant the tape showed it, months of sessions
    before anyone looked at these bars -- is the other route §5 names, and is
    the one this file exists for. What would cross the line is pointing this
    loader at a question nobody pre-registered. Do not.

    A missing session is a REASON, never an empty list: "could not score" and
    "scored, moved nothing" are opposite facts and must render differently.

    `cache` is the caller's own dict, one per `score` run rather than a module
    global: the cache exists to avoid re-parsing 70-odd sessions per row, and
    a global one would also mean a second run in the same process could not
    see a session that had arrived in between.
    """
    key = (index, day)
    if key in cache:
        return cache[key]
    try:
        sess = _load_sessions(index).get(day)
    except Exception as e:                     # noqa: BLE001 -- reported, not raised
        sess = None
        why = (f"the cached tape for {index} could not be loaded "
               f"({type(e).__name__}: {e}), so nothing forward of this row "
               f"was read")
    else:
        why = (f"no cached {index} session for {day} in data/backtest/, so no "
               f"bar after this row could be read — this row is UNMEASURED, "
               f"not flat")
    out = ((sess["bars"], None) if sess and sess.get("bars")
           else (None, why))
    cache[key] = out
    return out


def _closes_for(day, index, cache):
    """{minute-of-day: close} for one cached session, or None.

    Kept as f15/f30's own reader so that measure keeps exactly the semantics
    it had, but pointed at `_session_bars` rather than loading a second time:
    one parse of the cache per (index, day) per run.
    """
    bars, _why = _session_bars(index, day, cache)
    if bars is None:
        return None
    out = {}
    for b in bars:
        m = _mins(b.get("t"))
        if m is not None and b.get("c") is not None:
            out[m] = b["c"]
    return out or None


# ── SCORING THE OUTCOME ───────────────────────────────────────────────────
#
# THE OPERATOR'S OWN SPEC, 2026-08-12, verbatim:
#
#     "check that after it generates any signals what the max market moves
#      from price and did it touch the other side +-2 std +-3 std and beyond.
#      because i try to hold the trade if oi is heavy on that side."
#
# Four measures per row, from its anchor bar forward to 15:15:
#
#   MFE / MAE   the furthest FAVOURABLE and furthest ADVERSE move in points,
#               each with the clock it was reached. Bar EXTREMES, not closes:
#               "what the max market moves" is the move, and a close never
#               shows the wick that hit the target or the stop.
#   STOP        did price break the operator's own 20-point stop, and when.
#               Recording it DOES NOT END THE MEASUREMENT -- see `_outcome`.
#   BANDS       how far the OTHER side was reached: +/-1, +/-2, +/-3 sigma and
#               beyond, first-touch clock each, read LIVE -- see `_reached`.
#
# Signs are side-aware throughout, exactly as f15/f30 already are: a positive
# number is a move in the row's own favour, on a BUY and on a SELL alike.

# The operator's own flat-by time. Every measure below stops here -- a move
# that happened at 15:20 is not a move they could have been in. Bars are
# included while their LABEL is strictly before it: a 15:15-labelled candle on
# a 3-minute tape covers 15:15-15:18, which is after the flat.
FLAT_BY = "15:15"
FLAT_BY_MIN = 15 * 60 + 15

# How many scored §5c rows this log was built to collect before its questions
# can be read at all. The module docstring's own target ("~20-25 live
# signals"); research-findings §5e sets n >= 15 as the floor below which the
# result is INCONCLUSIVE and gets no verdict, favourable or not. Nothing here
# prints a rate at any n -- see `rate_refusal` for the second reason.
TARGET_N = 20

# "index low touched d3 57611.96 at 09:37, then closed ..." -- `_run_why`'s
# receipt. Worded so it cannot collide with `_trigger_why`'s sentence, which
# `_CLOSED_RE` above parses; these two must stay tellable apart.
_TOUCH_RE = re.compile(r"touched\s+([ud]\d)\s+(\d+(?:\.\d+)?)")


def _level_of(row):
    """`(level, where it came from)` -- the band price the setup armed on.

    The row's own `level` field when it has one. Rows written before
    2026-08-12 have none, so it is recovered from the detector's own receipt
    -- the same trick `backfill` uses on `px`, and exact rather than
    approximated. The band NAME in the sentence has to match the row's `band`
    or nothing is returned: a number lifted out of a sentence describing a
    different band is worse than no number.
    """
    lvl = band_rotation._num(row.get("level"))
    if lvl is not None:
        return lvl, "level"
    m = _TOUCH_RE.search(row.get("trigger") or "")
    if m and m.group(1) == row.get("band"):
        return float(m.group(2)), "trigger receipt"
    return None, None


def _reached(bars, sell):
    """How far the OPPOSITE side of the band was reached over `bars`.

    For a BUY armed on d3 that is u1 / u2 / u3 and beyond; for a SELL armed on
    u3, the d1 / d2 / d3 mirror. It is the side the operator takes profit on:
    *"target is always +2 and +3 std"*.

    THE BANDS ARE READ LIVE -- each bar is tested against ITS OWN band values,
    never against the ones frozen on the anchor bar. The operator trails band
    to band and the session VWAP keeps moving all day, so u2 at 09:38 is not
    u2 at 11:20. Freezing the anchor's numbers would score a target they were
    never trading toward, and on a trending session it would report a level
    "reached" that the chart never printed.

    `sigma` is how far the excursion got in the band's OWN sigma units,
    measured on the bar that got furthest. That is what answers *"and
    beyond"*: a touch of u3 and a run past it are the same event at the level
    test (u3 IS +3 sigma), and only the distance tells them apart.

    A bar whose bands cannot be read is counted in `no_band` rather than
    treated as a non-touch -- an unreadable band is not evidence price stayed
    inside it.
    """
    names = ("d1", "d2", "d3") if sell else ("u1", "u2", "u3")
    first = {n: None for n in names}
    best = best_t = None
    no_band = 0
    for b in bars:
        ext = band_rotation._num(b.get("l" if sell else "h"))
        vwap = band_rotation._num(b.get("vwap"))
        one = band_rotation._num(b.get(names[0]))
        sig = None if (vwap is None or one is None) else (
            (vwap - one) if sell else (one - vwap))
        if ext is None or sig is None or sig <= 0:
            no_band += 1
            continue
        for n in names:
            if first[n] is not None:
                continue
            lvl = band_rotation._num(b.get(n))
            if lvl is None:
                continue
            if (ext <= lvl) if sell else (ext >= lvl):
                first[n] = b.get("t")
        s = ((vwap - ext) if sell else (ext - vwap)) / sig
        if best is None or s > best:
            best, best_t = s, b.get("t")
    touched = [n for n in names if first[n] is not None]
    out = {"side": "d" if sell else "u"}
    out.update({n: first[n] for n in names})
    # `furthest` names the outermost band actually touched; `beyond` says the
    # excursion carried PAST it. They are reported apart because "reached +3"
    # and "went through +3" are the two different things the operator asked
    # about in one sentence.
    out.update({"furthest": touched[-1] if touched else None,
                "beyond": bool(best is not None and best > 3.0),
                "sigma": None if best is None else round(best, 2),
                "sigma_t": best_t, "no_band": no_band})
    return out


def _arm_trigger(row, bars, sell):
    """`(triggered, when, why not / why unknown)` for one ARM row.

    The question arms exist to answer is whether the TRIGGER condition earns
    its keep or filters out winners, and that cannot be read without knowing
    which arms went on to fire. The answer is taken from
    `band_rotation.run_states` replayed on this session -- the one state
    machine, not a second reading of the rule here.

    It is a RE-DERIVATION, and says so when it cannot be made: if the cached
    session shows no arm on this row's own bar, the honest answer is "not
    re-derived", never "did not trigger". The two would look identical on a
    screen and mean opposite things.
    """
    states = band_rotation.run_states(
        bars, stop_pts=band_rotation.OPERATOR_STOP_PTS,
        side="SELL" if sell else "BUY")
    i = next((s["i"] for s in states
              if s.get("t") == row.get("t") and s.get("arm") is not None), None)
    if i is None:
        return None, None, (
            f"replaying the setup on the cached {row.get('index')} "
            f"{row.get('day')} session shows no arm on the {row.get('t')} "
            f"candle, so whether this setup triggered was NOT re-derived — "
            f"this is not 'it did not trigger'")
    first_t = (states[i]["arm"] or {}).get("first_t")
    beat = "below" if sell else "above"
    for s in states[i + 1:]:
        a = s.get("arm")
        if a is not None and not a.get("rearm") and a.get("first_t") != first_t:
            return False, None, (f"a NEW setup armed at {s.get('t')} before "
                                 f"any candle closed {beat} this one's line")
        if s.get("entry") is not None:
            return True, s.get("t"), None
        if s.get("ref_i") is None and s.get("readable"):
            return False, None, (f"the reference expired at {s.get('t')} with "
                                 f"no candle closing {beat} it")
    return False, None, "the session ended with the setup still unfired"


def _outcome(row, bars):
    """The operator's four measures for one row, or `(None, why)`.

    ANCHOR. An entry row is measured from `px`, the close the rule entered on.
    An arm row has NO entry price -- nothing was entered -- so it is measured
    from the ARM CANDLE'S OWN CLOSE, read out of the session. Which one was
    used is written onto the row as `anchor`/`anchor_px`, because a reader who
    has to infer which price a number is measured from will eventually infer
    wrong, and every number here is in points from that price.

    The window opens on the bar AFTER the anchor bar. The anchor is that bar's
    CLOSE, so the bar's own high and low were printed before the position
    existed; counting them would credit the row with a move it could not have
    been in. It closes at `FLAT_BY`.

    THE STOP IS RECORDED, NOT OBEYED. `stop_hit`/`stop_t` say the operator's
    20 points broke and when; `mfe` keeps measuring to 15:15 regardless. The
    operator asked for exactly this -- *"i try to hold the trade if oi is
    heavy on that side"* -- so "this was stopped out" and "this would have
    worked" are two separate facts and both stay readable on the one row. A
    scorer that stopped measuring at the stop could not tell them apart.
    """
    sell = row.get("side") == "SELL"
    m = _mins(row.get("t"))
    if m is None:
        return None, ("this row carries no readable HH:MM label, so it cannot "
                      "be placed in its own session")

    if row.get("kind") == "arm":
        at = next((b for b in bars if b.get("t") == row.get("t")), None)
        anchor_px = band_rotation._num((at or {}).get("c"))
        if anchor_px is None:
            return None, (f"the cached {row.get('index')} {row.get('day')} "
                          f"session holds no {row.get('t')} candle with a "
                          f"readable close, and an arm is measured from its "
                          f"own candle's close — there is nothing to measure "
                          f"FROM")
        anchor = "arm_close"
    else:
        anchor_px = band_rotation._num(row.get("px"))
        if anchor_px is None:
            return None, ("this row carries no px, so there is no entry price "
                          "to measure from; `python trigger_log.py backfill` "
                          "recovers one where the receipt survives")
        anchor = "entry_close"

    win = [b for b in bars
           if _mins(b.get("t")) is not None
           and m < _mins(b.get("t")) < FLAT_BY_MIN]
    if not win:
        return None, (f"the cached {row.get('index')} {row.get('day')} session "
                      f"holds no candle after {row.get('t')} and before "
                      f"{FLAT_BY}, so there is no forward window — this row is "
                      f"UNMEASURED, not flat")

    sgn = -1 if sell else 1
    mfe = mfe_t = mae = mae_t = None
    for b in win:
        fav = band_rotation._num(b.get("l" if sell else "h"))
        adv = band_rotation._num(b.get("h" if sell else "l"))
        if fav is not None:
            v = sgn * (fav - anchor_px)
            if mfe is None or v > mfe:
                mfe, mfe_t = v, b.get("t")
        if adv is not None:
            v = sgn * (adv - anchor_px)
            if mae is None or v < mae:
                mae, mae_t = v, b.get("t")

    level, level_src = _level_of(row)
    # NEVER recomputed here. One expression for the stop, in band_rotation,
    # shared with the re-fire lock and the published field -- the comment above
    # OPERATOR_STOP_PTS says two copies of a risk parameter drift silently, and
    # a scorer's stop differing from the chart's is exactly that failure.
    stop_px = band_rotation._stop_px(level, band_rotation.OPERATOR_STOP_PTS,
                                     sell)
    stop_hit = stop_t = None
    if stop_px is not None:
        stop_hit = False
        for b in win:
            ext = band_rotation._num(b.get("h" if sell else "l"))
            if ext is None:
                continue
            if (ext >= stop_px) if sell else (ext <= stop_px):
                stop_hit, stop_t = True, b.get("t")
                break

    out = {
        "anchor": anchor, "anchor_px": anchor_px, "anchor_t": row.get("t"),
        "scored_from": win[0].get("t"), "scored_to": FLAT_BY,
        "mfe": None if mfe is None else round(mfe, 2), "mfe_t": mfe_t,
        "mae": None if mae is None else round(mae, 2), "mae_t": mae_t,
        "stop_px": stop_px, "stop_hit": stop_hit, "stop_t": stop_t,
        # Where the band price came from. A level lifted out of a sentence and
        # a level the detector logged are both usable and are not the same
        # provenance, so the row says which one placed its stop.
        "stop_from": level_src,
        "stop_why": None if stop_px is not None else (
            "this row carries no `level` and its receipt names no band price, "
            "so the operator's stop could not be placed — it is unknown "
            "whether it broke, not that it held"),
        "bands": _reached(win, sell),
        "scored_at": time.time(),
    }
    if row.get("kind") == "arm":
        fired, when, why = _arm_trigger(row, bars, sell)
        out.update({"triggered": fired, "trigger_t": when, "trigger_why": why})
    return out, None


def rate_refusal(n):
    """Why no hit rate, win rate or expectancy is printed. Published, not
    restated: server.py hands this sentence to the screen so the rule lives in
    one language, the way the 09:25 gate should have."""
    head = (f"{n} scored §5c entr{'y' if n == 1 else 'ies'} — LIVE forward "
            f"rows, not a backtest.")
    if n < TARGET_N:
        return (f"{head} No hit rate, win rate or expectancy: this log was "
                f"built to collect ~{TARGET_N}-25 signals before its questions "
                f"can be read, and research-findings §5e calls anything under "
                f"15 INCONCLUSIVE — no verdict, favourable or not. A rate over "
                f"{n} row{'' if n == 1 else 's'} would be a number about noise.")
    return (f"{head} Still no hit rate, win rate or expectancy here: §5e "
            f"records the pass criterion as OWED BY THE OPERATOR and not to be "
            f"invented, so the rows are printed and the reading is theirs.")


def score(path=PATH, quiet=False):
    """Fill f15/f30 AND the operator's outcome measures, in place.

    IDEMPOTENT AND ADDITIVE. Only outcome fields are ever written; `at`, `t`,
    `px`, `level` and everything else the logger stamped are read and never
    touched, and any key this module does not recognise rides through the
    rewrite verbatim (rows are parsed whole and re-dumped whole). A row is
    rewritten only when its dict actually changed, so a second run over an
    unchanged log writes nothing at all and the file stays byte for byte the
    one the first run left.
    """
    try:
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(x) for x in f if x.strip()]
    except OSError:
        print(f"no log at {path}")
        return
    closes, sessions = {}, {}
    changed = skipped = scored = unscored = 0
    lines = []
    for r in rows:
        before = json.dumps(r, sort_keys=True)
        arm = r.get("kind") == "arm"
        if not r.get("closed_bar"):
            # Logged by the pre-2026-08-04 forming-bar path: the trigger may
            # never have existed on the closed bar, and px is a mid-minute
            # tick. Scoring these would pollute the sample with signals the
            # backtested rule would not have produced. Quarantined by RULE,
            # not by missing data, so no `unscored` reason is written onto
            # them -- there is nothing about them a fuller cache would fix.
            skipped += 1
            continue
        if r.get("rule") != "5c":
            # Written before 2026-08-08, when this logger read `rotation` --
            # §1's ONE-CANDLE rule, which marks the d3 TOUCH and which
            # research-findings marks VOID. Those rows describe a different
            # BAR from the entries the tool now draws. Quarantined, not
            # deleted: the gamma/ctx/OI context in them is still real, only
            # the rule they belong to is not the one being scored.
            skipped += 1
            continue

        # f15/f30 -- ENTRIES ONLY, and untouched in meaning. An arm has no
        # entry price, so there is no forward move FROM anything; measuring one
        # would manufacture an outcome for a trade that may never have been
        # taken. The outcome block below CAN score an arm, because it says out
        # loud that its anchor is the arm candle's close and not an entry.
        if not arm and r.get("f30") is None and r.get("px") is not None:
            ck = (r["day"], r["index"])
            if ck not in closes:
                closes[ck] = _closes_for(*ck, cache=sessions)
            cs = closes[ck]
            m = _mins(r.get("t"))
            if cs and m is not None:
                sgn = 1 if r.get("side") == "BUY" else -1
                for name, dm in (("f15", 15), ("f30", 30)):
                    # the first close at or after t+dm
                    hit = next((cs[k] for k in sorted(cs) if k >= m + dm), None)
                    r[name] = (None if hit is None
                               else round(sgn * (hit - r["px"]), 2))

        if r.get("mfe") is None:
            bars, why = _session_bars(r.get("index"), r.get("day"), sessions)
            out = None
            if bars is not None:
                out, why = _outcome(r, bars)
            if out is None:
                # NEVER a zero and never a silent skip: the row says why it
                # holds no numbers, in words, and stays retryable -- a session
                # that lands in the cache tomorrow scores it then.
                r["unscored"] = why
                unscored += 1
            else:
                r.update(out)
                # Cleared, not left behind: a row that reads both "scored" and
                # "could not be scored" is a row nobody can act on.
                r.pop("unscored", None)
                scored += 1
                lines.append(_line(r))
        if json.dumps(r, sort_keys=True) != before:
            changed += 1

    if changed:
        # THE FILE IS APPENDED TO WHILE THIS RUNS. server.py's per-index
        # refresh threads write a row the moment the tape shows one, and this
        # function is a read / modify / REWRITE: a row appended between the
        # read above and the replace below would be erased by it. Nothing here
        # is worth losing a live signal for, so the line count is re-checked
        # against the read and the write is abandoned -- not forced -- if the
        # log grew. Scoring is idempotent, so the fix is to run it again.
        with open(path, encoding="utf-8") as f:
            now = sum(1 for line in f if line.strip())
        if now != len(rows):
            print(f"ABANDONED: the log grew from {len(rows)} to {now} rows "
                  f"while scoring (the tape logged one). Nothing was written; "
                  f"re-run `python trigger_log.py score`.")
            return 0, skipped
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(json.dumps(r) for r in rows) + "\n")
        os.replace(tmp, path)
    if not quiet:
        for line in lines:
            print(line)
        print(f"{len(rows)} rows, {changed} rewritten, {scored} newly scored, "
              f"{unscored} could not be scored (each carries its reason)"
              + (f", {skipped} quarantined (forming-bar capture or the void "
                 f"one-candle rule)" if skipped else ""))
        five = [r for r in rows if r.get("kind") != "arm"
                and r.get("rule") == "5c" and r.get("mfe") is not None]
        print(rate_refusal(len(five)))
    return changed, skipped


def _line(r):
    """One scored row as a sentence. Facts the row carries, nothing derived."""
    b = r.get("bands") or {}
    far = ("beyond " + str(b.get("furthest")) if b.get("beyond")
           else b.get("furthest"))
    stop = ("stop UNPLACEABLE" if r.get("stop_hit") is None else
            f"stop HIT {r.get('stop_t')}" if r.get("stop_hit") else "stop held")
    tail = ""
    if r.get("kind") == "arm":
        tail = ("  triggered " + (f"{r.get('trigger_t')}"
                                  if r.get("triggered") else
                                  "NOT RE-DERIVED" if r.get("triggered") is None
                                  else "no"))
    return (f"{r.get('day')} {r.get('t')} {r.get('index'):<10} "
            f"{r.get('side'):<4} {r.get('band'):<3} "
            f"{r.get('anchor')}={r.get('anchor_px')}  "
            f"MFE {r.get('mfe'):+.1f} @{r.get('mfe_t')}  "
            f"MAE {r.get('mae'):+.1f} @{r.get('mae_t')}  {stop}  "
            f"other side {far or 'not reached'}"
            f"{'' if b.get('sigma') is None else f' ({b['sigma']:+.2f}σ)'}"
            f"{tail}")


def show(path=PATH):
    try:
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(x) for x in f if x.strip()]
    except OSError:
        print(f"no log yet at {path} — it appears after the first live trigger")
        return
    # Two populations, never one table. An arm carries no px and no outcome,
    # so printing it in the entry columns would show a trade at price 0.
    arms = [r for r in rows if r.get("kind") == "arm"]
    rows = [r for r in rows if r.get("kind") != "arm"]
    print(f"{'':<2}{'day':<12}{'idx':<10}{'t':<7}{'side':<5}{'band':<5}"
          f"{'px':>9} {'gamma':<14}{'oi_str':>7} {'f15':>7} {'f30':>7}")
    for r in rows:
        s = r.get("oi_strength")
        f15 = r.get("f15")
        f30 = r.get("f30")
        g = r.get("gamma")                  # a dict per bar; the column wants
        if isinstance(g, dict):             # the one field the operator reads
            g = g.get("regime")
        # "!" = captured off a forming bar; the trigger may never have
        # survived its own bar's close. Marked, never silently mixed in.
        print(f"{('' if r.get('closed_bar') else '!'):<2}"
              f"{r.get('day', ''):<12}{r.get('index', ''):<10}"
              f"{r.get('t', ''):<7}{r.get('side', ''):<5}{r.get('band', ''):<5}"
              f"{(r.get('px') or 0):>9.1f} {str(g or '—'):<14}"
              f"{(f'{s:+.2f}' if s is not None else '   —'):>7} "
              f"{(f'{f15:+.1f}' if f15 is not None else '—'):>7} "
              f"{(f'{f30:+.1f}' if f30 is not None else '—'):>7}")
        # The outcome, on its own line under the row, because it is measured
        # from a named price and squeezing "MFE" into a column of a table whose
        # px column means something else is how the two get read as one number.
        if r.get("mfe") is not None:
            print(f"{'':<2}  {_line(r)}")
        elif r.get("unscored"):
            print(f"{'':<2}  not scored — {r['unscored']}")
    print("\n" + rate_refusal(sum(1 for r in rows if r.get("rule") == "5c"
                                  and r.get("mfe") is not None)))
    if not arms:
        return
    setups = sum(1 for r in arms if not r.get("rearm"))
    print(f"\n{len(arms)} ARM rows — the setup arming, NOT trades: "
          f"{setups} setup{'' if setups == 1 else 's'}, "
          f"{len(arms) - setups} re-arm{'' if len(arms) - setups == 1 else 's'}. "
          f"Never added to the counts above.")
    print(f"{'':<2}{'day':<12}{'idx':<10}{'t':<7}{'side':<5}{'band':<5}"
          f"{'level':>9} {'extreme':>9} {'1m':>7}")
    for r in arms:
        t1 = r.get("t_1m")
        print(f"{('R' if r.get('rearm') else ''):<2}"
              f"{r.get('day', ''):<12}{r.get('index', ''):<10}"
              f"{r.get('t', ''):<7}{r.get('side', ''):<5}{r.get('band', ''):<5}"
              f"{(r.get('level') or 0):>9.2f} {(r.get('extreme') or 0):>9.2f} "
              f"{(t1 or '—'):>7}")
        # An arm's outcome is measured from the ARM CANDLE'S CLOSE, which is
        # why `_line` prints that anchor by name on every row it renders.
        if r.get("mfe") is not None:
            print(f"{'':<2}  {_line(r)}")
        elif r.get("unscored"):
            print(f"{'':<2}  not scored — {r['unscored']}")


if __name__ == "__main__":
    import sys
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "score":
        score()
    elif verb == "backfill":
        backfill()
    else:
        show()
