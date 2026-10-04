"""trap_log.py -- the trap layer's I/O: its forward log, and the recorders' files it reads.

THE LOG, data/trap/trap_YYYY-MM-DD.jsonl (docs/board/TRAP-PREREG-2026-10-04.md §4): kind "state"
(one per state change, once on its own `key`), kind "slot" (one per index per closed 5-min slot)
and kind "outcome" (per RELEASED, after t+30). The guard is sides_log's, reused: market hours,
weekdays, today's own session, once-only, restart-safe.

THE INPUTS are files other recorders already write; this module only reads them, incrementally,
so a restart rebuilds the read exactly from what is on disk (the anytime-start rule):
  data/warmap/warmap_<day>.jsonl (+ _backfill.jsonl)   sequence.py's level stamps
  data/reader/reader_<IDX>_<day>.jsonl                 reader legs with WHO (rows carrying "leg")
  data/xindex/xindex_<day>.jsonl                       X2 extremes / X3 lead per 3-min bar
  data/vpin_fast.jsonl                                 NIFTY future fast buckets (all days; `day` field)
  data/tape/ux_NIFTY_<day>.jsonl                       Upstox 5-min bars with delta
  data/senses/senses_<day>.jsonl                       swept / pulled quotes (~260 MB a day: only the
                                                       lines naming them are parsed, per minute)
  data/chain/chain_<IDX>_<prev day>.jsonl[.gz]         yesterday's last snapshot -> oi_prev
"""
from __future__ import annotations

import gzip
import json
import os
import time

import sides_log

DIR = os.path.join("data", "trap")
FUT = {"NIFTY": "NIFTY-FUT", "BANKNIFTY": "BANKNIFTY-FUT", "SENSEX": "SENSEX-FUT"}


def append(day, idx, rows, now, d=None):
    return sides_log.append(day, idx, rows, now, d or DIR, "trap")


def unwritten(day, idx, kind, keys, d=None):
    return sides_log.unwritten(day, idx, kind, keys, d or DIR, "trap")


class Tail:
    """One JSONL file followed incrementally; `want(line_bytes)` filters before json parsing."""

    def __init__(self, path, want=None):
        self.path, self.want, self.off, self.rest, self.rows = path, want, 0, b"", []

    def read(self):
        try:
            f = open(self.path, "rb")
        except OSError:
            return self.rows
        with f:
            f.seek(self.off)
            while True:
                chunk = f.read(1 << 24)                  # 16 MB at a time: a day's senses file is ~260 MB
                if not chunk:
                    break
                self.off += len(chunk)
                lines = (self.rest + chunk).split(b"\n")
                self.rest = lines.pop()
                for ln in lines:
                    if not ln or (self.want and not self.want(ln)):
                        continue
                    try:
                        self.rows.append(json.loads(ln))
                    except ValueError:
                        continue
        return self.rows


def _hm_ms(ms):
    return time.strftime("%H:%M", time.localtime(ms / 1000))     # the machine clock IS IST (house fact)


