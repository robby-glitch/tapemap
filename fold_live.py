"""fold_live.py -- the rev 6 engine (fold.py) run LIVE inside the server (pro-tool P2-03, API-v3.md).

One Engine per index per day, driven by ONE thread (`run`). What it guarantees, and why:

  * NO REQUEST READS A DAY FILE (safety S11). The day's rows live in memory (a NIFTY day is ~22k
    book rows and ~2k chain rows). A restart reads the day files ONCE, in the background, then goes
    incremental; a request serves a cached read: O(1) however big the day.
  * ONE ORDER. Rows are fed in the recorded key order -- a book row by its arrival `t`, a chain row by
    its own `ts` -- LAG_MS after their key, so the live run and a restart's recompute from the files
    see the same order (6-blueprint §10) and the log stays free of `diverged` rows.
  * THE MARKET ALONE (fold.State(None)) is fed every row: the flat read, and the market half that IF
    YOU WERE IN copies. Each marked trade gets its own State, built from the rows so far when it is
    marked or its record changes (a chunked pass with a progress count, ~9 s on a full day), then stepped.
  * THE LOG (fold_log) is written after every step, per event; a build ends with the resume: logged
    words win on screen, a different recompute writes `diverged`.
  * ISOLATION. Every engine exception is caught per state and served as "could not check -- the engine
    failed: ..."; nothing here can reach /api/hold, /api/frame or the tape.

Anytime start: until the files are read and a state is built, a read says "could not check -- the
engine is catching up (n of m rows)". A marked trade lives in data/day_state/, never here.

Engines run all day for the three indices she trades (2026-10-03: she marks BANKNIFTY and SENSEX too, and
the DESK reads each one flat); a day's rows are ~25 MB per index in memory. NIFTY is built first.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import threading
import time

import book_log
import day_state
import daylog
import fold
import fold_log
import tape_log

log = logging.getLogger("tapemap.fold")
CC = fold.CC
ALWAYS = ("NIFTY", "BANKNIFTY", "SENSEX")   # the indices read all day, in build order; any other index while it has a marked trade
LAG_MS = 2000            # (h) a row is fed 2 s after its key: a chain row (own ts) lands before later book rows (arrival t)
READ_EVERY_S = 3         # (h) the cached reads are refreshed this often
IFIN_EVERY_S = 10        # (h) IF YOU WERE IN is re-read this often while she looks at a strike...
IFIN_KEEP_S = 60         # (h) ...and dropped a minute after her last look
CONTRACT_WAIT_S = 60     # (h) a live start waits this long for the contract before pooling priors without it
CHUNK = 500              # rows per feed while a state is built: the progress count's grain
EVENTS_SHOWN = 12        # API-v3: the view carries its last 12 events

_ENG = {}                # idx -> today's Engine
_Q = {}                  # idx -> [(kind, row)] pushed by the recorders' threads, drained by the loop
_QLOCK = threading.Lock()
_CFG = {}                # run()'s seams: day_fn, trades_fn, lot_fn, contract_fn, chain_dir_fn, vpin_path_fn, mock


# ---- the recorders push, the loop pulls
def push(idx, kind, rows):
    """kind: book | chain | vpin | tape. A row is the dict the recorder wrote (or would write)."""
    rows = list(rows)
    if not rows:
        return
    with _QLOCK:
        _Q.setdefault(idx, []).extend((kind, r) for r in rows)


def push_book(flushed):
    """book_log.Book.flush's return: [(idx, row)]."""
    by = {}
    for idx, r in flushed:
        by.setdefault(idx, []).append(r)
    for idx, rs in by.items():
        push(idx, "book", rs)


def push_chain(idx, doc):
    """The poller's published snapshot (the senses loop's parsed payload): live and mock rows only, never
    a restored one (the file has it already), trimmed to what fold reads."""
    if not doc.get("ok") or doc.get("mode") == "restored" or not doc.get("ts") or not doc.get("strikes"):
        return
    push(idx, "chain", [dict(ts=doc["ts"], spot=doc.get("spot"), strikes=doc["strikes"], expiry=doc.get("expiry"))])


def _drain(idx):
    with _QLOCK:
        rows, _Q[idx] = _Q.get(idx) or [], []
    return rows


def _queued():
    with _QLOCK:
        return [i for i, rs in _Q.items() if rs]


