"""The operator's own setup: an option premium at a band extreme, reversing.

Spec `docs/superpowers/specs/2026-07-31-operator-band-rotation-setup.md`.
This is the first analytic in the tool that encodes the OPERATOR's edge rather
than someone else's read, so the quotes below are theirs and the code is meant
to be checkable against them line by line.

Pure computation, stdlib only, NO I/O -- the same isolation as
`chain_metrics.py` / `structure.py` / `contract_bars.py`, and never imported by
`engine.py`. Wiring it into `/api/contract` is a separate task.

    legs (one shared axis)  ->  trigger  ->  confirm  ->  trap  ->  records
                                (this leg) (other leg  (the INDEX
                                            + both OI)  band width)

INPUT is exactly what `live.build_contract` returns: `legs["CE"]` and
`legs["PE"]`, each ``{"bars": [...], "vwap": [...], "oi": [...],
"bar_days": [...]}``, every array indexed by the ONE shared axis
(`live._align_to_axis`), so `CE.bars[i]` and `PE.bars[i]` are the same minute
of the same session or an explicit `None` where that leg did not print. Bars
carry `contract_bars.BAR_KEYS` (`t,o,h,l,c,v,oi`), bands `BAND_KEYS`
(`vwap,u1,d1,u2,d2,u3,d3`) -- the option's OWN premium VWAP, not the index's.
A whole `/api/contract` payload is accepted too and unwrapped.

SECOND INPUT, optional: `index_series` -- the INDEX (futures) bars for the
same sessions, carrying `t` and the same band keys. The TRIGGER stays on the
option leg's own bands, where the operator buys the touch; only the
compression / trap read is taken from the index underneath it. Without it
compression is `UNKNOWN` -- never `CLEAR`, and never silently re-derived from
premium. See `_trap`.

OUTPUT is one slot per axis index, `None` where nothing fired, so a consumer
can zip it straight onto the bars.

SECOND ENTRY POINT: `detect_index`, which runs the SAME trigger on a single
series -- the index's own bars, as `/api/data` already publishes them. The
operator's setup is theirs whatever chart it prints on, and the Trade tab
shows the index, so a d2 reversal there was going unflagged. It shares
`_trigger` rather than reimplementing it, and it is honest about what a single
series cannot answer: `confirm` is UNKNOWN on every record, because the pair
rotation and the two-book OI read have no meaning without an opposite leg.
See that function.

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
    moving"* -- the trap filter reads what the INDEX's VWAP BAND was doing
    BEFORE the move, not the move itself: how tight it was, how long it held
    that tightness, and whether it was narrowing or expanding into the break.
  * *"squeeze on index entry on option chart"* (2026-07-31) -- the squeeze is
    judged on the index and the entry is taken on the option. That one
    sentence is why this module reads two series.

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
  7. COMPRESSION IS MEASURED ON THE INDEX BAND. See `_trap` -- the operator's
     own correction of 2026-07-31, and the reason this module's first two
     versions did not work. `WIDTH_BANDS` records why the +/-3 sigma pair was
     picked over +/-1.
  8. THE INDEX JOIN IS BY (session, bar label), and the run-up is every index
     reading of THIS session whose label sorts strictly before the trigger
     bar's -- not the axis slots. The axis is the union of the two OPTION
     legs' minutes; a minute neither option printed is still a minute the
     index's band existed, and dropping it would put a hole in the very
     history the rank is taken against. The index series is therefore expected
     at the SAME bar interval as the legs: the windows below are counted in
     index readings, so a 1-minute index under a 3-minute option chart would
     silently shorten every one of them to a third of its intended span.

NO ABSOLUTE MARKET THRESHOLDS. The sigma bands are the operator's own relative
thresholds and are used as given. Everything this module adds on top is rank
or sign based -- the index band width is RANKED against a trailing window,
dwell and the two OI reads are counts and SIGNS, never an index level, a rupee
level or a lot count. The width is used in POINTS, unnormalised, exactly as
the operator reads it off the chart, and it needs no normalising to stay
index-independent: a rank is invariant under any positive rescaling of the
series and the direction test uses only the sign of a difference, so NIFTY at
24k and SENSEX at 80k decide identically. (Normalising by the option leg's
VWAP is what broke version one -- premium decays, so width/vwap rose
mechanically even while the band sat still. If a normaliser is ever needed
here it must be a stable denominator such as the index level itself, never a
decaying premium.) The one clock time in the module is the operator's own
09:25 anchor, which is a session landmark rather than a market level.
`test_band_rotation.py` locks all of this down, because an absolute number
here would silently work on one index and misfire on another.

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
# The two bands whose distance IS the width: the outermost pair, the
# operator's own "last line". Their difference is what their Kite export was
# measured in and what the verified 2026-07-30 phase table quotes (09:25
# 104.7 -> 12:30 87.4, the day's tightest -> 12:40 163.7 -> 13:00 173.2, the
# day's widest). The +/-1 sigma pair tracks the SAME shape on that session
# (34.9 -> 29.1 -> 57.4), so the choice is not load-bearing; +/-3 is taken
# because it is the pair the operator quoted and the pair the trigger fires
# on, and because at six sigma wide the feed's own price quantisation is a
# proportionally smaller share of the number being ranked.
WIDTH_BANDS = ("u3", "d3")

# How many recent width readings the pre-move reading is ranked against. This
# is THE fix for the first version's first defect: ranking against the session
# so far measured how late in the day it was, because the first version
# normalised width by the OPTION's VWAP and premium decays, so `width / vwap`
# rose monotonically (median `(u1-d1)/vwap` 0.117 -> 0.388 across session
# deciles, measured over 73 cached sessions) whatever the band did. On the
# index the width itself contracts and expands, and a trailing window asks the
# operator's actual question -- "is the band tight compared to how it has been
# lately" -- with no session-clock bias. 30 readings is ~90 minutes at the
# default 3-minute interval: long enough to be a population, short enough not
# to reach back to the open.
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

# A pre-move index width in the bottom 30% of the trailing readings is
# "compression". Carried over unchanged from the COILING state the rest of the
# tool already uses (`bw_r < 0.3`, see the Tape Chart spec) so the same word
# means the same thing in two places, and deliberately NOT retuned against the
# output of this module. It is a RANK, not a width, so it carries across
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


def _index_rows(series):
    """`[(session|None, "HH:MM", width)]` from whatever index shape came in.

    `None` (not a list) means NOTHING WAS SUPPLIED, which is a different fact
    from "supplied and unreadable" and gets a different receipt. Two shapes
    are accepted, both of which already exist in this codebase:

      * LEG SHAPE -- ``{"bars": [...], "vwap": [...], "bar_days": [...]}``,
        what `live._leg_series` returns when it is pointed at the futures
        security id. Bands live in `vwap[i]`, one per bar.
      * FLAT SHAPE -- a sequence of bar dicts each carrying `t` and the band
        keys directly, which is `/api/data`'s `day.bars[].fut` (there `vwap`
        is a NUMBER, so a nested band dict is the only thing that can shadow
        the bar itself, and the two shapes cannot be confused). A session
        label is read from `day` / `d` / `date` when the bar carries one.

    A bar with no clock label, no readable u3/d3, or a non-positive width is
    dropped rather than repaired: a width of zero is not a squeeze, it is a
    band we could not read.
    """
    if series is None:
        return None
    if isinstance(series, dict):
        bars = series.get("bars")
        if not isinstance(bars, (list, tuple)):
            return []
        vw, dys = series.get("vwap") or [], series.get("bar_days") or []
        items = [(_at(dys, i), b, _at(vw, i)) for i, b in enumerate(bars)]
    elif isinstance(series, (list, tuple)):
        items = [(b.get("day") or b.get("d") or b.get("date"), b, b.get("vwap"))
                 for b in series if isinstance(b, dict)]
    else:
        return []

    rows = []
    for day, bar, band in items:
        if not isinstance(bar, dict):
            continue
        src = band if isinstance(band, dict) else bar
        t = bar.get("t")
        up, dn = (_num(src.get(k)) for k in WIDTH_BANDS)
        if not isinstance(t, str) or up is None or dn is None or up - dn <= 0:
            continue
        rows.append((day if isinstance(day, str) else None, t, up - dn))
    return rows


def _index_by_day(series, days):
    """`({session: [(t, width)] sorted}, None)` or `(None, why)`.

    Grouped by session and sorted by clock label so a run-up can be taken as
    "every reading of THIS session before this label" -- interpretation 8.

    An index series carrying no session labels at all is a single-session
    series, and is placed on the request's session when the request has
    exactly one. With more than one it is REFUSED rather than guessed at:
    joining an unlabelled series onto a multi-session axis would let one day's
    band rank another day's bar, which is the exact leak `bar_days` exists to
    stop.
    """
    rows = _index_rows(series)
    if rows is None:
        return None, ("no index series was supplied, so compression was not "
                      "measured -- the squeeze is read on the INDEX and is "
                      "never fallen back to the option premium, where a "
                      "decaying VWAP makes width grow on its own")
    if not rows:
        return None, ("the index series carried no bar with a readable "
                      f"{WIDTH_BANDS[0]}/{WIDTH_BANDS[1]} band, so "
                      "compression could not be measured on the index")
    sessions = {d for d in days if d is not None}
    if any(r[0] is None for r in rows) and len(sessions) > 1:
        return None, (f"the index series carries no session labels but this "
                      f"request spans {len(sessions)} sessions, so it cannot "
                      f"be joined session by session; compression was not "
                      f"measured rather than measured against the wrong day")
    fill = next(iter(sessions)) if len(sessions) == 1 else None
    by_day = {}
    for day, t, w in rows:
        by_day.setdefault(day if day is not None else fill, []).append((t, w))
    for v in by_day.values():
        v.sort(key=lambda r: r[0])
    return by_day, None


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
    """For how many consecutive index BARS the band has stayed compressed.

    *"is its a good thing to notice or keep in mind for how long the price are
    in this range"* -- yes: how LONG the index has been coiling is a different
    reading from how tight it is right now, and *"a thin range held for 90
    minutes has far more loaded inside it than the same range held for ten"*.
    The walk goes backward from the reading before the move while each
    reading's OWN trailing rank still sits in the bottom `COMPRESSION_RANK`,
    and stops at the first one that did not -- or where there is no longer
    enough history to rank it, so the count is what could be VERIFIED rather
    than a guess. One reading is one index bar, so the count is already in
    bars. Zero when the band is not compressed here at all.

    MEASURED DEAD END, kept as a warning. When compression was read on option
    PRICE, dwell was first defined as containment -- take the high/low box of
    the last few bars and count back while price stayed inside it. It measures
    the wrong thing: a WIDE box swallows more history, so "long dwell" came
    out as a synonym for "the recent box is wide". On the 73 cached sessions
    every record with a dwell of 10+ bars failed the compression rank -- 0 of
    79 were ever CLEAR, and ranking against the pre-box regime instead did not
    rescue a single one (0 of 79 again). Defining dwell in terms of the very
    rank it accompanies, as here, is what avoids that.
    """
    held = 0
    for m in range(len(pre) - 1, -1, -1):
        rank, _n = _rank(pre, m)
        if rank is None or rank > COMPRESSION_RANK:
            break
        held += 1
    return held


def _direction(pre):
    """(prior mean, recent mean) of the last TREND_WINDOW readings.

    *"expanding or narrowing"*, *"not narrowing or staying flat"* -- so the
    LEVEL of the width is not the whole answer; its trend across the run-up is
    a second reading. The two halves of the run-up are compared and only the
    SIGN of the difference is ever used, so no magnitude is a threshold here.

    Two halves rather than a bar-to-bar difference because the question is
    what the run-up was doing, not what the last minute did -- the reference
    session's 11:50 -> 12:30 contraction runs 100.9 -> 87.4 points over many
    bars and is not visible in any single step.

    There is no "not enough readings" case to handle: `TREND_WINDOW` is
    smaller than `TRAIL_MIN`, and the caller has already refused to rank
    anything with fewer than `TRAIL_MIN` readings.
    """
    half = TREND_WINDOW // 2
    win = pre[-TREND_WINDOW:]
    return sum(win[:half]) / half, sum(win[half:]) / (TREND_WINDOW - half)


def _trap(by_day, why_none, day, t):
    """What was the INDEX BAND doing before this move? CLEAR/SUSPECT/UNKNOWN.

    *"smart money always make possition is narrow change once they load there
    position than the market start moving"*, and *"squeeze on index entry on
    option chart"*. A break out of a coil in the INDEX is the real thing; a
    spike out of an index band that was already opening up is the trap. The
    reference case is 2026-07-30 12:30 -- their own Kite export of NIFTY AUG
    FUT has the +/-3 sigma width at 100.9 points at 11:50, 87.4 at 12:30 (the
    day's tightest), 163.7 by 12:40 and 173.2 at 13:00, while the future ran
    ~110 points. Both halves of the operator's picture -- the squeeze and the
    blast out of it -- are in that one series and in neither option premium.

    Three readings, all on the index's own VWAP band, none on the option:

      * WIDTH  -- `u3 - d3` in POINTS at the last index reading of this
        session BEFORE the move, RANKED against the last `TRAIL_WINDOW`
        readings. Absolute, never divided by a VWAP: see the module docstring
        for why normalising by a decaying premium is what broke version one,
        and `TRAIL_WINDOW` for why the window is trailing and not
        session-so-far. The trigger bar's own reading is excluded -- its
        expansion IS the move, not the run-up.
      * DWELL  -- for how many consecutive index bars the width has stayed
        that tight. Reported always, with its bar count; it is context the
        operator asked for, not a gate, so it never turns a CLEAR into a
        SUSPECT nor a SUSPECT into a CLEAR on its own.
      * DIRECTION -- whether the band was narrowing, flat or expanding into
        the break. *"the whole vwap bands are expanding not narrowing or
        staying flat"* is the trap's tell, so an EXPANDING band is a SUSPECT
        however low it ranks.

    STILL OPEN with the operator: they said a long-held thin range has more
    loaded inside it than a short one, which reads like a strength ordering
    among coils, but they never said a long dwell should be able to override
    a rank that says the band is not tight, nor how long is long. So dwell is
    reported and never gates. Ask before making it one.

    CLEAR needs the band to be both tight AND not expanding. UNKNOWN is a real
    answer and is never rounded to CLEAR -- "we checked and it is fine", "no
    index series reached us", "it is too early to check" and "it is before the
    operator's 09:25 anchor" are four different claims and each says so in its
    own words.

    Returns `(verdict, why, dwell)`; `dwell` is None where it was never
    reached.
    """
    if by_day is None:
        return "UNKNOWN", why_none, None
    minute = _minute(t)
    if minute is None:
        return "UNKNOWN", (f"this bar carries no readable clock label, so it "
                           f"cannot be placed against the index series nor "
                           f"against the operator's {ANCHOR_HHMM} anchor, and "
                           f"compression is untested"), None
    if minute < ANCHOR_MINUTE:
        return "UNKNOWN", (f"this bar is {t}, before the {ANCHOR_HHMM} anchor "
                           f"-- *\"by 9:25 we have the values for vwap "
                           f"standard deviation\"* -- so compression is "
                           f"untested"), None

    rows = by_day.get(day)
    if rows is None and day is None and len(by_day) == 1:
        rows = next(iter(by_day.values()))     # one unlabelled session, joined
    pre = [w for lbl, w in (rows or []) if lbl < t]
    if not pre:
        return "UNKNOWN", (f"the index series carries no readable band before "
                           f"{t} in this session, so compression is "
                           f"untested"), None

    rank, seen = _rank(pre, len(pre) - 1)
    if rank is None:
        return "UNKNOWN", (f"only {seen} index band reading(s) of this "
                           f"session before the move; {TRAIL_MIN} are needed "
                           f"before a width can be ranked, so compression is "
                           f"untested"), None

    cur = pre[-1]
    narrow = rank <= COMPRESSION_RANK
    dwell = _dwell(pre)
    shape = (f"index band {cur:.1f} points wide ({WIDTH_BANDS[0]}-"
             f"{WIDTH_BANDS[1]}) before the move, rank {rank:.2f} of the last "
             f"{seen} readings")
    held = (f"the index band has held a width that tight for {dwell} "
            f"consecutive bar(s)" if dwell else
            "the index band is not holding a tight width here at all")

    prior, recent = _direction(pre)
    word = ("expanding" if recent > prior else
            "narrowing" if recent < prior else "flat")
    move = (f"it was {word} into the move ({prior:.1f} -> {recent:.1f} points "
            f"across the last {TREND_WINDOW} readings)")
    if narrow and word != "expanding":
        return "CLEAR", (f"broke out of an index squeeze: {shape} (bottom "
                         f"{COMPRESSION_RANK:.0%}), {held}, and "
                         f"{move}"), dwell
    if narrow:
        return "SUSPECT", (f"{shape} (bottom {COMPRESSION_RANK:.0%}) and "
                           f"{held}, but {move} -- the squeeze was already "
                           f"releasing before this bar"), dwell
    return "SUSPECT", (f"{shape} -- not in the bottom "
                       f"{COMPRESSION_RANK:.0%}, so the index was not "
                       f"squeezing into this move; {held}, and {move}"), dwell


# --- The single-series (INDEX) entry point -------------------------------
# The name a single-series record files itself under. Not "CE"/"PE": there is
# no leg here, and a consumer that groups by `leg` must never bucket an index
# signal with an option one.
INDEX_LEG = "index"

# Why a single series can never be CONFIRMED. This is not a data gap that
# better inputs would close -- it is structural: `_confirm` is a Kleene AND of
# "is the OTHER leg rotating off its opposite extreme" and "is OI decelerating
# on BOTH books", and an index has neither an other leg nor a strike's OI. So
# the answer is UNKNOWN, said in these words, on every index record.
SINGLE_SERIES_CONFIRM_WHY = (
    "a single index series has no opposite leg: the rotation half of the "
    "confirmation (*\"the other side is also coming down from the +3 +2 upper "
    "line\"*) and the two-book OI deceleration are both undefined here, so "
    "this is trigger plus compression context only and is never CONFIRMED")

INDEX_ROTATION_RULE = (
    "`rotation` is the band-rotation trigger run on THIS INDEX's own bars, "
    "one slot per bar of `bars`, null where nothing fired -- rotation[i] and "
    "bars[i] are the same minute. A record is the operator's own setup: the "
    "bar's low pierced its d2/d3 (or its high pierced u3) and the SAME bar "
    "closed back on the other side of that band. `confirm` is ALWAYS "
    "\"UNKNOWN\" here and `confirm_why` says why -- the pair rotation and the "
    "two-book OI deceleration that /api/contract's `rotation` can answer do "
    "not exist for one series. `trap` is the same compression read as there, "
    "and it was already measured on the index, so it applies unchanged. "
    "Additive: a consumer that does not know the key must ignore it.")


def _index_bar(row):
    """One index bar, from either shape `/api/data` and this module accept.

      * DAY ROW  -- `{"t": "HH:MM", "fut": {o,h,l,c,vwap,u1..d3, ...}, ...}`,
        i.e. an element of `/api/data`'s `day.bars`. The clock label lives on
        the ROW and the bands live under `fut`, so the two are merged into one
        dict here (the row's `t` wins: it is the bar's own label).
      * FLAT     -- a dict already carrying `t` AND the band keys, which is
        what `_index_rows` documents as the flat shape.

    None for anything else -- a null row keeps its slot in the output rather
    than shifting every later index by one.
    """
    if not isinstance(row, dict):
        return None
    fut = row.get("fut")
    if not isinstance(fut, dict):
        return row
    t = row.get("t")
    return dict(fut, t=t) if isinstance(t, str) else dict(fut)


def detect_index(bars, days=None):
    """The band-rotation records for ONE series -- the index's own bars.

    The operator found this gap on their own chart: `detect` above only ever
    watches OPTION legs, and the Trade tab shows the INDEX, so a textbook
    instance of their setup on NIFTY itself passed unflagged (2026-07-31,
    09:39: low 24371.10 tagged d2 24376.80 and the same bar closed 24385.00,
    then ran ~34 points).

    THE TRIGGER IS THE SAME CODE, not a second implementation: `_trigger` was
    already a single-series primitive -- it reads one bar and one band dict and
    knows nothing about legs -- so this passes the index bar as BOTH, since an
    index bar carries its own VWAP bands. Change the trigger and both callers
    change together, which is the point.

    WHAT IS DELIBERATELY NOT THE SAME:

      * CONFIRMATION DOES NOT EXIST HERE. See `SINGLE_SERIES_CONFIRM_WHY`.
        `confirm` is `"UNKNOWN"` on every record -- never `"CONFIRMED"`, and
        never omitted, because a consumer reading a record with no `confirm`
        field would have to guess, and the guess that costs money is the
        optimistic one.
      * THE COMPRESSION / TRAP READ IS UNCHANGED. It was ALREADY an index
        read (the operator's 2026-07-31 correction: *"squeeze on index entry
        on option chart"*), and here the series it ranks and the series that
        triggered are the same one -- which is what the operator does when
        they read the squeeze and the reversal off the same NIFTY chart.

    INTERPRETATION, AND IT IS OPEN. The buy-at-d2/d3 / sell-only-at-u3
    asymmetry is inherited verbatim from `BUY_BANDS`/`SELL_BANDS`, and the
    operator gave it for an option PREMIUM (*"a stretched premium can stretch
    further"* -- a premium has a floor at zero and no ceiling, which an index
    does not). Whether the same asymmetry is what they want on the index is a
    question for them; it is inherited rather than silently symmetrised so
    that there is exactly one place to change it if the answer is no.

    `bars` is `/api/data`'s `day.bars` (or a flat list -- see `_index_bar`).
    `days` is an optional per-bar session label; a single-session payload
    needs none, and unlabelled bars are one session, which is what a day is.

    Returns a list the LENGTH OF `bars`, aligned 1:1 with it, `None` where
    nothing fired, else the same record shape `detect` emits (plus `t`, the
    bar's own label) with `leg` set to `INDEX_LEG` and `also` always None --
    there is no other leg that could have lost a tie-break.
    """
    if not isinstance(bars, (list, tuple)) or not bars:
        return []
    rows = [_index_bar(b) for b in bars]
    n = len(rows)
    day_list = (list(days) if isinstance(days, (list, tuple)) and len(days) == n
                else [None] * n)
    # The trigger series IS the compression series. Normalised once, not per
    # bar, exactly as `detect` does it.
    by_day, why_none = _index_by_day(rows, day_list)

    out = []
    for i, bar in enumerate(rows):
        if bar is None:
            out.append(None)
            continue
        hit = _trigger(bar, bar)       # one series: it carries its own bands
        if hit is None:
            out.append(None)
            continue
        t = bar.get("t")
        trap, trap_why, dwell = _trap(by_day, why_none, _at(day_list, i), t)
        out.append({"i": i, "t": t if isinstance(t, str) else None,
                    "side": hit["side"], "leg": INDEX_LEG, "band": hit["band"],
                    "trigger": _trigger_why(INDEX_LEG, hit), "also": None,
                    "confirm": "UNKNOWN",
                    "confirm_why": SINGLE_SERIES_CONFIRM_WHY,
                    "trap": trap, "trap_why": trap_why, "trap_dwell": dwell})
    return out


# --- The operator's ACTUAL rule: a two-candle run -------------------------
# Pre-registered in `context/research-findings.md` §5c on 2026-08-05. UNSCORED
# -- nothing may be drawn or traded off this until §5c's number lands.
#
# `_trigger` above is a ONE-candle rule and is deliberately left alone: the
# two-leg `detect` path shares it, seven tests lock its semantics, and
# `trigger_log.py` parses its receipt sentence. This is a SECOND detector so
# the two can be scored head to head; when the number arrives, one of them wins
# and the loser goes.
#
# The difference in one line: `_trigger` wants ONE bar to pierce d3 AND close
# back above it. This wants a bar to TOUCH d3, then a LATER bar to close above
# THAT bar's high. The entry is therefore later, and higher.

# The only band this rule reads. A NAME, never a price level.
RUN_BAND = "d3"
# How many bars a reference stays live. The operator said 10 candles and the
# scoring path feeds 3-minute bars, so this is their 30 minutes -- counted in
# BARS like every other window here, so it cannot drift with the interval the
# way a wall-clock deadline would.
RUN_WINDOW = 10


def _run_read(bar):
    """(low, high, close, d3, vwap) as finite floats, or None if the bar's own
    OHLC cannot be read. `d3` and `vwap` may each be None -- a missing band is
    a fact the caller handles, never a zero."""
    low, high, close = (_num(bar.get(k)) for k in ("l", "h", "c"))
    if low is None or high is None or close is None:
        return None
    return low, high, close, _num(bar.get(RUN_BAND)), _num(bar.get("vwap"))


def _run_why(ref_t, ref_high, level, close, waited):
    """The receipt. Worded so it can never be confused with `_trigger_why`'s
    sentence -- `trigger_log.py` parses that one, and the two rules must stay
    tellable apart in a log written months from now."""
    at = f" at {ref_t}" if isinstance(ref_t, str) and ref_t else ""
    bars = "bar" if waited == 1 else "bars"
    return (f"index low touched {RUN_BAND} {_f(level)}{at}, then closed "
            f"{_f(close)} above that candle's high {_f(ref_high)} "
            f"{waited} {bars} later")


def detect_index_run(bars, days=None, stop_pts=None):
    """The operator's own two-candle d3 setup, one slot per bar of `bars`.

    ARM      a bar whose low TOUCHES d3 (no close-back needed). That bar is
             the reference; its HIGH is the level to beat. Gated at 09:25 off
             the bar's own clock label, so it lands right on any interval.
    RE-ARM   a later bar printing a NEW LOWER LOW becomes the reference, and
             the countdown restarts with it. A run of falling lows is ONE
             setup, not a stack of them.
    TRIGGER  a bar that CLOSES above the reference's high. A wick through is
             not a trigger. Entry is that close.
    EXPIRE   no trigger within RUN_WINDOW bars of the current reference.

    `stop_pts` is the re-fire lock's only price input and is a PARAMETER, not
    a module constant: after an entry the next setup cannot arm until price
    touches VWAP, or -- when the caller says what the stop was -- until that
    stop is hit. Called without it, the lock is VWAP-only, which is the
    conservative reading (it can only ever suppress a later signal, never
    invent one). The stop itself belongs to the scorer, not here.

    Records carry the same keys `detect_index` emits, so every existing
    consumer reads them unchanged, plus `ref_i` / `ref_high` / `level` /
    `waited` describing the run that produced the entry.

    The loop lives in `run_states`, which emits the same machine as a state PER
    BAR; this is the entries-only view of it. One implementation, two readings
    -- see `run_states` for why that is not optional.
    """
    return [s["entry"] for s in run_states(bars, days, stop_pts)]


def run_states(bars, days=None, stop_pts=None):
    """The same two-candle setup as a state PER BAR, not only its entries.

    `detect_index_run` answers "where did it fire". A screen also has to answer
    "where does this stand right now", which is the operator's five-state
    machine: WAITING -> ARMED -> TRIGGERED -> IN_TRADE -> OUT. Both readings
    come out of this one loop on purpose. Two implementations of one state
    machine drift, and the drift is invisible: the chart would mark an entry
    the scorer never counted, or sit ARMED through a bar the scorer had already
    triggered on, and nothing anywhere would raise.

    Returns a list the length of `bars`::

        {"i": int, "t": str|None,
         "state": "WAITING" | "ARMED" | "TRIGGERED" | "IN_TRADE",
         "ref_i": int|None, "ref_high": float|None, "level": float|None,
         "candles_left": int|None,        # of RUN_WINDOW, from the live ref
         "entry": record|None,            # exactly what detect_index_run emits
         "exit_why": "stop"|"vwap"|None,  # the bar the re-fire lock cleared
         "readable": bool}                # False: the bar had no usable read

    OUT is deliberately not one of the enum values. A bar can clear the lock
    AND arm the next setup within the same bar -- the loop falls through rather
    than continuing -- so collapsing that into one label would silently throw
    the arming away. `exit_why` carries the exit; a reader renders OUT from it.

    An unreadable bar (`readable: False`) reports the state it is still IN, not
    WAITING. A missing read is not evidence the setup went away, and rendering
    it as WAITING would blink a live reference off the screen.
    """
    if not isinstance(bars, (list, tuple)) or not bars:
        return []
    rows = [_index_bar(b) for b in bars]
    n = len(rows)
    day_list = (list(days) if isinstance(days, (list, tuple)) and len(days) == n
                else [None] * n)
    # Same compression series the one-candle path uses, normalised once.
    by_day, why_none = _index_by_day(rows, day_list)

    out = [None] * n
    ref = None            # the live reference candle, or None
    lock = None           # {"stop": float|None} while a trade is considered open
    cur_day = object()    # sentinel: the first bar always opens a session

    for i, bar in enumerate(rows):
        day = _at(day_list, i)
        if day != cur_day:
            # A new session starts clean: a reference never survives the close.
            cur_day, ref, lock = day, None, None
        t = bar.get("t") if bar is not None else None
        entry = exit_why = None
        read = _run_read(bar) if bar is not None else None
        readable = read is not None

        if readable:
            low, high, close, lvl, vwap = read

            # 1. The re-fire lock outranks everything. Note it does NOT skip the
            #    bar that CLEARS it -- that bar falls through and may arm the
            #    next setup, which is why OUT is a flag here and not a state.
            live = True
            if lock is not None:
                if lock["stop"] is not None and low <= lock["stop"]:
                    lock, exit_why = None, "stop"
                elif vwap is not None and high >= vwap:
                    lock, exit_why = None, "vwap"
                else:
                    live = False

            if live:
                # 2. Expire a reference that waited too long.
                if ref is not None and i - ref["i"] > RUN_WINDOW:
                    ref = None

                # The three branches below are mutually exclusive, which the
                # original spelled with `continue`. An if/elif chain says the
                # same thing while still letting every bar emit a state.
                if ref is not None and low < ref["low"]:
                    # 3. A new lower low MOVES the reference (and restarts its
                    #    clock). Such a bar cannot also trigger -- it would be
                    #    beating its own high.
                    ref = {"i": i, "t": t, "low": low, "high": high,
                           "level": lvl if lvl is not None else ref["level"]}
                elif ref is None:
                    # 4. Arm on a TOUCH of d3, after 09:25. A bar with no
                    #    readable clock is not assumed to be late enough.
                    minute = _minute(t) if isinstance(t, str) else None
                    if (lvl is not None and low <= lvl
                            and minute is not None and minute >= ANCHOR_MINUTE):
                        ref = {"i": i, "t": t, "low": low, "high": high,
                               "level": lvl}
                elif close > ref["high"]:
                    # 5. Trigger: a CLOSE above the reference's high.
                    trap, trap_why, dwell = _trap(by_day, why_none, day, t)
                    waited = i - ref["i"]
                    entry = {"i": i, "t": t if isinstance(t, str) else None,
                             "side": "BUY", "leg": INDEX_LEG, "band": RUN_BAND,
                             "trigger": _run_why(ref["t"], ref["high"],
                                                 ref["level"], close, waited),
                             "also": None,
                             "confirm": "UNKNOWN",
                             "confirm_why": SINGLE_SERIES_CONFIRM_WHY,
                             "trap": trap, "trap_why": trap_why,
                             "trap_dwell": dwell,
                             "ref_i": ref["i"], "ref_high": ref["high"],
                             "level": ref["level"], "waited": waited}
                    lock = {"stop": (ref["level"] - stop_pts)
                            if (stop_pts is not None and ref["level"] is not None)
                            else None}
                    ref = None

        if entry is not None:
            state = "TRIGGERED"
        elif lock is not None:
            state = "IN_TRADE"
        elif ref is not None:
            state = "ARMED"
        else:
            state = "WAITING"
        out[i] = {
            "i": i, "t": t if isinstance(t, str) else None, "state": state,
            "ref_i": ref["i"] if ref is not None else None,
            "ref_high": ref["high"] if ref is not None else None,
            "level": (entry["level"] if entry is not None
                      else (ref["level"] if ref is not None else None)),
            "candles_left": (RUN_WINDOW - (i - ref["i"])
                             if ref is not None else None),
            "entry": entry, "exit_why": exit_why, "readable": readable,
        }
    return out


def detect(legs, axis=None, index_series=None):
    """The band-rotation records for one `/api/contract` request.

    `legs` is `build_contract(...)["legs"]` -- `{"CE": leg, "PE": leg}` -- or
    the whole payload, which is unwrapped (`index_series` too: the payload's
    `index` key is the index NAME, so the series rides under its own key).

    `index_series` is the INDEX/futures bars for the same sessions -- the
    series the compression read is taken from. Optional, and when it is
    missing every `trap` is `UNKNOWN` saying so; it is never approximated from
    the option premium. Returns a list the length of the shared axis: `None`
    where nothing fired, else::

        {"i": int, "side": "BUY"|"SELL", "leg": "CE"|"PE",
         "band": "d2"|"d3"|"u3", "trigger": str,
         "also": [str] | None,      # hits on this bar that lost the tie-break
         "confirm": "CONFIRMED"|"UNCONFIRMED"|"UNKNOWN", "confirm_why": str,
         "trap": "CLEAR"|"SUSPECT"|"UNKNOWN", "trap_why": str,
         "trap_dwell": int | None}  # index bars the band held that width

    Nothing is ever raised for shape: a missing leg, a null bar, a band the
    feed never sent -- each removes what it removes and is said out loud in
    the receipts, because a fabricated read here is a trade.
    """
    if isinstance(legs, dict) and "legs" in legs:      # a whole payload
        payload = legs
        if axis is None:
            axis = payload.get("axis")
        if index_series is None:
            index_series = payload.get("index_series")
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

    # The index series is normalised ONCE per request, not per bar: it is the
    # same series for every slot and re-grouping it 375 times would be the
    # only expensive thing in this module.
    by_day, why_none = _index_by_day(index_series, days)

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
        # The bar's OWN clock label, not a bar count -- so the 09:25 anchor
        # lands at 09:25 on a 1-, 3- or 15-minute chart alike, and so the
        # index join is by (session, label) rather than by axis position.
        trap, trap_why, dwell = _trap(by_day, why_none, _at(days, i),
                                      _bar(views[name], i).get("t"))
        out.append({"i": i, "side": hit["side"], "leg": name,
                    "band": hit["band"], "trigger": trigger, "also": also,
                    "confirm": confirm, "confirm_why": confirm_why,
                    "trap": trap, "trap_why": trap_why, "trap_dwell": dwell})
    return out
