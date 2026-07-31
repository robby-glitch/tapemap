"""The operator's own setup: an option premium at a band extreme, reversing.

Spec `docs/superpowers/specs/2026-07-31-operator-band-rotation-setup.md`.
This is the first analytic in the tool that encodes the OPERATOR's edge rather
than someone else's read, so the quotes below are theirs and the code is meant
to be checkable against them line by line.

Pure computation, stdlib only, NO I/O -- the same isolation as
`chain_metrics.py` / `structure.py` / `contract_bars.py`, and never imported by
`engine.py`. Wiring it into `/api/contract` is a separate task.

    legs (one shared axis)  ->  trigger  ->  confirm  ->  trap  ->  records
                                (this leg) (other leg  (this leg's
                                            + both OI)  own bands)

INPUT is exactly what `live.build_contract` returns: `legs["CE"]` and
`legs["PE"]`, each ``{"bars": [...], "vwap": [...], "oi": [...],
"bar_days": [...]}``, every array indexed by the ONE shared axis
(`live._align_to_axis`), so `CE.bars[i]` and `PE.bars[i]` are the same minute
of the same session or an explicit `None` where that leg did not print. Bars
carry `contract_bars.BAR_KEYS` (`t,o,h,l,c,v,oi`), bands `BAND_KEYS`
(`vwap,u1,d1,u2,d2,u3,d3`) -- the option's OWN premium VWAP, not the index's.
A whole `/api/contract` payload is accepted too and unwrapped.

OUTPUT is one slot per axis index, `None` where nothing fired, so a consumer
can zip it straight onto the bars.

WHAT THE OPERATOR SAID, AND WHAT THIS DOES WITH IT

  * *"tag or wick is enough but has to reverse from the last band"* -- the
    touch is not the signal, the reversal is. A tag alone never fires.
  * BUY at -2 sigma OR -3 sigma; SELL only at +3 sigma. That asymmetry is
    theirs and is deliberately NOT symmetrised: *"a stretched premium can
    stretch further"*.
  * *"while making sure the other side is also coming down from the +3 +2
    upper line"* -- the pair must be ROTATING, one leg washed out while the
    other unwinds from stretched. Both legs merely decaying together is theta
    on a dead day, not a setup.
  * *"the rate of change of oi is declining now"* -- OI DECELERATION, not an
    OI peak. OI lags, so a peak is only knowable afterwards; the decay in the
    rate of building front-runs it. Second derivative, both books.
  * *"suppose book is put heavy but put prices are touching the last band so
    we can except a bounce from there"* -- positioning does NOT veto. There is
    no filter anywhere in this module that suppresses a signal because the
    book is heavy on the side being bought; adding one would delete the edge.
  * *"smart money always make possition is narrow ... than the market start
    moving"* -- the trap filter reads what PRICE was doing BEFORE the move,
    not the move itself: how narrow its range was, how long it held it, and
    whether that range was narrowing or expanding into the break.

INTERPRETATIONS -- places where the operator was not literal and this module
had to choose. Every one of these is worth putting back to them.

  1. SAME-BAR REVERSAL. *"has to reverse from the last band"* does not say
     when. This module requires the reversal ON THE TAGGING BAR: the bar's low
     pierces d2/d3 and that same bar's close is back above it. The alternative
     reading -- the reversal confirmed by the FOLLOWING bar -- is not
     implementable without lookahead, and causality here is absolute (bar `i`
     reads bars <= `i` only, so replay is truncation). Reading it the other
     way would change what fires and when, so CONFIRM THIS WITH THE OPERATOR.
     If they mean next-bar confirmation, the signal must be stamped on the
     later bar, never backdated onto the tag.
  2. THE ROTATION WINDOW. "coming down from" has no operator number.
     `ROTATION_WINDOW` bars is an assumption; see its comment.
  3. THE SELL-SIDE CONFIRMATION IS A MIRROR. The operator described the other
     leg "coming down from +2/+3" for the BUY case only and said nothing about
     what confirms a SELL. Applying the buy rule unchanged would leave every
     sell unconfirmed (when one leg is stretched the other is at its floor, by
     construction -- the legs mirror, which is why the pair is picked at the
     money). So for a SELL the other leg must be coming UP from its -2/-3
     sigma. That is a derivation from "they almost forms mirror charts", not
     something they said.
  4. THE OI SECOND DERIVATIVE is measured as two consecutive window slopes,
     recent versus prior, both on THESE strikes' own `oi` series. The engine's
     `oi_slope` is a different series (the index books) and is not read here.
  5. THREE-VALUED CONFIRMATION. Confirmation is a conjunction of two facts,
     either of which can be unreadable, so it is combined in Kleene logic: one
     definite failure gives UNCONFIRMED even if the other half is unknown; an
     unknown with nothing failing gives UNKNOWN. UNKNOWN is never rounded to
     either side.
  6. ONE RECORD PER BAR. Both legs can satisfy the trigger on the same bar
     (both at their floors = theta, not rotation). The stronger sigma wins,
     CE before PE on a tie. A per-leg record was not asked for and would let a
     consumer double-count one minute. The hit that LOST the tie-break is not
     thrown away silently -- it is named in `also` and in the trigger receipt,
     because a consumer reading "CE fired" has no other way to learn that the
     PE qualified on the same minute, which is the cleanest form of the
     operator's rotation.
  7. COMPRESSION IS MEASURED ON PRICE. See `_trap` -- the operator's own
     refinement of 2026-07-31, and the reason this module's first version
     did not work.

NO ABSOLUTE MARKET THRESHOLDS. The sigma bands are the operator's own relative
thresholds and are used as given. Everything this module adds on top is rank
or sign based -- the price range is normalised by the leg's own VWAP and
RANKED against a trailing window, dwell and the two OI reads are counts and
SIGNS, never a rupee level or a lot count. The one clock time in the module is
the operator's own 09:25 anchor, which is a session landmark rather than a
market level. The same shaped series at NIFTY, BANKNIFTY or SENSEX premium
magnitudes therefore yields identical signals; `test_band_rotation.py` locks
that down, because an absolute number here would silently work on one index
and misfire on another.

CAUSALITY. Every window looks BACKWARD and stops at the session boundary
(`bar_days`), so a multi-session axis cannot let yesterday's compression rank
today's bar or yesterday's tag confirm today's trigger. Replaying a truncated
series reproduces the earlier records field for field.
"""