# ---- trades, two shapes
def fold_trade(tr):
    """A marked trade (server._hold_trade's record) -> fold's trade."""
    return dict(k=int(float(tr["k"])), ty=tr["side"], side="BUY" if tr["role"] == "long" else "SELL", p0=tr["p0"],
                entry_t=tr["t0"], exit_t=tr.get("exit_t"), trade_id=tr["id"], qty=tr.get("qty"), expiry=tr.get("expiry"))


def api_trade(tr):
    """API-v3 `trade`: {idx, k, ty, side, p0, entry_t, exit_t, qty}."""
    return dict(idx=tr["idx"], k=int(float(tr["k"])), ty=tr["side"], side="BUY" if tr["role"] == "long" else "SELL",
                p0=tr["p0"], entry_t=tr["t0"], exit_t=tr.get("exit_t"), qty=tr.get("qty"))


def _sig(tr):
    """What a rebuild must follow: the exit, the entry premium, the size."""
    return (tr.get("exit_t"), tr.get("p0"), tr.get("qty"))


def _trim(v):
    out = {k: x for k, x in v.items() if k != "new_events"}
    out["events"] = list(v.get("events") or [])[-EVENTS_SHOWN:]
    return out


def _words(st, logged):
    """The headline history [{t, headline, clause, prem, pct, after_exit}]: a row per change, the logged row's words
    where one exists. After her exit the engine reads on (what holding would have done); those rows say so."""
    out, last = [], None
    for e in st.events:
        r = logged.get(e["seq"])
        h, c, t = (r["headline"], r["clause"], r["ts"]) if r else (e["row"]["headline"], e["row"]["clause"], e["ts"])
        p = (r or e["row"]).get("prem") or {}
        if h and (h, c) != last:
            out.append(dict(t=t, headline=h, clause=c, prem=p.get("now"), pct=p.get("pct"), after_exit=st.exit_t is not None and e["t"] > st.exit_t))
            last = (h, c)
    return out


def _as_trade(st, tr):
    """The trade half of fold.State.__init__ on a COPY of the market read (the flat State): IF YOU WERE IN
    without a second pass over the day (fold.ifin re-reads every row; the flat State already has them)."""
    st.trade, st.k, st.ty = tr, int(tr["k"]), str(tr["ty"]).lower()
    buy = str(tr["side"]).upper() == "BUY"
    st.own = 1 if buy else -1
    st.d = 1 if (st.ty == "ce") == buy else -1
    st.dty, st.aty = ("CE", "PE") if st.d < 0 else ("PE", "CE")
    st.p0, st.entry_t, st.exit_t, st.trade_id = float(tr["p0"]), int(tr["entry_t"]), None, tr["trade_id"]
    st.nfixed = len([r for r in st.runs if "fixed_t" in r])


def _fail(e):
    return f"{CC} — the engine failed: {type(e).__name__}: {e}"


