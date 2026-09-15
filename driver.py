"""driver.py -- war-map object E: who is driving.

TWO HALVES, TWO HONESTY LEVELS.

INTRADAY [I]: for each chain refresh, futures volume traded in the window vs
option OI turnover in the same window, both ranked percentile-so-far against
this session (fuse.Rank, the house pattern). Futures leading while the chain
sleeps is the Jane-Street shape -- drive the underlying, collect in options;
options leading is premium being chased. Published as a LEAN, never an
identification: FUTURES_LED / OPTION_LED / BOTH / UNCLEAR, always [I].

EOD [M, one day lagged]: NSE publishes participant-wise open interest daily
(FII / DII / Pro / Client, long and short, by instrument type) -- a free
public CSV, and THE ONLY DATA IN EXISTENCE that actually splits retail from
pro in this market. Fetched once per evening (or lazily next morning),
cached under data/participant/, rendered as context: "Client came in net
long index calls; Pro net short." Labeled with its day, because it is
yesterday's book, not this morning's.

KILL CONDITION (declared at birth, per the plan): if the intraday lean
disagrees with the EOD participant data more often than it agrees over ~30
sessions, the intraday half is DROPPED and only the EOD context stays.

The fetch is the one network touch, lazy and fail-soft: a first call kicks a
daemon thread and reports "fetching"; NSE being down costs the context line
its content, never the endpoint its answer.

Stdlib only. Pure computation apart from the declared EOD fetch/cache.
"""

from __future__ import annotations

import csv
import io
import os
import threading
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional

from fuse import Rank

# --- intraday [I] -----------------------------------------------------------
LEAD_P = 0.80        # rank at/above this reads as "leading"
QUIET_P = 0.50       # ...while the other side at/below this reads as quiet
MIN_HIST = 8         # ranks below this much history are not trusted


class Driver:
    """One per index. Feed it chain-pace snapshots (+ the future's session
    volume when the feed has it); it reports the lean."""

    def __init__(self):
        self._fut_rank = Rank()
        self._oi_rank = Rank()
        self._prev_vtt: Optional[float] = None
        self._prev_oi: Optional[Dict[tuple, float]] = None
        self.read: dict = {"lean": "UNCLEAR", "why": "no snapshot yet",
                           "tag": "I"}

    def on_snapshot(self, fut_vtt: Optional[float],
                    strikes: Optional[List[dict]]) -> dict:
        d_vtt = None
        if fut_vtt is not None and self._prev_vtt is not None:
            d_vtt = max(0.0, fut_vtt - self._prev_vtt)
        if fut_vtt is not None:
            self._prev_vtt = fut_vtt

        oi_now: Dict[tuple, float] = {}
        for s in strikes or []:
            k = s.get("k")
            if k is None:
                continue
            for side in ("ce", "pe"):
                oi = (s.get(side) or {}).get("oi")
                if oi is not None:
                    oi_now[(k, side)] = float(oi)
        d_oi = None
        if self._prev_oi is not None and oi_now:
            d_oi = sum(abs(oi_now[key] - self._prev_oi.get(key, oi_now[key]))
                       for key in oi_now)
        if oi_now:
            self._prev_oi = oi_now

        if d_vtt is None and d_oi is None:
            self.read = {"lean": "UNCLEAR", "tag": "I",
                         "why": "neither futures volume nor chain OI moved "
                                "into view yet"}
            return self.read
        # Every window is ranked, zeros included -- the drain-rank lesson
        # (chainside.py): a Rank that only ever sees action scores the first
        # real burst against an empty history.
        fr = self._fut_rank.rank(d_vtt) if d_vtt is not None else None
        orr = self._oi_rank.rank(d_oi) if d_oi is not None else None
        warm = (len(self._fut_rank) >= MIN_HIST
                or len(self._oi_rank) >= MIN_HIST)
        if not warm:
            lean, why = "UNCLEAR", (f"only {max(len(self._fut_rank), len(self._oi_rank))} "
                                    f"window(s) ranked; need {MIN_HIST}")
        else:
            # "hot" needs REAL flow, not just a high rank: the percentile of
            # 0 in a series of zeros is 1.00 (the chainside drain-rank trap,
            # mirrored), so a dead-quiet tape would otherwise rank "extreme".
            f_hot = fr is not None and fr >= LEAD_P and (d_vtt or 0) > 0
            o_hot = orr is not None and orr >= LEAD_P and (d_oi or 0) > 0
            f_quiet = fr is None or fr <= QUIET_P or not d_vtt
            o_quiet = orr is None or orr <= QUIET_P or not d_oi
            if f_hot and o_quiet:
                lean, why = "FUTURES_LED", ("futures volume at the session's "
                                            "extreme while the chain is quiet -- "
                                            "the drive-the-underlying shape")
            elif o_hot and f_quiet:
                lean, why = "OPTION_LED", ("chain OI turning over hard while "
                                           "the future is quiet -- premium "
                                           "being chased")
            elif f_hot and o_hot:
                lean, why = "BOTH", "both tapes running hot at once"
            else:
                lean, why = "UNCLEAR", "neither tape at an extreme"
        # None when the window held nothing to rank: the percentile of a zero
        # against zeros is 1.00, and "nothing traded" must never render as
        # "volume at the session's extreme" (chainside's drain_rank rule).
        self.read = {"lean": lean, "why": why, "tag": "I",
                     "fut_rank": round(fr, 3) if (fr is not None and d_vtt) else None,
                     "oi_rank": round(orr, 3) if (orr is not None and d_oi) else None,
                     "fut_why": None if d_vtt is not None else
                                "no futures volume on the feed this window"}
        return self.read