import math

# --- The trigger ---------------------------------------------------------
# The operator's own bands and their asymmetry. Buying is the -2 OR -3 sigma
# extreme; selling is +3 only. Ordered strongest first: a bar that pierces d3
# is reported as d3 even though it necessarily pierced d2 as well.
BUY_BANDS = ("d3", "d2")
SELL_BANDS = ("u3",)

_SIGMA = {"d3": 3, "u3": 3, "d2": 2, "u2": 2}
_LEGS = ("CE", "PE")

# --- The confirmation ----------------------------------------------------
# How far back the other leg's rotation still counts. NO OPERATOR VALUE
# EXISTS; this is an assumption. 10 bars is ~30 minutes at the default 3-min
# contract interval -- long enough that the pair's rotation is not required to
# be simultaneous to the bar (it never is: one leg turns first), short enough
# that a tag from an hour ago cannot dress up an unrelated move. It is a count
# of BARS, so a chart on a different interval spans a different wall time;
# that is deliberate (the operator reads bars, not minutes), and it means the
# window should be revisited if the default interval changes.
ROTATION_WINDOW = 10

# The OI slope window, in bars. Two consecutive windows are compared, so a
# read needs 2*OI_WINDOW+1 samples in the session -- 11 bars, ~33 minutes at
# the default interval, i.e. no OI read before roughly 09:48. Shorter windows
# made the second difference read the tick noise of a ~10.5s poller resampled
# into bars; longer ones cannot see a deceleration begin inside a session.
OI_WINDOW = 5

