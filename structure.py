"""SMC / ICT structure over one session's bars, confirmed by order flow.

Tape Chart Phase 3.5 (spec section 7). Pure computation, stdlib only, no I/O
-- same isolation as chain_metrics.py / gamma.py, and NEVER imported by
engine.py: this layer reads the engine's output and does not touch its signals
(invariant 3).

Input: the payload bar list produced by engine.session_json() ---

    [{"t": "09:15",
      "fut": {"o","h","l","c","vwap","u1".."d3","oi","v",
              "z","vol_r","oi_slope","oi_r","prem_d","bw_r"} | None,
      "ce": {...} | None, "pe": {...} | None,
      "ctx": {...}?, "gamma": {...}?, "setup": {...}?}, ...]

All geometry is read off the FUT leg. A bar whose FUT leg is missing or
non-numeric is skipped, not faked (session_json always emits a FUT leg; the
guard exists so a future caller cannot crash this module). Output indices are
always indices into the ORIGINAL bar list, so the UI can address them directly.

Output: a list of

    {"kind": "FVG|OB|BOS|CHOCH|EQH|EQL|SWING_H|SWING_L",
     "i0": int, "i1": int, "born": int,      # indices into `bars`
     "hi": float, "lo": float, "dir": 1|-1,
     "confirm": "CONFIRMED|UNCONFIRMED|UNKNOWN", "confirm_why": str}

sorted by (born, kind, i0, i1).

`born` is the index of the bar that COMPLETED the structure, and every field
of a structure -- including its confirmation -- is a function of bars[0..born]
only. So replay is truncation, not recomputation (invariant 2):

    [s for s in compute(bars) if s["born"] <= k] == compute(bars[:k+1])

For point structures (SWING_H/L, BOS, CHOCH) hi == lo == the single price the
structure is about: a pivot price, or the level a close broke. For area
structures (FVG, OB, EQH, EQL) hi/lo bound the box. `dir` is +1 for anything
bullish or high-side (swing high, EQH, up-break, bullish gap/block) and -1 for
its mirror. `i0..i1` is the span the structure was read from; `born >= i1`.

DEFINITIONS (spec section 7's table). Written from the public ICT/SMC
definitions; no Pine source from LuxAlgo, fadi or anyone else was read or
copied -- reimplementing a BOS from its definition is as legitimate as
reimplementing RSI (the section 7 IP line).

  Swing / fractal  bar j is a swing high when H[j] is strictly greater than
                   the SWING_N highs on each side; born at j+SWING_N, the last
                   bar that can still invalidate it. Mirror for a swing low.
                   Strict on both wings, so a plateau is not a fractal.
  BOS              a close beyond the most recent unbroken swing extreme, in
                   the trend direction. The broken swing is then retired; the
                   next confirmed swing on that side takes its place.
  CHoCH            the same break when it goes AGAINST the prevailing trend
                   (the trend being the direction of the last break). The
                   first break of a session has no trend to contradict, so it
                   is a BOS.
  EQH / EQL        two CONSECUTIVE same-side swings whose prices sit within
                   EQ_FRAC of the realised range -- a liquidity pool. Born
                   with the second swing.
  Order block      the last opposing candle before an impulsive move, where
                   "impulsive" is a body in the top (1-OB_PCTL) of the bodies
                   printed so far AND the impulse closes past the block
                   (above its high for a bullish block, below its low for a
                   bearish one). Scanned back at most OB_LOOKBACK bars; one
                   block per (side, candle).
  FVG              the three-bar gap H[i-2] < L[i] (bullish) or L[i-2] > H[i]
                   (bearish), at least FVG_MIN_FRAC of the realised range wide.

NOT COMPUTED, and why (never invent what the input cannot source):
  * Premium / discount (the working range split at 50%) -- the payload's
    `kind` enum has no member for it, and widening a shared contract to carry
    a derived midpoint the UI can compute from a swing pair is not worth it.
  * PDH/PDL, PWH/PWL, PMH/PML -- prior day / week / month extremes need bars
    from earlier sessions. This payload carries ONE session (live.py builds
    today; analyze.py builds each day independently), so there is nothing here
    to read them from. live.py does fetch the prior session for pivots, but
    those arrive as pre-reduced P/R1..S3 numbers, not bars.

TOLERANCES are fractions of the session's OWN realised range so far, or
percentile ranks over the session's own distribution so far -- never point
values (invariant 1). The identical code therefore reads NIFTY, BANKNIFTY and
SENSEX with no recalibration, which test_structure.py proves by replaying the
same tables at 2.35x and 3.2x. Every window ends at `born`, never at the end
of the session, which is what keeps truncation honest.

FLOW CONFIRMATION -- the part SMC does not have (spec section 7). Sources are
the per-bar FUT flow fields the engine already publishes:

  EQH / EQL  did the pool FORM on distribution? vol_r in the top (1-VOL_PCTL)
             of the session so far AND oi_slope < 0 (positions leaving) on the
             second pivot bar. (The SWEEP of the pool is a later-bar question,
             deferred — see above.)                 -> CONFIRMED/UNCONFIRMED
  FVG        was the gap OPENED by real displacement? vol_r ranked high on the
             gap bar AND oi_slope summing positive across the three bars (new
             positions behind the move, not a short squeeze).
                                                    -> CONFIRMED/UNCONFIRMED
  OB         "OI built at that level?" needs per-strike chain OI (ChainState
             oi_chg / ce_w / pe_w).                 -> UNKNOWN
  BOS/CHOCH  "did the OI wall hold or migrate?" needs ChainState.role[k] and
             wall_log.                              -> UNKNOWN
  SWING_H/L  section 7's table defines no flow test for a raw pivot.
                                                    -> UNKNOWN

UNKNOWN means "we could not check" and UNCONFIRMED means "we checked and flow
did not confirm". They are different claims and must never collapse into one
rendering (honesty rule 3). A FUT-volume proxy was deliberately NOT
substituted for the missing chain reads: /api/data carries no per-strike
chain, and a number you cannot source is not a number you may publish.

Two flow questions section 7 asks that CANNOT be answered at birth, because
the answer lives in bars after `born` and invariant 2 forbids reaching for
them: the SWEEP of an EQH (as opposed to its formation) and the FILL of an
FVG (as opposed to its creation). Both need a second birth -- a structure born
on the sweep/fill bar -- which the current `kind` enum has no member for. They
are left for a later phase rather than answered dishonestly at birth.
"""

