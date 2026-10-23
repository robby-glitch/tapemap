from rules2 import *
import json, sys, collections

N_HOLD = 10   # consecutive 1-min evaluations needed before the shown state switches
res = {}
summary = []
for idx in IDXS:
    for day in DAYS:
        d = Day(idx, day)
        if not d.v or not d.ch:
            continue
        rl = ruler_for(idx, day)
        shown = None
        cand = None
        cnt = 0
        seq = []
        raw_seq = []
        for T in range(9*3600+20*60, 15*3600+1, 60):
            if T < d.ts0 + 120:
                continue
            r = read(d, T, rl)
            if r['regime'] == 'WAIT':
                continue
            key = (r['regime'], r['dir'], r.get('pin'))
            raw_seq.append(key)
            if shown is None:
                shown = key
                cand = None
                cnt = 0
            elif key != shown:
                if key == cand:
                    cnt += 1
                else:
                    cand = key
                    cnt = 1
                if cnt >= N_HOLD:
                    shown = key
                    cand = None
                    cnt = 0
            else:
                cand = None
                cnt = 0
            seq.append((T, shown, r.get('flip'), r.get('phase')))
        if not seq:
            continue
        cnts = collections.Counter(s[1][0] + ('UP' if s[1][1] == 1 else ('DN' if s[1][1] == -1 else '')) for s in seq)
        sw = sum(1 for a, b in zip(seq, seq[1:]) if a[1] != b[1])
        rsw = sum(1 for a, b in zip(raw_seq, raw_seq[1:]) if a != b)
        n = len(seq)
        # longest run of UNCLEAR
        best = 0
        run = 0
        for s in seq:
            if s[1][0] == 'UNCLEAR':
                run += 1
                best = max(best, run)
            else:
                run = 0
        pct = {k: round(100*v/n) for k, v in cnts.items()}
        flipn = sum(1 for s in seq if s[2])
        summary.append((idx, day, n, pct, sw, rsw, best, round(100*flipn/n)))
        print('%-9s %s n=%3d switches shown %2d raw %3d longestUNCLEAR %3dm flipflag %2d%% | %s' % (idx, day[5:], n, sw, rsw, best, round(100*flipn/n), pct))
