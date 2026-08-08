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

    python trigger_log.py           # print the log as a table
    python trigger_log.py score     # fill f15/f30 where the session allows
    python trigger_log.py backfill  # recover a missing px from its receipt
"""

import json
import os
import re
import time

PATH = os.path.join("data", "trigger_log.jsonl")

_seen = None            # {(day, index, t, side, band)} already on disk


def _key(row):
    # `rule` is part of the identity: a §1 touch and a §5c entry can land on
    # the same (day, index, t, side, band) and are not the same event.
    return (row.get("day"), row.get("index"), row.get("t"),
            row.get("side"), row.get("band"), row.get("rule"))


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


def log_new(index, payload, chain_state=None, path=PATH):
    """Append every rotation record not yet on disk. Returns rows written.

    `payload` is build_payload's output — bytes, str or dict. Fail-soft:
    any exception is swallowed and 0 returned; the tape must never notice.
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


def _closes_for(day, index):
    """{minute-of-day: close} for one cached session, or None."""
    try:
        from squeeze_score import load
        d = load(index).get(day)
        if not d:
            return None
        out = {}
        for b in d["bars"]:
            m = _mins(b.get("t"))
            if m is not None:
                out[m] = b["c"]
        return out
    except Exception:
        return None


def score(path=PATH):
    """Fill f15/f30 for rows whose session is now in data/backtest/."""
    try:
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(x) for x in f if x.strip()]
    except OSError:
        print(f"no log at {path}")
        return
    closes = {}
    changed = 0
    skipped = 0
    for r in rows:
        if not r.get("closed_bar"):
            # Logged by the pre-2026-08-04 forming-bar path: the trigger may
            # never have existed on the closed bar, and px is a mid-minute
            # tick. Scoring these would pollute the sample with signals the
            # backtested rule would not have produced.
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
        if r.get("f30") is not None or r.get("px") is None:
            continue
        ck = (r["day"], r["index"])
        if ck not in closes:
            closes[ck] = _closes_for(*ck)
        cs = closes[ck]
        m = _mins(r.get("t"))
        if not cs or m is None:
            continue
        sgn = 1 if r.get("side") == "BUY" else -1
        for name, dm in (("f15", 15), ("f30", 30)):
            # the first close at or after t+dm
            hit = next((cs[k] for k in sorted(cs) if k >= m + dm), None)
            r[name] = None if hit is None else round(sgn * (hit - r["px"]), 2)
        changed += 1
    if changed:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(json.dumps(r) for r in rows) + "\n")
        os.replace(tmp, path)
    print(f"{len(rows)} rows, {changed} newly scored"
          + (f", {skipped} quarantined (forming-bar capture, not scorable)"
             if skipped else ""))
    return changed, skipped


def show(path=PATH):
    try:
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(x) for x in f if x.strip()]
    except OSError:
        print(f"no log yet at {path} — it appears after the first live trigger")
        return
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


if __name__ == "__main__":
    import sys
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    if verb == "score":
        score()
    elif verb == "backfill":
        backfill()
    else:
        show()
