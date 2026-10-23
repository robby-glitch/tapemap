"""Noise floor of buyer / seller flow RATES and of two SPEED measures, from the Upstox 1-min bars (pr_1m_<IDX>.json,
rebuilt from the book ticks by the repo's own ladder.Ladder, pr_build1m.py). DESCRIPTIVE ONLY: distributions of the
inputs, no outcome, no forward return. Run: python -B pr_flowrate.py > pr_flowrate_out.txt

Rate_W(m)  = lots bought (or sold) in the W minutes ending at minute m, / W            (lots per minute)
acc(m)     = rate_5(m) - rate_5(m-5)            first-difference "speed"
rel(m)     = rate_5(m) / rate_30(m)             short over long, scale-free
gap(m)     = pct(rate_5) - pct(rate_30)         each ranked against its 30-min slot on the OTHER days
pct        = leave-one-day-out percentile within the same 30-min slot (window end minute)
Null       = minutes shuffled within each day x 30-min slot (keeps time-of-day and day level, kills ordering),
             ranked against the REAL reference tables.
"""
import json, sys
import numpy as np
from scipy.stats import spearmanr

sys.dont_write_bytecode = True
FULL = ['2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30',
        '2026-10-01', '2026-10-05', '2026-10-06', '2026-10-08', '2026-10-19']
EXPIRY = {'NIFTY': {'2026-09-22', '2026-09-29', '2026-10-06', '2026-10-19'}, 'BANKNIFTY': {'2026-09-29'},
          'SENSEX': {'2026-09-24', '2026-10-01', '2026-10-08'}}   # chain `expiry` / surface files; 29 Sep is also the futures roll
M0, M1 = 558, 930                     # 09:18 .. 15:29 (the recorder starts ~09:17; that minute is partial)
MIN = np.arange(M0, M1)
SLOT = (MIN - 555) // 30              # 30-min slot of the window-END minute, 0 = 09:15-09:44
NS = SLOT.max() + 1
RNG = np.random.default_rng(20261020)
NSHUF = 40