# --- The trap filter -----------------------------------------------------
# How many bars of PRICE make up one range reading: the high/low of the last
# RANGE_WINDOW bars, i.e. the box price is currently working inside. The
# trigger bar is never part of the reading a verdict is based on -- its own
# expansion is the move, not the run-up.
RANGE_WINDOW = 5

# How many recent range readings the pre-move reading is ranked against. This
# is THE fix for the first version's first defect: ranking against the session
# so far measured how late in the day it was, because sigma accumulates from
# the 09:15 anchor and band width therefore grows monotonically (median
# `(u1-d1)/vwap` 0.117 -> 0.388 across session deciles, measured over 73 cached
# sessions). A trailing window asks the operator's actual question -- "is this
# narrow compared to how price has been moving lately" -- and carries no
# session-clock bias. 30 readings is ~90 minutes at the default 3-minute
# interval: long enough to be a population, short enough not to reach back to
# the open.
TRAIL_WINDOW = 30

# Below this many readings there is nothing to rank against and the answer is
# UNKNOWN, never CLEAR. 10 is the smallest population where a 0.30 rank
# threshold can be distinguished at all (3 readings below it).
TRAIL_MIN = 10

# Over how many readings the DIRECTION of change is judged -- *"expanding or
# narrowing"*, *"not narrowing or staying flat"*. The two halves' means are
# compared, so this must be even, at least 4 to have two samples a side, and
# no larger than TRAIL_MIN -- a verdict that ranks the range must always be
# able to say which way it was going.
TREND_WINDOW = 6

# A pre-move range in the bottom 30% of the trailing readings is
# "compression". Carried over unchanged from the COILING state the rest of the
# tool already uses (`bw_r < 0.3`, see the Tape Chart spec) so the same word
# means the same thing in two places, and deliberately NOT retuned against the
# output of this module. It is a RANK, not a range, so it carries across
# indices and across a quiet day versus a violent one.
COMPRESSION_RANK = 0.30

# *"by 9:25 we have the values for vwap standard deviation and from there we
# judge wheather they are expanding or narrowing."* Before this clock time the
# verdict is UNKNOWN whatever the arithmetic says. It is read off the BAR'S
# OWN `t` label rather than counted in bars, so it lands at 09:25 on a 1-, 3-
# or 15-minute chart alike and cannot drift with the interval or with a
# session whose feed dropped its first minutes. A bar with no readable clock
# label is UNKNOWN, not assumed to be late enough.
ANCHOR_HHMM = "09:25"
ANCHOR_MINUTE = 9 * 60 + 25


def _num(x):
    """A finite float, or None. Bools are not numbers here."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    f = float(x)
    return f if math.isfinite(f) else None


def _f(x):
    return "?" if x is None else f"{x:.2f}"


def _view(leg):
    """One leg's arrays, normalised. A missing leg is empty, never invented."""
    leg = leg if isinstance(leg, dict) else {}
    return {"bars": list(leg.get("bars") or []),
            "vwap": list(leg.get("vwap") or []),
            "oi": list(leg.get("oi") or []),
            "days": list(leg.get("bar_days") or [])}


def _at(seq, i):
    return seq[i] if 0 <= i < len(seq) else None


def _bar(view, i):
    b = _at(view["bars"], i)
    return b if isinstance(b, dict) else None


def _band(view, i):
    v = _at(view["vwap"], i)
    return v if isinstance(v, dict) else None


def _oi_at(view, i):
    """This strike's OI at bar `i`, from the parallel array or the bar."""
    v = _num(_at(view["oi"], i))
    if v is None:
        b = _bar(view, i)
        v = _num(b.get("oi")) if b else None
    return v


