"""levels.py -- war-map object A: the reaction-point map.

WHAT IT ANSWERS. Not "where is price" but "where are the places RETAIL
REACTS" -- because the operator's thesis (stated 2026-08-22, the seed of the
whole war map) is that smart money walks price TO those places, lets
positions load there, and runs the stops beyond them. Every other module in
the war map anchors to this one: a dwell is a dwell AT a level, a runway runs
TO a level. Until this file existed, no module in the stack knew what PDH
was.

THE LEVEL KINDS, AND WHERE EACH COMES FROM:

    PDH / PDL / PDC   prior session's high/low/close   [M] daily candles
    PWH / PWL         prior WEEK's high/low            [M] daily candles
    OPEN              today's opening print            [M] intraday candles
    ROUND             round numbers near spot          [M] arithmetic
    MAX_PAIN          strike minimizing payout         [M] computed from OI
    GAMMA_FLIP        dealer GEX sign change           [I] hedging inference
    CE_WALL / PE_WALL heaviest OI strike per side      [M] the chain

THE FRAME IS STATED ON EVERY LEVEL, because the frame discipline is law in
this stack: PDH/PDL/OPEN are INDEX prices (retail watches the index chart),
while chain-derived levels live in STRIKE space (which prices off the
future). The two differ by the basis, and a level compared against the wrong
frame is wrong by exactly that much. `frame` is "index" or "chain"; the
caller compares like with like or says it did not.

STABLE vs DRIFTING. PDH does not move during a session; max pain and the
walls do. `stable: True` marks the levels a sequence machine may anchor to --
a state machine keyed to a level that drifts under it would count phantom
approaches (sequence.py refuses unstable levels for exactly this reason).

THE ONE I/O FUNCTION. `fetch_daily` is the single function here that touches
the network (same division as senses.py being its group's one disk-toucher).
It costs three REST calls per index per day -- daily candles for PWH/PWL,
the prior session's 1-minute for PDH/PDL/PDC (before the closing auction),
intraday 1-minute for the opening print -- and is called from a
background thread the orchestrator owns, never from the senses loop or a
request handler. Everything else in this file is pure computation.

NO KILL CONDITION -- a level map states facts, not claims (the plan says so
explicitly). The modules that CLAIM things about these levels (dwell,
sequence) carry their own.

Pure computation + one declared I/O function. Stdlib only otherwise.
"""

from __future__ import annotations

from typing import List, Optional

# Round-number steps per index, (minor, major) -- the [I] layer, from the
# operator's own plan ("NIFTY 50/100, BANKNIFTY 100/500, SENSEX equivalents").
# A price on the major grid is emitted once, as major.
ROUND_STEPS = {"NIFTY": (50, 100), "BANKNIFTY": (100, 500),
               "SENSEX": (100, 500)}
# Rounds only within this fraction of spot either side -- beyond it a round
# number is not "near" and would bury the map in gridlines. [I]
ROUND_WINDOW = 0.008
# The last continuously traded minute of the cash session: the closing auction (CAS, 2026-08-03) begins after it.
LAST_CONTINUOUS = "15:15"


