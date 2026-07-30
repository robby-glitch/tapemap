"""contract_pair.py -- the 09:20 premium-matched leg picker.

Operator spec: docs/superpowers/specs/2026-07-31-operator-band-rotation-setup.md,
section "Leg selection". The operator follows a CE at one strike and a PE at
ANOTHER strike whose premiums are nearly equal shortly after the open, then
tracks that pair all day. This is a premium-PARITY pair, not "the one strike
where CE == PE" -- that single-strike crossing point is explicitly NOT the
setup. Reference case: SENSEX 77500 CE paired with 78000 PE -- different
strikes, generally neither delta-neutral nor equidistant from spot, and
nothing downstream may assume otherwise.

Pure stdlib, no I/O. Mirrors the chain_metrics.py / structure.py isolation:
never imported by engine.py.

INPUT SHAPE. `chain_rows` is the `strikes` list off a chain snapshot. Verified
against the "Snapshot contract" documented at the top of chain_metrics.py and
against data/chain_sample.jsonl (chain_live.py's own mock fixture)::

    [{"k": <int strike>,
      "ce": {"ltp": <float>, ...},
      "pe": {"ltp": <float>, ...}}, ...]

The strike key is **`k`**, not `strike` -- `ui-v2/src/data.ts` (`cstrikes.find
(s => s.k === atm)`, `s.ce?.ltp ?? 0`) renames it to `strike` only in its OWN
derived `StrikeRow`; the wire/snapshot payload itself never does. `ltp` is
confirmed as the premium field on both `ce` and `pe` books (same two
sources). A `strike` key is accepted as a defensive fallback if `k` is
absent, but `k` is what the real feed actually sends.

RETURN CONTRACT. `pick_pair(chain_rows, idx, tol=None, atm=None)` returns a
`(pair, why)` tuple -- always two values. This is a deliberate small
departure from the plan doc's inline sketch of a single
`{"ce": ..., "pe": ..., "why": str}` dict on success only: with a single
dict shape, "return None with a reason string" on failure has nowhere to put
the reason. A `(pair, why)` tuple lets a caller do `pair, why = pick_pair(...)`
and check `pair is None` uniformly in both cases. `why` is always a
non-empty string naming the actual numbers involved (invariant #7 -- every
signal carries its receipt). On success::

    pair = {"ce": {"strike": <float>, "ltp": <float>},
            "pe": {"strike": <float>, "ltp": <float>}}

On failure (nothing inside tolerance, or no usable data at all) `pair` is
`None`.

THE OBJECTIVE (fixed 2026-07-31; this used to minimise `abs(ce_ltp - pe_ltp)`
over every admitted cross pair -- see "WHY THE OBJECTIVE CHANGED" below).
Ranking now runs in two stages over the pairs that already passed the
tolerance ADMISSION GATE:

    1. PRIMARY key -- distance to the ATM straddle:
       `abs(ce_strike - atm) + abs(pe_strike - atm)`.
       Smallest wins. This is the sum of each leg's own distance from ATM,
       not a distance between the two legs.
    2. TIE-BREAK -- `abs(ce_ltp - pe_ltp)`, smallest wins. Only reached when
       two or more candidates sit at the exact same ATM distance.
    3. A final deterministic tie-break (lowest CE strike, then lowest PE
       strike) so the result never depends on dict/set ordering.

`atm` is an explicit parameter now: pass the chain snapshot's own top-level
`atm` (see `chain_live.normalize` / `ChainPoller._publish`, and how
`server.py`'s `/api/contract` handler and `live.build_contract` thread it
through) so no extra request and no proxy are needed for a live call. When
`atm` is not supplied, `_atm_proxy` derives an ESTIMATE from `chain_rows`
itself -- the strike (if any) whose own CE and PE premiums are closest to
each other, i.e. the classic put-call-parity approximation for ATM. `why`
always says which one was used ("atm=<value> (supplied)" vs "atm=<value>
(proxy, no atm given)"), so a caller can tell a real ATM apart from an
estimate. If neither is available (no `atm` argument and no same-strike
CE/PE row to build a proxy from), ranking falls back to the OLD rule --
smallest `abs(ce_ltp - pe_ltp)` first, then the same deterministic
strike order -- and `why` says plainly that no ATM information existed.

WHY THE OBJECTIVE CHANGED. Measured on real cached snapshots
(`data/chain/chain_NIFTY_2026-07-30.jsonl`, `chain_SENSEX_2026-07-30.jsonl`,
09:20 rows): deep-OTM wings on both sides decay to near-zero premium on
BOTH legs, so their difference is tiny (~0.05) and a bare
`min(abs(ce_ltp - pe_ltp))` search picks them almost every time --
- NIFTY 2026-07-30 09:20 (spot 24262.05): old rule chose CE 24800@4.40 /
  PE 23250@4.40 (a 4-way tie at diff 0), while the ATM straddle
  24300 CE@106.10 / 24300 PE@114.70 (diff 8.60) lost outright.
- SENSEX same day 09:20 (spot 77665.2): old rule chose CE 78300@11.05 /
  PE 76900@11.05, both deep OTM.
- Of 668 cross pairs admitted by the SENSEX gate that day, 520 sat inside
  tolerance -- the tolerance gate was doing almost no selecting; the
  minimise-diff objective was doing all the (wrong) work.

The operator was asked whether to add a premium floor or a
fraction-of-the-ATM-straddle constraint instead. Their answer, verbatim:
"yeah straddle is about right because they almost forms mirror charts."
The reasoning: near-the-money CE and PE mirror each other (delta ~= +/-0.5),
which is the property their setup actually reads off the chart. Deep wings
do not mirror one another -- they merely decay together, which looks like
agreement in raw premium but is not the same market behaviour.

OPEN OBSERVATION, not a settled question -- record, do not silently drop:
the operator's own reference charts were SENSEX 77500 CE and 78000 PE, but
at 09:20 those two legs' premiums differed by Rs 173.25 -- far outside the
+/-50 tolerance -- and only converged to within Re 1 of each other at 13:39
(both ~Rs 264.65). So that reference pair cannot have been produced by a
09:20 +/-50 rule of any kind, minimise-diff or nearest-ATM. The most likely
reading, consistent with "straddle is about right", is that the rule
selects the near-ATM pair EARLY in the session and the operator's reference
charts were simply whatever pair they happened to be watching mid-session,
by which time strikes/premiums had moved. This is evidence for the
nearest-ATM objective being the right one, not proof of it -- still open.

TOLERANCE. Defaults by index, overridden by an explicit `tol`. This stays a
hard ADMISSION GATE only -- it is never widened, and it never determines
which admitted pair wins; ranking (above) does that::

    NIFTY      +/-30
    BANKNIFTY  +/-50
    SENSEX     +/-50

An unrecognised `idx` with no explicit `tol` is a hard error -- there is no
safe default to fall back to without guessing, and guessing a tolerance is
exactly the "widen it to force a pair" failure mode this module must not have.

HONESTY RULES:
  * A pair with the same CE and PE strike is never considered -- the operator
    was explicit that this is not "one strike where CE == PE".
  * A missing or non-finite `ltp` on either book removes that book at that
    strike from consideration entirely; it is never treated as a premium
    of 0.
  * Tolerance is never widened to manufacture a pair. No candidate inside
    tolerance means `pick_pair` returns `(None, why)`, never a next-closest
    guess outside tolerance.
"""