def _trigger(bar, band):
    """A tag AND a same-bar reversal, or None. Interpretation 1.

    BUY  -- the low pierced d3 (preferred) or d2 and the CLOSE is back above
            the band it pierced.
    SELL -- the high pierced u3 and the close is back below it. There is no
            u2 sell: that asymmetry is the operator's.
    """
    low, high, close = (_num(bar.get(k)) for k in ("l", "h", "c"))
    if low is None or high is None or close is None:
        return None
    for name in BUY_BANDS:
        lvl = _num(band.get(name))
        if lvl is not None and low <= lvl and close > lvl:
            return {"side": "BUY", "band": name, "level": lvl,
                    "extreme": low, "close": close}
    for name in SELL_BANDS:
        lvl = _num(band.get(name))
        if lvl is not None and high >= lvl and close < lvl:
            return {"side": "SELL", "band": name, "level": lvl,
                    "extreme": high, "close": close}
    return None


def _trigger_why(leg, hit):
    word = "low" if hit["side"] == "BUY" else "high"
    rel = "<=" if hit["side"] == "BUY" else ">="
    back = "above" if hit["side"] == "BUY" else "below"
    return (f"{leg} {word} {_f(hit['extreme'])} {rel} {hit['band']} "
            f"{_f(hit['level'])} and the same bar closed {_f(hit['close'])} "
            f"back {back} it")


def _rotating(other, name, i, days, side):
    """Is the OTHER leg coming off its opposite extreme? (True/False/None).

    BUY  -- it tagged u3 (preferred) or u2 within `ROTATION_WINDOW` bars of
            this session and its close is now back below that band.
    SELL -- the mirror, off d3/d2. Interpretation 3.

    None means unreadable, not absent: if no tag is found but bars inside the
    window are missing, the honest answer is "cannot tell", not "it did not
    happen". A window merely cut short by the session's start is not a hole --
    that is all the history there is, and the tag really is not in it.
    """
    bar_i, band_i = _bar(other, i), _band(other, i)
    close_i = _num(bar_i.get("c")) if bar_i else None
    if bar_i is None or band_i is None or close_i is None:
        return None, (f"{name} did not print a readable bar here, so whether "
                      f"it is rotating cannot be read")

    tags = ("u3", "u2") if side == "BUY" else ("d3", "d2")
    stretched = "h" if side == "BUY" else "l"
    holes = 0
    for j in range(i, max(-1, i - ROTATION_WINDOW), -1):
        if _at(days, j) != _at(days, i):
            break                                # session boundary, not a hole
        bj, vj = _bar(other, j), _band(other, j)
        ext = _num(bj.get(stretched)) if bj else None
        if bj is None or vj is None or ext is None:
            holes += 1
            continue
        for tag in tags:
            lvl = _num(vj.get(tag))
            if lvl is None:
                continue
            if (ext >= lvl) if side == "BUY" else (ext <= lvl):
                now = _num(band_i.get(tag))
                if now is None:
                    return None, (f"{name} tagged {tag} {_f(lvl)} {i - j} bars "
                                  f"back but has no {tag} here to compare")
                off = (close_i < now) if side == "BUY" else (close_i > now)
                where = "below" if side == "BUY" else "above"
                still = "above" if side == "BUY" else "below"
                if off:
                    return True, (f"{name} tagged {tag} {_f(lvl)} {i - j} bars "
                                  f"back and now closes {_f(close_i)} {where} "
                                  f"its {tag} {_f(now)}")
                return False, (f"{name} tagged {tag} {_f(lvl)} {i - j} bars "
                               f"back but still closes {_f(close_i)} {still} "
                               f"its {tag} {_f(now)} -- not rotating yet")
    if holes:
        return None, (f"{name} did not tag its "
                      f"{'+' if side == 'BUY' else '-'}2/3 sigma in the last "
                      f"{ROTATION_WINDOW} bars, but {holes} bar(s) in that "
                      f"window are missing, so the tag cannot be ruled out")
    return False, (f"{name} did not tag its "
                   f"{'+' if side == 'BUY' else '-'}2/3 sigma in the last "
                   f"{ROTATION_WINDOW} bars, so the pair is not rotating")


