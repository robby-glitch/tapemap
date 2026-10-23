"""confluence_log.py -- the confluence setup's FORWARD LOG, data/confluence_log.jsonl (CONFLUENCE-PREREG.md §6).

ONE WRITE-ONCE ROW PER ZONE ENTRY, written once its window has closed: ZONE / OI / FLOW at the trigger bar and at each
of the next 3 bars, each read as at that bar's own close (confluence.evaluate cuts every input there), the §1 stamps,
and the confluence entry if there is one, with the two ATM premiums at entry (§5). NO OUTCOME IS EVER WRITTEN HERE:
R is the scorer's, recomputed from bars (tools/confluence_score.py). Keyed (day, index, t, side); a restart re-reads
the keys and never writes a row twice.

WIRING. server.py's per-index refresh thread calls `log_new` right after trigger_log.log_new, with the same payload.
It changes no existing log, row, gate or beep: it only appends to its own file. Fail-soft by contract (trigger_log's
rule, the 2026-07-27 frozen-tape post-mortem): any exception is swallowed and 0 returned. The files are read only on
a cycle that has a row due -- a handful of times a session -- and once for all the rows due on that cycle.

ONE LOADER, `inputs`, serves this file AND the one-shot, so a forward row and the scorer read the same records the same
way, each through its owner's constant at call time (a --mock-chain run reads data/mock/):
  chain_live.CHAIN_DIR  chain_<IDX>_<day>          OI fronts + ATM premiums (+ chain_backfill's minutes the
                                                   recorder never saw, its own rule: never clobber the socket)
  book_log.DIR          book_<IDX>_<day>           FLOW: Upstox futures frames, sided by ladder (rank.py's record)
  tape_log.DIR          tape_ / ofd_marks_NIFTY    GoCharting's 5-min bars (the disagreement check) and marks (R/T/P)
  decoder_log.DIR       decoder_<day>              the decoder's events (R/T/P stamps), NIFTY
  READ_DIR              read_<day>                 the READ word (stamp)
  trigger_log.PATH      the zone entry rows         NON-OUTCOME FIELDS ONLY (`LOGGED`): the §1d gate and ctx stamps
  squeeze_score.BT      fut_<prior day>             yesterday's futures high / low (PDH / PDL stamp)

§1m HOLD v2 reads no row of its own: `push_bars` / `push_refs` load the 5-min push bars and their references (the
tape_ / ux_ records under tape_log.DIR) for hold2.py, the same way for tools/hold2_score.py and the server's hold window.

§1n FADE-D (FADE-D-PREREG.md, Logging) shares it too: one write-once row per location episode (`setup: "FADE-D"`, keyed
("FADE-D", day, index, side, t)) once its 30-min window has closed, with the 2a / 2b / 3 readings at each 5-min close
and the entry if any (faded.row). `log_faded` is its own fail-soft call beside `log_ride`, at most one check per 5-min
bar per index; `faded_inputs` is the loader it, tools/faded_score.py and tools/decode_now.py share.

§1j RIDE (RIDE-PREREG.md §6) shares the file: one write-once row per READ-V2 §E ENTRY (`setup: "RIDE"`, keyed
("RIDE", day, index, t)), with LOCATION / OI / FLOW at the §E bar and the next 3 bars, the stamps and the RIDE entry if
any. FADE's rows carry `setup: "FADE"`. `log_ride` is its own fail-soft call beside `log_new`; `ride_inputs` is the
loader it and tools/ride_score.py share (server._v2_parts up to compose, on v2feed's warm Day, + `inputs` above).
"""
from __future__ import annotations

import glob
import importlib
import json
import os
import sys
import threading
import time

import band_rotation
import book_log
import chain_backfill
import chain_live
import confluence as C
import contract_bars as cb
import daylog
import decoder_log
import faded
import hold2
import rank
import read
import ride
import squeeze_score
import tape_log
import trigger_log

PATH = os.path.join("data", "confluence_log.jsonl")
READ_DIR = os.path.join("data", "read")
GRACE = 1                   # minutes after the window's last close before a row is written: the chain's last
                            # snapshot of that minute and GoCharting's 5-min bar land seconds after it [plumbing]