import math

TOL_BY_IDX = {"NIFTY": 30, "BANKNIFTY": 50, "SENSEX": 50}


def _finite(x):
    """A finite float, or None. Bools are not numbers here."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    f = float(x)
    return f if math.isfinite(f) else None


def _legs(chain_rows, side):
    """`chain_rows` -> `[(strike, ltp), ...]` for one book ('ce'/'pe'),
    skipping any row whose strike or premium is missing / non-finite."""
    out = []
    for row in chain_rows or ():
        if not isinstance(row, dict):
            continue
        strike = _finite(row.get("k", row.get("strike")))
        if strike is None:
            continue
        book = row.get(side)
        ltp = _finite(book.get("ltp")) if isinstance(book, dict) else None
        if ltp is None:
            continue
        out.append((strike, ltp))
    return out


def _atm_proxy(chain_rows):
    """The strike (if any) whose own CE and PE premiums are closest to each
    other -- an ATM ESTIMATE used only when the caller supplies no real
    `atm`. See the module docstring's "WHY THE OBJECTIVE CHANGED" section:
    this is the classic put-call-parity approximation for ATM, and, notably,
    the exact "one strike where CE == PE" point the spec says the setup is
    NOT -- it is used here purely as an internal ATM estimate, never as the
    returned pair itself.
    """
    best_k, best_diff = None, None
    for row in chain_rows or ():
        if not isinstance(row, dict):
            continue
        strike = _finite(row.get("k", row.get("strike")))
        ce, pe = row.get("ce"), row.get("pe")
        cp = _finite(ce.get("ltp")) if isinstance(ce, dict) else None
        pp = _finite(pe.get("ltp")) if isinstance(pe, dict) else None
        if strike is None or cp is None or pp is None:
            continue
        diff = abs(cp - pp)
        if best_diff is None or diff < best_diff:
            best_k, best_diff = strike, diff
    return best_k


def pick_pair(chain_rows, idx, tol=None, atm=None):
    """The nearest-to-ATM CE/PE pair (premium diff as tie-break), or
    `(None, why)`. See module docstring for the full contract, the ranking
    rule, and why it changed from a bare premium-diff minimisation."""
    if tol is None:
        tol = TOL_BY_IDX.get(idx)
        if tol is None:
            raise ValueError(
                f"pick_pair: no default tolerance for idx={idx!r}; pass "
                f"tol explicitly (defaults only cover "
                f"{sorted(TOL_BY_IDX)})")
    tol = float(tol)
    atm = _finite(atm)

    if not chain_rows:
        return None, "empty chain_rows: no strikes to pick a pair from"

    ce_legs = _legs(chain_rows, "ce")
    pe_legs = _legs(chain_rows, "pe")
    if not ce_legs or not pe_legs:
        return None, (
            f"no usable CE/PE premiums in chain_rows ({len(ce_legs)} valid "
            f"CE legs, {len(pe_legs)} valid PE legs)")

    # (diff, ce_strike, ce_ltp, pe_strike, pe_ltp) for every DIFFERENT-strike
    # cross pair; same-strike combos are the CE==PE point, not this setup.
    # Sorted by diff purely so the "nothing admitted" message below can name
    # the closest miss -- diff is NOT the ranking key once pairs are admitted.
    candidates = sorted(
        (abs(cp - pp), cs, cp, ps, pp)
        for cs, cp in ce_legs for ps, pp in pe_legs if cs != ps)

    if not candidates:
        return None, (
            "only same-strike CE/PE available in chain_rows; the setup "
            "requires a CE and PE at different strikes")

    within = [c for c in candidates if c[0] <= tol]
    if not within:
        diff, cs, cp, ps, pp = candidates[0]
        return None, (
            f"no CE/PE pair within tol +/-{tol:g} ({idx}); closest was "
            f"CE {cs:g}@{cp:g} vs PE {ps:g}@{pp:g}, diff={diff:g}")

    atm_source = "supplied"
    atm_used = atm
    if atm_used is None:
        atm_used = _atm_proxy(chain_rows)
        atm_source = "proxy, no atm given"

    if atm_used is None:
        # No real atm and no same-strike straddle to estimate one from
        # either -- fall back to the old rule (smallest premium diff, then a
        # stable strike order) rather than guessing an ATM value.
        diff, cs, cp, ps, pp = sorted(within, key=lambda c: (c[0], c[1], c[3]))[0]
        why = (
            f"CE {cs:g}@{cp:g} vs PE {ps:g}@{pp:g}: diff={diff:g} within "
            f"tol +/-{tol:g} ({idx}); no ATM available (not supplied, and "
            f"no same-strike CE/PE row to estimate one from), so ranked by "
            f"smallest premium diff among {len(within)} admitted pair(s)")
    else:
        def _atm_dist(c):
            _diff, ce_k, _cp, pe_k, _pp = c
            return abs(ce_k - atm_used) + abs(pe_k - atm_used)

        diff, cs, cp, ps, pp = sorted(
            within, key=lambda c: (_atm_dist(c), c[0], c[1], c[3]))[0]
        ce_dist, pe_dist = abs(cs - atm_used), abs(ps - atm_used)
        why = (
            f"CE {cs:g}@{cp:g} (dist {ce_dist:g} from atm) / PE {ps:g}@{pp:g} "
            f"(dist {pe_dist:g} from atm) nearest to atm={atm_used:g} "
            f"({atm_source}) among {len(within)} pair(s) within tol "
            f"+/-{tol:g} ({idx}); premium diff={diff:g} used only as tie-break")

    return {"ce": {"strike": cs, "ltp": cp},
            "pe": {"strike": ps, "ltp": pp}}, why
