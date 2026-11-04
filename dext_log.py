# tapemap/dext_log.py
"""dext_log.py -- THE DEXT RECORD (gate 3 of retiring GoCharting). data/dext/.

The Dext (Dhan) order-flow extension's service worker POSTs its chart's closed 1-minute getOrderFlow candles and its
getData OHLC rows to /api/dext/candles. This file keeps them, raw, per instrument per IST day:
  dext_<EXCH>-<SEC_ID>_<day>.jsonl        one 1m candle per line, Dext's own fields and units (CONTRACTS, epoch s)
  dext_ohlc_<EXCH>-<SEC_ID>_<day>.jsonl   one 1-minute getData row per line: t, o, h, l, c, v, oi
  dext_ohlc5m_<EXCH>-<SEC_ID>_<day>.jsonl a coarser chart's getData rows (5m here), kept apart: getData comes at the chart's
                                          timeframe, and a 5m bar sharing t with a minute overwrote it (A240, 2-4 Nov)
  instruments.json                        {key: {EXCH, SEG, SEC_ID, name, lot}}; lot stays null until someone knows it
Nothing else is ever stored: every field is allow-listed and range-checked, and an absurd payload is refused whole.

RECORDING ONLY. No engine, frame, signal or log TapeMap decides on reads this directory; dext_parity.py does.

IDEMPOTENT BY t, APPEND ONLY. A re-sent minute that is byte-identical to what is on disk is not written again; a
changed one is appended and the LAST copy wins on read (read_candles / read_ohlc return one row per t). A day file is
read once per process to learn what is on it, never rewritten per request -- the 2026-09-18 wedge was a 55 MB rewrite
per POST.
"""
from __future__ import annotations

import json
import math
import os
import re
import threading
import time
from typing import Dict, List, Optional

DIR = os.path.join("data", "dext")
MAX_CANDLES, MAX_OHLC, MAX_LEVELS = 2000, 2000, 1000      # per request / per candle; the extension sends <= 1,500

CANDLE_NUM = ("high", "low", "buy_volume", "sell_volume", "neutral_volume", "total_volume", "delta", "cumulative_delta")
LEVEL_NUM = ("price", "buy_volume", "sell_volume", "neutral_volume", "total_volume", "delta")
OHLC_NUM = ("o", "h", "l", "c", "v", "oi")
SIGNED = {"delta", "cumulative_delta"}
_TIME = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$")
_NAME = re.compile(r"^[\w &.()-]{1,60}$")
_SEEN: Dict[str, Dict[int, int]] = {}      # day file -> {t: hash of the line on disk}
_LOCK = threading.Lock()                   # ponytail: one lock for every file; per-file locks if two charts ever contend


class Refused(ValueError):
    """An absurd payload: nothing from it is stored."""


def tag(inst: dict) -> str:
    return f"{inst['EXCH']}-{inst['SEC_ID']}"


def candles_path(t: str, day: str) -> str:
    return os.path.join(DIR, f"dext_{t}_{day}.jsonl")


def ohlc_path(t: str, day: str, step: int = 60) -> str:
    return os.path.join(DIR, f"dext_ohlc{'' if step == 60 else f'{step // 60}m'}_{t}_{day}.jsonl")


def _step(rows: List[dict]) -> Optional[int]:
    """A getData batch's bar size in seconds, from its own spacing; None = a lone row (could be either)."""
    ts = sorted({r["t"] for r in rows})
    return min(b - a for a, b in zip(ts, ts[1:])) if len(ts) > 1 else None


def _num(v, key, signed=False):
    """None stays None (Dext sometimes omits a column); anything else must be a finite, sane number."""
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) >= 1e12 or (v < 0 and not signed):
        raise Refused(f"{key} is not a sane number")
    return v


def _t(v) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not 1.5e9 < v < 4.2e9 or v != int(v) or int(v) % 60:
        raise Refused("t must be an epoch second on a whole minute")
    return int(v)


def _inst(doc: dict) -> dict:
    i = doc.get("inst")
    if not isinstance(i, dict):
        raise Refused("inst must be {EXCH, SEG, SEC_ID}")
    ex, seg, sid = str(i.get("EXCH") or ""), str(i.get("SEG") or ""), str(i.get("SEC_ID") or "")
    if not (re.fullmatch(r"[A-Z]{2,8}", ex) and re.fullmatch(r"[A-Z0-9]{0,8}", seg) and re.fullmatch(r"\d{1,10}", sid)):
        raise Refused("inst must be {EXCH, SEG, SEC_ID}")
    return {"EXCH": ex, "SEG": seg, "SEC_ID": sid}