def _oi_slopes(view, i, days):
    """(prior, recent) OI slope per bar over two adjacent windows, or None.

    Session-local and causal. Slopes are divided by the BAR DISTANCE between
    the samples used, so a minute the feed never delivered stretches the
    window rather than inflating the rate. Sign only ever gets compared --
    the absolute lot count is never a threshold anywhere in this module.
    """
    pts = []
    for j in range(i + 1):
        if _at(days, j) != _at(days, i):
            continue
        v = _oi_at(view, j)
        if v is not None:
            pts.append((j, v))
    need = 2 * OI_WINDOW + 1
    if len(pts) < need:
        return None
    a, b, c = pts[-need], pts[-need + OI_WINDOW], pts[-1]
    return ((b[1] - a[1]) / (b[0] - a[0]), (c[1] - b[1]) / (c[0] - b[0]))


def _decelerating(views, i, days):
    """Is OI building more slowly on BOTH books? (True/False/None).

    *"oi is lagging so we need to prempt by the change ... the rate of change
    of oi is declining now"*. Not a peak: the slope of the slope.
    """
    read = {}
    for name in _LEGS:
        view = views.get(name)
        read[name] = _oi_slopes(view, i, days) if view else None
    missing = [n for n in _LEGS if read[n] is None]
    if missing:
        return None, (f"OI rate of change needs {2 * OI_WINDOW + 1} bars of "
                      f"this session on both legs; {' and '.join(missing)} "
                      f"has too few")
    hot = [n for n in _LEGS if read[n][1] >= read[n][0]]
    parts = ", ".join(f"{n} {_f(read[n][0])}/bar -> {_f(read[n][1])}/bar"
                      for n in _LEGS)
    if hot:
        return False, (f"OI rate is not decelerating on "
                       f"{' and '.join(hot)} ({parts})")
    return True, f"OI rate decelerating on both legs ({parts})"


def _confirm(views, own, i, days, side):
    """Kleene AND of the rotation and the OI read. Interpretation 5."""
    other = "PE" if own == "CE" else "CE"
    view = views.get(other)
    if view is None:
        return "UNKNOWN", (f"the {other} leg was not supplied, so the pair's "
                           f"rotation cannot be read")
    rot, rot_why = _rotating(view, other, i, days, side)
    oi, oi_why = _decelerating(views, i, days)
    why = f"{rot_why}; {oi_why}"
    if rot is False or oi is False:
        return "UNCONFIRMED", why
    if rot is None or oi is None:
        return "UNKNOWN", why
    return "CONFIRMED", why


def _minute(t):
    """A "HH:MM" bar label -> minutes since midnight, or None."""
    if not isinstance(t, str):
        return None
    parts = t.split(":")
    if len(parts) < 2:
        return None
    try:
        hh, mm = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    return hh * 60 + mm if 0 <= hh < 24 and 0 <= mm < 60 else None


def _price_points(view, i, days):
    """[(j, high, low, vwap)] for this session's readable bars up to `i`.

    Bars the feed never delivered are absent rather than interpolated, so a
    window is a window of bars that EXIST -- the same rule `_oi_slopes` uses.
    """
    out = []
    for j in range(i + 1):
        if _at(days, j) != _at(days, i):
            continue
        b, v = _bar(view, j), _band(view, j)
        if b is None or v is None:
            continue
        h, l, vw = _num(b.get("h")), _num(b.get("l")), _num(v.get("vwap"))
        if h is None or l is None or vw is None or vw <= 0:
            continue
        out.append((j, h, l, vw))
    return out


