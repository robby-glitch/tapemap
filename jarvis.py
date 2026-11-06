"""jarvis.py -- J2, THE JARVIS BRAIN (spec docs/superpowers/specs/2026-10-28-kahani-design.md §14-§17; plan
docs/superpowers/plans/2026-10-29-j2-jarvis-brain.md; inputs and order GAPS-AND-LIVE-CHECKLIST.md §3-§5).

`build(day, idx, upto)` -> the whole Jarvis frame for one index at one minute, from the record only (no network, no
clock, nothing written). Causal: it reads minutes < upto only (a minute m is complete at m + 1); upto None = the whole
session. One brain: the face (jarvis2.html) and the evening replay (export_mockup.py) render this dict, never their own.

Task 1 MOVED export_mockup.py's body here, rules unchanged (ROUND1-ANSWERS: handshake-2 hold, partial-minute hole,
publish clock, lots from start-5, direction stamp + re-stamp, PHANSE / KHISAK / WAPSI, PALAT two forms, context (b) until
the fight ends, FUEL (a) 30-min memory). Its sources, no REST and no HTTP:
  fut bars  Dext 0.8.1's 1-minute OHLC + OI where it has the minute, else the minute built from the 1-second book; each
            minute tagged in `f_src` (dext / book)
  spot      the chain record's spot, else chain_backfill's, carried over a minute with no chain at all
  Sides     sides.read on the saved chain (the same read /api/sides serves), the previous session's scale from
            sides_log.kal_scale (one copy with the server)
Every threshold is [I]. DISPLAY ONLY: no order path, no gate, no rate.
"""
from __future__ import annotations

import bisect
import collections
import datetime
import functools
import math
import os
import threading

import chain_backfill
import chain_live
import confluence_log
import dext_log
import fold
import fronts
import handshake as H
import tailread
import thresholds
import v2feed

START = "09:15"
CHAIN_END = "15:30"   # the option chain stops at 15:30:00 BY SCHEDULE (chain_live.in_session; F&O futures trade to 15:40):
                      # a minute from it with no snapshot (15:30 itself has one only when 15:30:00 lands) is "chain ends
                      # 15:30", never a chain hole -- no CAN'T SEE, no NO TRADE, no word change from it (I2)
P5_MIN = {"NIFTY": 5, "BANKNIFTY": 15}       # the |p5| floor (spec §14 row 8); another index reads BANKNIFTY's [I]
SAID = ("TOOT", "PHANS", "TIKI")
MSG_DIR = os.path.join("data", "messages")   # the stream's record: the real shown-at of each push line
REV = "jarvis-1 (J2): the exporter's rules moved, the face's reads ported (not the engine)"
hm, mod = H.hm, H.mod


def _m(s):
    return int(s[:2]) * 60 + int(s[3:5])


def L(x):
    return None if x is None else round(x / 1e5, 1)


def _rows(path):
    """A day file's rows (its .gz once daylog has compressed it), followed incrementally (tailread); missing -> []."""
    return tailread.rows(path)


def _fut_tag(brows):
    """The book record's own contract as Dext names it (dext_parity's rule, handshake.load_flow): NSE_FO|61471 -> NSE-61471."""
    ik = next((r.get("ik") for r in brows if r.get("ik")), None)
    return f"NSE-{ik.split('|')[1]}" if isinstance(ik, str) and ik.startswith("NSE_FO|") else None


TAPE_DIR = os.path.join("data", "tape")


def tape_path(day, idx):
    return os.path.join(TAPE_DIR, f"fut1m_{idx}_{day}.json")


def save_tape(idx, session, now_ms=None):
    """P0 (30 Oct, JARVIS-DAY review): the server's 1-minute futures tape (live.build_session re-fetches the whole session
    from Upstox REST every cycle, so a reconnect brings every minute back) saved per day as {"HH:MM": [o, h, l, c, v, oi,
    seen_ms]}. `seen_ms` is the FIRST time a bar was saved and never moves: a replay at minute m uses only the bars live
    Jarvis had by then, so an outage stays blind in the replay too. 30 Oct lost 78 minutes for good without this. Atomic
    replace; the caller is fail-soft."""
    import json
    import time
    day_ = (session or {}).get("day") or {}
    day, bars = day_.get("date"), day_.get("bars") or []
    if not day or not bars:
        return 0
    now_ms = now_ms or int(time.time() * 1000)
    path = tape_path(day, idx)
    try:
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = {}
    out = {}
    for b in bars:
        f_ = b.get("fut") or {}
        if b.get("t") and f_.get("c") is not None:
            seen = (old.get(b["t"]) or [None] * 7)[6] or now_ms
            out[b["t"]] = [f_.get("o"), f_.get("h"), f_.get("l"), f_.get("c"), f_.get("v") or 0, f_.get("oi") or 0, seen]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    os.replace(tmp, path)
    return len(out)


def _tape_bars(day, idx, upto, fill=False):
    """The saved tape's bars known by minute `upto` (first seen at or before it), minutes < upto -> {"HH:MM": bar}.
    fill=True (her backtest replay, 31 Oct): every saved bar regardless of when it was first seen -- the day with its holes
    filled, which live Jarvis did NOT have; the frame's health says so."""
    import json
    try:
        with open(tape_path(day, idx), encoding="utf-8") as f:
            tape = json.load(f)
    except (OSError, ValueError):
        return {}
    return {k: b for k, b in tape.items() if _m(k) < upto and b[6] and (fill or mod(b[6]) <= upto)}


def _fut_bars(tag, day, brows, upto, idx=None, fill=False, bars=None):
    """({"HH:MM": [iso, o, h, l, c, v, oi]}, {"HH:MM": "dext" | "book" | "tape"}) for the minutes < upto.
    Dext 0.8.1's getData rows where it has the minute -- a row is a 1-minute bar only when another row sits 60 s from it
    (29 Oct's file holds 5-minute bars, which are not minutes) -- else the minute from the 1-second book: ltp open / high
    / low / close, the vtt volume traded in it, its last OI -- else (P0, 30 Oct) the server's saved Upstox tape for a minute
    the book never saw, once that bar had reached the tape. A minute in none is absent (never a zero). `bars`: the book's
    minute bars already folded (_book), else folded here from `brows`."""
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    F, src = {}, {}
    rows = dext_log.read_ohlc(tag, day) if tag else []
    ts = {r["t"] for r in rows}
    for r in rows:
        d = datetime.datetime.fromtimestamp(r["t"], ist)
        if d.strftime("%Y-%m-%d") == day and r["t"] % 60 == 0 and (r["t"] - 60 in ts or r["t"] + 60 in ts) \
                and mod(r["t"] * 1000) < upto:
            F[d.strftime("%H:%M")] = [d.isoformat(), r["o"], r["h"], r["l"], r["c"], r.get("v") or 0, r.get("oi") or 0]
            src[d.strftime("%H:%M")] = "dext"
    if bars is None:                                  # time order, < upto (the caller cut them)
        bars = _book_fold(_book_new(), brows, 1)["bars"]
    for k, b in bars.items():
        if k not in F and b[6]:
            F[k], src[k] = b, "book"
    for k, b in (_tape_bars(day, idx, upto, fill) if idx else {}).items():
        if k not in F and b[5]:
            F[k], src[k] = [None, b[0], b[1], b[2], b[3], b[4], b[5]], "tape"
    return F, src


def _book_new():
    return {"n": 0, "first": None, "last": None, "upto": None, "ik": None, "m0": None, "prev": None, "pt": None,
            "bars": {}, "oi": {}, "px": {}, "sec": {}, "holes": []}


def _book_fold(b, rows, lot):
    """Fold 1-second book rows (time order, minutes < upto) into the state `b`: _fut_bars' minute bars (ltp open / high /
    low / close, the vtt traded in it, its last OI) and the oim read's book side (OI in lots, last LTP and second per
    minute, the > 60 s holes), the first `ik` (_fut_tag's) and the first minute (live_from). One pass, build's own rules."""
    for r in rows:
        t, p = r["t"], r.get("ltp")
        m = mod(t)
        if b["m0"] is None:
            b["m0"] = m
        if b["ik"] is None and r.get("ik"):
            b["ik"] = r["ik"]
        if p is not None:
            k = hm(m)
            x = b["bars"].get(k)
            if x is None:
                x = b["bars"][k] = [None, p, p, p, p, 0, 0]
            x[2], x[3], x[4] = max(x[2], p), min(x[3], p), p
            q = b["prev"]
            if q is not None and (r.get("vtt") or 0) > (q.get("vtt") or 0):
                x[5] += r["vtt"] - q["vtt"]
            if r.get("oi"):
                x[6] = r["oi"]
            b["prev"] = r
            b["px"][m] = p
        if r.get("oi"):
            b["oi"][m] = r["oi"] / lot
        b["sec"][m] = int(t / 1000) % 60
        pt = b["pt"]
        if pt is not None and t - pt > 60_000:
            b["holes"].append([hm(mod(pt)) + f":{int(pt / 1000) % 60:02d}", hm(m) + f":{int(t / 1000) % 60:02d}", mod(pt), m])
        b["pt"] = t
    return b


def _book(memo, rows, upto, lot, redo):
    """The book's fold for the minutes < upto (H.book_rows' rows). Task 6: the record's rows are in time order, so those
    minutes are a run of rows from the first; the memo keeps the fold after its n rows and folds only the new ones --
    while its first row is still tailread's own object (a re-read from the start makes every row new) and its last is the
    same row, upto did not go back, and no row after the run is < upto. Else this build folds the sorted rows cold, as
    build always did; a re-read from the start is said in `redo`."""
    b = memo.get("book")
    if b is not None and b["n"] and (len(rows) < b["n"] or rows[0] is not b["first"]
                                     or not (rows[b["n"] - 1] is b["last"] or rows[b["n"] - 1] == b["last"])):
        if upto >= b["upto"] and _changed(rows, b):   # (a reader's re-parse of the same rows is not news)
            redo.append((None, "the 1-second book (it shrank or was rewritten)"))
        memo.pop("book")
        b = None
    if b is None:
        b = _book_new()
    elif upto < b["upto"]:                           # an earlier upto: cold, and the memo's fold left for the next
        return _book_fold(_book_new(), sorted((r for r in rows if mod(r["t"]) < upto), key=lambda r: r["t"]), lot)
    j, t0 = b["n"], b["pt"]
    while j < len(rows) and mod(rows[j]["t"]) < upto and (t0 is None or rows[j]["t"] >= t0):
        t0 = rows[j]["t"]
        j += 1
    if any(mod(r["t"]) < upto for r in rows[j:]):   # a row out of time order (none on the record so far): cold
        return _book_fold(_book_new(), sorted((r for r in rows if mod(r["t"]) < upto), key=lambda r: r["t"]), lot)
    _book_fold(b, rows[b["n"]:j], lot)
    b.update(n=j, first=rows[0] if j else None, last=rows[j - 1] if j else None, upto=upto)
    memo["book"] = b
    return b


def _changed(rows, f):
    """Did the rows a fold kept (n, its first and last) change under it, beyond being parsed again? Shorter, or a
    different first or last row: the file shrank or was rewritten (tailread LRU-drops and re-parses an unchanged file too,
    and daylog's .gz is the same rows: neither is news)."""
    return len(rows) < f["n"] or rows[0] != f["first"] or rows[f["n"] - 1] != f["last"]


@functools.lru_cache(maxsize=8)
def _kal(chain_dir, idx, day):
    """The previous session's Sides scale (sides_log.kal_scale, the server's one copy), once per (dir, index, day): that
    session's file no longer changes."""
    import sides_log
    return sides_log.kal_scale(chain_dir, idx, day)


def _sides(day, idx, upto, live_from, memo=None, redo=None):
    """The Sides read of the saved chain as /api/sides serves it (sides.read on ChainState.oi_flow), each closed 5-min slot
    as known at its end, minutes < upto -> [{t, c, p, word, fuel_side, uw}] (export_mockup's shape), or None (no chain).
    Task 6: sides_log.take is a fold over the file's rows in order, so the memo keeps the state after the longest run of
    rows from the first that all fold (n rows, the first and the last of them, the upto they were cut at) and folds only
    what came after; a row out of time order folds into this build's copy. The chain rows re-read from the start (they
    shrank or were rewritten: tailread's rows are new) -> the fold starts again, said in `redo`."""
    import chain_metrics
    import sides
    import sides_log
    p = confluence_log._chain_path(idx, day)
    p = p if os.path.exists(p) else p + ".gz"
    if not os.path.exists(p):
        return None
    rows, lim, memo = _rows(p), hm(upto), {} if memo is None else memo
    f = memo.get("sides")
    if f and f["n"] and (len(rows) < f["n"] or rows[0] is not f["first"]
                         or not (rows[f["n"] - 1] is f["last"] or rows[f["n"] - 1] == f["last"])):
        if redo is not None and upto >= f["upto"] and _changed(rows, f):
            redo.append((None, "the chain record (it shrank or was rewritten): Sides folded again"))
        f = None
    ahead = f is not None and upto >= f["upto"]      # an earlier upto folds on its own and leaves the memo's fold be
    if not ahead:
        f = {"n": 0, "first": None, "last": None, "minutes": {}, "opens": {}, "book": {}}
    n = f["n"]
    while n < len(rows) and (rows[n].get("ts") or "")[:5] < lim:
        sides_log.take(rows[n], f["minutes"], f["opens"], f["book"])
        n += 1
    f.update(n=n, first=rows[0] if n else None, last=rows[n - 1] if n else None, upto=upto)
    if ahead or "sides" not in memo or upto >= memo["sides"]["upto"]:
        memo["sides"] = f
    minutes, opens, book = dict(f["minutes"]), dict(f["opens"]), dict(f["book"])     # this build's own: never the memo's
    for snap in rows[n:]:                            # a row out of time order (none on the record so far): this build only
        if (snap.get("ts") or "")[:5] < lim:
            sides_log.take(snap, minutes, opens, book)
    for t, rec in _grid(memo, day, idx).items():     # the REST walk's marks, as the server's warm start reads them
        if t < lim:
            minutes.setdefault(t, rec)
    g = chain_metrics.ChainState()
    g.minutes = minutes
    slots = sides.read(g.oi_flow(interval=sides.INTERVAL), minutes, now=hm(upto), live_from=live_from, opens=opens,
                       book=book, kal=_kal(str(chain_live.CHAIN_DIR), idx, day))
    return [{"t": s.get("slot_to") or s.get("t"), "c": s.get("c_state"), "p": s.get("p_state"), "word": s.get("word"),
             "fuel_side": s.get("fuel_side"), "uw": s.get("fuel_top2_underwater")} for s in slots]


# ---- Task 6: the incremental frame (JARVIS-REVIEW-2026-10-31 §3.7, P1 #6) ----------------------------------------------
# INVARIANT: an entry only MEMOISES pure reads of the record -- fronts.read and the ladder per chain minute, the ±7 writer
# flow, the chain's ATM read, the Sides fold over the saved chain, the backfill grid -- each kept beside its exact inputs
# (the row objects tailread keeps, equal values, or the file's size and mtime) and reused only when this build's inputs
# are the same; everything else is computed every build. A warm build therefore IS the cold build at the same upto
# (test_the_incremental_frame_equals_a_cold_build), whatever upto did since. Live (today, idx, False) and a replay (a past
# day, or fill) are different keys.
_CACHE: "collections.OrderedDict[tuple, dict]" = collections.OrderedDict()    # (day, idx, fill, dirs) -> its memo
CACHE_KEEP = 4                   # ponytail: NIFTY / SENSEX / BANKNIFTY live + one replay; the least recent is dropped
_CACHE_LOCK = threading.Lock()   # around the dict only: a build takes its entry OUT, so two builds never share one


def build(day: str, idx: str = "NIFTY", upto: int | None = None, fill: bool = False) -> dict:
    """The Jarvis frame for (day, idx) as known at minute `upto` (minutes < upto; None = the whole session). fill=True: book
    holes filled from the saved tape whenever it was saved (a backtest replay, not what live Jarvis saw). The [I] numbers
    are re-read first (jarvis_thresholds.json); the heavy reads come from this (day, idx, fill)'s memo when their inputs
    are unchanged (_CACHE's invariant). A build that raises leaves no memo: the next one is cold."""
    import book_log
    import legs
    _thresholds()
    legs._thresholds()
    key = (day, idx, fill, book_log.DIR, str(chain_live.CHAIN_DIR))   # the record's dirs: fixed live, a test's own in tests
    with _CACHE_LOCK:
        memo = _CACHE.pop(key, None)
    memo = {} if memo is None else memo
    out = _build(day, idx, upto, fill, memo)
    with _CACHE_LOCK:
        _CACHE[key] = memo
        if not fill and day == _today():             # T6: a live build drops another day's entries (a server left on
            for k in [k for k in _CACHE if k[0] != day]:     # overnight kept yesterday's, and every chain snapshot in them)
                del _CACHE[k]
        while len(_CACHE) > CACHE_KEEP:
            _CACHE.popitem(last=False)
    return out


def _today():
    """Today in IST: only which cache entries a build keeps -- never what a frame reads (the frame has no clock)."""
    return datetime.datetime.now(fold.IST).strftime("%Y-%m-%d")


def _le(keys, m):
    """The largest of the sorted `keys` <= m, or None: max(x for x in keys if x <= m), in log time."""
    i = bisect.bisect_right(keys, m)
    return keys[i - 1] if i else None


def _grid(memo, day, idx):
    """chain_backfill.read_grid(day, idx), parsed once per file state (a refill appends to it; tailread's same-size
    rewrite edge): the memo keeps ((size, mtime_ns), grid), the grid shared read-only."""
    p = chain_backfill.path(day, idx)
    try:
        st = os.stat(p)
    except OSError:
        return {}
    g = memo.setdefault("grid", {})
    if p not in g or g[p][0] != (st.st_size, st.st_mtime_ns):
        g[p] = ((st.st_size, st.st_mtime_ns), chain_backfill.read_grid(day, idx))
    return g[p][1]