CLOSE = 15 * 60 + 30        # after this every bar of the session is closed

# trigger_log's NON-outcome fields: the only ones kept. mfe / mae / stop_* / scored_* / triggered / f15 / f30 / bands /
# anchor_* / unscored are dropped at the parse, so nothing downstream can read one (CONFLUENCE-PREREG.md §2).
LOGGED = ("day", "index", "t", "side", "band", "rule", "kind", "px", "level", "trigger", "ctx", "gate", "closed_bar")

_seen = None
_lock = threading.Lock()


def _key(r):
    if r.get("setup") == "RIDE":
        return ("RIDE", r.get("day"), r.get("index"), r.get("t"))
    if r.get("setup") == "FADE-D":
        return ("FADE-D", r.get("day"), r.get("index"), r.get("side"), r.get("t"))
    return (r.get("day"), r.get("index"), r.get("t"), r.get("side"))


def _rows(path):
    """A day file's rows (its .jsonl.gz once daylog has compressed it); a torn line is skipped; missing -> nothing."""
    try:
        with daylog.open_text(path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict):
                    yield r
    except OSError:
        return


def logged(path=None):
    """trigger_log's zone ENTRY rows, {(day, index, t, side): row}, each cut to `LOGGED` before anything reads it."""
    out = {}
    for r in _rows(path or trigger_log.PATH):
        if r.get("rule") == "zone" and r.get("kind") is None:
            r = {k: r[k] for k in LOGGED if k in r}
            out[_key(r)] = r
    return out


def session(index, day):
    """The cached 1-min futures session (data/backtest, the zone machine's own series): its 3-min bars, its 1-min
    bars with the live session VWAP, and the future's expiry -- or None."""
    p = next((p for p in squeeze_score._paths(index) if os.path.basename(p)[4:14] == day), None)
    if p is None:
        return None
    with open(p, encoding="utf-8") as f:
        payload = json.load(f)
    ones = cb.vwap_bands(cb.to_bars(payload))
    if not any(ones):
        return None
    return {"bars": list(cb.resample(ones, C.INTERVAL)), "ones": [b for b in ones if b],
            "expiry": (payload.get("_meta") or {}).get("expiry")}


def _chain_path(index, day):
    return os.path.join(str(chain_live.CHAIN_DIR), f"chain_{index}_{day}.jsonl")


def prior(index, day, expiry=None):
    """Yesterday's futures high / low: the latest recorded session before `day` (chain or cache), only when the cache
    holds that very session on the same contract. None otherwise -- a stamp, never a guess."""
    days = {os.path.basename(p)[4:14] for p in squeeze_score._paths(index)}
    days |= {os.path.basename(p)[len(f"chain_{index}_"):][:10]
             for p in glob.glob(os.path.join(str(chain_live.CHAIN_DIR), f"chain_{index}_*.jsonl*"))}
    before = sorted(d for d in days if d < day)
    s = session(index, before[-1]) if before else None
    if s is None or (expiry and s["expiry"] and s["expiry"] != expiry):
        return None
    bs = [b for b in s["ones"] if b["t"] < "15:30"]
    return {"day": before[-1], "h": max(b["h"] for b in bs), "l": min(b["l"] for b in bs)} if bs else None


def inputs(index, day, expiry=None, lg=None):
    """Everything a row needs for (index, day), from the recorders' files. `lg` is `logged()` when the caller has it."""
    snaps = [s for s in _rows(_chain_path(index, day))]
    ux = tape_log._read(tape_log.ux_path(day, index))
    tick = next((r.get("tick") for r in ux if r.get("tick")), None)       # the tick that day's ux ladder used
    exp = {}

    def tap(rows):
        for r in rows:
            exp.setdefault("e", r.get("expiry"))
            yield r
    book = C.book_flow(tap(book_log.read_rows(day, index)), tick)
    nifty = index == "NIFTY"
    marks = None
    if nifty:
        marks = list(tape_log.read_marks(day, index)) + [
            r["event"] for r in _rows(decoder_log.path(day))
            if r.get("row") == "event" and r.get("idx") == index and isinstance(r.get("event"), dict)]
    return {"chain": C.chain_grid(snaps, chain_backfill.read_grid(day, index)), "book": book,
            "gc": tape_log.read_bars(day, index) if nifty else None, "marks": marks,
            "read": [r for r in _rows(os.path.join(READ_DIR, f"read_{day}.jsonl")) if r.get("idx") == index],
            "prior": prior(index, day, expiry or exp.get("e")),
            "n_snaps": len(snaps), "n_minutes": len(book[1]), "logged": logged() if lg is None else lg}


