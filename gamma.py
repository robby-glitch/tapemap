"""Black-Scholes pricing, implied volatility and dealer GEX profile.

TapeMap gamma layer, Stage 2 (architecture boundary: gamma.py = pure math,
stdlib only, no I/O). Consumed by gex_run.py; never imported by engine.py.

Model: Black-76 (the correct form for a futures underlying): no r-drift in
d1 — the future already embeds carry — and BOTH legs discounted at
r = 0.065. Price = e^{-rT} * (F*N(d1) - K*N(d2)) for calls.

Dealer sign convention (validated in the Stage-1 GEX-lite study): dealers are
LONG gamma on writer-built books (writer score w > 0 -> hedging dampens) and
SHORT gamma on buyer-built books (w < 0 -> hedging amplifies), so
    gex_k = gamma_k * (ce_oi * ce_w + pe_oi * pe_w)
is dealer-signed gamma exposure per strike (relative units: gamma x contracts;
only signs, zero crossings and rank order are consumed downstream).
"""

import math

R = 0.065   # domestic risk-free rate (discounting only — Black-76)


def _pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _cdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _d1(F, K, iv, T):
    # Black-76: no r-drift term (F is already a forward)
    return (math.log(F / K) + 0.5 * iv * iv * T) / (iv * math.sqrt(T))


def bs_price(F, K, iv, T, kind="C"):
    """Black-76 European option price on a future F."""
    df = math.exp(-R * max(T, 0.0))
    if T <= 0.0 or iv <= 0.0:
        base = max(F - K, 0.0) if kind == "C" else max(K - F, 0.0)
        return df * base
    d1 = _d1(F, K, iv, T)
    d2 = d1 - iv * math.sqrt(T)
    if kind == "C":
        return df * (F * _cdf(d1) - K * _cdf(d2))
    return df * (K * _cdf(-d2) - F * _cdf(-d1))


def vega(F, K, iv, T):
    """dPrice/dIV, identical for calls and puts (Black-76)."""
    if T <= 0.0 or iv <= 0.0:
        return 0.0
    return math.exp(-R * T) * F * _pdf(_d1(F, K, iv, T)) * math.sqrt(T)


def gamma(F, K, iv, T):
    """Black-76 gamma: d2Price/dF2, identical for calls and puts."""
    if T <= 0.0 or iv is None or iv <= 0.0:
        return 0.0
    return math.exp(-R * T) * _pdf(_d1(F, K, iv, T)) / (F * iv * math.sqrt(T))


IV_LO, IV_HI = 0.01, 2.0    # bisection bracket: 1% to 200% annualized vol


def implied_vol(price, F, K, T, kind="C"):
    """Invert BS for IV. Newton first, bisection fallback. None if unsolvable."""
    if T <= 0.0 or price is None or price <= 0.0 or F <= 0.0 or K <= 0.0:
        return None
    intrinsic = bs_price(F, K, 0.0, T, kind)
    if price <= intrinsic + 1e-9:
        return None                      # below arb floor: no finite IV
    # Newton from a mid-of-bracket seed
    iv = 0.2
    for _ in range(50):
        diff = bs_price(F, K, iv, T, kind) - price
        if abs(diff) < 1e-8:
            return iv
        v = vega(F, K, iv, T)
        if v < 1e-12:
            break                        # flat vega: hand over to bisection
        iv -= diff / v
        if not (IV_LO * 0.5 < iv < IV_HI * 1.5):
            break                        # walked out of sane territory
    # bisection fallback on [IV_LO, IV_HI]
    lo, hi = IV_LO, IV_HI
    f_lo = bs_price(F, K, lo, T, kind) - price
    f_hi = bs_price(F, K, hi, T, kind) - price
    if f_lo * f_hi > 0.0:
        return None                      # price outside the bracket's range
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        f_mid = bs_price(F, K, mid, T, kind) - price
        if abs(f_mid) < 1e-8:
            return mid
        if f_lo * f_mid <= 0.0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return 0.5 * (lo + hi)


def gex_profile(strikes_data, F, T):
    """Dealer-signed GEX profile across strikes at one minute.

    strikes_data: list of {"k", "ce_oi", "pe_oi", "ce_iv", "pe_iv",
                           "ce_w", "pe_w"} (w = Stage-1 writer score in
    [-1, 1]; iv may be None when never solved -> strike skipped).

    Returns {"gex_total", "flip_px", "wall_up", "wall_dn"}:
      flip_px  the spot level where TOTAL dealer-signed GEX changes sign,
               found by revaluing the whole book at hypothetical spots across
               the strike range and interpolating the zero crossing nearest the
               current spot F (None if total GEX never changes sign). This is
               the true gamma flip, not the cumulative-across-strikes proxy.
      wall_up  strike above F with max |gex_k| at the current spot (None if
               none / all zero)
      wall_dn  same below F
    """
    # (strike, mean solved IV, dealer-signed OI weight) per usable strike
    cache = []
    for s in strikes_data:
        ivs = [v for v in (s.get("ce_iv"), s.get("pe_iv")) if v]
        if not ivs:
            continue
        mean_iv = sum(ivs) / len(ivs)
        w_oi = s["ce_oi"] * s["ce_w"] + s["pe_oi"] * s["pe_w"]
        cache.append((s["k"], mean_iv, w_oi))
    if not cache:
        return {"gex_total": None, "flip_px": None, "flip_status": "NO_IV",
                "wall_up": None, "wall_dn": None}
    cache.sort()

    def total_at(Fh):
        """Total dealer-signed GEX with the book revalued at spot Fh."""
        return sum(gamma(Fh, k, iv, T) * w_oi for k, iv, w_oi in cache)

    gex_total = total_at(F)

    # per-strike GEX at the current spot (drives the walls)
    rows = [(k, gamma(F, k, iv, T) * w_oi) for k, iv, w_oi in cache]

    # true flip: scan hypothetical spots over [min_k, max_k], interpolate every
    # sign change of total GEX, keep the crossing nearest the current spot F
    lo, hi = cache[0][0], cache[-1][0]
    flip_px = None
    # A missing flip has three causes and they mean different things to a
    # trader: the book never changes sign anywhere in range (a REGIME, and
    # worth saying out loud), only one strike was usable (no scan possible),
    # or no IV solved at all (we could not look). Returning a bare None for
    # all three makes "there is no flip" indistinguishable from "we don't
    # know", which is the one conflation this repo does not allow.
    flip_status = "ONE_STRIKE"
    if hi > lo:
        flip_status = "NO_CROSSING"
        step = (hi - lo) / 200.0
        prev_F, prev_v = lo, total_at(lo)
        for n in range(1, 201):
            cur_F = lo + n * step
            cur_v = total_at(cur_F)
            if prev_v != cur_v and (
                    (prev_v < 0.0 <= cur_v) or (prev_v > 0.0 >= cur_v)):
                cross = prev_F + (cur_F - prev_F) * (0.0 - prev_v) / (cur_v - prev_v)
                if flip_px is None or abs(cross - F) < abs(flip_px - F):
                    flip_px = cross
                    flip_status = "FOUND"
            prev_F, prev_v = cur_F, cur_v

    def _wall(cands):
        if not cands:
            return None
        k, g = max(cands, key=lambda kg: abs(kg[1]))
        return k if abs(g) > 0.0 else None

    wall_up = _wall([(k, g) for k, g in rows if k > F])
    wall_dn = _wall([(k, g) for k, g in rows if k < F])

    return {"gex_total": gex_total, "flip_px": flip_px,
            "flip_status": flip_status,
            "wall_up": wall_up, "wall_dn": wall_dn}