def _ranges(pts):
    """Rolling price range over RANGE_WINDOW bars, over vwap.

    `out[m]` is the range of `pts[m : m + RANGE_WINDOW]`; the last entry is
    therefore the box price is working inside right now.

    Normalised by the leg's OWN vwap, which is what makes a 40-rupee premium
    and a 900-rupee one comparable at all -- and, deliberately, NOT by the
    band width. Band width is the envelope, and dividing by it would fold
    sigma's monotone session accumulation straight back into the measure this
    module exists to keep clean; the operator's own annotated chart is a WIDE
    +/-1 sigma region with price grinding in a thin strip inside it, so the
    envelope and the strip have to be allowed to disagree.
    """
    out = []
    for k in range(RANGE_WINDOW - 1, len(pts)):
        win = pts[k - RANGE_WINDOW + 1:k + 1]
        hi, lo = max(p[1] for p in win), min(p[2] for p in win)
        out.append((hi - lo) / pts[k][3])
    return out


def _rank(pre, m):
    """Rank of reading `m` among the TRAIL_WINDOW readings ending at it.

    `(rank, population size)`, or `(None, size)` when the population is too
    small to rank against at all. `<=` counts ties, so an unchanging series
    ranks 1.00 -- "price is using exactly as much room as it always has",
    which is not compression and must not read as it.
    """
    trail = pre[max(0, m - TRAIL_WINDOW + 1):m + 1]
    if len(trail) < TRAIL_MIN:
        return None, len(trail)
    return sum(1 for r in trail if r <= pre[m]) / len(trail), len(trail)


def _dwell(pre):
    """For how many consecutive BARS the range has stayed compressed.

    *"is its a good thing to notice or keep in mind for how long the price are
    in this range"* -- yes: how LONG price has been coiling is a different
    reading from how narrow it is right now, and *"a thin range held for 90
    minutes has far more loaded inside it than the same range held for ten"*.
    The walk goes backward from the bar before the move while each bar's own
    range reading still ranks in the bottom `COMPRESSION_RANK`, and stops at
    the first bar that did not -- or where there is no longer enough history
    to rank, so the count is what could be VERIFIED rather than a guess.

    Reported in bars: a run of `k` compressed readings covers
    `k + RANGE_WINDOW - 1` bars, because the first reading already spans a
    whole `RANGE_WINDOW`. Zero when price is not compressed here at all.

    MEASURED DEAD END, kept as a warning. The first definition was the
    intuitive one -- take the high/low box of the last `RANGE_WINDOW` bars and
    count back while price stayed inside it. It measures the wrong thing: a
    WIDE box swallows more history, so "long dwell" came out as a synonym for
    "the recent box is wide". On the 73 cached sessions every record with a
    dwell of 10+ bars failed the compression rank -- 0 of 79 were ever CLEAR,
    and ranking against the pre-box regime instead did not rescue a single one
    (0 of 79 again). The operator's longest and best coils were the one case
    the filter could never pass, for a definitional reason and not a market
    one.
    """
    held = 0
    for m in range(len(pre) - 1, -1, -1):
        rank, _n = _rank(pre, m)
        if rank is None or rank > COMPRESSION_RANK:
            break
        held += 1
    return held + RANGE_WINDOW - 1 if held else 0


def _direction(pre):
    """(prior mean, recent mean) of the last TREND_WINDOW readings.

    *"expanding or narrowing"*, *"not narrowing or staying flat"* -- so the
    LEVEL of the range is not the whole answer; its trend across the run-up is
    a second reading. The two halves of the run-up are compared and only the
    SIGN of the difference is ever used, so no magnitude is a threshold here.

    The readings overlap -- consecutive ones share all but one bar -- so this
    is a smoothed trend rather than a bar-to-bar one. That is wanted: the
    question is what the run-up was doing, not what the last minute did.

    There is no "not enough readings" case to handle: `TREND_WINDOW` is
    smaller than `TRAIL_MIN`, and the caller has already refused to rank
    anything with fewer than `TRAIL_MIN` readings.
    """
    half = TREND_WINDOW // 2
    win = pre[-TREND_WINDOW:]
    return sum(win[:half]) / half, sum(win[half:]) / (TREND_WINDOW - half)