def build(index, day, setup, bars, inp):
    """One row, the same for the forward log and the one-shot."""
    lg = inp["logged"].get((day, index, setup["t"], setup["side"])) or {}
    r = C.row(setup, bars, inp["chain"], inp["book"], inp["gc"],
              stamp_in={"ctx": lg.get("ctx"), "gate": lg.get("gate"), "read": inp["read"],
                        "marks": inp["marks"], "prior": inp["prior"]})
    return {"day": day, "index": index, "setup": "FADE", **r}


def _load(path):
    global _seen
    _seen = {_key(r) for r in _rows(path)}


def log_new(index, payload, path=PATH, now=None):
    """Append the row of every zone entry whose window has closed and is not on disk. Returns rows written."""
    global _seen
    try:
        if isinstance(payload, (bytes, str)):
            payload = json.loads(payload)
        day_js = (payload.get("days") or [None])[-1]
        if not day_js or payload.get("interval") != band_rotation.SCORED_INTERVAL:
            return 0
        lbl = str(day_js.get("day") or "")
        if lbl and not lbl.startswith(time.strftime("%b %d")):       # another session's payload (trigger_log's rule)
            return 0
        bars = day_js.get("bars") or []
        nowm = band_rotation._minute(now or time.strftime("%H:%M"))
        closed = bars if nowm >= CLOSE else bars[:-1]                  # the last bar is FORMING until the close
        day = time.strftime("%Y-%m-%d")
        with _lock:
            if _seen is None:
                _load(path)
            due = []
            for s in C.setups(closed):
                jl = min(s["i"] + C.WINDOW_BARS, len(closed) - 1)
                if s["i"] + C.WINDOW_BARS > jl and nowm < CLOSE:
                    continue                                           # the window is still open
                end = C.close_of(C.flat(closed[jl]).get("t"))
                if end is not None and nowm >= end + GRACE and (day, index, s["t"], s["side"]) not in _seen:
                    due.append(s)
            if not due:
                return 0
            inp = inputs(index, day)
            out = [dict(build(index, day, s, closed, inp), at=time.time()) for s in due]
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write("".join(json.dumps(r) + "\n" for r in out))
            _seen.update(_key(r) for r in out)
            return len(out)
    except Exception:
        return 0


# ---- §1j RIDE ------------------------------------------------------------------------------------------------------

_ride_slot = {}             # index -> the throttle slot last checked: at most one check per 3-min bar per index


def _server():
    """server.py's module, never imported twice: in the live process server.py is __main__, and a second import would
    re-run its module body (which re-points feed_health.LOG, undoing a --mock-chain isolation). Tools import it."""
    m = sys.modules.get("server")
    if m is None:
        main = sys.modules.get("__main__")
        m = main if hasattr(main, "_read_gc_pre") else importlib.import_module("server")
    return m


def _v2(D, idx, day, now):
    """server._v2_parts up to compose, for one index at `now` (sec of day; None = the recorded day's end) ->
    (X, timeline). Call under v2feed's lock."""
    import frame_v2
    import v2feed
    srv = _server()
    s = D.idx[idx]
    lot = v2feed.LOTS.get(idx) or 1
    X = frame_v2.cut(read.from_v2(s, lot, srv._read_gc_pre(idx, day, s, lot)), now)
    return X, read.timeline(X, srv._closed_by(srv._ux_bars(idx, day), now), None, now)


