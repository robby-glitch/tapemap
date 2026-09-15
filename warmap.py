"""warmap.py -- the OI war map, assembled. One board per index.

COMPOSITION ONLY, the direction.py precedent: nothing here measures anything
new. levels.py says WHERE the battlefield is, dwell.py whether a trap is
loading, chainside/trapped_inventory who is already underwater, hunt.py which
runway pays, sequence.py where each level is in the playbook, driver.py whose
tape is doing the driving. This file feeds them all from the same chain
snapshot the senses loop already pays for, and serves one assembled state to
/api/warmap.

EVERYTHING RUNS AT CHAIN PACE (~10s per index), never at the 0.5s book tick,
and `state()` serves the last assembled reading rather than recomputing per
HTTP request -- the same budget discipline as `_log_chain_pace`.

THE DAILY-CANDLE FETCH is a daemon thread this board owns, kicked on the
first snapshot, retried on a cooldown until it lands, re-kicked on day
rollover. Until it lands the map carries `daily_why` and draws what it has --
an absent PDH is a stated absence, never a guessed level.

SHADOW END TO END. No module below gates anything; the sequence machine's
forward log is the only record and it starts its 30-session clock at the
next open. No order path, no hit rate, describes-never-decides.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

import driver as driver_mod
import dwell as dwell_mod
import hunt
import levels as levels_mod
import sequence as sequence_mod

FETCH_RETRY_S = 600      # daily-candle fetch retry cooldown on failure


class WarMap:
    """One index's war map. Feed on_snapshot at chain pace; read state()."""

    def __init__(self, idx: str, seq_path: Optional[str] = None,
                 fetch=levels_mod.fetch_daily):
        self.idx = idx
        self.levels = levels_mod.Levels(idx)
        self.dwell = dwell_mod.DwellWatch()
        self.seq = sequence_mod.Sequencer(idx, path=seq_path)
        self.driver = driver_mod.Driver()
        self._fetch = fetch              # test seam
        self._fetching = False
        self._fetched_day: Optional[str] = None
        self._next_try = 0.0
        self.last: dict = {"ok": False, "why": "no chain snapshot yet"}
        # THE MORNING, REBUILT (the anytime-start rule). A process started at
        # 09:41 has machines that know nothing of 09:15-09:41 unless the
        # backfilled minute grid (chain_backfill -> ChainState.minutes, rows
        # src=backfill) is replayed through them first. Done ONCE, on the
        # first chain snapshot after both that grid and the daily levels have
        # landed; the replay's transitions go to a SEPARATE file tagged
        # backfill:true (the VPIN precedent) so the observed forward log is
        # never mixed with a reconstruction. `backfill` on state() says what
        # landed, or why nothing did.
        self._daily_failed = False
        self._first_sec: Optional[int] = None
        self.backfill: dict = {"done": False, "why": "no chain snapshot yet"}

    # -- the daily fetch, off-thread ----------------------------------------
    def _kick_daily(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if (self._fetching or self._fetched_day == today
                or time.monotonic() < self._next_try):
            return
        self._fetching = True

        def work():
            try:
                self.levels.set_daily(self._fetch(self.idx))
                self._fetched_day = today
            except Exception as e:
                self.levels.set_daily_error(
                    f"daily candles not fetched: {type(e).__name__}: {e} "
                    f"(retrying in {FETCH_RETRY_S // 60} min)")
                self._next_try = time.monotonic() + FETCH_RETRY_S
                self._daily_failed = True     # the replay stops waiting for PDH
            finally:
                self._fetching = False

        threading.Thread(target=work, daemon=True,
                         name=f"warmap-daily-{self.idx}").start()

    # -- the feed ------------------------------------------------------------
    def _legs(self, strikes: List[dict], chain_side) -> List[dict]:
        """chainside's ledgers + the live chain -> hunt.py's leg shape."""
        by_k = {s.get("k"): s for s in strikes or []}
        out = []
        for (k, side), led in getattr(chain_side, "_led", {}).items():
            leg = (by_k.get(k) or {}).get(side) or {}
            out.append({"k": k, "side": side, "oi": leg.get("oi"),
                        "ltp": leg.get("ltp"), "basis": led.basis,
                        "delta": leg.get("delta")})
        return out

    @staticmethod
    def _heat(strikes: List[dict], chain_side) -> List[dict]:
        """Per-strike OI + day change + pain, the map's paint. [M] except
        pain, which inherits trapped_inventory's [I]."""
        led = getattr(chain_side, "_led", {})
        rows = []
        for s in strikes or []:
            k = s.get("k")
            if k is None:
                continue
            row = {"k": k}
            for side in ("ce", "pe"):
                leg = s.get(side) or {}
                row[side + "_oi"] = leg.get("oi")
                row[side + "_chg"] = leg.get("oi_chg")
                l = led.get((k, side))
                pain = None
                if l is not None and leg.get("ltp") is not None:
                    _s, p = l.trapped(float(leg["ltp"]))
                    pain = round(p, 2) if p > 0 else 0.0
                row[side + "_pain"] = pain
                # HOW MUCH OF THIS BOOK THE LEDGER ACTUALLY WATCHED BUILD:
                # "none" / "low" / "session" (trapped_inventory.Ledger.
                # confidence -- "low" means under half the current size was
                # seen being built). NOT a confidence SCORE and not forbidden
                # by house rule 4: it is a coverage statement about the
                # ledger's own observation, the same string
                # `Ledger.snapshot()` has always published, and it carries no
                # claim about whether the read is right.
                #
                # Without it `_pain` is unreadable. A basis built watching 90%
                # of a wall and one inferred from the 10% that happened after
                # an 11:00 start produce the same-looking number, and the
                # second is nearly worthless. None when there is no ledger for
                # this leg at all -- a different sentence from "none", which
                # means the ledger exists and has no basis yet.
                row[side + "_conf"] = None if l is None else l.confidence()
            rows.append(row)
        rows.sort(key=lambda r: r["k"])
        return rows

    # -- the morning, rebuilt -------------------------------------------------
    SEED_OPEN_S = 9 * 3600 + 17 * 60   # a start by 09:17 has no morning to rebuild
    SEED_OPEN_M = "09:20"              # a grid whose first mark is by here has its open
    SEED_WAIT_S = 600                  # give the REST walk this long to land, then say so

    def _try_seed(self, grid: Optional[dict], sec: Optional[int],
                  strikes: List[dict], now: Optional[datetime]) -> None:
        if sec is None:
            return
        if self._first_sec is not None and self._first_sec <= self.SEED_OPEN_S:
            self.backfill = {"done": True, "minutes": 0,
                             "why": "started at the open; nothing to rebuild"}
            return
        if self.levels.daily is None and not self._daily_failed:
            self.backfill["why"] = "waiting for the daily levels before replaying"
            return                # PDH/PDL machines must exist DURING the replay
        # A copy: the poller writes `now` into this dict from its own thread.
        # EVERY minute before this snapshot is replayed, whatever wrote it:
        # rows with src=backfill came from REST candles, rows with no src were
        # OBSERVED by an earlier process today and restored. Both are the day;
        # only the tag differs. The grid is ready once its first mark is at
        # the open (the REST walk landed, or the earlier process was up from
        # 09:15); otherwise wait SEED_WAIT_S, then replay what there is and
        # name the missing stretch.
        bf = {m: r for m, r in dict(grid or {}).items() if r.get("spot") is not None}
        first = min(bf) if bf else None
        waited = sec - (self._first_sec or sec)
        if first is None or (first > self.SEED_OPEN_M and waited <= self.SEED_WAIT_S):
            self.backfill["why"] = ("waiting for the backfilled minute grid" if first is None
                                    else f"grid starts {first}; waiting for the REST walk to fill the open")
            return
        # Session-open OI per strike = live oi - live oi_chg (Upstox: chg is
        # since 09:15). The grid holds chg per minute; base + chg is the OI
        # the wall-finder, dwell and driver actually read. A strike the live
        # window no longer carries is left out rather than guessed.
        base = {}
        for s in strikes or []:
            for side in ("ce", "pe"):
                leg = s.get(side) or {}
                if s.get("k") is not None and leg.get("oi") is not None \
                        and leg.get("oi_chg") is not None:
                    base[(float(s["k"]), side)] = float(leg["oi"]) - float(leg["oi_chg"])
        cur_m = f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}"
        marks = [m for m in sorted(bf) if m < cur_m]
        if not marks:
            self.backfill = {"done": True, "minutes": 0,
                             "why": "grid holds no minute before this snapshot"}
            return
        live_path = self.seq.path
        bf_path = (live_path or sequence_mod.day_path()).replace(".jsonl", "_backfill.jsonl")
        self.dwell = dwell_mod.DwellWatch()
        self.seq = sequence_mod.Sequencer(self.idx, path=bf_path)
        self.driver = driver_mod.Driver()
        day = now or datetime.now()
        fired = 0
        for m in marks:
            r = bf[m]
            self.seq.extra = {"backfill": True,
                              "src": "rest_1m" if r.get("src") == "backfill" else "observed"}
            hh, mm = int(m[:2]), int(m[3:5])
            rows = []
            for k, chg in (r.get("k") or {}).items():
                leg = {"k": k}
                for side, c in (("ce", chg[0]), ("pe", chg[1])):
                    b = base.get((float(k), side))
                    leg[side] = {"oi": (b + c) if (b is not None and c is not None) else None}
                rows.append(leg)
            lv = self.levels.read(r["spot"], None, rows)
            dw = self.dwell.on_snapshot(hh * 3600 + mm * 60, r["spot"], rows, lv["levels"])
            band = self.dwell.band(r["spot"])
            fired += len(self.seq.on_snapshot(
                r["spot"], band, lv["levels"], dw,
                now=day.replace(hour=hh, minute=mm, second=0, microsecond=0)))
            self.driver.on_snapshot(None, rows)   # no futures volume in the grid: stated, not faked
        self.seq.path, self.seq.extra = live_path, {}
        nb = sum(1 for m in marks if bf[m].get("src") == "backfill")
        gap = first if first > self.SEED_OPEN_M else None
        self.backfill = {"done": True, "from": marks[0], "to": marks[-1],
                         "minutes": len(marks), "backfilled": nb,
                         "observed": len(marks) - nb, "missing_before": gap,
                         "transitions": fired, "log": bf_path, "tag": "backfill",
                         "why": (f"replayed {len(marks)} minute(s) {marks[0]}-{marks[-1]} "
                                 f"({nb} rebuilt from REST candles, {len(marks) - nb} "
                                 f"observed by an earlier process today) through fresh "
                                 f"dwell, sequence and driver machines before the first "
                                 f"live snapshot"
                                 + (f"; NOTHING before {gap} -- the REST walk did not "
                                    f"land and that stretch is missing" if gap else "")
                                 + "; the grid carries no futures volume, bid/ask or "
                                   "ledger basis, so the driver ranked on OI alone and "
                                   "dwell has no crossing evidence for that stretch")}

    def on_snapshot(self, doc: dict, chain_side=None,
                    fut_vtt: Optional[float] = None,
                    now: Optional[datetime] = None,
                    grid: Optional[dict] = None) -> dict:
        self._kick_daily()
        spot = doc.get("spot")
        # The PUBLISHED payload carries "ts" ("HH:MM:SS") but not "sec" --
        # that field only exists on the internal snapshot before _publish
        # (chain_live.py). Found on the first mock run: doc.get("sec") was
        # None on every snapshot and the dwell clock never started.
        sec = doc.get("sec")
        if sec is None:
            ts = doc.get("ts") or ""
            if len(ts) >= 8 and ts[2] == ":":
                sec = (int(ts[:2]) * 3600 + int(ts[3:5]) * 60 + int(ts[6:8]))
        strikes = doc.get("strikes") or []
        metrics = doc.get("metrics") or {}
        if sec is not None and self._first_sec is None:
            self._first_sec = sec
        if not self.backfill["done"]:
            self._try_seed(grid, sec, strikes, now)

        lv = self.levels.read(spot, metrics, strikes)
        dw = (self.dwell.on_snapshot(sec, spot, strikes, lv["levels"])
              if sec is not None else {"active": False,
                                       "why": "snapshot carries no clock"})
        band = self.dwell.band(spot)
        seq_fired = self.seq.on_snapshot(spot, band, lv["levels"], dw, now=now)
        dr = self.driver.on_snapshot(fut_vtt, strikes)
        legs = self._legs(strikes, chain_side) if chain_side else []
        run = hunt.runways(spot, lv["levels"], legs, band)

        self.last = {
            "ok": True, "idx": self.idx, "ts": doc.get("ts"),
            "spot": spot, "band": round(band, 2) if band else None,
            "levels": lv["levels"], "daily_why": lv["daily_why"],
            "dwell": dw, "runways": run, "driver": dr,
            "heat": self._heat(strikes, chain_side),
            "seq_fired": seq_fired,
            "flip_px": metrics.get("flip_px"),
            "max_pain": metrics.get("max_pain"),
            "note": "shadow end to end -- describes, never decides; "
                    "[M]/[I] ride on every reading",
        }
        return self.last

    def state(self) -> dict:
        out = dict(self.last)
        out["sequence"] = self.seq.state()
        out["seq_log"] = {"written": self.seq.written,
                          "failed": self.seq.failed,
                          "path": self.seq.path or sequence_mod.day_path()}
        out["backfill"] = self.backfill
        return out


class Boards:
    """One WarMap per index -- the drag.Board pattern, one level up."""

    def __init__(self):
        self._by: Dict[str, WarMap] = {}

    def for_index(self, idx: str) -> WarMap:
        if idx not in self._by:
            self._by[idx] = WarMap(idx)
        return self._by[idx]

    def states(self) -> Dict[str, dict]:
        return {idx: b.state() for idx, b in self._by.items()}