def clean_candle(c) -> dict:
    if not isinstance(c, dict):
        raise Refused("a candle is not an object")
    tm = c.get("time")
    if tm is not None and not (isinstance(tm, str) and _TIME.match(tm)):
        raise Refused("time must be YYYY-MM-DD HH:MM:SS")
    lv = c.get("levels") or []
    if not isinstance(lv, list) or len(lv) > MAX_LEVELS:
        raise Refused("levels must be a list of at most %d" % MAX_LEVELS)
    out = {"t": _t(c.get("t")), "time": tm}
    out.update({k: _num(c.get(k), k, k in SIGNED) for k in CANDLE_NUM})
    levels = []
    for x in lv:
        if not isinstance(x, dict):
            raise Refused("a level is not an object")
        levels.append({k: _num(x.get(k), k, k in SIGNED) for k in LEVEL_NUM})
    out["levels"] = levels
    return out


def clean_ohlc(r) -> dict:
    if not isinstance(r, dict):
        raise Refused("an ohlc row is not an object")
    return {"t": _t(r.get("t")), **{k: _num(r.get(k), k) for k in OHLC_NUM}}


def ist_day(t: int) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(t + 19800))


def _seen(p: str) -> Dict[int, int]:
    if p not in _SEEN:
        seen: Dict[int, int] = {}
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    try:
                        seen[json.loads(line)["t"]] = hash(line)
                    except (ValueError, KeyError, TypeError):
                        continue              # a torn line is skipped, never fatal
        except OSError:
            pass
        _SEEN[p] = seen
    return _SEEN[p]


def _append(rows: List[dict], path_of, fill_only: bool = False) -> Dict[str, int]:
    """Rows grouped by IST day; each day file gets only the lines that differ from what it holds (fill_only: only a t it
    lacks). -> {day: accepted}."""
    by: Dict[str, List[dict]] = {}
    for r in rows:
        by.setdefault(ist_day(r["t"]), []).append(r)
    for day, rs in by.items():
        p = path_of(day)
        seen, new = _seen(p), []
        for r in rs:
            line = json.dumps(r, separators=(",", ":"))
            if fill_only and r["t"] in seen:
                continue
            if seen.get(r["t"]) != hash(line):
                seen[r["t"]] = hash(line)
                new.append(line)
        if new:
            os.makedirs(DIR, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write("".join(x + "\n" for x in new))
    return {d: len(rs) for d, rs in by.items()}


def _register(inst: dict, name: Optional[str]) -> None:
    p, k = os.path.join(DIR, "instruments.json"), tag(inst)
    try:
        with open(p, encoding="utf-8") as f:
            reg = json.load(f)
    except (OSError, ValueError):
        reg = {}
    have = reg.get(k) or {}
    row = {**inst, "name": name or have.get("name"), "lot": have.get("lot")}     # a lot someone wrote in stays
    if have == row:
        return
    reg[k] = row
    os.makedirs(DIR, exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=1)
    os.replace(p + ".tmp", p)


def instruments() -> dict:
    try:
        with open(os.path.join(DIR, "instruments.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def store(doc) -> dict:
    """POST /api/dext/candles' body -> {ok, stored: {day: n}, last_t}. Raises Refused on an absurd payload (nothing
    stored). Every candle and row is checked before anything is written."""
    if not isinstance(doc, dict):
        raise Refused("body must be an object")
    inst = _inst(doc)
    name = doc.get("name")
    if name is not None and not (isinstance(name, str) and _NAME.match(name) and not re.search(r"\d{8,}", name)):
        raise Refused("name must be a plain instrument name")
    cs, oh = doc.get("candles") or [], doc.get("ohlc") or []
    if not isinstance(cs, list) or not isinstance(oh, list) or len(cs) > MAX_CANDLES or len(oh) > MAX_OHLC:
        raise Refused(f"at most {MAX_CANDLES} candles and {MAX_OHLC} ohlc rows per request")
    cs, oh = [clean_candle(c) for c in cs], [clean_ohlc(r) for r in oh]
    k = tag(inst)
    with _LOCK:
        _register(inst, name)
        stored = _append(cs, lambda d: candles_path(k, d))
        step = _step(oh)              # a lone row only fills a hole in the minutes: it may be a 5m bar
        _append(oh, lambda d: ohlc_path(k, d, step or 60), fill_only=step is None)
    return {"ok": True, "stored": stored, "last_t": max((c["t"] for c in cs), default=None)}


def _read(p: str) -> List[dict]:
    by: Dict[int, dict] = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    by[r["t"]] = r            # last copy wins
                except (ValueError, KeyError, TypeError):
                    continue
    except OSError:
        return []
    return [by[t] for t in sorted(by)]


def read_candles(t: str, day: str) -> List[dict]:
    return _read(candles_path(t, day))


def read_ohlc(t: str, day: str, step: int = 60) -> List[dict]:
    return _read(ohlc_path(t, day, step))