def _trap(view, i, days):
    """What was PRICE doing before this move? CLEAR / SUSPECT / UNKNOWN.

    *"smart money always make possition is narrow change once they load there
    position than the market start moving"*. A break out of a coil is the real
    thing; a spike out of a range that was already opening up is the trap (the
    reference case is 2026-07-30 12:30 -- straight up, no follow-through, gave
    it all back to near the day's low).

    Three separate readings, all on price, none on the envelope:

      * RANGE  -- the high/low of the last `RANGE_WINDOW` bars before the
        move, over the leg's own vwap, RANKED against the last `TRAIL_WINDOW`
        readings. Trailing, not session-so-far: see `TRAIL_WINDOW`.
      * DWELL  -- for how many consecutive bars the range has stayed that
        narrow. Reported always, with its bar count; it is context the
        operator asked for, not a gate, so it never turns a CLEAR into a
        SUSPECT nor a SUSPECT into a CLEAR on its own.
      * DIRECTION -- whether that range was narrowing, flat or expanding into
        the break. *"not narrowing or staying flat"* is the trap's tell, so an
        EXPANDING range is a SUSPECT however low it ranks.

    STILL OPEN with the operator: they said a long-held thin range has more
    loaded inside it than a short one, which reads like a strength ordering
    among coils, but they never said a long dwell should be able to override
    a rank that says the range is not narrow, nor how long is long. So dwell
    is reported and never gates. Ask before making it one.

    CLEAR needs the range to be both narrow AND not expanding. UNKNOWN is a
    real answer and is never rounded to CLEAR: "we checked and it is fine",
    "it is too early to check" and "it is before the operator's 09:25 anchor"
    are three different claims and each says so in its own words.

    Returns `(verdict, why, dwell)`; `dwell` is None where it was never
    reached.
    """
    bar = _bar(view, i)
    minute = _minute(bar.get("t")) if bar else None
    if minute is None:
        return "UNKNOWN", (f"this bar carries no readable clock label, so the "
                           f"operator's {ANCHOR_HHMM} anchor cannot be "
                           f"checked and compression is untested"), None
    if minute < ANCHOR_MINUTE:
        return "UNKNOWN", (f"this bar is {bar['t']}, before the "
                           f"{ANCHOR_HHMM} anchor -- there is too little "
                           f"session to say what price was doing, so "
                           f"compression is untested"), None

    pts = _price_points(view, i, days)
    pre_pts = [p for p in pts if p[0] <= i - 1]
    if len(pre_pts) < RANGE_WINDOW:
        return "UNKNOWN", (f"only {len(pre_pts)} readable bar(s) of this "
                           f"session before the move; {RANGE_WINDOW} are "
                           f"needed for one range reading, so compression is "
                           f"untested"), None

    pre = _ranges(pre_pts)
    cur = pre[-1]
    rank, seen = _rank(pre, len(pre) - 1)
    if rank is None:
        return "UNKNOWN", (f"only {seen} range reading(s) of session history "
                           f"before this move; {TRAIL_MIN} are needed before "
                           f"a range can be ranked, so compression is "
                           f"untested"), None

    narrow = rank <= COMPRESSION_RANK
    dwell = _dwell(pre)
    shape = (f"range before the move {cur:.4f} of vwap, rank {rank:.2f} of "
             f"the last {seen} readings")
    held = (f"price has held a range that narrow for {dwell} consecutive "
            f"bar(s)" if dwell else
            "price is not holding a narrow range here at all")

    prior, recent = _direction(pre)
    word = ("expanding" if recent > prior else
            "narrowing" if recent < prior else "flat")
    move = (f"the range was {word} into it ({prior:.4f} -> {recent:.4f} of "
            f"vwap across the last {TREND_WINDOW} readings)")
    if narrow and word != "expanding":
        return "CLEAR", (f"broke out of a coil: {shape} (bottom "
                         f"{COMPRESSION_RANK:.0%}), {held}, and "
                         f"{move}"), dwell
    if narrow:
        return "SUSPECT", (f"{shape} (bottom {COMPRESSION_RANK:.0%}) and "
                           f"{held}, but {move} -- the coil was already "
                           f"opening up before this bar"), dwell
    return "SUSPECT", (f"{shape} -- not in the bottom "
                       f"{COMPRESSION_RANK:.0%}, so price was not coiling "
                       f"into this move; {held}, and {move}"), dwell


