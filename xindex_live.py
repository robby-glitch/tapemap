"""xindex_live.py -- the SHADOW cross-index read (xindex.py) run on the reader thread's pass (reader_live.tick).

Per 3-minute bar close B (09:18 ... 15:30), once every index has had its minutes up to B stepped:
  * the reader's state per index AS OF B: reader_live records a snapshot on each bar close while it steps minutes, so a
    restart (which re-steps the book from its first row) rebuilds the same snapshots -- ANYTIME START, no repaint;
  * her zone machine's per-bar state for that bar, from the server's own /api/data payload (seam `_CFG["zone"]`); a
    payload from another session or a bar not served yet is CAN'T CHECK, never guessed;
  * the option chain file (read-only) now vs WRITE_MIN minutes before, for the walls;
  -> xindex.step(); every NEW bar is appended to data/xindex/xindex_<day>.jsonl (append-only, never twice); GET
  /api/xindex serves the latest output plus the day's LOOK HERE changes.

ISOLATION: reader_live calls tick() inside its own try; any failure here is served as "could not check" and costs the
reader, fold and the feed nothing. SHADOW: unsigned sheet; only the Trade tab's "LEGS · shadow" panel shows it.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

import xindex

log = logging.getLogger("tapemap.xindex")
DIR = os.path.join("data", "xindex")
WAIT_BARS = 2                         # a bar waits at most this many bars for its zone payload, then reads CAN'T CHECK
_CFG: Dict[str, object] = {"zone": None, "chain_dir": None}     # seams, set by server.py; tests inject them
_LOCK = threading.Lock()
_S: Dict[str, object] = {"day": None}
_READ: Dict[str, object] = {}


def log_path(day: str) -> str:
    return os.path.join(DIR, f"xindex_{day}.jsonl")


def snapshot(eng) -> dict:
    """The reader's state as xindex reads it (reader objects only: nothing recomputed)."""
    if eng is None or eng.delta is None or not eng.m:
        return {"ok": False, "why": "reader warming: no ruler yet"}
    return {"ok": True, "ruler": eng.delta, "legs": list(eng.legs), "forming": eng.forming(),
            "auction": eng.auction_state(), "t_last": eng.m[-1]["t"], "px": eng.m[-1]["c"]}


def bar_closes(day: str) -> List[int]:
    base = int(datetime.fromisoformat(f"{day}T00:00:00+05:30").timestamp() * 1000)
    return [base + m * 60000 for m in range(555 + 3, 15 * 60 + 31, 3)]


def _zone(idx: str, day: str, close: int):
    """(zone for xindex or None, why). The zone machine's own state for the bar that closed at `close`."""
    f = _CFG.get("zone")
    if f is None:
        return None, "zone seam not wired"
    z = f(idx)
    if not z:
        return None, "zone payload not readable"
    lbl = str(z.get("label") or "")
    if lbl and not lbl.startswith(datetime.fromisoformat(day).strftime("%b %d")):
        return None, f"zone payload is another session ({lbl})"
    want = xindex.hm(close - 3 * 60000)
    out = {}
    for key, rows in (("buy", z.get("buy")), ("sell", z.get("sell"))):
        e = next((r for r in rows or [] if isinstance(r, dict) and r.get("t") == want), None)
        if e is None:
            return None, f"zone bar {want} not served yet"
        ref = e.get("ref_high") if key == "buy" else e.get("ref_low")
        out[key] = {"state": e.get("state"), "level": e.get("level"), "ref": ref, "stop": e.get("stop"),
                    "exit": e.get("exit_why")}                  # stop / vwap on the bar her trade closed
    return out, None


class _Chain:
    """Today's chain file for one index, tailed read-only: {minute of day: last row}."""

    def __init__(self, path: str):
        self.path, self.off, self.rest, self.by = path, 0, b"", {}

    def read(self) -> Dict[int, dict]:
        try:
            with open(self.path, "rb") as f:
                f.seek(self.off)
                chunk = f.read()
        except OSError:
            return self.by
        self.off += len(chunk)
        lines = (self.rest + chunk).split(b"\n")
        self.rest = lines.pop()
        for ln in lines:
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            ts = r.get("ts") if isinstance(r, dict) else None
            if isinstance(ts, str) and len(ts) >= 5:
                self.by[int(ts[:2]) * 60 + int(ts[3:5])] = r
        return self.by


def _before(by: Dict[int, dict], m: int) -> Optional[dict]:
    ks = [k for k in by if k <= m]
    return by[max(ks)] if ks else None