def _basis_at(X, rows, day, dte_, e):
    """frame_v2.compose's basis band as the frame computed it at `e` (sec of day): read.card's spot there (the chain
    row at or before e) and its basis (the last READ row's), the carry band, the options' witness (parity_basis at e).
    None before the first READ row (compose: no card). On the day's arrays this reads nothing after e."""
    import frame_v2
    rk = ride._upto(rows, e)
    if not rk:
        return None
    return frame_v2.basis_band(X["spot"][read._at(X, e) or 0], rk[-1].get("basis"), dte_,
                               frame_v2.parity_basis(X, e, day))


def ride_inputs(index, day, now=None, light=False):
    """Everything a RIDE row needs for (index, day) at `now` (sec of day; None = the day's end), from the recorders'
    files: the closed 3-min and 1-min futures bars, the READ rows and the frame's basis band at each bar close (`basis`,
    a function of the close: ride.entries reads each bar with the band the frame had then), DTE to the options expiry
    -- all from v2feed's warm Day (the one the face reads, refreshed by its byte offsets) -- and, unless `light` (the
    live log's per-bar check, which needs only those to find the §E entries), FADE's chain / book / GC and the peers'
    READ rows."""
    import frame_v2
    import v2feed

    def go(D):
        X, tl = _v2(D, index, day, now)
        b3 = frame_v2.bars3(X["bars"], X["lot"], now)
        dte_ = frame_v2.dte(day, D.idx[index].fut_expiry)
        bz = {b["e"]: _basis_at(X, tl["rows"], day, dte_, b["e"]) for b in b3}     # computed here, under the lock
        out = {"b3": b3, "ones": frame_v2.bars3(X["bars"], X["lot"], now, width=60),
               "rows": tl["rows"], "basis": bz.get, "dte": frame_v2.dte(day, D.idx[index].expiry),
               "chain": None, "book": None, "gc": None, "peers_rows": None}
        if not light:
            out["peers_rows"] = {i: _v2(D, i, day, now)[1]["rows"] for i in v2feed.IDXS if i != index}
        return out
    out = v2feed.with_day(day, go)
    if not light:
        f = inputs(index, day, lg={})            # the chain grid, the sided book and GoCharting: §1i's own loader
        out.update(chain=f["chain"], book=f["book"], gc=f["gc"])
    return out


def build_ride(index, day, ent, inp):
    """One RIDE row, the same for the forward log and the scorer: ride.row, plus the peers' READ words at the §E bar
    (and how many read the same TREND / LEAN direction: the sync count) and which pullback of the leg this is (the
    1-based count of §E entries of the same direction under the same READ `since`)."""
    b3, rows = inp["b3"], inp["rows"]
    ents = inp.get("entries")
    if ents is None:
        ents = ride.entries(b3, rows, inp["basis"])
    e = b3[ent["i"]]["e"]

    def since(x):
        rk = ride._upto(rows, b3[x["i"]]["e"])
        return rk[-1].get("since") if rk else None
    n = sum(1 for x in ents if x["i"] <= ent["i"] and x["d"] == ent["d"] and since(x) == since(ent))
    words, sync = {}, 0
    for idx, prow in (inp.get("peers_rows") or {}).items():
        rk = ride._upto(prow, e)
        w = rk[-1] if rk else None
        words[idx] = None if w is None else f"{w.get('word')} {read.ARROW.get(w.get('dir'), '')}".strip()
        sync += bool(w and w.get("word") in ("TREND", "LEAN") and w.get("dir") == ent["d"])
    peers = {"words": words, "sync": sync} if inp.get("peers_rows") is not None else None
    r = ride.row(ent, b3, rows, inp["chain"], inp["book"], inp["gc"], peers=peers, dte=inp.get("dte"),
                 pullback_no=n or None)
    return {"day": day, "index": index, **r}


def _ride_due(ent, b3, nowm):
    """The §E entry's window (its bar + 3 bars) has closed and the grace minute passed, or the session is over."""
    if nowm >= CLOSE:
        return True
    jl = min(ent["i"] + ride.WINDOW_BARS, len(b3) - 1)
    if ent["i"] + ride.WINDOW_BARS > jl:
        return False                             # the window is still open
    return nowm >= b3[jl]["e"] // 60 + GRACE


