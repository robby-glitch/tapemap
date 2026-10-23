"""FS1m - are 5-min bars too coarse? 1-min delta rebuilt from Upstox book ticks (repo Ladder, live settings; the 5-min sums equal the shipped ux bars exactly: 955 of 955 NIFTY bars).
Full-session days only. Descriptive. SEEN."""
import json, numpy as np, collections
from fs_lib import *

for idx in ('NIFTY', 'BANKNIFTY'):
    R = json.load(open(HERE + '/fs_1m_%s.json' % idx))
    days = [d for d in sorted(R) if len(R[d]['1m']) >= 360]
    t0m = {}
    A = {}
    for d in days:
        b1 = R[d]['1m']; t0 = (min(b['t'] for b in b1) // 300000) * 300000
        t0 = b1[0]['t'] // 86400000 * 86400000 + (9 * 3600 + 15 * 60 - 19800) * 1000      # 09:15 IST of that day
        n = 375
        dl = np.zeros(n); vl = np.zeros(n)
        for b in b1:
            m = (b['t'] - t0) // 60000
            if 0 <= m < n: dl[m] += b['delta']; vl[m] += b['vol']
        A[d] = (dl, vl)
    d5 = {d: A[d][0].reshape(75, 5).sum(1) for d in days}
    allabs = np.concatenate([np.abs(x) for x in d5.values()])
    th90, th70 = np.quantile(allabs, .9), np.quantile(allabs, .7)
    print('=== %s: %d full days, %d aligned 5-min bars; pooled |5-min delta| p70 %.0f p90 %.0f lots' % (idx, len(days), len(allabs), th70, th90))
    # (a) concentration inside the bar
    conc_hi, conc_all, sgn_hi, sgn_all = [], [], [], []
    for d in days:
        dl = A[d][0].reshape(75, 5)
        for k in range(75):
            row = dl[k]; tot = row.sum()
            if abs(tot) < 1e-9 or np.abs(row).sum() == 0: continue
            share = np.abs(row).max() / np.abs(row).sum()
            nsame = int((np.sign(row) == np.sign(tot)).sum())
            conc_all.append(share); sgn_all.append(nsame)
            if abs(tot) >= th90: conc_hi.append(share); sgn_hi.append(nsame)
    print('(a) inside the 5-min bar: share of the five 1-min |delta| carried by the largest minute')
    print('    all bars (%d): median %.2f ; bars with |d5|>=p90 (%d): median %.2f, one minute >= 50%% of the bar in %d of %d' % (len(conc_all), np.median(conc_all), len(conc_hi), np.median(conc_hi), sum(c >= .5 for c in conc_hi), len(conc_hi)))
    print('    minutes agreeing with the bar sign (of 5): bars |d5|>=p90: 5 of 5 in %d, 4 in %d, 3 in %d, <=2 in %d of %d ; all bars: 5 in %d, 4 in %d, 3 in %d, <=2 in %d of %d' % (
        sgn_hi.count(5), sgn_hi.count(4), sgn_hi.count(3), sum(1 for x in sgn_hi if x <= 2), len(sgn_hi), sgn_all.count(5), sgn_all.count(4), sgn_all.count(3), sum(1 for x in sgn_all if x <= 2), len(sgn_all)))
    # (b) latency: rolling 5-min window, 1-min step
    lead = collections.Counter(); ratio = []; nhi = 0; ep_total = 0; ep_missed = 0; ep_len = []
    roll_hi_minutes = 0
    for d in days:
        dl = A[d][0]; roll = np.convolve(dl, np.ones(5), 'full')[:375]       # roll[m] = sum of minutes m-4..m (needs m>=4)
        roll[:4] = np.nan
        a5 = d5[d]
        for k in range(75):
            tot = a5[k]
            if abs(tot) >= th90:
                nhi += 1
                js = [j for j in range(5) if k * 5 + j >= 4 and abs(roll[k * 5 + j]) >= th90 and roll[k * 5 + j] * tot > 0]
                lead[4 - js[0] if js else -1] += 1
            w = roll[k * 5:k * 5 + 5]
            if not np.all(np.isnan(w)) and abs(tot) > 0: ratio.append(np.nanmax(np.abs(w)) / abs(tot) if abs(tot) >= th70 else np.nan)
        # episodes of the rolling window (minutes where |roll| >= p90): merge consecutive minutes with the same sign
        m = 4; eps = []
        while m < 375:
            if abs(roll[m]) >= th90:
                s = np.sign(roll[m]); st = m
                while m + 1 < 375 and abs(roll[m + 1]) >= th90 and np.sign(roll[m + 1]) == s: m += 1
                eps.append((st, m, s))
            m += 1
        for st, en, s in eps:
            ep_total += 1; ep_len.append(en - st + 1)
            ks = range((st - 4) // 5, en // 5 + 1)
            if not any(0 <= kk < 75 and abs(a5[kk]) >= th90 and a5[kk] * s > 0 for kk in ks): ep_missed += 1
    print('(b) aligned bars with |d5|>=p90: %d.  Minutes before the bar close at which a rolling 5-min window (1-min step) first showed the same sign and >= p90:' % nhi)
    print('    lead 4 min %d, 3 min %d, 2 min %d, 1 min %d, 0 (only at the close) %d, never inside the bar %d' % (lead[4], lead[3], lead[2], lead[1], lead[0], lead[-1]))
    print('    rolling-window episodes (consecutive minutes |roll5|>=p90, same sign): %d (median length %d min); episodes with NO aligned bar >= p90 of the same sign overlapping them: %d' % (ep_total, np.median(ep_len), ep_missed))
    r_ = [x for x in ratio if not np.isnan(x)]
    print('    for aligned bars with |d5|>=p70: the largest rolling window ending inside the bar / the aligned bar |d5|: median %.2f, p90 %.2f (>=1 by construction when the aligned window is one of the five)' % (np.median(r_), np.quantile(r_, .9)))
    # 1-min volume spikes hidden in 5-min bars: bars whose 5-min RVOL-ish rank is low but one minute carries a big share
    vol5 = {d: A[d][1].reshape(75, 5) for d in days}
    allv5 = np.concatenate([x.sum(1) for x in vol5.values()]); vmed = np.median(allv5)
    allv1 = np.concatenate([x.ravel() for x in vol5.values()]); p99 = np.quantile(allv1, .99)
    hid = 0; tot_hi1 = 0
    for d in days:
        for k in range(75):
            row = vol5[d][k]
            if row.max() >= p99:
                tot_hi1 += 1
                if row.sum() < np.quantile(allv5, .7): hid += 1
    print('    1-min volume >= its pooled p99 (%.0f lots): inside %d 5-min bars, of which the 5-min bar volume is below the pooled p70 5-min volume in %d' % (p99, tot_hi1, hid))
    print()
