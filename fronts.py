"""The near-ATM fronts, and whether a fade is legal against them.

THE OPERATOR'S RULE, stated 2026-09-22 in her own words:

    "hamesha read nearest ATM pe rehni chahiye. 23700 PE writers are irrelevant
     because wahan pe hedging ke liye positions banate hain, chhote seller to
     get the premium benefit to sell options. Poora 1.5L kaun dega per lot.
     Hamesha check karo the strike with most of OI and second best on BOTH
     sides, and always check WHICH SIDE STOPS FIRST increasing their positions
     and then unwinding."

Pre-registered as §1d of `context/research-findings.md` BEFORE this file
existed. Read that section before changing a threshold here; the parameters are
fixed and are not to be grid-searched (§5c's rule).

WHY THIS MODULE EXISTS AT ALL. `frame._trapped` answers a different question:
it takes `max(pain)` over every leg in the heat map, and on 2026-09-22 it
returned **PE 23700 at confidence "low"** -- a strike nobody carries margin on.
The front that actually broke that morning was **PE 23400, whose build peaked
at 10:19, one minute before a 105-point fall**, and which no surface named.

Pure computation, stdlib only, NO I/O -- the same isolation as
`chain_metrics.py` / `band_rotation.py`. Both callers hand it the SAME two
objects, so the rule exists once: `/api/oihist` (which does not depend on the
extension, so the read survives a dead GoCharting tab) and `frame.py` (which
already receives the same minute grid for `_trapped`).

INPUT is `ChainState.minutes` -- ``{"HH:MM": {"spot": float, "k": {strike:
(ce_chg, pe_chg)}}}``, where each value is OI CHANGE SINCE THE OPEN, not a
level -- and optionally `ChainState.peak`, ``{(strike, "ce"|"pe"): oi}``, the
session-high ABSOLUTE OI. Strike keys arrive as numbers in memory and as
strings over JSON; both are accepted.

RANKING IS BY PEAK OI, NOT CURRENT, and that is deliberate: a front that has
already given back 70% of its build is the one being hunted, and ranking by
current OI would drop it out of the top two exactly when it matters most.
Without `peak` the ranking falls back to each front's own peak CHANGE, which
is the same ordering question asked of the only number available, and says so
by leaving `oi` null.
"""

# §1d's parameters. Fixed, pre-registered, not to be tuned per index: every
# threshold below is a fraction of the front's OWN peak, so NIFTY and SENSEX
# read alike without a per-index table that would have to be maintained.
NEAR = 9                # strikes nearest spot that can matter today
TOP_PER_SIDE = 2        # "most OI and second best", her words
UNWIND_FRAC = 0.15      # off its own peak, with a falling slope -> UNWINDING
STALL_FRAC = 0.05       # slope inside +/-this of its own peak -> STALLED
SLOPE_MARKS = 15        # ~15 one-minute marks back for the slope

BUILDING, STALLED, UNWINDING = "BUILDING", "STALLED", "UNWINDING"

# Which side has to be adding for a fade of that band to have a defender.
# A BUY fade at d2/d3 is a bet the PUT writers hold; a SELL fade at u2/u3 is a
# bet the CALL writers hold.
DEFENDER = {"buy": "PE", "sell": "CE"}

# The engine's own veto, verbatim from `engine.Session.context`'s playbook.
# It carries no side -- negative gamma is a statement about the tape, not about
# one band -- so it vetoes a fade in either direction. See §1d.
VETO = "NO FADE"


