"""feed_health.py -- is the GoCharting tape alive? Read from DATA, never from a timer alone (docs/reader/6-judgement.md
§3.7, must-fix 11; 7-final-design.md §3.1 P3): post arrival, the extension's heartbeat, bar lag, and GoCharting-vs-Upstox
lots for the same closed bars. One tracker per index, fed by POST /api/frame, read by GET /api/feed/gc and by the replies
the faces already poll (/api/fold*, /api/tape).

Six states, six meanings, never collapsed (house rule 6):
  LIVE            posts arriving, bars advancing, tab visible
  SLOW            posts arriving but throttled (a hidden tab: Chrome aligns hidden timers to ~1/min) -- quiet, not an alarm
  STALLED         posts arrive but bars stop advancing, or a closed GoCharting bar holds well under Upstox's lots
  DEAD            no post for DEAD_S in session, after GoCharting had posted today -- THE alarm (29 Sep, 12:26-16:08)
  NOT OPEN TODAY  no post from GoCharting today (she may not open it some days) -- grey
  AFTER CLOSE     the session is over; the last post's time is kept. A tape that died in session stays DEAD until it posts.

Session bounds are chain_live's, unchanged (her decision 2026-09-29: the 15:40 fix is dropped). `since` is always the
moment the CONDITION began, computed from the data (last post + DEAD_S, the bar's close, ...), never the moment a
reader noticed. Pure apart from the optional transition log; fail-soft everywhere it is called.
"""
from __future__ import annotations

import collections
import json
import threading
import time
from datetime import datetime

from chain_live import IST, SESS_CLOSE, SESS_OPEN

# ---- THRESHOLDS (h): provisional, in ONE place. Mary signs these after one hidden-tab measurement of the extension's
# post cadence (7-final-design §5: "after P3 is built: sound on DEAD, once the hidden-tab measurement is in").
# None of them is a lot count.
SLOW_S = 20            # (h) a post gap past this is throttled, not dead
DEAD_S = 90            # (h) no post for this long, in session, after posts today. Keep >= 75 s (§3.7): a hidden tab's timers align to ~60 s
BAR_LAG_S = 90         # (h) the bar that should have closed is not posted within this of its close -> STALLED
STALL_FRAC = 0.80      # (h) a closed GoCharting bar under this fraction of Upstox's lots for the same bin -> STALLED (ticks died inside it)
SOUND_ON_DEAD = False  # OFF until she signs N. The faces read this flag; nothing chimes while it is False.

STATES = ("LIVE", "SLOW", "STALLED", "DEAD", "NOT OPEN TODAY", "AFTER CLOSE")
# what goes to CAN'T CHECK when GoCharting is not LIVE/SLOW, and what keeps working on Upstox alone
DEPENDS_ON_GC = ["her P / A / E / C marks", "GoCharting bars, ladder and stacks (/api/tape bars, the Flow pane)",
                 "the extension's walls (B/S)", "the frame's tape events and the ZONE + FLOW fire", "ux.agree (two-tape agreement)"]
UPSTOX_ONLY = ["Upstox bars (ux)", "fold's ZONE / FLOW / OI / VPIN rows", "the chain", "VPIN"]
DO_ON_DEAD = ("Open the GoCharting tab; if its panel says 'extension context gone', press F5 on that tab. "
              "Your Chrome setting (not ours): Settings > Performance > Memory Saver > 'Always keep these sites active' > gocharting.com.")

LOG = None             # a path for the transition log; the server sets it, tests leave it None
_LOCK = threading.Lock()
_T: dict = {}          # idx -> Tracker


def _sec(ts: float) -> int:
    d = datetime.fromtimestamp(ts, IST)
    return d.hour * 3600 + d.minute * 60 + d.second


def _hms(ts) -> str | None:
    return None if ts is None else datetime.fromtimestamp(ts, IST).strftime("%H:%M:%S")


