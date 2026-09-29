"""reader_live.py -- the SHADOW leg engine (reader.py) run live inside the server, on its own thread.

Per index (NIFTY, BANKNIFTY, SENSEX), every PERIOD_S:
  * tail today's Upstox book file (book_log.DIR: the recorder's own file, read-only) into reader.BookMinutes;
  * step every CLOSED minute (LAG_MS after its end) into one reader.Engine;
  * NIFTY: stamp each GoCharting bar in tape_log's day file with the time this thread first saw it;
  * append every NEW event to data/reader/reader_<IDX>_<day>.jsonl -- append-only; a leg row carries its frozen leg;
  * cache one reply for GET /api/reader?idx=.

ANYTIME START. The book file is read from its first row, so the rebuilt cut equals the live one (reader.py is a pure
fold over closed minutes). Events already in the day's log are never written twice (keyed by kind, time and leg id),
and the reply serves the LOGGED legs, so a restart repaints nothing. GoCharting bars already on disk at a restart are
stamped with the restart time: legs before it read their GC side as "not received" -- the true arrival is unknown.

ISOLATION. Everything is try-guarded per index; a failure is served as "could not check -- the reader failed: ...".
Nothing here is called from the frame door, fold, or the feed alarm. SHADOW: no face shows this unless the Trade tab's
"LEGS · shadow" toggle is on, and its thresholds are unsigned (reader.SHEET).
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from typing import Dict, List, Optional

import book_log
import daylog
import reader
import tape_log
import xindex_live

log = logging.getLogger("tapemap.reader")
DIR = os.path.join("data", "reader")
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
PERIOD_S = 15
LAG_MS = 5000               # a minute is stepped 5 s after it ends: late frames land first
EVENTS_SHOWN = 40
_DAYS: Dict[str, "_Day"] = {}
_READ: Dict[str, dict] = {}
_LOCK = threading.Lock()
_CFG: Dict[str, object] = {"lot_tick": None}     # seam: idx -> (lot, dump tick in paise); tests inject it


def log_path(idx: str, day: str) -> str:
    return os.path.join(DIR, f"reader_{idx}_{day}.jsonl")


def _lot_tick(idx: str):
    f = _CFG.get("lot_tick")
    if f is None:
        import upstox_instruments
        f = upstox_instruments.lot_tick
    return f(idx)


def _rows(path: str) -> List[dict]:
    out = []
    try:
        with daylog.open_text(path) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict):
                    out.append(r)
    except OSError:
        return []
    return out


class _Tail:
    """New complete JSON lines of a growing file since the last call."""

    def __init__(self, path: str):
        self.path, self.off, self.rest = path, 0, b""

    def read(self) -> List[dict]:
        try:
            with open(self.path, "rb") as f:
                f.seek(self.off)
                chunk = f.read()
        except OSError:
            return []
        self.off += len(chunk)
        lines = (self.rest + chunk).split(b"\n")
        self.rest = lines.pop()
        out = []
        for ln in lines:
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if isinstance(r, dict):
                out.append(r)
        return out


class _Day:
    def __init__(self, idx: str, day: str):
        self.idx, self.day = idx, day
        lot, tick_paise = _lot_tick(idx)
        self.lot = int(lot)
        self.tick_px = reader.rupee_tick(float(tick_paise)) if tick_paise else None
        self.bm = reader.BookMinutes(self.lot, self.tick_px)
        self.book = _Tail(book_log.day_path(day, idx))
        self.tape = _Tail(tape_log.day_path(day, idx)) if idx == "NIFTY" else None
        self.eng: Optional[reader.Engine] = None
        self.stepped = 0
        self.expiry = self.ik = None
        self.n_ev = 0
        self.keys = set()
        self.logged: List[dict] = []
        self.snaps: Dict[int, dict] = {}                 # 3-min bar close (ms) -> the engine as of it, for xindex
        self.closes = xindex_live.bar_closes(day)
        for row in _rows(log_path(idx, day)):           # a restart: what was already said stays said
            e = row.get("event") or {}
            self.keys.add(self._key(e))
            self.logged.append(row)
        self.prior = self._priors()

    @staticmethod
    def _key(e: dict):
        return (e.get("kind"), e.get("t"), e.get("leg") or e.get("en"))

    def _priors(self):
        pre = f"book_{self.idx}_"
        try:
            names = os.listdir(book_log.DIR)
        except OSError:
            names = []
        days = sorted({m.group(1) for n in names for m in [re.match(pre + r"(\d{4}-\d\d-\d\d)\.jsonl(\.gz)?$", n)]
                       if m and m.group(1) < self.day})[-int(reader.TH["PRIOR_N"]):]
        lists = [reader.canonical(reader.book_minutes(_rows(book_log.day_path(d, self.idx)), self.lot, self.tick_px))
                 for d in days]
        lists = [x for x in lists if x]
        if not lists:
            return None, None, None, days
        return reader.prior_unit(lists), reader.prior_spread(lists), reader.oi_sigma(lists[-1]), days

    def tick(self, now_ms: int) -> None:
        for r in self.book.read():
            if self.expiry is None and r.get("expiry"):
                self.expiry, self.ik = r["expiry"], r.get("ik")
            self.bm.feed(r)
        mins = reader.canonical(self.bm.minutes())
        if self.eng is None:
            if not mins:
                return
            unit, spread, sigma, _ = self.prior
            self.eng = reader.Engine(idx=self.idx, day=self.day, lot=self.lot, unit=unit, expiry=self.expiry,
                                     gc_expected=(self.idx == "NIFTY"), prior_sigma=sigma, spread=spread,
                                     contract=self.ik or "front")
        if self.tape is not None:
            for b in self.tape.read():
                self.eng.add_gc(b, now_ms)
        for m in mins:
            if m["t"] > self.stepped and m["t"] + 60000 + LAG_MS <= now_ms:
                self._snap_to(m["t"])
                self.eng.step(m)
                self.stepped = m["t"]
        self._snap_to(self.stepped + 60000)
        self._append(now_ms)

    def _snap_to(self, limit: int) -> None:
        """Record the engine's state at every bar close <= limit not yet recorded (the minutes before it are in)."""
        if self.eng is None or not self.eng.m:
            return
        for c in self.closes:
            if c > limit:
                break
            if c not in self.snaps and c > self.eng.m[0]["t"]:
                self.snaps[c] = xindex_live.snapshot(self.eng)

    def _append(self, now_ms: int) -> None:
        legs = {L["id"]: L for L in self.eng.legs}
        new = []
        for e in self.eng.events[self.n_ev:]:
            k = self._key(e)
            if k in self.keys:
                continue
            row = {"idx": self.idx, "day": self.day, "at": now_ms, "rev": reader.REV, "shadow": True, "event": e}
            if e.get("kind") == "leg" and e.get("leg") in legs:
                row["leg"] = legs[e["leg"]]
            new.append(row)
            self.keys.add(k)
        self.n_ev = len(self.eng.events)
        if not new:
            return
        self.logged += new
        try:
            os.makedirs(DIR, exist_ok=True)
            with open(log_path(self.idx, self.day), "a", encoding="utf-8") as f:
                for row in new:
                    f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        except OSError as e:                              # the record failed; the read still serves
            log.warning("reader log write failed: %s", e)

    def reply(self, now_ms: int) -> dict:
        eng = self.eng
        base = {"idx": self.idx, "day": self.day, "rev": reader.REV, "shadow": True, "signed": False,
                "asof": reader.ladder.hms_ist(now_ms), "tag_note": "Δ is [I] (side inferred); pts, lots, OI are [M]"}
        if eng is None:
            return {**base, "ok": False, "why": "could not check — no Upstox book rows for today yet"}
        if eng.delta is None:
            return {**base, "ok": False, "why": f"warming — the ruler is set after {int(reader.TH['SELF_N'])} minutes "
                                                "(no prior session on disk)"}
        legs = [r["leg"] for r in self.logged if r.get("leg")]
        story = []
        for r in self.logged:
            e = r["event"]
            story.append({"t": reader.hm(e["t"]), "kind": e["kind"], "en": e["en"], "chip": e["chip"]})
        f = eng.forming()
        unit, spread, sigma, days = self.prior
        return {**base, "ok": True, "why": None, "ruler": round(eng.delta, 1), "ruler_note": eng.ruler_note,
                "prior_days": days, "expiry": self.expiry, "expiring": eng.expiring, "sessions_left": eng.sessions_left,
                "auction": {k: eng.au.get(k) for k in ("state", "d", "band")}, "legs": legs,
                "forming": f, "story": story[-EVENTS_SHOWN:], "minutes": len(eng.m),
                "counts": {"legs": len(legs), "auction_changes": sum(1 for s in story if s["kind"] == "auction"
                                                                     and "edge widened" not in s["en"])},
                "thresholds": reader.TH}