def detect(legs, axis=None):
    """The band-rotation records for one `/api/contract` request.

    `legs` is `build_contract(...)["legs"]` -- `{"CE": leg, "PE": leg}` -- or
    the whole payload, which is unwrapped. Returns a list the length of the
    shared axis: `None` where nothing fired, else::

        {"i": int, "side": "BUY"|"SELL", "leg": "CE"|"PE",
         "band": "d2"|"d3"|"u3", "trigger": str,
         "also": [str] | None,      # hits on this bar that lost the tie-break
         "confirm": "CONFIRMED"|"UNCONFIRMED"|"UNKNOWN", "confirm_why": str,
         "trap": "CLEAR"|"SUSPECT"|"UNKNOWN", "trap_why": str,
         "trap_dwell": int | None}  # bars price held its pre-move box

    Nothing is ever raised for shape: a missing leg, a null bar, a band the
    feed never sent -- each removes what it removes and is said out loud in
    the receipts, because a fabricated read here is a trade.
    """
    if isinstance(legs, dict) and "legs" in legs:      # a whole payload
        payload = legs
        if axis is None:
            axis = payload.get("axis")
        legs = payload.get("legs")
    legs = legs if isinstance(legs, dict) else {}
    views = {name: _view(legs[name])
             for name in _LEGS if isinstance(legs.get(name), dict)}
    if not views:
        return []

    n = max([len(v["bars"]) for v in views.values()]
            + [len(axis) if isinstance(axis, (list, tuple)) else 0])
    if n == 0:
        return []

    # One day label per axis slot. `_align_to_axis` writes the same
    # `bar_days` onto every leg, so any leg's is the axis's; the axis itself
    # wins when it was passed. Unlabelled bars are one session, which is what
    # a single-day request is.
    days = [None] * n
    if isinstance(axis, (list, tuple)) and len(axis) == n:
        days = [a[0] if isinstance(a, (list, tuple)) and a else None
                for a in axis]
    else:
        for v in views.values():
            if len(v["days"]) == n:
                days = v["days"]
                break

    out = []
    for i in range(n):
        hits = []
        for name in _LEGS:
            view = views.get(name)
            bar = _bar(view, i) if view else None
            band = _band(view, i) if view else None
            if bar is None or band is None:
                continue
            hit = _trigger(bar, band)
            if hit:
                hits.append((name, hit))
        if not hits:
            out.append(None)
            continue
        # Interpretation 6: one record per bar, strongest sigma first, then
        # CE before PE so the choice is deterministic and replayable. The
        # loser is NAMED rather than dropped -- both legs qualifying on one
        # minute is the pair rotating in its purest form, and a consumer that
        # only ever sees the winner cannot tell that apart from a lone tag.
        name, hit = min(hits, key=lambda h: (-_SIGMA[h[1]["band"]],
                                             _LEGS.index(h[0])))
        also = [_trigger_why(n, h) for n, h in hits if n != name] or None
        trigger = _trigger_why(name, hit)
        if also:
            trigger += (f" (the other leg qualified on this same bar too -- "
                        f"{'; '.join(also)} -- and one record is emitted per "
                        f"bar, the deeper sigma reported)")
        confirm, confirm_why = _confirm(views, name, i, days, hit["side"])
        trap, trap_why, dwell = _trap(views[name], i, days)
        out.append({"i": i, "side": hit["side"], "leg": name,
                    "band": hit["band"], "trigger": trigger, "also": also,
                    "confirm": confirm, "confirm_why": confirm_why,
                    "trap": trap, "trap_why": trap_why, "trap_dwell": dwell})
    return out