def _hm(ts) -> str | None:
    return None if ts is None else datetime.fromtimestamp(ts, IST).strftime("%H:%M")


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts, IST).strftime("%Y-%m-%d")


class Tracker:
    """One index's GoCharting tape, as the server saw it today."""

    def __init__(self, idx: str):
        self.idx = idx
        self.day = None
        self.posts = 0
        self.first_post = self.last_post = None
        self.gaps: collections.deque = collections.deque(maxlen=12)
        self.hb = None
        self.last_bar_t = None          # newest closed bar's open, ms
        self.last_bars: dict = {}       # t(ms) -> lots, the newest closed bars, for the volume check
        self.state = None
        self.events: collections.deque = collections.deque(maxlen=200)

    def _reset(self, day):
        self.__init__(self.idx)
        self.day = day

    def on_post(self, now: float, day: str, doc: dict) -> None:
        if day != self.day:
            self._reset(day)                       # a day roll, or yesterday's session re-posted before the open
        if self.last_post is not None:
            self.gaps.append(now - self.last_post)
        self.first_post = self.first_post or now
        self.last_post = now
        self.posts += 1
        hb = doc.get("hb") if isinstance(doc, dict) else None
        self.hb = hb if isinstance(hb, dict) else None
        closed = [b for b in (doc.get("closed") or []) if isinstance(b, dict) and isinstance(b.get("t"), (int, float))]
        if closed:
            closed.sort(key=lambda b: b["t"])
            self.last_bar_t = int(closed[-1]["t"])
            self.last_bars = {int(b["t"]): b.get("vol") for b in closed[-3:]}

    def read(self, now: float, ux_vols: dict | None = None) -> dict:
        """The state at `now` from the data. `ux_vols`: t(ms) -> Upstox lots of the same closed bins, if known."""
        day, sec = _day(now), _sec(now)
        before, after = sec < SESS_OPEN, sec > SESS_CLOSE
        posted = self.day == day and self.last_post is not None
        age = (now - self.last_post) if posted else None
        vis = (self.hb or {}).get("visible") if posted else None
        state, since, why, chip, do, short = None, None, None, None, None, None
        if not posted:
            state = "NOT OPEN TODAY"
            why = "no post from GoCharting today" + (" (the session has not opened)" if before else "")
            chip = "GoCharting aaj khula nahi"
        elif after:
            close_ts = now - (sec - SESS_CLOSE)
            if self.last_post >= close_ts - DEAD_S:
                state, since = "AFTER CLOSE", close_ts
                why, chip = f"session closed; last GoCharting post {_hms(self.last_post)}", f"session band · last GoCharting post {_hm(self.last_post)}"
            else:                                  # it died in session and never came back: the alarm stands until it posts
                state, since = "DEAD", self.last_post + DEAD_S
                why = f"GoCharting stopped posting at {_hms(self.last_post)} and did not return before the close"
                chip, do = f"GoCharting bhej nahi raha · {_hm(since)} se · tab kholo / F5", DO_ON_DEAD
        elif age > DEAD_S:
            state, since = "DEAD", self.last_post + DEAD_S
            why = f"no post from GoCharting for {int(age)} s (last {_hms(self.last_post)})"
            chip, do = f"GoCharting bhej nahi raha · {_hm(since)} se · tab kholo / F5", DO_ON_DEAD
        else:
            # STALLED, from the data: the bar that should have closed is missing, or the newest closed bar is short of Upstox
            if self.last_bar_t is not None and not before:
                due = self.last_bar_t / 1000.0 + 600.0       # the NEXT bar's close
                if now > due + BAR_LAG_S:                     # in session here, so a due bar is a session bar
                    state, since = "STALLED", due + BAR_LAG_S
                    why = f"posts arrive but no bar has closed since {_hm(self.last_bar_t / 1000.0)} (bar due {_hms(due)})"
                    chip = f"GoCharting bars ruke · {_hm(since)} se · bar aage nahi badha"
            if state is None and ux_vols and self.last_bars:
                t = max(self.last_bars)
                gv, uv = self.last_bars.get(t), ux_vols.get(t)
                if isinstance(gv, (int, float)) and isinstance(uv, (int, float)) and uv > 0 and gv < STALL_FRAC * uv:
                    state, since = "STALLED", t / 1000.0 + 300.0
                    short = {"t": _hm(t / 1000.0), "gc": gv, "ux": uv}
                    why = f"GoCharting bar {_hm(t / 1000.0)} holds {gv:.0f} of Upstox's {uv:.0f} lots ({100 * gv / uv:.0f} %): its ticks died inside the bar"
                    chip = f"GoCharting ticks ruke · {_hm(t / 1000.0)} bar adhoora ({gv:.0f}/{uv:.0f})"
            if state is None and (age > SLOW_S or vis == "hidden"):
                state = "SLOW"
                since = (self.last_post + SLOW_S) if age > SLOW_S else self.last_post
                why = (f"posts arriving slowly: last {int(age)} s ago" if age > SLOW_S else "the GoCharting tab is hidden") + " (a hidden tab is throttled by Chrome)"
                chip = f"GoCharting dheere · {_hm(since)} se · tab chhupa hai?"
            if state is None:
                state, since = "LIVE", self.first_post
                why, chip = f"posting; last {_hms(self.last_post)}; {self.posts} posts today", f"GoCharting LIVE · {_hm(self.last_post)}"
        out = {"idx": self.idx, "state": state, "since": _hms(since), "age_s": None if age is None else int(age), "why": why, "chip": chip,
               "do": do, "last_post": _hms(self.last_post) if posted else None, "last_bar": _hm(self.last_bar_t / 1000.0) if posted and self.last_bar_t else None,
               "posts": self.posts if posted else 0, "visible": vis, "hb": self.hb if posted else None, "short_bar": short,
               "alarm": state in ("DEAD", "STALLED"), "sound": bool(SOUND_ON_DEAD and state == "DEAD"),
               "depends_on_gc": DEPENDS_ON_GC, "upstox_only": UPSTOX_ONLY,
               "thresholds": {"slow_s": SLOW_S, "dead_s": DEAD_S, "bar_lag_s": BAR_LAG_S, "stall_frac": STALL_FRAC, "signed": False},
               "tag": "M"}
        if state != self.state:
            ev = {"t": _hms(now), "day": day, "idx": self.idx, "from": self.state, "to": state, "since": out["since"], "why": why}
            self.state = state
            self.events.append(ev)
            _log(ev)
        out["events"] = list(self.events)[-12:]
        return out