SWING_N = 3            # bars each side of a fractal pivot
EQ_FRAC = 0.05         # EQH/EQL equality, as a fraction of realised range
FVG_MIN_FRAC = 0.01    # smallest gap worth calling one, same fraction
OB_PCTL = 0.80         # a body must out-rank this share of the session's own
OB_LOOKBACK = 10       # bars to scan back for the opposing candle
VOL_PCTL = 0.70        # "vol_r high" = out-ranks this share of the session
MIN_HIST = 5           # no percentile verdict on fewer samples than this

KINDS = ("FVG", "OB", "BOS", "CHOCH", "EQH", "EQL", "SWING_H", "SWING_L")
_ORDER = {k: n for n, k in enumerate(KINDS)}

CONFIRMED, UNCONFIRMED, UNKNOWN = "CONFIRMED", "UNCONFIRMED", "UNKNOWN"

_NO_CHAIN = "/api/data carries no per-strike option chain"


# ------------------------------------------------------------------ helpers

def _num(x):
    """x as a float when it is a real number, else None (NaN is not a price)."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return None if x != x else float(x)


def _rank(vals, v):
    """Share of `vals` strictly below `v`. `vals` includes `v` itself, so the
    session's single largest sample ranks (n-1)/n -- a rank, never a level."""
    return sum(1 for x in vals if x < v) / len(vals) if vals else 0.0


def _mk(kind, i0, i1, born, hi, lo, d, confirm, why):
    return {"kind": kind, "i0": i0, "i1": i1, "born": born,
            "hi": round(hi, 2), "lo": round(lo, 2), "dir": d,
            "confirm": confirm, "confirm_why": why}


def _why_swing(price, bar_no):
    return (f"geometry only -- spec 7 defines no flow test for a raw swing "
            f"point ({price:.2f} pivoting at bar {bar_no})")


def _why_break(kind, level):
    return (f"{kind} at {level:.2f} needs the OI wall's fate there "
            f"(ChainState.role / wall_log) -- {_NO_CHAIN}")


def _why_ob(lo, hi):
    return (f"order block {lo:.2f}-{hi:.2f} needs OI built at that level "
            f"(ChainState per-strike oi_chg / ce_w / pe_w) -- {_NO_CHAIN}")