class Day:
    """Every input of one session, for all three indices, followed incrementally."""

    def __init__(self, day, root="data", chain_dir=None, vpin_path=None, dirs=None):
        """`dirs` names each recorder's own folder (the server passes the modules' constants, so a
        --mock-chain run reads its isolated folders); missing ones default under `root`."""
        self.day, self.root = day, root
        dirs = dict(dirs or {})
        d = lambda k: dirs.get(k) or os.path.join(root, k)
        self.chain_dir = chain_dir or d("chain")
        self.warmap = [Tail(os.path.join(d("warmap"), f"warmap_{day}.jsonl")),
                       Tail(os.path.join(d("warmap"), f"warmap_{day}_backfill.jsonl"))]
        self.reader = {i: Tail(os.path.join(d("reader"), f"reader_{i}_{day}.jsonl"), lambda b: b'"leg": {' in b)
                       for i in FUT}
        self.xindex = Tail(os.path.join(d("xindex"), f"xindex_{day}.jsonl"))
        tag = f'"day": "{day}"'.encode()
        self.vpin = Tail(vpin_path or os.path.join(root, "vpin_fast.jsonl"), lambda b: tag in b)
        self.ux = Tail(os.path.join(d("tape"), f"ux_NIFTY_{day}.jsonl"))
        self.senses = Tail(os.path.join(d("senses"), f"senses_{day}.jsonl"),
                           lambda b: (b'"pulled"' in b or b'"swept"' in b) and b'-FUT"' in b)
        self.minutes = {i: {} for i in FUT}             # idx -> 'HH:MM' -> pulled/swept sums
        self._sn = 0
        self._prev = {}

    def stamps(self):
        """warmap's day as ONE machine per index: the last restart's replay of the morning (backfill) and
        the live rows after its last mark. A replay re-runs fresh machines from the session's first mark and
        the live machine continues from it, so an earlier process's live rows before the replay's end, and
        earlier replays, are superseded -- never counted twice (a restart mid-day doubled them otherwise)."""
        live, bf = self.warmap[0].read(), self.warmap[1].read()
        out = []
        for i in FUT:
            run, prev = [], None
            for r in bf:
                if r.get("idx") != i:
                    continue
                ts = r.get("ts") or ""
                if prev is not None and ts < prev:      # a later restart's replay starts again from the morning
                    run = []                            # ponytail: a replay that fires nothing is not seen
                run.append(r)
                prev = ts
            end = run[-1].get("ts") or "" if run else ""
            out += [dict(r, backfill=True) for r in run]
            out += [r for r in live if r.get("idx") == i and (r.get("ts") or "") > end]
        return out

    def legs(self, idx):
        rows = self.reader[idx].read()
        if not rows and not os.path.exists(self.reader[idx].path):
            return None
        out, seen = [], set()
        for r in rows:
            g = r.get("leg") or {}
            if not g.get("t0") or g.get("id") in seen:
                continue
            seen.add(g.get("id"))
            out.append({"t0": _hm_ms(g["t0"]), "t1": _hm_ms(g["t1"]), "dir": g.get("dir"),
                        "who": (g.get("who") or {}).get("class"), "oi": (g.get("oi") or {}).get("moved")})
        return out

    def xin(self):
        rows = self.xindex.read()
        if not rows and not os.path.exists(self.xindex.path):
            return None
        return [{"t": r.get("t"), "extremes": (r.get("out") or {}).get("extremes"), "lead": (r.get("out") or {}).get("lead")}
                for r in rows if r.get("t")]

    def _senses(self):
        rows = self.senses.read()
        inst = {v: k for k, v in FUT.items()}
        for r in rows[self._sn:]:
            i = inst.get(r.get("inst"))
            if i is None or not r.get("t"):
                continue
            b = self.minutes[i].setdefault(r["t"][:5], {})
            k = f"{r.get('kind')}_{r.get('side')}"
            b[k] = b.get(k, 0.0) + (r.get("qty") or 0.0)
        self._sn = len(rows)
        self.senses.rows = []                            # the per-minute sums are the record; free the rows
        self._sn = 0

    def tape(self, idx):
        """NIFTY only (prereg §3); None for the others."""
        if idx != "NIFTY":
            return None
        self._senses()
        vp = [{"at": r.get("at"), "buy": r.get("buy") or 0.0, "sell": r.get("sell") or 0.0}
              for r in self.vpin.read() if r.get("day") == self.day and r.get("at")]
        ux = [{"t": _hm_ms(r["t"]), "delta": r.get("delta"), "vol": r.get("vol")} for r in self.ux.read() if r.get("t")]
        mins = self.minutes["NIFTY"]
        if not vp and not ux and not mins:
            return None
        return {"vpin": vp, "ux": ux, "minutes": mins}

    def pulled(self, idx):
        self._senses()
        return {m: {"pulled_buy": v.get("pulled_buy"), "pulled_sell": v.get("pulled_sell")}
                for m, v in self.minutes[idx].items()}

    def oi_prev(self, idx):
        """Yesterday's closing book per strike: {k: {"ce": (oi, avg, ltp), "pe": ...}}, from its last snapshot."""
        if idx in self._prev:
            return self._prev[idx]
        got = None
        prev = sides_log.prev_session_path(self.chain_dir, idx, self.day)
        if prev:
            last = None
            op = gzip.open if prev[1].endswith(".gz") else open
            with op(prev[1], "rt", encoding="utf-8") as f:
                for line in f:
                    if '"strikes"' in line:
                        last = line
            if last:
                snap = json.loads(last)
                got = {"day": prev[0], "k": {float(r["k"]): {s: ((r.get(s) or {}).get("oi"), (r.get(s) or {}).get("avg"),
                                                             (r.get(s) or {}).get("ltp")) for s in ("ce", "pe")}
                                           for r in snap.get("strikes") or ()}}
        self._prev[idx] = got
        return got