def round_levels(idx: str, spot: Optional[float]) -> List[dict]:
    """Round numbers near spot, minor and major, each emitted once."""
    if not spot:
        return []
    minor, major = ROUND_STEPS.get(idx, (100, 500))
    lo, hi = spot * (1 - ROUND_WINDOW), spot * (1 + ROUND_WINDOW)
    out = []
    k = int(lo // minor) * minor
    while k <= hi:
        if k >= lo:
            is_major = k % major == 0
            out.append({"kind": "ROUND", "px": float(k), "frame": "index",
                        "tag": "M", "stable": True, "major": is_major,
                        "label": f"round {k:,}"})
        k += minor
    return out


def static_levels(daily: Optional[dict]) -> List[dict]:
    """PDH/PDL/PDC/PWH/PWL/OPEN from a `fetch_daily` result. Empty when the
    fetch has not landed -- the caller carries the why."""
    if not daily:
        return []
    out = []
    pd_ = daily.get("pd") or {}
    for kind, key in (("PDH", "h"), ("PDL", "l"), ("PDC", "c")):
        if pd_.get(key) is not None:
            auc = (f" · auction close {pd_['auction_c']:,.1f}" if kind == "PDC" and pd_.get("auction_c") is not None
                   else f" · {pd_['c_why']}" if kind == "PDC" and pd_.get("c_why") else "")
            out.append({"kind": kind, "px": float(pd_[key]), "frame": "index",
                        "tag": "M", "stable": True,
                        "label": f"{kind} {pd_[key]:,.1f} spot ({pd_.get('date', '?')}{auc})"})
    pw = daily.get("pw") or {}
    for kind, key in (("PWH", "h"), ("PWL", "l")):
        if pw.get(key) is not None:
            out.append({"kind": kind, "px": float(pw[key]), "frame": "index",
                        "tag": "M", "stable": True,
                        "label": f"{kind} {pw[key]:,.1f} (week of {pw.get('start', '?')})"})
    op = daily.get("open") or {}
    if op.get("px") is not None:
        out.append({"kind": "OPEN", "px": float(op["px"]), "frame": "index",
                    "tag": op.get("tag", "M"), "stable": True,
                    "label": f"day open {op['px']:,.1f}"})
    return out


def chain_levels(metrics: Optional[dict],
                 strikes: Optional[List[dict]]) -> List[dict]:
    """Max pain, gamma flip and the heaviest-OI wall per side, off the chain.

    These DRIFT during a session (stable: False): a sequence machine must not
    anchor to them, but the map draws them -- they are where the dealer's own
    physics says pin and cascade live.
    """
    out = []
    m = metrics or {}
    if m.get("max_pain") is not None:
        out.append({"kind": "MAX_PAIN", "px": float(m["max_pain"]),
                    "frame": "chain", "tag": "M", "stable": False,
                    "label": f"max pain {m['max_pain']:,.0f}"})
    if m.get("flip_px") is not None:
        out.append({"kind": "GAMMA_FLIP", "px": float(m["flip_px"]),
                    "frame": "chain", "tag": "I", "stable": False,
                    "label": f"gamma flip {m['flip_px']:,.0f} [I]"})
    best = {"ce": (None, 0.0), "pe": (None, 0.0)}
    for s in strikes or []:
        for side in ("ce", "pe"):
            oi = (s.get(side) or {}).get("oi") or 0
            if oi > best[side][1]:
                best[side] = (s.get("k"), oi)
    for side, kind in (("ce", "CE_WALL"), ("pe", "PE_WALL")):
        k, oi = best[side]
        if k is not None and oi > 0:
            out.append({"kind": kind, "px": float(k), "frame": "chain",
                        "tag": "M", "stable": False,
                        "label": f"{kind.replace('_', ' ').lower()} {k:,.0f} "
                                 f"({oi / 1e6:.1f}M OI)"})
    return out


class Levels:
    """The level book for one index. Holds the daily fetch result (or the
    reason it is absent) and assembles the full map per read -- stateless
    beyond that, so a read can never serve a stale chain level."""

    def __init__(self, idx: str):
        self.idx = idx
        self.daily: Optional[dict] = None
        self.daily_why: Optional[str] = "daily candles not fetched yet"

    def set_daily(self, daily: dict):
        self.daily, self.daily_why = daily, None

    def set_daily_error(self, why: str):
        # keep any earlier successful fetch; only the why updates
        self.daily_why = why

    def read(self, spot: Optional[float], metrics: Optional[dict],
             strikes: Optional[List[dict]]) -> dict:
        lv = (static_levels(self.daily) + round_levels(self.idx, spot)
              + chain_levels(metrics, strikes))
        lv.sort(key=lambda l: -l["px"])
        return {"levels": lv, "daily_why": self.daily_why,
                "n_static": len(static_levels(self.daily))}


# --- the one I/O function ---------------------------------------------------

def fetch_daily(idx: str, tok: Optional[str] = None) -> dict:
    """Prior-day OHLC, prior-week H/L and today's open for one index. [M]

    Three REST calls: ~10 daily candles in one range request, the prior
    session's 1-minute candles (its H/L/C before the closing auction), plus
    today's 1-minute candles for the opening print. Raises on transport/auth failure
    -- the caller (warmap's fetch thread) owns retry and the stated absence.
    """
    from datetime import datetime, timedelta

    import upstox_feed
    import upstox_instruments
    import upstox_rest

    tok = tok or upstox_feed.read_token()
    key = upstox_instruments.index_key(idx)
    today = datetime.now().strftime("%Y-%m-%d")
    frm = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    daily = upstox_rest.daily_range(key, tok, frm, today)   # newest first
    # candle: [ts, o, h, l, c, v, oi]; completed sessions only, today excluded
    days = [c for c in daily if str(c[0])[:10] < today]
    out: dict = {"day": today, "pd": None, "pw": None, "open": None}
    if days:
        c = days[0]
        out["pd"] = {"date": str(c[0])[:10], "h": c[2], "l": c[3], "c": c[4]}
        # THE CLOSING AUCTION (NSE/BSE CAS, since 2026-08-03): continuous trading stops at 15:15, the index
        # freezes there, and the official close -- the daily candle's c, and its h/l when the auction prints past
        # the range -- lands on the 15:29 bar (21 Oct NIFTY: 22,738.45 at 15:15, auction 22,811.35, futures 22,745.3
        # at 15:29). The futures and options trade on against the 15:15 level, so the prior session's H/L/C here
        # are its continuous bars'; the auction close rides along, named.
        try:
            cont = [b for b in upstox_rest.historical(key, tok, out["pd"]["date"])
                    if str(b[0])[11:16] <= LAST_CONTINUOUS]           # newest first
        except Exception:                                             # noqa: BLE001 -- the candle still stands
            cont = []
        if cont:
            out["pd"].update(h=max(b[2] for b in cont), l=min(b[3] for b in cont), c=cont[0][4], auction_c=c[4])
        else:
            out["pd"]["c_why"] = "auction close: the 1-min bars did not land"
        # prior ISO week, relative to today's week
        this_week = datetime.now().isocalendar()[:2]
        wk = {}
        for cd in days:
            d = datetime.strptime(str(cd[0])[:10], "%Y-%m-%d")
            wk.setdefault(d.isocalendar()[:2], []).append(cd)
        prev_weeks = sorted(k for k in wk if k < this_week)
        if prev_weeks:
            cs = wk[prev_weeks[-1]]
            out["pw"] = {"h": max(c[2] for c in cs),
                        "l": min(c[3] for c in cs),
                        "start": min(str(c[0])[:10] for c in cs)}
    ones = upstox_rest.intraday(key, tok)                   # newest first
    if ones:
        out["open"] = {"px": ones[-1][1], "tag": "M"}       # oldest bar's open
    return out
