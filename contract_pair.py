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

RETURN CONTRACT. `pick_pair(chain_rows, idx, tol=None)` returns a
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

ASSUMPTION NOT YET CONFIRMED WITH THE OPERATOR -- do not bury this:
when more than one CE/PE pair ties at the smallest `abs(ce_ltp - pe_ltp)`
inside tolerance, this picks the pair nearest to an ATM proxy. The picker's
signature carries no spot/atm input, so the proxy is derived from the chain
itself: the single strike (if any) where that SAME strike's own CE and PE
premiums are closest to each other -- the classic put-call-parity
approximation for ATM, and, notably, the exact "one strike where CE == PE"
point the spec says the setup is NOT. Using it only as an internal ATM
*estimate* for tie-breaking (never as the returned pair itself) is this
implementation's choice, not the operator's. Both the tie-break rule itself
and this proxy for "ATM" are open questions -- confirm with the operator
before relying on tie-broken output. Ties are detected by exact float
equality of the diff; real premiums rarely tie exactly, so in practice this
path fires on synthetic/test data far more than on live ticks.

TOLERANCE. Defaults by index, overridden by an explicit `tol`::

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
    other -- an ATM ESTIMATE used only for the tie-break, never returned as
    the pair itself. See the module docstring's unconfirmed-assumption note.
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


def pick_pair(chain_rows, idx, tol=None):
    """The premium-matched CE/PE pair, or `(None, why)`. See module
    docstring for the full contract."""
    if tol is None:
        tol = TOL_BY_IDX.get(idx)
        if tol is None:
            raise ValueError(
                f"pick_pair: no default tolerance for idx={idx!r}; pass "
                f"tol explicitly (defaults only cover "
                f"{sorted(TOL_BY_IDX)})")
    tol = float(tol)

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

    min_diff = within[0][0]
    tied = [c for c in within if c[0] == min_diff]

    if len(tied) == 1:
        diff, cs, cp, ps, pp = tied[0]
        why = (f"CE {cs:g}@{cp:g} vs PE {ps:g}@{pp:g}: diff={diff:g} within "
               f"tol +/-{tol:g} ({idx})")
    else:
        atm = _atm_proxy(chain_rows)
        if atm is None:
            # No same-strike straddle to estimate an ATM proxy from either
            # -- fall back to a stable, deterministic order (lowest CE
            # strike, then lowest PE strike) rather than guessing further.
            diff, cs, cp, ps, pp = sorted(tied, key=lambda c: (c[1], c[3]))[0]
            why = (
                f"{len(tied)} pairs tied at diff={diff:g} within tol "
                f"+/-{tol:g} ({idx}); no ATM proxy available (no strike had "
                f"both CE and PE ltp), so the lowest-strike pair CE "
                f"{cs:g}/PE {ps:g} was chosen deterministically -- "
                f"UNCONFIRMED tie-break, ask the operator")
        else:
            diff, cs, cp, ps, pp = sorted(
                tied,
                key=lambda c: (abs(c[1] - atm) + abs(c[3] - atm), c[1], c[3])
            )[0]
            why = (
                f"{len(tied)} pairs tied at diff={diff:g} within tol "
                f"+/-{tol:g} ({idx}); resolved by nearest-to-ATM proxy "
                f"(atm~={atm:g}, the strike whose own CE/PE ltp are "
                f"closest -- UNCONFIRMED tie-break rule, ask the operator): "
                f"chose CE {cs:g}@{cp:g} / PE {ps:g}@{pp:g}")

    return {"ce": {"strike": cs, "ltp": cp},
            "pe": {"strike": ps, "ltp": pp}}, why