def load(idx):
    d = json.load(open(f'pr_1m_{idx}.json'))
    B = np.full((len(FULL), len(MIN)), np.nan)
    S = B.copy()
    for i, day in enumerate(FULL):
        for b in d[day]['1m']:
            m = (int(b['t'] // 60000) + 330) % 1440
            if M0 <= m < M1 and not b['partial']:
                B[i, m - M0], S[i, m - M0] = b['buy'], b['sell']
    return B, S


def roll(X, W):
    """mean of the last W minutes ending at each minute; NaN unless all W are present."""
    out = np.full(X.shape, np.nan)
    c = np.nancumsum(np.nan_to_num(X), axis=1)
    ok = (~np.isnan(X)).astype(int).cumsum(axis=1)
    for j in range(W - 1, X.shape[1]):
        s = c[:, j] - (c[:, j - W] if j >= W else 0)
        n = ok[:, j] - (ok[:, j - W] if j >= W else 0)
        out[:, j] = np.where(n == W, s / W, np.nan)
    return out


def ref_tables(V):
    """per (day, slot): sorted values of the OTHER days in that slot (leave-one-day-out)."""
    T = {}
    for s in range(NS):
        cols = SLOT == s
        for i in range(V.shape[0]):
            o = np.delete(V[:, cols], i, axis=0).ravel()
            T[i, s] = np.sort(o[~np.isnan(o)])
    return T


def pct(V, T):
    P = np.full(V.shape, np.nan)
    for (i, s), ref in T.items():
        if not len(ref):
            continue
        cols = np.where(SLOT == s)[0]
        x = V[i, cols]
        ok = ~np.isnan(x)
        lo = np.searchsorted(ref, x[ok], 'left')
        hi = np.searchsorted(ref, x[ok], 'right')
        P[i, cols[ok]] = 100 * (lo + hi) / 2 / len(ref)
    return P


def shuffle(X):
    Y = X.copy()
    for i in range(X.shape[0]):
        for s in range(NS):
            cols = np.where(SLOT == s)[0]
            Y[i, cols] = X[i, RNG.permutation(cols)]
    return Y


def lagpair(V, k):
    a, b = V[:, :-k].ravel(), V[:, k:].ravel()
    ok = ~np.isnan(a) & ~np.isnan(b)
    return a[ok], b[ok]


def sp(a, b):
    return round(float(spearmanr(a, b)[0]), 2) if len(a) > 10 else None


def q(x, ps=(10, 50, 90)):
    x = np.asarray(x)
    x = x[~np.isnan(x)]
    return [round(float(np.percentile(x, p)), 2) for p in ps] if len(x) else None


def hm(m):
    return f'{m // 60:02d}:{m % 60:02d}'


def section_rates(idx, B, S, detail):
    print(f'\n=== {idx}: RATES (lots/min), {len(FULL)} full days, expiry days {sorted(EXPIRY[idx] & set(FULL))} ===')
    vol_day = np.nansum(B + S, axis=1)
    print('day volume (lots) min / median / max:', int(vol_day.min()), int(np.median(vol_day)), int(vol_day.max()),
          '| buy share of day volume min/max:', round(float((np.nansum(B, 1) / vol_day).min()), 3), round(float((np.nansum(B, 1) / vol_day).max()), 3))
    for side, X in (('BUY', B), ('SELL', S)):
        R = {W: roll(X, W) for W in (1, 3, 5, 15)}
        if detail:
            print(f'\n{side} rate by 30-min slot (window end), pooled over days and minutes: p10 / p50 / p90')
            print('slot          3-min                    15-min')
            for s in range(NS):
                cols = SLOT == s
                print(f'{hm(555 + 30 * s)}  ', q(R[3][:, cols]), '  ', q(R[15][:, cols]))
        print(f'\n{side}: noise structure of the slot-ranked rate')
        print(' W | lagW-corr of pct (adjacent, non-overlapping) | median |pct swing| real vs shuffled-null [5-95%] '
              '| top-decile windows: max minute >= half of window | day-volume rho with share of windows >= p90')
        for W in (1, 3, 5, 15):
            T = ref_tables(R[W])
            P = pct(R[W], T)
            a, b = lagpair(P, W)
            swing = float(np.median(np.abs(a - b)))
            nul = []
            for _ in range(NSHUF):
                Pn = pct(roll(shuffle(X), W), T)
                an, bn = lagpair(Pn, W)
                nul.append(float(np.median(np.abs(an - bn))))
            # one-minute dominance in the top decile
            Xm = np.full(X.shape, np.nan)
            for j in range(W - 1, X.shape[1]):
                Xm[:, j] = np.nanmax(X[:, j - W + 1:j + 1], axis=1) if W > 1 else X[:, j]
            top = P >= 90
            dom = (Xm[top] >= 0.5 * R[W][top] * W).mean() if W > 1 else float('nan')
            share90 = [np.mean(P[i][~np.isnan(P[i])] >= 90) for i in range(len(FULL))]
            rho = sp(vol_day, share90)
            print(f'{W:2d} | {sp(a, b)} | {swing:.1f} vs {np.mean(nul):.1f} [{np.percentile(nul, 5):.1f}-{np.percentile(nul, 95):.1f}] '
                  f'| {dom:.2f} (n {int(top.sum())}) | {rho}  (share>=p90 per day {min(share90):.2f}-{max(share90):.2f})')
        # variance decomposition of log rate
        for W in (3, 15):
            L = np.log(R[W] + 1.0)
            slotm = np.array([np.nanmean(L[:, SLOT == s]) for s in range(NS)])[SLOT]
            r1 = L - slotm
            daym = np.nanmean(r1, axis=1, keepdims=True)
            r2 = r1 - daym
            tot = np.nanvar(L)
            print(f'  log rate_{W}: variance share  time-of-day {1 - np.nanvar(r1) / tot:.2f} · day level '
                  f'{(np.nanvar(r1) - np.nanvar(r2)) / tot:.2f} · within day x slot {np.nanvar(r2) / tot:.2f}')


def section_speed(idx, B, S):
    print(f'\n=== {idx}: SPEED — first difference vs short/long ratio (rate_5 vs rate_30) ===')
    vol_day = np.nansum(B + S, axis=1)
    for side, X in (('BUY', B), ('SELL', S)):
        r5, r30 = roll(X, 5), roll(X, 30)
        acc = np.full(r5.shape, np.nan)
        acc[:, 5:] = r5[:, 5:] - r5[:, :-5]
        rel = np.where(r30 > 0, r5 / r30, np.nan)
        lrel = np.log(np.where(rel > 0, rel, np.nan))
        p5, p30 = pct(r5, ref_tables(r5)), pct(r30, ref_tables(r30))
        gap = p5 - p30
        prev5 = np.full(r5.shape, np.nan)
        prev5[:, 5:] = r5[:, :-5]
        T5, T30 = ref_tables(r5), ref_tables(r30)
        # the null: shuffled minutes, the same measures
        def measures(Y):
            a5, a30 = roll(Y, 5), roll(Y, 30)
            ac = np.full(a5.shape, np.nan)
            ac[:, 5:] = a5[:, 5:] - a5[:, :-5]
            rl = np.where(a30 > 0, a5 / a30, np.nan)
            return ac, np.log(np.where(rl > 0, rl, np.nan)), pct(a5, T5) - pct(a30, T30)
        nul = [measures(shuffle(X)) for _ in range(NSHUF)]
        rows = (('acc  r5(t)-r5(t-5)', acc, np.abs(acc), prev5), ('rel  r5/r30 (log)', lrel, np.abs(lrel), r30),
                ('gap  pct5-pct30', gap, np.abs(gap), p30))
        print(f'\n{side}')
        print(' measure | first minute | lag-5 rho | same sign at +5 min | rho with its own base (mechanical) '
              '| p90 of |x| real vs null [5-95%] | top decile: one minute carries it | day-vol rho w/ top-decile share')
        for k, (name, V, A, base) in enumerate(rows):
            a, b = lagpair(V, 5)
            same = np.mean(np.sign(a) == np.sign(b))
            ok = ~np.isnan(V) & ~np.isnan(base)
            mech = sp(V[ok], base[ok])
            first = MIN[np.where(~np.isnan(V).all(axis=0))[0][0]] if (~np.isnan(V)).any() else None
            p90 = float(np.nanpercentile(A, 90))
            nn = [float(np.nanpercentile(np.abs(x[k]), 90)) for x in nul]
            # one-minute dependence: replace the biggest minute of the 5-min window by the window's median minute
            thr70 = np.nanpercentile(A, 70)
            topm = A >= np.nanpercentile(A, 90)
            flips, n = 0, 0
            for i, j in zip(*np.where(topm)):
                if j < 4:
                    continue
                w = X[i, j - 4:j + 1].copy()
                if np.isnan(w).any():
                    continue
                w[np.argmax(w)] = np.median(w)
                n5 = w.mean()
                if k == 0:
                    v2 = abs(n5 - prev5[i, j])
                elif k == 1:
                    v2 = abs(np.log(n5 / r30[i, j])) if n5 > 0 and r30[i, j] > 0 else np.nan
                else:
                    ref = T5[i, SLOT[j]]
                    v2 = abs(100 * np.searchsorted(ref, n5) / len(ref) - p30[i, j])
                if not np.isnan(v2):
                    n += 1
                    flips += v2 < thr70
            share = [np.nanmean(topm[i][~np.isnan(V[i])]) for i in range(len(FULL))]
            print(f' {name} | {hm(first) if first else "?"} | {sp(a, b)} | {same:.2f} | {mech} | {p90:.2f} vs '
                  f'{np.mean(nn):.2f} [{np.percentile(nn, 5):.2f}-{np.percentile(nn, 95):.2f}] | {flips}/{n} '
                  f'| {sp(vol_day, share)}')


if __name__ == '__main__':
    for idx in ('NIFTY', 'BANKNIFTY', 'SENSEX'):
        B, S = load(idx)
        section_rates(idx, B, S, detail=True)
        section_speed(idx, B, S)