def _build(day, idx, upto, fill, memo):
    import trigger_log
    upto = H.LAST_M + 2 if upto is None else upto
    redo = []                                        # the memo's own news: (from HH:MM or None = the file's start, what)
    LOT, BAR = v2feed.LOTS[idx], H.FUT_LOTS[idx]
    P5 = P5_MIN.get(idx, P5_MIN["BANKNIFTY"])

    # ---- the book (causal), the fut bars, the spot -----------------------------------------------------------------------
    bk = _book(memo, H.book_rows(day, idx), upto, LOT, redo)    # Task 6: the book's fold, carried (its rows < upto)
    tag = _fut_tag([{"ik": bk["ik"]}])
    F, f_src = _fut_bars(tag, day, [], upto, idx, fill, bars=bk["bars"])
    S = {}
    cp = confluence_log._chain_path(idx, day)
    for r in _rows(cp):                              # the index from the chain's own spot (recorded, else the backfill's)
        if r.get("spot") and START <= (r.get("ts") or "")[:5] <= "15:30" and _m(r["ts"]) < upto:
            S[r["ts"][:5]] = [None, r["spot"], r["spot"], r["spot"], r["spot"], 0, 0]
    bf = {ts: rec for ts, rec in _grid(memo, day, idx).items() if _m(ts) < upto}
    for ts, rec in bf.items():
        if ts not in S and rec.get("spot"):
            S[ts] = [None, rec["spot"], rec["spot"], rec["spot"], rec["spot"], 0, 0]
    for mm in F:                                     # a minute with no chain at all (12:55-12:59) carries the last spot seen
        if mm not in S:
            prev = max((k for k in S if k < mm), default=None)
            if prev:
                S[mm] = S[prev]
    mins = [m for m in sorted(F) if START <= m and _m(m) < upto and m in S]
    if not mins:
        return {"ok": False, "day": day, "idx": idx, "upto": hm(upto),
                "why": "could not check — no futures minute and spot on the record before " + hm(upto)}
    MI = [_m(m) for m in mins]
    ks0 = H._ks(next(iter(r for r in _rows(cp) if r.get("strikes")), None))
    STEP = H._step(ks0) or 50
    sp = [S[m][4] for m in mins]
    STRIKES = list(range(int(round(min(sp) / STEP) * STEP - STEP), int(round(max(sp) / STEP) * STEP + STEP) + 1, STEP))

    # ---- the book: oim (lots), last LTP, holes, partial minutes ----------------------------------------------------------
    book_oi, book_px, last_sec, holes = bk["oi"], bk["px"], bk["sec"], bk["holes"]    # _book_fold's; read only here

    def hole_minute(m):
        """Finding 5: a minute whose last book row comes before :50 s, or that sits inside a > 60 s gap, is a hole."""
        if m not in book_oi or last_sec.get(m, 0) < 50:
            return True
        return any(a < m <= b for _, _, a, b in holes)

    oim, px, src = {}, {}, {}
    for mm, m in zip(mins, MI):
        if not hole_minute(m):
            oim[m], px[m], src[m] = book_oi[m], book_px.get(m, F[mm][4]), "book"
        else:
            oim[m], px[m], src[m] = F[mm][6] / LOT, F[mm][4], "rest"   # the bar's own OI (Dext / book: f_src says which)
    for mm, c in F.items():                          # the run rule needs the 5 minutes before START too
        m = _m(mm)
        if MI[0] - 6 <= m < MI[0]:
            oim[m], px[m], src[m] = (book_oi[m], book_px.get(m, c[4]), "book") if not hole_minute(m) else (c[6] / LOT, c[4], "rest")

    # ---- RASAD: the RUN rule as amended ---------------------------------------------------------------------------------
    def p5sign(m):
        if m - 5 not in px or m not in px:
            return "?"
        d = px[m] - px[m - 5]
        return "▲" if d >= P5 else "▼" if d <= -P5 else "?"

    def meaning(kind, d):
        return {("COVER", "▲"): "shorts cover", ("COVER", "▼"): "longs nikal rahe", ("FRESH", "▲"): "naye long",
                ("FRESH", "▼"): "naye short"}.get((kind, d), "disha ?")

    runs, run, last_ext_m, fuel = [], None, None, {}
    for m in sorted(oim):
        if m - 5 not in oim or m - 5 < H.FIRST_M + 1:
            fuel[m] = {"state": "?", "why": "5-min window mein hole"}
            continue
        w = oim[m] - oim[m - 5]
        if run is None:
            if abs(w) >= BAR:
                base = m - 5 if last_ext_m is None or m - 5 >= last_ext_m else last_ext_m
                d = p5sign(m)
                run = {"kind": "COVER" if w < 0 else "FRESH", "sgn": -1 if w < 0 else 1, "start": m, "base": base,
                       "ext": oim[m], "ext_m": m, "pub": 0, "dir": d, "dirs": [(m, d)], "opp": 0, "khatam": None}
                runs.append(run)
            fuel[m] = {"state": "LIVE", "run": len(runs) - 1} if run else {"state": "-"}
            continue
        if run["sgn"] * (oim[m] - run["ext"]) > 0:
            run["ext"], run["ext_m"], run["pub"] = oim[m], m, 0
        elif oim[m] != oim.get(m - 1):                              # finding 6: an unchanged minute is no publish
            run["pub"] += 1
        d = p5sign(m)
        if d != "?" and d != run["dir"]:
            run["opp"] += 1
            if run["opp"] >= 3:
                run["dir"], run["opp"] = d, 0
                run["dirs"].append((m, d))
        else:
            run["opp"] = 0
        if run["pub"] >= 3:
            run["khatam"] = m
            last_ext_m = run["ext_m"]
            fuel[m] = {"state": "KHATAM", "run": len(runs) - 1}
            run = None
        else:
            fuel[m] = {"state": "LIVE", "run": len(runs) - 1}
    for r in runs:
        r["lots"] = round(r["ext"] - oim[r["base"]])
        r["meaning"] = meaning(r["kind"], r["dir"])
        r["fuel_dir"] = r["dir"]
    RUNS = [{"kind": r["kind"], "start": hm(r["start"]), "base": hm(r["base"]), "last_ext": hm(r["ext_m"]),
             "khatam": None if r["khatam"] is None else hm(r["khatam"]), "lots": r["lots"], "dir": r["dir"],
             "dirs": [[hm(a), b] for a, b in r["dirs"]], "meaning": r["meaning"]} for r in runs]

    def run_at(m):
        """The run live at minute m (or just KHATAM'd at m), with lots so far."""
        for i, r in enumerate(runs):
            if r["start"] <= m <= (r["khatam"] if r["khatam"] is not None else 10 ** 6):
                so_far = round((min(oim[j] for j in oim if r["start"] <= j <= m) if r["sgn"] < 0
                                else max(oim[j] for j in oim if r["start"] <= j <= m)) - oim[r["base"]])
                d = next((b for a, b in reversed(r["dirs"]) if a <= m), r["dirs"][0][1])
                return {"i": i, "kind": r["kind"], "dir": d, "lots": so_far, "khatam": r["khatam"] == m,
                        "start": r["start"], "meaning": meaning(r["kind"], d)}
        return None

    # ---- the chain grid, the §1d fronts per minute (causal), the ladder -------------------------------------------------
    snaps = {}
    for s in _rows(cp):
        ts = (s.get("ts") or "")[:5]
        if ts and START <= ts <= "15:30" and s.get("spot") and _m(ts) < upto:
            snaps[ts] = s                                            # the last snapshot of each minute
    inp = H.load(day, idx)
    for k in ("R", "F", "src", "oim", "fm"):                         # causal: the handshake sees minutes < upto only
        inp[k] = {m: v for m, v in (inp.get(k) or {}).items() if m < upto}
    inp["ms"] = [m for m in inp["ms"] if m < upto]
    R, MS = inp["R"], inp["ms"]
    # J1b (29 Oct): the REST morning (chain_backfill) joins the walls as if we had been there -- an observed minute always
    # wins; absolute OI from handshake.with_backfill (the day's base seen live + the change); tagged src backfill.
    for ts, rec in bf.items():
        if ts not in snaps and rec.get("spot") and START <= ts <= "15:30":
            r = R.get(_m(ts)) or {}
            snaps[ts] = {"ts": ts + ":00", "spot": rec["spot"], "src": "backfill",
                         "strikes": [{"k": k, "ce": {"oi": H._leg(r, k, "ce").get("oi"), "oi_chg": c[0]},
                                      "pe": {"oi": H._leg(r, k, "pe").get("oi"), "oi_chg": c[1]}} for k, c in rec["k"].items()]}
    grid, peak, FR, ladder = {}, {}, {}, {}
    END = mins[-1]
    # Task 6: a minute's fronts and ladder row are pure reads of the snapshots up to it (grid and peak are built in time
    # order), so they are reused while every snapshot up to it is the one they were read from (tailread's own row, or an
    # equal backfill one) and the ladder's strikes are the same; from the first changed minute on, read again
    was, now_, same = memo.get("fronts") or [], [], True
    for j, ts in enumerate(sorted(snaps)):
        s = snaps[ts]
        old = was[j] if same and j < len(was) and was[j][0] == ts and (was[j][1] is s or was[j][1] == s) else None
        if same and old is None and j < len(was) - 1:              # an earlier minute changed under the memo, not the last
            redo.append((ts, "the chain minutes changed under the cache (a backfill refill or a rewritten record): "
                             "their walls"))
        same = old is not None
        grid[ts] = {"spot": s["spot"], "k": {float(r["k"]): ((r["ce"].get("oi_chg") or 0.0), (r["pe"].get("oi_chg") or 0.0))
                                            for r in s["strikes"]}}
        for r in s["strikes"]:
            for side in ("ce", "pe"):
                if isinstance(r[side].get("oi"), (int, float)):
                    peak[(float(r["k"]), side)] = max(peak.get((float(r["k"]), side), 0.0), r[side]["oi"])
        if ts < START or ts > END:
            now_.append((ts, s, None, None))
            continue
        fr = old[2] if old and old[2] is not None else (
            [{"k": f["k"], "side": f["side"], "state": f["state"], "chg": L(f["chg"]), "peak": L(f["peak"]),
              "peak_at": f["peak_at"], "slope": L(f["slope"]), "oi": L(f["oi"])} for f in fronts.read(grid, dict(peak))])
        FR[_m(ts)] = fr
        atm = int(round(s["spot"] / STEP) * STEP)                   # causal: also ATM ±LAD_NEAR of this minute (below)
        ks = sorted(set(STRIKES) | set(range(atm - LAD_NEAR * STEP, atm + LAD_NEAR * STEP + 1, STEP)))
        lad = old[3] if old and old[3] is not None and old[3][0] == ks else (
            (ks, {"spot": s["spot"],
                  "ce": {k: L(H._leg(s, k, "ce").get("oi")) for k in ks},
                  "pe": {k: L(H._leg(s, k, "pe").get("oi")) for k in ks},
                  "ce_pk": {k: L(peak.get((float(k), "ce"))) for k in ks},
                  "pe_pk": {k: L(peak.get((float(k), "pe"))) for k in ks}}))
        ladder[ts] = lad[1]
        now_.append((ts, s, fr, lad))
    memo["fronts"] = now_ + was[len(now_):] if same else now_      # an earlier upto keeps the later minutes for the next
    chain_missing = [mm for mm in mins if mm not in ladder and mm < CHAIN_END]     # from 15:30: its scheduled end
    FK = sorted(FR)

    def front_state(m, side, k):
        """The §1d state of (side, k) as of minute m, with a 3-minute hold for UNWINDING (Q17)."""
        j = _le(FK, m)
        if j is None:
            return None
        return next((f for f in FR[j] if f["side"] == side and f["k"] == k), None)

    def unwinding_held(m, side, k):
        return all((front_state(j, side, k) or {}).get("state") == "UNWINDING" for j in (m, m - 1, m - 2) if j in FR)

    # ---- pushes: the handshake rows, the hold rule, the artifact flag ----------------------------------------------------
    HS = H.read(inp, upto)
    PUSH = []
    for row, p in zip(HS, inp["pushes"]):
        m, d = p["m"], p["dir"]
        a1 = H.answer(R, MS, p, upto)
        a4 = H.answer(R, MS, p, upto, first=False)
        held, held_at = None, None
        if a1 and a1["ans"] in SAID:
            # handshake-2 already confirmed it (its "held" minute), or it was read at m+4 (final). The brain used to re-read
            # the one strike here, which turned every band answer (G1) into a false "wapas".
            held, held_at = a1["ans"], a1.get("held", a1["am"])
        artifact = any(a <= m and m - 2 <= b for _, _, a, b in holes)
        PUSH.append({"t": row["t"], "m": m, "dir": d, "lots": row["lots"], "norm": row["norm"], "src": row["src"],
                     "k": row["k"], "side": row["side"], "oi_L": row["oi_L"], "ans": row["ans"], "chg": row["chg"],
                     "bar": row["bar"], "am": row["am"], "am_m": None if a1 is None else a1["am"],
                     "ans4": None if a4 is None else a4["ans"], "chg4": None if a4 is None else a4["chg"],
                     "held": held, "held_at": None if held_at is None else hm(held_at), "held_m": held_at,
                     "who": row["who"], "behind": row["behind"], "floor_cap": row["floor_cap"], "fut": row["fut"],
                     "effort": row["effort"], "p15": row.get("p15"), "p30": row.get("p30"), "artifact": artifact,
                     "key": row["key"], "via": row.get("via")})

    shown = {}                                       # the stream's real shown-at (the lag she lived with), as of upto
    for r in _rows(os.path.join(MSG_DIR, f"msg_{day}.jsonl")):
        if r.get("kind") == "FLOW" and r.get("key") and isinstance(r.get("at"), (int, float)) \
                and datetime.datetime.fromtimestamp(r["at"]).strftime("%Y-%m-%d") == day and mod(r["at"] * 1000) < upto:
            shown[r["key"]] = datetime.datetime.fromtimestamp(r["at"]).strftime("%H:%M:%S")
    for p in PUSH:
        p["shown"] = shown.get(p["key"])

    def final_ans(p, at):
        """What the push's answer reads at minute `at` (causal): None (pending), 'TOOT?' (crossed, hold pending), the held
        word, 'wapas', 'NAHI', or '?'. G4: a TIKI whose OI BUYERS opened reads 'GHUSE' (buyers in): not a defended wall,
        so no rule that counts a TIKI as the wall holding counts it."""
        if p["artifact"]:
            return "artifact"
        if p["am_m"] is None or p["am_m"] > at - 1:
            return None
        if p["ans"] in SAID:
            w = "GHUSE" if p["ans"] == "TIKI" and p.get("who") == "KHAREEDAR" else p["ans"]
            if p["held_m"] is not None and p["held_m"] <= at - 1:
                return w if p["held"] == p["ans"] else p["held"]
            return w + "?"
        return p["ans"] if p["ans"] is not None else "?"

    # ---- KAHANI: the fight, its chapters, per minute (causal) -----------------------------------------------------------
    def wall_ahead(m, d, spot):
        j = _le(FK, m)
        if j is None:
            return None
        side = "CE" if d > 0 else "PE"
        lo, hi = (spot - STEP / 2, spot + 2 * STEP) if d > 0 else (spot - 2 * STEP, spot + STEP / 2)
        for f in FR[j]:                                              # fronts.read is ranked: rank 1 first
            if f["side"] == side and lo <= f["k"] <= hi:
                return f
        return None

    RK = sorted(R)

    def spot_at(m):
        j = _le(RK, m)
        return None if j is None else R[j]["spot"]

    fight, fights, timeline = None, [], []
    asof = {}       # causal: the fight's KHATAM and latest TOOT as known at each minute (the verdict reads these, never the
                    # fight's end-of-window state; found by test_causal_prefix, J2)
    for mm, m in zip(mins, MI):
        spot = spot_at(m)
        known = [p for p in PUSH if p["m"] < m and not p["artifact"]]
        if fight is None or (fight.get("ended") and fight["ended_m"] < m):
            d = (known[-1]["dir"] if known else None)
            if d is None:
                s0 = spot_at(m - 15)
                d = 1 if (spot or 0) >= (s0 or 0) else -1
            w = wall_ahead(m, d, spot) if spot is not None else None
            fight = {"id": len(fights), "d": d, "side": "CE" if d > 0 else "PE", "k": None if w is None else w["k"],
                     "born": mm, "dastak": [], "toot": None, "floor": None, "naya_floor": None, "khatam": None,
                     "ending": None, "ended": False, "ended_m": None, "chips": [], "stamps": []}
            fights.append(fight)
        # re-target in the DEEWAR / KHISAK stage: the fight is where the first knock lands
        if not fight["dastak"] and known and fight["toot"] is None:
            lp = known[-1]
            if lp["dir"] != fight["d"] or fight["k"] is None:
                w = wall_ahead(m, lp["dir"], spot)
                if w is not None:
                    fight.update(d=lp["dir"], side=w["side"], k=w["k"])
        # the knocks: pushes into the fight's side whose attacked strike is the wall or nearer to price
        for p in known:
            if p["dir"] == fight["d"] and p["m"] >= _m(fight["born"]) - 1 and p not in [q["p"] for q in fight["dastak"]]:
                if fight["k"] is None or p["k"] is None or (p["k"] <= fight["k"] if fight["d"] > 0 else p["k"] >= fight["k"]):
                    fight["dastak"].append({"p": p})
        # the answers as known now
        for q in fight["dastak"]:
            q["ans"] = final_ans(q["p"], m)
            if q["ans"] in ("TOOT", "PHANS") and not q.get("stamped"):
                q["stamped"] = True
                fight["toot"] = fight["toot"] or {"t": q["p"]["t"], "ans": q["ans"], "chg": q["p"]["chg"], "known": hm(m), "m": m}
                fight["latest_toot"] = q["p"]["t"]                      # NEXT / ULTA PUSH count from the LATEST toot
                fight["stamps"].append([mm, "TOOT" if q["ans"] == "TOOT" else "PHANSE", f"{q['p']['t']} {q['p']['chg']:+.1f}L"])
        wf = front_state(m, fight["side"], fight["k"]) if fight["k"] is not None else None
        wstate = None if wf is None else wf["state"]
        unw = fight["k"] is not None and unwinding_held(m, fight["side"], fight["k"])
        ru = run_at(m)
        # the opposite pushes: ulta dastak, NAYA FLOOR (flip), PALAT wall form
        opp = [p for p in known if p["dir"] == -fight["d"] and p["m"] >= _m(fight["born"]) - 1]
        for p in opp:
            a = final_ans(p, m)
            if a == "TIKI" and p.get("who") == "WRITERS" and fight["toot"] and fight["naya_floor"] is None:
                other = front_state(m, fight["side"], p["k"])          # the same strike's other side (the wall's side)
                flip = (fight["k"] == p["k"]) or (other or {}).get("state") == "UNWINDING"
                if flip:
                    fight["naya_floor"] = {"k": p["k"], "side": p["side"], "chg": p["chg"], "t": p["t"], "known": hm(m)}
                    fight["stamps"].append([mm, "NAYA FLOOR" if fight["d"] > 0 else "NAYA CAP",
                                            f"{p['k']:,.0f}s {p['side']} {p['chg']:+.1f}L (flip)"])
        # P2 (30 Oct, NOISE-DECODER §4.6): a fight price has LEFT BEHIND -- more than FIGHT_AWAY steps from its wall for
        # FIGHT_AWAY_MIN minutes -- ends; the next minute a new fight is born at the wall ahead. 29 Oct kept 22,700s PE all
        # day (315 of 361 minutes > 2 steps away); 30 Oct kept 23,000s CE with price three hours above 23,100s.
        if not fight["ending"] and fight["k"] is not None and spot is not None and abs(spot - fight["k"]) > FIGHT_AWAY * STEP:
            fight.setdefault("away_since", m)
            if m - fight["away_since"] >= FIGHT_AWAY_MIN:
                fight["ending"], fight["ended"], fight["ended_m"] = "PEECHHE CHHOOTA", True, m
                fight["stamps"].append([mm, "PEECHHE CHHOOTA",
                                        f"{fight['k']:,.0f}s {fight['side']} · price {FIGHT_AWAY}+ steps away for {FIGHT_AWAY_MIN} min"])
        else:
            fight.pop("away_since", None)
        # chapter
        if fight["ending"]:
            chap = fight["ending"]
        elif fight["toot"] is None:
            n = len(fight["dastak"])
            if any(q["ans"] in ("TOOT?", "PHANS?") for q in fight["dastak"]):
                chap = "TOOT?"
            elif n == 0:
                chap = "KHISAK" if unw else "DEEWAR"
            else:
                chap = "THAKAN" if unw else f"DASTAK ×{n}"
            if n and ru and fight["toot"] is None:
                chap += " · RASAD bina toot"
        else:
            if fight["khatam"] is None:
                if ru and ru["khatam"]:
                    fight["khatam"] = {"t": mm, "lots": ru["lots"], "kind": ru["kind"], "dir": ru["dir"]}
                    fight["stamps"].append([mm, "KHATAM", f"{ru['kind'].lower()} {ru['lots']:+,} lots"])
                    chap = "KHATAM"
                elif ru:
                    chap = f"RASAD {ru['kind'].lower()} {ru['dir']}"
                else:
                    chap = "TOOT · RASAD ?" if fight["toot"]["ans"] == "TOOT" else "PHANSE"
            else:
                chap = "KHATAM"
                kh = _m(fight["khatam"]["t"])
                after = [p for p in known if p["m"] > kh]
                if ru and ru["start"] > kh:
                    if ru["dir"] == ("▲" if fight["d"] > 0 else "▼"):
                        fight["ending"], chap = "CHAL", "CHAL"
                    elif ru["dir"] == ("▼" if fight["d"] > 0 else "▲"):
                        fight["ending"], chap = "PALAT (eendhan)", "PALAT (eendhan)"
                if not fight["ending"]:
                    opp_toot = [p for p in after if p["dir"] == -fight["d"] and final_ans(p, m) in ("TOOT", "PHANS")
                                and fight["naya_floor"] and p["k"] == fight["naya_floor"]["k"]]
                    if opp_toot:
                        fight["ending"], chap = "PALAT (deewar)", "PALAT (deewar)"
                    else:
                        ok = ("NAHI", "TIKI", "wapas")
                        up = any(p["dir"] == fight["d"] and final_ans(p, m) in ok for p in after)
                        dn = any(p["dir"] == -fight["d"] and final_ans(p, m) in ok for p in after)
                        if up and dn:
                            fight["ending"], chap = "PIN", "PIN"
                        elif not after and m - kh >= 20:
                            fight["ending"], chap = "KHAMOSH", "KHAMOSH"
                if fight["ending"]:
                    fight["ended"], fight["ended_m"] = True, m
                    fight["stamps"].append([mm, fight["ending"], ""])
        # WAPSI: the broken strike rebuilt by >= the bar after its TOOT
        if fight["toot"] and fight["k"] is not None and wf and fight["toot"]["ans"] == "TOOT":
            tq = next((q for q in fight["dastak"] if q["ans"] in ("TOOT", "PHANS")), None)
            if tq and tq["p"]["bar"] and wf["chg"] is not None:
                at_toot = front_state(_m(tq["p"]["am"]), fight["side"], fight["k"])
                if at_toot and at_toot["chg"] is not None and wf["chg"] - at_toot["chg"] >= tq["p"]["bar"] \
                        and not any(s[1] == "WAPSI" for s in fight["stamps"]):
                    fight["stamps"].append([mm, "WAPSI", f"{fight['k']:,.0f}s {fight['side']} +{wf['chg'] - at_toot['chg']:.1f}L"])
        if fight["stamps"] and not any(s[1] in ("DEEWAR", "KHISAK") for s in fight["stamps"]) and fight["k"] is not None:
            fight["stamps"].insert(0, [fight["born"], "KHISAK" if unw else "DEEWAR", f"{fight['k']:,.0f}s {fight['side']}"])
        last_chap = timeline[-1]["chapter"] if timeline else None
        if chap != last_chap and chap.split(" ·")[0].startswith(("DASTAK", "THAKAN", "TOOT?", "RASAD", "KHATAM", "DEEWAR", "KHISAK")):
            if not fight["stamps"] or fight["stamps"][-1][1] != chap.split(" ·")[0]:
                fight["stamps"].append([mm, chap.split(" ·")[0], ""])
        timeline.append({"t": mm, "fight": fight["id"], "wall": fight["k"], "side": fight["side"], "wall_state": wstate,
                         "wall_chg": None if wf is None else wf["chg"], "wall_peak": None if wf is None else wf["peak"],
                         "chapter": chap,
                         # a pending answer's attacked strike is not known yet at m (the handshake returns it with the answer)
                         "dastak": [[q["p"]["t"], q["ans"], q["p"]["lots"], q["p"]["k"] if q["ans"] is not None else None]
                                    for q in fight["dastak"]],
                         "ulta": [[p["t"], a, p["lots"], p["k"] if a is not None else None] for p, a in ((p, final_ans(p, m)) for p in opp)],
                         "fuel": None if ru is None else {k: v for k, v in ru.items() if k != "i"},
                         "fuel_state": fuel.get(m, {}).get("state"), "fuel_src": src.get(m),
                         "naya_floor": fight["naya_floor"], "khatam": fight["khatam"], "ending": fight["ending"],
                         "fronts": FR.get(_le(FK, m), [])})
        asof[mm] = (fight["khatam"], fight.get("latest_toot"))

    # ---- the band verdict per minute, both sides (SELL: defender CE, wants fuel ▼; BUY: mirror) --------------------------
    def verdict(m, tside):
        want = "▼" if tside == "SELL" else "▲"
        band_d = 1 if tside == "SELL" else -1                        # the band side's push direction (into the defender)
        dside = "CE" if tside == "SELL" else "PE"
        tl = TL.get(hm(m))                                           # timeline's minutes are unique
        if tl is None:
            return None
        ru = tl["fuel"]
        fstate = tl["fuel_state"]
        known = [p for p in PUSH if p["m"] < m and not p["artifact"]]
        f = fights[tl["fight"]]
        f_khatam, f_latest = asof[tl["t"]]
        b = f["side"] == dside and f["toot"] is not None and f["toot"]["m"] <= m and not (f["ended"] and f["ended_m"] < m)
        pieces = {}
        if fstate == "?":
            pieces["FUEL"] = ["?", "hole"]
        elif ru and not ru["khatam"]:
            pieces["FUEL"] = (["?", f"{ru['kind'].lower()} disha ?"] if ru["dir"] == "?" else
                              ["✓", f"{ru['kind'].lower()} {ru['dir']} {ru['lots']:+,}"] if ru["dir"] == want else
                              ["✗", f"{ru['kind'].lower()} {ru['dir']} {ru['lots']:+,} chal raha"])
        else:
            if b:
                pieces["FUEL"] = ["✓", "KHATAM" if f_khatam else "koi run nahi"]
            else:
                recent = [r for r in runs if r["khatam"] is not None and m - 30 <= r["khatam"] <= m and r["dir"] != "?"]
                against = [r for r in recent if r["dir"] != want]
                opp_since = any(r["khatam"] > against[-1]["khatam"] and r["dir"] == want for r in recent) if against else False
                pieces["FUEL"] = (["✗", f"run {against[-1]['dir']} {hm(against[-1]['khatam'])} tak (30 min)"]
                                  if against and not opp_since else ["✓", "koi run nahi"])
        if not b:
            w = wall_ahead(m, band_d, spot_at(m)) if spot_at(m) is not None else None
            if w is None:
                pieces["WALL"] = ["✗", "koi deewar nahi (2 step)"]
            else:
                pieces["WALL"] = (["✓", f"{w['k']:,.0f}s {w['side']} {w['state'].lower()}"] if w["state"] in ("BUILDING", "STALLED")
                                  else ["✗", f"{w['k']:,.0f}s {w['side']} unwinding {w['chg'] - w['peak']:+.1f}L"])
            last = [p for p in known if p["dir"] == band_d and p["m"] >= m - 15]
            if not last:
                pieces["DASTAK"] = ["?", "15 min mein push nahi"]
            else:
                a = final_ans(last[-1], m)
                pieces["DASTAK"] = (["✓", f"{last[-1]['t']} {a}"] if a in ("NAHI", "TIKI", "wapas") else
                                    ["✗", f"{last[-1]['t']} {a}"] if a in ("TOOT", "PHANS") else ["?", f"{last[-1]['t']} {a or 'jawab baaki'}"])
        else:
            lt = _m(f_latest or f["toot"]["t"])
            nxt = [p for p in known if p["dir"] == band_d and p["m"] > lt]
            if not nxt:
                pieces["NEXT PUSH"] = ["?", "abhi push nahi"]
            else:
                a = final_ans(nxt[0], m)
                pieces["NEXT PUSH"] = (["✓", f"{nxt[0]['t']} {a}"] if a in ("NAHI", "TIKI", "wapas") else
                                       ["✗", f"{nxt[0]['t']} {a}"] if a in ("TOOT", "PHANS") else ["?", f"{nxt[0]['t']} {a or 'jawab baaki'}"])
            ul = [p for p in known if p["dir"] == -band_d and p["m"] > lt]
            if not ul:
                pieces["ULTA PUSH"] = ["?", "abhi push nahi"]
            else:
                a = final_ans(ul[0], m)
                pieces["ULTA PUSH"] = (["✓", f"{ul[0]['t']} TOOT {ul[0]['k']:,.0f}s"] if a in ("TOOT", "PHANS") else
                                       ["✗", f"{ul[0]['t']} TIKI {ul[0]['k']:,.0f}s"] if a == "TIKI" else
                                       ["·", f"{ul[0]['t']} NAHI"] if a in ("NAHI", "wapas") else ["?", f"{ul[0]['t']} {a or 'jawab baaki'}"])
        marks = [v[0] for v in pieces.values()]
        n_ok, n_bad, N = marks.count("✓"), marks.count("✗"), marks.count("✓") + marks.count("✗")
        if pieces["FUEL"][0] == "✗" or (not b and pieces["WALL"][0] == "✗" and pieces["DASTAK"][0] == "✗") or \
                (b and pieces["NEXT PUSH"][0] == "✗"):
            word = "CHALEGA"
        elif n_ok >= 2 and n_bad == 0:
            word = "GHUMEGA"
        else:
            word = "SAAF NAHI"
        return {"ctx": "b" if b else "a", "word": word, "n": n_ok, "N": N, "q": marks.count("?"), "pieces": pieces}

    TL = {x["t"]: x for x in timeline}
    VERD = {s: {} for s in ("SELL", "BUY")}
    for mm, m in zip(mins, MI):
        for s in VERD:
            v = verdict(m, s)
            if v:
                VERD[s][mm] = v

    # ---- the zone rows (trigger_log, zone3, today) ----------------------------------------------------------------------
    ZONE = []
    import effort
    for r in _rows(trigger_log.PATH):
        if r.get("day") == day and r.get("index") == idx and r.get("rule") == "zone3" and START <= str(r.get("t", ""))[:5] \
                and _m(str(r["t"])) < upto:
            z = {k: r.get(k) for k in ("t", "kind", "side", "px", "level", "stop", "entry", "band", "u2", "d2", "bands_on",
                                       "stop_px", "gate", "at",
                                       "vwap", "u3", "d3", "bands3_why")    # vwap / u3 / d3: §6a (Task 9a)
                 if r.get(k) is not None}   # never a scored field (mfe, mae, stop_hit, bands, f15, f30, scored_at)
            if not z.get("kind") and z.get("px") is not None:   # the zone card's sign 3 at the trigger's close (effort.py;
                lam, med, nb = effort.lam_at(inp.get("fm") or {}, _m(str(r["t"])[:5]) + 2)   # SENSEX: NIFTY's flow, 1q)
                z["effort"] = ({"x": round(lam / med, 2), "why": None} if lam and med else
                               {"x": None, "why": f"the day median needs {effort.MIN_HIST} five-minute blocks (has {nb})"
                                if med is None else "no price range or volume in the last 5 min"})
            ZONE.append(z)

    data = {"ok": True, "day": day, "idx": idx, "lot": LOT, "bar": BAR, "step": STEP, "start": START, "end": END,
            "upto": hm(upto), "fill": fill, "mins": mins,
            "spot": [S[m][4] for m in mins], "fut": [F[m][4] for m in mins], "fhi": [F[m][2] for m in mins],
            "flo": [F[m][3] for m in mins], "f_src": [f_src[m] for m in mins],
            "oi": [round(oim[m], 1) for m in MI], "oi_src": [src[m] for m in MI], "vol": [round(F[m][5] / LOT) for m in mins],
            "runs": RUNS, "strikes": STRIKES, "ladder": ladder, "chain_missing": chain_missing,
            "holes": [[a, b] for a, b, _, _ in holes],
            "pushes": PUSH, "timeline": timeline, "verdict": VERD, "zone": ZONE,
            "fights": [{"id": f["id"], "k": f["k"], "side": f["side"], "born": f["born"], "stamps": f["stamps"],
                        "ending": f["ending"]} for f in fights],
            "rev": "mockup reading of ROUND1-ANSWERS rules (not the engine)", "brain": REV}
    if any(not z.get("kind") for z in ZONE):         # §6a: effort per minute for an open zone trade's WIDEN (sign 3 at
        data["eff_x"] = [(lambda a: round(a[0] / a[1], 2) if a[0] and a[1] else None)(   # minute m: effort.lam_at's
            effort.lam_at(inp.get("fm") or {}, _m(m))) for m in mins]                   # m-4..m; SENSEX: NIFTY's, §1q)
    # Her asks, 29 Oct ~01:45 (speed, candle-vs-delta at the top, absorption / exhaustion, her VWAP bands to trail, all 3 in
    # sync): the true 1-min open, Dext 0.8.1's footprint delta and volume per minute (lots), the session VWAP (hlc3) and its
    # SD from the 1-min bars (matches her zone's logged u2 within ~1 pt), and BANKNIFTY / SENSEX spot (chain + backfill, carried).
    data["fo"] = [F[m][1] for m in mins]
    data["delta"], data["fvol"] = _footprint(tag, day, mins, LOT)
    sv = spv = 0.0
    xs, data["vwap"], data["sd"] = [], [], []
    for m in mins:
        p, v = (F[m][2] + F[m][3] + F[m][4]) / 3, F[m][5] or 0
        sv, spv = sv + v, spv + p * v
        xs.append((p, v))
        w = spv / sv if sv else p
        data["vwap"].append(round(w, 1))
        data["sd"].append(round(math.sqrt(sum(v * (q - w) ** 2 for q, v in xs) / sv), 1) if sv else 0.0)

    def other_spot(i):
        got = {}
        for r in _rows(confluence_log._chain_path(i, day)):
            if r.get("spot") and START <= (r.get("ts") or "")[:5] <= "15:30":
                got[r["ts"][:5]] = r["spot"]
        for ts, rec in _grid(memo, day, i).items():
            if ts not in got and rec.get("spot"):
                got[ts] = rec["spot"]
        out, last = [], None
        for m in mins:
            last = got.get(m, last)
            out.append(last)
        return out

    data["bnf"], data["sx"] = other_spot("BANKNIFTY"), other_spot("SENSEX")
    data["nf"] = other_spot("NIFTY")                 # NIFTY's spot on every frame: the card's sync sign and ALL 3's N slot
    data["live_from"] = hm(bk["m0"]) if bk["m0"] is not None else None
    # Her catch, 29 Oct 10:45: the Board's Sides read (sides.py, /api/sides) is the options-side fuel; each 5-min slot as
    # known at its end. Her ask, 29 Oct 11:00: WRITER FLOW ±7 -- the 3-min OI change summed over ATM ±7 strikes, per side
    # (L), per minute.

    wfm, wfn = memo.get("wflow") or {}, {}         # Task 6: (minute, side) -> (its two snapshots, STEP, the value)

    def wflow(m, side, w=7):
        a, b = snaps.get(m), snaps.get(hm(_m(m) - 3))
        if not a or not b or not a.get("spot"):
            return None
        hit = wfm.get((m, side))
        if hit and hit[0] is a and hit[1] is b and hit[2] == STEP:
            wfn[(m, side)] = hit
            return hit[3]
        atm = round(a["spot"] / STEP) * STEP
        tot, n = 0.0, 0
        for k in range(int(atm - w * STEP), int(atm + w * STEP) + 1, STEP):
            x, y = H._leg(a, k, side).get("oi"), H._leg(b, k, side).get("oi")
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                tot, n = tot + (x - y), n + 1
        v = round(tot / 1e5, 1) if n >= 2 * w else None
        wfn[(m, side)] = (a, b, STEP, v)
        return v

    data["wf_ce"], data["wf_pe"] = [wflow(m, "ce") for m in mins], [wflow(m, "pe") for m in mins]
    memo["wflow"] = wfm | wfn                        # an earlier upto keeps the later minutes for the next
    data["sides"] = _sides(day, idx, upto, data["live_from"], memo, redo)
    for s in data["sides"] or ():
        s["fuel"] = sides_fuel(s)                    # the face draws the brain's fuel slots, never its own rule
    # the flow the reads use: Dext's footprint delta, else the book's own (handshake.book_flow, src B) -- a minute in
    # neither stays None (Dext missing AND the book blind), never a zero
    data["flow"] = _frame_flow(data["delta"], MI, inp)
    data["flow_src"] = ["D" if x is not None else ("B" if y is not None else None) for x, y in zip(data["delta"], data["flow"])]
    import sensex_flow
    if sensex_flow.on(idx) and all(x is None for x in data["delta"]):   # G13: SENSEX has no footprint of its own (§1q)
        data["flow"], data["flow_src"] = _nifty_flow(day, mins, MI, inp)
    try:                                             # Task 5: what the tool already measures (display only, fail-soft)
        data["ctx"] = _context(day, idx, upto, cp, snaps, STEP, memo)
    except Exception as e:
        data["ctx"] = {"notes": [f"the reads (levels, EM, the logs) failed: {type(e).__name__}: {e}"]}
    data["reads"] = reads(data)
    data["health"] = health(data, _readable(day, "BANKNIFTY", upto, 100))
    data["health"]["method"] += [f"re-read from {a or mins[0]}: {x}" for a, x in redo]   # Task 6: how it was made, never a
                                                     # gap (a cold replay has no such line: health.method, not notes)
    try:
        ach = _atm_chain(R, STEP)
    except Exception:                                # display only: the premium reads say could not check
        ach = None
    data["legs"] = _legs(data, ach, day, idx)
    try:                                             # the ACTION word per minute: it needs the leg's rows (Jarvis v3)
        data["reads"]["action"] = action_words(data)
    except Exception as e:                           # display only: never take the frame down; the leg's word stands
        data["reads"]["action"] = []
        data["health"]["notes"].append(f"the ACTION word failed: {type(e).__name__}: {e} — the leg's word shown")
    try:                                             # THE MARKET STATE (mstate.py, spec 2026-11-06): display only
        import mstate
        mstate._thresholds()
        data["mstate"], data["pivots"] = mstate.fold(data, ach, mstate.norm(idx, day))
        data["zone_cards"] = mstate.cards(data, data["mstate"], data["pivots"])     # spec §6: one card per trigger
    except Exception as e:                           # never the frame: the ACTION word stays the word
        data["mstate"], data["pivots"], data["zone_cards"] = [], [], []
        data["health"]["notes"].append(f"the market state failed: {type(e).__name__}: {e} — the ACTION word shown")
    data["call"] = call(data)
    return data