def _walls(ch: Optional[_Chain], close: int, s: dict, lot: int, day: str):
    if ch is None or not s.get("ok"):
        return None
    by = ch.read()
    m = xindex.mod(close) - 1
    now, then = _before(by, m), _before(by, m - int(xindex.TH["WRITE_MIN"]))
    if now is None or m - (int(now["ts"][:2]) * 60 + int(now["ts"][3:5])) > 3:
        return None
    return xindex.walls(now, then, s["px"], s["ruler"], lot, day)


def _open_day(day: str) -> None:
    keys, last, looks = set(), None, []
    try:
        with open(log_path(day), encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                keys.add(r.get("asof"))
                last = r.get("out")
                lk = (last or {}).get("look") or {}
                if not looks or looks[-1]["idx"] != lk.get("idx"):
                    looks.append({"t": (last or {}).get("t"), "idx": lk.get("idx"), "line": lk.get("line")})
    except OSError:
        pass
    chain_dir = (_CFG.get("chain_dir") or (lambda: os.path.join("data", "chain")))()
    _S.clear()
    _S.update(day=day, keys=keys, state=None, done=set(), out=last, looks=looks, first_live=None,
              chains={i: _Chain(os.path.join(chain_dir, f"chain_{i}_{day}.jsonl")) for i in xindex.IDXS})


def tick(now_ms: int, day: str, days: Dict[str, object]) -> None:
    """Step every bar close that is due. `days` = reader_live's per-index _Day objects (snaps, eng, stepped, lot)."""
    if _S.get("day") != day:
        _open_day(day)
    for close in bar_closes(day):
        if close in _S["done"]:
            continue
        if close + 5000 > now_ms:
            break
        snaps, wait = {}, False
        for i in xindex.IDXS:
            d = days.get(i)
            eng = getattr(d, "eng", None)
            snap = (getattr(d, "snaps", {}) or {}).get(close)
            if snap is None:
                if eng is None:
                    snap = {"ok": False, "why": "could not check — no Upstox book rows yet"}
                elif d.stepped + 60000 <= close:
                    snap = snapshot(eng)            # nothing stepped past B: its state as of B (a stale t_last = a hole)
                else:
                    snap = {"ok": False, "why": "no reader state recorded for this bar"}
            snap = dict(snap)
            if snap.get("ok"):
                z, zwhy = _zone(i, day, close)
                if z is None and "not served yet" in (zwhy or "") and now_ms - close < WAIT_BARS * 3 * 60000:
                    wait = True
                snap["zone"], snap["zone_why"] = z, zwhy
                snap["walls"] = _walls(_S["chains"].get(i), close, snap, int(getattr(d, "lot", 1) or 1), day)
            snaps[i] = snap
        if wait:
            break
        out, _S["state"] = xindex.step(close, snaps, _S["state"])
        _S["done"].add(close)
        if close in _S["keys"]:
            continue                                    # already logged (a restart): said once, never again
        _S["keys"].add(close)
        row = {"day": day, "asof": close, "t": out["t"], "at": now_ms, "rev": xindex.REV, "shadow": True,
               "late": now_ms - close > 60000, "out": out}
        _S["out"] = out
        lk = out["look"]
        if not _S["looks"] or _S["looks"][-1]["idx"] != lk["idx"]:
            _S["looks"].append({"t": out["t"], "idx": lk["idx"], "line": lk["line"]})
        try:
            os.makedirs(DIR, exist_ok=True)
            with open(log_path(day), "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        except OSError as e:                            # the record failed; the read still serves
            log.warning("xindex log write failed: %s", e)
    with _LOCK:
        _READ.clear()
        _READ.update(ok=_S.get("out") is not None, day=day, out=_S.get("out"), looks=list(_S.get("looks") or []),
                     why=None if _S.get("out") else "warming — the first read is at 09:30 (her 09:25 anchor)")


def fail(why: str) -> None:
    with _LOCK:
        _READ.clear()
        _READ.update(ok=False, why=f"could not check — xindex failed: {why}")


def read() -> dict:
    base = {"shadow": True, "signed": False, "rev": xindex.REV,
            "note": "counts of lines, never a %; unsigned sheet; describes, decides nothing"}
    with _LOCK:
        r = dict(_READ)
    if not r:
        return {**base, "ok": False, "why": "could not check — xindex has not run yet"}
    return {**base, **r, "sheet": {k: v for k, v, _ in xindex.SHEET}}