def _vol_note(V, at, born, bar_no):
    """(ok, note): does bar `at` sit in the top (1-VOL_PCTL) of the session's
    own vol_r so far? `ok` is None when the question cannot be answered, and
    the note then says what was missing -- never a silent False."""
    v = V[at]
    if v is None:
        return None, f"fut.vol_r missing on bar {bar_no}"
    win = [x for x in V[:born + 1] if x is not None]
    if len(win) < MIN_HIST:
        return None, (f"only {len(win)} bar(s) of fut.vol_r by bar {bar_no} -- "
                      f"{MIN_HIST} needed before a rank means anything")
    if max(win) == min(win):
        return None, (f"fut.vol_r identical ({v:.2f}) on all {len(win)} bars to "
                      f"bar {bar_no} -- no distribution to rank against")
    r = _rank(win, v)
    return r >= VOL_PCTL, (f"vol_r={v:.2f} ranks {r:.2f} of {len(win)} bars "
                           f"(needs >= {VOL_PCTL:.2f})")


def _confirm_pool(kind, V, S, at, born, bar_no):
    """EQH/EQL: did the pool FORM on expanded volume with OI leaving?"""
    s = S[at]
    if s is None:
        return UNKNOWN, (f"no flow read for {kind} at bar {bar_no}: "
                         f"fut.oi_slope missing")
    ok, note = _vol_note(V, at, born, bar_no)
    if ok is None:
        return UNKNOWN, f"no flow read for {kind} at bar {bar_no}: {note}"
    unwind = s < 0
    return (CONFIRMED if (ok and unwind) else UNCONFIRMED,
            f"{kind} formation at bar {bar_no} -- sweep flow is a later-bar "
            f"question, not answered here: {note}; oi_slope={s:+.0f} "
            f"({'unwinding' if unwind else 'not unwinding'})")


def _confirm_fvg(V, S, ps, born, nos):
    """FVG: was the gap opened by displacement with OI building through it?"""
    vals = [S[p] for p in ps]
    if any(v is None for v in vals):
        miss = ",".join(str(nos[k]) for k, v in enumerate(vals) if v is None)
        return UNKNOWN, (f"no flow read for FVG at bar {nos[-1]}: "
                         f"fut.oi_slope missing on bar(s) {miss}")
    ok, note = _vol_note(V, ps[-1], born, nos[-1])
    if ok is None:
        return UNKNOWN, f"no flow read for FVG at bar {nos[-1]}: {note}"
    tot = sum(vals)
    build = tot > 0
    return (CONFIRMED if (ok and build) else UNCONFIRMED,
            f"FVG opened at bar {nos[-1]}: {note}; oi_slope over bars "
            f"{nos[0]}-{nos[-1]} sums {tot:+.0f} "
            f"({'building' if build else 'not building'})")


# ------------------------------------------------------------------- public