def _nifty_flow(day, mins, MI, inp):
    """G13 (§1q, sensex_flow.ON): a SENSEX frame reads NIFTY's order flow, by the NIFTY frame's own rule -- Dext's footprint
    of NIFTY's book contract, else NIFTY's book (a SENSEX `inp` already carries NIFTY's book flow: handshake.load_flow, the
    flow its pushes are born on) -- on the SENSEX minutes -> (flow, flow_src "N" | None). A minute in neither stays None."""
    delta, _ = _footprint(_fut_tag(H.book_rows(day, "NIFTY")), day, mins, v2feed.LOTS["NIFTY"])
    flow = _frame_flow(delta, MI, inp)
    return flow, ["N" if x is not None else None for x in flow]


def _footprint(tag, day, mins, lot):
    """Dext 0.8.1's footprint per minute of `mins`, in lots -> (delta, volume); a minute Dext lacks is None."""
    fp = {c["time"][11:16]: c for c in (dext_log.read_candles(tag, day) if tag else [])}
    return ([round(fp[m]["delta"] / lot) if m in fp else None for m in mins],
            [round(fp[m]["total_volume"] / lot) if m in fp else None for m in mins])


def _frame_flow(delta, MI, inp):
    """The flow the reads use: Dext's footprint delta, else the book's own (handshake.book_flow, src B) -- a minute in
    neither stays None (Dext missing AND the book blind), never a zero."""
    return [x if x is not None else (inp["F"].get(m) if inp["src"].get(m) == "B" else None) for x, m in zip(delta, MI)]


def _atm_chain(R, step):
    """The ATM premium + delta per chain minute, near ATM (+/- 5 steps) -> {"HH:MM": {"spot", "ce": {k: {"ltp",
    "delta"}}, "pe": {...}}}: the leg's premium read (legs.read) and the market state's straddle / premium gauges
    (mstate.gauges, mstate._prem). A minute without spot is absent."""
    chain = {}
    for m, r in R.items():
        sp = r.get("spot")
        if not sp:
            continue
        row = {"spot": sp, "ce": {}, "pe": {}}
        for s in r.get("strikes") or ():
            if isinstance(s.get("k"), (int, float)) and abs(s["k"] - sp) <= 5 * step:
                for side in ("ce", "pe"):
                    leg = s.get(side) or {}
                    if leg.get("ltp") is not None and leg.get("delta") is not None:
                        row[side][s["k"]] = {"ltp": leg["ltp"], "delta": leg["delta"]}
        chain[hm(m)] = row
    return chain


def _legs(d, chain, day, idx):
    """THE LEG (legs.py, NOISE-DECODER-BRAINSTORM.md, merged decision 30 Oct) on this frame, with its two extras: the ATM
    premium + delta per chain minute (`chain`, _atm_chain's; None: its read says could not check) and her footprint
    marks (NIFTY's chart only: SENSEX reads NIFTY's flow, §1q, but a NIFTY mark's price means nothing on SENSEX).
    Fail-soft: a decoder error leaves the frame and the old call standing, and says so."""
    import legs
    import tape_log
    try:
        marks = list(_rows(os.path.join(tape_log.DIR, f"ofd_marks2_{idx}_{day}.jsonl"))) if idx == "NIFTY" else None
        return legs.read(d, chain=chain, marks=marks)
    except Exception as e:                                    # display only: never take the frame down
        return {"error": f"{type(e).__name__}: {e}", "rows": [], "pauses": [], "day": {}, "missing": ["the leg read failed"]}


def _readable(day, idx, upto, step):
    """Is this index's chain OI big enough to read? A strike within ATM ±7 moved >= the handshake's bar (CUT_L, 3L) in 3
    min at least once before upto [I]. BANKNIFTY's biggest 3-min strike move was 0.24L (28 Oct) / 0.52L (29 Oct) against
    NIFTY's 8.8L / 18.1L: it never can. None = no chain on the record (could not check)."""
    R = H.chain_minutes(_rows(confluence_log._chain_path(idx, day)))
    R = {m: r for m, r in R.items() if m < upto}
    if not R:
        return None
    for m, a in R.items():
        b = R.get(m - 3)
        if not b:
            continue
        atm = round(a["spot"] / step) * step
        for k in range(int(atm - 7 * step), int(atm + 7 * step) + 1, step):
            for s in ("ce", "pe"):
                x, y = H._leg(a, k, s).get("oi"), H._leg(b, k, s).get("oi")
                if x is not None and y is not None and abs(x - y) >= H.CUT_L * 1e5:
                    return True
    return False


# GAPS §3 rows this frame does not read (GAPS §5: named, never dropped): no source anywhere yet (Task 5 read the rest).
NOT_READ = ("book depth: pulls / stacking at the level (recorded, not read)",
            "points per minute, acceleration / decay",
            "IV per strike: bid vs crush, premium decay vs the move")
# rule 6's third sentence: read by their own module, not shown here
NOT_SHOWN = ("not shown here (their own module reads them): dwell (dwell.py), PCR change (chain_metrics), wall migration "
             "(warmap), Board agreement (board.py), GEX after 14:30 (gamma.py), footprint events other than BADA PRINT "
             "(the decoder log)",)


def _stretches(flags, mins):
    """[[from, to]] of the runs of True in `flags`."""
    out, i = [], 0
    while i < len(flags):
        if flags[i]:
            j = i
            while j + 1 < len(flags) and flags[j + 1]:
                j += 1
            out.append([mins[i], mins[j]])
            i = j + 1
        else:
            i += 1
    return out


def health(d: dict, bnf_readable=None) -> dict:
    """GAPS §3 A: every source's state as of the frame's last minute, each gap named with its span (rule 6: could not
    check is its own sentence, never a zero)."""
    mins = d["mins"]
    no_dx = [x is None for x in d["delta"]]
    missing = _stretches(no_dx, mins)
    tail = 0
    for x in reversed(no_dx):
        if not x:
            break
        tail += 1
    notes, own, meth = [], missing, []
    if "N" in (d.get("flow_src") or ()):           # G13: the flow is NIFTY's, so its gaps are NIFTY's (SENSEX has no footprint)
        meth.append("flow from NIFTY (§1q)")       # A231: how the flow is made (signed), never a gap (notes = missing)
        notes += [f"NIFTY flow missing {a}–{b}" for a, b in _stretches([x is None for x in d["flow"]], mins)]
        own = []
    for a, b in own:
        if tail and b == mins[-1]:
            src = d.get("flow_src") or []
            book = sum(1 for s in src[-tail:] if s == "B")
            notes.append(f"Dext footprint missing since {a} · newest {tail} min "
                         + (f"from the book" if book == tail else f"from the book {book}, blind {tail - book}"))
        else:
            notes.append(f"Dext footprint missing {a}–{b}" + (" (flow from the book)" if a != b else ""))
    for a, b in d.get("holes") or ():
        notes.append(f"book hole {a}–{b}: no 1-second book; "
                     + ("FILL replay: fut from the saved tape" if d.get("fill") else "answers there unread"))
    for a, b in _stretches([m in set(d.get("chain_missing") or ()) for m in mins], mins):
        notes.append(f"chain missing {a}–{b}: walls and answers there not read")
    fs = d.get("f_src") or []
    if fs.count("book"):
        notes.append(f"fut 1-min bars from the book for {fs.count('book')} min (Dext has no 1-minute bars there)")
    if fs.count("tape"):
        notes.append(f"fut 1-min bars rebuilt from the Upstox tape for {fs.count('tape')} min (the book was empty there)"
                     + (" · FILL replay: live Jarvis did not have these minutes" if d.get("fill") else ""))
    if d.get("live_from") and d["live_from"] > mins[0]:
        notes.append(f"recorded live from {d['live_from']}: {mins[0]}–{d['live_from']} rebuilt (chain backfill, Dext)")
    if d.get("sides") is None:
        notes.append("Sides: could not check — no saved chain")
    if bnf_readable is False and d.get("idx") == "BANKNIFTY":
        notes.append("BANKNIFTY chain OI too small to answer pushes (G14)")      # its own frame: one line, pushes kept
    elif bnf_readable is False:
        notes.append("BANKNIFTY chain OI too small to read (no strike near ATM moved 3L in 3 min)")
    elif bnf_readable is None:
        notes.append("BANKNIFTY chain: could not check — no chain on the record")
    notes += (d.get("ctx") or {}).get("notes") or []          # Task 5: each read's absent source, named (_context)
    method = meth + list((d.get("ctx") or {}).get("method") or ())   # how a number was made: not a gap (Task 6)
    if mins and mins[-1] >= CHAIN_END:
        method.append(f"chain ends {CHAIN_END} (scheduled)")   # I2: the close, never "chain missing"
    if thresholds.problem():
        method.append(thresholds.problem())                    # T6: every [I] number at the module's default, said
    return {"dext": {"minutes": no_dx.count(False), "missing": missing, "book_only_tail": tail},
            "holes": d.get("holes") or [], "chain_missing": d.get("chain_missing") or [], "bnf_chain_readable": bnf_readable,
            "f_src": {k: fs.count(k) for k in ("dext", "book", "tape")}, "live_from": d.get("live_from"), "notes": notes,
            "method": method, "not_read": list(NOT_READ), "not_shown": list(NOT_SHOWN)}