def tick(now_ms: Optional[int] = None, day: Optional[str] = None) -> None:
    """One pass over the three indices. Never raises."""
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    day = day or time.strftime("%Y-%m-%d")
    for idx in IDXS:
        try:
            d = _DAYS.get(idx)
            if d is None or d.day != day:
                d = _DAYS[idx] = _Day(idx, day)
            d.tick(now_ms)
            out = d.reply(now_ms)
        except Exception as e:                            # the reader's failure stays the reader's
            log.warning("reader %s failed: %s", idx, e, exc_info=True)
            out = {"ok": False, "idx": idx, "day": day, "shadow": True,
                   "why": f"could not check — the reader failed: {type(e).__name__}: {e}"}
        with _LOCK:
            _READ[idx] = out
    try:                                                  # the cross-index read: its failure is its own
        xindex_live.tick(now_ms, day, _DAYS)
    except Exception as e:
        log.warning("xindex failed: %s", e, exc_info=True)
        xindex_live.fail(f"{type(e).__name__}: {e}")


def read(idx: str) -> dict:
    with _LOCK:
        out = _READ.get(idx)
    return out or {"ok": False, "idx": idx, "shadow": True, "why": "could not check — the reader has not run yet"}


def run(day_fn=None, period: float = PERIOD_S) -> None:
    """The thread: one pass every `period` seconds, forever. A pass never raises."""
    while True:
        try:
            tick(day=day_fn() if day_fn else None)
        except Exception as e:                            # belt and braces: the loop outlives any pass
            log.warning("reader pass failed: %s", e)
        time.sleep(period)