def log_ride(index, now=None, path=PATH):
    """§1j's forward log: append the RIDE row of every §E ENTRY whose window has closed and is not on disk. At most one
    check per 3-min bar per index, at the bar's first cycle after its grace minute (a check that fails is retried at
    the next bar, never in a loop). The heavy inputs are read only when a row is due. Fail-soft: returns rows written,
    0 on any error."""
    global _seen
    try:
        nowm = band_rotation._minute(now or time.strftime("%H:%M"))
        slot = (nowm - GRACE) // C.INTERVAL
        if _ride_slot.get(index) == slot:
            return 0
        _ride_slot[index] = slot                 # used even if this check fails: the next bar retries, never a loop
        day = time.strftime("%Y-%m-%d")
        lt = time.localtime()
        now_s = nowm * 60 if now else lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec
        inp = ride_inputs(index, day, now_s, light=True)
        ents = ride.entries(inp["b3"], inp["rows"], inp["basis"])
        n = 0
        with _lock:
            if _seen is None:
                _load(path)
            due = [e for e in ents if ("RIDE", day, index, e["t"]) not in _seen and _ride_due(e, inp["b3"], nowm)]
            if due:
                full = dict(ride_inputs(index, day, now_s), entries=ents)
                # the heavy load rebuilt the bars ~1 s later: a row is built only on the very bar the check found
                out = [dict(build_ride(index, day, e, full), at=time.time()) for e in due
                       if e["i"] < len(full["b3"]) and full["b3"][e["i"]]["e"] == ride.frame_v2._sec(e["t"])]
                if out:
                    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                    with open(path, "a", encoding="utf-8") as f:
                        f.write("".join(json.dumps(r) + "\n" for r in out))
                    _seen.update(_key(r) for r in out)
                n = len(out)
        return n
    except Exception:
        return 0


# ---- §1m HOLD v2: the push bars and their references (hold2.py) ---------------------------------------------------------

def _tape_rows(prefix, day):
    """One tape-dir record's rows for a day (plain or .gz; rank_build's reader), [] when absent."""
    return _server()._rank_mod()._rows(os.path.join(tape_log.DIR, f"{prefix}{day}.jsonl"))


def push_bars(index, day, gc_rows=None, ux_rows=None):
    """The day's closed 5-min push bars for hold2.pushes, each tagged with its source: NIFTY GoCharting's (tape_) with
    the Upstox (ux_) bar of the same slot only where GoCharting lacks one; BANKNIFTY / SENSEX Upstox's. `gc_rows` /
    `ux_rows` are the records' rows when the caller holds them in memory (the live server), else the files are read."""
    ux = rank.bars_of(_tape_rows(f"ux_{index}_", day) if ux_rows is None else ux_rows, 5)
    gc = None
    if index == "NIFTY":
        gc = rank.bars_of(_tape_rows(f"tape_{index}_", day) if gc_rows is None else gc_rows, 5)
    return hold2.source_bars(gc, ux)


def push_refs(index, day):
    """HOLD v2's push tables for (index, day): ({src: rank_build.flow_ref table}, why-inactive or None), each over that
    source's own record strictly BEFORE `day`. NIFTY: "gc" (rank_build.gc_bars, exactly the table the extension ranks
    with -- equal to that day's rank_ref `flow` section) and "ux" (rank.bars_of on the ux_ record) for the bars
    GoCharting lacks; BANKNIFTY: "ux". SENSEX: none -- its 5-min bars are not rankable (rank.BAR_MIN 15, FLOW-STATE §5),
    so its push trail is inactive and says so."""
    if rank.BAR_MIN.get(index, 5) != 5:
        return {}, (f"{hold2.NO_REF} — {index} 5-min bars are not rankable (its reference is "
                    f"{rank.BAR_MIN[index]}-min bars, FLOW-STATE §5)")
    rb = _server()._rank_mod()
    data = os.path.dirname(tape_log.DIR) or "."
    out = {}
    for src, prefix in (("gc", f"tape_{index}_"), ("ux", f"ux_{index}_")):
        if src == "gc" and index != "NIFTY":
            continue
        ds = rb._days(data, "tape", prefix, day)
        bars = {d: (rb.gc_bars(data, index, d) if src == "gc" else rank.bars_of(_tape_rows(prefix, d), 5)) for d in ds}
        F = rb.flow_ref({d: b for d, b in bars.items() if b})
        if F.get("size") and F.get("slot_absd"):
            out[src] = F
    return out, None if out else f"{hold2.NO_REF} — no {index} reference day before {day}"