def compute(bars):
    """Structures over one session's payload bars. See the module docstring."""
    if not bars:
        return []
    idx, O, H, L, C, V, S = [], [], [], [], [], [], []
    for i, b in enumerate(bars):
        f = b.get("fut") if isinstance(b, dict) else None
        if not isinstance(f, dict):
            continue
        o, h, l, c = (_num(f.get(k)) for k in ("o", "h", "l", "c"))
        if o is None or h is None or l is None or c is None:
            continue
        idx.append(i)
        O.append(o)
        H.append(h)
        L.append(l)
        C.append(c)
        V.append(_num(f.get("vol_r")))
        S.append(_num(f.get("oi_slope")))
    n = len(idx)
    if not n:
        return []

    out = []
    bodies = []
    hi_run, lo_run = H[0], L[0]
    prev_sh = prev_sl = None      # previous CONFIRMED swing, for EQH/EQL pairing
    last_sh = last_sl = None      # most recent UNBROKEN swing, for BOS/CHoCH
    trend = 0                     # 0 until the first break; then +1 / -1
    seen_ob = set()

    for p in range(n):
        # the session's own realised range, causally: bars 0..p and no further
        hi_run, lo_run = max(hi_run, H[p]), min(lo_run, L[p])
        rng = hi_run - lo_run
        bodies.append(abs(C[p] - O[p]))

        # -- 1. fractal pivots this bar completes (a swing cannot exist before
        # the bars that confirm it, so it is born SWING_N bars after the pivot)
        j = p - SWING_N
        if j >= SWING_N:
            hj, lj = H[j], L[j]
            if (all(H[q] < hj for q in range(j - SWING_N, j))
                    and all(H[q] < hj for q in range(j + 1, p + 1))):
                out.append(_mk("SWING_H", idx[j - SWING_N], idx[p], idx[p],
                               hj, hj, 1, UNKNOWN, _why_swing(hj, idx[j])))
                if (prev_sh is not None and rng > 0
                        and abs(hj - prev_sh[1]) <= EQ_FRAC * rng):
                    out.append(_mk("EQH", idx[prev_sh[0]], idx[j], idx[p],
                                   max(hj, prev_sh[1]), min(hj, prev_sh[1]), 1,
                                   *_confirm_pool("EQH", V, S, j, p, idx[j])))
                prev_sh = last_sh = (j, hj)
            if (all(L[q] > lj for q in range(j - SWING_N, j))
                    and all(L[q] > lj for q in range(j + 1, p + 1))):
                out.append(_mk("SWING_L", idx[j - SWING_N], idx[p], idx[p],
                               lj, lj, -1, UNKNOWN, _why_swing(lj, idx[j])))
                if (prev_sl is not None and rng > 0
                        and abs(lj - prev_sl[1]) <= EQ_FRAC * rng):
                    out.append(_mk("EQL", idx[prev_sl[0]], idx[j], idx[p],
                                   max(lj, prev_sl[1]), min(lj, prev_sl[1]), -1,
                                   *_confirm_pool("EQL", V, S, j, p, idx[j])))
                prev_sl = last_sl = (j, lj)

        # -- 2. break of structure / change of character. A swing born on this
        # bar cannot be broken by it: the fractal requires H[j] > H[j+1..p], so
        # C[p] <= H[p] < H[j]. The two are consistent by construction.
        if last_sh is not None and C[p] > last_sh[1]:
            lvl = last_sh[1]
            kind = "BOS" if trend >= 0 else "CHOCH"
            out.append(_mk(kind, idx[last_sh[0]], idx[p], idx[p], lvl, lvl, 1,
                           UNKNOWN, _why_break(kind, lvl)))
            trend, last_sh = 1, None
        if last_sl is not None and C[p] < last_sl[1]:
            lvl = last_sl[1]
            kind = "BOS" if trend <= 0 else "CHOCH"
            out.append(_mk(kind, idx[last_sl[0]], idx[p], idx[p], lvl, lvl, -1,
                           UNKNOWN, _why_break(kind, lvl)))
            trend, last_sl = -1, None

        # -- 3. fair value gap: the three-bar gap, floored relatively
        if p >= 2:
            floor = FVG_MIN_FRAC * rng
            nos = (idx[p - 2], idx[p - 1], idx[p])
            if H[p - 2] < L[p] and L[p] - H[p - 2] >= floor:
                out.append(_mk("FVG", nos[0], nos[2], nos[2],
                               L[p], H[p - 2], 1,
                               *_confirm_fvg(V, S, (p - 2, p - 1, p), p, nos)))
            if L[p - 2] > H[p] and L[p - 2] - H[p] >= floor:
                out.append(_mk("FVG", nos[0], nos[2], nos[2],
                               L[p - 2], H[p], -1,
                               *_confirm_fvg(V, S, (p - 2, p - 1, p), p, nos)))

        # -- 4. order block: the last opposing candle before an impulse
        body = bodies[p]
        if (body > 0 and len(bodies) >= MIN_HIST
                and _rank(bodies, body) >= OB_PCTL):
            up = C[p] > O[p]
            for q in range(p - 1, max(-1, p - 1 - OB_LOOKBACK), -1):
                if (C[q] < O[q]) if up else (C[q] > O[q]):
                    # the impulse must actually displace past the block
                    if (C[p] > H[q]) if up else (C[p] < L[q]):
                        key = (1 if up else -1, q)
                        if key not in seen_ob:
                            seen_ob.add(key)
                            out.append(_mk("OB", idx[q], idx[p], idx[p],
                                           H[q], L[q], 1 if up else -1,
                                           UNKNOWN, _why_ob(L[q], H[q])))
                    break

    out.sort(key=lambda s: (s["born"], _ORDER[s["kind"]], s["i0"], s["i1"]))
    return out