def _num(x):
    """A strike key, from memory (number) or from JSON (string), or None."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _pair(v):
    """``(ce_chg, pe_chg)`` from a list or tuple, defaulting either to 0.0."""
    if not isinstance(v, (list, tuple)):
        return 0.0, 0.0
    ce = v[0] if len(v) > 0 and isinstance(v[0], (int, float)) else 0.0
    pe = v[1] if len(v) > 1 and isinstance(v[1], (int, float)) else 0.0
    return float(ce), float(pe)


def _at(row, k):
    """This strike's cell, whatever the key type the caller's grid used."""
    if not isinstance(row, dict):
        return None
    if k in row:
        return row[k]
    if float(k).is_integer() and int(k) in row:
        return row[int(k)]
    for key in (str(int(k)) if float(k).is_integer() else None, str(k)):
        if key is not None and key in row:
            return row[key]
    return None


def _state(chg, peak, slope):
    """build -> stall -> unwind, each judged against the front's OWN peak."""
    scale = max(abs(peak), 1.0)
    if peak - chg >= UNWIND_FRAC * scale and slope < 0:
        return UNWINDING
    if abs(slope) <= STALL_FRAC * scale:
        return STALLED
    return BUILDING if slope > 0 else UNWINDING


def read(minutes, peak=None):
    """The near-ATM fronts, top `TOP_PER_SIDE` per side, CE rows then PE rows.

    An empty list means the grid could not be read -- never an assertion that
    there are no fronts. The caller turns that into its own PATA NAHI.
    """
    if not isinstance(minutes, dict) or not minutes:
        return []
    times = sorted(t for t in minutes if isinstance(t, str))
    if not times:
        return []
    last = minutes[times[-1]] or {}
    spot = last.get("spot")
    grid = last.get("k") or {}
    if spot is None or not grid:
        return []

    strikes = sorted((k for k in (_num(s) for s in grid) if k is not None),
                     key=lambda k: abs(k - spot))[:NEAR]
    if not strikes:
        return []

    def series(k, i):
        """This strike's side-`i` change at every mark, oldest first.

        A mark that never carried this strike reads 0.0: the grid is written
        whole per minute, so an absent strike is one that had no position --
        a real zero, not a hole.
        """
        return [_pair(_at((minutes[t] or {}).get("k"), k))[i] for t in times]

    def oi_of(side, k):
        if not isinstance(peak, dict):
            return None
        for key in ((k, side.lower()), (int(k), side.lower()),
                    (str(k), side.lower())):
            try:
                if key in peak:
                    return peak[key]
            except TypeError:          # an unhashable key can only be absent
                continue
        return None

    def build(side, k):
        vals = series(k, 0 if side == "CE" else 1)
        pk = max(vals)
        chg = vals[-1]
        back = vals[max(0, len(vals) - 1 - SLOPE_MARKS)]
        slope = chg - back
        return {"k": k, "side": side, "oi": oi_of(side, k),
                "chg": chg, "peak": pk, "peak_at": times[vals.index(pk)],
                "from_peak": chg - pk, "slope": slope,
                "state": _state(chg, pk, slope), "tag": "M"}

    out = []
    for side in ("CE", "PE"):
        rows = [build(side, k) for k in strikes]
        # "most OI and second best" -- by session-peak absolute OI where the
        # chain gave it, else by the front's own peak build.
        rows.sort(key=lambda r: -(r["oi"] if r["oi"] is not None else r["peak"]))
        out.extend(rows[:TOP_PER_SIDE])
    return out


def side_front(fronts, side):
    """The top front on `side` ("CE"/"PE"), or None."""
    for f in fronts or ():
        if f.get("side") == side:
            return f
    return None


def broke(fronts):
    """The front that stopped adding FIRST and is giving inventory back.

    Both sides unwinding is normal late in a leg; the one that peaked EARLIER
    started it, and that is the one the operator's rule points at.
    """
    cands = [f for f in (fronts or ()) if f.get("state") != BUILDING]
    if not cands:
        return None
    unwinding = [f for f in cands if f.get("state") == UNWINDING]
    return sorted(unwinding or cands, key=lambda f: f.get("peak_at") or "")[0]


STALE_MIN = 3   # an OI grid whose newest minute is this far behind the bar is not a read