# ---- §1n FADE-D: the deceleration fade at an extreme (faded.py) --------------------------------------------------------

_faded_slot = {}            # index -> the throttle slot last checked: at most one check per 5-min bar per index


def zone_rows(index, day, path=None):
    """trigger_log's zone ARM and ENTRY rows for (index, day), oldest first, one per (t, side, kind), each cut to
    `LOGGED` -- no outcome field reaches FADE-D."""
    out = {}
    for r in _rows(path or trigger_log.PATH):
        if (r.get("rule") == "zone" and r.get("kind") in (None, "arm") and r.get("day") == day
                and r.get("index") == index and isinstance(r.get("t"), str)):
            out.setdefault((r["t"], r.get("side"), r.get("kind")), {k: r[k] for k in LOGGED if k in r})
    return [out[k] for k in sorted(out, key=lambda k: (k[0], k[1] or "", k[2] or ""))]


def faded_inputs(index, day, now=None, lead=True):
    """FADE-D's inputs for (index, day) cut at `now` (sec of day; None = the whole day): the closed 5-min push / flow bars
    (push_bars), the zone rows whose 3-min bar had closed (zone_rows) and, unless lead=False, the PE lead at every 5-min
    close from 09:20 (faded.leads on v2feed's warm Day: read.py's own arrays, the nine strikes and aaj likha)."""
    bars5 = [b for b in push_bars(index, day) if now is None or b["s"] + 300 <= now]
    zone = [z for z in zone_rows(index, day)
            if now is None or (band_rotation._minute(z["t"]) is not None and (band_rotation._minute(z["t"]) + 3) * 60 <= now)]
    out = {"bars5": bars5, "zone": zone, "lead": None, "why": faded.opened(bars5)}
    if lead:
        import v2feed
        last = min(faded.CUTOFF + 30, (now if now is not None else 86400) // 60)
        closes = list(range(faded.OPEN_M + faded.BAR, last + 1, faded.BAR))
        out["lead"] = v2feed.with_day(day, lambda D: faded.leads(read.from_v2(D.idx[index]), closes))
    return out


def build_faded(index, day, ep, inp):
    """One FADE-D row, the same for the forward log and the scorer."""
    return {"day": day, "index": index, **faded.row(ep, inp["bars5"], inp["lead"]), "why": inp.get("why")}


def log_faded(index, now=None, path=PATH):
    """§1n's forward log: append the row of every location episode whose 30-min window has closed (and the grace minute
    passed, or the session is over) and is not on disk. At most one check per 5-min bar per index (a check that fails is
    retried at the next bar, never in a loop); the lead is read only when a row is due. Fail-soft: returns rows written,
    0 on any error."""
    global _seen
    try:
        nowm = band_rotation._minute(now or time.strftime("%H:%M"))
        slot = (nowm - GRACE) // faded.BAR
        if _faded_slot.get(index) == slot:
            return 0
        _faded_slot[index] = slot                # used even if this check fails: the next bar retries, never a loop
        day = time.strftime("%Y-%m-%d")
        lt = time.localtime()
        now_s = nowm * 60 if now else lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec
        inp = faded_inputs(index, day, now_s, lead=False)
        eps = faded.episodes(inp["bars5"], inp["zone"])
        with _lock:
            if _seen is None:
                _load(path)
            due = [e for e in eps if ("FADE-D", day, index, e["side"], e["t"]) not in _seen
                   and (nowm >= CLOSE or nowm >= e["end"] + GRACE)]
            if not due:
                return 0
            inp = faded_inputs(index, day, now_s)
            out = [dict(build_faded(index, day, e, inp), at=time.time()) for e in due]
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write("".join(json.dumps(r) + "\n" for r in out))
            _seen.update(_key(r) for r in out)
            return len(out)
    except Exception:
        return 0