# --- EOD participant data [M, one day lagged] -------------------------------
PART_DIR = os.path.join("data", "participant")
PART_URL = ("https://archives.nseindia.com/content/nsccl/"
            "fao_participant_oi_{ddmmyyyy}.csv")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

_part_lock = threading.Lock()
_part_state: dict = {"day": None, "status": "idle", "data": None, "why": None}


def _part_path(day: str) -> str:
    dd = datetime.strptime(day, "%Y-%m-%d").strftime("%d%m%Y")
    return os.path.join(PART_DIR, f"fao_participant_oi_{dd}.csv")


def _parse_participant(text: str) -> Dict[str, dict]:
    """The NSE CSV -> {client_type: {fut_long, fut_short, call_long,
    call_short, put_long, put_short}} for INDEX instruments only."""
    lines = [l for l in text.splitlines() if l.strip()]
    # the header row is the one naming Client Type; NSE pads a title line
    hdr_i = next(i for i, l in enumerate(lines) if "Client Type" in l)
    rows = list(csv.DictReader(io.StringIO("\n".join(lines[hdr_i:]))))
    want = {"fut_long": "Future Index Long", "fut_short": "Future Index Short",
            "call_long": "Option Index Call Long",
            "call_short": "Option Index Call Short",
            "put_long": "Option Index Put Long",
            "put_short": "Option Index Put Short"}
    out = {}
    for r in rows:
        who = (r.get("Client Type") or "").strip()
        if not who or who.upper() == "TOTAL":
            continue
        rec = {}
        for key, col in want.items():
            cell = next((v for c, v in r.items()
                         if c and c.strip() == col), None)
            try:
                rec[key] = int(str(cell).replace(",", "").strip())
            except (TypeError, ValueError):
                rec[key] = None
        out[who] = rec
    return out


def _fetch_participant(day: str) -> Dict[str, dict]:
    path = _part_path(day)
    if not os.path.exists(path):
        dd = datetime.strptime(day, "%Y-%m-%d").strftime("%d%m%Y")
        req = urllib.request.Request(PART_URL.format(ddmmyyyy=dd),
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
        os.makedirs(PART_DIR, exist_ok=True)
        with open(path, "wb") as f:
            f.write(raw)
    with open(path, encoding="utf-8", errors="ignore") as f:
        return _parse_participant(f.read())


def participant_context(day: str) -> dict:
    """The EOD context for `day` (the PRIOR session), non-blocking.

    First call kicks a daemon fetch and answers {"status": "fetching"}; later
    calls serve the parsed cache or the failure with its reason. `day` is
    'YYYY-MM-DD'.
    """
    with _part_lock:
        st = dict(_part_state)
        if st["day"] == day and st["status"] in ("done", "failed", "fetching"):
            return {"status": st["status"], "day": day,
                    "data": st["data"], "why": st["why"],
                    "tag": "M", "lag": "one day -- yesterday's book"}
        _part_state.update({"day": day, "status": "fetching",
                            "data": None, "why": None})

    def work():
        try:
            data = _fetch_participant(day)
            with _part_lock:
                _part_state.update({"status": "done", "data": data})
        except Exception as e:
            with _part_lock:
                _part_state.update(
                    {"status": "failed",
                     "why": f"NSE participant file not fetched: "
                            f"{type(e).__name__}: {e}"})

    threading.Thread(target=work, daemon=True,
                     name=f"participant-{day}").start()
    return {"status": "fetching", "day": day, "data": None, "why": None,
            "tag": "M", "lag": "one day -- yesterday's book"}