def _basis(d, i):
    """Her display basis at minute i: the median fut − spot over the last 3 min (fold.BIX_MS, A60); 0.0 with none."""
    a = max(0, i + 1 - fold.BIX_MS // 60000)
    bs = sorted(f - s for f, s in zip(d["fut"][a:i + 1], d["spot"][a:i + 1]) if f is not None and s is not None)
    return bs[len(bs) // 2] if bs else 0.0


def _walls(fr, spot):
    """The walls around spot among §1d's fronts (top-2 a side) -> (CE at / above spot, PE at / below it), nearest first."""
    return (sorted((f for f in fr if f["side"] == "CE" and f["k"] > spot - 5), key=lambda f: f["k"]),
            sorted((f for f in fr if f["side"] == "PE" and f["k"] < spot + 5), key=lambda f: -f["k"]))


def call(d: dict) -> dict:
    """THE ONE CALL at the frame's last minute, in GAPS §4's order: health -> location -> flow + speed -> writers ->
    futures OI -> cross-index -> her setup -> one word, its wrong-line, two scenarios, both expressions. The word is the
    market state's (spec 2026-11-06 §7: `mstate`, its fuel `grade`, `chips`, the `zone` card), and the ACTION word (Jarvis
    v3, `action_words` at this minute) is `action.said`, a chip under it; with no state row, or when that block raises
    ("market state: could not check — <ExcName>"), the word is the ACTION word as before. The ACTION word: the leg's state
    decided by the writers-first WITH / AGAINST count (`count`), changed only at two consecutive 3-min closes (PALAT, the wall behind BROKEN and CAN'T SEE at once);
    `state` is the leg's raw word. The 29 Oct vote stays as `v1` (UP / DOWN when the writers and one more of {a fut run,
    speed FAST, ALL 3} agree; RANGE when both sides add; NO TRADE when quiet or nothing agrees), and is the word only for a
    frame with no leg read. Counts, never %. Guidance only. Task 5 adds what the tool already measures, as lines and keys,
    never as a word: how_much / where / expression {buyer, seller, pick, pick_why, in_trade} / cross / her_setup / bada /
    expiry (how_much, where, expression, _cross, _her_setup, _bada, _vpin on the frame's `ctx`). `expiry` is {dte, mode}
    every day (mode null off 0 DTE: DTE is still worth a line), null only when the chain carries no expiry."""
    r, h, mins = d["reads"], d["health"], d["mins"]
    i = len(mins) - 1
    tl, sp, sy, w = d["timeline"][i], r["speed"][i], r["sync"][i], r["writers"][i]
    fut = d["fut"][i]
    basis = _basis(d, i)                             # her display basis: the 3-min median (fold.BIX_MS, A60)

    def lv(k):
        return f"{_fmt(k)}s ({_fmt(k + basis)}f)"

    # P0 (30 Oct): BLIND live. The frame's newest minute trails the clock (the futures trade to 15:39): no book, no tape --
    # her internet or Upstox is down. 30 Oct 14:30-14:45 read UP off 14:26's data while price fell 38; now it says so.
    up_m = _m(d["upto"]) if d.get("upto") else None
    lag = None if up_m is None else (up_m - 1) - _m(mins[i])
    blind = lag is not None and lag > BLIND_MIN and up_m - 1 <= H.LAST_M + 9
    missing = ([f"BLIND since {mins[i]}: no market data for {lag} min (internet or Upstox)"] if blind else []) + list(h["notes"])
    why = ["health: " + ("every source live" if not missing else f"{len(missing)} gap{'s' if len(missing) > 1 else ''}: "
                         + " · ".join(missing))]
    vw, sd = d["vwap"][i], d["sd"][i]
    why.append(f"location: {_fmt(fut)}f · VWAP {_fmt(vw)}f" + (f" · {(fut - vw) / sd:+.1f}σ" if sd else "")
               + f" · day {_fmt(min(d['flo']))}–{_fmt(max(d['fhi']))}f")
    why.append(f"flow: speed {ARR[sp['dir']]} ×{sp['x']:.1f} {sp['word']} · 3-min delta {_sgn(sp['d3'])}" if sp["x"] is not None
               else f"flow: speed ? ({sp['why']})")
    s = None
    for x in d.get("sides") or ():
        if x.get("t") and x["t"] <= mins[i]:
            s = x
    spot = d["spot"][i]
    ce, pe = _walls(tl.get("fronts") or [], spot)
    answered = [p for p in d["pushes"] if p.get("ans") not in (None, "?") and p.get("am") and p["am"] <= mins[i]]
    wtxt = (f"±7 {w['state']} (CE {H._l(w['ce'])} · PE {H._l(w['pe'])} / 3 min)" if w["state"] and w["ce"] is not None
            else f"±7 {w['state'] or 'quiet'}" + (" (chain not read this minute)" if w["ce"] is None else ""))
    stxt = ("Sides: could not check" if d.get("sides") is None else "Sides: no closed slot yet" if s is None else
            f"Sides {s['t']} {s['word'] or '?'}" + (f" ({'call' if s['fuel_side'] == 'ce' else 'put'} writers covering"
                                                     + (f", top-2 under water {s['uw']}/2" if s.get("uw") else "") + ")"
                                                     if sides_fuel(s) else ""))
    why.append("writers: " + " · ".join([wtxt, stxt,
                                         f"wall above {lv(ce[0]['k'])} CE {ce[0]['oi']:.0f}L {ce[0]['state'].lower()}"
                                         if ce and ce[0].get("oi") is not None else "no CE wall above in range",
                                         f"wall below {lv(pe[0]['k'])} PE {pe[0]['oi']:.0f}L {pe[0]['state'].lower()}"
                                         if pe and pe[0].get("oi") is not None else "no PE wall below in range"]
                                        + ([f"last answer {answered[-1]['t']} {answered[-1]['k'] and _fmt(answered[-1]['k'])}s "
                                            f"{answered[-1]['side']}{' ±2' if answered[-1].get('via') == 'band' else ''} "
                                            + ("GHUSE (buyers' add, not a defence)" if answered[-1]['ans'] == "TIKI"
                                               and answered[-1].get("who") == "KHAREEDAR" else answered[-1]['ans'])]
                                           if answered else [])))
    fu, fst = tl.get("fuel"), tl.get("fuel_state")
    why.append("fut OI: " + (f"{MEAN.get(fu['meaning'], fu['meaning'])} {_sgn(fu['lots'])} lots "
                             + ("LIVE" if fst == "LIVE" else "SPENT" if fst == "KHATAM" else "") if fu else
                             "could not check (a hole in the 5-min window)" if fst == "?" else "no run (bar 500 lots / 5 min)"))
    why.append("cross-index: " + ("could not check" if not sy or sy["dir"] is None else
                                  f"all 3 {ARR[sy['dir']]} in sync" if sy["dir"] else "3 indices mixed")
               + (f" (N {_sgn(sy['ch'][0])} · BN {_sgn(sy['ch'][1])} · SX {_sgn(sy['ch'][2])} / 5 min)"
                  if sy and sy["dir"] is not None else ""))
    tr = r["trade"][i]
    vb, vs = d["verdict"]["BUY"].get(mins[i]), d["verdict"]["SELL"].get(mins[i])
    pts_s = H._sg(f"{tr['pts']:+.0f}") if tr else ""
    mine = bool(tr) and tr.get("subject") == "her trade"       # Task 5: her marked trade is the subject when one is open
    why.append("her setup: " + ((f"her trade {tr['t']} " + (f"{lv(tr['k'])} " if tr.get("k") is not None else "")
                                 + f"{tr['opt']} {tr['role']} @{tr.get('p0') if tr.get('p0') is not None else '?'}"
                                 if mine else f"last trigger {tr['t']} {tr['side']} {_fmt(tr['px'])}f")
                                + f" · {pts_s} pts" + (f" · {tr['st']}" if tr["st"] else "") if tr else "no trigger yet")
               + f" · band verdict BUY {(vb or {}).get('word', '?')} / SELL {(vs or {}).get('word', '?')}")
    if mins[i] >= "15:00":
        why.append("after 15:00: her practice is no new trades (a reminder, not a rule)")
    ri = next((j for j in range(i, -1, -1) if r["writers"][j]["ev"] == "RISK"), None) if w["state"] == "RISK" else None
    if ri is not None:
        risk = r["writers"][ri]
        up_ = risk["dir"] > 0
        why.append(f"{'TOP' if up_ else 'BOTTOM'} RISK since {mins[ri]}: writers stopped pushing and {'sellers' if up_ else 'buyers'} hit — "
                   f"3-min delta {_sgn(risk['d3'])}, ×{risk['x']} normal")

    # the word
    s_dir = sides_fuel(s) or 0
    w_dirs = {w["dir"] if w["state"] in ("UP", "DOWN", "BACK") else 0, w.get("push") or 0}   # the leg's state, or this minute's push

    def more(dr):
        way = "▲" if dr > 0 else "▼"
        return [lbl for ok, lbl in ((fst == "LIVE" and fu and fu["dir"] == way, "fut run"),
                                    (sp["word"] == "FAST" and sp["dir"] == dr, "speed FAST"),
                                    (bool(sy) and sy["dir"] == dr, "all 3")) if ok]
    nt = next((x for x in r["notrade"] if x["from"] <= mins[i] <= x["to"]), None)
    both_add = (s is not None and s.get("c") == "ADD" and s.get("p") == "ADD") or \
        (w["ce"] is not None and w["ce"] >= WF_L and w["pe"] >= WF_L)
    agree = {dr: ([x for x, ok in (("Sides", s_dir == dr), ("writers ±7", dr in w_dirs)) if ok], more(dr)) for dr in (1, -1)}
    ok = [dr for dr in (1, -1) if agree[dr][0] and agree[dr][1]]
    if blind:
        word, reason = "CAN'T SEE", f"blind since {mins[i]} ({lag} min) — the last read is not carried"
    elif nt and nt["why"] == "can't see":
        word, reason = "NO TRADE", f"can't see: {nt['from']}–{nt['to']} not on the record"
    elif len(ok) == 1:
        word, reason = ("UP" if ok[0] > 0 else "DOWN"), " + ".join(agree[ok[0]][0] + agree[ok[0]][1]) + " agree"
    elif both_add:
        word, reason = "RANGE", "call and put writers both adding"
    elif nt:
        word, reason = "NO TRADE", f"quiet since {nt['since']}"
    else:
        lean = [f"{'▲' if dr > 0 else '▼'}: " + (" + ".join(agree[dr][0] + agree[dr][1]) or "nothing") for dr in (1, -1)]
        word, reason = "NO TRADE", "unclear — writers and flow do not agree (" + " · ".join(lean) + ")"
    v1 = {"word": word, "reason": reason}           # the 29 Oct vote, kept beside the leg for the evening comparison

    # THE LEG (legs.py, merged decision 30 Oct): the word is the leg's state, its lean changes only at PALAT. The vote
    # above flickered UP <-> NO TRADE 8 times in 30 Oct's 11:00-12:10 leg; the leg did not change once.
    LG = d.get("legs") or {}
    row = (LG.get("rows") or [None])[-1] if not LG.get("error") else None
    if row and row.get("t") != mins[i]:
        row = None
    lean = (row or {}).get("lean") or 0
    acts = r.get("action") or []
    act = acts[i] if len(acts) == len(mins) and not blind else None
    if act:
        word = said(act["word"], act["lean"])
        reason = act["why"] + (f" · leg {row['word']}: {row.get('line') or row['word']}" if row else "")
    elif not blind and row:                          # a frame whose ACTION series was not built (read before Jarvis v3)
        word = row["word"] + (f" {ARR[lean]}" if lean else "")
        reason = row.get("line") or row["word"]
    aw = act["word"] if act else row["word"] if row and not blind else None      # the word the expressions follow
    why.append(f"call: {word} — {reason}" + (f" · (the vote: {v1['word']})" if row and not blind else ""))
    leg_line = day_line = None
    if row and row.get("leg"):
        g = row["leg"]
        em = (d.get("ctx") or {}).get("em")              # A232: how much of the move the leg already used, display only
        used = f" · {g['pts'] / em['em']:.2f} of EM" if em and em.get("em") and (em.get("t") or "99") <= mins[i] else ""
        leg_line = (f"leg {ARR.get(g['dir'], '?')} {g.get('quality') or ''} {g['pts']} pts{used}"
                    + f" · {g.get('sigma_max') or 0:.1f}σ"
                    + (f" · TOOT {g['toot']}" if g.get("toot") else "") + (f" · fuelled {g['fuelled']}" if g.get("fuelled") else "")
                    + f" · origin {_fmt(g['origin'])}f {g['origin_t']} · extreme {_fmt(g['extreme'])}f {g['extreme_t']}")
        why.insert(1, leg_line)
    if row is not None:
        dd = LG.get("day") or {}
        fl = (dd.get("flips") or [None])[-1]
        fo = (dd.get("fut_oi") or [None])[-1]
        day_line = (f"day: legs flipped {fl} time{'s' if fl != 1 else ''} so far" if fl is not None else "day: flips ?") + \
            (f" · fut OI {fo['word']} {_sgn(fo['lots'])} lots / 30 min" if fo else " · fut OI: no 30-min story yet")
        why.insert(2 if leg_line else 1, day_line)
    elif LG.get("error"):
        why.append(f"leg: could not check — {LG['error']}")

    # the wrong-line, the two scenarios, both expressions (levels s / f)
    nb = [("d2", vw - 2 * sd), ("d1", vw - sd), ("VWAP", vw), ("u1", vw + sd), ("u2", vw + 2 * sd)]
    below = next((x for x in reversed(nb) if x[1] < fut - 3), None)
    above = next((x for x in nb if x[1] > fut + 3), None)
    up_s = (f"▲ if {lv(ce[0]['k'])} CE breaks (BROKEN) with writers ±7 ▲ → " + (lv(ce[1]["k"]) if len(ce) > 1 else "open space"))\
        if ce else "▲ open: no CE wall above in range"
    dn_s = (f"▼ if {lv(pe[0]['k'])} PE breaks (BROKEN) with writers ±7 ▼ → " + (lv(pe[1]["k"]) if len(pe) > 1 else "open space"))\
        if pe else "▼ open: no PE wall below in range"
    g = (row or {}).get("leg") if row and not blind else None
    lines = None
    if g and aw in ("TREND", "HOLD", "WATCH", "PALAT?") and lean:
        import legs as _lg
        U = max(sd or 0, 0.001 * fut)
        q35 = g["extreme"] - lean * _lg.DEEP * g["pts"]
        half = g["extreme"] - lean * max(_lg.REV_FRAC * g["pts"], _lg.REV_U * U)
        lines = {"q35": round(q35, 2), "half": round(half, 2)}     # the faces draw these, never their own copy (Dext 0.9)
        opt, other = ("CE", "PE") if lean > 0 else ("PE", "CE")
        wall = (pe[0] if pe else None) if lean > 0 else (ce[0] if ce else None)
        wrong = (f"back to HOLD on a real new {'high' if lean > 0 else 'low'} past {_fmt(g['extreme'])}f; "
                 f"PALAT at {_fmt(half)}f" if aw == "PALAT?" else
                 f"PALAT? if back past {_fmt(q35)}f (0.35 of the leg) · PALAT at {_fmt(half)}f: the lean ends there")
        entry = row["word"]                          # the ACTION word is the holder's; an entry keys on the leg's
        if entry == "PALAT?" or aw == "PALAT?":       # either word cautious: no new one (an ACTION PALAT? outlasts
            buyer = f"no new {opt}; a {opt} held tightens to {_fmt(half)}f (the PALAT line)"     # the leg's by 1-2 closes)
            seller = f"no new {other} sale until it holds again"
        else:
            buyer = (f"hold the {opt}, no new one while WATCH · stop = the PALAT line {_fmt(half)}f"
                     if entry == "WATCH" or aw == "WATCH" else
                     f"buy the {opt} on the pullback, not chased · stop = the PALAT line {_fmt(half)}f")
            seller = (f"hold a {other} sale, no new one while WATCH · same stop" if entry == "WATCH" or aw == "WATCH" else
                      f"sell the {other} at / beyond {lv(wall['k'])}: its writers are the leg's floor · same stop" if wall
                      else f"sell the {other}: its writers are the leg's floor · same stop")   # 5 Nov: WATCH offered a
            # new PE sale while its own count was 5 against (NIFTY 14:14-14:19); the buyer line already said no new one
    elif aw == "PALAT" and g and lean:               # the old leg ended, the new one is the lean: say both, both ways
        old = g["extreme"] if g["dir"] != lean else g["origin"]   # the flip minute's row holds the old leg, later rows the
        opt, other = ("CE", "PE") if lean > 0 else ("PE", "CE")   # new one (born at the old extreme)
        wrong = f"back to {ARR[-lean]} on a new {'high' if lean < 0 else 'low'} past {_fmt(old)}f"
        buyer = f"PALAT: the {ARR[-lean]} leg ended · no new {opt} until the {ARR[lean]} leg holds {ACT_CLOSES} closes"
        seller = f"PALAT: the {ARR[-lean]} leg ended · no new {other} sale until the {ARR[lean]} leg holds {ACT_CLOSES} closes"
    elif aw in ("PALAT", "ROTATION", "OPENING", "NO LEG"):
        wrong = ("ends: a leg that qualifies — after 10:00 ≥ 80 pts with 1.5σ, a TOOT or fuel; before 10:00 ≥ 100 pts and a TOOT")
        buyer = "no lean: buy only at her bands (the zone), never mid-range"
        seller = "no lean: sell outside the band, both sides"
    elif word == "UP":
        wrong = f"wrong if: below {lv(pe[0]['k'])} (the floor) or call writers adding again" if pe else \
            "wrong if: call writers adding again or a 3-min delta >= 2x normal against"
        buyer = f"buy the CE on a pullback to {below[0]} {_fmt(below[1])}f, not chased" if below else "buy the CE on a pullback, not chased"
        seller = f"sell the PE at / below {lv(pe[0]['k'])}: put writers are writing it" if pe else "sell the PE: put writers are writing"
    elif word == "DOWN":
        wrong = f"wrong if: above {lv(ce[0]['k'])} (the cap) or put writers adding again" if ce else \
            "wrong if: put writers adding again or a 3-min delta >= 2x normal against"
        buyer = f"buy the PE on a pullback to {above[0]} {_fmt(above[1])}f, not chased" if above else "buy the PE on a pullback, not chased"
        seller = f"sell the CE at / above {lv(ce[0]['k'])}: call writers are writing it" if ce else "sell the CE: call writers are writing"
    elif word == "RANGE":
        lo_, hi_ = (lv(pe[0]["k"]) if pe else "?"), (lv(ce[0]["k"]) if ce else "?")
        wrong = f"wrong if: a 3-min close outside {lo_} – {hi_}"
        buyer = "no buyer trade mid-range"
        seller = f"sell outside the range: CE at / above {hi_}, PE at / below {lo_} (both sides writing)"
    elif word == "CAN'T SEE":
        wrong = "ends: market data back on the record (book or the saved tape)"
        buyer, seller = "wait: blind, no new trade", "wait: blind, no new sale"
    else:
        wrong = "ends: " + (nt["ends"] if nt else "the writers and one more read agree (FUEL, speed FAST, ALL 3)")
        buyer, seller = "wait: no buyer trade", "wait: no new sale"

    if act:
        cnt = act["count"]
    elif blind:
        cnt = _count_of([{"k": k, "side": "?", "text": f"could not check — blind since {mins[i]}"} for k in PIECES])
    else:
        try:                                         # I1: wrapped as action_words is -- one bad piece never the build
            cnt = count(d, i)
        except Exception as e:
            cnt = _count_of([{"k": k, "side": "?", "text": f"could not check — {type(e).__name__}"} for k in PIECES])
    # Task 5 (VISION §4 stages 5-9): HOW MUCH, WHERE, EXPRESSION, her trade, the cross-checks. Display only, fail-soft:
    # they add lines, never a word
    T5 = {"how_much": None, "where": None, "expression": None, "cross": None, "her_setup": [], "expiry": None, "bada": None}
    try:
        T5["cross"], cline = _cross(d, i)
        T5["her_setup"] = _her_setup(d, i)
        dte = (d.get("ctx") or {}).get("dte")
        T5["expiry"] = None if dte is None else {"dte": dte, "mode": None if dte else
                                                 "EXPIRY UNWIND after 14:00" if mins[i] >= UNWIND_AT else "EXPIRY DAY"}
        ent = None
        if mine:
            j = mins.index(tr["t"]) if tr["t"] in mins else None
            a = acts[j] if j is not None and len(acts) == len(mins) else None
            ent = {"id": tr["id"], "side": tr["opt"], "role": tr["role"], "pts": None if blind else tr["pts"],
                   "word_at_entry": said(a["word"], a["lean"]) if a else None}
        if blind:
            T5["how_much"] = {"line": f"could not check — blind since {mins[i]}", "rows": []}
            T5["expression"] = {"buyer": buyer, "seller": seller, "pick": None, "pick_why": f"blind since {mins[i]}",
                                "in_trade": ent}
        else:
            side_ = 0 if aw == "RANGE" else lean        # A229: RANGE names no side, so no T1 / T2 or buyer leg its way
            T5["how_much"], T5["where"] = how_much(d, i, lv), where(d, i, side_, lines, ce, pe, lv, basis)
            ex = expression(d, i, aw, side_, s, buyer, seller, lv, cnt)
            buyer, seller, T5["expression"] = ex["buyer"], ex["seller"], dict(ex, in_trade=ent)
            wh = T5["where"]
            why += [f"how much: {T5['how_much']['line']}",
                    "where: " + (" · ".join(f"{k.upper()} {wh[k]}" for k in ("stop", "pool", "t1", "t2", "room") if wh[k])
                                 or "nothing placed (the card's rows say why)"),
                    f"expression: pick {ex['pick'] or 'none'} — {ex['pick_why']}", cline]
            T5["bada"] = _bada(d, i, (ce[0] if ce else None, pe[0] if pe else None), lv, basis)   # the card's pushes' neighbour
            why += [T5["bada"], _vpin(d, i)]
            if T5["her_setup"]:                      # the latest three; the card's her_setup holds the day
                hs = T5["her_setup"]
                why.append("her setup (confluence log): " + " · ".join(hs[-3:])
                           + (f" (+{len(hs) - 3} earlier)" if len(hs) > 3 else ""))
            if T5["expiry"] and T5["expiry"]["mode"]:
                why.append(f"expiry: 0 DTE · {T5['expiry']['mode']}"
                           + (" — writers covering is not counted WITH" if mins[i] >= UNWIND_AT else ""))
    except Exception as e:                           # never the frame, never the word
        why.append(f"the reads failed: {type(e).__name__}: {e}")
    ms = d.get("mstate") or []
    srow = ms[i] if len(ms) == len(mins) and not blind else None      # THE MARKET STATE leads (spec 2026-11-06 §7)
    said_act, grade, zone, mso, chips = word, None, None, None, []   # the ACTION word: now a chip under the state
    if srow:
        try:                                         # M3: fail-soft; a raise keeps the ACTION word, never fails the build
            import mstate
            grade = _grade(cnt, srow["dir"], lean)
            vw_ = (srow.get("vol") or {}).get("word")
            head = [f"state: {srow['word']}" + (f" · {vw_}" if vw_ else "") + f" since {srow['since']} — {srow['why']}"
                    + (f" · {srow['line']}" if srow.get("line") else "")
                    + (f" · eff {srow['eff']:.2f}" if srow.get("eff") is not None else "")
                    + ((f" · {grade}" if str(grade).startswith("fuel") else f" · fuel {grade}") if grade else "") + f" · action {said_act}"]
            zc = [z for z in d.get("zone_cards") or () if z["known"] <= mins[i] and _m(mins[i]) - _m(z["known"]) < MANAGE_WIN]
            tc = [z for z in zc if z.get("trade")]   # §6a: the open trade as of this minute (Task 9a), never a later one
            op = [e for e in tc[-1]["trade"] if e["t"] <= mins[i]] if tc else []
            zone = (dict({k: v for k, v in zc[-1].items() if k != "trade"}, line=mstate.card_line(zc[-1]),
                         open=dict(op[-1], of=tc[-1]["t"]) if op else None) if zc else None)
            if zone:
                gt, O = zone.get("gate"), zone["open"]
                head.append("zone: " + zone["line"] + f" — {zone['why']}"
                            + (f" · her gate (§1d): {'legal' if gt.get('legal') else 'NOT legal'} — {gt.get('why')}"
                               if isinstance(gt, dict) else "")
                            + (f" · open {O['of']}: " + " · ".join(O["chips"]) if O and O["chips"] else ""))
            mso = ({k: srow.get(k) for k in ("word", "dir", "conf", "since", "why", "line", "eff", "expiry")}
                   | {"vol": {k: (srow.get("vol") or {}).get(k) for k in ("word", "since", "up", "down", "read", "gauges")},
                      "grade": grade, "chip": mstate.chip(srow)})
            chips = [x for x in (said_act, grade and (grade if grade.startswith("fuel") else f"fuel {grade}")) if x]
            word, why = srow["word"], head + why
        except Exception as e:                       # noqa: BLE001
            srow, grade, zone, mso, chips = None, None, None, None, None
            why.insert(0, f"market state: could not check — {type(e).__name__}")
    return T5 | {"at": mins[i], "word": word, "why": why, "wrong_line": wrong, "up": up_s, "dn": dn_s, "buyer": buyer,
            "seller": seller, "missing": missing, "note": "guidance only: she places every trade herself",
            "state": (row or {}).get("word"),
            "since": srow["since"] if srow else act["since"] if act else mins[i] if blind else None,
            "count": cnt,
            "action_why": act["why"] if act else reason,
            "lean": lean, "leg": leg_line, "day": day_line, "pause": None if row is None or blind else
            {"line": row.get("line"), "alive": row.get("alive"), "risk": row.get("risk"), "notes": row.get("notes"),
             "missing": row.get("missing")}, "v1": v1, "lines": lines,
            "action": {"said": said_act, "word": act["word"] if act else None, "lean": lean,
                       "since": act["since"] if act else None, "why": act["why"] if act else reason},
            "mstate": mso,
            "chips": chips,
            "zone": zone,
            "walls": {"ce": None if not ce else {"k": ce[0]["k"], "f": round(ce[0]["k"] + basis, 2), "oi": ce[0].get("oi"),
                                                 "state": ce[0].get("state")},
                      "pe": None if not pe else {"k": pe[0]["k"], "f": round(pe[0]["k"] + basis, 2), "oi": pe[0].get("oi"),
                                                 "state": pe[0].get("state")}}}


# ---- Task 2: the face's reads, in the brain (jarvis2.html / jarvis2_live.html JS, ported; DAY-2026-10-29 §8 corrections)

ARR = {1: "▲", -1: "▼"}
MEAN = {"shorts cover": "shorts covering", "naye short": "fresh shorts", "naye long": "fresh longs",
        "longs nikal rahe": "longs closing"}
FAST, SLOW = 2.0, 0.5                         # SPEED: x its own median [I]
SYNC_PTS = (10, 25, 35)                       # ALL 3: NIFTY fut / BANKNIFTY / SENSEX in 5 min [I]
WF_L, WF_STOP = 10.0, -2.0                    # WRITER FLOW ±7: a leg's 3-min L; the covering side "stopped" at >= -2L [I]
RISK_X, RISK_WIN = 2.0, 9                     # TOP / BOTTOM RISK: 3-min delta >= 2x its day median against, within 9 min [I]
RISK_HOLD, RISK_CONF = 9, 0.3                 # G2: RISK lasts 9 min unless price went 0.3 step against the leg since [I]
BLIND_MIN = 2                                 # P0: the newest minute more than 2 min behind the clock = blind [I]
LAD_NEAR = 7          # [I] each minute's ladder also holds ATM ±7 of that minute (the ±7 writer flow's width): STRIKES spans
                      #     the whole frame's spot range, so a 13:41 frame's 12:11 ladder had 22,800 and a 12:50 frame's did
                      #     not, and the leg's band read changed with later minutes (28 Oct; Jarvis v3, the causal test)
FIGHT_AWAY, FIGHT_AWAY_MIN = 2, 15            # P2: a fight's wall > 2 steps from price for 15 min is left behind [I]
MANAGE_PTS, MANAGE_WIN, MANAGE_GAP = 15, 46, 6
QUIET_MIN = 20
# Jarvis v3, the ACTION word (Task 1; JARVIS-REVIEW-2026-10-31 §3.1-3.2, P0 #1-3)
ACT_LEAD = 2           # [I] TREND needs WITH >= AGAINST + 2, two more voices than against (the dream mockup's n/N separated
                       #     the 0/11 red-leg buys from the 6/10 holds); a pause holds at WITH >= AGAINST, else WATCH
ACT_CLOSES = 2         # [I] a new word needs the same candidate at 2 consecutive 3-min closes: the leg's state flipped
                       #     78 / 52 / 79 times on 21 / 29 / 30 Oct (a 3-pt wiggle flipped WATCH -> HOLD -> WATCH)
ANSWER_MIN = 15        # [I] the count's last answer: a push answered within 15 min (the band verdict's DASTAK window)
AHEAD_STEPS = 2        # [I] the wall ahead: within 2 strike steps of spot (the band verdict's own reach, wall_ahead)
BOX_STEPS = 1          # [I] the range guard (A229): the leg turned inside the writers' box, within 1 strike step of a wall
PIECES = ("sides", "wf7", "wall_ahead", "answer", "trapped", "fut_oi", "speed", "all3")   # GAPS §4, writers first; her
                                                       # zone trigger left the count 6 Nov: it is the zone card's (spec §2)
CHAIN_PIECES = ("sides", "wf7", "wall_ahead", "trapped", "all3")   # read off the chain this minute (all3: BN / SX spot)
ANSWER_EN = {"TOOT": "BROKEN", "PHANS": "TRAPPED", "TIKI": "DEFENDED", "NAHI": "HELD"}           # spec §16.2
# Jarvis v3 Task 5, the reads (JARVIS-REVIEW-2026-10-31 §3.3, P0 #4; VISION §4 stages 5-9; NOTEPAD A207). Display only.
NEED_X = 1.15          # [I] the buyer's required move = the ATM premium x 1.15 in points (algo_ai T3: the premium back
                       #     plus a cushion for spread and theta), set against EM left = EM - |fut - the open|
IV_RV = 1.15           # [I] ATM IV >= RV x 1.15 reads rich (<= RV / 1.15 cheap, else fair): the seller's edge
CPR_NARROW = 0.1       # [I] CPR narrow when |tc - bc| <= 0.1 x the prior day's range (algo_ai's CPR; the cut is ours)
VIX_OPEN_BY = "09:17"  # [I] the day's first VIX row by 09:17 is its open (09:15's candle, or one or two missing from Upstox);
                       #     a later first row reads "since HH:MM (started late)"
POOL_X = 1.5           # [I] the stop's pool: PDH / PWH (a short; a long PDL / PWL) beyond the stop, within 1.5 x its distance
UNWIND_AT = "14:00"    # [I] 0 DTE from 14:00: writers covering is the expiry unwind (G9), never counted WITH
RANK_3OF5 = math.sqrt(3 / 5)   # [I] rank_build keeps |5-min delta| medians; a 3-min sum's yardstick is sqrt(3/5) of one
                               #     (a sum's size grows ~sqrt(n)): of sqrt and linear (3/5) the bigger, so fewer FAST
RANK_DIR = os.path.join("data", "rank")                # rank_build's rank_ref_<IDX>_<day>.json (days before the day)
DECODE_DIR = os.path.join("data", "decode")            # the DECODE block's forward log (the server's decode_<day>.jsonl)
VPIN_FAST = os.path.join("data", "vpin_fast.jsonl")    # the fast VPIN gauge on NIFTY's future, shadow (server.VPIN_FAST_LOG)
RV_N, RV_MIN, RV_YEAR = 6, 4, 252.0                    # server._rv5's: 6 closes, >= 4 returns, sqrt(252) (reproduced)
RV_CAL = math.sqrt(365 / 252)  # [I] server._rv5 annualises on 252 TRADING days, the chain's IV is on 365 CALENDAR days
                               #     (surface.years_to_expiry / gamma.DAYS_PER_YEAR): RV x sqrt(365/252) onto IV's basis
                               #     before grading, else ~1.20 of a "rich" would be the day count alone (review 1 Nov);
                               #     exact with no weekend inside the option's life, so _rv_cal scales it by
                               #     sqrt(trading / calendar days to expiry) when the chain names the expiry (Task 6)

# Jarvis v3 Task 6: every [I] number above is looked up in jarvis_thresholds.json as "jarvis.<NAME>" (thresholds.py), its
# value here the default -- at import and at the start of each build, so a change takes effect at the next build, no
# restart. Every change needs a NOTEPAD line (the file's "_rule"). RV_N / RV_MIN / RV_YEAR are server._rv5's, reproduced:
# not ours to move.
_I = ("P5_MIN", "FAST", "SLOW", "SYNC_PTS", "WF_L", "WF_STOP", "RISK_X", "RISK_WIN", "RISK_HOLD", "RISK_CONF", "BLIND_MIN",
      "LAD_NEAR", "FIGHT_AWAY", "FIGHT_AWAY_MIN", "MANAGE_PTS", "MANAGE_WIN", "MANAGE_GAP", "QUIET_MIN", "ACT_LEAD",
      "ACT_CLOSES", "ANSWER_MIN", "AHEAD_STEPS", "BOX_STEPS", "NEED_X", "IV_RV", "CPR_NARROW", "POOL_X", "UNWIND_AT",
      "RANK_3OF5", "RV_CAL", "VIX_OPEN_BY")
_DEF = {n: globals()[n] for n in _I}
_APPLIED = [None]                # the thresholds file state last applied


def _thresholds():
    """The [I] numbers from jarvis_thresholds.json, applied again only when the file changed (thresholds.stamp)."""
    st = thresholds.stamp()
    if st != _APPLIED[0]:
        globals().update({n: thresholds.get(f"jarvis.{n}", v) for n, v in _DEF.items()})
        _APPLIED[0] = st


_thresholds()


def days() -> dict:
    """Her replay calendar (31 Oct): the days a replay can build, per index -- the 1-second book AND the chain both on the
    record (plain or gzipped); file names only, no build. A day can still be partial (16 Oct: 32 min): the replay names
    its own span."""
    import glob
    import re
    import book_log

    def have(pat):
        return {m.group(1) for p in glob.glob(pat) if (m := re.search(r"_(\d{4}-\d\d-\d\d)\.jsonl", p))}
    return {i: sorted(have(os.path.join(book_log.DIR, f"book_{i}_*.jsonl*"))
                      & have(os.path.join(str(chain_live.CHAIN_DIR), f"chain_{i}_*.jsonl*"))) for i in ("NIFTY", "SENSEX", "BANKNIFTY")}


def calls(d: dict) -> list:
    """Her backtest replay (31 Oct): THE ONE CALL as it stood at every minute -- call() on the frame cut at minute i (the
    per-minute series, reads and leg rows to i; holes and health as known then), so a scrubbed replay shows what Jarvis
    said at 11:14, not the close's call. The card's fields only. A replay has no clock, so CAN'T SEE never shows here: a
    minute missing from the record is simply absent (health names the hole)."""
    out = []
    for i in range(len(d["mins"])):
        c = call(cut_at(d, i))
        out.append({k: c[k] for k in ("at", "word", "lean", "leg", "day", "wrong_line", "buyer", "seller", "state", "since",
                                      "count", "action_why", "action", "mstate", "chips", "zone")}
                   | {"pause": c["pause"] and {"line": c["pause"].get("line")}})
    return out


def cut_at(d: dict, i: int) -> dict:
    """The frame as it stood at minute i: the per-minute series, reads and leg rows to i, holes and health as known then
    (`ctx` is keyed by minute, never cut). calls() runs call() on it at every minute."""
    mins, N = d["mins"], len(d["mins"])

    def cut(v):
        return v[:i + 1] if isinstance(v, list) and len(v) == N else v
    lg = d.get("legs") or {}
    v = {k: x if k in ("zone_cards", "pivots") else cut(x) for k, x in d.items()}   # cards/pivots are not per-minute
    v["reads"] = {k: cut(x) for k, x in d["reads"].items()}
    v["legs"] = dict(lg, rows=cut(lg.get("rows") or []), day={k: cut(x) for k, x in (lg.get("day") or {}).items()})
    v["holes"] = [h for h in d.get("holes") or () if h[0][:5] <= mins[i]]
    v["upto"] = hm(_m(mins[i]) + 1)
    v["health"] = health(v, d["health"].get("bnf_chain_readable"))
    return v


def _count_of(pieces):
    """A230 (rule 6, A223): every piece carries its `state` -- with / against / flat (checked, it takes no side) / blind
    (could not check: its text says so) -- and the count says flat and blind apart; `unread` (= flat + blind) stays for
    the faces that read it."""
    for p in pieces:
        p["state"] = p["side"] if p["side"] != "?" else "blind" if p["text"].startswith("could not check") else "flat"
    st = [p["state"] for p in pieces]
    w, a, fl, bl = st.count("with"), st.count("against"), st.count("flat"), st.count("blind")
    return {"with": w, "against": a, "N": w + a, "flat": fl, "blind": bl, "unread": fl + bl, "pieces": pieces}


def count(d: dict, i: int, vote: list | None = None) -> dict:
    """WITH / AGAINST at minute i of frame d, in GAPS §4's order, writers first (sides, wf7, wall_ahead, answer, trapped)
    -> fut OI -> flow and speed -> cross-index (her zone trigger is the zone card's, never a vote: spec 2026-11-06 §2). Counted for the leg's lean (legs row i); with no leg, for the
    29 Oct vote's direction (`vote`: legs._jarvis_words(d), passed by a caller that has it), else every piece is "?".
    Each piece says with / against / "?"; a "?" is "could not check — why" or "checked: says nothing" and never counts
    against (N = with + against). Causal: minute i reads minutes <= i only. Counts, never a rate."""
    import legs
    mins, t = d["mins"], d["mins"][i]
    m = _m(t)
    rows = (d.get("legs") or {}).get("rows") or []
    row = rows[i] if i < len(rows) and rows[i].get("t") == t else None
    L = (row or {}).get("lean") or 0
    if not L:
        v = (vote if vote is not None else legs._jarvis_words(d) or [None] * len(mins))[i]
        L = {"UP": 1, "DOWN": -1}.get(v, 0)
    if not L:
        return _count_of([{"k": k, "side": "?", "text": "could not check — no leg and no vote: no direction to count"}
                          for k in PIECES])
    R, P = d.get("reads") or {}, []

    def put(k, side, text):
        P.append({"k": k, "side": side, "text": text})

    def by(dr):
        return "with" if dr == L else "against"

    # the writers: Sides (the 2x2), the ±7 flow, the wall ahead, the last answer, who is trapped
    slot = None
    for x in d.get("sides") or ():
        if x.get("t") and x["t"] <= t:
            slot = x
    no_slot = "could not check — no saved chain" if d.get("sides") is None else "could not check — Sides has no closed slot"
    if slot is None:
        put("sides", "?", no_slot)
    else:
        f, head = sides_fuel(slot), f"Sides {slot['t']} {slot.get('word') or '?'}"
        if f:
            put("sides", by(f), f"{head} · {'call' if f > 0 else 'put'} writers covering")
        elif slot.get("word") == "CAPPED" or (slot.get("c") == "ADD" and slot.get("p") == "ADD"):
            put("sides", "against" if (row or {}).get("word") == "TREND" else "?",
                f"Sides {slot['t']} CAPPED · both sides writing")
        else:
            put("sides", "?", head)
    w = (R.get("writers") or [{}] * (i + 1))[i] or {}
    if w.get("ce") is None or w.get("pe") is None:
        put("wf7", "?", "could not check — chain not read this minute")
    else:
        nums = f"(CE {H._l(w['ce'])} · PE {H._l(w['pe'])} / 3 min)"
        if w.get("state") in ("UP", "DOWN", "BACK") and w.get("dir"):
            put("wf7", by(w["dir"]), f"writers ±7 {w['state']} {nums}")
        elif w.get("push"):
            put("wf7", by(w["push"]), f"writers ±7 {'call' if w['push'] > 0 else 'put'} writers covering {nums}")
        else:
            put("wf7", "?", f"writers ±7 {w.get('state') or 'quiet'} {nums}")
    step, spot = d.get("step") or 50, (d.get("spot") or [None] * (i + 1))[i]
    side = "CE" if L > 0 else "PE"
    if t in set(d.get("chain_missing") or ()) or spot is None:
        put("wall_ahead", "?", f"could not check — chain missing at {t}")
    else:
        lo, hi = (spot - step / 2, spot + AHEAD_STEPS * step) if L > 0 else (spot - AHEAD_STEPS * step, spot + step / 2)
        fr = [f for f in ((d.get("timeline") or [{}] * (i + 1))[i] or {}).get("fronts") or ()
              if f.get("side") == side and lo <= f["k"] <= hi]
        if not fr:
            put("wall_ahead", "?", f"no wall ahead in {AHEAD_STEPS} steps")
        else:
            f = min(fr, key=lambda f: L * f["k"])                        # the first one price meets
            put("wall_ahead", {"UNWINDING": "with", "BUILDING": "against"}.get(f.get("state"), "?"),
                f"wall ahead {_fmt(f['k'])}s {side}" + (f" {f['oi']:.0f}L" if f.get("oi") is not None else "")
                + f" {f.get('state')}")
    known = [p for p in d.get("pushes") or () if not p.get("artifact") and p.get("am") and p["am"] < t   # known the minute
             and p.get("ans") not in (None, "?") and m - _m(p["t"]) <= ANSWER_MIN]                     # after (final_ans)
    if d.get("idx") and d["idx"] not in H.SPEAK:     # A231: handshake.SPEAK -- this index's OI cannot cross the 3L answer
        put("answer", "?", f"not counted — {d['idx']}'s answers are logged, not said: the 3L answer bar is "   # bar, so
                           "NIFTY's (handshake.SPEAK)")      # every answer reads HELD (3 Nov SENSEX: 19 of 19); flat, not
                                                             # blind: the data is there, left out by design (rule 6)
    elif not known:
        put("answer", "?", f"no answered push in {ANSWER_MIN} min")
    else:
        p = known[-1]
        a = "GHUSE" if p["ans"] == "TIKI" and p.get("who") == "KHAREEDAR" else p["ans"]
        txt = (f"last answer {p['t']} push {ARR.get(p['dir'], '?')} "
               + (f"{_fmt(p['k'])}s " if p.get("k") is not None else "") + f"{p.get('side') or ''}{' ±2' if p.get('via') == 'band' else ''} ")
        if a == "GHUSE":
            put("answer", "?", txt + "buyers in at the wall")
        elif p["dir"] == L:                                              # the lean's own push: did its wall give way?
            put("answer", "with" if a in ("TOOT", "PHANS") else "against" if a in ("TIKI", "NAHI") else "?",
                txt + ANSWER_EN.get(a, a))
        else:                                                            # a push against: did the floor / cap behind hold?
            put("answer", "with" if a == "TIKI" else "against" if a in ("TOOT", "PHANS") else "?", txt + ANSWER_EN.get(a, a))
    who = "call" if L > 0 else "put"
    if slot is None:
        put("trapped", "?", no_slot)
    elif slot.get("fuel_side") != ("ce" if L > 0 else "pe") or slot.get("uw") is None:
        put("trapped", "?", f"could not check — Sides {slot['t']} reads under water on its fuel side only")
    elif slot["uw"] >= 1:
        put("trapped", "with", f"top-2 {who} writers under water {slot['uw']}/2 · Sides {slot['t']}")
    else:
        put("trapped", "?", f"top-2 {who} writers under water 0/2 · Sides {slot['t']}")
    # futures OI (the leg's DAY line, its 30-min quadrant)
    LG = d.get("legs") or {}
    fo = (LG.get("day") or {}).get("fut_oi") or []
    if LG.get("error") or len(fo) <= i:
        put("fut_oi", "?", "could not check — the leg read has no DAY line")
    elif fo[i] is None:
        oi, t30 = d.get("oi") or [], hm(m - legs.FUT_WIN)
        j30 = mins.index(t30) if t30 in mins else None
        if j30 is None or len(oi) <= i or oi[i] is None or oi[j30] is None:
            put("fut_oi", "?", f"could not check — fut OI needs {legs.FUT_WIN} min of OI")
        else:
            put("fut_oi", "?", "no 30-min story")
    else:
        q = fo[i]
        put("fut_oi", by(1 if q["word"] in ("fresh longs", "short covering") else -1),
            f"fut OI {q['word']} {_sgn(q['lots'])} lots / 30 min")
    # flow and speed, cross-index
    sp = (R.get("speed") or [None] * (i + 1))[i]
    if not sp or sp.get("x") is None:
        put("speed", "?", f"could not check — speed ({(sp or {}).get('why') or 'no flow'})")
    else:
        put("speed", by(sp["dir"]) if sp["word"] == "FAST" else "?", f"speed {ARR[sp['dir']]} ×{sp['x']:.1f} {sp['word']}")
    sy = (R.get("sync") or [None] * (i + 1))[i]
    if not sy or sy.get("dir") is None:
        put("all3", "?", "could not check — ALL 3 needs 5 min of all three indices")
    else:
        nums = f"(N {_sgn(sy['ch'][0])} · BN {_sgn(sy['ch'][1])} · SX {_sgn(sy['ch'][2])} / 5 min)"
        put("all3", by(sy["dir"]) if sy["dir"] else "?",
            (f"all 3 {ARR[sy['dir']]} " if sy["dir"] else "3 indices mixed ") + nums)
    if (d.get("ctx") or {}).get("dte") == 0 and t >= UNWIND_AT:      # Task 5, G9: 0 DTE afternoon, covering is the unwind
        for p in P[:2]:                                              # (sides, wf7): never WITH, said why
            if p["side"] == "with":
                p.update(side="?", text=p["text"] + " · expiry unwind")
    if t >= CHAIN_END and t not in (d.get("ladder") or {}):         # I2: past the chain's scheduled end its reads are
        for p in P:                                                  # not carried, never counted (an answer known stays)
            if p["k"] in CHAIN_PIECES or (p["k"] == "answer" and p["text"].startswith("no answered push")):
                p.update(side="?", text=f"could not check — chain ends {CHAIN_END}")
    return _count_of(P)


def said(word, lean):
    """The ACTION word as said: the word and its lean arrow -- except OPENING and NO TRADE, whose lean is a chip of its
    own (the card's `lean`), never part of the word (ruling 1, 1 Nov: the open's geometric flips are not announced). RANGE
    too (A229): inside the writers' box the lean flips with every swing; the word names no side."""
    return word + (f" {ARR[lean]}" if lean and word not in ("OPENING", "NO TRADE", "RANGE") else "")


def _grade(cnt, D, lean):
    """The trend's fuel from the count (spec 2026-11-06 §3: the pieces GRADE a trend, never flip it) -> "healthy" /
    "tired" / "fuel blind", None outside a trend. The count is for the leg's lean: a trend the other way reads it
    mirrored. HOLD with nothing voting is not allowed: no WITH and no AGAINST reads "fuel blind" (spec §7)."""
    if not D:
        return None
    w, a = (cnt or {}).get("with") or 0, (cnt or {}).get("against") or 0
    if lean and lean != D:
        w, a = a, w
    if not w and not a:           # rule 6: could not check (blind, none checked flat) is not checked and took no side (flat)
        return "fuel flat" if (cnt or {}).get("flat") else "fuel blind"
    return "healthy" if w >= a else "tired"


def _box(d, i, g):
    """THE RANGE GUARD at minute i (A229; docs/kahani/review/JARVIS-FIX-2026-11-04.md §1) -> the box in words, or None.
    The writers hold a box when the nearest CE wall at / above spot and the nearest PE wall at / below it (§1d's fronts,
    top-2 a side, read only) are both there and neither is covering (UNWINDING held 3 min, Q17: both sides writing or
    holding),
    the leg `g` turned inside them (its extreme within BOX_STEPS strike steps of the box, in spot terms: futures less the
    3-min basis) and §1o's day type, as DECODE last logged it by minute i, is not TREND. A chain-missing minute has no box
    (its walls are carried, not seen). Causal like the count: minute i reads minutes <= i only."""
    t, spot = d["mins"][i], (d.get("spot") or [None] * (i + 1))[i]
    if not g or g.get("extreme") is None or spot is None or t in (d.get("chain_missing") or ()):
        return None
    dec = _logged(d, i)[1]
    ty = (dec[-1].get("os") or {}).get("type") if dec else None
    if str(ty or "").startswith("TREND"):
        return None
    tl = d.get("timeline") or [{}] * (i + 1)
    ce, pe = _walls((tl[i] or {}).get("fronts") or [], spot)

    def covering(f):                  # §1d's UNWINDING held 3 minutes (Q17's hold, _build's unwinding_held): a one-minute
        return all(any(x.get("side") == f["side"] and x.get("k") == f["k"] and x.get("state") == "UNWINDING"   # dip of
                       for x in (tl[j] or {}).get("fronts") or ()) for j in range(max(0, i - 2), i + 1))    # the slope is not
    if not ce or not pe or covering(ce[0]) or covering(pe[0]):                                         # covering (4 Nov 11:32)
        return None
    lo, hi, tol = pe[0]["k"], ce[0]["k"], BOX_STEPS * (d.get("step") or 50)
    if not lo - tol <= g["extreme"] - _basis(d, i) <= hi + tol:
        return None
    return (f"writers' box {_fmt(lo)}s PE {str(pe[0].get('state')).lower()} – {_fmt(hi)}s CE "
            f"{str(ce[0].get('state')).lower()} · the leg turned at {_fmt(g['extreme'])}f inside · §1o {ty or '?'}")


def _palat_cond(row):
    """The leg's own PALAT? condition at this minute (legs.read: FAST against, >= 3 risk items, or 0.35 of the leg back),
    as distinct from its latched / minimum-display PALAT? word."""
    import legs
    risk = row.get("risk") or ()
    return (any(x.get("k") == "fast_against" for x in risk) or len(risk) >= legs.PALAT_N
            or ((row.get("leg") or {}).get("retrace") or 0) >= legs.DEEP)


def action_words(d: dict) -> list:
    """THE ACTION WORD per minute (Jarvis v3; JARVIS-REVIEW-2026-10-31 §3.1, P0 #1-3): the leg's word is a STATE, this is
    the word she acts on -> [{"word", "lean", "since", "count", "why"}] per minute of d["mins"] ([] when the leg read has
    no rows for this frame). Causal: minute i reads minutes <= i only.
      candidate  the leg's word, decided by the count: TREND -> TREND at WITH >= AGAINST + ACT_LEAD, else HOLD; the
                 pause (the leg's HOLD or WATCH, or a latched PALAT? whose condition is gone) -> HOLD at WITH >= AGAINST,
                 else WATCH -- WATCH only when the count has turned (ruling 2, 1 Nov: HOLD and WATCH are the same action
                 for a holder; the leg's risk items ride along as a chip, "HOLD · 2 risk"); PALAT? -> PALAT? while its
                 condition holds; NO LEG / ROTATION as themselves; NO TRADE (quiet / can't see, reads.notrade) when there
                 is no TREND leg; RANGE (A229, no arrow) when the lean flips inside the writers' box (_box), held while
                 the box holds -- a range day's swings re-leaned the word 11 times in 63 min on 4 Nov; once PALAT?
                 is said, the pause stays PALAT? until the leg makes a new extreme (5 Nov, its wrong-line's promise)
      changes    only at her 3-min closes, on the same candidate at ACT_CLOSES consecutive closes; PALAT? also at one
                 close once 0.35 of the leg is back (legs.DEEP). At once: PALAT (the lean flipped; RANGE inside the
                 box), and a push against
                 the lean that BROKE / TRAPPED the wall behind (legs.wall_behind_broke, the leg's own risk rule: TREND /
                 HOLD -> WATCH). CAN'T SEE is the call's (a clock). After the chain's scheduled end (CHAIN_END, 15:30;
                 the futures trade to 15:40) no close changes it: only those two at-once events do (I2)
      the open   before 10:00 the word is OPENING (NO LEG before the first leg), no arrow: the lean is its own chip; with
                 nothing held yet (the frame's first minute, the open's end at 10:00) the candidate is said at once --
                 without the two-close wait, never without the count
    `why` = the rule that set the word · WITH n · AGAINST m (· a pending candidate, n of ACT_CLOSES closes)."""
    import legs
    mins = d["mins"]
    rows = (d.get("legs") or {}).get("rows") or []
    if len(rows) != len(mins) or any(r.get("t") != t for r, t in zip(rows, mins)):
        return []
    nt = [None] * len(mins)
    for x in (d.get("reads") or {}).get("notrade") or ():
        for j, t in enumerate(mins):
            if x["from"] <= t <= x["to"]:
                nt[j] = x
    pushes = d.get("pushes") or []
    vote, spoken, out = None, set(), []
    word = rule = shown = since = pend = pq = pq_t = None
    for i, (t, row) in enumerate(zip(mins, rows)):
        m, raw, lean = _m(t), row["word"], row.get("lean") or 0
        if not lean and vote is None:
            vote = legs._jarvis_words(d) or [None] * len(mins)
        c = count(d, i, vote)
        W, A = c["with"], c["against"]
        g = row.get("leg") or {}
        brk = legs.wall_behind_broke(pushes, lean, m) if lean else None     # the leg's own rule (its risk item)
        box = _box(d, i, g) if m >= legs.OPEN_M and (raw == "PALAT" or word == "RANGE") else None   # A229
        # the candidate
        if m < legs.OPEN_M:
            cand = ("NO LEG", "NO LEG: no leg yet") if raw == "NO LEG" else ("OPENING", "OPENING: before 10:00, no word")
        elif box and (nt[i] or {}).get("why") != "can't see":    # the range guard: the lean flipped inside the writers'
            cand = ("RANGE", f"RANGE: {box}")    # box (a swing, not a reversal); RANGE holds while the box does, quiet or
                                                  # not (a quiet box is still one), never over CAN'T SEE
        elif nt[i] and g.get("quality") != "TREND" and raw != "PALAT":
            cand = ("NO TRADE", f"NO TRADE: quiet since {nt[i]['since']}" if nt[i]["why"] == "quiet"
                    else f"NO TRADE: can't see {nt[i]['from']}–{nt[i]['to']}")
        elif raw == "TREND":
            cand = (("TREND", f"TREND: with ≥ against + {ACT_LEAD}") if W >= A + ACT_LEAD
                    else ("HOLD", f"HOLD: a TREND leg, with < against + {ACT_LEAD}"))
        elif raw == "PALAT?" and _palat_cond(row):
            cand = ("PALAT?", "PALAT?: ≥ 3 risk items or FAST against")
        elif raw in ("HOLD", "WATCH", "PALAT?") and word == "PALAT?" and pq is not None and pq == g.get("extreme"):
            cand = ("PALAT?", f"PALAT?: said at {pq_t}, no new {'high' if lean > 0 else 'low'} past {_fmt(pq)}f since")
            # 5 Nov (docs/review-2026-11-05/JARVIS.md): the card's own wrong-line, "back to HOLD on a real new high past
            # X". The leg's latch lapsing in the same pause is not a new high (5 Nov NIFTY / SENSEX 14:44, SENSEX 10:29 /
            # 10:38: HOLD again with no new extreme, so the buyer line offered a new CE / PE)
        elif raw in ("HOLD", "WATCH", "PALAT?"):         # the pause (a latched PALAT? too): the count decides
            cand = (("HOLD", "HOLD: the pause, with ≥ against") if W >= A
                    else ("WATCH", "WATCH: the count turned, against > with"))
        else:
            cand = (raw, f"{raw}: the leg says {raw}")
        # the word
        new = None
        if m < legs.OPEN_M:
            new = cand
        elif word is None or word in ("OPENING", "NO LEG"):            # nothing held: the candidate, count and all
            new = (cand[0], f"{cand[1]} · at once (nothing held yet)")
        elif raw == "PALAT":                                             # at once: a lean flip, or inside the box RANGE
            new = (cand[0], cand[1] + " · at once") if cand[0] == "RANGE" else ("PALAT", "PALAT: the lean flipped")
        elif t > CHAIN_END:                                              # I2: the chain ends 15:30 by schedule: the
            pend = None                                                  # word holds; only PALAT / the wall behind
        elif (m - legs.START_M) % 3 == 2:                                # her 3-min close
            if cand[0] == word:
                pend = None
            else:
                again = bool(pend) and pend[0] == cand[0]
                pend = [cand[0], cand[1], pend[2] + 1 if again else 1, pend[3] if again else t]
                if pend[2] >= ACT_CLOSES:
                    new = (cand[0], f"{cand[1]} · {ACT_CLOSES} closes")
                elif cand[0] == "PALAT?" and (g.get("retrace") or 0) >= legs.DEEP:
                    new = ("PALAT?", f"PALAT?: retrace {g['retrace']:.2f} ≥ {legs.DEEP} of the leg")
        if new:
            word, rule, pend = new[0], new[1], None
        if word != "PALAT?":
            pq = pq_t = None
        elif pq is None:                                                 # the leg's extreme when PALAT? was said
            pq, pq_t = g.get("extreme"), t
        # EXIT-class, at once, any minute: a push against the lean BROKE / TRAPPED the wall behind. Spoken once per push;
        # a break landing while the word is not a holding word waits in its window (never lost); a cautious word has it
        if brk is not None and id(brk) not in spoken and m >= legs.OPEN_M and g.get("quality") == "TREND":
            if word in ("TREND", "HOLD"):
                word, pend = "WATCH", None
                rule = (f"WATCH: the wall behind {ANSWER_EN.get(brk['ans'])} — {brk['t']} push {ARR[brk['dir']]}"
                        + (f" {_fmt(brk['k'])}s {brk.get('side') or ''}" if brk.get("k") is not None else ""))
                spoken.add(id(brk))
            elif word in ("WATCH", "PALAT?", "PALAT"):
                spoken.add(id(brk))
        if said(word, lean) != shown:
            shown, since = said(word, lean), t
        nr = len(row.get("risk") or ())                                  # the leg's risk items ride along as a chip
        why = (f"{rule}" + (f" · {nr} risk" if nr else "") + f" · WITH {W} · AGAINST {A}"
               + (f" · {pend[0]} at {pend[3]} ({pend[2]} of {ACT_CLOSES} closes)" if pend else "")
               + (f" · chain ends {CHAIN_END}: only PALAT / the wall behind change it" if t > CHAIN_END else ""))
        out.append({"word": word, "lean": lean, "since": since, "count": c, "why": why})
    return out


def sides_fuel(s):
    """The writers' fuel direction of one Sides slot -> 1 / -1 / None: REAL / BACKED by its fuel side, and SQUEEZE (the
    move's own writers covering) only while the other side is FLAT -- call writers covering with puts flat = ▲, the
    mirror ▼ (A176, decided as the trader: 29 Oct's afternoon driver, DAY §1). Both sides covering is not counted."""
    if not s or s.get("fuel_side") not in ("ce", "pe"):
        return None
    dr = 1 if s["fuel_side"] == "ce" else -1
    if s.get("word") in ("REAL", "BACKED"):
        return dr
    if s.get("word") == "SQUEEZE" and (s.get("p") if dr > 0 else s.get("c")) == "FLAT":
        return dr
    return None


def wf_push(ce, pe):
    """WRITER FLOW ±7 as writers' fuel -> 1 / -1 / None: a covering side <= -10L / 3 min while the other side is not
    covering against it (>= -2L), which holds DAY §5's two-leg UP (CE <= -10L with PE >= +10L) and adds the covering side
    alone (A176). Fuel only: the ±7 STATES (UP / PAUSED / BACK / RISK) keep the two-leg rule."""
    if ce is None or pe is None:
        return None
    return 1 if ce <= -WF_L and pe >= WF_STOP else -1 if pe <= -WF_L and ce >= WF_STOP else None


def _med(xs):
    """The face's median (jarvis2.html `med`): the sorted values' element at len // 2."""
    s = sorted(x for x in xs if x is not None and math.isfinite(x))
    return s[len(s) // 2] if s else None


def _fmt(x):
    """Math.round(x).toLocaleString("en-IN"): 1,23,456."""
    n = int(math.floor(x + 0.5))
    s = str(abs(n))
    if len(s) > 3:
        h, s = s[:-3], s[-3:]
        while len(h) > 2:
            h, s = h[:-2], h[-2:] + "," + s
        s = h + "," + s
    return ("-" if n < 0 else "") + s


def _sgn(x):
    return ("+" if x >= 0 else "−") + _fmt(abs(x))


def reads(d: dict) -> dict:
    """The per-minute reads of one frame (causal: minute i reads minutes <= i only) -> {speed, signs, sync, writers,
    manage, trade, notrade}. The face renders these; its own JS reads are only the fallback for old JSON files."""
    mins, N = d["mins"], len(d["mins"])
    fut, fo, fhi, flo, tl = d["fut"], d["fo"], d["fhi"], d["flo"], d["timeline"]
    flow = d.get("flow") or d["delta"]
    vol = [f if f is not None else v for f, v in zip(d["fvol"], d.get("vol") or [None] * N)]
    bar = d.get("bar") or 500
    ix = {m: i for i, m in enumerate(mins)}

    def s3(k):
        """The signed 3-min flow ending at minute k; None when any of its minutes is missing (never a zero)."""
        xs = flow[k - 2:k + 1] if k >= 2 else [None]
        return None if any(x is None for x in xs) else sum(xs)

    # SPEED: |3-min delta| against its own median so far [I]; for the first 10 bars against rank_build's same-slot
    # median (Task 5: data/rank, days before today, RANK_3OF5), so it reads from 09:17 instead of "?"
    ref = (d.get("ctx") or {}).get("absd")
    speed, hist = [], []
    for i in range(N):
        x3 = s3(i)
        m = _med(hist) if len(hist) >= 10 else None
        r5 = None if m is not None or not ref else ref.get(_m(mins[i]) // 15)
        m = m if r5 is None else r5 * RANK_3OF5
        x = abs(x3) / m if x3 is not None and m else None
        speed.append({"x": None if x is None else round(x, 2), "dir": None if x3 is None else (1 if x3 >= 0 else -1),
                      "word": "?" if x is None else "FAST" if x >= FAST else "SLOW" if x <= SLOW else "NORMAL", "d3": x3,
                      "why": None if x is not None else ("flow missing (Dext and the book)" if x3 is None and i >= 2
                                                          else "warming up: needs 10 bars of history"
                                                          + ("" if ref else " · no rank reference"))})
        if r5 is not None and x is not None:
            speed[-1]["src"] = "rank"
        if x3 is not None:
            hist.append(abs(x3))

    # ALL 3 IN SYNC: the three moved >= 10 / 25 / 35 pts the same way in 5 min [I]
    def sync_at(i):
        if i < 5 or not d.get("bnf"):
            return None
        nf = fut if d.get("idx") in (None, "NIFTY") else (d.get("nf") or [None] * N)   # N is NIFTY on every frame (spec
        ch = [None if a[i] is None or a[i - 5] is None else round(a[i] - a[i - 5], 2)   # §4: it read the frame's own future)
              for a in (nf, d["bnf"], d["sx"])]
        if None in ch:
            return {"dir": None, "ch": ch}
        up, dn = all(c >= n for c, n in zip(ch, SYNC_PTS)), all(c <= -n for c, n in zip(ch, SYNC_PTS))
        return {"dir": 1 if up else -1 if dn else 0, "ch": ch}
    sync = [sync_at(i) for i in range(N)]

    # Sides (the Board's options-side fuel) and WRITER FLOW ±7 (her 29 Oct asks), reused as the face read them
    def sides_at(i):
        s = None
        for x in d.get("sides") or ():
            if x.get("t") and x["t"] <= mins[i]:
                s = x
            elif x.get("t") and x["t"] > mins[i]:
                break
        return s

    def opt_fuel(i):
        s = sides_at(i)
        return s if sides_fuel(s) else None

    def wf(i):
        c, p = (d.get("wf_ce") or [None] * N)[i], (d.get("wf_pe") or [None] * N)[i]
        return None if c is None or p is None else (c, p)

    def wf_fuel(i):
        w = wf(i)
        return None if not w else 1 if w[0] <= -WF_L and w[1] >= WF_L else -1 if w[1] <= -WF_L and w[0] >= WF_L else None

    def wf_leg(i):
        """G3 (30 Oct): the ±7 leg's direction and the side that drives it -> (dir, "both" | "calls" | "puts") or None.
        Both: DAY §5's two-leg rule (CE <= -L with PE >= +L, mirror ▼). One side alone: its covering (CE <= -L while PE
        neither builds a leg nor covers against it) or its building (PE >= +L while CE neither covers a leg nor adds
        against it); mirror ▼. 29 Oct (+236 pts) had 18 two-leg minutes and the state read UP for 33 in all."""
        w = wf(i)
        if not w:
            return None
        c, p = w
        if c <= -WF_L and p >= WF_L:
            return 1, "both"
        if p <= -WF_L and c >= WF_L:
            return -1, "both"
        if c <= -WF_L and WF_STOP <= p < WF_L:
            return 1, "calls"                                    # call writers covering, puts not covering against
        if p <= -WF_L and WF_STOP <= c < WF_L:
            return -1, "puts"
        if p >= WF_L and -WF_L < c <= -WF_STOP:
            return 1, "puts"                                     # put writers adding, calls not adding against
        if c >= WF_L and -WF_L < p <= -WF_STOP:
            return -1, "calls"
        return None

    # WRITER FLOW ±7 states (DAY §5): UP / DOWN when a leg starts (>= 6 min after the last), PAUSED when its driving
    # side(s) stop -- the covering side back over -2L, the building side under half its leg peak -- BACK when the fuel
    # returns, RISK when the pause meets a 3-min delta >= 2x its day median against within 9 min. `legs` says which side
    # drives (G3). G2 (30 Oct): RISK is an event, not a state for the rest of the day (29 Oct it sat 10:38-12:50 on a day
    # that closed +236; 28 Oct from 13:19 to the close). It ends ("RISK OFF", back to PAUSED) at a new extreme the leg's
    # way, or after RISK_HOLD minutes unless price has gone RISK_CONF of a strike step against the leg since.
    writers, seen = [], []
    on, legs, peak, last_on, paused, paused_at, warned, state = None, None, 0.0, -99, False, -99, False, None
    ext, risk_at, risk_px, risk_ext = None, None, None, None
    step = d.get("step") or 50
    for i in range(N):
        dd, w, ev = s3(i), wf(i), None
        if dd is not None:
            seen.append(abs(dd))
        row = {"state": None, "dir": None, "ce": None if w is None else w[0], "pe": None if w is None else w[1], "ev": None,
               "push": None if w is None else wf_push(*w), "legs": legs}
        hi_, lo_ = fhi[i] if fhi[i] is not None else fut[i], flo[i] if flo[i] is not None else fut[i]
        if on and hi_ is not None and lo_ is not None:
            ext = (max(ext, hi_) if on > 0 else min(ext, lo_)) if ext is not None else (hi_ if on > 0 else lo_)
        if state == "RISK" and risk_at is not None:
            new_ext = risk_ext is not None and ext is not None and on * (ext - risk_ext) > 0
            held_against = fut[i] is not None and risk_px is not None and on * (fut[i] - risk_px) <= -RISK_CONF * step
            if new_ext or (i - risk_at >= RISK_HOLD and not held_against):
                state, ev, risk_at = "PAUSED", "RISK OFF", None
        if i < 3 or w is None:
            row.update(state=state, dir=on, ev=ev)
            writers.append(row)
            continue
        lg = wf_leg(i)
        f, up = (lg[0] if lg else None), (on or 0) > 0
        if f and on != f and i - last_on >= 6:
            on, legs, peak, last_on, paused, warned = f, lg[1], (w[1] if f > 0 else w[0]), i, False, False
            state = ev = "UP" if f > 0 else "DOWN"
            ext, risk_at = (hi_ if f > 0 else lo_), None
        elif on:
            if f == on and paused:                             # a new pause after this may warn again: RISK expires now
                paused, warned, ev, legs, risk_at = False, False, "BACK", lg[1], None
                state = "UP" if on > 0 else "DOWN"
            else:
                if not paused and lg and lg[0] == on and lg[1] == "both":
                    legs = "both"                                # the other side joined: a two-leg push from here
                build, cover = (w[1], w[0]) if up else (w[0], w[1])
                peak = max(peak, build)
                med = sorted(seen)[len(seen) // 2] if len(seen) >= 10 else None
                hit = dd is not None and bool(med) and on * dd <= -RISK_X * med
                covers = legs == "both" or legs == ("calls" if up else "puts")     # the leg's covering side drives it
                builds = legs == "both" or legs == ("puts" if up else "calls")     # its building side drives it
                stopped = (not covers or cover >= WF_STOP) and (not builds or build < peak / 2)
                if not paused and stopped and (dd is None or on * dd <= 0):
                    paused, paused_at = True, i
                    if not hit or warned:                    # (a hit already warned of reads as the pause it is)
                        state = ev = "PAUSED"
                if paused and not warned and i - paused_at <= RISK_WIN and hit:
                    warned, state, ev = True, "RISK", "RISK"
                    risk_at, risk_px, risk_ext = i, fut[i], ext
                    row.update(d3=dd, x=round(abs(dd) / med, 1))
        row.update(state="BACK" if ev == "BACK" else state, dir=on, ev=ev, legs=legs)
        writers.append(row)

    # TOP / BOTTOM SIGNS n/3 at a fresh 30-min extreme, on her 3-min bars from 09:15; spoken at 2/3, noted (not called)
    # while ANY fuel still drives into the extreme (DAY §8 item 3)
    def bar3(b):
        a = b - 2
        if a < 0:
            return None
        ds, vs = flow[a:b + 1], vol[a:b + 1]
        h, lo = max(fhi[a:b + 1]), min(flo[a:b + 1])
        v = None if None in vs else sum(vs)
        return {"a": a, "b": b, "o": fo[a], "c": fut[b], "h": h, "l": lo, "d": None if None in ds else sum(ds), "v": v,
                "eff": None if v is None else v / max(h - lo, 0.5)}

    def known_at(p):
        """The minute index from which a push's answer is known (the face's ix(held_at || am) + 1), or None."""
        k = ix.get(p.get("held_at") or p.get("am") or "")
        return None if k is None else k + 1

    miss = set(d.get("chain_missing") or ())

    def break_at(p):
        """From when a BROKEN counts as fuel (A176, decided as the trader): its push minute when the answer was read late
        through a chain hole (a chain-missing minute between the push and its confirmation), else the minute it became
        known -- the market broke it then; only our reading was late."""
        conf = p.get("held_at") or p.get("am")
        if conf and p["t"] in ix and any(p["t"] < m_ <= conf for m_ in miss):
            return ix[p["t"]] + 1
        return known_at(p)

    pushes = [p for p in d.get("pushes") or () if not p.get("artifact")]
    signs, effs = [], []
    for b in range(2, N, 3):
        B = bar3(b)
        m = _med(effs) if len(effs) >= 6 else None
        if B["eff"] is not None:
            effs.append(B["eff"])
        lo0 = max(0, B["a"] - 30)
        if B["a"] - lo0 < 10:
            continue
        hi30, lo30 = max(fhi[lo0:B["a"]]), min(flo[lo0:B["a"]])
        for is_high in (True, False):
            if (B["h"] < hi30) if is_high else (B["l"] > lo30):
                continue
            sg, P = [], [q for q in (bar3(b - 6), bar3(b - 3)) if q]
            if B["d"] is not None and ((B["c"] < B["o"] and B["d"] > 0) if is_high else (B["c"] > B["o"] and B["d"] < 0)):
                sg.append(f"{'red candle, green delta' if is_high else 'green candle, red delta'} {_sgn(B['d'])}")
            if m and B["eff"] is not None and B["eff"] >= 2 * m:
                sg.append(f"absorption: {_fmt(B['v'])} lots / {B['h'] - B['l']:.0f} pts (effort ×{B['eff'] / m:.1f})")
            pk = max([(1 if is_high else -1) * q["d"] for q in P if q["d"] is not None] + [0])
            if pk > 0 and B["d"] is not None and (B["d"] if is_high else -B["d"]) < pk / 2:
                sg.append("exhaustion: delta " + " → ".join(_sgn(q["d"]) for q in P if q["d"] is not None) + f" → {_sgn(B['d'])}")
            if len(sg) < 2:
                continue                                  # one sign alone is noise: it speaks at 2 of 3
            way, sd = ("▲" if is_high else "▼"), (1 if is_high else -1)
            row, drive = tl[b] or {}, []
            fu = row.get("fuel")
            spent = any(r.get("khatam") and r["dir"] == way and abs(r["lots"]) >= 2 * bar and r["khatam"] in ix
                        and 0 <= b - ix[r["khatam"]] <= 10 for r in d.get("runs") or ())
            if row.get("fuel_state") == "LIVE" and fu and (fu["dir"] == "▲") == is_high and not spent:
                drive.append(f"fut {MEAN.get(fu['meaning'], fu['meaning'])} {_sgn(fu['lots'])}")
            of = opt_fuel(b)
            if of and (of["fuel_side"] == "ce") == is_high:
                drive.append(f"{'call' if of['fuel_side'] == 'ce' else 'put'} writers covering · Sides {of['word']}")
            w = wf(b)
            if wf_fuel(b) == sd:
                drive.append(f"writers ±7 {way}: CE {H._l(w[0])} · PE {H._l(w[1])}")
            elif w and wf_push(*w) == sd:
                drive.append(f"{'call' if is_high else 'put'} writers covering ±7: {'CE' if is_high else 'PE'} "
                             f"{H._l(w[0] if is_high else w[1])} / 3 min")
            elif w and (w[1] if is_high else w[0]) >= WF_L:
                drive.append(f"{'put writers lifting the floor: PE' if is_high else 'call writers lowering the cap: CE'} "
                             f"{H._l(w[1] if is_high else w[0])} / 3 min")
            brk = [p for p in pushes if p["dir"] == sd and p.get("held") == "TOOT" and known_at(p) is not None
                   and known_at(p) <= b + 1 and 0 <= b + 1 - break_at(p) <= 10]
            if brk:
                drive.append(f"BROKEN {_fmt(brk[-1]['k'])}s {brk[-1]['side']} ({brk[-1].get('held_at') or brk[-1]['am']})")
            signs.append({"b": b, "t": mins[b], "at": mins[b + 1] if b + 1 < N else hm(_m(mins[b]) + 1), "isHigh": is_high,
                          "n": len(sg), "items": sg, "driving": bool(drive), "drive": drive, "px": B["h"] if is_high else B["l"],
                          "speed": speed[b]})

    # MANAGE: after each of her triggers, at her 3-min closes for 45 min; on change, >= 6 min apart; at most 4 lines.
    # Judged against price FIRST (GAPS §1, the -120 pts HOLD): AGAINST YOU at <= -15 pts whatever else says.
    def band(i):
        w_, s_ = d["vwap"][i], d["sd"][i]
        return [("d2", w_ - 2 * s_), ("d1", w_ - s_), ("VWAP", w_), ("u1", w_ + s_), ("u2", w_ + 2 * s_)]

    def trail_band(i, dr):
        bs = band(i)
        got = next((x for x in bs if x[1] > fut[i] + 3), None) if dr < 0 else \
            next((x for x in reversed(bs) if x[1] < fut[i] - 3), None)
        return None if got is None else [got[0], round(got[1], 1)]

    def judge(pts, withm, against):
        if pts <= -MANAGE_PTS or (pts < 0 and len(against) >= 2):
            return "AGAINST YOU"
        if pts >= MANAGE_PTS and against:
            return "BOOK / TRAIL TIGHT"
        if pts >= MANAGE_PTS and withm:
            return "HOLD"
        return None

    def sides_of(b, dr):
        withm, against = [], []
        sp, sy, row = speed[b], sync[b], tl[b] or {}
        if sp["word"] == "FAST":
            (withm if sp["dir"] == dr else against).append(f"speed {ARR[sp['dir']]} ×{sp['x']:.1f}")
        if sy and sy["dir"]:
            (withm if sy["dir"] == dr else against).append(f"all 3 {ARR[sy['dir']]}")
        fu = row.get("fuel")
        if row.get("fuel_state") == "LIVE" and fu:
            (withm if (fu["dir"] == "▲") == (dr > 0) else against).append(f"fuel {MEAN.get(fu['meaning'], fu['meaning'])}")
        wff = wf_push(*wf(b)) if wf(b) else None
        if wff:
            (withm if wff == dr else against).append(f"writers ±7 {ARR[wff]}")
        of = opt_fuel(b)
        if of:
            (withm if (of["fuel_side"] == "ce") == (dr > 0) else against).append(
                f"{'call' if of['fuel_side'] == 'ce' else 'put'} writers covering")
        sg = next((s for s in signs if not s["driving"] and s["b"] == b and s["isHigh"] == (dr > 0)), None)
        if sg:
            against.append(f"{'top' if sg['isHigh'] else 'bottom'} signs {sg['n']}/3")
        return withm, against

    def manage_of(z, ti, dr, stop_b, cap, tag):
        was, last_at, n, out = None, -99, 0, []
        for b in range(ti + 2, stop_b):
            if n >= cap:
                break
            if (b + 1) % 3:
                continue                                  # read at her 3-min closes
            pts = dr * (fut[b] - z["px"])
            withm, against = sides_of(b, dr)
            st = judge(pts, withm, against)
            if not st or st == was or b - last_at < MANAGE_GAP:
                continue
            was, last_at, n = st, b, n + 1
            out.append(dict({"at": mins[b + 1] if b + 1 < N else hm(_m(mins[b]) + 1), "b": b, "t": z["t"][:5],
                             "side": z["side"], "px": z["px"], "st": st, "pts": round(pts, 1), "trail": trail_band(b, dr),
                             "with": withm, "against": against, "note": "guidance only: you place and move your own stop"},
                            **tag))
        return out

    triggers = [z for z in d.get("zone") or () if not z.get("kind") and z.get("px") is not None and z["t"][:5] in ix]
    manage = []
    for z in triggers:
        ti, dr = ix[z["t"][:5]], (-1 if z["side"] == "SELL" else 1)
        manage += manage_of(z, ti, dr, min(N, ti + MANAGE_WIN), 4, {"subject": "zone trigger"})
    # Task 5: her open marked trade is the subject (day_state's hold_trades: entry t0, CE / PE, long / short), from the
    # minute it was known (t0, or `at` when marked later) to her exit; judged against price the same way, no 4-line cap
    # [I] (a trade lasts hours, a trigger's window 45 min). The zone trigger stays the labelled fallback.
    mine = []
    for tr in (d.get("ctx") or {}).get("marked") or ():
        t0, ex = str(tr.get("t0") or "")[:5], str(tr.get("exit_t") or "")[:5]
        at = datetime.datetime.fromtimestamp(tr["at"], fold.IST) if isinstance(tr.get("at"), (int, float)) else None
        known = t0 if at is None else max(t0, at.strftime("%H:%M")) if at.strftime("%Y-%m-%d") == d.get("day") else None
        ti = next((j for j, m_ in enumerate(mins) if known and m_ >= known), None)
        if ti is None or tr.get("side") not in ("CE", "PE"):
            continue
        dr = (1 if tr["side"] == "CE" else -1) * (-1 if tr.get("role") == "short" else 1)
        z = {"t": t0, "side": "BUY" if dr > 0 else "SELL", "px": fut[ix.get(t0, ti)], "ti": ti, "dr": dr,
             "end": next((j for j, m_ in enumerate(mins) if ex and m_ >= ex), N),
             **{k: tr.get(k) for k in ("id", "role", "k", "p0")}, "opt": tr["side"]}
        mine.append(z)
        manage += manage_of(z, ti, dr, z["end"], N, {"subject": "her trade", "id": z["id"]})

    # the LAST TRIGGER card, per minute: the points now, the last MANAGE word said, re-judged against price now
    trade = []
    for i in range(N):
        mt = next((q for q in reversed(mine) if q["ti"] <= i < q["end"]), None)
        if mt is not None:
            pts = mt["dr"] * (fut[i] - mt["px"])
            said = next((m_ for m_ in reversed(manage) if m_.get("id") == mt["id"] and m_["b"] + 1 <= i), None)
            trade.append({"subject": "her trade", **{k: mt[k] for k in ("id", "t", "side", "opt", "role", "k", "p0", "px")},
                          "band": None, "pts": round(pts, 1), "age": i - mt["ti"],
                          "st": "AGAINST YOU" if pts <= -MANAGE_PTS else (said or {}).get("st"),
                          "said": (said or {}).get("st"), "window": True, "trail": trail_band(i, mt["dr"])})
            continue
        z = next((q for q in reversed(triggers) if ix[q["t"][:5]] <= i), None)
        if z is None:
            trade.append(None)
            continue
        dr = -1 if z["side"] == "SELL" else 1
        pts, age = dr * (fut[i] - z["px"]), i - ix[z["t"][:5]]
        said = next((m_ for m_ in reversed(manage) if m_["subject"] == "zone trigger" and m_["t"] == z["t"][:5]
                     and m_["side"] == z["side"] and m_["b"] + 1 <= i), None)
        st = "AGAINST YOU" if pts <= -MANAGE_PTS else (said or {}).get("st")
        trade.append({"subject": "zone trigger", "t": z["t"][:5], "side": z["side"], "px": z["px"], "band": z.get("band"), "pts": round(pts, 1), "age": age,
                      "st": st, "said": (said or {}).get("st"), "window": age < MANAGE_WIN, "trail": trail_band(i, dr)})

    # NO TRADE: 20 quiet minutes (no break, no fuel, no trigger, writers not pushing) -> quiet; a data hole -> can't see
    loud = {1}
    for p in pushes:
        if p.get("ans") in SAID and known_at(p) is not None:
            loud.add(known_at(p))
    big = set()                                   # a run speaks once its lots so far reach 2x the bar, and at its KHATAM
    for i in range(N):
        fu = (tl[i] or {}).get("fuel")
        if fu and abs(fu["lots"]) >= 2 * bar and (fu["start"] not in big or fu["khatam"]):
            big.add(fu["start"])
            loud.add(i + 1)
    for f in d.get("fights") or ():
        for t, word, _ in f["stamps"]:
            if t in ix and (word.startswith(("NAYA", "PIN")) or (word == "DEEWAR" and f["id"] > 0)):
                loud.add(ix[t] + 1)
    loud.update(ix[z["t"][:5]] + 1 for z in triggers)
    loud.update(s["b"] + 1 for s in signs if not s["driving"])
    loud.update(m_["b"] + 2 for m_ in manage if m_["st"] != "HOLD" and m_["subject"] == "zone trigger")   # the tool's own
    loud.update(i + 1 for i, w in enumerate(writers) if w["ev"] in ("UP", "DOWN", "RISK"))
    was = None
    for i in range(N):
        s = opt_fuel(i)
        on_ = s["fuel_side"] if s else None
        if on_ and on_ != was:
            loud.add(i + 1)
        was = on_
    blind = set()
    fs = d.get("flow_src") or [None] * N
    for a, b_ in d.get("holes") or ():               # a fill replay (31 Oct) has a hole's minutes back -- fut from the tape,
        blind.update(i for i, m_ in enumerate(mins)   # OI from the chain backfill: blind there only if the flow is gone too
                     if a[:5] <= m_ <= b_[:5] and not (d.get("fill") and fs[i]))
    blind.update(ix[m_] for m_ in d.get("chain_missing") or () if m_ in ix)
    nt, last_loud = [None] * N, 0
    for i in range(N):
        if i in blind:
            nt[i] = ("can't see", mins[i])
        if i in loud:
            last_loud = i
            continue
        if nt[i] is None and (tl[i] or {}).get("fuel_state") != "LIVE" and writers[i]["state"] not in ("UP", "DOWN", "BACK") \
                and i - last_loud >= QUIET_MIN:
            nt[i] = ("quiet", mins[last_loud])
    notrade, i = [], 0
    while i < N:
        if nt[i] is None:
            i += 1
            continue
        j = i
        while j + 1 < N and nt[j + 1] is not None and nt[j + 1][0] == nt[i][0]:
            j += 1
        notrade.append({"from": mins[i], "to": mins[j], "why": nt[i][0], "since": nt[i][1],
                        "ends": "FUEL >= 500 lots / 5 min, writers ±7 pushing, or a BREAK" if nt[i][0] == "quiet"
                        else "the record resumes"})
        i = j + 1
    return {"speed": speed, "signs": signs, "sync": sync, "writers": writers, "manage": manage, "trade": trade,
            "notrade": notrade}


# ---- Jarvis v3 Task 5: what the tool already measures, read (HOW MUCH, WHERE, EXPRESSION, her trade, the cross-checks) --

def cpr(h, l, c):
    """algo_ai's central pivot range on the prior day's H / L / C: pivot (H+L+C)/3, bc (H+L)/2, tc 2·pivot − bc, width
    |tc − bc|; narrow at <= CPR_NARROW of that day's range [I]."""
    p, bc = (h + l + c) / 3, (h + l) / 2
    w = abs(2 * p - 2 * bc)
    return {"pivot": round(p, 2), "bc": round(bc, 2), "tc": round(2 * p - bc, 2), "w": round(w, 2),
            "kind": "narrow" if w <= CPR_NARROW * (h - l) else "wide"}


def rv(closes):
    """server._rv5's realized vol, reproduced (the server is never imported): close-to-close LOG returns of the sessions'
    last closes, SAMPLE sd (n − 1), x sqrt(252) -> a fraction (0.098 = 9.8), or None under RV_MIN returns (noise)."""
    r = [math.log(b / a) for a, b in zip(closes, closes[1:]) if a > 0 and b > 0]
    if len(r) < RV_MIN:
        return None
    mu = sum(r) / len(r)
    return math.sqrt(sum((x - mu) ** 2 for x in r) / (len(r) - 1)) * math.sqrt(RV_YEAR)


@functools.lru_cache(maxsize=16)          # ponytail: per process; a prior session recover_tape refills mid-day reads at a restart
def _prior(bt, tape_dir, idx, day):
    """The sessions before `day`, from the record -- levels.fetch_daily is REST, this never touches the network ->
    ({levels, pd, pw, cpr, rv, vp, vp_why}, notes). The futures' 1-min sessions (data/backtest through
    confluence_log.session, the zone machine's own series, so every level here is `f`): PD = the prior session's H / L / C
    from its bars <= 15:15 (the CAS rule, levels.LAST_CONTINUOUS), PW = the prior ISO week's H / L, each only on a
    contract still trading on `day` (THE ROLL: the expired future is off by the calendar spread, and says so);
    levels.static_levels on them; CPR on PD; RV on the last RV_N closes; the prior session's POC / VAH / VAL
    (prints.profile on GoCharting's tape). `bt` / `tape_dir` (squeeze_score.BT, tape_log.DIR) only key the cache."""
    import levels
    import prints
    import squeeze_score
    import tape_log
    out = {"levels": {}, "pd": None, "pw": None, "cpr": None, "rv": None, "vp": None, "vp_why": None}
    prev = sorted(x for x in (os.path.basename(p)[4:14] for p in squeeze_score._paths(idx)) if x < day)
    if not prev:
        out["vp_why"] = "no prior session"
        return out, (f"levels / CPR / RV: could not check — no futures session before {day} in data/backtest",)
    S, notes = {x: confluence_log.session(idx, x) for x in prev[-12:]}, []

    def live(x):                                     # the session's bars are this contract's
        return S.get(x) is not None and not (S[x]["expiry"] and S[x]["expiry"] < day)
    x = prev[-1]
    bs = [b for b in S[x]["ones"] if b["t"] <= levels.LAST_CONTINUOUS] if live(x) else []
    if not bs:
        notes.append(f"PD levels / CPR: could not check — fut_{x}.json is "
                     + (f"the future that expired {S[x]['expiry']}: another contract" if S.get(x) and not live(x)
                        else "without 1-min bars to 15:15"))
        out["vp_why"] = "the prior day was not read"
    else:
        out["pd"] = {"date": x, "h": max(b["h"] for b in bs), "l": min(b["l"] for b in bs), "c": bs[-1]["c"]}
        out["cpr"] = cpr(out["pd"]["h"], out["pd"]["l"], out["pd"]["c"])
        vp = prints.prior_levels([(x, tape_log.read_bars(x, idx))])
        out["vp"], out["vp_why"] = (vp[0] if vp else None), (None if vp else f"no GoCharting tape for {x}")
    wk, weeks = datetime.date.fromisoformat(day).isocalendar()[:2], {}
    for y in prev[-12:]:
        weeks.setdefault(datetime.date.fromisoformat(y).isocalendar()[:2], []).append(y)
    pk = max((k for k in weeks if k < wk), default=None)
    ok = [y for y in weeks.get(pk) or () if live(y)]
    if ok:
        pb = [b for y in ok for b in S[y]["ones"] if b["t"] <= levels.LAST_CONTINUOUS]       # the CAS rule, as PD
        out["pw"] = {"h": max(b["h"] for b in pb), "l": min(b["l"] for b in pb), "start": ok[0]} if pb else None
    if pk is None or len(ok) < len(weeks[pk]):
        notes.append("PW levels: could not check — no session of the prior week on this contract" if not ok else
                     f"PW levels from {len(ok)} of {len(weeks[pk])} sessions: "
                     + ", ".join(y for y in weeks[pk] if y not in ok) + " another contract")
    out["levels"] = {v["kind"]: v["px"] for v in levels.static_levels({"pd": out["pd"], "pw": out["pw"]})}
    closes = [S[y]["ones"][-1]["c"] for y in prev[-RV_N:] if S.get(y) and S[y]["ones"]]
    out["rv"] = rv(closes)
    if out["rv"] is None:
        notes.append(f"RV: could not check — {len(closes)} cached sessions before {day}, it needs {RV_MIN + 1}")
    return out, tuple(notes)


def _best(r):
    """A FADE / RIDE confluence row's closest bar: its three checks at the bar with the most ✓ (FADE-D's are its own)."""
    keys = {"FADE": ("zone", "oi", "flow"), "RIDE": ("loc", "oi", "flow")}.get(r.get("setup"))
    bs = [b for b in r.get("bars") or () if isinstance(b, dict)] if keys else []
    if not bs:
        return None
    b = max(bs, key=lambda b: sum(bool((b.get(k) or {}).get("ok")) for k in keys))
    return " ".join(f"{k.upper()} {'✓' if (b.get(k) or {}).get('ok') else '✗'}" for k in keys) + f" {b.get('t') or ''}".rstrip()


def _context(day, idx, upto, cp, snaps, step, memo=None):
    """Task 5: the reads the tool already has and Jarvis never consumed, gathered once per build from the record (no
    network, nothing written) -> the frame's `ctx`, a dict calls() never cuts: every per-minute part is keyed "HH:MM" or
    carries its time, so call() at minute i reads only what was known by then. _prior (PD / PW / CPR / RV / the prior
    POC), trademap.em (the 09:20 straddle), the chain's ATM read per minute (premium, IV, chain_metrics.max_pain),
    frame_v2.dte, rank_build's reference (the speed warm-up), THE READ / DECODE logs, confluence_log's rows, the
    decoder's BADA PRINTs, the fast VPIN, her marked trades (day_state's file, read only). An absent source -> `notes`."""
    import json
    import chain_metrics
    import day_state
    import decoder_log
    import frame_v2
    import sensex_flow
    import squeeze_score
    import tape_log
    import trademap
    pr, pn = _prior(squeeze_score.BT, tape_log.DIR, idx, day)
    ctx = dict(pr, notes=list(pn))
    notes = ctx["notes"]
    rows = trademap.snaps(_rows(cp), upto - 1)
    ctx["em"], ctx["em_why"] = trademap.em(rows, day) if rows else (None, "no chain row 09:20–09:30")
    if ctx["em"] is None and upto - 1 >= 9 * 60 + 30:
        notes.append(f"EM: could not check — {ctx['em_why']}")
    ctx["dte"] = frame_v2.dte(day, next((r.get("expiry") for r in rows if r.get("expiry")), None))
    ctx["opt"] = {}
    om, on = (memo or {}).get("opt") or {}, {}       # Task 6: minute -> (its snapshot, step, the read): a pure read of it
    for ts, s in snaps.items():
        if s.get("src") == "backfill":
            continue                                 # the REST morning carries OI only: no premium, no IV
        hit = om.get(ts)
        if hit and hit[0] is s and hit[1] == step:
            ctx["opt"][ts], on[ts] = hit[2], hit
            continue
        k = s.get("atm") or int(round(s["spot"] / step) * step)
        ce, pe = H._leg(s, k, "ce"), H._leg(s, k, "pe")
        iv = [x["iv"] * 100 for x in (ce, pe) if isinstance(x.get("iv"), (int, float)) and x["iv"] > 0]
        st = [r for r in s.get("strikes") or ()
              if all(isinstance((r.get(x) or {}).get("oi"), (int, float)) for x in ("ce", "pe"))]
        ctx["opt"][ts] = {"k": k, "ce": ce.get("ltp"), "pe": pe.get("ltp"), "iv": round(sum(iv) / len(iv), 2) if iv else None,
                          "mp": chain_metrics.max_pain(st) if st else None}
        on[ts] = (s, step, ctx["opt"][ts])
    if memo is not None:
        memo["opt"] = om | on                        # an earlier upto keeps the later minutes for the next
    ctx["rv_cal"], tr = _rv_cal(day, ctx["dte"])
    ctx["method"] = []                               # Task 6: how a number was made, never a gap (health.method)
    if ctx["rv"] is not None:                        # server._rv5's basis, said once (rule 7: say which)
        ctx["method"].append(f"RV {ctx['rv'] * 100:.1f} on 252 trading days (server._rv5's) × "
                             + (f"√(365/252 × {tr}/{ctx['dte'] + 1} trading / calendar days to expiry, today in both)"
                                if tr else "√(365/252)")
                             + f" = {ctx['rv'] * 100 * ctx['rv_cal']:.1f} on the chain IV's 365-day basis [I]")
    fi = "NIFTY" if sensex_flow.on(idx) else idx     # §1q: SENSEX's speed is NIFTY's flow, so NIFTY's yardstick
    try:
        with open(os.path.join(RANK_DIR, f"rank_ref_{fi}_{day}.json"), encoding="utf-8") as f:
            ab = ((json.load(f) or {}).get("flow") or {}).get("slot_absd") or {}
        ctx["absd"] = {int(k): v for k, v in ab.items() if isinstance(v, (int, float)) and v > 0} or None
    except (OSError, ValueError, AttributeError):
        ctx["absd"] = None
    if not ctx["absd"]:
        notes.append(f"speed warm-up: could not check — no rank reference for {fi} {day}")
    ctx["read"] = [{"t": r["t"], "word": r.get("word"), "dir": r.get("dir")}
                   for r in _rows(os.path.join(confluence_log.READ_DIR, f"read_{day}.jsonl"))
                   if r.get("idx") == idx and r.get("kind") == "mark" and isinstance(r.get("t"), str)]
    ctx["decode"] = [{"T": r["T"], "at": r.get("at"), "call": (r.get("call") or {}).get("text"),
                      "lines": [x for x in r.get("lines") or () if isinstance(x, str) and x.startswith(("CVD", "EFFORT"))
                                and "%" not in x],
                      "os": {k: (r.get("onesided") or {}).get(k) for k in ("type", "why", "up", "down", "flips", "crosses")}}
                     for r in _rows(os.path.join(DECODE_DIR, f"decode_{day}.jsonl"))
                     if r.get("idx") == idx and isinstance(r.get("T"), str)]
    for k, what in (("read", f"THE READ: could not check — no {idx} mark in read_{day}.jsonl"),
                    ("decode", f"DECODE and its §1o day type: could not check — no {idx} row in decode_{day}.jsonl")):
        if not ctx[k]:
            notes.append(what)
    ctx["conf"] = [dict({k: r.get(k) for k in ("setup", "t", "end", "side", "d", "entry", "at")}, best=_best(r))
                   for r in _rows(confluence_log.PATH) if r.get("day") == day and r.get("index") == idx]
    ev = decoder_log.read_events(day, idx)
    ctx["dec_n"] = len(ev)
    ctx["bada"] = [{k: e.get(k) for k in ("kind", "t", "time", "p", "side", "lots", "shown")} for e in ev
                   if e.get("kind") == "E1" and e.get("shown")]
    if not ev:
        notes.append(f"BADA PRINT: could not check — no decoder rows for {idx} on {day}")
    ctx["vpin"] = [[r["at"], r.get("vpin"), r.get("pct")] for r in _rows(VPIN_FAST)
                   if r.get("day") == day and isinstance(r.get("at"), str)]
    ctx["vix"], ctx["vix_why"] = _vix_rows(day, upto)
    if ctx["vix_why"]:
        notes.append(f"VIX: could not check — {ctx['vix_why']}")
    try:                                             # her marked trades: the file the server writes, read only (never
        with open(day_state.path_for(day), encoding="utf-8") as f:     # day_state.load, which renames a corrupt one)
            ds = json.load(f)
    except (OSError, ValueError):
        ds = {}
    ht = (ds.get("hold_trades") or ()) if isinstance(ds, dict) and ds.get("day") == day else ()
    ctx["marked"] = sorted((t for t in ht if isinstance(t, dict) and t.get("idx") == idx and t.get("t0")),
                           key=lambda t: t["t0"])
    return ctx


def _rv_cal(day, dte):
    """RV onto the chain IV's calendar basis -> (factor, trading days to expiry or None): realized variance accrues on
    trading days, IV spreads its variance over calendar ones, so RV_CAL (sqrt(365/252), exact with no weekend inside the
    option's life) x sqrt(trading / calendar days to expiry), today's session counted in both (the T6 review: left out,
    RV read ~6-15 of a percent low and tilted the grade to "rich"); RV_CAL itself on 0 DTE or an unknown expiry ->
    (factor, the trading days counted, today in).
    ponytail: weekdays only -- NSE holidays are not on the record, so a holiday inside the life counts one trading day
    too many; take the exchange calendar when one is kept."""
    if not dte or dte < 0:
        return RV_CAL, None
    d0 = datetime.date.fromisoformat(day)
    tr = 1 + sum(1 for j in range(1, dte + 1) if (d0 + datetime.timedelta(days=j)).weekday() < 5)
    return RV_CAL * math.sqrt(tr / (dte + 1)), tr


def _opt_at(d, t):
    """The chain's ATM read at minute t: that minute's, else the last within 3 min (a chain minute missing), else None."""
    o = (d.get("ctx") or {}).get("opt") or {}
    if t in o:
        return o[t]
    k = max((x for x in o if x <= t), default=None)
    return o[k] if k is not None and _m(t) - _m(k) <= 3 else None


def _vix_rows(day, upto):
    """vix_log's rows of `day` before minute `upto` (the build's causal cut), as [ts, vix, src] -> (rows, why): why names an
    empty file (a day before the recorder, or it never read), else None (rows only after upto: _vix_at says so)."""
    import vix_log
    rs = vix_log.rows(day)
    return ([[r["ts"], r["vix"], r.get("src")] for r in rs if _m(r["ts"]) < upto],
            None if rs else f"no row in vix_{day}.jsonl (India VIX is recorded by the server's 1-min read)")


def _vix_at(c, t):
    """HOW MUCH's VIX at minute t from ctx["vix"] (closed 1-min candles, ts <= t) -> (the line's words, the row). The read
    is the change, not the level (algo_ai T2): since the open when the day's first row is by VIX_OPEN_BY [I], else the
    first row's time, "started late"."""
    xs = [x for x in c.get("vix") or () if x[0] <= t]
    if not xs:
        why = f"no VIX row before {hm(_m(t) + 1)}"
        return f"VIX could not check — {why}", f"VIX: could not check — {why}" + (f" ({c['vix_why']})" if c.get("vix_why") else "")
    (t0, v0, s0), (t1, v1, _) = xs[0], xs[-1]
    ch = f"{round(v1 - v0, 1) + 0.0:+.1f}"           # + 0.0: a -0.0 prints +0.0
    word = f"VIX {v1:.1f} · " + (f"since {t0} (started late)" if t0 > VIX_OPEN_BY else f"{ch} since open")
    return word, (f"{word}: {v1:.2f} at {t1}, {ch} on {v0:.2f} at {t0}" + (" (backfilled)" if s0 == "backfill" else "")
                  + f" · the 1-min closes of NSE_INDEX|India VIX (vix_log) · open = a first row by {VIX_OPEN_BY} [I]")


def how_much(d, i, lv):
    """HOW MUCH (stage 5), is there a move to pay for? -> {"line", "rows"}: the §1o day type as the DECODE block logged it
    at its last 5-min close (one meter: the frame lacks its writers' lead and the peers' bars, so a copy here would read
    3 of its 7 votes "?" and never one-sided), the day's spot range over trademap.em's EM, the session VWAP's σ, India
    VIX and its change since the open (vix_log), CPR. Each row names its source; an absent one says could not check."""
    c, t = d.get("ctx") or {}, d["mins"][i]
    dec = _logged(d, i)[1]
    o = dec[-1]["os"] if dec else {}
    if not o.get("type"):
        dt, rows = "?", ["day type: could not check — " + (f"{o.get('why')} (DECODE {dec[-1]['T']})" if dec else
                                                           f"no DECODE row by {t}" if c.get("decode") else "no DECODE log")]
    else:
        dt, rows = o["type"], [f"day {o['type']}: §1o at DECODE {dec[-1]['T']} · one-sided bars {o['up']} ▲ {o['down']} ▼ · "
                               f"flips {o['flips']} · VWAP crosses {o['crosses']}"]
    em = c.get("em")
    hi = max((x for x in d["fhi"][:i + 1] if x is not None), default=None)
    lo = min((x for x in d["flo"][:i + 1] if x is not None), default=None)
    if em and em["t"] <= t and hi is not None and lo is not None:
        ru = f"range used {(hi - lo) / em['em']:.2f} of EM"
        rows.append(f"{ru}: day range {hi - lo:.0f} pts (the 1-min futures bars) / EM {em['em']:.0f} pts (trademap.em at "
                    f"{em['t']}: the ATM {lv(em['K'])} straddle {em['straddle']:.1f} / 0.8 / √{em['N']})")
    else:
        ru = "range used could not check — " + ("before the 09:20 straddle" if em or t < "09:20" else
                                                c.get("em_why") or "no 09:20 straddle")
        rows.append(f"EM: {ru[11:]}")
    sd = d["sd"][i]                                  # M1: the build's 0.0 with no volume is no σ, never a σ of 0
    sdt = f"σ {sd:.0f}" if sd else "σ could not check — no σ yet (needs 1-min futures volume)"
    vx, vrow = _vix_at(c, t)
    rows += [f"{sdt} pts: the session VWAP's SD on the 1-min futures" if sd else sdt, vrow]
    cp = c.get("cpr")
    if cp:
        p = c["pd"]
        cpt = f"CPR {cp['kind']} ({cp['w']:.0f} pts)"
        rows.append(f"{cpt}: {p['date']} H {_fmt(p['h'])}f · L {_fmt(p['l'])}f · C {_fmt(p['c'])}f (bars ≤ 15:15) · CPR "
                    f"{_fmt(min(cp['tc'], cp['bc']))}–{_fmt(max(cp['tc'], cp['bc']))}f · narrow ≤ {CPR_NARROW} of the range [I]")
    else:
        cpt = "CPR could not check"
        rows.append("CPR: could not check — no prior-day H / L / C (health names why)")
    return {"line": f"day {dt} · {ru} · {sdt} · {vx} · {cpt}", "rows": rows}


def where(d, i, lean, lines, ce, pe, lv, basis):
    """WHERE (stage 6): the stop, its pool, two targets, the room -> {"stop", "pool", "t1", "t2", "room", "rows"}. Stop =
    her live zone trigger's stop (zone3's rows carry none yet: named), else the leg's PALAT line; pool = the nearest of
    PDH / PWH beyond it (a short; a long PDL / PWL) within POOL_X of its distance; T1 / T2 = the nearest two the lean's
    way of {the prior day's POC / VAH / VAL, the wall ahead, MAX PAIN, PDH / PDL}; room = points to T1. A strike prints in
    both frames (`lv`, the 3-min basis), a futures level `f`. A field it cannot fill is None and its row says why."""
    c, t, fut = d.get("ctx") or {}, d["mins"][i], d["fut"][i]
    L, rows, out = c.get("levels") or {}, [], {"stop": None, "pool": None, "t1": None, "t2": None, "room": None}
    zs = [z for z in d.get("zone") or () if not z.get("kind") and z.get("px") is not None and str(z.get("t", ""))[:5] <= t
          and _m(t) - _m(str(z["t"])[:5]) < MANAGE_WIN]
    stop = zs[-1].get("stop") if zs else None
    if stop is not None:
        out["stop"] = f"{_fmt(stop)}f (zone)"
    else:
        if zs:
            rows.append(f"stop: her zone {zs[-1]['t'][:5]} {zs[-1]['side']} — could not check: its row carries no stop")
        if lines:
            stop, out["stop"] = lines["half"], f"{_fmt(lines['half'])}f (PALAT line)"
        else:
            rows.append("stop: could not check — no zone stop and no leg's PALAT line")
    if not lean:
        return dict(out, rows=rows + ["pool / T1 / T2: no lean — they need a side"])
    keys = ("PDH", "PWH") if lean < 0 else ("PDL", "PWL")
    if stop is not None:
        dist = abs(stop - fut)
        got = sorted((abs(L[k] - fut), k) for k in keys if L.get(k) is not None and lean * (stop - L[k]) > 0
                     and abs(L[k] - fut) <= POOL_X * dist)
        if got:
            out["pool"] = f"{got[0][1]} {_fmt(L[got[0][1]])}f"
        else:
            rows.append("pool: " + (f"none — no {' / '.join(keys)} beyond the stop within {POOL_X}× its {dist:.0f} pts"
                                    if any(L.get(k) is not None for k in keys) else
                                    f"could not check — no {' / '.join(keys)} (health names why)"))
    vp, cand = c.get("vp"), []
    if vp:
        cand += [(f"p{n}", vp[k], f"p{n} {_fmt(vp[k])}f") for n, k in (("POC", "poc"), ("VAH", "vah"), ("VAL", "val"))]
    else:
        rows.append(f"prior POC / VAH / VAL: skipped — {c.get('vp_why') or 'not on the tape'}")
    w = (ce[0] if ce else None) if lean > 0 else (pe[0] if pe else None)
    if w:
        cand.append((f"{w['side']} wall", w["k"] + basis, f"{w['side']} wall {lv(w['k'])}"))
    mp = (_opt_at(d, t) or {}).get("mp")
    if mp is not None:
        cand.append(("MAX PAIN", mp + basis, f"MAX PAIN {lv(mp)}"))
    cand += [(k, L[k], f"{k} {_fmt(L[k])}f") for k in ("PDH", "PDL") if L.get(k) is not None]
    way = sorted((x for x in cand if lean * (x[1] - fut) > 3), key=lambda x: lean * (x[1] - fut))
    if way:
        out["t1"], out["room"] = way[0][2], f"{lean * (way[0][1] - fut):.0f} to {way[0][0]}"
        out["t2"] = way[1][2] if len(way) > 1 else None
    else:
        rows.append(f"T1 / T2: none {'above' if lean > 0 else 'below'} {_fmt(fut)}f among the levels read")
    return dict(out, rows=rows)


def expression(d, i, aw, lean, s, buyer, seller, lv, cnt):
    """EXPRESSION (stage 7): both lines priced, and a pick [I, display only, for her signature if it ever becomes a rule]
    -> {"buyer", "seller", "pick", "pick_why"}. The buyer's line gains what the move must pay (the ATM premium x NEED_X)
    against EM left (EM − |fut − the open|); the seller's, the ATM IV against RV on IV's calendar basis (_rv_cal; IV_RV:
    rich / fair / cheap) and where her fold line would be (HOLD v2's line, not logged: said so). Pick: `seller` on TREND
    with Sides REAL / BACKED the lean's way and IV rich; `buyer` when the count's answer piece (`cnt`) is the lean's own
    push BROKEN (within ANSWER_MIN) and the required move fits EM left; else None, "no edge named"."""
    c, t, fut = d.get("ctx") or {}, d["mins"][i], d["fut"][i]
    o, em = _opt_at(d, t) or {}, c.get("em")
    left = em["em"] - abs(fut - d["fo"][0]) if em and em["t"] <= t and (d.get("fo") or [None])[0] is not None else None
    opts = (("CE",) if lean > 0 else ("PE",)) if lean else ("CE", "PE")
    need = {x: o[x.lower()] * NEED_X for x in opts if isinstance(o.get(x.lower()), (int, float))}
    thin = None if left is None or not need else max(need.values()) > left
    buyer += (" · needs " + (" / ".join(f"+{v:.0f}" + (f" ({x})" if len(opts) > 1 else "") for x, v in need.items())
                             if need else f"+? (could not check — no ATM premium at {t})")
              + f" pts today [I ×{NEED_X}] · EM left " + (H._sg(f"{left:.0f}") if left is not None else "? (no 09:20 straddle)")
              + ("" if thin is None else " → thin" if thin else " → fits"))
    iv, r_ = o.get("iv"), (c.get("rv") or 0) * 100 * (c.get("rv_cal") or RV_CAL)
    grade = None if iv is None or not r_ else "rich" if iv >= r_ * IV_RV else "cheap" if iv <= r_ / IV_RV else "fair"
    seller += (f" · IV {iv:.1f} vs RV {r_:.1f} (cal) → {grade}" if grade else
               f" · IV ? vs RV ? (could not check — {'no ATM IV at ' + t if iv is None else 'no RV: health names why'})")
    if seller.startswith("sell"):
        seller += " · fold: could not check — the HOLD v2 line is not logged"
    ans = next((p for p in (cnt or {}).get("pieces") or () if p.get("k") == "answer"), None)
    brk = ans if lean and ans and ans["side"] == "with" and ans["text"].endswith(" BROKEN") else None
    if aw == "TREND" and lean and s and s.get("word") in ("REAL", "BACKED") and sides_fuel(s) == lean and grade == "rich":
        pick, why = "seller", (f"TREND {ARR[lean]} · Sides {s['t']} {s['word']} with it · IV {iv:.1f} ≥ RV {r_:.1f} (cal) "
                               f"×{IV_RV}")
    elif brk and thin is False and aw in ("TREND", "HOLD"):     # never a pick beside a line that says no new one (review 1 Nov)
        pick, why = "buyer", f"{brk['text']} · needs +{max(need.values()):.0f} ≤ EM left {left:.0f}"
    else:
        pick, why = None, "no edge named"
    return {"buyer": buyer, "seller": seller, "pick": pick, "pick_why": why}


def _logged(d, i):
    """THE READ marks and DECODE closes readable at minute i -> (read rows, decode rows): a DECODE row once written (`at`
    <= the minute's end; a row without `at`, at close + 1), a READ mark at close + 1 (it carries no `at`):
    holdshadow._dec_at's rule, so a replay never shows a row before the live server had written it."""
    c, m = d.get("ctx") or {}, _m(d["mins"][i])
    end = fold.ms(d["day"], d["mins"][i]) / 1000 + 60 if c.get("decode") else None
    return ([r for r in c.get("read") or () if _m(r["t"]) + 1 <= m],
            [r for r in c.get("decode") or ()
             if (r["at"] <= end if isinstance(r.get("at"), (int, float)) else _m(r["T"]) + 1 <= m)])


def _cross(d, i):
    """THE READ word and DECODE's call at their last close <= the frame's minute (data/read, data/decode), verbatim, plus
    DECODE's CVD and EFFORT lines -> ({"read", "decode", "board": None}, the why line). The Board is not read."""
    c = d.get("ctx") or {}
    rd, dc = _logged(d, i)
    read = (f"THE READ {ARR[rd[-1]['dir']] + ' ' if rd[-1].get('dir') in ARR else ''}{rd[-1]['word']} {rd[-1]['t']}"
            if rd else None)
    dec = f"DECODE {dc[-1]['call']} {dc[-1]['T']}" if dc and dc[-1].get("call") else None
    line = ("cross-check: " + (read or "THE READ could not check — " + ("no mark yet" if c.get("read") else "no read log"))
            + " · " + (dec or "DECODE could not check — " + ("no close yet" if c.get("decode") else "no decode log"))
            + "".join(f" · {x}" for x in (dc[-1]["lines"] if dc else ())))
    return {"read": read, "decode": dec, "board": None}, line


def _her_setup(d, i):
    """Her registered band setups today (confluence_log's FADE §1i / FADE-D §1n / RIDE §1j rows), each once written (its
    window closed: `at` <= the frame's minute) -> ["FADE SELL 14:39 · entry 23,040f 14:42 · stop 23,128f", ...]."""
    c, t = d.get("ctx") or {}, d["mins"][i]
    if not c.get("conf"):
        return []
    end, out = fold.ms(d["day"], t) / 1000 + 60, []
    for r in c["conf"]:
        if not isinstance(r.get("at"), (int, float)) or r["at"] > end:
            continue
        e = r.get("entry") or {}
        head = (f"{r.get('setup')} {r.get('side') or ARR.get(r.get('d'), '')} {r.get('t')}"
                + (f"–{r['end']}" if r.get("end") else ""))
        if e.get("E") is not None:
            out.append(head + f" · entry {_fmt(e['E'])}f {e.get('t') or ''}".rstrip()
                       + (f" · stop {_fmt(e['stop'])}f" if e.get("stop") is not None else
                          f" · line {_fmt(e['line0'])}f" if e.get("line0") is not None else ""))
        else:
            out.append(head + " · no entry" + (f" ({r['best']})" if r.get("best") else ""))
    return out


def _bada(d, i, walls, lv, basis):
    """Her BADA PRINT (the decoder's E1, shown on her chart) within one strike step of a wall, its 5-min bar closed in the
    last 15 min (trademap.bada's own rule) -> the why line."""
    import trademap
    c, t = d.get("ctx") or {}, d["mins"][i]
    if not c.get("dec_n"):
        return "BADA PRINT: could not check — no decoder rows today"
    t1 = fold.ms(d["day"], t) + 60000
    got = [f"{x} at the {w['side']} wall {lv(w['k'])}" for w in walls if w
           for x in [trademap.bada(c.get("bada"), w["k"] + basis, d.get("step") or 50, t1 - 15 * 60000, t1)] if x]
    return "BADA PRINT: " + (" · ".join(got) if got else "none at a wall in 15 min")


def _vpin(d, i):
    """The fast VPIN gauge's latest row by the frame's minute (NIFTY's future, shadow): display only, never a sign (A198)."""
    t = d["mins"][i]
    xs = [x for x in (d.get("ctx") or {}).get("vpin") or () if x[0][:5] <= t]
    if not xs:
        return "VPIN: could not check — no fast VPIN row today"
    a, v, p = xs[-1]
    return (f"VPIN (NIFTY fut, shadow): {v:.2f}" + (f" · p{round(p * 100)} of its history" if p is not None else
                                                     " · no percentile yet") + f" at {a[:5]} · display only")