def _log(ev: dict) -> None:
    if not LOG:
        return
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev) + "\n")
    except OSError:
        pass


def tracker(idx: str) -> Tracker:
    with _LOCK:
        t = _T.get(idx)
        if t is None:
            t = _T[idx] = Tracker(idx)
        return t


def on_post(idx: str, day: str, doc: dict, now: float | None = None) -> None:
    """Called by the frame door on every accepted POST. Never raises."""
    try:
        t = tracker(idx)
        with _LOCK:
            t.on_post(time.time() if now is None else now, day, doc)
    except Exception:
        pass


def read(idx: str, now: float | None = None, ux_vols: dict | None = None) -> dict:
    """The state now. Never raises: a failure is a why."""
    try:
        t = tracker(idx)
        with _LOCK:
            return t.read(time.time() if now is None else now, ux_vols)
    except Exception as e:                       # never at a face's expense
        return {"idx": idx, "state": None, "why": f"could not check — feed health failed: {type(e).__name__}: {e}", "chip": "feed check nahi hua", "alarm": False, "sound": False, "tag": "M"}


def last_post(day: str):
    """The newest frame POST today on any index (epoch s), or None: the server's recording check (25 Oct review F13b)."""
    with _LOCK:
        return max((t.last_post for t in _T.values() if t.day == day and t.last_post is not None), default=None)


def reset() -> None:
    with _LOCK:
        _T.clear()