def _mins(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def stale(minutes, as_of):
    """Why the grid cannot speak for `as_of` ("HH:MM"), or None when it can.

    `read` uses the grid's newest minute however old it is. On a chain feed
    that dies at 10:40 with the CE front unwinding, every SELL fade would read
    ILLEGAL for the rest of the session -- a dead socket muting the operator
    with a confident "no". A grid more than STALE_MIN behind the bar is a
    missing input, and a missing input is PATA NAHI (§1d), never a verdict.
    """
    times = sorted(t for t in (minutes or {}) if isinstance(t, str))
    if not times or not as_of:
        return None
    if _mins(as_of) - _mins(times[-1]) > STALE_MIN:
        return f"chain grid stale since {times[-1]}"
    return None


def bar_last_minute(t, interval=3):
    """The last one-minute mark INSIDE the bar labelled `t` (its opening minute).

    Every reader of a bar's gate reads it here -- trigger_log's stamp, the
    frame's tap and trigger -- so the three surfaces agree. On 2026-09-23 the
    NIFTY PE gate flickered minute to minute 09:50-10:05, and reading one bar at
    its open, its close and five minutes later gave three different answers.
    `interval` is the zone machine's bar (band_rotation.SCORED_INTERVAL = 3).
    """
    end = _mins(t) + int(interval) - 1
    return f"{end // 60:02d}:{end % 60:02d}"


def cut(minutes, as_of):
    """The grid as it stood at `as_of`: marks at or before that minute only."""
    return {k: v for k, v in (minutes or {}).items() if isinstance(k, str) and k <= as_of}


def fade_gate(fronts, side, plays=None, stale_why=None):
    """Is a fade of `side` ("buy"/"sell") legal right now? §1d.

    LEGAL only when the defending front is still BUILDING and the engine has
    not printed its NO FADE veto. A missing input is PATA NAHI (`legal: None`),
    never legal -- "we could not check" must not render as "we checked and
    found nothing". Both conditions are inputs: `plays=None` means the engine's
    playbook was NOT READ, so a building defender without it is PATA NAHI, not
    legal. `plays=[]` is the engine read and printing nothing -- no veto.
    `stale_why` (from `stale`) makes the whole read PATA NAHI.

    NOTHING IS SUPPRESSED BY THIS. §1d is explicit: the forward log keeps every
    row it would have written, and this rides alongside as a field, so the
    question "what would obeying it have cost and saved" stays answerable from
    rows logged FORWARD rather than from a re-cut cache.
    """
    want = DEFENDER.get(side)
    veto = None
    if plays is not None:
        veto = any(isinstance(p, str) and p.startswith(VETO) for p in plays)
    out = {"legal": None, "why": None, "side": side, "defender": want,
           "front": None, "veto": veto, "tag": "I"}
    if want is None:
        out["why"] = f"{side!r} is not a fade side"
        return out
    if stale_why:
        out["why"] = stale_why
        return out
    if not fronts:
        out["why"] = "near-ATM fronts not read"
        return out
    front = side_front(fronts, want)
    if front is None:
        out["why"] = f"no {want} front among the {NEAR} strikes nearest spot"
        return out
    out["front"] = front
    if veto:
        out["legal"] = False
        out["why"] = "engine says NO FADE -- negative gamma, continuation only"
        return out
    if front["state"] == BUILDING:
        if veto is None:
            # The defender holds, but the engine's veto was never read: one of
            # §1d's two conditions is a hole, so this is PATA NAHI, not legal.
            out["why"] = f"{want} {front['k']:.0f} building, NO FADE check not read"
            return out
        out["legal"] = True
        # A front that ran and then came back reads BUILDING again -- the state
        # is the CURRENT direction, by design (§1d). But "still building" would
        # be a lie about a front sitting far under its own peak: on 2026-09-22
        # at 11:12, PE 23400 was adding again while still 172.5L below its
        # 10:19 high. Legal, and the reader is told what they are leaning on.
        under = -front["from_peak"]
        if under >= UNWIND_FRAC * max(abs(front["peak"]), 1.0):
            out["why"] = (f"{want} {front['k']:.0f} adding again, still "
                          f"{under / 1e5:.1f}L under its {front['peak_at']} peak")
        else:
            out["why"] = f"{want} {front['k']:.0f} still building"
        return out
    out["legal"] = False
    word = "gave up its build" if front["state"] == UNWINDING else "stopped building"
    out["why"] = f"{want} {front['k']:.0f} {word} at {front['peak_at']}"
    return out