def _jsonl(path, keep):
    out = []
    try:
        with daylog.open_text(path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and keep(r):
                    out.append(r)
    except OSError:
        pass
    return out


class Engine:
    """One index, one day: the rows, the market read, her trades' reads, and the cached replies."""

    def __init__(self, idx, day, lot=None, prior=(), mock=False):
        self.idx, self.day, self.lot, self.prior, self.mock = idx, day, lot, list(prior), mock
        self.rows = dict(book=[], chain=[], vpin=[], tape=[])
        self.pending = []                     # live rows waiting LAG_MS: (key, kind, row)
        self.last = {"book": -1, "chain": ""}   # the last key fed, per kind: a repeat or a late row is dropped
        self.seen = {"vpin": set(), "tape": set()}
        self.loaded, self.progress, self.expiry = False, None, None
        self.flat, self.flat_read, self.err = None, None, None
        self.trades = {}                      # id -> {tr, sig, st, res, logged, err, reply}
        self.ifin = {}                        # (k, ty, side) -> {asked, at, reply, logged}
        self.read_at = 0
        self.close_ms = fold.ms(day, fold.SESSION_CLOSE)

    # ---- the day files, once
    def load(self, chain_dir, vpin_path):
        """Today's rows from disk (a restart). Streamed; a torn line is skipped; a missing file is an empty day."""
        self.progress = "reading the day's files"
        book = list(book_log.read_rows(self.day, self.idx))
        chain = _jsonl(os.path.join(str(chain_dir), f"chain_{self.idx}_{self.day}.jsonl"), lambda r: r.get("ts") and r.get("strikes"))
        vpin = _jsonl(str(vpin_path), lambda r: r.get("day") == self.day)
        tape = [b for b in tape_log.read_bars(self.day, self.idx) if b.get("t") is not None]
        self.install(book, chain, vpin, tape)

    def install(self, book, chain, vpin=(), tape=()):
        """The day's rows so far, in place of load() (the tests)."""
        self.rows = dict(book=list(book), chain=list(chain), vpin=list(vpin), tape=list(tape))
        if book:
            self.last["book"] = max(r["t"] for r in book)
        if chain:
            self.last["chain"] = max(r["ts"] for r in chain)
        self.seen = {"vpin": {r.get("at") for r in vpin}, "tape": {b.get("t") for b in tape}}
        self.loaded, self.progress = True, None

    def inputs(self):
        return dict(day=self.day, idx=self.idx, lot=self.lot, prior=self.prior, expiry=self.expiry)

    def _keys(self):
        rows = [(r["t"], 1, r) for r in self.rows["book"]] + [(fold.ms(self.day, r["ts"]), 0, r) for r in self.rows["chain"]]
        rows.sort(key=lambda x: (x[0], x[1]))
        return rows

    def _build(self, trade):
        """A State over the rows so far, fed in chunks so the progress count moves (one pass, once per mark)."""
        st = fold.State(trade, self.inputs())
        st.feed(vpin=self.rows["vpin"], tape=self.rows["tape"])
        keys = self._keys()
        m = len(keys)
        self.progress = (0, m)
        for i in range(0, m, CHUNK):
            part = keys[i:i + CHUNK]
            st.feed(book=[r for _, kind, r in part if kind], chain=[r for _, kind, r in part if not kind])
            self.progress = (min(i + CHUNK, m), m)
        self.progress = None
        return st

    # ---- live rows, in key order
    def absorb(self, now_ms):
        """Queue -> pending -> fed, LAG_MS after a row's key, sorted the way the files are read. VPIN and tape
        rows have no place in the order (fold reads them by window) and go straight in."""
        for kind, r in _drain(self.idx):
            if kind == "book":
                self.pending.append((r["t"], 1, r))
            elif kind == "chain":
                self.pending.append((fold.ms(self.day, r["ts"]), 0, r))
            elif kind == "vpin" and r.get("at") not in self.seen["vpin"]:
                self.seen["vpin"].add(r.get("at"))
                self.rows["vpin"].append(r)
                self._feed_all(vpin=[r])
            elif kind == "tape" and r.get("t") is not None and r["t"] not in self.seen["tape"]:
                self.seen["tape"].add(r["t"])
                self.rows["tape"].append(r)
                self._feed_all(tape=[r])
        cut = now_ms - LAG_MS
        due = sorted((x for x in self.pending if x[0] <= cut), key=lambda x: (x[0], x[1]))
        if not due:
            return
        self.pending = [x for x in self.pending if x[0] > cut]
        b, c = [], []
        for _, kind, r in due:
            if kind:
                if r["t"] > self.last["book"]:
                    self.last["book"] = r["t"]
                    b.append(r)
            elif r["ts"] > self.last["chain"]:
                self.last["chain"] = r["ts"]
                c.append(r)
        if b or c:
            self.rows["book"] += b
            self.rows["chain"] += c
            self._feed_all(book=b, chain=c)

    def _feed_all(self, **batch):
        if self.flat is not None and self.err is None:
            try:
                self.flat.feed(**batch)
            except Exception as e:                       # the market read is down until a rebuild; it says so
                self.err = _fail(e)
                log.exception("fold flat %s", self.idx)
        for tid, e in self.trades.items():
            if e["st"] is None or e["err"]:
                continue
            try:
                e["st"].feed(**batch)
                fold_log.write(e["st"], exit_t=e["st"].exit_t)
            except Exception as x:
                e["err"] = _fail(x)
                log.exception("fold trade %s", tid)

    # ---- her trades
    def sync(self, trades):
        """The marked trades of this index: build the new, rebuild a changed one, drop the unmarked. The market
        read first, once a chain snapshot is in (its expiry decides the expiry-day rule for every state)."""
        if not self.rows["chain"]:
            return
        expiry = self.rows["chain"][-1].get("expiry")
        if self.flat is None or expiry != self.expiry:
            self.expiry = expiry
            try:
                self.flat, self.err = self._build(None), None
            except Exception as e:
                self.err = _fail(e)
                log.exception("fold build flat %s", self.idx)
            for e in self.trades.values():                # the expiry changed under them: rebuild
                e["st"], e["err"] = None, None
            self.ifin.clear()
            self.read_at = 0
        want = {t["id"]: t for t in trades if t["idx"] == self.idx}
        for tid in [t for t in self.trades if t not in want]:
            del self.trades[tid]
        for tid, tr in want.items():
            e = self.trades.get(tid)
            if e is not None and e["sig"] == _sig(tr) and (e["st"] is not None or e["err"]):
                continue
            e = self.trades[tid] = dict(tr=tr, sig=_sig(tr), st=None, res=None, logged={}, err=None, reply=None)
            self.read_at = 0
            if tr.get("p0") is None:
                e["err"] = f"{CC} — no entry premium was marked for {tid}"
                continue
            try:
                st = self._build(fold_trade(tr))
                e["res"] = fold_log.resume(st)
                e["logged"] = {r["seq"]: r for r in fold_log.read(self.idx, self.day)
                               if r.get("trade_id") == tid and r.get("event") not in ("outcome", "diverged")}
                fold_log.write(st, exit_t=st.exit_t)
                e["st"] = st
            except Exception as x:
                e["err"] = _fail(x)
                log.exception("fold build %s", tid)

    # ---- the reads, cached
    def refresh(self, now_ms):
        if now_ms - self.read_at < READ_EVERY_S * 1000:
            return
        self.read_at = now_ms
        now = min(now_ms, self.close_ms)                  # after the close the read is the last snapshot
        if self.err:
            self.flat_read = dict(ok=False, why=self.err)
        elif self.flat is not None:
            try:
                self.flat_read = dict(ok=True, **self.flat.flat_view(now))
            except Exception as e:
                self.flat_read = dict(ok=False, why=_fail(e))
        for tid, e in self.trades.items():
            e["reply"] = self._reply(tid, e, now)
        wall = time.time()                                # her looks are on the wall clock, the rows on theirs
        for key, x in list(self.ifin.items()):
            if wall - x["asked"] > IFIN_KEEP_S:
                del self.ifin[key]
            elif wall - x["at"] >= IFIN_EVERY_S:
                x["at"] = wall
                try:
                    x["reply"] = self._ifin(*key, log_it=not x["logged"])
                    x["logged"] = True
                except Exception as e:
                    x["reply"] = dict(ok=False, why=_fail(e))

    def _reply(self, tid, e, now):
        head = dict(id=tid, trade=api_trade(e["tr"]))
        if e["err"]:
            return dict(ok=False, why=e["err"], **head)
        if e["st"] is None:
            return dict(ok=False, why=self.catching_up(), **head)
        try:
            v = fold_log.words(e["st"].view(now), e["res"])
            return dict(ok=True, view=_trim(v), words=_words(e["st"], e["logged"]), asof=fold.hms(now), **head)
        except Exception as x:
            return dict(ok=False, why=_fail(x), **head)

    def catching_up(self):
        p = self.progress
        if isinstance(p, tuple):
            return f"{CC} — the engine is catching up ({p[0]} of {p[1]} rows)"
        if not self.loaded or p:
            return f"{CC} — the engine is catching up (reading the day's files)"
        if not self.rows["chain"]:
            return f"{CC} — the engine is catching up (no chain snapshot yet)"
        return f"{CC} — the engine is catching up (0 of {len(self.rows['book']) + len(self.rows['chain'])} rows)"

    def _ifin(self, k, ty, side, log_it=False):
        """IF YOU WERE IN: the market read copied, marked now at the last chain snapshot's premium (§5)."""
        if self.err:
            return dict(ok=False, why=self.err)
        if self.flat is None or not self.rows["chain"]:
            return dict(ok=False, why=self.catching_up())
        c = self.rows["chain"][-1]
        t = fold.ms(self.day, c["ts"])
        x = next((x for x in c["strikes"] if x["k"] == k), None)
        p0 = x[ty.lower()]["ltp"] if x else None
        if not p0:
            return dict(ok=False, why=f"{CC} — no chain price for {k} {ty} at {c['ts']}")
        st = copy.deepcopy(self.flat)
        tr = dict(k=k, ty=ty, side=side, p0=p0, entry_t=t, trade_id=f"ifin:{self.day}:{k}{ty}:{side[0]}:{c['ts']}")
        _as_trade(st, tr)
        st.feed(chain=[c])                                # the mark: seeds on the last chain row, at its own ts
        v = st.view(t)
        v.update(ifin=True, trade=tr, p0=p0, entry_t=fold.hms(t))
        if log_it:
            fold_log.write(st, src="ifin")
        return dict(ok=v.get("headline") is not None, why=v.get("why"), view=_trim(v))

    def ask_ifin(self, k, ty, side):
        key = (int(float(k)), str(ty).upper(), str(side).upper())
        x = self.ifin.get(key)
        if x is None:
            x = self.ifin[key] = dict(asked=0, at=0, reply=None, logged=False)
            self.read_at = 0
        x["asked"] = time.time()
        return x["reply"] or dict(ok=False, why=f"{CC} — reading {key[0]} {key[1]} {key[2]} now (first look)")

    def record(self):
        """RECORD (API-v3): her trades' words and premiums, as numbers from the frozen view, never rates."""
        out = []
        for tid, e in self.trades.items():
            r = e.get("reply") or {}
            v = r.get("view") or {}
            p = v.get("prem") or {}
            ex = e["tr"].get("exit_t")
            out.append(dict(id=tid, trade=e["tr"], words=r.get("words") or [], why=None if r.get("ok") else r.get("why"),
                            exit=dict(t=ex, prem=p.get("now"), pct=p.get("pct")) if ex and v.get("frozen") else None,
                            best=dict(t=p.get("peak_t"), prem=p.get("peak"), pct=p.get("peak_pct")) if p else None,
                            peak_before_exit=dict(t=p.get("peak_t"), prem=p.get("peak")) if ex and v.get("frozen") else None,
                            given_back=p.get("given_back") if p else None))
        return out


# ---- the server's seams
def _engine(idx, day, now_ms):
    """Today's engine for idx, made on first use: the lot and the prior sessions come from the seams."""
    eng = _ENG.get(idx)
    if eng is not None and eng.day == day:
        return eng
    ct = _CFG["contract_fn"](idx)
    born = _CFG.setdefault("born", {}).setdefault((idx, day), now_ms)
    if ct is None and not _CFG.get("mock") and now_ms - born < CONTRACT_WAIT_S * 1000:
        return None                                       # a live start: the contract names the prior pool (P1-03)
    lot = _CFG["lot_fn"](idx)
    ct = ct or {}
    try:
        days, _why = tape_log.prior_pool(day, idx, fold.PRIOR_N, after=ct.get("expired"), ik=ct.get("ik"))
        prior = [fold.session_from_book(list(book_log.read_rows(d, idx)), lot=lot or 65, idx=idx, day=d) for d in reversed(days)]
    except Exception:
        log.exception("fold prior sessions %s", idx)
        prior = []
    eng = _ENG[idx] = Engine(idx, day, lot=lot, prior=prior, mock=_CFG.get("mock", False))
    return eng


def tick(now_ms=None):
    """One pass of the loop: NIFTY and every index with a marked trade; the rest of the queue is dropped."""
    now_ms = now_ms or int(time.time() * 1000)
    day = _CFG["day_fn"]()
    trades = _CFG["trades_fn"]()
    want = set(ALWAYS) | {t["idx"] for t in trades}
    for idx in _queued():
        if idx not in want:
            _drain(idx)
    for idx in [i for i in ALWAYS if i in want] + sorted(want - set(ALWAYS)):
        try:
            eng = _engine(idx, day, now_ms)
            if eng is None:
                continue
            if not eng.loaded:
                eng.load(_CFG["chain_dir_fn"](), _CFG["vpin_path_fn"]())
            eng.absorb(now_ms)
            eng.sync(trades)
            eng.refresh(now_ms)
        except Exception:
            log.exception("fold tick %s", idx)


def run(day_fn, trades_fn, lot_fn, contract_fn, chain_dir_fn, vpin_path_fn, mock=False, period=1.0):
    """The loop, on its own daemon thread (server.main). Every seam is a function read at call time, so a
    --mock-chain run and the tests point them wherever they like."""
    _CFG.update(day_fn=day_fn, trades_fn=trades_fn, lot_fn=lot_fn, contract_fn=contract_fn,
                chain_dir_fn=chain_dir_fn, vpin_path_fn=vpin_path_fn, mock=mock)
    while True:
        try:
            tick()
        except Exception:                                 # a seam failing must not end the thread
            log.exception("fold loop")
        time.sleep(period)


# ---- the requests: the cache, never the engine
def _one(q, n):
    return (q.get(n) or [None])[0]


def past_record(day):
    """RECORD for a day gone from memory, off the files: her marked trades (day_state) and the words the engine
    logged for them (fold_log). The same shape as Engine.record(); the premiums are the logged rows' [M]."""
    trades = (day_state.load(day) or {}).get("hold_trades") or []
    if not trades:
        return dict(ok=True, day=day, trades=[])
    out = []
    for tr in trades:
        src = tr.get("src") or "marked"                   # "import": from her tradebook after the day, replayed; shown apart
        rows = [r for r in fold_log.read(tr["idx"], day) if r.get("trade_id") == tr["id"] and r.get("src", "marked") == src
                and r.get("event") not in ("outcome", "diverged") and r.get("headline")]
        ex, words, last = tr.get("exit_t"), [], None
        for r in rows:
            p = r.get("prem") or {}
            if (r["headline"], r.get("clause")) != last:
                words.append(dict(t=r["ts"], headline=r["headline"], clause=r.get("clause"), prem=p.get("now"), pct=p.get("pct"),
                                  after_exit=ex is not None and r["ts"] > ex))
                last = (r["headline"], r.get("clause"))
        held = [r for r in rows if ex is None or r["ts"] <= ex]
        p = (held[-1].get("prem") or {}) if held else {}
        out.append(dict(id=tr["id"], trade=tr, words=words, why=None if rows else f"{CC} — no engine words were logged for {tr['id']}",
                        exit=dict(t=ex, prem=p.get("now"), pct=p.get("pct"), at=held[-1]["ts"]) if ex and held else None,
                        best=dict(t=p.get("peak_t"), prem=p.get("peak"), pct=p.get("peak_pct")) if p else None,
                        peak_before_exit=dict(t=p.get("peak_t"), prem=p.get("peak")) if ex and held else None,
                        given_back=p.get("given_back") if p else None))
    return dict(ok=True, day=day, trades=out)


def _not_started(eng):
    return eng.err or eng.catching_up() if eng else f"{CC} — the engine has not started on this index"


def reply(path, q, trades):
    """GET /api/fold, /api/fold/flat, /api/fold/ifin, /api/fold/record (API-v3). Isolated: a failure is a why."""
    try:
        if path == "/api/fold/flat":
            eng = _ENG.get(_one(q, "idx") or ALWAYS[0])
            return eng.flat_read if eng and eng.flat_read else dict(ok=False, why=_not_started(eng))
        if path == "/api/fold/ifin":
            eng = _ENG.get(_one(q, "idx") or ALWAYS[0])
            if eng is None:
                return dict(ok=False, why=_not_started(eng))
            try:
                return eng.ask_ifin(_one(q, "k"), _one(q, "ty"), _one(q, "side"))
            except (TypeError, ValueError):
                return dict(ok=False, why=f"{CC} — ifin needs k, ty CE|PE and side BUY|SELL")
        if path == "/api/fold/record":
            today = _CFG["day_fn"]() if _CFG.get("day_fn") else time.strftime("%Y-%m-%d")
            day = _one(q, "day") or today
            if day != today:
                return past_record(day)
            engs = [e for e in _ENG.values() if e.day == day]
            if not engs:
                return dict(ok=False, why=f"{CC} — the engine has not started today")
            return dict(ok=True, day=day, trades=[t for e in engs for t in e.record()])
        tid = _one(q, "id")
        tr = next((t for t in trades if t["id"] == tid), None)
        if tr is None:
            return dict(ok=False, why=f"{CC} — no marked trade {tid} today")
        eng = _ENG.get(tr["idx"])
        e = eng.trades.get(tid) if eng else None
        if e is None or e["reply"] is None or (e["st"] is None and not e["err"]):
            return dict(ok=False, id=tid, trade=api_trade(tr), why=_not_started(eng))
        return e["reply"]
    except Exception as e:
        return dict(ok=False, why=_fail(e))


def frame(idx, trades):
    """POST /api/frame's two extra fields: `fold` for the open marked trade on idx (else None), `flat` when none."""
    try:
        open_ = [t for t in trades if t["idx"] == idx and not t.get("exit_t")]
        if open_:
            return reply("/api/fold", {"id": [open_[0]["id"]]}, trades), None
        return None, reply("/api/fold/flat", {"idx": [idx]}, trades)
    except Exception as e:
        return dict(ok=False, why=_fail(e)), None
