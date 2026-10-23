"""Replay a full day minute by minute (causal) with the persistence filter. Returns per-minute records."""
from rules2 import *

N_HOLD = 10
_cache = {}


def replay(idx, day):
    k = (idx, day)
    if k in _cache:
        return _cache[k]
    d = Day(idx, day)
    rl = ruler_for(idx, day)
    shown = None
    cand = None
    cnt = 0
    since = None
    recs = {}
    for T in range(9*3600+20*60, 15*3600+31*60, 60):
        if not d.v or not d.ch or T < d.ts0 + 120:
            continue
        r = read(d, T, rl)
        if r['regime'] == 'WAIT':
            continue
        key = (r['regime'], r['dir'], r.get('pin'))
        if shown is None:
            shown = key
            since = T
        elif key != shown:
            if key == cand:
                cnt += 1
            else:
                cand = key
                cnt = 1
            if cnt >= N_HOLD:
                shown = key
                since = T - (N_HOLD-1)*60
                cand = None
                cnt = 0
        else:
            cand = None
            cnt = 0
        r['shown'] = shown
        r['since'] = since
        recs[T] = r
    out = (d, rl, recs)
    _cache[k] = out
    return out


if __name__ == '__main__':
    import sys
    idx, day = sys.argv[1], sys.argv[2]
    d, rl, recs = replay(idx, day)
    for hhmm in sys.argv[3:]:
        h, m = hhmm.split(':')
        T = int(h)*3600+int(m)*60
        r = recs[T]
        print(hhmm, r['shown'], 'since', fmt(r['since']), 'raw', r['regime'], r['dir'], r['phase'], 'flip', r['flip'],
              'F %.1f vwap %.1f sig %.1f z %+.2f' % (r['F'], r['vwap'], r['sigma'], r['z']), 'wr', r['wr'], 'fl15', r['fl15'], 'moved', r.get('moved30'))
