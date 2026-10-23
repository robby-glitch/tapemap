"""Second pass (descriptive): (1) how much of a rate's within-day x slot variance i.i.d. minutes reproduce (variance
ratio, minute-shuffle null); (2) the DELTA side of speed -- first difference vs one-sidedness shift -- against both a
minute-shuffle and FLOW-STATE's sign-shuffle null. Uses pr_flowrate's loaders. Run: python -B pr_flowrate2.py"""
import sys
import numpy as np
sys.dont_write_bytecode = True
import pr_flowrate as F

RNG = np.random.default_rng(7)


def shuffle_block(X, block):
    Y = X.copy()
    blk = (F.MIN - 555) // block
    for i in range(X.shape[0]):
        for s in np.unique(blk):
            cols = np.where(blk == s)[0]
            Y[i, cols] = X[i, RNG.permutation(cols)]
    return Y


def within_var(L, block):
    blk = (F.MIN - 555) // block
    r = L.copy()
    for i in range(L.shape[0]):
        for s in np.unique(blk):
            cols = blk == s
            r[i, cols] = L[i, cols] - np.nanmean(L[i, cols])
    return np.nanvar(r)


def var_ratio(X, W, block, n=30):
    real = within_var(np.log(F.roll(X, W) + 1), block)
    nul = [within_var(np.log(F.roll(shuffle_block(X, block), W) + 1), block) for _ in range(n)]
    return real, float(np.mean(nul))


def lag(V, k):
    a, b = V[:, :-k].ravel(), V[:, k:].ravel()
    ok = ~np.isnan(a) & ~np.isnan(b)
    return a[ok], b[ok]


def delta_measures(B, S):
    D, V = B - S, B + S
    r5, r30, v5, v30 = F.roll(D, 5), F.roll(D, 30), F.roll(V, 5), F.roll(V, 30)
    acc = np.full(r5.shape, np.nan)
    acc[:, 5:] = r5[:, 5:] - r5[:, :-5]
    with np.errstate(invalid='ignore', divide='ignore'):
        shift = np.where((v5 > 0) & (v30 > 0), r5 / v5 - r30 / v30, np.nan)
    prev = np.full(r5.shape, np.nan)
    prev[:, 5:] = r5[:, :-5]
    with np.errstate(invalid='ignore', divide='ignore'):
        base30 = np.where(v30 > 0, r30 / v30, np.nan)
    return acc, shift, prev, base30


def sign_null(B, S):
    D, V = B - S, B + S
    sg = RNG.choice([-1, 1], size=D.shape)
    Dn = np.abs(D) * sg
    return (V + Dn) / 2, (V - Dn) / 2


if __name__ == '__main__':
    for idx in ('NIFTY', 'BANKNIFTY', 'SENSEX'):
        B, S = F.load(idx)
        print(f'\n=== {idx} ===')
        print('variance of log rate_W around its own day x block mean: real vs minute-shuffled (same block); '
              'ratio = the share i.i.d. minutes reproduce')
        for side, X in (('BUY', B), ('SELL', S)):
            for W, block in ((1, 30), (3, 30), (5, 30), (15, 60)):
                r, nl = var_ratio(X, W, block)
                print(f'  {side} W={W:2d} block {block}m: real {r:.3f} null {nl:.3f} -> i.i.d. share {nl / r:.2f}')
        D = B - S
        for W in (1, 3, 5):
            R = F.roll(D, W)
            a, b = lag(R, W)
            print(f'  delta rate W={W}: lag-{W} (adjacent) Pearson {np.corrcoef(a, b)[0, 1]:.2f}, sign kept {np.mean(np.sign(a) == np.sign(b)):.2f}')
        acc, shift, prev, base30 = delta_measures(B, S)
        nul_s = [delta_measures(*sign_null(B, S)) for _ in range(100)]
        for name, V, base, k in (('accD r5D(t)-r5D(t-5)', acc, prev, 0), ('shift D5/V5 - D30/V30', shift, base30, 1)):
            a, b = lag(V, 5)
            ok = ~np.isnan(V) & ~np.isnan(base)
            mech = np.corrcoef(V[ok], base[ok])[0, 1]
            p90 = np.nanpercentile(np.abs(V), 90)
            ns = [np.nanpercentile(np.abs(x[k]), 90) for x in nul_s]
            print(f'  {name}: lag-5 Pearson {np.corrcoef(a, b)[0, 1]:.2f}, sign kept at +5 {np.mean(np.sign(a) == np.sign(b)):.2f}, '
                  f'r with its base {mech:.2f}, p90 |x| real {p90:.3f} vs sign-shuffle {np.mean(ns):.3f} '
                  f'[{np.percentile(ns, 5):.3f}-{np.percentile(ns, 95):.3f}]')
