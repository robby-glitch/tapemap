"""Two Upstox side rules on the same book frames: v2feed's (whole frame volume to one side: quote, then tick rule;
THE READ's FLOW) vs ladder.py's (quote + mid + depth march; the ux bars that rank.py ranks it against). Read-only."""
import json, glob, gzip, sys
import numpy as np
sys.dont_write_bytecode = True
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/data/'
LOT = {'NIFTY': 65, 'BANKNIFTY': 30, 'SENSEX': 20}
d1m = {i: json.load(open(f'pr_1m_{i}.json')) for i in LOT}
for idx in LOT:
    res = []
    for day in ['2026-09-23', '2026-09-28', '2026-10-01', '2026-10-05', '2026-10-08', '2026-10-19']:
        f = glob.glob(D + f'book/book_{idx}_{day}.jsonl*')[0]
        op = gzip.open if f.endswith('.gz') else open
        prev, last, cum = None, 1, {}
        c = 0
        with op(f, 'rt', encoding='utf-8') as fh:
            for l in fh:
                try: r = json.loads(l)
                except ValueError: continue
                if 'ltp' not in r or 'vtt' not in r or r.get('ltp') is None or r.get('vtt') is None: continue
                if prev is not None:
                    v = max(0, r['vtt'] - prev['vtt']); ask = prev['a'][0][0] if prev.get('a') else None; bid = prev['b'][0][0] if prev.get('b') else None
                    ltp = r['ltp']
                    s = 1 if ask is not None and ltp >= ask else -1 if bid is not None and ltp <= bid else 1 if ltp > prev['ltp'] else -1 if ltp < prev['ltp'] else last
                    last = s; c += s * v
                    m = (int(r['t'] // 60000) + 330) % 1440
                    cum[m] = c / LOT[idx]
                prev = r
        lad = {}
        cc = 0
        for b in d1m[idx][day]['1m']:
            m = (int(b['t'] // 60000) + 330) % 1440
            cc += b['delta']; lad[m] = cc
        ms = [m for m in range(570, 925, 5) if m in cum and m in lad]
        a = np.array([cum[m] for m in ms]); b = np.array([lad[m] for m in ms])
        # 5-min increments
        da, db = np.diff(a), np.diff(b)
        res.append((day[5:], round(a[-1]), round(b[-1]), round(float(np.corrcoef(da, db)[0, 1]), 2), round(float(np.mean(np.sign(da) == np.sign(db))), 2)))
    print(idx, 'day: CVD at close v2feed-rule vs ladder (lots) · 5-min increment r · sign agree:', res)
